from pathlib import Path
import ast
import sys

from ai_video_production.dbd_training_form_support import (
    SOURCE_MODE_MANUAL_JA,
    SOURCE_MODE_URL_JA,
    TrainingFieldValidationError,
    compose_source_ref,
    validate_game_version_range,
    visual_domain_display,
)

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"src"/"ai_video_production"
STUDIO=SRC/"dbd_training_studio.py"
FORM=SRC/"dbd_training_form_support.py"

def test_parse():
    ast.parse(STUDIO.read_text(encoding="utf-8"))
    ast.parse(FORM.read_text(encoding="utf-8"))

def test_version_100():
    try:
        validate_game_version_range("100","")
    except TrainingFieldValidationError as e:
        assert e.field_ja=="対象ゲームバージョン（開始）"
        assert "8.7.0" in e.guidance_ja
    else:
        raise AssertionError

def test_version_range():
    assert validate_game_version_range("8.7.0","9.0.0")==("8.7.0","9.0.0")

def test_source_modes():
    assert compose_source_ref(SOURCE_MODE_MANUAL_JA,"")=="manual://owner"
    assert compose_source_ref(SOURCE_MODE_URL_JA,"https://example.com")=="https://example.com"

def test_domain_labels():
    assert visual_domain_display("PERK_ICON")=="パークアイコン"
    assert visual_domain_display("KILLER_POWER")=="キラー能力アイコン"

def test_ui_strings():
    t=STUDIO.read_text(encoding="utf-8")
    assert 'text="Target"' not in t
    assert '("Notes", "notes")' not in t
    assert "Registered:" not in t
    assert "visual_source_mode" in t
    assert "trivia_source_mode" in t
    assert "source_mode" in t
    assert "SOURCE_MODE_MANUAL_JA" in t
    assert "SOURCE_MODE_URL_JA" in t
    assert 'text="メモ"' in t
    assert "tk.Text(" in t
    assert "通知の種類（内部コード）" not in t
    assert 'text="通知の種類"' in t

def test_internal_values_preserved():
    t=STUDIO.read_text(encoding="utf-8")
    assert "VisualTrainingDomain.PERK_ICON" in t
    assert "VisualTrainingDomain.KILLER_POWER" in t
    assert "manual://owner" in t
    assert sys.modules["ai_video_production"].__spec__ is not None
