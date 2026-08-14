from __future__ import annotations

from decimal import Decimal

import pytest

from ai_video_production.approved_plan_orchestration import (
    ApprovedPlanGenerationAdmissionService,
    ApprovedPlanProductionControlInstaller,
)
from ai_video_production.errors import ProductError
from ai_video_production.production_blueprint import (
    AssetSourceStrategy, BlueprintScene, CameraMotion, GenerationRisk, ProductionBlueprint,
)
from ai_video_production.production_control import ProductionControlRegistry
from ai_video_production.production_proposal import (
    CreationIntent, ProductionGoApprovalService, ProductionProposalRegistry,
    ProductionProposalRevision, ProposalSection, ProviderPolicyBinding,
)
from ai_video_production.shot_feasibility import CheckState, ShotFeasibilityAssessment
from ai_video_production.timebase import FrameRate

POLICY_SHA = "sha256:" + "c" * 64


def approved():
    registry = ProductionProposalRegistry()
    intent = CreationIntent(
        "INTENT-DEMO", 1, "Intro", "Viewers", "YouTube", "16:9", Decimal("10"),
        "Calm", "Explain", "ja-JP", budget_ceiling=Decimal("20"),
    )
    registry.add_intent(intent)
    scene = BlueprintScene(
        "SC01", 0, 300, "Opening", AssetSourceStrategy.AI_GENERATED,
        GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, (),
    )
    blueprint = ProductionBlueprint("BP-DEMO-001", "Demo", FrameRate(30, 1), 300, (), (scene,))
    proposal = ProductionProposalRevision(
        "PROPOSAL-DEMO", 1, intent.to_dict()["intent_sha256"], blueprint,
        (ProposalSection("concept", "CONCEPT", "Concept", "Opening"),),
        ProviderPolicyBinding("policy", "1", POLICY_SHA), Decimal("1"), Decimal("10"), "USD",
    )
    registry.add_proposal(proposal)
    go = ProductionGoApprovalService(registry, token_factory=lambda: "go")
    go.prepare_go(
        proposal_id="PROPOSAL-DEMO", proposal_revision=1, reference_bindings=(),
        cost_ceiling="12", rights_warnings_acknowledged=False,
    )
    plan = go.approve_go(confirmation_id="go", approved_by="owner")
    return registry, blueprint, plan


def feasibility() -> ShotFeasibilityAssessment:
    return ShotFeasibilityAssessment(
        "SC01",
        {
            "subject_position_exists": CheckState.PASS,
            "orientation_camera_compatible": CheckState.PASS,
            "required_visible_coexists": CheckState.PASS,
            "prohibited_change_not_required": CheckState.PASS,
            "shot_reference_matches_final_camera": CheckState.PASS,
            "reference_roles_valid": CheckState.PASS,
            "continuity_contract_valid": CheckState.PASS,
            "task_axis_valid": CheckState.PASS,
            "depth_order_valid": CheckState.PASS,
            "occlusion_valid": CheckState.PASS,
            "furniture_integrity_valid": CheckState.PASS,
            "room_anchor_integrity_valid": CheckState.PASS,
            "production_gear_absent": CheckState.PASS,
            "character_identity_valid": CheckState.PASS,
        },
        "TEST",
    )


def test_approved_plan_installs_exact_blueprint_into_production_control() -> None:
    proposal_registry, bp, plan = approved()
    production = ProductionControlRegistry()
    control_plan = ApprovedPlanProductionControlInstaller.install(
        proposal_registry=proposal_registry, plan_id=plan.plan_id, blueprint=bp,
        project_id="project-1", production_registry=production,
    )
    assert control_plan.blueprint_sha256 == plan.blueprint_sha256
    assert "slot:SC01:VIDEO" in production.slots
    assert any(edge.from_ref.entity_id == bp.blueprint_id for edge in production.edges.values())
    approved_edges = [edge for edge in production.edges.values() if edge.from_ref.entity_id == plan.plan_id]
    assert len(approved_edges) == 1
    assert approved_edges[0].from_hash == plan.to_dict()["approved_plan_sha256"]


def test_unregistered_or_wrong_blueprint_cannot_claim_go_approval() -> None:
    proposal_registry, bp, plan = approved()
    with pytest.raises(ProductError) as exc:
        ApprovedPlanProductionControlInstaller.compile(
            proposal_registry=proposal_registry, plan_id="PLAN-0000000000000000",
            blueprint=bp, project_id="project-1",
        )
    assert exc.value.code == "ERR_APPROVED_PLAN_NOT_FOUND"

    different_scene = BlueprintScene(
        "SC01", 0, 301, "Changed", AssetSourceStrategy.AI_GENERATED,
        GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, (),
    )
    changed = ProductionBlueprint("BP-DEMO-001", "Demo", FrameRate(30, 1), 301, (), (different_scene,))
    with pytest.raises(ProductError) as exc:
        ApprovedPlanProductionControlInstaller.compile(
            proposal_registry=proposal_registry, plan_id=plan.plan_id,
            blueprint=changed, project_id="project-1",
        )
    assert exc.value.code == "ERR_APPROVED_PLAN_BLUEPRINT_MISMATCH"


def test_approved_plan_generation_derives_plan_approval_but_keeps_paid_gate() -> None:
    proposal_registry, bp, plan = approved()
    production = ProductionControlRegistry()
    ApprovedPlanProductionControlInstaller.install(
        proposal_registry=proposal_registry, plan_id=plan.plan_id, blueprint=bp,
        project_id="project-1", production_registry=production,
    )
    blocked = ApprovedPlanGenerationAdmissionService.evaluate(
        proposal_registry=proposal_registry, plan_id=plan.plan_id, blueprint=bp,
        scene_id="SC01", slot_id="slot:SC01:VIDEO", feasibility=feasibility(),
        required_input_slot_ids=(), production_registry=production,
        prompt_provider_policy_sha256=POLICY_SHA,
        explicit_paid_execution_authorization=False, cost_required=True,
    )
    assert blocked.status == "BLOCKED"
    assert blocked.cost_authorized is False
    free = ApprovedPlanGenerationAdmissionService.require_ready(
        proposal_registry=proposal_registry, plan_id=plan.plan_id, blueprint=bp,
        scene_id="SC01", slot_id="slot:SC01:VIDEO", feasibility=feasibility(),
        required_input_slot_ids=(), production_registry=production,
        prompt_provider_policy_sha256=POLICY_SHA,
        explicit_paid_execution_authorization=False, cost_required=False,
    )
    assert free.ready is True
    assert free.to_dict()["provider_execution_started"] is False


def test_approved_plan_generation_rejects_provider_policy_drift() -> None:
    proposal_registry, bp, plan = approved()
    production = ProductionControlRegistry()
    ApprovedPlanProductionControlInstaller.install(
        proposal_registry=proposal_registry, plan_id=plan.plan_id, blueprint=bp,
        project_id="project-1", production_registry=production,
    )
    with pytest.raises(ProductError) as exc:
        ApprovedPlanGenerationAdmissionService.evaluate(
            proposal_registry=proposal_registry, plan_id=plan.plan_id, blueprint=bp,
            scene_id="SC01", slot_id="slot:SC01:VIDEO", feasibility=feasibility(),
            required_input_slot_ids=(), production_registry=production,
            prompt_provider_policy_sha256="sha256:" + "d" * 64,
            explicit_paid_execution_authorization=True,
        )
    assert exc.value.code == "ERR_APPROVED_PLAN_PROVIDER_POLICY_MISMATCH"


def test_paid_generation_requires_budget_ledger_bound_to_same_approved_plan() -> None:
    from ai_video_production.approved_plan_orchestration import BudgetedApprovedPlanGenerationAdmissionService
    from ai_video_production.production_budget import ProductionBudgetLedger

    proposal_registry, bp, plan = approved()
    production = ProductionControlRegistry()
    ApprovedPlanProductionControlInstaller.install(
        proposal_registry=proposal_registry, plan_id=plan.plan_id, blueprint=bp,
        project_id="project-1", production_registry=production,
    )
    ledger = ProductionBudgetLedger.from_approved_plan(plan)
    with pytest.raises(ProductError) as exc:
        BudgetedApprovedPlanGenerationAdmissionService.require_ready(
            budget_ledger=ledger, budget_operation_id="job-1",
            proposal_registry=proposal_registry, plan_id=plan.plan_id, blueprint=bp,
            scene_id="SC01", slot_id="slot:SC01:VIDEO", feasibility=feasibility(),
            required_input_slot_ids=(), production_registry=production,
            prompt_provider_policy_sha256=POLICY_SHA,
        )
    assert exc.value.code == "ERR_PRODUCTION_BUDGET_RESERVATION_REQUIRED"
    ledger.reserve(operation_id="job-1", estimated_amount="2")
    result = BudgetedApprovedPlanGenerationAdmissionService.require_ready(
        budget_ledger=ledger, budget_operation_id="job-1",
        proposal_registry=proposal_registry, plan_id=plan.plan_id, blueprint=bp,
        scene_id="SC01", slot_id="slot:SC01:VIDEO", feasibility=feasibility(),
        required_input_slot_ids=(), production_registry=production,
        prompt_provider_policy_sha256=POLICY_SHA,
    )
    assert result.ready is True
    assert result.cost_authorized is True
