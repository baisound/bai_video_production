"""TASK-029 R2 pure Owner Profile materialization candidate.

This module materializes only an in-memory, Human-review candidate from an
exact TASK-019 proposal/binding and the latest TASK-029 decision history.  It
does not expose a store, filesystem, registry, promotion, or rollback effect.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Iterable, Mapping

from .multimodal_scoring import ScoringProfile
from .owner_decision_store import OwnerDecisionHistory
from .profile_tuning import ProfileTuningProposal
from .profile_tuning_owner_decision import (
    AdjustmentDecisionSelection,
    OwnerDecisionBindingState,
    ProfileTuningOwnerDecisionBinding,
    verify_profile_tuning_owner_decision_binding,
)
from .serialization import canonical_json_bytes, sha256_bytes


_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_STABLE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


def _sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field} must be sha256:<64 lowercase hex>")
    return value


def _stable_id(value: object, field: str) -> str:
    if not isinstance(value, str) or not _STABLE_ID_RE.fullmatch(value):
        raise ValueError(f"{field} is invalid")
    return value


class OwnerProfileMaterializationState(str, Enum):
    READY_FOR_HUMAN_MATERIALIZATION = "READY_FOR_HUMAN_MATERIALIZATION"
    PROFILE_PROPOSAL_NOT_READY = "PROFILE_PROPOSAL_NOT_READY"
    REJECTED_OWNER_DECISION_PRESENT = "REJECTED_OWNER_DECISION_PRESENT"


@dataclass(frozen=True, slots=True)
class OwnerProfileMaterializationCandidate:
    candidate_id: str
    owner_scope_sha256: str
    decision_store_id: str
    decision_history_revision: int
    decision_history_sha256: str
    proposal_sha256: str
    binding_sha256: str
    baseline_profile_sha256: str
    proposed_profile_sha256: str
    rollback_profile_sha256: str
    source_decision_ids: tuple[str, ...]
    profile_snapshot: ScoringProfile | None
    state: OwnerProfileMaterializationState

    def __post_init__(self) -> None:
        _stable_id(self.candidate_id, "candidate_id")
        _stable_id(self.decision_store_id, "decision_store_id")
        for field in (
            "owner_scope_sha256", "decision_history_sha256", "proposal_sha256",
            "binding_sha256", "baseline_profile_sha256", "proposed_profile_sha256",
            "rollback_profile_sha256",
        ):
            _sha256(getattr(self, field), field)
        if (
            isinstance(self.decision_history_revision, bool)
            or not isinstance(self.decision_history_revision, int)
            or self.decision_history_revision < 1
        ):
            raise ValueError("decision_history_revision must be an integer >= 1")
        if not self.source_decision_ids or self.source_decision_ids != tuple(
            sorted(set(self.source_decision_ids))
        ):
            raise ValueError("source_decision_ids must be non-empty, unique, and sorted")
        if len(self.source_decision_ids) > 512:
            raise ValueError("source_decision_ids exceeds the bounded candidate limit")
        for value in self.source_decision_ids:
            _stable_id(value, "source_decision_id")
        if self.baseline_profile_sha256 == self.proposed_profile_sha256:
            raise ValueError("proposed profile must differ from the baseline profile")
        if self.rollback_profile_sha256 != self.baseline_profile_sha256:
            raise ValueError("rollback profile must match the baseline profile")
        if not isinstance(self.state, OwnerProfileMaterializationState):
            raise ValueError("state must be an OwnerProfileMaterializationState")
        if self.state is OwnerProfileMaterializationState.READY_FOR_HUMAN_MATERIALIZATION:
            if not isinstance(self.profile_snapshot, ScoringProfile):
                raise ValueError("ready candidate requires a profile_snapshot")
            if self.profile_snapshot.to_dict()["profile_sha256"] != self.proposed_profile_sha256:
                raise ValueError("profile_snapshot must equal the exact proposed profile")
        elif self.profile_snapshot is not None:
            raise ValueError("non-ready candidate must not expose a profile_snapshot")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "materialization_version": "1.0.0",
            "record_type": "OWNER_PROFILE_MATERIALIZATION_CANDIDATE",
            "task_owner": "TASK-029",
            "source_task": "TASK-019",
            "candidate_id": self.candidate_id,
            "owner_scope_sha256": self.owner_scope_sha256,
            "decision_store_id": self.decision_store_id,
            "decision_history_revision": self.decision_history_revision,
            "decision_history_sha256": self.decision_history_sha256,
            "proposal_sha256": self.proposal_sha256,
            "binding_sha256": self.binding_sha256,
            "baseline_profile_sha256": self.baseline_profile_sha256,
            "proposed_profile_sha256": self.proposed_profile_sha256,
            "rollback_profile_sha256": self.rollback_profile_sha256,
            "source_decision_ids": list(self.source_decision_ids),
            "profile_snapshot": None if self.profile_snapshot is None else self.profile_snapshot.to_dict(),
            "state": self.state.value,
            "latest_history_revalidation_required": True,
            "human_materialization_confirmation_required": True,
            "in_memory_candidate_only": True,
            "owner_profile_store_write_authorized": False,
            "model_profile_registry_write_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "automatic_promotion_authorized": False,
            "rollback_execution_authorized": False,
            "edit_plan_mutation_authorized": False,
            "external_effect_authorized": False,
        }
        body["materialization_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


def _state(binding_state: OwnerDecisionBindingState) -> OwnerProfileMaterializationState:
    if binding_state is OwnerDecisionBindingState.READY_FOR_HUMAN_REVIEW:
        return OwnerProfileMaterializationState.READY_FOR_HUMAN_MATERIALIZATION
    if binding_state is OwnerDecisionBindingState.PROFILE_PROPOSAL_NOT_READY:
        return OwnerProfileMaterializationState.PROFILE_PROPOSAL_NOT_READY
    return OwnerProfileMaterializationState.REJECTED_OWNER_DECISION_PRESENT


def compile_owner_profile_materialization_candidate(
    candidate_id: str,
    proposal: ProfileTuningProposal,
    binding: ProfileTuningOwnerDecisionBinding,
    history: OwnerDecisionHistory,
    selections: Iterable[AdjustmentDecisionSelection],
) -> OwnerProfileMaterializationCandidate:
    """Revalidate exact sources and compile a no-write Owner Profile candidate."""

    if not isinstance(proposal, ProfileTuningProposal):
        raise ValueError("proposal must be a ProfileTuningProposal")
    if not isinstance(binding, ProfileTuningOwnerDecisionBinding):
        raise ValueError("binding must be a ProfileTuningOwnerDecisionBinding")
    if not isinstance(history, OwnerDecisionHistory):
        raise ValueError("history must be an OwnerDecisionHistory")
    selection_rows = tuple(selections)
    verified_history = OwnerDecisionHistory.from_dict(history.to_dict())
    verify_profile_tuning_owner_decision_binding(
        binding.to_dict(), proposal, verified_history, selection_rows
    )
    proposal_payload = proposal.to_dict()
    binding_payload = binding.to_dict()
    history_payload = verified_history.to_dict()
    decision_ids = tuple(sorted(
        ref.decision_id for support in binding.supports for ref in support.decisions
    ))
    state = _state(binding.state)
    return OwnerProfileMaterializationCandidate(
        candidate_id=candidate_id,
        owner_scope_sha256=binding.owner_scope_sha256,
        decision_store_id=binding.decision_store_id,
        decision_history_revision=binding.decision_history_revision,
        decision_history_sha256=history_payload["history_sha256"],
        proposal_sha256=proposal_payload["proposal_sha256"],
        binding_sha256=binding_payload["binding_sha256"],
        baseline_profile_sha256=binding.baseline_profile_sha256,
        proposed_profile_sha256=binding.proposed_profile_sha256,
        rollback_profile_sha256=binding.rollback_profile_sha256,
        source_decision_ids=decision_ids,
        profile_snapshot=(
            proposal.proposed_profile
            if state is OwnerProfileMaterializationState.READY_FOR_HUMAN_MATERIALIZATION
            else None
        ),
        state=state,
    )


def verify_owner_profile_materialization_candidate(
    payload: Mapping[str, Any],
    candidate_id: str,
    proposal: ProfileTuningProposal,
    binding: ProfileTuningOwnerDecisionBinding,
    history: OwnerDecisionHistory,
    selections: Iterable[AdjustmentDecisionSelection],
) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be an object")
    expected = compile_owner_profile_materialization_candidate(
        candidate_id, proposal, binding, history, selections
    ).to_dict()
    if dict(payload) != expected:
        raise ValueError("materialization candidate does not match its exact sources")


__all__ = [
    "OwnerProfileMaterializationCandidate",
    "OwnerProfileMaterializationState",
    "compile_owner_profile_materialization_candidate",
    "verify_owner_profile_materialization_candidate",
]
