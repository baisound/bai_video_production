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


def test_html_exposes_queue_admission_and_separate_bounded_local_execution_control():
    assert 'data-w="GENERATION_QUEUE"' in HTML
    assert 'id="generationQueueWorkspace"' in HTML
    assert "generation_queue_snapshot" in HTML
    assert "generation_queue_prepare" in HTML
    assert "generation_queue_apply" in HTML
    assert "EXECUTION_NOT_AUTHORIZED" in HTML
    assert "generation_queue_dispatch" not in HTML
    assert "generation_execution_prepare" in HTML
    assert "generation_execution_apply" in HTML
    assert "LOCAL_FREE_AI" in HTML
    assert "RECOVERY_REQUIRED" in HTML
    assert "Provider呼出し・課金・Budget予約・Candidate作成" in HTML


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
    assert "planning_prepare_go" in HTML
    assert "planning_approve_go" in HTML
    assert "planning_prepare_install_plan" in HTML
    assert "planning_apply_install_plan" in HTML
    assert "Provider/課金/Resolveは開始しません" in HTML
    assert "生成・課金・Resolve操作は開始しません" in HTML
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
            self.approved = None
            self.install = None
            self.installed = None

        def snapshot(self, *, proposal_id=None):
            return {"selected_proposal_id": proposal_id, "proposal_ids": []}

        def prepare_go(self, **values):
            self.go = values
            return {"confirmation_id": "go", **values}

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


def test_generation_execution_bridge_keeps_queue_and_external_mutation_authority_separate():
    class QueueStub:
        def snapshot(self):
            return {"project_id": "project-1", "queue_snapshot_sha256": "sha256:" + "1" * 64, "entries": []}

    class ExecutionStub:
        def __init__(self): self.calls = []
        def snapshot(self):
            return {"project_id": "project-1", "execution_snapshot_sha256": "sha256:" + "2" * 64, "recovery": {"required": False}}
        def prepare_execution(self, **values):
            self.calls.append(("prepare", values)); return {"confirmation_id": "confirm-local"}
        def apply_execution(self, **values):
            self.calls.append(("apply", values)); return {"events": [{"state": "COMPLETED"}]}

    execution = ExecutionStub()
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.20.1"),
        generation_queue_application=QueueStub(),
        generation_execution_application=execution,
    )
    combined = bridge.generation_queue_snapshot({})
    assert combined["execution_control"]["available"] is True
    prepared = bridge.generation_execution_prepare({
        "queue_entry_id": "QUEUE-1",
        "expected_queue_snapshot_sha256": "sha256:" + "1" * 64,
        "expected_execution_snapshot_sha256": "sha256:" + "2" * 64,
    })
    assert prepared["confirmation_id"] == "confirm-local"
    result = bridge.generation_execution_apply({"confirmation_id": "confirm-local"})
    assert result["events"][0]["state"] == "COMPLETED"
    assert [name for name, _ in execution.calls] == ["prepare", "apply"]
    with pytest.raises(ProductError) as exc:
        bridge.generation_execution_prepare({
            "queue_entry_id": "QUEUE-1", "expected_queue_snapshot_sha256": "sha256:" + "1" * 64,
        })
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"
