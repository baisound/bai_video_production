"""TASK-101 pure existing-model import custody contract.

This module is deliberately effect-free.  It validates body-free public records
and offers an in-memory fake backend for contract tests.  It never opens a path,
reads model bytes, creates native custody, or issues a live capability.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
import json
import re
from types import MappingProxyType
from typing import Any, Mapping

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


MAX_JSON_BYTES = 131_072
MAX_JSON_DEPTH = 16
MAX_JSON_NODES = 4_096
MAX_MAPPING_KEYS = 256
MAX_ARRAY_ENTRIES = 64
MAX_STRING_SCALARS = 512
MAX_REASON_CODES = 16
MAX_POSITIVE_INT = 2_147_483_647
MAX_BYTE_COUNT = 9_007_199_254_740_991

CANONICAL_OWNER_TASK = "TASK-101"
INTENT_VERSION = "EXISTING_MODEL_IMPORT_INTENT_V1"
RECEIPT_VERSION = "EXISTING_MODEL_IMPORT_CUSTODY_RECEIPT_V1"
READBACK_VERSION = "EXISTING_MODEL_IMPORT_CUSTODY_READBACK_V1"
AUDIT_VERSION = "EXISTING_MODEL_IMPORT_CAPABILITY_AUDIT_V1"

_INTENT_DOMAIN = b"bai-video-production/task101/existing-model-import-intent/v1\0"
_RECEIPT_DOMAIN = b"bai-video-production/task101/existing-model-import-custody-receipt/v1\0"
_READBACK_DOMAIN = b"bai-video-production/task101/existing-model-import-custody-readback/v1\0"
_AUDIT_DOMAIN = b"bai-video-production/task101/existing-model-import-capability-audit/v1\0"

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$", re.ASCII)
_TIMESTAMP_RE = re.compile(
    r"^(?:[0-9]{4})-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])"
    r"T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]{1,6})?Z$",
    re.ASCII,
)
_FACTORY_KEY = object()

_ARTIFACT_FIELDS = {"role", "content_sha256", "byte_count", "opaque_source_identity_sha256"}
_RECEIPT_ARTIFACT_FIELDS = {
    "role",
    "content_sha256",
    "plaintext_byte_count",
    "source_physical_identity_sha256",
    "ciphertext_sha256",
    "ciphertext_byte_count",
    "destination_physical_identity_sha256",
}
_INTENT_FIELDS = {
    "contract_version", "record_type", "canonical_owner_task", "import_intent_id",
    "revision", "predecessor_sha256", "project_manifest_sha256",
    "voice_profile_revision_sha256", "model_candidate_revision_sha256",
    "model_artifact_binding_sha256", "h4_approval_sha256",
    "consent_currentness_sha256", "rights_currentness_sha256",
    "license_evidence_sha256", "historical_provenance_reconciliation_sha256",
    "provider_id", "engine_id", "model_id", "runtime_build_sha256",
    "model_pair_sha256", "artifacts", "protected_destination_class",
    "cipher_policy_sha256", "key_scope_sha256", "principal_access_policy_sha256",
    "retention_policy_sha256", "revocation_policy_sha256",
    "human_import_authority_sha256", "issued_at", "evaluated_at", "expires_at",
    "intent_sha256",
}
_RECEIPT_FIELDS = {
    "contract_version", "record_type", "canonical_owner_task", "operation_id",
    "import_intent_id", "intent_sha256", "project_manifest_sha256",
    "voice_profile_revision_sha256", "model_candidate_revision_sha256",
    "model_artifact_binding_sha256", "model_pair_sha256", "runtime_build_sha256",
    "source_physical_identity_set_sha256", "destination_instance_sha256",
    "sealed_inventory_sha256", "artifacts", "cipher_backend_sha256",
    "cipher_policy_sha256", "key_scope_sha256", "principal_access_policy_sha256",
    "import_event_chain_head_sha256", "seal_receipt_sha256",
    "durability_receipt_sha256", "physical_readback_sha256", "started_at",
    "sealed_at", "read_back_at", "expires_at", "completion_state", "receipt_sha256",
}
_READBACK_FIELDS = {
    "contract_version", "record_type", "canonical_owner_task", "readback_id",
    "operation_id", "import_intent_id", "intent_sha256", "receipt_sha256",
    "destination_instance_sha256", "sealed_inventory_sha256",
    "current_inventory_sha256", "current_physical_identity_set_sha256",
    "model_pair_sha256", "runtime_build_sha256", "custody_generation",
    "revocation_state", "decision", "reason_codes", "evaluated_at", "expires_at",
    "readback_sha256",
}
_AUDIT_FIELDS = {
    "contract_version", "record_type", "canonical_owner_task", "capability_id",
    "operation_id", "purpose", "consumer_task", "custody_readback_sha256",
    "model_pair_sha256", "state", "predecessor_sha256", "issued_at", "expires_at",
    "transitioned_at", "completed_at", "audit_sha256",
}

_INTENT_DIGEST_FIELDS = {
    "project_manifest_sha256", "voice_profile_revision_sha256",
    "model_candidate_revision_sha256", "model_artifact_binding_sha256",
    "h4_approval_sha256", "consent_currentness_sha256", "rights_currentness_sha256",
    "license_evidence_sha256", "historical_provenance_reconciliation_sha256",
    "runtime_build_sha256", "model_pair_sha256", "cipher_policy_sha256",
    "key_scope_sha256", "principal_access_policy_sha256", "retention_policy_sha256",
    "revocation_policy_sha256", "human_import_authority_sha256",
}
_RECEIPT_DIGEST_FIELDS = {
    "intent_sha256", "project_manifest_sha256", "voice_profile_revision_sha256",
    "model_candidate_revision_sha256", "model_artifact_binding_sha256",
    "model_pair_sha256", "runtime_build_sha256", "source_physical_identity_set_sha256",
    "destination_instance_sha256", "sealed_inventory_sha256", "cipher_backend_sha256",
    "cipher_policy_sha256", "key_scope_sha256", "principal_access_policy_sha256",
    "import_event_chain_head_sha256", "seal_receipt_sha256",
    "durability_receipt_sha256", "physical_readback_sha256",
}
_READBACK_DIGEST_FIELDS = {
    "intent_sha256", "receipt_sha256", "destination_instance_sha256",
    "sealed_inventory_sha256", "current_inventory_sha256",
    "current_physical_identity_set_sha256", "model_pair_sha256", "runtime_build_sha256",
}
_AUDIT_DIGEST_FIELDS = {"custody_readback_sha256", "model_pair_sha256"}

_REASON_CODES = {
    "CURRENT", "STALE", "REVOKED", "REVOCATION_UNKNOWN", "INTENT_MISMATCH",
    "RECEIPT_MISMATCH", "INVENTORY_MISMATCH", "PHYSICAL_IDENTITY_MISMATCH",
    "PAIR_IDENTITY_MISMATCH", "RUNTIME_IDENTITY_MISMATCH", "COMPLETION_UNKNOWN",
}
_AUDIT_STATES = {
    "ISSUED", "OPEN_STARTED", "CONSUMED", "EXPIRED", "COMPLETION_UNKNOWN", "FAILED_CLOSED",
}
_TERMINAL_AUDIT_STATES = {"CONSUMED", "EXPIRED", "COMPLETION_UNKNOWN", "FAILED_CLOSED"}
_AUDIT_TRANSITIONS = {
    "ISSUED": {"OPEN_STARTED", "EXPIRED", "FAILED_CLOSED"},
    "OPEN_STARTED": {"CONSUMED", "COMPLETION_UNKNOWN", "FAILED_CLOSED"},
    "CONSUMED": set(),
    "EXPIRED": set(),
    "COMPLETION_UNKNOWN": set(),
    "FAILED_CLOSED": set(),
}
_AUDIT_MUTABLE_FIELDS = {
    "state", "predecessor_sha256", "transitioned_at", "completed_at", "audit_sha256",
}


def _exact(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields are not exact")


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is not a valid Id")
    return value


def _digest_value(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a digest")
    return validate_sha256(value, field_name=name)


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= MAX_POSITIVE_INT:
        raise ValueError(f"{name} is outside PositiveInt")
    return value


def _byte_count(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= MAX_BYTE_COUNT:
        raise ValueError(f"{name} is outside ByteCount")
    return value


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not _TIMESTAMP_RE.fullmatch(value):
        raise ValueError(f"{name} must be a calendar-valid UTC Timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be a calendar-valid UTC Timestamp") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%S") != value[:19]:
        raise ValueError(f"{name} must be a calendar-valid UTC Timestamp")
    return parsed


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


def _record_digest(body: Mapping[str, Any], field: str, domain: bytes) -> str:
    value = copy.deepcopy(dict(body))
    value.pop(field, None)
    return sha256_bytes(domain + canonical_json_bytes(value))


def _verify_record_digest(body: Mapping[str, Any], field: str, domain: bytes) -> None:
    _digest_value(body.get(field), field)
    if body[field] != _record_digest(body, field, domain):
        raise ValueError(f"{field} does not match canonical content")


def _validate_discriminator(body: Mapping[str, Any], version: str, record_type: str) -> None:
    if (
        body.get("contract_version") != version
        or body.get("record_type") != record_type
        or body.get("canonical_owner_task") != CANONICAL_OWNER_TASK
    ):
        raise ValueError(f"{record_type} discriminator mismatch")


def _validate_artifacts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("artifacts must contain exactly SOVITS then GPT")
    result: list[dict[str, Any]] = []
    for expected_role, raw in zip(("SOVITS", "GPT"), value, strict=True):
        _exact(raw, _ARTIFACT_FIELDS, "ExistingModelImportArtifactV1")
        if raw["role"] != expected_role:
            raise ValueError("artifact role order must be SOVITS then GPT")
        _digest_value(raw["content_sha256"], "content_sha256")
        _byte_count(raw["byte_count"], "byte_count")
        _digest_value(raw["opaque_source_identity_sha256"], "opaque_source_identity_sha256")
        result.append(copy.deepcopy(dict(raw)))
    return result


def _validate_receipt_artifacts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("receipt artifacts must contain exactly SOVITS then GPT")
    result: list[dict[str, Any]] = []
    for expected_role, raw in zip(("SOVITS", "GPT"), value, strict=True):
        _exact(raw, _RECEIPT_ARTIFACT_FIELDS, "ExistingModelImportReceiptArtifactV1")
        if raw["role"] != expected_role:
            raise ValueError("receipt artifact role order must be SOVITS then GPT")
        for field in (
            "content_sha256", "source_physical_identity_sha256", "ciphertext_sha256",
            "destination_physical_identity_sha256",
        ):
            _digest_value(raw[field], field)
        _byte_count(raw["plaintext_byte_count"], "plaintext_byte_count")
        _byte_count(raw["ciphertext_byte_count"], "ciphertext_byte_count")
        result.append(copy.deepcopy(dict(raw)))
    return result


@dataclass(frozen=True, slots=True, init=False)
class _ImmutableRecord:
    data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _FACTORY_KEY:
            raise TypeError("record must be created by its validated factory")
        object.__setattr__(self, "data", data)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.data)


@dataclass(frozen=True, slots=True, init=False)
class ExistingModelImportIntentV1(_ImmutableRecord):
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExistingModelImportIntentV1":
        body = copy.deepcopy(dict(value))
        _exact(body, _INTENT_FIELDS, "ExistingModelImportIntentV1")
        _validate_discriminator(body, INTENT_VERSION, "ExistingModelImportIntentV1")
        _identifier(body["import_intent_id"], "import_intent_id")
        revision = _positive_int(body["revision"], "revision")
        predecessor = body["predecessor_sha256"]
        if revision == 1:
            if predecessor is not None:
                raise ValueError("revision 1 predecessor_sha256 must be null")
        else:
            _digest_value(predecessor, "predecessor_sha256")
        for field in _INTENT_DIGEST_FIELDS:
            _digest_value(body[field], field)
        for field in ("provider_id", "engine_id", "model_id"):
            _identifier(body[field], field)
        body["artifacts"] = _validate_artifacts(body["artifacts"])
        if body["protected_destination_class"] != "BVP_OWNER_VOICE_MODEL_CUSTODY_V1":
            raise ValueError("protected_destination_class mismatch")
        issued = _timestamp(body["issued_at"], "issued_at")
        evaluated = _timestamp(body["evaluated_at"], "evaluated_at")
        expires = _timestamp(body["expires_at"], "expires_at")
        if not issued <= evaluated < expires:
            raise ValueError("intent timestamps are not ordered")
        _verify_record_digest(body, "intent_sha256", _INTENT_DOMAIN)
        return cls(_freeze(body), _token=_FACTORY_KEY)

    @property
    def intent_sha256(self) -> str:
        return str(self.data["intent_sha256"])


@dataclass(frozen=True, slots=True, init=False)
class ExistingModelImportCustodyReceiptV1(_ImmutableRecord):
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExistingModelImportCustodyReceiptV1":
        body = copy.deepcopy(dict(value))
        _exact(body, _RECEIPT_FIELDS, "ExistingModelImportCustodyReceiptV1")
        _validate_discriminator(body, RECEIPT_VERSION, "ExistingModelImportCustodyReceiptV1")
        for field in ("operation_id", "import_intent_id"):
            _identifier(body[field], field)
        for field in _RECEIPT_DIGEST_FIELDS:
            _digest_value(body[field], field)
        body["artifacts"] = _validate_receipt_artifacts(body["artifacts"])
        started = _timestamp(body["started_at"], "started_at")
        sealed = _timestamp(body["sealed_at"], "sealed_at")
        read_back = _timestamp(body["read_back_at"], "read_back_at")
        expires = _timestamp(body["expires_at"], "expires_at")
        if not started <= sealed <= read_back < expires:
            raise ValueError("receipt timestamps are not ordered")
        if body["completion_state"] != "SEALED_CURRENT":
            raise ValueError("receipt completion_state mismatch")
        _verify_record_digest(body, "receipt_sha256", _RECEIPT_DOMAIN)
        return cls(_freeze(body), _token=_FACTORY_KEY)

    @property
    def receipt_sha256(self) -> str:
        return str(self.data["receipt_sha256"])


@dataclass(frozen=True, slots=True, init=False)
class ExistingModelImportCustodyReadbackV1(_ImmutableRecord):
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExistingModelImportCustodyReadbackV1":
        body = copy.deepcopy(dict(value))
        _exact(body, _READBACK_FIELDS, "ExistingModelImportCustodyReadbackV1")
        _validate_discriminator(body, READBACK_VERSION, "ExistingModelImportCustodyReadbackV1")
        for field in ("readback_id", "operation_id", "import_intent_id"):
            _identifier(body[field], field)
        for field in _READBACK_DIGEST_FIELDS:
            _digest_value(body[field], field)
        _positive_int(body["custody_generation"], "custody_generation")
        if body["revocation_state"] not in {"NOT_REVOKED", "REVOKED", "UNKNOWN"}:
            raise ValueError("revocation_state is unsupported")
        if body["decision"] not in {
            "CURRENT", "STALE", "REVOKED", "IDENTITY_MISMATCH", "COMPLETION_UNKNOWN"
        }:
            raise ValueError("decision is unsupported")
        reason_codes = body["reason_codes"]
        if (
            not isinstance(reason_codes, list)
            or not 1 <= len(reason_codes) <= MAX_REASON_CODES
            or len(set(reason_codes)) != len(reason_codes)
            or reason_codes != sorted(reason_codes)
            or any(code not in _REASON_CODES for code in reason_codes)
        ):
            raise ValueError("reason_codes must be unique, closed and lexicographically ordered")
        decision = body["decision"]
        revocation = body["revocation_state"]
        if decision == "CURRENT":
            if revocation != "NOT_REVOKED" or reason_codes != ["CURRENT"]:
                raise ValueError("CURRENT readback requires NOT_REVOKED and exact CURRENT reason")
            if body["current_inventory_sha256"] != body["sealed_inventory_sha256"]:
                raise ValueError("CURRENT inventory must equal sealed inventory")
        elif decision == "STALE" and "STALE" not in reason_codes:
            raise ValueError("STALE readback requires STALE reason")
        elif decision == "REVOKED" and (revocation != "REVOKED" or "REVOKED" not in reason_codes):
            raise ValueError("REVOKED readback requires revoked state and reason")
        elif decision == "IDENTITY_MISMATCH" and not any(code.endswith("_MISMATCH") for code in reason_codes):
            raise ValueError("IDENTITY_MISMATCH requires a mismatch reason")
        elif decision == "COMPLETION_UNKNOWN" and not (
            {"COMPLETION_UNKNOWN", "REVOCATION_UNKNOWN"} & set(reason_codes)
        ):
            raise ValueError("COMPLETION_UNKNOWN requires an unknown reason")
        evaluated = _timestamp(body["evaluated_at"], "evaluated_at")
        expires = _timestamp(body["expires_at"], "expires_at")
        if decision == "CURRENT" and evaluated >= expires:
            raise ValueError("CURRENT readback must be unexpired")
        _verify_record_digest(body, "readback_sha256", _READBACK_DOMAIN)
        return cls(_freeze(body), _token=_FACTORY_KEY)

    @property
    def readback_sha256(self) -> str:
        return str(self.data["readback_sha256"])


def _validate_audit_intrinsic(body: dict[str, Any]) -> None:
    _exact(body, _AUDIT_FIELDS, "ExistingModelImportCapabilityAuditV1")
    _validate_discriminator(body, AUDIT_VERSION, "ExistingModelImportCapabilityAuditV1")
    for field in ("capability_id", "operation_id"):
        _identifier(body[field], field)
    if body["purpose"] not in {"INSTALLED_IDENTITY_OBSERVATION", "LOCAL_NARRATION_INFERENCE"}:
        raise ValueError("purpose is unsupported")
    expected_consumer = {
        "INSTALLED_IDENTITY_OBSERVATION": "TASK-100",
        "LOCAL_NARRATION_INFERENCE": "TASK-075",
    }[body["purpose"]]
    if body["consumer_task"] != expected_consumer:
        raise ValueError("consumer_task does not match purpose")
    for field in _AUDIT_DIGEST_FIELDS:
        _digest_value(body[field], field)
    state = body["state"]
    if state not in _AUDIT_STATES:
        raise ValueError("state is unsupported")
    predecessor_sha = body["predecessor_sha256"]
    if state == "ISSUED":
        if predecessor_sha is not None:
            raise ValueError("ISSUED predecessor_sha256 must be null")
    else:
        _digest_value(predecessor_sha, "predecessor_sha256")
    issued = _timestamp(body["issued_at"], "issued_at")
    expires = _timestamp(body["expires_at"], "expires_at")
    transitioned = _timestamp(body["transitioned_at"], "transitioned_at")
    if not issued < expires or issued > transitioned:
        raise ValueError("audit timestamps are not ordered")
    if state == "ISSUED" and transitioned != issued:
        raise ValueError("ISSUED transitioned_at must equal issued_at")
    if state == "OPEN_STARTED" and transitioned >= expires:
        raise ValueError("OPEN_STARTED must precede expiry")
    if state == "EXPIRED" and transitioned < expires:
        raise ValueError("EXPIRED must be at or after expiry")
    completed_at = body["completed_at"]
    if state in {"ISSUED", "OPEN_STARTED"}:
        if completed_at is not None:
            raise ValueError("nonterminal audit completed_at must be null")
    elif completed_at != body["transitioned_at"]:
        raise ValueError("terminal audit completed_at must equal transitioned_at")
    _verify_record_digest(body, "audit_sha256", _AUDIT_DOMAIN)


def _validate_audit_transition(current: Mapping[str, Any], predecessor: Mapping[str, Any]) -> None:
    if current["predecessor_sha256"] != predecessor["audit_sha256"]:
        raise ValueError("predecessor_sha256 does not link the exact predecessor")
    for field in _AUDIT_FIELDS - _AUDIT_MUTABLE_FIELDS:
        if current[field] != predecessor[field]:
            raise ValueError(f"audit immutable field changed: {field}")
    if current["state"] not in _AUDIT_TRANSITIONS[predecessor["state"]]:
        raise ValueError("audit state transition is not allowed")
    if _timestamp(predecessor["transitioned_at"], "predecessor.transitioned_at") > _timestamp(
        current["transitioned_at"], "transitioned_at"
    ):
        raise ValueError("audit transitioned_at moved backward")


@dataclass(frozen=True, slots=True, init=False)
class ExistingModelImportCapabilityAuditV1(_ImmutableRecord):
    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        predecessor: "ExistingModelImportCapabilityAuditV1 | Mapping[str, Any] | None" = None,
    ) -> "ExistingModelImportCapabilityAuditV1":
        body = copy.deepcopy(dict(value))
        _validate_audit_intrinsic(body)
        if body["state"] != "ISSUED":
            if predecessor is None:
                raise ValueError("noninitial audit requires its canonical predecessor")
            predecessor_body = predecessor.to_dict() if type(predecessor) is cls else copy.deepcopy(dict(predecessor))
            _validate_audit_intrinsic(predecessor_body)
            _validate_audit_transition(body, predecessor_body)
        elif predecessor is not None:
            raise ValueError("initial ISSUED audit must not provide a predecessor")
        return cls(_freeze(body), _token=_FACTORY_KEY)

    @property
    def audit_sha256(self) -> str:
        return str(self.data["audit_sha256"])


def create_existing_model_import_intent(**fields: Any) -> ExistingModelImportIntentV1:
    body = {
        "contract_version": INTENT_VERSION,
        "record_type": "ExistingModelImportIntentV1",
        "canonical_owner_task": CANONICAL_OWNER_TASK,
        **fields,
    }
    body["intent_sha256"] = _record_digest(body, "intent_sha256", _INTENT_DOMAIN)
    return ExistingModelImportIntentV1.from_dict(body)


def create_existing_model_import_custody_receipt(**fields: Any) -> ExistingModelImportCustodyReceiptV1:
    body = {
        "contract_version": RECEIPT_VERSION,
        "record_type": "ExistingModelImportCustodyReceiptV1",
        "canonical_owner_task": CANONICAL_OWNER_TASK,
        **fields,
    }
    body["receipt_sha256"] = _record_digest(body, "receipt_sha256", _RECEIPT_DOMAIN)
    return ExistingModelImportCustodyReceiptV1.from_dict(body)


def create_existing_model_import_custody_readback(**fields: Any) -> ExistingModelImportCustodyReadbackV1:
    body = {
        "contract_version": READBACK_VERSION,
        "record_type": "ExistingModelImportCustodyReadbackV1",
        "canonical_owner_task": CANONICAL_OWNER_TASK,
        **fields,
    }
    body["readback_sha256"] = _record_digest(body, "readback_sha256", _READBACK_DOMAIN)
    return ExistingModelImportCustodyReadbackV1.from_dict(body)


def create_existing_model_import_capability_audit(
    *,
    predecessor: ExistingModelImportCapabilityAuditV1 | None = None,
    **fields: Any,
) -> ExistingModelImportCapabilityAuditV1:
    body = {
        "contract_version": AUDIT_VERSION,
        "record_type": "ExistingModelImportCapabilityAuditV1",
        "canonical_owner_task": CANONICAL_OWNER_TASK,
        **fields,
    }
    body["audit_sha256"] = _record_digest(body, "audit_sha256", _AUDIT_DOMAIN)
    return ExistingModelImportCapabilityAuditV1.from_dict(body, predecessor=predecessor)


def evaluate_existing_model_import_custody_readback(
    receipt: ExistingModelImportCustodyReceiptV1,
    *,
    readback_id: str,
    custody_generation: int,
    current_inventory_sha256: str,
    current_physical_identity_set_sha256: str,
    observed_model_pair_sha256: str,
    observed_runtime_build_sha256: str,
    revocation_state: str,
    evaluated_at: str,
    expires_at: str,
    physical_identity_matches: bool,
) -> ExistingModelImportCustodyReadbackV1:
    """Purely derive a closed readback decision from body-free observations."""
    if type(receipt) is not ExistingModelImportCustodyReceiptV1:
        raise TypeError("receipt must be an exact validated custody receipt")
    receipt_body = ExistingModelImportCustodyReceiptV1.from_dict(receipt.to_dict()).to_dict()
    reasons: set[str] = set()
    if revocation_state == "REVOKED":
        decision = "REVOKED"
        reasons.add("REVOKED")
    elif revocation_state == "UNKNOWN":
        decision = "COMPLETION_UNKNOWN"
        reasons.add("REVOCATION_UNKNOWN")
    else:
        if current_inventory_sha256 != receipt_body["sealed_inventory_sha256"]:
            reasons.add("INVENTORY_MISMATCH")
        if not physical_identity_matches:
            reasons.add("PHYSICAL_IDENTITY_MISMATCH")
        if observed_model_pair_sha256 != receipt_body["model_pair_sha256"]:
            reasons.add("PAIR_IDENTITY_MISMATCH")
        if observed_runtime_build_sha256 != receipt_body["runtime_build_sha256"]:
            reasons.add("RUNTIME_IDENTITY_MISMATCH")
        if reasons:
            decision = "IDENTITY_MISMATCH"
        else:
            decision = "CURRENT"
            reasons.add("CURRENT")
    return create_existing_model_import_custody_readback(
        readback_id=readback_id,
        operation_id=receipt_body["operation_id"],
        import_intent_id=receipt_body["import_intent_id"],
        intent_sha256=receipt_body["intent_sha256"],
        receipt_sha256=receipt_body["receipt_sha256"],
        destination_instance_sha256=receipt_body["destination_instance_sha256"],
        sealed_inventory_sha256=receipt_body["sealed_inventory_sha256"],
        current_inventory_sha256=current_inventory_sha256,
        current_physical_identity_set_sha256=current_physical_identity_set_sha256,
        model_pair_sha256=observed_model_pair_sha256,
        runtime_build_sha256=observed_runtime_build_sha256,
        custody_generation=custody_generation,
        revocation_state=revocation_state,
        decision=decision,
        reason_codes=sorted(reasons),
        evaluated_at=evaluated_at,
        expires_at=expires_at,
    )


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("security JSON contains duplicate object keys")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite number {value} is forbidden")


def _validate_json_limits(value: Any) -> None:
    nodes = 0
    pending: list[tuple[Any, int]] = [(value, 1)]
    while pending:
        current, depth = pending.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            raise ValueError("security JSON exceeds node or depth limits")
        if isinstance(current, Mapping):
            if len(current) > MAX_MAPPING_KEYS:
                raise ValueError("security JSON mapping is too large")
            for key, item in current.items():
                if not isinstance(key, str) or len(key) > MAX_STRING_SCALARS:
                    raise ValueError("security JSON key is invalid or too long")
                pending.append((item, depth + 1))
        elif isinstance(current, list):
            if len(current) > MAX_ARRAY_ENTRIES:
                raise ValueError("security JSON array is too large")
            pending.extend((item, depth + 1) for item in current)
        elif isinstance(current, str) and len(current) > MAX_STRING_SCALARS:
            raise ValueError("security JSON string is too long")


def parse_existing_model_import_json(
    payload: bytes,
    *,
    predecessor: ExistingModelImportCapabilityAuditV1 | Mapping[str, Any] | None = None,
) -> (
    ExistingModelImportIntentV1
    | ExistingModelImportCustodyReceiptV1
    | ExistingModelImportCustodyReadbackV1
    | ExistingModelImportCapabilityAuditV1
):
    if (
        not isinstance(payload, bytes)
        or not payload
        or len(payload) > MAX_JSON_BYTES
        or payload.startswith(b"\xef\xbb\xbf")
    ):
        raise ValueError("security JSON is empty, oversized, non-bytes, or contains BOM")
    try:
        text = payload.decode("utf-8", errors="strict")
        decoder = json.JSONDecoder(object_pairs_hook=_pairs_no_duplicates, parse_constant=_reject_constant)
        value, end = decoder.raw_decode(text)
    except RecursionError as exc:
        raise ValueError("security JSON has excessive depth") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("security JSON is invalid") from exc
    if end != len(text):
        raise ValueError("security JSON contains trailing data")
    _validate_json_limits(value)
    if not isinstance(value, Mapping):
        raise ValueError("security JSON root must be an object")
    record_type = value.get("record_type")
    if record_type == "ExistingModelImportIntentV1":
        if predecessor is not None:
            raise ValueError("predecessor is only valid for a capability audit")
        return ExistingModelImportIntentV1.from_dict(value)
    if record_type == "ExistingModelImportCustodyReceiptV1":
        if predecessor is not None:
            raise ValueError("predecessor is only valid for a capability audit")
        return ExistingModelImportCustodyReceiptV1.from_dict(value)
    if record_type == "ExistingModelImportCustodyReadbackV1":
        if predecessor is not None:
            raise ValueError("predecessor is only valid for a capability audit")
        return ExistingModelImportCustodyReadbackV1.from_dict(value)
    if record_type == "ExistingModelImportCapabilityAuditV1":
        return ExistingModelImportCapabilityAuditV1.from_dict(value, predecessor=predecessor)
    raise ValueError("security JSON record_type is unsupported")


class FakeExistingModelImportCustodyBackend:
    """In-memory, body-free contract backend.  It has no native effect surface."""

    def __init__(self) -> None:
        self._intents: dict[str, list[ExistingModelImportIntentV1]] = {}
        self._receipts: dict[str, ExistingModelImportCustodyReceiptV1] = {}
        self._readbacks: dict[str, ExistingModelImportCustodyReadbackV1] = {}
        self._audits: dict[str, ExistingModelImportCapabilityAuditV1] = {}

    def admit_intent(self, intent: ExistingModelImportIntentV1) -> ExistingModelImportIntentV1:
        if type(intent) is not ExistingModelImportIntentV1:
            raise TypeError("intent must be an exact validated record")
        canonical = ExistingModelImportIntentV1.from_dict(intent.to_dict())
        body = canonical.to_dict()
        history = self._intents.setdefault(body["import_intent_id"], [])
        if history and history[-1].intent_sha256 == canonical.intent_sha256:
            return history[-1]
        expected_revision = len(history) + 1
        expected_predecessor = history[-1].intent_sha256 if history else None
        if body["revision"] != expected_revision or body["predecessor_sha256"] != expected_predecessor:
            raise ValueError("intent revision does not extend the exact current predecessor")
        history.append(canonical)
        return canonical

    def admit_receipt(
        self,
        receipt: ExistingModelImportCustodyReceiptV1,
    ) -> ExistingModelImportCustodyReceiptV1:
        if type(receipt) is not ExistingModelImportCustodyReceiptV1:
            raise TypeError("receipt must be an exact validated record")
        canonical = ExistingModelImportCustodyReceiptV1.from_dict(receipt.to_dict())
        body = canonical.to_dict()
        existing = self._receipts.get(body["operation_id"])
        if existing is not None:
            if existing.receipt_sha256 == canonical.receipt_sha256:
                return existing
            raise ValueError("operation_id replay differs from the current receipt")
        history = self._intents.get(body["import_intent_id"])
        if not history:
            raise ValueError("receipt has no admitted intent")
        intent = history[-1].to_dict()
        equality = {
            "intent_sha256": "intent_sha256",
            "project_manifest_sha256": "project_manifest_sha256",
            "voice_profile_revision_sha256": "voice_profile_revision_sha256",
            "model_candidate_revision_sha256": "model_candidate_revision_sha256",
            "model_artifact_binding_sha256": "model_artifact_binding_sha256",
            "model_pair_sha256": "model_pair_sha256",
            "runtime_build_sha256": "runtime_build_sha256",
            "cipher_policy_sha256": "cipher_policy_sha256",
            "key_scope_sha256": "key_scope_sha256",
            "principal_access_policy_sha256": "principal_access_policy_sha256",
        }
        for receipt_field, intent_field in equality.items():
            if body[receipt_field] != intent[intent_field]:
                raise ValueError(f"receipt does not equal intent field: {receipt_field}")
        expected_artifacts = [
            (item["role"], item["content_sha256"], item["byte_count"])
            for item in intent["artifacts"]
        ]
        actual_artifacts = [
            (item["role"], item["content_sha256"], item["plaintext_byte_count"])
            for item in body["artifacts"]
        ]
        if actual_artifacts != expected_artifacts:
            raise ValueError("receipt artifact inventory does not equal intent")
        self._receipts[body["operation_id"]] = canonical
        return canonical

    def admit_readback(
        self,
        readback: ExistingModelImportCustodyReadbackV1,
    ) -> ExistingModelImportCustodyReadbackV1:
        if type(readback) is not ExistingModelImportCustodyReadbackV1:
            raise TypeError("readback must be an exact validated record")
        canonical = ExistingModelImportCustodyReadbackV1.from_dict(readback.to_dict())
        body = canonical.to_dict()
        receipt = self._receipts.get(body["operation_id"])
        if receipt is None:
            raise ValueError("readback has no admitted receipt")
        receipt_body = receipt.to_dict()
        for field in (
            "import_intent_id", "intent_sha256", "receipt_sha256",
            "destination_instance_sha256", "sealed_inventory_sha256",
        ):
            expected = receipt_body["receipt_sha256"] if field == "receipt_sha256" else receipt_body[field]
            if body[field] != expected:
                raise ValueError(f"readback does not equal receipt field: {field}")
        if body["decision"] == "CURRENT" and (
            body["model_pair_sha256"] != receipt_body["model_pair_sha256"]
            or body["runtime_build_sha256"] != receipt_body["runtime_build_sha256"]
        ):
            raise ValueError("CURRENT readback pair/runtime does not equal receipt")
        self._readbacks[body["readback_sha256"]] = canonical
        return canonical

    def admit_capability_audit(
        self,
        audit: ExistingModelImportCapabilityAuditV1,
    ) -> ExistingModelImportCapabilityAuditV1:
        if type(audit) is not ExistingModelImportCapabilityAuditV1:
            raise TypeError("audit must be an exact validated record")
        body = audit.to_dict()
        current = self._audits.get(body["capability_id"])
        if current is not None and current.audit_sha256 == body["audit_sha256"]:
            return current
        canonical = ExistingModelImportCapabilityAuditV1.from_dict(body, predecessor=current)
        if current is None:
            readback = self._readbacks.get(body["custody_readback_sha256"])
            if readback is None or readback.data["decision"] != "CURRENT":
                raise ValueError("initial capability audit requires an admitted CURRENT readback")
            if readback.data["model_pair_sha256"] != body["model_pair_sha256"]:
                raise ValueError("capability audit model pair does not equal readback")
        self._audits[body["capability_id"]] = canonical
        return canonical

    def current_audit(self, capability_id: str) -> ExistingModelImportCapabilityAuditV1:
        _identifier(capability_id, "capability_id")
        try:
            return self._audits[capability_id]
        except KeyError as exc:
            raise ValueError("capability_id is unknown") from exc


__all__ = [
    "AUDIT_VERSION",
    "CANONICAL_OWNER_TASK",
    "ExistingModelImportCapabilityAuditV1",
    "ExistingModelImportCustodyReadbackV1",
    "ExistingModelImportCustodyReceiptV1",
    "ExistingModelImportIntentV1",
    "FakeExistingModelImportCustodyBackend",
    "INTENT_VERSION",
    "MAX_JSON_BYTES",
    "READBACK_VERSION",
    "RECEIPT_VERSION",
    "create_existing_model_import_capability_audit",
    "create_existing_model_import_custody_readback",
    "create_existing_model_import_custody_receipt",
    "create_existing_model_import_intent",
    "evaluate_existing_model_import_custody_readback",
    "parse_existing_model_import_json",
]
