from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "src" / "ai_video_production" / "dbd_training_studio.py"
SHARED = ROOT / "src" / "ai_video_production" / "dbd_training_video_player.py"


def test_integration():
    studio = STUDIO.read_text(encoding="utf-8")
    shared = SHARED.read_text(encoding="utf-8")
    ast.parse(studio)
    ast.parse(shared)
    assert "video_learning_player = TkTrainingMediaPlayer(" in studio
    assert "calibration_video_session = TkTrainingMediaSession(" in studio
    assert "apply_calibration_memory_preview" in studio
    assert "PersistentPreviewWorker" in shared
    assert "TkVideoTransportBar" in shared
    assert 'PhotoImage(data=frame.tk_photo_data())' in shared
    assert 'tk.PhotoImage(data=frame.tk_photo_data())' in studio  # HUD overlay painter
    assert '"preview_image": None' in studio
    assert '("-10秒", -300)' not in studio and '("-1秒", -30)' not in studio
    assert "動画プレビュー" in shared
    assert (
        'text="Cropプレビュー"' in studio
        or 'text="複数Cropプレビュー"' in studio
    )
