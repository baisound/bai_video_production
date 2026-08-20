from pathlib import Path
import ast

SOURCE = Path("src/ai_video_production/dbd_training_studio.py")

def source_text():
    return SOURCE.read_text(encoding="utf-8")

def test_source_parses():
    ast.parse(source_text())

def test_hud_tab_has_scrollbars_and_mousewheel():
    text = source_text()
    assert "calibration_vscroll = ttk.Scrollbar" in text
    assert "calibration_hscroll = ttk.Scrollbar" in text
    assert "calibration_mousewheel" in text
    assert "refresh_calibration_scrollregion" in text

def test_hud_adjustments_are_two_column_groups():
    text = source_text()
    assert 'move_panel = ttk.LabelFrame(fine, text="位置を移動"' in text
    assert 'edge_panel = ttk.LabelFrame(fine, text="範囲の辺を調整"' in text
    assert 'move_panel.grid(row=0, column=0' in text
    assert 'edge_panel.grid(row=0, column=1' in text

def test_lower_media_area_places_video_left_and_operations_right():
    text = source_text()
    assert 'calibration_media_paned = ttk.Panedwindow(' in text
    assert 'calibration_preview_host, orient="horizontal"' in text
    assert 'calibration_media_paned.add(calibration_video_host, weight=3)' in text
    assert 'calibration_media_paned.add(calibration_side_host, weight=2)' in text
    assert 'preview_canvas_frame = ttk.Frame(calibration_video_host)' in text
    assert 'calibration_ops = ttk.Frame(calibration_side_host)' in text
    assert 'seek.grid(row=0, column=0' in text
    assert 'profile_actions.grid(row=1, column=0' in text

def test_long_old_english_action_labels_removed():
    text = source_text()
    assert "Load preview" not in text
    assert "Save versioned profile + anchors" not in text
    assert "Test auto profile + anchor correction" not in text
    assert "Registered profiles" not in text
    assert "Load profile" not in text

def test_compact_japanese_action_labels_present():
    text = source_text()
    assert "プレビューを読み込む" in text
    assert "HUD設定を保存" in text
    assert "自動補正をテスト" in text
    assert "登録済みHUD設定" in text

def test_old_grid_collisions_are_removed():
    text = source_text()
    assert "control_row = ttk.Frame(calibration_tab)" not in text
    assert "profile_row = ttk.Frame(calibration_tab)" not in text
    assert 'calibration_scroll_canvas.grid(row=0, column=0, sticky="nsew")' in text
    assert 'calibration_vscroll.grid(row=0, column=1, sticky="ns")' in text
    assert 'calibration_hscroll.grid(row=1, column=0, sticky="ew")' in text
