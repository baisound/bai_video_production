from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Iterable

from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes
from .timebase import FrameRate, FrameRounding


def _round(value: Fraction, mode: FrameRounding) -> int:
    floor = value.numerator // value.denominator
    if mode is FrameRounding.FLOOR:
        return floor
    if mode is FrameRounding.CEIL:
        return floor if value == floor else floor + 1
    return floor + (1 if value - floor >= Fraction(1, 2) else 0)


@dataclass(frozen=True, slots=True)
class AffineTimeMap:
    """Exact bounded mapping between source and normalized media clocks."""

    source_start_us: int
    source_duration_us: int
    normalized_start_us: int
    normalized_duration_us: int

    def __post_init__(self) -> None:
        if min(self.source_start_us, self.normalized_start_us) < 0:
            raise ValueError("mapping starts must be >= 0")
        if self.source_duration_us <= 0 or self.normalized_duration_us <= 0:
            raise ValueError("mapping durations must be positive")

    @property
    def source_end_us(self) -> int:
        return self.source_start_us + self.source_duration_us

    @property
    def normalized_end_us(self) -> int:
        return self.normalized_start_us + self.normalized_duration_us

    def source_to_normalized(self, source_us: int, *, rounding: FrameRounding) -> int:
        if not self.source_start_us <= source_us <= self.source_end_us:
            raise ValueError("source timestamp is outside affine mapping")
        relative = Fraction(
            (source_us - self.source_start_us) * self.normalized_duration_us,
            self.source_duration_us,
        )
        return self.normalized_start_us + _round(relative, rounding)

    def normalized_to_source(self, normalized_us: int, *, rounding: FrameRounding) -> int:
        if not self.normalized_start_us <= normalized_us <= self.normalized_end_us:
            raise ValueError("normalized timestamp is outside affine mapping")
        relative = Fraction(
            (normalized_us - self.normalized_start_us) * self.source_duration_us,
            self.normalized_duration_us,
        )
        return self.source_start_us + _round(relative, rounding)

    def to_dict(self) -> dict[str, int | str]:
        return {
            "mapping_kind": "WHOLE_FILE_AFFINE",
            "source_start_us": self.source_start_us,
            "source_duration_us": self.source_duration_us,
            "normalized_start_us": self.normalized_start_us,
            "normalized_duration_us": self.normalized_duration_us,
        }


@dataclass(frozen=True, slots=True)
class EditSegment:
    placement_id: str
    source_asset_id: str
    source_start_us: int
    source_end_us: int
    normalized_asset_id: str | None = None
    affine_map: AffineTimeMap | None = None
    playback_rate_numerator: int = 1
    playback_rate_denominator: int = 1
    gap_before_frames: int = 0

    def __post_init__(self) -> None:
        if not self.placement_id or len(self.placement_id) > 128:
            raise ValueError("placement_id must be 1-128 characters")
        validate_id(self.source_asset_id, IdKind.ASSET)
        if self.normalized_asset_id is not None:
            validate_id(self.normalized_asset_id, IdKind.ASSET)
        if self.source_start_us < 0 or self.source_end_us <= self.source_start_us:
            raise ValueError("source range must be positive and end-exclusive")
        if self.playback_rate_numerator <= 0 or self.playback_rate_denominator <= 0:
            raise ValueError("playback rate must be positive")
        if self.gap_before_frames < 0:
            raise ValueError("gap_before_frames must be >= 0")
        if (self.normalized_asset_id is None) != (self.affine_map is None):
            raise ValueError("normalized_asset_id and affine_map must be supplied together")
        if self.affine_map is not None:
            if self.source_start_us < self.affine_map.source_start_us or self.source_end_us > self.affine_map.source_end_us:
                raise ValueError("source range is outside affine mapping")

    @property
    def playback_rate(self) -> Fraction:
        return Fraction(self.playback_rate_numerator, self.playback_rate_denominator)


@dataclass(frozen=True, slots=True)
class TimelinePlacement:
    placement_id: str
    source_asset_id: str
    mapped_asset_id: str
    source_start_us: int
    source_end_us: int
    mapped_start_us: int
    mapped_end_us: int
    timeline_start_frame: int
    timeline_end_frame: int
    playback_rate_numerator: int
    playback_rate_denominator: int

    def __post_init__(self) -> None:
        if self.timeline_start_frame < 0 or self.timeline_end_frame <= self.timeline_start_frame:
            raise ValueError("timeline placement must contain at least one frame")

    def to_dict(self) -> dict[str, Any]:
        return {
            "placement_id": self.placement_id,
            "source_asset_id": self.source_asset_id,
            "mapped_asset_id": self.mapped_asset_id,
            "source_range_us": {"start": self.source_start_us, "end_exclusive": self.source_end_us},
            "mapped_range_us": {"start": self.mapped_start_us, "end_exclusive": self.mapped_end_us},
            "timeline_range_frames": {
                "start": self.timeline_start_frame,
                "end_exclusive": self.timeline_end_frame,
            },
            "playback_rate": {
                "numerator": self.playback_rate_numerator,
                "denominator": self.playback_rate_denominator,
            },
        }


@dataclass(frozen=True, slots=True)
class TimelineMappingPlan:
    timeline_rate: FrameRate
    timeline_origin_frame: int
    placements: tuple[TimelinePlacement, ...]

    def __post_init__(self) -> None:
        if self.timeline_origin_frame < 0:
            raise ValueError("timeline_origin_frame must be >= 0")
        ids: set[str] = set()
        previous_end = self.timeline_origin_frame
        for placement in self.placements:
            if placement.placement_id in ids:
                raise ValueError("duplicate placement_id")
            if placement.timeline_start_frame < previous_end:
                raise ValueError("timeline placements overlap or are out of order")
            ids.add(placement.placement_id)
            previous_end = placement.timeline_end_frame

    @property
    def timeline_end_frame(self) -> int:
        return self.placements[-1].timeline_end_frame if self.placements else self.timeline_origin_frame

    @property
    def duration_frames(self) -> int:
        return self.timeline_end_frame - self.timeline_origin_frame

    def to_dict(self) -> dict[str, Any]:
        body = {
            "plan_version": "1.0.0",
            "timeline_rate": {
                "numerator": self.timeline_rate.numerator,
                "denominator": self.timeline_rate.denominator,
            },
            "timeline_origin_frame": self.timeline_origin_frame,
            "timeline_end_frame": self.timeline_end_frame,
            "duration_frames": self.duration_frames,
            "placements": [placement.to_dict() for placement in self.placements],
        }
        body["plan_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class TimelineMappingService:
    """Compile source ranges into exact, non-overlapping timeline placements."""

    @staticmethod
    def build(
        segments: Iterable[EditSegment],
        *,
        timeline_rate: FrameRate,
        timeline_origin_frame: int = 0,
    ) -> TimelineMappingPlan:
        if timeline_origin_frame < 0:
            raise ValueError("timeline_origin_frame must be >= 0")
        cursor = timeline_origin_frame
        placements: list[TimelinePlacement] = []
        for segment in segments:
            cursor += segment.gap_before_frames
            if segment.affine_map is None:
                mapped_start = segment.source_start_us
                mapped_end = segment.source_end_us
                mapped_asset_id = segment.source_asset_id
            else:
                mapped_start = segment.affine_map.source_to_normalized(
                    segment.source_start_us, rounding=FrameRounding.FLOOR
                )
                mapped_end = segment.affine_map.source_to_normalized(
                    segment.source_end_us, rounding=FrameRounding.CEIL
                )
                assert segment.normalized_asset_id is not None
                mapped_asset_id = segment.normalized_asset_id

            mapped_duration = mapped_end - mapped_start
            timeline_duration_us = Fraction(mapped_duration, 1) / segment.playback_rate
            frame_duration = _round(
                timeline_duration_us * timeline_rate.numerator
                / (1_000_000 * timeline_rate.denominator),
                FrameRounding.CEIL,
            )
            frame_duration = max(1, frame_duration)
            placement = TimelinePlacement(
                placement_id=segment.placement_id,
                source_asset_id=segment.source_asset_id,
                mapped_asset_id=mapped_asset_id,
                source_start_us=segment.source_start_us,
                source_end_us=segment.source_end_us,
                mapped_start_us=mapped_start,
                mapped_end_us=mapped_end,
                timeline_start_frame=cursor,
                timeline_end_frame=cursor + frame_duration,
                playback_rate_numerator=segment.playback_rate_numerator,
                playback_rate_denominator=segment.playback_rate_denominator,
            )
            placements.append(placement)
            cursor = placement.timeline_end_frame
        return TimelineMappingPlan(timeline_rate, timeline_origin_frame, tuple(placements))
