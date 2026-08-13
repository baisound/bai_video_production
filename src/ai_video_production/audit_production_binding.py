"""TASK-038 -> TASK-037 Human audit decision binding.

The binding makes Audit Workspace decisions affect Production Control lifecycle
without allowing AI scores, critical findings, or regeneration requests to
silently choose an Asset Candidate. HumanDecision remains the authority input.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .candidate_audit import (
    AuditRecord,
    CandidateAuditRegistry,
    HumanCandidateDecision,
    HumanDecision,
)
from .errors import ProductError, ProductErrorCategory
from .production_control import CandidateLifecycle, ProductionControlRegistry
from .serialization import canonical_json_bytes, sha256_bytes


_DECISION_TARGET: dict[HumanCandidateDecision, CandidateLifecycle | None] = {
    HumanCandidateDecision.ACCEPT: CandidateLifecycle.ACCEPTED,
    HumanCandidateDecision.REJECT: CandidateLifecycle.REJECTED,
    HumanCandidateDecision.ALTERNATE_USE: CandidateLifecycle.ALTERNATE_USE,
    HumanCandidateDecision.NEEDS_REGENERATION: None,
}


@dataclass(frozen=True, slots=True)
class AuditProductionBindingResult:
    candidate_id: str
    decision_id: str
    decision: HumanCandidateDecision
    lifecycle_before: CandidateLifecycle
    lifecycle_after: CandidateLifecycle
    regeneration_requested: bool

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "report_version": "1.0.0",
            "task_owner": "TASK-038",
            "candidate_id": self.candidate_id,
            "decision_id": self.decision_id,
            "decision": self.decision.value,
            "lifecycle_before": self.lifecycle_before.value,
            "lifecycle_after": self.lifecycle_after.value,
            "regeneration_requested": self.regeneration_requested,
            "automatic_regeneration_started": False,
            "physical_delete_requested": False,
            "human_final_authority_preserved": True,
        }
        body["report_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class AuditProductionControlBinding:
    """Bind immutable audits/Human decisions to Production Control state."""

    @staticmethod
    def _production_candidate(production: ProductionControlRegistry, candidate_id: str):
        candidate = production.candidates.get(candidate_id)
        if candidate is None:
            raise ProductError(
                "ERR_AUDIT_PRODUCTION_CANDIDATE_NOT_FOUND",
                "Audit candidate does not exist in Production Control",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return candidate

    @classmethod
    def record_audit(
        cls,
        production: ProductionControlRegistry,
        audits: CandidateAuditRegistry,
        record: AuditRecord,
    ) -> None:
        """Record an audit only against the exact Candidate Asset identity.

        First audit registration moves CREATED -> READY_FOR_AUDIT. The method
        never accepts/rejects a Candidate based on AI or Human audit content.
        """
        candidate = cls._production_candidate(production, record.candidate_id)
        if candidate.asset_sha256 != record.asset_sha256:
            raise ProductError(
                "ERR_AUDIT_PRODUCTION_ASSET_HASH_MISMATCH",
                "Audit asset checksum does not match the Production Candidate",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if candidate.lifecycle_state not in {
            CandidateLifecycle.CREATED,
            CandidateLifecycle.READY_FOR_AUDIT,
        }:
            raise ProductError(
                "ERR_AUDIT_PRODUCTION_CANDIDATE_NOT_AUDITABLE",
                "Terminal/accepted Candidate cannot receive a new lifecycle-driving audit",
                ProductErrorCategory.STATE,
                details={"lifecycle_state": candidate.lifecycle_state.value},
            )
        # Validate audit id conflict before changing Production state so the two
        # in-memory registries cannot become partially updated on a known error.
        if record.audit_id in audits.audit_records:
            raise ProductError(
                "ERR_AUDIT_RECORD_CONFLICT",
                "audit_id already exists",
                ProductErrorCategory.STATE,
            )
        audits.add_audit(record)
        if candidate.lifecycle_state is CandidateLifecycle.CREATED:
            production.transition_candidate(record.candidate_id, CandidateLifecycle.READY_FOR_AUDIT)

    @classmethod
    def apply_human_decision(
        cls,
        production: ProductionControlRegistry,
        audits: CandidateAuditRegistry,
        decision: HumanDecision,
    ) -> AuditProductionBindingResult:
        """Apply one Human decision to one exact audited Candidate.

        NEEDS_REGENERATION is deliberately non-mutating for the Candidate
        lifecycle and does not start generation. A later orchestrator/Human GO
        may create a new version while the current Candidate remains traceable.
        """
        candidate = cls._production_candidate(production, decision.candidate_id)
        before = candidate.lifecycle_state
        if before is not CandidateLifecycle.READY_FOR_AUDIT:
            raise ProductError(
                "ERR_AUDIT_PRODUCTION_DECISION_STATE_INVALID",
                "Human audit decision requires a READY_FOR_AUDIT Candidate",
                ProductErrorCategory.STATE,
                details={"lifecycle_state": before.value},
            )
        if decision.decision_id in audits.decisions:
            raise ProductError(
                "ERR_AUDIT_DECISION_CONFLICT",
                "decision_id already exists",
                ProductErrorCategory.STATE,
            )
        existing = [item for item in audits.decisions.values() if item.candidate_id == decision.candidate_id]
        if existing:
            raise ProductError(
                "ERR_AUDIT_PRODUCTION_DECISION_ALREADY_RECORDED",
                "Candidate already has a Human lifecycle decision",
                ProductErrorCategory.STATE,
                details={"decision_ids": sorted(item.decision_id for item in existing)},
            )

        # Fully pre-validate references and exact Asset identity before mutating
        # either registry. CandidateAuditRegistry.add_human_decision repeats the
        # candidate-reference validation as a second integrity boundary.
        for audit_id in decision.audit_refs:
            record = audits.audit_records.get(audit_id)
            if record is None:
                raise ProductError(
                    "ERR_AUDIT_REFERENCE_NOT_FOUND",
                    "Human decision references an unknown audit",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            if record.candidate_id != decision.candidate_id:
                raise ProductError(
                    "ERR_AUDIT_CANDIDATE_MISMATCH",
                    "Human decision audit belongs to a different Candidate",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            if record.asset_sha256 != candidate.asset_sha256:
                raise ProductError(
                    "ERR_AUDIT_PRODUCTION_ASSET_HASH_MISMATCH",
                    "Human decision references an audit of a different Asset checksum",
                    ProductErrorCategory.DATA_INTEGRITY,
                )

        target = _DECISION_TARGET[decision.decision]
        audits.add_human_decision(decision)
        if target is None:
            after = before
        else:
            after = production.transition_candidate(decision.candidate_id, target).lifecycle_state

        return AuditProductionBindingResult(
            candidate_id=decision.candidate_id,
            decision_id=decision.decision_id,
            decision=decision.decision,
            lifecycle_before=before,
            lifecycle_after=after,
            regeneration_requested=decision.decision is HumanCandidateDecision.NEEDS_REGENERATION,
        )
