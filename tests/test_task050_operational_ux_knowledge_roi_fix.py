from pathlib import Path
import ast
import json

from ai_video_production.canonical_game_event import GameKnowledgeKind
from ai_video_production.dbd_entity_aliases import EntityAliasCatalog
from ai_video_production.dbd_hud_calibration_editor import RoiPixelEditor
from ai_video_production.dbd_kamigame_candidate_bridge import (
    index_kamigame_candidates_for_search,
    load_kamigame_candidate_summaries,
)
from ai_video_production.dbd_optional_roi_defaults import ensure_optional_roi_initialized

STUDIO = Path("src/ai_video_production/dbd_training_studio.py")


def test_studio_source_parses():
    ast.parse(STUDIO.read_text(encoding="utf-8"))


def test_hud_uses_split_pane_for_controls_and_preview():
    text = STUDIO.read_text(encoding="utf-8")
    assert 'calibration_paned = ttk.Panedwindow(calibration_page, orient="vertical")' in text
    assert "calibration_controls_host" in text
    assert "calibration_preview_host" in text
    assert "preview_canvas_frame" in text
    assert "calibration_preview_hscroll" in text


def test_optional_roi_initialization_is_safe_and_idempotent():
    editor = RoiPixelEditor(source_width=1920, source_height=1080, rois={})
    assert ensure_optional_roi_initialized(editor, "killer_power_hud") is True
    rect = editor.pixel_rect("killer_power_hud")
    assert rect.width > 0 and rect.height > 0
    assert ensure_optional_roi_initialized(editor, "killer_power_hud") is False


def test_kamigame_candidates_become_searchable_without_verified_promotion(tmp_path):
    normalized = tmp_path / "normalized"
    normalized.mkdir()
    perk = {
        "candidate_id": "perk_kamigame_test",
        "name_ja": "鋼の意思",
        "aliases_ja": ["アイウィル"],
        "review_status": "CANDIDATE",
        "detail_url": "https://kamigame.jp/dbd/page/test.html",
    }
    (normalized / "survivor-perks.jsonl").write_text(
        json.dumps(perk, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (normalized / "killer-perks.jsonl").write_text("", encoding="utf-8")
    (normalized / "killers.jsonl").write_text("", encoding="utf-8")

    catalog = EntityAliasCatalog(tmp_path / "entity-aliases.sqlite")
    report = index_kamigame_candidates_for_search(catalog, tmp_path)
    assert report.candidates == 1
    assert catalog.search("鋼の意思", knowledge_kind=GameKnowledgeKind.PERK, verified_only=False)
    assert catalog.search("アイウィル", knowledge_kind=GameKnowledgeKind.PERK, verified_only=False)
    assert catalog.search("鋼の意志", knowledge_kind=GameKnowledgeKind.PERK, verified_only=False)
    assert catalog.search("鋼の意思", knowledge_kind=GameKnowledgeKind.PERK, verified_only=True) == ()


def test_candidate_inventory_loads_names_and_aliases(tmp_path):
    normalized = tmp_path / "normalized"
    normalized.mkdir()
    (normalized / "survivor-perks.jsonl").write_text(
        json.dumps(
            {
                "candidate_id": "perk_a",
                "name_ja": "全力疾走",
                "aliases_ja": ["スプバ"],
                "review_status": "CANDIDATE",
                "detail_url": "https://kamigame.jp/dbd/page/a.html",
            },
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
    (normalized / "killer-perks.jsonl").write_text("", encoding="utf-8")
    (normalized / "killers.jsonl").write_text("", encoding="utf-8")
    rows = load_kamigame_candidate_summaries(tmp_path)
    assert len(rows) == 1
    assert rows[0].name_ja == "全力疾走"
    assert rows[0].aliases_ja == ("スプバ",)


def test_game_information_tab_explains_raw_vs_normalized():
    text = STUDIO.read_text(encoding="utf-8")
    assert "raw に証跡として保存" in text
    assert "normalized/*.jsonl" in text
    assert "取得済みゲーム情報（取込候補 / 確認済み）" in text
    assert "検索用インデックスへ反映" in text
