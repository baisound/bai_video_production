"""R2 Production Control traceability across TASK-027/037/038.

The service proves the relationship path required by PRODUCT-CONTROL-001:
Plan -> Scene -> Slot -> Candidate -> Audit -> Human Decision -> Locked Asset.
It is read-only and never repairs missing links silently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .candidate_audit import CandidateAuditRegistry, HumanCandidateDecision
from .errors import ProductError, ProductErrorCategory
from .production_control import (
    CandidateLifecycle,
    EntityRef,
    EntityType,
    ProductionControlRegistry,
    SlotStatus,
)
from .serialization import canonical_json_bytes, sha256_bytes


@dataclass(frozen=True, slots=True)
class LockedProductionTrace:
    plan_id: str
    scene_id: str
    slot_id: str
    candidate_id: str
    asset_id: str
    asset_sha256: str
    audit_ids: tuple[str, ...]
    human_decision_id: str

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "trace_version": "1.0.0",
            "task_owner": "TASK-027/TASK-037/TASK-038",
            "plan_id": self.plan_id,
            "scene_id": self.scene_id,
            "slot_id": self.slot_id,
            "candidate_id": self.candidate_id,
            "asset_id": self.asset_id,
            "asset_sha256": self.asset_sha256,
            "audit_ids": list(self.audit_ids),
            "human_decision_id": self.human_decision_id,
            "human_decision": "ACCEPT",
            "slot_locked": True,
            "candidate_locked": True,
            "physical_delete_performed": False,
            "automatic_regeneration_started": False,
            "human_final_authority_preserved": True,
        }
        body["trace_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class ProductionTraceService:
    @staticmethod
    def _has_edge(production: ProductionControlRegistry, from_ref: EntityRef, to_ref: EntityRef) -> bool:
        return any(edge.from_ref == from_ref and edge.to_ref == to_ref for edge in production.edges.values())

    @classmethod
    def locked_asset_trace(
        cls,
        *,
        plan_id: str,
        slot_id: str,
        production: ProductionControlRegistry,
        audits: CandidateAuditRegistry,
    ) -> LockedProductionTrace:
        slot = production.slots.get(slot_id)
        if slot is None:
            raise ProductError("ERR_PRODUCTION_TRACE_SLOT_NOT_FOUND", "Trace Slot does not exist", ProductErrorCategory.STATE)
        if slot.status is not SlotStatus.LOCKED or slot.locked_candidate_id is None:
            raise ProductError("ERR_PRODUCTION_TRACE_SLOT_NOT_LOCKED", "Trace requires a locked Slot", ProductErrorCategory.STATE)
        candidate = production.candidates.get(slot.locked_candidate_id)
        if candidate is None or candidate.slot_id != slot.slot_id or candidate.lifecycle_state is not CandidateLifecycle.LOCKED:
            raise ProductError(
                "ERR_PRODUCTION_TRACE_LOCK_INCONSISTENT",
                "Locked Slot/Candidate state is inconsistent",
                ProductErrorCategory.DATA_INTEGRITY,
            )

        plan_ref = EntityRef(EntityType.PLAN, plan_id)
        scene_ref = EntityRef(EntityType.SCENE, slot.scene_id)
        slot_ref = EntityRef(EntityType.SLOT, slot.slot_id)
        candidate_ref = EntityRef(EntityType.CANDIDATE, candidate.candidate_id)
        if not cls._has_edge(production, plan_ref, scene_ref):
            raise ProductError("ERR_PRODUCTION_TRACE_PLAN_SCENE_MISSING", "Plan -> Scene trace edge is missing", ProductErrorCategory.DATA_INTEGRITY)
        if not cls._has_edge(production, scene_ref, slot_ref):
            raise ProductError("ERR_PRODUCTION_TRACE_SCENE_SLOT_MISSING", "Scene -> Slot trace edge is missing", ProductErrorCategory.DATA_INTEGRITY)
        if not cls._has_edge(production, slot_ref, candidate_ref):
            raise ProductError("ERR_PRODUCTION_TRACE_SLOT_CANDIDATE_MISSING", "Slot -> Candidate trace edge is missing", ProductErrorCategory.DATA_INTEGRITY)

        candidate_audits = sorted(
            (
                record for record in audits.audit_records.values()
                if record.candidate_id == candidate.candidate_id and record.asset_sha256 == candidate.asset_sha256
            ),
            key=lambda item: item.audit_id,
        )
        if not candidate_audits:
            raise ProductError("ERR_PRODUCTION_TRACE_AUDIT_MISSING", "Locked Candidate has no exact Asset audit Evidence", ProductErrorCategory.DATA_INTEGRITY)
        audit_ids = {item.audit_id for item in candidate_audits}

        accepted = [
            decision for decision in audits.decisions.values()
            if decision.candidate_id == candidate.candidate_id and decision.decision is HumanCandidateDecision.ACCEPT
        ]
        if len(accepted) != 1:
            raise ProductError(
                "ERR_PRODUCTION_TRACE_HUMAN_ACCEPT_INVALID",
                "Locked Candidate must have exactly one Human ACCEPT decision",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"accept_decision_count": len(accepted)},
            )
        human = accepted[0]
        if not set(human.audit_refs).issubset(audit_ids):
            raise ProductError(
                "ERR_PRODUCTION_TRACE_DECISION_AUDIT_MISMATCH",
                "Human ACCEPT references audit Evidence not bound to the locked Asset bytes",
                ProductErrorCategory.DATA_INTEGRITY,
            )

        return LockedProductionTrace(
            plan_id=plan_id,
            scene_id=slot.scene_id,
            slot_id=slot.slot_id,
            candidate_id=candidate.candidate_id,
            asset_id=candidate.asset_id,
            asset_sha256=candidate.asset_sha256,
            audit_ids=tuple(item.audit_id for item in candidate_audits),
            human_decision_id=human.decision_id,
        )
