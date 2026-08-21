"""Held-out DbD Human Gold manifest, KPI and correction-feedback contracts."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
import re
from typing import Iterable

from .serialization import canonical_json_bytes, sha256_bytes


_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_REF = re.compile(r"^[a-z][a-z0-9+.-]*://[^\s]{1,1000}$")


class GoldSplit(str, Enum):
    TRAIN = "TRAIN"
    VALIDATION = "VALIDATION"
    TEST = "TEST"


class GoldDomain(str, Enum):
    GENERATOR = "GENERATOR"
    CHASE = "CHASE"
    SURVIVOR_STATE = "SURVIVOR_STATE"
    HOOK = "HOOK"
    SPEAKER = "SPEAKER"
    TRANSCRIPT = "TRANSCRIPT"
    TACTICAL_NOTE = "TACTICAL_NOTE"
    PERK = "PERK"
    KILLER = "KILLER"
    MAP = "MAP"
    STATUS_EFFECT = "STATUS_EFFECT"
    OBJECT_SCENE = "OBJECT_SCENE"
    ADD_ON = "ADD_ON"


class ClaimValidatorStatus(str, Enum):
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    NOT_CHECKED = "NOT_CHECKED"


class GoldAcceptanceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_CONFIRMED = "NOT_CONFIRMED"


PILOT_REQUIRED_DOMAINS = frozenset({
    GoldDomain.GENERATOR, GoldDomain.CHASE, GoldDomain.SURVIVOR_STATE,
    GoldDomain.HOOK, GoldDomain.SPEAKER, GoldDomain.TRANSCRIPT,
    GoldDomain.TACTICAL_NOTE,
})
RECOGNITION_KPI_DOMAINS = frozenset({
    GoldDomain.GENERATOR, GoldDomain.CHASE, GoldDomain.SURVIVOR_STATE,
    GoldDomain.HOOK, GoldDomain.PERK, GoldDomain.KILLER, GoldDomain.MAP,
    GoldDomain.STATUS_EFFECT, GoldDomain.OBJECT_SCENE, GoldDomain.ADD_ON,
})


def _bounded(value: str, name: str, maximum: int = 256) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(ord(x) < 32 for x in value):
        raise ValueError(f"{name} must be bounded text")


def _milli(n: int, d: int) -> int | None:
    return None if d == 0 else (n * 1000 + d // 2) // d


@dataclass(frozen=True, slots=True)
class GoldMatch:
    match_id: str
    source_group_id: str
    source_ref: str
    rights_ref: str
    split: GoldSplit
    patch_version: str
    hud_profile_version: str
    domains: frozenset[GoldDomain]
    real_media: bool

    def __post_init__(self) -> None:
        if not _ID.fullmatch(self.match_id) or not _ID.fullmatch(self.source_group_id):
            raise ValueError("match_id and source_group_id must be safe identifiers")
        if not _REF.fullmatch(self.source_ref):
            raise ValueError("source_ref must be a bounded reference")
        if not self.rights_ref.startswith("rights://") or not _REF.fullmatch(self.rights_ref):
            raise ValueError("rights_ref must use rights://")
        if not isinstance(self.split, GoldSplit) or not isinstance(self.real_media, bool):
            raise ValueError("invalid Gold match split or real_media flag")
        _bounded(self.patch_version, "patch_version", 64)
        _bounded(self.hud_profile_version, "hud_profile_version", 64)
        if not self.domains or any(not isinstance(x, GoldDomain) for x in self.domains):
            raise ValueError("domains must contain GoldDomain values")

    def to_dict(self) -> dict[str, object]:
        return {
            "match_id": self.match_id, "source_group_id": self.source_group_id,
            "source_ref": self.source_ref, "rights_ref": self.rights_ref,
            "split": self.split.value, "patch_version": self.patch_version,
            "hud_profile_version": self.hud_profile_version,
            "domains": sorted(x.value for x in self.domains), "real_media": self.real_media,
        }


@dataclass(frozen=True, slots=True)
class DbDGoldManifest:
    dataset_id: str
    revision: int
    detector_version: str
    model_version: str
    matches: tuple[GoldMatch, ...]

    def __post_init__(self) -> None:
        if not _ID.fullmatch(self.dataset_id):
            raise ValueError("dataset_id must be a safe identifier")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise ValueError("revision must be positive")
        _bounded(self.detector_version, "detector_version", 64)
        _bounded(self.model_version, "model_version", 128)
        if not self.matches or any(not isinstance(x, GoldMatch) for x in self.matches):
            raise ValueError("matches must contain GoldMatch values")
        ids = tuple(x.match_id for x in self.matches)
        if ids != tuple(sorted(set(ids))):
            raise ValueError("matches must be unique and sorted by match_id")
        group_splits: dict[str, GoldSplit] = {}
        for item in self.matches:
            old = group_splits.setdefault(item.source_group_id, item.split)
            if old is not item.split:
                raise ValueError("source group leakage across dataset splits")

    def to_dict(self) -> dict[str, object]:
        body = {
            "schema_version": "1.0.0", "dataset_id": self.dataset_id,
            "revision": self.revision, "detector_version": self.detector_version,
            "model_version": self.model_version,
            "matches": [x.to_dict() for x in self.matches],
        }
        return {**body, "dataset_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class GoldPrediction:
    sample_id: str
    match_id: str
    domain: GoldDomain
    expected_label: str | None
    predicted_label: str | None
    abstained: bool
    confidence_milli: int
    latency_ms: int
    contradiction: bool
    replay_consistent: bool
    validator_status: ClaimValidatorStatus
    validator_source_ref: str | None

    def __post_init__(self) -> None:
        if not _ID.fullmatch(self.sample_id) or not _ID.fullmatch(self.match_id):
            raise ValueError("sample_id and match_id must be safe identifiers")
        if not isinstance(self.domain, GoldDomain) or not isinstance(self.validator_status, ClaimValidatorStatus):
            raise ValueError("invalid prediction domain or validator status")
        for value, name in ((self.expected_label, "expected_label"), (self.predicted_label, "predicted_label")):
            if value is not None:
                _bounded(value, name, 256)
        if not isinstance(self.abstained, bool) or not isinstance(self.contradiction, bool) or not isinstance(self.replay_consistent, bool):
            raise ValueError("abstained, contradiction and replay_consistent must be bool")
        if self.abstained and self.predicted_label is not None:
            raise ValueError("abstention cannot assert a predicted label")
        if isinstance(self.confidence_milli, bool) or not isinstance(self.confidence_milli, int) or not 0 <= self.confidence_milli <= 1000:
            raise ValueError("confidence_milli must be 0..1000")
        if isinstance(self.latency_ms, bool) or not isinstance(self.latency_ms, int) or self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
        if self.validator_source_ref is not None and not _REF.fullmatch(self.validator_source_ref):
            raise ValueError("validator_source_ref must be a bounded reference")
        if self.validator_status is ClaimValidatorStatus.VERIFIED and self.validator_source_ref is None:
            raise ValueError("VERIFIED claim requires validator source provenance")


@dataclass(frozen=True, slots=True)
class GoldCorrection:
    correction_id: str
    sample_id: str
    original_label: str | None
    corrected_label: str | None
    reviewer_ref: str
    reason_code: str
    provenance_ref: str

    def __post_init__(self) -> None:
        if not _ID.fullmatch(self.correction_id) or not _ID.fullmatch(self.sample_id):
            raise ValueError("correction_id and sample_id must be safe identifiers")
        if self.original_label == self.corrected_label:
            raise ValueError("correction must change the original label")
        for value, name in ((self.original_label, "original_label"), (self.corrected_label, "corrected_label")):
            if value is not None:
                _bounded(value, name, 256)
        for value, name in ((self.reviewer_ref, "reviewer_ref"), (self.reason_code, "reason_code"), (self.provenance_ref, "provenance_ref")):
            _bounded(value, name, 1024)
        if not _REF.fullmatch(self.reviewer_ref) or not _REF.fullmatch(self.provenance_ref):
            raise ValueError("reviewer/provenance must be references")


@dataclass(frozen=True, slots=True)
class GoldRejection:
    rejection_id: str
    candidate_ref: str
    domain: GoldDomain
    reason_code: str
    reviewer_ref: str
    provenance_ref: str

    def __post_init__(self) -> None:
        if not _ID.fullmatch(self.rejection_id):
            raise ValueError("rejection_id must be a safe identifier")
        if not isinstance(self.domain, GoldDomain):
            raise ValueError("rejection domain is invalid")
        for value, name in ((self.candidate_ref, "candidate_ref"), (self.reviewer_ref, "reviewer_ref"), (self.provenance_ref, "provenance_ref")):
            if not _REF.fullmatch(value):
                raise ValueError(f"{name} must be a bounded reference")
        _bounded(self.reason_code, "reason_code", 128)


@dataclass(frozen=True, slots=True)
class DomainKpi:
    domain: GoldDomain
    case_count: int
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int
    unknown_count: int
    contradiction_count: int
    invalid_claim_count: int
    precision_milli: int | None
    recall_milli: int | None
    unknown_rate_milli: int
    calibration_error_milli: int
    stability_milli: int
    mean_latency_ms: int


@dataclass(frozen=True, slots=True)
class DbDGoldKpiReport:
    dataset_sha256: str
    acceptance_status: GoldAcceptanceStatus
    reason_codes: tuple[str, ...]
    evaluated_match_count: int
    held_out_case_count: int
    domain_kpis: tuple[DomainKpi, ...]
    correction_candidate_ids: tuple[str, ...]
    rejection_reason_counts: tuple[tuple[str, int], ...]
    production_accuracy_claim_authorized: bool


class DbDGoldKpiEvaluator:
    @staticmethod
    def evaluate(
        manifest: DbDGoldManifest,
        predictions: Iterable[GoldPrediction],
        corrections: Iterable[GoldCorrection] = (),
        *,
        rejections: Iterable[GoldRejection] = (),
        production_accuracy_claim_authorized: bool = False,
    ) -> DbDGoldKpiReport:
        if not isinstance(manifest, DbDGoldManifest):
            raise ValueError("manifest must be DbDGoldManifest")
        rows = tuple(predictions)
        fixes = tuple(corrections)
        rejected = tuple(rejections)
        if (
            any(not isinstance(x, GoldPrediction) for x in rows)
            or any(not isinstance(x, GoldCorrection) for x in fixes)
            or any(not isinstance(x, GoldRejection) for x in rejected)
        ):
            raise ValueError("predictions/corrections/rejections contain invalid values")
        sample_ids = tuple(x.sample_id for x in rows)
        if len(sample_ids) != len(set(sample_ids)):
            raise ValueError("prediction sample_id values must be unique")
        correction_ids = tuple(x.correction_id for x in fixes)
        if len(correction_ids) != len(set(correction_ids)):
            raise ValueError("correction_id values must be unique")
        rejection_ids = tuple(x.rejection_id for x in rejected)
        if len(rejection_ids) != len(set(rejection_ids)):
            raise ValueError("rejection_id values must be unique")
        if any(x.sample_id not in set(sample_ids) for x in fixes):
            raise ValueError("correction must reference an evaluated sample")
        matches = {x.match_id: x for x in manifest.matches}
        if any(x.match_id not in matches or x.domain not in matches[x.match_id].domains for x in rows):
            raise ValueError("prediction must reference a declared match/domain")
        held_out = tuple(x for x in rows if matches[x.match_id].split is GoldSplit.TEST)
        metrics: list[DomainKpi] = []
        for domain in sorted({x.domain for x in held_out}, key=lambda x: x.value):
            items = tuple(x for x in held_out if x.domain is domain)
            tp = fp = fn = tn = unknown = contradictions = invalid = 0
            for item in items:
                exact = item.expected_label is not None and item.predicted_label == item.expected_label and not item.abstained
                if exact:
                    tp += 1
                else:
                    if item.expected_label is not None:
                        fn += 1
                    if item.predicted_label is not None:
                        fp += 1
                    elif item.expected_label is None:
                        tn += 1
                unknown += int(item.abstained or item.predicted_label is None)
                contradictions += int(item.contradiction)
                invalid += int(item.predicted_label is not None and item.validator_status is not ClaimValidatorStatus.VERIFIED)
            metrics.append(DomainKpi(
                domain, len(items), tp, fp, fn, tn, unknown, contradictions, invalid,
                _milli(tp, tp + fp), _milli(tp, tp + fn), _milli(unknown, len(items)) or 0,
                (sum(abs(x.confidence_milli - (1000 if x.expected_label is not None and x.predicted_label == x.expected_label and not x.abstained else 0)) for x in items) + len(items) // 2) // len(items),
                _milli(sum(x.replay_consistent for x in items), len(items)) or 0,
                (sum(x.latency_ms for x in items) + len(items) // 2) // len(items),
            ))
        reasons: list[str] = []
        if not 5 <= len(manifest.matches) <= 10:
            reasons.append("PILOT_MATCH_COUNT_OUTSIDE_5_TO_10")
        if any(not PILOT_REQUIRED_DOMAINS.issubset(x.domains) for x in manifest.matches):
            reasons.append("PILOT_LABEL_COMPLETENESS_MISSING")
        if not any(x.split is GoldSplit.TEST for x in manifest.matches):
            reasons.append("HELD_OUT_TEST_SPLIT_MISSING")
        if any(not x.real_media for x in manifest.matches):
            reasons.append("REAL_MEDIA_EVIDENCE_INCOMPLETE")
        covered = {x.domain for x in held_out}
        if not RECOGNITION_KPI_DOMAINS.issubset(covered):
            reasons.append("RECOGNITION_DOMAIN_KPI_MISSING")
        if any(x.invalid_claim_count for x in metrics):
            reasons.append("UNVALIDATED_PREDICTION_CLAIM")
        if production_accuracy_claim_authorized and reasons:
            raise ValueError("production accuracy authority requires complete held-out real-media evidence")
        if not production_accuracy_claim_authorized:
            reasons.append("PRODUCTION_ACCURACY_AUTHORITY_NOT_GRANTED")
        status = GoldAcceptanceStatus.PASS if production_accuracy_claim_authorized and not reasons else GoldAcceptanceStatus.NOT_CONFIRMED
        return DbDGoldKpiReport(
            manifest.to_dict()["dataset_sha256"], status, tuple(sorted(reasons)),
            len({x.match_id for x in held_out}), len(held_out), tuple(metrics),
            tuple(sorted(x.correction_id for x in fixes)),
            tuple(sorted(Counter(x.reason_code for x in rejected).items())),
            production_accuracy_claim_authorized and not reasons,
        )


__all__ = [
    "ClaimValidatorStatus", "DbDGoldKpiEvaluator", "DbDGoldKpiReport",
    "DbDGoldManifest", "DomainKpi", "GoldAcceptanceStatus", "GoldCorrection",
    "GoldDomain", "GoldMatch", "GoldPrediction", "GoldRejection", "GoldSplit",
    "PILOT_REQUIRED_DOMAINS", "RECOGNITION_KPI_DOMAINS",
]
