"""TASK-041 R1B cooperative immutable Audio Completion ledger store.

R1B provides a point-in-time namespace observation and a no-replace append
protocol.  It does not authenticate upstream origins, mint canonical PASS,
claim WORM/power-loss durability, or authorize a later consumer.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from enum import Enum
import hmac
import json
from pathlib import PureWindowsPath
import re
import secrets
from types import MappingProxyType
from typing import Any, Mapping, Sequence
import weakref

from .audio_completion_ledger_contract import (
    AppendDecision,
    AudioCompletionLedgerCasExpectation,
    AudioCompletionLedgerEntryEnvelope,
    AudioCompletionLedgerKeyBinding,
    cas_for_chain,
    evaluate_append,
    make_entry_envelope,
    validate_full_chain,
)
from .audio_completion_receipt import AudioCompletionAdmissionCandidate, parse_audio_completion_admission_candidate
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from . import audio_completion_ledger_windows_port as _windows


SCHEMA_VERSION = "bai.task041.audio-completion-ledger-store.v1"
SCHEMA_ID = "https://baisound.dev/schemas/audio-completion-ledger-store-receipt.schema.json"
_STORED_DOMAIN = b"TASK041_AUDIO_COMPLETION_STORED_ENTRY_R1B_V1\0"
_TOKEN_DOMAIN = b"TASK041_AUDIO_COMPLETION_RECOVERY_TOKEN_R1B_V1\0"
_ROOT_DOMAIN = b"TASK041_AUDIO_COMPLETION_ROOT_IDENTITY_R1B_V1\0"
_FILE_ID_DOMAIN = b"TASK041_AUDIO_COMPLETION_FILE_ID_R1B_V1\0"
_RECOVERY_DOMAIN = b"TASK041_AUDIO_COMPLETION_RECOVERY_RECEIPT_R1B_V1\0"
_RECEIPT_DOMAIN = b"TASK041_AUDIO_COMPLETION_STORE_RECEIPT_R1B_V1\0"
_PUBLIC_DOMAIN = b"TASK041_AUDIO_COMPLETION_STORE_PUBLIC_R1B_V1\0"
_TOKEN = object()
_MAX_ENTRIES = 256
_MAX_ENTRY_BYTES = 4 * 1024 * 1024
_MAX_STORED_BYTES = _MAX_ENTRY_BYTES + 64 * 1024
_MAX_CHAIN_DISK_BYTES = 16 * 1024 * 1024
_MAX_PENDING = 8
_MAX_PENDING_BYTES = 16 * 1024 * 1024
_MAX_RETAINED_HANDLES = _windows.MAX_TRACKED_HANDLES
_FINAL_RE = re.compile(r"^(?P<key>[0-9a-f]{64})-(?P<revision>[0-9]{8})\.json$")
_PENDING_RE = re.compile(r"^\.pending-(?P<token>[0-9a-f]{64})\.json$")


class Operation(str, Enum):
    OBSERVE = "OBSERVE"
    APPEND = "APPEND"
    INSPECT_PENDING = "INSPECT_PENDING"
    RESUME_PENDING = "RESUME_PENDING"


class StoreDecision(str, Enum):
    OBSERVED = "OBSERVED"
    APPENDED = "APPENDED"
    ALREADY_COMMITTED_RECONCILED = "ALREADY_COMMITTED_RECONCILED"
    RECOVERY_AVAILABLE = "RECOVERY_AVAILABLE"
    NOT_COMMITTED = "NOT_COMMITTED"
    BLOCKED = "BLOCKED"
    INCOMPLETE = "INCOMPLETE"
    COMMIT_STATE_UNKNOWN = "COMMIT_STATE_UNKNOWN"


class RenameState(str, Enum):
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    RETURNED_TRUE = "RETURNED_TRUE"
    RETURNED_FALSE = "RETURNED_FALSE"
    SYSCALL_COMPLETION_UNKNOWN = "SYSCALL_COMPLETION_UNKNOWN"


class NamespaceState(str, Enum):
    PENDING_ONLY = "PENDING_ONLY"
    FINAL_ONLY = "FINAL_ONLY"
    BOTH = "BOTH"
    NEITHER = "NEITHER"
    DIFFERENT_FINAL = "DIFFERENT_FINAL"
    NOT_OBSERVED = "NOT_OBSERVED"


class ContentState(str, Enum):
    PENDING_VERIFIED = "PENDING_VERIFIED"
    FINAL_VERIFIED = "FINAL_VERIFIED"
    BOTH_IDENTICAL = "BOTH_IDENTICAL"
    CONFLICT = "CONFLICT"
    CORRUPT = "CORRUPT"
    NOT_OBSERVED = "NOT_OBSERVED"


class ResourceObservationState(str, Enum):
    NOT_OBSERVED = "NOT_OBSERVED"
    FILE_FLUSH_RETURNED_TRUE = "FILE_FLUSH_RETURNED_TRUE"
    FINAL_REOPEN_VERIFIED = "FINAL_REOPEN_VERIFIED"
    INCOMPLETE = "INCOMPLETE"


class ResourceReleaseState(str, Enum):
    RELEASE_CONFIRMED = "RELEASE_CONFIRMED"
    INCOMPLETE = "INCOMPLETE"
    UNKNOWN = "UNKNOWN"


class PendingState(str, Enum):
    NONE = "NONE"
    RECOVERABLE = "RECOVERABLE"
    STALE = "STALE"
    CORRUPT = "CORRUPT"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN = "UNKNOWN"


class ChainState(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    NOT_OBSERVED = "NOT_OBSERVED"


class CommitState(str, Enum):
    NOT_COMMITTED = "NOT_COMMITTED"
    KNOWN_COMMITTED = "KNOWN_COMMITTED"
    COMMIT_STATE_UNKNOWN = "COMMIT_STATE_UNKNOWN"


def _validate_decision_matrix(value: Mapping[str, Any]) -> None:
    decision, reasons = value["decision"], tuple(value["reason_codes"])
    allowed_exact = {
        StoreDecision.OBSERVED.value: {
            ("POINT_IN_TIME_NAMESPACE_OBSERVED",),
        },
        StoreDecision.APPENDED.value: {
            ("NO_REPLACE_APPEND_OBSERVED",),
            ("RECOVERED_NO_REPLACE_APPEND_OBSERVED",),
        },
        StoreDecision.ALREADY_COMMITTED_RECONCILED.value: {
            ("EXACT_LATEST_REPLAY_RECONCILED",), ("EXACT_FINAL_ALREADY_PRESENT",),
            ("FINAL_ONLY_EXACT",),
        },
        StoreDecision.RECOVERY_AVAILABLE.value: {
            ("EXACT_PENDING_PRESENT",), ("PENDING_ONLY_EXACT",),
        },
        StoreDecision.NOT_COMMITTED.value: {("NEITHER_PRESENT",)},
    }
    if decision in allowed_exact and reasons not in allowed_exact[decision]:
        raise ValueError("decision/reason matrix is invalid")
    reserved_reasons = {item for groups in allowed_exact.values() for item in groups}
    reserved_reasons.add(("POINT_IN_TIME_NAMESPACE_OBSERVED", "CORRUPT_PENDING_OBSERVED"))
    if decision not in allowed_exact and reasons in reserved_reasons:
        raise ValueError("reserved success reason is invalid for failure decision")
    if decision in allowed_exact and not (
            value["resource_release_state"] == ResourceReleaseState.RELEASE_CONFIRMED.value
            and value["lock_release_confirmed"]
            and value["unreleased_handle_count"] == 0
            and value["unreleased_native_allocation_count"] == 0):
        raise ValueError("success decision requires confirmed resource release")
    operation = value["operation"]
    read_attempted = value["filesystem_read_attempted"]
    read_observed = value["filesystem_read_observed"]
    write_attempted = value["filesystem_write_attempted"]
    write_observed = value["filesystem_write_observed"]
    operation_decisions = {
        Operation.OBSERVE.value: {
            StoreDecision.OBSERVED.value, StoreDecision.BLOCKED.value,
            StoreDecision.INCOMPLETE.value},
        Operation.APPEND.value: {
            StoreDecision.APPENDED.value,
            StoreDecision.ALREADY_COMMITTED_RECONCILED.value,
            StoreDecision.RECOVERY_AVAILABLE.value, StoreDecision.BLOCKED.value,
            StoreDecision.INCOMPLETE.value, StoreDecision.COMMIT_STATE_UNKNOWN.value},
        Operation.INSPECT_PENDING.value: {
            StoreDecision.ALREADY_COMMITTED_RECONCILED.value,
            StoreDecision.RECOVERY_AVAILABLE.value, StoreDecision.NOT_COMMITTED.value,
            StoreDecision.BLOCKED.value, StoreDecision.INCOMPLETE.value},
        Operation.RESUME_PENDING.value: {
            StoreDecision.APPENDED.value,
            StoreDecision.ALREADY_COMMITTED_RECONCILED.value,
            StoreDecision.BLOCKED.value, StoreDecision.INCOMPLETE.value,
            StoreDecision.COMMIT_STATE_UNKNOWN.value},
    }
    if decision not in operation_decisions[operation]:
        raise ValueError("operation/decision matrix is invalid")
    if read_observed and not read_attempted:
        raise ValueError("read observation requires an attempted read phase")
    if write_observed and not write_attempted:
        raise ValueError("write observation requires an attempted write phase")
    if write_attempted and (operation not in {Operation.APPEND.value, Operation.RESUME_PENDING.value}
                            or not value["lock_acquired"]):
        raise ValueError("write attempt is invalid for operation/lock phase")
    if operation in {Operation.OBSERVE.value, Operation.INSPECT_PENDING.value} and (
            write_attempted or write_observed or value["rename_state"] != RenameState.NOT_ATTEMPTED.value):
        raise ValueError("read-only operation contains a mutation phase")
    if value["chain_state"] in {ChainState.NOT_OBSERVED.value, ChainState.INVALID.value}:
        for field in ("entry_count", "pending_count", "chain_disk_bytes", "pending_disk_bytes"):
            if field in value and value[field] != 0:
                raise ValueError("unobserved chain contains observed aggregate facts")
    if value["entry_count"] == 0 and "chain_disk_bytes" in value and value["chain_disk_bytes"] != 0:
        raise ValueError("empty chain cannot contain stored bytes")
    if value["entry_count"] > 0 and "chain_disk_bytes" in value and value["chain_disk_bytes"] == 0:
        raise ValueError("nonempty chain requires stored bytes")
    if value["pending_count"] == 0 and "pending_disk_bytes" in value and value["pending_disk_bytes"] != 0:
        raise ValueError("empty pending aggregate cannot contain stored bytes")
    pending_is_verified = (
        value["global_pending_state"] == PendingState.RECOVERABLE.value
        or value["pending_state"] == PendingState.RECOVERABLE.value
        or value["content_state"] in {
            ContentState.PENDING_VERIFIED.value, ContentState.BOTH_IDENTICAL.value})
    if pending_is_verified and (value["pending_count"] == 0 or (
            "pending_disk_bytes" in value and value["pending_disk_bytes"] == 0)):
        raise ValueError("verified pending observation requires positive count and bytes")
    if value["pending_count"] > 0 and "pending_disk_bytes" in value and value[
            "pending_disk_bytes"] == 0:
        if (value["global_pending_state"] != PendingState.CORRUPT.value
                or value["pending_state"] == PendingState.RECOVERABLE.value
                or value["content_state"] in {
                    ContentState.PENDING_VERIFIED.value, ContentState.BOTH_IDENTICAL.value}):
            raise ValueError("zero-byte pending observation cannot be verified or recoverable")
    if value["pending_count"] == 0 and value["pending_state"] in {
            PendingState.RECOVERABLE.value, PendingState.CORRUPT.value}:
        raise ValueError("pending state requires a global pending observation")
    if value["chain_state"] == ChainState.VALID.value and value["pending_count"] == 0 and value[
            "global_pending_state"] != PendingState.NONE.value:
        raise ValueError("empty global pending aggregate is invalid")
    if value["chain_state"] == ChainState.VALID.value and value["pending_count"] > 0 and value[
            "global_pending_state"] not in {PendingState.RECOVERABLE.value, PendingState.CORRUPT.value}:
        raise ValueError("global pending state requires a count")
    if decision == StoreDecision.OBSERVED.value:
        has_entries = value["entry_count"] > 0
        if not (operation == Operation.OBSERVE.value and value["commit_state"] == CommitState.NOT_COMMITTED.value
                and value["rename_state"] == RenameState.NOT_ATTEMPTED.value
                and value["chain_state"] == ChainState.VALID.value and value["lock_acquired"]
                and read_attempted and read_observed and not write_attempted and not write_observed):
            raise ValueError("OBSERVED state matrix is invalid")
        if not (value["namespace_state"] == (
                    NamespaceState.FINAL_ONLY.value if has_entries else NamespaceState.NEITHER.value)
                and value["content_state"] == (
                    ContentState.FINAL_VERIFIED.value if has_entries else ContentState.NOT_OBSERVED.value)
                and value["resource_observation_state"] == (
                    ResourceObservationState.FINAL_REOPEN_VERIFIED.value
                    if has_entries else ResourceObservationState.NOT_OBSERVED.value)
                and value["pending_state"] == PendingState.NONE.value):
            raise ValueError("OBSERVED target state is invalid")
        if "stored_entry_sha256" in value:
            target_values = tuple(value[field] for field in (
                "stored_entry_sha256", "expected_cas_sha256"))
            if (has_entries and any(item is None for item in target_values)) or (
                    not has_entries and any(item is not None for item in target_values)):
                raise ValueError("OBSERVED target coordinates are invalid")
    if decision == StoreDecision.APPENDED.value:
        expected_reason = (("NO_REPLACE_APPEND_OBSERVED",) if operation == Operation.APPEND.value
            else (("RECOVERED_NO_REPLACE_APPEND_OBSERVED",) if operation == Operation.RESUME_PENDING.value else ()))
        if not (reasons == expected_reason and value["commit_state"] == CommitState.KNOWN_COMMITTED.value
                and value["rename_state"] == RenameState.RETURNED_TRUE.value
                and value["namespace_state"] == NamespaceState.FINAL_ONLY.value
                and value["content_state"] == ContentState.FINAL_VERIFIED.value
                and value["resource_observation_state"] == ResourceObservationState.FINAL_REOPEN_VERIFIED.value
                and value["chain_state"] == ChainState.VALID.value and value["entry_count"] >= 1
                and value["pending_state"] == PendingState.NONE.value
                and value["lock_acquired"] and read_attempted and read_observed
                and write_attempted and write_observed):
            raise ValueError("APPENDED state matrix is invalid")
        if "stored_entry_sha256" in value and any(value[field] is None for field in (
                "stored_entry_sha256", "expected_cas_sha256")):
            raise ValueError("APPENDED target coordinates are incomplete")
    if decision == StoreDecision.ALREADY_COMMITTED_RECONCILED.value:
        reason_operation = {
            ("EXACT_LATEST_REPLAY_RECONCILED",): Operation.APPEND.value,
            ("EXACT_FINAL_ALREADY_PRESENT",): Operation.RESUME_PENDING.value,
            ("FINAL_ONLY_EXACT",): Operation.INSPECT_PENDING.value,
        }
        if not (reason_operation.get(reasons) == operation
                and value["commit_state"] == CommitState.KNOWN_COMMITTED.value
                and value["rename_state"] == RenameState.NOT_ATTEMPTED.value
                and value["namespace_state"] == NamespaceState.FINAL_ONLY.value
                and value["content_state"] == ContentState.FINAL_VERIFIED.value
                and value["chain_state"] == ChainState.VALID.value and value["entry_count"] >= 1
                and value["pending_state"] == PendingState.NONE.value
                and value["lock_acquired"] and read_attempted and read_observed
                and not write_attempted and not write_observed):
            raise ValueError("ALREADY_COMMITTED state matrix is invalid")
        if value["resource_observation_state"] != ResourceObservationState.FINAL_REOPEN_VERIFIED.value:
            raise ValueError("ALREADY_COMMITTED requires final reopen observation")
        if "stored_entry_sha256" in value and any(value[field] is None for field in (
                "stored_entry_sha256", "expected_cas_sha256")):
            raise ValueError("ALREADY_COMMITTED target coordinates are incomplete")
    if decision == StoreDecision.RECOVERY_AVAILABLE.value:
        reason_operation = {("EXACT_PENDING_PRESENT",): Operation.APPEND.value,
            ("PENDING_ONLY_EXACT",): Operation.INSPECT_PENDING.value}
        if not (reason_operation.get(reasons) == operation
                and value["commit_state"] == CommitState.NOT_COMMITTED.value
                and value["rename_state"] == RenameState.NOT_ATTEMPTED.value
                and value["namespace_state"] == NamespaceState.PENDING_ONLY.value
                and value["content_state"] == ContentState.PENDING_VERIFIED.value
                and value["pending_state"] == PendingState.RECOVERABLE.value
                and value["chain_state"] == ChainState.VALID.value
                and value["resource_observation_state"] == ResourceObservationState.NOT_OBSERVED.value
                and value["lock_acquired"] and read_attempted and read_observed
                and not write_attempted and not write_observed):
            raise ValueError("RECOVERY_AVAILABLE state matrix is invalid")
        if "stored_entry_sha256" in value and any(value[field] is None for field in (
                "stored_entry_sha256", "expected_cas_sha256")):
            raise ValueError("RECOVERY_AVAILABLE target coordinates are incomplete")
    if decision == StoreDecision.NOT_COMMITTED.value and not (
            operation == Operation.INSPECT_PENDING.value
            and value["commit_state"] == CommitState.NOT_COMMITTED.value
            and value["rename_state"] == RenameState.NOT_ATTEMPTED.value
            and value["namespace_state"] == NamespaceState.NEITHER.value
            and value["content_state"] == ContentState.NOT_OBSERVED.value
            and value["pending_state"] == PendingState.STALE.value
            and value["resource_observation_state"] == ResourceObservationState.NOT_OBSERVED.value
            and value["chain_state"] == ChainState.VALID.value
            and value["lock_acquired"] and read_attempted and read_observed
            and not write_attempted and not write_observed):
        raise ValueError("NOT_COMMITTED state matrix is invalid")
    if decision == StoreDecision.NOT_COMMITTED.value and "stored_entry_sha256" in value and any(
            value[field] is not None for field in (
                "stored_entry_sha256", "expected_cas_sha256")):
        raise ValueError("NOT_COMMITTED cannot claim target coordinates")
    if decision == StoreDecision.COMMIT_STATE_UNKNOWN.value and not (
            value["commit_state"] == CommitState.COMMIT_STATE_UNKNOWN.value
            and operation in {Operation.APPEND.value, Operation.RESUME_PENDING.value}
            and value["rename_state"] == RenameState.SYSCALL_COMPLETION_UNKNOWN.value
            and write_attempted):
        raise ValueError("unknown decision/state matrix is invalid")
    if decision == StoreDecision.BLOCKED.value and not (
            value["commit_state"] == CommitState.NOT_COMMITTED.value
            and value["rename_state"] == RenameState.NOT_ATTEMPTED.value):
        raise ValueError("BLOCKED cannot claim a rename or commit")
    if decision == StoreDecision.INCOMPLETE.value and value["commit_state"] not in {
            CommitState.NOT_COMMITTED.value, CommitState.KNOWN_COMMITTED.value}:
        raise ValueError("INCOMPLETE commit state is invalid")
    if value["rename_state"] != RenameState.NOT_ATTEMPTED.value:
        if value["operation"] not in {Operation.APPEND.value, Operation.RESUME_PENDING.value}:
            raise ValueError("rename phase is invalid for operation")
        if not write_attempted:
            raise ValueError("rename phase must retain write attempt")
    if value["rename_state"] == RenameState.RETURNED_TRUE.value and value["commit_state"] != CommitState.KNOWN_COMMITTED.value:
        raise ValueError("rename TRUE must retain known commit")
    if value["rename_state"] == RenameState.RETURNED_TRUE.value and decision not in {
            StoreDecision.APPENDED.value, StoreDecision.INCOMPLETE.value}:
        raise ValueError("rename TRUE decision is invalid")
    if value["rename_state"] == RenameState.RETURNED_FALSE.value and not (
            decision == StoreDecision.INCOMPLETE.value
            and value["commit_state"] == CommitState.NOT_COMMITTED.value):
        raise ValueError("rename FALSE state matrix is invalid")
    if value["commit_state"] == CommitState.COMMIT_STATE_UNKNOWN.value and not (
            decision == StoreDecision.COMMIT_STATE_UNKNOWN.value
            and value["rename_state"] == RenameState.SYSCALL_COMPLETION_UNKNOWN.value):
        raise ValueError("unknown commit state is invalid")
    if value["commit_state"] == CommitState.KNOWN_COMMITTED.value and value["namespace_state"] not in {
            NamespaceState.FINAL_ONLY.value, NamespaceState.BOTH.value, NamespaceState.NOT_OBSERVED.value}:
        raise ValueError("known commit namespace matrix is invalid")
    if (value["commit_state"] == CommitState.KNOWN_COMMITTED.value and
            value["namespace_state"] == NamespaceState.NOT_OBSERVED.value and
            decision != StoreDecision.INCOMPLETE.value):
        raise ValueError("only an incomplete receipt may retain unobserved known commit")
    if value["namespace_state"] == NamespaceState.NOT_OBSERVED.value and value["chain_state"] not in {
            ChainState.NOT_OBSERVED.value, ChainState.INVALID.value}:
        raise ValueError("unobserved namespace/chain matrix is invalid")


_AUTHORITY_FLAGS = MappingProxyType({
    "storage_origin_authenticated": False,
    "upstream_owner_revalidated": False,
    "canonical_latest_authorized": False,
    "canonical_pass_authorized": False,
    "final_review_gate_issued": False,
    "consumer_execution_authorized": False,
    "r2_ready_claimed": False,
})


def _token_hash(token: bytes) -> str:
    if type(token) is not bytes or len(token) != 32:
        raise ValueError("recovery token must be exactly 32 opaque bytes")
    return sha256_bytes(_TOKEN_DOMAIN + token)


def _digest_without(value: Mapping[str, Any], field: str, domain: bytes) -> str:
    return sha256_bytes(domain + canonical_json_bytes({
        key: copy.deepcopy(item) for key, item in value.items() if key != field
    }))


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


class _Sealed:
    __slots__ = ("_data",)

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _TOKEN:
            raise TypeError(f"{type(self).__name__} must use a validated factory")
        object.__setattr__(self, "_data", _freeze(copy.deepcopy(dict(data))))

    def __setattr__(self, name: str, value: Any) -> None:
        del name, value
        raise AttributeError(f"{type(self).__name__} is immutable")

    def __reduce__(self) -> object:
        raise TypeError("sealed runtime capabilities and receipts are not pickleable")

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


class PreparedAudioCompletionAppend:
    """Nonserializable capability carrying the raw recovery token in memory."""

    __slots__ = ("_key", "_candidate", "_expectation", "_token", "__weakref__")

    def __init__(self, *, key: AudioCompletionLedgerKeyBinding,
                 candidate: AudioCompletionAdmissionCandidate,
                 expectation: AudioCompletionLedgerCasExpectation,
                 token: bytes, _seal: object | None = None) -> None:
        del key, candidate, expectation, token, _seal
        raise TypeError("use prepare_append")

    def __setattr__(self, name: str, value: Any) -> None:
        del name, value
        raise AttributeError("prepared append is immutable")

    def __repr__(self) -> str:
        return "PreparedAudioCompletionAppend(<sealed>)"

    def __reduce__(self) -> object:
        raise TypeError("prepared append is not serializable")

    def recovery_token(self) -> bytes:
        return bytes(self._token)


def _prepared_api_factory() -> tuple[Any, Any]:
    issued: weakref.WeakKeyDictionary[PreparedAudioCompletionAppend, tuple[bytes, bytes, bytes, bytes]] = (
        weakref.WeakKeyDictionary())

    def prepare_append(*, key: AudioCompletionLedgerKeyBinding,
                       candidate: AudioCompletionAdmissionCandidate | Mapping[str, Any],
                       expectation: AudioCompletionLedgerCasExpectation) -> PreparedAudioCompletionAppend:
        """Prepare and privately register a token before any filesystem effect."""
        parsed_key, parsed_cas = _key(key), _cas(expectation)
        parsed_candidate = parse_audio_completion_admission_candidate(
            candidate.to_dict() if isinstance(candidate, AudioCompletionAdmissionCandidate) else candidate)
        if parsed_cas.to_dict()["ledger_key_sha256"] != parsed_key.to_dict()["ledger_key_sha256"]:
            raise ValueError("CAS belongs to another ledger")
        token = secrets.token_bytes(32)
        _token_hash(token)
        item = object.__new__(PreparedAudioCompletionAppend)
        object.__setattr__(item, "_key", parsed_key)
        object.__setattr__(item, "_candidate", parsed_candidate)
        object.__setattr__(item, "_expectation", parsed_cas)
        object.__setattr__(item, "_token", token)
        issued[item] = (canonical_json_bytes(parsed_key.to_dict()),
            canonical_json_bytes(parsed_candidate.to_dict()),
            canonical_json_bytes(parsed_cas.to_dict()), bytes(token))
        return item

    def resolve(item: Any) -> tuple[AudioCompletionLedgerKeyBinding,
                                    AudioCompletionAdmissionCandidate,
                                    AudioCompletionLedgerCasExpectation, bytes] | None:
        if type(item) is not PreparedAudioCompletionAppend:
            return None
        snapshot = issued.get(item)
        if snapshot is None:
            return None
        try:
            current = (canonical_json_bytes(
                    AudioCompletionLedgerKeyBinding.from_dict(item._key.to_dict()).to_dict()),
                canonical_json_bytes(parse_audio_completion_admission_candidate(
                    item._candidate.to_dict()).to_dict()),
                canonical_json_bytes(AudioCompletionLedgerCasExpectation.from_dict(
                    item._expectation.to_dict()).to_dict()),
                bytes(item._token) if type(item._token) is bytes else b"")
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
        matches = tuple(hmac.compare_digest(observed, expected)
                        for observed, expected in zip(current, snapshot, strict=True))
        if not all(matches):
            return None
        key_body, candidate_body, expectation_body = (
            json.loads(snapshot[index].decode("utf-8")) for index in range(3))
        return (AudioCompletionLedgerKeyBinding.from_dict(key_body),
            parse_audio_completion_admission_candidate(candidate_body),
            AudioCompletionLedgerCasExpectation.from_dict(expectation_body), bytes(snapshot[3]))

    return prepare_append, resolve


prepare_append, _RESOLVE_PREPARED = _prepared_api_factory()
del _prepared_api_factory


class AudioCompletionLedgerRecoveryReceipt(_Sealed):
    RECORD_TYPE = "AudioCompletionLedgerRecoveryReceipt"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AudioCompletionLedgerRecoveryReceipt":
        fields = {"schema_version", "record_type", "task_owner", "ledger_key_sha256",
            "entry_revision", "expected_cas_sha256", "token_sha256", "root_identity_sha256",
            "pending_file_identity_sha256", "rename_continuity_file_identity_sha256",
            "payload_sha256", "pending_name_sha256",
            "receipt_is_capability", "resume_requires_live_revalidation", "recovery_receipt_sha256"}
        if not isinstance(value, Mapping) or set(value) != fields:
            raise ValueError("recovery receipt fields are incomplete or unknown")
        if value["schema_version"] != SCHEMA_VERSION or value["record_type"] != cls.RECORD_TYPE or value["task_owner"] != "TASK-041":
            raise ValueError("recovery receipt identity is invalid")
        for field in ("ledger_key_sha256", "expected_cas_sha256", "token_sha256",
                      "root_identity_sha256", "pending_file_identity_sha256", "payload_sha256",
                      "rename_continuity_file_identity_sha256", "pending_name_sha256",
                      "recovery_receipt_sha256"):
            validate_sha256(value[field], field_name=field)
        if not hmac.compare_digest(value["pending_file_identity_sha256"],
                                   value["rename_continuity_file_identity_sha256"]):
            raise ValueError("recovery rename-continuity binding mismatch")
        if isinstance(value["entry_revision"], bool) or not 1 <= value["entry_revision"] <= _MAX_ENTRIES:
            raise ValueError("recovery revision is invalid")
        if value["receipt_is_capability"] is not False or value["resume_requires_live_revalidation"] is not True:
            raise ValueError("recovery authority boundary is invalid")
        expected_pending_name = f".pending-{value['token_sha256'].removeprefix('sha256:')}.json"
        if value["pending_name_sha256"] != sha256_bytes(expected_pending_name.encode("ascii")):
            raise ValueError("recovery pending-name binding mismatch")
        expected = _digest_without(value, "recovery_receipt_sha256", _RECOVERY_DOMAIN)
        if value["recovery_receipt_sha256"] != expected:
            raise ValueError("recovery receipt digest mismatch")
        return cls(value, _token=_TOKEN)


class AudioCompletionLedgerStoreReceipt(_Sealed):
    RECORD_TYPE = "AudioCompletionLedgerStoreReceipt"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AudioCompletionLedgerStoreReceipt":
        fields = {"schema_version", "record_type", "task_owner", "operation", "decision",
            "reason_codes", "ledger_key_sha256", "entry_count",
            "pending_count", "chain_disk_bytes", "pending_disk_bytes", "stored_entry_sha256",
            "expected_cas_sha256", "rename_state", "namespace_state", "content_state",
            "global_pending_state",
            "resource_observation_state", "resource_release_state", "pending_state", "chain_state",
            "commit_state", "lock_acquired", "filesystem_read_attempted", "filesystem_read_observed",
            "filesystem_write_attempted", "filesystem_write_observed",
            "lock_release_confirmed", "unreleased_handle_count", "unreleased_native_allocation_count",
            "directory_flush_claimed", "power_loss_durability_claimed", "worm_claimed",
            "owner_death_detected", "receipt_is_authority", "consumer_revalidation_required",
            "post_return_state_guaranteed", "authority_flags", "receipt_sha256"}
        if not isinstance(value, Mapping) or set(value) != fields:
            raise ValueError("store receipt fields are incomplete or unknown")
        if value["schema_version"] != SCHEMA_VERSION or value["record_type"] != cls.RECORD_TYPE or value["task_owner"] != "TASK-041":
            raise ValueError("store receipt identity is invalid")
        try:
            Operation(value["operation"]); StoreDecision(value["decision"])
            RenameState(value["rename_state"]); NamespaceState(value["namespace_state"])
            PendingState(value["global_pending_state"])
            ContentState(value["content_state"]); ResourceObservationState(value["resource_observation_state"])
            ResourceReleaseState(value["resource_release_state"]); PendingState(value["pending_state"])
            ChainState(value["chain_state"]); CommitState(value["commit_state"])
        except (TypeError, ValueError) as exc:
            raise ValueError("store receipt state is invalid") from exc
        reasons = value["reason_codes"]
        if (not isinstance(reasons, list) or not 1 <= len(reasons) <= 16 or
                any(not isinstance(item, str) or not re.fullmatch(r"[A-Z0-9_]{1,96}", item) for item in reasons) or
                len(set(reasons)) != len(reasons)):
            raise ValueError("store reason codes are invalid")
        validate_sha256(value["ledger_key_sha256"], field_name="ledger_key_sha256")
        for field in ("stored_entry_sha256", "expected_cas_sha256"):
            if value[field] is not None:
                validate_sha256(value[field], field_name=field)
        for field, maximum in (("entry_count", 256), ("pending_count", 8),
                               ("chain_disk_bytes", _MAX_CHAIN_DISK_BYTES),
                               ("pending_disk_bytes", _MAX_PENDING_BYTES)):
            item = value[field]
            if isinstance(item, bool) or not isinstance(item, int) or not 0 <= item <= maximum:
                raise ValueError(f"{field} is invalid")
        for field in ("lock_acquired", "filesystem_read_attempted", "filesystem_read_observed",
                      "filesystem_write_attempted", "filesystem_write_observed",
                      "lock_release_confirmed"):
            if type(value[field]) is not bool:
                raise ValueError(f"{field} is invalid")
        if (isinstance(value["unreleased_handle_count"], bool) or
                not isinstance(value["unreleased_handle_count"], int) or
                not 0 <= value["unreleased_handle_count"] <= _MAX_RETAINED_HANDLES):
            raise ValueError("unreleased_handle_count is invalid")
        if (isinstance(value["unreleased_native_allocation_count"], bool) or
                not isinstance(value["unreleased_native_allocation_count"], int) or
                not 0 <= value["unreleased_native_allocation_count"] <= 64):
            raise ValueError("unreleased_native_allocation_count is invalid")
        for field in ("directory_flush_claimed", "power_loss_durability_claimed", "worm_claimed", "owner_death_detected"):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        if (value["receipt_is_authority"] is not False or
                value["consumer_revalidation_required"] is not True or
                value["post_return_state_guaranteed"] is not False):
            raise ValueError("store receipt persistence boundary is invalid")
        if value["resource_release_state"] == ResourceReleaseState.RELEASE_CONFIRMED.value and not (
                value["lock_release_confirmed"] and value["unreleased_handle_count"] == 0):
            raise ValueError("lock release/state matrix is invalid")
        if value["unreleased_handle_count"] > 0 and value["resource_release_state"] == ResourceReleaseState.RELEASE_CONFIRMED.value:
            raise ValueError("unreleased handle/state matrix is invalid")
        if value["authority_flags"] != dict(_AUTHORITY_FLAGS):
            raise ValueError("store authority boundary is invalid")
        if (value["unreleased_handle_count"] or value["unreleased_native_allocation_count"]) and value[
                "resource_release_state"] == ResourceReleaseState.RELEASE_CONFIRMED.value:
            raise ValueError("unreleased native resource/state matrix is invalid")
        _validate_decision_matrix(value)
        expected = _digest_without(value, "receipt_sha256", _RECEIPT_DOMAIN)
        if value["receipt_sha256"] != expected:
            raise ValueError("store receipt digest mismatch")
        return cls(value, _token=_TOKEN)

    def to_public_dict(self) -> dict[str, Any]:
        private = type(self).from_dict(self.to_dict()).to_dict()
        body = {"schema_version": SCHEMA_VERSION,
            "record_type": "AudioCompletionLedgerStorePublicProjection",
            "operation": private["operation"], "decision": private["decision"],
            "reason_codes": private["reason_codes"], "entry_count": private["entry_count"],
            "pending_count": private["pending_count"],
            "rename_state": private["rename_state"], "namespace_state": private["namespace_state"],
            "global_pending_state": private["global_pending_state"],
            "content_state": private["content_state"], "resource_observation_state": private["resource_observation_state"],
            "resource_release_state": private["resource_release_state"], "pending_state": private["pending_state"],
            "chain_state": private["chain_state"], "commit_state": private["commit_state"],
            "lock_acquired": private["lock_acquired"],
            "filesystem_read_attempted": private["filesystem_read_attempted"],
            "filesystem_read_observed": private["filesystem_read_observed"],
            "filesystem_write_attempted": private["filesystem_write_attempted"],
            "filesystem_write_observed": private["filesystem_write_observed"],
            "lock_release_confirmed": private["lock_release_confirmed"],
            "unreleased_handle_count": private["unreleased_handle_count"],
            "unreleased_native_allocation_count": private["unreleased_native_allocation_count"],
            "receipt_is_authority": False, "consumer_revalidation_required": True,
            "post_return_state_guaranteed": False,
            "canonical_latest_authorized": False, "canonical_pass_authorized": False,
            "storage_origin_authenticated": False, "r2_ready_claimed": False}
        body["public_projection_sha256"] = sha256_bytes(_PUBLIC_DOMAIN + canonical_json_bytes(body))
        return AudioCompletionLedgerStorePublicProjection.from_dict(body).to_dict()


class AudioCompletionLedgerStorePublicProjection(_Sealed):
    RECORD_TYPE = "AudioCompletionLedgerStorePublicProjection"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AudioCompletionLedgerStorePublicProjection":
        fields = {"schema_version", "record_type", "operation", "decision", "reason_codes",
            "entry_count", "pending_count", "rename_state", "namespace_state",
            "global_pending_state",
            "content_state", "resource_observation_state", "resource_release_state", "pending_state",
            "chain_state", "commit_state", "lock_acquired", "filesystem_read_attempted",
            "filesystem_read_observed", "filesystem_write_attempted", "filesystem_write_observed",
            "lock_release_confirmed", "unreleased_handle_count", "unreleased_native_allocation_count",
            "canonical_latest_authorized", "canonical_pass_authorized",
            "storage_origin_authenticated", "r2_ready_claimed", "receipt_is_authority",
            "consumer_revalidation_required", "post_return_state_guaranteed", "public_projection_sha256"}
        if not isinstance(value, Mapping) or set(value) != fields:
            raise ValueError("public projection fields are incomplete or unknown")
        if value["schema_version"] != SCHEMA_VERSION or value["record_type"] != cls.RECORD_TYPE:
            raise ValueError("public projection identity is invalid")
        try:
            Operation(value["operation"]); StoreDecision(value["decision"])
            RenameState(value["rename_state"]); NamespaceState(value["namespace_state"])
            PendingState(value["global_pending_state"])
            ContentState(value["content_state"]); ResourceObservationState(value["resource_observation_state"])
            ResourceReleaseState(value["resource_release_state"]); PendingState(value["pending_state"])
            ChainState(value["chain_state"]); CommitState(value["commit_state"])
        except (TypeError, ValueError) as exc:
            raise ValueError("public projection state is invalid") from exc
        reasons = value["reason_codes"]
        if (not isinstance(reasons, list) or not 1 <= len(reasons) <= 16 or
                any(not isinstance(item, str) or not re.fullmatch(r"[A-Z0-9_]{1,96}", item) for item in reasons) or
                len(set(reasons)) != len(reasons)):
            raise ValueError("public projection reasons are invalid")
        for field, maximum in (("entry_count", 256), ("pending_count", 8)):
            item = value[field]
            if isinstance(item, bool) or not isinstance(item, int) or not 0 <= item <= maximum:
                raise ValueError(f"public {field} is invalid")
        for field in ("lock_acquired", "filesystem_read_attempted", "filesystem_read_observed",
                      "filesystem_write_attempted", "filesystem_write_observed", "lock_release_confirmed"):
            if type(value[field]) is not bool:
                raise ValueError(f"public {field} is invalid")
        for field, maximum in (("unreleased_handle_count", _MAX_RETAINED_HANDLES),
                               ("unreleased_native_allocation_count", 64)):
            if (isinstance(value[field], bool) or not isinstance(value[field], int)
                    or not 0 <= value[field] <= maximum):
                raise ValueError(f"public {field} is invalid")
        for field in ("canonical_latest_authorized", "canonical_pass_authorized",
                      "storage_origin_authenticated", "r2_ready_claimed"):
            if value[field] is not False:
                raise ValueError("public projection exceeds R1B authority")
        if (value["receipt_is_authority"] is not False or
                value["consumer_revalidation_required"] is not True or
                value["post_return_state_guaranteed"] is not False):
            raise ValueError("public projection persistence boundary is invalid")
        if (value["unreleased_handle_count"] or value["unreleased_native_allocation_count"] or
                not value["lock_release_confirmed"]) and value[
                "resource_release_state"] == ResourceReleaseState.RELEASE_CONFIRMED.value:
            raise ValueError("public release matrix is invalid")
        _validate_decision_matrix(value)
        expected = _digest_without(value, "public_projection_sha256", _PUBLIC_DOMAIN)
        if value["public_projection_sha256"] != expected:
            raise ValueError("public projection digest mismatch")
        return cls(value, _token=_TOKEN)


@dataclass(slots=True)
class _Outcome:
    operation: Operation
    decision: StoreDecision = StoreDecision.BLOCKED
    reasons: tuple[str, ...] = ("UNINITIALIZED",)
    entry_revision: int | None = None
    entry_count: int = 0
    final_count: int = 0
    pending_count: int = 0
    chain_disk_bytes: int = 0
    pending_disk_bytes: int = 0
    stored_entry_sha256: str | None = None
    expected_cas_sha256: str | None = None
    rename: RenameState = RenameState.NOT_ATTEMPTED
    namespace: NamespaceState = NamespaceState.NOT_OBSERVED
    content: ContentState = ContentState.NOT_OBSERVED
    observation: ResourceObservationState = ResourceObservationState.NOT_OBSERVED
    release: ResourceReleaseState = ResourceReleaseState.RELEASE_CONFIRMED
    pending: PendingState = PendingState.UNKNOWN
    global_pending: PendingState = PendingState.UNKNOWN
    chain: ChainState = ChainState.NOT_OBSERVED
    commit: CommitState = CommitState.NOT_COMMITTED
    lock_acquired: bool = False
    read_attempted: bool = False
    read: bool = False
    write_attempted: bool = False
    write: bool = False
    recovery: Any = None
    lock_release_confirmed: bool = True
    unreleased_handle_count: int = 0
    unreleased_native_allocation_count: int = 0


def _receipt(outcome: _Outcome, key_sha: str) -> AudioCompletionLedgerStoreReceipt:
    body = {"schema_version": SCHEMA_VERSION, "record_type": AudioCompletionLedgerStoreReceipt.RECORD_TYPE,
        "task_owner": "TASK-041", "operation": outcome.operation.value, "decision": outcome.decision.value,
        "reason_codes": list(outcome.reasons), "ledger_key_sha256": key_sha,
        "entry_count": outcome.entry_count, "pending_count": outcome.pending_count,
        "chain_disk_bytes": outcome.chain_disk_bytes, "pending_disk_bytes": outcome.pending_disk_bytes,
        "stored_entry_sha256": outcome.stored_entry_sha256, "expected_cas_sha256": outcome.expected_cas_sha256,
        "rename_state": outcome.rename.value, "namespace_state": outcome.namespace.value,
        "global_pending_state": outcome.global_pending.value,
        "content_state": outcome.content.value, "resource_observation_state": outcome.observation.value,
        "resource_release_state": outcome.release.value, "pending_state": outcome.pending.value,
        "chain_state": outcome.chain.value, "commit_state": outcome.commit.value,
        "lock_acquired": outcome.lock_acquired,
        "filesystem_read_attempted": outcome.read_attempted,
        "filesystem_read_observed": outcome.read,
        "filesystem_write_attempted": outcome.write_attempted,
        "filesystem_write_observed": outcome.write,
        "lock_release_confirmed": outcome.lock_release_confirmed,
        "unreleased_handle_count": outcome.unreleased_handle_count,
        "unreleased_native_allocation_count": outcome.unreleased_native_allocation_count,
        "directory_flush_claimed": False,
        "power_loss_durability_claimed": False, "worm_claimed": False,
        "owner_death_detected": False, "receipt_is_authority": False,
        "consumer_revalidation_required": True, "post_return_state_guaranteed": False,
        "authority_flags": dict(_AUTHORITY_FLAGS)}
    body["receipt_sha256"] = _digest_without(body, "receipt_sha256", _RECEIPT_DOMAIN)
    return AudioCompletionLedgerStoreReceipt.from_dict(body)


def _key(value: AudioCompletionLedgerKeyBinding) -> AudioCompletionLedgerKeyBinding:
    if type(value) is not AudioCompletionLedgerKeyBinding:
        raise TypeError("key must be an exact R1A ledger key")
    return AudioCompletionLedgerKeyBinding.from_dict(value.to_dict())


def _cas(value: AudioCompletionLedgerCasExpectation) -> AudioCompletionLedgerCasExpectation:
    if type(value) is not AudioCompletionLedgerCasExpectation:
        raise TypeError("expectation must be an exact R1A CAS expectation")
    return AudioCompletionLedgerCasExpectation.from_dict(value.to_dict())


def _canonical_final_name(key_sha: str, revision: int) -> str:
    validate_sha256(key_sha, field_name="ledger_key_sha256")
    if isinstance(revision, bool) or not 1 <= revision <= _MAX_ENTRIES + 1:
        raise ValueError("revision outside direct-probe range")
    return f"{key_sha.removeprefix('sha256:')}-{revision:08d}.json"


def _pending_name(token_sha: str) -> str:
    validate_sha256(token_sha, field_name="token_sha256")
    return f".pending-{token_sha.removeprefix('sha256:')}.json"


def _stored_payload(*, entry: AudioCompletionLedgerEntryEnvelope, expectation_sha: str,
                    token_sha: str, root_sha: str) -> tuple[dict[str, Any], bytes]:
    entry_body = AudioCompletionLedgerEntryEnvelope.from_dict(entry.to_dict()).to_dict()
    body = {"schema_version": SCHEMA_VERSION, "record_type": "AudioCompletionStoredLedgerEntry",
        "task_owner": "TASK-041", "ledger_key_sha256": entry_body["ledger_key_sha256"],
        "entry_revision": entry_body["entry_revision"], "entry_envelope": entry_body,
        "r1a_entry_sha256": entry_body["entry_sha256"], "expected_cas_sha256": expectation_sha,
        "token_sha256": token_sha, "root_identity_sha256": root_sha,
        "storage_origin_authenticated": False, "canonical_latest_authorized": False,
        "canonical_pass_authorized": False, "power_loss_durability_claimed": False,
        "worm_claimed": False, "r2_ready_claimed": False}
    body["stored_entry_sha256"] = _digest_without(body, "stored_entry_sha256", _STORED_DOMAIN)
    encoded = canonical_json_bytes(body) + b"\n"
    if len(canonical_json_bytes(entry_body)) > _MAX_ENTRY_BYTES or len(encoded) > _MAX_STORED_BYTES:
        raise ValueError("stored entry exceeds the byte bound")
    return body, encoded


def _parse_stored(payload: bytes) -> tuple[dict[str, Any], AudioCompletionLedgerEntryEnvelope]:
    if type(payload) is not bytes or not payload.endswith(b"\n") or len(payload) > _MAX_STORED_BYTES:
        raise ValueError("stored bytes are not exact bounded LF JSON")
    if payload[:-1].endswith((b"\r", b"\n")):
        raise ValueError("stored bytes have a noncanonical line ending")
    try:
        value = json.loads(payload[:-1].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("stored bytes are not canonical JSON") from exc
    fields = {"schema_version", "record_type", "task_owner", "ledger_key_sha256", "entry_revision",
        "entry_envelope", "r1a_entry_sha256", "expected_cas_sha256", "token_sha256",
        "root_identity_sha256", "storage_origin_authenticated", "canonical_latest_authorized",
        "canonical_pass_authorized", "power_loss_durability_claimed", "worm_claimed",
        "r2_ready_claimed", "stored_entry_sha256"}
    if not isinstance(value, dict) or set(value) != fields or canonical_json_bytes(value) + b"\n" != payload:
        raise ValueError("stored wrapper is noncanonical or has unknown fields")
    if value["schema_version"] != SCHEMA_VERSION or value["record_type"] != "AudioCompletionStoredLedgerEntry" or value["task_owner"] != "TASK-041":
        raise ValueError("stored wrapper identity is invalid")
    entry = AudioCompletionLedgerEntryEnvelope.from_dict(value["entry_envelope"])
    entry_body = entry.to_dict()
    if (value["ledger_key_sha256"] != entry_body["ledger_key_sha256"] or
            value["entry_revision"] != entry_body["entry_revision"] or
            value["r1a_entry_sha256"] != entry_body["entry_sha256"]):
        raise ValueError("stored wrapper and R1A entry differ")
    for field in ("expected_cas_sha256", "token_sha256", "root_identity_sha256", "stored_entry_sha256"):
        validate_sha256(value[field], field_name=field)
    for field in ("storage_origin_authenticated", "canonical_latest_authorized", "canonical_pass_authorized",
                  "power_loss_durability_claimed", "worm_claimed", "r2_ready_claimed"):
        if value[field] is not False:
            raise ValueError("stored wrapper exceeds R1B authority")
    if value["stored_entry_sha256"] != _digest_without(value, "stored_entry_sha256", _STORED_DOMAIN):
        raise ValueError("stored wrapper digest mismatch")
    return value, entry


@dataclass(slots=True)
class _LockedSession:
    port: Any
    handles: list[int]
    root: int | None = None
    lock_handle: int | None = None
    root_sha: str | None = None
    volume_serial: int | None = None
    acquired: bool = False
    lock_was_acquired: bool = False
    release: ResourceReleaseState = ResourceReleaseState.RELEASE_CONFIRMED
    initial_root_identity: Any = None
    initial_lock_identity: Any = None
    lock_release_confirmed: bool = True

    def open(self) -> None:
        volume = self.port.open_volume_root(); self.handles.append(volume)
        current = volume
        expected_parts = _windows.PRODUCTION_LEDGER_ROOT.parts[1:]
        prior_identity = self.port.identity(volume, security_role="ancestor")
        volume_serial = prior_identity.volume_serial
        expected_path = PureWindowsPath(_windows.PRODUCTION_LEDGER_ROOT.anchor)
        if (_canonical_handle_path(prior_identity.final_path).casefold() != str(expected_path).casefold() or
                not prior_identity.attributes & 0x10):
            raise _windows.NativePortError("CANONICAL_PATH_MISMATCH")
        for index, component in enumerate(expected_parts):
            current = self.port.open_relative(current, component, kind="directory")
            self.handles.append(current)
            role = "private_root" if index == len(expected_parts) - 1 else "ancestor"
            identity = self.port.identity(current, security_role=role)
            expected_path /= component
            observed_path = PureWindowsPath(_canonical_handle_path(identity.final_path))
            if (identity.volume_serial != volume_serial or not identity.security_digest_material or
                    not identity.attributes & 0x10 or observed_path.name != component or
                    str(observed_path).casefold() != str(expected_path).casefold()):
                raise _windows.NativePortError("ROOT_IDENTITY_POLICY_FAILED")
        self.root = current; self.volume_serial = volume_serial
        root_identity = self.port.identity(current, security_role="private_root")
        self.initial_root_identity = root_identity
        self.root_sha = sha256_bytes(_ROOT_DOMAIN + canonical_json_bytes({
            "volume_serial": root_identity.volume_serial,
            "file_id": root_identity.file_id.hex(),
            "final_path": root_identity.final_path,
            "security": root_identity.security_digest_material.hex()}))
        lock_handle = self.port.open_relative(current, ".global.lock", kind="lock")
        self.handles.append(lock_handle); self.lock_handle = lock_handle
        lock_identity = self.port.identity(lock_handle, security_role="private_child")
        self.initial_lock_identity = lock_identity
        if (lock_identity.volume_serial != volume_serial or lock_identity.link_count != 1 or
                lock_identity.size != 0 or lock_identity.attributes & 0x10 or
                PureWindowsPath(_canonical_handle_path(lock_identity.final_path)).name != ".global.lock" or
                not lock_identity.security_digest_material):
            raise _windows.NativePortError("LOCK_ANCHOR_POLICY_FAILED")
        self.port.lock(lock_handle); self.acquired = True; self.lock_was_acquired = True
        if (self.port.identity(current, security_role="private_root") != root_identity or
                self.port.identity(lock_handle, security_role="private_child") != lock_identity):
            raise _windows.NativePortError("LOCK_COORDINATE_CHANGED")

    def reverify(self) -> None:
        if (self.root is None or self.lock_handle is None or
                self.port.identity(self.root, security_role="private_root") != self.initial_root_identity or
                self.port.identity(self.lock_handle, security_role="private_child") != self.initial_lock_identity):
            raise _windows.NativePortError("LOCK_COORDINATE_CHANGED")

    def close_handle(self, handle: int) -> bool:
        try:
            self.port.close(handle)
        except Exception:
            return False
        try:
            self.handles.remove(handle)
        except ValueError:
            pass
        return True

    def close(self) -> None:
        failures = 0
        if self.acquired and self.lock_handle is not None:
            try:
                self.port.unlock(self.lock_handle)
            except Exception:
                failures += 1
                self.lock_release_confirmed = False
            else:
                self.acquired = False
        for handle in tuple(reversed(self.handles)):
            if not self.close_handle(handle):
                failures += 1
        self.release = ResourceReleaseState.RELEASE_CONFIRMED if failures == 0 else ResourceReleaseState.INCOMPLETE

    def native_resource_counts(self) -> tuple[int, int]:
        reporter = getattr(self.port, "resource_counts", None)
        if not callable(reporter):
            return len(self.handles), 0
        try:
            handles, allocations = reporter()
        except Exception:
            return max(len(self.handles), 1), 1
        if (isinstance(handles, bool) or not isinstance(handles, int) or handles < 0 or
                isinstance(allocations, bool) or not isinstance(allocations, int) or allocations < 0):
            return max(len(self.handles), 1), 1
        return max(len(self.handles), min(handles, _MAX_RETAINED_HANDLES)), min(allocations, 64)


@dataclass(frozen=True, slots=True)
class _Namespace:
    entries: tuple[AudioCompletionLedgerEntryEnvelope, ...]
    final_payloads: Mapping[int, bytes]
    final_file_ids: Mapping[int, bytes]
    pending_payloads: Mapping[str, bytes]
    pending_file_ids: Mapping[str, bytes]
    pending_handles: Mapping[str, int]
    pending_faults: Mapping[str, str]
    final_count: int
    pending_count: int
    chain_bytes: int
    pending_bytes: int


def _canonical_handle_path(value: str) -> str:
    if not isinstance(value, str) or value.startswith("\\\\?\\UNC\\"):
        raise _windows.NativePortError("CANONICAL_PATH_MISMATCH")
    if value.startswith("\\\\?\\"):
        value = value[4:]
    return str(PureWindowsPath(value))


def _read_verified_relative(session: _LockedSession, name: str, kind: str,
                            listed_file_id: bytes | None = None) -> tuple[bytes, Any, int]:
    handle = session.port.open_relative(session.root, name, kind=kind)
    session.handles.append(handle)
    identity = session.port.identity(handle, security_role="private_child")
    if (identity.volume_serial != session.volume_serial or identity.link_count != 1 or
            not identity.security_digest_material or (listed_file_id is not None and identity.file_id != listed_file_id)):
        raise _windows.NativePortError("RELATIVE_REOPEN_IDENTITY_FAILED")
    return session.port.read_all(handle, maximum=_MAX_STORED_BYTES), identity, handle


def _scan(session: _LockedSession, key: AudioCompletionLedgerKeyBinding, *,
          retained_pending: Mapping[str, tuple[int, bytes, bytes]] | None = None) -> _Namespace:
    listed = session.port.enumerate_relative(session.root, max_entries=274)
    seen_casefold: set[str] = set()
    final_payloads: dict[int, bytes] = {}
    final_file_ids: dict[int, bytes] = {}
    pending_payloads: dict[str, bytes] = {}
    pending_file_ids: dict[str, bytes] = {}
    pending_handles: dict[str, int] = {}
    pending_faults: dict[str, str] = {}
    retained_pending = {} if retained_pending is None else dict(retained_pending)
    final_total = pending_total = final_count = pending_count = 0
    key_hex = key.to_dict()["ledger_key_sha256"].removeprefix("sha256:")
    lock_anchor_seen = False
    for item in listed:
        if item.name in {".", ".."}:
            continue
        folded = item.name.casefold()
        if folded in seen_casefold:
            raise _windows.NativePortError("CASE_COLLISION")
        seen_casefold.add(folded)
        if item.name == ".global.lock":
            if (lock_anchor_seen or session.initial_lock_identity is None or
                    item.file_id != session.initial_lock_identity.file_id or
                    item.size != 0 or item.attributes & 0x10):
                raise _windows.NativePortError("LOCK_ANCHOR_ENUMERATION_MISMATCH")
            lock_anchor_seen = True
            continue
        final_match, pending_match = _FINAL_RE.fullmatch(item.name), _PENDING_RE.fullmatch(item.name)
        if final_match:
            if item.name != item.name.lower():
                raise _windows.NativePortError("NONCANONICAL_NAME")
            payload, identity, handle = _read_verified_relative(
                session, item.name, "final", item.file_id)
            if not session.close_handle(handle):
                raise _windows.NativePortError("FINAL_SCAN_HANDLE_CLOSE_FAILED")
            wrapper, entry = _parse_stored(payload)
            if final_match.group("key") != wrapper["ledger_key_sha256"].removeprefix("sha256:") or int(final_match.group("revision")) != wrapper["entry_revision"]:
                raise _windows.NativePortError("FILENAME_CONTENT_MISMATCH")
            if final_match.group("key") == key_hex:
                final_count += 1; final_total += len(payload)
                revision = int(final_match.group("revision"))
                if revision in final_payloads:
                    raise _windows.NativePortError("LEDGER_FORK")
                final_payloads[revision] = payload
                final_file_ids[revision] = identity.file_id
        elif pending_match:
            pending_count += 1
            retained = retained_pending.get(item.name)
            if item.size < 0:
                raise _windows.NativePortError("PENDING_SIZE_INVALID")
            if retained is None and item.size > _MAX_STORED_BYTES:
                # Keep a verified handle/identity observation, but do not read an
                # adversarially oversized pending wrapper into memory.  A
                # malformed pending is recoverable evidence, not permission to
                # mutate or a reason for read-only inspection to lose the rest
                # of the bounded namespace observation.
                pending_handle = session.port.open_relative(
                    session.root, item.name, kind="pending")
                session.handles.append(pending_handle)
                identity = session.port.identity(
                    pending_handle, security_role="private_child")
                if (identity.volume_serial != session.volume_serial or
                        identity.link_count != 1 or
                        not identity.security_digest_material or
                        identity.file_id != item.file_id):
                    raise _windows.NativePortError(
                        "RELATIVE_REOPEN_IDENTITY_FAILED")
                payload = b""
                pending_faults[item.name] = "OVERSIZED_PENDING"
            elif retained is None:
                payload, identity, pending_handle = _read_verified_relative(session, item.name, "pending", item.file_id)
            else:
                handle, payload, retained_file_id = retained
                pending_handle = handle
                identity = session.port.identity(handle, security_role="private_child")
                if identity.file_id != retained_file_id or item.file_id != retained_file_id:
                    raise _windows.NativePortError("RETAINED_PENDING_IDENTITY_CHANGED")
            if item.size <= _MAX_STORED_BYTES and len(payload) != item.size:
                pending_faults[item.name] = "PENDING_SIZE_CHANGED"
            pending_total += max(item.size, len(payload))
            pending_payloads[item.name] = payload
            pending_file_ids[item.name] = identity.file_id
            pending_handles[item.name] = pending_handle
            try:
                wrapper, _ = _parse_stored(payload)
                if pending_match.group("token") != wrapper["token_sha256"].removeprefix("sha256:"):
                    raise ValueError("pending token/name mismatch")
            except (KeyError, TypeError, ValueError):
                pending_faults[item.name] = "CORRUPT_OR_PARTIAL_PENDING"
        else:
            raise _windows.NativePortError("UNKNOWN_NAMESPACE_ENTRY")
    if not lock_anchor_seen:
        raise _windows.NativePortError("LOCK_ANCHOR_ENUMERATION_MISMATCH")
    if final_count > _MAX_ENTRIES or final_total > _MAX_CHAIN_DISK_BYTES:
        raise _windows.NativePortError("FINAL_NAMESPACE_BOUND_EXCEEDED")
    if pending_count > _MAX_PENDING or pending_total > _MAX_PENDING_BYTES:
        raise _windows.NativePortError("PENDING_NAMESPACE_BOUND_EXCEEDED")
    # Exact direct probes, including the 257 sentinel, are relative handle opens.
    for revision in range(1, _MAX_ENTRIES + 2):
        name = _canonical_final_name(key.to_dict()["ledger_key_sha256"], revision)
        try:
            handle = session.port.open_relative(session.root, name, kind="final")
        except _windows.NativePortError as exc:
            if exc.reason == "NOT_FOUND":
                if revision in final_payloads:
                    raise _windows.NativePortError("ENUMERATION_PROBE_MISMATCH")
                continue
            raise
        session.handles.append(handle)
        identity = session.port.identity(handle, security_role="private_child")
        if identity.volume_serial != session.volume_serial or identity.link_count != 1:
            raise _windows.NativePortError("DIRECT_PROBE_IDENTITY_FAILED")
        payload = session.port.read_all(handle, maximum=_MAX_STORED_BYTES)
        if not session.close_handle(handle):
            raise _windows.NativePortError("DIRECT_PROBE_HANDLE_CLOSE_FAILED")
        if revision == _MAX_ENTRIES + 1:
            raise _windows.NativePortError("REVISION_257_SENTINEL_PRESENT")
        if (final_payloads.get(revision) != payload or
                final_file_ids.get(revision) != identity.file_id):
            raise _windows.NativePortError("ENUMERATION_PROBE_MISMATCH")
    if final_payloads and set(final_payloads) != set(range(1, max(final_payloads) + 1)):
        raise _windows.NativePortError("LEDGER_GAP")
    parsed_entries = tuple(_parse_stored(final_payloads[index])[1] for index in sorted(final_payloads))
    validate_full_chain(parsed_entries, key)
    for index, entry in enumerate(parsed_entries):
        wrapper, _ = _parse_stored(final_payloads[index + 1])
        prefix_cas = cas_for_chain(parsed_entries[:index], key).to_dict()["expectation_sha256"]
        if (wrapper["root_identity_sha256"] != session.root_sha or
                wrapper["expected_cas_sha256"] != prefix_cas or
                wrapper["ledger_key_sha256"] != key.to_dict()["ledger_key_sha256"]):
            raise _windows.NativePortError("STORED_PREFIX_BINDING_MISMATCH")
    return _Namespace(parsed_entries, MappingProxyType(final_payloads), MappingProxyType(final_file_ids),
        MappingProxyType(pending_payloads),
        MappingProxyType(pending_file_ids), MappingProxyType(pending_handles), MappingProxyType(pending_faults),
        final_count, pending_count, final_total, pending_total)


def _recovery_receipt(*, key_sha: str, revision: int, expectation_sha: str,
                      token_sha: str, root_sha: str, file_id: bytes,
                      payload_sha: str, pending_name: str) -> AudioCompletionLedgerRecoveryReceipt:
    body = {"schema_version": SCHEMA_VERSION,
        "record_type": AudioCompletionLedgerRecoveryReceipt.RECORD_TYPE, "task_owner": "TASK-041",
        "ledger_key_sha256": key_sha, "entry_revision": revision,
        "expected_cas_sha256": expectation_sha, "token_sha256": token_sha,
        "root_identity_sha256": root_sha,
        "pending_file_identity_sha256": sha256_bytes(_FILE_ID_DOMAIN + file_id),
        "rename_continuity_file_identity_sha256": sha256_bytes(_FILE_ID_DOMAIN + file_id),
        "payload_sha256": payload_sha,
        "pending_name_sha256": sha256_bytes(pending_name.encode("ascii")),
        "receipt_is_capability": False, "resume_requires_live_revalidation": True}
    body["recovery_receipt_sha256"] = _digest_without(body, "recovery_receipt_sha256", _RECOVERY_DOMAIN)
    return AudioCompletionLedgerRecoveryReceipt.from_dict(body)


def _sync_namespace_counts(outcome: _Outcome, namespace: _Namespace) -> None:
    outcome.entry_count = len(namespace.entries); outcome.final_count = namespace.final_count
    outcome.pending_count = namespace.pending_count; outcome.chain_disk_bytes = namespace.chain_bytes
    outcome.pending_disk_bytes = namespace.pending_bytes; outcome.chain = ChainState.VALID
    outcome.global_pending = (PendingState.CORRUPT if namespace.pending_faults else
        (PendingState.NONE if namespace.pending_count == 0 else PendingState.RECOVERABLE))


def _validate_recovery_pending(payload: bytes, *, body: Mapping[str, Any],
                               key: AudioCompletionLedgerKeyBinding,
                               current_entries: Sequence[AudioCompletionLedgerEntryEnvelope],
                               validate_extension: bool = True) -> None:
    wrapper, entry = _parse_stored(payload)
    if (wrapper["ledger_key_sha256"] != body["ledger_key_sha256"] or
            wrapper["entry_revision"] != body["entry_revision"] or
            wrapper["expected_cas_sha256"] != body["expected_cas_sha256"] or
            wrapper["token_sha256"] != body["token_sha256"] or
            wrapper["root_identity_sha256"] != body["root_identity_sha256"]):
        raise _windows.NativePortError("RECOVERY_WRAPPER_BINDING_MISMATCH")
    if validate_extension:
        validate_full_chain(tuple(current_entries) + (entry,), key)


def _bind_recovery_target(outcome: _Outcome, payload: bytes, *, body: Mapping[str, Any],
                          namespace: _Namespace, pending_name: str | None,
                          key: AudioCompletionLedgerKeyBinding,
                          validate_extension: bool) -> None:
    """Revalidate all persistent recovery coordinates for an observed target."""
    _validate_recovery_pending(payload, body=body, key=key,
        current_entries=namespace.entries, validate_extension=validate_extension)
    if not hmac.compare_digest(sha256_bytes(payload), body["payload_sha256"]):
        raise _windows.NativePortError("RECOVERY_PAYLOAD_BINDING_MISMATCH")
    if pending_name is not None:
        observed_id = namespace.pending_file_ids.get(pending_name)
        if observed_id is None or not hmac.compare_digest(
                sha256_bytes(_FILE_ID_DOMAIN + observed_id), body["pending_file_identity_sha256"]):
            raise _windows.NativePortError("PENDING_FILE_ID_CHANGED")
    else:
        observed_id = namespace.final_file_ids.get(body["entry_revision"])
        if observed_id is None:
            raise _windows.NativePortError("FINAL_FILE_ID_NOT_OBSERVED")
    if not hmac.compare_digest(
            sha256_bytes(_FILE_ID_DOMAIN + observed_id),
            body["rename_continuity_file_identity_sha256"]):
        raise _windows.NativePortError("RENAME_FILE_ID_CONTINUITY_FAILED")
    wrapper, _ = _parse_stored(payload)
    outcome.entry_revision = wrapper["entry_revision"]
    outcome.stored_entry_sha256 = wrapper["stored_entry_sha256"]
    outcome.expected_cas_sha256 = wrapper["expected_cas_sha256"]


def _fresh_before_rename(session: _LockedSession, key: AudioCompletionLedgerKeyBinding, *,
                         prior: _Namespace, pending_name: str, handle: int,
                         payload: bytes, file_id: bytes, expected_cas_sha: str) -> _Namespace:
    session.reverify()
    session.port.rewind(handle)
    if session.port.read_all(handle, maximum=_MAX_STORED_BYTES) != payload:
        raise _windows.NativePortError("PENDING_PAYLOAD_CHANGED")
    identity = session.port.identity(handle, security_role="private_child")
    if identity.file_id != file_id or identity.volume_serial != session.volume_serial or identity.link_count != 1:
        raise _windows.NativePortError("PENDING_IDENTITY_CHANGED")
    retained = {name: (prior.pending_handles[name], prior.pending_payloads[name], prior.pending_file_ids[name])
        for name in prior.pending_handles}
    retained[pending_name] = (handle, payload, file_id)
    fresh = _scan(session, key, retained_pending=retained)
    if ([entry.to_dict() for entry in fresh.entries] != [entry.to_dict() for entry in prior.entries] or
            fresh.pending_payloads.get(pending_name) != payload or
            fresh.pending_file_ids.get(pending_name) != file_id or fresh.pending_faults or
            cas_for_chain(fresh.entries, key).to_dict()["expectation_sha256"] != expected_cas_sha):
        raise _windows.NativePortError("PRE_RENAME_LIVE_REVALIDATION_FAILED")
    return fresh


def _verify_after_rename(session: _LockedSession, key: AudioCompletionLedgerKeyBinding, *,
                         handle: int, original_identity: Any, final_name: str, payload: bytes,
                         prior: _Namespace, renamed_pending_name: str) -> _Namespace | None:
    moved = session.port.identity(handle, security_role="private_child")
    expected_path = PureWindowsPath(_windows.PRODUCTION_LEDGER_ROOT) / final_name
    if (moved.volume_serial != original_identity.volume_serial or moved.file_id != original_identity.file_id or
            moved.link_count != 1 or moved.security_digest_material != original_identity.security_digest_material or
            _canonical_handle_path(moved.final_path).casefold() != str(expected_path).casefold()):
        raise _windows.NativePortError("RENAMED_HANDLE_IDENTITY_FAILED")
    session.port.rewind(handle)
    if session.port.read_all(handle, maximum=_MAX_STORED_BYTES) != payload:
        raise _windows.NativePortError("RENAMED_HANDLE_READBACK_MISMATCH")
    if not session.close_handle(handle):
        return None
    reopened = session.port.open_relative(session.root, final_name, kind="final")
    session.handles.append(reopened)
    reopened_identity = session.port.identity(reopened, security_role="private_child")
    if (reopened_identity.file_id != original_identity.file_id or
            reopened_identity.volume_serial != original_identity.volume_serial or
            reopened_identity.link_count != 1 or
            reopened_identity.security_digest_material != original_identity.security_digest_material or
            session.port.read_all(reopened, maximum=_MAX_STORED_BYTES) != payload):
        raise _windows.NativePortError("FINAL_REOPEN_IDENTITY_OR_CONTENT_FAILED")
    retained = {name: (prior.pending_handles[name], prior.pending_payloads[name], prior.pending_file_ids[name])
        for name in prior.pending_handles if name != renamed_pending_name}
    fresh = _scan(session, key, retained_pending=retained)
    if (len(fresh.entries) != len(prior.entries) + 1 or
            [entry.to_dict() for entry in fresh.entries[:-1]] != [entry.to_dict() for entry in prior.entries] or
            fresh.final_payloads.get(len(fresh.entries)) != payload or
            fresh.final_file_ids.get(len(fresh.entries)) != original_identity.file_id or
            fresh.pending_faults):
        raise _windows.NativePortError("POST_RENAME_FULL_RECONCILIATION_FAILED")
    return fresh


def _reconcile_unknown_rename(session: _LockedSession, key: AudioCompletionLedgerKeyBinding,
                              *, payload: bytes, revision: int, pending_name: str,
                              handle: int, original_identity: Any,
                              prior: _Namespace, outcome: _Outcome, reason: str) -> None:
    try:
        retained_identity = session.port.identity(handle, security_role="private_child")
        session.port.rewind(handle)
        if (retained_identity.volume_serial != original_identity.volume_serial or
                retained_identity.file_id != original_identity.file_id or
                retained_identity.link_count != 1 or
                session.port.read_all(handle, maximum=_MAX_STORED_BYTES) != payload):
            raise _windows.NativePortError("UNKNOWN_RENAME_RETAINED_HANDLE_MISMATCH")
    except Exception:
        outcome.decision = StoreDecision.COMMIT_STATE_UNKNOWN; outcome.commit = CommitState.COMMIT_STATE_UNKNOWN
        _invalidate_observation(outcome); outcome.observation = ResourceObservationState.INCOMPLETE
        outcome.reasons = (reason, "UNKNOWN_RENAME_RETAINED_HANDLE_UNVERIFIED")
        return
    if not session.close_handle(handle):
        outcome.decision = StoreDecision.COMMIT_STATE_UNKNOWN; outcome.commit = CommitState.COMMIT_STATE_UNKNOWN
        _invalidate_observation(outcome); outcome.observation = ResourceObservationState.INCOMPLETE
        outcome.reasons = (reason, "UNKNOWN_RENAME_HANDLE_RELEASE_FAILED")
        return
    retained = {name: (prior.pending_handles[name], prior.pending_payloads[name], prior.pending_file_ids[name])
        for name in prior.pending_handles if name != pending_name}
    observed = _scan(session, key, retained_pending=retained); _sync_namespace_counts(outcome, observed)
    pending = observed.pending_payloads.get(pending_name)
    final = observed.final_payloads.get(revision)
    pending_exact, final_exact = pending == payload, final == payload
    outcome.reasons = (reason,)
    if final_exact and observed.final_file_ids.get(revision) != original_identity.file_id:
        outcome.decision = StoreDecision.COMMIT_STATE_UNKNOWN
        outcome.commit = CommitState.COMMIT_STATE_UNKNOWN
        outcome.namespace = NamespaceState.DIFFERENT_FINAL
        outcome.content = ContentState.CONFLICT
        outcome.pending = PendingState.AMBIGUOUS
        outcome.observation = ResourceObservationState.INCOMPLETE
        outcome.reasons = (reason, "RENAME_FILE_ID_CONTINUITY_FAILED")
        return
    if final_exact and pending is None:
        outcome.write = True
        outcome.decision = StoreDecision.INCOMPLETE; outcome.commit = CommitState.KNOWN_COMMITTED
        outcome.namespace = NamespaceState.FINAL_ONLY; outcome.content = ContentState.FINAL_VERIFIED
        outcome.pending = PendingState.NONE; outcome.observation = ResourceObservationState.FINAL_REOPEN_VERIFIED
    elif final_exact and pending_exact:
        outcome.write = True
        outcome.decision = StoreDecision.INCOMPLETE; outcome.commit = CommitState.KNOWN_COMMITTED
        outcome.namespace = NamespaceState.BOTH; outcome.content = ContentState.BOTH_IDENTICAL
        outcome.pending = PendingState.RECOVERABLE; outcome.observation = ResourceObservationState.INCOMPLETE
    elif pending_exact and final is None:
        outcome.decision = StoreDecision.INCOMPLETE; outcome.commit = CommitState.NOT_COMMITTED
        outcome.namespace = NamespaceState.PENDING_ONLY; outcome.content = ContentState.PENDING_VERIFIED
        outcome.pending = PendingState.RECOVERABLE; outcome.observation = ResourceObservationState.INCOMPLETE
    else:
        outcome.decision = StoreDecision.COMMIT_STATE_UNKNOWN; outcome.commit = CommitState.COMMIT_STATE_UNKNOWN
        outcome.namespace = (NamespaceState.NEITHER if pending is None and final is None
            else NamespaceState.DIFFERENT_FINAL)
        outcome.content = ContentState.CONFLICT if pending is not None or final is not None else ContentState.NOT_OBSERVED
        outcome.pending = PendingState.AMBIGUOUS; outcome.observation = ResourceObservationState.INCOMPLETE


_PORT_FACTORY = _windows.create_production_port


def _invalidate_observation(outcome: _Outcome) -> None:
    """Discard aggregate claims after a failed live revalidation.

    The operation/rename/commit phases remain truthful.  Counts and source
    digests are point-in-time namespace observations and therefore cannot be
    retained when the post-scan coordinate or post-rename verification fails.
    """
    outcome.entry_revision = None
    outcome.entry_count = outcome.final_count = outcome.pending_count = 0
    outcome.chain_disk_bytes = outcome.pending_disk_bytes = 0
    outcome.stored_entry_sha256 = outcome.expected_cas_sha256 = None
    outcome.namespace = NamespaceState.NOT_OBSERVED
    outcome.content = ContentState.NOT_OBSERVED
    outcome.pending = PendingState.UNKNOWN
    outcome.global_pending = PendingState.UNKNOWN
    outcome.chain = ChainState.NOT_OBSERVED


def _execute_locked(key: AudioCompletionLedgerKeyBinding, operation: Operation, action: Any) -> tuple[AudioCompletionLedgerStoreReceipt, AudioCompletionLedgerRecoveryReceipt | None]:
    key = _key(key); key_sha = key.to_dict()["ledger_key_sha256"]
    outcome = _Outcome(operation=operation)
    recovery: AudioCompletionLedgerRecoveryReceipt | None = None
    try:
        port = _PORT_FACTORY()
    except _windows.NativePortError as exc:
        outcome.reasons = (exc.reason,)
        return _receipt(outcome, key_sha), None
    except Exception:
        outcome.reasons = ("UNEXPECTED_NATIVE_FAULT",)
        return _receipt(outcome, key_sha), None
    session = _LockedSession(port, [])
    try:
        outcome.read_attempted = True
        session.open(); outcome.lock_acquired = session.acquired
        outcome.read = True
        namespace = _scan(session, key)
        _sync_namespace_counts(outcome, namespace)
        outcome.namespace = (NamespaceState.FINAL_ONLY if namespace.final_count else NamespaceState.NEITHER)
        outcome.pending = outcome.global_pending
        outcome.content = (ContentState.FINAL_VERIFIED if namespace.final_count else
            (ContentState.CORRUPT if namespace.pending_faults else
             (ContentState.PENDING_VERIFIED if namespace.pending_count else ContentState.NOT_OBSERVED)))
        session.reverify()
        recovery = action(session, namespace, outcome)
        session.reverify()
    except _windows.NativePortError as exc:
        if outcome.commit is CommitState.KNOWN_COMMITTED:
            outcome.decision = StoreDecision.INCOMPLETE
            outcome.observation = ResourceObservationState.INCOMPLETE
        else:
            outcome.decision = StoreDecision.COMMIT_STATE_UNKNOWN if exc.completion_unknown else StoreDecision.BLOCKED
        outcome.reasons = (exc.reason,)
        _invalidate_observation(outcome)
        if exc.completion_unknown and outcome.commit is not CommitState.KNOWN_COMMITTED:
            outcome.rename = RenameState.SYSCALL_COMPLETION_UNKNOWN
            outcome.commit = CommitState.COMMIT_STATE_UNKNOWN
    except (KeyError, TypeError, ValueError):
        outcome.decision = StoreDecision.INCOMPLETE if outcome.commit is CommitState.KNOWN_COMMITTED else StoreDecision.BLOCKED
        outcome.reasons = ("INVALID_OR_CORRUPT_LEDGER_CONTENT",)
        if outcome.commit is CommitState.KNOWN_COMMITTED:
            outcome.observation = ResourceObservationState.INCOMPLETE
        _invalidate_observation(outcome); outcome.chain = ChainState.INVALID
    except Exception:
        outcome.decision = StoreDecision.INCOMPLETE if outcome.commit is CommitState.KNOWN_COMMITTED else StoreDecision.BLOCKED
        outcome.reasons = ("UNEXPECTED_NATIVE_FAULT",)
        if outcome.commit is CommitState.KNOWN_COMMITTED:
            outcome.observation = ResourceObservationState.INCOMPLETE
        _invalidate_observation(outcome)
    finally:
        outcome.lock_acquired = outcome.lock_acquired or session.lock_was_acquired
        if not outcome.read and session.handles:
            outcome.read = True
        session.close(); outcome.release = session.release
        outcome.lock_release_confirmed = session.lock_release_confirmed
        handles, allocations = session.native_resource_counts()
        outcome.unreleased_handle_count = handles
        outcome.unreleased_native_allocation_count = allocations
        if handles or allocations:
            outcome.release = ResourceReleaseState.INCOMPLETE
        if outcome.release is not ResourceReleaseState.RELEASE_CONFIRMED:
            if outcome.decision in {StoreDecision.OBSERVED, StoreDecision.APPENDED,
                    StoreDecision.ALREADY_COMMITTED_RECONCILED, StoreDecision.RECOVERY_AVAILABLE,
                    StoreDecision.NOT_COMMITTED}:
                outcome.decision = StoreDecision.INCOMPLETE
            outcome.reasons = tuple(dict.fromkeys((*outcome.reasons, "RESOURCE_RELEASE_INCOMPLETE")))
    return _receipt(outcome, key_sha), recovery if recovery is not None else outcome.recovery


def observe_ledger(key: AudioCompletionLedgerKeyBinding) -> AudioCompletionLedgerStoreReceipt:
    def action(session: _LockedSession, namespace: _Namespace, outcome: _Outcome) -> None:
        del session
        outcome.decision = StoreDecision.OBSERVED
        outcome.reasons = ("POINT_IN_TIME_NAMESPACE_OBSERVED",)
        if outcome.entry_count:
            wrapper, _ = _parse_stored(namespace.final_payloads[outcome.entry_count])
            outcome.entry_revision = wrapper["entry_revision"]
            outcome.stored_entry_sha256 = wrapper["stored_entry_sha256"]
            outcome.expected_cas_sha256 = wrapper["expected_cas_sha256"]
            outcome.namespace = NamespaceState.FINAL_ONLY
            outcome.content = ContentState.FINAL_VERIFIED
            outcome.observation = ResourceObservationState.FINAL_REOPEN_VERIFIED
        else:
            outcome.namespace = NamespaceState.NEITHER
            outcome.content = ContentState.NOT_OBSERVED
            outcome.observation = ResourceObservationState.NOT_OBSERVED
        outcome.pending = PendingState.NONE
        return None
    return _execute_locked(_key(key), Operation.OBSERVE, action)[0]


def append_prepared(prepared: PreparedAudioCompletionAppend) -> tuple[AudioCompletionLedgerStoreReceipt, AudioCompletionLedgerRecoveryReceipt | None]:
    snapshot = _RESOLVE_PREPARED(prepared)
    if snapshot is None:
        raise TypeError("prepared must be an exact sealed prepared append")
    key, candidate, expectation, token = snapshot
    token_sha = _token_hash(token)

    def action(session: _LockedSession, namespace: _Namespace, outcome: _Outcome) -> AudioCompletionLedgerRecoveryReceipt | None:
        evaluation = evaluate_append(namespace.entries, candidate, expectation)
        evaluation_decision = evaluation.to_dict()["decision"]
        if evaluation_decision == AppendDecision.IDEMPOTENT_LATEST_MATCH_NOT_AUTHORIZED.value:
            latest_revision = len(namespace.entries)
            latest_payload = namespace.final_payloads.get(latest_revision)
            if latest_payload is None:
                raise _windows.NativePortError("IDEMPOTENT_FINAL_MISSING")
            wrapper, latest_entry = _parse_stored(latest_payload)
            if latest_entry.to_dict()["candidate_receipt_sha256"] != candidate.to_dict()["receipt_sha256"]:
                raise _windows.NativePortError("IDEMPOTENT_FINAL_MISMATCH")
            outcome.entry_revision = latest_revision; outcome.stored_entry_sha256 = wrapper["stored_entry_sha256"]
            outcome.expected_cas_sha256 = wrapper["expected_cas_sha256"]
            outcome.decision = StoreDecision.ALREADY_COMMITTED_RECONCILED
            outcome.reasons = ("EXACT_LATEST_REPLAY_RECONCILED",)
            outcome.commit = CommitState.KNOWN_COMMITTED
            outcome.namespace = NamespaceState.FINAL_ONLY
            outcome.content = ContentState.FINAL_VERIFIED
            outcome.pending = PendingState.NONE
            outcome.observation = ResourceObservationState.FINAL_REOPEN_VERIFIED
            return None
        if evaluation_decision != AppendDecision.CONTRACT_APPEND_ELIGIBLE_NOT_AUTHORIZED.value:
            outcome.decision = StoreDecision.BLOCKED
            outcome.reasons = (evaluation_decision,)
            return None
        prior = None if not namespace.entries else namespace.entries[-1]
        entry = make_entry_envelope(candidate, key=key, previous_entry=prior)
        revision = entry.to_dict()["entry_revision"]
        outcome.entry_revision = revision; outcome.expected_cas_sha256 = expectation.to_dict()["expectation_sha256"]
        body, payload = _stored_payload(entry=entry, expectation_sha=outcome.expected_cas_sha256,
            token_sha=token_sha, root_sha=session.root_sha)
        payload_sha = sha256_bytes(payload); outcome.stored_entry_sha256 = body["stored_entry_sha256"]
        final_name, pending_name = _canonical_final_name(key.to_dict()["ledger_key_sha256"], revision), _pending_name(token_sha)
        existing_final = namespace.final_payloads.get(revision)
        existing_pending = namespace.pending_payloads.get(pending_name)
        if existing_final is not None:
            if existing_final == payload:
                outcome.decision = StoreDecision.ALREADY_COMMITTED_RECONCILED
                outcome.reasons = ("EXACT_LATEST_REPLAY_RECONCILED",); outcome.commit = CommitState.KNOWN_COMMITTED
                outcome.namespace = NamespaceState.FINAL_ONLY; outcome.content = ContentState.FINAL_VERIFIED
                outcome.pending = PendingState.NONE
                outcome.observation = ResourceObservationState.FINAL_REOPEN_VERIFIED
            else:
                outcome.decision = StoreDecision.BLOCKED; outcome.reasons = ("DIFFERENT_FINAL_PRESENT",)
                outcome.namespace = NamespaceState.DIFFERENT_FINAL; outcome.content = ContentState.CONFLICT
            return None
        if existing_pending is not None:
            if pending_name in namespace.pending_faults or existing_pending != payload:
                outcome.decision = StoreDecision.BLOCKED; outcome.reasons = ("DIFFERENT_OR_CORRUPT_PENDING_CONFLICT",)
                outcome.namespace = NamespaceState.PENDING_ONLY; outcome.content = ContentState.CONFLICT
                outcome.pending = PendingState.CORRUPT if pending_name in namespace.pending_faults else PendingState.AMBIGUOUS
                return None
            file_id = namespace.pending_file_ids[pending_name]
            _validate_recovery_pending(existing_pending, body={
                "ledger_key_sha256": key.to_dict()["ledger_key_sha256"], "entry_revision": revision,
                "expected_cas_sha256": outcome.expected_cas_sha256, "token_sha256": token_sha,
                "root_identity_sha256": session.root_sha}, key=key, current_entries=namespace.entries)
            recovery = _recovery_receipt(key_sha=key.to_dict()["ledger_key_sha256"], revision=revision,
                expectation_sha=outcome.expected_cas_sha256, token_sha=token_sha,
                root_sha=session.root_sha, file_id=file_id, payload_sha=payload_sha,
                pending_name=pending_name)
            outcome.decision = StoreDecision.RECOVERY_AVAILABLE; outcome.reasons = ("EXACT_PENDING_PRESENT",)
            outcome.namespace = NamespaceState.PENDING_ONLY; outcome.content = ContentState.PENDING_VERIFIED
            outcome.pending = PendingState.RECOVERABLE
            return recovery
        if namespace.pending_faults:
            outcome.decision = StoreDecision.BLOCKED; outcome.reasons = ("CORRUPT_PENDING_REQUIRES_RECOVERY",)
            outcome.namespace = NamespaceState.PENDING_ONLY; outcome.content = ContentState.CORRUPT
            outcome.pending = PendingState.CORRUPT; return None
        # Bounds are rechecked while the global lock is held, immediately before CREATE_NEW.
        if namespace.pending_count + 1 > _MAX_PENDING or namespace.pending_bytes + len(payload) > _MAX_PENDING_BYTES:
            raise _windows.NativePortError("PENDING_NAMESPACE_BOUND_EXCEEDED")
        if namespace.final_count + 1 > _MAX_ENTRIES or namespace.chain_bytes + len(payload) > _MAX_CHAIN_DISK_BYTES:
            raise _windows.NativePortError("FINAL_NAMESPACE_BOUND_EXCEEDED")
        outcome.write_attempted = True
        handle = session.port.open_relative(session.root, pending_name, kind="pending", create=True)
        session.handles.append(handle)
        outcome.write = True
        outcome.pending_count += 1; outcome.namespace = NamespaceState.PENDING_ONLY
        outcome.global_pending = PendingState.UNKNOWN
        outcome.pending = PendingState.UNKNOWN
        identity = session.port.identity(handle, security_role="private_child")
        if identity.volume_serial != session.volume_serial or identity.link_count != 1:
            raise _windows.NativePortError("PENDING_CREATE_IDENTITY_FAILED")
        session.port.write_all(handle, payload); outcome.pending_disk_bytes += len(payload)
        session.port.flush_file(handle)
        outcome.observation = ResourceObservationState.FILE_FLUSH_RETURNED_TRUE
        session.port.rewind(handle)
        if session.port.read_all(handle, maximum=_MAX_STORED_BYTES) != payload:
            raise _windows.NativePortError("PENDING_READBACK_MISMATCH")
        outcome.content = ContentState.PENDING_VERIFIED; outcome.pending = PendingState.RECOVERABLE
        outcome.global_pending = PendingState.RECOVERABLE
        recovery = _recovery_receipt(key_sha=key.to_dict()["ledger_key_sha256"], revision=revision,
            expectation_sha=outcome.expected_cas_sha256, token_sha=token_sha,
            root_sha=session.root_sha, file_id=identity.file_id, payload_sha=payload_sha,
            pending_name=pending_name)
        outcome.recovery = recovery
        _fresh_before_rename(session, key, prior=namespace, pending_name=pending_name,
            handle=handle, payload=payload, file_id=identity.file_id,
            expected_cas_sha=outcome.expected_cas_sha256)
        try:
            session.port.rename_no_replace(handle, session.root, final_name)
        except _windows.NativePortError as exc:
            outcome.rename = RenameState.SYSCALL_COMPLETION_UNKNOWN if exc.completion_unknown else RenameState.RETURNED_FALSE
            if exc.completion_unknown:
                _reconcile_unknown_rename(session, key, payload=payload, revision=revision,
                    pending_name=pending_name, handle=handle, original_identity=identity,
                    prior=namespace, outcome=outcome, reason=exc.reason)
            else:
                outcome.namespace = NamespaceState.PENDING_ONLY; outcome.content = ContentState.PENDING_VERIFIED
                outcome.pending = PendingState.RECOVERABLE; outcome.commit = CommitState.NOT_COMMITTED
                outcome.decision = StoreDecision.INCOMPLETE; outcome.reasons = (exc.reason,)
            return recovery
        outcome.rename = RenameState.RETURNED_TRUE; outcome.commit = CommitState.KNOWN_COMMITTED
        outcome.namespace = NamespaceState.FINAL_ONLY; outcome.pending = PendingState.NONE
        verified = _verify_after_rename(session, key, handle=handle, original_identity=identity,
            final_name=final_name, payload=payload, prior=namespace, renamed_pending_name=pending_name)
        if verified is None:
            outcome.decision = StoreDecision.INCOMPLETE; outcome.reasons = ("RENAMED_HANDLE_RELEASE_FAILED",)
            _invalidate_observation(outcome)
            outcome.observation = ResourceObservationState.INCOMPLETE
            return recovery
        _sync_namespace_counts(outcome, verified)
        outcome.namespace = NamespaceState.FINAL_ONLY
        outcome.pending = PendingState.NONE
        outcome.decision = StoreDecision.APPENDED; outcome.reasons = ("NO_REPLACE_APPEND_OBSERVED",)
        outcome.content = ContentState.FINAL_VERIFIED; outcome.observation = ResourceObservationState.FINAL_REOPEN_VERIFIED
        return recovery
    return _execute_locked(key, Operation.APPEND, action)


def _validated_recovery(value: AudioCompletionLedgerRecoveryReceipt, token: bytes) -> tuple[dict[str, Any], str]:
    if type(value) is not AudioCompletionLedgerRecoveryReceipt:
        raise TypeError("recovery must be an exact sealed recovery receipt")
    body = AudioCompletionLedgerRecoveryReceipt.from_dict(value.to_dict()).to_dict()
    supplied_hash = _token_hash(token)
    if not hmac.compare_digest(supplied_hash, body["token_sha256"]):
        raise ValueError("recovery token does not match")
    return body, _pending_name(supplied_hash)


def inspect_pending(*, key: AudioCompletionLedgerKeyBinding,
                    recovery: AudioCompletionLedgerRecoveryReceipt,
                    token: bytes) -> AudioCompletionLedgerStoreReceipt:
    body, pending_name = _validated_recovery(recovery, token); key = _key(key)
    def action(session: _LockedSession, namespace: _Namespace, outcome: _Outcome) -> None:
        if body["ledger_key_sha256"] != key.to_dict()["ledger_key_sha256"] or body["root_identity_sha256"] != session.root_sha:
            raise _windows.NativePortError("RECOVERY_LIVE_BINDING_MISMATCH")
        pending, final = namespace.pending_payloads.get(pending_name), namespace.final_payloads.get(body["entry_revision"])
        expected_sha = body["payload_sha256"]
        pending_exact = pending is not None and hmac.compare_digest(sha256_bytes(pending), expected_sha)
        final_exact = final is not None and hmac.compare_digest(sha256_bytes(final), expected_sha)
        if pending_exact:
            _bind_recovery_target(outcome, pending, body=body, namespace=namespace,
                pending_name=pending_name, key=key, validate_extension=final is None)
        if final_exact:
            _bind_recovery_target(outcome, final, body=body, namespace=namespace,
                pending_name=None, key=key, validate_extension=False)
        current_cas_sha = cas_for_chain(namespace.entries, key).to_dict()["expectation_sha256"]
        if pending_exact and final is None and not hmac.compare_digest(current_cas_sha, body["expected_cas_sha256"]):
            outcome.decision = StoreDecision.BLOCKED; outcome.reasons = ("RECOVERY_CAS_STALE",)
            outcome.namespace = NamespaceState.PENDING_ONLY; outcome.content = ContentState.PENDING_VERIFIED
            outcome.pending = PendingState.STALE; return None
        if pending_exact and not final:
            outcome.decision = StoreDecision.RECOVERY_AVAILABLE; outcome.reasons = ("PENDING_ONLY_EXACT",)
            outcome.namespace = NamespaceState.PENDING_ONLY; outcome.content = ContentState.PENDING_VERIFIED
            outcome.pending = PendingState.RECOVERABLE
        elif final_exact and not pending:
            outcome.decision = StoreDecision.ALREADY_COMMITTED_RECONCILED; outcome.reasons = ("FINAL_ONLY_EXACT",)
            outcome.namespace = NamespaceState.FINAL_ONLY; outcome.content = ContentState.FINAL_VERIFIED
            outcome.pending = PendingState.NONE; outcome.commit = CommitState.KNOWN_COMMITTED
            outcome.observation = ResourceObservationState.FINAL_REOPEN_VERIFIED
        elif pending_exact and final_exact:
            outcome.decision = StoreDecision.INCOMPLETE; outcome.reasons = ("BOTH_IDENTICAL",)
            outcome.namespace = NamespaceState.BOTH; outcome.content = ContentState.BOTH_IDENTICAL
            outcome.pending = PendingState.RECOVERABLE; outcome.commit = CommitState.KNOWN_COMMITTED
        elif final_exact and pending is not None:
            outcome.decision = StoreDecision.INCOMPLETE
            outcome.reasons = ("FINAL_WITH_DIFFERENT_PENDING",)
            outcome.namespace = NamespaceState.BOTH; outcome.content = ContentState.CONFLICT
            outcome.pending = PendingState.AMBIGUOUS; outcome.commit = CommitState.KNOWN_COMMITTED
        elif pending is None and final is None:
            outcome.decision = StoreDecision.NOT_COMMITTED; outcome.reasons = ("NEITHER_PRESENT",)
            outcome.namespace = NamespaceState.NEITHER; outcome.content = ContentState.NOT_OBSERVED
            outcome.pending = PendingState.STALE
        else:
            outcome.decision = StoreDecision.BLOCKED; outcome.reasons = ("RECOVERY_CONTENT_CONFLICT",)
            outcome.namespace = NamespaceState.DIFFERENT_FINAL if final else NamespaceState.PENDING_ONLY
            outcome.content = ContentState.CONFLICT; outcome.pending = PendingState.AMBIGUOUS
        return None
    return _execute_locked(key, Operation.INSPECT_PENDING, action)[0]


def resume_pending(*, key: AudioCompletionLedgerKeyBinding,
                   recovery: AudioCompletionLedgerRecoveryReceipt,
                   token: bytes) -> AudioCompletionLedgerStoreReceipt:
    body, pending_name = _validated_recovery(recovery, token); key = _key(key)
    def action(session: _LockedSession, namespace: _Namespace, outcome: _Outcome) -> None:
        if body["ledger_key_sha256"] != key.to_dict()["ledger_key_sha256"] or body["root_identity_sha256"] != session.root_sha:
            raise _windows.NativePortError("RECOVERY_LIVE_BINDING_MISMATCH")
        pending, final = namespace.pending_payloads.get(pending_name), namespace.final_payloads.get(body["entry_revision"])
        expected_sha = body["payload_sha256"]
        pending_exact = pending is not None and hmac.compare_digest(sha256_bytes(pending), expected_sha)
        final_exact = final is not None and hmac.compare_digest(sha256_bytes(final), expected_sha)
        if pending_exact:
            _bind_recovery_target(outcome, pending, body=body, namespace=namespace,
                pending_name=pending_name, key=key, validate_extension=final is None)
        if final_exact:
            _bind_recovery_target(outcome, final, body=body, namespace=namespace,
                pending_name=None, key=key, validate_extension=False)
        if final_exact and pending is None:
            outcome.decision = StoreDecision.ALREADY_COMMITTED_RECONCILED; outcome.reasons = ("EXACT_FINAL_ALREADY_PRESENT",)
            outcome.namespace = NamespaceState.FINAL_ONLY
            outcome.content = ContentState.FINAL_VERIFIED
            outcome.pending = PendingState.NONE
            outcome.commit = CommitState.KNOWN_COMMITTED
            outcome.observation = ResourceObservationState.FINAL_REOPEN_VERIFIED
            return None
        if final_exact and pending_exact:
            outcome.decision = StoreDecision.INCOMPLETE; outcome.reasons = ("BOTH_IDENTICAL",)
            outcome.namespace = NamespaceState.BOTH; outcome.content = ContentState.BOTH_IDENTICAL
            outcome.pending = PendingState.RECOVERABLE; outcome.commit = CommitState.KNOWN_COMMITTED
            return None
        if final_exact and pending is not None:
            outcome.decision = StoreDecision.INCOMPLETE
            outcome.reasons = ("FINAL_WITH_DIFFERENT_PENDING",)
            outcome.namespace = NamespaceState.BOTH; outcome.content = ContentState.CONFLICT
            outcome.pending = PendingState.AMBIGUOUS; outcome.commit = CommitState.KNOWN_COMMITTED
            return None
        if pending is None or not pending_exact or final is not None:
            outcome.decision = StoreDecision.BLOCKED; outcome.reasons = ("RESUME_REQUIRES_PENDING_ONLY_EXACT",)
            outcome.namespace = NamespaceState.DIFFERENT_FINAL if final is not None else NamespaceState.NEITHER
            outcome.content = ContentState.CONFLICT; outcome.pending = PendingState.AMBIGUOUS
            return None
        current_cas_sha = cas_for_chain(namespace.entries, key).to_dict()["expectation_sha256"]
        if not hmac.compare_digest(current_cas_sha, body["expected_cas_sha256"]):
            outcome.decision = StoreDecision.BLOCKED; outcome.reasons = ("RECOVERY_CAS_STALE",)
            outcome.namespace = NamespaceState.PENDING_ONLY; outcome.content = ContentState.PENDING_VERIFIED
            outcome.pending = PendingState.STALE; return None
        handle = namespace.pending_handles[pending_name]
        identity = session.port.identity(handle, security_role="private_child")
        observed_id_sha = sha256_bytes(_FILE_ID_DOMAIN + identity.file_id)
        if not hmac.compare_digest(observed_id_sha, body["pending_file_identity_sha256"]):
            raise _windows.NativePortError("PENDING_FILE_ID_CHANGED")
        _fresh_before_rename(session, key, prior=namespace, pending_name=pending_name,
            handle=handle, payload=pending, file_id=identity.file_id,
            expected_cas_sha=body["expected_cas_sha256"])
        final_name = _canonical_final_name(body["ledger_key_sha256"], body["entry_revision"])
        outcome.write_attempted = True
        try:
            session.port.rename_no_replace(handle, session.root, final_name)
        except _windows.NativePortError as exc:
            outcome.rename = RenameState.SYSCALL_COMPLETION_UNKNOWN if exc.completion_unknown else RenameState.RETURNED_FALSE
            if exc.completion_unknown:
                _reconcile_unknown_rename(session, key, payload=pending, revision=body["entry_revision"],
                    pending_name=pending_name, handle=handle, original_identity=identity,
                    prior=namespace, outcome=outcome, reason=exc.reason)
            else:
                outcome.decision = StoreDecision.INCOMPLETE; outcome.commit = CommitState.NOT_COMMITTED
                outcome.reasons = (exc.reason,); outcome.namespace = NamespaceState.PENDING_ONLY
                outcome.content = ContentState.PENDING_VERIFIED; outcome.pending = PendingState.RECOVERABLE
            return None
        outcome.write = True
        outcome.rename = RenameState.RETURNED_TRUE; outcome.commit = CommitState.KNOWN_COMMITTED
        verified = _verify_after_rename(session, key, handle=handle, original_identity=identity,
            final_name=final_name, payload=pending, prior=namespace, renamed_pending_name=pending_name)
        if verified is None:
            outcome.decision = StoreDecision.INCOMPLETE; outcome.reasons = ("RENAMED_HANDLE_RELEASE_FAILED",)
            _invalidate_observation(outcome)
            outcome.observation = ResourceObservationState.INCOMPLETE; return None
        _sync_namespace_counts(outcome, verified)
        outcome.decision = StoreDecision.APPENDED; outcome.reasons = ("RECOVERED_NO_REPLACE_APPEND_OBSERVED",)
        outcome.namespace = NamespaceState.FINAL_ONLY; outcome.content = ContentState.FINAL_VERIFIED
        outcome.pending = PendingState.NONE
        outcome.observation = ResourceObservationState.FINAL_REOPEN_VERIFIED
        return None
    return _execute_locked(key, Operation.RESUME_PENDING, action)[0]


def parse_store_receipt(value: Mapping[str, Any]) -> AudioCompletionLedgerStoreReceipt:
    return AudioCompletionLedgerStoreReceipt.from_dict(value)


def parse_recovery_receipt(value: Mapping[str, Any]) -> AudioCompletionLedgerRecoveryReceipt:
    return AudioCompletionLedgerRecoveryReceipt.from_dict(value)


def parse_store_public_projection(value: Mapping[str, Any]) -> AudioCompletionLedgerStorePublicProjection:
    return AudioCompletionLedgerStorePublicProjection.from_dict(value)


__all__ = [
    "AudioCompletionLedgerRecoveryReceipt", "AudioCompletionLedgerStoreReceipt",
    "AudioCompletionLedgerStorePublicProjection",
    "PreparedAudioCompletionAppend", "append_prepared", "inspect_pending",
    "observe_ledger", "parse_recovery_receipt", "parse_store_receipt", "parse_store_public_projection",
    "prepare_append", "resume_pending",
]
