"""TASK-029 R5 explicitly confirmed encrypted Model/Profile Registry store.

The source Owner Profile Store and destination registry are locked together,
the R4 candidate is recompiled from the exact latest encrypted source, and one
separate Human confirmation is consumed for one append.  Registration does not
apply a runtime profile or authorize promotion, rollback, or external effects.
"""

from __future__ import annotations

import base64
from contextlib import ExitStack
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping, Protocol, runtime_checkable

from .atomic import AtomicJsonWriter, AtomicWriteResult, FailureInjector, exclusive_file_update_lock
from .errors import ProductError, ProductErrorCategory
from .owner_profile_registry import (
    OwnerProfileRegistryCandidate,
    OwnerProfileRegistryCandidateState,
    compile_owner_profile_registry_candidate,
)
from .owner_profile_store import OwnerProfileStore
from .serialization import canonical_json_bytes, sha256_bytes


REGISTRY_STORE_SCHEMA_VERSION = "1.0.0"
REGISTRY_STORE_RECORD_VERSION = "1.0.0"
REGISTRY_DPAPI_CIPHER_SUITE = "WINDOWS_DPAPI_CURRENT_USER_OWNER_PROFILE_REGISTRY_V1"
_DPAPI_ENTROPY = b"BAI_VIDEO_PRODUCTION\0TASK029_OWNER_PROFILE_REGISTRY_STORE\0V1"
_MAX_CIPHERTEXT_BYTES = 16 * 1024 * 1024
_STABLE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _fail(code: str, message: str, category: ProductErrorCategory, **details: object) -> ProductError:
    return ProductError(code, message, category, details=dict(details))


def _stable_id(value: object, field: str) -> str:
    if not isinstance(value, str) or _STABLE_ID_RE.fullmatch(value) is None:
        raise ValueError(f"{field} must be a stable identifier")
    return value


def _sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase sha256 coordinate")
    return value


def _positive_int(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{field} must be an integer >= 1")
    return value


@runtime_checkable
class OwnerProfileRegistryCipher(Protocol):
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


class WindowsDpapiOwnerProfileRegistryCipher:
    """Windows Current User DPAPI with a registry-specific entropy domain."""

    cipher_suite = REGISTRY_DPAPI_CIPHER_SUITE
    _UI_FORBIDDEN = 0x1

    def __init__(self) -> None:
        if os.name != "nt":
            raise _fail(
                "ERR_OWNER_PROFILE_REGISTRY_ENCRYPTION_UNAVAILABLE",
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
            WindowsDpapiOwnerProfileRegistryCipher._UI_FORBIDDEN, ctypes.byref(output_blob),
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
class OwnerProfileRegistryConfirmation:
    confirmation_id: str
    registry_candidate_sha256: str
    owner_scope_sha256: str
    source_history_revision: int
    source_history_sha256: str
    source_profile_revision_sha256: str
    profile_sha256: str
    confirmed_at_epoch_ms: int

    def __post_init__(self) -> None:
        _stable_id(self.confirmation_id, "confirmation_id")
        for field in (
            "registry_candidate_sha256", "owner_scope_sha256", "source_history_sha256",
            "source_profile_revision_sha256", "profile_sha256",
        ):
            _sha256(getattr(self, field), field)
        _positive_int(self.source_history_revision, "source_history_revision")
        _positive_int(self.confirmed_at_epoch_ms, "confirmed_at_epoch_ms")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "record_version": REGISTRY_STORE_RECORD_VERSION,
            "record_type": "OWNER_PROFILE_REGISTRY_CONFIRMATION",
            "task_owner": "TASK-029",
            "confirmation_id": self.confirmation_id,
            "registry_candidate_sha256": self.registry_candidate_sha256,
            "owner_scope_sha256": self.owner_scope_sha256,
            "source_history_revision": self.source_history_revision,
            "source_history_sha256": self.source_history_sha256,
            "source_profile_revision_sha256": self.source_profile_revision_sha256,
            "profile_sha256": self.profile_sha256,
            "confirmed_at_epoch_ms": self.confirmed_at_epoch_ms,
            "explicit_human_registry_confirmation_received": True,
            "one_registry_registration_confirmed": True,
            "automatic_registry_write_authorized": False,
            "runtime_profile_apply_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "rollback_execution_authorized": False,
            "external_effect_authorized": False,
        }
        body["confirmation_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OwnerProfileRegistryConfirmation":
        expected = {
            "record_version", "record_type", "task_owner", "confirmation_id",
            "registry_candidate_sha256", "owner_scope_sha256", "source_history_revision",
            "source_history_sha256", "source_profile_revision_sha256", "profile_sha256",
            "confirmed_at_epoch_ms", "explicit_human_registry_confirmation_received",
            "one_registry_registration_confirmed", "automatic_registry_write_authorized",
            "runtime_profile_apply_authorized", "knowledge_pack_promotion_authorized",
            "rollback_execution_authorized", "external_effect_authorized",
            "confirmation_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("registry confirmation fields are incomplete or unknown")
        if (
            value["record_version"] != REGISTRY_STORE_RECORD_VERSION
            or value["record_type"] != "OWNER_PROFILE_REGISTRY_CONFIRMATION"
            or value["task_owner"] != "TASK-029"
            or value["explicit_human_registry_confirmation_received"] is not True
            or value["one_registry_registration_confirmed"] is not True
        ):
            raise ValueError("registry confirmation identity mismatch")
        for field in (
            "automatic_registry_write_authorized", "runtime_profile_apply_authorized",
            "knowledge_pack_promotion_authorized", "rollback_execution_authorized",
            "external_effect_authorized",
        ):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        result = cls(
            value["confirmation_id"], value["registry_candidate_sha256"],
            value["owner_scope_sha256"], value["source_history_revision"],
            value["source_history_sha256"], value["source_profile_revision_sha256"],
            value["profile_sha256"], value["confirmed_at_epoch_ms"],
        )
        if result.to_dict() != dict(value):
            raise ValueError("registry confirmation hash or derived fields mismatch")
        return result


def confirm_owner_profile_registry_registration(
    *, confirmation_id: str, candidate: OwnerProfileRegistryCandidate,
    confirmed_at_epoch_ms: int, human_confirmed: bool,
) -> OwnerProfileRegistryConfirmation:
    if human_confirmed is not True:
        raise ValueError("explicit Human registry confirmation is required")
    if not isinstance(candidate, OwnerProfileRegistryCandidate):
        raise ValueError("candidate must be an OwnerProfileRegistryCandidate")
    if candidate.state is not OwnerProfileRegistryCandidateState.READY_FOR_HUMAN_REGISTRY_REVIEW:
        raise ValueError("only READY_FOR_HUMAN_REGISTRY_REVIEW candidates may be confirmed")
    payload = candidate.to_dict()
    return OwnerProfileRegistryConfirmation(
        confirmation_id, payload["registry_candidate_sha256"], candidate.owner_scope_sha256,
        candidate.source_history_revision, candidate.source_history_sha256,
        candidate.source_profile_revision_sha256,
        candidate.profile_snapshot.to_dict()["profile_sha256"], confirmed_at_epoch_ms,
    )


@dataclass(frozen=True, slots=True)
class OwnerProfileRegistryRevision:
    sequence: int
    candidate: OwnerProfileRegistryCandidate
    confirmation: OwnerProfileRegistryConfirmation
    previous_revision_sha256: str | None

    def __post_init__(self) -> None:
        _positive_int(self.sequence, "sequence")
        if not isinstance(self.candidate, OwnerProfileRegistryCandidate):
            raise ValueError("candidate must be an OwnerProfileRegistryCandidate")
        candidate = self.candidate
        if not isinstance(self.confirmation, OwnerProfileRegistryConfirmation):
            raise ValueError("confirmation must be an OwnerProfileRegistryConfirmation")
        payload = candidate.to_dict()
        confirmation = self.confirmation
        if payload["registry_candidate_sha256"] != confirmation.registry_candidate_sha256:
            raise ValueError("registry confirmation does not bind the candidate")
        if candidate.owner_scope_sha256 != confirmation.owner_scope_sha256:
            raise ValueError("registry confirmation owner scope mismatch")
        if candidate.source_history_revision != confirmation.source_history_revision:
            raise ValueError("registry confirmation source revision mismatch")
        if candidate.source_history_sha256 != confirmation.source_history_sha256:
            raise ValueError("registry confirmation source history mismatch")
        if candidate.source_profile_revision_sha256 != confirmation.source_profile_revision_sha256:
            raise ValueError("registry confirmation source profile revision mismatch")
        if candidate.profile_snapshot.to_dict()["profile_sha256"] != confirmation.profile_sha256:
            raise ValueError("registry confirmation profile mismatch")
        if self.sequence == 1:
            if self.previous_revision_sha256 is not None:
                raise ValueError("first registry revision must not have a previous hash")
        else:
            _sha256(self.previous_revision_sha256, "previous_revision_sha256")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "record_version": REGISTRY_STORE_RECORD_VERSION,
            "record_type": "OWNER_PROFILE_REGISTRY_REVISION",
            "task_owner": "TASK-029",
            "sequence": self.sequence,
            "candidate": self.candidate.to_dict(),
            "confirmation": self.confirmation.to_dict(),
            "previous_revision_sha256": self.previous_revision_sha256,
            "registered_in_model_profile_registry": True,
            "registration_authority_consumed": True,
            "runtime_profile_apply_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "automatic_promotion_authorized": False,
            "rollback_execution_authorized": False,
            "edit_plan_mutation_authorized": False,
            "external_effect_authorized": False,
        }
        body["revision_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OwnerProfileRegistryRevision":
        expected = {
            "record_version", "record_type", "task_owner", "sequence", "candidate",
            "confirmation", "previous_revision_sha256", "registered_in_model_profile_registry",
            "registration_authority_consumed", "runtime_profile_apply_authorized",
            "knowledge_pack_promotion_authorized", "automatic_promotion_authorized",
            "rollback_execution_authorized", "edit_plan_mutation_authorized",
            "external_effect_authorized", "revision_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("registry revision fields are incomplete or unknown")
        if (
            value["record_version"] != REGISTRY_STORE_RECORD_VERSION
            or value["record_type"] != "OWNER_PROFILE_REGISTRY_REVISION"
            or value["task_owner"] != "TASK-029"
            or value["registered_in_model_profile_registry"] is not True
            or value["registration_authority_consumed"] is not True
        ):
            raise ValueError("registry revision identity mismatch")
        for field in (
            "runtime_profile_apply_authorized", "knowledge_pack_promotion_authorized",
            "automatic_promotion_authorized", "rollback_execution_authorized",
            "edit_plan_mutation_authorized", "external_effect_authorized",
        ):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        result = cls(
            value["sequence"], OwnerProfileRegistryCandidate.from_dict(value["candidate"]),
            OwnerProfileRegistryConfirmation.from_dict(value["confirmation"]),
            value["previous_revision_sha256"],
        )
        if result.to_dict() != dict(value):
            raise ValueError("registry revision hash or derived fields mismatch")
        return result


@dataclass(frozen=True, slots=True)
class OwnerProfileRegistryHistory:
    registry_id: str
    owner_scope_sha256: str
    source_store_id: str
    revision: int
    revisions: tuple[OwnerProfileRegistryRevision, ...]

    def __post_init__(self) -> None:
        _stable_id(self.registry_id, "registry_id")
        _stable_id(self.source_store_id, "source_store_id")
        _sha256(self.owner_scope_sha256, "owner_scope_sha256")
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 0:
            raise ValueError("revision must be an integer >= 0")
        if self.revision != len(self.revisions):
            raise ValueError("revision must equal revision count")
        previous: str | None = None
        last_source_revision = 0
        last_profile_sha256: str | None = None
        profile_id: str | None = None
        candidate_ids: set[str] = set()
        confirmation_ids: set[str] = set()
        source_revision_hashes: set[str] = set()
        profile_versions: set[str] = set()
        for sequence, item in enumerate(self.revisions, 1):
            candidate = item.candidate
            profile = candidate.profile_snapshot.to_dict()
            if item.sequence != sequence or item.previous_revision_sha256 != previous:
                raise ValueError("Owner Profile Registry revision chain is not contiguous")
            if candidate.owner_scope_sha256 != self.owner_scope_sha256:
                raise ValueError("Owner Profile Registry scope mismatch")
            if candidate.source_store_id != self.source_store_id:
                raise ValueError("Owner Profile Registry source store mismatch")
            if candidate.source_history_revision <= last_source_revision:
                raise ValueError("source Owner Profile revision must advance")
            if last_profile_sha256 is not None and candidate.baseline_profile_sha256 != last_profile_sha256:
                raise ValueError("new registry candidate baseline must equal the active registry profile")
            if profile_id is not None and profile["profile_id"] != profile_id:
                raise ValueError("registered profile identity cannot change within a registry")
            if candidate.registry_candidate_id in candidate_ids:
                raise ValueError("registry candidate replay is not allowed")
            if item.confirmation.confirmation_id in confirmation_ids:
                raise ValueError("registry confirmation replay is not allowed")
            if candidate.source_profile_revision_sha256 in source_revision_hashes:
                raise ValueError("source profile revision replay is not allowed")
            if profile["profile_version"] in profile_versions:
                raise ValueError("registered profile version replay is not allowed")
            candidate_ids.add(candidate.registry_candidate_id)
            confirmation_ids.add(item.confirmation.confirmation_id)
            source_revision_hashes.add(candidate.source_profile_revision_sha256)
            profile_versions.add(profile["profile_version"])
            last_source_revision = candidate.source_history_revision
            last_profile_sha256 = profile["profile_sha256"]
            profile_id = profile["profile_id"]
            previous = item.to_dict()["revision_sha256"]

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "record_version": REGISTRY_STORE_RECORD_VERSION,
            "record_type": "OWNER_PROFILE_REGISTRY_HISTORY",
            "task_owner": "TASK-029",
            "registry_id": self.registry_id,
            "owner_scope_sha256": self.owner_scope_sha256,
            "source_store_id": self.source_store_id,
            "revision": self.revision,
            "revisions": [item.to_dict() for item in self.revisions],
            "owner_local_profile_registry": True,
            "encrypted_at_rest_required": True,
            "explicit_human_registry_confirmation_required": True,
            "plaintext_export_authorized": False,
            "physical_delete_authorized": False,
            "runtime_profile_apply_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "automatic_promotion_authorized": False,
            "rollback_execution_authorized": False,
            "external_effect_authorized": False,
        }
        body["history_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OwnerProfileRegistryHistory":
        expected = {
            "record_version", "record_type", "task_owner", "registry_id",
            "owner_scope_sha256", "source_store_id", "revision", "revisions",
            "owner_local_profile_registry", "encrypted_at_rest_required",
            "explicit_human_registry_confirmation_required", "plaintext_export_authorized",
            "physical_delete_authorized", "runtime_profile_apply_authorized",
            "knowledge_pack_promotion_authorized", "automatic_promotion_authorized",
            "rollback_execution_authorized", "external_effect_authorized", "history_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("Owner Profile Registry history fields are incomplete or unknown")
        if (
            value["record_version"] != REGISTRY_STORE_RECORD_VERSION
            or value["record_type"] != "OWNER_PROFILE_REGISTRY_HISTORY"
            or value["task_owner"] != "TASK-029"
            or value["owner_local_profile_registry"] is not True
            or value["encrypted_at_rest_required"] is not True
            or value["explicit_human_registry_confirmation_required"] is not True
        ):
            raise ValueError("Owner Profile Registry safety identity mismatch")
        for field in (
            "plaintext_export_authorized", "physical_delete_authorized",
            "runtime_profile_apply_authorized", "knowledge_pack_promotion_authorized",
            "automatic_promotion_authorized", "rollback_execution_authorized",
            "external_effect_authorized",
        ):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        result = cls(
            value["registry_id"], value["owner_scope_sha256"], value["source_store_id"],
            value["revision"],
            tuple(OwnerProfileRegistryRevision.from_dict(row) for row in value["revisions"]),
        )
        if result.to_dict() != dict(value):
            raise ValueError("Owner Profile Registry history hash or derived fields mismatch")
        return result


@dataclass(frozen=True, slots=True)
class OwnerProfileRegistrySaveResult:
    history: OwnerProfileRegistryHistory
    write: AtomicWriteResult


class OwnerProfileRegistryStore:
    """CAS append/read of explicitly confirmed encrypted registry entries."""

    def __init__(self, path: str | Path, cipher: OwnerProfileRegistryCipher | None = None) -> None:
        self.path = Path(path)
        self.cipher = cipher if cipher is not None else WindowsDpapiOwnerProfileRegistryCipher()
        if not isinstance(self.cipher, OwnerProfileRegistryCipher):
            raise ValueError("cipher does not implement OwnerProfileRegistryCipher")
        _stable_id(self.cipher.cipher_suite, "cipher_suite")

    def _envelope(self, history: OwnerProfileRegistryHistory) -> dict[str, object]:
        ciphertext = self.cipher.encrypt(canonical_json_bytes(history.to_dict()))
        if not ciphertext or len(ciphertext) > _MAX_CIPHERTEXT_BYTES:
            raise ValueError("ciphertext size is invalid")
        body: dict[str, object] = {
            "schema_version": REGISTRY_STORE_SCHEMA_VERSION,
            "record_type": "OWNER_PROFILE_REGISTRY_STORE_ENCRYPTED",
            "task_owner": "TASK-029",
            "cipher_suite": self.cipher.cipher_suite,
            "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
            "ciphertext_sha256": sha256_bytes(ciphertext),
            "plaintext_fields_present": False,
        }
        body["document_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    def _parse_envelope(self, value: Mapping[str, Any]) -> OwnerProfileRegistryHistory:
        expected = {
            "schema_version", "record_type", "task_owner", "cipher_suite",
            "ciphertext_b64", "ciphertext_sha256", "plaintext_fields_present",
            "document_sha256",
        }
        if set(value) != expected:
            raise ValueError("encrypted registry fields are incomplete or unknown")
        if (
            value["schema_version"] != REGISTRY_STORE_SCHEMA_VERSION
            or value["record_type"] != "OWNER_PROFILE_REGISTRY_STORE_ENCRYPTED"
            or value["task_owner"] != "TASK-029"
            or value["cipher_suite"] != self.cipher.cipher_suite
            or value["plaintext_fields_present"] is not False
        ):
            raise ValueError("encrypted registry identity or plaintext boundary mismatch")
        body = {key: item for key, item in value.items() if key != "document_sha256"}
        if value["document_sha256"] != sha256_bytes(canonical_json_bytes(body)):
            raise ValueError("encrypted registry document checksum mismatch")
        ciphertext = base64.b64decode(value["ciphertext_b64"], validate=True)
        if (
            not ciphertext or len(ciphertext) > _MAX_CIPHERTEXT_BYTES
            or value["ciphertext_sha256"] != sha256_bytes(ciphertext)
        ):
            raise ValueError("encrypted registry ciphertext checksum mismatch")
        document = json.loads(self.cipher.decrypt(ciphertext).decode("utf-8"))
        if not isinstance(document, dict):
            raise ValueError("decrypted Owner Profile Registry history must be an object")
        return OwnerProfileRegistryHistory.from_dict(document)

    def load(self) -> OwnerProfileRegistryHistory:
        try:
            if self.path.is_symlink() or not self.path.is_file():
                raise ValueError("Owner Profile Registry Store must be a regular non-symlink file")
            document = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError("encrypted Owner Profile Registry Store must be an object")
            return self._parse_envelope(document)
        except ProductError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise _fail(
                "ERR_OWNER_PROFILE_REGISTRY_STORE_INTEGRITY",
                "Owner Profile Registry Store could not be decrypted and verified safely",
                ProductErrorCategory.DATA_INTEGRITY,
                reason=type(exc).__name__,
            ) from exc

    def append(
        self, *, registry_id: str, registry_candidate_id: str,
        source_profile_store: OwnerProfileStore,
        expected_source_history_revision: int,
        confirmation: OwnerProfileRegistryConfirmation,
        expected_registry_revision: int,
        failure_injector: FailureInjector | None = None,
    ) -> OwnerProfileRegistrySaveResult:
        _stable_id(registry_id, "registry_id")
        _stable_id(registry_candidate_id, "registry_candidate_id")
        _positive_int(expected_source_history_revision, "expected_source_history_revision")
        if not isinstance(expected_registry_revision, int) or isinstance(expected_registry_revision, bool) or expected_registry_revision < 0:
            raise ValueError("expected_registry_revision must be an integer >= 0")
        if not isinstance(source_profile_store, OwnerProfileStore):
            raise ValueError("source_profile_store must be an OwnerProfileStore")
        if not isinstance(confirmation, OwnerProfileRegistryConfirmation):
            raise ValueError("exact explicit Human registry confirmation is required")
        source_path = source_profile_store.path.absolute()
        registry_path = self.path.absolute()
        if source_path == registry_path:
            raise ValueError("source Owner Profile Store and Registry Store must be separate files")
        ordered_paths = sorted((source_path, registry_path), key=lambda item: os.path.normcase(str(item)))
        with ExitStack() as stack:
            for path in ordered_paths:
                stack.enter_context(exclusive_file_update_lock(path))
            source_history = source_profile_store.load()
            candidate = compile_owner_profile_registry_candidate(
                registry_candidate_id, source_history,
                expected_history_revision=expected_source_history_revision,
            )
            candidate_payload = candidate.to_dict()
            if confirmation.registry_candidate_sha256 != candidate_payload["registry_candidate_sha256"]:
                raise ValueError("exact explicit Human registry confirmation does not match the candidate")
            if self.path.exists():
                current = self.load()
                if (
                    current.registry_id != registry_id
                    or current.owner_scope_sha256 != candidate.owner_scope_sha256
                    or current.source_store_id != candidate.source_store_id
                ):
                    raise _fail(
                        "ERR_OWNER_PROFILE_REGISTRY_STORE_SCOPE",
                        "Owner Profile Registry Store scope mismatch",
                        ProductErrorCategory.AUTHORIZATION,
                    )
            else:
                if self.path.is_symlink():
                    raise _fail(
                        "ERR_OWNER_PROFILE_REGISTRY_STORE_INTEGRITY",
                        "Owner Profile Registry Store path is a symlink",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
                current = OwnerProfileRegistryHistory(
                    registry_id, candidate.owner_scope_sha256, candidate.source_store_id, 0, (),
                )
            if current.revision != expected_registry_revision:
                raise _fail(
                    "ERR_OWNER_PROFILE_REGISTRY_STORE_CONFLICT",
                    "Owner Profile Registry Store changed since it was read",
                    ProductErrorCategory.STATE,
                    expected_revision=expected_registry_revision,
                    current_revision=current.revision,
                )
            previous = current.revisions[-1].to_dict()["revision_sha256"] if current.revisions else None
            revision = OwnerProfileRegistryRevision(
                current.revision + 1, candidate, confirmation, previous,
            )
            history = OwnerProfileRegistryHistory(
                current.registry_id, current.owner_scope_sha256, current.source_store_id,
                current.revision + 1, current.revisions + (revision,),
            )
            envelope = self._envelope(history)
            write = AtomicJsonWriter.write(
                self.path, envelope, validator=lambda value: self._parse_envelope(value),
                failure_injector=failure_injector,
            )
            return OwnerProfileRegistrySaveResult(history, write)


__all__ = [
    "OwnerProfileRegistryCipher", "OwnerProfileRegistryConfirmation",
    "OwnerProfileRegistryHistory", "OwnerProfileRegistryRevision",
    "OwnerProfileRegistrySaveResult", "OwnerProfileRegistryStore",
    "REGISTRY_DPAPI_CIPHER_SUITE", "WindowsDpapiOwnerProfileRegistryCipher",
    "confirm_owner_profile_registry_registration",
]
