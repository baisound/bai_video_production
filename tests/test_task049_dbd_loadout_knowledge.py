import hashlib
from pathlib import Path

from ai_video_production.canonical_game_event import GameKnowledgeKind
from ai_video_production.dbd_loadout_knowledge import (
    DbDLoadoutKnowledgeStore, LoadoutKnowledgeKind, LoadoutKnowledgeRevision,
    LoadoutKnowledgeSource, LoadoutKnowledgeStatus,
)
from ai_video_production.dbd_perk_knowledge import PerkEnvironment


def test_item_addon_store_resolves_patch_compatible_verified_revisions(tmp_path: Path) -> None:
    store = DbDLoadoutKnowledgeStore(tmp_path / "loadout.sqlite3")
    source = LoadoutKnowledgeSource("src-loadout", "MANUAL_VERIFIED", "manual://owner", hashlib.sha256(b"loadout").hexdigest())
    store.put_source(source)
    store.put_revision(LoadoutKnowledgeRevision(
        "item_medkit", "IREV-1", LoadoutKnowledgeKind.ITEM, "医療キット", "Med-Kit",
        PerkEnvironment.LIVE, "9.0.0", None, LoadoutKnowledgeStatus.VERIFIED, source.source_id,
    ))
    store.put_revision(LoadoutKnowledgeRevision(
        "addon_bandages", "AREV-1", LoadoutKnowledgeKind.ADDON, "包帯", "Bandages",
        PerkEnvironment.LIVE, "9.0.0", None, LoadoutKnowledgeStatus.VERIFIED, source.source_id,
        parent_item_id="item_medkit",
    ))
    item = store.lookup("item_medkit", game_version="9.1.0")
    addon = store.lookup("addon_bandages", game_version="9.1.0")
    assert item.to_knowledge_ref().knowledge_kind is GameKnowledgeKind.ITEM
    assert addon.to_knowledge_ref().knowledge_kind is GameKnowledgeKind.ADDON
    assert addon.parent_item_id == "item_medkit"


def test_recognition_knowledge_resolver_binds_item_and_addon(tmp_path: Path) -> None:
    from ai_video_production.canonical_game_event import GameEnvironment, GameKnowledgeKind
    from ai_video_production.dbd_loadout_knowledge import LoadoutVisualObservation
    from ai_video_production.dbd_recorded_video_recognition import DBDFrameRecognition, DbDRecognitionKnowledgeResolver

    store = DbDLoadoutKnowledgeStore(tmp_path / "loadout-resolve.sqlite3")
    source = LoadoutKnowledgeSource("src-loadout", "MANUAL_VERIFIED", "manual://owner", hashlib.sha256(b"loadout").hexdigest())
    store.put_source(source)
    store.put_revision(LoadoutKnowledgeRevision(
        "item_medkit", "IREV-1", LoadoutKnowledgeKind.ITEM, "医療キット", "Med-Kit",
        PerkEnvironment.LIVE, "9.0.0", None, LoadoutKnowledgeStatus.VERIFIED, source.source_id,
    ))
    store.put_revision(LoadoutKnowledgeRevision(
        "addon_bandages", "AREV-1", LoadoutKnowledgeKind.ADDON, "包帯", "Bandages",
        PerkEnvironment.LIVE, "9.0.0", None, LoadoutKnowledgeStatus.VERIFIED, source.source_id,
        parent_item_id="item_medkit",
    ))
    recognition = DBDFrameRecognition(
        frame_index=100, survivor_slots=(), perk_slots=(), notification=None, killer_power=None, slice_artifacts=(),
        item=LoadoutVisualObservation("item_medkit", 950, LoadoutKnowledgeKind.ITEM),
        addons=(
            LoadoutVisualObservation("addon_bandages", 910, LoadoutKnowledgeKind.ADDON, 0),
            LoadoutVisualObservation(None, 500, LoadoutKnowledgeKind.ADDON, 1),
        ),
    )
    result = DbDRecognitionKnowledgeResolver(loadout_store=store).resolve(
        recognition, game_version="9.1.0", environment=GameEnvironment.LIVE,
    )
    assert {ref.knowledge_kind for ref in result.knowledge_refs} == {GameKnowledgeKind.ITEM, GameKnowledgeKind.ADDON}
    assert "addon_slot_1:UNKNOWN" in result.unresolved
