"""Pure TASK-066 bindings for local audio compute routes.

This module translates an already-resolved GF-A workload route into an exact
FasterWhisper device selection.  It performs no model load, transcription,
voice synthesis, training, file I/O, Provider call, or native operation.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from .desktop_compute_policy import (
    AdapterCapability,
    CompatibilityStatus,
    ComputePreference,
    EffectiveWorkloadRoute,
    WorkloadClass,
    frozen_workload_registry,
)
from .desktop_compute_probe import (
    DesktopComputeProbeError,
    validate_capability_admission_receipt,
)
from .faster_whisper_asr import FasterWhisperConfig
from .serialization import canonical_json_bytes, sha256_bytes


FASTER_WHISPER_WORKLOAD_ID = "audio.asr.faster_whisper"
LOCAL_VOICE_WORKLOAD_ID = "audio.voice.local"


class Task066AudioComputeError(ValueError):
    """Stable fail-closed error for a rejected audio compute binding."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class FasterWhisperComputeBinding:
    workload_id: str
    effective_backend: str
    device: str
    compute_type: str
    reason_code: str
    cpu_fallback_visible_before_execution: bool
    adapter_identity_sha256: str | None
    capability_receipt_sha256: str | None
    route_sha256: str

    def public_projection(self) -> dict[str, object]:
        """Return a body-free projection safe for Settings/diagnostics."""
        return {
            "workload_id": self.workload_id,
            "effective_backend": self.effective_backend,
            "device": self.device,
            "compute_type": self.compute_type,
            "reason_code": self.reason_code,
            "cpu_fallback_visible_before_execution": (
                self.cpu_fallback_visible_before_execution
            ),
            "adapter_identity_sha256": self.adapter_identity_sha256,
            "capability_receipt_sha256": self.capability_receipt_sha256,
            "route_sha256": self.route_sha256,
            "execution_started": False,
            "model_load_started": False,
            "audio_access_started": False,
            "provider_execution_started": False,
        }


@dataclass(frozen=True, slots=True)
class BoundFasterWhisperExecution:
    """In-process config plus its public-safe route identity."""

    config: FasterWhisperConfig = field(repr=False)
    binding: FasterWhisperComputeBinding


@dataclass(frozen=True, slots=True)
class LocalVoiceComputeProjection:
    workload_id: str
    adapter_state: str
    reason_code: str
    execution_allowed: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "workload_id": self.workload_id,
            "adapter_state": self.adapter_state,
            "reason_code": self.reason_code,
            "execution_allowed": False,
            "model_load_started": False,
            "voice_generation_started": False,
            "training_started": False,
            "owner_voice_used": False,
        }


def bind_faster_whisper_config(
    *,
    route: EffectiveWorkloadRoute,
    config: FasterWhisperConfig,
    selected_preference: ComputePreference,
    capability: AdapterCapability,
    observed_cpu_fallback_route_sha256: str | None = None,
) -> BoundFasterWhisperExecution:
    """Bind one exact GF-A route without allowing implicit device fallback."""
    binding = project_faster_whisper_compute_binding(
        route=route,
        config=config,
        selected_preference=selected_preference,
        capability=capability,
    )
    if binding.cpu_fallback_visible_before_execution and (
        observed_cpu_fallback_route_sha256 != binding.route_sha256
    ):
        raise Task066AudioComputeError(
            "AUDIO_COMPUTE_FALLBACK_NOTICE_REQUIRED",
            "Exact automatic CPU fallback route was not observed before execution",
        )
    return BoundFasterWhisperExecution(
        config=replace(config, device=binding.device),
        binding=binding,
    )


def project_faster_whisper_compute_binding(
    *,
    route: EffectiveWorkloadRoute,
    config: FasterWhisperConfig,
    selected_preference: ComputePreference,
    capability: AdapterCapability,
) -> FasterWhisperComputeBinding:
    """Validate and project an exact route before any provider/model effect."""
    if not isinstance(selected_preference, ComputePreference):
        raise Task066AudioComputeError(
            "AUDIO_COMPUTE_PREFERENCE_INVALID",
            "Selected compute preference is invalid",
        )
    if not isinstance(config, FasterWhisperConfig):
        raise Task066AudioComputeError(
            "AUDIO_COMPUTE_CONFIG_INVALID",
            "FasterWhisper config is invalid",
        )
    if not isinstance(capability, AdapterCapability):
        raise Task066AudioComputeError(
            "AUDIO_COMPUTE_CAPABILITY_INVALID",
            "Audio compute capability is invalid",
        )
    _require_faster_whisper_route(route)

    if route.effective_backend == "CPU":
        _require_cpu_route(route, capability, selected_preference)
        device = "cpu"
    elif route.effective_backend == "CUDA":
        _require_live_cuda_route(route, capability, selected_preference)
        device = "cuda"
    else:
        raise Task066AudioComputeError(
            "AUDIO_COMPUTE_BACKEND_UNSUPPORTED",
            "FasterWhisper route backend is not implemented",
        )

    if config.device not in {"auto", device}:
        raise Task066AudioComputeError(
            "AUDIO_COMPUTE_LEGACY_DEVICE_CONFLICT",
            "Legacy FasterWhisper device conflicts with the effective route",
        )

    adapter_digest = (
        None
        if route.adapter_identity is None
        else sha256_bytes(canonical_json_bytes(route.adapter_identity.to_dict()))
    )
    receipt_digest = (
        None
        if route.capability_admission_receipt is None
        else route.capability_admission_receipt.receipt_sha256
    )
    return FasterWhisperComputeBinding(
        workload_id=route.workload_id,
        effective_backend=route.effective_backend,
        device=device,
        compute_type=config.compute_type,
        reason_code=route.reason_code,
        cpu_fallback_visible_before_execution=(
            route.cpu_fallback_visible_before_execution
        ),
        adapter_identity_sha256=adapter_digest,
        capability_receipt_sha256=receipt_digest,
        route_sha256=sha256_bytes(canonical_json_bytes(route.to_dict())),
    )


def project_local_voice_compute_state(
    route: EffectiveWorkloadRoute,
) -> LocalVoiceComputeProjection:
    """Expose the frozen disabled voice route without issuing TTS authority."""
    row = _workload_row(LOCAL_VOICE_WORKLOAD_ID)
    if row["adapter_admission_state"] != "DISABLED_UNTIL_MAPPED":
        raise Task066AudioComputeError(
            "AUDIO_VOICE_REGISTRY_DRIFT",
            "Local voice registry state changed outside GF-C ownership",
        )
    if (
        not isinstance(route, EffectiveWorkloadRoute)
        or route.workload_id != LOCAL_VOICE_WORKLOAD_ID
        or route.workload_class is not WorkloadClass.GPU_PREFERRED_CPU_ALLOWED
        or route.compatibility_status is not CompatibilityStatus.BLOCKED
        or route.effective_backend != "DISABLED"
        or route.reason_code != "REGISTRY_ADAPTER_DISABLED"
        or route.adapter_identity is not None
        or route.capability_admission_receipt is not None
        or route.loaded_runtime_versions
        or route.cpu_fallback_visible_before_execution
    ):
        raise Task066AudioComputeError(
            "AUDIO_VOICE_ROUTE_NOT_DISABLED",
            "Local voice compute remains disabled until an exact adapter is mapped",
        )
    return LocalVoiceComputeProjection(
        workload_id=LOCAL_VOICE_WORKLOAD_ID,
        adapter_state="DISABLED_UNTIL_MAPPED",
        reason_code=route.reason_code,
    )


def _require_faster_whisper_route(route: EffectiveWorkloadRoute) -> None:
    if not isinstance(route, EffectiveWorkloadRoute):
        raise Task066AudioComputeError(
            "AUDIO_COMPUTE_ROUTE_INVALID", "Compute route has an invalid type"
        )
    row = _workload_row(FASTER_WHISPER_WORKLOAD_ID)
    if (
        route.workload_id != FASTER_WHISPER_WORKLOAD_ID
        or route.workload_class is not WorkloadClass.GPU_PREFERRED_CPU_ALLOWED
        or row["adapter_admission_state"] != "CURRENT_BIND_REQUIRED"
    ):
        raise Task066AudioComputeError(
            "AUDIO_COMPUTE_ROUTE_SCOPE",
            "Compute route is outside the FasterWhisper workload boundary",
        )
    if route.compatibility_status is not CompatibilityStatus.PASS:
        raise Task066AudioComputeError(
            "AUDIO_COMPUTE_ROUTE_BLOCKED",
            "Blocked or unconfirmed FasterWhisper route cannot execute",
        )
    if route.restart_required:
        raise Task066AudioComputeError(
            "AUDIO_COMPUTE_RESTART_REQUIRED",
            "FasterWhisper route requires restart before execution",
        )


def _require_cpu_route(
    route: EffectiveWorkloadRoute,
    capability: AdapterCapability,
    selected_preference: ComputePreference,
) -> None:
    if (
        capability.backend != "CPU"
        or capability.device_kind != "CPU"
        or capability.identity is not None
        or FASTER_WHISPER_WORKLOAD_ID not in capability.supported_workloads
        or not capability.current_bind_verified
        or not capability.implemented
        or not capability.compatible
        or capability.admission_receipt is not None
        or capability.live_admission_token is not None
        or capability.loaded_runtime_versions
        or capability.runtime_inventory_sha256 is not None
        or route.adapter_identity is not None
        or route.capability_admission_receipt is not None
        or route.loaded_runtime_versions
    ):
        raise Task066AudioComputeError(
            "AUDIO_COMPUTE_CPU_IDENTITY_INVALID",
            "CPU route cannot claim GPU capability identity",
        )
    if route.reason_code == "CPU_EXPLICIT_SELECTED":
        if (
            selected_preference is not ComputePreference.CPU_EXPLICIT
            or route.cpu_fallback_visible_before_execution
        ):
            raise Task066AudioComputeError(
                "AUDIO_COMPUTE_CPU_REASON_INVALID",
                "Explicit CPU selection cannot claim automatic fallback",
            )
        return
    if route.reason_code == "AUTO_GPU_UNAVAILABLE_CPU_FALLBACK":
        if (
            selected_preference is not ComputePreference.AUTO_GPU_FIRST
            or not route.cpu_fallback_visible_before_execution
        ):
            raise Task066AudioComputeError(
                "AUDIO_COMPUTE_FALLBACK_HIDDEN",
                "Automatic CPU fallback must be visible before execution",
            )
        return
    raise Task066AudioComputeError(
        "AUDIO_COMPUTE_CPU_REASON_INVALID",
        "CPU route reason does not match the frozen policy",
    )


def _require_live_cuda_route(
    route: EffectiveWorkloadRoute,
    capability: AdapterCapability,
    selected_preference: ComputePreference,
) -> None:
    if (
        selected_preference is ComputePreference.CPU_EXPLICIT
        or route.reason_code != "COMPATIBLE_GPU_SELECTED"
        or route.cpu_fallback_visible_before_execution
        or route.adapter_identity is None
        or route.capability_admission_receipt is None
        or not route.loaded_runtime_versions
    ):
        raise Task066AudioComputeError(
            "AUDIO_COMPUTE_GPU_BINDING_INCOMPLETE",
            "CUDA route lacks an exact live capability binding",
        )
    if (
        capability.backend != "CUDA"
        or capability.device_kind != "GPU"
        or capability.identity != route.adapter_identity
        or capability.loaded_runtime_versions != route.loaded_runtime_versions
        or capability.admission_receipt != route.capability_admission_receipt
        or FASTER_WHISPER_WORKLOAD_ID not in capability.supported_workloads
        or not capability.current_bind_verified
        or not capability.implemented
        or not capability.compatible
    ):
        raise Task066AudioComputeError(
            "AUDIO_COMPUTE_GPU_IDENTITY_DRIFT",
            "CUDA route and live capability identities differ",
        )
    try:
        validate_capability_admission_receipt(
            capability,
            workload_id=FASTER_WHISPER_WORKLOAD_ID,
        )
    except DesktopComputeProbeError as exc:
        raise Task066AudioComputeError(
            "AUDIO_COMPUTE_GPU_RECEIPT_INVALID",
            "CUDA capability admission receipt is not live and exact",
        ) from exc


def _workload_row(workload_id: str) -> Mapping[str, Any]:
    registry = frozen_workload_registry()
    row = next(
        (item for item in registry["workloads"] if item["workload_id"] == workload_id),
        None,
    )
    if row is None:
        raise Task066AudioComputeError(
            "AUDIO_COMPUTE_REGISTRY_MISSING",
            "Required audio workload is missing from the frozen registry",
        )
    return row


__all__ = [
    "BoundFasterWhisperExecution",
    "FASTER_WHISPER_WORKLOAD_ID",
    "FasterWhisperComputeBinding",
    "LOCAL_VOICE_WORKLOAD_ID",
    "LocalVoiceComputeProjection",
    "Task066AudioComputeError",
    "bind_faster_whisper_config",
    "project_faster_whisper_compute_binding",
    "project_local_voice_compute_state",
]
