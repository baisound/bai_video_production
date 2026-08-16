from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys
import textwrap
import zipfile

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
ISS = ROOT / "packaging" / "task047_obs_voice_capture_installer.iss"
BUILD = ROOT / "tools" / "windows" / "build-task047-obs-installer.ps1"
ACCEPTANCE = ROOT / "tools" / "windows" / "test-task047-obs-installer.ps1"
MANUAL = ROOT / "docs" / "user" / "OBS-VOICE-CAPTURE-PLUGIN.md"
README_JA = ROOT / "README.md"
README_EN = ROOT / "README.en.md"
ASSET_ROOT = ROOT / "packaging" / "release-assets" / "task047"
INSTALLER = ASSET_ROOT / "bai-voice-capture-0.1.0-dev.10-installer.1-windows-x64-setup.exe"
RUNTIME = ASSET_ROOT / "bai-voice-capture-0.1.0-dev.10-windows-x64.zip"


def _text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def test_installer_contract_has_portable_payload_and_no_private_path() -> None:
    text = _text(ISS)
    assert '#ifndef PayloadRoot' in text
    assert 'ExpandConstant(\'{autopf}\\obs-studio\')' in text
    assert re.search(r"[A-Za-z]:\\", text) is None
    assert "BAI_WORKSPACES" not in text
    assert "BAI_AI" not in text


def test_installer_is_bilingual_and_never_auto_launches_obs() -> None:
    text = _text(ISS)
    assert 'Name: "en"' in text
    assert 'Name: "ja"' in text
    assert "ja.ObsPageTitle=" in text
    assert "en.ObsPageTitle=" in text
    assert "[Run]" not in text


def test_installer_preflight_and_exact3_are_fail_closed() -> None:
    text = _text(ISS)
    for token in (
        "GetVersionNumbersString",
        "CreateToolhelp32Snapshot",
        "Process32FirstW",
        "DirectoryIsReparsePoint",
        "DirectoryIsWritable",
        "GetSpaceOnDisk64",
        "ExistingFileIsAllowed",
        "TargetCollision",
        "GetSHA256OfFile(Target1)",
        "GetSHA256OfFile(Target2)",
        "GetSHA256OfFile(Target3)",
    ):
        assert token in text
    assert text.count("uninsneveruninstall") == 3
    assert "automatic rollback is disabled" in text
    assert "RestoreOrRemove(Target1" not in text.split("procedure DeinitializeSetup", 1)[1].split("procedure CurUninstallStepChanged", 1)[0]


def test_installer_preserves_original_ownership_and_journals_repairs() -> None:
    text = _text(ISS)
    assert 'PreviousPluginSha "14839bcad60fe47583a97729e3dc41c23b9f6c06012d5a83a38d8fc04b435b38"' in text
    assert "(CompareText(ActualSha, PreviousSha) = 0)" in text
    assert "Repair/update detected; preserving original exact3 ownership state." in text
    assert "install-journal-v2.jsonl" in text
    assert "install-journal-v2-head.txt" in text
    assert "prev_sha256=" in text
    assert "DeinitializeSetup" in text
    assert "RestoreOrRemove" in text


def test_build_runner_requires_exact_runtime_and_compiler_hashes() -> None:
    text = _text(BUILD)
    assert "ExpectedRuntimeSha256" in text
    assert "ExpectedCompilerSha256" in text
    assert "Runtime ZIP hash mismatch" in text
    assert "ISCC hash mismatch" in text
    assert "OutputDirectory must not already exist" in text
    assert "external_download_performed = $false" in text
    assert "obs_mutated = $false" in text


def test_acceptance_runner_covers_install_repair_collision_and_uninstall() -> None:
    text = _text(ACCEPTANCE)
    for token in (
        "clean-install.log",
        "repair.log",
        "Collision install unexpectedly succeeded",
        "Target remained after uninstall",
        "existing_exact3_restore_on_uninstall",
        "append_only_journal_hash_chain",
        "owner_voice_recorded = $false",
    ):
        assert token in text


def test_beginner_guides_cover_the_complete_flow_and_are_reachable() -> None:
    manual = _text(MANUAL)
    for token in (
        "## 初めて使う方へ（日本語）",
        "### 導入する前の準備",
        "### インストーラーで導入する",
        "### Controllerを開いて保存先を決める",
        "### 録音前にGAINを確認する",
        "### 録音を開始する",
        "### 一時停止して再開する",
        "### 録音を停止してfileを確認する",
        "## Beginner guide (English)",
        "### Prepare the computer",
        "### Install the Plugin",
        "### Open the Controller and select a destination",
        "### Check gain before recording",
        "### Start recording",
        "### Pause and resume",
        "### Stop and verify the result",
    ):
        assert token in manual
    assert "10手順" in manual
    assert "not a fixed ten-step checklist" in manual
    assert "docs/user/OBS-VOICE-CAPTURE-PLUGIN.md" in _text(README_JA)
    assert "docs/user/OBS-VOICE-CAPTURE-PLUGIN.md" in _text(README_EN)


@pytest.mark.skipif(sys.platform != "win32", reason="Inno Setup acceptance is Windows-only")
def test_installer_executes_clean_repair_collision_and_uninstall(tmp_path: pathlib.Path) -> None:
    running = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "if (Get-Process obs64 -ErrorAction SilentlyContinue) { 'RUNNING' } else { 'STOPPED' }",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if running == "RUNNING":
        pytest.skip("A real obs64 process is running; the release installer correctly fails closed")

    source = tmp_path / "FakeObs.cs"
    source.write_text(
        textwrap.dedent(
            """
            using System.Reflection;
            [assembly: AssemblyVersion("32.2.1.0")]
            [assembly: AssemblyFileVersion("32.2.1.0")]
            public static class Program { public static void Main() { } }
            """
        ).strip(),
        encoding="utf-8",
    )
    obs_exe = tmp_path / "obs64.exe"
    vswhere = (
        pathlib.Path(os.environ["ProgramFiles(x86)"])
        / "Microsoft Visual Studio"
        / "Installer"
        / "vswhere.exe"
    )
    installation = subprocess.run(
        [
            str(vswhere),
            "-latest",
            "-products",
            "*",
            "-requires",
            "Microsoft.Component.MSBuild",
            "-property",
            "installationPath",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    csc = pathlib.Path(installation) / "MSBuild" / "Current" / "Bin" / "Roslyn" / "csc.exe"
    assert csc.is_file()
    subprocess.run(
        [
            str(csc),
            "/nologo",
            "/target:exe",
            f"/out:{obs_exe}",
            str(source),
        ],
        check=True,
    )

    payload = tmp_path / "payload"
    with zipfile.ZipFile(RUNTIME) as archive:
        archive.extractall(payload)
    acceptance_root = tmp_path / "bai-task047-installer-acceptance"
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ACCEPTANCE),
            "-InstallerPath",
            str(INSTALLER),
            "-ObsExe",
            str(obs_exe),
            "-PayloadDirectory",
            str(payload),
            "-AcceptanceRoot",
            str(acceptance_root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, (
        f"installer acceptance failed with exit {completed.returncode}\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
    assert "INSTALLER_ACCEPTANCE_PASS" in completed.stdout
