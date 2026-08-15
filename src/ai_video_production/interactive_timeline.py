"""TASK-044 P-NLE-1 frame-authoritative interactive Timeline semantics."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
import re
from typing import Any, Iterable

from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes
from .timebase import FrameRate

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")


def _id(value: object, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _frame(value: object, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} is invalid")
    return value


class TimelineTrackRole(str, Enum):
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    SUBTITLE = "SUBTITLE"
    OVERLAY = "OVERLAY"


class TimelineMediaKind(str, Enum):
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    TEXT = "TEXT"
    CONTROL = "CONTROL"


class TimelineFocusKind(str, Enum):
    NONE = "NONE"
    CLIP = "CLIP"
    TRACK = "TRACK"
    RULER = "RULER"
    PLAYHEAD = "PLAYHEAD"


class TimelineFitMode(str, Enum):
    MANUAL = "MANUAL"
    ENTIRE = "ENTIRE"
    SELECTION = "SELECTION"


@dataclass(frozen=True, slots=True)
class TimelineTrack:
    track_id: str
    order: int
    role: TimelineTrackRole
    media_kind: TimelineMediaKind
    label: str
    minimum_required: bool = False

    def __post_init__(self) -> None:
        _id(self.track_id, "track_id")
        _frame(self.order, "order")
        if not isinstance(self.role, TimelineTrackRole) or not isinstance(self.media_kind, TimelineMediaKind):
            raise ValueError("track role/media_kind is invalid")
        if not isinstance(self.label, str) or not self.label.strip() or len(self.label) > 120:
            raise ValueError("track label is invalid")
        if not isinstance(self.minimum_required, bool):
            raise ValueError("minimum_required must be boolean")

    def to_dict(self) -> dict[str, Any]:
        return {"track_id": self.track_id, "order": self.order, "role": self.role.value,
                "media_kind": self.media_kind.value, "label": self.label,
                "minimum_required": self.minimum_required}


@dataclass(frozen=True, slots=True)
class InteractiveTimelineClip:
    clip_id: str
    track_id: str
    start_frame: int
    end_frame: int
    source_owner: str
    source_ref: str
    source_sha256: str
    label: str
    state: str
    review_candidate_id: str | None = None

    def __post_init__(self) -> None:
        _id(self.clip_id, "clip_id")
        _id(self.track_id, "track_id")
        _frame(self.start_frame, "start_frame")
        _frame(self.end_frame, "end_frame", minimum=1)
        if self.end_frame <= self.start_frame:
            raise ValueError("clip range must be positive and end-exclusive")
        _id(self.source_owner, "source_owner")
        _id(self.source_ref, "source_ref")
        if not isinstance(self.source_sha256, str) or not _SHA_RE.fullmatch(self.source_sha256):
            raise ValueError("source_sha256 is invalid")
        if not isinstance(self.label, str) or not self.label.strip() or len(self.label) > 240:
            raise ValueError("clip label is invalid")
        _id(self.state, "state")
        if self.review_candidate_id is not None:
            _id(self.review_candidate_id, "review_candidate_id")

    def to_dict(self) -> dict[str, Any]:
        return {"clip_id": self.clip_id, "track_id": self.track_id,
                "start_frame": self.start_frame, "end_frame": self.end_frame,
                "source_owner": self.source_owner, "source_ref": self.source_ref,
                "source_sha256": self.source_sha256, "label": self.label,
                "state": self.state, "review_candidate_id": self.review_candidate_id}


@dataclass(frozen=True, slots=True)
class TimelineViewport:
    visible_start_frame: int
    visible_end_frame: int
    pixels_per_second_numerator: int
    pixels_per_second_denominator: int
    first_track_index: int = 0
    visible_track_count: int = 8
    fit_mode: TimelineFitMode = TimelineFitMode.MANUAL

    def __post_init__(self) -> None:
        _frame(self.visible_start_frame, "visible_start_frame")
        _frame(self.visible_end_frame, "visible_end_frame", minimum=1)
        if self.visible_end_frame <= self.visible_start_frame:
            raise ValueError("visible frame range is invalid")
        _frame(self.pixels_per_second_numerator, "pixels_per_second_numerator", minimum=1)
        _frame(self.pixels_per_second_denominator, "pixels_per_second_denominator", minimum=1)
        _frame(self.first_track_index, "first_track_index")
        _frame(self.visible_track_count, "visible_track_count", minimum=1)
        if not isinstance(self.fit_mode, TimelineFitMode):
            raise ValueError("fit_mode is invalid")

    @property
    def pixels_per_second(self) -> Fraction:
        return Fraction(self.pixels_per_second_numerator, self.pixels_per_second_denominator)

    def frame_to_pixel(self, frame: int, rate: FrameRate) -> Fraction:
        _frame(frame, "frame")
        return Fraction(frame - self.visible_start_frame, 1) * rate.denominator * self.pixels_per_second / rate.numerator

    @classmethod
    def fit(cls, *, start_frame: int, end_frame: int, viewport_width_px: int,
            rate: FrameRate, mode: TimelineFitMode, first_track_index: int = 0,
            visible_track_count: int = 8) -> "TimelineViewport":
        _frame(viewport_width_px, "viewport_width_px", minimum=1)
        duration = _frame(end_frame, "end_frame", minimum=1) - _frame(start_frame, "start_frame")
        if duration < 1:
            raise ValueError("fit range is invalid")
        scale = Fraction(viewport_width_px * rate.numerator, duration * rate.denominator)
        return cls(start_frame, end_frame, scale.numerator, scale.denominator,
                   first_track_index, visible_track_count, mode)

    def to_dict(self) -> dict[str, Any]:
        return {"visible_start_frame": self.visible_start_frame,
                "visible_end_frame": self.visible_end_frame,
                "pixels_per_second": {"numerator": self.pixels_per_second_numerator,
                                      "denominator": self.pixels_per_second_denominator},
                "first_track_index": self.first_track_index,
                "visible_track_count": self.visible_track_count,
                "fit_mode": self.fit_mode.value}


@dataclass(frozen=True, slots=True)
class TimelineInteractionState:
    project_id: str
    timeline_sha256: str
    playhead_frame: int
    selected_clip_ids: tuple[str, ...] = ()
    focused_kind: TimelineFocusKind = TimelineFocusKind.NONE
    focused_id: str | None = None
    review_candidate_id: str | None = None
    in_frame: int | None = None
    out_frame: int | None = None

    def __post_init__(self) -> None:
        _id(self.project_id, "project_id")
        if not isinstance(self.timeline_sha256, str) or not _SHA_RE.fullmatch(self.timeline_sha256):
            raise ValueError("timeline_sha256 is invalid")
        _frame(self.playhead_frame, "playhead_frame")
        if tuple(dict.fromkeys(self.selected_clip_ids)) != self.selected_clip_ids:
            raise ValueError("selected clips must be unique")
        for value in self.selected_clip_ids:
            _id(value, "selected_clip_id")
        if not isinstance(self.focused_kind, TimelineFocusKind):
            raise ValueError("focused_kind is invalid")
        if (self.focused_kind is TimelineFocusKind.NONE) != (self.focused_id is None):
            raise ValueError("focus kind/id are inconsistent")
        if self.focused_id is not None:
            _id(self.focused_id, "focused_id")
        if self.review_candidate_id is not None:
            _id(self.review_candidate_id, "review_candidate_id")
        if (self.in_frame is None) != (self.out_frame is None):
            raise ValueError("IN/OUT must be both set or both absent")
        if self.in_frame is not None:
            _frame(self.in_frame, "in_frame")
            _frame(self.out_frame, "out_frame", minimum=1)
            if self.out_frame <= self.in_frame:
                raise ValueError("IN/OUT range is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {"project_id": self.project_id, "timeline_sha256": self.timeline_sha256,
                "playhead_frame": self.playhead_frame,
                "selected_clip_ids": list(self.selected_clip_ids),
                "focused_kind": self.focused_kind.value, "focused_id": self.focused_id,
                "review_candidate_id": self.review_candidate_id,
                "in_frame": self.in_frame, "out_frame": self.out_frame,
                "product_semantic_mutation_started": False}


class TimelineInteractionReducer:
    @staticmethod
    def select_clip(state: TimelineInteractionState, clip: InteractiveTimelineClip,
                    *, extend: bool = False) -> TimelineInteractionState:
        if extend:
            selected = state.selected_clip_ids if clip.clip_id in state.selected_clip_ids else state.selected_clip_ids + (clip.clip_id,)
        else:
            selected = (clip.clip_id,)
        return replace(state, selected_clip_ids=selected, focused_kind=TimelineFocusKind.CLIP,
                       focused_id=clip.clip_id, review_candidate_id=clip.review_candidate_id)

    @staticmethod
    def seek(state: TimelineInteractionState, *, frame: int, timeline_duration_frames: int,
             focus: TimelineFocusKind = TimelineFocusKind.PLAYHEAD) -> TimelineInteractionState:
        _frame(frame, "frame")
        _frame(timeline_duration_frames, "timeline_duration_frames", minimum=1)
        if focus not in {TimelineFocusKind.RULER, TimelineFocusKind.PLAYHEAD}:
            raise ValueError("seek focus must be RULER or PLAYHEAD")
        if frame >= timeline_duration_frames:
            raise ProductError("ERR_TIMELINE_SEEK_RANGE", "Seek frame is outside the Timeline", ProductErrorCategory.VALIDATION)
        return replace(state, playhead_frame=frame, focused_kind=focus, focused_id=focus.value.lower())

    @staticmethod
    def set_in_out(state: TimelineInteractionState, *, in_frame: int | None,
                   out_frame: int | None) -> TimelineInteractionState:
        return replace(state, in_frame=in_frame, out_frame=out_frame)


@dataclass(frozen=True, slots=True)
class InteractiveTimeline:
    project_id: str
    timeline_id: str
    timeline_rate: FrameRate
    duration_frames: int
    tracks: tuple[TimelineTrack, ...]
    clips: tuple[InteractiveTimelineClip, ...]

    def __post_init__(self) -> None:
        _id(self.project_id, "project_id")
        _id(self.timeline_id, "timeline_id")
        _frame(self.duration_frames, "duration_frames", minimum=1)
        if not isinstance(self.timeline_rate, FrameRate):
            raise ValueError("timeline_rate is invalid")
        track_ids = [item.track_id for item in self.tracks]
        clip_ids = [item.clip_id for item in self.clips]
        if len(track_ids) != len(set(track_ids)) or len(clip_ids) != len(set(clip_ids)):
            raise ValueError("track/clip identities must be unique")
        if tuple(sorted(self.tracks, key=lambda item: (item.order, item.track_id))) != self.tracks:
            raise ValueError("tracks must be canonically ordered")
        known = set(track_ids)
        for clip in self.clips:
            if clip.track_id not in known or clip.end_frame > self.duration_frames:
                raise ValueError("clip track/range is outside the Timeline")

    def to_dict(self) -> dict[str, Any]:
        body = {"timeline_version": "1.0.0", "task_owner": "TASK-044/P-NLE-1",
                "project_id": self.project_id, "timeline_id": self.timeline_id,
                "timeline_rate": {"numerator": self.timeline_rate.numerator,
                                  "denominator": self.timeline_rate.denominator},
                "duration_frames": self.duration_frames,
                "tracks": [item.to_dict() for item in self.tracks],
                "clips": [item.to_dict() for item in sorted(self.clips, key=lambda value: (value.start_frame, value.track_id, value.clip_id))],
                "product_semantic_mutation_authorized": False,
                "external_mutation_authorized": False}
        body["timeline_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @property
    def timeline_sha256(self) -> str:
        return self.to_dict()["timeline_sha256"]


@dataclass(frozen=True, slots=True)
class TimelineWindowProjection:
    viewport: TimelineViewport
    tracks: tuple[TimelineTrack, ...]
    clips: tuple[InteractiveTimelineClip, ...]
    total_intersecting_clips: int
    clip_offset: int
    next_clip_offset: int | None

    def to_dict(self, *, rate: FrameRate) -> dict[str, Any]:
        media_by_track = {item.track_id: item.media_kind.value for item in self.tracks}
        return {"projection_version": "1.0.0", "task_owner": "TASK-044/P-NLE-1",
                "viewport": self.viewport.to_dict(),
                "tracks": [item.to_dict() for item in self.tracks],
                "clips": [{**item.to_dict(), "media_kind": media_by_track[item.track_id],
                           "left_px": float(self.viewport.frame_to_pixel(item.start_frame, rate)),
                           "width_px": float(self.viewport.frame_to_pixel(item.end_frame, rate) - self.viewport.frame_to_pixel(item.start_frame, rate))}
                          for item in self.clips],
                "total_intersecting_clips": self.total_intersecting_clips,
                "clip_offset": self.clip_offset, "next_clip_offset": self.next_clip_offset,
                "bounded_projection": True}


class TimelineWindowProjector:
    @staticmethod
    def project(timeline: InteractiveTimeline, viewport: TimelineViewport, *,
                overscan_frames: int = 0, clip_offset: int = 0,
                max_clips: int = 500) -> TimelineWindowProjection:
        _frame(overscan_frames, "overscan_frames")
        _frame(clip_offset, "clip_offset")
        _frame(max_clips, "max_clips", minimum=1)
        if max_clips > 2000:
            raise ValueError("max_clips exceeds bounded projection limit")
        first = viewport.first_track_index
        tracks = timeline.tracks[first:first + viewport.visible_track_count]
        track_ids = {item.track_id for item in tracks}
        start = max(0, viewport.visible_start_frame - overscan_frames)
        end = min(timeline.duration_frames, viewport.visible_end_frame + overscan_frames)
        intersecting = sorted((clip for clip in timeline.clips
            if clip.track_id in track_ids and clip.end_frame > start and clip.start_frame < end),
            key=lambda value: (value.start_frame, value.track_id, value.clip_id))
        page = tuple(intersecting[clip_offset:clip_offset + max_clips])
        next_offset = clip_offset + len(page) if clip_offset + len(page) < len(intersecting) else None
        return TimelineWindowProjection(viewport, tracks, page, len(intersecting), clip_offset, next_offset)


__all__ = ["InteractiveTimeline", "InteractiveTimelineClip", "TimelineFitMode",
 "TimelineFocusKind", "TimelineInteractionReducer", "TimelineInteractionState",
 "TimelineMediaKind", "TimelineTrack", "TimelineTrackRole", "TimelineViewport",
 "TimelineWindowProjection", "TimelineWindowProjector"]
