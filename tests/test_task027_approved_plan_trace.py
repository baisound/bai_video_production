from __future__ import annotations

from decimal import Decimal

import pytest

from ai_video_production.approved_plan_orchestration import ApprovedPlanProductionControlInstaller
from ai_video_production.approved_plan_trace import ApprovedPlanTraceValidator
from ai_video_production.errors import ProductError
from ai_video_production.production_blueprint import (
    AssetSourceStrategy, BlueprintScene, CameraMotion, GenerationRisk, ProductionBlueprint,
)
from ai_video_production.production_control import ProductionControlRegistry
from ai_video_production.production_proposal import (
    CreationIntent, ProductionGoApprovalService, ProductionProposalRegistry,
    ProductionProposalRevision, ProposalSection, ProviderPolicyBinding,
)
from ai_video_production.timebase import FrameRate

POLICY_SHA = "sha256:" + "c" * 64


def installed():
    proposals = ProductionProposalRegistry()
    intent = CreationIntent(
        "INTENT-TRACE", 1, "Intro", "Viewers", "YouTube", "16:9", Decimal("2"),
        "Calm", "Explain", "ja-JP", budget_ceiling=Decimal("5"),
    )
    proposals.add_intent(intent)
    scene = BlueprintScene(
        "SC01", 0, 60, "opening", AssetSourceStrategy.AI_GENERATED,
        GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, (),
    )
    blueprint = ProductionBlueprint("BP-TRACE03", "Trace", FrameRate(30), 60, (), (scene,))
    proposals.add_proposal(ProductionProposalRevision(
        "PROPOSAL-TRACE", 1, intent.to_dict()["intent_sha256"], blueprint,
        (ProposalSection("concept", "CONCEPT", "Concept", "Opening"),),
        ProviderPolicyBinding("policy", "1", POLICY_SHA), Decimal("1"), Decimal("2"), "USD",
    ))
    go = ProductionGoApprovalService(proposals, token_factory=lambda: "go")
    go.prepare_go(
        proposal_id="PROPOSAL-TRACE", proposal_revision=1, reference_bindings=(),
        cost_ceiling="3", rights_warnings_acknowledged=False,
    )
    plan = go.approve_go(confirmation_id="go", approved_by="owner")
    production = ProductionControlRegistry()
    ApprovedPlanProductionControlInstaller.install(
        proposal_registry=proposals, plan_id=plan.plan_id, blueprint=blueprint,
        project_id="project-1", production_registry=production,
    )
    return proposals, production, plan


def test_approved_plan_trace_proves_go_blueprint_scene_slot_chain() -> None:
    proposals, production, plan = installed()
    report = ApprovedPlanTraceValidator.validate(
        proposals=proposals, plan_id=plan.plan_id, production=production, project_id="project-1",
    ).to_dict()
    assert report["status"] == "PASS"
    assert report["human_go_proven"] is True
    assert report["scene_count"] == 1
    assert report["slot_count"] == 4
    assert report["automatic_generation_started"] is False


def test_approved_plan_trace_fails_if_human_go_edge_is_missing() -> None:
    proposals, production, plan = installed()
    key = next(key for key, edge in production.edges.items() if edge.from_ref.entity_id == plan.plan_id)
    del production.edges[key]
    with pytest.raises(ProductError) as exc:
        ApprovedPlanTraceValidator.validate(
            proposals=proposals, plan_id=plan.plan_id, production=production, project_id="project-1",
        )
    assert exc.value.code == "ERR_APPROVED_PLAN_TRACE_PLAN_SCENE_MISSING"
