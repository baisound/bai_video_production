"""TASK-019 deterministic, no-effect scoring profile tuning proposals.

The contract consumes TASK-008 profiles and TASK-015 aggregate feedback that
already exist in memory.  It produces Human-review candidates only: no profile
store, API, media, filesystem, subprocess, or automatic promotion is exposed.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import re
from typing import Any, Iterable

from .multimodal_scoring import EvidenceValidity, FeatureRule, ScoringProfile
from .serialization import canonical_json_bytes, sha256_bytes
from .youtube_feedback import FeedbackSnapshotState, YouTubeFeedbackSnapshot


_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_STABLE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_MAX_ADJUSTMENTS = 16
_MAX_EVALUATIONS = 32
_MAX_SAMPLE_COUNT = 1_000_000_000


def _sha256(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be sha256:<64 lowercase hex>")
    return value


def _bounded_int(value: int, field_name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{field_name} must be an integer in {minimum}..{maximum}")
    return value


class AdjustmentReason(str, Enum):
    ENGAGEMENT_SIGNAL = "ENGAGEMENT_SIGNAL"
    RETENTION_SIGNAL = "RETENTION_SIGNAL"
    FEATURE_BALANCE = "FEATURE_BALANCE"


class TuningProposalState(str, Enum):
    READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
    FEEDBACK_INCOMPLETE = "FEEDBACK_INCOMPLETE"
    INSUFFICIENT_HOLDOUT = "INSUFFICIENT_HOLDOUT"
    NO_MEASURED_IMPROVEMENT = "NO_MEASURED_IMPROVEMENT"
    HOLDOUT_REGRESSION = "HOLDOUT_REGRESSION"
    UNKNOWN_EVIDENCE = "UNKNOWN_EVIDENCE"
    STALE_OR_REVOKED_EVIDENCE = "STALE_OR_REVOKED_EVIDENCE"


@dataclass(frozen=True, slots=True, order=True)
class WeightAdjustment:
    feature_key: str
    proposed_weight_milli: int
    reason: AdjustmentReason

    def __post_init__(self) -> None:
        if not isinstance(self.feature_key, str) or not _STABLE_ID_RE.fullmatch(self.feature_key):
            raise ValueError("feature_key is invalid")
        _bounded_int(self.proposed_weight_milli, "proposed_weight_milli", 1, 1000)
        if not isinstance(self.reason, AdjustmentReason):
            raise ValueError("reason must be an AdjustmentReason")

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_key": self.feature_key,
            "proposed_weight_milli": self.proposed_weight_milli,
            "reason": self.reason.value,
        }


@dataclass(frozen=True, slots=True)
class TuningPolicy:
    policy_id: str
    policy_version: str
    max_changed_rules: int
    max_abs_weight_delta_milli: int
    minimum_holdout_samples: int
    minimum_improvement_milli: int
    max_single_holdout_regression_milli: int

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, str) or not _STABLE_ID_RE.fullmatch(self.policy_id):
            raise ValueError("policy_id is invalid")
        if not isinstance(self.policy_version, str) or not _SEMVER_RE.fullmatch(self.policy_version):
            raise ValueError("policy_version must be semantic version x.y.z")
        _bounded_int(self.max_changed_rules, "max_changed_rules", 2, _MAX_ADJUSTMENTS)
        _bounded_int(
            self.max_abs_weight_delta_milli,
            "max_abs_weight_delta_milli",
            1,
            500,
        )
        _bounded_int(self.minimum_holdout_samples, "minimum_holdout_samples", 1, _MAX_SAMPLE_COUNT)
        _bounded_int(self.minimum_improvement_milli, "minimum_improvement_milli", 1, 1000)
        _bounded_int(
            self.max_single_holdout_regression_milli,
            "max_single_holdout_regression_milli",
            0,
            1000,
        )

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "max_changed_rules": self.max_changed_rules,
            "max_abs_weight_delta_milli": self.max_abs_weight_delta_milli,
            "minimum_holdout_samples": self.minimum_holdout_samples,
            "minimum_improvement_milli": self.minimum_improvement_milli,
            "max_single_holdout_regression_milli": self.max_single_holdout_regression_milli,
        }
        body["policy_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(frozen=True, slots=True, order=True)
class HoldoutEvaluation:
    evaluation_id: str
    holdout_manifest_sha256: str
    sample_count: int
    baseline_quality_milli: int
    proposed_quality_milli: int
    validity: EvidenceValidity

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation_id, str) or not _STABLE_ID_RE.fullmatch(
            self.evaluation_id
        ):
            raise ValueError("evaluation_id is invalid")
        _sha256(self.holdout_manifest_sha256, "holdout_manifest_sha256")
        _bounded_int(self.sample_count, "sample_count", 1, _MAX_SAMPLE_COUNT)
        _bounded_int(self.baseline_quality_milli, "baseline_quality_milli", 0, 1000)
        _bounded_int(self.proposed_quality_milli, "proposed_quality_milli", 0, 1000)
        if not isinstance(self.validity, EvidenceValidity):
            raise ValueError("validity must be an EvidenceValidity")

    @property
    def delta_milli(self) -> int:
        return self.proposed_quality_milli - self.baseline_quality_milli

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "holdout_manifest_sha256": self.holdout_manifest_sha256,
            "sample_count": self.sample_count,
            "baseline_quality_milli": self.baseline_quality_milli,
            "proposed_quality_milli": self.proposed_quality_milli,
            "delta_milli": self.delta_milli,
            "validity": self.validity.value,
        }


@dataclass(frozen=True, slots=True)
class ProfileTuningProposal:
    baseline_profile: ScoringProfile
    proposed_profile: ScoringProfile
    feedback_snapshot_sha256: str
    feedback_state: FeedbackSnapshotState
    policy: TuningPolicy
    adjustments: tuple[WeightAdjustment, ...]
    evaluations: tuple[HoldoutEvaluation, ...]
    state: TuningProposalState
    total_holdout_samples: int
    weighted_improvement_milli: int | None
    regressed_evaluation_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.baseline_profile, ScoringProfile):
            raise ValueError("baseline_profile must be a ScoringProfile")
        if not isinstance(self.proposed_profile, ScoringProfile):
            raise ValueError("proposed_profile must be a ScoringProfile")
        _sha256(self.feedback_snapshot_sha256, "feedback_snapshot_sha256")
        if not isinstance(self.feedback_state, FeedbackSnapshotState):
            raise ValueError("feedback_state must be a FeedbackSnapshotState")
        if not isinstance(self.policy, TuningPolicy):
            raise ValueError("policy must be a TuningPolicy")
        if not isinstance(self.state, TuningProposalState):
            raise ValueError("state must be a TuningProposalState")
        if self.adjustments != tuple(sorted(self.adjustments, key=lambda item: item.feature_key)):
            raise ValueError("adjustments must be canonically sorted")
        if self.evaluations != tuple(sorted(self.evaluations, key=lambda item: item.evaluation_id)):
            raise ValueError("evaluations must be canonically sorted")
        expected_profile = _build_proposed_profile(
            self.baseline_profile,
            self.proposed_profile.profile_version,
            self.policy,
            self.adjustments,
        )
        if self.proposed_profile != expected_profile:
            raise ValueError("proposed_profile does not exactly project the declared adjustments")
        expected = _classify_evaluations(
            self.policy,
            self.evaluations,
            feedback_complete=self.feedback_state is FeedbackSnapshotState.COMPLETE,
        )
        actual = (
            self.state,
            self.total_holdout_samples,
            self.weighted_improvement_milli,
            self.regressed_evaluation_ids,
        )
        if actual != expected:
            raise ValueError("proposal state and evaluation summary do not match constituents")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "proposal_version": "1.0.0",
            "task_owner": "TASK-019",
            "baseline_profile": self.baseline_profile.to_dict(),
            "proposed_profile": self.proposed_profile.to_dict(),
            "feedback_snapshot_sha256": self.feedback_snapshot_sha256,
            "feedback_state": self.feedback_state.value,
            "tuning_policy": self.policy.to_dict(),
            "adjustments": [item.to_dict() for item in self.adjustments],
            "holdout_evaluations": [item.to_dict() for item in self.evaluations],
            "state": self.state.value,
            "total_holdout_samples": self.total_holdout_samples,
            "weighted_improvement_milli": self.weighted_improvement_milli,
            "regressed_evaluation_ids": list(self.regressed_evaluation_ids),
            "rollback_profile_sha256": self.baseline_profile.to_dict()["profile_sha256"],
            "human_review_required": True,
            "automatic_profile_write_authorized": False,
            "automatic_promotion_authorized": False,
            "automatic_rollback_execution_authorized": False,
            "edit_plan_mutation_authorized": False,
            "external_effect_authorized": False,
        }
        body["proposal_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


def compile_profile_tuning_proposal(
    baseline_profile: ScoringProfile,
    proposed_profile_version: str,
    feedback_snapshot: YouTubeFeedbackSnapshot,
    policy: TuningPolicy,
    adjustments: Iterable[WeightAdjustment],
    evaluations: Iterable[HoldoutEvaluation],
) -> ProfileTuningProposal:
    """Compile a bounded Human-review proposal without applying any profile change."""

    if not isinstance(baseline_profile, ScoringProfile):
        raise ValueError("baseline_profile must be a ScoringProfile")
    if not isinstance(proposed_profile_version, str) or not _SEMVER_RE.fullmatch(
        proposed_profile_version
    ):
        raise ValueError("proposed_profile_version must be semantic version x.y.z")
    if proposed_profile_version == baseline_profile.profile_version:
        raise ValueError("proposed_profile_version must differ from the baseline")
    if not isinstance(feedback_snapshot, YouTubeFeedbackSnapshot):
        raise ValueError("feedback_snapshot must be a YouTubeFeedbackSnapshot")
    if not isinstance(policy, TuningPolicy):
        raise ValueError("policy must be a TuningPolicy")
    adjustment_rows = tuple(adjustments)
    evaluation_rows = tuple(evaluations)
    if any(not isinstance(item, WeightAdjustment) for item in adjustment_rows):
        raise ValueError("adjustments must contain WeightAdjustment values")
    if any(not isinstance(item, HoldoutEvaluation) for item in evaluation_rows):
        raise ValueError("evaluations must contain HoldoutEvaluation values")
    canonical_adjustments = tuple(sorted(adjustment_rows, key=lambda item: item.feature_key))
    canonical_evaluations = tuple(sorted(evaluation_rows, key=lambda item: item.evaluation_id))
    proposed = _build_proposed_profile(
        baseline_profile,
        proposed_profile_version,
        policy,
        canonical_adjustments,
    )
    feedback_payload = feedback_snapshot.to_dict()
    feedback_sha = feedback_payload["snapshot_sha256"]
    feedback_complete = feedback_snapshot.state is FeedbackSnapshotState.COMPLETE
    state, total_samples, improvement, regressed = _classify_evaluations(
        policy,
        canonical_evaluations,
        feedback_complete,
    )
    return ProfileTuningProposal(
        baseline_profile,
        proposed,
        feedback_sha,
        feedback_snapshot.state,
        policy,
        canonical_adjustments,
        canonical_evaluations,
        state,
        total_samples,
        improvement,
        regressed,
    )


def _build_proposed_profile(
    baseline: ScoringProfile,
    proposed_version: str,
    policy: TuningPolicy,
    adjustments: tuple[WeightAdjustment, ...],
) -> ScoringProfile:
    if not 2 <= len(adjustments) <= min(policy.max_changed_rules, _MAX_ADJUSTMENTS):
        raise ValueError("adjustments must contain 2..max_changed_rules rows")
    keys = [item.feature_key for item in adjustments]
    if len(keys) != len(set(keys)):
        raise ValueError("adjustment feature keys must be unique")
    baseline_by_key = {item.feature_key: item for item in baseline.rules}
    if set(keys) - set(baseline_by_key):
        raise ValueError("adjustment feature is not present in the baseline profile")
    adjusted = {item.feature_key: item for item in adjustments}
    rules: list[FeatureRule] = []
    changed = 0
    for rule in baseline.rules:
        adjustment = adjusted.get(rule.feature_key)
        if adjustment is None:
            rules.append(rule)
            continue
        delta = adjustment.proposed_weight_milli - rule.weight_milli
        if delta == 0:
            raise ValueError("adjustment must change its baseline weight")
        if abs(delta) > policy.max_abs_weight_delta_milli:
            raise ValueError("weight delta exceeds policy")
        rules.append(replace(rule, weight_milli=adjustment.proposed_weight_milli))
        changed += 1
    if changed != len(adjustments):
        raise ValueError("adjustment projection mismatch")
    return ScoringProfile(baseline.profile_id, proposed_version, tuple(rules))


def _classify_evaluations(
    policy: TuningPolicy,
    evaluations: tuple[HoldoutEvaluation, ...],
    feedback_complete: bool,
) -> tuple[TuningProposalState, int, int | None, tuple[str, ...]]:
    if not 1 <= len(evaluations) <= _MAX_EVALUATIONS:
        raise ValueError("evaluations must contain 1-32 rows")
    ids = [item.evaluation_id for item in evaluations]
    if len(ids) != len(set(ids)):
        raise ValueError("evaluation_id values must be unique")
    manifests = [item.holdout_manifest_sha256 for item in evaluations]
    if len(manifests) != len(set(manifests)):
        raise ValueError("holdout manifests must be unique")
    total = sum(item.sample_count for item in evaluations)
    if total > _MAX_SAMPLE_COUNT:
        raise ValueError("total holdout samples exceed the cap")
    weighted_delta = sum(item.delta_milli * item.sample_count for item in evaluations)
    improvement = (weighted_delta + total // 2) // total
    regressed = tuple(
        item.evaluation_id
        for item in evaluations
        if item.delta_milli < -policy.max_single_holdout_regression_milli
    )
    if not feedback_complete:
        state = TuningProposalState.FEEDBACK_INCOMPLETE
    elif any(item.validity in {EvidenceValidity.STALE, EvidenceValidity.REVOKED} for item in evaluations):
        state = TuningProposalState.STALE_OR_REVOKED_EVIDENCE
    elif any(item.validity is EvidenceValidity.UNKNOWN for item in evaluations):
        state = TuningProposalState.UNKNOWN_EVIDENCE
    elif total < policy.minimum_holdout_samples:
        state = TuningProposalState.INSUFFICIENT_HOLDOUT
    elif regressed:
        state = TuningProposalState.HOLDOUT_REGRESSION
    elif improvement < policy.minimum_improvement_milli:
        state = TuningProposalState.NO_MEASURED_IMPROVEMENT
    else:
        state = TuningProposalState.READY_FOR_HUMAN_REVIEW
    return state, total, improvement, regressed


def verify_profile_tuning_proposal_hash(payload: dict[str, Any]) -> None:
    """Verify all nested non-self digests and the outer proposal digest."""

    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")
    body = dict(payload)
    claimed = body.pop("proposal_sha256", None)
    _sha256(claimed, "proposal_sha256")
    for field_name, digest_name in (
        ("baseline_profile", "profile_sha256"),
        ("proposed_profile", "profile_sha256"),
        ("tuning_policy", "policy_sha256"),
    ):
        nested = body.get(field_name)
        if not isinstance(nested, dict):
            raise ValueError(f"{field_name} must be an object")
        nested_body = dict(nested)
        nested_claimed = nested_body.pop(digest_name, None)
        _sha256(nested_claimed, f"{field_name}.{digest_name}")
        if nested_claimed != sha256_bytes(canonical_json_bytes(nested_body)):
            raise ValueError(f"{field_name}.{digest_name} does not match its canonical body")
    baseline_sha = body["baseline_profile"]["profile_sha256"]
    if body.get("rollback_profile_sha256") != baseline_sha:
        raise ValueError("rollback_profile_sha256 must equal baseline profile digest")
    if claimed != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError("proposal_sha256 does not match the canonical proposal body")
