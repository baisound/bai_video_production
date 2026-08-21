"""Windows handle-locked read session for the exact TASK-014 Qwen-TTS wheel.

The public factory accepts no path.  It opens the fixed production hierarchy
top-down, retains every directory handle without delete sharing, opens the
wheel read-only without write/delete sharing, and reads from that same wheel
handle.  No persistent receipt can recreate or extend the session capability.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import PureWindowsPath
import re
from types import MappingProxyType
from typing import Any, Mapping

from .qwen_tts_pinned_wheel import (
    PinnedQwenTtsWheel,
    PinnedWheelError,
    parse_pinned_qwen_tts_011_wheel,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_ID = "bai.task014.qwen-tts-locked-wheel-session-observation.v1"
SCOPE = "HANDLE_LOCKED_PINNED_WHEEL_READ_SESSION_DIAGNOSTIC_ONLY"
_PRODUCTION_WHEEL_PATH = PureWindowsPath(r"E:\BAI_AI\downloads\TASK-014\qwen_tts-0.1.1-py3-none-any.whl")
_WHEEL_FILENAME = "qwen_tts-0.1.1-py3-none-any.whl"
_WHEEL_BYTES = 113_529
_WHEEL_SHA256 = "sha256:11a290d8dabc7ef91a90c54478c8ab19b3edb1d85c0882313721892bdc4af15d"
_TRUSTED_INVENTORY_SHA256 = "sha256:0a0568dfbbf716135c911322c22dc44df1e279dfd52ab25de9a4edb6a8a11dd6"
_RFC3339_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z$")
_SUCCESS = "LOCKED_SOURCE_VERIFIED_DIAGNOSTIC"
_BLOCKERS = frozenset({
    "UNSUPPORTED_PLATFORM", "NON_FIXED_LOCAL_DRIVE", "HANDLE_OPEN_DENIED",
    "REPARSE_POINT_REJECTED", "CANONICAL_PATH_MISMATCH", "FILE_ID_INVALID",
    "HANDLE_IDENTITY_CHANGED", "HANDLE_INHERITANCE_UNSAFE", "WHEEL_SIZE_MISMATCH",
    "WHEEL_READ_FAILED", "WHEEL_PIN_MISMATCH", "INVALID_WHEEL_ARCHIVE",
    "UNSAFE_ARCHIVE_PATH", "UNSAFE_ARCHIVE_MEMBER", "DUPLICATE_ARCHIVE_MEMBER",
    "ARCHIVE_BOUNDS_EXCEEDED", "ARCHIVE_MEMBER_SIZE_MISMATCH", "WHEEL_RECORD_MISSING",
    "WHEEL_RECORD_MEMBER_SET_MISMATCH", "WHEEL_RECORD_HASH_MISMATCH",
    "WHEEL_OBSERVED_COUNT_MISMATCH", "WHEEL_ENTRY_POINT_MISMATCH", "MALFORMED_RECORD",
    "DUPLICATE_RECORD_PATH", "TRUSTED_PAYLOAD_INVENTORY_MISMATCH", "HANDLE_CLOSE_FAILED",
})
_UNKNOWN = frozenset({"WIN32_IO_UNAVAILABLE"})

_GENERIC_READ = 0x80000000
_FILE_READ_ATTRIBUTES = 0x00000080
_FILE_SHARE_READ = 0x00000001
_FILE_SHARE_WRITE = 0x00000002
_OPEN_EXISTING = 3
_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_FILE_ATTRIBUTE_DIRECTORY = 0x00000010
_FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
_HANDLE_FLAG_INHERIT = 0x00000001
_DRIVE_FIXED = 3
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class _Win32Blocked(Exception):
    pass


class _Win32Unknown(Exception):
    pass


class _OpenedHandleSafetyFailure(Exception):
    """Carry a handle-open observation internally without rendering its value."""

    __slots__ = ("reason", "handle", "directory")

    def __init__(self, reason: str, handle: int | None, *, directory: bool) -> None:
        super().__init__(reason)
        self.reason = reason
        self.handle = handle
        self.directory = directory

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class _HandleIdentity:
    canonical_path: str
    volume_serial: int
    file_id: bytes
    directory: bool


class _FILE_ATTRIBUTE_TAG_INFO(ctypes.Structure):
    _fields_ = [("FileAttributes", wintypes.DWORD), ("ReparseTag", wintypes.DWORD)]


class _FILE_ID_INFO(ctypes.Structure):
    _fields_ = [("VolumeSerialNumber", ctypes.c_ulonglong), ("FileId", ctypes.c_ubyte * 16)]


class _SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("nLength", wintypes.DWORD), ("lpSecurityDescriptor", ctypes.c_void_p), ("bInheritHandle", wintypes.BOOL)]


def _timestamp(value: str) -> str:
    if not isinstance(value, str) or not _RFC3339_UTC.fullmatch(value):
        raise ValueError("evaluated_at must be RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("evaluated_at must be RFC3339 UTC") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("evaluated_at must be UTC")
    return value


def _production_chain() -> tuple[str, tuple[str, ...], str]:
    wheel = _PRODUCTION_WHEEL_PATH
    if wheel.name != _WHEEL_FILENAME or wheel.drive.upper() != "E:":
        raise _Win32Blocked("CANONICAL_PATH_MISMATCH")
    directories = (wheel.anchor, str(wheel.parents[2]), str(wheel.parents[1]), str(wheel.parent))
    expected = ("E:\\", "E:\\BAI_AI", "E:\\BAI_AI\\downloads", "E:\\BAI_AI\\downloads\\TASK-014")
    if tuple(item.casefold() for item in directories) != tuple(item.casefold() for item in expected):
        raise _Win32Blocked("CANONICAL_PATH_MISMATCH")
    return wheel.anchor, directories, str(wheel)


def _canonicalize_handle_path(value: str) -> str:
    if value.startswith("\\\\?\\UNC\\"):
        raise _Win32Blocked("CANONICAL_PATH_MISMATCH")
    if value.startswith("\\\\?\\"):
        value = value[4:]
    return str(PureWindowsPath(value))


class _CtypesWin32Port:
    """Private Win32 port. Tests replace its private factory, never public API."""

    def __init__(self) -> None:
        if os.name != "nt":
            raise _Win32Blocked("UNSUPPORTED_PLATFORM")
        self._kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
        self._kernel.GetDriveTypeW.restype = wintypes.UINT
        self._kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(_SECURITY_ATTRIBUTES), wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        self._kernel.CreateFileW.restype = wintypes.HANDLE
        self._kernel.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
        self._kernel.SetHandleInformation.restype = wintypes.BOOL
        self._kernel.GetHandleInformation.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        self._kernel.GetHandleInformation.restype = wintypes.BOOL
        self._kernel.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self._kernel.GetFileInformationByHandleEx.restype = wintypes.BOOL
        self._kernel.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
        self._kernel.GetFinalPathNameByHandleW.restype = wintypes.DWORD
        self._kernel.GetFileSizeEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_longlong)]
        self._kernel.GetFileSizeEx.restype = wintypes.BOOL
        self._kernel.SetFilePointerEx.argtypes = [wintypes.HANDLE, ctypes.c_longlong, ctypes.POINTER(ctypes.c_longlong), wintypes.DWORD]
        self._kernel.SetFilePointerEx.restype = wintypes.BOOL
        self._kernel.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        self._kernel.ReadFile.restype = wintypes.BOOL
        self._kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel.CloseHandle.restype = wintypes.BOOL

    def drive_type(self, root: str) -> int:
        return int(self._kernel.GetDriveTypeW(root))

    def _open(self, path: str, access: int, share: int, flags: int, *, directory: bool) -> int:
        security = _SECURITY_ATTRIBUTES(ctypes.sizeof(_SECURITY_ATTRIBUTES), None, False)
        handle = self._kernel.CreateFileW(path, access, share, ctypes.byref(security), _OPEN_EXISTING, flags, None)
        if handle in (None, 0, _INVALID_HANDLE_VALUE):
            raise _Win32Blocked("HANDLE_OPEN_DENIED")
        if not self._kernel.SetHandleInformation(handle, _HANDLE_FLAG_INHERIT, 0):
            self._close_or_handoff(handle, "HANDLE_INHERITANCE_UNSAFE", directory=directory)
        flags_value = wintypes.DWORD()
        if not self._kernel.GetHandleInformation(handle, ctypes.byref(flags_value)) or flags_value.value & _HANDLE_FLAG_INHERIT:
            self._close_or_handoff(handle, "HANDLE_INHERITANCE_UNSAFE", directory=directory)
        return int(handle)

    def _close_or_handoff(self, handle: int, reason: str, *, directory: bool) -> None:
        retained = None if self._kernel.CloseHandle(handle) else int(handle)
        raise _OpenedHandleSafetyFailure(reason, retained, directory=directory)

    def open_directory(self, path: str) -> int:
        return self._open(path, _FILE_READ_ATTRIBUTES, _FILE_SHARE_READ | _FILE_SHARE_WRITE, _FILE_FLAG_BACKUP_SEMANTICS | _FILE_FLAG_OPEN_REPARSE_POINT, directory=True)

    def open_wheel(self, path: str) -> int:
        return self._open(path, _GENERIC_READ, _FILE_SHARE_READ, _FILE_FLAG_OPEN_REPARSE_POINT, directory=False)

    def identity(self, handle: int, expected_path: str, *, directory: bool) -> _HandleIdentity:
        tag = _FILE_ATTRIBUTE_TAG_INFO()
        if not self._kernel.GetFileInformationByHandleEx(handle, 9, ctypes.byref(tag), ctypes.sizeof(tag)):
            raise _Win32Unknown("WIN32_IO_UNAVAILABLE")
        if tag.FileAttributes & _FILE_ATTRIBUTE_REPARSE_POINT:
            raise _Win32Blocked("REPARSE_POINT_REJECTED")
        if bool(tag.FileAttributes & _FILE_ATTRIBUTE_DIRECTORY) is not directory:
            raise _Win32Blocked("CANONICAL_PATH_MISMATCH")
        capacity = 32768
        buffer = ctypes.create_unicode_buffer(capacity)
        length = self._kernel.GetFinalPathNameByHandleW(handle, buffer, capacity, 0)
        if length == 0 or length >= capacity:
            raise _Win32Unknown("WIN32_IO_UNAVAILABLE")
        canonical = _canonicalize_handle_path(buffer.value)
        if canonical.casefold() != str(PureWindowsPath(expected_path)).casefold():
            raise _Win32Blocked("CANONICAL_PATH_MISMATCH")
        info = _FILE_ID_INFO()
        if not self._kernel.GetFileInformationByHandleEx(handle, 18, ctypes.byref(info), ctypes.sizeof(info)):
            raise _Win32Unknown("WIN32_IO_UNAVAILABLE")
        file_id = bytes(info.FileId)
        if not any(file_id):
            raise _Win32Blocked("FILE_ID_INVALID")
        return _HandleIdentity(canonical, int(info.VolumeSerialNumber), file_id, directory)

    def read_exact(self, handle: int, byte_count: int) -> bytes:
        size = ctypes.c_longlong()
        if not self._kernel.GetFileSizeEx(handle, ctypes.byref(size)):
            raise _Win32Unknown("WIN32_IO_UNAVAILABLE")
        if size.value != byte_count:
            raise _Win32Blocked("WHEEL_SIZE_MISMATCH")
        origin = ctypes.c_longlong(0)
        if not self._kernel.SetFilePointerEx(handle, origin, None, 0):
            raise _Win32Unknown("WIN32_IO_UNAVAILABLE")
        buffer = ctypes.create_string_buffer(byte_count + 1)
        read = wintypes.DWORD()
        if not self._kernel.ReadFile(handle, buffer, byte_count + 1, ctypes.byref(read), None):
            raise _Win32Blocked("WHEEL_READ_FAILED")
        if read.value != byte_count:
            raise _Win32Blocked("WHEEL_READ_FAILED")
        return bytes(buffer.raw[:byte_count])

    def close(self, handle: int) -> bool:
        return bool(self._kernel.CloseHandle(handle))


_WIN32_PORT_FACTORY = _CtypesWin32Port


def _digest(value: Mapping[str, Any], field: str) -> str:
    return sha256_bytes(canonical_json_bytes({key: item for key, item in value.items() if key != field}))


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


def _private_body(
    *, evaluated_at: str, decision: str, reasons: tuple[str, ...],
    directory_handles_opened: int = 0, wheel_handle_opened: bool = False,
    wheel_bytes_read: int = 0, pinned_payload_files: int = 0,
    source_fully_verified: bool = False, unreleased_handle_count: int = 0,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA_ID, "scope": SCOPE, "package_name": "qwen-tts", "package_version": "0.1.1",
        "wheel_filename": _WHEEL_FILENAME, "wheel_bytes": _WHEEL_BYTES, "wheel_sha256": _WHEEL_SHA256,
        "trusted_payload_inventory_sha256": _TRUSTED_INVENTORY_SHA256 if pinned_payload_files == 23 else None,
        "evaluated_at": evaluated_at, "decision": decision, "reason_codes": list(reasons),
        "directory_handles_opened": directory_handles_opened, "wheel_handle_opened": wheel_handle_opened,
        "wheel_bytes_read": wheel_bytes_read, "pinned_payload_files": pinned_payload_files,
        "canonical_paths_verified": source_fully_verified, "non_reparse_verified": source_fully_verified,
        "file_ids_retained_in_session_only": source_fully_verified, "handles_non_inheritable": source_fully_verified,
        "handle_release_confirmed": unreleased_handle_count == 0,
        "unreleased_handle_count": unreleased_handle_count,
        "persistent_receipt_is_capability": False, "runtime_reuse_authorized": False,
        "post_return_state_guaranteed": False, "consumer_execution_authorized": False,
        "dependency_resolved_or_installed": False, "target_python_executed": False,
        "target_package_imported": False, "model_loaded": False, "owner_audio_read": False,
        "inference_executed": False, "network_accessed": False, "subprocess_started": False,
        "archive_extracted": False, "filesystem_modified": False, "absolute_path_persisted": False,
    }


def _validate(value: Mapping[str, Any]) -> dict[str, Any]:
    sample = _private_body(evaluated_at="2026-08-21T00:00:00Z", decision="UNKNOWN", reasons=("WIN32_IO_UNAVAILABLE",))
    if not isinstance(value, Mapping) or set(value) != set(sample) | {"receipt_sha256"}:
        raise ValueError("receipt fields are incomplete or unknown")
    copy = dict(value)
    if (copy["schema"], copy["scope"], copy["package_name"], copy["package_version"]) != (SCHEMA_ID, SCOPE, "qwen-tts", "0.1.1"):
        raise ValueError("receipt identity mismatch")
    if (copy["wheel_filename"], copy["wheel_bytes"], copy["wheel_sha256"]) != (_WHEEL_FILENAME, _WHEEL_BYTES, _WHEEL_SHA256):
        raise ValueError("wheel pin mismatch")
    _timestamp(copy["evaluated_at"])
    validate_sha256(copy["wheel_sha256"], field_name="wheel_sha256")
    validate_sha256(copy["receipt_sha256"], field_name="receipt_sha256")
    if copy["trusted_payload_inventory_sha256"] is not None:
        validate_sha256(copy["trusted_payload_inventory_sha256"], field_name="trusted_payload_inventory_sha256")
    if copy["decision"] not in {_SUCCESS, "BLOCKED", "UNKNOWN"} or not isinstance(copy["reason_codes"], list) or any(not isinstance(item, str) for item in copy["reason_codes"]):
        raise ValueError("decision or reasons invalid")
    if len(copy["reason_codes"]) != len(set(copy["reason_codes"])):
        raise ValueError("decision or reasons invalid")
    if copy["decision"] == _SUCCESS and copy["reason_codes"]:
        raise ValueError("success requires no reason")
    if copy["decision"] == "BLOCKED" and (len(copy["reason_codes"]) != 1 or copy["reason_codes"][0] not in _BLOCKERS):
        raise ValueError("blocked reason invalid")
    if copy["decision"] == "UNKNOWN" and (len(copy["reason_codes"]) != 1 or copy["reason_codes"][0] not in _UNKNOWN):
        raise ValueError("unknown reason invalid")
    false_fields = (
        "persistent_receipt_is_capability", "runtime_reuse_authorized", "post_return_state_guaranteed",
        "consumer_execution_authorized", "dependency_resolved_or_installed", "target_python_executed",
        "target_package_imported", "model_loaded", "owner_audio_read", "inference_executed",
        "network_accessed", "subprocess_started", "archive_extracted", "filesystem_modified",
        "absolute_path_persisted",
    )
    if any(copy[field] is not False for field in false_fields):
        raise ValueError("receipt authority/effect invariant failed")
    truth_fields = ("wheel_handle_opened", "canonical_paths_verified", "non_reparse_verified", "file_ids_retained_in_session_only", "handles_non_inheritable", "handle_release_confirmed")
    if any(not isinstance(copy[field], bool) for field in truth_fields):
        raise ValueError("receipt verification flag invalid")
    for field in ("directory_handles_opened", "wheel_bytes_read", "pinned_payload_files", "unreleased_handle_count"):
        if not isinstance(copy[field], int) or isinstance(copy[field], bool):
            raise ValueError("receipt count invalid")
    if not 0 <= copy["unreleased_handle_count"] <= 5 or copy["handle_release_confirmed"] is not (copy["unreleased_handle_count"] == 0):
        raise ValueError("handle release observation invalid")
    if copy["unreleased_handle_count"] > copy["directory_handles_opened"] + int(copy["wheel_handle_opened"]):
        raise ValueError("unreleased handle count exceeds opened handles")
    if not 0 <= copy["directory_handles_opened"] <= 4 or copy["wheel_bytes_read"] not in {0, _WHEEL_BYTES} or copy["pinned_payload_files"] not in {0, 23}:
        raise ValueError("receipt observation count invalid")
    if not copy["wheel_handle_opened"] and (copy["wheel_bytes_read"] or copy["pinned_payload_files"]):
        raise ValueError("wheel observations require an opened handle")
    if copy["pinned_payload_files"] == 23:
        if copy["wheel_bytes_read"] != _WHEEL_BYTES or copy["trusted_payload_inventory_sha256"] != _TRUSTED_INVENTORY_SHA256:
            raise ValueError("payload observation invariant failed")
    elif copy["trusted_payload_inventory_sha256"] is not None:
        raise ValueError("unverified payload cannot carry inventory digest")
    source_truth_fields = ("canonical_paths_verified", "non_reparse_verified", "file_ids_retained_in_session_only", "handles_non_inheritable")
    if any(copy[field] for field in source_truth_fields) and not all(copy[field] for field in source_truth_fields):
        raise ValueError("source verification flags must move together")
    if all(copy[field] for field in source_truth_fields) and (copy["directory_handles_opened"], copy["wheel_handle_opened"], copy["wheel_bytes_read"], copy["pinned_payload_files"]) != (4, True, _WHEEL_BYTES, 23):
        raise ValueError("source verification requires complete observations")
    if copy["decision"] == _SUCCESS:
        if copy["directory_handles_opened"] != 4 or copy["wheel_bytes_read"] != _WHEEL_BYTES or copy["pinned_payload_files"] != 23 or copy["trusted_payload_inventory_sha256"] != _TRUSTED_INVENTORY_SHA256 or not all(copy[field] for field in source_truth_fields) or copy["unreleased_handle_count"] not in {0, 5}:
            raise ValueError("success invariants failed")
    if copy["receipt_sha256"] != _digest(copy, "receipt_sha256"):
        raise ValueError("receipt_sha256 mismatch")
    return copy


@dataclass(frozen=True, slots=True)
class LockedWheelSessionReceipt:
    _value: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "_value", _freeze(_validate(self._value)))

    def to_private_dict(self) -> dict[str, Any]:
        return _thaw(self._value)

    def to_public_dict(self) -> dict[str, Any]:
        return {key: item for key, item in self.to_private_dict().items() if key not in {"trusted_payload_inventory_sha256", "receipt_sha256"}}


def parse_locked_wheel_session_receipt(mapping: Mapping[str, Any]) -> LockedWheelSessionReceipt:
    return LockedWheelSessionReceipt(dict(mapping))


class LockedQwenTtsWheelSession:
    """Non-serializable capability valid only between context enter and exit."""

    __slots__ = (
        "_evaluated_at", "_port", "_handles", "_identities", "_active", "_entered", "_receipt",
        "_directory_handles_opened", "_wheel_handle_opened", "_wheel_bytes_read",
        "_pinned_payload_files", "_source_fully_verified",
    )

    def __init__(self, evaluated_at: str) -> None:
        self._evaluated_at = _timestamp(evaluated_at)
        self._port: Any = None
        self._handles: list[int] = []
        self._identities: tuple[_HandleIdentity, ...] = ()
        self._active = False
        self._entered = False
        self._receipt: LockedWheelSessionReceipt | None = None
        self._directory_handles_opened = 0
        self._wheel_handle_opened = False
        self._wheel_bytes_read = 0
        self._pinned_payload_files = 0
        self._source_fully_verified = False

    def __reduce__(self) -> Any:
        raise TypeError("locked wheel session capability is not serializable")

    def __reduce_ex__(self, protocol: int) -> Any:
        raise TypeError("locked wheel session capability is not serializable")

    def __getstate__(self) -> Any:
        raise TypeError("locked wheel session capability is not serializable")

    @property
    def receipt(self) -> LockedWheelSessionReceipt:
        if self._receipt is None:
            raise RuntimeError("session has not been entered")
        return self._receipt

    @property
    def active(self) -> bool:
        return self._active

    def _set_receipt(self, decision: str, reasons: tuple[str, ...]) -> None:
        body = _private_body(
            evaluated_at=self._evaluated_at, decision=decision, reasons=reasons,
            directory_handles_opened=self._directory_handles_opened,
            wheel_handle_opened=self._wheel_handle_opened,
            wheel_bytes_read=self._wheel_bytes_read,
            pinned_payload_files=self._pinned_payload_files,
            source_fully_verified=self._source_fully_verified,
            unreleased_handle_count=len(self._handles),
        )
        body["receipt_sha256"] = _digest(body, "receipt_sha256")
        self._receipt = LockedWheelSessionReceipt(body)

    def _close_reverse(self) -> bool:
        ok = True
        pending = list(reversed(self._handles))
        self._handles.clear()
        failed: list[int] = []
        for handle in pending:
            try:
                if not self._port.close(handle):
                    failed.append(handle); ok = False
            except Exception:
                failed.append(handle); ok = False
        # Preserve still-unclosed handles in an order that produces the same
        # reverse retry order on the next cleanup attempt.
        self._handles.extend(reversed(failed))
        self._active = False
        self._identities = ()
        return ok

    def __enter__(self) -> "LockedQwenTtsWheelSession":
        if self._entered:
            raise RuntimeError("locked wheel session is one-shot")
        self._entered = True
        try:
            self._port = _WIN32_PORT_FACTORY()
            root, directories, wheel_path = _production_chain()
            if self._port.drive_type(root) != _DRIVE_FIXED:
                raise _Win32Blocked("NON_FIXED_LOCAL_DRIVE")
            identities: list[_HandleIdentity] = []
            for path in directories:
                handle = self._port.open_directory(path)
                self._handles.append(handle)
                self._directory_handles_opened += 1
                identities.append(self._port.identity(handle, path, directory=True))
            wheel_handle = self._port.open_wheel(wheel_path)
            self._handles.append(wheel_handle)
            self._wheel_handle_opened = True
            wheel_identity = self._port.identity(wheel_handle, wheel_path, directory=False)
            raw = self._port.read_exact(wheel_handle, _WHEEL_BYTES)
            self._wheel_bytes_read = _WHEEL_BYTES
            parse_pinned_qwen_tts_011_wheel(raw)
            self._pinned_payload_files = 23
            if self._port.identity(wheel_handle, wheel_path, directory=False) != wheel_identity:
                raise _Win32Blocked("HANDLE_IDENTITY_CHANGED")
            for handle, path, expected_identity in zip(self._handles[:-1], directories, identities, strict=True):
                if self._port.identity(handle, path, directory=True) != expected_identity:
                    raise _Win32Blocked("HANDLE_IDENTITY_CHANGED")
            identities.append(wheel_identity)
            self._identities = tuple(identities)
            self._source_fully_verified = True
            self._active = True
            self._set_receipt(_SUCCESS, ())
        except _OpenedHandleSafetyFailure as exc:
            # Count the actual open even when safety readback failed. If the
            # immediate close failed, retain the opaque value for retry.
            if exc.directory:
                self._directory_handles_opened += 1
            else:
                self._wheel_handle_opened = True
            if exc.handle is not None:
                self._handles.append(exc.handle)
            close_ok = self._close_reverse()
            self._set_receipt("BLOCKED", (exc.reason if close_ok else "HANDLE_CLOSE_FAILED",))
        except PinnedWheelError as exc:
            close_ok = self._close_reverse()
            self._set_receipt("BLOCKED", ((str(exc) if str(exc) in _BLOCKERS else "INVALID_WHEEL_ARCHIVE") if close_ok else "HANDLE_CLOSE_FAILED",))
        except _Win32Blocked as exc:
            close_ok = self._close_reverse()
            self._set_receipt("BLOCKED", (str(exc) if close_ok else "HANDLE_CLOSE_FAILED",))
        except _Win32Unknown as exc:
            close_ok = self._close_reverse()
            if close_ok:
                self._set_receipt("UNKNOWN", (str(exc),))
            else:
                self._set_receipt("BLOCKED", ("HANDLE_CLOSE_FAILED",))
        except Exception:
            close_ok = self._close_reverse()
            if close_ok:
                self._set_receipt("UNKNOWN", ("WIN32_IO_UNAVAILABLE",))
            else:
                self._set_receipt("BLOCKED", ("HANDLE_CLOSE_FAILED",))
        except BaseException:
            self._close_reverse()
            raise
        return self

    def read_verified_wheel(self) -> PinnedQwenTtsWheel:
        """Re-read and parse through the still-held wheel handle."""
        if not self._active or len(self._handles) != 5 or len(self._identities) != 5:
            raise RuntimeError("locked wheel session capability is inactive")
        wheel_handle = self._handles[-1]
        root, directories, wheel_path = _production_chain()
        del root
        try:
            raw = self._port.read_exact(wheel_handle, _WHEEL_BYTES)
            parsed = parse_pinned_qwen_tts_011_wheel(raw)
            current = self._port.identity(wheel_handle, wheel_path, directory=False)
            if current != self._identities[-1]:
                raise _Win32Blocked("HANDLE_IDENTITY_CHANGED")
            for handle, path, expected in zip(self._handles[:-1], directories, self._identities[:-1], strict=True):
                if self._port.identity(handle, path, directory=True) != expected:
                    raise _Win32Blocked("HANDLE_IDENTITY_CHANGED")
        except PinnedWheelError as exc:
            self._active = False
            close_ok = self._close_reverse()
            self._set_receipt("BLOCKED", ((str(exc) if str(exc) in _BLOCKERS else "INVALID_WHEEL_ARCHIVE") if close_ok else "HANDLE_CLOSE_FAILED",))
            raise RuntimeError("locked wheel revalidation blocked") from None
        except _Win32Blocked as exc:
            self._active = False
            close_ok = self._close_reverse()
            self._set_receipt("BLOCKED", (str(exc) if close_ok else "HANDLE_CLOSE_FAILED",))
            raise RuntimeError("locked wheel revalidation blocked") from None
        except (_Win32Unknown, Exception):
            self._active = False
            close_ok = self._close_reverse()
            if close_ok:
                self._set_receipt("UNKNOWN", ("WIN32_IO_UNAVAILABLE",))
            else:
                self._set_receipt("BLOCKED", ("HANDLE_CLOSE_FAILED",))
            raise RuntimeError("locked wheel revalidation unavailable") from None
        return parsed

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        self._active = False
        prior = self.receipt.to_private_dict()
        if not self._close_reverse():
            # A false/exceptional close retains the opaque handle internally;
            # make one bounded retry before leaving the context.
            self._close_reverse()
            self._set_receipt("BLOCKED", ("HANDLE_CLOSE_FAILED",))
        else:
            self._set_receipt(str(prior["decision"]), tuple(prior["reason_codes"]))
        return False


def open_locked_qwen_tts_wheel_session(evaluated_at: str) -> LockedQwenTtsWheelSession:
    """Return a one-shot fixed-path context manager; callers cannot supply a path."""
    return LockedQwenTtsWheelSession(evaluated_at)
