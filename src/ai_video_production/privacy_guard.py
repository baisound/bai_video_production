"""TASK-016 body-free Privacy Guard metadata contracts.

This module never reads media/text bodies, runs a detector, mutates canonical
content, sends notifications, publishes, or performs retention/deletion.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, ClassVar, Mapping, Sequence
import copy
import re

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_ID = "bai.task016.privacy-guard.v1"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_REASON_RE = re.compile(r"[A-Z][A-Z0-9_]{1,95}")
_MAX_COORDINATES = 128
_MAX_CLAIMS = 512
_MAX_OPERATIONS = 512


class ContractState(str, Enum):
    CANONICAL_REF_NOT_PROVIDED = "CANONICAL_REF_NOT_PROVIDED"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class PrivacyPolicyScope(str, Enum):
    INTERNAL_REVIEW = "INTERNAL_REVIEW"
    EXPORT = "EXPORT"
    PUBLICATION = "PUBLICATION"
    NOTIFICATION = "NOTIFICATION"


class PrivacySourceKind(str, Enum):
    ASSET_REVISION = "ASSET_REVISION"
    TRANSCRIPT_SEGMENT = "TRANSCRIPT_SEGMENT"
    SRT_CUE = "SRT_CUE"
    NARRATION_TEXT_REVISION = "NARRATION_TEXT_REVISION"
    PRODUCTION_BUNDLE = "PRODUCTION_BUNDLE"


class PrivacyFactState(str, Enum):
    DETECTED = "DETECTED"
    NOT_DETECTED = "NOT_DETECTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    INSUFFICIENT_INPUT = "INSUFFICIENT_INPUT"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class PrivacyFindingKind(str, Enum):
    PERSON_NAME = "PERSON_NAME"
    EMAIL_ADDRESS = "EMAIL_ADDRESS"
    PHONE_NUMBER = "PHONE_NUMBER"
    POSTAL_ADDRESS = "POSTAL_ADDRESS"
    GOVERNMENT_ID = "GOVERNMENT_ID"
    FINANCIAL_IDENTIFIER = "FINANCIAL_IDENTIFIER"
    FACE_IDENTITY = "FACE_IDENTITY"
    VOICE_IDENTITY = "VOICE_IDENTITY"
    PRIVATE_LOCATION = "PRIVATE_LOCATION"
    PRIVATE_PATH = "PRIVATE_PATH"
    CREDENTIAL_LIKE = "CREDENTIAL_LIKE"
    SENSITIVE_NOTIFICATION_CONTENT = "SENSITIVE_NOTIFICATION_CONTENT"
    RIGHTS_RESTRICTION = "RIGHTS_RESTRICTION"
    PROHIBITED_CONTENT = "PROHIBITED_CONTENT"
    POLICY_DEFINED = "POLICY_DEFINED"


class PrivacySeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class CoverageState(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class PrivacyEvaluationDecision(str, Enum):
    PASS = "PASS"
    BLOCK = "BLOCK"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    UNKNOWN = "UNKNOWN"


class RedactionAction(str, Enum):
    MASK = "MASK"
    REMOVE = "REMOVE"
    MUTE = "MUTE"
    BLUR = "BLUR"
    CROP = "CROP"
    REPLACE_TEXT = "REPLACE_TEXT"
    REPLACE_AUDIO = "REPLACE_AUDIO"
    DROP_RANGE = "DROP_RANGE"
    NO_CHANGE_PROPOSED = "NO_CHANGE_PROPOSED"


class HumanPrivacyDecision(str, Enum):
    APPROVE_AS_IS = "APPROVE_AS_IS"
    APPROVE_REDACTION_PLAN = "APPROVE_REDACTION_PLAN"
    REJECT = "REJECT"
    REVISE = "REVISE"


class NotificationDecisionState(str, Enum):
    DO_NOT_NOTIFY = "DO_NOT_NOTIFY"
    PROPOSE_NOTIFICATION = "PROPOSE_NOTIFICATION"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    UNKNOWN = "UNKNOWN"


class PrivacyValidityState(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"
    UNKNOWN = "UNKNOWN"


class PrivacyInvalidationReason(str, Enum):
    ASSET_REVISION_CHANGED = "ASSET_REVISION_CHANGED"
    TRANSCRIPT_REVISION_CHANGED = "TRANSCRIPT_REVISION_CHANGED"
    POLICY_CHANGED = "POLICY_CHANGED"
    DETECTOR_CHANGED = "DETECTOR_CHANGED"
    RIGHTS_CHANGED = "RIGHTS_CHANGED"
    CONSENT_CHANGED = "CONSENT_CHANGED"
    HUMAN_DECISION_CHANGED = "HUMAN_DECISION_CHANGED"
    RETENTION_STATE_CHANGED = "RETENTION_STATE_CHANGED"
    TAMPER_DETECTED = "TAMPER_DETECTED"


class PrivacyPublicationGateDecision(str, Enum):
    READY_FOR_EXTERNAL_HUMAN_GATE = "READY_FOR_EXTERNAL_HUMAN_GATE"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


def _id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    folded = value.casefold()
    if "\\" in value or value.startswith("/") or ".." in value.split("/") or any(
        word in folded for word in ("credential", "password", "secret", "token", "private-key")
    ):
        raise ValueError(f"{name} violates the body-free boundary")
    return value


def _digest(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a SHA-256 digest")
    return validate_sha256(value, field_name=name)


def _time(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{name} must be UTC RFC3339")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be UTC RFC3339") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{name} must be UTC RFC3339")
    return value


def _enum(kind: type[Enum], value: Any, name: str) -> Enum:
    try:
        return kind(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


def _keys(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _unique(values: Any, name: str, limit: int, *, reasons: bool = False) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{name} must be an ordered array")
    result = tuple(values)
    if len(result) > limit or len(set(result)) != len(result):
        raise ValueError(f"{name} must be unique and bounded")
    for item in result:
        if reasons:
            if not isinstance(item, str) or not _REASON_RE.fullmatch(item):
                raise ValueError(f"{name} contains an invalid reason")
        else:
            _id(item, name)
    return result


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return copy.deepcopy(value)


def _hash(body: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(body))
    result["record_sha256"] = sha256_bytes(canonical_json_bytes(result))
    return result


def _check_hash(value: Mapping[str, Any]) -> None:
    supplied = _digest(value["record_sha256"], "record_sha256")
    body = {key: copy.deepcopy(item) for key, item in value.items() if key != "record_sha256"}
    if supplied != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError("record_sha256 mismatch")


def _revision(value: Mapping[str, Any], name: str) -> None:
    revision, parent = value["revision"], value["parent_record_sha256"]
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise ValueError(f"{name} revision must be >= 1")
    _digest(parent, "parent_record_sha256", nullable=True)
    if (revision == 1) != (parent is None):
        raise ValueError(f"{name} parent/revision mismatch")


def _state_binding(value: Mapping[str, Any], name: str) -> None:
    fields = {"contract_state", "decision", "evaluation_ref", "evaluation_sha256", "evaluated_at"}
    _keys(value, fields, name)
    state = _enum(ContractState, value["contract_state"], f"{name}.contract_state")
    nullable = fields - {"contract_state"}
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in nullable):
            raise ValueError(f"{name} unresolved binding invents fields")
        return
    if value["decision"] not in {"PASS", "BLOCKED", "REVIEW_REQUIRED", "REVOKED", "NOT_APPLICABLE", "UNKNOWN", None}:
        raise ValueError(f"{name}.decision is invalid")
    if value["evaluation_ref"] is not None:
        _id(value["evaluation_ref"], f"{name}.evaluation_ref")
    _digest(value["evaluation_sha256"], f"{name}.evaluation_sha256", nullable=True)
    _time(value["evaluated_at"], f"{name}.evaluated_at", nullable=True)
    if state is ContractState.BOUND_VERIFIED and any(value[field] is None for field in nullable):
        raise ValueError(f"{name} BOUND_VERIFIED is incomplete")


def _coordinate(value: Mapping[str, Any]) -> None:
    fields = {
        "coordinate_id", "source_kind", "asset_id", "asset_checksum_sha256",
        "asset_revision_ref", "asset_revision_sha256", "transcript_manifest_ref",
        "transcript_manifest_sha256", "segment_id", "range_start_int",
        "range_end_exclusive_int", "coordinate_sha256",
    }
    _keys(value, fields, "PrivacyInputCoordinate")
    _id(value["coordinate_id"], "coordinate_id")
    kind = _enum(PrivacySourceKind, value["source_kind"], "source_kind")
    for field in ("asset_id", "asset_revision_ref"):
        _id(value[field], field)
    for field in ("asset_checksum_sha256", "asset_revision_sha256"):
        _digest(value[field], field)
    if value["transcript_manifest_ref"] is not None:
        _id(value["transcript_manifest_ref"], "transcript_manifest_ref")
    _digest(value["transcript_manifest_sha256"], "transcript_manifest_sha256", nullable=True)
    if value["segment_id"] is not None:
        _id(value["segment_id"], "segment_id")
    start, end = value["range_start_int"], value["range_end_exclusive_int"]
    if kind is PrivacySourceKind.ASSET_REVISION:
        if any(item is not None for item in (
            value["transcript_manifest_ref"], value["transcript_manifest_sha256"],
            value["segment_id"], start, end,
        )):
            raise ValueError("whole Asset coordinate cannot invent a sub-range")
    else:
        if any(item is None for item in (
            value["transcript_manifest_ref"], value["transcript_manifest_sha256"], start, end,
        )):
            raise ValueError("ranged coordinate is incomplete")
        if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
            raise ValueError("range must be canonical half-open integers")
    supplied = _digest(value["coordinate_sha256"], "coordinate_sha256")
    body = {key: copy.deepcopy(item) for key, item in value.items() if key != "coordinate_sha256"}
    if supplied != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError("coordinate_sha256 mismatch")


def create_coordinate(**fields: Any) -> dict[str, Any]:
    result = copy.deepcopy(fields)
    result["coordinate_sha256"] = sha256_bytes(canonical_json_bytes(result))
    _coordinate(result)
    return result


def _operation(value: Mapping[str, Any]) -> None:
    fields = {"operation_id", "coordinate_sha256", "action", "replacement_digest", "reason_codes", "operation_sha256"}
    _keys(value, fields, "RedactionOperation")
    _id(value["operation_id"], "operation_id")
    _digest(value["coordinate_sha256"], "coordinate_sha256")
    action = _enum(RedactionAction, value["action"], "action")
    replacement = action in {RedactionAction.REPLACE_TEXT, RedactionAction.REPLACE_AUDIO}
    if replacement != (value["replacement_digest"] is not None):
        raise ValueError("replacement_digest nullability mismatch")
    _digest(value["replacement_digest"], "replacement_digest", nullable=True)
    _unique(value["reason_codes"], "reason_codes", 64, reasons=True)
    supplied = _digest(value["operation_sha256"], "operation_sha256")
    body = {key: copy.deepcopy(item) for key, item in value.items() if key != "operation_sha256"}
    if supplied != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError("operation_sha256 mismatch")


def create_redaction_operation(**fields: Any) -> dict[str, Any]:
    result = copy.deepcopy(fields)
    result["operation_sha256"] = sha256_bytes(canonical_json_bytes(result))
    _operation(result)
    return result


def _policy(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "policy_id", "revision", "parent_record_sha256", "scope",
        "enabled_finding_kinds", "block_severities", "review_severities",
        "max_claim_age_seconds", "authority_ref", "authority_sha256", "effective_at",
        "expires_at", "record_sha256",
    }
    _keys(value, fields, "PrivacyPolicyRevision")
    _id(value["policy_id"], "policy_id")
    _revision(value, "policy")
    _enum(PrivacyPolicyScope, value["scope"], "scope")
    kinds = _unique(value["enabled_finding_kinds"], "enabled_finding_kinds", 32)
    if not kinds:
        raise ValueError("policy needs an enabled finding kind")
    for item in kinds:
        _enum(PrivacyFindingKind, item, "enabled_finding_kind")
    for field in ("block_severities", "review_severities"):
        for item in _unique(value[field], field, 5):
            _enum(PrivacySeverity, item, field)
    if set(value["block_severities"]) & set(value["review_severities"]):
        raise ValueError("block/review severities must be disjoint")
    age = value["max_claim_age_seconds"]
    if isinstance(age, bool) or not isinstance(age, int) or not 1 <= age <= 31_536_000:
        raise ValueError("max_claim_age_seconds is outside the cap")
    _id(value["authority_ref"], "authority_ref")
    _digest(value["authority_sha256"], "authority_sha256")
    effective = _time(value["effective_at"], "effective_at")
    expires = _time(value["expires_at"], "expires_at", nullable=True)
    if expires is not None and expires <= effective:
        raise ValueError("expires_at must follow effective_at")


def _input(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "binding_id", "production_job_id", "revision", "parent_record_sha256",
        "coordinates", "rights_binding", "consent_binding", "body_persisted", "record_sha256",
    }
    _keys(value, fields, "PrivacyInputBinding")
    _id(value["binding_id"], "binding_id")
    _id(value["production_job_id"], "production_job_id")
    _revision(value, "input")
    coordinates = value["coordinates"]
    if not isinstance(coordinates, (list, tuple)) or not 1 <= len(coordinates) <= _MAX_COORDINATES:
        raise ValueError("coordinates must be non-empty and bounded")
    for item in coordinates:
        _coordinate(item)
    ids = [item["coordinate_id"] for item in coordinates]
    hashes = [item["coordinate_sha256"] for item in coordinates]
    if len(ids) != len(set(ids)) or len(hashes) != len(set(hashes)):
        raise ValueError("coordinates must be unique")
    _state_binding(value["rights_binding"], "rights_binding")
    _state_binding(value["consent_binding"], "consent_binding")
    if value["body_persisted"] is not False:
        raise ValueError("PrivacyInputBinding must be body-free")


def _detector(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "contract_state", "profile_ref", "profile_sha256", "detector_id",
        "detector_version", "code_sha256", "model_ref", "model_sha256",
        "supported_finding_kinds", "capability_state", "license_state", "evidence_ref",
        "evidence_sha256", "execution_authorized", "execution_started", "record_sha256",
    }
    _keys(value, fields, "PrivacyDetectorProfileBinding")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    if value["execution_authorized"] is not False or value["execution_started"] is not False:
        raise ValueError("detector binding cannot authorize execution")
    nullable = fields - {
        "record_type", "contract_state", "supported_finding_kinds", "execution_authorized",
        "execution_started", "record_sha256",
    }
    kinds = _unique(value["supported_finding_kinds"], "supported_finding_kinds", 32)
    for item in kinds:
        _enum(PrivacyFindingKind, item, "supported_finding_kind")
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if kinds or any(value[field] is not None for field in nullable):
            raise ValueError("unresolved detector invents canonical fields")
        return
    for field in ("profile_ref", "detector_id", "detector_version", "model_ref", "evidence_ref"):
        if value[field] is not None:
            _id(value[field], field)
    for field in ("profile_sha256", "code_sha256", "model_sha256", "evidence_sha256"):
        _digest(value[field], field, nullable=True)
    if value["capability_state"] not in {"VERIFIED", "FAILED", "UNKNOWN", None}:
        raise ValueError("capability_state is invalid")
    if value["license_state"] not in {"PASS", "LEGAL_REVIEW_REQUIRED", "REVOKED", "UNKNOWN", None}:
        raise ValueError("license_state is invalid")
    if state is ContractState.BOUND_VERIFIED and (not kinds or any(value[field] is None for field in nullable)):
        raise ValueError("BOUND_VERIFIED detector is incomplete")


def _claim(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "claim_id", "input_binding_sha256", "coordinate_sha256",
        "detector_profile_sha256", "finding_kind", "fact_state", "severity",
        "coverage_state", "reason_codes", "confidence_millionths", "private_evidence_ref",
        "private_evidence_sha256", "matched_content_sha256", "observed_at",
        "body_persisted", "record_sha256",
    }
    _keys(value, fields, "PrivacyEvidenceClaim")
    _id(value["claim_id"], "claim_id")
    for field in ("input_binding_sha256", "coordinate_sha256", "detector_profile_sha256"):
        _digest(value[field], field)
    _enum(PrivacyFindingKind, value["finding_kind"], "finding_kind")
    fact = _enum(PrivacyFactState, value["fact_state"], "fact_state")
    _enum(PrivacySeverity, value["severity"], "severity")
    _enum(CoverageState, value["coverage_state"], "coverage_state")
    _unique(value["reason_codes"], "reason_codes", 64, reasons=True)
    confidence = value["confidence_millionths"]
    if confidence is not None and (
        isinstance(confidence, bool) or not isinstance(confidence, int) or not 0 <= confidence <= 1_000_000
    ):
        raise ValueError("confidence_millionths must be 0..1000000")
    if value["private_evidence_ref"] is not None:
        _id(value["private_evidence_ref"], "private_evidence_ref")
    _digest(value["private_evidence_sha256"], "private_evidence_sha256", nullable=True)
    _digest(value["matched_content_sha256"], "matched_content_sha256", nullable=True)
    if (value["private_evidence_ref"] is None) != (value["private_evidence_sha256"] is None):
        raise ValueError("private Evidence ref/hash must be paired")
    if fact is not PrivacyFactState.DETECTED and value["matched_content_sha256"] is not None:
        raise ValueError("only DETECTED claims may bind matched-content digest")
    _time(value["observed_at"], "observed_at")
    if value["body_persisted"] is not False:
        raise ValueError("PrivacyEvidenceClaim must be body-free")


def _evaluation(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "evaluation_id", "policy_sha256", "input_binding_sha256",
        "detector_profile_hashes", "claim_hashes", "decision", "reason_codes",
        "evaluated_at", "validity_state", "record_sha256",
    }
    _keys(value, fields, "PrivacyEvaluationReceipt")
    _id(value["evaluation_id"], "evaluation_id")
    _digest(value["policy_sha256"], "policy_sha256")
    _digest(value["input_binding_sha256"], "input_binding_sha256")
    for field, limit in (("detector_profile_hashes", 64), ("claim_hashes", _MAX_CLAIMS)):
        for item in _unique(value[field], field, limit):
            _digest(item, field)
    _enum(PrivacyEvaluationDecision, value["decision"], "decision")
    _unique(value["reason_codes"], "reason_codes", 64, reasons=True)
    _time(value["evaluated_at"], "evaluated_at")
    _enum(PrivacyValidityState, value["validity_state"], "validity_state")


def _plan(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "plan_id", "revision", "parent_record_sha256", "input_binding_sha256",
        "evaluation_sha256", "operations", "proposal_only", "mutation_started",
        "asset_modified", "transcript_modified", "srt_modified", "record_sha256",
    }
    _keys(value, fields, "RedactionPlanRevision")
    _id(value["plan_id"], "plan_id")
    _revision(value, "redaction plan")
    _digest(value["input_binding_sha256"], "input_binding_sha256")
    _digest(value["evaluation_sha256"], "evaluation_sha256")
    operations = value["operations"]
    if not isinstance(operations, (list, tuple)) or len(operations) > _MAX_OPERATIONS:
        raise ValueError("operations must be bounded")
    for item in operations:
        _operation(item)
    ids = [item["operation_id"] for item in operations]
    coordinates = [item["coordinate_sha256"] for item in operations]
    if len(ids) != len(set(ids)) or len(coordinates) != len(set(coordinates)):
        raise ValueError("operations duplicate identity or coordinate")
    if value["proposal_only"] is not True or any(
        value[field] is not False for field in ("mutation_started", "asset_modified", "transcript_modified", "srt_modified")
    ):
        raise ValueError("redaction plan is proposal-only and non-mutating")


def _human(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "contract_state", "decision_id", "decision_revision", "decision_sha256",
        "input_binding_sha256", "policy_sha256", "evaluation_sha256", "redaction_plan_sha256",
        "reviewer_kind", "decision", "decided_at", "evidence_ref", "evidence_sha256",
        "record_sha256",
    }
    _keys(value, fields, "HumanPrivacyReviewBinding")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    nullable = fields - {"record_type", "contract_state", "record_sha256"}
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in nullable):
            raise ValueError("unresolved Human binding invents fields")
        return
    for field in ("decision_id", "evidence_ref"):
        if value[field] is not None:
            _id(value[field], field)
    for field in (
        "decision_sha256", "input_binding_sha256", "policy_sha256", "evaluation_sha256",
        "redaction_plan_sha256", "evidence_sha256",
    ):
        _digest(value[field], field, nullable=True)
    revision = value["decision_revision"]
    if revision is not None and (isinstance(revision, bool) or not isinstance(revision, int) or revision < 1):
        raise ValueError("decision_revision must be >= 1")
    if value["reviewer_kind"] not in {"HUMAN", None}:
        raise ValueError("reviewer_kind must be HUMAN")
    if value["decision"] is not None:
        _enum(HumanPrivacyDecision, value["decision"], "decision")
    _time(value["decided_at"], "decided_at", nullable=True)
    if state is ContractState.BOUND_VERIFIED:
        required = nullable - {"redaction_plan_sha256"}
        if any(value[field] is None for field in required):
            raise ValueError("BOUND_VERIFIED Human binding is incomplete")
        if value["decision"] == HumanPrivacyDecision.APPROVE_REDACTION_PLAN.value and value["redaction_plan_sha256"] is None:
            raise ValueError("approved redaction plan requires its exact digest")
        if value["decision"] == HumanPrivacyDecision.APPROVE_AS_IS.value and value["redaction_plan_sha256"] is not None:
            raise ValueError("APPROVE_AS_IS cannot bind a redaction plan")


def _notification(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "decision_id", "input_binding_sha256", "evaluation_sha256", "state",
        "reason_codes", "human_review_sha256", "notification_body_persisted",
        "send_authorized", "sent", "record_sha256",
    }
    _keys(value, fields, "NotificationDecision")
    _id(value["decision_id"], "decision_id")
    _digest(value["input_binding_sha256"], "input_binding_sha256")
    _digest(value["evaluation_sha256"], "evaluation_sha256")
    _enum(NotificationDecisionState, value["state"], "state")
    _unique(value["reason_codes"], "reason_codes", 64, reasons=True)
    _digest(value["human_review_sha256"], "human_review_sha256", nullable=True)
    if value["notification_body_persisted"] is not False or value["send_authorized"] is not False or value["sent"] is not False:
        raise ValueError("notification record cannot carry or send a body")


def _invalidation(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "receipt_id", "target_record_type", "target_ref", "target_sha256",
        "reason", "invalidated_at", "replacement_ref", "replacement_sha256",
        "physical_delete_started", "record_sha256",
    }
    _keys(value, fields, "PrivacyInvalidationReceipt")
    for field in ("receipt_id", "target_record_type", "target_ref"):
        _id(value[field], field)
    _digest(value["target_sha256"], "target_sha256")
    _enum(PrivacyInvalidationReason, value["reason"], "reason")
    _time(value["invalidated_at"], "invalidated_at")
    if value["replacement_ref"] is not None:
        _id(value["replacement_ref"], "replacement_ref")
    _digest(value["replacement_sha256"], "replacement_sha256", nullable=True)
    if (value["replacement_ref"] is None) != (value["replacement_sha256"] is None):
        raise ValueError("replacement ref/hash must be paired")
    if value["physical_delete_started"] is not False:
        raise ValueError("invalidation is not physical deletion")


def _publication(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "gate_id", "input_binding_sha256", "policy_sha256", "evaluation_sha256",
        "redaction_plan_sha256", "human_review_sha256", "invalidation_receipt_hashes",
        "validity_state", "decision", "reason_codes", "evaluated_at", "publication_started",
        "release_deploy_started", "record_sha256",
    }
    _keys(value, fields, "PrivacyPublicationGateBinding")
    _id(value["gate_id"], "gate_id")
    for field in ("input_binding_sha256", "policy_sha256", "evaluation_sha256"):
        _digest(value[field], field)
    _digest(value["redaction_plan_sha256"], "redaction_plan_sha256", nullable=True)
    _digest(value["human_review_sha256"], "human_review_sha256", nullable=True)
    for item in _unique(value["invalidation_receipt_hashes"], "invalidation_receipt_hashes", 64):
        _digest(item, "invalidation_receipt_hash")
    _enum(PrivacyValidityState, value["validity_state"], "validity_state")
    _enum(PrivacyPublicationGateDecision, value["decision"], "decision")
    _unique(value["reason_codes"], "reason_codes", 64, reasons=True)
    _time(value["evaluated_at"], "evaluated_at")
    if value["publication_started"] is not False or value["release_deploy_started"] is not False:
        raise ValueError("publication gate cannot start an effect")


_VALIDATORS = {
    "PrivacyPolicyRevision": _policy,
    "PrivacyInputBinding": _input,
    "PrivacyDetectorProfileBinding": _detector,
    "PrivacyEvidenceClaim": _claim,
    "PrivacyEvaluationReceipt": _evaluation,
    "RedactionPlanRevision": _plan,
    "HumanPrivacyReviewBinding": _human,
    "NotificationDecision": _notification,
    "PrivacyInvalidationReceipt": _invalidation,
    "PrivacyPublicationGateBinding": _publication,
}


@dataclass(frozen=True, slots=True)
class _Record:
    data: Mapping[str, Any]
    RECORD_TYPE: ClassVar[str]

    @classmethod
    def create(cls, **fields: Any) -> "_Record":
        return cls.from_dict(_hash({"record_type": cls.RECORD_TYPE, **copy.deepcopy(fields)}))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "_Record":
        if value.get("record_type") != cls.RECORD_TYPE:
            raise ValueError(f"record_type must be {cls.RECORD_TYPE}")
        _VALIDATORS[cls.RECORD_TYPE](value)
        _check_hash(value)
        return cls(_freeze(value))

    @property
    def record_sha256(self) -> str:
        return self.data["record_sha256"]

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.data)


class PrivacyPolicyRevision(_Record): RECORD_TYPE = "PrivacyPolicyRevision"
class PrivacyInputBinding(_Record): RECORD_TYPE = "PrivacyInputBinding"
class PrivacyDetectorProfileBinding(_Record): RECORD_TYPE = "PrivacyDetectorProfileBinding"
class PrivacyEvidenceClaim(_Record): RECORD_TYPE = "PrivacyEvidenceClaim"
class PrivacyEvaluationReceipt(_Record): RECORD_TYPE = "PrivacyEvaluationReceipt"
class RedactionPlanRevision(_Record): RECORD_TYPE = "RedactionPlanRevision"
class HumanPrivacyReviewBinding(_Record): RECORD_TYPE = "HumanPrivacyReviewBinding"
class NotificationDecision(_Record): RECORD_TYPE = "NotificationDecision"
class PrivacyInvalidationReceipt(_Record): RECORD_TYPE = "PrivacyInvalidationReceipt"
class PrivacyPublicationGateBinding(_Record): RECORD_TYPE = "PrivacyPublicationGateBinding"


def validate_record(value: Mapping[str, Any]) -> _Record:
    classes = {cls.RECORD_TYPE: cls for cls in (
        PrivacyPolicyRevision, PrivacyInputBinding, PrivacyDetectorProfileBinding,
        PrivacyEvidenceClaim, PrivacyEvaluationReceipt, RedactionPlanRevision,
        HumanPrivacyReviewBinding, NotificationDecision, PrivacyInvalidationReceipt,
        PrivacyPublicationGateBinding,
    )}
    try:
        return classes[value.get("record_type")].from_dict(value)
    except (KeyError, TypeError) as exc:
        raise ValueError("unknown Privacy Guard record_type") from exc


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value[:-1] + "+00:00")


def evaluate_privacy(
    *, evaluation_id: str, policy: PrivacyPolicyRevision, input_binding: PrivacyInputBinding,
    detector_profiles: Sequence[PrivacyDetectorProfileBinding],
    claims: Sequence[PrivacyEvidenceClaim], evaluated_at: str,
) -> PrivacyEvaluationReceipt:
    """Classify exact external facts; missing/unsupported evidence stays UNKNOWN."""
    _id(evaluation_id, "evaluation_id")
    now_text = _time(evaluated_at, "evaluated_at")
    now = _dt(now_text)
    policy_data, input_data = policy.to_dict(), input_binding.to_dict()
    reasons: list[str] = []
    blocked = False
    unknown = False
    review = False
    if policy_data["effective_at"] > now_text or (
        policy_data["expires_at"] is not None and policy_data["expires_at"] <= now_text
    ):
        unknown = True
        reasons.append("POLICY_NOT_CURRENT")
    for name in ("rights_binding", "consent_binding"):
        binding = input_data[name]
        state = ContractState(binding["contract_state"])
        if state is not ContractState.BOUND_VERIFIED:
            unknown = True
            reasons.append(f"{name.upper()}_{state.value}")
        elif binding["decision"] in {"BLOCKED", "REVOKED"}:
            blocked = True
            reasons.append(f"{name.upper()}_{binding['decision']}")
        elif binding["decision"] in {"REVIEW_REQUIRED", "UNKNOWN"}:
            unknown = True
            reasons.append(f"{name.upper()}_{binding['decision']}")
    profiles = {item.record_sha256: item.to_dict() for item in detector_profiles}
    if len(profiles) != len(detector_profiles) or len(profiles) > 64:
        raise ValueError("detector profiles must be unique and bounded")
    coordinate_hashes = {item["coordinate_sha256"] for item in input_data["coordinates"]}
    enabled = set(policy_data["enabled_finding_kinds"])
    if len(claims) > _MAX_CLAIMS:
        raise ValueError("claims exceed the cap")
    pairs: set[tuple[str, str]] = set()
    for claim in claims:
        data = claim.to_dict()
        if data["input_binding_sha256"] != input_binding.record_sha256 or data["coordinate_sha256"] not in coordinate_hashes:
            raise ValueError("claim/input coordinate mismatch")
        if data["finding_kind"] not in enabled:
            raise ValueError("claim is outside the policy")
        pair = (data["coordinate_sha256"], data["finding_kind"])
        if pair in pairs:
            raise ValueError("duplicate coordinate/finding claim")
        pairs.add(pair)
        profile = profiles.get(data["detector_profile_sha256"])
        if profile is None:
            raise ValueError("claim references an unbound detector")
        if (
            profile["contract_state"] != ContractState.BOUND_VERIFIED.value
            or profile["capability_state"] != "VERIFIED"
            or profile["license_state"] != "PASS"
            or data["finding_kind"] not in profile["supported_finding_kinds"]
        ):
            unknown = True
            reasons.append("DETECTOR_NOT_ADMITTED")
        fact = PrivacyFactState(data["fact_state"])
        coverage = CoverageState(data["coverage_state"])
        if now.timestamp() - _dt(data["observed_at"]).timestamp() > policy_data["max_claim_age_seconds"]:
            unknown = True
            reasons.append("CLAIM_STALE")
        elif fact is PrivacyFactState.DETECTED:
            severity = PrivacySeverity(data["severity"])
            if severity.value in policy_data["block_severities"]:
                blocked = True
                reasons.append("BLOCKING_FINDING_DETECTED")
            elif severity.value in policy_data["review_severities"] or severity is PrivacySeverity.UNKNOWN:
                review = True
                reasons.append("FINDING_REQUIRES_HUMAN_REVIEW")
        elif fact is PrivacyFactState.NOT_DETECTED and coverage is CoverageState.COMPLETE:
            pass
        else:
            unknown = True
            reasons.append(f"FACT_{fact.value}")
    if len(pairs) != len(coordinate_hashes) * len(enabled):
        unknown = True
        reasons.append("CLAIM_COVERAGE_INCOMPLETE")
    reasons = list(dict.fromkeys(reasons))
    decision = (
        PrivacyEvaluationDecision.BLOCK if blocked
        else PrivacyEvaluationDecision.UNKNOWN if unknown
        else PrivacyEvaluationDecision.HUMAN_REVIEW_REQUIRED if review
        else PrivacyEvaluationDecision.PASS
    )
    return PrivacyEvaluationReceipt.create(
        evaluation_id=evaluation_id, policy_sha256=policy.record_sha256,
        input_binding_sha256=input_binding.record_sha256,
        detector_profile_hashes=[item.record_sha256 for item in detector_profiles],
        claim_hashes=[item.record_sha256 for item in claims], decision=decision.value,
        reason_codes=reasons, evaluated_at=evaluated_at,
        validity_state=PrivacyValidityState.CURRENT.value,
    )


def classify_notification(
    *, decision_id: str, input_binding: PrivacyInputBinding,
    evaluation: PrivacyEvaluationReceipt, human_review: HumanPrivacyReviewBinding | None = None,
) -> NotificationDecision:
    data = evaluation.to_dict()
    if data["input_binding_sha256"] != input_binding.record_sha256:
        raise ValueError("evaluation/input mismatch")
    reasons: list[str] = []
    if data["validity_state"] != PrivacyValidityState.CURRENT.value or data["decision"] == PrivacyEvaluationDecision.UNKNOWN.value:
        state = NotificationDecisionState.UNKNOWN
        reasons.append("PRIVACY_EVALUATION_UNKNOWN_OR_STALE")
    elif data["decision"] == PrivacyEvaluationDecision.PASS.value:
        state = NotificationDecisionState.DO_NOT_NOTIFY
    else:
        state = NotificationDecisionState.HUMAN_REVIEW_REQUIRED
        reasons.append("PRIVACY_HUMAN_REVIEW_REQUIRED")
    return NotificationDecision.create(
        decision_id=decision_id, input_binding_sha256=input_binding.record_sha256,
        evaluation_sha256=evaluation.record_sha256, state=state.value,
        reason_codes=reasons,
        human_review_sha256=None if human_review is None else human_review.record_sha256,
        notification_body_persisted=False, send_authorized=False, sent=False,
    )


def classify_publication_gate(
    *, gate_id: str, input_binding: PrivacyInputBinding, policy: PrivacyPolicyRevision,
    evaluation: PrivacyEvaluationReceipt, human_review: HumanPrivacyReviewBinding | None,
    redaction_plan: RedactionPlanRevision | None,
    invalidations: Sequence[PrivacyInvalidationReceipt], evaluated_at: str,
) -> PrivacyPublicationGateBinding:
    data = evaluation.to_dict()
    if data["input_binding_sha256"] != input_binding.record_sha256 or data["policy_sha256"] != policy.record_sha256:
        raise ValueError("publication exact binding mismatch")
    reasons: list[str] = []
    validity = PrivacyValidityState.CURRENT
    if invalidations:
        validity = PrivacyValidityState.INVALIDATED
        decision = PrivacyPublicationGateDecision.BLOCKED
        reasons.append("PRIVACY_RECORD_INVALIDATED")
    elif data["validity_state"] != PrivacyValidityState.CURRENT.value or data["decision"] == PrivacyEvaluationDecision.UNKNOWN.value:
        validity = PrivacyValidityState.UNKNOWN
        decision = PrivacyPublicationGateDecision.UNKNOWN
        reasons.append("PRIVACY_EVALUATION_UNKNOWN_OR_STALE")
    elif data["decision"] == PrivacyEvaluationDecision.BLOCK.value:
        decision = PrivacyPublicationGateDecision.BLOCKED
        reasons.append("PRIVACY_POLICY_BLOCK")
    elif human_review is None:
        decision = PrivacyPublicationGateDecision.BLOCKED
        reasons.append("HUMAN_PRIVACY_REVIEW_NOT_BOUND")
    else:
        review = human_review.to_dict()
        exact = (
            review["contract_state"] == ContractState.BOUND_VERIFIED.value
            and review["input_binding_sha256"] == input_binding.record_sha256
            and review["policy_sha256"] == policy.record_sha256
            and review["evaluation_sha256"] == evaluation.record_sha256
        )
        approve_as_is = review["decision"] == HumanPrivacyDecision.APPROVE_AS_IS.value and redaction_plan is None
        approve_plan = (
            review["decision"] == HumanPrivacyDecision.APPROVE_REDACTION_PLAN.value
            and redaction_plan is not None
            and review["redaction_plan_sha256"] == redaction_plan.record_sha256
        )
        if exact and (approve_as_is or approve_plan):
            decision = PrivacyPublicationGateDecision.READY_FOR_EXTERNAL_HUMAN_GATE
        else:
            decision = PrivacyPublicationGateDecision.BLOCKED
            reasons.append("HUMAN_PRIVACY_REVIEW_MISMATCH")
    return PrivacyPublicationGateBinding.create(
        gate_id=gate_id, input_binding_sha256=input_binding.record_sha256,
        policy_sha256=policy.record_sha256, evaluation_sha256=evaluation.record_sha256,
        redaction_plan_sha256=None if redaction_plan is None else redaction_plan.record_sha256,
        human_review_sha256=None if human_review is None else human_review.record_sha256,
        invalidation_receipt_hashes=[item.record_sha256 for item in invalidations],
        validity_state=validity.value, decision=decision.value, reason_codes=reasons,
        evaluated_at=evaluated_at, publication_started=False, release_deploy_started=False,
    )


def project_private(record: _Record) -> dict[str, Any]:
    return record.to_dict()


def project_public(record: _Record) -> dict[str, Any]:
    data = record.to_dict()
    result: dict[str, Any] = {
        "record_type": data["record_type"], "record_sha256": data["record_sha256"],
        "body_included": False, "private_coordinates_included": False,
        "low_count_details_included": False,
    }
    for field in ("decision", "state", "validity_state", "proposal_only", "publication_started", "send_authorized", "sent"):
        if field in data:
            result[field] = data[field]
    if "reason_codes" in data:
        result["reason_codes"] = list(data["reason_codes"])
    return result


EFFECT_SURFACE = MappingProxyType({
    "filesystem_io": False, "body_access": False, "detector_execution": False,
    "asset_transcript_srt_mutation": False, "redaction_execution": False,
    "notification_send": False, "publication": False, "retention_delete": False,
    "provider_model_runtime": False, "release_deploy_production": False,
})


__all__ = [
    "ContractState", "CoverageState", "EFFECT_SURFACE", "HumanPrivacyDecision",
    "HumanPrivacyReviewBinding", "NotificationDecision", "NotificationDecisionState",
    "PrivacyDetectorProfileBinding", "PrivacyEvaluationDecision", "PrivacyEvaluationReceipt",
    "PrivacyEvidenceClaim", "PrivacyFactState", "PrivacyFindingKind", "PrivacyInputBinding",
    "PrivacyInvalidationReason", "PrivacyInvalidationReceipt", "PrivacyPolicyRevision",
    "PrivacyPolicyScope", "PrivacyPublicationGateBinding", "PrivacyPublicationGateDecision",
    "PrivacySeverity", "PrivacySourceKind", "PrivacyValidityState", "RedactionAction",
    "RedactionPlanRevision", "classify_notification", "classify_publication_gate",
    "create_coordinate", "create_redaction_operation", "evaluate_privacy", "project_private",
    "project_public", "validate_record",
]
