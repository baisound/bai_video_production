from __future__ import annotations

import inspect

import pytest

import ai_video_production.owner_signing_key_ppk_windows_dialog as windows_dialog
from ai_video_production.owner_signing_key_ppk_windows_dialog import (
    PpkWindowsNativeDialogUnavailable,
    WindowsPpkNativeDialogBackend,
)


class FileDialog:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def choose_encrypted_ppk(self):
        self.calls.append("ppk")
        return r"C:\keys\owner.ppk"

    def choose_rfc4716_public_key(self):
        self.calls.append("public")
        return r"C:\keys\owner.pub"


def _prompt_for_units(units: list[int], captured: list[object]):
    def prompt(native_buffer, maximum_units):
        captured.append(native_buffer)
        assert maximum_units == len(native_buffer) - 1
        for index, unit in enumerate(units):
            native_buffer[index] = unit
        return len(units)

    return prompt


def test_backend_delegates_only_non_secret_file_selection() -> None:
    files = FileDialog()
    backend = WindowsPpkNativeDialogBackend(
        file_dialog=files,
        secret_prompt=lambda buffer, maximum: None,
        platform_name="nt",
    )
    assert backend.choose_encrypted_ppk() == r"C:\keys\owner.ppk"
    assert backend.choose_rfc4716_public_key() == r"C:\keys\owner.pub"
    assert files.calls == ["ppk", "public"]


def test_multilingual_secret_is_written_directly_and_native_buffer_is_zeroed() -> None:
    # "A雪😀" as numeric UTF-16 units. No secret Python str crosses production.
    units = [0x0041, 0x96EA, 0xD83D, 0xDE00]
    captured: list[object] = []
    destination = bytearray(1024)
    backend = WindowsPpkNativeDialogBackend(
        file_dialog=FileDialog(),
        secret_prompt=_prompt_for_units(units, captured),
        platform_name="nt",
    )

    length = backend.read_passphrase_utf8(destination, maximum_bytes=1024)
    assert length == 8
    assert bytes(destination[:length]) == b"A\xe9\x9b\xaa\xf0\x9f\x98\x80"
    assert not any(destination[length:])
    assert len(captured) == 1
    assert not any(int(value) for value in captured[0])


def test_cancel_returns_none_and_zeroes_native_and_destination_buffers() -> None:
    captured: list[object] = []

    def cancel(native_buffer, maximum_units):
        native_buffer[0] = 0x0078
        captured.append(native_buffer)
        return None

    destination = bytearray(64)
    backend = WindowsPpkNativeDialogBackend(
        file_dialog=FileDialog(),
        secret_prompt=cancel,
        platform_name="nt",
    )
    assert backend.read_passphrase_utf8(destination, maximum_bytes=64) is None
    assert not any(destination)
    assert not any(int(value) for value in captured[0])


@pytest.mark.parametrize(
    ("units", "maximum"),
    [
        ([0xD800], 16),
        ([0xDC00], 16),
        ([0xD800, 0x0041], 16),
        ([0xD83D, 0xDE00], 3),
    ],
)
def test_invalid_surrogate_or_utf8_overflow_fails_body_free_and_zeroes(
    units: list[int],
    maximum: int,
) -> None:
    captured: list[object] = []
    destination = bytearray(maximum)
    backend = WindowsPpkNativeDialogBackend(
        file_dialog=FileDialog(),
        secret_prompt=_prompt_for_units(units, captured),
        platform_name="nt",
    )
    with pytest.raises(PpkWindowsNativeDialogUnavailable) as error:
        backend.read_passphrase_utf8(
            destination,
            maximum_bytes=maximum,
        )
    assert error.value.code == "ERR_PPK_WINDOWS_SECRET_DIALOG_FAILED"
    assert repr(error.value) == (
        "PpkWindowsNativeDialogUnavailable("
        "code='ERR_PPK_WINDOWS_SECRET_DIALOG_FAILED')"
    )
    assert not any(destination)
    assert not any(int(value) for value in captured[0])


@pytest.mark.parametrize(
    ("count", "dirty_index"),
    [
        (True, None),
        (-1, None),
        (65, None),
        (1, 2),
    ],
)
def test_prompt_shape_or_undeclared_tail_fails_closed(
    count,
    dirty_index: int | None,
) -> None:
    captured: list[object] = []

    def prompt(native_buffer, maximum_units):
        native_buffer[0] = 0x0041
        if dirty_index is not None:
            native_buffer[dirty_index] = 0x0042
        captured.append(native_buffer)
        return count

    destination = bytearray(64)
    backend = WindowsPpkNativeDialogBackend(
        file_dialog=FileDialog(),
        secret_prompt=prompt,
        platform_name="nt",
    )
    with pytest.raises(PpkWindowsNativeDialogUnavailable) as error:
        backend.read_passphrase_utf8(destination, maximum_bytes=64)
    assert error.value.code == "ERR_PPK_WINDOWS_SECRET_DIALOG_FAILED"
    assert not any(destination)
    assert not any(int(value) for value in captured[0])


def test_dirty_destination_and_non_windows_fail_before_prompt() -> None:
    calls = []

    def prompt(native_buffer, maximum_units):
        calls.append(True)
        return 0

    dirty = bytearray(64)
    dirty[3] = 1
    backend = WindowsPpkNativeDialogBackend(
        file_dialog=FileDialog(),
        secret_prompt=prompt,
        platform_name="nt",
    )
    with pytest.raises(PpkWindowsNativeDialogUnavailable) as dirty_error:
        backend.read_passphrase_utf8(dirty, maximum_bytes=64)
    assert dirty_error.value.code == "ERR_PPK_WINDOWS_SECRET_DIALOG_UNAVAILABLE"
    assert not any(dirty)
    assert calls == []

    backend = WindowsPpkNativeDialogBackend(
        file_dialog=FileDialog(),
        secret_prompt=prompt,
        platform_name="posix",
    )
    clean = bytearray(64)
    with pytest.raises(PpkWindowsNativeDialogUnavailable) as platform_error:
        backend.read_passphrase_utf8(clean, maximum_bytes=64)
    assert platform_error.value.code == "ERR_PPK_WINDOWS_SECRET_DIALOG_UNAVAILABLE"
    assert calls == []


def test_prompt_exception_is_fixed_and_never_exposes_detail() -> None:
    def prompt(native_buffer, maximum_units):
        raise RuntimeError("synthetic-secret and native implementation detail")

    destination = bytearray(64)
    backend = WindowsPpkNativeDialogBackend(
        file_dialog=FileDialog(),
        secret_prompt=prompt,
        platform_name="nt",
    )
    with pytest.raises(PpkWindowsNativeDialogUnavailable) as error:
        backend.read_passphrase_utf8(destination, maximum_bytes=64)
    assert error.value.code == "ERR_PPK_WINDOWS_SECRET_DIALOG_FAILED"
    assert "synthetic-secret" not in repr(error.value)
    assert not any(destination)


def test_production_source_uses_nonpersistent_mutable_windows_boundary() -> None:
    source = inspect.getsource(windows_dialog)
    assert "_CREDUI_FLAGS_DO_NOT_PERSIST" in source
    assert "_CREDUI_FLAGS_KEEP_USERNAME" in source
    assert "CredUIPromptForCredentialsW" in source
    assert "ctypes.memset" in source
    assert "create_string_buffer" not in source
    assert "simpledialog" not in source
    assert "clipboard" not in source.casefold()
    assert "subprocess" not in source
    assert "powershell.exe" not in source.casefold()
    assert "native_buffer.value" not in source
    assert ".decode(" not in source
    assert "bytes(destination" not in source
