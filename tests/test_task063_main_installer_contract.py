from __future__ import annotations

from pathlib import Path
import re


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
    assert r"C:\ProgramData\BAI Video Production\montage-learning-bridge" not in text


def test_main_installer_is_per_user_reparse_checked_and_preserves_data() -> None:
    text = _text(ISS)
    assert "PrivilegesRequired=lowest" in text
    assert "DirectoryIsReparsePoint" in text
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
        "bridge-instance.json",
        "installer-readback.json",
        "connector_enabled",
        "activation_authorized",
    ):
        assert token in acceptance
