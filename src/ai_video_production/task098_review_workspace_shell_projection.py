"""Body-free public Shell projection for TASK-098 A4 review workspaces."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from .task098_review_workspace_contract import MAX_SEGMENT_COUNT, REQUIRED_SAMPLE_RATE_HZ
from .task098_review_workspace_coordinator import (
    ReviewWorkspaceViewModel,
    SubtitleTimingRow,
    TranscriptTimingRow,
)


_ROW_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def _integer(value: int, name: str, *, minimum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} is invalid")


@dataclass(frozen=True, slots=True)
class ShellTranscriptTimingRow:
    segment_id: str
    source_start_us: int
    source_end_us_exclusive: int
    sample_start: int
    sample_end_exclusive: int

    @classmethod
    def from_private(cls, row: TranscriptTimingRow) -> "ShellTranscriptTimingRow":
        if type(row) is not TranscriptTimingRow:
            raise ValueError("transcript timing row is invalid")
        return cls(
            row.segment_id,
            row.source_start_us,
            row.source_end_us_exclusive,
            row.projected_range.sample_start,
            row.projected_range.sample_end_exclusive,
        )

    def __post_init__(self) -> None:
        if not isinstance(self.segment_id, str) or not _ROW_ID_RE.fullmatch(self.segment_id):
            raise ValueError("segment_id is invalid")
        for name, value, minimum in (
            ("source_start_us", self.source_start_us, 0),
            ("source_end_us_exclusive", self.source_end_us_exclusive, 1),
            ("sample_start", self.sample_start, 0),
            ("sample_end_exclusive", self.sample_end_exclusive, 1),
        ):
            _integer(value, name, minimum=minimum)
        if self.source_end_us_exclusive <= self.source_start_us:
            raise ValueError("transcript timing range is invalid")
        if self.sample_end_exclusive <= self.sample_start:
            raise ValueError("transcript sample range is invalid")
        expected_start = self.source_start_us * REQUIRED_SAMPLE_RATE_HZ // 1_000_000
        expected_end = (
            self.source_end_us_exclusive * REQUIRED_SAMPLE_RATE_HZ + 999_999
        ) // 1_000_000
        if (self.sample_start, self.sample_end_exclusive) != (
            expected_start,
            expected_end,
        ):
            raise ValueError("transcript sample projection is inconsistent")

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "source_range_us": {
                "start": self.source_start_us,
                "end_exclusive": self.source_end_us_exclusive,
            },
            "sample_range": {
                "start": self.sample_start,
                "end_exclusive": self.sample_end_exclusive,
            },
        }


@dataclass(frozen=True, slots=True)
class ShellSubtitleTimingRow:
    cue_id: str
    source_start_ms: int
    source_end_ms_exclusive: int
    sample_start: int
    sample_end_exclusive: int

    @classmethod
    def from_private(cls, row: SubtitleTimingRow) -> "ShellSubtitleTimingRow":
        if type(row) is not SubtitleTimingRow:
            raise ValueError("subtitle timing row is invalid")
        return cls(
            row.cue_id,
            row.source_start_ms,
            row.source_end_ms_exclusive,
            row.projected_range.sample_start,
            row.projected_range.sample_end_exclusive,
        )

    def __post_init__(self) -> None:
        if not isinstance(self.cue_id, str) or not _ROW_ID_RE.fullmatch(self.cue_id):
            raise ValueError("cue_id is invalid")
        for name, value, minimum in (
            ("source_start_ms", self.source_start_ms, 0),
            ("source_end_ms_exclusive", self.source_end_ms_exclusive, 1),
            ("sample_start", self.sample_start, 0),
            ("sample_end_exclusive", self.sample_end_exclusive, 1),
        ):
            _integer(value, name, minimum=minimum)
        if self.source_end_ms_exclusive <= self.source_start_ms:
            raise ValueError("subtitle timing range is invalid")
        if self.sample_end_exclusive <= self.sample_start:
            raise ValueError("subtitle sample range is invalid")
        expected_start = self.source_start_ms * REQUIRED_SAMPLE_RATE_HZ // 1_000
        expected_end = (
            self.source_end_ms_exclusive * REQUIRED_SAMPLE_RATE_HZ + 999
        ) // 1_000
        if (self.sample_start, self.sample_end_exclusive) != (
            expected_start,
            expected_end,
        ):
            raise ValueError("subtitle sample projection is inconsistent")

    def to_dict(self) -> dict[str, Any]:
        return {
            "cue_id": self.cue_id,
            "source_range_ms": {
                "start": self.source_start_ms,
                "end_exclusive": self.source_end_ms_exclusive,
            },
            "sample_range": {
                "start": self.sample_start,
                "end_exclusive": self.sample_end_exclusive,
            },
        }


@dataclass(frozen=True, slots=True)
class ShellReviewViewport:
    waveform_start_sample: int
    waveform_span_samples: int
    segment_count: int
    segment_scroll_index: int
    visible_segment_count: int

    def __post_init__(self) -> None:
        for name, value, minimum in (
            ("waveform_start_sample", self.waveform_start_sample, 0),
            ("waveform_span_samples", self.waveform_span_samples, 1),
            ("segment_count", self.segment_count, 0),
            ("segment_scroll_index", self.segment_scroll_index, 0),
            ("visible_segment_count", self.visible_segment_count, 1),
        ):
            _integer(value, name, minimum=minimum)
        maximum = max(0, self.segment_count - self.visible_segment_count)
        if self.segment_scroll_index > maximum:
            raise ValueError("segment_scroll_index is invalid")

    def to_dict(self) -> dict[str, int]:
        return {
            "waveform_start_sample": self.waveform_start_sample,
            "waveform_span_samples": self.waveform_span_samples,
            "segment_count": self.segment_count,
            "segment_scroll_index": self.segment_scroll_index,
            "visible_segment_count": self.visible_segment_count,
        }


@dataclass(frozen=True, slots=True)
class ReviewWorkspaceShellProjection:
    sample_rate_hz: int
    source_duration_samples: int
    workspace_revision: int
    transcript_rows: tuple[ShellTranscriptTimingRow, ...]
    subtitle_rows: tuple[ShellSubtitleTimingRow, ...]
    viewport: ShellReviewViewport
    workspace_transcript_lineage_confirmed: bool = False

    def __post_init__(self) -> None:
        if self.sample_rate_hz != REQUIRED_SAMPLE_RATE_HZ:
            raise ValueError("sample_rate_hz must remain 48000")
        _integer(
            self.source_duration_samples,
            "source_duration_samples",
            minimum=1,
        )
        _integer(self.workspace_revision, "workspace_revision", minimum=0)
        if self.workspace_transcript_lineage_confirmed is not False:
            raise ValueError("workspace transcript lineage cannot be claimed")
        if not isinstance(self.transcript_rows, tuple) or any(
            type(row) is not ShellTranscriptTimingRow for row in self.transcript_rows
        ):
            raise ValueError("transcript_rows are invalid")
        if not isinstance(self.subtitle_rows, tuple) or any(
            type(row) is not ShellSubtitleTimingRow for row in self.subtitle_rows
        ):
            raise ValueError("subtitle_rows are invalid")
        if (
            len(self.transcript_rows) > MAX_SEGMENT_COUNT
            or len(self.subtitle_rows) > MAX_SEGMENT_COUNT
        ):
            raise ValueError("timing row count exceeds the supported limit")
        for rows, id_name, start_name, end_name in (
            (
                self.transcript_rows,
                "segment_id",
                "source_start_us",
                "source_end_us_exclusive",
            ),
            (
                self.subtitle_rows,
                "cue_id",
                "source_start_ms",
                "source_end_ms_exclusive",
            ),
        ):
            seen: set[str] = set()
            previous_end = 0
            for row in rows:
                row_id = getattr(row, id_name)
                start = getattr(row, start_name)
                end = getattr(row, end_name)
                if row_id in seen or start < previous_end:
                    raise ValueError("timing rows are duplicated or out of order")
                seen.add(row_id)
                previous_end = end
        if type(self.viewport) is not ShellReviewViewport:
            raise ValueError("viewport is invalid")
        if self.viewport.segment_count != max(
            len(self.transcript_rows), len(self.subtitle_rows)
        ):
            raise ValueError("viewport segment_count is inconsistent")
        if (
            self.viewport.waveform_start_sample + self.viewport.waveform_span_samples
            > self.source_duration_samples
        ):
            raise ValueError("waveform viewport exceeds source duration")
        if any(
            row.sample_end_exclusive > self.source_duration_samples
            for row in (*self.transcript_rows, *self.subtitle_rows)
        ):
            raise ValueError("timing row exceeds source duration")

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_version": "1.0.0",
            "task_owner": "TASK-098",
            "available": True,
            "sample_rate_hz": self.sample_rate_hz,
            "source_duration_samples": self.source_duration_samples,
            "workspace_revision": self.workspace_revision,
            "workspace_transcript_lineage_confirmed": False,
            "transcript_timing_rows": [row.to_dict() for row in self.transcript_rows],
            "subtitle_timing_rows": [row.to_dict() for row in self.subtitle_rows],
            "viewport": self.viewport.to_dict(),
            "capabilities": {
                "local_viewport_scroll": True,
                "audition": False,
                "waveform_render": False,
                "subtitle_mutation": False,
                "review_completion": False,
                "review_state_persistence": False,
                "human_decision_authorized": False,
            },
        }


def project_review_workspace(
    value: ReviewWorkspaceViewModel,
) -> ReviewWorkspaceShellProjection:
    if type(value) is not ReviewWorkspaceViewModel:
        raise ValueError("review workspace ViewModel is invalid")
    private_viewport = value.viewport
    return ReviewWorkspaceShellProjection(
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
        source_duration_samples=private_viewport.source_duration_samples,
        workspace_revision=value.workspace_revision,
        transcript_rows=tuple(
            ShellTranscriptTimingRow.from_private(row) for row in value.transcript_rows
        ),
        subtitle_rows=tuple(
            ShellSubtitleTimingRow.from_private(row) for row in value.subtitle_rows
        ),
        viewport=ShellReviewViewport(
            waveform_start_sample=private_viewport.waveform_start_sample,
            waveform_span_samples=private_viewport.waveform_span_samples,
            segment_count=private_viewport.segment_count,
            segment_scroll_index=private_viewport.segment_scroll_index,
            visible_segment_count=private_viewport.visible_segment_count,
        ),
    )


__all__ = [
    "ReviewWorkspaceShellProjection",
    "ShellReviewViewport",
    "ShellSubtitleTimingRow",
    "ShellTranscriptTimingRow",
    "project_review_workspace",
]
