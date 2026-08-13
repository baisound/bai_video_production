"""TASK-013 -> TASK-038 adapter for Visual Compliance inspection Evidence.

The adapter converts a structured Visual Compliance decision into an immutable AI
AuditRecord. It never creates a HumanDecision or accepts/rejects an Asset itself.
"""

from __future__ import annotations

from .candidate_audit import (
    AuditDimension,
    AuditFinding,
    AuditRecord,
    AuditorKind,
    FindingSeverity,
)
from .visual_compliance import VisualComplianceDecision, VisualDecision


class VisualComplianceAuditAdapter:
    @staticmethod
    def to_audit(
        decision: VisualComplianceDecision,
        *,
        audit_id: str,
        auditor_id: str,
        auditor_version: str | None = None,
    ) -> AuditRecord:
        inspection = decision.inspection
        findings: list[AuditFinding] = []
        for index, check_id in enumerate(decision.failed_check_ids, 1):
            findings.append(AuditFinding(
                finding_id=f"{audit_id}:fail:{index:03d}",
                dimension=AuditDimension.CONTRACT,
                severity=FindingSeverity.CRITICAL if not decision.critical_pass else FindingSeverity.ERROR,
                code="VISUAL_CONTRACT_FAIL",
                summary=f"Visual contract check failed: {check_id}",
                critical_violation=not decision.critical_pass,
            ))
        for index, check_id in enumerate(decision.unverified_check_ids, 1):
            findings.append(AuditFinding(
                finding_id=f"{audit_id}:review:{index:03d}",
                dimension=AuditDimension.CONTRACT,
                severity=FindingSeverity.WARNING,
                code="VISUAL_CHECK_UNVERIFIED",
                summary=f"Visual contract check requires review: {check_id}",
                critical_violation=False,
            ))
        if decision.decision is VisualDecision.ELIGIBLE_FOR_HUMAN_APPROVAL and not findings:
            findings.append(AuditFinding(
                finding_id=f"{audit_id}:eligible:001",
                dimension=AuditDimension.CONTRACT,
                severity=FindingSeverity.INFO,
                code="VISUAL_CONTRACT_PASS",
                summary="All structured Visual Compliance checks passed; Human approval remains separate.",
                critical_violation=False,
            ))
        scores = inspection.scores
        return AuditRecord(
            audit_id=audit_id,
            candidate_id=inspection.candidate_id,
            asset_sha256=inspection.candidate_asset_sha256,
            contract_refs=(inspection.contract_id,),
            auditor_kind=AuditorKind.AI,
            auditor_id=auditor_id,
            auditor_version=auditor_version,
            dimension_scores={
                "CONTRACT": scores.contract_compliance * 100.0,
                "IDENTITY": scores.character_consistency * 100.0,
                "COMPOSITION": scores.composition * 100.0,
                "AESTHETIC": scores.aesthetic * 100.0,
            },
            findings=tuple(findings),
            failure_codes=inspection.failure_codes,
        )
