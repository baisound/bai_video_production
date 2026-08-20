from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from ai_video_production.game_event_store import GameIntelligenceStore


ROOT = Path(__file__).resolve().parents[1]


def test_windows_smoke_script_builds_existing_exe_and_checks_packaged_restart_readback() -> None:
    source = (ROOT / "tools" / "windows" / "run-task049-r9b2-packaged-smoke.ps1").read_text(encoding="utf-8")
    for token in (
        "build-windows-exe.bat",
        "BAI Video Production.exe",
        "create-task049-game-intelligence-fixture.py",
        "G Game Intelligence",
        "Wait-ForEventState $first.root 'NEEDS_REVIEW'",
        "Wait-ForEventState $first.root 'CONFIRMED'",
        "Wait-ForEventState $second.root 'CONFIRMED'",
        "承認 / Confirm",
        "task049-r9b2-packaged-smoke.json",
        "provider_execution_started = $false",
        "production_timeline_mutated = $false",
        "resolve_write_performed = $false",
    ):
        assert token in source
    assert "Release" not in source or "public_release_performed" in source


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
