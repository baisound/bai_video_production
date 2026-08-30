from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from pathlib import Path

import pytest

from ai_video_production.desktop_compute_policy import (
    AdapterCapability,
    AdapterIdentity,
    CompatibilityStatus,
    ComputePreference,
    DesktopComputePolicyError,
    DesktopComputeProfileStore,
    EffectiveWorkloadRoute,
    ProfileLoadStatus,
    frozen_workload_registry,
    rank_gpu_capabilities,
    resolve_workload_route,
)
from ai_video_production.desktop_install_layout import DesktopInstallLayout


INSTANCE = "bvp-install-" + "1" * 32


def _identity(suffix: str) -> AdapterIdentity:
    return AdapterIdentity(
        luid=f"LUID-{suffix}",
        vendor_id="10DE",
        device_id=f"DEVICE-{suffix}",
        subsystem_id="SUBSYSTEM",
        driver_instance_digest="sha256:" + suffix * 64,
    )


def _gpu(suffix: str, memory: int, *workloads: str, discrete: bool = True) -> AdapterCapability:
    return AdapterCapability(
        backend="CUDA",
        device_kind="GPU",
        identity=_identity(suffix),
        supported_workloads=frozenset(workloads),
        implemented=True,
        compatible=True,
        discrete=discrete,
        dedicated_memory_bytes=memory,
        current_bind_verified=True,
        loaded_runtime_versions=("CUDA-TEST-1",),
    )


def _cpu(*workloads: str) -> AdapterCapability:
    return AdapterCapability(
        backend="CPU",
        device_kind="CPU",
        identity=None,
        supported_workloads=frozenset(workloads),
        implemented=True,
        compatible=True,
        current_bind_verified=True,
    )


def _layout(tmp_path: Path) -> DesktopInstallLayout:
    data = tmp_path / "data"
    for leaf in ("settings", "logs", "runtime-cache", "settings/installation"):
        (data / leaf).mkdir(parents=True, exist_ok=True)
    return DesktopInstallLayout(
        install_instance_id=INSTANCE,
        install_scope="PER_USER",
        binary_root=tmp_path,
        data_root=data,
        task063_descriptor_sha256="sha256:" + "a" * 64,
        layout_sha256="sha256:" + "b" * 64,
        acl_principal_sids=("S-1-5-21-1000",),
    )


def test_frozen_registry_ids_classes_and_cpu_ceilings_are_exact() -> None:
    registry = frozen_workload_registry()
    entries = {item["workload_id"]: item for item in registry["workloads"]}
    assert list(entries) == [
        "planning.local.ollama",
        "image.local.comfyui",
        "video.local.generation",
        "audio.asr.faster_whisper",
        "audio.voice.local",
        "dbd.reasoning.qwen3_8b",
        "dbd.training",
        "dbd.trivia.editor",
        "voice.capture.controller",
        "key.helper",
    ]
    assert entries["video.local.generation"]["adapter_admission_state"] == "DISABLED_UNTIL_IMPLEMENTED"
    assert entries["dbd.training"]["adapter_admission_state"] == "HUMAN_GATE_REQUIRED"
    assert entries["image.local.comfyui"]["cpu_fallback_eligible"] is False


def test_gpu_ranking_prefers_compatible_discrete_memory_then_stable_identity() -> None:
    workload = "image.local.comfyui"
    integrated = _gpu("f", 64_000, workload, discrete=False)
    low = _gpu("c", 8_000, workload)
    tied_later = _gpu("b", 16_000, workload)
    tied_first = _gpu("a", 16_000, workload)

    ranked = rank_gpu_capabilities([integrated, low, tied_later, tied_first])
    assert ranked[0].identity == tied_first.identity
    route = resolve_workload_route(
        workload,
        ComputePreference.AUTO_GPU_FIRST,
        [integrated, low, tied_later, tied_first],
    )
    assert route.compatibility_status is CompatibilityStatus.BLOCKED
    assert route.reason_code == "COMPATIBLE_GPU_NOT_AVAILABLE"


def test_gpu_required_never_silently_falls_back_to_cpu() -> None:
    workload = "image.local.comfyui"
    for preference in (ComputePreference.AUTO_GPU_FIRST, ComputePreference.GPU_REQUIRED, ComputePreference.CPU_EXPLICIT):
        route = resolve_workload_route(workload, preference, [_cpu(workload)])
        assert route.compatibility_status is CompatibilityStatus.BLOCKED
        assert route.effective_backend == "DISABLED"
        assert route.adapter_identity is None


def test_current_bind_required_cannot_be_enabled_by_unbound_capability() -> None:
    capability = _gpu("a", 16_000, "image.local.comfyui")
    unbound = AdapterCapability(
        backend=capability.backend,
        device_kind=capability.device_kind,
        identity=capability.identity,
        supported_workloads=capability.supported_workloads,
        implemented=True,
        compatible=True,
        discrete=True,
        dedicated_memory_bytes=capability.dedicated_memory_bytes,
        current_bind_verified=False,
        loaded_runtime_versions=capability.loaded_runtime_versions,
    )
    route = resolve_workload_route(
        "image.local.comfyui",
        ComputePreference.AUTO_GPU_FIRST,
        [unbound],
    )
    assert route.compatibility_status is CompatibilityStatus.BLOCKED
    assert route.reason_code == "COMPATIBLE_GPU_NOT_AVAILABLE"


@pytest.mark.parametrize(
    "workload",
    [
        "planning.local.ollama",
        "image.local.comfyui",
        "video.local.generation",
        "audio.asr.faster_whisper",
        "audio.voice.local",
        "dbd.reasoning.qwen3_8b",
        "dbd.training",
    ],
)
def test_unsealed_registry_blocks_forged_gpu_capability_for_every_gpu_workload(
    workload: str,
) -> None:
    route = resolve_workload_route(
        workload,
        ComputePreference.AUTO_GPU_FIRST,
        [_gpu("a", 16_000, workload)],
    )
    assert route.compatibility_status is CompatibilityStatus.BLOCKED
    assert route.effective_backend == "DISABLED"


def test_cpu_fallback_is_only_declared_and_visible_before_execution() -> None:
    workload = "planning.local.ollama"
    route = resolve_workload_route(workload, ComputePreference.AUTO_GPU_FIRST, [_cpu(workload)])
    assert route.effective_backend == "CPU"
    assert route.reason_code == "AUTO_GPU_UNAVAILABLE_CPU_FALLBACK"
    assert route.cpu_fallback_visible_before_execution is True


def test_frozen_disabled_and_human_gate_entries_cannot_be_enabled_by_probe_claim() -> None:
    disabled = resolve_workload_route(
        "video.local.generation",
        ComputePreference.AUTO_GPU_FIRST,
        [_gpu("a", 16_000, "video.local.generation")],
    )
    gated = resolve_workload_route(
        "dbd.training",
        ComputePreference.AUTO_GPU_FIRST,
        [_gpu("b", 16_000, "dbd.training")],
    )
    assert disabled.reason_code == "REGISTRY_ADAPTER_DISABLED"
    assert gated.reason_code == "HUMAN_GATE_REQUIRED"


def test_profile_store_atomic_save_readback_and_revision_conflict(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    receipt = layout.installer_receipt_path
    receipt.write_text("installer-owned", encoding="utf-8")
    store = DesktopComputeProfileStore(layout)
    assert store.load().status is ProfileLoadStatus.DEFAULT_MISSING

    saved = store.save(selected_preference=ComputePreference.GPU_REQUIRED, expected_revision=0)
    loaded = store.load()

    assert loaded.status is ProfileLoadStatus.LOADED
    assert loaded.profile == saved.profile
    assert loaded.profile.revision == 1
    assert receipt.read_text(encoding="utf-8") == "installer-owned"
    with pytest.raises(DesktopComputePolicyError, match="revision conflict"):
        store.save(selected_preference=ComputePreference.CPU_EXPLICIT, expected_revision=0)


def test_invalid_profile_is_preserved_and_not_overwritten(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    layout.profile_path.write_text('{"schema_version":"9.0.0"}', encoding="utf-8")
    original = layout.profile_path.read_bytes()
    store = DesktopComputeProfileStore(layout)

    result = store.load()

    assert result.status is ProfileLoadStatus.DEFAULT_REJECTED
    assert result.profile.selected_preference is ComputePreference.AUTO_GPU_FIRST
    assert result.rejected_source_preserved is True
    with pytest.raises(DesktopComputePolicyError, match="preserved"):
        store.save(selected_preference=ComputePreference.AUTO_GPU_FIRST, expected_revision=0)
    assert layout.profile_path.read_bytes() == original


def test_atomic_failure_preserves_previous_profile(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    store = DesktopComputeProfileStore(layout)
    first = store.save(selected_preference=ComputePreference.AUTO_GPU_FIRST, expected_revision=0)
    original = layout.profile_path.read_bytes()

    def fail(stage: str, _: Path) -> None:
        if stage == "before_replace":
            raise RuntimeError("synthetic crash")

    with pytest.raises(RuntimeError, match="synthetic crash"):
        store.save(
            selected_preference=ComputePreference.GPU_REQUIRED,
            expected_revision=first.profile.revision,
            failure_injector=fail,
        )
    assert layout.profile_path.read_bytes() == original
    assert store.load().profile == first.profile


def test_concurrent_same_revision_has_one_winner(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    store = DesktopComputeProfileStore(layout)

    def attempt(preference: ComputePreference) -> str:
        try:
            store.save(selected_preference=preference, expected_revision=0)
            return "PASS"
        except DesktopComputePolicyError:
            return "CONFLICT"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [ComputePreference.GPU_REQUIRED, ComputePreference.CPU_EXPLICIT]))
    assert sorted(results) == ["CONFLICT", "PASS"]
    assert store.load().profile.revision == 1


def test_profile_rejects_backend_routes_that_contradict_selected_preference(tmp_path: Path) -> None:
    workload = "planning.local.ollama"
    cpu_fallback = resolve_workload_route(
        workload,
        ComputePreference.AUTO_GPU_FIRST,
        [_cpu(workload)],
    )
    gpu = _gpu("a", 16_000, workload)
    gpu_route = EffectiveWorkloadRoute(
        workload_id=workload,
        workload_class=cpu_fallback.workload_class,
        effective_backend="CUDA",
        adapter_identity=gpu.identity,
        reason_code="COMPATIBLE_GPU_SELECTED",
        compatibility_status=CompatibilityStatus.PASS,
        loaded_runtime_versions=gpu.loaded_runtime_versions,
    )
    store = DesktopComputeProfileStore(_layout(tmp_path))
    with pytest.raises(DesktopComputePolicyError, match="GPU-required preference"):
        store.save(
            selected_preference=ComputePreference.GPU_REQUIRED,
            workload_routes=(cpu_fallback,),
            expected_revision=0,
        )
    with pytest.raises(DesktopComputePolicyError, match="explicit CPU preference"):
        store.save(
            selected_preference=ComputePreference.CPU_EXPLICIT,
            workload_routes=(gpu_route,),
            expected_revision=0,
        )
    with pytest.raises(DesktopComputePolicyError, match="outside local admission"):
        store.save(
            selected_preference=ComputePreference.AUTO_GPU_FIRST,
            workload_routes=(replace(gpu_route, effective_backend="OPENAI_CLOUD"),),
            expected_revision=0,
        )
    with pytest.raises(DesktopComputePolicyError, match="live Evidence"):
        store.save(
            selected_preference=ComputePreference.AUTO_GPU_FIRST,
            workload_routes=(gpu_route,),
            expected_revision=0,
        )
    with pytest.raises(DesktopComputePolicyError, match="fallback status"):
        store.save(
            selected_preference=ComputePreference.AUTO_GPU_FIRST,
            workload_routes=(replace(cpu_fallback, compatibility_status=CompatibilityStatus.NOT_APPLICABLE),),
            expected_revision=0,
        )


def test_profile_and_workload_schema_mirrors_are_byte_exact() -> None:
    root = Path(__file__).parents[1]
    for name in (
        "desktop-compute-profile.schema.json",
        "desktop-compute-workload-registry.schema.json",
    ):
        assert (root / "schemas" / name).read_bytes() == (
            root / "src" / "ai_video_production" / "schema_resources" / name
        ).read_bytes()
