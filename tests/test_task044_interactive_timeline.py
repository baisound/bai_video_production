from fractions import Fraction

import pytest

from ai_video_production.desktop_shell import CommandCategory, ShellApplicationService
from ai_video_production.desktop_shell_projection import EditingProjection, TimelineBlock
from ai_video_production.errors import ProductError
from ai_video_production.interactive_timeline import (InteractiveTimeline,
    InteractiveTimelineClip, TimelineFitMode, TimelineFocusKind,
    TimelineInteractionReducer, TimelineInteractionState, TimelineMediaKind,
    TimelineTrack, TimelineTrackRole, TimelineViewport, TimelineWindowProjector)
from ai_video_production.interactive_timeline_projection import InteractiveTimelineProjectionService
from ai_video_production.timebase import FrameRate
from ai_video_production.timeline_audio import (AudioCue, AudioSourceBinding,
    AudioSourceIntent, TimelineAudioPlan)

SHA = "sha256:" + "1" * 64


def track(track_id: str = "V1", order: int = 0) -> TimelineTrack:
    return TimelineTrack(track_id, order, TimelineTrackRole.VIDEO, TimelineMediaKind.VIDEO, track_id, True)


def clip(clip_id: str = "clip-1", *, start: int = 0, end: int = 30,
         track_id: str = "V1", candidate: str | None = None) -> InteractiveTimelineClip:
    return InteractiveTimelineClip(clip_id, track_id, start, end, "TASK-007", clip_id,
                                   SHA, clip_id, "CURRENT", candidate)


def timeline(*clips: InteractiveTimelineClip, tracks: tuple[TimelineTrack, ...] | None = None,
             duration: int = 300) -> InteractiveTimeline:
    return InteractiveTimeline("project-1", "timeline-1", FrameRate(30), duration,
                               tracks or (track(),), tuple(clips))


def state(value: InteractiveTimeline) -> TimelineInteractionState:
    return TimelineInteractionState("project-1", value.timeline_sha256, 0)


def test_clip_selection_does_not_seek_and_seek_does_not_change_selection() -> None:
    item = clip(start=90, end=120)
    value = timeline(item)
    selected = TimelineInteractionReducer.select_clip(state(value), item)
    assert selected.playhead_frame == 0
    assert selected.selected_clip_ids == ("clip-1",)
    sought = TimelineInteractionReducer.seek(selected, frame=100, timeline_duration_frames=300)
    assert sought.playhead_frame == 100
    assert sought.selected_clip_ids == ("clip-1",)


def test_extended_selection_keeps_existing_items_without_duplicates() -> None:
    first, second = clip("clip-1"), clip("clip-2", start=30, end=60)
    value = timeline(first, second)
    selected = TimelineInteractionReducer.select_clip(state(value), first)
    selected = TimelineInteractionReducer.select_clip(selected, second, extend=True)
    selected = TimelineInteractionReducer.select_clip(selected, first, extend=True)
    assert selected.selected_clip_ids == ("clip-1", "clip-2")


def test_cut_candidate_review_identity_is_explicit_not_a_seek_side_effect() -> None:
    item = clip(candidate="candidate-1", start=100, end=130)
    selected = TimelineInteractionReducer.select_clip(state(timeline(item)), item)
    assert selected.review_candidate_id == "candidate-1"
    assert selected.playhead_frame == 0


def test_seek_and_in_out_fail_closed_on_invalid_ranges() -> None:
    value = timeline(clip())
    with pytest.raises(ProductError, match="outside"):
        TimelineInteractionReducer.seek(state(value), frame=300, timeline_duration_frames=300)
    with pytest.raises(ValueError, match="IN/OUT"):
        TimelineInteractionReducer.set_in_out(state(value), in_frame=50, out_frame=40)


def test_fit_uses_one_exact_rational_transform() -> None:
    viewport = TimelineViewport.fit(start_frame=0, end_frame=300, viewport_width_px=1000,
                                    rate=FrameRate(30), mode=TimelineFitMode.ENTIRE)
    assert viewport.pixels_per_second == Fraction(100, 1)
    assert viewport.frame_to_pixel(150, FrameRate(30)) == 500


def test_windowing_bounds_ten_thousand_clips_and_pages_deterministically() -> None:
    clips = tuple(clip(f"clip-{index:05d}", start=index, end=index + 1) for index in range(10_000))
    value = timeline(*clips, duration=10_001)
    viewport = TimelineViewport(0, 10_001, 100, 1)
    first = TimelineWindowProjector.project(value, viewport, max_clips=500)
    second = TimelineWindowProjector.project(value, viewport, clip_offset=first.next_clip_offset or 0, max_clips=500)
    assert first.total_intersecting_clips == 10_000
    assert len(first.clips) == len(second.clips) == 500
    assert first.next_clip_offset == 500
    assert first.clips[-1].clip_id < second.clips[0].clip_id


def test_vertical_track_window_excludes_hidden_track_clips() -> None:
    tracks = tuple(track(f"V{index}", index) for index in range(10))
    clips = tuple(clip(f"clip-{index}", track_id=f"V{index}") for index in range(10))
    value = timeline(*clips, tracks=tracks)
    projected = TimelineWindowProjector.project(value, TimelineViewport(0, 300, 100, 1, 3, 2))
    assert [item.track_id for item in projected.tracks] == ["V3", "V4"]
    assert {item.track_id for item in projected.clips} == {"V3", "V4"}


def test_legacy_projection_converts_microseconds_to_frame_bounds() -> None:
    source = EditingProjection(2_000_000, (), (
        TimelineBlock("cut:c1", "CUT_OVERLAY", "CUT_CANDIDATE", 100_001, 200_001,
                      "SILENCE", "REVIEW", ("candidate-1",)),
    ))
    value = InteractiveTimelineProjectionService.from_editing_projection(
        project_id="project-1", timeline_id="timeline-1", timeline_rate=FrameRate(30), projection=source)
    assert (value.clips[0].start_frame, value.clips[0].end_frame) == (3, 7)
    assert value.clips[0].review_candidate_id == "candidate-1"


def test_audio_plan_creates_dynamic_lane_track_with_exact_item_hash() -> None:
    binding = AudioSourceBinding("slot-se", AudioSourceIntent.GENERATION_INTENT)
    plan = TimelineAudioPlan("project-1", "timeline-1", 1, "blueprint-1", SHA,
        FrameRate(30), 300, (AudioCue("se-1", "foley", 30, 15, binding),))
    value = InteractiveTimelineProjectionService.from_audio_plan(plan)
    assert value.tracks[0].track_id == "audio:se:foley"
    assert value.clips[0].source_sha256 == plan.items[0].to_dict()["item_sha256"]


def test_shell_timeline_commands_have_narrow_reversible_authority() -> None:
    assert ShellApplicationService.command_spec("timeline.snapshot").category is CommandCategory.READ_ONLY
    for command in ("timeline.selection.update", "timeline.seek", "timeline.viewport.update"):
        assert ShellApplicationService.command_spec(command).category is CommandCategory.LOCAL_REVERSIBLE


@pytest.mark.parametrize("bad", [True, -1, 1.5])
def test_frame_fields_reject_bool_negative_and_float(bad) -> None:
    with pytest.raises(ValueError):
        clip(start=bad)
