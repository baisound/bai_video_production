from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import ipaddress
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import uuid

from .assets import AssetType, AudioRightsStatus, PermissionState, RightsStatus
from .derived_assets import DerivedAssetPublisher, DerivedAssetSpec, sha256_file
from .errors import ProductError, ProductErrorCategory
from .h3_acceleration import H3AccelerationContract, H3AccelerationMode, SPECTRUM_CLASS_TYPE
from .media_probe import FFprobeMediaProbe
from .paths import SourcePathPolicy, LogicalPathResolver
from .serialization import sha256_bytes, canonical_json_bytes
from .store import OperationRecord, SQLiteProductStore
from .task004_manifest import Task004ManifestWriter


class VideoGenerationMode(str, Enum):
    TEXT_TO_VIDEO = "TEXT_TO_VIDEO"
    IMAGE_TO_VIDEO = "IMAGE_TO_VIDEO"
    FIRST_LAST = "FIRST_LAST"
    REFERENCE = "REFERENCE"


class ImageGenerationMode(str, Enum):
    TEXT_TO_IMAGE = "TEXT_TO_IMAGE"
    IMAGE_TO_IMAGE = "IMAGE_TO_IMAGE"


class VisualModelFamily(str, Enum):
    FLUX_1_SCHNELL = "FLUX_1_SCHNELL"
    FLUX_1_DEV = "FLUX_1_DEV"
    SDXL_1_0 = "SDXL_1_0"
    SD3_5 = "SD3_5"
    SD1_5 = "SD1_5"
    CUSTOM = "CUSTOM"


class RuntimeLicenseState(str, Enum):
    ALLOWED = "ALLOWED"
    RESTRICTED = "RESTRICTED"
    CONDITIONAL = "CONDITIONAL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class LocalImageModelProfile:
    family: VisualModelFamily
    model_identifier: str
    license_id: str
    runtime_license_state: RuntimeLicenseState
    profile_name: str

    def __post_init__(self) -> None:
        for value, field_name in ((self.model_identifier, "model_identifier"), (self.license_id, "license_id"), (self.profile_name, "profile_name")):
            if not value.strip() or "\x00" in value or len(value) > 500:
                raise ValueError(f"{field_name} must be non-empty, bounded text")

    def to_dict(self) -> dict[str, str]:
        return {
            "family": self.family.value,
            "model_identifier": self.model_identifier,
            "license_id": self.license_id,
            "runtime_license_state": self.runtime_license_state.value,
            "profile_name": self.profile_name,
        }


def builtin_image_model_profile(family: VisualModelFamily) -> LocalImageModelProfile:
    profiles = {
        VisualModelFamily.FLUX_1_SCHNELL: LocalImageModelProfile(
            family, "black-forest-labs/FLUX.1-schnell", "Apache-2.0", RuntimeLicenseState.ALLOWED, "flux-1-schnell-native"
        ),
        VisualModelFamily.FLUX_1_DEV: LocalImageModelProfile(
            family, "black-forest-labs/FLUX.1-dev", "FLUX.1-dev-Non-Commercial", RuntimeLicenseState.RESTRICTED, "flux-1-dev-compatible"
        ),
        VisualModelFamily.SDXL_1_0: LocalImageModelProfile(
            family, "stabilityai/stable-diffusion-xl-base-1.0", "CreativeML-Open-RAIL++-M", RuntimeLicenseState.CONDITIONAL, "sdxl-1.0-compatible"
        ),
        VisualModelFamily.SD3_5: LocalImageModelProfile(
            family, "stabilityai/stable-diffusion-3.5-large", "Stability-AI-Community", RuntimeLicenseState.CONDITIONAL, "sd3.5-compatible"
        ),
        VisualModelFamily.SD1_5: LocalImageModelProfile(
            family, "stable-diffusion-1.5-compatible-checkpoint", "MODEL-SPECIFIC-REVIEW", RuntimeLicenseState.UNKNOWN, "sd1.5-legacy-compatible"
        ),
    }
    if family is VisualModelFamily.CUSTOM:
        raise ValueError("CUSTOM model family requires an explicit LocalImageModelProfile")
    return profiles[family]


def authorize_image_runtime_license(
    profile: LocalImageModelProfile,
    *,
    commercial_runtime_requested: bool,
    license_authorization_ref: str | None,
) -> None:
    _validate_license_authorization_ref(license_authorization_ref)
    if not commercial_runtime_requested:
        return
    if profile.runtime_license_state is RuntimeLicenseState.ALLOWED:
        return
    if license_authorization_ref:
        return
    raise ProductError(
        "ERR_AUTH_MODEL_COMMERCIAL_RUNTIME_LICENSE",
        "commercial local model execution requires explicit license authorization for this model profile",
        ProductErrorCategory.AUTHORIZATION,
        details={
            "model_family": profile.family.value,
            "license_id": profile.license_id,
            "runtime_license_state": profile.runtime_license_state.value,
        },
    )


_SAFE_WORKFLOW_PLACEHOLDER = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_IMAGE_RESERVED_SUBSTITUTIONS = {"PROMPT", "NEGATIVE_PROMPT", "SEED", "WIDTH", "HEIGHT", "REFERENCE_IMAGE"}
_VIDEO_RESERVED_SUBSTITUTIONS = {"PROMPT", "SEED"}


def _validate_license_authorization_ref(value: str | None) -> str | None:
    if value is None:
        return None
    if not value.strip() or "\x00" in value or len(value) > 1000:
        raise ProductError("ERR_INPUT_MODEL_LICENSE_AUTH_REF", "model license authorization reference is invalid", ProductErrorCategory.VALIDATION)
    return value


def _prepare_owned_comfy_subdir(root: Path, relative_dir: Path) -> Path:
    canonical_root = root.resolve(strict=True)
    if relative_dir.is_absolute() or any(part in {"", ".", ".."} for part in relative_dir.parts):
        raise ProductError("ERR_SECURITY_COMFY_INPUT_PATH", "invalid Product-owned ComfyUI input staging path", ProductErrorCategory.SECURITY)
    current = canonical_root
    for part in relative_dir.parts:
        current = current / part
        if current.is_symlink():
            raise ProductError("ERR_SECURITY_COMFY_INPUT_SYMLINK", "ComfyUI input staging path contains a symlink", ProductErrorCategory.SECURITY)
    try:
        current.relative_to(canonical_root)
    except ValueError as exc:
        raise ProductError("ERR_SECURITY_COMFY_INPUT_ESCAPE", "ComfyUI input staging path escapes configured root", ProductErrorCategory.SECURITY) from exc
    if current.exists():
        if not current.is_dir():
            raise ProductError("ERR_SECURITY_COMFY_INPUT_PATH", "Product-owned ComfyUI input staging target is not a directory", ProductErrorCategory.SECURITY)
        shutil.rmtree(current)
    current.mkdir(parents=True, exist_ok=False)
    resolved = current.resolve(strict=True)
    try:
        resolved.relative_to(canonical_root)
    except ValueError as exc:
        raise ProductError("ERR_SECURITY_COMFY_INPUT_ESCAPE", "ComfyUI input staging path escaped during creation", ProductErrorCategory.SECURITY) from exc
    return resolved


def _bounded_reference_placeholder(name: str) -> str:
    if not _SAFE_WORKFLOW_PLACEHOLDER.fullmatch(name):
        raise ProductError("ERR_INPUT_COMFY_REFERENCE_PLACEHOLDER", "reference placeholder must be an uppercase safe token", ProductErrorCategory.VALIDATION)
    return name


@dataclass(frozen=True, slots=True)
class ComfyEndpointPolicy:
    allowlisted_local_hostnames: tuple[str, ...] = ()

    def authorize(self, endpoint: str) -> str:
        parsed = urlparse(endpoint)
        if parsed.scheme != "http":
            raise ProductError("ERR_SECURITY_COMFY_ENDPOINT_SCHEME", "ComfyUI endpoint must use local HTTP", ProductErrorCategory.SECURITY)
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
            raise ProductError("ERR_SECURITY_COMFY_ENDPOINT_FORMAT", "ComfyUI endpoint must be a bare local origin without credentials/query/path", ProductErrorCategory.SECURITY)
        if parsed.port is None:
            raise ProductError("ERR_SECURITY_COMFY_ENDPOINT_PORT", "ComfyUI endpoint must specify an explicit port", ProductErrorCategory.SECURITY)
        host = (parsed.hostname or "").lower().rstrip(".")
        if not host:
            raise ProductError("ERR_SECURITY_COMFY_ENDPOINT_HOST", "ComfyUI endpoint host is missing", ProductErrorCategory.SECURITY)
        if host == "localhost":
            return f"http://localhost:{parsed.port}"
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if host not in {h.lower().rstrip('.') for h in self.allowlisted_local_hostnames}:
                raise ProductError("ERR_SECURITY_COMFY_ENDPOINT_DENIED", "ComfyUI hostname is not explicitly allowlisted", ProductErrorCategory.SECURITY)
        else:
            allowed = address.is_loopback
            if isinstance(address, ipaddress.IPv4Address):
                allowed = allowed or any(address in network for network in (
                    ipaddress.ip_network("10.0.0.0/8"),
                    ipaddress.ip_network("172.16.0.0/12"),
                    ipaddress.ip_network("192.168.0.0/16"),
                ))
            else:
                allowed = allowed or address in ipaddress.ip_network("fc00::/7")
            if not allowed or address.is_unspecified or address.is_multicast or address.is_link_local or (address.is_reserved and not address.is_loopback):
                raise ProductError("ERR_SECURITY_COMFY_ENDPOINT_DENIED", "ComfyUI endpoint is not an explicitly permitted local address", ProductErrorCategory.SECURITY)
        display_host = f"[{host}]" if ":" in host else host
        return f"http://{display_host}:{parsed.port}"


_MAX_COMFY_RESPONSE_BYTES = 64 * 1024 * 1024
_MAX_WORKFLOW_BYTES = 10 * 1024 * 1024


def _load_workflow_json(path: Path, *, max_bytes: int = _MAX_WORKFLOW_BYTES) -> dict[str, Any]:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ProductError("ERR_INPUT_COMFY_WORKFLOW_UNREADABLE", "ComfyUI workflow cannot be read", ProductErrorCategory.VALIDATION) from exc
    if size <= 0 or size > max_bytes:
        raise ProductError("ERR_INPUT_COMFY_WORKFLOW_SIZE", "ComfyUI workflow file is empty or exceeds the configured size limit", ProductErrorCategory.VALIDATION, details={"size_bytes": size, "max_bytes": max_bytes})
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProductError("ERR_INPUT_COMFY_WORKFLOW_JSON", "ComfyUI workflow must be valid UTF-8 JSON", ProductErrorCategory.VALIDATION) from exc
    if not isinstance(value, dict) or not value:
        raise ProductError("ERR_INPUT_COMFY_WORKFLOW_FORMAT", "ComfyUI workflow must be a non-empty JSON object", ProductErrorCategory.VALIDATION)
    return value


class ComfyUIClient:
    def __init__(self, endpoint: str, *, endpoint_policy: ComfyEndpointPolicy | None = None, timeout_seconds: int = 15, max_response_bytes: int = _MAX_COMFY_RESPONSE_BYTES) -> None:
        if not 1 <= timeout_seconds <= 120:
            raise ValueError("timeout_seconds must be 1-120")
        if not 1024 <= max_response_bytes <= 128 * 1024 * 1024:
            raise ValueError("max_response_bytes must be 1 KiB-128 MiB")
        self.endpoint = (endpoint_policy or ComfyEndpointPolicy()).authorize(endpoint).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes

    def _json(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        data = canonical_json_bytes(body) if body is not None else None
        request = Request(self.endpoint + path, data=data, method=method, headers={"Content-Type": "application/json"} if data is not None else {})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read(self.max_response_bytes + 1)
                if len(raw) > self.max_response_bytes:
                    raise ProductError("ERR_PROVIDER_COMFY_RESPONSE_TOO_LARGE", "ComfyUI response exceeded the configured size limit", ProductErrorCategory.EXTERNAL_DEPENDENCY, details={"max_bytes": self.max_response_bytes})
        except HTTPError as exc:
            raise ProductError("ERR_PROVIDER_COMFY_HTTP", "ComfyUI returned an HTTP error", ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=500 <= exc.code < 600, details={"status": exc.code}) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ProductError("ERR_PROVIDER_COMFY_UNREACHABLE", "ComfyUI local endpoint is unreachable", ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=True) from exc
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_PROVIDER_COMFY_INVALID_JSON", "ComfyUI returned invalid JSON", ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=True) from exc

    def system_stats(self) -> dict[str, Any]:
        value = self._json("GET", "/system_stats")
        if not isinstance(value, dict):
            raise ProductError("ERR_PROVIDER_COMFY_INVALID_STATS", "ComfyUI system_stats must be an object", ProductErrorCategory.EXTERNAL_DEPENDENCY)
        return value

    def object_info(self) -> dict[str, Any]:
        value = self._json("GET", "/object_info")
        if not isinstance(value, dict):
            raise ProductError("ERR_PROVIDER_COMFY_INVALID_OBJECT_INFO", "ComfyUI object_info must be an object", ProductErrorCategory.EXTERNAL_DEPENDENCY)
        return value

    def queue(self, workflow: dict[str, Any], *, client_id: str) -> str:
        value = self._json("POST", "/prompt", {"prompt": workflow, "client_id": client_id})
        prompt_id = value.get("prompt_id") if isinstance(value, dict) else None
        if not isinstance(prompt_id, str) or not prompt_id.strip():
            raise ProductError("ERR_PROVIDER_COMFY_PROMPT_ID_MISSING", "ComfyUI queue response did not include prompt_id", ProductErrorCategory.EXTERNAL_DEPENDENCY)
        return prompt_id

    def history(self, prompt_id: str) -> dict[str, Any]:
        value = self._json("GET", f"/history/{prompt_id}")
        if not isinstance(value, dict):
            raise ProductError("ERR_PROVIDER_COMFY_INVALID_HISTORY", "ComfyUI history must be an object", ProductErrorCategory.EXTERNAL_DEPENDENCY)
        return value


@dataclass(frozen=True, slots=True)
class ComfyResourcePolicy:
    require_gpu: bool = True
    min_free_vram_bytes: int = 0
    min_free_ram_bytes: int = 0
    min_free_disk_bytes: int = 2 * 1024 * 1024 * 1024

    def __post_init__(self) -> None:
        if self.min_free_vram_bytes < 0 or self.min_free_ram_bytes < 0 or self.min_free_disk_bytes < 0:
            raise ValueError("resource floors must be >= 0")


def _device_list(stats: dict[str, Any]) -> list[dict[str, Any]]:
    devices = stats.get("devices")
    if isinstance(devices, list):
        return [d for d in devices if isinstance(d, dict)]
    nested = stats.get("system")
    if isinstance(nested, dict) and isinstance(nested.get("devices"), list):
        return [d for d in nested["devices"] if isinstance(d, dict)]
    return []


def admit_comfy_resources(stats: dict[str, Any], policy: ComfyResourcePolicy, *, staging_root: Path) -> dict[str, Any]:
    devices = _device_list(stats)
    gpu_like = [d for d in devices if any(token in str(d.get(k, "")).lower() for k in ("type", "name", "device") for token in ("cuda", "gpu", "mps", "xpu"))]
    if policy.require_gpu and not gpu_like:
        raise ProductError("ERR_RESOURCE_COMFY_GPU_REQUIRED", "configured ComfyUI generation requires a visible GPU device", ProductErrorCategory.RESOURCE_EXHAUSTED)
    candidates = gpu_like or devices
    free_values: list[int] = []
    for device in candidates:
        for key in ("vram_free", "free_vram", "torch_vram_free"):
            value = device.get(key)
            if isinstance(value, (int, float)) and value >= 0:
                free_values.append(int(value))
    if policy.min_free_vram_bytes:
        if not free_values:
            raise ProductError("ERR_RESOURCE_COMFY_VRAM_UNKNOWN", "ComfyUI did not prove free VRAM for configured admission floor", ProductErrorCategory.RESOURCE_EXHAUSTED)
        if max(free_values) < policy.min_free_vram_bytes:
            raise ProductError("ERR_RESOURCE_COMFY_VRAM_LOW", "free VRAM is below configured admission floor", ProductErrorCategory.RESOURCE_EXHAUSTED, details={"required_bytes": policy.min_free_vram_bytes, "max_verified_free_bytes": max(free_values)})
    system = stats.get("system") if isinstance(stats.get("system"), dict) else {}
    ram_free = system.get("ram_free") if isinstance(system.get("ram_free"), (int, float)) else None
    if policy.min_free_ram_bytes:
        if ram_free is None:
            raise ProductError("ERR_RESOURCE_COMFY_RAM_UNKNOWN", "ComfyUI did not prove free RAM for configured admission floor", ProductErrorCategory.RESOURCE_EXHAUSTED)
        if int(ram_free) < policy.min_free_ram_bytes:
            raise ProductError("ERR_RESOURCE_COMFY_RAM_LOW", "free RAM is below configured admission floor", ProductErrorCategory.RESOURCE_EXHAUSTED, details={"required_bytes": policy.min_free_ram_bytes, "free_bytes": int(ram_free)})
    staging_root.mkdir(parents=True, exist_ok=True)
    free_disk = shutil.disk_usage(staging_root).free
    if free_disk < policy.min_free_disk_bytes:
        raise ProductError("ERR_RESOURCE_LOCAL_DISK_LOW", "free disk is below configured admission floor", ProductErrorCategory.RESOURCE_EXHAUSTED, details={"required_bytes": policy.min_free_disk_bytes, "free_bytes": free_disk})
    return {
        "device_count": len(devices),
        "gpu_device_count": len(gpu_like),
        "max_verified_free_vram_bytes": max(free_values) if free_values else None,
        "free_ram_bytes": int(ram_free) if ram_free is not None else None,
        "free_disk_bytes": free_disk,
    }




def _admit_comfy_input_staging_disk(root: Path, required_copy_bytes: int, policy: ComfyResourcePolicy) -> dict[str, int]:
    if required_copy_bytes < 0:
        raise ValueError("required_copy_bytes must be >= 0")
    free_disk = shutil.disk_usage(root).free
    required = required_copy_bytes + policy.min_free_disk_bytes
    if free_disk < required:
        raise ProductError(
            "ERR_RESOURCE_COMFY_INPUT_DISK_LOW",
            "ComfyUI input root lacks free disk for reference staging plus the configured safety floor",
            ProductErrorCategory.RESOURCE_EXHAUSTED,
            details={"required_copy_bytes": required_copy_bytes, "safety_floor_bytes": policy.min_free_disk_bytes, "required_bytes": required, "free_bytes": free_disk},
        )
    return {"reference_copy_bytes": required_copy_bytes, "input_root_free_disk_bytes": free_disk}

def render_workflow_placeholders(value: Any, substitutions: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {str(k): render_workflow_placeholders(v, substitutions) for k, v in value.items()}
    if isinstance(value, list):
        return [render_workflow_placeholders(v, substitutions) for v in value]
    if isinstance(value, str) and value.startswith("{{") and value.endswith("}}") and value.count("{{") == 1:
        key = value[2:-2]
        if key not in substitutions:
            raise ProductError("ERR_INPUT_COMFY_PLACEHOLDER_MISSING", "workflow placeholder has no supplied value", ProductErrorCategory.VALIDATION, details={"placeholder": key})
        return substitutions[key]
    return value


def workflow_class_types(workflow: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for node in workflow.values():
        if isinstance(node, dict) and isinstance(node.get("class_type"), str):
            result.add(node["class_type"])
    return result


def assert_workflow_supported(workflow: dict[str, Any], object_info: dict[str, Any]) -> None:
    missing = sorted(workflow_class_types(workflow) - set(object_info))
    if missing:
        raise ProductError("ERR_PROVIDER_COMFY_NODE_UNAVAILABLE", "workflow references unavailable ComfyUI node classes", ProductErrorCategory.NOT_SUPPORTED, details={"missing_class_types": missing})


def assert_workflow_inputs_available(workflow: dict[str, Any], object_info: dict[str, Any]) -> None:
    """Validate literal workflow choices (notably model filenames) when object_info proves an enum."""
    for node_id, node in workflow.items():
        if not isinstance(node, dict) or not isinstance(node.get("class_type"), str) or not isinstance(node.get("inputs"), dict):
            continue
        info = object_info.get(node["class_type"])
        if not isinstance(info, dict):
            continue
        input_contract = info.get("input")
        if not isinstance(input_contract, dict):
            continue
        descriptors: dict[str, Any] = {}
        for group in ("required", "optional"):
            values = input_contract.get(group)
            if isinstance(values, dict):
                descriptors.update(values)
        for input_name, supplied in node["inputs"].items():
            descriptor = descriptors.get(input_name)
            if not isinstance(descriptor, (list, tuple)) or not descriptor:
                continue
            first = descriptor[0]
            if not isinstance(first, (list, tuple)) or not first:
                continue
            choices = list(first)
            if not all(isinstance(value, (str, int, float, bool)) for value in choices):
                continue
            if isinstance(supplied, (str, int, float, bool)) and supplied not in choices:
                raise ProductError(
                    "ERR_PROVIDER_COMFY_INPUT_CHOICE_UNAVAILABLE",
                    "workflow references an unavailable ComfyUI enumerated input/model choice",
                    ProductErrorCategory.NOT_SUPPORTED,
                    details={"node_id": str(node_id), "class_type": node["class_type"], "input_name": str(input_name)},
                )


def _history_entry(history: dict[str, Any], prompt_id: str) -> dict[str, Any] | None:
    entry = history.get(prompt_id)
    if isinstance(entry, dict):
        return entry
    # Some wrappers may return the single entry directly.
    if "outputs" in history and isinstance(history.get("outputs"), dict):
        return history
    return None


def _video_descriptors(entry: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if isinstance(value.get("filename"), str):
                filename = value["filename"].lower()
                if Path(filename).suffix in {".mp4", ".mov", ".mkv", ".webm", ".avi"}:
                    found.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(entry.get("outputs", {}))
    return found


def _image_descriptors(entry: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            filename = value.get("filename")
            if isinstance(filename, str) and Path(filename.lower()).suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
                found.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(entry.get("outputs", {}))
    return found


def resolve_comfy_output(root: Path, descriptor: dict[str, Any]) -> Path:
    if descriptor.get("type", "output") != "output":
        raise ProductError("ERR_SECURITY_COMFY_OUTPUT_TYPE", "only ComfyUI output files may become canonical Assets", ProductErrorCategory.SECURITY)
    filename = descriptor.get("filename")
    subfolder = descriptor.get("subfolder", "")
    if (
        not isinstance(filename, str)
        or not filename
        or Path(filename).name != filename
        or "/" in filename
        or "\\" in filename
        or "\x00" in filename
    ):
        raise ProductError("ERR_SECURITY_COMFY_OUTPUT_PATH", "invalid ComfyUI output filename", ProductErrorCategory.SECURITY)
    if not isinstance(subfolder, str) or "\x00" in subfolder:
        raise ProductError("ERR_SECURITY_COMFY_OUTPUT_PATH", "invalid ComfyUI output subfolder", ProductErrorCategory.SECURITY)
    normalized_subfolder = subfolder.replace("\\", "/")
    windows_subfolder = PureWindowsPath(subfolder)
    parts = [] if not normalized_subfolder else normalized_subfolder.split("/")
    if (
        any(part in {"", ".", ".."} for part in parts)
        or PurePosixPath(normalized_subfolder).is_absolute()
        or windows_subfolder.is_absolute()
        or bool(windows_subfolder.drive)
    ):
        raise ProductError("ERR_SECURITY_COMFY_OUTPUT_PATH", "ComfyUI output traversal is forbidden", ProductErrorCategory.SECURITY)
    canonical_root = root.resolve(strict=True)
    candidate = canonical_root.joinpath(*parts, filename)
    if candidate.is_symlink():
        raise ProductError("ERR_SECURITY_COMFY_OUTPUT_SYMLINK", "ComfyUI output symlink is forbidden", ProductErrorCategory.SECURITY)
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(canonical_root)
    except (FileNotFoundError, ValueError) as exc:
        raise ProductError("ERR_SECURITY_COMFY_OUTPUT_ESCAPE", "ComfyUI output is missing or escapes configured output root", ProductErrorCategory.SECURITY) from exc
    if not resolved.is_file():
        raise ProductError("ERR_INPUT_COMFY_OUTPUT_NOT_FILE", "ComfyUI output is not a regular file", ProductErrorCategory.VALIDATION)
    return resolved


def _request_bound_command(base: str, payload: dict[str, Any]) -> str:
    fingerprint = sha256_bytes(canonical_json_bytes(payload)).removeprefix("sha256:")
    return f"{base}:{fingerprint}"


def _queue_or_resume_comfy_prompt(
    *,
    store: SQLiteProductStore,
    operation: OperationRecord,
    client: ComfyUIClient,
    workflow: dict[str, Any],
) -> tuple[OperationRecord, str, bool]:
    if operation.status in {"IN_PROGRESS", "PARTIAL"}:
        if not operation.result_ref:
            raise ProductError(
                "ERR_STATE_COMFY_DISPATCH_UNCERTAIN",
                "prior local-AI operation entered dispatch state without a persisted ComfyUI prompt_id; automatic replay is unsafe",
                ProductErrorCategory.STATE,
                operation_id=operation.operation_id,
            )
        return operation, operation.result_ref, True
    if operation.status == "FAILED" and operation.result_ref:
        return operation, operation.result_ref, True
    operation = store.update_operation_status(operation.operation_id, "IN_PROGRESS", increment_attempt=True)
    prompt_id = client.queue(workflow, client_id=str(uuid.uuid4()))
    operation = store.update_operation_status(operation.operation_id, "IN_PROGRESS", result_ref=prompt_id)
    return operation, prompt_id, False


def _mark_comfy_failure(
    store: SQLiteProductStore, operation: OperationRecord, exc: Exception, *, dispatched: bool
) -> OperationRecord:
    code = exc.code if isinstance(exc, ProductError) else "ERR_INTERNAL_LOCAL_AI_FAILED"
    explicit_provider_failure = isinstance(exc, ProductError) and exc.code in {
        "ERR_PROVIDER_COMFY_EXECUTION_FAILED",
        "ERR_PROVIDER_H3_SINGLE_FRAME_FAILED",
        "ERR_PROVIDER_H3_FOLEY_FAILED",
    }
    status = "FAILED" if (not dispatched or explicit_provider_failure) else "PARTIAL"
    return store.update_operation_status(operation.operation_id, status, last_error_code=code)


@dataclass(frozen=True, slots=True)
class LocalImageGenerationRequest:
    production_job_id: str
    idempotency_key: str
    mode: ImageGenerationMode
    workflow_path: Path
    substitutions: dict[str, Any]
    prompt: str
    seed: int
    authorize_execution: bool
    model_profile: LocalImageModelProfile
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    commercial_runtime_requested: bool = False
    license_authorization_ref: str | None = None
    reference_asset_id: str | None = None
    poll_interval_seconds: float = 1.0
    completion_timeout_seconds: int = 1800


@dataclass(frozen=True, slots=True)
class LocalImageGenerationResult:
    operation: OperationRecord
    asset_id: str
    manifest_uri: str
    evidence_uri: str
    prompt_id: str


class LocalImageGenerationService:
    def __init__(
        self,
        *,
        store: SQLiteProductStore,
        resolver: LogicalPathResolver,
        client: ComfyUIClient,
        workflow_policy: SourcePathPolicy,
        comfy_output_root: Path,
        staging_root: Path,
        comfy_input_root: Path | None = None,
        resource_policy: ComfyResourcePolicy | None = None,
        media_probe: FFprobeMediaProbe | None = None,
    ) -> None:
        self.store = store
        self.resolver = resolver
        self.client = client
        self.workflow_policy = workflow_policy
        self.comfy_output_root = comfy_output_root.resolve(strict=True)
        self.staging_root = staging_root.resolve(strict=False)
        self.comfy_input_root = comfy_input_root.resolve(strict=True) if comfy_input_root is not None else None
        self.resource_policy = resource_policy or ComfyResourcePolicy()
        self.media_probe = media_probe or FFprobeMediaProbe()
        self.publisher = DerivedAssetPublisher(store=store, resolver=resolver)
        self.manifests = Task004ManifestWriter(store=store, resolver=resolver)

    def capability_report(self) -> dict[str, Any]:
        stats = self.client.system_stats()
        info = self.client.object_info()
        return {
            "reachable": True,
            "class_count": len(info),
            "devices": _device_list(stats),
            "provider_profiles": [builtin_image_model_profile(f).to_dict() for f in (
                VisualModelFamily.FLUX_1_SCHNELL, VisualModelFamily.FLUX_1_DEV, VisualModelFamily.SDXL_1_0,
                VisualModelFamily.SD3_5, VisualModelFamily.SD1_5,
            )],
            "executable_modes": [m.value for m in ImageGenerationMode],
            "capability_only_extensions": ["INPAINT", "CONTROLNET", "LORA"],
        }

    def _load_completed(self, request: LocalImageGenerationRequest, operation: OperationRecord) -> LocalImageGenerationResult:
        manifest = self.store.find_manifest_by_operation(operation.operation_id, "local-image-generation-manifest")
        if manifest is None:
            raise ProductError("ERR_INTEGRITY_LOCAL_IMAGE_MANIFEST_MISSING", "completed image generation manifest is missing", ProductErrorCategory.DATA_INTEGRITY)
        doc = self.manifests.load_verified(manifest)
        ids = [a["asset_id"] for a in doc["payload"]["output_assets"]]
        if len(ids) != 1:
            raise ProductError("ERR_INTEGRITY_LOCAL_IMAGE_RESULT", "image generation manifest must reference one output", ProductErrorCategory.DATA_INTEGRITY)
        return LocalImageGenerationResult(operation, ids[0], manifest.uri, f"job://{request.production_job_id}/evidence/task004.jsonl", doc["payload"]["details"].get("prompt_id", ""))

    def _prepare_reference(self, request: LocalImageGenerationRequest, operation: OperationRecord) -> tuple[tuple[str, ...], tuple[str, ...], Path | None, str | None]:
        if request.mode is ImageGenerationMode.TEXT_TO_IMAGE:
            if request.reference_asset_id is not None:
                raise ProductError("ERR_INPUT_IMAGE_REFERENCE_UNEXPECTED", "TEXT_TO_IMAGE must not include a reference Asset", ProductErrorCategory.VALIDATION)
            return (), (), None, None
        if not request.reference_asset_id:
            raise ProductError("ERR_INPUT_IMAGE_REFERENCE_REQUIRED", "IMAGE_TO_IMAGE requires one reference image Asset", ProductErrorCategory.VALIDATION)
        if self.comfy_input_root is None:
            raise ProductError("ERR_PROVIDER_COMFY_INPUT_ROOT_REQUIRED", "IMAGE_TO_IMAGE requires a configured ComfyUI input root", ProductErrorCategory.EXTERNAL_DEPENDENCY)
        asset = self.store.get_asset(request.reference_asset_id)
        if asset.production_job_id != request.production_job_id or asset.asset_type is not AssetType.IMAGE:
            raise ProductError("ERR_INPUT_IMAGE_REFERENCE_SCOPE", "reference Asset must be an IMAGE in the same Job", ProductErrorCategory.SECURITY)
        if not asset.derivative_use_allowed:
            raise ProductError("ERR_AUTH_IMAGE_REFERENCE_DERIVATIVE_RIGHTS", "reference image is not authorized for derivative generation", ProductErrorCategory.AUTHORIZATION)
        source = self.resolver.resolve(asset.logical_uri)
        if not isinstance(source, Path) or not source.exists() or source.is_symlink() or sha256_file(source) != asset.checksum:
            raise ProductError("ERR_INTEGRITY_IMAGE_REFERENCE", "reference image Asset is missing, symlinked, or tampered", ProductErrorCategory.DATA_INTEGRITY)
        _admit_comfy_input_staging_disk(self.comfy_input_root, source.stat().st_size, self.resource_policy)
        relative_dir = Path("bai-task004") / request.production_job_id / operation.operation_id
        target_dir = _prepare_owned_comfy_subdir(self.comfy_input_root, relative_dir)
        try:
            suffix = source.suffix.lower() or ".png"
            target = target_dir / f"reference{suffix}"
            shutil.copyfile(source, target)
            if sha256_file(target) != asset.checksum:
                raise ProductError("ERR_INTEGRITY_IMAGE_REFERENCE_COPY", "reference image copy checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
            relative_name = (relative_dir / target.name).as_posix()
            return (asset.logical_uri,), (asset.checksum,), target_dir, relative_name
        except Exception:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise

    def generate(self, request: LocalImageGenerationRequest) -> LocalImageGenerationResult:
        if not request.authorize_execution:
            raise ProductError("ERR_AUTH_LOCAL_IMAGE_EXECUTION_REQUIRED", "local image generation requires explicit execution authorization", ProductErrorCategory.AUTHORIZATION)
        if not request.prompt.strip() or len(request.prompt) > 20_000 or len(request.negative_prompt) > 20_000:
            raise ProductError("ERR_INPUT_LOCAL_IMAGE_PROMPT", "image generation prompts must be bounded and the positive prompt non-empty", ProductErrorCategory.VALIDATION)
        if request.seed < 0 or request.seed > 2**63 - 1:
            raise ProductError("ERR_INPUT_LOCAL_IMAGE_SEED", "seed out of range", ProductErrorCategory.VALIDATION)
        if not 64 <= request.width <= 8192 or not 64 <= request.height <= 8192:
            raise ProductError("ERR_INPUT_LOCAL_IMAGE_DIMENSIONS", "image dimensions must be between 64 and 8192 pixels", ProductErrorCategory.VALIDATION)
        if not 0.1 <= request.poll_interval_seconds <= 30 or not 1 <= request.completion_timeout_seconds <= 86400:
            raise ValueError("invalid polling timeout configuration")
        if request.model_profile.family is VisualModelFamily.CUSTOM and request.model_profile.license_id == "MODEL-SPECIFIC-REVIEW":
            raise ProductError("ERR_INPUT_CUSTOM_MODEL_LICENSE", "custom model profiles must declare a concrete license policy", ProductErrorCategory.VALIDATION)
        authorize_image_runtime_license(
            request.model_profile,
            commercial_runtime_requested=request.commercial_runtime_requested,
            license_authorization_ref=request.license_authorization_ref,
        )
        workflow_path = self.workflow_policy.authorize_file(request.workflow_path)
        try:
            workflow_raw = _load_workflow_json(workflow_path)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_INPUT_COMFY_WORKFLOW_JSON", "ComfyUI workflow must be valid JSON", ProductErrorCategory.VALIDATION) from exc
        if not isinstance(workflow_raw, dict):
            raise ProductError("ERR_INPUT_COMFY_WORKFLOW_FORMAT", "ComfyUI API workflow must be an object", ProductErrorCategory.VALIDATION)
        request_command = _request_bound_command("LOCAL_IMAGE_GENERATE", {
            "mode": request.mode.value,
            "workflow_checksum": sha256_bytes(canonical_json_bytes(workflow_raw)),
            "substitutions": request.substitutions,
            "prompt_checksum": sha256_bytes(request.prompt.encode("utf-8")),
            "negative_prompt_checksum": sha256_bytes(request.negative_prompt.encode("utf-8")),
            "seed": request.seed, "width": request.width, "height": request.height,
            "model_profile": request.model_profile.to_dict(),
            "commercial_runtime_requested": request.commercial_runtime_requested,
            "license_authorization_ref_checksum": sha256_bytes(request.license_authorization_ref.encode("utf-8")) if request.license_authorization_ref else None,
            "reference_asset_id": request.reference_asset_id,
        })
        operation, _ = self.store.reserve_operation(request.production_job_id, request_command, request.idempotency_key)
        if operation.status == "COMPLETED":
            return self._load_completed(request, operation)

        source_refs: tuple[str, ...] = ()
        source_checksums: tuple[str, ...] = ()
        reference_temp_root: Path | None = None
        reference_name: str | None = None
        dispatched = bool(operation.result_ref)
        try:
            source_refs, source_checksums, reference_temp_root, reference_name = self._prepare_reference(request, operation)
            if _IMAGE_RESERVED_SUBSTITUTIONS.intersection(request.substitutions):
                raise ProductError("ERR_INPUT_COMFY_RESERVED_SUBSTITUTION", "caller substitutions must not override canonical image-generation fields", ProductErrorCategory.VALIDATION, details={"reserved": sorted(_IMAGE_RESERVED_SUBSTITUTIONS.intersection(request.substitutions))})
            substitutions = dict(request.substitutions)
            substitutions["PROMPT"] = request.prompt
            substitutions["NEGATIVE_PROMPT"] = request.negative_prompt
            substitutions["SEED"] = request.seed
            substitutions["WIDTH"] = request.width
            substitutions["HEIGHT"] = request.height
            if reference_name is not None:
                substitutions["REFERENCE_IMAGE"] = reference_name
            workflow = render_workflow_placeholders(workflow_raw, substitutions)
            object_info = self.client.object_info()
            assert_workflow_supported(workflow, object_info)
            assert_workflow_inputs_available(workflow, object_info)
            stats = self.client.system_stats()
            resource = admit_comfy_resources(stats, self.resource_policy, staging_root=self.staging_root)
            operation, prompt_id, _resumed = _queue_or_resume_comfy_prompt(
                store=self.store, operation=operation, client=self.client, workflow=workflow
            )
            dispatched = True
            deadline = time.monotonic() + request.completion_timeout_seconds
            entry: dict[str, Any] | None = None
            while time.monotonic() < deadline:
                history = self.client.history(prompt_id)
                entry = _history_entry(history, prompt_id)
                if entry is not None:
                    status = entry.get("status")
                    if isinstance(status, dict) and str(status.get("status_str", "")).lower() in {"error", "failed"}:
                        raise ProductError("ERR_PROVIDER_COMFY_EXECUTION_FAILED", "ComfyUI workflow reported failure", ProductErrorCategory.EXTERNAL_DEPENDENCY)
                    images = _image_descriptors(entry)
                    if images:
                        break
                time.sleep(request.poll_interval_seconds)
            else:
                raise ProductError("ERR_PROVIDER_COMFY_GENERATION_TIMEOUT", "ComfyUI generation did not complete before deadline", ProductErrorCategory.TIMEOUT, retryable=True)
            assert entry is not None
            images = _image_descriptors(entry)
            if not images:
                raise ProductError("ERR_PROVIDER_COMFY_IMAGE_MISSING", "ComfyUI history did not contain an image output", ProductErrorCategory.DATA_INTEGRITY)
            if len(images) > 1:
                raise ProductError("ERR_PROVIDER_COMFY_IMAGE_AMBIGUOUS", "ComfyUI history contains multiple image outputs; select a workflow with one canonical output", ProductErrorCategory.HUMAN_REVIEW_REQUIRED, details={"image_count": len(images)})
            output = resolve_comfy_output(self.comfy_output_root, images[0])
            probe = self.media_probe.probe(output)
            video_streams = [stream for stream in probe.streams if stream.get("codec_type") == "video"]
            if not video_streams or not all(int(stream.get("width", 0)) > 0 and int(stream.get("height", 0)) > 0 for stream in video_streams):
                raise ProductError("ERR_INTEGRITY_COMFY_OUTPUT_NOT_IMAGE", "ComfyUI image output is not structurally visual", ProductErrorCategory.DATA_INTEGRITY)
            workflow_checksum = sha256_bytes(canonical_json_bytes(workflow_raw))
            rendered_workflow_checksum = sha256_bytes(canonical_json_bytes(workflow))
            prompt_checksum = sha256_bytes(request.prompt.encode("utf-8"))
            negative_prompt_checksum = sha256_bytes(request.negative_prompt.encode("utf-8"))
            license_ref_checksum = sha256_bytes(request.license_authorization_ref.encode("utf-8")) if request.license_authorization_ref else None
            provenance = {
                "provider": "COMFYUI_LOCAL",
                "profile": request.model_profile.profile_name,
                "model_family": request.model_profile.family.value,
                "model_identifier": request.model_profile.model_identifier,
                "model_license_id": request.model_profile.license_id,
                "runtime_license_state": request.model_profile.runtime_license_state.value,
                "commercial_runtime_requested": request.commercial_runtime_requested,
                "license_authorization_ref_checksum": license_ref_checksum,
                "mode": request.mode.value,
                "workflow_checksum": workflow_checksum,
                "rendered_workflow_checksum": rendered_workflow_checksum,
                "prompt_checksum": prompt_checksum,
                "negative_prompt_checksum": negative_prompt_checksum,
                "seed": request.seed,
                "width": request.width,
                "height": request.height,
                "reference_asset_id": request.reference_asset_id,
            }
            asset = self.publisher.publish(
                output,
                DerivedAssetSpec(
                    production_job_id=request.production_job_id, namespace="generated-image", asset_type=AssetType.IMAGE,
                    owner="LOCAL_AI_OUTPUT", rights_status=RightsStatus.UNKNOWN, commercial_use=PermissionState.UNKNOWN,
                    derivative_allowed=PermissionState.UNKNOWN, reuse_allowed=PermissionState.UNKNOWN,
                    audio_rights_status=AudioRightsStatus.NOT_APPLICABLE, generation_provenance=provenance,
                    source_ref=request.reference_asset_id, media_metadata=probe.to_dict(),
                    publication_restrictions=("RIGHTS_REVIEW_REQUIRED",),
                ),
                operation_id=operation.operation_id,
            )
            details = dict(provenance)
            details.update({"prompt_id": prompt_id, "resource_admission": resource, "output_binding": {"asset_id": asset.asset_id, "checksum": asset.checksum}})
            input_checksums = (workflow_checksum, rendered_workflow_checksum, prompt_checksum, negative_prompt_checksum, *source_checksums)
            manifest = self.manifests.write(
                job_id=request.production_job_id, operation_id=operation.operation_id,
                manifest_type="local-image-generation-manifest", schema_id="ai-video.local-image-generation-manifest",
                lane="LOCAL_IMAGE_AI", operation_kind=request.mode.value,
                source_refs=source_refs, input_checksums=input_checksums, output_assets=(asset,), details=details,
                evidence_category="LOCAL_IMAGE_GENERATION", producer_component="comfyui-local-image-adapter",
            )
            operation = self.store.update_operation_status(operation.operation_id, "COMPLETED", result_ref=asset.asset_id)
            return LocalImageGenerationResult(operation, asset.asset_id, manifest.manifest.uri, manifest.evidence_uri, prompt_id)
        except Exception as exc:
            _mark_comfy_failure(self.store, operation, exc, dispatched=dispatched)
            if isinstance(exc, ProductError):
                raise
            raise ProductError("ERR_INTERNAL_LOCAL_IMAGE_GENERATION_FAILED", "local image generation failed unexpectedly", ProductErrorCategory.INTERNAL, operation_id=operation.operation_id) from exc
        finally:
            if reference_temp_root is not None:
                shutil.rmtree(reference_temp_root, ignore_errors=True)


@dataclass(frozen=True, slots=True)
class LocalVideoGenerationRequest:
    production_job_id: str
    idempotency_key: str
    mode: VideoGenerationMode
    workflow_path: Path
    substitutions: dict[str, Any]
    prompt: str
    seed: int
    authorize_execution: bool
    profile_name: str = "minimax-h3-native"
    model_family: str = "MiniMax-H3"
    model_identifier: str = "MiniMaxAI/MiniMax-H3"
    model_license_id: str = "MiniMax-H3-Community-License-Agreement"
    runtime_license_state: RuntimeLicenseState = RuntimeLicenseState.CONDITIONAL
    license_authorization_ref: str | None = None
    reference_bindings: dict[str, str] | None = None
    poll_interval_seconds: float = 1.0
    completion_timeout_seconds: int = 3600
    acceleration_mode: H3AccelerationMode = H3AccelerationMode.NATIVE


@dataclass(frozen=True, slots=True)
class LocalVideoGenerationResult:
    operation: OperationRecord
    asset_id: str
    manifest_uri: str
    evidence_uri: str
    prompt_id: str


class LocalVideoGenerationService:
    def __init__(
        self,
        *,
        store: SQLiteProductStore,
        resolver: LogicalPathResolver,
        client: ComfyUIClient,
        workflow_policy: SourcePathPolicy,
        comfy_output_root: Path,
        staging_root: Path,
        comfy_input_root: Path | None = None,
        resource_policy: ComfyResourcePolicy | None = None,
        media_probe: FFprobeMediaProbe | None = None,
    ) -> None:
        self.store = store
        self.resolver = resolver
        self.client = client
        self.workflow_policy = workflow_policy
        self.comfy_output_root = comfy_output_root.resolve(strict=True)
        self.staging_root = staging_root.resolve(strict=False)
        self.comfy_input_root = comfy_input_root.resolve(strict=True) if comfy_input_root is not None else None
        self.resource_policy = resource_policy or ComfyResourcePolicy()
        self.media_probe = media_probe or FFprobeMediaProbe()
        self.publisher = DerivedAssetPublisher(store=store, resolver=resolver)
        self.manifests = Task004ManifestWriter(store=store, resolver=resolver)

    def capability_report(self) -> dict[str, Any]:
        stats = self.client.system_stats()
        info = self.client.object_info()
        return {
            "reachable": True,
            "class_count": len(info),
            "devices": _device_list(stats),
            "provider_profiles": [
                {
                    "profile_name": "minimax-h3-native",
                    "model_family": "MiniMax-H3",
                    "model_identifier": "MiniMaxAI/MiniMax-H3",
                    "license_id": "MiniMax-H3-Community-License-Agreement",
                    "runtime_license_state": RuntimeLicenseState.CONDITIONAL.value,
                },
                {"profile_name": "minimax-h3-easy-compatible", "compatibility_only": True},
            ],
            "executable_modes": [m.value for m in VideoGenerationMode],
            "acceleration_profiles": [m.value for m in H3AccelerationMode],
            "spectrum_class_available": SPECTRUM_CLASS_TYPE in info,
        }

    def _prepare_references(
        self, request: LocalVideoGenerationRequest, operation: OperationRecord
    ) -> tuple[tuple[str, ...], tuple[str, ...], Path | None, dict[str, str]]:
        bindings = dict(request.reference_bindings or {})
        if request.mode is VideoGenerationMode.TEXT_TO_VIDEO:
            if bindings:
                raise ProductError("ERR_INPUT_VIDEO_REFERENCE_UNEXPECTED", "TEXT_TO_VIDEO must not include reference Assets", ProductErrorCategory.VALIDATION)
            return (), (), None, {}
        if not bindings:
            raise ProductError("ERR_INPUT_VIDEO_REFERENCE_REQUIRED", "selected video generation mode requires reference Assets", ProductErrorCategory.VALIDATION)
        if self.comfy_input_root is None:
            raise ProductError("ERR_PROVIDER_COMFY_INPUT_ROOT_REQUIRED", "reference video generation requires a configured ComfyUI input root", ProductErrorCategory.EXTERNAL_DEPENDENCY)
        if len(bindings) > 15:
            raise ProductError("ERR_INPUT_VIDEO_REFERENCE_COUNT", "video reference count exceeds TASK-004 safety limit", ProductErrorCategory.VALIDATION)
        if _VIDEO_RESERVED_SUBSTITUTIONS.intersection(bindings):
            raise ProductError("ERR_INPUT_COMFY_RESERVED_SUBSTITUTION", "reference placeholders must not override canonical video-generation fields", ProductErrorCategory.VALIDATION)
        for placeholder in bindings:
            _bounded_reference_placeholder(placeholder)
        assets = []
        for placeholder, asset_id in sorted(bindings.items()):
            asset = self.store.get_asset(asset_id)
            if asset.production_job_id != request.production_job_id:
                raise ProductError("ERR_SECURITY_VIDEO_REFERENCE_SCOPE", "video reference Asset belongs to another Job", ProductErrorCategory.SECURITY)
            assets.append((placeholder, asset))
        image_types = {AssetType.IMAGE}
        reference_types = {AssetType.IMAGE, AssetType.VIDEO, AssetType.GENERATED_VIDEO, AssetType.AUDIO, AssetType.BGM, AssetType.SFX}
        if request.mode is VideoGenerationMode.IMAGE_TO_VIDEO:
            if not (1 <= len(assets) <= 2) or any(asset.asset_type not in image_types for _, asset in assets):
                raise ProductError("ERR_INPUT_VIDEO_REFERENCE_MODE", "IMAGE_TO_VIDEO requires one or two IMAGE Assets", ProductErrorCategory.VALIDATION)
        elif request.mode is VideoGenerationMode.FIRST_LAST:
            if len(assets) != 2 or any(asset.asset_type not in image_types for _, asset in assets):
                raise ProductError("ERR_INPUT_VIDEO_REFERENCE_MODE", "FIRST_LAST requires exactly two IMAGE Assets", ProductErrorCategory.VALIDATION)
        elif request.mode is VideoGenerationMode.REFERENCE:
            if any(asset.asset_type not in reference_types for _, asset in assets):
                raise ProductError("ERR_INPUT_VIDEO_REFERENCE_MODE", "REFERENCE mode received an unsupported reference Asset type", ProductErrorCategory.VALIDATION)
        verified_sources: list[tuple[str, Any, Path]] = []
        required_copy_bytes = 0
        for placeholder, asset in assets:
            if not asset.derivative_use_allowed:
                raise ProductError("ERR_AUTH_VIDEO_REFERENCE_DERIVATIVE_RIGHTS", "video reference Asset is not authorized for derivative generation", ProductErrorCategory.AUTHORIZATION, details={"asset_id": asset.asset_id})
            source = self.resolver.resolve(asset.logical_uri)
            if not isinstance(source, Path) or not source.exists() or source.is_symlink() or sha256_file(source) != asset.checksum:
                raise ProductError("ERR_INTEGRITY_VIDEO_REFERENCE", "video reference Asset is missing, symlinked, or tampered", ProductErrorCategory.DATA_INTEGRITY, details={"asset_id": asset.asset_id})
            required_copy_bytes += source.stat().st_size
            verified_sources.append((placeholder, asset, source))
        _admit_comfy_input_staging_disk(self.comfy_input_root, required_copy_bytes, self.resource_policy)
        relative_dir = Path("bai-task004-video") / request.production_job_id / operation.operation_id
        target_dir = _prepare_owned_comfy_subdir(self.comfy_input_root, relative_dir)
        try:
            source_refs: list[str] = []
            source_checksums: list[str] = []
            substitutions: dict[str, str] = {}
            for index, (placeholder, asset, source) in enumerate(verified_sources, start=1):
                suffix = source.suffix.lower() if source.suffix else ".bin"
                safe_name = f"ref-{index:02d}-{placeholder.lower()}{suffix}"
                target = target_dir / safe_name
                shutil.copyfile(source, target)
                if sha256_file(target) != asset.checksum:
                    raise ProductError("ERR_INTEGRITY_VIDEO_REFERENCE_COPY", "video reference copy checksum mismatch", ProductErrorCategory.DATA_INTEGRITY, details={"asset_id": asset.asset_id})
                source_refs.append(asset.logical_uri)
                source_checksums.append(asset.checksum)
                substitutions[placeholder] = (relative_dir / safe_name).as_posix()
            return tuple(source_refs), tuple(source_checksums), target_dir, substitutions
        except Exception:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise

    def generate(self, request: LocalVideoGenerationRequest) -> LocalVideoGenerationResult:
        if not request.authorize_execution:
            raise ProductError("ERR_AUTH_LOCAL_VIDEO_EXECUTION_REQUIRED", "local video generation requires explicit execution authorization", ProductErrorCategory.AUTHORIZATION)
        if not request.prompt.strip() or len(request.prompt) > 20_000:
            raise ProductError("ERR_INPUT_LOCAL_VIDEO_PROMPT", "generation prompt must be non-empty and bounded", ProductErrorCategory.VALIDATION)
        if request.seed < 0 or request.seed > 2**63 - 1:
            raise ProductError("ERR_INPUT_LOCAL_VIDEO_SEED", "seed out of range", ProductErrorCategory.VALIDATION)
        if not 0.1 <= request.poll_interval_seconds <= 30 or not 1 <= request.completion_timeout_seconds <= 86400:
            raise ValueError("invalid polling timeout configuration")
        for value, field_name in ((request.profile_name, "profile_name"), (request.model_family, "model_family"), (request.model_identifier, "model_identifier"), (request.model_license_id, "model_license_id")):
            if not value.strip() or "\x00" in value or len(value) > 500:
                raise ProductError("ERR_INPUT_VIDEO_MODEL_PROFILE", f"{field_name} is invalid", ProductErrorCategory.VALIDATION)
        license_ref = _validate_license_authorization_ref(request.license_authorization_ref)
        if request.runtime_license_state is not RuntimeLicenseState.ALLOWED and not license_ref:
            raise ProductError(
                "ERR_AUTH_VIDEO_MODEL_RUNTIME_LICENSE",
                "video model execution requires explicit license acknowledgement/authorization for this conditional or restricted profile",
                ProductErrorCategory.AUTHORIZATION,
                details={
                    "model_family": request.model_family,
                    "license_id": request.model_license_id,
                    "runtime_license_state": request.runtime_license_state.value,
                },
            )
        if _VIDEO_RESERVED_SUBSTITUTIONS.intersection(request.substitutions):
            raise ProductError("ERR_INPUT_COMFY_RESERVED_SUBSTITUTION", "caller substitutions must not override canonical video-generation fields", ProductErrorCategory.VALIDATION, details={"reserved": sorted(_VIDEO_RESERVED_SUBSTITUTIONS.intersection(request.substitutions))})
        workflow_path = self.workflow_policy.authorize_file(request.workflow_path)
        try:
            workflow_raw = _load_workflow_json(workflow_path)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_INPUT_COMFY_WORKFLOW_JSON", "ComfyUI workflow must be valid JSON", ProductErrorCategory.VALIDATION) from exc
        if not isinstance(workflow_raw, dict):
            raise ProductError("ERR_INPUT_COMFY_WORKFLOW_FORMAT", "ComfyUI API workflow must be an object", ProductErrorCategory.VALIDATION)
        request_command = _request_bound_command("LOCAL_VIDEO_GENERATE", {
            "mode": request.mode.value,
            "workflow_checksum": sha256_bytes(canonical_json_bytes(workflow_raw)),
            "substitutions": request.substitutions,
            "prompt_checksum": sha256_bytes(request.prompt.encode("utf-8")),
            "seed": request.seed,
            "profile_name": request.profile_name, "model_family": request.model_family,
            "model_identifier": request.model_identifier, "model_license_id": request.model_license_id,
            "runtime_license_state": request.runtime_license_state.value,
            "license_authorization_ref_checksum": sha256_bytes(license_ref.encode("utf-8")) if license_ref else None,
            "reference_bindings": request.reference_bindings or {},
            "acceleration_mode": request.acceleration_mode.value,
        })
        operation, _ = self.store.reserve_operation(request.production_job_id, request_command, request.idempotency_key)
        if operation.status == "COMPLETED":
            manifest = self.store.find_manifest_by_operation(operation.operation_id, "local-video-generation-manifest")
            if manifest is None:
                raise ProductError("ERR_INTEGRITY_LOCAL_VIDEO_MANIFEST_MISSING", "completed video generation manifest is missing", ProductErrorCategory.DATA_INTEGRITY)
            doc = self.manifests.load_verified(manifest)
            ids = [a["asset_id"] for a in doc["payload"]["output_assets"]]
            if len(ids) != 1:
                raise ProductError("ERR_INTEGRITY_LOCAL_VIDEO_RESULT", "video generation manifest must reference one output", ProductErrorCategory.DATA_INTEGRITY)
            return LocalVideoGenerationResult(operation, ids[0], manifest.uri, f"job://{request.production_job_id}/evidence/task004.jsonl", doc["payload"]["details"].get("prompt_id", ""))

        source_refs: tuple[str, ...] = ()
        source_checksums: tuple[str, ...] = ()
        reference_temp_root: Path | None = None
        prompt_id = ""
        dispatched = bool(operation.result_ref)
        try:
            source_refs, source_checksums, reference_temp_root, reference_substitutions = self._prepare_references(request, operation)
            substitutions = dict(request.substitutions)
            substitutions.update(reference_substitutions)
            substitutions["PROMPT"] = request.prompt
            substitutions["SEED"] = request.seed
            workflow = render_workflow_placeholders(workflow_raw, substitutions)
            acceleration = H3AccelerationContract(request.acceleration_mode).validate_workflow(
                workflow, configured_vram_floor_bytes=self.resource_policy.min_free_vram_bytes
            )
            object_info = self.client.object_info()
            assert_workflow_supported(workflow, object_info)
            assert_workflow_inputs_available(workflow, object_info)
            stats = self.client.system_stats()
            resource = admit_comfy_resources(stats, self.resource_policy, staging_root=self.staging_root)
            operation, prompt_id, _resumed = _queue_or_resume_comfy_prompt(
                store=self.store, operation=operation, client=self.client, workflow=workflow
            )
            dispatched = True
            deadline = time.monotonic() + request.completion_timeout_seconds
            entry: dict[str, Any] | None = None
            while time.monotonic() < deadline:
                history = self.client.history(prompt_id)
                entry = _history_entry(history, prompt_id)
                if entry is not None:
                    status = entry.get("status")
                    if isinstance(status, dict) and str(status.get("status_str", "")).lower() in {"error", "failed"}:
                        raise ProductError("ERR_PROVIDER_COMFY_EXECUTION_FAILED", "ComfyUI workflow reported failure", ProductErrorCategory.EXTERNAL_DEPENDENCY)
                    videos = _video_descriptors(entry)
                    if videos:
                        break
                time.sleep(request.poll_interval_seconds)
            else:
                raise ProductError("ERR_PROVIDER_COMFY_GENERATION_TIMEOUT", "ComfyUI generation did not complete before deadline", ProductErrorCategory.TIMEOUT, retryable=True)
            assert entry is not None
            videos = _video_descriptors(entry)
            if not videos:
                raise ProductError("ERR_PROVIDER_COMFY_VIDEO_MISSING", "ComfyUI history did not contain a video output", ProductErrorCategory.DATA_INTEGRITY)
            if len(videos) > 1:
                raise ProductError("ERR_PROVIDER_COMFY_VIDEO_AMBIGUOUS", "ComfyUI history contains multiple video outputs; select a workflow with one canonical output", ProductErrorCategory.HUMAN_REVIEW_REQUIRED, details={"video_count": len(videos)})
            output = resolve_comfy_output(self.comfy_output_root, videos[0])
            probe = self.media_probe.probe(output)
            if not probe.has_video:
                raise ProductError("ERR_INTEGRITY_COMFY_OUTPUT_NOT_VIDEO", "ComfyUI output does not contain a video stream", ProductErrorCategory.DATA_INTEGRITY)
            workflow_checksum = sha256_bytes(canonical_json_bytes(workflow_raw))
            rendered_workflow_checksum = sha256_bytes(canonical_json_bytes(workflow))
            prompt_checksum = sha256_bytes(request.prompt.encode("utf-8"))
            license_ref_checksum = sha256_bytes(license_ref.encode("utf-8")) if license_ref else None
            provenance = {
                "provider": "COMFYUI_LOCAL",
                "profile": request.profile_name,
                "model_family": request.model_family,
                "model_identifier": request.model_identifier,
                "model_license_id": request.model_license_id,
                "runtime_license_state": request.runtime_license_state.value,
                "license_authorization_ref_checksum": license_ref_checksum,
                "mode": request.mode.value,
                "workflow_checksum": workflow_checksum,
                "rendered_workflow_checksum": rendered_workflow_checksum,
                "prompt_checksum": prompt_checksum,
                "seed": request.seed,
                "reference_asset_ids": sorted((request.reference_bindings or {}).values()),
                "acceleration": acceleration,
            }
            restrictions = ["RIGHTS_REVIEW_REQUIRED"]
            if request.acceleration_mode is not H3AccelerationMode.NATIVE:
                restrictions.append("ACCELERATOR_OUTPUT_QA_REQUIRED")
            if request.runtime_license_state is not RuntimeLicenseState.ALLOWED:
                restrictions.extend(["MODEL_LICENSE_REVIEW_REQUIRED", "MODEL_LICENSE_TERRITORY_REVIEW"] )
            asset = self.publisher.publish(
                output,
                DerivedAssetSpec(
                    production_job_id=request.production_job_id,
                    namespace="generated-video",
                    asset_type=AssetType.GENERATED_VIDEO,
                    owner="LOCAL_AI_OUTPUT",
                    rights_status=RightsStatus.UNKNOWN,
                    commercial_use=PermissionState.UNKNOWN,
                    derivative_allowed=PermissionState.UNKNOWN,
                    reuse_allowed=PermissionState.UNKNOWN,
                    audio_rights_status=AudioRightsStatus.REVIEW if probe.has_audio else AudioRightsStatus.NOT_APPLICABLE,
                    generation_provenance=provenance,
                    media_metadata=probe.to_dict(),
                    source_ref=(next(iter((request.reference_bindings or {}).values())) if len(request.reference_bindings or {}) == 1 else None),
                    publication_restrictions=tuple(restrictions),
                ),
                operation_id=operation.operation_id,
            )
            details = dict(provenance)
            details.update({
                "prompt_id": prompt_id,
                "resource_admission": resource,
                "reference_bindings": [
                    {"placeholder": key, "asset_id": value}
                    for key, value in sorted((request.reference_bindings or {}).items())
                ],
                "output_binding": {"asset_id": asset.asset_id, "checksum": asset.checksum},
            })
            manifest = self.manifests.write(
                job_id=request.production_job_id, operation_id=operation.operation_id,
                manifest_type="local-video-generation-manifest", schema_id="ai-video.local-video-generation-manifest",
                lane="LOCAL_VIDEO_AI", operation_kind=request.mode.value,
                source_refs=source_refs, input_checksums=(workflow_checksum, rendered_workflow_checksum, prompt_checksum, *source_checksums), output_assets=(asset,),
                details=details, evidence_category="LOCAL_VIDEO_GENERATION", producer_component="comfyui-local-video-adapter",
            )
            operation = self.store.update_operation_status(operation.operation_id, "COMPLETED", result_ref=asset.asset_id)
            return LocalVideoGenerationResult(operation, asset.asset_id, manifest.manifest.uri, manifest.evidence_uri, prompt_id)
        except Exception as exc:
            _mark_comfy_failure(self.store, operation, exc, dispatched=dispatched)
            if isinstance(exc, ProductError):
                raise
            raise ProductError("ERR_INTERNAL_LOCAL_VIDEO_GENERATION_FAILED", "local video generation failed unexpectedly", ProductErrorCategory.INTERNAL, operation_id=operation.operation_id) from exc
        finally:
            if reference_temp_root is not None:
                shutil.rmtree(reference_temp_root, ignore_errors=True)
