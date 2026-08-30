"""TASK-054 R4E-B deterministic blind-review promotion-candidate report."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from itertools import combinations
import re
from typing import Any, Mapping

from .dbd_reasoning_blind_human_review import (
    BlindHumanReviewAuthorityBinding,
    BlindHumanReviewSubmission,
    BlindPreference,
    BlindReviewPresentation,
    BlindReviewRevealManifest,
    admit_blind_human_review_submission,
    admit_blind_review_presentation,
    admit_blind_review_reveal_manifest,
)
from .dbd_reasoning_offline_evaluation import (
    DbDReasoningOfflineEvaluationReport,
    OfflineEvaluationArm,
    OfflineGateStatus,
    admit_dbd_reasoning_offline_evaluation_report,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_VERSION = "1.0.0"
MIN_REVIEWERS = 2
MAX_REVIEWERS = 20
MAX_SAMPLES = 1_000
MIN_AGREEMENT_MILLI = 500
MAX_REPORT_BYTES = 512 * 1024
REPORT_STATE = "PROMOTION_CANDIDATE_ONLY_OWNER_DECISION_REQUIRED"
_REVIEWER_REF_RE = re.compile(r"reviewer://sha256/[0-9a-f]{64}")
_FINDING_RE = re.compile(r"[A-Z][A-Z0-9_]{1,63}")


class PromotionCandidateStatus(str, Enum):
    READY_FOR_OWNER_REVIEW = "READY_FOR_OWNER_REVIEW"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    NOT_CONFIRMED = "NOT_CONFIRMED"


@dataclass(frozen=True, slots=True)
class BlindReviewEvidence:
    submission: BlindHumanReviewSubmission
    authority_binding: BlindHumanReviewAuthorityBinding

    def __post_init__(self) -> None:
        if not isinstance(self.submission, BlindHumanReviewSubmission):
            raise ValueError("submission evidence is invalid")
        if not isinstance(self.authority_binding, BlindHumanReviewAuthorityBinding):
            raise ValueError("authority binding evidence is invalid")


@dataclass(frozen=True, slots=True)
class ArmHumanAggregate:
    arm: OfflineEvaluationArm
    observation_count: int
    factual_acceptable_count: int
    factual_acceptability_milli: int
    preference_count: int
    style_score_milli: int

    def __post_init__(self) -> None:
        if not isinstance(self.arm, OfflineEvaluationArm):
            raise ValueError("aggregate arm is invalid")
        for name in ("observation_count", "factual_acceptable_count", "preference_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} is invalid")
        if self.observation_count < 1:
            raise ValueError("aggregate requires observations")
        if self.factual_acceptable_count > self.observation_count:
            raise ValueError("factual acceptable count exceeds observations")
        if self.preference_count > self.observation_count:
            raise ValueError("preference count exceeds observations")
        for name in ("factual_acceptability_milli", "style_score_milli"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1000:
                raise ValueError(f"{name} is invalid")
        expected_factual = self.factual_acceptable_count * 1000 // self.observation_count
        if self.factual_acceptability_milli != expected_factual:
            raise ValueError("factual acceptability ratio is inconsistent")

    def to_dict(self) -> dict[str, object]:
        return {
            "arm": self.arm.value,
            "observation_count": self.observation_count,
            "factual_acceptable_count": self.factual_acceptable_count,
            "factual_acceptability_milli": self.factual_acceptability_milli,
            "preference_count": self.preference_count,
            "style_score_milli": self.style_score_milli,
        }


@dataclass(frozen=True, slots=True)
class DbDReasoningPromotionCandidateReport:
    offline_evaluation_report_sha256: str
    presentation_sha256: str
    reveal_manifest_sha256: str
    test_sample_set_sha256: str
    review_evidence_set_sha256: str
    evaluated_at: str
    reviewer_refs: tuple[str, ...]
    sample_count: int
    submission_count: int
    aggregates: tuple[ArmHumanAggregate, ...]
    preference_agreement_milli: int
    finding_codes: tuple[str, ...]
    status: PromotionCandidateStatus
    report_state: str = REPORT_STATE

    def __post_init__(self) -> None:
        for name in (
            "offline_evaluation_report_sha256",
            "presentation_sha256",
            "reveal_manifest_sha256",
            "test_sample_set_sha256",
            "review_evidence_set_sha256",
        ):
            validate_sha256(getattr(self, name), field_name=name)
        _utc(self.evaluated_at, "evaluated_at")
        _validate_reviewers(self.reviewer_refs)
        for name in ("sample_count", "submission_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} is invalid")
        if self.sample_count > MAX_SAMPLES:
            raise ValueError("sample_count exceeds the R4E bound")
        if self.submission_count != self.sample_count * len(self.reviewer_refs):
            raise ValueError("submission_count does not cover every sample/reviewer")
        if (
            not isinstance(self.aggregates, tuple)
            or len(self.aggregates) != 3
            or any(not isinstance(item, ArmHumanAggregate) for item in self.aggregates)
        ):
            raise ValueError("aggregates must contain exactly three arm records")
        if tuple(item.arm for item in self.aggregates) != tuple(OfflineEvaluationArm):
            raise ValueError("aggregates must use canonical BASELINE/GENERIC/TUNED order")
        if any(item.observation_count != self.submission_count for item in self.aggregates):
            raise ValueError("aggregate observations do not cover every submission")
        if (
            isinstance(self.preference_agreement_milli, bool)
            or not isinstance(self.preference_agreement_milli, int)
            or not 0 <= self.preference_agreement_milli <= 1000
        ):
            raise ValueError("preference_agreement_milli is invalid")
        if not isinstance(self.finding_codes, tuple):
            raise ValueError("finding_codes must be a tuple")
        if any(not isinstance(code, str) or not _FINDING_RE.fullmatch(code) for code in self.finding_codes):
            raise ValueError("finding_codes contain an invalid stable code")
        if self.finding_codes != tuple(sorted(set(self.finding_codes))):
            raise ValueError("finding_codes must be sorted and unique")
        expected_findings, expected_status = _decision(self.aggregates, self.preference_agreement_milli)
        if self.finding_codes != expected_findings or self.status is not expected_status:
            raise ValueError("promotion candidate decision does not match evidence")
        if self.report_state != REPORT_STATE:
            raise ValueError("R4E-B cannot grant promotion authority")
        if len(canonical_json_bytes(self.to_dict())) > MAX_REPORT_BYTES:
            raise ValueError("promotion candidate report exceeds canonical byte ceiling")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_kind": "DBD_REASONING_PROMOTION_CANDIDATE_REPORT",
            "offline_evaluation_report_sha256": self.offline_evaluation_report_sha256,
            "presentation_sha256": self.presentation_sha256,
            "reveal_manifest_sha256": self.reveal_manifest_sha256,
            "test_sample_set_sha256": self.test_sample_set_sha256,
            "review_evidence_set_sha256": self.review_evidence_set_sha256,
            "evaluated_at": self.evaluated_at,
            "reviewer_refs": list(self.reviewer_refs),
            "sample_count": self.sample_count,
            "submission_count": self.submission_count,
            "aggregates": [item.to_dict() for item in self.aggregates],
            "preference_agreement_milli": self.preference_agreement_milli,
            "finding_codes": list(self.finding_codes),
            "status": self.status.value,
            "report_state": self.report_state,
        }

    def to_dict(self) -> dict[str, object]:
        body = self._body()
        return {**body, "promotion_candidate_report_sha256": sha256_bytes(canonical_json_bytes(body))}


class DbDReasoningPromotionCandidateEvaluator:
    @staticmethod
    def evaluate(
        *,
        offline_report: DbDReasoningOfflineEvaluationReport,
        presentation: BlindReviewPresentation,
        reveal_manifest: BlindReviewRevealManifest,
        reviewer_refs: tuple[str, ...],
        evidence: tuple[BlindReviewEvidence, ...],
        evaluated_at: str,
    ) -> DbDReasoningPromotionCandidateReport:
        report = admit_dbd_reasoning_offline_evaluation_report(offline_report.to_dict())
        if report.tuned_gate_status is not OfflineGateStatus.PASS:
            raise ValueError("R4E-B requires a PASS TUNED R4D automated gate")
        presentation = admit_blind_review_presentation(presentation.to_dict())
        _validate_reviewers(reviewer_refs)
        if not isinstance(evidence, tuple) or any(not isinstance(item, BlindReviewEvidence) for item in evidence):
            raise ValueError("blind review evidence must be a tuple of valid pairs")

        admitted: list[BlindReviewEvidence] = []
        for item in evidence:
            submission = admit_blind_human_review_submission(
                item.submission.to_dict(),
                presentation=presentation,
                authority_record=item.authority_binding.to_dict(),
                evaluated_at=evaluated_at,
            )
            admitted.append(BlindReviewEvidence(submission, item.authority_binding))

        reveal = admit_blind_review_reveal_manifest(
            reveal_manifest.to_dict(),
            presentation=presentation,
            offline_report=report,
        )
        expected_coordinates = tuple(
            (sample.sample_ref, reviewer_ref)
            for sample in presentation.samples
            for reviewer_ref in reviewer_refs
        )
        coordinates = tuple(
            (item.submission.sample_ref, item.submission.reviewer_ref) for item in admitted
        )
        if coordinates != expected_coordinates:
            raise ValueError("blind submissions must exactly cover sorted sample/reviewer coordinates")
        confirmation_refs = tuple(item.authority_binding.confirmation_ref for item in admitted)
        confirmation_hashes = tuple(item.authority_binding.confirmation_sha256 for item in admitted)
        if len(set(confirmation_refs)) != len(confirmation_refs) or len(set(confirmation_hashes)) != len(confirmation_hashes):
            raise ValueError("one-shot Human confirmation was reused")

        label_arms = {
            sample.sample_ref: {mapping.label.value: mapping.arm for mapping in sample.mappings}
            for sample in reveal.samples
        }
        observations = len(admitted)
        facts = {arm: 0 for arm in OfflineEvaluationArm}
        preferences = {arm: 0 for arm in OfflineEvaluationArm}
        style_totals = {arm: 0 for arm in OfflineEvaluationArm}
        by_sample: dict[str, list[BlindPreference]] = {sample.sample_ref: [] for sample in presentation.samples}
        for item in admitted:
            submission = item.submission
            mapping = label_arms[submission.sample_ref]
            for score in submission.scores:
                arm = mapping[score.label.value]
                facts[arm] += int(score.factual_acceptable)
                style_totals[arm] += (
                    score.uncertainty_handling + score.usefulness + score.timing
                    + score.naturalness + score.density
                )
            if submission.preference is not BlindPreference.ALL_REJECTED:
                preferences[mapping[submission.preference.value]] += 1
            by_sample[submission.sample_ref].append(submission.preference)
        aggregates = tuple(
            ArmHumanAggregate(
                arm=arm,
                observation_count=observations,
                factual_acceptable_count=facts[arm],
                factual_acceptability_milli=facts[arm] * 1000 // observations,
                preference_count=preferences[arm],
                style_score_milli=style_totals[arm] * 1000 // (observations * 25),
            )
            for arm in OfflineEvaluationArm
        )
        agreeing_pairs = 0
        total_pairs = 0
        for choices in by_sample.values():
            for left, right in combinations(choices, 2):
                total_pairs += 1
                agreeing_pairs += int(left is right)
        agreement = agreeing_pairs * 1000 // total_pairs
        findings, status = _decision(aggregates, agreement)
        evidence_set_sha256 = sha256_bytes(canonical_json_bytes([
            {
                "submission": item.submission.to_dict(),
                "authority_binding": item.authority_binding.to_dict(),
            }
            for item in admitted
        ]))
        return DbDReasoningPromotionCandidateReport(
            offline_evaluation_report_sha256=report.to_dict()["evaluation_report_sha256"],
            presentation_sha256=presentation.to_dict()["presentation_sha256"],
            reveal_manifest_sha256=reveal.to_dict()["reveal_manifest_sha256"],
            test_sample_set_sha256=report.test_sample_set_sha256,
            review_evidence_set_sha256=evidence_set_sha256,
            evaluated_at=evaluated_at,
            reviewer_refs=reviewer_refs,
            sample_count=len(presentation.samples),
            submission_count=observations,
            aggregates=aggregates,
            preference_agreement_milli=agreement,
            finding_codes=findings,
            status=status,
        )


def admit_dbd_reasoning_promotion_candidate_report(
    record: Mapping[str, Any],
) -> DbDReasoningPromotionCandidateReport:
    expected = {
        "schema_version", "record_kind", "offline_evaluation_report_sha256",
        "presentation_sha256", "reveal_manifest_sha256", "test_sample_set_sha256",
        "review_evidence_set_sha256", "evaluated_at",
        "reviewer_refs", "sample_count", "submission_count", "aggregates",
        "preference_agreement_milli", "finding_codes", "status", "report_state",
        "promotion_candidate_report_sha256",
    }
    if not isinstance(record, Mapping) or set(record) != expected:
        raise ValueError("promotion candidate report shape is invalid")
    if record.get("schema_version") != SCHEMA_VERSION or record.get("record_kind") != "DBD_REASONING_PROMOTION_CANDIDATE_REPORT":
        raise ValueError("promotion candidate report version or kind is invalid")
    raw_reviewers = record.get("reviewer_refs")
    raw_aggregates = record.get("aggregates")
    raw_findings = record.get("finding_codes")
    if not isinstance(raw_reviewers, list) or not isinstance(raw_aggregates, list) or not isinstance(raw_findings, list):
        raise ValueError("promotion candidate report arrays are invalid")
    aggregates = []
    expected_aggregate = set(ArmHumanAggregate.__dataclass_fields__)
    for raw in raw_aggregates:
        if not isinstance(raw, Mapping) or set(raw) != expected_aggregate:
            raise ValueError("promotion candidate aggregate shape is invalid")
        values = dict(raw)
        values["arm"] = OfflineEvaluationArm(values["arm"])
        aggregates.append(ArmHumanAggregate(**values))
    report = DbDReasoningPromotionCandidateReport(
        offline_evaluation_report_sha256=record["offline_evaluation_report_sha256"],
        presentation_sha256=record["presentation_sha256"],
        reveal_manifest_sha256=record["reveal_manifest_sha256"],
        test_sample_set_sha256=record["test_sample_set_sha256"],
        review_evidence_set_sha256=record["review_evidence_set_sha256"],
        evaluated_at=record["evaluated_at"],
        reviewer_refs=tuple(raw_reviewers),
        sample_count=record["sample_count"],
        submission_count=record["submission_count"],
        aggregates=tuple(aggregates),
        preference_agreement_milli=record["preference_agreement_milli"],
        finding_codes=tuple(raw_findings),
        status=PromotionCandidateStatus(record["status"]),
        report_state=record["report_state"],
    )
    if report.to_dict() != dict(record):
        raise ValueError("promotion candidate report checksum or canonical form is invalid")
    return report


def _validate_reviewers(reviewer_refs: tuple[str, ...]) -> None:
    if not isinstance(reviewer_refs, tuple) or not MIN_REVIEWERS <= len(reviewer_refs) <= MAX_REVIEWERS:
        raise ValueError("reviewer cohort is outside bounds")
    if any(not isinstance(ref, str) or not _REVIEWER_REF_RE.fullmatch(ref) for ref in reviewer_refs):
        raise ValueError("reviewer cohort contains a non-canonical reference")
    if reviewer_refs != tuple(sorted(set(reviewer_refs))):
        raise ValueError("reviewer cohort must be sorted and unique")


def _utc(value: object, name: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z") or len(value) > 40:
        raise ValueError(f"{name} must be UTC RFC3339")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be UTC RFC3339") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{name} must be UTC RFC3339")
    return parsed


def _decision(
    aggregates: tuple[ArmHumanAggregate, ...],
    agreement_milli: int,
) -> tuple[tuple[str, ...], PromotionCandidateStatus]:
    by_arm = {item.arm: item for item in aggregates}
    baseline = by_arm[OfflineEvaluationArm.BASELINE]
    tuned = by_arm[OfflineEvaluationArm.TUNED]
    findings: list[str] = []
    if tuned.factual_acceptability_milli < baseline.factual_acceptability_milli:
        findings.append("FACTUAL_ACCEPTABILITY_REGRESSION")
    if (
        tuned.preference_count <= baseline.preference_count
        or tuned.style_score_milli <= baseline.style_score_milli
    ):
        findings.append("STYLE_IMPROVEMENT_NOT_JUSTIFIED")
    if agreement_milli < MIN_AGREEMENT_MILLI:
        findings.append("INTER_REVIEWER_AGREEMENT_LOW")
    codes = tuple(sorted(findings))
    status = (
        PromotionCandidateStatus.NOT_ELIGIBLE
        if any(code != "INTER_REVIEWER_AGREEMENT_LOW" for code in codes)
        else PromotionCandidateStatus.NOT_CONFIRMED
        if codes
        else PromotionCandidateStatus.READY_FOR_OWNER_REVIEW
    )
    return codes, status


__all__ = [
    "ArmHumanAggregate",
    "BlindReviewEvidence",
    "DbDReasoningPromotionCandidateEvaluator",
    "DbDReasoningPromotionCandidateReport",
    "PromotionCandidateStatus",
    "REPORT_STATE",
    "admit_dbd_reasoning_promotion_candidate_report",
]
