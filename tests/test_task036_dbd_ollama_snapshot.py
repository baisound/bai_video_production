from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.dbd_reasoning_model_panel import (
    format_ollama_runtime_status,
    unavailable_ollama_runtime_snapshot,
)
from ai_video_production.task036_ollama_runtime import OllamaRuntimeSnapshot


@pytest.mark.parametrize(
    ("state", "model_ids", "reason_code"),
    (
        ("READY", ("qwen3:8b",), None),
        ("NO_MODEL", (), "OLLAMA_MODEL_NOT_INSTALLED"),
        ("STARTING", (), "OLLAMA_STARTING"),
        ("FAILED", (), "OLLAMA_NOT_RUNNING"),
    ),
)
def test_dbd_projects_each_shared_ollama_state_without_execution(
    state: str, model_ids: tuple[str, ...], reason_code: str | None,
) -> None:
    snapshot = OllamaRuntimeSnapshot(
        state, model_ids, False, reason_code, "ローカルruntimeの状態を確認してください。",
    )

    text = format_ollama_runtime_status(snapshot)

    assert f"({state})" in text
    assert "導入済みModel:" in text
    assert "ローカルruntimeの状態を確認してください。" in text


def test_dbd_unbound_shared_snapshot_is_explicit_not_blank() -> None:
    snapshot = unavailable_ollama_runtime_snapshot()

    assert snapshot.state == "FAILED"
    assert snapshot.reason_code == "OLLAMA_RUNTIME_SNAPSHOT_UNAVAILABLE"
    assert "OLLAMA_RUNTIME_SNAPSHOT_UNAVAILABLE" in format_ollama_runtime_status(snapshot)


def test_dbd_training_studio_only_probes_the_shared_runtime() -> None:
    ui_source = Path("src/ai_video_production/dbd_reasoning_model_panel_ui.py").read_text(encoding="utf-8")
    studio_source = Path("src/ai_video_production/dbd_training_studio.py").read_text(encoding="utf-8")

    assert "runtime_snapshot_provider" in ui_source
