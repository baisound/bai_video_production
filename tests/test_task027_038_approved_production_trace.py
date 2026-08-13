from __future__ import annotations

from decimal import Decimal

from ai_video_production.approved_plan_orchestration import ApprovedPlanProductionControlInstaller
from ai_video_production.audit_production_binding import AuditProductionControlBinding
from ai_video_production.candidate_audit import (
    AuditDimension, AuditFinding, AuditRecord, AuditorKind, CandidateAuditRegistry,
    FindingSeverity, HumanCandidateDecision, HumanDecision,
)
from ai_video_production.production_blueprint import (
    AssetSourceStrategy, BlueprintScene, CameraMotion, GenerationRisk, ProductionBlueprint,
)
from ai_video_production.production_control import AssetCandidate, ProductionControlRegistry
from ai_video_production.production_proposal import (
    CreationIntent, ProductionGoApprovalService, ProductionProposalRegistry,
    ProductionProposalRevision, ProposalSection, ProviderPolicyBinding,
)
from ai_video_production.production_trace import ProductionTraceService
from ai_video_production.timebase import FrameRate


ASSET_SHA = "sha256:" + "a" * 64
POLICY_SHA = "sha256:" + "c" * 64


def test_human_go_to_locked_asset_trace_uses_true_approved_plan_identity() -> None:
    proposals = ProductionProposalRegistry()
    intent = CreationIntent(
        "INTENT-TRACE", 1, "Intro", "Viewers", "YouTube", "16:9", Decimal("2"),
        "Calm", "Opening", "ja-JP", budget_ceiling=Decimal("5"),
    )
    proposals.add_intent(intent)
    scene = BlueprintScene(
        "SC01", 0, 60, "opening", AssetSourceStrategy.AI_GENERATED,
        GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, (),
    )
    blueprint = ProductionBlueprint("BP-TRACE02", "Trace", FrameRate(30), 60, (), (scene,))
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
    approved = go.approve_go(confirmation_id="go", approved_by="owner")

    production = ProductionControlRegistry()
    ApprovedPlanProductionControlInstaller.install(
        proposal_registry=proposals, plan_id=approved.plan_id, blueprint=blueprint,
        project_id="project-1", production_registry=production,
    )
    slot_id = "slot:SC01:START_FRAME"
    production.add_candidate(AssetCandidate("candidate-1", slot_id, "asset-1", ASSET_SHA, 1))

    audits = CandidateAuditRegistry()
    audit = AuditRecord(
        "audit-1", "candidate-1", ASSET_SHA, ("contract-1",), AuditorKind.AI,
        "vision-judge", "v1", {"CONTRACT": 100.0},
        (AuditFinding("finding-1", AuditDimension.CONTRACT, FindingSeverity.INFO, "PASS", "pass"),),
        (),
    )
    AuditProductionControlBinding.record_audit(production, audits, audit)
    AuditProductionControlBinding.apply_human_decision(
        production, audits,
        HumanDecision("decision-1", "candidate-1", ("audit-1",), HumanCandidateDecision.ACCEPT, "owner"),
    )
    slot = production.slots[slot_id]
    production.lock_candidate(slot_id=slot_id, candidate_id="candidate-1", expected_revision=slot.revision)

    trace = ProductionTraceService.locked_asset_trace(
        plan_id=approved.plan_id, slot_id=slot_id, production=production, audits=audits,
    ).to_dict()
    assert trace["plan_id"] == approved.plan_id
    assert trace["human_decision_id"] == "decision-1"
    assert trace["candidate_locked"] is True
