"""Strict Product Project child history for TASK-026 placement plans."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .audio_placement import (
    AudioPlacementPlan,
    AudioPlacementRole,
    AudioPlacementSegment,
    BedMode,
    SnapAnchor,
)
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes


FORMAT_ID = "bai-video-production.audio-placement-history"
FORMAT_VERSION = "1.0.0"
RELATIVE_PATH = "state/audio-placement-history.json"
MAX_RECORDS = 10_000
MAX_BYTES = 12 * 1024 * 1024

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")
_ROOT_FIELDS = {
    "snapshot_version",
    "task_owner",
    "project_id",
    "store_revision",
    "records",
    "provider_execution_authority",
    "paid_execution_authority",
    "media_bytes_embedded",
    "external_mutation_authority",
    "snapshot_sha256",
}
_RECORD_FIELDS = {
    "compilation_id",
    "project_id",
    "source_project_revision",
    "source_project_manifest_sha256",
    "review_id",
    "placement_decision",
    "audio_snapshot_sha256",
    "production_snapshot_sha256",
    "timeline_snapshot_sha256",
    "slot_id",
    "candidate_id",
    "asset_id",
    "asset_sha256",
    "timeline_plan_id",
    "timeline_revision",
    "timeline_plan_sha256",
    "timeline_item_id",
    "timeline_item_sha256",
    "track_index",
    "bed_mode",
    "task026_plan",
    "task026_plan_sha256",
    "task010_structurally_compatible",
    "provider_execution_started",
    "paid_execution_authorized",
    "media_write_started",
    "task010_execution_started",
    "resolve_mutation_started",
    "cubase_mutation_started",
}


def _require_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{field} is invalid")
    return value


def _require_sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise ValueError(f"{field} is invalid")
    return value


def _require_int(value: Any, field: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{field} is invalid")
    return value


def parse_audio_placement_plan(value: Mapping[str, Any]) -> AudioPlacementPlan:
    expected = {
        "plan_version", "task_owner", "resolve_execution_owner", "asset_id", "role",
        "track_index", "requested_start_frame", "effective_start_frame",
        "desired_duration_frames", "source_duration_frames", "snapped_to", "loop",
        "fade_in_frames", "fade_out_frames", "gain_db", "bed_mode", "segments",
        "task010_compatible", "external_write_authorized", "plan_sha256",
    }
    if set(value) != expected:
        raise ValueError("TASK-026 Plan fields are not exact")
    if value.get("plan_version") != FORMAT_VERSION or value.get("task_owner") != "TASK-026":
        raise ValueError("TASK-026 Plan version/owner is invalid")
    if value.get("resolve_execution_owner") != "TASK-010" or value.get("external_write_authorized") is not False:
        raise ValueError("TASK-026 Plan authority boundary is invalid")
    _require_id(value.get("asset_id"), "asset_id")
    for field, minimum in (
        ("track_index", 1),
        ("requested_start_frame", 0),
        ("effective_start_frame", 0),
        ("desired_duration_frames", 1),
        ("source_duration_frames", 1),
        ("fade_in_frames", 0),
        ("fade_out_frames", 0),
    ):
        _require_int(value.get(field), field, minimum=minimum)
    if not isinstance(value.get("loop"), bool):
        raise ValueError("TASK-026 loop is invalid")
    if value["fade_in_frames"] + value["fade_out_frames"] > value["desired_duration_frames"]:
        raise ValueError("TASK-026 fade range is invalid")
    gain = value.get("gain_db")
    if gain is not None and (
        isinstance(gain, bool) or not isinstance(gain, (int, float)) or not -120 <= gain <= 24
    ):
        raise ValueError("TASK-026 gain_db is invalid")
    if not isinstance(value.get("task010_compatible"), bool):
        raise ValueError("TASK-026 compatibility flag is invalid")
    _require_sha(value.get("plan_sha256"), "plan_sha256")
    snapped = value.get("snapped_to")
    if snapped is not None:
        if not isinstance(snapped, Mapping) or set(snapped) != {"frame", "reason"}:
            raise ValueError("TASK-026 snap binding is invalid")
        _require_int(snapped.get("frame"), "snapped_to.frame", minimum=0)
        if not isinstance(snapped.get("reason"), str):
            raise ValueError("TASK-026 snap reason is invalid")
        snap = SnapAnchor(frame=snapped["frame"], reason=snapped["reason"])
    else:
        snap = None
    rows = value.get("segments")
    if not isinstance(rows, list) or not rows or len(rows) > MAX_RECORDS:
        raise ValueError("TASK-026 Plan segments are invalid")
    segments_list = []
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {
            "segment_index", "timeline_start_frame", "duration_frames", "source_start_frame"
        }:
            raise ValueError("TASK-026 Plan segment fields are invalid")
        for field, minimum in (
            ("segment_index", 1), ("timeline_start_frame", 0),
            ("duration_frames", 1), ("source_start_frame", 0),
        ):
            _require_int(row.get(field), f"segment.{field}", minimum=minimum)
        segments_list.append(AudioPlacementSegment(
            segment_index=row["segment_index"],
            timeline_start_frame=row["timeline_start_frame"],
            duration_frames=row["duration_frames"],
            source_start_frame=row["source_start_frame"],
        ))
    segments = tuple(segments_list)
    plan = AudioPlacementPlan(
        asset_id=value["asset_id"],
        role=AudioPlacementRole(value["role"]),
        track_index=value["track_index"],
        requested_start_frame=value["requested_start_frame"],
        effective_start_frame=value["effective_start_frame"],
        desired_duration_frames=value["desired_duration_frames"],
        source_duration_frames=value["source_duration_frames"],
        snapped_to=snap,
        loop=value["loop"],
        fade_in_frames=value["fade_in_frames"],
        fade_out_frames=value["fade_out_frames"],
        gain_db=value.get("gain_db"),
        bed_mode=BedMode(value["bed_mode"]),
        segments=segments,
    )
    if plan.to_dict() != dict(value):
        raise ValueError("TASK-026 Plan canonical form/checksum is invalid")
    return plan


def _plan_sha256(plan: AudioPlacementPlan) -> str:
    """Return the checksum from the canonical TASK-026 projection."""
    value = plan.to_dict().get("plan_sha256")
    return _require_sha(value, "task026_plan_sha256")


@dataclass(frozen=True, slots=True)
class AudioPlacementCompilationRecord:
    compilation_id: str
    project_id: str
    source_project_revision: int
    source_project_manifest_sha256: str
    review_id: str
    placement_decision: str
    audio_snapshot_sha256: str
    production_snapshot_sha256: str
    timeline_snapshot_sha256: str
    slot_id: str
    candidate_id: str
    asset_id: str
    asset_sha256: str
    timeline_plan_id: str
    timeline_revision: int
    timeline_plan_sha256: str
    timeline_item_id: str
    timeline_item_sha256: str
    track_index: int
    bed_mode: BedMode
    plan: AudioPlacementPlan

    def __post_init__(self) -> None:
        for field in (
            "compilation_id", "project_id", "review_id", "slot_id", "candidate_id",
            "asset_id", "timeline_plan_id", "timeline_item_id",
        ):
            _require_id(getattr(self, field), field)
        for field in (
            "source_project_manifest_sha256", "audio_snapshot_sha256",
            "production_snapshot_sha256", "timeline_snapshot_sha256", "asset_sha256",
            "timeline_plan_sha256", "timeline_item_sha256",
        ):
            _require_sha(getattr(self, field), field)
        _require_int(self.source_project_revision, "source_project_revision", minimum=1)
        _require_int(self.timeline_revision, "timeline_revision", minimum=1)
        _require_int(self.track_index, "track_index", minimum=1)
        if self.placement_decision != "ACCEPT":
            raise ValueError("placement_decision must be ACCEPT")
        if self.plan.asset_id != self.asset_id or self.plan.track_index != self.track_index or self.plan.bed_mode is not self.bed_mode:
            raise ValueError("TASK-026 Plan does not match its compilation binding")
        if self.compilation_id != self.derive_compilation_id(self.identity_body()):
            raise ValueError("compilation_id is not deterministic")

    @staticmethod
    def derive_compilation_id(body: Mapping[str, Any]) -> str:
        return "audio-placement-" + sha256_bytes(canonical_json_bytes(body))[7:31]

    def identity_body(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "review_id": self.review_id,
            "audio_snapshot_sha256": self.audio_snapshot_sha256,
            "production_snapshot_sha256": self.production_snapshot_sha256,
            "timeline_snapshot_sha256": self.timeline_snapshot_sha256,
            "slot_id": self.slot_id,
            "candidate_id": self.candidate_id,
            "asset_id": self.asset_id,
            "asset_sha256": self.asset_sha256,
            "timeline_plan_id": self.timeline_plan_id,
            "timeline_revision": self.timeline_revision,
            "timeline_plan_sha256": self.timeline_plan_sha256,
            "timeline_item_id": self.timeline_item_id,
            "timeline_item_sha256": self.timeline_item_sha256,
            "track_index": self.track_index,
            "bed_mode": self.bed_mode.value,
            "task026_plan_sha256": _plan_sha256(self.plan),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "compilation_id": self.compilation_id,
            "project_id": self.project_id,
            "source_project_revision": self.source_project_revision,
            "source_project_manifest_sha256": self.source_project_manifest_sha256,
            "review_id": self.review_id,
            "placement_decision": self.placement_decision,
            "audio_snapshot_sha256": self.audio_snapshot_sha256,
            "production_snapshot_sha256": self.production_snapshot_sha256,
            "timeline_snapshot_sha256": self.timeline_snapshot_sha256,
            "slot_id": self.slot_id,
            "candidate_id": self.candidate_id,
            "asset_id": self.asset_id,
            "asset_sha256": self.asset_sha256,
            "timeline_plan_id": self.timeline_plan_id,
            "timeline_revision": self.timeline_revision,
            "timeline_plan_sha256": self.timeline_plan_sha256,
            "timeline_item_id": self.timeline_item_id,
            "timeline_item_sha256": self.timeline_item_sha256,
            "track_index": self.track_index,
            "bed_mode": self.bed_mode.value,
            "task026_plan": self.plan.to_dict(),
            "task026_plan_sha256": _plan_sha256(self.plan),
            "task010_structurally_compatible": self.plan.task010_compatible,
            "provider_execution_started": False,
            "paid_execution_authorized": False,
            "media_write_started": False,
            "task010_execution_started": False,
            "resolve_mutation_started": False,
            "cubase_mutation_started": False,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AudioPlacementCompilationRecord":
        if set(value) != _RECORD_FIELDS:
            raise ValueError("TASK-026 compilation fields are not exact")
        for field in (
            "provider_execution_started", "paid_execution_authorized", "media_write_started",
            "task010_execution_started", "resolve_mutation_started", "cubase_mutation_started",
        ):
            if value.get(field) is not False:
                raise ValueError("TASK-026 compilation authority boundary is invalid")
        plan_value = value.get("task026_plan")
        if not isinstance(plan_value, Mapping):
            raise ValueError("TASK-026 Plan is invalid")
        plan = parse_audio_placement_plan(plan_value)
        if value.get("task026_plan_sha256") != _plan_sha256(plan) or value.get("task010_structurally_compatible") is not plan.task010_compatible:
            raise ValueError("TASK-026 derived Plan fields are invalid")
        return cls(
            compilation_id=value["compilation_id"], project_id=value["project_id"],
            source_project_revision=value["source_project_revision"],
            source_project_manifest_sha256=value["source_project_manifest_sha256"],
            review_id=value["review_id"], placement_decision=value["placement_decision"],
            audio_snapshot_sha256=value["audio_snapshot_sha256"],
            production_snapshot_sha256=value["production_snapshot_sha256"],
            timeline_snapshot_sha256=value["timeline_snapshot_sha256"],
            slot_id=value["slot_id"], candidate_id=value["candidate_id"],
            asset_id=value["asset_id"], asset_sha256=value["asset_sha256"],
            timeline_plan_id=value["timeline_plan_id"], timeline_revision=value["timeline_revision"],
            timeline_plan_sha256=value["timeline_plan_sha256"],
            timeline_item_id=value["timeline_item_id"], timeline_item_sha256=value["timeline_item_sha256"],
            track_index=value["track_index"], bed_mode=BedMode(value["bed_mode"]), plan=plan,
        )


class AudioPlacementHistory:
    def __init__(self, project_id: str) -> None:
        _require_id(project_id, "project_id")
        self.project_id = project_id
        self.store_revision = 0
        self.records: dict[str, AudioPlacementCompilationRecord] = {}

    def append(self, record: AudioPlacementCompilationRecord) -> bool:
        if record.project_id != self.project_id:
            raise ProductError("ERR_AUDIO_PLACEMENT_PROJECT_MISMATCH", "Compilation belongs to another Project", ProductErrorCategory.SECURITY)
        existing = self.records.get(record.compilation_id)
        if existing is not None:
            if existing != record:
                raise ProductError("ERR_AUDIO_PLACEMENT_IDENTITY_COLLISION", "Compilation identity has conflicting content", ProductErrorCategory.DATA_INTEGRITY)
            return False
        if len(self.records) >= MAX_RECORDS:
            raise ProductError("ERR_AUDIO_PLACEMENT_HISTORY_LIMIT", "Compilation history reached its bounded maximum", ProductErrorCategory.NOT_SUPPORTED)
        self.records[record.compilation_id] = record
        self.store_revision += 1
        return True


class AudioPlacementHistoryStore:
    @staticmethod
    def snapshot(history: AudioPlacementHistory) -> dict[str, Any]:
        body = {
            "snapshot_version": FORMAT_VERSION,
            "task_owner": "TASK-026",
            "project_id": history.project_id,
            "store_revision": history.store_revision,
            "records": [history.records[key].to_dict() for key in sorted(history.records)],
            "provider_execution_authority": False,
            "paid_execution_authority": False,
            "media_bytes_embedded": False,
            "external_mutation_authority": False,
        }
        body["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def serialize(cls, history: AudioPlacementHistory) -> bytes:
        value = canonical_json_bytes(cls.snapshot(history))
        if len(value) > MAX_BYTES:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_HISTORY_SIZE",
                "History exceeds the allowed serialized byte bound",
                ProductErrorCategory.RESOURCE_EXHAUSTED,
            )
        return value

    @classmethod
    def parse(cls, document: Mapping[str, Any], *, expected_project_id: str | None = None) -> AudioPlacementHistory:
        if set(document) != _ROOT_FIELDS:
            raise ProductError("ERR_AUDIO_PLACEMENT_HISTORY_FIELDS", "History fields are not exact", ProductErrorCategory.DATA_INTEGRITY)
        body = {key: value for key, value in document.items() if key != "snapshot_sha256"}
        if document.get("snapshot_sha256") != sha256_bytes(canonical_json_bytes(body)):
            raise ProductError("ERR_AUDIO_PLACEMENT_HISTORY_CHECKSUM", "History checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
        if document.get("snapshot_version") != FORMAT_VERSION or document.get("task_owner") != "TASK-026":
            raise ProductError("ERR_AUDIO_PLACEMENT_HISTORY_VERSION", "History version/owner is unsupported", ProductErrorCategory.NOT_SUPPORTED)
        try:
            _require_int(document.get("store_revision"), "store_revision", minimum=0)
        except ValueError as exc:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_HISTORY_REVISION",
                "History store revision is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        for field in ("provider_execution_authority", "paid_execution_authority", "media_bytes_embedded", "external_mutation_authority"):
            if document.get(field) is not False:
                raise ProductError("ERR_AUDIO_PLACEMENT_HISTORY_BOUNDARY", "History violates authority/privacy boundaries", ProductErrorCategory.SECURITY)
        rows = document.get("records")
        if not isinstance(rows, list) or len(rows) > MAX_RECORDS:
            raise ProductError("ERR_AUDIO_PLACEMENT_HISTORY_RECORDS", "History records are invalid", ProductErrorCategory.DATA_INTEGRITY)
        try:
            history = AudioPlacementHistory(document["project_id"])
            for row in rows:
                if not isinstance(row, Mapping):
                    raise ValueError("compilation row is invalid")
                record = AudioPlacementCompilationRecord.from_dict(row)
                if record.compilation_id in history.records:
                    raise ValueError("duplicate compilation identity")
                history.append(record)
            if document.get("store_revision") != history.store_revision:
                raise ValueError("store revision is invalid")
            if expected_project_id is not None and history.project_id != expected_project_id:
                raise ProductError("ERR_AUDIO_PLACEMENT_PROJECT_MISMATCH", "History belongs to another Project", ProductErrorCategory.SECURITY)
            return history
        except ProductError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ProductError("ERR_AUDIO_PLACEMENT_HISTORY_INVALID", "History contains invalid compilation records", ProductErrorCategory.DATA_INTEGRITY) from exc

    @classmethod
    def parse_bytes(cls, value: bytes, *, expected_project_id: str | None = None) -> AudioPlacementHistory:
        if not isinstance(value, bytes) or not 0 < len(value) <= MAX_BYTES:
            raise ProductError("ERR_AUDIO_PLACEMENT_HISTORY_SIZE", "History size is outside the allowed bound", ProductErrorCategory.VALIDATION)
        try:
            document = json.loads(value.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_AUDIO_PLACEMENT_HISTORY_READ", "History is not UTF-8 JSON", ProductErrorCategory.DATA_INTEGRITY) from exc
        if not isinstance(document, dict):
            raise ProductError("ERR_AUDIO_PLACEMENT_HISTORY_INVALID", "History root must be an object", ProductErrorCategory.DATA_INTEGRITY)
        return cls.parse(document, expected_project_id=expected_project_id)

    @classmethod
    def load(cls, path: str | Path, *, expected_project_id: str | None = None) -> AudioPlacementHistory:
        target = Path(path)
        if target.is_symlink() or not target.is_file():
            raise ProductError("ERR_AUDIO_PLACEMENT_HISTORY_FILE", "History must be a regular non-symlink file", ProductErrorCategory.SECURITY)
        return cls.parse_bytes(target.read_bytes(), expected_project_id=expected_project_id)


__all__ = [
    "AudioPlacementCompilationRecord", "AudioPlacementHistory", "AudioPlacementHistoryStore",
    "FORMAT_ID", "FORMAT_VERSION", "MAX_BYTES", "MAX_RECORDS", "RELATIVE_PATH",
    "parse_audio_placement_plan",
]
