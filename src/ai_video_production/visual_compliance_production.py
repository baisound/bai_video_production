"""TASK-013 Visual Compliance -> TASK-038 audit -> TASK-037 Candidate bridge.

This integration records machine inspection Evidence against the exact Production
Candidate. It intentionally stops at READY_FOR_AUDIT; no Visual/AI result can
perform the Human Candidate decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .audit_production_binding import AuditProductionControlBinding
from .candidate_audit import CandidateAuditRegistry
from .production_control import CandidateLifecycle, ProductionControlRegistry
from .visual_compliance import VisualComplianceDecision
from .visual_compliance_audit import VisualComplianceAuditAdapter


@dataclass(frozen=True, slots=True)
class VisualComplianceProductionResult:
    audit_id: str
    candidate_id: str
    critical_pass: bool
    candidate_lifecycle: CandidateLifecycle
    human_decision_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": "1.0.0",
            "task_owner": "TASK-013/TASK-038",
            "audit_id": self.audit_id,
            "candidate_id": self.candidate_id,
            "critical_pass": self.critical_pass,
            "candidate_lifecycle": self.candidate_lifecycle.value,
            "human_decision_required": self.human_decision_required,
            "automatic_candidate_accept": False,
            "automatic_candidate_reject": False,
            "automatic_regeneration_started": False,
        }


class VisualComplianceProductionControlService:
    @staticmethod
    def record_inspection(
        decision: VisualComplianceDecision,
        *,
        audit_id: str,
        auditor_id: str,
        auditor_version: str | None,
        production: ProductionControlRegistry,
        audits: CandidateAuditRegistry,
    ) -> VisualComplianceProductionResult:
        record = VisualComplianceAuditAdapter.to_audit(
            decision,
            audit_id=audit_id,
            auditor_id=auditor_id,
            auditor_version=auditor_version,
        )
        AuditProductionControlBinding.record_audit(production, audits, record)
        candidate = production.candidates[record.candidate_id]
        return VisualComplianceProductionResult(
            audit_id=record.audit_id,
            candidate_id=record.candidate_id,
            critical_pass=not record.critical_violation,
            candidate_lifecycle=candidate.lifecycle_state,
        )
