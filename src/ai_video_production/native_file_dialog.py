"""Native file dialogs for the local Windows operator UI.

The browser is intentionally not given filesystem access. Instead the loopback
application asks Windows to display its own Open/Save dialog after an explicit
operator click. No selected file is uploaded to a remote service.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
from typing import Callable


class NativeFileDialogUnavailable(RuntimeError):
    """Raised when the native dialog cannot be shown on this platform."""


Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(slots=True)
class WindowsNativeFileDialog:
    """Open Windows Forms dialogs through a fixed, non-interpolated script."""

    runner: Runner = subprocess.run
    platform_name: str = os.name

    def _run(self, script: str) -> str | None:
        if self.platform_name != "nt":
            raise NativeFileDialogUnavailable("Native file selection is available on Windows only")

        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        completed = self.runner(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-STA",
                "-EncodedCommand",
                encoded,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or "Windows file dialog failed"
            raise NativeFileDialogUnavailable(detail[:500])

        selected = completed.stdout.strip()
        if not selected:
            return None
        if "\x00" in selected or len(selected) > 32_767:
            raise NativeFileDialogUnavailable("Windows returned an invalid file path")
        return str(Path(selected))

    def choose_open_srt(self) -> str | None:
        return self._run(
            r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
$utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = 'SRT字幕ファイルを選択 / Select SRT subtitle'
$dialog.Filter = 'SRT subtitle (*.srt)|*.srt|All files (*.*)|*.*'
$dialog.Multiselect = $false
$dialog.CheckFileExists = $true
$dialog.CheckPathExists = $true
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
    [Console]::Out.Write($dialog.FileName)
}
"""
        )

    def choose_save_srt(self) -> str | None:
        return self._run(
            r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
$utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8
$dialog = New-Object System.Windows.Forms.SaveFileDialog
$dialog.Title = 'SRTの保存先を選択 / Choose SRT destination'
$dialog.Filter = 'SRT subtitle (*.srt)|*.srt|All files (*.*)|*.*'
$dialog.DefaultExt = 'srt'
$dialog.AddExtension = $true
$dialog.OverwritePrompt = $true
$dialog.CheckPathExists = $true
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
    [Console]::Out.Write($dialog.FileName)
}
"""
        )
