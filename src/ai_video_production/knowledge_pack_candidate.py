"""TASK-029 R6 pure cross-owner Knowledge Pack promotion candidate.

The compiler revalidates exact R5 Owner Profile Registry histories against the
R1 Human Decision histories bound into their latest revisions.  It emits a
body-free, unlinkable in-memory review candidate only; it cannot write, sign,
promote, release, apply, or roll back a Knowledge Pack.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Iterable, Mapping

from .human_edit_learning import HumanActionEvidence, OwnerDecisionState
from .multimodal_scoring import (
    EvidenceValidity,
    FeatureModality,
    FeaturePolarity,
    FeatureRule,
    FeatureSourceSelector,
)
from .owner_decision_store import HumanDecision, OwnerDecisionHistory
from .owner_profile_registry_store import OwnerProfileRegistryHistory
from .serialization import canonical_json_bytes, sha256_bytes


KNOWLEDGE_PACK_CANDIDATE_VERSION = "1.0.0"
_METRIC_IDS = (
    "human_acceptance",
    "qa_compliance",
    "quality_improvement",
    "rework_reduction",
    "sample_confidence",
    "time_reduction",
)
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_STABLE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_MAX_SOURCES = 64


def _sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{field} must be sha256:<64 lowercase hex>")
    return value


def _stable_id(value: object, field: str) -> str:
    if not isinstance(value, str) or _STABLE_ID_RE.fullmatch(value) is None:
        raise ValueError(f"{field} is invalid")
    return value


def _bounded_int(value: object, field: str, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ValueError(f"{field} must be an integer in {minimum}..{maximum}")
    return value


def _feature_rule_from_dict(value: Mapping[str, Any]) -> FeatureRule:
    expected = {
        "feature_key", "modality", "weight_milli", "raw_range", "polarity",
        "required", "optional_missing_value_milli", "allowed_sources",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("feature rule fields are incomplete or unknown")
    raw_range = value["raw_range"]
    sources = value["allowed_sources"]
    if not isinstance(raw_range, Mapping) or set(raw_range) != {"minimum", "maximum"}:
        raise ValueError("feature rule raw_range is invalid")
    if not isinstance(sources, list):
        raise ValueError("feature rule allowed_sources must be an array")
    selectors: list[FeatureSourceSelector] = []
    for row in sources:
        if not isinstance(row, Mapping) or set(row) != {"producer_task_id", "contract_id"}:
            raise ValueError("feature rule source selector is invalid")
        selectors.append(FeatureSourceSelector(row["producer_task_id"], row["contract_id"]))
    return FeatureRule(
        feature_key=value["feature_key"],
        modality=FeatureModality(value["modality"]),
        weight_milli=value["weight_milli"],
        raw_minimum=raw_range["minimum"],
        raw_maximum=raw_range["maximum"],
        polarity=FeaturePolarity(value["polarity"]),
        required=value["required"],
        optional_missing_value_milli=value["optional_missing_value_milli"],
        allowed_sources=tuple(selectors),
    )


class KnowledgePackCandidateState(str, Enum):
    READY_FOR_HUMAN_KNOWLEDGE_PACK_REVIEW = "READY_FOR_HUMAN_KNOWLEDGE_PACK_REVIEW"
    INSUFFICIENT_OWNER_DIVERSITY = "INSUFFICIENT_OWNER_DIVERSITY"
    INSUFFICIENT_PROJECT_DIVERSITY = "INSUFFICIENT_PROJECT_DIVERSITY"
    INSUFFICIENT_SAMPLES = "INSUFFICIENT_SAMPLES"
    AXIS_REGRESSION = "AXIS_REGRESSION"
    NO_REPRODUCIBLE_BENEFIT = "NO_REPRODUCIBLE_BENEFIT"


@dataclass(frozen=True, slots=True)
class KnowledgePackCandidatePolicy:
    policy_id: str
    policy_version: str
    minimum_owner_count: int
    minimum_project_count: int
    minimum_samples_per_axis: int
    minimum_owner_weighted_benefit_milli: int
    maximum_axis_regression_milli: int

    def __post_init__(self) -> None:
        _stable_id(self.policy_id, "policy_id")
        if not isinstance(self.policy_version, str) or _SEMVER_RE.fullmatch(self.policy_version) is None:
            raise ValueError("policy_version must be semantic version x.y.z")
        _bounded_int(self.minimum_owner_count, "minimum_owner_count", 2, _MAX_SOURCES)
        _bounded_int(self.minimum_project_count, "minimum_project_count", 2, 4096)
        _bounded_int(self.minimum_samples_per_axis, "minimum_samples_per_axis", 1, 1_000_000_000)
        _bounded_int(
            self.minimum_owner_weighted_benefit_milli,
            "minimum_owner_weighted_benefit_milli", 0, 1000,
        )
        _bounded_int(self.maximum_axis_regression_milli, "maximum_axis_regression_milli", 0, 1000)

    def to_dict(self) -> dict[str, Any]:
        body = {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "minimum_owner_count": self.minimum_owner_count,
            "minimum_project_count": self.minimum_project_count,
            "minimum_samples_per_axis": self.minimum_samples_per_axis,
            "minimum_owner_weighted_benefit_milli": self.minimum_owner_weighted_benefit_milli,
            "maximum_axis_regression_milli": self.maximum_axis_regression_milli,
        }
        body["policy_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "KnowledgePackCandidatePolicy":
        expected = {
            "policy_id", "policy_version", "minimum_owner_count",
            "minimum_project_count", "minimum_samples_per_axis",
            "minimum_owner_weighted_benefit_milli", "maximum_axis_regression_milli",
            "policy_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("knowledge pack policy fields are incomplete or unknown")
        result = cls(
            value["policy_id"], value["policy_version"], value["minimum_owner_count"],
            value["minimum_project_count"], value["minimum_samples_per_axis"],
            value["minimum_owner_weighted_benefit_milli"],
            value["maximum_axis_regression_milli"],
        )
        if result.to_dict() != dict(value):
            raise ValueError("knowledge pack policy hash mismatch")
        return result


@dataclass(frozen=True, slots=True, order=True)
class AggregatedMetricEvaluation:
    metric_id: str
    minimum_delta_milli: int
    total_sample_count: int
    contributing_owner_count: int

    def __post_init__(self) -> None:
        if self.metric_id not in _METRIC_IDS:
            raise ValueError("metric_id is not a TASK-029 axis")
        _bounded_int(self.minimum_delta_milli, "minimum_delta_milli", -1000, 1000)
        _bounded_int(self.total_sample_count, "total_sample_count", 1, 1_000_000_000)
        _bounded_int(self.contributing_owner_count, "contributing_owner_count", 1, _MAX_SOURCES)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "minimum_delta_milli": self.minimum_delta_milli,
            "total_sample_count": self.total_sample_count,
            "contributing_owner_count": self.contributing_owner_count,
        }


@dataclass(frozen=True, slots=True)
class KnowledgePackSource:
    registry_history: OwnerProfileRegistryHistory
    decision_history: OwnerDecisionHistory
    decision_id: str
    evidence: tuple[HumanActionEvidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.registry_history, OwnerProfileRegistryHistory):
            raise ValueError("registry_history must be an OwnerProfileRegistryHistory")
        if not isinstance(self.decision_history, OwnerDecisionHistory):
            raise ValueError("decision_history must be an OwnerDecisionHistory")
        _stable_id(self.decision_id, "decision_id")
        if not self.evidence or not all(isinstance(row, HumanActionEvidence) for row in self.evidence):
            raise ValueError("evidence must contain HumanActionEvidence values")
        hashes = tuple(row.to_dict()["evidence_sha256"] for row in self.evidence)
        if hashes != tuple(sorted(set(hashes))):
            raise ValueError("evidence must be unique and sorted by evidence hash")


@dataclass(frozen=True, slots=True)
class KnowledgePackPromotionCandidate:
    candidate_id: str
    feature_rule: FeatureRule
    hypothesis_id: str
    action_type: str
    condition_fingerprint_sha256: str
    source_coordinate_sha256s: tuple[str, ...]
    source_owner_count: int
    source_project_count: int
    source_evidence_count: int
    metrics: tuple[AggregatedMetricEvaluation, ...]
    minimum_owner_weighted_benefit_milli: int
    policy: KnowledgePackCandidatePolicy
    state: KnowledgePackCandidateState

    def __post_init__(self) -> None:
        _stable_id(self.candidate_id, "candidate_id")
        if not isinstance(self.feature_rule, FeatureRule):
            raise ValueError("feature_rule must be a FeatureRule")
        _stable_id(self.hypothesis_id, "hypothesis_id")
        _stable_id(self.action_type, "action_type")
        _sha256(self.condition_fingerprint_sha256, "condition_fingerprint_sha256")
        if not 1 <= len(self.source_coordinate_sha256s) <= _MAX_SOURCES:
            raise ValueError("source coordinates must contain 1..64 items")
        if self.source_coordinate_sha256s != tuple(sorted(set(self.source_coordinate_sha256s))):
            raise ValueError("source coordinates must be unique and sorted")
        for value in self.source_coordinate_sha256s:
            _sha256(value, "source_coordinate_sha256")
        _bounded_int(self.source_owner_count, "source_owner_count", 1, _MAX_SOURCES)
        _bounded_int(self.source_project_count, "source_project_count", 1, 4096)
        _bounded_int(self.source_evidence_count, "source_evidence_count", 1, 16384)
        if self.metrics != tuple(sorted(self.metrics, key=lambda row: row.metric_id)):
            raise ValueError("metrics must be sorted")
        if tuple(row.metric_id for row in self.metrics) != _METRIC_IDS:
            raise ValueError("all six TASK-029 axes are required exactly once")
        _bounded_int(
            self.minimum_owner_weighted_benefit_milli,
            "minimum_owner_weighted_benefit_milli", -1000, 1000,
        )
        if not isinstance(self.policy, KnowledgePackCandidatePolicy):
            raise ValueError("policy must be a KnowledgePackCandidatePolicy")
        if not isinstance(self.state, KnowledgePackCandidateState):
            raise ValueError("state must be a KnowledgePackCandidateState")
        if self.source_owner_count != len(self.source_coordinate_sha256s):
            raise ValueError("source_owner_count must equal the source coordinate count")
        if self.source_project_count > self.source_evidence_count:
            raise ValueError("source_project_count cannot exceed source_evidence_count")
        if any(row.contributing_owner_count != self.source_owner_count for row in self.metrics):
            raise ValueError("every metric must include every source Owner")
        if self.state is not _classify(owner_count=self.source_owner_count, project_count=self.source_project_count, metrics=self.metrics, minimum_benefit=self.minimum_owner_weighted_benefit_milli, policy=self.policy):
            raise ValueError("candidate state does not match its aggregate Evidence")

    def to_dict(self) -> dict[str, Any]:
        rule = self.feature_rule.to_dict()
        body: dict[str, Any] = {
            "candidate_version": KNOWLEDGE_PACK_CANDIDATE_VERSION,
            "record_type": "KNOWLEDGE_PACK_PROMOTION_CANDIDATE",
            "task_owner": "TASK-029",
            "candidate_id": self.candidate_id,
            "feature_rule": rule,
            "feature_rule_sha256": sha256_bytes(canonical_json_bytes(rule)),
            "hypothesis_id": self.hypothesis_id,
            "action_type": self.action_type,
            "condition_fingerprint_sha256": self.condition_fingerprint_sha256,
            "source_coordinate_sha256s": list(self.source_coordinate_sha256s),
            "source_owner_count": self.source_owner_count,
            "source_project_count": self.source_project_count,
            "source_evidence_count": self.source_evidence_count,
            "aggregated_metric_evaluations": [row.to_dict() for row in self.metrics],
            "minimum_owner_weighted_benefit_milli": self.minimum_owner_weighted_benefit_milli,
            "promotion_policy": self.policy.to_dict(),
            "state": self.state.value,
            "owner_scope_coordinates_included": False,
            "project_scope_coordinates_included": False,
            "raw_media_included": False,
            "text_body_included": False,
            "absolute_host_path_included": False,
            "credential_included": False,
            "latest_source_revalidation_required": True,
            "human_review_required": True,
            "independent_critic_required": True,
            "signature_required": True,
            "in_memory_candidate_only": True,
            "knowledge_pack_write_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "automatic_promotion_authorized": False,
            "runtime_profile_apply_authorized": False,
            "rollback_execution_authorized": False,
            "release_authorized": False,
            "external_effect_authorized": False,
        }
        body["candidate_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "KnowledgePackPromotionCandidate":
        expected = {
            "candidate_version", "record_type", "task_owner", "candidate_id",
            "feature_rule", "feature_rule_sha256", "hypothesis_id", "action_type",
            "condition_fingerprint_sha256", "source_coordinate_sha256s",
            "source_owner_count", "source_project_count", "source_evidence_count",
            "aggregated_metric_evaluations", "minimum_owner_weighted_benefit_milli",
            "promotion_policy", "state", "owner_scope_coordinates_included",
            "project_scope_coordinates_included", "raw_media_included", "text_body_included",
            "absolute_host_path_included", "credential_included",
            "latest_source_revalidation_required", "human_review_required",
            "independent_critic_required", "signature_required", "in_memory_candidate_only",
            "knowledge_pack_write_authorized", "knowledge_pack_promotion_authorized",
            "automatic_promotion_authorized", "runtime_profile_apply_authorized",
            "rollback_execution_authorized", "release_authorized",
            "external_effect_authorized", "candidate_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("knowledge pack candidate fields are incomplete or unknown")
        if (
            value["candidate_version"] != KNOWLEDGE_PACK_CANDIDATE_VERSION
            or value["record_type"] != "KNOWLEDGE_PACK_PROMOTION_CANDIDATE"
            or value["task_owner"] != "TASK-029"
        ):
            raise ValueError("knowledge pack candidate identity mismatch")
        for field in (
            "owner_scope_coordinates_included", "project_scope_coordinates_included",
            "raw_media_included", "text_body_included", "absolute_host_path_included",
            "credential_included", "knowledge_pack_write_authorized",
            "knowledge_pack_promotion_authorized", "automatic_promotion_authorized",
            "runtime_profile_apply_authorized", "rollback_execution_authorized",
            "release_authorized", "external_effect_authorized",
        ):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        for field in (
            "latest_source_revalidation_required", "human_review_required",
            "independent_critic_required", "signature_required", "in_memory_candidate_only",
        ):
            if value[field] is not True:
                raise ValueError(f"{field} must remain true")
        rule = _feature_rule_from_dict(value["feature_rule"])
        if value["feature_rule_sha256"] != sha256_bytes(canonical_json_bytes(rule.to_dict())):
            raise ValueError("feature rule hash mismatch")
        rows = value["aggregated_metric_evaluations"]
        if not isinstance(rows, list):
            raise ValueError("aggregated metrics must be an array")
        metrics = tuple(
            AggregatedMetricEvaluation(
                row["metric_id"], row["minimum_delta_milli"], row["total_sample_count"],
                row["contributing_owner_count"],
            )
            for row in rows
        )
        result = cls(
            value["candidate_id"], rule, value["hypothesis_id"], value["action_type"],
            value["condition_fingerprint_sha256"], tuple(value["source_coordinate_sha256s"]),
            value["source_owner_count"], value["source_project_count"],
            value["source_evidence_count"], metrics,
            value["minimum_owner_weighted_benefit_milli"],
            KnowledgePackCandidatePolicy.from_dict(value["promotion_policy"]),
            KnowledgePackCandidateState(value["state"]),
        )
        if result.to_dict() != dict(value):
            raise ValueError("knowledge pack candidate hash or derived fields mismatch")
        return result


def _classify(
    *, owner_count: int, project_count: int,
    metrics: tuple[AggregatedMetricEvaluation, ...],
    minimum_benefit: int, policy: KnowledgePackCandidatePolicy,
) -> KnowledgePackCandidateState:
    if owner_count < policy.minimum_owner_count:
        return KnowledgePackCandidateState.INSUFFICIENT_OWNER_DIVERSITY
    if project_count < policy.minimum_project_count:
        return KnowledgePackCandidateState.INSUFFICIENT_PROJECT_DIVERSITY
    if any(row.total_sample_count < policy.minimum_samples_per_axis for row in metrics):
        return KnowledgePackCandidateState.INSUFFICIENT_SAMPLES
    if any(row.minimum_delta_milli < -policy.maximum_axis_regression_milli for row in metrics):
        return KnowledgePackCandidateState.AXIS_REGRESSION
    if minimum_benefit < policy.minimum_owner_weighted_benefit_milli:
        return KnowledgePackCandidateState.NO_REPRODUCIBLE_BENEFIT
    return KnowledgePackCandidateState.READY_FOR_HUMAN_KNOWLEDGE_PACK_REVIEW


def compile_knowledge_pack_promotion_candidate(
    candidate_id: str,
    feature_key: str,
    sources: Iterable[KnowledgePackSource],
    policy: KnowledgePackCandidatePolicy,
) -> KnowledgePackPromotionCandidate:
    """Compile one no-effect candidate from exact registered Human-approved sources."""

    _stable_id(candidate_id, "candidate_id")
    _stable_id(feature_key, "feature_key")
    if not isinstance(policy, KnowledgePackCandidatePolicy):
        raise ValueError("policy must be a KnowledgePackCandidatePolicy")
    rows = tuple(sources)
    if not 1 <= len(rows) <= _MAX_SOURCES or not all(isinstance(row, KnowledgePackSource) for row in rows):
        raise ValueError("sources must contain 1..64 KnowledgePackSource values")

    owners: set[str] = set()
    projects: set[str] = set()
    source_coordinates: list[str] = []
    source_evidence_hashes: set[str] = set()
    rules: list[FeatureRule] = []
    hypotheses: set[str] = set()
    actions: set[str] = set()
    conditions: set[str] = set()
    per_owner_benefits: list[int] = []
    metric_rows: dict[str, list[tuple[int, int]]] = {name: [] for name in _METRIC_IDS}

    for source in rows:
        registry = OwnerProfileRegistryHistory.from_dict(source.registry_history.to_dict())
        decisions = OwnerDecisionHistory.from_dict(source.decision_history.to_dict())
        if registry.revision < 1:
            raise ValueError("registered Owner Profile revision is required")
        if registry.owner_scope_sha256 != decisions.owner_scope_sha256:
            raise ValueError("registry and decision owner scope mismatch")
        if registry.owner_scope_sha256 in owners:
            raise ValueError("exactly one source per Owner is allowed")
        latest = registry.revisions[-1]
        registry_candidate = latest.candidate
        decision_payload = decisions.to_dict()
        if registry_candidate.source_decision_history_sha256 != decision_payload["history_sha256"]:
            raise ValueError("decision history does not match the registered source lineage")
        if source.decision_id not in registry_candidate.source_decision_ids:
            raise ValueError("decision is not bound into the active registered Profile")
        matches = tuple(entry for entry in decisions.entries if entry.decision_id == source.decision_id)
        if len(matches) != 1 or matches[0].decision is not HumanDecision.ADOPTED:
            raise ValueError("source decision must be one exact ADOPTED decision")
        entry = matches[0]
        candidate = entry.candidate
        if candidate["state"] != OwnerDecisionState.READY_FOR_HUMAN_REVIEW.value:
            raise ValueError("source decision candidate is not review-ready")
        profile = registry_candidate.profile_snapshot
        matched_rules = tuple(rule for rule in profile.rules if rule.feature_key == feature_key)
        if len(matched_rules) != 1:
            raise ValueError("feature rule is absent from the active registered Profile")

        owners.add(registry.owner_scope_sha256)
        rules.append(matched_rules[0])
        hypotheses.add(candidate["hypothesis_id"])
        actions.add(candidate["action_type"])
        conditions.add(candidate["condition_fingerprint_sha256"])
        for evidence in candidate["source_evidence_sha256s"]:
            _sha256(evidence, "source_evidence_sha256")
            if evidence in source_evidence_hashes:
                raise ValueError("source evidence replay across Owners is not allowed")
            source_evidence_hashes.add(evidence)
        supplied_evidence = tuple(row.to_dict()["evidence_sha256"] for row in source.evidence)
        if supplied_evidence != tuple(sorted(candidate["source_evidence_sha256s"])):
            raise ValueError("supplied Human Action Evidence does not match the decision")
        if any(row.owner_scope_sha256 != registry.owner_scope_sha256 for row in source.evidence):
            raise ValueError("Human Action Evidence owner scope mismatch")
        projects.update(row.project_scope_sha256 for row in source.evidence)
        benefit = candidate["weighted_benefit_milli"]
        if not isinstance(benefit, int) or isinstance(benefit, bool):
            raise ValueError("source decision weighted benefit is unavailable")
        per_owner_benefits.append(benefit)
        for metric in candidate["metric_evaluations"]:
            if metric["validity"] != EvidenceValidity.CURRENT_VALID.value:
                raise ValueError("source metric validity is not current")
            metric_rows[metric["metric_id"]].append((metric["delta_milli"], metric["sample_count"]))

        coordinate_body = {
            "candidate_id": candidate_id,
            "feature_key": feature_key,
            "registry_history_sha256": registry.to_dict()["history_sha256"],
            "registry_revision_sha256": latest.to_dict()["revision_sha256"],
            "decision_history_sha256": decision_payload["history_sha256"],
            "decision_entry_sha256": entry.to_dict()["entry_sha256"],
            "decision_candidate_sha256": candidate["candidate_sha256"],
            "profile_sha256": profile.to_dict()["profile_sha256"],
        }
        source_coordinates.append(sha256_bytes(canonical_json_bytes(coordinate_body)))

    if len(hypotheses) != 1 or len(actions) != 1 or len(conditions) != 1:
        raise ValueError("source hypothesis, action, and condition must match exactly")
    first_rule = rules[0]
    if any(rule != first_rule for rule in rules[1:]):
        raise ValueError("active registered feature rules must match exactly")
    metrics = tuple(
        AggregatedMetricEvaluation(
            metric_id,
            min(delta for delta, _ in metric_rows[metric_id]),
            sum(samples for _, samples in metric_rows[metric_id]),
            len(metric_rows[metric_id]),
        )
        for metric_id in _METRIC_IDS
    )
    minimum_benefit = min(per_owner_benefits)
    state = _classify(
        owner_count=len(owners), project_count=len(projects), metrics=metrics,
        minimum_benefit=minimum_benefit, policy=policy,
    )
    return KnowledgePackPromotionCandidate(
        candidate_id, first_rule, next(iter(hypotheses)), next(iter(actions)),
        next(iter(conditions)), tuple(sorted(source_coordinates)), len(owners), len(projects),
        len(source_evidence_hashes), metrics, minimum_benefit, policy, state,
    )


def verify_knowledge_pack_promotion_candidate(
    payload: Mapping[str, Any], candidate_id: str, feature_key: str,
    sources: Iterable[KnowledgePackSource], policy: KnowledgePackCandidatePolicy,
) -> None:
    expected = compile_knowledge_pack_promotion_candidate(
        candidate_id, feature_key, sources, policy
    ).to_dict()
    if not isinstance(payload, Mapping) or dict(payload) != expected:
        raise ValueError("knowledge pack candidate does not match exact current sources")


__all__ = [
    "AggregatedMetricEvaluation",
    "KNOWLEDGE_PACK_CANDIDATE_VERSION",
    "KnowledgePackCandidatePolicy",
    "KnowledgePackCandidateState",
    "KnowledgePackPromotionCandidate",
    "KnowledgePackSource",
    "compile_knowledge_pack_promotion_candidate",
    "verify_knowledge_pack_promotion_candidate",
]
