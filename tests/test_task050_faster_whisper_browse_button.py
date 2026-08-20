from pathlib import Path
import ast

SOURCE = Path("src/ai_video_production/dbd_training_studio_foundation_ui.py")

def source_text():
    return SOURCE.read_text(encoding="utf-8")

def test_source_parses():
    ast.parse(source_text())

def test_faster_whisper_cache_row_has_clear_label():
    text = source_text()
    assert '("FasterWhisper / Hugging Face キャッシュ", runtime_vars["model_cache"], False),' in text

def test_faster_whisper_has_folder_browse_button():
    text = source_text()
    assert 'elif label == "FasterWhisper / Hugging Face キャッシュ":' in text
    assert "def browse_model_cache(" in text
    assert "filedialog.askdirectory(" in text
    assert 'text="参照"' in text

def test_model_cache_selection_updates_runtime_var():
    text = source_text()
    assert "target.set(chosen)" in text

def test_runtime_profile_still_saves_model_cache_value():
    text = source_text()
    assert 'faster_whisper_model_cache=runtime_vars["model_cache"].get().strip() or None' in text
