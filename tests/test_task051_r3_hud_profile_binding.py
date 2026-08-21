from pathlib import Path
import json

from ai_video_production.canonical_game_event import GameKnowledgeKind
from ai_video_production.dbd_hud_calibration_editor import RoiPixelEditor
from ai_video_production.dbd_training_hud_binding import (
    ADDON_SLOT_LABELS,
    PERK_SLOT_LABELS,
    roi_pixel_rect,
    slot_specifications,
    training_roi,
)
from ai_video_production.dbd_training_workspace import VisualTrainingDomain
from ai_video_production.dbd_vision_slices import DBDHudRoiProfile, NormalizedROI

from ai_video_production.dbd_entity_aliases import (
    EntityAliasCatalog,
    EntityAliasRecord,
    EntityAliasType,
)
from ai_video_production.dbd_training_hud_binding import alias_choices

def calibrated_profile():
    return DBDHudRoiProfile(
        profile_id="calibrated-test",
        calibrated_frame_width=1920,
        calibrated_frame_height=1080,
        item_slot=NormalizedROI("item_slot", 0.10, 0.80, 0.05, 0.08),
        addon_slots=(
            NormalizedROI("addon_slot_0", 0.16, 0.80, 0.04, 0.06),
            NormalizedROI("addon_slot_1", 0.21, 0.80, 0.04, 0.06),
        ),
        perk_slots=(
            NormalizedROI("perk_slot_0", 0.80, 0.70, 0.05, 0.08),
            NormalizedROI("perk_slot_1", 0.86, 0.70, 0.05, 0.08),
            NormalizedROI("perk_slot_2", 0.80, 0.79, 0.05, 0.08),
            NormalizedROI("perk_slot_3", 0.86, 0.79, 0.05, 0.08),
        ),
    )


def test_perk_and_addon_slot_specifications():
    assert [x[1] for x in slot_specifications(VisualTrainingDomain.PERK_ICON)] == list(PERK_SLOT_LABELS)
    assert [x[1] for x in slot_specifications(VisualTrainingDomain.ADDON_ICON)] == list(ADDON_SLOT_LABELS)
    assert len(slot_specifications(VisualTrainingDomain.PERK_ICON)) == 4
    assert len(slot_specifications(VisualTrainingDomain.ADDON_ICON)) == 2


def test_training_roi_uses_exact_perk_and_addon_slots():
    p = calibrated_profile()
    assert training_roi(p, VisualTrainingDomain.PERK_ICON, 3).roi_id == "perk_slot_3"
    assert training_roi(p, VisualTrainingDomain.ADDON_ICON, 1).roi_id == "addon_slot_1"
    assert training_roi(p, VisualTrainingDomain.ITEM_ICON, None).roi_id == "item_slot"


def test_training_pixel_rect_equals_calibration_editor():
    p = calibrated_profile()
    for slot in range(4):
        roi = p.perk_slot_roi(slot)
        editor = RoiPixelEditor(
            source_width=1920,
            source_height=1080,
            rois={roi.roi_id: roi},
        )
        expected = editor.pixel_rect(roi.roi_id)
        actual = roi_pixel_rect(
            p,
            domain=VisualTrainingDomain.PERK_ICON,
            slot=slot,
            source_width=1920,
            source_height=1080,
        )
        assert actual == expected


def test_uncalibrated_addon_slots_fail_closed():
    p = DBDHudRoiProfile(
        profile_id="no-addons",
        calibrated_frame_width=1920,
        calibrated_frame_height=1080,
    )
    try:
        training_roi(p, VisualTrainingDomain.ADDON_ICON, 0)
    except ValueError as exc:
        assert "not calibrated" in str(exc)
    else:
        raise AssertionError("uncalibrated add-on slots must fail")

def test_alias_choices_can_list_catalog_without_search_text(tmp_path):
    catalog = EntityAliasCatalog(tmp_path / "aliases.sqlite")
    catalog.put(
        EntityAliasRecord(
            "perk_windows",
            GameKnowledgeKind.PERK,
            "好機の窓",
            EntityAliasType.OFFICIAL_NAME,
            priority=100,
        )
    )

    choices = alias_choices(
        catalog,
        knowledge_kind=GameKnowledgeKind.PERK,
    )

    assert len(choices) == 1
    assert choices[0].entity_id == "perk_windows"