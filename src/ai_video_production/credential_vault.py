"""OS-backed credential storage without secret persistence in project files."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
import os
from typing import Protocol

from .errors import ProductError, ProductErrorCategory


CRED_MAX_CREDENTIAL_BLOB_SIZE = 2560
_TARGET_PREFIX = "BAI.VideoProduction/"


class CredentialVault(Protocol):
    def write(self, credential_ref: str, secret: str) -> None: ...
    def resolve(self, credential_ref: str) -> str: ...
    def contains(self, credential_ref: str) -> bool: ...
    def delete(self, credential_ref: str) -> bool: ...


class NativeCredentialBackend(Protocol):
    def write(self, target: str, blob: bytes) -> None: ...
    def read(self, target: str) -> bytes | None: ...
    def delete(self, target: str) -> bool: ...


def _validate_ref(credential_ref: str) -> None:
    if not isinstance(credential_ref, str) or not credential_ref.startswith("credential://"):
        raise ValueError("credential_ref must use credential://")


def credential_target(credential_ref: str) -> str:
    """Return an opaque target name so provider references are not exposed in UI tools."""
    _validate_ref(credential_ref)
    return _TARGET_PREFIX + hashlib.sha256(credential_ref.encode("utf-8")).hexdigest()


class WindowsCredentialManagerStore:
    """Store UTF-8 secrets as Windows generic credentials for the current user."""

    def __init__(self, backend: NativeCredentialBackend | None = None) -> None:
        if backend is None:
            if os.name != "nt":
                raise ProductError(
                    "ERR_CREDENTIAL_VAULT_UNSUPPORTED",
                    "Windows Credential Manager is available only on Windows",
                    ProductErrorCategory.EXTERNAL_DEPENDENCY,
                )
            backend = _Win32CredentialBackend()
        self._backend = backend

    def write(self, credential_ref: str, secret: str) -> None:
        _validate_ref(credential_ref)
        if not isinstance(secret, str) or not secret or not secret.strip() or "\x00" in secret:
            raise ValueError("credential must be non-empty text without NUL")
        blob = secret.encode("utf-8")
        if len(blob) > CRED_MAX_CREDENTIAL_BLOB_SIZE:
            raise ValueError("credential exceeds Windows Credential Manager size limit")
        self._backend.write(credential_target(credential_ref), blob)

    def resolve(self, credential_ref: str) -> str:
        blob = self._backend.read(credential_target(credential_ref))
        if blob is None:
            raise ProductError(
                "ERR_PROVIDER_CREDENTIAL_MISSING",
                "provider credential is unavailable",
                ProductErrorCategory.AUTHORIZATION,
            )
        try:
            value = blob.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProductError(
                "ERR_CREDENTIAL_VAULT_CORRUPT",
                "stored provider credential could not be decoded",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if not value:
            raise ProductError(
                "ERR_PROVIDER_CREDENTIAL_MISSING",
                "provider credential is unavailable",
                ProductErrorCategory.AUTHORIZATION,
            )
        return value

    def contains(self, credential_ref: str) -> bool:
        return self._backend.read(credential_target(credential_ref)) is not None

    def delete(self, credential_ref: str) -> bool:
        return self._backend.delete(credential_target(credential_ref))


class _CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


class _Win32CredentialBackend:
    _TYPE_GENERIC = 1
    _PERSIST_LOCAL_MACHINE = 2
    _ERROR_NOT_FOUND = 1168

    def __init__(self) -> None:
        self._advapi = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        self._advapi.CredWriteW.argtypes = [ctypes.POINTER(_CREDENTIALW), wintypes.DWORD]
        self._advapi.CredWriteW.restype = wintypes.BOOL
        self._advapi.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(_CREDENTIALW))]
        self._advapi.CredReadW.restype = wintypes.BOOL
        self._advapi.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        self._advapi.CredDeleteW.restype = wintypes.BOOL
        self._advapi.CredFree.argtypes = [ctypes.c_void_p]
        self._advapi.CredFree.restype = None

    @staticmethod
    def _failure(code: int) -> ProductError:
        return ProductError(
            "ERR_CREDENTIAL_VAULT_IO",
            "Windows Credential Manager operation failed",
            ProductErrorCategory.EXTERNAL_DEPENDENCY,
            details={"winerror": code},
        )

    def write(self, target: str, blob: bytes) -> None:
        buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
        value = _CREDENTIALW(
            Type=self._TYPE_GENERIC,
            TargetName=target,
            CredentialBlobSize=len(blob),
            CredentialBlob=ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)),
            Persist=self._PERSIST_LOCAL_MACHINE,
            UserName="BAI Video Production",
        )
        if not self._advapi.CredWriteW(ctypes.byref(value), 0):
            raise self._failure(ctypes.get_last_error())

    def read(self, target: str) -> bytes | None:
        pointer = ctypes.POINTER(_CREDENTIALW)()
        if not self._advapi.CredReadW(target, self._TYPE_GENERIC, 0, ctypes.byref(pointer)):
            code = ctypes.get_last_error()
            if code == self._ERROR_NOT_FOUND:
                return None
            raise self._failure(code)
        try:
            item = pointer.contents
            return ctypes.string_at(item.CredentialBlob, item.CredentialBlobSize)
        finally:
            self._advapi.CredFree(pointer)

    def delete(self, target: str) -> bool:
        if self._advapi.CredDeleteW(target, self._TYPE_GENERIC, 0):
            return True
        code = ctypes.get_last_error()
        if code == self._ERROR_NOT_FOUND:
            return False
        raise self._failure(code)
