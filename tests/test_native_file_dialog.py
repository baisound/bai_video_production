from __future__ import annotations

import base64
import subprocess

import pytest

import ai_video_production.native_file_dialog as native


def test_native_dialog_fails_closed_off_windows() -> None:
    with pytest.raises(native.NativeFileDialogUnavailable, match="Windows only"):
        native.WindowsNativeFileDialog(platform_name="posix").choose_open_srt()


def test_native_dialog_uses_fixed_encoded_powershell_script() -> None:
    captured: dict[str, object] = {}

    def runner(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=r"C:\work\字幕.srt", stderr="")

    dialog = native.WindowsNativeFileDialog(runner=runner, platform_name="nt")
    assert dialog.choose_open_srt() == r"C:\work\字幕.srt"

    args = captured["args"]
    assert isinstance(args, list)
    assert args[:4] == ["powershell.exe", "-NoLogo", "-NoProfile", "-STA"]
    assert args[4] == "-EncodedCommand"
    script = base64.b64decode(args[5]).decode("utf-16le")
    assert "OpenFileDialog" in script
    assert "CheckFileExists = $true" in script
    assert "C:\\work\\字幕.srt" not in script


def test_native_dialog_propagates_bounded_error() -> None:
    def runner(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="dialog failed")

    with pytest.raises(native.NativeFileDialogUnavailable, match="dialog failed"):
        native.WindowsNativeFileDialog(runner=runner, platform_name="nt").choose_save_srt()