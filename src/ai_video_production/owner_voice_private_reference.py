"""TASK-074 pure private-reference metadata and state validators.

No class in this module is a live reference capability.  The module never
opens an audio/transcript source, stores a body or path, handles a key, spawns
a process, or performs purge.  Those effects remain behind TASK074-C/D gates.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence
import unicodedata

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


MEDIA_POLICY_CONTRACT_VERSION = "OWNER_VOICE_REFERENCE_MEDIA_POLICY_V1"
MEDIA_FACTS_CONTRACT_VERSION = "OWNER_VOICE_REFERENCE_MEDIA_FACTS_V1"
TRANSCRIPT_FACTS_CONTRACT_VERSION = "OWNER_VOICE_REFERENCE_TRANSCRIPT_FACTS_V1"
TRANSCRIPT_BINDING_CONTRACT_VERSION = "TASK046_OWNER_REFERENCE_TRANSCRIPT_BINDING_FIXTURE_V1"
PREPARE_PLAN_CONTRACT_VERSION = "OWNER_VOICE_REFERENCE_PREPARE_PLAN_V1"
DOMAIN_SNAPSHOT_CONTRACT_VERSION = "TASK074_REFERENCE_DOMAIN_SNAPSHOT_V1"
V2_ISSUE_READBACK_CONTRACT_VERSION = "TASK074_REFERENCE_V2_ISSUE_OR_REVOKE_READBACK_V1"
TERMINAL_RETIRE_REQUEST_CONTRACT_VERSION = "TASK074_REFERENCE_V2_TERMINAL_RETIRE_REQUEST_V1"
TERMINAL_RETIRE_READBACK_CONTRACT_VERSION = "TASK074_REFERENCE_V2_TERMINAL_RETIRE_READBACK_V1"
V1_REVOKE_FINALIZE_READBACK_CONTRACT_VERSION = "TASK074_REFERENCE_V1_REVOKE_FINALIZE_READBACK_V1"
CHILD_ABORT_READBACK_CONTRACT_VERSION = "TASK074_REFERENCE_CHILD_ABORT_RECOVERY_READBACK_V1"

_MEDIA_POLICY_DOMAIN = b"TASK074_OWNER_VOICE_REFERENCE_MEDIA_POLICY_V1\0"
_MEDIA_FACTS_DOMAIN = b"TASK074_OWNER_VOICE_REFERENCE_MEDIA_FACTS_V1\0"
_TRANSCRIPT_FACTS_DOMAIN = b"TASK074_OWNER_VOICE_REFERENCE_TRANSCRIPT_FACTS_V1\0"
_TRANSCRIPT_BINDING_DOMAIN = b"TASK046_OWNER_REFERENCE_TRANSCRIPT_BINDING_FIXTURE_V1\0"
_PREPARE_PLAN_DOMAIN = b"TASK074_OWNER_VOICE_REFERENCE_PREPARE_PLAN_V1\0"
_SNAPSHOT_DOMAIN = b"TASK074_REFERENCE_DOMAIN_SNAPSHOT_V1\0"
_FENCE_DOMAIN = b"TASK074_REFERENCE_LEASE_VERSION_FENCE_V1\0"
_V2_ISSUE_READBACK_DOMAIN = b"TASK074_REFERENCE_V2_ISSUE_OR_REVOKE_READBACK_V1\0"
_TERMINAL_RETIRE_REQUEST_DOMAIN = b"TASK074_REFERENCE_V2_TERMINAL_RETIRE_REQUEST_V1\0"
_TERMINAL_RETIRE_DOMAIN = b"TASK074_REFERENCE_V2_TERMINAL_RETIRE_READBACK_V1\0"
_V1_REVOKE_FINALIZE_DOMAIN = b"TASK074_REFERENCE_V1_REVOKE_FINALIZE_READBACK_V1\0"
_CHILD_ABORT_DOMAIN = b"TASK074_REFERENCE_CHILD_ABORT_RECOVERY_READBACK_V1\0"
_CONSTRUCTION_TOKEN = object()
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9][A-Za-z0-9_-]*)*$")
_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")


class ReferenceLifecycle(str, Enum):
    UNBOUND = "UNBOUND"
    PREPARE_PLANNED = "PREPARE_PLANNED"
    PREPARING = "PREPARING"
    PREPARED = "PREPARED"
    PREPARE_FAILED_NO_DERIVATIVE = "PREPARE_FAILED_NO_DERIVATIVE"
    PREPARE_FAILED_RETAINED = "PREPARE_FAILED_RETAINED"
    REVOKE_PENDING = "REVOKE_PENDING"
    REVOKED = "REVOKED"
    PURGE_PENDING = "PURGE_PENDING"
    PURGED = "PURGED"
    PURGE_NOT_CONFIRMED = "PURGE_NOT_CONFIRMED"


class RetainedObject(str, Enum):
    NONE = "NONE"
    ALLOCATED = "ALLOCATED"
    ENCRYPTED_UNPUBLISHED = "ENCRYPTED_UNPUBLISHED"
    PUBLISHED = "PUBLISHED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    RECOVERABLE_RETAINED = "RECOVERABLE_RETAINED"
    KEY_REVOKED = "KEY_REVOKED"
    PURGED = "PURGED"
    FOREIGN_PRESERVED = "FOREIGN_PRESERVED"


class CapabilityLeaseV1Current(str, Enum):
    NONE = "NONE"
    ISSUED = "ISSUED"
    IN_FLIGHT = "IN_FLIGHT"
    BODY_READ_STARTED = "BODY_READ_STARTED"
    CONSUMED = "CONSUMED"
    BURNED = "BURNED"
    FAILED_CLOSED = "FAILED_CLOSED"


class CapabilityLeaseV2Current(str, Enum):
    V2_ABSENT = "V2_ABSENT"
    ISSUED = "ISSUED"
    IN_FLIGHT_PARENT_DELEGATION = "IN_FLIGHT_PARENT_DELEGATION"
    CHILD_TRANSFER_IN_FLIGHT = "CHILD_TRANSFER_IN_FLIGHT"
    CHILD_PAIR_READY = "CHILD_PAIR_READY"
    BODY_READ_STARTED = "BODY_READ_STARTED"
    CONSUMED = "CONSUMED"
    BURNED = "BURNED"
    FAILED_CLOSED = "FAILED_CLOSED"


class ReferenceSourceClassification(str, Enum):
    TASK046_PRIVATE_RECORDING_REFERENCE = "TASK046_PRIVATE_RECORDING_REFERENCE"
    TASK003_PRIVATE_ASSET_REFERENCE = "TASK003_PRIVATE_ASSET_REFERENCE"
    TRUSTED_PICKER_EXTERNAL_REFERENCE = "TRUSTED_PICKER_EXTERNAL_REFERENCE"


class RetentionPolicy(str, Enum):
    UNTIL_EXPLICIT_REVOKE = "UNTIL_EXPLICIT_REVOKE"
    UNTIL_PROJECT_DELETE_HUMAN_GATED = "UNTIL_PROJECT_DELETE_HUMAN_GATED"
    OWNER_SELECTED_EXPIRY = "OWNER_SELECTED_EXPIRY"


class RevokeExpiryIntent(str, Enum):
    ABSENT = "ABSENT"
    EXPLICIT_REVOKE = "EXPLICIT_REVOKE"
    TRUSTED_TIME_EXPIRY = "TRUSTED_TIME_EXPIRY"


class ReferenceTransition(str, Enum):
    PREPARE_PLAN = "PREPARE_PLAN"
    PREPARE_START = "PREPARE_START"
    PREPARE_PUBLISH = "PREPARE_PUBLISH"
    PREPARE_FAIL_NO_DERIVATIVE = "PREPARE_FAIL_NO_DERIVATIVE"
    PREPARE_FAIL_RETAINED = "PREPARE_FAIL_RETAINED"
    V1_TERMINAL_RETIRE = "V1_TERMINAL_RETIRE"
    V2_ISSUE = "V2_ISSUE"
    V2_PARENT_DELEGATION_BEGIN = "V2_PARENT_DELEGATION_BEGIN"
    V2_CHILD_TRANSFER_BEGIN = "V2_CHILD_TRANSFER_BEGIN"
    V2_CHILD_PAIR_READY = "V2_CHILD_PAIR_READY"
    V2_BODY_READ_BEGIN = "V2_BODY_READ_BEGIN"
    V2_CONSUME = "V2_CONSUME"
    V2_BURN = "V2_BURN"
    V2_FAIL_CLOSED = "V2_FAIL_CLOSED"
    V2_TERMINAL_RETIRE = "V2_TERMINAL_RETIRE"
    V2_TERMINAL_REVOKE_FINALIZE = "V2_TERMINAL_REVOKE_FINALIZE"
    REVOKE_DIRECT = "REVOKE_DIRECT"
    REVOKE_PENDING = "REVOKE_PENDING"
    V1_REVOKE_FINALIZE = "V1_REVOKE_FINALIZE"
    V2_REVOKE_FINALIZE = "V2_REVOKE_FINALIZE"
    PURGE_BEGIN = "PURGE_BEGIN"
    PURGE_SUCCESS = "PURGE_SUCCESS"
    PURGE_NOT_CONFIRMED = "PURGE_NOT_CONFIRMED"


class V2IssueOrRevokeOutcome(str, Enum):
    V2_ISSUE_COMMITTED_DELIVERY_ACKNOWLEDGED = "V2_ISSUE_COMMITTED_DELIVERY_ACKNOWLEDGED"
    V2_ISSUE_COMMITTED_DELIVERY_NOT_CONFIRMED = "V2_ISSUE_COMMITTED_DELIVERY_NOT_CONFIRMED"
    REVOKE_COMMITTED = "REVOKE_COMMITTED"
    EXPIRY_COMMITTED = "EXPIRY_COMMITTED"
    NO_COMMIT_STALE_PREDECESSOR = "NO_COMMIT_STALE_PREDECESSOR"
    OUTCOME_NOT_CONFIRMED = "OUTCOME_NOT_CONFIRMED"


class TerminalKind(str, Enum):
    CONSUMED = "CONSUMED"
    BURNED = "BURNED"
    FAILED_CLOSED = "FAILED_CLOSED"


class TerminalRetireOutcome(str, Enum):
    CONSUMED_RETIRED = "CONSUMED_RETIRED"
    BURNED_RETIRED = "BURNED_RETIRED"
    FAILED_CLOSED_RETIRED_NOT_CONFIRMED = "FAILED_CLOSED_RETIRED_NOT_CONFIRMED"
    TERMINAL_REVOKE_COMMITTED = "TERMINAL_REVOKE_COMMITTED"
    TERMINAL_EXPIRY_COMMITTED = "TERMINAL_EXPIRY_COMMITTED"
    NO_COMMIT_TERMINAL_STILL_CURRENT = "NO_COMMIT_TERMINAL_STILL_CURRENT"
    STALE_OTHER_COMMIT = "STALE_OTHER_COMMIT"
    OUTCOME_NOT_CONFIRMED = "OUTCOME_NOT_CONFIRMED"


class TerminalRetireAction(str, Enum):
    RETIRE = "RETIRE"
    EXPLICIT_REVOKE = "EXPLICIT_REVOKE"
    TRUSTED_TIME_EXPIRY = "TRUSTED_TIME_EXPIRY"


class TerminalHistoryDisposition(str, Enum):
    EXACT_PRESENT = "EXACT_PRESENT"
    SEALED_ONCE = "SEALED_ONCE"
    NOT_CONFIRMED = "NOT_CONFIRMED"


class V1RevokeFinalizeOutcome(str, Enum):
    V1_CONSUMED_REVOKE_FINALIZED = "V1_CONSUMED_REVOKE_FINALIZED"
    V1_BURNED_REVOKE_FINALIZED = "V1_BURNED_REVOKE_FINALIZED"
    V1_FAILED_CLOSED_REVOKE_FINALIZED_NOT_CONFIRMED = "V1_FAILED_CLOSED_REVOKE_FINALIZED_NOT_CONFIRMED"
    V1_TERMINAL_AWAITING_FINALIZE = "V1_TERMINAL_AWAITING_FINALIZE"
    V1_ACTIVE_RECOVERY_REQUIRED = "V1_ACTIVE_RECOVERY_REQUIRED"
    STALE_OTHER_COMMIT = "STALE_OTHER_COMMIT"
    OUTCOME_NOT_CONFIRMED = "OUTCOME_NOT_CONFIRMED"


class SpawnTruth(str, Enum):
    PROVEN_FALSE = "PROVEN_FALSE"
    PROVEN_TRUE = "PROVEN_TRUE"
    NOT_CONFIRMED = "NOT_CONFIRMED"


class RemoteRoleState(str, Enum):
    ABSENT_PROVEN = "ABSENT_PROVEN"
    CREATED_THEN_CLOSED_VERIFIED = "CREATED_THEN_CLOSED_VERIFIED"
    NOT_CONFIRMED = "NOT_CONFIRMED"


class EffectTruth(str, Enum):
    ZERO = "ZERO"
    OBSERVED = "OBSERVED"
    NOT_CONFIRMED = "NOT_CONFIRMED"


_FALSE_EFFECT_FLAGS = MappingProxyType(
    {
        "authority_created": False,
        "private_body_present": False,
        "path_present": False,
        "secret_present": False,
        "model_loaded": False,
        "inference_started": False,
        "wav_created": False,
        "external_effect_started": False,
    }
)

_FIXTURE_READBACK_BOUNDARY = MappingProxyType(
    {
        "producer_binding_state": "NOT_BOUND",
        "fixture_only": True,
        "canonical_producer_acceptance_state": "NOT_CONFIRMED",
        "canonical_producer_readback": False,
        "execution_ready": False,
    }
)


def _exact(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} is invalid")
    if len(value) > 200:
        raise ValueError(f"{name} exceeds 200 characters")
    normalized = unicodedata.normalize("NFKC", value)
    if (
        any(token in normalized for token in ("/", "\\", ":"))
        or normalized.startswith(".")
        or normalized.endswith(".")
        or ".." in normalized
    ):
        raise ValueError(f"{name} must not be a host path or URI")
    if not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _digest(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} is invalid")
    return validate_sha256(value, field_name=name)


def _bounded_int(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in {minimum}..{maximum}")
    return value


def _positive(value: Any, name: str) -> int:
    return _bounded_int(value, name, 1, 2_147_483_647)


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not _TIME_RE.fullmatch(value):
        raise ValueError(f"{name} must be canonical UTC")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be canonical UTC") from exc


def _enum(kind: type[Enum], value: Any, name: str) -> Enum:
    try:
        return kind(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


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


def _without(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    return {key: copy.deepcopy(item) for key, item in value.items() if key != field}


def _hash(domain: bytes, value: Mapping[str, Any], field: str) -> str:
    return sha256_bytes(domain + canonical_json_bytes(_without(value, field)))


def _validate_false_flags(value: Mapping[str, Any]) -> None:
    for name, expected in _FALSE_EFFECT_FLAGS.items():
        if value[name] is not expected:
            raise ValueError(f"{name} must remain false")


def _validate_fixture_readback_boundary(value: Mapping[str, Any]) -> None:
    for name, expected in _FIXTURE_READBACK_BOUNDARY.items():
        if value[name] != expected:
            raise ValueError(f"{name} cannot claim a canonical TASK074-C/D producer")


def _media_policy_body() -> dict[str, Any]:
    return {
        "contract_version": MEDIA_POLICY_CONTRACT_VERSION,
        "record_type": "OwnerVoiceReferenceMediaPolicy",
        "audio_container_signature": "RIFF/WAVE",
        "allowed_codec_tuples": [
            {"codec_name": "pcm_s16le", "sample_format": "signed-integer", "valid_bits_per_sample": 16},
            {"codec_name": "pcm_s24le", "sample_format": "signed-integer", "valid_bits_per_sample": 24},
        ],
        "allowed_sample_rates_hz": [16000, 22050, 24000, 32000, 44100, 48000],
        "channels": 1,
        "channel_layout": "mono",
        "duration_ms_inclusive": [1000, 60000],
        "decoded_frame_count_inclusive": [1, 2880000],
        "container_size_bytes_inclusive": [45, 8704000],
        "transcript_encoding": "UTF-8",
        "transcript_bom_allowed": False,
        "transcript_normalization": "NFC",
        "transcript_line_endings": "LF_ONLY",
        "transcript_nul_allowed": False,
        "transcript_control_policy": "LF_ONLY",
        "transcript_scalar_count_inclusive": [1, 4000],
        "transcript_utf8_bytes_inclusive": [1, 16384],
        "post_admission_rewrite_allowed": False,
    }


_MEDIA_POLICY_WITHOUT_HASH = _media_policy_body()
MEDIA_POLICY_SHA256 = sha256_bytes(
    _MEDIA_POLICY_DOMAIN + canonical_json_bytes(_MEDIA_POLICY_WITHOUT_HASH)
)


def owner_voice_reference_media_policy() -> dict[str, Any]:
    """Return the frozen body-free policy and its canonical digest."""

    return {**copy.deepcopy(_MEDIA_POLICY_WITHOUT_HASH), "media_policy_sha256": MEDIA_POLICY_SHA256}


@dataclass(frozen=True, slots=True, init=False)
class OwnerVoiceReferenceMediaFacts:
    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("media facts must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        codec_name: str,
        valid_bits_per_sample: int,
        sample_rate_hz: int,
        duration_ms: int,
        decoded_frame_count: int,
        container_size_bytes: int,
        audio_sha256: str,
    ) -> "OwnerVoiceReferenceMediaFacts":
        body: dict[str, Any] = {
            "contract_version": MEDIA_FACTS_CONTRACT_VERSION,
            "record_type": "OwnerVoiceReferenceMediaFacts",
            "media_policy_sha256": MEDIA_POLICY_SHA256,
            "audio_container_signature": "RIFF/WAVE",
            "audio_stream_count": 1,
            "video_stream_count": 0,
            "data_stream_count": 0,
            "codec_name": codec_name,
            "sample_format": "signed-integer",
            "valid_bits_per_sample": valid_bits_per_sample,
            "sample_rate_hz": sample_rate_hz,
            "channels": 1,
            "channel_layout": "mono",
            "duration_ms": duration_ms,
            "decoded_frame_count": decoded_frame_count,
            "container_size_bytes": container_size_bytes,
            "audio_sha256": audio_sha256,
            "body_present": False,
            "path_present": False,
        }
        body["media_facts_sha256"] = sha256_bytes(_MEDIA_FACTS_DOMAIN + canonical_json_bytes(body))
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OwnerVoiceReferenceMediaFacts":
        fields = {
            "contract_version", "record_type", "media_policy_sha256",
            "audio_container_signature", "audio_stream_count", "video_stream_count",
            "data_stream_count", "codec_name", "sample_format", "valid_bits_per_sample",
            "sample_rate_hz", "channels", "channel_layout", "duration_ms",
            "decoded_frame_count", "container_size_bytes", "audio_sha256",
            "body_present", "path_present", "media_facts_sha256",
        }
        _exact(value, fields, "OwnerVoiceReferenceMediaFacts")
        if value["contract_version"] != MEDIA_FACTS_CONTRACT_VERSION or value["record_type"] != "OwnerVoiceReferenceMediaFacts":
            raise ValueError("media facts identity/version is invalid")
        if value["media_policy_sha256"] != MEDIA_POLICY_SHA256:
            raise ValueError("media policy digest is not the frozen policy")
        if (
            value["audio_container_signature"] != "RIFF/WAVE"
            or value["audio_stream_count"] != 1
            or value["video_stream_count"] != 0
            or value["data_stream_count"] != 0
            or value["sample_format"] != "signed-integer"
            or value["channels"] != 1
            or value["channel_layout"] != "mono"
        ):
            raise ValueError("media container/stream/layout tuple is not admitted")
        codec_tuple = (value["codec_name"], value["sample_format"], value["valid_bits_per_sample"])
        if codec_tuple not in {("pcm_s16le", "signed-integer", 16), ("pcm_s24le", "signed-integer", 24)}:
            raise ValueError("media codec/bit-depth tuple is not admitted")
        if value["sample_rate_hz"] not in {16000, 22050, 24000, 32000, 44100, 48000}:
            raise ValueError("media sample rate is not admitted")
        _bounded_int(value["duration_ms"], "duration_ms", 1000, 60000)
        _bounded_int(value["decoded_frame_count"], "decoded_frame_count", 1, 2880000)
        _bounded_int(value["container_size_bytes"], "container_size_bytes", 45, 8704000)
        _digest(value["audio_sha256"], "audio_sha256")
        if value["body_present"] is not False or value["path_present"] is not False:
            raise ValueError("media facts must remain body/path free")
        if value["media_facts_sha256"] != _hash(_MEDIA_FACTS_DOMAIN, value, "media_facts_sha256"):
            raise ValueError("media facts digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


@dataclass(frozen=True, slots=True, init=False)
class OwnerVoiceReferenceTranscriptFacts:
    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("transcript facts must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        transcript_utf8_sha256: str,
        unicode_scalar_count: int,
        utf8_byte_count: int,
        strict_utf8_valid: bool = True,
        bom_present: bool = False,
        nfc_normalized: bool = True,
        lf_only: bool = True,
        nul_present: bool = False,
        forbidden_control_present: bool = False,
    ) -> "OwnerVoiceReferenceTranscriptFacts":
        body: dict[str, Any] = {
            "contract_version": TRANSCRIPT_FACTS_CONTRACT_VERSION,
            "record_type": "OwnerVoiceReferenceTranscriptFacts",
            "media_policy_sha256": MEDIA_POLICY_SHA256,
            "transcript_utf8_sha256": transcript_utf8_sha256,
            "unicode_scalar_count": unicode_scalar_count,
            "utf8_byte_count": utf8_byte_count,
            "strict_utf8_valid": strict_utf8_valid,
            "bom_present": bom_present,
            "nfc_normalized": nfc_normalized,
            "lf_only": lf_only,
            "nul_present": nul_present,
            "forbidden_control_present": forbidden_control_present,
            "post_admission_rewrite_performed": False,
            "body_present": False,
            "path_present": False,
        }
        body["transcript_facts_sha256"] = sha256_bytes(
            _TRANSCRIPT_FACTS_DOMAIN + canonical_json_bytes(body)
        )
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OwnerVoiceReferenceTranscriptFacts":
        fields = {
            "contract_version", "record_type", "media_policy_sha256",
            "transcript_utf8_sha256", "unicode_scalar_count", "utf8_byte_count",
            "strict_utf8_valid", "bom_present", "nfc_normalized", "lf_only",
            "nul_present", "forbidden_control_present", "post_admission_rewrite_performed",
            "body_present", "path_present", "transcript_facts_sha256",
        }
        _exact(value, fields, "OwnerVoiceReferenceTranscriptFacts")
        if value["contract_version"] != TRANSCRIPT_FACTS_CONTRACT_VERSION or value["record_type"] != "OwnerVoiceReferenceTranscriptFacts":
            raise ValueError("transcript facts identity/version is invalid")
        if value["media_policy_sha256"] != MEDIA_POLICY_SHA256:
            raise ValueError("transcript facts do not bind the frozen media policy")
        _digest(value["transcript_utf8_sha256"], "transcript_utf8_sha256")
        _bounded_int(value["unicode_scalar_count"], "unicode_scalar_count", 1, 4000)
        _bounded_int(value["utf8_byte_count"], "utf8_byte_count", 1, 16384)
        expected_bools = {
            "strict_utf8_valid": True,
            "bom_present": False,
            "nfc_normalized": True,
            "lf_only": True,
            "nul_present": False,
            "forbidden_control_present": False,
            "post_admission_rewrite_performed": False,
            "body_present": False,
            "path_present": False,
        }
        if any(value[name] is not expected for name, expected in expected_bools.items()):
            raise ValueError("transcript encoding/body policy is not admitted")
        if value["transcript_facts_sha256"] != _hash(
            _TRANSCRIPT_FACTS_DOMAIN, value, "transcript_facts_sha256"
        ):
            raise ValueError("transcript facts digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


@dataclass(frozen=True, slots=True, init=False)
class Task046OwnerReferenceTranscriptBindingFixture:
    """Synthetic TASK074-B fixture; never a TASK-046 producer receipt."""
    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("transcript binding must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        binding_id: str,
        project_id: str,
        voice_profile_id: str,
        voice_profile_revision_sha256: str,
        consent_current_evaluation_sha256: str,
        audio_source_identity_sha256: str,
        audio_sha256: str,
        transcript_revision: int,
        transcript_utf8_sha256: str,
        transcript_facts_sha256: str,
        human_verification_receipt_sha256: str,
        verified_at: str,
    ) -> "Task046OwnerReferenceTranscriptBindingFixture":
        body: dict[str, Any] = {
            "contract_version": TRANSCRIPT_BINDING_CONTRACT_VERSION,
            "record_type": "Task046OwnerReferenceTranscriptBindingFixture",
            "binding_id": binding_id,
            "semantic_owner": "TASK-074-FIXTURE",
            "intended_semantic_owner": "TASK-046",
            "project_id": project_id,
            "voice_profile_id": voice_profile_id,
            "voice_profile_revision_sha256": voice_profile_revision_sha256,
            "consent_current_evaluation_sha256": consent_current_evaluation_sha256,
            "audio_source_identity_sha256": audio_source_identity_sha256,
            "audio_sha256": audio_sha256,
            "transcript_revision": transcript_revision,
            "transcript_utf8_sha256": transcript_utf8_sha256,
            "transcript_facts_sha256": transcript_facts_sha256,
            "media_policy_sha256": MEDIA_POLICY_SHA256,
            "speaker_profile_exact_match": True,
            "transcript_audio_exact_match_human_verified": True,
            "human_verification_receipt_sha256": human_verification_receipt_sha256,
            "verified_at": verified_at,
            "producer_binding_state": "NOT_BOUND",
            "fixture_only": True,
            "canonical_producer_receipt": False,
            "execution_ready": False,
            "task046_owner_acceptance_sha256": None,
            "body_present": False,
            "path_present": False,
            "authority_created": False,
        }
        body["transcript_binding_receipt_sha256"] = sha256_bytes(
            _TRANSCRIPT_BINDING_DOMAIN + canonical_json_bytes(body)
        )
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Task046OwnerReferenceTranscriptBindingFixture":
        fields = {
            "contract_version", "record_type", "binding_id", "semantic_owner",
            "intended_semantic_owner", "project_id",
            "voice_profile_id", "voice_profile_revision_sha256",
            "consent_current_evaluation_sha256", "audio_source_identity_sha256",
            "audio_sha256", "transcript_revision", "transcript_utf8_sha256",
            "transcript_facts_sha256", "media_policy_sha256",
            "speaker_profile_exact_match", "transcript_audio_exact_match_human_verified",
            "human_verification_receipt_sha256", "verified_at", "producer_binding_state",
            "fixture_only", "canonical_producer_receipt", "execution_ready",
            "task046_owner_acceptance_sha256", "body_present",
            "path_present", "authority_created", "transcript_binding_receipt_sha256",
        }
        _exact(value, fields, "Task046OwnerReferenceTranscriptBindingFixture")
        if (
            value["contract_version"] != TRANSCRIPT_BINDING_CONTRACT_VERSION
            or value["record_type"] != "Task046OwnerReferenceTranscriptBindingFixture"
            or value["semantic_owner"] != "TASK-074-FIXTURE"
            or value["intended_semantic_owner"] != "TASK-046"
        ):
            raise ValueError("transcript binding identity/owner is invalid")
        for name in ("binding_id", "project_id", "voice_profile_id"):
            _identifier(value[name], name)
        for name in (
            "voice_profile_revision_sha256", "consent_current_evaluation_sha256",
            "audio_source_identity_sha256", "audio_sha256", "transcript_utf8_sha256",
            "transcript_facts_sha256", "human_verification_receipt_sha256",
        ):
            _digest(value[name], name)
        _positive(value["transcript_revision"], "transcript_revision")
        if value["media_policy_sha256"] != MEDIA_POLICY_SHA256:
            raise ValueError("transcript binding media policy mismatch")
        if value["speaker_profile_exact_match"] is not True or value["transcript_audio_exact_match_human_verified"] is not True:
            raise ValueError("speaker/profile/audio/transcript binding is not exact")
        _timestamp(value["verified_at"], "verified_at")
        _digest(
            value["task046_owner_acceptance_sha256"],
            "task046_owner_acceptance_sha256",
            nullable=True,
        )
        if value["task046_owner_acceptance_sha256"] is not None:
            raise ValueError("TASK074-B fixture cannot claim TASK-046 producer acceptance")
        if (
            value["producer_binding_state"] != "NOT_BOUND"
            or value["fixture_only"] is not True
            or value["canonical_producer_receipt"] is not False
            or value["execution_ready"] is not False
        ):
            raise ValueError("TASK-046 transcript binding fixture must remain producer-unbound")
        if value["body_present"] is not False or value["path_present"] is not False or value["authority_created"] is not False:
            raise ValueError("transcript binding must remain body/path/authority free")
        if value["transcript_binding_receipt_sha256"] != _hash(
            _TRANSCRIPT_BINDING_DOMAIN, value, "transcript_binding_receipt_sha256"
        ):
            raise ValueError("transcript binding digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


@dataclass(frozen=True, slots=True, init=False)
class OwnerVoiceReferencePreparePlan:
    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("prepare plan must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        project_id: str,
        project_manifest_revision_sha256: str,
        installed_context_sha256: str,
        voice_profile_id: str,
        voice_profile_revision_sha256: str,
        consent_current_evaluation_sha256: str,
        route_selection_sha256: str,
        source_classification: ReferenceSourceClassification,
        audio_source_identity_sha256: str,
        transcript_source_identity_sha256: str,
        media_facts_sha256: str,
        transcript_facts_sha256: str,
        transcript_binding_receipt_sha256: str,
        retention_policy: RetentionPolicy,
        retention_policy_revision_sha256: str,
        expires_at: str | None,
        expected_lifecycle_snapshot_sha256: str,
        human_action_receipt_sha256: str,
        task072_ticket_sha256: str,
        created_at: str,
    ) -> "OwnerVoiceReferencePreparePlan":
        body: dict[str, Any] = {
            "contract_version": PREPARE_PLAN_CONTRACT_VERSION,
            "record_type": "OwnerVoiceReferencePreparePlan",
            "operation_id": operation_id,
            "project_id": project_id,
            "project_manifest_revision_sha256": project_manifest_revision_sha256,
            "installed_context_sha256": installed_context_sha256,
            "voice_profile_id": voice_profile_id,
            "voice_profile_revision_sha256": voice_profile_revision_sha256,
            "consent_current_evaluation_sha256": consent_current_evaluation_sha256,
            "route_selection_sha256": route_selection_sha256,
            "source_classification": source_classification.value if isinstance(source_classification, ReferenceSourceClassification) else source_classification,
            "audio_source_identity_sha256": audio_source_identity_sha256,
            "transcript_source_identity_sha256": transcript_source_identity_sha256,
            "media_policy_sha256": MEDIA_POLICY_SHA256,
            "media_facts_sha256": media_facts_sha256,
            "transcript_facts_sha256": transcript_facts_sha256,
            "transcript_binding_receipt_sha256": transcript_binding_receipt_sha256,
            "retention_policy": retention_policy.value if isinstance(retention_policy, RetentionPolicy) else retention_policy,
            "retention_policy_revision_sha256": retention_policy_revision_sha256,
            "expires_at": expires_at,
            "expected_lifecycle_snapshot_sha256": expected_lifecycle_snapshot_sha256,
            "human_action_receipt_sha256": human_action_receipt_sha256,
            "task072_ticket_sha256": task072_ticket_sha256,
            "created_at": created_at,
            **dict(_FALSE_EFFECT_FLAGS),
        }
        body["prepare_plan_sha256"] = sha256_bytes(_PREPARE_PLAN_DOMAIN + canonical_json_bytes(body))
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OwnerVoiceReferencePreparePlan":
        fields = {
            "contract_version", "record_type", "operation_id", "project_id",
            "project_manifest_revision_sha256", "installed_context_sha256", "voice_profile_id",
            "voice_profile_revision_sha256", "consent_current_evaluation_sha256",
            "route_selection_sha256", "source_classification", "audio_source_identity_sha256",
            "transcript_source_identity_sha256", "media_policy_sha256", "media_facts_sha256",
            "transcript_facts_sha256", "transcript_binding_receipt_sha256",
            "retention_policy", "retention_policy_revision_sha256", "expires_at",
            "expected_lifecycle_snapshot_sha256", "human_action_receipt_sha256",
            "task072_ticket_sha256", "created_at", *set(_FALSE_EFFECT_FLAGS),
            "prepare_plan_sha256",
        }
        _exact(value, fields, "OwnerVoiceReferencePreparePlan")
        if value["contract_version"] != PREPARE_PLAN_CONTRACT_VERSION or value["record_type"] != "OwnerVoiceReferencePreparePlan":
            raise ValueError("prepare plan identity/version is invalid")
        for name in ("operation_id", "project_id", "voice_profile_id"):
            _identifier(value[name], name)
        for name in (
            "project_manifest_revision_sha256", "installed_context_sha256",
            "voice_profile_revision_sha256", "consent_current_evaluation_sha256",
            "route_selection_sha256", "audio_source_identity_sha256",
            "transcript_source_identity_sha256", "media_facts_sha256",
            "transcript_facts_sha256", "transcript_binding_receipt_sha256",
            "retention_policy_revision_sha256", "expected_lifecycle_snapshot_sha256",
            "human_action_receipt_sha256", "task072_ticket_sha256",
        ):
            _digest(value[name], name)
        if value["media_policy_sha256"] != MEDIA_POLICY_SHA256:
            raise ValueError("prepare plan media policy mismatch")
        _enum(ReferenceSourceClassification, value["source_classification"], "source_classification")
        policy = _enum(RetentionPolicy, value["retention_policy"], "retention_policy")
        expires = value["expires_at"]
        if policy is RetentionPolicy.OWNER_SELECTED_EXPIRY:
            if expires is None:
                raise ValueError("owner-selected expiry requires expires_at")
            _timestamp(expires, "expires_at")
        elif expires is not None:
            raise ValueError("expires_at is allowed only for owner-selected expiry")
        _timestamp(value["created_at"], "created_at")
        _validate_false_flags(value)
        if value["prepare_plan_sha256"] != _hash(_PREPARE_PLAN_DOMAIN, value, "prepare_plan_sha256"):
            raise ValueError("prepare plan digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


_PREPARATION_STATES = {
    ReferenceLifecycle.UNBOUND,
    ReferenceLifecycle.PREPARE_PLANNED,
    ReferenceLifecycle.PREPARING,
    ReferenceLifecycle.PREPARE_FAILED_NO_DERIVATIVE,
    ReferenceLifecycle.PREPARE_FAILED_RETAINED,
}
_V1_TERMINALS = {
    CapabilityLeaseV1Current.CONSUMED,
    CapabilityLeaseV1Current.BURNED,
    CapabilityLeaseV1Current.FAILED_CLOSED,
}
_V1_ACTIVE = {
    CapabilityLeaseV1Current.ISSUED,
    CapabilityLeaseV1Current.IN_FLIGHT,
    CapabilityLeaseV1Current.BODY_READ_STARTED,
}
_V2_TERMINALS = {
    CapabilityLeaseV2Current.CONSUMED,
    CapabilityLeaseV2Current.BURNED,
    CapabilityLeaseV2Current.FAILED_CLOSED,
}
_V2_ACTIVE = set(CapabilityLeaseV2Current) - _V2_TERMINALS - {CapabilityLeaseV2Current.V2_ABSENT}


def _validate_handle_cardinality(
    v1: CapabilityLeaseV1Current,
    v1_count: int,
    v2: CapabilityLeaseV2Current,
    v2_count: int,
) -> None:
    expected_v1 = 1 if v1 in _V1_ACTIVE else 0
    if v1_count != expected_v1:
        raise ValueError("V1 live-handle cardinality disagrees with state")
    if v2 is CapabilityLeaseV2Current.V2_ABSENT or v2 in _V2_TERMINALS:
        if v2_count != 0:
            raise ValueError("absent/terminal V2 must have handle count zero")
    elif v2 is CapabilityLeaseV2Current.CHILD_TRANSFER_IN_FLIGHT:
        if v2_count not in {2, 3, 4}:
            raise ValueError("V2 transfer must retain the bounded two-role physical handle set")
    elif v2_count != 2:
        raise ValueError("active V2 must own exactly the two logical role handles")


def _validate_retained_object(lifecycle: ReferenceLifecycle, retained: RetainedObject) -> None:
    allowed: dict[ReferenceLifecycle, set[RetainedObject]] = {
        ReferenceLifecycle.UNBOUND: {RetainedObject.NONE},
        ReferenceLifecycle.PREPARE_PLANNED: {RetainedObject.NONE},
        ReferenceLifecycle.PREPARING: {
            RetainedObject.NONE, RetainedObject.ALLOCATED, RetainedObject.ENCRYPTED_UNPUBLISHED
        },
        ReferenceLifecycle.PREPARE_FAILED_NO_DERIVATIVE: {RetainedObject.NONE, RetainedObject.PURGED},
        ReferenceLifecycle.PREPARE_FAILED_RETAINED: {
            RetainedObject.RECONCILIATION_REQUIRED, RetainedObject.RECOVERABLE_RETAINED,
            RetainedObject.KEY_REVOKED, RetainedObject.FOREIGN_PRESERVED,
        },
        ReferenceLifecycle.PREPARED: {RetainedObject.PUBLISHED},
        ReferenceLifecycle.REVOKE_PENDING: {RetainedObject.PUBLISHED},
        ReferenceLifecycle.REVOKED: {
            RetainedObject.PUBLISHED, RetainedObject.KEY_REVOKED, RetainedObject.PURGED,
            RetainedObject.FOREIGN_PRESERVED,
        },
        ReferenceLifecycle.PURGE_PENDING: {
            RetainedObject.RECOVERABLE_RETAINED, RetainedObject.PUBLISHED, RetainedObject.KEY_REVOKED,
        },
        ReferenceLifecycle.PURGED: {RetainedObject.PURGED},
        ReferenceLifecycle.PURGE_NOT_CONFIRMED: {
            RetainedObject.RECOVERABLE_RETAINED, RetainedObject.PUBLISHED,
            RetainedObject.KEY_REVOKED, RetainedObject.FOREIGN_PRESERVED,
        },
    }
    if retained not in allowed[lifecycle]:
        raise ValueError("RL/RO tuple is outside the closed matrix")


def _validate_joint_tuple(
    lifecycle: ReferenceLifecycle,
    retained: RetainedObject,
    v1: CapabilityLeaseV1Current,
    v1_count: int,
    v2: CapabilityLeaseV2Current,
    v2_count: int,
    intent: RevokeExpiryIntent,
) -> None:
    _validate_retained_object(lifecycle, retained)
    _validate_handle_cardinality(v1, v1_count, v2, v2_count)
    if v1 is not CapabilityLeaseV1Current.NONE and v2 is not CapabilityLeaseV2Current.V2_ABSENT:
        raise ValueError("V1 and V2 current identities cannot coexist")
    if lifecycle in _PREPARATION_STATES:
        if v1 is not CapabilityLeaseV1Current.NONE or v2 is not CapabilityLeaseV2Current.V2_ABSENT:
            raise ValueError("preparation/failure states cannot carry a lease")
        if intent is not RevokeExpiryIntent.ABSENT:
            raise ValueError("preparation states cannot carry revoke/expiry intent")
    elif lifecycle is ReferenceLifecycle.PREPARED:
        if intent is not RevokeExpiryIntent.ABSENT:
            raise ValueError("PREPARED snapshot cannot carry a committed revoke/expiry intent")
    elif lifecycle is ReferenceLifecycle.REVOKE_PENDING:
        valid_v1 = v1 in (_V1_ACTIVE | _V1_TERMINALS) and v2 is CapabilityLeaseV2Current.V2_ABSENT
        valid_v2 = v1 is CapabilityLeaseV1Current.NONE and v2 is not CapabilityLeaseV2Current.V2_ABSENT
        if not (valid_v1 or valid_v2) or intent is RevokeExpiryIntent.ABSENT:
            raise ValueError("REVOKE_PENDING tuple is outside the finalize-only matrix")
    else:
        if v1 is not CapabilityLeaseV1Current.NONE:
            raise ValueError("revoked/purge states require current V1 NONE/0")
        if v2 not in (_V2_TERMINALS | {CapabilityLeaseV2Current.V2_ABSENT}):
            raise ValueError("revoked/purge states cannot carry a nonterminal V2 lease")
        if lifecycle is ReferenceLifecycle.REVOKED and intent is RevokeExpiryIntent.ABSENT:
            raise ValueError("terminal/purge state requires retained revoke/expiry lineage")


@dataclass(frozen=True, slots=True, init=False)
class ReferenceDomainSnapshot:
    """Body-free audit snapshot; never a capability or CAS implementation."""

    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("domain snapshot must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        reference_id: str,
        reference_revision: int,
        predecessor_snapshot_sha256: str | None,
        project_id: str,
        project_manifest_revision_sha256: str,
        voice_profile_id: str,
        voice_profile_revision_sha256: str,
        consent_current_evaluation_sha256: str,
        route_selection_sha256: str,
        reference_pair_sha256: str,
        reference_lifecycle: ReferenceLifecycle,
        retained_object: RetainedObject,
        retained_object_generation: int,
        retained_object_revision_sha256: str,
        v1_state: CapabilityLeaseV1Current,
        v1_lease_identity_sha256: str | None,
        v1_live_handle_count: int,
        v1_terminal_history_sha256: str | None,
        v2_state: CapabilityLeaseV2Current,
        v2_lease_identity_sha256: str | None,
        v2_live_handle_count: int,
        v2_terminal_history_sha256: str | None,
        revoke_or_expiry_intent: RevokeExpiryIntent,
        revoke_or_expiry_event_sha256: str | None,
        purge_human_action_receipt_sha256: str | None,
        ownership_recovery_readback_sha256: str | None,
        broker_domain_sha256: str,
        broker_process_identity_sha256: str,
        broker_session_sha256: str,
        product_build_sha256: str,
        broker_protocol_version: str,
        trusted_time_domain_sha256: str,
        trusted_time_receipt_sha256: str | None,
        currentness_readback_sha256: str,
        semantic_operation_key: str,
        current_operation_id: str | None,
        last_retired_semantic_operation_key: str | None,
        last_retired_operation_id: str | None,
        committed_event_sha256: str,
        fence_revision: int,
        predecessor_fence_sha256: str | None,
        observed_at: str,
    ) -> "ReferenceDomainSnapshot":
        body: dict[str, Any] = {
            "contract_version": DOMAIN_SNAPSHOT_CONTRACT_VERSION,
            "record_type": "ReferenceDomainSnapshot",
            "reference_id": reference_id,
            "reference_revision": reference_revision,
            "predecessor_snapshot_sha256": predecessor_snapshot_sha256,
            "project_id": project_id,
            "project_manifest_revision_sha256": project_manifest_revision_sha256,
            "voice_profile_id": voice_profile_id,
            "voice_profile_revision_sha256": voice_profile_revision_sha256,
            "consent_current_evaluation_sha256": consent_current_evaluation_sha256,
            "route_selection_sha256": route_selection_sha256,
            "reference_pair_sha256": reference_pair_sha256,
            "reference_lifecycle": reference_lifecycle.value if isinstance(reference_lifecycle, ReferenceLifecycle) else reference_lifecycle,
            "retained_object": retained_object.value if isinstance(retained_object, RetainedObject) else retained_object,
            "retained_object_generation": retained_object_generation,
            "retained_object_revision_sha256": retained_object_revision_sha256,
            "v1_state": v1_state.value if isinstance(v1_state, CapabilityLeaseV1Current) else v1_state,
            "v1_lease_identity_sha256": v1_lease_identity_sha256,
            "v1_live_handle_count": v1_live_handle_count,
            "v1_terminal_history_sha256": v1_terminal_history_sha256,
            "v2_state": v2_state.value if isinstance(v2_state, CapabilityLeaseV2Current) else v2_state,
            "v2_lease_identity_sha256": v2_lease_identity_sha256,
            "v2_live_handle_count": v2_live_handle_count,
            "v2_terminal_history_sha256": v2_terminal_history_sha256,
            "revoke_or_expiry_intent": revoke_or_expiry_intent.value if isinstance(revoke_or_expiry_intent, RevokeExpiryIntent) else revoke_or_expiry_intent,
            "revoke_or_expiry_event_sha256": revoke_or_expiry_event_sha256,
            "purge_human_action_receipt_sha256": purge_human_action_receipt_sha256,
            "ownership_recovery_readback_sha256": ownership_recovery_readback_sha256,
            "broker_domain_sha256": broker_domain_sha256,
            "broker_process_identity_sha256": broker_process_identity_sha256,
            "broker_session_sha256": broker_session_sha256,
            "product_build_sha256": product_build_sha256,
            "broker_protocol_version": broker_protocol_version,
            "trusted_time_domain_sha256": trusted_time_domain_sha256,
            "trusted_time_receipt_sha256": trusted_time_receipt_sha256,
            "currentness_readback_sha256": currentness_readback_sha256,
            "semantic_operation_key": semantic_operation_key,
            "current_operation_id": current_operation_id,
            "last_retired_semantic_operation_key": last_retired_semantic_operation_key,
            "last_retired_operation_id": last_retired_operation_id,
            "committed_event_sha256": committed_event_sha256,
            "fence_revision": fence_revision,
            "predecessor_fence_sha256": predecessor_fence_sha256,
            "guard_current": True,
            "observed_at": observed_at,
            **dict(_FALSE_EFFECT_FLAGS),
        }
        fence_body = {
            key: body[key]
            for key in (
                "reference_id", "reference_revision", "predecessor_snapshot_sha256",
                "project_id", "project_manifest_revision_sha256", "voice_profile_id",
                "voice_profile_revision_sha256", "consent_current_evaluation_sha256",
                "route_selection_sha256", "reference_pair_sha256", "reference_lifecycle",
                "retained_object", "retained_object_generation", "retained_object_revision_sha256",
                "v1_state", "v1_lease_identity_sha256", "v1_live_handle_count",
                "v1_terminal_history_sha256", "v2_state", "v2_lease_identity_sha256",
                "v2_live_handle_count", "v2_terminal_history_sha256",
                "revoke_or_expiry_intent", "revoke_or_expiry_event_sha256",
                "purge_human_action_receipt_sha256", "ownership_recovery_readback_sha256",
                "broker_domain_sha256", "broker_process_identity_sha256", "broker_session_sha256",
                "product_build_sha256", "broker_protocol_version", "trusted_time_domain_sha256",
                "trusted_time_receipt_sha256", "currentness_readback_sha256",
                "semantic_operation_key", "current_operation_id",
                "last_retired_semantic_operation_key", "last_retired_operation_id",
                "committed_event_sha256",
                "fence_revision", "predecessor_fence_sha256",
            )
        }
        body["fence_sha256"] = sha256_bytes(_FENCE_DOMAIN + canonical_json_bytes(fence_body))
        body["snapshot_sha256"] = sha256_bytes(_SNAPSHOT_DOMAIN + canonical_json_bytes(body))
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReferenceDomainSnapshot":
        fields = {
            "contract_version", "record_type", "reference_id", "reference_revision",
            "predecessor_snapshot_sha256", "project_id", "project_manifest_revision_sha256",
            "voice_profile_id", "voice_profile_revision_sha256",
            "consent_current_evaluation_sha256", "route_selection_sha256",
            "reference_pair_sha256", "reference_lifecycle", "retained_object",
            "retained_object_generation", "retained_object_revision_sha256", "v1_state",
            "v1_lease_identity_sha256", "v1_live_handle_count", "v1_terminal_history_sha256",
            "v2_state", "v2_lease_identity_sha256", "v2_live_handle_count",
            "v2_terminal_history_sha256", "revoke_or_expiry_intent",
            "revoke_or_expiry_event_sha256", "purge_human_action_receipt_sha256",
            "ownership_recovery_readback_sha256", "broker_domain_sha256",
            "broker_process_identity_sha256", "broker_session_sha256", "product_build_sha256",
            "broker_protocol_version", "trusted_time_domain_sha256",
            "trusted_time_receipt_sha256", "currentness_readback_sha256",
            "semantic_operation_key", "current_operation_id",
            "last_retired_semantic_operation_key", "last_retired_operation_id",
            "committed_event_sha256",
            "fence_revision", "predecessor_fence_sha256",
            "fence_sha256", "guard_current", "observed_at", *set(_FALSE_EFFECT_FLAGS),
            "snapshot_sha256",
        }
        _exact(value, fields, "ReferenceDomainSnapshot")
        if value["contract_version"] != DOMAIN_SNAPSHOT_CONTRACT_VERSION or value["record_type"] != "ReferenceDomainSnapshot":
            raise ValueError("domain snapshot identity/version is invalid")
        for name in ("reference_id", "project_id", "voice_profile_id", "semantic_operation_key", "broker_protocol_version"):
            _identifier(value[name], name)
        revision = _positive(value["reference_revision"], "reference_revision")
        predecessor = _digest(value["predecessor_snapshot_sha256"], "predecessor_snapshot_sha256", nullable=True)
        if (revision == 1) != (predecessor is None):
            raise ValueError("reference snapshot genesis/predecessor invariant is invalid")
        fence_revision = _positive(value["fence_revision"], "fence_revision")
        predecessor_fence = _digest(value["predecessor_fence_sha256"], "predecessor_fence_sha256", nullable=True)
        if (fence_revision == 1) != (predecessor_fence is None):
            raise ValueError("fence genesis/predecessor invariant is invalid")
        fence_body = {
            key: copy.deepcopy(value[key])
            for key in (
                "reference_id", "reference_revision", "predecessor_snapshot_sha256",
                "project_id", "project_manifest_revision_sha256", "voice_profile_id",
                "voice_profile_revision_sha256", "consent_current_evaluation_sha256",
                "route_selection_sha256", "reference_pair_sha256", "reference_lifecycle",
                "retained_object", "retained_object_generation", "retained_object_revision_sha256",
                "v1_state", "v1_lease_identity_sha256", "v1_live_handle_count",
                "v1_terminal_history_sha256", "v2_state", "v2_lease_identity_sha256",
                "v2_live_handle_count", "v2_terminal_history_sha256",
                "revoke_or_expiry_intent", "revoke_or_expiry_event_sha256",
                "purge_human_action_receipt_sha256", "ownership_recovery_readback_sha256",
                "broker_domain_sha256", "broker_process_identity_sha256", "broker_session_sha256",
                "product_build_sha256", "broker_protocol_version", "trusted_time_domain_sha256",
                "trusted_time_receipt_sha256", "currentness_readback_sha256",
                "semantic_operation_key", "current_operation_id",
                "last_retired_semantic_operation_key", "last_retired_operation_id",
                "committed_event_sha256",
                "fence_revision", "predecessor_fence_sha256",
            )
        }
        expected_fence = sha256_bytes(_FENCE_DOMAIN + canonical_json_bytes(fence_body))
        if value["fence_sha256"] != expected_fence:
            raise ValueError("lease-version fence digest mismatch")
        for name in (
            "project_manifest_revision_sha256", "voice_profile_revision_sha256",
            "consent_current_evaluation_sha256", "route_selection_sha256", "reference_pair_sha256",
            "retained_object_revision_sha256", "broker_domain_sha256",
            "broker_process_identity_sha256", "broker_session_sha256", "product_build_sha256",
            "trusted_time_domain_sha256", "currentness_readback_sha256", "committed_event_sha256",
        ):
            _digest(value[name], name)
        _positive(value["retained_object_generation"], "retained_object_generation")
        _digest(value["trusted_time_receipt_sha256"], "trusted_time_receipt_sha256", nullable=True)
        v1_identity = _digest(value["v1_lease_identity_sha256"], "v1_lease_identity_sha256", nullable=True)
        v2_identity = _digest(value["v2_lease_identity_sha256"], "v2_lease_identity_sha256", nullable=True)
        v1_history = _digest(value["v1_terminal_history_sha256"], "v1_terminal_history_sha256", nullable=True)
        v2_history = _digest(value["v2_terminal_history_sha256"], "v2_terminal_history_sha256", nullable=True)
        revoke_event = _digest(value["revoke_or_expiry_event_sha256"], "revoke_or_expiry_event_sha256", nullable=True)
        purge_action = _digest(value["purge_human_action_receipt_sha256"], "purge_human_action_receipt_sha256", nullable=True)
        ownership_recovery = _digest(value["ownership_recovery_readback_sha256"], "ownership_recovery_readback_sha256", nullable=True)
        if value["current_operation_id"] is not None:
            _identifier(value["current_operation_id"], "current_operation_id")
        last_retired_semantic = value["last_retired_semantic_operation_key"]
        last_retired_operation = value["last_retired_operation_id"]
        if (last_retired_semantic is None) != (last_retired_operation is None):
            raise ValueError("last retired operation identity is partial")
        if last_retired_semantic is not None:
            _identifier(last_retired_semantic, "last_retired_semantic_operation_key")
            _identifier(last_retired_operation, "last_retired_operation_id")
        lifecycle = _enum(ReferenceLifecycle, value["reference_lifecycle"], "reference_lifecycle")
        retained = _enum(RetainedObject, value["retained_object"], "retained_object")
        v1 = _enum(CapabilityLeaseV1Current, value["v1_state"], "v1_state")
        v2 = _enum(CapabilityLeaseV2Current, value["v2_state"], "v2_state")
        intent = _enum(RevokeExpiryIntent, value["revoke_or_expiry_intent"], "revoke_or_expiry_intent")
        v1_count = _bounded_int(value["v1_live_handle_count"], "v1_live_handle_count", 0, 1)
        v2_count = _bounded_int(value["v2_live_handle_count"], "v2_live_handle_count", 0, 4)
        _validate_joint_tuple(lifecycle, retained, v1, v1_count, v2, v2_count, intent)  # type: ignore[arg-type]
        if (v1 is CapabilityLeaseV1Current.NONE) != (v1_identity is None):
            raise ValueError("V1 current lease identity/state mismatch")
        if (v2 is CapabilityLeaseV2Current.V2_ABSENT) != (v2_identity is None):
            raise ValueError("V2 current lease identity/state mismatch")
        if v1 in _V1_TERMINALS and v1_history is None:
            raise ValueError("V1 terminal current state requires exact immutable history")
        if v2 in _V2_TERMINALS and v2_history is None:
            raise ValueError("V2 terminal current state requires exact immutable history")
        if (intent is RevokeExpiryIntent.ABSENT) != (revoke_event is None):
            if not (lifecycle is ReferenceLifecycle.PURGE_NOT_CONFIRMED and intent is RevokeExpiryIntent.ABSENT and revoke_event is None):
                raise ValueError("revoke/expiry intent event binding mismatch")
        if lifecycle in {ReferenceLifecycle.PURGE_PENDING, ReferenceLifecycle.PURGED, ReferenceLifecycle.PURGE_NOT_CONFIRMED}:
            if purge_action is None:
                raise ValueError("purge lifecycle requires exact Human action binding")
        elif purge_action is not None or ownership_recovery is not None:
            raise ValueError("non-purge lifecycle cannot carry purge/recovery authority")
        if value["guard_current"] is not True:
            raise ValueError("domain snapshot guard must be exact/current")
        _timestamp(value["observed_at"], "observed_at")
        _validate_false_flags(value)
        if value["snapshot_sha256"] != _hash(_SNAPSHOT_DOMAIN, value, "snapshot_sha256"):
            raise ValueError("domain snapshot digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    @property
    def lifecycle(self) -> ReferenceLifecycle:
        return ReferenceLifecycle(self._data["reference_lifecycle"])

    @property
    def snapshot_sha256(self) -> str:
        return self._data["snapshot_sha256"]

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


def validate_v2_mint_predecessor(snapshot: ReferenceDomainSnapshot) -> None:
    if not isinstance(snapshot, ReferenceDomainSnapshot):
        raise TypeError("snapshot must be ReferenceDomainSnapshot")
    value = snapshot.to_dict()
    expected = {
        "reference_lifecycle": ReferenceLifecycle.PREPARED.value,
        "retained_object": RetainedObject.PUBLISHED.value,
        "v1_state": CapabilityLeaseV1Current.NONE.value,
        "v1_lease_identity_sha256": None,
        "v1_live_handle_count": 0,
        "v2_state": CapabilityLeaseV2Current.V2_ABSENT.value,
        "v2_lease_identity_sha256": None,
        "v2_live_handle_count": 0,
        "revoke_or_expiry_intent": RevokeExpiryIntent.ABSENT.value,
        "guard_current": True,
    }
    if any(value[name] != item for name, item in expected.items()):
        raise ValueError("snapshot is not the exact V2 mint predecessor")
    if value["trusted_time_receipt_sha256"] is None or value["currentness_readback_sha256"] is None:
        raise ValueError("V2 mint requires current trusted-time/currentness readback")


def validate_v2_terminal_retire_predecessor(snapshot: ReferenceDomainSnapshot) -> None:
    if not isinstance(snapshot, ReferenceDomainSnapshot):
        raise TypeError("snapshot must be ReferenceDomainSnapshot")
    value = snapshot.to_dict()
    if not (
        value["reference_lifecycle"] == ReferenceLifecycle.PREPARED.value
        and value["retained_object"] == RetainedObject.PUBLISHED.value
        and value["v1_state"] == CapabilityLeaseV1Current.NONE.value
        and value["v1_live_handle_count"] == 0
        and value["v2_state"] in {state.value for state in _V2_TERMINALS}
        and value["v2_lease_identity_sha256"] is not None
        and value["v2_live_handle_count"] == 0
        and value["v2_terminal_history_sha256"] is not None
        and value["revoke_or_expiry_intent"] == RevokeExpiryIntent.ABSENT.value
        and value["revoke_or_expiry_event_sha256"] is None
        and value["guard_current"] is True
    ):
        raise ValueError("snapshot is not the exact terminal-three retirement predecessor")


def validate_v1_finalize_predecessor(snapshot: ReferenceDomainSnapshot) -> None:
    if not isinstance(snapshot, ReferenceDomainSnapshot):
        raise TypeError("snapshot must be ReferenceDomainSnapshot")
    value = snapshot.to_dict()
    if not (
        value["reference_lifecycle"] == ReferenceLifecycle.REVOKE_PENDING.value
        and value["retained_object"] == RetainedObject.PUBLISHED.value
        and value["v1_state"] in {state.value for state in _V1_TERMINALS}
        and value["v1_lease_identity_sha256"] is not None
        and value["v1_live_handle_count"] == 0
        and value["v2_state"] == CapabilityLeaseV2Current.V2_ABSENT.value
        and value["v2_live_handle_count"] == 0
        and value["v1_terminal_history_sha256"] is not None
        and value["revoke_or_expiry_intent"] != RevokeExpiryIntent.ABSENT.value
        and value["revoke_or_expiry_event_sha256"] is not None
    ):
        raise ValueError("snapshot is not the V1 terminal finalize-only predecessor")


def _require_lineage(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    event: ReferenceTransition,
) -> None:
    for name in (
        "reference_id", "project_id", "project_manifest_revision_sha256", "voice_profile_id",
        "voice_profile_revision_sha256", "consent_current_evaluation_sha256",
        "route_selection_sha256", "reference_pair_sha256", "broker_domain_sha256",
        "broker_process_identity_sha256", "broker_session_sha256", "product_build_sha256",
        "broker_protocol_version", "trusted_time_domain_sha256",
    ):
        if previous[name] != current[name]:
            raise ValueError(f"reference transition {name} mismatch")

    terminal_retirement_events = {
        ReferenceTransition.V2_TERMINAL_RETIRE,
        ReferenceTransition.V2_TERMINAL_REVOKE_FINALIZE,
    }
    if event is ReferenceTransition.V2_ISSUE:
        if current["current_operation_id"] is None:
            raise ValueError("V2 issue requires an exact current operation identity")
        is_repeated_operation = any(
            previous[name] is not None
            for name in (
                "v1_terminal_history_sha256",
                "v2_terminal_history_sha256",
                "last_retired_operation_id",
            )
        )
        if is_repeated_operation and (
            current["semantic_operation_key"]
            in {
                previous["semantic_operation_key"],
                previous["last_retired_semantic_operation_key"],
            }
            or current["current_operation_id"]
            in {
                previous["current_operation_id"],
                previous["last_retired_operation_id"],
            }
        ):
            raise ValueError(
                "repeated V2 issue requires an identity distinct from both retired and retirement operations"
            )
        if (
            current["last_retired_semantic_operation_key"]
            != previous["last_retired_semantic_operation_key"]
            or current["last_retired_operation_id"]
            != previous["last_retired_operation_id"]
        ):
            raise ValueError("V2 issue cannot rewrite last retired operation identity")
    elif event in terminal_retirement_events:
        if previous["current_operation_id"] is None or current["current_operation_id"] is None:
            raise ValueError("terminal retirement requires retired and retirement operation identities")
        if (
            current["semantic_operation_key"] == previous["semantic_operation_key"]
            or current["current_operation_id"] == previous["current_operation_id"]
        ):
            raise ValueError("terminal retirement operation identity must be fresh")
        if (
            current["last_retired_semantic_operation_key"]
            != previous["semantic_operation_key"]
            or current["last_retired_operation_id"]
            != previous["current_operation_id"]
        ):
            raise ValueError("terminal retirement result did not fence the retired operation identity")
    elif (
        current["semantic_operation_key"] != previous["semantic_operation_key"]
        or current["current_operation_id"] != previous["current_operation_id"]
        or current["last_retired_semantic_operation_key"]
        != previous["last_retired_semantic_operation_key"]
        or current["last_retired_operation_id"] != previous["last_retired_operation_id"]
    ):
        raise ValueError("reference transition operation lineage mismatch")

    preparation_events = {
        ReferenceTransition.PREPARE_PLAN,
        ReferenceTransition.PREPARE_START,
        ReferenceTransition.PREPARE_PUBLISH,
        ReferenceTransition.PREPARE_FAIL_NO_DERIVATIVE,
        ReferenceTransition.PREPARE_FAIL_RETAINED,
    }
    if event not in preparation_events | {ReferenceTransition.PURGE_SUCCESS}:
        for name in (
            "retained_object",
            "retained_object_generation",
            "retained_object_revision_sha256",
        ):
            if previous[name] != current[name]:
                raise ValueError(f"reference transition {name} mismatch")
    elif event is ReferenceTransition.PURGE_SUCCESS and (
        current["retained_object_generation"]
        != previous["retained_object_generation"] + 1
        or current["retained_object_revision_sha256"]
        == previous["retained_object_revision_sha256"]
    ):
        raise ValueError("purge success requires the exact next retained-object generation")

    v1_history_append = (
        event is ReferenceTransition.REVOKE_DIRECT
        and previous["v1_state"] == CapabilityLeaseV1Current.ISSUED.value
    )
    v2_history_append = event in {
        ReferenceTransition.V2_CONSUME,
        ReferenceTransition.V2_BURN,
        ReferenceTransition.V2_FAIL_CLOSED,
    } or (
        event is ReferenceTransition.REVOKE_DIRECT
        and previous["v2_state"] == CapabilityLeaseV2Current.ISSUED.value
    )
    for name, append_allowed in (
        ("v1_terminal_history_sha256", v1_history_append),
        ("v2_terminal_history_sha256", v2_history_append),
    ):
        if append_allowed:
            if current[name] is None or current[name] == previous[name]:
                raise ValueError(f"reference transition {name} was not appended exactly once")
        elif current[name] != previous[name]:
            raise ValueError(f"reference transition {name} mismatch")
    if current["reference_revision"] != previous["reference_revision"] + 1:
        raise ValueError("reference transition revision is not contiguous")
    if current["predecessor_snapshot_sha256"] != previous["snapshot_sha256"]:
        raise ValueError("reference transition predecessor mismatch")
    if current["fence_revision"] != previous["fence_revision"] + 1:
        raise ValueError("reference transition fence is not contiguous")
    if current["predecessor_fence_sha256"] != previous["fence_sha256"]:
        raise ValueError("reference transition fence predecessor mismatch")
    if current["committed_event_sha256"] == previous["committed_event_sha256"]:
        raise ValueError("reference transition committed event identity was replayed")


def validate_reference_transition(
    previous: ReferenceDomainSnapshot,
    current: ReferenceDomainSnapshot,
    event: ReferenceTransition,
) -> None:
    """Validate an observed transition; never perform the transition."""

    if not isinstance(previous, ReferenceDomainSnapshot) or not isinstance(current, ReferenceDomainSnapshot):
        raise TypeError("transition snapshots must use ReferenceDomainSnapshot")
    if not isinstance(event, ReferenceTransition):
        raise TypeError("event must use ReferenceTransition")
    before, after = previous.to_dict(), current.to_dict()
    _require_lineage(before, after, event)
    lifecycle_pair = (before["reference_lifecycle"], after["reference_lifecycle"])
    preparation_pairs = {
        ReferenceTransition.PREPARE_PLAN: ("UNBOUND", "PREPARE_PLANNED"),
        ReferenceTransition.PREPARE_START: ("PREPARE_PLANNED", "PREPARING"),
        ReferenceTransition.PREPARE_PUBLISH: ("PREPARING", "PREPARED"),
        ReferenceTransition.PREPARE_FAIL_NO_DERIVATIVE: ("PREPARING", "PREPARE_FAILED_NO_DERIVATIVE"),
        ReferenceTransition.PREPARE_FAIL_RETAINED: ("PREPARING", "PREPARE_FAILED_RETAINED"),
    }
    if event in preparation_pairs:
        if lifecycle_pair != preparation_pairs[event]:
            raise ValueError("preparation lifecycle edge is invalid")
        if any(
            value["v1_state"] != CapabilityLeaseV1Current.NONE.value
            or value["v2_state"] != CapabilityLeaseV2Current.V2_ABSENT.value
            for value in (before, after)
        ):
            raise ValueError("preparation edge cannot carry a current lease")
        if event is ReferenceTransition.PREPARE_PUBLISH and after["retained_object"] != RetainedObject.PUBLISHED.value:
            raise ValueError("prepare publish must commit the exact PUBLISHED object")
        return

    active_v2_edges = {
        ReferenceTransition.V2_PARENT_DELEGATION_BEGIN: ("ISSUED", "IN_FLIGHT_PARENT_DELEGATION"),
        ReferenceTransition.V2_CHILD_TRANSFER_BEGIN: ("IN_FLIGHT_PARENT_DELEGATION", "CHILD_TRANSFER_IN_FLIGHT"),
        ReferenceTransition.V2_CHILD_PAIR_READY: ("CHILD_TRANSFER_IN_FLIGHT", "CHILD_PAIR_READY"),
        ReferenceTransition.V2_BODY_READ_BEGIN: ("CHILD_PAIR_READY", "BODY_READ_STARTED"),
        ReferenceTransition.V2_CONSUME: ("BODY_READ_STARTED", "CONSUMED"),
    }
    if event in active_v2_edges:
        before_state, after_state = active_v2_edges[event]
        allowed_lifecycle = "REVOKE_PENDING" if event is ReferenceTransition.V2_CONSUME and before["reference_lifecycle"] == "REVOKE_PENDING" else "PREPARED"
        if (
            lifecycle_pair != (allowed_lifecycle, allowed_lifecycle)
            or before["v2_state"] != before_state
            or after["v2_state"] != after_state
            or before["v2_lease_identity_sha256"] != after["v2_lease_identity_sha256"]
            or before["v2_lease_identity_sha256"] is None
            or before["v1_state"] != "NONE"
            or after["v1_state"] != "NONE"
            or before["retained_object"] != "PUBLISHED"
            or after["retained_object"] != "PUBLISHED"
        ):
            raise ValueError("V2 active edge/lease lineage is invalid")
        if event is ReferenceTransition.V2_CONSUME and (
            after["v2_live_handle_count"] != 0 or after["v2_terminal_history_sha256"] is None
        ):
            raise ValueError("V2 consume requires closed handles and immutable terminal history")
        return

    if event in {ReferenceTransition.V2_BURN, ReferenceTransition.V2_FAIL_CLOSED}:
        expected_terminal = "BURNED" if event is ReferenceTransition.V2_BURN else "FAILED_CLOSED"
        if (
            before["reference_lifecycle"] not in {"PREPARED", "REVOKE_PENDING"}
            or after["reference_lifecycle"] != before["reference_lifecycle"]
            or before["v2_state"] not in {state.value for state in _V2_ACTIVE}
            or after["v2_state"] != expected_terminal
            or before["v2_lease_identity_sha256"] != after["v2_lease_identity_sha256"]
            or after["v2_live_handle_count"] != 0
            or after["v2_terminal_history_sha256"] is None
        ):
            raise ValueError("V2 terminalization edge is invalid")
        return

    if event is ReferenceTransition.V2_ISSUE:
        validate_v2_mint_predecessor(previous)
        if not (
            after["reference_lifecycle"] == "PREPARED"
            and after["retained_object"] == "PUBLISHED"
            and after["v1_state"] == "NONE"
            and after["v1_lease_identity_sha256"] is None
            and after["v2_state"] == "ISSUED"
            and after["v2_lease_identity_sha256"] is not None
            and after["v2_live_handle_count"] == 2
        ):
            raise ValueError("V2 issue result tuple is invalid")
        return
    if event is ReferenceTransition.V2_TERMINAL_RETIRE:
        validate_v2_terminal_retire_predecessor(previous)
        if not (
            after["reference_lifecycle"] == "PREPARED"
            and after["v1_state"] == "NONE"
            and after["v2_state"] == "V2_ABSENT"
            and after["v2_lease_identity_sha256"] is None
            and after["v2_terminal_history_sha256"] == before["v2_terminal_history_sha256"]
        ):
            raise ValueError("V2 terminal retirement result tuple is invalid")
        return
    if event is ReferenceTransition.V1_TERMINAL_RETIRE:
        if not (
            before["reference_lifecycle"] == "PREPARED"
            and before["retained_object"] == "PUBLISHED"
            and before["v1_state"] in {state.value for state in _V1_TERMINALS}
            and before["v1_lease_identity_sha256"] is not None
            and before["v1_live_handle_count"] == 0
            and before["v1_terminal_history_sha256"] is not None
            and before["v2_state"] == "V2_ABSENT"
            and before["v2_live_handle_count"] == 0
            and before["revoke_or_expiry_intent"] == "ABSENT"
            and before["revoke_or_expiry_event_sha256"] is None
        ):
            raise ValueError("V1 terminal retirement predecessor is invalid")
        if (
            after["reference_lifecycle"] != "PREPARED"
            or after["retained_object"] != "PUBLISHED"
            or after["v1_state"] != "NONE"
            or after["v1_lease_identity_sha256"] is not None
            or after["v1_live_handle_count"] != 0
            or after["v1_terminal_history_sha256"]
            != before["v1_terminal_history_sha256"]
            or after["v2_state"] != "V2_ABSENT"
            or after["v2_lease_identity_sha256"] is not None
            or after["v2_live_handle_count"] != 0
            or after["revoke_or_expiry_intent"] != "ABSENT"
            or after["revoke_or_expiry_event_sha256"] is not None
        ):
            raise ValueError("V1 terminal retirement result is invalid")
        return
    if event is ReferenceTransition.REVOKE_PENDING:
        active_v1 = before["v1_state"] in {state.value for state in _V1_ACTIVE}
        active_v2 = before["v2_state"] in {state.value for state in _V2_ACTIVE}
        if (
            lifecycle_pair != ("PREPARED", "REVOKE_PENDING")
            or active_v1 == active_v2
            or before["v1_state"] != after["v1_state"]
            or before["v1_lease_identity_sha256"] != after["v1_lease_identity_sha256"]
            or before["v2_state"] != after["v2_state"]
            or before["v2_lease_identity_sha256"] != after["v2_lease_identity_sha256"]
            or after["revoke_or_expiry_intent"] == "ABSENT"
            or after["revoke_or_expiry_event_sha256"] is None
        ):
            raise ValueError("revoke-pending one-winner edge is invalid")
        return
    if event is ReferenceTransition.REVOKE_DIRECT:
        idle = before["v1_state"] == "NONE" and before["v2_state"] == "V2_ABSENT"
        v2_issued = before["v1_state"] == "NONE" and before["v2_state"] == "ISSUED"
        v1_issued = before["v1_state"] == "ISSUED" and before["v2_state"] == "V2_ABSENT"
        if lifecycle_pair != ("PREPARED", "REVOKED") or not (idle or v2_issued or v1_issued):
            raise ValueError("direct revoke edge is invalid")
        if after["revoke_or_expiry_intent"] == "ABSENT" or after["revoke_or_expiry_event_sha256"] is None:
            raise ValueError("direct revoke lacks exact intent/event")
        if v2_issued and (after["v2_state"] != "BURNED" or after["v2_lease_identity_sha256"] != before["v2_lease_identity_sha256"] or after["v2_terminal_history_sha256"] is None):
            raise ValueError("issued V2 direct revoke must preserve exact burn history")
        if idle and after["v2_state"] != "V2_ABSENT":
            raise ValueError("idle direct revoke cannot invent a V2 terminal")
        if v1_issued and (after["v1_state"] != "NONE" or after["v1_terminal_history_sha256"] is None):
            raise ValueError("legacy V1 direct revoke must close and preserve history")
        return
    if event is ReferenceTransition.V1_REVOKE_FINALIZE:
        if lifecycle_pair != ("REVOKE_PENDING", "REVOKED"):
            raise ValueError("V1 finalize lifecycle edge is invalid")
        validate_v1_finalize_predecessor(previous)
        if (
            after["v1_state"] != "NONE"
            or after["v1_lease_identity_sha256"] is not None
            or after["v2_state"] != "V2_ABSENT"
            or after["v1_terminal_history_sha256"] != before["v1_terminal_history_sha256"]
        ):
            raise ValueError("V1 finalize must retire current lease identities")
        return
    if event in {ReferenceTransition.V2_REVOKE_FINALIZE, ReferenceTransition.V2_TERMINAL_REVOKE_FINALIZE}:
        expected_before_lifecycle = "REVOKE_PENDING" if event is ReferenceTransition.V2_REVOKE_FINALIZE else "PREPARED"
        if (
            lifecycle_pair != (expected_before_lifecycle, "REVOKED")
            or before["v1_state"] != "NONE"
            or before["v2_state"] not in {state.value for state in _V2_TERMINALS}
            or before["v2_live_handle_count"] != 0
            or before["v2_terminal_history_sha256"] is None
            or after["v2_state"] != "V2_ABSENT"
            or after["v2_lease_identity_sha256"] is not None
            or after["v2_terminal_history_sha256"] != before["v2_terminal_history_sha256"]
            or after["revoke_or_expiry_intent"] == "ABSENT"
        ):
            raise ValueError("V2 terminal revoke-finalize edge is invalid")
        return
    if event is ReferenceTransition.PURGE_BEGIN:
        allowed = {"REVOKED", "PREPARE_FAILED_RETAINED", "PURGE_NOT_CONFIRMED"}
        if (
            lifecycle_pair != (before["reference_lifecycle"], "PURGE_PENDING")
            or before["reference_lifecycle"] not in allowed
            or before["retained_object"] == "FOREIGN_PRESERVED"
            or after["purge_human_action_receipt_sha256"] is None
            or (
                before["retained_object"] in {"RECOVERABLE_RETAINED", "RECONCILIATION_REQUIRED"}
                and after["ownership_recovery_readback_sha256"] is None
            )
        ):
            raise ValueError("purge begin predecessor is not exact-owned/recoverable")
        return
    if event is ReferenceTransition.PURGE_SUCCESS:
        if (
            lifecycle_pair != ("PURGE_PENDING", "PURGED")
            or after["retained_object"] != "PURGED"
            or after["purge_human_action_receipt_sha256"]
            != before["purge_human_action_receipt_sha256"]
            or after["ownership_recovery_readback_sha256"]
            != before["ownership_recovery_readback_sha256"]
        ):
            raise ValueError("purge success edge is invalid")
        return
    if event is ReferenceTransition.PURGE_NOT_CONFIRMED:
        if (
            lifecycle_pair != ("PURGE_PENDING", "PURGE_NOT_CONFIRMED")
            or after["purge_human_action_receipt_sha256"]
            != before["purge_human_action_receipt_sha256"]
            or after["ownership_recovery_readback_sha256"]
            != before["ownership_recovery_readback_sha256"]
        ):
            raise ValueError("purge-not-confirmed edge is invalid")
        return
    raise ValueError("reference transition event is outside the closed edge table")


def _parse_optional_readback_joint(
    value: Mapping[str, Any],
) -> tuple[
    ReferenceLifecycle,
    RetainedObject,
    CapabilityLeaseV1Current,
    int,
    CapabilityLeaseV2Current,
    int,
    RevokeExpiryIntent,
] | None:
    names = (
        "result_lifecycle", "result_retained_object", "result_v1_state",
        "result_v1_handle_count", "result_v2_state", "result_v2_handle_count",
        "result_revoke_or_expiry_intent",
    )
    if all(value[name] is None for name in names):
        for name in (
            "result_v1_lease_identity_sha256", "result_v1_terminal_history_sha256",
            "result_v2_lease_identity_sha256", "result_v2_terminal_history_sha256",
            "result_revoke_or_expiry_event_sha256",
        ):
            if value[name] is not None:
                raise ValueError("unknown result joint tuple cannot retain partial lease evidence")
        return None
    if any(value[name] is None for name in names):
        raise ValueError("result joint tuple is partial")
    lifecycle = _enum(ReferenceLifecycle, value["result_lifecycle"], "result_lifecycle")
    retained = _enum(RetainedObject, value["result_retained_object"], "result_retained_object")
    v1 = _enum(CapabilityLeaseV1Current, value["result_v1_state"], "result_v1_state")
    v2 = _enum(CapabilityLeaseV2Current, value["result_v2_state"], "result_v2_state")
    intent = _enum(RevokeExpiryIntent, value["result_revoke_or_expiry_intent"], "result_revoke_or_expiry_intent")
    v1_count = _bounded_int(value["result_v1_handle_count"], "result_v1_handle_count", 0, 1)
    v2_count = _bounded_int(value["result_v2_handle_count"], "result_v2_handle_count", 0, 4)
    _validate_joint_tuple(lifecycle, retained, v1, v1_count, v2, v2_count, intent)  # type: ignore[arg-type]
    v1_identity = _digest(value["result_v1_lease_identity_sha256"], "result_v1_lease_identity_sha256", nullable=True)
    v2_identity = _digest(value["result_v2_lease_identity_sha256"], "result_v2_lease_identity_sha256", nullable=True)
    v1_history = _digest(value["result_v1_terminal_history_sha256"], "result_v1_terminal_history_sha256", nullable=True)
    v2_history = _digest(value["result_v2_terminal_history_sha256"], "result_v2_terminal_history_sha256", nullable=True)
    event = _digest(value["result_revoke_or_expiry_event_sha256"], "result_revoke_or_expiry_event_sha256", nullable=True)
    if (v1 is CapabilityLeaseV1Current.NONE) != (v1_identity is None):
        raise ValueError("result V1 lease identity/state mismatch")
    if (v2 is CapabilityLeaseV2Current.V2_ABSENT) != (v2_identity is None):
        raise ValueError("result V2 lease identity/state mismatch")
    if v1 in _V1_TERMINALS and v1_history is None:
        raise ValueError("result V1 terminal state lacks immutable history")
    if v2 in _V2_TERMINALS and v2_history is None:
        raise ValueError("result V2 terminal state lacks immutable history")
    if (intent is RevokeExpiryIntent.ABSENT) != (event is None):
        raise ValueError("result revoke/expiry intent event mismatch")
    return lifecycle, retained, v1, v1_count, v2, v2_count, intent  # type: ignore[return-value]


@dataclass(frozen=True, slots=True, init=False)
class ReferenceV2IssueOrRevokeReadback:
    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("V2 issue readback must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        semantic_operation_key: str,
        request_sha256: str,
        outcome: V2IssueOrRevokeOutcome,
        expected_fence_revision: int,
        expected_fence_sha256: str,
        predecessor_snapshot_sha256: str,
        expected_v1_terminal_history_sha256: str | None,
        expected_v2_terminal_history_sha256: str | None,
        result_fence_revision: int | None,
        result_fence_sha256: str | None,
        result_snapshot_sha256: str | None,
        committed_event_sha256: str | None,
        trusted_time_receipt_sha256: str,
        broker_domain_sha256: str,
        broker_process_identity_sha256: str,
        broker_session_sha256: str,
        product_build_sha256: str,
        broker_protocol_version: str,
        result_lifecycle: ReferenceLifecycle | None,
        result_retained_object: RetainedObject | None,
        result_v1_state: CapabilityLeaseV1Current | None,
        result_v1_lease_identity_sha256: str | None,
        result_v1_handle_count: int | None,
        result_v1_terminal_history_sha256: str | None,
        result_v2_state: CapabilityLeaseV2Current | None,
        result_v2_lease_identity_sha256: str | None,
        result_v2_handle_count: int | None,
        result_v2_terminal_history_sha256: str | None,
        result_revoke_or_expiry_intent: RevokeExpiryIntent | None,
        result_revoke_or_expiry_event_sha256: str | None,
        live_capability_delivery_acknowledged: bool | None,
        request_issuance_effect: EffectTruth,
        request_live_handle_effect: EffectTruth,
        readback_at: str,
    ) -> "ReferenceV2IssueOrRevokeReadback":
        body: dict[str, Any] = {
            "contract_version": V2_ISSUE_READBACK_CONTRACT_VERSION,
            "record_type": "ReferenceV2IssueOrRevokeReadback",
            "operation_id": operation_id,
            "semantic_operation_key": semantic_operation_key,
            "request_sha256": request_sha256,
            "outcome": outcome.value if isinstance(outcome, V2IssueOrRevokeOutcome) else outcome,
            "expected_fence_revision": expected_fence_revision,
            "expected_fence_sha256": expected_fence_sha256,
            "predecessor_snapshot_sha256": predecessor_snapshot_sha256,
            "expected_v1_terminal_history_sha256": expected_v1_terminal_history_sha256,
            "expected_v2_terminal_history_sha256": expected_v2_terminal_history_sha256,
            "result_fence_revision": result_fence_revision,
            "result_fence_sha256": result_fence_sha256,
            "result_snapshot_sha256": result_snapshot_sha256,
            "committed_event_sha256": committed_event_sha256,
            "trusted_time_receipt_sha256": trusted_time_receipt_sha256,
            "broker_domain_sha256": broker_domain_sha256,
            "broker_process_identity_sha256": broker_process_identity_sha256,
            "broker_session_sha256": broker_session_sha256,
            "product_build_sha256": product_build_sha256,
            "broker_protocol_version": broker_protocol_version,
            "result_lifecycle": result_lifecycle.value if isinstance(result_lifecycle, ReferenceLifecycle) else result_lifecycle,
            "result_retained_object": result_retained_object.value if isinstance(result_retained_object, RetainedObject) else result_retained_object,
            "result_v1_state": result_v1_state.value if isinstance(result_v1_state, CapabilityLeaseV1Current) else result_v1_state,
            "result_v1_lease_identity_sha256": result_v1_lease_identity_sha256,
            "result_v1_handle_count": result_v1_handle_count,
            "result_v1_terminal_history_sha256": result_v1_terminal_history_sha256,
            "result_v2_state": result_v2_state.value if isinstance(result_v2_state, CapabilityLeaseV2Current) else result_v2_state,
            "result_v2_lease_identity_sha256": result_v2_lease_identity_sha256,
            "result_v2_handle_count": result_v2_handle_count,
            "result_v2_terminal_history_sha256": result_v2_terminal_history_sha256,
            "result_revoke_or_expiry_intent": result_revoke_or_expiry_intent.value if isinstance(result_revoke_or_expiry_intent, RevokeExpiryIntent) else result_revoke_or_expiry_intent,
            "result_revoke_or_expiry_event_sha256": result_revoke_or_expiry_event_sha256,
            "live_capability_delivery_acknowledged": live_capability_delivery_acknowledged,
            "request_issuance_effect": request_issuance_effect.value if isinstance(request_issuance_effect, EffectTruth) else request_issuance_effect,
            "request_live_handle_effect": request_live_handle_effect.value if isinstance(request_live_handle_effect, EffectTruth) else request_live_handle_effect,
            "automatic_retry_started": False,
            "serialized_capability_present": False,
            "readback_at": readback_at,
            **dict(_FIXTURE_READBACK_BOUNDARY),
            **dict(_FALSE_EFFECT_FLAGS),
        }
        body["issue_readback_sha256"] = sha256_bytes(
            _V2_ISSUE_READBACK_DOMAIN + canonical_json_bytes(body)
        )
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReferenceV2IssueOrRevokeReadback":
        fields = {
            "contract_version", "record_type", "operation_id", "semantic_operation_key",
            "request_sha256", "outcome", "expected_fence_revision", "expected_fence_sha256",
            "predecessor_snapshot_sha256", "expected_v1_terminal_history_sha256",
            "expected_v2_terminal_history_sha256", "result_fence_revision", "result_fence_sha256",
            "result_snapshot_sha256", "committed_event_sha256", "trusted_time_receipt_sha256",
            "broker_domain_sha256", "broker_process_identity_sha256", "broker_session_sha256",
            "product_build_sha256", "broker_protocol_version", "result_lifecycle",
            "result_retained_object", "result_v1_state", "result_v1_lease_identity_sha256",
            "result_v1_handle_count", "result_v1_terminal_history_sha256", "result_v2_state",
            "result_v2_lease_identity_sha256", "result_v2_handle_count",
            "result_v2_terminal_history_sha256", "result_revoke_or_expiry_intent",
            "result_revoke_or_expiry_event_sha256", "live_capability_delivery_acknowledged",
            "request_issuance_effect", "request_live_handle_effect",
            "automatic_retry_started", "serialized_capability_present", "readback_at",
            *set(_FIXTURE_READBACK_BOUNDARY), *set(_FALSE_EFFECT_FLAGS),
            "issue_readback_sha256",
        }
        _exact(value, fields, "ReferenceV2IssueOrRevokeReadback")
        if value["contract_version"] != V2_ISSUE_READBACK_CONTRACT_VERSION or value["record_type"] != "ReferenceV2IssueOrRevokeReadback":
            raise ValueError("V2 issue readback identity/version is invalid")
        _identifier(value["operation_id"], "operation_id")
        _identifier(value["semantic_operation_key"], "semantic_operation_key")
        _identifier(value["broker_protocol_version"], "broker_protocol_version")
        for name in (
            "request_sha256", "expected_fence_sha256", "predecessor_snapshot_sha256",
            "trusted_time_receipt_sha256", "broker_domain_sha256",
            "broker_process_identity_sha256", "broker_session_sha256", "product_build_sha256",
        ):
            _digest(value[name], name)
        for name in (
            "expected_v1_terminal_history_sha256",
            "expected_v2_terminal_history_sha256",
        ):
            _digest(value[name], name, nullable=True)
        expected_revision = _positive(value["expected_fence_revision"], "expected_fence_revision")
        result_revision = None if value["result_fence_revision"] is None else _positive(value["result_fence_revision"], "result_fence_revision")
        result_fence = _digest(value["result_fence_sha256"], "result_fence_sha256", nullable=True)
        result_snapshot = _digest(value["result_snapshot_sha256"], "result_snapshot_sha256", nullable=True)
        event = _digest(value["committed_event_sha256"], "committed_event_sha256", nullable=True)
        outcome = _enum(V2IssueOrRevokeOutcome, value["outcome"], "outcome")
        joint = _parse_optional_readback_joint(value)
        ack = value["live_capability_delivery_acknowledged"]
        if ack is not None and not isinstance(ack, bool):
            raise ValueError("delivery acknowledgement must be boolean or null")
        issuance_effect = _enum(EffectTruth, value["request_issuance_effect"], "request_issuance_effect")
        handle_effect = _enum(EffectTruth, value["request_live_handle_effect"], "request_live_handle_effect")

        def committed_result() -> None:
            if (
                event is None
                or result_revision != expected_revision + 1
                or result_fence is None
                or result_snapshot is None
                or joint is None
            ):
                raise ValueError("committed V2 readback lacks exact next-generation result")

        if outcome is V2IssueOrRevokeOutcome.V2_ISSUE_COMMITTED_DELIVERY_ACKNOWLEDGED:
            committed_result()
            lifecycle, retained, v1, v1_count, v2, v2_count, intent = joint  # type: ignore[misc]
            if (
                ack is not True
                or lifecycle is not ReferenceLifecycle.PREPARED
                or retained is not RetainedObject.PUBLISHED
                or v1 is not CapabilityLeaseV1Current.NONE
                or v1_count != 0
                or value["result_v1_lease_identity_sha256"] is not None
                or v2 is not CapabilityLeaseV2Current.ISSUED
                or v2_count != 2
                or value["result_v2_lease_identity_sha256"] is None
                or value["result_v1_terminal_history_sha256"]
                != value["expected_v1_terminal_history_sha256"]
                or value["result_v2_terminal_history_sha256"]
                != value["expected_v2_terminal_history_sha256"]
                or intent is not RevokeExpiryIntent.ABSENT
                or issuance_effect is not EffectTruth.OBSERVED
                or handle_effect is not EffectTruth.OBSERVED
            ):
                raise ValueError("acknowledged V2 issue readback tuple is invalid")
        elif outcome is V2IssueOrRevokeOutcome.V2_ISSUE_COMMITTED_DELIVERY_NOT_CONFIRMED:
            committed_result()
            lifecycle, retained, v1, v1_count, v2, v2_count, intent = joint  # type: ignore[misc]
            if (
                ack is not False
                or lifecycle is not ReferenceLifecycle.PREPARED
                or retained is not RetainedObject.PUBLISHED
                or v1 is not CapabilityLeaseV1Current.NONE
                or v1_count != 0
                or v2 is not CapabilityLeaseV2Current.BURNED
                or v2_count != 0
                or value["result_v2_terminal_history_sha256"] is None
                or value["result_v2_terminal_history_sha256"]
                == value["expected_v2_terminal_history_sha256"]
                or value["result_v1_terminal_history_sha256"]
                != value["expected_v1_terminal_history_sha256"]
                or intent is not RevokeExpiryIntent.ABSENT
                or issuance_effect is not EffectTruth.OBSERVED
                or handle_effect is not EffectTruth.OBSERVED
            ):
                raise ValueError("undelivered V2 issue readback tuple is invalid")
        elif outcome in {V2IssueOrRevokeOutcome.REVOKE_COMMITTED, V2IssueOrRevokeOutcome.EXPIRY_COMMITTED}:
            committed_result()
            lifecycle, retained, v1, v1_count, v2, v2_count, intent = joint  # type: ignore[misc]
            expected_intent = RevokeExpiryIntent.EXPLICIT_REVOKE if outcome is V2IssueOrRevokeOutcome.REVOKE_COMMITTED else RevokeExpiryIntent.TRUSTED_TIME_EXPIRY
            if (
                ack is not None
                or lifecycle is not ReferenceLifecycle.REVOKED
                or retained is not RetainedObject.PUBLISHED
                or v1 is not CapabilityLeaseV1Current.NONE
                or v1_count != 0
                or v2 is not CapabilityLeaseV2Current.V2_ABSENT
                or v2_count != 0
                or intent is not expected_intent
                or value["result_revoke_or_expiry_event_sha256"] is None
                or value["result_v1_terminal_history_sha256"]
                != value["expected_v1_terminal_history_sha256"]
                or value["result_v2_terminal_history_sha256"]
                != value["expected_v2_terminal_history_sha256"]
                or issuance_effect is not EffectTruth.ZERO
                or handle_effect is not EffectTruth.ZERO
            ):
                raise ValueError("revoke/expiry committed readback tuple is invalid")
        elif outcome is V2IssueOrRevokeOutcome.NO_COMMIT_STALE_PREDECESSOR:
            if (
                event is not None
                or ack is not None
                or joint is None
                or result_revision is None
                or result_fence is None
                or result_snapshot is None
                or (result_revision == expected_revision and result_fence == value["expected_fence_sha256"])
                or issuance_effect is not EffectTruth.ZERO
                or handle_effect is not EffectTruth.ZERO
            ):
                raise ValueError("stale no-commit cannot carry commit/delivery evidence")
        else:
            if (
                event is not None
                or ack is not None
                or joint is not None
                or result_revision is not None
                or result_fence is not None
                or result_snapshot is not None
                or issuance_effect is not EffectTruth.NOT_CONFIRMED
                or handle_effect is not EffectTruth.NOT_CONFIRMED
            ):
                raise ValueError("unknown V2 outcome must preserve exact NOT_CONFIRMED truth")
        if value["automatic_retry_started"] is not False or value["serialized_capability_present"] is not False:
            raise ValueError("V2 readback cannot replay or serialize capability authority")
        _timestamp(value["readback_at"], "readback_at")
        _validate_fixture_readback_boundary(value)
        _validate_false_flags(value)
        if value["issue_readback_sha256"] != _hash(
            _V2_ISSUE_READBACK_DOMAIN, value, "issue_readback_sha256"
        ):
            raise ValueError("V2 issue readback digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


def _validate_terminal_specific_proofs(
    value: Mapping[str, Any],
    terminal: TerminalKind,
) -> None:
    proof_fields = {
        TerminalKind.CONSUMED: "consumer_two_role_close_readback_sha256",
        TerminalKind.BURNED: "burn_abort_close_readback_sha256",
        TerminalKind.FAILED_CLOSED: "failed_closed_gate_proof_sha256",
    }
    required_proof = proof_fields[terminal]
    if value[required_proof] is None or any(
        value[name] is not None for name in proof_fields.values() if name != required_proof
    ):
        raise ValueError("terminal-specific proof set is incomplete or mixed")


@dataclass(frozen=True, slots=True, init=False)
class ReferenceTerminalRetireRequest:
    """Body-free terminal-retirement CAS request; never combines a V2 issue."""

    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("terminal retire request must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        semantic_operation_key: str,
        retired_operation_id: str,
        retired_semantic_operation_key: str,
        requested_action: TerminalRetireAction,
        terminal_kind: TerminalKind,
        retired_lease_identity_sha256: str,
        terminal_readback_sha256: str,
        consumer_two_role_close_readback_sha256: str | None,
        burn_abort_close_readback_sha256: str | None,
        failed_closed_gate_proof_sha256: str | None,
        expected_fence_revision: int,
        expected_fence_sha256: str,
        predecessor_snapshot_sha256: str,
        expected_terminal_history_event_sha256: str,
        expected_terminal_history_sha256: str,
        trusted_time_receipt_sha256: str,
        broker_domain_sha256: str,
        broker_process_identity_sha256: str,
        broker_session_sha256: str,
        product_build_sha256: str,
        broker_protocol_version: str,
    ) -> "ReferenceTerminalRetireRequest":
        body: dict[str, Any] = {
            "contract_version": TERMINAL_RETIRE_REQUEST_CONTRACT_VERSION,
            "record_type": "ReferenceTerminalRetireRequest",
            "operation_id": operation_id,
            "semantic_operation_key": semantic_operation_key,
            "retired_operation_id": retired_operation_id,
            "retired_semantic_operation_key": retired_semantic_operation_key,
            "requested_action": requested_action.value if isinstance(requested_action, TerminalRetireAction) else requested_action,
            "terminal_kind": terminal_kind.value if isinstance(terminal_kind, TerminalKind) else terminal_kind,
            "retired_lease_identity_sha256": retired_lease_identity_sha256,
            "terminal_readback_sha256": terminal_readback_sha256,
            "consumer_two_role_close_readback_sha256": consumer_two_role_close_readback_sha256,
            "burn_abort_close_readback_sha256": burn_abort_close_readback_sha256,
            "failed_closed_gate_proof_sha256": failed_closed_gate_proof_sha256,
            "expected_fence_revision": expected_fence_revision,
            "expected_fence_sha256": expected_fence_sha256,
            "predecessor_snapshot_sha256": predecessor_snapshot_sha256,
            "expected_terminal_history_event_sha256": expected_terminal_history_event_sha256,
            "expected_terminal_history_sha256": expected_terminal_history_sha256,
            "trusted_time_receipt_sha256": trusted_time_receipt_sha256,
            "broker_domain_sha256": broker_domain_sha256,
            "broker_process_identity_sha256": broker_process_identity_sha256,
            "broker_session_sha256": broker_session_sha256,
            "product_build_sha256": product_build_sha256,
            "broker_protocol_version": broker_protocol_version,
            "new_issue_combined": False,
            "automatic_retry_allowed": False,
            **dict(_FIXTURE_READBACK_BOUNDARY),
            **dict(_FALSE_EFFECT_FLAGS),
        }
        body["terminal_retire_request_sha256"] = sha256_bytes(
            _TERMINAL_RETIRE_REQUEST_DOMAIN + canonical_json_bytes(body)
        )
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReferenceTerminalRetireRequest":
        fields = {
            "contract_version", "record_type", "operation_id", "semantic_operation_key",
            "retired_operation_id", "retired_semantic_operation_key", "requested_action",
            "terminal_kind", "retired_lease_identity_sha256", "terminal_readback_sha256",
            "consumer_two_role_close_readback_sha256", "burn_abort_close_readback_sha256",
            "failed_closed_gate_proof_sha256", "expected_fence_revision",
            "expected_fence_sha256", "predecessor_snapshot_sha256",
            "expected_terminal_history_event_sha256", "expected_terminal_history_sha256",
            "trusted_time_receipt_sha256", "broker_domain_sha256",
            "broker_process_identity_sha256", "broker_session_sha256", "product_build_sha256",
            "broker_protocol_version", "new_issue_combined", "automatic_retry_allowed",
            *set(_FIXTURE_READBACK_BOUNDARY), *set(_FALSE_EFFECT_FLAGS),
            "terminal_retire_request_sha256",
        }
        _exact(value, fields, "ReferenceTerminalRetireRequest")
        if (
            value["contract_version"] != TERMINAL_RETIRE_REQUEST_CONTRACT_VERSION
            or value["record_type"] != "ReferenceTerminalRetireRequest"
        ):
            raise ValueError("terminal retire request identity/version is invalid")
        for name in (
            "operation_id", "semantic_operation_key", "retired_operation_id",
            "retired_semantic_operation_key", "broker_protocol_version",
        ):
            _identifier(value[name], name)
        if (
            value["operation_id"] == value["retired_operation_id"]
            or value["semantic_operation_key"] == value["retired_semantic_operation_key"]
        ):
            raise ValueError("terminal retirement and retired operation identities must be distinct")
        terminal = _enum(TerminalKind, value["terminal_kind"], "terminal_kind")
        _enum(TerminalRetireAction, value["requested_action"], "requested_action")
        for name in (
            "retired_lease_identity_sha256", "terminal_readback_sha256",
            "expected_fence_sha256", "predecessor_snapshot_sha256",
            "expected_terminal_history_event_sha256", "expected_terminal_history_sha256",
            "trusted_time_receipt_sha256", "broker_domain_sha256",
            "broker_process_identity_sha256", "broker_session_sha256", "product_build_sha256",
        ):
            _digest(value[name], name)
        for name in (
            "consumer_two_role_close_readback_sha256", "burn_abort_close_readback_sha256",
            "failed_closed_gate_proof_sha256",
        ):
            _digest(value[name], name, nullable=True)
        _positive(value["expected_fence_revision"], "expected_fence_revision")
        _validate_terminal_specific_proofs(value, terminal)  # type: ignore[arg-type]
        if value["new_issue_combined"] is not False or value["automatic_retry_allowed"] is not False:
            raise ValueError("terminal retire request cannot combine issue or automatic retry")
        _validate_fixture_readback_boundary(value)
        _validate_false_flags(value)
        if value["terminal_retire_request_sha256"] != _hash(
            _TERMINAL_RETIRE_REQUEST_DOMAIN, value, "terminal_retire_request_sha256"
        ):
            raise ValueError("terminal retire request digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


@dataclass(frozen=True, slots=True, init=False)
class ReferenceTerminalRetireReadback:
    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("terminal retire readback must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        request: ReferenceTerminalRetireRequest,
        result_fence_revision: int | None,
        result_fence_sha256: str | None,
        result_snapshot_sha256: str | None,
        committed_event_sha256: str | None,
        terminal_history_event_sha256: str | None,
        terminal_history_sha256: str | None,
        terminal_history_disposition: TerminalHistoryDisposition,
        history_append_count: int,
        outcome: TerminalRetireOutcome,
        result_lifecycle: ReferenceLifecycle | None,
        result_retained_object: RetainedObject | None,
        result_v1_state: CapabilityLeaseV1Current | None,
        result_v1_lease_identity_sha256: str | None,
        result_v1_handle_count: int | None,
        result_v1_terminal_history_sha256: str | None,
        result_v2_state: CapabilityLeaseV2Current | None,
        result_v2_lease_identity_sha256: str | None,
        result_v2_handle_count: int | None,
        result_v2_terminal_history_sha256: str | None,
        result_revoke_or_expiry_intent: RevokeExpiryIntent | None,
        result_revoke_or_expiry_event_sha256: str | None,
        body_effect: EffectTruth,
        model_effect: EffectTruth,
        readback_at: str,
    ) -> "ReferenceTerminalRetireReadback":
        if not isinstance(request, ReferenceTerminalRetireRequest):
            raise TypeError("request must be ReferenceTerminalRetireRequest")
        request_data = request.to_dict()
        body: dict[str, Any] = {
            "contract_version": TERMINAL_RETIRE_READBACK_CONTRACT_VERSION,
            "record_type": "ReferenceTerminalRetireReadback",
            "operation_id": request_data["operation_id"],
            "semantic_operation_key": request_data["semantic_operation_key"],
            "retired_operation_id": request_data["retired_operation_id"],
            "retired_semantic_operation_key": request_data["retired_semantic_operation_key"],
            "request_sha256": request_data["terminal_retire_request_sha256"],
            "requested_action": request_data["requested_action"],
            "terminal_kind": request_data["terminal_kind"],
            "retired_lease_identity_sha256": request_data["retired_lease_identity_sha256"],
            "terminal_readback_sha256": request_data["terminal_readback_sha256"],
            "consumer_two_role_close_readback_sha256": request_data["consumer_two_role_close_readback_sha256"],
            "burn_abort_close_readback_sha256": request_data["burn_abort_close_readback_sha256"],
            "failed_closed_gate_proof_sha256": request_data["failed_closed_gate_proof_sha256"],
            "expected_fence_revision": request_data["expected_fence_revision"],
            "expected_fence_sha256": request_data["expected_fence_sha256"],
            "predecessor_snapshot_sha256": request_data["predecessor_snapshot_sha256"],
            "result_fence_revision": result_fence_revision,
            "result_fence_sha256": result_fence_sha256,
            "result_snapshot_sha256": result_snapshot_sha256,
            "committed_event_sha256": committed_event_sha256,
            "terminal_history_event_sha256": terminal_history_event_sha256,
            "terminal_history_sha256": terminal_history_sha256,
            "terminal_history_disposition": terminal_history_disposition.value if isinstance(terminal_history_disposition, TerminalHistoryDisposition) else terminal_history_disposition,
            "history_append_count": history_append_count,
            "outcome": outcome.value if isinstance(outcome, TerminalRetireOutcome) else outcome,
            "trusted_time_receipt_sha256": request_data["trusted_time_receipt_sha256"],
            "broker_domain_sha256": request_data["broker_domain_sha256"],
            "broker_process_identity_sha256": request_data["broker_process_identity_sha256"],
            "broker_session_sha256": request_data["broker_session_sha256"],
            "product_build_sha256": request_data["product_build_sha256"],
            "broker_protocol_version": request_data["broker_protocol_version"],
            "result_lifecycle": result_lifecycle.value if isinstance(result_lifecycle, ReferenceLifecycle) else result_lifecycle,
            "result_retained_object": result_retained_object.value if isinstance(result_retained_object, RetainedObject) else result_retained_object,
            "result_v1_state": result_v1_state.value if isinstance(result_v1_state, CapabilityLeaseV1Current) else result_v1_state,
            "result_v1_lease_identity_sha256": result_v1_lease_identity_sha256,
            "result_v1_handle_count": result_v1_handle_count,
            "result_v1_terminal_history_sha256": result_v1_terminal_history_sha256,
            "result_v2_state": result_v2_state.value if isinstance(result_v2_state, CapabilityLeaseV2Current) else result_v2_state,
            "result_v2_lease_identity_sha256": result_v2_lease_identity_sha256,
            "result_v2_handle_count": result_v2_handle_count,
            "result_v2_terminal_history_sha256": result_v2_terminal_history_sha256,
            "result_revoke_or_expiry_intent": result_revoke_or_expiry_intent.value if isinstance(result_revoke_or_expiry_intent, RevokeExpiryIntent) else result_revoke_or_expiry_intent,
            "result_revoke_or_expiry_event_sha256": result_revoke_or_expiry_event_sha256,
            "body_effect": body_effect.value if isinstance(body_effect, EffectTruth) else body_effect,
            "model_effect": model_effect.value if isinstance(model_effect, EffectTruth) else model_effect,
            "new_lease_issued": False,
            "history_duplicate_count": 0,
            "automatic_retry_started": False,
            "readback_at": readback_at,
            **dict(_FIXTURE_READBACK_BOUNDARY),
            **dict(_FALSE_EFFECT_FLAGS),
        }
        body["terminal_retire_readback_sha256"] = sha256_bytes(
            _TERMINAL_RETIRE_DOMAIN + canonical_json_bytes(body)
        )
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReferenceTerminalRetireReadback":
        fields = {
            "contract_version", "record_type", "operation_id", "semantic_operation_key",
            "retired_operation_id", "retired_semantic_operation_key", "request_sha256",
            "requested_action", "terminal_kind", "retired_lease_identity_sha256",
            "terminal_readback_sha256", "consumer_two_role_close_readback_sha256",
            "burn_abort_close_readback_sha256", "failed_closed_gate_proof_sha256",
            "expected_fence_revision", "expected_fence_sha256", "predecessor_snapshot_sha256",
            "result_fence_revision", "result_fence_sha256", "result_snapshot_sha256",
            "committed_event_sha256", "terminal_history_event_sha256", "terminal_history_sha256",
            "terminal_history_disposition", "history_append_count", "outcome",
            "trusted_time_receipt_sha256", "broker_domain_sha256", "broker_process_identity_sha256",
            "broker_session_sha256", "product_build_sha256", "broker_protocol_version",
            "result_lifecycle", "result_retained_object", "result_v1_state",
            "result_v1_lease_identity_sha256", "result_v1_handle_count",
            "result_v1_terminal_history_sha256", "result_v2_state",
            "result_v2_lease_identity_sha256", "result_v2_handle_count",
            "result_v2_terminal_history_sha256", "result_revoke_or_expiry_intent",
            "result_revoke_or_expiry_event_sha256", "body_effect", "model_effect",
            "new_lease_issued", "history_duplicate_count", "automatic_retry_started",
            "readback_at", *set(_FIXTURE_READBACK_BOUNDARY), *set(_FALSE_EFFECT_FLAGS),
            "terminal_retire_readback_sha256",
        }
        _exact(value, fields, "ReferenceTerminalRetireReadback")
        if value["contract_version"] != TERMINAL_RETIRE_READBACK_CONTRACT_VERSION or value["record_type"] != "ReferenceTerminalRetireReadback":
            raise ValueError("terminal retire readback identity/version is invalid")
        for name in (
            "operation_id", "semantic_operation_key", "retired_operation_id",
            "retired_semantic_operation_key", "broker_protocol_version",
        ):
            _identifier(value[name], name)
        if (
            value["operation_id"] == value["retired_operation_id"]
            or value["semantic_operation_key"] == value["retired_semantic_operation_key"]
        ):
            raise ValueError("terminal retirement and retired operation identities must be distinct")
        action = _enum(TerminalRetireAction, value["requested_action"], "requested_action")
        terminal = _enum(TerminalKind, value["terminal_kind"], "terminal_kind")
        outcome = _enum(TerminalRetireOutcome, value["outcome"], "outcome")
        for name in (
            "request_sha256", "retired_lease_identity_sha256", "terminal_readback_sha256",
            "expected_fence_sha256", "predecessor_snapshot_sha256",
            "trusted_time_receipt_sha256", "broker_domain_sha256",
            "broker_process_identity_sha256", "broker_session_sha256", "product_build_sha256",
        ):
            _digest(value[name], name)
        for name in (
            "consumer_two_role_close_readback_sha256", "burn_abort_close_readback_sha256",
            "failed_closed_gate_proof_sha256", "result_fence_sha256", "result_snapshot_sha256",
            "committed_event_sha256", "terminal_history_event_sha256", "terminal_history_sha256",
        ):
            _digest(value[name], name, nullable=True)
        expected_revision = _positive(value["expected_fence_revision"], "expected_fence_revision")
        result_revision = None if value["result_fence_revision"] is None else _positive(value["result_fence_revision"], "result_fence_revision")
        disposition = _enum(TerminalHistoryDisposition, value["terminal_history_disposition"], "terminal_history_disposition")
        append_count = _bounded_int(value["history_append_count"], "history_append_count", 0, 1)
        if (disposition is TerminalHistoryDisposition.SEALED_ONCE) != (append_count == 1):
            raise ValueError("terminal history disposition/append count mismatch")
        if disposition is TerminalHistoryDisposition.NOT_CONFIRMED and append_count != 0:
            raise ValueError("unknown terminal history cannot claim append")
        _validate_terminal_specific_proofs(value, terminal)  # type: ignore[arg-type]
        body_effect = _enum(EffectTruth, value["body_effect"], "body_effect")
        model_effect = _enum(EffectTruth, value["model_effect"], "model_effect")
        if terminal is TerminalKind.CONSUMED and (body_effect is not EffectTruth.OBSERVED or model_effect is not EffectTruth.OBSERVED):
            raise ValueError("CONSUMED terminal requires exact observed body/model effect")
        if terminal is TerminalKind.FAILED_CLOSED and (body_effect is not EffectTruth.NOT_CONFIRMED or model_effect is not EffectTruth.NOT_CONFIRMED):
            raise ValueError("FAILED_CLOSED terminal must preserve effect NOT_CONFIRMED")
        joint = _parse_optional_readback_joint(value)
        if (
            value["new_lease_issued"] is not False
            or type(value["history_duplicate_count"]) is not int
            or value["history_duplicate_count"] != 0
            or value["automatic_retry_started"] is not False
        ):
            raise ValueError("terminal retirement cannot issue/retry/duplicate history")
        terminal_success = {
            TerminalKind.CONSUMED: TerminalRetireOutcome.CONSUMED_RETIRED,
            TerminalKind.BURNED: TerminalRetireOutcome.BURNED_RETIRED,
            TerminalKind.FAILED_CLOSED: TerminalRetireOutcome.FAILED_CLOSED_RETIRED_NOT_CONFIRMED,
        }
        committed = {
            *terminal_success.values(),
            TerminalRetireOutcome.TERMINAL_REVOKE_COMMITTED,
            TerminalRetireOutcome.TERMINAL_EXPIRY_COMMITTED,
        }
        if outcome in committed:
            if (
                result_revision != expected_revision + 1
                or value["result_fence_sha256"] is None
                or value["result_snapshot_sha256"] is None
                or value["committed_event_sha256"] is None
                or value["terminal_history_event_sha256"] is None
                or value["terminal_history_sha256"] is None
                or disposition is TerminalHistoryDisposition.NOT_CONFIRMED
                or joint is None
            ):
                raise ValueError("committed terminal result lacks exact generation/history truth")
            lifecycle, retained, v1, v1_count, v2, v2_count, intent = joint
            if v1 is not CapabilityLeaseV1Current.NONE or v1_count != 0 or v2 is not CapabilityLeaseV2Current.V2_ABSENT or v2_count != 0 or retained is not RetainedObject.PUBLISHED:
                raise ValueError("committed terminal result current lease tuple is invalid")
            if value["result_v2_terminal_history_sha256"] != value["terminal_history_sha256"]:
                raise ValueError("committed terminal result history lineage mismatch")
            if outcome in terminal_success.values():
                if outcome is not terminal_success[terminal] or action is not TerminalRetireAction.RETIRE or lifecycle is not ReferenceLifecycle.PREPARED or intent is not RevokeExpiryIntent.ABSENT:
                    raise ValueError("terminal retirement outcome/action tuple mismatch")
            elif outcome is TerminalRetireOutcome.TERMINAL_REVOKE_COMMITTED:
                if action is not TerminalRetireAction.EXPLICIT_REVOKE or lifecycle is not ReferenceLifecycle.REVOKED or intent is not RevokeExpiryIntent.EXPLICIT_REVOKE:
                    raise ValueError("terminal revoke committed tuple mismatch")
            elif action is not TerminalRetireAction.TRUSTED_TIME_EXPIRY or lifecycle is not ReferenceLifecycle.REVOKED or intent is not RevokeExpiryIntent.TRUSTED_TIME_EXPIRY:
                raise ValueError("terminal expiry committed tuple mismatch")
        elif outcome is TerminalRetireOutcome.NO_COMMIT_TERMINAL_STILL_CURRENT:
            if (
                result_revision != expected_revision
                or value["result_fence_sha256"] != value["expected_fence_sha256"]
                or value["result_snapshot_sha256"] != value["predecessor_snapshot_sha256"]
                or value["committed_event_sha256"] is not None
                or value["terminal_history_event_sha256"] is None
                or disposition is not TerminalHistoryDisposition.EXACT_PRESENT
                or append_count != 0
                or joint is None
            ):
                raise ValueError("no-commit terminal readback lacks exact unchanged predecessor")
            lifecycle, retained, v1, v1_count, v2, v2_count, intent = joint
            if (
                lifecycle is not ReferenceLifecycle.PREPARED
                or retained is not RetainedObject.PUBLISHED
                or v1 is not CapabilityLeaseV1Current.NONE
                or v1_count != 0
                or v2.value != terminal.value
                or v2_count != 0
                or value["result_v2_lease_identity_sha256"] != value["retired_lease_identity_sha256"]
                or value["result_v2_terminal_history_sha256"] != value["terminal_history_sha256"]
                or intent is not RevokeExpiryIntent.ABSENT
            ):
                raise ValueError("terminal-still-current joint tuple mismatch")
        elif outcome is TerminalRetireOutcome.STALE_OTHER_COMMIT:
            if (
                joint is None
                or result_revision is None
                or value["result_fence_sha256"] is None
                or value["result_snapshot_sha256"] is None
                or value["committed_event_sha256"] is None
                or (result_revision == expected_revision and value["result_fence_sha256"] == value["expected_fence_sha256"])
                or append_count != 0
            ):
                raise ValueError("stale terminal readback lacks exact other-commit truth")
        elif (
            joint is not None
            or result_revision is not None
            or value["result_fence_sha256"] is not None
            or value["result_snapshot_sha256"] is not None
            or value["committed_event_sha256"] is not None
            or value["terminal_history_event_sha256"] is not None
            or value["terminal_history_sha256"] is not None
            or disposition is not TerminalHistoryDisposition.NOT_CONFIRMED
            or append_count != 0
        ):
            raise ValueError("unknown terminal outcome must preserve NOT_CONFIRMED truth")
        _timestamp(value["readback_at"], "readback_at")
        _validate_fixture_readback_boundary(value)
        _validate_false_flags(value)
        if value["terminal_retire_readback_sha256"] != _hash(
            _TERMINAL_RETIRE_DOMAIN, value, "terminal_retire_readback_sha256"
        ):
            raise ValueError("terminal retire readback digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


def validate_terminal_retire_transaction(
    request: ReferenceTerminalRetireRequest,
    predecessor: ReferenceDomainSnapshot,
    result: ReferenceDomainSnapshot | None,
    readback: ReferenceTerminalRetireReadback,
) -> None:
    """Cross-bind one typed retirement request, fence transition and readback."""

    if not isinstance(request, ReferenceTerminalRetireRequest):
        raise TypeError("request must be ReferenceTerminalRetireRequest")
    if not isinstance(predecessor, ReferenceDomainSnapshot):
        raise TypeError("predecessor must be ReferenceDomainSnapshot")
    if result is not None and not isinstance(result, ReferenceDomainSnapshot):
        raise TypeError("result must be ReferenceDomainSnapshot or None")
    if not isinstance(readback, ReferenceTerminalRetireReadback):
        raise TypeError("readback must be ReferenceTerminalRetireReadback")

    request_data = request.to_dict()
    before = predecessor.to_dict()
    receipt = readback.to_dict()
    request_to_readback = (
        "operation_id", "semantic_operation_key", "retired_operation_id",
        "retired_semantic_operation_key", "requested_action", "terminal_kind",
        "retired_lease_identity_sha256", "terminal_readback_sha256",
        "consumer_two_role_close_readback_sha256", "burn_abort_close_readback_sha256",
        "failed_closed_gate_proof_sha256", "expected_fence_revision",
        "expected_fence_sha256", "predecessor_snapshot_sha256",
        "trusted_time_receipt_sha256", "broker_domain_sha256",
        "broker_process_identity_sha256", "broker_session_sha256", "product_build_sha256",
        "broker_protocol_version",
    )
    if (
        receipt["request_sha256"] != request_data["terminal_retire_request_sha256"]
        or any(receipt[name] != request_data[name] for name in request_to_readback)
    ):
        raise ValueError("terminal retire request/readback lineage mismatch")

    validate_v2_terminal_retire_predecessor(predecessor)
    predecessor_bindings = {
        "predecessor_snapshot_sha256": "snapshot_sha256",
        "expected_fence_revision": "fence_revision",
        "expected_fence_sha256": "fence_sha256",
        "retired_operation_id": "current_operation_id",
        "retired_semantic_operation_key": "semantic_operation_key",
        "retired_lease_identity_sha256": "v2_lease_identity_sha256",
        "expected_terminal_history_sha256": "v2_terminal_history_sha256",
        "trusted_time_receipt_sha256": "trusted_time_receipt_sha256",
        "broker_domain_sha256": "broker_domain_sha256",
        "broker_process_identity_sha256": "broker_process_identity_sha256",
        "broker_session_sha256": "broker_session_sha256",
        "product_build_sha256": "product_build_sha256",
        "broker_protocol_version": "broker_protocol_version",
    }
    if any(request_data[left] != before[right] for left, right in predecessor_bindings.items()):
        raise ValueError("terminal retire request/predecessor fence lineage mismatch")
    if receipt["terminal_kind"] != before["v2_state"]:
        raise ValueError("terminal retire request/predecessor terminal kind mismatch")

    outcome = TerminalRetireOutcome(receipt["outcome"])
    if outcome is TerminalRetireOutcome.OUTCOME_NOT_CONFIRMED:
        if result is not None:
            raise ValueError("unknown terminal retirement cannot bind a result snapshot")
        return
    if result is None:
        raise ValueError("known terminal retirement outcome requires a typed result snapshot")

    after = result.to_dict()
    result_bindings = {
        "result_fence_revision": "fence_revision",
        "result_fence_sha256": "fence_sha256",
        "result_snapshot_sha256": "snapshot_sha256",
        "result_lifecycle": "reference_lifecycle",
        "result_retained_object": "retained_object",
        "result_v1_state": "v1_state",
        "result_v1_lease_identity_sha256": "v1_lease_identity_sha256",
        "result_v1_handle_count": "v1_live_handle_count",
        "result_v1_terminal_history_sha256": "v1_terminal_history_sha256",
        "result_v2_state": "v2_state",
        "result_v2_lease_identity_sha256": "v2_lease_identity_sha256",
        "result_v2_handle_count": "v2_live_handle_count",
        "result_v2_terminal_history_sha256": "v2_terminal_history_sha256",
        "result_revoke_or_expiry_intent": "revoke_or_expiry_intent",
        "result_revoke_or_expiry_event_sha256": "revoke_or_expiry_event_sha256",
    }
    if any(receipt[left] != after[right] for left, right in result_bindings.items()):
        raise ValueError("terminal retire readback/result snapshot tuple mismatch")
    for name in (
        "reference_id", "project_id", "project_manifest_revision_sha256", "voice_profile_id",
        "voice_profile_revision_sha256", "consent_current_evaluation_sha256",
        "route_selection_sha256", "reference_pair_sha256", "broker_domain_sha256",
        "broker_process_identity_sha256", "broker_session_sha256", "product_build_sha256",
        "broker_protocol_version", "trusted_time_domain_sha256",
    ):
        expected = request_data[name] if name in request_data else before[name]
        if after[name] != expected:
            raise ValueError(f"terminal retire result {name} mismatch")
    if (
        receipt["terminal_history_event_sha256"]
        != request_data["expected_terminal_history_event_sha256"]
        or receipt["terminal_history_sha256"]
        != request_data["expected_terminal_history_sha256"]
    ):
        raise ValueError("terminal retire history event/digest lineage mismatch")

    committed = {
        TerminalRetireOutcome.CONSUMED_RETIRED,
        TerminalRetireOutcome.BURNED_RETIRED,
        TerminalRetireOutcome.FAILED_CLOSED_RETIRED_NOT_CONFIRMED,
        TerminalRetireOutcome.TERMINAL_REVOKE_COMMITTED,
        TerminalRetireOutcome.TERMINAL_EXPIRY_COMMITTED,
    }
    if outcome in committed:
        if after["trusted_time_receipt_sha256"] != request_data["trusted_time_receipt_sha256"]:
            raise ValueError("terminal retire trusted-time result mismatch")
        if receipt["committed_event_sha256"] != after["committed_event_sha256"]:
            raise ValueError("terminal retire committed event/result mismatch")
        action = TerminalRetireAction(receipt["requested_action"])
        event = (
            ReferenceTransition.V2_TERMINAL_RETIRE
            if action is TerminalRetireAction.RETIRE
            else ReferenceTransition.V2_TERMINAL_REVOKE_FINALIZE
        )
        validate_reference_transition(predecessor, result, event)
        if (
            after["current_operation_id"] != request_data["operation_id"]
            or after["semantic_operation_key"] != request_data["semantic_operation_key"]
            or after["last_retired_operation_id"] != request_data["retired_operation_id"]
            or after["last_retired_semantic_operation_key"]
            != request_data["retired_semantic_operation_key"]
        ):
            raise ValueError("terminal retirement result fence operation identity mismatch")
    elif outcome is TerminalRetireOutcome.NO_COMMIT_TERMINAL_STILL_CURRENT:
        if after["snapshot_sha256"] != before["snapshot_sha256"]:
            raise ValueError("no-commit retirement result is not the exact predecessor")
    elif outcome is TerminalRetireOutcome.STALE_OTHER_COMMIT:
        if receipt["committed_event_sha256"] != after["committed_event_sha256"]:
            raise ValueError("stale-other retirement event/result mismatch")


@dataclass(frozen=True, slots=True, init=False)
class ReferenceV1RevokeFinalizeReadback:
    """R13 V1 finalize/reply-loss truth; never starts recovery or a new lease."""

    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("V1 finalize readback must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        semantic_operation_key: str,
        request_sha256: str,
        terminal_kind: TerminalKind | None,
        v1_lease_identity_sha256: str,
        terminal_readback_sha256: str | None,
        terminal_close_readback_sha256: str | None,
        failed_closed_gate_proof_sha256: str | None,
        revoke_or_expiry_intent: RevokeExpiryIntent,
        revoke_or_expiry_event_sha256: str,
        expected_fence_revision: int,
        expected_fence_sha256: str,
        predecessor_snapshot_sha256: str,
        result_fence_revision: int | None,
        result_fence_sha256: str | None,
        result_snapshot_sha256: str | None,
        committed_event_sha256: str | None,
        terminal_history_event_sha256: str | None,
        terminal_history_sha256: str | None,
        terminal_history_disposition: TerminalHistoryDisposition,
        history_append_count: int,
        outcome: V1RevokeFinalizeOutcome,
        trusted_time_receipt_sha256: str,
        broker_domain_sha256: str,
        broker_process_identity_sha256: str,
        broker_session_sha256: str,
        product_build_sha256: str,
        broker_protocol_version: str,
        result_lifecycle: ReferenceLifecycle | None,
        result_retained_object: RetainedObject | None,
        result_v1_state: CapabilityLeaseV1Current | None,
        result_v1_lease_identity_sha256: str | None,
        result_v1_handle_count: int | None,
        result_v1_terminal_history_sha256: str | None,
        result_v2_state: CapabilityLeaseV2Current | None,
        result_v2_lease_identity_sha256: str | None,
        result_v2_handle_count: int | None,
        result_v2_terminal_history_sha256: str | None,
        result_revoke_or_expiry_intent: RevokeExpiryIntent | None,
        result_revoke_or_expiry_event_sha256: str | None,
        body_effect: EffectTruth,
        model_effect: EffectTruth,
        readback_at: str,
    ) -> "ReferenceV1RevokeFinalizeReadback":
        body: dict[str, Any] = {
            "contract_version": V1_REVOKE_FINALIZE_READBACK_CONTRACT_VERSION,
            "record_type": "ReferenceV1RevokeFinalizeReadback",
            "operation_id": operation_id,
            "semantic_operation_key": semantic_operation_key,
            "request_sha256": request_sha256,
            "terminal_kind": terminal_kind.value if isinstance(terminal_kind, TerminalKind) else terminal_kind,
            "v1_lease_identity_sha256": v1_lease_identity_sha256,
            "terminal_readback_sha256": terminal_readback_sha256,
            "terminal_close_readback_sha256": terminal_close_readback_sha256,
            "failed_closed_gate_proof_sha256": failed_closed_gate_proof_sha256,
            "revoke_or_expiry_intent": revoke_or_expiry_intent.value if isinstance(revoke_or_expiry_intent, RevokeExpiryIntent) else revoke_or_expiry_intent,
            "revoke_or_expiry_event_sha256": revoke_or_expiry_event_sha256,
            "expected_fence_revision": expected_fence_revision,
            "expected_fence_sha256": expected_fence_sha256,
            "predecessor_snapshot_sha256": predecessor_snapshot_sha256,
            "result_fence_revision": result_fence_revision,
            "result_fence_sha256": result_fence_sha256,
            "result_snapshot_sha256": result_snapshot_sha256,
            "committed_event_sha256": committed_event_sha256,
            "terminal_history_event_sha256": terminal_history_event_sha256,
            "terminal_history_sha256": terminal_history_sha256,
            "terminal_history_disposition": terminal_history_disposition.value if isinstance(terminal_history_disposition, TerminalHistoryDisposition) else terminal_history_disposition,
            "history_append_count": history_append_count,
            "outcome": outcome.value if isinstance(outcome, V1RevokeFinalizeOutcome) else outcome,
            "trusted_time_receipt_sha256": trusted_time_receipt_sha256,
            "broker_domain_sha256": broker_domain_sha256,
            "broker_process_identity_sha256": broker_process_identity_sha256,
            "broker_session_sha256": broker_session_sha256,
            "product_build_sha256": product_build_sha256,
            "broker_protocol_version": broker_protocol_version,
            "result_lifecycle": result_lifecycle.value if isinstance(result_lifecycle, ReferenceLifecycle) else result_lifecycle,
            "result_retained_object": result_retained_object.value if isinstance(result_retained_object, RetainedObject) else result_retained_object,
            "result_v1_state": result_v1_state.value if isinstance(result_v1_state, CapabilityLeaseV1Current) else result_v1_state,
            "result_v1_lease_identity_sha256": result_v1_lease_identity_sha256,
            "result_v1_handle_count": result_v1_handle_count,
            "result_v1_terminal_history_sha256": result_v1_terminal_history_sha256,
            "result_v2_state": result_v2_state.value if isinstance(result_v2_state, CapabilityLeaseV2Current) else result_v2_state,
            "result_v2_lease_identity_sha256": result_v2_lease_identity_sha256,
            "result_v2_handle_count": result_v2_handle_count,
            "result_v2_terminal_history_sha256": result_v2_terminal_history_sha256,
            "result_revoke_or_expiry_intent": result_revoke_or_expiry_intent.value if isinstance(result_revoke_or_expiry_intent, RevokeExpiryIntent) else result_revoke_or_expiry_intent,
            "result_revoke_or_expiry_event_sha256": result_revoke_or_expiry_event_sha256,
            "body_effect": body_effect.value if isinstance(body_effect, EffectTruth) else body_effect,
            "model_effect": model_effect.value if isinstance(model_effect, EffectTruth) else model_effect,
            "new_v1_or_v2_lease_issued": False,
            "history_duplicate_count": 0,
            "automatic_retry_started": False,
            "body_or_model_entry_started": False,
            "readback_at": readback_at,
            **dict(_FIXTURE_READBACK_BOUNDARY),
            **dict(_FALSE_EFFECT_FLAGS),
        }
        body["v1_finalize_readback_sha256"] = sha256_bytes(
            _V1_REVOKE_FINALIZE_DOMAIN + canonical_json_bytes(body)
        )
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReferenceV1RevokeFinalizeReadback":
        fields = {
            "contract_version", "record_type", "operation_id", "semantic_operation_key",
            "request_sha256", "terminal_kind", "v1_lease_identity_sha256",
            "terminal_readback_sha256", "terminal_close_readback_sha256",
            "failed_closed_gate_proof_sha256", "revoke_or_expiry_intent",
            "revoke_or_expiry_event_sha256", "expected_fence_revision", "expected_fence_sha256",
            "predecessor_snapshot_sha256", "result_fence_revision", "result_fence_sha256",
            "result_snapshot_sha256", "committed_event_sha256", "terminal_history_event_sha256",
            "terminal_history_sha256", "terminal_history_disposition", "history_append_count",
            "outcome", "trusted_time_receipt_sha256", "broker_domain_sha256",
            "broker_process_identity_sha256", "broker_session_sha256", "product_build_sha256",
            "broker_protocol_version", "result_lifecycle", "result_retained_object",
            "result_v1_state", "result_v1_lease_identity_sha256", "result_v1_handle_count",
            "result_v1_terminal_history_sha256", "result_v2_state",
            "result_v2_lease_identity_sha256", "result_v2_handle_count",
            "result_v2_terminal_history_sha256", "result_revoke_or_expiry_intent",
            "result_revoke_or_expiry_event_sha256", "body_effect", "model_effect",
            "new_v1_or_v2_lease_issued", "history_duplicate_count", "automatic_retry_started",
            "body_or_model_entry_started", "readback_at", *set(_FIXTURE_READBACK_BOUNDARY),
            *set(_FALSE_EFFECT_FLAGS),
            "v1_finalize_readback_sha256",
        }
        _exact(value, fields, "ReferenceV1RevokeFinalizeReadback")
        if value["contract_version"] != V1_REVOKE_FINALIZE_READBACK_CONTRACT_VERSION or value["record_type"] != "ReferenceV1RevokeFinalizeReadback":
            raise ValueError("V1 finalize readback identity/version is invalid")
        for name in ("operation_id", "semantic_operation_key", "broker_protocol_version"):
            _identifier(value[name], name)
        for name in (
            "request_sha256", "v1_lease_identity_sha256", "revoke_or_expiry_event_sha256",
            "expected_fence_sha256", "predecessor_snapshot_sha256", "trusted_time_receipt_sha256",
            "broker_domain_sha256", "broker_process_identity_sha256", "broker_session_sha256",
            "product_build_sha256",
        ):
            _digest(value[name], name)
        for name in (
            "terminal_readback_sha256", "terminal_close_readback_sha256",
            "failed_closed_gate_proof_sha256", "result_fence_sha256", "result_snapshot_sha256",
            "committed_event_sha256", "terminal_history_event_sha256", "terminal_history_sha256",
        ):
            _digest(value[name], name, nullable=True)
        intent = _enum(RevokeExpiryIntent, value["revoke_or_expiry_intent"], "revoke_or_expiry_intent")
        if intent is RevokeExpiryIntent.ABSENT:
            raise ValueError("V1 revoke finalize requires exact revoke/expiry intent")
        terminal = None if value["terminal_kind"] is None else _enum(TerminalKind, value["terminal_kind"], "terminal_kind")
        outcome = _enum(V1RevokeFinalizeOutcome, value["outcome"], "outcome")
        disposition = _enum(TerminalHistoryDisposition, value["terminal_history_disposition"], "terminal_history_disposition")
        append_count = _bounded_int(value["history_append_count"], "history_append_count", 0, 1)
        if (disposition is TerminalHistoryDisposition.SEALED_ONCE) != (append_count == 1):
            raise ValueError("V1 history disposition/append count mismatch")
        expected_revision = _positive(value["expected_fence_revision"], "expected_fence_revision")
        result_revision = None if value["result_fence_revision"] is None else _positive(value["result_fence_revision"], "result_fence_revision")
        body_effect = _enum(EffectTruth, value["body_effect"], "body_effect")
        model_effect = _enum(EffectTruth, value["model_effect"], "model_effect")
        joint = _parse_optional_readback_joint(value)
        for name in (
            "new_v1_or_v2_lease_issued",
            "automatic_retry_started",
            "body_or_model_entry_started",
        ):
            if value[name] is not False:
                raise ValueError(f"{name} must remain zero/false")
        if type(value["history_duplicate_count"]) is not int or value["history_duplicate_count"] != 0:
            raise ValueError("history_duplicate_count must be exact integer zero")
        finalized = {
            TerminalKind.CONSUMED: V1RevokeFinalizeOutcome.V1_CONSUMED_REVOKE_FINALIZED,
            TerminalKind.BURNED: V1RevokeFinalizeOutcome.V1_BURNED_REVOKE_FINALIZED,
            TerminalKind.FAILED_CLOSED: V1RevokeFinalizeOutcome.V1_FAILED_CLOSED_REVOKE_FINALIZED_NOT_CONFIRMED,
        }
        if outcome in finalized.values():
            if terminal is None or outcome is not finalized[terminal]:
                raise ValueError("V1 finalize terminal/outcome mismatch")
            if terminal is TerminalKind.FAILED_CLOSED:
                if value["failed_closed_gate_proof_sha256"] is None or value["terminal_close_readback_sha256"] is not None or body_effect is not EffectTruth.NOT_CONFIRMED or model_effect is not EffectTruth.NOT_CONFIRMED:
                    raise ValueError("V1 FAILED_CLOSED finalize lacks exact gate/effect truth")
            elif value["terminal_close_readback_sha256"] is None or value["failed_closed_gate_proof_sha256"] is not None:
                raise ValueError("V1 terminal finalize lacks exact close proof")
            if (
                value["terminal_readback_sha256"] is None
                or result_revision != expected_revision + 1
                or value["result_fence_sha256"] is None
                or value["result_snapshot_sha256"] is None
                or value["committed_event_sha256"] is None
                or value["terminal_history_event_sha256"] is None
                or value["terminal_history_sha256"] is None
                or disposition is TerminalHistoryDisposition.NOT_CONFIRMED
                or joint is None
            ):
                raise ValueError("V1 finalize committed result lacks exact history/generation")
            lifecycle, retained, v1, v1_count, v2, v2_count, result_intent = joint
            if lifecycle is not ReferenceLifecycle.REVOKED or retained is not RetainedObject.PUBLISHED or v1 is not CapabilityLeaseV1Current.NONE or v1_count != 0 or v2 is not CapabilityLeaseV2Current.V2_ABSENT or v2_count != 0 or result_intent is not intent or value["result_revoke_or_expiry_event_sha256"] != value["revoke_or_expiry_event_sha256"]:
                raise ValueError("V1 finalized result tuple is invalid")
            if value["result_v1_terminal_history_sha256"] != value["terminal_history_sha256"]:
                raise ValueError("V1 finalized terminal history lineage mismatch")
        elif outcome is V1RevokeFinalizeOutcome.V1_TERMINAL_AWAITING_FINALIZE:
            if terminal is None or value["terminal_readback_sha256"] is None:
                raise ValueError("V1 awaiting-finalize terminal proof is incomplete")
            if terminal is TerminalKind.FAILED_CLOSED:
                if (
                    value["failed_closed_gate_proof_sha256"] is None
                    or value["terminal_close_readback_sha256"] is not None
                    or body_effect is not EffectTruth.NOT_CONFIRMED
                    or model_effect is not EffectTruth.NOT_CONFIRMED
                ):
                    raise ValueError("V1 awaiting-finalize FAILED_CLOSED proof is incomplete")
            elif (
                value["terminal_close_readback_sha256"] is None
                or value["failed_closed_gate_proof_sha256"] is not None
            ):
                raise ValueError("V1 awaiting-finalize terminal close proof is incomplete")
            if (
                result_revision != expected_revision
                or value["result_fence_sha256"] != value["expected_fence_sha256"]
                or value["result_snapshot_sha256"] != value["predecessor_snapshot_sha256"]
                or value["committed_event_sha256"] is not None
                or value["terminal_history_event_sha256"] is None
                or disposition is not TerminalHistoryDisposition.EXACT_PRESENT
                or append_count != 0
                or joint is None
            ):
                raise ValueError("V1 terminal-awaiting readback is not unchanged/current")
            lifecycle, retained, v1, v1_count, v2, v2_count, result_intent = joint
            if lifecycle is not ReferenceLifecycle.REVOKE_PENDING or retained is not RetainedObject.PUBLISHED or v1.value != terminal.value or v1_count != 0 or value["result_v1_lease_identity_sha256"] != value["v1_lease_identity_sha256"] or value["result_v1_terminal_history_sha256"] != value["terminal_history_sha256"] or v2 is not CapabilityLeaseV2Current.V2_ABSENT or result_intent is not intent or value["result_revoke_or_expiry_event_sha256"] != value["revoke_or_expiry_event_sha256"]:
                raise ValueError("V1 terminal-awaiting joint tuple mismatch")
        elif outcome is V1RevokeFinalizeOutcome.V1_ACTIVE_RECOVERY_REQUIRED:
            if terminal is not None or value["terminal_readback_sha256"] is not None or value["terminal_close_readback_sha256"] is not None or value["failed_closed_gate_proof_sha256"] is not None or joint is None or result_revision is None or value["result_fence_sha256"] is None or value["result_snapshot_sha256"] is None or value["committed_event_sha256"] is not None or value["terminal_history_event_sha256"] is not None or value["terminal_history_sha256"] is not None or disposition is not TerminalHistoryDisposition.NOT_CONFIRMED or append_count != 0 or body_effect is not EffectTruth.NOT_CONFIRMED or model_effect is not EffectTruth.NOT_CONFIRMED:
                raise ValueError("V1 active recovery truth is incomplete")
            lifecycle, retained, v1, v1_count, v2, v2_count, result_intent = joint
            if lifecycle is not ReferenceLifecycle.REVOKE_PENDING or retained is not RetainedObject.PUBLISHED or v1 not in _V1_ACTIVE or v1_count != 1 or v2 is not CapabilityLeaseV2Current.V2_ABSENT or result_intent is not intent or value["result_revoke_or_expiry_event_sha256"] != value["revoke_or_expiry_event_sha256"]:
                raise ValueError("V1 active recovery tuple is invalid")
        elif outcome is V1RevokeFinalizeOutcome.STALE_OTHER_COMMIT:
            if joint is None or result_revision is None or value["result_fence_sha256"] is None or value["result_snapshot_sha256"] is None or value["committed_event_sha256"] is None or (result_revision == expected_revision and value["result_fence_sha256"] == value["expected_fence_sha256"]) or append_count != 0:
                raise ValueError("V1 stale readback lacks exact other-commit truth")
        elif (
            terminal is not None
            or joint is not None
            or result_revision is not None
            or value["result_fence_sha256"] is not None
            or value["result_snapshot_sha256"] is not None
            or value["committed_event_sha256"] is not None
            or value["terminal_history_event_sha256"] is not None
            or value["terminal_history_sha256"] is not None
            or disposition is not TerminalHistoryDisposition.NOT_CONFIRMED
            or append_count != 0
            or body_effect is not EffectTruth.NOT_CONFIRMED
            or model_effect is not EffectTruth.NOT_CONFIRMED
        ):
            raise ValueError("unknown V1 finalize outcome must remain NOT_CONFIRMED")
        _timestamp(value["readback_at"], "readback_at")
        _validate_fixture_readback_boundary(value)
        _validate_false_flags(value)
        if value["v1_finalize_readback_sha256"] != _hash(
            _V1_REVOKE_FINALIZE_DOMAIN, value, "v1_finalize_readback_sha256"
        ):
            raise ValueError("V1 finalize readback digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


_ABORT_EVENTS = [
    "SPAWN_COMMITTED", "ABORT_REQUESTED", "EXIT_WAIT_STARTED", "CHILD_EXITED",
    "REMOTE_CLOSE_VERIFIED", "ABORT_COMPLETE",
]


@dataclass(frozen=True, slots=True, init=False)
class ReferenceChildAbortRecoveryReadback:
    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("child abort readback must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        attachment_sha256: str,
        begin_lineage_sha256: str,
        spawn_truth: SpawnTruth,
        lifecycle_events: Sequence[str],
        child_process_identity_sha256: str | None,
        body_gate_opened: bool | None,
        audio_role_read_count: int | None,
        transcript_role_read_count: int | None,
        model_invocation_start_count: int | None,
        child_exited: bool | None,
        no_surviving_child: bool | None,
        audio_remote_role_state: RemoteRoleState,
        transcript_remote_role_state: RemoteRoleState,
        body_effect: EffectTruth,
        model_effect: EffectTruth,
        readback_at: str,
        body_observation_readback_sha256: str | None = None,
        model_observation_readback_sha256: str | None = None,
    ) -> "ReferenceChildAbortRecoveryReadback":
        body: dict[str, Any] = {
            "contract_version": CHILD_ABORT_READBACK_CONTRACT_VERSION,
            "record_type": "ReferenceChildAbortRecoveryReadback",
            "operation_id": operation_id,
            "attachment_sha256": attachment_sha256,
            "begin_lineage_sha256": begin_lineage_sha256,
            "spawn_truth": spawn_truth.value if isinstance(spawn_truth, SpawnTruth) else spawn_truth,
            "lifecycle_events": list(lifecycle_events),
            "child_process_identity_sha256": child_process_identity_sha256,
            "body_gate_opened": body_gate_opened,
            "audio_role_read_count": audio_role_read_count,
            "transcript_role_read_count": transcript_role_read_count,
            "model_invocation_start_count": model_invocation_start_count,
            "child_exited": child_exited,
            "no_surviving_child": no_surviving_child,
            "audio_remote_role_state": audio_remote_role_state.value if isinstance(audio_remote_role_state, RemoteRoleState) else audio_remote_role_state,
            "transcript_remote_role_state": transcript_remote_role_state.value if isinstance(transcript_remote_role_state, RemoteRoleState) else transcript_remote_role_state,
            "body_effect": body_effect.value if isinstance(body_effect, EffectTruth) else body_effect,
            "model_effect": model_effect.value if isinstance(model_effect, EffectTruth) else model_effect,
            "body_observation_readback_sha256": body_observation_readback_sha256,
            "model_observation_readback_sha256": model_observation_readback_sha256,
            "unrelated_process_affected": False,
            "pid_or_name_fallback_used": False,
            "replay_started": False,
            "readback_at": readback_at,
            **dict(_FIXTURE_READBACK_BOUNDARY),
            **dict(_FALSE_EFFECT_FLAGS),
        }
        body["child_abort_readback_sha256"] = sha256_bytes(
            _CHILD_ABORT_DOMAIN + canonical_json_bytes(body)
        )
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReferenceChildAbortRecoveryReadback":
        fields = {
            "contract_version", "record_type", "operation_id", "attachment_sha256",
            "begin_lineage_sha256", "spawn_truth", "lifecycle_events",
            "child_process_identity_sha256", "body_gate_opened", "audio_role_read_count",
            "transcript_role_read_count", "model_invocation_start_count", "child_exited",
            "no_surviving_child", "audio_remote_role_state", "transcript_remote_role_state",
            "body_effect", "model_effect", "body_observation_readback_sha256",
            "model_observation_readback_sha256", "unrelated_process_affected",
            "pid_or_name_fallback_used", "replay_started", "readback_at",
            *set(_FIXTURE_READBACK_BOUNDARY), *set(_FALSE_EFFECT_FLAGS),
            "child_abort_readback_sha256",
        }
        _exact(value, fields, "ReferenceChildAbortRecoveryReadback")
        if value["contract_version"] != CHILD_ABORT_READBACK_CONTRACT_VERSION or value["record_type"] != "ReferenceChildAbortRecoveryReadback":
            raise ValueError("child abort readback identity/version is invalid")
        _identifier(value["operation_id"], "operation_id")
        for name in ("attachment_sha256", "begin_lineage_sha256"):
            _digest(value[name], name)
        child_identity = _digest(value["child_process_identity_sha256"], "child_process_identity_sha256", nullable=True)
        truth = _enum(SpawnTruth, value["spawn_truth"], "spawn_truth")
        if not isinstance(value["lifecycle_events"], list) or any(not isinstance(item, str) for item in value["lifecycle_events"]):
            raise ValueError("abort lifecycle events must be a string array")
        audio_remote = _enum(RemoteRoleState, value["audio_remote_role_state"], "audio_remote_role_state")
        transcript_remote = _enum(RemoteRoleState, value["transcript_remote_role_state"], "transcript_remote_role_state")
        body_effect = _enum(EffectTruth, value["body_effect"], "body_effect")
        model_effect = _enum(EffectTruth, value["model_effect"], "model_effect")
        body_observation = _digest(
            value["body_observation_readback_sha256"],
            "body_observation_readback_sha256",
            nullable=True,
        )
        model_observation = _digest(
            value["model_observation_readback_sha256"],
            "model_observation_readback_sha256",
            nullable=True,
        )
        nullable_bools = ("body_gate_opened", "child_exited", "no_surviving_child")
        if any(value[name] is not None and not isinstance(value[name], bool) for name in nullable_bools):
            raise ValueError("child abort tri-state observations must be bool or null")
        counts: dict[str, int | None] = {}
        for name in ("audio_role_read_count", "transcript_role_read_count", "model_invocation_start_count"):
            counts[name] = None if value[name] is None else _bounded_int(value[name], name, 0, 2_147_483_647)
        if truth is SpawnTruth.PROVEN_FALSE:
            if (
                child_identity is not None
                or value["lifecycle_events"]
                or value["body_gate_opened"] is not False
                or any(item != 0 for item in counts.values())
                or value["child_exited"] is not False
                or value["no_surviving_child"] is not True
                or audio_remote is not RemoteRoleState.ABSENT_PROVEN
                or transcript_remote is not RemoteRoleState.ABSENT_PROVEN
                or body_effect is not EffectTruth.ZERO
                or model_effect is not EffectTruth.ZERO
            ):
                raise ValueError("child-not-created proof is incomplete or contradictory")
        elif truth is SpawnTruth.PROVEN_TRUE:
            if child_identity is None:
                raise ValueError("created child requires pinned process identity")
            events = value["lifecycle_events"]
            if events != _ABORT_EVENTS[: len(events)] or not events:
                raise ValueError("created-child abort lifecycle is out of order")
            complete = events == _ABORT_EVENTS
            if complete:
                if value["child_exited"] is not True or value["no_surviving_child"] is not True:
                    raise ValueError("abort completion requires exact child exit/no survivor")
                closed = {RemoteRoleState.ABSENT_PROVEN, RemoteRoleState.CREATED_THEN_CLOSED_VERIFIED}
                if audio_remote not in closed or transcript_remote not in closed:
                    raise ValueError("abort completion requires both remote role close proofs")
            zero_proven = (
                complete
                and value["body_gate_opened"] is False
                and counts["audio_role_read_count"] == 0
                and counts["transcript_role_read_count"] == 0
                and counts["model_invocation_start_count"] == 0
            )
            if (body_effect is EffectTruth.ZERO or model_effect is EffectTruth.ZERO) and not zero_proven:
                raise ValueError("created-child zero effect lacks the complete positive proof")
            if any(item is not None and item > 0 for item in counts.values()):
                if body_effect is EffectTruth.ZERO or model_effect is EffectTruth.ZERO:
                    raise ValueError("observed reads/model start cannot be relabeled zero")
        else:
            if body_effect is not EffectTruth.NOT_CONFIRMED or model_effect is not EffectTruth.NOT_CONFIRMED:
                raise ValueError("unknown creation truth cannot claim effect zero/success")
        if body_effect is EffectTruth.OBSERVED:
            if (
                truth is not SpawnTruth.PROVEN_TRUE
                or body_observation is None
                or not (
                    value["body_gate_opened"] is True
                    or (counts["audio_role_read_count"] or 0) > 0
                    or (counts["transcript_role_read_count"] or 0) > 0
                )
            ):
                raise ValueError("observed body effect requires an exact positive observation readback")
        elif body_observation is not None:
            raise ValueError("non-observed body effect cannot carry a positive observation readback")
        if model_effect is EffectTruth.OBSERVED:
            if (
                truth is not SpawnTruth.PROVEN_TRUE
                or model_observation is None
                or (counts["model_invocation_start_count"] or 0) <= 0
            ):
                raise ValueError("observed model effect requires an exact positive observation readback")
        elif model_observation is not None:
            raise ValueError("non-observed model effect cannot carry a positive observation readback")
        for name in ("unrelated_process_affected", "pid_or_name_fallback_used", "replay_started"):
            if value[name] is not False:
                raise ValueError(f"{name} must remain false")
        _timestamp(value["readback_at"], "readback_at")
        _validate_fixture_readback_boundary(value)
        _validate_false_flags(value)
        if value["child_abort_readback_sha256"] != _hash(
            _CHILD_ABORT_DOMAIN, value, "child_abort_readback_sha256"
        ):
            raise ValueError("child abort readback digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


class OwnerVoiceReferenceDomainPort(Protocol):
    """TASK-043-owned transaction capability shape; no implementation here."""

    def compare_and_transition(
        self,
        previous: ReferenceDomainSnapshot,
        proposed: ReferenceDomainSnapshot,
        event: ReferenceTransition,
    ) -> Mapping[str, Any]: ...


class OwnerVoiceReferenceCustodyPort(Protocol):
    """Future trusted broker boundary.  No body or handle API is exposed here."""

    def validate_prepare_plan(self, plan: OwnerVoiceReferencePreparePlan) -> Mapping[str, Any]: ...


__all__ = [
    "CapabilityLeaseV1Current",
    "CapabilityLeaseV2Current",
    "EffectTruth",
    "MEDIA_POLICY_SHA256",
    "OwnerVoiceReferenceCustodyPort",
    "OwnerVoiceReferenceDomainPort",
    "OwnerVoiceReferenceMediaFacts",
    "OwnerVoiceReferencePreparePlan",
    "OwnerVoiceReferenceTranscriptFacts",
    "ReferenceChildAbortRecoveryReadback",
    "ReferenceDomainSnapshot",
    "ReferenceLifecycle",
    "ReferenceSourceClassification",
    "ReferenceTerminalRetireRequest",
    "ReferenceTerminalRetireReadback",
    "ReferenceV1RevokeFinalizeReadback",
    "ReferenceTransition",
    "ReferenceV2IssueOrRevokeReadback",
    "RemoteRoleState",
    "RetentionPolicy",
    "RetainedObject",
    "RevokeExpiryIntent",
    "SpawnTruth",
    "Task046OwnerReferenceTranscriptBindingFixture",
    "TerminalKind",
    "TerminalHistoryDisposition",
    "TerminalRetireAction",
    "TerminalRetireOutcome",
    "V1RevokeFinalizeOutcome",
    "V2IssueOrRevokeOutcome",
    "owner_voice_reference_media_policy",
    "validate_reference_transition",
    "validate_terminal_retire_transaction",
    "validate_v1_finalize_predecessor",
    "validate_v2_mint_predecessor",
    "validate_v2_terminal_retire_predecessor",
]
