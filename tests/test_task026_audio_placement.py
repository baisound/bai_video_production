from __future__ import annotations

import pytest

from ai_video_production.audio_placement import (
    AudioPlacementRequest,
    AudioPlacementRole,
    AudioPlacementService,
    BedMode,
    SnapAnchor,
)
from ai_video_production.errors import ProductError


def test_bounded_snap_selects_nearest_anchor_with_lower_frame_tie_break():
    request = AudioPlacementRequest(
        "asset-se", AudioPlacementRole.SE, 3, 30, 100, 20,
        snap_tolerance_frames=5,
        snap_anchors=(SnapAnchor(104, "event-b"), SnapAnchor(96, "event-a"), SnapAnchor(140, "too-far")),
    )
    plan = AudioPlacementService.compile(request)
    assert plan.effective_start_frame == 96
    assert plan.snapped_to.reason == "event-a"


def test_snap_never_exceeds_tolerance():
    request = AudioPlacementRequest(
        "asset-se", AudioPlacementRole.SE, 3, 30, 100, 20,
        snap_tolerance_frames=3,
        snap_anchors=(SnapAnchor(104, "outside"),),
    )
    plan = AudioPlacementService.compile(request)
    assert plan.effective_start_frame == 100
    assert plan.snapped_to is None


def test_loop_segments_exact_requested_bgm_bed_duration():
    request = AudioPlacementRequest(
        "asset-bgm", AudioPlacementRole.BGM, 4, 100, 0, 250,
        loop=True, bed_mode=BedMode.FULL,
    )
    plan = AudioPlacementService.compile(request)
    assert [item.duration_frames for item in plan.segments] == [100, 100, 50]
    assert [item.timeline_start_frame for item in plan.segments] == [0, 100, 200]
    assert sum(item.duration_frames for item in plan.segments) == 250
    assert len(plan.to_task010_audio_placements()) == 3


def test_long_bed_without_loop_fails_closed():
    request = AudioPlacementRequest("asset-bgm", AudioPlacementRole.BGM, 4, 100, 0, 101, loop=False)
    with pytest.raises(ProductError) as exc:
        AudioPlacementService.compile(request)
    assert exc.value.code == "ERR_AUDIO_PLACEMENT_LOOP_REQUIRED"


def test_narration_cannot_loop():
    with pytest.raises(ValueError):
        AudioPlacementRequest("asset-narr", AudioPlacementRole.NARRATION, 2, 100, 0, 200, loop=True)


def test_fade_or_gain_plan_is_valid_but_not_silently_downgraded_to_task010():
    request = AudioPlacementRequest(
        "asset-bgm", AudioPlacementRole.BGM, 4, 300, 0, 300,
        fade_in_frames=15, fade_out_frames=30, gain_db=-8.0,
    )
    plan = AudioPlacementService.compile(request)
    assert plan.task010_compatible is False
    with pytest.raises(ProductError) as exc:
        plan.to_task010_audio_placements()
    assert exc.value.code == "ERR_AUDIO_PLACEMENT_TASK010_FEATURE_GAP"


def test_same_request_produces_same_plan_hash():
    request = AudioPlacementRequest("asset-se", AudioPlacementRole.SE, 3, 30, 100, 20)
    assert AudioPlacementService.compile(request).to_dict()["plan_sha256"] == AudioPlacementService.compile(request).to_dict()["plan_sha256"]
