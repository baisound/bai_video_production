"""Effect-zero TASK-048 Q2 to TASK-046 Q3 handoff fixture contract.

The current Product producer and durable Q2 owner are not bound.  This module
therefore validates body-free synthetic metadata only and always leaves Q3
preflight blocked.  It does not read media, invoke TASK-048 processing, publish
an Asset, create a Transcript, mutate a Dataset, or grant Product authority.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
import re
from types import MappingProxyType
from typing import Any, Mapping

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


CONTRACT_VERSION = "TASK046_Q2_Q3_HANDOFF_FIXTURE_R1"
RECORD_TYPE = "Task046Q2Q3HandoffFixture"
PUBLIC_RECORD_TYPE = "Task046Q2Q3HandoffPublicProjection"
AUTHORITY_KIND = "SYNTHETIC_CONTRACT_TEST"
INTENDED_Q2_OWNER = "TASK-048"
INTENDED_Q3_OWNER = "TASK-046"
DATA_PREPARATION_SCOPE = "OWNER_VOICE_DATA_PREPARATION"
DATA_PREPARATION_DECISION = "ALLOW"
PRODUCT_BINDING_STATE = "NOT_BOUND"
Q3_ADMISSION_STATE = "PREFLIGHT_BLOCKED"
TRAINING_COPY_FORMAT = "PCM_S24LE_48000_MONO"
SAMPLE_RATE_HZ = 48_000
CHANNEL_COUNT = 1
BIT_DEPTH = 24
MAX_SAMPLE_COUNT = SAMPLE_RATE_HZ * 60 * 60 * 2
BLOCKING_REASON_CODES = (
    "Q2_DURABLE_OWNER_NOT_BOUND",
    "Q2_PRODUCT_TERMINAL_NOT_BOUND",
    "Q3_PRODUCT_AUTHORITY_FALSE",
)

_DIGEST_DOMAIN = b"BAI:TASK046:Q2_Q3_HANDOFF_FIXTURE:R1\x00"
_CONSTRUCTION_TOKEN = object()
_ID_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9_-]*(?::[A-Za-z0-9][A-Za-z0-9_-]*)+"
)
_UTC_TIMESTAMP_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z"
)

_IDENTIFIER_PREFIXES = {
    "fixture_id": "fixture:",
    "project_id": "project:",
    "q2_operation_id": "operation:",
    "q2_idempotency_key": "idempotency:",
    "processed_asset_ref": "asset:",
    "training_copy_asset_ref": "asset:",
}

_DIGEST_FIELDS = {
    "owner_subject_binding_sha256",
    "data_preparation_consent_sha256",
    "q1_capture_chain_terminal_receipt_sha256",
    "processed_asset_revision_sha256",
    "processed_asset_checksum_sha256",
    "processed_custody_receipt_sha256",
    "processed_task003_adoption_receipt_sha256",
    "processed_task003_current_readback_sha256",
    "training_copy_asset_revision_sha256",
    "training_copy_asset_checksum_sha256",
    "training_copy_custody_receipt_sha256",
    "training_copy_task003_adoption_receipt_sha256",
    "training_copy_task003_current_readback_sha256",
    "quality_receipt_sha256",
    "speech_continuous_receipt_sha256",
    "range_map_receipt_sha256",
    "sample_map_receipt_sha256",
    "policy_sha256",
    "analyzer_sha256",
    "producer_code_sha256",
    "runtime_sha256",
}

_NULL_PRODUCT_RECEIPT_FIELDS = {
    "q2_product_terminal_receipt_sha256",
    "q2_publication_readback_sha256",
    "q2_currentness_readback_sha256",
}

_PRIVACY_MARKERS = {
    "host_path_present": False,
    "filename_present": False,
    "audio_body_present": False,
    "transcript_body_present": False,
    "prompt_body_present": False,
    "secret_present": False,
    "device_identity_present": False,
    "voice_fingerprint_present": False,
}

_FIELDS = {
    "contract_version",
    "record_type",
    "fixture_id",
    "authority_kind",
    "intended_q2_owner",
    "intended_q3_owner",
    "synthetic_input_only",
    "owner_audio_used",
    "external_effect_count",
    "product_authority",
    "canonical_producer_receipt",
    "project_id",
    "owner_subject_binding_sha256",
    "data_preparation_consent_sha256",
    "data_preparation_scope",
    "data_preparation_decision",
    "q1_capture_chain_terminal_receipt_sha256",
    "q2_operation_id",
    "q2_idempotency_key",
    "processed_asset_ref",
    "processed_asset_revision_sha256",
    "processed_asset_checksum_sha256",
    "processed_sample_count",
    "processed_custody_receipt_sha256",
    "processed_task003_adoption_receipt_sha256",
    "processed_task003_current_readback_sha256",
    "training_copy_asset_ref",
    "training_copy_asset_revision_sha256",
    "training_copy_asset_checksum_sha256",
    "training_copy_sample_count",
    "training_copy_format",
    "training_copy_sample_rate_hz",
    "training_copy_channel_count",
    "training_copy_bit_depth",
    "training_copy_custody_receipt_sha256",
    "training_copy_task003_adoption_receipt_sha256",
    "training_copy_task003_current_readback_sha256",
    "quality_receipt_sha256",
    "speech_continuous_receipt_sha256",
    "range_map_receipt_sha256",
    "sample_map_receipt_sha256",
    "policy_sha256",
    "analyzer_sha256",
    "producer_code_sha256",
    "runtime_sha256",
    "q2_durable_owner_binding_state",
    "q2_product_terminal_state",
    "q2_product_terminal_receipt_sha256",
    "q2_publication_readback_sha256",
    "q2_currentness_readback_sha256",
    "created_at",
    "replay",
    "q3_admission_state",
    "reason_codes",
    *_PRIVACY_MARKERS,
    "fixture_receipt_sha256",
}


def _expect_exact_fields(value: Mapping[str, Any]) -> None:
    if not isinstance(value, Mapping) or set(value) != _FIELDS:
        raise ValueError("Q2-Q3 handoff fixture fields are incomplete or unknown")


def _identifier(value: Any, name: str, *, prefix: str) -> str:
    if (
        not isinstance(value, str)
        or not _ID_RE.fullmatch(value)
        or not value.startswith(prefix)
        or "\\" in value
        or "/" in value
    ):
        raise ValueError(f"{name} must be a contained logical identifier")
    return value


def _digest(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be SHA-256")
    return validate_sha256(value, field_name=name)


def _sample_count(value: Any, name: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= MAX_SAMPLE_COUNT
    ):
        raise ValueError(f"{name} is outside the bounded sample policy")
    return value


def _timestamp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _UTC_TIMESTAMP_RE.fullmatch(value):
        raise ValueError(f"{name} must be RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be RFC3339 UTC") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{name} must be UTC")
    return value


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


def _receipt_digest(value: Mapping[str, Any]) -> str:
    body = {
        key: item
        for key, item in value.items()
        if key != "fixture_receipt_sha256"
    }
    return sha256_bytes(_DIGEST_DOMAIN + canonical_json_bytes(body))


@dataclass(frozen=True, slots=True, init=False)
class Task046Q2Q3HandoffFixture:
    """Immutable synthetic mapping fixture that can never unlock Product Q3."""

    _data: Mapping[str, Any]

    def __init__(
        self,
        data: Mapping[str, Any],
        *,
        _token: object | None = None,
    ) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("handoff fixture must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        fixture_id: str,
        project_id: str,
        owner_subject_binding_sha256: str,
        data_preparation_consent_sha256: str,
        q1_capture_chain_terminal_receipt_sha256: str,
        q2_operation_id: str,
        q2_idempotency_key: str,
        processed_asset_ref: str,
        processed_asset_revision_sha256: str,
        processed_asset_checksum_sha256: str,
        processed_sample_count: int,
        processed_custody_receipt_sha256: str,
        processed_task003_adoption_receipt_sha256: str,
        processed_task003_current_readback_sha256: str,
        training_copy_asset_ref: str,
        training_copy_asset_revision_sha256: str,
        training_copy_asset_checksum_sha256: str,
        training_copy_sample_count: int,
        training_copy_custody_receipt_sha256: str,
        training_copy_task003_adoption_receipt_sha256: str,
        training_copy_task003_current_readback_sha256: str,
        quality_receipt_sha256: str,
        speech_continuous_receipt_sha256: str,
        range_map_receipt_sha256: str,
        sample_map_receipt_sha256: str,
        policy_sha256: str,
        analyzer_sha256: str,
        producer_code_sha256: str,
        runtime_sha256: str,
        created_at: str,
    ) -> "Task046Q2Q3HandoffFixture":
        body: dict[str, Any] = {
            "contract_version": CONTRACT_VERSION,
            "record_type": RECORD_TYPE,
            "fixture_id": fixture_id,
            "authority_kind": AUTHORITY_KIND,
            "intended_q2_owner": INTENDED_Q2_OWNER,
            "intended_q3_owner": INTENDED_Q3_OWNER,
            "synthetic_input_only": True,
            "owner_audio_used": False,
            "external_effect_count": 0,
            "product_authority": False,
            "canonical_producer_receipt": False,
            "project_id": project_id,
            "owner_subject_binding_sha256": owner_subject_binding_sha256,
            "data_preparation_consent_sha256": data_preparation_consent_sha256,
            "data_preparation_scope": DATA_PREPARATION_SCOPE,
            "data_preparation_decision": DATA_PREPARATION_DECISION,
            "q1_capture_chain_terminal_receipt_sha256": (
                q1_capture_chain_terminal_receipt_sha256
            ),
            "q2_operation_id": q2_operation_id,
            "q2_idempotency_key": q2_idempotency_key,
            "processed_asset_ref": processed_asset_ref,
            "processed_asset_revision_sha256": processed_asset_revision_sha256,
            "processed_asset_checksum_sha256": processed_asset_checksum_sha256,
            "processed_sample_count": processed_sample_count,
            "processed_custody_receipt_sha256": processed_custody_receipt_sha256,
            "processed_task003_adoption_receipt_sha256": (
                processed_task003_adoption_receipt_sha256
            ),
            "processed_task003_current_readback_sha256": (
                processed_task003_current_readback_sha256
            ),
            "training_copy_asset_ref": training_copy_asset_ref,
            "training_copy_asset_revision_sha256": training_copy_asset_revision_sha256,
            "training_copy_asset_checksum_sha256": training_copy_asset_checksum_sha256,
            "training_copy_sample_count": training_copy_sample_count,
            "training_copy_format": TRAINING_COPY_FORMAT,
            "training_copy_sample_rate_hz": SAMPLE_RATE_HZ,
            "training_copy_channel_count": CHANNEL_COUNT,
            "training_copy_bit_depth": BIT_DEPTH,
            "training_copy_custody_receipt_sha256": (
                training_copy_custody_receipt_sha256
            ),
            "training_copy_task003_adoption_receipt_sha256": (
                training_copy_task003_adoption_receipt_sha256
            ),
            "training_copy_task003_current_readback_sha256": (
                training_copy_task003_current_readback_sha256
            ),
            "quality_receipt_sha256": quality_receipt_sha256,
            "speech_continuous_receipt_sha256": speech_continuous_receipt_sha256,
            "range_map_receipt_sha256": range_map_receipt_sha256,
            "sample_map_receipt_sha256": sample_map_receipt_sha256,
            "policy_sha256": policy_sha256,
            "analyzer_sha256": analyzer_sha256,
            "producer_code_sha256": producer_code_sha256,
            "runtime_sha256": runtime_sha256,
            "q2_durable_owner_binding_state": PRODUCT_BINDING_STATE,
            "q2_product_terminal_state": PRODUCT_BINDING_STATE,
            "q2_product_terminal_receipt_sha256": None,
            "q2_publication_readback_sha256": None,
            "q2_currentness_readback_sha256": None,
            "created_at": created_at,
            "replay": False,
            "q3_admission_state": Q3_ADMISSION_STATE,
            "reason_codes": list(BLOCKING_REASON_CODES),
            **_PRIVACY_MARKERS,
        }
        body["fixture_receipt_sha256"] = _receipt_digest(body)
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Task046Q2Q3HandoffFixture":
        if cls is not Task046Q2Q3HandoffFixture:
            raise TypeError("handoff fixture subclass construction is forbidden")
        if not isinstance(value, Mapping):
            raise ValueError("Q2-Q3 handoff fixture must be a mapping")
        value = copy.deepcopy(dict(value))
        _expect_exact_fields(value)
        if (
            value["contract_version"] != CONTRACT_VERSION
            or value["record_type"] != RECORD_TYPE
            or value["authority_kind"] != AUTHORITY_KIND
            or value["intended_q2_owner"] != INTENDED_Q2_OWNER
            or value["intended_q3_owner"] != INTENDED_Q3_OWNER
        ):
            raise ValueError("handoff fixture identity/owner is invalid")
        for name, prefix in _IDENTIFIER_PREFIXES.items():
            _identifier(value[name], name, prefix=prefix)
        if value["processed_asset_ref"] == value["training_copy_asset_ref"]:
            raise ValueError("processed and training-copy Asset identities must differ")
        typed_digests = [_digest(value[name], name) for name in _DIGEST_FIELDS]
        if len(set(typed_digests)) != len(typed_digests):
            raise ValueError("typed receipt/revision digests must not alias")
        for name in _NULL_PRODUCT_RECEIPT_FIELDS:
            _digest(value[name], name, nullable=True)
            if value[name] is not None:
                raise ValueError("producer-unbound fixture cannot invent Product receipts")
        _sample_count(value["processed_sample_count"], "processed_sample_count")
        _sample_count(value["training_copy_sample_count"], "training_copy_sample_count")
        if (
            value["data_preparation_scope"] != DATA_PREPARATION_SCOPE
            or value["data_preparation_decision"] != DATA_PREPARATION_DECISION
        ):
            raise ValueError("data-preparation Consent scope/decision is invalid")
        expected_format = {
            "training_copy_format": TRAINING_COPY_FORMAT,
            "training_copy_sample_rate_hz": SAMPLE_RATE_HZ,
            "training_copy_channel_count": CHANNEL_COUNT,
            "training_copy_bit_depth": BIT_DEPTH,
        }
        if any(
            type(value[name]) is not type(expected) or value[name] != expected
            for name, expected in expected_format.items()
        ):
            raise ValueError("training-copy format must be PCM_S24LE/48000/mono")
        expected_constants = {
            "synthetic_input_only": True,
            "owner_audio_used": False,
            "external_effect_count": 0,
            "product_authority": False,
            "canonical_producer_receipt": False,
            "q2_durable_owner_binding_state": PRODUCT_BINDING_STATE,
            "q2_product_terminal_state": PRODUCT_BINDING_STATE,
            "replay": False,
            "q3_admission_state": Q3_ADMISSION_STATE,
            **_PRIVACY_MARKERS,
        }
        for name, expected in expected_constants.items():
            if type(value[name]) is not type(expected) or value[name] != expected:
                raise ValueError(
                    "handoff fixture violates the no-authority/no-effect boundary"
                )
        if value["reason_codes"] != list(BLOCKING_REASON_CODES):
            raise ValueError("reason_codes must match the exact blocked state")
        _timestamp(value["created_at"], "created_at")
        _digest(value["fixture_receipt_sha256"], "fixture_receipt_sha256")
        if value["fixture_receipt_sha256"] != _receipt_digest(value):
            raise ValueError("fixture_receipt_sha256 mismatch")
        return cls(_freeze(value), _token=_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


def public_projection(
    value: Mapping[str, Any] | Task046Q2Q3HandoffFixture,
) -> dict[str, Any]:
    fixture = (
        value
        if isinstance(value, Task046Q2Q3HandoffFixture)
        else Task046Q2Q3HandoffFixture.from_dict(value)
    )
    if type(fixture) is not Task046Q2Q3HandoffFixture:
        raise TypeError("only the exact handoff fixture may produce a projection")
    return {
        "record_type": PUBLIC_RECORD_TYPE,
        "contract_version": CONTRACT_VERSION,
        "authority_kind": AUTHORITY_KIND,
        "intended_q2_owner": INTENDED_Q2_OWNER,
        "intended_q3_owner": INTENDED_Q3_OWNER,
        "q2_durable_owner_binding_state": PRODUCT_BINDING_STATE,
        "q2_product_terminal_state": PRODUCT_BINDING_STATE,
        "q3_admission_state": Q3_ADMISSION_STATE,
        "reason_codes": list(BLOCKING_REASON_CODES),
        "owner_audio_used": False,
        "external_effect_count": 0,
        "product_authority": False,
        "canonical_producer_receipt": False,
        "host_path_present": False,
        "audio_body_present": False,
        "transcript_body_present": False,
    }


__all__ = [
    "AUTHORITY_KIND",
    "BIT_DEPTH",
    "BLOCKING_REASON_CODES",
    "CHANNEL_COUNT",
    "CONTRACT_VERSION",
    "DATA_PREPARATION_DECISION",
    "DATA_PREPARATION_SCOPE",
    "INTENDED_Q2_OWNER",
    "INTENDED_Q3_OWNER",
    "PRODUCT_BINDING_STATE",
    "PUBLIC_RECORD_TYPE",
    "Q3_ADMISSION_STATE",
    "SAMPLE_RATE_HZ",
    "TRAINING_COPY_FORMAT",
    "Task046Q2Q3HandoffFixture",
    "public_projection",
]
