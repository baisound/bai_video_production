"""Pure TASK-098 A4 review completion, timing, and viewport contracts.

This module does not read media, persist review state, render a waveform, start
playback, or mutate TASK-041 / TASK-006 canonical state.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from types import MappingProxyType
from typing import Any

from .audio_workspace_media_review import (
    AudioMediaReviewIntent,
    AudioMediaSourceBinding,
    ContractState,
    ExternalAudioReviewReceiptBinding,
    ExternalReviewState,
    PlaybackWaveformCapabilityBinding,
    validate_external_review_inclusion,
)
from .serialization import validate_sha256


REQUIRED_SAMPLE_RATE_HZ = 48_000
MAX_DURATION_SAMPLES = REQUIRED_SAMPLE_RATE_HZ * 60 * 60 * 24
MAX_SEGMENT_COUNT = 1_000_000
_COMPLETION_REASON_CODES = frozenset(
    {
        "AUDITION_NOT_COMPLETED",
        "CANONICAL_PERSISTENCE_NOT_VERIFIED",
        "CAPABILITY_MISMATCH",
        "EXTERNAL_REVIEW_NOT_COMPLETED",
        "INCLUSION_NOT_PROVEN",
        "INTENT_MISMATCH",
        "RANGE_MISMATCH",
        "RECEIPT_NOT_BOUND",
        "SOURCE_MISMATCH",
        "WAVEFORM_NOT_AVAILABLE",
    }
)


class ReviewCompletionClassification(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


class TimingUnit(str, Enum):
    MICROSECONDS = "MICROSECONDS"
    MILLISECONDS = "MILLISECONDS"


def _integer(value: Any, name: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} is outside the supported range")
    return value


@dataclass(frozen=True, slots=True)
class ReviewCompletionResult:
    classification: ReviewCompletionClassification
    reason_codes: tuple[str, ...]
    intent_sha256: str
    receipt_sha256: str
    playback_started: bool = False
    waveform_render_started: bool = False
    media_mutation_started: bool = False
    human_decision_authorized: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.classification, ReviewCompletionClassification):
            raise ValueError("classification is invalid")
        if (
            tuple(sorted(set(self.reason_codes))) != self.reason_codes
            or any(code not in _COMPLETION_REASON_CODES for code in self.reason_codes)
        ):
            raise ValueError("reason_codes must be closed, unique, and ordered")
        if (self.classification is ReviewCompletionClassification.COMPLETE) != (
            not self.reason_codes
        ):
            raise ValueError("completion classification and reasons disagree")
        validate_sha256(self.intent_sha256, field_name="intent_sha256")
        validate_sha256(self.receipt_sha256, field_name="receipt_sha256")
        if any(
            value is not False
            for value in (
                self.playback_started,
                self.waveform_render_started,
                self.media_mutation_started,
                self.human_decision_authorized,
            )
        ):
            raise ValueError("completion result cannot claim effects or Human authority")

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification.value,
            "reason_codes": list(self.reason_codes),
            "intent_sha256": self.intent_sha256,
            "receipt_sha256": self.receipt_sha256,
            "playback_started": self.playback_started,
            "waveform_render_started": self.waveform_render_started,
            "media_mutation_started": self.media_mutation_started,
            "human_decision_authorized": self.human_decision_authorized,
        }


def classify_review_completion(
    *,
    receipt: ExternalAudioReviewReceiptBinding,
    intent: AudioMediaReviewIntent,
    source: AudioMediaSourceBinding,
    capability: PlaybackWaveformCapabilityBinding,
) -> ReviewCompletionResult:
    """Classify completed external review separately from exact inclusion."""

    inclusion = validate_external_review_inclusion(
        receipt=receipt,
        intent=intent,
        source=source,
        capability=capability,
    )
    reasons = set(inclusion["reason_codes"])
    if inclusion["classification"] != "ACCEPT_PROVEN_EXTERNAL_REVIEW":
        reasons.add("INCLUSION_NOT_PROVEN")

    receipt_data = receipt.to_dict()
    intent_data = intent.to_dict()
    if receipt_data["contract_state"] != ContractState.BOUND_VERIFIED.value:
        reasons.add("RECEIPT_NOT_BOUND")
    if receipt_data["external_state"] != ExternalReviewState.COMPLETED.value:
        reasons.add("EXTERNAL_REVIEW_NOT_COMPLETED")
    if receipt_data["canonical_persistence_verified"] is not True:
        reasons.add("CANONICAL_PERSISTENCE_NOT_VERIFIED")

    requested = set(intent_data["requested_operations"])
    if "AUDITION" in requested and receipt_data["audition_completed"] is not True:
        reasons.add("AUDITION_NOT_COMPLETED")
    if "WAVEFORM_VIEW" in requested and receipt_data["waveform_available"] is not True:
        reasons.add("WAVEFORM_NOT_AVAILABLE")

    classification = (
        ReviewCompletionClassification.COMPLETE
        if not reasons
        else ReviewCompletionClassification.INCOMPLETE
    )
    return ReviewCompletionResult(
        classification=classification,
        reason_codes=tuple(sorted(reasons)),
        intent_sha256=intent.record_sha256,
        receipt_sha256=receipt.record_sha256,
    )


@dataclass(frozen=True, slots=True)
class ProjectedHalfOpenRange:
    source_unit: TimingUnit
    source_start: int
    source_end_exclusive: int
    sample_rate_hz: int
    sample_start: int
    sample_end_exclusive: int

    def __post_init__(self) -> None:
        if not isinstance(self.source_unit, TimingUnit):
            raise ValueError("source_unit is invalid")
        denominator = 1_000_000 if self.source_unit is TimingUnit.MICROSECONDS else 1_000
        _integer(
            self.source_start,
            "source_start",
            minimum=0,
            maximum=denominator * 60 * 60 * 24,
        )
        _integer(
            self.source_end_exclusive,
            "source_end_exclusive",
            minimum=1,
            maximum=denominator * 60 * 60 * 24,
        )
        if self.source_end_exclusive <= self.source_start:
            raise ValueError("source range must be non-empty and half-open")
        if self.sample_rate_hz != REQUIRED_SAMPLE_RATE_HZ:
            raise ValueError("sample_rate_hz must remain 48000")
        expected_start = self.source_start * REQUIRED_SAMPLE_RATE_HZ // denominator
        expected_end = (
            self.source_end_exclusive * REQUIRED_SAMPLE_RATE_HZ + denominator - 1
        ) // denominator
        if (self.sample_start, self.sample_end_exclusive) != (
            expected_start,
            expected_end,
        ):
            raise ValueError("projected sample range does not match source timing")


def _project_half_open_range(
    *, source_unit: TimingUnit, start: int, end_exclusive: int, denominator: int
) -> ProjectedHalfOpenRange:
    _integer(start, "start", minimum=0, maximum=denominator * 60 * 60 * 24)
    _integer(
        end_exclusive,
        "end_exclusive",
        minimum=1,
        maximum=denominator * 60 * 60 * 24,
    )
    if end_exclusive <= start:
        raise ValueError("source range must be non-empty and half-open")
    start_product = start * REQUIRED_SAMPLE_RATE_HZ
    end_product = end_exclusive * REQUIRED_SAMPLE_RATE_HZ
    sample_start = start_product // denominator
    sample_end = (end_product + denominator - 1) // denominator
    return ProjectedHalfOpenRange(
        source_unit=source_unit,
        source_start=start,
        source_end_exclusive=end_exclusive,
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
        sample_start=sample_start,
        sample_end_exclusive=sample_end,
    )


def project_microseconds_to_samples(
    start_us: int, end_us_exclusive: int
) -> ProjectedHalfOpenRange:
    return _project_half_open_range(
        source_unit=TimingUnit.MICROSECONDS,
        start=start_us,
        end_exclusive=end_us_exclusive,
        denominator=1_000_000,
    )


def project_milliseconds_to_samples(
    start_ms: int, end_ms_exclusive: int
) -> ProjectedHalfOpenRange:
    return _project_half_open_range(
        source_unit=TimingUnit.MILLISECONDS,
        start=start_ms,
        end_exclusive=end_ms_exclusive,
        denominator=1_000,
    )


@dataclass(frozen=True, slots=True)
class ReviewViewport:
    source_duration_samples: int
    waveform_start_sample: int
    waveform_span_samples: int
    segment_count: int
    segment_scroll_index: int
    visible_segment_count: int

    def __post_init__(self) -> None:
        duration = _integer(
            self.source_duration_samples,
            "source_duration_samples",
            minimum=1,
            maximum=MAX_DURATION_SAMPLES,
        )
        span = _integer(
            self.waveform_span_samples,
            "waveform_span_samples",
            minimum=1,
            maximum=duration,
        )
        start = _integer(
            self.waveform_start_sample,
            "waveform_start_sample",
            minimum=0,
            maximum=duration - span,
        )
        segment_count = _integer(
            self.segment_count,
            "segment_count",
            minimum=0,
            maximum=MAX_SEGMENT_COUNT,
        )
        visible = _integer(
            self.visible_segment_count,
            "visible_segment_count",
            minimum=1,
            maximum=MAX_SEGMENT_COUNT,
        )
        _integer(
            self.segment_scroll_index,
            "segment_scroll_index",
            minimum=0,
            maximum=max(0, segment_count - visible),
        )
        del start

    def scroll_waveform(self, delta_samples: int) -> "ReviewViewport":
        delta = _integer(
            delta_samples,
            "delta_samples",
            minimum=-MAX_DURATION_SAMPLES,
            maximum=MAX_DURATION_SAMPLES,
        )
        maximum = self.source_duration_samples - self.waveform_span_samples
        next_start = min(maximum, max(0, self.waveform_start_sample + delta))
        return replace(self, waveform_start_sample=next_start)

    def scroll_segments(self, delta_rows: int) -> "ReviewViewport":
        delta = _integer(
            delta_rows,
            "delta_rows",
            minimum=-MAX_SEGMENT_COUNT,
            maximum=MAX_SEGMENT_COUNT,
        )
        maximum = max(0, self.segment_count - self.visible_segment_count)
        next_index = min(maximum, max(0, self.segment_scroll_index + delta))
        return replace(self, segment_scroll_index=next_index)


EFFECT_SURFACE = MappingProxyType(
    {
        "audio_read": False,
        "playback": False,
        "waveform_render": False,
        "media_mutation": False,
        "subtitle_workspace_mutation": False,
        "review_state_persistence": False,
        "human_decision_authorized": False,
    }
)


__all__ = [
    "EFFECT_SURFACE",
    "ProjectedHalfOpenRange",
    "ReviewCompletionClassification",
    "ReviewCompletionResult",
    "ReviewViewport",
    "TimingUnit",
    "classify_review_completion",
    "project_microseconds_to_samples",
    "project_milliseconds_to_samples",
]
