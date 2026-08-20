from ai_video_production.dbd_hud_detectors import PerkSlotObservation
from ai_video_production.dbd_hud_visibility import HudVisibility
from ai_video_production.dbd_loadout_knowledge import LoadoutKnowledgeKind, LoadoutVisualObservation
from ai_video_production.dbd_recognition_observation_adapter import frame_recognition_to_observations
from ai_video_production.dbd_recorded_video_recognition import DBDFrameRecognition


def test_existing_frame_recognition_projects_visibility_and_provenance():
    recognition = DBDFrameRecognition(
        frame_index=42,
        survivor_slots=(),
        perk_slots=(
            PerkSlotObservation(0, None, 970, (), HudVisibility.HIDDEN),
            PerkSlotObservation(1, None, 500, (), HudVisibility.UNKNOWN),
            PerkSlotObservation(2, None, 500, (), HudVisibility.UNKNOWN),
            PerkSlotObservation(3, None, 500, (), HudVisibility.UNKNOWN),
        ),
        notification=None,
        killer_power=None,
        slice_artifacts=(),
        item=LoadoutVisualObservation(
            "item_medkit",
            900,
            LoadoutKnowledgeKind.ITEM,
            None,
            HudVisibility.VISIBLE,
        ),
        addons=(),
    )

    rows = frame_recognition_to_observations(
        recognition,
        workspace_id="dbdws-1",
        runtime_profile_id="default",
        hud_profile_id="hud-v3",
        hud_profile_version=3,
        detector_versions={"perk": "perk-v2", "item": "item-v1"},
        anchor_offsets_px={"perk_slot_0": (-2, 1)},
        knowledge_revision_by_entity={"item_medkit": "item-rev-7"},
    )

    assert len(rows) == 5
    perk = next(
        row
        for row in rows
        if row.observation_type.value == "PERK"
        and row.provenance.roi_id == "perk_slot_0"
    )
    item = next(row for row in rows if row.observation_type.value == "ITEM")

    assert perk.visibility is HudVisibility.HIDDEN
    assert perk.entity_id is None
    assert perk.provenance.anchor_offset_x_px == -2
    assert item.provenance.knowledge_revision_refs == ("item-rev-7",)
