"""Canonical TASK-044 P-NLE-2 append-only Timeline edit child document."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .errors import ProductError, ProductErrorCategory
from .interactive_timeline import TimelineMediaKind, TimelineTrack, TimelineTrackRole
from .interactive_timeline_edit import (
    SnapAnchor,
    SnapDecision,
    SnapKind,
    TimelineEditCommand,
    TimelineEditHistory,
    TimelineEditKind,
    TimelineEditRevision,
)
from .serialization import canonical_json_bytes, sha256_bytes

FORMAT_ID = "bai-video-production.interactive-timeline-edit-history"
FORMAT_VERSION = "1.0.0"
RELATIVE_PATH = "state/interactive-timeline-edits.json"
_MAX_BYTES = 16 * 1024 * 1024
_FIELDS = {
    "snapshot_version", "task_owner", "project_id", "history_id", "revisions",
    "current_revision", "base_timeline_sha256", "external_mutation_authorized",
    "snapshot_sha256",
}


def _track(value: Mapping[str, Any]) -> TimelineTrack:
    if set(value) != {"track_id", "order", "role", "media_kind", "label", "minimum_required"}:
        raise ValueError("track fields are not exact")
    return TimelineTrack(
        value["track_id"], value["order"], TimelineTrackRole(value["role"]),
        TimelineMediaKind(value["media_kind"]), value["label"], value["minimum_required"],
    )


def _snap(value: Mapping[str, Any] | None) -> SnapDecision | None:
    if value is None:
        return None
    if set(value) != {"desired_frame", "effective_frame", "anchor"}:
        raise ValueError("snap fields are not exact")
    anchor_value = value["anchor"]
    anchor = None
    if anchor_value is not None:
        if set(anchor_value) != {"anchor_id", "frame", "kind", "priority"}:
            raise ValueError("snap anchor fields are not exact")
        anchor = SnapAnchor(
            anchor_value["anchor_id"], anchor_value["frame"],
            SnapKind(anchor_value["kind"]), anchor_value["priority"],
        )
    return SnapDecision(value["desired_frame"], value["effective_frame"], anchor)


def _command(value: Mapping[str, Any]) -> TimelineEditCommand:
    expected = {
        "command_id", "kind", "target_clip_id", "target_track_id",
        "before_start_frame", "before_end_frame", "after_start_frame",
        "after_end_frame", "in_frame", "out_frame", "track", "snap",
        "command_sha256",
    }
    if set(value) != expected:
        raise ValueError("command fields are not exact")
    claimed = value["command_sha256"]
    command = TimelineEditCommand(
        command_id=value["command_id"], kind=TimelineEditKind(value["kind"]),
        target_clip_id=value["target_clip_id"], target_track_id=value["target_track_id"],
        before_start_frame=value["before_start_frame"], before_end_frame=value["before_end_frame"],
        after_start_frame=value["after_start_frame"], after_end_frame=value["after_end_frame"],
        in_frame=value["in_frame"], out_frame=value["out_frame"],
        track=None if value["track"] is None else _track(value["track"]), snap=_snap(value["snap"]),
    )
    if claimed != command.command_sha256:
        raise ValueError("command checksum mismatch")
    return command


def parse_timeline_edit_history(document: Mapping[str, Any]) -> TimelineEditHistory:
    try:
        if not isinstance(document, Mapping) or set(document) != _FIELDS:
            raise ValueError("snapshot fields are not exact")
        claimed = document["snapshot_sha256"]
        body = {key: value for key, value in document.items() if key != "snapshot_sha256"}
        if claimed != sha256_bytes(canonical_json_bytes(body)):
            raise ValueError("snapshot checksum mismatch")
        if document["snapshot_version"] != FORMAT_VERSION or document["task_owner"] != "TASK-044/P-NLE-2":
            raise ValueError("snapshot identity is invalid")
        if document["external_mutation_authorized"] is not False:
            raise ValueError("external authority boundary is invalid")
        history = TimelineEditHistory(document["project_id"], document["history_id"])
        for row in document["revisions"]:
            expected = {
                "revision_version", "task_owner", "project_id", "history_id", "revision",
                "base_timeline_sha256", "previous_revision_sha256", "command",
                "external_mutation_authorized", "revision_sha256",
            }
            if not isinstance(row, Mapping) or set(row) != expected:
                raise ValueError("revision fields are not exact")
            revision = TimelineEditRevision(
                project_id=row["project_id"], history_id=row["history_id"], revision=row["revision"],
                base_timeline_sha256=row["base_timeline_sha256"], command=_command(row["command"]),
                previous_revision_sha256=row["previous_revision_sha256"],
            )
            if row["revision_version"] != FORMAT_VERSION or row["task_owner"] != "TASK-044/P-NLE-2":
                raise ValueError("revision identity is invalid")
            if row["external_mutation_authorized"] is not False or row["revision_sha256"] != revision.revision_sha256:
                raise ValueError("revision checksum or authority mismatch")
            history.append(revision)
        current = history.current
        if document["current_revision"] != (0 if current is None else current.revision):
            raise ValueError("current revision mismatch")
        if document["base_timeline_sha256"] != (None if current is None else current.base_timeline_sha256):
            raise ValueError("base Timeline checksum mismatch")
        return history
    except ProductError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductError(
            "ERR_TIMELINE_EDIT_SNAPSHOT_INVALID",
            "Timeline edit history is invalid",
            ProductErrorCategory.DATA_INTEGRITY,
        ) from exc


class TimelineEditSnapshotStore:
    @staticmethod
    def serialize(history: TimelineEditHistory) -> bytes:
        current = history.current
        body = {
            "snapshot_version": FORMAT_VERSION,
            "task_owner": "TASK-044/P-NLE-2",
            "project_id": history.project_id,
            "history_id": history.history_id,
            "revisions": [item.to_dict() for item in history.revisions],
            "current_revision": 0 if current is None else current.revision,
            "base_timeline_sha256": None if current is None else current.base_timeline_sha256,
            "external_mutation_authorized": False,
        }
        return canonical_json_bytes({**body, "snapshot_sha256": sha256_bytes(canonical_json_bytes(body))})

    @staticmethod
    def load(path: str | Path, *, expected_project_id: str) -> TimelineEditHistory:
        target = Path(path)
        if target.is_symlink() or not target.is_file() or not 0 < target.stat().st_size <= _MAX_BYTES:
            raise ProductError("ERR_TIMELINE_EDIT_FILE_INVALID", "Timeline edit file is invalid", ProductErrorCategory.DATA_INTEGRITY)
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_TIMELINE_EDIT_READ", "Timeline edit file cannot be read", ProductErrorCategory.DATA_INTEGRITY) from exc
        history = parse_timeline_edit_history(document)
        if history.project_id != expected_project_id:
            raise ProductError("ERR_TIMELINE_EDIT_PROJECT_MISMATCH", "Timeline edits belong to another Project", ProductErrorCategory.SECURITY)
        return history


__all__ = [
    "FORMAT_ID", "FORMAT_VERSION", "RELATIVE_PATH", "TimelineEditSnapshotStore",
    "parse_timeline_edit_history",
]
