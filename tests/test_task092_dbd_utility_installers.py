from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
ISS = ROOT / "packaging" / "task092_dbd_utility_installer.iss"
BUILD = ROOT / "tools" / "windows" / "build-task092-dbd-utility-installers.ps1"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_two_dbd_installers_have_stable_product_identities_and_names() -> None:
    text = _text(BUILD)
    for token in (
        "BAI DbD Training Studio",
        "C6B19B19-D58E-4A73-B97C-BE18FDD5019E",
        "BAI DbD Training Studio.exe",
        "bai-dbd-training-studio-$Version-windows-x64-setup",
        "BAI DbD Trivia Editor",
        "D419E021-D94F-46F2-92D6-E60533342402",
        "BAI DbD Trivia Editor.exe",
        "bai-dbd-trivia-editor-$Version-windows-x64-setup",
    ):
        assert token in text


def test_build_is_fresh_contained_and_hash_binds_each_payload() -> None:
    text = _text(BUILD)
    for token in (
        "Installer output must be contained by the repository worktree",
        "Installer output already exists; use a fresh operation directory",
        "Expected executable is missing from payload",
        "Get-FileHash -Algorithm SHA256",
        "payload_tree_sha256",
        "PayloadTreeSha",
        '"/O$output"',
    ):
        assert token in text


def test_installer_is_per_user_bilingual_and_never_auto_launches() -> None:
    text = _text(ISS)
    assert "PrivilegesRequired=lowest" in text
    assert 'Name: "en"' in text
    assert 'Name: "ja"' in text
    assert "DefaultDirName={localappdata}\\Programs\\{#AppName}" in text
    assert "[Run]" not in text
    assert "Uninstallable=yes" in text
    assert "PayloadTreeSha256" in text


def test_installer_rejects_unsafe_destination_before_payload_effects() -> None:
    text = _text(ISS)
    for token in (
        "InstallRootIsContained",
        "FindDeepestExistingAncestor",
        "BuildExistingAncestorSnapshot",
        "DirectoryIsReparsePoint",
        "ReadDirectoryIdentity",
        "PrepareToInstall",
        "PreparedAncestorsStillMatch",
        "CurStep = ssInstall",
        "CurStep = ssPostInstall",
        "UnsafeDestination",
    ):
        assert token in text
    assert re.search(r"[A-Za-z]:\\", text) is None
