from __future__ import annotations

import pytest

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


SHA = "sha256:" + "b" * 64


def audit(audit_id: str = "audit-1", candidate_id: str = "candidate-1") -> AuditRecord:
    return AuditRecord(
        audit_id=audit_id,
        candidate_id=candidate_id,
        asset_sha256=SHA,
        contract_refs=("contract-1",),
        auditor_kind=AuditorKind.AI,
        auditor_id="vision-judge",
        auditor_version="v1",
        dimension_scores={"CONTRACT": 88.0, "COMPOSITION": 97.0},
        findings=(AuditFinding("finding-1", AuditDimension.GEOMETRY, FindingSeverity.CRITICAL, "DEPTH_ORDER_REVERSED", "monitor is behind actor", True),),
        failure_codes=("DEPTH_ORDER_REVERSED",),
    )


def test_audit_hash_preserves_critical_violation_separate_from_score():
    record = audit()
    body = record.to_dict()
    assert body["critical_violation"] is True
    assert body["dimension_scores"]["COMPOSITION"] == 97.0
    assert body["record_sha256"].startswith("sha256:")


def test_human_decision_is_separate_from_ai_audit():
    registry = CandidateAuditRegistry()
    registry.add_audit(audit())
    decision = HumanDecision(
        "decision-1", "candidate-1", ("audit-1",), HumanCandidateDecision.NEEDS_REGENERATION, "owner"
    )
    registry.add_human_decision(decision)
    history = registry.candidate_history("candidate-1")
    assert history["human_final_authority_preserved"] is True
    assert history["human_decisions"][0]["decision"] == "NEEDS_REGENERATION"


def test_human_decision_cannot_reference_other_candidates_audit():
    registry = CandidateAuditRegistry()
    registry.add_audit(audit(candidate_id="candidate-1"))
    decision = HumanDecision("decision-1", "candidate-2", ("audit-1",), HumanCandidateDecision.ACCEPT, "owner")
    with pytest.raises(ProductError) as exc:
        registry.add_human_decision(decision)
    assert exc.value.code == "ERR_AUDIT_CANDIDATE_MISMATCH"


def test_audit_history_does_not_delete_rejected_candidate_bytes():
    registry = CandidateAuditRegistry()
    registry.add_audit(audit())
    registry.add_human_decision(HumanDecision("decision-1", "candidate-1", ("audit-1",), HumanCandidateDecision.REJECT, "owner"))
    history = registry.candidate_history("candidate-1")
    assert history["human_decisions"][0]["decision"] == "REJECT"
    assert "physical_delete" not in history
