"""TASK-013 restart-safe local creative-generation execution control.

This module consumes exact TASK-027 queue Evidence and can invoke only an
injected local/free execution port.  It deliberately contains no concrete
Provider adapter, credential lookup, Candidate publication or paid route.
"""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import re
import secrets
from threading import Lock
from typing import Any, Callable, Mapping, Protocol

from .ai_connections import (
    AiConnectionResolver,
    AiWorkload,
    ConnectionAvailability,
    CostClass,
    ModelRoute,
    ProviderFamily,
)
from .atomic import AtomicJsonWriter
from .connection_settings_store import ConnectionSettingsStore
from .errors import ProductError, ProductErrorCategory
from .generation_queue_application import Task027GenerationQueueApplication
from .production_control import SlotKind
from .production_control_store import _exclusive_snapshot_lock
from .product_project_store import ProductProjectManifestStore, _exclusive_project_lock
from .project_save import ProductProjectSaveCoordinator
from .serialization import canonical_json_bytes, sha256_bytes


TokenFactory = Callable[[], str]
AvailabilityFactory = Callable[[], ConnectionAvailability]
_STORE_NAME = "generation-executions.json"
_SETTINGS_NAME = "ai-connection-settings.json"
_MAX_STORE_BYTES = 8 * 1024 * 1024
_MAX_PROMPT_BYTES = 128 * 1024
_MAX_PENDING_CONFIRMATIONS = 256
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_ROUTE_VALUE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/:-]{0,199}")
_OUTPUT_REF_RE = re.compile(r"project-output://[A-Za-z0-9][A-Za-z0-9._/-]{0,499}")
_MEDIA_KINDS = {"IMAGE", "VIDEO", "AUDIO"}


@dataclass(frozen=True, slots=True)
class LocalGenerationExecutionRequest:
    execution_id: str
    queue_entry_id: str
    scene_id: str
    slot_id: str
    capability: str
    prompt_text: str
    prompt_sha256: str
    input_bindings: tuple[Mapping[str, Any], ...]
    rights_authorization_ref: str


@dataclass(frozen=True, slots=True)
class LocalGenerationExecutionResult:
    route_id: str
    provider_family: ProviderFamily
    provider_id: str
    model_id: str
    capability: str
    provider_operation_id: str
    output_ref: str
    output_sha256: str
    media_kind: str
    latency_ms: int | None = None

    def __post_init__(self) -> None:
        for value, name in (
            (self.route_id, "route_id"),
            (self.provider_id, "provider_id"),
            (self.model_id, "model_id"),
            (self.provider_operation_id, "provider_operation_id"),
        ):
            if not isinstance(value, str) or not _ROUTE_VALUE_RE.fullmatch(value):
                raise ValueError(f"{name} is invalid")
        if not isinstance(self.provider_family, ProviderFamily):
            raise ValueError("provider_family is invalid")
        if not isinstance(self.capability, str) or not self.capability:
            raise ValueError("capability is invalid")
        if not _OUTPUT_REF_RE.fullmatch(self.output_ref):
            raise ValueError("output_ref must use project-output://")
        output_path = PurePosixPath(self.output_ref.removeprefix("project-output://"))
        if any(part in {"", ".", ".."} for part in output_path.parts):
            raise ValueError("output_ref contains an unsafe path segment")
        if not _SHA_RE.fullmatch(self.output_sha256):
            raise ValueError("output_sha256 is invalid")
        if self.media_kind not in _MEDIA_KINDS:
            raise ValueError("media_kind is invalid")
        if self.latency_ms is not None and (
            isinstance(self.latency_ms, bool)
            or not isinstance(self.latency_ms, int)
            or self.latency_ms < 0
        ):
            raise ValueError("latency_ms is invalid")


@dataclass(frozen=True, slots=True)
class LocalGenerationRuntimeReadiness:
    route_id: str
    provider_id: str
    model_id: str
    workflow_sha256: str
    required_class_count: int
    runtime_policy: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.route_id, "route_id"),
            (self.provider_id, "provider_id"),
            (self.model_id, "model_id"),
            (self.runtime_policy, "runtime_policy"),
        ):
            if not isinstance(value, str) or not _ROUTE_VALUE_RE.fullmatch(value):
                raise ValueError(f"{name} is invalid")
        if not _SHA_RE.fullmatch(self.workflow_sha256):
            raise ValueError("workflow_sha256 is invalid")
        if isinstance(self.required_class_count, bool) or not isinstance(self.required_class_count, int) or self.required_class_count <= 0:
            raise ValueError("required_class_count must be positive")

    def as_dict(self) -> dict[str, Any]:
        return {
            "readiness_version": "1.0.0",
            "task_owner": "TASK-013",
            "result": "SAFE_RUNTIME_PREFLIGHT_PASS_EXECUTION_PARKED",
            "route_id": self.route_id,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "workflow_sha256": self.workflow_sha256,
            "required_class_count": self.required_class_count,
            "runtime_policy": self.runtime_policy,
            "read_only": True,
            "resource_admission_passed": True,
            "runtime_identity_passed": True,
            "dispatch_performed": False,
            "journal_created": False,
            "execution_authorized": False,
            "native_gate_satisfied": False,
        }


class LocalGenerationExecutionPort(Protocol):
    def preflight(self) -> LocalGenerationRuntimeReadiness: ...

    def execute(
        self,
        route: ModelRoute,
        request: LocalGenerationExecutionRequest,
    ) -> LocalGenerationExecutionResult: ...

LocalGenerationExecutionPortSelector = Callable[
    [ModelRoute, str], LocalGenerationExecutionPort
]


@dataclass(slots=True)
class _PendingExecution:
    confirmation_id: str
    queue_snapshot_sha256: str
    execution_snapshot_sha256: str
    queue_entry_id: str
    profile_sha256: str
    route_id: str
    capability: str
    prompt_sha256: str
    provider_id: str
    model_id: str
    workflow_sha256: str
    required_class_count: int
    runtime_policy: str
    project_manifest_sha256: str | None


def _with_hash(value: Mapping[str, Any]) -> dict[str, Any]:
    body = {key: item for key, item in value.items() if key != "execution_snapshot_sha256"}
    body["execution_snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


class Task013CreativeGenerationExecutionApplication:
    """Body-private, local-only, no-replay generation execution controller."""

    def __init__(
        self,
        *,
        project_root: str | Path,
        project_id: str,
        generation_queue: Task027GenerationQueueApplication,
        execution_port: LocalGenerationExecutionPort | None,
        availability_factory: AvailabilityFactory,
        execution_port_selector: LocalGenerationExecutionPortSelector | None = None,
        token_factory: TokenFactory | None = None,
    ) -> None:
        root = Path(project_root)
        if root.is_symlink() or not root.is_dir():
            raise ProductError("ERR_GENERATION_EXECUTION_PROJECT_ROOT", "Generation execution project root is invalid", ProductErrorCategory.VALIDATION)
        if generation_queue.project_root != root or generation_queue.project_id != project_id:
            raise ProductError("ERR_GENERATION_EXECUTION_SCOPE", "Generation execution and Queue must share exact project scope", ProductErrorCategory.SECURITY)
        self.project_root = root
        self.project_id = project_id
        self.generation_queue = generation_queue
        if (execution_port is None) == (execution_port_selector is None):
            raise ProductError(
                "ERR_GENERATION_EXECUTION_PORT_BINDING",
                "Bind exactly one fixed execution port or route/capability selector",
                ProductErrorCategory.VALIDATION,
            )
        self.execution_port = execution_port
        self.execution_port_selector = execution_port_selector
        self.availability_factory = availability_factory
        self.settings_path = root / _SETTINGS_NAME
        self.snapshot_path = root / _STORE_NAME
        self.private_prompt_root = root / "private" / "prompts"
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._confirmations: dict[str, _PendingExecution] = {}
        self._confirmation_lock = Lock()

    @staticmethod
    def _validate_port(port: Any) -> LocalGenerationExecutionPort:
        if not callable(getattr(port, "preflight", None)) or not callable(
            getattr(port, "execute", None)
        ):
            raise ProductError(
                "ERR_GENERATION_EXECUTION_PORT_UNSUPPORTED",
                "Selected local execution port is invalid",
                ProductErrorCategory.NOT_SUPPORTED,
            )
        return port

    def _port_for(
        self,
        *,
        route: ModelRoute | None = None,
        capability: str | None = None,
    ) -> LocalGenerationExecutionPort:
        if self.execution_port_selector is None:
            return self._validate_port(self.execution_port)
        if route is None or not isinstance(capability, str) or not capability:
            raise ProductError(
                "ERR_GENERATION_EXECUTION_PREFLIGHT_SCOPE_REQUIRED",
                "Queue entry is required to select a local execution runtime",
                ProductErrorCategory.VALIDATION,
            )
        try:
            selected = self.execution_port_selector(route, capability)
        except ProductError:
            raise
        except Exception as exc:
            raise ProductError(
                "ERR_GENERATION_EXECUTION_PORT_UNSUPPORTED",
                "No local execution port accepts the exact route and capability",
                ProductErrorCategory.NOT_SUPPORTED,
            ) from exc
        return self._validate_port(selected)

    @staticmethod
    def _preflight_port(
        port: LocalGenerationExecutionPort,
        *,
        route: ModelRoute | None = None,
    ) -> LocalGenerationRuntimeReadiness:
        readiness = port.preflight()
        if not isinstance(readiness, LocalGenerationRuntimeReadiness):
            raise ProductError(
                "ERR_GENERATION_PREFLIGHT_RESULT",
                "Local runtime preflight returned an invalid result",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if route is not None and (
            readiness.route_id != route.route_id
            or readiness.provider_id != route.provider_id
            or readiness.model_id != route.model_id
        ):
            raise ProductError(
                "ERR_GENERATION_PREFLIGHT_ROUTE_MISMATCH",
                "Local runtime readiness differs from the exact Queue route",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return readiness

    def _empty(self) -> dict[str, Any]:
        return _with_hash({
            "execution_store_version": "1.0.0",
            "task_owner": "TASK-013",
            "project_id": self.project_id,
            "revision": 0,
            "events": [],
            "paid_execution_authorized": False,
            "candidate_creation_authorized": False,
        })

    def _validate(self, value: Any) -> None:
        top = {
            "execution_store_version", "task_owner", "project_id", "revision",
            "events", "paid_execution_authorized", "candidate_creation_authorized",
            "execution_snapshot_sha256",
        }
        event_fields = {
            "event_version", "task_owner", "event_revision", "execution_id",
            "project_id", "queue_entry_id", "prompt_id", "prompt_version",
            "prompt_sha256", "profile_id", "profile_version", "profile_sha256",
            "route_id", "provider_family", "provider_id", "model_id", "workload",
            "capability", "cost_class", "state", "provider_operation_id",
            "output_ref", "output_sha256", "media_kind", "latency_ms", "failure_code",
            "provider_execution_started", "paid_execution_authorized",
            "candidate_creation_authorized",
        }
        if not isinstance(value, dict) or set(value) != top:
            raise ProductError("ERR_GENERATION_EXECUTION_SNAPSHOT", "Generation execution snapshot fields are invalid", ProductErrorCategory.DATA_INTEGRITY)
        if value.get("execution_store_version") != "1.0.0" or value.get("task_owner") != "TASK-013" or value.get("project_id") != self.project_id:
            raise ProductError("ERR_GENERATION_EXECUTION_SNAPSHOT", "Generation execution snapshot identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
        if value.get("execution_snapshot_sha256") != _with_hash(value)["execution_snapshot_sha256"]:
            raise ProductError("ERR_GENERATION_EXECUTION_CHECKSUM", "Generation execution snapshot checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
        if value.get("paid_execution_authorized") is not False or value.get("candidate_creation_authorized") is not False:
            raise ProductError("ERR_GENERATION_EXECUTION_AUTHORITY", "Generation execution snapshot exceeds bounded authority", ProductErrorCategory.SECURITY)
        revision, events = value.get("revision"), value.get("events")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0 or not isinstance(events, list) or revision != len(events):
            raise ProductError("ERR_GENERATION_EXECUTION_REVISION", "Generation execution history is invalid", ProductErrorCategory.DATA_INTEGRITY)
        latest: dict[str, str] = {}
        identities: dict[str, dict[str, Any]] = {}
        queue_owner: dict[str, str] = {}
        for index, event in enumerate(events, 1):
            if not isinstance(event, dict) or set(event) != event_fields or event.get("event_revision") != index:
                raise ProductError("ERR_GENERATION_EXECUTION_EVENT", "Generation execution event fields/revision are invalid", ProductErrorCategory.DATA_INTEGRITY)
            if event.get("event_version") != "1.0.0" or event.get("task_owner") != "TASK-013" or event.get("project_id") != self.project_id:
                raise ProductError("ERR_GENERATION_EXECUTION_EVENT", "Generation execution event identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
            if event.get("cost_class") != CostClass.LOCAL_FREE_AI.value or event.get("paid_execution_authorized") is not False or event.get("candidate_creation_authorized") is not False:
                raise ProductError("ERR_GENERATION_EXECUTION_AUTHORITY", "Execution event contains a prohibited route or authority", ProductErrorCategory.SECURITY)
            if not all(isinstance(event.get(name), str) and _SHA_RE.fullmatch(event[name]) for name in ("prompt_sha256", "profile_sha256")):
                raise ProductError("ERR_GENERATION_EXECUTION_EVENT", "Execution event hashes are invalid", ProductErrorCategory.DATA_INTEGRITY)
            execution_id = event.get("execution_id")
            queue_entry_id = event.get("queue_entry_id")
            if not isinstance(execution_id, str) or not _ID_RE.fullmatch(execution_id) or not isinstance(queue_entry_id, str) or not _ID_RE.fullmatch(queue_entry_id):
                raise ProductError("ERR_GENERATION_EXECUTION_EVENT", "Execution/Queue identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
            if queue_entry_id in queue_owner and queue_owner[queue_entry_id] != execution_id:
                raise ProductError("ERR_GENERATION_EXECUTION_DUPLICATE", "One Queue entry cannot own multiple executions", ProductErrorCategory.DATA_INTEGRITY)
            queue_owner[queue_entry_id] = execution_id
            previous = latest.get(execution_id)
            state = event.get("state")
            identity = {key: event[key] for key in (
                "execution_id", "project_id", "queue_entry_id", "prompt_id", "prompt_version",
                "prompt_sha256", "profile_id", "profile_version", "profile_sha256", "route_id",
                "provider_family", "provider_id", "model_id", "workload", "capability", "cost_class",
            )}
            if execution_id in identities and identity != identities[execution_id]:
                raise ProductError("ERR_GENERATION_EXECUTION_IDENTITY_DRIFT", "Execution identity changed between events", ProductErrorCategory.DATA_INTEGRITY)
            identities[execution_id] = identity
            if previous is None and state != "DISPATCHING":
                raise ProductError("ERR_GENERATION_EXECUTION_TRANSITION", "Execution must start with DISPATCHING", ProductErrorCategory.DATA_INTEGRITY)
            if previous is not None and not (previous == "DISPATCHING" and state in {"COMPLETED", "FAILED"}):
                raise ProductError("ERR_GENERATION_EXECUTION_TRANSITION", "Execution state transition is invalid", ProductErrorCategory.DATA_INTEGRITY)
            if state == "DISPATCHING":
                if event.get("provider_execution_started") is not True or any(event.get(name) is not None for name in ("provider_operation_id", "output_ref", "output_sha256", "media_kind", "latency_ms", "failure_code")):
                    raise ProductError("ERR_GENERATION_EXECUTION_EVENT", "DISPATCHING event payload is invalid", ProductErrorCategory.DATA_INTEGRITY)
            elif state == "COMPLETED":
                if event.get("provider_execution_started") is not True or event.get("failure_code") is not None:
                    raise ProductError("ERR_GENERATION_EXECUTION_EVENT", "COMPLETED event payload is invalid", ProductErrorCategory.DATA_INTEGRITY)
                if not _OUTPUT_REF_RE.fullmatch(event.get("output_ref", "")) or not _SHA_RE.fullmatch(event.get("output_sha256", "")) or event.get("media_kind") not in _MEDIA_KINDS:
                    raise ProductError("ERR_GENERATION_EXECUTION_EVENT", "COMPLETED output Evidence is invalid", ProductErrorCategory.DATA_INTEGRITY)
                output_path = PurePosixPath(event["output_ref"].removeprefix("project-output://"))
                if any(part in {"", ".", ".."} for part in output_path.parts) or not isinstance(event.get("provider_operation_id"), str) or not _ROUTE_VALUE_RE.fullmatch(event["provider_operation_id"]):
                    raise ProductError("ERR_GENERATION_EXECUTION_EVENT", "COMPLETED operation/output reference is invalid", ProductErrorCategory.DATA_INTEGRITY)
            elif state == "FAILED":
                if event.get("provider_execution_started") is not True or not isinstance(event.get("failure_code"), str) or not _ID_RE.fullmatch(event["failure_code"]):
                    raise ProductError("ERR_GENERATION_EXECUTION_EVENT", "FAILED event payload is invalid", ProductErrorCategory.DATA_INTEGRITY)
                if any(event.get(name) is not None for name in ("provider_operation_id", "output_ref", "output_sha256", "media_kind", "latency_ms")):
                    raise ProductError("ERR_GENERATION_EXECUTION_EVENT", "FAILED event must not claim output Evidence", ProductErrorCategory.DATA_INTEGRITY)
            else:
                raise ProductError("ERR_GENERATION_EXECUTION_STATE", "Unknown generation execution state", ProductErrorCategory.DATA_INTEGRITY)
            latest[execution_id] = state

    def _load(self) -> dict[str, Any]:
        target = self.snapshot_path
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ProductError("ERR_GENERATION_EXECUTION_FILE", "Generation execution snapshot must be a regular non-symlink file", ProductErrorCategory.SECURITY)
        if not target.exists():
            return self._empty()
        size = target.stat().st_size
        if size <= 0 or size > _MAX_STORE_BYTES:
            raise ProductError("ERR_GENERATION_EXECUTION_SIZE", "Generation execution snapshot size is invalid", ProductErrorCategory.DATA_INTEGRITY)
        try:
            value = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_GENERATION_EXECUTION_READ", "Generation execution snapshot could not be read", ProductErrorCategory.DATA_INTEGRITY) from exc
        self._validate(value)
        return value

    @staticmethod
    def _mode_for_slot(slot_kind: str, has_inputs: bool) -> tuple[AiWorkload, str, str]:
        if slot_kind in {SlotKind.START_FRAME.value, SlotKind.END_FRAME.value}:
            return AiWorkload.IMAGE, "IMAGE_TO_IMAGE" if has_inputs else "TEXT_TO_IMAGE", "IMAGE"
        if slot_kind in {SlotKind.VIDEO.value, SlotKind.VFX.value}:
            return AiWorkload.VIDEO, "IMAGE_TO_VIDEO" if has_inputs else "TEXT_TO_VIDEO", "VIDEO"
        if slot_kind == SlotKind.SE.value:
            return AiWorkload.AUDIO, "SFX", "AUDIO"
        if slot_kind == SlotKind.BGM.value:
            return AiWorkload.MUSIC, "MUSIC_GENERATION", "AUDIO"
        if slot_kind == SlotKind.NARRATION.value:
            raise ProductError("ERR_GENERATION_EXECUTION_TASK014_REQUIRED", "Narration execution belongs to TASK-014", ProductErrorCategory.NOT_SUPPORTED)
        raise ProductError("ERR_GENERATION_EXECUTION_SLOT_KIND", "Target Slot kind has no TASK-013 generation mode", ProductErrorCategory.NOT_SUPPORTED, details={"slot_kind": slot_kind})

    def _prompt_text(self, body_ref: Any, expected_sha256: str) -> str:
        prefix = "project-private://prompts/"
        if not isinstance(body_ref, str) or not body_ref.startswith(prefix):
            raise ProductError("ERR_GENERATION_EXECUTION_PROMPT_REF", "Prompt body must use project-private://prompts/", ProductErrorCategory.SECURITY)
        relative = PurePosixPath(body_ref[len(prefix):])
        if relative.is_absolute() or not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
            raise ProductError("ERR_GENERATION_EXECUTION_PROMPT_REF", "Prompt body reference is invalid", ProductErrorCategory.SECURITY)
        if self.private_prompt_root.is_symlink() or not self.private_prompt_root.is_dir():
            raise ProductError("ERR_GENERATION_EXECUTION_PROMPT_ROOT", "Private Prompt root is missing or unsafe", ProductErrorCategory.SECURITY)
        target = self.private_prompt_root
        for part in relative.parts:
            target = target / part
            if target.is_symlink():
                raise ProductError("ERR_GENERATION_EXECUTION_PROMPT_SYMLINK", "Prompt body path must not contain a symlink", ProductErrorCategory.SECURITY)
        try:
            target.resolve(strict=False).relative_to(self.private_prompt_root.resolve(strict=False))
        except ValueError as exc:
            raise ProductError("ERR_GENERATION_EXECUTION_PROMPT_ESCAPE", "Prompt body reference escapes the private root", ProductErrorCategory.SECURITY) from exc
        if target.is_symlink() or not target.is_file():
            raise ProductError("ERR_GENERATION_EXECUTION_PROMPT_FILE", "Prompt body file is missing or unsafe", ProductErrorCategory.VALIDATION)
        size = target.stat().st_size
        if size <= 0 or size > _MAX_PROMPT_BYTES:
            raise ProductError("ERR_GENERATION_EXECUTION_PROMPT_SIZE", "Prompt body file size is invalid", ProductErrorCategory.VALIDATION)
        try:
            raw = target.read_bytes()
            text = raw.decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise ProductError("ERR_GENERATION_EXECUTION_PROMPT_READ", "Prompt body must be readable UTF-8", ProductErrorCategory.DATA_INTEGRITY) from exc
        if sha256_bytes(raw) != expected_sha256:
            raise ProductError("ERR_GENERATION_EXECUTION_PROMPT_CHECKSUM", "Private Prompt body does not match Queue Evidence", ProductErrorCategory.DATA_INTEGRITY)
        if not text.strip() or "\x00" in text:
            raise ProductError("ERR_GENERATION_EXECUTION_PROMPT_CONTENT", "Private Prompt body content is invalid", ProductErrorCategory.VALIDATION)
        return text

    def _derive(self, queue_entry_id: str) -> tuple[dict[str, Any], Any, ModelRoute, str, str, AiWorkload, str, str]:
        current = self.generation_queue.require_current_entry(queue_entry_id=queue_entry_id)
        queue, entry = current, current["entry"]
        if entry["queue_status"] != "ADMISSION_READY" or entry["execution_status"] != "EXECUTION_NOT_AUTHORIZED":
            raise ProductError("ERR_GENERATION_EXECUTION_QUEUE_STATE", "Queue entry is not an exact execution candidate", ProductErrorCategory.AUTHORIZATION)
        prompts = self.generation_queue.prompt_evidence_application.snapshot()
        prompt = next((item for item in prompts["prompts"] if item["prompt_id"] == entry["prompt_id"] and item["prompt_version"] == entry["prompt_version"]), None)
        if prompt is None or prompt["body_sha256"] != entry["prompt_sha256"] or prompt["provider_profile_id"] != entry["provider_profile_id"] or prompt["provider_profile_version"] != entry["provider_profile_version"]:
            raise ProductError("ERR_GENERATION_EXECUTION_PROMPT_DRIFT", "Prompt Evidence differs from the exact Queue entry", ProductErrorCategory.AUTHORIZATION)
        production = self.generation_queue.production_control.snapshot()
        slot = next((item for item in production["slots"] if item["slot_id"] == entry["slot_id"]), None)
        if slot is None or slot["scene_id"] != entry["scene_id"]:
            raise ProductError("ERR_GENERATION_EXECUTION_SLOT_DRIFT", "Target Slot differs from Queue Evidence", ProductErrorCategory.DATA_INTEGRITY)
        workload, capability, media_kind = self._mode_for_slot(slot["slot_kind"], bool(entry["input_bindings"]))
        settings = ConnectionSettingsStore.load(self.settings_path).record
        profile = settings.profile
        profile_sha = profile.to_dict()["profile_sha256"]
        if profile.profile_id != entry["provider_profile_id"] or profile.profile_version != entry["provider_profile_version"]:
            raise ProductError("ERR_GENERATION_EXECUTION_PROFILE_DRIFT", "Current Provider Profile differs from Queue/Human GO", ProductErrorCategory.AUTHORIZATION)
        route = AiConnectionResolver.resolve(profile, workload, self.availability_factory(), required_capabilities=(capability,))
        if (
            not route.enabled
            or route.cost_class is not CostClass.LOCAL_FREE_AI
            or route.credential_ref is not None
            or route.endpoint_ref is not None
            or route.settings != {}
            or route.capabilities != (capability,)
        ):
            raise ProductError(
                "ERR_GENERATION_EXECUTION_LOCAL_ONLY",
                "This unit permits only an enabled, exact-capability, configuration-free LOCAL_FREE_AI route",
                ProductErrorCategory.AUTHORIZATION,
                details={"cost_class": route.cost_class.value},
            )
        prompt_text = self._prompt_text(prompt.get("body_ref"), entry["prompt_sha256"])
        return queue, entry, route, profile_sha, prompt_text, workload, capability, media_kind

    def snapshot(self) -> dict[str, Any]:
        store = self._load()
        latest: dict[str, dict[str, Any]] = {}
        for event in store["events"]:
            latest[event["execution_id"]] = event
        dispatched_queue_ids = {event["queue_entry_id"] for event in store["events"]}
        queue = self.generation_queue.snapshot()
        available = [
            {"queue_entry_id": item["queue_entry_id"], "scene_id": item["scene_id"], "slot_id": item["slot_id"], "prompt_id": item["prompt_id"], "prompt_version": item["prompt_version"]}
            for item in queue["entries"] if item["queue_entry_id"] not in dispatched_queue_ids
        ]
        recovery = []
        for event in latest.values():
            if event["state"] != "DISPATCHING":
                continue
            recovery_supported = False
            try:
                _queue, _entry, route, _profile_sha, _prompt, _workload, capability, _media = self._derive(
                    event["queue_entry_id"]
                )
                port = self._port_for(route=route, capability=capability)
                recovery_supported = (
                    route.route_id == event["route_id"]
                    and route.provider_id == event["provider_id"]
                    and route.model_id == event["model_id"]
                    and capability == event["capability"]
                    and callable(getattr(port, "recover", None))
                )
            except ProductError:
                recovery_supported = False
            recovery.append({**event, "recovery_supported": recovery_supported})
        return {
            "application_version": "1.0.0", "task_owner": "TASK-013", "project_id": self.project_id,
            "execution_snapshot_sha256": store["execution_snapshot_sha256"], "queue_snapshot_sha256": queue["queue_snapshot_sha256"],
            "events": list(store["events"]), "latest_executions": list(latest.values()), "available_queue_entries": available,
            "recovery": {
                "required": bool(recovery),
                "dispatching": recovery,
                "human_recovery_available": any(item["recovery_supported"] for item in recovery),
                "automatic_retry_allowed": False,
            },
            "paid_execution_authorized": False, "candidate_creation_authorized": False, "resolve_mutation_started": False,
        }

    def runtime_preflight(self, *, queue_entry_id: str | None = None) -> dict[str, Any]:
        """Inspect the bound local runtime without creating execution Authority."""
        route = None
        capability = None
        if queue_entry_id is not None:
            if not isinstance(queue_entry_id, str) or not queue_entry_id.strip():
                raise ProductError(
                    "ERR_GENERATION_EXECUTION_PREFLIGHT_SCOPE_REQUIRED",
                    "Queue entry is required to select a local execution runtime",
                    ProductErrorCategory.VALIDATION,
                )
            _queue, _entry, route, _profile_sha, _prompt, _workload, capability, _media = self._derive(queue_entry_id)
        port = self._port_for(route=route, capability=capability)
        readiness = self._preflight_port(port, route=route)
        return readiness.as_dict()

    def prepare_execution(
        self,
        *,
        queue_entry_id: str,
        expected_queue_snapshot_sha256: str,
        expected_execution_snapshot_sha256: str,
        expected_project_manifest_sha256: str | None = None,
    ) -> dict[str, Any]:
        store = self._load()
        if expected_project_manifest_sha256 is not None:
            if not isinstance(expected_project_manifest_sha256, str) or not _SHA_RE.fullmatch(expected_project_manifest_sha256):
                raise ProductError("ERR_GENERATION_EXECUTION_MANIFEST_EXPECTED_INVALID", "Expected Project manifest identity is invalid", ProductErrorCategory.VALIDATION)
            manifest = ProductProjectManifestStore.load(self.project_root)
            if manifest.project_id != self.project_id or manifest.project_manifest_sha256 != expected_project_manifest_sha256:
                raise ProductError("ERR_GENERATION_EXECUTION_MANIFEST_CONFLICT", "Project manifest changed before execution confirmation", ProductErrorCategory.AUTHORIZATION)
        queue, entry, route, profile_sha, _prompt_text, _workload, capability, media_kind = self._derive(queue_entry_id)
        if queue["queue_snapshot_sha256"] != expected_queue_snapshot_sha256 or store["execution_snapshot_sha256"] != expected_execution_snapshot_sha256:
            raise ProductError("ERR_GENERATION_EXECUTION_CONFLICT", "Queue or execution state changed; reload before execution", ProductErrorCategory.STATE)
        if any(event["queue_entry_id"] == queue_entry_id for event in store["events"]):
            raise ProductError("ERR_GENERATION_EXECUTION_ALREADY_DISPATCHED", "Queue entry already has execution history", ProductErrorCategory.STATE)
        port = self._port_for(route=route, capability=capability)
        readiness = self._preflight_port(port, route=route)
        token = self._token_factory()
        pending = _PendingExecution(
            token, queue["queue_snapshot_sha256"], store["execution_snapshot_sha256"],
            queue_entry_id, profile_sha, route.route_id, capability,
            entry["prompt_sha256"], readiness.provider_id, readiness.model_id,
            readiness.workflow_sha256, readiness.required_class_count,
            readiness.runtime_policy,
            expected_project_manifest_sha256,
        )
        with self._confirmation_lock:
            if not isinstance(token, str) or not token.strip() or token in self._confirmations:
                raise ProductError("ERR_GENERATION_EXECUTION_CONFIRMATION", "Generation execution confirmation token is invalid", ProductErrorCategory.INTERNAL)
            if len(self._confirmations) >= _MAX_PENDING_CONFIRMATIONS:
                raise ProductError(
                    "ERR_GENERATION_EXECUTION_CONFIRMATION_CAPACITY",
                    "Generation execution confirmation capacity is exhausted; cancel an unused confirmation",
                    ProductErrorCategory.STATE,
                )
            self._confirmations[token] = pending
        return {
            "confirmation_id": token, "queue_entry_id": queue_entry_id, "scene_id": entry["scene_id"], "slot_id": entry["slot_id"],
            "prompt_id": entry["prompt_id"], "prompt_version": entry["prompt_version"], "prompt_sha256": entry["prompt_sha256"],
            "route_id": route.route_id, "provider_family": route.provider_family.value, "provider_id": route.provider_id, "model_id": route.model_id,
            "capability": pending.capability, "cost_class": route.cost_class.value, "media_kind": media_kind,
            "human_final_authority_required": True, "provider_execution_started": False, "paid_execution_authorized": False,
            "prompt_body_exposed": False, "automatic_retry_allowed": False,
        }

    def _append(self, store: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        store["revision"] += 1
        event["event_revision"] = store["revision"]
        store["events"].append(event)
        document = _with_hash(store)
        AtomicJsonWriter.write(self.snapshot_path, document, validator=self._validate)
        return document

    @staticmethod
    def _event_base(*, revision: int, execution_id: str, entry: Mapping[str, Any], profile_sha: str, route: ModelRoute, workload: AiWorkload, capability: str) -> dict[str, Any]:
        return {
            "event_version": "1.0.0", "task_owner": "TASK-013", "event_revision": revision, "execution_id": execution_id,
            "project_id": entry["project_id"], "queue_entry_id": entry["queue_entry_id"], "prompt_id": entry["prompt_id"],
            "prompt_version": entry["prompt_version"], "prompt_sha256": entry["prompt_sha256"], "profile_id": entry["provider_profile_id"],
            "profile_version": entry["provider_profile_version"], "profile_sha256": profile_sha, "route_id": route.route_id,
            "provider_family": route.provider_family.value, "provider_id": route.provider_id, "model_id": route.model_id,
            "workload": workload.value, "capability": capability, "cost_class": route.cost_class.value,
            "state": None, "provider_operation_id": None, "output_ref": None, "output_sha256": None, "media_kind": None,
            "latency_ms": None, "failure_code": None, "provider_execution_started": True,
            "paid_execution_authorized": False, "candidate_creation_authorized": False,
        }

    def apply_execution(self, *, confirmation_id: str) -> dict[str, Any]:
        if not isinstance(confirmation_id, str) or not confirmation_id.strip():
            raise ProductError("ERR_GENERATION_EXECUTION_CONFIRMATION", "Generation execution confirmation is invalid", ProductErrorCategory.AUTHORIZATION)
        with self._confirmation_lock:
            pending = self._confirmations.pop(confirmation_id, None)
        if pending is None:
            raise ProductError("ERR_GENERATION_EXECUTION_CONFIRMATION", "Generation execution confirmation is missing or already used", ProductErrorCategory.AUTHORIZATION)
        queue, entry, route, profile_sha, prompt_text, workload, capability, media_kind = self._derive(pending.queue_entry_id)
        if queue["queue_snapshot_sha256"] != pending.queue_snapshot_sha256 or profile_sha != pending.profile_sha256 or route.route_id != pending.route_id or entry["prompt_sha256"] != pending.prompt_sha256:
            raise ProductError("ERR_GENERATION_EXECUTION_CONFIRMATION_STALE", "Queue, Prompt, Profile or route changed after confirmation", ProductErrorCategory.AUTHORIZATION)
        if capability != pending.capability:
            raise ProductError("ERR_GENERATION_EXECUTION_CONFIRMATION_STALE", "Generation mode changed after confirmation", ProductErrorCategory.AUTHORIZATION)
        port = self._port_for(route=route, capability=capability)
        readiness = self._preflight_port(port, route=route)
        if (
            readiness.provider_id != pending.provider_id
            or readiness.model_id != pending.model_id
            or readiness.workflow_sha256 != pending.workflow_sha256
            or readiness.required_class_count != pending.required_class_count
            or readiness.runtime_policy != pending.runtime_policy
        ):
            raise ProductError(
                "ERR_GENERATION_EXECUTION_CONFIRMATION_STALE",
                "Local runtime identity changed after confirmation",
                ProductErrorCategory.AUTHORIZATION,
            )
        project_guard = (
            nullcontext()
            if pending.project_manifest_sha256 is None
            else _exclusive_project_lock(ProductProjectManifestStore.path(self.project_root))
        )
        with project_guard:
            if pending.project_manifest_sha256 is not None:
                manifest = ProductProjectManifestStore.load(self.project_root)
                if manifest.project_id != self.project_id or manifest.project_manifest_sha256 != pending.project_manifest_sha256:
                    raise ProductError("ERR_GENERATION_EXECUTION_MANIFEST_CONFLICT", "Project manifest changed after execution confirmation", ProductErrorCategory.AUTHORIZATION)
                ProductProjectSaveCoordinator().require_current_integrity(self.project_root, manifest)
            with _exclusive_snapshot_lock(self.snapshot_path):
                store = self._load()
                if store["execution_snapshot_sha256"] != pending.execution_snapshot_sha256:
                    raise ProductError("ERR_GENERATION_EXECUTION_CONFLICT", "Execution state changed after confirmation", ProductErrorCategory.STATE)
                # This post-preflight re-derive is the admission linearization point
                # for Queue/Prompt/Profile currentness. No Provider side effect or
                # DISPATCHING record exists before this exact recheck.
                queue, entry, route, profile_sha, prompt_text, workload, capability, media_kind = self._derive(pending.queue_entry_id)
                if (
                    queue["queue_snapshot_sha256"] != pending.queue_snapshot_sha256
                    or profile_sha != pending.profile_sha256
                    or route.route_id != pending.route_id
                    or entry["prompt_sha256"] != pending.prompt_sha256
                    or capability != pending.capability
                    or route.provider_id != pending.provider_id
                    or route.model_id != pending.model_id
                ):
                    raise ProductError(
                        "ERR_GENERATION_EXECUTION_CONFIRMATION_STALE",
                        "Queue, Prompt, Profile, route or runtime changed during preflight",
                        ProductErrorCategory.AUTHORIZATION,
                    )
                if any(event["queue_entry_id"] == entry["queue_entry_id"] for event in store["events"]):
                    raise ProductError("ERR_GENERATION_EXECUTION_ALREADY_DISPATCHED", "Queue entry already has execution history", ProductErrorCategory.STATE)
                seed = {"queue_entry_id": entry["queue_entry_id"], "profile_sha256": profile_sha, "route_id": route.route_id, "capability": capability}
                execution_id = "EXEC-" + sha256_bytes(canonical_json_bytes(seed)).split(":", 1)[1][:24].upper()
                event = self._event_base(revision=store["revision"] + 1, execution_id=execution_id, entry=entry, profile_sha=profile_sha, route=route, workload=workload, capability=capability)
                event["state"] = "DISPATCHING"
                self._append(store, event)
        request = LocalGenerationExecutionRequest(
            execution_id, entry["queue_entry_id"], entry["scene_id"], entry["slot_id"], capability,
            prompt_text, entry["prompt_sha256"], tuple(entry["input_bindings"]), f"rights://{self.project_id}/{entry['scene_id']}",
        )
        try:
            result = port.execute(route, request)
            if (
                result.route_id != route.route_id or result.provider_family is not route.provider_family
                or result.provider_id != route.provider_id or result.model_id != route.model_id
                or result.capability != capability or result.media_kind != media_kind
            ):
                raise ProductError("ERR_GENERATION_EXECUTION_RESULT_MISMATCH", "Local execution result identity differs from the authorized route", ProductErrorCategory.DATA_INTEGRITY)
        except ProductError as exc:
            if exc.details.get("execution_state_uncertain") is True:
                raise
            with _exclusive_snapshot_lock(self.snapshot_path):
                store = self._load()
                failed = self._event_base(revision=store["revision"] + 1, execution_id=execution_id, entry=entry, profile_sha=profile_sha, route=route, workload=workload, capability=capability)
                failed["state"] = "FAILED"
                failed["failure_code"] = exc.code if _ID_RE.fullmatch(exc.code) else "ERR_GENERATION_EXECUTION_PORT"
                self._append(store, failed)
            raise
        with _exclusive_snapshot_lock(self.snapshot_path):
            store = self._load()
            completed = self._event_base(revision=store["revision"] + 1, execution_id=execution_id, entry=entry, profile_sha=profile_sha, route=route, workload=workload, capability=capability)
            completed.update({
                "state": "COMPLETED", "provider_operation_id": result.provider_operation_id, "output_ref": result.output_ref,
                "output_sha256": result.output_sha256, "media_kind": result.media_kind, "latency_ms": result.latency_ms,
            })
            self._append(store, completed)
        return self.snapshot()

    def cancel_execution(self, *, confirmation_id: str) -> dict[str, Any]:
        """Consume one unused Human confirmation without starting execution."""
        if not isinstance(confirmation_id, str) or not confirmation_id.strip():
            raise ProductError("ERR_GENERATION_EXECUTION_CONFIRMATION", "Generation execution confirmation is invalid", ProductErrorCategory.AUTHORIZATION)
        with self._confirmation_lock:
            pending = self._confirmations.pop(confirmation_id, None)
        if pending is None:
            raise ProductError("ERR_GENERATION_EXECUTION_CONFIRMATION", "Generation execution confirmation is missing or already used", ProductErrorCategory.AUTHORIZATION)
        return {
            "confirmation_id": confirmation_id,
            "queue_entry_id": pending.queue_entry_id,
            "cancelled": True,
            "provider_execution_started": False,
            "dispatch_performed": False,
            "execution_history_created": False,
            "paid_execution_authorized": False,
        }

    def recover_execution(
        self,
        *,
        execution_id: str,
        expected_execution_snapshot_sha256: str,
    ) -> dict[str, Any]:
        """Human-triggered reconciliation of one durable DISPATCHING execution.

        This path never calls ``execute`` and therefore cannot enqueue Provider
        work.  It only asks the exact selected port to reconcile its own
        operation journal/history, then appends one matching terminal event.
        """
        if not isinstance(execution_id, str) or not _ID_RE.fullmatch(execution_id):
            raise ProductError(
                "ERR_GENERATION_EXECUTION_RECOVERY_ID",
                "Generation execution recovery identity is invalid",
                ProductErrorCategory.VALIDATION,
            )
        if (
            not isinstance(expected_execution_snapshot_sha256, str)
            or not _SHA_RE.fullmatch(expected_execution_snapshot_sha256)
        ):
            raise ProductError(
                "ERR_GENERATION_EXECUTION_RECOVERY_SNAPSHOT",
                "Generation execution recovery snapshot identity is invalid",
                ProductErrorCategory.VALIDATION,
            )
        with _exclusive_snapshot_lock(self.snapshot_path):
            store = self._load()
            if store["execution_snapshot_sha256"] != expected_execution_snapshot_sha256:
                raise ProductError(
                    "ERR_GENERATION_EXECUTION_RECOVERY_CONFLICT",
                    "Generation execution state changed; reload before recovery",
                    ProductErrorCategory.STATE,
                )
            latest = next(
                (
                    event
                    for event in reversed(store["events"])
                    if event["execution_id"] == execution_id
                ),
                None,
            )
            if latest is None or latest["state"] != "DISPATCHING":
                raise ProductError(
                    "ERR_GENERATION_EXECUTION_RECOVERY_STATE",
                    "Only the exact current DISPATCHING execution can be recovered",
                    ProductErrorCategory.STATE,
                )
            (
                _queue,
                entry,
                route,
                profile_sha,
                prompt_text,
                workload,
                capability,
                media_kind,
            ) = self._derive(latest["queue_entry_id"])
            identity = {
                "project_id": entry["project_id"],
                "queue_entry_id": entry["queue_entry_id"],
                "prompt_id": entry["prompt_id"],
                "prompt_version": entry["prompt_version"],
                "prompt_sha256": entry["prompt_sha256"],
                "profile_id": entry["provider_profile_id"],
                "profile_version": entry["provider_profile_version"],
                "profile_sha256": profile_sha,
                "route_id": route.route_id,
                "provider_family": route.provider_family.value,
                "provider_id": route.provider_id,
                "model_id": route.model_id,
                "workload": workload.value,
                "capability": capability,
                "cost_class": route.cost_class.value,
            }
            if any(latest[name] != value for name, value in identity.items()):
                raise ProductError(
                    "ERR_GENERATION_EXECUTION_RECOVERY_IDENTITY",
                    "Current Queue, Prompt, Profile or route differs from the interrupted execution",
                    ProductErrorCategory.AUTHORIZATION,
                )
            port = self._port_for(route=route, capability=capability)
            recover = getattr(port, "recover", None)
            if not callable(recover):
                raise ProductError(
                    "ERR_GENERATION_EXECUTION_RECOVERY_UNSUPPORTED",
                    "The exact local execution port cannot reconcile interrupted work",
                    ProductErrorCategory.NOT_SUPPORTED,
                )
            request = LocalGenerationExecutionRequest(
                execution_id,
                entry["queue_entry_id"],
                entry["scene_id"],
                entry["slot_id"],
                capability,
                prompt_text,
                entry["prompt_sha256"],
                tuple(entry["input_bindings"]),
                f"rights://{self.project_id}/{entry['scene_id']}",
            )
            terminal_failure = False
            try:
                result = recover(route, request)
            except ProductError as exc:
                if exc.details.get("execution_state_terminal_failure") is not True:
                    raise
                failed = self._event_base(
                    revision=store["revision"] + 1,
                    execution_id=execution_id,
                    entry=entry,
                    profile_sha=profile_sha,
                    route=route,
                    workload=workload,
                    capability=capability,
                )
                failed["state"] = "FAILED"
                failed["failure_code"] = (
                    exc.code
                    if _ID_RE.fullmatch(exc.code)
                    else "ERR_GENERATION_EXECUTION_RECOVERY_FAILED"
                )
                self._append(store, failed)
                terminal_failure = True
            except Exception as exc:
                raise ProductError(
                    "ERR_GENERATION_EXECUTION_RECOVERY_PORT",
                    "Local generation recovery failed without terminal Evidence",
                    ProductErrorCategory.EXTERNAL_DEPENDENCY,
                ) from exc
            if not terminal_failure and (
                not isinstance(result, LocalGenerationExecutionResult) or (
                result.route_id != route.route_id
                or result.provider_family is not route.provider_family
                or result.provider_id != route.provider_id
                or result.model_id != route.model_id
                or result.capability != capability
                or result.media_kind != media_kind
                )
            ):
                raise ProductError(
                    "ERR_GENERATION_EXECUTION_RECOVERY_RESULT",
                    "Recovered local output differs from the interrupted execution identity",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            if not terminal_failure:
                completed = self._event_base(
                    revision=store["revision"] + 1,
                    execution_id=execution_id,
                    entry=entry,
                    profile_sha=profile_sha,
                    route=route,
                    workload=workload,
                    capability=capability,
                )
                completed.update(
                    {
                        "state": "COMPLETED",
                        "provider_operation_id": result.provider_operation_id,
                        "output_ref": result.output_ref,
                        "output_sha256": result.output_sha256,
                        "media_kind": result.media_kind,
                        "latency_ms": result.latency_ms,
                    }
                )
                self._append(store, completed)
        return self.snapshot()


__all__ = [
    "LocalGenerationExecutionPort", "LocalGenerationExecutionPortSelector", "LocalGenerationExecutionRequest",
    "LocalGenerationExecutionResult", "LocalGenerationRuntimeReadiness",
    "Task013CreativeGenerationExecutionApplication",
]
