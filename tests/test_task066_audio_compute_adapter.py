from __future__ import annotations

import json

import pytest

from ai_video_production.desktop_compute_policy import (
    AdapterCapability,
    AdapterIdentity,
    CapabilityAdmissionReceipt,
    CompatibilityStatus,
    ComputePreference,
    EffectiveWorkloadRoute,
    WorkloadClass,
)
from ai_video_production.faster_whisper_asr import (
    FasterWhisperConfig,
    FasterWhisperProvider,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task066_audio_compute_adapter import (
    FASTER_WHISPER_WORKLOAD_ID,
    LOCAL_VOICE_WORKLOAD_ID,
    Task066AudioComputeError,
    bind_faster_whisper_config,
    project_faster_whisper_compute_binding,
    project_local_voice_compute_state,
)


def _cpu_route(*, automatic: bool = False, restart_required: bool = False) -> EffectiveWorkloadRoute:
    return EffectiveWorkloadRoute(
        workload_id=FASTER_WHISPER_WORKLOAD_ID,
        workload_class=WorkloadClass.GPU_PREFERRED_CPU_ALLOWED,
        effective_backend="CPU",
        adapter_identity=None,
        reason_code=(
            "AUTO_GPU_UNAVAILABLE_CPU_FALLBACK"
            if automatic
            else "CPU_EXPLICIT_SELECTED"
        ),
        compatibility_status=CompatibilityStatus.PASS,
        restart_required=restart_required,
        cpu_fallback_visible_before_execution=automatic,
    )


def _blocked_voice_route() -> EffectiveWorkloadRoute:
    return EffectiveWorkloadRoute(
        workload_id=LOCAL_VOICE_WORKLOAD_ID,
        workload_class=WorkloadClass.GPU_PREFERRED_CPU_ALLOWED,
        effective_backend="DISABLED",
        adapter_identity=None,
        reason_code="REGISTRY_ADAPTER_DISABLED",
        compatibility_status=CompatibilityStatus.BLOCKED,
    )


def _identity() -> AdapterIdentity:
    return AdapterIdentity(
        luid="LUID-1",
        vendor_id="10DE",
        device_id="2783",
        subsystem_id="TEST",
        driver_instance_digest="sha256:" + "1" * 64,
    )


def _cpu_capability() -> AdapterCapability:
    return AdapterCapability(
        backend="CPU",
        device_kind="CPU",
        identity=None,
        supported_workloads=frozenset({FASTER_WHISPER_WORKLOAD_ID}),
        implemented=True,
        compatible=True,
        current_bind_verified=True,
    )


def _receipt(identity: AdapterIdentity) -> CapabilityAdmissionReceipt:
    body = {
        "registry_revision": 1,
        "registry_sha256": "sha256:" + "2" * 64,
        "probe_id": "audio.asr.faster_whisper.cuda",
        "workload_id": FASTER_WHISPER_WORKLOAD_ID,
        "backend": "CUDA",
        "adapter_identity_sha256": sha256_bytes(canonical_json_bytes(identity.to_dict())),
        "runtime_inventory_sha256": "sha256:" + "3" * 64,
        "runtime_versions_sha256": "sha256:" + "4" * 64,
        "helper_sha256": "sha256:" + "5" * 64,
        "command_sha256": "sha256:" + "6" * 64,
        "consumer_process_pid": 10,
        "probe_process_pid": 11,
    }
    return CapabilityAdmissionReceipt(
        **body,
        receipt_sha256=sha256_bytes(canonical_json_bytes(body)),
    )


def _forged_cuda() -> tuple[EffectiveWorkloadRoute, AdapterCapability]:
    identity = _identity()
    receipt = _receipt(identity)
    capability = AdapterCapability(
        backend="CUDA",
        device_kind="GPU",
        identity=identity,
        supported_workloads=frozenset({FASTER_WHISPER_WORKLOAD_ID}),
        implemented=True,
        compatible=True,
        discrete=True,
        dedicated_memory_bytes=12 * 1024**3,
        current_bind_verified=True,
        loaded_runtime_versions=("CUDA-TEST",),
        admission_receipt=receipt,
        runtime_inventory_sha256=receipt.runtime_inventory_sha256,
        live_admission_token=object(),
    )
    route = EffectiveWorkloadRoute(
        workload_id=FASTER_WHISPER_WORKLOAD_ID,
        workload_class=WorkloadClass.GPU_PREFERRED_CPU_ALLOWED,
        effective_backend="CUDA",
        adapter_identity=identity,
        reason_code="COMPATIBLE_GPU_SELECTED",
        compatibility_status=CompatibilityStatus.PASS,
        loaded_runtime_versions=("CUDA-TEST",),
        capability_admission_receipt=receipt,
    )
    return route, capability


def test_explicit_cpu_route_replaces_legacy_auto_without_other_config_drift() -> None:
    original = FasterWhisperConfig(
        model="small",
        device="auto",
        compute_type="int8",
        beam_size=7,
        allow_model_download=False,
    )
    result = bind_faster_whisper_config(
        route=_cpu_route(),
        config=original,
        selected_preference=ComputePreference.CPU_EXPLICIT,
        capability=_cpu_capability(),
    )

    assert result.config.device == "cpu"
    assert result.config.model == original.model
    assert result.config.compute_type == original.compute_type
    assert result.config.beam_size == original.beam_size
    assert result.config.allow_model_download is False
    assert result.binding.public_projection()["execution_started"] is False


def test_bound_config_reaches_provider_factory_with_explicit_device() -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeModel:
        pass

    def factory(model: str, **kwargs: object) -> FakeModel:
        calls.append((model, kwargs))
        return FakeModel()

    result = bind_faster_whisper_config(
        route=_cpu_route(),
        config=FasterWhisperConfig(device="auto", allow_model_download=False),
        selected_preference=ComputePreference.CPU_EXPLICIT,
        capability=_cpu_capability(),
    )
    provider = FasterWhisperProvider(result.config, model_factory=factory)
    provider._model()

    assert calls == [
        (
            "small",
            {
                "device": "cpu",
                "compute_type": "int8",
                "local_files_only": True,
            },
        )
    ]


def test_automatic_cpu_fallback_requires_pre_execution_notice_observation() -> None:
    route = _cpu_route(automatic=True)
    config = FasterWhisperConfig()
    with pytest.raises(Task066AudioComputeError) as hidden:
        bind_faster_whisper_config(
            route=route,
            config=config,
            selected_preference=ComputePreference.AUTO_GPU_FIRST,
            capability=_cpu_capability(),
        )
    assert hidden.value.code == "AUDIO_COMPUTE_FALLBACK_NOTICE_REQUIRED"

    projection = project_faster_whisper_compute_binding(
        route=route,
        config=config,
        selected_preference=ComputePreference.AUTO_GPU_FIRST,
        capability=_cpu_capability(),
    )
    result = bind_faster_whisper_config(
        route=route,
        config=config,
        selected_preference=ComputePreference.AUTO_GPU_FIRST,
        capability=_cpu_capability(),
        observed_cpu_fallback_route_sha256=projection.route_sha256,
    )
    assert result.config.device == "cpu"
    assert result.binding.cpu_fallback_visible_before_execution is True

    with pytest.raises(Task066AudioComputeError) as replayed:
        bind_faster_whisper_config(
            route=route,
            config=config,
            selected_preference=ComputePreference.AUTO_GPU_FIRST,
            capability=_cpu_capability(),
            observed_cpu_fallback_route_sha256="sha256:" + "0" * 64,
        )
    assert replayed.value.code == "AUDIO_COMPUTE_FALLBACK_NOTICE_REQUIRED"


def test_cpu_route_requires_matching_preference_and_current_capability() -> None:
    with pytest.raises(Task066AudioComputeError) as preference:
        bind_faster_whisper_config(
            route=_cpu_route(),
            config=FasterWhisperConfig(),
            selected_preference=ComputePreference.AUTO_GPU_FIRST,
            capability=_cpu_capability(),
        )
    assert preference.value.code == "AUDIO_COMPUTE_CPU_REASON_INVALID"

    stale = AdapterCapability(
        backend="CPU",
        device_kind="CPU",
        identity=None,
        supported_workloads=frozenset({FASTER_WHISPER_WORKLOAD_ID}),
        implemented=True,
        compatible=True,
        current_bind_verified=False,
    )
    with pytest.raises(Task066AudioComputeError) as capability:
        bind_faster_whisper_config(
            route=_cpu_route(),
            config=FasterWhisperConfig(),
            selected_preference=ComputePreference.CPU_EXPLICIT,
            capability=stale,
        )
    assert capability.value.code == "AUDIO_COMPUTE_CPU_IDENTITY_INVALID"


def test_blocked_restart_and_legacy_device_conflict_fail_before_provider_use() -> None:
    blocked = EffectiveWorkloadRoute(
        workload_id=FASTER_WHISPER_WORKLOAD_ID,
        workload_class=WorkloadClass.GPU_PREFERRED_CPU_ALLOWED,
        effective_backend="DISABLED",
        adapter_identity=None,
        reason_code="COMPATIBLE_GPU_NOT_AVAILABLE",
        compatibility_status=CompatibilityStatus.BLOCKED,
    )
    with pytest.raises(Task066AudioComputeError) as rejected:
        bind_faster_whisper_config(
            route=blocked,
            config=FasterWhisperConfig(),
            selected_preference=ComputePreference.AUTO_GPU_FIRST,
            capability=_cpu_capability(),
        )
    assert rejected.value.code == "AUDIO_COMPUTE_ROUTE_BLOCKED"

    with pytest.raises(Task066AudioComputeError) as restart:
        bind_faster_whisper_config(
            route=_cpu_route(restart_required=True),
            config=FasterWhisperConfig(),
            selected_preference=ComputePreference.CPU_EXPLICIT,
            capability=_cpu_capability(),
        )
    assert restart.value.code == "AUDIO_COMPUTE_RESTART_REQUIRED"

    with pytest.raises(Task066AudioComputeError) as conflict:
        bind_faster_whisper_config(
            route=_cpu_route(),
            config=FasterWhisperConfig(device="cuda"),
            selected_preference=ComputePreference.CPU_EXPLICIT,
            capability=_cpu_capability(),
        )
    assert conflict.value.code == "AUDIO_COMPUTE_LEGACY_DEVICE_CONFLICT"


def test_wrong_workload_backend_and_forged_gpu_receipt_fail_closed() -> None:
    wrong_workload = EffectiveWorkloadRoute(
        **{
            **_cpu_route().to_dict(),
            "workload_id": "planning.local.ollama",
            "workload_class": WorkloadClass.GPU_PREFERRED_CPU_ALLOWED,
            "compatibility_status": CompatibilityStatus.PASS,
        }
    )
    with pytest.raises(Task066AudioComputeError) as scope:
        bind_faster_whisper_config(
            route=wrong_workload,
            config=FasterWhisperConfig(),
            selected_preference=ComputePreference.CPU_EXPLICIT,
            capability=_cpu_capability(),
        )
    assert scope.value.code == "AUDIO_COMPUTE_ROUTE_SCOPE"

    unknown_backend = EffectiveWorkloadRoute(
        workload_id=FASTER_WHISPER_WORKLOAD_ID,
        workload_class=WorkloadClass.GPU_PREFERRED_CPU_ALLOWED,
        effective_backend="DIRECTML",
        adapter_identity=None,
        reason_code="COMPATIBLE_GPU_SELECTED",
        compatibility_status=CompatibilityStatus.PASS,
    )
    with pytest.raises(Task066AudioComputeError) as backend:
        bind_faster_whisper_config(
            route=unknown_backend,
            config=FasterWhisperConfig(),
            selected_preference=ComputePreference.AUTO_GPU_FIRST,
            capability=_cpu_capability(),
        )
    assert backend.value.code == "AUDIO_COMPUTE_BACKEND_UNSUPPORTED"

    route, capability = _forged_cuda()
    with pytest.raises(Task066AudioComputeError) as forged:
        bind_faster_whisper_config(
            route=route,
            config=FasterWhisperConfig(),
            selected_preference=ComputePreference.AUTO_GPU_FIRST,
            capability=capability,
        )
    assert forged.value.code == "AUDIO_COMPUTE_GPU_RECEIPT_INVALID"


def test_gpu_route_without_exact_capability_is_never_admitted() -> None:
    route, _capability = _forged_cuda()
    with pytest.raises(Task066AudioComputeError) as missing:
        bind_faster_whisper_config(
            route=route,
            config=FasterWhisperConfig(),
            selected_preference=ComputePreference.AUTO_GPU_FIRST,
            capability=_cpu_capability(),
        )
    assert missing.value.code == "AUDIO_COMPUTE_GPU_IDENTITY_DRIFT"


def test_public_binding_does_not_leak_local_model_or_cache_path(tmp_path) -> None:
    private_model = tmp_path / "private" / "model"
    private_cache = tmp_path / "private" / "cache"
    result = bind_faster_whisper_config(
        route=_cpu_route(),
        config=FasterWhisperConfig(
            model=str(private_model),
            cache_directory=private_cache,
        ),
        selected_preference=ComputePreference.CPU_EXPLICIT,
        capability=_cpu_capability(),
    )
    public = json.dumps(result.binding.public_projection(), sort_keys=True)
    rendered = repr(result)
    assert str(private_model) not in public
    assert str(private_cache) not in public
    assert str(private_model) not in rendered
    assert str(private_cache) not in rendered


def test_local_voice_route_is_projection_only_and_forged_enablement_rejects() -> None:
    projection = project_local_voice_compute_state(_blocked_voice_route())
    assert projection.to_dict() == {
        "workload_id": LOCAL_VOICE_WORKLOAD_ID,
        "adapter_state": "DISABLED_UNTIL_MAPPED",
        "reason_code": "REGISTRY_ADAPTER_DISABLED",
        "execution_allowed": False,
        "model_load_started": False,
        "voice_generation_started": False,
        "training_started": False,
        "owner_voice_used": False,
    }

    forged = EffectiveWorkloadRoute(
        workload_id=LOCAL_VOICE_WORKLOAD_ID,
        workload_class=WorkloadClass.GPU_PREFERRED_CPU_ALLOWED,
        effective_backend="CPU",
        adapter_identity=None,
        reason_code="CPU_EXPLICIT_SELECTED",
        compatibility_status=CompatibilityStatus.PASS,
    )
    with pytest.raises(Task066AudioComputeError) as rejected:
        project_local_voice_compute_state(forged)
    assert rejected.value.code == "AUDIO_VOICE_ROUTE_NOT_DISABLED"
