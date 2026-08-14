from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import json
from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.audit_application import Task038AuditApplication
from ai_video_production.generation_safety_application import Task013GenerationSafetyApplication
from ai_video_production.planning_application import Task027PlanningApplication
from ai_video_production.production_blueprint import (
    AssetSourceStrategy,
    BlueprintScene,
    CameraMotion,
    GenerationRisk,
    ProductionBlueprint,
)
from ai_video_production.production_proposal import (
    CreationIntent,
    ProductionProposalRegistry,
    ProductionProposalRevision,
    ProposalSection,
    ProviderPolicyBinding,
)
from ai_video_production.production_proposal_store import ProductionProposalSnapshotStore
from ai_video_production.timebase import FrameRate
from ai_video_production.visual_compliance import (
    CoordinateConvention,
    VisualCheckState,
    VisualComplianceContract,
    VisualComplianceGate,
    VisualContractCheck,
    VisualScoreSet,
)


SHA = "sha256:" + "a" * 64
POLICY_SHA = "sha256:" + "c" * 64


def seed_approved_plan(root: Path) -> Task027PlanningApplication:
    registry = ProductionProposalRegistry()
    intent = CreationIntent(
        "INTENT-SAFE", 1, "Safe generation", "Viewer", "YouTube", "16:9", Decimal("2"),
        "Calm", "Show a safe shot", "ja-JP", budget_ceiling=Decimal("5"),
    )
    registry.add_intent(intent)
    scene = BlueprintScene(
        "SC01", 0, 60, "Opening", AssetSourceStrategy.AI_GENERATED,
        GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, (),
    )
    blueprint = ProductionBlueprint("BP-SAFE013", "Safe", FrameRate(30), 60, (), (scene,))
    registry.add_proposal(ProductionProposalRevision(
        "PROPOSAL-SAFE", 1, intent.to_dict()["intent_sha256"], blueprint,
        (ProposalSection("concept", "CONCEPT", "Concept", "Safe opening"),),
        ProviderPolicyBinding("policy", "1", POLICY_SHA), Decimal("0"), Decimal("0"), "USD",
    ))
    ProductionProposalSnapshotStore.save(root / "production-proposal.json", registry)
    planning = Task027PlanningApplication(project_root=root, project_id="project-1", token_factory=lambda: "go")
    state = planning.snapshot()
    prepared = planning.prepare_go(
        proposal_id="PROPOSAL-SAFE", proposal_revision=1, reference_bindings=(), cost_ceiling="0",
        rights_warnings_acknowledged=False, expected_snapshot_sha256=state["snapshot_sha256"],
    )
    planning.approve_go(confirmation_id=prepared["confirmation_id"], approved_by="owner")
    return planning


def spec(**overrides):
    value = {
        "scene_id": "SC01",
        "continuity_type": "CUT",
        "character_required": True,
        "character_identity_profile_id": "CHAR-1",
        "character_reference_asset_ids": ["ASSET-CHAR"],
        "room_master_asset_id": "ASSET-ROOM",
        "room_shot_reference_asset_id": "ASSET-SHOT",
        "style_reference_asset_id": None,
        "required_visible": ["FACE", "MONITOR"],
        "subject_orientation": "THREE_QUARTER",
        "camera_semantic": "DESK_FRONT",
        "start_frame_source": "NEW",
        "previous_end_asset_id": None,
        "previous_end_sha256": None,
        "start_asset_id": None,
        "start_asset_sha256": None,
        "prohibited_changes": ["ADD_DESK", "MOVE_FURNITURE"],
    }
    value.update(overrides)
    return value


def checks(value: str = "PASS"):
    return {name: value for name in (
        "subject_position_exists", "orientation_camera_compatible", "required_visible_coexists",
        "prohibited_change_not_required", "shot_reference_matches_final_camera", "task_axis_valid",
        "depth_order_valid", "occlusion_valid", "furniture_integrity_valid",
        "room_anchor_integrity_valid", "production_gear_absent", "character_identity_valid",
    )}


def prepare(app: Task013GenerationSafetyApplication, **overrides):
    state = app.snapshot()
    values = dict(
        spec=spec(), human_reviewed_checks=checks(), blocking_reasons=(),
        expected_planning_snapshot_sha256=state["planning_snapshot_sha256"],
        expected_safety_snapshot_sha256=state["safety_snapshot_sha256"],
    )
    values.update(overrides)
    return app.prepare_feasibility(**values)


def test_snapshot_requires_current_human_approved_plan(tmp_path: Path) -> None:
    app = Task013GenerationSafetyApplication(project_root=tmp_path, project_id="project-1")
    state = app.snapshot()
    assert state["plan_status"] == "GO_REQUIRED"
    assert state["all_current_feasibility_pass"] is False
    assert state["provider_execution_started"] is False
    assert state["generation_admission_complete"] is False


def test_exact_human_review_persists_and_survives_restart_without_execution(tmp_path: Path) -> None:
    planning = seed_approved_plan(tmp_path)
    app = Task013GenerationSafetyApplication(
        project_root=tmp_path, project_id="project-1", planning_application=planning,
        token_factory=lambda: "feasibility-confirm",
    )
    prepared = prepare(app)
    assert prepared["assessment"]["status"] == "PASS"
    result = app.apply_feasibility(confirmation_id="feasibility-confirm", reviewed_by="owner")
    assert result["application"]["all_current_feasibility_pass"] is True
    reopened = Task013GenerationSafetyApplication(project_root=tmp_path, project_id="project-1").snapshot()
    assert reopened["scenes"][0]["feasibility_status"] == "PASS"
    assert reopened["provider_execution_started"] is False
    assert reopened["candidate_created"] is False
    with pytest.raises(ProductError) as exc:
        app.apply_feasibility(confirmation_id="feasibility-confirm", reviewed_by="owner")
    assert exc.value.code == "ERR_GENERATION_SAFETY_CONFIRMATION_INVALID"


def test_partial_or_unverified_human_review_fails_closed(tmp_path: Path) -> None:
    planning = seed_approved_plan(tmp_path)
    app = Task013GenerationSafetyApplication(project_root=tmp_path, project_id="project-1", planning_application=planning)
    partial = checks(); partial.pop("depth_order_valid")
    with pytest.raises(ProductError) as exc:
        prepare(app, human_reviewed_checks=partial)
    assert exc.value.code == "ERR_GENERATION_SAFETY_CHECK_SET"
    unverified = checks(); unverified["depth_order_valid"] = "UNVERIFIED"
    with pytest.raises(ProductError) as exc:
        prepare(app, human_reviewed_checks=unverified)
    assert exc.value.code == "ERR_GENERATION_SAFETY_CHECK_UNVERIFIED"


def test_deterministic_continuity_failure_cannot_be_overridden(tmp_path: Path) -> None:
    planning = seed_approved_plan(tmp_path)
    app = Task013GenerationSafetyApplication(project_root=tmp_path, project_id="project-1", planning_application=planning)
    broken = spec(
        continuity_type="DIRECT_CONTINUATION", start_frame_source="NEW",
        previous_end_asset_id="ASSET-END", previous_end_sha256=SHA,
        start_asset_id="ASSET-NEW", start_asset_sha256="sha256:" + "b" * 64,
    )
    prepared = prepare(app, spec=broken)
    assert prepared["assessment"]["status"] == "FAIL"
    assert prepared["assessment"]["checks"]["continuity_contract_valid"] == "FAIL"


def test_planning_change_after_prepare_consumes_confirmation(tmp_path: Path) -> None:
    planning = seed_approved_plan(tmp_path)
    app = Task013GenerationSafetyApplication(
        project_root=tmp_path, project_id="project-1", planning_application=planning,
        token_factory=lambda: "stale-confirm",
    )
    prepare(app)
    registry = ProductionProposalSnapshotStore.load(tmp_path / "production-proposal.json")
    previous = ProductionProposalSnapshotStore.snapshot(registry)["snapshot_sha256"]
    latest = registry.latest_proposal("PROPOSAL-SAFE")
    registry.add_proposal(ProductionProposalRevision(
        latest.proposal_id, 2, latest.intent_sha256, latest.blueprint,
        (ProposalSection("concept", "CONCEPT", "Concept", "Changed"),), latest.provider_policy,
        latest.estimated_cost_min, latest.estimated_cost_max, latest.currency,
        parent_proposal_sha256=latest.to_dict()["proposal_sha256"],
    ))
    ProductionProposalSnapshotStore.save(
        tmp_path / "production-proposal.json", registry,
        expected_previous_snapshot_sha256=previous,
    )
    with pytest.raises(ProductError) as exc:
        app.apply_feasibility(confirmation_id="stale-confirm", reviewed_by="owner")
    assert exc.value.code == "ERR_GENERATION_SAFETY_SNAPSHOT_CONFLICT"
    with pytest.raises(ProductError) as exc:
        app.apply_feasibility(confirmation_id="stale-confirm", reviewed_by="owner")
    assert exc.value.code == "ERR_GENERATION_SAFETY_CONFIRMATION_INVALID"


def test_concurrent_publication_allows_exactly_one_writer(tmp_path: Path) -> None:
    seed_approved_plan(tmp_path)
    first = Task013GenerationSafetyApplication(project_root=tmp_path, project_id="project-1", token_factory=lambda: "first")
    second = Task013GenerationSafetyApplication(project_root=tmp_path, project_id="project-1", token_factory=lambda: "second")
    prepare(first); prepare(second)

    def publish(service, token):
        try:
            service.apply_feasibility(confirmation_id=token, reviewed_by="owner")
            return "PASS"
        except ProductError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda item: publish(*item), ((first, "first"), (second, "second"))))
    assert results.count("PASS") == 1
    assert results.count("ERR_GENERATION_SAFETY_SNAPSHOT_CONFLICT") == 1


def test_snapshot_tamper_and_cross_project_binding_fail_closed(tmp_path: Path) -> None:
    planning = seed_approved_plan(tmp_path)
    with pytest.raises(ProductError) as exc:
        Task013GenerationSafetyApplication(project_root=tmp_path, project_id="other", planning_application=planning)
    assert exc.value.code == "ERR_GENERATION_SAFETY_PLANNING_SCOPE_MISMATCH"
    app = Task013GenerationSafetyApplication(project_root=tmp_path, project_id="project-1", planning_application=planning, token_factory=lambda: "write")
    prepare(app); app.apply_feasibility(confirmation_id="write", reviewed_by="owner")
    document = json.loads(app.snapshot_path.read_text(encoding="utf-8"))
    document["records"][0]["reviewed_by"] = "attacker"
    app.snapshot_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        app.snapshot()
    assert exc.value.code == "ERR_GENERATION_SAFETY_SNAPSHOT_CHECKSUM"


def test_visual_compliance_persists_as_audit_without_human_decision(tmp_path: Path) -> None:
    planning = seed_approved_plan(tmp_path)
    planning_state = planning.snapshot()
    plan_id = planning_state["workspace"]["approved_plan"]["plan_id"]
    install = planning.prepare_install_plan(
        plan_id=plan_id,
        expected_proposal_snapshot_sha256=planning_state["snapshot_sha256"],
        expected_production_snapshot_sha256=planning_state["installation"]["production"]["snapshot_sha256"],
    )
    planning.apply_install_plan(confirmation_id=install["confirmation_id"])
    production = planning.production_control
    production_state = production.snapshot()
    slot = next(row for row in production_state["slots"] if row["scene_id"] == "SC01" and row["slot_kind"] == "VIDEO")
    production.register_candidate(
        candidate_id="candidate-visual", slot_id=slot["slot_id"], asset_id="asset-visual",
        asset_sha256=SHA, expected_snapshot_sha256=production_state["snapshot_sha256"],
    )
    production_state = production.snapshot()
    production.mark_ready_for_audit(
        candidate_id="candidate-visual",
        expected_snapshot_sha256=production_state["snapshot_sha256"],
    )
    audit = Task038AuditApplication(project_root=tmp_path, project_id="project-1")
    app = Task013GenerationSafetyApplication(
        project_root=tmp_path, project_id="project-1", planning_application=planning,
        audit_application=audit,
    )
    contract = VisualComplianceContract(
        "contract-sc01", 1, "SC01",
        (VisualContractCheck("depth.order", "Monitor remains in foreground", True),),
        CoordinateConvention.VIEWER,
    )
    decision = VisualComplianceGate.evaluate(
        contract, candidate_id="candidate-visual", candidate_asset_sha256=SHA,
        observed_checks={"depth.order": VisualCheckState.PASS},
        scores=VisualScoreSet(1, 0.9, 0.9, 0.8), inspector_kind="VISION_JUDGE",
    )
    audit_state = audit.snapshot()
    result = app.record_visual_compliance(
        decision, audit_id="audit-visual", auditor_id="vision-judge", auditor_version="v1",
        expected_production_snapshot_sha256=audit_state["production_snapshot_sha256"],
        expected_audit_snapshot_sha256=audit_state["audit_snapshot_sha256"],
    )
    assert result["human_candidate_decision_recorded"] is False
    assert result["automatic_candidate_accept"] is False
    reopened = audit.snapshot()
    candidate = next(row for row in reopened["workspace"]["candidates"] if row["candidate_id"] == "candidate-visual")
    assert candidate["audit_history"][0]["audit_id"] == "audit-visual"
    assert candidate["human_decision"] is None
