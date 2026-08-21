"""TASK-044 P-NLE-2 immutable Timeline edit and snap contracts."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import re
from typing import Any, Iterable

from .errors import ProductError, ProductErrorCategory
from .interactive_timeline import (
    InteractiveTimeline, InteractiveTimelineClip, TimelineTrack,
    timeline_track_category,
)
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
    INSERT_CLIP = "INSERT_CLIP"
    REMOVE_CLIP = "REMOVE_CLIP"
    REPLACE_CLIP = "REPLACE_CLIP"


class SnapKind(str, Enum):
    PLAYHEAD = "PLAYHEAD"
    SCENE_BOUNDARY = "SCENE_BOUNDARY"
    CLIP_EDGE = "CLIP_EDGE"
    NARRATION_CUE = "NARRATION_CUE"
    MARKER = "MARKER"
    FRAME_GRID = "FRAME_GRID"


@dataclass(frozen=True, slots=True)
class TimelineSourceBinding:
    """Body-free, immutable source proof for a v1.1 placed Timeline clip."""

    project_id: str
    production_snapshot_sha256: str
    scene_id: str
    slot_id: str
    candidate_id: str
    asset_id: str
    asset_sha256: str
    product_job_id: str
    generation_execution_id: str
    queue_entry_id: str
    publication_authorized: bool = False

    def __post_init__(self) -> None:
        for name in (
            "project_id", "scene_id", "slot_id", "candidate_id", "asset_id",
            "product_job_id", "generation_execution_id", "queue_entry_id",
        ):
            _identity(getattr(self, name), name)
        for name in ("production_snapshot_sha256", "asset_sha256"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _SHA.fullmatch(value):
                raise ValueError(f"{name} is invalid")
        if self.publication_authorized is not False:
            raise ValueError("source binding cannot authorize publication")

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "production_snapshot_sha256": self.production_snapshot_sha256,
            "scene_id": self.scene_id,
            "slot_id": self.slot_id,
            "candidate_id": self.candidate_id,
            "asset_id": self.asset_id,
            "asset_sha256": self.asset_sha256,
            "product_job_id": self.product_job_id,
            "generation_execution_id": self.generation_execution_id,
            "queue_entry_id": self.queue_entry_id,
            "publication_authorized": False,
        }


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
    before_clip: InteractiveTimelineClip | None = None
    after_clip: InteractiveTimelineClip | None = None
    before_source_binding: TimelineSourceBinding | None = None
    after_source_binding: TimelineSourceBinding | None = None

    def __post_init__(self) -> None:
        _identity(self.command_id, "command_id")
        if not isinstance(self.kind, TimelineEditKind):
            raise ValueError("edit kind is invalid")
        if self.snap is not None and not isinstance(self.snap, SnapDecision):
            raise ValueError("snap decision is invalid")
        placement_kinds = {TimelineEditKind.INSERT_CLIP, TimelineEditKind.REMOVE_CLIP, TimelineEditKind.REPLACE_CLIP}
        if self.kind in placement_kinds:
            if self.target_clip_id is not None or self.target_track_id is not None:
                raise ValueError("clip placement does not use legacy target ids")
            if any(value is not None for value in (
                self.before_start_frame, self.before_end_frame, self.after_start_frame,
                self.after_end_frame, self.in_frame, self.out_frame, self.track, self.snap,
            )):
                raise ValueError("clip placement cannot carry legacy command data")
            if self.kind is TimelineEditKind.INSERT_CLIP:
                if (
                    self.before_clip is not None
                    or self.before_source_binding is not None
                    or self.after_clip is None
                    or self.after_source_binding is None
                ):
                    raise ValueError("INSERT_CLIP requires an exact absent-before pair")
            elif self.kind is TimelineEditKind.REMOVE_CLIP:
                if (
                    self.before_clip is None
                    or self.before_source_binding is None
                    or self.after_clip is not None
                    or self.after_source_binding is not None
                ):
                    raise ValueError("REMOVE_CLIP requires an exact absent-after pair")
            elif (
                self.before_clip is None
                or self.after_clip is None
                or (
                    self.before_source_binding is None
                    and self.after_source_binding is None
                )
            ):
                raise ValueError("REPLACE_CLIP requires exact before/after clips")
            for clip, binding, name in (
                (self.before_clip, self.before_source_binding, "before"),
                (self.after_clip, self.after_source_binding, "after"),
            ):
                if binding is not None and not isinstance(binding, TimelineSourceBinding):
                    raise ValueError(f"{name}_source_binding is invalid")
                if clip is None and binding is not None:
                    raise ValueError(f"{name}_source_binding requires its clip")
                if clip is not None and binding is not None and (
                    clip.source_owner != "TASK-003" or clip.source_ref != binding.asset_id
                    or clip.source_sha256 != binding.asset_sha256
                    or clip.review_candidate_id != binding.candidate_id
                    or clip.state != "PLACED_LOCKED_ASSET"
                ):
                    raise ValueError(f"{name} clip/source binding differs")
            if self.kind is TimelineEditKind.REPLACE_CLIP and (
                self.before_clip.clip_id != self.after_clip.clip_id
                or self.before_clip.track_id != self.after_clip.track_id
                or self.before_clip.start_frame != self.after_clip.start_frame
                or self.before_clip.end_frame != self.after_clip.end_frame
            ):
                raise ValueError("REPLACE_CLIP must preserve clip identity and placement")
        elif any(value is not None for value in (
            self.before_clip, self.after_clip, self.before_source_binding, self.after_source_binding,
        )):
            raise ValueError("legacy command cannot carry v1.1 clip placement data")
        elif self.kind in {TimelineEditKind.TRIM_START, TimelineEditKind.TRIM_END, TimelineEditKind.MOVE}:
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
        if self.kind in {TimelineEditKind.INSERT_CLIP, TimelineEditKind.REMOVE_CLIP, TimelineEditKind.REPLACE_CLIP}:
            body = {
                "command_id": self.command_id, "kind": self.kind.value,
                "target_clip_id": None, "target_track_id": None,
                "before_start_frame": None, "before_end_frame": None,
                "after_start_frame": None, "after_end_frame": None,
                "in_frame": None, "out_frame": None, "track": None, "snap": None,
                "before_clip": None if self.before_clip is None else self.before_clip.to_dict(),
                "after_clip": None if self.after_clip is None else self.after_clip.to_dict(),
                "before_source_binding": None if self.before_source_binding is None else self.before_source_binding.to_dict(),
                "after_source_binding": None if self.after_source_binding is None else self.after_source_binding.to_dict(),
            }
            body["command_sha256"] = sha256_bytes(canonical_json_bytes(body))
            return body
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
        if self.kind is TimelineEditKind.INSERT_CLIP:
            return TimelineEditCommand(
                command_id, TimelineEditKind.REMOVE_CLIP,
                before_clip=self.after_clip, before_source_binding=self.after_source_binding,
            )
        if self.kind is TimelineEditKind.REMOVE_CLIP:
            return TimelineEditCommand(
                command_id, TimelineEditKind.INSERT_CLIP,
                after_clip=self.before_clip, after_source_binding=self.before_source_binding,
            )
        if self.kind is TimelineEditKind.REPLACE_CLIP:
            return TimelineEditCommand(
                command_id, TimelineEditKind.REPLACE_CLIP,
                before_clip=self.after_clip, after_clip=self.before_clip,
                before_source_binding=self.after_source_binding,
                after_source_binding=self.before_source_binding,
            )
        if self.kind is TimelineEditKind.ADD_TRACK:
            return TimelineEditCommand(command_id, TimelineEditKind.REMOVE_TRACK,
                                       target_track_id=self.track.track_id, track=self.track)
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
    revision_version: str = "1.0.0"

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
        if self.revision_version not in {"1.0.0", "1.1.0"}:
            raise ValueError("revision_version is unsupported")
        placement = self.command.kind in {
            TimelineEditKind.INSERT_CLIP,
            TimelineEditKind.REMOVE_CLIP,
            TimelineEditKind.REPLACE_CLIP,
        }
        if placement and self.revision_version != "1.1.0":
            raise ValueError("clip placement requires revision version 1.1.0")
        for binding in (
            self.command.before_source_binding,
            self.command.after_source_binding,
        ):
            if binding is not None and binding.project_id != self.project_id:
                raise ValueError("source binding crosses revision Project scope")

    def to_dict(self) -> dict[str, Any]:
        body = {"revision_version": self.revision_version, "task_owner": "TASK-044/P-NLE-2",
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
        if current is not None and current.revision_version == "1.1.0" and value.revision_version != "1.1.0":
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_VERSION_DOWNGRADE",
                "Timeline edit history cannot append a v1.0 revision after v1.1",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        self.revisions.append(value)


class TimelineEditProjector:
    @staticmethod
    def apply(timeline: InteractiveTimeline, history: TimelineEditHistory) -> tuple[InteractiveTimeline, tuple[int, int] | None]:
        projected, in_out, _bindings = TimelineEditProjector.apply_with_source_bindings(timeline, history)
        return projected, in_out

    @staticmethod
    def apply_with_source_bindings(
        timeline: InteractiveTimeline,
        history: TimelineEditHistory,
    ) -> tuple[
        InteractiveTimeline,
        tuple[int, int] | None,
        dict[str, TimelineSourceBinding | None],
    ]:
        if history.current is not None and history.current.base_timeline_sha256 != timeline.timeline_sha256:
            raise ProductError("ERR_TIMELINE_EDIT_BASE_STALE", "Edit history targets an older Timeline", ProductErrorCategory.STATE)
        clips = {item.clip_id: item for item in timeline.clips}
        bindings: dict[str, TimelineSourceBinding | None] = {
            item.clip_id: None for item in timeline.clips
        }
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
                category_count = 0 if track is None else sum(
                    timeline_track_category(item) is timeline_track_category(track)
                    for item in tracks.values()
                )
                if track is None or track.minimum_required or category_count <= 1 or any(
                    clip.track_id == command.target_track_id for clip in clips.values()
                ):
                    raise ProductError(
                        "ERR_TIMELINE_TRACK_REMOVE_BLOCKED",
                        "Required, missing or non-empty track cannot be removed",
                        ProductErrorCategory.STATE,
                    )
                tracks.pop(command.target_track_id)
            elif command.kind is TimelineEditKind.INSERT_CLIP:
                after = command.after_clip
                if after.clip_id in clips:
                    raise ProductError(
                        "ERR_TIMELINE_EDIT_TARGET_STALE",
                        "Clip exists before INSERT_CLIP projection",
                        ProductErrorCategory.STATE,
                    )
                if after.track_id not in tracks or after.end_frame > timeline.duration_frames:
                    raise ProductError(
                        "ERR_TIMELINE_EDIT_RANGE",
                        "Inserted clip targets an invalid track or range",
                        ProductErrorCategory.STATE,
                    )
                clips[after.clip_id] = after
                bindings[after.clip_id] = command.after_source_binding
            elif command.kind is TimelineEditKind.REMOVE_CLIP:
                before = command.before_clip
                active = clips.get(before.clip_id)
                if active != before or bindings.get(before.clip_id) != command.before_source_binding:
                    raise ProductError(
                        "ERR_TIMELINE_EDIT_TARGET_STALE",
                        "Clip/source binding changed before REMOVE_CLIP projection",
                        ProductErrorCategory.STATE,
                    )
                clips.pop(before.clip_id)
                bindings.pop(before.clip_id)
            elif command.kind is TimelineEditKind.REPLACE_CLIP:
                before = command.before_clip
                after = command.after_clip
                active = clips.get(before.clip_id)
                if active != before or bindings.get(before.clip_id) != command.before_source_binding:
                    raise ProductError(
                        "ERR_TIMELINE_EDIT_TARGET_STALE",
                        "Clip/source binding changed before REPLACE_CLIP projection",
                        ProductErrorCategory.STATE,
                    )
                if after.track_id not in tracks or after.end_frame > timeline.duration_frames:
                    raise ProductError(
                        "ERR_TIMELINE_EDIT_RANGE",
                        "Replacement clip targets an invalid track or range",
                        ProductErrorCategory.STATE,
                    )
                clips[after.clip_id] = after
                bindings[after.clip_id] = command.after_source_binding
        projected = InteractiveTimeline(timeline.project_id, timeline.timeline_id, timeline.timeline_rate, timeline.duration_frames,
            tuple(sorted(tracks.values(), key=lambda item: (item.order, item.track_id))), tuple(clips.values()))
        return projected, in_out, bindings


__all__ = ["SnapAnchor", "SnapDecision", "SnapKind", "TimelineEditCommand", "TimelineEditHistory",
 "TimelineEditKind", "TimelineEditProjector", "TimelineEditRevision", "TimelineSnapService",
 "TimelineSourceBinding"]
