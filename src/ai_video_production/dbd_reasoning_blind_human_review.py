"""TASK-054 R4E-A body-free blind comparative Human-review evidence."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from typing import Any, Mapping

from .dbd_reasoning_offline_evaluation import (
    DbDReasoningOfflineEvaluationReport,
    OfflineEvaluationArm,
    OfflineGateStatus,
    admit_dbd_reasoning_offline_evaluation_report,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_VERSION = "1.0.0"
MAX_SAMPLES = 1_000
MAX_REASON_CODES = 16
MAX_RECORD_BYTES = 512 * 1024
_PACK_REF_RE = re.compile(r"blind-review-pack://sha256/[0-9a-f]{64}")
_SAMPLE_REF_RE = re.compile(r"eval-sample://sha256/[0-9a-f]{64}")
_REVIEWER_REF_RE = re.compile(r"reviewer://sha256/[0-9a-f]{64}")
_CONFIRMATION_REF_RE = re.compile(
    r"human-confirmation://dbd-blind-review/[0-9A-HJKMNP-TV-Z]{26}"
)
_AUTHORITY_EVIDENCE_REF_RE = re.compile(
    r"human-evidence://dbd-blind-review/sha256/[0-9a-f]{64}"
)
_CODE_RE = re.compile(r"[A-Z][A-Z0-9_]{1,63}")
_REVIEW_REASON_CODES = frozenset({
    "ALL_CANDIDATES_UNACCEPTABLE",
    "DENSITY_POOR",
    "FACTUAL_ERROR",
    "NOT_USEFUL",
    "OTHER_REVIEW_REASON",
    "TIMING_POOR",
    "UNCERTAINTY_POOR",
    "UNNATURAL",
})


class BlindLabel(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class BlindPreference(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    ALL_REJECTED = "ALL_REJECTED"


@dataclass(frozen=True, slots=True)
class BlindCandidate:
    label: BlindLabel
    candidate_output_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.label, BlindLabel):
            raise ValueError("blind label is invalid")
        validate_sha256(self.candidate_output_sha256, field_name="candidate_output_sha256")

    def to_dict(self) -> dict[str, object]:
        return {"label": self.label.value, "candidate_output_sha256": self.candidate_output_sha256}


@dataclass(frozen=True, slots=True)
class BlindPresentationSample:
    sample_ref: str
    candidates: tuple[BlindCandidate, ...]

    def __post_init__(self) -> None:
        _safe_ref(self.sample_ref, _SAMPLE_REF_RE, "sample_ref")
        if not isinstance(self.candidates, tuple) or len(self.candidates) != 3:
            raise ValueError("sample candidates must contain exactly three labels")
        if any(not isinstance(item, BlindCandidate) for item in self.candidates):
            raise ValueError("sample candidates contain an invalid record")
        if tuple(item.label for item in self.candidates) != tuple(BlindLabel):
            raise ValueError("sample candidates must use canonical A/B/C order")

    def to_dict(self) -> dict[str, object]:
        return {
            "sample_ref": self.sample_ref,
            "candidates": [item.to_dict() for item in self.candidates],
        }


@dataclass(frozen=True, slots=True)
class BlindReviewPresentation:
    offline_evaluation_report_sha256: str
    test_sample_set_sha256: str
    pack_ref: str
    samples: tuple[BlindPresentationSample, ...]
    presentation_state: str = "BLIND_PRESENTATION_NO_IDENTITY_REVEAL"

    def __post_init__(self) -> None:
        validate_sha256(
            self.offline_evaluation_report_sha256,
            field_name="offline_evaluation_report_sha256",
        )
        validate_sha256(self.test_sample_set_sha256, field_name="test_sample_set_sha256")
        _safe_ref(self.pack_ref, _PACK_REF_RE, "pack_ref")
        if (
            not isinstance(self.samples, tuple)
            or not 1 <= len(self.samples) <= MAX_SAMPLES
            or any(not isinstance(item, BlindPresentationSample) for item in self.samples)
        ):
            raise ValueError("presentation samples are invalid or outside bounds")
        refs = tuple(item.sample_ref for item in self.samples)
        if refs != tuple(sorted(set(refs))):
            raise ValueError("presentation samples must be sorted and unique")
        if self.presentation_state != "BLIND_PRESENTATION_NO_IDENTITY_REVEAL":
            raise ValueError("presentation cannot reveal arm or model identity")
        _bounded(self.to_dict(), "presentation")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_kind": "DBD_REASONING_BLIND_REVIEW_PRESENTATION",
            "offline_evaluation_report_sha256": self.offline_evaluation_report_sha256,
            "test_sample_set_sha256": self.test_sample_set_sha256,
            "pack_ref": self.pack_ref,
            "samples": [item.to_dict() for item in self.samples],
            "presentation_state": self.presentation_state,
        }

    def to_dict(self) -> dict[str, object]:
        body = self._body()
        return {**body, "presentation_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class BlindArmMapping:
    label: BlindLabel
    arm: OfflineEvaluationArm
    binding_sha256: str
    output_evidence_set_sha256: str
    candidate_output_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.label, BlindLabel) or not isinstance(self.arm, OfflineEvaluationArm):
            raise ValueError("reveal mapping enum is invalid")
        for name in (
            "binding_sha256",
            "output_evidence_set_sha256",
            "candidate_output_sha256",
        ):
            validate_sha256(getattr(self, name), field_name=name)

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label.value,
            "arm": self.arm.value,
            "binding_sha256": self.binding_sha256,
            "output_evidence_set_sha256": self.output_evidence_set_sha256,
            "candidate_output_sha256": self.candidate_output_sha256,
        }


@dataclass(frozen=True, slots=True)
class BlindRevealSample:
    sample_ref: str
    mappings: tuple[BlindArmMapping, ...]

    def __post_init__(self) -> None:
        _safe_ref(self.sample_ref, _SAMPLE_REF_RE, "sample_ref")
        if not isinstance(self.mappings, tuple) or len(self.mappings) != 3:
            raise ValueError("reveal mappings must contain exactly three records")
        if any(not isinstance(item, BlindArmMapping) for item in self.mappings):
            raise ValueError("reveal mappings contain an invalid record")
        if tuple(item.label for item in self.mappings) != tuple(BlindLabel):
            raise ValueError("reveal mappings must use canonical A/B/C order")
        if set(item.arm for item in self.mappings) != set(OfflineEvaluationArm):
            raise ValueError("each sample must map every evaluation arm exactly once")

    def to_dict(self) -> dict[str, object]:
        return {"sample_ref": self.sample_ref, "mappings": [item.to_dict() for item in self.mappings]}


@dataclass(frozen=True, slots=True)
class BlindReviewRevealManifest:
    offline_evaluation_report_sha256: str
    presentation_sha256: str
    pack_ref: str
    samples: tuple[BlindRevealSample, ...]
    reveal_state: str = "SEALED_UNTIL_SUBMISSIONS_ADMITTED"

    def __post_init__(self) -> None:
        validate_sha256(
            self.offline_evaluation_report_sha256,
            field_name="offline_evaluation_report_sha256",
        )
        validate_sha256(self.presentation_sha256, field_name="presentation_sha256")
        _safe_ref(self.pack_ref, _PACK_REF_RE, "pack_ref")
        if (
            not isinstance(self.samples, tuple)
            or not 1 <= len(self.samples) <= MAX_SAMPLES
            or any(not isinstance(item, BlindRevealSample) for item in self.samples)
        ):
            raise ValueError("reveal samples are invalid or outside bounds")
        refs = tuple(item.sample_ref for item in self.samples)
        if refs != tuple(sorted(set(refs))):
            raise ValueError("reveal samples must be sorted and unique")
        if self.reveal_state != "SEALED_UNTIL_SUBMISSIONS_ADMITTED":
            raise ValueError("reveal manifest state is invalid")
        _bounded(self.to_dict(), "reveal manifest")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_kind": "DBD_REASONING_BLIND_REVIEW_REVEAL_MANIFEST",
            "offline_evaluation_report_sha256": self.offline_evaluation_report_sha256,
            "presentation_sha256": self.presentation_sha256,
            "pack_ref": self.pack_ref,
            "samples": [item.to_dict() for item in self.samples],
            "reveal_state": self.reveal_state,
        }

    def to_dict(self) -> dict[str, object]:
        body = self._body()
        return {**body, "reveal_manifest_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class BlindCandidateScore:
    label: BlindLabel
    candidate_output_sha256: str
    factual_acceptable: bool
    uncertainty_handling: int
    usefulness: int
    timing: int
    naturalness: int
    density: int

    def __post_init__(self) -> None:
        if not isinstance(self.label, BlindLabel):
            raise ValueError("score label is invalid")
        validate_sha256(self.candidate_output_sha256, field_name="candidate_output_sha256")
        if not isinstance(self.factual_acceptable, bool):
            raise ValueError("factual_acceptable must be boolean")
        for name in ("uncertainty_handling", "usefulness", "timing", "naturalness", "density"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
                raise ValueError(f"{name} must be an integer from 1 through 5")

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label.value,
            "candidate_output_sha256": self.candidate_output_sha256,
            "factual_acceptable": self.factual_acceptable,
            "uncertainty_handling": self.uncertainty_handling,
            "usefulness": self.usefulness,
            "timing": self.timing,
            "naturalness": self.naturalness,
            "density": self.density,
        }


@dataclass(frozen=True, slots=True)
class BlindHumanReviewSubmission:
    offline_evaluation_report_sha256: str
    presentation_sha256: str
    pack_ref: str
    sample_ref: str
    reviewer_ref: str
    scores: tuple[BlindCandidateScore, ...]
    preference: BlindPreference
    reason_codes: tuple[str, ...]
    reviewer_kind: str
    confirmation_ref: str
    confirmation_sha256: str
    one_shot: bool
    reviewed_at: str
    submission_state: str = "BLIND_HUMAN_EVIDENCE_NO_PROMOTION"

    def __post_init__(self) -> None:
        validate_sha256(
            self.offline_evaluation_report_sha256,
            field_name="offline_evaluation_report_sha256",
        )
        validate_sha256(self.presentation_sha256, field_name="presentation_sha256")
        validate_sha256(self.confirmation_sha256, field_name="confirmation_sha256")
        _safe_ref(self.pack_ref, _PACK_REF_RE, "pack_ref")
        _safe_ref(self.sample_ref, _SAMPLE_REF_RE, "sample_ref")
        _safe_ref(self.reviewer_ref, _REVIEWER_REF_RE, "reviewer_ref")
        _safe_ref(self.confirmation_ref, _CONFIRMATION_REF_RE, "confirmation_ref")
        if not isinstance(self.scores, tuple) or len(self.scores) != 3:
            raise ValueError("scores must contain exactly three candidates")
        if any(not isinstance(item, BlindCandidateScore) for item in self.scores):
            raise ValueError("scores contain an invalid candidate")
        if tuple(item.label for item in self.scores) != tuple(BlindLabel):
            raise ValueError("scores must use canonical A/B/C order")
        if not isinstance(self.preference, BlindPreference):
            raise ValueError("preference is invalid")
        object.__setattr__(self, "reason_codes", _codes(self.reason_codes))
        if self.preference is BlindPreference.ALL_REJECTED and not self.reason_codes:
            raise ValueError("ALL_REJECTED requires a stable reason code")
        if self.reviewer_kind != "HUMAN" or self.one_shot is not True:
            raise ValueError("submission requires one-shot external Human confirmation")
        _utc(self.reviewed_at)
        if self.submission_state != "BLIND_HUMAN_EVIDENCE_NO_PROMOTION":
            raise ValueError("submission cannot grant promotion authority")
        _bounded(self.to_dict(), "submission")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_kind": "DBD_REASONING_BLIND_HUMAN_REVIEW_SUBMISSION",
            "offline_evaluation_report_sha256": self.offline_evaluation_report_sha256,
            "presentation_sha256": self.presentation_sha256,
            "pack_ref": self.pack_ref,
            "sample_ref": self.sample_ref,
            "reviewer_ref": self.reviewer_ref,
            "scores": [item.to_dict() for item in self.scores],
            "preference": self.preference.value,
            "reason_codes": list(self.reason_codes),
            "reviewer_kind": self.reviewer_kind,
            "confirmation_ref": self.confirmation_ref,
            "confirmation_sha256": self.confirmation_sha256,
            "one_shot": self.one_shot,
            "reviewed_at": self.reviewed_at,
            "submission_state": self.submission_state,
        }

    def to_dict(self) -> dict[str, object]:
        body = self._body()
        return {**body, "submission_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class BlindHumanReviewAuthorityBinding:
    presentation_sha256: str
    pack_ref: str
    sample_ref: str
    reviewer_ref: str
    expected_submission_sha256: str
    confirmation_ref: str
    confirmation_revision: int
    confirmation_sha256: str
    authority_evidence_ref: str
    authority_evidence_sha256: str
    reviewer_kind: str
    decided_at: str
    expires_at: str
    one_shot: bool
    binding_state: str = "EXTERNAL_HUMAN_AUTHORITY_BOUND"

    def __post_init__(self) -> None:
        for name in (
            "presentation_sha256",
            "expected_submission_sha256",
            "confirmation_sha256",
            "authority_evidence_sha256",
        ):
            validate_sha256(getattr(self, name), field_name=name)
        _safe_ref(self.pack_ref, _PACK_REF_RE, "pack_ref")
        _safe_ref(self.sample_ref, _SAMPLE_REF_RE, "sample_ref")
        _safe_ref(self.reviewer_ref, _REVIEWER_REF_RE, "reviewer_ref")
        _safe_ref(self.confirmation_ref, _CONFIRMATION_REF_RE, "confirmation_ref")
        _safe_ref(
            self.authority_evidence_ref,
            _AUTHORITY_EVIDENCE_REF_RE,
            "authority_evidence_ref",
        )
        if (
            isinstance(self.confirmation_revision, bool)
            or not isinstance(self.confirmation_revision, int)
            or self.confirmation_revision < 1
        ):
            raise ValueError("confirmation_revision must be positive")
        if self.reviewer_kind != "HUMAN" or self.one_shot is not True:
            raise ValueError("authority binding requires a one-shot Human decision")
        if _utc(self.expires_at, "expires_at") <= _utc(self.decided_at, "decided_at"):
            raise ValueError("expires_at must follow decided_at")
        if self.binding_state != "EXTERNAL_HUMAN_AUTHORITY_BOUND":
            raise ValueError("authority binding state is invalid")
        _bounded(self.to_dict(), "authority binding")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_kind": "DBD_REASONING_BLIND_HUMAN_REVIEW_AUTHORITY_BINDING",
            "presentation_sha256": self.presentation_sha256,
            "pack_ref": self.pack_ref,
            "sample_ref": self.sample_ref,
            "reviewer_ref": self.reviewer_ref,
            "expected_submission_sha256": self.expected_submission_sha256,
            "confirmation_ref": self.confirmation_ref,
            "confirmation_revision": self.confirmation_revision,
            "confirmation_sha256": self.confirmation_sha256,
            "authority_evidence_ref": self.authority_evidence_ref,
            "authority_evidence_sha256": self.authority_evidence_sha256,
            "reviewer_kind": self.reviewer_kind,
            "decided_at": self.decided_at,
            "expires_at": self.expires_at,
            "one_shot": self.one_shot,
            "binding_state": self.binding_state,
        }

    def to_dict(self) -> dict[str, object]:
        body = self._body()
        return {**body, "binding_sha256": sha256_bytes(canonical_json_bytes(body))}


def create_blind_review_pack(
    *,
    offline_report: DbDReasoningOfflineEvaluationReport,
    pack_ref: str,
    presentation_samples: tuple[BlindPresentationSample, ...],
    reveal_samples: tuple[BlindRevealSample, ...],
) -> tuple[BlindReviewPresentation, BlindReviewRevealManifest]:
    report = admit_dbd_reasoning_offline_evaluation_report(offline_report.to_dict())
    if report.tuned_gate_status is not OfflineGateStatus.PASS:
        raise ValueError("R4E requires a PASS TUNED R4D automated gate")
    report_sha = report.to_dict()["evaluation_report_sha256"]
    presentation = BlindReviewPresentation(
        offline_evaluation_report_sha256=report_sha,
        test_sample_set_sha256=report.test_sample_set_sha256,
        pack_ref=pack_ref,
        samples=presentation_samples,
    )
    reveal = BlindReviewRevealManifest(
        offline_evaluation_report_sha256=report_sha,
        presentation_sha256=presentation.to_dict()["presentation_sha256"],
        pack_ref=pack_ref,
        samples=reveal_samples,
    )
    if tuple(item.sample_ref for item in presentation.samples) != tuple(
        item.sample_ref for item in reveal.samples
    ):
        raise ValueError("presentation and reveal sample sets do not match")
    arms = {item.arm: item for item in report.evaluations}
    for presented, revealed in zip(presentation.samples, reveal.samples, strict=True):
        for candidate, mapping in zip(presented.candidates, revealed.mappings, strict=True):
            arm = arms[mapping.arm]
            if (
                candidate.label is not mapping.label
                or candidate.candidate_output_sha256 != mapping.candidate_output_sha256
                or arm.binding_sha256 != mapping.binding_sha256
                or arm.output_evidence_set_sha256 != mapping.output_evidence_set_sha256
            ):
                raise ValueError("blind reveal mapping crosses presentation or R4D evidence")
    return presentation, reveal


def admit_blind_human_review_authority_binding(
    record: Mapping[str, Any],
) -> BlindHumanReviewAuthorityBinding:
    expected = set(BlindHumanReviewAuthorityBinding.__dataclass_fields__) | {
        "schema_version", "record_kind", "binding_sha256",
    }
    if not isinstance(record, Mapping) or set(record) != expected:
        raise ValueError("blind Human authority binding shape is invalid")
    if record.get("schema_version") != SCHEMA_VERSION or record.get("record_kind") != "DBD_REASONING_BLIND_HUMAN_REVIEW_AUTHORITY_BINDING":
        raise ValueError("blind Human authority binding version or kind is invalid")
    values = {
        key: record[key]
        for key in BlindHumanReviewAuthorityBinding.__dataclass_fields__
    }
    binding = BlindHumanReviewAuthorityBinding(**values)
    if binding.to_dict() != dict(record):
        raise ValueError("blind Human authority binding checksum or canonical form is invalid")
    return binding


def admit_blind_human_review_submission(
    record: Mapping[str, Any],
    *,
    presentation: BlindReviewPresentation,
    authority_record: Mapping[str, Any],
    evaluated_at: str,
) -> BlindHumanReviewSubmission:
    presentation = admit_blind_review_presentation(presentation.to_dict())
    authority = admit_blind_human_review_authority_binding(authority_record)
    expected = set(BlindHumanReviewSubmission.__dataclass_fields__) | {
        "schema_version",
        "record_kind",
        "submission_sha256",
    }
    expected -= {"submission_state"}
    expected.add("submission_state")
    if not isinstance(record, Mapping) or set(record) != expected:
        raise ValueError("blind submission shape is invalid")
    if record.get("schema_version") != SCHEMA_VERSION or record.get("record_kind") != "DBD_REASONING_BLIND_HUMAN_REVIEW_SUBMISSION":
        raise ValueError("blind submission version or kind is invalid")
    raw_scores = record.get("scores")
    raw_reasons = record.get("reason_codes")
    if not isinstance(raw_scores, list) or not isinstance(raw_reasons, list):
        raise ValueError("blind submission arrays are invalid")
    scores = tuple(_score_from_dict(item) for item in raw_scores)
    submission = BlindHumanReviewSubmission(
        offline_evaluation_report_sha256=record["offline_evaluation_report_sha256"],
        presentation_sha256=record["presentation_sha256"],
        pack_ref=record["pack_ref"],
        sample_ref=record["sample_ref"],
        reviewer_ref=record["reviewer_ref"],
        scores=scores,
        preference=BlindPreference(record["preference"]),
        reason_codes=tuple(raw_reasons),
        reviewer_kind=record["reviewer_kind"],
        confirmation_ref=record["confirmation_ref"],
        confirmation_sha256=record["confirmation_sha256"],
        one_shot=record["one_shot"],
        reviewed_at=record["reviewed_at"],
        submission_state=record["submission_state"],
    )
    presentation_record = presentation.to_dict()
    if (
        submission.offline_evaluation_report_sha256
        != presentation.offline_evaluation_report_sha256
        or submission.presentation_sha256 != presentation_record["presentation_sha256"]
        or submission.pack_ref != presentation.pack_ref
    ):
        raise ValueError("blind submission crosses its presentation")
    sample = next((item for item in presentation.samples if item.sample_ref == submission.sample_ref), None)
    if sample is None or tuple(item.candidate_output_sha256 for item in sample.candidates) != tuple(
        item.candidate_output_sha256 for item in submission.scores
    ):
        raise ValueError("blind submission sample or candidate outputs do not match presentation")
    if submission.to_dict() != dict(record):
        raise ValueError("blind submission checksum or canonical form is invalid")
    if (
        authority.presentation_sha256 != submission.presentation_sha256
        or authority.pack_ref != submission.pack_ref
        or authority.sample_ref != submission.sample_ref
        or authority.reviewer_ref != submission.reviewer_ref
        or authority.expected_submission_sha256 != record["submission_sha256"]
        or authority.confirmation_ref != submission.confirmation_ref
        or authority.confirmation_sha256 != submission.confirmation_sha256
        or authority.decided_at != submission.reviewed_at
    ):
        raise ValueError("external Human authority does not bind the exact blind submission")
    evaluated = _utc(evaluated_at, "evaluated_at")
    decided = _utc(authority.decided_at, "decided_at")
    expires = _utc(authority.expires_at, "expires_at")
    if evaluated < decided:
        raise ValueError("external Human confirmation is not yet effective")
    if evaluated >= expires:
        raise ValueError("external Human confirmation expired")
    return submission


def admit_blind_review_presentation(record: Mapping[str, Any]) -> BlindReviewPresentation:
    expected = {
        "schema_version", "record_kind", "offline_evaluation_report_sha256",
        "test_sample_set_sha256", "pack_ref", "samples", "presentation_state",
        "presentation_sha256",
    }
    if not isinstance(record, Mapping) or set(record) != expected:
        raise ValueError("blind presentation shape is invalid")
    if record.get("schema_version") != SCHEMA_VERSION or record.get("record_kind") != "DBD_REASONING_BLIND_REVIEW_PRESENTATION":
        raise ValueError("blind presentation version or kind is invalid")
    raw_samples = record.get("samples")
    if not isinstance(raw_samples, list):
        raise ValueError("blind presentation samples must be a list")
    samples = tuple(_presentation_sample_from_dict(item) for item in raw_samples)
    admitted = BlindReviewPresentation(
        offline_evaluation_report_sha256=record["offline_evaluation_report_sha256"],
        test_sample_set_sha256=record["test_sample_set_sha256"],
        pack_ref=record["pack_ref"],
        samples=samples,
        presentation_state=record["presentation_state"],
    )
    if admitted.to_dict() != dict(record):
        raise ValueError("blind presentation checksum or canonical form is invalid")
    return admitted


def admit_blind_review_reveal_manifest(
    record: Mapping[str, Any],
    *,
    presentation: BlindReviewPresentation,
    offline_report: DbDReasoningOfflineEvaluationReport,
) -> BlindReviewRevealManifest:
    expected = {
        "schema_version", "record_kind", "offline_evaluation_report_sha256",
        "presentation_sha256", "pack_ref", "samples", "reveal_state",
        "reveal_manifest_sha256",
    }
    if not isinstance(record, Mapping) or set(record) != expected:
        raise ValueError("blind reveal manifest shape is invalid")
    if record.get("schema_version") != SCHEMA_VERSION or record.get("record_kind") != "DBD_REASONING_BLIND_REVIEW_REVEAL_MANIFEST":
        raise ValueError("blind reveal manifest version or kind is invalid")
    raw_samples = record.get("samples")
    if not isinstance(raw_samples, list):
        raise ValueError("blind reveal samples must be a list")
    reveal_samples = []
    for raw_sample in raw_samples:
        if not isinstance(raw_sample, Mapping) or set(raw_sample) != {"sample_ref", "mappings"}:
            raise ValueError("blind reveal sample shape is invalid")
        raw_mappings = raw_sample["mappings"]
        if not isinstance(raw_mappings, list):
            raise ValueError("blind reveal mappings must be a list")
        mappings = []
        expected_mapping = set(BlindArmMapping.__dataclass_fields__)
        for raw_mapping in raw_mappings:
            if not isinstance(raw_mapping, Mapping) or set(raw_mapping) != expected_mapping:
                raise ValueError("blind arm mapping shape is invalid")
            values = dict(raw_mapping)
            values["label"] = BlindLabel(values["label"])
            values["arm"] = OfflineEvaluationArm(values["arm"])
            mappings.append(BlindArmMapping(**values))
        reveal_samples.append(BlindRevealSample(raw_sample["sample_ref"], tuple(mappings)))
    reveal = BlindReviewRevealManifest(
        offline_evaluation_report_sha256=record["offline_evaluation_report_sha256"],
        presentation_sha256=record["presentation_sha256"],
        pack_ref=record["pack_ref"],
        samples=tuple(reveal_samples),
        reveal_state=record["reveal_state"],
    )
    rebuilt_presentation, rebuilt_reveal = create_blind_review_pack(
        offline_report=offline_report,
        pack_ref=presentation.pack_ref,
        presentation_samples=presentation.samples,
        reveal_samples=reveal.samples,
    )
    if (
        rebuilt_presentation.to_dict() != presentation.to_dict()
        or rebuilt_reveal.to_dict() != dict(record)
    ):
        raise ValueError("blind reveal checksum, presentation or R4D binding is invalid")
    return reveal


def _presentation_sample_from_dict(record: object) -> BlindPresentationSample:
    if not isinstance(record, Mapping) or set(record) != {"sample_ref", "candidates"}:
        raise ValueError("blind presentation sample shape is invalid")
    raw = record["candidates"]
    if not isinstance(raw, list):
        raise ValueError("blind candidates must be a list")
    candidates = []
    for item in raw:
        if not isinstance(item, Mapping) or set(item) != {"label", "candidate_output_sha256"}:
            raise ValueError("blind candidate shape is invalid")
        candidates.append(BlindCandidate(BlindLabel(item["label"]), item["candidate_output_sha256"]))
    return BlindPresentationSample(record["sample_ref"], tuple(candidates))


def _score_from_dict(record: object) -> BlindCandidateScore:
    expected = set(BlindCandidateScore.__dataclass_fields__)
    if not isinstance(record, Mapping) or set(record) != expected:
        raise ValueError("blind score shape is invalid")
    values = dict(record)
    values["label"] = BlindLabel(values["label"])
    return BlindCandidateScore(**values)


def _safe_ref(value: object, pattern: re.Pattern[str], name: str) -> None:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"{name} is not a canonical body-free reference")


def _codes(value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ValueError("reason_codes must be a tuple")
    if any(not isinstance(item, str) or not _CODE_RE.fullmatch(item) for item in value):
        raise ValueError("reason_codes contain an invalid stable code")
    if len(value) > MAX_REASON_CODES or value != tuple(sorted(set(value))):
        raise ValueError("reason_codes must be bounded, sorted and unique")
    if any(item not in _REVIEW_REASON_CODES for item in value):
        raise ValueError("reason_codes contain a non-blind or unsupported code")
    return value


def _utc(value: object, name: str = "reviewed_at") -> datetime:
    if not isinstance(value, str) or not value.endswith("Z") or len(value) > 40:
        raise ValueError(f"{name} must be UTC RFC3339")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be UTC RFC3339") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{name} must be UTC RFC3339")
    return parsed


def _bounded(record: Mapping[str, object], name: str) -> None:
    if len(canonical_json_bytes(record)) > MAX_RECORD_BYTES:
        raise ValueError(f"{name} exceeds the canonical byte ceiling")


__all__ = [
    "BlindArmMapping",
    "BlindCandidate",
    "BlindCandidateScore",
    "BlindHumanReviewAuthorityBinding",
    "BlindHumanReviewSubmission",
    "BlindLabel",
    "BlindPreference",
    "BlindPresentationSample",
    "BlindRevealSample",
    "BlindReviewPresentation",
    "BlindReviewRevealManifest",
    "admit_blind_human_review_authority_binding",
    "admit_blind_human_review_submission",
    "admit_blind_review_presentation",
    "admit_blind_review_reveal_manifest",
    "create_blind_review_pack",
]
