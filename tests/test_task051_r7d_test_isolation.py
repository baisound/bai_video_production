from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_no_task051_support_test_replaces_package_module():
    for name in (
        "test_current_source_validated.py",
        "test_task050_sqlite_windows_lock_fix.py",
        "test_task051_r1_training_presentation.py",
    ):
        text=(ROOT/"tests"/name).read_text(encoding="utf-8")
        assert 'sys.modules["ai_video_production"] =' not in text
        assert "types.ModuleType(\"ai_video_production\")" not in text
