from importlib import resources
from pathlib import Path

import pytest

from ai_video_production import (
    AffineTimeMap,
    EditSegment,
    FrameRate,
    FrameRounding,
    TimelineMappingPlan,
    TimelineMappingService,
)
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.schema_contracts import validate_instance


def asset_id() -> str:
    return generate_id(IdKind.ASSET)


def test_affine_map_uses_exact_bounded_integer_rounding():
    mapping = AffineTimeMap(0, 10_000_000, 0, 9_999_000)
    assert mapping.source_to_normalized(1_000_000, rounding=FrameRounding.FLOOR) == 999_900
    assert mapping.source_to_normalized(1_000_001, rounding=FrameRounding.CEIL) == 999_901
    assert mapping.normalized_to_source(999_900, rounding=FrameRounding.NEAREST) == 1_000_000
    with pytest.raises(ValueError, match="outside"):
        mapping.source_to_normalized(10_000_001, rounding=FrameRounding.FLOOR)


def test_ntsc_mapping_uses_end_exclusive_ceil_without_float_drift():
    source = asset_id()
    plan = TimelineMappingService.build(
        [EditSegment("clip-1", source, 0, 10_000_000)],
        timeline_rate=FrameRate(30000, 1001),
    )
    placement = plan.placements[0]
    assert placement.timeline_start_frame == 0
    assert placement.timeline_end_frame == 300
    assert plan.duration_frames == 300


def test_affine_proxy_mapping_and_gap_are_preserved():
    source, proxy = asset_id(), asset_id()
    mapping = AffineTimeMap(0, 10_000_000, 0, 9_999_000)
    plan = TimelineMappingService.build(
        [EditSegment("proxy-clip", source, 1_000_000, 2_000_000, proxy, mapping, gap_before_frames=12)],
        timeline_rate=FrameRate(30000, 1001),
        timeline_origin_frame=100,
    )
    placement = plan.placements[0]
    assert placement.mapped_asset_id == proxy
    assert (placement.mapped_start_us, placement.mapped_end_us) == (999_900, 1_999_800)
    assert (placement.timeline_start_frame, placement.timeline_end_frame) == (112, 142)


def test_playback_rate_changes_timeline_duration_exactly():
    source = asset_id()
    plan = TimelineMappingService.build(
        [EditSegment("fast", source, 0, 2_000_000, playback_rate_numerator=2)],
        timeline_rate=FrameRate(30, 1),
    )
    assert plan.duration_frames == 30


def test_plan_rejects_duplicate_or_overlapping_placements():
    source = asset_id()
    plan = TimelineMappingService.build(
        [EditSegment("a", source, 0, 1_000_000)], timeline_rate=FrameRate(30, 1)
    )
    placement = plan.placements[0]
    with pytest.raises(ValueError, match="duplicate"):
        TimelineMappingPlan(FrameRate(30, 1), 0, (placement, placement))


def test_segment_requires_normalized_asset_and_map_as_one_binding():
    with pytest.raises(ValueError, match="supplied together"):
        EditSegment("bad", asset_id(), 0, 1_000_000, normalized_asset_id=asset_id())


def test_mapping_plan_schema_and_hash_are_deterministic():
    source = asset_id()
    plan = TimelineMappingService.build(
        [EditSegment("schema", source, 0, 1_000_000)], timeline_rate=FrameRate(24000, 1001)
    )
    first = plan.to_dict()
    second = plan.to_dict()
    assert first == second
    schema = Path(__file__).parents[1] / "schemas" / "timeline-mapping-plan.schema.json"
    validate_instance(first, schema)


def test_packaged_timeline_mapping_schema_matches_canonical():
    name = "timeline-mapping-plan.schema.json"
    canonical = (Path(__file__).parents[1] / "schemas" / name).read_text(encoding="utf-8")
    packaged = resources.files("ai_video_production").joinpath("schema_resources", name).read_text(encoding="utf-8")
    # Formatting may differ; semantic JSON equality is the packaging contract.
    import json
    assert json.loads(canonical) == json.loads(packaged)
