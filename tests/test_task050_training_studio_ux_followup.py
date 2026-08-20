from pathlib import Path

from ai_video_production.dbd_entity_aliases import (
    EntityAliasCatalog,
    EntityAliasRecord,
    EntityAliasType,
)
from ai_video_production.canonical_game_event import GameKnowledgeKind

def test_alias_catalog_count_and_kind_filtered_search(tmp_path):
    catalog = EntityAliasCatalog(tmp_path / "aliases.sqlite")
    assert catalog.count() == 0
    catalog.put(EntityAliasRecord(
        entity_id="perk_iron_will",
        knowledge_kind=GameKnowledgeKind.PERK,
        alias_text="アイウィル",
        alias_type=EntityAliasType.COMMUNITY_SHORT_NAME,
    ))
    assert catalog.count() == 1
    rows = catalog.search("アイウィル", knowledge_kind=GameKnowledgeKind.PERK, verified_only=False)
    assert rows and rows[0].entity_id == "perk_iron_will"

def test_video_learning_ui_explains_required_game_element_before_preview():
    source = Path("src/ai_video_production/dbd_training_studio.py").read_text(encoding="utf-8")

    # R3 contract: multi-slot learning makes the required answer assignment explicit.
    assert "学習スロットと正解ゲーム要素" in source
    assert "登録するスロットのゲーム要素を1件以上選択してください。" in source

    # Candidate selection is assisted by Knowledge/Alias and remains human-confirmed.
    assert "候補はKnowledge/Aliasから表示" in source
    assert "open_game_element_selector(" in source

    # R3 is a two-stage Human workflow: inspect all crops, then register the reviewed batch.
    assert "1. 全スロットのCropを確認" in source
    assert "2. 確認したCropを一括登録" in source
    assert "先に複数Cropプレビューを作成してください。" in source

    # The active HUD profile and exact crop geometry are surfaced to the operator.
    assert "使用中HUD設定:" in source
    assert "複数Cropプレビュー" in source
    assert "x={rect.x} y={rect.y} w={rect.width} h={rect.height}" in source

def test_trivia_search_uses_visible_selector():
    source = Path("src/ai_video_production/dbd_training_studio.py").read_text(encoding="utf-8")
    assert "豆知識に関連するゲーム要素を選択" in source
    assert "open_game_element_selector(" in source
