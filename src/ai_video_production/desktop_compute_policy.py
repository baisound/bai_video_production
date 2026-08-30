"""Canonical TASK-066 compute policy, registries and profile persistence."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass, replace
from enum import Enum
from importlib.resources import files
import json
import os
from pathlib import Path
import re
import stat
import threading
import time
from typing import Any, Iterable, Mapping

from .atomic import AtomicJsonWriter, FailureInjector
from .desktop_install_layout import DesktopInstallLayout
from .schema_contracts import validate_instance
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso


PROFILE_SCHEMA_VERSION = "1.0.0"
WORKLOAD_REGISTRY_SCHEMA_VERSION = "1.0.0"
RENDERER_REGISTRY_SCHEMA_VERSION = "1.0.0"
PROFILE_MESSAGE_TYPE = "BvpDesktopComputeProfile"
WORKLOAD_REGISTRY_MESSAGE_TYPE = "BvpDesktopComputeWorkloadRegistry"
RENDERER_REGISTRY_MESSAGE_TYPE = "BvpDesktopRendererEvidenceRegistry"
PROFILE_LOCK_TIMEOUT_SECONDS = 2.0
_MAX_PROFILE_BYTES = 1024 * 1024
_REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,95}$")


class DesktopComputePolicyError(ValueError):
    """Compute policy or persisted profile is invalid."""


class ComputePreference(str, Enum):
    AUTO_GPU_FIRST = "AUTO_GPU_FIRST"
    GPU_REQUIRED = "GPU_REQUIRED"
    CPU_EXPLICIT = "CPU_EXPLICIT"


class WorkloadClass(str, Enum):
    GPU_REQUIRED = "GPU_REQUIRED"
    GPU_PREFERRED_CPU_ALLOWED = "GPU_PREFERRED_CPU_ALLOWED"
    CPU_ONLY = "CPU_ONLY"


class CompatibilityStatus(str, Enum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ProfileLoadStatus(str, Enum):
    LOADED = "LOADED"
    DEFAULT_MISSING = "DEFAULT_MISSING"
    DEFAULT_REJECTED = "DEFAULT_REJECTED"


@dataclass(frozen=True, slots=True)
class CapabilityAdmissionReceipt:
    registry_revision: int
    registry_sha256: str
    probe_id: str
    workload_id: str
    backend: str
    adapter_identity_sha256: str
    runtime_inventory_sha256: str
    runtime_versions_sha256: str
    helper_sha256: str
    command_sha256: str
    consumer_process_pid: int
    probe_process_pid: int
    receipt_sha256: str

    def body(self) -> dict[str, object]:
        return {
            "registry_revision": self.registry_revision,
            "registry_sha256": self.registry_sha256,
            "probe_id": self.probe_id,
            "workload_id": self.workload_id,
            "backend": self.backend,
            "adapter_identity_sha256": self.adapter_identity_sha256,
            "runtime_inventory_sha256": self.runtime_inventory_sha256,
            "runtime_versions_sha256": self.runtime_versions_sha256,
            "helper_sha256": self.helper_sha256,
            "command_sha256": self.command_sha256,
            "consumer_process_pid": self.consumer_process_pid,
            "probe_process_pid": self.probe_process_pid,
        }

    def __post_init__(self) -> None:
        for value in (
            self.registry_sha256,
            self.adapter_identity_sha256,
            self.runtime_inventory_sha256,
            self.runtime_versions_sha256,
            self.helper_sha256,
            self.command_sha256,
            self.receipt_sha256,
        ):
            if re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None:
                raise DesktopComputePolicyError("capability receipt digest is invalid")
        if self.receipt_sha256 != sha256_bytes(canonical_json_bytes(self.body())):
            raise DesktopComputePolicyError("capability receipt self-hash mismatch")
        if self.consumer_process_pid <= 0 or self.probe_process_pid <= 0:
            raise DesktopComputePolicyError("capability receipt process identity is invalid")


@dataclass(frozen=True, slots=True)
class AdapterIdentity:
    luid: str
    vendor_id: str
    device_id: str
    subsystem_id: str
    driver_instance_digest: str

    def __post_init__(self) -> None:
        for label, value in (
            ("luid", self.luid),
            ("vendor_id", self.vendor_id),
            ("device_id", self.device_id),
            ("subsystem_id", self.subsystem_id),
        ):
            if not value or len(value) > 128:
                raise DesktopComputePolicyError(f"{label} is invalid")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", self.driver_instance_digest):
            raise DesktopComputePolicyError("driver instance digest is invalid")

    @property
    def stable_key(self) -> str:
        return "|".join(
            (
                self.luid,
                self.vendor_id,
                self.device_id,
                self.subsystem_id,
                self.driver_instance_digest,
            )
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "luid": self.luid,
            "vendor_id": self.vendor_id,
            "device_id": self.device_id,
            "subsystem_id": self.subsystem_id,
            "driver_instance_digest": self.driver_instance_digest,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AdapterIdentity":
        return cls(
            luid=value["luid"],
            vendor_id=value["vendor_id"],
            device_id=value["device_id"],
            subsystem_id=value["subsystem_id"],
            driver_instance_digest=value["driver_instance_digest"],
        )


@dataclass(frozen=True, slots=True)
class AdapterCapability:
    backend: str
    device_kind: str
    identity: AdapterIdentity | None
    supported_workloads: frozenset[str]
    implemented: bool
    compatible: bool
    discrete: bool = False
    dedicated_memory_bytes: int = 0
    reason_code: str = "CAPABILITY_REPORTED"
    current_bind_verified: bool = False
    loaded_runtime_versions: tuple[str, ...] = ()
    admission_receipt: CapabilityAdmissionReceipt | None = None
    runtime_inventory_sha256: str | None = None
    live_admission_token: object | None = None

    def __post_init__(self) -> None:
        if self.device_kind not in {"GPU", "CPU"}:
            raise DesktopComputePolicyError("device_kind is invalid")
        if not self.backend or len(self.backend) > 128:
            raise DesktopComputePolicyError("backend is invalid")
        if self.device_kind == "GPU" and self.identity is None:
            raise DesktopComputePolicyError("GPU capability requires stable identity")
        if self.device_kind == "CPU" and (self.discrete or self.dedicated_memory_bytes):
            raise DesktopComputePolicyError("CPU capability cannot claim GPU properties")
        if self.dedicated_memory_bytes < 0:
            raise DesktopComputePolicyError("dedicated memory is invalid")
        if self.device_kind == "GPU" and self.implemented and self.compatible and not self.loaded_runtime_versions:
            raise DesktopComputePolicyError("compatible GPU capability requires loaded runtime identity")
        if any(not value or len(value) > 160 for value in self.loaded_runtime_versions):
            raise DesktopComputePolicyError("loaded runtime version is invalid")
        if self.runtime_inventory_sha256 is not None and re.fullmatch(
            r"sha256:[0-9a-f]{64}", self.runtime_inventory_sha256
        ) is None:
            raise DesktopComputePolicyError("runtime inventory digest is invalid")
        _require_reason(self.reason_code)


@dataclass(frozen=True, slots=True)
class EffectiveWorkloadRoute:
    workload_id: str
    workload_class: WorkloadClass
    effective_backend: str
    adapter_identity: AdapterIdentity | None
    reason_code: str
    compatibility_status: CompatibilityStatus
    loaded_runtime_versions: tuple[str, ...] = ()
    restart_required: bool = False
    cpu_fallback_visible_before_execution: bool = False
    capability_admission_receipt: CapabilityAdmissionReceipt | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "workload_id": self.workload_id,
            "workload_class": self.workload_class.value,
            "effective_backend": self.effective_backend,
            "adapter_identity": (
                None if self.adapter_identity is None else self.adapter_identity.to_dict()
            ),
            "reason_code": self.reason_code,
            "compatibility_status": self.compatibility_status.value,
            "loaded_runtime_versions": list(self.loaded_runtime_versions),
            "restart_required": self.restart_required,
            "cpu_fallback_visible_before_execution": self.cpu_fallback_visible_before_execution,
            "capability_admission_receipt": (
                None
                if self.capability_admission_receipt is None
                else {
                    **self.capability_admission_receipt.body(),
                    "receipt_sha256": self.capability_admission_receipt.receipt_sha256,
                }
            ),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EffectiveWorkloadRoute":
        identity = value["adapter_identity"]
        receipt_value = value["capability_admission_receipt"]
        return cls(
            workload_id=value["workload_id"],
            workload_class=WorkloadClass(value["workload_class"]),
            effective_backend=value["effective_backend"],
            adapter_identity=(None if identity is None else AdapterIdentity.from_dict(identity)),
            reason_code=value["reason_code"],
            compatibility_status=CompatibilityStatus(value["compatibility_status"]),
            loaded_runtime_versions=tuple(value["loaded_runtime_versions"]),
            restart_required=value["restart_required"],
            cpu_fallback_visible_before_execution=value[
                "cpu_fallback_visible_before_execution"
            ],
            capability_admission_receipt=(
                None
                if receipt_value is None
                else CapabilityAdmissionReceipt(**receipt_value)
            ),
        )


@dataclass(frozen=True, slots=True)
class DesktopComputeProfile:
    install_instance_id: str
    revision: int
    selected_preference: ComputePreference
    workload_routes: tuple[EffectiveWorkloadRoute, ...]
    updated_at: str

    @classmethod
    def default(cls, install_instance_id: str) -> "DesktopComputeProfile":
        return cls(
            install_instance_id=install_instance_id,
            revision=0,
            selected_preference=ComputePreference.AUTO_GPU_FIRST,
            workload_routes=(),
            updated_at="IN_MEMORY_DEFAULT",
        )

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema_version": PROFILE_SCHEMA_VERSION,
            "message_type": PROFILE_MESSAGE_TYPE,
            "product_id": "BAI_VIDEO_PRODUCTION",
            "install_instance_id": self.install_instance_id,
            "revision": self.revision,
            "selected_preference": self.selected_preference.value,
            "workload_routes": [item.to_dict() for item in self.workload_routes],
            "updated_at": self.updated_at,
        }
        document = dict(body)
        document["document_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return document

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "DesktopComputeProfile":
        value = dict(document)
        _validate_resource(value, "desktop-compute-profile.schema.json")
        if value["schema_version"] != PROFILE_SCHEMA_VERSION:
            raise DesktopComputePolicyError("compute profile version mismatch")
        body = dict(value)
        supplied = body.pop("document_sha256")
        if supplied != sha256_bytes(canonical_json_bytes(body)):
            raise DesktopComputePolicyError("compute profile digest mismatch")
        routes = tuple(EffectiveWorkloadRoute.from_dict(item) for item in value["workload_routes"])
        if len({item.workload_id for item in routes}) != len(routes):
            raise DesktopComputePolicyError("duplicate workload route")
        registry = {
            item["workload_id"]: item
            for item in frozen_workload_registry()["workloads"]
        }
        registry_ids = set(registry)
        if not {item.workload_id for item in routes}.issubset(registry_ids):
            raise DesktopComputePolicyError("profile contains an unknown workload")
        preference = ComputePreference(value["selected_preference"])
        for route in routes:
            _validate_persisted_route(route, preference, registry[route.workload_id])
        return cls(
            install_instance_id=value["install_instance_id"],
            revision=value["revision"],
            selected_preference=preference,
            workload_routes=routes,
            updated_at=value["updated_at"],
        )


@dataclass(frozen=True, slots=True)
class ProfileLoadResult:
    status: ProfileLoadStatus
    profile: DesktopComputeProfile
    reason_code: str
    rejected_source_preserved: bool


@dataclass(frozen=True, slots=True)
class ProfileSaveResult:
    profile: DesktopComputeProfile
    document_sha256: str
    bytes_written: int


_WORKLOADS: tuple[dict[str, object], ...] = (
    {"workload_id": "planning.local.ollama", "owner": "Development 2", "workload_class": "GPU_PREFERRED_CPU_ALLOWED", "cpu_fallback_eligible": True, "adapter_admission_state": "CURRENT_BIND_REQUIRED", "admitted_local_backends": ["CUDA", "ROCM", "DIRECTML", "CPU"]},
    {"workload_id": "image.local.comfyui", "owner": "Development 2", "workload_class": "GPU_REQUIRED", "cpu_fallback_eligible": False, "adapter_admission_state": "CURRENT_BIND_REQUIRED", "admitted_local_backends": ["CUDA", "ROCM", "DIRECTML"]},
    {"workload_id": "video.local.generation", "owner": "Development 2", "workload_class": "GPU_REQUIRED", "cpu_fallback_eligible": False, "adapter_admission_state": "DISABLED_UNTIL_IMPLEMENTED", "admitted_local_backends": []},
    {"workload_id": "audio.asr.faster_whisper", "owner": "Development", "workload_class": "GPU_PREFERRED_CPU_ALLOWED", "cpu_fallback_eligible": True, "adapter_admission_state": "CURRENT_BIND_REQUIRED", "admitted_local_backends": ["CUDA", "CPU"]},
    {"workload_id": "audio.voice.local", "owner": "Development", "workload_class": "GPU_PREFERRED_CPU_ALLOWED", "cpu_fallback_eligible": True, "adapter_admission_state": "DISABLED_UNTIL_MAPPED", "admitted_local_backends": []},
    {"workload_id": "dbd.reasoning.qwen3_8b", "owner": "Development 3", "workload_class": "GPU_REQUIRED", "cpu_fallback_eligible": False, "adapter_admission_state": "CURRENT_BIND_REQUIRED", "admitted_local_backends": ["CUDA"]},
    {"workload_id": "dbd.training", "owner": "Development 3", "workload_class": "GPU_REQUIRED", "cpu_fallback_eligible": False, "adapter_admission_state": "HUMAN_GATE_REQUIRED", "admitted_local_backends": []},
    {"workload_id": "dbd.trivia.editor", "owner": "Development 3", "workload_class": "CPU_ONLY", "cpu_fallback_eligible": False, "adapter_admission_state": "CPU_CONTROL_PLANE", "admitted_local_backends": ["CPU"]},
    {"workload_id": "voice.capture.controller", "owner": "Development", "workload_class": "CPU_ONLY", "cpu_fallback_eligible": False, "adapter_admission_state": "CPU_CONTROL_PLANE", "admitted_local_backends": ["CPU"]},
    {"workload_id": "key.helper", "owner": "Production Linkage Setup", "workload_class": "CPU_ONLY", "cpu_fallback_eligible": False, "adapter_admission_state": "NOT_APPLICABLE_PROVEN", "admitted_local_backends": ["CPU"]},
)

def _renderer_row(renderer_id: str, frontend: str, policy: str, capability_status: str) -> dict[str, object]:
    return {
        "renderer_id": renderer_id,
        "frontend": frontend,
        "preference_applies": False,
        "hardware_acceleration_policy": policy,
        "capability_inventory": {
            "status": capability_status,
            "runtime_version": None,
            "adapter_identity_sha256": None,
        },
        "packaged_renderer_observation": {
            "status": "NOT_CONFIRMED",
            "process_identity_sha256": None,
            "window_identity_sha256": None,
            "adapter_identity_sha256": None,
            "core_webview2_version": None,
            "renderer_kind": None,
            "software_renderer": None,
            "observation_sha256": None,
        },
    }


_RENDERERS: tuple[dict[str, object], ...] = (
    _renderer_row("shell.webview2.renderer", "WEBVIEW2", "ENABLED_WHEN_SUPPORTED", "NOT_CONFIRMED"),
    _renderer_row("dbd.training.tk", "TK", "NO_GPU_RENDERING_CLAIM", "NOT_APPLICABLE"),
    _renderer_row("dbd.trivia.tk", "TK", "NO_GPU_RENDERING_CLAIM", "NOT_APPLICABLE"),
    _renderer_row("voice.model.builder.tk", "TK", "NO_GPU_RENDERING_CLAIM", "NOT_APPLICABLE"),
    _renderer_row("voice.capture.winforms", "WINFORMS", "INDEPENDENT_EVIDENCE_REQUIRED", "NOT_CONFIRMED"),
)


def frozen_workload_registry() -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": WORKLOAD_REGISTRY_SCHEMA_VERSION,
        "message_type": WORKLOAD_REGISTRY_MESSAGE_TYPE,
        "product_id": "BAI_VIDEO_PRODUCTION",
        "registry_revision": 1,
        "workloads": [dict(item) for item in _WORKLOADS],
    }
    value = dict(body)
    value["registry_sha256"] = sha256_bytes(canonical_json_bytes(body))
    validate_workload_registry(value)
    return json.loads(json.dumps(value))


def frozen_renderer_evidence_registry() -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": RENDERER_REGISTRY_SCHEMA_VERSION,
        "message_type": RENDERER_REGISTRY_MESSAGE_TYPE,
        "product_id": "BAI_VIDEO_PRODUCTION",
        "registry_revision": 1,
        "renderers": [dict(item) for item in _RENDERERS],
    }
    value = dict(body)
    value["registry_sha256"] = sha256_bytes(canonical_json_bytes(body))
    validate_renderer_evidence_registry(value)
    return json.loads(json.dumps(value))


def validate_workload_registry(document: Mapping[str, Any]) -> None:
    value = dict(document)
    _validate_resource(value, "desktop-compute-workload-registry.schema.json")
    body = dict(value)
    supplied = body.pop("registry_sha256")
    if supplied != sha256_bytes(canonical_json_bytes(body)):
        raise DesktopComputePolicyError("workload registry digest mismatch")
    rows = value["workloads"]
    if rows != [dict(item) for item in _WORKLOADS]:
        raise DesktopComputePolicyError("workload registry frozen rows mismatch")


def validate_renderer_evidence_registry(document: Mapping[str, Any]) -> None:
    value = dict(document)
    _validate_resource(value, "desktop-renderer-evidence.schema.json")
    body = dict(value)
    supplied = body.pop("registry_sha256")
    if supplied != sha256_bytes(canonical_json_bytes(body)):
        raise DesktopComputePolicyError("renderer registry digest mismatch")
    rows = value["renderers"]
    if len({item["renderer_id"] for item in rows}) != len(_RENDERERS):
        raise DesktopComputePolicyError("renderer registry IDs are not unique")
    expected = {item["renderer_id"]: item for item in _RENDERERS}
    if set(item["renderer_id"] for item in rows) != set(expected):
        raise DesktopComputePolicyError("renderer registry ID set mismatch")
    for item in rows:
        frozen = expected[item["renderer_id"]]
        for field in ("frontend", "preference_applies", "hardware_acceleration_policy"):
            if item[field] != frozen[field]:
                raise DesktopComputePolicyError("renderer responsibility ceiling mismatch")
        if item["frontend"] == "TK" and (
            item["capability_inventory"]["status"] == "PASS"
            or item["packaged_renderer_observation"]["status"] == "PASS"
        ):
            raise DesktopComputePolicyError("Tk frontend cannot claim GPU renderer PASS")
        if (
            item["renderer_id"] == "shell.webview2.renderer"
            and item["packaged_renderer_observation"]["status"] == "PASS"
            and item["capability_inventory"]["status"] != "PASS"
        ):
            raise DesktopComputePolicyError("WebView renderer PASS requires capability inventory")
        if item["renderer_id"] == "shell.webview2.renderer" and item["packaged_renderer_observation"]["status"] == "PASS":
            capability = item["capability_inventory"]
            observation = item["packaged_renderer_observation"]
            if capability["adapter_identity_sha256"] != observation["adapter_identity_sha256"]:
                raise DesktopComputePolicyError("WebView renderer adapter identity mismatch")
            if capability["runtime_version"] != observation["core_webview2_version"]:
                raise DesktopComputePolicyError("WebView renderer runtime version mismatch")
        observation = item["packaged_renderer_observation"]
        if observation["status"] == "PASS":
            observation_body = dict(observation)
            observation_digest = observation_body.pop("observation_sha256")
            if observation_digest != sha256_bytes(canonical_json_bytes(observation_body)):
                raise DesktopComputePolicyError("renderer observation digest mismatch")


def resolve_workload_route(
    workload_id: str,
    preference: ComputePreference,
    capabilities: Iterable[AdapterCapability],
) -> EffectiveWorkloadRoute:
    registry = {item["workload_id"]: item for item in _WORKLOADS}
    if workload_id not in registry:
        raise DesktopComputePolicyError("workload is not in the frozen registry")
    definition = registry[workload_id]
    workload_class = WorkloadClass(definition["workload_class"])
    admission_state = definition["adapter_admission_state"]
    if admission_state in {"DISABLED_UNTIL_IMPLEMENTED", "DISABLED_UNTIL_MAPPED"}:
        return _blocked(workload_id, workload_class, "REGISTRY_ADAPTER_DISABLED")
    if admission_state == "HUMAN_GATE_REQUIRED":
        return _blocked(workload_id, workload_class, "HUMAN_GATE_REQUIRED")
    candidates = [
        item
        for item in capabilities
        if workload_id in item.supported_workloads
        and item.backend in definition["admitted_local_backends"]
        and item.implemented
        and item.compatible
        and (item.device_kind == "CPU" or _gpu_capability_admitted(item, workload_id))
        and (
            admission_state not in {"CURRENT_BIND_REQUIRED", "HUMAN_GATE_REQUIRED"}
            or item.current_bind_verified
        )
    ]
    gpu = list(rank_gpu_capabilities(item for item in candidates if item.device_kind == "GPU"))
    cpu = sorted(
        (item for item in candidates if item.device_kind == "CPU"),
        key=lambda item: item.backend,
    )

    if workload_class is WorkloadClass.CPU_ONLY:
        if cpu:
            return _route(workload_id, workload_class, cpu[0], "CPU_ONLY_NOT_GPU_APPLICABLE", CompatibilityStatus.NOT_APPLICABLE)
        return _blocked(workload_id, workload_class, "CPU_ADAPTER_NOT_IMPLEMENTED")
    if preference is ComputePreference.CPU_EXPLICIT:
        if workload_class is WorkloadClass.GPU_REQUIRED:
            return _blocked(workload_id, workload_class, "CPU_NOT_ADMITTED_FOR_GPU_REQUIRED")
        if cpu:
            return _route(workload_id, workload_class, cpu[0], "CPU_EXPLICIT_SELECTED", CompatibilityStatus.PASS)
        return _blocked(workload_id, workload_class, "CPU_ADAPTER_NOT_IMPLEMENTED")
    if gpu:
        reason = "COMPATIBLE_GPU_SELECTED"
        return _route(workload_id, workload_class, gpu[0], reason, CompatibilityStatus.PASS)
    if preference is ComputePreference.GPU_REQUIRED:
        return _blocked(workload_id, workload_class, "COMPATIBLE_GPU_NOT_AVAILABLE")
    if workload_class is WorkloadClass.GPU_PREFERRED_CPU_ALLOWED and cpu:
        result = _route(workload_id, workload_class, cpu[0], "AUTO_GPU_UNAVAILABLE_CPU_FALLBACK", CompatibilityStatus.PASS)
        return replace(result, cpu_fallback_visible_before_execution=True)
    return _blocked(workload_id, workload_class, "COMPATIBLE_GPU_NOT_AVAILABLE")


def rank_gpu_capabilities(capabilities: Iterable[AdapterCapability]) -> tuple[AdapterCapability, ...]:
    return tuple(
        sorted(
            (item for item in capabilities if item.device_kind == "GPU"),
            key=lambda item: (
                0 if item.discrete else 1,
                -item.dedicated_memory_bytes,
                item.identity.stable_key if item.identity else "",
            ),
        )
    )


def _gpu_capability_admitted(capability: AdapterCapability, workload_id: str) -> bool:
    try:
        from .desktop_compute_probe import validate_capability_admission_receipt

        validate_capability_admission_receipt(capability, workload_id=workload_id)
        return True
    except Exception:
        return False


def _route(
    workload_id: str,
    workload_class: WorkloadClass,
    capability: AdapterCapability,
    reason_code: str,
    status: CompatibilityStatus,
) -> EffectiveWorkloadRoute:
    return EffectiveWorkloadRoute(
        workload_id=workload_id,
        workload_class=workload_class,
        effective_backend=capability.backend,
        adapter_identity=capability.identity,
        reason_code=reason_code,
        compatibility_status=status,
        loaded_runtime_versions=capability.loaded_runtime_versions,
        capability_admission_receipt=capability.admission_receipt,
    )


def _blocked(workload_id: str, workload_class: WorkloadClass, reason: str) -> EffectiveWorkloadRoute:
    return EffectiveWorkloadRoute(
        workload_id=workload_id,
        workload_class=workload_class,
        effective_backend="DISABLED",
        adapter_identity=None,
        reason_code=reason,
        compatibility_status=CompatibilityStatus.BLOCKED,
    )


class DesktopComputeProfileStore:
    """Sole-writer store used by the main Settings service."""

    def __init__(self, layout: DesktopInstallLayout, *, lock_timeout_seconds: float = PROFILE_LOCK_TIMEOUT_SECONDS) -> None:
        if not 0 < lock_timeout_seconds <= PROFILE_LOCK_TIMEOUT_SECONDS:
            raise DesktopComputePolicyError("profile lock timeout exceeds contract")
        self.layout = layout
        self.path = layout.profile_path
        self.lock_timeout_seconds = lock_timeout_seconds
        if self.path.parent != layout.settings_root:
            raise DesktopComputePolicyError("profile path escaped Settings ownership")

    def load(self) -> ProfileLoadResult:
        default = DesktopComputeProfile.default(self.layout.install_instance_id)
        if not self.path.exists() and not self.path.is_symlink():
            return ProfileLoadResult(ProfileLoadStatus.DEFAULT_MISSING, default, "PROFILE_NOT_CONFIGURED", False)
        try:
            document = _read_profile_document(self.path)
            profile = DesktopComputeProfile.from_dict(document)
            if profile.install_instance_id != self.layout.install_instance_id:
                raise DesktopComputePolicyError("profile install instance mismatch")
            return ProfileLoadResult(ProfileLoadStatus.LOADED, profile, "PROFILE_LOADED", False)
        except Exception as exc:
            return ProfileLoadResult(ProfileLoadStatus.DEFAULT_REJECTED, default, _profile_rejection_reason(exc), True)

    def save(
        self,
        *,
        selected_preference: ComputePreference,
        workload_routes: Iterable[EffectiveWorkloadRoute] = (),
        expected_revision: int | None,
        failure_injector: FailureInjector | None = None,
    ) -> ProfileSaveResult:
        _require_existing_settings_root(self.layout)
        with _ProfileMutex(self.layout.install_instance_id, self.layout.settings_root, self.lock_timeout_seconds):
            current = self.load()
            if current.status is ProfileLoadStatus.DEFAULT_REJECTED:
                raise DesktopComputePolicyError("rejected profile is preserved and cannot be overwritten")
            revision = current.profile.revision
            if expected_revision != revision:
                raise DesktopComputePolicyError("compute profile revision conflict")
            routes = tuple(sorted(workload_routes, key=lambda item: item.workload_id))
            profile = DesktopComputeProfile(
                install_instance_id=self.layout.install_instance_id,
                revision=revision + 1,
                selected_preference=selected_preference,
                workload_routes=routes,
                updated_at=utc_now_iso(),
            )
            document = profile.to_dict()
            _validate_resource(document, "desktop-compute-profile.schema.json")
            write = AtomicJsonWriter.write(
                self.path,
                document,
                validator=lambda value: DesktopComputeProfile.from_dict(value),
                failure_injector=failure_injector,
            )
            readback = self.load()
            if readback.status is not ProfileLoadStatus.LOADED or readback.profile != profile:
                raise DesktopComputePolicyError("compute profile exact read-back failed")
            return ProfileSaveResult(
                profile=profile,
                document_sha256=document["document_sha256"],
                bytes_written=write.bytes_written,
            )


class _ProfileMutex(AbstractContextManager[None]):
    def __init__(self, install_instance_id: str, settings_root: Path, timeout: float) -> None:
        digest = sha256_bytes(install_instance_id.encode("utf-8")).removeprefix("sha256:")[:32]
        self.name = f"Local\\BAI-Video-Production-Desktop-Compute-{digest}"
        self.lock_path = settings_root / f".desktop-compute-{digest}.lock"
        self.timeout = timeout
        self._handle: Any = None
        self._thread_lock = _PROCESS_LOCKS.setdefault(self.name, threading.Lock())

    def __enter__(self) -> None:
        if not self._thread_lock.acquire(timeout=self.timeout):
            raise DesktopComputePolicyError("compute profile mutex timeout")
        try:
            if os.name == "nt":
                self._enter_windows()
            else:
                self._enter_posix()
        except Exception:
            self._thread_lock.release()
            raise
        return None

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        try:
            if os.name == "nt":
                import ctypes

                if self._handle:
                    ctypes.windll.kernel32.ReleaseMutex(self._handle)
                    ctypes.windll.kernel32.CloseHandle(self._handle)
            elif self._handle:
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
                self._handle.close()
        finally:
            self._handle = None
            self._thread_lock.release()

    def _enter_windows(self) -> None:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel32.CreateMutexW(None, False, self.name)
        if not handle:
            raise DesktopComputePolicyError("compute profile mutex creation failed")
        result = kernel32.WaitForSingleObject(handle, int(self.timeout * 1000))
        if result not in {0x00000000, 0x00000080}:
            kernel32.CloseHandle(handle)
            raise DesktopComputePolicyError("compute profile mutex timeout")
        self._handle = handle

    def _enter_posix(self) -> None:
        import fcntl

        self._handle = self.lock_path.open("a+b")
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    self._handle.close()
                    self._handle = None
                    raise DesktopComputePolicyError("compute profile mutex timeout")
                time.sleep(0.01)


_PROCESS_LOCKS: dict[str, threading.Lock] = {}


def _validate_resource(document: Any, name: str) -> None:
    schema = json.loads(
        files("ai_video_production.schema_resources").joinpath(name).read_text(encoding="utf-8")
    )
    try:
        validate_instance(document, schema)
    except Exception as exc:
        raise DesktopComputePolicyError(f"{name} validation failed") from exc


def _read_profile_document(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise DesktopComputePolicyError("compute profile must not be a symlink")
    before = path.stat(follow_symlinks=False)
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or getattr(before, "st_file_attributes", 0) & 0x400
    ):
        raise DesktopComputePolicyError("compute profile must be a single-link regular file")
    if not 1 <= before.st_size <= _MAX_PROFILE_BYTES:
        raise DesktopComputePolicyError("compute profile size is invalid")
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                raise DesktopComputePolicyError("compute profile opened identity is unsafe")
            data = os.read(descriptor, _MAX_PROFILE_BYTES + 1)
            after_open = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        after = path.stat(follow_symlinks=False)
        identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
        if not (
            identity(before) == identity(opened)
            and identity(opened) == identity(after_open)
            and identity(after_open) == identity(after)
        ):
            raise DesktopComputePolicyError("compute profile changed during read-back")
        if not 1 <= len(data) <= _MAX_PROFILE_BYTES:
            raise DesktopComputePolicyError("compute profile size is invalid")
        document = json.loads(data.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DesktopComputePolicyError("compute profile JSON is invalid") from exc
    if not isinstance(document, dict):
        raise DesktopComputePolicyError("compute profile must be an object")
    return document


def _require_existing_settings_root(layout: DesktopInstallLayout) -> None:
    root = layout.settings_root
    if root.is_symlink():
        raise DesktopComputePolicyError("settings root must not be a symlink")
    try:
        metadata = root.stat(follow_symlinks=False)
    except OSError as exc:
        raise DesktopComputePolicyError("settings root must be installer-provisioned") from exc
    if not stat.S_ISDIR(metadata.st_mode):
        raise DesktopComputePolicyError("settings root must be a directory")
    installation = layout.installation_state_root
    if installation.exists() and installation.is_symlink():
        raise DesktopComputePolicyError("installation state root is unsafe")


def _profile_rejection_reason(exc: Exception) -> str:
    text = str(exc).lower()
    if "version" in text:
        return "PROFILE_VERSION_UNSUPPORTED"
    if "digest" in text or "checksum" in text:
        return "PROFILE_DIGEST_INVALID"
    if "instance" in text:
        return "PROFILE_INSTANCE_MISMATCH"
    if "symlink" in text or "regular" in text:
        return "PROFILE_FILE_IDENTITY_UNSAFE"
    return "PROFILE_INVALID_PRESERVED"


def _validate_persisted_route(
    route: EffectiveWorkloadRoute,
    preference: ComputePreference,
    definition: Mapping[str, Any],
) -> None:
    expected_class = WorkloadClass(definition["workload_class"])
    if route.workload_class is not expected_class:
        raise DesktopComputePolicyError("persisted workload class exceeds registry ceiling")
    if route.compatibility_status is CompatibilityStatus.BLOCKED:
        if route.effective_backend != "DISABLED" or route.adapter_identity is not None or route.capability_admission_receipt is not None:
            raise DesktopComputePolicyError("blocked route claims an effective backend")
        if route.cpu_fallback_visible_before_execution:
            raise DesktopComputePolicyError("blocked route claims CPU fallback")
        return
    if definition["adapter_admission_state"] in {
        "DISABLED_UNTIL_IMPLEMENTED",
        "DISABLED_UNTIL_MAPPED",
        "HUMAN_GATE_REQUIRED",
    }:
        raise DesktopComputePolicyError("persisted route exceeds registry admission state")
    if route.effective_backend == "DISABLED":
        raise DesktopComputePolicyError("admitted route has no effective backend")
    if route.effective_backend not in definition["admitted_local_backends"]:
        raise DesktopComputePolicyError("persisted backend is outside local admission")
    if route.effective_backend == "CPU":
        if expected_class is WorkloadClass.GPU_REQUIRED:
            raise DesktopComputePolicyError("GPU-required route cannot persist CPU")
        if expected_class is WorkloadClass.CPU_ONLY:
            if route.compatibility_status is not CompatibilityStatus.NOT_APPLICABLE:
                raise DesktopComputePolicyError("CPU-only route must be not GPU-applicable")
        elif not definition["cpu_fallback_eligible"]:
            raise DesktopComputePolicyError("CPU fallback exceeds registry ceiling")
        if route.adapter_identity is not None:
            raise DesktopComputePolicyError("CPU route cannot claim GPU adapter identity")
        if route.capability_admission_receipt is not None:
            raise DesktopComputePolicyError("CPU route cannot claim GPU admission receipt")
        if expected_class is WorkloadClass.GPU_PREFERRED_CPU_ALLOWED:
            if route.compatibility_status is not CompatibilityStatus.PASS:
                raise DesktopComputePolicyError("CPU fallback status is inconsistent")
            if preference is ComputePreference.GPU_REQUIRED:
                raise DesktopComputePolicyError("GPU-required preference cannot persist CPU")
            if preference is ComputePreference.CPU_EXPLICIT:
                if route.reason_code != "CPU_EXPLICIT_SELECTED" or route.cpu_fallback_visible_before_execution:
                    raise DesktopComputePolicyError("explicit CPU route reason is inconsistent")
            elif not (
                route.reason_code == "AUTO_GPU_UNAVAILABLE_CPU_FALLBACK"
                and route.cpu_fallback_visible_before_execution
            ):
                raise DesktopComputePolicyError("automatic CPU fallback is not visible")
        elif route.reason_code != "CPU_ONLY_NOT_GPU_APPLICABLE":
            raise DesktopComputePolicyError("CPU-only route reason is inconsistent")
    else:
        if preference is ComputePreference.CPU_EXPLICIT:
            raise DesktopComputePolicyError("explicit CPU preference cannot persist GPU")
        if route.adapter_identity is None:
            raise DesktopComputePolicyError("GPU route requires stable adapter identity")
        if route.compatibility_status is not CompatibilityStatus.PASS:
            raise DesktopComputePolicyError("GPU route status is inconsistent")
        if not route.loaded_runtime_versions:
            raise DesktopComputePolicyError("GPU route lacks loaded runtime identity")
        if route.reason_code != "COMPATIBLE_GPU_SELECTED":
            raise DesktopComputePolicyError("GPU route reason is inconsistent")
        raise DesktopComputePolicyError(
            "GPU admission is live Evidence and must not be persisted in the profile"
        )
    if route.cpu_fallback_visible_before_execution:
        if not (
            preference is ComputePreference.AUTO_GPU_FIRST
            and route.effective_backend == "CPU"
            and expected_class is WorkloadClass.GPU_PREFERRED_CPU_ALLOWED
            and definition["cpu_fallback_eligible"]
            and route.reason_code == "AUTO_GPU_UNAVAILABLE_CPU_FALLBACK"
        ):
            raise DesktopComputePolicyError("CPU fallback visibility is inconsistent")


def _require_reason(value: str) -> None:
    if not isinstance(value, str) or _REASON_RE.fullmatch(value) is None:
        raise DesktopComputePolicyError("reason_code is invalid")


__all__ = [
    "AdapterCapability",
    "AdapterIdentity",
    "CapabilityAdmissionReceipt",
    "CompatibilityStatus",
    "ComputePreference",
    "DesktopComputePolicyError",
    "DesktopComputeProfile",
    "DesktopComputeProfileStore",
    "EffectiveWorkloadRoute",
    "PROFILE_LOCK_TIMEOUT_SECONDS",
    "ProfileLoadResult",
    "ProfileLoadStatus",
    "ProfileSaveResult",
    "WorkloadClass",
    "frozen_renderer_evidence_registry",
    "frozen_workload_registry",
    "resolve_workload_route",
    "rank_gpu_capabilities",
    "validate_renderer_evidence_registry",
    "validate_workload_registry",
]
