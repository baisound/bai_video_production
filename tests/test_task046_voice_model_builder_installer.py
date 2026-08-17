from __future__ import annotations

import pathlib
import re
import os
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
ISS = ROOT / "packaging" / "task046_voice_model_builder_installer.iss"
BUILD = ROOT / "tools" / "windows" / "build-task046-voice-model-builder-installer.ps1"
ACCEPTANCE = ROOT / "tools" / "windows" / "test-task046-voice-model-builder-installer.ps1"
LAUNCHER = ROOT / "tools" / "windows" / "task046_voice_model_builder_launcher.py"
NOTICES = ROOT / "tools" / "windows" / "task046_collect_third_party_notices.py"
GUIDE = ROOT / "docs" / "user" / "VOICE-MODEL-BUILDER.md"


def _text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def test_launcher_performs_only_contained_synthetic_self_check() -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, str(LAUNCHER), "--self-check", "--locale", "ja"],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    text = _text(LAUNCHER)
    for forbidden in ("subprocess", "requests", "torch", "wave", "pathlib", "open("):
        assert forbidden not in text


def test_installer_is_bilingual_per_user_and_never_auto_launches() -> None:
    text = _text(ISS)
    assert 'AppId={{4DA96B8F-C27E-4AD8-B7C5-5F8EF105AEEA}' in text
    assert 'PrivilegesRequired=lowest' in text
    assert '{localappdata}\\Programs\\BAI Voice Model Builder' in text
    assert 'Name: "en"' in text and 'Name: "ja"' in text
    assert 'ja.DataNotice=' in text and 'en.DataNotice=' in text
    assert "[Run] section" in text and "\n[Run]\n" not in text
    assert "ChangesEnvironment=no" in text


def test_installer_checks_collision_disk_reparse_and_exact_readback() -> None:
    text = _text(ISS)
    for token in (
        "DirectoryIsReparsePoint",
        "GetSpaceOnDisk64",
        "ExistingFileIsAllowed",
        "TargetCollision",
        "GetSHA256OfFile(TargetExecutable)",
        "GetSHA256OfFile(TargetGuide)",
        "GetSHA256OfFile(TargetLicense)",
        "GetSHA256OfFile(TargetManifest)",
        "GetSHA256OfFile(TargetNotice)",
    ):
        assert token in text
    assert "[UninstallDelete]" not in text
    assert re.search(r"[A-Za-z]:\\", text) is None


def test_build_is_hash_bound_and_has_no_runtime_effect() -> None:
    text = _text(BUILD)
    for token in (
        "ExpectedPythonSha256",
        "ExpectedCompilerSha256",
        "PyInstaller 6.22.0 is required",
        "jsonschema_version",
        "python_sha256",
        "package_manifest_sha256",
        "third_party_notice_sha256",
        "model_download_started = $false",
        "training_started = $false",
        "audio_access_started = $false",
        "publication_started = $false",
    ):
        assert token in text
    assert "Invoke-WebRequest" not in text
    assert "Start-Process" not in text


def test_acceptance_covers_install_repair_collision_self_check_and_uninstall() -> None:
    text = _text(ACCEPTANCE)
    for token in (
        "clean install",
        "exact repair",
        "collision install",
        "--self-check",
        "WaitForExit(30000)",
        "Uninstall failed",
        "User data sentinel was changed or removed",
        "THIRD-PARTY-NOTICES.txt",
    ):
        assert token in text


def test_beginner_guide_is_bilingual_and_reachable_from_both_readmes() -> None:
    guide = _text(GUIDE)
    for token in (
        "## このアプリは何ですか",
        "## インストールする",
        "## 起動して確認する",
        "## 将来の完成形",
        "## アンインストールとデータ",
        "## English guide",
        "### Before installation",
        "### Install and open",
        "### Safety and future workflow",
        "E:\\BAI_AI",
        "P_OBS_PLUGIN_DEVELOPMENT_COMPLETE",
    ):
        if token == "P_OBS_PLUGIN_DEVELOPMENT_COMPLETE":
            assert token not in guide
        else:
            assert token in guide
    assert "docs/user/VOICE-MODEL-BUILDER.md" in _text(ROOT / "README.md")
    assert "docs/user/VOICE-MODEL-BUILDER.md" in _text(ROOT / "README.en.md")


def test_notice_collector_is_closed_exact_and_path_free() -> None:
    text = _text(NOTICES)
    for component in (
        '"pyinstaller"',
        '"jsonschema"',
        '"attrs"',
        '"jsonschema-specifications"',
        '"referencing"',
        '"rpds-py"',
        '"CPython"',
        '"Tcl/Tk"',
    ):
        assert component in text
    assert "private_path_exposed" in text
    assert "os.environ" not in text


def test_public_sources_contain_no_private_absolute_paths_or_credentials() -> None:
    combined = "\n".join(_text(path) for path in (ISS, BUILD, ACCEPTANCE, LAUNCHER, NOTICES, GUIDE))
    assert "BAI_WORKSPACES" not in combined
    assert "sk-" not in combined
    assert "AppData\\Local\\Temp" not in combined
