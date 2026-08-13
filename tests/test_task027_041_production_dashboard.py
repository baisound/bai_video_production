from __future__ import annotations

from decimal import Decimal

import pytest

from ai_video_production.approved_plan_orchestration import ApprovedPlanProductionControlInstaller
from ai_video_production.audio_workspace import AudioWorkspaceRegistry
from ai_video_production.candidate_audit import CandidateAuditRegistry
from ai_video_production.continuity_registry import ContinuityRegistry
from ai_video_production.errors import ProductError
from ai_video_production.production_blueprint import (
    AssetSourceStrategy,
    BlueprintScene,
    CameraMotion,
    GenerationRisk,
    ProductionBlueprint,
)
from ai_video_production.production_budget import ProductionBudgetLedger
from ai_video_production.production_control import AssetCandidate, CandidateLifecycle, ProductionControlRegistry
from ai_video_production.production_dashboard import ProductionDashboardProjection
from ai_video_production.production_proposal import (
    CreationIntent,
    ProductionGoApprovalService,
    ProductionProposalRegistry,
    ProductionProposalRevision,
    ProposalSection,
    ProviderPolicyBinding,
)
from ai_video_production.prompt_registry import PromptGenerationRegistry
from ai_video_production.timebase import FrameRate

POLICY_SHA = "sha256:" + "c" * 64
ASSET_SHA = "sha256:" + "a" * 64


def installed():
    proposals = ProductionProposalRegistry()
    intent = CreationIntent(
        "INTENT-DASH", 1, "Promo", "Viewers", "YouTube", "16:9", Decimal("2"),
        "Calm", "Explain", "ja-JP", budget_ceiling=Decimal("5"),
    )
    proposals.add_intent(intent)
    scene = BlueprintScene(
        "SC01", 0, 60, "opening", AssetSourceStrategy.AI_GENERATED,
        GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, (),
    )
    blueprint = ProductionBlueprint("BP-DASH-001", "Dashboard Demo", FrameRate(30), 60, (), (scene,))
    proposals.add_proposal(ProductionProposalRevision(
        "PROPOSAL-DASH", 1, intent.to_dict()["intent_sha256"], blueprint,
        (ProposalSection("concept", "CONCEPT", "Concept", "Opening"),),
        ProviderPolicyBinding("policy", "1", POLICY_SHA), Decimal("1"), Decimal("2"), "USD",
    ))
    go = ProductionGoApprovalService(proposals, token_factory=lambda: "go")
    go.prepare_go(
        proposal_id="PROPOSAL-DASH", proposal_revision=1, reference_bindings=(),
        cost_ceiling="3", rights_warnings_acknowledged=False,
    )
    plan = go.approve_go(confirmation_id="go", approved_by="owner")
    production = ProductionControlRegistry()
    ApprovedPlanProductionControlInstaller.install(
        proposal_registry=proposals,
        plan_id=plan.plan_id,
        blueprint=blueprint,
        project_id="project-1",
        production_registry=production,
    )
    return proposals, plan, production


def empty_supporting_registries():
    return CandidateAuditRegistry(), PromptGenerationRegistry(), ContinuityRegistry(), AudioWorkspaceRegistry()


def test_dashboard_projects_approved_plan_budget_and_scene_attention_read_only() -> None:
    proposals, plan, production = installed()
    audits, prompts, continuity, audio = empty_supporting_registries()
    budget = ProductionBudgetLedger.from_approved_plan(plan)

    report = ProductionDashboardProjection.build(
        proposals=proposals,
        plan_id=plan.plan_id,
        project_id="project-1",
        budget=budget,
        production=production,
        audits=audits,
        prompts=prompts,
        continuity=continuity,
        audio=audio,
    ).to_dict()

    assert report["status"] == "NEEDS_ATTENTION"
    assert report["human_go_proven"] is True
    assert report["read_only_projection"] is True
    assert report["provider_execution_started"] is False
    assert report["automatic_regeneration_started"] is False
    assert report["budget"]["cost_ceiling"] == "3"
    assert report["budget"]["credit_purchase_authorized"] is False
    scene = report["scenes"][0]
    assert scene["required_slot_count"] == 4
    assert scene["empty_required_slot_count"] == 4
    assert scene["attention_reasons"] == ["REQUIRED_SLOT_EMPTY"]


def test_dashboard_marks_ready_for_audit_candidate_as_human_attention() -> None:
    proposals, plan, production = installed()
    audits, prompts, continuity, audio = empty_supporting_registries()
    budget = ProductionBudgetLedger.from_approved_plan(plan)
    slot_id = "slot:SC01:VIDEO"
    production.add_candidate(AssetCandidate("candidate-1", slot_id, "asset-1", ASSET_SHA, 1))
    production.transition_candidate("candidate-1", CandidateLifecycle.READY_FOR_AUDIT)

    scene = ProductionDashboardProjection.build(
        proposals=proposals, plan_id=plan.plan_id, project_id="project-1", budget=budget,
        production=production, audits=audits, prompts=prompts, continuity=continuity, audio=audio,
    ).to_dict()["scenes"][0]

    assert scene["ready_for_audit_count"] == 1
    assert "HUMAN_AUDIT_DECISION_REQUIRED" in scene["attention_reasons"]
    assert "REQUIRED_SLOT_EMPTY" in scene["attention_reasons"]


def test_dashboard_fails_closed_if_budget_is_not_bound_to_exact_approved_plan() -> None:
    proposals, plan, production = installed()
    audits, prompts, continuity, audio = empty_supporting_registries()
    wrong = ProductionBudgetLedger(plan_id="PLAN-0000000000000000", cost_ceiling="3", currency="USD")

    with pytest.raises(ProductError) as exc:
        ProductionDashboardProjection.build(
            proposals=proposals, plan_id=plan.plan_id, project_id="project-1", budget=wrong,
            production=production, audits=audits, prompts=prompts, continuity=continuity, audio=audio,
        )
    assert exc.value.code == "ERR_PRODUCTION_DASHBOARD_BUDGET_PLAN_MISMATCH"
