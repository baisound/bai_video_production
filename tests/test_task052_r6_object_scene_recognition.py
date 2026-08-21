from __future__ import annotations

from dataclasses import replace

import pytest

from ai_video_production.canonical_game_event import GameKnowledgeKind
from ai_video_production.dbd_object_scene_recognition import (
    ObjectSceneCrop, ObjectSceneDefinition, ObjectSceneKind,
    ObjectSceneRecognitionStatus, ObjectSceneRecognizer, hard_negative_label,
)
from ai_video_production.dbd_vision_slices import (
    GrayImage, NormalizedROI, ReferenceSliceIndex, SliceReference,
)
from ai_video_production.serialization import sha256_bytes


def _image(invert: bool = False) -> GrayImage:
    pixels = bytes(
        (255 if (x + y * 3) % 5 < 2 else 0) ^ (255 if invert else 0)
        for y in range(8) for x in range(9)
    )
    return GrayImage(9, 8, pixels)


def _reference(label: str, image: GrayImage) -> SliceReference:
    body = f"{image.width}x{image.height}\0".encode("ascii") + image.pixels
    digest = sha256_bytes(body)
    return SliceReference(label, f"{image.dhash64():016x}", digest, f"fixture://{digest}")


PALLET = ObjectSceneDefinition(
    "pallet_standard", ObjectSceneKind.PALLET, GameKnowledgeKind.MECHANIC,
)
BUILDING = ObjectSceneDefinition(
    "main_building_coal_tower", ObjectSceneKind.MAIN_BUILDING,
    GameKnowledgeKind.MAP, map_id="map_coal_tower",
)


def _recognizer(*definitions: ObjectSceneDefinition) -> ObjectSceneRecognizer:
    rows = definitions or (PALLET,)
    index = ReferenceSliceIndex(
        index_id="object-scene-test",
        references=(
            _reference(rows[0].label, _image()),
            _reference(hard_negative_label("background_foliage"), _image(True)),
        ),
        created_at="2026-08-21T00:00:00.000Z",
    )
    return ObjectSceneRecognizer(index, definitions=rows, acceptance_milli=800)


def _crop(image: GrayImage, *, map_id: str = "") -> ObjectSceneCrop:
    return ObjectSceneCrop(
        10, NormalizedROI("scene_proposal_0", 0.1, 0.1, 0.4, 0.4), image,
        "video://owned#frame=10&proposal=0", map_id,
    )


def test_pallet_identity_is_object_evidence_not_pallet_drop_event() -> None:
    result = _recognizer(PALLET).recognize(_crop(_image()))
    assert result.status is ObjectSceneRecognitionStatus.IDENTIFIED
    assert result.object_id == "pallet_standard"
    assert result.kind is ObjectSceneKind.PALLET
    assert result.owner_kind is GameKnowledgeKind.MECHANIC
    assert result.event_claim_allowed is False
    assert result.crop_sha256.startswith("sha256:")


def test_hard_negative_and_ambiguous_crop_do_not_claim_identity() -> None:
    recognizer = _recognizer(PALLET)
    negative = recognizer.recognize(_crop(_image(True)))
    assert negative.status is ObjectSceneRecognitionStatus.HARD_NEGATIVE
    assert negative.object_id is None

    duplicate_index = ReferenceSliceIndex(
        index_id="ambiguous",
        references=(
            _reference(PALLET.label, _image()),
            _reference("OBJECT_SCENE/WINDOW/window_standard", _image()),
            _reference(hard_negative_label("background_foliage"), _image(True)),
        ),
    )
    window = ObjectSceneDefinition(
        "window_standard", ObjectSceneKind.WINDOW, GameKnowledgeKind.MECHANIC,
    )
    ambiguous = ObjectSceneRecognizer(
        duplicate_index, definitions=(PALLET, window), acceptance_milli=800,
    ).recognize(_crop(_image()))
    assert ambiguous.status is ObjectSceneRecognitionStatus.ABSTAINED


def test_map_bound_scene_requires_exact_map_namespace() -> None:
    recognizer = _recognizer(BUILDING)
    accepted = recognizer.recognize(_crop(_image(), map_id="map_coal_tower"))
    assert accepted.status is ObjectSceneRecognitionStatus.IDENTIFIED
    mismatch = recognizer.recognize(_crop(_image(), map_id="map_other"))
    assert mismatch.status is ObjectSceneRecognitionStatus.CONTRADICTION
    assert mismatch.reason_codes == ("OBJECT_SCENE_MAP_NAMESPACE_MISMATCH",)


def test_definition_owner_boundaries_and_index_admission_fail_closed() -> None:
    with pytest.raises(ValueError, match="canonical owner"):
        replace(PALLET, owner_kind=GameKnowledgeKind.PERK)
    with pytest.raises(ValueError, match="requires map_id"):
        ObjectSceneDefinition(
            "main_building", ObjectSceneKind.MAIN_BUILDING, GameKnowledgeKind.MAP,
        )
    identity_only = ReferenceSliceIndex(
        index_id="identity-only", references=(_reference(PALLET.label, _image()),),
    )
    with pytest.raises(ValueError, match="identity and hard-negative"):
        ObjectSceneRecognizer(identity_only, definitions=(PALLET,))
    with pytest.raises(ValueError, match="unique"):
        ObjectSceneRecognizer(
            _recognizer(PALLET).classifier.index,
            definitions=(
                PALLET,
                ObjectSceneDefinition(
                    PALLET.object_id, ObjectSceneKind.WINDOW, GameKnowledgeKind.MECHANIC,
                ),
            ),
        )
    foreign = ReferenceSliceIndex(
        index_id="foreign",
        references=(
            _reference("PERK_ICON/perk_sprint_burst", _image()),
            _reference(hard_negative_label("background_foliage"), _image(True)),
        ),
    )
    with pytest.raises(ValueError, match="unregistered"):
        ObjectSceneRecognizer(foreign, definitions=(PALLET,))
    malformed = ReferenceSliceIndex(
        index_id="malformed-negative",
        references=(
            _reference(PALLET.label, _image()),
            _reference("OBJECT_SCENE/HARD_NEGATIVE/not-valid", _image(True)),
        ),
    )
    with pytest.raises(ValueError, match="malformed"):
        ObjectSceneRecognizer(malformed, definitions=(PALLET,))
