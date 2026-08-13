"""TASK-038 Audit Workspace projection and Human-final-authority service.

This module is UI/toolkit neutral.  It projects Production Control + immutable
Audit records into one review surface and binds an exact one-shot Human decision
confirmation to Candidate bytes and the current audit set.  It does not delete
media, start regeneration, or execute a Provider.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import secrets
from typing import Any, Callable

from .audit_production_binding import AuditProductionControlBinding
from .candidate_audit import CandidateAuditRegistry, HumanCandidateDecision, HumanDecision
from .errors import ProductError, ProductErrorCategory
from .production_control import CandidateLifecycle, ProductionControlRegistry
from .serialization import canonical_json_bytes, sha256_bytes


TokenFactory = Callable[[], str]


@dataclass(frozen=True, slots=True)
class AuditWorkspaceCandidateRow:
    candidate_id: str
    slot_id: str
    scene_id: str
    asset_id: str
    asset_sha256: str
    lifecycle_state: str
    slot_status: str
    audit_count: int
    ai_audit_count: int
    human_audit_count: int
    critical_violation: bool
    failure_codes: tuple[str, ...]
    latest_dimension_scores: dict[str, float]
    human_decision: str | None
    regeneration_requested: bool
    available_human_actions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "slot_id": self.slot_id,
            "scene_id": self.scene_id,
            "asset_id": self.asset_id,
            "asset_sha256": self.asset_sha256,
            "lifecycle_state": self.lifecycle_state,
            "slot_status": self.slot_status,
            "audit_count": self.audit_count,
            "ai_audit_count": self.ai_audit_count,
            "human_audit_count": self.human_audit_count,
            "critical_violation": self.critical_violation,
            "failure_codes": list(self.failure_codes),
            "latest_dimension_scores": dict(sorted(self.latest_dimension_scores.items())),
            "human_decision": self.human_decision,
            "regeneration_requested": self.regeneration_requested,
            "available_human_actions": list(self.available_human_actions),
            "ai_score_is_human_decision": False,
        }


class Task038AuditWorkspaceProjection:
    @staticmethod
    def build(
        *,
        production: ProductionControlRegistry,
        audits: CandidateAuditRegistry,
        scene_id: str | None = None,
    ) -> dict[str, Any]:
        rows: list[AuditWorkspaceCandidateRow] = []
        candidates = sorted(
            production.candidates.values(),
            key=lambda item: (item.slot_id, item.candidate_version, item.candidate_id),
        )
        for candidate in candidates:
            slot = production.slots.get(candidate.slot_id)
            if slot is None:
                raise ProductError(
                    "ERR_AUDIT_WORKSPACE_SLOT_MISSING",
                    "Production Candidate references a missing Slot",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"candidate_id": candidate.candidate_id},
                )
            if scene_id is not None and slot.scene_id != scene_id:
                continue
            candidate_audits = sorted(
                (item for item in audits.audit_records.values() if item.candidate_id == candidate.candidate_id),
                key=lambda item: item.audit_id,
            )
            decisions = sorted(
                (item for item in audits.decisions.values() if item.candidate_id == candidate.candidate_id),
                key=lambda item: item.decision_id,
            )
            if len(decisions) > 1:
                raise ProductError(
                    "ERR_AUDIT_WORKSPACE_MULTIPLE_HUMAN_DECISIONS",
                    "Candidate has multiple Human lifecycle decisions",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"candidate_id": candidate.candidate_id},
                )
            for record in candidate_audits:
                if record.asset_sha256 != candidate.asset_sha256:
                    raise ProductError(
                        "ERR_AUDIT_WORKSPACE_ASSET_HASH_MISMATCH",
                        "Audit Workspace found an Audit for stale/different Candidate bytes",
                        ProductErrorCategory.DATA_INTEGRITY,
                        details={"candidate_id": candidate.candidate_id, "audit_id": record.audit_id},
                    )
            failures = tuple(sorted({code for item in candidate_audits for code in item.failure_codes}))
            latest_scores = dict(candidate_audits[-1].dimension_scores) if candidate_audits else {}
            decision = decisions[0].decision if decisions else None
            actions: tuple[str, ...] = ()
            if (
                candidate.lifecycle_state is CandidateLifecycle.READY_FOR_AUDIT
                and candidate_audits
                and decision is None
            ):
                actions = tuple(item.value for item in HumanCandidateDecision)
            rows.append(AuditWorkspaceCandidateRow(
                candidate_id=candidate.candidate_id,
                slot_id=candidate.slot_id,
                scene_id=slot.scene_id,
                asset_id=candidate.asset_id,
                asset_sha256=candidate.asset_sha256,
                lifecycle_state=candidate.lifecycle_state.value,
                slot_status=slot.status.value,
                audit_count=len(candidate_audits),
                ai_audit_count=sum(item.auditor_kind.value == "AI" for item in candidate_audits),
                human_audit_count=sum(item.auditor_kind.value == "HUMAN" for item in candidate_audits),
                critical_violation=any(item.critical_violation for item in candidate_audits),
                failure_codes=failures,
                latest_dimension_scores=latest_scores,
                human_decision=None if decision is None else decision.value,
                regeneration_requested=decision is HumanCandidateDecision.NEEDS_REGENERATION,
                available_human_actions=actions,
            ))
        body: dict[str, Any] = {
            "projection_version": "1.0.0",
            "task_owner": "TASK-038",
            "scene_filter": scene_id,
            "candidates": [row.to_dict() for row in rows],
            "human_final_authority_preserved": True,
            "automatic_regeneration_started": False,
            "physical_delete_requested": False,
        }
        body["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(slots=True)
class _DecisionConfirmation:
    confirmation_id: str
    candidate_id: str
    asset_sha256: str
    audit_refs: tuple[str, ...]
    audit_set_sha256: str
    decision: HumanCandidateDecision
    consumed: bool = False


class Task038AuditWorkspaceService:
    """Human decision boundary with exact Candidate/Audit confirmation binding."""

    def __init__(
        self,
        *,
        production: ProductionControlRegistry,
        audits: CandidateAuditRegistry,
        token_factory: TokenFactory | None = None,
    ) -> None:
        self.production = production
        self.audits = audits
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._confirmations: dict[str, _DecisionConfirmation] = {}

    def snapshot(self, *, scene_id: str | None = None) -> dict[str, Any]:
        return Task038AuditWorkspaceProjection.build(
            production=self.production,
            audits=self.audits,
            scene_id=scene_id,
        )

    def _candidate_audit_refs(self, candidate_id: str) -> tuple[str, ...]:
        return tuple(sorted(
            item.audit_id for item in self.audits.audit_records.values()
            if item.candidate_id == candidate_id
        ))

    @staticmethod
    def _audit_set_hash(audits: CandidateAuditRegistry, refs: tuple[str, ...]) -> str:
        return sha256_bytes(canonical_json_bytes([
            audits.audit_records[ref].to_dict()["record_sha256"] for ref in refs
        ]))

    def prepare_human_decision(self, *, candidate_id: str, decision: str) -> dict[str, Any]:
        try:
            decision_kind = HumanCandidateDecision(decision)
        except ValueError as exc:
            raise ProductError(
                "ERR_AUDIT_WORKSPACE_DECISION_INVALID",
                "Unknown Human Candidate decision",
                ProductErrorCategory.VALIDATION,
            ) from exc
        candidate = self.production.candidates.get(candidate_id)
        if candidate is None:
            raise ProductError(
                "ERR_AUDIT_PRODUCTION_CANDIDATE_NOT_FOUND",
                "Audit candidate does not exist in Production Control",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if candidate.lifecycle_state is not CandidateLifecycle.READY_FOR_AUDIT:
            raise ProductError(
                "ERR_AUDIT_WORKSPACE_CANDIDATE_NOT_READY",
                "Human decision confirmation requires READY_FOR_AUDIT Candidate",
                ProductErrorCategory.STATE,
                details={"lifecycle_state": candidate.lifecycle_state.value},
            )
        if any(item.candidate_id == candidate_id for item in self.audits.decisions.values()):
            raise ProductError(
                "ERR_AUDIT_PRODUCTION_DECISION_ALREADY_RECORDED",
                "Candidate already has a Human lifecycle decision",
                ProductErrorCategory.STATE,
            )
        refs = self._candidate_audit_refs(candidate_id)
        if not refs:
            raise ProductError(
                "ERR_AUDIT_WORKSPACE_AUDIT_REQUIRED",
                "Human Candidate decision requires at least one immutable Audit",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        for ref in refs:
            if self.audits.audit_records[ref].asset_sha256 != candidate.asset_sha256:
                raise ProductError(
                    "ERR_AUDIT_WORKSPACE_ASSET_HASH_MISMATCH",
                    "Human decision cannot be prepared against stale/different Candidate bytes",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
        token = self._token_factory()
        if not isinstance(token, str) or not token.strip() or token in self._confirmations:
            raise ProductError(
                "ERR_AUDIT_WORKSPACE_CONFIRMATION_TOKEN_INVALID",
                "Audit confirmation token factory returned an invalid token",
                ProductErrorCategory.INTERNAL,
            )
        audit_hash = self._audit_set_hash(self.audits, refs)
        self._confirmations[token] = _DecisionConfirmation(
            token, candidate_id, candidate.asset_sha256, refs, audit_hash, decision_kind
        )
        return {
            "confirmation_version": "1.0.0",
            "task_owner": "TASK-038",
            "confirmation_id": token,
            "candidate_id": candidate_id,
            "asset_sha256": candidate.asset_sha256,
            "audit_refs": list(refs),
            "audit_set_sha256": audit_hash,
            "decision": decision_kind.value,
            "critical_violation_present": any(self.audits.audit_records[ref].critical_violation for ref in refs),
            "human_final_authority_required": True,
            "automatic_regeneration_started": False,
            "physical_delete_requested": False,
        }

    def apply_human_decision(
        self,
        *,
        confirmation_id: str,
        actor_id: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        pending = self._confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError(
                "ERR_AUDIT_WORKSPACE_CONFIRMATION_INVALID",
                "Audit Human decision confirmation is missing or already used",
                ProductErrorCategory.AUTHORIZATION,
            )
        candidate = self.production.candidates.get(pending.candidate_id)
        refs = self._candidate_audit_refs(pending.candidate_id)
        if (
            candidate is None
            or candidate.lifecycle_state is not CandidateLifecycle.READY_FOR_AUDIT
            or candidate.asset_sha256 != pending.asset_sha256
            or refs != pending.audit_refs
            or self._audit_set_hash(self.audits, refs) != pending.audit_set_sha256
        ):
            raise ProductError(
                "ERR_AUDIT_WORKSPACE_CONFIRMATION_STALE",
                "Candidate or Audit state changed after Human confirmation was prepared",
                ProductErrorCategory.AUTHORIZATION,
            )
        pending.consumed = True
        seed = hashlib.sha256(confirmation_id.encode("utf-8")).hexdigest()[:24]
        decision = HumanDecision(
            decision_id=f"decision-{seed}",
            candidate_id=pending.candidate_id,
            audit_refs=pending.audit_refs,
            decision=pending.decision,
            actor_id=actor_id,
            notes=notes,
        )
        result = AuditProductionControlBinding.apply_human_decision(
            self.production,
            self.audits,
            decision,
        )
        return {
            "decision": decision.to_dict(),
            "production_binding": result.to_dict(),
            "workspace": self.snapshot(),
        }
