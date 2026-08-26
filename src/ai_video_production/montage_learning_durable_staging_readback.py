"""TASK-058 P1C-B handle-bound, non-authoritative staging read-back."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import json
import os
from pathlib import Path, PureWindowsPath
import re
import stat
from typing import Any, Mapping

from .montage_learning_admission_store import (
    RELATIVE_PATH,
    MontageLearningAdmissionLedger,
)
from .montage_learning_bridge_contracts import EXACT_CONTRACT_PROFILE
from .montage_learning_canonical_preflight import (
    MontageLearningCanonicalPreflightError,
    compile_montage_learning_canonical_preflight,
)
from .serialization import canonical_json_bytes, sha256_bytes


SCHEMA_VERSION = "1.0.0"
RECORD_TYPE = "MONTAGE_LEARNING_DURABLE_STAGING_READBACK"
TASK_OWNER = "TASK-058"
NONAUTHORITATIVE_DURABLE_STAGING_READBACK_PROJECTION = (
    "NONAUTHORITATIVE_DURABLE_STAGING_READBACK_PROJECTION"
)
READBACK_DOMAIN = b"TASK058_MONTAGE_LEARNING_DURABLE_STAGING_READBACK_V1\0"
FILE_IDENTITY_DOMAIN = b"TASK058_MONTAGE_LEARNING_STAGING_FILE_IDENTITY_V1\0"
_MAX_STORE_BYTES = 32 * 1024 * 1024
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$")
_RUNTIME_TOKEN = object()

_GENERIC_READ = 0x80000000
_FILE_READ_ATTRIBUTES = 0x0080
_FILE_SHARE_READ = 0x00000001
_FILE_SHARE_WRITE = 0x00000002
_FILE_SHARE_DELETE = 0x00000004
_OPEN_EXISTING = 3
_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_FILE_ATTRIBUTE_DIRECTORY = 0x00000010
_FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
_HANDLE_FLAG_INHERIT = 0x00000001
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class MontageLearningDurableStagingReadbackError(ValueError):
    """Raised when a durable staging observation cannot be proven."""


def _digest(value: object, name: str) -> str:
    if type(value) is not str or _DIGEST_RE.fullmatch(value) is None:
        raise MontageLearningDurableStagingReadbackError(f"{name} is invalid")
    return value


def _identifier(value: object, name: str) -> str:
    if type(value) is not str or _ID_RE.fullmatch(value) is None:
        raise MontageLearningDurableStagingReadbackError(f"{name} is invalid")
    return value


def _revision(value: object) -> int:
    if type(value) is not int or value < 1:
        raise MontageLearningDurableStagingReadbackError(
            "expected_revision must be a positive integer"
        )
    return value


def _snapshot_exact_json(value: Mapping[str, Any]) -> dict[str, Any]:
    def snapshot(item: object, path: str) -> Any:
        if item is None or type(item) in {str, bool, int}:
            return item
        if type(item) is list:
            return [snapshot(child, f"{path}[]") for child in item]
        if type(item) is dict:
            result: dict[str, Any] = {}
            for key, child in item.items():
                if type(key) is not str:
                    raise MontageLearningDurableStagingReadbackError(
                        f"{path} keys must be exact strings"
                    )
                result[key] = snapshot(child, f"{path}.{key}")
            return result
        raise MontageLearningDurableStagingReadbackError(
            f"{path} must contain exact built-in JSON values"
        )

    if type(value) is not dict:
        raise MontageLearningDurableStagingReadbackError(
            "delivery must be an exact built-in object"
        )
    return snapshot(value, "delivery")


@dataclass(frozen=True, slots=True)
class _PinnedLedgerBytes:
    raw: bytes
    file_identity_sha256: str
    platform_security_model: str


class _FILE_ATTRIBUTE_TAG_INFO(ctypes.Structure):
    _fields_ = (
        ("FileAttributes", wintypes.DWORD),
        ("ReparseTag", wintypes.DWORD),
    )


class _FILE_ID_INFO(ctypes.Structure):
    _fields_ = (
        ("VolumeSerialNumber", ctypes.c_ulonglong),
        ("FileId", ctypes.c_ubyte * 16),
    )


class _SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = (
        ("nLength", wintypes.DWORD),
        ("lpSecurityDescriptor", ctypes.c_void_p),
        ("bInheritHandle", wintypes.BOOL),
    )


@dataclass(frozen=True, slots=True)
class _WindowsIdentity:
    canonical_path: str
    volume_serial: int
    file_id: bytes
    directory: bool


def _windows_canonical_path(value: str) -> str:
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return str(PureWindowsPath(value))


class _WindowsPinnedReadPort:
    """Private non-inheritable Win32 handle port."""

    def __init__(self) -> None:
        if os.name != "nt":
            raise MontageLearningDurableStagingReadbackError(
                "Windows handle port is unavailable"
            )
        self._kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel.CreateFileW.argtypes = (
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(_SECURITY_ATTRIBUTES),
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        )
        self._kernel.CreateFileW.restype = wintypes.HANDLE
        self._kernel.SetHandleInformation.argtypes = (
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.DWORD,
        )
        self._kernel.SetHandleInformation.restype = wintypes.BOOL
        self._kernel.GetHandleInformation.argtypes = (
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        )
        self._kernel.GetHandleInformation.restype = wintypes.BOOL
        self._kernel.GetFileInformationByHandleEx.argtypes = (
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        )
        self._kernel.GetFileInformationByHandleEx.restype = wintypes.BOOL
        self._kernel.GetFinalPathNameByHandleW.argtypes = (
            wintypes.HANDLE,
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
        )
        self._kernel.GetFinalPathNameByHandleW.restype = wintypes.DWORD
        self._kernel.GetFileSizeEx.argtypes = (
            wintypes.HANDLE,
            ctypes.POINTER(ctypes.c_longlong),
        )
        self._kernel.GetFileSizeEx.restype = wintypes.BOOL
        self._kernel.ReadFile.argtypes = (
            wintypes.HANDLE,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.c_void_p,
        )
        self._kernel.ReadFile.restype = wintypes.BOOL
        self._kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        self._kernel.CloseHandle.restype = wintypes.BOOL

    def open(self, path: Path, *, directory: bool) -> int:
        access = _FILE_READ_ATTRIBUTES if directory else _GENERIC_READ
        share = (
            _FILE_SHARE_READ | _FILE_SHARE_WRITE | _FILE_SHARE_DELETE
            if directory
            else _FILE_SHARE_READ
        )
        flags = _FILE_FLAG_OPEN_REPARSE_POINT
        if directory:
            flags |= _FILE_FLAG_BACKUP_SEMANTICS
        security = _SECURITY_ATTRIBUTES(
            ctypes.sizeof(_SECURITY_ATTRIBUTES), None, False
        )
        handle = self._kernel.CreateFileW(
            str(path), access, share, ctypes.byref(security),
            _OPEN_EXISTING, flags, None,
        )
        if handle in (None, 0, _INVALID_HANDLE_VALUE):
            raise MontageLearningDurableStagingReadbackError(
                "handle open failed"
            )
        handle_value = int(handle)
        if not self._kernel.SetHandleInformation(
            handle_value, _HANDLE_FLAG_INHERIT, 0
        ):
            self.close(handle_value)
            raise MontageLearningDurableStagingReadbackError(
                "handle inheritance could not be disabled"
            )
        flags_value = wintypes.DWORD()
        if (
            not self._kernel.GetHandleInformation(
                handle_value, ctypes.byref(flags_value)
            )
            or flags_value.value & _HANDLE_FLAG_INHERIT
        ):
            self.close(handle_value)
            raise MontageLearningDurableStagingReadbackError(
                "handle inheritance is unsafe"
            )
        return handle_value

    def identity(
        self, handle: int, expected_path: Path, *, directory: bool
    ) -> _WindowsIdentity:
        tag = _FILE_ATTRIBUTE_TAG_INFO()
        if not self._kernel.GetFileInformationByHandleEx(
            handle, 9, ctypes.byref(tag), ctypes.sizeof(tag)
        ):
            raise MontageLearningDurableStagingReadbackError(
                "handle attributes are unavailable"
            )
        if tag.FileAttributes & _FILE_ATTRIBUTE_REPARSE_POINT:
            raise MontageLearningDurableStagingReadbackError(
                "reparse points are forbidden"
            )
        if bool(tag.FileAttributes & _FILE_ATTRIBUTE_DIRECTORY) is not directory:
            raise MontageLearningDurableStagingReadbackError(
                "handle type mismatch"
            )
        capacity = 32768
        buffer = ctypes.create_unicode_buffer(capacity)
        length = self._kernel.GetFinalPathNameByHandleW(
            handle, buffer, capacity, 0
        )
        if length == 0 or length >= capacity:
            raise MontageLearningDurableStagingReadbackError(
                "final handle path is unavailable"
            )
        actual = _windows_canonical_path(buffer.value)
        expected = str(PureWindowsPath(expected_path))
        if os.path.normcase(os.path.normpath(actual)) != os.path.normcase(
            os.path.normpath(expected)
        ):
            raise MontageLearningDurableStagingReadbackError(
                "final handle path mismatch"
            )
        info = _FILE_ID_INFO()
        if not self._kernel.GetFileInformationByHandleEx(
            handle, 18, ctypes.byref(info), ctypes.sizeof(info)
        ):
            raise MontageLearningDurableStagingReadbackError(
                "file identity is unavailable"
            )
        file_id = bytes(info.FileId)
        if not any(file_id):
            raise MontageLearningDurableStagingReadbackError(
                "file identity is invalid"
            )
        return _WindowsIdentity(actual, int(info.VolumeSerialNumber), file_id, directory)

    def read(self, handle: int) -> bytes:
        size = ctypes.c_longlong()
        if not self._kernel.GetFileSizeEx(handle, ctypes.byref(size)):
            raise MontageLearningDurableStagingReadbackError(
                "ledger size is unavailable"
            )
        if not 1 <= size.value <= _MAX_STORE_BYTES:
            raise MontageLearningDurableStagingReadbackError(
                "ledger size is invalid"
            )
        buffer = ctypes.create_string_buffer(size.value)
        read = wintypes.DWORD()
        if not self._kernel.ReadFile(
            handle, buffer, size.value, ctypes.byref(read), None
        ):
            raise MontageLearningDurableStagingReadbackError(
                "ledger read failed"
            )
        after = ctypes.c_longlong()
        if (
            read.value != size.value
            or not self._kernel.GetFileSizeEx(handle, ctypes.byref(after))
            or after.value != size.value
        ):
            raise MontageLearningDurableStagingReadbackError(
                "ledger changed during read"
            )
        return bytes(buffer.raw[: size.value])

    def close(self, handle: int) -> bool:
        return bool(self._kernel.CloseHandle(handle))


_WINDOWS_PORT_FACTORY = _WindowsPinnedReadPort


def _identity_digest(body: Mapping[str, object]) -> str:
    return sha256_bytes(FILE_IDENTITY_DOMAIN + canonical_json_bytes(body))


def _read_windows(project_root: Path) -> _PinnedLedgerBytes:
    port = _WINDOWS_PORT_FACTORY()
    state_path = project_root / RELATIVE_PATH.parent
    ledger_path = project_root / RELATIVE_PATH
    handles: list[int] = []
    primary_error: BaseException | None = None
    result: _PinnedLedgerBytes | None = None
    try:
        root_handle = port.open(project_root, directory=True)
        handles.append(root_handle)
        root_identity = port.identity(root_handle, project_root, directory=True)
        state_handle = port.open(state_path, directory=True)
        handles.append(state_handle)
        state_identity = port.identity(state_handle, state_path, directory=True)
        ledger_handle = port.open(ledger_path, directory=False)
        handles.append(ledger_handle)
        ledger_identity = port.identity(ledger_handle, ledger_path, directory=False)
        if len({
            root_identity.volume_serial,
            state_identity.volume_serial,
            ledger_identity.volume_serial,
        }) != 1:
            raise MontageLearningDurableStagingReadbackError(
                "handle chain crosses volumes"
            )
        raw = port.read(ledger_handle)
        identity_sha = _identity_digest({
            "platform": "WINDOWS_PINNED_HANDLE_READ_V1",
            "relative_path": RELATIVE_PATH.as_posix(),
            "volume_serial": ledger_identity.volume_serial,
            "file_id": ledger_identity.file_id.hex(),
            "byte_count": len(raw),
        })
        result = _PinnedLedgerBytes(
            raw, identity_sha, "WINDOWS_PINNED_HANDLE_READ_V1"
        )
    except BaseException as exc:
        primary_error = exc
    close_failed = False
    for handle in reversed(handles):
        try:
            close_failed = not port.close(handle) or close_failed
        except BaseException:
            close_failed = True
    if close_failed:
        raise MontageLearningDurableStagingReadbackError(
            "one or more pinned handles failed to close"
        ) from primary_error
    if primary_error is not None:
        if isinstance(primary_error, (KeyboardInterrupt, SystemExit)):
            raise primary_error
        if isinstance(primary_error, MontageLearningDurableStagingReadbackError):
            raise primary_error
        raise MontageLearningDurableStagingReadbackError(
            "Windows pinned read failed"
        ) from primary_error
    if result is None:
        raise MontageLearningDurableStagingReadbackError(
            "Windows pinned read produced no result"
        )
    return result


def _read_posix(project_root: Path) -> _PinnedLedgerBytes:
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    if not nofollow or not directory or os.open not in os.supports_dir_fd:
        raise MontageLearningDurableStagingReadbackError(
            "required POSIX handle features are unavailable"
        )
    descriptors: list[int] = []
    primary_error: BaseException | None = None
    result: _PinnedLedgerBytes | None = None
    try:
        root_fd = os.open(project_root, os.O_RDONLY | directory | nofollow)
        descriptors.append(root_fd)
        root_info = os.fstat(root_fd)
        if not stat.S_ISDIR(root_info.st_mode):
            raise MontageLearningDurableStagingReadbackError(
                "Project root handle is not a directory"
            )
        state_fd = os.open(
            RELATIVE_PATH.parent.name,
            os.O_RDONLY | directory | nofollow,
            dir_fd=root_fd,
        )
        descriptors.append(state_fd)
        state_info = os.fstat(state_fd)
        if not stat.S_ISDIR(state_info.st_mode):
            raise MontageLearningDurableStagingReadbackError(
                "state handle is not a directory"
            )
        file_fd = os.open(
            RELATIVE_PATH.name,
            os.O_RDONLY | getattr(os, "O_BINARY", 0) | nofollow,
            dir_fd=state_fd,
        )
        descriptors.append(file_fd)
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode) or not 1 <= before.st_size <= _MAX_STORE_BYTES:
            raise MontageLearningDurableStagingReadbackError(
                "ledger handle is not a bounded regular file"
            )
        chunks: list[bytes] = []
        remaining = _MAX_STORE_BYTES + 1
        while remaining:
            chunk = os.read(file_fd, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(file_fd)
        identity = lambda item: (
            item.st_dev,
            item.st_ino,
            item.st_size,
            item.st_mtime_ns,
            item.st_ctime_ns,
        )
        if (
            identity(before) != identity(after)
            or len(raw) != before.st_size
            or not 1 <= len(raw) <= _MAX_STORE_BYTES
        ):
            raise MontageLearningDurableStagingReadbackError(
                "ledger changed during read"
            )
        identity_sha = _identity_digest({
            "platform": "POSIX_OPENAT_NOFOLLOW_READ_V1",
            "relative_path": RELATIVE_PATH.as_posix(),
            "device": before.st_dev,
            "inode": before.st_ino,
            "byte_count": len(raw),
        })
        result = _PinnedLedgerBytes(
            raw, identity_sha, "POSIX_OPENAT_NOFOLLOW_READ_V1"
        )
    except BaseException as exc:
        primary_error = exc
    close_failed = False
    for descriptor in reversed(descriptors):
        try:
            os.close(descriptor)
        except BaseException:
            close_failed = True
    if close_failed:
        raise MontageLearningDurableStagingReadbackError(
            "one or more pinned descriptors failed to close"
        ) from primary_error
    if primary_error is not None:
        if isinstance(primary_error, (KeyboardInterrupt, SystemExit)):
            raise primary_error
        if isinstance(primary_error, MontageLearningDurableStagingReadbackError):
            raise primary_error
        raise MontageLearningDurableStagingReadbackError(
            "POSIX pinned read failed"
        ) from primary_error
    if result is None:
        raise MontageLearningDurableStagingReadbackError(
            "POSIX pinned read produced no result"
        )
    return result


def _read_pinned_ledger(project_root: Path) -> _PinnedLedgerBytes:
    if not project_root.is_absolute():
        raise MontageLearningDurableStagingReadbackError(
            "project_root must be absolute"
        )
    return _read_windows(project_root) if os.name == "nt" else _read_posix(project_root)


def _parse_exact_ledger(raw: bytes) -> MontageLearningAdmissionLedger:
    if not 1 <= len(raw) <= _MAX_STORE_BYTES:
        raise MontageLearningDurableStagingReadbackError(
            "pinned ledger byte count is invalid"
        )
    try:
        document = json.loads(raw.decode("utf-8"))
        if type(document) is not dict:
            raise ValueError("ledger root must be an exact object")
        if canonical_json_bytes(document) + b"\n" != raw:
            raise ValueError("ledger bytes are not canonical")
        return MontageLearningAdmissionLedger.from_dict(document)
    except (UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise MontageLearningDurableStagingReadbackError(
            "pinned ledger bytes failed exact verification"
        ) from exc


@dataclass(frozen=True, slots=True, init=False)
class MontageLearningDurableStagingReadback:
    project_id: str
    store_id: str
    store_revision: int
    ledger_sha256: str
    staging_file_identity_sha256: str
    platform_security_model: str
    source_record_id: str
    source_sha256: str
    owner_scope_hash: str
    proposal_sha256: str
    approved_plan_sha256: str
    idempotency_key_sha256: str
    staging_entry_sha256: str
    canonical_evidence_id: str
    canonical_evidence_sha256: str
    human_binding_sha256: str
    negative_feedback_preserved: bool
    _token: object

    def __new__(cls) -> "MontageLearningDurableStagingReadback":
        raise TypeError(
            "durable staging read-back results are created only by verification"
        )

    @classmethod
    def _verified(
        cls,
        *,
        project_id: str,
        store_id: str,
        store_revision: int,
        ledger_sha256: str,
        staging_file_identity_sha256: str,
        platform_security_model: str,
        source_record_id: str,
        source_sha256: str,
        owner_scope_hash: str,
        proposal_sha256: str,
        approved_plan_sha256: str,
        idempotency_key_sha256: str,
        staging_entry_sha256: str,
        canonical_evidence_id: str,
        canonical_evidence_sha256: str,
        human_binding_sha256: str,
        negative_feedback_preserved: bool,
    ) -> "MontageLearningDurableStagingReadback":
        result = object.__new__(cls)
        values = locals()
        for name in cls.__dataclass_fields__:
            if name == "_token":
                object.__setattr__(result, name, _RUNTIME_TOKEN)
            else:
                object.__setattr__(result, name, values[name])
        return result

    @property
    def runtime_attested(self) -> bool:
        return self._token is _RUNTIME_TOKEN

    def to_dict(self) -> dict[str, object]:
        if not self.runtime_attested:
            raise MontageLearningDurableStagingReadbackError(
                "runtime attestation is absent"
            )
        body: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": RECORD_TYPE,
            "task_owner": TASK_OWNER,
            "source_contract_profile": EXACT_CONTRACT_PROFILE,
            "project_id": self.project_id,
            "store_id": self.store_id,
            "store_revision": self.store_revision,
            "ledger_sha256": self.ledger_sha256,
            "staging_file_identity_sha256": self.staging_file_identity_sha256,
            "platform_security_model": self.platform_security_model,
            "source_record_id": self.source_record_id,
            "source_sha256": self.source_sha256,
            "owner_scope_hash": self.owner_scope_hash,
            "proposal_sha256": self.proposal_sha256,
            "approved_plan_sha256": self.approved_plan_sha256,
            "idempotency_key_sha256": self.idempotency_key_sha256,
            "staging_entry_sha256": self.staging_entry_sha256,
            "canonical_evidence_id": self.canonical_evidence_id,
            "canonical_evidence_sha256": self.canonical_evidence_sha256,
            "human_binding_sha256": self.human_binding_sha256,
            "admission_state": NONAUTHORITATIVE_DURABLE_STAGING_READBACK_PROJECTION,
            "projection_structure_valid": True,
            "raw_delivery_recompiled": True,
            "handle_bound_file_read_verified": True,
            "staging_membership_verified": True,
            "staging_store_path_identity_verified": True,
            "staging_store_origin_verified": False,
            "project_root_canonical_ownership_verified": False,
            "source_lineage_origin_verified": False,
            "human_binding_origin_verified": False,
            "hostile_ancestor_namespace_race_protection_verified": False,
            "point_in_time_readback_only": True,
            "post_return_state_guaranteed": False,
            "do_not_learn": False,
            "negative_feedback_preserved": self.negative_feedback_preserved,
            "monotonic_project_anchor_verified": False,
            "rollback_detection_authority_created": False,
            "canonical_store_written": False,
            "canonical_store_commit_sha256": None,
            "receipt_minted": False,
            "canonical_admission_authority_created": False,
            "automatic_learning_promotion_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
            "external_effect_authorized": False,
        }
        body["readback_sha256"] = sha256_bytes(
            READBACK_DOMAIN + canonical_json_bytes(body)
        )
        return body


def verify_montage_learning_durable_staging_readback(
    delivery: Mapping[str, Any],
    *,
    project_root: str | Path,
    store_id: str,
    expected_owner_scope_hash: str,
    expected_revision: int,
    expected_staging_entry_sha256: str,
) -> MontageLearningDurableStagingReadback:
    """Recompile raw delivery against one entry read from a pinned P1B ledger."""

    snapshot = _snapshot_exact_json(delivery)
    store = _identifier(store_id, "store_id")
    scope = _digest(expected_owner_scope_hash, "expected_owner_scope_hash")
    revision = _revision(expected_revision)
    entry_sha = _digest(
        expected_staging_entry_sha256, "expected_staging_entry_sha256"
    )
    pinned = _read_pinned_ledger(Path(project_root))
    ledger = _parse_exact_ledger(pinned.raw)
    if (
        ledger.store_id != store
        or ledger.owner_scope_hash != scope
        or ledger.revision != revision
    ):
        raise MontageLearningDurableStagingReadbackError(
            "staging ledger coordinates do not match the expected read"
        )
    matches = [
        entry for entry in ledger.entries
        if entry.to_dict()["entry_sha256"] == entry_sha
    ]
    if len(matches) != 1:
        raise MontageLearningDurableStagingReadbackError(
            "expected staging entry is not an exact ledger member"
        )
    try:
        preflight = compile_montage_learning_canonical_preflight(
            snapshot,
            matches[0].to_dict(),
            expected_owner_scope_hash=scope,
        )
    except MontageLearningCanonicalPreflightError as exc:
        raise MontageLearningDurableStagingReadbackError(
            "raw delivery did not recompile against the staged member"
        ) from exc
    if preflight.staging_entry_sha256 != entry_sha:
        raise MontageLearningDurableStagingReadbackError(
            "recompiled entry digest mismatch"
        )
    ledger_sha = _digest(ledger.to_dict()["ledger_sha256"], "ledger_sha256")
    return MontageLearningDurableStagingReadback._verified(
        project_id=preflight.project_id,
        store_id=store,
        store_revision=revision,
        ledger_sha256=ledger_sha,
        staging_file_identity_sha256=pinned.file_identity_sha256,
        platform_security_model=pinned.platform_security_model,
        source_record_id=preflight.source_record_id,
        source_sha256=preflight.source_sha256,
        owner_scope_hash=preflight.owner_scope_hash,
        proposal_sha256=preflight.proposal_sha256,
        approved_plan_sha256=preflight.approved_plan_sha256,
        idempotency_key_sha256=preflight.idempotency_key_sha256,
        staging_entry_sha256=preflight.staging_entry_sha256,
        canonical_evidence_id=preflight.canonical_evidence_id,
        canonical_evidence_sha256=preflight.canonical_evidence_sha256,
        human_binding_sha256=preflight.human_binding_sha256,
        negative_feedback_preserved=preflight.negative_feedback_preserved,
    )


__all__ = [
    "FILE_IDENTITY_DOMAIN",
    "NONAUTHORITATIVE_DURABLE_STAGING_READBACK_PROJECTION",
    "READBACK_DOMAIN",
    "MontageLearningDurableStagingReadback",
    "MontageLearningDurableStagingReadbackError",
    "verify_montage_learning_durable_staging_readback",
]
