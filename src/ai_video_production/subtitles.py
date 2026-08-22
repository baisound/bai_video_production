"""Canonical transcript, cut-aware subtitle planning, and deterministic SRT."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import re
from typing import Any, Iterable, Protocol

from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes
from .timebase import FrameRate
from .timeline_mapping import TimelineMappingPlan


_SAFE_TEXT = re.compile(r"^[^\x00]*$")


def _floor(value: Fraction) -> int:
    return value.numerator // value.denominator


def _ceil(value: Fraction) -> int:
    floor = _floor(value)
    return floor if value == floor else floor + 1


def _text(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("subtitle text must be text")
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized or len(normalized) > 10_000 or not _SAFE_TEXT.fullmatch(normalized):
        raise ValueError("subtitle text must be non-empty bounded text without NUL")
    return normalized


def _word_text(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("transcript word text must be text")
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized or len(normalized) > 512 or not _SAFE_TEXT.fullmatch(normalized):
        raise ValueError("transcript word text must be non-empty bounded text without NUL")
    return normalized


@dataclass(frozen=True, slots=True)
class TranscriptWord:
    start_us: int
    end_us: int
    text: str
    confidence: float | None = None

    def __post_init__(self) -> None:
        if self.start_us < 0 or self.end_us <= self.start_us:
            raise ValueError("transcript word range must be positive and end-exclusive")
        object.__setattr__(self, "text", _word_text(self.text))
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("word confidence must be 0-1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "range_us": {"start": self.start_us, "end_exclusive": self.end_us},
            "text": self.text,
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    segment_id: str
    start_us: int
    end_us: int
    text: str
    confidence: float | None = None
    speaker: str | None = None
    words: tuple[TranscriptWord, ...] = ()

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", self.segment_id):
            raise ValueError("segment_id is invalid")
        if self.start_us < 0 or self.end_us <= self.start_us:
            raise ValueError("transcript range must be positive and end-exclusive")
        object.__setattr__(self, "text", _text(self.text))
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be 0-1")
        if self.speaker is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", self.speaker):
            raise ValueError("speaker is invalid")

        words = tuple(self.words)
        if any(not isinstance(word, TranscriptWord) for word in words):
            raise ValueError("transcript words must contain TranscriptWord values")
        object.__setattr__(self, "words", words)
        previous_end = self.start_us
        for word in words:
            if word.start_us < self.start_us or word.end_us > self.end_us:
                raise ValueError("transcript word must be contained by its segment")
            if word.start_us < previous_end:
                raise ValueError("transcript words overlap or are out of order")
            previous_end = word.end_us

    def to_dict(self, *, include_words: bool = False) -> dict[str, Any]:
        body = {
            "segment_id": self.segment_id,
            "range_us": {"start": self.start_us, "end_exclusive": self.end_us},
            "text": self.text,
            "confidence": self.confidence,
            "speaker": self.speaker,
        }
        if include_words:
            body["words"] = [word.to_dict() for word in self.words]
        return body


@dataclass(frozen=True, slots=True)
class TranscriptManifest:
    source_asset_id: str
    language: str
    provider_id: str
    model_id: str
    segments: tuple[TranscriptSegment, ...]
    word_timestamps_included: bool = False

    def __post_init__(self) -> None:
        validate_id(self.source_asset_id, IdKind.ASSET)
        if not re.fullmatch(r"[a-z]{2,3}(?:-[A-Z]{2})?", self.language):
            raise ValueError("language must be a BCP-47 language tag")
        for name, value in (("provider_id", self.provider_id), ("model_id", self.model_id)):
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}", value):
                raise ValueError(f"{name} is invalid")
        previous_end = 0
        ids: set[str] = set()
        for segment in self.segments:
            if segment.segment_id in ids:
                raise ValueError("duplicate transcript segment_id")
            if segment.start_us < previous_end:
                raise ValueError("transcript segments overlap or are out of order")
            ids.add(segment.segment_id)
            previous_end = segment.end_us
            if segment.words and not self.word_timestamps_included:
                raise ValueError("word-timed segments require word_timestamps_included=True")

    def to_dict(self) -> dict[str, Any]:
        version = "1.1.0" if self.word_timestamps_included else "1.0.0"
        body = {
            "manifest_version": version,
            "source_asset_id": self.source_asset_id,
            "language": self.language,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "segments": [
                item.to_dict(include_words=self.word_timestamps_included)
                for item in self.segments
            ],
        }
        body["manifest_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(frozen=True, slots=True)
class AsrRequest:
    source_asset_id: str
    media_path: str
    language: str | None = None
    include_word_timestamps: bool = False

    def __post_init__(self) -> None:
        validate_id(self.source_asset_id, IdKind.ASSET)
        if not self.media_path or "\x00" in self.media_path:
            raise ValueError("media_path is invalid")


class AsrProvider(Protocol):
    provider_id: str
    model_id: str

    def transcribe(self, request: AsrRequest) -> TranscriptManifest: ...


@dataclass(frozen=True, slots=True)
class SubtitleCue:
    cue_id: str
    source_segment_id: str
    timeline_start_frame: int
    timeline_end_frame: int
    text: str

    def __post_init__(self) -> None:
        if self.timeline_start_frame < 0 or self.timeline_end_frame <= self.timeline_start_frame:
            raise ValueError("subtitle cue must contain at least one frame")
        object.__setattr__(self, "text", _text(self.text))

    def to_dict(self) -> dict[str, Any]:
        return {
            "cue_id": self.cue_id,
            "source_segment_id": self.source_segment_id,
            "timeline_range_frames": {
                "start": self.timeline_start_frame,
                "end_exclusive": self.timeline_end_frame,
            },
            "text": self.text,
        }


@dataclass(frozen=True, slots=True)
class SubtitlePlan:
    source_asset_id: str
    timeline_rate: FrameRate
    language: str
    cues: tuple[SubtitleCue, ...]

    def __post_init__(self) -> None:
        validate_id(self.source_asset_id, IdKind.ASSET)
        previous_end = 0
        ids: set[str] = set()
        for cue in self.cues:
            if cue.cue_id in ids:
                raise ValueError("duplicate subtitle cue_id")
            if cue.timeline_start_frame < previous_end:
                raise ValueError("subtitle cues overlap or are out of order")
            ids.add(cue.cue_id)
            previous_end = cue.timeline_end_frame

    def to_dict(self) -> dict[str, Any]:
        body = {
            "plan_version": "1.0.0",
            "source_asset_id": self.source_asset_id,
            "timeline_rate": {
                "numerator": self.timeline_rate.numerator,
                "denominator": self.timeline_rate.denominator,
            },
            "language": self.language,
            "cues": [item.to_dict() for item in self.cues],
        }
        body["plan_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class SubtitlePlanningService:
    """Map transcript segments through a cut plan without floating-point drift."""

    @staticmethod
    def build(transcript: TranscriptManifest, timeline: TimelineMappingPlan) -> SubtitlePlan:
        cues: list[SubtitleCue] = []
        for placement in timeline.placements:
            if placement.source_asset_id != transcript.source_asset_id:
                continue
            source_duration = placement.source_end_us - placement.source_start_us
            timeline_duration = placement.timeline_end_frame - placement.timeline_start_frame
            for segment in transcript.segments:
                start = max(segment.start_us, placement.source_start_us)
                end = min(segment.end_us, placement.source_end_us)
                if end <= start:
                    continue
                start_frame = placement.timeline_start_frame + _floor(
                    Fraction((start - placement.source_start_us) * timeline_duration, source_duration)
                )
                end_frame = placement.timeline_start_frame + _ceil(
                    Fraction((end - placement.source_start_us) * timeline_duration, source_duration)
                )
                if cues:
                    start_frame = max(start_frame, cues[-1].timeline_end_frame)
                end_frame = max(start_frame + 1, end_frame)
                if start_frame >= placement.timeline_end_frame:
                    continue
                end_frame = min(end_frame, placement.timeline_end_frame)
                cues.append(SubtitleCue(
                    f"{placement.placement_id}-{segment.segment_id}",
                    segment.segment_id,
                    start_frame,
                    end_frame,
                    segment.text,
                ))
        return SubtitlePlan(transcript.source_asset_id, timeline.timeline_rate, transcript.language, tuple(cues))


def _srt_milliseconds(frame: int, rate: FrameRate, *, end: bool) -> int:
    milliseconds = Fraction(frame * rate.denominator * 1000, rate.numerator)
    return _ceil(milliseconds) if end else _floor(milliseconds)


def _format_srt_timestamp(value: int) -> str:
    hours, remainder = divmod(value, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


class SrtRenderer:
    @staticmethod
    def render(plan: SubtitlePlan) -> str:
        blocks = []
        for index, cue in enumerate(plan.cues, 1):
            start_ms = _srt_milliseconds(cue.timeline_start_frame, plan.timeline_rate, end=False)
            end_ms = _srt_milliseconds(cue.timeline_end_frame, plan.timeline_rate, end=True)
            if index < len(plan.cues):
                next_start_ms = _srt_milliseconds(
                    plan.cues[index].timeline_start_frame, plan.timeline_rate, end=False
                )
                end_ms = min(end_ms, next_start_ms - 1)
            if end_ms < start_ms:
                raise ValueError("SRT millisecond resolution cannot represent a non-overlapping cue")
            start = _format_srt_timestamp(start_ms)
            end = _format_srt_timestamp(end_ms)
            blocks.append(f"{index}\n{start} --> {end}\n{cue.text}")
        return "\n\n".join(blocks) + ("\n" if blocks else "")
