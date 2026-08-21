"""Pure TASK-041 Audio Completion ledger contract R1A.

The module validates caller-supplied immutable entry chains and evaluates CAS
coordinates.  It performs no filesystem operation, persistence, owner API
revalidation, canonical admission, or Final Review gate issuance.
"""
from __future__ import annotations

import copy
from enum import Enum
import re
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .audio_completion_receipt import (
    AudioCompletionAdmissionCandidate,
    CandidateState,
    CanonicalState,
    parse_audio_completion_admission_candidate,
    validate_audio_completion_transition,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_VERSION = "bai.task041.audio-completion-ledger-contract.v1"
SCHEMA_ID = "https://baisound.dev/schemas/audio-completion-ledger-contract.schema.json"
_KEY_DOMAIN = b"TASK041_AUDIO_COMPLETION_LEDGER_KEY_V1\0"
_ENTRY_DOMAIN = b"TASK041_AUDIO_COMPLETION_LEDGER_ENTRY_V1\0"
_CHAIN_DOMAIN = b"TASK041_AUDIO_COMPLETION_LEDGER_CHAIN_V1\0"
_CAS_DOMAIN = b"TASK041_AUDIO_COMPLETION_LEDGER_CAS_EXPECTATION_V1\0"
_EVALUATION_DOMAIN = b"TASK041_AUDIO_COMPLETION_LEDGER_APPEND_EVALUATION_V1\0"
_OBSERVATION_DOMAIN = b"TASK041_AUDIO_COMPLETION_LEDGER_LATEST_OBSERVATION_V1\0"
_PUBLIC_DOMAIN = b"TASK041_AUDIO_COMPLETION_LEDGER_LATEST_PUBLIC_V1\0"
EMPTY_CHAIN_SHA256 = sha256_bytes(_CHAIN_DOMAIN + canonical_json_bytes([]))
_TOKEN = object()
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_MAX_ENTRIES = 256
_MAX_ENTRY_CANONICAL_BYTES = 4 * 1024 * 1024
_MAX_CHAIN_CANONICAL_BYTES = 16 * 1024 * 1024
_MAX_CHAIN_ITEMS = 4096


class EntryState(str, Enum):
    PERSISTENCE_NOT_OBSERVED_BY_R1A = "PERSISTENCE_NOT_OBSERVED_BY_R1A"


class AppendDecision(str, Enum):
    CONTRACT_APPEND_ELIGIBLE_NOT_AUTHORIZED = "CONTRACT_APPEND_ELIGIBLE_NOT_AUTHORIZED"
    IDEMPOTENT_LATEST_MATCH_NOT_AUTHORIZED = "IDEMPOTENT_LATEST_MATCH_NOT_AUTHORIZED"
    CAS_CONFLICT = "CAS_CONFLICT"
    TRANSITION_CONFLICT = "TRANSITION_CONFLICT"
    LEDGER_KEY_CONFLICT = "LEDGER_KEY_CONFLICT"


class LatestObservationState(str, Enum):
    EMPTY = "EMPTY"
    PROVIDED_CHAIN_DIAGNOSTIC = "PROVIDED_CHAIN_DIAGNOSTIC"


_AUTHORITY_FLAGS = MappingProxyType({
    "native_append_authorized": False,
    "filesystem_persistence_verified": False,
    "storage_origin_authenticated": False,
    "upstream_owner_revalidated": False,
    "canonical_latest_authorized": False,
    "canonical_pass_authorized": False,
    "final_review_gate_issued": False,
})
_EFFECT_FLAGS = MappingProxyType({
    "filesystem_read": False,
    "filesystem_written": False,
    "network_accessed": False,
    "provider_called": False,
    "audio_read": False,
    "audio_written": False,
    "model_loaded": False,
    "process_started": False,
    "release_started": False,
    "deployment_started": False,
})


def _exact(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _identity(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _digest(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} is invalid")
    return validate_sha256(value, field_name=name)


def _count(value: Any, name: str, *, positive: bool = False) -> int:
    lower = 1 if positive else 0
    if isinstance(value, bool) or not isinstance(value, int) or not lower <= value <= _MAX_ENTRIES:
        raise ValueError(f"{name} is outside the bounded range")
    return value


def _positive_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 2_147_483_647:
        raise ValueError(f"{name} must be a positive bounded integer")
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


def _without(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    return {key: copy.deepcopy(item) for key, item in value.items() if key != field}


def _candidate(value: AudioCompletionAdmissionCandidate | Mapping[str, Any]) -> AudioCompletionAdmissionCandidate:
    if isinstance(value, AudioCompletionAdmissionCandidate):
        return parse_audio_completion_admission_candidate(value.to_dict())
    if not isinstance(value, Mapping):
        raise TypeError("candidate must be a validated candidate or mapping")
    return parse_audio_completion_admission_candidate(value)


def _key(value: Any) -> "AudioCompletionLedgerKeyBinding":
    if type(value) is not AudioCompletionLedgerKeyBinding:
        raise TypeError("key must be an exact AudioCompletionLedgerKeyBinding")
    return AudioCompletionLedgerKeyBinding.from_dict(value.to_dict())


class _SealedRecord:
    __slots__ = ("_data",)

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _TOKEN:
            raise TypeError(f"{type(self).__name__} must use a validated factory")
        object.__setattr__(self, "_data", data)

    def __setattr__(self, name: str, value: Any) -> None:
        del name, value
        raise AttributeError(f"{type(self).__name__} is immutable")

    def __reduce__(self) -> object:
        raise TypeError("serialize the validated dictionary, not the typed object")

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


class AudioCompletionLedgerKeyBinding(_SealedRecord):
    RECORD_TYPE = "AudioCompletionLedgerKeyBinding"

    @classmethod
    def for_candidate(cls, candidate: AudioCompletionAdmissionCandidate | Mapping[str, Any]) -> "AudioCompletionLedgerKeyBinding":
        parsed = _candidate(candidate).to_dict()
        scope = parsed["scope_binding"]
        body = {
            "schema_version": SCHEMA_VERSION,
            "record_type": cls.RECORD_TYPE,
            "task_owner": "TASK-041",
            "project_id": scope["project_id"],
            "timeline_id": scope["timeline_id"],
            "timeline_revision": scope["timeline_revision"],
            "timeline_sha256": scope["timeline_sha256"],
            "scope_binding_sha256": parsed["scope_binding_sha256"],
            "receipt_id": parsed["receipt_id"],
        }
        body["ledger_key_sha256"] = sha256_bytes(_KEY_DOMAIN + canonical_json_bytes(body))
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AudioCompletionLedgerKeyBinding":
        _exact(value, {"schema_version", "record_type", "task_owner", "project_id", "timeline_id",
            "timeline_revision", "timeline_sha256", "scope_binding_sha256", "receipt_id",
            "ledger_key_sha256"}, cls.RECORD_TYPE)
        if value["schema_version"] != SCHEMA_VERSION or value["record_type"] != cls.RECORD_TYPE or value["task_owner"] != "TASK-041":
            raise ValueError("ledger key identity/version is invalid")
        _identity(value["project_id"], "project_id")
        _identity(value["timeline_id"], "timeline_id")
        _positive_integer(value["timeline_revision"], "timeline_revision")
        _digest(value["timeline_sha256"], "timeline_sha256")
        _digest(value["scope_binding_sha256"], "scope_binding_sha256")
        _identity(value["receipt_id"], "receipt_id")
        expected = sha256_bytes(_KEY_DOMAIN + canonical_json_bytes(_without(value, "ledger_key_sha256")))
        if value["ledger_key_sha256"] != expected:
            raise ValueError("ledger key digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_TOKEN)


class AudioCompletionLedgerEntryEnvelope(_SealedRecord):
    RECORD_TYPE = "AudioCompletionLedgerEntryEnvelope"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AudioCompletionLedgerEntryEnvelope":
        _exact(value, {"schema_version", "record_type", "task_owner", "key_binding", "ledger_key_sha256",
            "entry_revision", "parent_entry_sha256", "prior_chain_sha256", "candidate",
            "candidate_receipt_sha256", "entry_state", "authority_flags", "effect_flags",
            "entry_sha256", "chain_sha256"}, cls.RECORD_TYPE)
        if value["schema_version"] != SCHEMA_VERSION or value["record_type"] != cls.RECORD_TYPE or value["task_owner"] != "TASK-041":
            raise ValueError("entry identity/version is invalid")
        key = AudioCompletionLedgerKeyBinding.from_dict(value["key_binding"]).to_dict()
        if value["ledger_key_sha256"] != key["ledger_key_sha256"]:
            raise ValueError("entry ledger key mismatch")
        revision = _count(value["entry_revision"], "entry_revision", positive=True)
        parent = _digest(value["parent_entry_sha256"], "parent_entry_sha256", nullable=True)
        if (revision == 1) != (parent is None):
            raise ValueError("entry genesis/parent invariant is invalid")
        prior_chain = _digest(value["prior_chain_sha256"], "prior_chain_sha256")
        if revision == 1 and prior_chain != EMPTY_CHAIN_SHA256:
            raise ValueError("genesis prior chain is invalid")
        candidate = parse_audio_completion_admission_candidate(value["candidate"]).to_dict()
        candidate_key = AudioCompletionLedgerKeyBinding.for_candidate(candidate).to_dict()
        if candidate_key != key or candidate["revision"] != revision:
            raise ValueError("entry candidate key/revision mismatch")
        if value["candidate_receipt_sha256"] != candidate["receipt_sha256"]:
            raise ValueError("entry candidate digest mismatch")
        if value["entry_state"] != EntryState.PERSISTENCE_NOT_OBSERVED_BY_R1A.value:
            raise ValueError("R1A entry state cannot claim a persistence observation")
        if value["authority_flags"] != dict(_AUTHORITY_FLAGS) or value["effect_flags"] != dict(_EFFECT_FLAGS):
            raise ValueError("entry authority/effect boundary is invalid")
        expected_entry = sha256_bytes(_ENTRY_DOMAIN + canonical_json_bytes(
            {key_name: copy.deepcopy(item) for key_name, item in value.items()
             if key_name not in {"entry_sha256", "chain_sha256"}}
        ))
        if value["entry_sha256"] != expected_entry:
            raise ValueError("entry digest mismatch")
        expected_chain = sha256_bytes(_CHAIN_DOMAIN + canonical_json_bytes({
            "prior_chain_sha256": prior_chain,
            "entry_sha256": expected_entry,
        }))
        if value["chain_sha256"] != expected_chain:
            raise ValueError("entry chain digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_TOKEN)


class AudioCompletionLedgerCasExpectation(_SealedRecord):
    RECORD_TYPE = "AudioCompletionLedgerCasExpectation"

    @classmethod
    def create(cls, *, key: AudioCompletionLedgerKeyBinding, expected_entry_count: int,
               expected_latest_entry_sha256: str | None,
               expected_latest_candidate_sha256: str | None,
               expected_chain_sha256: str) -> "AudioCompletionLedgerCasExpectation":
        key = _key(key)
        body = {"schema_version": SCHEMA_VERSION, "record_type": cls.RECORD_TYPE,
            "task_owner": "TASK-041", "ledger_key_sha256": key.to_dict()["ledger_key_sha256"],
            "expected_entry_count": expected_entry_count,
            "expected_latest_entry_sha256": expected_latest_entry_sha256,
            "expected_latest_candidate_sha256": expected_latest_candidate_sha256,
            "expected_chain_sha256": expected_chain_sha256,
            "expectation_is_authority": False}
        body["expectation_sha256"] = sha256_bytes(_CAS_DOMAIN + canonical_json_bytes(body))
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AudioCompletionLedgerCasExpectation":
        _exact(value, {"schema_version", "record_type", "task_owner", "ledger_key_sha256",
            "expected_entry_count", "expected_latest_entry_sha256", "expected_latest_candidate_sha256",
            "expected_chain_sha256", "expectation_is_authority", "expectation_sha256"}, cls.RECORD_TYPE)
        if value["schema_version"] != SCHEMA_VERSION or value["record_type"] != cls.RECORD_TYPE or value["task_owner"] != "TASK-041":
            raise ValueError("CAS identity/version is invalid")
        _digest(value["ledger_key_sha256"], "ledger_key_sha256")
        count = _count(value["expected_entry_count"], "expected_entry_count")
        latest_entry = _digest(value["expected_latest_entry_sha256"], "expected_latest_entry_sha256", nullable=True)
        latest_candidate = _digest(value["expected_latest_candidate_sha256"], "expected_latest_candidate_sha256", nullable=True)
        chain = _digest(value["expected_chain_sha256"], "expected_chain_sha256")
        if count == 0:
            if latest_entry is not None or latest_candidate is not None or chain != EMPTY_CHAIN_SHA256:
                raise ValueError("empty CAS sentinel is invalid")
        elif latest_entry is None or latest_candidate is None:
            raise ValueError("nonempty CAS requires latest coordinates")
        if value["expectation_is_authority"] is not False:
            raise ValueError("CAS expectation cannot be authority")
        expected = sha256_bytes(_CAS_DOMAIN + canonical_json_bytes(_without(value, "expectation_sha256")))
        if value["expectation_sha256"] != expected:
            raise ValueError("CAS expectation digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_TOKEN)


class AudioCompletionAppendEvaluation(_SealedRecord):
    RECORD_TYPE = "AudioCompletionAppendEvaluation"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AudioCompletionAppendEvaluation":
        _exact(value, {"schema_version", "record_type", "task_owner", "decision", "reason_codes",
            "ledger_key_sha256", "observed_entry_count", "observed_latest_entry_sha256",
            "observed_latest_candidate_sha256", "observed_chain_sha256", "incoming_candidate_sha256",
            "expectation_sha256", "authority_flags", "effect_flags", "evaluation_sha256"}, cls.RECORD_TYPE)
        if value["schema_version"] != SCHEMA_VERSION or value["record_type"] != cls.RECORD_TYPE or value["task_owner"] != "TASK-041":
            raise ValueError("append evaluation identity/version is invalid")
        try:
            decision = AppendDecision(value["decision"])
        except (TypeError, ValueError) as exc:
            raise ValueError("append decision is invalid") from exc
        reasons = value["reason_codes"]
        if not isinstance(reasons, list) or reasons != [decision.value] or len(set(reasons)) != len(reasons):
            raise ValueError("append reasons are not canonical")
        _digest(value["ledger_key_sha256"], "ledger_key_sha256")
        count = _count(value["observed_entry_count"], "observed_entry_count")
        latest_entry = _digest(value["observed_latest_entry_sha256"], "observed_latest_entry_sha256", nullable=True)
        latest_candidate = _digest(value["observed_latest_candidate_sha256"], "observed_latest_candidate_sha256", nullable=True)
        chain = _digest(value["observed_chain_sha256"], "observed_chain_sha256")
        if count == 0:
            if latest_entry is not None or latest_candidate is not None or chain != EMPTY_CHAIN_SHA256:
                raise ValueError("empty evaluation observation is invalid")
        elif latest_entry is None or latest_candidate is None:
            raise ValueError("nonempty evaluation observation lacks latest coordinates")
        _digest(value["incoming_candidate_sha256"], "incoming_candidate_sha256")
        _digest(value["expectation_sha256"], "expectation_sha256")
        if value["authority_flags"] != dict(_AUTHORITY_FLAGS) or value["effect_flags"] != dict(_EFFECT_FLAGS):
            raise ValueError("evaluation authority/effect boundary is invalid")
        expected = sha256_bytes(_EVALUATION_DOMAIN + canonical_json_bytes(_without(value, "evaluation_sha256")))
        if value["evaluation_sha256"] != expected:
            raise ValueError("append evaluation digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_TOKEN)


class AudioCompletionLatestObservation(_SealedRecord):
    RECORD_TYPE = "AudioCompletionLatestObservation"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AudioCompletionLatestObservation":
        _exact(value, {"schema_version", "record_type", "task_owner", "observation_state",
            "ledger_key_sha256", "entry_count", "latest_entry_sha256",
            "latest_candidate_sha256", "chain_sha256", "latest_candidate_state", "canonical_state",
            "current_valid", "provided_chain_semantically_validated", "consumer_revalidation_required",
            "authority_flags", "effect_flags",
            "observation_sha256"}, cls.RECORD_TYPE)
        if value["schema_version"] != SCHEMA_VERSION or value["record_type"] != cls.RECORD_TYPE or value["task_owner"] != "TASK-041":
            raise ValueError("latest observation identity/version is invalid")
        try:
            state = LatestObservationState(value["observation_state"])
        except (TypeError, ValueError) as exc:
            raise ValueError("latest observation state is invalid") from exc
        _digest(value["ledger_key_sha256"], "ledger_key_sha256")
        count = _count(value["entry_count"], "entry_count")
        latest_entry = _digest(value["latest_entry_sha256"], "latest_entry_sha256", nullable=True)
        latest_candidate = _digest(value["latest_candidate_sha256"], "latest_candidate_sha256", nullable=True)
        chain = _digest(value["chain_sha256"], "chain_sha256")
        if state is LatestObservationState.EMPTY:
            if count != 0 or latest_entry is not None or latest_candidate is not None or chain != EMPTY_CHAIN_SHA256 or value["latest_candidate_state"] is not None:
                raise ValueError("empty latest observation is inconsistent")
        else:
            if count < 1 or latest_entry is None or latest_candidate is None:
                raise ValueError("provided-chain latest observation is inconsistent")
            if value["latest_candidate_state"] != CandidateState.SOURCE_REVALIDATION_REQUIRED.value:
                raise ValueError("latest candidate state is outside R0")
        if value["canonical_state"] != CanonicalState.NOT_MINTED.value or value["current_valid"] is not False:
            raise ValueError("R1A cannot claim canonical/current state")
        if value["provided_chain_semantically_validated"] is not False or value["consumer_revalidation_required"] is not True:
            raise ValueError("serialized observations cannot preserve supplied-chain validation authority")
        if value["authority_flags"] != dict(_AUTHORITY_FLAGS) or value["effect_flags"] != dict(_EFFECT_FLAGS):
            raise ValueError("latest observation authority/effect boundary is invalid")
        expected = sha256_bytes(_OBSERVATION_DOMAIN + canonical_json_bytes(_without(value, "observation_sha256")))
        if value["observation_sha256"] != expected:
            raise ValueError("latest observation digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_TOKEN)

    def to_public_dict(self) -> dict[str, Any]:
        if type(self) is not AudioCompletionLatestObservation:
            raise TypeError("public projection requires an exact latest observation")
        private = AudioCompletionLatestObservation.from_dict(self.to_dict()).to_dict()
        body = {"schema_version": SCHEMA_VERSION,
            "record_type": "AudioCompletionLedgerLatestPublicProjection",
            "observation_state": ("EMPTY" if private["observation_state"] == LatestObservationState.EMPTY.value
                                  else "PROVIDED_CHAIN_DIAGNOSTIC"),
            "entry_count": private["entry_count"],
            "latest_candidate_state": private["latest_candidate_state"],
            "canonical_state": CanonicalState.NOT_MINTED.value,
            "current_valid": False,
            "provided_chain_semantically_validated": False,
            "consumer_revalidation_required": True,
            "storage_origin_authenticated": False,
            "native_append_authorized": False,
            "canonical_latest_authorized": False,
            "canonical_pass_authorized": False}
        body["public_projection_sha256"] = sha256_bytes(_PUBLIC_DOMAIN + canonical_json_bytes(body))
        return body


def make_entry_envelope(candidate: AudioCompletionAdmissionCandidate | Mapping[str, Any], *,
                        key: AudioCompletionLedgerKeyBinding,
                        previous_entry: AudioCompletionLedgerEntryEnvelope | None = None) -> AudioCompletionLedgerEntryEnvelope:
    key = _key(key)
    parsed = _candidate(candidate)
    candidate_body = parsed.to_dict()
    if AudioCompletionLedgerKeyBinding.for_candidate(parsed).to_dict() != key.to_dict():
        raise ValueError("candidate does not belong to the ledger key")
    if previous_entry is None:
        if candidate_body["revision"] != 1:
            raise ValueError("genesis entry requires candidate revision 1")
        parent_entry, prior_chain = None, EMPTY_CHAIN_SHA256
    else:
        if type(previous_entry) is not AudioCompletionLedgerEntryEnvelope:
            raise TypeError("previous_entry must be an exact entry envelope")
        prior = AudioCompletionLedgerEntryEnvelope.from_dict(previous_entry.to_dict()).to_dict()
        if prior["key_binding"] != key.to_dict():
            raise ValueError("previous entry belongs to another ledger key")
        validate_audio_completion_transition(prior["candidate"], candidate_body)
        parent_entry, prior_chain = prior["entry_sha256"], prior["chain_sha256"]
    body = {"schema_version": SCHEMA_VERSION,
        "record_type": AudioCompletionLedgerEntryEnvelope.RECORD_TYPE,
        "task_owner": "TASK-041", "key_binding": key.to_dict(),
        "ledger_key_sha256": key.to_dict()["ledger_key_sha256"],
        "entry_revision": candidate_body["revision"],
        "parent_entry_sha256": parent_entry, "prior_chain_sha256": prior_chain,
        "candidate": candidate_body, "candidate_receipt_sha256": candidate_body["receipt_sha256"],
        "entry_state": EntryState.PERSISTENCE_NOT_OBSERVED_BY_R1A.value,
        "authority_flags": dict(_AUTHORITY_FLAGS), "effect_flags": dict(_EFFECT_FLAGS)}
    body["entry_sha256"] = sha256_bytes(_ENTRY_DOMAIN + canonical_json_bytes(body))
    body["chain_sha256"] = sha256_bytes(_CHAIN_DOMAIN + canonical_json_bytes({
        "prior_chain_sha256": prior_chain, "entry_sha256": body["entry_sha256"]}))
    return AudioCompletionLedgerEntryEnvelope.from_dict(body)


def _parse_bounded_entry_chain(
    entries: Sequence[AudioCompletionLedgerEntryEnvelope | Mapping[str, Any]],
) -> tuple[AudioCompletionLedgerEntryEnvelope, ...]:
    if type(entries) not in {list, tuple}:
        raise TypeError("entry chain must be an exact list or tuple")
    if len(entries) > _MAX_ENTRIES:
        raise ValueError("entry chain exceeds the entry-count bound")
    parsed: list[AudioCompletionLedgerEntryEnvelope] = []
    total_bytes = 0
    total_items = 0
    for item in entries:
        raw = item.to_dict() if isinstance(item, AudioCompletionLedgerEntryEnvelope) else item
        if not isinstance(raw, Mapping):
            raise ValueError("entry chain item must be a mapping or entry envelope")
        try:
            normalized = copy.deepcopy(dict(raw))
            encoded = canonical_json_bytes(normalized)
        except (TypeError, ValueError) as exc:
            raise ValueError("entry chain item is not canonically serializable") from exc
        if len(encoded) > _MAX_ENTRY_CANONICAL_BYTES:
            raise ValueError("entry chain item exceeds the canonical byte bound")
        total_bytes += len(encoded)
        if total_bytes > _MAX_CHAIN_CANONICAL_BYTES:
            raise ValueError("entry chain exceeds the aggregate canonical byte bound")
        try:
            entry = AudioCompletionLedgerEntryEnvelope.from_dict(normalized)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("entry chain item is malformed") from exc
        total_items += len(entry.to_dict()["candidate"]["evidence_bindings"])
        if total_items > _MAX_CHAIN_ITEMS:
            raise ValueError("entry chain exceeds the aggregate item bound")
        parsed.append(entry)
    return tuple(parsed)


def _validate_parsed_chain(
    parsed: tuple[AudioCompletionLedgerEntryEnvelope, ...],
    key: AudioCompletionLedgerKeyBinding,
) -> tuple[AudioCompletionLedgerEntryEnvelope, ...]:
    prior: AudioCompletionLedgerEntryEnvelope | None = None
    seen_entries: set[str] = set()
    seen_candidates: set[str] = set()
    key_body = key.to_dict()
    for index, entry in enumerate(parsed, start=1):
        body = entry.to_dict()
        if body["key_binding"] != key_body or body["entry_revision"] != index:
            raise ValueError("entry key/order is invalid")
        rebuilt = make_entry_envelope(body["candidate"], key=key, previous_entry=prior)
        if rebuilt.to_dict() != body:
            raise ValueError("entry chain semantics are invalid")
        if body["entry_sha256"] in seen_entries or body["candidate_receipt_sha256"] in seen_candidates:
            raise ValueError("entry/candidate replay is invalid")
        seen_entries.add(body["entry_sha256"])
        seen_candidates.add(body["candidate_receipt_sha256"])
        prior = entry
    return parsed


def validate_full_chain(entries: Sequence[AudioCompletionLedgerEntryEnvelope | Mapping[str, Any]],
                        key: AudioCompletionLedgerKeyBinding) -> tuple[AudioCompletionLedgerEntryEnvelope, ...]:
    key = _key(key)
    return _validate_parsed_chain(_parse_bounded_entry_chain(entries), key)


def cas_for_chain(entries: Sequence[AudioCompletionLedgerEntryEnvelope | Mapping[str, Any]],
                  key: AudioCompletionLedgerKeyBinding) -> AudioCompletionLedgerCasExpectation:
    key = _key(key)
    parsed = validate_full_chain(entries, key)
    if not parsed:
        return AudioCompletionLedgerCasExpectation.create(key=key, expected_entry_count=0,
            expected_latest_entry_sha256=None, expected_latest_candidate_sha256=None,
            expected_chain_sha256=EMPTY_CHAIN_SHA256)
    latest = parsed[-1].to_dict()
    return AudioCompletionLedgerCasExpectation.create(key=key, expected_entry_count=len(parsed),
        expected_latest_entry_sha256=latest["entry_sha256"],
        expected_latest_candidate_sha256=latest["candidate_receipt_sha256"],
        expected_chain_sha256=latest["chain_sha256"])


def observe_latest(entries: Sequence[AudioCompletionLedgerEntryEnvelope | Mapping[str, Any]],
                   key: AudioCompletionLedgerKeyBinding) -> AudioCompletionLatestObservation:
    key = _key(key)
    parsed = validate_full_chain(entries, key)
    latest = None if not parsed else parsed[-1].to_dict()
    body = {"schema_version": SCHEMA_VERSION,
        "record_type": AudioCompletionLatestObservation.RECORD_TYPE,
        "task_owner": "TASK-041",
        "observation_state": (LatestObservationState.EMPTY.value if latest is None
                              else LatestObservationState.PROVIDED_CHAIN_DIAGNOSTIC.value),
        "ledger_key_sha256": key.to_dict()["ledger_key_sha256"],
        "entry_count": len(parsed),
        "latest_entry_sha256": None if latest is None else latest["entry_sha256"],
        "latest_candidate_sha256": None if latest is None else latest["candidate_receipt_sha256"],
        "chain_sha256": EMPTY_CHAIN_SHA256 if latest is None else latest["chain_sha256"],
        "latest_candidate_state": None if latest is None else CandidateState.SOURCE_REVALIDATION_REQUIRED.value,
        "canonical_state": CanonicalState.NOT_MINTED.value, "current_valid": False,
        "provided_chain_semantically_validated": False,
        "consumer_revalidation_required": True,
        "authority_flags": dict(_AUTHORITY_FLAGS), "effect_flags": dict(_EFFECT_FLAGS)}
    body["observation_sha256"] = sha256_bytes(_OBSERVATION_DOMAIN + canonical_json_bytes(body))
    return AudioCompletionLatestObservation.from_dict(body)


def _append_evaluation(decision: AppendDecision, *, key_sha: str,
                       entries: tuple[AudioCompletionLedgerEntryEnvelope, ...],
                       incoming_sha: str, expectation_sha: str) -> AudioCompletionAppendEvaluation:
    latest = None if not entries else entries[-1].to_dict()
    body = {"schema_version": SCHEMA_VERSION,
        "record_type": AudioCompletionAppendEvaluation.RECORD_TYPE,
        "task_owner": "TASK-041", "decision": decision.value,
        "reason_codes": [decision.value], "ledger_key_sha256": key_sha,
        "observed_entry_count": len(entries),
        "observed_latest_entry_sha256": None if latest is None else latest["entry_sha256"],
        "observed_latest_candidate_sha256": None if latest is None else latest["candidate_receipt_sha256"],
        "observed_chain_sha256": EMPTY_CHAIN_SHA256 if latest is None else latest["chain_sha256"],
        "incoming_candidate_sha256": incoming_sha, "expectation_sha256": expectation_sha,
        "authority_flags": dict(_AUTHORITY_FLAGS), "effect_flags": dict(_EFFECT_FLAGS)}
    body["evaluation_sha256"] = sha256_bytes(_EVALUATION_DOMAIN + canonical_json_bytes(body))
    return AudioCompletionAppendEvaluation.from_dict(body)


def evaluate_append(entries: Sequence[AudioCompletionLedgerEntryEnvelope | Mapping[str, Any]],
                    incoming_candidate: AudioCompletionAdmissionCandidate | Mapping[str, Any],
                    expectation: AudioCompletionLedgerCasExpectation) -> AudioCompletionAppendEvaluation:
    if type(expectation) is not AudioCompletionLedgerCasExpectation:
        raise TypeError("expectation must be an exact CAS expectation")
    expectation = AudioCompletionLedgerCasExpectation.from_dict(expectation.to_dict())
    incoming = _candidate(incoming_candidate)
    incoming_body = incoming.to_dict()
    incoming_key = AudioCompletionLedgerKeyBinding.for_candidate(incoming)
    expected_body = expectation.to_dict()
    bounded_entries = _parse_bounded_entry_chain(entries)
    if not bounded_entries:
        parsed: tuple[AudioCompletionLedgerEntryEnvelope, ...] = ()
        key = incoming_key
    else:
        first = bounded_entries[0].to_dict()
        key = AudioCompletionLedgerKeyBinding.from_dict(first["key_binding"])
        parsed = _validate_parsed_chain(bounded_entries, key)
    if expected_body["ledger_key_sha256"] != key.to_dict()["ledger_key_sha256"] or incoming_key.to_dict() != key.to_dict():
        return _append_evaluation(AppendDecision.LEDGER_KEY_CONFLICT,
            key_sha=key.to_dict()["ledger_key_sha256"], entries=parsed,
            incoming_sha=incoming_body["receipt_sha256"], expectation_sha=expected_body["expectation_sha256"])
    current_cas = cas_for_chain(parsed, key).to_dict()
    incoming_sha = incoming_body["receipt_sha256"]
    candidate_shas = [entry.to_dict()["candidate_receipt_sha256"] for entry in parsed]
    if parsed and incoming_sha == candidate_shas[-1]:
        prefix_cas = cas_for_chain(parsed[:-1], key).to_dict()
        decision = (AppendDecision.IDEMPOTENT_LATEST_MATCH_NOT_AUTHORIZED
                    if expected_body == prefix_cas else AppendDecision.CAS_CONFLICT)
        return _append_evaluation(decision, key_sha=key.to_dict()["ledger_key_sha256"],
            entries=parsed, incoming_sha=incoming_sha, expectation_sha=expected_body["expectation_sha256"])
    if incoming_sha in candidate_shas:
        return _append_evaluation(AppendDecision.TRANSITION_CONFLICT,
            key_sha=key.to_dict()["ledger_key_sha256"], entries=parsed,
            incoming_sha=incoming_sha, expectation_sha=expected_body["expectation_sha256"])
    if expected_body != current_cas:
        return _append_evaluation(AppendDecision.CAS_CONFLICT,
            key_sha=key.to_dict()["ledger_key_sha256"], entries=parsed,
            incoming_sha=incoming_sha, expectation_sha=expected_body["expectation_sha256"])
    try:
        make_entry_envelope(incoming, key=key, previous_entry=None if not parsed else parsed[-1])
    except (TypeError, ValueError):
        decision = AppendDecision.TRANSITION_CONFLICT
    else:
        decision = AppendDecision.CONTRACT_APPEND_ELIGIBLE_NOT_AUTHORIZED
    return _append_evaluation(decision, key_sha=key.to_dict()["ledger_key_sha256"],
        entries=parsed, incoming_sha=incoming_sha, expectation_sha=expected_body["expectation_sha256"])


def parse_ledger_key(value: Mapping[str, Any]) -> AudioCompletionLedgerKeyBinding:
    return AudioCompletionLedgerKeyBinding.from_dict(value)


def parse_entry_envelope(value: Mapping[str, Any]) -> AudioCompletionLedgerEntryEnvelope:
    return AudioCompletionLedgerEntryEnvelope.from_dict(value)


def parse_cas_expectation(value: Mapping[str, Any]) -> AudioCompletionLedgerCasExpectation:
    return AudioCompletionLedgerCasExpectation.from_dict(value)


def parse_append_evaluation(value: Mapping[str, Any]) -> AudioCompletionAppendEvaluation:
    return AudioCompletionAppendEvaluation.from_dict(value)


def parse_latest_observation(value: Mapping[str, Any]) -> AudioCompletionLatestObservation:
    return AudioCompletionLatestObservation.from_dict(value)


__all__ = [
    "AppendDecision", "AudioCompletionAppendEvaluation", "AudioCompletionLatestObservation",
    "AudioCompletionLedgerCasExpectation", "AudioCompletionLedgerEntryEnvelope",
    "AudioCompletionLedgerKeyBinding", "EMPTY_CHAIN_SHA256", "EntryState",
    "LatestObservationState", "SCHEMA_ID", "SCHEMA_VERSION", "cas_for_chain",
    "evaluate_append", "make_entry_envelope", "observe_latest", "parse_append_evaluation",
    "parse_cas_expectation", "parse_entry_envelope", "parse_latest_observation",
    "parse_ledger_key", "validate_full_chain",
]
