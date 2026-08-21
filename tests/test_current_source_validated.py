from pathlib import Path
import sys
import tempfile

from ai_video_production.canonical_game_event import GameKnowledgeKind
from ai_video_production.dbd_entity_aliases import EntityAliasCatalog, EntityAliasRecord, EntityAliasType

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "ai_video_production"

def test_current_source_video_learning_ux_contract():
    text = (SRC / "dbd_training_studio.py").read_text(encoding="utf-8")
    assert "学習スロットと正解ゲーム要素" in text
    assert "登録するスロットのゲーム要素を1件以上選択してください。" in text
    assert "1. 全スロットのCropを確認" in text
    assert "2. 確認したCropを一括登録" in text
    assert "使用中HUD設定:" in text

def test_current_source_trivia_selector_contract():
    text = (SRC / "dbd_training_studio.py").read_text(encoding="utf-8")
    assert 'title="豆知識に関連するゲーム要素を選択"' in text
    assert 'text="名前・略称から選択"' in text
    assert 'trivia_notebook.add(mining_tab, text="動画から候補を作る")' in text
    assert 'trivia_notebook.add(list_tab, text="登録済み・候補一覧")' in text
    assert text.count("open_game_element_selector(") >= 2

def test_current_source_alias_catalog_count_and_search():
    package_before = sys.modules.get("ai_video_production")
    with tempfile.TemporaryDirectory() as td:
        catalog = EntityAliasCatalog(Path(td) / "aliases.sqlite")
        assert catalog.count() == 0
        catalog.put(EntityAliasRecord(
            entity_id="perk_iron_will",
            knowledge_kind=GameKnowledgeKind.PERK,
            alias_text="アイウィル",
            alias_type=EntityAliasType.COMMUNITY_SHORT_NAME,
        ))
        assert catalog.count() == 1
        rows = catalog.search("アイウィル", knowledge_kind=GameKnowledgeKind.PERK, verified_only=False)
        assert len(rows) == 1
        assert rows[0].entity_id == "perk_iron_will"
    assert sys.modules.get("ai_video_production") is package_before
    assert package_before is not None and package_before.__spec__ is not None
