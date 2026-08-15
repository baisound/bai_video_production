"""TASK-048 P-QC-1A body-free voice-quality calibration contract.

The module is deliberately a pure metadata/control-plane implementation.  It
does not read audio, run an analyzer, operate OBS/RX or hardware, persist an
Asset, dispatch a Job, or mutate a Dataset/Model/production setting.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import datetime
from enum import Enum
import math
import re
from typing import Any, ClassVar, Iterable, Mapping, Sequence

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


VOICE_QUALITY_CALIBRATION_VERSION = "1.0.0"
TASK_OWNER = "TASK-048/P-QC-1A"
SAMPLE_RATE = 48_000
BIT_DEPTH = 24
CHANNELS = 1
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}")


class ContractState(str, Enum):
    CANONICAL_REF_NOT_PROVIDED = "CANONICAL_REF_NOT_PROVIDED"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class MetricValueState(str, Enum):
    DECLARED = "DECLARED"
    MEASURED = "MEASURED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    INSUFFICIENT_INPUT = "INSUFFICIENT_INPUT"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class MeasurementFactValidity(str, Enum):
    VALID = "VALID"
    INVALID_INPUT = "INVALID_INPUT"
    UNKNOWN = "UNKNOWN"


class QualityState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    RERECORD_RECOMMENDED = "RERECORD_RECOMMENDED"


class MeasurementSourceClass(str, Enum):
    CALIBRATION_STAGING_EVIDENCE = "CALIBRATION_STAGING_EVIDENCE"
    TASK003_ASSET_REVISION = "TASK003_ASSET_REVISION"


class MetricInputKind(str, Enum):
    SINGLE_RANGE = "SINGLE_RANGE"
    ORDERED_MULTI_RANGE = "ORDERED_MULTI_RANGE"
    PAIRED_BEFORE_AFTER = "PAIRED_BEFORE_AFTER"


class MetricInputRole(str, Enum):
    SIGNAL = "SIGNAL"
    NOISE = "NOISE"
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    TARGET = "TARGET"
    REFERENCE = "REFERENCE"


class ProcessingClass(str, Enum):
    RAW_PRE_FILTER = "RAW_PRE_FILTER"
    OBS_POST_FILTER = "OBS_POST_FILTER"
    CANONICAL_CONVERTED_RAW = "CANONICAL_CONVERTED_RAW"
    RX_DERIVED = "RX_DERIVED"


class CaptureChainStageKind(str, Enum):
    MIC_PAD_HPF = "MIC_PAD_HPF"
    INTERFACE_ANALOGUE_PREAMP = "INTERFACE_ANALOGUE_PREAMP"
    DRIVER_OS_ENDPOINT = "DRIVER_OS_ENDPOINT"
    OBS_SOURCE = "OBS_SOURCE"
    OBS_FILTERS = "OBS_FILTERS"
    OBS_MIXER = "OBS_MIXER"
    PLUGIN_CAPTURE_TAP = "PLUGIN_CAPTURE_TAP"
    NON_REALTIME_CANONICAL_CONVERSION = "NON_REALTIME_CANONICAL_CONVERSION"


class RecommendationState(str, Enum):
    PROPOSED = "PROPOSED"
    OWNER_APPROVED = "OWNER_APPROVED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


_EXPECTED_STAGE_ORDER = tuple(CaptureChainStageKind)
_BODY_FLAGS = {
    "audio_body_persisted": False,
    "raw_sample_body_persisted": False,
    "transcript_body_persisted": False,
    "credential_value_persisted": False,
    "host_absolute_path_persisted": False,
    "device_fingerprint_public": False,
    "capture_or_staging_write_authorized": False,
    "asset_effect_authorized": False,
    "analyzer_execution_authorized": False,
    "obs_rx_device_effect_authorized": False,
    "dataset_training_production_authorized": False,
}
_PRIVATE_KEYS = {
    "capture_receipt_ref", "staging_owner_ref", "encrypted_staging_object_ref",
    "staging_object_sha256", "canonical_mapping_receipt_ref",
    "canonical_mapping_receipt_sha256", "asset_id", "asset_checksum_sha256",
    "asset_record_evidence_sha256", "asset_revision_binding_ref",
    "asset_revision_binding_sha256", "stable_private_ref",
    "observed_display_name", "evidence_ref", "owner_evidence_ref",
    "source_asset_ref", "derived_asset_ref", "source_asset_sha256",
    "derived_asset_sha256", "range_ref", "range_sha256", "intervals",
    "metric_fact_refs", "measurement_receipt_refs", "approved_label_index_ref",
    "approved_label_index_sha256", "questionnaire_ref", "human_input_ref",
}
_SUPPRESSED_DETAIL_KEYS = {
    "numerator_sample_count", "denominator_sample_count", "percentage_basis_points",
    "duration", "estimated_duration", "coverage_buckets", "approved_labels",
    "metric_name", "unit", "value", "input_refs", "source_binding",
    "start_sample", "end_sample", "receipt_index_sha256",
    "current_receipt_index_sha256", "eligible_interval_index_sha256",
    "member_count", "item_count",
}


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _timestamp(value: str, name: str = "timestamp") -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{name} must be a UTC RFC3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be a UTC RFC3339 timestamp") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{name} must be UTC")
    return value


def _digest(value: str | None, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    validate_sha256(value or "", field_name=name)
    return value


def _integer(value: int, name: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _bool(value: bool, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be boolean")
    return value


def _expect_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _enum(enum_type: type[Enum], value: Any, name: str) -> Enum:
    try:
        return value if isinstance(value, enum_type) else enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


def canonical_sha256(value: Any) -> str:
    """Return the repository canonical JSON digest for in-memory metadata."""
    return sha256_bytes(canonical_json_bytes(value))


def _revision_guard(revision: int, parent_sha256: str | None, name: str) -> None:
    _integer(revision, f"{name}.revision", minimum=1)
    if revision == 1:
        if parent_sha256 is not None:
            raise ValueError(f"{name} first revision cannot have a parent")
    else:
        _digest(parent_sha256, f"{name}.parent_revision_sha256")


def _body_flags(value: Mapping[str, Any]) -> None:
    _expect_keys(value, set(_BODY_FLAGS), "body_authority_flags")
    if dict(value) != _BODY_FLAGS:
        raise ValueError("body and external-effect authority flags must remain false")


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class RationalSampleDuration:
    sample_count: int
    denominator: int = SAMPLE_RATE

    def __post_init__(self) -> None:
        _integer(self.sample_count, "sample_count")
        if self.denominator != SAMPLE_RATE:
            raise ValueError("canonical duration denominator must be 48000")

    def to_dict(self) -> dict[str, int]:
        return {"sample_count": self.sample_count, "denominator": self.denominator}


@dataclass(frozen=True, slots=True, order=True)
class HalfOpenSampleInterval:
    start_sample: int
    end_sample: int

    def __post_init__(self) -> None:
        _integer(self.start_sample, "start_sample")
        _integer(self.end_sample, "end_sample", minimum=1)
        if self.start_sample >= self.end_sample:
            raise ValueError("sample interval must be non-empty and half-open")

    @property
    def sample_count(self) -> int:
        return self.end_sample - self.start_sample

    def to_dict(self) -> dict[str, int]:
        return {"start_sample": self.start_sample, "end_sample": self.end_sample}


@dataclass(frozen=True, slots=True)
class CaptureChainStage:
    stage_index: int
    stage_kind: CaptureChainStageKind
    stage_id: str
    stage_revision: int
    stage_sha256: str
    settings_sha256: str
    processing_state: str
    phantom_power_observation_state: str
    pad_observation_state: str
    hpf_observation_state: str
    preamp_gain_observation_state: str
    hidden_processing_state: str
    gain_role: str
    previous_stage_sha256: str | None
    next_stage_sha256: str | None
    evidence_ref: str
    evidence_sha256: str
    stable_private_ref: str | None
    stable_private_ref_sha256: str | None
    observed_display_name: str | None
    automatic_change_authorized: bool = False

    def __post_init__(self) -> None:
        _integer(self.stage_index, "stage_index", minimum=1)
        if not isinstance(self.stage_kind, CaptureChainStageKind):
            raise ValueError("stage_kind must be CaptureChainStageKind")
        _id(self.stage_id, "stage_id")
        _integer(self.stage_revision, "stage_revision", minimum=1)
        for name in ("stage_sha256", "settings_sha256", "evidence_sha256"):
            _digest(getattr(self, name), name)
        _id(self.evidence_ref, "evidence_ref")
        for name in ("previous_stage_sha256", "next_stage_sha256", "stable_private_ref_sha256"):
            _digest(getattr(self, name), name, nullable=True)
        if self.stable_private_ref is not None:
            _id(self.stable_private_ref, "stable_private_ref")
        if self.processing_state not in {"DECLARED", "OBSERVED", "UNKNOWN"}:
            raise ValueError("processing_state is invalid")
        observation_states = {"DECLARED", "MEASURED", "OBSERVED", "UNKNOWN", "NOT_APPLICABLE"}
        for name in (
            "phantom_power_observation_state", "pad_observation_state",
            "hpf_observation_state", "preamp_gain_observation_state",
        ):
            if getattr(self, name) not in observation_states:
                raise ValueError(f"{name} is invalid")
        if self.stage_kind is CaptureChainStageKind.MIC_PAD_HPF and any(
            getattr(self, name) == "NOT_APPLICABLE"
            for name in ("phantom_power_observation_state", "pad_observation_state", "hpf_observation_state")
        ):
            raise ValueError("mic +48V/PAD/HPF observation states are required")
        if (
            self.stage_kind is CaptureChainStageKind.INTERFACE_ANALOGUE_PREAMP
            and self.preamp_gain_observation_state == "NOT_APPLICABLE"
        ):
            raise ValueError("interface preamp gain observation state is required")
        if self.hidden_processing_state not in {"CLEAR", "DETECTED", "UNKNOWN"}:
            raise ValueError("hidden_processing_state is invalid")
        if self.gain_role not in {"NONE", "PRIMARY", "DECLARED_SECONDARY", "UNKNOWN"}:
            raise ValueError("gain_role is invalid")
        if self.automatic_change_authorized:
            raise ValueError("hardware/software stage auto-change is never authorized")
        if self.stage_kind is CaptureChainStageKind.DRIVER_OS_ENDPOINT:
            if self.stable_private_ref is None or self.stable_private_ref_sha256 is None:
                raise ValueError("endpoint identity cannot rely on display name alone")

    def to_dict(self) -> dict[str, Any]:
        return {field.name: _plain(getattr(self, field.name)) for field in fields(self)}


@dataclass(frozen=True, slots=True)
class MetricInputReference:
    role: MetricInputRole
    range_ref: str
    range_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.role, MetricInputRole):
            raise ValueError("role must be MetricInputRole")
        _id(self.range_ref, "range_ref")
        _digest(self.range_sha256, "range_sha256")

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role.value, "range_ref": self.range_ref, "range_sha256": self.range_sha256}


@dataclass(frozen=True, slots=True)
class RecordReference:
    record_ref: str
    record_sha256: str

    def __post_init__(self) -> None:
        _id(self.record_ref, "record_ref")
        _digest(self.record_sha256, "record_sha256")

    def to_dict(self) -> dict[str, str]:
        return {"record_ref": self.record_ref, "record_sha256": self.record_sha256}


@dataclass(frozen=True, slots=True)
class CoverageIntervalEntry:
    source_identity_sha256: str
    processing_class: ProcessingClass
    policy_scope: str
    interval: HalfOpenSampleInterval
    receipt_sha256: str
    receipt_state: QualityState
    policy_revision_sha256: str
    current: bool
    tampered: bool
    retry_group_id: str

    def __post_init__(self) -> None:
        for name in ("source_identity_sha256", "receipt_sha256", "policy_revision_sha256"):
            _digest(getattr(self, name), name)
        if not isinstance(self.processing_class, ProcessingClass):
            raise ValueError("processing_class must be ProcessingClass")
        _id(self.policy_scope, "policy_scope")
        if not isinstance(self.interval, HalfOpenSampleInterval):
            raise ValueError("interval must be HalfOpenSampleInterval")
        if not isinstance(self.receipt_state, QualityState):
            raise ValueError("receipt_state must be QualityState")
        _bool(self.current, "current")
        _bool(self.tampered, "tampered")
        _id(self.retry_group_id, "retry_group_id")

    def to_dict(self) -> dict[str, Any]:
        return {field.name: _plain(getattr(self, field.name)) for field in fields(self)}


@dataclass(frozen=True, slots=True)
class IntervalUnionResult:
    state: QualityState
    intervals_by_index: Mapping[str, tuple[HalfOpenSampleInterval, ...]]
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CoverageCalculation:
    numerator_sample_count: int
    denominator_sample_count: int
    percentage_basis_points: int
    processing_class: ProcessingClass
    policy_scope: str

    def __post_init__(self) -> None:
        _integer(self.numerator_sample_count, "numerator_sample_count")
        _integer(self.denominator_sample_count, "denominator_sample_count", minimum=1)
        if self.numerator_sample_count > self.denominator_sample_count:
            raise ValueError("coverage numerator cannot exceed denominator")
        expected = self.numerator_sample_count * 10_000 // self.denominator_sample_count
        if self.percentage_basis_points != expected or not 0 <= self.percentage_basis_points <= 10_000:
            raise ValueError("percentage must be the integer-rational canonical value")


@dataclass(frozen=True, slots=True)
class QualityClassification:
    state: QualityState
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _RevisionRecord:
    project_id: str
    revision: int
    parent_revision_sha256: str | None
    created_at: str
    body_authority_flags: Mapping[str, Any]

    record_type: ClassVar[str]
    hash_field: ClassVar[str]
    identity_fields: ClassVar[tuple[str, ...]]

    def __post_init__(self) -> None:
        _id(self.project_id, "project_id")
        _revision_guard(self.revision, self.parent_revision_sha256, self.record_type)
        _timestamp(self.created_at, "created_at")
        _body_flags(self.body_authority_flags)
        self._validate_payload()

    def _validate_payload(self) -> None:
        raise NotImplementedError

    def _payload(self) -> Mapping[str, Any]:
        common = {"project_id", "revision", "parent_revision_sha256", "created_at", "body_authority_flags"}
        return {field.name: _plain(getattr(self, field.name)) for field in fields(self) if field.name not in common}

    def _body(self) -> dict[str, Any]:
        return {
            "voice_quality_contract_version": VOICE_QUALITY_CALIBRATION_VERSION,
            "record_type": self.record_type,
            "task_owner": TASK_OWNER,
            "project_id": self.project_id,
            "revision": self.revision,
            "parent_revision_sha256": self.parent_revision_sha256,
            "created_at": self.created_at,
            **dict(self._payload()),
            "body_authority_flags": dict(self.body_authority_flags),
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self._body())

    def to_private_dict(self) -> dict[str, Any]:
        body = self._body()
        return {**body, self.hash_field: canonical_sha256(body)}


def _validate_ref_pair(ref: str | None, digest: str | None, name: str, *, required: bool) -> None:
    if required and (ref is None or digest is None):
        raise ValueError(f"{name} canonical ref/hash are required")
    if ref is not None:
        _id(ref, f"{name}_ref")
    _digest(digest, f"{name}_sha256", nullable=True)


def _validate_reason_codes(value: Sequence[str], name: str = "reason_codes") -> None:
    if not isinstance(value, tuple) or not value:
        raise ValueError(f"{name} must be a non-empty tuple")
    if len(value) != len(set(value)):
        raise ValueError(f"{name} must not contain duplicates")
    for item in value:
        _id(item, name)


@dataclass(frozen=True, slots=True)
class CaptureChainRevision(_RevisionRecord):
    capture_chain_id: str
    sample_rate: int
    bit_depth: int
    channels: int
    stages: tuple[CaptureChainStage, ...]
    calibration_state: QualityState
    human_input_binding_sha256: str

    record_type = "CaptureChainRevision"
    hash_field = "capture_chain_revision_sha256"
    identity_fields = ("project_id", "capture_chain_id")

    def _validate_payload(self) -> None:
        _id(self.capture_chain_id, "capture_chain_id")
        if (self.sample_rate, self.bit_depth, self.channels) != (SAMPLE_RATE, BIT_DEPTH, CHANNELS):
            raise ValueError("capture format must be 48kHz/24-bit/mono")
        if not isinstance(self.calibration_state, QualityState):
            raise ValueError("calibration_state must be QualityState")
        _digest(self.human_input_binding_sha256, "human_input_binding_sha256")
        validate_capture_chain(self)


@dataclass(frozen=True, slots=True)
class CalibrationProfileRevision(_RevisionRecord):
    calibration_profile_id: str
    capture_chain_revision_sha256: str
    scenario: str
    processing_class: ProcessingClass
    sample_rate: int
    bit_depth: int
    channels: int
    policy_scope: str

    record_type = "CalibrationProfileRevision"
    hash_field = "calibration_profile_revision_sha256"
    identity_fields = ("project_id", "calibration_profile_id")

    def _validate_payload(self) -> None:
        _id(self.calibration_profile_id, "calibration_profile_id")
        _digest(self.capture_chain_revision_sha256, "capture_chain_revision_sha256")
        if self.scenario not in {"ROOM_TONE", "NORMAL_VOICE", "LOUD_VOICE", "WHISPER", "SOFT_WHISPER", "NORMAL_INTERMEDIATE"}:
            raise ValueError("calibration scenario is invalid")
        if not isinstance(self.processing_class, ProcessingClass):
            raise ValueError("processing_class must be ProcessingClass")
        if (self.sample_rate, self.bit_depth, self.channels) != (SAMPLE_RATE, BIT_DEPTH, CHANNELS):
            raise ValueError("calibration profile format must be 48kHz/24-bit/mono")
        _id(self.policy_scope, "policy_scope")


@dataclass(frozen=True, slots=True)
class QualityPolicyRevision(_RevisionRecord):
    quality_policy_id: str
    use_case_scope: str
    metric_rules_sha256: str
    precedence_rule: str
    conflict_rule: str
    percentage_policy_state: ContractState
    target_percentage_basis_points: int | None
    privacy_policy_binding_sha256: str
    default_valid_decision: QualityState

    record_type = "QualityPolicyRevision"
    hash_field = "quality_policy_revision_sha256"
    identity_fields = ("project_id", "quality_policy_id")

    def _validate_payload(self) -> None:
        _id(self.quality_policy_id, "quality_policy_id")
        if self.use_case_scope not in {"NARRATION_RECORDING", "TRAINING_SOURCE", "PUBLISHED_PROGRAMME", "MODEL_EVALUATION"}:
            raise ValueError("use_case_scope is invalid")
        _digest(self.metric_rules_sha256, "metric_rules_sha256")
        if self.precedence_rule not in {"EXACT_CURRENT_ONLY", "EXPLICIT_ORDER", "UNKNOWN"}:
            raise ValueError("precedence_rule is invalid")
        if self.conflict_rule not in {"FAIL_WINS", "EXPLICIT_PRECEDENCE", "UNKNOWN"}:
            raise ValueError("conflict_rule is invalid")
        if not isinstance(self.percentage_policy_state, ContractState):
            raise ValueError("percentage_policy_state must be ContractState")
        if self.target_percentage_basis_points is not None:
            _integer(self.target_percentage_basis_points, "target_percentage_basis_points")
            if self.target_percentage_basis_points > 10_000:
                raise ValueError("target percentage cannot exceed 100 percent")
        if self.percentage_policy_state is not ContractState.BOUND_VERIFIED and self.target_percentage_basis_points is not None:
            raise ValueError("unbound policy cannot publish a percentage target")
        _digest(self.privacy_policy_binding_sha256, "privacy_policy_binding_sha256")
        if not isinstance(self.default_valid_decision, QualityState):
            raise ValueError("default_valid_decision must be QualityState")
        if self.default_valid_decision is QualityState.PASS and self.precedence_rule == "UNKNOWN":
            raise ValueError("unknown precedence cannot default to PASS")


@dataclass(frozen=True, slots=True)
class AnalyzerProfileRevision(_RevisionRecord):
    analyzer_profile_id: str
    analyzer_name: str
    analyzer_version: str
    code_sha256: str
    supported_metrics: tuple[str, ...]
    capability_evidence_sha256: str
    contract_state: ContractState

    record_type = "AnalyzerProfileRevision"
    hash_field = "analyzer_profile_revision_sha256"
    identity_fields = ("project_id", "analyzer_profile_id")

    def _validate_payload(self) -> None:
        for value, name in ((self.analyzer_profile_id, "analyzer_profile_id"), (self.analyzer_name, "analyzer_name"), (self.analyzer_version, "analyzer_version")):
            _id(value, name)
        for name in ("code_sha256", "capability_evidence_sha256"):
            _digest(getattr(self, name), name)
        if not isinstance(self.supported_metrics, tuple) or len(self.supported_metrics) != len(set(self.supported_metrics)):
            raise ValueError("supported_metrics must be a unique tuple")
        for metric in self.supported_metrics:
            _id(metric, "supported_metric")
        if not isinstance(self.contract_state, ContractState):
            raise ValueError("contract_state must be ContractState")


@dataclass(frozen=True, slots=True)
class CalibrationSessionRevision(_RevisionRecord):
    calibration_session_id: str
    state: str
    capture_chain_revision_sha256: str
    calibration_profile_revision_sha256: str
    quality_policy_revision_sha256: str
    analyzer_profile_revision_sha256: str
    human_input_binding_sha256: str
    capture_evidence_binding_sha256: str
    production_admission: bool

    record_type = "CalibrationSessionRevision"
    hash_field = "calibration_session_revision_sha256"
    identity_fields = ("project_id", "calibration_session_id")

    def _validate_payload(self) -> None:
        _id(self.calibration_session_id, "calibration_session_id")
        if self.state not in {"DRAFT", "PREFLIGHT_PENDING", "BLOCKED", "READY_FOR_HUMAN_GATE", "MEASUREMENT_PENDING", "MEASURED", "FAILED_KNOWN", "UNKNOWN", "CANCELLED_SAFE"}:
            raise ValueError("calibration session state is invalid")
        for name in ("capture_chain_revision_sha256", "calibration_profile_revision_sha256", "quality_policy_revision_sha256", "analyzer_profile_revision_sha256", "human_input_binding_sha256", "capture_evidence_binding_sha256"):
            _digest(getattr(self, name), name)
        if self.production_admission:
            raise ValueError("calibration metadata never grants production admission")


@dataclass(frozen=True, slots=True)
class MeasurementInputRangeBinding(_RevisionRecord):
    measurement_input_range_id: str
    source_class: MeasurementSourceClass
    processing_class: ProcessingClass
    sample_rate: int
    bit_depth: int
    channels: int
    interval: HalfOpenSampleInterval
    canonical_mapping_sha256: str
    capture_chain_revision_sha256: str
    source_binding: Mapping[str, Any]

    record_type = "MeasurementInputRangeBinding"
    hash_field = "measurement_input_range_binding_sha256"
    identity_fields = ("project_id", "measurement_input_range_id")

    def _validate_payload(self) -> None:
        _id(self.measurement_input_range_id, "measurement_input_range_id")
        if not isinstance(self.source_class, MeasurementSourceClass):
            raise ValueError("source_class must be MeasurementSourceClass")
        if not isinstance(self.processing_class, ProcessingClass):
            raise ValueError("processing_class must be ProcessingClass")
        if (self.sample_rate, self.bit_depth, self.channels) != (SAMPLE_RATE, BIT_DEPTH, CHANNELS):
            raise ValueError("measurement range format must be 48kHz/24-bit/mono")
        if not isinstance(self.interval, HalfOpenSampleInterval):
            raise ValueError("interval must be HalfOpenSampleInterval")
        _digest(self.canonical_mapping_sha256, "canonical_mapping_sha256")
        _digest(self.capture_chain_revision_sha256, "capture_chain_revision_sha256")
        _validate_measurement_source(self.source_class, self.source_binding)


@dataclass(frozen=True, slots=True)
class StagingToTask003AssetPromotionBinding(_RevisionRecord):
    promotion_binding_id: str
    contract_state: ContractState
    staging_input_range_sha256: str | None
    asset_mapping_ref: str | None
    asset_mapping_sha256: str | None
    owner_decision_ref: str | None
    owner_decision_sha256: str | None
    effect_receipt_ref: str | None
    effect_receipt_sha256: str | None
    source_object_state_mutated: bool
    effect_issued_by_pqc: bool

    record_type = "StagingToTask003AssetPromotionBinding"
    hash_field = "staging_to_task003_asset_promotion_binding_sha256"
    identity_fields = ("project_id", "promotion_binding_id")

    def _validate_payload(self) -> None:
        _id(self.promotion_binding_id, "promotion_binding_id")
        if not isinstance(self.contract_state, ContractState):
            raise ValueError("contract_state must be ContractState")
        pairs = ((self.staging_input_range_sha256, "staging_input_range_sha256"), (self.asset_mapping_sha256, "asset_mapping_sha256"), (self.owner_decision_sha256, "owner_decision_sha256"), (self.effect_receipt_sha256, "effect_receipt_sha256"))
        for value, name in pairs:
            _digest(value, name, nullable=True)
        for value, name in ((self.asset_mapping_ref, "asset_mapping_ref"), (self.owner_decision_ref, "owner_decision_ref"), (self.effect_receipt_ref, "effect_receipt_ref")):
            if value is not None:
                _id(value, name)
        values = (self.staging_input_range_sha256, self.asset_mapping_ref, self.asset_mapping_sha256, self.owner_decision_ref, self.owner_decision_sha256, self.effect_receipt_ref, self.effect_receipt_sha256)
        if self.contract_state is ContractState.CANONICAL_REF_NOT_PROVIDED and any(item is not None for item in values):
            raise ValueError("unresolved promotion binding fields must be null")
        if self.contract_state is ContractState.BOUND_VERIFIED and any(item is None for item in values):
            raise ValueError("verified promotion binding is incomplete")
        if self.source_object_state_mutated or self.effect_issued_by_pqc:
            raise ValueError("P-QC cannot mutate/promote staging or issue the effect")


@dataclass(frozen=True, slots=True)
class MetricInputSetBinding(_RevisionRecord):
    metric_input_set_id: str
    input_kind: MetricInputKind
    purpose: str
    input_refs: tuple[MetricInputReference, ...]
    analyzer_profile_revision_sha256: str
    calibration_profile_revision_sha256: str
    quality_policy_revision_sha256: str
    compatibility_state: QualityState

    record_type = "MetricInputSetBinding"
    hash_field = "metric_input_set_binding_sha256"
    identity_fields = ("project_id", "metric_input_set_id")

    def _validate_payload(self) -> None:
        _id(self.metric_input_set_id, "metric_input_set_id")
        if not isinstance(self.input_kind, MetricInputKind):
            raise ValueError("input_kind must be MetricInputKind")
        _id(self.purpose, "purpose")
        for name in ("analyzer_profile_revision_sha256", "calibration_profile_revision_sha256", "quality_policy_revision_sha256"):
            _digest(getattr(self, name), name)
        if not isinstance(self.compatibility_state, QualityState):
            raise ValueError("compatibility_state must be QualityState")
        _validate_input_roles(self)


@dataclass(frozen=True, slots=True)
class MetricFact(_RevisionRecord):
    metric_fact_id: str
    metric_input_set_sha256: str
    metric_name: str
    unit: str
    value_state: MetricValueState
    value: int | float | None
    error_code: str | None
    evidence_sha256: str

    record_type = "MetricFact"
    hash_field = "metric_fact_sha256"
    identity_fields = ("project_id", "metric_fact_id")

    def _validate_payload(self) -> None:
        for value, name in ((self.metric_fact_id, "metric_fact_id"), (self.metric_name, "metric_name"), (self.unit, "unit")):
            _id(value, name)
        _digest(self.metric_input_set_sha256, "metric_input_set_sha256")
        _digest(self.evidence_sha256, "evidence_sha256")
        if not isinstance(self.value_state, MetricValueState):
            raise ValueError("value_state must be MetricValueState")
        if self.value_state is MetricValueState.MEASURED:
            if not isinstance(self.value, (int, float)) or isinstance(self.value, bool) or not math.isfinite(self.value):
                raise ValueError("MEASURED requires one finite numeric value")
            if self.error_code is not None:
                raise ValueError("MEASURED cannot carry an error_code")
        else:
            if self.value is not None:
                raise ValueError("non-MEASURED facts must keep value null")
            if self.value_state is MetricValueState.ERROR:
                if self.error_code is None:
                    raise ValueError("ERROR requires error_code")
                _id(self.error_code, "error_code")
            elif self.error_code is not None:
                raise ValueError("only ERROR can carry error_code")


@dataclass(frozen=True, slots=True)
class MeasurementReceipt(_RevisionRecord):
    measurement_receipt_id: str
    measured_at: str
    metric_input_set_ref: str
    metric_input_set_sha256: str
    analyzer_profile_ref: str
    analyzer_profile_revision_sha256: str
    calibration_profile_revision_sha256: str
    capture_chain_revision_sha256: str
    metric_fact_refs: tuple[RecordReference, ...]
    fact_validity: MeasurementFactValidity
    current: bool
    tampered: bool

    record_type = "MeasurementReceipt"
    hash_field = "measurement_receipt_sha256"
    identity_fields = ("project_id", "measurement_receipt_id")

    def _validate_payload(self) -> None:
        for value, name in ((self.measurement_receipt_id, "measurement_receipt_id"), (self.metric_input_set_ref, "metric_input_set_ref"), (self.analyzer_profile_ref, "analyzer_profile_ref")):
            _id(value, name)
        _timestamp(self.measured_at, "measured_at")
        for name in ("metric_input_set_sha256", "analyzer_profile_revision_sha256", "calibration_profile_revision_sha256", "capture_chain_revision_sha256"):
            _digest(getattr(self, name), name)
        if not isinstance(self.metric_fact_refs, tuple) or not self.metric_fact_refs:
            raise ValueError("measurement receipt requires ordered MetricFact refs")
        if len({ref.record_sha256 for ref in self.metric_fact_refs}) != len(self.metric_fact_refs):
            raise ValueError("measurement receipt contains duplicate MetricFact refs")
        if not isinstance(self.fact_validity, MeasurementFactValidity):
            raise ValueError("fact_validity must be MeasurementFactValidity")
        _bool(self.current, "current")
        _bool(self.tampered, "tampered")
        if self.tampered and self.fact_validity is MeasurementFactValidity.VALID:
            raise ValueError("tampered receipt cannot remain VALID")


@dataclass(frozen=True, slots=True)
class QualityEvaluationReceipt(_RevisionRecord):
    quality_evaluation_receipt_id: str
    evaluated_at: str
    measurement_receipt_refs: tuple[RecordReference, ...]
    receipt_index_sha256: str
    analyzer_profile_ref: str
    analyzer_profile_revision_sha256: str
    quality_policy_ref: str
    quality_policy_revision_sha256: str
    capture_chain_revision_sha256: str
    result: QualityState
    reason_codes: tuple[str, ...]
    precedence_digest: str
    conflict_state: str

    record_type = "QualityEvaluationReceipt"
    hash_field = "quality_evaluation_receipt_sha256"
    identity_fields = ("project_id", "quality_evaluation_receipt_id")

    def _validate_payload(self) -> None:
        for value, name in ((self.quality_evaluation_receipt_id, "quality_evaluation_receipt_id"), (self.analyzer_profile_ref, "analyzer_profile_ref"), (self.quality_policy_ref, "quality_policy_ref")):
            _id(value, name)
        _timestamp(self.evaluated_at, "evaluated_at")
        for name in ("receipt_index_sha256", "analyzer_profile_revision_sha256", "quality_policy_revision_sha256", "capture_chain_revision_sha256", "precedence_digest"):
            _digest(getattr(self, name), name)
        if not isinstance(self.measurement_receipt_refs, tuple) or not self.measurement_receipt_refs:
            raise ValueError("quality evaluation requires MeasurementReceipt refs")
        if not isinstance(self.result, QualityState):
            raise ValueError("result must be QualityState")
        _validate_reason_codes(self.reason_codes)
        if self.conflict_state not in {"CLEAR", "CONFLICT", "UNKNOWN"}:
            raise ValueError("conflict_state is invalid")
        if self.result is QualityState.PASS and self.conflict_state != "CLEAR":
            raise ValueError("conflict/unknown cannot be evaluated PASS")


@dataclass(frozen=True, slots=True)
class CaptureEvidenceBinding(_RevisionRecord):
    capture_evidence_binding_id: str
    contract_state: ContractState
    capture_receipt_ref: str | None
    capture_receipt_sha256: str | None
    staging_owner_ref: str | None
    staging_owner_sha256: str | None
    evidence_state: QualityState
    callback_bounded_copy_only: bool
    analyzer_in_callback: bool

    record_type = "CaptureEvidenceBinding"
    hash_field = "capture_evidence_binding_sha256"
    identity_fields = ("project_id", "capture_evidence_binding_id")

    def _validate_payload(self) -> None:
        _id(self.capture_evidence_binding_id, "capture_evidence_binding_id")
        if not isinstance(self.contract_state, ContractState):
            raise ValueError("contract_state must be ContractState")
        _validate_ref_pair(self.capture_receipt_ref, self.capture_receipt_sha256, "capture_receipt", required=self.contract_state is ContractState.BOUND_VERIFIED)
        _validate_ref_pair(self.staging_owner_ref, self.staging_owner_sha256, "staging_owner", required=self.contract_state is ContractState.BOUND_VERIFIED)
        if self.contract_state is ContractState.CANONICAL_REF_NOT_PROVIDED and any(
            value is not None for value in (self.capture_receipt_ref, self.capture_receipt_sha256, self.staging_owner_ref, self.staging_owner_sha256)
        ):
            raise ValueError("unresolved capture Evidence fields must be null")
        if not isinstance(self.evidence_state, QualityState):
            raise ValueError("evidence_state must be QualityState")
        if self.contract_state is not ContractState.BOUND_VERIFIED and self.evidence_state is QualityState.PASS:
            raise ValueError("unbound capture Evidence cannot PASS")
        if not self.callback_bounded_copy_only or self.analyzer_in_callback:
            raise ValueError("real-time callback permits bounded copy only and no analyzer")


@dataclass(frozen=True, slots=True)
class RXDerivedQualityBinding(_RevisionRecord):
    rx_derived_quality_binding_id: str
    contract_state: ContractState
    source_asset_ref: str | None
    source_asset_sha256: str | None
    derived_asset_ref: str | None
    derived_asset_sha256: str | None
    rx_version_ref: str | None
    rx_version_sha256: str | None
    module_preset_parameter_sha256: str | None
    render_receipt_ref: str | None
    render_receipt_sha256: str | None
    before_measurement_receipt_sha256: str | None
    after_measurement_receipt_sha256: str | None
    source_overwritten: bool
    raw_delete_authorized: bool
    dataset_adoption_authorized: bool

    record_type = "RXDerivedQualityBinding"
    hash_field = "rx_derived_quality_binding_sha256"
    identity_fields = ("project_id", "rx_derived_quality_binding_id")

    def _validate_payload(self) -> None:
        _id(self.rx_derived_quality_binding_id, "rx_derived_quality_binding_id")
        if not isinstance(self.contract_state, ContractState):
            raise ValueError("contract_state must be ContractState")
        ref_pairs = (
            (self.source_asset_ref, self.source_asset_sha256, "source_asset"),
            (self.derived_asset_ref, self.derived_asset_sha256, "derived_asset"),
            (self.rx_version_ref, self.rx_version_sha256, "rx_version"),
            (self.render_receipt_ref, self.render_receipt_sha256, "render_receipt"),
        )
        required = self.contract_state is ContractState.BOUND_VERIFIED
        for ref, digest, name in ref_pairs:
            _validate_ref_pair(ref, digest, name, required=required)
        for name in ("module_preset_parameter_sha256", "before_measurement_receipt_sha256", "after_measurement_receipt_sha256"):
            _digest(getattr(self, name), name, nullable=True)
            if required and getattr(self, name) is None:
                raise ValueError("verified RX provenance is incomplete")
        values = tuple(item for pair in ref_pairs for item in pair[:2]) + (
            self.module_preset_parameter_sha256,
            self.before_measurement_receipt_sha256,
            self.after_measurement_receipt_sha256,
        )
        if self.contract_state is ContractState.CANONICAL_REF_NOT_PROVIDED and any(item is not None for item in values):
            raise ValueError("unresolved RX binding fields must be null")
        if self.source_overwritten or self.raw_delete_authorized or self.dataset_adoption_authorized:
            raise ValueError("RX metadata cannot replace/delete/adopt source audio")


@dataclass(frozen=True, slots=True)
class PrivacyPolicyBinding(_RevisionRecord):
    privacy_policy_binding_id: str
    contract_state: ContractState
    policy_ref: str | None
    policy_sha256: str | None
    public_detail_state: str
    public_detail_allowed: bool
    low_count_suppression_evidence_sha256: str | None

    record_type = "PrivacyPolicyBinding"
    hash_field = "privacy_policy_binding_sha256"
    identity_fields = ("project_id", "privacy_policy_binding_id")

    def _validate_payload(self) -> None:
        _id(self.privacy_policy_binding_id, "privacy_policy_binding_id")
        if not isinstance(self.contract_state, ContractState):
            raise ValueError("contract_state must be ContractState")
        _validate_ref_pair(self.policy_ref, self.policy_sha256, "privacy_policy", required=self.contract_state is ContractState.BOUND_VERIFIED)
        _digest(self.low_count_suppression_evidence_sha256, "low_count_suppression_evidence_sha256", nullable=True)
        if self.public_detail_state not in {"SUPPRESSED", "POLICY_AUTHORIZED", "UNKNOWN"}:
            raise ValueError("public_detail_state is invalid")
        if self.contract_state is ContractState.CANONICAL_REF_NOT_PROVIDED:
            if self.policy_ref is not None or self.policy_sha256 is not None or self.low_count_suppression_evidence_sha256 is not None:
                raise ValueError("unresolved privacy policy fields must be null")
            if self.public_detail_state != "SUPPRESSED" or self.public_detail_allowed:
                raise ValueError("unresolved privacy policy must suppress all detail")
        if self.public_detail_allowed and (
            self.contract_state is not ContractState.BOUND_VERIFIED
            or self.public_detail_state != "POLICY_AUTHORIZED"
            or self.low_count_suppression_evidence_sha256 is None
        ):
            raise ValueError("public detail requires verified privacy and low-count policy")


@dataclass(frozen=True, slots=True)
class HumanInputBinding(_RevisionRecord):
    human_input_binding_id: str
    contract_state: ContractState
    human_input_ref: str | None
    human_input_sha256: str | None
    input_state: str
    required_answers_sha256: str | None
    hardware_change_authorized: bool
    owner_voice_recording_authorized: bool

    record_type = "HumanInputBinding"
    hash_field = "human_input_binding_sha256"
    identity_fields = ("project_id", "human_input_binding_id")

    def _validate_payload(self) -> None:
        _id(self.human_input_binding_id, "human_input_binding_id")
        if not isinstance(self.contract_state, ContractState):
            raise ValueError("contract_state must be ContractState")
        _validate_ref_pair(self.human_input_ref, self.human_input_sha256, "human_input", required=self.contract_state is ContractState.BOUND_VERIFIED)
        _digest(self.required_answers_sha256, "required_answers_sha256", nullable=True)
        if self.input_state not in {"COMPLETE", "INCOMPLETE", "UNKNOWN"}:
            raise ValueError("input_state is invalid")
        if self.contract_state is ContractState.BOUND_VERIFIED and (self.input_state != "COMPLETE" or self.required_answers_sha256 is None):
            raise ValueError("verified Human input must be complete")
        if self.contract_state is ContractState.CANONICAL_REF_NOT_PROVIDED and any(
            item is not None for item in (self.human_input_ref, self.human_input_sha256, self.required_answers_sha256)
        ):
            raise ValueError("unresolved Human input fields must be null")
        if self.hardware_change_authorized or self.owner_voice_recording_authorized:
            raise ValueError("HumanInputBinding does not authorize hardware or recording effects")


@dataclass(frozen=True, slots=True)
class GainRecommendationRevision(_RevisionRecord):
    gain_recommendation_id: str
    state: RecommendationState
    capture_chain_revision_sha256: str
    measurement_receipt_sha256: str
    quality_policy_revision_sha256: str
    proposed_stage_id: str
    proposed_change_sha256: str
    human_confirmation_binding_sha256: str
    device_setting_change_authorized: bool

    record_type = "GainRecommendationRevision"
    hash_field = "gain_recommendation_revision_sha256"
    identity_fields = ("project_id", "gain_recommendation_id")

    def _validate_payload(self) -> None:
        for value, name in ((self.gain_recommendation_id, "gain_recommendation_id"), (self.proposed_stage_id, "proposed_stage_id")):
            _id(value, name)
        if not isinstance(self.state, RecommendationState):
            raise ValueError("state must be RecommendationState")
        for name in ("capture_chain_revision_sha256", "measurement_receipt_sha256", "quality_policy_revision_sha256", "proposed_change_sha256", "human_confirmation_binding_sha256"):
            _digest(getattr(self, name), name)
        if self.device_setting_change_authorized:
            raise ValueError("gain recommendation is proposal-only")


@dataclass(frozen=True, slots=True)
class AdditionalRecordingRecommendationRevision(_RevisionRecord):
    additional_recording_recommendation_id: str
    state: RecommendationState
    readiness_axis_refs: tuple[RecordReference, ...]
    reason_codes: tuple[str, ...]
    estimated_duration: RationalSampleDuration
    proposed_coverage_sha256: str
    human_confirmation_binding_sha256: str
    recording_plan_mutation_authorized: bool

    record_type = "AdditionalRecordingRecommendationRevision"
    hash_field = "additional_recording_recommendation_revision_sha256"
    identity_fields = ("project_id", "additional_recording_recommendation_id")

    def _validate_payload(self) -> None:
        _id(self.additional_recording_recommendation_id, "additional_recording_recommendation_id")
        if not isinstance(self.state, RecommendationState):
            raise ValueError("state must be RecommendationState")
        if not isinstance(self.readiness_axis_refs, tuple) or not self.readiness_axis_refs:
            raise ValueError("recommendation requires exact readiness axes")
        _validate_reason_codes(self.reason_codes)
        if not isinstance(self.estimated_duration, RationalSampleDuration):
            raise ValueError("estimated_duration must be RationalSampleDuration")
        for name in ("proposed_coverage_sha256", "human_confirmation_binding_sha256"):
            _digest(getattr(self, name), name)
        if self.recording_plan_mutation_authorized:
            raise ValueError("additional recording recommendation is proposal-only")


@dataclass(frozen=True, slots=True)
class DriftComparisonReceipt(_RevisionRecord):
    drift_comparison_receipt_id: str
    compared_at: str
    before_capture_chain_sha256: str
    after_capture_chain_sha256: str
    before_profile_sha256: str
    after_profile_sha256: str
    before_measurement_receipt_sha256: str
    after_measurement_receipt_sha256: str
    paired_metric_input_set_sha256: str
    result: QualityState
    raw_fact_mutated: bool

    record_type = "DriftComparisonReceipt"
    hash_field = "drift_comparison_receipt_sha256"
    identity_fields = ("project_id", "drift_comparison_receipt_id")

    def _validate_payload(self) -> None:
        _id(self.drift_comparison_receipt_id, "drift_comparison_receipt_id")
        _timestamp(self.compared_at, "compared_at")
        for name in ("before_capture_chain_sha256", "after_capture_chain_sha256", "before_profile_sha256", "after_profile_sha256", "before_measurement_receipt_sha256", "after_measurement_receipt_sha256", "paired_metric_input_set_sha256"):
            _digest(getattr(self, name), name)
        if not isinstance(self.result, QualityState):
            raise ValueError("result must be QualityState")
        if self.raw_fact_mutated:
            raise ValueError("before/after comparison cannot rewrite raw facts")


@dataclass(frozen=True, slots=True)
class _CoverageIndicator(_RevisionRecord):
    state: QualityState
    policy_ref: str
    policy_revision_sha256: str
    numerator_sample_count: int
    denominator_sample_count: int
    percentage_basis_points: int | None
    percentage_policy_state: ContractState

    def _validate_coverage(self) -> None:
        if not isinstance(self.state, QualityState):
            raise ValueError("coverage state must be QualityState")
        _id(self.policy_ref, "policy_ref")
        _digest(self.policy_revision_sha256, "policy_revision_sha256")
        _integer(self.numerator_sample_count, "numerator_sample_count")
        _integer(self.denominator_sample_count, "denominator_sample_count", minimum=1)
        if self.numerator_sample_count > self.denominator_sample_count:
            raise ValueError("coverage numerator cannot exceed denominator")
        if not isinstance(self.percentage_policy_state, ContractState):
            raise ValueError("percentage_policy_state must be ContractState")
        if self.percentage_policy_state is ContractState.BOUND_VERIFIED:
            if self.percentage_basis_points is None:
                raise ValueError("bound coverage policy requires percentage")
            expected = self.numerator_sample_count * 10_000 // self.denominator_sample_count
            if self.percentage_basis_points != expected or not 0 <= self.percentage_basis_points <= 10_000:
                raise ValueError("coverage percentage is not integer-rational truth")
        else:
            if self.percentage_basis_points is not None or self.state is not QualityState.UNKNOWN:
                raise ValueError("unbound percentage policy requires null/UNKNOWN")


@dataclass(frozen=True, slots=True)
class DurationCoverageIndicator(_CoverageIndicator):
    duration_coverage_indicator_id: str
    eligible_interval_index_sha256: str

    record_type = "DurationCoverageIndicator"
    hash_field = "duration_coverage_indicator_sha256"
    identity_fields = ("project_id", "duration_coverage_indicator_id")

    def _validate_payload(self) -> None:
        _id(self.duration_coverage_indicator_id, "duration_coverage_indicator_id")
        _digest(self.eligible_interval_index_sha256, "eligible_interval_index_sha256")
        self._validate_coverage()


@dataclass(frozen=True, slots=True)
class ApprovedStyleLanguageEmotionCoverageIndicator(_CoverageIndicator):
    approved_style_language_emotion_coverage_indicator_id: str
    approved_label_index_ref: str
    approved_label_index_sha256: str
    upstream_truth_recomputed: bool

    record_type = "ApprovedStyleLanguageEmotionCoverageIndicator"
    hash_field = "approved_style_language_emotion_coverage_indicator_sha256"
    identity_fields = ("project_id", "approved_style_language_emotion_coverage_indicator_id")

    def _validate_payload(self) -> None:
        _id(self.approved_style_language_emotion_coverage_indicator_id, "approved_style_language_emotion_coverage_indicator_id")
        _id(self.approved_label_index_ref, "approved_label_index_ref")
        _digest(self.approved_label_index_sha256, "approved_label_index_sha256")
        if self.upstream_truth_recomputed:
            raise ValueError("P-QC cannot recompute P-VS3A approved-label truth")
        self._validate_coverage()


@dataclass(frozen=True, slots=True)
class RawAcousticQualityCoverageIndicator(_CoverageIndicator):
    raw_acoustic_quality_coverage_indicator_id: str
    processing_class: ProcessingClass
    policy_scope: str
    current_receipt_index_sha256: str
    eligible_interval_index_sha256: str
    conflict_state: str

    record_type = "RawAcousticQualityCoverageIndicator"
    hash_field = "raw_acoustic_quality_coverage_indicator_sha256"
    identity_fields = ("project_id", "raw_acoustic_quality_coverage_indicator_id")

    def _validate_payload(self) -> None:
        _id(self.raw_acoustic_quality_coverage_indicator_id, "raw_acoustic_quality_coverage_indicator_id")
        if not isinstance(self.processing_class, ProcessingClass):
            raise ValueError("processing_class must be ProcessingClass")
        _id(self.policy_scope, "policy_scope")
        for name in ("current_receipt_index_sha256", "eligible_interval_index_sha256"):
            _digest(getattr(self, name), name)
        if self.conflict_state not in {"CLEAR", "CONFLICT", "UNKNOWN"}:
            raise ValueError("conflict_state is invalid")
        if self.state is QualityState.PASS and self.conflict_state != "CLEAR":
            raise ValueError("conflicting receipts cannot produce PASS coverage")
        self._validate_coverage()


@dataclass(frozen=True, slots=True)
class DatasetReadinessIndicator(_RevisionRecord):
    dataset_readiness_indicator_id: str
    duration_axis_ref: RecordReference
    approved_coverage_axis_ref: RecordReference
    acoustic_quality_axis_ref: RecordReference
    policy_ref: str
    policy_revision_sha256: str
    state: QualityState
    percentage_basis_points: int | None
    arithmetic_average_used: bool
    upstream_truth_recomputed: bool

    record_type = "DatasetReadinessIndicator"
    hash_field = "dataset_readiness_indicator_sha256"
    identity_fields = ("project_id", "dataset_readiness_indicator_id")

    def _validate_payload(self) -> None:
        _id(self.dataset_readiness_indicator_id, "dataset_readiness_indicator_id")
        _id(self.policy_ref, "policy_ref")
        _digest(self.policy_revision_sha256, "policy_revision_sha256")
        if not isinstance(self.state, QualityState):
            raise ValueError("state must be QualityState")
        if self.percentage_basis_points is not None:
            raise ValueError("Dataset readiness cannot invent a cross-axis percentage")
        if self.arithmetic_average_used or self.upstream_truth_recomputed:
            raise ValueError("Dataset readiness is refs-only and never averages/recomputes axes")


@dataclass(frozen=True, slots=True)
class ModelEvaluationReadinessIndicator(_RevisionRecord):
    model_evaluation_readiness_indicator_id: str
    duration_axis_ref: RecordReference
    approved_coverage_axis_ref: RecordReference
    acoustic_quality_axis_ref: RecordReference
    dataset_readiness_ref: RecordReference
    evaluation_policy_ref: str
    evaluation_policy_sha256: str
    state: QualityState
    percentage_basis_points: int | None
    arithmetic_average_used: bool
    model_effect_authorized: bool

    record_type = "ModelEvaluationReadinessIndicator"
    hash_field = "model_evaluation_readiness_indicator_sha256"
    identity_fields = ("project_id", "model_evaluation_readiness_indicator_id")

    def _validate_payload(self) -> None:
        _id(self.model_evaluation_readiness_indicator_id, "model_evaluation_readiness_indicator_id")
        _id(self.evaluation_policy_ref, "evaluation_policy_ref")
        _digest(self.evaluation_policy_sha256, "evaluation_policy_sha256")
        if not isinstance(self.state, QualityState):
            raise ValueError("state must be QualityState")
        if self.percentage_basis_points is not None:
            raise ValueError("Model readiness cannot invent a cross-axis percentage")
        if self.arithmetic_average_used or self.model_effect_authorized:
            raise ValueError("Model readiness is metadata-only and never averages/dispatches")


def _validate_measurement_source(source_class: MeasurementSourceClass, value: Mapping[str, Any]) -> None:
    if source_class is MeasurementSourceClass.CALIBRATION_STAGING_EVIDENCE:
        expected = {
            "contract_state", "capture_evidence_binding_ref", "capture_evidence_binding_sha256",
            "encrypted_staging_object_ref", "staging_object_sha256",
            "canonical_mapping_receipt_ref", "canonical_mapping_receipt_sha256",
            "retention_expires_at", "disposition", "reverification_state",
            "dataset_adoption_permitted", "asset_publication_permitted", "training_use_permitted",
        }
        _expect_keys(value, expected, "CalibrationStagingObjectBinding")
        state = _enum(ContractState, value["contract_state"], "staging contract_state")
        nullable = expected - {"contract_state", "disposition", "reverification_state", "dataset_adoption_permitted", "asset_publication_permitted", "training_use_permitted"}
        if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
            if any(value[name] is not None for name in nullable):
                raise ValueError("unresolved staging binding fields must be null")
        else:
            for name in ("capture_evidence_binding_ref", "encrypted_staging_object_ref", "canonical_mapping_receipt_ref"):
                if value[name] is not None:
                    _id(value[name], name)
            for name in ("capture_evidence_binding_sha256", "staging_object_sha256", "canonical_mapping_receipt_sha256"):
                _digest(value[name], name, nullable=True)
            if state is ContractState.BOUND_VERIFIED and any(value[name] is None for name in nullable):
                raise ValueError("verified staging binding is incomplete")
            if value["retention_expires_at"] is not None:
                _timestamp(value["retention_expires_at"], "retention_expires_at")
        if value["disposition"] not in {"ACTIVE", "EXPIRED", "DELETED", "UNKNOWN"}:
            raise ValueError("staging disposition is invalid")
        if value["reverification_state"] not in {"AVAILABLE", "UNAVAILABLE", "UNKNOWN"}:
            raise ValueError("staging reverification_state is invalid")
        if value["disposition"] in {"EXPIRED", "DELETED"} and value["reverification_state"] != "UNAVAILABLE":
            raise ValueError("expired/deleted staging cannot remain re-verifiable")
        for flag in ("dataset_adoption_permitted", "asset_publication_permitted", "training_use_permitted"):
            if value[flag] is not False:
                raise ValueError("calibration staging cannot be adopted/published/trained")
        return
    expected = {
        "contract_state", "asset_id", "asset_checksum_sha256", "asset_record_evidence_sha256",
        "asset_revision_binding_ref", "asset_revision_binding_sha256", "official_mapping_state",
    }
    _expect_keys(value, expected, "TASK003AssetBinding")
    state = _enum(ContractState, value["contract_state"], "asset contract_state")
    nullable = expected - {"contract_state", "official_mapping_state"}
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[name] is not None for name in nullable):
            raise ValueError("unresolved TASK003 Asset fields must be null")
    else:
        for name in ("asset_id", "asset_revision_binding_ref"):
            if value[name] is not None:
                _id(value[name], name)
        for name in ("asset_checksum_sha256", "asset_record_evidence_sha256", "asset_revision_binding_sha256"):
            _digest(value[name], name, nullable=True)
        if state is ContractState.BOUND_VERIFIED and (
            any(value[name] is None for name in nullable) or value["official_mapping_state"] != "BOUND"
        ):
            raise ValueError("verified TASK003 Asset requires official mapping/checksum Evidence")
    if value["official_mapping_state"] not in {"UNBOUND_PENDING_TASK003", "BOUND", "MISMATCH", "UNKNOWN"}:
        raise ValueError("official_mapping_state is invalid")


def _validate_input_roles(input_set: MetricInputSetBinding) -> None:
    refs = input_set.input_refs
    if not isinstance(refs, tuple) or not refs or not all(isinstance(ref, MetricInputReference) for ref in refs):
        raise ValueError("input_refs must be a non-empty tuple of MetricInputReference")
    roles = tuple(ref.role for ref in refs)
    if input_set.input_kind is MetricInputKind.SINGLE_RANGE:
        if len(refs) != 1 or roles[0] not in {MetricInputRole.TARGET, MetricInputRole.SIGNAL, MetricInputRole.REFERENCE}:
            raise ValueError("SINGLE_RANGE requires exactly one target/signal/reference")
        if input_set.purpose in {"SNR", "BEFORE_AFTER"}:
            raise ValueError("multi-range metric cannot be disguised as SINGLE_RANGE")
    elif input_set.input_kind is MetricInputKind.ORDERED_MULTI_RANGE:
        if input_set.purpose != "SNR" or roles != (MetricInputRole.SIGNAL, MetricInputRole.NOISE):
            raise ValueError("SNR requires ordered SIGNAL then NOISE ranges")
    elif input_set.input_kind is MetricInputKind.PAIRED_BEFORE_AFTER:
        if input_set.purpose != "BEFORE_AFTER" or roles != (MetricInputRole.BEFORE, MetricInputRole.AFTER):
            raise ValueError("paired comparison requires BEFORE then AFTER")


_RECORD_TYPES: tuple[type[_RevisionRecord], ...] = (
    CaptureChainRevision,
    CalibrationProfileRevision,
    QualityPolicyRevision,
    AnalyzerProfileRevision,
    CalibrationSessionRevision,
    MeasurementInputRangeBinding,
    StagingToTask003AssetPromotionBinding,
    MetricInputSetBinding,
    MetricFact,
    MeasurementReceipt,
    QualityEvaluationReceipt,
    CaptureEvidenceBinding,
    RXDerivedQualityBinding,
    PrivacyPolicyBinding,
    HumanInputBinding,
    GainRecommendationRevision,
    AdditionalRecordingRecommendationRevision,
    DriftComparisonReceipt,
    DurationCoverageIndicator,
    ApprovedStyleLanguageEmotionCoverageIndicator,
    RawAcousticQualityCoverageIndicator,
    DatasetReadinessIndicator,
    ModelEvaluationReadinessIndicator,
)
_RECORD_MAP = {record.record_type: record for record in _RECORD_TYPES}
_ENUM_FIELDS: dict[type[_RevisionRecord], dict[str, type[Enum]]] = {
    CaptureChainRevision: {"calibration_state": QualityState},
    CalibrationProfileRevision: {"processing_class": ProcessingClass},
    QualityPolicyRevision: {"percentage_policy_state": ContractState, "default_valid_decision": QualityState},
    AnalyzerProfileRevision: {"contract_state": ContractState},
    MeasurementInputRangeBinding: {"source_class": MeasurementSourceClass, "processing_class": ProcessingClass},
    StagingToTask003AssetPromotionBinding: {"contract_state": ContractState},
    MetricInputSetBinding: {"input_kind": MetricInputKind, "compatibility_state": QualityState},
    MetricFact: {"value_state": MetricValueState},
    MeasurementReceipt: {"fact_validity": MeasurementFactValidity},
    QualityEvaluationReceipt: {"result": QualityState},
    CaptureEvidenceBinding: {"contract_state": ContractState, "evidence_state": QualityState},
    RXDerivedQualityBinding: {"contract_state": ContractState},
    PrivacyPolicyBinding: {"contract_state": ContractState},
    HumanInputBinding: {"contract_state": ContractState},
    GainRecommendationRevision: {"state": RecommendationState},
    AdditionalRecordingRecommendationRevision: {"state": RecommendationState},
    DriftComparisonReceipt: {"result": QualityState},
    DurationCoverageIndicator: {"state": QualityState, "percentage_policy_state": ContractState},
    ApprovedStyleLanguageEmotionCoverageIndicator: {"state": QualityState, "percentage_policy_state": ContractState},
    RawAcousticQualityCoverageIndicator: {"state": QualityState, "percentage_policy_state": ContractState, "processing_class": ProcessingClass},
    DatasetReadinessIndicator: {"state": QualityState},
    ModelEvaluationReadinessIndicator: {"state": QualityState},
}


def _parse_nested(record_type: type[_RevisionRecord], kwargs: dict[str, Any]) -> None:
    if record_type is CaptureChainRevision:
        kwargs["stages"] = tuple(
            CaptureChainStage(**{**row, "stage_kind": CaptureChainStageKind(row["stage_kind"])})
            for row in kwargs["stages"]
        )
    if record_type is AnalyzerProfileRevision:
        kwargs["supported_metrics"] = tuple(kwargs["supported_metrics"])
    if record_type is MeasurementInputRangeBinding:
        kwargs["interval"] = HalfOpenSampleInterval(**kwargs["interval"])
    if record_type is MetricInputSetBinding:
        kwargs["input_refs"] = tuple(
            MetricInputReference(**{**row, "role": MetricInputRole(row["role"])})
            for row in kwargs["input_refs"]
        )
    if record_type in {MeasurementReceipt, QualityEvaluationReceipt}:
        key = "metric_fact_refs" if record_type is MeasurementReceipt else "measurement_receipt_refs"
        kwargs[key] = tuple(RecordReference(**row) for row in kwargs[key])
    if record_type is QualityEvaluationReceipt:
        kwargs["reason_codes"] = tuple(kwargs["reason_codes"])
    if record_type is AdditionalRecordingRecommendationRevision:
        kwargs["readiness_axis_refs"] = tuple(RecordReference(**row) for row in kwargs["readiness_axis_refs"])
        kwargs["reason_codes"] = tuple(kwargs["reason_codes"])
        kwargs["estimated_duration"] = RationalSampleDuration(**kwargs["estimated_duration"])
    if record_type in {DatasetReadinessIndicator, ModelEvaluationReadinessIndicator}:
        for key in ("duration_axis_ref", "approved_coverage_axis_ref", "acoustic_quality_axis_ref", "dataset_readiness_ref"):
            if key in kwargs:
                kwargs[key] = RecordReference(**kwargs[key])


def parse_voice_quality_record(document: Mapping[str, Any]) -> _RevisionRecord:
    if not isinstance(document, Mapping) or document.get("record_type") not in _RECORD_MAP:
        raise ValueError("unknown voice-quality record_type")
    record_type = _RECORD_MAP[document["record_type"]]
    expected = {field.name for field in fields(record_type)}
    envelope = {"voice_quality_contract_version", "record_type", "task_owner", record_type.hash_field}
    _expect_keys(document, expected | envelope, record_type.record_type)
    if document["voice_quality_contract_version"] != VOICE_QUALITY_CALIBRATION_VERSION or document["task_owner"] != TASK_OWNER:
        raise ValueError("unsupported voice-quality contract identity")
    body = {key: value for key, value in document.items() if key != record_type.hash_field}
    if document[record_type.hash_field] != canonical_sha256(body):
        raise ValueError(f"{record_type.record_type} checksum mismatch")
    kwargs = {key: document[key] for key in expected}
    for field_name, enum_type in _ENUM_FIELDS.get(record_type, {}).items():
        kwargs[field_name] = enum_type(kwargs[field_name])
    _parse_nested(record_type, kwargs)
    return record_type(**kwargs)


def validate_append_only_revision(previous: _RevisionRecord, current: _RevisionRecord) -> None:
    if type(previous) is not type(current):
        raise ValueError("append-only revision type mismatch")
    if any(getattr(previous, name) != getattr(current, name) for name in previous.identity_fields):
        raise ValueError("append-only identity mismatch")
    if current.revision != previous.revision + 1 or current.parent_revision_sha256 != previous.sha256:
        raise ValueError("append-only revision lineage mismatch")


def validate_revision_cas(
    previous: _RevisionRecord,
    current: _RevisionRecord,
    expected_parent_sha256: str,
) -> None:
    _digest(expected_parent_sha256, "expected_parent_sha256")
    if expected_parent_sha256 != previous.sha256:
        raise ValueError("stale revision CAS expectation")
    validate_append_only_revision(previous, current)


def validate_capture_chain(revision: CaptureChainRevision) -> None:
    if not isinstance(revision.stages, tuple) or len(revision.stages) != 8:
        raise ValueError("capture chain requires exact ordered eight stages")
    kinds = tuple(stage.stage_kind for stage in revision.stages)
    if kinds != _EXPECTED_STAGE_ORDER:
        raise ValueError("capture chain stage order is invalid")
    primary_gain_count = 0
    for index, stage in enumerate(revision.stages):
        if stage.stage_index != index + 1:
            raise ValueError("capture chain stage index is discontinuous")
        expected_previous = None if index == 0 else revision.stages[index - 1].stage_sha256
        expected_next = None if index == 7 else revision.stages[index + 1].stage_sha256
        if stage.previous_stage_sha256 != expected_previous or stage.next_stage_sha256 != expected_next:
            raise ValueError("capture chain prev/next lineage gap")
        if stage.gain_role == "PRIMARY":
            primary_gain_count += 1
    if primary_gain_count > 1:
        raise ValueError("capture chain contains duplicate primary gain stages")
    if revision.calibration_state is QualityState.PASS and any(
        stage.processing_state == "UNKNOWN"
        or stage.hidden_processing_state != "CLEAR"
        or stage.gain_role == "UNKNOWN"
        or (
            stage.stage_kind is CaptureChainStageKind.MIC_PAD_HPF
            and "UNKNOWN" in {
                stage.phantom_power_observation_state,
                stage.pad_observation_state,
                stage.hpf_observation_state,
            }
        )
        or (
            stage.stage_kind is CaptureChainStageKind.INTERFACE_ANALOGUE_PREAMP
            and stage.preamp_gain_observation_state == "UNKNOWN"
        )
        for stage in revision.stages
    ):
        raise ValueError("unknown/hidden processing cannot produce raw calibration PASS")


def validate_metric_input_set(
    input_set: MetricInputSetBinding,
    ranges: Mapping[str, MeasurementInputRangeBinding],
    chains: Mapping[str, CaptureChainRevision],
    profiles: Mapping[str, CalibrationProfileRevision],
    policy: QualityPolicyRevision,
) -> None:
    _validate_input_roles(input_set)
    resolved: list[MeasurementInputRangeBinding] = []
    for ref in input_set.input_refs:
        candidate = ranges.get(ref.range_ref)
        if candidate is None or candidate.sha256 != ref.range_sha256:
            raise ValueError("MetricInputSet range ref/hash mismatch")
        resolved.append(candidate)
    if any(item.project_id != input_set.project_id for item in resolved):
        raise ValueError("MetricInputSet range project mismatch")
    if policy.sha256 != input_set.quality_policy_revision_sha256:
        raise ValueError("MetricInputSet policy mismatch")
    if input_set.calibration_profile_revision_sha256 not in {profile.sha256 for profile in profiles.values()}:
        raise ValueError("MetricInputSet calibration profile mismatch")
    if any(item.capture_chain_revision_sha256 not in {chain.sha256 for chain in chains.values()} for item in resolved):
        raise ValueError("MetricInputSet capture chain is not provided")
    first = resolved[0]
    for item in resolved[1:]:
        if (item.sample_rate, item.bit_depth, item.channels) != (first.sample_rate, first.bit_depth, first.channels):
            raise ValueError("MetricInputSet sample formats are incompatible")
        if item.capture_chain_revision_sha256 != first.capture_chain_revision_sha256:
            raise ValueError("MetricInputSet capture chains are incompatible")
    if input_set.input_kind is MetricInputKind.PAIRED_BEFORE_AFTER:
        if resolved[0].processing_class is ProcessingClass.RAW_PRE_FILTER and resolved[1].processing_class is ProcessingClass.RX_DERIVED:
            raise ValueError("raw and RX-derived ranges cannot be presented as one raw fact")
    if input_set.input_kind is MetricInputKind.ORDERED_MULTI_RANGE:
        left, right = resolved
        if (
            left.canonical_mapping_sha256 == right.canonical_mapping_sha256
            and left.interval.start_sample < right.interval.end_sample
            and right.interval.start_sample < left.interval.end_sample
        ):
            raise ValueError("policy does not admit overlapping SIGNAL/NOISE ranges")


def validate_measurement_receipt(
    receipt: MeasurementReceipt,
    input_set: MetricInputSetBinding,
    analyzer_profile: AnalyzerProfileRevision,
) -> None:
    if receipt.metric_input_set_ref != input_set.metric_input_set_id or receipt.metric_input_set_sha256 != input_set.sha256:
        raise ValueError("MeasurementReceipt input-set mismatch")
    if receipt.analyzer_profile_ref != analyzer_profile.analyzer_profile_id or receipt.analyzer_profile_revision_sha256 != analyzer_profile.sha256:
        raise ValueError("MeasurementReceipt analyzer mismatch")
    if analyzer_profile.contract_state is not ContractState.BOUND_VERIFIED and receipt.fact_validity is MeasurementFactValidity.VALID:
        raise ValueError("unbound analyzer cannot issue VALID facts")
    if receipt.calibration_profile_revision_sha256 != input_set.calibration_profile_revision_sha256:
        raise ValueError("MeasurementReceipt calibration profile mismatch")


def classify_quality_evaluation(
    receipts: Sequence[MeasurementReceipt],
    policy: QualityPolicyRevision,
) -> QualityClassification:
    if not receipts:
        return QualityClassification(QualityState.UNKNOWN, ("NO_MEASUREMENT_RECEIPTS",))
    if any(receipt.tampered or not receipt.current for receipt in receipts):
        return QualityClassification(QualityState.UNKNOWN, ("STALE_OR_TAMPERED_RECEIPT",))
    if any(receipt.fact_validity is MeasurementFactValidity.UNKNOWN for receipt in receipts):
        return QualityClassification(QualityState.UNKNOWN, ("MEASUREMENT_FACT_UNKNOWN",))
    if any(receipt.fact_validity is MeasurementFactValidity.INVALID_INPUT for receipt in receipts):
        return QualityClassification(QualityState.FAIL, ("INVALID_MEASUREMENT_INPUT",))
    if policy.precedence_rule == "UNKNOWN" or policy.conflict_rule == "UNKNOWN":
        return QualityClassification(QualityState.UNKNOWN, ("POLICY_PRECEDENCE_OR_CONFLICT_UNKNOWN",))
    return QualityClassification(policy.default_valid_decision, ("POLICY_CLASSIFICATION",))


def _merge_intervals(intervals: Iterable[HalfOpenSampleInterval]) -> tuple[HalfOpenSampleInterval, ...]:
    ordered = sorted(intervals)
    merged: list[HalfOpenSampleInterval] = []
    for interval in ordered:
        if not merged or interval.start_sample > merged[-1].end_sample:
            merged.append(interval)
        else:
            merged[-1] = HalfOpenSampleInterval(
                merged[-1].start_sample,
                max(merged[-1].end_sample, interval.end_sample),
            )
    return tuple(merged)


def union_eligible_intervals(
    receipts: Sequence[QualityEvaluationReceipt],
    eligibility_index: Sequence[CoverageIntervalEntry],
    policy: QualityPolicyRevision,
) -> IntervalUnionResult:
    valid_receipts = {receipt.sha256 for receipt in receipts if receipt.result is QualityState.PASS}
    groups: dict[str, list[HalfOpenSampleInterval]] = {}
    states: dict[tuple[str, int, int], set[QualityState]] = {}
    for entry in eligibility_index:
        if entry.policy_revision_sha256 != policy.sha256 or not entry.current or entry.tampered:
            continue
        index_key = f"{entry.source_identity_sha256}|{entry.processing_class.value}|{entry.policy_scope}"
        conflict_key = (index_key, entry.interval.start_sample, entry.interval.end_sample)
        states.setdefault(conflict_key, set()).add(entry.receipt_state)
        if entry.receipt_state is QualityState.PASS and entry.receipt_sha256 in valid_receipts:
            groups.setdefault(index_key, []).append(entry.interval)
    if any(len(values) > 1 for values in states.values()) and policy.conflict_rule == "UNKNOWN":
        return IntervalUnionResult(QualityState.UNKNOWN, {}, ("PASS_FAIL_CONFLICT_POLICY_UNKNOWN",))
    merged = {key: _merge_intervals(value) for key, value in groups.items()}
    return IntervalUnionResult(QualityState.PASS, merged, ("UNION_DEDUPED",))


def calculate_coverage_indicator(
    numerator_intervals: Sequence[HalfOpenSampleInterval],
    denominator_index: Sequence[HalfOpenSampleInterval],
    processing_class: ProcessingClass,
    policy_scope: str,
) -> CoverageCalculation:
    numerator = _merge_intervals(numerator_intervals)
    denominator = _merge_intervals(denominator_index)
    denominator_count = sum(item.sample_count for item in denominator)
    if denominator_count <= 0:
        raise ValueError("coverage denominator cannot be empty")
    for item in numerator:
        if not any(item.start_sample >= base.start_sample and item.end_sample <= base.end_sample for base in denominator):
            raise ValueError("coverage numerator is outside the eligible denominator")
    numerator_count = sum(item.sample_count for item in numerator)
    return CoverageCalculation(
        numerator_sample_count=numerator_count,
        denominator_sample_count=denominator_count,
        percentage_basis_points=numerator_count * 10_000 // denominator_count,
        processing_class=processing_class,
        policy_scope=_id(policy_scope, "policy_scope"),
    )


def validate_readiness_axes(typed_axes: Sequence[_RevisionRecord]) -> None:
    expected = {
        DurationCoverageIndicator,
        ApprovedStyleLanguageEmotionCoverageIndicator,
        RawAcousticQualityCoverageIndicator,
        DatasetReadinessIndicator,
        ModelEvaluationReadinessIndicator,
    }
    actual = {type(axis) for axis in typed_axes}
    if len(typed_axes) != 5 or actual != expected:
        raise ValueError("five independent readiness axes are required exactly once")
    for axis in typed_axes:
        if isinstance(axis, (DatasetReadinessIndicator, ModelEvaluationReadinessIndicator)) and axis.arithmetic_average_used:
            raise ValueError("readiness axes cannot be arithmetically averaged")


def _pvs3a_projection(state: ContractState, *, result: str | None = None, analyzer: AnalyzerProfileRevision | None = None, policy: QualityPolicyRevision | None = None, chain: CaptureChainRevision | None = None, evaluation: QualityEvaluationReceipt | None = None, measured_at: str | None = None) -> dict[str, Any]:
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        return {
            "contract_state": state.value,
            "analyzer_profile_ref": None,
            "analyzer_profile_sha256": None,
            "calibration_receipt_ref": None,
            "calibration_receipt_sha256": None,
            "result": None,
            "threshold_profile_revision": None,
            "capture_chain_sha256": None,
            "measured_at": None,
        }
    return {
        "contract_state": state.value,
        "analyzer_profile_ref": analyzer.analyzer_profile_id if analyzer else None,
        "analyzer_profile_sha256": analyzer.sha256 if analyzer else None,
        "calibration_receipt_ref": evaluation.quality_evaluation_receipt_id if evaluation else None,
        "calibration_receipt_sha256": evaluation.sha256 if evaluation else None,
        "result": result or "UNKNOWN",
        "threshold_profile_revision": policy.quality_policy_id if policy else None,
        "capture_chain_sha256": chain.sha256 if chain else None,
        "measured_at": measured_at,
    }


def project_pvs3a_calibration_binding(
    evaluation: QualityEvaluationReceipt | None,
    analyzer: AnalyzerProfileRevision | None,
    policy: QualityPolicyRevision | None,
    chain: CaptureChainRevision | None,
    measurements: Sequence[MeasurementReceipt] = (),
) -> dict[str, Any]:
    if evaluation is None or analyzer is None or policy is None or chain is None:
        return _pvs3a_projection(ContractState.CANONICAL_REF_NOT_PROVIDED)
    exact = (
        evaluation.analyzer_profile_ref == analyzer.analyzer_profile_id
        and evaluation.analyzer_profile_revision_sha256 == analyzer.sha256
        and evaluation.quality_policy_ref == policy.quality_policy_id
        and evaluation.quality_policy_revision_sha256 == policy.sha256
        and evaluation.capture_chain_revision_sha256 == chain.sha256
    )
    if not exact:
        return _pvs3a_projection(ContractState.MISMATCH, analyzer=analyzer, policy=policy, chain=chain, evaluation=evaluation)
    expected_receipts = {ref.record_sha256 for ref in evaluation.measurement_receipt_refs}
    provided_receipts = {receipt.sha256 for receipt in measurements}
    if not measurements or expected_receipts != provided_receipts:
        return _pvs3a_projection(ContractState.UNKNOWN, analyzer=analyzer, policy=policy, chain=chain, evaluation=evaluation)
    if any(receipt.fact_validity is not MeasurementFactValidity.VALID or receipt.tampered or not receipt.current for receipt in measurements):
        return _pvs3a_projection(ContractState.UNKNOWN, analyzer=analyzer, policy=policy, chain=chain, evaluation=evaluation)
    measured_at = max(receipt.measured_at for receipt in measurements)
    result = {
        QualityState.PASS: "PASS",
        QualityState.FAIL: "FAIL",
        QualityState.RERECORD_RECOMMENDED: "FAIL",
        QualityState.UNKNOWN: "UNKNOWN",
    }[evaluation.result]
    return _pvs3a_projection(
        ContractState.BOUND_VERIFIED,
        result=result,
        analyzer=analyzer,
        policy=policy,
        chain=chain,
        evaluation=evaluation,
        measured_at=measured_at,
    )


def to_private_dict(record: _RevisionRecord) -> dict[str, Any]:
    if not isinstance(record, _RevisionRecord):
        raise ValueError("record must be a canonical voice-quality record")
    return record.to_private_dict()


def to_public_dict(record: _RevisionRecord, privacy_policy_binding: PrivacyPolicyBinding) -> dict[str, Any]:
    if not isinstance(record, _RevisionRecord) or not isinstance(privacy_policy_binding, PrivacyPolicyBinding):
        raise ValueError("record and PrivacyPolicyBinding are required")
    private = record.to_private_dict()
    detail_allowed = (
        privacy_policy_binding.contract_state is ContractState.BOUND_VERIFIED
        and privacy_policy_binding.public_detail_allowed
        and privacy_policy_binding.public_detail_state == "POLICY_AUTHORIZED"
    )

    def redact(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                key: redact(item)
                for key, item in value.items()
                if key not in _PRIVATE_KEYS and (detail_allowed or key not in _SUPPRESSED_DETAIL_KEYS)
            }
        if isinstance(value, list):
            return [redact(item) for item in value]
        return value

    projection = redact(private)
    projection["projection"] = "PUBLIC_REDACTED"
    projection["privacy_policy_contract_state"] = privacy_policy_binding.contract_state.value
    projection["public_detail_allowed"] = detail_allowed
    projection["public_projection_sha256"] = canonical_sha256(projection)
    return projection


def clone_with_new_revision(record: _RevisionRecord, **changes: Any) -> _RevisionRecord:
    return replace(record, revision=record.revision + 1, parent_revision_sha256=record.sha256, **changes)


BODY_AUTHORITY_FLAGS = dict(_BODY_FLAGS)
CANONICAL_SERIALIZED_TYPES = tuple(record.record_type for record in _RECORD_TYPES)
