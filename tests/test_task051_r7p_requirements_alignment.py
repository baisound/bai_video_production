from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "src" / "ai_video_production" / "dbd_training_studio.py"
OPTIONS = ROOT / "src" / "ai_video_production" / "dbd_runtime_options.py"


def _studio() -> str:
    return STUDIO.read_text(encoding="utf-8")


def test_runtime_options_are_shared_and_japanese() -> None:
    text = OPTIONS.read_text(encoding="utf-8")
    assert "WHISPER_MODEL_OPTIONS_JA" in text
    assert '"自動": "auto"' in text
    studio = _studio()
    assert "dict(WHISPER_MODEL_OPTIONS_JA)" in studio
    assert "analysis_model_display" in studio
    assert 'text="デバイス"' in studio
    assert 'text="計算方式"' in studio
    assert 'text="Device / Compute"' not in studio


def test_video_analysis_has_analysis_and_result_tabs_and_profile_defaults() -> None:
    studio = _studio()
    assert 'analysis_notebook.add(analysis_run_tab,text="解析")' in studio
    assert 'analysis_notebook.add(analysis_result_tab,text="解析結果")' in studio
    assert "active_runtime.default_whisper_model" in studio
    assert "active_runtime.device" in studio
    assert "active_runtime.compute_type" in studio
    assert "analysis_notebook.select(analysis_result_tab)" in studio


def test_game_knowledge_list_removes_image_and_adds_filters() -> None:
    studio = _studio()
    inventory = studio.split("inventory_filter_row = ttk.Frame(inventory_box)", 1)[1].split("def _sync_candidate_alias_index", 1)[0]
    assert 'show="headings"' in inventory
    assert 'heading("#0", text="画像")' not in inventory
    assert 'text="種別"' in inventory
    assert 'text="キーワード検索"' in inventory
    assert "inventory_keyword_filter" in inventory


def test_game_knowledge_detail_uses_human_fields_and_collapsed_diagnostics() -> None:
    studio = _studio()
    edit = studio.split("def edit_knowledge_candidate()", 1)[1].split("def verify_knowledge_candidate()", 1)[0]
    assert 'text="画像"' in edit
    assert "image_path_label" in edit
    assert 'text="ゲーム情報"' in edit
    assert "human_knowledge_fields(row)" in edit
    assert 'text="内部・診断情報を表示"' in edit
    assert "diagnostics_frame.grid_remove()" in edit
