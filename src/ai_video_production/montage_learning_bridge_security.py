"""TASK-061 CA-A read-only Windows bridge security attestation.

The attestor inspects a bridge root and every ancestor without repairing ACLs,
creating directories, migrating data, or changing connector configuration.
Public evidence contains only hashes of paths, identities, owners, and DACLs.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
import re
import stat
from typing import Any, Callable, Protocol, runtime_checkable

from .serialization import canonical_json_bytes, sha256_bytes


ATTESTATION_VERSION = "1.0.0"
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
_STABLE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")
_SID = re.compile(r"S-[0-9]+(?:-[0-9]+)+")
_REPARSE_ATTRIBUTE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

_EVERYONE = "S-1-1-0"
_LOCAL_SYSTEM = "S-1-5-18"
_ADMINISTRATORS = "S-1-5-32-544"
_USERS = "S-1-5-32-545"
_OWNER_RIGHTS = "S-1-3-4"
_ALLOWED_FIXED_SIDS = frozenset(
    {_EVERYONE, _LOCAL_SYSTEM, _ADMINISTRATORS, _USERS, _OWNER_RIGHTS}
)

_ACCESS_ALLOWED_ACE_TYPE = 0
_ACCESS_DENIED_ACE_TYPE = 1
_DANGEROUS_WRITE_MASK = (
    0x00000002  # FILE_WRITE_DATA / FILE_ADD_FILE
    | 0x00000004  # FILE_APPEND_DATA / FILE_ADD_SUBDIRECTORY
    | 0x00000010  # FILE_WRITE_EA
    | 0x00000040  # FILE_DELETE_CHILD
    | 0x00000100  # FILE_WRITE_ATTRIBUTES
    | 0x00010000  # DELETE
    | 0x00040000  # WRITE_DAC
    | 0x00080000  # WRITE_OWNER
    | 0x10000000  # GENERIC_ALL
    | 0x40000000  # GENERIC_WRITE
)


def _stable(value: object, field: str) -> str:
    if type(value) is not str or _STABLE_ID.fullmatch(value) is None:
        raise ValueError(f"{field} must be a stable identifier")
    return value


def _sha(value: object, field: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase sha256 coordinate")
    return value


def _is_reparse(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & _REPARSE_ATTRIBUTE
    )


def _file_identity(path: Path, info: os.stat_result) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "domain": "TASK061_BRIDGE_SECURITY_FILE_IDENTITY_V1",
                "path_sha256": sha256_bytes(str(path).encode("utf-8")),
                "device": info.st_dev,
                "inode": info.st_ino,
                "mode": info.st_mode,
            }
        )
    )


@dataclass(frozen=True, slots=True, order=True)
class BridgeAce:
    ace_type: int
    ace_flags: int
    access_mask: int
    sid: str

    def __post_init__(self) -> None:
        for field in ("ace_type", "ace_flags", "access_mask"):
            value = getattr(self, field)
            if type(value) is not int or value < 0 or value > 0xFFFFFFFF:
                raise ValueError(f"{field} is invalid")
        if type(self.sid) is not str or _SID.fullmatch(self.sid) is None:
            raise ValueError("sid is invalid")

    def private_dict(self) -> dict[str, Any]:
        return {
            "ace_type": self.ace_type,
            "ace_flags": self.ace_flags,
            "access_mask": self.access_mask,
            "sid": self.sid,
        }

    def public_dict(self) -> dict[str, Any]:
        return {
            "ace_type": self.ace_type,
            "ace_flags": self.ace_flags,
            "access_mask": self.access_mask,
            "sid_sha256": sha256_bytes(self.sid.encode("ascii")),
        }


@dataclass(frozen=True, slots=True)
class BridgeSecurityDescriptor:
    owner_sid: str
    current_user_sid: str
    dacl_present: bool
    aces: tuple[BridgeAce, ...]

    def __post_init__(self) -> None:
        for field in ("owner_sid", "current_user_sid"):
            value = getattr(self, field)
            if type(value) is not str or _SID.fullmatch(value) is None:
                raise ValueError(f"{field} is invalid")
        if self.dacl_present is not True:
            raise ValueError("a present non-NULL DACL is required")
        if type(self.aces) is not tuple or not self.aces:
            raise ValueError("DACL must contain at least one ACE")
        if any(type(ace) is not BridgeAce for ace in self.aces):
            raise ValueError("aces must contain exact BridgeAce values")


@runtime_checkable
class BridgeSecurityBackend(Protocol):
    def inspect(self, path: Path) -> BridgeSecurityDescriptor: ...


class _Acl(ctypes.Structure):
    _fields_ = [
        ("AclRevision", wintypes.BYTE),
        ("Sbz1", wintypes.BYTE),
        ("AclSize", wintypes.WORD),
        ("AceCount", wintypes.WORD),
        ("Sbz2", wintypes.WORD),
    ]


class _AceHeader(ctypes.Structure):
    _fields_ = [
        ("AceType", wintypes.BYTE),
        ("AceFlags", wintypes.BYTE),
        ("AceSize", wintypes.WORD),
    ]


class _SidAndAttributes(ctypes.Structure):
    _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]


class _TokenUser(ctypes.Structure):
    _fields_ = [("User", _SidAndAttributes)]


class WindowsBridgeSecurityBackend:
    """Read owner and DACL with Windows Security APIs; never call a setter."""

    _OWNER_SECURITY_INFORMATION = 0x00000001
    _DACL_SECURITY_INFORMATION = 0x00000004
    _SE_FILE_OBJECT = 1
    _TOKEN_QUERY = 0x0008
    _TOKEN_USER = 1

    def __init__(self) -> None:
        if os.name != "nt":
            raise OSError("Windows bridge security inspection is unavailable")
        self.advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    def _sid_text(self, sid: ctypes.c_void_p) -> str:
        output = wintypes.LPWSTR()
        function = self.advapi32.ConvertSidToStringSidW
        function.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
        function.restype = wintypes.BOOL
        if not function(sid, ctypes.byref(output)):
            raise OSError(ctypes.get_last_error(), "ConvertSidToStringSidW failed")
        try:
            return str(output.value)
        finally:
            self.kernel32.LocalFree(ctypes.cast(output, ctypes.c_void_p))

    def _current_user_sid(self) -> str:
        token = wintypes.HANDLE()
        open_token = self.advapi32.OpenProcessToken
        open_token.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
        open_token.restype = wintypes.BOOL
        if not open_token(self.kernel32.GetCurrentProcess(), self._TOKEN_QUERY, ctypes.byref(token)):
            raise OSError(ctypes.get_last_error(), "OpenProcessToken failed")
        try:
            required = wintypes.DWORD()
            get_info = self.advapi32.GetTokenInformation
            get_info.argtypes = [
                wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD),
            ]
            get_info.restype = wintypes.BOOL
            get_info(token, self._TOKEN_USER, None, 0, ctypes.byref(required))
            if required.value == 0:
                raise OSError(ctypes.get_last_error(), "GetTokenInformation sizing failed")
            buffer = ctypes.create_string_buffer(required.value)
            if not get_info(
                token, self._TOKEN_USER, buffer, required, ctypes.byref(required)
            ):
                raise OSError(ctypes.get_last_error(), "GetTokenInformation failed")
            token_user = ctypes.cast(buffer, ctypes.POINTER(_TokenUser)).contents
            return self._sid_text(token_user.User.Sid)
        finally:
            self.kernel32.CloseHandle(token)

    def inspect(self, path: Path) -> BridgeSecurityDescriptor:
        owner = ctypes.c_void_p()
        dacl = ctypes.c_void_p()
        descriptor = ctypes.c_void_p()
        function = self.advapi32.GetNamedSecurityInfoW
        function.argtypes = [
            wintypes.LPWSTR, ctypes.c_int, wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        function.restype = wintypes.DWORD
        result = function(
            str(path), self._SE_FILE_OBJECT,
            self._OWNER_SECURITY_INFORMATION | self._DACL_SECURITY_INFORMATION,
            ctypes.byref(owner), None, ctypes.byref(dacl), None,
            ctypes.byref(descriptor),
        )
        if result != 0:
            raise PermissionError(result, "GetNamedSecurityInfoW failed")
        try:
            if not owner.value or not dacl.value:
                raise ValueError("owner or DACL is absent")
            acl = ctypes.cast(dacl, ctypes.POINTER(_Acl)).contents
            get_ace = self.advapi32.GetAce
            get_ace.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)]
            get_ace.restype = wintypes.BOOL
            aces: list[BridgeAce] = []
            for index in range(acl.AceCount):
                ace_pointer = ctypes.c_void_p()
                if not get_ace(dacl, index, ctypes.byref(ace_pointer)):
                    raise OSError(ctypes.get_last_error(), "GetAce failed")
                header = ctypes.cast(ace_pointer, ctypes.POINTER(_AceHeader)).contents
                if header.AceSize < 12:
                    raise ValueError("ACE is truncated")
                access_mask = ctypes.c_uint32.from_address(ace_pointer.value + 4).value
                if header.AceType not in {
                    _ACCESS_ALLOWED_ACE_TYPE, _ACCESS_DENIED_ACE_TYPE,
                }:
                    aces.append(
                        BridgeAce(
                            int(header.AceType), int(header.AceFlags), access_mask,
                            "S-1-0-0",
                        )
                    )
                    continue
                sid_pointer = ctypes.c_void_p(ace_pointer.value + 8)
                aces.append(
                    BridgeAce(
                        int(header.AceType), int(header.AceFlags), access_mask,
                        self._sid_text(sid_pointer),
                    )
                )
            return BridgeSecurityDescriptor(
                self._sid_text(owner), self._current_user_sid(), True, tuple(aces)
            )
        finally:
            if descriptor.value:
                self.kernel32.LocalFree(descriptor)


class BridgeSecurityState(str, Enum):
    SECURE = "SECURE"
    BRIDGE_REPAIR_REQUIRED = "BRIDGE_REPAIR_REQUIRED"
    INSPECTION_FAILED = "INSPECTION_FAILED"
    NOT_SUPPORTED = "NOT_SUPPORTED"


@dataclass(frozen=True, slots=True)
class BridgeSecurityAttestation:
    attestation_id: str
    state: BridgeSecurityState
    root_identity_sha256: str | None
    owner_sid_sha256: str | None
    current_user_sid_sha256: str | None
    dacl_sha256: str | None
    ancestor_count: int
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        _stable(self.attestation_id, "attestation_id")
        if type(self.state) is not BridgeSecurityState:
            raise ValueError("state is invalid")
        for field in (
            "root_identity_sha256", "owner_sid_sha256", "current_user_sid_sha256",
            "dacl_sha256",
        ):
            value = getattr(self, field)
            if value is not None:
                _sha(value, field)
        if type(self.ancestor_count) is not int or self.ancestor_count < 0:
            raise ValueError("ancestor_count is invalid")
        if (
            type(self.reason_codes) is not tuple
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
            or any(type(code) is not str or not code for code in self.reason_codes)
        ):
            raise ValueError("reason_codes must be canonical")
        complete = all(
            getattr(self, field) is not None
            for field in (
                "root_identity_sha256", "owner_sid_sha256",
                "current_user_sid_sha256", "dacl_sha256",
            )
        )
        if self.state is BridgeSecurityState.SECURE and (not complete or self.reason_codes):
            raise ValueError("SECURE attestation requires complete clean evidence")
        if self.state is not BridgeSecurityState.SECURE and not self.reason_codes:
            raise ValueError("non-secure attestation requires reason codes")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema_version": ATTESTATION_VERSION,
            "record_type": "MONTAGE_LEARNING_BRIDGE_SECURITY_ATTESTATION",
            "task_owner": "TASK-061",
            "attestation_id": self.attestation_id,
            "state": self.state.value,
            "root_identity_sha256": self.root_identity_sha256,
            "owner_sid_sha256": self.owner_sid_sha256,
            "current_user_sid_sha256": self.current_user_sid_sha256,
            "dacl_sha256": self.dacl_sha256,
            "ancestor_count": self.ancestor_count,
            "reason_codes": list(self.reason_codes),
            "all_ancestors_revalidated": self.state is BridgeSecurityState.SECURE,
            "unknown_ace_rejected": True,
            "shared_writer_ace_rejected": True,
            "repair_performed": False,
            "migration_started": False,
            "connector_config_write_authorized": False,
            "activation_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
            "external_effect_authorized": False,
        }
        body["attestation_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "BridgeSecurityAttestation":
        expected = {
            "schema_version", "record_type", "task_owner", "attestation_id", "state",
            "root_identity_sha256", "owner_sid_sha256", "current_user_sid_sha256",
            "dacl_sha256", "ancestor_count", "reason_codes",
            "all_ancestors_revalidated", "unknown_ace_rejected",
            "shared_writer_ace_rejected", "repair_performed", "migration_started",
            "connector_config_write_authorized", "activation_authorized",
            "timeline_mutation_authorized", "resolve_write_authorized",
            "external_effect_authorized", "attestation_sha256",
        }
        if type(value) is not dict or set(value) != expected:
            raise ValueError("attestation fields are incomplete or unknown")
        if (
            value["schema_version"] != ATTESTATION_VERSION
            or value["record_type"] != "MONTAGE_LEARNING_BRIDGE_SECURITY_ATTESTATION"
            or value["task_owner"] != "TASK-061"
            or value["unknown_ace_rejected"] is not True
            or value["shared_writer_ace_rejected"] is not True
            or value["repair_performed"] is not False
            or value["migration_started"] is not False
        ):
            raise ValueError("attestation identity or safety boundary mismatch")
        for field in (
            "connector_config_write_authorized", "activation_authorized",
            "timeline_mutation_authorized", "resolve_write_authorized",
            "external_effect_authorized",
        ):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        result = cls(
            value["attestation_id"], BridgeSecurityState(value["state"]),
            value["root_identity_sha256"], value["owner_sid_sha256"],
            value["current_user_sid_sha256"], value["dacl_sha256"],
            value["ancestor_count"], tuple(value["reason_codes"]),
        )
        if value["all_ancestors_revalidated"] is not (
            result.state is BridgeSecurityState.SECURE
        ) or result.to_dict() != value:
            raise ValueError("attestation hash or derived fields mismatch")
        return result


def _evaluate_descriptor(descriptor: BridgeSecurityDescriptor) -> tuple[str, ...]:
    reasons: set[str] = set()
    if descriptor.owner_sid != descriptor.current_user_sid:
        reasons.add("WRONG_OWNER")
    known = _ALLOWED_FIXED_SIDS | {descriptor.current_user_sid}
    for ace in descriptor.aces:
        if ace.ace_type not in {_ACCESS_ALLOWED_ACE_TYPE, _ACCESS_DENIED_ACE_TYPE}:
            reasons.add("UNKNOWN_ACE_TYPE")
            continue
        if ace.sid not in known:
            reasons.add("UNKNOWN_ACE_SID")
            continue
        if ace.ace_type == _ACCESS_DENIED_ACE_TYPE:
            reasons.add("DENY_ACE_UNSUPPORTED")
            continue
        if ace.sid in {_EVERYONE, _USERS} and ace.access_mask & _DANGEROUS_WRITE_MASK:
            reasons.add("SHARED_WRITER_ACE")
    return tuple(sorted(reasons))


def _evaluate_ancestor_descriptor(
    descriptor: BridgeSecurityDescriptor,
) -> tuple[str, ...]:
    reasons: set[str] = set()
    for ace in descriptor.aces:
        if ace.ace_type not in {_ACCESS_ALLOWED_ACE_TYPE, _ACCESS_DENIED_ACE_TYPE}:
            reasons.add("UNKNOWN_ANCESTOR_ACE_TYPE")
            continue
        if ace.ace_type == _ACCESS_DENIED_ACE_TYPE:
            continue
        if not ace.access_mask & _DANGEROUS_WRITE_MASK:
            continue
        if ace.sid in {_EVERYONE, _USERS}:
            reasons.add("SHARED_WRITER_ANCESTOR")
    return tuple(sorted(reasons))


SecurityHook = Callable[[str, Path], None]


def attest_bridge_security(
    root: str | Path,
    *,
    attestation_id: str,
    backend: BridgeSecurityBackend | None = None,
    hook: SecurityHook | None = None,
) -> BridgeSecurityAttestation:
    """Inspect exact root/ancestor identities and DACL; perform no repair."""

    _stable(attestation_id, "attestation_id")
    path = Path(root)
    if not path.is_absolute() or any(part in {".", ".."} for part in path.parts):
        return BridgeSecurityAttestation(
            attestation_id, BridgeSecurityState.INSPECTION_FAILED,
            None, None, None, None, 0, ("ROOT_PATH_INVALID",),
        )
    if backend is None:
        if os.name != "nt":
            return BridgeSecurityAttestation(
                attestation_id, BridgeSecurityState.NOT_SUPPORTED,
                None, None, None, None, 0, ("WINDOWS_SECURITY_API_UNAVAILABLE",),
            )
        backend = WindowsBridgeSecurityBackend()
    if not isinstance(backend, BridgeSecurityBackend):
        raise ValueError("backend does not implement BridgeSecurityBackend")

    identities: list[tuple[Path, str]] = []
    current = path
    try:
        while True:
            info = os.lstat(current)
            if _is_reparse(info):
                return BridgeSecurityAttestation(
                    attestation_id, BridgeSecurityState.BRIDGE_REPAIR_REQUIRED,
                    None, None, None, None, max(0, len(identities) - 1),
                    ("REPARSE_POINT_REJECTED",),
                )
            if not stat.S_ISDIR(info.st_mode):
                return BridgeSecurityAttestation(
                    attestation_id, BridgeSecurityState.BRIDGE_REPAIR_REQUIRED,
                    None, None, None, None, max(0, len(identities) - 1),
                    ("ROOT_OR_ANCESTOR_NOT_DIRECTORY",),
                )
            identities.append((current, _file_identity(current, info)))
            if current.parent == current:
                break
            current = current.parent
        if hook:
            hook("before_descriptor", path)
        descriptors = tuple(backend.inspect(target) for target, _ in identities)
        if hook:
            hook("after_descriptor", path)
        for target, expected_identity in identities:
            info = os.lstat(target)
            if _is_reparse(info) or _file_identity(target, info) != expected_identity:
                return BridgeSecurityAttestation(
                    attestation_id, BridgeSecurityState.BRIDGE_REPAIR_REQUIRED,
                    None, None, None, None, len(identities) - 1,
                    ("ANCESTOR_IDENTITY_CHANGED",),
                )
    except PermissionError:
        return BridgeSecurityAttestation(
            attestation_id, BridgeSecurityState.BRIDGE_REPAIR_REQUIRED,
            None, None, None, None, max(0, len(identities) - 1),
            ("SECURITY_DESCRIPTOR_ACCESS_DENIED",),
        )
    except (OSError, TypeError, ValueError):
        return BridgeSecurityAttestation(
            attestation_id, BridgeSecurityState.INSPECTION_FAILED,
            None, None, None, None, max(0, len(identities) - 1),
            ("SECURITY_INSPECTION_FAILED",),
        )

    descriptor = descriptors[0]
    reasons = tuple(
        sorted(
            set(_evaluate_descriptor(descriptor)).union(
                reason
                for ancestor in descriptors[1:]
                for reason in _evaluate_ancestor_descriptor(ancestor)
            )
        )
    )
    state = (
        BridgeSecurityState.SECURE
        if not reasons
        else BridgeSecurityState.BRIDGE_REPAIR_REQUIRED
    )
    dacl_sha256 = sha256_bytes(
        canonical_json_bytes(
            [
                {
                    "path_identity_sha256": identities[index][1],
                    "owner_sid": item.owner_sid,
                    "aces": [ace.private_dict() for ace in item.aces],
                }
                for index, item in enumerate(descriptors)
            ]
        )
    )
    return BridgeSecurityAttestation(
        attestation_id, state, identities[0][1],
        sha256_bytes(descriptor.owner_sid.encode("ascii")),
        sha256_bytes(descriptor.current_user_sid.encode("ascii")), dacl_sha256,
        len(identities) - 1, reasons,
    )


__all__ = [
    "ATTESTATION_VERSION", "BridgeAce", "BridgeSecurityAttestation",
    "BridgeSecurityBackend", "BridgeSecurityDescriptor", "BridgeSecurityState",
    "WindowsBridgeSecurityBackend", "attest_bridge_security",
]
