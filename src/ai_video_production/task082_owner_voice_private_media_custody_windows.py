"""Windows private-media custody backend for TASK-082.

The backend owns encrypted owner-voice media semantics while delegating only
root-pinned, no-replace, durable JSON persistence to ``SecureAuthorityIO``.
It never returns a host path, plaintext body, key, or reusable capability.

Production construction is Windows-only and requires Current User DPAPI plus
trusted, digest-only root and authorization verifiers.  Tests may use the
explicit ``_for_test`` constructor with synthetic bytes below an authorized
temporary root; test ciphers can never claim the production cipher suite.
"""

from __future__ import annotations

import base64
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import os
from pathlib import Path
import re
import threading
from typing import Any, Callable, Iterator, Mapping, Protocol, Sequence

from .secure_authority_io import (
    ArtifactIdentity,
    SecureAuthorityIO,
    SecureAuthorityIOError,
    SecureJsonRead,
    SecurePublishReceipt,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .task082_owner_voice_private_media_custody import (
    ArtifactClass,
    GenerationCurrentness,
    GenerationEventKind,
    LeaseDecisionKind,
    LeaseKind,
    PrivateMediaCustodyReceipt,
    PrivateMediaGenerationEvent,
    ReadPurpose,
    Task082ContractError,
    Task082FixtureLeaseSentinel,
    Task082Reason,
    WritePurpose,
    compile_fixture_read_lease_admission,
    compile_fixture_write_lease_admission,
    custody_staged_binding_sha256,
)


TASK_OWNER = "TASK-082"
WINDOWS_BACKEND_VERSION = 1
WINDOWS_BACKEND_ID = "TASK082_WINDOWS_PRIVATE_MEDIA_CUSTODY_R0"
WINDOWS_DPAPI_CIPHER_SUITE = "WINDOWS_CURRENT_USER_DPAPI_TASK082_MEDIA_V1"
WINDOWS_DPAPI_BACKEND_IDENTITY_SHA256 = sha256_bytes(
    b"TASK082_WINDOWS_CURRENT_USER_DPAPI_BACKEND_V1\0"
)

CHUNK_PLAINTEXT_BYTES = 384 * 1024
MAX_PRIVATE_MEDIA_BYTES = 512 * 1024 * 1024
MAX_CHUNKS = 2_048
_LOCK_NAME = ".task082-private-media.lock"
_MANIFEST_DOMAIN = b"TASK082_WINDOWS_PRIVATE_MEDIA_MANIFEST_V1\0"
_ROOT_BINDING_DOMAIN = b"TASK082_WINDOWS_PRIVATE_MEDIA_ROOT_BINDING_V1\0"
_WRITE_RESULT_DOMAIN = b"TASK082_WINDOWS_PRIVATE_MEDIA_WRITE_RESULT_V1\0"
_READ_RESULT_DOMAIN = b"TASK082_WINDOWS_PRIVATE_MEDIA_READ_RESULT_V1\0"
_PHYSICAL_IDENTITY_DOMAIN = b"TASK082_WINDOWS_PRIVATE_MEDIA_PHYSICAL_IDENTITY_V1\0"
_GRANT_DOMAIN = b"TASK082_WINDOWS_PRIVATE_MEDIA_GRANT_V1\0"
_ARTIFACT_DOMAIN = b"TASK082_WINDOWS_PRIVATE_MEDIA_ARTIFACT_V1\0"
_CHUNK_ENTROPY_DOMAIN = b"TASK082_WINDOWS_PRIVATE_MEDIA_CHUNK_ENTROPY_V1\0"
_LEASE_OPERATION_DOMAIN = b"TASK082_WINDOWS_PRIVATE_MEDIA_LEASE_OPERATION_V1\0"
_LEASE_OPEN_DOMAIN = b"TASK082_WINDOWS_PRIVATE_MEDIA_LEASE_OPEN_V1\0"
_LEASE_COMPLETION_DOMAIN = b"TASK082_WINDOWS_PRIVATE_MEDIA_LEASE_COMPLETION_V1\0"
_LIVE_CURRENTNESS_DOMAIN = b"TASK082_WINDOWS_PRIVATE_MEDIA_LIVE_CURRENTNESS_V1\0"
_SLOT_RESERVATION_DOMAIN = b"TASK082_WINDOWS_PRIVATE_MEDIA_SLOT_RESERVATION_V1\0"
_ROOT_OBSERVATION_DOMAIN = b"TASK082_WINDOWS_PRIVATE_MEDIA_ROOT_OBSERVATION_V1\0"
_CURRENTNESS_RESERVATION_DOMAIN = (
    b"TASK082_WINDOWS_PRIVATE_MEDIA_CURRENTNESS_RESERVATION_V1\0"
)
_WRITE_RECOVERY_DOMAIN = b"TASK082_WINDOWS_PRIVATE_MEDIA_WRITE_RECOVERY_V1\0"

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_TIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)
_PRIVATE_MARKERS = (
    "private-path",
    "host-path",
    "credential",
    "password",
    "secret",
    "token",
    "speaker-fingerprint",
)


class WindowsBackendReason(str, Enum):
    READY = "READY"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    ROOT_UNSAFE = "ROOT_UNSAFE"
    ROOT_BINDING_MISMATCH = "ROOT_BINDING_MISMATCH"
    AUTHORIZATION_REJECTED = "AUTHORIZATION_REJECTED"
    ADMISSION_REJECTED = "ADMISSION_REJECTED"
    REQUEST_INVALID = "REQUEST_INVALID"
    BODY_INVALID = "BODY_INVALID"
    BODY_DIGEST_MISMATCH = "BODY_DIGEST_MISMATCH"
    CIPHER_REJECTED = "CIPHER_REJECTED"
    PUBLISH_FAILED = "PUBLISH_FAILED"
    READ_FAILED = "READ_FAILED"
    MANIFEST_INVALID = "MANIFEST_INVALID"
    PHYSICAL_IDENTITY_MISMATCH = "PHYSICAL_IDENTITY_MISMATCH"
    CIPHERTEXT_DIGEST_MISMATCH = "CIPHERTEXT_DIGEST_MISMATCH"
    PLAINTEXT_DIGEST_MISMATCH = "PLAINTEXT_DIGEST_MISMATCH"
    CALLBACK_FAILED = "CALLBACK_FAILED"
    ZEROIZATION_NOT_CONFIRMED = "ZEROIZATION_NOT_CONFIRMED"
    RECEIPT_AS_CAPABILITY = "RECEIPT_AS_CAPABILITY"
    REPLAY = "REPLAY"
    COMPLETION_UNKNOWN = "COMPLETION_UNKNOWN"


class WindowsPrivateMediaBackendError(RuntimeError):
    """Body-free failure carrying only a stable public reason code."""

    def __init__(
        self,
        reason: WindowsBackendReason,
        *,
        completion_unknown: bool = False,
    ) -> None:
        self.reason = reason
        self.completion_unknown = completion_unknown
        super().__init__(reason.value)


class ProductionLeaseState(str, Enum):
    ISSUED = "ISSUED"
    OPEN_STARTED = "OPEN_STARTED"
    CONSUMED = "CONSUMED"
    EXPIRED = "EXPIRED"
    COMPLETION_UNKNOWN = "COMPLETION_UNKNOWN"
    FAILED_CLOSED = "FAILED_CLOSED"


def _fail(
    reason: WindowsBackendReason,
    *,
    completion_unknown: bool = False,
) -> WindowsPrivateMediaBackendError:
    return WindowsPrivateMediaBackendError(
        reason,
        completion_unknown=completion_unknown,
    )


def _digest(value: object, field: str) -> str:
    if type(value) is not str:
        raise _fail(WindowsBackendReason.REQUEST_INVALID)
    try:
        return validate_sha256(value)
    except ValueError:
        raise _fail(WindowsBackendReason.REQUEST_INVALID) from None


def _nullable_digest(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _digest(value, field)


def _identifier(value: object, field: str) -> str:
    if type(value) is not str or not _ID_RE.fullmatch(value):
        raise _fail(WindowsBackendReason.REQUEST_INVALID)
    folded = value.casefold()
    if (
        any(character in value for character in ("/", "\\", ":", "?", "#", "@"))
        or value in {".", ".."}
        or ".." in value
        or any(marker in folded for marker in _PRIVATE_MARKERS)
    ):
        raise _fail(WindowsBackendReason.REQUEST_INVALID)
    return value


def _timestamp(value: object, field: str) -> datetime:
    if type(value) is not str or not _TIME_RE.fullmatch(value):
        raise _fail(WindowsBackendReason.REQUEST_INVALID)
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise _fail(WindowsBackendReason.REQUEST_INVALID) from None
    if parsed.tzinfo != timezone.utc:
        raise _fail(WindowsBackendReason.REQUEST_INVALID)
    return parsed


def _enum(enum_type: type[Enum], value: object) -> Enum:
    if isinstance(value, enum_type):
        return value
    if type(value) is not str:
        raise _fail(WindowsBackendReason.REQUEST_INVALID)
    try:
        return enum_type(value)
    except ValueError:
        raise _fail(WindowsBackendReason.REQUEST_INVALID) from None


def _record_digest(domain: bytes, value: Mapping[str, Any], field: str) -> str:
    body = dict(value)
    body.pop(field, None)
    return sha256_bytes(domain + canonical_json_bytes(body))


def _zeroize(value: bytearray) -> bool:
    for index in range(len(value)):
        value[index] = 0
    return not any(value)


def _sha256_buffer(value: bytes | bytearray | memoryview) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _digest_bytes(value: str) -> bytes:
    _digest(value, "digest")
    return bytes.fromhex(value.removeprefix("sha256:"))


def _digest_hex(value: str) -> str:
    _digest(value, "digest")
    return value.removeprefix("sha256:")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_thaw(item) for item in value]
    return value


def _exact_mapping(value: object, fields: frozenset[str]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise _fail(WindowsBackendReason.MANIFEST_INVALID)
    snapshot = _thaw(value)
    if type(snapshot) is not dict or set(snapshot) != fields:
        raise _fail(WindowsBackendReason.MANIFEST_INVALID)
    return snapshot


def _path_binding_sha256(path: Path) -> str:
    spelling = os.path.normcase(os.path.abspath(os.fspath(path))).replace("\\", "/")
    return sha256_bytes(b"TASK082_WINDOWS_PRIVATE_ROOT_PATH_V1\0" + spelling.encode("utf-8"))


def _canonical_root(value: str | os.PathLike[str]) -> Path:
    try:
        raw = os.fspath(value)
    except TypeError:
        raise _fail(WindowsBackendReason.ROOT_UNSAFE) from None
    if type(raw) is not str or not raw or "\x00" in raw:
        raise _fail(WindowsBackendReason.ROOT_UNSAFE)
    path = Path(os.path.abspath(raw))
    anchor = path.anchor
    if not anchor:
        raise _fail(WindowsBackendReason.ROOT_UNSAFE)
    relative_parts = path.parts[1:] if path.parts and path.parts[0] == anchor else path.parts
    if len(relative_parts) < 2:
        raise _fail(WindowsBackendReason.ROOT_UNSAFE)
    try:
        if not path.exists() or not path.is_dir() or path.is_symlink():
            raise _fail(WindowsBackendReason.ROOT_UNSAFE)
    except OSError:
        raise _fail(WindowsBackendReason.ROOT_UNSAFE) from None
    return path


@dataclass(frozen=True, slots=True, repr=False)
class WindowsPrivateMediaRootBinding:
    root_path_binding_sha256: str
    root_identity_sha256: str
    root_security_sha256: str
    principal_sid_sha256: str
    cipher_backend_identity_sha256: str
    observed_at: str
    fresh_until: str
    h1_authorization_sha256: str
    binding_sha256: str

    @classmethod
    def create(
        cls,
        *,
        root_path_binding_sha256: str,
        root_identity_sha256: str,
        root_security_sha256: str,
        principal_sid_sha256: str,
        cipher_backend_identity_sha256: str,
        observed_at: str,
        fresh_until: str,
        h1_authorization_sha256: str,
    ) -> "WindowsPrivateMediaRootBinding":
        body = {
            "root_path_binding_sha256": root_path_binding_sha256,
            "root_identity_sha256": root_identity_sha256,
            "root_security_sha256": root_security_sha256,
            "principal_sid_sha256": principal_sid_sha256,
            "cipher_backend_identity_sha256": cipher_backend_identity_sha256,
            "observed_at": observed_at,
            "fresh_until": fresh_until,
            "h1_authorization_sha256": h1_authorization_sha256,
            "binding_sha256": None,
        }
        body["binding_sha256"] = _record_digest(
            _ROOT_BINDING_DOMAIN,
            body,
            "binding_sha256",
        )
        return cls(**body)  # type: ignore[arg-type]

    def validate(self, *, observed_at: str) -> None:
        if type(self) is not WindowsPrivateMediaRootBinding:
            raise _fail(WindowsBackendReason.ROOT_BINDING_MISMATCH)
        for field in (
            "root_path_binding_sha256",
            "root_identity_sha256",
            "root_security_sha256",
            "principal_sid_sha256",
            "cipher_backend_identity_sha256",
            "h1_authorization_sha256",
            "binding_sha256",
        ):
            _digest(getattr(self, field), field)
        observed = _timestamp(self.observed_at, "observed_at")
        fresh = _timestamp(self.fresh_until, "fresh_until")
        now = _timestamp(observed_at, "operation_observed_at")
        if not observed <= now < fresh:
            raise _fail(WindowsBackendReason.ROOT_BINDING_MISMATCH)
        if self.binding_sha256 != _record_digest(
            _ROOT_BINDING_DOMAIN,
            {
                "root_path_binding_sha256": self.root_path_binding_sha256,
                "root_identity_sha256": self.root_identity_sha256,
                "root_security_sha256": self.root_security_sha256,
                "principal_sid_sha256": self.principal_sid_sha256,
                "cipher_backend_identity_sha256": self.cipher_backend_identity_sha256,
                "observed_at": self.observed_at,
                "fresh_until": self.fresh_until,
                "h1_authorization_sha256": self.h1_authorization_sha256,
                "binding_sha256": self.binding_sha256,
            },
            "binding_sha256",
        ):
            raise _fail(WindowsBackendReason.ROOT_BINDING_MISMATCH)

    def __reduce__(self) -> Any:
        raise TypeError(WindowsBackendReason.RECEIPT_AS_CAPABILITY.value)

    def __repr__(self) -> str:
        return "<WindowsPrivateMediaRootBinding body-free>"


@dataclass(frozen=True, slots=True, repr=False)
class WindowsPrivateMediaWriteGrant:
    purpose: WritePurpose | str
    expected_purpose: WritePurpose | str
    producer_task: str
    producer_output_role: str
    artifact_class: ArtifactClass | str
    operation_id: str
    expected_operation_id: str
    logical_slot_ref: str
    generation_revision: int
    expected_generation_revision: int
    event_revision: int
    predecessor_event_sha256: str | None
    predecessor_receipt_sha256: str | None
    owner_subject_revision_sha256: str
    expected_owner_subject_revision_sha256: str
    consent_scope: str
    consent_rights_revision_sha256: str
    expected_consent_rights_revision_sha256: str
    current_event_head_sha256: str | None
    expected_event_head_sha256: str | None
    producer_output_record_type: str
    expected_producer_output_record_type: str
    producer_output_receipt_sha256: str
    expected_producer_output_receipt_sha256: str
    producer_output_currentness_sha256: str
    expected_producer_output_currentness_sha256: str
    producer_output_current: bool
    expected_content_sha256: str
    media_metadata_sha256: str
    trusted_time_binding_sha256: str
    created_at: str
    issued_at: str
    expires_at: str
    observed_at: str
    fresh_until: str
    root_binding_sha256: str
    backend_authorization_sha256: str
    revoked: bool = False
    receipt_as_capability: bool = False

    def __repr__(self) -> str:
        return "<WindowsPrivateMediaWriteGrant body-free>"

    def __reduce__(self) -> Any:
        raise TypeError(WindowsBackendReason.RECEIPT_AS_CAPABILITY.value)


@dataclass(frozen=True, slots=True, repr=False)
class WindowsPrivateMediaReadGrant:
    receipt: PrivateMediaCustodyReceipt
    currentness: GenerationCurrentness
    purpose: ReadPurpose | str
    expected_purpose: ReadPurpose | str
    consumer_task: str
    operation_id: str
    expected_operation_id: str
    expected_owner_subject_revision_sha256: str
    expected_consent_rights_revision_sha256: str
    issued_at: str
    expires_at: str
    observed_at: str
    root_binding_sha256: str
    backend_authorization_sha256: str
    asset_adoption_readback_sha256: str | None = None
    expected_asset_adoption_readback_sha256: str | None = None
    producer_output_receipt_sha256: str | None = None
    expected_producer_output_receipt_sha256: str | None = None
    dataset_review_binding_sha256: str | None = None
    expected_dataset_review_binding_sha256: str | None = None
    dataset_snapshot_sha256: str | None = None
    expected_dataset_snapshot_sha256: str | None = None
    durable_job_head_sha256: str | None = None
    expected_durable_job_head_sha256: str | None = None
    run_recipe_binding_sha256: str | None = None
    expected_run_recipe_binding_sha256: str | None = None
    h3_authorization_sha256: str | None = None
    expected_h3_authorization_sha256: str | None = None
    training_compound_operation_sha256: str | None = None
    expected_training_compound_operation_sha256: str | None = None
    revoked: bool = False
    receipt_as_capability: bool = False

    def __repr__(self) -> str:
        return "<WindowsPrivateMediaReadGrant body-free>"

    def __reduce__(self) -> Any:
        raise TypeError(WindowsBackendReason.RECEIPT_AS_CAPABILITY.value)


class WindowsPrivateMediaCipher(Protocol):
    cipher_suite: str
    backend_identity_sha256: str

    def seal(self, plaintext: bytearray, *, entropy: bytes) -> bytes: ...

    def open(self, ciphertext: bytes, *, entropy: bytes) -> bytearray: ...


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _mutable_blob(value: bytearray) -> tuple[_DataBlob, object]:
    if not value:
        raise _fail(WindowsBackendReason.CIPHER_REJECTED)
    buffer = (ctypes.c_ubyte * len(value)).from_buffer(value)
    return _DataBlob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer


def _bytes_blob(value: bytes) -> tuple[_DataBlob, object]:
    if not value:
        raise _fail(WindowsBackendReason.CIPHER_REJECTED)
    buffer = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
    return _DataBlob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer


class WindowsCurrentUserDpapiPrivateMediaCipher:
    """Windows Current User DPAPI with per-chunk TASK-082 entropy."""

    __slots__ = ()
    cipher_suite = WINDOWS_DPAPI_CIPHER_SUITE
    backend_identity_sha256 = WINDOWS_DPAPI_BACKEND_IDENTITY_SHA256
    _UI_FORBIDDEN = 0x1

    def __init__(self) -> None:
        if os.name != "nt":
            raise _fail(WindowsBackendReason.BACKEND_UNAVAILABLE)

    @staticmethod
    def _crypt(
        value: bytearray | bytes,
        *,
        entropy: bytes,
        protect: bool,
    ) -> bytes | bytearray:
        if type(entropy) is not bytes or len(entropy) != 32:
            raise _fail(WindowsBackendReason.CIPHER_REJECTED)
        in_blob, in_buffer = (
            _mutable_blob(value) if type(value) is bytearray else _bytes_blob(value)
        )
        entropy_blob, entropy_buffer = _bytes_blob(entropy)
        output_blob = _DataBlob()
        crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        function = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
        function.argtypes = [
            ctypes.POINTER(_DataBlob),
            ctypes.c_wchar_p,
            ctypes.POINTER(_DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(_DataBlob),
        ]
        function.restype = wintypes.BOOL
        if not function(
            ctypes.byref(in_blob),
            None,
            ctypes.byref(entropy_blob),
            None,
            None,
            WindowsCurrentUserDpapiPrivateMediaCipher._UI_FORBIDDEN,
            ctypes.byref(output_blob),
        ):
            raise _fail(WindowsBackendReason.CIPHER_REJECTED)
        try:
            if protect:
                return ctypes.string_at(output_blob.pbData, output_blob.cbData)
            plaintext = bytearray(int(output_blob.cbData))
            if plaintext:
                target = (ctypes.c_ubyte * len(plaintext)).from_buffer(plaintext)
                ctypes.memmove(target, output_blob.pbData, len(plaintext))
            return plaintext
        finally:
            if output_blob.pbData:
                wipe_failed = False
                try:
                    if not protect and output_blob.cbData:
                        ctypes.memset(
                            output_blob.pbData,
                            0,
                            int(output_blob.cbData),
                        )
                except Exception:
                    wipe_failed = True
                finally:
                    kernel32.LocalFree(
                        ctypes.cast(output_blob.pbData, ctypes.c_void_p)
                    )
                if wipe_failed:
                    raise _fail(WindowsBackendReason.ZEROIZATION_NOT_CONFIRMED)
            _ = in_buffer, entropy_buffer

    def seal(self, plaintext: bytearray, *, entropy: bytes) -> bytes:
        result = self._crypt(plaintext, entropy=entropy, protect=True)
        if type(result) is not bytes:
            raise _fail(WindowsBackendReason.CIPHER_REJECTED)
        return result

    def open(self, ciphertext: bytes, *, entropy: bytes) -> bytearray:
        result = self._crypt(ciphertext, entropy=entropy, protect=False)
        if type(result) is not bytearray:
            raise _fail(WindowsBackendReason.CIPHER_REJECTED)
        return result


@dataclass(frozen=True, slots=True, repr=False)
class WindowsPrivateMediaRootObservation:
    root_path_binding_sha256: str
    root_identity_sha256: str
    root_security_sha256: str
    principal_sid_sha256: str
    cipher_backend_identity_sha256: str
    root_binding_sha256: str
    observed_at: str
    observation_sha256: str

    @classmethod
    def create(
        cls,
        *,
        root_path_binding_sha256: str,
        root_identity_sha256: str,
        root_security_sha256: str,
        principal_sid_sha256: str,
        cipher_backend_identity_sha256: str,
        root_binding_sha256: str,
        observed_at: str,
    ) -> "WindowsPrivateMediaRootObservation":
        body = {
            "root_path_binding_sha256": root_path_binding_sha256,
            "root_identity_sha256": root_identity_sha256,
            "root_security_sha256": root_security_sha256,
            "principal_sid_sha256": principal_sid_sha256,
            "cipher_backend_identity_sha256": cipher_backend_identity_sha256,
            "root_binding_sha256": root_binding_sha256,
            "observed_at": observed_at,
            "observation_sha256": None,
        }
        for field in (
            "root_path_binding_sha256",
            "root_identity_sha256",
            "root_security_sha256",
            "principal_sid_sha256",
            "cipher_backend_identity_sha256",
            "root_binding_sha256",
        ):
            _digest(body[field], field)
        _timestamp(observed_at, "observed_at")
        body["observation_sha256"] = _record_digest(
            _ROOT_OBSERVATION_DOMAIN,
            body,
            "observation_sha256",
        )
        return cls(**body)  # type: ignore[arg-type]

    def validate(
        self,
        *,
        binding: WindowsPrivateMediaRootBinding,
        observed_at: str,
    ) -> None:
        if type(self) is not WindowsPrivateMediaRootObservation:
            raise _fail(WindowsBackendReason.ROOT_BINDING_MISMATCH)
        body = {
            "root_path_binding_sha256": self.root_path_binding_sha256,
            "root_identity_sha256": self.root_identity_sha256,
            "root_security_sha256": self.root_security_sha256,
            "principal_sid_sha256": self.principal_sid_sha256,
            "cipher_backend_identity_sha256": self.cipher_backend_identity_sha256,
            "root_binding_sha256": self.root_binding_sha256,
            "observed_at": self.observed_at,
            "observation_sha256": self.observation_sha256,
        }
        if (
            self.root_path_binding_sha256 != binding.root_path_binding_sha256
            or self.root_identity_sha256 != binding.root_identity_sha256
            or self.root_security_sha256 != binding.root_security_sha256
            or self.principal_sid_sha256 != binding.principal_sid_sha256
            or self.cipher_backend_identity_sha256
            != binding.cipher_backend_identity_sha256
            or self.root_binding_sha256 != binding.binding_sha256
            or self.observed_at != observed_at
            or self.observation_sha256
            != _record_digest(
                _ROOT_OBSERVATION_DOMAIN,
                body,
                "observation_sha256",
            )
        ):
            raise _fail(WindowsBackendReason.ROOT_BINDING_MISMATCH)
        _digest(self.observation_sha256, "observation_sha256")
        _timestamp(self.observed_at, "observed_at")

    def __repr__(self) -> str:
        return "<WindowsPrivateMediaRootObservation body-free>"


@dataclass(frozen=True, slots=True, repr=False)
class WindowsPrivateMediaCurrentnessReservationReceipt:
    lease_kind: LeaseKind
    operation_id: str
    grant_sha256: str
    currentness_binding_sha256: str
    canonical_head_sha256: str | None
    acquired_at: str
    expires_at: str
    exclusive: bool
    replayable: bool
    reservation_sha256: str

    @classmethod
    def create(
        cls,
        *,
        lease_kind: LeaseKind,
        operation_id: str,
        grant_sha256: str,
        currentness_binding_sha256: str,
        canonical_head_sha256: str | None,
        acquired_at: str,
        expires_at: str,
    ) -> "WindowsPrivateMediaCurrentnessReservationReceipt":
        if type(lease_kind) is not LeaseKind:
            raise _fail(WindowsBackendReason.AUTHORIZATION_REJECTED)
        body = {
            "lease_kind": lease_kind.value,
            "operation_id": _identifier(operation_id, "operation_id"),
            "grant_sha256": _digest(grant_sha256, "grant_sha256"),
            "currentness_binding_sha256": _digest(
                currentness_binding_sha256,
                "currentness_binding_sha256",
            ),
            "canonical_head_sha256": _nullable_digest(
                canonical_head_sha256,
                "canonical_head_sha256",
            ),
            "acquired_at": acquired_at,
            "expires_at": expires_at,
            "exclusive": True,
            "replayable": False,
            "reservation_sha256": None,
        }
        acquired = _timestamp(acquired_at, "acquired_at")
        expires = _timestamp(expires_at, "expires_at")
        if acquired >= expires:
            raise _fail(WindowsBackendReason.AUTHORIZATION_REJECTED)
        body["reservation_sha256"] = _record_digest(
            _CURRENTNESS_RESERVATION_DOMAIN,
            body,
            "reservation_sha256",
        )
        return cls(
            lease_kind=lease_kind,
            operation_id=body["operation_id"],
            grant_sha256=body["grant_sha256"],
            currentness_binding_sha256=body["currentness_binding_sha256"],
            canonical_head_sha256=body["canonical_head_sha256"],
            acquired_at=acquired_at,
            expires_at=expires_at,
            exclusive=True,
            replayable=False,
            reservation_sha256=body["reservation_sha256"],
        )

    def validate(
        self,
        *,
        lease_kind: LeaseKind,
        operation_id: str,
        grant_sha256: str,
        currentness_binding_sha256: str,
        canonical_head_sha256: str | None,
        acquired_at: str,
        expires_at: str,
    ) -> None:
        if type(self) is not WindowsPrivateMediaCurrentnessReservationReceipt:
            raise _fail(WindowsBackendReason.AUTHORIZATION_REJECTED)
        body = {
            "lease_kind": self.lease_kind.value,
            "operation_id": self.operation_id,
            "grant_sha256": self.grant_sha256,
            "currentness_binding_sha256": self.currentness_binding_sha256,
            "canonical_head_sha256": self.canonical_head_sha256,
            "acquired_at": self.acquired_at,
            "expires_at": self.expires_at,
            "exclusive": self.exclusive,
            "replayable": self.replayable,
            "reservation_sha256": self.reservation_sha256,
        }
        if (
            self.lease_kind is not lease_kind
            or self.operation_id != operation_id
            or self.grant_sha256 != grant_sha256
            or self.currentness_binding_sha256 != currentness_binding_sha256
            or self.canonical_head_sha256 != canonical_head_sha256
            or self.acquired_at != acquired_at
            or self.expires_at != expires_at
            or self.exclusive is not True
            or self.replayable is not False
            or self.reservation_sha256
            != _record_digest(
                _CURRENTNESS_RESERVATION_DOMAIN,
                body,
                "reservation_sha256",
            )
        ):
            raise _fail(WindowsBackendReason.AUTHORIZATION_REJECTED)
        _digest(self.reservation_sha256, "reservation_sha256")
        acquired = _timestamp(self.acquired_at, "acquired_at")
        expires = _timestamp(self.expires_at, "expires_at")
        if acquired >= expires:
            raise _fail(WindowsBackendReason.AUTHORIZATION_REJECTED)

    def __repr__(self) -> str:
        return "<WindowsPrivateMediaCurrentnessReservationReceipt body-free>"


AuthorizationVerifier = Callable[[LeaseKind, str, str], bool]
CurrentnessVerifier = Callable[[LeaseKind, str, str], bool]
CurrentnessReservationVerifier = Callable[
    [LeaseKind, str, str, str, str | None, str, str],
    WindowsPrivateMediaCurrentnessReservationReceipt,
]
RootBindingVerifier = Callable[
    [Path, WindowsPrivateMediaRootBinding, str],
    WindowsPrivateMediaRootObservation,
]
TrustedTimeProvider = Callable[[], str]
StageHook = Callable[[str], None]
PrivateMediaConsumer = Callable[[memoryview], None]


def _grant_projection(grant: object) -> dict[str, Any]:
    if type(grant) is WindowsPrivateMediaWriteGrant:
        value = {
            field: getattr(grant, field)
            for field in grant.__dataclass_fields__  # type: ignore[attr-defined]
        }
        for field in ("purpose", "expected_purpose", "artifact_class"):
            if isinstance(value[field], Enum):
                value[field] = value[field].value
        return value
    if type(grant) is WindowsPrivateMediaReadGrant:
        value = {
            field: getattr(grant, field)
            for field in grant.__dataclass_fields__  # type: ignore[attr-defined]
            if field not in {"receipt", "currentness"}
        }
        for field in ("purpose", "expected_purpose"):
            if isinstance(value[field], Enum):
                value[field] = value[field].value
        value["receipt_sha256"] = grant.receipt.receipt_sha256
        value["currentness_sha256"] = grant.currentness.currentness_sha256
        return value
    raise _fail(WindowsBackendReason.REQUEST_INVALID)


def _grant_sha256(grant: object) -> str:
    return sha256_bytes(_GRANT_DOMAIN + canonical_json_bytes(_grant_projection(grant)))


def _identity_projection(
    role: str,
    relative_name: str,
    observation: SecurePublishReceipt | SecureJsonRead,
) -> dict[str, Any]:
    identity = observation.identity
    return {
        "role": role,
        "relative_name_sha256": sha256_bytes(relative_name.encode("ascii")),
        "payload_sha256": observation.sha256,
        "byte_count": observation.byte_count,
        "security_sha256": observation.security_sha256,
        "identity": {
            "device": identity.device,
            "inode": identity.inode,
            "mode": identity.mode,
            "nlink": identity.nlink,
            "size": identity.size,
            "mtime_ns": identity.mtime_ns,
            "reparse_point": identity.reparse_point,
        },
    }


def _identity_sha256(value: Mapping[str, Any]) -> str:
    return sha256_bytes(_PHYSICAL_IDENTITY_DOMAIN + canonical_json_bytes(value))


def _aggregate_physical_identity_sha256(
    manifest_name: str,
    manifest: SecurePublishReceipt | SecureJsonRead,
    chunks: Sequence[tuple[str, SecurePublishReceipt | SecureJsonRead]],
) -> str:
    projection = {
        "manifest": _identity_projection("MANIFEST", manifest_name, manifest),
        "chunks": [
            _identity_projection(f"CHUNK_{index}", name, observation)
            for index, (name, observation) in enumerate(chunks)
        ],
    }
    return _identity_sha256(projection)


def _same_pinned_observation(
    published: SecurePublishReceipt,
    readback: SecureJsonRead,
) -> bool:
    return (
        published.sha256 == readback.sha256
        and published.byte_count == readback.byte_count
        and published.identity == readback.identity
        and published.security_sha256 == readback.security_sha256
    )


def _record_observation_sha256(
    role: str,
    relative_name: str,
    observation: SecurePublishReceipt | SecureJsonRead,
) -> str:
    return _identity_sha256(_identity_projection(role, relative_name, observation))


@dataclass(frozen=True, slots=True)
class WindowsPrivateMediaWriteResult:
    receipt: PrivateMediaCustodyReceipt
    generation_event: PrivateMediaGenerationEvent
    write_publish_pinned_readback_sha256: str
    plaintext_byte_count: int
    chunk_count: int
    body_zeroization_confirmed: bool
    production_backend_invoked: bool
    private_media_effect_count: int
    result_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_type": "Task082WindowsPrivateMediaWriteResultV1",
            "schema_version": 1,
            "canonical_owner_task": TASK_OWNER,
            "receipt": self.receipt.as_dict(),
            "generation_event": self.generation_event.as_dict(),
            "write_publish_pinned_readback_sha256": self.write_publish_pinned_readback_sha256,
            "plaintext_byte_count": self.plaintext_byte_count,
            "chunk_count": self.chunk_count,
            "body_zeroization_confirmed": self.body_zeroization_confirmed,
            "production_backend_invoked": self.production_backend_invoked,
            "private_media_effect_count": self.private_media_effect_count,
            "result_sha256": self.result_sha256,
        }


@dataclass(frozen=True, slots=True)
class WindowsPrivateMediaReadResult:
    receipt_sha256: str
    operation_id: str
    read_close_handle_identity_sha256: str
    read_completion_readback_sha256: str
    plaintext_byte_count: int
    body_zeroization_confirmed: bool
    callback_completed: bool
    production_backend_invoked: bool
    private_media_effect_count: int
    result_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_type": "Task082WindowsPrivateMediaReadResultV1",
            "schema_version": 1,
            "canonical_owner_task": TASK_OWNER,
            "receipt_sha256": self.receipt_sha256,
            "operation_id": self.operation_id,
            "read_close_handle_identity_sha256": self.read_close_handle_identity_sha256,
            "read_completion_readback_sha256": self.read_completion_readback_sha256,
            "plaintext_byte_count": self.plaintext_byte_count,
            "body_zeroization_confirmed": self.body_zeroization_confirmed,
            "callback_completed": self.callback_completed,
            "production_backend_invoked": self.production_backend_invoked,
            "private_media_effect_count": self.private_media_effect_count,
            "result_sha256": self.result_sha256,
        }


@dataclass(frozen=True, slots=True)
class WindowsPrivateMediaLeaseStateReadback:
    lease_kind: LeaseKind
    operation_id: str
    state: ProductionLeaseState
    replayable: bool
    body_returned: bool
    capability_returned: bool
    durable: bool
    issuance_record_sha256: str | None
    burn_record_sha256: str | None
    completion_record_sha256: str | None
    currentness_reservation_sha256: str | None
    write_recovery_record_sha256: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "lease_kind": self.lease_kind.value,
            "operation_id": self.operation_id,
            "state": self.state.value,
            "replayable": self.replayable,
            "body_returned": self.body_returned,
            "capability_returned": self.capability_returned,
            "durable": self.durable,
            "issuance_record_sha256": self.issuance_record_sha256,
            "burn_record_sha256": self.burn_record_sha256,
            "completion_record_sha256": self.completion_record_sha256,
            "currentness_reservation_sha256": self.currentness_reservation_sha256,
            "write_recovery_record_sha256": self.write_recovery_record_sha256,
        }


_LEASE_TOKEN = object()


class _ProductionLease:
    __slots__ = (
        "_backend_nonce",
        "_burn_record_sha256",
        "_completion_record_sha256",
        "_currentness_reservation_sha256",
        "_grant",
        "_issuance_record_sha256",
        "_kind",
        "_operation_id",
        "_state",
        "_state_lock",
        "_write_recovery_record_sha256",
    )

    def __init__(
        self,
        token: object,
        *,
        backend_nonce: object,
        grant: WindowsPrivateMediaWriteGrant | WindowsPrivateMediaReadGrant,
        kind: LeaseKind,
        issuance_record_sha256: str,
    ) -> None:
        if token is not _LEASE_TOKEN or type(self) is _ProductionLease:
            raise _fail(WindowsBackendReason.RECEIPT_AS_CAPABILITY)
        object.__setattr__(self, "_backend_nonce", backend_nonce)
        object.__setattr__(self, "_grant", grant)
        object.__setattr__(self, "_kind", kind)
        object.__setattr__(self, "_operation_id", grant.operation_id)
        object.__setattr__(self, "_state", ProductionLeaseState.ISSUED)
        object.__setattr__(self, "_state_lock", threading.Lock())
        object.__setattr__(self, "_issuance_record_sha256", issuance_record_sha256)
        object.__setattr__(self, "_burn_record_sha256", None)
        object.__setattr__(self, "_completion_record_sha256", None)
        object.__setattr__(self, "_currentness_reservation_sha256", None)
        object.__setattr__(self, "_write_recovery_record_sha256", None)

    def __setattr__(self, name: str, value: Any) -> None:
        raise TypeError(WindowsBackendReason.RECEIPT_AS_CAPABILITY.value)

    def __reduce__(self) -> Any:
        raise TypeError(WindowsBackendReason.RECEIPT_AS_CAPABILITY.value)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} redacted state={self._state.value}>"

    @property
    def state(self) -> ProductionLeaseState:
        with self._state_lock:
            return self._state

    def _transition(
        self,
        nonce: object,
        state: ProductionLeaseState,
        *,
        burn_record_sha256: str | None = None,
        completion_record_sha256: str | None = None,
        currentness_reservation_sha256: str | None = None,
        write_recovery_record_sha256: str | None = None,
    ) -> None:
        if nonce is not self._backend_nonce:
            raise _fail(WindowsBackendReason.RECEIPT_AS_CAPABILITY)
        allowed = {
            ProductionLeaseState.ISSUED: {
                ProductionLeaseState.OPEN_STARTED,
                ProductionLeaseState.EXPIRED,
                ProductionLeaseState.FAILED_CLOSED,
                ProductionLeaseState.COMPLETION_UNKNOWN,
            },
            ProductionLeaseState.OPEN_STARTED: {
                ProductionLeaseState.CONSUMED,
                ProductionLeaseState.COMPLETION_UNKNOWN,
                ProductionLeaseState.FAILED_CLOSED,
            },
        }
        with self._state_lock:
            if state not in allowed.get(self._state, set()):
                raise _fail(WindowsBackendReason.REPLAY)
            object.__setattr__(self, "_state", state)
            if burn_record_sha256 is not None:
                object.__setattr__(self, "_burn_record_sha256", burn_record_sha256)
            if completion_record_sha256 is not None:
                object.__setattr__(
                    self,
                    "_completion_record_sha256",
                    completion_record_sha256,
                )
            if currentness_reservation_sha256 is not None:
                object.__setattr__(
                    self,
                    "_currentness_reservation_sha256",
                    currentness_reservation_sha256,
                )
            if write_recovery_record_sha256 is not None:
                object.__setattr__(
                    self,
                    "_write_recovery_record_sha256",
                    write_recovery_record_sha256,
                )


class Task082PrivateMediaWriteLeaseV1(_ProductionLease):
    __slots__ = ()


class Task082PrivateMediaReadLeaseV1(_ProductionLease):
    __slots__ = ()


_CHUNK_FIELDS = frozenset(
    {
        "record_type",
        "schema_version",
        "canonical_owner_task",
        "cipher_suite",
        "cipher_backend_identity_sha256",
        "artifact_key_sha256",
        "chunk_index",
        "chunk_count",
        "plaintext_byte_count",
        "plaintext_chunk_sha256",
        "entropy_sha256",
        "ciphertext_sha256",
        "ciphertext_b64",
    }
)
_CHUNK_DESCRIPTOR_FIELDS = frozenset(
    {
        "relative_name",
        "chunk_index",
        "plaintext_byte_count",
        "plaintext_chunk_sha256",
        "entropy_sha256",
        "ciphertext_sha256",
        "publish_identity_sha256",
    }
)
_MANIFEST_FIELDS = frozenset(
    {
        "record_type",
        "schema_version",
        "canonical_owner_task",
        "backend_id",
        "cipher_suite",
        "cipher_backend_identity_sha256",
        "root_binding_sha256",
        "backend_authorization_sha256",
        "artifact_key_sha256",
        "opaque_artifact_id",
        "logical_slot_ref",
        "artifact_class",
        "generation_revision",
        "content_sha256",
        "media_metadata_sha256",
        "plaintext_byte_count",
        "chunk_count",
        "chunks",
        "manifest_sha256",
    }
)
_LEASE_ISSUANCE_FIELDS = frozenset(
    {
        "record_type",
        "schema_version",
        "canonical_owner_task",
        "lease_kind",
        "operation_id",
        "grant_sha256",
        "root_binding_sha256",
        "root_observation_sha256",
        "backend_authorization_sha256",
        "currentness_binding_sha256",
        "body_binding_sha256",
        "admitted_at",
        "state",
        "record_sha256",
    }
)
_LEASE_OPEN_FIELDS = frozenset(
    {
        "record_type",
        "schema_version",
        "canonical_owner_task",
        "lease_kind",
        "operation_id",
        "grant_sha256",
        "issuance_record_sha256",
        "root_binding_sha256",
        "root_observation_sha256",
        "currentness_binding_sha256",
        "currentness_reservation_sha256",
        "body_binding_sha256",
        "opened_at",
        "state",
        "record_sha256",
    }
)
_LEASE_COMPLETION_FIELDS = frozenset(
    {
        "record_type",
        "schema_version",
        "canonical_owner_task",
        "lease_kind",
        "operation_id",
        "grant_sha256",
        "issuance_record_sha256",
        "burn_record_sha256",
        "currentness_reservation_sha256",
        "write_recovery_record_sha256",
        "receipt_sha256",
        "completion_kind",
        "completion_binding_sha256",
        "body_zeroization_confirmed",
        "callback_completed",
        "completed_at",
        "state",
        "record_sha256",
    }
)
_SLOT_RESERVATION_FIELDS = frozenset(
    {
        "record_type",
        "schema_version",
        "canonical_owner_task",
        "logical_slot_ref",
        "artifact_class",
        "generation_revision",
        "operation_id",
        "grant_sha256",
        "predecessor_event_sha256",
        "predecessor_receipt_sha256",
        "currentness_binding_sha256",
        "currentness_reservation_sha256",
        "root_observation_sha256",
        "burn_record_sha256",
        "reserved_at",
        "record_sha256",
    }
)
_WRITE_RECOVERY_FIELDS = frozenset(
    {
        "record_type",
        "schema_version",
        "canonical_owner_task",
        "operation_id",
        "grant_sha256",
        "receipt",
        "generation_event",
        "write_publish_pinned_readback_sha256",
        "plaintext_byte_count",
        "chunk_count",
        "body_zeroization_confirmed",
        "production_backend_invoked",
        "private_media_effect_count",
        "result_sha256",
        "record_sha256",
    }
)


class WindowsPrivateMediaCustodyBackend:
    """One-use production lease broker and encrypted chunk custody backend."""

    __slots__ = (
        "_root",
        "_root_binding",
        "_authorization_verifier",
        "_currentness_verifier",
        "_currentness_reservation_verifier",
        "_root_binding_verifier",
        "_trusted_time_provider",
        "_cipher",
        "_io",
        "_nonce",
        "_test_only",
        "_stage_hook",
        "_claim_lock",
    )

    def __init__(
        self,
        root: str | os.PathLike[str],
        *,
        root_binding: WindowsPrivateMediaRootBinding,
        authorization_verifier: AuthorizationVerifier,
        currentness_verifier: CurrentnessVerifier,
        currentness_reservation_verifier: CurrentnessReservationVerifier,
        root_binding_verifier: RootBindingVerifier,
        trusted_time_provider: TrustedTimeProvider,
        cipher: WindowsPrivateMediaCipher | None = None,
    ) -> None:
        self._initialize(
            root,
            root_binding=root_binding,
            authorization_verifier=authorization_verifier,
            currentness_verifier=currentness_verifier,
            currentness_reservation_verifier=currentness_reservation_verifier,
            root_binding_verifier=root_binding_verifier,
            trusted_time_provider=trusted_time_provider,
            cipher=cipher or WindowsCurrentUserDpapiPrivateMediaCipher(),
            test_only=False,
            stage_hook=None,
        )

    @classmethod
    def _for_test(
        cls,
        root: str | os.PathLike[str],
        *,
        root_binding: WindowsPrivateMediaRootBinding,
        authorization_verifier: AuthorizationVerifier,
        currentness_verifier: CurrentnessVerifier,
        currentness_reservation_verifier: CurrentnessReservationVerifier,
        root_binding_verifier: RootBindingVerifier,
        trusted_time_provider: TrustedTimeProvider,
        cipher: WindowsPrivateMediaCipher,
        stage_hook: StageHook | None = None,
    ) -> "WindowsPrivateMediaCustodyBackend":
        instance = object.__new__(cls)
        instance._initialize(
            root,
            root_binding=root_binding,
            authorization_verifier=authorization_verifier,
            currentness_verifier=currentness_verifier,
            currentness_reservation_verifier=currentness_reservation_verifier,
            root_binding_verifier=root_binding_verifier,
            trusted_time_provider=trusted_time_provider,
            cipher=cipher,
            test_only=True,
            stage_hook=stage_hook,
        )
        return instance

    def _initialize(
        self,
        root: str | os.PathLike[str],
        *,
        root_binding: WindowsPrivateMediaRootBinding,
        authorization_verifier: AuthorizationVerifier,
        currentness_verifier: CurrentnessVerifier,
        currentness_reservation_verifier: CurrentnessReservationVerifier,
        root_binding_verifier: RootBindingVerifier,
        trusted_time_provider: TrustedTimeProvider,
        cipher: WindowsPrivateMediaCipher,
        test_only: bool,
        stage_hook: StageHook | None,
    ) -> None:
        canonical_root = _canonical_root(root)
        if not all(
            callable(value)
            for value in (
                authorization_verifier,
                currentness_verifier,
                currentness_reservation_verifier,
                root_binding_verifier,
                trusted_time_provider,
            )
        ):
            raise _fail(WindowsBackendReason.AUTHORIZATION_REJECTED)
        if type(test_only) is not bool or (stage_hook is not None and not callable(stage_hook)):
            raise _fail(WindowsBackendReason.REQUEST_INVALID)
        if not test_only and os.name != "nt":
            raise _fail(WindowsBackendReason.BACKEND_UNAVAILABLE)
        if not all(
            hasattr(cipher, name)
            for name in ("cipher_suite", "backend_identity_sha256", "seal", "open")
        ):
            raise _fail(WindowsBackendReason.CIPHER_REJECTED)
        _identifier(cipher.cipher_suite, "cipher_suite")
        _digest(cipher.backend_identity_sha256, "backend_identity_sha256")
        if not test_only and (
            type(cipher) is not WindowsCurrentUserDpapiPrivateMediaCipher
            or cipher.cipher_suite != WINDOWS_DPAPI_CIPHER_SUITE
            or cipher.backend_identity_sha256 != WINDOWS_DPAPI_BACKEND_IDENTITY_SHA256
        ):
            raise _fail(WindowsBackendReason.CIPHER_REJECTED)
        if test_only and (
            cipher.cipher_suite == WINDOWS_DPAPI_CIPHER_SUITE
            or cipher.backend_identity_sha256 == WINDOWS_DPAPI_BACKEND_IDENTITY_SHA256
        ):
            raise _fail(WindowsBackendReason.CIPHER_REJECTED)
        object.__setattr__(self, "_root", canonical_root)
        object.__setattr__(self, "_root_binding", root_binding)
        object.__setattr__(self, "_authorization_verifier", authorization_verifier)
        object.__setattr__(self, "_currentness_verifier", currentness_verifier)
        object.__setattr__(
            self,
            "_currentness_reservation_verifier",
            currentness_reservation_verifier,
        )
        object.__setattr__(self, "_root_binding_verifier", root_binding_verifier)
        object.__setattr__(self, "_trusted_time_provider", trusted_time_provider)
        object.__setattr__(self, "_cipher", cipher)
        object.__setattr__(self, "_nonce", object())
        object.__setattr__(self, "_test_only", test_only)
        object.__setattr__(self, "_stage_hook", stage_hook)
        object.__setattr__(self, "_claim_lock", threading.RLock())
        object.__setattr__(
            self,
            "_io",
            SecureAuthorityIO(
                canonical_root,
                max_bytes=1024 * 1024,
                max_json_depth=16,
                max_json_nodes=10_000,
                _stage_hook=stage_hook,
            ),
        )

    def __repr__(self) -> str:
        return "<WindowsPrivateMediaCustodyBackend root=redacted>"

    def _stage(self, name: str) -> None:
        if self._stage_hook is not None:
            self._stage_hook(name)

    def _trusted_now(self) -> str:
        try:
            value = self._trusted_time_provider()
        except Exception:
            raise _fail(WindowsBackendReason.AUTHORIZATION_REJECTED) from None
        _timestamp(value, "trusted_now")
        return value

    def _validate_root(self, observed_at: str) -> str:
        self._root_binding.validate(observed_at=observed_at)
        if self._root_binding.root_path_binding_sha256 != _path_binding_sha256(self._root):
            raise _fail(WindowsBackendReason.ROOT_BINDING_MISMATCH)
        if (
            self._root_binding.cipher_backend_identity_sha256
            != self._cipher.backend_identity_sha256
        ):
            raise _fail(WindowsBackendReason.ROOT_BINDING_MISMATCH)
        try:
            observation = self._root_binding_verifier(
                self._root,
                self._root_binding,
                observed_at,
            )
        except Exception:
            raise _fail(WindowsBackendReason.ROOT_BINDING_MISMATCH) from None
        if type(observation) is not WindowsPrivateMediaRootObservation:
            raise _fail(WindowsBackendReason.ROOT_BINDING_MISMATCH)
        observation.validate(binding=self._root_binding, observed_at=observed_at)
        return observation.observation_sha256

    def _authorize(self, kind: LeaseKind, grant: object, authorization_sha256: str) -> None:
        digest = _grant_sha256(grant)
        try:
            accepted = self._authorization_verifier(kind, digest, authorization_sha256)
        except Exception:
            raise _fail(WindowsBackendReason.AUTHORIZATION_REJECTED) from None
        if accepted is not True:
            raise _fail(WindowsBackendReason.AUTHORIZATION_REJECTED)

    @staticmethod
    def _currentness_binding_sha256(
        kind: LeaseKind,
        grant: WindowsPrivateMediaWriteGrant | WindowsPrivateMediaReadGrant,
    ) -> str:
        if kind is LeaseKind.WRITE and type(grant) is WindowsPrivateMediaWriteGrant:
            projection = {
                "lease_kind": kind.value,
                "logical_slot_ref": grant.logical_slot_ref,
                "artifact_class": (
                    grant.artifact_class.value
                    if isinstance(grant.artifact_class, ArtifactClass)
                    else grant.artifact_class
                ),
                "generation_revision": grant.generation_revision,
                "current_event_head_sha256": grant.current_event_head_sha256,
                "expected_event_head_sha256": grant.expected_event_head_sha256,
                "producer_output_currentness_sha256": (
                    grant.producer_output_currentness_sha256
                ),
            }
        elif kind is LeaseKind.READ and type(grant) is WindowsPrivateMediaReadGrant:
            projection = {
                "lease_kind": kind.value,
                "logical_slot_ref": grant.receipt.logical_slot_ref,
                "artifact_class": grant.receipt.artifact_class.value,
                "generation_revision": grant.receipt.generation_revision,
                "receipt_sha256": grant.receipt.receipt_sha256,
                "event_head_sha256": grant.receipt.event_head_sha256,
                "currentness_sha256": grant.currentness.currentness_sha256,
            }
        else:
            raise _fail(WindowsBackendReason.REQUEST_INVALID)
        return sha256_bytes(_LIVE_CURRENTNESS_DOMAIN + canonical_json_bytes(projection))

    def _verify_live_authority(
        self,
        kind: LeaseKind,
        grant: WindowsPrivateMediaWriteGrant | WindowsPrivateMediaReadGrant,
    ) -> tuple[str, str, str]:
        now_value = self._trusted_now()
        issued = _timestamp(grant.issued_at, "issued_at")
        expires = _timestamp(grant.expires_at, "expires_at")
        now = _timestamp(now_value, "trusted_now")
        if not issued <= now < expires:
            raise _fail(WindowsBackendReason.AUTHORIZATION_REJECTED)
        if kind is LeaseKind.WRITE and type(grant) is WindowsPrivateMediaWriteGrant:
            fresh_until = _timestamp(grant.fresh_until, "fresh_until")
        elif kind is LeaseKind.READ and type(grant) is WindowsPrivateMediaReadGrant:
            fresh_until = _timestamp(grant.receipt.fresh_until, "receipt_fresh_until")
        else:
            raise _fail(WindowsBackendReason.REQUEST_INVALID)
        if now >= fresh_until:
            raise _fail(WindowsBackendReason.AUTHORIZATION_REJECTED)
        root_observation_sha256 = self._validate_root(now_value)
        self._authorize(kind, grant, grant.backend_authorization_sha256)
        currentness_sha256 = self._currentness_binding_sha256(kind, grant)
        try:
            current = self._currentness_verifier(
                kind,
                _grant_sha256(grant),
                currentness_sha256,
            )
        except Exception:
            raise _fail(WindowsBackendReason.AUTHORIZATION_REJECTED) from None
        if current is not True:
            raise _fail(WindowsBackendReason.AUTHORIZATION_REJECTED)
        return now_value, root_observation_sha256, currentness_sha256

    @staticmethod
    def _canonical_head_sha256(
        kind: LeaseKind,
        grant: WindowsPrivateMediaWriteGrant | WindowsPrivateMediaReadGrant,
    ) -> str | None:
        if kind is LeaseKind.WRITE and type(grant) is WindowsPrivateMediaWriteGrant:
            return grant.expected_event_head_sha256
        if kind is LeaseKind.READ and type(grant) is WindowsPrivateMediaReadGrant:
            return grant.receipt.event_head_sha256
        raise _fail(WindowsBackendReason.REQUEST_INVALID)

    def _reserve_currentness(
        self,
        kind: LeaseKind,
        grant: WindowsPrivateMediaWriteGrant | WindowsPrivateMediaReadGrant,
        *,
        acquired_at: str,
        currentness_binding_sha256: str,
    ) -> str:
        grant_sha256 = _grant_sha256(grant)
        canonical_head_sha256 = self._canonical_head_sha256(kind, grant)
        self._stage("before_currentness_cas_reservation")
        try:
            receipt = self._currentness_reservation_verifier(
                kind,
                grant.operation_id,
                grant_sha256,
                currentness_binding_sha256,
                canonical_head_sha256,
                acquired_at,
                grant.expires_at,
            )
        except Exception:
            raise _fail(WindowsBackendReason.AUTHORIZATION_REJECTED) from None
        if type(receipt) is not WindowsPrivateMediaCurrentnessReservationReceipt:
            raise _fail(WindowsBackendReason.AUTHORIZATION_REJECTED)
        receipt.validate(
            lease_kind=kind,
            operation_id=grant.operation_id,
            grant_sha256=grant_sha256,
            currentness_binding_sha256=currentness_binding_sha256,
            canonical_head_sha256=canonical_head_sha256,
            acquired_at=acquired_at,
            expires_at=grant.expires_at,
        )
        return receipt.reservation_sha256

    @staticmethod
    def _lease_names(kind: LeaseKind, operation_id: str) -> tuple[str, str, str]:
        _identifier(operation_id, "operation_id")
        key = sha256_bytes(
            _LEASE_OPERATION_DOMAIN
            + canonical_json_bytes(
                {"lease_kind": kind.value, "operation_id": operation_id}
            )
        )
        stem = f"t082-lease-{_digest_hex(key)}"
        return (
            f"{stem}.issued.json",
            f"{stem}.open.json",
            f"{stem}.completion.json",
        )

    @staticmethod
    def _write_recovery_name(operation_id: str) -> str:
        issue_name, _, _ = WindowsPrivateMediaCustodyBackend._lease_names(
            LeaseKind.WRITE,
            operation_id,
        )
        return issue_name.removesuffix(".issued.json") + ".write-result.json"

    @staticmethod
    def _body_binding_sha256(
        kind: LeaseKind,
        grant: WindowsPrivateMediaWriteGrant | WindowsPrivateMediaReadGrant,
    ) -> str:
        if kind is LeaseKind.WRITE and type(grant) is WindowsPrivateMediaWriteGrant:
            return _digest(grant.expected_content_sha256, "expected_content_sha256")
        if kind is LeaseKind.READ and type(grant) is WindowsPrivateMediaReadGrant:
            return _digest(grant.receipt.receipt_sha256, "receipt_sha256")
        raise _fail(WindowsBackendReason.REQUEST_INVALID)

    @staticmethod
    def _slot_reservation_name(grant: WindowsPrivateMediaWriteGrant) -> str:
        artifact_class = (
            grant.artifact_class.value
            if isinstance(grant.artifact_class, ArtifactClass)
            else grant.artifact_class
        )
        slot_key = sha256_bytes(
            _SLOT_RESERVATION_DOMAIN
            + canonical_json_bytes(
                {
                    "logical_slot_ref": grant.logical_slot_ref,
                    "artifact_class": artifact_class,
                }
            )
        )
        return (
            f"t082-slot-{_digest_hex(slot_key)}-"
            f"{grant.generation_revision:020d}.reservation.json"
        )

    def _publish_pinned_record(
        self,
        relative_name: str,
        document: Mapping[str, Any],
        *,
        writer: Any,
        on_published: Callable[[SecurePublishReceipt], None] | None = None,
    ) -> SecureJsonRead:
        published = self._io.publish_json_noreplace(
            relative_name,
            document,
            lease=writer,
        )
        if on_published is not None:
            on_published(published)
        self._stage("after_record_publish_before_readback")
        readback = self._io.read_json(relative_name)
        if (
            _thaw(readback.document) != dict(document)
            or not _same_pinned_observation(published, readback)
        ):
            raise _fail(WindowsBackendReason.PHYSICAL_IDENTITY_MISMATCH)
        return readback

    def _persist_issuance(
        self,
        kind: LeaseKind,
        grant: WindowsPrivateMediaWriteGrant | WindowsPrivateMediaReadGrant,
        admitted_at: str,
        root_observation_sha256: str,
    ) -> str:
        issue_name, _, _ = self._lease_names(kind, grant.operation_id)
        body = {
            "record_type": "Task082WindowsPrivateMediaLeaseIssuanceV1",
            "schema_version": 1,
            "canonical_owner_task": TASK_OWNER,
            "lease_kind": kind.value,
            "operation_id": grant.operation_id,
            "grant_sha256": _grant_sha256(grant),
            "root_binding_sha256": grant.root_binding_sha256,
            "root_observation_sha256": root_observation_sha256,
            "backend_authorization_sha256": grant.backend_authorization_sha256,
            "currentness_binding_sha256": self._currentness_binding_sha256(kind, grant),
            "body_binding_sha256": self._body_binding_sha256(kind, grant),
            "admitted_at": admitted_at,
            "state": ProductionLeaseState.ISSUED.value,
            "record_sha256": None,
        }
        body["record_sha256"] = _record_digest(
            _LEASE_OPERATION_DOMAIN,
            body,
            "record_sha256",
        )
        try:
            with self._writer_lock() as writer:
                try:
                    self._io.read_json(issue_name)
                except SecureAuthorityIOError as existing_error:
                    if existing_error.code != "NOT_FOUND":
                        raise
                else:
                    raise _fail(WindowsBackendReason.REPLAY)
                self._stage("before_durable_lease_issuance")
                readback = self._publish_pinned_record(issue_name, body, writer=writer)
                return _record_observation_sha256(
                    "LEASE_ISSUANCE",
                    issue_name,
                    readback,
                )
        except SecureAuthorityIOError as exc:
            if exc.code == "DESTINATION_EXISTS":
                raise _fail(WindowsBackendReason.REPLAY) from None
            raise _fail(
                WindowsBackendReason.COMPLETION_UNKNOWN,
                completion_unknown=exc.completion_unknown,
            ) from None

    def _persist_open_burn(
        self,
        kind: LeaseKind,
        grant: WindowsPrivateMediaWriteGrant | WindowsPrivateMediaReadGrant,
        *,
        issuance_record_sha256: str,
    ) -> tuple[str, int, str]:
        _, open_name, _ = self._lease_names(kind, grant.operation_id)
        currentness_reserved = False
        open_persisted = False

        def mark_open_persisted(_: SecurePublishReceipt) -> None:
            nonlocal open_persisted
            open_persisted = True

        try:
            with self._writer_lock() as writer:
                try:
                    self._io.read_json(open_name)
                except SecureAuthorityIOError as existing_error:
                    if existing_error.code != "NOT_FOUND":
                        raise
                else:
                    raise _fail(
                        WindowsBackendReason.REPLAY,
                        completion_unknown=True,
                    )
                opened_at, root_observation_sha256, currentness_sha256 = (
                    self._verify_live_authority(kind, grant)
                )
                currentness_reservation_sha256 = self._reserve_currentness(
                    kind,
                    grant,
                    acquired_at=opened_at,
                    currentness_binding_sha256=currentness_sha256,
                )
                currentness_reserved = True
                body = {
                    "record_type": "Task082WindowsPrivateMediaLeaseOpenV1",
                    "schema_version": 1,
                    "canonical_owner_task": TASK_OWNER,
                    "lease_kind": kind.value,
                    "operation_id": grant.operation_id,
                    "grant_sha256": _grant_sha256(grant),
                    "issuance_record_sha256": issuance_record_sha256,
                    "root_binding_sha256": grant.root_binding_sha256,
                    "root_observation_sha256": root_observation_sha256,
                    "currentness_binding_sha256": currentness_sha256,
                    "currentness_reservation_sha256": (
                        currentness_reservation_sha256
                    ),
                    "body_binding_sha256": self._body_binding_sha256(kind, grant),
                    "opened_at": opened_at,
                    "state": ProductionLeaseState.OPEN_STARTED.value,
                    "record_sha256": None,
                }
                body["record_sha256"] = _record_digest(
                    _LEASE_OPEN_DOMAIN,
                    body,
                    "record_sha256",
                )
                self._stage("before_durable_lease_open")
                open_readback = self._publish_pinned_record(
                    open_name,
                    body,
                    writer=writer,
                    on_published=mark_open_persisted,
                )
                open_identity_sha256 = _record_observation_sha256(
                    "LEASE_OPEN",
                    open_name,
                    open_readback,
                )
                effect_count = 3
                if kind is LeaseKind.WRITE:
                    if type(grant) is not WindowsPrivateMediaWriteGrant:
                        raise _fail(WindowsBackendReason.REQUEST_INVALID)
                    artifact_class = (
                        grant.artifact_class.value
                        if isinstance(grant.artifact_class, ArtifactClass)
                        else grant.artifact_class
                    )
                    reservation = {
                        "record_type": "Task082WindowsPrivateMediaSlotReservationV1",
                        "schema_version": 1,
                        "canonical_owner_task": TASK_OWNER,
                        "logical_slot_ref": grant.logical_slot_ref,
                        "artifact_class": artifact_class,
                        "generation_revision": grant.generation_revision,
                        "operation_id": grant.operation_id,
                        "grant_sha256": _grant_sha256(grant),
                        "predecessor_event_sha256": grant.predecessor_event_sha256,
                        "predecessor_receipt_sha256": grant.predecessor_receipt_sha256,
                        "currentness_binding_sha256": currentness_sha256,
                        "currentness_reservation_sha256": (
                            currentness_reservation_sha256
                        ),
                        "root_observation_sha256": root_observation_sha256,
                        "burn_record_sha256": open_identity_sha256,
                        "reserved_at": opened_at,
                        "record_sha256": None,
                    }
                    reservation["record_sha256"] = _record_digest(
                        _SLOT_RESERVATION_DOMAIN,
                        reservation,
                        "record_sha256",
                    )
                    self._stage("before_slot_generation_reservation")
                    reservation_name = self._slot_reservation_name(grant)
                    try:
                        self._io.read_json(reservation_name)
                    except SecureAuthorityIOError as existing_error:
                        if existing_error.code != "NOT_FOUND":
                            raise
                    else:
                        raise _fail(
                            WindowsBackendReason.COMPLETION_UNKNOWN,
                            completion_unknown=True,
                        )
                    self._publish_pinned_record(
                        reservation_name,
                        reservation,
                        writer=writer,
                    )
                    effect_count += 2
                return (
                    open_identity_sha256,
                    effect_count,
                    currentness_reservation_sha256,
                )
        except WindowsPrivateMediaBackendError:
            if currentness_reserved or open_persisted:
                raise _fail(
                    WindowsBackendReason.COMPLETION_UNKNOWN,
                    completion_unknown=True,
                ) from None
            raise
        except SecureAuthorityIOError as exc:
            if not currentness_reserved and not open_persisted and exc.code == "DESTINATION_EXISTS":
                raise _fail(
                    WindowsBackendReason.REPLAY,
                    completion_unknown=True,
                ) from None
            raise _fail(
                WindowsBackendReason.COMPLETION_UNKNOWN,
                completion_unknown=(
                    currentness_reserved or open_persisted or exc.completion_unknown
                ),
            ) from None
        except Exception:
            if currentness_reserved or open_persisted:
                raise _fail(
                    WindowsBackendReason.COMPLETION_UNKNOWN,
                    completion_unknown=True,
                ) from None
            raise _fail(WindowsBackendReason.AUTHORIZATION_REJECTED) from None

    def _begin_open(
        self,
        lease: _ProductionLease,
        kind: LeaseKind,
        grant: WindowsPrivateMediaWriteGrant | WindowsPrivateMediaReadGrant,
    ) -> int:
        with self._claim_lock:
            if lease.state is not ProductionLeaseState.ISSUED:
                raise _fail(WindowsBackendReason.REPLAY)
            try:
                (
                    burn_sha256,
                    effect_count,
                    currentness_reservation_sha256,
                ) = self._persist_open_burn(
                    kind,
                    grant,
                    issuance_record_sha256=lease._issuance_record_sha256,
                )
            except WindowsPrivateMediaBackendError as exc:
                lease._transition(
                    self._nonce,
                    (
                        ProductionLeaseState.COMPLETION_UNKNOWN
                        if exc.completion_unknown
                        or exc.reason is WindowsBackendReason.COMPLETION_UNKNOWN
                        or exc.reason is WindowsBackendReason.REPLAY
                        else ProductionLeaseState.FAILED_CLOSED
                    ),
                )
                raise
            lease._transition(
                self._nonce,
                ProductionLeaseState.OPEN_STARTED,
                burn_record_sha256=burn_sha256,
                currentness_reservation_sha256=currentness_reservation_sha256,
            )
            return effect_count

    def _persist_completion(
        self,
        lease: _ProductionLease,
        grant: WindowsPrivateMediaWriteGrant | WindowsPrivateMediaReadGrant,
        *,
        receipt_sha256: str,
        completion_kind: str,
        completion_binding_sha256: str,
        callback_completed: bool,
        write_recovery_record_sha256: str | None,
    ) -> str:
        _, _, completion_name = self._lease_names(lease._kind, grant.operation_id)
        _digest(
            lease._currentness_reservation_sha256,
            "currentness_reservation_sha256",
        )
        if lease._kind is LeaseKind.WRITE:
            _digest(write_recovery_record_sha256, "write_recovery_record_sha256")
        elif write_recovery_record_sha256 is not None:
            raise _fail(WindowsBackendReason.REQUEST_INVALID)
        completed_at = self._trusted_now()
        body = {
            "record_type": "Task082WindowsPrivateMediaLeaseCompletionV1",
            "schema_version": 1,
            "canonical_owner_task": TASK_OWNER,
            "lease_kind": lease._kind.value,
            "operation_id": grant.operation_id,
            "grant_sha256": _grant_sha256(grant),
            "issuance_record_sha256": lease._issuance_record_sha256,
            "burn_record_sha256": lease._burn_record_sha256,
            "currentness_reservation_sha256": (
                lease._currentness_reservation_sha256
            ),
            "write_recovery_record_sha256": write_recovery_record_sha256,
            "receipt_sha256": receipt_sha256,
            "completion_kind": completion_kind,
            "completion_binding_sha256": completion_binding_sha256,
            "body_zeroization_confirmed": True,
            "callback_completed": callback_completed,
            "completed_at": completed_at,
            "state": ProductionLeaseState.CONSUMED.value,
            "record_sha256": None,
        }
        body["record_sha256"] = _record_digest(
            _LEASE_COMPLETION_DOMAIN,
            body,
            "record_sha256",
        )
        try:
            with self._writer_lock() as writer:
                self._stage("before_durable_lease_completion")
                readback = self._publish_pinned_record(
                    completion_name,
                    body,
                    writer=writer,
                )
                return _record_observation_sha256(
                    "LEASE_COMPLETION",
                    completion_name,
                    readback,
                )
        except SecureAuthorityIOError as exc:
            raise _fail(
                WindowsBackendReason.COMPLETION_UNKNOWN,
                completion_unknown=True,
            ) from None

    def _persist_write_recovery(
        self,
        grant: WindowsPrivateMediaWriteGrant,
        result: WindowsPrivateMediaWriteResult,
    ) -> str:
        relative_name = self._write_recovery_name(grant.operation_id)
        result_value = result.as_dict()
        body = {
            "record_type": "Task082WindowsPrivateMediaWriteRecoveryV1",
            "schema_version": 1,
            "canonical_owner_task": TASK_OWNER,
            "operation_id": grant.operation_id,
            "grant_sha256": _grant_sha256(grant),
            "receipt": result_value["receipt"],
            "generation_event": result_value["generation_event"],
            "write_publish_pinned_readback_sha256": (
                result.write_publish_pinned_readback_sha256
            ),
            "plaintext_byte_count": result.plaintext_byte_count,
            "chunk_count": result.chunk_count,
            "body_zeroization_confirmed": result.body_zeroization_confirmed,
            "production_backend_invoked": result.production_backend_invoked,
            "private_media_effect_count": result.private_media_effect_count,
            "result_sha256": result.result_sha256,
            "record_sha256": None,
        }
        body["record_sha256"] = _record_digest(
            _WRITE_RECOVERY_DOMAIN,
            body,
            "record_sha256",
        )
        try:
            with self._writer_lock() as writer:
                self._stage("before_durable_write_recovery")
                readback = self._publish_pinned_record(
                    relative_name,
                    body,
                    writer=writer,
                )
                return _record_observation_sha256(
                    "WRITE_RECOVERY",
                    relative_name,
                    readback,
                )
        except SecureAuthorityIOError:
            raise _fail(
                WindowsBackendReason.COMPLETION_UNKNOWN,
                completion_unknown=True,
            ) from None

    def issue_write_lease(
        self,
        grant: WindowsPrivateMediaWriteGrant,
    ) -> Task082PrivateMediaWriteLeaseV1:
        if type(grant) is not WindowsPrivateMediaWriteGrant:
            raise _fail(WindowsBackendReason.REQUEST_INVALID)
        self._validate_root(grant.observed_at)
        if grant.root_binding_sha256 != self._root_binding.binding_sha256:
            raise _fail(WindowsBackendReason.ROOT_BINDING_MISMATCH)
        for field in (
            "expected_content_sha256",
            "media_metadata_sha256",
            "trusted_time_binding_sha256",
            "backend_authorization_sha256",
        ):
            _digest(getattr(grant, field), field)
        if type(grant.event_revision) is not int or grant.event_revision < 1:
            raise _fail(WindowsBackendReason.REQUEST_INVALID)
        _nullable_digest(grant.predecessor_event_sha256, "predecessor_event_sha256")
        _nullable_digest(grant.predecessor_receipt_sha256, "predecessor_receipt_sha256")
        created = _timestamp(grant.created_at, "created_at")
        observed = _timestamp(grant.observed_at, "observed_at")
        fresh = _timestamp(grant.fresh_until, "fresh_until")
        if not created <= observed < fresh:
            raise _fail(WindowsBackendReason.ADMISSION_REJECTED)
        if (grant.event_revision == 1) != (grant.predecessor_event_sha256 is None):
            raise _fail(WindowsBackendReason.ADMISSION_REJECTED)
        if grant.predecessor_event_sha256 != grant.current_event_head_sha256:
            raise _fail(WindowsBackendReason.ADMISSION_REJECTED)
        if (grant.generation_revision == 1) != (grant.predecessor_receipt_sha256 is None):
            raise _fail(WindowsBackendReason.ADMISSION_REJECTED)
        try:
            decision = compile_fixture_write_lease_admission(
                purpose=(
                    grant.purpose.value
                    if isinstance(grant.purpose, WritePurpose)
                    else grant.purpose
                ),
                expected_purpose=grant.expected_purpose,
                producer_task=grant.producer_task,
                producer_output_role=grant.producer_output_role,
                artifact_class=grant.artifact_class,
                operation_id=grant.operation_id,
                expected_operation_id=grant.expected_operation_id,
                logical_slot_ref=grant.logical_slot_ref,
                generation_revision=grant.generation_revision,
                expected_generation_revision=grant.expected_generation_revision,
                owner_subject_revision_sha256=grant.owner_subject_revision_sha256,
                expected_owner_subject_revision_sha256=grant.expected_owner_subject_revision_sha256,
                consent_scope=grant.consent_scope,
                consent_rights_revision_sha256=grant.consent_rights_revision_sha256,
                expected_consent_rights_revision_sha256=(
                    grant.expected_consent_rights_revision_sha256
                ),
                current_event_head_sha256=grant.current_event_head_sha256,
                expected_event_head_sha256=grant.expected_event_head_sha256,
                producer_output_record_type=grant.producer_output_record_type,
                expected_producer_output_record_type=grant.expected_producer_output_record_type,
                producer_output_receipt_sha256=grant.producer_output_receipt_sha256,
                expected_producer_output_receipt_sha256=(
                    grant.expected_producer_output_receipt_sha256
                ),
                producer_output_currentness_sha256=grant.producer_output_currentness_sha256,
                expected_producer_output_currentness_sha256=(
                    grant.expected_producer_output_currentness_sha256
                ),
                producer_output_current=grant.producer_output_current,
                issued_at=grant.issued_at,
                expires_at=grant.expires_at,
                observed_at=grant.observed_at,
                revoked=grant.revoked,
                receipt_as_capability=grant.receipt_as_capability,
            )
        except (Task082ContractError, TypeError, ValueError):
            raise _fail(WindowsBackendReason.ADMISSION_REJECTED) from None
        decision_value = decision.as_dict()
        if (
            decision.reason_code is not Task082Reason.READY
            or decision.decision is not LeaseDecisionKind.READY_FIXTURE_ONLY
            or decision_value["authority_created"] is not False
            or decision_value["body_access_granted"] is not False
            or decision_value["fixture_only"] is not True
            or decision_value["production_backend_invoked"] is not False
            or decision_value["private_media_effect_count"] != 0
        ):
            raise _fail(WindowsBackendReason.ADMISSION_REJECTED)
        admitted_at, root_observation_sha256, _ = self._verify_live_authority(
            LeaseKind.WRITE,
            grant,
        )
        with self._claim_lock:
            issuance_record_sha256 = self._persist_issuance(
                LeaseKind.WRITE,
                grant,
                admitted_at,
                root_observation_sha256,
            )
        return Task082PrivateMediaWriteLeaseV1(
            _LEASE_TOKEN,
            backend_nonce=self._nonce,
            grant=grant,
            kind=LeaseKind.WRITE,
            issuance_record_sha256=issuance_record_sha256,
        )

    def issue_read_lease(
        self,
        grant: WindowsPrivateMediaReadGrant,
    ) -> Task082PrivateMediaReadLeaseV1:
        if type(grant) is not WindowsPrivateMediaReadGrant:
            raise _fail(WindowsBackendReason.REQUEST_INVALID)
        self._validate_root(grant.observed_at)
        if grant.root_binding_sha256 != self._root_binding.binding_sha256:
            raise _fail(WindowsBackendReason.ROOT_BINDING_MISMATCH)
        _digest(grant.backend_authorization_sha256, "backend_authorization_sha256")
        if (
            type(grant.receipt) is not PrivateMediaCustodyReceipt
            or type(grant.currentness) is not GenerationCurrentness
            or grant.receipt.cipher_backend_identity_sha256
            != self._cipher.backend_identity_sha256
        ):
            raise _fail(WindowsBackendReason.ADMISSION_REJECTED)
        try:
            decision = compile_fixture_read_lease_admission(
                receipt=grant.receipt,
                currentness=grant.currentness,
                purpose=(
                    grant.purpose.value
                    if isinstance(grant.purpose, ReadPurpose)
                    else grant.purpose
                ),
                expected_purpose=grant.expected_purpose,
                consumer_task=grant.consumer_task,
                operation_id=grant.operation_id,
                expected_operation_id=grant.expected_operation_id,
                expected_owner_subject_revision_sha256=grant.expected_owner_subject_revision_sha256,
                expected_consent_rights_revision_sha256=(
                    grant.expected_consent_rights_revision_sha256
                ),
                issued_at=grant.issued_at,
                expires_at=grant.expires_at,
                observed_at=grant.observed_at,
                asset_adoption_readback_sha256=grant.asset_adoption_readback_sha256,
                expected_asset_adoption_readback_sha256=(
                    grant.expected_asset_adoption_readback_sha256
                ),
                producer_output_receipt_sha256=grant.producer_output_receipt_sha256,
                expected_producer_output_receipt_sha256=(
                    grant.expected_producer_output_receipt_sha256
                ),
                dataset_review_binding_sha256=grant.dataset_review_binding_sha256,
                expected_dataset_review_binding_sha256=grant.expected_dataset_review_binding_sha256,
                dataset_snapshot_sha256=grant.dataset_snapshot_sha256,
                expected_dataset_snapshot_sha256=grant.expected_dataset_snapshot_sha256,
                durable_job_head_sha256=grant.durable_job_head_sha256,
                expected_durable_job_head_sha256=grant.expected_durable_job_head_sha256,
                run_recipe_binding_sha256=grant.run_recipe_binding_sha256,
                expected_run_recipe_binding_sha256=grant.expected_run_recipe_binding_sha256,
                h3_authorization_sha256=grant.h3_authorization_sha256,
                expected_h3_authorization_sha256=grant.expected_h3_authorization_sha256,
                training_compound_operation_sha256=grant.training_compound_operation_sha256,
                expected_training_compound_operation_sha256=(
                    grant.expected_training_compound_operation_sha256
                ),
                revoked=grant.revoked,
                receipt_as_capability=grant.receipt_as_capability,
            )
        except (Task082ContractError, TypeError, ValueError):
            raise _fail(WindowsBackendReason.ADMISSION_REJECTED) from None
        decision_value = decision.as_dict()
        if (
            decision.reason_code is not Task082Reason.READY
            or decision.decision is not LeaseDecisionKind.READY_FIXTURE_ONLY
            or decision_value["authority_created"] is not False
            or decision_value["body_access_granted"] is not False
            or decision_value["fixture_only"] is not True
            or decision_value["production_backend_invoked"] is not False
            or decision_value["private_media_effect_count"] != 0
        ):
            raise _fail(WindowsBackendReason.ADMISSION_REJECTED)
        admitted_at, root_observation_sha256, _ = self._verify_live_authority(
            LeaseKind.READ,
            grant,
        )
        with self._claim_lock:
            issuance_record_sha256 = self._persist_issuance(
                LeaseKind.READ,
                grant,
                admitted_at,
                root_observation_sha256,
            )
        return Task082PrivateMediaReadLeaseV1(
            _LEASE_TOKEN,
            backend_nonce=self._nonce,
            grant=grant,
            kind=LeaseKind.READ,
            issuance_record_sha256=issuance_record_sha256,
        )

    def _require_lease(
        self,
        lease: object,
        expected_type: type[_ProductionLease],
    ) -> _ProductionLease:
        if (
            type(lease) is not expected_type
            or lease._backend_nonce is not self._nonce  # type: ignore[attr-defined]
        ):
            if type(lease) is Task082FixtureLeaseSentinel:
                raise _fail(WindowsBackendReason.RECEIPT_AS_CAPABILITY)
            raise _fail(WindowsBackendReason.RECEIPT_AS_CAPABILITY)
        if lease.state is not ProductionLeaseState.ISSUED:  # type: ignore[attr-defined]
            raise _fail(WindowsBackendReason.REPLAY)
        return lease  # type: ignore[return-value]

    @contextmanager
    def _writer_lock(self) -> Iterator[Any]:
        try:
            with self._io.lock(_LOCK_NAME, mode="existing") as lock:
                yield lock
                return
        except SecureAuthorityIOError as first:
            if first.code != "LOCK_NOT_FOUND":
                raise
        try:
            with self._io.lock(_LOCK_NAME, mode="initial") as lock:
                yield lock
                return
        except SecureAuthorityIOError as second:
            if second.code != "LOCK_CREATE_COLLISION":
                raise
        with self._io.lock(_LOCK_NAME, mode="existing") as lock:
            yield lock

    @staticmethod
    def _artifact_coordinates(grant: WindowsPrivateMediaWriteGrant) -> tuple[str, str]:
        projection = {
            "operation_id": grant.operation_id,
            "logical_slot_ref": grant.logical_slot_ref,
            "artifact_class": (
                grant.artifact_class.value
                if isinstance(grant.artifact_class, ArtifactClass)
                else grant.artifact_class
            ),
            "generation_revision": grant.generation_revision,
            "owner_subject_revision_sha256": grant.owner_subject_revision_sha256,
            "consent_rights_revision_sha256": grant.consent_rights_revision_sha256,
            "root_binding_sha256": grant.root_binding_sha256,
            "backend_authorization_sha256": grant.backend_authorization_sha256,
        }
        key = sha256_bytes(_ARTIFACT_DOMAIN + canonical_json_bytes(projection))
        return key, f"T082-{_digest_hex(key)}"

    @staticmethod
    def _chunk_name(key: str, index: int) -> str:
        return f"t082-{_digest_hex(key)}-{index:08d}.chunk.json"

    @staticmethod
    def _manifest_name_from_id(opaque_artifact_id: str) -> str:
        _identifier(opaque_artifact_id, "opaque_artifact_id")
        if not opaque_artifact_id.startswith("T082-") or len(opaque_artifact_id) != 69:
            raise _fail(WindowsBackendReason.MANIFEST_INVALID)
        key = "sha256:" + opaque_artifact_id[5:]
        _digest(key, "artifact_key_sha256")
        return f"t082-{_digest_hex(key)}.manifest.json"

    @staticmethod
    def _chunk_entropy(
        *,
        artifact_key_sha256: str,
        chunk_index: int,
        chunk_count: int,
        plaintext_chunk_sha256: str,
        media_metadata_sha256: str,
        root_binding_sha256: str,
        backend_authorization_sha256: str,
    ) -> tuple[str, bytes]:
        projection = {
            "artifact_key_sha256": artifact_key_sha256,
            "chunk_index": chunk_index,
            "chunk_count": chunk_count,
            "plaintext_chunk_sha256": plaintext_chunk_sha256,
            "media_metadata_sha256": media_metadata_sha256,
            "root_binding_sha256": root_binding_sha256,
            "backend_authorization_sha256": backend_authorization_sha256,
        }
        digest = sha256_bytes(_CHUNK_ENTROPY_DOMAIN + canonical_json_bytes(projection))
        return digest, _digest_bytes(digest)

    def publish_private_media(
        self,
        lease: Task082PrivateMediaWriteLeaseV1,
        private_body: bytearray,
    ) -> WindowsPrivateMediaWriteResult:
        with self._claim_lock:
            return self._publish_private_media_locked(lease, private_body)

    def _publish_private_media_locked(
        self,
        lease: Task082PrivateMediaWriteLeaseV1,
        private_body: bytearray,
    ) -> WindowsPrivateMediaWriteResult:
        lease_value = self._require_lease(lease, Task082PrivateMediaWriteLeaseV1)
        grant = lease_value._grant
        if type(grant) is not WindowsPrivateMediaWriteGrant:
            raise _fail(WindowsBackendReason.RECEIPT_AS_CAPABILITY)
        if type(private_body) is not bytearray or not private_body:
            lease_value._transition(self._nonce, ProductionLeaseState.FAILED_CLOSED)
            raise _fail(WindowsBackendReason.BODY_INVALID)
        if len(private_body) > MAX_PRIVATE_MEDIA_BYTES:
            _zeroize(private_body)
            lease_value._transition(self._nonce, ProductionLeaseState.FAILED_CLOSED)
            raise _fail(WindowsBackendReason.BODY_INVALID)
        started = False
        zeroized = False
        effect_count = 2
        try:
            effect_count += self._begin_open(lease_value, LeaseKind.WRITE, grant)
            started = True
            content_sha256 = _sha256_buffer(private_body)
            if content_sha256 != grant.expected_content_sha256:
                raise _fail(WindowsBackendReason.BODY_DIGEST_MISMATCH)
            chunk_count = (len(private_body) + CHUNK_PLAINTEXT_BYTES - 1) // CHUNK_PLAINTEXT_BYTES
            if not 1 <= chunk_count <= MAX_CHUNKS:
                lease_value._transition(self._nonce, ProductionLeaseState.FAILED_CLOSED)
                raise _fail(WindowsBackendReason.BODY_INVALID)
            artifact_key, opaque_artifact_id = self._artifact_coordinates(grant)
            descriptors: list[dict[str, Any]] = []
            chunk_receipts: list[tuple[str, SecurePublishReceipt]] = []
            with self._writer_lock() as writer:
                for index in range(chunk_count):
                    start = index * CHUNK_PLAINTEXT_BYTES
                    chunk = private_body[start : start + CHUNK_PLAINTEXT_BYTES]
                    try:
                        plaintext_chunk_sha256 = _sha256_buffer(chunk)
                        entropy_sha256, entropy = self._chunk_entropy(
                            artifact_key_sha256=artifact_key,
                            chunk_index=index,
                            chunk_count=chunk_count,
                            plaintext_chunk_sha256=plaintext_chunk_sha256,
                            media_metadata_sha256=grant.media_metadata_sha256,
                            root_binding_sha256=grant.root_binding_sha256,
                            backend_authorization_sha256=grant.backend_authorization_sha256,
                        )
                        ciphertext = self._cipher.seal(chunk, entropy=entropy)
                    except WindowsPrivateMediaBackendError:
                        raise
                    except Exception:
                        raise _fail(WindowsBackendReason.CIPHER_REJECTED) from None
                    finally:
                        if not _zeroize(chunk):
                            raise _fail(WindowsBackendReason.ZEROIZATION_NOT_CONFIRMED)
                    if type(ciphertext) is not bytes or not ciphertext:
                        raise _fail(WindowsBackendReason.CIPHER_REJECTED)
                    ciphertext_sha256 = _sha256_buffer(ciphertext)
                    chunk_name = self._chunk_name(artifact_key, index)
                    envelope = {
                        "record_type": "Task082WindowsPrivateMediaChunkV1",
                        "schema_version": 1,
                        "canonical_owner_task": TASK_OWNER,
                        "cipher_suite": self._cipher.cipher_suite,
                        "cipher_backend_identity_sha256": self._cipher.backend_identity_sha256,
                        "artifact_key_sha256": artifact_key,
                        "chunk_index": index,
                        "chunk_count": chunk_count,
                        "plaintext_byte_count": min(
                            CHUNK_PLAINTEXT_BYTES,
                            len(private_body) - start,
                        ),
                        "plaintext_chunk_sha256": plaintext_chunk_sha256,
                        "entropy_sha256": entropy_sha256,
                        "ciphertext_sha256": ciphertext_sha256,
                        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
                    }
                    self._stage(f"before_chunk_publish_{index}")
                    published = self._io.publish_json_noreplace(
                        chunk_name,
                        envelope,
                        lease=writer,
                    )
                    effect_count += 1
                    self._stage(f"after_chunk_publish_before_readback_{index}")
                    readback = self._io.read_json(chunk_name)
                    effect_count += 1
                    if (
                        _thaw(readback.document) != envelope
                        or not _same_pinned_observation(published, readback)
                    ):
                        raise _fail(WindowsBackendReason.PHYSICAL_IDENTITY_MISMATCH)
                    identity_sha256 = _identity_sha256(
                        _identity_projection(f"CHUNK_{index}", chunk_name, published)
                    )
                    descriptors.append(
                        {
                            "relative_name": chunk_name,
                            "chunk_index": index,
                            "plaintext_byte_count": envelope["plaintext_byte_count"],
                            "plaintext_chunk_sha256": plaintext_chunk_sha256,
                            "entropy_sha256": entropy_sha256,
                            "ciphertext_sha256": ciphertext_sha256,
                            "publish_identity_sha256": identity_sha256,
                        }
                    )
                    chunk_receipts.append((chunk_name, published))
                manifest = {
                    "record_type": "Task082WindowsPrivateMediaManifestV1",
                    "schema_version": 1,
                    "canonical_owner_task": TASK_OWNER,
                    "backend_id": WINDOWS_BACKEND_ID,
                    "cipher_suite": self._cipher.cipher_suite,
                    "cipher_backend_identity_sha256": self._cipher.backend_identity_sha256,
                    "root_binding_sha256": grant.root_binding_sha256,
                    "backend_authorization_sha256": grant.backend_authorization_sha256,
                    "artifact_key_sha256": artifact_key,
                    "opaque_artifact_id": opaque_artifact_id,
                    "logical_slot_ref": grant.logical_slot_ref,
                    "artifact_class": (
                        grant.artifact_class.value
                        if isinstance(grant.artifact_class, ArtifactClass)
                        else grant.artifact_class
                    ),
                    "generation_revision": grant.generation_revision,
                    "content_sha256": content_sha256,
                    "media_metadata_sha256": grant.media_metadata_sha256,
                    "plaintext_byte_count": len(private_body),
                    "chunk_count": chunk_count,
                    "chunks": descriptors,
                    "manifest_sha256": None,
                }
                manifest["manifest_sha256"] = _record_digest(
                    _MANIFEST_DOMAIN,
                    manifest,
                    "manifest_sha256",
                )
                manifest_name = f"t082-{_digest_hex(artifact_key)}.manifest.json"
                self._stage("before_manifest_publish")
                manifest_receipt = self._io.publish_json_noreplace(
                    manifest_name,
                    manifest,
                    lease=writer,
                )
                effect_count += 1
                self._stage("after_manifest_publish_before_readback")
                manifest_readback = self._io.read_json(manifest_name)
                effect_count += 1
                if (
                    _thaw(manifest_readback.document) != manifest
                    or not _same_pinned_observation(
                        manifest_receipt,
                        manifest_readback,
                    )
                ):
                    raise _fail(WindowsBackendReason.PHYSICAL_IDENTITY_MISMATCH)
            opened_physical_identity_sha256 = _aggregate_physical_identity_sha256(
                manifest_name,
                manifest_receipt,
                chunk_receipts,
            )
            custody_binding_sha256 = custody_staged_binding_sha256(
                opaque_artifact_id=opaque_artifact_id,
                logical_slot_ref=grant.logical_slot_ref,
                generation_revision=grant.generation_revision,
                owner_subject_revision_sha256=grant.owner_subject_revision_sha256,
                purpose=(
                    grant.purpose.value
                    if isinstance(grant.purpose, WritePurpose)
                    else grant.purpose
                ),
                artifact_class=(
                    grant.artifact_class.value
                    if isinstance(grant.artifact_class, ArtifactClass)
                    else grant.artifact_class
                ),
                content_sha256=content_sha256,
                media_metadata_sha256=grant.media_metadata_sha256,
                opened_physical_identity_sha256=opened_physical_identity_sha256,
                cipher_backend_identity_sha256=self._cipher.backend_identity_sha256,
                consent_rights_revision_sha256=grant.consent_rights_revision_sha256,
                observed_at=grant.observed_at,
                fresh_until=grant.fresh_until,
            )
            event = PrivateMediaGenerationEvent.create(
                event_kind=GenerationEventKind.GENERATION_PUBLISHED,
                logical_slot_ref=grant.logical_slot_ref,
                artifact_class=grant.artifact_class,
                event_revision=grant.event_revision,
                predecessor_event_sha256=grant.predecessor_event_sha256,
                owner_subject_revision_sha256=grant.owner_subject_revision_sha256,
                purpose=(
                    grant.purpose.value
                    if isinstance(grant.purpose, WritePurpose)
                    else grant.purpose
                ),
                consent_rights_revision_sha256=grant.consent_rights_revision_sha256,
                created_at=grant.created_at,
                observed_at=grant.observed_at,
                fresh_until=grant.fresh_until,
                trusted_time_binding_sha256=grant.trusted_time_binding_sha256,
                published_generation_revision=grant.generation_revision,
                opaque_artifact_id=opaque_artifact_id,
                custody_binding_sha256=custody_binding_sha256,
                content_sha256=content_sha256,
                media_metadata_sha256=grant.media_metadata_sha256,
                opened_physical_identity_sha256=opened_physical_identity_sha256,
                cipher_backend_identity_sha256=self._cipher.backend_identity_sha256,
                target_generation_revision=None,
                target_publish_event_sha256=None,
                tombstone_decision_sha256=None,
            )
            receipt = PrivateMediaCustodyReceipt.create(
                opaque_artifact_id=opaque_artifact_id,
                logical_slot_ref=grant.logical_slot_ref,
                generation_revision=grant.generation_revision,
                predecessor_receipt_sha256=grant.predecessor_receipt_sha256,
                custody_binding_sha256=custody_binding_sha256,
                owner_subject_revision_sha256=grant.owner_subject_revision_sha256,
                purpose=(
                    grant.purpose.value
                    if isinstance(grant.purpose, WritePurpose)
                    else grant.purpose
                ),
                artifact_class=grant.artifact_class,
                content_sha256=content_sha256,
                media_metadata_sha256=grant.media_metadata_sha256,
                opened_physical_identity_sha256=opened_physical_identity_sha256,
                cipher_backend_identity_sha256=self._cipher.backend_identity_sha256,
                consent_rights_revision_sha256=grant.consent_rights_revision_sha256,
                generation_event_sha256=event.event_sha256,
                event_head_sha256=event.event_sha256,
                observed_at=grant.observed_at,
                fresh_until=grant.fresh_until,
            )
            pinned_readback_sha256 = sha256_bytes(
                canonical_json_bytes(
                    {
                        "manifest_sha256": manifest["manifest_sha256"],
                        "opened_physical_identity_sha256": opened_physical_identity_sha256,
                        "generation_event_sha256": event.event_sha256,
                        "receipt_sha256": receipt.receipt_sha256,
                    }
                )
            )
            zeroized = _zeroize(private_body)
            if not zeroized:
                raise _fail(WindowsBackendReason.ZEROIZATION_NOT_CONFIRMED)
            effect_count += 4
            body = {
                "receipt": receipt.as_dict(),
                "generation_event": event.as_dict(),
                "write_publish_pinned_readback_sha256": pinned_readback_sha256,
                "plaintext_byte_count": manifest["plaintext_byte_count"],
                "chunk_count": chunk_count,
                "body_zeroization_confirmed": True,
                "production_backend_invoked": not self._test_only,
                "private_media_effect_count": effect_count,
                "result_sha256": None,
            }
            body["result_sha256"] = _record_digest(
                _WRITE_RESULT_DOMAIN,
                body,
                "result_sha256",
            )
            result = WindowsPrivateMediaWriteResult(
                receipt=receipt,
                generation_event=event,
                write_publish_pinned_readback_sha256=pinned_readback_sha256,
                plaintext_byte_count=manifest["plaintext_byte_count"],
                chunk_count=chunk_count,
                body_zeroization_confirmed=True,
                production_backend_invoked=not self._test_only,
                private_media_effect_count=effect_count,
                result_sha256=body["result_sha256"],
            )
            write_recovery_record_sha256 = self._persist_write_recovery(
                grant,
                result,
            )
            completion_record_sha256 = self._persist_completion(
                lease_value,
                grant,
                receipt_sha256=receipt.receipt_sha256,
                completion_kind="WRITE_PUBLISH_PINNED_READBACK",
                completion_binding_sha256=pinned_readback_sha256,
                callback_completed=False,
                write_recovery_record_sha256=write_recovery_record_sha256,
            )
            lease_value._transition(
                self._nonce,
                ProductionLeaseState.CONSUMED,
                completion_record_sha256=completion_record_sha256,
                write_recovery_record_sha256=write_recovery_record_sha256,
            )
            return result
        except WindowsPrivateMediaBackendError:
            if started and lease_value.state is ProductionLeaseState.OPEN_STARTED:
                lease_value._transition(self._nonce, ProductionLeaseState.COMPLETION_UNKNOWN)
                raise _fail(
                    WindowsBackendReason.COMPLETION_UNKNOWN,
                    completion_unknown=True,
                ) from None
            raise
        except (
            SecureAuthorityIOError,
            Task082ContractError,
            OSError,
            ValueError,
            TypeError,
        ):
            if started:
                if lease_value.state is ProductionLeaseState.OPEN_STARTED:
                    lease_value._transition(
                        self._nonce,
                        ProductionLeaseState.COMPLETION_UNKNOWN,
                    )
                raise _fail(
                    WindowsBackendReason.COMPLETION_UNKNOWN,
                    completion_unknown=True,
                ) from None
            lease_value._transition(self._nonce, ProductionLeaseState.FAILED_CLOSED)
            raise _fail(WindowsBackendReason.PUBLISH_FAILED) from None
        except Exception:
            if started:
                if lease_value.state is ProductionLeaseState.OPEN_STARTED:
                    lease_value._transition(
                        self._nonce,
                        ProductionLeaseState.COMPLETION_UNKNOWN,
                    )
                raise _fail(
                    WindowsBackendReason.COMPLETION_UNKNOWN,
                    completion_unknown=True,
                ) from None
            lease_value._transition(self._nonce, ProductionLeaseState.FAILED_CLOSED)
            raise _fail(WindowsBackendReason.PUBLISH_FAILED) from None
        finally:
            if type(private_body) is bytearray and not zeroized:
                _zeroize(private_body)

    def consume_private_media(
        self,
        lease: Task082PrivateMediaReadLeaseV1,
        consumer: PrivateMediaConsumer,
    ) -> WindowsPrivateMediaReadResult:
        with self._claim_lock:
            return self._consume_private_media_locked(lease, consumer)

    def _consume_private_media_locked(
        self,
        lease: Task082PrivateMediaReadLeaseV1,
        consumer: PrivateMediaConsumer,
    ) -> WindowsPrivateMediaReadResult:
        lease_value = self._require_lease(lease, Task082PrivateMediaReadLeaseV1)
        grant = lease_value._grant
        if type(grant) is not WindowsPrivateMediaReadGrant or not callable(consumer):
            lease_value._transition(self._nonce, ProductionLeaseState.FAILED_CLOSED)
            raise _fail(WindowsBackendReason.REQUEST_INVALID)
        aggregate = bytearray()
        started = False
        effect_count = 2
        try:
            effect_count += self._begin_open(lease_value, LeaseKind.READ, grant)
            started = True
            receipt = grant.receipt
            manifest_name = self._manifest_name_from_id(receipt.opaque_artifact_id)
            manifest_read = self._io.read_json(manifest_name)
            manifest = _exact_mapping(manifest_read.document, _MANIFEST_FIELDS)
            if (
                manifest["record_type"] != "Task082WindowsPrivateMediaManifestV1"
                or type(manifest["schema_version"]) is not int
                or manifest["schema_version"] != 1
                or manifest["canonical_owner_task"] != TASK_OWNER
                or manifest["backend_id"] != WINDOWS_BACKEND_ID
                or manifest["cipher_suite"] != self._cipher.cipher_suite
                or manifest["cipher_backend_identity_sha256"]
                != self._cipher.backend_identity_sha256
                or manifest["root_binding_sha256"] != grant.root_binding_sha256
                or manifest["opaque_artifact_id"] != receipt.opaque_artifact_id
                or manifest["logical_slot_ref"] != receipt.logical_slot_ref
                or manifest["artifact_class"] != receipt.artifact_class.value
                or manifest["generation_revision"] != receipt.generation_revision
                or manifest["content_sha256"] != receipt.content_sha256
                or manifest["media_metadata_sha256"] != receipt.media_metadata_sha256
                or manifest["manifest_sha256"]
                != _record_digest(_MANIFEST_DOMAIN, manifest, "manifest_sha256")
            ):
                raise _fail(WindowsBackendReason.MANIFEST_INVALID)
            chunk_count = manifest["chunk_count"]
            plaintext_byte_count = manifest["plaintext_byte_count"]
            chunks = manifest["chunks"]
            if (
                type(chunk_count) is not int
                or not 1 <= chunk_count <= MAX_CHUNKS
                or type(plaintext_byte_count) is not int
                or not 1 <= plaintext_byte_count <= MAX_PRIVATE_MEDIA_BYTES
                or type(chunks) is not list
                or len(chunks) != chunk_count
            ):
                raise _fail(WindowsBackendReason.MANIFEST_INVALID)
            aggregate = bytearray(plaintext_byte_count)
            write_offset = 0
            artifact_key = manifest["artifact_key_sha256"]
            _digest(artifact_key, "artifact_key_sha256")
            expected_id = f"T082-{_digest_hex(artifact_key)}"
            if expected_id != receipt.opaque_artifact_id:
                raise _fail(WindowsBackendReason.MANIFEST_INVALID)
            chunk_reads: list[tuple[str, SecureJsonRead]] = []
            effect_count += 1
            for index, raw_descriptor in enumerate(chunks):
                descriptor = _exact_mapping(raw_descriptor, _CHUNK_DESCRIPTOR_FIELDS)
                expected_name = self._chunk_name(artifact_key, index)
                if (
                    descriptor["relative_name"] != expected_name
                    or descriptor["chunk_index"] != index
                    or type(descriptor["plaintext_byte_count"]) is not int
                    or not 1 <= descriptor["plaintext_byte_count"] <= CHUNK_PLAINTEXT_BYTES
                ):
                    raise _fail(WindowsBackendReason.MANIFEST_INVALID)
                readback = self._io.read_json(expected_name)
                effect_count += 1
                chunk = _exact_mapping(readback.document, _CHUNK_FIELDS)
                if (
                    chunk["record_type"] != "Task082WindowsPrivateMediaChunkV1"
                    or type(chunk["schema_version"]) is not int
                    or chunk["schema_version"] != 1
                    or chunk["canonical_owner_task"] != TASK_OWNER
                    or chunk["cipher_suite"] != self._cipher.cipher_suite
                    or chunk["cipher_backend_identity_sha256"]
                    != self._cipher.backend_identity_sha256
                    or chunk["artifact_key_sha256"] != artifact_key
                    or chunk["chunk_index"] != index
                    or chunk["chunk_count"] != chunk_count
                    or chunk["plaintext_byte_count"]
                    != descriptor["plaintext_byte_count"]
                    or chunk["plaintext_chunk_sha256"]
                    != descriptor["plaintext_chunk_sha256"]
                    or chunk["entropy_sha256"] != descriptor["entropy_sha256"]
                    or chunk["ciphertext_sha256"] != descriptor["ciphertext_sha256"]
                    or descriptor["publish_identity_sha256"]
                    != _identity_sha256(
                        _identity_projection(f"CHUNK_{index}", expected_name, readback)
                    )
                ):
                    raise _fail(WindowsBackendReason.MANIFEST_INVALID)
                try:
                    ciphertext = base64.b64decode(
                        chunk["ciphertext_b64"],
                        validate=True,
                    )
                except (ValueError, TypeError):
                    raise _fail(WindowsBackendReason.CIPHERTEXT_DIGEST_MISMATCH) from None
                if _sha256_buffer(ciphertext) != chunk["ciphertext_sha256"]:
                    raise _fail(WindowsBackendReason.CIPHERTEXT_DIGEST_MISMATCH)
                entropy_sha256, entropy = self._chunk_entropy(
                    artifact_key_sha256=artifact_key,
                    chunk_index=index,
                    chunk_count=chunk_count,
                    plaintext_chunk_sha256=chunk["plaintext_chunk_sha256"],
                    media_metadata_sha256=manifest["media_metadata_sha256"],
                    root_binding_sha256=manifest["root_binding_sha256"],
                    backend_authorization_sha256=manifest["backend_authorization_sha256"],
                )
                if entropy_sha256 != chunk["entropy_sha256"]:
                    raise _fail(WindowsBackendReason.MANIFEST_INVALID)
                try:
                    plaintext_chunk = self._cipher.open(ciphertext, entropy=entropy)
                except WindowsPrivateMediaBackendError:
                    raise
                except Exception:
                    raise _fail(WindowsBackendReason.CIPHER_REJECTED) from None
                try:
                    if (
                        type(plaintext_chunk) is not bytearray
                        or len(plaintext_chunk) != chunk["plaintext_byte_count"]
                        or _sha256_buffer(plaintext_chunk)
                        != chunk["plaintext_chunk_sha256"]
                    ):
                        raise _fail(WindowsBackendReason.PLAINTEXT_DIGEST_MISMATCH)
                    end_offset = write_offset + len(plaintext_chunk)
                    aggregate[write_offset:end_offset] = plaintext_chunk
                    write_offset = end_offset
                finally:
                    if type(plaintext_chunk) is bytearray and not _zeroize(plaintext_chunk):
                        raise _fail(WindowsBackendReason.ZEROIZATION_NOT_CONFIRMED)
                chunk_reads.append((expected_name, readback))
            if (
                write_offset != plaintext_byte_count
                or _sha256_buffer(aggregate) != receipt.content_sha256
            ):
                raise _fail(WindowsBackendReason.PLAINTEXT_DIGEST_MISMATCH)
            physical_identity_sha256 = _aggregate_physical_identity_sha256(
                manifest_name,
                manifest_read,
                chunk_reads,
            )
            if physical_identity_sha256 != receipt.opened_physical_identity_sha256:
                raise _fail(WindowsBackendReason.PHYSICAL_IDENTITY_MISMATCH)
            self._stage("before_private_consumer")
            view = memoryview(aggregate).toreadonly()
            try:
                callback_result = consumer(view)
            except Exception:
                raise _fail(WindowsBackendReason.CALLBACK_FAILED) from None
            finally:
                view.release()
            if callback_result is not None:
                raise _fail(WindowsBackendReason.CALLBACK_FAILED)
            if not _zeroize(aggregate):
                raise _fail(WindowsBackendReason.ZEROIZATION_NOT_CONFIRMED)
            close_identity_sha256 = sha256_bytes(
                canonical_json_bytes(
                    {
                        "operation_id": grant.operation_id,
                        "receipt_sha256": receipt.receipt_sha256,
                        "opened_physical_identity_sha256": physical_identity_sha256,
                        "chunk_count": chunk_count,
                        "plaintext_byte_count": plaintext_byte_count,
                        "body_zeroization_confirmed": True,
                    }
                )
            )
            completion_readback_sha256 = self._persist_completion(
                lease_value,
                grant,
                receipt_sha256=receipt.receipt_sha256,
                completion_kind="READ_CLOSE_IDENTITY_COMPLETION_READBACK",
                completion_binding_sha256=close_identity_sha256,
                callback_completed=True,
                write_recovery_record_sha256=None,
            )
            effect_count += 2
            body = {
                "receipt_sha256": receipt.receipt_sha256,
                "operation_id": grant.operation_id,
                "read_close_handle_identity_sha256": close_identity_sha256,
                "read_completion_readback_sha256": completion_readback_sha256,
                "plaintext_byte_count": plaintext_byte_count,
                "body_zeroization_confirmed": True,
                "callback_completed": True,
                "production_backend_invoked": not self._test_only,
                "private_media_effect_count": effect_count,
                "result_sha256": None,
            }
            body["result_sha256"] = _record_digest(
                _READ_RESULT_DOMAIN,
                body,
                "result_sha256",
            )
            result = WindowsPrivateMediaReadResult(**body)  # type: ignore[arg-type]
            lease_value._transition(
                self._nonce,
                ProductionLeaseState.CONSUMED,
                completion_record_sha256=completion_readback_sha256,
            )
            return result
        except WindowsPrivateMediaBackendError:
            if started and lease_value.state is ProductionLeaseState.OPEN_STARTED:
                lease_value._transition(self._nonce, ProductionLeaseState.COMPLETION_UNKNOWN)
                raise _fail(
                    WindowsBackendReason.COMPLETION_UNKNOWN,
                    completion_unknown=True,
                ) from None
            raise
        except (SecureAuthorityIOError, Task082ContractError, OSError, ValueError, TypeError):
            if started:
                if lease_value.state is ProductionLeaseState.OPEN_STARTED:
                    lease_value._transition(
                        self._nonce,
                        ProductionLeaseState.COMPLETION_UNKNOWN,
                    )
                raise _fail(
                    WindowsBackendReason.COMPLETION_UNKNOWN,
                    completion_unknown=True,
                ) from None
            lease_value._transition(self._nonce, ProductionLeaseState.FAILED_CLOSED)
            raise _fail(WindowsBackendReason.READ_FAILED) from None
        except Exception:
            if started:
                if lease_value.state is ProductionLeaseState.OPEN_STARTED:
                    lease_value._transition(
                        self._nonce,
                        ProductionLeaseState.COMPLETION_UNKNOWN,
                    )
                raise _fail(
                    WindowsBackendReason.COMPLETION_UNKNOWN,
                    completion_unknown=True,
                ) from None
            lease_value._transition(self._nonce, ProductionLeaseState.FAILED_CLOSED)
            raise _fail(WindowsBackendReason.READ_FAILED) from None
        finally:
            if aggregate:
                _zeroize(aggregate)

    def read_lease_state(
        self,
        lease: Task082PrivateMediaWriteLeaseV1 | Task082PrivateMediaReadLeaseV1,
    ) -> WindowsPrivateMediaLeaseStateReadback:
        if type(lease) not in {
            Task082PrivateMediaWriteLeaseV1,
            Task082PrivateMediaReadLeaseV1,
        } or lease._backend_nonce is not self._nonce:
            raise _fail(WindowsBackendReason.RECEIPT_AS_CAPABILITY)
        return self.read_durable_lease_state(lease._grant)

    def _read_optional_record(self, relative_name: str) -> SecureJsonRead | None:
        try:
            return self._io.read_json(relative_name)
        except SecureAuthorityIOError as exc:
            if exc.code == "NOT_FOUND":
                return None
            raise _fail(
                WindowsBackendReason.COMPLETION_UNKNOWN,
                completion_unknown=True,
            ) from None

    @staticmethod
    def _validate_operation_record(
        readback: SecureJsonRead,
        *,
        fields: frozenset[str],
        record_type: str,
        domain: bytes,
        kind: LeaseKind,
        grant: WindowsPrivateMediaWriteGrant | WindowsPrivateMediaReadGrant,
    ) -> dict[str, Any]:
        try:
            value = _exact_mapping(readback.document, fields)
        except WindowsPrivateMediaBackendError:
            raise _fail(
                WindowsBackendReason.COMPLETION_UNKNOWN,
                completion_unknown=True,
            ) from None
        if (
            value["record_type"] != record_type
            or type(value["schema_version"]) is not int
            or value["schema_version"] != 1
            or value["canonical_owner_task"] != TASK_OWNER
            or value["lease_kind"] != kind.value
            or value["operation_id"] != grant.operation_id
            or value["grant_sha256"] != _grant_sha256(grant)
            or value["record_sha256"]
            != _record_digest(domain, value, "record_sha256")
        ):
            raise _fail(
                WindowsBackendReason.COMPLETION_UNKNOWN,
                completion_unknown=True,
            )
        _digest(value["record_sha256"], "record_sha256")
        return value

    @staticmethod
    def _validate_write_recovery_record(
        readback: SecureJsonRead,
        grant: WindowsPrivateMediaWriteGrant,
    ) -> WindowsPrivateMediaWriteResult:
        try:
            value = _exact_mapping(readback.document, _WRITE_RECOVERY_FIELDS)
            receipt = PrivateMediaCustodyReceipt.from_mapping(value["receipt"])
            event = PrivateMediaGenerationEvent.from_mapping(value["generation_event"])
        except (WindowsPrivateMediaBackendError, Task082ContractError, TypeError, ValueError):
            raise _fail(
                WindowsBackendReason.COMPLETION_UNKNOWN,
                completion_unknown=True,
            ) from None
        result_body = {
            "receipt": receipt.as_dict(),
            "generation_event": event.as_dict(),
            "write_publish_pinned_readback_sha256": (
                value["write_publish_pinned_readback_sha256"]
            ),
            "plaintext_byte_count": value["plaintext_byte_count"],
            "chunk_count": value["chunk_count"],
            "body_zeroization_confirmed": value["body_zeroization_confirmed"],
            "production_backend_invoked": value["production_backend_invoked"],
            "private_media_effect_count": value["private_media_effect_count"],
            "result_sha256": value["result_sha256"],
        }
        if (
            value["record_type"] != "Task082WindowsPrivateMediaWriteRecoveryV1"
            or type(value["schema_version"]) is not int
            or value["schema_version"] != 1
            or value["canonical_owner_task"] != TASK_OWNER
            or value["operation_id"] != grant.operation_id
            or value["grant_sha256"] != _grant_sha256(grant)
            or value["record_sha256"]
            != _record_digest(
                _WRITE_RECOVERY_DOMAIN,
                value,
                "record_sha256",
            )
            or value["result_sha256"]
            != _record_digest(
                _WRITE_RESULT_DOMAIN,
                result_body,
                "result_sha256",
            )
            or receipt.logical_slot_ref != grant.logical_slot_ref
            or receipt.generation_revision != grant.generation_revision
            or receipt.owner_subject_revision_sha256
            != grant.owner_subject_revision_sha256
            or receipt.content_sha256 != grant.expected_content_sha256
            or receipt.media_metadata_sha256 != grant.media_metadata_sha256
            or receipt.consent_rights_revision_sha256
            != grant.consent_rights_revision_sha256
            or receipt.generation_event_sha256 != event.event_sha256
            or receipt.event_head_sha256 != event.event_sha256
            or event.predecessor_event_sha256 != grant.predecessor_event_sha256
            or event.event_revision != grant.event_revision
            or type(value["plaintext_byte_count"]) is not int
            or not 1 <= value["plaintext_byte_count"] <= MAX_PRIVATE_MEDIA_BYTES
            or type(value["chunk_count"]) is not int
            or not 1 <= value["chunk_count"] <= MAX_CHUNKS
            or value["chunk_count"]
            != (
                value["plaintext_byte_count"] + CHUNK_PLAINTEXT_BYTES - 1
            )
            // CHUNK_PLAINTEXT_BYTES
            or value["body_zeroization_confirmed"] is not True
            or type(value["production_backend_invoked"]) is not bool
            or type(value["private_media_effect_count"]) is not int
            or value["private_media_effect_count"] != 13 + 2 * value["chunk_count"]
        ):
            raise _fail(
                WindowsBackendReason.COMPLETION_UNKNOWN,
                completion_unknown=True,
            )
        for field in (
            "write_publish_pinned_readback_sha256",
            "result_sha256",
            "record_sha256",
        ):
            _digest(value[field], field)
        return WindowsPrivateMediaWriteResult(
            receipt=receipt,
            generation_event=event,
            write_publish_pinned_readback_sha256=(
                value["write_publish_pinned_readback_sha256"]
            ),
            plaintext_byte_count=value["plaintext_byte_count"],
            chunk_count=value["chunk_count"],
            body_zeroization_confirmed=True,
            production_backend_invoked=value["production_backend_invoked"],
            private_media_effect_count=value["private_media_effect_count"],
            result_sha256=value["result_sha256"],
        )

    @staticmethod
    def _validate_slot_reservation(
        readback: SecureJsonRead,
        grant: WindowsPrivateMediaWriteGrant,
        *,
        burn_record_sha256: str,
        currentness_reservation_sha256: str,
        root_observation_sha256: str,
    ) -> None:
        try:
            value = _exact_mapping(readback.document, _SLOT_RESERVATION_FIELDS)
        except WindowsPrivateMediaBackendError:
            raise _fail(
                WindowsBackendReason.COMPLETION_UNKNOWN,
                completion_unknown=True,
            ) from None
        artifact_class = (
            grant.artifact_class.value
            if isinstance(grant.artifact_class, ArtifactClass)
            else grant.artifact_class
        )
        if (
            value["record_type"] != "Task082WindowsPrivateMediaSlotReservationV1"
            or type(value["schema_version"]) is not int
            or value["schema_version"] != 1
            or value["canonical_owner_task"] != TASK_OWNER
            or value["logical_slot_ref"] != grant.logical_slot_ref
            or value["artifact_class"] != artifact_class
            or value["generation_revision"] != grant.generation_revision
            or value["operation_id"] != grant.operation_id
            or value["grant_sha256"] != _grant_sha256(grant)
            or value["predecessor_event_sha256"]
            != grant.predecessor_event_sha256
            or value["predecessor_receipt_sha256"]
            != grant.predecessor_receipt_sha256
            or value["currentness_binding_sha256"]
            != WindowsPrivateMediaCustodyBackend._currentness_binding_sha256(
                LeaseKind.WRITE,
                grant,
            )
            or value["currentness_reservation_sha256"]
            != currentness_reservation_sha256
            or value["root_observation_sha256"] != root_observation_sha256
            or value["burn_record_sha256"] != burn_record_sha256
            or value["record_sha256"]
            != _record_digest(
                _SLOT_RESERVATION_DOMAIN,
                value,
                "record_sha256",
            )
        ):
            raise _fail(
                WindowsBackendReason.COMPLETION_UNKNOWN,
                completion_unknown=True,
            )
        _timestamp(value["reserved_at"], "reserved_at")

    def read_durable_lease_state(
        self,
        grant: WindowsPrivateMediaWriteGrant | WindowsPrivateMediaReadGrant,
    ) -> WindowsPrivateMediaLeaseStateReadback:
        if type(grant) is WindowsPrivateMediaWriteGrant:
            kind = LeaseKind.WRITE
        elif type(grant) is WindowsPrivateMediaReadGrant:
            kind = LeaseKind.READ
        else:
            raise _fail(WindowsBackendReason.RECEIPT_AS_CAPABILITY)
        if grant.root_binding_sha256 != self._root_binding.binding_sha256:
            raise _fail(WindowsBackendReason.ROOT_BINDING_MISMATCH)
        issue_name, open_name, completion_name = self._lease_names(
            kind,
            grant.operation_id,
        )
        issue_read = self._read_optional_record(issue_name)
        if issue_read is None:
            raise _fail(WindowsBackendReason.REQUEST_INVALID)
        issue = self._validate_operation_record(
            issue_read,
            fields=_LEASE_ISSUANCE_FIELDS,
            record_type="Task082WindowsPrivateMediaLeaseIssuanceV1",
            domain=_LEASE_OPERATION_DOMAIN,
            kind=kind,
            grant=grant,
        )
        issuance_record_sha256 = _record_observation_sha256(
            "LEASE_ISSUANCE",
            issue_name,
            issue_read,
        )
        if (
            issue["root_binding_sha256"] != grant.root_binding_sha256
            or issue["backend_authorization_sha256"]
            != grant.backend_authorization_sha256
            or issue["currentness_binding_sha256"]
            != self._currentness_binding_sha256(kind, grant)
            or issue["body_binding_sha256"]
            != self._body_binding_sha256(kind, grant)
            or issue["state"] != ProductionLeaseState.ISSUED.value
        ):
            raise _fail(
                WindowsBackendReason.COMPLETION_UNKNOWN,
                completion_unknown=True,
            )
        _digest(issue["root_observation_sha256"], "root_observation_sha256")
        admitted_at = _timestamp(issue["admitted_at"], "admitted_at")
        if not (
            _timestamp(grant.issued_at, "issued_at")
            <= admitted_at
            < _timestamp(grant.expires_at, "expires_at")
        ):
            raise _fail(
                WindowsBackendReason.COMPLETION_UNKNOWN,
                completion_unknown=True,
            )
        open_read = self._read_optional_record(open_name)
        completion_read = self._read_optional_record(completion_name)
        state = ProductionLeaseState.ISSUED
        burn_record_sha256: str | None = None
        completion_record_sha256: str | None = None
        currentness_reservation_sha256: str | None = None
        root_observation_sha256: str | None = None
        write_recovery_record_sha256: str | None = None
        reservation_read: SecureJsonRead | None = None
        if open_read is not None:
            opened = self._validate_operation_record(
                open_read,
                fields=_LEASE_OPEN_FIELDS,
                record_type="Task082WindowsPrivateMediaLeaseOpenV1",
                domain=_LEASE_OPEN_DOMAIN,
                kind=kind,
                grant=grant,
            )
            if (
                opened["issuance_record_sha256"] != issuance_record_sha256
                or opened["root_binding_sha256"] != grant.root_binding_sha256
                or opened["currentness_binding_sha256"]
                != self._currentness_binding_sha256(kind, grant)
                or opened["body_binding_sha256"]
                != self._body_binding_sha256(kind, grant)
                or opened["state"] != ProductionLeaseState.OPEN_STARTED.value
            ):
                raise _fail(
                    WindowsBackendReason.COMPLETION_UNKNOWN,
                    completion_unknown=True,
                )
            root_observation_sha256 = _digest(
                opened["root_observation_sha256"],
                "root_observation_sha256",
            )
            currentness_reservation_sha256 = _digest(
                opened["currentness_reservation_sha256"],
                "currentness_reservation_sha256",
            )
            opened_at = _timestamp(opened["opened_at"], "opened_at")
            if not admitted_at <= opened_at < _timestamp(grant.expires_at, "expires_at"):
                raise _fail(
                    WindowsBackendReason.COMPLETION_UNKNOWN,
                    completion_unknown=True,
                )
            burn_record_sha256 = _record_observation_sha256(
                "LEASE_OPEN",
                open_name,
                open_read,
            )
            if kind is LeaseKind.WRITE:
                if type(grant) is not WindowsPrivateMediaWriteGrant:
                    raise _fail(WindowsBackendReason.REQUEST_INVALID)
                reservation_read = self._read_optional_record(
                    self._slot_reservation_name(grant)
                )
            state = ProductionLeaseState.COMPLETION_UNKNOWN
        if completion_read is not None:
            if open_read is None:
                raise _fail(
                    WindowsBackendReason.COMPLETION_UNKNOWN,
                    completion_unknown=True,
                )
            if kind is LeaseKind.WRITE:
                if (
                    type(grant) is not WindowsPrivateMediaWriteGrant
                    or reservation_read is None
                    or burn_record_sha256 is None
                    or currentness_reservation_sha256 is None
                    or root_observation_sha256 is None
                ):
                    raise _fail(
                        WindowsBackendReason.COMPLETION_UNKNOWN,
                        completion_unknown=True,
                    )
                self._validate_slot_reservation(
                    reservation_read,
                    grant,
                    burn_record_sha256=burn_record_sha256,
                    currentness_reservation_sha256=(
                        currentness_reservation_sha256
                    ),
                    root_observation_sha256=root_observation_sha256,
                )
            completed = self._validate_operation_record(
                completion_read,
                fields=_LEASE_COMPLETION_FIELDS,
                record_type="Task082WindowsPrivateMediaLeaseCompletionV1",
                domain=_LEASE_COMPLETION_DOMAIN,
                kind=kind,
                grant=grant,
            )
            if (
                completed["issuance_record_sha256"] != issuance_record_sha256
                or completed["burn_record_sha256"] != burn_record_sha256
                or completed["currentness_reservation_sha256"]
                != currentness_reservation_sha256
                or completed["body_zeroization_confirmed"] is not True
                or completed["state"] != ProductionLeaseState.CONSUMED.value
            ):
                raise _fail(
                    WindowsBackendReason.COMPLETION_UNKNOWN,
                    completion_unknown=True,
                )
            _digest(completed["receipt_sha256"], "receipt_sha256")
            _digest(
                completed["completion_binding_sha256"],
                "completion_binding_sha256",
            )
            completed_at = _timestamp(completed["completed_at"], "completed_at")
            if completed_at < opened_at:
                raise _fail(
                    WindowsBackendReason.COMPLETION_UNKNOWN,
                    completion_unknown=True,
                )
            expected_kind = (
                "WRITE_PUBLISH_PINNED_READBACK"
                if kind is LeaseKind.WRITE
                else "READ_CLOSE_IDENTITY_COMPLETION_READBACK"
            )
            if (
                completed["completion_kind"] != expected_kind
                or completed["callback_completed"] is not (kind is LeaseKind.READ)
            ):
                raise _fail(
                    WindowsBackendReason.COMPLETION_UNKNOWN,
                    completion_unknown=True,
                )
            if kind is LeaseKind.WRITE:
                if type(grant) is not WindowsPrivateMediaWriteGrant:
                    raise _fail(WindowsBackendReason.REQUEST_INVALID)
                recovery_name = self._write_recovery_name(grant.operation_id)
                recovery_read = self._read_optional_record(recovery_name)
                if recovery_read is None:
                    raise _fail(
                        WindowsBackendReason.COMPLETION_UNKNOWN,
                        completion_unknown=True,
                    )
                recovered_result = self._validate_write_recovery_record(
                    recovery_read,
                    grant,
                )
                write_recovery_record_sha256 = _record_observation_sha256(
                    "WRITE_RECOVERY",
                    recovery_name,
                    recovery_read,
                )
                if (
                    completed["write_recovery_record_sha256"]
                    != write_recovery_record_sha256
                    or completed["receipt_sha256"]
                    != recovered_result.receipt.receipt_sha256
                    or completed["completion_binding_sha256"]
                    != recovered_result.write_publish_pinned_readback_sha256
                ):
                    raise _fail(
                        WindowsBackendReason.COMPLETION_UNKNOWN,
                        completion_unknown=True,
                    )
            elif completed["write_recovery_record_sha256"] is not None:
                raise _fail(
                    WindowsBackendReason.COMPLETION_UNKNOWN,
                    completion_unknown=True,
                )
            completion_record_sha256 = _record_observation_sha256(
                "LEASE_COMPLETION",
                completion_name,
                completion_read,
            )
            state = ProductionLeaseState.CONSUMED
        return WindowsPrivateMediaLeaseStateReadback(
            lease_kind=kind,
            operation_id=grant.operation_id,
            state=state,
            replayable=False,
            body_returned=False,
            capability_returned=False,
            durable=True,
            issuance_record_sha256=issuance_record_sha256,
            burn_record_sha256=burn_record_sha256,
            completion_record_sha256=completion_record_sha256,
            currentness_reservation_sha256=currentness_reservation_sha256,
            write_recovery_record_sha256=write_recovery_record_sha256,
        )

    def read_durable_write_result(
        self,
        grant: WindowsPrivateMediaWriteGrant,
    ) -> WindowsPrivateMediaWriteResult:
        if type(grant) is not WindowsPrivateMediaWriteGrant:
            raise _fail(WindowsBackendReason.RECEIPT_AS_CAPABILITY)
        state = self.read_durable_lease_state(grant)
        if (
            state.state is not ProductionLeaseState.CONSUMED
            or state.write_recovery_record_sha256 is None
        ):
            raise _fail(
                WindowsBackendReason.COMPLETION_UNKNOWN,
                completion_unknown=True,
            )
        relative_name = self._write_recovery_name(grant.operation_id)
        readback = self._read_optional_record(relative_name)
        if readback is None:
            raise _fail(
                WindowsBackendReason.COMPLETION_UNKNOWN,
                completion_unknown=True,
            )
        if (
            _record_observation_sha256("WRITE_RECOVERY", relative_name, readback)
            != state.write_recovery_record_sha256
        ):
            raise _fail(
                WindowsBackendReason.COMPLETION_UNKNOWN,
                completion_unknown=True,
            )
        return self._validate_write_recovery_record(readback, grant)


__all__ = [
    "CHUNK_PLAINTEXT_BYTES",
    "MAX_PRIVATE_MEDIA_BYTES",
    "ProductionLeaseState",
    "Task082PrivateMediaReadLeaseV1",
    "Task082PrivateMediaWriteLeaseV1",
    "WINDOWS_BACKEND_ID",
    "WINDOWS_BACKEND_VERSION",
    "WINDOWS_DPAPI_BACKEND_IDENTITY_SHA256",
    "WINDOWS_DPAPI_CIPHER_SUITE",
    "WindowsBackendReason",
    "WindowsCurrentUserDpapiPrivateMediaCipher",
    "WindowsPrivateMediaBackendError",
    "WindowsPrivateMediaCustodyBackend",
    "WindowsPrivateMediaCurrentnessReservationReceipt",
    "WindowsPrivateMediaLeaseStateReadback",
    "WindowsPrivateMediaReadGrant",
    "WindowsPrivateMediaReadResult",
    "WindowsPrivateMediaRootBinding",
    "WindowsPrivateMediaRootObservation",
    "WindowsPrivateMediaWriteGrant",
    "WindowsPrivateMediaWriteResult",
]
