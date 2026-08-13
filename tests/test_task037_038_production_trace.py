from __future__ import annotations

import pytest

from ai_video_production.audit_production_binding import AuditProductionControlBinding
from ai_video_production.candidate_audit import (
    AuditDimension,
    AuditFinding,
    AuditRecord,
    AuditorKind,
    CandidateAuditRegistry,
    FindingSeverity,
    HumanCandidateDecision,
    HumanDecision,
)
from ai_video_production.errors import ProductError
from ai_video_production.production_blueprint import (
    AssetSourceStrategy,
    BlueprintReference,
    BlueprintScene,
    CameraMotion,
    GenerationRisk,
    ProductionBlueprint,
    ReferenceKind,
    ReferenceStatus,
    SceneAudioPlan,
)
from ai_video_production.production_control import AssetCandidate, ProductionControlRegistry
from ai_video_production.production_orchestrator import BlueprintProductionControlCompiler
from ai_video_production.production_trace import ProductionTraceService
from ai_video_production.timebase import FrameRate


SHA = "sha256:" + "a" * 64


def blueprint() -> ProductionBlueprint:
    return ProductionBlueprint(
        "BP-TRACE01", "Trace", FrameRate(30), 60,
        (BlueprintReference("REF-ROOM", ReferenceKind.SPACE, ReferenceStatus.LOCKED, "room.png"),),
        (BlueprintScene("SC01", 0, 60, "opening", AssetSourceStrategy.AI_GENERATED, GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, ("REF-ROOM",), SceneAudioPlan(bgm=False)),),
    )


def audit() -> AuditRecord:
    return AuditRecord(
        "audit-1", "candidate-1", SHA, ("contract-1",), AuditorKind.AI, "vision-judge", "v1",
        {"CONTRACT": 100.0},
        (AuditFinding("finding-1", AuditDimension.CONTRACT, FindingSeverity.INFO, "PASS", "pass", False),),
        (),
    )


def setup_locked(*, with_audit: bool = True):
    plan = BlueprintProductionControlCompiler.compile(blueprint(), project_id="project-1")
    production = ProductionControlRegistry(); BlueprintProductionControlCompiler.install(plan, production)
    slot_id = "slot:SC01:START_FRAME"
    production.add_candidate(AssetCandidate("candidate-1", slot_id, "asset-1", SHA, 1))
    audits = CandidateAuditRegistry()
    if with_audit:
        AuditProductionControlBinding.record_audit(production, audits, audit())
        AuditProductionControlBinding.apply_human_decision(
            production, audits,
            HumanDecision("decision-1", "candidate-1", ("audit-1",), HumanCandidateDecision.ACCEPT, "owner"),
        )
    else:
        from ai_video_production.production_control import CandidateLifecycle
        production.transition_candidate("candidate-1", CandidateLifecycle.READY_FOR_AUDIT)
        production.transition_candidate("candidate-1", CandidateLifecycle.ACCEPTED)
    slot = production.slots[slot_id]
    production.lock_candidate(slot_id=slot_id, candidate_id="candidate-1", expected_revision=slot.revision)
    return production, audits, slot_id


def test_locked_trace_proves_plan_scene_slot_candidate_audit_human_lock_chain():
    production, audits, slot_id = setup_locked()
    trace = ProductionTraceService.locked_asset_trace(
        plan_id="BP-TRACE01", slot_id=slot_id, production=production, audits=audits
    ).to_dict()
    assert trace["plan_id"] == "BP-TRACE01"
    assert trace["scene_id"] == "SC01"
    assert trace["candidate_id"] == "candidate-1"
    assert trace["audit_ids"] == ["audit-1"]
    assert trace["human_decision_id"] == "decision-1"
    assert trace["slot_locked"] is True
    assert trace["trace_sha256"].startswith("sha256:")


def test_manual_lifecycle_lock_without_audit_evidence_fails_trace():
    production, audits, slot_id = setup_locked(with_audit=False)
    with pytest.raises(ProductError) as exc:
        ProductionTraceService.locked_asset_trace(
            plan_id="BP-TRACE01", slot_id=slot_id, production=production, audits=audits
        )
    assert exc.value.code == "ERR_PRODUCTION_TRACE_AUDIT_MISSING"


def test_wrong_plan_identity_fails_closed_instead_of_guessing_trace():
    production, audits, slot_id = setup_locked()
    with pytest.raises(ProductError) as exc:
        ProductionTraceService.locked_asset_trace(
            plan_id="BP-WRONG1", slot_id=slot_id, production=production, audits=audits
        )
    assert exc.value.code == "ERR_PRODUCTION_TRACE_PLAN_SCENE_MISSING"
