"""TASK-048 P-QC-P0V-FINISH-1 fixture-only audio finishing contract.

This module deliberately does not open audio files, spawn FFmpeg, publish a
WAV, scan a recording directory, or adopt a Dataset item.  It provides a
closed, body-free contract and a deterministic fake runner so the Product
owners can integrate a native executor and a private sink later without
turning test evidence into Production authority.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import math
import re
import threading
from typing import Any, Protocol

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


CONTRACT_VERSION = "1.0.0"
TASK_OWNER = "TASK-048/P-QC-P0V-FINISH-1"
TECHNICAL_QA_RECEIPT_TYPE = "FIXTURE_OWNER_VOICE_TECHNICAL_QA_RECEIPT_V1"
TRAINING_COPY_RECEIPT_TYPE = "VOICE_TRAINING_COPY_QA_RECEIPT_V1"
ENVIRONMENT_AB_RECEIPT_TYPE = "FIXTURE_VOICE_ENVIRONMENT_AB_QA_RECEIPT_V1"
SPEECH_CONTINUOUS_RECEIPT_TYPE = "FIXTURE_SPEECH_CONTINUOUS_TRAINING_WAV_RECEIPT_V1"
TASK047_TERMINAL_RECEIPT_TYPE = "TASK047_FINALIZED_RECORDING_READBACK_V1"
SAMPLE_RATE_HZ = 48_000
CHANNELS = 1
SAMPLE_FORMAT = "PCM_S24LE"
PCM_BYTES_PER_SAMPLE = 3
CONFIRMED_NON_SPEECH_CONFIDENCE = 0.95
BOUNDARY_CROSSFADE_SAMPLES = 240
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}")
_OPAQUE_REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}")


class OperationKind(str, Enum):
    GENERATED_WAV_FINISH = "GENERATED_WAV_FINISH"
    TRAINING_COPY_QA = "TRAINING_COPY_QA"
    ENVIRONMENT_AB_QA = "ENVIRONMENT_AB_QA"
    SPEECH_CONTINUOUS_TRAINING_FINISH = "SPEECH_CONTINUOUS_TRAINING_FINISH"


class QAState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class ClassificationState(str, Enum):
    PASS = "PASS"
    DETECTED = "DETECTED"
    UNKNOWN = "UNKNOWN"


class CaptureCondition(str, Enum):
    AIR_CONDITIONER_OFF = "AIR_CONDITIONER_OFF"
    AIR_CONDITIONER_ON = "AIR_CONDITIONER_ON"


class VoiceEffort(str, Enum):
    WHISPER = "WHISPER"
    NORMAL = "NORMAL"
    SHOUT = "SHOUT"


class SegmentEligibility(str, Enum):
    TRAINING_ELIGIBLE = "TRAINING_ELIGIBLE"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


class IntervalClass(str, Enum):
    SPEECH = "SPEECH"
    NON_SPEECH = "NON_SPEECH"
    UNCERTAIN = "UNCERTAIN"


class ChannelStrategy(str, Enum):
    MONO_PRESERVE = "MONO_PRESERVE"
    SELECT_CHANNEL = "SELECT_CHANNEL"
    PHASE_SAFE_DOWNMIX = "PHASE_SAFE_DOWNMIX"


class BoundaryMode(str, Enum):
    EQUAL_POWER_CROSSFADE = "EQUAL_POWER_CROSSFADE"


class ReasonCode(str, Enum):
    SOURCE_RECEIPT_MISSING = "SOURCE_RECEIPT_MISSING"
    SOURCE_STILL_WRITING = "SOURCE_STILL_WRITING"
    SOURCE_CURRENTNESS_UNKNOWN = "SOURCE_CURRENTNESS_UNKNOWN"
    SOURCE_IDENTITY_CHANGED = "SOURCE_IDENTITY_CHANGED"
    SOURCE_LINK_REJECTED = "SOURCE_LINK_REJECTED"
    WAV_INVALID_OR_INCOMPLETE = "WAV_INVALID_OR_INCOMPLETE"
    SOURCE_EMPTY_OR_OVERSIZE = "SOURCE_EMPTY_OR_OVERSIZE"
    CANONICAL_INPUT_UNBOUND = "CANONICAL_INPUT_UNBOUND"
    CLIPPING_DETECTED = "CLIPPING_DETECTED"
    CLIPPING_UNKNOWN = "CLIPPING_UNKNOWN"
    LOUDNESS_OUT_OF_POLICY = "LOUDNESS_OUT_OF_POLICY"
    LOUDNESS_UNKNOWN = "LOUDNESS_UNKNOWN"
    TRUE_PEAK_OUT_OF_POLICY = "TRUE_PEAK_OUT_OF_POLICY"
    TRUE_PEAK_UNKNOWN = "TRUE_PEAK_UNKNOWN"
    LOUDNESS_RANGE_OUT_OF_POLICY = "LOUDNESS_RANGE_OUT_OF_POLICY"
    LOUDNESS_RANGE_UNKNOWN = "LOUDNESS_RANGE_UNKNOWN"
    SNR_BELOW_POLICY = "SNR_BELOW_POLICY"
    SNR_UNKNOWN = "SNR_UNKNOWN"
    SILENCE_EXCESSIVE = "SILENCE_EXCESSIVE"
    SILENCE_UNKNOWN = "SILENCE_UNKNOWN"
    SPEECH_TOO_SHORT = "SPEECH_TOO_SHORT"
    SPEECH_DURATION_UNKNOWN = "SPEECH_DURATION_UNKNOWN"
    SPEECH_DURATION_OUT_OF_RANGE = "SPEECH_DURATION_OUT_OF_RANGE"
    SPEECH_RATIO_OUT_OF_POLICY = "SPEECH_RATIO_OUT_OF_POLICY"
    SPEECH_RATIO_UNKNOWN = "SPEECH_RATIO_UNKNOWN"
    DROPOUT_DETECTED = "DROPOUT_DETECTED"
    DROPOUT_UNKNOWN = "DROPOUT_UNKNOWN"
    DC_OFFSET_OUT_OF_POLICY = "DC_OFFSET_OUT_OF_POLICY"
    DC_OFFSET_UNKNOWN = "DC_OFFSET_UNKNOWN"
    OTHER_SPEAKER_DETECTED = "OTHER_SPEAKER_DETECTED"
    OTHER_SPEAKER_UNVERIFIED = "OTHER_SPEAKER_UNVERIFIED"
    BGM_EXCESSIVE = "BGM_EXCESSIVE"
    BGM_CLASSIFICATION_UNKNOWN = "BGM_CLASSIFICATION_UNKNOWN"
    CONSENT_OR_REVIEW_NOT_CURRENT = "CONSENT_OR_REVIEW_NOT_CURRENT"
    TRAINING_FORMAT_UNBOUND = "TRAINING_FORMAT_UNBOUND"
    TRAINING_FORMAT_MISMATCH = "TRAINING_FORMAT_MISMATCH"
    COPY_CONVERSION_FAILED = "COPY_CONVERSION_FAILED"
    COPY_READBACK_MISMATCH = "COPY_READBACK_MISMATCH"
    GENERATED_FINISH_FAILED = "GENERATED_FINISH_FAILED"
    GENERATED_READBACK_MISMATCH = "GENERATED_READBACK_MISMATCH"
    AB_CHAIN_MISMATCH = "AB_CHAIN_MISMATCH"
    AB_CAPTURE_NOT_CURRENT = "AB_CAPTURE_NOT_CURRENT"
    AB_MEASUREMENT_SET_INVALID = "AB_MEASUREMENT_SET_INVALID"
    AB_MEASUREMENT_NOT_CURRENT = "AB_MEASUREMENT_NOT_CURRENT"
    NONFINITE_SAMPLES = "NONFINITE_SAMPLES"
    NOISE_FLOOR_UNKNOWN = "NOISE_FLOOR_UNKNOWN"
    SPEECH_LEVEL_UNKNOWN = "SPEECH_LEVEL_UNKNOWN"
    NOISE_PROFILE_UNKNOWN = "NOISE_PROFILE_UNKNOWN"
    DENOISE_INPUT_MISMATCH = "DENOISE_INPUT_MISMATCH"
    DENOISE_IMPROVEMENT_INSUFFICIENT = "DENOISE_IMPROVEMENT_INSUFFICIENT"
    DENOISE_DISTORTION_RISK = "DENOISE_DISTORTION_RISK"
    DENOISE_RISK_UNKNOWN = "DENOISE_RISK_UNKNOWN"
    STRICT_WAV_INVALID = "STRICT_WAV_INVALID"
    SPEECH_REQUIRED = "SPEECH_REQUIRED"
    VAD_COVERAGE_INVALID = "VAD_COVERAGE_INVALID"
    SPEECH_BOUNDARY_UNVERIFIED = "SPEECH_BOUNDARY_UNVERIFIED"
    SPEECH_ATTACK_OR_TAIL_DAMAGED = "SPEECH_ATTACK_OR_TAIL_DAMAGED"
    LOSSY_TRAINING_FORMAT = "LOSSY_TRAINING_FORMAT"
    PHASE_CANCELLATION_RISK = "PHASE_CANCELLATION_RISK"
    AB_SEGMENT_REJECTED = "AB_SEGMENT_REJECTED"
    AB_REVIEW_REQUIRED = "AB_REVIEW_REQUIRED"


class FinishingContractError(ValueError):
    """Stable, body-free contract rejection."""

    code = "REJECTED_AUDIO_FINISHING_CONTRACT"


class OperationAlreadyConsumedError(FinishingContractError):
    code = "REJECTED_OPERATION_ALREADY_CONSUMED"


def _id(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or not _ID_RE.fullmatch(value)
        or "://" in value
        or re.match(r"^[A-Za-z]:/", value)
        or value.startswith(("/", "./", "../"))
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise FinishingContractError(f"{name} is invalid")
    return value


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise FinishingContractError(f"{name} is invalid")
    try:
        return validate_sha256(value, field_name=name)
    except ValueError:
        raise FinishingContractError(f"{name} is invalid") from None


def _positive_int(value: Any, name: str, *, maximum: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise FinishingContractError(f"{name} must be a positive integer")
    if maximum is not None and value > maximum:
        raise FinishingContractError(f"{name} exceeds the contract ceiling")
    return value


def _finite(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise FinishingContractError(f"{name} must be finite")
    return float(value)


def _enum(enum_type: type[Enum], value: Any, name: str) -> Enum:
    try:
        return value if isinstance(value, enum_type) else enum_type(value)
    except (TypeError, ValueError):
        raise FinishingContractError(f"{name} is invalid") from None


def _opaque_ref(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _OPAQUE_REF_RE.fullmatch(value):
        raise FinishingContractError(f"{name} is invalid")
    return value


def _receipt_hash(body: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(body))


@dataclass(frozen=True, slots=True)
class AudioFormat:
    sample_rate_hz: int = SAMPLE_RATE_HZ
    channels: int = CHANNELS
    sample_format: str = SAMPLE_FORMAT

    def __post_init__(self) -> None:
        if (
            type(self.sample_rate_hz) is not int
            or type(self.channels) is not int
            or type(self.sample_format) is not str
            or (self.sample_rate_hz, self.channels, self.sample_format) != (
            SAMPLE_RATE_HZ,
            CHANNELS,
            SAMPLE_FORMAT,
            )
        ):
            raise FinishingContractError("audio format must be PCM_S24LE/48000/mono")

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_rate_hz": self.sample_rate_hz,
            "channels": self.channels,
            "sample_format": self.sample_format,
        }


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    source_ref: str
    source_sha256: str
    source_identity_sha256: str
    terminal_receipt_sha256: str | None
    terminal_receipt_owner: str | None
    terminal_receipt_type: str | None
    terminal_receipt_current: bool
    source_size_bytes: int
    sample_count: int
    source_format: AudioFormat | None
    regular_file: bool
    single_link: bool
    no_reparse: bool
    ancestor_current: bool
    identity_current: bool
    read_current: bool
    write_closed_verified: bool
    wav_complete: bool

    def __post_init__(self) -> None:
        _opaque_ref(self.source_ref, "source_ref")
        _digest(self.source_sha256, "source_sha256")
        _digest(self.source_identity_sha256, "source_identity_sha256")
        if self.terminal_receipt_sha256 is not None:
            _digest(self.terminal_receipt_sha256, "terminal_receipt_sha256")
        if self.terminal_receipt_owner is not None:
            _id(self.terminal_receipt_owner, "terminal_receipt_owner")
        if self.terminal_receipt_type is not None:
            _id(self.terminal_receipt_type, "terminal_receipt_type")
        _positive_int(self.source_size_bytes, "source_size_bytes", maximum=4 * 1024**3)
        _positive_int(self.sample_count, "sample_count", maximum=12 * 60 * 60 * SAMPLE_RATE_HZ)
        if self.source_format is not None and type(self.source_format) is not AudioFormat:
            raise FinishingContractError("source_format must be an AudioFormat")
        for name in (
            "regular_file", "single_link", "no_reparse", "ancestor_current",
            "terminal_receipt_current", "identity_current", "read_current",
            "write_closed_verified", "wav_complete",
        ):
            if type(getattr(self, name)) is not bool:
                raise FinishingContractError(f"{name} must be boolean")

    @property
    def secure_and_current(self) -> bool:
        return all((
            self.regular_file,
            self.single_link,
            self.no_reparse,
            self.ancestor_current,
            self.identity_current,
            self.read_current,
            self.write_closed_verified,
            self.wav_complete,
        ))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_ref": self.source_ref,
            "source_sha256": self.source_sha256,
            "source_identity_sha256": self.source_identity_sha256,
            "terminal_receipt_sha256": self.terminal_receipt_sha256,
            "terminal_receipt_owner": self.terminal_receipt_owner,
            "terminal_receipt_type": self.terminal_receipt_type,
            "terminal_receipt_current": self.terminal_receipt_current,
            "source_size_bytes": self.source_size_bytes,
            "sample_count": self.sample_count,
            "source_format": None if self.source_format is None else self.source_format.to_dict(),
            "regular_file": self.regular_file,
            "single_link": self.single_link,
            "no_reparse": self.no_reparse,
            "ancestor_current": self.ancestor_current,
            "identity_current": self.identity_current,
            "read_current": self.read_current,
            "write_closed_verified": self.write_closed_verified,
            "wav_complete": self.wav_complete,
        }


@dataclass(frozen=True, slots=True)
class QualityMeasurements:
    integrated_lufs: float | None
    true_peak_dbtp: float | None
    loudness_range_lu: float | None
    clipped_sample_count: int | None
    snr_db: float | None
    silence_ratio: float | None
    speech_duration_seconds: float | None
    speech_ratio: float | None
    dropout_count: int | None
    dc_offset_abs: float | None
    other_speaker_state: ClassificationState
    bgm_state: ClassificationState

    def __post_init__(self) -> None:
        for name in ("integrated_lufs", "true_peak_dbtp", "loudness_range_lu", "snr_db"):
            value = getattr(self, name)
            if value is not None:
                _finite(value, name)
        if self.clipped_sample_count is not None:
            if not isinstance(self.clipped_sample_count, int) or isinstance(self.clipped_sample_count, bool) or self.clipped_sample_count < 0:
                raise FinishingContractError("clipped_sample_count must be a non-negative integer")
        for name in ("silence_ratio", "speech_duration_seconds", "speech_ratio", "dc_offset_abs"):
            value = getattr(self, name)
            if value is not None:
                value = _finite(value, name)
                if value < 0 or (name in {"silence_ratio", "speech_ratio"} and value > 1):
                    raise FinishingContractError(f"{name} is out of range")
        if self.dropout_count is not None:
            if not isinstance(self.dropout_count, int) or isinstance(self.dropout_count, bool) or self.dropout_count < 0:
                raise FinishingContractError("dropout_count must be a non-negative integer")
        object.__setattr__(self, "other_speaker_state", _enum(ClassificationState, self.other_speaker_state, "other_speaker_state"))
        object.__setattr__(self, "bgm_state", _enum(ClassificationState, self.bgm_state, "bgm_state"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "integrated_lufs": self.integrated_lufs,
            "true_peak_dbtp": self.true_peak_dbtp,
            "loudness_range_lu": self.loudness_range_lu,
            "clipped_sample_count": self.clipped_sample_count,
            "snr_db": self.snr_db,
            "silence_ratio": self.silence_ratio,
            "speech_duration_seconds": self.speech_duration_seconds,
            "speech_ratio": self.speech_ratio,
            "dropout_count": self.dropout_count,
            "dc_offset_abs": self.dc_offset_abs,
            "other_speaker_state": self.other_speaker_state.value,
            "bgm_state": self.bgm_state.value,
        }


def _generated_measurements_pass(value: QualityMeasurements) -> bool:
    return all((
        value.integrated_lufs is not None and abs(value.integrated_lufs - (-16.0)) <= 1.0,
        value.true_peak_dbtp is not None and value.true_peak_dbtp <= -1.0,
        value.loudness_range_lu is not None and 0.0 <= value.loudness_range_lu <= 11.0,
        value.clipped_sample_count == 0,
        value.silence_ratio is not None and value.silence_ratio <= 0.35,
    ))


def _training_measurements_pass(value: QualityMeasurements, selected_sample_count: int) -> bool:
    selected_seconds = selected_sample_count / SAMPLE_RATE_HZ
    return all((
        value.clipped_sample_count == 0,
        value.snr_db is not None and value.snr_db >= 20.0,
        value.silence_ratio is not None and value.silence_ratio <= 0.35,
        value.speech_duration_seconds is not None and 1.0 <= value.speech_duration_seconds <= selected_seconds,
        value.speech_ratio is not None and 0.5 <= value.speech_ratio <= 1.0,
        value.dropout_count == 0,
        value.dc_offset_abs is not None and value.dc_offset_abs <= 0.01,
        value.other_speaker_state is ClassificationState.PASS,
        value.bgm_state is ClassificationState.PASS,
    ))


def _unknown_measurements() -> QualityMeasurements:
    return QualityMeasurements(
        integrated_lufs=None,
        true_peak_dbtp=None,
        loudness_range_lu=None,
        clipped_sample_count=None,
        snr_db=None,
        silence_ratio=None,
        speech_duration_seconds=None,
        speech_ratio=None,
        dropout_count=None,
        dc_offset_abs=None,
        other_speaker_state=ClassificationState.UNKNOWN,
        bgm_state=ClassificationState.UNKNOWN,
    )


@dataclass(frozen=True, slots=True)
class FixtureEffectReadback:
    output_sha256: str
    output_identity_sha256: str
    output_format: AudioFormat
    output_sample_count: int
    exact_range_applied: bool
    readback_verified: bool
    directory_durable: bool
    raw_source_preserved: bool
    external_effect_count: int = 0

    def __post_init__(self) -> None:
        _digest(self.output_sha256, "output_sha256")
        _digest(self.output_identity_sha256, "output_identity_sha256")
        if not isinstance(self.output_format, AudioFormat):
            raise FinishingContractError("output_format must be an AudioFormat")
        _positive_int(self.output_sample_count, "output_sample_count", maximum=12 * 60 * 60 * SAMPLE_RATE_HZ)
        for name in ("exact_range_applied", "readback_verified", "directory_durable", "raw_source_preserved"):
            if type(getattr(self, name)) is not bool:
                raise FinishingContractError(f"{name} must be boolean")
        if type(self.external_effect_count) is not int or self.external_effect_count != 0:
            raise FinishingContractError("fixture runner cannot report an external effect")

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_sha256": self.output_sha256,
            "output_identity_sha256": self.output_identity_sha256,
            "output_format": self.output_format.to_dict(),
            "output_sample_count": self.output_sample_count,
            "exact_range_applied": self.exact_range_applied,
            "readback_verified": self.readback_verified,
            "directory_durable": self.directory_durable,
            "raw_source_preserved": self.raw_source_preserved,
            "external_effect_count": self.external_effect_count,
        }


@dataclass(frozen=True, slots=True)
class GeneratedFinishingPlan:
    operation_id: str
    project_id: str
    project_manifest_sha256: str
    installed_session_sha256: str
    operation_plan_sha256: str
    quick_clone_flow_sha256: str
    source: SourceSnapshot
    runner_build_sha256: str
    analyzer_profile_sha256: str
    start_sample: int
    end_sample: int
    output_format: AudioFormat = AudioFormat()
    head_tail_trim_only: bool = True
    cleanup_chain: tuple[str, ...] = ("highpass=f=60", "lowpass=f=18000")
    loudnorm_passes: int = 2
    target_lufs: float = -16.0
    target_true_peak_dbtp: float = -1.0
    target_lra_lu: float = 11.0

    def __post_init__(self) -> None:
        _id(self.operation_id, "operation_id")
        _id(self.project_id, "project_id")
        for value, name in (
            (self.project_manifest_sha256, "project_manifest_sha256"),
            (self.installed_session_sha256, "installed_session_sha256"),
            (self.operation_plan_sha256, "operation_plan_sha256"),
            (self.quick_clone_flow_sha256, "quick_clone_flow_sha256"),
        ):
            _digest(value, name)
        _digest(self.runner_build_sha256, "runner_build_sha256")
        _digest(self.analyzer_profile_sha256, "analyzer_profile_sha256")
        if type(self.source) is not SourceSnapshot or type(self.output_format) is not AudioFormat:
            raise FinishingContractError("generated plan binding type is invalid")
        if not isinstance(self.start_sample, int) or isinstance(self.start_sample, bool) or self.start_sample < 0:
            raise FinishingContractError("start_sample must be a non-negative integer")
        if not isinstance(self.end_sample, int) or isinstance(self.end_sample, bool) or not self.start_sample < self.end_sample <= self.source.sample_count:
            raise FinishingContractError("generated trim range is invalid")
        if type(self.head_tail_trim_only) is not bool or not self.head_tail_trim_only:
            raise FinishingContractError("only head/tail trimming is admitted")
        if type(self.cleanup_chain) is not tuple or any(type(item) is not str for item in self.cleanup_chain):
            raise FinishingContractError("cleanup chain type is invalid")
        if self.cleanup_chain != ("highpass=f=60", "lowpass=f=18000"):
            raise FinishingContractError("cleanup chain is fixed")
        if (self.loudnorm_passes, self.target_lufs, self.target_true_peak_dbtp, self.target_lra_lu) != (2, -16.0, -1.0, 11.0):
            raise FinishingContractError("generated finishing policy is fixed")


@dataclass(frozen=True, slots=True)
class TrainingCopyPlan:
    operation_id: str
    project_id: str
    project_manifest_sha256: str
    installed_session_sha256: str
    operation_plan_sha256: str
    quick_clone_flow_sha256: str
    source: SourceSnapshot
    runner_build_sha256: str
    analyzer_profile_sha256: str
    engine_recipe_sha256: str
    consent_receipt_sha256: str
    review_receipt_sha256: str
    canonical_input_receipt_sha256: str
    transport_format_receipt_sha256: str
    capture_chain_receipt_sha256: str
    consent_current: bool
    review_current: bool
    canonical_input_current: bool
    start_sample: int
    end_sample: int
    output_format: AudioFormat = AudioFormat()
    format_only: bool = True
    effects: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _id(self.operation_id, "operation_id")
        _id(self.project_id, "project_id")
        for value, name in (
            (self.project_manifest_sha256, "project_manifest_sha256"),
            (self.installed_session_sha256, "installed_session_sha256"),
            (self.operation_plan_sha256, "operation_plan_sha256"),
            (self.quick_clone_flow_sha256, "quick_clone_flow_sha256"),
            (self.runner_build_sha256, "runner_build_sha256"),
            (self.analyzer_profile_sha256, "analyzer_profile_sha256"),
            (self.engine_recipe_sha256, "engine_recipe_sha256"),
            (self.consent_receipt_sha256, "consent_receipt_sha256"),
            (self.review_receipt_sha256, "review_receipt_sha256"),
            (self.canonical_input_receipt_sha256, "canonical_input_receipt_sha256"),
            (self.transport_format_receipt_sha256, "transport_format_receipt_sha256"),
            (self.capture_chain_receipt_sha256, "capture_chain_receipt_sha256"),
        ):
            _digest(value, name)
        if type(self.source) is not SourceSnapshot or type(self.output_format) is not AudioFormat:
            raise FinishingContractError("training plan binding type is invalid")
        for name in ("consent_current", "review_current", "canonical_input_current", "format_only"):
            if type(getattr(self, name)) is not bool:
                raise FinishingContractError(f"{name} must be boolean")
        if not isinstance(self.start_sample, int) or isinstance(self.start_sample, bool) or self.start_sample < 0:
            raise FinishingContractError("start_sample must be a non-negative integer")
        if not isinstance(self.end_sample, int) or isinstance(self.end_sample, bool) or not self.start_sample < self.end_sample <= self.source.sample_count:
            raise FinishingContractError("training range is invalid")
        if type(self.effects) is not tuple or any(type(item) is not str for item in self.effects):
            raise FinishingContractError("training effects type is invalid")
        if not self.format_only or self.effects:
            raise FinishingContractError("training copy must remain format-only")
        if not self.consent_current or not self.review_current:
            raise FinishingContractError("training copy requires current Consent and review")
        if not self.canonical_input_current or self.source.source_format != AudioFormat():
            raise FinishingContractError("training copy requires current canonical input format evidence")
        if (
            self.source.terminal_receipt_sha256 is None
            or self.source.terminal_receipt_owner != "TASK-047"
            or self.source.terminal_receipt_type != TASK047_TERMINAL_RECEIPT_TYPE
            or not self.source.terminal_receipt_current
        ):
            raise FinishingContractError("training copy requires the current TASK-047 terminal recording receipt")


@dataclass(frozen=True, slots=True)
class CaptureChainBinding:
    microphone_sha256: str
    filter_chain_sha256: str
    gain_sha256: str
    transport_format_sha256: str
    sample_rate_hz: int
    channels: int
    current: bool

    def __post_init__(self) -> None:
        for value, name in (
            (self.microphone_sha256, "microphone_sha256"),
            (self.filter_chain_sha256, "filter_chain_sha256"),
            (self.gain_sha256, "gain_sha256"),
            (self.transport_format_sha256, "transport_format_sha256"),
        ):
            _digest(value, name)
        if self.sample_rate_hz != SAMPLE_RATE_HZ or self.channels != CHANNELS:
            raise FinishingContractError("A/B capture format must be 48000 Hz mono")
        if type(self.current) is not bool:
            raise FinishingContractError("capture-chain currentness must be boolean")

    def to_dict(self) -> dict[str, Any]:
        return {
            "microphone_sha256": self.microphone_sha256,
            "filter_chain_sha256": self.filter_chain_sha256,
            "gain_sha256": self.gain_sha256,
            "transport_format_sha256": self.transport_format_sha256,
            "sample_rate_hz": self.sample_rate_hz,
            "channels": self.channels,
            "current": self.current,
        }


@dataclass(frozen=True, slots=True)
class EnvironmentCaptureBinding:
    session_id: str
    condition: CaptureCondition
    capture_receipt_sha256: str
    room_tone_receipt_sha256: str
    source_sha256: str
    source_identity_sha256: str
    capture_generation_sha256: str
    room_tone_generation_sha256: str
    capture_receipt_current: bool
    room_tone_receipt_current: bool
    source_identity_current: bool
    source_read_current: bool
    source_ancestor_current: bool
    capture_chain: CaptureChainBinding

    def __post_init__(self) -> None:
        _id(self.session_id, "session_id")
        object.__setattr__(self, "condition", _enum(CaptureCondition, self.condition, "condition"))
        _digest(self.capture_receipt_sha256, "capture_receipt_sha256")
        _digest(self.room_tone_receipt_sha256, "room_tone_receipt_sha256")
        _digest(self.source_sha256, "source_sha256")
        _digest(self.source_identity_sha256, "source_identity_sha256")
        _digest(self.capture_generation_sha256, "capture_generation_sha256")
        _digest(self.room_tone_generation_sha256, "room_tone_generation_sha256")
        for name in (
            "capture_receipt_current", "room_tone_receipt_current",
            "source_identity_current", "source_read_current", "source_ancestor_current",
        ):
            if type(getattr(self, name)) is not bool:
                raise FinishingContractError(f"{name} must be boolean")
        if type(self.capture_chain) is not CaptureChainBinding:
            raise FinishingContractError("capture_chain type is invalid")

    @property
    def secure_and_current(self) -> bool:
        return all((
            self.capture_chain.current,
            self.capture_receipt_current,
            self.room_tone_receipt_current,
            self.source_identity_current,
            self.source_read_current,
            self.source_ancestor_current,
            self.capture_generation_sha256 == self.room_tone_generation_sha256,
        ))

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "condition": self.condition.value,
            "capture_receipt_sha256": self.capture_receipt_sha256,
            "room_tone_receipt_sha256": self.room_tone_receipt_sha256,
            "source_sha256": self.source_sha256,
            "source_identity_sha256": self.source_identity_sha256,
            "capture_generation_sha256": self.capture_generation_sha256,
            "room_tone_generation_sha256": self.room_tone_generation_sha256,
            "capture_receipt_current": self.capture_receipt_current,
            "room_tone_receipt_current": self.room_tone_receipt_current,
            "source_identity_current": self.source_identity_current,
            "source_read_current": self.source_read_current,
            "source_ancestor_current": self.source_ancestor_current,
            "capture_chain": self.capture_chain.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class NoiseBandProfile:
    low_dbfs: float
    mid_dbfs: float
    high_dbfs: float

    def __post_init__(self) -> None:
        for name in ("low_dbfs", "mid_dbfs", "high_dbfs"):
            value = _finite(getattr(self, name), name)
            if value > 0:
                raise FinishingContractError("noise-band measurements must use dBFS")

    def to_dict(self) -> dict[str, float]:
        return {"low_dbfs": self.low_dbfs, "mid_dbfs": self.mid_dbfs, "high_dbfs": self.high_dbfs}


@dataclass(frozen=True, slots=True)
class EnvironmentSegmentMeasurement:
    condition: CaptureCondition
    effort: VoiceEffort
    source_sha256: str
    source_identity_sha256: str
    room_tone_noise_floor_dbfs: float | None
    speech_rms_dbfs: float | None
    speech_peak_dbfs: float | None
    clipped_sample_count: int | None
    nonfinite_sample_count: int | None
    dc_offset_abs: float | None
    dropout_count: int | None
    snr_db: float | None
    snr_approximate: bool
    speech_ratio: float | None
    noise_profile: NoiseBandProfile | None
    current: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "condition", _enum(CaptureCondition, self.condition, "condition"))
        object.__setattr__(self, "effort", _enum(VoiceEffort, self.effort, "effort"))
        _digest(self.source_sha256, "source_sha256")
        _digest(self.source_identity_sha256, "source_identity_sha256")
        for name in ("room_tone_noise_floor_dbfs", "speech_rms_dbfs", "speech_peak_dbfs", "dc_offset_abs", "snr_db", "speech_ratio"):
            value = getattr(self, name)
            if value is not None:
                value = _finite(value, name)
                if name in {"room_tone_noise_floor_dbfs", "speech_rms_dbfs", "speech_peak_dbfs"} and value > 0:
                    raise FinishingContractError("level measurements must use dBFS")
                if name in {"dc_offset_abs", "speech_ratio"} and not 0 <= value <= 1:
                    raise FinishingContractError(f"{name} is out of range")
        for name in ("clipped_sample_count", "nonfinite_sample_count", "dropout_count"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                raise FinishingContractError(f"{name} must be a non-negative integer")
        if type(self.snr_approximate) is not bool or type(self.current) is not bool:
            raise FinishingContractError("measurement flags must be boolean")
        if self.noise_profile is not None and type(self.noise_profile) is not NoiseBandProfile:
            raise FinishingContractError("noise_profile type is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition.value,
            "effort": self.effort.value,
            "source_sha256": self.source_sha256,
            "source_identity_sha256": self.source_identity_sha256,
            "room_tone_noise_floor_dbfs": self.room_tone_noise_floor_dbfs,
            "speech_rms_dbfs": self.speech_rms_dbfs,
            "speech_peak_dbfs": self.speech_peak_dbfs,
            "clipped_sample_count": self.clipped_sample_count,
            "nonfinite_sample_count": self.nonfinite_sample_count,
            "dc_offset_abs": self.dc_offset_abs,
            "dropout_count": self.dropout_count,
            "snr_db": self.snr_db,
            "snr_approximate": self.snr_approximate,
            "speech_ratio": self.speech_ratio,
            "noise_profile": None if self.noise_profile is None else self.noise_profile.to_dict(),
            "current": self.current,
        }


@dataclass(frozen=True, slots=True)
class DenoisePairMeasurement:
    condition: CaptureCondition
    effort: VoiceEffort
    input_source_sha256: str
    denoised_input_source_sha256: str
    input_source_identity_sha256: str
    denoised_input_source_identity_sha256: str
    raw_artifact_sha256: str
    denoised_artifact_sha256: str
    noise_reduction_db: float | None
    voice_distortion_ratio: float | None
    overprocessing_state: ClassificationState
    current: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "condition", _enum(CaptureCondition, self.condition, "condition"))
        object.__setattr__(self, "effort", _enum(VoiceEffort, self.effort, "effort"))
        for value, name in (
            (self.input_source_sha256, "input_source_sha256"),
            (self.denoised_input_source_sha256, "denoised_input_source_sha256"),
            (self.input_source_identity_sha256, "input_source_identity_sha256"),
            (self.denoised_input_source_identity_sha256, "denoised_input_source_identity_sha256"),
            (self.raw_artifact_sha256, "raw_artifact_sha256"),
            (self.denoised_artifact_sha256, "denoised_artifact_sha256"),
        ):
            _digest(value, name)
        if self.noise_reduction_db is not None:
            _finite(self.noise_reduction_db, "noise_reduction_db")
        if self.voice_distortion_ratio is not None:
            value = _finite(self.voice_distortion_ratio, "voice_distortion_ratio")
            if not 0 <= value <= 1:
                raise FinishingContractError("voice_distortion_ratio is out of range")
        object.__setattr__(self, "overprocessing_state", _enum(ClassificationState, self.overprocessing_state, "overprocessing_state"))
        if type(self.current) is not bool:
            raise FinishingContractError("denoise currentness must be boolean")

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition.value,
            "effort": self.effort.value,
            "input_source_sha256": self.input_source_sha256,
            "denoised_input_source_sha256": self.denoised_input_source_sha256,
            "input_source_identity_sha256": self.input_source_identity_sha256,
            "denoised_input_source_identity_sha256": self.denoised_input_source_identity_sha256,
            "raw_artifact_sha256": self.raw_artifact_sha256,
            "denoised_artifact_sha256": self.denoised_artifact_sha256,
            "noise_reduction_db": self.noise_reduction_db,
            "voice_distortion_ratio": self.voice_distortion_ratio,
            "overprocessing_state": self.overprocessing_state.value,
            "current": self.current,
        }


@dataclass(frozen=True, slots=True)
class EnvironmentMeasurementBundle:
    segments: tuple[EnvironmentSegmentMeasurement, ...]
    denoise_pairs: tuple[DenoisePairMeasurement, ...]

    def __post_init__(self) -> None:
        expected = tuple((condition, effort) for condition in CaptureCondition for effort in VoiceEffort)
        if (
            len(self.segments) != 6
            or any(type(item) is not EnvironmentSegmentMeasurement for item in self.segments)
            or tuple((item.condition, item.effort) for item in self.segments) != expected
        ):
            raise FinishingContractError("environment segment measurement set is invalid")
        if (
            len(self.denoise_pairs) != 6
            or any(type(item) is not DenoisePairMeasurement for item in self.denoise_pairs)
            or tuple((item.condition, item.effort) for item in self.denoise_pairs) != expected
        ):
            raise FinishingContractError("denoise comparison set is invalid")


@dataclass(frozen=True, slots=True)
class EnvironmentABPlan:
    operation_id: str
    project_id: str
    project_manifest_sha256: str
    installed_session_sha256: str
    operation_plan_sha256: str
    runner_build_sha256: str
    analyzer_profile_sha256: str
    quality_policy_sha256: str
    off_capture: EnvironmentCaptureBinding
    on_capture: EnvironmentCaptureBinding

    def __post_init__(self) -> None:
        _id(self.operation_id, "operation_id")
        _id(self.project_id, "project_id")
        for value, name in (
            (self.project_manifest_sha256, "project_manifest_sha256"),
            (self.installed_session_sha256, "installed_session_sha256"),
            (self.operation_plan_sha256, "operation_plan_sha256"),
            (self.runner_build_sha256, "runner_build_sha256"),
            (self.analyzer_profile_sha256, "analyzer_profile_sha256"),
            (self.quality_policy_sha256, "quality_policy_sha256"),
        ):
            _digest(value, name)
        if type(self.off_capture) is not EnvironmentCaptureBinding or type(self.on_capture) is not EnvironmentCaptureBinding:
            raise FinishingContractError("environment capture binding type is invalid")
        if self.off_capture.condition is not CaptureCondition.AIR_CONDITIONER_OFF or self.on_capture.condition is not CaptureCondition.AIR_CONDITIONER_ON:
            raise FinishingContractError("A/B plan requires exact OFF and ON captures")
        if self.off_capture.session_id == self.on_capture.session_id:
            raise FinishingContractError("A/B captures require distinct sessions")

    @property
    def comparable(self) -> bool:
        return (
            self.off_capture.secure_and_current
            and self.on_capture.secure_and_current
            and replace(self.off_capture.capture_chain, current=True)
            == replace(self.on_capture.capture_chain, current=True)
        )


@dataclass(frozen=True, slots=True)
class StrictWavDecodeEvidence:
    source_sha256: str
    source_identity_sha256: str
    decoder_build_sha256: str
    sample_rate_hz: int
    channels: int
    sample_format: str
    sample_count_per_channel: int
    riff_header_valid: bool
    format_chunk_valid: bool
    data_length_exact: bool
    odd_chunks_validated: bool
    nonfinite_sample_count: int
    current: bool

    def __post_init__(self) -> None:
        for value, name in (
            (self.source_sha256, "source_sha256"),
            (self.source_identity_sha256, "source_identity_sha256"),
            (self.decoder_build_sha256, "decoder_build_sha256"),
        ):
            _digest(value, name)
        _positive_int(self.sample_rate_hz, "sample_rate_hz", maximum=384_000)
        _positive_int(self.channels, "channels", maximum=32)
        if self.sample_format not in {"IEEE_FLOAT32", "PCM_S16LE", "PCM_S24LE", "PCM_S32LE"}:
            raise FinishingContractError("input WAV sample format is unsupported")
        _positive_int(self.sample_count_per_channel, "sample_count_per_channel", maximum=12 * 60 * 60 * 384_000)
        for name in ("riff_header_valid", "format_chunk_valid", "data_length_exact", "odd_chunks_validated", "current"):
            if type(getattr(self, name)) is not bool:
                raise FinishingContractError(f"{name} must be boolean")
        if not isinstance(self.nonfinite_sample_count, int) or isinstance(self.nonfinite_sample_count, bool) or self.nonfinite_sample_count < 0:
            raise FinishingContractError("nonfinite_sample_count must be a non-negative integer")

    @property
    def strict_valid(self) -> bool:
        return all((
            self.riff_header_valid,
            self.format_chunk_valid,
            self.data_length_exact,
            self.odd_chunks_validated,
            self.current,
            self.nonfinite_sample_count == 0,
        ))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_sha256": self.source_sha256,
            "source_identity_sha256": self.source_identity_sha256,
            "decoder_build_sha256": self.decoder_build_sha256,
            "sample_rate_hz": self.sample_rate_hz,
            "channels": self.channels,
            "sample_format": self.sample_format,
            "sample_count_per_channel": self.sample_count_per_channel,
            "riff_header_valid": self.riff_header_valid,
            "format_chunk_valid": self.format_chunk_valid,
            "data_length_exact": self.data_length_exact,
            "odd_chunks_validated": self.odd_chunks_validated,
            "nonfinite_sample_count": self.nonfinite_sample_count,
            "current": self.current,
        }


@dataclass(frozen=True, slots=True)
class TrainingFormatPolicy:
    policy_receipt_sha256: str
    policy_current: bool
    output_format: AudioFormat
    channel_strategy: ChannelStrategy
    selected_channel_index: int | None
    phase_audit_receipt_sha256: str | None
    resampler_build_sha256: str
    dither_policy_sha256: str | None
    lossy_codec: bool = False

    def __post_init__(self) -> None:
        _digest(self.policy_receipt_sha256, "policy_receipt_sha256")
        if type(self.policy_current) is not bool or not self.policy_current:
            raise FinishingContractError("training format policy must be current")
        if type(self.output_format) is not AudioFormat:
            raise FinishingContractError("output_format type is invalid")
        object.__setattr__(self, "channel_strategy", _enum(ChannelStrategy, self.channel_strategy, "channel_strategy"))
        if self.selected_channel_index is not None and (
            not isinstance(self.selected_channel_index, int)
            or isinstance(self.selected_channel_index, bool)
            or self.selected_channel_index < 0
        ):
            raise FinishingContractError("selected_channel_index is invalid")
        if self.phase_audit_receipt_sha256 is not None:
            _digest(self.phase_audit_receipt_sha256, "phase_audit_receipt_sha256")
        _digest(self.resampler_build_sha256, "resampler_build_sha256")
        if self.dither_policy_sha256 is not None:
            _digest(self.dither_policy_sha256, "dither_policy_sha256")
        if type(self.lossy_codec) is not bool:
            raise FinishingContractError("lossy_codec must be boolean")
        if self.lossy_codec:
            raise FinishingContractError("lossy codec is forbidden for training WAV")

    def validate_input(self, decode: StrictWavDecodeEvidence) -> None:
        if decode.channels == 1:
            if self.channel_strategy is not ChannelStrategy.MONO_PRESERVE or self.selected_channel_index is not None:
                raise FinishingContractError("mono input must use MONO_PRESERVE")
        elif self.channel_strategy is ChannelStrategy.SELECT_CHANNEL:
            if self.selected_channel_index is None or self.selected_channel_index >= decode.channels:
                raise FinishingContractError("selected channel is outside the input")
        elif self.channel_strategy is ChannelStrategy.PHASE_SAFE_DOWNMIX:
            if self.phase_audit_receipt_sha256 is None:
                raise FinishingContractError("phase-safe downmix requires an audit receipt")
        else:
            raise FinishingContractError("multichannel input needs explicit channel policy")
        if decode.sample_format != SAMPLE_FORMAT and self.dither_policy_sha256 is None:
            raise FinishingContractError("format conversion requires an explicit dither policy")

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_receipt_sha256": self.policy_receipt_sha256,
            "policy_current": self.policy_current,
            "output_format": self.output_format.to_dict(),
            "channel_strategy": self.channel_strategy.value,
            "selected_channel_index": self.selected_channel_index,
            "phase_audit_receipt_sha256": self.phase_audit_receipt_sha256,
            "resampler_build_sha256": self.resampler_build_sha256,
            "dither_policy_sha256": self.dither_policy_sha256,
            "lossy_codec": self.lossy_codec,
        }


@dataclass(frozen=True, slots=True, order=True)
class SampleRange:
    start_sample: int
    end_sample: int

    def __post_init__(self) -> None:
        if not isinstance(self.start_sample, int) or isinstance(self.start_sample, bool) or self.start_sample < 0:
            raise FinishingContractError("range start is invalid")
        if not isinstance(self.end_sample, int) or isinstance(self.end_sample, bool) or self.end_sample <= self.start_sample:
            raise FinishingContractError("range end is invalid")

    @property
    def sample_count(self) -> int:
        return self.end_sample - self.start_sample

    def to_dict(self) -> dict[str, int]:
        return {"start_sample": self.start_sample, "end_sample": self.end_sample}


@dataclass(frozen=True, slots=True)
class SpeechEvidenceInterval:
    sample_range: SampleRange
    interval_class: IntervalClass
    confidence: float
    evidence_sha256: str

    def __post_init__(self) -> None:
        if type(self.sample_range) is not SampleRange:
            raise FinishingContractError("sample_range type is invalid")
        object.__setattr__(self, "interval_class", _enum(IntervalClass, self.interval_class, "interval_class"))
        confidence = _finite(self.confidence, "confidence")
        if not 0 <= confidence <= 1:
            raise FinishingContractError("confidence is out of range")
        _digest(self.evidence_sha256, "evidence_sha256")

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_range": self.sample_range.to_dict(),
            "interval_class": self.interval_class.value,
            "confidence": self.confidence,
            "evidence_sha256": self.evidence_sha256,
        }


@dataclass(frozen=True, slots=True)
class SpeechContinuityPolicy:
    policy_receipt_sha256: str
    long_non_speech_min_samples: int = 48_000
    max_natural_pause_samples: int = 24_000
    pre_speech_padding_samples: int = 2_400
    post_speech_padding_samples: int = 3_600
    hangover_samples: int = 2_400
    minimum_speech_samples: int = 4_800
    fade_samples: int = BOUNDARY_CROSSFADE_SAMPLES
    minimum_confirmed_non_speech_confidence: float = CONFIRMED_NON_SPEECH_CONFIDENCE

    def __post_init__(self) -> None:
        _digest(self.policy_receipt_sha256, "policy_receipt_sha256")
        for name in (
            "long_non_speech_min_samples", "max_natural_pause_samples",
            "pre_speech_padding_samples", "post_speech_padding_samples",
            "hangover_samples", "minimum_speech_samples", "fade_samples",
        ):
            _positive_int(getattr(self, name), name, maximum=10 * SAMPLE_RATE_HZ)
        if self.long_non_speech_min_samples <= self.max_natural_pause_samples:
            raise FinishingContractError("long non-speech threshold must preserve natural pauses")
        if self.fade_samples != BOUNDARY_CROSSFADE_SAMPLES:
            raise FinishingContractError("boundary fade sample count is fixed")
        if self.fade_samples >= min(self.pre_speech_padding_samples, self.post_speech_padding_samples):
            raise FinishingContractError("fade must not consume speech padding")
        confidence = _finite(
            self.minimum_confirmed_non_speech_confidence,
            "minimum_confirmed_non_speech_confidence",
        )
        if confidence != CONFIRMED_NON_SPEECH_CONFIDENCE:
            raise FinishingContractError("confirmed non-speech confidence is fixed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_receipt_sha256": self.policy_receipt_sha256,
            "long_non_speech_min_samples": self.long_non_speech_min_samples,
            "max_natural_pause_samples": self.max_natural_pause_samples,
            "pre_speech_padding_samples": self.pre_speech_padding_samples,
            "post_speech_padding_samples": self.post_speech_padding_samples,
            "hangover_samples": self.hangover_samples,
            "minimum_speech_samples": self.minimum_speech_samples,
            "fade_samples": self.fade_samples,
            "minimum_confirmed_non_speech_confidence": self.minimum_confirmed_non_speech_confidence,
        }


def _derive_speech_ranges(
    *,
    sample_count: int,
    intervals: tuple[SpeechEvidenceInterval, ...],
    policy: SpeechContinuityPolicy,
) -> tuple[tuple[SampleRange, ...], tuple[SampleRange, ...]]:
    keep: list[SampleRange] = []
    speech = [item for item in intervals if item.interval_class is IntervalClass.SPEECH]
    for item in intervals:
        remove_long = (
            item.interval_class is IntervalClass.NON_SPEECH
            and item.sample_range.sample_count >= policy.long_non_speech_min_samples
            and item.confidence >= policy.minimum_confirmed_non_speech_confidence
        )
        if not remove_long:
            keep.append(item.sample_range)
    for item in speech:
        keep.append(SampleRange(
            max(0, item.sample_range.start_sample - policy.pre_speech_padding_samples),
            min(
                sample_count,
                item.sample_range.end_sample
                + policy.post_speech_padding_samples
                + policy.hangover_samples,
            ),
        ))
    keep.sort()
    merged: list[SampleRange] = []
    for item in keep:
        if not merged or item.start_sample > merged[-1].end_sample:
            merged.append(item)
        else:
            merged[-1] = SampleRange(
                merged[-1].start_sample,
                max(merged[-1].end_sample, item.end_sample),
            )
    removed: list[SampleRange] = []
    cursor = 0
    for item in merged:
        if cursor < item.start_sample:
            removed.append(SampleRange(cursor, item.start_sample))
        cursor = item.end_sample
    if cursor < sample_count:
        removed.append(SampleRange(cursor, sample_count))
    return tuple(merged), tuple(removed)


@dataclass(frozen=True, slots=True)
class SpeechContinuousPlan:
    operation_id: str
    project_id: str
    project_manifest_sha256: str
    installed_session_sha256: str
    operation_plan_sha256: str
    runner_build_sha256: str
    source: SourceSnapshot
    decode_evidence: StrictWavDecodeEvidence
    format_policy: TrainingFormatPolicy
    continuity_policy: SpeechContinuityPolicy
    quality_measurements_sha256: str
    intervals: tuple[SpeechEvidenceInterval, ...]
    retained_ranges: tuple[SampleRange, ...]
    removed_ranges: tuple[SampleRange, ...]
    boundary_mode: BoundaryMode
    boundary_count: int
    crossfade_overlap_samples: int
    output_sample_count: int

    def __post_init__(self) -> None:
        _id(self.operation_id, "operation_id")
        _id(self.project_id, "project_id")
        for value, name in (
            (self.project_manifest_sha256, "project_manifest_sha256"),
            (self.installed_session_sha256, "installed_session_sha256"),
            (self.operation_plan_sha256, "operation_plan_sha256"),
            (self.runner_build_sha256, "runner_build_sha256"),
            (self.quality_measurements_sha256, "quality_measurements_sha256"),
        ):
            _digest(value, name)
        if (
            type(self.source) is not SourceSnapshot
            or type(self.decode_evidence) is not StrictWavDecodeEvidence
            or type(self.format_policy) is not TrainingFormatPolicy
            or type(self.continuity_policy) is not SpeechContinuityPolicy
        ):
            raise FinishingContractError("speech-continuous plan binding type is invalid")
        if (
            not self.decode_evidence.strict_valid
            or not self.source.secure_and_current
            or not self.source.terminal_receipt_current
            or self.source.terminal_receipt_sha256 is None
            or self.source.terminal_receipt_owner != "TASK-047"
            or self.source.terminal_receipt_type != TASK047_TERMINAL_RECEIPT_TYPE
            or self.source.source_sha256 != self.decode_evidence.source_sha256
            or self.source.source_identity_sha256
            != self.decode_evidence.source_identity_sha256
            or self.source.sample_count
            != self.decode_evidence.sample_count_per_channel
            or self.decode_evidence.sample_rate_hz != SAMPLE_RATE_HZ
            or self.decode_evidence.channels != CHANNELS
            or self.decode_evidence.sample_format != SAMPLE_FORMAT
            or self.source.source_format != AudioFormat()
        ):
            raise FinishingContractError("speech-continuous source binding is invalid")
        if not self.retained_ranges or any(type(item) is not SampleRange for item in self.retained_ranges):
            raise FinishingContractError("speech-continuous retained ranges are invalid")
        if any(type(item) is not SampleRange for item in self.removed_ranges):
            raise FinishingContractError("speech-continuous removed ranges are invalid")
        if not self.intervals or any(type(item) is not SpeechEvidenceInterval for item in self.intervals):
            raise FinishingContractError("speech-continuous interval evidence is invalid")
        interval_cursor = 0
        speech_sample_count = 0
        for item in self.intervals:
            if item.sample_range.start_sample != interval_cursor:
                raise FinishingContractError("VAD intervals must exactly cover the input")
            interval_cursor = item.sample_range.end_sample
            if item.interval_class is IntervalClass.SPEECH:
                speech_sample_count += item.sample_range.sample_count
        if interval_cursor != self.source.sample_count:
            raise FinishingContractError("VAD intervals must exactly cover the input")
        if speech_sample_count < self.continuity_policy.minimum_speech_samples:
            raise FinishingContractError("minimum speech evidence is required")
        object.__setattr__(self, "boundary_mode", _enum(BoundaryMode, self.boundary_mode, "boundary_mode"))
        expected_boundary_count = max(0, len(self.retained_ranges) - 1)
        if (
            not isinstance(self.boundary_count, int)
            or isinstance(self.boundary_count, bool)
            or self.boundary_count != expected_boundary_count
        ):
            raise FinishingContractError("speech-continuous boundary count is invalid")
        expected_overlap = expected_boundary_count * self.continuity_policy.fade_samples
        if expected_boundary_count and any(
            item.sample_count < self.continuity_policy.fade_samples
            for item in self.retained_ranges
        ):
            raise FinishingContractError("retained range is too short for boundary crossfade")
        if (
            not isinstance(self.crossfade_overlap_samples, int)
            or isinstance(self.crossfade_overlap_samples, bool)
            or self.crossfade_overlap_samples != expected_overlap
        ):
            raise FinishingContractError("speech-continuous crossfade accounting is invalid")
        if self.boundary_mode is not BoundaryMode.EQUAL_POWER_CROSSFADE:
            raise FinishingContractError("speech-continuous boundary mode is invalid")
        if (
            not isinstance(self.output_sample_count, int)
            or isinstance(self.output_sample_count, bool)
            or self.output_sample_count <= 0
            or self.output_sample_count
            != sum(item.sample_count for item in self.retained_ranges) - expected_overlap
        ):
            raise FinishingContractError("speech-continuous output range accounting is invalid")
        cursor = 0
        for item in sorted((*self.retained_ranges, *self.removed_ranges)):
            if item.start_sample != cursor:
                raise FinishingContractError("speech-continuous range map must partition the input")
            cursor = item.end_sample
        if cursor != self.source.sample_count:
            raise FinishingContractError("speech-continuous range map must partition the input")
        expected_retained, expected_removed = _derive_speech_ranges(
            sample_count=self.source.sample_count,
            intervals=self.intervals,
            policy=self.continuity_policy,
        )
        if (
            self.retained_ranges != expected_retained
            or self.removed_ranges != expected_removed
        ):
            raise FinishingContractError("speech-continuous range map is not policy-derived")

    @property
    def input_pcm_payload_bytes(self) -> int:
        return self.source.sample_count * CHANNELS * PCM_BYTES_PER_SAMPLE

    @property
    def output_pcm_payload_bytes(self) -> int:
        return self.output_sample_count * CHANNELS * PCM_BYTES_PER_SAMPLE

    @property
    def size_reduction_bytes(self) -> int:
        return self.input_pcm_payload_bytes - self.output_pcm_payload_bytes


def plan_speech_continuous(
    *,
    operation_id: str,
    project_id: str,
    project_manifest_sha256: str,
    installed_session_sha256: str,
    operation_plan_sha256: str,
    runner_build_sha256: str,
    source: SourceSnapshot,
    decode_evidence: StrictWavDecodeEvidence,
    format_policy: TrainingFormatPolicy,
    continuity_policy: SpeechContinuityPolicy,
    quality_measurements_sha256: str,
    intervals: tuple[SpeechEvidenceInterval, ...],
) -> SpeechContinuousPlan:
    if not decode_evidence.strict_valid:
        raise FinishingContractError("strict WAV evidence is invalid")
    if (
        source.source_sha256 != decode_evidence.source_sha256
        or source.source_identity_sha256 != decode_evidence.source_identity_sha256
        or source.sample_count != decode_evidence.sample_count_per_channel
        or not source.secure_and_current
        or source.terminal_receipt_sha256 is None
        or source.terminal_receipt_owner != "TASK-047"
        or source.terminal_receipt_type != TASK047_TERMINAL_RECEIPT_TYPE
        or not source.terminal_receipt_current
    ):
        raise FinishingContractError("strict WAV evidence is not current for the source")
    if (
        decode_evidence.sample_rate_hz != SAMPLE_RATE_HZ
        or decode_evidence.channels != CHANNELS
        or decode_evidence.sample_format != SAMPLE_FORMAT
        or source.source_format != AudioFormat()
    ):
        raise FinishingContractError("TASK-048 requires verified canonical TASK-047 input")
    format_policy.validate_input(decode_evidence)
    if not intervals:
        raise FinishingContractError("VAD interval coverage is empty")
    cursor = 0
    for item in intervals:
        if type(item) is not SpeechEvidenceInterval or item.sample_range.start_sample != cursor:
            raise FinishingContractError("VAD intervals must exactly cover the input")
        cursor = item.sample_range.end_sample
    if cursor != source.sample_count:
        raise FinishingContractError("VAD intervals must exactly cover the input")
    speech = [item for item in intervals if item.interval_class is IntervalClass.SPEECH]
    if not speech or sum(item.sample_range.sample_count for item in speech) < continuity_policy.minimum_speech_samples:
        raise FinishingContractError("minimum speech evidence is required")
    retained, removed = _derive_speech_ranges(
        sample_count=source.sample_count,
        intervals=intervals,
        policy=continuity_policy,
    )
    boundary_count = max(0, len(retained) - 1)
    crossfade_overlap_samples = boundary_count * continuity_policy.fade_samples
    return SpeechContinuousPlan(
        operation_id=operation_id,
        project_id=project_id,
        project_manifest_sha256=project_manifest_sha256,
        installed_session_sha256=installed_session_sha256,
        operation_plan_sha256=operation_plan_sha256,
        runner_build_sha256=runner_build_sha256,
        source=source,
        decode_evidence=decode_evidence,
        format_policy=format_policy,
        continuity_policy=continuity_policy,
        quality_measurements_sha256=quality_measurements_sha256,
        intervals=intervals,
        retained_ranges=retained,
        removed_ranges=removed,
        boundary_mode=BoundaryMode.EQUAL_POWER_CROSSFADE,
        boundary_count=boundary_count,
        crossfade_overlap_samples=crossfade_overlap_samples,
        output_sample_count=sum(item.sample_count for item in retained) - crossfade_overlap_samples,
    )


@dataclass(frozen=True, slots=True)
class SpeechContinuousReadback:
    output_sha256: str
    output_identity_sha256: str
    output_format: AudioFormat
    output_sample_count: int
    boundary_mode: BoundaryMode
    boundary_count: int
    crossfade_overlap_samples: int
    boundary_evidence_sha256s: tuple[str, ...]
    range_map_verified: bool
    zero_cross_or_crossfade_verified: bool
    speech_attack_preserved: bool
    speech_tail_preserved: bool
    partial_output_published: bool
    readback_verified: bool
    directory_durable: bool
    raw_source_preserved: bool
    external_effect_count: int = 0

    def __post_init__(self) -> None:
        _digest(self.output_sha256, "output_sha256")
        _digest(self.output_identity_sha256, "output_identity_sha256")
        if type(self.output_format) is not AudioFormat:
            raise FinishingContractError("output_format type is invalid")
        _positive_int(self.output_sample_count, "output_sample_count", maximum=12 * 60 * 60 * SAMPLE_RATE_HZ)
        object.__setattr__(self, "boundary_mode", _enum(BoundaryMode, self.boundary_mode, "boundary_mode"))
        if not isinstance(self.boundary_count, int) or isinstance(self.boundary_count, bool) or self.boundary_count < 0:
            raise FinishingContractError("boundary_count is invalid")
        if not isinstance(self.crossfade_overlap_samples, int) or isinstance(self.crossfade_overlap_samples, bool) or self.crossfade_overlap_samples < 0:
            raise FinishingContractError("crossfade_overlap_samples is invalid")
        if len(self.boundary_evidence_sha256s) != self.boundary_count:
            raise FinishingContractError("boundary evidence cardinality is invalid")
        for item in self.boundary_evidence_sha256s:
            _digest(item, "boundary_evidence_sha256")
        for name in (
            "range_map_verified", "zero_cross_or_crossfade_verified",
            "speech_attack_preserved", "speech_tail_preserved",
            "partial_output_published", "readback_verified",
            "directory_durable", "raw_source_preserved",
        ):
            if type(getattr(self, name)) is not bool:
                raise FinishingContractError(f"{name} must be boolean")
        if type(self.external_effect_count) is not int or self.external_effect_count != 0:
            raise FinishingContractError("fixture speech runner cannot report an external effect")


def _speech_plan_sha256(plan: SpeechContinuousPlan) -> str:
    return _receipt_hash({
        "operation_kind": OperationKind.SPEECH_CONTINUOUS_TRAINING_FINISH.value,
        "operation_id": plan.operation_id,
        "project_id": plan.project_id,
        "project_manifest_sha256": plan.project_manifest_sha256,
        "installed_session_sha256": plan.installed_session_sha256,
        "operation_plan_sha256": plan.operation_plan_sha256,
        "runner_build_sha256": plan.runner_build_sha256,
        "source_sha256": plan.source.source_sha256,
        "source_identity_sha256": plan.source.source_identity_sha256,
        "decode_evidence": plan.decode_evidence.to_dict(),
        "format_policy": plan.format_policy.to_dict(),
        "continuity_policy": plan.continuity_policy.to_dict(),
        "quality_measurements_sha256": plan.quality_measurements_sha256,
        "intervals": [item.to_dict() for item in plan.intervals],
        "retained_ranges": [item.to_dict() for item in plan.retained_ranges],
        "removed_ranges": [item.to_dict() for item in plan.removed_ranges],
        "boundary_mode": plan.boundary_mode.value,
        "boundary_count": plan.boundary_count,
        "crossfade_overlap_samples": plan.crossfade_overlap_samples,
        "output_sample_count": plan.output_sample_count,
        "input_pcm_payload_bytes": plan.input_pcm_payload_bytes,
        "output_pcm_payload_bytes": plan.output_pcm_payload_bytes,
        "size_reduction_bytes": plan.size_reduction_bytes,
        "size_optimization_mode": "LOSSLESS_SAMPLE_RANGE_REMOVAL_PLUS_BOUNDARY_CROSSFADE",
    })


def _task046_lineage_candidate_sha256(
    plan: SpeechContinuousPlan,
    readback: SpeechContinuousReadback,
) -> str:
    return _receipt_hash({
        "lineage_type": "TASK048_SPEECH_CONTINUOUS_CANDIDATE_V1",
        "source_owner": "TASK-047",
        "candidate_consumer": "TASK-046",
        "source_sha256": plan.source.source_sha256,
        "source_identity_sha256": plan.source.source_identity_sha256,
        "source_terminal_receipt_sha256": plan.source.terminal_receipt_sha256,
        "plan_sha256": _speech_plan_sha256(plan),
        "quality_measurements_sha256": plan.quality_measurements_sha256,
        "format_policy_receipt_sha256": plan.format_policy.policy_receipt_sha256,
        "continuity_policy_receipt_sha256": plan.continuity_policy.policy_receipt_sha256,
        "retained_ranges": [item.to_dict() for item in plan.retained_ranges],
        "removed_ranges": [item.to_dict() for item in plan.removed_ranges],
        "output_sha256": readback.output_sha256,
        "output_identity_sha256": readback.output_identity_sha256,
        "output_format": readback.output_format.to_dict(),
        "output_sample_count": readback.output_sample_count,
        "boundary_mode": readback.boundary_mode.value,
        "boundary_count": readback.boundary_count,
        "crossfade_overlap_samples": readback.crossfade_overlap_samples,
        "boundary_evidence_sha256s": list(readback.boundary_evidence_sha256s),
        "raw_source_preserved": readback.raw_source_preserved,
        "authority_created": False,
        "dataset_adoption_started": False,
    })


def _plan_sha256(plan: GeneratedFinishingPlan | TrainingCopyPlan) -> str:
    body: dict[str, Any] = {
        "operation_id": plan.operation_id,
        "project_id": plan.project_id,
        "project_manifest_sha256": plan.project_manifest_sha256,
        "installed_session_sha256": plan.installed_session_sha256,
        "operation_plan_sha256": plan.operation_plan_sha256,
        "quick_clone_flow_sha256": plan.quick_clone_flow_sha256,
        "source": plan.source.to_dict(),
        "runner_build_sha256": plan.runner_build_sha256,
        "analyzer_profile_sha256": plan.analyzer_profile_sha256,
        "start_sample": plan.start_sample,
        "end_sample": plan.end_sample,
        "output_format": plan.output_format.to_dict(),
    }
    if type(plan) is GeneratedFinishingPlan:
        body.update({
            "operation_kind": OperationKind.GENERATED_WAV_FINISH.value,
            "head_tail_trim_only": plan.head_tail_trim_only,
            "cleanup_chain": list(plan.cleanup_chain),
            "loudnorm_passes": plan.loudnorm_passes,
            "target_lufs": plan.target_lufs,
            "target_true_peak_dbtp": plan.target_true_peak_dbtp,
            "target_lra_lu": plan.target_lra_lu,
        })
    else:
        body.update({
            "operation_kind": OperationKind.TRAINING_COPY_QA.value,
            "engine_recipe_sha256": plan.engine_recipe_sha256,
            "consent_receipt_sha256": plan.consent_receipt_sha256,
            "review_receipt_sha256": plan.review_receipt_sha256,
            "canonical_input_receipt_sha256": plan.canonical_input_receipt_sha256,
            "transport_format_receipt_sha256": plan.transport_format_receipt_sha256,
            "capture_chain_receipt_sha256": plan.capture_chain_receipt_sha256,
            "consent_current": plan.consent_current,
            "review_current": plan.review_current,
            "canonical_input_current": plan.canonical_input_current,
            "format_only": plan.format_only,
            "effects": list(plan.effects),
        })
    return _receipt_hash(body)


def _environment_plan_sha256(plan: EnvironmentABPlan) -> str:
    return _receipt_hash({
        "operation_kind": OperationKind.ENVIRONMENT_AB_QA.value,
        "operation_id": plan.operation_id,
        "project_id": plan.project_id,
        "project_manifest_sha256": plan.project_manifest_sha256,
        "installed_session_sha256": plan.installed_session_sha256,
        "operation_plan_sha256": plan.operation_plan_sha256,
        "runner_build_sha256": plan.runner_build_sha256,
        "analyzer_profile_sha256": plan.analyzer_profile_sha256,
        "quality_policy_sha256": plan.quality_policy_sha256,
        "off_capture": plan.off_capture.to_dict(),
        "on_capture": plan.on_capture.to_dict(),
    })


class FixtureAudioRunner(Protocol):
    fixture_only: bool
    authority_created: bool
    production_eligible: bool
    runner_build_sha256: str

    def finish_generated(self, plan: GeneratedFinishingPlan) -> tuple[QualityMeasurements, FixtureEffectReadback]: ...
    def prepare_training_copy(self, plan: TrainingCopyPlan) -> tuple[QualityMeasurements, FixtureEffectReadback]: ...
    def measure_environment(self, plan: EnvironmentABPlan) -> EnvironmentMeasurementBundle: ...
    def finish_speech_continuous(self, plan: SpeechContinuousPlan) -> SpeechContinuousReadback: ...


class DeterministicFixtureAudioRunner:
    """Scripted no-I/O runner for focused contract tests only."""

    fixture_only = True
    authority_created = False
    production_eligible = False

    def __init__(
        self,
        *,
        runner_build_sha256: str,
        generated_result: tuple[QualityMeasurements, FixtureEffectReadback] | Exception | None = None,
        training_result: tuple[QualityMeasurements, FixtureEffectReadback] | Exception | None = None,
        environment_result: EnvironmentMeasurementBundle | Exception | None = None,
        speech_result: SpeechContinuousReadback | Exception | None = None,
    ) -> None:
        self.runner_build_sha256 = _digest(runner_build_sha256, "runner_build_sha256")
        self.generated_result = generated_result
        self.training_result = training_result
        self.environment_result = environment_result
        self.speech_result = speech_result
        self.calls: list[tuple[OperationKind, str]] = []

    @staticmethod
    def _result(value: tuple[QualityMeasurements, FixtureEffectReadback] | Exception | None) -> tuple[QualityMeasurements, FixtureEffectReadback]:
        if isinstance(value, Exception):
            raise value
        if value is None:
            raise FinishingContractError("fixture result was not configured")
        return value

    def finish_generated(self, plan: GeneratedFinishingPlan) -> tuple[QualityMeasurements, FixtureEffectReadback]:
        self.calls.append((OperationKind.GENERATED_WAV_FINISH, plan.operation_id))
        return self._result(self.generated_result)

    def prepare_training_copy(self, plan: TrainingCopyPlan) -> tuple[QualityMeasurements, FixtureEffectReadback]:
        self.calls.append((OperationKind.TRAINING_COPY_QA, plan.operation_id))
        return self._result(self.training_result)

    def measure_environment(self, plan: EnvironmentABPlan) -> EnvironmentMeasurementBundle:
        self.calls.append((OperationKind.ENVIRONMENT_AB_QA, plan.operation_id))
        if isinstance(self.environment_result, Exception):
            raise self.environment_result
        if self.environment_result is None:
            raise FinishingContractError("fixture environment result was not configured")
        return self.environment_result

    def finish_speech_continuous(self, plan: SpeechContinuousPlan) -> SpeechContinuousReadback:
        self.calls.append((OperationKind.SPEECH_CONTINUOUS_TRAINING_FINISH, plan.operation_id))
        if isinstance(self.speech_result, Exception):
            raise self.speech_result
        if self.speech_result is None:
            raise FinishingContractError("fixture speech result was not configured")
        return self.speech_result


@dataclass(frozen=True, slots=True)
class AudioFinishingReceipt:
    receipt_type: str
    operation_kind: OperationKind
    operation_id: str
    project_id: str
    project_manifest_sha256: str
    installed_session_sha256: str
    operation_plan_sha256: str
    quick_clone_flow_sha256: str
    plan_sha256: str
    source_sha256: str
    source_identity_sha256: str
    terminal_source_receipt_sha256: str | None
    runner_build_sha256: str
    analyzer_profile_sha256: str
    engine_recipe_sha256: str | None
    consent_receipt_sha256: str | None
    review_receipt_sha256: str | None
    canonical_input_receipt_sha256: str | None
    transport_format_receipt_sha256: str | None
    capture_chain_receipt_sha256: str | None
    start_sample: int
    end_sample: int
    output_sha256: str | None
    output_identity_sha256: str | None
    output_format: AudioFormat | None
    output_sample_count: int | None
    exact_range_applied: bool
    readback_verified: bool
    directory_durable: bool
    measurements: QualityMeasurements
    state: QAState
    reason_codes: tuple[ReasonCode, ...]
    raw_source_preserved: bool
    fixture_only: bool = True
    authority_created: bool = False
    production_eligible: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation_kind", _enum(OperationKind, self.operation_kind, "operation_kind"))
        object.__setattr__(self, "state", _enum(QAState, self.state, "state"))
        if self.operation_kind not in {
            OperationKind.GENERATED_WAV_FINISH,
            OperationKind.TRAINING_COPY_QA,
        }:
            raise FinishingContractError("operation kind is invalid for audio finishing receipt")
        expected_type = TECHNICAL_QA_RECEIPT_TYPE if self.operation_kind is OperationKind.GENERATED_WAV_FINISH else TRAINING_COPY_RECEIPT_TYPE
        if self.receipt_type != expected_type:
            raise FinishingContractError("receipt type does not match operation")
        _id(self.operation_id, "operation_id")
        _id(self.project_id, "project_id")
        for value, name in (
            (self.project_manifest_sha256, "project_manifest_sha256"),
            (self.installed_session_sha256, "installed_session_sha256"),
            (self.operation_plan_sha256, "operation_plan_sha256"),
            (self.quick_clone_flow_sha256, "quick_clone_flow_sha256"),
            (self.plan_sha256, "plan_sha256"),
        ):
            _digest(value, name)
        _digest(self.source_sha256, "source_sha256")
        _digest(self.source_identity_sha256, "source_identity_sha256")
        _digest(self.runner_build_sha256, "runner_build_sha256")
        _digest(self.analyzer_profile_sha256, "analyzer_profile_sha256")
        if self.terminal_source_receipt_sha256 is not None:
            _digest(self.terminal_source_receipt_sha256, "terminal_source_receipt_sha256")
        if self.engine_recipe_sha256 is not None:
            _digest(self.engine_recipe_sha256, "engine_recipe_sha256")
        if self.consent_receipt_sha256 is not None:
            _digest(self.consent_receipt_sha256, "consent_receipt_sha256")
        if self.review_receipt_sha256 is not None:
            _digest(self.review_receipt_sha256, "review_receipt_sha256")
        for value, name in (
            (self.canonical_input_receipt_sha256, "canonical_input_receipt_sha256"),
            (self.transport_format_receipt_sha256, "transport_format_receipt_sha256"),
            (self.capture_chain_receipt_sha256, "capture_chain_receipt_sha256"),
        ):
            if value is not None:
                _digest(value, name)
        if not isinstance(self.start_sample, int) or isinstance(self.start_sample, bool) or self.start_sample < 0:
            raise FinishingContractError("start_sample must be a non-negative integer")
        if not isinstance(self.end_sample, int) or isinstance(self.end_sample, bool) or self.end_sample <= self.start_sample:
            raise FinishingContractError("receipt sample range is invalid")
        if type(self.measurements) is not QualityMeasurements:
            raise FinishingContractError("measurements type is invalid")
        if self.output_sha256 is not None:
            _digest(self.output_sha256, "output_sha256")
        if self.output_identity_sha256 is not None:
            _digest(self.output_identity_sha256, "output_identity_sha256")
        if self.output_format is not None and type(self.output_format) is not AudioFormat:
            raise FinishingContractError("output_format type is invalid")
        if self.output_sample_count is not None:
            _positive_int(self.output_sample_count, "output_sample_count", maximum=12 * 60 * 60 * SAMPLE_RATE_HZ)
        output_values = (self.output_sha256, self.output_identity_sha256, self.output_format, self.output_sample_count)
        if any(value is None for value in output_values) != all(value is None for value in output_values):
            raise FinishingContractError("output readback fields must be all present or all absent")
        for name in ("exact_range_applied", "readback_verified", "directory_durable"):
            if type(getattr(self, name)) is not bool:
                raise FinishingContractError(f"{name} must be boolean")
        if self.operation_kind is OperationKind.GENERATED_WAV_FINISH:
            if any(value is not None for value in (
                self.engine_recipe_sha256, self.consent_receipt_sha256,
                self.review_receipt_sha256, self.canonical_input_receipt_sha256,
                self.transport_format_receipt_sha256, self.capture_chain_receipt_sha256,
            )):
                raise FinishingContractError("generated receipt cannot contain training-only bindings")
        else:
            if any(value is None for value in (
                self.engine_recipe_sha256, self.terminal_source_receipt_sha256,
                self.consent_receipt_sha256, self.review_receipt_sha256,
                self.canonical_input_receipt_sha256,
                self.transport_format_receipt_sha256,
                self.capture_chain_receipt_sha256,
            )):
                raise FinishingContractError("training receipt bindings are incomplete")
        codes = tuple(sorted((_enum(ReasonCode, value, "reason_code") for value in self.reason_codes), key=lambda item: item.value))
        if len(set(codes)) != len(codes) or len(codes) > 16:
            raise FinishingContractError("reason codes must be unique and bounded")
        object.__setattr__(self, "reason_codes", codes)
        for name in ("raw_source_preserved", "fixture_only", "authority_created", "production_eligible"):
            if type(getattr(self, name)) is not bool:
                raise FinishingContractError(f"{name} must be boolean")
        if not self.raw_source_preserved:
            raise FinishingContractError("raw source preservation is mandatory")
        if (self.fixture_only, self.authority_created, self.production_eligible) != (True, False, False):
            raise FinishingContractError("fixture evidence cannot create Production authority")
        if self.state is QAState.PASS and codes:
            raise FinishingContractError("PASS cannot contain reason codes")
        if self.state is not QAState.PASS and not codes:
            raise FinishingContractError("non-PASS requires a reason code")
        if self.state is QAState.PASS:
            if any(value is None for value in output_values) or not all((self.exact_range_applied, self.readback_verified, self.directory_durable)):
                raise FinishingContractError("PASS requires complete durable output readback")
            if self.output_sample_count != self.end_sample - self.start_sample:
                raise FinishingContractError("PASS output does not match the exact sample range")
            if self.operation_kind is OperationKind.GENERATED_WAV_FINISH:
                if not _generated_measurements_pass(self.measurements):
                    raise FinishingContractError("generated PASS measurements are invalid")
            elif not _training_measurements_pass(self.measurements, self.end_sample - self.start_sample):
                raise FinishingContractError("training PASS measurements are invalid")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "contract_version": CONTRACT_VERSION,
            "receipt_type": self.receipt_type,
            "task_owner": TASK_OWNER,
            "operation_kind": self.operation_kind.value,
            "operation_id": self.operation_id,
            "project_id": self.project_id,
            "project_manifest_sha256": self.project_manifest_sha256,
            "installed_session_sha256": self.installed_session_sha256,
            "operation_plan_sha256": self.operation_plan_sha256,
            "quick_clone_flow_sha256": self.quick_clone_flow_sha256,
            "plan_sha256": self.plan_sha256,
            "source_sha256": self.source_sha256,
            "source_identity_sha256": self.source_identity_sha256,
            "terminal_source_receipt_sha256": self.terminal_source_receipt_sha256,
            "runner_build_sha256": self.runner_build_sha256,
            "analyzer_profile_sha256": self.analyzer_profile_sha256,
            "engine_recipe_sha256": self.engine_recipe_sha256,
            "consent_receipt_sha256": self.consent_receipt_sha256,
            "review_receipt_sha256": self.review_receipt_sha256,
            "canonical_input_receipt_sha256": self.canonical_input_receipt_sha256,
            "transport_format_receipt_sha256": self.transport_format_receipt_sha256,
            "capture_chain_receipt_sha256": self.capture_chain_receipt_sha256,
            "start_sample": self.start_sample,
            "end_sample": self.end_sample,
            "output_sha256": self.output_sha256,
            "output_identity_sha256": self.output_identity_sha256,
            "output_format": None if self.output_format is None else self.output_format.to_dict(),
            "output_sample_count": self.output_sample_count,
            "exact_range_applied": self.exact_range_applied,
            "readback_verified": self.readback_verified,
            "directory_durable": self.directory_durable,
            "measurements": self.measurements.to_dict(),
            "state": self.state.value,
            "reason_codes": [item.value for item in self.reason_codes],
            "raw_source_preserved": self.raw_source_preserved,
            "audio_body_persisted": False,
            "transcript_body_persisted": False,
            "host_absolute_path_persisted": False,
            "external_effect_count": 0,
            "dataset_adoption_started": False,
            "fixture_only": self.fixture_only,
            "authority_created": self.authority_created,
            "production_eligible": self.production_eligible,
        }
        body["receipt_sha256"] = _receipt_hash(body)
        return body


@dataclass(frozen=True, slots=True)
class SegmentAssessment:
    condition: CaptureCondition
    effort: VoiceEffort
    eligibility: SegmentEligibility
    reason_codes: tuple[ReasonCode, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "condition", _enum(CaptureCondition, self.condition, "condition"))
        object.__setattr__(self, "effort", _enum(VoiceEffort, self.effort, "effort"))
        object.__setattr__(self, "eligibility", _enum(SegmentEligibility, self.eligibility, "eligibility"))
        codes = tuple(sorted((_enum(ReasonCode, item, "reason_code") for item in self.reason_codes), key=lambda item: item.value))
        if len(codes) != len(set(codes)) or len(codes) > 12:
            raise FinishingContractError("segment reason codes are invalid")
        object.__setattr__(self, "reason_codes", codes)
        if self.eligibility is SegmentEligibility.TRAINING_ELIGIBLE and codes:
            raise FinishingContractError("eligible segment cannot contain reasons")
        if self.eligibility is not SegmentEligibility.TRAINING_ELIGIBLE and not codes:
            raise FinishingContractError("non-eligible segment requires reasons")

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition.value,
            "effort": self.effort.value,
            "eligibility": self.eligibility.value,
            "reason_codes": [item.value for item in self.reason_codes],
        }


@dataclass(frozen=True, slots=True)
class EnvironmentNoiseDelta:
    effort: VoiceEffort
    noise_floor_delta_dbfs: float
    low_band_delta_dbfs: float
    mid_band_delta_dbfs: float
    high_band_delta_dbfs: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "effort", _enum(VoiceEffort, self.effort, "effort"))
        for name in (
            "noise_floor_delta_dbfs", "low_band_delta_dbfs",
            "mid_band_delta_dbfs", "high_band_delta_dbfs",
        ):
            _finite(getattr(self, name), name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "effort": self.effort.value,
            "noise_floor_delta_dbfs": self.noise_floor_delta_dbfs,
            "low_band_delta_dbfs": self.low_band_delta_dbfs,
            "mid_band_delta_dbfs": self.mid_band_delta_dbfs,
            "high_band_delta_dbfs": self.high_band_delta_dbfs,
        }


@dataclass(frozen=True, slots=True)
class EnvironmentABReceipt:
    operation_id: str
    project_id: str
    project_manifest_sha256: str
    installed_session_sha256: str
    operation_plan_sha256: str
    plan_sha256: str
    runner_build_sha256: str
    analyzer_profile_sha256: str
    quality_policy_sha256: str
    off_capture_receipt_sha256: str
    on_capture_receipt_sha256: str
    measurement_bundle_sha256: str | None
    segment_assessments: tuple[SegmentAssessment, ...]
    denoise_assessments: tuple[SegmentAssessment, ...]
    noise_deltas: tuple[EnvironmentNoiseDelta, ...]
    comparison_state: QAState
    reason_codes: tuple[ReasonCode, ...]
    recommended_condition: None = None
    fixture_only: bool = True
    authority_created: bool = False
    production_eligible: bool = False

    def __post_init__(self) -> None:
        _id(self.operation_id, "operation_id")
        _id(self.project_id, "project_id")
        for value, name in (
            (self.project_manifest_sha256, "project_manifest_sha256"),
            (self.installed_session_sha256, "installed_session_sha256"),
            (self.operation_plan_sha256, "operation_plan_sha256"),
            (self.plan_sha256, "plan_sha256"),
            (self.runner_build_sha256, "runner_build_sha256"),
            (self.analyzer_profile_sha256, "analyzer_profile_sha256"),
            (self.quality_policy_sha256, "quality_policy_sha256"),
            (self.off_capture_receipt_sha256, "off_capture_receipt_sha256"),
            (self.on_capture_receipt_sha256, "on_capture_receipt_sha256"),
        ):
            _digest(value, name)
        if self.measurement_bundle_sha256 is not None:
            _digest(self.measurement_bundle_sha256, "measurement_bundle_sha256")
        object.__setattr__(self, "comparison_state", _enum(QAState, self.comparison_state, "comparison_state"))
        codes = tuple(sorted((_enum(ReasonCode, item, "reason_code") for item in self.reason_codes), key=lambda item: item.value))
        if len(codes) != len(set(codes)) or len(codes) > 8:
            raise FinishingContractError("comparison reason codes are invalid")
        object.__setattr__(self, "reason_codes", codes)
        if self.recommended_condition is not None:
            raise FinishingContractError("environment condition cannot be an automatic recommendation")
        for name in ("fixture_only", "authority_created", "production_eligible"):
            if type(getattr(self, name)) is not bool:
                raise FinishingContractError(f"{name} must be boolean")
        if (self.fixture_only, self.authority_created, self.production_eligible) != (True, False, False):
            raise FinishingContractError("fixture comparison cannot create Production authority")
        if self.comparison_state is QAState.PASS:
            if codes or self.measurement_bundle_sha256 is None:
                raise FinishingContractError("PASS comparison requires a bound measurement bundle")
            expected = tuple((condition, effort) for condition in CaptureCondition for effort in VoiceEffort)
            if (
                len(self.segment_assessments) != 6
                or any(type(item) is not SegmentAssessment for item in self.segment_assessments)
                or tuple((item.condition, item.effort) for item in self.segment_assessments) != expected
            ):
                raise FinishingContractError("PASS comparison segment assessments are incomplete")
            if (
                len(self.denoise_assessments) != 6
                or any(type(item) is not SegmentAssessment for item in self.denoise_assessments)
                or tuple((item.condition, item.effort) for item in self.denoise_assessments) != expected
            ):
                raise FinishingContractError("PASS comparison denoise assessments are incomplete")
            if (
                len(self.noise_deltas) != 3
                or any(type(item) is not EnvironmentNoiseDelta for item in self.noise_deltas)
                or tuple(item.effort for item in self.noise_deltas) != tuple(VoiceEffort)
            ):
                raise FinishingContractError("PASS comparison noise deltas are incomplete")
        elif not codes:
            raise FinishingContractError("non-PASS comparison requires a reason")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "contract_version": CONTRACT_VERSION,
            "receipt_type": ENVIRONMENT_AB_RECEIPT_TYPE,
            "task_owner": TASK_OWNER,
            "operation_kind": OperationKind.ENVIRONMENT_AB_QA.value,
            "operation_id": self.operation_id,
            "project_id": self.project_id,
            "project_manifest_sha256": self.project_manifest_sha256,
            "installed_session_sha256": self.installed_session_sha256,
            "operation_plan_sha256": self.operation_plan_sha256,
            "plan_sha256": self.plan_sha256,
            "runner_build_sha256": self.runner_build_sha256,
            "analyzer_profile_sha256": self.analyzer_profile_sha256,
            "quality_policy_sha256": self.quality_policy_sha256,
            "off_capture_receipt_sha256": self.off_capture_receipt_sha256,
            "on_capture_receipt_sha256": self.on_capture_receipt_sha256,
            "measurement_bundle_sha256": self.measurement_bundle_sha256,
            "segment_assessments": [item.to_dict() for item in self.segment_assessments],
            "denoise_assessments": [item.to_dict() for item in self.denoise_assessments],
            "noise_deltas": [item.to_dict() for item in self.noise_deltas],
            "comparison_state": self.comparison_state.value,
            "reason_codes": [item.value for item in self.reason_codes],
            "recommended_condition": None,
            "measurement_unit": "dBFS",
            "dba_or_spl_claimed": False,
            "audio_body_persisted": False,
            "host_absolute_path_persisted": False,
            "external_effect_count": 0,
            "dataset_adoption_started": False,
            "fixture_only": self.fixture_only,
            "authority_created": self.authority_created,
            "production_eligible": self.production_eligible,
        }
        body["receipt_sha256"] = _receipt_hash(body)
        return body


@dataclass(frozen=True, slots=True)
class SpeechContinuousReceipt:
    operation_id: str
    project_id: str
    project_manifest_sha256: str
    installed_session_sha256: str
    operation_plan_sha256: str
    plan_sha256: str
    source_sha256: str
    source_identity_sha256: str
    quality_measurements_sha256: str
    format_policy_receipt_sha256: str
    continuity_policy_receipt_sha256: str
    retained_ranges: tuple[SampleRange, ...]
    removed_ranges: tuple[SampleRange, ...]
    removed_sample_count: int
    fade_samples: int
    boundary_mode: BoundaryMode
    boundary_count: int
    crossfade_overlap_samples: int
    boundary_evidence_sha256s: tuple[str, ...]
    output_sha256: str | None
    output_identity_sha256: str | None
    output_format: AudioFormat | None
    output_sample_count: int | None
    task046_lineage_candidate_sha256: str | None
    range_map_verified: bool
    zero_cross_or_crossfade_verified: bool
    speech_attack_preserved: bool
    speech_tail_preserved: bool
    partial_output_published: bool
    readback_verified: bool
    directory_durable: bool
    state: QAState
    reason_codes: tuple[ReasonCode, ...]
    raw_source_preserved: bool
    fixture_only: bool = True
    authority_created: bool = False
    production_eligible: bool = False

    def __post_init__(self) -> None:
        _id(self.operation_id, "operation_id")
        _id(self.project_id, "project_id")
        for value, name in (
            (self.project_manifest_sha256, "project_manifest_sha256"),
            (self.installed_session_sha256, "installed_session_sha256"),
            (self.operation_plan_sha256, "operation_plan_sha256"),
            (self.plan_sha256, "plan_sha256"),
            (self.source_sha256, "source_sha256"),
            (self.source_identity_sha256, "source_identity_sha256"),
            (self.quality_measurements_sha256, "quality_measurements_sha256"),
            (self.format_policy_receipt_sha256, "format_policy_receipt_sha256"),
            (self.continuity_policy_receipt_sha256, "continuity_policy_receipt_sha256"),
        ):
            _digest(value, name)
        if not isinstance(self.removed_sample_count, int) or isinstance(self.removed_sample_count, bool) or self.removed_sample_count < 0:
            raise FinishingContractError("removed_sample_count is invalid")
        if (
            any(type(item) is not SampleRange for item in self.retained_ranges)
            or any(type(item) is not SampleRange for item in self.removed_ranges)
            or self.removed_sample_count
            != sum(item.sample_count for item in self.removed_ranges)
        ):
            raise FinishingContractError("speech receipt range map is invalid")
        range_cursor = 0
        for item in sorted((*self.retained_ranges, *self.removed_ranges)):
            if item.start_sample != range_cursor:
                raise FinishingContractError("speech receipt range map is invalid")
            range_cursor = item.end_sample
        _positive_int(self.fade_samples, "fade_samples", maximum=SAMPLE_RATE_HZ)
        if self.fade_samples != BOUNDARY_CROSSFADE_SAMPLES:
            raise FinishingContractError("speech receipt fade sample count is fixed")
        object.__setattr__(self, "boundary_mode", _enum(BoundaryMode, self.boundary_mode, "boundary_mode"))
        expected_boundary_count = max(0, len(self.retained_ranges) - 1)
        if (
            not isinstance(self.boundary_count, int)
            or isinstance(self.boundary_count, bool)
            or self.boundary_count < 0
        ):
            raise FinishingContractError("speech receipt boundary count is invalid")
        if (
            not isinstance(self.crossfade_overlap_samples, int)
            or isinstance(self.crossfade_overlap_samples, bool)
            or self.crossfade_overlap_samples < 0
        ):
            raise FinishingContractError("speech receipt crossfade accounting is invalid")
        if self.boundary_mode is not BoundaryMode.EQUAL_POWER_CROSSFADE:
            raise FinishingContractError("speech receipt boundary mode is invalid")
        if len(self.boundary_evidence_sha256s) != expected_boundary_count:
            raise FinishingContractError("speech receipt boundary evidence is incomplete")
        for item in self.boundary_evidence_sha256s:
            _digest(item, "boundary_evidence_sha256")
        object.__setattr__(self, "state", _enum(QAState, self.state, "state"))
        for name in (
            "range_map_verified", "zero_cross_or_crossfade_verified",
            "speech_attack_preserved", "speech_tail_preserved",
            "partial_output_published", "readback_verified", "directory_durable",
            "raw_source_preserved",
        ):
            if type(getattr(self, name)) is not bool:
                raise FinishingContractError(f"{name} must be boolean")
        codes = tuple(sorted((_enum(ReasonCode, item, "reason_code") for item in self.reason_codes), key=lambda item: item.value))
        if len(codes) != len(set(codes)) or len(codes) > 8:
            raise FinishingContractError("speech receipt reason codes are invalid")
        object.__setattr__(self, "reason_codes", codes)
        output = (self.output_sha256, self.output_identity_sha256, self.output_format, self.output_sample_count)
        if any(value is None for value in output) != all(value is None for value in output):
            raise FinishingContractError("speech output fields must be all present or all absent")
        if self.output_sha256 is not None:
            _digest(self.output_sha256, "output_sha256")
            _digest(self.output_identity_sha256, "output_identity_sha256")
            if type(self.output_format) is not AudioFormat:
                raise FinishingContractError("output_format type is invalid")
            _positive_int(self.output_sample_count, "output_sample_count")
        if self.task046_lineage_candidate_sha256 is not None:
            _digest(
                self.task046_lineage_candidate_sha256,
                "task046_lineage_candidate_sha256",
            )
        for name in ("fixture_only", "authority_created", "production_eligible"):
            if type(getattr(self, name)) is not bool:
                raise FinishingContractError(f"{name} must be boolean")
        if not self.raw_source_preserved:
            raise FinishingContractError("raw source preservation is mandatory")
        if (self.fixture_only, self.authority_created, self.production_eligible) != (True, False, False):
            raise FinishingContractError("fixture speech receipt cannot create Production authority")
        if self.state is QAState.PASS:
            if (
                codes
                or any(value is None for value in output)
                or self.task046_lineage_candidate_sha256 is None
                or self.boundary_count != expected_boundary_count
                or self.crossfade_overlap_samples
                != expected_boundary_count * self.fade_samples
            ):
                raise FinishingContractError("speech PASS requires complete output")
            if self.output_sample_count != (
                sum(item.sample_count for item in self.retained_ranges)
                - self.crossfade_overlap_samples
            ):
                raise FinishingContractError("speech PASS output range map is inconsistent")
            if not all((
                self.range_map_verified,
                self.zero_cross_or_crossfade_verified,
                self.speech_attack_preserved,
                self.speech_tail_preserved,
                self.readback_verified,
                self.directory_durable,
            )) or self.partial_output_published:
                raise FinishingContractError("speech PASS readback flags are invalid")
        else:
            if not codes:
                raise FinishingContractError("non-PASS speech receipt requires a reason")
            if self.task046_lineage_candidate_sha256 is not None:
                raise FinishingContractError("failed speech receipt cannot emit Dataset lineage")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "contract_version": CONTRACT_VERSION,
            "receipt_type": SPEECH_CONTINUOUS_RECEIPT_TYPE,
            "task_owner": TASK_OWNER,
            "operation_kind": OperationKind.SPEECH_CONTINUOUS_TRAINING_FINISH.value,
            "operation_id": self.operation_id,
            "project_id": self.project_id,
            "project_manifest_sha256": self.project_manifest_sha256,
            "installed_session_sha256": self.installed_session_sha256,
            "operation_plan_sha256": self.operation_plan_sha256,
            "plan_sha256": self.plan_sha256,
            "source_sha256": self.source_sha256,
            "source_identity_sha256": self.source_identity_sha256,
            "quality_measurements_sha256": self.quality_measurements_sha256,
            "format_policy_receipt_sha256": self.format_policy_receipt_sha256,
            "continuity_policy_receipt_sha256": self.continuity_policy_receipt_sha256,
            "retained_ranges": [item.to_dict() for item in self.retained_ranges],
            "removed_ranges": [item.to_dict() for item in self.removed_ranges],
            "removed_sample_count": self.removed_sample_count,
            "fade_samples": self.fade_samples,
            "boundary_mode": self.boundary_mode.value,
            "boundary_count": self.boundary_count,
            "crossfade_overlap_samples": self.crossfade_overlap_samples,
            "boundary_evidence_sha256s": list(self.boundary_evidence_sha256s),
            "zero_gap_compression": False,
            "output_sha256": self.output_sha256,
            "output_identity_sha256": self.output_identity_sha256,
            "output_format": None if self.output_format is None else self.output_format.to_dict(),
            "output_sample_count": self.output_sample_count,
            "input_sample_count": sum(item.sample_count for item in self.retained_ranges)
            + self.removed_sample_count,
            "input_pcm_payload_bytes": (
                sum(item.sample_count for item in self.retained_ranges)
                + self.removed_sample_count
            ) * CHANNELS * PCM_BYTES_PER_SAMPLE,
            "output_pcm_payload_bytes": None
            if self.output_sample_count is None
            else self.output_sample_count * CHANNELS * PCM_BYTES_PER_SAMPLE,
            "size_reduction_bytes": (
                self.removed_sample_count + self.crossfade_overlap_samples
            ) * CHANNELS * PCM_BYTES_PER_SAMPLE,
            "size_optimization_mode": "LOSSLESS_SAMPLE_RANGE_REMOVAL_PLUS_BOUNDARY_CROSSFADE",
            "canonical_wav_container": "RIFF_WAVE_PCM_S24LE",
            "task046_lineage_candidate_sha256": self.task046_lineage_candidate_sha256,
            "task046_lineage_authority_created": False,
            "range_map_verified": self.range_map_verified,
            "zero_cross_or_crossfade_verified": self.zero_cross_or_crossfade_verified,
            "speech_attack_preserved": self.speech_attack_preserved,
            "speech_tail_preserved": self.speech_tail_preserved,
            "readback_verified": self.readback_verified,
            "directory_durable": self.directory_durable,
            "state": self.state.value,
            "reason_codes": [item.value for item in self.reason_codes],
            "raw_source_preserved": self.raw_source_preserved,
            "partial_output_published": self.partial_output_published,
            "lossy_codec_used": False,
            "audio_body_persisted": False,
            "host_absolute_path_persisted": False,
            "external_effect_count": 0,
            "dataset_adoption_started": False,
            "fixture_only": self.fixture_only,
            "authority_created": self.authority_created,
            "production_eligible": self.production_eligible,
        }
        body["receipt_sha256"] = _receipt_hash(body)
        return body


def _assess_environment_segment(item: EnvironmentSegmentMeasurement) -> SegmentAssessment:
    reject: set[ReasonCode] = set()
    review: set[ReasonCode] = set()
    if item.nonfinite_sample_count is None:
        review.add(ReasonCode.AB_MEASUREMENT_NOT_CURRENT)
    elif item.nonfinite_sample_count > 0:
        reject.add(ReasonCode.NONFINITE_SAMPLES)
    if item.clipped_sample_count is None:
        review.add(ReasonCode.CLIPPING_UNKNOWN)
    elif item.clipped_sample_count > 0:
        reject.add(ReasonCode.CLIPPING_DETECTED)
    if item.dropout_count is None:
        review.add(ReasonCode.DROPOUT_UNKNOWN)
    elif item.dropout_count > 0:
        reject.add(ReasonCode.DROPOUT_DETECTED)
    if item.dc_offset_abs is None:
        review.add(ReasonCode.DC_OFFSET_UNKNOWN)
    elif item.dc_offset_abs > 0.01:
        reject.add(ReasonCode.DC_OFFSET_OUT_OF_POLICY)
    if item.room_tone_noise_floor_dbfs is None:
        review.add(ReasonCode.NOISE_FLOOR_UNKNOWN)
    if item.speech_rms_dbfs is None or item.speech_peak_dbfs is None:
        review.add(ReasonCode.SPEECH_LEVEL_UNKNOWN)
    if item.noise_profile is None:
        review.add(ReasonCode.NOISE_PROFILE_UNKNOWN)
    if item.snr_db is None:
        review.add(ReasonCode.SNR_UNKNOWN)
    elif item.snr_db < 15.0:
        reject.add(ReasonCode.SNR_BELOW_POLICY)
    elif item.snr_db < 20.0 or item.snr_approximate:
        review.add(ReasonCode.SNR_BELOW_POLICY)
    if item.speech_ratio is None:
        review.add(ReasonCode.SPEECH_RATIO_UNKNOWN)
    elif item.speech_ratio < 0.5:
        reject.add(ReasonCode.SPEECH_RATIO_OUT_OF_POLICY)
    if reject:
        return SegmentAssessment(item.condition, item.effort, SegmentEligibility.REJECT, tuple(reject | review))
    if review:
        return SegmentAssessment(item.condition, item.effort, SegmentEligibility.REVIEW, tuple(review))
    return SegmentAssessment(item.condition, item.effort, SegmentEligibility.TRAINING_ELIGIBLE, ())


def _assess_denoise(item: DenoisePairMeasurement) -> SegmentAssessment:
    reject: set[ReasonCode] = set()
    review: set[ReasonCode] = set()
    if item.input_source_sha256 != item.denoised_input_source_sha256:
        reject.add(ReasonCode.DENOISE_INPUT_MISMATCH)
    if item.overprocessing_state is ClassificationState.DETECTED:
        reject.add(ReasonCode.DENOISE_DISTORTION_RISK)
    elif item.overprocessing_state is ClassificationState.UNKNOWN:
        review.add(ReasonCode.DENOISE_RISK_UNKNOWN)
    if item.voice_distortion_ratio is None:
        review.add(ReasonCode.DENOISE_RISK_UNKNOWN)
    elif item.voice_distortion_ratio > 0.1:
        reject.add(ReasonCode.DENOISE_DISTORTION_RISK)
    if item.noise_reduction_db is None or item.noise_reduction_db < 1.0:
        review.add(ReasonCode.DENOISE_IMPROVEMENT_INSUFFICIENT)
    if item.raw_artifact_sha256 == item.denoised_artifact_sha256:
        review.add(ReasonCode.DENOISE_IMPROVEMENT_INSUFFICIENT)
    if reject:
        return SegmentAssessment(item.condition, item.effort, SegmentEligibility.REJECT, tuple(reject | review))
    if review:
        return SegmentAssessment(item.condition, item.effort, SegmentEligibility.REVIEW, tuple(review))
    return SegmentAssessment(item.condition, item.effort, SegmentEligibility.TRAINING_ELIGIBLE, ())


def _noise_deltas(bundle: EnvironmentMeasurementBundle) -> tuple[EnvironmentNoiseDelta, ...]:
    by_key = {(item.condition, item.effort): item for item in bundle.segments}
    values: list[EnvironmentNoiseDelta] = []
    for effort in VoiceEffort:
        off = by_key[(CaptureCondition.AIR_CONDITIONER_OFF, effort)]
        on = by_key[(CaptureCondition.AIR_CONDITIONER_ON, effort)]
        if off.room_tone_noise_floor_dbfs is None or on.room_tone_noise_floor_dbfs is None:
            raise FinishingContractError("noise floor delta cannot be calculated")
        if off.noise_profile is None or on.noise_profile is None:
            raise FinishingContractError("noise profile delta cannot be calculated")
        values.append(EnvironmentNoiseDelta(
            effort=effort,
            noise_floor_delta_dbfs=on.room_tone_noise_floor_dbfs - off.room_tone_noise_floor_dbfs,
            low_band_delta_dbfs=on.noise_profile.low_dbfs - off.noise_profile.low_dbfs,
            mid_band_delta_dbfs=on.noise_profile.mid_dbfs - off.noise_profile.mid_dbfs,
            high_band_delta_dbfs=on.noise_profile.high_dbfs - off.noise_profile.high_dbfs,
        ))
    return tuple(values)


def _bundle_sha256(bundle: EnvironmentMeasurementBundle) -> str:
    return _receipt_hash({
        "segments": [item.to_dict() for item in bundle.segments],
        "denoise_pairs": [item.to_dict() for item in bundle.denoise_pairs],
    })


class FixtureVoiceQualityAudioFinishingService:
    """One-use fixture orchestrator; all entry attempts burn operation IDs."""

    def __init__(self, runner: FixtureAudioRunner) -> None:
        if type(getattr(runner, "fixture_only", None)) is not bool or not runner.fixture_only:
            raise FinishingContractError("only a fixture runner is admitted")
        if (
            type(getattr(runner, "authority_created", None)) is not bool
            or type(getattr(runner, "production_eligible", None)) is not bool
        ):
            raise FinishingContractError("runner authority flags are invalid")
        if getattr(runner, "authority_created", None) is not False or getattr(runner, "production_eligible", None) is not False:
            raise FinishingContractError("runner authority flags are invalid")
        _digest(runner.runner_build_sha256, "runner_build_sha256")
        self._runner = runner
        self._lock = threading.Lock()
        self._consumed: set[str] = set()

    def _enter(self, kind: OperationKind, operation_id: str) -> None:
        key = _id(operation_id, "operation_id")
        with self._lock:
            if key in self._consumed:
                raise OperationAlreadyConsumedError("operation has already been consumed")
            self._consumed.add(key)

    @staticmethod
    def _source_reasons(source: SourceSnapshot, *, require_terminal: bool) -> set[ReasonCode]:
        reasons: set[ReasonCode] = set()
        if require_terminal and (
            source.terminal_receipt_sha256 is None
            or source.terminal_receipt_owner != "TASK-047"
            or source.terminal_receipt_type != TASK047_TERMINAL_RECEIPT_TYPE
            or not source.terminal_receipt_current
        ):
            reasons.add(ReasonCode.SOURCE_RECEIPT_MISSING)
        if not source.write_closed_verified:
            reasons.add(ReasonCode.SOURCE_STILL_WRITING)
        if not source.read_current or not source.ancestor_current:
            reasons.add(ReasonCode.SOURCE_CURRENTNESS_UNKNOWN)
        if not source.identity_current:
            reasons.add(ReasonCode.SOURCE_IDENTITY_CHANGED)
        if not source.regular_file or not source.single_link or not source.no_reparse:
            reasons.add(ReasonCode.SOURCE_LINK_REJECTED)
        if not source.wav_complete:
            reasons.add(ReasonCode.WAV_INVALID_OR_INCOMPLETE)
        return reasons

    @staticmethod
    def _generated_reasons(measurements: QualityMeasurements, readback: FixtureEffectReadback) -> set[ReasonCode]:
        reasons: set[ReasonCode] = set()
        if measurements.clipped_sample_count is None:
            reasons.add(ReasonCode.CLIPPING_UNKNOWN)
        elif measurements.clipped_sample_count > 0:
            reasons.add(ReasonCode.CLIPPING_DETECTED)
        if measurements.integrated_lufs is None:
            reasons.add(ReasonCode.LOUDNESS_UNKNOWN)
        elif abs(measurements.integrated_lufs - (-16.0)) > 1.0:
            reasons.add(ReasonCode.LOUDNESS_OUT_OF_POLICY)
        if measurements.true_peak_dbtp is None:
            reasons.add(ReasonCode.TRUE_PEAK_UNKNOWN)
        elif measurements.true_peak_dbtp > -1.0:
            reasons.add(ReasonCode.TRUE_PEAK_OUT_OF_POLICY)
        if measurements.loudness_range_lu is None:
            reasons.add(ReasonCode.LOUDNESS_RANGE_UNKNOWN)
        elif not 0.0 <= measurements.loudness_range_lu <= 11.0:
            reasons.add(ReasonCode.LOUDNESS_RANGE_OUT_OF_POLICY)
        if measurements.silence_ratio is None:
            reasons.add(ReasonCode.SILENCE_UNKNOWN)
        elif measurements.silence_ratio > 0.35:
            reasons.add(ReasonCode.SILENCE_EXCESSIVE)
        if not all((readback.exact_range_applied, readback.readback_verified, readback.directory_durable, readback.raw_source_preserved)):
            reasons.add(ReasonCode.GENERATED_READBACK_MISMATCH)
        return reasons

    @staticmethod
    def _training_reasons(
        measurements: QualityMeasurements,
        readback: FixtureEffectReadback,
        selected_sample_count: int,
    ) -> set[ReasonCode]:
        reasons: set[ReasonCode] = set()
        if measurements.clipped_sample_count is None:
            reasons.add(ReasonCode.CLIPPING_UNKNOWN)
        elif measurements.clipped_sample_count > 0:
            reasons.add(ReasonCode.CLIPPING_DETECTED)
        if measurements.snr_db is None:
            reasons.add(ReasonCode.SNR_UNKNOWN)
        elif measurements.snr_db < 20.0:
            reasons.add(ReasonCode.SNR_BELOW_POLICY)
        if measurements.silence_ratio is None:
            reasons.add(ReasonCode.SILENCE_UNKNOWN)
        elif measurements.silence_ratio > 0.35:
            reasons.add(ReasonCode.SILENCE_EXCESSIVE)
        if measurements.speech_duration_seconds is None:
            reasons.add(ReasonCode.SPEECH_DURATION_UNKNOWN)
        elif measurements.speech_duration_seconds < 1.0:
            reasons.add(ReasonCode.SPEECH_TOO_SHORT)
        elif measurements.speech_duration_seconds > selected_sample_count / SAMPLE_RATE_HZ:
            reasons.add(ReasonCode.SPEECH_DURATION_OUT_OF_RANGE)
        if measurements.speech_ratio is None:
            reasons.add(ReasonCode.SPEECH_RATIO_UNKNOWN)
        elif measurements.speech_ratio < 0.5:
            reasons.add(ReasonCode.SPEECH_RATIO_OUT_OF_POLICY)
        if measurements.dropout_count is None:
            reasons.add(ReasonCode.DROPOUT_UNKNOWN)
        elif measurements.dropout_count > 0:
            reasons.add(ReasonCode.DROPOUT_DETECTED)
        if measurements.dc_offset_abs is None:
            reasons.add(ReasonCode.DC_OFFSET_UNKNOWN)
        elif measurements.dc_offset_abs > 0.01:
            reasons.add(ReasonCode.DC_OFFSET_OUT_OF_POLICY)
        if measurements.other_speaker_state is ClassificationState.UNKNOWN:
            reasons.add(ReasonCode.OTHER_SPEAKER_UNVERIFIED)
        elif measurements.other_speaker_state is ClassificationState.DETECTED:
            reasons.add(ReasonCode.OTHER_SPEAKER_DETECTED)
        if measurements.bgm_state is ClassificationState.UNKNOWN:
            reasons.add(ReasonCode.BGM_CLASSIFICATION_UNKNOWN)
        elif measurements.bgm_state is ClassificationState.DETECTED:
            reasons.add(ReasonCode.BGM_EXCESSIVE)
        if not all((readback.exact_range_applied, readback.readback_verified, readback.directory_durable, readback.raw_source_preserved)):
            reasons.add(ReasonCode.COPY_READBACK_MISMATCH)
        return reasons

    @staticmethod
    def _state(reasons: set[ReasonCode]) -> QAState:
        unknown = {
            ReasonCode.SOURCE_RECEIPT_MISSING,
            ReasonCode.SOURCE_STILL_WRITING,
            ReasonCode.SOURCE_CURRENTNESS_UNKNOWN,
            ReasonCode.SNR_UNKNOWN,
            ReasonCode.CLIPPING_UNKNOWN,
            ReasonCode.LOUDNESS_UNKNOWN,
            ReasonCode.TRUE_PEAK_UNKNOWN,
            ReasonCode.LOUDNESS_RANGE_UNKNOWN,
            ReasonCode.SILENCE_UNKNOWN,
            ReasonCode.SPEECH_DURATION_UNKNOWN,
            ReasonCode.SPEECH_RATIO_UNKNOWN,
            ReasonCode.DROPOUT_UNKNOWN,
            ReasonCode.DC_OFFSET_UNKNOWN,
            ReasonCode.OTHER_SPEAKER_UNVERIFIED,
            ReasonCode.BGM_CLASSIFICATION_UNKNOWN,
        }
        if not reasons:
            return QAState.PASS
        return QAState.UNKNOWN if reasons <= unknown else QAState.FAIL

    def finish_generated(self, plan: GeneratedFinishingPlan) -> AudioFinishingReceipt:
        if type(plan) is not GeneratedFinishingPlan:
            raise FinishingContractError("generated plan type is invalid")
        self._enter(OperationKind.GENERATED_WAV_FINISH, plan.operation_id)
        if plan.runner_build_sha256 != self._runner.runner_build_sha256:
            raise FinishingContractError("runner build does not match plan")
        source_reasons = self._source_reasons(plan.source, require_terminal=False)
        if source_reasons:
            return self._receipt(plan, _unknown_measurements(), None, source_reasons)
        try:
            measurements, readback = self._runner.finish_generated(plan)
        except Exception:
            raise FinishingContractError("fixture generated finishing failed") from None
        if type(measurements) is not QualityMeasurements or type(readback) is not FixtureEffectReadback:
            raise FinishingContractError("fixture generated result type is invalid")
        reasons = self._generated_reasons(measurements, readback)
        if readback.output_format != plan.output_format:
            reasons.add(ReasonCode.GENERATED_READBACK_MISMATCH)
        if readback.output_sample_count != plan.end_sample - plan.start_sample:
            reasons.add(ReasonCode.GENERATED_READBACK_MISMATCH)
        return self._receipt(plan, measurements, readback, reasons)

    def prepare_training_copy(self, plan: TrainingCopyPlan) -> AudioFinishingReceipt:
        if type(plan) is not TrainingCopyPlan:
            raise FinishingContractError("training plan type is invalid")
        self._enter(OperationKind.TRAINING_COPY_QA, plan.operation_id)
        if plan.runner_build_sha256 != self._runner.runner_build_sha256:
            raise FinishingContractError("runner build does not match plan")
        source_reasons = self._source_reasons(plan.source, require_terminal=True)
        if source_reasons:
            return self._receipt(plan, _unknown_measurements(), None, source_reasons)
        try:
            measurements, readback = self._runner.prepare_training_copy(plan)
        except Exception:
            raise FinishingContractError("fixture training copy failed") from None
        if type(measurements) is not QualityMeasurements or type(readback) is not FixtureEffectReadback:
            raise FinishingContractError("fixture training result type is invalid")
        reasons = self._training_reasons(measurements, readback, plan.end_sample - plan.start_sample)
        if readback.output_format != plan.output_format or readback.output_sample_count != plan.end_sample - plan.start_sample:
            reasons.add(ReasonCode.TRAINING_FORMAT_MISMATCH)
        return self._receipt(plan, measurements, readback, reasons)

    def compare_environment(self, plan: EnvironmentABPlan) -> EnvironmentABReceipt:
        if type(plan) is not EnvironmentABPlan:
            raise FinishingContractError("environment A/B plan type is invalid")
        self._enter(OperationKind.ENVIRONMENT_AB_QA, plan.operation_id)
        if plan.runner_build_sha256 != self._runner.runner_build_sha256:
            raise FinishingContractError("runner build does not match plan")
        if not plan.off_capture.secure_and_current or not plan.on_capture.secure_and_current:
            return self._environment_receipt(plan, None, {ReasonCode.AB_CAPTURE_NOT_CURRENT})
        if not plan.comparable:
            return self._environment_receipt(plan, None, {ReasonCode.AB_CHAIN_MISMATCH})
        try:
            bundle = self._runner.measure_environment(plan)
        except Exception:
            raise FinishingContractError("fixture environment measurement failed") from None
        if type(bundle) is not EnvironmentMeasurementBundle:
            raise FinishingContractError("fixture environment result type is invalid")
        segments = {(item.condition, item.effort): item for item in bundle.segments}
        captures = {
            CaptureCondition.AIR_CONDITIONER_OFF: plan.off_capture,
            CaptureCondition.AIR_CONDITIONER_ON: plan.on_capture,
        }
        invalid = any(
            not item.current
            or item.source_sha256 != captures[item.condition].source_sha256
            or item.source_identity_sha256 != captures[item.condition].source_identity_sha256
            for item in bundle.segments
        )
        invalid = invalid or any(
            not item.current
            or item.input_source_sha256 != segments[(item.condition, item.effort)].source_sha256
            or item.denoised_input_source_sha256 != item.input_source_sha256
            or item.input_source_identity_sha256
            != segments[(item.condition, item.effort)].source_identity_sha256
            or item.denoised_input_source_identity_sha256
            != item.input_source_identity_sha256
            for item in bundle.denoise_pairs
        )
        if invalid:
            return self._environment_receipt(plan, None, {ReasonCode.AB_MEASUREMENT_NOT_CURRENT})
        try:
            _noise_deltas(bundle)
        except FinishingContractError:
            return self._environment_receipt(plan, None, {ReasonCode.AB_MEASUREMENT_SET_INVALID})
        return self._environment_receipt(plan, bundle, set())

    def finish_speech_continuous(self, plan: SpeechContinuousPlan) -> SpeechContinuousReceipt:
        if type(plan) is not SpeechContinuousPlan:
            raise FinishingContractError("speech-continuous plan type is invalid")
        self._enter(OperationKind.SPEECH_CONTINUOUS_TRAINING_FINISH, plan.operation_id)
        if plan.runner_build_sha256 != self._runner.runner_build_sha256:
            raise FinishingContractError("runner build does not match plan")
        try:
            readback = self._runner.finish_speech_continuous(plan)
        except Exception:
            raise FinishingContractError("fixture speech-continuous finishing failed") from None
        if type(readback) is not SpeechContinuousReadback:
            raise FinishingContractError("fixture speech-continuous result type is invalid")
        reasons: set[ReasonCode] = set()
        if (
            readback.output_format != plan.format_policy.output_format
            or readback.output_sample_count != plan.output_sample_count
            or readback.boundary_mode is not plan.boundary_mode
            or readback.boundary_count != plan.boundary_count
            or readback.crossfade_overlap_samples != plan.crossfade_overlap_samples
            or len(readback.boundary_evidence_sha256s) != plan.boundary_count
            or not readback.range_map_verified
            or not readback.readback_verified
            or not readback.directory_durable
            or readback.partial_output_published
        ):
            reasons.add(ReasonCode.COPY_READBACK_MISMATCH)
        if not readback.zero_cross_or_crossfade_verified:
            reasons.add(ReasonCode.SPEECH_BOUNDARY_UNVERIFIED)
        if not readback.speech_attack_preserved or not readback.speech_tail_preserved:
            reasons.add(ReasonCode.SPEECH_ATTACK_OR_TAIL_DAMAGED)
        if not readback.raw_source_preserved:
            reasons.add(ReasonCode.COPY_READBACK_MISMATCH)
        lineage_candidate_sha256 = (
            None
            if reasons
            else _task046_lineage_candidate_sha256(plan, readback)
        )
        return SpeechContinuousReceipt(
            operation_id=plan.operation_id,
            project_id=plan.project_id,
            project_manifest_sha256=plan.project_manifest_sha256,
            installed_session_sha256=plan.installed_session_sha256,
            operation_plan_sha256=plan.operation_plan_sha256,
            plan_sha256=_speech_plan_sha256(plan),
            source_sha256=plan.source.source_sha256,
            source_identity_sha256=plan.source.source_identity_sha256,
            quality_measurements_sha256=plan.quality_measurements_sha256,
            format_policy_receipt_sha256=plan.format_policy.policy_receipt_sha256,
            continuity_policy_receipt_sha256=plan.continuity_policy.policy_receipt_sha256,
            retained_ranges=plan.retained_ranges,
            removed_ranges=plan.removed_ranges,
            removed_sample_count=sum(item.sample_count for item in plan.removed_ranges),
            fade_samples=plan.continuity_policy.fade_samples,
            boundary_mode=readback.boundary_mode,
            boundary_count=readback.boundary_count,
            crossfade_overlap_samples=readback.crossfade_overlap_samples,
            boundary_evidence_sha256s=readback.boundary_evidence_sha256s,
            output_sha256=readback.output_sha256,
            output_identity_sha256=readback.output_identity_sha256,
            output_format=readback.output_format,
            output_sample_count=readback.output_sample_count,
            task046_lineage_candidate_sha256=lineage_candidate_sha256,
            range_map_verified=readback.range_map_verified,
            zero_cross_or_crossfade_verified=readback.zero_cross_or_crossfade_verified,
            speech_attack_preserved=readback.speech_attack_preserved,
            speech_tail_preserved=readback.speech_tail_preserved,
            partial_output_published=readback.partial_output_published,
            readback_verified=readback.readback_verified,
            directory_durable=readback.directory_durable,
            state=QAState.PASS if not reasons else QAState.FAIL,
            reason_codes=tuple(reasons),
            raw_source_preserved=readback.raw_source_preserved,
        )

    @staticmethod
    def _environment_receipt(
        plan: EnvironmentABPlan,
        bundle: EnvironmentMeasurementBundle | None,
        reasons: set[ReasonCode],
    ) -> EnvironmentABReceipt:
        segment_assessments = () if bundle is None else tuple(
            _assess_environment_segment(item) for item in bundle.segments
        )
        denoise_assessments = () if bundle is None else tuple(
            _assess_denoise(item) for item in bundle.denoise_pairs
        )
        final_reasons = set(reasons)
        comparison_state = QAState.UNKNOWN
        if bundle is not None and not final_reasons:
            all_assessments = (*segment_assessments, *denoise_assessments)
            if any(item.eligibility is SegmentEligibility.REJECT for item in all_assessments):
                comparison_state = QAState.FAIL
                final_reasons.add(ReasonCode.AB_SEGMENT_REJECTED)
            elif any(item.eligibility is SegmentEligibility.REVIEW for item in all_assessments):
                comparison_state = QAState.UNKNOWN
                final_reasons.add(ReasonCode.AB_REVIEW_REQUIRED)
            else:
                comparison_state = QAState.PASS
        return EnvironmentABReceipt(
            operation_id=plan.operation_id,
            project_id=plan.project_id,
            project_manifest_sha256=plan.project_manifest_sha256,
            installed_session_sha256=plan.installed_session_sha256,
            operation_plan_sha256=plan.operation_plan_sha256,
            plan_sha256=_environment_plan_sha256(plan),
            runner_build_sha256=plan.runner_build_sha256,
            analyzer_profile_sha256=plan.analyzer_profile_sha256,
            quality_policy_sha256=plan.quality_policy_sha256,
            off_capture_receipt_sha256=plan.off_capture.capture_receipt_sha256,
            on_capture_receipt_sha256=plan.on_capture.capture_receipt_sha256,
            measurement_bundle_sha256=None if bundle is None else _bundle_sha256(bundle),
            segment_assessments=segment_assessments,
            denoise_assessments=denoise_assessments,
            noise_deltas=() if bundle is None else _noise_deltas(bundle),
            comparison_state=comparison_state,
            reason_codes=tuple(final_reasons),
        )

    def _receipt(
        self,
        plan: GeneratedFinishingPlan | TrainingCopyPlan,
        measurements: QualityMeasurements,
        readback: FixtureEffectReadback | None,
        reasons: set[ReasonCode],
    ) -> AudioFinishingReceipt:
        is_generated = isinstance(plan, GeneratedFinishingPlan)
        return AudioFinishingReceipt(
            receipt_type=TECHNICAL_QA_RECEIPT_TYPE if is_generated else TRAINING_COPY_RECEIPT_TYPE,
            operation_kind=OperationKind.GENERATED_WAV_FINISH if is_generated else OperationKind.TRAINING_COPY_QA,
            operation_id=plan.operation_id,
            project_id=plan.project_id,
            project_manifest_sha256=plan.project_manifest_sha256,
            installed_session_sha256=plan.installed_session_sha256,
            operation_plan_sha256=plan.operation_plan_sha256,
            quick_clone_flow_sha256=plan.quick_clone_flow_sha256,
            plan_sha256=_plan_sha256(plan),
            source_sha256=plan.source.source_sha256,
            source_identity_sha256=plan.source.source_identity_sha256,
            terminal_source_receipt_sha256=plan.source.terminal_receipt_sha256,
            runner_build_sha256=plan.runner_build_sha256,
            analyzer_profile_sha256=plan.analyzer_profile_sha256,
            engine_recipe_sha256=None if is_generated else plan.engine_recipe_sha256,
            consent_receipt_sha256=None if is_generated else plan.consent_receipt_sha256,
            review_receipt_sha256=None if is_generated else plan.review_receipt_sha256,
            canonical_input_receipt_sha256=None if is_generated else plan.canonical_input_receipt_sha256,
            transport_format_receipt_sha256=None if is_generated else plan.transport_format_receipt_sha256,
            capture_chain_receipt_sha256=None if is_generated else plan.capture_chain_receipt_sha256,
            start_sample=plan.start_sample,
            end_sample=plan.end_sample,
            output_sha256=None if readback is None else readback.output_sha256,
            output_identity_sha256=None if readback is None else readback.output_identity_sha256,
            output_format=None if readback is None else readback.output_format,
            output_sample_count=None if readback is None else readback.output_sample_count,
            exact_range_applied=False if readback is None else readback.exact_range_applied,
            readback_verified=False if readback is None else readback.readback_verified,
            directory_durable=False if readback is None else readback.directory_durable,
            measurements=measurements,
            state=self._state(reasons),
            reason_codes=tuple(reasons),
            raw_source_preserved=True if readback is None else readback.raw_source_preserved,
        )


__all__ = [
    "AudioFinishingReceipt",
    "AudioFormat",
    "CaptureChainBinding",
    "CaptureCondition",
    "ChannelStrategy",
    "ClassificationState",
    "DeterministicFixtureAudioRunner",
    "DenoisePairMeasurement",
    "EnvironmentABPlan",
    "EnvironmentABReceipt",
    "EnvironmentCaptureBinding",
    "EnvironmentMeasurementBundle",
    "EnvironmentNoiseDelta",
    "EnvironmentSegmentMeasurement",
    "FinishingContractError",
    "FixtureEffectReadback",
    "FixtureVoiceQualityAudioFinishingService",
    "GeneratedFinishingPlan",
    "NoiseBandProfile",
    "OperationAlreadyConsumedError",
    "OperationKind",
    "QAState",
    "QualityMeasurements",
    "ReasonCode",
    "SegmentAssessment",
    "SegmentEligibility",
    "SampleRange",
    "SpeechContinuityPolicy",
    "SpeechContinuousPlan",
    "SpeechContinuousReadback",
    "SpeechContinuousReceipt",
    "SpeechEvidenceInterval",
    "StrictWavDecodeEvidence",
    "SourceSnapshot",
    "TrainingCopyPlan",
    "TrainingFormatPolicy",
    "VoiceEffort",
    "IntervalClass",
    "plan_speech_continuous",
]
