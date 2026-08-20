from pathlib import Path

from ai_video_production.canonical_game_event import GameKnowledgeKind
from ai_video_production.dbd_entity_aliases import (
    EntityAliasCatalog, EntityAliasRecord, EntityAliasReviewStatus, EntityAliasType,
)
from ai_video_production.dbd_training_form_support import EVENT_TYPE_JA, TRIVIA_CATEGORIES


def test_multiple_names_resolve_to_same_perk(tmp_path):
    store = EntityAliasCatalog(tmp_path / "aliases.sqlite")
    records = (
        EntityAliasRecord("perk_iron_will", GameKnowledgeKind.PERK, "鋼の意志", EntityAliasType.OFFICIAL_NAME, review_status=EntityAliasReviewStatus.VERIFIED, priority=100),
        EntityAliasRecord("perk_iron_will", GameKnowledgeKind.PERK, "アイアンウィル", EntityAliasType.OFFICIAL_ENGLISH, reading="あいあんうぃる", review_status=EntityAliasReviewStatus.VERIFIED, priority=90),
        EntityAliasRecord("perk_iron_will", GameKnowledgeKind.PERK, "アイウィル", EntityAliasType.COMMUNITY_SHORT_NAME, reading="あいうぃる", review_status=EntityAliasReviewStatus.VERIFIED, priority=80),
    )
    store.put_many(records)
    assert store.resolve_unique("鋼の意志").entity_id == "perk_iron_will"
    assert store.resolve_unique("アイアンウィル").entity_id == "perk_iron_will"
    assert store.resolve_unique("アイウィル").entity_id == "perk_iron_will"


def test_japanese_abbreviation_can_be_verified(tmp_path):
    store = EntityAliasCatalog(tmp_path / "aliases.sqlite")
    store.put(EntityAliasRecord(
        "perk_monitor_and_abuse", GameKnowledgeKind.PERK, "観虐",
        EntityAliasType.COMMUNITY_SHORT_NAME,
        reading="かんぎゃく", priority=85,
        review_status=EntityAliasReviewStatus.VERIFIED,
    ))
    assert store.resolve_unique("観虐").entity_id == "perk_monitor_and_abuse"


def test_ambiguous_alias_fails_closed(tmp_path):
    store = EntityAliasCatalog(tmp_path / "aliases.sqlite")
    for entity in ("perk_a", "perk_b"):
        store.put(EntityAliasRecord(entity, GameKnowledgeKind.PERK, "同じ呼び方", EntityAliasType.COMMUNITY_NICKNAME, review_status=EntityAliasReviewStatus.VERIFIED))
    try:
        store.resolve_unique("同じ呼び方")
    except ValueError:
        pass
    else:
        raise AssertionError("ambiguous alias must require Human selection")


def test_ui_choices_come_from_existing_event_contract():
    assert "GENERAL" in TRIVIA_CATEGORIES
    assert any(label == "チェイス開始" for label in EVENT_TYPE_JA.values())

def test_blank_search_lists_aliases_without_weakening_alias_validation(tmp_path):
    store = EntityAliasCatalog(tmp_path / "aliases.sqlite")

    store.put_many(
        (
            EntityAliasRecord(
                "perk_a",
                GameKnowledgeKind.PERK,
                "パークA",
                EntityAliasType.OFFICIAL_NAME,
                priority=100,
            ),
            EntityAliasRecord(
                "perk_b",
                GameKnowledgeKind.PERK,
                "パークB",
                EntityAliasType.OFFICIAL_NAME,
                priority=90,
            ),
        )
    )

    rows = store.search(
        "",
        knowledge_kind=GameKnowledgeKind.PERK,
        verified_only=False,
    )

    assert [row.entity_id for row in rows] == ["perk_a", "perk_b"]


def test_blank_unique_resolution_still_fails_closed(tmp_path):
    store = EntityAliasCatalog(tmp_path / "aliases.sqlite")

    try:
        store.resolve_unique("")
    except ValueError as exc:
        assert "1..256" in str(exc)
    else:
        raise AssertionError("blank alias resolution must remain invalid")