"""TASK-027 adoption of a completed local generation output.

This application closes the Product lineage gap between TASK-013 execution
Evidence and the existing TASK-003/037/040 registries.  It never dispatches a
Provider and never makes a Human audit, ACCEPT, LOCK, publish, NLE or release
decision.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib import resources
import json
from pathlib import Path, PurePosixPath
import re
import secrets
from typing import Any, Callable, Mapping

from .assets import (
    AssetType,
    AudioRightsStatus,
    PermissionState,
    RetentionClass,
    RightsStatus,
)
from .atomic import AtomicJsonWriter, exclusive_file_update_lock
from .errors import ProductError, ProductErrorCategory
from .ingest import AssetIngestRequest, AssetIngestService
from .serialization import canonical_json_bytes, sha256_bytes
from .schema_contracts import validate_instance


TokenFactory = Callable[[], str]
_STORE_NAME = "generation-output-adoptions.json"
_MAX_BYTES = 8 * 1024 * 1024
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_OUTPUT_REF_RE = re.compile(r"project-output://[A-Za-z0-9][A-Za-z0-9._/-]{0,499}")
_STATES = (
    "PREPARED",
    "ASSET_REGISTERED",
    "CANDIDATE_REGISTERED",
    "ATTEMPT_BOUND",
    "READY_FOR_AUDIT",
    "FAILED_KNOWN",
)
_TERMINAL_STATES = {"READY_FOR_AUDIT", "FAILED_KNOWN"}
_MEDIA_ASSET_TYPES = {
    "IMAGE": AssetType.IMAGE,
    "VIDEO": AssetType.GENERATED_VIDEO,
    "AUDIO": AssetType.AUDIO,
}


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _with_hash(value: Mapping[str, Any]) -> dict[str, Any]:
    body = {key: item for key, item in value.items() if key != "adoption_snapshot_sha256"}
    body["adoption_snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


@dataclass(frozen=True, slots=True)
class AdoptedAssetIdentity:
    asset_id: str
    asset_sha256: str


@dataclass(slots=True)
class Task027GeneratedOutputAssetPort:
    """Resolve one private Product output and ingest it through TASK-003."""

    service: AssetIngestService
    project_output_root: Path
    production_job_id: str
    owner: str
    max_output_bytes: int = 16 * 1024 * 1024 * 1024

    def __post_init__(self) -> None:
        root = self.project_output_root
        if root.is_symlink() or not root.is_dir():
            raise ProductError(
                "ERR_OUTPUT_ADOPTION_ROOT_INVALID",
                "Generated-output root must be an existing non-symlink directory",
                ProductErrorCategory.SECURITY,
            )
        self.project_output_root = root.resolve(strict=True)
        if isinstance(self.max_output_bytes, bool) or not isinstance(self.max_output_bytes, int) or self.max_output_bytes <= 0:
            raise ProductError(
                "ERR_OUTPUT_ADOPTION_SIZE_POLICY_INVALID",
                "Generated-output size policy must be a positive integer",
                ProductErrorCategory.VALIDATION,
            )

    def _resolve(self, output_ref: str) -> Path:
        if not isinstance(output_ref, str) or not _OUTPUT_REF_RE.fullmatch(output_ref):
            raise ProductError(
                "ERR_OUTPUT_ADOPTION_REF_INVALID",
                "Completed output must use a safe project-output:// reference",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        relative = PurePosixPath(output_ref.removeprefix("project-output://"))
        if any(part in {"", ".", ".."} for part in relative.parts):
            raise ProductError(
                "ERR_OUTPUT_ADOPTION_REF_INVALID",
                "Completed output reference contains an unsafe segment",
                ProductErrorCategory.SECURITY,
            )
        candidate = self.project_output_root.joinpath(*relative.parts)
        cursor = self.project_output_root
        for part in relative.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise ProductError(
                    "ERR_OUTPUT_ADOPTION_SYMLINK",
                    "Generated output must not traverse a symlink",
                    ProductErrorCategory.SECURITY,
                )
        if not candidate.is_file():
            raise ProductError(
                "ERR_OUTPUT_ADOPTION_FILE_MISSING",
                "Completed generated output is missing or is not a regular file",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if candidate.stat().st_size <= 0 or candidate.stat().st_size > self.max_output_bytes:
            raise ProductError(
                "ERR_OUTPUT_ADOPTION_FILE_SIZE",
                "Completed generated output is outside the configured size bound",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        resolved = candidate.resolve(strict=True)
        try:
            resolved.relative_to(self.project_output_root)
        except ValueError as exc:
            raise ProductError(
                "ERR_OUTPUT_ADOPTION_CONTAINMENT",
                "Generated output escaped the configured Product output root",
                ProductErrorCategory.SECURITY,
            ) from exc
        return resolved

    def adopt(self, event: Mapping[str, Any]) -> AdoptedAssetIdentity:
        media_kind = event.get("media_kind")
        if media_kind not in _MEDIA_ASSET_TYPES:
            raise ProductError(
                "ERR_OUTPUT_ADOPTION_MEDIA_KIND",
                "Completed generated output has an unsupported media kind",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        source = self._resolve(event.get("output_ref"))
        actual_sha256 = _file_sha256(source)
        if actual_sha256 != event.get("output_sha256"):
            raise ProductError(
                "ERR_OUTPUT_ADOPTION_CHECKSUM_MISMATCH",
                "Generated output bytes do not match completed execution Evidence",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        audio_rights = AudioRightsStatus.REVIEW if media_kind == "AUDIO" else AudioRightsStatus.NOT_APPLICABLE
        result = self.service.ingest(
            AssetIngestRequest(
                production_job_id=self.production_job_id,
                source_path=source,
                asset_type=_MEDIA_ASSET_TYPES[media_kind],
                rights_status=RightsStatus.UNKNOWN,
                owner=self.owner,
                idempotency_key=f"task027-output-adoption-{event['execution_id']}-{actual_sha256[7:31]}",
                retention_class=RetentionClass.STANDARD,
                commercial_use=PermissionState.UNKNOWN,
                derivative_allowed=PermissionState.UNKNOWN,
                reuse_allowed=PermissionState.UNKNOWN,
                audio_rights_status=audio_rights,
                source_ref=event["output_ref"],
                source_project=event["project_id"],
                publication_restrictions=(
                    "HUMAN_RIGHTS_REVIEW_REQUIRED",
                    "PUBLICATION_NOT_AUTHORIZED",
                ),
                generation_provenance={
                    "kind": "TASK013_COMPLETED_LOCAL_GENERATION",
                    "execution_id": event["execution_id"],
                    "queue_entry_id": event["queue_entry_id"],
                    "prompt_id": event["prompt_id"],
                    "prompt_version": event["prompt_version"],
                    "prompt_sha256": event["prompt_sha256"],
                    "provider_id": event["provider_id"],
                    "model_id": event["model_id"],
                    "provider_operation_id": event["provider_operation_id"],
                    "output_sha256": actual_sha256,
                    "provider_execution_replayed": False,
                    "paid_execution_authorized": False,
                },
            )
        )
        if result.asset.checksum != actual_sha256:
            raise ProductError(
                "ERR_OUTPUT_ADOPTION_ASSET_CHECKSUM_MISMATCH",
                "Canonical Asset checksum differs from completed output Evidence",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return AdoptedAssetIdentity(result.asset.asset_id, result.asset.checksum)

    def verify(self, event: Mapping[str, Any], asset_id: str) -> AdoptedAssetIdentity:
        """Revalidate bytes and canonical TASK-003 identity without a new ingest."""
        source = self._resolve(event.get("output_ref"))
        actual_sha256 = _file_sha256(source)
        if actual_sha256 != event.get("output_sha256"):
            raise ProductError(
                "ERR_OUTPUT_ADOPTION_CHECKSUM_MISMATCH",
                "Generated output bytes changed after Asset registration",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        asset = self.service.store.get_asset(asset_id)
        expected_type = _MEDIA_ASSET_TYPES.get(event.get("media_kind"))
        provenance = asset.generation_provenance
        if (
            expected_type is None
            or asset.asset_type is not expected_type
            or asset.checksum != actual_sha256
            or asset.source_ref != event.get("output_ref")
            or asset.rights_status is not RightsStatus.UNKNOWN
            or "PUBLICATION_NOT_AUTHORIZED" not in asset.publication_restrictions
            or provenance.get("kind") != "TASK013_COMPLETED_LOCAL_GENERATION"
            or provenance.get("execution_id") != event.get("execution_id")
            or provenance.get("queue_entry_id") != event.get("queue_entry_id")
            or provenance.get("output_sha256") != actual_sha256
        ):
            raise ProductError(
                "ERR_OUTPUT_ADOPTION_ASSET_IDENTITY_DRIFT",
                "Canonical Asset no longer matches the active output adoption",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return AdoptedAssetIdentity(asset.asset_id, asset.checksum)


@dataclass(slots=True)
class _PendingAdoption:
    confirmation_id: str
    event: dict[str, Any]
    queue_entry: dict[str, Any]
    candidate_id: str
    execution_snapshot_sha256: str
    queue_snapshot_sha256: str
    production_snapshot_sha256: str
    prompt_snapshot_sha256: str
    adoption_snapshot_sha256: str
    consumed: bool = False


class Task027GenerationOutputAdoptionApplication:
    """Checksum-closed, restart-safe promotion to Human audit candidacy."""

    def __init__(
        self,
        *,
        project_root: str | Path,
        project_id: str,
        generation_execution: Any,
        generation_queue: Any,
        production_control: Any,
        prompt_evidence: Any,
        asset_port: Task027GeneratedOutputAssetPort,
        token_factory: TokenFactory | None = None,
    ) -> None:
        root = Path(project_root)
        if root.is_symlink() or not root.is_dir():
            raise ProductError(
                "ERR_OUTPUT_ADOPTION_PROJECT_ROOT_INVALID",
                "Output-adoption project root must be an existing non-symlink directory",
                ProductErrorCategory.VALIDATION,
            )
        if not isinstance(project_id, str) or not project_id.strip():
            raise ProductError(
                "ERR_OUTPUT_ADOPTION_PROJECT_ID_INVALID",
                "Output-adoption project_id must be non-empty text",
                ProductErrorCategory.VALIDATION,
            )
        self.project_root = root
        self.project_id = project_id
        self.snapshot_path = root / _STORE_NAME
        self.generation_execution = generation_execution
        self.generation_queue = generation_queue
        self.production_control = production_control
        self.prompt_evidence = prompt_evidence
        self.asset_port = asset_port
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._confirmations: dict[str, _PendingAdoption] = {}

    def _empty(self) -> dict[str, Any]:
        return _with_hash({
            "adoption_version": "1.0.0",
            "task_owner": "TASK-027",
            "project_id": self.project_id,
            "revision": 0,
            "records": [],
            "provider_execution_started": False,
            "provider_execution_replayed": False,
            "paid_execution_authorized": False,
            "human_audit_decision_created": False,
            "candidate_accepted": False,
            "candidate_locked": False,
            "publication_authorized": False,
            "nle_mutation_started": False,
        })

    def _validate(self, value: Any) -> None:
        schema = json.loads(
            resources.files("ai_video_production")
            .joinpath("schema_resources", "generation-output-adoption.schema.json")
            .read_text(encoding="utf-8")
        )
        validate_instance(value, schema)
        if not isinstance(value, dict) or value.get("adoption_version") != "1.0.0":
            raise ProductError("ERR_OUTPUT_ADOPTION_SNAPSHOT_INVALID", "Output-adoption snapshot identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
        if value.get("task_owner") != "TASK-027" or value.get("project_id") != self.project_id:
            raise ProductError("ERR_OUTPUT_ADOPTION_SNAPSHOT_SCOPE", "Output-adoption snapshot is outside this Project", ProductErrorCategory.DATA_INTEGRITY)
        if value.get("adoption_snapshot_sha256") != _with_hash(value)["adoption_snapshot_sha256"]:
            raise ProductError("ERR_OUTPUT_ADOPTION_SNAPSHOT_CHECKSUM", "Output-adoption snapshot checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
        flags = (
            "provider_execution_started", "provider_execution_replayed", "paid_execution_authorized",
            "human_audit_decision_created", "candidate_accepted", "candidate_locked",
            "publication_authorized", "nle_mutation_started",
        )
        if any(value.get(name) is not False for name in flags):
            raise ProductError("ERR_OUTPUT_ADOPTION_AUTHORITY_BOUNDARY", "Output-adoption snapshot claims prohibited authority", ProductErrorCategory.SECURITY)
        records = value.get("records")
        revision = value.get("revision")
        if isinstance(revision, bool) or not isinstance(revision, int) or not isinstance(records, list) or revision != len(records):
            raise ProductError("ERR_OUTPUT_ADOPTION_REVISION", "Output-adoption history revision is invalid", ProductErrorCategory.DATA_INTEGRITY)
        latest: dict[str, str] = {}
        identities: dict[str, tuple[Any, ...]] = {}
        asset_ids: dict[str, str | None] = {}
        for index, record in enumerate(records, 1):
            if not isinstance(record, dict) or record.get("record_revision") != index:
                raise ProductError("ERR_OUTPUT_ADOPTION_RECORD", "Output-adoption record revision is invalid", ProductErrorCategory.DATA_INTEGRITY)
            for name in ("adoption_id", "execution_id", "queue_entry_id", "slot_id", "prompt_id", "candidate_id"):
                if not isinstance(record.get(name), str) or not _ID_RE.fullmatch(record[name]):
                    raise ProductError("ERR_OUTPUT_ADOPTION_RECORD", "Output-adoption identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
            if record.get("state") not in _STATES or not _SHA_RE.fullmatch(record.get("output_sha256", "")):
                raise ProductError("ERR_OUTPUT_ADOPTION_RECORD", "Output-adoption state/checksum is invalid", ProductErrorCategory.DATA_INTEGRITY)
            if not _OUTPUT_REF_RE.fullmatch(record.get("output_ref", "")) or not _SHA_RE.fullmatch(record.get("execution_event_sha256", "")):
                raise ProductError("ERR_OUTPUT_ADOPTION_RECORD", "Output-adoption output/execution binding is invalid", ProductErrorCategory.DATA_INTEGRITY)
            if record.get("asset_id") is not None and not _ID_RE.fullmatch(record["asset_id"]):
                raise ProductError("ERR_OUTPUT_ADOPTION_RECORD", "Output-adoption Asset identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
            previous = latest.get(record["adoption_id"])
            state = record["state"]
            identity = tuple(record[name] for name in (
                "execution_id", "queue_entry_id", "slot_id", "prompt_id",
                "prompt_version", "output_ref", "output_sha256",
                "execution_event_sha256", "media_kind", "candidate_id",
            ))
            if record["adoption_id"] in identities and identities[record["adoption_id"]] != identity:
                raise ProductError("ERR_OUTPUT_ADOPTION_IDENTITY_DRIFT", "Output-adoption identity changed between records", ProductErrorCategory.DATA_INTEGRITY)
            identities[record["adoption_id"]] = identity
            previous_asset = asset_ids.get(record["adoption_id"])
            current_asset = record.get("asset_id")
            if previous_asset is not None and current_asset != previous_asset:
                raise ProductError("ERR_OUTPUT_ADOPTION_ASSET_IDENTITY_DRIFT", "Output-adoption Asset changed between records", ProductErrorCategory.DATA_INTEGRITY)
            if current_asset is not None:
                asset_ids[record["adoption_id"]] = current_asset
            if previous is None and state not in {"PREPARED", "FAILED_KNOWN"}:
                raise ProductError("ERR_OUTPUT_ADOPTION_TRANSITION", "Output adoption must begin at PREPARED", ProductErrorCategory.DATA_INTEGRITY)
            if previous is not None:
                allowed = {
                    "PREPARED": {"ASSET_REGISTERED", "FAILED_KNOWN"},
                    "ASSET_REGISTERED": {"CANDIDATE_REGISTERED"},
                    "CANDIDATE_REGISTERED": {"ATTEMPT_BOUND"},
                    "ATTEMPT_BOUND": {"READY_FOR_AUDIT"},
                }.get(previous, set())
                if state not in allowed:
                    raise ProductError("ERR_OUTPUT_ADOPTION_TRANSITION", "Output-adoption state transition is invalid", ProductErrorCategory.DATA_INTEGRITY)
            latest[record["adoption_id"]] = state

    def _load(self) -> dict[str, Any]:
        target = self.snapshot_path
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ProductError("ERR_OUTPUT_ADOPTION_SNAPSHOT_FILE", "Output-adoption snapshot must be a regular non-symlink file", ProductErrorCategory.SECURITY)
        if not target.exists():
            return self._empty()
        if not 0 < target.stat().st_size <= _MAX_BYTES:
            raise ProductError("ERR_OUTPUT_ADOPTION_SNAPSHOT_SIZE", "Output-adoption snapshot size is invalid", ProductErrorCategory.DATA_INTEGRITY)
        try:
            value = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_OUTPUT_ADOPTION_SNAPSHOT_READ", "Output-adoption snapshot is unreadable", ProductErrorCategory.DATA_INTEGRITY) from exc
        self._validate(value)
        return value

    def _save(self, store: dict[str, Any]) -> dict[str, Any]:
        document = _with_hash(store)
        AtomicJsonWriter.write(self.snapshot_path, document, validator=self._validate)
        return document

    @staticmethod
    def _latest_by_adoption(store: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        for record in store["records"]:
            latest[record["adoption_id"]] = record
        return latest

    @staticmethod
    def _candidate(production: Mapping[str, Any], candidate_id: str) -> dict[str, Any] | None:
        for slot in production.get("slots", []):
            for candidate in slot.get("candidates", []):
                if candidate.get("candidate_id") == candidate_id:
                    return candidate
        return None

    @staticmethod
    def _attempt(prompt: Mapping[str, Any], generation_job_id: str) -> dict[str, Any] | None:
        for entity in prompt.get("prompts", []):
            for attempt in entity.get("attempts", []):
                if attempt.get("generation_job_id") == generation_job_id:
                    return attempt
        return None

    @staticmethod
    def _require_equal(actual: Any, expected: Any, code: str, message: str) -> None:
        if actual != expected:
            raise ProductError(code, message, ProductErrorCategory.STATE)

    def _sources(
        self,
        execution_id: str,
        *,
        allow_prompt_recovery: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        execution = self.generation_execution.snapshot()
        queue = self.generation_queue.snapshot()
        production = self.production_control.snapshot()
        prompt = self.prompt_evidence.snapshot()
        event = next((item for item in execution.get("latest_executions", []) if item.get("execution_id") == execution_id), None)
        if event is None or event.get("state") != "COMPLETED":
            raise ProductError("ERR_OUTPUT_ADOPTION_EXECUTION_NOT_COMPLETED", "Only an exact completed execution may be adopted", ProductErrorCategory.STATE)
        if event.get("project_id") != self.project_id:
            raise ProductError("ERR_OUTPUT_ADOPTION_PROJECT_MISMATCH", "Completed execution belongs to another Project", ProductErrorCategory.DATA_INTEGRITY)
        entry = next((item for item in queue.get("entries", []) if item.get("queue_entry_id") == event.get("queue_entry_id")), None)
        if entry is None:
            raise ProductError("ERR_OUTPUT_ADOPTION_QUEUE_ENTRY_MISSING", "Completed execution has no canonical Queue entry", ProductErrorCategory.DATA_INTEGRITY)
        for name in ("slot_id", "prompt_id", "prompt_version", "prompt_sha256"):
            if entry.get(name) != event.get(name):
                raise ProductError("ERR_OUTPUT_ADOPTION_QUEUE_IDENTITY_DRIFT", "Execution and Queue identities differ", ProductErrorCategory.DATA_INTEGRITY)
        if execution.get("queue_snapshot_sha256") not in {None, queue.get("queue_snapshot_sha256")}:
            raise ProductError("ERR_OUTPUT_ADOPTION_QUEUE_SNAPSHOT_DRIFT", "Execution is not bound to the current Queue snapshot", ProductErrorCategory.DATA_INTEGRITY)
        if prompt.get("production_snapshot_sha256") != production.get("snapshot_sha256"):
            raise ProductError("ERR_OUTPUT_ADOPTION_CROSS_STORE_DRIFT", "Prompt and Production snapshots are not synchronized", ProductErrorCategory.DATA_INTEGRITY)
        lineage = self._execution_lineage(entry)
        prompt_row = next((
            item for item in prompt.get("prompts", [])
            if item.get("prompt_id") == event.get("prompt_id")
            and item.get("prompt_version") == event.get("prompt_version")
        ), None)
        if prompt_row is None:
            raise ProductError("ERR_OUTPUT_ADOPTION_PROMPT_MISSING", "Completed execution Prompt is missing from canonical Evidence", ProductErrorCategory.DATA_INTEGRITY)
        self._require_prompt_lineage(prompt_row, event, lineage)
        if execution.get("recovery", {}).get("required") or (
            prompt.get("recovery", {}).get("required") and not allow_prompt_recovery
        ):
            raise ProductError("ERR_OUTPUT_ADOPTION_DEPENDENCY_RECOVERY_REQUIRED", "Complete exact dependency recovery before adopting another output", ProductErrorCategory.STATE)
        return execution, queue, production, prompt, entry

    @staticmethod
    def _execution_lineage(entry: Mapping[str, Any]) -> dict[str, Any]:
        prompt_version = entry.get("prompt_version")
        lineage = entry.get("execution_lineage")
        if isinstance(prompt_version, bool) or not isinstance(prompt_version, int) or prompt_version < 1:
            raise ProductError("ERR_OUTPUT_ADOPTION_REGENERATION_BINDING_INVALID", "Queue Prompt version is invalid", ProductErrorCategory.DATA_INTEGRITY)
        if prompt_version == 1 and lineage is None:
            return {
                "lineage_version": "1.0.0", "kind": "INITIAL", "strategy_level": 0,
                "parent_attempt_id": None, "regeneration_plan_sha256": None,
            }
        expected_fields = {
            "lineage_version", "kind", "strategy_level", "parent_attempt_id",
            "regeneration_plan_sha256",
        }
        if not isinstance(lineage, dict) or set(lineage) != expected_fields:
            raise ProductError(
                "ERR_OUTPUT_ADOPTION_REGENERATION_STRATEGY_UNBOUND",
                "Regenerated Prompt output lacks an exact persisted strategy/parent binding",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={"prompt_id": entry.get("prompt_id"), "prompt_version": prompt_version},
            )
        strategy = lineage.get("strategy_level")
        if (
            lineage.get("lineage_version") != "1.0.0"
            or isinstance(strategy, bool)
            or not isinstance(strategy, int)
            or strategy not in range(7)
        ):
            raise ProductError("ERR_OUTPUT_ADOPTION_REGENERATION_BINDING_INVALID", "Queue execution lineage is invalid", ProductErrorCategory.DATA_INTEGRITY)
        if prompt_version == 1:
            if lineage != {
                "lineage_version": "1.0.0", "kind": "INITIAL", "strategy_level": 0,
                "parent_attempt_id": None, "regeneration_plan_sha256": None,
            }:
                raise ProductError("ERR_OUTPUT_ADOPTION_REGENERATION_BINDING_INVALID", "Initial Queue lineage is invalid", ProductErrorCategory.DATA_INTEGRITY)
        elif (
            not isinstance(prompt_version, int)
            or prompt_version < 2
            or lineage.get("kind") != "REGENERATION"
            or not isinstance(lineage.get("parent_attempt_id"), str)
            or not _ID_RE.fullmatch(lineage["parent_attempt_id"])
            or not isinstance(lineage.get("regeneration_plan_sha256"), str)
            or not _SHA_RE.fullmatch(lineage["regeneration_plan_sha256"])
        ):
            raise ProductError("ERR_OUTPUT_ADOPTION_REGENERATION_BINDING_INVALID", "Regenerated Queue lineage is invalid", ProductErrorCategory.DATA_INTEGRITY)
        return dict(lineage)

    @staticmethod
    def _require_prompt_lineage(
        prompt_row: Mapping[str, Any],
        event: Mapping[str, Any],
        lineage: Mapping[str, Any],
    ) -> None:
        if event.get("prompt_version") == 1:
            if prompt_row.get("regeneration_binding") is not None or lineage.get("kind") != "INITIAL":
                raise ProductError("ERR_OUTPUT_ADOPTION_REGENERATION_BINDING_DRIFT", "Initial Prompt carries incompatible regeneration lineage", ProductErrorCategory.DATA_INTEGRITY)
            return
        binding = prompt_row.get("regeneration_binding")
        expected = None if not isinstance(binding, dict) else {
            "lineage_version": "1.0.0", "kind": "REGENERATION",
            "strategy_level": binding.get("strategy_level"),
            "parent_attempt_id": binding.get("parent_attempt_id"),
            "regeneration_plan_sha256": binding.get("regeneration_plan_sha256"),
        }
        if (
            not isinstance(binding, dict)
            or binding.get("binding_version") != "1.0.0"
            or binding.get("parent_prompt_id") != event.get("prompt_id")
            or binding.get("parent_prompt_version") != event.get("prompt_version") - 1
            or expected != lineage
        ):
            raise ProductError("ERR_OUTPUT_ADOPTION_REGENERATION_BINDING_DRIFT", "Queue and Prompt regeneration lineage differ", ProductErrorCategory.DATA_INTEGRITY)

    def snapshot(self) -> dict[str, Any]:
        store = self._load()
        latest = self._latest_by_adoption(store)
        active = [item for item in latest.values() if item["state"] not in _TERMINAL_STATES]
        execution = self.generation_execution.snapshot()
        adopted_execution_ids = {item["execution_id"] for item in latest.values()}
        eligible = []
        queue_entries = {
            item.get("queue_entry_id"): item
            for item in self.generation_queue.snapshot().get("entries", [])
        }
        prompt_rows = {
            (item.get("prompt_id"), item.get("prompt_version")): item
            for item in self.prompt_evidence.snapshot().get("prompts", [])
        }
        for item in execution.get("latest_executions", []):
            if item.get("state") != "COMPLETED" or item.get("execution_id") in adopted_execution_ids:
                continue
            status = "READY"
            try:
                lineage = self._execution_lineage(queue_entries.get(item.get("queue_entry_id"), {}))
                prompt_row = prompt_rows.get((item.get("prompt_id"), item.get("prompt_version")))
                if prompt_row is None:
                    raise ProductError("ERR_OUTPUT_ADOPTION_PROMPT_MISSING", "Prompt is missing", ProductErrorCategory.DATA_INTEGRITY)
                self._require_prompt_lineage(prompt_row, item, lineage)
            except ProductError:
                status = "PARKED_STRATEGY_BINDING_REQUIRED"
            eligible.append({
                "execution_id": item["execution_id"],
                "queue_entry_id": item["queue_entry_id"],
                "slot_id": item["slot_id"],
                "prompt_id": item["prompt_id"],
                "prompt_version": item["prompt_version"],
                "output_sha256": item["output_sha256"],
                "media_kind": item["media_kind"],
                "adoption_status": status,
            })
        return {
            **store,
            "latest_adoptions": list(latest.values()),
            "eligible_completed_outputs": eligible,
            "recovery": {
                "required": bool(active),
                "active": active,
                "automatic_provider_retry_allowed": False,
            },
            "action_label": "検証して監査候補へ登録",
        }

    def prepare_adoption(
        self,
        *,
        execution_id: str,
        expected_execution_snapshot_sha256: str,
        expected_queue_snapshot_sha256: str,
        expected_production_snapshot_sha256: str,
        expected_prompt_snapshot_sha256: str,
        expected_adoption_snapshot_sha256: str,
    ) -> dict[str, Any]:
        store = self._load()
        if store["adoption_snapshot_sha256"] != expected_adoption_snapshot_sha256:
            raise ProductError("ERR_OUTPUT_ADOPTION_SNAPSHOT_CONFLICT", "Output-adoption state changed; reload before confirming", ProductErrorCategory.STATE)
        if any(item["state"] not in _TERMINAL_STATES for item in self._latest_by_adoption(store).values()):
            raise ProductError("ERR_OUTPUT_ADOPTION_RECOVERY_REQUIRED", "Complete the interrupted output adoption first", ProductErrorCategory.STATE)
        execution, queue, production, prompt, entry = self._sources(execution_id)
        self._require_equal(execution["execution_snapshot_sha256"], expected_execution_snapshot_sha256, "ERR_OUTPUT_ADOPTION_EXECUTION_CONFLICT", "Execution state changed; reload before confirming")
        self._require_equal(queue["queue_snapshot_sha256"], expected_queue_snapshot_sha256, "ERR_OUTPUT_ADOPTION_QUEUE_CONFLICT", "Queue state changed; reload before confirming")
        self._require_equal(production["snapshot_sha256"], expected_production_snapshot_sha256, "ERR_OUTPUT_ADOPTION_PRODUCTION_CONFLICT", "Production state changed; reload before confirming")
        self._require_equal(prompt["prompt_snapshot_sha256"], expected_prompt_snapshot_sha256, "ERR_OUTPUT_ADOPTION_PROMPT_CONFLICT", "Prompt state changed; reload before confirming")
        event = next(item for item in execution["latest_executions"] if item["execution_id"] == execution_id)
        if any(item.get("execution_id") == execution_id for item in self._latest_by_adoption(store).values()):
            raise ProductError("ERR_OUTPUT_ADOPTION_ALREADY_RECORDED", "This completed execution already has an adoption record", ProductErrorCategory.STATE)
        seed = {
            "project_id": self.project_id,
            "execution_id": execution_id,
            "queue_entry_id": event["queue_entry_id"],
            "output_sha256": event["output_sha256"],
            "execution_lineage": self._execution_lineage(entry),
        }
        suffix = sha256_bytes(canonical_json_bytes(seed))[7:31]
        candidate_id = f"candidate-{suffix}"
        token = self._token_factory()
        if not isinstance(token, str) or not token.strip() or token in self._confirmations:
            raise ProductError("ERR_OUTPUT_ADOPTION_CONFIRMATION_TOKEN", "Output-adoption confirmation token is invalid", ProductErrorCategory.INTERNAL)
        self._confirmations[token] = _PendingAdoption(
            token, dict(event), dict(entry), candidate_id,
            execution["execution_snapshot_sha256"], queue["queue_snapshot_sha256"],
            production["snapshot_sha256"], prompt["prompt_snapshot_sha256"],
            store["adoption_snapshot_sha256"],
        )
        return {
            "confirmation_id": token,
            "action_label": "検証して監査候補へ登録",
            "execution_id": execution_id,
            "slot_id": event["slot_id"],
            "candidate_id": candidate_id,
            "output_sha256": event["output_sha256"],
            "execution_lineage": self._execution_lineage(entry),
            "human_final_confirmation_required": True,
            "provider_execution_started": False,
            "provider_execution_replayed": False,
            "paid_execution_authorized": False,
            "human_audit_decision_created": False,
            "candidate_accepted": False,
            "candidate_locked": False,
            "publication_authorized": False,
            "nle_mutation_started": False,
        }

    def _append(self, store: dict[str, Any], base: Mapping[str, Any], state: str, *, asset_id: str | None, failure_code: str | None = None) -> dict[str, Any]:
        store["revision"] += 1
        record = {
            **base,
            "record_revision": store["revision"],
            "state": state,
            "asset_id": asset_id,
            "failure_code": failure_code,
        }
        store["records"].append(record)
        self._save(store)
        return record

    @staticmethod
    def _base(event: Mapping[str, Any], candidate_id: str) -> dict[str, Any]:
        seed = {
            "project_id": event["project_id"], "execution_id": event["execution_id"],
            "queue_entry_id": event["queue_entry_id"], "output_sha256": event["output_sha256"],
        }
        return {
            "adoption_id": "adoption-" + sha256_bytes(canonical_json_bytes(seed))[7:31],
            "execution_id": event["execution_id"], "queue_entry_id": event["queue_entry_id"],
            "slot_id": event["slot_id"], "prompt_id": event["prompt_id"],
            "prompt_version": event["prompt_version"], "output_ref": event["output_ref"],
            "output_sha256": event["output_sha256"],
            "execution_event_sha256": sha256_bytes(canonical_json_bytes(event)),
            "media_kind": event["media_kind"], "candidate_id": candidate_id,
        }

    @staticmethod
    def _require_candidate_exact(candidate: Mapping[str, Any], *, base: Mapping[str, Any], asset: AdoptedAssetIdentity) -> None:
        expected = {
            "candidate_id": base["candidate_id"], "slot_id": base["slot_id"],
            "asset_id": asset.asset_id, "asset_sha256": asset.asset_sha256,
            "generation_job_id": base["execution_id"], "parent_candidate_id": None, "supersedes": None,
        }
        if any(candidate.get(name) != value for name, value in expected.items()):
            raise ProductError("ERR_OUTPUT_ADOPTION_CANDIDATE_CONFLICT", "Deterministic Candidate identity conflicts with Product state", ProductErrorCategory.DATA_INTEGRITY)

    @staticmethod
    def _require_attempt_exact(
        attempt: Mapping[str, Any],
        *,
        event: Mapping[str, Any],
        base: Mapping[str, Any],
        lineage: Mapping[str, Any],
    ) -> None:
        expected = {
            "generation_job_id": event["execution_id"], "slot_id": event["slot_id"],
            "prompt_id": event["prompt_id"], "prompt_version": event["prompt_version"],
            "prompt_sha256": event["prompt_sha256"], "provider_id": event["provider_id"],
            "model_id": event["model_id"], "strategy_level": lineage["strategy_level"], "result": "PASS",
            "failure_codes": [], "output_candidate_id": base["candidate_id"],
            "parent_attempt_id": lineage["parent_attempt_id"], "cost": None, "latency_ms": event.get("latency_ms"),
        }
        if any(attempt.get(name) != value for name, value in expected.items()):
            raise ProductError("ERR_OUTPUT_ADOPTION_ATTEMPT_CONFLICT", "Generation Attempt identity conflicts with completed execution", ProductErrorCategory.DATA_INTEGRITY)

    def _continue(self, store: dict[str, Any], latest: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        base = {key: latest[key] for key in (
            "adoption_id", "execution_id", "queue_entry_id", "slot_id", "prompt_id",
            "prompt_version", "output_ref", "output_sha256",
            "execution_event_sha256", "media_kind", "candidate_id",
        )}
        state = latest["state"]
        asset_id = latest.get("asset_id")
        asset_just_registered = False
        queue = self.generation_queue.snapshot()
        entry = next((item for item in queue.get("entries", []) if item.get("queue_entry_id") == event["queue_entry_id"]), None)
        if entry is None:
            raise ProductError("ERR_OUTPUT_ADOPTION_QUEUE_ENTRY_MISSING", "Active adoption Queue entry disappeared", ProductErrorCategory.DATA_INTEGRITY)
        lineage = self._execution_lineage(entry)

        if state == "PREPARED":
            try:
                asset = self.asset_port.adopt(event)
            except ProductError as exc:
                self._append(store, base, "FAILED_KNOWN", asset_id=None, failure_code=exc.code)
                raise
            latest = self._append(store, base, "ASSET_REGISTERED", asset_id=asset.asset_id)
            state, asset_id = latest["state"], latest["asset_id"]
            asset_just_registered = True
        asset = AdoptedAssetIdentity(asset_id, base["output_sha256"])
        if not asset_just_registered:
            asset = self.asset_port.verify(event, asset.asset_id)

        if state == "ASSET_REGISTERED":
            production = self.production_control.snapshot()
            candidate = self._candidate(production, base["candidate_id"])
            if candidate is None:
                result = self.production_control.register_candidate(
                    candidate_id=base["candidate_id"], slot_id=base["slot_id"],
                    asset_id=asset.asset_id, asset_sha256=asset.asset_sha256,
                    generation_job_id=base["execution_id"], parent_candidate_id=None,
                    supersedes=None, expected_snapshot_sha256=production["snapshot_sha256"],
                )
                candidate = result["candidate"]
            self._require_candidate_exact(candidate, base=base, asset=asset)
            latest = self._append(store, base, "CANDIDATE_REGISTERED", asset_id=asset.asset_id)
            state = latest["state"]

        if state == "CANDIDATE_REGISTERED":
            prompt = self.prompt_evidence.snapshot()
            recovery = prompt.get("recovery", {})
            if recovery.get("required"):
                actions = recovery.get("available_actions", [])
                if len(actions) != 1 or actions[0] not in {"COMPLETE", "FINALIZE"}:
                    raise ProductError("ERR_OUTPUT_ADOPTION_PROMPT_RECOVERY_AMBIGUOUS", "Prompt recovery is not an exact continuable suffix", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
                self.prompt_evidence.apply_recovery(action=actions[0])
                prompt = self.prompt_evidence.snapshot()
            attempt = self._attempt(prompt, base["execution_id"])
            if attempt is None:
                prepared = self.prompt_evidence.prepare_attempt(
                    generation_job_id=event["execution_id"], slot_id=event["slot_id"],
                    prompt_id=event["prompt_id"], prompt_version=event["prompt_version"],
                    provider_id=event["provider_id"], model_id=event["model_id"],
                    strategy_level=lineage["strategy_level"], result="PASS", failure_codes=(),
                    output_candidate_id=base["candidate_id"], parent_attempt_id=lineage["parent_attempt_id"],
                    cost=None, latency_ms=event.get("latency_ms"),
                    expected_prompt_snapshot_sha256=prompt["prompt_snapshot_sha256"],
                    expected_production_snapshot_sha256=prompt["production_snapshot_sha256"],
                )
                self.prompt_evidence.apply_attempt(confirmation_id=prepared["confirmation_id"])
                prompt = self.prompt_evidence.snapshot()
                attempt = self._attempt(prompt, base["execution_id"])
            if attempt is None:
                raise ProductError("ERR_OUTPUT_ADOPTION_ATTEMPT_MISSING", "PASS Attempt did not become durable", ProductErrorCategory.DATA_INTEGRITY)
            self._require_attempt_exact(attempt, event=event, base=base, lineage=lineage)
            latest = self._append(store, base, "ATTEMPT_BOUND", asset_id=asset.asset_id)
            state = latest["state"]

        if state == "ATTEMPT_BOUND":
            production = self.production_control.snapshot()
            candidate = self._candidate(production, base["candidate_id"])
            if candidate is None:
                raise ProductError("ERR_OUTPUT_ADOPTION_CANDIDATE_MISSING", "Output Candidate disappeared before audit readiness", ProductErrorCategory.DATA_INTEGRITY)
            self._require_candidate_exact(candidate, base=base, asset=asset)
            lifecycle = candidate.get("lifecycle_state")
            if lifecycle == "CREATED":
                result = self.production_control.mark_ready_for_audit(
                    candidate_id=base["candidate_id"],
                    expected_snapshot_sha256=production["snapshot_sha256"],
                )
                candidate = result["candidate"]
            if candidate.get("lifecycle_state") != "READY_FOR_AUDIT":
                raise ProductError("ERR_OUTPUT_ADOPTION_CANDIDATE_STATE_CONFLICT", "Candidate is outside the exact audit-readiness transition", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
            self._append(store, base, "READY_FOR_AUDIT", asset_id=asset.asset_id)
        return self.snapshot()

    def apply_adoption(self, *, confirmation_id: str) -> dict[str, Any]:
        pending = self._confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError("ERR_OUTPUT_ADOPTION_CONFIRMATION_INVALID", "Output-adoption confirmation is missing or already used", ProductErrorCategory.AUTHORIZATION)
        pending.consumed = True
        with exclusive_file_update_lock(self.snapshot_path):
            store = self._load()
            self._require_equal(store["adoption_snapshot_sha256"], pending.adoption_snapshot_sha256, "ERR_OUTPUT_ADOPTION_CONFIRMATION_STALE", "Output-adoption state changed after confirmation")
            execution, queue, production, prompt, entry = self._sources(pending.event["execution_id"])
            for actual, expected, code, message in (
                (execution["execution_snapshot_sha256"], pending.execution_snapshot_sha256, "ERR_OUTPUT_ADOPTION_EXECUTION_CONFLICT", "Execution state changed after confirmation"),
                (queue["queue_snapshot_sha256"], pending.queue_snapshot_sha256, "ERR_OUTPUT_ADOPTION_QUEUE_CONFLICT", "Queue state changed after confirmation"),
                (production["snapshot_sha256"], pending.production_snapshot_sha256, "ERR_OUTPUT_ADOPTION_PRODUCTION_CONFLICT", "Production state changed after confirmation"),
                (prompt["prompt_snapshot_sha256"], pending.prompt_snapshot_sha256, "ERR_OUTPUT_ADOPTION_PROMPT_CONFLICT", "Prompt state changed after confirmation"),
            ):
                self._require_equal(actual, expected, code, message)
            event = next(item for item in execution["latest_executions"] if item["execution_id"] == pending.event["execution_id"])
            if event != pending.event:
                raise ProductError("ERR_OUTPUT_ADOPTION_EXECUTION_IDENTITY_DRIFT", "Completed execution changed after confirmation", ProductErrorCategory.DATA_INTEGRITY)
            if entry != pending.queue_entry:
                raise ProductError("ERR_OUTPUT_ADOPTION_QUEUE_IDENTITY_DRIFT", "Queue execution lineage changed after confirmation", ProductErrorCategory.DATA_INTEGRITY)
            base = self._base(event, pending.candidate_id)
            latest = self._append(store, base, "PREPARED", asset_id=None)
            return self._continue(store, latest, event)

    def apply_recovery(self, *, adoption_id: str) -> dict[str, Any]:
        with exclusive_file_update_lock(self.snapshot_path):
            store = self._load()
            latest = self._latest_by_adoption(store).get(adoption_id)
            if latest is None or latest["state"] in _TERMINAL_STATES:
                raise ProductError("ERR_OUTPUT_ADOPTION_RECOVERY_NOT_REQUIRED", "No active output adoption matches this identity", ProductErrorCategory.STATE)
            execution, _queue, _production, _prompt, _entry = self._sources(
                latest["execution_id"], allow_prompt_recovery=True
            )
            event = next(item for item in execution["latest_executions"] if item["execution_id"] == latest["execution_id"])
            if (
                event["output_sha256"] != latest["output_sha256"]
                or event["output_ref"] != latest["output_ref"]
                or event["queue_entry_id"] != latest["queue_entry_id"]
                or sha256_bytes(canonical_json_bytes(event)) != latest["execution_event_sha256"]
            ):
                raise ProductError("ERR_OUTPUT_ADOPTION_RECOVERY_IDENTITY_DRIFT", "Completed execution no longer matches the active adoption", ProductErrorCategory.DATA_INTEGRITY)
            return self._continue(store, latest, event)


__all__ = [
    "AdoptedAssetIdentity",
    "Task027GeneratedOutputAssetPort",
    "Task027GenerationOutputAdoptionApplication",
]
