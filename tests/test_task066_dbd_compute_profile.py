from __future__ import annotations

from dataclasses import replace
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_video_production.dbd_reasoning_local_runtime import (
    LocalReasoningRuntimeService,
    prepare_packaged_dbd_compute_profile,
    read_dbd_compute_profile,
    read_packaged_dbd_compute_profile,
)
from ai_video_production import dbd_training_studio, dbd_trivia_editor
from ai_video_production import dbd_reasoning_local_runtime as runtime_module
from ai_video_production.desktop_compute_policy import (
    ComputePreference,
    DesktopComputeProfile,
    ProfileLoadStatus,
)
from ai_video_production.desktop_install_layout import DesktopInstallLayout


def _layout(tmp_path) -> DesktopInstallLayout:
    binary_root = tmp_path / "bin"
    data_root = tmp_path / "data"
    binary_root.mkdir()
    for relative in ("settings", "logs", "runtime-cache"):
        (data_root / relative).mkdir(parents=True, exist_ok=True)
    return DesktopInstallLayout(
        install_instance_id="bvp-install-0123456789abcdef0123456789abcdef",
        install_scope="PER_USER",
        binary_root=binary_root,
        data_root=data_root,
        task063_descriptor_sha256="sha256:" + "1" * 64,
        layout_sha256="sha256:" + "2" * 64,
        acl_principal_sids=("S-1-5-21-1",),
    )


def test_missing_profile_is_revision_zero_and_cannot_authorize_gpu(tmp_path) -> None:
    layout = _layout(tmp_path)
    snapshot = read_dbd_compute_profile(layout)

    assert snapshot.profile_status is ProfileLoadStatus.DEFAULT_MISSING
    assert snapshot.profile_revision == 0
    assert snapshot.reasoning_reason_code == "COMPUTE_PROFILE_NOT_CONFIGURED"
    assert snapshot.reasoning_execution_authorized is False
    assert snapshot.training_authorized is False
    assert snapshot.training_human_gate_required is True
    assert snapshot.authority_created is False
    assert snapshot.trivia_control_plane_available is True
    assert snapshot.trivia_reason_code == "CPU_ONLY_NOT_GPU_APPLICABLE"
    assert not layout.profile_path.exists()

    with pytest.raises(ValueError, match="cannot grant execution"):
        replace(snapshot, reasoning_execution_authorized=True)
    with pytest.raises(ValueError, match="cannot grant execution"):
        replace(snapshot, training_authorized=True)
    with pytest.raises(ValueError, match="cannot grant execution"):
        replace(snapshot, authority_created=True)
    with pytest.raises(ValueError, match="cannot remove the training Human Gate"):
        replace(snapshot, training_human_gate_required=False)


def test_rejected_profile_is_preserved_as_effect_free_readback(tmp_path) -> None:
    layout = _layout(tmp_path)
    layout.profile_path.write_text('{"revision": NaN}', encoding="utf-8")

    snapshot = read_dbd_compute_profile(layout)

    assert snapshot.profile_status is ProfileLoadStatus.DEFAULT_REJECTED
    assert snapshot.profile_revision == 0
    assert snapshot.reasoning_reason_code == "COMPUTE_PROFILE_REJECTED"
    assert snapshot.reasoning_execution_authorized is False
    assert layout.profile_path.read_text(encoding="utf-8") == '{"revision": NaN}'


def test_cross_instance_profile_is_rejected_without_rewrite(tmp_path) -> None:
    layout = _layout(tmp_path)
    foreign = DesktopComputeProfile(
        install_instance_id="bvp-install-fedcba9876543210fedcba9876543210",
        revision=4,
        selected_preference=ComputePreference.AUTO_GPU_FIRST,
        workload_routes=(),
        updated_at="2026-08-31T00:00:00Z",
    )
    raw = json.dumps(foreign.to_dict(), separators=(",", ":"))
    layout.profile_path.write_text(raw, encoding="utf-8")

    snapshot = read_dbd_compute_profile(layout)

    assert snapshot.profile_status is ProfileLoadStatus.DEFAULT_REJECTED
    assert snapshot.profile_revision == 0
    assert snapshot.install_instance_id == layout.install_instance_id
    assert snapshot.reasoning_execution_authorized is False
    assert layout.profile_path.read_text(encoding="utf-8") == raw


def test_loaded_profile_remains_data_only_without_live_gpu_receipt(tmp_path) -> None:
    layout = _layout(tmp_path)
    profile = DesktopComputeProfile(
        install_instance_id=layout.install_instance_id,
        revision=3,
        selected_preference=ComputePreference.GPU_REQUIRED,
        workload_routes=(),
        updated_at="2026-08-31T00:00:00Z",
    )
    layout.profile_path.write_text(
        json.dumps(profile.to_dict(), separators=(",", ":")), encoding="utf-8"
    )

    snapshot = read_dbd_compute_profile(layout)

    assert snapshot.profile_status is ProfileLoadStatus.LOADED
    assert snapshot.profile_revision == 3
    assert snapshot.selected_preference is ComputePreference.GPU_REQUIRED
    assert snapshot.reasoning_reason_code == "TRUSTED_GPU_ADMISSION_REQUIRED"
    assert snapshot.reasoning_execution_authorized is False
    assert snapshot.training_reason_code == "TRUSTED_GPU_ADMISSION_REQUIRED"
    assert snapshot.training_human_gate_required is True
    assert snapshot.frontend_kind == "TKINTER"
    assert snapshot.ui_gpu_rendering_confirmed is False
    assert snapshot.ui_renderer_reason_code == "TKINTER_GPU_RENDERING_NOT_CONFIRMED"

    service = LocalReasoningRuntimeService(
        workspace_id="workspace-1",
        workspace_root=tmp_path / "workspace",
        compute_profile_readback=snapshot,
    )
    entry = service.catalog_snapshot().entries[0]
    assert entry.status_code == "TRUSTED_GPU_ADMISSION_REQUIRED"
    assert entry.selectable is False


def test_public_profile_route_reason_cannot_mint_gpu_admission(
    tmp_path, monkeypatch
) -> None:
    layout = _layout(tmp_path)
    profile = SimpleNamespace(
        revision=9,
        selected_preference=ComputePreference.GPU_REQUIRED,
        workload_routes=(
            SimpleNamespace(
                workload_id="dbd.reasoning.qwen3_8b",
                reason_code="COMPATIBLE_GPU_SELECTED",
            ),
        ),
    )
    result = SimpleNamespace(
        status=ProfileLoadStatus.LOADED,
        profile=profile,
        reason_code="PROFILE_LOADED",
    )

    class FakeStore:
        def __init__(self, observed_layout):
            assert observed_layout is layout

        def load(self):
            return result

    monkeypatch.setattr(runtime_module, "DesktopComputeProfileStore", FakeStore)

    snapshot = read_dbd_compute_profile(layout)

    assert snapshot.profile_revision == 9
    assert snapshot.reasoning_reason_code == "TRUSTED_GPU_ADMISSION_REQUIRED"
    assert snapshot.reasoning_execution_authorized is False
    assert snapshot.authority_created is False


def test_compute_readback_cannot_mint_tk_gpu_rendering_authority(tmp_path) -> None:
    snapshot = read_packaged_dbd_compute_profile(tmp_path / "missing.exe")

    assert snapshot.frontend_kind == "TKINTER"
    assert snapshot.ui_gpu_rendering_confirmed is False
    assert snapshot.ui_renderer_reason_code == "TKINTER_GPU_RENDERING_NOT_CONFIRMED"
    with pytest.raises(ValueError, match="cannot confirm Tk GPU rendering"):
        replace(snapshot, ui_gpu_rendering_confirmed=True)
    with pytest.raises(ValueError, match="frontend kind is invalid"):
        replace(snapshot, frontend_kind="WEBVIEW2")
    with pytest.raises(ValueError, match="renderer reason is invalid"):
        replace(snapshot, ui_renderer_reason_code="GPU_RENDERING_CONFIRMED")


def test_cpu_explicit_profile_blocks_gpu_required_dbd_without_fallback(tmp_path) -> None:
    layout = _layout(tmp_path)
    profile = DesktopComputeProfile(
        install_instance_id=layout.install_instance_id,
        revision=5,
        selected_preference=ComputePreference.CPU_EXPLICIT,
        workload_routes=(),
        updated_at="2026-08-31T00:00:00Z",
    )
    layout.profile_path.write_text(
        json.dumps(profile.to_dict(), separators=(",", ":")), encoding="utf-8"
    )

    snapshot = read_dbd_compute_profile(layout)
    service = LocalReasoningRuntimeService(
        workspace_id="workspace-1",
        workspace_root=tmp_path / "workspace",
        compute_profile_readback=snapshot,
    )

    assert snapshot.reasoning_reason_code == "CPU_NOT_ADMITTED_FOR_GPU_REQUIRED"
    assert snapshot.training_reason_code == "CPU_NOT_ADMITTED_FOR_GPU_REQUIRED"
    assert snapshot.trivia_reason_code == "CPU_ONLY_NOT_GPU_APPLICABLE"
    entry = service.catalog_snapshot().entries[0]
    assert entry.status_code == "CPU_NOT_ADMITTED_FOR_GPU_REQUIRED"
    assert entry.selectable is False
    assert "CPU指定では実行できません" in entry.status_message_ja
    assert service.store.latest() is None


def test_caller_constructed_loaded_readback_cannot_enable_catalog_or_save(tmp_path) -> None:
    snapshot = read_packaged_dbd_compute_profile(tmp_path / "missing.exe")
    forged = replace(
        snapshot,
        profile_status=ProfileLoadStatus.LOADED,
        install_instance_id="bvp-install-0123456789abcdef0123456789abcdef",
        profile_revision=1,
        profile_reason_code="PROFILE_LOADED",
        reasoning_reason_code="COMPATIBLE_GPU_SELECTED",
    )
    service = LocalReasoningRuntimeService(
        workspace_id="workspace-1",
        workspace_root=tmp_path / "workspace",
        compute_profile_readback=forged,
    )

    entry = service.catalog_snapshot().entries[0]
    assert entry.status_code == "TRUSTED_GPU_ADMISSION_REQUIRED"
    assert entry.selectable is False
    with pytest.raises(ValueError, match="trusted Product compute admission"):
        service.save_selection(entry.candidate.candidate_id)
    assert service.store.latest() is None


def test_packaged_layout_failure_is_body_free_and_keeps_trivia_available(tmp_path) -> None:
    snapshot = read_packaged_dbd_compute_profile(tmp_path / "missing.exe")

    assert snapshot.profile_status is ProfileLoadStatus.DEFAULT_REJECTED
    assert snapshot.install_instance_id is None
    assert snapshot.profile_reason_code == "INSTALL_LAYOUT_UNAVAILABLE"
    assert snapshot.reasoning_execution_authorized is False
    assert snapshot.trivia_control_plane_available is True
    assert str(tmp_path) not in repr(snapshot)


@pytest.mark.parametrize(
    ("family", "application", "backend", "compatibility"),
    [
        ("dbd.training", "DBD_TRAINING_STUDIO", "DISABLED", "BLOCKED"),
        ("dbd.trivia", "DBD_TRIVIA_EDITOR", "CPU", "NOT_APPLICABLE"),
    ],
)
def test_packaged_profile_emits_only_closed_common_diagnostics(
    tmp_path, monkeypatch, family, application, backend, compatibility
) -> None:
    layout = _layout(tmp_path)
    events = []

    class FakeDiagnostics:
        def __init__(self, observed_layout, *, application_family):
            assert observed_layout is layout
            assert application_family == family

        def emit(self, event):
            events.append(event)

    monkeypatch.setattr(runtime_module, "derive_binary_root", lambda _path: layout.binary_root)
    monkeypatch.setattr(runtime_module, "resolve_desktop_install_layout", lambda _root: layout)
    monkeypatch.setattr(runtime_module, "BoundedDesktopDiagnostics", FakeDiagnostics)

    snapshot = prepare_packaged_dbd_compute_profile(
        application_family=family
    )

    assert snapshot.profile_status is ProfileLoadStatus.DEFAULT_MISSING
    assert len(events) == 1
    record = events[0].to_record("2026-08-31T00:00:00Z")
    assert record["application"] == application
    assert record["application_version"] == "0.23.0"
    assert record["effective_backend"] == backend
    assert record["compatibility_result"] == compatibility
    assert record["detected_adapter"] == "NOT_ATTESTED"
    assert str(tmp_path) not in repr(record)


def test_packaged_diagnostics_failure_does_not_block_profile_readback(
    tmp_path, monkeypatch
) -> None:
    layout = _layout(tmp_path)
    monkeypatch.setattr(runtime_module, "derive_binary_root", lambda _path: layout.binary_root)
    monkeypatch.setattr(runtime_module, "resolve_desktop_install_layout", lambda _root: layout)
    monkeypatch.setattr(
        runtime_module,
        "BoundedDesktopDiagnostics",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("private path")),
    )

    snapshot = prepare_packaged_dbd_compute_profile(
        application_family="dbd.trivia"
    )

    assert snapshot.profile_status is ProfileLoadStatus.DEFAULT_MISSING
    assert snapshot.trivia_control_plane_available is True
    assert str(tmp_path) not in repr(snapshot)


def test_cpu_explicit_training_diagnostic_remains_gpu_required_blocked(
    tmp_path, monkeypatch
) -> None:
    layout = _layout(tmp_path)
    profile = DesktopComputeProfile(
        install_instance_id=layout.install_instance_id,
        revision=7,
        selected_preference=ComputePreference.CPU_EXPLICIT,
        workload_routes=(),
        updated_at="2026-08-31T00:00:00Z",
    )
    layout.profile_path.write_text(
        json.dumps(profile.to_dict(), separators=(",", ":")), encoding="utf-8"
    )
    events = []

    class FakeDiagnostics:
        def __init__(self, observed_layout, *, application_family):
            assert observed_layout is layout
            assert application_family == "dbd.training"

        def emit(self, event):
            events.append(event)

    monkeypatch.setattr(runtime_module, "derive_binary_root", lambda _path: layout.binary_root)
    monkeypatch.setattr(runtime_module, "resolve_desktop_install_layout", lambda _root: layout)
    monkeypatch.setattr(runtime_module, "BoundedDesktopDiagnostics", FakeDiagnostics)

    snapshot = prepare_packaged_dbd_compute_profile(
        application_family="dbd.training"
    )

    assert snapshot.profile_status is ProfileLoadStatus.LOADED
    assert snapshot.training_reason_code == "CPU_NOT_ADMITTED_FOR_GPU_REQUIRED"
    assert snapshot.training_authorized is False
    assert len(events) == 1
    record = events[0].to_record("2026-08-31T00:00:00Z")
    assert record["effective_backend"] == "DISABLED"
    assert record["compatibility_result"] == "BLOCKED"
    assert record["reason_code"] == "CPU_NOT_ADMITTED_FOR_GPU_REQUIRED"
    assert record["detected_adapter"] == "NOT_ATTESTED"
    assert str(tmp_path) not in repr(record)


def test_unknown_packaged_application_family_is_rejected(tmp_path) -> None:
    with pytest.raises(ValueError, match="application family is invalid"):
        prepare_packaged_dbd_compute_profile(
            application_family="dbd.unknown"
        )


def test_packaged_prepare_uses_only_internal_process_executable(
    tmp_path, monkeypatch
) -> None:
    executable = tmp_path / "private" / "BAI DbD Training Studio.exe"
    observed = []

    def derive(value):
        observed.append(value)
        raise ValueError("layout unavailable")

    monkeypatch.setattr(runtime_module.sys, "executable", str(executable))
    monkeypatch.setattr(runtime_module, "derive_binary_root", derive)

    snapshot = prepare_packaged_dbd_compute_profile(
        application_family="dbd.training"
    )

    assert observed == [str(executable)]
    assert snapshot.profile_status is ProfileLoadStatus.DEFAULT_REJECTED
    assert snapshot.authority_created is False
    assert str(tmp_path) not in repr(snapshot)


def test_app_mains_forward_profile_readback_without_creating_authority(
    tmp_path, monkeypatch
) -> None:
    snapshot = read_packaged_dbd_compute_profile(tmp_path / "missing.exe")
    observed = []

    def training_launch(**kwargs):
        observed.append(("training", kwargs["compute_profile_readback"]))
        return 11

    def trivia_launch(**kwargs):
        observed.append(("trivia", kwargs["compute_profile_readback"]))
        return 12

    monkeypatch.setattr(dbd_training_studio, "launch_training_studio", training_launch)
    monkeypatch.setattr(dbd_trivia_editor, "launch_editor", trivia_launch)

    assert dbd_training_studio.main(compute_profile_readback=snapshot) == 11
    assert dbd_trivia_editor.main(compute_profile_readback=snapshot) == 12
    assert observed == [("training", snapshot), ("trivia", snapshot)]
    assert snapshot.reasoning_execution_authorized is False
    assert snapshot.training_authorized is False


@pytest.mark.parametrize(
    ("entry_name", "application_module", "family"),
    [
        (
            "task049_training_studio_windows_entry.py",
            dbd_training_studio,
            "dbd.training",
        ),
        (
            "task049_trivia_editor_windows_entry.py",
            dbd_trivia_editor,
            "dbd.trivia",
        ),
    ],
)
def test_packaged_entries_bind_internal_executable_profile_once(
    tmp_path, monkeypatch, entry_name, application_module, family
) -> None:
    snapshot = read_packaged_dbd_compute_profile(tmp_path / "missing.exe")
    observed = []

    def prepare(*, application_family):
        observed.append(("prepare", application_family))
        return snapshot

    def app_main(*, compute_profile_readback):
        observed.append(("main", compute_profile_readback))
        return 17

    monkeypatch.setattr(
        runtime_module, "prepare_packaged_dbd_compute_profile", prepare
    )
    monkeypatch.setattr(application_module, "main", app_main)
    entry_path = Path(__file__).resolve().parents[1] / "packaging" / entry_name
    spec = importlib.util.spec_from_file_location(
        "task066_test_" + entry_name.removesuffix(".py"), entry_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.packaged_main() == 17
    assert observed == [
        ("prepare", family),
        ("main", snapshot),
    ]


def test_training_start_log_does_not_expose_executable_path_on_cancel(
    monkeypatch
) -> None:
    class FakeDiagnostics:
        enabled = True

        def __init__(self) -> None:
            self.events = []
            self.closed = 0

        def emit(self, event, **fields) -> None:
            self.events.append((event, fields))

        def close(self) -> None:
            self.closed += 1

    diagnostics = FakeDiagnostics()
    monkeypatch.setattr(dbd_training_studio, "get_diagnostic_logger", lambda: diagnostics)
    monkeypatch.setattr(
        dbd_training_studio,
        "choose_workspace_before_launch",
        lambda _workspace: (_ for _ in ()).throw(
            dbd_training_studio.WorkspaceSelectionCancelled()
        ),
    )
    monkeypatch.setattr(
        dbd_training_studio.sys,
        "executable",
        r"C:\owner\private\BAI DbD Training Studio.exe",
    )
    monkeypatch.setattr(dbd_training_studio.sys, "frozen", True, raising=False)

    assert dbd_training_studio.launch_training_studio([]) == 0
    assert diagnostics.closed == 1
    rendered = repr(diagnostics.events)
    assert r"C:\owner\private" not in rendered
    assert diagnostics.events[0][1]["executable_kind"] == "PACKAGED_EXECUTABLE"
    assert diagnostics.events[-1] == (
        "APP_EXIT", {"reason": "WORKSPACE_SELECTION_CANCELLED"}
    )
