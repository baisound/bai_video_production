"""Pure TASK-058 P1A montage-learning admission receipt contract.

This module validates caller-supplied receipt bodies and deterministic identity
bindings. It performs no filesystem, store, importer, queue, connector, network,
database, native, provider, receipt-minting, or canonical-admission operation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from types import MappingProxyType
from typing import Any, Mapping

from .montage_learning_bridge_contracts import (
    EXACT_CONTRACT_PROFILE,
    GENERIC_CONTRACT_PROFILE,
)


SCHEMA_VERSION = "2.0.0"
MESSAGE_TYPE = "BvpMontageLearningAdmissionReceipt"
CONTRACT_PROFILE = "bvp-task058-montage-learning-admission-receipt-v2"

EXACT_EVIDENCE = "EXACT_EVIDENCE"
GENERIC_OBSERVATION = "GENERIC_OBSERVATION"
ACCEPTED = "ACCEPTED"
DUPLICATE = "DUPLICATE"
REJECTED = "REJECTED"
REVIEW_REQUIRED = "REVIEW_REQUIRED"

IDEMPOTENCY_DOMAIN = b"TASK058_MONTAGE_LEARNING_IDEMPOTENCY_V1\0"
RECEIPT_DOMAIN = b"TASK058_MONTAGE_LEARNING_ADMISSION_RECEIPT_V2\0"

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)
_TOKEN = object()

_FIELDS = frozenset(
    {
        "schema_version",
        "message_type",
        "contract_profile",
        "receipt_id",
        "admission_class",
        "source_contract_profile",
        "source_record_id",
        "source_sha256",
        "owner_scope_hash",
        "idempotency_key_sha256",
        "status",
        "canonical_store_written",
        "canonical_evidence_id",
        "canonical_evidence_sha256",
        "canonical_store_commit_sha256",
        "duplicate_of_receipt_sha256",
        "reason_codes",
        "attempt",
        "processed_at",
        "bridge_instance_id",
        "receipt_sha256",
    }
)
_REASON_CODES = frozenset(
    {
        "SCHEMA_INVALID",
        "HASH_MISMATCH",
        "OWNER_SCOPE_MISMATCH",
        "ID_COLLISION",
        "LINEAGE_NOT_FOUND",
        "LINEAGE_MISMATCH",
        "REVIEW_BINDING_REQUIRED",
        "FORBIDDEN_DATA_PRESENT",
        "PATH_UNSAFE",
        "FILE_UNSTABLE",
        "STORE_COMMIT_FAILED",
        "DUPLICATE_IDEMPOTENCY_KEY",
    }
)
_TERMINAL_REJECTION_CODES = _REASON_CODES - {
    "REVIEW_BINDING_REQUIRED",
    "DUPLICATE_IDEMPOTENCY_KEY",
}
_PUBLIC_FIELDS = frozenset(
    {
        "receipt_id",
        "admission_class",
        "source_record_id",
        "source_sha256",
        "status",
        "reason_codes",
        "receipt_sha256",
        "canonical_store_commit_claimed",
        "receipt_structure_valid",
        "origin_authority_verified",
        "duplicate_lineage_verified",
        "canonical_store_commit_verified",
        "canonical_admission_authority_created",
        "receipt_minted",
    }
)


class MontageLearningReceiptContractError(ValueError):
    """Raised when an untrusted P1A receipt body fails closed validation."""


class MontageLearningAdmissionReceipt:
    """Sealed immutable view of one structurally valid caller-supplied receipt."""

    __slots__ = ("_data",)

    def __init__(
        self,
        data: Mapping[str, Any],
        *,
        _token: object | None = None,
    ) -> None:
        if _token is not _TOKEN:
            raise TypeError(
                "MontageLearningAdmissionReceipt must use the validated parser"
            )
        object.__setattr__(self, "_data", data)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("MontageLearningAdmissionReceipt is immutable")

    def __reduce__(self) -> object:
        raise TypeError("serialize the validated dictionary, not the typed object")

    def to_dict(self) -> dict[str, Any]:
        """Return a fresh JSON-compatible copy of the validated receipt."""

        return _thaw(self._data)

    def to_public_projection(self) -> dict[str, object]:
        """Return the exact body-free, non-authoritative P1A projection."""

        projection: dict[str, object] = {
            "receipt_id": self._data["receipt_id"],
            "admission_class": self._data["admission_class"],
            "source_record_id": self._data["source_record_id"],
            "source_sha256": self._data["source_sha256"],
            "status": self._data["status"],
            "reason_codes": list(self._data["reason_codes"]),
            "receipt_sha256": self._data["receipt_sha256"],
            "canonical_store_commit_claimed": self._data[
                "canonical_store_written"
            ],
            "receipt_structure_valid": True,
            "origin_authority_verified": False,
            "duplicate_lineage_verified": False,
            "canonical_store_commit_verified": False,
            "canonical_admission_authority_created": False,
            "receipt_minted": False,
        }
        if set(projection) != _PUBLIC_FIELDS:
            raise AssertionError("public projection fields drifted")
        return projection


def derive_montage_learning_idempotency_key_sha256(
    *,
    source_contract_profile: str,
    source_record_id: str,
    source_sha256: str,
    owner_scope_hash: str,
) -> str:
    """Derive the domain-separated identity digest required by P1A."""

    if type(source_contract_profile) is not str or source_contract_profile not in {
        EXACT_CONTRACT_PROFILE,
        GENERIC_CONTRACT_PROFILE,
    }:
        raise MontageLearningReceiptContractError(
            "source_contract_profile is unsupported"
        )
    record_id = _identifier(source_record_id, "source_record_id")
    source_digest = _digest(source_sha256, "source_sha256")
    scope_digest = _digest(owner_scope_hash, "owner_scope_hash")
    body = {
        "contract_profile": source_contract_profile,
        "owner_scope_hash": scope_digest,
        "record_id": record_id,
        "source_sha256": source_digest,
    }
    return _domain_hash(IDEMPOTENCY_DOMAIN, body)


def compute_montage_learning_receipt_sha256(
    value: Mapping[str, object],
) -> str:
    """Compute the domain-separated receipt hash without minting authority."""

    body = _plain_json_snapshot(value, name="receipt")
    body.pop("receipt_sha256", None)
    return _receipt_hash_from_plain(body)


def parse_montage_learning_admission_receipt(
    value: Mapping[str, object],
) -> MontageLearningAdmissionReceipt:
    """Strictly parse a caller-supplied v2 receipt without trusting its origin."""

    body = _plain_json_snapshot(value, name="receipt")
    if set(body) != _FIELDS:
        missing = sorted(_FIELDS - set(body))
        extra = sorted(set(body) - _FIELDS)
        raise MontageLearningReceiptContractError(
            f"receipt fields mismatch; missing={missing}; extra={extra}"
        )

    _constant(body, "schema_version", SCHEMA_VERSION)
    _constant(body, "message_type", MESSAGE_TYPE)
    _constant(body, "contract_profile", CONTRACT_PROFILE)
    _identifier(body["receipt_id"], "receipt_id")
    admission_class = body["admission_class"]
    if type(admission_class) is not str or admission_class not in {
        EXACT_EVIDENCE,
        GENERIC_OBSERVATION,
    }:
        raise MontageLearningReceiptContractError("admission_class is invalid")

    source_profile = body["source_contract_profile"]
    expected_profile = (
        EXACT_CONTRACT_PROFILE
        if admission_class == EXACT_EVIDENCE
        else GENERIC_CONTRACT_PROFILE
    )
    if source_profile != expected_profile:
        raise MontageLearningReceiptContractError(
            "source_contract_profile does not match admission_class"
        )

    source_record_id = _identifier(body["source_record_id"], "source_record_id")
    source_digest = _digest(body["source_sha256"], "source_sha256")
    owner_scope = _digest(body["owner_scope_hash"], "owner_scope_hash")
    key_digest = _digest(
        body["idempotency_key_sha256"], "idempotency_key_sha256"
    )
    expected_key = derive_montage_learning_idempotency_key_sha256(
        source_contract_profile=source_profile,
        source_record_id=source_record_id,
        source_sha256=source_digest,
        owner_scope_hash=owner_scope,
    )
    if key_digest != expected_key:
        raise MontageLearningReceiptContractError(
            "idempotency_key_sha256 mismatch"
        )

    status = body["status"]
    if type(status) is not str or status not in {
        ACCEPTED,
        DUPLICATE,
        REJECTED,
        REVIEW_REQUIRED,
    }:
        raise MontageLearningReceiptContractError("status is invalid")
    if type(body["canonical_store_written"]) is not bool:
        raise MontageLearningReceiptContractError(
            "canonical_store_written must be a boolean"
        )
    _nullable_identifier(body["canonical_evidence_id"], "canonical_evidence_id")
    _nullable_digest(
        body["canonical_evidence_sha256"], "canonical_evidence_sha256"
    )
    _nullable_digest(
        body["canonical_store_commit_sha256"],
        "canonical_store_commit_sha256",
    )
    _nullable_digest(
        body["duplicate_of_receipt_sha256"],
        "duplicate_of_receipt_sha256",
    )
    reasons = _reason_codes(body["reason_codes"])
    _positive_integer(body["attempt"], "attempt")
    _utc_timestamp(body["processed_at"], "processed_at")
    _identifier(body["bridge_instance_id"], "bridge_instance_id")
    _validate_state_matrix(body, admission_class, status, reasons)

    supplied_receipt_hash = _digest(body["receipt_sha256"], "receipt_sha256")
    expected_receipt_hash = _receipt_hash_from_plain(body)
    if supplied_receipt_hash != expected_receipt_hash:
        raise MontageLearningReceiptContractError("receipt_sha256 mismatch")

    return MontageLearningAdmissionReceipt(
        _freeze(body),
        _token=_TOKEN,
    )


def _validate_state_matrix(
    body: Mapping[str, Any],
    admission_class: str,
    status: str,
    reasons: tuple[str, ...],
) -> None:
    if admission_class == GENERIC_OBSERVATION:
        if status not in {REVIEW_REQUIRED, REJECTED}:
            raise MontageLearningReceiptContractError(
                "generic observation status is invalid"
            )
        if body["canonical_store_written"] is not False:
            raise MontageLearningReceiptContractError(
                "generic observation cannot claim a canonical store write"
            )
    elif status not in {ACCEPTED, DUPLICATE, REJECTED}:
        raise MontageLearningReceiptContractError(
            "exact evidence status is invalid"
        )

    duplicate_ref = body["duplicate_of_receipt_sha256"]
    if status == ACCEPTED:
        if reasons != () or duplicate_ref is not None:
            raise MontageLearningReceiptContractError(
                "ACCEPTED reason or duplicate reference is invalid"
            )
    elif status == DUPLICATE:
        if reasons != ("DUPLICATE_IDEMPOTENCY_KEY",):
            raise MontageLearningReceiptContractError(
                "DUPLICATE reason_codes are invalid"
            )
        if duplicate_ref is None:
            raise MontageLearningReceiptContractError(
                "DUPLICATE requires a structural prior receipt reference"
            )
    elif status == REVIEW_REQUIRED:
        if reasons != ("REVIEW_BINDING_REQUIRED",) or duplicate_ref is not None:
            raise MontageLearningReceiptContractError(
                "REVIEW_REQUIRED state is invalid"
            )
    else:
        if (
            not reasons
            or any(reason not in _TERMINAL_REJECTION_CODES for reason in reasons)
            or duplicate_ref is not None
        ):
            raise MontageLearningReceiptContractError(
                "REJECTED reason or duplicate reference is invalid"
            )
        if body["canonical_store_written"] is not False:
            raise MontageLearningReceiptContractError(
                "REJECTED cannot claim a canonical store write"
            )

    canonical_fields = (
        body["canonical_evidence_id"],
        body["canonical_evidence_sha256"],
        body["canonical_store_commit_sha256"],
    )
    if body["canonical_store_written"]:
        if admission_class != EXACT_EVIDENCE or status not in {
            ACCEPTED,
            DUPLICATE,
        }:
            raise MontageLearningReceiptContractError(
                "canonical store claim state is invalid"
            )
        if any(item is None for item in canonical_fields):
            raise MontageLearningReceiptContractError(
                "canonical store claim requires exact evidence and commit refs"
            )
    elif any(item is not None for item in canonical_fields):
        raise MontageLearningReceiptContractError(
            "canonical refs require canonical_store_written true"
        )


def _plain_json_snapshot(value: object, *, name: str) -> dict[str, Any]:
    """Copy exact built-in JSON values once without invoking user hooks."""

    def snapshot(item: object, path: str) -> Any:
        if item is None or type(item) in {str, bool, int}:
            return item
        if type(item) is list:
            return [snapshot(child, f"{path}[]") for child in item]
        if type(item) is dict:
            result: dict[str, Any] = {}
            for key, child in item.items():
                if type(key) is not str:
                    raise MontageLearningReceiptContractError(
                        f"{path} keys must be exact strings"
                    )
                result[key] = snapshot(child, f"{path}.{key}")
            return result
        raise MontageLearningReceiptContractError(
            f"{path} must contain exact built-in JSON values"
        )

    if type(value) is not dict:
        raise MontageLearningReceiptContractError(
            f"{name} must be an exact built-in object"
        )
    return snapshot(value, name)


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _domain_hash(domain: bytes, value: object) -> str:
    return f"sha256:{sha256(domain + _canonical_json_bytes(value)).hexdigest()}"


def _receipt_hash_from_plain(body: Mapping[str, Any]) -> str:
    unhashed = dict(body)
    unhashed.pop("receipt_sha256", None)
    return _domain_hash(RECEIPT_DOMAIN, unhashed)


def _constant(body: Mapping[str, Any], field: str, expected: str) -> None:
    if type(body[field]) is not str or body[field] != expected:
        raise MontageLearningReceiptContractError(
            f"{field} must equal {expected!r}"
        )


def _identifier(value: object, name: str) -> str:
    if type(value) is not str or _ID_RE.fullmatch(value) is None:
        raise MontageLearningReceiptContractError(f"{name} is invalid")
    return value


def _nullable_identifier(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _identifier(value, name)


def _digest(value: object, name: str) -> str:
    if type(value) is not str or _DIGEST_RE.fullmatch(value) is None:
        raise MontageLearningReceiptContractError(f"{name} is invalid")
    return value


def _nullable_digest(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _digest(value, name)


def _reason_codes(value: object) -> tuple[str, ...]:
    if type(value) is not list or not 0 <= len(value) <= 12:
        raise MontageLearningReceiptContractError(
            "reason_codes must be a bounded JSON array"
        )
    if any(type(item) is not str or item not in _REASON_CODES for item in value):
        raise MontageLearningReceiptContractError("reason_codes contains an invalid code")
    if value != sorted(value) or len(value) != len(set(value)):
        raise MontageLearningReceiptContractError(
            "reason_codes must be unique and lexicographically sorted"
        )
    return tuple(value)


def _positive_integer(value: object, name: str) -> int:
    if (
        type(value) is not int
        or not 1 <= value <= 2_147_483_647
    ):
        raise MontageLearningReceiptContractError(
            f"{name} must be a positive bounded integer"
        )
    return value


def _utc_timestamp(value: object, name: str) -> str:
    if type(value) is not str or _UTC_RE.fullmatch(value) is None:
        raise MontageLearningReceiptContractError(
            f"{name} must be an exact UTC Z timestamp"
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise MontageLearningReceiptContractError(
            f"{name} is not a valid timestamp"
        ) from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise MontageLearningReceiptContractError(f"{name} must be UTC")
    return value


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


__all__ = [
    "ACCEPTED",
    "CONTRACT_PROFILE",
    "DUPLICATE",
    "EXACT_EVIDENCE",
    "GENERIC_OBSERVATION",
    "IDEMPOTENCY_DOMAIN",
    "MESSAGE_TYPE",
    "MontageLearningAdmissionReceipt",
    "MontageLearningReceiptContractError",
    "RECEIPT_DOMAIN",
    "REJECTED",
    "REVIEW_REQUIRED",
    "SCHEMA_VERSION",
    "compute_montage_learning_receipt_sha256",
    "derive_montage_learning_idempotency_key_sha256",
    "parse_montage_learning_admission_receipt",
]
