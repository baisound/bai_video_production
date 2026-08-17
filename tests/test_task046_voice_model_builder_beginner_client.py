from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.voice_model_builder_beginner_client import (
    BeginnerClientSnapshot,
    assert_no_forbidden_effect_surface,
    build_demo_snapshot,
    public_projection,
    render_beginner_html,
    validate_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "voice-model-builder-beginner-client.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / "voice-model-builder-beginner-client.schema.json"


def test_demo_snapshot_matches_schema_and_is_deterministic() -> None:
    first = build_demo_snapshot().to_dict()
    second = build_demo_snapshot().to_dict()
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(first)
    assert BeginnerClientSnapshot(first).canonical_json() == BeginnerClientSnapshot(second).canonical_json()
    assert len(first["steps"]) == 12
    assert first["current_step"] == 2


def test_schema_mirror_is_byte_exact() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()


def test_public_projection_hides_workflow_coordinates() -> None:
    value = public_projection(build_demo_snapshot().to_dict())
    rendered = json.dumps(value, ensure_ascii=False)
    assert "workflow_sha256" not in rendered
    assert "canonical_ref" not in rendered
    assert "未確認" not in rendered or "開始しません" in rendered
    assert all(step["operation_effect_authorized"] is False for step in value["steps"])


def test_html_is_beginner_friendly_and_has_no_action_surface() -> None:
    html = render_beginner_html(build_demo_snapshot().to_dict())
    assert "音声モデル作成ガイド" in html
    assert "学習・音声生成を開始しません" in html
    assert html.count("<li class=") == 12
    assert "<button" not in html
    assert "C:\\" not in html and "E:\\" not in html


@pytest.mark.parametrize(
    "field",
    [
        "execution_started", "dataset_effect_started", "training_started",
        "model_inference_started", "audio_access_started", "publication_started",
    ],
)
def test_effect_flags_cannot_be_forged(field: str) -> None:
    value = build_demo_snapshot().to_dict()
    value[field] = True
    with pytest.raises(ValueError, match="no-effect boundary"):
        validate_snapshot(value)


def test_step_order_and_effect_authority_are_closed() -> None:
    value = build_demo_snapshot().to_dict()
    value["steps"][0]["step_key"] = "START_TRAINING"
    with pytest.raises(ValueError, match="order"):
        validate_snapshot(value)
    value = build_demo_snapshot().to_dict()
    value["steps"][0]["operation_effect_authorized"] = True
    with pytest.raises(ValueError, match="cannot authorize"):
        validate_snapshot(value)


def test_unknown_state_cannot_be_projected_as_complete() -> None:
    value = build_demo_snapshot().to_dict()
    value["workflow_state"] = "UNKNOWN"
    value["client_state"] = "COMPLETE"
    with pytest.raises(ValueError):
        validate_snapshot(value)


def test_tamper_and_unknown_fields_fail_closed() -> None:
    value = build_demo_snapshot().to_dict()
    value["current_step"] = 12
    with pytest.raises(ValueError, match="snapshot_sha256 mismatch"):
        validate_snapshot(value)
    value = build_demo_snapshot().to_dict()
    value["raw_audio_path"] = "owner.wav"
    with pytest.raises(ValueError, match="incomplete or unknown"):
        validate_snapshot(value)


def test_english_projection_is_supported() -> None:
    value = public_projection(build_demo_snapshot(locale="en").to_dict())
    assert value["locale"] == "en"
    assert value["steps"][0]["label"] == "Choose recordings"
    assert value["safety_notice"].startswith("This screen never")


def test_no_forbidden_effect_surface() -> None:
    assert_no_forbidden_effect_surface()
