from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_video_analysis_tab_does_not_bind_paned_helper_to_plain_frame() -> None:
    studio = (ROOT / "src/ai_video_production/dbd_training_studio.py").read_text(encoding="utf-8")
    assert "bind_media_minimum_height(analysis_media" not in studio
    assert "analysis_top.rowconfigure(0,weight=1,minsize=420)" in studio


def test_media_minimum_height_helper_contract_remains_paned_only() -> None:
    helper = (ROOT / "src/ai_video_production/dbd_training_ui_components.py").read_text(encoding="utf-8")
    assert "def bind_media_minimum_height(" in helper
    assert "media_first: bool" in helper
    assert "minimum_pixels: int = 260" in helper
    assert "minimum=" not in helper.split("def bind_media_minimum_height(", 1)[1].split(") -> None:", 1)[0]
