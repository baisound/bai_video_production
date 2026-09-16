from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "windows" / "build-all-windows-release.ps1"
TASK = ROOT / "docs" / "ai-team" / "tasks" / "TASK-096" / "task.md"
RUNBOOK = ROOT / "docs" / "windows" / "BUILDING-ALL-WINDOWS-RELEASE.md"
INDEX = ROOT / "docs" / "windows" / "WINDOWS-EXE-BUILD-INDEX.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_orchestrator_reuses_every_authoritative_builder() -> None:
    text = _text(SCRIPT)
    for required in (
        "build-windows-exe.bat",
        "build-dbd-training-studio-exe.bat",
        "build-dbd-trivia-editor-exe.bat",
        "build-task063-main-installer.ps1",
        "build-task092-dbd-utility-installers.ps1",
        "build-task046-voice-model-builder-installer.ps1",
        "build-task047-obs-installer.ps1",
        "build-task093-owner-voice-runtime-installer.ps1",
        "python -m build",
    ):
        assert required in text
    assert "PyInstaller" not in text.split("Invoke-BuildStage 'main-exe'", 1)[1]
    assert ".iss" not in text


def test_orchestrator_has_complete_artifact_manifest_contract() -> None:
    text = _text(SCRIPT)
    for product in (
        "BAI Video Production",
        "BAI DbD Training Studio",
        "BAI DbD Trivia Editor",
        "BAI Voice Model Builder",
        "BAI Voice Capture",
        "BAI Owner Voice Runtime",
        "BAI Windows Release Bundle",
    ):
        assert product in text
    for required in (
        "SHA256SUMS.txt",
        "build-manifest.json",
        "SUMMARY.txt",
        "logs\\build.log",
        "Get-FileHash -Algorithm SHA256",
        "Manifest read-back verification failed",
        "Expected 15 release artifacts",
        "executable_components",
        "internal-key-helper",
        "internal-meter-controller",
        "internal-meter-worker",
        "Required EXE component is missing",
        "relative path",
    ):
        if required == "relative path":
            assert "path = $relative" in text
        else:
            assert required in text


def test_orchestrator_fails_closed_before_output_and_never_publishes() -> None:
    text = _text(SCRIPT)
    assert text.index("$PreflightOnly") < text.index("New-Item -ItemType Directory -Path $runDirectory")
    for required in (
        "OutputRoot must stay inside this exact worktree",
        "OutputRoot must not be a drive root or its direct child",
        "OutputRoot crosses a reparse point",
        "Run directory already exists",
        "Source worktree is dirty",
        "-AllowDirtySource",
    ):
        assert required in text
    lowered = text.lower()
    for forbidden in (
        "gh release create",
        "git push",
        "git tag",
        "invoke-webrequest",
        "start-process",
    ):
        assert forbidden not in lowered


def test_orchestrator_exit_codes_are_stable_and_documented() -> None:
    text = _text(SCRIPT)
    task = _text(TASK)
    runbook = _text(RUNBOOK)
    for code in (0, 2, 3, 10, 11, 12, 13, 20, 21, 22, 23, 24, 30, 31, 99):
        assert f"`{code}`" in runbook
    for task_code in (0, 2, 3, 13, 20, 24, 30, 31, 99):
        assert f"`{task_code}`" in task
    assert "`10`–`12`" in task
    assert "`20`–`24`" in task
    for stage, code in (
        ("main-exe", 10),
        ("dbd-training-studio-exe", 11),
        ("dbd-trivia-editor-exe", 12),
        ("python-distributions", 13),
        ("main-installer", 20),
        ("dbd-installers", 21),
        ("voice-model-builder", 22),
        ("voice-capture-installer", 23),
        ("owner-voice-runtime-installer", 24),
        ("distribution-packaging", 30),
        ("manifest-and-checksums", 31),
    ):
        assert f"Invoke-BuildStage '{stage}' {code}" in text


def test_dbd_builders_accept_fresh_caller_owned_roots() -> None:
    training = _text(ROOT / "build-dbd-training-studio-exe.bat")
    trivia = _text(ROOT / "build-dbd-trivia-editor-exe.bat")
    assert "BVP_TASK049_TRAINING_BUILD_ROOT" in training
    assert "BVP_TASK049_TRIVIA_BUILD_ROOT" in trivia
    for text in (training, trivia):
        assert 'if exist "%BUILD_ROOT%"' in text
        assert "Build output already exists" in text
        assert '--distpath "%BUILD_ROOT%"' in text


def test_user_entry_is_one_command_and_developer_detail_is_separate() -> None:
    index = _text(INDEX)
    runbook = _text(RUNBOOK)
    command = ".\\tools\\windows\\build-all-windows-release.ps1"
    assert command in index
    assert "result=PASS" in index and "exit_code=0" in index
    assert command in runbook
    assert "## Exit codes and diagnosis" in runbook
    assert "## Publication boundary" in runbook


def test_help_is_effect_zero_on_windows() -> None:
    if os.name != "nt":
        return
    powershell = shutil.which("powershell.exe")
    assert powershell is not None
    output_root = ROOT / ".artifacts"
    before = sorted(path.relative_to(ROOT) for path in output_root.rglob("*")) if output_root.exists() else []
    completed = subprocess.run(
        [powershell, "-NoProfile", "-NonInteractive", "-File", str(SCRIPT), "-Help"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    after = sorted(path.relative_to(ROOT) for path in output_root.rglob("*")) if output_root.exists() else []
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert command_in_output(completed.stdout)
    assert before == after


def command_in_output(output: str) -> bool:
    return ".\\tools\\windows\\build-all-windows-release.ps1" in output
