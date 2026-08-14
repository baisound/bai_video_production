"""Canonical append-only child document for TASK-042 Timeline Audio."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes
from .timebase import FrameRate
from .timeline_audio import (AudioCue, AudioFitPolicy, AudioRange, AudioSourceBinding,
    AudioSourceIntent, MusicPlan, NarrationCue, NarrationCueOrigin, SrtProposalState,
    TimelineAudioItem, TimelineAudioPlan, TimelineAudioRole)

FORMAT_ID = "bai-video-production.timeline-audio-history"
FORMAT_VERSION = "1.0.0"
RELATIVE_PATH = "state/timeline-audio.json"
_MAX_BYTES = 12 * 1024 * 1024
_FIELDS = {"snapshot_version", "task_owner", "project_id", "plans", "current_plan_id",
           "current_revision", "script_bodies_embedded", "media_bytes_embedded",
           "provider_execution_authority", "snapshot_sha256"}


class TimelineAudioHistory:
    def __init__(self, project_id: str) -> None:
        if not isinstance(project_id, str) or not project_id.strip(): raise ValueError("project_id is invalid")
        self.project_id = project_id
        self.plans: dict[tuple[str, int], TimelineAudioPlan] = {}
        self.current_key: tuple[str, int] | None = None

    @property
    def current_plan(self) -> TimelineAudioPlan | None:
        return None if self.current_key is None else self.plans[self.current_key]

    def add_plan(self, plan: TimelineAudioPlan) -> None:
        if plan.project_id != self.project_id:
            raise ProductError("ERR_TIMELINE_AUDIO_PROJECT_MISMATCH", "Timeline plan belongs to another project", ProductErrorCategory.SECURITY)
        key = (plan.plan_id, plan.revision)
        if key in self.plans: raise ProductError("ERR_TIMELINE_AUDIO_REVISION_CONFLICT", "Plan revision already exists", ProductErrorCategory.STATE)
        current = self.current_plan
        if current is None:
            valid = plan.revision == 1 and plan.previous_plan_sha256 is None
        else:
            valid = (plan.plan_id == current.plan_id and plan.revision == current.revision + 1
                     and plan.previous_plan_sha256 == current.plan_sha256)
        if not valid: raise ProductError("ERR_TIMELINE_AUDIO_HISTORY_FORK", "Plan must append to the exact current revision", ProductErrorCategory.DATA_INTEGRITY)
        self.plans[key] = plan; self.current_key = key


def _source(value: Mapping[str, Any]) -> AudioSourceBinding:
    return AudioSourceBinding(value["slot_id"], AudioSourceIntent(value["source_intent"]),
        value.get("candidate_id"), value.get("asset_id"), value.get("asset_sha256"), value.get("source_duration_frames"))


def _parse_item(row: Mapping[str, Any]) -> TimelineAudioItem:
    claimed = row.get("item_sha256"); body = {key: value for key, value in row.items() if key != "item_sha256"}
    if claimed != sha256_bytes(canonical_json_bytes(body)): raise ValueError("item checksum mismatch")
    common = dict(item_id=row["item_id"], lane_id=row["lane_id"], start_frame=row["start_frame"], source=_source(row["source"]))
    kind = row["item_kind"]
    if kind == "MUSIC_PLAN":
        item = MusicPlan(**common, end_frame=row["end_frame"], fit_policy=AudioFitPolicy(row["fit_policy"]),
            fade_in_frames=row["fade_in_frames"], fade_out_frames=row["fade_out_frames"], gain_db=row.get("gain_db"),
            whole_timeline=row["whole_timeline"], transition_group_id=row.get("transition_group_id"))
    elif kind == "NARRATION_CUE":
        if row.get("text_body_persisted") is not False: raise ValueError("text boundary invalid")
        item = NarrationCue(**common, end_frame=row["end_frame"], scene_id=row["scene_id"], text_ref=row["text_ref"],
            text_sha256=row["text_sha256"], origin=NarrationCueOrigin(row["origin"]),
            proposal_state=SrtProposalState(row["proposal_state"]), conflict_codes=tuple(row["conflict_codes"]), gain_db=row.get("gain_db"))
    elif kind == "AUDIO_CUE":
        item = AudioCue(**common, duration_frames=row["duration_frames"], gain_db=row.get("gain_db"))
    elif kind == "AUDIO_RANGE":
        item = AudioRange(**common, role=TimelineAudioRole(row["role"]), end_frame=row["end_frame"],
            fit_policy=AudioFitPolicy(row["fit_policy"]), fade_in_frames=row["fade_in_frames"],
            fade_out_frames=row["fade_out_frames"], gain_db=row.get("gain_db"))
    else: raise ValueError("unknown item kind")
    if item.to_dict() != dict(row): raise ValueError("item canonical form mismatch")
    return item


def _parse_plan(row: Mapping[str, Any]) -> TimelineAudioPlan:
    claimed = row.get("plan_sha256"); body = {key: value for key, value in row.items() if key != "plan_sha256"}
    if claimed != sha256_bytes(canonical_json_bytes(body)): raise ValueError("plan checksum mismatch")
    boundary = {"timeline_frames_authoritative": True, "srt_timing_authoritative": False,
      "provider_execution_started": False, "candidate_mutation_started": False,
      "task026_compile_started": False, "resolve_mutation_started": False, "cubase_mutation_started": False}
    if row.get("timeline_audio_plan_version") != FORMAT_VERSION or row.get("task_owner") != "TASK-042/P-V6-4" or any(row.get(k) is not v for k,v in boundary.items()):
        raise ValueError("plan version/authority boundary invalid")
    rate = row["timeline_rate"]
    plan = TimelineAudioPlan(row["project_id"], row["plan_id"], row["revision"], row["blueprint_id"],
        row["blueprint_sha256"], FrameRate(rate["numerator"], rate["denominator"]),
        row["target_duration_frames"], tuple(_parse_item(item) for item in row["items"]), row.get("previous_plan_sha256"))
    if plan.to_dict() != dict(row): raise ValueError("plan canonical form mismatch")
    return plan


class TimelineAudioSnapshotStore:
    @staticmethod
    def snapshot(history: TimelineAudioHistory) -> dict[str, Any]:
        current = history.current_plan
        body = {"snapshot_version": FORMAT_VERSION, "task_owner": "TASK-042/P-V6-4", "project_id": history.project_id,
          "plans": [history.plans[key].to_dict() for key in sorted(history.plans)],
          "current_plan_id": None if current is None else current.plan_id,
          "current_revision": None if current is None else current.revision,
          "script_bodies_embedded": False, "media_bytes_embedded": False, "provider_execution_authority": False}
        body["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body)); return body

    @classmethod
    def serialize(cls, history: TimelineAudioHistory) -> bytes:
        return canonical_json_bytes(cls.snapshot(history))

    @classmethod
    def parse(cls, document: Mapping[str, Any], *, expected_project_id: str | None = None) -> TimelineAudioHistory:
        if set(document) != _FIELDS: raise ProductError("ERR_TIMELINE_AUDIO_SNAPSHOT_FIELDS", "Snapshot fields are not exact", ProductErrorCategory.DATA_INTEGRITY)
        body = {key: value for key, value in document.items() if key != "snapshot_sha256"}
        if document.get("snapshot_sha256") != sha256_bytes(canonical_json_bytes(body)):
            raise ProductError("ERR_TIMELINE_AUDIO_SNAPSHOT_CHECKSUM", "Snapshot checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
        if document.get("snapshot_version") != FORMAT_VERSION or document.get("task_owner") != "TASK-042/P-V6-4" or document.get("script_bodies_embedded") is not False or document.get("media_bytes_embedded") is not False or document.get("provider_execution_authority") is not False:
            raise ProductError("ERR_TIMELINE_AUDIO_SNAPSHOT_BOUNDARY", "Snapshot version or boundary is invalid", ProductErrorCategory.SECURITY)
        try:
            history = TimelineAudioHistory(document["project_id"])
            for row in document["plans"]: history.add_plan(_parse_plan(row))
            current = history.current_plan
            pointer = (document["current_plan_id"], document["current_revision"]) if document["current_plan_id"] is not None else None
            if pointer != (None if current is None else (current.plan_id, current.revision)): raise ValueError("current pointer mismatch")
            if expected_project_id is not None and history.project_id != expected_project_id: raise ProductError("ERR_TIMELINE_AUDIO_PROJECT_MISMATCH", "Snapshot belongs to another project", ProductErrorCategory.SECURITY)
            return history
        except ProductError: raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ProductError("ERR_TIMELINE_AUDIO_SNAPSHOT_INVALID", "Snapshot history is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc

    @classmethod
    def parse_bytes(cls, value: bytes, *, expected_project_id: str | None = None) -> TimelineAudioHistory:
        if not isinstance(value, bytes) or not 0 < len(value) <= _MAX_BYTES: raise ProductError("ERR_TIMELINE_AUDIO_SNAPSHOT_SIZE", "Snapshot size is invalid", ProductErrorCategory.VALIDATION)
        try: document = json.loads(value.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc: raise ProductError("ERR_TIMELINE_AUDIO_SNAPSHOT_READ", "Snapshot is not UTF-8 JSON", ProductErrorCategory.DATA_INTEGRITY) from exc
        if not isinstance(document, dict): raise ProductError("ERR_TIMELINE_AUDIO_SNAPSHOT_INVALID", "Snapshot root must be an object", ProductErrorCategory.DATA_INTEGRITY)
        return cls.parse(document, expected_project_id=expected_project_id)

    @classmethod
    def load(cls, path: str | Path, *, expected_project_id: str | None = None) -> TimelineAudioHistory:
        target = Path(path)
        if target.is_symlink() or not target.is_file(): raise ProductError("ERR_TIMELINE_AUDIO_SNAPSHOT_FILE", "Snapshot must be a regular non-symlink file", ProductErrorCategory.SECURITY)
        return cls.parse_bytes(target.read_bytes(), expected_project_id=expected_project_id)


__all__ = ["FORMAT_ID", "FORMAT_VERSION", "RELATIVE_PATH", "TimelineAudioHistory", "TimelineAudioSnapshotStore"]
