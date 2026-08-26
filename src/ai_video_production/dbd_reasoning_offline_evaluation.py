from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Mapping

from .dbd_reasoning_dataset_leakage import (
    DbDReasoningDatasetLeakageReport,
    LeakageAuditStatus,
    admit_dbd_reasoning_dataset_leakage_report,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


EVALUATION_VERSION = "1.0.0"
RECORD_KIND = "DBD_REASONING_OFFLINE_EVALUATION_REPORT"
EVALUATION_STATE = "EVIDENCE_ONLY_NO_PROMOTION"
MIN_SCHEMA_VALID_MILLI = 995
MIN_REPLAY_STABILITY_MILLI = 950
MIN_SAFE_NEGATIVE_ABSTENTION_MILLI = 950
CANONICAL_EVALUATION_SEEDS = (104729, 130363, 155921)
MAX_SAMPLE_COUNT = 20_000
MAX_REPORT_CANONICAL_BYTES = 512 * 1024
_BINDING_REF_RE = re.compile(
    r"^(?:baseline|generic|model-quarantine)://[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$"
)
_ARM_BINDING_SCHEMES = {
    "BASELINE": "baseline://",
    "GENERIC": "generic://",
    "TUNED": "model-quarantine://",
}


class OfflineEvaluationArm(str, Enum):
    BASELINE = "BASELINE"
    GENERIC = "GENERIC"
    TUNED = "TUNED"


class OfflineGateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_CONFIRMED = "NOT_CONFIRMED"


@dataclass(frozen=True, slots=True)
class OfflineArmEvidence:
    arm: OfflineEvaluationArm
    binding_ref: str
    binding_sha256: str
    output_evidence_set_sha256: str
    sample_count: int
    observation_count: int
    schema_valid_count: int
    unsupported_admitted_fact_count: int
    patch_incompatible_claim_count: int
    citation_required_count: int
    citation_covered_count: int
    secret_pii_leak_count: int
    split_leakage_count: int
    replay_comparison_count: int
    replay_stable_count: int
    safe_negative_count: int
    safe_negative_abstained_count: int
    latency_p95_ms: int
    total_cost_milli: int
    peak_memory_mib: int

    def __post_init__(self) -> None:
        if not isinstance(self.arm, OfflineEvaluationArm):
            raise ValueError("arm is invalid")
        if not isinstance(self.binding_ref, str) or not _BINDING_REF_RE.fullmatch(self.binding_ref):
            raise ValueError("binding_ref is invalid")
        _validate_arm_binding(self.arm, self.binding_ref)
        validate_sha256(self.binding_sha256, field_name="binding_sha256")
        validate_sha256(self.output_evidence_set_sha256, field_name="output_evidence_set_sha256")
        integer_fields = (
            "sample_count",
            "observation_count",
            "schema_valid_count",
            "unsupported_admitted_fact_count",
            "patch_incompatible_claim_count",
            "citation_required_count",
            "citation_covered_count",
            "secret_pii_leak_count",
            "split_leakage_count",
            "replay_comparison_count",
            "replay_stable_count",
            "safe_negative_count",
            "safe_negative_abstained_count",
            "latency_p95_ms",
            "total_cost_milli",
            "peak_memory_mib",
        )
        for name in integer_fields:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} is invalid")
        if not 1 <= self.sample_count <= MAX_SAMPLE_COUNT:
            raise ValueError("sample_count is outside the evaluation ceiling")
        for value, ceiling, name in (
            (self.schema_valid_count, self.observation_count, "schema_valid_count"),
            (self.citation_covered_count, self.citation_required_count, "citation_covered_count"),
            (self.replay_stable_count, self.replay_comparison_count, "replay_stable_count"),
            (self.safe_negative_count, self.observation_count, "safe_negative_count"),
            (
                self.safe_negative_abstained_count,
                self.safe_negative_count,
                "safe_negative_abstained_count",
            ),
        ):
            if value > ceiling:
                raise ValueError(f"{name} exceeds its denominator")

    def to_dict(self) -> dict[str, object]:
        return {
            "arm": self.arm.value,
            "binding_ref": self.binding_ref,
            "binding_sha256": self.binding_sha256,
            "output_evidence_set_sha256": self.output_evidence_set_sha256,
            "sample_count": self.sample_count,
            "observation_count": self.observation_count,
            "schema_valid_count": self.schema_valid_count,
            "unsupported_admitted_fact_count": self.unsupported_admitted_fact_count,
            "patch_incompatible_claim_count": self.patch_incompatible_claim_count,
            "citation_required_count": self.citation_required_count,
            "citation_covered_count": self.citation_covered_count,
            "secret_pii_leak_count": self.secret_pii_leak_count,
            "split_leakage_count": self.split_leakage_count,
            "replay_comparison_count": self.replay_comparison_count,
            "replay_stable_count": self.replay_stable_count,
            "safe_negative_count": self.safe_negative_count,
            "safe_negative_abstained_count": self.safe_negative_abstained_count,
            "latency_p95_ms": self.latency_p95_ms,
            "total_cost_milli": self.total_cost_milli,
            "peak_memory_mib": self.peak_memory_mib,
        }


@dataclass(frozen=True, slots=True)
class OfflineArmEvaluation:
    arm: OfflineEvaluationArm
    binding_ref: str
    binding_sha256: str
    output_evidence_set_sha256: str
    sample_count: int
    observation_count: int
    schema_valid_milli: int
    unsupported_admitted_fact_count: int
    patch_incompatible_claim_count: int
    citation_coverage_milli: int
    secret_pii_leak_count: int
    split_leakage_count: int
    replay_stability_milli: int
    safe_negative_abstention_milli: int | None
    latency_p95_ms: int
    total_cost_milli: int
    peak_memory_mib: int
    failure_codes: tuple[str, ...]
    status: OfflineGateStatus

    def __post_init__(self) -> None:
        if not isinstance(self.arm, OfflineEvaluationArm) or not isinstance(self.status, OfflineGateStatus):
            raise ValueError("evaluation enum is invalid")
        if not isinstance(self.binding_ref, str) or not _BINDING_REF_RE.fullmatch(self.binding_ref):
            raise ValueError("binding_ref is invalid")
        _validate_arm_binding(self.arm, self.binding_ref)
        validate_sha256(self.binding_sha256, field_name="binding_sha256")
        validate_sha256(self.output_evidence_set_sha256, field_name="output_evidence_set_sha256")
        for name in (
            "sample_count",
            "observation_count",
            "unsupported_admitted_fact_count",
            "patch_incompatible_claim_count",
            "secret_pii_leak_count",
            "split_leakage_count",
            "latency_p95_ms",
            "total_cost_milli",
            "peak_memory_mib",
        ):
            _validate_nonnegative_int(getattr(self, name), name)
        if not 1 <= self.sample_count <= MAX_SAMPLE_COUNT:
            raise ValueError("sample_count is outside the evaluation ceiling")
        if self.observation_count < self.sample_count:
            raise ValueError("observation_count cannot be smaller than sample_count")
        for name in ("schema_valid_milli", "citation_coverage_milli", "replay_stability_milli"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1000:
                raise ValueError(f"{name} is invalid")
        if self.safe_negative_abstention_milli is not None:
            if (
                isinstance(self.safe_negative_abstention_milli, bool)
                or not isinstance(self.safe_negative_abstention_milli, int)
                or not 0 <= self.safe_negative_abstention_milli <= 1000
            ):
                raise ValueError("safe_negative_abstention_milli is invalid")
        if not isinstance(self.failure_codes, tuple):
            raise ValueError("failure_codes must be a tuple")
        if any(not isinstance(code, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", code) for code in self.failure_codes):
            raise ValueError("failure_codes contain an invalid stable code")
        if self.failure_codes != tuple(sorted(set(self.failure_codes))):
            raise ValueError("failure_codes must be sorted and unique")
        expected_failures: list[str] = []
        if self.schema_valid_milli < MIN_SCHEMA_VALID_MILLI:
            expected_failures.append("SCHEMA_VALID_RATE_BELOW_GATE")
        if self.unsupported_admitted_fact_count:
            expected_failures.append("UNSUPPORTED_ADMITTED_FACT")
        if self.patch_incompatible_claim_count:
            expected_failures.append("PATCH_INCOMPATIBLE_CLAIM")
        if self.citation_coverage_milli < 1000:
            expected_failures.append("CITATION_COVERAGE_BELOW_GATE")
        if self.secret_pii_leak_count:
            expected_failures.append("SECRET_PII_LEAK")
        if self.split_leakage_count:
            expected_failures.append("SOURCE_SPLIT_LEAKAGE")
        if self.replay_stability_milli < MIN_REPLAY_STABILITY_MILLI:
            expected_failures.append("REPLAY_STABILITY_BELOW_GATE")
        if self.safe_negative_abstention_milli is not None and self.safe_negative_abstention_milli < MIN_SAFE_NEGATIVE_ABSTENTION_MILLI:
            expected_failures.append("SAFE_NEGATIVE_ABSTENTION_BELOW_GATE")
        if self.failure_codes != tuple(sorted(expected_failures)):
            raise ValueError("failure_codes do not match automated gate evidence")
        expected = (
            OfflineGateStatus.FAIL
            if self.failure_codes
            else OfflineGateStatus.NOT_CONFIRMED
            if self.safe_negative_abstention_milli is None
            else OfflineGateStatus.PASS
        )
        if self.status is not expected:
            raise ValueError("status does not match automated gate evidence")

    def to_dict(self) -> dict[str, object]:
        return {
            "arm": self.arm.value,
            "binding_ref": self.binding_ref,
            "binding_sha256": self.binding_sha256,
            "output_evidence_set_sha256": self.output_evidence_set_sha256,
            "sample_count": self.sample_count,
            "observation_count": self.observation_count,
            "schema_valid_milli": self.schema_valid_milli,
            "unsupported_admitted_fact_count": self.unsupported_admitted_fact_count,
            "patch_incompatible_claim_count": self.patch_incompatible_claim_count,
            "citation_coverage_milli": self.citation_coverage_milli,
            "secret_pii_leak_count": self.secret_pii_leak_count,
            "split_leakage_count": self.split_leakage_count,
            "replay_stability_milli": self.replay_stability_milli,
            "safe_negative_abstention_milli": self.safe_negative_abstention_milli,
            "latency_p95_ms": self.latency_p95_ms,
            "total_cost_milli": self.total_cost_milli,
            "peak_memory_mib": self.peak_memory_mib,
            "failure_codes": list(self.failure_codes),
            "status": self.status.value,
        }


@dataclass(frozen=True, slots=True)
class DbDReasoningOfflineEvaluationReport:
    leakage_report_sha256: str
    rights_manifest_sha256: str
    audited_segments_sha256: str
    test_sample_set_sha256: str
    seeds: tuple[int, ...]
    evaluations: tuple[OfflineArmEvaluation, ...]
    tuned_gate_status: OfflineGateStatus
    evaluation_state: str = EVALUATION_STATE

    def __post_init__(self) -> None:
        for name in (
            "leakage_report_sha256",
            "rights_manifest_sha256",
            "audited_segments_sha256",
            "test_sample_set_sha256",
        ):
            validate_sha256(getattr(self, name), field_name=name)
        _validate_seeds(self.seeds)
        if not isinstance(self.evaluations, tuple) or len(self.evaluations) != 3:
            raise ValueError("evaluations must contain exactly three arms")
        if any(not isinstance(item, OfflineArmEvaluation) for item in self.evaluations):
            raise ValueError("evaluations contain an invalid arm record")
        arms = tuple(item.arm for item in self.evaluations)
        if arms != tuple(OfflineEvaluationArm):
            raise ValueError("evaluations must use canonical BASELINE/GENERIC/TUNED order")
        if len({item.sample_count for item in self.evaluations}) != 1:
            raise ValueError("all evaluation arms must use the same sample count")
        expected_observations = self.evaluations[0].sample_count * len(self.seeds)
        if any(item.observation_count != expected_observations for item in self.evaluations):
            raise ValueError("evaluation observations do not cover every sample/seed")
        if not isinstance(self.tuned_gate_status, OfflineGateStatus):
            raise ValueError("tuned_gate_status is invalid")
        if self.tuned_gate_status is not self.evaluations[-1].status:
            raise ValueError("tuned_gate_status must equal the TUNED arm status")
        if self.evaluation_state != EVALUATION_STATE:
            raise ValueError("R4D cannot grant promotion authority")
        if len(canonical_json_bytes(self.to_dict())) > MAX_REPORT_CANONICAL_BYTES:
            raise ValueError("evaluation report exceeds the canonical byte ceiling")

    def to_dict(self) -> dict[str, object]:
        body = {
            "schema_version": EVALUATION_VERSION,
            "record_kind": RECORD_KIND,
            "leakage_report_sha256": self.leakage_report_sha256,
            "rights_manifest_sha256": self.rights_manifest_sha256,
            "audited_segments_sha256": self.audited_segments_sha256,
            "test_sample_set_sha256": self.test_sample_set_sha256,
            "seeds": list(self.seeds),
            "evaluations": [item.to_dict() for item in self.evaluations],
            "tuned_gate_status": self.tuned_gate_status.value,
            "evaluation_state": self.evaluation_state,
        }
        return {**body, "evaluation_report_sha256": sha256_bytes(canonical_json_bytes(body))}


class DbDReasoningOfflineEvaluationHarness:
    @staticmethod
    def evaluate(
        *,
        leakage_report: DbDReasoningDatasetLeakageReport,
        test_sample_set_sha256: str,
        seeds: tuple[int, ...],
        arms: tuple[OfflineArmEvidence, ...],
    ) -> DbDReasoningOfflineEvaluationReport:
        leakage_report = admit_dbd_reasoning_dataset_leakage_report(leakage_report.to_dict())
        if leakage_report.status is not LeakageAuditStatus.PASS:
            raise ValueError("R4D requires a PASS R4C leakage report")
        validate_sha256(test_sample_set_sha256, field_name="test_sample_set_sha256")
        _validate_seeds(seeds)
        if not isinstance(arms, tuple) or len(arms) != 3:
            raise ValueError("arms must contain exactly three evidence records")
        if any(not isinstance(item, OfflineArmEvidence) for item in arms):
            raise ValueError("arms contain an invalid evidence record")
        admitted = tuple(admit_offline_arm_evidence(item.to_dict()) for item in arms)
        if tuple(item.arm for item in admitted) != tuple(OfflineEvaluationArm):
            raise ValueError("arms must use canonical BASELINE/GENERIC/TUNED order")
        sample_counts = {item.sample_count for item in admitted}
        if len(sample_counts) != 1:
            raise ValueError("all arms must use the same test cohort")
        expected_observations = admitted[0].sample_count * len(seeds)
        expected_replays = admitted[0].sample_count * (len(seeds) - 1)
        for item in admitted:
            if item.observation_count != expected_observations:
                raise ValueError("observation_count does not cover every sample/seed")
            if item.replay_comparison_count != expected_replays:
                raise ValueError("replay comparisons do not cover every sample/seed")
        evaluations = tuple(_evaluate_arm(item) for item in admitted)
        record = leakage_report.to_dict()
        return DbDReasoningOfflineEvaluationReport(
            leakage_report_sha256=record["report_sha256"],
            rights_manifest_sha256=leakage_report.rights_manifest_sha256,
            audited_segments_sha256=leakage_report.audited_segments_sha256,
            test_sample_set_sha256=test_sample_set_sha256,
            seeds=seeds,
            evaluations=evaluations,
            tuned_gate_status=evaluations[-1].status,
        )


def admit_offline_arm_evidence(record: Mapping[str, Any]) -> OfflineArmEvidence:
    if not isinstance(record, Mapping):
        raise ValueError("arm evidence must be a mapping")
    expected = set(OfflineArmEvidence.__dataclass_fields__)
    if set(record) != expected:
        raise ValueError("arm evidence shape is invalid")
    values = dict(record)
    values["arm"] = OfflineEvaluationArm(values["arm"])
    evidence = OfflineArmEvidence(**values)
    if evidence.to_dict() != dict(record):
        raise ValueError("arm evidence is not canonical")
    return evidence


def admit_dbd_reasoning_offline_evaluation_report(
    record: Mapping[str, Any],
) -> DbDReasoningOfflineEvaluationReport:
    if not isinstance(record, Mapping):
        raise ValueError("evaluation report must be a mapping")
    expected = {
        "schema_version",
        "record_kind",
        "leakage_report_sha256",
        "rights_manifest_sha256",
        "audited_segments_sha256",
        "test_sample_set_sha256",
        "seeds",
        "evaluations",
        "tuned_gate_status",
        "evaluation_state",
        "evaluation_report_sha256",
    }
    if (
        set(record) != expected
        or record.get("schema_version") != EVALUATION_VERSION
        or record.get("record_kind") != RECORD_KIND
    ):
        raise ValueError("evaluation report shape or version is invalid")
    raw_seeds = record.get("seeds")
    raw_evaluations = record.get("evaluations")
    if not isinstance(raw_seeds, list) or not isinstance(raw_evaluations, list):
        raise ValueError("evaluation report arrays are invalid")
    evaluation_keys = set(OfflineArmEvaluation.__dataclass_fields__)
    evaluations: list[OfflineArmEvaluation] = []
    for raw in raw_evaluations:
        if not isinstance(raw, Mapping) or set(raw) != evaluation_keys:
            raise ValueError("arm evaluation shape is invalid")
        values = dict(raw)
        values["arm"] = OfflineEvaluationArm(values["arm"])
        values["status"] = OfflineGateStatus(values["status"])
        if not isinstance(values["failure_codes"], list):
            raise ValueError("failure_codes must be a list")
        values["failure_codes"] = tuple(values["failure_codes"])
        evaluations.append(OfflineArmEvaluation(**values))
    report = DbDReasoningOfflineEvaluationReport(
        leakage_report_sha256=record["leakage_report_sha256"],
        rights_manifest_sha256=record["rights_manifest_sha256"],
        audited_segments_sha256=record["audited_segments_sha256"],
        test_sample_set_sha256=record["test_sample_set_sha256"],
        seeds=tuple(raw_seeds),
        evaluations=tuple(evaluations),
        tuned_gate_status=OfflineGateStatus(record["tuned_gate_status"]),
        evaluation_state=record["evaluation_state"],
    )
    if report.to_dict() != dict(record):
        raise ValueError("evaluation report checksum or canonical representation is invalid")
    return report


def _validate_seeds(seeds: tuple[int, ...]) -> None:
    if (
        not isinstance(seeds, tuple)
        or seeds != CANONICAL_EVALUATION_SEEDS
        or any(isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**31 for seed in seeds)
    ):
        raise ValueError("seeds must equal the canonical R4D seed tuple")


def _validate_nonnegative_int(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} is invalid")


def _validate_arm_binding(arm: OfflineEvaluationArm, binding_ref: str) -> None:
    if not binding_ref.startswith(_ARM_BINDING_SCHEMES[arm.value]):
        raise ValueError("binding_ref scheme does not match arm")


def _ratio_milli(numerator: int, denominator: int, *, empty_value: int | None) -> int | None:
    if denominator == 0:
        return empty_value
    return numerator * 1000 // denominator


def _evaluate_arm(evidence: OfflineArmEvidence) -> OfflineArmEvaluation:
    schema_valid = _ratio_milli(evidence.schema_valid_count, evidence.observation_count, empty_value=0)
    citation_coverage = _ratio_milli(
        evidence.citation_covered_count, evidence.citation_required_count, empty_value=1000
    )
    replay_stability = _ratio_milli(
        evidence.replay_stable_count, evidence.replay_comparison_count, empty_value=0
    )
    safe_negative = _ratio_milli(
        evidence.safe_negative_abstained_count, evidence.safe_negative_count, empty_value=None
    )
    assert schema_valid is not None and citation_coverage is not None and replay_stability is not None
    failures: list[str] = []
    if schema_valid < MIN_SCHEMA_VALID_MILLI:
        failures.append("SCHEMA_VALID_RATE_BELOW_GATE")
    if evidence.unsupported_admitted_fact_count:
        failures.append("UNSUPPORTED_ADMITTED_FACT")
    if evidence.patch_incompatible_claim_count:
        failures.append("PATCH_INCOMPATIBLE_CLAIM")
    if citation_coverage < 1000:
        failures.append("CITATION_COVERAGE_BELOW_GATE")
    if evidence.secret_pii_leak_count:
        failures.append("SECRET_PII_LEAK")
    if evidence.split_leakage_count:
        failures.append("SOURCE_SPLIT_LEAKAGE")
    if replay_stability < MIN_REPLAY_STABILITY_MILLI:
        failures.append("REPLAY_STABILITY_BELOW_GATE")
    if safe_negative is not None and safe_negative < MIN_SAFE_NEGATIVE_ABSTENTION_MILLI:
        failures.append("SAFE_NEGATIVE_ABSTENTION_BELOW_GATE")
    failure_codes = tuple(sorted(failures))
    status = (
        OfflineGateStatus.FAIL
        if failure_codes
        else OfflineGateStatus.NOT_CONFIRMED
        if safe_negative is None
        else OfflineGateStatus.PASS
    )
    return OfflineArmEvaluation(
        arm=evidence.arm,
        binding_ref=evidence.binding_ref,
        binding_sha256=evidence.binding_sha256,
        output_evidence_set_sha256=evidence.output_evidence_set_sha256,
        sample_count=evidence.sample_count,
        observation_count=evidence.observation_count,
        schema_valid_milli=schema_valid,
        unsupported_admitted_fact_count=evidence.unsupported_admitted_fact_count,
        patch_incompatible_claim_count=evidence.patch_incompatible_claim_count,
        citation_coverage_milli=citation_coverage,
        secret_pii_leak_count=evidence.secret_pii_leak_count,
        split_leakage_count=evidence.split_leakage_count,
        replay_stability_milli=replay_stability,
        safe_negative_abstention_milli=safe_negative,
        latency_p95_ms=evidence.latency_p95_ms,
        total_cost_milli=evidence.total_cost_milli,
        peak_memory_mib=evidence.peak_memory_mib,
        failure_codes=failure_codes,
        status=status,
    )


__all__ = [
    "DbDReasoningOfflineEvaluationHarness",
    "DbDReasoningOfflineEvaluationReport",
    "CANONICAL_EVALUATION_SEEDS",
    "EVALUATION_STATE",
    "OfflineArmEvaluation",
    "OfflineArmEvidence",
    "OfflineEvaluationArm",
    "OfflineGateStatus",
    "admit_dbd_reasoning_offline_evaluation_report",
    "admit_offline_arm_evidence",
]
