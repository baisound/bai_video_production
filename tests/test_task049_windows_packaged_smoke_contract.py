from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from ai_video_production.dbd_commentary_knowledge import DbDTriviaStore
from ai_video_production.game_event_store import GameIntelligenceStore
from ai_video_production.task036_trusted_launcher import Task036LaunchConfiguration


ROOT = Path(__file__).resolve().parents[1]


def test_windows_smoke_script_builds_existing_exe_and_checks_packaged_restart_readback() -> None:
    source = (ROOT / "tools" / "windows" / "run-task049-r9b2-packaged-smoke.ps1").read_text(encoding="utf-8")
    for token in (
        "build-windows-exe.bat",
        "BAI Video Production.exe",
        "create-task049-game-intelligence-fixture.py",
        "Find-ButtonContaining $root 'Game Intelligence'",
        "Wait-ForEventState $first.handle 'NEEDS_REVIEW'",
        "Wait-ForEventState $first.handle 'CONFIRMED'",
        "Wait-ForEventState $second.handle 'CONFIRMED'",
        "承認 / Confirm",
        "task049-r9b2-packaged-smoke.json",
        "provider_execution_started = $false",
        "production_timeline_mutated = $false",
        "resolve_write_performed = $false",
        "[string]$BuildRoot = ''",
        "$env:BVP_TASK048_BUILD_ROOT = $buildRootFull",
        "$package = Join-Path $buildRootFull 'BAI Video Production'",
        "[switch]$SkipBuild",
        "build_reused = [bool]$SkipBuild",
        "$start.UseShellExecute = $false",
        "$start.EnvironmentVariables['BAI_TASK036_LAUNCH_CONFIG']",
        "Observed buttons:",
        "observed elements:",
        "Find-ButtonWithTokens $root @('WINDOW_VAULT', $State)",
        "Wait-ForEnabledButton $first.handle '承認 / Confirm' 5",
        "foreach ($selectionAttempt in 1..3)",
    ):
        assert token in source
    assert "Release" not in source or "public_release_performed" in source


def test_consumer_gate_orchestrates_three_packages_with_safe_bounded_evidence() -> None:
    source = (ROOT / "tools" / "windows" / "run-task049-consumer-gate.ps1").read_text(encoding="utf-8")
    for token in (
        "C:\\home\\baisound\\evidence\\bai-video-production",
        "TASK-049\\windows-consumer-gate",
        "bai-video-production\\TASK-049\\windows-consumer-gate",
        "builds\\t49\\$runDigest",
        "run-task049-r9b2-packaged-smoke.ps1",
        "build-dbd-trivia-editor-exe.bat",
        "build-dbd-training-studio-exe.bat",
        "BAI Video Production.exe",
        "BAI DbD Trivia Editor.exe",
        "BAI DbD Training Studio.exe",
        "candidate_readback = 'PASS'",
        "workspace_template_readback = 'PASS'",
        "real_media_roi_calibration = 'NOT_CONFIRMED'",
        "human_gold_kpi = 'NOT_CONFIRMED'",
        "provider_execution_started = $false",
        "model_or_runtime_acquired = $false",
        "release_or_deploy_performed = $false",
        "Get-Content -LiteralPath $receiptPath",
        'assert PyInstaller.__version__ == "6.22.2"',
        "worktree_build_root = $worktreeBuildRun",
        "System.Security.Cryptography.SHA256",
        "[string]$ExistingMainBuildRoot = ''",
        "[string]$ExistingMainBuildSourceHead = ''",
        "artifact_source_head = $mainBuildSourceHead",
        "[string]$ExistingMainSmokeReceipt = ''",
        "Existing main smoke receipt does not match the exact PASS build artifact.",
        "smoke_receipt_sha256",
        "-SkipBuild",
    ):
        assert token in source
    assert "build-all-windows-release.ps1" not in source


def test_consumer_gate_fixture_is_synthetic_candidate_without_human_gold(tmp_path: Path) -> None:
    root = tmp_path / "consumer-gate-fixture"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "windows" / "create-task049-consumer-gate-fixture.py"),
            "--root",
            str(root),
        ],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    metadata = json.loads(result.stdout)
    assert metadata["rights_basis"] == "SYNTHETIC_CREATED_FOR_LOCAL_TEST"
    assert metadata["trivia_status"] == "CANDIDATE"
    assert metadata["real_media_used"] is False
    assert metadata["private_media_used"] is False
    assert metadata["human_gold_labels_created"] is False
    assert metadata["provider_execution_started"] is False
    assert metadata["model_or_runtime_acquired"] is False
    assert Path(metadata["training_workspace"], "workspace.json").is_file()
    trivia = DbDTriviaStore(metadata["trivia_database"])
    stored = trivia.latest(metadata["trivia_id"])
    assert stored.status.value == "CANDIDATE"
    assert stored.title == metadata["trivia_title"]


def test_fixture_tool_creates_real_store_state_without_real_media_or_external_effects(tmp_path: Path) -> None:
    root = tmp_path / "fixture"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "windows" / "create-task049-game-intelligence-fixture.py"), "--root", str(root)],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    metadata = json.loads(result.stdout)
    assert metadata["real_media"] is False
    assert metadata["provider_execution_started"] is False
    assert metadata["production_timeline_mutated"] is False
    assert metadata["resolve_write_performed"] is False
    store = GameIntelligenceStore(metadata["game_database"])
    event = store.get_event(metadata["event_id"])
    assert event.confirmation_state.value == "NEEDS_REVIEW"
    assert event.state == {"fixture": True, "real_media": False}
    assert Path(metadata["launch_config"]).is_file()
    launch = json.loads(Path(metadata["launch_config"]).read_text(encoding="utf-8"))
    assert launch["resolve"]["sandbox_project"] == "BAI_CAPABILITY_PROBE_TASK049_R9B2_SMOKE"
    assert Task036LaunchConfiguration.load(metadata["launch_config"]).resolve_project == launch["resolve"]["sandbox_project"]
