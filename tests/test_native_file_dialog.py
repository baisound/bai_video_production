from __future__ import annotations

import base64
import subprocess

import pytest

import ai_video_production.native_file_dialog as native


def protocol(kind: str, text: str = "") -> bytes:
    if kind == "cancel":
        return b"BAI_DIALOG_CANCEL"
    value = base64.b64encode(text.encode("utf-8")).decode("ascii")
    prefix = "BAI_DIALOG_OK" if kind == "ok" else "BAI_DIALOG_ERROR"
    return f"{prefix}:{value}".encode("ascii")


def test_native_dialog_fails_closed_off_windows() -> None:
    with pytest.raises(native.NativeFileDialogUnavailable, match="Windows only"):
        native.WindowsNativeFileDialog(platform_name="posix").choose_open_srt()


def test_native_dialog_uses_topmost_cursor_owned_fixed_powershell_script() -> None:
    captured: dict[str, object] = {}

    def runner(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=protocol("ok", r"C:\work\字幕.srt"), stderr=b"")

    dialog = native.WindowsNativeFileDialog(runner=runner, platform_name="nt")
    assert dialog.choose_open_srt() == r"C:\work\字幕.srt"

    args = captured["args"]
    assert isinstance(args, list)
    assert args[:4] == ["powershell.exe", "-NoLogo", "-NoProfile", "-STA"]
    assert args[4:7] == ["-OutputFormat", "Text", "-EncodedCommand"]
    script = base64.b64decode(args[7]).decode("utf-16le")
    assert "OpenFileDialog" in script
    assert "CheckFileExists = $true" in script
    assert "$owner.TopMost = $true" in script
    assert "[void]$owner.Show()" in script
    assert "[void]$owner.Activate()" in script
    assert "[System.Windows.Forms.Cursor]::Position" in script
    assert "$dialog.ShowDialog($owner)" in script
    assert "Add-Type -TypeDefinition" not in script
    assert "using System.Windows.Forms" not in script
    assert "GetForegroundWindow" not in script
    assert "C:\\work\\字幕.srt" not in script
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["text"] is False


def test_native_dialog_cancel_is_not_an_error() -> None:
    def runner(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=protocol("cancel"), stderr=b"")

    assert native.WindowsNativeFileDialog(runner=runner, platform_name="nt").choose_save_srt() is None


def test_native_dialog_propagates_bounded_protocol_error() -> None:
    def runner(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=2, stdout=protocol("error", "WinForms failed"), stderr=b"")

    with pytest.raises(native.NativeFileDialogUnavailable, match="WinForms failed"):
        native.WindowsNativeFileDialog(runner=runner, platform_name="nt").choose_save_srt()


def test_native_dialog_never_exposes_raw_clixml_to_browser_error() -> None:
    def runner(args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout=b"",
            stderr=b'#< CLIXML\r\n<Objs><S S="Error">Add-Type failed</S></Objs>',
        )

    with pytest.raises(native.NativeFileDialogUnavailable) as exc:
        native.WindowsNativeFileDialog(runner=runner, platform_name="nt").choose_open_srt()
    assert "CLIXML" not in str(exc.value)
    assert "<Objs" not in str(exc.value)
    assert "PowerShell" in str(exc.value)


def test_native_dialog_rejects_malformed_protocol_payload() -> None:
    def runner(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=b"BAI_DIALOG_OK:not-base64!", stderr=b"")

    with pytest.raises(native.NativeFileDialogUnavailable, match="invalid response"):
        native.WindowsNativeFileDialog(runner=runner, platform_name="nt").choose_open_srt()
