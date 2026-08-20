from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "src" / "ai_video_production" / "dbd_training_studio.py"


def test_studio_r3_integration():
    text = STUDIO.read_text(encoding="utf-8")
    ast.parse(text)
    assert "resolve_training_hud_profile(" in text
    assert "slot_specifications(" in text
    assert "alias_choices(" in text
    assert "複数Cropプレビュー" in text
    assert "全スロットのCropを確認" in text
    assert "確認したCropを一括登録" in text


def test_manual_profile_is_advanced_not_primary():
    text = STUDIO.read_text(encoding="utf-8")
    assert "詳細設定：HUDプロファイルJSON（任意）" in text
    assert "使用中HUD設定:" in text


def test_old_single_slot_fields_removed_from_video_learning_block():
    text = STUDIO.read_text(encoding="utf-8")
    start = text.index("    # ---- Video batch learning tab")
    end = text.index("    # ---- Image training data", start)
    block = text[start:end]
    assert "video_vars[\"slot\"]" not in block
    assert "video_vars[\"label\"]" not in block
    assert "スロット（パーク/サバイバー 0～3" not in block
