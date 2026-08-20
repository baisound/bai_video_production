from pathlib import Path
import ast

R = Path(__file__).resolve().parents[1]
S = R / "src" / "ai_video_production" / "dbd_training_studio.py"
T = R / "src" / "ai_video_production" / "dbd_video_transport.py"


def test_ui():
    t = S.read_text(encoding="utf-8")
    ast.parse(t)
    assert 'visual_notebook.add(visual_video_tab, text="動画から登録")' in t
    assert 'visual_notebook.add(visual_manual_tab, text="手動で登録")' in t
    assert 'visual_notebook.add(visual_list_tab, text="登録済み一覧")' in t
    assert "visual_player = TkTrainingMediaPlayer(" in t
    assert 'ocr_notebook.add(ocr_video_tab, text="動画から抽出")' in t
    assert 'ocr_notebook.add(ocr_manual_tab, text="手動で登録")' in t
    assert 'ocr_notebook.add(ocr_list_tab, text="登録済み一覧")' in t
    assert "ocr_player = TkTrainingMediaPlayer(" in t
    assert "この通知の意味・説明" in t
    assert "通知の種類（内部コード）" not in t


def test_transport_ja():
    t = T.read_text(encoding="utf-8")
    assert "STATE_JA" in t and "self.model.state.value" not in t
