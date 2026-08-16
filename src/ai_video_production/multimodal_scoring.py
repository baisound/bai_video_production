"""TASK-008 deterministic, provider-neutral multimodal scoring contracts.

The module consumes canonical in-memory feature coordinates only. It has no
media reader, OCR engine, provider client, filesystem, subprocess, callback,
or downstream edit authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Iterable

from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes


_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_TASK_ID_RE = re.compile(r"^TASK-[0-9]{3}$")
_STABLE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_FEATURE_KEY_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+){0,7}$")
_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_MAX_RULES = 128
_MAX_OBSERVATIONS = 256
_MAX_CANDIDATES = 100_000
_MIN_RAW_VALUE = -1_000_000_000
_MAX_RAW_VALUE = 1_000_000_000


def _sha256(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be sha256:<64 lowercase hex>")
    return value


def _bounded_int(value: int, field_name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{field_name} must be an integer in {minimum}..{maximum}")
    return value


class FeatureModality(str, Enum):
    AUDIO = "AUDIO"
    VISUAL = "VISUAL"
    LANGUAGE_TEXT = "LANGUAGE_TEXT"
    OCR_TEXT = "OCR_TEXT"


class FeaturePolarity(str, Enum):
    DIRECT = "DIRECT"
    INVERSE = "INVERSE"


class EvidenceValidity(str, Enum):
    CURRENT_VALID = "CURRENT_VALID"
    STALE = "STALE"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"


class CandidateScoreState(str, Enum):
    COMPLETE = "COMPLETE"
    MISSING_REQUIRED_FEATURE = "MISSING_REQUIRED_FEATURE"
    UNKNOWN_EVIDENCE = "UNKNOWN_EVIDENCE"
    STALE_OR_REVOKED_EVIDENCE = "STALE_OR_REVOKED_EVIDENCE"


@dataclass(frozen=True, slots=True, order=True)
class FeatureSourceSelector:
    producer_task_id: str
    contract_id: str

    def __post_init__(self) -> None:
        if not _TASK_ID_RE.fullmatch(self.producer_task_id):
            raise ValueError("producer_task_id must be TASK-<3 digits>")
        if not _STABLE_ID_RE.fullmatch(self.contract_id):
            raise ValueError("contract_id is invalid")

    def to_dict(self) -> dict[str, str]:
        return {"producer_task_id": self.producer_task_id, "contract_id": self.contract_id}


@dataclass(frozen=True, slots=True)
class FeatureProvenance:
    source: FeatureSourceSelector
    manifest_sha256: str
    row_id: str
    row_sha256: str
    validity: EvidenceValidity

    def __post_init__(self) -> None:
        if not isinstance(self.source, FeatureSourceSelector):
            raise ValueError("source must be a FeatureSourceSelector")
        if not isinstance(self.validity, EvidenceValidity):
            raise ValueError("validity must be an EvidenceValidity")
        _sha256(self.manifest_sha256, "manifest_sha256")
        _sha256(self.row_sha256, "row_sha256")
        if not _STABLE_ID_RE.fullmatch(self.row_id):
            raise ValueError("row_id is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source.to_dict(),
            "manifest_sha256": self.manifest_sha256,
            "row_id": self.row_id,
            "row_sha256": self.row_sha256,
            "validity": self.validity.value,
        }


@dataclass(frozen=True, slots=True)
class FeatureRule:
    feature_key: str
    modality: FeatureModality
    weight_milli: int
    raw_minimum: int
    raw_maximum: int
    polarity: FeaturePolarity
    required: bool
    optional_missing_value_milli: int | None
    allowed_sources: tuple[FeatureSourceSelector, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.modality, FeatureModality):
            raise ValueError("modality must be a FeatureModality")
        if not isinstance(self.polarity, FeaturePolarity):
            raise ValueError("polarity must be a FeaturePolarity")
        if not _FEATURE_KEY_RE.fullmatch(self.feature_key):
            raise ValueError("feature_key is invalid")
        _bounded_int(self.weight_milli, "weight_milli", 1, 1000)
        _bounded_int(self.raw_minimum, "raw_minimum", _MIN_RAW_VALUE, _MAX_RAW_VALUE)
        _bounded_int(self.raw_maximum, "raw_maximum", _MIN_RAW_VALUE, _MAX_RAW_VALUE)
        if self.raw_maximum <= self.raw_minimum:
            raise ValueError("raw_maximum must be greater than raw_minimum")
        if not isinstance(self.required, bool):
            raise ValueError("required must be boolean")
        if self.required:
            if self.optional_missing_value_milli is not None:
                raise ValueError("required rule cannot define an optional missing value")
        else:
            _bounded_int(
                self.optional_missing_value_milli,
                "optional_missing_value_milli",
                0,
                1000,
            )
        if not 1 <= len(self.allowed_sources) <= 32:
            raise ValueError("allowed_sources must contain 1-32 selectors")
        if any(not isinstance(item, FeatureSourceSelector) for item in self.allowed_sources):
            raise ValueError("allowed_sources must contain FeatureSourceSelector values")
        if self.allowed_sources != tuple(sorted(set(self.allowed_sources))):
            raise ValueError("allowed_sources must be unique and canonically sorted")

    def normalize(self, raw_value: int) -> int:
        _bounded_int(raw_value, "raw_value", self.raw_minimum, self.raw_maximum)
        span = self.raw_maximum - self.raw_minimum
        direct = ((raw_value - self.raw_minimum) * 1000 + span // 2) // span
        return direct if self.polarity is FeaturePolarity.DIRECT else 1000 - direct

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_key": self.feature_key,
            "modality": self.modality.value,
            "weight_milli": self.weight_milli,
            "raw_range": {"minimum": self.raw_minimum, "maximum": self.raw_maximum},
            "polarity": self.polarity.value,
            "required": self.required,
            "optional_missing_value_milli": self.optional_missing_value_milli,
            "allowed_sources": [item.to_dict() for item in self.allowed_sources],
        }


@dataclass(frozen=True, slots=True)
class ScoringProfile:
    profile_id: str
    profile_version: str
    rules: tuple[FeatureRule, ...]

    def __post_init__(self) -> None:
        if not _STABLE_ID_RE.fullmatch(self.profile_id):
            raise ValueError("profile_id is invalid")
        if not _SEMVER_RE.fullmatch(self.profile_version):
            raise ValueError("profile_version must be semantic version x.y.z")
        if not 2 <= len(self.rules) <= _MAX_RULES:
            raise ValueError("rules must contain 2-128 entries")
        if any(not isinstance(item, FeatureRule) for item in self.rules):
            raise ValueError("rules must contain FeatureRule values")
        keys = tuple(item.feature_key for item in self.rules)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("rules must have unique, canonically sorted feature keys")
        if sum(item.weight_milli for item in self.rules) != 1000:
            raise ValueError("rule weights must sum to exactly 1000")
        if len({item.modality for item in self.rules}) < 2:
            raise ValueError("multimodal profile must contain at least two modalities")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "rules": [item.to_dict() for item in self.rules],
        }
        body["profile_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(frozen=True, slots=True)
class FeatureObservation:
    feature_key: str
    modality: FeatureModality
    raw_value: int
    provenance: FeatureProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.modality, FeatureModality):
            raise ValueError("modality must be a FeatureModality")
        if not isinstance(self.provenance, FeatureProvenance):
            raise ValueError("provenance must be a FeatureProvenance")
        if not _FEATURE_KEY_RE.fullmatch(self.feature_key):
            raise ValueError("feature_key is invalid")
        _bounded_int(self.raw_value, "raw_value", _MIN_RAW_VALUE, _MAX_RAW_VALUE)


@dataclass(frozen=True, slots=True)
class CandidateFeatureInput:
    candidate_id: str
    start_us: int
    end_us: int
    observations: tuple[FeatureObservation, ...]

    def __post_init__(self) -> None:
        validate_id(self.candidate_id, IdKind.CANDIDATE)
        _bounded_int(self.start_us, "start_us", 0, (1 << 63) - 1)
        _bounded_int(self.end_us, "end_us", 1, (1 << 63) - 1)
        if self.end_us <= self.start_us:
            raise ValueError("candidate range must be positive and end-exclusive")
        if len(self.observations) > _MAX_OBSERVATIONS:
            raise ValueError("observations exceed the 256-entry cap")
        if any(not isinstance(item, FeatureObservation) for item in self.observations):
            raise ValueError("observations must contain FeatureObservation values")


@dataclass(frozen=True, slots=True)
class FeatureEvaluation:
    rule: FeatureRule
    observation: FeatureObservation | None
    disposition: str
    normalized_value_milli: int | None
    weighted_units: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_key": self.rule.feature_key,
            "modality": self.rule.modality.value,
            "required": self.rule.required,
            "disposition": self.disposition,
            "raw_value": None if self.observation is None else self.observation.raw_value,
            "normalized_value_milli": self.normalized_value_milli,
            "weight_milli": self.rule.weight_milli,
            "weighted_units": self.weighted_units,
            "provenance": None if self.observation is None else self.observation.provenance.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class CandidateScore:
    candidate_id: str
    start_us: int
    end_us: int
    state: CandidateScoreState
    evaluations: tuple[FeatureEvaluation, ...]
    missing_required_feature_keys: tuple[str, ...]
    unknown_feature_keys: tuple[str, ...]
    stale_or_revoked_feature_keys: tuple[str, ...]
    composite_score_milli: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "range_us": {"start": self.start_us, "end_exclusive": self.end_us},
            "state": self.state.value,
            "feature_evaluations": [item.to_dict() for item in self.evaluations],
            "missing_required_feature_keys": list(self.missing_required_feature_keys),
            "unknown_feature_keys": list(self.unknown_feature_keys),
            "stale_or_revoked_feature_keys": list(self.stale_or_revoked_feature_keys),
            "composite_score_milli": self.composite_score_milli,
            "human_review_required": True,
            "automatic_edit_decision_authorized": False,
        }


@dataclass(frozen=True, slots=True)
class MultimodalScoringManifest:
    source_asset_id: str
    source_edit_plan_sha256: str
    profile: ScoringProfile
    scores: tuple[CandidateScore, ...]

    def __post_init__(self) -> None:
        validate_id(self.source_asset_id, IdKind.ASSET)
        _sha256(self.source_edit_plan_sha256, "source_edit_plan_sha256")
        if not 1 <= len(self.scores) <= _MAX_CANDIDATES:
            raise ValueError("scores must contain 1-100000 candidates")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "manifest_version": "1.0.0",
            "task_owner": "TASK-008",
            "upstream_graph_owner": "TASK-007",
            "source_asset_id": self.source_asset_id,
            "source_edit_plan_sha256": self.source_edit_plan_sha256,
            "scoring_profile": self.profile.to_dict(),
            "candidate_scores": [item.to_dict() for item in self.scores],
            "review_state": "REVIEW_REQUIRED",
            "downstream_edit_plan_use": "ADVISORY_ONLY",
            "media_read_performed": False,
            "ocr_execution_performed": False,
            "provider_execution_authorized": False,
            "automatic_edit_plan_mutation_authorized": False,
        }
        body["manifest_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


def compile_multimodal_scores(
    source_asset_id: str,
    source_edit_plan_sha256: str,
    profile: ScoringProfile,
    candidates: Iterable[CandidateFeatureInput],
) -> MultimodalScoringManifest:
    """Compile bounded canonical feature rows into advisory candidate scores."""

    validate_id(source_asset_id, IdKind.ASSET)
    _sha256(source_edit_plan_sha256, "source_edit_plan_sha256")
    candidate_rows = tuple(candidates)
    if not 1 <= len(candidate_rows) <= _MAX_CANDIDATES:
        raise ValueError("candidates must contain 1-100000 rows")
    candidate_ids = [item.candidate_id for item in candidate_rows]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("candidate_id values must be unique")

    rules = {item.feature_key: item for item in profile.rules}
    compiled = tuple(
        _compile_candidate(item, rules)
        for item in sorted(candidate_rows, key=lambda row: (row.start_us, row.end_us, row.candidate_id))
    )
    return MultimodalScoringManifest(source_asset_id, source_edit_plan_sha256, profile, compiled)


def _compile_candidate(candidate: CandidateFeatureInput, rules: dict[str, FeatureRule]) -> CandidateScore:
    observations: dict[str, FeatureObservation] = {}
    for observation in candidate.observations:
        if observation.feature_key in observations:
            raise ValueError(f"duplicate feature observation: {observation.feature_key}")
        rule = rules.get(observation.feature_key)
        if rule is None:
            raise ValueError(f"feature is not declared by the scoring profile: {observation.feature_key}")
        if observation.modality is not rule.modality:
            raise ValueError(f"feature modality mismatch: {observation.feature_key}")
        if observation.provenance.source not in rule.allowed_sources:
            raise ValueError(f"feature provenance is not allowed: {observation.feature_key}")
        if not rule.raw_minimum <= observation.raw_value <= rule.raw_maximum:
            raise ValueError(f"feature raw value is outside the profile range: {observation.feature_key}")
        observations[observation.feature_key] = observation

    evaluations: list[FeatureEvaluation] = []
    missing: list[str] = []
    unknown: list[str] = []
    stale_or_revoked: list[str] = []
    total_weighted_units = 0
    for rule in rules.values():
        observation = observations.get(rule.feature_key)
        if observation is None:
            if rule.required:
                missing.append(rule.feature_key)
                evaluations.append(FeatureEvaluation(rule, None, "MISSING_REQUIRED", None, None))
            else:
                assert rule.optional_missing_value_milli is not None
                normalized = rule.optional_missing_value_milli
                weighted = normalized * rule.weight_milli
                total_weighted_units += weighted
                evaluations.append(FeatureEvaluation(rule, None, "DEFAULTED_OPTIONAL", normalized, weighted))
            continue

        validity = observation.provenance.validity
        if validity is EvidenceValidity.UNKNOWN:
            unknown.append(rule.feature_key)
            evaluations.append(FeatureEvaluation(rule, observation, "UNKNOWN_EVIDENCE", None, None))
            continue
        if validity in {EvidenceValidity.STALE, EvidenceValidity.REVOKED}:
            stale_or_revoked.append(rule.feature_key)
            evaluations.append(FeatureEvaluation(rule, observation, validity.value, None, None))
            continue
        normalized = rule.normalize(observation.raw_value)
        weighted = normalized * rule.weight_milli
        total_weighted_units += weighted
        evaluations.append(FeatureEvaluation(rule, observation, "OBSERVED_CURRENT", normalized, weighted))

    if stale_or_revoked:
        state = CandidateScoreState.STALE_OR_REVOKED_EVIDENCE
    elif unknown:
        state = CandidateScoreState.UNKNOWN_EVIDENCE
    elif missing:
        state = CandidateScoreState.MISSING_REQUIRED_FEATURE
    else:
        state = CandidateScoreState.COMPLETE
    score = None if state is not CandidateScoreState.COMPLETE else (total_weighted_units + 500) // 1000
    return CandidateScore(
        candidate.candidate_id,
        candidate.start_us,
        candidate.end_us,
        state,
        tuple(evaluations),
        tuple(missing),
        tuple(unknown),
        tuple(stale_or_revoked),
        score,
    )


def verify_multimodal_scoring_manifest_hash(payload: dict[str, Any]) -> None:
    """Verify the non-self digest without accepting a digest-only substitute."""

    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")
    body = dict(payload)
    claimed = body.pop("manifest_sha256", None)
    _sha256(claimed, "manifest_sha256")
    if claimed != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError("manifest_sha256 does not match the canonical manifest body")
