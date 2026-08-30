"""TASK-019 R1 no-effect bridge to TASK-029 Owner Decision history.

The bridge binds each proposed profile-weight adjustment to a distinct explicit
Owner decision.  It does not load a store, write a profile, promote knowledge,
or execute rollback.  Downstream consumers must revalidate the exact latest
encrypted history coordinates before presenting or applying any proposal.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Iterable, Mapping

from .owner_decision_store import HumanDecision, OwnerDecisionEntry, OwnerDecisionHistory
from .profile_tuning import (
    ProfileTuningProposal, TuningProposalState, verify_profile_tuning_proposal_hash,
)
from .serialization import canonical_json_bytes, sha256_bytes


_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_STABLE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_MAX_SELECTIONS = 16
_MAX_DECISIONS_PER_SELECTION = 32


def _stable_id(value: object, field: str) -> str:
    if not isinstance(value, str) or not _STABLE_ID_RE.fullmatch(value):
        raise ValueError(f"{field} is invalid")
    return value


def _sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field} must be sha256:<64 lowercase hex>")
    return value


def _bounded_int(value: object, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{field} must be an integer in {minimum}..{maximum}")
    return value


class OwnerDecisionBindingState(str, Enum):
    READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
    PROFILE_PROPOSAL_NOT_READY = "PROFILE_PROPOSAL_NOT_READY"
    REJECTED_OWNER_DECISION_PRESENT = "REJECTED_OWNER_DECISION_PRESENT"


@dataclass(frozen=True, slots=True, order=True)
class AdjustmentDecisionSelection:
    feature_key: str
    decision_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _stable_id(self.feature_key, "feature_key")
        if not 1 <= len(self.decision_ids) <= _MAX_DECISIONS_PER_SELECTION:
            raise ValueError("decision_ids must contain 1..32 values")
        if self.decision_ids != tuple(sorted(set(self.decision_ids))):
            raise ValueError("decision_ids must be unique and canonically sorted")
        for decision_id in self.decision_ids:
            _stable_id(decision_id, "decision_id")


@dataclass(frozen=True, slots=True, order=True)
class OwnerDecisionReference:
    decision_id: str
    entry_sha256: str
    candidate_sha256: str
    hypothesis_id: str
    action_type: str
    decision: HumanDecision
    decided_at_epoch_ms: int

    def __post_init__(self) -> None:
        _stable_id(self.decision_id, "decision_id")
        _sha256(self.entry_sha256, "entry_sha256")
        _sha256(self.candidate_sha256, "candidate_sha256")
        _stable_id(self.hypothesis_id, "hypothesis_id")
        _stable_id(self.action_type, "action_type")
        if not isinstance(self.decision, HumanDecision):
            raise ValueError("decision must be a HumanDecision")
        _bounded_int(self.decided_at_epoch_ms, "decided_at_epoch_ms", 1, 9_999_999_999_999)

    @classmethod
    def from_entry(cls, entry: OwnerDecisionEntry) -> "OwnerDecisionReference":
        payload = entry.to_dict()
        candidate = payload["candidate"]
        return cls(
            decision_id=entry.decision_id,
            entry_sha256=payload["entry_sha256"],
            candidate_sha256=payload["candidate_sha256"],
            hypothesis_id=candidate["hypothesis_id"],
            action_type=candidate["action_type"],
            decision=entry.decision,
            decided_at_epoch_ms=entry.decided_at_epoch_ms,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "entry_sha256": self.entry_sha256,
            "candidate_sha256": self.candidate_sha256,
            "hypothesis_id": self.hypothesis_id,
            "action_type": self.action_type,
            "decision": self.decision.value,
            "decided_at_epoch_ms": self.decided_at_epoch_ms,
        }


@dataclass(frozen=True, slots=True, order=True)
class AdjustmentOwnerDecisionSupport:
    feature_key: str
    decisions: tuple[OwnerDecisionReference, ...]

    def __post_init__(self) -> None:
        _stable_id(self.feature_key, "feature_key")
        if not 1 <= len(self.decisions) <= _MAX_DECISIONS_PER_SELECTION:
            raise ValueError("decisions must contain 1..32 values")
        if not all(isinstance(row, OwnerDecisionReference) for row in self.decisions):
            raise ValueError("decisions must contain OwnerDecisionReference values")
        if self.decisions != tuple(sorted(self.decisions, key=lambda row: row.decision_id)):
            raise ValueError("decisions must be canonically sorted")
        if len({row.decision_id for row in self.decisions}) != len(self.decisions):
            raise ValueError("decision references must be unique")

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_key": self.feature_key,
            "owner_decisions": [row.to_dict() for row in self.decisions],
        }


@dataclass(frozen=True, slots=True)
class ProfileTuningOwnerDecisionBinding:
    proposal_sha256: str
    proposal_state: TuningProposalState
    owner_scope_sha256: str
    decision_store_id: str
    decision_history_revision: int
    decision_history_sha256: str
    baseline_profile_sha256: str
    proposed_profile_sha256: str
    rollback_profile_sha256: str
    supports: tuple[AdjustmentOwnerDecisionSupport, ...]
    state: OwnerDecisionBindingState

    def __post_init__(self) -> None:
        for field in (
            "proposal_sha256", "owner_scope_sha256", "decision_history_sha256",
            "baseline_profile_sha256", "proposed_profile_sha256", "rollback_profile_sha256",
        ):
            _sha256(getattr(self, field), field)
        if not isinstance(self.proposal_state, TuningProposalState):
            raise ValueError("proposal_state must be a TuningProposalState")
        _stable_id(self.decision_store_id, "decision_store_id")
        _bounded_int(self.decision_history_revision, "decision_history_revision", 1, 1_000_000_000)
        if not 2 <= len(self.supports) <= _MAX_SELECTIONS:
            raise ValueError("supports must contain 2..16 adjusted features")
        if not all(isinstance(row, AdjustmentOwnerDecisionSupport) for row in self.supports):
            raise ValueError("supports must contain AdjustmentOwnerDecisionSupport values")
        if self.supports != tuple(sorted(self.supports, key=lambda row: row.feature_key)):
            raise ValueError("supports must be canonically sorted")
        if len({row.feature_key for row in self.supports}) != len(self.supports):
            raise ValueError("support feature keys must be unique")
        decision_ids = [ref.decision_id for support in self.supports for ref in support.decisions]
        if len(decision_ids) != len(set(decision_ids)):
            raise ValueError("an Owner decision may support only one adjusted feature")
        expected = _classify(self.proposal_state, self.supports)
        if self.state is not expected:
            raise ValueError("binding state does not match proposal and Owner decisions")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "binding_version": "1.0.0",
            "record_type": "PROFILE_TUNING_OWNER_DECISION_BINDING",
            "task_owner": "TASK-019",
            "source_task": "TASK-029",
            "proposal_sha256": self.proposal_sha256,
            "proposal_state": self.proposal_state.value,
            "owner_scope_sha256": self.owner_scope_sha256,
            "decision_store_id": self.decision_store_id,
            "decision_history_revision": self.decision_history_revision,
            "decision_history_sha256": self.decision_history_sha256,
            "baseline_profile_sha256": self.baseline_profile_sha256,
            "proposed_profile_sha256": self.proposed_profile_sha256,
            "rollback_profile_sha256": self.rollback_profile_sha256,
            "adjustment_supports": [row.to_dict() for row in self.supports],
            "state": self.state.value,
            "latest_history_revalidation_required": True,
            "human_review_required": True,
            "profile_materialization_authorized": False,
            "automatic_profile_write_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "automatic_promotion_authorized": False,
            "rollback_execution_authorized": False,
            "edit_plan_mutation_authorized": False,
            "external_effect_authorized": False,
        }
        body["binding_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


def _classify(
    proposal_state: TuningProposalState,
    supports: tuple[AdjustmentOwnerDecisionSupport, ...],
) -> OwnerDecisionBindingState:
    if proposal_state is not TuningProposalState.READY_FOR_HUMAN_REVIEW:
        return OwnerDecisionBindingState.PROFILE_PROPOSAL_NOT_READY
    if any(
        ref.decision is HumanDecision.REJECTED
        for support in supports
        for ref in support.decisions
    ):
        return OwnerDecisionBindingState.REJECTED_OWNER_DECISION_PRESENT
    return OwnerDecisionBindingState.READY_FOR_HUMAN_REVIEW


def compile_profile_tuning_owner_decision_binding(
    proposal: ProfileTuningProposal,
    history: OwnerDecisionHistory,
    selections: Iterable[AdjustmentDecisionSelection],
) -> ProfileTuningOwnerDecisionBinding:
    """Bind exact proposal adjustments to distinct explicit Owner decisions."""

    if not isinstance(proposal, ProfileTuningProposal):
        raise ValueError("proposal must be a ProfileTuningProposal")
    if not isinstance(history, OwnerDecisionHistory):
        raise ValueError("history must be an OwnerDecisionHistory")
    supplied_selections = tuple(selections)
    if not all(isinstance(row, AdjustmentDecisionSelection) for row in supplied_selections):
        raise ValueError("selections must contain AdjustmentDecisionSelection values")
    selection_rows = tuple(sorted(supplied_selections, key=lambda row: row.feature_key))
    expected_keys = tuple(row.feature_key for row in proposal.adjustments)
    actual_keys = tuple(row.feature_key for row in selection_rows)
    if actual_keys != expected_keys:
        raise ValueError("selections must cover every adjusted feature exactly once")
    all_ids = [decision_id for row in selection_rows for decision_id in row.decision_ids]
    if len(all_ids) != len(set(all_ids)):
        raise ValueError("an Owner decision may be selected only once")
    proposal_payload = proposal.to_dict()
    verify_profile_tuning_proposal_hash(proposal_payload)
    verified_history = OwnerDecisionHistory.from_dict(history.to_dict())
    entry_by_id = {entry.decision_id: entry for entry in verified_history.entries}
    if missing := sorted(set(all_ids) - set(entry_by_id)):
        raise ValueError(f"selected Owner decisions are missing from history: {missing}")
    supports = tuple(
        AdjustmentOwnerDecisionSupport(
            selection.feature_key,
            tuple(OwnerDecisionReference.from_entry(entry_by_id[value]) for value in selection.decision_ids),
        )
        for selection in selection_rows
    )
    history_payload = verified_history.to_dict()
    state = _classify(proposal.state, supports)
    return ProfileTuningOwnerDecisionBinding(
        proposal_sha256=proposal_payload["proposal_sha256"],
        proposal_state=proposal.state,
        owner_scope_sha256=verified_history.owner_scope_sha256,
        decision_store_id=verified_history.store_id,
        decision_history_revision=verified_history.revision,
        decision_history_sha256=history_payload["history_sha256"],
        baseline_profile_sha256=proposal_payload["baseline_profile"]["profile_sha256"],
        proposed_profile_sha256=proposal_payload["proposed_profile"]["profile_sha256"],
        rollback_profile_sha256=proposal_payload["rollback_profile_sha256"],
        supports=supports,
        state=state,
    )


def verify_profile_tuning_owner_decision_binding(
    payload: Mapping[str, Any],
    proposal: ProfileTuningProposal,
    history: OwnerDecisionHistory,
    selections: Iterable[AdjustmentDecisionSelection],
) -> None:
    """Recompute a binding against its exact source proposal and history."""

    if not isinstance(payload, Mapping):
        raise ValueError("payload must be an object")
    expected = compile_profile_tuning_owner_decision_binding(
        proposal, history, selections
    ).to_dict()
    if dict(payload) != expected:
        raise ValueError("binding does not match its exact proposal and Owner Decision history")


__all__ = [
    "AdjustmentDecisionSelection",
    "AdjustmentOwnerDecisionSupport",
    "OwnerDecisionBindingState",
    "OwnerDecisionReference",
    "ProfileTuningOwnerDecisionBinding",
    "compile_profile_tuning_owner_decision_binding",
    "verify_profile_tuning_owner_decision_binding",
]
