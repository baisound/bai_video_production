"""TASK-102 pure Project Manifest Secure Transaction contracts.

This module contains strict body-free parsers, a deterministic transition
machine, and an injected in-memory fake port.  It deliberately contains no
filesystem, process, socket, Windows service, ACL, clock, or Project-store
implementation.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
import json
import math
import re
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


PROTOCOL_VERSION = "PMST_V1"
MAX_RECORD_BYTES = 131_072
MAX_BODY_ENVELOPE_BYTES = 4_194_304
MAX_JSON_DEPTH = 16

_DOMAINS = {
    "intent": b"BAI:TASK-102:PMST-OPERATION-INTENT:V1\0",
    "request": b"BAI:TASK-102:PMST-PRIVATE-REQUEST:V1\0",
    "phase": b"BAI:TASK-102:PMST-PRIVATE-PHASE-RESULT:V1\0",
    "enrollment": b"BAI:TASK-102:PMST-ENROLLMENT:V1\0",
    "participant_plan": b"BAI:TASK-102:PMST-PARTICIPANT-PLAN:V1\0",
    "participant": b"BAI:TASK-102:PMST-PARTICIPANT-RECEIPT:V1\0",
    "profile_validation": b"BAI:TASK-102:PMST-PROFILE-VALIDATION-RECEIPT:V1\0",
    "journal": b"BAI:TASK-102:PMST-TRANSACTION-JOURNAL:V1\0",
    "witness": b"BAI:TASK-102:PMST-OPERATION-WITNESS:V1\0",
    "public": b"BAI:TASK-102:PMST-PUBLIC-OPERATION-STATUS:V1\0",
}

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_TIMESTAMP_RE = re.compile(
    r"^(?:(?:(?!0000)[0-9]{4})-(?:(?:0[13578]|1[02])-(?:0[1-9]|[12][0-9]|3[01])|"
    r"(?:0[469]|11)-(?:0[1-9]|[12][0-9]|30)|02-(?:0[1-9]|1[0-9]|2[0-8]))|"
    r"(?:(?!0000)(?:[0-9]{2}(?:0[48]|[2468][048]|[13579][26])|"
    r"(?:0[48]|[2468][048]|[13579][26])00))-02-29)"
    r"T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]{1,6})?Z$"
)

OPERATION_KINDS = frozenset(
    {
        "MANIFEST_CREATE_V1",
        "MANIFEST_TRANSITION_V1",
        "CONTROL_OBJECT_CAS_V1",
        "CONTROL_APPEND_CHAIN_V1",
        "CONTROL_RECOVERY_OBJECT_V1",
        "CONTROL_SNAPSHOT_SET_V1",
        "PROJECT_READ_LEASE_V1",
        "QUERY_OPERATION_V1",
    }
)
MUTATING_KINDS = OPERATION_KINDS - {"PROJECT_READ_LEASE_V1", "QUERY_OPERATION_V1"}
MANIFEST_KINDS = frozenset({"MANIFEST_CREATE_V1", "MANIFEST_TRANSITION_V1"})
FAILURE_CLASSES = frozenset(
    {
        "IO_FAILURE",
        "CORRUPT_RECORD",
        "DIGEST_MISMATCH",
        "AUTHENTICITY_UNPROVEN",
        "SECURITY_BINDING_DRIFT",
        "AMBIGUOUS_DUPLICATE",
    }
)
OBSERVATIONS = frozenset({"NOT_OBSERVED", "COMMITTED", "NOT_COMMITTED", "UNKNOWN"})

_INTENT_FIELDS = {
    "protocol_version",
    "record_type",
    "project_registration_id",
    "operation_id",
    "operation_kind",
    "operation_profile_id",
    "caller_task_id",
    "caller_build_sha256",
    "caller_policy_sha256",
    "requested_at",
    "expires_at",
    "payload",
    "intent_sha256",
}
_REQUEST_FIELDS = {
    "protocol_version",
    "record_type",
    "broker_instance_id",
    "session_id",
    "request_nonce_id",
    "intent",
    "request_sha256",
}
_PHASE_FIELDS = {
    "protocol_version",
    "record_type",
    "broker_instance_id",
    "session_id",
    "project_registration_id",
    "operation_id",
    "operation_kind",
    "operation_profile_id",
    "intent_sha256",
    "request_sha256",
    "phase",
    "phase_status",
    "manifest_commit_observation",
    "effect_count",
    "reason_code",
    "payload",
    "phase_result_sha256",
}
_PARTICIPANT_FIELDS = {
    "record_type",
    "protocol_version",
    "operation_id",
    "participant_id",
    "plan_sha256",
    "participant_phase",
    "participant_status",
    "object_observations",
    "effect_observation",
    "receipt_sequence",
    "receipt_sha256",
}
_ENROLLMENT_FIELDS = {
    "record_type",
    "protocol_version",
    "project_registration_id",
    "project_id",
    "root_physical_identity_ref",
    "control_physical_identity_ref",
    "manifest_physical_identity_ref",
    "volume_binding_sha256",
    "owner_dacl_binding_sha256",
    "writer_migration_matrix_sha256",
    "broker_install_binding_sha256",
    "enrollment_epoch",
    "created_at",
    "status",
    "enrollment_sha256",
}
_PARTICIPANT_PLAN_FIELDS = {
    "record_type",
    "protocol_version",
    "operation_id",
    "participant_id",
    "participant_profile_id",
    "semantic_owner_task_id",
    "object_commitments",
    "prepare_supported",
    "commit_supported",
    "reconcile_supported",
    "abort_before_commit_supported",
    "plan_sha256",
}
_PROFILE_VALIDATION_FIELDS = {
    "record_type",
    "protocol_version",
    "operation_id",
    "intent_sha256",
    "operation_profile_id",
    "parser_id",
    "transition_validator_id",
    "semantic_owner_task_id",
    "validated_payload_sha256",
    "validation_status",
    "validation_receipt_sha256",
}
_JOURNAL_FIELDS = {
    "record_type",
    "protocol_version",
    "project_registration_id",
    "operation_id",
    "operation_kind",
    "operation_profile_id",
    "intent_sha256",
    "request_sha256",
    "caller_task_id",
    "caller_build_sha256",
    "caller_policy_sha256",
    "prior_observation_sha256",
    "intended_successor_set_sha256",
    "participant_plan_sha256s",
    "broker_instance_id",
    "enrollment_epoch",
    "expires_at",
    "phase",
    "phase_sequence",
    "phase_evidence_sha256s",
    "journal_sha256",
}
_WITNESS_FIELDS = {
    "record_type",
    "protocol_version",
    "project_registration_id",
    "operation_id",
    "operation_kind",
    "operation_profile_id",
    "intent_sha256",
    "request_sha256",
    "prior_observation_sha256",
    "intended_successor_set_sha256",
    "participant_plan_sha256s",
    "observed_participant_receipt_sha256s",
    "observed_object_identity_sha256s",
    "journal_sha256",
    "broker_instance_id",
    "enrollment_epoch",
    "witness_state",
    "manifest_commit_observation",
    "committed_manifest_sha256",
    "committed_manifest_physical_identity_ref",
    "created_at",
    "terminalized_at",
    "witness_sha256",
}
_PUBLIC_FIELDS = {
    "record_type",
    "protocol_version",
    "operation_id",
    "operation_kind",
    "operation_profile_id",
    "intent_sha256",
    "request_sha256",
    "status",
    "reason_codes",
    "operation_witness_sha256",
    "readback_sha256",
    "retry_allowed",
    "human_recovery_required",
    "effect_count",
    "public_status_sha256",
}

_INTENT_PAYLOAD_FIELDS = {
    "MANIFEST_CREATE_V1": {
        "successor_manifest",
        "successor_manifest_sha256",
        "semantic_authorization_sha256",
    },
    "MANIFEST_TRANSITION_V1": {
        "prior_manifest_sha256",
        "prior_manifest_physical_identity_ref",
        "successor_manifest",
        "successor_manifest_sha256",
        "participant_plan_sha256",
        "semantic_authorization_sha256",
    },
    "CONTROL_OBJECT_CAS_V1": {
        "predecessor_sha256",
        "predecessor_physical_identity_ref",
        "successor_document",
        "successor_sha256",
        "semantic_authorization_sha256",
    },
    "CONTROL_APPEND_CHAIN_V1": {
        "prior_terminal_revision",
        "prior_terminal_sha256",
        "successor_document",
        "successor_sha256",
        "semantic_authorization_sha256",
    },
    "CONTROL_RECOVERY_OBJECT_V1": {
        "recovery_action",
        "predecessor_sha256",
        "successor_document",
        "successor_sha256",
        "terminal_proof_sha256",
        "semantic_authorization_sha256",
    },
    "CONTROL_SNAPSHOT_SET_V1": {
        "create_set",
        "retain_set",
        "remove_set",
        "retention_policy_sha256",
        "semantic_authorization_sha256",
    },
    "PROJECT_READ_LEASE_V1": {
        "expected_manifest_sha256",
        "expected_state_coordinate_sha256",
        "observation_profile_id",
    },
    "QUERY_OPERATION_V1": {
        "queried_operation_id",
        "queried_intent_sha256",
        "queried_request_sha256",
    },
}

_PARTICIPANT_TUPLES = frozenset(
    {
        ("PREPARE", "PREPARED_NO_COMMIT", "NO_EFFECT"),
        ("PREPARE", "PREPARE_BLOCKED_NO_EFFECT", "NO_EFFECT"),
        ("PREPARE", "PREPARE_OUTCOME_UNKNOWN", "UNKNOWN"),
        ("COMMIT", "OBJECTS_COMMITTED", "COMMITTED"),
        ("COMMIT", "OBJECTS_NOT_COMMITTED_PROVEN", "NOT_COMMITTED"),
        ("COMMIT", "OBJECT_COMMIT_OUTCOME_UNKNOWN", "UNKNOWN"),
        ("RECONCILE", "RECONCILED_COMMITTED", "COMMITTED"),
        ("RECONCILE", "RECONCILED_NOT_COMMITTED", "NOT_COMMITTED"),
        ("RECONCILE", "RECONCILIATION_REQUIRED_COMMITTED", "COMMITTED"),
        ("RECONCILE", "RECONCILIATION_REQUIRED_NOT_COMMITTED", "NOT_COMMITTED"),
        ("RECONCILE", "RECONCILIATION_REQUIRED_UNKNOWN", "UNKNOWN"),
        ("ABORT", "ABORTED_OWNED_PREPARE", "NOT_COMMITTED"),
        ("ABORT", "ABORT_NOT_PROVEN", "UNKNOWN"),
    }
)

_PHASE_PAYLOAD_FIELDS: dict[tuple[str, str], frozenset[str]] = {
    ("ADMIT", "ACCEPTED_NO_EFFECT"): frozenset({"admission_binding_sha256"}),
    ("ADMIT", "REJECTED_NO_EFFECT"): frozenset({"rejection_class"}),
    ("OPEN", "CURRENT_NO_EFFECT"): frozenset(
        {"manifest_sha256", "manifest_physical_identity_ref", "state_coordinate_sha256", "security_binding_sha256"}
    ),
    ("OPEN", "BLOCKED_NO_EFFECT"): frozenset({"rejection_class"}),
    ("PREPARE", "PREPARED"): frozenset({"journal_sha256", "intent_witness_sha256"}),
    ("PREPARE", "BLOCKED_NO_EFFECT"): frozenset({"rejection_class"}),
    ("PARTICIPANTS", "PARTICIPANTS_PREPARED"): frozenset({"participant_receipt_sha256s"}),
    ("PARTICIPANTS", "PARTICIPANT_BLOCKED"): frozenset({"rejection_class"}),
    ("STAGE", "OBJECTS_STAGED"): frozenset({"staged_identity_sha256s"}),
    ("STAGE", "STAGE_BLOCKED"): frozenset({"rejection_class"}),
    ("COMMIT_OBJECTS", "OBJECTS_COMMITTED"): frozenset({"object_receipt_sha256s"}),
    ("COMMIT_OBJECTS", "OBJECT_OUTCOME_UNKNOWN"): frozenset({"object_receipt_sha256s"}),
    ("COMMIT_MANIFEST", "MANIFEST_COMMITTED"): frozenset(
        {"prior_manifest_sha256", "successor_manifest_sha256", "successor_physical_identity_ref", "operation_witness_sha256"}
    ),
    ("COMMIT_MANIFEST", "MANIFEST_NOT_COMMITTED"): frozenset(
        {"prior_manifest_sha256", "successor_manifest_sha256", "successor_physical_identity_ref", "operation_witness_sha256"}
    ),
    ("COMMIT_MANIFEST", "MANIFEST_OUTCOME_UNKNOWN"): frozenset(
        {"prior_manifest_sha256", "successor_manifest_sha256", "successor_physical_identity_ref", "operation_witness_sha256"}
    ),
    ("RECONCILE", "RECONCILED"): frozenset({"participant_terminal_receipt_sha256s"}),
    ("RECONCILE", "RECONCILIATION_REQUIRED"): frozenset({"participant_terminal_receipt_sha256s"}),
    ("TERMINAL", "COMMITTED_WITH_READBACK"): frozenset(
        {"operation_witness_sha256", "fresh_readback_sha256", "admission_barrier_state"}
    ),
    ("TERMINAL", "NOT_COMMITTED_PROVEN"): frozenset(
        {"operation_witness_sha256", "fresh_readback_sha256", "admission_barrier_state"}
    ),
    ("TERMINAL", "BLOCKED_AFTER_PREPARE"): frozenset(
        {"operation_witness_sha256", "fresh_readback_sha256", "admission_barrier_state"}
    ),
    ("TERMINAL", "COMMIT_OUTCOME_UNKNOWN"): frozenset(
        {"operation_witness_sha256", "fresh_readback_sha256", "admission_barrier_state"}
    ),
    ("READ", "READ_CURRENT_NO_EFFECT"): frozenset(
        {"manifest_sha256", "state_coordinate_sha256", "readback_sha256"}
    ),
    ("READ", "READ_BLOCKED_NO_EFFECT"): frozenset({"read_failure_class", "failure_observation_sha256"}),
    ("QUERY", "COMMITTED_CURRENT"): frozenset({"operation_witness_sha256", "fresh_readback_sha256"}),
    ("QUERY", "COMMITTED_SUPERSEDED"): frozenset({"operation_witness_sha256", "fresh_readback_sha256"}),
    ("QUERY", "NOT_COMMITTED"): frozenset({"operation_witness_sha256", "fresh_readback_sha256"}),
    ("QUERY", "UNKNOWN_WITH_WITNESS"): frozenset({"operation_witness_sha256", "fresh_readback_sha256"}),
    ("QUERY", "WITNESS_NOT_FOUND_NO_EFFECT"): frozenset(
        {"queried_operation_id", "queried_intent_sha256", "absence_observation_sha256"}
    ),
    ("QUERY", "WITNESS_EVIDENCE_UNAVAILABLE_NO_EFFECT"): frozenset(
        {"queried_operation_id", "queried_intent_sha256", "evidence_failure_class", "failure_observation_sha256"}
    ),
    ("QUERY", "READBACK_EVIDENCE_UNAVAILABLE_WITH_WITNESS"): frozenset(
        {
            "queried_operation_id",
            "queried_intent_sha256",
            "operation_witness_sha256",
            "evidence_failure_class",
            "failure_observation_sha256",
        }
    ),
    ("RELEASE", "RELEASED"): frozenset({"release_warning_code"}),
    ("RELEASE", "RELEASE_WARNING"): frozenset({"release_warning_code"}),
}

_PUBLIC_RULES: dict[str, tuple[str, str, bool]] = {
    # status: witness mode, readback mode, human recovery required
    "COMMITTED_WITH_READBACK": ("REQUIRED", "REQUIRED", False),
    "NOT_COMMITTED_PROVEN": ("REQUIRED", "OPTIONAL", False),
    "BLOCKED_NO_WRITE": ("FORBIDDEN", "FORBIDDEN", False),
    "COMMIT_OUTCOME_UNKNOWN": ("REQUIRED", "OPTIONAL", True),
    "READ_CURRENT_NO_EFFECT": ("FORBIDDEN", "REQUIRED", False),
    "READ_BLOCKED_NO_EFFECT": ("FORBIDDEN", "FORBIDDEN", False),
    "QUERY_COMMITTED_CURRENT": ("REQUIRED", "REQUIRED", False),
    "QUERY_COMMITTED_SUPERSEDED": ("REQUIRED", "REQUIRED", False),
    "QUERY_NOT_COMMITTED": ("REQUIRED", "REQUIRED", False),
    "QUERY_UNKNOWN_WITH_WITNESS": ("REQUIRED", "REQUIRED", True),
    "QUERY_WITNESS_NOT_FOUND_NO_EFFECT": ("FORBIDDEN", "FORBIDDEN", False),
    "QUERY_WITNESS_EVIDENCE_UNAVAILABLE_NO_EFFECT": ("FORBIDDEN", "FORBIDDEN", True),
    "QUERY_READBACK_EVIDENCE_UNAVAILABLE_WITH_WITNESS": ("REQUIRED", "FORBIDDEN", True),
}

_QUERY_PUBLIC = {
    "COMMITTED_CURRENT": "QUERY_COMMITTED_CURRENT",
    "COMMITTED_SUPERSEDED": "QUERY_COMMITTED_SUPERSEDED",
    "NOT_COMMITTED": "QUERY_NOT_COMMITTED",
    "UNKNOWN_WITH_WITNESS": "QUERY_UNKNOWN_WITH_WITNESS",
    "WITNESS_NOT_FOUND_NO_EFFECT": "QUERY_WITNESS_NOT_FOUND_NO_EFFECT",
    "WITNESS_EVIDENCE_UNAVAILABLE_NO_EFFECT": "QUERY_WITNESS_EVIDENCE_UNAVAILABLE_NO_EFFECT",
    "READBACK_EVIDENCE_UNAVAILABLE_WITH_WITNESS": "QUERY_READBACK_EVIDENCE_UNAVAILABLE_WITH_WITNESS",
}

_JOURNAL_PHASE_VALUES = frozenset(
    {
        "PREPARED",
        "PARTICIPANTS_PREPARED",
        "OBJECTS_STAGED",
        "OBJECTS_COMMITTED",
        "MANIFEST_COMMITTING",
        "MANIFEST_COMMITTED",
        "PARTICIPANTS_RECONCILED",
        "TERMINAL",
        "UNKNOWN_QUARANTINED",
    }
)


def _exact(value: Mapping[str, Any], fields: set[str] | frozenset[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != set(fields):
        raise ValueError(f"{name} fields are not exact")


def _bounded(value: Any, name: str, *, body_envelope: bool = False) -> None:
    try:
        encoded = canonical_json_bytes(value)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError(f"{name} is not canonical JSON") from exc
    limit = MAX_BODY_ENVELOPE_BYTES if body_envelope else MAX_RECORD_BYTES
    if not encoded or len(encoded) > limit:
        raise ValueError(f"{name} is outside its byte bound")
    pending: list[tuple[Any, int]] = [(value, 0)]
    while pending:
        current, depth = pending.pop()
        if depth > MAX_JSON_DEPTH:
            raise ValueError(f"{name} exceeds depth bound")
        if isinstance(current, Mapping):
            pending.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, (list, tuple)):
            pending.extend((item, depth + 1) for item in current)
        elif isinstance(current, float) and not math.isfinite(current):
            raise ValueError(f"{name} contains a nonfinite number")


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be SHA-256")
    return validate_sha256(value, field_name=name)


def _id(value: Any, name: str, *, reference: bool = False) -> str:
    pattern = _REF_RE if reference else _ID_RE
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"{name} is not a valid opaque identifier")
    lowered = value.casefold()
    if "/" in value or "\\" in value or "://" in lowered or re.match(r"^[a-z][a-z0-9+.-]*:", lowered):
        raise ValueError(f"{name} must not be a path or URI")
    return value


def _positive(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 2_147_483_647:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _nonnegative(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 2_147_483_647:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def _time(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not _TIMESTAMP_RE.fullmatch(value):
        raise ValueError(f"{name} must be a calendar-valid UTC timestamp")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be a calendar-valid UTC timestamp") from exc


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _digest(body: Mapping[str, Any], field: str, domain: bytes) -> str:
    value = copy.deepcopy(dict(body))
    value.pop(field, None)
    return sha256_bytes(domain + canonical_json_bytes(value))


def _verify_digest(body: Mapping[str, Any], field: str, domain: bytes) -> None:
    _sha(body.get(field), field)
    if body[field] != _digest(body, field, domain):
        raise ValueError(f"{field} does not match canonical content")


def _sha_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or len(value) > 4_096:
        raise ValueError(f"{name} must be a bounded ordered array")
    return [_sha(item, f"{name} item") for item in value]


def parse_security_json(payload: bytes, *, body_envelope: bool = False) -> Any:
    limit = MAX_BODY_ENVELOPE_BYTES if body_envelope else MAX_RECORD_BYTES
    if not isinstance(payload, bytes) or not payload or len(payload) > limit or payload.startswith(b"\xef\xbb\xbf"):
        raise ValueError("JSON payload is outside its byte bound or has a BOM")

    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicate,
            parse_constant=lambda item: (_ for _ in ()).throw(ValueError(f"nonfinite number {item}")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("JSON payload is not strict UTF-8 JSON") from exc
    _bounded(value, "JSON payload", body_envelope=body_envelope)
    return value


@dataclass(frozen=True, slots=True)
class ContractRecord:
    kind: str
    data: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.data)


def seal_record(body: Mapping[str, Any], *, kind: str) -> dict[str, Any]:
    fields = {
        "intent": "intent_sha256",
        "request": "request_sha256",
        "phase": "phase_result_sha256",
        "enrollment": "enrollment_sha256",
        "participant_plan": "plan_sha256",
        "participant": "receipt_sha256",
        "profile_validation": "validation_receipt_sha256",
        "journal": "journal_sha256",
        "witness": "witness_sha256",
        "public": "public_status_sha256",
    }
    if kind not in fields:
        raise ValueError("record kind is unsupported")
    result = copy.deepcopy(dict(body))
    result[fields[kind]] = _digest(result, fields[kind], _DOMAINS[kind])
    return result


def _validate_intent_payload(kind: str, payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("intent payload must be an object")
    body = copy.deepcopy(dict(payload))
    _exact(body, _INTENT_PAYLOAD_FIELDS[kind], f"{kind} payload")
    for field, value in body.items():
        if field.endswith("_sha256"):
            _sha(value, field)
        elif field.endswith("_physical_identity_ref"):
            _id(value, field, reference=True)
        elif field in {"successor_manifest", "successor_document"}:
            if not isinstance(value, Mapping):
                raise ValueError(f"{field} must be a canonical object")
            _bounded(value, field, body_envelope=True)
        elif field in {"create_set", "retain_set", "remove_set"}:
            _sha_list(value, field)
        elif field in {"prior_terminal_revision"}:
            _positive(value, field)
        elif field in {"recovery_action", "observation_profile_id", "queried_operation_id"}:
            _id(value, field)
    if kind == "CONTROL_SNAPSHOT_SET_V1":
        sets = [body[name] for name in ("create_set", "retain_set", "remove_set")]
        flattened = [item for values in sets for item in values]
        if len(flattened) != len(set(flattened)):
            raise ValueError("snapshot sets must be disjoint")
    document_pairs = {
        "MANIFEST_CREATE_V1": ("successor_manifest", "successor_manifest_sha256"),
        "MANIFEST_TRANSITION_V1": ("successor_manifest", "successor_manifest_sha256"),
        "CONTROL_OBJECT_CAS_V1": ("successor_document", "successor_sha256"),
        "CONTROL_APPEND_CHAIN_V1": ("successor_document", "successor_sha256"),
        "CONTROL_RECOVERY_OBJECT_V1": ("successor_document", "successor_sha256"),
    }
    if kind in document_pairs:
        document_field, digest_field = document_pairs[kind]
        if body[digest_field] != sha256_bytes(canonical_json_bytes(body[document_field])):
            raise ValueError(f"{digest_field} does not match canonical successor document")
    return body


def parse_intent(value: Mapping[str, Any]) -> ContractRecord:
    _bounded(value, "PMST_OPERATION_INTENT_V1", body_envelope=True)
    body = copy.deepcopy(dict(value))
    _exact(body, _INTENT_FIELDS, "PMST_OPERATION_INTENT_V1")
    if body["protocol_version"] != PROTOCOL_VERSION or body["record_type"] != "PMST_OPERATION_INTENT_V1":
        raise ValueError("intent discriminator mismatch")
    for field in ("project_registration_id", "operation_id", "operation_profile_id", "caller_task_id"):
        _id(body[field], field)
    if body["operation_kind"] not in OPERATION_KINDS:
        raise ValueError("operation_kind is unsupported")
    for field in ("caller_build_sha256", "caller_policy_sha256"):
        _sha(body[field], field)
    if _time(body["requested_at"], "requested_at") >= _time(body["expires_at"], "expires_at"):
        raise ValueError("intent validity interval is empty")
    body["payload"] = _validate_intent_payload(body["operation_kind"], body["payload"])
    _verify_digest(body, "intent_sha256", _DOMAINS["intent"])
    return ContractRecord("intent", _freeze(body))


def parse_private_request(value: Mapping[str, Any]) -> ContractRecord:
    _bounded(value, "PMST_PRIVATE_REQUEST_V1", body_envelope=True)
    body = copy.deepcopy(dict(value))
    _exact(body, _REQUEST_FIELDS, "PMST_PRIVATE_REQUEST_V1")
    if body["protocol_version"] != PROTOCOL_VERSION or body["record_type"] != "PMST_PRIVATE_REQUEST_V1":
        raise ValueError("request discriminator mismatch")
    for field in ("broker_instance_id", "session_id", "request_nonce_id"):
        _id(body[field], field)
    intent = parse_intent(body["intent"]).to_dict()
    body["intent"] = intent
    _verify_digest(body, "request_sha256", _DOMAINS["request"])
    return ContractRecord("request", _freeze(body))


def parse_enrollment(value: Mapping[str, Any]) -> ContractRecord:
    _bounded(value, "PMST_ENROLLMENT_V1")
    body = copy.deepcopy(dict(value))
    _exact(body, _ENROLLMENT_FIELDS, "PMST_ENROLLMENT_V1")
    if body["protocol_version"] != PROTOCOL_VERSION or body["record_type"] != "PMST_ENROLLMENT_V1":
        raise ValueError("enrollment discriminator mismatch")
    for field in ("project_registration_id", "project_id", "enrollment_epoch"):
        _id(body[field], field)
    for field in (
        "root_physical_identity_ref",
        "control_physical_identity_ref",
        "manifest_physical_identity_ref",
    ):
        _id(body[field], field, reference=True)
    for field in (
        "volume_binding_sha256",
        "owner_dacl_binding_sha256",
        "writer_migration_matrix_sha256",
        "broker_install_binding_sha256",
    ):
        _sha(body[field], field)
    _time(body["created_at"], "created_at")
    if body["status"] not in {"PREPARED", "ACTIVE", "SUSPENDED", "REVOKED"}:
        raise ValueError("enrollment status is unsupported")
    _verify_digest(body, "enrollment_sha256", _DOMAINS["enrollment"])
    return ContractRecord("enrollment", _freeze(body))


def parse_participant_plan(value: Mapping[str, Any]) -> ContractRecord:
    _bounded(value, "PMST_PARTICIPANT_PLAN_V1")
    body = copy.deepcopy(dict(value))
    _exact(body, _PARTICIPANT_PLAN_FIELDS, "PMST_PARTICIPANT_PLAN_V1")
    if body["protocol_version"] != PROTOCOL_VERSION or body["record_type"] != "PMST_PARTICIPANT_PLAN_V1":
        raise ValueError("participant plan discriminator mismatch")
    for field in ("operation_id", "participant_id", "participant_profile_id", "semantic_owner_task_id"):
        _id(body[field], field)
    _sha_list(body["object_commitments"], "object_commitments")
    flags = (
        "prepare_supported",
        "commit_supported",
        "reconcile_supported",
        "abort_before_commit_supported",
    )
    if any(type(body[field]) is not bool for field in flags):
        raise ValueError("participant capability flags must be booleans")
    if not body["prepare_supported"] or not body["reconcile_supported"]:
        raise ValueError("participant must support prepare and reconcile")
    if body["abort_before_commit_supported"] and not body["prepare_supported"]:
        raise ValueError("abort support requires prepare support")
    _verify_digest(body, "plan_sha256", _DOMAINS["participant_plan"])
    return ContractRecord("participant_plan", _freeze(body))


def parse_profile_validation_receipt(value: Mapping[str, Any]) -> ContractRecord:
    _bounded(value, "PMST_PROFILE_VALIDATION_RECEIPT_V1")
    body = copy.deepcopy(dict(value))
    _exact(body, _PROFILE_VALIDATION_FIELDS, "PMST_PROFILE_VALIDATION_RECEIPT_V1")
    if body["protocol_version"] != PROTOCOL_VERSION or body["record_type"] != "PMST_PROFILE_VALIDATION_RECEIPT_V1":
        raise ValueError("profile validation receipt discriminator mismatch")
    for field in (
        "operation_id",
        "operation_profile_id",
        "parser_id",
        "transition_validator_id",
        "semantic_owner_task_id",
    ):
        _id(body[field], field)
    for field in ("intent_sha256", "validated_payload_sha256"):
        _sha(body[field], field)
    if body["validation_status"] != "ACCEPTED":
        raise ValueError("profile validation status must be ACCEPTED")
    _verify_digest(body, "validation_receipt_sha256", _DOMAINS["profile_validation"])
    return ContractRecord("profile_validation", _freeze(body))


def parse_participant_receipt(value: Mapping[str, Any]) -> ContractRecord:
    _bounded(value, "PMST_PARTICIPANT_RECEIPT_V1")
    body = copy.deepcopy(dict(value))
    _exact(body, _PARTICIPANT_FIELDS, "PMST_PARTICIPANT_RECEIPT_V1")
    if body["protocol_version"] != PROTOCOL_VERSION or body["record_type"] != "PMST_PARTICIPANT_RECEIPT_V1":
        raise ValueError("participant receipt discriminator mismatch")
    for field in ("operation_id", "participant_id"):
        _id(body[field], field)
    _sha(body["plan_sha256"], "plan_sha256")
    _sha_list(body["object_observations"], "object_observations")
    _positive(body["receipt_sequence"], "receipt_sequence")
    triple = (body["participant_phase"], body["participant_status"], body["effect_observation"])
    if triple not in _PARTICIPANT_TUPLES:
        raise ValueError("participant phase/status/effect tuple is not allowed")
    _verify_digest(body, "receipt_sha256", _DOMAINS["participant"])
    return ContractRecord("participant", _freeze(body))


def _validate_phase_payload(phase: str, status: str, payload: Any) -> dict[str, Any]:
    key = (phase, status)
    fields = _PHASE_PAYLOAD_FIELDS.get(key)
    if fields is None or not isinstance(payload, Mapping):
        raise ValueError("phase/status is unsupported")
    body = copy.deepcopy(dict(payload))
    _exact(body, fields, f"{phase}/{status} payload")
    for field, value in body.items():
        if field.endswith("_sha256"):
            if value is None and not (phase == "TERMINAL" and field == "fresh_readback_sha256"):
                raise ValueError(f"{field} must not be null")
            if value is not None:
                _sha(value, field)
        elif field.endswith("_sha256s"):
            _sha_list(value, field)
        elif field.endswith("_physical_identity_ref"):
            if value is not None:
                _id(value, field, reference=True)
        elif field in {"queried_operation_id"}:
            _id(value, field)
        elif field in {"read_failure_class", "evidence_failure_class"}:
            if value not in FAILURE_CLASSES:
                raise ValueError(f"{field} is unsupported")
        elif field == "admission_barrier_state" and value not in {"OPEN", "CLOSED"}:
            raise ValueError("admission_barrier_state is unsupported")
        elif field in {"rejection_class"}:
            _id(value, field)
        elif field == "release_warning_code":
            if status == "RELEASED" and value is not None:
                raise ValueError("RELEASED must not carry a warning")
            if status == "RELEASE_WARNING":
                _id(value, field)

    if phase == "COMMIT_MANIFEST":
        if status == "MANIFEST_COMMITTED" and body["successor_physical_identity_ref"] is None:
            raise ValueError("committed manifest requires successor physical identity")
        if status != "MANIFEST_COMMITTED" and body["successor_physical_identity_ref"] is not None:
            raise ValueError("uncommitted/unknown manifest must not claim successor physical identity")
    if phase == "OPEN" and status == "CURRENT_NO_EFFECT" and body["manifest_physical_identity_ref"] is None:
        raise ValueError("current manifest observation requires physical identity")
    if phase == "TERMINAL":
        if status == "COMMITTED_WITH_READBACK" and body["fresh_readback_sha256"] is None:
            raise ValueError("committed terminal result requires readback")
        if status in {"BLOCKED_AFTER_PREPARE", "COMMIT_OUTCOME_UNKNOWN"} and body["admission_barrier_state"] != "CLOSED":
            raise ValueError("unresolved terminal result must keep admission barrier closed")
    if phase == "QUERY":
        if status in {"COMMITTED_CURRENT", "COMMITTED_SUPERSEDED", "NOT_COMMITTED", "UNKNOWN_WITH_WITNESS"}:
            if body["operation_witness_sha256"] is None or body["fresh_readback_sha256"] is None:
                raise ValueError("query witness result requires witness and readback")
    return body


def _expected_observation(phase: str, status: str) -> str | None:
    if phase in {"ADMIT", "OPEN", "PREPARE", "PARTICIPANTS", "STAGE", "COMMIT_OBJECTS", "READ"}:
        return "NOT_OBSERVED"
    if phase == "COMMIT_MANIFEST":
        return {
            "MANIFEST_COMMITTED": "COMMITTED",
            "MANIFEST_NOT_COMMITTED": "NOT_COMMITTED",
            "MANIFEST_OUTCOME_UNKNOWN": "UNKNOWN",
        }[status]
    if phase == "QUERY":
        return {
            "COMMITTED_CURRENT": "COMMITTED",
            "COMMITTED_SUPERSEDED": "COMMITTED",
            "NOT_COMMITTED": "NOT_COMMITTED",
            "UNKNOWN_WITH_WITNESS": None,
            "WITNESS_NOT_FOUND_NO_EFFECT": "NOT_OBSERVED",
            "WITNESS_EVIDENCE_UNAVAILABLE_NO_EFFECT": "NOT_OBSERVED",
            "READBACK_EVIDENCE_UNAVAILABLE_WITH_WITNESS": None,
        }[status]
    return None


def parse_phase_result(value: Mapping[str, Any]) -> ContractRecord:
    _bounded(value, "PMST_PRIVATE_PHASE_RESULT_V1")
    body = copy.deepcopy(dict(value))
    _exact(body, _PHASE_FIELDS, "PMST_PRIVATE_PHASE_RESULT_V1")
    if body["protocol_version"] != PROTOCOL_VERSION or body["record_type"] != "PMST_PRIVATE_PHASE_RESULT_V1":
        raise ValueError("phase result discriminator mismatch")
    for field in (
        "broker_instance_id",
        "session_id",
        "project_registration_id",
        "operation_id",
        "operation_profile_id",
    ):
        _id(body[field], field)
    if body["operation_kind"] not in OPERATION_KINDS:
        raise ValueError("operation_kind is unsupported")
    for field in ("intent_sha256", "request_sha256"):
        _sha(body[field], field)
    body["payload"] = _validate_phase_payload(body["phase"], body["phase_status"], body["payload"])
    if body["manifest_commit_observation"] not in OBSERVATIONS:
        raise ValueError("manifest_commit_observation is unsupported")
    expected = _expected_observation(body["phase"], body["phase_status"])
    if expected is not None and body["manifest_commit_observation"] != expected:
        raise ValueError("phase/status manifest observation is inconsistent")
    if (
        body["phase"] == "QUERY"
        and body["phase_status"] == "UNKNOWN_WITH_WITNESS"
        and body["manifest_commit_observation"] not in {"NOT_OBSERVED", "UNKNOWN"}
    ):
        raise ValueError("unknown query witness observation is inconsistent")
    _nonnegative(body["effect_count"], "effect_count")
    if (
        body["phase"] in {"ADMIT", "OPEN", "READ", "QUERY"}
        or body["phase_status"] == "BLOCKED_NO_EFFECT"
    ) and body["effect_count"] != 0:
        raise ValueError("non-effect phase must have zero effect_count")
    if body["reason_code"] is not None:
        _id(body["reason_code"], "reason_code")
    _verify_digest(body, "phase_result_sha256", _DOMAINS["phase"])
    return ContractRecord("phase", _freeze(body))


def parse_journal(value: Mapping[str, Any]) -> ContractRecord:
    _bounded(value, "PMST_TRANSACTION_JOURNAL_V1")
    body = copy.deepcopy(dict(value))
    _exact(body, _JOURNAL_FIELDS, "PMST_TRANSACTION_JOURNAL_V1")
    if body["protocol_version"] != PROTOCOL_VERSION or body["record_type"] != "PMST_TRANSACTION_JOURNAL_V1":
        raise ValueError("journal discriminator mismatch")
    for field in (
        "project_registration_id",
        "operation_id",
        "operation_profile_id",
        "caller_task_id",
        "broker_instance_id",
        "enrollment_epoch",
    ):
        _id(body[field], field)
    if body["operation_kind"] not in MUTATING_KINDS:
        raise ValueError("journal operation kind must mutate")
    for field in (
        "intent_sha256",
        "request_sha256",
        "caller_build_sha256",
        "caller_policy_sha256",
        "prior_observation_sha256",
        "intended_successor_set_sha256",
    ):
        _sha(body[field], field)
    for field in ("participant_plan_sha256s", "phase_evidence_sha256s"):
        _sha_list(body[field], field)
    _time(body["expires_at"], "expires_at")
    if body["phase"] not in _JOURNAL_PHASE_VALUES:
        raise ValueError("journal phase is unsupported")
    sequence = _positive(body["phase_sequence"], "phase_sequence")
    has_participants = bool(body["participant_plan_sha256s"])
    phases = ["PREPARED"]
    if has_participants:
        phases.append("PARTICIPANTS_PREPARED")
    phases.extend(["OBJECTS_STAGED", "OBJECTS_COMMITTED"])
    if body["operation_kind"] in MANIFEST_KINDS:
        phases.extend(["MANIFEST_COMMITTING", "MANIFEST_COMMITTED"])
    if has_participants:
        phases.append("PARTICIPANTS_RECONCILED")
    phases.append("TERMINAL")
    if body["phase"] == "UNKNOWN_QUARANTINED":
        if sequence > len(phases) + 1:
            raise ValueError("quarantine journal sequence is outside operation route")
    elif body["phase"] not in phases or sequence != phases.index(body["phase"]) + 1:
        raise ValueError("journal phase sequence is inconsistent with operation route")
    _verify_digest(body, "journal_sha256", _DOMAINS["journal"])
    return ContractRecord("journal", _freeze(body))


def parse_witness(value: Mapping[str, Any]) -> ContractRecord:
    _bounded(value, "PMST_OPERATION_WITNESS_V1")
    body = copy.deepcopy(dict(value))
    _exact(body, _WITNESS_FIELDS, "PMST_OPERATION_WITNESS_V1")
    if body["protocol_version"] != PROTOCOL_VERSION or body["record_type"] != "PMST_OPERATION_WITNESS_V1":
        raise ValueError("witness discriminator mismatch")
    for field in (
        "project_registration_id",
        "operation_id",
        "operation_profile_id",
        "broker_instance_id",
        "enrollment_epoch",
    ):
        _id(body[field], field)
    if body["operation_kind"] not in MUTATING_KINDS:
        raise ValueError("witness operation kind must mutate")
    for field in (
        "intent_sha256",
        "request_sha256",
        "prior_observation_sha256",
        "intended_successor_set_sha256",
        "journal_sha256",
    ):
        _sha(body[field], field)
    for field in (
        "participant_plan_sha256s",
        "observed_participant_receipt_sha256s",
        "observed_object_identity_sha256s",
    ):
        _sha_list(body[field], field)
    state = body["witness_state"]
    if state not in {"PREPARED", "COMMITTED_DURABLE", "NOT_COMMITTED_PROVEN", "UNKNOWN_QUARANTINED"}:
        raise ValueError("witness_state is unsupported")
    observation = body["manifest_commit_observation"]
    if body["operation_kind"] in MANIFEST_KINDS:
        if state == "UNKNOWN_QUARANTINED":
            if observation not in {"NOT_OBSERVED", "UNKNOWN"}:
                raise ValueError("witness state/observation is inconsistent")
            expected = observation
        else:
            expected = {
                "PREPARED": "NOT_OBSERVED",
                "COMMITTED_DURABLE": "COMMITTED",
                "NOT_COMMITTED_PROVEN": "NOT_COMMITTED",
            }[state]
    else:
        expected = "NOT_OBSERVED"
    if observation != expected:
        raise ValueError("witness state/observation is inconsistent")
    if state == "COMMITTED_DURABLE" and body["operation_kind"] in MANIFEST_KINDS:
        _sha(body["committed_manifest_sha256"], "committed_manifest_sha256")
        _id(body["committed_manifest_physical_identity_ref"], "committed_manifest_physical_identity_ref", reference=True)
    elif body["committed_manifest_sha256"] is not None or body["committed_manifest_physical_identity_ref"] is not None:
        raise ValueError("non-committed witness must not claim committed manifest")
    _time(body["created_at"], "created_at")
    if state == "PREPARED":
        if body["terminalized_at"] is not None or body["observed_participant_receipt_sha256s"] or body["observed_object_identity_sha256s"]:
            raise ValueError("prepared witness must not claim future observations")
    else:
        if _time(body["terminalized_at"], "terminalized_at") < _time(body["created_at"], "created_at"):
            raise ValueError("witness terminal time precedes creation")
    _verify_digest(body, "witness_sha256", _DOMAINS["witness"])
    return ContractRecord("witness", _freeze(body))


def parse_public_status(value: Mapping[str, Any]) -> ContractRecord:
    _bounded(value, "PMST_PUBLIC_OPERATION_STATUS_V1")
    body = copy.deepcopy(dict(value))
    _exact(body, _PUBLIC_FIELDS, "PMST_PUBLIC_OPERATION_STATUS_V1")
    if body["protocol_version"] != PROTOCOL_VERSION or body["record_type"] != "PMST_PUBLIC_OPERATION_STATUS_V1":
        raise ValueError("public status discriminator mismatch")
    for field in ("operation_id", "operation_profile_id"):
        _id(body[field], field)
    if body["operation_kind"] not in OPERATION_KINDS:
        raise ValueError("operation_kind is unsupported")
    for field in ("intent_sha256", "request_sha256"):
        _sha(body[field], field)
    rule = _PUBLIC_RULES.get(body["status"])
    if rule is None:
        raise ValueError("public status is unsupported")
    witness_mode, readback_mode, base_human_required = rule
    witness = body["operation_witness_sha256"]
    readback = body["readback_sha256"]
    if (witness_mode == "REQUIRED" and witness is None) or (witness_mode == "FORBIDDEN" and witness is not None):
        raise ValueError("public status witness/readback nullability mismatch")
    if (readback_mode == "REQUIRED" and readback is None) or (readback_mode == "FORBIDDEN" and readback is not None):
        raise ValueError("public status witness/readback nullability mismatch")
    if witness is not None:
        _sha(witness, "operation_witness_sha256")
    if readback is not None:
        _sha(readback, "readback_sha256")
    if not isinstance(body["reason_codes"], list) or len(body["reason_codes"]) > 64:
        raise ValueError("reason_codes must be a bounded ordered array")
    human_required = base_human_required or "RECONCILIATION_REQUIRED" in body["reason_codes"]
    if body["retry_allowed"] is not False or body["human_recovery_required"] is not human_required:
        raise ValueError("public retry/recovery flags are inconsistent")
    for reason in body["reason_codes"]:
        _id(reason, "reason_code")
    if len(body["reason_codes"]) != len(set(body["reason_codes"])):
        raise ValueError("reason_codes must not contain duplicates")
    effects = _nonnegative(body["effect_count"], "effect_count")
    if body["status"].startswith(("READ_", "QUERY_")) or body["status"] == "BLOCKED_NO_WRITE":
        if effects != 0:
            raise ValueError("no-effect public status must have zero effect_count")
    _verify_digest(body, "public_status_sha256", _DOMAINS["public"])
    return ContractRecord("public", _freeze(body))


@dataclass(frozen=True, slots=True)
class ReadbackBinding:
    readback_sha256: str
    operation_id: str
    intent_sha256: str
    manifest_sha256: str
    state_coordinate_sha256: str
    security_binding_sha256: str
    operation_witness_sha256: str | None
    manifest_commit_observation: str

    def __post_init__(self) -> None:
        for field in ("readback_sha256", "intent_sha256", "manifest_sha256", "state_coordinate_sha256", "security_binding_sha256"):
            _sha(getattr(self, field), field)
        _id(self.operation_id, "operation_id")
        if self.operation_witness_sha256 is not None:
            _sha(self.operation_witness_sha256, "operation_witness_sha256")
        if self.manifest_commit_observation not in OBSERVATIONS:
            raise ValueError("readback manifest observation is unsupported")


class PureEvidenceRegistry:
    """Validated in-memory evidence lookup; no record is read from a path."""

    def __init__(
        self,
        records: Sequence[Mapping[str, Any]] = (),
        readbacks: Sequence[ReadbackBinding] = (),
    ) -> None:
        self._records: dict[str, tuple[str, dict[str, Any]]] = {}
        self._readbacks: dict[str, ReadbackBinding] = {}
        for record in records:
            self.add(record)
        for binding in readbacks:
            self.add_readback(binding)

    def add(self, record: Mapping[str, Any]) -> None:
        parsers = {
            "PMST_TRANSACTION_JOURNAL_V1": (parse_journal, "journal_sha256"),
            "PMST_OPERATION_WITNESS_V1": (parse_witness, "witness_sha256"),
            "PMST_PARTICIPANT_PLAN_V1": (parse_participant_plan, "plan_sha256"),
            "PMST_PARTICIPANT_RECEIPT_V1": (parse_participant_receipt, "receipt_sha256"),
            "PMST_PROFILE_VALIDATION_RECEIPT_V1": (parse_profile_validation_receipt, "validation_receipt_sha256"),
        }
        record_type = record.get("record_type") if isinstance(record, Mapping) else None
        if record_type not in parsers:
            raise ValueError("evidence record type is unsupported")
        parser, digest_field = parsers[record_type]
        parsed = parser(record).to_dict()
        digest = parsed[digest_field]
        prior = self._records.get(digest)
        if prior is not None and prior != (record_type, parsed):
            raise ValueError("evidence digest collision")
        self._records[digest] = (record_type, parsed)

    def add_readback(self, binding: ReadbackBinding) -> None:
        prior = self._readbacks.get(binding.readback_sha256)
        if prior is not None and prior != binding:
            raise ValueError("readback digest collision")
        self._readbacks[binding.readback_sha256] = binding

    def require(self, digest: str, record_type: str) -> dict[str, Any]:
        _sha(digest, "evidence_sha256")
        value = self._records.get(digest)
        if value is None or value[0] != record_type:
            raise ValueError(f"required {record_type} evidence is unavailable")
        return copy.deepcopy(value[1])

    def optional(self, digest: str, record_type: str) -> dict[str, Any] | None:
        value = self._records.get(digest)
        if value is None:
            return None
        if value[0] != record_type:
            raise ValueError("evidence type does not match digest use")
        return copy.deepcopy(value[1])

    def require_readback(self, digest: str) -> ReadbackBinding:
        _sha(digest, "readback_sha256")
        binding = self._readbacks.get(digest)
        if binding is None:
            raise ValueError("required readback binding is unavailable")
        return binding


@dataclass(frozen=True, slots=True)
class OperationProfile:
    profile_id: str
    operation_kind: str
    target_class: str
    parser_id: str
    transition_validator_id: str
    maximum_body_bytes: int
    maximum_object_count: int
    durability_class: str
    semantic_owner_task_id: str
    allowed_predecessor_relation: str
    participant_plan_sha256s: tuple[str, ...]
    permitted_phases: tuple[str, ...]
    participant_required: bool

    def __post_init__(self) -> None:
        for field in ("profile_id", "target_class", "parser_id", "transition_validator_id", "semantic_owner_task_id"):
            _id(getattr(self, field), field)
        if self.operation_kind not in OPERATION_KINDS:
            raise ValueError("profile operation kind is unsupported")
        if not 1 <= self.maximum_body_bytes <= MAX_BODY_ENVELOPE_BYTES:
            raise ValueError("profile maximum_body_bytes is outside bound")
        if not 1 <= self.maximum_object_count <= 4_096:
            raise ValueError("profile maximum_object_count is outside bound")
        expected_durability = "READ_ONLY_PINNED" if self.operation_kind in {"PROJECT_READ_LEASE_V1", "QUERY_OPERATION_V1"} else "DURABLE_READBACK"
        if self.durability_class != expected_durability:
            raise ValueError("profile durability class is inconsistent")
        allowed_relations = {
            "MANIFEST_CREATE_V1": "ABSENT_TO_REVISION_1",
            "MANIFEST_TRANSITION_V1": "EXACT_PREDECESSOR_CAS",
            "CONTROL_OBJECT_CAS_V1": "EXACT_PREDECESSOR_CAS",
            "CONTROL_APPEND_CHAIN_V1": "APPEND_CHAIN",
            "CONTROL_RECOVERY_OBJECT_V1": "PROFILE_RECOVERY",
            "CONTROL_SNAPSHOT_SET_V1": "BOUNDED_SNAPSHOT_SET",
            "PROJECT_READ_LEASE_V1": "READ_ONLY_EXPECTED_STATE",
            "QUERY_OPERATION_V1": "QUERY_BY_OPERATION",
        }
        if self.allowed_predecessor_relation != allowed_relations[self.operation_kind]:
            raise ValueError("profile predecessor relation is inconsistent")
        if type(self.participant_plan_sha256s) is not tuple or type(self.permitted_phases) is not tuple:
            raise ValueError("profile arrays must be immutable tuples")
        for plan_sha256 in self.participant_plan_sha256s:
            _sha(plan_sha256, "participant_plan_sha256")
        if self.participant_required != bool(self.participant_plan_sha256s):
            raise ValueError("profile participant requirement/plan set is inconsistent")
        if tuple(self.permitted_phases) != _profile_phase_route(self.operation_kind, self.participant_required):
            raise ValueError("profile permitted phases are not exact")


def _profile_phase_route(operation_kind: str, participant_required: bool) -> tuple[str, ...]:
    if operation_kind == "QUERY_OPERATION_V1":
        if participant_required:
            raise ValueError("query profile cannot require participants")
        return ("ADMIT", "QUERY", "RELEASE")
    if operation_kind == "PROJECT_READ_LEASE_V1":
        if participant_required:
            raise ValueError("read profile cannot require participants")
        return ("ADMIT", "OPEN", "READ", "RELEASE")
    phases = ["ADMIT", "OPEN", "PREPARE"]
    if participant_required:
        phases.append("PARTICIPANTS")
    phases.extend(["STAGE", "COMMIT_OBJECTS"])
    if operation_kind in MANIFEST_KINDS:
        phases.append("COMMIT_MANIFEST")
    if participant_required:
        phases.append("RECONCILE")
    phases.extend(["TERMINAL", "RELEASE"])
    return tuple(phases)


@dataclass(frozen=True, slots=True)
class AdmissionContext:
    broker_instance_id: str
    session_id: str
    client_process_instance_sha256: str
    broker_process_instance_sha256: str
    security_binding_sha256: str
    broker_install_binding_sha256: str
    trusted_now: str

    def __post_init__(self) -> None:
        _id(self.broker_instance_id, "broker_instance_id")
        _id(self.session_id, "session_id")
        _sha(self.client_process_instance_sha256, "client_process_instance_sha256")
        _sha(self.broker_process_instance_sha256, "broker_process_instance_sha256")
        _sha(self.security_binding_sha256, "security_binding_sha256")
        _sha(self.broker_install_binding_sha256, "broker_install_binding_sha256")
        _time(self.trusted_now, "trusted_now")


@dataclass(frozen=True, slots=True)
class NonceBinding:
    request_nonce_id: str
    intent_sha256: str
    project_registration_id: str
    operation_id: str
    operation_kind: str
    operation_profile_id: str
    context: AdmissionContext

    def __post_init__(self) -> None:
        for field in ("request_nonce_id", "project_registration_id", "operation_id", "operation_profile_id"):
            _id(getattr(self, field), field)
        _sha(self.intent_sha256, "intent_sha256")
        if self.operation_kind not in OPERATION_KINDS:
            raise ValueError("nonce operation kind is unsupported")


class PureNonceLedger:
    """In-memory single-use nonce model for PMST-I1 tests and pure execution."""

    def __init__(self) -> None:
        self._available: dict[str, NonceBinding] = {}
        self._consumed: set[str] = set()

    def register(self, binding: NonceBinding) -> None:
        nonce = binding.request_nonce_id
        if nonce in self._available or nonce in self._consumed:
            raise ValueError("nonce was already registered or consumed")
        self._available[nonce] = binding

    def consume(self, request: Mapping[str, Any], context: AdmissionContext) -> None:
        nonce = request["request_nonce_id"]
        binding = self._available.get(nonce)
        if binding is None:
            raise ValueError("nonce is unknown or already consumed")
        intent = request["intent"]
        expected = (
            intent["intent_sha256"],
            intent["project_registration_id"],
            intent["operation_id"],
            intent["operation_kind"],
            intent["operation_profile_id"],
            context,
        )
        actual = (
            binding.intent_sha256,
            binding.project_registration_id,
            binding.operation_id,
            binding.operation_kind,
            binding.operation_profile_id,
            binding.context,
        )
        if request["broker_instance_id"] != context.broker_instance_id or request["session_id"] != context.session_id or actual != expected:
            raise ValueError("nonce binding does not match request/admission context")
        del self._available[nonce]
        self._consumed.add(nonce)


class PmstPhasePort(Protocol):
    fixture_only: bool

    def perform(
        self,
        phase: str,
        request: Mapping[str, Any],
        prior_result: Mapping[str, Any] | None,
    ) -> Mapping[str, Any]: ...


class PurePmstStateMachine:
    """Deterministic validator for one admitted PMST request."""

    def __init__(
        self,
        request: Mapping[str, Any],
        profile: OperationProfile,
        enrollment: Mapping[str, Any],
        profile_validation_receipt: Mapping[str, Any] | None,
        evidence_registry: PureEvidenceRegistry,
        nonce_ledger: PureNonceLedger,
        admission_context: AdmissionContext,
    ) -> None:
        parsed = parse_private_request(request).to_dict()
        parsed_enrollment = parse_enrollment(enrollment).to_dict()
        intent = parsed["intent"]
        if intent["operation_profile_id"] != profile.profile_id or intent["operation_kind"] != profile.operation_kind:
            raise ValueError("request does not match immutable operation profile")
        participant_sha = intent["payload"].get("participant_plan_sha256")
        if participant_sha is not None and participant_sha not in profile.participant_plan_sha256s:
            raise ValueError("participant plan/profile requirement mismatch")
        if participant_sha is not None and not profile.participant_required:
            raise ValueError("participant plan/profile requirement mismatch")
        payload_bytes = canonical_json_bytes(intent["payload"])
        if len(payload_bytes) > profile.maximum_body_bytes:
            raise ValueError("intent payload exceeds operation profile byte bound")
        if intent["operation_kind"] == "CONTROL_SNAPSHOT_SET_V1":
            object_count = sum(len(intent["payload"][name]) for name in ("create_set", "retain_set", "remove_set"))
        elif intent["operation_kind"] in MUTATING_KINDS:
            object_count = 1
        else:
            object_count = 0
        if object_count > profile.maximum_object_count:
            raise ValueError("intent payload exceeds operation profile object bound")
        if intent["operation_kind"] in MUTATING_KINDS:
            if profile_validation_receipt is None:
                raise ValueError("mutating operation requires profile validation receipt")
            validation = parse_profile_validation_receipt(profile_validation_receipt).to_dict()
            expected_validation = {
                "operation_id": intent["operation_id"],
                "intent_sha256": intent["intent_sha256"],
                "operation_profile_id": profile.profile_id,
                "parser_id": profile.parser_id,
                "transition_validator_id": profile.transition_validator_id,
                "semantic_owner_task_id": profile.semantic_owner_task_id,
                "validated_payload_sha256": sha256_bytes(payload_bytes),
            }
            if any(validation[field] != expected for field, expected in expected_validation.items()):
                raise ValueError("profile validation receipt does not match request/profile")
        elif profile_validation_receipt is not None:
            raise ValueError("read/query operation must not carry profile validation receipt")
        if parsed_enrollment["status"] != "ACTIVE":
            raise ValueError("only ACTIVE enrollment admits operations")
        if parsed_enrollment["project_registration_id"] != intent["project_registration_id"]:
            raise ValueError("enrollment/request registration mismatch")
        if parsed_enrollment["broker_install_binding_sha256"] != admission_context.broker_install_binding_sha256:
            raise ValueError("enrollment/admission install binding mismatch")
        trusted_now = _time(admission_context.trusted_now, "trusted_now")
        if trusted_now < _time(intent["requested_at"], "requested_at") or trusted_now >= _time(intent["expires_at"], "expires_at"):
            raise ValueError("intent is not valid at trusted broker time")
        participant_plans: dict[str, dict[str, Any]] = {}
        for plan_sha256 in profile.participant_plan_sha256s:
            plan = evidence_registry.require(plan_sha256, "PMST_PARTICIPANT_PLAN_V1")
            if plan["operation_id"] != intent["operation_id"] or plan["semantic_owner_task_id"] != profile.semantic_owner_task_id:
                raise ValueError("participant plan does not match operation/profile owner")
            participant_plans[plan_sha256] = plan
        nonce_ledger.consume(parsed, admission_context)
        self.request = parsed
        self.enrollment = parsed_enrollment
        self.admission_context = admission_context
        self.evidence_registry = evidence_registry
        self.participant_plans = participant_plans
        self.profile = profile
        self.expected_phase: str | None = "ADMIT"
        self.last_result: dict[str, Any] | None = None
        self.outcome_result: dict[str, Any] | None = None
        self.prepared = False
        self.reconciled = not profile.participant_required
        self.observation = "NOT_OBSERVED"
        self.effect_count = 0
        self.reason_codes: list[str] = []
        self.operation_witness_sha256: str | None = None
        self.prepared_journal: dict[str, Any] | None = None
        self.commit_witness: dict[str, Any] | None = None
        self.accepted_participant_receipt_sha256s: list[str] = []
        self.participant_receipt_sequences: dict[str, int] = {}
        self.staged_identity_sha256s: tuple[str, ...] = ()
        self.open_manifest_sha256: str | None = None
        self.open_state_coordinate_sha256: str | None = None
        self.protected_object_observation = "NOT_OBSERVED"
        self.complete = False

    def _binding_check(self, result: Mapping[str, Any]) -> None:
        intent = self.request["intent"]
        expected = {
            "broker_instance_id": self.request["broker_instance_id"],
            "session_id": self.request["session_id"],
            "project_registration_id": intent["project_registration_id"],
            "operation_id": intent["operation_id"],
            "operation_kind": intent["operation_kind"],
            "operation_profile_id": intent["operation_profile_id"],
            "intent_sha256": intent["intent_sha256"],
            "request_sha256": self.request["request_sha256"],
        }
        if any(result[field] != value for field, value in expected.items()):
            raise ValueError("phase result operation binding mismatch")

    def _require_bound_journal(self, digest: str, expected_phase: str | set[str]) -> dict[str, Any]:
        journal = self.evidence_registry.require(digest, "PMST_TRANSACTION_JOURNAL_V1")
        intent = self.request["intent"]
        expected = {
            "project_registration_id": intent["project_registration_id"],
            "operation_id": intent["operation_id"],
            "operation_kind": intent["operation_kind"],
            "operation_profile_id": intent["operation_profile_id"],
            "intent_sha256": intent["intent_sha256"],
            "request_sha256": self.request["request_sha256"],
            "caller_task_id": intent["caller_task_id"],
            "caller_build_sha256": intent["caller_build_sha256"],
            "caller_policy_sha256": intent["caller_policy_sha256"],
            "broker_instance_id": self.request["broker_instance_id"],
            "enrollment_epoch": self.enrollment["enrollment_epoch"],
            "expires_at": intent["expires_at"],
        }
        if any(journal[field] != value for field, value in expected.items()):
            raise ValueError("journal evidence does not match operation/phase")
        if tuple(journal["participant_plan_sha256s"]) != self.profile.participant_plan_sha256s:
            raise ValueError("journal participant plan set does not match profile")
        intended_payload_sha256 = sha256_bytes(canonical_json_bytes(intent["payload"]))
        if journal["intended_successor_set_sha256"] != intended_payload_sha256:
            raise ValueError("journal intended successor commitment does not match intent payload")
        if self.open_state_coordinate_sha256 is not None and journal["prior_observation_sha256"] != self.open_state_coordinate_sha256:
            raise ValueError("journal prior observation does not match pinned open state")
        allowed_phases = {expected_phase} if isinstance(expected_phase, str) else expected_phase
        if journal["phase"] not in allowed_phases:
            raise ValueError("journal evidence does not match required phase")
        return journal

    def _require_bound_witness(
        self,
        digest: str,
        allowed_states: set[str],
        *,
        expected_receipts: Sequence[str] | None = None,
        expected_objects: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        witness = self.evidence_registry.require(digest, "PMST_OPERATION_WITNESS_V1")
        intent = self.request["intent"]
        expected = {
            "project_registration_id": intent["project_registration_id"],
            "operation_id": intent["operation_id"],
            "operation_kind": intent["operation_kind"],
            "operation_profile_id": intent["operation_profile_id"],
            "intent_sha256": intent["intent_sha256"],
            "request_sha256": self.request["request_sha256"],
            "broker_instance_id": self.request["broker_instance_id"],
            "enrollment_epoch": self.enrollment["enrollment_epoch"],
        }
        if any(witness[field] != value for field, value in expected.items()):
            raise ValueError("witness evidence does not match operation")
        if tuple(witness["participant_plan_sha256s"]) != self.profile.participant_plan_sha256s:
            raise ValueError("witness participant plan set does not match profile")
        if witness["witness_state"] not in allowed_states:
            raise ValueError("witness state does not match phase outcome")
        journal = self._require_bound_journal(
            witness["journal_sha256"],
            self._journal_phases_for_witness(witness["witness_state"]),
        )
        for field in ("prior_observation_sha256", "intended_successor_set_sha256"):
            if witness[field] != journal[field]:
                raise ValueError("witness does not preserve journal content commitment")
        if expected_receipts is not None and tuple(witness["observed_participant_receipt_sha256s"]) != tuple(expected_receipts):
            raise ValueError("witness participant observations do not match accepted receipts")
        if expected_objects is not None and tuple(witness["observed_object_identity_sha256s"]) != tuple(expected_objects):
            raise ValueError("witness object observations do not match staged identities")
        return witness

    def _journal_phases_for_witness(self, witness_state: str, operation_kind: str | None = None) -> set[str]:
        bound_kind = operation_kind or self.profile.operation_kind
        if witness_state == "PREPARED":
            return {"PREPARED"}
        if witness_state == "UNKNOWN_QUARANTINED":
            return {"UNKNOWN_QUARANTINED", "TERMINAL"}
        if witness_state == "NOT_COMMITTED_PROVEN":
            return {"MANIFEST_COMMITTING", "OBJECTS_COMMITTED", "TERMINAL"}
        if bound_kind in MANIFEST_KINDS:
            return {"MANIFEST_COMMITTED", "PARTICIPANTS_RECONCILED", "TERMINAL"}
        return {"OBJECTS_COMMITTED", "PARTICIPANTS_RECONCILED", "TERMINAL"}

    def _require_query_witness(self, digest: str, allowed_states: set[str]) -> dict[str, Any]:
        witness = self.evidence_registry.require(digest, "PMST_OPERATION_WITNESS_V1")
        query = self.request["intent"]
        payload = query["payload"]
        if (
            witness["project_registration_id"] != query["project_registration_id"]
            or witness["operation_id"] != payload["queried_operation_id"]
            or witness["intent_sha256"] != payload["queried_intent_sha256"]
            or witness["request_sha256"] != payload["queried_request_sha256"]
            or witness["enrollment_epoch"] != self.enrollment["enrollment_epoch"]
            or witness["witness_state"] not in allowed_states
        ):
            raise ValueError("query witness does not match queried operation")
        journal = self.evidence_registry.require(witness["journal_sha256"], "PMST_TRANSACTION_JOURNAL_V1")
        if (
            journal["project_registration_id"] != witness["project_registration_id"]
            or journal["operation_id"] != witness["operation_id"]
            or journal["intent_sha256"] != witness["intent_sha256"]
            or journal["request_sha256"] != witness["request_sha256"]
            or journal["operation_kind"] != witness["operation_kind"]
            or journal["operation_profile_id"] != witness["operation_profile_id"]
            or journal["broker_instance_id"] != witness["broker_instance_id"]
            or journal["enrollment_epoch"] != witness["enrollment_epoch"]
            or journal["prior_observation_sha256"] != witness["prior_observation_sha256"]
            or journal["intended_successor_set_sha256"] != witness["intended_successor_set_sha256"]
            or tuple(journal["participant_plan_sha256s"]) != tuple(witness["participant_plan_sha256s"])
        ):
            raise ValueError("query witness journal binding mismatch")
        if journal["phase"] not in self._journal_phases_for_witness(witness["witness_state"], witness["operation_kind"]):
            raise ValueError("query witness state does not match journal phase")
        query_plans: dict[str, dict[str, Any]] = {}
        for plan_sha256 in witness["participant_plan_sha256s"]:
            plan = self.evidence_registry.require(plan_sha256, "PMST_PARTICIPANT_PLAN_V1")
            if plan["operation_id"] != witness["operation_id"]:
                raise ValueError("query witness participant plan is foreign")
            query_plans[plan_sha256] = plan
        for receipt_sha256 in witness["observed_participant_receipt_sha256s"]:
            receipt = self.evidence_registry.require(receipt_sha256, "PMST_PARTICIPANT_RECEIPT_V1")
            plan = query_plans.get(receipt["plan_sha256"])
            if (
                receipt["operation_id"] != witness["operation_id"]
                or plan is None
                or receipt["participant_id"] != plan["participant_id"]
                or tuple(receipt["object_observations"]) != tuple(plan["object_commitments"])
            ):
                raise ValueError("query witness participant observation is foreign")
        return witness

    def _require_participant_receipts(
        self,
        digests: Sequence[str],
        participant_phase: str,
        allowed_statuses: set[str],
    ) -> list[dict[str, Any]]:
        if len(digests) < len(self.participant_plans) or not digests:
            raise ValueError("required participant receipt set is incomplete")
        receipts = [self.evidence_registry.require(digest, "PMST_PARTICIPANT_RECEIPT_V1") for digest in digests]
        by_plan: dict[str, dict[str, Any]] = {}
        for receipt in receipts:
            if receipt["operation_id"] != self.request["intent"]["operation_id"]:
                raise ValueError("participant receipt operation mismatch")
            if receipt["participant_phase"] != participant_phase or receipt["participant_status"] not in allowed_statuses:
                raise ValueError("participant receipt phase/status mismatch")
            if receipt["plan_sha256"] in by_plan:
                raise ValueError("duplicate participant receipt for plan")
            plan = self.participant_plans.get(receipt["plan_sha256"])
            if plan is None or receipt["participant_id"] != plan["participant_id"]:
                raise ValueError("participant receipt identity does not match plan")
            expected_sequence = {"PREPARE": 1, "COMMIT": 2, "RECONCILE": 3, "ABORT": 2}[participant_phase]
            if receipt["receipt_sequence"] != expected_sequence:
                raise ValueError("participant receipt sequence does not match phase history")
            prior_sequence = self.participant_receipt_sequences.get(receipt["plan_sha256"], 0)
            if receipt["receipt_sequence"] <= prior_sequence:
                raise ValueError("participant receipt sequence is not monotonic")
            if tuple(receipt["object_observations"]) != tuple(plan["object_commitments"]):
                raise ValueError("participant receipt observations do not match plan commitments")
            by_plan[receipt["plan_sha256"]] = receipt
        if set(by_plan) != set(self.participant_plans):
            raise ValueError("participant receipt plan set is incomplete or foreign")
        return receipts

    def _record_participant_receipts(self, receipts: Sequence[Mapping[str, Any]]) -> None:
        for receipt in receipts:
            digest = receipt["receipt_sha256"]
            self.accepted_participant_receipt_sha256s.append(digest)
            self.participant_receipt_sequences[receipt["plan_sha256"]] = receipt["receipt_sequence"]

    def _require_readback(
        self,
        digest: str,
        *,
        witness_sha256: str | None,
        observation: str,
    ) -> ReadbackBinding:
        binding = self.evidence_registry.require_readback(digest)
        intent = self.request["intent"]
        if (
            binding.operation_id != intent["operation_id"]
            or binding.intent_sha256 != intent["intent_sha256"]
            or binding.security_binding_sha256 != self.admission_context.security_binding_sha256
            or binding.operation_witness_sha256 != witness_sha256
            or binding.manifest_commit_observation != observation
        ):
            raise ValueError("readback binding does not match operation/witness")
        return binding

    def accept(self, value: Mapping[str, Any]) -> None:
        if self.complete or self.expected_phase is None:
            raise ValueError("operation is already complete")
        result = parse_phase_result(value).to_dict()
        self._binding_check(result)
        if result["phase"] != self.expected_phase:
            raise ValueError("phase is out of order")
        prior_effect_count = self.effect_count
        if result["effect_count"] < prior_effect_count:
            raise ValueError("effect_count must be monotonic")
        if result["phase"] == "RELEASE" and result["effect_count"] != prior_effect_count:
            raise ValueError("release must preserve the determined effect_count")
        self.effect_count = result["effect_count"]
        if result["reason_code"] is not None and result["reason_code"] not in self.reason_codes:
            self.reason_codes.append(result["reason_code"])
        phase = result["phase"]
        status = result["phase_status"]
        observation = result["manifest_commit_observation"]
        if self.observation != "NOT_OBSERVED" and observation != self.observation:
            raise ValueError("manifest observation must be monotonic")
        if phase in {"COMMIT_MANIFEST", "QUERY"}:
            self.observation = observation
        elif phase in {"RECONCILE", "TERMINAL", "RELEASE"} and observation != self.observation:
            raise ValueError("later phase must preserve manifest observation")

        kind = self.profile.operation_kind
        if phase == "ADMIT":
            self.expected_phase = "RELEASE" if status == "REJECTED_NO_EFFECT" else ("QUERY" if kind == "QUERY_OPERATION_V1" else "OPEN")
        elif phase == "OPEN":
            intent_payload = self.request["intent"]["payload"]
            if status == "CURRENT_NO_EFFECT" and result["payload"]["security_binding_sha256"] != self.admission_context.security_binding_sha256:
                raise ValueError("open security observation does not match admission context")
            if status == "CURRENT_NO_EFFECT":
                self.open_manifest_sha256 = result["payload"]["manifest_sha256"]
                self.open_state_coordinate_sha256 = result["payload"]["state_coordinate_sha256"]
            if status == "CURRENT_NO_EFFECT" and kind == "MANIFEST_TRANSITION_V1":
                if (
                    result["payload"]["manifest_sha256"] != intent_payload["prior_manifest_sha256"]
                    or result["payload"]["manifest_physical_identity_ref"]
                    != intent_payload["prior_manifest_physical_identity_ref"]
                ):
                    raise ValueError("open result does not match manifest predecessor commitment")
            if status == "CURRENT_NO_EFFECT" and kind == "PROJECT_READ_LEASE_V1":
                if (
                    result["payload"]["manifest_sha256"] != intent_payload["expected_manifest_sha256"]
                    or result["payload"]["state_coordinate_sha256"]
                    != intent_payload["expected_state_coordinate_sha256"]
                ):
                    raise ValueError("open result does not match read commitment")
            if status == "BLOCKED_NO_EFFECT":
                self.expected_phase = "RELEASE"
            elif kind == "PROJECT_READ_LEASE_V1":
                self.expected_phase = "READ"
            else:
                self.expected_phase = "PREPARE"
        elif phase == "PREPARE":
            if status == "PREPARED":
                journal = self._require_bound_journal(result["payload"]["journal_sha256"], "PREPARED")
                witness = self._require_bound_witness(result["payload"]["intent_witness_sha256"], {"PREPARED"})
                if witness["journal_sha256"] != journal["journal_sha256"]:
                    raise ValueError("prepared witness does not bind prepared journal")
                self.prepared_journal = journal
                self.prepared = True
                self.expected_phase = "PARTICIPANTS" if self.profile.participant_required else "STAGE"
            else:
                self.expected_phase = "RELEASE"
        elif phase == "PARTICIPANTS":
            if status == "PARTICIPANTS_PREPARED":
                receipts = self._require_participant_receipts(
                    result["payload"]["participant_receipt_sha256s"],
                    "PREPARE",
                    {"PREPARED_NO_COMMIT"},
                )
                self._record_participant_receipts(receipts)
            self.expected_phase = "STAGE" if status == "PARTICIPANTS_PREPARED" else "TERMINAL"
        elif phase == "STAGE":
            if status == "OBJECTS_STAGED" and not result["payload"]["staged_identity_sha256s"]:
                raise ValueError("staged operation requires at least one staged identity")
            if status == "OBJECTS_STAGED":
                self.staged_identity_sha256s = tuple(result["payload"]["staged_identity_sha256s"])
            self.expected_phase = "COMMIT_OBJECTS" if status == "OBJECTS_STAGED" else "TERMINAL"
        elif phase == "COMMIT_OBJECTS":
            if status == "OBJECTS_COMMITTED" and not result["payload"]["object_receipt_sha256s"]:
                raise ValueError("committed objects require at least one receipt")
            if status == "OBJECTS_COMMITTED" and self.profile.participant_required:
                participant_commit_digests = [
                    digest
                    for digest in result["payload"]["object_receipt_sha256s"]
                    if self.evidence_registry.optional(digest, "PMST_PARTICIPANT_RECEIPT_V1") is not None
                ]
                receipts = self._require_participant_receipts(
                    participant_commit_digests,
                    "COMMIT",
                    {"OBJECTS_COMMITTED"},
                )
                self._record_participant_receipts(receipts)
            if status == "OBJECT_OUTCOME_UNKNOWN" and self.profile.participant_required:
                participant_unknown_digests = [
                    digest
                    for digest in result["payload"]["object_receipt_sha256s"]
                    if self.evidence_registry.optional(digest, "PMST_PARTICIPANT_RECEIPT_V1") is not None
                ]
                receipts = self._require_participant_receipts(
                    participant_unknown_digests,
                    "COMMIT",
                    {"OBJECT_COMMIT_OUTCOME_UNKNOWN"},
                )
                self._record_participant_receipts(receipts)
            if status == "OBJECTS_COMMITTED" and kind not in MANIFEST_KINDS and result["effect_count"] <= prior_effect_count:
                raise ValueError("committed control object must advance effect_count")
            if status == "OBJECTS_COMMITTED":
                self.protected_object_observation = "COMMITTED"
            elif status == "OBJECT_OUTCOME_UNKNOWN":
                self.protected_object_observation = "UNKNOWN"
            if status == "OBJECT_OUTCOME_UNKNOWN":
                self.expected_phase = "RECONCILE" if self.profile.participant_required else "TERMINAL"
            elif kind in MANIFEST_KINDS:
                self.expected_phase = "COMMIT_MANIFEST"
            elif self.profile.participant_required:
                self.expected_phase = "RECONCILE"
            else:
                self.expected_phase = "TERMINAL"
        elif phase == "COMMIT_MANIFEST":
            intent_payload = self.request["intent"]["payload"]
            if result["payload"]["successor_manifest_sha256"] != intent_payload["successor_manifest_sha256"]:
                raise ValueError("manifest result does not match successor commitment")
            if kind == "MANIFEST_TRANSITION_V1" and result["payload"]["prior_manifest_sha256"] != intent_payload["prior_manifest_sha256"]:
                raise ValueError("manifest result does not match predecessor commitment")
            if status == "MANIFEST_COMMITTED" and result["effect_count"] <= prior_effect_count:
                raise ValueError("committed manifest must advance effect_count")
            self.operation_witness_sha256 = result["payload"]["operation_witness_sha256"]
            allowed_witness_states = {
                "MANIFEST_COMMITTED": {"COMMITTED_DURABLE"},
                "MANIFEST_NOT_COMMITTED": {"NOT_COMMITTED_PROVEN"},
                "MANIFEST_OUTCOME_UNKNOWN": {"UNKNOWN_QUARANTINED"},
            }[status]
            witness = self._require_bound_witness(
                self.operation_witness_sha256,
                allowed_witness_states,
                expected_receipts=self.accepted_participant_receipt_sha256s,
                expected_objects=self.staged_identity_sha256s,
            )
            if witness["manifest_commit_observation"] != result["manifest_commit_observation"]:
                raise ValueError("manifest result does not match witness observation")
            if status == "MANIFEST_COMMITTED" and (
                witness["committed_manifest_sha256"] != result["payload"]["successor_manifest_sha256"]
                or witness["committed_manifest_physical_identity_ref"]
                != result["payload"]["successor_physical_identity_ref"]
            ):
                raise ValueError("committed witness does not match manifest result content")
            self.commit_witness = witness
            self.expected_phase = "RECONCILE" if self.profile.participant_required else "TERMINAL"
        elif phase == "RECONCILE":
            participant_outcome = (
                self.observation
                if kind in MANIFEST_KINDS and self.observation != "NOT_OBSERVED"
                else self.protected_object_observation
            )
            statuses = {
                "RECONCILED": {
                    "COMMITTED": {"RECONCILED_COMMITTED"},
                    "NOT_COMMITTED": {"RECONCILED_NOT_COMMITTED"},
                    "UNKNOWN": set(),
                },
                "RECONCILIATION_REQUIRED": {
                    "COMMITTED": {"RECONCILIATION_REQUIRED_COMMITTED"},
                    "NOT_COMMITTED": {"RECONCILIATION_REQUIRED_NOT_COMMITTED"},
                    "UNKNOWN": {"RECONCILIATION_REQUIRED_UNKNOWN"},
                },
            }[status][participant_outcome]
            if not statuses:
                raise ValueError("unknown participant outcome cannot be marked reconciled")
            receipts = self._require_participant_receipts(
                result["payload"]["participant_terminal_receipt_sha256s"],
                "RECONCILE",
                statuses,
            )
            self._record_participant_receipts(receipts)
            self.reconciled = status == "RECONCILED"
            if not self.reconciled and "RECONCILIATION_REQUIRED" not in self.reason_codes:
                self.reason_codes.append("RECONCILIATION_REQUIRED")
            self.expected_phase = "TERMINAL"
        elif phase in {"READ", "QUERY"}:
            intent_payload = self.request["intent"]["payload"]
            if phase == "READ" and status == "READ_CURRENT_NO_EFFECT":
                if (
                    result["payload"]["manifest_sha256"] != intent_payload["expected_manifest_sha256"]
                    or result["payload"]["state_coordinate_sha256"] != intent_payload["expected_state_coordinate_sha256"]
                ):
                    raise ValueError("read result does not match intent commitment")
                readback = self._require_readback(
                    result["payload"]["readback_sha256"],
                    witness_sha256=None,
                    observation="NOT_OBSERVED",
                )
                if (
                    readback.manifest_sha256 != result["payload"]["manifest_sha256"]
                    or readback.state_coordinate_sha256 != result["payload"]["state_coordinate_sha256"]
                ):
                    raise ValueError("readback content binding does not match read result")
            if phase == "QUERY" and status in {
                "WITNESS_NOT_FOUND_NO_EFFECT",
                "WITNESS_EVIDENCE_UNAVAILABLE_NO_EFFECT",
                "READBACK_EVIDENCE_UNAVAILABLE_WITH_WITNESS",
            }:
                if (
                    result["payload"]["queried_operation_id"] != intent_payload["queried_operation_id"]
                    or result["payload"]["queried_intent_sha256"] != intent_payload["queried_intent_sha256"]
                ):
                    raise ValueError("query result does not match queried operation commitment")
            if phase == "QUERY" and status in {"COMMITTED_CURRENT", "COMMITTED_SUPERSEDED", "NOT_COMMITTED", "UNKNOWN_WITH_WITNESS"}:
                allowed_states = {
                    "COMMITTED_CURRENT": {"COMMITTED_DURABLE"},
                    "COMMITTED_SUPERSEDED": {"COMMITTED_DURABLE"},
                    "NOT_COMMITTED": {"NOT_COMMITTED_PROVEN"},
                    "UNKNOWN_WITH_WITNESS": {"UNKNOWN_QUARANTINED"},
                }[status]
                witness_sha256 = result["payload"]["operation_witness_sha256"]
                witness = self._require_query_witness(witness_sha256, allowed_states)
                if witness["manifest_commit_observation"] != result["manifest_commit_observation"]:
                    raise ValueError("query result does not preserve witness observation")
                readback = self._require_readback(
                    result["payload"]["fresh_readback_sha256"],
                    witness_sha256=witness_sha256,
                    observation=result["manifest_commit_observation"],
                )
                if witness["witness_state"] == "COMMITTED_DURABLE" and witness["operation_kind"] in MANIFEST_KINDS:
                    is_current = readback.manifest_sha256 == witness["committed_manifest_sha256"]
                    if status == "COMMITTED_CURRENT" and not is_current:
                        raise ValueError("query currentness contradicts committed witness/readback")
                    if status == "COMMITTED_SUPERSEDED" and is_current:
                        raise ValueError("query supersession contradicts committed witness/readback")
            if phase == "QUERY" and status == "READBACK_EVIDENCE_UNAVAILABLE_WITH_WITNESS":
                witness_sha256 = result["payload"]["operation_witness_sha256"]
                witness = self._require_query_witness(
                    witness_sha256,
                    {"PREPARED", "COMMITTED_DURABLE", "NOT_COMMITTED_PROVEN", "UNKNOWN_QUARANTINED"},
                )
                if witness["manifest_commit_observation"] != result["manifest_commit_observation"]:
                    raise ValueError("query readback failure must preserve known witness observation")
            self.outcome_result = result
            self.expected_phase = "RELEASE"
        elif phase == "TERMINAL":
            barrier = result["payload"]["admission_barrier_state"]
            terminal_states = {
                "COMMITTED_WITH_READBACK": {"COMMITTED_DURABLE"},
                "NOT_COMMITTED_PROVEN": {"NOT_COMMITTED_PROVEN"},
                "COMMIT_OUTCOME_UNKNOWN": {"UNKNOWN_QUARANTINED"},
                "BLOCKED_AFTER_PREPARE": {"PREPARED", "NOT_COMMITTED_PROVEN", "UNKNOWN_QUARANTINED"},
            }[status]
            witness_sha256 = result["payload"]["operation_witness_sha256"]
            witness = self._require_bound_witness(
                witness_sha256,
                terminal_states,
                expected_receipts=self.accepted_participant_receipt_sha256s,
                expected_objects=self.staged_identity_sha256s,
            )
            if self.commit_witness is not None:
                for field in (
                    "prior_observation_sha256",
                    "intended_successor_set_sha256",
                    "witness_state",
                    "manifest_commit_observation",
                    "committed_manifest_sha256",
                    "committed_manifest_physical_identity_ref",
                ):
                    if witness[field] != self.commit_witness[field]:
                        raise ValueError("terminal witness does not preserve committed witness content")
            if witness["manifest_commit_observation"] != result["manifest_commit_observation"]:
                raise ValueError("terminal result does not preserve witness observation")
            witness_journal = self.evidence_registry.require(
                witness["journal_sha256"],
                "PMST_TRANSACTION_JOURNAL_V1",
            )
            if barrier == "OPEN" and witness_journal["phase"] != "TERMINAL":
                raise ValueError("open admission barrier requires TERMINAL journal evidence")
            if result["payload"]["fresh_readback_sha256"] is not None:
                readback = self._require_readback(
                    result["payload"]["fresh_readback_sha256"],
                    witness_sha256=witness_sha256,
                    observation=result["manifest_commit_observation"],
                )
                if status == "COMMITTED_WITH_READBACK" and kind in MANIFEST_KINDS:
                    if readback.manifest_sha256 != witness["committed_manifest_sha256"]:
                        raise ValueError("terminal readback does not match committed manifest")
                elif kind not in MANIFEST_KINDS and self.open_manifest_sha256 is not None:
                    if readback.manifest_sha256 != self.open_manifest_sha256:
                        raise ValueError("control-operation readback changed pinned manifest")
            if status in {"BLOCKED_AFTER_PREPARE", "COMMIT_OUTCOME_UNKNOWN"} and barrier != "CLOSED":
                raise ValueError("unresolved outcome must keep admission barrier closed")
            if kind in MANIFEST_KINDS:
                required_observation = {
                    "COMMITTED_WITH_READBACK": "COMMITTED",
                    "NOT_COMMITTED_PROVEN": "NOT_COMMITTED",
                    "COMMIT_OUTCOME_UNKNOWN": "UNKNOWN",
                }.get(status)
                if required_observation is not None and result["manifest_commit_observation"] != required_observation:
                    raise ValueError("terminal status contradicts manifest outcome")
            if status in {"COMMITTED_WITH_READBACK", "NOT_COMMITTED_PROVEN"}:
                if self.profile.participant_required and not self.reconciled:
                    if barrier != "CLOSED" or "RECONCILIATION_REQUIRED" not in self.reason_codes:
                        raise ValueError("known unreconciled outcome must remain closed and recovery-required")
                elif barrier != "OPEN":
                    raise ValueError("known reconciled terminal outcome must open barrier")
            self.operation_witness_sha256 = witness_sha256
            self.outcome_result = result
            self.expected_phase = "RELEASE"
        elif phase == "RELEASE":
            if self.outcome_result is None and self.prepared:
                raise ValueError("prepared operation requires terminal outcome before release")
            self.expected_phase = None
            self.complete = True
        self.last_result = result

    def public_status(self) -> ContractRecord:
        if not self.complete:
            raise ValueError("operation is not complete")
        intent = self.request["intent"]
        outcome = self.outcome_result
        if outcome is None:
            status = "BLOCKED_NO_WRITE"
            witness = None
            readback = None
            effects = 0
            reasons = list(self.reason_codes)
        else:
            phase = outcome["phase"]
            phase_status = outcome["phase_status"]
            if phase == "TERMINAL":
                status = phase_status if phase_status != "BLOCKED_AFTER_PREPARE" else "COMMIT_OUTCOME_UNKNOWN"
                witness = outcome["payload"]["operation_witness_sha256"]
                readback = outcome["payload"]["fresh_readback_sha256"]
            elif phase == "READ":
                status = phase_status
                witness = None
                readback = outcome["payload"].get("readback_sha256")
            elif phase == "QUERY":
                status = _QUERY_PUBLIC[phase_status]
                witness = outcome["payload"].get("operation_witness_sha256")
                readback = outcome["payload"].get("fresh_readback_sha256")
            else:
                raise ValueError("outcome phase cannot be projected")
            effects = outcome["effect_count"]
            reasons = list(self.reason_codes)
        body = {
            "record_type": "PMST_PUBLIC_OPERATION_STATUS_V1",
            "protocol_version": PROTOCOL_VERSION,
            "operation_id": intent["operation_id"],
            "operation_kind": intent["operation_kind"],
            "operation_profile_id": intent["operation_profile_id"],
            "intent_sha256": intent["intent_sha256"],
            "request_sha256": self.request["request_sha256"],
            "status": status,
            "reason_codes": reasons,
            "operation_witness_sha256": witness,
            "readback_sha256": readback,
            "retry_allowed": False,
            "human_recovery_required": _PUBLIC_RULES[status][2] or "RECONCILIATION_REQUIRED" in reasons,
            "effect_count": effects,
        }
        return parse_public_status(seal_record(body, kind="public"))


class ScriptedFakePmstPort:
    """Fixture-only port. It can return records but cannot perform effects."""

    fixture_only = True
    live_effect_authorized = False

    def __init__(self, script: Sequence[Mapping[str, Any]]) -> None:
        self._script = [copy.deepcopy(dict(item)) for item in script]
        self.calls: list[str] = []

    def perform(
        self,
        phase: str,
        request: Mapping[str, Any],
        prior_result: Mapping[str, Any] | None,
    ) -> Mapping[str, Any]:
        del request, prior_result
        if not self._script:
            raise ValueError("fake port script is exhausted")
        result = self._script.pop(0)
        if result.get("phase") != phase:
            raise ValueError("fake port script phase mismatch")
        self.calls.append(phase)
        return result

    def assert_consumed(self) -> None:
        if self._script:
            raise ValueError("fake port script contains unused results")


def run_operation(
    request: Mapping[str, Any],
    profile: OperationProfile,
    port: ScriptedFakePmstPort,
    enrollment: Mapping[str, Any],
    profile_validation_receipt: Mapping[str, Any] | None,
    evidence_registry: PureEvidenceRegistry,
    nonce_ledger: PureNonceLedger,
    admission_context: AdmissionContext,
) -> ContractRecord:
    if type(port) is not ScriptedFakePmstPort or not port.fixture_only:
        raise ValueError("PMST-I1 accepts fixture-only ports")
    machine = PurePmstStateMachine(
        request,
        profile,
        enrollment,
        profile_validation_receipt,
        evidence_registry,
        nonce_ledger,
        admission_context,
    )
    for _ in range(16):
        if machine.complete:
            if isinstance(port, ScriptedFakePmstPort):
                port.assert_consumed()
            return machine.public_status()
        assert machine.expected_phase is not None
        phase = machine.expected_phase
        result = port.perform(phase, machine.request, machine.last_result)
        machine.accept(result)
    raise ValueError("operation exceeded phase bound")


__all__ = [
    "AdmissionContext",
    "ContractRecord",
    "NonceBinding",
    "OperationProfile",
    "PROTOCOL_VERSION",
    "PureNonceLedger",
    "PureEvidenceRegistry",
    "PurePmstStateMachine",
    "ReadbackBinding",
    "ScriptedFakePmstPort",
    "parse_enrollment",
    "parse_intent",
    "parse_journal",
    "parse_participant_plan",
    "parse_participant_receipt",
    "parse_phase_result",
    "parse_private_request",
    "parse_profile_validation_receipt",
    "parse_public_status",
    "parse_security_json",
    "parse_witness",
    "run_operation",
    "seal_record",
]
