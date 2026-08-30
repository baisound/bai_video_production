"""TASK-059 P1C-H2 concrete Windows native PPK dialog backend.

File paths use the existing fixed WinForms chooser. The passphrase uses Windows
Credential UI with DO_NOT_PERSIST and a caller-owned native UTF-16 buffer. The
buffer is converted numerically into the H1 caller-owned UTF-8 bytearray and is
zeroed before this boundary returns.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass, field
import os
from typing import Callable

from .native_file_dialog import WindowsNativeFileDialog
from .owner_signing_key_ppk_native_adapter import MAX_PASSPHRASE_UTF8_BYTES


_ERROR_CANCELLED = 1223
_CREDUI_FLAGS_ALWAYS_SHOW_UI = 0x00000080
_CREDUI_FLAGS_DO_NOT_PERSIST = 0x00000002
_CREDUI_FLAGS_EXCLUDE_CERTIFICATES = 0x00000008
_CREDUI_FLAGS_GENERIC_CREDENTIALS = 0x00040000
_CREDUI_FLAGS_KEEP_USERNAME = 0x00100000
_CREDUI_FLAGS = (
    _CREDUI_FLAGS_ALWAYS_SHOW_UI
    | _CREDUI_FLAGS_DO_NOT_PERSIST
    | _CREDUI_FLAGS_EXCLUDE_CERTIFICATES
    | _CREDUI_FLAGS_GENERIC_CREDENTIALS
    | _CREDUI_FLAGS_KEEP_USERNAME
)


class PpkWindowsNativeDialogUnavailable(RuntimeError):
    """Body-free concrete native-dialog failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)

    def __repr__(self) -> str:
        return f"PpkWindowsNativeDialogUnavailable(code={self.code!r})"


class _CREDUI_INFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hwndParent", wintypes.HWND),
        ("pszMessageText", wintypes.LPCWSTR),
        ("pszCaptionText", wintypes.LPCWSTR),
        ("hbmBanner", wintypes.HANDLE),
    ]


NativeUtf16Buffer = ctypes.Array
SecretPrompt = Callable[[NativeUtf16Buffer, int], int | None]


def _clear_bytearray(value: bytearray) -> None:
    for index in range(len(value)):
        value[index] = 0


def _secure_zero_native(native_buffer: NativeUtf16Buffer) -> None:
    address = ctypes.addressof(native_buffer)
    size = ctypes.sizeof(native_buffer)
    if os.name == "nt":
        try:
            secure_zero = ctypes.WinDLL(
                "kernel32", use_last_error=True
            ).RtlSecureZeroMemory
            secure_zero.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
            secure_zero.restype = ctypes.c_void_p
            secure_zero(address, size)
            return
        except Exception:
            pass
    # ctypes is an FFI call and cannot be optimized away by Python.
    ctypes.memset(address, 0, size)


def _append_utf8(destination: bytearray, offset: int, code_point: int) -> int:
    if code_point <= 0x7F:
        needed = 1
    elif code_point <= 0x7FF:
        needed = 2
    elif code_point <= 0xFFFF:
        needed = 3
    elif code_point <= 0x10FFFF:
        needed = 4
    else:
        raise ValueError("invalid Unicode scalar")
    if offset + needed > len(destination):
        raise ValueError("passphrase exceeds UTF-8 byte ceiling")

    if needed == 1:
        destination[offset] = code_point
    elif needed == 2:
        destination[offset] = 0xC0 | (code_point >> 6)
        destination[offset + 1] = 0x80 | (code_point & 0x3F)
    elif needed == 3:
        destination[offset] = 0xE0 | (code_point >> 12)
        destination[offset + 1] = 0x80 | ((code_point >> 6) & 0x3F)
        destination[offset + 2] = 0x80 | (code_point & 0x3F)
    else:
        destination[offset] = 0xF0 | (code_point >> 18)
        destination[offset + 1] = 0x80 | ((code_point >> 12) & 0x3F)
        destination[offset + 2] = 0x80 | ((code_point >> 6) & 0x3F)
        destination[offset + 3] = 0x80 | (code_point & 0x3F)
    return offset + needed


def _utf16_units_to_utf8(
    native_buffer: NativeUtf16Buffer,
    unit_count: int,
    destination: bytearray,
) -> int:
    """Write strict UTF-8 without materializing a Python secret string/bytes."""

    if (
        isinstance(unit_count, bool)
        or not isinstance(unit_count, int)
        or unit_count < 0
        or unit_count >= len(native_buffer)
        or not isinstance(destination, bytearray)
        or not destination
    ):
        raise ValueError("native secret buffer shape is invalid")

    output = 0
    index = 0
    try:
        while index < unit_count:
            first = int(native_buffer[index])
            if first == 0:
                raise ValueError("native secret contains NUL")
            if 0xD800 <= first <= 0xDBFF:
                if index + 1 >= unit_count:
                    raise ValueError("native secret contains truncated surrogate")
                second = int(native_buffer[index + 1])
                if not 0xDC00 <= second <= 0xDFFF:
                    raise ValueError("native secret contains invalid surrogate")
                code_point = (
                    0x10000 + ((first - 0xD800) << 10) + (second - 0xDC00)
                )
                index += 2
            elif 0xDC00 <= first <= 0xDFFF:
                raise ValueError("native secret contains invalid surrogate")
            else:
                code_point = first
                index += 1
            output = _append_utf8(destination, output, code_point)
        return output
    except Exception:
        _clear_bytearray(destination)
        raise


def _windows_credential_prompt(
    native_buffer: NativeUtf16Buffer,
    maximum_units: int,
) -> int | None:
    """Fill a caller-owned UTF-16 buffer through Windows Credential UI."""

    if os.name != "nt":
        raise PpkWindowsNativeDialogUnavailable(
            "ERR_PPK_WINDOWS_SECRET_DIALOG_UNAVAILABLE"
        )
    try:
        credui = ctypes.WinDLL("credui", use_last_error=True)
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        prompt = credui.CredUIPromptForCredentialsW
        prompt.argtypes = [
            ctypes.POINTER(_CREDUI_INFOW),
            wintypes.LPCWSTR,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.LPWSTR,
            wintypes.ULONG,
            wintypes.LPWSTR,
            wintypes.ULONG,
            ctypes.POINTER(wintypes.BOOL),
            wintypes.DWORD,
        ]
        prompt.restype = wintypes.DWORD
        get_active_window = user32.GetActiveWindow
        get_active_window.argtypes = []
        get_active_window.restype = wintypes.HWND

        username = ctypes.create_unicode_buffer("BVP Owner signing key", 128)
        save = wintypes.BOOL(False)
        info = _CREDUI_INFOW(
            cbSize=ctypes.sizeof(_CREDUI_INFOW),
            hwndParent=get_active_window(),
            pszMessageText=(
                "暗号化PPKのパスフレーズを入力してください。"
                "保存・署名・公開はまだ実行しません。"
            ),
            pszCaptionText="BAI Video Production - 署名鍵の安全な取込",
            hbmBanner=None,
        )
        result = int(
            prompt(
                ctypes.byref(info),
                "BAI Video Production Owner Signing Key",
                None,
                0,
                username,
                len(username),
                ctypes.cast(native_buffer, wintypes.LPWSTR),
                maximum_units + 1,
                ctypes.byref(save),
                _CREDUI_FLAGS,
            )
        )
        if result == _ERROR_CANCELLED:
            return None
        if result != 0 or bool(save.value):
            raise PpkWindowsNativeDialogUnavailable(
                "ERR_PPK_WINDOWS_SECRET_DIALOG_FAILED"
            )
        for index in range(maximum_units + 1):
            if int(native_buffer[index]) == 0:
                return index
        raise PpkWindowsNativeDialogUnavailable(
            "ERR_PPK_WINDOWS_SECRET_DIALOG_FAILED"
        )
    except PpkWindowsNativeDialogUnavailable:
        raise
    except Exception:
        raise PpkWindowsNativeDialogUnavailable(
            "ERR_PPK_WINDOWS_SECRET_DIALOG_FAILED"
        ) from None


@dataclass(slots=True)
class WindowsPpkNativeDialogBackend:
    """Concrete H1 backend; secret values never enter PowerShell or stdout."""

    file_dialog: WindowsNativeFileDialog = field(
        default_factory=WindowsNativeFileDialog
    )
    secret_prompt: SecretPrompt | None = None
    platform_name: str = os.name

    def choose_encrypted_ppk(self) -> str | None:
        return self.file_dialog.choose_encrypted_ppk()

    def choose_rfc4716_public_key(self) -> str | None:
        return self.file_dialog.choose_rfc4716_public_key()

    def read_passphrase_utf8(
        self,
        destination: bytearray,
        *,
        maximum_bytes: int,
    ) -> int | None:
        if (
            self.platform_name != "nt"
            or not isinstance(destination, bytearray)
            or isinstance(maximum_bytes, bool)
            or not isinstance(maximum_bytes, int)
            or not 1 <= maximum_bytes <= MAX_PASSPHRASE_UTF8_BYTES
            or len(destination) != maximum_bytes
            or any(destination)
        ):
            if isinstance(destination, bytearray):
                _clear_bytearray(destination)
            raise PpkWindowsNativeDialogUnavailable(
                "ERR_PPK_WINDOWS_SECRET_DIALOG_UNAVAILABLE"
            )

        native_buffer = (ctypes.c_uint16 * (maximum_bytes + 1))()
        try:
            prompt = self.secret_prompt or _windows_credential_prompt
            unit_count = prompt(native_buffer, maximum_bytes)
            if unit_count is None:
                return None
            if (
                isinstance(unit_count, bool)
                or not isinstance(unit_count, int)
                or not 0 <= unit_count <= maximum_bytes
                or int(native_buffer[unit_count]) != 0
                or any(
                    int(native_buffer[index]) != 0
                    for index in range(unit_count + 1, len(native_buffer))
                )
            ):
                raise PpkWindowsNativeDialogUnavailable(
                    "ERR_PPK_WINDOWS_SECRET_DIALOG_FAILED"
                )
            return _utf16_units_to_utf8(
                native_buffer,
                unit_count,
                destination,
            )
        except PpkWindowsNativeDialogUnavailable:
            _clear_bytearray(destination)
            raise
        except Exception:
            _clear_bytearray(destination)
            raise PpkWindowsNativeDialogUnavailable(
                "ERR_PPK_WINDOWS_SECRET_DIALOG_FAILED"
            ) from None
        finally:
            _secure_zero_native(native_buffer)


__all__ = [
    "PpkWindowsNativeDialogUnavailable",
    "WindowsPpkNativeDialogBackend",
]
