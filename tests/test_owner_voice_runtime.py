from __future__ import annotations

import json
from pathlib import Path

from ai_video_production.owner_voice_runtime import MODEL_FILES, MODEL_REVISION, main, verify_model_root


def test_missing_model_fails_without_loading_or_generation(tmp_path: Path) -> None:
    report = verify_model_root(tmp_path / "missing")
    assert report["result"] == "FAIL"
    assert report["model_revision"] == MODEL_REVISION
    assert report["model_loaded"] is False
    assert report["generation_started"] is False
    assert {item["path"] for item in report["files"]} == set(MODEL_FILES)


def test_model_cli_writes_bounded_failure_report(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    exit_code = main(["model", "--model-root", str(tmp_path / "model"), "--report", str(report_path)])
    assert exit_code == 2
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["result"] == "FAIL"
    assert payload["generation_started"] is False
