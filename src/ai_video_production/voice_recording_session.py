"""TASK-046 P-VS-3A body-free recording-session contract.

This module deliberately owns metadata validation only.  It never opens an
audio device, dispatches an OBS command, writes an Asset, creates a durable
job, adopts a Dataset candidate, or starts training.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
import re
from typing import Any, Mapping, Sequence

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


VOICE_RECORDING_SESSION_VERSION = "1.0.0"
TASK_OWNER = "TASK-046/P-VS-3A"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}")
_PRIVATE_KEYS = {
    "consent_subject_ref",
    "consent_scope",
    "allowed_usage_classes",
    "evidence_id",
    "evidence_ref",
    "evidence_sha256",
    "receipt_ref",
    "resource_profile_ref",
    "job_ref",
    "checkpoint_ref",
    "source_private_ref",
    "source_revision_sha256",
    "approved_text_revision_ref",
    "approved_text_revision_sha256",
    "source_text_binding_sha256",
    "asset_id",
    "asset_checksum_sha256",
    "asset_record_evidence_sha256",
    "asset_revision_binding_ref",
    "asset_revision_binding_sha256",
    "calibration_receipt_ref",
    "authorization_id",
    "human_gate_evidence_ref",
    "human_gate_evidence_sha256",
    "label_proposals",
    "approved_labels",
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


def _expect_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _enum(enum_type: type[Enum], value: Any, name: str) -> Enum:
    try:
        return value if isinstance(value, enum_type) else enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


def _bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be boolean")
    return value


def _integer(value: Any, name: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _digest(value: str | None, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    validate_sha256(value or "", field_name=name)
    return value


def _hash_body(body: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(body))


def _revision_guard(revision: int, parent_sha256: str | None, *, name: str) -> None:
    _integer(revision, f"{name}.revision", minimum=1)
    if revision == 1:
        if parent_sha256 is not None:
            raise ValueError(f"{name} first revision cannot have a parent")
    else:
        _digest(parent_sha256, f"{name}.parent_revision_sha256")


class ContractState(str, Enum):
    CANONICAL_REF_NOT_PROVIDED = "CANONICAL_REF_NOT_PROVIDED"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class CaptureMode(str, Enum):
    SYNTHETIC_CONTRACT_TEST = "SYNTHETIC_CONTRACT_TEST"
    OWNER_APPROVED_NON_DATASET_TECHNICAL_PROBE = "OWNER_APPROVED_NON_DATASET_TECHNICAL_PROBE"
    PRODUCTION_RECORDING = "PRODUCTION_RECORDING"


class ReadinessEvaluationState(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    TEST_READY = "TEST_READY"
    TECHNICAL_PROBE_READY = "TECHNICAL_PROBE_READY"
    PRODUCTION_READY = "PRODUCTION_READY"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class RecordingSessionState(str, Enum):
    DRAFT = "DRAFT"
    PREFLIGHT_PENDING = "PREFLIGHT_PENDING"
    PREFLIGHT_BLOCKED = "PREFLIGHT_BLOCKED"
    READY = "READY"
    CAPTURING = "CAPTURING"
    PAUSED = "PAUSED"
    STOP_REQUESTED = "STOP_REQUESTED"
    CAPTURED_CANDIDATE = "CAPTURED_CANDIDATE"
    REVIEW_PENDING = "REVIEW_PENDING"
    APPROVED_FOR_DATASET_ADOPTION = "APPROVED_FOR_DATASET_ADOPTION"
    ADOPTED_TO_DATASET = "ADOPTED_TO_DATASET"
    REJECTED = "REJECTED"
    FAILED_KNOWN = "FAILED_KNOWN"
    UNKNOWN = "UNKNOWN"
    CANCELLED = "CANCELLED"
    CANCELLED_WITH_RETAINED_EVIDENCE = "CANCELLED_WITH_RETAINED_EVIDENCE"


class SegmentAttemptState(str, Enum):
    PLANNED = "PLANNED"
    CAPTURING = "CAPTURING"
    INCOMPLETE = "INCOMPLETE"
    CAPTURED = "CAPTURED"
    FAILED_KNOWN = "FAILED_KNOWN"
    UNKNOWN = "UNKNOWN"
    CANCELLED_SAFE = "CANCELLED_SAFE"


class CandidateState(str, Enum):
    CAPTURED_CANDIDATE = "CAPTURED_CANDIDATE"
    REVIEW_PENDING = "REVIEW_PENDING"
    APPROVED_FOR_ADOPTION = "APPROVED_FOR_ADOPTION"
    ADOPTED_TO_DATASET = "ADOPTED_TO_DATASET"
    REJECTED = "REJECTED"
    RERECORD = "RERECORD"
    UNKNOWN = "UNKNOWN"


class ReviewDecision(str, Enum):
    APPROVE_FOR_ADOPTION = "APPROVE_FOR_ADOPTION"
    REJECT = "REJECT"
    RERECORD = "RERECORD"


class CaptureCommandKind(str, Enum):
    START = "START"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    STOP = "STOP"
    CANCEL = "CANCEL"


_BODY_FLAGS = {
    "audio_body_persisted": False,
    "script_body_persisted": False,
    "transcript_body_persisted": False,
    "credential_value_persisted": False,
    "host_absolute_path_persisted": False,
    "device_fingerprint_public": False,
    "dataset_mutation_authorized": False,
    "training_start_authorized": False,
    "capture_dispatch_authorized": False,
}


def _validate_body_flags(value: Mapping[str, Any]) -> None:
    _expect_keys(value, set(_BODY_FLAGS), "body_authority_flags")
    if dict(value) != _BODY_FLAGS:
        raise ValueError("body/effect authority flags must all remain false")


def _validate_consent(value: Mapping[str, Any]) -> None:
    expected = {
        "consent_subject_ref", "consent_scope", "allowed_usage_classes", "state",
        "subject_verified", "evidence_id", "evidence_sha256", "consent_sha256",
    }
    _expect_keys(value, expected, "ConsentReference")
    _id(value["consent_subject_ref"], "consent_subject_ref")
    if not isinstance(value["consent_scope"], str) or not value["consent_scope"].strip():
        raise ValueError("consent_scope is invalid")
    usages = value["allowed_usage_classes"]
    if not isinstance(usages, list) or not usages or len(usages) != len(set(usages)):
        raise ValueError("allowed_usage_classes must be a unique non-empty list")
    for item in usages:
        _id(item, "allowed_usage_class")
    if value["state"] not in {"UNKNOWN", "ACTIVE", "REVOKED"}:
        raise ValueError("ConsentReference state is invalid")
    _bool(value["subject_verified"], "subject_verified")
    if (value["evidence_id"] is None) != (value["evidence_sha256"] is None):
        raise ValueError("Consent evidence id/hash must be supplied together")
    if value["evidence_id"] is not None:
        _id(value["evidence_id"], "evidence_id")
        _digest(value["evidence_sha256"], "evidence_sha256")
    _digest(value["consent_sha256"], "consent_sha256")
    body = {key: item for key, item in value.items() if key != "consent_sha256"}
    if value["consent_sha256"] != _hash_body(body):
        raise ValueError("ConsentReference checksum mismatch")


def _validate_voice_profile_binding(value: Mapping[str, Any]) -> None:
    expected = {
        "voice_profile_id", "canonical_narration_profile_sha256", "revision",
        "parent_revision_sha256", "voice_profile_revision_sha256", "consent",
    }
    _expect_keys(value, expected, "VoiceProfileRevisionBinding")
    _id(value["voice_profile_id"], "voice_profile_id")
    _digest(value["canonical_narration_profile_sha256"], "canonical_narration_profile_sha256")
    _revision_guard(value["revision"], value["parent_revision_sha256"], name="VoiceProfileRevisionBinding")
    _digest(value["voice_profile_revision_sha256"], "voice_profile_revision_sha256")
    _validate_consent(value["consent"])


def _validate_text_binding(value: Mapping[str, Any]) -> None:
    expected = {
        "text_owner", "approved_text_revision_ref", "approved_text_revision_sha256",
        "source_text_binding_sha256", "body_persisted",
    }
    _expect_keys(value, expected, "ApprovedTextBinding")
    if value["text_owner"] not in {"TASK-006", "TASK-006/SRT"}:
        raise ValueError("text_owner is not canonical")
    _id(value["approved_text_revision_ref"], "approved_text_revision_ref")
    _digest(value["approved_text_revision_sha256"], "approved_text_revision_sha256")
    _digest(value["source_text_binding_sha256"], "source_text_binding_sha256")
    if value["body_persisted"] is not False:
        raise ValueError("text body must not be persisted")


def _validate_contract_binding(
    value: Mapping[str, Any],
    *,
    name: str,
    ref_field: str,
    state_field: str,
    pass_states: set[str],
) -> None:
    expected = {"contract_state", ref_field, f"{ref_field}_sha256", state_field, "evidence_sha256"}
    _expect_keys(value, expected, name)
    state = _enum(ContractState, value["contract_state"], f"{name}.contract_state")
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in expected - {"contract_state"}):
            raise ValueError(f"{name} unresolved binding must not invent canonical fields")
        return
    if value[ref_field] is not None:
        _id(value[ref_field], ref_field)
    for field in (f"{ref_field}_sha256", "evidence_sha256"):
        _digest(value[field], field, nullable=True)
    if state is ContractState.BOUND_VERIFIED:
        if any(value[field] is None for field in (ref_field, f"{ref_field}_sha256", state_field, "evidence_sha256")):
            raise ValueError(f"{name} BOUND_VERIFIED fields are incomplete")
        if value[state_field] not in pass_states | ({"FAIL", "DENIED", "BLOCKED"} if pass_states else set()):
            raise ValueError(f"{name}.{state_field} is invalid")
    elif value[state_field] is not None and not isinstance(value[state_field], str):
        raise ValueError(f"{name}.{state_field} is invalid")


def _validate_resource_binding(value: Mapping[str, Any]) -> None:
    expected = {
        "contract_state", "receipt_ref", "receipt_sha256", "decision_state",
        "resource_profile_ref", "resource_profile_sha256", "evidence_source_revision",
    }
    _expect_keys(value, expected, "ResourceAdmissionBinding")
    state = _enum(ContractState, value["contract_state"], "resource contract_state")
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in expected - {"contract_state"}):
            raise ValueError("unresolved resource binding must be null")
        return
    if value["decision_state"] not in {"UNKNOWN", "ADMITTED", "DENIED"}:
        raise ValueError("resource decision_state is invalid")
    for field in ("receipt_ref", "resource_profile_ref", "evidence_source_revision"):
        if value[field] is not None:
            _id(value[field], field)
    for field in ("receipt_sha256", "resource_profile_sha256"):
        _digest(value[field], field, nullable=True)
    if state is ContractState.BOUND_VERIFIED and any(
        value[field] is None
        for field in ("receipt_ref", "receipt_sha256", "decision_state", "resource_profile_ref", "resource_profile_sha256", "evidence_source_revision")
    ):
        raise ValueError("BOUND_VERIFIED resource binding is incomplete")


def _validate_calibration_binding(value: Mapping[str, Any]) -> None:
    expected = {
        "contract_state", "analyzer_profile_ref", "analyzer_profile_sha256",
        "calibration_receipt_ref", "calibration_receipt_sha256", "result",
        "threshold_profile_revision", "capture_chain_sha256", "measured_at",
    }
    _expect_keys(value, expected, "CalibrationBinding")
    state = _enum(ContractState, value["contract_state"], "calibration contract_state")
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in expected - {"contract_state"}):
            raise ValueError("unresolved calibration binding must be null")
        return
    if value["result"] not in {"PASS", "FAIL", "UNKNOWN"}:
        raise ValueError("calibration result is invalid")
    for field in ("analyzer_profile_ref", "calibration_receipt_ref", "threshold_profile_revision"):
        if value[field] is not None:
            _id(value[field], field)
    for field in ("analyzer_profile_sha256", "calibration_receipt_sha256", "capture_chain_sha256"):
        _digest(value[field], field, nullable=True)
    if value["measured_at"] is not None:
        _timestamp(value["measured_at"], "measured_at")
    if state is ContractState.BOUND_VERIFIED and any(
        value[field] is None for field in expected - {"contract_state"}
    ):
        raise ValueError("BOUND_VERIFIED calibration binding is incomplete")


def _validate_capture_adapter(value: Mapping[str, Any]) -> None:
    _validate_contract_binding(
        value,
        name="CaptureAdapterBinding",
        ref_field="adapter_ref",
        state_field="probe_state",
        pass_states={"PASS"},
    )


def _validate_durable_job(value: Mapping[str, Any]) -> None:
    expected = {"contract_state", "job_ref", "job_sha256", "checkpoint_ref", "checkpoint_sha256", "job_state"}
    _expect_keys(value, expected, "CaptureDurableJobBinding")
    state = _enum(ContractState, value["contract_state"], "job contract_state")
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in expected - {"contract_state"}):
            raise ValueError("unresolved job binding must be null")
        return
    for field in ("job_ref", "checkpoint_ref"):
        if value[field] is not None:
            _id(value[field], field)
    for field in ("job_sha256", "checkpoint_sha256"):
        _digest(value[field], field, nullable=True)
    if state is ContractState.BOUND_VERIFIED and any(value[field] is None for field in expected - {"contract_state"}):
        raise ValueError("BOUND_VERIFIED job binding is incomplete")
    if value["job_state"] is not None and value["job_state"] == "PROJECT_MAINTENANCE":
        raise ValueError("PROJECT_MAINTENANCE cannot be reused for capture")


def _validate_asset_binding(value: Mapping[str, Any]) -> None:
    expected = {
        "asset_binding_state", "asset_id", "asset_checksum_sha256",
        "asset_record_evidence_sha256", "asset_revision_binding_ref",
        "asset_revision_binding_sha256",
    }
    _expect_keys(value, expected, "AssetBinding")
    state = value["asset_binding_state"]
    if state == "UNBOUND_PENDING_TASK003":
        if any(value[field] is not None for field in expected - {"asset_binding_state"}):
            raise ValueError("UNBOUND asset binding cannot invent Asset fields")
        return
    if state != "BOUND":
        raise ValueError("asset_binding_state is invalid")
    _id(value["asset_id"], "asset_id")
    _id(value["asset_revision_binding_ref"], "asset_revision_binding_ref")
    for field in ("asset_checksum_sha256", "asset_record_evidence_sha256", "asset_revision_binding_sha256"):
        _digest(value[field], field)


def _validate_consent_evaluation(value: Mapping[str, Any]) -> None:
    expected = {
        "consent_snapshot_sha256", "current_evaluation_state",
        "current_evaluation_sha256", "evaluated_at",
    }
    _expect_keys(value, expected, "ConsentCurrentEvaluationBinding")
    _digest(value["consent_snapshot_sha256"], "consent_snapshot_sha256")
    if value["current_evaluation_state"] not in {"PASS", "REVOKED", "MISMATCH", "UNKNOWN"}:
        raise ValueError("current Consent evaluation is invalid")
    _digest(value["current_evaluation_sha256"], "current_evaluation_sha256")
    _timestamp(value["evaluated_at"], "Consent evaluated_at")


def _validate_authorization(value: Mapping[str, Any]) -> None:
    expected = {
        "contract_state", "authorization_id", "authorization_revision",
        "authorization_sha256", "authority_kind", "project_id", "recording_session_id",
        "session_revision_sha256", "capture_mode", "readiness_evaluation_sha256",
        "selected_source_binding_sha256", "consent_current_evaluation_sha256",
        "approved_text_binding_sha256", "scope", "issued_at", "expires_at",
        "one_shot", "replay_policy", "evidence_ref", "evidence_sha256",
    }
    _expect_keys(value, expected, "ExecutionAuthorizationBinding")
    state = _enum(ContractState, value["contract_state"], "authorization contract_state")
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in expected - {"contract_state"}):
            raise ValueError("unresolved authorization must not contain authority fields")
        return
    for field in ("authorization_id", "project_id", "recording_session_id", "evidence_ref"):
        if value[field] is not None:
            _id(value[field], field)
    if value["authorization_revision"] is not None:
        _integer(value["authorization_revision"], "authorization_revision", minimum=1)
    for field in (
        "authorization_sha256", "session_revision_sha256", "readiness_evaluation_sha256",
        "selected_source_binding_sha256", "consent_current_evaluation_sha256",
        "approved_text_binding_sha256", "evidence_sha256",
    ):
        _digest(value[field], field, nullable=True)
    if value["capture_mode"] is not None:
        _enum(CaptureMode, value["capture_mode"], "authorization capture_mode")
    if value["authority_kind"] not in {None, "OWNER_HUMAN_GATE", "APPROVED_SYNTHETIC_TEST_AUTHORITY"}:
        raise ValueError("authority_kind is invalid")
    if value["scope"] not in {None, "START", "RESUME"}:
        raise ValueError("authorization scope is invalid")
    if value["issued_at"] is not None:
        _timestamp(value["issued_at"], "issued_at")
    if value["expires_at"] is not None:
        _timestamp(value["expires_at"], "expires_at")
    if value["one_shot"] is not None:
        _bool(value["one_shot"], "one_shot")
    if value["replay_policy"] not in {None, "DENY_REPLAY", "SINGLE_USE_WITH_RECONCILIATION"}:
        raise ValueError("replay_policy is invalid")
    if state is ContractState.BOUND_VERIFIED and any(value[field] is None for field in expected - {"contract_state"}):
        raise ValueError("BOUND_VERIFIED authorization is incomplete")
    if state is ContractState.BOUND_VERIFIED:
        body = {key: item for key, item in value.items() if key != "authorization_sha256"}
        if value["authorization_sha256"] != _hash_body(body):
            raise ValueError("ExecutionAuthorizationBinding checksum mismatch")


def _validate_selected_source(value: Mapping[str, Any]) -> None:
    expected = {
        "contract_state", "source_private_ref", "source_revision_sha256",
        "public_opaque_ref", "source_class", "synthetic_non_biometric",
    }
    _expect_keys(value, expected, "SelectedSourceBinding")
    state = _enum(ContractState, value["contract_state"], "source contract_state")
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in expected - {"contract_state"}):
            raise ValueError("unresolved source binding must be null")
        return
    for field in ("source_private_ref", "public_opaque_ref"):
        if value[field] is not None:
            _id(value[field], field)
    _digest(value["source_revision_sha256"], "source_revision_sha256", nullable=True)
    if value["source_class"] not in {None, "SYNTHETIC_VIRTUAL", "OWNER_VOICE_PRIVATE", "PRODUCTION_SELECTED_SOURCE"}:
        raise ValueError("source_class is invalid")
    if value["synthetic_non_biometric"] is not None:
        _bool(value["synthetic_non_biometric"], "synthetic_non_biometric")
    if state is ContractState.BOUND_VERIFIED and any(value[field] is None for field in expected - {"contract_state"}):
        raise ValueError("BOUND_VERIFIED source binding is incomplete")


def _validate_cancel_disposition(value: Mapping[str, Any]) -> None:
    expected = {
        "cancel_ack_state", "external_work_present", "retained_evidence_present",
        "complete_candidate_present", "retained_evidence_ledger_sha256",
        "retention_state", "encryption_recovery_state",
    }
    _expect_keys(value, expected, "CancelDisposition")
    if value["cancel_ack_state"] not in {"NOT_REQUESTED", "ACK_VERIFIED", "UNKNOWN"}:
        raise ValueError("cancel_ack_state is invalid")
    for field in ("external_work_present", "retained_evidence_present", "complete_candidate_present"):
        _bool(value[field], field)
    _digest(value["retained_evidence_ledger_sha256"], "retained_evidence_ledger_sha256", nullable=True)
    if value["retention_state"] not in {"NOT_APPLICABLE", "BOUND", "UNKNOWN"}:
        raise ValueError("retention_state is invalid")
    if value["encryption_recovery_state"] not in {"NOT_APPLICABLE", "PASS", "UNKNOWN"}:
        raise ValueError("encryption_recovery_state is invalid")
    if value["retained_evidence_present"] and value["retained_evidence_ledger_sha256"] is None:
        raise ValueError("retained Evidence requires an exact ledger digest")


def _validate_dataset_adoption_binding(value: Mapping[str, Any]) -> None:
    expected = {
        "contract_state", "approved_review_decision_sha256", "dataset_parent_revision_sha256",
        "dataset_new_revision_sha256", "adoption_receipt_ref", "adoption_receipt_sha256",
        "effect_operation_id", "idempotency_key",
    }
    _expect_keys(value, expected, "DatasetAdoptionReceiptBinding")
    state = _enum(ContractState, value["contract_state"], "adoption contract_state")
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in expected - {"contract_state"}):
            raise ValueError("unresolved adoption binding must be null")
        return
    for field in ("adoption_receipt_ref", "effect_operation_id", "idempotency_key"):
        if value[field] is not None:
            _id(value[field], field)
    for field in (
        "approved_review_decision_sha256", "dataset_parent_revision_sha256",
        "dataset_new_revision_sha256", "adoption_receipt_sha256",
    ):
        _digest(value[field], field, nullable=True)
    if state is ContractState.BOUND_VERIFIED and any(value[field] is None for field in expected - {"contract_state"}):
        raise ValueError("BOUND_VERIFIED adoption binding is incomplete")


def _validate_label_rows(value: Sequence[Mapping[str, Any]], name: str) -> None:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be a list")
    seen: set[tuple[str, str]] = set()
    for row in value:
        _expect_keys(row, {"axis", "value", "source", "evidence_sha256"}, name)
        _id(row["axis"], f"{name}.axis")
        _id(row["value"], f"{name}.value")
        if row["source"] not in {"AI_PROPOSAL", "OWNER_APPROVED"}:
            raise ValueError(f"{name}.source is invalid")
        _digest(row["evidence_sha256"], f"{name}.evidence_sha256")
        key = (row["axis"], row["value"])
        if key in seen:
            raise ValueError(f"{name} contains duplicate labels")
        seen.add(key)


class _HashedRecord:
    record_type: str
    hash_field: str

    def _body(self) -> dict[str, Any]:
        raise NotImplementedError

    @property
    def sha256(self) -> str:
        return _hash_body(self._body())

    def to_private_dict(self) -> dict[str, Any]:
        body = self._body()
        return {**body, self.hash_field: _hash_body(body)}

    def to_public_dict(self) -> dict[str, Any]:
        private = self.to_private_dict()

        def redact(value: Any) -> Any:
            if isinstance(value, Mapping):
                return {
                    key: redact(item)
                    for key, item in value.items()
                    if key not in _PRIVATE_KEYS
                }
            if isinstance(value, list):
                return [redact(item) for item in value]
            return value

        projection = redact(private)
        projection["projection"] = "PUBLIC_REDACTED"
        projection["public_projection_sha256"] = _hash_body(projection)
        return projection


@dataclass(frozen=True, slots=True)
class VoiceRecordingSessionRevision(_HashedRecord):
    project_id: str
    recording_session_id: str
    revision: int
    parent_revision_sha256: str | None
    created_at: str
    state: RecordingSessionState
    capture_mode: CaptureMode
    readiness_evaluation_state: ReadinessEvaluationState
    readiness_evaluation_sha256: str
    production_admission: bool
    operation_id: str
    voice_profile_binding: Mapping[str, Any]
    approved_text_binding: Mapping[str, Any]
    selected_source_binding: Mapping[str, Any]
    capture_adapter_binding: Mapping[str, Any]
    resource_admission_binding: Mapping[str, Any]
    calibration_binding: Mapping[str, Any]
    capture_durable_job_binding: Mapping[str, Any]
    encryption_recovery_binding: Mapping[str, Any]
    disk_floor_binding: Mapping[str, Any]
    owner_go_binding: Mapping[str, Any]
    consent_current_evaluation: Mapping[str, Any]
    execution_authorization_binding: Mapping[str, Any]
    cancel_disposition: Mapping[str, Any]
    dataset_adoption_receipt_binding: Mapping[str, Any]
    body_authority_flags: Mapping[str, Any]

    record_type = "VoiceRecordingSessionRevision"
    hash_field = "voice_recording_session_revision_sha256"

    def __post_init__(self) -> None:
        for field in ("project_id", "recording_session_id", "operation_id"):
            _id(getattr(self, field), field)
        _revision_guard(self.revision, self.parent_revision_sha256, name=self.record_type)
        _timestamp(self.created_at, "created_at")
        if not isinstance(self.state, RecordingSessionState):
            raise ValueError("state must be RecordingSessionState")
        if not isinstance(self.capture_mode, CaptureMode):
            raise ValueError("capture_mode must be CaptureMode")
        if not isinstance(self.readiness_evaluation_state, ReadinessEvaluationState):
            raise ValueError("readiness_evaluation_state must be ReadinessEvaluationState")
        _digest(self.readiness_evaluation_sha256, "readiness_evaluation_sha256")
        _bool(self.production_admission, "production_admission")
        _validate_voice_profile_binding(self.voice_profile_binding)
        _validate_text_binding(self.approved_text_binding)
        _validate_selected_source(self.selected_source_binding)
        _validate_capture_adapter(self.capture_adapter_binding)
        _validate_resource_binding(self.resource_admission_binding)
        _validate_calibration_binding(self.calibration_binding)
        _validate_durable_job(self.capture_durable_job_binding)
        _validate_contract_binding(
            self.encryption_recovery_binding,
            name="EncryptionRecoveryBinding",
            ref_field="policy_ref",
            state_field="result",
            pass_states={"PASS"},
        )
        _validate_contract_binding(
            self.disk_floor_binding,
            name="DiskFloorBinding",
            ref_field="receipt_ref",
            state_field="result",
            pass_states={"PASS"},
        )
        _validate_contract_binding(
            self.owner_go_binding,
            name="OwnerGoBinding",
            ref_field="decision_ref",
            state_field="decision",
            pass_states={"GO"},
        )
        _validate_consent_evaluation(self.consent_current_evaluation)
        _validate_authorization(self.execution_authorization_binding)
        _validate_cancel_disposition(self.cancel_disposition)
        _validate_dataset_adoption_binding(self.dataset_adoption_receipt_binding)
        _validate_body_flags(self.body_authority_flags)
        self._validate_readiness()
        self._validate_cancel_state()
        if (
            self.state is RecordingSessionState.ADOPTED_TO_DATASET
            and self.dataset_adoption_receipt_binding["contract_state"]
            != ContractState.BOUND_VERIFIED.value
        ):
            raise ValueError("session ADOPTED_TO_DATASET requires verified external adoption receipt")

    def _validate_readiness(self) -> None:
        expected = {
            CaptureMode.SYNTHETIC_CONTRACT_TEST: ReadinessEvaluationState.TEST_READY,
            CaptureMode.OWNER_APPROVED_NON_DATASET_TECHNICAL_PROBE: ReadinessEvaluationState.TECHNICAL_PROBE_READY,
            CaptureMode.PRODUCTION_RECORDING: ReadinessEvaluationState.PRODUCTION_READY,
        }
        if self.state is RecordingSessionState.READY and self.readiness_evaluation_state is not expected[self.capture_mode]:
            raise ValueError("READY state does not match capture_mode readiness class")
        if self.production_admission:
            if self.capture_mode is not CaptureMode.PRODUCTION_RECORDING or self.readiness_evaluation_state is not ReadinessEvaluationState.PRODUCTION_READY:
                raise ValueError("production_admission requires PRODUCTION_READY mode")
            gates = (
                self.capture_adapter_binding.get("contract_state") == ContractState.BOUND_VERIFIED.value
                and self.capture_adapter_binding.get("probe_state") == "PASS"
                and self.resource_admission_binding.get("contract_state") == ContractState.BOUND_VERIFIED.value
                and self.resource_admission_binding.get("decision_state") == "ADMITTED"
                and self.calibration_binding.get("contract_state") == ContractState.BOUND_VERIFIED.value
                and self.calibration_binding.get("result") == "PASS"
                and self.capture_durable_job_binding.get("contract_state") == ContractState.BOUND_VERIFIED.value
                and self.encryption_recovery_binding.get("contract_state") == ContractState.BOUND_VERIFIED.value
                and self.encryption_recovery_binding.get("result") == "PASS"
                and self.disk_floor_binding.get("contract_state") == ContractState.BOUND_VERIFIED.value
                and self.disk_floor_binding.get("result") == "PASS"
                and self.owner_go_binding.get("contract_state") == ContractState.BOUND_VERIFIED.value
                and self.owner_go_binding.get("decision") == "GO"
                and self.consent_current_evaluation.get("current_evaluation_state") == "PASS"
                and self.selected_source_binding.get("contract_state") == ContractState.BOUND_VERIFIED.value
                and self.selected_source_binding.get("source_class") == "PRODUCTION_SELECTED_SOURCE"
            )
            if not gates:
                raise ValueError("production admission gates are incomplete")
        elif self.readiness_evaluation_state is ReadinessEvaluationState.PRODUCTION_READY:
            raise ValueError("PRODUCTION_READY cannot claim production_admission=false")
        if self.capture_mode is CaptureMode.SYNTHETIC_CONTRACT_TEST:
            if self.selected_source_binding.get("contract_state") == ContractState.BOUND_VERIFIED.value and (
                self.selected_source_binding.get("source_class") != "SYNTHETIC_VIRTUAL"
                or self.selected_source_binding.get("synthetic_non_biometric") is not True
            ):
                raise ValueError("synthetic mode requires a non-biometric synthetic source")

    def _validate_cancel_state(self) -> None:
        disposition = self.cancel_disposition
        if disposition["complete_candidate_present"] and self.state in {
            RecordingSessionState.CANCELLED,
            RecordingSessionState.CANCELLED_WITH_RETAINED_EVIDENCE,
        }:
            raise ValueError("a complete Candidate cannot be concealed by cancellation")
        if self.state is RecordingSessionState.CANCELLED:
            if disposition["cancel_ack_state"] != "ACK_VERIFIED" or any(
                disposition[field]
                for field in ("external_work_present", "retained_evidence_present", "complete_candidate_present")
            ):
                raise ValueError("plain CANCELLED requires verified no-work disposition")
        if self.state is RecordingSessionState.CANCELLED_WITH_RETAINED_EVIDENCE:
            if (
                disposition["cancel_ack_state"] != "ACK_VERIFIED"
                or not disposition["retained_evidence_present"]
                or disposition["complete_candidate_present"]
                or disposition["retention_state"] != "BOUND"
                or disposition["encryption_recovery_state"] != "PASS"
            ):
                raise ValueError("retained Evidence cancellation guards are incomplete")

    def _body(self) -> dict[str, Any]:
        return {
            "recording_contract_version": VOICE_RECORDING_SESSION_VERSION,
            "record_type": self.record_type,
            "task_owner": TASK_OWNER,
            "project_id": self.project_id,
            "recording_session_id": self.recording_session_id,
            "revision": self.revision,
            "parent_revision_sha256": self.parent_revision_sha256,
            "created_at": self.created_at,
            "state": self.state.value,
            "capture_mode": self.capture_mode.value,
            "readiness_evaluation_state": self.readiness_evaluation_state.value,
            "readiness_evaluation_sha256": self.readiness_evaluation_sha256,
            "production_admission": self.production_admission,
            "operation_id": self.operation_id,
            "voice_profile_binding": dict(self.voice_profile_binding),
            "approved_text_binding": dict(self.approved_text_binding),
            "selected_source_binding": dict(self.selected_source_binding),
            "capture_adapter_binding": dict(self.capture_adapter_binding),
            "resource_admission_binding": dict(self.resource_admission_binding),
            "calibration_binding": dict(self.calibration_binding),
            "capture_durable_job_binding": dict(self.capture_durable_job_binding),
            "encryption_recovery_binding": dict(self.encryption_recovery_binding),
            "disk_floor_binding": dict(self.disk_floor_binding),
            "owner_go_binding": dict(self.owner_go_binding),
            "consent_current_evaluation": dict(self.consent_current_evaluation),
            "execution_authorization_binding": dict(self.execution_authorization_binding),
            "cancel_disposition": dict(self.cancel_disposition),
            "dataset_adoption_receipt_binding": dict(self.dataset_adoption_receipt_binding),
            "body_authority_flags": dict(self.body_authority_flags),
        }


@dataclass(frozen=True, slots=True)
class VoiceSegmentAttemptRevision(_HashedRecord):
    project_id: str
    recording_session_id: str
    segment_id: str
    attempt_id: str
    revision: int
    parent_revision_sha256: str | None
    attempt_number: int
    parent_attempt_sha256: str | None
    cue_id: str
    sentence_id: str
    source_text_binding_sha256: str
    sentence_start_anchor: int
    state: SegmentAttemptState
    capture_receipt_binding: Mapping[str, Any]
    asset_binding: Mapping[str, Any]
    calibration_binding: Mapping[str, Any]
    consent_current_evaluation: Mapping[str, Any]
    operation_id: str
    created_at: str
    body_authority_flags: Mapping[str, Any]

    record_type = "VoiceSegmentAttemptRevision"
    hash_field = "voice_segment_attempt_revision_sha256"

    def __post_init__(self) -> None:
        for field in ("project_id", "recording_session_id", "segment_id", "attempt_id", "cue_id", "sentence_id", "operation_id"):
            _id(getattr(self, field), field)
        _revision_guard(self.revision, self.parent_revision_sha256, name=self.record_type)
        _integer(self.attempt_number, "attempt_number", minimum=1)
        if self.attempt_number == 1:
            if self.parent_attempt_sha256 is not None:
                raise ValueError("first attempt cannot have parent_attempt_sha256")
        else:
            _digest(self.parent_attempt_sha256, "parent_attempt_sha256")
        _digest(self.source_text_binding_sha256, "source_text_binding_sha256")
        _integer(self.sentence_start_anchor, "sentence_start_anchor")
        if not isinstance(self.state, SegmentAttemptState):
            raise ValueError("state must be SegmentAttemptState")
        _validate_contract_binding(
            self.capture_receipt_binding,
            name="CaptureEvidenceBinding",
            ref_field="receipt_ref",
            state_field="capture_state",
            pass_states={"CAPTURED"},
        )
        _validate_asset_binding(self.asset_binding)
        _validate_calibration_binding(self.calibration_binding)
        _validate_consent_evaluation(self.consent_current_evaluation)
        _timestamp(self.created_at, "created_at")
        _validate_body_flags(self.body_authority_flags)

    def _body(self) -> dict[str, Any]:
        return {
            "recording_contract_version": VOICE_RECORDING_SESSION_VERSION,
            "record_type": self.record_type,
            "task_owner": TASK_OWNER,
            "project_id": self.project_id,
            "recording_session_id": self.recording_session_id,
            "segment_id": self.segment_id,
            "attempt_id": self.attempt_id,
            "revision": self.revision,
            "parent_revision_sha256": self.parent_revision_sha256,
            "attempt_number": self.attempt_number,
            "parent_attempt_sha256": self.parent_attempt_sha256,
            "cue_id": self.cue_id,
            "sentence_id": self.sentence_id,
            "source_text_binding_sha256": self.source_text_binding_sha256,
            "sentence_start_anchor": self.sentence_start_anchor,
            "state": self.state.value,
            "capture_receipt_binding": dict(self.capture_receipt_binding),
            "asset_binding": dict(self.asset_binding),
            "calibration_binding": dict(self.calibration_binding),
            "consent_current_evaluation": dict(self.consent_current_evaluation),
            "operation_id": self.operation_id,
            "created_at": self.created_at,
            "body_authority_flags": dict(self.body_authority_flags),
        }


@dataclass(frozen=True, slots=True)
class TeleprompterCheckpointRevision(_HashedRecord):
    project_id: str
    recording_session_id: str
    checkpoint_id: str
    revision: int
    parent_revision_sha256: str | None
    plan_binding: Mapping[str, Any]
    segment_id: str
    attempt_id: str
    attempt_number: int
    cue_id: str
    sentence_id: str
    source_text_binding_sha256: str
    sentence_start_anchor: int
    scroll_position: int
    last_completed_segment_id: str | None
    checkpoint_state: str
    created_at: str
    body_authority_flags: Mapping[str, Any]

    record_type = "TeleprompterCheckpointRevision"
    hash_field = "teleprompter_checkpoint_revision_sha256"

    def __post_init__(self) -> None:
        for field in ("project_id", "recording_session_id", "checkpoint_id", "segment_id", "attempt_id", "cue_id", "sentence_id"):
            _id(getattr(self, field), field)
        _revision_guard(self.revision, self.parent_revision_sha256, name=self.record_type)
        _expect_keys(
            self.plan_binding,
            {"plan_id", "plan_revision", "plan_sha256", "approved_text_binding_sha256", "planned_minutes"},
            "TeleprompterPlanBinding",
        )
        _id(self.plan_binding["plan_id"], "plan_id")
        _integer(self.plan_binding["plan_revision"], "plan_revision", minimum=1)
        _digest(self.plan_binding["plan_sha256"], "plan_sha256")
        _digest(self.plan_binding["approved_text_binding_sha256"], "approved_text_binding_sha256")
        if self.plan_binding["planned_minutes"] not in {30, 60, 90, 120}:
            raise ValueError("planned_minutes must be 30, 60, 90, or 120")
        _integer(self.attempt_number, "attempt_number", minimum=1)
        _digest(self.source_text_binding_sha256, "source_text_binding_sha256")
        _integer(self.sentence_start_anchor, "sentence_start_anchor")
        _integer(self.scroll_position, "scroll_position")
        if self.last_completed_segment_id is not None:
            _id(self.last_completed_segment_id, "last_completed_segment_id")
        if self.checkpoint_state not in {"CURRENT", "SUPERSEDED", "UNKNOWN"}:
            raise ValueError("checkpoint_state is invalid")
        _timestamp(self.created_at, "created_at")
        _validate_body_flags(self.body_authority_flags)

    def _body(self) -> dict[str, Any]:
        return {
            "recording_contract_version": VOICE_RECORDING_SESSION_VERSION,
            "record_type": self.record_type,
            "task_owner": TASK_OWNER,
            "project_id": self.project_id,
            "recording_session_id": self.recording_session_id,
            "checkpoint_id": self.checkpoint_id,
            "revision": self.revision,
            "parent_revision_sha256": self.parent_revision_sha256,
            "plan_binding": dict(self.plan_binding),
            "segment_id": self.segment_id,
            "attempt_id": self.attempt_id,
            "attempt_number": self.attempt_number,
            "cue_id": self.cue_id,
            "sentence_id": self.sentence_id,
            "source_text_binding_sha256": self.source_text_binding_sha256,
            "sentence_start_anchor": self.sentence_start_anchor,
            "scroll_position": self.scroll_position,
            "last_completed_segment_id": self.last_completed_segment_id,
            "checkpoint_state": self.checkpoint_state,
            "created_at": self.created_at,
            "body_authority_flags": dict(self.body_authority_flags),
        }


@dataclass(frozen=True, slots=True)
class DatasetCandidateRevision(_HashedRecord):
    project_id: str
    recording_session_id: str
    candidate_id: str
    revision: int
    parent_revision_sha256: str | None
    state: CandidateState
    segment_attempt_id: str
    segment_attempt_revision_sha256: str
    capture_receipt_binding: Mapping[str, Any]
    asset_binding: Mapping[str, Any]
    voice_profile_binding: Mapping[str, Any]
    consent_current_evaluation: Mapping[str, Any]
    calibration_binding: Mapping[str, Any]
    label_proposals: Sequence[Mapping[str, Any]]
    approved_labels: Sequence[Mapping[str, Any]]
    review_decision_binding: Mapping[str, Any]
    dataset_adoption_receipt_binding: Mapping[str, Any]
    operation_id: str
    created_at: str
    body_authority_flags: Mapping[str, Any]

    record_type = "DatasetCandidateRevision"
    hash_field = "dataset_candidate_revision_sha256"

    def __post_init__(self) -> None:
        for field in ("project_id", "recording_session_id", "candidate_id", "segment_attempt_id", "operation_id"):
            _id(getattr(self, field), field)
        _revision_guard(self.revision, self.parent_revision_sha256, name=self.record_type)
        if not isinstance(self.state, CandidateState):
            raise ValueError("state must be CandidateState")
        _digest(self.segment_attempt_revision_sha256, "segment_attempt_revision_sha256")
        _validate_contract_binding(
            self.capture_receipt_binding,
            name="CaptureEvidenceBinding",
            ref_field="receipt_ref",
            state_field="capture_state",
            pass_states={"CAPTURED"},
        )
        _validate_asset_binding(self.asset_binding)
        _validate_voice_profile_binding(self.voice_profile_binding)
        _validate_consent_evaluation(self.consent_current_evaluation)
        _validate_calibration_binding(self.calibration_binding)
        _validate_label_rows(self.label_proposals, "label_proposals")
        _validate_label_rows(self.approved_labels, "approved_labels")
        if any(row["source"] != "AI_PROPOSAL" for row in self.label_proposals):
            raise ValueError("label proposals must remain proposals")
        if any(row["source"] != "OWNER_APPROVED" for row in self.approved_labels):
            raise ValueError("approved labels require Owner approval")
        _validate_contract_binding(
            self.review_decision_binding,
            name="DatasetCandidateReviewDecisionBinding",
            ref_field="decision_ref",
            state_field="decision",
            pass_states={"APPROVE_FOR_ADOPTION", "REJECT", "RERECORD"},
        )
        _validate_dataset_adoption_binding(self.dataset_adoption_receipt_binding)
        approval_gates = (
            self.asset_binding["asset_binding_state"] == "BOUND"
            and self.review_decision_binding["contract_state"] == ContractState.BOUND_VERIFIED.value
            and self.review_decision_binding["decision"] == "APPROVE_FOR_ADOPTION"
            and self.consent_current_evaluation["current_evaluation_state"] == "PASS"
            and self.calibration_binding["contract_state"] == ContractState.BOUND_VERIFIED.value
            and self.calibration_binding["result"] == "PASS"
        )
        if self.state in {CandidateState.APPROVED_FOR_ADOPTION, CandidateState.ADOPTED_TO_DATASET} and not approval_gates:
            raise ValueError("Dataset approval requires exact Review/Asset/Consent/quality bindings")
        if self.state is CandidateState.ADOPTED_TO_DATASET and self.dataset_adoption_receipt_binding["contract_state"] != ContractState.BOUND_VERIFIED.value:
            raise ValueError("ADOPTED_TO_DATASET requires a verified external adoption receipt")
        expected_review_decision = {
            CandidateState.REJECTED: "REJECT",
            CandidateState.RERECORD: "RERECORD",
        }.get(self.state)
        if expected_review_decision is not None and not (
            self.review_decision_binding["contract_state"] == ContractState.BOUND_VERIFIED.value
            and self.review_decision_binding["decision"] == expected_review_decision
        ):
            raise ValueError(f"{self.state.value} requires an exact Owner ReviewDecision binding")
        _timestamp(self.created_at, "created_at")
        _validate_body_flags(self.body_authority_flags)

    def _body(self) -> dict[str, Any]:
        return {
            "recording_contract_version": VOICE_RECORDING_SESSION_VERSION,
            "record_type": self.record_type,
            "task_owner": TASK_OWNER,
            "project_id": self.project_id,
            "recording_session_id": self.recording_session_id,
            "candidate_id": self.candidate_id,
            "revision": self.revision,
            "parent_revision_sha256": self.parent_revision_sha256,
            "state": self.state.value,
            "segment_attempt_id": self.segment_attempt_id,
            "segment_attempt_revision_sha256": self.segment_attempt_revision_sha256,
            "capture_receipt_binding": dict(self.capture_receipt_binding),
            "asset_binding": dict(self.asset_binding),
            "voice_profile_binding": dict(self.voice_profile_binding),
            "consent_current_evaluation": dict(self.consent_current_evaluation),
            "calibration_binding": dict(self.calibration_binding),
            "label_proposals": [dict(row) for row in self.label_proposals],
            "approved_labels": [dict(row) for row in self.approved_labels],
            "review_decision_binding": dict(self.review_decision_binding),
            "dataset_adoption_receipt_binding": dict(self.dataset_adoption_receipt_binding),
            "operation_id": self.operation_id,
            "created_at": self.created_at,
            "body_authority_flags": dict(self.body_authority_flags),
        }


@dataclass(frozen=True, slots=True)
class DatasetCandidateReviewDecision(_HashedRecord):
    project_id: str
    recording_session_id: str
    review_decision_id: str
    revision: int
    parent_revision_sha256: str | None
    candidate_id: str
    candidate_revision_sha256: str
    decision: ReviewDecision
    reviewer_kind: str
    human_gate_evidence_ref: str
    human_gate_evidence_sha256: str
    asset_binding: Mapping[str, Any]
    consent_current_evaluation: Mapping[str, Any]
    calibration_binding: Mapping[str, Any]
    decided_at: str
    training_start_authorized: bool
    body_authority_flags: Mapping[str, Any]

    record_type = "DatasetCandidateReviewDecision"
    hash_field = "dataset_candidate_review_decision_sha256"

    def __post_init__(self) -> None:
        for field in ("project_id", "recording_session_id", "review_decision_id", "candidate_id", "human_gate_evidence_ref"):
            _id(getattr(self, field), field)
        _revision_guard(self.revision, self.parent_revision_sha256, name=self.record_type)
        _digest(self.candidate_revision_sha256, "candidate_revision_sha256")
        if not isinstance(self.decision, ReviewDecision):
            raise ValueError("decision must be ReviewDecision")
        if self.reviewer_kind != "OWNER":
            raise ValueError("Dataset Candidate review requires the Owner")
        _digest(self.human_gate_evidence_sha256, "human_gate_evidence_sha256")
        _validate_asset_binding(self.asset_binding)
        _validate_consent_evaluation(self.consent_current_evaluation)
        _validate_calibration_binding(self.calibration_binding)
        _timestamp(self.decided_at, "decided_at")
        if self.training_start_authorized is not False:
            raise ValueError("review decision cannot authorize training")
        if self.decision is ReviewDecision.APPROVE_FOR_ADOPTION and not (
            self.asset_binding["asset_binding_state"] == "BOUND"
            and self.consent_current_evaluation["current_evaluation_state"] == "PASS"
            and self.calibration_binding["contract_state"] == ContractState.BOUND_VERIFIED.value
            and self.calibration_binding["result"] == "PASS"
        ):
            raise ValueError("APPROVE_FOR_ADOPTION gates are incomplete")
        _validate_body_flags(self.body_authority_flags)

    def _body(self) -> dict[str, Any]:
        return {
            "recording_contract_version": VOICE_RECORDING_SESSION_VERSION,
            "record_type": self.record_type,
            "task_owner": TASK_OWNER,
            "project_id": self.project_id,
            "recording_session_id": self.recording_session_id,
            "review_decision_id": self.review_decision_id,
            "revision": self.revision,
            "parent_revision_sha256": self.parent_revision_sha256,
            "candidate_id": self.candidate_id,
            "candidate_revision_sha256": self.candidate_revision_sha256,
            "decision": self.decision.value,
            "reviewer_kind": self.reviewer_kind,
            "human_gate_evidence_ref": self.human_gate_evidence_ref,
            "human_gate_evidence_sha256": self.human_gate_evidence_sha256,
            "asset_binding": dict(self.asset_binding),
            "consent_current_evaluation": dict(self.consent_current_evaluation),
            "calibration_binding": dict(self.calibration_binding),
            "decided_at": self.decided_at,
            "training_start_authorized": self.training_start_authorized,
            "body_authority_flags": dict(self.body_authority_flags),
        }


_RECORDS: dict[str, type[_HashedRecord]] = {
    record.record_type: record
    for record in (
        VoiceRecordingSessionRevision,
        VoiceSegmentAttemptRevision,
        TeleprompterCheckpointRevision,
        DatasetCandidateRevision,
        DatasetCandidateReviewDecision,
    )
}


def _construct_record(record_type: type[_HashedRecord], value: Mapping[str, Any]) -> _HashedRecord:
    expected = set(record_type.__dataclass_fields__)  # type: ignore[attr-defined]
    envelope = {
        "recording_contract_version", "record_type", "task_owner", record_type.hash_field,
    }
    _expect_keys(value, expected | envelope, record_type.record_type)
    if value["recording_contract_version"] != VOICE_RECORDING_SESSION_VERSION or value["task_owner"] != TASK_OWNER:
        raise ValueError("unsupported recording contract identity")
    body = {key: item for key, item in value.items() if key != record_type.hash_field}
    if value[record_type.hash_field] != _hash_body(body):
        raise ValueError(f"{record_type.record_type} checksum mismatch")
    kwargs = {key: value[key] for key in expected}
    enum_fields: dict[type[_HashedRecord], dict[str, type[Enum]]] = {
        VoiceRecordingSessionRevision: {
            "state": RecordingSessionState,
            "capture_mode": CaptureMode,
            "readiness_evaluation_state": ReadinessEvaluationState,
        },
        VoiceSegmentAttemptRevision: {"state": SegmentAttemptState},
        DatasetCandidateRevision: {"state": CandidateState},
        DatasetCandidateReviewDecision: {"decision": ReviewDecision},
    }
    for field, enum_type in enum_fields.get(record_type, {}).items():
        kwargs[field] = enum_type(kwargs[field])
    return record_type(**kwargs)


def parse_record(value: Mapping[str, Any]) -> _HashedRecord:
    if not isinstance(value, Mapping) or value.get("record_type") not in _RECORDS:
        raise ValueError("unknown recording contract record_type")
    return _construct_record(_RECORDS[value["record_type"]], value)


_ALLOWED_SESSION_TRANSITIONS: dict[RecordingSessionState, set[RecordingSessionState]] = {
    RecordingSessionState.DRAFT: {RecordingSessionState.PREFLIGHT_PENDING, RecordingSessionState.CANCELLED},
    RecordingSessionState.PREFLIGHT_PENDING: {RecordingSessionState.PREFLIGHT_BLOCKED, RecordingSessionState.READY, RecordingSessionState.UNKNOWN},
    RecordingSessionState.PREFLIGHT_BLOCKED: {RecordingSessionState.PREFLIGHT_PENDING, RecordingSessionState.CANCELLED, RecordingSessionState.UNKNOWN},
    RecordingSessionState.READY: {RecordingSessionState.CAPTURING, RecordingSessionState.CANCELLED, RecordingSessionState.UNKNOWN},
    RecordingSessionState.CAPTURING: {RecordingSessionState.PAUSED, RecordingSessionState.STOP_REQUESTED, RecordingSessionState.UNKNOWN, RecordingSessionState.FAILED_KNOWN},
    RecordingSessionState.PAUSED: {RecordingSessionState.CAPTURING, RecordingSessionState.STOP_REQUESTED, RecordingSessionState.CANCELLED, RecordingSessionState.CANCELLED_WITH_RETAINED_EVIDENCE, RecordingSessionState.CAPTURED_CANDIDATE, RecordingSessionState.UNKNOWN},
    RecordingSessionState.STOP_REQUESTED: {RecordingSessionState.CAPTURED_CANDIDATE, RecordingSessionState.CANCELLED, RecordingSessionState.CANCELLED_WITH_RETAINED_EVIDENCE, RecordingSessionState.UNKNOWN, RecordingSessionState.FAILED_KNOWN},
    RecordingSessionState.CAPTURED_CANDIDATE: {RecordingSessionState.REVIEW_PENDING},
    RecordingSessionState.REVIEW_PENDING: {RecordingSessionState.APPROVED_FOR_DATASET_ADOPTION, RecordingSessionState.REJECTED},
    RecordingSessionState.APPROVED_FOR_DATASET_ADOPTION: {RecordingSessionState.ADOPTED_TO_DATASET},
    RecordingSessionState.UNKNOWN: set(),
    RecordingSessionState.FAILED_KNOWN: set(),
    RecordingSessionState.REJECTED: set(),
    RecordingSessionState.ADOPTED_TO_DATASET: set(),
    RecordingSessionState.CANCELLED: set(),
    RecordingSessionState.CANCELLED_WITH_RETAINED_EVIDENCE: set(),
}


def validate_session_transition(
    previous: VoiceRecordingSessionRevision,
    current: VoiceRecordingSessionRevision,
    *,
    expected_parent_revision_sha256: str,
) -> None:
    _digest(expected_parent_revision_sha256, "expected_parent_revision_sha256")
    if previous.project_id != current.project_id or previous.recording_session_id != current.recording_session_id:
        raise ValueError("session transition identity mismatch")
    if expected_parent_revision_sha256 != previous.sha256:
        raise ValueError("stale session CAS expectation")
    if current.revision != previous.revision + 1 or current.parent_revision_sha256 != previous.sha256:
        raise ValueError("session revision lineage is not append-only")
    if current.capture_mode is not previous.capture_mode:
        if current.state is not RecordingSessionState.PREFLIGHT_PENDING:
            raise ValueError("capture_mode change requires a new full preflight revision")
        if current.readiness_evaluation_state is not ReadinessEvaluationState.NOT_EVALUATED:
            raise ValueError("capture_mode change cannot retain prior readiness")
        if current.production_admission:
            raise ValueError("capture_mode change cannot retain production admission")
    if current.state not in _ALLOWED_SESSION_TRANSITIONS[previous.state]:
        raise ValueError(f"session transition {previous.state.value}->{current.state.value} is forbidden")


def validate_append_only_revision(
    previous: _HashedRecord,
    current: _HashedRecord,
    *,
    expected_parent_revision_sha256: str,
) -> None:
    """Validate exact-CAS append semantics without performing any persistence."""
    _digest(expected_parent_revision_sha256, "expected_parent_revision_sha256")
    if type(previous) is not type(current):
        raise ValueError("append-only revision type mismatch")
    identity_fields: dict[type[_HashedRecord], tuple[str, ...]] = {
        VoiceRecordingSessionRevision: ("project_id", "recording_session_id"),
        VoiceSegmentAttemptRevision: ("project_id", "recording_session_id", "segment_id", "attempt_id"),
        TeleprompterCheckpointRevision: ("project_id", "recording_session_id", "checkpoint_id"),
        DatasetCandidateRevision: ("project_id", "recording_session_id", "candidate_id"),
        DatasetCandidateReviewDecision: ("project_id", "recording_session_id", "review_decision_id"),
    }
    if any(
        getattr(previous, field) != getattr(current, field)
        for field in identity_fields[type(previous)]
    ):
        raise ValueError("append-only revision identity mismatch")
    if expected_parent_revision_sha256 != previous.sha256:
        raise ValueError("stale append-only CAS expectation")
    if current.revision != previous.revision + 1 or current.parent_revision_sha256 != previous.sha256:  # type: ignore[attr-defined]
        raise ValueError("append-only revision lineage mismatch")


_ALLOWED_ATTEMPT_TRANSITIONS: dict[SegmentAttemptState, set[SegmentAttemptState]] = {
    SegmentAttemptState.PLANNED: {
        SegmentAttemptState.CAPTURING,
        SegmentAttemptState.CANCELLED_SAFE,
        SegmentAttemptState.UNKNOWN,
    },
    SegmentAttemptState.CAPTURING: {
        SegmentAttemptState.INCOMPLETE,
        SegmentAttemptState.CAPTURED,
        SegmentAttemptState.FAILED_KNOWN,
        SegmentAttemptState.UNKNOWN,
    },
    SegmentAttemptState.INCOMPLETE: set(),
    SegmentAttemptState.CAPTURED: set(),
    SegmentAttemptState.FAILED_KNOWN: set(),
    SegmentAttemptState.UNKNOWN: set(),
    SegmentAttemptState.CANCELLED_SAFE: set(),
}


def validate_attempt_transition(
    previous: VoiceSegmentAttemptRevision,
    current: VoiceSegmentAttemptRevision,
    *,
    expected_parent_revision_sha256: str,
) -> None:
    validate_append_only_revision(
        previous,
        current,
        expected_parent_revision_sha256=expected_parent_revision_sha256,
    )
    if current.state not in _ALLOWED_ATTEMPT_TRANSITIONS[previous.state]:
        raise ValueError(f"attempt transition {previous.state.value}->{current.state.value} is forbidden")


_ALLOWED_CANDIDATE_TRANSITIONS: dict[CandidateState, set[CandidateState]] = {
    CandidateState.CAPTURED_CANDIDATE: {CandidateState.REVIEW_PENDING, CandidateState.UNKNOWN},
    CandidateState.REVIEW_PENDING: {
        CandidateState.APPROVED_FOR_ADOPTION,
        CandidateState.REJECTED,
        CandidateState.RERECORD,
        CandidateState.UNKNOWN,
    },
    CandidateState.APPROVED_FOR_ADOPTION: {CandidateState.ADOPTED_TO_DATASET, CandidateState.UNKNOWN},
    CandidateState.ADOPTED_TO_DATASET: set(),
    CandidateState.REJECTED: set(),
    CandidateState.RERECORD: set(),
    CandidateState.UNKNOWN: set(),
}


def validate_candidate_transition(
    previous: DatasetCandidateRevision,
    current: DatasetCandidateRevision,
    *,
    expected_parent_revision_sha256: str,
) -> None:
    validate_append_only_revision(
        previous,
        current,
        expected_parent_revision_sha256=expected_parent_revision_sha256,
    )
    if current.state not in _ALLOWED_CANDIDATE_TRANSITIONS[previous.state]:
        raise ValueError(f"candidate transition {previous.state.value}->{current.state.value} is forbidden")


def validate_checkpoint_transition(
    previous: TeleprompterCheckpointRevision,
    current: TeleprompterCheckpointRevision,
    *,
    expected_parent_revision_sha256: str,
) -> None:
    validate_append_only_revision(
        previous,
        current,
        expected_parent_revision_sha256=expected_parent_revision_sha256,
    )
    allowed = {
        "CURRENT": {"CURRENT", "SUPERSEDED", "UNKNOWN"},
        "SUPERSEDED": set(),
        "UNKNOWN": set(),
    }
    if current.checkpoint_state not in allowed[previous.checkpoint_state]:
        raise ValueError(
            f"checkpoint transition {previous.checkpoint_state}->{current.checkpoint_state} is forbidden"
        )


def validate_resume_attempt(
    previous: VoiceSegmentAttemptRevision,
    current: VoiceSegmentAttemptRevision,
) -> None:
    if previous.state is not SegmentAttemptState.INCOMPLETE:
        raise ValueError("RESUME requires an immutable INCOMPLETE prior attempt")
    if current.state is not SegmentAttemptState.PLANNED:
        raise ValueError("RESUME must target a P-VS-3A issued PLANNED attempt")
    stable = (
        "project_id", "recording_session_id", "segment_id", "cue_id", "sentence_id",
        "source_text_binding_sha256", "sentence_start_anchor",
    )
    if any(getattr(previous, field) != getattr(current, field) for field in stable):
        raise ValueError("RESUME must keep the exact segment/cue/sentence/text/start anchor")
    if current.attempt_number != previous.attempt_number + 1:
        raise ValueError("RESUME attempt_number must increment by one")
    if current.parent_attempt_sha256 != previous.sha256:
        raise ValueError("RESUME parent_attempt_sha256 mismatch")
    if current.revision != 1 or current.parent_revision_sha256 is not None:
        raise ValueError("new attempt identity starts at revision 1")
    if current.attempt_id == previous.attempt_id:
        raise ValueError("RESUME requires a new P-VS-3A attempt identity")


@dataclass(frozen=True, slots=True)
class CaptureCommandAdmissionReport:
    command_id: str
    operation_id: str
    admitted: bool
    reason_codes: tuple[str, ...]
    session_revision_sha256: str
    authorization_sha256: str | None
    dispatch_authorized: bool = False
    dispatch_started: bool = False
    runtime_probe_started: bool = False

    def __post_init__(self) -> None:
        _id(self.command_id, "command_id")
        _id(self.operation_id, "operation_id")
        _bool(self.admitted, "admitted")
        if not isinstance(self.reason_codes, tuple) or not self.reason_codes:
            raise ValueError("reason_codes must be a non-empty tuple")
        for reason in self.reason_codes:
            _id(reason, "reason_code")
        _digest(self.session_revision_sha256, "session_revision_sha256")
        _digest(self.authorization_sha256, "authorization_sha256", nullable=True)
        if self.dispatch_authorized or self.dispatch_started or self.runtime_probe_started:
            raise ValueError("pure admission report cannot dispatch or probe")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "recording_contract_version": VOICE_RECORDING_SESSION_VERSION,
            "report_type": "CaptureCommandAdmissionReport",
            "task_owner": TASK_OWNER,
            "command_id": self.command_id,
            "operation_id": self.operation_id,
            "admitted": self.admitted,
            "reason_codes": list(self.reason_codes),
            "session_revision_sha256": self.session_revision_sha256,
            "authorization_sha256": self.authorization_sha256,
            "dispatch_authorized": self.dispatch_authorized,
            "dispatch_started": self.dispatch_started,
            "runtime_probe_started": self.runtime_probe_started,
        }
        body["capture_command_admission_report_sha256"] = _hash_body(body)
        return body


def evaluate_capture_command(
    session: VoiceRecordingSessionRevision,
    command: Mapping[str, Any],
    *,
    evaluated_at: str,
    consumed_authorization_sha256s: Sequence[str] = (),
    previous_attempt: VoiceSegmentAttemptRevision | None = None,
    new_attempt: VoiceSegmentAttemptRevision | None = None,
) -> CaptureCommandAdmissionReport:
    expected = {
        "command_id", "operation_id", "command", "project_id", "recording_session_id",
        "session_revision_sha256", "capture_mode", "readiness_evaluation_sha256",
        "selected_source_binding_sha256", "consent_current_evaluation_sha256",
        "approved_text_binding_sha256", "execution_authorization_binding",
        "segment_id", "attempt_id", "attempt_number", "parent_attempt_sha256",
        "cue_id", "sentence_id", "source_text_binding_sha256", "sentence_start_anchor",
        "dispatch_started", "runtime_probe_started",
    }
    _expect_keys(command, expected, "CaptureCommand")
    for field in ("command_id", "operation_id", "project_id", "recording_session_id", "segment_id", "attempt_id", "cue_id", "sentence_id"):
        _id(command[field], field)
    kind = _enum(CaptureCommandKind, command["command"], "command")
    mode = _enum(CaptureMode, command["capture_mode"], "capture_mode")
    _integer(command["attempt_number"], "attempt_number", minimum=1)
    _integer(command["sentence_start_anchor"], "sentence_start_anchor")
    for field in (
        "session_revision_sha256", "readiness_evaluation_sha256", "selected_source_binding_sha256",
        "consent_current_evaluation_sha256", "approved_text_binding_sha256", "source_text_binding_sha256",
    ):
        _digest(command[field], field)
    _digest(command["parent_attempt_sha256"], "parent_attempt_sha256", nullable=True)
    if command["dispatch_started"] is not False or command["runtime_probe_started"] is not False:
        raise ValueError("CaptureCommand cannot claim dispatch/probe effects")
    authorization = command["execution_authorization_binding"]
    _validate_authorization(authorization)
    _timestamp(evaluated_at, "evaluated_at")
    reasons: list[str] = []
    if kind not in {CaptureCommandKind.START, CaptureCommandKind.RESUME}:
        reasons.append("COMMAND_NOT_ADMITTED_BY_START_RESUME_GATE")
    if session.state is not RecordingSessionState.READY:
        reasons.append("SESSION_NOT_READY")
    if command["project_id"] != session.project_id or command["recording_session_id"] != session.recording_session_id:
        reasons.append("SESSION_IDENTITY_MISMATCH")
    if command["session_revision_sha256"] != session.sha256:
        reasons.append("SESSION_REVISION_MISMATCH")
    if mode is not session.capture_mode:
        reasons.append("CAPTURE_MODE_MISMATCH")
    expected_readiness = {
        CaptureMode.SYNTHETIC_CONTRACT_TEST: ReadinessEvaluationState.TEST_READY,
        CaptureMode.OWNER_APPROVED_NON_DATASET_TECHNICAL_PROBE: ReadinessEvaluationState.TECHNICAL_PROBE_READY,
        CaptureMode.PRODUCTION_RECORDING: ReadinessEvaluationState.PRODUCTION_READY,
    }[mode]
    if session.readiness_evaluation_state is not expected_readiness:
        reasons.append("READINESS_CLASS_MISMATCH")
    exact_bindings = {
        "readiness_evaluation_sha256": session.readiness_evaluation_sha256,
        "selected_source_binding_sha256": _hash_body(session.selected_source_binding),
        "consent_current_evaluation_sha256": session.consent_current_evaluation["current_evaluation_sha256"],
        "approved_text_binding_sha256": session.approved_text_binding["source_text_binding_sha256"],
    }
    for field, expected_value in exact_bindings.items():
        if command[field] != expected_value:
            reasons.append(f"{field.upper()}_MISMATCH")
    if authorization["contract_state"] != ContractState.BOUND_VERIFIED.value:
        reasons.append("AUTHORIZATION_NOT_BOUND")
        auth_sha = None
    else:
        auth_sha = authorization["authorization_sha256"]
        auth_pairs = {
            "project_id": session.project_id,
            "recording_session_id": session.recording_session_id,
            "session_revision_sha256": session.sha256,
            "capture_mode": session.capture_mode.value,
            "readiness_evaluation_sha256": session.readiness_evaluation_sha256,
            "selected_source_binding_sha256": exact_bindings["selected_source_binding_sha256"],
            "consent_current_evaluation_sha256": exact_bindings["consent_current_evaluation_sha256"],
            "approved_text_binding_sha256": exact_bindings["approved_text_binding_sha256"],
            "scope": kind.value,
        }
        for field, expected_value in auth_pairs.items():
            if authorization[field] != expected_value:
                reasons.append(f"AUTHORIZATION_{field.upper()}_MISMATCH")
        if authorization["authority_kind"] == "APPROVED_SYNTHETIC_TEST_AUTHORITY" and mode is not CaptureMode.SYNTHETIC_CONTRACT_TEST:
            reasons.append("SYNTHETIC_AUTHORITY_MODE_MISMATCH")
        if authorization["authority_kind"] == "OWNER_HUMAN_GATE" and mode is CaptureMode.SYNTHETIC_CONTRACT_TEST:
            reasons.append("OWNER_AUTHORITY_MODE_MISMATCH")
        if authorization["issued_at"] > evaluated_at or authorization["expires_at"] <= evaluated_at:
            reasons.append("AUTHORIZATION_EXPIRED_OR_NOT_YET_VALID")
        if authorization["one_shot"] and auth_sha in set(consumed_authorization_sha256s):
            reasons.append("AUTHORIZATION_REPLAY_REJECTED")
    if mode is CaptureMode.SYNTHETIC_CONTRACT_TEST and (
        session.selected_source_binding.get("source_class") != "SYNTHETIC_VIRTUAL"
        or session.selected_source_binding.get("synthetic_non_biometric") is not True
    ):
        reasons.append("OWNER_VOICE_INJECTION_REJECTED")
    if kind is CaptureCommandKind.RESUME:
        if previous_attempt is None or new_attempt is None:
            reasons.append("RESUME_ATTEMPT_LINEAGE_MISSING")
        else:
            try:
                validate_resume_attempt(previous_attempt, new_attempt)
            except ValueError:
                reasons.append("RESUME_ATTEMPT_LINEAGE_INVALID")
            for field in ("segment_id", "attempt_id", "attempt_number", "parent_attempt_sha256", "cue_id", "sentence_id", "source_text_binding_sha256", "sentence_start_anchor"):
                if command[field] != getattr(new_attempt, field):
                    reasons.append(f"RESUME_{field.upper()}_MISMATCH")
    admitted = not reasons
    return CaptureCommandAdmissionReport(
        command_id=command["command_id"],
        operation_id=command["operation_id"],
        admitted=admitted,
        reason_codes=("ADMITTED_METADATA_ONLY",) if admitted else tuple(dict.fromkeys(reasons)),
        session_revision_sha256=session.sha256,
        authorization_sha256=auth_sha,
    )


def clone_with_new_revision(record: _HashedRecord, **changes: Any) -> _HashedRecord:
    """Create an append-only successor; useful to callers and focused tests."""
    return replace(record, revision=record.revision + 1, parent_revision_sha256=record.sha256, **changes)  # type: ignore[attr-defined]


BODY_AUTHORITY_FLAGS = dict(_BODY_FLAGS)
