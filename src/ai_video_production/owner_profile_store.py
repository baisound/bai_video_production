"""TASK-029 R3 encrypted Owner Profile revision store.

Only an exact R2 materialization candidate with a separate explicit Human
confirmation may be appended.  This store does not register, promote, apply,
or roll back a profile outside its encrypted local history.
"""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable

from .atomic import AtomicJsonWriter, AtomicWriteResult, FailureInjector, exclusive_file_update_lock
from .errors import ProductError, ProductErrorCategory
from .owner_decision_store import OwnerDecisionHistory
from .owner_profile_materialization import (
    OwnerProfileMaterializationCandidate,
    OwnerProfileMaterializationState,
    compile_owner_profile_materialization_candidate,
)
from .profile_tuning import ProfileTuningProposal
from .profile_tuning_owner_decision import (
    AdjustmentDecisionSelection,
    ProfileTuningOwnerDecisionBinding,
)
from .serialization import canonical_json_bytes, sha256_bytes


STORE_SCHEMA_VERSION = "1.0.0"
STORE_RECORD_VERSION = "1.0.0"
DPAPI_CIPHER_SUITE = "WINDOWS_DPAPI_CURRENT_USER_OWNER_PROFILE_V1"
_DPAPI_ENTROPY = b"BAI_VIDEO_PRODUCTION\0TASK029_OWNER_PROFILE_STORE\0V1"
_MAX_CIPHERTEXT_BYTES = 16 * 1024 * 1024
_STABLE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
_CANDIDATE_FIELDS = {
    "materialization_version", "record_type", "task_owner", "source_task",
    "candidate_id", "owner_scope_sha256", "decision_store_id",
    "decision_history_revision", "decision_history_sha256", "proposal_sha256",
    "binding_sha256", "baseline_profile_sha256", "proposed_profile_sha256",
    "rollback_profile_sha256", "source_decision_ids", "profile_snapshot", "state",
    "latest_history_revalidation_required", "human_materialization_confirmation_required",
    "in_memory_candidate_only", "owner_profile_store_write_authorized",
    "model_profile_registry_write_authorized", "knowledge_pack_promotion_authorized",
    "automatic_promotion_authorized", "rollback_execution_authorized",
    "edit_plan_mutation_authorized", "external_effect_authorized",
    "materialization_sha256",
}


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


def _positive_int(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{field} must be an integer >= 1")
    return value

def _verify_candidate_payload(value: Mapping[str, Any]) -> None:
    if set(value) != _CANDIDATE_FIELDS:
        raise ValueError("materialization candidate fields are incomplete or unknown")
    if value["materialization_version"] != "1.0.0" or value["record_type"] != "OWNER_PROFILE_MATERIALIZATION_CANDIDATE" or value["task_owner"] != "TASK-029" or value["source_task"] != "TASK-019":
        raise ValueError("materialization candidate identity mismatch")
    for field in (
        "latest_history_revalidation_required", "human_materialization_confirmation_required",
        "in_memory_candidate_only",
    ):
        if value[field] is not True:
            raise ValueError(f"{field} must remain true")
    for field in (
        "owner_profile_store_write_authorized", "model_profile_registry_write_authorized",
        "knowledge_pack_promotion_authorized", "automatic_promotion_authorized",
        "rollback_execution_authorized", "edit_plan_mutation_authorized",
        "external_effect_authorized",
    ):
        if value[field] is not False:
            raise ValueError(f"{field} must remain false")
    body = dict(value)
    claimed = body.pop("materialization_sha256", None)
    _sha256(claimed, "materialization_sha256")
    if claimed != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError("materialization candidate hash mismatch")
    snapshot = value.get("profile_snapshot")
    if not isinstance(snapshot, Mapping):
        raise ValueError("stored materialization candidate requires a profile snapshot")
    snapshot_body = dict(snapshot)
    profile_sha256 = snapshot_body.pop("profile_sha256", None)
    _sha256(profile_sha256, "profile_snapshot.profile_sha256")
    if (
        profile_sha256 != value["proposed_profile_sha256"]
        or profile_sha256 != sha256_bytes(canonical_json_bytes(snapshot_body))
    ):
        raise ValueError("profile snapshot hash mismatch")


@runtime_checkable
class OwnerProfileCipher(Protocol):
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


class WindowsDpapiOwnerProfileCipher:
    """Windows Current User DPAPI with a store-specific entropy domain."""

    cipher_suite = DPAPI_CIPHER_SUITE
    _UI_FORBIDDEN = 0x1

    def __init__(self) -> None:
        if os.name != "nt":
            raise _fail(
                "ERR_OWNER_PROFILE_ENCRYPTION_UNAVAILABLE",
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
            WindowsDpapiOwnerProfileCipher._UI_FORBIDDEN, ctypes.byref(output_blob),
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
class OwnerProfileMaterializationConfirmation:
    confirmation_id: str
    candidate_sha256: str
    owner_scope_sha256: str
    profile_sha256: str
    confirmed_at_epoch_ms: int

    def __post_init__(self) -> None:
        _stable_id(self.confirmation_id, "confirmation_id")
        _sha256(self.candidate_sha256, "candidate_sha256")
        _sha256(self.owner_scope_sha256, "owner_scope_sha256")
        _sha256(self.profile_sha256, "profile_sha256")
        _positive_int(self.confirmed_at_epoch_ms, "confirmed_at_epoch_ms")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "record_version": STORE_RECORD_VERSION,
            "record_type": "OWNER_PROFILE_MATERIALIZATION_CONFIRMATION",
            "task_owner": "TASK-029",
            "confirmation_id": self.confirmation_id,
            "candidate_sha256": self.candidate_sha256,
            "owner_scope_sha256": self.owner_scope_sha256,
            "profile_sha256": self.profile_sha256,
            "confirmed_at_epoch_ms": self.confirmed_at_epoch_ms,
            "explicit_human_confirmation_received": True,
            "automatic_materialization_authorized": False,
            "model_profile_registry_write_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "rollback_execution_authorized": False,
            "external_effect_authorized": False,
        }
        body["confirmation_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OwnerProfileMaterializationConfirmation":
        expected = {
            "record_version", "record_type", "task_owner", "confirmation_id",
            "candidate_sha256", "owner_scope_sha256", "profile_sha256",
            "confirmed_at_epoch_ms", "explicit_human_confirmation_received",
            "automatic_materialization_authorized", "model_profile_registry_write_authorized",
            "knowledge_pack_promotion_authorized", "rollback_execution_authorized",
            "external_effect_authorized", "confirmation_sha256",
        }
        if set(value) != expected:
            raise ValueError("confirmation fields are incomplete or unknown")
        if value["record_version"] != STORE_RECORD_VERSION or value["record_type"] != "OWNER_PROFILE_MATERIALIZATION_CONFIRMATION" or value["task_owner"] != "TASK-029":
            raise ValueError("confirmation identity mismatch")
        if value["explicit_human_confirmation_received"] is not True:
            raise ValueError("explicit Human confirmation is required")
        for field in (
            "automatic_materialization_authorized", "model_profile_registry_write_authorized",
            "knowledge_pack_promotion_authorized", "rollback_execution_authorized",
            "external_effect_authorized",
        ):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        result = cls(
            value["confirmation_id"], value["candidate_sha256"],
            value["owner_scope_sha256"], value["profile_sha256"],
            value["confirmed_at_epoch_ms"],
        )
        if result.to_dict() != dict(value):
            raise ValueError("confirmation hash or derived fields mismatch")
        return result


def confirm_owner_profile_materialization(
    *, confirmation_id: str, candidate: OwnerProfileMaterializationCandidate,
    confirmed_at_epoch_ms: int, human_confirmed: bool,
) -> OwnerProfileMaterializationConfirmation:
    if human_confirmed is not True:
        raise ValueError("explicit Human materialization confirmation is required")
    if not isinstance(candidate, OwnerProfileMaterializationCandidate):
        raise ValueError("candidate must be an OwnerProfileMaterializationCandidate")
    if candidate.state is not OwnerProfileMaterializationState.READY_FOR_HUMAN_MATERIALIZATION:
        raise ValueError("only READY_FOR_HUMAN_MATERIALIZATION candidates may be confirmed")
    payload = candidate.to_dict()
    return OwnerProfileMaterializationConfirmation(
        confirmation_id, payload["materialization_sha256"], candidate.owner_scope_sha256,
        candidate.proposed_profile_sha256, confirmed_at_epoch_ms,
    )


@dataclass(frozen=True, slots=True)
class OwnerProfileRevision:
    sequence: int
    candidate: Mapping[str, Any]
    confirmation: OwnerProfileMaterializationConfirmation
    previous_revision_sha256: str | None

    def __post_init__(self) -> None:
        _positive_int(self.sequence, "sequence")
        if not isinstance(self.candidate, Mapping):
            raise ValueError("candidate must be an object")
        _verify_candidate_payload(self.candidate)
        if not isinstance(self.confirmation, OwnerProfileMaterializationConfirmation):
            raise ValueError("confirmation must be an OwnerProfileMaterializationConfirmation")
        if self.candidate.get("state") != OwnerProfileMaterializationState.READY_FOR_HUMAN_MATERIALIZATION.value:
            raise ValueError("only ready materialization candidates may be stored")
        if self.candidate.get("profile_snapshot") is None:
            raise ValueError("stored candidate requires an exact profile snapshot")
        if self.candidate.get("materialization_sha256") != self.confirmation.candidate_sha256:
            raise ValueError("confirmation does not bind the candidate")
        if self.candidate.get("owner_scope_sha256") != self.confirmation.owner_scope_sha256:
            raise ValueError("confirmation owner scope mismatch")
        if self.candidate.get("proposed_profile_sha256") != self.confirmation.profile_sha256:
            raise ValueError("confirmation profile mismatch")
        if self.sequence == 1:
            if self.previous_revision_sha256 is not None:
                raise ValueError("first revision must not have previous_revision_sha256")
        else:
            _sha256(self.previous_revision_sha256, "previous_revision_sha256")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "record_version": STORE_RECORD_VERSION,
            "record_type": "OWNER_PROFILE_REVISION",
            "task_owner": "TASK-029",
            "sequence": self.sequence,
            "candidate": dict(self.candidate),
            "confirmation": self.confirmation.to_dict(),
            "previous_revision_sha256": self.previous_revision_sha256,
            "profile_materialized_in_owner_store": True,
            "model_profile_registry_write_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "automatic_promotion_authorized": False,
            "rollback_execution_authorized": False,
            "edit_plan_mutation_authorized": False,
            "external_effect_authorized": False,
        }
        body["revision_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OwnerProfileRevision":
        expected = {
            "record_version", "record_type", "task_owner", "sequence", "candidate",
            "confirmation", "previous_revision_sha256", "profile_materialized_in_owner_store",
            "model_profile_registry_write_authorized", "knowledge_pack_promotion_authorized",
            "automatic_promotion_authorized", "rollback_execution_authorized",
            "edit_plan_mutation_authorized", "external_effect_authorized", "revision_sha256",
        }
        if set(value) != expected:
            raise ValueError("profile revision fields are incomplete or unknown")
        if value["record_version"] != STORE_RECORD_VERSION or value["record_type"] != "OWNER_PROFILE_REVISION" or value["task_owner"] != "TASK-029":
            raise ValueError("profile revision identity mismatch")
        if value["profile_materialized_in_owner_store"] is not True:
            raise ValueError("profile materialization marker must remain true")
        for field in (
            "model_profile_registry_write_authorized", "knowledge_pack_promotion_authorized",
            "automatic_promotion_authorized", "rollback_execution_authorized",
            "edit_plan_mutation_authorized", "external_effect_authorized",
        ):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        result = cls(
            value["sequence"], value["candidate"],
            OwnerProfileMaterializationConfirmation.from_dict(value["confirmation"]),
            value["previous_revision_sha256"],
        )
        if result.to_dict() != dict(value):
            raise ValueError("profile revision hash or derived fields mismatch")
        return result


@dataclass(frozen=True, slots=True)
class OwnerProfileHistory:
    store_id: str
    owner_scope_sha256: str
    revision: int
    revisions: tuple[OwnerProfileRevision, ...]

    def __post_init__(self) -> None:
        _stable_id(self.store_id, "store_id")
        _sha256(self.owner_scope_sha256, "owner_scope_sha256")
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 0:
            raise ValueError("revision must be an integer >= 0")
        if self.revision != len(self.revisions):
            raise ValueError("revision must equal revision count")
        previous: str | None = None
        candidate_ids: set[str] = set()
        confirmation_ids: set[str] = set()
        profile_versions: set[str] = set()
        last_profile_sha256: str | None = None
        profile_id: str | None = None
        for sequence, item in enumerate(self.revisions, 1):
            payload = item.candidate
            snapshot = payload["profile_snapshot"]
            if item.sequence != sequence or item.previous_revision_sha256 != previous:
                raise ValueError("Owner Profile revision chain is not contiguous")
            if payload["owner_scope_sha256"] != self.owner_scope_sha256:
                raise ValueError("Owner Profile scope mismatch")
            if last_profile_sha256 is not None and payload["baseline_profile_sha256"] != last_profile_sha256:
                raise ValueError("new candidate baseline must equal the current Owner Profile")
            if profile_id is not None and snapshot["profile_id"] != profile_id:
                raise ValueError("Owner Profile identity cannot change within a store")
            identifiers = (payload["candidate_id"], item.confirmation.confirmation_id, snapshot["profile_version"])
            if identifiers[0] in candidate_ids or identifiers[1] in confirmation_ids or identifiers[2] in profile_versions:
                raise ValueError("candidate, confirmation, or profile version replay is not allowed")
            candidate_ids.add(identifiers[0]); confirmation_ids.add(identifiers[1]); profile_versions.add(identifiers[2])
            profile_id = snapshot["profile_id"]
            last_profile_sha256 = payload["proposed_profile_sha256"]
            previous = item.to_dict()["revision_sha256"]

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "record_version": STORE_RECORD_VERSION,
            "record_type": "OWNER_PROFILE_HISTORY",
            "task_owner": "TASK-029",
            "store_id": self.store_id,
            "owner_scope_sha256": self.owner_scope_sha256,
            "revision": self.revision,
            "revisions": [item.to_dict() for item in self.revisions],
            "encrypted_at_rest_required": True,
            "explicit_human_confirmation_required": True,
            "plaintext_export_authorized": False,
            "physical_delete_authorized": False,
            "model_profile_registry_write_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "automatic_promotion_authorized": False,
            "rollback_execution_authorized": False,
            "external_effect_authorized": False,
        }
        body["history_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OwnerProfileHistory":
        expected = {
            "record_version", "record_type", "task_owner", "store_id",
            "owner_scope_sha256", "revision", "revisions", "encrypted_at_rest_required",
            "explicit_human_confirmation_required", "plaintext_export_authorized",
            "physical_delete_authorized", "model_profile_registry_write_authorized",
            "knowledge_pack_promotion_authorized", "automatic_promotion_authorized",
            "rollback_execution_authorized", "external_effect_authorized", "history_sha256",
        }
        if set(value) != expected:
            raise ValueError("Owner Profile history fields are incomplete or unknown")
        if value["record_version"] != STORE_RECORD_VERSION or value["record_type"] != "OWNER_PROFILE_HISTORY" or value["task_owner"] != "TASK-029":
            raise ValueError("Owner Profile history identity mismatch")
        if value["encrypted_at_rest_required"] is not True or value["explicit_human_confirmation_required"] is not True:
            raise ValueError("Owner Profile safety requirements must remain true")
        for field in (
            "plaintext_export_authorized", "physical_delete_authorized",
            "model_profile_registry_write_authorized", "knowledge_pack_promotion_authorized",
            "automatic_promotion_authorized", "rollback_execution_authorized",
            "external_effect_authorized",
        ):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        result = cls(
            value["store_id"], value["owner_scope_sha256"], value["revision"],
            tuple(OwnerProfileRevision.from_dict(row) for row in value["revisions"]),
        )
        if result.to_dict() != dict(value):
            raise ValueError("Owner Profile history hash or derived fields mismatch")
        return result


@dataclass(frozen=True, slots=True)
class OwnerProfileSaveResult:
    history: OwnerProfileHistory
    write: AtomicWriteResult


class OwnerProfileStore:
    """CAS append/read of explicitly confirmed encrypted Owner Profiles."""

    def __init__(self, path: str | Path, cipher: OwnerProfileCipher | None = None) -> None:
        self.path = Path(path)
        self.cipher = cipher if cipher is not None else WindowsDpapiOwnerProfileCipher()
        if not isinstance(self.cipher, OwnerProfileCipher):
            raise ValueError("cipher does not implement OwnerProfileCipher")
        _stable_id(self.cipher.cipher_suite, "cipher_suite")

    def _envelope(self, history: OwnerProfileHistory) -> dict[str, object]:
        ciphertext = self.cipher.encrypt(canonical_json_bytes(history.to_dict()))
        if not ciphertext or len(ciphertext) > _MAX_CIPHERTEXT_BYTES:
            raise ValueError("ciphertext size is invalid")
        body: dict[str, object] = {
            "schema_version": STORE_SCHEMA_VERSION,
            "record_type": "OWNER_PROFILE_STORE_ENCRYPTED",
            "task_owner": "TASK-029",
            "cipher_suite": self.cipher.cipher_suite,
            "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
            "ciphertext_sha256": sha256_bytes(ciphertext),
            "plaintext_fields_present": False,
        }
        body["document_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    def _parse_envelope(self, value: Mapping[str, Any]) -> OwnerProfileHistory:
        expected = {"schema_version", "record_type", "task_owner", "cipher_suite", "ciphertext_b64", "ciphertext_sha256", "plaintext_fields_present", "document_sha256"}
        if set(value) != expected:
            raise ValueError("encrypted store fields are incomplete or unknown")
        if value["schema_version"] != STORE_SCHEMA_VERSION or value["record_type"] != "OWNER_PROFILE_STORE_ENCRYPTED" or value["task_owner"] != "TASK-029":
            raise ValueError("encrypted store identity mismatch")
        if value["cipher_suite"] != self.cipher.cipher_suite or value["plaintext_fields_present"] is not False:
            raise ValueError("cipher suite or plaintext boundary mismatch")
        body = {key: item for key, item in value.items() if key != "document_sha256"}
        if value["document_sha256"] != sha256_bytes(canonical_json_bytes(body)):
            raise ValueError("encrypted store document checksum mismatch")
        ciphertext = base64.b64decode(value["ciphertext_b64"], validate=True)
        if not ciphertext or len(ciphertext) > _MAX_CIPHERTEXT_BYTES or value["ciphertext_sha256"] != sha256_bytes(ciphertext):
            raise ValueError("encrypted store ciphertext checksum mismatch")
        document = json.loads(self.cipher.decrypt(ciphertext).decode("utf-8"))
        if not isinstance(document, dict):
            raise ValueError("decrypted Owner Profile history must be an object")
        return OwnerProfileHistory.from_dict(document)

    def load(self) -> OwnerProfileHistory:
        try:
            if self.path.is_symlink() or not self.path.is_file():
                raise ValueError("Owner Profile Store must be a regular non-symlink file")
            document = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError("encrypted Owner Profile Store must be an object")
            return self._parse_envelope(document)
        except ProductError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise _fail(
                "ERR_OWNER_PROFILE_STORE_INTEGRITY",
                "Owner Profile Store could not be decrypted and verified safely",
                ProductErrorCategory.DATA_INTEGRITY,
                reason=type(exc).__name__,
            ) from exc

    def append(
        self, *, store_id: str, owner_scope_sha256: str, candidate_id: str,
        proposal: ProfileTuningProposal, binding: ProfileTuningOwnerDecisionBinding,
        decision_history: OwnerDecisionHistory,
        selections: Iterable[AdjustmentDecisionSelection],
        confirmation: OwnerProfileMaterializationConfirmation,
        expected_revision: int, failure_injector: FailureInjector | None = None,
    ) -> OwnerProfileSaveResult:
        candidate = compile_owner_profile_materialization_candidate(
            candidate_id, proposal, binding, decision_history, tuple(selections)
        )
        if candidate.state is not OwnerProfileMaterializationState.READY_FOR_HUMAN_MATERIALIZATION:
            raise ValueError("only READY_FOR_HUMAN_MATERIALIZATION candidates may be stored")
        candidate_payload = candidate.to_dict()
        if not isinstance(confirmation, OwnerProfileMaterializationConfirmation) or confirmation.candidate_sha256 != candidate_payload["materialization_sha256"]:
            raise ValueError("exact explicit Human confirmation does not match the candidate")
        with exclusive_file_update_lock(self.path):
            if self.path.exists():
                current = self.load()
                if current.store_id != store_id or current.owner_scope_sha256 != owner_scope_sha256:
                    raise _fail("ERR_OWNER_PROFILE_STORE_SCOPE", "Owner Profile Store scope mismatch", ProductErrorCategory.AUTHORIZATION)
            else:
                if self.path.is_symlink():
                    raise _fail("ERR_OWNER_PROFILE_STORE_INTEGRITY", "Owner Profile Store path is a symlink", ProductErrorCategory.DATA_INTEGRITY)
                current = OwnerProfileHistory(store_id, owner_scope_sha256, 0, ())
            if current.revision != expected_revision:
                raise _fail(
                    "ERR_OWNER_PROFILE_STORE_CONFLICT", "Owner Profile Store changed since it was read",
                    ProductErrorCategory.STATE, expected_revision=expected_revision,
                    current_revision=current.revision,
                )
            previous = current.revisions[-1].to_dict()["revision_sha256"] if current.revisions else None
            revision = OwnerProfileRevision(current.revision + 1, candidate_payload, confirmation, previous)
            history = OwnerProfileHistory(store_id, owner_scope_sha256, current.revision + 1, current.revisions + (revision,))
            envelope = self._envelope(history)
            write = AtomicJsonWriter.write(
                self.path, envelope, validator=lambda value: self._parse_envelope(value),
                failure_injector=failure_injector,
            )
            return OwnerProfileSaveResult(history, write)


__all__ = [
    "DPAPI_CIPHER_SUITE", "OwnerProfileCipher", "OwnerProfileHistory",
    "OwnerProfileMaterializationConfirmation", "OwnerProfileRevision",
    "OwnerProfileSaveResult", "OwnerProfileStore", "WindowsDpapiOwnerProfileCipher",
    "confirm_owner_profile_materialization",
]
