from pathlib import Path

import pytest

from ai_video_production.dbd_hud_calibration import (
    DBDHudProfileResolver,
    HudAnchorAligner,
    HudProfileRegistry,
)
from ai_video_production.dbd_vision_slices import DBDHudRoiProfile, GrayImage, HudAnchorReference, NormalizedROI
from ai_video_production.serialization import sha256_bytes


def _pattern(seed: int, width: int = 96, height: int = 96) -> GrayImage:
    pixels = bytearray()
    for y in range(height):
        for x in range(width):
            pixels.append(255 if ((x * (seed + 1) + y * (seed + 3) + seed) % 13) < 6 else 0)
    return GrayImage(width, height, bytes(pixels))


def test_versioned_hud_profile_round_trip_preserves_calibration_metadata_and_anchor(tmp_path: Path) -> None:
    image = _pattern(2)
    anchor_path = image.write_pgm(tmp_path / "anchor.pgm")
    anchor = HudAnchorReference("bottom_right_perks", f"{image.dhash64():016x}", sha256_bytes(anchor_path.read_bytes()), "anchors/bottom_right_perks.pgm")
    profile = DBDHudRoiProfile(
        profile_id="dbd-16x9-ui100-910",
        profile_version=3,
        calibrated_frame_width=1920,
        calibrated_frame_height=1080,
        ui_scale_percent=100,
        game_version_from="9.1.0",
        game_version_to="9.9.9",
        calibration_source_ref="video://owned-match",
        anchors=(anchor,),
    )
    loaded = DBDHudRoiProfile.from_dict(profile.to_dict())
    assert loaded.profile_version == 3
    assert loaded.aspect_ratio == pytest.approx(16 / 9)
    assert loaded.ui_scale_percent == 100
    assert loaded.anchor_for("bottom_right_perks") == anchor


def test_profile_registry_and_resolver_choose_exact_compatible_profile(tmp_path: Path) -> None:
    registry = HudProfileRegistry(tmp_path / "profiles")
    a = DBDHudRoiProfile(profile_id="a", calibrated_frame_width=1920, calibrated_frame_height=1080, ui_scale_percent=100, game_version_from="9.0.0")
    b = DBDHudRoiProfile(profile_id="b", calibrated_frame_width=2560, calibrated_frame_height=1440, ui_scale_percent=100, game_version_from="9.0.0")
    registry.save(a); registry.save(b)
    resolution = DBDHudProfileResolver(registry.list_profiles()).resolve(frame_width=1920, frame_height=1080, ui_scale_percent=100, game_version="9.2.0")
    assert resolution.profile.profile_id == "a"
    assert resolution.score_milli >= 900


def test_profile_resolver_fails_closed_when_multiple_profiles_are_ambiguous() -> None:
    profiles = (
        DBDHudRoiProfile(profile_id="a", calibrated_frame_width=1920, calibrated_frame_height=1080, ui_scale_percent=100),
        DBDHudRoiProfile(profile_id="b", calibrated_frame_width=1920, calibrated_frame_height=1080, ui_scale_percent=100),
    )
    with pytest.raises(Exception) as exc:
        DBDHudProfileResolver(profiles).resolve(frame_width=1920, frame_height=1080, ui_scale_percent=100)
    assert "AMBIGUOUS" in str(exc.value) or "Multiple" in str(exc.value)


class _ShiftAwareExtractor:
    def __init__(self, *, target_roi: NormalizedROI, target_image: GrayImage, expected_dx: float, expected_dy: float) -> None:
        self.target_roi = target_roi
        self.target_image = target_image
        self.expected_dx = expected_dx
        self.expected_dy = expected_dy
        self.bad_image = _pattern(9)

    def extract_frame_roi(self, *, video_path, frame_index, roi, output_path, width=64, height=64):
        distance = abs((roi.x - self.target_roi.x) - self.expected_dx) + abs((roi.y - self.target_roi.y) - self.expected_dy)
        image = self.target_image if distance < 1e-9 else self.bad_image
        image.resized(width, height).write_pgm(output_path)
        return Path(output_path)


def test_anchor_aligner_applies_parent_shift_to_perk_slots(tmp_path: Path) -> None:
    anchor_image = _pattern(3)
    anchor_path = anchor_image.write_pgm(tmp_path / "anchor.pgm")
    profile = DBDHudRoiProfile(
        profile_id="aligned",
        calibrated_frame_width=1000,
        calibrated_frame_height=1000,
        anchors=(HudAnchorReference("bottom_right_perks", f"{anchor_image.dhash64():016x}", sha256_bytes(anchor_path.read_bytes()), "anchor.pgm"),),
    )
    dx, dy = -4 / 1000, -4 / 1000
    aligner = HudAnchorAligner(
        extractor=_ShiftAwareExtractor(target_roi=profile.bottom_right_perks, target_image=anchor_image, expected_dx=dx, expected_dy=dy),
        search_radius_pixels=4, search_step_pixels=4, acceptance_milli=700,
    )
    result = aligner.align(video_path=tmp_path / "fake.mp4", frame_index=10, profile=profile, frame_width=1000, frame_height=1000, working_directory=tmp_path / "work")
    assert result.corrections[0].dx_normalized == pytest.approx(dx)
    assert result.corrections[0].dy_normalized == pytest.approx(dy)
    assert result.profile.perk_slot_roi(0).x == pytest.approx(profile.perk_slot_roi(0).x + dx)
    assert result.profile.perk_slot_roi(0).y == pytest.approx(profile.perk_slot_roi(0).y + dy)


def test_hud_profile_round_trip_supports_left_loadout_item_and_two_addon_slots() -> None:
    profile = DBDHudRoiProfile(
        profile_id="loadout-profile",
        lower_left_loadout_hud=NormalizedROI("lower_left_loadout_hud", 0.13, 0.74, 0.20, 0.24),
        item_slot=NormalizedROI("item_slot", 0.14, 0.80, 0.08, 0.12),
        addon_slots=(
            NormalizedROI("addon_slot_0", 0.225, 0.80, 0.045, 0.055),
            NormalizedROI("addon_slot_1", 0.275, 0.80, 0.045, 0.055),
        ),
    )
    restored = DBDHudRoiProfile.from_dict(profile.to_dict())
    assert restored.to_dict()["schema_version"] == "2.2.0"
    assert restored.item_slot_roi().roi_id == "item_slot"
    assert restored.addon_slot_roi(0).roi_id == "addon_slot_0"
    assert restored.addon_slot_roi(1).roi_id == "addon_slot_1"
    assert restored.roi_by_id("lower_left_loadout_hud").width == pytest.approx(0.20)
