from __future__ import annotations

import pytest

from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.errors import ProductError
from ai_video_production.task036_shell_ui import HTML, Task036ShellBridge


def test_ui_is_professional_nle_layout_not_chat_first():
    assert "TIMELINE" not in HTML  # track labels are Japanese/product-specific, not a placeholder title
    assert "文字起こし / カット候補" in HTML
    assert "インスペクタ / AI" in HTML
    assert "A3　ナレーション" in HTML
    assert "BAI Video Production" in HTML
    assert "window.pywebview.api" in HTML
    assert "chat" not in HTML.lower()


def test_bridge_exposes_snapshot_and_workspace_only():
    service = ShellApplicationService(product_version="0.19.0")
    service.open_project_context(project_id="p1", display_name="Project 1")
    bridge = Task036ShellBridge(service)
    snapshot = bridge.snapshot()
    assert snapshot["project"]["project_id"] == "p1"
    changed = bridge.set_workspace({"workspace": "EDIT"})
    assert changed["current_workspace"] == "EDIT"
    assert not hasattr(bridge, "exec")
    assert not hasattr(bridge, "open_file")


def test_bridge_rejects_extra_request_fields():
    service = ShellApplicationService(product_version="0.19.0")
    bridge = Task036ShellBridge(service)
    with pytest.raises(ProductError) as exc:
        bridge.set_workspace({"workspace": "EDIT", "command": "whoami"})
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"


def _review_bridge():
    from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
    from ai_video_production.desktop_editing_review import ReviewWorkspaceState, Task036ReviewFacade

    h = lambda ch: "sha256:" + ch * 64
    manifest = CutCandidateManifest(
        source_asset_id="ASSET-00000000000000000000000000",
        analysis_audio_sha256=h("1"),
        analysis_sample_rate=48_000,
        source_duration_us=5_000_000,
        config_sha256=h("2"),
        transcript_manifest_sha256=h("3"),
        candidates=(CutCandidate("cut-000001", CutCandidateKind.SILENCE, 1_000_000, 1_500_000, 90, ("SILENCE",)),),
        keep_blocks=(),
    )
    service = ShellApplicationService(product_version="0.19.0", token_factory=iter(("review", "approve")).__next__)
    service.open_project_context(project_id="p1", display_name="Project 1")
    review = Task036ReviewFacade(service, ReviewWorkspaceState(manifest))
    return Task036ShellBridge(service, review=review)


def test_bridge_cut_review_is_allowlisted_and_stateful():
    bridge = _review_bridge()
    selected = bridge.select_candidate({"candidate_id": "cut-000001"})
    assert selected["selected_candidate_id"] == "cut-000001"
    result = bridge.review_candidate({"candidate_id": "cut-000001", "decision": "KEEP"})
    assert result["review"]["unresolved_count"] == 0
    prepared = bridge.prepare_edit_plan_approval({})
    assert prepared["cut_count"] == 0
    approved = bridge.approve_edit_plan({
        "confirmation_id": prepared["confirmation_id"],
        "draft_plan_sha256": prepared["draft_plan_sha256"],
        "approved_by": "owner",
    })
    assert approved["review"]["approved_plan"]["approval_state"] == "APPROVED"


def test_bridge_rejects_arbitrary_fields_on_review_methods():
    bridge = _review_bridge()
    with pytest.raises(ProductError) as exc:
        bridge.select_candidate({"candidate_id": "cut-000001", "exec": "whoami"})
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"


def test_html_includes_cut_overlay_and_human_review_controls():
    assert 'data-track="CUT_OVERLAY"' in HTML
    assert 'id="keepButton"' in HTML
    assert 'id="cutButton"' in HTML
    assert 'id="approvePlanButton"' in HTML
    assert "KEEP/CUTは明示的なHuman Decision" in HTML


def test_html_exposes_native_chooser_controls_without_starting_product_operations():
    assert 'id="chooseProjectButton"' in HTML
    assert 'id="chooseMediaButton"' in HTML
    assert 'id="chooseHandoffButton"' in HTML
    assert 'id="dialogStatus"' in HTML
    assert 'aria-live="polite"' in HTML
    assert "choose_project_folder" in HTML
    assert "choose_media_source" in HTML
    assert "choose_handoff_folder" in HTML
    assert "操作は未開始" in HTML


def test_html_exposes_allowlisted_post_review_workflow_action():
    assert 'id="workflowActionButton"' in HTML
    assert "workflow_status" in HTML
    assert "choose_and_ingest_media" in HTML
    assert "run_local_transcription" in HTML
    assert "create_runtime_subtitle_workspace" in HTML
    assert "generate_runtime_cut_candidates" in HTML
    assert "compile_resolve_assembly" in HTML
    assert "prepare_resolve_apply" in HTML
    assert "apply_resolve_assembly" in HTML
    assert "prepare_native_render_confirmation" in HTML
    assert "execute_native_render" in HTML
    assert "bind_runtime_render_qa" in HTML
    assert "create_editor_handoff" in HTML


def test_html_has_keyboard_focus_and_screen_reader_landmarks():
    assert "button:focus-visible" in HTML
    assert 'class="skip-link"' in HTML
    assert "applyAccessibility()" in HTML
    assert "映像プレビュー" in HTML
    assert "編集タイムライン" in HTML
    assert "候補をカットする" in HTML
    assert "@media(max-width:900px)" in HTML
    assert ".main{grid-template-columns:1fr}" in HTML


def test_html_promotes_production_control_without_task038_authority_shortcut():
    assert 'data-w="PRODUCTION_CONTROL"' in HTML
    assert 'id="productionWorkspace"' in HTML
    assert 'id="productionSlots"' in HTML
    assert "production_snapshot" in HTML
    assert "production_prepare_lock" in HTML
    assert "production_apply_lock" in HTML
    assert "expected_snapshot_sha256:model.snapshot_sha256" in HTML
    assert "prepared.asset_sha256" in HTML
    assert "textContent=`${candidate.candidate_id}" in HTML
    assert "production_accept" not in HTML
    assert "production_reject" not in HTML


def test_production_bridge_is_unavailable_until_trusted_project_binding():
    service = ShellApplicationService(product_version="0.19.0")
    bridge = Task036ShellBridge(service)
    assert bridge.production_snapshot({}) == {"available": False}
    with pytest.raises(ProductError) as exc:
        bridge.production_prepare_lock({
            "slot_id": "slot-1",
            "candidate_id": "candidate-1",
            "expected_snapshot_sha256": "sha256:" + "a" * 64,
        })
    assert exc.value.code == "ERR_TASK037_PRODUCTION_CONTROL_NOT_BOUND"


def test_production_bridge_routes_only_exact_lock_confirmation_contract():
    class ProductionControlStub:
        def __init__(self):
            self.prepared = None
            self.applied = None

        def snapshot(self):
            return {"snapshot_sha256": "sha256:" + "a" * 64, "slots": []}

        def prepare_lock(self, **values):
            self.prepared = values
            return {"confirmation_id": "lock-1", **values}

        def apply_lock(self, *, confirmation_id):
            self.applied = confirmation_id
            return {"locked": True}

    control = ProductionControlStub()
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.19.0"),
        production_control=control,
    )
    snapshot = bridge.production_snapshot({})
    assert snapshot["available"] is True
    prepared = bridge.production_prepare_lock({
        "slot_id": "slot-1",
        "candidate_id": "candidate-1",
        "expected_snapshot_sha256": snapshot["snapshot_sha256"],
    })
    assert control.prepared == {
        "slot_id": "slot-1",
        "candidate_id": "candidate-1",
        "expected_snapshot_sha256": snapshot["snapshot_sha256"],
    }
    assert bridge.production_apply_lock({"confirmation_id": prepared["confirmation_id"]}) == {"locked": True}
    assert control.applied == "lock-1"
    with pytest.raises(ProductError) as exc:
        bridge.production_apply_lock({"confirmation_id": "lock-1", "force": True})
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"


def test_integrated_bridge_plan_approval_advances_workflow_stage():
    from ai_video_production.desktop_editing_application import Task036EditingApplication

    source_bridge = _review_bridge()
    values = iter(("review-1", "approve"))
    app = Task036EditingApplication.create(
        product_version="0.19.0",
        project_id="project-1",
        display_name="Project 1",
        source_asset_sha256="sha256:" + "9" * 64,
        cut_manifest=source_bridge.review.state.manifest,
        token_factory=lambda: next(values),
    )
    bridge = Task036ShellBridge(app.shell, application=app)
    bridge.review_candidate({"candidate_id": "cut-000001", "decision": "CUT"})
    prepared = bridge.prepare_edit_plan_approval()
    result = bridge.approve_edit_plan({
        "confirmation_id": prepared["confirmation_id"],
        "draft_plan_sha256": prepared["draft_plan_sha256"],
        "approved_by": "owner",
    })
    assert "resolve.assembly.prepare" in result["available_commands"]
    vm = bridge.view_model()
    assert vm["shell"]["next_recommended_action"] == "resolve.assembly.prepare"


def test_bridge_native_dialog_methods_are_allowlisted_and_do_not_start_operations(tmp_path):
    from ai_video_production.task036_native_dialog import Task036NativeDialogService

    media = tmp_path / "source.mp4"
    media.write_bytes(b"media")
    project = tmp_path / "project"; project.mkdir()
    handoff = tmp_path / "handoff"; handoff.mkdir()

    class Backend:
        def choose_open_media(self): return str(media)
        def choose_project_folder(self): return str(project)
        def choose_handoff_folder(self): return str(handoff)

    service = ShellApplicationService(product_version="0.19.0")
    bridge = Task036ShellBridge(service, native_dialog=Task036NativeDialogService(Backend()))
    selected = bridge.choose_media_source({})
    assert selected["selected"] is True
    assert selected["operation_started"] is False
    assert selected["persisted_to_product_state"] is False
    assert bridge.choose_project_folder()["path_kind"] == "DIRECTORY"
    assert bridge.choose_handoff_folder()["host_path"] == str(handoff)


def test_bridge_native_dialog_rejects_unbound_or_extra_fields():
    service = ShellApplicationService(product_version="0.19.0")
    bridge = Task036ShellBridge(service)
    with pytest.raises(ProductError) as exc:
        bridge.choose_media_source()
    assert exc.value.code == "ERR_TASK036_NATIVE_DIALOG_NOT_BOUND"
    with pytest.raises(ProductError) as exc:
        bridge.choose_project_folder({"path": "C:/unsafe"})
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"
