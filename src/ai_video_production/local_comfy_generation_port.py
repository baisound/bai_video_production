"""Concrete, fail-closed TASK-013 port for local MiniMax H3 text-to-video."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import time
from typing import Any, Protocol
from urllib.parse import urlparse

from .ai_connections import AiWorkload, CostClass, ModelRoute, ProviderFamily
from .atomic import AtomicJsonWriter
from .comfyui import (
    ComfyResourcePolicy,
    ComfyUIClient,
    _history_entry,
    _video_descriptors,
    admit_comfy_resources,
    assert_workflow_inputs_available,
    assert_workflow_supported,
    render_workflow_placeholders,
    resolve_comfy_output,
)
from .creative_generation_execution_application import (
    LocalGenerationExecutionRequest,
    LocalGenerationExecutionResult,
)
from .derived_assets import sha256_file
from .errors import ProductError, ProductErrorCategory
from .media_probe import FFprobeMediaProbe
from .production_control_store import _exclusive_snapshot_lock
from .serialization import canonical_json_bytes, sha256_bytes


_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")
_VIDEO_SUFFIXES = {".avi", ".mkv", ".mov", ".mp4", ".webm"}
_REQUIRED_CLASSES = frozenset({
    "UNETLoader", "CLIPLoader", "VAELoader", "MiniMaxH3ImageToVideo",
    "BasicGuider", "RandomNoise", "KSamplerSelect", "BasicScheduler",
    "SamplerCustomAdvanced", "VAEDecode", "VAEDecodeAudio", "CreateVideo", "SaveVideo",
})
MINIMAX_H3_NATIVE_WORKFLOW_SHA256 = "sha256:1a1d2a6108c5fe94df006f3c9177832db51302d4135b1e502e2c71afef2194f8"


class MediaProbe(Protocol):
    def probe(self, path: str | Path) -> Any: ...


def default_minimax_h3_workflow_path() -> Path:
    target = files("ai_video_production").joinpath("workflow_resources/minimax_h3_native_t2v_api.json")
    path = Path(str(target))
    if path.is_symlink() or not path.is_file():
        raise ProductError(
            "ERR_GENERATION_COMFY_WORKFLOW_RESOURCE",
            "Packaged MiniMax H3 workflow resource is unavailable",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    return path


@dataclass(frozen=True, slots=True)
class LocalComfyGenerationConfig:
    endpoint: str
    workflow_path: Path
    workflow_sha256: str
    comfy_output_root: Path
    project_output_root: Path
    staging_root: Path
    dispatch_journal_root: Path
    route_id: str
    provider_id: str
    model_id: str
    width: int = 832
    height: int = 480
    length: int = 124
    steps: int = 20
    poll_interval_seconds: float = 1.0
    completion_timeout_seconds: int = 3600
    max_output_bytes: int = 16 * 1024 * 1024 * 1024

    def __post_init__(self) -> None:
        parsed_endpoint = urlparse(self.endpoint)
        if (
            parsed_endpoint.scheme != "http"
            or parsed_endpoint.hostname != "127.0.0.1"
            or parsed_endpoint.port is None
            or parsed_endpoint.username is not None
            or parsed_endpoint.password is not None
            or parsed_endpoint.query
            or parsed_endpoint.fragment
            or parsed_endpoint.path not in {"", "/"}
            or self.endpoint.rstrip("/") != f"http://127.0.0.1:{parsed_endpoint.port}"
        ):
            raise ValueError("endpoint must be the exact bare 127.0.0.1 HTTP origin")
        for value, name in (
            (self.route_id, "route_id"),
            (self.provider_id, "provider_id"),
            (self.model_id, "model_id"),
        ):
            if not isinstance(value, str) or not _ID_RE.fullmatch(value):
                raise ValueError(f"{name} is invalid")
        if not _SHA_RE.fullmatch(self.workflow_sha256):
            raise ValueError("workflow_sha256 is invalid")
        for value, name in (
            (self.width, "width"), (self.height, "height"), (self.length, "length"),
            (self.steps, "steps"), (self.completion_timeout_seconds, "completion_timeout_seconds"),
            (self.max_output_bytes, "max_output_bytes"),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
        if isinstance(self.poll_interval_seconds, bool) or not isinstance(self.poll_interval_seconds, (int, float)):
            raise ValueError("poll_interval_seconds must be numeric")
        if self.width < 32 or self.height < 32 or self.width % 32 or self.height % 32:
            raise ValueError("width and height must be >=32 and divisible by 32")
        if self.length < 5 or (self.length - 5) % 17:
            raise ValueError("length must use the MiniMax H3 5+17k frame grid")
        if not 1 <= self.steps <= 100:
            raise ValueError("steps must be 1-100")
        if not 0.1 <= self.poll_interval_seconds <= 30:
            raise ValueError("poll_interval_seconds is invalid")
        if not 1 <= self.completion_timeout_seconds <= 86400:
            raise ValueError("completion_timeout_seconds is invalid")
        if self.max_output_bytes <= 0:
            raise ValueError("max_output_bytes must be positive")


def _require_directory(path: Path, *, code: str) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise ProductError(code, "Configured local generation directory is missing or unsafe", ProductErrorCategory.SECURITY)
    return path.resolve(strict=True)


def _load_workflow(path: Path, expected_sha256: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ProductError("ERR_GENERATION_COMFY_WORKFLOW", "Configured workflow is missing or unsafe", ProductErrorCategory.SECURITY)
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProductError("ERR_GENERATION_COMFY_WORKFLOW", "Configured workflow is unreadable", ProductErrorCategory.DATA_INTEGRITY) from exc
    if sha256_bytes(canonical_json_bytes(value)) != expected_sha256:
        raise ProductError("ERR_GENERATION_COMFY_WORKFLOW_CHECKSUM", "Configured workflow checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
    if not isinstance(value, dict) or not value:
        raise ProductError("ERR_GENERATION_COMFY_WORKFLOW", "Configured workflow must be a non-empty API object", ProductErrorCategory.DATA_INTEGRITY)
    classes = {node.get("class_type") for node in value.values() if isinstance(node, dict)}
    if classes != _REQUIRED_CLASSES:
        raise ProductError("ERR_GENERATION_COMFY_WORKFLOW_CLASSES", "Configured workflow has unexpected native classes", ProductErrorCategory.SECURITY)
    serialized = json.dumps(value, ensure_ascii=False)
    for placeholder in ("{{PROMPT}}", "{{SEED}}", "{{WIDTH}}", "{{HEIGHT}}", "{{LENGTH}}", "{{STEPS}}", "{{OUTPUT_PREFIX}}"):
        if serialized.count(placeholder) != 1:
            raise ProductError("ERR_GENERATION_COMFY_WORKFLOW_PLACEHOLDER", "Configured workflow placeholders are invalid", ProductErrorCategory.DATA_INTEGRITY)
    return value


def _with_hash(value: dict[str, Any]) -> dict[str, Any]:
    body = {key: item for key, item in value.items() if key != "journal_sha256"}
    body["journal_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


class LocalComfyTextToVideoPort:
    """Exact local/free ComfyUI execution port with a body-private dispatch journal."""

    def __init__(
        self,
        *,
        config: LocalComfyGenerationConfig,
        client: ComfyUIClient,
        resource_policy: ComfyResourcePolicy | None = None,
        media_probe: MediaProbe | None = None,
        monotonic: Any = time.monotonic,
        sleeper: Any = time.sleep,
    ) -> None:
        if client.endpoint != config.endpoint.rstrip("/"):
            raise ProductError("ERR_GENERATION_COMFY_ENDPOINT_DRIFT", "ComfyUI client endpoint differs from trusted configuration", ProductErrorCategory.SECURITY)
        self.config = config
        self.client = client
        self.comfy_output_root = _require_directory(config.comfy_output_root, code="ERR_GENERATION_COMFY_OUTPUT_ROOT")
        self.project_output_root = _require_directory(config.project_output_root, code="ERR_GENERATION_PROJECT_OUTPUT_ROOT")
        self.staging_root = _require_directory(config.staging_root, code="ERR_GENERATION_COMFY_STAGING_ROOT")
        self.dispatch_journal_root = _require_directory(config.dispatch_journal_root, code="ERR_GENERATION_COMFY_JOURNAL_ROOT")
        self.workflow = _load_workflow(config.workflow_path, config.workflow_sha256)
        self.resource_policy = resource_policy or ComfyResourcePolicy(
            min_free_vram_bytes=8 * 1024 * 1024 * 1024,
            min_free_ram_bytes=16 * 1024 * 1024 * 1024,
            min_free_disk_bytes=10 * 1024 * 1024 * 1024,
        )
        self.media_probe = media_probe or FFprobeMediaProbe()
        self._monotonic = monotonic
        self._sleeper = sleeper

    def _journal_path(self, execution_id: str) -> Path:
        if not _ID_RE.fullmatch(execution_id):
            raise ProductError("ERR_GENERATION_COMFY_EXECUTION_ID", "Execution identity is invalid", ProductErrorCategory.VALIDATION)
        return self.dispatch_journal_root / f"{execution_id}.json"

    @staticmethod
    def _validate_journal(value: Any) -> None:
        expected = {
            "journal_version", "task_owner", "execution_id", "queue_entry_id", "route_id",
            "workflow_sha256", "prompt_sha256", "state", "prompt_id", "output_ref",
            "output_sha256", "journal_sha256",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise ProductError("ERR_GENERATION_COMFY_JOURNAL", "Dispatch journal fields are invalid", ProductErrorCategory.DATA_INTEGRITY)
        if value.get("journal_version") != "1.0.0" or value.get("task_owner") != "TASK-013":
            raise ProductError("ERR_GENERATION_COMFY_JOURNAL", "Dispatch journal identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
        if value.get("journal_sha256") != _with_hash(value)["journal_sha256"]:
            raise ProductError("ERR_GENERATION_COMFY_JOURNAL_CHECKSUM", "Dispatch journal checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
        state = value.get("state")
        if state not in {"PREPARED", "QUEUED", "COMPLETED", "FAILED"}:
            raise ProductError("ERR_GENERATION_COMFY_JOURNAL", "Dispatch journal state is invalid", ProductErrorCategory.DATA_INTEGRITY)
        if state == "PREPARED" and any(value.get(name) is not None for name in ("prompt_id", "output_ref", "output_sha256")):
            raise ProductError("ERR_GENERATION_COMFY_JOURNAL", "PREPARED journal contains output identity", ProductErrorCategory.DATA_INTEGRITY)
        if state in {"QUEUED", "FAILED"} and (not isinstance(value.get("prompt_id"), str) or value.get("output_ref") is not None or value.get("output_sha256") is not None):
            raise ProductError("ERR_GENERATION_COMFY_JOURNAL", "Queued/failed journal fields are invalid", ProductErrorCategory.DATA_INTEGRITY)
        if state == "COMPLETED" and (not isinstance(value.get("prompt_id"), str) or not isinstance(value.get("output_ref"), str) or not _SHA_RE.fullmatch(value.get("output_sha256", ""))):
            raise ProductError("ERR_GENERATION_COMFY_JOURNAL", "Completed journal fields are invalid", ProductErrorCategory.DATA_INTEGRITY)

    def _reserve(self, route: ModelRoute, request: LocalGenerationExecutionRequest) -> tuple[Path, dict[str, Any]]:
        path = self._journal_path(request.execution_id)
        owned_comfy_root = self.comfy_output_root / "bai-task013"
        if owned_comfy_root.is_symlink():
            raise ProductError("ERR_GENERATION_COMFY_OUTPUT_SYMLINK", "Product-owned ComfyUI output root must not be a symlink", ProductErrorCategory.SECURITY)
        try:
            owned_comfy_root.mkdir(exist_ok=True)
            owned_comfy_root.resolve(strict=True).relative_to(self.comfy_output_root)
        except (OSError, ValueError) as exc:
            raise ProductError("ERR_GENERATION_COMFY_OUTPUT_ESCAPE", "Product-owned ComfyUI output root is unsafe", ProductErrorCategory.SECURITY) from exc
        expected_comfy_dir = owned_comfy_root / request.execution_id
        if expected_comfy_dir.exists() or expected_comfy_dir.is_symlink():
            raise ProductError("ERR_GENERATION_COMFY_OUTPUT_EXISTS", "Execution output prefix already exists", ProductErrorCategory.STATE)
        with _exclusive_snapshot_lock(path):
            if path.exists():
                raise ProductError("ERR_GENERATION_COMFY_ALREADY_DISPATCHED", "Execution already has a local dispatch journal", ProductErrorCategory.STATE)
            value = _with_hash({
                "journal_version": "1.0.0", "task_owner": "TASK-013",
                "execution_id": request.execution_id, "queue_entry_id": request.queue_entry_id,
                "route_id": route.route_id, "workflow_sha256": self.config.workflow_sha256,
                "prompt_sha256": request.prompt_sha256, "state": "PREPARED", "prompt_id": None,
                "output_ref": None, "output_sha256": None,
            })
            AtomicJsonWriter.write(path, value, validator=self._validate_journal)
        return path, value

    def _advance(self, path: Path, value: dict[str, Any], *, state: str, prompt_id: str, output_ref: str | None = None, output_sha256: str | None = None) -> dict[str, Any]:
        with _exclusive_snapshot_lock(path):
            if path.is_symlink() or not path.is_file():
                raise ProductError("ERR_GENERATION_COMFY_JOURNAL_FILE", "Dispatch journal is missing or unsafe", ProductErrorCategory.SECURITY)
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ProductError("ERR_GENERATION_COMFY_JOURNAL", "Dispatch journal is unreadable", ProductErrorCategory.DATA_INTEGRITY) from exc
            self._validate_journal(current)
            if current != value:
                raise ProductError("ERR_GENERATION_COMFY_JOURNAL_CONFLICT", "Dispatch journal changed concurrently", ProductErrorCategory.STATE)
            allowed = {"PREPARED": {"QUEUED", "FAILED"}, "QUEUED": {"COMPLETED", "FAILED"}}
            if state not in allowed.get(current["state"], set()):
                raise ProductError("ERR_GENERATION_COMFY_JOURNAL_TRANSITION", "Dispatch journal transition is invalid", ProductErrorCategory.STATE)
            updated = dict(current)
            updated.update({"state": state, "prompt_id": prompt_id, "output_ref": output_ref, "output_sha256": output_sha256})
            updated = _with_hash(updated)
            AtomicJsonWriter.write(path, updated, validator=self._validate_journal)
            return updated

    def _authorize(self, route: ModelRoute, request: LocalGenerationExecutionRequest) -> None:
        exact = (
            route.route_id == self.config.route_id
            and route.provider_id == self.config.provider_id
            and route.model_id == self.config.model_id
            and route.workload is AiWorkload.VIDEO
            and route.provider_family is ProviderFamily.COMFYUI
            and route.cost_class is CostClass.LOCAL_FREE_AI
            and route.credential_ref is None
            and route.enabled
            and request.capability == "TEXT_TO_VIDEO"
            and request.capability in route.capabilities
        )
        if not exact:
            raise ProductError("ERR_GENERATION_COMFY_ROUTE", "Route is not the exact authorized local/free T2V target", ProductErrorCategory.AUTHORIZATION)
        if request.input_bindings:
            raise ProductError("ERR_GENERATION_COMFY_INPUTS", "This bounded native adapter accepts text-to-video without external inputs", ProductErrorCategory.NOT_SUPPORTED)
        if sha256_bytes(request.prompt_text.encode("utf-8")) != request.prompt_sha256:
            raise ProductError("ERR_GENERATION_COMFY_PROMPT_CHECKSUM", "Execution Prompt does not match authorized Evidence", ProductErrorCategory.DATA_INTEGRITY)

    def _authorize_runtime(self, stats: dict[str, Any]) -> None:
        system = stats.get("system")
        argv = system.get("argv") if isinstance(system, dict) else None
        if not isinstance(argv, list) or not argv or any(not isinstance(item, str) for item in argv):
            raise ProductError("ERR_GENERATION_COMFY_RUNTIME_IDENTITY", "ComfyUI did not prove its exact launch identity", ProductErrorCategory.AUTHORIZATION)
        prohibited = {
            "--cpu", "--disable-dynamic-vram", "--gpu-only", "--highvram",
            "--lowvram", "--novram",
        }
        present = sorted(prohibited.intersection(argv))
        if present:
            raise ProductError(
                "ERR_GENERATION_COMFY_RUNTIME_UNSAFE",
                "ComfyUI launch mode is outside the verified native execution boundary",
                ProductErrorCategory.RESOURCE_EXHAUSTED,
                details={"prohibited_flags": present},
            )
        if "--disable-auto-launch" not in argv:
            raise ProductError("ERR_GENERATION_COMFY_RUNTIME_IDENTITY", "ComfyUI must use the non-interactive trusted launch boundary", ProductErrorCategory.AUTHORIZATION)

        def exact_flag(name: str) -> str:
            indexes = [index for index, value in enumerate(argv) if value == name]
            if len(indexes) != 1 or indexes[0] + 1 >= len(argv):
                raise ProductError("ERR_GENERATION_COMFY_RUNTIME_IDENTITY", "ComfyUI launch arguments are missing or ambiguous", ProductErrorCategory.AUTHORIZATION, details={"flag": name})
            return argv[indexes[0] + 1]

        parsed = urlparse(self.config.endpoint)
        if exact_flag("--listen") != "127.0.0.1" or exact_flag("--port") != str(parsed.port):
            raise ProductError("ERR_GENERATION_COMFY_RUNTIME_ENDPOINT", "ComfyUI launch endpoint differs from the authorized loopback origin", ProductErrorCategory.SECURITY)
        runtime_output = Path(exact_flag("--output-directory"))
        try:
            matches = runtime_output.resolve(strict=True) == self.comfy_output_root
        except OSError:
            matches = False
        if not matches:
            raise ProductError("ERR_GENERATION_COMFY_RUNTIME_OUTPUT", "ComfyUI runtime output root differs from the Product-owned root", ProductErrorCategory.SECURITY)

    @staticmethod
    def _uncertain(code: str, message: str, *, prompt_id: str | None = None) -> ProductError:
        details: dict[str, Any] = {"execution_state_uncertain": True, "automatic_retry_allowed": False}
        if prompt_id is not None:
            details["provider_operation_id"] = prompt_id
        return ProductError(code, message, ProductErrorCategory.STATE, retryable=False, details=details)

    def _publish(self, source: Path, execution_id: str) -> tuple[str, str]:
        size = source.stat().st_size
        if size <= 0 or size > self.config.max_output_bytes:
            raise ProductError("ERR_GENERATION_COMFY_OUTPUT_SIZE", "Generated output size is invalid", ProductErrorCategory.DATA_INTEGRITY)
        suffix = source.suffix.lower()
        if suffix not in _VIDEO_SUFFIXES:
            raise ProductError("ERR_GENERATION_COMFY_OUTPUT_SUFFIX", "Generated output is not a supported video container", ProductErrorCategory.DATA_INTEGRITY)
        relative = PurePosixPath("generated") / execution_id / f"result{suffix}"
        generated_root = self.project_output_root / "generated"
        if generated_root.is_symlink():
            raise ProductError("ERR_GENERATION_PROJECT_OUTPUT_SYMLINK", "Canonical generated root must not be a symlink", ProductErrorCategory.SECURITY)
        try:
            generated_root.mkdir(exist_ok=True)
        except OSError as exc:
            raise ProductError("ERR_GENERATION_PROJECT_OUTPUT_ROOT", "Canonical generated root cannot be prepared", ProductErrorCategory.SECURITY) from exc
        try:
            generated_root.resolve(strict=True).relative_to(self.project_output_root)
        except ValueError as exc:
            raise ProductError("ERR_GENERATION_PROJECT_OUTPUT_ESCAPE", "Canonical generated root escapes project output", ProductErrorCategory.SECURITY) from exc
        target_dir = generated_root / execution_id
        if target_dir.exists() or target_dir.is_symlink():
            raise ProductError("ERR_GENERATION_PROJECT_OUTPUT_EXISTS", "Canonical output target already exists", ProductErrorCategory.STATE)
        try:
            target_dir.mkdir(parents=True, exist_ok=False)
        except OSError as exc:
            raise ProductError("ERR_GENERATION_PROJECT_OUTPUT_EXISTS", "Canonical output target cannot be reserved", ProductErrorCategory.STATE) from exc
        target = target_dir / f"result{suffix}"
        temporary = target_dir / f".result{suffix}.tmp"
        try:
            shutil.copyfile(source, temporary)
            source_sha = sha256_file(source)
            if sha256_file(temporary) != source_sha:
                raise ProductError("ERR_GENERATION_PROJECT_OUTPUT_CHECKSUM", "Canonical output copy checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
            os.replace(temporary, target)
        except ProductError:
            raise
        except OSError as exc:
            raise ProductError("ERR_GENERATION_PROJECT_OUTPUT_WRITE", "Canonical output could not be written", ProductErrorCategory.DATA_INTEGRITY) from exc
        if target.is_symlink() or not target.is_file():
            raise ProductError("ERR_GENERATION_PROJECT_OUTPUT_FILE", "Canonical output is missing or unsafe", ProductErrorCategory.SECURITY)
        probe = self.media_probe.probe(target)
        if not probe.has_video:
            raise ProductError("ERR_GENERATION_PROJECT_OUTPUT_NOT_VIDEO", "Canonical output has no video stream", ProductErrorCategory.DATA_INTEGRITY)
        target_sha = sha256_file(target)
        if target_sha != source_sha:
            raise ProductError("ERR_GENERATION_PROJECT_OUTPUT_CHECKSUM", "Canonical output changed after publication", ProductErrorCategory.DATA_INTEGRITY)
        return f"project-output://{relative.as_posix()}", target_sha

    def execute(self, route: ModelRoute, request: LocalGenerationExecutionRequest) -> LocalGenerationExecutionResult:
        self._authorize(route, request)
        workflow = render_workflow_placeholders(self.workflow, {
            "PROMPT": request.prompt_text,
            "SEED": int(request.prompt_sha256[-16:], 16) & (2**63 - 1),
            "WIDTH": self.config.width, "HEIGHT": self.config.height,
            "LENGTH": self.config.length, "STEPS": self.config.steps,
            "OUTPUT_PREFIX": f"bai-task013/{request.execution_id}/result",
        })
        object_info = self.client.object_info()
        assert_workflow_supported(workflow, object_info)
        assert_workflow_inputs_available(workflow, object_info)
        stats = self.client.system_stats()
        admit_comfy_resources(stats, self.resource_policy, staging_root=self.staging_root)
        self._authorize_runtime(stats)
        journal_path, journal = self._reserve(route, request)
        started = self._monotonic()
        try:
            prompt_id = self.client.queue(workflow, client_id=request.execution_id)
        except ProductError as exc:
            if exc.code == "ERR_PROVIDER_COMFY_HTTP" and isinstance(exc.details.get("status"), int) and exc.details["status"] < 500:
                self._advance(journal_path, journal, state="FAILED", prompt_id="REQUEST_REJECTED")
                raise
            raise self._uncertain("ERR_GENERATION_COMFY_DISPATCH_UNCERTAIN", "ComfyUI dispatch result is uncertain") from exc
        if not _ID_RE.fullmatch(prompt_id):
            raise self._uncertain("ERR_GENERATION_COMFY_PROMPT_ID", "ComfyUI returned an unsafe prompt identity")
        journal = self._advance(journal_path, journal, state="QUEUED", prompt_id=prompt_id)
        deadline = self._monotonic() + self.config.completion_timeout_seconds
        entry: dict[str, Any] | None = None
        while self._monotonic() < deadline:
            try:
                history = self.client.history(prompt_id)
            except ProductError as exc:
                raise self._uncertain("ERR_GENERATION_COMFY_HISTORY_UNCERTAIN", "ComfyUI history is unavailable after dispatch", prompt_id=prompt_id) from exc
            entry = _history_entry(history, prompt_id)
            if entry is not None:
                status = entry.get("status")
                if isinstance(status, dict) and str(status.get("status_str", "")).lower() in {"error", "failed"}:
                    self._advance(journal_path, journal, state="FAILED", prompt_id=prompt_id)
                    raise ProductError("ERR_GENERATION_COMFY_EXECUTION_FAILED", "ComfyUI reported native generation failure", ProductErrorCategory.EXTERNAL_DEPENDENCY)
                if _video_descriptors(entry):
                    break
            self._sleeper(self.config.poll_interval_seconds)
        else:
            raise self._uncertain("ERR_GENERATION_COMFY_TIMEOUT_UNCERTAIN", "ComfyUI generation did not finish before the bounded timeout", prompt_id=prompt_id)
        assert entry is not None
        videos = _video_descriptors(entry)
        if len(videos) != 1:
            self._advance(journal_path, journal, state="FAILED", prompt_id=prompt_id)
            raise ProductError("ERR_GENERATION_COMFY_OUTPUT_AMBIGUOUS", "ComfyUI did not return exactly one video output", ProductErrorCategory.HUMAN_REVIEW_REQUIRED, details={"video_count": len(videos)})
        try:
            source = resolve_comfy_output(self.comfy_output_root, videos[0])
            try:
                expected_source_root = (self.comfy_output_root / "bai-task013" / request.execution_id).resolve(strict=True)
                source.relative_to(expected_source_root)
            except (FileNotFoundError, ValueError) as exc:
                raise ProductError("ERR_GENERATION_COMFY_OUTPUT_IDENTITY", "ComfyUI output is outside the exact execution prefix", ProductErrorCategory.SECURITY) from exc
            output_ref, output_sha = self._publish(source, request.execution_id)
        except ProductError:
            self._advance(journal_path, journal, state="FAILED", prompt_id=prompt_id)
            raise
        self._advance(journal_path, journal, state="COMPLETED", prompt_id=prompt_id, output_ref=output_ref, output_sha256=output_sha)
        latency_ms = max(0, int((self._monotonic() - started) * 1000))
        return LocalGenerationExecutionResult(
            route.route_id, route.provider_family, route.provider_id, route.model_id,
            request.capability, prompt_id, output_ref, output_sha, "VIDEO", latency_ms,
        )


__all__ = [
    "LocalComfyGenerationConfig", "LocalComfyTextToVideoPort", "MINIMAX_H3_NATIVE_WORKFLOW_SHA256",
    "default_minimax_h3_workflow_path",
]
