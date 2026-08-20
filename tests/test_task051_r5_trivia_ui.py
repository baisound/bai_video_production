from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]
STUDIO=ROOT/"src"/"ai_video_production"/"dbd_training_studio.py"

def test_three_section_trivia_ui_and_video_transport():
    text=STUDIO.read_text(encoding="utf-8")
    ast.parse(text)
    assert 'trivia_notebook.add(manual_tab, text="手動で登録")' in text
    assert 'trivia_notebook.add(mining_tab, text="動画から候補を作る")' in text
    assert 'trivia_notebook.add(list_tab, text="登録済み・候補一覧")' in text
    assert "trivia_player = TkTrainingMediaPlayer(" in text
    assert "動画を文字起こしして候補を抽出" in text
    assert "既存の文字起こしデータから候補を抽出" in text

def test_candidate_list_has_required_actions_and_provenance():
    text=STUDIO.read_text(encoding="utf-8")
    for token in (
        "状態","タイトル","本文","関連ゲーム要素","使用場面","情報源・動画","時間",
        "詳細・編集","確認済みにする","複製","却下","削除（履歴は保持）",
    ):
        assert token in text
    assert "format_time_range(metadata)" in text

def test_asr_user_labels_are_japanese_while_internal_values_remain():
    text=STUDIO.read_text(encoding="utf-8")
    assert "小（small・推奨）" in text
    assert "自動" in text
    assert "省メモリ（int8）" in text
    assert "日本語" in text
    assert 'trivia_model = tk.StringVar(value=active_runtime.default_whisper_model or "small")' in text
    assert 'cache_directory=runtime_model_cache' in text
