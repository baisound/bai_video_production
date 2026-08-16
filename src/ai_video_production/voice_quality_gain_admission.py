"""TASK-048 P-QC-1B body-free local gain receipt admission adapter.

This module validates metadata emitted by the TASK-047 local gain check and
classifies whether it is suitable input for a later canonical P-QC-1A
evaluation.  It never reads audio, runs an analyzer, changes gain, or issues a
canonical MeasurementReceipt/QualityEvaluationReceipt.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import math
import re
from typing import Any, Mapping

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


GAIN_ADMISSION_CONTRACT_VERSION = "1.0.0"
SOURCE_RECEIPT_SCHEMA = "bvp.task047.local-gain-check-receipt.v1"
TASK_OWNER = "TASK-048/P-QC-1B"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}")
_UTC_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")
_SOURCE_FIELDS = {
    "schema", "terminal_reason", "started_at_utc", "finished_at_utc",
    "measurement_fact_state", "signal_integrity_state", "gain_admission_state",
    "recommendation", "sample_peak_dbfs", "rms_dbfs", "clip_threshold_abs",
    "clip_sample_count", "non_finite_sample_count", "measured_sample_values",
    "received_bytes", "audio_body_persisted", "hardware_setting_changed",
    "session_key_persisted",
}


class ContractState(str, Enum):
    CANONICAL_REF_NOT_PROVIDED = "CANONICAL_REF_NOT_PROVIDED"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class MeasurementFactState(str, Enum):
    MEASURED = "MEASURED"
    ERROR_NON_FINITE_SAMPLE = "ERROR_NON_FINITE_SAMPLE"
    INSUFFICIENT_INPUT = "INSUFFICIENT_INPUT"


class SignalIntegrityState(str, Enum):
    MEASURED_NO_CLIPPING = "MEASURED_NO_CLIPPING"
    FAIL_CLIPPING = "FAIL_CLIPPING"
    UNKNOWN = "UNKNOWN"


class MeasurementFactValidity(str, Enum):
    VALID = "VALID"
    INVALID_INPUT = "INVALID_INPUT"
    UNKNOWN = "UNKNOWN"


class QualityState(str, Enum):
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    RERECORD_RECOMMENDED = "RERECORD_RECOMMENDED"


class AdmissionClassification(str, Enum):
    INVALID_MEASUREMENT = "INVALID_MEASUREMENT"
    RERECORD_RECOMMENDED_CLIPPING = "RERECORD_RECOMMENDED_CLIPPING"
    MEASURED_FACTS_POLICY_OR_CHAIN_UNBOUND = "MEASURED_FACTS_POLICY_OR_CHAIN_UNBOUND"
    MISMATCH = "MISMATCH"
    READY_FOR_CANONICAL_PQC_EVALUATION = "READY_FOR_CANONICAL_PQC_EVALUATION"


class GainReceiptValidationError(ValueError):
    """Bounded fail-closed rejection for an invalid TASK-047 source receipt."""

    code = "REJECTED_INVALID_RECEIPT"


class ProcessingClass(str, Enum):
    RAW_PRE_FILTER = "RAW_PRE_FILTER"
    OBS_POST_FILTER = "OBS_POST_FILTER"
    CANONICAL_CONVERTED_RAW = "CANONICAL_CONVERTED_RAW"
    RX_DERIVED = "RX_DERIVED"


def _expect_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _integer(value: Any, name: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _finite_number(value: Any, name: str, *, nullable: bool = False) -> float | None:
    if value is None and nullable:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


def _id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} is invalid")
    return validate_sha256(value, field_name=name)


def _timestamp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _UTC_RE.fullmatch(value):
        raise ValueError(f"{name} must be a UTC RFC3339 timestamp")
    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a UTC RFC3339 timestamp") from exc
    return value


def _enum(enum_type: type[Enum], value: Any, name: str) -> Enum:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


def canonical_sha256(value: Any) -> str:
    """Return the repository canonical-JSON digest for metadata."""
    return sha256_bytes(canonical_json_bytes(value))


@dataclass(frozen=True, slots=True)
class CanonicalRecordBinding:
    contract_state: ContractState
    record_ref: str | None
    record_sha256: str | None
    evidence_sha256: str | None

    def __post_init__(self) -> None:
        state = _enum(ContractState, self.contract_state, "contract_state")
        object.__setattr__(self, "contract_state", state)
        values = (self.record_ref, self.record_sha256, self.evidence_sha256)
        if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
            if any(value is not None for value in values):
                raise ValueError("unprovided binding cannot contain canonical fields")
            return
        if state is ContractState.BOUND_VERIFIED:
            _id(self.record_ref, "record_ref")
            _digest(self.record_sha256, "record_sha256")
            _digest(self.evidence_sha256, "evidence_sha256")
            return
        for value, name in zip(values, ("record_ref", "record_sha256", "evidence_sha256")):
            if value is not None:
                _id(value, name) if name == "record_ref" else _digest(value, name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_state": self.contract_state.value,
            "record_ref": self.record_ref,
            "record_sha256": self.record_sha256,
            "evidence_sha256": self.evidence_sha256,
        }


@dataclass(frozen=True, slots=True)
class CanonicalMeasurementBinding:
    contract_state: ContractState
    measurement_input_range_ref: str | None
    measurement_input_range_sha256: str | None
    canonical_mapping_receipt_ref: str | None
    canonical_mapping_receipt_sha256: str | None
    sample_rate: int | None
    bit_depth: int | None
    channels: int | None
    processing_class: ProcessingClass | None

    def __post_init__(self) -> None:
        state = _enum(ContractState, self.contract_state, "contract_state")
        object.__setattr__(self, "contract_state", state)
        values = (
            self.measurement_input_range_ref, self.measurement_input_range_sha256,
            self.canonical_mapping_receipt_ref, self.canonical_mapping_receipt_sha256,
            self.sample_rate, self.bit_depth, self.channels, self.processing_class,
        )
        if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
            if any(value is not None for value in values):
                raise ValueError("unprovided measurement binding cannot contain canonical fields")
            return
        if state is ContractState.BOUND_VERIFIED:
            _id(self.measurement_input_range_ref, "measurement_input_range_ref")
            _digest(self.measurement_input_range_sha256, "measurement_input_range_sha256")
            _id(self.canonical_mapping_receipt_ref, "canonical_mapping_receipt_ref")
            _digest(self.canonical_mapping_receipt_sha256, "canonical_mapping_receipt_sha256")
            if (self.sample_rate, self.bit_depth, self.channels) != (48_000, 24, 1):
                raise ValueError("canonical P-QC input must be 48000 Hz, 24-bit, mono")
            processing = _enum(ProcessingClass, self.processing_class, "processing_class")
            object.__setattr__(self, "processing_class", processing)
            return
        for value, name in (
            (self.measurement_input_range_ref, "measurement_input_range_ref"),
            (self.canonical_mapping_receipt_ref, "canonical_mapping_receipt_ref"),
        ):
            if value is not None:
                _id(value, name)
        for value, name in (
            (self.measurement_input_range_sha256, "measurement_input_range_sha256"),
            (self.canonical_mapping_receipt_sha256, "canonical_mapping_receipt_sha256"),
        ):
            if value is not None:
                _digest(value, name)
        for value, name in ((self.sample_rate, "sample_rate"), (self.bit_depth, "bit_depth"), (self.channels, "channels")):
            if value is not None:
                _integer(value, name, minimum=1)
        if self.processing_class is not None:
            object.__setattr__(self, "processing_class", _enum(ProcessingClass, self.processing_class, "processing_class"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_state": self.contract_state.value,
            "measurement_input_range_ref": self.measurement_input_range_ref,
            "measurement_input_range_sha256": self.measurement_input_range_sha256,
            "canonical_mapping_receipt_ref": self.canonical_mapping_receipt_ref,
            "canonical_mapping_receipt_sha256": self.canonical_mapping_receipt_sha256,
            "sample_rate": self.sample_rate,
            "bit_depth": self.bit_depth,
            "channels": self.channels,
            "processing_class": self.processing_class.value if self.processing_class else None,
        }


@dataclass(frozen=True, slots=True)
class GainAdmissionContext:
    measurement_binding: CanonicalMeasurementBinding
    capture_chain_binding: CanonicalRecordBinding
    analyzer_profile_binding: CanonicalRecordBinding
    quality_policy_binding: CanonicalRecordBinding

    def to_dict(self) -> dict[str, Any]:
        return {
            "measurement_binding": self.measurement_binding.to_dict(),
            "capture_chain_binding": self.capture_chain_binding.to_dict(),
            "analyzer_profile_binding": self.analyzer_profile_binding.to_dict(),
            "quality_policy_binding": self.quality_policy_binding.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class LocalGainCheckReceipt:
    terminal_reason: str
    started_at_utc: str
    finished_at_utc: str
    measurement_fact_state: MeasurementFactState
    signal_integrity_state: SignalIntegrityState
    recommendation: str
    sample_peak_dbfs: float | None
    rms_dbfs: float | None
    clip_threshold_abs: float
    clip_sample_count: int
    non_finite_sample_count: int
    measured_sample_values: int
    received_bytes: int

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LocalGainCheckReceipt":
        _expect_keys(value, _SOURCE_FIELDS, "local gain receipt")
        if value["schema"] != SOURCE_RECEIPT_SCHEMA:
            raise ValueError("source receipt schema is not supported")
        if not isinstance(value["terminal_reason"], str) or not value["terminal_reason"]:
            raise ValueError("terminal_reason is required")
        if value["gain_admission_state"] != "UNKNOWN_POLICY_NOT_BOUND":
            raise ValueError("source receipt cannot claim policy admission")
        if value["recommendation"] not in {"LOWER_HARDWARE_GAIN_PROPOSAL", "NO_AUTOMATIC_RECOMMENDATION"}:
            raise ValueError("recommendation is invalid")
        for flag in ("audio_body_persisted", "hardware_setting_changed", "session_key_persisted"):
            if value[flag] is not False:
                raise ValueError(f"{flag} must remain false")
        fact_state = _enum(MeasurementFactState, value["measurement_fact_state"], "measurement_fact_state")
        signal_state = _enum(SignalIntegrityState, value["signal_integrity_state"], "signal_integrity_state")
        peak = _finite_number(value["sample_peak_dbfs"], "sample_peak_dbfs", nullable=True)
        rms = _finite_number(value["rms_dbfs"], "rms_dbfs", nullable=True)
        threshold = _finite_number(value["clip_threshold_abs"], "clip_threshold_abs")
        if threshold != 0.9999:
            raise ValueError("clip_threshold_abs must match the hosted controller constant")
        clips = _integer(value["clip_sample_count"], "clip_sample_count")
        nonfinite = _integer(value["non_finite_sample_count"], "non_finite_sample_count")
        measured = _integer(value["measured_sample_values"], "measured_sample_values")
        received = _integer(value["received_bytes"], "received_bytes")
        started = _timestamp(value["started_at_utc"], "started_at_utc")
        finished = _timestamp(value["finished_at_utc"], "finished_at_utc")
        if datetime.fromisoformat(finished) < datetime.fromisoformat(started):
            raise ValueError("finished_at_utc cannot precede started_at_utc")
        if clips > measured or nonfinite > measured:
            raise ValueError("sample anomaly counts cannot exceed measured_sample_values")
        if fact_state is MeasurementFactState.INSUFFICIENT_INPUT:
            if measured != 0 or peak is not None or rms is not None or signal_state is not SignalIntegrityState.UNKNOWN:
                raise ValueError("insufficient input facts are inconsistent")
        elif fact_state is MeasurementFactState.ERROR_NON_FINITE_SAMPLE:
            if measured == 0 or nonfinite == 0:
                raise ValueError("non-finite error facts are inconsistent")
        else:
            if measured == 0 or nonfinite != 0:
                raise ValueError("measured facts are inconsistent")
            if received == 0:
                raise ValueError("measured facts require received bytes")
            if (peak is None) != (rms is None):
                raise ValueError("peak and RMS must both be measured zero or both numeric")
            if peak is not None and rms is not None and rms > peak:
                raise ValueError("RMS cannot exceed sample peak")
        if clips > 0:
            if signal_state is not SignalIntegrityState.FAIL_CLIPPING or value["recommendation"] != "LOWER_HARDWARE_GAIN_PROPOSAL":
                raise ValueError("clipping facts are inconsistent")
        elif measured > 0 and signal_state is not SignalIntegrityState.MEASURED_NO_CLIPPING:
            raise ValueError("non-clipping facts are inconsistent")
        elif clips == 0 and value["recommendation"] != "NO_AUTOMATIC_RECOMMENDATION":
            raise ValueError("non-clipping recommendation is inconsistent")
        return cls(
            terminal_reason=value["terminal_reason"],
            started_at_utc=started,
            finished_at_utc=finished,
            measurement_fact_state=fact_state,
            signal_integrity_state=signal_state,
            recommendation=value["recommendation"],
            sample_peak_dbfs=peak, rms_dbfs=rms, clip_threshold_abs=threshold,
            clip_sample_count=clips, non_finite_sample_count=nonfinite,
            measured_sample_values=measured, received_bytes=received,
        )

    @property
    def measured_linear_zero(self) -> bool:
        return self.measurement_fact_state is MeasurementFactState.MEASURED and self.sample_peak_dbfs is None and self.rms_dbfs is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SOURCE_RECEIPT_SCHEMA,
            "terminal_reason": self.terminal_reason,
            "started_at_utc": self.started_at_utc,
            "finished_at_utc": self.finished_at_utc,
            "measurement_fact_state": self.measurement_fact_state.value,
            "signal_integrity_state": self.signal_integrity_state.value,
            "gain_admission_state": "UNKNOWN_POLICY_NOT_BOUND",
            "recommendation": self.recommendation,
            "sample_peak_dbfs": self.sample_peak_dbfs,
            "rms_dbfs": self.rms_dbfs,
            "clip_threshold_abs": self.clip_threshold_abs,
            "clip_sample_count": self.clip_sample_count,
            "non_finite_sample_count": self.non_finite_sample_count,
            "measured_sample_values": self.measured_sample_values,
            "received_bytes": self.received_bytes,
            "audio_body_persisted": False,
            "hardware_setting_changed": False,
            "session_key_persisted": False,
        }


@dataclass(frozen=True, slots=True)
class GainReceiptAdmissionReport:
    source_receipt_sha256: str
    source_receipt: LocalGainCheckReceipt
    context: GainAdmissionContext
    measurement_fact_validity: MeasurementFactValidity
    classification: AdmissionClassification
    quality_state: QualityState

    def __post_init__(self) -> None:
        _digest(self.source_receipt_sha256, "source_receipt_sha256")
        if self.source_receipt_sha256 != canonical_sha256(self.source_receipt.to_dict()):
            raise ValueError("source receipt digest mismatch")
        if self.quality_state.value == "PASS":
            raise ValueError("adapter cannot issue quality PASS")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "gain_admission_contract_version": GAIN_ADMISSION_CONTRACT_VERSION,
            "record_type": "GainReceiptAdmissionReport",
            "task_owner": TASK_OWNER,
            "source_schema": SOURCE_RECEIPT_SCHEMA,
            "source_receipt_sha256": self.source_receipt_sha256,
            "source_receipt": self.source_receipt.to_dict(),
            "context": self.context.to_dict(),
            "measurement_fact_validity": self.measurement_fact_validity.value,
            "classification": self.classification.value,
            "quality_state": self.quality_state.value,
            "measured_linear_zero": self.source_receipt.measured_linear_zero,
            "canonical_pqc_measurement_receipt_issued": False,
            "canonical_pqc_quality_receipt_issued": False,
            "audio_body_read": False,
            "analyzer_executed": False,
            "hardware_or_obs_setting_changed": False,
            "gain_change_authorized": False,
            "dataset_training_production_authorized": False,
        }
        return {**body, "gain_receipt_admission_report_sha256": canonical_sha256(body)}


def classify_gain_receipt(
    source: Mapping[str, Any],
    context: GainAdmissionContext,
) -> GainReceiptAdmissionReport:
    """Validate and classify a TASK-047 receipt without issuing P-QC truth."""
    try:
        receipt = LocalGainCheckReceipt.from_dict(source)
    except ValueError as exc:
        raise GainReceiptValidationError(str(exc)) from exc
    digest = canonical_sha256(receipt.to_dict())
    if receipt.measurement_fact_state is MeasurementFactState.INSUFFICIENT_INPUT:
        validity = MeasurementFactValidity.UNKNOWN
        classification = AdmissionClassification.INVALID_MEASUREMENT
        quality = QualityState.UNKNOWN
    elif receipt.measurement_fact_state is MeasurementFactState.ERROR_NON_FINITE_SAMPLE:
        validity = MeasurementFactValidity.INVALID_INPUT
        classification = AdmissionClassification.INVALID_MEASUREMENT
        quality = QualityState.FAIL
    elif receipt.clip_sample_count > 0:
        validity = MeasurementFactValidity.VALID
        classification = AdmissionClassification.RERECORD_RECOMMENDED_CLIPPING
        quality = QualityState.RERECORD_RECOMMENDED
    else:
        states = {
            context.measurement_binding.contract_state,
            context.capture_chain_binding.contract_state,
            context.analyzer_profile_binding.contract_state,
            context.quality_policy_binding.contract_state,
        }
        validity = MeasurementFactValidity.VALID
        if ContractState.MISMATCH in states:
            classification = AdmissionClassification.MISMATCH
        elif states != {ContractState.BOUND_VERIFIED}:
            classification = AdmissionClassification.MEASURED_FACTS_POLICY_OR_CHAIN_UNBOUND
        else:
            classification = AdmissionClassification.READY_FOR_CANONICAL_PQC_EVALUATION
        quality = QualityState.UNKNOWN
    return GainReceiptAdmissionReport(
        source_receipt_sha256=digest,
        source_receipt=receipt,
        context=context,
        measurement_fact_validity=validity,
        classification=classification,
        quality_state=quality,
    )


def parse_gain_admission_report(value: Mapping[str, Any]) -> GainReceiptAdmissionReport:
    """Strictly parse and hash-verify a serialized admission report."""
    expected = {
        "gain_admission_contract_version", "record_type", "task_owner", "source_schema",
        "source_receipt_sha256", "source_receipt", "context", "measurement_fact_validity",
        "classification", "quality_state", "measured_linear_zero",
        "canonical_pqc_measurement_receipt_issued", "canonical_pqc_quality_receipt_issued",
        "audio_body_read", "analyzer_executed", "hardware_or_obs_setting_changed",
        "gain_change_authorized", "dataset_training_production_authorized",
        "gain_receipt_admission_report_sha256",
    }
    _expect_keys(value, expected, "GainReceiptAdmissionReport")
    if value["gain_admission_contract_version"] != GAIN_ADMISSION_CONTRACT_VERSION or value["record_type"] != "GainReceiptAdmissionReport" or value["task_owner"] != TASK_OWNER or value["source_schema"] != SOURCE_RECEIPT_SCHEMA:
        raise ValueError("admission report identity mismatch")
    for flag in (
        "canonical_pqc_measurement_receipt_issued", "canonical_pqc_quality_receipt_issued",
        "audio_body_read", "analyzer_executed", "hardware_or_obs_setting_changed",
        "gain_change_authorized", "dataset_training_production_authorized",
    ):
        if value[flag] is not False:
            raise ValueError(f"{flag} must remain false")
    context_value = value["context"]
    _expect_keys(context_value, {"measurement_binding", "capture_chain_binding", "analyzer_profile_binding", "quality_policy_binding"}, "context")
    context = GainAdmissionContext(
        measurement_binding=CanonicalMeasurementBinding(**context_value["measurement_binding"]),
        capture_chain_binding=CanonicalRecordBinding(**context_value["capture_chain_binding"]),
        analyzer_profile_binding=CanonicalRecordBinding(**context_value["analyzer_profile_binding"]),
        quality_policy_binding=CanonicalRecordBinding(**context_value["quality_policy_binding"]),
    )
    _enum(MeasurementFactValidity, value["measurement_fact_validity"], "measurement_fact_validity")
    _enum(AdmissionClassification, value["classification"], "classification")
    _enum(QualityState, value["quality_state"], "quality_state")
    report = classify_gain_receipt(value["source_receipt"], context)
    expected_dict = report.to_dict()
    if dict(value) != expected_dict:
        raise ValueError("serialized admission report is inconsistent or tampered")
    return report


_PUBLIC_SOURCE_FIELDS = {
    "measurement_fact_state", "signal_integrity_state", "recommendation",
    "sample_peak_dbfs", "rms_dbfs", "clip_sample_count", "non_finite_sample_count",
    "measured_sample_values",
}


def to_public_dict(report: GainReceiptAdmissionReport) -> dict[str, Any]:
    """Project non-identifying status while suppressing private refs and times."""
    source = report.source_receipt.to_dict()
    return {
        "gain_admission_contract_version": GAIN_ADMISSION_CONTRACT_VERSION,
        "record_type": "GainReceiptAdmissionReportPublicProjection",
        "source_schema": SOURCE_RECEIPT_SCHEMA,
        "source_receipt_sha256": report.source_receipt_sha256,
        "measurement_facts": {key: source[key] for key in sorted(_PUBLIC_SOURCE_FIELDS)},
        "binding_states": {
            "measurement": report.context.measurement_binding.contract_state.value,
            "capture_chain": report.context.capture_chain_binding.contract_state.value,
            "analyzer_profile": report.context.analyzer_profile_binding.contract_state.value,
            "quality_policy": report.context.quality_policy_binding.contract_state.value,
        },
        "measurement_fact_validity": report.measurement_fact_validity.value,
        "classification": report.classification.value,
        "quality_state": report.quality_state.value,
        "canonical_pqc_receipts_issued": False,
        "external_effect_authorized": False,
    }


CANONICAL_SERIALIZED_TYPES = ("GainReceiptAdmissionReport",)
