from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.dbd_killer_status_temporal import EffectPolarity
from ai_video_production.dbd_recorded_video_recognition import DbDRecordedVideoRecognizer
from ai_video_production.dbd_status_icon_segmentation import (
    StatusIconSegmentationProfile,
    StatusIconSegmentationStatus,
    StatusIconSegmenter,
)
from ai_video_production.dbd_vision_slices import DBDHudRoiProfile, GrayImage, NormalizedROI


def _region(*, blocks: tuple[tuple[int, int, int, int], ...] = ()) -> GrayImage:
    width, height = 40, 20
    pixels = bytearray([20] * (width * height))
    for left, top, right, bottom in blocks:
        for y in range(top, bottom):
            for x in range(left, right):
                pixels[y * width + x] = 220
    return GrayImage(width, height, bytes(pixels))


def _write(path: Path, image: GrayImage) -> Path:
    return image.write_pgm(path)


class Extractor:
    def __init__(self, mapping: dict[str, Path]) -> None:
        self.mapping = mapping

    def extract_frame_roi(self, *, roi, output_path, **_kwargs):
        Path(output_path).write_bytes(self.mapping[roi.roi_id].read_bytes())
        return Path(output_path)


def test_segments_zero_one_and_multiple_icons_with_body_free_crop_evidence() -> None:
    segmenter = StatusIconSegmenter(StatusIconSegmentationProfile(
        contrast_threshold=50,
        bridge_pixels=0,
        minimum_width=3,
        minimum_height=3,
        minimum_foreground_pixels=8,
        crop_padding_pixels=0,
    ))
    empty = segmenter.segment(
        _region(), polarity=EffectPolarity.POSITIVE,
        region_roi_id="bottom_right_positive_effects",
    )
    assert empty.status is StatusIconSegmentationStatus.EMPTY
    assert empty.candidates == ()

    one = segmenter.segment(
        _region(blocks=((3, 4, 9, 11),)), polarity=EffectPolarity.POSITIVE,
        region_roi_id="bottom_right_positive_effects",
    )
    assert one.status is StatusIconSegmentationStatus.SEGMENTED
    assert len(one.candidates) == 1
    assert one.candidates[0].crop_roi.roi_id.endswith("/segment_0")
    assert one.candidates[0].crop_sha256.startswith("sha256:")
    assert not hasattr(one.candidates[0], "pixels")

    multiple = segmenter.segment(
        _region(blocks=((2, 3, 8, 10), (16, 3, 23, 10), (30, 7, 36, 15))),
        polarity=EffectPolarity.NEGATIVE,
        region_roi_id="bottom_right_negative_effects",
    )
    assert multiple.status is StatusIconSegmentationStatus.SEGMENTED
    assert len(multiple.candidates) == 3
    assert all(item.polarity is EffectPolarity.NEGATIVE for item in multiple.candidates)
    assert [item.ordinal for item in multiple.candidates] == [0, 1, 2]


def test_component_overflow_fails_closed_without_partial_candidates() -> None:
    segmenter = StatusIconSegmenter(StatusIconSegmentationProfile(
        contrast_threshold=50, bridge_pixels=0,
        minimum_width=3, minimum_height=3, minimum_foreground_pixels=8,
        maximum_icons=1, crop_padding_pixels=0,
    ))
    result = segmenter.segment(
        _region(blocks=((2, 3, 8, 10), (16, 3, 23, 10))),
        polarity=EffectPolarity.NEGATIVE,
        region_roi_id="bottom_right_negative_effects",
    )
    assert result.status is StatusIconSegmentationStatus.OVERFLOW
    assert result.candidates == ()
    assert result.reason_codes == ("STATUS_ICON_COMPONENT_LIMIT_EXCEEDED",)


def test_polarity_region_namespace_and_resource_bounds_fail_closed() -> None:
    segmenter = StatusIconSegmenter()
    with pytest.raises(ValueError, match="polarity and region namespace"):
        segmenter.segment(
            _region(), polarity=EffectPolarity.POSITIVE,
            region_roi_id="bottom_right_negative_effects",
        )
    with pytest.raises(ValueError, match="must not exceed 64"):
        StatusIconSegmentationProfile(maximum_icons=65)
    with pytest.raises(ValueError, match="canonical region"):
        DBDHudRoiProfile(
            bottom_right_positive_effects=NormalizedROI(
                "bottom_right_negative_effects", 0.6, 0.7, 0.1, 0.2,
            )
        )


def test_hud_profile_23_round_trip_and_old_profile_backward_read() -> None:
    positive = NormalizedROI("bottom_right_positive_effects", 0.62, 0.70, 0.10, 0.25)
    negative = NormalizedROI("bottom_right_negative_effects", 0.78, 0.54, 0.20, 0.10)
    profile = DBDHudRoiProfile(
        profile_id="status-effects-profile",
        bottom_right_positive_effects=positive,
        bottom_right_negative_effects=negative,
    )
    payload = profile.to_dict()
    assert payload["schema_version"] == "2.3.0"
    assert DBDHudRoiProfile.from_dict(payload) == profile
    assert profile.roi_by_id("bottom_right_positive_effects") == positive
    assert profile.roi_by_id("bottom_right_negative_effects") == negative

    legacy = DBDHudRoiProfile().to_dict()
    legacy["schema_version"] = "2.2.0"
    legacy.pop("bottom_right_positive_effects")
    legacy.pop("bottom_right_negative_effects")
    restored = DBDHudRoiProfile.from_dict(legacy)
    assert restored.bottom_right_positive_effects is None
    assert restored.bottom_right_negative_effects is None


def test_recorded_video_routes_both_calibrated_regions_and_reports_missing_region(tmp_path: Path) -> None:
    positive_roi = NormalizedROI("bottom_right_positive_effects", 0.62, 0.70, 0.10, 0.25)
    negative_roi = NormalizedROI("bottom_right_negative_effects", 0.78, 0.54, 0.20, 0.10)
    positive_path = _write(tmp_path / "positive.pgm", _region(blocks=((3, 4, 9, 11),)))
    negative_path = _write(tmp_path / "negative.pgm", _region(blocks=((2, 3, 8, 10), (16, 3, 23, 10))))
    profile = DBDHudRoiProfile(
        bottom_right_positive_effects=positive_roi,
        bottom_right_negative_effects=negative_roi,
    )
    recognizer = DbDRecordedVideoRecognizer(
        roi_profile=profile,
        extractor=Extractor({positive_roi.roi_id: positive_path, negative_roi.roi_id: negative_path}),
        status_icon_segmenter=StatusIconSegmenter(StatusIconSegmentationProfile(
            contrast_threshold=50, bridge_pixels=0,
            minimum_width=3, minimum_height=3, minimum_foreground_pixels=8,
            crop_padding_pixels=0,
        )),
    )
    result = recognizer.recognize_frame(
        video_path=tmp_path / "owned.mp4", frame_index=12,
        working_directory=tmp_path / "work",
    )
    by_polarity = {item.polarity: item for item in result.status_effect_regions}
    assert len(by_polarity[EffectPolarity.POSITIVE].candidates) == 1
    assert len(by_polarity[EffectPolarity.NEGATIVE].candidates) == 2
    assert {item.roi_id for item in result.slice_artifacts} == {
        "bottom_right_positive_effects", "bottom_right_negative_effects",
    }

    missing = DbDRecordedVideoRecognizer(
        roi_profile=DBDHudRoiProfile(bottom_right_positive_effects=positive_roi),
        extractor=Extractor({positive_roi.roi_id: positive_path}),
        status_icon_segmenter=StatusIconSegmenter(),
    ).recognize_frame(
        video_path=tmp_path / "owned.mp4", frame_index=13,
        working_directory=tmp_path / "work-missing",
    )
    unavailable = next(
        item for item in missing.status_effect_regions
        if item.polarity is EffectPolarity.NEGATIVE
    )
    assert unavailable.status is StatusIconSegmentationStatus.REGION_UNAVAILABLE
    assert unavailable.reason_codes == ("STATUS_EFFECT_REGION_NOT_CALIBRATED",)


def test_training_studio_exposes_both_optional_status_calibration_regions() -> None:
    studio = Path("src/ai_video_production/dbd_training_studio.py").read_text(encoding="utf-8")
    labels = Path("src/ai_video_production/dbd_hud_calibration_editor.py").read_text(encoding="utf-8")
    for roi_id in ("bottom_right_positive_effects", "bottom_right_negative_effects"):
        assert roi_id in studio
        assert roi_id in labels
