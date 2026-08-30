"""TASK-029 R4 pure Model/Profile Registry admission candidate.

The latest encrypted Owner Profile history is revalidated and projected into an
in-memory candidate for separate Human registry review.  This module performs
no filesystem, registry, runtime-profile, promotion, rollback, or external
effect.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Mapping

from .multimodal_scoring import (
    FeatureModality,
    FeaturePolarity,
    FeatureRule,
    FeatureSourceSelector,
    ScoringProfile,
)
from .owner_profile_store import OwnerProfileHistory
from .serialization import canonical_json_bytes, sha256_bytes


REGISTRY_CANDIDATE_VERSION = "1.0.0"
SCORING_PROFILE_COMPATIBILITY_CONTRACT = "TASK-008/SCORING_PROFILE/1.0.0"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_STABLE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


def _sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{field} must be sha256:<64 lowercase hex>")
    return value


def _stable_id(value: object, field: str) -> str:
    if not isinstance(value, str) or _STABLE_ID_RE.fullmatch(value) is None:
        raise ValueError(f"{field} is invalid")
    return value


def _positive_int(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{field} must be an integer >= 1")
    return value


def _profile_from_payload(value: Mapping[str, Any]) -> ScoringProfile:
    if set(value) != {"profile_id", "profile_version", "rules", "profile_sha256"}:
        raise ValueError("profile snapshot fields are incomplete or unknown")
    rows = value.get("rules")
    if not isinstance(rows, list):
        raise ValueError("profile rules must be an array")
    rules: list[FeatureRule] = []
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {
            "feature_key", "modality", "weight_milli", "raw_range", "polarity",
            "required", "optional_missing_value_milli", "allowed_sources",
        }:
            raise ValueError("profile rule fields are incomplete or unknown")
        raw_range = row.get("raw_range")
        sources = row.get("allowed_sources")
        if not isinstance(raw_range, Mapping) or set(raw_range) != {"minimum", "maximum"}:
            raise ValueError("profile raw_range is invalid")
        if not isinstance(sources, list):
            raise ValueError("profile allowed_sources must be an array")
        selectors: list[FeatureSourceSelector] = []
        for source in sources:
            if not isinstance(source, Mapping) or set(source) != {
                "producer_task_id", "contract_id"
            }:
                raise ValueError("profile source selector is invalid")
            selectors.append(FeatureSourceSelector(
                source["producer_task_id"], source["contract_id"]
            ))
        rules.append(FeatureRule(
            feature_key=row["feature_key"],
            modality=FeatureModality(row["modality"]),
            weight_milli=row["weight_milli"],
            raw_minimum=raw_range["minimum"],
            raw_maximum=raw_range["maximum"],
            polarity=FeaturePolarity(row["polarity"]),
            required=row["required"],
            optional_missing_value_milli=row["optional_missing_value_milli"],
            allowed_sources=tuple(selectors),
        ))
    profile = ScoringProfile(value["profile_id"], value["profile_version"], tuple(rules))
    if profile.to_dict() != dict(value):
        raise ValueError("profile snapshot hash or semantic fields mismatch")
    return profile


class OwnerProfileRegistryCandidateState(str, Enum):
    READY_FOR_HUMAN_REGISTRY_REVIEW = "READY_FOR_HUMAN_REGISTRY_REVIEW"


@dataclass(frozen=True, slots=True)
class OwnerProfileRegistryCandidate:
    registry_candidate_id: str
    owner_scope_sha256: str
    source_store_id: str
    source_history_revision: int
    source_history_sha256: str
    source_profile_revision_sha256: str
    source_materialization_sha256: str
    source_confirmation_sha256: str
    source_proposal_sha256: str
    source_binding_sha256: str
    source_decision_history_sha256: str
    source_decision_ids: tuple[str, ...]
    baseline_profile_sha256: str
    rollback_profile_sha256: str
    profile_snapshot: ScoringProfile
    state: OwnerProfileRegistryCandidateState

    def __post_init__(self) -> None:
        _stable_id(self.registry_candidate_id, "registry_candidate_id")
        _stable_id(self.source_store_id, "source_store_id")
        _positive_int(self.source_history_revision, "source_history_revision")
        for field in (
            "owner_scope_sha256", "source_history_sha256",
            "source_profile_revision_sha256", "source_materialization_sha256",
            "source_confirmation_sha256", "source_proposal_sha256",
            "source_binding_sha256", "source_decision_history_sha256",
            "baseline_profile_sha256", "rollback_profile_sha256",
        ):
            _sha256(getattr(self, field), field)
        if not self.source_decision_ids or self.source_decision_ids != tuple(
            sorted(set(self.source_decision_ids))
        ):
            raise ValueError("source_decision_ids must be non-empty, unique, and sorted")
        if len(self.source_decision_ids) > 512:
            raise ValueError("source_decision_ids exceeds the bounded candidate limit")
        for decision_id in self.source_decision_ids:
            _stable_id(decision_id, "source_decision_id")
        if self.rollback_profile_sha256 != self.baseline_profile_sha256:
            raise ValueError("rollback profile must equal the exact baseline profile")
        if not isinstance(self.profile_snapshot, ScoringProfile):
            raise ValueError("profile_snapshot must be a ScoringProfile")
        if self.profile_snapshot.to_dict()["profile_sha256"] == self.baseline_profile_sha256:
            raise ValueError("registry candidate profile must differ from its baseline")
        if not isinstance(self.state, OwnerProfileRegistryCandidateState):
            raise ValueError("state must be an OwnerProfileRegistryCandidateState")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "registry_candidate_version": REGISTRY_CANDIDATE_VERSION,
            "record_type": "OWNER_PROFILE_REGISTRY_CANDIDATE",
            "task_owner": "TASK-029",
            "registry_candidate_id": self.registry_candidate_id,
            "owner_scope_sha256": self.owner_scope_sha256,
            "source_store_id": self.source_store_id,
            "source_history_revision": self.source_history_revision,
            "source_history_sha256": self.source_history_sha256,
            "source_profile_revision_sha256": self.source_profile_revision_sha256,
            "source_materialization_sha256": self.source_materialization_sha256,
            "source_confirmation_sha256": self.source_confirmation_sha256,
            "source_proposal_sha256": self.source_proposal_sha256,
            "source_binding_sha256": self.source_binding_sha256,
            "source_decision_history_sha256": self.source_decision_history_sha256,
            "source_decision_ids": list(self.source_decision_ids),
            "baseline_profile_sha256": self.baseline_profile_sha256,
            "rollback_profile_sha256": self.rollback_profile_sha256,
            "profile_snapshot": self.profile_snapshot.to_dict(),
            "compatibility_contract": SCORING_PROFILE_COMPATIBILITY_CONTRACT,
            "state": self.state.value,
            "owner_local_profile_only": True,
            "latest_owner_profile_history_revalidation_required": True,
            "explicit_human_registry_confirmation_required": True,
            "in_memory_candidate_only": True,
            "model_profile_registry_write_authorized": False,
            "runtime_profile_apply_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "automatic_promotion_authorized": False,
            "rollback_execution_authorized": False,
            "edit_plan_mutation_authorized": False,
            "external_effect_authorized": False,
        }
        body["registry_candidate_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OwnerProfileRegistryCandidate":
        expected = {
            "registry_candidate_version", "record_type", "task_owner",
            "registry_candidate_id", "owner_scope_sha256", "source_store_id",
            "source_history_revision", "source_history_sha256",
            "source_profile_revision_sha256", "source_materialization_sha256",
            "source_confirmation_sha256", "source_proposal_sha256",
            "source_binding_sha256", "source_decision_history_sha256",
            "source_decision_ids", "baseline_profile_sha256",
            "rollback_profile_sha256", "profile_snapshot",
            "compatibility_contract", "state", "owner_local_profile_only",
            "latest_owner_profile_history_revalidation_required",
            "explicit_human_registry_confirmation_required",
            "in_memory_candidate_only", "model_profile_registry_write_authorized",
            "runtime_profile_apply_authorized", "knowledge_pack_promotion_authorized",
            "automatic_promotion_authorized", "rollback_execution_authorized",
            "edit_plan_mutation_authorized", "external_effect_authorized",
            "registry_candidate_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("registry candidate fields are incomplete or unknown")
        if (
            value["registry_candidate_version"] != REGISTRY_CANDIDATE_VERSION
            or value["record_type"] != "OWNER_PROFILE_REGISTRY_CANDIDATE"
            or value["task_owner"] != "TASK-029"
            or value["compatibility_contract"] != SCORING_PROFILE_COMPATIBILITY_CONTRACT
            or value["state"]
            != OwnerProfileRegistryCandidateState.READY_FOR_HUMAN_REGISTRY_REVIEW.value
        ):
            raise ValueError("registry candidate identity mismatch")
        for field in (
            "owner_local_profile_only",
            "latest_owner_profile_history_revalidation_required",
            "explicit_human_registry_confirmation_required",
            "in_memory_candidate_only",
        ):
            if value[field] is not True:
                raise ValueError(f"{field} must remain true")
        for field in (
            "model_profile_registry_write_authorized",
            "runtime_profile_apply_authorized",
            "knowledge_pack_promotion_authorized", "automatic_promotion_authorized",
            "rollback_execution_authorized", "edit_plan_mutation_authorized",
            "external_effect_authorized",
        ):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        profile = _profile_from_payload(value["profile_snapshot"])
        result = cls(
            value["registry_candidate_id"], value["owner_scope_sha256"],
            value["source_store_id"], value["source_history_revision"],
            value["source_history_sha256"], value["source_profile_revision_sha256"],
            value["source_materialization_sha256"], value["source_confirmation_sha256"],
            value["source_proposal_sha256"], value["source_binding_sha256"],
            value["source_decision_history_sha256"], tuple(value["source_decision_ids"]),
            value["baseline_profile_sha256"], value["rollback_profile_sha256"], profile,
            OwnerProfileRegistryCandidateState(value["state"]),
        )
        if result.to_dict() != dict(value):
            raise ValueError("registry candidate hash or derived fields mismatch")
        return result


def compile_owner_profile_registry_candidate(
    registry_candidate_id: str,
    history: OwnerProfileHistory,
    *,
    expected_history_revision: int,
) -> OwnerProfileRegistryCandidate:
    """Compile a no-write candidate from the exact latest R3 Owner Profile."""

    _stable_id(registry_candidate_id, "registry_candidate_id")
    _positive_int(expected_history_revision, "expected_history_revision")
    if not isinstance(history, OwnerProfileHistory):
        raise ValueError("history must be an OwnerProfileHistory")
    verified = OwnerProfileHistory.from_dict(history.to_dict())
    if verified.revision == 0:
        raise ValueError("a materialized Owner Profile revision is required")
    if verified.revision != expected_history_revision:
        raise ValueError("Owner Profile history changed since registry candidate review")
    latest = verified.revisions[-1]
    revision_payload = latest.to_dict()
    candidate_payload = latest.candidate
    confirmation_payload = latest.confirmation.to_dict()
    snapshot = candidate_payload.get("profile_snapshot")
    if not isinstance(snapshot, Mapping):
        raise ValueError("latest Owner Profile revision has no profile snapshot")
    profile = _profile_from_payload(snapshot)
    if profile.to_dict()["profile_sha256"] != candidate_payload["proposed_profile_sha256"]:
        raise ValueError("latest Owner Profile hash does not match its profile snapshot")
    return OwnerProfileRegistryCandidate(
        registry_candidate_id=registry_candidate_id,
        owner_scope_sha256=verified.owner_scope_sha256,
        source_store_id=verified.store_id,
        source_history_revision=verified.revision,
        source_history_sha256=verified.to_dict()["history_sha256"],
        source_profile_revision_sha256=revision_payload["revision_sha256"],
        source_materialization_sha256=candidate_payload["materialization_sha256"],
        source_confirmation_sha256=confirmation_payload["confirmation_sha256"],
        source_proposal_sha256=candidate_payload["proposal_sha256"],
        source_binding_sha256=candidate_payload["binding_sha256"],
        source_decision_history_sha256=candidate_payload["decision_history_sha256"],
        source_decision_ids=tuple(candidate_payload["source_decision_ids"]),
        baseline_profile_sha256=candidate_payload["baseline_profile_sha256"],
        rollback_profile_sha256=candidate_payload["rollback_profile_sha256"],
        profile_snapshot=profile,
        state=OwnerProfileRegistryCandidateState.READY_FOR_HUMAN_REGISTRY_REVIEW,
    )


def verify_owner_profile_registry_candidate(
    payload: Mapping[str, Any],
    registry_candidate_id: str,
    history: OwnerProfileHistory,
    *,
    expected_history_revision: int,
) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be an object")
    expected = compile_owner_profile_registry_candidate(
        registry_candidate_id,
        history,
        expected_history_revision=expected_history_revision,
    ).to_dict()
    if dict(payload) != expected:
        raise ValueError("registry candidate does not match the exact latest Owner Profile")


__all__ = [
    "OwnerProfileRegistryCandidate",
    "OwnerProfileRegistryCandidateState",
    "REGISTRY_CANDIDATE_VERSION",
    "SCORING_PROFILE_COMPATIBILITY_CONTRACT",
    "compile_owner_profile_registry_candidate",
    "verify_owner_profile_registry_candidate",
]
