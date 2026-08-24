"""Encrypted, atomic Owner Decision Store for TASK-029 R1."""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from enum import Enum
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping, Protocol, runtime_checkable

from .atomic import AtomicJsonWriter, AtomicWriteResult, FailureInjector, exclusive_file_update_lock
from .errors import ProductError, ProductErrorCategory
from .human_edit_learning import OwnerDecisionState, verify_owner_decision_candidate_hash
from .serialization import canonical_json_bytes, sha256_bytes


STORE_SCHEMA_VERSION = "1.0.0"
STORE_RECORD_VERSION = "1.0.0"
DPAPI_CIPHER_SUITE = "WINDOWS_DPAPI_CURRENT_USER_V1"
_DPAPI_ENTROPY = b"BAI_VIDEO_PRODUCTION\0TASK029_OWNER_DECISION_STORE\0V1"
_MAX_CIPHERTEXT_BYTES = 16 * 1024 * 1024
_STABLE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")


def _fail(code: str, message: str, category: ProductErrorCategory, **details: object) -> ProductError:
    return ProductError(code, message, category, details=dict(details))


def _stable_id(value: object, field: str) -> str:
    if not isinstance(value, str) or _STABLE_ID.fullmatch(value) is None:
        raise ValueError(f"{field} must be a stable identifier")
    return value


def _sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase sha256 coordinate")
    return value


def _int(value: object, field: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{field} must be an integer >= {minimum}")
    return value


class HumanDecision(str, Enum):
    ADOPTED = "ADOPTED"
    REJECTED = "REJECTED"


@runtime_checkable
class OwnerDecisionCipher(Protocol):
    cipher_suite: str

    def encrypt(self, plaintext: bytes) -> bytes: ...
    def decrypt(self, ciphertext: bytes) -> bytes: ...


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _blob(value: bytes) -> tuple[_DataBlob, object]:
    if value:
        buffer = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
        return _DataBlob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer
    return _DataBlob(0, ctypes.POINTER(ctypes.c_ubyte)()), None


class WindowsDpapiOwnerDecisionCipher:
    """Windows Current User DPAPI; no key material is accepted or persisted."""

    cipher_suite = DPAPI_CIPHER_SUITE
    _UI_FORBIDDEN = 0x1

    def __init__(self) -> None:
        if os.name != "nt":
            raise _fail(
                "ERR_OWNER_DECISION_ENCRYPTION_UNAVAILABLE",
                "Windows DPAPI is unavailable on this platform",
                ProductErrorCategory.NOT_SUPPORTED,
            )

    @staticmethod
    def _crypt(value: bytes, *, protect: bool) -> bytes:
        input_blob, input_buffer = _blob(value)
        entropy_blob, entropy_buffer = _blob(_DPAPI_ENTROPY)
        output_blob = _DataBlob()
        crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        function = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
        function.argtypes = [
            ctypes.POINTER(_DataBlob), ctypes.c_wchar_p, ctypes.POINTER(_DataBlob),
            ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_DataBlob),
        ]
        function.restype = wintypes.BOOL
        if not function(
            ctypes.byref(input_blob), None, ctypes.byref(entropy_blob), None, None,
            WindowsDpapiOwnerDecisionCipher._UI_FORBIDDEN, ctypes.byref(output_blob),
        ):
            raise OSError(ctypes.get_last_error(), "DPAPI operation failed")
        try:
            return ctypes.string_at(output_blob.pbData, output_blob.cbData)
        finally:
            if output_blob.pbData:
                kernel32.LocalFree(ctypes.cast(output_blob.pbData, ctypes.c_void_p))

    def encrypt(self, plaintext: bytes) -> bytes:
        return self._crypt(plaintext, protect=True)

    def decrypt(self, ciphertext: bytes) -> bytes:
        return self._crypt(ciphertext, protect=False)


@dataclass(frozen=True, slots=True)
class OwnerDecisionEntry:
    sequence: int
    decision_id: str
    candidate: Mapping[str, Any]
    decision: HumanDecision
    reason_codes: tuple[str, ...]
    decided_at_epoch_ms: int
    previous_entry_sha256: str | None

    def __post_init__(self) -> None:
        _int(self.sequence, "sequence", 1)
        _stable_id(self.decision_id, "decision_id")
        if not isinstance(self.candidate, Mapping):
            raise ValueError("candidate must be an object")
        verify_owner_decision_candidate_hash(self.candidate)
        if self.candidate.get("state") != OwnerDecisionState.READY_FOR_HUMAN_REVIEW.value:
            raise ValueError("only READY_FOR_HUMAN_REVIEW candidates may be decided")
        if not isinstance(self.decision, HumanDecision):
            raise ValueError("decision must be a HumanDecision")
        if not self.reason_codes or tuple(sorted(set(self.reason_codes))) != self.reason_codes:
            raise ValueError("reason_codes must be non-empty, unique, and sorted")
        for value in self.reason_codes:
            _stable_id(value, "reason_code")
        _int(self.decided_at_epoch_ms, "decided_at_epoch_ms", 1)
        if self.sequence == 1:
            if self.previous_entry_sha256 is not None:
                raise ValueError("first entry must not have previous_entry_sha256")
        else:
            _sha256(self.previous_entry_sha256, "previous_entry_sha256")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "record_version": STORE_RECORD_VERSION,
            "record_type": "OWNER_DECISION_ENTRY",
            "task_owner": "TASK-029",
            "sequence": self.sequence,
            "decision_id": self.decision_id,
            "candidate": dict(self.candidate),
            "candidate_sha256": self.candidate["candidate_sha256"],
            "decision": self.decision.value,
            "reason_codes": list(self.reason_codes),
            "decided_at_epoch_ms": self.decided_at_epoch_ms,
            "previous_entry_sha256": self.previous_entry_sha256,
            "human_decision_recorded": True,
            "owner_profile_write_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "cloud_telemetry_authorized": False,
            "rollback_authorized": False,
            "external_effect_authorized": False,
        }
        body["entry_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OwnerDecisionEntry":
        expected = {
            "record_version", "record_type", "task_owner", "sequence", "decision_id",
            "candidate", "candidate_sha256", "decision", "reason_codes",
            "decided_at_epoch_ms", "previous_entry_sha256", "human_decision_recorded",
            "owner_profile_write_authorized", "knowledge_pack_promotion_authorized",
            "cloud_telemetry_authorized", "rollback_authorized",
            "external_effect_authorized", "entry_sha256",
        }
        if set(value) != expected:
            raise ValueError("owner decision entry fields are incomplete or unknown")
        if value["record_version"] != STORE_RECORD_VERSION or value["record_type"] != "OWNER_DECISION_ENTRY" or value["task_owner"] != "TASK-029":
            raise ValueError("owner decision entry identity mismatch")
        for field in ("owner_profile_write_authorized", "knowledge_pack_promotion_authorized", "cloud_telemetry_authorized", "rollback_authorized", "external_effect_authorized"):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        if value["human_decision_recorded"] is not True:
            raise ValueError("human_decision_recorded must remain true")
        entry = cls(
            value["sequence"], value["decision_id"], value["candidate"],
            HumanDecision(value["decision"]), tuple(value["reason_codes"]),
            value["decided_at_epoch_ms"], value["previous_entry_sha256"],
        )
        if entry.to_dict() != dict(value):
            raise ValueError("owner decision entry hash or derived fields mismatch")
        return entry


@dataclass(frozen=True, slots=True)
class OwnerDecisionHistory:
    store_id: str
    owner_scope_sha256: str
    revision: int
    entries: tuple[OwnerDecisionEntry, ...]

    def __post_init__(self) -> None:
        _stable_id(self.store_id, "store_id")
        _sha256(self.owner_scope_sha256, "owner_scope_sha256")
        _int(self.revision, "revision")
        if self.revision != len(self.entries):
            raise ValueError("revision must equal entry count")
        seen_decisions: set[str] = set()
        seen_candidates: set[str] = set()
        previous: str | None = None
        for index, entry in enumerate(self.entries, 1):
            if entry.sequence != index or entry.previous_entry_sha256 != previous:
                raise ValueError("owner decision history chain is not contiguous")
            if entry.candidate["owner_scope_sha256"] != self.owner_scope_sha256:
                raise ValueError("candidate owner scope mismatch")
            if entry.decision_id in seen_decisions or entry.candidate["candidate_sha256"] in seen_candidates:
                raise ValueError("decision or candidate replay is not allowed")
            seen_decisions.add(entry.decision_id)
            seen_candidates.add(entry.candidate["candidate_sha256"])
            previous = entry.to_dict()["entry_sha256"]

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "record_version": STORE_RECORD_VERSION,
            "record_type": "OWNER_DECISION_HISTORY",
            "task_owner": "TASK-029",
            "store_id": self.store_id,
            "owner_scope_sha256": self.owner_scope_sha256,
            "revision": self.revision,
            "entries": [entry.to_dict() for entry in self.entries],
            "plaintext_export_authorized": False,
            "physical_delete_authorized": False,
            "owner_profile_write_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "cloud_telemetry_authorized": False,
            "external_effect_authorized": False,
        }
        body["history_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OwnerDecisionHistory":
        expected = {
            "record_version", "record_type", "task_owner", "store_id",
            "owner_scope_sha256", "revision", "entries", "plaintext_export_authorized",
            "physical_delete_authorized", "owner_profile_write_authorized",
            "knowledge_pack_promotion_authorized", "cloud_telemetry_authorized",
            "external_effect_authorized", "history_sha256",
        }
        if set(value) != expected:
            raise ValueError("owner decision history fields are incomplete or unknown")
        if value["record_version"] != STORE_RECORD_VERSION or value["record_type"] != "OWNER_DECISION_HISTORY" or value["task_owner"] != "TASK-029":
            raise ValueError("owner decision history identity mismatch")
        for field in ("plaintext_export_authorized", "physical_delete_authorized", "owner_profile_write_authorized", "knowledge_pack_promotion_authorized", "cloud_telemetry_authorized", "external_effect_authorized"):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        history = cls(
            value["store_id"], value["owner_scope_sha256"], value["revision"],
            tuple(OwnerDecisionEntry.from_dict(row) for row in value["entries"]),
        )
        if history.to_dict() != dict(value):
            raise ValueError("owner decision history hash or derived fields mismatch")
        return history


@dataclass(frozen=True, slots=True)
class OwnerDecisionSaveResult:
    history: OwnerDecisionHistory
    write: AtomicWriteResult


class OwnerDecisionStore:
    """CAS append/read of an encrypted, body-free decision history."""

    def __init__(self, path: str | Path, cipher: OwnerDecisionCipher | None = None) -> None:
        self.path = Path(path)
        self.cipher = cipher if cipher is not None else WindowsDpapiOwnerDecisionCipher()
        if not isinstance(self.cipher, OwnerDecisionCipher):
            raise ValueError("cipher does not implement OwnerDecisionCipher")
        _stable_id(self.cipher.cipher_suite, "cipher_suite")

    def _envelope(self, history: OwnerDecisionHistory) -> dict[str, object]:
        plaintext = canonical_json_bytes(history.to_dict())
        ciphertext = self.cipher.encrypt(plaintext)
        if not ciphertext or len(ciphertext) > _MAX_CIPHERTEXT_BYTES:
            raise ValueError("ciphertext size is invalid")
        body: dict[str, object] = {
            "schema_version": STORE_SCHEMA_VERSION,
            "record_type": "OWNER_DECISION_STORE_ENCRYPTED",
            "task_owner": "TASK-029",
            "cipher_suite": self.cipher.cipher_suite,
            "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
            "ciphertext_sha256": sha256_bytes(ciphertext),
            "plaintext_fields_present": False,
        }
        body["document_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    def _parse_envelope(self, value: Mapping[str, Any]) -> OwnerDecisionHistory:
        expected = {"schema_version", "record_type", "task_owner", "cipher_suite", "ciphertext_b64", "ciphertext_sha256", "plaintext_fields_present", "document_sha256"}
        if set(value) != expected:
            raise ValueError("encrypted store fields are incomplete or unknown")
        if value["schema_version"] != STORE_SCHEMA_VERSION or value["record_type"] != "OWNER_DECISION_STORE_ENCRYPTED" or value["task_owner"] != "TASK-029":
            raise ValueError("encrypted store identity mismatch")
        if value["cipher_suite"] != self.cipher.cipher_suite or value["plaintext_fields_present"] is not False:
            raise ValueError("cipher suite or plaintext boundary mismatch")
        body = {key: item for key, item in value.items() if key != "document_sha256"}
        if value["document_sha256"] != sha256_bytes(canonical_json_bytes(body)):
            raise ValueError("encrypted store document checksum mismatch")
        ciphertext = base64.b64decode(value["ciphertext_b64"], validate=True)
        if not ciphertext or len(ciphertext) > _MAX_CIPHERTEXT_BYTES or value["ciphertext_sha256"] != sha256_bytes(ciphertext):
            raise ValueError("encrypted store ciphertext checksum mismatch")
        plaintext = self.cipher.decrypt(ciphertext)
        document = json.loads(plaintext.decode("utf-8"))
        if not isinstance(document, dict):
            raise ValueError("decrypted owner decision history must be an object")
        return OwnerDecisionHistory.from_dict(document)

    def load(self) -> OwnerDecisionHistory:
        try:
            if self.path.is_symlink() or not self.path.is_file():
                raise ValueError("owner decision store must be a regular non-symlink file")
            document = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError("encrypted owner decision store must be an object")
            return self._parse_envelope(document)
        except ProductError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise _fail(
                "ERR_OWNER_DECISION_STORE_INTEGRITY",
                "Owner Decision Store could not be decrypted and verified safely",
                ProductErrorCategory.DATA_INTEGRITY,
                reason=type(exc).__name__,
            ) from exc

    def append(
        self,
        *,
        store_id: str,
        owner_scope_sha256: str,
        decision_id: str,
        candidate: Mapping[str, Any],
        decision: HumanDecision,
        reason_codes: tuple[str, ...],
        decided_at_epoch_ms: int,
        expected_revision: int,
        failure_injector: FailureInjector | None = None,
    ) -> OwnerDecisionSaveResult:
        with exclusive_file_update_lock(self.path):
            if self.path.exists():
                current = self.load()
                if current.store_id != store_id or current.owner_scope_sha256 != owner_scope_sha256:
                    raise _fail("ERR_OWNER_DECISION_STORE_SCOPE", "Owner Decision Store scope mismatch", ProductErrorCategory.AUTHORIZATION)
            else:
                if self.path.is_symlink():
                    raise _fail("ERR_OWNER_DECISION_STORE_INTEGRITY", "Owner Decision Store path is a symlink", ProductErrorCategory.DATA_INTEGRITY)
                current = OwnerDecisionHistory(store_id, owner_scope_sha256, 0, ())
            if current.revision != expected_revision:
                raise _fail(
                    "ERR_OWNER_DECISION_STORE_CONFLICT",
                    "Owner Decision Store changed since it was read",
                    ProductErrorCategory.STATE,
                    expected_revision=expected_revision,
                    current_revision=current.revision,
                )
            previous = current.entries[-1].to_dict()["entry_sha256"] if current.entries else None
            entry = OwnerDecisionEntry(
                current.revision + 1, decision_id, dict(candidate), decision,
                tuple(sorted(reason_codes)), decided_at_epoch_ms, previous,
            )
            history = OwnerDecisionHistory(store_id, owner_scope_sha256, current.revision + 1, current.entries + (entry,))
            envelope = self._envelope(history)
            write = AtomicJsonWriter.write(
                self.path, envelope,
                validator=lambda value: self._parse_envelope(value),
                failure_injector=failure_injector,
            )
            return OwnerDecisionSaveResult(history, write)


__all__ = [
    "DPAPI_CIPHER_SUITE", "HumanDecision", "OwnerDecisionCipher",
    "OwnerDecisionEntry", "OwnerDecisionHistory", "OwnerDecisionSaveResult",
    "OwnerDecisionStore", "WindowsDpapiOwnerDecisionCipher",
]
