from __future__ import annotations

from statistics import median
import time

from ai_video_production.interactive_timeline import (
    InteractiveTimeline,
    InteractiveTimelineClip,
    TimelineMediaKind,
    TimelineTrack,
    TimelineTrackRole,
)
from ai_video_production.serialization import sha256_bytes
from ai_video_production.task044_nle_shell import Task044NleShellController
from ai_video_production.timebase import FrameRate


def two_hour_timeline() -> InteractiveTimeline:
    rate = FrameRate(30)
    duration_frames = 2 * 60 * 60 * 30 + 1
    tracks = (
        TimelineTrack("V1", 0, TimelineTrackRole.VIDEO, TimelineMediaKind.VIDEO, "Video", True),
        TimelineTrack("A1", 1, TimelineTrackRole.AUDIO, TimelineMediaKind.AUDIO, "Audio", True),
    )
    step = duration_frames // 10_000
    clips = tuple(
        InteractiveTimelineClip(
            f"clip-{index:05d}",
            "V1" if index % 2 == 0 else "A1",
            index * step,
            min(index * step + 10, duration_frames),
            "TASK-007",
            f"source-{index:05d}",
            sha256_bytes(str(index).encode()),
            f"Clip {index}",
            "CURRENT",
        )
        for index in range(10_000)
    )
    return InteractiveTimeline(
        "task045-release-project",
        "task045-two-hour-timeline",
        rate,
        duration_frames,
        tracks,
        clips,
    )


def test_two_hour_ten_thousand_clip_controller_projection_is_bounded_and_fast() -> None:
    value = two_hour_timeline()
    controller = Task044NleShellController(timeline=value)
    samples_ms: list[float] = []
    snapshots = []
    for _ in range(7):
        started = time.perf_counter()
        snapshots.append(controller.snapshot({"clip_offset": 0, "max_clips": 500}))
        samples_ms.append((time.perf_counter() - started) * 1000)

    projection = snapshots[-1]["projection"]
    assert value.duration_frames > 2 * 60 * 60 * value.timeline_rate.numerator
    assert projection["total_intersecting_clips"] == 10_000
    assert len(projection["clips"]) == 500
    assert projection["next_clip_offset"] == 500
    assert median(samples_ms) <= 500
    assert snapshots[-1]["durable_state_in_javascript"] is False
