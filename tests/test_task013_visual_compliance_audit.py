from __future__ import annotations

from ai_video_production.candidate_audit import CandidateAuditRegistry
from ai_video_production.visual_compliance import (
    CoordinateConvention,
    VisualCheckState,
    VisualComplianceContract,
    VisualComplianceGate,
    VisualContractCheck,
    VisualScoreSet,
)
from ai_video_production.visual_compliance_audit import VisualComplianceAuditAdapter


SHA = "sha256:" + "a" * 64


def contract():
    return VisualComplianceContract(
        "VC-SC01", 1, "SC01",
        (
            VisualContractCheck("depth.order", "Monitor before person", True),
            VisualContractCheck("identity", "Character identity", False),
        ),
        CoordinateConvention.VIEWER,
    )


def decision(depth=VisualCheckState.PASS, identity=VisualCheckState.PASS, failure_codes=()):
    return VisualComplianceGate.evaluate(
        contract(), candidate_id="candidate-1", candidate_asset_sha256=SHA,
        observed_checks={"depth.order": depth, "identity": identity},
        scores=VisualScoreSet(0.9, 0.8, 0.7, 0.95),
        failure_codes=failure_codes, inspector_kind="VISION_JUDGE",
    )


def test_visual_compliance_pass_becomes_ai_audit_not_human_decision():
    audit = VisualComplianceAuditAdapter.to_audit(decision(), audit_id="audit-1", auditor_id="vision-judge")
    registry = CandidateAuditRegistry(); registry.add_audit(audit)
    history = registry.candidate_history("candidate-1")
    assert len(history["audits"]) == 1
    assert history["human_decisions"] == []
    assert audit.to_dict()["critical_violation"] is False
    assert audit.findings[0].code == "VISUAL_CONTRACT_PASS"


def test_critical_visual_failure_maps_to_critical_audit_finding_and_failure_code():
    audit = VisualComplianceAuditAdapter.to_audit(
        decision(VisualCheckState.FAIL, failure_codes=("SPATIAL_RELATION_FAILURE",)),
        audit_id="audit-2", auditor_id="vision-judge",
    )
    assert audit.critical_violation is True
    assert audit.findings[0].critical_violation is True
    assert audit.failure_codes == ("SPATIAL_RELATION_FAILURE",)
    assert audit.dimension_scores["AESTHETIC"] == 95.0
