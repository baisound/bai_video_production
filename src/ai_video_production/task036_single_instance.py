"""Windows-only BAI Video Production single-instance guard."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from dataclasses import dataclass
from typing import Protocol

from .errors import ProductError, ProductErrorCategory


_ERROR_ALREADY_EXISTS = 183
_MUTEX_NAME = "Local\\BAIVideoProduction.Desktop.SingleInstance.v1"


class _Kernel32(Protocol):
    def CreateMutexW(self, attributes: object, initial_owner: bool, name: str) -> object: ...

    def GetLastError(self) -> int: ...

    def CloseHandle(self, handle: object) -> bool: ...


@dataclass(slots=True)
class Task036SingleInstanceLease:
    _kernel32: _Kernel32
    _handle: object | None

    def close(self) -> None:
        if self._handle is not None:
            self._kernel32.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self) -> "Task036SingleInstanceLease":
        return self

    def __exit__(self, *_unused: object) -> None:
        self.close()


def _windows_kernel32() -> _Kernel32:
    if os.name != "nt":
        raise ProductError(
            "ERR_TASK036_SINGLE_INSTANCE_WINDOWS_REQUIRED",
            "BAI Video Productionの多重起動防止はWindowsでのみ利用できます。",
            ProductErrorCategory.NOT_SUPPORTED,
        )
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.GetLastError.argtypes = ()
    kernel32.GetLastError.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    return kernel32


class Task036SingleInstanceGuard:
    """Reject a second packaged BVP process without using a stale-prone file lock."""

    def __init__(self, *, kernel32: _Kernel32 | None = None) -> None:
        if kernel32 is None:
            kernel32 = _windows_kernel32()
        self._kernel32 = kernel32

    def acquire(self) -> Task036SingleInstanceLease:
        handle = self._kernel32.CreateMutexW(None, False, _MUTEX_NAME)
        if not handle:
            raise ProductError(
                "ERR_TASK036_SINGLE_INSTANCE_UNAVAILABLE",
                "BAI Video Productionの多重起動防止を初期化できませんでした。再起動してから再試行してください。",
                ProductErrorCategory.STATE,
            )
        if self._kernel32.GetLastError() == _ERROR_ALREADY_EXISTS:
            self._kernel32.CloseHandle(handle)
            raise ProductError(
                "ERR_TASK036_ALREADY_RUNNING",
                "BAI Video Productionは既に起動しています。既存のウィンドウを確認してください。",
                ProductErrorCategory.STATE,
            )
        return Task036SingleInstanceLease(self._kernel32, handle)


__all__ = ["Task036SingleInstanceGuard", "Task036SingleInstanceLease"]