from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_task036_windows_entry_uses_product_cli_without_duplicating_shell_logic():
    entry = (ROOT / "packaging" / "task036_windows_entry.py").read_text(encoding="utf-8")
    assert "from ai_video_production.task036_shell_cli import main" in entry
    assert "run_native_layout_spike" not in entry


def test_task036_pyinstaller_definition_is_one_dir_and_path_portable():
    spec = (ROOT / "packaging" / "task036_shell.spec").read_text(encoding="utf-8")
    assert "COLLECT(" in spec
    assert 'name="BAI Video Production"' in spec
    assert "console=False" in spec
    assert 'collect_all("webview")' in spec
    assert 'schema_directory.glob("*.json")' in spec
    assert "D:\\" not in spec
