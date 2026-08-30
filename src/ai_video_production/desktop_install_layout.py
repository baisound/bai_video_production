"""Trusted TASK-066 desktop installation layout read-back.

GF-A owns this schema and read-only resolver.  The installer-side GF-E helper
may use :func:`build_install_layout_document` and
:func:`validate_install_layout_document`, but it remains the only component
authorised to publish the sidecar or create protected writable leaves.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Mapping

from .montage_learning_installation import (
    BRIDGE_RELATIVE_PATH,
    BridgeInstanceDescriptor,
    discover_installed_bridge,
)
from .schema_contracts import validate_instance
from .serialization import canonical_json_bytes, sha256_bytes


SCHEMA_VERSION = "1.0.0"
MESSAGE_TYPE = "BvpDesktopInstallLayout"
PRODUCT_ID = "BAI_VIDEO_PRODUCTION"
SIDECAR_FILENAME = "desktop-install-layout.json"
PROFILE_RELATIVE_PATH = "settings/desktop-compute-profile.json"
INSTALLATION_STATE_RELATIVE_PATH = "settings/installation"
INSTALLER_RECEIPT_RELATIVE_PATH = (
    "settings/installation/task066-installer-readback.json"
)
INSTALLER_JOURNAL_RELATIVE_PATH = (
    "settings/installation/task066-installer-transaction.json"
)
WRITABLE_LEAVES = {
    "settings": "settings",
    "logs": "logs",
    "runtime_cache": "runtime-cache",
}
_MAX_SIDECAR_BYTES = 64 * 1024
_INSTANCE_RE = re.compile(r"^bvp-install-[0-9a-f]{32}$")
_REPARSE_POINT = 0x400


class DesktopInstallLayoutError(ValueError):
    """The installation coordinate cannot be trusted."""


@dataclass(frozen=True, slots=True)
class AclAceSnapshot:
    """Minimal Windows DACL Evidence used by the pure policy validator."""

    sid: str
    access_mask: int
    inherited: bool
    allow: bool


@dataclass(frozen=True, slots=True)
class Task063DescriptorIdentity:
    install_instance_id: str
    bridge_relative_path: str
    descriptor_sha256: str


@dataclass(frozen=True, slots=True)
class DesktopInstallLayout:
    install_instance_id: str
    install_scope: str
    binary_root: Path
    data_root: Path
    task063_descriptor_sha256: str
    layout_sha256: str
    acl_principal_sids: tuple[str, ...]

    @property
    def sidecar_path(self) -> Path:
        return self.binary_root / SIDECAR_FILENAME

    @property
    def settings_root(self) -> Path:
        return self.data_root / WRITABLE_LEAVES["settings"]

    @property
    def logs_root(self) -> Path:
        return self.data_root / WRITABLE_LEAVES["logs"]

    @property
    def runtime_cache_root(self) -> Path:
        return self.data_root / WRITABLE_LEAVES["runtime_cache"]

    @property
    def profile_path(self) -> Path:
        return self.data_root / Path(PROFILE_RELATIVE_PATH)

    @property
    def installation_state_root(self) -> Path:
        return self.data_root / Path(INSTALLATION_STATE_RELATIVE_PATH)

    @property
    def installer_receipt_path(self) -> Path:
        return self.data_root / Path(INSTALLER_RECEIPT_RELATIVE_PATH)

    @property
    def installer_journal_path(self) -> Path:
        return self.data_root / Path(INSTALLER_JOURNAL_RELATIVE_PATH)

    def public_receipt(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "message_type": "BvpDesktopInstallLayoutReadback",
            "product_id": PRODUCT_ID,
            "install_instance_id": self.install_instance_id,
            "install_scope": self.install_scope,
            "binary_root": str(self.binary_root),
            "data_root": str(self.data_root),
            "layout_sha256": self.layout_sha256,
            "acl_principal_set_sha256": sha256_bytes(
                canonical_json_bytes(list(self.acl_principal_sids))
            ),
            "status": "READY",
        }


def derive_binary_root(executable_path: str | Path) -> Path:
    """Derive the immutable binary root from an exact executable, never cwd."""
    executable = Path(executable_path)
    if not executable.is_absolute():
        raise DesktopInstallLayoutError("executable path must be absolute")
    _require_safe_regular_file(executable, "executable")
    return executable.resolve(strict=True).parent


def read_task063_descriptor_identity(
    binary_root: str | Path,
) -> Task063DescriptorIdentity:
    """Consume the canonical TASK-063 descriptor through its accepted reader."""
    root = _require_safe_directory(Path(binary_root), "binary_root")
    try:
        discovery = discover_installed_bridge(root)
    except Exception as exc:
        raise DesktopInstallLayoutError(
            "TASK-063 installation descriptor is unavailable or invalid"
        ) from exc
    if discovery.install_root.resolve(strict=True) != root:
        raise DesktopInstallLayoutError("TASK-063 install root mismatch")
    descriptor = discovery.descriptor
    if descriptor.bridge_relative_path != BRIDGE_RELATIVE_PATH:
        raise DesktopInstallLayoutError("TASK-063 bridge coordinate mismatch")
    return _descriptor_identity(descriptor)


def expected_data_root(
    binary_root: str | Path,
    install_scope: str,
    install_instance_id: str,
    *,
    program_data_root: str | Path | None = None,
) -> Path:
    root = Path(binary_root).resolve(strict=False)
    _require_instance_id(install_instance_id)
    if install_scope == "PER_USER":
        return root / "data"
    if install_scope != "SYSTEM_WIDE":
        raise DesktopInstallLayoutError("install_scope is unsupported")
    base_value = program_data_root or os.environ.get("PROGRAMDATA")
    if base_value is None:
        raise DesktopInstallLayoutError("ProgramData root is unavailable")
    base = Path(base_value)
    if not base.is_absolute():
        raise DesktopInstallLayoutError("ProgramData root must be absolute")
    return base.resolve(strict=False) / "BAI Video Production" / "instances" / install_instance_id


def build_install_layout_document(
    *,
    binary_root: str | Path,
    data_root: str | Path,
    install_scope: str,
    acl_principal_sids: tuple[str, ...],
    descriptor: Task063DescriptorIdentity | BridgeInstanceDescriptor,
    program_data_root: str | Path | None = None,
) -> dict[str, object]:
    """Build, but do not publish, a canonical sidecar document for GF-E."""
    root = Path(binary_root)
    if not root.is_absolute():
        raise DesktopInstallLayoutError("binary_root must be absolute")
    root = root.resolve(strict=False)
    identity = (
        descriptor
        if isinstance(descriptor, Task063DescriptorIdentity)
        else _descriptor_identity(descriptor)
    )
    expected = expected_data_root(
        root,
        install_scope,
        identity.install_instance_id,
        program_data_root=program_data_root,
    )
    supplied_data_root = Path(data_root)
    if not supplied_data_root.is_absolute():
        raise DesktopInstallLayoutError("data_root must be absolute")
    supplied_data_root = supplied_data_root.resolve(strict=False)
    if not _same_path(supplied_data_root, expected):
        raise DesktopInstallLayoutError("data_root does not match install scope")
    principals = _validate_acl_principal_sids(install_scope, acl_principal_sids)
    body: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "message_type": MESSAGE_TYPE,
        "product_id": PRODUCT_ID,
        "install_instance_id": identity.install_instance_id,
        "install_scope": install_scope,
        "binary_root": str(root),
        "binary_root_identity_sha256": _path_identity(root),
        "data_root": str(supplied_data_root),
        "task063_bridge_relative_path": identity.bridge_relative_path,
        "task063_descriptor_sha256": identity.descriptor_sha256,
        "writable_leaves": dict(WRITABLE_LEAVES),
        "acl_policy": "INSTALLER_PROTECTED",
        "acl_principal_sids": list(principals),
    }
    document = dict(body)
    document["layout_sha256"] = sha256_bytes(canonical_json_bytes(body))
    validate_install_layout_document(
        document,
        binary_root=root,
        descriptor=identity,
        program_data_root=program_data_root,
    )
    return document


def validate_install_layout_document(
    document: Mapping[str, Any],
    *,
    binary_root: str | Path,
    descriptor: Task063DescriptorIdentity | BridgeInstanceDescriptor,
    program_data_root: str | Path | None = None,
) -> DesktopInstallLayout:
    """Validate schema, digest, TASK-063 binding and canonical root rules."""
    value = dict(document)
    try:
        schema = json.loads(
            files("ai_video_production.schema_resources")
            .joinpath("desktop-install-layout.schema.json")
            .read_text(encoding="utf-8")
        )
        validate_instance(value, schema)
    except Exception as exc:
        raise DesktopInstallLayoutError("desktop InstallLayout schema mismatch") from exc
    if value["schema_version"] != SCHEMA_VERSION:
        raise DesktopInstallLayoutError("desktop InstallLayout version mismatch")
    body = dict(value)
    supplied_digest = body.pop("layout_sha256")
    if supplied_digest != sha256_bytes(canonical_json_bytes(body)):
        raise DesktopInstallLayoutError("desktop InstallLayout digest mismatch")

    root = Path(binary_root)
    if not root.is_absolute():
        raise DesktopInstallLayoutError("binary_root must be absolute")
    root = root.resolve(strict=False)
    if not _same_path(Path(value["binary_root"]), root):
        raise DesktopInstallLayoutError("binary_root substitution detected")
    if value["binary_root_identity_sha256"] != _path_identity(root):
        raise DesktopInstallLayoutError("binary_root identity mismatch")

    identity = (
        descriptor
        if isinstance(descriptor, Task063DescriptorIdentity)
        else _descriptor_identity(descriptor)
    )
    if value["install_instance_id"] != identity.install_instance_id:
        raise DesktopInstallLayoutError("install instance mismatch")
    if value["task063_bridge_relative_path"] != identity.bridge_relative_path:
        raise DesktopInstallLayoutError("TASK-063 bridge coordinate mismatch")
    if value["task063_descriptor_sha256"] != identity.descriptor_sha256:
        raise DesktopInstallLayoutError("TASK-063 descriptor digest mismatch")
    if value["writable_leaves"] != WRITABLE_LEAVES:
        raise DesktopInstallLayoutError("writable leaf ownership mismatch")
    principals = _validate_acl_principal_sids(
        value["install_scope"], tuple(value["acl_principal_sids"])
    )

    expected = expected_data_root(
        root,
        value["install_scope"],
        identity.install_instance_id,
        program_data_root=program_data_root,
    )
    data_root = Path(value["data_root"])
    if not data_root.is_absolute() or not _same_path(data_root, expected):
        raise DesktopInstallLayoutError("data_root substitution detected")
    return DesktopInstallLayout(
        install_instance_id=identity.install_instance_id,
        install_scope=value["install_scope"],
        binary_root=root,
        data_root=expected,
        task063_descriptor_sha256=identity.descriptor_sha256,
        layout_sha256=supplied_digest,
        acl_principal_sids=principals,
    )


def resolve_desktop_install_layout(
    binary_root: str | Path,
    *,
    program_data_root: str | Path | None = None,
) -> DesktopInstallLayout:
    """Read back the canonical TASK-063 descriptor and TASK-066 sidecar."""
    root = _require_safe_directory(Path(binary_root), "binary_root")
    descriptor = read_task063_descriptor_identity(root)
    sidecar = root / SIDECAR_FILENAME
    raw = _read_stable_regular_bytes(sidecar, _MAX_SIDECAR_BYTES, "InstallLayout sidecar")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DesktopInstallLayoutError("desktop InstallLayout JSON is invalid") from exc
    if not isinstance(document, dict):
        raise DesktopInstallLayoutError("desktop InstallLayout must be an object")
    layout = validate_install_layout_document(
        document,
        binary_root=root,
        descriptor=descriptor,
        program_data_root=program_data_root,
    )
    _require_safe_directory(layout.data_root, "data_root")
    protected_paths = [layout.data_root]
    for name, relative in WRITABLE_LEAVES.items():
        protected_paths.append(
            _require_contained_directory(layout.data_root, relative, name)
        )
    for path in protected_paths:
        _verify_protected_data_root_acl(
            path, layout.install_scope, layout.acl_principal_sids
        )
    return layout


def _descriptor_identity(
    descriptor: BridgeInstanceDescriptor,
) -> Task063DescriptorIdentity:
    _require_instance_id(descriptor.install_instance_id)
    if descriptor.bridge_relative_path != BRIDGE_RELATIVE_PATH:
        raise DesktopInstallLayoutError("TASK-063 bridge coordinate mismatch")
    return Task063DescriptorIdentity(
        install_instance_id=descriptor.install_instance_id,
        bridge_relative_path=descriptor.bridge_relative_path,
        descriptor_sha256=descriptor.descriptor_sha256,
    )


def _require_instance_id(value: str) -> None:
    if not isinstance(value, str) or _INSTANCE_RE.fullmatch(value) is None:
        raise DesktopInstallLayoutError("install instance id is invalid")


def _validate_acl_principal_sids(
    install_scope: str,
    values: tuple[str, ...],
) -> tuple[str, ...]:
    sid_re = re.compile(r"^S-1-(?:[0-9]+-)+[0-9]+$")
    if not values or len(values) > 64 or len(set(values)) != len(values):
        raise DesktopInstallLayoutError("DACL principal set is invalid")
    if any(sid_re.fullmatch(value) is None for value in values):
        raise DesktopInstallLayoutError("DACL principal SID is invalid")
    forbidden = _BROAD_WRITE_SIDS | {_SYSTEM_SID, _ADMINISTRATORS_SID}
    if any(value in forbidden for value in values):
        raise DesktopInstallLayoutError("DACL principal set contains a core or broad SID")
    if install_scope == "PER_USER" and len(values) != 1:
        raise DesktopInstallLayoutError("per-user layout requires one installing-user SID")
    if install_scope not in {"PER_USER", "SYSTEM_WIDE"}:
        raise DesktopInstallLayoutError("DACL install scope is unsupported")
    return tuple(sorted(values))


def _path_identity(path: Path) -> str:
    normalized = os.path.normcase(str(path.resolve(strict=False))).replace("\\", "/")
    return sha256_bytes(normalized.encode("utf-8"))


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve(strict=False))) == os.path.normcase(
        str(right.resolve(strict=False))
    )


def _require_safe_directory(path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise DesktopInstallLayoutError(f"{label} must be absolute")
    _reject_reparse_ancestors(path, include_leaf=True)
    try:
        metadata = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise DesktopInstallLayoutError(f"{label} is unavailable") from exc
    if not stat.S_ISDIR(metadata.st_mode):
        raise DesktopInstallLayoutError(f"{label} must be a directory")
    return path.resolve(strict=True)


def _require_safe_regular_file(path: Path, label: str) -> None:
    if not path.is_absolute():
        raise DesktopInstallLayoutError(f"{label} must be absolute")
    _reject_reparse_ancestors(path, include_leaf=True)
    try:
        metadata = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise DesktopInstallLayoutError(f"{label} is unavailable") from exc
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise DesktopInstallLayoutError(f"{label} must be a single-link regular file")


def _require_contained_directory(root: Path, relative: str, label: str) -> Path:
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise DesktopInstallLayoutError(f"{label} leaf is invalid")
    candidate = root / relative
    resolved = _require_safe_directory(candidate, label)
    try:
        resolved.relative_to(root.resolve(strict=True))
    except ValueError as exc:
        raise DesktopInstallLayoutError(f"{label} escapes data_root") from exc
    return resolved


def _reject_reparse_ancestors(path: Path, *, include_leaf: bool) -> None:
    absolute = Path(os.path.abspath(path))
    candidates = list(reversed(absolute.parents))
    if include_leaf:
        candidates.append(absolute)
    for candidate in candidates:
        if not candidate.exists() and not candidate.is_symlink():
            continue
        try:
            metadata = candidate.stat(follow_symlinks=False)
        except OSError as exc:
            raise DesktopInstallLayoutError("path ancestry is unavailable") from exc
        if candidate.is_symlink() or getattr(metadata, "st_file_attributes", 0) & _REPARSE_POINT:
            raise DesktopInstallLayoutError("reparse or symlink ancestry is prohibited")


def _read_stable_regular_bytes(path: Path, maximum: int, label: str) -> bytes:
    _require_safe_regular_file(path, label)
    before = path.stat(follow_symlinks=False)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise DesktopInstallLayoutError(f"{label} cannot be opened") from exc
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise DesktopInstallLayoutError(f"{label} identity is unsafe")
        if not 1 <= opened.st_size <= maximum:
            raise DesktopInstallLayoutError(f"{label} size is invalid")
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(descriptor, min(remaining, 64 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        after_open = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after = path.stat(follow_symlinks=False)
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
    if identity(before) != identity(opened) or identity(opened) != identity(after_open) or identity(after_open) != identity(after):
        raise DesktopInstallLayoutError(f"{label} changed during read-back")
    data = b"".join(chunks)
    if not 1 <= len(data) <= maximum:
        raise DesktopInstallLayoutError(f"{label} size is invalid")
    return data


_BROAD_WRITE_SIDS = {
    "S-1-1-0",       # Everyone
    "S-1-5-11",      # Authenticated Users
    "S-1-5-32-545",  # Builtin Users
}
_SYSTEM_SID = "S-1-5-18"
_ADMINISTRATORS_SID = "S-1-5-32-544"
_WRITE_ACCESS_MASK = (
    0x00000002  # FILE_WRITE_DATA
    | 0x00000004  # FILE_APPEND_DATA
    | 0x00000010  # FILE_WRITE_EA
    | 0x00000040  # FILE_DELETE_CHILD
    | 0x00000100  # FILE_WRITE_ATTRIBUTES
    | 0x00010000  # DELETE
    | 0x00040000  # WRITE_DAC
    | 0x00080000  # WRITE_OWNER
    | 0x10000000  # GENERIC_ALL
    | 0x40000000  # GENERIC_WRITE
)


def _ace_allow_classification(ace_type: int) -> bool:
    allow_types = {0x00, 0x05, 0x09, 0x0B}
    deny_types = {0x01, 0x06, 0x0A, 0x0C}
    if ace_type in allow_types:
        return True
    if ace_type in deny_types:
        return False
    raise DesktopInstallLayoutError("unsupported data DACL ACE type")


def _validate_acl_snapshot(
    *,
    owner_sid: str,
    dacl_protected: bool,
    aces: tuple[AclAceSnapshot, ...],
    install_scope: str,
    admitted_principal_sids: tuple[str, ...],
) -> None:
    if install_scope not in {"PER_USER", "SYSTEM_WIDE"}:
        raise DesktopInstallLayoutError("DACL install scope is unsupported")
    if not dacl_protected:
        raise DesktopInstallLayoutError("data DACL inheritance is not protected")
    principals = _validate_acl_principal_sids(install_scope, admitted_principal_sids)
    if not owner_sid or owner_sid in _BROAD_WRITE_SIDS:
        raise DesktopInstallLayoutError("data DACL owner is not trusted")
    deny_write_aces = [
        item for item in aces if not item.allow and item.access_mask & _WRITE_ACCESS_MASK
    ]
    if deny_write_aces:
        raise DesktopInstallLayoutError("data write deny ACE is prohibited")
    write_aces = [item for item in aces if item.allow and item.access_mask & _WRITE_ACCESS_MASK]
    if any(item.inherited for item in write_aces):
        raise DesktopInstallLayoutError("inherited data write ACE is prohibited")
    if any(item.sid in _BROAD_WRITE_SIDS for item in write_aces):
        raise DesktopInstallLayoutError("broad data write ACE is prohibited")
    permitted = set(principals) | {_SYSTEM_SID, _ADMINISTRATORS_SID}
    if any(item.sid not in permitted for item in write_aces):
        raise DesktopInstallLayoutError("data writer is not explicitly admitted")
    if install_scope == "PER_USER" and owner_sid != principals[0]:
        raise DesktopInstallLayoutError("per-user DACL owner does not match installing user")
    if install_scope == "SYSTEM_WIDE" and owner_sid not in {_SYSTEM_SID, _ADMINISTRATORS_SID}:
        raise DesktopInstallLayoutError("system-wide DACL owner is not privileged")
    required = set(principals) | (
        {_SYSTEM_SID, _ADMINISTRATORS_SID}
        if install_scope == "SYSTEM_WIDE"
        else {principals[0]}
    )
    if not required.issubset({item.sid for item in write_aces}):
        raise DesktopInstallLayoutError("required protected data writer is missing")


def _verify_protected_data_root_acl(
    path: Path,
    install_scope: str,
    admitted_principal_sids: tuple[str, ...],
) -> None:
    """Read the actual Windows owner/DACL and enforce the frozen policy."""
    if os.name != "nt":
        raise DesktopInstallLayoutError("Windows DACL verification is unavailable")
    import ctypes
    from ctypes import wintypes

    class ACL_SIZE_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("AceCount", wintypes.DWORD),
            ("AclBytesInUse", wintypes.DWORD),
            ("AclBytesFree", wintypes.DWORD),
        ]

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_named = advapi32.GetNamedSecurityInfoW
    get_named.argtypes = [
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    get_named.restype = wintypes.DWORD
    get_control = advapi32.GetSecurityDescriptorControl
    get_control.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.WORD), ctypes.POINTER(wintypes.DWORD)]
    get_control.restype = wintypes.BOOL
    get_acl_info = advapi32.GetAclInformation
    get_acl_info.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD]
    get_acl_info.restype = wintypes.BOOL
    get_ace = advapi32.GetAce
    get_ace.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)]
    get_ace.restype = wintypes.BOOL
    convert_sid = advapi32.ConvertSidToStringSidW
    convert_sid.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
    convert_sid.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    owner = ctypes.c_void_p()
    dacl = ctypes.c_void_p()
    security_descriptor = ctypes.c_void_p()
    result = get_named(
        str(path),
        1,  # SE_FILE_OBJECT
        0x00000001 | 0x00000004,  # OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION
        ctypes.byref(owner),
        None,
        ctypes.byref(dacl),
        None,
        ctypes.byref(security_descriptor),
    )
    if result != 0 or not security_descriptor.value or not owner.value or not dacl.value:
        if security_descriptor.value:
            kernel32.LocalFree(security_descriptor)
        raise DesktopInstallLayoutError("protected data DACL cannot be read")

    def sid_text(sid_pointer: ctypes.c_void_p) -> str:
        text_pointer = wintypes.LPWSTR()
        if not convert_sid(sid_pointer, ctypes.byref(text_pointer)):
            raise DesktopInstallLayoutError("data DACL SID cannot be read")
        try:
            return text_pointer.value
        finally:
            kernel32.LocalFree(text_pointer)

    try:
        control = wintypes.WORD()
        revision = wintypes.DWORD()
        if not get_control(security_descriptor, ctypes.byref(control), ctypes.byref(revision)):
            raise DesktopInstallLayoutError("data DACL control cannot be read")
        info = ACL_SIZE_INFORMATION()
        if not get_acl_info(dacl, ctypes.byref(info), ctypes.sizeof(info), 2):
            raise DesktopInstallLayoutError("data DACL entries cannot be read")
        snapshots: list[AclAceSnapshot] = []
        for index in range(info.AceCount):
            ace = ctypes.c_void_p()
            if not get_ace(dacl, index, ctypes.byref(ace)):
                raise DesktopInstallLayoutError("data DACL ACE cannot be read")
            address = int(ace.value)
            ace_type = ctypes.c_ubyte.from_address(address).value
            ace_flags = ctypes.c_ubyte.from_address(address + 1).value
            access_mask = ctypes.c_uint32.from_address(address + 4).value
            allow = _ace_allow_classification(ace_type)
            sid_offset = 8
            if ace_type in {0x05, 0x06, 0x0B, 0x0C}:
                object_flags = ctypes.c_uint32.from_address(address + 8).value
                sid_offset = 12 + (16 if object_flags & 0x1 else 0) + (16 if object_flags & 0x2 else 0)
            snapshots.append(
                AclAceSnapshot(
                    sid=sid_text(ctypes.c_void_p(address + sid_offset)),
                    access_mask=access_mask,
                    inherited=bool(ace_flags & 0x10),
                    allow=allow,
                )
            )
        _validate_acl_snapshot(
            owner_sid=sid_text(owner),
            dacl_protected=bool(control.value & 0x1000),
            aces=tuple(snapshots),
            install_scope=install_scope,
            admitted_principal_sids=admitted_principal_sids,
        )
    finally:
        kernel32.LocalFree(security_descriptor)


__all__ = [
    "AclAceSnapshot",
    "DesktopInstallLayout",
    "DesktopInstallLayoutError",
    "INSTALLATION_STATE_RELATIVE_PATH",
    "INSTALLER_JOURNAL_RELATIVE_PATH",
    "INSTALLER_RECEIPT_RELATIVE_PATH",
    "MESSAGE_TYPE",
    "PROFILE_RELATIVE_PATH",
    "PRODUCT_ID",
    "SCHEMA_VERSION",
    "SIDECAR_FILENAME",
    "Task063DescriptorIdentity",
    "WRITABLE_LEAVES",
    "build_install_layout_document",
    "derive_binary_root",
    "expected_data_root",
    "read_task063_descriptor_identity",
    "resolve_desktop_install_layout",
    "validate_install_layout_document",
]
