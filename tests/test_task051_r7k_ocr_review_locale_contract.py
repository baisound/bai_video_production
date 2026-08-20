from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "src" / "ai_video_production" / "dbd_training_workspace.py"
REVIEW = ROOT / "src" / "ai_video_production" / "dbd_training_review_ui_v2.py"


def test_ocr_vocabulary_contract_uses_locale_not_language():
    source = WORKSPACE.read_text(encoding="utf-8")
    start = source.index("class OcrVocabularySample:")
    block = source[start:start + 1200]
    assert 'locale: str = "ja-JP"' in block
    assert "language:" not in block


def test_review_surface_reads_ocr_locale_contract():
    source = REVIEW.read_text(encoding="utf-8")
    assert '"日本語" if item.locale == "ja-JP" else item.locale' in source
    assert "item.language" not in source
