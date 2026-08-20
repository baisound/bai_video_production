from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]
FOUNDATION=ROOT/"src"/"ai_video_production"/"dbd_training_studio_foundation_ui.py"
REVIEW=ROOT/"src"/"ai_video_production"/"dbd_training_review_ui_v2.py"

def test_review_tab_name_and_v2_module():
    foundation=FOUNDATION.read_text(encoding="utf-8")
    review=REVIEW.read_text(encoding="utf-8")
    ast.parse(foundation); ast.parse(review)
    assert 'text="学習・登録データを確認"' in foundation
    assert "dbd_training_review_ui_v2" in foundation

def test_required_review_subtabs_exist():
    text=REVIEW.read_text(encoding="utf-8")
    for label in (
        "すべて","ゲーム情報","画像・Crop学習","右上通知",
        "実況・豆知識","Human Gold / その他",
    ):
        assert f'text="{label}"' in text

def test_dashboard_and_zero_state_contracts():
    text=REVIEW.read_text(encoding="utf-8")
    assert "候補" in text and "確認済み" in text
    assert "まだ登録されていません" in text
    assert "Human Goldの正式な保存契約" in text

def test_data_type_specific_actions():
    text=REVIEW.read_text(encoding="utf-8")
    for token in (
        "確認済みにする","却下","正解ラベルを選び直す",
        "学習データから削除","選択通知を削除",
    ):
        assert token in text
