"""TASK-029 R0 pure Human Action Evidence and Owner Decision candidates.

The module accepts already-admitted, body-free Product evidence and creates
deterministic advisory records.  It has no persistence, network, media,
provider, profile-write, promotion, rollback, or external-effect surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Iterable, Mapping

from .montage_contracts import admit_montage_human_edit_evidence
from .multimodal_scoring import EvidenceValidity
from .serialization import canonical_json_bytes, sha256_bytes


_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_STABLE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_TASK_ID_RE = re.compile(r"^TASK-[0-9]{3}$")
_MAX_EVIDENCE = 256
_METRIC_IDS = (
    "human_acceptance",
    "qa_compliance",
    "quality_improvement",
    "rework_reduction",
    "sample_confidence",
    "time_reduction",
)


def _sha256(value: str, name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{name} must be sha256:<64 lowercase hex>")
    return value


def _stable_id(value: str, name: str) -> str:
    if not isinstance(value, str) or not _STABLE_ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _bounded_int(value: int, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in {minimum}..{maximum}")
    return value


def _sorted_unique(values: tuple[str, ...], name: str, maximum: int) -> None:
    if not values or len(values) > maximum:
        raise ValueError(f"{name} must contain 1..{maximum} items")
    if values != tuple(sorted(set(values))):
        raise ValueError(f"{name} must be sorted and unique")
    for value in values:
        _stable_id(value, name)


def _verify_hash(value: Mapping[str, Any], field: str) -> None:
    body = dict(value)
    supplied = body.pop(field, None)
    _sha256(supplied, field)
    expected = sha256_bytes(canonical_json_bytes(body))
    if supplied != expected:
        raise ValueError(f"{field} mismatch")


class HumanDisposition(str, Enum):
    ACCEPTED_AS_PROPOSED = "ACCEPTED_AS_PROPOSED"
    MODIFIED = "MODIFIED"
    REJECTED = "REJECTED"
    UNDONE = "UNDONE"
    REVISED_AFTER_ACCEPTANCE = "REVISED_AFTER_ACCEPTANCE"


class HardGateState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class EvidenceAdmissionState(str, Enum):
    ELIGIBLE_FOR_EVALUATION = "ELIGIBLE_FOR_EVALUATION"
    DO_NOT_LEARN = "DO_NOT_LEARN"
    IMMEDIATE_UNDO = "IMMEDIATE_UNDO"
    LATER_REVISION = "LATER_REVISION"
    SAFETY_BLOCKED = "SAFETY_BLOCKED"
    RIGHTS_BLOCKED = "RIGHTS_BLOCKED"
    UNKNOWN_EVIDENCE = "UNKNOWN_EVIDENCE"
    STALE_OR_REVOKED_EVIDENCE = "STALE_OR_REVOKED_EVIDENCE"


class OwnerDecisionState(str, Enum):
    READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    EXCLUDED_EVIDENCE_PRESENT = "EXCLUDED_EVIDENCE_PRESENT"
    CONFLICTING_CONTEXT = "CONFLICTING_CONTEXT"
    UNKNOWN_EVIDENCE = "UNKNOWN_EVIDENCE"
    STALE_OR_REVOKED_EVIDENCE = "STALE_OR_REVOKED_EVIDENCE"
    SAFETY_OR_RIGHTS_BLOCKED = "SAFETY_OR_RIGHTS_BLOCKED"
    AXIS_REGRESSION = "AXIS_REGRESSION"
    NO_MEASURED_BENEFIT = "NO_MEASURED_BENEFIT"


@dataclass(frozen=True, slots=True)
class HumanActionEvidence:
    evidence_id: str
    owner_scope_sha256: str
    project_scope_sha256: str
    producer_task_id: str
    source_record_sha256: str
    action_type: str
    condition_keys: tuple[str, ...]
    before_snapshot_sha256: str
    proposed_snapshot_sha256: str | None
    final_snapshot_sha256: str | None
    disposition: HumanDisposition
    validity: EvidenceValidity
    do_not_learn: bool
    immediate_undo: bool
    later_revision: bool
    safety_state: HardGateState
    rights_state: HardGateState
    observed_at_epoch_ms: int
    work_duration_ms: int | None = None

    def __post_init__(self) -> None:
        _stable_id(self.evidence_id, "evidence_id")
        _sha256(self.owner_scope_sha256, "owner_scope_sha256")
        _sha256(self.project_scope_sha256, "project_scope_sha256")
        if not isinstance(self.producer_task_id, str) or not _TASK_ID_RE.fullmatch(
            self.producer_task_id
        ):
            raise ValueError("producer_task_id must be TASK-<3 digits>")
        _sha256(self.source_record_sha256, "source_record_sha256")
        _stable_id(self.action_type, "action_type")
        _sorted_unique(self.condition_keys, "condition_keys", 32)
        _sha256(self.before_snapshot_sha256, "before_snapshot_sha256")
        if self.proposed_snapshot_sha256 is not None:
            _sha256(self.proposed_snapshot_sha256, "proposed_snapshot_sha256")
        if self.final_snapshot_sha256 is not None:
            _sha256(self.final_snapshot_sha256, "final_snapshot_sha256")
        if not isinstance(self.disposition, HumanDisposition):
            raise ValueError("disposition must be a HumanDisposition")
        if not isinstance(self.validity, EvidenceValidity):
            raise ValueError("validity must be an EvidenceValidity")
        if not all(
            isinstance(value, bool)
            for value in (self.do_not_learn, self.immediate_undo, self.later_revision)
        ):
            raise ValueError("learning exclusion flags must be booleans")
        if not isinstance(self.safety_state, HardGateState) or not isinstance(
            self.rights_state, HardGateState
        ):
            raise ValueError("safety_state and rights_state must be HardGateState")
        _bounded_int(self.observed_at_epoch_ms, "observed_at_epoch_ms", 0, 2**63 - 1)
        if self.work_duration_ms is not None:
            _bounded_int(self.work_duration_ms, "work_duration_ms", 0, 7 * 24 * 60 * 60 * 1000)
        if self.immediate_undo != (self.disposition is HumanDisposition.UNDONE):
            raise ValueError("immediate_undo must exactly match UNDONE disposition")
        if self.later_revision != (
            self.disposition is HumanDisposition.REVISED_AFTER_ACCEPTANCE
        ):
            raise ValueError("later_revision must exactly match REVISED_AFTER_ACCEPTANCE")
        if self.disposition is HumanDisposition.REJECTED and self.final_snapshot_sha256 is not None:
            raise ValueError("REJECTED evidence cannot claim a final snapshot")
        if self.disposition is not HumanDisposition.REJECTED and self.final_snapshot_sha256 is None:
            raise ValueError("non-REJECTED evidence requires a final snapshot")

    @property
    def admission_state(self) -> EvidenceAdmissionState:
        if self.validity is EvidenceValidity.UNKNOWN:
            return EvidenceAdmissionState.UNKNOWN_EVIDENCE
        if self.validity in (EvidenceValidity.STALE, EvidenceValidity.REVOKED):
            return EvidenceAdmissionState.STALE_OR_REVOKED_EVIDENCE
        if self.safety_state is not HardGateState.PASS:
            return EvidenceAdmissionState.SAFETY_BLOCKED
        if self.rights_state is not HardGateState.PASS:
            return EvidenceAdmissionState.RIGHTS_BLOCKED
        if self.do_not_learn:
            return EvidenceAdmissionState.DO_NOT_LEARN
        if self.immediate_undo:
            return EvidenceAdmissionState.IMMEDIATE_UNDO
        if self.later_revision:
            return EvidenceAdmissionState.LATER_REVISION
        return EvidenceAdmissionState.ELIGIBLE_FOR_EVALUATION

    @property
    def condition_fingerprint_sha256(self) -> str:
        return sha256_bytes(
            canonical_json_bytes(
                {"action_type": self.action_type, "condition_keys": list(self.condition_keys)}
            )
        )

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "record_version": "1.0.0",
            "record_type": "HUMAN_ACTION_EVIDENCE",
            "task_owner": "TASK-029",
            "evidence_id": self.evidence_id,
            "owner_scope_sha256": self.owner_scope_sha256,
            "project_scope_sha256": self.project_scope_sha256,
            "producer_task_id": self.producer_task_id,
            "source_record_sha256": self.source_record_sha256,
            "action_type": self.action_type,
            "condition_keys": list(self.condition_keys),
            "condition_fingerprint_sha256": self.condition_fingerprint_sha256,
            "before_snapshot_sha256": self.before_snapshot_sha256,
            "proposed_snapshot_sha256": self.proposed_snapshot_sha256,
            "final_snapshot_sha256": self.final_snapshot_sha256,
            "disposition": self.disposition.value,
            "validity": self.validity.value,
            "do_not_learn": self.do_not_learn,
            "immediate_undo": self.immediate_undo,
            "later_revision": self.later_revision,
            "safety_state": self.safety_state.value,
            "rights_state": self.rights_state.value,
            "admission_state": self.admission_state.value,
            "observed_at_epoch_ms": self.observed_at_epoch_ms,
            "work_duration_ms": self.work_duration_ms,
            "raw_media_included": False,
            "text_body_included": False,
            "absolute_host_path_included": False,
            "credential_included": False,
            "automatic_learning_promotion_authorized": False,
            "external_effect_authorized": False,
        }
        body["evidence_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(frozen=True, slots=True, order=True)
class MetricEvaluation:
    metric_id: str
    baseline_milli: int
    observed_milli: int
    sample_count: int
    validity: EvidenceValidity

    def __post_init__(self) -> None:
        if self.metric_id not in _METRIC_IDS:
            raise ValueError("metric_id is not a TASK-029 R0 axis")
        _bounded_int(self.baseline_milli, "baseline_milli", 0, 1000)
        _bounded_int(self.observed_milli, "observed_milli", 0, 1000)
        _bounded_int(self.sample_count, "sample_count", 1, 1_000_000_000)
        if not isinstance(self.validity, EvidenceValidity):
            raise ValueError("validity must be an EvidenceValidity")

    @property
    def delta_milli(self) -> int:
        return self.observed_milli - self.baseline_milli

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "baseline_milli": self.baseline_milli,
            "observed_milli": self.observed_milli,
            "delta_milli": self.delta_milli,
            "sample_count": self.sample_count,
            "validity": self.validity.value,
        }


@dataclass(frozen=True, slots=True)
class OwnerLearningPolicy:
    policy_id: str
    policy_version: str
    minimum_evidence_records: int
    minimum_samples_per_axis: int
    minimum_weighted_benefit_milli: int
    maximum_axis_regression_milli: int

    def __post_init__(self) -> None:
        _stable_id(self.policy_id, "policy_id")
        if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", self.policy_version):
            raise ValueError("policy_version must be semantic version x.y.z")
        _bounded_int(self.minimum_evidence_records, "minimum_evidence_records", 1, _MAX_EVIDENCE)
        _bounded_int(self.minimum_samples_per_axis, "minimum_samples_per_axis", 1, 1_000_000_000)
        _bounded_int(
            self.minimum_weighted_benefit_milli,
            "minimum_weighted_benefit_milli",
            0,
            1000,
        )
        _bounded_int(
            self.maximum_axis_regression_milli,
            "maximum_axis_regression_milli",
            0,
            1000,
        )

    def to_dict(self) -> dict[str, Any]:
        body = {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "minimum_evidence_records": self.minimum_evidence_records,
            "minimum_samples_per_axis": self.minimum_samples_per_axis,
            "minimum_weighted_benefit_milli": self.minimum_weighted_benefit_milli,
            "maximum_axis_regression_milli": self.maximum_axis_regression_milli,
        }
        body["policy_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(frozen=True, slots=True)
class OwnerDecisionCandidate:
    candidate_id: str
    owner_scope_sha256: str
    hypothesis_id: str
    evidence: tuple[HumanActionEvidence, ...]
    metrics: tuple[MetricEvaluation, ...]
    policy: OwnerLearningPolicy
    state: OwnerDecisionState
    weighted_benefit_milli: int | None
    regressed_metric_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _stable_id(self.candidate_id, "candidate_id")
        _sha256(self.owner_scope_sha256, "owner_scope_sha256")
        _stable_id(self.hypothesis_id, "hypothesis_id")
        if not self.evidence or len(self.evidence) > _MAX_EVIDENCE:
            raise ValueError(f"evidence must contain 1..{_MAX_EVIDENCE} records")
        if self.evidence != tuple(sorted(self.evidence, key=lambda row: row.evidence_id)):
            raise ValueError("evidence must be sorted by evidence_id")
        if len({row.evidence_id for row in self.evidence}) != len(self.evidence):
            raise ValueError("evidence_id must be unique")
        evidence_hashes = [row.to_dict()["evidence_sha256"] for row in self.evidence]
        if len(set(evidence_hashes)) != len(evidence_hashes):
            raise ValueError("evidence_sha256 must be unique")
        if any(row.owner_scope_sha256 != self.owner_scope_sha256 for row in self.evidence):
            raise ValueError("evidence owner scope mismatch")
        if self.metrics != tuple(sorted(self.metrics, key=lambda row: row.metric_id)):
            raise ValueError("metrics must be sorted by metric_id")
        if tuple(row.metric_id for row in self.metrics) != _METRIC_IDS:
            raise ValueError("all six TASK-029 R0 metric axes are required exactly once")
        if not isinstance(self.policy, OwnerLearningPolicy):
            raise ValueError("policy must be an OwnerLearningPolicy")
        expected = _classify_candidate(self.evidence, self.metrics, self.policy)
        if (self.state, self.weighted_benefit_milli, self.regressed_metric_ids) != expected:
            raise ValueError("candidate state does not match its constituents")

    def to_dict(self) -> dict[str, Any]:
        first = self.evidence[0]
        body: dict[str, Any] = {
            "record_version": "1.0.0",
            "record_type": "OWNER_DECISION_CANDIDATE",
            "task_owner": "TASK-029",
            "candidate_id": self.candidate_id,
            "owner_scope_sha256": self.owner_scope_sha256,
            "hypothesis_id": self.hypothesis_id,
            "action_type": first.action_type,
            "condition_fingerprint_sha256": first.condition_fingerprint_sha256,
            "source_evidence_sha256s": [row.to_dict()["evidence_sha256"] for row in self.evidence],
            "source_producer_task_ids": sorted({row.producer_task_id for row in self.evidence}),
            "metric_evaluations": [row.to_dict() for row in self.metrics],
            "learning_policy": self.policy.to_dict(),
            "state": self.state.value,
            "weighted_benefit_milli": self.weighted_benefit_milli,
            "regressed_metric_ids": list(self.regressed_metric_ids),
            "human_review_required": True,
            "owner_profile_write_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "cloud_telemetry_authorized": False,
            "automatic_rollback_authorized": False,
            "edit_plan_mutation_authorized": False,
            "external_effect_authorized": False,
        }
        body["candidate_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


def _classify_candidate(
    evidence: tuple[HumanActionEvidence, ...],
    metrics: tuple[MetricEvaluation, ...],
    policy: OwnerLearningPolicy,
) -> tuple[OwnerDecisionState, int | None, tuple[str, ...]]:
    validity = {row.validity for row in (*evidence, *metrics)}
    if EvidenceValidity.UNKNOWN in validity:
        return OwnerDecisionState.UNKNOWN_EVIDENCE, None, ()
    if EvidenceValidity.STALE in validity or EvidenceValidity.REVOKED in validity:
        return OwnerDecisionState.STALE_OR_REVOKED_EVIDENCE, None, ()
    states = {row.admission_state for row in evidence}
    if EvidenceAdmissionState.SAFETY_BLOCKED in states or EvidenceAdmissionState.RIGHTS_BLOCKED in states:
        return OwnerDecisionState.SAFETY_OR_RIGHTS_BLOCKED, None, ()
    if states != {EvidenceAdmissionState.ELIGIBLE_FOR_EVALUATION}:
        return OwnerDecisionState.EXCLUDED_EVIDENCE_PRESENT, None, ()
    contexts = {(row.action_type, row.condition_fingerprint_sha256) for row in evidence}
    if len(contexts) != 1:
        return OwnerDecisionState.CONFLICTING_CONTEXT, None, ()
    if len(evidence) < policy.minimum_evidence_records or any(
        row.sample_count < policy.minimum_samples_per_axis for row in metrics
    ):
        return OwnerDecisionState.INSUFFICIENT_EVIDENCE, None, ()
    regressed = tuple(
        row.metric_id
        for row in metrics
        if row.delta_milli < -policy.maximum_axis_regression_milli
    )
    total_samples = sum(row.sample_count for row in metrics)
    weighted = sum(row.delta_milli * row.sample_count for row in metrics) // total_samples
    if regressed:
        return OwnerDecisionState.AXIS_REGRESSION, weighted, regressed
    if weighted < policy.minimum_weighted_benefit_milli:
        return OwnerDecisionState.NO_MEASURED_BENEFIT, weighted, ()
    return OwnerDecisionState.READY_FOR_HUMAN_REVIEW, weighted, ()


def compile_owner_decision_candidate(
    candidate_id: str,
    owner_scope_sha256: str,
    hypothesis_id: str,
    evidence: Iterable[HumanActionEvidence],
    metrics: Iterable[MetricEvaluation],
    policy: OwnerLearningPolicy,
) -> OwnerDecisionCandidate:
    evidence_rows = tuple(sorted(tuple(evidence), key=lambda row: row.evidence_id))
    metric_rows = tuple(sorted(tuple(metrics), key=lambda row: row.metric_id))
    if not evidence_rows or len(evidence_rows) > _MAX_EVIDENCE:
        raise ValueError(f"evidence must contain 1..{_MAX_EVIDENCE} records")
    if not all(isinstance(row, HumanActionEvidence) for row in evidence_rows):
        raise ValueError("evidence must contain HumanActionEvidence records")
    if tuple(row.metric_id for row in metric_rows) != _METRIC_IDS:
        raise ValueError("all six TASK-029 R0 metric axes are required exactly once")
    if not all(isinstance(row, MetricEvaluation) for row in metric_rows):
        raise ValueError("metrics must contain MetricEvaluation records")
    if not isinstance(policy, OwnerLearningPolicy):
        raise ValueError("policy must be an OwnerLearningPolicy")
    state, weighted, regressed = _classify_candidate(evidence_rows, metric_rows, policy)
    return OwnerDecisionCandidate(
        candidate_id,
        owner_scope_sha256,
        hypothesis_id,
        evidence_rows,
        metric_rows,
        policy,
        state,
        weighted,
        regressed,
    )


def compile_montage_human_action_evidence(
    *,
    evidence_id: str,
    owner_scope_sha256: str,
    project_scope_sha256: str,
    proposal: Mapping[str, Any],
    approved_plan: Mapping[str, Any],
    montage_evidence: Mapping[str, Any],
    observed_at_epoch_ms: int,
    validity: EvidenceValidity = EvidenceValidity.CURRENT_VALID,
    safety_state: HardGateState = HardGateState.PASS,
    rights_state: HardGateState = HardGateState.PASS,
    immediate_undo: bool = False,
    later_revision: bool = False,
    work_duration_ms: int | None = None,
) -> HumanActionEvidence:
    """Admit TASK-055 evidence without copying media, text, or host paths."""

    source = admit_montage_human_edit_evidence(
        proposal, approved_plan, montage_evidence
    ).to_dict()
    disposition = {
        "UNCHANGED": HumanDisposition.ACCEPTED_AS_PROPOSED,
        "MOVED": HumanDisposition.MODIFIED,
        "DELETED": HumanDisposition.REJECTED,
    }[source["disposition"]]
    if immediate_undo and later_revision:
        raise ValueError("immediate_undo and later_revision are mutually exclusive")
    if immediate_undo:
        disposition = HumanDisposition.UNDONE
    elif later_revision:
        disposition = HumanDisposition.REVISED_AFTER_ACCEPTANCE
    condition_keys = {
        f"anchor:{source['music_anchor_kind'].lower()}",
        f"event:{source['event_type']}",
        f"style:{source['style_profile_id']}",
        *(f"preset:{value}" for value in source["preset_families"]),
    }
    return HumanActionEvidence(
        evidence_id=evidence_id,
        owner_scope_sha256=owner_scope_sha256,
        project_scope_sha256=project_scope_sha256,
        producer_task_id="TASK-055",
        source_record_sha256=source["evidence_sha256"],
        action_type="montage.timing",
        condition_keys=tuple(sorted(condition_keys)),
        before_snapshot_sha256=source["source_proposal_sha256"],
        proposed_snapshot_sha256=source["source_approved_plan_sha256"],
        final_snapshot_sha256=(
            None if disposition is HumanDisposition.REJECTED else source["evidence_sha256"]
        ),
        disposition=disposition,
        validity=validity,
        do_not_learn=source["do_not_learn"],
        immediate_undo=immediate_undo,
        later_revision=later_revision,
        safety_state=safety_state,
        rights_state=rights_state,
        observed_at_epoch_ms=observed_at_epoch_ms,
        work_duration_ms=work_duration_ms,
    )


def verify_human_action_evidence_hash(value: Mapping[str, Any]) -> None:
    _verify_hash(value, "evidence_sha256")
    try:
        reconstructed = HumanActionEvidence(
            evidence_id=value["evidence_id"],
            owner_scope_sha256=value["owner_scope_sha256"],
            project_scope_sha256=value["project_scope_sha256"],
            producer_task_id=value["producer_task_id"],
            source_record_sha256=value["source_record_sha256"],
            action_type=value["action_type"],
            condition_keys=tuple(value["condition_keys"]),
            before_snapshot_sha256=value["before_snapshot_sha256"],
            proposed_snapshot_sha256=value["proposed_snapshot_sha256"],
            final_snapshot_sha256=value["final_snapshot_sha256"],
            disposition=HumanDisposition(value["disposition"]),
            validity=EvidenceValidity(value["validity"]),
            do_not_learn=value["do_not_learn"],
            immediate_undo=value["immediate_undo"],
            later_revision=value["later_revision"],
            safety_state=HardGateState(value["safety_state"]),
            rights_state=HardGateState(value["rights_state"]),
            observed_at_epoch_ms=value["observed_at_epoch_ms"],
            work_duration_ms=value["work_duration_ms"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("human action evidence constituents are invalid") from exc
    if reconstructed.to_dict() != dict(value):
        raise ValueError("human action evidence derived fields or authority flags mismatch")

def verify_owner_decision_candidate_hash(value: Mapping[str, Any]) -> None:
    _verify_hash(value, "candidate_sha256")
    policy = value.get("learning_policy")
    if not isinstance(policy, Mapping):
        raise ValueError("learning_policy must be an object")
    _verify_hash(policy, "policy_sha256")
    metric_ids: list[str] = []
    for row in value.get("metric_evaluations", ()):
        if not isinstance(row, Mapping):
            raise ValueError("metric_evaluations must contain objects")
        baseline = row.get("baseline_milli")
        observed = row.get("observed_milli")
        if not isinstance(baseline, int) or isinstance(baseline, bool):
            raise ValueError("metric baseline must be an integer")
        if not isinstance(observed, int) or isinstance(observed, bool):
            raise ValueError("metric observed value must be an integer")
        if row.get("delta_milli") != observed - baseline:
            raise ValueError("metric delta mismatch")
        metric_ids.append(row.get("metric_id"))
    if tuple(metric_ids) != _METRIC_IDS:
        raise ValueError("metric axes must be sorted and complete")
    if value.get("human_review_required") is not True:
        raise ValueError("human_review_required must remain true")
    for field in (
        "owner_profile_write_authorized",
        "knowledge_pack_promotion_authorized",
        "cloud_telemetry_authorized",
        "automatic_rollback_authorized",
        "edit_plan_mutation_authorized",
        "external_effect_authorized",
    ):
        if value.get(field) is not False:
            raise ValueError(f"{field} must remain false")


__all__ = [
    "EvidenceAdmissionState",
    "HardGateState",
    "HumanActionEvidence",
    "HumanDisposition",
    "MetricEvaluation",
    "OwnerDecisionCandidate",
    "OwnerDecisionState",
    "OwnerLearningPolicy",
    "compile_montage_human_action_evidence",
    "compile_owner_decision_candidate",
    "verify_human_action_evidence_hash",
    "verify_owner_decision_candidate_hash",
]
