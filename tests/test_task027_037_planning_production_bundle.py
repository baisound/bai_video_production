from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from ai_video_production.approved_plan_orchestration import ApprovedPlanProductionControlInstaller
from ai_video_production.errors import ProductError
from ai_video_production.planning_production_bundle import PlanningProductionBundleStore
from ai_video_production.production_blueprint import (
    AssetSourceStrategy, BlueprintScene, CameraMotion, GenerationRisk, ProductionBlueprint,
)
from ai_video_production.production_budget import ProductionBudgetLedger
from ai_video_production.production_budget_store import ProductionBudgetSnapshotStore
from ai_video_production.production_control import ProductionControlRegistry
from ai_video_production.production_control_store import ProductionControlSnapshotStore
from ai_video_production.production_proposal import (
    CreationIntent, ProductionGoApprovalService, ProductionProposalRegistry,
    ProductionProposalRevision, ProposalSection, ProviderPolicyBinding,
)
from ai_video_production.production_proposal_store import ProductionProposalSnapshotStore
from ai_video_production.timebase import FrameRate

POLICY_SHA = "sha256:" + "c" * 64


def state():
    proposals = ProductionProposalRegistry()
    intent = CreationIntent(
        "INTENT-BUNDLE", 1, "Intro", "Viewers", "YouTube", "16:9", Decimal("2"),
        "Calm", "Explain", "ja-JP", budget_ceiling=Decimal("5"),
    )
    proposals.add_intent(intent)
    scene = BlueprintScene(
        "SC01", 0, 60, "opening", AssetSourceStrategy.AI_GENERATED,
        GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, (),
    )
    blueprint = ProductionBlueprint("BP-BUNDLE1", "Bundle", FrameRate(30), 60, (), (scene,))
    proposals.add_proposal(ProductionProposalRevision(
        "PROPOSAL-BUNDLE", 1, intent.to_dict()["intent_sha256"], blueprint,
        (ProposalSection("concept", "CONCEPT", "Concept", "Opening"),),
        ProviderPolicyBinding("policy", "1", POLICY_SHA), Decimal("1"), Decimal("2"), "USD",
    ))
    go = ProductionGoApprovalService(proposals, token_factory=lambda: "go")
    go.prepare_go(
        proposal_id="PROPOSAL-BUNDLE", proposal_revision=1, reference_bindings=(),
        cost_ceiling="3", rights_warnings_acknowledged=False,
    )
    plan = go.approve_go(confirmation_id="go", approved_by="owner")
    budget = ProductionBudgetLedger.from_approved_plan(plan)
    production = ProductionControlRegistry()
    ApprovedPlanProductionControlInstaller.install(
        proposal_registry=proposals, plan_id=plan.plan_id, blueprint=blueprint,
        project_id="project-1", production_registry=production,
    )
    return proposals, plan, budget, production


def write_bundle(root: Path):
    proposals, plan, budget, production = state()
    ProductionProposalSnapshotStore.save(root / "production-proposal.json", proposals)
    ProductionBudgetSnapshotStore.save(root / "production-budget.json", budget)
    ProductionControlSnapshotStore.save(root / "production-control.json", production)
    manifest = PlanningProductionBundleStore.build(
        proposals=proposals, plan_id=plan.plan_id, budget=budget,
        production=production, project_id="project-1",
    )
    PlanningProductionBundleStore.save(root / "planning-production-bundle.json", manifest)
    return proposals, plan, budget, production, manifest


def test_planning_production_bundle_recovers_exact_go_budget_production_set(tmp_path: Path) -> None:
    proposals, plan, budget, production, manifest = write_bundle(tmp_path)
    recovered = PlanningProductionBundleStore.recover(tmp_path)
    assert recovered.proposals.to_dict() == proposals.to_dict()
    assert recovered.budget.to_dict() == budget.to_dict()
    assert ProductionControlSnapshotStore.snapshot(recovered.production) == ProductionControlSnapshotStore.snapshot(production)
    assert recovered.trace.plan_id == plan.plan_id
    assert recovered.manifest_sha256 == manifest["manifest_sha256"]


def test_planning_production_bundle_rejects_mixed_new_budget_snapshot(tmp_path: Path) -> None:
    _proposals, _plan, budget, _production, _manifest = write_bundle(tmp_path)
    old = ProductionBudgetSnapshotStore.snapshot(budget)["snapshot_sha256"]
    budget.reserve(operation_id="job-1", estimated_amount="1")
    ProductionBudgetSnapshotStore.save(
        tmp_path / "production-budget.json", budget,
        expected_previous_snapshot_sha256=old,
    )
    with pytest.raises(ProductError) as exc:
        PlanningProductionBundleStore.recover(tmp_path)
    assert exc.value.code == "ERR_PLANNING_BUNDLE_SNAPSHOT_SET_CHANGED"
    assert exc.value.details["changed_stores"] == ["budget"]


def test_planning_production_bundle_rejects_budget_for_other_plan() -> None:
    proposals, plan, _budget, production = state()
    wrong = ProductionBudgetLedger(plan_id="PLAN-FFFFFFFFFFFFFFFF", cost_ceiling="3", currency="USD")
    with pytest.raises(ProductError) as exc:
        PlanningProductionBundleStore.build(
            proposals=proposals, plan_id=plan.plan_id, budget=wrong,
            production=production, project_id="project-1",
        )
    assert exc.value.code == "ERR_PLANNING_BUNDLE_BUDGET_PLAN_MISMATCH"
