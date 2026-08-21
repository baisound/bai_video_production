"""Private Windows native port for TASK-041 R1B immutable ledger storage.

Only the fixed volume root is opened by pathname.  Every child directory and
file is opened relative to a retained parent handle with NtCreateFile.  The
module deliberately offers no public path-taking API and no path-based
enumeration fallback.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os
from pathlib import PureWindowsPath
from typing import Iterator


PRODUCTION_LEDGER_ROOT = PureWindowsPath(
    r"C:\ProgramData\BAISOUND\BAI Video Production\audio-completion-ledgers"
)
MAX_TRACKED_HANDLES = 32

# Win32/NT masks are kept here so the production and fake-port tests share the
# exact access contract.
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
DELETE = 0x00010000
READ_CONTROL = 0x00020000
FILE_LIST_DIRECTORY = 0x00000001
FILE_READ_DATA = 0x00000001
FILE_WRITE_DATA = 0x00000002
FILE_READ_ATTRIBUTES = 0x00000080
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_SHARE_DELETE = 0x00000004
OPEN_EXISTING = 3
CREATE_NEW = 1
FILE_FLAG_WRITE_THROUGH = 0x80000000
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
LOCKFILE_FAIL_IMMEDIATELY = 0x00000001
LOCKFILE_EXCLUSIVE_LOCK = 0x00000002
FILE_RENAME_INFO_EX_CLASS = 22
FILE_RENAME_FLAGS_NONE = 0
ERROR_LOCK_VIOLATION = 33
ERROR_FILE_NOT_FOUND = 2
ERROR_NO_MORE_FILES = 18

DIRECTORY_ACCESS = FILE_LIST_DIRECTORY | FILE_READ_ATTRIBUTES | READ_CONTROL
DIRECTORY_SHARE = FILE_SHARE_READ | FILE_SHARE_WRITE
DIRECTORY_FLAGS = FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT
LOCK_ACCESS = GENERIC_READ | GENERIC_WRITE | FILE_READ_ATTRIBUTES | READ_CONTROL
LOCK_SHARE = FILE_SHARE_READ | FILE_SHARE_WRITE
LOCK_FLAGS = FILE_FLAG_OPEN_REPARSE_POINT
PENDING_ACCESS = GENERIC_READ | GENERIC_WRITE | DELETE | FILE_READ_ATTRIBUTES | READ_CONTROL
PENDING_SHARE = FILE_SHARE_READ
PENDING_FLAGS = FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_WRITE_THROUGH
FINAL_ACCESS = GENERIC_READ | FILE_READ_ATTRIBUTES | READ_CONTROL
FINAL_SHARE = FILE_SHARE_READ
FINAL_FLAGS = FILE_FLAG_OPEN_REPARSE_POINT

_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
_OBJ_CASE_INSENSITIVE = 0x00000040
_FILE_OPEN = 0x00000001
_FILE_CREATE = 0x00000002
_FILE_DIRECTORY_FILE = 0x00000001
_FILE_NON_DIRECTORY_FILE = 0x00000040
_FILE_OPEN_REPARSE_POINT = 0x00200000
_FILE_WRITE_THROUGH = 0x00000002
_FILE_SYNCHRONOUS_IO_NONALERT = 0x00000020
_SYNCHRONIZE = 0x00100000
_FILE_ATTRIBUTE_NORMAL = 0x00000080
_FILE_ATTRIBUTE_DIRECTORY = 0x00000010
_FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
_HANDLE_FLAG_INHERIT = 0x00000001
_DRIVE_FIXED = 3
_FILE_ID_EXTD_DIRECTORY_INFORMATION = 60
_STATUS_NO_MORE_FILES = ctypes.c_int32(0x80000006).value
_STATUS_NO_SUCH_FILE = ctypes.c_int32(0xC000000F).value
_STATUS_OBJECT_NAME_NOT_FOUND = ctypes.c_int32(0xC0000034).value
_STATUS_OBJECT_NAME_COLLISION = ctypes.c_int32(0xC0000035).value
_OWNER_SECURITY_INFORMATION = 0x00000001
_DACL_SECURITY_INFORMATION = 0x00000004
_SE_FILE_OBJECT = 1
_SE_DACL_PROTECTED = 0x1000
_TOKEN_QUERY = 0x0008
_TOKEN_USER = 1
_TOKEN_ELEVATION = 20
_ACL_SIZE_INFORMATION = 2
_ACCESS_ALLOWED_ACE_TYPE = 0
_ACCESS_DENIED_ACE_TYPE = 1
_INHERITED_ACE = 0x10
_WRITE_DAC = 0x00040000
_WRITE_OWNER = 0x00080000
_FILE_APPEND_DATA = 0x00000004
_FILE_WRITE_EA = 0x00000010
_FILE_WRITE_ATTRIBUTES = 0x00000100
_FILE_DELETE_CHILD = 0x00000040
_GENERIC_ALL = 0x10000000
_DANGEROUS_ACCESS = (_GENERIC_ALL | GENERIC_WRITE | DELETE | _WRITE_DAC | _WRITE_OWNER |
    FILE_WRITE_DATA | _FILE_APPEND_DATA | _FILE_WRITE_EA |
    _FILE_WRITE_ATTRIBUTES | _FILE_DELETE_CHILD)
_PRIVATE_ACCESS = (_DANGEROUS_ACCESS | GENERIC_READ | READ_CONTROL |
    FILE_READ_DATA | FILE_READ_ATTRIBUTES | 0x00000008 | 0x00000020)
_DOS_DEVICE_NAMES = frozenset({"CON", "PRN", "AUX", "NUL"} |
    {f"COM{index}" for index in range(1, 10)} |
    {f"LPT{index}" for index in range(1, 10)})


def _last_error() -> int:
    getter = getattr(ctypes, "get_last_error", None)
    return int(getter()) if callable(getter) else 0


class NativePortError(RuntimeError):
    """Expected native failure with a public-safe reason code."""

    __slots__ = ("reason", "completion_unknown", "unreleased_handle_count",
                 "unreleased_native_allocation_count")

    def __init__(self, reason: str, *, completion_unknown: bool = False,
                 unreleased_handle_count: int = 0,
                 unreleased_native_allocation_count: int = 0) -> None:
        super().__init__(reason)
        self.reason = reason
        self.completion_unknown = completion_unknown
        self.unreleased_handle_count = min(
            max(int(unreleased_handle_count), 0), MAX_TRACKED_HANDLES)
        self.unreleased_native_allocation_count = min(
            max(int(unreleased_native_allocation_count), 0), 64)


@dataclass(frozen=True, slots=True)
class HandleIdentity:
    volume_serial: int
    file_id: bytes
    final_path: str
    attributes: int
    link_count: int
    size: int
    security_digest_material: bytes


@dataclass(frozen=True, slots=True)
class DirectoryEntry:
    name: str
    file_id: bytes
    attributes: int
    size: int


# Windows ABI scalar widths are explicit so fake-port validation on a non-
# Windows host cannot silently inherit that host's C ``long`` width.
_U16 = ctypes.c_uint16
_U32 = ctypes.c_uint32
_S32 = ctypes.c_int32
_U64 = ctypes.c_uint64


class _UNICODE_STRING(ctypes.Structure):
    _fields_ = [
        ("Length", _U16),
        ("MaximumLength", _U16),
        ("Buffer", wintypes.LPWSTR),
    ]


class _OBJECT_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Length", _U32),
        ("RootDirectory", wintypes.HANDLE),
        ("ObjectName", ctypes.POINTER(_UNICODE_STRING)),
        ("Attributes", _U32),
        ("SecurityDescriptor", ctypes.c_void_p),
        ("SecurityQualityOfService", ctypes.c_void_p),
    ]


class _IO_STATUS_BLOCK_UNION(ctypes.Union):
    _fields_ = [("Status", _S32), ("Pointer", ctypes.c_void_p)]


class _IO_STATUS_BLOCK(ctypes.Structure):
    _fields_ = [("u", _IO_STATUS_BLOCK_UNION), ("Information", ctypes.c_size_t)]


class _SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("nLength", _U32),
        ("lpSecurityDescriptor", ctypes.c_void_p),
        ("bInheritHandle", _S32),
    ]


class _OVERLAPPED_UNION_STRUCT(ctypes.Structure):
    _fields_ = [("Offset", _U32), ("OffsetHigh", _U32)]


class _OVERLAPPED_UNION(ctypes.Union):
    _fields_ = [("s", _OVERLAPPED_UNION_STRUCT), ("Pointer", ctypes.c_void_p)]


class _OVERLAPPED(ctypes.Structure):
    _fields_ = [
        ("Internal", ctypes.c_size_t),
        ("InternalHigh", ctypes.c_size_t),
        ("u", _OVERLAPPED_UNION),
        ("hEvent", wintypes.HANDLE),
    ]


class _FILE_ATTRIBUTE_TAG_INFO(ctypes.Structure):
    _fields_ = [("FileAttributes", _U32), ("ReparseTag", _U32)]


class _FILE_ID_INFO(ctypes.Structure):
    _fields_ = [("VolumeSerialNumber", _U64), ("FileId", ctypes.c_ubyte * 16)]


class _BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("dwFileAttributes", _U32),
        ("ftCreationTimeLow", _U32), ("ftCreationTimeHigh", _U32),
        ("ftLastAccessTimeLow", _U32), ("ftLastAccessTimeHigh", _U32),
        ("ftLastWriteTimeLow", _U32), ("ftLastWriteTimeHigh", _U32),
        ("dwVolumeSerialNumber", _U32), ("nFileSizeHigh", _U32),
        ("nFileSizeLow", _U32), ("nNumberOfLinks", _U32),
        ("nFileIndexHigh", _U32), ("nFileIndexLow", _U32),
    ]


class _FILE_RENAME_INFO_EX_HEAD(ctypes.Structure):
    _fields_ = [
        ("Flags", _U32),
        ("RootDirectory", wintypes.HANDLE),
        ("FileNameLength", _U32),
    ]


class _ACL_SIZE_INFORMATION_STRUCT(ctypes.Structure):
    _fields_ = [("AceCount", _U32), ("AclBytesInUse", _U32),
                ("AclBytesFree", _U32)]


class _ACE_HEADER(ctypes.Structure):
    _fields_ = [("AceType", ctypes.c_ubyte), ("AceFlags", ctypes.c_ubyte),
                ("AceSize", _U16)]


class _TOKEN_USER_STRUCT(ctypes.Structure):
    _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", _U32)]


def _safe_component(name: str) -> str:
    if not isinstance(name, str) or not name or name in {".", ".."}:
        raise NativePortError("UNSAFE_RELATIVE_NAME")
    try:
        encoded = name.encode("ascii")
    except UnicodeEncodeError as exc:
        raise NativePortError("UNSAFE_RELATIVE_NAME") from exc
    stem = name.split(".", 1)[0].upper()
    if (len(encoded) > 255 or any(char in name for char in "\\/:*?\"<>|") or
            any(ord(char) < 32 or ord(char) == 127 for char in name) or
            name[-1] in {" ", "."} or stem in _DOS_DEVICE_NAMES):
        raise NativePortError("UNSAFE_RELATIVE_NAME")
    return name


def _validate_ace_policy(*, role: str, ace_type: int, ace_flags: int, mask: int,
                         sid_is_allowed: bool, allow_seen: bool) -> bool:
    """Pure DACL policy seam; returns the updated canonical-order allow flag."""
    if role not in {"private_root", "private_child"}:
        raise NativePortError("INVALID_SECURITY_ROLE")
    if ace_type not in {_ACCESS_ALLOWED_ACE_TYPE, _ACCESS_DENIED_ACE_TYPE}:
        raise NativePortError("DACL_UNSUPPORTED_ACE")
    if role == "private_root" and ace_flags & _INHERITED_ACE:
        raise NativePortError("DACL_NONCANONICAL_ACE")
    if ace_type == _ACCESS_DENIED_ACE_TYPE and allow_seen:
        raise NativePortError("DACL_NONCANONICAL_ORDER")
    if mask & _PRIVATE_ACCESS and not sid_is_allowed:
        raise NativePortError("DACL_PRIVACY_POLICY_FAILED")
    return allow_seen or ace_type == _ACCESS_ALLOWED_ACE_TYPE


class CtypesWindowsLedgerPort:
    """ctypes backend. Construction has no filesystem effect."""

    def __init__(self) -> None:
        if os.name != "nt":
            raise NativePortError("UNSUPPORTED_PLATFORM")
        self._kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self._ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
        self._advapi = ctypes.WinDLL("advapi32", use_last_error=True)
        self._tracked_handles: set[int] = set()
        self._native_allocations: set[int] = set()
        self._configure_abi()

    def resource_counts(self) -> tuple[int, int]:
        return len(self._tracked_handles), len(self._native_allocations)

    def _error(self, reason: str, *, completion_unknown: bool = False) -> NativePortError:
        handles, allocations = self.resource_counts()
        return NativePortError(reason, completion_unknown=completion_unknown,
            unreleased_handle_count=handles,
            unreleased_native_allocation_count=allocations)

    def _release_local(self, pointer: ctypes.c_void_p) -> None:
        if self._kernel.LocalFree(pointer):
            raise self._error("SECURITY_DESCRIPTOR_LOCALFREE_FAILED")
        if pointer.value:
            self._native_allocations.discard(int(pointer.value))

    def _configure_abi(self) -> None:
        k, n = self._kernel, self._ntdll
        k.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
            ctypes.POINTER(_SECURITY_ATTRIBUTES), wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        k.CreateFileW.restype = wintypes.HANDLE
        n.NtCreateFile.argtypes = [ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD,
            ctypes.POINTER(_OBJECT_ATTRIBUTES), ctypes.POINTER(_IO_STATUS_BLOCK),
            ctypes.POINTER(ctypes.c_longlong), wintypes.ULONG, wintypes.ULONG,
            wintypes.ULONG, wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG]
        n.NtCreateFile.restype = _S32
        n.NtQueryDirectoryFile.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.c_void_p,
            ctypes.c_void_p, ctypes.POINTER(_IO_STATUS_BLOCK), ctypes.c_void_p, wintypes.ULONG,
            ctypes.c_int, wintypes.BOOL, ctypes.c_void_p, wintypes.BOOL]
        n.NtQueryDirectoryFile.restype = _S32
        k.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
        k.SetHandleInformation.restype = wintypes.BOOL
        k.GetHandleInformation.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        k.GetHandleInformation.restype = wintypes.BOOL
        k.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        k.GetFileInformationByHandleEx.restype = wintypes.BOOL
        k.GetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.POINTER(_BY_HANDLE_FILE_INFORMATION)]
        k.GetFileInformationByHandle.restype = wintypes.BOOL
        k.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
        k.GetFinalPathNameByHandleW.restype = wintypes.DWORD
        k.LockFileEx.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
            wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(_OVERLAPPED)]
        k.LockFileEx.restype = wintypes.BOOL
        k.UnlockFileEx.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
            wintypes.DWORD, ctypes.POINTER(_OVERLAPPED)]
        k.UnlockFileEx.restype = wintypes.BOOL
        k.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        k.ReadFile.restype = wintypes.BOOL
        k.WriteFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        k.WriteFile.restype = wintypes.BOOL
        k.FlushFileBuffers.argtypes = [wintypes.HANDLE]
        k.FlushFileBuffers.restype = wintypes.BOOL
        k.SetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        k.SetFileInformationByHandle.restype = wintypes.BOOL
        k.SetFilePointerEx.argtypes = [wintypes.HANDLE, ctypes.c_longlong,
            ctypes.POINTER(ctypes.c_longlong), wintypes.DWORD]
        k.SetFilePointerEx.restype = wintypes.BOOL
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.CloseHandle.restype = wintypes.BOOL
        k.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
        k.GetDriveTypeW.restype = wintypes.UINT
        k.GetVolumeInformationByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR,
            wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR, wintypes.DWORD]
        k.GetVolumeInformationByHandleW.restype = wintypes.BOOL
        k.GetCurrentProcess.argtypes = []
        k.GetCurrentProcess.restype = wintypes.HANDLE
        k.LocalFree.argtypes = [ctypes.c_void_p]
        k.LocalFree.restype = ctypes.c_void_p
        a = self._advapi
        a.GetSecurityInfo.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_void_p)]
        a.GetSecurityInfo.restype = wintypes.DWORD
        a.GetSecurityDescriptorControl.argtypes = [ctypes.c_void_p,
            ctypes.POINTER(wintypes.USHORT), ctypes.POINTER(wintypes.DWORD)]
        a.GetSecurityDescriptorControl.restype = wintypes.BOOL
        a.GetSecurityDescriptorLength.argtypes = [ctypes.c_void_p]
        a.GetSecurityDescriptorLength.restype = wintypes.DWORD
        a.GetSecurityDescriptorDacl.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.BOOL),
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.BOOL)]
        a.GetSecurityDescriptorDacl.restype = wintypes.BOOL
        a.GetAclInformation.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.c_int]
        a.GetAclInformation.restype = wintypes.BOOL
        a.GetAce.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)]
        a.GetAce.restype = wintypes.BOOL
        a.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
        a.OpenProcessToken.restype = wintypes.BOOL
        a.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
            wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        a.GetTokenInformation.restype = wintypes.BOOL
        a.EqualSid.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        a.EqualSid.restype = wintypes.BOOL
        a.IsValidSid.argtypes = [ctypes.c_void_p]
        a.IsValidSid.restype = wintypes.BOOL
        a.GetLengthSid.argtypes = [ctypes.c_void_p]
        a.GetLengthSid.restype = wintypes.DWORD
        a.CreateWellKnownSid.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.POINTER(wintypes.DWORD)]
        a.CreateWellKnownSid.restype = wintypes.BOOL

    def _noninherit(self, handle: int) -> int:
        self._tracked_handles.add(int(handle))
        if not self._kernel.SetHandleInformation(handle, _HANDLE_FLAG_INHERIT, 0):
            error = _last_error()
            if self._kernel.CloseHandle(handle):
                self._tracked_handles.discard(int(handle))
            raise self._error(f"HANDLE_INHERITANCE_SET_FAILED_{error}")
        flags = wintypes.DWORD()
        if not self._kernel.GetHandleInformation(handle, ctypes.byref(flags)) or flags.value & _HANDLE_FLAG_INHERIT:
            error = _last_error()
            if self._kernel.CloseHandle(handle):
                self._tracked_handles.discard(int(handle))
            raise self._error(f"HANDLE_INHERITANCE_READBACK_FAILED_{error}")
        return int(handle)

    def open_volume_root(self) -> int:
        root = PRODUCTION_LEDGER_ROOT.anchor
        if self._kernel.GetDriveTypeW(root) != _DRIVE_FIXED:
            raise NativePortError("ROOT_NOT_FIXED_LOCAL")
        security = _SECURITY_ATTRIBUTES(ctypes.sizeof(_SECURITY_ATTRIBUTES), None, False)
        handle = self._kernel.CreateFileW(root, DIRECTORY_ACCESS, DIRECTORY_SHARE,
            ctypes.byref(security), OPEN_EXISTING, DIRECTORY_FLAGS, None)
        if handle in (None, 0, _INVALID_HANDLE_VALUE):
            raise NativePortError("ROOT_OPEN_FAILED")
        handle = self._noninherit(int(handle))
        filesystem = ctypes.create_unicode_buffer(32)
        if not self._kernel.GetVolumeInformationByHandleW(handle, None, 0, None, None,
                None, filesystem, len(filesystem)):
            error = _last_error()
            try:
                self.close(handle)
            except NativePortError:
                raise self._error(f"ROOT_FILESYSTEM_READ_FAILED_{error}_HANDLE_RETAINED")
            raise self._error(f"ROOT_FILESYSTEM_READ_FAILED_{error}")
        if filesystem.value.upper() != "NTFS":
            try:
                self.close(handle)
            except NativePortError:
                raise self._error("ROOT_FILESYSTEM_NOT_NTFS_HANDLE_RETAINED")
            raise self._error("ROOT_FILESYSTEM_NOT_NTFS")
        return handle

    def open_relative(self, parent: int, name: str, *, kind: str, create: bool = False) -> int:
        name = _safe_component(name)
        table = {
            "directory": (DIRECTORY_ACCESS, DIRECTORY_SHARE, _FILE_DIRECTORY_FILE, _FILE_OPEN),
            "lock": (LOCK_ACCESS, LOCK_SHARE, _FILE_NON_DIRECTORY_FILE, _FILE_OPEN),
            "pending": (PENDING_ACCESS, PENDING_SHARE,
                _FILE_NON_DIRECTORY_FILE | _FILE_WRITE_THROUGH, _FILE_CREATE if create else _FILE_OPEN),
            "final": (FINAL_ACCESS, FINAL_SHARE, _FILE_NON_DIRECTORY_FILE, _FILE_OPEN),
        }
        try:
            access, share, options, disposition = table[kind]
        except KeyError as exc:
            raise NativePortError("INVALID_OPEN_KIND") from exc
        buffer = ctypes.create_unicode_buffer(name)
        unicode = _UNICODE_STRING(len(name.encode("utf-16-le")),
            len(name.encode("utf-16-le")) + 2, ctypes.cast(buffer, wintypes.LPWSTR))
        attrs = _OBJECT_ATTRIBUTES(ctypes.sizeof(_OBJECT_ATTRIBUTES), parent,
            ctypes.pointer(unicode), _OBJ_CASE_INSENSITIVE, None, None)
        iosb, output = _IO_STATUS_BLOCK(), wintypes.HANDLE()
        status = int(self._ntdll.NtCreateFile(ctypes.byref(output), access | _SYNCHRONIZE,
            ctypes.byref(attrs), ctypes.byref(iosb), None, _FILE_ATTRIBUTE_NORMAL,
            share, disposition, options | _FILE_OPEN_REPARSE_POINT | _FILE_SYNCHRONOUS_IO_NONALERT,
            None, 0))
        if status < 0:
            if status in {_STATUS_NO_SUCH_FILE, _STATUS_OBJECT_NAME_NOT_FOUND}:
                raise NativePortError("NOT_FOUND")
            if status == _STATUS_OBJECT_NAME_COLLISION:
                raise NativePortError("CREATE_COLLISION")
            raise NativePortError(f"NTCREATE_FAILED_{status & 0xFFFFFFFF:08X}")
        return self._noninherit(int(output.value))

    def enumerate_relative(self, directory: int, *, max_entries: int = 274) -> tuple[DirectoryEntry, ...]:
        """Handle-only bounded enumeration; no FindFirstFile/path fallback."""
        results: list[DirectoryEntry] = []
        restart = True
        while True:
            storage = ctypes.create_string_buffer(64 * 1024)
            iosb = _IO_STATUS_BLOCK()
            status = int(self._ntdll.NtQueryDirectoryFile(directory, None, None, None,
                ctypes.byref(iosb), storage, len(storage), _FILE_ID_EXTD_DIRECTORY_INFORMATION,
                False, None, restart))
            restart = False
            if status in {_STATUS_NO_MORE_FILES, _STATUS_NO_SUCH_FILE}:
                break
            if status < 0:
                raise NativePortError(f"ENUMERATION_FAILED_{status & 0xFFFFFFFF:08X}")
            used, offset = int(iosb.Information), 0
            if used <= 0 or used > len(storage):
                raise NativePortError("MALFORMED_DIRECTORY_ENUMERATION")
            while offset < used:
                # FILE_ID_EXTD_DIR_INFORMATION has a 16-byte FileId and an
                # 88-byte fixed prefix on supported Windows/NTFS systems.
                next_offset = int.from_bytes(storage.raw[offset:offset + 4], "little")
                attributes = int.from_bytes(storage.raw[offset + 56:offset + 60], "little")
                name_len = int.from_bytes(storage.raw[offset + 60:offset + 64], "little")
                size = int.from_bytes(storage.raw[offset + 40:offset + 48], "little", signed=True)
                file_id = storage.raw[offset + 72:offset + 88]
                raw_name = storage.raw[offset + 88:offset + 88 + name_len]
                record_end = offset + 88 + name_len
                if (len(file_id) != 16 or not any(file_id) or size < 0 or name_len % 2
                        or record_end > used):
                    raise NativePortError("MALFORMED_DIRECTORY_ENUMERATION")
                try:
                    name = raw_name.decode("utf-16-le", errors="strict")
                except UnicodeDecodeError as exc:
                    raise NativePortError("MALFORMED_DIRECTORY_ENUMERATION") from exc
                if name not in {".", ".."}:
                    results.append(DirectoryEntry(name, file_id, attributes, size))
                    if len(results) > max_entries:
                        raise NativePortError("NAMESPACE_ENTRY_BOUND_EXCEEDED")
                if next_offset == 0:
                    if record_end != used:
                        raise NativePortError("MALFORMED_DIRECTORY_ENUMERATION")
                    break
                if (next_offset < 88 + name_len or next_offset % 8 != 0 or
                        offset + next_offset > used):
                    raise NativePortError("MALFORMED_DIRECTORY_ENUMERATION")
                offset += next_offset
        return tuple(results)

    def identity(self, handle: int, *, security_role: str = "private_child") -> HandleIdentity:
        tag, fid, basic = _FILE_ATTRIBUTE_TAG_INFO(), _FILE_ID_INFO(), _BY_HANDLE_FILE_INFORMATION()
        if not self._kernel.GetFileInformationByHandleEx(handle, 9, ctypes.byref(tag), ctypes.sizeof(tag)):
            raise NativePortError("IDENTITY_ATTRIBUTE_FAILED")
        if tag.FileAttributes & _FILE_ATTRIBUTE_REPARSE_POINT:
            raise NativePortError("REPARSE_POINT_REJECTED")
        if not self._kernel.GetFileInformationByHandleEx(handle, 18, ctypes.byref(fid), ctypes.sizeof(fid)):
            raise NativePortError("IDENTITY_FILEID_FAILED")
        if not self._kernel.GetFileInformationByHandle(handle, ctypes.byref(basic)):
            raise NativePortError("IDENTITY_BASIC_FAILED")
        capacity = 32768
        path = ctypes.create_unicode_buffer(capacity)
        length = self._kernel.GetFinalPathNameByHandleW(handle, path, capacity, 0)
        if not length or length >= capacity:
            raise NativePortError("IDENTITY_FINAL_PATH_FAILED")
        size = (int(basic.nFileSizeHigh) << 32) | int(basic.nFileSizeLow)
        # DACL/owner verification is intentionally a native method boundary;
        # the implementation fails closed until the strict predicate succeeds.
        security = (b"ANCESTOR_IDENTITY_ONLY" if security_role == "ancestor"
            else self._strict_security_material(handle, role=security_role))
        return HandleIdentity(int(fid.VolumeSerialNumber), bytes(fid.FileId), path.value,
            int(tag.FileAttributes), int(basic.nNumberOfLinks), size, security)

    def _strict_security_material(self, handle: int, *, role: str) -> bytes:
        """Return opaque verified owner/DACL material or fail closed.

        No SDDL/SID is rendered.  The production policy requires the root to be
        provisioned by the installer; this adapter uses GetSecurityInfo through
        a deliberately narrow helper that can be replaced only privately in
        focused tests.
        """
        if role not in {"private_root", "private_child"}:
            raise NativePortError("INVALID_SECURITY_ROLE")
        owner, dacl, descriptor = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_void_p()
        result = self._advapi.GetSecurityInfo(handle, _SE_FILE_OBJECT,
            _OWNER_SECURITY_INFORMATION | _DACL_SECURITY_INFORMATION,
            ctypes.byref(owner), None, ctypes.byref(dacl), None, ctypes.byref(descriptor))
        if descriptor.value:
            self._native_allocations.add(int(descriptor.value))
        if result != 0 or not descriptor.value or not owner.value:
            if descriptor.value:
                self._release_local(descriptor)
            raise self._error("SECURITY_DESCRIPTOR_READ_FAILED")
        token_handle = wintypes.HANDLE()
        try:
            control, revision = wintypes.USHORT(), wintypes.DWORD()
            if not self._advapi.GetSecurityDescriptorControl(descriptor,
                    ctypes.byref(control), ctypes.byref(revision)):
                raise NativePortError("DACL_CONTROL_READ_FAILED")
            if role == "private_root" and not control.value & _SE_DACL_PROTECTED:
                raise NativePortError("DACL_NOT_PROTECTED")
            present, defaulted, observed_dacl = wintypes.BOOL(), wintypes.BOOL(), ctypes.c_void_p()
            if (not self._advapi.GetSecurityDescriptorDacl(descriptor, ctypes.byref(present),
                    ctypes.byref(observed_dacl), ctypes.byref(defaulted)) or
                    not present.value or not observed_dacl.value or observed_dacl.value != dacl.value):
                raise NativePortError("DACL_NULL_OR_MISSING")
            if not self._advapi.OpenProcessToken(self._kernel.GetCurrentProcess(), _TOKEN_QUERY,
                    ctypes.byref(token_handle)):
                raise NativePortError("PROCESS_TOKEN_OPEN_FAILED")
            self._tracked_handles.add(int(token_handle.value))
            required = wintypes.DWORD()
            self._advapi.GetTokenInformation(token_handle, _TOKEN_USER, None, 0, ctypes.byref(required))
            if not required.value:
                raise NativePortError("PROCESS_TOKEN_USER_FAILED")
            token_buffer = ctypes.create_string_buffer(required.value)
            if not self._advapi.GetTokenInformation(token_handle, _TOKEN_USER, token_buffer,
                    required, ctypes.byref(required)):
                raise NativePortError("PROCESS_TOKEN_USER_FAILED")
            current_sid = _TOKEN_USER_STRUCT.from_buffer(token_buffer).Sid
            if (not current_sid or not self._advapi.IsValidSid(owner) or
                    not self._advapi.IsValidSid(current_sid) or
                    not self._advapi.EqualSid(owner, current_sid)):
                raise NativePortError("OWNER_SID_POLICY_FAILED")
            elevation, elevation_size = wintypes.DWORD(), wintypes.DWORD()
            if (not self._advapi.GetTokenInformation(token_handle, _TOKEN_ELEVATION,
                    ctypes.byref(elevation), ctypes.sizeof(elevation), ctypes.byref(elevation_size)) or
                    elevation.value != 0):
                raise NativePortError("ELEVATED_PROCESS_REJECTED")
            allowed_sids = [current_sid]
            for well_known in (22, 26):  # LocalSystemSid, BuiltinAdministratorsSid
                size = wintypes.DWORD(68)
                sid_buffer = ctypes.create_string_buffer(size.value)
                if not self._advapi.CreateWellKnownSid(well_known, None, sid_buffer, ctypes.byref(size)):
                    raise NativePortError("WELL_KNOWN_SID_BUILD_FAILED")
                allowed_sids.append(ctypes.addressof(sid_buffer))
                # Keep buffers alive until all ACE comparisons have completed.
                if "sid_buffers" not in locals():
                    sid_buffers = []
                sid_buffers.append(sid_buffer)
            acl_info = _ACL_SIZE_INFORMATION_STRUCT()
            if not self._advapi.GetAclInformation(dacl, ctypes.byref(acl_info),
                    ctypes.sizeof(acl_info), _ACL_SIZE_INFORMATION):
                raise NativePortError("DACL_INFO_READ_FAILED")
            allow_seen = False
            for index in range(int(acl_info.AceCount)):
                ace_pointer = ctypes.c_void_p()
                if not self._advapi.GetAce(dacl, index, ctypes.byref(ace_pointer)) or not ace_pointer.value:
                    raise NativePortError("DACL_ACE_READ_FAILED")
                header = _ACE_HEADER.from_address(ace_pointer.value)
                if header.AceSize < 12:
                    raise NativePortError("DACL_NONCANONICAL_ACE")
                mask = ctypes.c_uint32.from_address(ace_pointer.value + 4).value
                sid = ctypes.c_void_p(ace_pointer.value + 8)
                sid_length = (int(self._advapi.GetLengthSid(sid))
                    if self._advapi.IsValidSid(sid) else 0)
                if sid_length == 0 or sid_length > header.AceSize - 8:
                    raise NativePortError("DACL_INVALID_SID")
                allow_seen = _validate_ace_policy(role=role, ace_type=header.AceType,
                    ace_flags=header.AceFlags, mask=mask,
                    sid_is_allowed=any(self._advapi.EqualSid(sid, candidate)
                        for candidate in allowed_sids), allow_seen=allow_seen)
            length = int(self._advapi.GetSecurityDescriptorLength(descriptor))
            if not 1 <= length <= 65536:
                raise NativePortError("SECURITY_DESCRIPTOR_LENGTH_INVALID")
            return ctypes.string_at(descriptor, length)
        finally:
            cleanup_failure = None
            if token_handle.value:
                try:
                    self.close(int(token_handle.value))
                except NativePortError:
                    cleanup_failure = "TOKEN_HANDLE_CLOSE_FAILED"
            if descriptor.value:
                try:
                    self._release_local(descriptor)
                except NativePortError:
                    cleanup_failure = (cleanup_failure or "SECURITY_DESCRIPTOR_LOCALFREE_FAILED")
            if cleanup_failure is not None:
                raise self._error(cleanup_failure)

    def lock(self, handle: int) -> None:
        ov = _OVERLAPPED(); ov.u.s.Offset = 0; ov.u.s.OffsetHigh = 0
        if not self._kernel.LockFileEx(handle,
            LOCKFILE_EXCLUSIVE_LOCK | LOCKFILE_FAIL_IMMEDIATELY, 0,
            0xFFFFFFFF, 0xFFFFFFFF, ctypes.byref(ov)):
            error = _last_error()
            if error == ERROR_LOCK_VIOLATION:
                raise NativePortError("LOCK_BUSY")
            raise NativePortError(f"LOCK_ACQUIRE_FAILED_{error}")

    def unlock(self, handle: int) -> None:
        ov = _OVERLAPPED(); ov.u.s.Offset = 0; ov.u.s.OffsetHigh = 0
        if not self._kernel.UnlockFileEx(handle, 0xFFFFFFFF, 0xFFFFFFFF, ctypes.byref(ov)):
            raise NativePortError(f"LOCK_RELEASE_FAILED_{_last_error()}")

    def read_all(self, handle: int, *, maximum: int) -> bytes:
        identity = self.identity(handle)
        if identity.size > maximum:
            raise NativePortError("FILE_SIZE_BOUND_EXCEEDED")
        buffer = ctypes.create_string_buffer(identity.size + 1)
        read = wintypes.DWORD()
        if not self._kernel.ReadFile(handle, buffer, identity.size + 1, ctypes.byref(read), None):
            raise NativePortError("READ_FAILED")
        if read.value != identity.size:
            raise NativePortError("SHORT_READ")
        return bytes(buffer.raw[:read.value])

    def rewind(self, handle: int) -> None:
        if not self._kernel.SetFilePointerEx(handle, ctypes.c_longlong(0), None, 0):
            raise NativePortError("FILE_REWIND_FAILED")

    def write_all(self, handle: int, payload: bytes) -> None:
        written = wintypes.DWORD()
        buffer = ctypes.create_string_buffer(payload)
        if not self._kernel.WriteFile(handle, buffer, len(payload), ctypes.byref(written), None):
            raise NativePortError("WRITE_FAILED")
        if written.value != len(payload):
            raise NativePortError("SHORT_WRITE")

    def flush_file(self, handle: int) -> None:
        if not self._kernel.FlushFileBuffers(handle):
            raise NativePortError("FILE_FLUSH_FAILED")

    def rename_no_replace(self, handle: int, root: int, final_name: str) -> None:
        final_name = _safe_component(final_name)
        encoded = final_name.encode("utf-16-le")
        filename_offset = _FILE_RENAME_INFO_EX_HEAD.FileNameLength.offset + ctypes.sizeof(wintypes.DWORD)
        size = filename_offset + len(encoded)
        storage = ctypes.create_string_buffer(size)
        head = _FILE_RENAME_INFO_EX_HEAD.from_buffer(storage)
        head.Flags = FILE_RENAME_FLAGS_NONE
        head.RootDirectory = root
        head.FileNameLength = len(encoded)
        ctypes.memmove(ctypes.addressof(storage) + filename_offset, encoded, len(encoded))
        if not self._kernel.SetFileInformationByHandle(handle, FILE_RENAME_INFO_EX_CLASS,
            storage, size):
            raise NativePortError(f"RENAME_FAILED_{_last_error()}")

    def close(self, handle: int) -> None:
        if not self._kernel.CloseHandle(handle):
            raise self._error(f"HANDLE_CLOSE_FAILED_{_last_error()}")
        self._tracked_handles.discard(int(handle))


def create_production_port() -> CtypesWindowsLedgerPort:
    """Fail before filesystem I/O when the production backend is unsupported."""
    if os.name != "nt":
        raise NativePortError("UNSUPPORTED_PLATFORM")
    return CtypesWindowsLedgerPort()


__all__ = ["NativePortError", "create_production_port"]
