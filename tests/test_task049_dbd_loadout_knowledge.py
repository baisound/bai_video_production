import hashlib
from pathlib import Path

from ai_video_production.canonical_game_event import GameKnowledgeKind
from ai_video_production.dbd_loadout_knowledge import (
    DbDLoadoutKnowledgeStore, LoadoutKnowledgeKind, LoadoutKnowledgeRevision,
    LoadoutKnowledgeSource, LoadoutKnowledgeStatus, LoadoutVisualRecognizer,
)
from ai_video_production.dbd_hud_visibility import HudVisibility
from ai_video_production.dbd_vision_slices import GrayImage, ReferenceSliceIndex
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
            LoadoutVisualObservation(None, 500, LoadoutKnowledgeKind.ADDON, 1, HudVisibility.UNKNOWN),
        ),
    )
    result = DbDRecognitionKnowledgeResolver(loadout_store=store).resolve(
        recognition, game_version="9.1.0", environment=GameEnvironment.LIVE,
    )
    assert {ref.knowledge_kind for ref in result.knowledge_refs} == {GameKnowledgeKind.ITEM, GameKnowledgeKind.ADDON}
    assert "addon_slot_1:UNKNOWN" in result.unresolved


def _pgm(path: Path, invert: bool = False) -> Path:
    pixels = []
    for y in range(8):
        for x in range(9):
            value = 255 if x > 3 else 0
            pixels.append(255 - value if invert else value)
    path.write_bytes(b"P5\n9 8\n255\n" + bytes(pixels))
    return path


def test_item_hidden_is_distinct_from_missing_identity(tmp_path: Path) -> None:
    visible = _pgm(tmp_path / "item-visible.pgm")
    hidden = _pgm(tmp_path / "item-hidden.pgm", True)
    index = ReferenceSliceIndex.train_from_pgm(
        index_id="item-hidden",
        samples=[("item_medkit", visible), ("ITEM_HIDDEN", hidden)],
    )
    recognizer = LoadoutVisualRecognizer(index, kind=LoadoutKnowledgeKind.ITEM, acceptance_milli=700)
    result = recognizer.recognize(GrayImage.read_pgm(hidden))
    assert result.entity_id is None
    assert result.visibility is HudVisibility.HIDDEN


def test_addon_hidden_is_distinct_from_missing_identity(tmp_path: Path) -> None:
    visible = _pgm(tmp_path / "addon-visible.pgm")
    hidden = _pgm(tmp_path / "addon-hidden.pgm", True)
    index = ReferenceSliceIndex.train_from_pgm(
        index_id="addon-hidden",
        samples=[("addon_bandages", visible), ("ADDON_HIDDEN", hidden)],
    )
    recognizer = LoadoutVisualRecognizer(index, kind=LoadoutKnowledgeKind.ADDON, acceptance_milli=700)
    result = recognizer.recognize(GrayImage.read_pgm(hidden), slot=1)
    assert result.entity_id is None
    assert result.slot == 1
    assert result.visibility is HudVisibility.HIDDEN
