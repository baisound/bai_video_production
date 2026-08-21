from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ai_video_production.dbd_hud_visibility import HudVisibility
from ai_video_production.dbd_killer_status_temporal import (
    EffectPolarity,
    EffectSourceKind,
    StatusEffectDefinition,
)
from ai_video_production.dbd_recorded_video_recognition import DbDRecordedVideoRecognizer
from ai_video_production.dbd_status_effect_recognition import (
    StatusEffectIconRecognizer,
    StatusEffectReferenceKind,
    StatusEffectReferenceLabel,
    StatusIconRecognitionStatus,
)
from ai_video_production.dbd_status_icon_segmentation import (
    StatusIconSegmentCandidate,
    StatusIconSegmentationProfile,
    StatusIconSegmenter,
)
from ai_video_production.dbd_vision_slices import (
    DBDHudRoiProfile,
    GrayImage,
    NormalizedROI,
    ReferenceSliceIndex,
    SliceReference,
)
from ai_video_production.serialization import sha256_bytes


DEFINITIONS = (
    StatusEffectDefinition(
        "status_bloodlust", EffectPolarity.POSITIVE, EffectSourceKind.GAME_MECHANIC,
        survivor_scoped=False,
    ),
    StatusEffectDefinition(
        "status_hindered", EffectPolarity.NEGATIVE, EffectSourceKind.PERK,
        survivor_scoped=False,
    ),
)


def _image(*, invert: bool = False) -> GrayImage:
    width, height = 9, 8
    pixels = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            value = 230 if x <= y else 20
            pixels[y * width + x] = 255 - value if invert else value
    return GrayImage(width, height, bytes(pixels))


def _reference(label: str, image: GrayImage, *, group: str = "normal") -> SliceReference:
    body = f"{image.width}x{image.height}\0".encode("ascii") + image.pixels
    digest = sha256_bytes(body)
    return SliceReference(label, f"{image.dhash64():016x}", digest, f"fixture://{digest}", group)


def _index(*rows: tuple[str, GrayImage]) -> ReferenceSliceIndex:
    return ReferenceSliceIndex(
        index_id="status-effect-test-index",
        references=tuple(_reference(label, image) for label, image in rows),
        created_at="2026-08-21T00:00:00.000Z",
    )


def _candidate(polarity: EffectPolarity = EffectPolarity.POSITIVE) -> StatusIconSegmentCandidate:
    region = (
        "bottom_right_positive_effects"
        if polarity is EffectPolarity.POSITIVE
        else "bottom_right_negative_effects"
    )
    return StatusIconSegmentCandidate(
        ordinal=0,
        polarity=polarity,
        region_roi_id=region,
        crop_roi=NormalizedROI(f"{region}/segment_0", 0.1, 0.1, 0.5, 0.5),
        foreground_pixels=30,
        segmentation_score_milli=920,
        crop_sha256="sha256:" + "1" * 64,
    )


def test_reference_label_codec_preserves_domain_identity_and_visibility() -> None:
    identity = StatusEffectReferenceLabel(
        StatusEffectReferenceKind.IDENTITY,
        polarity=EffectPolarity.POSITIVE,
        effect_id="status_bloodlust",
    )
    visibility = StatusEffectReferenceLabel(
        StatusEffectReferenceKind.VISIBILITY,
        polarity=EffectPolarity.NEGATIVE,
        visibility=HudVisibility.PARTIALLY_OCCLUDED,
    )
    hard_negative = StatusEffectReferenceLabel(
        StatusEffectReferenceKind.PERK_HARD_NEGATIVE,
        perk_id="perk_sprint_burst",
    )
    for label in (identity, visibility, hard_negative):
        assert StatusEffectReferenceLabel.decode(label.encode()) == label
    assert identity.encode() == "STATUS_EFFECT_POSITIVE/status_bloodlust"
    assert hard_negative.encode() == "PERK_ICON/perk_sprint_burst"
    with pytest.raises(ValueError, match="unsupported namespace"):
        StatusEffectReferenceLabel.decode("KILLER_POWER/status_bloodlust")
    with pytest.raises(ValueError, match="explicit visibility"):
        StatusEffectReferenceLabel(
            StatusEffectReferenceKind.VISIBILITY,
            polarity=EffectPolarity.POSITIVE,
            visibility=HudVisibility.UNKNOWN,
        )


def test_registry_is_canonical_for_polarity_and_source_and_conflicts_fail_closed() -> None:
    positive = StatusEffectReferenceLabel(
        StatusEffectReferenceKind.IDENTITY,
        polarity=EffectPolarity.POSITIVE,
        effect_id="status_bloodlust",
    ).encode()
    StatusEffectIconRecognizer(_index((positive, _image())), definitions=DEFINITIONS)

    wrong_polarity = "STATUS_EFFECT_NEGATIVE/status_bloodlust"
    with pytest.raises(ValueError, match="polarity contradicts registry"):
        StatusEffectIconRecognizer(_index((wrong_polarity, _image())), definitions=DEFINITIONS)
    with pytest.raises(ValueError, match="unregistered effect_id"):
        StatusEffectIconRecognizer(
            _index(("STATUS_EFFECT_POSITIVE/status_unknown", _image())),
            definitions=DEFINITIONS,
        )
    conflicting = ReferenceSliceIndex(
        index_id="conflicting-status-index",
        references=(
            _reference(positive, _image()),
            _reference("PERK_ICON/perk_sprint_burst", _image()),
        ),
        created_at="2026-08-21T00:00:00.000Z",
    )
    with pytest.raises(ValueError, match="conflicting labels"):
        StatusEffectIconRecognizer(conflicting, definitions=DEFINITIONS)


def test_identified_icon_resolves_registry_source_and_creates_body_free_temporal_observation() -> None:
    label = "STATUS_EFFECT_POSITIVE/status_bloodlust"
    recognizer = StatusEffectIconRecognizer(_index((label, _image())), definitions=DEFINITIONS)
    result = recognizer.recognize(
        _image(),
        candidate=_candidate(),
        evidence_ref="recognition://status/positive/0/sha256:" + "2" * 64,
    )
    assert result.status is StatusIconRecognitionStatus.IDENTIFIED
    assert result.effect_id == "status_bloodlust"
    assert result.polarity is EffectPolarity.POSITIVE
    assert result.source_kind is EffectSourceKind.GAME_MECHANIC
    assert result.visibility is HudVisibility.VISIBLE
    assert result.confidence_milli == 920
    observation = result.to_temporal_observation(match_id="match-r5b", frame_index=42)
    assert observation.active is True
    assert observation.survivor_slot is None
    assert observation.effect_id == result.effect_id
    assert not hasattr(result, "pixels")


@pytest.mark.parametrize(
    ("label", "candidate_polarity", "expected_status", "expected_reason"),
    (
        (
            "PERK_ICON/perk_sprint_burst",
            EffectPolarity.POSITIVE,
            StatusIconRecognitionStatus.HARD_NEGATIVE,
            "STATUS_ICON_MATCHED_PERK_HARD_NEGATIVE",
        ),
        (
            "STATUS_EFFECT_NEGATIVE/status_hindered",
            EffectPolarity.POSITIVE,
            StatusIconRecognitionStatus.CONTRADICTION,
            "STATUS_EFFECT_POLARITY_CONTRADICTION",
        ),
        (
            "STATUS_EFFECT_POSITIVE/VISIBILITY/PARTIALLY_OCCLUDED",
            EffectPolarity.POSITIVE,
            StatusIconRecognitionStatus.VISIBILITY_ONLY,
            "STATUS_EFFECT_VISIBILITY_ONLY",
        ),
    ),
)
def test_hard_negative_opposite_polarity_and_visibility_never_claim_identity(
    label: str,
    candidate_polarity: EffectPolarity,
    expected_status: StatusIconRecognitionStatus,
    expected_reason: str,
) -> None:
    recognizer = StatusEffectIconRecognizer(_index((label, _image())), definitions=DEFINITIONS)
    result = recognizer.recognize(
        _image(), candidate=_candidate(candidate_polarity), evidence_ref="fixture://status-icon",
    )
    assert result.status is expected_status
    assert result.effect_id is None
    assert result.source_kind is EffectSourceKind.UNKNOWN
    assert result.reason_codes == (expected_reason,)
    with pytest.raises(ValueError, match="only an identified"):
        result.to_temporal_observation(match_id="match-r5b", frame_index=3)


def test_low_similarity_abstains_but_preserves_visible_segmentation_evidence() -> None:
    recognizer = StatusEffectIconRecognizer(
        _index(("STATUS_EFFECT_POSITIVE/status_bloodlust", _image())),
        definitions=DEFINITIONS,
        acceptance_milli=990,
    )
    result = recognizer.recognize(
        _image(invert=True), candidate=_candidate(), evidence_ref="fixture://unknown-status-icon",
    )
    assert result.status is StatusIconRecognitionStatus.ABSTAINED
    assert result.effect_id is None
    assert result.visibility is HudVisibility.VISIBLE
    assert result.reason_codes == ("STATUS_EFFECT_IDENTITY_UNKNOWN",)


class Extractor:
    def __init__(self, mapping: dict[str, Path]) -> None:
        self.mapping = mapping

    def extract_frame_roi(self, *, roi, output_path, **_kwargs):
        Path(output_path).write_bytes(self.mapping[roi.roi_id].read_bytes())
        return Path(output_path)


def _status_region() -> GrayImage:
    width, height = 40, 20
    pixels = bytearray([20] * (width * height))
    for y in range(4, 12):
        for x in range(3, 12):
            pixels[y * width + x] = 230 if x - 3 <= y - 4 else 80
    return GrayImage(width, height, bytes(pixels))


def test_recorded_video_connects_segment_crop_to_identity_without_image_body(tmp_path: Path) -> None:
    roi = NormalizedROI("bottom_right_positive_effects", 0.62, 0.70, 0.10, 0.25)
    region = _status_region()
    region_path = region.write_pgm(tmp_path / "positive-region.pgm")
    segmenter = StatusIconSegmenter(StatusIconSegmentationProfile(
        contrast_threshold=40,
        bridge_pixels=0,
        minimum_width=3,
        minimum_height=3,
        minimum_foreground_pixels=8,
        crop_padding_pixels=0,
    ))
    segmentation = segmenter.segment(
        region,
        polarity=EffectPolarity.POSITIVE,
        region_roi_id=roi.roi_id,
    )
    crop = StatusEffectIconRecognizer.crop_segment(region, segmentation.candidates[0])
    tampered_pixels = bytearray(region.pixels)
    tampered_pixels[4 * region.width + 3] = 20
    with pytest.raises(ValueError, match="checksum does not match"):
        StatusEffectIconRecognizer.crop_segment(
            GrayImage(region.width, region.height, bytes(tampered_pixels)),
            segmentation.candidates[0],
        )
    index = _index(("STATUS_EFFECT_POSITIVE/status_bloodlust", crop))
    result = DbDRecordedVideoRecognizer(
        roi_profile=DBDHudRoiProfile(bottom_right_positive_effects=roi),
        extractor=Extractor({roi.roi_id: region_path}),
        status_icon_segmenter=segmenter,
        status_effect_recognizer=StatusEffectIconRecognizer(index, definitions=DEFINITIONS),
    ).recognize_frame(
        video_path=tmp_path / "owned.mp4",
        frame_index=18,
        working_directory=tmp_path / "work",
    )
    assert len(result.status_effects) == 1
    assert result.status_effects[0].effect_id == "status_bloodlust"
    assert result.status_effects[0].evidence_ref.endswith(segmentation.candidates[0].crop_sha256)
    assert not hasattr(result.status_effects[0], "image")
    with pytest.raises(ValueError, match="refer to candidates"):
        replace(result, status_effect_regions=())
    with pytest.raises(ValueError, match="requires status_icon_segmenter"):
        DbDRecordedVideoRecognizer(
            status_effect_recognizer=StatusEffectIconRecognizer(index, definitions=DEFINITIONS)
        )
