from __future__ import annotations

from contextlib import contextmanager

import pytest

from ai_video_production.ai_connections import (
    AiConnectionProfile,
    AiWorkload,
    ConnectionAvailability,
    CostClass,
    ModelRoute,
    ProviderFamily,
    SelectionMode,
)
from ai_video_production.connection_settings_store import ConnectionSettingsStore
from ai_video_production.connection_settings_web import ConnectionSettingsWebService
from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.errors import ProductError, ProductErrorCategory
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


def test_visual_generation_handoff_bridge_requires_every_exact_source_and_stays_read_only():
    service = ShellApplicationService(product_version="0.21.0")
    unavailable = Task036ShellBridge(service).visual_generation_handoff_snapshot({})
    assert unavailable == {
        "available": False,
        "missing_sources": ["production", "safety", "prompt", "queue", "execution", "adoption"],
        "provider_execution_authorized": False,
        "human_decision_created": False,
        "asset_or_timeline_mutation_started": False,
    }

    class Stub:
        def __init__(self, value):
            self.value = value

        def snapshot(self):
            return self.value

    h = lambda char: "sha256:" + char * 64
    production = Stub({
        "project_id": "project-1", "snapshot_sha256": h("1"),
        "slots": [{"slot_id": "slot-1", "scene_id": "SC01", "slot_kind": "VIDEO", "required": True,
                   "status": "EMPTY", "stale_state": "CURRENT", "candidates": []}],
    })
    safety = Stub({"project_id": "project-1", "safety_snapshot_sha256": h("2"), "scenes": [
        {"scene": {"scene_id": "SC01"}, "feasibility_status": "PASS"},
    ]})
    prompt = Stub({"project_id": "project-1", "prompt_snapshot_sha256": h("3"), "prompts": [
        {"prompt_id": "prompt-1", "prompt_version": 1, "scene_id": "SC01", "slot_id": "slot-1"},
    ]})
    queue = Stub({"project_id": "project-1", "queue_snapshot_sha256": h("4"), "entries": []})
    execution = Stub({"project_id": "project-1", "execution_snapshot_sha256": h("5"), "queue_snapshot_sha256": h("4"), "latest_executions": []})
    adoption = Stub({"project_id": "project-1", "adoption_snapshot_sha256": h("6"), "eligible_completed_outputs": [], "latest_adoptions": []})
    bridge = Task036ShellBridge(
        service,
        production_control=production,
        generation_safety_application=safety,
        prompt_evidence_application=prompt,
        generation_queue_application=queue,
        generation_execution_application=execution,
        generation_output_adoption_application=adoption,
    )
    result = bridge.visual_generation_handoff_snapshot({})
    assert result["available"] is True
    assert result["rows"][0]["state"] == "PROMPT_READY"
    assert result["provider_execution_authorized"] is False
    assert result["human_decision_created"] is False
    assert result["asset_or_timeline_mutation_started"] is False
    with pytest.raises(ProductError) as exc:
        bridge.visual_generation_handoff_snapshot({"execute": True})
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"


def _connection_settings_service(tmp_path):
    profile = AiConnectionProfile(
        "desktop-profile",
        "1",
        SelectionMode.AUTO,
        (
            ModelRoute(
                "local-image",
                AiWorkload.IMAGE,
                ProviderFamily.COMFYUI,
                "comfyui",
                "workflow-v1",
                CostClass.LOCAL_FREE_AI,
                priority=10,
                capabilities=("IMAGE_GENERATION",),
            ),
            ModelRoute(
                "cloud-image",
                AiWorkload.IMAGE,
                ProviderFamily.OPENAI,
                "openai",
                "configured-image-model",
                CostClass.CLOUD_PAID_AI,
                priority=20,
                credential_ref="credential://openai/default",
                capabilities=("IMAGE_GENERATION",),
            ),
        ),
    )
    return ConnectionSettingsWebService(
        tmp_path / "ai-connection-settings.json",
        profile,
        0,
        ConnectionAvailability(frozenset({"local-image", "cloud-image"})),
    )


def test_connection_settings_bridge_projects_and_updates_exact_modes_without_execution(tmp_path):
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        connection_settings=_connection_settings_service(tmp_path),
    )
    snapshot = bridge.connection_settings_snapshot({})
    assert snapshot["available"] is True
    assert snapshot["revision"] == 0
    assert snapshot["credential_values_redisplayed"] is False
    assert snapshot["provider_execution_started"] is False
    assert snapshot["paid_execution_authorized"] is False
    assert "credential://" not in str(snapshot)

    modes = {row["workload"]: row["selection_mode"] for row in snapshot["workloads"]}
    modes["IMAGE"] = "OFFLINE_ONLY"
    preferred = {row["workload"]: None for row in snapshot["workloads"]}
    preferred["IMAGE"] = "local-image"
    updated = bridge.connection_settings_update({
        "revision": 0,
        "workload_modes": modes,
        "preferred_route_ids": preferred,
    })
    assert updated["revision"] == 1
    assert updated["provider_execution_started"] is False
    loaded = ConnectionSettingsStore.load(tmp_path / "ai-connection-settings.json").record
    assert loaded.profile.mode_for(AiWorkload.IMAGE) is SelectionMode.OFFLINE_ONLY
    assert loaded.profile.routes[0].route_id == "local-image"


def test_connection_settings_bridge_is_fail_closed_when_unbound_or_request_is_broad(tmp_path):
    bridge = Task036ShellBridge(ShellApplicationService(product_version="0.21.0"))
    assert bridge.connection_settings_snapshot({})["available"] is False
    with pytest.raises(ProductError) as exc:
        bridge.connection_settings_update({"revision": 0, "exec": "provider"})
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"

    bound = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        connection_settings=_connection_settings_service(tmp_path),
    )
    with pytest.raises(ProductError) as exc:
        bound.connection_settings_snapshot({"secret": True})
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"


def test_pux2_settings_ui_uses_existing_task028_contract_and_never_collects_secrets():
    assert "connection_settings_snapshot" in HTML
    assert "connection_settings_update" in HTML
    assert "data-connection-mode" in HTML
    assert "data-connection-route" in HTML
    assert "Secret本文の表示・入力・削除はこのShellでは行いません" in HTML
    assert "保存はProvider実行・課金・生成を許可しません" in HTML


def test_pux2a1_model_selection_bridge_reuses_existing_receipts_without_audio_overlap(tmp_path):
    class PromptApplicationStub:
        def snapshot(self):
            return {"prompts": [{
                "prompt_id": "prompt-1", "prompt_version": 1, "scene_id": "scene-1", "slot_id": "slot-1",
                "compilation_binding": {"selected_route_id": "local-image"},
            }]}

    class QuickApplicationStub:
        def snapshot(self):
            return {"intents": [{
                "intent_id": "quick-1", "intent_version": 1, "mode": "IMAGE", "scene_id": "scene-1",
                "selected_route_id": "local-image", "selected_capability": "IMAGE_GENERATION",
            }]}

    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        connection_settings=_connection_settings_service(tmp_path),
        prompt_evidence_application=PromptApplicationStub(),
        quick_generation_application=QuickApplicationStub(),
    )
    snapshot = bridge.model_selection_snapshot({})
    assert snapshot["available"] is True
    assert snapshot["scene_bindings"][0]["selected_route_id"] == "local-image"
    assert snapshot["quick_bindings"][0]["coordinate_state"] == "CURRENT_CONFIGURED"
    assert snapshot["delegated_audio_owner"] == "DEVELOPER2"
    assert snapshot["provider_execution_started"] is False
    assert snapshot["paid_execution_authorized"] is False
    assert snapshot["generation_started"] is False
    assert "credential://" not in str(snapshot)


def test_pux2a1_model_selection_bridge_fails_closed_when_unbound_or_request_is_broad():
    bridge = Task036ShellBridge(ShellApplicationService(product_version="0.21.0"))
    assert bridge.model_selection_snapshot({}) == {
        "available": False,
        "unavailable_reason": "CONNECTION_SETTINGS_NOT_BOUND",
        "delegated_audio_owner": "DEVELOPER2",
        "credential_values_redisplayed": False,
        "provider_execution_started": False,
        "paid_execution_authorized": False,
        "generation_started": False,
    }
    with pytest.raises(ProductError) as exc:
        bridge.model_selection_snapshot({"execute": True})
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"


def test_pux2a1_main_pages_expose_project_selection_and_persisted_coordinate_projection():
    assert "model_selection_snapshot" in HTML
    assert "planningModelSelection" in HTML
    assert "imageModelSelection" in HTML
    assert "videoModelSelection" in HTML
    assert "quickModelSelection" in HTML
    assert "Audioは開発担当2の専用レーン" in HTML
    assert "Provider実行・課金・生成は開始しません" in HTML


def test_quick_generation_bridge_projects_snapshot_read_only():
    class QuickApplicationStub:
        def snapshot(self):
            return {"project_id": "project-1", "intent_count": 0, "intents": []}

    service = ShellApplicationService(product_version="0.21.0")
    unavailable = Task036ShellBridge(service).quick_generation_snapshot({})
    assert unavailable == {"available": False}
    bridge = Task036ShellBridge(service, quick_generation_application=QuickApplicationStub())
    assert bridge.quick_generation_snapshot({}) == {
        "available": True,
        "project_id": "project-1",
        "intent_count": 0,
        "intents": [],
    }
    with pytest.raises(ProductError) as exc:
        bridge.quick_generation_snapshot({"create": True})
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
    assert "choose_and_ingest_media" in HTML
    assert "chooseAndReport('choose_media_source','メディア')" not in HTML
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


def test_html_exposes_queue_admission_and_separate_bounded_local_execution_control():
    assert 'data-w="GENERATION_QUEUE"' in HTML
    assert 'id="generationQueueWorkspace"' in HTML
    assert "generation_queue_snapshot" in HTML
    assert "generation_queue_prepare" in HTML
    assert "generation_queue_apply" in HTML
    assert "Execution: ${entry.execution_status}" in HTML
    assert "generation_queue_dispatch" not in HTML
    assert "generation_execution_prepare" in HTML
    assert "generation_execution_apply" in HTML
    assert "generation_execution_preflight" in HTML
    assert "generation_execution_cancel" in HTML
    assert "LOCAL_FREE_AI" in HTML
    assert "RECOVERY_REQUIRED" in HTML
    assert "Queue登録だけではProviderを呼びません。" in HTML


def test_html_promotes_audio_workspace_without_provider_or_nle_shortcut():
    assert 'data-w="AUDIO_WORKSPACE"' in HTML
    assert 'id="audioWorkspace"' in HTML
    assert "audio_workspace_snapshot" in HTML
    assert "audio_workspace_prepare_placement" in HTML
    assert "audio_workspace_apply_placement" in HTML
    assert "audio_workspace_prepare_decision" in HTML
    assert "audio_workspace_apply_decision" in HTML
    assert "TASK-026/Resolve/Cubaseは開始しません" in HTML
    assert "audio_workspace_execute" not in HTML


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
    assert "audit_snapshot" in HTML
    assert "audit_prepare_human_decision" in HTML
    assert "audit_apply_human_decision" in HTML
    assert "audit_apply_recovery" in HTML
    assert "AI /" not in HTML
    assert "LOCKは別操作です" in HTML
    assert "innerHTML" not in HTML


def test_html_promotes_planning_scene_contract_with_separate_go_and_install():
    assert 'data-w="PLANNING"' in HTML
    assert 'id="planningWorkspace"' in HTML
    assert "planning_snapshot" in HTML
    assert "planning_prepare_revision" in HTML
    assert "planning_apply_revision" in HTML
    assert "planning_prepare_go" in HTML
    assert "planning_approve_go" in HTML
    assert "planning_prepare_install_plan" in HTML
    assert "planning_apply_install_plan" in HTML
    assert "企画AIは明示確認後に無償ローカルModelだけを実行します" in HTML
    assert "有償Provider・課金・Resolveは開始しません" in HTML
    assert "生成・課金・Resolve操作は開始しません" in HTML
    assert "Proposal本文を改訂" in HTML
    assert "新しいHuman GOを要求します" in HTML
    assert "innerHTML" not in HTML


def test_html_promotes_generation_safety_without_provider_or_human_accept_shortcut():
    assert 'data-w="GENERATION_SAFETY"' in HTML
    assert 'id="generationSafetyWorkspace"' in HTML
    assert "generation_safety_snapshot" in HTML
    assert "generation_safety_prepare_review" in HTML
    assert "generation_safety_apply_review" in HTML
    assert "expected_planning_snapshot_sha256:model.planning_snapshot_sha256" in HTML
    assert "expected_safety_snapshot_sha256:model.safety_snapshot_sha256" in HTML
    assert "Provider・課金・Candidate生成は開始しません" in HTML
    assert "Human ACCEPT" in HTML
    assert "generation_safety_execute" not in HTML
    assert "innerHTML" not in HTML


def test_html_promotes_continuity_without_regeneration_or_direct_override_shortcut():
    assert 'data-w="CONTINUITY"' in HTML
    assert 'id="continuityWorkspace"' in HTML
    assert "continuity_snapshot" in HTML
    assert "continuity_prepare_edge" in HTML
    assert "continuity_apply_edge" in HTML
    assert "continuity_inspect" in HTML
    assert "continuity_prepare_soft_approval" in HTML
    assert "continuity_apply_soft_approval" in HTML
    assert "continuity_propagate_stale" in HTML
    assert "continuity_apply_recovery" in HTML
    assert "Human override for DIRECT: NO" in HTML
    assert "continuity_regenerate" not in HTML
    assert "continuity_direct_override" not in HTML
    assert "innerHTML" not in HTML


def test_html_promotes_prompt_evidence_without_provider_or_candidate_creation_shortcut():
    assert 'data-w="PROMPT_EVIDENCE"' in HTML
    assert 'id="promptEvidenceWorkspace"' in HTML
    assert "prompt_evidence_snapshot" in HTML
    assert "prompt_evidence_prepare_prompt" in HTML
    assert "prompt_evidence_apply_prompt" in HTML
    assert "prompt_evidence_prepare_attempt" in HTML
    assert "prompt_evidence_apply_attempt" in HTML
    assert "prompt_evidence_prepare_regeneration" in HTML
    assert "prompt_evidence_apply_regeneration" in HTML
    assert "prompt_evidence_apply_recovery" in HTML
    assert "Provider実行・課金・Candidate作成・自動再生成・Human判断は行いません" in HTML
    assert "prompt_evidence_execute" not in HTML
    assert "innerHTML" not in HTML


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


def test_audit_bridge_routes_only_exact_human_confirmation_and_recovery_contracts():
    class AuditApplicationStub:
        def __init__(self):
            self.prepared = None
            self.applied = None
            self.recovered = None

        def snapshot(self):
            return {"project_id": "project-1", "workspace": {"candidates": []}, "recovery": {"required": False}}

        def prepare_human_decision(self, **values):
            self.prepared = values
            return {"confirmation_id": "audit-confirm-1", **values}

        def apply_human_decision(self, **values):
            self.applied = values
            return {"decision": "saved"}

        def apply_recovery(self, *, action):
            self.recovered = action
            return {"recovered": action}

    audit = AuditApplicationStub()
    bridge = Task036ShellBridge(ShellApplicationService(product_version="0.20.1"), audit_application=audit)
    assert bridge.audit_snapshot({})["available"] is True
    prepared = bridge.audit_prepare_human_decision({
        "candidate_id": "candidate-1",
        "decision": "ACCEPT",
        "expected_production_snapshot_sha256": "sha256:" + "a" * 64,
        "expected_audit_snapshot_sha256": "sha256:" + "b" * 64,
    })
    assert audit.prepared["candidate_id"] == "candidate-1"
    bridge.audit_apply_human_decision({
        "confirmation_id": prepared["confirmation_id"],
        "actor_id": "owner",
        "notes": "reviewed",
    })
    assert audit.applied == {"confirmation_id": "audit-confirm-1", "actor_id": "owner", "notes": "reviewed"}
    assert bridge.audit_apply_recovery({"action": "COMPLETE"}) == {"recovered": "COMPLETE"}
    with pytest.raises(ProductError) as exc:
        bridge.audit_apply_human_decision({"confirmation_id": "x", "actor_id": "owner", "force": True})
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"


def test_planning_bridge_routes_exact_go_and_separate_install_contracts():
    class PlanningApplicationStub:
        def __init__(self):
            self.go = None
            self.revision = None
            self.revised = None
            self.scene_revision = None
            self.scene_revised = None
            self.scene_finalization = None
            self.scene_finalized = None
            self.approved = None
            self.install = None
            self.installed = None

        def snapshot(self, *, proposal_id=None):
            return {"selected_proposal_id": proposal_id, "proposal_ids": []}

        def prepare_go(self, **values):
            self.go = values
            return {"confirmation_id": "go", **values}

        def prepare_revision(self, **values):
            self.revision = values
            return {"confirmation_id": "revision", **values}

        def apply_revision(self, **values):
            self.revised = values
            return {"revised": True}

        def prepare_scene_revision(self, **values):
            self.scene_revision = values
            return {"confirmation_id": "scene-revision", **values}

        def apply_scene_revision(self, **values):
            self.scene_revised = values
            return {"scene_revised": True}

        def prepare_scene_finalization(self, **values):
            self.scene_finalization = values
            return {"confirmation_id": "scene-finalization", **values}

        def apply_scene_finalization(self, **values):
            self.scene_finalized = values
            return {"scene_finalized": True}

        def approve_go(self, **values):
            self.approved = values
            return {"approved": True}

        def prepare_install_plan(self, **values):
            self.install = values
            return {"confirmation_id": "install", **values}

        def apply_install_plan(self, **values):
            self.installed = values
            return {"installed": True}

    planning = PlanningApplicationStub()
    bridge = Task036ShellBridge(ShellApplicationService(product_version="0.20.1"), planning_application=planning)
    assert bridge.planning_snapshot({"proposal_id": "proposal-1"})["selected_proposal_id"] == "proposal-1"
    revision = bridge.planning_prepare_revision({
        "proposal_id": "proposal-1",
        "sections": [{"section_id": "concept", "kind": "CONCEPT", "title": "Concept", "body": "Revised"}],
        "expected_snapshot_sha256": "sha256:" + "a" * 64,
    })
    assert planning.revision["sections"][0]["body"] == "Revised"
    assert bridge.planning_apply_revision({"confirmation_id": revision["confirmation_id"]}) == {"revised": True}
    assert planning.revised == {"confirmation_id": "revision"}
    scene_revision = bridge.planning_prepare_scene_revision({
        "proposal_id": "proposal-1",
        "scenes": [{
            "scene_id": "SC01", "start_frame": 0, "end_frame": 30,
            "narrative_role": "Opening", "source_strategy": "REAL_CAPTURE",
            "generation_risk": "A_LOW_TEXT", "camera_motion": "STATIC",
            "post_composite_text": False, "final_hold_frames": 0,
        }],
        "expected_snapshot_sha256": "sha256:" + "a" * 64,
    })
    assert planning.scene_revision["scenes"][0]["scene_id"] == "SC01"
    assert bridge.planning_apply_scene_revision(
        {"confirmation_id": scene_revision["confirmation_id"]}
    ) == {"scene_revised": True}
    assert planning.scene_revised == {"confirmation_id": "scene-revision"}
    scene_finalization = bridge.planning_prepare_scene_finalization({
        "proposal_id": "proposal-1",
        "finalized_by": "owner",
        "expected_proposal_snapshot_sha256": "sha256:" + "a" * 64,
        "expected_finalization_snapshot_sha256": "sha256:" + "b" * 64,
    })
    assert planning.scene_finalization["finalized_by"] == "owner"
    assert bridge.planning_apply_scene_finalization(
        {"confirmation_id": scene_finalization["confirmation_id"]}
    ) == {"scene_finalized": True}
    assert planning.scene_finalized == {"confirmation_id": "scene-finalization"}
    prepared = bridge.planning_prepare_go({
        "proposal_id": "proposal-1", "proposal_revision": 1, "reference_bindings": [],
        "cost_ceiling": "10", "rights_warnings_acknowledged": False,
        "expected_snapshot_sha256": "sha256:" + "a" * 64,
    })
    assert planning.go["proposal_revision"] == 1
    bridge.planning_approve_go({"confirmation_id": prepared["confirmation_id"], "approved_by": "owner"})
    assert planning.approved == {"confirmation_id": "go", "approved_by": "owner"}
    install = bridge.planning_prepare_install_plan({
        "plan_id": "plan-1",
        "expected_proposal_snapshot_sha256": "sha256:" + "a" * 64,
        "expected_production_snapshot_sha256": "sha256:" + "b" * 64,
    })
    bridge.planning_apply_install_plan({"confirmation_id": install["confirmation_id"]})
    assert planning.installed == {"confirmation_id": "install"}
    with pytest.raises(ProductError) as exc:
        bridge.planning_prepare_go({"proposal_id": "x", "proposal_revision": True, "reference_bindings": [], "cost_ceiling": "1", "rights_warnings_acknowledged": False, "expected_snapshot_sha256": "x"})
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"
    with pytest.raises(ProductError) as exc:
        bridge.planning_prepare_revision({"proposal_id": "x", "sections": {}, "expected_snapshot_sha256": "x"})
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"
    with pytest.raises(ProductError) as exc:
        bridge.planning_prepare_scene_revision({"proposal_id": "x", "scenes": {}, "expected_snapshot_sha256": "x"})
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"
    with pytest.raises(ProductError) as exc:
        bridge.planning_prepare_scene_finalization({
            "proposal_id": "x", "finalized_by": "owner",
            "expected_proposal_snapshot_sha256": "x",
        })
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"


def test_generation_safety_bridge_routes_only_exact_two_step_review_contract():
    class GenerationSafetyStub:
        def __init__(self):
            self.prepared = None
            self.applied = None

        def snapshot(self):
            return {"project_id": "project-1", "plan_status": "APPROVED", "scenes": []}

        def prepare_feasibility(self, **values):
            self.prepared = values
            return {"confirmation_id": "safe-confirm", **values}

        def apply_feasibility(self, **values):
            self.applied = values
            return {"saved": True}

    safety = GenerationSafetyStub()
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.20.1"),
        generation_safety_application=safety,
    )
    assert bridge.generation_safety_snapshot({})["available"] is True
    prepared = bridge.generation_safety_prepare_review({
        "spec": {"scene_id": "SC01"},
        "human_reviewed_checks": {"depth_order_valid": "PASS"},
        "blocking_reasons": [],
        "expected_planning_snapshot_sha256": "sha256:" + "a" * 64,
        "expected_safety_snapshot_sha256": "sha256:" + "b" * 64,
    })
    assert safety.prepared["blocking_reasons"] == ()
    assert bridge.generation_safety_apply_review({
        "confirmation_id": prepared["confirmation_id"],
        "reviewed_by": "owner",
    }) == {"saved": True}
    assert safety.applied == {"confirmation_id": "safe-confirm", "reviewed_by": "owner"}
    with pytest.raises(ProductError) as exc:
        bridge.generation_safety_prepare_review({
            "spec": {}, "human_reviewed_checks": {}, "blocking_reasons": "NONE",
            "expected_planning_snapshot_sha256": "x", "expected_safety_snapshot_sha256": "y",
        })
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"


def test_continuity_bridge_routes_only_exact_recoverable_contracts():
    class ContinuityStub:
        def __init__(self):
            self.calls = []

        def snapshot(self):
            return {"project_id": "project-1", "workspace": {"edges": []}, "recovery": {"required": False}}

        def prepare_register_edge(self, **values):
            self.calls.append(("prepare", values))
            return {"confirmation_id": "edge-confirm", **values}

        def apply_register_edge(self, **values):
            self.calls.append(("apply", values))
            return {"saved": True}

        def inspect_locked_target(self, **values):
            self.calls.append(("inspect", values))
            return {"inspected": True}

        def prepare_soft_approval(self, **values):
            self.calls.append(("soft-prepare", values))
            return {"confirmation_id": "soft-confirm"}

        def apply_soft_approval(self, **values):
            self.calls.append(("soft-apply", values))
            return {"approved": True}

        def propagate_stale(self, **values):
            self.calls.append(("stale", values))
            return {"stale": True}

        def apply_recovery(self, **values):
            self.calls.append(("recovery", values))
            return {"recovered": True}

    app = ContinuityStub()
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.20.1"),
        continuity_application=app,
    )
    assert bridge.continuity_snapshot({})["available"] is True
    hashes = {
        "expected_production_snapshot_sha256": "sha256:" + "a" * 64,
        "expected_continuity_snapshot_sha256": "sha256:" + "b" * 64,
    }
    prepared = bridge.continuity_prepare_edge({
        "edge_id": "edge-1", "from_slot_id": "slot-end", "to_slot_id": "slot-start",
        "boundary_type": "DIRECT_CONTINUATION", "character_contract_refs": ["char-1"],
        "space_contract_refs": ["space-1"], **hashes,
    })
    assert app.calls[-1][1]["character_contract_refs"] == ("char-1",)
    assert bridge.continuity_apply_edge({"confirmation_id": prepared["confirmation_id"]}) == {"saved": True}
    bridge.continuity_inspect({"edge_id": "edge-1", **hashes})
    soft = bridge.continuity_prepare_soft_approval({"edge_id": "edge-1", **hashes})
    bridge.continuity_apply_soft_approval({"confirmation_id": soft["confirmation_id"], "approved_by": "owner"})
    bridge.continuity_propagate_stale({"root_slot_id": "slot-end", **hashes})
    bridge.continuity_apply_recovery({"action": "COMPLETE"})
    assert [name for name, _ in app.calls] == ["prepare", "apply", "inspect", "soft-prepare", "soft-apply", "stale", "recovery"]
    with pytest.raises(ProductError) as exc:
        bridge.continuity_prepare_edge({
            "edge_id": True, "from_slot_id": "slot-end", "to_slot_id": "slot-start",
            "boundary_type": "DIRECT_CONTINUATION", "character_contract_refs": [],
            "space_contract_refs": [], **hashes,
        })
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"


def test_prompt_evidence_bridge_routes_exact_import_only_contracts():
    class PromptEvidenceStub:
        def __init__(self): self.calls = []
        def snapshot(self): return {"project_id": "project-1", "prompts": [], "recovery": {"required": False}}
        def prepare_prompt(self, **values): self.calls.append(("prompt-prepare", values)); return {"confirmation_id": "p"}
        def apply_prompt(self, **values): self.calls.append(("prompt-apply", values)); return {"saved": True}
        def prepare_attempt(self, **values): self.calls.append(("attempt-prepare", values)); return {"confirmation_id": "a"}
        def apply_attempt(self, **values): self.calls.append(("attempt-apply", values)); return {"saved": True}
        def prepare_regeneration(self, **values): self.calls.append(("regen-prepare", values)); return {"confirmation_id": "r"}
        def apply_regeneration(self, **values): self.calls.append(("regen-apply", values)); return {"saved": True}
        def apply_recovery(self, **values): self.calls.append(("recovery", values)); return {"saved": True}

    app = PromptEvidenceStub()
    bridge = Task036ShellBridge(ShellApplicationService(product_version="0.20.1"), prompt_evidence_application=app)
    assert bridge.prompt_evidence_snapshot({})["available"] is True
    hashes = {"expected_prompt_snapshot_sha256": "sha256:" + "1" * 64, "expected_production_snapshot_sha256": "sha256:" + "2" * 64}
    prompt = bridge.prompt_evidence_prepare_prompt({
        "prompt_id": "prompt-1", "prompt_version": 1, "purpose": "frame", "scene_id": "scene-1",
        "slot_id": "slot-1", "body_ref": "project-private://p", "body_sha256": "sha256:" + "3" * 64,
        "provider_profile_id": "profile", "provider_profile_version": "v1", "input_asset_hashes": [],
        "keep_conditions": ["keep"], **hashes,
    })
    bridge.prompt_evidence_apply_prompt({"confirmation_id": prompt["confirmation_id"]})
    attempt = bridge.prompt_evidence_prepare_attempt({
        "generation_job_id": "job-1", "slot_id": "slot-1", "prompt_id": "prompt-1", "prompt_version": 1,
        "provider_id": "provider", "model_id": "model", "strategy_level": 0, "result": "FAIL",
        "failure_codes": ["DEPTH"], "output_candidate_id": None, "parent_attempt_id": None,
        "cost": None, "latency_ms": 10, **hashes,
    })
    bridge.prompt_evidence_apply_attempt({"confirmation_id": attempt["confirmation_id"]})
    regen = bridge.prompt_evidence_prepare_regeneration({
        "candidate_id": "candidate-1", "new_body_sha256": "sha256:" + "4" * 64,
        "new_body_ref": "project-private://p/v2", "provider_profile_id": None,
        "provider_profile_version": None, "input_asset_hashes": None, "keep_conditions": None,
        "repeated_failure_threshold": 2, "expected_audit_snapshot_sha256": "sha256:" + "5" * 64, **hashes,
    })
    bridge.prompt_evidence_apply_regeneration({"confirmation_id": regen["confirmation_id"]})
    bridge.prompt_evidence_apply_recovery({"action": "COMPLETE"})
    assert [name for name, _ in app.calls] == ["prompt-prepare", "prompt-apply", "attempt-prepare", "attempt-apply", "regen-prepare", "regen-apply", "recovery"]
    with pytest.raises(ProductError) as exc:
        bridge.prompt_evidence_prepare_attempt({
            "generation_job_id": "job", "slot_id": "slot", "prompt_id": "prompt", "prompt_version": True,
            "provider_id": "p", "model_id": "m", "strategy_level": 0, "result": "FAIL", "failure_codes": [],
            "output_candidate_id": None, "parent_attempt_id": None, "cost": None, "latency_ms": None, **hashes,
        })
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
        cut_manifest=source_bridge._review.state.manifest,
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


def test_generation_execution_bridge_keeps_queue_and_external_mutation_authority_separate():
    class QueueStub:
        def snapshot(self):
            return {"project_id": "project-1", "queue_snapshot_sha256": "sha256:" + "1" * 64, "entries": []}

    class ExecutionStub:
        def __init__(self): self.calls = []
        def snapshot(self):
            return {"project_id": "project-1", "execution_snapshot_sha256": "sha256:" + "2" * 64, "recovery": {"required": False}}
        def runtime_preflight(self, *, queue_entry_id=None):
            self.calls.append(("preflight", {"queue_entry_id": queue_entry_id})); return {
                "result": "SAFE_RUNTIME_PREFLIGHT_PASS_EXECUTION_PARKED",
                "dispatch_performed": False,
                "execution_authorized": False,
            }
        def prepare_execution(self, **values):
            self.calls.append(("prepare", values)); return {"confirmation_id": "confirm-local"}
        def apply_execution(self, **values):
            self.calls.append(("apply", values)); return {"events": [{"state": "COMPLETED"}]}
        def cancel_execution(self, **values):
            self.calls.append(("cancel", values)); return {"cancelled": True}
        def recover_execution(self, **values):
            self.calls.append(("recover", values)); return {"events": [{"state": "COMPLETED"}]}

    execution = ExecutionStub()
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.20.1"),
        generation_queue_application=QueueStub(),
        generation_execution_application=execution,
    )
    combined = bridge.generation_queue_snapshot({})
    assert combined["execution_control"]["available"] is True
    readiness = bridge.generation_execution_preflight({})
    assert readiness["result"] == "SAFE_RUNTIME_PREFLIGHT_PASS_EXECUTION_PARKED"
    assert readiness["dispatch_performed"] is False
    scoped = bridge.generation_execution_preflight({"queue_entry_id": "QUEUE-1"})
    assert scoped["result"] == "SAFE_RUNTIME_PREFLIGHT_PASS_EXECUTION_PARKED"
    prepared = bridge.generation_execution_prepare({
        "queue_entry_id": "QUEUE-1",
        "expected_queue_snapshot_sha256": "sha256:" + "1" * 64,
        "expected_execution_snapshot_sha256": "sha256:" + "2" * 64,
    })
    assert prepared["confirmation_id"] == "confirm-local"
    extended_prepared = bridge.generation_execution_prepare({
        "queue_entry_id": "QUEUE-1",
        "expected_queue_snapshot_sha256": "sha256:" + "1" * 64,
        "expected_execution_snapshot_sha256": "sha256:" + "2" * 64,
        "expected_project_manifest_sha256": "sha256:" + "3" * 64,
    })
    assert extended_prepared["confirmation_id"] == "confirm-local"
    result = bridge.generation_execution_apply({"confirmation_id": "confirm-local"})
    assert result["events"][0]["state"] == "COMPLETED"
    cancelled = bridge.generation_execution_cancel({"confirmation_id": "cancel-local"})
    assert cancelled["cancelled"] is True
    recovered = bridge.generation_execution_recover({
        "execution_id": "EXEC-1",
        "expected_execution_snapshot_sha256": "sha256:" + "2" * 64,
    })
    assert recovered["events"][0]["state"] == "COMPLETED"
    assert [name for name, _ in execution.calls] == ["preflight", "preflight", "prepare", "prepare", "apply", "cancel", "recover"]
    assert execution.calls[0][1]["queue_entry_id"] is None
    assert execution.calls[1][1]["queue_entry_id"] == "QUEUE-1"
    with pytest.raises(ProductError) as exc:
        bridge.generation_execution_prepare({
            "queue_entry_id": "QUEUE-1", "expected_queue_snapshot_sha256": "sha256:" + "1" * 64,
        })
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"
    for invalid in ({"queue_entry_id": ""}, {"queue_entry_id": 1}, {"queue_entry_id": True}, {"queue_entry_id": None}, {"extra": "QUEUE-1"}):
        with pytest.raises(ProductError) as invalid_exc:
            bridge.generation_execution_preflight(invalid)
        assert invalid_exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"
    for invalid in ({}, {"confirmation_id": ""}, {"confirmation_id": 1}, {"confirmation_id": None}):
        with pytest.raises(ProductError) as invalid_exc:
            bridge.generation_execution_cancel(invalid)
        assert invalid_exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"
    for invalid in (
        {},
        {"execution_id": "", "expected_execution_snapshot_sha256": "sha256:" + "2" * 64},
        {"execution_id": 1, "expected_execution_snapshot_sha256": "sha256:" + "2" * 64},
        {"execution_id": "EXEC-1", "expected_execution_snapshot_sha256": None},
    ):
        with pytest.raises(ProductError) as invalid_exc:
            bridge.generation_execution_recover(invalid)
        assert invalid_exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"


def test_generation_execution_bridge_enters_runtime_lease_before_touching_application():
    class ExecutionStub:
        calls = 0
        def snapshot(self):
            self.calls += 1
            return {"project_id": "project-1", "execution_snapshot_sha256": "sha256:" + "2" * 64}

    lease_active = False

    @contextmanager
    def guard():
        if not lease_active:
            raise ProductError("ERR_TASK036_RUNTIME_LEASE_REQUIRED", "closed", ProductErrorCategory.AUTHORIZATION)
        yield

    execution = ExecutionStub()
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.20.1"),
        generation_execution_application=execution,
        nle_runtime_guard=guard,
    )
    with pytest.raises(ProductError) as closed:
        bridge.generation_execution_snapshot({})
    assert closed.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    assert execution.calls == 0
    lease_active = True
    assert bridge.generation_execution_snapshot({})["available"] is True
    assert execution.calls == 1


def test_generation_output_adoption_bridge_is_allowlisted_and_separate_from_provider_execution():
    class QueueStub:
        def snapshot(self):
            return {"project_id": "project-1", "queue_snapshot_sha256": "sha256:" + "1" * 64, "entries": []}

    class AdoptionStub:
        def __init__(self):
            self.calls = []

        def snapshot(self):
            return {
                "project_id": "project-1",
                "adoption_snapshot_sha256": "sha256:" + "2" * 64,
                "eligible_completed_outputs": [],
                "recovery": {"required": False, "active": []},
                "provider_execution_started": False,
                "publication_authorized": False,
            }

        def prepare_adoption(self, **values):
            self.calls.append(("prepare", values))
            return {"confirmation_id": "adopt-confirm", "action_label": "検証して監査候補へ登録"}

        def apply_adoption(self, **values):
            self.calls.append(("apply", values))
            return {"records": [{"state": "READY_FOR_AUDIT"}]}

        def apply_recovery(self, **values):
            self.calls.append(("recover", values))
            return {"recovery": {"required": False}}

    adoption = AdoptionStub()
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        generation_queue_application=QueueStub(),
        generation_output_adoption_application=adoption,
    )
    combined = bridge.generation_queue_snapshot({})
    assert combined["output_adoption_control"]["available"] is True
    values = {
        "execution_id": "execution-1",
        "expected_execution_snapshot_sha256": "sha256:" + "3" * 64,
        "expected_queue_snapshot_sha256": "sha256:" + "1" * 64,
        "expected_production_snapshot_sha256": "sha256:" + "4" * 64,
        "expected_prompt_snapshot_sha256": "sha256:" + "5" * 64,
        "expected_adoption_snapshot_sha256": "sha256:" + "2" * 64,
    }
    prepared = bridge.generation_output_adoption_prepare(values)
    assert prepared["action_label"] == "検証して監査候補へ登録"
    extended = {**values, "expected_project_manifest_sha256": "sha256:" + "6" * 64}
    assert bridge.generation_output_adoption_prepare(extended)["confirmation_id"] == "adopt-confirm"
    assert bridge.generation_output_adoption_apply({"confirmation_id": "adopt-confirm"})["records"][0]["state"] == "READY_FOR_AUDIT"
    assert bridge.generation_output_adoption_recover({"adoption_id": "adoption-1"})["recovery"]["required"] is False
    assert [name for name, _ in adoption.calls] == ["prepare", "prepare", "apply", "recover"]
    with pytest.raises(ProductError) as exc:
        bridge.generation_output_adoption_prepare({"execution_id": "execution-1"})
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"


def test_audio_workspace_bridge_is_allowlisted_and_keeps_execution_separate():
    class AudioStub:
        def __init__(self):
            self.calls = []

        def snapshot(self):
            return {"project_id": "project-1", "task026_compile_started": False, "resolve_mutation_started": False}

        def prepare_placement(self, **values):
            self.calls.append(("prepare-placement", values))
            return {"confirmation_id": "placement-confirm"}

        def apply_placement(self, **values):
            self.calls.append(("apply-placement", values))
            return {"workspace": {"placements": []}}

        def prepare_placement_decision(self, **values):
            self.calls.append(("prepare-decision", values))
            return {"confirmation_id": "decision-confirm"}

        def apply_placement_decision(self, **values):
            self.calls.append(("apply-decision", values))
            return {"workspace": {"placements": [{"decision": "ACCEPT"}]}}

    audio = AudioStub()
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.20.1"),
        audio_workspace_application=audio,
    )
    assert bridge.audio_workspace_snapshot({})["task026_compile_started"] is False
    prepared = bridge.audio_workspace_prepare_placement({
        "review_id": "review-1",
        "candidate_id": "candidate-1",
        "timeline_start_frame": 0,
        "duration_frames": 120,
        "track_role": "BGM",
        "gain_db": -6.0,
        "expected_production_snapshot_sha256": "sha256:" + "1" * 64,
        "expected_audio_snapshot_sha256": "sha256:" + "2" * 64,
    })
    assert prepared["confirmation_id"] == "placement-confirm"
    bridge.audio_workspace_apply_placement({"confirmation_id": "placement-confirm"})
    decision = bridge.audio_workspace_prepare_decision({
        "review_id": "review-1",
        "decision": "ACCEPT",
        "expected_production_snapshot_sha256": "sha256:" + "1" * 64,
        "expected_audio_snapshot_sha256": "sha256:" + "2" * 64,
    })
    assert decision["confirmation_id"] == "decision-confirm"
    result = bridge.audio_workspace_apply_decision({"confirmation_id": "decision-confirm"})
    assert result["workspace"]["placements"][0]["decision"] == "ACCEPT"
    assert [name for name, _ in audio.calls] == [
        "prepare-placement", "apply-placement", "prepare-decision", "apply-decision",
    ]
    with pytest.raises(ProductError) as exc:
        bridge.audio_workspace_prepare_placement({"review_id": "review-1"})
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"


def test_task026_audio_placement_bridge_is_narrow_and_non_executing():
    class PlacementStub:
        def __init__(self):
            self.calls = []

        def snapshot(self):
            return {"project_id": "project-1", "records": [], "resolve_mutation_started": False}

        def prepare_compilation(self, **values):
            self.calls.append(("prepare", values))
            return {"confirmation_id": "compile-confirm", "estimated_cost": 0}

        def apply_compilation(self, **values):
            self.calls.append(("apply", values))
            return {"apply_result": {"external_execution_started": False}}

    placement = PlacementStub()
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        audio_placement_application=placement,
    )
    assert bridge.audio_placement_snapshot({})["resolve_mutation_started"] is False
    prepared = bridge.audio_placement_prepare({
        "review_id": "review-1",
        "track_index": 2,
        "bed_mode": "FULL",
        "expected_project_manifest_sha256": "sha256:" + "1" * 64,
        "expected_production_snapshot_sha256": "sha256:" + "2" * 64,
        "expected_audio_snapshot_sha256": "sha256:" + "3" * 64,
        "expected_timeline_snapshot_sha256": "sha256:" + "4" * 64,
        "expected_history_snapshot_sha256": "sha256:" + "5" * 64,
    })
    assert prepared == {"confirmation_id": "compile-confirm", "estimated_cost": 0}
    applied = bridge.audio_placement_apply({"confirmation_id": "compile-confirm"})
    assert applied["apply_result"]["external_execution_started"] is False
    assert [name for name, _ in placement.calls] == ["prepare", "apply"]
    with pytest.raises(ProductError) as exc:
        bridge.audio_placement_prepare({"review_id": "review-1"})
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"


def test_html_exposes_task026_plan_without_external_execution_claim():
    assert "Placement Planを作成" in HTML
    assert "audio_placement_prepare" in HTML
    assert "audio_placement_apply" in HTML
    assert "Provider・課金・音声生成・Resolve/Cubaseは開始しません" in HTML


def test_final_review_readiness_bridge_fails_closed_when_sources_are_missing():
    bridge = Task036ShellBridge(ShellApplicationService(product_version="0.21.0"))
    result = bridge.final_review_readiness_snapshot({})
    assert result["available"] is False
    assert result["state"] == "SOURCE_UNAVAILABLE"
    assert result["missing_sources"] == ["audit", "export", "production", "timeline", "visual"]
    assert result["delegated_audio_owner"] == "DEVELOPER2"
    assert result["final_approval_created"] is False
    assert result["export_job_created"] is False
    assert result["render_or_publish_started"] is False
    assert result["human_decision_authorized"] is False


def test_final_review_readiness_bridge_keeps_missing_external_gates_explicit(monkeypatch):
    sha = lambda char: "sha256:" + char * 64
    bridge = Task036ShellBridge(ShellApplicationService(product_version="0.21.0"))
    monkeypatch.setattr(bridge, "production_snapshot", lambda args=None: {
        "available": True, "project_id": "project-1", "snapshot_sha256": sha("1"),
        "slots": [{"slot_id": "slot-1", "required": True, "status": "LOCKED", "stale_state": "CURRENT"}],
    })
    monkeypatch.setattr(bridge, "audit_snapshot", lambda args=None: {
        "available": True, "project_id": "project-1",
        "production_snapshot_sha256": sha("1"), "audit_snapshot_sha256": sha("2"),
        "recovery": {"required": False}, "workspace": {"candidates": []},
    })
    monkeypatch.setattr(bridge, "visual_generation_handoff_snapshot", lambda args=None: {
        "available": True, "project_id": "project-1",
        "source_snapshots": {"production": sha("1")}, "projection_sha256": sha("3"),
        "all_required_visual_slots_adopted": True, "required_blocker_count": 0,
    })
    monkeypatch.setattr(bridge, "interactive_timeline_snapshot", lambda args=None: {
        "available": True, "projected_timeline_sha256": sha("4"),
        "project_manifest_sha256": sha("5"),
    })
    monkeypatch.setattr(bridge, "export_queue_snapshot", lambda args=None: {"available": True, "rows": []})
    result = bridge.final_review_readiness_snapshot({})
    assert result["available"] is True
    assert result["state"] == "BLOCKED_EXTERNAL_GATES"
    assert [gate["state"] for gate in result["external_gates"]] == ["MISSING"] * 5
    assert result["final_approval_created"] is False
