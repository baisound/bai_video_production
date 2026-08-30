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


Runner = Callable[..., subprocess.CompletedProcess[bytes]]

_PROTOCOL_OK = "BAI_DIALOG_OK:"
_PROTOCOL_ERROR = "BAI_DIALOG_ERROR:"
_PROTOCOL_CANCEL = "BAI_DIALOG_CANCEL"

# Keep the PowerShell side deliberately simple. The previous foreground-owner
# implementation compiled a custom C# IWin32Window type. Windows PowerShell can
# load System.Windows.Forms successfully while Add-Type's C# compiler still
# lacks an explicit Forms reference, which caused native acceptance to fail.
#
# A temporary top-most WinForms owner is enough for the actual requirement:
# keep Open/Save visible on the monitor where the operator clicked, even when a
# fullscreen game occupies another monitor. Position the owner at the current
# cursor location and avoid custom C# compilation entirely.
_POWERSHELL_PREAMBLE = r"""
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8

function ConvertTo-BaiBase64([string]$Text) {
    if ($null -eq $Text) { $Text = '' }
    return [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Text))
}

function Write-BaiResult([string]$Kind, [string]$Text) {
    [Console]::Out.Write($Kind + ':' + (ConvertTo-BaiBase64 $Text))
}

function New-BaiDialogOwner {
    $owner = New-Object System.Windows.Forms.Form
    $owner.ShowInTaskbar = $false
    $owner.TopMost = $true
    $owner.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::None
    $owner.StartPosition = [System.Windows.Forms.FormStartPosition]::Manual
    $cursor = [System.Windows.Forms.Cursor]::Position
    $owner.Left = $cursor.X
    $owner.Top = $cursor.Y
    $owner.Width = 1
    $owner.Height = 1
    $owner.Opacity = 0.01
    [void]$owner.Show()
    [void]$owner.Activate()
    return $owner
}

try {
    Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
"""

_POWERSHELL_EPILOGUE = r"""
}
catch {
    Write-BaiResult 'BAI_DIALOG_ERROR' $_.Exception.Message
    exit 2
}
"""


def _decode_protocol_value(value: str) -> str:
    try:
        raw = base64.b64decode(value.encode("ascii"), validate=True)
        return raw.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise NativeFileDialogUnavailable("Windows file dialog returned an invalid response") from exc


def _parse_protocol(stdout: bytes | str) -> tuple[str, str | None] | None:
    if isinstance(stdout, bytes):
        text = stdout.decode("ascii", errors="replace")
    else:
        text = stdout
    # PowerShell can emit incidental whitespace. Search from the end so the
    # explicit result token wins over any earlier host noise.
    for line in reversed(text.replace("\r", "\n").split("\n")):
        token = line.strip().lstrip("\ufeff")
        if not token:
            continue
        if token == _PROTOCOL_CANCEL:
            return "cancel", None
        if token.startswith(_PROTOCOL_OK):
            return "ok", _decode_protocol_value(token[len(_PROTOCOL_OK) :])
        if token.startswith(_PROTOCOL_ERROR):
            return "error", _decode_protocol_value(token[len(_PROTOCOL_ERROR) :])
    return None


def _safe_process_error(stderr: bytes | str) -> str:
    if isinstance(stderr, bytes):
        # We intentionally do not expose PowerShell's serialized CLIXML. It is
        # unreadable in the GUI and may contain mojibake from Windows code pages.
        raw = stderr.decode("utf-8", errors="replace")
    else:
        raw = stderr
    if "CLIXML" in raw or "<Objs" in raw or "<S S=\"Error\"" in raw:
        return "Windows native file dialog failed inside PowerShell"
    compact = " ".join(raw.split())
    return compact[:500] if compact else "Windows native file dialog failed"


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
                "-OutputFormat",
                "Text",
                "-EncodedCommand",
                encoded,
            ],
            capture_output=True,
            text=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )

        parsed = _parse_protocol(completed.stdout)
        if parsed is not None:
            state, detail = parsed
            if state == "ok":
                assert detail is not None
                if "\x00" in detail or len(detail) > 32_767:
                    raise NativeFileDialogUnavailable("Windows returned an invalid file path")
                return str(Path(detail))
            if state == "cancel":
                return None
            assert detail is not None
            raise NativeFileDialogUnavailable(detail[:500] or "Windows native file dialog failed")

        if completed.returncode != 0:
            raise NativeFileDialogUnavailable(_safe_process_error(completed.stderr))
        raise NativeFileDialogUnavailable("Windows file dialog returned no result")

    def choose_open_srt(self) -> str | None:
        return self._run(
            _POWERSHELL_PREAMBLE
            + r"""
    $owner = $null
    $dialog = $null
    try {
        $owner = New-BaiDialogOwner
        $dialog = New-Object System.Windows.Forms.OpenFileDialog
        $dialog.Title = 'SRT字幕ファイルを選択 / Select SRT subtitle'
        $dialog.Filter = 'SRT subtitle (*.srt)|*.srt|All files (*.*)|*.*'
        $dialog.Multiselect = $false
        $dialog.CheckFileExists = $true
        $dialog.CheckPathExists = $true
        $dialog.RestoreDirectory = $true
        if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {
            Write-BaiResult 'BAI_DIALOG_OK' $dialog.FileName
        }
        else {
            [Console]::Out.Write('BAI_DIALOG_CANCEL')
        }
    }
    finally {
        if ($null -ne $dialog) { $dialog.Dispose() }
        if ($null -ne $owner) { $owner.Close(); $owner.Dispose() }
    }
"""
            + _POWERSHELL_EPILOGUE
        )

    def choose_save_srt(self) -> str | None:
        return self._run(
            _POWERSHELL_PREAMBLE
            + r"""
    $owner = $null
    $dialog = $null
    try {
        $owner = New-BaiDialogOwner
        $dialog = New-Object System.Windows.Forms.SaveFileDialog
        $dialog.Title = 'SRTの保存先を選択 / Choose SRT destination'
        $dialog.Filter = 'SRT subtitle (*.srt)|*.srt|All files (*.*)|*.*'
        $dialog.DefaultExt = 'srt'
        $dialog.AddExtension = $true
        $dialog.OverwritePrompt = $true
        $dialog.CheckPathExists = $true
        $dialog.RestoreDirectory = $true
        if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {
            Write-BaiResult 'BAI_DIALOG_OK' $dialog.FileName
        }
        else {
            [Console]::Out.Write('BAI_DIALOG_CANCEL')
        }
    }
    finally {
        if ($null -ne $dialog) { $dialog.Dispose() }
        if ($null -ne $owner) { $owner.Close(); $owner.Dispose() }
    }
"""
            + _POWERSHELL_EPILOGUE
        )


    def choose_open_media(self) -> str | None:
        """Choose one local media source for TASK-036 ingest.

        The selected host path is returned only to the local caller.  It is not
        persisted by this dialog boundary and is never interpolated into the
        PowerShell program.
        """
        return self._run(
            _POWERSHELL_PREAMBLE
            + r"""
    $owner = $null
    $dialog = $null
    try {
        $owner = New-BaiDialogOwner
        $dialog = New-Object System.Windows.Forms.OpenFileDialog
        $dialog.Title = '動画・音声・画像を選択 / Select media'
        $dialog.Filter = 'Media files|*.mp4;*.mov;*.mkv;*.avi;*.webm;*.m4v;*.wav;*.mp3;*.m4a;*.flac;*.aac;*.ogg;*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tif;*.tiff|Video files|*.mp4;*.mov;*.mkv;*.avi;*.webm;*.m4v|Audio files|*.wav;*.mp3;*.m4a;*.flac;*.aac;*.ogg|Image files|*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tif;*.tiff|All files (*.*)|*.*'
        $dialog.Multiselect = $false
        $dialog.CheckFileExists = $true
        $dialog.CheckPathExists = $true
        $dialog.RestoreDirectory = $true
        if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {
            Write-BaiResult 'BAI_DIALOG_OK' $dialog.FileName
        }
        else {
            [Console]::Out.Write('BAI_DIALOG_CANCEL')
        }
    }
    finally {
        if ($null -ne $dialog) { $dialog.Dispose() }
        if ($null -ne $owner) { $owner.Close(); $owner.Dispose() }
    }
"""
            + _POWERSHELL_EPILOGUE
        )

    def choose_project_folder(self) -> str | None:
        """Choose an existing local Project folder for the desktop shell."""
        return self._run(
            _POWERSHELL_PREAMBLE
            + r"""
    $owner = $null
    $dialog = $null
    try {
        $owner = New-BaiDialogOwner
        $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
        $dialog.Description = 'BAI Video Production プロジェクトフォルダーを選択 / Select Project folder'
        $dialog.ShowNewFolderButton = $true
        if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {
            Write-BaiResult 'BAI_DIALOG_OK' $dialog.SelectedPath
        }
        else {
            [Console]::Out.Write('BAI_DIALOG_CANCEL')
        }
    }
    finally {
        if ($null -ne $dialog) { $dialog.Dispose() }
        if ($null -ne $owner) { $owner.Close(); $owner.Dispose() }
    }
"""
            + _POWERSHELL_EPILOGUE
        )

    def choose_handoff_folder(self) -> str | None:
        """Choose an existing destination folder for deterministic EDITOR_WORK."""
        return self._run(
            _POWERSHELL_PREAMBLE
            + r"""
    $owner = $null
    $dialog = $null
    try {
        $owner = New-BaiDialogOwner
        $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
        $dialog.Description = 'EDITOR_WORK の出力先を選択 / Choose EDITOR_WORK destination'
        $dialog.ShowNewFolderButton = $true
        if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {
            Write-BaiResult 'BAI_DIALOG_OK' $dialog.SelectedPath
        }
        else {
            [Console]::Out.Write('BAI_DIALOG_CANCEL')
        }
    }
    finally {
        if ($null -ne $dialog) { $dialog.Dispose() }
        if ($null -ne $owner) { $owner.Close(); $owner.Dispose() }
    }
"""
            + _POWERSHELL_EPILOGUE
        )

    def choose_encrypted_ppk(self) -> str | None:
        """Choose one encrypted PuTTY PPK v3 file for TASK-059."""
        return self._run(
            _POWERSHELL_PREAMBLE
            + r"""
    $owner = $null
    $dialog = $null
    try {
        $owner = New-BaiDialogOwner
        $dialog = New-Object System.Windows.Forms.OpenFileDialog
        $dialog.Title = '暗号化PPK鍵を選択 / Select encrypted PPK key'
        $dialog.Filter = 'PuTTY private key (*.ppk)|*.ppk'
        $dialog.Multiselect = $false
        $dialog.CheckFileExists = $true
        $dialog.CheckPathExists = $true
        $dialog.RestoreDirectory = $true
        if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {
            Write-BaiResult 'BAI_DIALOG_OK' $dialog.FileName
        }
        else {
            [Console]::Out.Write('BAI_DIALOG_CANCEL')
        }
    }
    finally {
        if ($null -ne $dialog) { $dialog.Dispose() }
        if ($null -ne $owner) { $owner.Close(); $owner.Dispose() }
    }
"""
            + _POWERSHELL_EPILOGUE
        )

    def choose_rfc4716_public_key(self) -> str | None:
        """Choose the separate RFC4716 public-key file for TASK-059."""
        return self._run(
            _POWERSHELL_PREAMBLE
            + r"""
    $owner = $null
    $dialog = $null
    try {
        $owner = New-BaiDialogOwner
        $dialog = New-Object System.Windows.Forms.OpenFileDialog
        $dialog.Title = 'RFC4716公開鍵を選択 / Select RFC4716 public key'
        $dialog.Filter = 'RFC4716 public key (*.pub)|*.pub'
        $dialog.Multiselect = $false
        $dialog.CheckFileExists = $true
        $dialog.CheckPathExists = $true
        $dialog.RestoreDirectory = $true
        if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {
            Write-BaiResult 'BAI_DIALOG_OK' $dialog.FileName
        }
        else {
            [Console]::Out.Write('BAI_DIALOG_CANCEL')
        }
    }
    finally {
        if ($null -ne $dialog) { $dialog.Dispose() }
        if ($null -ne $owner) { $owner.Close(); $owner.Dispose() }
    }
"""
            + _POWERSHELL_EPILOGUE
        )
