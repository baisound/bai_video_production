from pathlib import Path

def test_workspace_management_panel_uses_grid_in_intro_tab():
    source = Path(
        "src/ai_video_production/dbd_workspace_management_ui.py"
    ).read_text(encoding="utf-8")

    assert 'box.grid(row=2, column=0, sticky="ew", pady=(12, 0))' in source
    assert 'box.pack(fill="x",pady=(12,0))' not in source
