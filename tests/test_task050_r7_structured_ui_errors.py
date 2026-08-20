from pathlib import Path
import re

from ai_video_production import dbd_training_studio


def test_training_studio_has_no_raw_exception_only_error_dialogs():
    source = Path(dbd_training_studio.__file__).read_text(encoding="utf-8")
    pattern = re.compile(r'messagebox\.showerror\([^,\n]+,\s*str\(exc\)\)', re.MULTILINE)
    assert not pattern.search(source)


def test_training_studio_structured_error_helper_is_present():
    source = Path(dbd_training_studio.__file__).read_text(encoding="utf-8")
    assert "def show_operation_error(" in source
    assert "エラーコード:" in source
    assert "次にすること:" in source
