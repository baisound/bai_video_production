"""Configurable Owner-voice recording coverage and reference eligibility.

The original Voice Studio design treats duration as a target, not a hard-coded
2-hour requirement.  This module keeps overall, style, and emotion coverage
separate and counts only usable, approved, de-duplicated material.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping
import re

SAMPLE_RATE_HZ = 48_000
DEFAULT_STYLE_IDS = (
    "NORMAL",
    "NORMAL_TO_WHISPER",
    "WHISPER",
    "SAD",
    "ANGRY",
    "AFRAID",
    "PROJECTED",
    "SPORTS_COMMENTARY",
)
DEFAULT_EMOTION_IDS = (
    "NORMAL",
    "JOY",
    "SAD",
    "ANGRY",
    "AFRAID",
    "EXCITED",
    "TENSE",
    "GENTLE",
)
_ID = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


def _axis(value: str, name: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _seconds_to_samples(value: float | int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{name} must be positive seconds")
    samples = round(float(value) * SAMPLE_RATE_HZ)
    if samples <= 0:
        raise ValueError(f"{name} is too small")
    return samples


@dataclass(frozen=True, slots=True)
class RecordingCoverageSegment:
    segment_id: str
    content_sha256: str
    duration_samples: int
    style_id: str
    emotion_id: str
    quality_pass: bool
    owner_approved: bool
    transcript_verified: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.segment_id, str) or not self.segment_id or len(self.segment_id) > 200:
            raise ValueError("segment_id is invalid")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", self.content_sha256):
            raise ValueError("content_sha256 is invalid")
        if isinstance(self.duration_samples, bool) or not isinstance(self.duration_samples, int) or self.duration_samples <= 0:
            raise ValueError("duration_samples must be positive")
        _axis(self.style_id, "style_id")
        _axis(self.emotion_id, "emotion_id")
        for name in ("quality_pass", "owner_approved", "transcript_verified"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be boolean")


@dataclass(frozen=True, slots=True)
class RecordingCoverageTarget:
    overall_target_samples: int
    style_target_samples: Mapping[str, int]
    emotion_target_samples: Mapping[str, int]

    @classmethod
    def from_seconds(
        cls,
        overall_target_seconds: float | int,
        *,
        style_target_seconds: Mapping[str, float | int] | None = None,
        emotion_target_seconds: Mapping[str, float | int] | None = None,
    ) -> "RecordingCoverageTarget":
        return cls(
            _seconds_to_samples(overall_target_seconds, "overall_target_seconds"),
            { _axis(k, "style_id"): _seconds_to_samples(v, f"style target {k}") for k,v in (style_target_seconds or {}).items()},
            { _axis(k, "emotion_id"): _seconds_to_samples(v, f"emotion target {k}") for k,v in (emotion_target_seconds or {}).items()},
        )

    def __post_init__(self) -> None:
        if isinstance(self.overall_target_samples, bool) or not isinstance(self.overall_target_samples, int) or self.overall_target_samples <= 0:
            raise ValueError("overall_target_samples must be positive")
        for mapping, axis_name in ((self.style_target_samples, "style"), (self.emotion_target_samples, "emotion")):
            for key, value in mapping.items():
                _axis(key, f"{axis_name}_id")
                if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                    raise ValueError(f"{axis_name} target must be positive")


@dataclass(frozen=True, slots=True)
class CoverageBucket:
    axis_id: str
    target_samples: int
    usable_samples: int

    @property
    def percentage_basis_points(self) -> int:
        return min(10_000, (self.usable_samples * 10_000) // self.target_samples)

    @property
    def percentage(self) -> float:
        return self.percentage_basis_points / 100.0

    @property
    def remaining_samples(self) -> int:
        return max(0, self.target_samples - self.usable_samples)

    @property
    def remaining_seconds(self) -> float:
        return self.remaining_samples / SAMPLE_RATE_HZ

    def to_dict(self) -> dict[str, object]:
        return {
            "axis_id": self.axis_id,
            "target_samples": self.target_samples,
            "usable_samples": self.usable_samples,
            "percentage_basis_points": self.percentage_basis_points,
            "percentage": self.percentage,
            "remaining_samples": self.remaining_samples,
            "remaining_seconds": self.remaining_seconds,
        }


@dataclass(frozen=True, slots=True)
class VoiceRecordingCoverage:
    raw_samples: int
    usable_samples: int
    rejected_samples: int
    unapproved_samples: int
    duplicate_samples: int
    overall: CoverageBucket
    styles: tuple[CoverageBucket, ...]
    emotions: tuple[CoverageBucket, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "sample_rate_hz": SAMPLE_RATE_HZ,
            "raw_samples": self.raw_samples,
            "usable_samples": self.usable_samples,
            "rejected_samples": self.rejected_samples,
            "unapproved_samples": self.unapproved_samples,
            "duplicate_samples": self.duplicate_samples,
            "overall": self.overall.to_dict(),
            "styles": [x.to_dict() for x in self.styles],
            "emotions": [x.to_dict() for x in self.emotions],
        }


def compute_recording_coverage(
    segments: Iterable[RecordingCoverageSegment], target: RecordingCoverageTarget
) -> VoiceRecordingCoverage:
    values = tuple(segments)
    seen: set[str] = set()
    raw = usable = rejected = unapproved = duplicate = 0
    style_samples: dict[str, int] = {}
    emotion_samples: dict[str, int] = {}
    for item in values:
        if not isinstance(item, RecordingCoverageSegment):
            raise ValueError("segments must contain RecordingCoverageSegment")
        raw += item.duration_samples
        if not item.quality_pass:
            rejected += item.duration_samples
            continue
        if not item.owner_approved:
            unapproved += item.duration_samples
            continue
        if item.content_sha256 in seen:
            duplicate += item.duration_samples
            continue
        seen.add(item.content_sha256)
        usable += item.duration_samples
        style_samples[item.style_id] = style_samples.get(item.style_id, 0) + item.duration_samples
        emotion_samples[item.emotion_id] = emotion_samples.get(item.emotion_id, 0) + item.duration_samples
    styles = tuple(
        CoverageBucket(key, target.style_target_samples[key], style_samples.get(key, 0))
        for key in sorted(target.style_target_samples)
    )
    emotions = tuple(
        CoverageBucket(key, target.emotion_target_samples[key], emotion_samples.get(key, 0))
        for key in sorted(target.emotion_target_samples)
    )
    return VoiceRecordingCoverage(
        raw, usable, rejected, unapproved, duplicate,
        CoverageBucket("OVERALL", target.overall_target_samples, usable), styles, emotions,
    )


__all__ = [
    "CoverageBucket", "DEFAULT_EMOTION_IDS", "DEFAULT_STYLE_IDS",
    "RecordingCoverageSegment", "RecordingCoverageTarget", "SAMPLE_RATE_HZ",
    "VoiceRecordingCoverage", "compute_recording_coverage",
]
