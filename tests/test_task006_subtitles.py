from importlib import resources
import json
from pathlib import Path

import pytest

from ai_video_production import (
    EditSegment, FrameRate, SrtRenderer, SubtitlePlanningService,
    TimelineMappingService, TranscriptManifest, TranscriptSegment,
)
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.schema_contracts import validate_instance


def _asset() -> str:
    return generate_id(IdKind.ASSET)


def _transcript(asset_id: str) -> TranscriptManifest:
    return TranscriptManifest(
        asset_id, "ja", "fixture", "human-reviewed",
        (
            TranscriptSegment("seg-1", 500_000, 1_500_000, "こんにちは", 0.98),
            TranscriptSegment("seg-2", 2_000_000, 3_000_000, "次の字幕です", 0.91),
        ),
    )


def test_transcript_rejects_overlap_duplicate_and_unsafe_text() -> None:
    asset = _asset()
    with pytest.raises(ValueError, match="overlap"):
        TranscriptManifest(asset, "ja", "fixture", "model", (
            TranscriptSegment("a", 0, 2_000_000, "one"),
            TranscriptSegment("b", 1_000_000, 3_000_000, "two"),
        ))
    with pytest.raises(ValueError, match="NUL"):
        TranscriptSegment("unsafe", 0, 1, "bad\x00text")


def test_uncut_timeline_maps_transcript_to_exact_frames() -> None:
    asset = _asset()
    timeline = TimelineMappingService.build(
        [EditSegment("clip", asset, 0, 4_000_000)], timeline_rate=FrameRate(30, 1)
    )
    plan = SubtitlePlanningService.build(_transcript(asset), timeline)
    assert [(item.timeline_start_frame, item.timeline_end_frame) for item in plan.cues] == [
        (15, 45), (60, 90),
    ]


def test_cut_aware_plan_removes_cut_portion_and_retimes_survivors() -> None:
    asset = _asset()
    timeline = TimelineMappingService.build(
        [
            EditSegment("keep-a", asset, 0, 1_000_000),
            EditSegment("keep-b", asset, 2_000_000, 4_000_000),
        ],
        timeline_rate=FrameRate(30, 1),
    )
    plan = SubtitlePlanningService.build(_transcript(asset), timeline)
    assert [(cue.source_segment_id, cue.timeline_start_frame, cue.timeline_end_frame) for cue in plan.cues] == [
        ("seg-1", 15, 30),
        ("seg-2", 30, 60),
    ]


def test_segment_crossing_two_kept_ranges_is_split_deterministically() -> None:
    asset = _asset()
    transcript = TranscriptManifest(
        asset, "en", "fixture", "model", (TranscriptSegment("wide", 500_000, 2_500_000, "Across cuts"),),
    )
    timeline = TimelineMappingService.build(
        [EditSegment("a", asset, 0, 1_000_000), EditSegment("b", asset, 2_000_000, 3_000_000)],
        timeline_rate=FrameRate(30000, 1001),
    )
    plan = SubtitlePlanningService.build(transcript, timeline)
    assert [cue.cue_id for cue in plan.cues] == ["a-wide", "b-wide"]
    assert plan.to_dict() == SubtitlePlanningService.build(transcript, timeline).to_dict()


def test_srt_uses_ntsc_safe_floor_start_and_ceil_end() -> None:
    asset = _asset()
    timeline = TimelineMappingService.build(
        [EditSegment("clip", asset, 0, 1_000_000)], timeline_rate=FrameRate(30000, 1001)
    )
    transcript = TranscriptManifest(
        asset, "ja", "fixture", "model", (TranscriptSegment("one", 0, 1_000_000, "1行目\r\n2行目"),),
    )
    rendered = SrtRenderer.render(SubtitlePlanningService.build(transcript, timeline))
    assert rendered == "1\n00:00:00,000 --> 00:00:01,001\n1行目\n2行目\n"


def test_empty_plan_renders_empty_srt() -> None:
    asset, other = _asset(), _asset()
    timeline = TimelineMappingService.build(
        [EditSegment("other", other, 0, 1_000_000)], timeline_rate=FrameRate(30, 1)
    )
    plan = SubtitlePlanningService.build(_transcript(asset), timeline)
    assert plan.cues == ()
    assert SrtRenderer.render(plan) == ""


def test_adjacent_microsecond_segments_remain_non_overlapping_at_ntsc_rate() -> None:
    asset = _asset()
    transcript = TranscriptManifest(asset, "ja", "fixture", "model", (
        TranscriptSegment("a", 100_000, 1_250_000, "前"),
        TranscriptSegment("b", 1_250_000, 2_000_000, "後"),
    ))
    timeline = TimelineMappingService.build(
        [EditSegment("clip", asset, 0, 2_000_000)], timeline_rate=FrameRate(30000, 1001)
    )
    plan = SubtitlePlanningService.build(transcript, timeline)
    assert plan.cues[0].timeline_end_frame == plan.cues[1].timeline_start_frame


def test_transcript_and_subtitle_schemas_validate_and_are_packaged() -> None:
    asset = _asset()
    transcript = _transcript(asset)
    timeline = TimelineMappingService.build(
        [EditSegment("clip", asset, 0, 4_000_000)], timeline_rate=FrameRate(30, 1)
    )
    documents = {
        "transcript-manifest.schema.json": transcript.to_dict(),
        "subtitle-plan.schema.json": SubtitlePlanningService.build(transcript, timeline).to_dict(),
    }
    for name, document in documents.items():
        canonical = Path(__file__).parents[1] / "schemas" / name
        validate_instance(document, canonical)
        packaged = resources.files("ai_video_production").joinpath("schema_resources", name)
        assert json.loads(canonical.read_text(encoding="utf-8")) == json.loads(packaged.read_text(encoding="utf-8"))
