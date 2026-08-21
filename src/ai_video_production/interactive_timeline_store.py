"""Canonical TASK-044 P-NLE-2 append-only Timeline edit child document."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .errors import ProductError, ProductErrorCategory
from .interactive_timeline import (
    InteractiveTimelineClip,
    TimelineMediaKind,
    TimelineTrack,
    TimelineTrackRole,
)
from .interactive_timeline_edit import (
    SnapAnchor,
    SnapDecision,
    SnapKind,
    TimelineEditCommand,
    TimelineEditHistory,
    TimelineEditKind,
    TimelineEditRevision,
    TimelineSourceBinding,
)
from .serialization import canonical_json_bytes, sha256_bytes

FORMAT_ID = "bai-video-production.interactive-timeline-edit-history"
FORMAT_VERSION = "1.0.0"
FORMAT_VERSION_V1_1 = "1.1.0"
SUPPORTED_FORMAT_VERSIONS = (FORMAT_VERSION, FORMAT_VERSION_V1_1)
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


def _clip(value: Mapping[str, Any] | None) -> InteractiveTimelineClip | None:
    if value is None:
        return None
    expected = {
        "clip_id", "track_id", "start_frame", "end_frame", "source_owner",
        "source_ref", "source_sha256", "label", "state", "review_candidate_id",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("clip fields are not exact")
    return InteractiveTimelineClip(
        value["clip_id"], value["track_id"], value["start_frame"],
        value["end_frame"], value["source_owner"], value["source_ref"],
        value["source_sha256"], value["label"], value["state"],
        value["review_candidate_id"],
    )


def _source_binding(value: Mapping[str, Any] | None) -> TimelineSourceBinding | None:
    if value is None:
        return None
    expected = {
        "project_id", "production_snapshot_sha256", "scene_id", "slot_id",
        "candidate_id", "asset_id", "asset_sha256", "product_job_id",
        "generation_execution_id", "queue_entry_id", "publication_authorized",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("source binding fields are not exact")
    return TimelineSourceBinding(
        project_id=value["project_id"],
        production_snapshot_sha256=value["production_snapshot_sha256"],
        scene_id=value["scene_id"],
        slot_id=value["slot_id"],
        candidate_id=value["candidate_id"],
        asset_id=value["asset_id"],
        asset_sha256=value["asset_sha256"],
        product_job_id=value["product_job_id"],
        generation_execution_id=value["generation_execution_id"],
        queue_entry_id=value["queue_entry_id"],
        publication_authorized=value["publication_authorized"],
    )


def _command(value: Mapping[str, Any], *, revision_version: str) -> TimelineEditCommand:
    legacy_fields = {
        "command_id", "kind", "target_clip_id", "target_track_id",
        "before_start_frame", "before_end_frame", "after_start_frame",
        "after_end_frame", "in_frame", "out_frame", "track", "snap",
        "command_sha256",
    }
    placement_fields = legacy_fields | {
        "before_clip", "after_clip", "before_source_binding", "after_source_binding",
    }
    if not isinstance(value, Mapping) or frozenset(value) not in {
        frozenset(legacy_fields), frozenset(placement_fields),
    }:
        raise ValueError("command fields are not exact")
    is_placement_shape = set(value) == placement_fields
    if is_placement_shape and revision_version != FORMAT_VERSION_V1_1:
        raise ValueError("placement command requires revision version 1.1.0")
    claimed = value["command_sha256"]
    command = TimelineEditCommand(
        command_id=value["command_id"], kind=TimelineEditKind(value["kind"]),
        target_clip_id=value["target_clip_id"], target_track_id=value["target_track_id"],
        before_start_frame=value["before_start_frame"], before_end_frame=value["before_end_frame"],
        after_start_frame=value["after_start_frame"], after_end_frame=value["after_end_frame"],
        in_frame=value["in_frame"], out_frame=value["out_frame"],
        track=None if value["track"] is None else _track(value["track"]), snap=_snap(value["snap"]),
        before_clip=_clip(value["before_clip"]) if is_placement_shape else None,
        after_clip=_clip(value["after_clip"]) if is_placement_shape else None,
        before_source_binding=(
            _source_binding(value["before_source_binding"])
            if is_placement_shape else None
        ),
        after_source_binding=(
            _source_binding(value["after_source_binding"])
            if is_placement_shape else None
        ),
    )
    is_placement_kind = command.kind in {
        TimelineEditKind.INSERT_CLIP,
        TimelineEditKind.REMOVE_CLIP,
        TimelineEditKind.REPLACE_CLIP,
    }
    if is_placement_shape != is_placement_kind:
        raise ValueError("command kind/shape version is inconsistent")
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
        snapshot_version = document["snapshot_version"]
        if snapshot_version not in SUPPORTED_FORMAT_VERSIONS or document["task_owner"] != "TASK-044/P-NLE-2":
            raise ValueError("snapshot identity is invalid")
        if document["external_mutation_authorized"] is not False:
            raise ValueError("external authority boundary is invalid")
        history = TimelineEditHistory(document["project_id"], document["history_id"])
        saw_v1_1 = False
        for row in document["revisions"]:
            expected = {
                "revision_version", "task_owner", "project_id", "history_id", "revision",
                "base_timeline_sha256", "previous_revision_sha256", "command",
                "external_mutation_authorized", "revision_sha256",
            }
            if not isinstance(row, Mapping) or set(row) != expected:
                raise ValueError("revision fields are not exact")
            revision_version = row["revision_version"]
            if revision_version not in SUPPORTED_FORMAT_VERSIONS:
                raise ValueError("revision version is unsupported")
            if saw_v1_1 and revision_version == FORMAT_VERSION:
                raise ValueError("revision history downgrades after v1.1")
            saw_v1_1 = saw_v1_1 or revision_version == FORMAT_VERSION_V1_1
            revision = TimelineEditRevision(
                project_id=row["project_id"], history_id=row["history_id"], revision=row["revision"],
                base_timeline_sha256=row["base_timeline_sha256"],
                command=_command(row["command"], revision_version=revision_version),
                previous_revision_sha256=row["previous_revision_sha256"],
                revision_version=revision_version,
            )
            if row["task_owner"] != "TASK-044/P-NLE-2":
                raise ValueError("revision identity is invalid")
            if row["external_mutation_authorized"] is not False or row["revision_sha256"] != revision.revision_sha256:
                raise ValueError("revision checksum or authority mismatch")
            history.append(revision)
        if snapshot_version == FORMAT_VERSION and saw_v1_1:
            raise ValueError("v1.0 snapshot contains a v1.1 revision")
        if snapshot_version == FORMAT_VERSION_V1_1 and not saw_v1_1:
            raise ValueError("v1.1 snapshot requires at least one v1.1 revision")
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
        snapshot_version = (
            FORMAT_VERSION_V1_1
            if any(item.revision_version == FORMAT_VERSION_V1_1 for item in history.revisions)
            else FORMAT_VERSION
        )
        body = {
            "snapshot_version": snapshot_version,
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
    "FORMAT_ID", "FORMAT_VERSION", "FORMAT_VERSION_V1_1", "RELATIVE_PATH",
    "SUPPORTED_FORMAT_VERSIONS", "TimelineEditSnapshotStore", "parse_timeline_edit_history",
]
