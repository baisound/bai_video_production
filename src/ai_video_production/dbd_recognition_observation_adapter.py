"""TASK-050 R5 adapters from existing recognition results to observation envelopes."""
from __future__ import annotations

from typing import Mapping, Sequence

from .canonical_game_event import GameKnowledgeKind
from .dbd_loadout_knowledge import LoadoutKnowledgeKind
from .dbd_observation_envelope import (
    DbDObservationEnvelope,
    DbDObservationType,
    ObservationProvenance,
)
from .dbd_recorded_video_recognition import DBDFrameRecognition


def frame_recognition_to_observations(
    recognition: DBDFrameRecognition,
    *,
    workspace_id: str,
    runtime_profile_id: str | None,
    hud_profile_id: str,
    hud_profile_version: int,
    detector_versions: Mapping[str, str],
    anchor_offsets_px: Mapping[str, tuple[int, int]] = {},
    knowledge_revision_by_entity: Mapping[str, str] = {},
) -> tuple[DbDObservationEnvelope, ...]:
    """Project existing recognizer outputs into reusable evidence envelopes.

    This does not resolve or create CGEL events.  Revision IDs are included only
    when the caller already has a canonical Knowledge resolution.
    """
    frame = recognition.frame_index
    rows: list[DbDObservationEnvelope] = []

    def provenance(roi_id: str, detector_key: str, entity_id: str | None) -> ObservationProvenance:
        dx, dy = anchor_offsets_px.get(roi_id, (0, 0))
        revisions = ()
        if entity_id is not None and entity_id in knowledge_revision_by_entity:
            revisions = (knowledge_revision_by_entity[entity_id],)
        return ObservationProvenance(
            workspace_id=workspace_id,
            runtime_profile_id=runtime_profile_id,
            hud_profile_id=hud_profile_id,
            hud_profile_version=hud_profile_version,
            roi_id=roi_id,
            detector_version=detector_versions.get(detector_key, "UNKNOWN"),
            anchor_offset_x_px=dx,
            anchor_offset_y_px=dy,
            knowledge_revision_refs=revisions,
        )

    for item in recognition.perk_slots:
        roi_id = f"perk_slot_{item.slot}"
        rows.append(DbDObservationEnvelope(
            observation_id=f"obs-perk-{frame}-{item.slot}",
            observation_type=DbDObservationType.PERK,
            frame_start=frame,
            frame_end_exclusive=frame + 1,
            confidence_milli=item.confidence_milli,
            provenance=provenance(roi_id, "perk", item.perk_id),
            visibility=item.visibility,
            entity_id=item.perk_id,
            candidates=tuple(sorted({candidate.label for candidate in item.candidates})),
        ))

    if recognition.item is not None:
        item = recognition.item
        rows.append(DbDObservationEnvelope(
            observation_id=f"obs-item-{frame}",
            observation_type=DbDObservationType.ITEM,
            frame_start=frame,
            frame_end_exclusive=frame + 1,
            confidence_milli=item.confidence_milli,
            provenance=provenance("item_slot", "item", item.entity_id),
            visibility=item.visibility,
            entity_id=item.entity_id,
        ))

    for item in recognition.addons:
        slot = 0 if item.slot is None else item.slot
        roi_id = f"addon_slot_{slot}"
        rows.append(DbDObservationEnvelope(
            observation_id=f"obs-addon-{frame}-{slot}",
            observation_type=DbDObservationType.ADDON,
            frame_start=frame,
            frame_end_exclusive=frame + 1,
            confidence_milli=item.confidence_milli,
            provenance=provenance(roi_id, "addon", item.entity_id),
            visibility=item.visibility,
            entity_id=item.entity_id,
        ))

    return tuple(sorted(rows, key=lambda x: (x.observation_type.value, x.observation_id)))
