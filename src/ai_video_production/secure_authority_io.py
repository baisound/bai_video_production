from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import ctypes
from ctypes import wintypes
import errno
from functools import wraps
import hashlib
import json
import math
import os
from pathlib import Path, PurePath
import secrets
import stat
from typing import Any, Callable, Literal, NoReturn
import weakref


_WINDOWS_REPARSE_POINT = 0x400
_MAX_COMPONENTS = 32
_MAX_COMPONENT_CHARS = 255
_MAX_RELATIVE_PATH_CHARS = 4096
_DEFAULT_MAX_BYTES = 1024 * 1024
_DEFAULT_MAX_DEPTH = 64
_DEFAULT_MAX_NODES = 100_000
_MAX_IMMUTABLE_REVISION = 1_000_000
_MAX_U64 = (1 << 64) - 1
_MIN_I64 = -(1 << 63)
_MAX_I64 = (1 << 63) - 1
_IMMUTABLE_NAMESPACE = ".immutable-authority"
_IMMUTABLE_PLAN_VERSION = "TASK068_IMMUTABLE_PLAN_V1"
_IMMUTABLE_RECEIPT_VERSION = "TASK068_IMMUTABLE_RECEIPT_V1"
_CURRENTNESS_STATUS = "CURRENT_HEAD_AUTHORITY_NOT_CREATED"
_DIRECTORY_TREE_STATUS = "DIRECTORY_TREE_COMMIT_AUTHORITY_NOT_CREATED"
_MUTABLE_PHASE_STATUS = "MUTABLE_PHASE_ADVANCE_UNAVAILABLE"
_DUPLICATE_CURRENTNESS_STATUS = "DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED"
_WINDOWS_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)
_WINDOWS_SUPERSCRIPT_DEVICE_DIGITS = str.maketrans({"¹": "1", "²": "2", "³": "3"})


class SecureAuthorityIOError(RuntimeError):
    """Body-free failure suitable for authority boundaries and audit receipts."""

    def __init__(self, code: str, *, completion_unknown: bool = False) -> None:
        self.code = code
        self.completion_unknown = completion_unknown
        self.authority_created = False
        self.currentness_selected = False
        self.status_code = _CURRENTNESS_STATUS
        self.directory_tree_status_code = _DIRECTORY_TREE_STATUS
        self.mutable_phase_status_code = _MUTABLE_PHASE_STATUS
        self.duplicate_currentness_status_code = _DUPLICATE_CURRENTNESS_STATUS
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class ArtifactIdentity:
    device: int
    inode: int
    mode: int
    nlink: int
    size: int
    mtime_ns: int
    reparse_point: bool

    @property
    def authority_created(self) -> bool:
        return False

    @property
    def currentness_selected(self) -> bool:
        return False

    @property
    def status_code(self) -> str:
        return _CURRENTNESS_STATUS

    @property
    def duplicate_currentness_status_code(self) -> str:
        return _DUPLICATE_CURRENTNESS_STATUS


@dataclass(frozen=True, repr=False, slots=True)
class TrustedImmutablePlan:
    relative_path: str
    operation_id: str
    revision: int
    body_sha256: str
    expected_predecessor_sha256: str
    action: Literal["GENERATION", "COMMIT", "TOMBSTONE", "ABORT", "COMPENSATE"]
    build_id: str
    backend_id: str
    session_id: str
    instance_id: str
    authorization: str

    @property
    def authority_created(self) -> bool:
        return False

    @property
    def currentness_selected(self) -> bool:
        return False

    @property
    def status_code(self) -> str:
        return _CURRENTNESS_STATUS

    @property
    def duplicate_currentness_status_code(self) -> str:
        return _DUPLICATE_CURRENTNESS_STATUS

    def __repr__(self) -> str:
        return "<TrustedImmutablePlan redacted>"


@dataclass(frozen=True, slots=True)
class ImmutablePublishReceipt:
    sha256: str
    predecessor_sha256: str
    byte_count: int
    identity: ArtifactIdentity
    plan_fingerprint: str
    security_sha256: str
    receipt_fingerprint: str
    version: str

    @property
    def authority_created(self) -> bool:
        return False

    @property
    def currentness_selected(self) -> bool:
        return False

    @property
    def status_code(self) -> str:
        return _CURRENTNESS_STATUS

    @property
    def directory_tree_status_code(self) -> str:
        return _DIRECTORY_TREE_STATUS

    @property
    def mutable_phase_status_code(self) -> str:
        return _MUTABLE_PHASE_STATUS

    @property
    def duplicate_currentness_status_code(self) -> str:
        return _DUPLICATE_CURRENTNESS_STATUS


@dataclass(frozen=True)
class ImmutableGraphInspectionReceipt:
    inspected_count: int
    plan_fingerprint: str

    @property
    def authority_created(self) -> bool:
        return False

    @property
    def currentness_selected(self) -> bool:
        return False

    @property
    def status_code(self) -> str:
        return _CURRENTNESS_STATUS

    @property
    def directory_tree_status_code(self) -> str:
        return _DIRECTORY_TREE_STATUS

    @property
    def mutable_phase_status_code(self) -> str:
        return _MUTABLE_PHASE_STATUS

    @property
    def duplicate_currentness_status_code(self) -> str:
        return _DUPLICATE_CURRENTNESS_STATUS


@dataclass(frozen=True, repr=False)
class FrozenJsonObject(Mapping[str, Any]):
    _items: tuple[tuple[str, Any], ...]

    def __init__(self, values: dict[str, Any]) -> None:
        object.__setattr__(self, "_items", tuple(values.items()))

    def __getitem__(self, key: str) -> Any:
        for candidate, value in self._items:
            if candidate == key:
                return value
        raise KeyError(key)

    def __iter__(self):
        return (key for key, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} keys={len(self)}>"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Mapping):
            return dict(self.items()) == dict(other.items())
        return False


@dataclass(frozen=True, repr=False)
class FrozenJsonArray(Sequence[Any]):
    _values: tuple[Any, ...]

    def __init__(self, values: list[Any]) -> None:
        object.__setattr__(self, "_values", tuple(values))

    def __getitem__(self, index):
        return self._values[index]

    def __len__(self) -> int:
        return len(self._values)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} items={len(self)}>"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Sequence) and not isinstance(other, (str, bytes, bytearray)):
            return tuple(self) == tuple(other)
        return False


@dataclass(frozen=True, repr=False)
class SecureJsonRead:
    document: Any
    sha256: str
    byte_count: int
    identity: ArtifactIdentity
    security_sha256: str

    @property
    def authority_created(self) -> bool:
        return False

    @property
    def currentness_selected(self) -> bool:
        return False

    @property
    def status_code(self) -> str:
        return _CURRENTNESS_STATUS

    @property
    def directory_tree_status_code(self) -> str:
        return _DIRECTORY_TREE_STATUS

    @property
    def mutable_phase_status_code(self) -> str:
        return _MUTABLE_PHASE_STATUS

    @property
    def duplicate_currentness_status_code(self) -> str:
        return _DUPLICATE_CURRENTNESS_STATUS


@dataclass(frozen=True)
class SecurePublishReceipt:
    sha256: str
    byte_count: int
    identity: ArtifactIdentity
    security_sha256: str

    @property
    def authority_created(self) -> bool:
        return False

    @property
    def currentness_selected(self) -> bool:
        return False

    @property
    def status_code(self) -> str:
        return _CURRENTNESS_STATUS

    @property
    def directory_tree_status_code(self) -> str:
        return _DIRECTORY_TREE_STATUS

    @property
    def mutable_phase_status_code(self) -> str:
        return _MUTABLE_PHASE_STATUS

    @property
    def duplicate_currentness_status_code(self) -> str:
        return _DUPLICATE_CURRENTNESS_STATUS


StageHook = Callable[[str], None]
ImmutablePlanVerifier = Callable[[TrustedImmutablePlan, str], bool]
ImmutableReceiptVerifier = Callable[[str], bool]
ImmutableGraphVerifier = Callable[[str, str], bool]


@dataclass(frozen=True, slots=True)
class _ValidatedImmutablePlan:
    snapshot: TrustedImmutablePlan
    parts: tuple[str, ...]
    fingerprint: str


@dataclass(frozen=True, slots=True)
class _ValidatedImmutableReceipt:
    snapshot: ImmutablePublishReceipt
    fingerprint: str


def _fail(code: str, *, completion_unknown: bool = False) -> SecureAuthorityIOError:
    return SecureAuthorityIOError(code, completion_unknown=completion_unknown)


def _detached_public_error_boundary(
    operation: Callable[..., Any],
) -> Callable[..., Any]:
    """Reconstruct public failures after the private exception scope ends."""

    @wraps(operation)
    def detached(*args: Any, **kwargs: Any) -> Any:
        try:
            return operation(*args, **kwargs)
        except SecureAuthorityIOError as caught:
            code = caught.code
            completion_unknown = caught.completion_unknown
        try:
            raise _fail(code, completion_unknown=completion_unknown) from None
        except SecureAuthorityIOError as public_error:
            # `from None` suppresses display but Python still records any
            # caller-ambient exception in __context__. Clear it on the actual
            # raised instance, then bare-reraise without creating a new chain.
            public_error.__cause__ = None
            public_error.__context__ = None
            public_error.__suppress_context__ = True
            raise

    return detached


def _sha256(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _is_sha256(value: object) -> bool:
    if type(value) is not str or len(value) != 71 or not value.startswith("sha256:"):
        return False
    suffix = value[7:]
    return suffix == suffix.lower() and all(character in "0123456789abcdef" for character in suffix)


def _snapshot_artifact_identity(value: object) -> ArtifactIdentity:
    if type(value) is not ArtifactIdentity:
        raise _fail("IMMUTABLE_IDENTITY_REQUIRED")
    first = (
        value.device,
        value.inode,
        value.mode,
        value.nlink,
        value.size,
        value.mtime_ns,
        value.reparse_point,
    )
    second = (
        value.device,
        value.inode,
        value.mode,
        value.nlink,
        value.size,
        value.mtime_ns,
        value.reparse_point,
    )
    if first != second:
        raise _fail("IMMUTABLE_IDENTITY_CHANGED")
    if (
        any(type(field) is not int for field in first[:6])
        or type(first[6]) is not bool
        or not 0 <= first[0] <= _MAX_U64
        or first[1] <= 0
        or first[1] > _MAX_U64
        or not 0 <= first[2] <= _MAX_U64
        or not 0 <= first[3] <= _MAX_U64
        or not 0 <= first[4] <= _MAX_U64
        or not _MIN_I64 <= first[5] <= _MAX_I64
    ):
        raise _fail("IMMUTABLE_IDENTITY_REQUIRED")
    snapshot = ArtifactIdentity(*first)
    _require_regular(snapshot)
    return snapshot


def _identity_binding(identity: ArtifactIdentity) -> dict[str, int | bool]:
    return {
        "device": identity.device,
        "inode": identity.inode,
        "mode": identity.mode,
        "nlink": identity.nlink,
        "size": identity.size,
        "mtime_ns": identity.mtime_ns,
        "reparse_point": identity.reparse_point,
    }


def _immutable_receipt_fingerprint(
    *,
    sha256: str,
    predecessor_sha256: str,
    byte_count: int,
    identity: ArtifactIdentity,
    plan_fingerprint: str,
    security_sha256: str,
    version: str,
) -> str:
    payload = json.dumps(
        {
            "byte_count": byte_count,
            "identity": _identity_binding(identity),
            "plan_fingerprint": plan_fingerprint,
            "predecessor_sha256": predecessor_sha256,
            "security_sha256": security_sha256,
            "sha256": sha256,
            "version": version,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return _sha256(payload)


def _bounded_identifier(value: object) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= 128
        and value.isascii()
        and all(32 < ord(character) < 127 for character in value)
    )


def _identity(value: os.stat_result) -> ArtifactIdentity:
    attributes = int(getattr(value, "st_file_attributes", 0))
    return ArtifactIdentity(
        device=int(value.st_dev),
        inode=int(value.st_ino),
        mode=int(value.st_mode),
        nlink=int(value.st_nlink),
        size=int(value.st_size),
        mtime_ns=int(value.st_mtime_ns),
        reparse_point=bool(attributes & _WINDOWS_REPARSE_POINT),
    )


def _require_directory(value: ArtifactIdentity) -> None:
    if value.reparse_point:
        raise _fail("REPARSE_POINT_REJECTED")
    if not stat.S_ISDIR(value.mode):
        raise _fail("ANCESTOR_NOT_DIRECTORY")


def _require_regular(value: ArtifactIdentity, *, allow_zero_links: bool = False) -> None:
    if value.reparse_point:
        raise _fail("REPARSE_POINT_REJECTED")
    if not stat.S_ISREG(value.mode):
        raise _fail("NOT_REGULAR_FILE")
    if value.nlink != 1 and not (allow_zero_links and value.nlink == 0):
        raise _fail("LINK_COUNT_REJECTED")
    if value.inode == 0:
        raise _fail("FILE_IDENTITY_UNAVAILABLE")


def _same_ancestor_object(left: ArtifactIdentity, right: ArtifactIdentity) -> bool:
    """Directory namespace mutation may change metadata, not its pinned object."""
    return (
        left.device == right.device
        and left.inode == right.inode
        and stat.S_IFMT(left.mode) == stat.S_IFMT(right.mode)
        and left.reparse_point == right.reparse_point
    )


def _same_file_object(left: ArtifactIdentity, right: ArtifactIdentity) -> bool:
    return (
        left.device == right.device
        and left.inode == right.inode
        and stat.S_IFMT(left.mode) == stat.S_IFMT(right.mode)
        and left.size == right.size
        and left.mtime_ns == right.mtime_ns
        and left.reparse_point == right.reparse_point
    )


def _snapshot_for_write(
    value: Any,
    *,
    max_depth: int,
    max_nodes: int,
    max_bytes: int,
) -> Any:
    nodes = 0
    scalar_bytes = 0
    active: set[int] = set()

    def visit(current: Any, depth: int) -> Any:
        nonlocal nodes, scalar_bytes
        nodes += 1
        if nodes > max_nodes:
            raise _fail("JSON_NODE_BOUND_EXCEEDED")
        if depth > max_depth:
            raise _fail("JSON_DEPTH_BOUND_EXCEEDED")
        current_type = type(current)
        if current_type is dict:
            marker = id(current)
            if marker in active:
                raise _fail("JSON_CYCLE_REJECTED")
            active.add(marker)
            result: dict[str, Any] = {}
            try:
                if len(current) > max_nodes - nodes:
                    raise _fail("JSON_NODE_BOUND_EXCEEDED")
                for key in current:
                    if type(key) is not str or any(ord(character) < 32 for character in key):
                        raise _fail("JSON_KEY_REJECTED")
                    try:
                        scalar_bytes += len(key.encode("utf-8"))
                        child = current[key]
                    except (KeyError, RuntimeError, UnicodeError):
                        raise _fail("JSON_MUTATION_REJECTED") from None
                    if scalar_bytes > max_bytes:
                        raise _fail("BYTE_BOUND_EXCEEDED")
                    result[key] = visit(child, depth + 1)
            except SecureAuthorityIOError:
                raise
            except RuntimeError:
                raise _fail("JSON_MUTATION_REJECTED") from None
            finally:
                active.remove(marker)
            return result
        if current_type is list:
            marker = id(current)
            if marker in active:
                raise _fail("JSON_CYCLE_REJECTED")
            active.add(marker)
            try:
                length = len(current)
                if length > max_nodes - nodes:
                    raise _fail("JSON_NODE_BOUND_EXCEEDED")
                result = []
                for index in range(length):
                    try:
                        child = current[index]
                    except IndexError:
                        raise _fail("JSON_MUTATION_REJECTED") from None
                    result.append(visit(child, depth + 1))
                if len(current) != length:
                    raise _fail("JSON_MUTATION_REJECTED")
                return result
            finally:
                active.remove(marker)
        if current is None or current_type is bool:
            return current
        if current_type is str:
            if any(ord(character) < 32 for character in current):
                raise _fail("JSON_CONTROL_CHARACTER_REJECTED")
            try:
                scalar_bytes += len(current.encode("utf-8"))
            except UnicodeError:
                raise _fail("JSON_VALUE_REJECTED") from None
            if scalar_bytes > max_bytes:
                raise _fail("BYTE_BOUND_EXCEEDED")
            return current
        if current_type is int:
            try:
                scalar_bytes += len(str(current))
            except (ValueError, OverflowError):
                raise _fail("JSON_VALUE_REJECTED") from None
            if scalar_bytes > max_bytes:
                raise _fail("BYTE_BOUND_EXCEEDED")
            return current
        if current_type is float:
            if not math.isfinite(current):
                raise _fail("JSON_NONFINITE_REJECTED")
            return current
        raise _fail("JSON_VALUE_REJECTED")

    return visit(value, 1)


def _canonical_json_bytes(
    value: Any,
    *,
    max_depth: int,
    max_nodes: int,
    max_bytes: int,
) -> bytes:
    snapshot = _snapshot_for_write(
        value,
        max_depth=max_depth,
        max_nodes=max_nodes,
        max_bytes=max_bytes,
    )
    try:
        payload = json.dumps(
            snapshot,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise _fail("JSON_ENCODE_REJECTED") from None
    if len(payload) > max_bytes:
        raise _fail("BYTE_BOUND_EXCEEDED")
    return payload


class _DuplicateKey(ValueError):
    pass


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey
        result[key] = value
    return result


def _reject_constant(_: str) -> Any:
    raise ValueError


def _validate_tree(value: Any, *, max_depth: int, max_nodes: int) -> None:
    nodes = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > max_nodes:
            raise _fail("JSON_NODE_BOUND_EXCEEDED")
        if depth > max_depth:
            raise _fail("JSON_DEPTH_BOUND_EXCEEDED")
        if isinstance(current, dict):
            for key, child in current.items():
                if not isinstance(key, str):
                    raise _fail("JSON_KEY_REJECTED")
                if any(ord(character) < 32 for character in key):
                    raise _fail("JSON_CONTROL_CHARACTER_REJECTED")
                stack.append((child, depth + 1))
        elif isinstance(current, list):
            stack.extend((child, depth + 1) for child in current)
        elif isinstance(current, str):
            if any(ord(character) < 32 for character in current):
                raise _fail("JSON_CONTROL_CHARACTER_REJECTED")
        elif isinstance(current, float):
            if not math.isfinite(current):
                raise _fail("JSON_NONFINITE_REJECTED")
        elif current is not None and not isinstance(current, (str, int, float, bool)):
            raise _fail("JSON_VALUE_REJECTED")


def _strict_json(payload: bytes, *, max_depth: int, max_nodes: int) -> Any:
    try:
        text = payload.decode("utf-8", errors="strict")
        if text.startswith("\ufeff"):
            raise ValueError
        result = json.loads(
            text,
            object_pairs_hook=_pairs_without_duplicates,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise _fail("STRICT_JSON_REJECTED") from None
    _validate_tree(result, max_depth=max_depth, max_nodes=max_nodes)
    return _freeze_json(result)


def _freeze_json(value: Any) -> Any:
    if type(value) is dict:
        return FrozenJsonObject({key: _freeze_json(child) for key, child in value.items()})
    if type(value) is list:
        return FrozenJsonArray([_freeze_json(child) for child in value])
    return value


def _relative_parts(value: str | os.PathLike[str]) -> tuple[str, ...]:
    path: PurePath | None
    try:
        raw = os.fspath(value)
        if type(raw) is not str or len(raw) > _MAX_RELATIVE_PATH_CHARS:
            raise ValueError
        path = PurePath(raw)
    except Exception:
        path = None
    if path is None:
        raise _fail("RELATIVE_PATH_REJECTED") from None
    parts = tuple(path.parts)
    if (
        path.is_absolute()
        or bool(path.anchor)
        or not parts
        or len(parts) > _MAX_COMPONENTS
        or any(part in {"", ".", ".."} for part in parts)
        or any(len(part) > _MAX_COMPONENT_CHARS for part in parts)
        or any(any(ord(character) < 32 for character in part) for part in parts)
        or any((os.altsep and os.altsep in part) for part in parts)
        or any(":" in part or part.endswith((".", " ")) for part in parts)
        or any(
            part.split(".", 1)[0]
            .upper()
            .translate(_WINDOWS_SUPERSCRIPT_DEVICE_DIGITS)
            in _WINDOWS_RESERVED_NAMES
            for part in parts
        )
    ):
        raise _fail("RELATIVE_PATH_REJECTED")
    return parts


def _open_flags(*, writable: bool = False, create: bool = False, exclusive: bool = False) -> int:
    flags = os.O_RDWR if writable else os.O_RDONLY
    flags |= int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_CLOEXEC", 0))
    flags |= int(getattr(os, "O_NOINHERIT", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    if create:
        flags |= os.O_CREAT
    if exclusive:
        flags |= os.O_EXCL
    return flags


def _set_noninheritable(fd: int) -> None:
    try:
        os.set_inheritable(fd, False)
        if os.get_inheritable(fd):
            raise OSError
    except OSError:
        raise _fail("HANDLE_INHERITANCE_REJECTED") from None


def _windows_mark_delete_native_handle(handle: int) -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.SetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel.SetFileInformationByHandle.restype = wintypes.BOOL
    flags = wintypes.DWORD(0x1 | 0x2 | 0x4 | 0x10)
    if not kernel.SetFileInformationByHandle(
        wintypes.HANDLE(handle),
        21,
        ctypes.byref(flags),
        ctypes.sizeof(flags),
    ):
        raise _fail("HANDLE_DELETE_FAILED")


def _windows_abandon_native_handle(handle: int, *, delete_created: bool) -> None:
    cleanup_failed = False
    if delete_created:
        try:
            _windows_mark_delete_native_handle(handle)
        except SecureAuthorityIOError:
            cleanup_failed = True
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    if not kernel.CloseHandle(wintypes.HANDLE(handle)):
        cleanup_failed = True
    if cleanup_failed:
        raise _fail("HANDLE_CLEANUP_UNKNOWN", completion_unknown=True) from None


def _windows_open(
    path: Path,
    *,
    writable: bool,
    create_new: bool,
    directory: bool,
    delete_access: bool = False,
    share_write: bool = False,
) -> int:
    if os.name != "nt":
        raise _fail("WINDOWS_BACKEND_UNAVAILABLE")
    import msvcrt

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    access = 0x80000000 | (0x40000000 if writable else 0) | (0x00010000 if delete_access else 0)
    # Delete sharing is intentionally absent: an opened ancestor or target
    # cannot be renamed/reparsed out from under its operation.
    share = 0x1 | (0x2 if directory or share_write else 0)
    disposition = 1 if create_new else 3
    flags = 0x00200000 | (0x02000000 if directory else 0)  # OPEN_REPARSE_POINT | BACKUP_SEMANTICS
    handle = create_file(str(path), access, share, None, disposition, flags, None)
    invalid = ctypes.c_void_p(-1).value
    if handle in (None, 0, invalid):
        error = ctypes.get_last_error()
        if error in {2, 3}:
            raise FileNotFoundError from None
        if error in {80, 183}:
            raise FileExistsError from None
        if error in {32, 33}:
            raise _fail("WINDOWS_SHARING_VIOLATION")
        raise _fail("OPEN_FAILED")
    kernel.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
    kernel.SetHandleInformation.restype = wintypes.BOOL
    if not kernel.SetHandleInformation(handle, 1, 0):
        _windows_abandon_native_handle(int(handle), delete_created=create_new)
        raise _fail("HANDLE_INHERITANCE_REJECTED")
    try:
        flags = (os.O_RDWR if writable else os.O_RDONLY) | int(getattr(os, "O_BINARY", 0))
        return int(msvcrt.open_osfhandle(int(handle), flags))
    except OSError:
        _windows_abandon_native_handle(int(handle), delete_created=create_new)
        raise _fail("OPEN_FAILED") from None


def _windows_security_digest(fd: int) -> str | None:
    if os.name != "nt":
        return None
    import msvcrt

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    descriptor = ctypes.c_void_p()
    owner = ctypes.c_void_p()
    dacl = ctypes.c_void_p()
    advapi.GetSecurityInfo.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    advapi.GetSecurityInfo.restype = wintypes.DWORD
    advapi.GetSecurityDescriptorLength.argtypes = [ctypes.c_void_p]
    advapi.GetSecurityDescriptorLength.restype = wintypes.DWORD
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    result = advapi.GetSecurityInfo(
        wintypes.HANDLE(msvcrt.get_osfhandle(fd)),
        1,
        0x1 | 0x4,
        ctypes.byref(owner),
        None,
        ctypes.byref(dacl),
        None,
        ctypes.byref(descriptor),
    )
    if result != 0 or not descriptor.value or not owner.value or not dacl.value:
        if descriptor.value:
            kernel.LocalFree(descriptor)
        raise _fail("SECURITY_DESCRIPTOR_READ_FAILED")
    try:
        length = int(advapi.GetSecurityDescriptorLength(descriptor))
        if not 1 <= length <= 65536:
            raise _fail("SECURITY_DESCRIPTOR_LENGTH_REJECTED")
        return _sha256(ctypes.string_at(descriptor, length))
    finally:
        if kernel.LocalFree(descriptor):
            raise _fail("SECURITY_DESCRIPTOR_RELEASE_FAILED")


def _fd_security_digest(fd: int) -> str:
    if os.name == "nt":
        digest = _windows_security_digest(fd)
        if not _is_sha256(digest):
            raise _fail("SECURITY_DESCRIPTOR_READ_FAILED")
        return digest
    try:
        observed = os.fstat(fd)
    except OSError:
        raise _fail("SECURITY_DESCRIPTOR_READ_FAILED") from None
    payload = json.dumps(
        {
            "gid": int(getattr(observed, "st_gid", -1)),
            "mode": stat.S_IMODE(int(observed.st_mode)),
            "uid": int(getattr(observed, "st_uid", -1)),
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return _sha256(payload)


@dataclass
class _PinnedParent:
    root: Path
    target: Path
    name: str
    parent_fd: int | None
    pinned: list[tuple[Path, int, ArtifactIdentity, str]]

    def verify(self) -> None:
        for path, fd, expected, expected_security in self.pinned:
            try:
                observed = _identity(os.fstat(fd))
                named = _identity(os.lstat(path))
            except OSError:
                raise _fail("ANCESTOR_POST_IDENTITY_FAILED") from None
            if (
                not _same_ancestor_object(observed, expected)
                or not _same_ancestor_object(named, expected)
            ):
                raise _fail("ANCESTOR_IDENTITY_CHANGED")
            if _fd_security_digest(fd) != expected_security:
                raise _fail("ANCESTOR_SECURITY_DRIFT")

    def close(self) -> None:
        failure: SecureAuthorityIOError | None = None
        try:
            self.verify()
        except SecureAuthorityIOError as exc:
            failure = exc
        close_failed = False
        for _, fd, _, _ in reversed(self.pinned):
            try:
                os.close(fd)
            except OSError:
                close_failed = True
        if close_failed and failure is not None:
            raise _fail("HANDLE_CLEANUP_UNKNOWN", completion_unknown=True)
        if close_failed:
            raise _fail("HANDLE_CLOSE_FAILED")
        if failure is not None:
            raise failure


@dataclass
class _TempLease:
    name: str | None
    path: Path | None
    fd: int
    identity: ArtifactIdentity
    payload_sha256: str
    closed: bool = False

    def close(self) -> None:
        if not self.closed:
            try:
                os.close(self.fd)
            except OSError:
                raise _fail("HANDLE_CLOSE_FAILED") from None
            self.closed = True


class _WindowsRenameInfoHead(ctypes.Structure):
    _fields_ = [
        ("ReplaceIfExists", wintypes.BOOLEAN),
        ("RootDirectory", wintypes.HANDLE),
        ("FileNameLength", wintypes.DWORD),
    ]


class _WindowsIoStatusBlock(ctypes.Structure):
    _fields_ = [("Status", ctypes.c_void_p), ("Information", ctypes.c_size_t)]


def _windows_rename_handle(
    fd: int,
    destination: Path,
    *,
    replace: bool,
) -> None:
    if os.name != "nt":
        raise _fail("WINDOWS_BACKEND_UNAVAILABLE")
    import msvcrt

    # Keep the validated absolute spelling without resolving filesystem
    # objects. Path.resolve() would follow a final symlink/reparse point that a
    # competitor creates after the absence check and could redirect the live
    # source handle outside the pinned authority root.
    encoded = os.path.abspath(os.fspath(destination)).encode("utf-16-le")
    offset = _WindowsRenameInfoHead.FileNameLength.offset + ctypes.sizeof(wintypes.DWORD)
    logical_size = offset + len(encoded)
    # Some Windows builds consult the WCHAR terminator while normalizing an
    # absolute FileRenameInfo destination even though FileNameLength excludes
    # it. Keep the terminator inside the kernel-visible buffer.
    storage = ctypes.create_string_buffer(logical_size + ctypes.sizeof(wintypes.WCHAR))
    head = _WindowsRenameInfoHead.from_buffer(storage)
    head.ReplaceIfExists = 1 if replace else 0
    head.RootDirectory = wintypes.HANDLE()
    head.FileNameLength = len(encoded)
    ctypes.memmove(ctypes.addressof(storage) + offset, encoded, len(encoded))
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.SetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel.SetFileInformationByHandle.restype = wintypes.BOOL
    if not kernel.SetFileInformationByHandle(
        wintypes.HANDLE(msvcrt.get_osfhandle(fd)), 3, storage, len(storage)
    ):
        error = ctypes.get_last_error()
        if not replace and error in {80, 183}:
            raise _fail("DESTINATION_EXISTS")
        raise _fail("NOREPLACE_RENAME_FAILED")


def _windows_delete_handle(fd: int) -> None:
    if os.name != "nt":
        raise _fail("WINDOWS_BACKEND_UNAVAILABLE")
    import msvcrt

    _windows_mark_delete_native_handle(int(msvcrt.get_osfhandle(fd)))


def _posix_link_handle_noreplace(fd: int, parent_fd: int, final_name: str) -> None:
    if os.name == "nt":
        raise _fail("POSIX_BACKEND_UNAVAILABLE")
    libc = ctypes.CDLL(None, use_errno=True)
    libc.linkat.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    libc.linkat.restype = ctypes.c_int
    if libc.linkat(fd, b"", parent_fd, os.fsencode(final_name), 0x1000) != 0:
        error = ctypes.get_errno()
        if error == errno.EEXIST:
            raise _fail("DESTINATION_EXISTS")
        raise _fail("NOREPLACE_LINK_FAILED")


class _SecureFileLock:
    __slots__ = (
        "__weakref__",
        "__owner",
        "__relative_path",
        "__mode",
        "__fd",
        "__parent",
        "__identity_value",
        "__used",
        "__active",
        "__burned",
        "__issuer_nonce",
        "__security_digest",
    )

    def __init__(
        self,
        owner: "SecureAuthorityIO",
        relative_path: str | os.PathLike[str],
        mode: Literal["initial", "existing"],
        issuer_nonce: object,
    ) -> None:
        self.__owner = owner
        self.__relative_path = relative_path
        self.__mode = mode
        self.__fd: int | None = None
        self.__parent: _PinnedParent | None = None
        self.__identity_value: ArtifactIdentity | None = None
        self.__used = False
        self.__active = False
        self.__burned = False
        self.__issuer_nonce = issuer_nonce
        self.__security_digest: str | None = None

    @property
    def identity(self) -> ArtifactIdentity | None:
        return self.__identity_value

    def _validate_for(
        self,
        owner: "SecureAuthorityIO",
        issuer_nonce: object,
    ) -> ArtifactIdentity:
        if self.__burned:
            raise _fail("CAPABILITY_BURNED")
        if (
            self.__owner is not owner
            or self.__issuer_nonce is not issuer_nonce
            or not owner._lease_is_active(self)
            or not self.__active
            or self.__fd is None
            or self.__parent is None
            or self.__identity_value is None
        ):
            raise _fail("WRITER_LEASE_REQUIRED")
        try:
            self.__parent.verify()
            if _identity(os.fstat(self.__fd)) != self.__identity_value:
                raise _fail("WRITER_LEASE_CHANGED")
            if _identity(os.lstat(self.__parent.target)) != self.__identity_value:
                raise _fail("WRITER_LEASE_CHANGED")
            if _fd_security_digest(self.__fd) != self.__security_digest:
                raise _fail("WRITER_LEASE_CHANGED")
        except OSError:
            raise _fail("WRITER_LEASE_CHANGED") from None
        if not self.__parent.pinned:
            raise _fail("WRITER_ROOT_CHANGED")
        return self.__parent.pinned[0][2]

    def _burn_for(
        self,
        owner: "SecureAuthorityIO",
        issuer_nonce: object,
    ) -> ArtifactIdentity:
        identity = _SecureFileLock._validate_for(self, owner, issuer_nonce)
        self.__burned = True
        owner._release_writer_lease(self)
        return identity

    def _revoke_after_failure(
        self,
        owner: "SecureAuthorityIO",
        issuer_nonce: object,
    ) -> None:
        if (
            self.__owner is owner
            and self.__issuer_nonce is issuer_nonce
            and self.__active
        ):
            self.__burned = True
            owner._release_writer_lease(self)

    @_detached_public_error_boundary
    def __enter__(self) -> "_SecureFileLock":
        if self.__used or self.__burned:
            raise _fail("CAPABILITY_BURNED")
        self.__owner._require_issued_writer_lease(self, self.__issuer_nonce)
        self.__used = True
        parent = self.__owner._pin_parent(self.__relative_path)
        fd: int | None = None
        initial_lease: _TempLease | None = None
        initial_published = False
        initial_effect_unknown = False
        terminal_failure: BaseException | None = None
        try:
            self.__owner._stage("before_lock_open")
            if self.__mode == "initial":
                try:
                    os.lstat(parent.target)
                except FileNotFoundError:
                    pass
                except OSError:
                    raise _fail("LOCK_DESTINATION_LSTAT_FAILED") from None
                else:
                    raise _fail("LOCK_CREATE_COLLISION")
                initial_lease = self.__owner._write_temp(parent, b"\0", share_write=True)
                self.__owner._stage("before_initial_lock_publish")
                publish_state: Literal["OWNED", "FOREIGN_COLLISION", "UNKNOWN"] | None = None
                try:
                    self.__owner._rename_noreplace(parent, initial_lease)
                    initial_published = True
                except BaseException as publish_error:
                    publish_state = self.__owner._classify_failed_noreplace(
                        parent,
                        initial_lease,
                        publish_error,
                    )
                if publish_state == "FOREIGN_COLLISION":
                    raise _fail("LOCK_CREATE_COLLISION") from None
                if publish_state is not None:
                    initial_published = publish_state == "OWNED"
                    initial_effect_unknown = True
                    raise _fail(
                        "LOCK_INITIALIZATION_UNKNOWN",
                        completion_unknown=True,
                    ) from None
                try:
                    self.__owner._directory_durable(parent)
                except SecureAuthorityIOError:
                    self.__owner._rollback_owned_publish(parent, b"\0", initial_lease)
                    initial_published = False
                    try:
                        self.__owner._directory_durable(parent)
                    except SecureAuthorityIOError:
                        raise _fail("LOCK_INITIALIZATION_UNKNOWN", completion_unknown=True) from None
                    raise _fail("LOCK_INITIALIZE_FAILED") from None
                fd = initial_lease.fd
                current = _identity(os.fstat(fd))
                _require_regular(current)
                if self.__owner._read_fd(fd, current) != b"\0":
                    raise _fail("LOCK_MARKER_REJECTED")
            else:
                try:
                    fd = self.__owner._open_target(
                        parent,
                        writable=True,
                        share_write=True,
                    )
                except FileNotFoundError:
                    raise _fail("LOCK_NOT_FOUND") from None
                except SecureAuthorityIOError as open_error:
                    if open_error.code == "WINDOWS_SHARING_VIOLATION":
                        raise _fail("LOCK_BUSY") from None
                    raise
                current = self.__owner._bind_regular(parent, fd)
                if current.size != 1 or self.__owner._read_fd(fd, current) != b"\0":
                    raise _fail("LOCK_MARKER_REJECTED")
            self.__owner._lock_fd(fd)
            self.__security_digest = _fd_security_digest(fd)
            self.__owner._stage("lock_acquired")
            try:
                named = _identity(os.lstat(parent.target))
            except OSError:
                raise _fail("LOCK_IDENTITY_CHANGED") from None
            if named != current:
                raise _fail("LOCK_IDENTITY_CHANGED")
            parent.verify()
            self.__fd, self.__parent, self.__identity_value = fd, parent, current
            self.__active = True
            self.__owner._activate_writer_lease(self, self.__issuer_nonce)
            if initial_lease is not None:
                initial_lease = None
            return self
        except BaseException as caught_failure:
            primary_failure = caught_failure
            self.__owner._release_writer_lease(self)
            self.__active = False
            cleanup_unknown = False
            if initial_lease is not None:
                if initial_published:
                    try:
                        self.__owner._rollback_owned_publish(parent, b"\0", initial_lease)
                    except SecureAuthorityIOError:
                        cleanup_unknown = True
                        try:
                            self.__owner._cleanup_temp(parent, initial_lease)
                        except SecureAuthorityIOError:
                            cleanup_unknown = True
                else:
                    try:
                        self.__owner._cleanup_temp(parent, initial_lease)
                    except SecureAuthorityIOError:
                        cleanup_unknown = True
                try:
                    self.__owner._directory_durable(parent)
                except SecureAuthorityIOError:
                    cleanup_unknown = True
                try:
                    initial_lease.close()
                except SecureAuthorityIOError:
                    cleanup_unknown = True
                fd = None
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    cleanup_unknown = True
            try:
                parent.close()
            except SecureAuthorityIOError:
                cleanup_unknown = True
            if initial_effect_unknown:
                terminal_failure = _fail("LOCK_INITIALIZATION_UNKNOWN", completion_unknown=True)
            elif cleanup_unknown:
                code = "LOCK_INITIALIZATION_UNKNOWN" if initial_lease is not None else "LOCK_CLEANUP_UNKNOWN"
                terminal_failure = _fail(code, completion_unknown=True)
            else:
                terminal_failure = primary_failure
        if terminal_failure is None:
            raise _fail("LOCK_CLEANUP_UNKNOWN", completion_unknown=True)
        raise terminal_failure from None

    @_detached_public_error_boundary
    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        failures: list[SecureAuthorityIOError] = []
        if self.__fd is not None:
            if self.__identity_value is not None:
                try:
                    if _identity(os.lstat(self.__parent.target)) != self.__identity_value:
                        failures.append(_fail("LOCK_IDENTITY_CHANGED"))
                except OSError:
                    failures.append(_fail("LOCK_IDENTITY_CHANGED"))
            try:
                if _fd_security_digest(self.__fd) != self.__security_digest:
                    failures.append(_fail("LOCK_SECURITY_DRIFT"))
            except SecureAuthorityIOError as security_error:
                failures.append(security_error)
            try:
                self.__owner._unlock_fd(self.__fd)
            except SecureAuthorityIOError as unlock_error:
                failures.append(unlock_error)
            try:
                os.close(self.__fd)
            except OSError:
                failures.append(_fail("HANDLE_CLOSE_FAILED"))
        if self.__parent is not None:
            try:
                self.__parent.close()
            except SecureAuthorityIOError as parent_error:
                failures.append(parent_error)
        self.__owner._release_writer_lease(self)
        self.__fd = None
        self.__parent = None
        self.__active = False
        if failures:
            if (
                exc_type is not None
                or len(failures) > 1
                or any(failure.completion_unknown for failure in failures)
            ):
                raise _fail("LOCK_CLEANUP_UNKNOWN", completion_unknown=True)
            raise failures[0]
        return False


class SecureAuthorityIO:
    """Root-bound, fail-closed I/O for authority artifacts.

    The class performs no I/O at construction time. Every effect pins the root
    and each ancestor, refuses reparse/symlink and multi-link files, and verifies
    identities again after the operation.

    This is an API-boundary control, not a sandbox against arbitrary hostile
    Python running in this same interpreter.  Code able to inspect or mutate
    private object state can also monkeypatch this module or the runtime; that
    requires process or native isolation outside this Product-local API.
    """

    def __init__(
        self,
        root: str | os.PathLike[str],
        *,
        max_bytes: int = _DEFAULT_MAX_BYTES,
        max_json_depth: int = _DEFAULT_MAX_DEPTH,
        max_json_nodes: int = _DEFAULT_MAX_NODES,
        immutable_plan_verifier: ImmutablePlanVerifier | None = None,
        immutable_receipt_verifier: ImmutableReceiptVerifier | None = None,
        immutable_graph_verifier: ImmutableGraphVerifier | None = None,
        authority_instance_id: str | None = None,
        _stage_hook: StageHook | None = None,
    ) -> None:
        bounds = (
            (max_bytes, _DEFAULT_MAX_BYTES),
            (max_json_depth, _DEFAULT_MAX_DEPTH),
            (max_json_nodes, _DEFAULT_MAX_NODES),
        )
        if any(type(value) is not int or not 1 <= value <= ceiling for value, ceiling in bounds):
            raise _fail("BOUND_REJECTED")
        if (immutable_plan_verifier is None) != (authority_instance_id is None):
            raise _fail("TRUSTED_PLAN_CONFIGURATION_REJECTED")
        if immutable_plan_verifier is not None and not callable(immutable_plan_verifier):
            raise _fail("TRUSTED_PLAN_CONFIGURATION_REJECTED")
        if immutable_receipt_verifier is not None and (
            immutable_plan_verifier is None or not callable(immutable_receipt_verifier)
        ):
            raise _fail("TRUSTED_PLAN_CONFIGURATION_REJECTED")
        if immutable_graph_verifier is not None and (
            immutable_plan_verifier is None
            or immutable_receipt_verifier is None
            or not callable(immutable_graph_verifier)
        ):
            raise _fail("TRUSTED_PLAN_CONFIGURATION_REJECTED")
        if authority_instance_id is not None and not _bounded_identifier(authority_instance_id):
            raise _fail("TRUSTED_PLAN_CONFIGURATION_REJECTED")
        self._root = Path(os.path.abspath(os.fspath(root)))
        self._max_bytes = max_bytes
        self._max_json_depth = max_json_depth
        self._max_json_nodes = max_json_nodes
        self._immutable_plan_verifier = immutable_plan_verifier
        self._immutable_receipt_verifier = immutable_receipt_verifier
        self._immutable_graph_verifier = immutable_graph_verifier
        self._authority_instance_id = authority_instance_id
        self._stage_hook = _stage_hook
        self.__lease_issuer_nonce = object()
        self.__issued_leases: weakref.WeakKeyDictionary[_SecureFileLock, str] = (
            weakref.WeakKeyDictionary()
        )

    def _stage(self, name: str) -> None:
        if self._stage_hook is not None:
            self._stage_hook(name)

    def _cleanup_failed_open(self, fd: int, *, delete_created: bool) -> None:
        cleanup_failed = False
        if delete_created and os.name == "nt":
            try:
                _windows_delete_handle(fd)
            except (OSError, SecureAuthorityIOError):
                cleanup_failed = True
        try:
            os.close(fd)
        except OSError:
            cleanup_failed = True
        if cleanup_failed:
            raise _fail("HANDLE_CLEANUP_UNKNOWN", completion_unknown=True) from None

    def _open_directory(self, path: Path, *, parent_fd: int | None = None, name: str | None = None) -> int:
        fd: int | None = None
        try:
            if os.name == "nt":
                fd = _windows_open(path, writable=False, create_new=False, directory=True)
            else:
                flags = _open_flags() | int(getattr(os, "O_DIRECTORY", 0))
                fd = os.open(name or os.fspath(path), flags, dir_fd=parent_fd)
            _set_noninheritable(fd)
            return fd
        except SecureAuthorityIOError:
            if fd is not None:
                self._cleanup_failed_open(fd, delete_created=False)
            raise
        except OSError:
            if fd is not None:
                self._cleanup_failed_open(fd, delete_created=False)
            raise _fail("ANCESTOR_OPEN_FAILED") from None

    def _pin_parent(self, relative_path: str | os.PathLike[str]) -> _PinnedParent:
        parts = _relative_parts(relative_path)
        target = self._root.joinpath(*parts)
        pinned: list[tuple[Path, int, ArtifactIdentity, str]] = []
        current_path = self._root
        parent_fd: int | None = None
        opened_fd: int | None = None
        try:
            for index, component in enumerate((None, *parts[:-1])):
                if index > 0:
                    current_path = current_path / str(component)
                try:
                    named = _identity(os.lstat(current_path))
                except OSError:
                    raise _fail("ANCESTOR_LSTAT_FAILED") from None
                _require_directory(named)
                opened_fd = self._open_directory(
                    current_path,
                    parent_fd=parent_fd if os.name != "nt" else None,
                    name=str(component) if index > 0 and os.name != "nt" else None,
                )
                opened = _identity(os.fstat(opened_fd))
                _require_directory(opened)
                if named != opened:
                    os.close(opened_fd)
                    opened_fd = None
                    raise _fail("ANCESTOR_BINDING_MISMATCH")
                security = _fd_security_digest(opened_fd)
                pinned.append((current_path, opened_fd, opened, security))
                parent_fd = opened_fd
                opened_fd = None
            return _PinnedParent(self._root, target, parts[-1], parent_fd, pinned)
        except BaseException:
            cleanup_failed = False
            if opened_fd is not None:
                try:
                    os.close(opened_fd)
                except OSError:
                    cleanup_failed = True
            for _, fd, _, _ in reversed(pinned):
                try:
                    os.close(fd)
                except OSError:
                    cleanup_failed = True
            if cleanup_failed:
                raise _fail("HANDLE_CLEANUP_UNKNOWN", completion_unknown=True) from None
            raise

    def _open_target(
        self,
        parent: _PinnedParent,
        *,
        writable: bool,
        create_new: bool = False,
        delete_access: bool = False,
        share_write: bool = False,
    ) -> int:
        fd: int | None = None
        try:
            if os.name == "nt":
                fd = _windows_open(
                    parent.target,
                    writable=writable,
                    create_new=create_new,
                    directory=False,
                    delete_access=delete_access,
                    share_write=share_write,
                )
            else:
                fd = os.open(
                    parent.name,
                    _open_flags(writable=writable, create=create_new, exclusive=create_new),
                    0o600,
                    dir_fd=parent.parent_fd,
                )
            _set_noninheritable(fd)
            return fd
        except (FileExistsError, FileNotFoundError):
            raise
        except SecureAuthorityIOError:
            if fd is not None:
                self._cleanup_failed_open(fd, delete_created=create_new)
            raise
        except OSError:
            if fd is not None:
                self._cleanup_failed_open(fd, delete_created=create_new)
            raise _fail("OPEN_FAILED") from None

    def _bind_regular(self, parent: _PinnedParent, fd: int) -> ArtifactIdentity:
        try:
            opened = _identity(os.fstat(fd))
            named = _identity(os.lstat(parent.target))
        except OSError:
            raise _fail("FILE_IDENTITY_FAILED") from None
        _require_regular(opened)
        _require_regular(named)
        if opened != named:
            raise _fail("FILE_BINDING_MISMATCH")
        return opened

    def _namespace_security_commitment(
        self,
        parent: _PinnedParent,
        fd: int,
        target_identity: ArtifactIdentity,
    ) -> str:
        parent.verify()
        try:
            current = _identity(os.fstat(fd))
        except OSError:
            raise _fail("FILE_IDENTITY_FAILED") from None
        if current != target_identity:
            raise _fail("FILE_IDENTITY_CHANGED")
        target_security = _fd_security_digest(fd)
        ancestors = [
            {
                "device": identity.device,
                "file_type": stat.S_IFMT(identity.mode),
                "index": index,
                "inode": identity.inode,
                "reparse_point": identity.reparse_point,
                "security_sha256": security,
            }
            for index, (_, _, identity, security) in enumerate(parent.pinned)
        ]
        payload = json.dumps(
            {
                "ancestors": ancestors,
                "target": {
                    **_identity_binding(target_identity),
                    "security_sha256": target_security,
                },
                "version": _IMMUTABLE_RECEIPT_VERSION,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        parent.verify()
        if _fd_security_digest(fd) != target_security:
            raise _fail("FILE_SECURITY_DRIFT")
        return _sha256(payload)

    def _read_fd(self, fd: int, identity: ArtifactIdentity) -> bytes:
        if identity.size > self._max_bytes:
            raise _fail("BYTE_BOUND_EXCEEDED")
        chunks: list[bytes] = []
        total = 0
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            while True:
                chunk = os.read(fd, min(65536, self._max_bytes + 1 - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > self._max_bytes:
                    raise _fail("BYTE_BOUND_EXCEEDED")
        except SecureAuthorityIOError:
            raise
        except OSError:
            raise _fail("READ_FAILED") from None
        payload = b"".join(chunks)
        if len(payload) != identity.size:
            raise _fail("READ_SIZE_CHANGED")
        return payload

    def _read_bytes(
        self, relative_path: str | os.PathLike[str]
    ) -> tuple[bytes, ArtifactIdentity, str]:
        parent = self._pin_parent(relative_path)
        fd: int | None = None
        try:
            self._stage("ancestors_pinned")
            try:
                before = _identity(os.lstat(parent.target))
            except FileNotFoundError:
                raise _fail("NOT_FOUND") from None
            except OSError:
                raise _fail("FILE_LSTAT_FAILED") from None
            _require_regular(before)
            self._stage("target_lstat_complete")
            fd = self._open_target(parent, writable=False)
            self._stage("target_open_complete")
            opened = _identity(os.fstat(fd))
            _require_regular(opened)
            if before != opened:
                raise _fail("FILE_BINDING_MISMATCH")
            security_digest = self._namespace_security_commitment(parent, fd, before)
            self._stage("target_fstat_complete")
            self._stage("read_bound")
            payload = self._read_fd(fd, before)
            self._stage("read_complete")
            after = _identity(os.fstat(fd))
            self._stage("post_fstat_complete")
            named = _identity(os.lstat(parent.target))
            self._stage("post_lstat_complete")
            if before != after or before != named:
                raise _fail("FILE_IDENTITY_CHANGED")
            if self._namespace_security_commitment(parent, fd, before) != security_digest:
                raise _fail("FILE_SECURITY_DRIFT")
            parent.verify()
            return payload, before, security_digest
        except FileNotFoundError:
            raise _fail("NOT_FOUND") from None
        except OSError:
            raise _fail("READ_FAILED") from None
        finally:
            close_failures: list[SecureAuthorityIOError] = []
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    close_failures.append(_fail("HANDLE_CLOSE_FAILED"))
            try:
                parent.close()
            except SecureAuthorityIOError as exc:
                close_failures.append(exc)
            if close_failures:
                if len(close_failures) > 1 or any(
                    failure.completion_unknown for failure in close_failures
                ):
                    raise _fail("HANDLE_CLEANUP_UNKNOWN", completion_unknown=True)
                raise close_failures[0]

    @_detached_public_error_boundary
    def read_json(self, relative_path: str | os.PathLike[str]) -> SecureJsonRead:
        payload, identity, security_sha256 = self._read_bytes(relative_path)
        document = _strict_json(
            payload,
            max_depth=self._max_json_depth,
            max_nodes=self._max_json_nodes,
        )
        return SecureJsonRead(
            document,
            _sha256(payload),
            len(payload),
            identity,
            security_sha256,
        )

    @_detached_public_error_boundary
    def lock(
        self,
        relative_path: str | os.PathLike[str],
        *,
        mode: Literal["initial", "existing"],
    ) -> _SecureFileLock:
        if mode not in {"initial", "existing"}:
            raise _fail("LOCK_MODE_REJECTED")
        lease = _SecureFileLock(
            self,
            relative_path,
            mode,
            self.__lease_issuer_nonce,
        )
        self.__issued_leases[lease] = "ISSUED"
        return lease

    def _activate_writer_lease(
        self,
        lease: _SecureFileLock,
        issuer_nonce: object,
    ) -> None:
        if (
            type(lease) is not _SecureFileLock
            or issuer_nonce is not self.__lease_issuer_nonce
            or self.__issued_leases.get(lease) != "ISSUED"
        ):
            raise _fail("WRITER_LEASE_REQUIRED")
        self.__issued_leases[lease] = "ACTIVE"

    def _require_issued_writer_lease(
        self,
        lease: _SecureFileLock,
        issuer_nonce: object,
    ) -> None:
        if (
            type(lease) is not _SecureFileLock
            or issuer_nonce is not self.__lease_issuer_nonce
            or self.__issued_leases.get(lease) != "ISSUED"
        ):
            raise _fail("WRITER_LEASE_REQUIRED")

    def _lease_is_active(self, lease: _SecureFileLock) -> bool:
        return self.__issued_leases.get(lease) == "ACTIVE"

    def _release_writer_lease(self, lease: _SecureFileLock) -> None:
        self.__issued_leases.pop(lease, None)

    def _require_writer_lease(self, lease: _SecureFileLock) -> ArtifactIdentity:
        if type(lease) is not _SecureFileLock:
            raise _fail("WRITER_LEASE_REQUIRED")
        return _SecureFileLock._validate_for(
            lease,
            self,
            self.__lease_issuer_nonce,
        )

    def _burn_writer_lease(self, lease: _SecureFileLock) -> ArtifactIdentity:
        if type(lease) is not _SecureFileLock:
            raise _fail("WRITER_LEASE_REQUIRED")
        try:
            return _SecureFileLock._burn_for(
                lease,
                self,
                self.__lease_issuer_nonce,
            )
        except BaseException:
            _SecureFileLock._revoke_after_failure(
                lease,
                self,
                self.__lease_issuer_nonce,
            )
            raise

    def _revoke_writer_lease_after_failure(self, lease: _SecureFileLock) -> None:
        if type(lease) is _SecureFileLock:
            _SecureFileLock._revoke_after_failure(
                lease,
                self,
                self.__lease_issuer_nonce,
            )

    def _bind_writer_parent(
        self,
        lease: _SecureFileLock,
        parent: _PinnedParent,
    ) -> None:
        expected_root = self._require_writer_lease(lease)
        parent.verify()
        if (
            not parent.pinned
            or not _same_ancestor_object(parent.pinned[0][2], expected_root)
        ):
            raise _fail("WRITER_ROOT_CHANGED")
        # Revalidate the lease after the effect parent is pinned. Subsequent
        # POSIX namespace operations use the pinned dirfd; Windows ancestors
        # remain open without delete sharing for the critical section.
        if not _same_ancestor_object(self._require_writer_lease(lease), expected_root):
            raise _fail("WRITER_ROOT_CHANGED")
        parent.verify()

    def _lock_fd(self, fd: int) -> None:
        try:
            if os.name == "nt":
                import msvcrt
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                raise _fail("LOCK_BUSY") from None
            raise _fail("LOCK_ACQUIRE_FAILED") from None

    def _unlock_fd(self, fd: int) -> None:
        try:
            if os.name == "nt":
                import msvcrt
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            raise _fail("LOCK_RELEASE_FAILED") from None

    def _write_temp(
        self,
        parent: _PinnedParent,
        payload: bytes,
        *,
        share_write: bool = False,
    ) -> _TempLease:
        if len(payload) > self._max_bytes:
            raise _fail("BYTE_BOUND_EXCEEDED")
        if os.name != "nt":
            if parent.parent_fd is None or not getattr(os, "O_TMPFILE", 0):
                raise _fail("UNNAMED_TEMP_UNAVAILABLE")
            fd: int | None = None
            try:
                fd = os.open(
                    ".",
                    os.O_RDWR | int(getattr(os, "O_CLOEXEC", 0)) | os.O_TMPFILE,
                    0o600,
                    dir_fd=parent.parent_fd,
                )
                _set_noninheritable(fd)
            except SecureAuthorityIOError:
                if fd is not None:
                    self._cleanup_failed_open(fd, delete_created=False)
                raise
            except OSError:
                if fd is not None:
                    self._cleanup_failed_open(fd, delete_created=False)
                raise _fail("UNNAMED_TEMP_UNAVAILABLE") from None
            name: str | None = None
            path: Path | None = None
        else:
            for _ in range(8):
                name = f".authority-{secrets.token_hex(16)}.tmp"
                path = parent.target.parent / name
                temp_parent = _PinnedParent(parent.root, path, name, parent.parent_fd, parent.pinned)
                try:
                    fd = self._open_target(
                        temp_parent,
                        writable=True,
                        create_new=True,
                        delete_access=True,
                        share_write=share_write,
                    )
                    break
                except FileExistsError:
                    continue
            else:
                raise _fail("TEMP_NAMESPACE_EXHAUSTED")
        try:
            if os.name == "nt":
                initial = self._bind_regular(temp_parent, fd)
            else:
                initial = _identity(os.fstat(fd))
                _require_regular(initial, allow_zero_links=True)
            if initial.size != 0:
                raise _fail("TEMP_NOT_EMPTY")
            view = memoryview(payload)
            try:
                while view:
                    written = os.write(fd, view)
                    if written <= 0:
                        raise OSError
                    view = view[written:]
            except OSError:
                raise _fail("WRITE_FAILED") from None
            try:
                written_identity = _identity(os.fstat(fd))
            except OSError:
                raise _fail("TEMP_IDENTITY_FAILED") from None
            _require_regular(written_identity, allow_zero_links=os.name != "nt")
            if written_identity.size != len(payload):
                raise _fail("WRITE_SIZE_CHANGED")
            try:
                os.fsync(fd)
            except OSError:
                raise _fail("FILE_DURABILITY_FAILED") from None
            os.lseek(fd, 0, os.SEEK_SET)
            if self._read_fd(fd, written_identity) != payload:
                raise _fail("WRITE_READBACK_MISMATCH")
            self._stage("temp_durable")
            return _TempLease(name, path, fd, written_identity, _sha256(payload))
        except BaseException:
            cleanup_failed = False
            try:
                if os.name == "nt":
                    _windows_delete_handle(fd)
            except (OSError, SecureAuthorityIOError):
                cleanup_failed = True
            try:
                os.close(fd)
            except OSError:
                cleanup_failed = True
            if cleanup_failed:
                raise _fail("TEMP_CLEANUP_UNKNOWN", completion_unknown=True) from None
            raise

    def _rename_noreplace(self, parent: _PinnedParent, lease: _TempLease) -> None:
        self._validate_temp_lease(parent, lease)
        if os.name == "nt":
            if parent.parent_fd is None:
                raise _fail("PARENT_HANDLE_MISSING")
            _windows_rename_handle(
                lease.fd,
                parent.target,
                replace=False,
            )
        else:
            if parent.parent_fd is None:
                raise _fail("PARENT_HANDLE_MISSING")
            _posix_link_handle_noreplace(lease.fd, parent.parent_fd, parent.name)

    def _classify_failed_noreplace(
        self,
        parent: _PinnedParent,
        lease: _TempLease,
        failure: BaseException,
    ) -> Literal["OWNED", "FOREIGN_COLLISION", "UNKNOWN"]:
        """Classify a failure that may have happened after namespace commit.

        The native no-replace primitive and Python's next assignment are not a
        single operation.  A helper fault or asynchronous exception can arrive
        after the native effect but before the caller records it.  Only an
        exact foreign destination paired with the native collision result is a
        confirmed no-effect outcome; every other ambiguous observation stays
        completion-unknown.
        """

        try:
            live = _identity(os.fstat(lease.fd))
            named = _identity(os.lstat(parent.target))
            parent.verify()
        except BaseException:
            return "UNKNOWN"
        live_is_owned = _same_file_object(live, lease.identity)
        if live_is_owned and _same_file_object(named, live):
            return "OWNED"
        if (
            live == lease.identity
            and not _same_file_object(named, live)
            and isinstance(failure, SecureAuthorityIOError)
            and failure.code == "DESTINATION_EXISTS"
        ):
            return "FOREIGN_COLLISION"
        return "UNKNOWN"

    def _validate_temp_lease(self, parent: _PinnedParent, lease: _TempLease) -> None:
        if lease.closed:
            raise _fail("TEMP_CAPABILITY_BURNED")
        try:
            live = _identity(os.fstat(lease.fd))
        except OSError:
            raise _fail("TEMP_IDENTITY_CHANGED") from None
        if live != lease.identity:
            raise _fail("TEMP_IDENTITY_CHANGED")
        if lease.path is not None:
            try:
                named = _identity(os.lstat(lease.path))
            except OSError:
                raise _fail("TEMP_IDENTITY_CHANGED") from None
            if named != lease.identity:
                raise _fail("TEMP_IDENTITY_CHANGED")
        parent.verify()

    def _unlink_live_name(
        self,
        parent: _PinnedParent,
        name: str,
        fd: int,
        expected: ArtifactIdentity,
    ) -> None:
        if os.name != "nt":
            raise _fail("HANDLE_BOUND_DELETE_UNAVAILABLE")
        try:
            live = _identity(os.fstat(fd))
            named = _identity(os.lstat(parent.target.parent / name))
        except OSError:
            raise _fail("DELETE_IDENTITY_CHANGED") from None
        try:
            _require_regular(live)
            _require_regular(named)
        except SecureAuthorityIOError:
            raise _fail("DELETE_IDENTITY_CHANGED") from None
        if live != expected or named != expected:
            raise _fail("DELETE_IDENTITY_CHANGED")
        self._stage("before_live_unlink")
        try:
            final_named = _identity(os.lstat(parent.target.parent / name))
            _require_regular(final_named)
            if final_named != expected:
                raise _fail("DELETE_IDENTITY_CHANGED")
            _windows_delete_handle(fd)
        except SecureAuthorityIOError:
            raise
        except OSError:
            raise _fail("HANDLE_BOUND_DELETE_FAILED") from None

    def _directory_durable(self, parent: _PinnedParent) -> None:
        if os.name == "nt":
            import msvcrt

            fd: int | None = None
            try:
                fd = _windows_open(
                    parent.target.parent,
                    writable=True,
                    create_new=False,
                    directory=True,
                )
                ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
                ntdll.NtFlushBuffersFile.argtypes = [
                    wintypes.HANDLE,
                    ctypes.POINTER(_WindowsIoStatusBlock),
                ]
                ntdll.NtFlushBuffersFile.restype = ctypes.c_long
                iosb = _WindowsIoStatusBlock()
                status = int(
                    ntdll.NtFlushBuffersFile(
                        wintypes.HANDLE(msvcrt.get_osfhandle(fd)), ctypes.byref(iosb)
                    )
                )
                if status < 0:
                    raise _fail("DIRECTORY_DURABILITY_FAILED")
            except SecureAuthorityIOError:
                raise
            except OSError:
                raise _fail("DIRECTORY_DURABILITY_FAILED") from None
            finally:
                if fd is not None:
                    try:
                        os.close(fd)
                    except OSError:
                        raise _fail("HANDLE_CLOSE_FAILED") from None
        else:
            try:
                if parent.parent_fd is None:
                    raise OSError
                os.fsync(parent.parent_fd)
            except OSError:
                raise _fail("DIRECTORY_DURABILITY_FAILED") from None

    def _verify_published(
        self,
        parent: _PinnedParent,
        expected_payload: bytes,
        lease: _TempLease,
    ) -> tuple[ArtifactIdentity, str]:
        try:
            current = _identity(os.fstat(lease.fd))
            named = _identity(os.lstat(parent.target))
            _require_regular(current)
            _require_regular(named)
            if not _same_file_object(current, lease.identity) or current != named:
                raise _fail("PUBLISHED_INODE_MISMATCH")
            security_sha256 = self._namespace_security_commitment(
                parent,
                lease.fd,
                current,
            )
            if self._read_fd(lease.fd, current) != expected_payload:
                raise _fail("PUBLISHED_BYTES_MISMATCH")
            self._stage("published_readback_complete")
            after = _identity(os.fstat(lease.fd))
            named = _identity(os.lstat(parent.target))
            if current != after or current != named:
                raise _fail("PUBLISHED_IDENTITY_CHANGED")
            if (
                self._namespace_security_commitment(parent, lease.fd, current)
                != security_sha256
            ):
                raise _fail("PUBLISHED_SECURITY_CHANGED")
            return current, security_sha256
        except OSError:
            raise _fail("PUBLISHED_IDENTITY_CHANGED") from None

    def _rollback_owned_publish(
        self,
        parent: _PinnedParent,
        expected_payload: bytes,
        lease: _TempLease,
    ) -> None:
        if os.name != "nt":
            raise _fail("PUBLISH_ROLLBACK_UNAVAILABLE", completion_unknown=True)
        try:
            current = _identity(os.fstat(lease.fd))
            named = _identity(os.lstat(parent.target))
            if (
                not _same_file_object(current, lease.identity)
                or current != named
                or self._read_fd(lease.fd, current) != expected_payload
            ):
                raise _fail("PUBLISH_ROLLBACK_OWNERSHIP_CHANGED")
        except OSError:
            raise _fail("PUBLISH_ROLLBACK_OWNERSHIP_CHANGED") from None
        self._unlink_live_name(parent, parent.name, lease.fd, current)

    def _snapshot_immutable_plan(
        self,
        plan: TrustedImmutablePlan,
    ) -> _ValidatedImmutablePlan:
        if type(plan) is not TrustedImmutablePlan:
            raise _fail("TRUSTED_GENERATION_PLAN_REQUIRED")
        first = (
            plan.relative_path,
            plan.operation_id,
            plan.revision,
            plan.body_sha256,
            plan.expected_predecessor_sha256,
            plan.action,
            plan.build_id,
            plan.backend_id,
            plan.session_id,
            plan.instance_id,
            plan.authorization,
        )
        second = (
            plan.relative_path,
            plan.operation_id,
            plan.revision,
            plan.body_sha256,
            plan.expected_predecessor_sha256,
            plan.action,
            plan.build_id,
            plan.backend_id,
            plan.session_id,
            plan.instance_id,
            plan.authorization,
        )
        if first != second:
            raise _fail("TRUSTED_GENERATION_PLAN_CHANGED")
        snapshot = TrustedImmutablePlan(*first)
        parts = _relative_parts(snapshot.relative_path)
        if (
            len(parts) != 2
            or parts[0] != _IMMUTABLE_NAMESPACE
            or not _bounded_identifier(parts[1])
        ):
            raise _fail("IMMUTABLE_COORDINATE_REJECTED")
        if (
            type(snapshot.operation_id) is not str
            or len(snapshot.operation_id) != 32
            or snapshot.operation_id != snapshot.operation_id.lower()
            or any(
                character not in "0123456789abcdef"
                for character in snapshot.operation_id
            )
        ):
            raise _fail("IMMUTABLE_OPERATION_ID_REJECTED")
        if (
            type(snapshot.revision) is not int
            or not 1 <= snapshot.revision <= _MAX_IMMUTABLE_REVISION
        ):
            raise _fail("IMMUTABLE_REVISION_REJECTED")
        if not _is_sha256(snapshot.body_sha256) or not _is_sha256(
            snapshot.expected_predecessor_sha256
        ):
            raise _fail("IMMUTABLE_DIGEST_REJECTED")
        if type(snapshot.action) is not str or snapshot.action not in {
            "GENERATION",
            "COMMIT",
            "TOMBSTONE",
            "ABORT",
            "COMPENSATE",
        }:
            raise _fail("IMMUTABLE_ACTION_REJECTED")
        identifiers = (
            snapshot.build_id,
            snapshot.backend_id,
            snapshot.session_id,
            snapshot.instance_id,
            snapshot.authorization,
        )
        if not all(_bounded_identifier(value) for value in identifiers):
            raise _fail("IMMUTABLE_BINDING_REJECTED")
        if (
            self._immutable_plan_verifier is None
            or self._authority_instance_id is None
            or snapshot.instance_id != self._authority_instance_id
        ):
            raise _fail("TRUSTED_GENERATION_PLAN_REQUIRED")
        fingerprint_payload = json.dumps(
            {
                "action": snapshot.action,
                "authorization_sha256": _sha256(snapshot.authorization.encode("ascii")),
                "backend_id": snapshot.backend_id,
                "body_sha256": snapshot.body_sha256,
                "build_id": snapshot.build_id,
                "expected_predecessor_sha256": snapshot.expected_predecessor_sha256,
                "instance_id": snapshot.instance_id,
                "operation_id": snapshot.operation_id,
                "relative_path": "/".join(parts),
                "revision": snapshot.revision,
                "session_id": snapshot.session_id,
                "version": _IMMUTABLE_PLAN_VERSION,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        fingerprint = _sha256(fingerprint_payload)
        return _ValidatedImmutablePlan(snapshot, parts, fingerprint)

    def _admit_immutable_plan(
        self,
        plan: _ValidatedImmutablePlan,
    ) -> _ValidatedImmutablePlan:
        snapshot = plan.snapshot
        verifier_snapshot = TrustedImmutablePlan(
            snapshot.relative_path,
            snapshot.operation_id,
            snapshot.revision,
            snapshot.body_sha256,
            snapshot.expected_predecessor_sha256,
            snapshot.action,
            snapshot.build_id,
            snapshot.backend_id,
            snapshot.session_id,
            snapshot.instance_id,
            snapshot.authorization,
        )
        verifier = self._immutable_plan_verifier
        if verifier is None:
            raise _fail("TRUSTED_GENERATION_PLAN_REQUIRED")
        try:
            accepted = verifier(
                verifier_snapshot,
                plan.fingerprint,
            )
        except Exception:
            raise _fail("TRUSTED_GENERATION_PLAN_REJECTED") from None
        if accepted is not True:
            raise _fail("TRUSTED_GENERATION_PLAN_REJECTED")
        return plan

    def _validate_immutable_plan(
        self,
        plan: TrustedImmutablePlan,
    ) -> _ValidatedImmutablePlan:
        return self._admit_immutable_plan(self._snapshot_immutable_plan(plan))

    def _snapshot_immutable_receipt(
        self,
        receipt: ImmutablePublishReceipt,
    ) -> ImmutablePublishReceipt:
        if type(receipt) is not ImmutablePublishReceipt:
            raise _fail("TRUSTED_IMMUTABLE_RECEIPT_REQUIRED")
        first = (
            receipt.sha256,
            receipt.predecessor_sha256,
            receipt.byte_count,
            receipt.identity,
            receipt.plan_fingerprint,
            receipt.security_sha256,
            receipt.receipt_fingerprint,
            receipt.version,
        )
        second = (
            receipt.sha256,
            receipt.predecessor_sha256,
            receipt.byte_count,
            receipt.identity,
            receipt.plan_fingerprint,
            receipt.security_sha256,
            receipt.receipt_fingerprint,
            receipt.version,
        )
        if (
            first[:3] != second[:3]
            or first[3] is not second[3]
            or first[4:] != second[4:]
        ):
            raise _fail("IMMUTABLE_RECEIPT_CHANGED")
        identity = _snapshot_artifact_identity(first[3])
        return ImmutablePublishReceipt(
            sha256=first[0],
            predecessor_sha256=first[1],
            byte_count=first[2],
            identity=identity,
            plan_fingerprint=first[4],
            security_sha256=first[5],
            receipt_fingerprint=first[6],
            version=first[7],
        )

    def _validate_immutable_receipt(
        self,
        plan: _ValidatedImmutablePlan,
        receipt: ImmutablePublishReceipt,
    ) -> _ValidatedImmutableReceipt:
        snapshot = self._snapshot_immutable_receipt(receipt)
        if (
            snapshot.version != _IMMUTABLE_RECEIPT_VERSION
            or not _is_sha256(snapshot.sha256)
            or not _is_sha256(snapshot.predecessor_sha256)
            or type(snapshot.byte_count) is not int
            or snapshot.byte_count < 0
            or snapshot.byte_count > self._max_bytes
            or snapshot.byte_count != snapshot.identity.size
            or not _is_sha256(snapshot.plan_fingerprint)
            or not _is_sha256(snapshot.security_sha256)
            or not _is_sha256(snapshot.receipt_fingerprint)
        ):
            raise _fail("IMMUTABLE_RECEIPT_REJECTED")
        if (
            snapshot.sha256 != plan.snapshot.body_sha256
            or snapshot.predecessor_sha256
            != plan.snapshot.expected_predecessor_sha256
            or snapshot.plan_fingerprint != plan.fingerprint
        ):
            raise _fail("IMMUTABLE_BINDING_MISMATCH")
        fingerprint = _immutable_receipt_fingerprint(
            sha256=snapshot.sha256,
            predecessor_sha256=snapshot.predecessor_sha256,
            byte_count=snapshot.byte_count,
            identity=snapshot.identity,
            plan_fingerprint=snapshot.plan_fingerprint,
            security_sha256=snapshot.security_sha256,
            version=snapshot.version,
        )
        if fingerprint != snapshot.receipt_fingerprint:
            raise _fail("IMMUTABLE_RECEIPT_REJECTED")
        if self._immutable_receipt_verifier is None:
            raise _fail("TRUSTED_IMMUTABLE_RECEIPT_REQUIRED")
        try:
            accepted = self._immutable_receipt_verifier(fingerprint)
        except Exception:
            raise _fail("TRUSTED_IMMUTABLE_RECEIPT_REJECTED") from None
        if accepted is not True:
            raise _fail("TRUSTED_IMMUTABLE_RECEIPT_REJECTED")
        return _ValidatedImmutableReceipt(snapshot, fingerprint)

    def _reject_reserved_immutable_parent(
        self,
        parent: _PinnedParent,
        parts: tuple[str, ...],
        lease: _SecureFileLock,
    ) -> None:
        if len(parts) < 2 or os.name != "nt":
            return
        self._stage("raw_parent_pinned")
        try:
            os.lstat(self._root / _IMMUTABLE_NAMESPACE)
        except FileNotFoundError:
            return
        except OSError:
            raise _fail("IMMUTABLE_NAMESPACE_CLASSIFICATION_FAILED") from None
        self._stage("before_reserved_namespace_pin")
        try:
            reserved = self._pin_parent(
                f"{_IMMUTABLE_NAMESPACE}/.classification-only"
            )
        except SecureAuthorityIOError as exc:
            if exc.completion_unknown:
                raise
            raise _fail("IMMUTABLE_NAMESPACE_CLASSIFICATION_FAILED") from None
        try:
            self._bind_writer_parent(lease, reserved)
            self._stage("reserved_namespace_pinned")
            parent.verify()
            if (
                len(parent.pinned) < 2
                or not reserved.pinned
                or _same_ancestor_object(
                    parent.pinned[1][2], reserved.pinned[-1][2]
                )
            ):
                raise _fail("TRUSTED_GENERATION_PLAN_REQUIRED")
        finally:
            reserved.close()

    @_detached_public_error_boundary
    def publish_immutable_json(
        self,
        document: Any,
        *,
        plan: TrustedImmutablePlan,
        lease: _SecureFileLock,
    ) -> ImmutablePublishReceipt:
        try:
            self._require_writer_lease(lease)
            return self._publish_immutable_json_with_active_lease(
                document,
                plan=plan,
                lease=lease,
            )
        except BaseException:
            # A failed authority effect is terminal for the capability.  This
            # prevents a caller from probing a rejected plan/body/path and
            # then reusing the same live context for a different write.
            self._revoke_writer_lease_after_failure(lease)
            raise

    def _publish_immutable_json_with_active_lease(
        self,
        document: Any,
        *,
        plan: TrustedImmutablePlan,
        lease: _SecureFileLock,
    ) -> ImmutablePublishReceipt:
        validated_plan = self._snapshot_immutable_plan(plan)
        payload = _canonical_json_bytes(
            document,
            max_depth=self._max_json_depth,
            max_nodes=self._max_json_nodes,
            max_bytes=self._max_bytes,
        )
        validated_plan = self._admit_immutable_plan(validated_plan)
        if _sha256(payload) != validated_plan.snapshot.body_sha256:
            raise _fail("IMMUTABLE_BODY_DIGEST_MISMATCH")
        receipt = self._publish_payload_noreplace(
            validated_plan.snapshot.relative_path,
            payload,
            lease=lease,
        )
        receipt_fingerprint = _immutable_receipt_fingerprint(
            sha256=receipt.sha256,
            predecessor_sha256=validated_plan.snapshot.expected_predecessor_sha256,
            byte_count=receipt.byte_count,
            identity=receipt.identity,
            plan_fingerprint=validated_plan.fingerprint,
            security_sha256=receipt.security_sha256,
            version=_IMMUTABLE_RECEIPT_VERSION,
        )
        return ImmutablePublishReceipt(
            sha256=receipt.sha256,
            predecessor_sha256=validated_plan.snapshot.expected_predecessor_sha256,
            byte_count=receipt.byte_count,
            identity=receipt.identity,
            plan_fingerprint=validated_plan.fingerprint,
            security_sha256=receipt.security_sha256,
            receipt_fingerprint=receipt_fingerprint,
            version=_IMMUTABLE_RECEIPT_VERSION,
        )

    @_detached_public_error_boundary
    def read_immutable_json(
        self,
        *,
        plan: TrustedImmutablePlan,
        receipt: ImmutablePublishReceipt,
    ) -> SecureJsonRead:
        plan_snapshot = self._snapshot_immutable_plan(plan)
        receipt_snapshot = self._snapshot_immutable_receipt(receipt)
        validated_plan = self._admit_immutable_plan(plan_snapshot)
        validated_receipt = self._validate_immutable_receipt(
            validated_plan,
            receipt_snapshot,
        )
        return self._read_validated_immutable_json(
            validated_plan,
            validated_receipt,
        )

    def _read_validated_immutable_json(
        self,
        plan: _ValidatedImmutablePlan,
        receipt: _ValidatedImmutableReceipt,
    ) -> SecureJsonRead:
        result = self.read_json(plan.snapshot.relative_path)
        if (
            result.sha256 != plan.snapshot.body_sha256
            or result.sha256 != receipt.snapshot.sha256
            or result.byte_count != receipt.snapshot.byte_count
            or result.identity != receipt.snapshot.identity
            or result.security_sha256 != receipt.snapshot.security_sha256
        ):
            raise _fail("IMMUTABLE_BINDING_MISMATCH")
        return result

    def _snapshot_immutable_namespace(
        self, representative_path: str
    ) -> dict[str, ArtifactIdentity]:
        parent = self._pin_parent(representative_path)
        try:
            self._stage("immutable_scan_before")
            scan_target: int | Path
            if os.name != "nt" and parent.parent_fd is not None:
                scan_target = parent.parent_fd
            else:
                scan_target = parent.target.parent
            snapshot: dict[str, ArtifactIdentity] = {}
            try:
                with os.scandir(scan_target) as entries:
                    for entry in entries:
                        if len(snapshot) >= self._max_json_nodes:
                            raise _fail("IMMUTABLE_SCAN_BOUND_EXCEEDED")
                        name = entry.name
                        if not _bounded_identifier(name):
                            raise _fail("IMMUTABLE_UNKNOWN_ARTIFACT")
                        if os.name == "nt":
                            # DirEntry.stat may expose st_nlink == 0 for a
                            # regular Windows file even when lstat/fstat bind
                            # the same object with nlink == 1. Use the pinned
                            # parent spelling and the module's canonical lstat
                            # representation so link-count policy stays exact.
                            identity = _identity(os.lstat(parent.target.parent / name))
                        else:
                            identity = _identity(entry.stat(follow_symlinks=False))
                        _require_regular(identity)
                        if name in snapshot:
                            raise _fail("IMMUTABLE_DUPLICATE_ARTIFACT")
                        snapshot[name] = identity
            except SecureAuthorityIOError:
                raise
            except OSError:
                raise _fail("IMMUTABLE_SCAN_FAILED") from None
            parent.verify()
            self._stage("immutable_scan_after")
            return snapshot
        finally:
            parent.close()

    @_detached_public_error_boundary
    def inspect_immutable_graph(
        self,
        *,
        plans: Sequence[TrustedImmutablePlan],
        expected_receipts: Mapping[str, ImmutablePublishReceipt],
        specified_plan: TrustedImmutablePlan,
    ) -> ImmutableGraphInspectionReceipt:
        if type(plans) not in {list, tuple}:
            raise _fail("IMMUTABLE_GRAPH_BOUND_REJECTED")
        plan_count = len(plans)
        if not 1 <= plan_count <= 1024:
            raise _fail("IMMUTABLE_GRAPH_BOUND_REJECTED")
        try:
            plan_objects = tuple(plans)
            repeated_plan_objects = tuple(plans)
        except Exception:
            raise _fail("IMMUTABLE_GRAPH_BOUND_REJECTED") from None
        if (
            len(plan_objects) != plan_count
            or len(repeated_plan_objects) != plan_count
            or any(
                first is not second
                for first, second in zip(plan_objects, repeated_plan_objects)
            )
        ):
            raise _fail("IMMUTABLE_GRAPH_CHANGED")
        if type(expected_receipts) is not dict:
            raise _fail("IMMUTABLE_GRAPH_BINDINGS_REJECTED")
        if len(expected_receipts) != plan_count:
            raise _fail("IMMUTABLE_GRAPH_BINDINGS_REJECTED")
        try:
            receipt_items = tuple(expected_receipts.items())
            repeated_receipt_items = tuple(expected_receipts.items())
        except Exception:
            raise _fail("IMMUTABLE_GRAPH_BINDINGS_REJECTED") from None
        if (
            len(receipt_items) != plan_count
            or len(repeated_receipt_items) != plan_count
            or any(
                first_key != second_key or first_value is not second_value
                for (first_key, first_value), (second_key, second_value) in zip(
                    receipt_items,
                    repeated_receipt_items,
                )
            )
        ):
            raise _fail("IMMUTABLE_GRAPH_CHANGED")
        receipt_objects: dict[str, ImmutablePublishReceipt] = {}
        for key, value in receipt_items:
            if type(key) is not str or key in receipt_objects:
                raise _fail("IMMUTABLE_GRAPH_BINDINGS_REJECTED")
            receipt_objects[key] = self._snapshot_immutable_receipt(value)

        plan_snapshots = tuple(
            self._snapshot_immutable_plan(plan) for plan in plan_objects
        )
        specified_indexes = [
            index for index, plan in enumerate(plan_objects) if plan is specified_plan
        ]
        if len(specified_indexes) != 1:
            raise _fail("IMMUTABLE_SPECIFIED_COORDINATE_REJECTED")
        validated_plans = tuple(
            self._admit_immutable_plan(plan) for plan in plan_snapshots
        )
        specified = validated_plans[specified_indexes[0]]

        plans_by_path: dict[str, _ValidatedImmutablePlan] = {}
        plans_by_digest: dict[str, _ValidatedImmutablePlan] = {}
        revisions: set[tuple[str, int]] = set()
        names: set[str] = set()
        common: tuple[str, str, str, str, str] | None = None
        for validated in validated_plans:
            plan = validated.snapshot
            parts = validated.parts
            binding = (
                plan.operation_id,
                plan.build_id,
                plan.backend_id,
                plan.session_id,
                plan.instance_id,
            )
            if common is None:
                common = binding
            elif binding != common:
                raise _fail("IMMUTABLE_CROSS_BINDING_REJECTED")
            revision_key = (plan.operation_id, plan.revision)
            if (
                revision_key in revisions
                or plan.body_sha256 in plans_by_digest
                or plan.relative_path in plans_by_path
                or parts[1] in names
            ):
                raise _fail("IMMUTABLE_DUPLICATE_ARTIFACT")
            revisions.add(revision_key)
            names.add(parts[1])
            plans_by_path[plan.relative_path] = validated
            plans_by_digest[plan.body_sha256] = validated

        roots = [
            plan
            for plan in validated_plans
            if plan.snapshot.expected_predecessor_sha256 == "sha256:" + "0" * 64
        ]
        if len(roots) != 1:
            raise _fail("IMMUTABLE_GRAPH_INCONSISTENT")
        children: dict[str, list[_ValidatedImmutablePlan]] = {}
        for plan in validated_plans:
            predecessor = plan.snapshot.expected_predecessor_sha256
            if predecessor == "sha256:" + "0" * 64:
                continue
            if predecessor not in plans_by_digest:
                raise _fail("IMMUTABLE_PREDECESSOR_MISSING")
            children.setdefault(predecessor, []).append(plan)
        if any(len(values) != 1 for values in children.values()):
            raise _fail("IMMUTABLE_FORK_STOP")

        visited: set[str] = set()
        cursor = specified
        while True:
            if cursor.snapshot.body_sha256 in visited:
                raise _fail("IMMUTABLE_CYCLE_STOP")
            visited.add(cursor.snapshot.body_sha256)
            predecessor = cursor.snapshot.expected_predecessor_sha256
            if predecessor == "sha256:" + "0" * 64:
                break
            cursor = plans_by_digest[predecessor]
        if len(visited) != len(validated_plans):
            raise _fail("IMMUTABLE_ORPHAN_STOP")

        if set(receipt_objects) != set(plans_by_path):
            raise _fail("IMMUTABLE_UNKNOWN_ARTIFACT")
        validated_receipts = {
            relative_path: self._validate_immutable_receipt(
                validated_plan,
                receipt_objects[relative_path],
            )
            for relative_path, validated_plan in plans_by_path.items()
        }
        aggregate = _sha256(
            "\n".join(
                sorted(
                    receipt.fingerprint
                    for receipt in validated_receipts.values()
                )
            ).encode("ascii")
        )
        if self._immutable_graph_verifier is None:
            raise _fail("TRUSTED_IMMUTABLE_GRAPH_REQUIRED")
        try:
            graph_accepted = self._immutable_graph_verifier(
                aggregate,
                validated_receipts[specified.snapshot.relative_path].fingerprint,
            )
        except Exception:
            raise _fail("TRUSTED_IMMUTABLE_GRAPH_REJECTED") from None
        if graph_accepted is not True:
            raise _fail("TRUSTED_IMMUTABLE_GRAPH_REJECTED")

        before = self._snapshot_immutable_namespace(specified.snapshot.relative_path)
        if set(before) != names:
            raise _fail("IMMUTABLE_UNKNOWN_ARTIFACT")
        for relative_path, validated_plan in plans_by_path.items():
            self._read_validated_immutable_json(
                validated_plan,
                validated_receipts[relative_path],
            )
        after = self._snapshot_immutable_namespace(specified.snapshot.relative_path)
        if before != after:
            raise _fail("IMMUTABLE_SCAN_CHANGED")
        for relative_path, validated_plan in plans_by_path.items():
            self._read_validated_immutable_json(
                validated_plan,
                validated_receipts[relative_path],
            )

        return ImmutableGraphInspectionReceipt(len(validated_plans), aggregate)

    @_detached_public_error_boundary
    def publish_json_noreplace(
        self,
        relative_path: str | os.PathLike[str],
        document: Any,
        *,
        lease: _SecureFileLock,
    ) -> SecurePublishReceipt:
        try:
            self._require_writer_lease(lease)
            parts = _relative_parts(relative_path)
            if parts[0].casefold() == _IMMUTABLE_NAMESPACE.casefold():
                raise _fail("TRUSTED_GENERATION_PLAN_REQUIRED")
            return self._publish_json_noreplace(
                relative_path,
                document,
                lease=lease,
                reject_physical_immutable_parent=True,
            )
        except BaseException:
            self._revoke_writer_lease_after_failure(lease)
            raise

    def _publish_json_noreplace(
        self,
        relative_path: str | os.PathLike[str],
        document: Any,
        *,
        lease: _SecureFileLock,
        reject_physical_immutable_parent: bool = False,
    ) -> SecurePublishReceipt:
        self._require_writer_lease(lease)
        payload = _canonical_json_bytes(
            document,
            max_depth=self._max_json_depth,
            max_nodes=self._max_json_nodes,
            max_bytes=self._max_bytes,
        )
        return self._publish_payload_noreplace(
            relative_path,
            payload,
            lease=lease,
            reject_physical_immutable_parent=reject_physical_immutable_parent,
        )

    def _publish_payload_noreplace(
        self,
        relative_path: str | os.PathLike[str],
        payload: bytes,
        *,
        lease: _SecureFileLock,
        reject_physical_immutable_parent: bool = False,
    ) -> SecurePublishReceipt:
        if type(payload) is not bytes or len(payload) > self._max_bytes:
            raise _fail("BYTE_BOUND_EXCEEDED")
        self._require_writer_lease(lease)
        parts = _relative_parts(relative_path)
        parent = self._pin_parent(relative_path)
        temp_lease: _TempLease | None = None
        published = False
        namespace_effect_unknown = False
        try:
            self._bind_writer_parent(lease, parent)
            if reject_physical_immutable_parent:
                self._reject_reserved_immutable_parent(parent, parts, lease)
            try:
                os.lstat(parent.target)
            except FileNotFoundError:
                pass
            except OSError:
                raise _fail("DESTINATION_LSTAT_FAILED") from None
            else:
                raise _fail("DESTINATION_EXISTS")
            temp_lease = self._write_temp(parent, payload)
            self._stage("temp_handle_live")
            self._stage("before_noreplace")
            parent.verify()
            publish_state: Literal["OWNED", "FOREIGN_COLLISION", "UNKNOWN"] | None = None
            try:
                self._rename_noreplace(parent, temp_lease)
                published = True
            except BaseException as publish_error:
                publish_state = self._classify_failed_noreplace(
                    parent,
                    temp_lease,
                    publish_error,
                )
            if publish_state == "FOREIGN_COLLISION":
                raise _fail("DESTINATION_EXISTS") from None
            if publish_state is not None:
                published = publish_state == "OWNED"
                namespace_effect_unknown = True
                raise _fail(
                    "PUBLISH_COMMIT_UNKNOWN",
                    completion_unknown=True,
                ) from None
            try:
                self._directory_durable(parent)
            except SecureAuthorityIOError as durability_error:
                try:
                    self._rollback_owned_publish(parent, payload, temp_lease)
                except SecureAuthorityIOError as rollback_error:
                    if rollback_error.completion_unknown:
                        raise
                    raise _fail("PUBLISH_ROLLBACK_UNKNOWN", completion_unknown=True) from None
                published = False
                try:
                    self._directory_durable(parent)
                except SecureAuthorityIOError:
                    raise _fail("PUBLISH_ROLLBACK_UNKNOWN", completion_unknown=True) from None
                raise durability_error
            try:
                final_identity, security_sha256 = self._verify_published(
                    parent,
                    payload,
                    temp_lease,
                )
                parent.verify()
            except SecureAuthorityIOError:
                raise _fail("PUBLISH_COMMIT_UNKNOWN", completion_unknown=True) from None
            return SecurePublishReceipt(
                _sha256(payload),
                len(payload),
                final_identity,
                security_sha256,
            )
        finally:
            close_failures: list[SecureAuthorityIOError] = []
            if temp_lease is not None:
                if not published:
                    try:
                        self._cleanup_temp(parent, temp_lease)
                    except SecureAuthorityIOError as exc:
                        close_failures.append(exc)
                try:
                    temp_lease.close()
                except SecureAuthorityIOError as exc:
                    close_failures.append(exc)
            try:
                parent.close()
            except SecureAuthorityIOError as exc:
                close_failures.append(exc)
            if close_failures:
                if published or namespace_effect_unknown:
                    raise _fail("PUBLISH_COMMIT_UNKNOWN", completion_unknown=True) from None
                if len(close_failures) > 1 or any(
                    failure.completion_unknown for failure in close_failures
                ):
                    raise _fail("HANDLE_CLEANUP_UNKNOWN", completion_unknown=True) from None
                raise close_failures[0]

    @_detached_public_error_boundary
    def replace_json_cas(
        self,
        relative_path: str | os.PathLike[str],
        document: Any,
        *,
        lease: _SecureFileLock,
        expected_identity: ArtifactIdentity,
        expected_sha256: str,
    ) -> NoReturn:
        """Discover that same-path mutable authority replacement is unsupported.

        TASK-068 IMMUTABLE_ONLY_V1 intentionally exposes no effect-bearing
        mutable CAS.  The live writer lease is validated and consumed, then the
        operation fails before inspecting caller data or touching the target.
        """
        self._burn_writer_lease(lease)
        # Neither supported platform currently exposes a portable primitive
        # that atomically conditions replacement on the captured target inode
        # while also binding the source to this live handle. Fail closed before
        # payload allocation, temporary creation, or namespace effect.
        raise _fail("CAS_ATOMIC_UNAVAILABLE")

    @_detached_public_error_boundary
    def commit_directory_tree(
        self,
        relative_path: str | os.PathLike[str],
        document: Any,
        *,
        lease: _SecureFileLock,
    ) -> NoReturn:
        """Discover that directory/tree publication is outside v1 authority."""
        self._burn_writer_lease(lease)
        raise _fail("DIRECTORY_TREE_COMMIT_AUTHORITY_NOT_CREATED")

    @_detached_public_error_boundary
    def advance_mutable_phase(
        self,
        relative_path: str | os.PathLike[str],
        document: Any,
        *,
        lease: _SecureFileLock,
    ) -> NoReturn:
        """Discover that fixed-path mutable phase advancement is unsupported."""
        self._burn_writer_lease(lease)
        raise _fail("MUTABLE_PHASE_ADVANCE_UNAVAILABLE")

    def _cleanup_temp(self, parent: _PinnedParent, lease: _TempLease) -> None:
        if lease.path is None:
            return
        try:
            live = _identity(os.fstat(lease.fd))
            observed = _identity(os.lstat(lease.path))
            if not _same_file_object(live, lease.identity) or observed != live:
                raise _fail("TEMP_OWNERSHIP_CHANGED")
            self._unlink_live_name(parent, lease.name, lease.fd, live)
        except FileNotFoundError:
            return
        except SecureAuthorityIOError:
            raise
        except OSError:
            raise _fail("TEMP_CLEANUP_FAILED") from None

    @_detached_public_error_boundary
    def cleanup_owned_file(
        self,
        relative_path: str | os.PathLike[str],
        *,
        lease: _SecureFileLock,
        expected_identity: ArtifactIdentity,
        expected_sha256: str,
    ) -> NoReturn:
        """Discover that authority-artifact namespace deletion is unsupported.

        Published authority artifacts are immutable in v1.  Revocation is a
        consumer-owned immutable transition, and physical GC requires a
        separate Task/Human Gate.  This operation therefore burns a valid
        writer lease and fails before any read, hook, open, rename, or unlink.
        """
        self._burn_writer_lease(lease)
        raise _fail("CLEANUP_ATOMIC_UNAVAILABLE")


__all__ = [
    "ArtifactIdentity",
    "ImmutableGraphInspectionReceipt",
    "ImmutablePublishReceipt",
    "SecureAuthorityIO",
    "SecureAuthorityIOError",
    "SecureJsonRead",
    "SecurePublishReceipt",
    "TrustedImmutablePlan",
]
