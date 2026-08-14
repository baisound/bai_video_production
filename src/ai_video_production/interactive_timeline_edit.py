"""TASK-044 P-NLE-2 immutable Timeline edit and snap contracts."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import re
from typing import Any, Iterable

from .errors import ProductError, ProductErrorCategory
from .interactive_timeline import InteractiveTimeline, InteractiveTimelineClip, TimelineTrack
from .serialization import canonical_json_bytes, sha256_bytes

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_SHA = re.compile(r"sha256:[0-9a-f]{64}")


def _identity(value: object, name: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _integer(value: object, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} is invalid")
    return value


class TimelineEditKind(str, Enum):
    TRIM_START = "TRIM_START"
    TRIM_END = "TRIM_END"
    MOVE = "MOVE"
    SET_IN_OUT = "SET_IN_OUT"
    ADD_TRACK = "ADD_TRACK"
    REMOVE_TRACK = "REMOVE_TRACK"


class SnapKind(str, Enum):
    PLAYHEAD = "PLAYHEAD"
    SCENE_BOUNDARY = "SCENE_BOUNDARY"
    CLIP_EDGE = "CLIP_EDGE"
    NARRATION_CUE = "NARRATION_CUE"
    MARKER = "MARKER"
    FRAME_GRID = "FRAME_GRID"


@dataclass(frozen=True, slots=True)
class SnapAnchor:
    anchor_id: str
    frame: int
    kind: SnapKind
    priority: int

    def __post_init__(self) -> None:
        _identity(self.anchor_id, "anchor_id")
        _integer(self.frame, "frame")
        _integer(self.priority, "priority")
        if not isinstance(self.kind, SnapKind):
            raise ValueError("snap kind is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {"anchor_id": self.anchor_id, "frame": self.frame, "kind": self.kind.value, "priority": self.priority}


@dataclass(frozen=True, slots=True)
class SnapDecision:
    desired_frame: int
    effective_frame: int
    anchor: SnapAnchor | None

    def __post_init__(self) -> None:
        _integer(self.desired_frame, "desired_frame")
        _integer(self.effective_frame, "effective_frame")
        if self.anchor is not None and not isinstance(self.anchor, SnapAnchor):
            raise ValueError("snap anchor is invalid")
        if self.anchor is None and self.effective_frame != self.desired_frame:
            raise ValueError("unsnapped decision must retain desired frame")
        if self.anchor is not None and self.effective_frame != self.anchor.frame:
            raise ValueError("snapped decision must use anchor frame")

    def to_dict(self) -> dict[str, Any]:
        return {"desired_frame": self.desired_frame, "effective_frame": self.effective_frame,
                "anchor": None if self.anchor is None else self.anchor.to_dict()}


class TimelineSnapService:
    @staticmethod
    def snap(desired_frame: int, *, tolerance_frames: int,
             anchors: Iterable[SnapAnchor]) -> SnapDecision:
        _integer(desired_frame, "desired_frame")
        _integer(tolerance_frames, "tolerance_frames")
        eligible = [item for item in anchors if abs(item.frame - desired_frame) <= tolerance_frames]
        if not eligible:
            return SnapDecision(desired_frame, desired_frame, None)
        selected = min(
            eligible,
            key=lambda item: (
                abs(item.frame - desired_frame), item.priority, item.frame, item.anchor_id
            ),
        )
        return SnapDecision(desired_frame, selected.frame, selected)


@dataclass(frozen=True, slots=True)
class TimelineEditCommand:
    command_id: str
    kind: TimelineEditKind
    target_clip_id: str | None = None
    target_track_id: str | None = None
    before_start_frame: int | None = None
    before_end_frame: int | None = None
    after_start_frame: int | None = None
    after_end_frame: int | None = None
    in_frame: int | None = None
    out_frame: int | None = None
    track: TimelineTrack | None = None
    snap: SnapDecision | None = None

    def __post_init__(self) -> None:
        _identity(self.command_id, "command_id")
        if not isinstance(self.kind, TimelineEditKind):
            raise ValueError("edit kind is invalid")
        if self.snap is not None and not isinstance(self.snap, SnapDecision):
            raise ValueError("snap decision is invalid")
        if self.kind in {TimelineEditKind.TRIM_START, TimelineEditKind.TRIM_END, TimelineEditKind.MOVE}:
            if self.target_clip_id is None:
                raise ValueError("clip edit requires target_clip_id")
            _identity(self.target_clip_id, "target_clip_id")
            values = (self.before_start_frame, self.before_end_frame, self.after_start_frame, self.after_end_frame)
            if any(value is None for value in values):
                raise ValueError("clip edit requires exact before/after range")
            for name, value in zip(("before_start", "before_end", "after_start", "after_end"), values):
                _integer(value, name)
            if self.before_end_frame <= self.before_start_frame or self.after_end_frame <= self.after_start_frame:
                raise ValueError("clip edit range is invalid")
        elif self.kind is TimelineEditKind.SET_IN_OUT:
            _integer(self.in_frame, "in_frame")
            _integer(self.out_frame, "out_frame", 1)
            if self.out_frame <= self.in_frame:
                raise ValueError("IN/OUT range is invalid")
        elif self.kind is TimelineEditKind.ADD_TRACK:
            if self.track is None:
                raise ValueError("ADD_TRACK requires track")
        elif self.kind is TimelineEditKind.REMOVE_TRACK:
            _identity(self.target_track_id, "target_track_id")
            if self.track is None or self.track.track_id != self.target_track_id:
                raise ValueError("REMOVE_TRACK requires the exact removed track snapshot")

    def to_dict(self) -> dict[str, Any]:
        body = {"command_id": self.command_id, "kind": self.kind.value,
          "target_clip_id": self.target_clip_id, "target_track_id": self.target_track_id,
          "before_start_frame": self.before_start_frame, "before_end_frame": self.before_end_frame,
          "after_start_frame": self.after_start_frame, "after_end_frame": self.after_end_frame,
          "in_frame": self.in_frame, "out_frame": self.out_frame,
          "track": None if self.track is None else self.track.to_dict(),
          "snap": None if self.snap is None else self.snap.to_dict()}
        body["command_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @property
    def command_sha256(self) -> str:
        return self.to_dict()["command_sha256"]

    def inverse(self, *, command_id: str) -> "TimelineEditCommand":
        """Return an explicit compensating command; history is never rewritten."""
        if self.kind in {TimelineEditKind.TRIM_START, TimelineEditKind.TRIM_END, TimelineEditKind.MOVE}:
            return TimelineEditCommand(
                command_id=command_id,
                kind=self.kind,
                target_clip_id=self.target_clip_id,
                before_start_frame=self.after_start_frame,
                before_end_frame=self.after_end_frame,
                after_start_frame=self.before_start_frame,
                after_end_frame=self.before_end_frame,
            )
        if self.kind is TimelineEditKind.ADD_TRACK:
            return TimelineEditCommand(command_id, TimelineEditKind.REMOVE_TRACK,
                                       target_track_id=self.track.track_id)
        if self.kind is TimelineEditKind.REMOVE_TRACK:
            if self.track is None:
                raise ValueError("REMOVE_TRACK compensation requires removed track snapshot")
            return TimelineEditCommand(command_id, TimelineEditKind.ADD_TRACK, track=self.track)
        raise ProductError(
            "ERR_TIMELINE_EDIT_NOT_COMPENSATABLE",
            "This Timeline command is reversible session state, not a durable edit",
            ProductErrorCategory.NOT_SUPPORTED,
        )


@dataclass(frozen=True, slots=True)
class TimelineEditRevision:
    project_id: str
    history_id: str
    revision: int
    base_timeline_sha256: str
    command: TimelineEditCommand
    previous_revision_sha256: str | None = None

    def __post_init__(self) -> None:
        _identity(self.project_id, "project_id")
        _identity(self.history_id, "history_id")
        _integer(self.revision, "revision", 1)
        if not isinstance(self.base_timeline_sha256, str) or not _SHA.fullmatch(self.base_timeline_sha256):
            raise ValueError("base timeline hash is invalid")
        if (self.revision == 1) != (self.previous_revision_sha256 is None):
            raise ValueError("revision chain is invalid")
        if self.previous_revision_sha256 is not None and not _SHA.fullmatch(self.previous_revision_sha256):
            raise ValueError("previous hash is invalid")

    def to_dict(self) -> dict[str, Any]:
        body = {"revision_version": "1.0.0", "task_owner": "TASK-044/P-NLE-2",
          "project_id": self.project_id, "history_id": self.history_id, "revision": self.revision,
          "base_timeline_sha256": self.base_timeline_sha256,
          "previous_revision_sha256": self.previous_revision_sha256,
          "command": self.command.to_dict(), "external_mutation_authorized": False}
        body["revision_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @property
    def revision_sha256(self) -> str: return self.to_dict()["revision_sha256"]


class TimelineEditHistory:
    def __init__(self, project_id: str, history_id: str) -> None:
        self.project_id = _identity(project_id, "project_id")
        self.history_id = _identity(history_id, "history_id")
        self.revisions: list[TimelineEditRevision] = []

    @property
    def current(self) -> TimelineEditRevision | None: return self.revisions[-1] if self.revisions else None

    def append(self, value: TimelineEditRevision) -> None:
        current = self.current
        valid = value.project_id == self.project_id and value.history_id == self.history_id
        valid = valid and ((current is None and value.revision == 1 and value.previous_revision_sha256 is None) or
            (current is not None and value.revision == current.revision+1 and value.previous_revision_sha256 == current.revision_sha256 and value.base_timeline_sha256 == current.base_timeline_sha256))
        if not valid:
            raise ProductError("ERR_TIMELINE_EDIT_HISTORY_FORK", "Edit revision does not append to current history", ProductErrorCategory.DATA_INTEGRITY)
        self.revisions.append(value)


class TimelineEditProjector:
    @staticmethod
    def apply(timeline: InteractiveTimeline, history: TimelineEditHistory) -> tuple[InteractiveTimeline, tuple[int, int] | None]:
        if history.current is not None and history.current.base_timeline_sha256 != timeline.timeline_sha256:
            raise ProductError("ERR_TIMELINE_EDIT_BASE_STALE", "Edit history targets an older Timeline", ProductErrorCategory.STATE)
        clips = {item.clip_id: item for item in timeline.clips}
        tracks = {item.track_id: item for item in timeline.tracks}
        in_out = None
        for revision in history.revisions:
            command = revision.command
            if command.kind in {TimelineEditKind.TRIM_START, TimelineEditKind.TRIM_END, TimelineEditKind.MOVE}:
                clip = clips.get(command.target_clip_id or "")
                if clip is None or (clip.start_frame, clip.end_frame) != (command.before_start_frame, command.before_end_frame):
                    raise ProductError("ERR_TIMELINE_EDIT_TARGET_STALE", "Clip range changed before edit projection", ProductErrorCategory.STATE)
                clips[clip.clip_id] = replace(
                    clip,
                    start_frame=command.after_start_frame,
                    end_frame=command.after_end_frame,
                )
            elif command.kind is TimelineEditKind.SET_IN_OUT:
                in_out = (command.in_frame, command.out_frame)
            elif command.kind is TimelineEditKind.ADD_TRACK:
                if command.track.track_id in tracks:
                    raise ProductError("ERR_TIMELINE_TRACK_EXISTS", "Track already exists", ProductErrorCategory.STATE)
                tracks[command.track.track_id] = command.track
            elif command.kind is TimelineEditKind.REMOVE_TRACK:
                track = tracks.get(command.target_track_id or "")
                if track is None or track.minimum_required or any(
                    clip.track_id == command.target_track_id for clip in clips.values()
                ):
                    raise ProductError(
                        "ERR_TIMELINE_TRACK_REMOVE_BLOCKED",
                        "Required, missing or non-empty track cannot be removed",
                        ProductErrorCategory.STATE,
                    )
                tracks.pop(command.target_track_id)
        projected = InteractiveTimeline(timeline.project_id, timeline.timeline_id, timeline.timeline_rate, timeline.duration_frames,
            tuple(sorted(tracks.values(), key=lambda item: (item.order, item.track_id))), tuple(clips.values()))
        return projected, in_out


__all__ = ["SnapAnchor", "SnapDecision", "SnapKind", "TimelineEditCommand", "TimelineEditHistory",
 "TimelineEditKind", "TimelineEditProjector", "TimelineEditRevision", "TimelineSnapService"]
