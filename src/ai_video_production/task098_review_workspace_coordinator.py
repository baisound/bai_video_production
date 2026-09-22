"""Pure, ephemeral TASK-098 A4 review-workspace coordination.

The coordinator copies only body-free identities and timing ranges.  It never
reads media, persists canonical state, renders a waveform, or starts playback.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import re
from types import MappingProxyType

from .audio_workspace_media_review import (
    AudioMediaReviewIntent,
    AudioMediaReviewPolicyRevision,
    AudioMediaSourceBinding,
    PlaybackWaveformCapabilityBinding,
    classify_review_admission,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .subtitle_workspace import SubtitleWorkspace
from .subtitles import TranscriptManifest
from .task098_review_workspace_contract import (
    MAX_SEGMENT_COUNT,
    REQUIRED_SAMPLE_RATE_HZ,
    ProjectedHalfOpenRange,
    ReviewViewport,
    TimingUnit,
    project_microseconds_to_samples,
    project_milliseconds_to_samples,
)


_ERROR_CODES = frozenset(
    {
        "ADMISSION_NOT_READY",
        "IDENTITY_FORMAT_INVALID",
        "INPUT_TYPE_INVALID",
        "ROW_LIMIT_EXCEEDED",
        "SOURCE_ASSET_MISMATCH",
        "SOURCE_CONTRACT_INVALID",
        "TIMING_OUTSIDE_SOURCE",
        "TRANSCRIPT_DIGEST_MISMATCH",
        "VIEWPORT_INVALID",
        "WORKSPACE_SNAPSHOT_DIGEST_MISMATCH",
    }
)
_IDENTITY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")


def _identity(value: str, name: str) -> None:
    if not isinstance(value, str) or not _IDENTITY_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")


def _bounded_integer(value: int, name: str, *, minimum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} is invalid")


class ReviewWorkspaceOpenError(ValueError):
    """Closed, body-free opening failure."""

    def __init__(self, code: str) -> None:
        if code not in _ERROR_CODES:
            raise ValueError("review workspace error code is not closed")
        self.code = code
        self.reason_codes = (code,)
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class TranscriptTimingRow:
    segment_id: str
    source_start_us: int
    source_end_us_exclusive: int
    projected_range: ProjectedHalfOpenRange

    def __post_init__(self) -> None:
        _identity(self.segment_id, "segment_id")
        _bounded_integer(self.source_start_us, "source_start_us", minimum=0)
        _bounded_integer(
            self.source_end_us_exclusive,
            "source_end_us_exclusive",
            minimum=1,
        )
        if (
            not isinstance(self.projected_range, ProjectedHalfOpenRange)
            or self.projected_range.source_unit is not TimingUnit.MICROSECONDS
            or self.projected_range.source_start != self.source_start_us
            or self.projected_range.source_end_exclusive != self.source_end_us_exclusive
        ):
            raise ValueError("transcript projection is inconsistent")


@dataclass(frozen=True, slots=True)
class SubtitleTimingRow:
    cue_id: str
    source_start_ms: int
    source_end_ms_exclusive: int
    projected_range: ProjectedHalfOpenRange

    def __post_init__(self) -> None:
        _identity(self.cue_id, "cue_id")
        _bounded_integer(self.source_start_ms, "source_start_ms", minimum=0)
        _bounded_integer(
            self.source_end_ms_exclusive,
            "source_end_ms_exclusive",
            minimum=1,
        )
        if (
            not isinstance(self.projected_range, ProjectedHalfOpenRange)
            or self.projected_range.source_unit is not TimingUnit.MILLISECONDS
            or self.projected_range.source_start != self.source_start_ms
            or self.projected_range.source_end_exclusive != self.source_end_ms_exclusive
        ):
            raise ValueError("subtitle projection is inconsistent")


@dataclass(frozen=True, slots=True)
class ReviewWorkspaceViewModel:
    source_binding_sha256: str
    source_asset_id: str
    source_candidate_id: str
    intent_sha256: str
    intent_id: str
    transcript_manifest_sha256: str
    workspace_id: str
    workspace_revision: int
    workspace_snapshot_sha256: str
    transcript_rows: tuple[TranscriptTimingRow, ...]
    subtitle_rows: tuple[SubtitleTimingRow, ...]
    viewport: ReviewViewport
    workspace_transcript_lineage_confirmed: bool = False

    def __post_init__(self) -> None:
        if self.workspace_transcript_lineage_confirmed is not False:
            raise ValueError("workspace transcript lineage cannot be claimed")
        for name, value in (
            ("source_binding_sha256", self.source_binding_sha256),
            ("intent_sha256", self.intent_sha256),
            ("transcript_manifest_sha256", self.transcript_manifest_sha256),
            ("workspace_snapshot_sha256", self.workspace_snapshot_sha256),
        ):
            validate_sha256(value, field_name=name)
        for name, value in (
            ("source_asset_id", self.source_asset_id),
            ("source_candidate_id", self.source_candidate_id),
            ("intent_id", self.intent_id),
            ("workspace_id", self.workspace_id),
        ):
            _identity(value, name)
        _bounded_integer(self.workspace_revision, "workspace_revision", minimum=0)
        if not isinstance(self.transcript_rows, tuple) or any(
            not isinstance(row, TranscriptTimingRow) for row in self.transcript_rows
        ):
            raise ValueError("transcript_rows must contain body-free timing rows")
        if not isinstance(self.subtitle_rows, tuple) or any(
            not isinstance(row, SubtitleTimingRow) for row in self.subtitle_rows
        ):
            raise ValueError("subtitle_rows must contain body-free timing rows")
        if not isinstance(self.viewport, ReviewViewport):
            raise ValueError("viewport is invalid")
        if self.viewport.segment_count != max(
            len(self.transcript_rows), len(self.subtitle_rows)
        ):
            raise ValueError("viewport segment_count is inconsistent")
        if any(
            row.projected_range.sample_end_exclusive
            > self.viewport.source_duration_samples
            for row in (*self.transcript_rows, *self.subtitle_rows)
        ):
            raise ValueError("timing rows exceed source duration")

    def scroll_waveform(self, delta_samples: int) -> "ReviewWorkspaceViewModel":
        return replace(self, viewport=self.viewport.scroll_waveform(delta_samples))

    def scroll_segments(self, delta_rows: int) -> "ReviewWorkspaceViewModel":
        return replace(self, viewport=self.viewport.scroll_segments(delta_rows))


EFFECT_SURFACE = MappingProxyType(
    {
        "audio_read": False,
        "filesystem_read": False,
        "human_decision_authorized": False,
        "media_mutation": False,
        "network_call": False,
        "playback": False,
        "review_state_persistence": False,
        "subtitle_workspace_mutation": False,
        "waveform_render": False,
    }
)


def _fail(code: str) -> None:
    raise ReviewWorkspaceOpenError(code)


def open_review_workspace(
    *,
    policy: AudioMediaReviewPolicyRevision,
    source: AudioMediaSourceBinding,
    capability: PlaybackWaveformCapabilityBinding,
    intent: AudioMediaReviewIntent,
    transcript: TranscriptManifest,
    expected_transcript_sha256: str,
    workspace: SubtitleWorkspace,
    expected_workspace_snapshot_sha256: str,
    evaluated_at: str,
    visible_segment_count: int = 20,
) -> ReviewWorkspaceViewModel:
    """Open an all-or-nothing, exact-identity, body-free review ViewModel."""

    expected_types = (
        (policy, AudioMediaReviewPolicyRevision),
        (source, AudioMediaSourceBinding),
        (capability, PlaybackWaveformCapabilityBinding),
        (intent, AudioMediaReviewIntent),
        (transcript, TranscriptManifest),
        (workspace, SubtitleWorkspace),
    )
    if any(not isinstance(value, expected) for value, expected in expected_types):
        _fail("INPUT_TYPE_INVALID")

    try:
        validate_sha256(
            expected_transcript_sha256,
            field_name="expected_transcript_sha256",
        )
        validate_sha256(
            expected_workspace_snapshot_sha256,
            field_name="expected_workspace_snapshot_sha256",
        )
    except (TypeError, ValueError):
        _fail("IDENTITY_FORMAT_INVALID")

    if len(transcript.segments) > MAX_SEGMENT_COUNT or len(workspace.cues) > MAX_SEGMENT_COUNT:
        _fail("ROW_LIMIT_EXCEEDED")

    try:
        admission = classify_review_admission(
            policy=policy,
            source=source,
            capability=capability,
            intent=intent,
            evaluated_at=evaluated_at,
        )
    except (TypeError, ValueError):
        _fail("ADMISSION_NOT_READY")
    if admission["decision"] != "READY_FOR_HUMAN_REVIEW":
        _fail("ADMISSION_NOT_READY")

    source_data = source.to_dict()
    intent_data = intent.to_dict()
    if (
        source_data["contract_state"] != "BOUND_VERIFIED"
        or source_data["rights_state"] != "PASS"
        or source_data["sample_rate_hz"] != REQUIRED_SAMPLE_RATE_HZ
        or not isinstance(source_data["duration_samples"], int)
        or isinstance(source_data["duration_samples"], bool)
        or source_data["duration_samples"] <= 0
        or not source_data["asset_id"]
        or not source_data["candidate_id"]
    ):
        _fail("SOURCE_CONTRACT_INVALID")

    if transcript.source_asset_id != source_data["asset_id"]:
        _fail("SOURCE_ASSET_MISMATCH")

    transcript_data = transcript.to_dict()
    if transcript_data["manifest_sha256"] != expected_transcript_sha256:
        _fail("TRANSCRIPT_DIGEST_MISMATCH")

    workspace_snapshot_sha256 = sha256_bytes(canonical_json_bytes(workspace.to_dict()))
    if workspace_snapshot_sha256 != expected_workspace_snapshot_sha256:
        _fail("WORKSPACE_SNAPSHOT_DIGEST_MISMATCH")

    duration_samples = source_data["duration_samples"]
    transcript_rows: list[TranscriptTimingRow] = []
    subtitle_rows: list[SubtitleTimingRow] = []
    try:
        for segment in transcript.segments:
            projected = project_microseconds_to_samples(segment.start_us, segment.end_us)
            if projected.sample_end_exclusive > duration_samples:
                _fail("TIMING_OUTSIDE_SOURCE")
            transcript_rows.append(
                TranscriptTimingRow(
                    segment_id=segment.segment_id,
                    source_start_us=segment.start_us,
                    source_end_us_exclusive=segment.end_us,
                    projected_range=projected,
                )
            )
        for cue in workspace.cues:
            projected = project_milliseconds_to_samples(cue.start_ms, cue.end_ms)
            if projected.sample_end_exclusive > duration_samples:
                _fail("TIMING_OUTSIDE_SOURCE")
            subtitle_rows.append(
                SubtitleTimingRow(
                    cue_id=cue.cue_id,
                    source_start_ms=cue.start_ms,
                    source_end_ms_exclusive=cue.end_ms,
                    projected_range=projected,
                )
            )
    except ReviewWorkspaceOpenError:
        raise
    except (TypeError, ValueError):
        _fail("TIMING_OUTSIDE_SOURCE")

    try:
        viewport = ReviewViewport(
            source_duration_samples=duration_samples,
            waveform_start_sample=intent_data["range_start_sample"],
            waveform_span_samples=(
                intent_data["range_end_sample"] - intent_data["range_start_sample"]
            ),
            segment_count=max(len(transcript_rows), len(subtitle_rows)),
            segment_scroll_index=0,
            visible_segment_count=visible_segment_count,
        )
    except (TypeError, ValueError):
        _fail("VIEWPORT_INVALID")

    return ReviewWorkspaceViewModel(
        source_binding_sha256=source.record_sha256,
        source_asset_id=source_data["asset_id"],
        source_candidate_id=source_data["candidate_id"],
        intent_sha256=intent.record_sha256,
        intent_id=intent_data["intent_id"],
        transcript_manifest_sha256=expected_transcript_sha256,
        workspace_id=workspace.workspace_id,
        workspace_revision=workspace.revision,
        workspace_snapshot_sha256=expected_workspace_snapshot_sha256,
        transcript_rows=tuple(transcript_rows),
        subtitle_rows=tuple(subtitle_rows),
        viewport=viewport,
    )


__all__ = [
    "EFFECT_SURFACE",
    "ReviewWorkspaceOpenError",
    "ReviewWorkspaceViewModel",
    "SubtitleTimingRow",
    "TranscriptTimingRow",
    "open_review_workspace",
]
