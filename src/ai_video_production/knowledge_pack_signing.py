"""TASK-029 R7 pure, unsigned Knowledge Pack review binding."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Iterable, Mapping

from .knowledge_pack_candidate import (
    KnowledgePackCandidatePolicy,
    KnowledgePackCandidateState,
    KnowledgePackPromotionCandidate,
    KnowledgePackSource,
    compile_knowledge_pack_promotion_candidate,
)
from .serialization import canonical_json_bytes, sha256_bytes


KNOWLEDGE_PACK_SIGNING_VERSION = "1.0.0"
KNOWLEDGE_PACK_COMPATIBILITY_CONTRACT = "TASK-029/KNOWLEDGE_PACK/1.0.0"
_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        raise ValueError(f"{field} must be sha256:<64 lowercase hex>")
    return value


def _id(value: object, field: str) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise ValueError(f"{field} is invalid")
    return value


def _reasons(value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError("reason_codes must be an array")
    result = tuple(value)
    if not 1 <= len(result) <= 8:
        raise ValueError("reason_codes must contain 1..8 values")
    for item in result:
        _id(item, "reason_code")
    if result != tuple(sorted(set(result))):
        raise ValueError("reason_codes must be unique and sorted")
    return result


def _epoch(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 9_999_999_999_999:
        raise ValueError("reviewed_at_epoch_ms is invalid")
    return value


class HumanKnowledgePackDecision(str, Enum):
    APPROVE_FOR_INDEPENDENT_CRITIC = "APPROVE_FOR_INDEPENDENT_CRITIC"
    REJECT = "REJECT"


class CriticKnowledgePackDecision(str, Enum):
    ACCEPT_FOR_EXTERNAL_SIGNATURE = "ACCEPT_FOR_EXTERNAL_SIGNATURE"
    REJECT = "REJECT"


class KnowledgePackSigningState(str, Enum):
    READY_FOR_EXTERNAL_SIGNATURE = "READY_FOR_EXTERNAL_SIGNATURE"
    HUMAN_REJECTED = "HUMAN_REJECTED"
    CRITIC_REJECTED = "CRITIC_REJECTED"


@dataclass(frozen=True, slots=True)
class HumanKnowledgePackReview:
    review_id: str
    source_candidate_id: str
    source_candidate_sha256: str
    reviewer_coordinate_sha256: str
    decision: HumanKnowledgePackDecision
    reason_codes: tuple[str, ...]
    reviewed_at_epoch_ms: int

    def __post_init__(self) -> None:
        _id(self.review_id, "review_id")
        _id(self.source_candidate_id, "source_candidate_id")
        _sha(self.source_candidate_sha256, "source_candidate_sha256")
        _sha(self.reviewer_coordinate_sha256, "reviewer_coordinate_sha256")
        if not isinstance(self.decision, HumanKnowledgePackDecision):
            raise ValueError("decision must be a HumanKnowledgePackDecision")
        _reasons(self.reason_codes)
        _epoch(self.reviewed_at_epoch_ms)

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "review_version": KNOWLEDGE_PACK_SIGNING_VERSION,
            "record_type": "HUMAN_KNOWLEDGE_PACK_REVIEW",
            "task_owner": "TASK-029",
            "review_id": self.review_id,
            "source_candidate_id": self.source_candidate_id,
            "source_candidate_sha256": self.source_candidate_sha256,
            "reviewer_coordinate_sha256": self.reviewer_coordinate_sha256,
            "decision": self.decision.value,
            "reason_codes": list(self.reason_codes),
            "reviewed_at_epoch_ms": self.reviewed_at_epoch_ms,
            "knowledge_pack_write_authorized": False,
            "signature_authorized": False,
            "release_authorized": False,
        }
        body["review_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "HumanKnowledgePackReview":
        expected = {
            "review_version", "record_type", "task_owner", "review_id",
            "source_candidate_id", "source_candidate_sha256", "reviewer_coordinate_sha256",
            "decision", "reason_codes", "reviewed_at_epoch_ms",
            "knowledge_pack_write_authorized", "signature_authorized",
            "release_authorized", "review_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("Human review fields are incomplete or unknown")
        if (value["review_version"], value["record_type"], value["task_owner"]) != (
            KNOWLEDGE_PACK_SIGNING_VERSION, "HUMAN_KNOWLEDGE_PACK_REVIEW", "TASK-029"
        ):
            raise ValueError("Human review identity mismatch")
        for field in ("knowledge_pack_write_authorized", "signature_authorized", "release_authorized"):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        result = cls(
            value["review_id"], value["source_candidate_id"], value["source_candidate_sha256"],
            value["reviewer_coordinate_sha256"], HumanKnowledgePackDecision(value["decision"]),
            _reasons(value["reason_codes"]), value["reviewed_at_epoch_ms"],
        )
        if result.to_dict() != dict(value):
            raise ValueError("Human review hash mismatch")
        return result


@dataclass(frozen=True, slots=True)
class IndependentKnowledgePackCriticReview:
    review_id: str
    source_candidate_id: str
    source_candidate_sha256: str
    reviewer_coordinate_sha256: str
    critic_report_sha256: str
    decision: CriticKnowledgePackDecision
    unresolved_critical_count: int
    unresolved_high_count: int
    reason_codes: tuple[str, ...]
    reviewed_at_epoch_ms: int

    def __post_init__(self) -> None:
        _id(self.review_id, "review_id")
        _id(self.source_candidate_id, "source_candidate_id")
        for field in ("source_candidate_sha256", "reviewer_coordinate_sha256", "critic_report_sha256"):
            _sha(getattr(self, field), field)
        if not isinstance(self.decision, CriticKnowledgePackDecision):
            raise ValueError("decision must be a CriticKnowledgePackDecision")
        for field in ("unresolved_critical_count", "unresolved_high_count"):
            value = getattr(self, field)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 1000:
                raise ValueError(f"{field} is invalid")
        _reasons(self.reason_codes)
        _epoch(self.reviewed_at_epoch_ms)
        if self.decision is CriticKnowledgePackDecision.ACCEPT_FOR_EXTERNAL_SIGNATURE and (
            self.unresolved_critical_count or self.unresolved_high_count
        ):
            raise ValueError("Critic acceptance requires zero unresolved Critical/High findings")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "review_version": KNOWLEDGE_PACK_SIGNING_VERSION,
            "record_type": "INDEPENDENT_KNOWLEDGE_PACK_CRITIC_REVIEW",
            "task_owner": "TASK-029",
            "review_id": self.review_id,
            "source_candidate_id": self.source_candidate_id,
            "source_candidate_sha256": self.source_candidate_sha256,
            "reviewer_coordinate_sha256": self.reviewer_coordinate_sha256,
            "critic_report_sha256": self.critic_report_sha256,
            "decision": self.decision.value,
            "unresolved_critical_count": self.unresolved_critical_count,
            "unresolved_high_count": self.unresolved_high_count,
            "reason_codes": list(self.reason_codes),
            "reviewed_at_epoch_ms": self.reviewed_at_epoch_ms,
            "knowledge_pack_write_authorized": False,
            "signature_authorized": False,
            "release_authorized": False,
        }
        body["review_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "IndependentKnowledgePackCriticReview":
        expected = {
            "review_version", "record_type", "task_owner", "review_id",
            "source_candidate_id", "source_candidate_sha256", "reviewer_coordinate_sha256",
            "critic_report_sha256", "decision", "unresolved_critical_count",
            "unresolved_high_count", "reason_codes", "reviewed_at_epoch_ms",
            "knowledge_pack_write_authorized", "signature_authorized",
            "release_authorized", "review_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("Critic review fields are incomplete or unknown")
        if (value["review_version"], value["record_type"], value["task_owner"]) != (
            KNOWLEDGE_PACK_SIGNING_VERSION, "INDEPENDENT_KNOWLEDGE_PACK_CRITIC_REVIEW", "TASK-029"
        ):
            raise ValueError("Critic review identity mismatch")
        for field in ("knowledge_pack_write_authorized", "signature_authorized", "release_authorized"):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        result = cls(
            value["review_id"], value["source_candidate_id"], value["source_candidate_sha256"],
            value["reviewer_coordinate_sha256"], value["critic_report_sha256"],
            CriticKnowledgePackDecision(value["decision"]), value["unresolved_critical_count"],
            value["unresolved_high_count"], _reasons(value["reason_codes"]),
            value["reviewed_at_epoch_ms"],
        )
        if result.to_dict() != dict(value):
            raise ValueError("Critic review hash mismatch")
        return result


@dataclass(frozen=True, slots=True)
class KnowledgePackSigningCandidate:
    signing_candidate_id: str
    pack_id: str
    pack_version: str
    source_candidate_id: str
    source_candidate_sha256: str
    source_feature_rule_sha256: str
    source_policy_sha256: str
    predecessor_pack_sha256: str | None
    human_review_id: str
    human_review_sha256: str
    critic_review_id: str
    critic_review_sha256: str
    state: KnowledgePackSigningState

    def __post_init__(self) -> None:
        for field in ("signing_candidate_id", "pack_id", "source_candidate_id", "human_review_id", "critic_review_id"):
            _id(getattr(self, field), field)
        if not isinstance(self.pack_version, str) or _SEMVER.fullmatch(self.pack_version) is None:
            raise ValueError("pack_version must be semantic version x.y.z")
        for field in ("source_candidate_sha256", "source_feature_rule_sha256", "source_policy_sha256", "human_review_sha256", "critic_review_sha256"):
            _sha(getattr(self, field), field)
        if self.predecessor_pack_sha256 is not None:
            _sha(self.predecessor_pack_sha256, "predecessor_pack_sha256")
        if self.human_review_id == self.critic_review_id:
            raise ValueError("Human and Critic review IDs must be distinct")
        if not isinstance(self.state, KnowledgePackSigningState):
            raise ValueError("state must be a KnowledgePackSigningState")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "candidate_version": KNOWLEDGE_PACK_SIGNING_VERSION,
            "record_type": "KNOWLEDGE_PACK_SIGNING_CANDIDATE",
            "task_owner": "TASK-029",
            "compatibility_contract": KNOWLEDGE_PACK_COMPATIBILITY_CONTRACT,
            "signing_candidate_id": self.signing_candidate_id,
            "pack_id": self.pack_id,
            "pack_version": self.pack_version,
            "source_candidate_id": self.source_candidate_id,
            "source_candidate_sha256": self.source_candidate_sha256,
            "source_feature_rule_sha256": self.source_feature_rule_sha256,
            "source_policy_sha256": self.source_policy_sha256,
            "predecessor_pack_sha256": self.predecessor_pack_sha256,
            "human_review_id": self.human_review_id,
            "human_review_sha256": self.human_review_sha256,
            "critic_review_id": self.critic_review_id,
            "critic_review_sha256": self.critic_review_sha256,
            "state": self.state.value,
            "owner_scope_coordinates_included": False,
            "project_scope_coordinates_included": False,
            "reviewer_coordinates_included": False,
            "raw_media_included": False,
            "text_body_included": False,
            "absolute_host_path_included": False,
            "credential_included": False,
            "signing_key_material_included": False,
            "signature_present": False,
            "signature_verified": False,
            "latest_source_revalidation_required": True,
            "external_signature_required": True,
            "in_memory_candidate_only": True,
            "knowledge_pack_write_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "automatic_promotion_authorized": False,
            "runtime_profile_apply_authorized": False,
            "rollback_execution_authorized": False,
            "release_authorized": False,
            "external_effect_authorized": False,
        }
        body["signing_candidate_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "KnowledgePackSigningCandidate":
        expected = {
            "candidate_version", "record_type", "task_owner", "compatibility_contract",
            "signing_candidate_id", "pack_id", "pack_version", "source_candidate_id",
            "source_candidate_sha256", "source_feature_rule_sha256", "source_policy_sha256",
            "predecessor_pack_sha256", "human_review_id", "human_review_sha256",
            "critic_review_id", "critic_review_sha256", "state",
            "owner_scope_coordinates_included", "project_scope_coordinates_included",
            "reviewer_coordinates_included", "raw_media_included", "text_body_included",
            "absolute_host_path_included", "credential_included", "signing_key_material_included",
            "signature_present", "signature_verified", "latest_source_revalidation_required",
            "external_signature_required", "in_memory_candidate_only",
            "knowledge_pack_write_authorized", "knowledge_pack_promotion_authorized",
            "automatic_promotion_authorized", "runtime_profile_apply_authorized",
            "rollback_execution_authorized", "release_authorized",
            "external_effect_authorized", "signing_candidate_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("signing candidate fields are incomplete or unknown")
        if (value["candidate_version"], value["record_type"], value["task_owner"], value["compatibility_contract"]) != (
            KNOWLEDGE_PACK_SIGNING_VERSION, "KNOWLEDGE_PACK_SIGNING_CANDIDATE", "TASK-029",
            KNOWLEDGE_PACK_COMPATIBILITY_CONTRACT,
        ):
            raise ValueError("signing candidate identity mismatch")
        false_fields = (
            "owner_scope_coordinates_included", "project_scope_coordinates_included",
            "reviewer_coordinates_included", "raw_media_included", "text_body_included",
            "absolute_host_path_included", "credential_included", "signing_key_material_included",
            "signature_present", "signature_verified", "knowledge_pack_write_authorized",
            "knowledge_pack_promotion_authorized", "automatic_promotion_authorized",
            "runtime_profile_apply_authorized", "rollback_execution_authorized",
            "release_authorized", "external_effect_authorized",
        )
        for field in false_fields:
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        for field in ("latest_source_revalidation_required", "external_signature_required", "in_memory_candidate_only"):
            if value[field] is not True:
                raise ValueError(f"{field} must remain true")
        result = cls(
            value["signing_candidate_id"], value["pack_id"], value["pack_version"],
            value["source_candidate_id"], value["source_candidate_sha256"],
            value["source_feature_rule_sha256"], value["source_policy_sha256"],
            value["predecessor_pack_sha256"], value["human_review_id"],
            value["human_review_sha256"], value["critic_review_id"],
            value["critic_review_sha256"], KnowledgePackSigningState(value["state"]),
        )
        if result.to_dict() != dict(value):
            raise ValueError("signing candidate hash mismatch")
        return result


def confirm_human_knowledge_pack_review(
    *, review_id: str, candidate: KnowledgePackPromotionCandidate,
    reviewer_coordinate_sha256: str, decision: HumanKnowledgePackDecision,
    reason_codes: Iterable[str], reviewed_at_epoch_ms: int,
) -> HumanKnowledgePackReview:
    if not isinstance(candidate, KnowledgePackPromotionCandidate) or candidate.state is not KnowledgePackCandidateState.READY_FOR_HUMAN_KNOWLEDGE_PACK_REVIEW:
        raise ValueError("candidate is not ready for Human Knowledge Pack review")
    return HumanKnowledgePackReview(
        review_id, candidate.candidate_id, candidate.to_dict()["candidate_sha256"],
        reviewer_coordinate_sha256, decision, tuple(reason_codes), reviewed_at_epoch_ms,
    )


def confirm_independent_knowledge_pack_critic_review(
    *, review_id: str, candidate: KnowledgePackPromotionCandidate,
    reviewer_coordinate_sha256: str, critic_report_sha256: str,
    decision: CriticKnowledgePackDecision, unresolved_critical_count: int,
    unresolved_high_count: int, reason_codes: Iterable[str], reviewed_at_epoch_ms: int,
) -> IndependentKnowledgePackCriticReview:
    if not isinstance(candidate, KnowledgePackPromotionCandidate) or candidate.state is not KnowledgePackCandidateState.READY_FOR_HUMAN_KNOWLEDGE_PACK_REVIEW:
        raise ValueError("candidate is not ready for independent Critic review")
    return IndependentKnowledgePackCriticReview(
        review_id, candidate.candidate_id, candidate.to_dict()["candidate_sha256"],
        reviewer_coordinate_sha256, critic_report_sha256, decision,
        unresolved_critical_count, unresolved_high_count, tuple(reason_codes),
        reviewed_at_epoch_ms,
    )


def compile_knowledge_pack_signing_candidate(
    *, signing_candidate_id: str, pack_id: str, pack_version: str,
    source_candidate_payload: Mapping[str, Any], source_candidate_id: str,
    feature_key: str, sources: Iterable[KnowledgePackSource],
    policy: KnowledgePackCandidatePolicy, human_review: HumanKnowledgePackReview,
    critic_review: IndependentKnowledgePackCriticReview,
    predecessor_pack_sha256: str | None = None,
) -> KnowledgePackSigningCandidate:
    """Recompile R6 and bind exact independent reviews without signing or I/O."""
    current = compile_knowledge_pack_promotion_candidate(source_candidate_id, feature_key, sources, policy)
    current_payload = current.to_dict()
    if not isinstance(source_candidate_payload, Mapping) or dict(source_candidate_payload) != current_payload:
        raise ValueError("source candidate does not match exact current sources")
    if current.state is not KnowledgePackCandidateState.READY_FOR_HUMAN_KNOWLEDGE_PACK_REVIEW:
        raise ValueError("source candidate is not ready for review binding")
    human = HumanKnowledgePackReview.from_dict(human_review.to_dict())
    critic = IndependentKnowledgePackCriticReview.from_dict(critic_review.to_dict())
    candidate_sha = current_payload["candidate_sha256"]
    for label, review in (("Human", human), ("Critic", critic)):
        if review.source_candidate_id != current.candidate_id or review.source_candidate_sha256 != candidate_sha:
            raise ValueError(f"{label} review does not bind the exact current candidate")
    if human.review_id == critic.review_id:
        raise ValueError("Human and Critic review IDs must be distinct")
    if human.reviewer_coordinate_sha256 == critic.reviewer_coordinate_sha256:
        raise ValueError("Human and Critic reviewers must be independent")
    if human.decision is HumanKnowledgePackDecision.REJECT:
        state = KnowledgePackSigningState.HUMAN_REJECTED
    elif critic.decision is CriticKnowledgePackDecision.REJECT:
        state = KnowledgePackSigningState.CRITIC_REJECTED
    else:
        state = KnowledgePackSigningState.READY_FOR_EXTERNAL_SIGNATURE
    return KnowledgePackSigningCandidate(
        signing_candidate_id, pack_id, pack_version, current.candidate_id, candidate_sha,
        current_payload["feature_rule_sha256"], current_payload["promotion_policy"]["policy_sha256"],
        predecessor_pack_sha256, human.review_id, human.to_dict()["review_sha256"],
        critic.review_id, critic.to_dict()["review_sha256"], state,
    )


def verify_knowledge_pack_signing_candidate(payload: Mapping[str, Any], **compile_kwargs: Any) -> None:
    expected = compile_knowledge_pack_signing_candidate(**compile_kwargs).to_dict()
    if not isinstance(payload, Mapping) or dict(payload) != expected:
        raise ValueError("signing candidate does not match exact current sources and reviews")


__all__ = [
    "CriticKnowledgePackDecision", "HumanKnowledgePackDecision",
    "HumanKnowledgePackReview", "IndependentKnowledgePackCriticReview",
    "KNOWLEDGE_PACK_COMPATIBILITY_CONTRACT", "KNOWLEDGE_PACK_SIGNING_VERSION",
    "KnowledgePackSigningCandidate", "KnowledgePackSigningState",
    "compile_knowledge_pack_signing_candidate", "confirm_human_knowledge_pack_review",
    "confirm_independent_knowledge_pack_critic_review",
    "verify_knowledge_pack_signing_candidate",
]
