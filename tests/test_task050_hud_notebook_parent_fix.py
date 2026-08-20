from pathlib import Path
import ast
import re

SOURCE = Path("src/ai_video_production/dbd_training_studio.py")

def source_text():
    return SOURCE.read_text(encoding="utf-8")

def test_source_parses():
    ast.parse(source_text())

def test_notebook_manages_calibration_page_not_canvas_child():
    text = source_text()
    assert 'calibration_page = ttk.Frame(notebook)' in text
    assert 'notebook.add(calibration_page, text="HUD位置を設定")' in text
    assert 'calibration_tab = ttk.Frame(calibration_scroll_canvas, padding=12)' in text

def test_operational_order_uses_notebook_child():
    text = source_text()
    start = text.index("    ordered_tabs = (")
    end = text.index("    for index, tab in enumerate(ordered_tabs):", start)
    block = text[start:end]
    assert "calibration_page" in block
    assert "calibration_tab" not in block

def test_no_notebook_insert_of_nested_calibration_tab():
    text = source_text()
    assert "notebook.insert(index, tab)" in text
    assert """knowledge_import_tab,
        calibration_page,
        video_tab""" in text

def test_scroll_layout_remains_intact():
    text = source_text()
    assert "calibration_scroll_canvas = tk.Canvas(" in text
    assert "calibration_vscroll = ttk.Scrollbar(" in text
    assert "calibration_hscroll = ttk.Scrollbar(" in text
    assert 'move_panel = ttk.LabelFrame(fine, text="位置を移動"' in text
    assert 'edge_panel = ttk.LabelFrame(fine, text="範囲の辺を調整"' in text

def test_crash_shape_is_removed():
    text = source_text()
    start = text.index("    ordered_tabs = (")
    end = text.index("    for index, tab in enumerate(ordered_tabs):", start)
    block = text[start:end]
    assert "calibration_tab," not in block
