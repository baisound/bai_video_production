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
from ai_video_production.production_control import (
    AssetCandidate,
    CandidateLifecycle,
    ProductionControlRegistry,
    SceneAssetSlot,
    SlotKind,
)


SHA = "sha256:" + "a" * 64
OTHER_SHA = "sha256:" + "b" * 64


def production() -> ProductionControlRegistry:
    value = ProductionControlRegistry()
    value.add_slot(SceneAssetSlot("slot-1", "project-1", "scene-1", SlotKind.START_FRAME, True))
    value.add_candidate(AssetCandidate("candidate-1", "slot-1", "asset-1", SHA, 1))
    return value


def audit(*, sha: str = SHA, audit_id: str = "audit-1") -> AuditRecord:
    return AuditRecord(
        audit_id,
        "candidate-1",
        sha,
        ("contract-1",),
        AuditorKind.AI,
        "vision-judge",
        "v1",
        {"CONTRACT": 95.0},
        (AuditFinding("finding-1", AuditDimension.GEOMETRY, FindingSeverity.CRITICAL, "DEPTH_REVERSED", "wrong depth", True),),
        ("DEPTH_REVERSED",),
    )


def decision(kind: HumanCandidateDecision, decision_id: str = "decision-1") -> HumanDecision:
    return HumanDecision(decision_id, "candidate-1", ("audit-1",), kind, "owner")


def test_record_audit_requires_exact_candidate_asset_and_marks_ready_for_audit():
    prod = production()
    audits = CandidateAuditRegistry()
    AuditProductionControlBinding.record_audit(prod, audits, audit())
    assert prod.candidates["candidate-1"].lifecycle_state is CandidateLifecycle.READY_FOR_AUDIT
    assert "audit-1" in audits.audit_records


def test_record_audit_hash_mismatch_is_fail_closed_without_partial_state():
    prod = production()
    audits = CandidateAuditRegistry()
    with pytest.raises(ProductError) as exc:
        AuditProductionControlBinding.record_audit(prod, audits, audit(sha=OTHER_SHA))
    assert exc.value.code == "ERR_AUDIT_PRODUCTION_ASSET_HASH_MISMATCH"
    assert prod.candidates["candidate-1"].lifecycle_state is CandidateLifecycle.CREATED
    assert not audits.audit_records


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        (HumanCandidateDecision.ACCEPT, CandidateLifecycle.ACCEPTED),
        (HumanCandidateDecision.REJECT, CandidateLifecycle.REJECTED),
        (HumanCandidateDecision.ALTERNATE_USE, CandidateLifecycle.ALTERNATE_USE),
    ],
)
def test_human_terminal_decisions_drive_production_lifecycle(kind, expected):
    prod = production()
    audits = CandidateAuditRegistry()
    AuditProductionControlBinding.record_audit(prod, audits, audit())
    result = AuditProductionControlBinding.apply_human_decision(prod, audits, decision(kind))
    assert result.lifecycle_after is expected
    assert prod.candidates["candidate-1"].lifecycle_state is expected
    assert result.to_dict()["human_final_authority_preserved"] is True
    assert result.to_dict()["physical_delete_requested"] is False


def test_needs_regeneration_is_traceable_but_does_not_generate_or_change_candidate_lifecycle():
    prod = production()
    audits = CandidateAuditRegistry()
    AuditProductionControlBinding.record_audit(prod, audits, audit())
    result = AuditProductionControlBinding.apply_human_decision(
        prod, audits, decision(HumanCandidateDecision.NEEDS_REGENERATION)
    )
    assert result.regeneration_requested is True
    assert result.lifecycle_after is CandidateLifecycle.READY_FOR_AUDIT
    assert prod.candidates["candidate-1"].lifecycle_state is CandidateLifecycle.READY_FOR_AUDIT
    assert result.to_dict()["automatic_regeneration_started"] is False


def test_ai_critical_finding_never_changes_lifecycle_without_human_decision():
    prod = production()
    audits = CandidateAuditRegistry()
    AuditProductionControlBinding.record_audit(prod, audits, audit())
    assert audits.audit_records["audit-1"].critical_violation is True
    assert prod.candidates["candidate-1"].lifecycle_state is CandidateLifecycle.READY_FOR_AUDIT


def test_second_human_lifecycle_decision_is_rejected():
    prod = production()
    audits = CandidateAuditRegistry()
    AuditProductionControlBinding.record_audit(prod, audits, audit())
    AuditProductionControlBinding.apply_human_decision(
        prod, audits, decision(HumanCandidateDecision.NEEDS_REGENERATION)
    )
    with pytest.raises(ProductError) as exc:
        AuditProductionControlBinding.apply_human_decision(
            prod, audits, decision(HumanCandidateDecision.ACCEPT, "decision-2")
        )
    assert exc.value.code == "ERR_AUDIT_PRODUCTION_DECISION_ALREADY_RECORDED"


def test_stale_audit_hash_is_rejected_before_human_decision_is_stored():
    prod = production()
    audits = CandidateAuditRegistry()
    # Bypass the binding to simulate imported/stale audit state.
    audits.add_audit(audit(sha=OTHER_SHA))
    prod.transition_candidate("candidate-1", CandidateLifecycle.READY_FOR_AUDIT)
    with pytest.raises(ProductError) as exc:
        AuditProductionControlBinding.apply_human_decision(
            prod, audits, decision(HumanCandidateDecision.ACCEPT)
        )
    assert exc.value.code == "ERR_AUDIT_PRODUCTION_ASSET_HASH_MISMATCH"
    assert not audits.decisions
    assert prod.candidates["candidate-1"].lifecycle_state is CandidateLifecycle.READY_FOR_AUDIT
