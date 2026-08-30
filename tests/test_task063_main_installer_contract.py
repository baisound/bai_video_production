from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
ISS = ROOT / "packaging" / "task063_main_installer.iss"
BUILD = ROOT / "tools" / "windows" / "build-task063-main-installer.ps1"
ACCEPTANCE = ROOT / "tools" / "windows" / "test-task063-main-installer.ps1"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_main_installer_allows_selected_destination_and_uses_relative_bridge() -> None:
    text = _text(ISS)
    assert "DisableDirPage=yes" not in text
    assert "DefaultDirName={localappdata}\\Programs\\BAI Video Production" in text
    assert "{app}\\data\\montage-learning-bridge" in text
    assert "--install-root \"" in text
    assert "--bvp-installer-bridge provision" in text
    assert "--bvp-installer-bridge discover" in text
    assert "--receipt-output" not in text
    assert r"C:\ProgramData\BAI Video Production\montage-learning-bridge" not in text


def test_main_installer_is_per_user_reparse_checked_and_preserves_data() -> None:
    text = _text(ISS)
    assert "PrivilegesRequired=lowest" in text
    assert "DirectoryIsReparsePoint" in text
    assert "BuildExistingAncestorSnapshot" in text
    assert "GetFileInformationByHandle" in text
    assert "CurStep = ssInstall" in text
    assert "PreparedAncestorSnapshot" in text
    assert "BridgeProvisionFailed" in text
    assert "[UninstallDelete]" not in text
    assert "preserves learning data" in text
    assert re.search(r"[A-Za-z]:\\", text) is None


def test_build_hash_binds_payload_and_acceptance_is_bounded() -> None:
    build = _text(BUILD)
    acceptance = _text(ACCEPTANCE)
    for token in (
        "Get-FileHash -Algorithm SHA256",
        "payload_tree_sha256",
        "PayloadTreeSha",
        "Inno Setup compilation failed",
    ):
        assert token in build
    for token in (
        "test-install",
        "ConvertTo-NormalizedAbsolutePath",
        "Test-IsBoundedInstallRoot",
        "Get-SafeAncestorSnapshot",
        "[IO.Path]::DirectorySeparatorChar",
        "[StringComparison]::OrdinalIgnoreCase",
        "bridge-instance.json",
        "installer-readback.json",
        "connector_enabled",
        "activation_authorized",
    ):
        assert token in acceptance
    assert "$root.StartsWith($expectedPrefix" not in acceptance
    assert "test-install-evil" not in acceptance


@pytest.mark.parametrize(
    ("candidate", "accepted"),
    [
        (r"D:\BAI\BAI VIDEO PRODUCTION FOR DRFX\test-install", True),
        (r"d:\bai\bai video production for drfx\test-install\child\..", True),
        (r"D:/BAI/BAI VIDEO PRODUCTION FOR DRFX/test-install/child/", True),
        (r"D:\BAI\BAI VIDEO PRODUCTION FOR DRFX\test-install-evil", False),
        (r"D:\BAI\BAI VIDEO PRODUCTION FOR DRFX\test-install\..\escape", False),
        (r"relative\test-install", False),
        (r"C:\test-install", False),
    ],
)
def test_acceptance_root_validation_is_boundary_aware_on_windows(
    candidate: str,
    accepted: bool,
) -> None:
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("Windows PowerShell is unavailable")
    completed = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(ACCEPTANCE),
            "-InstallRoot",
            candidate,
            "-ValidateRootOnly",
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if accepted:
        assert completed.returncode == 0, completed.stderr
        assert '"effect":"NONE"' in completed.stdout
    else:
        assert completed.returncode != 0
        assert "BOUNDED_ROOT_VALID" not in completed.stdout
