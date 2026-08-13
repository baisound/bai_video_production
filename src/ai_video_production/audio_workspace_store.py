"""TASK-041 crash-safe persistence for non-destructive Audio Workspace metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .atomic import AtomicJsonWriter, AtomicWriteResult
from .audio_workspace import (
    AudioCandidateDecision,
    AudioDecisionKind,
    AudioDerivationType,
    AudioDerivedAsset,
    AudioSlotKind,
    AudioWorkspaceRegistry,
    PlacementDecision,
    PlacementReview,
)
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes


_MAX_BYTES = 8 * 1024 * 1024


def _body(registry: AudioWorkspaceRegistry) -> dict[str, Any]:
    body: dict[str, Any] = {
        "snapshot_version": "1.0.0",
        "task_owner": "TASK-041",
        "decisions": [registry.decisions[key].to_dict() for key in sorted(registry.decisions)],
        "derived_assets": [registry.derived_assets[key].to_dict() for key in sorted(registry.derived_assets)],
        "placements": [registry.placements[key].to_dict() for key in sorted(registry.placements)],
        "source_media_bytes_embedded": False,
        "destructive_source_write_authority": False,
    }
    body["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def _parse(document: dict[str, Any]) -> AudioWorkspaceRegistry:
    if document.get("snapshot_version") != "1.0.0":
        raise ProductError("ERR_AUDIO_SNAPSHOT_VERSION", "Unsupported Audio Workspace snapshot version", ProductErrorCategory.DATA_INTEGRITY)
    expected = document.get("snapshot_sha256")
    body = {k: v for k, v in document.items() if k != "snapshot_sha256"}
    if expected != sha256_bytes(canonical_json_bytes(body)):
        raise ProductError("ERR_AUDIO_SNAPSHOT_CHECKSUM", "Audio Workspace snapshot checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
    if document.get("source_media_bytes_embedded") is not False or document.get("destructive_source_write_authority") is not False:
        raise ProductError("ERR_AUDIO_SNAPSHOT_BOUNDARY", "Audio Workspace snapshot violates non-destructive boundaries", ProductErrorCategory.SECURITY)
    try:
        decisions = tuple(
            AudioCandidateDecision(
                decision_id=row["decision_id"],
                candidate_id=row["candidate_id"],
                audio_slot_kind=AudioSlotKind(row["audio_slot_kind"]),
                decision=AudioDecisionKind(row["decision"]),
                actor_id=row["actor_id"],
                reason_codes=tuple(row.get("reason_codes", [])),
            )
            for row in document["decisions"]
        )
        derived = tuple(
            AudioDerivedAsset(
                derived_asset_id=row["derived_asset_id"],
                source_asset_id=row["source_asset_id"],
                source_sha256=row["source_sha256"],
                derived_sha256=row["derived_sha256"],
                derivation_type=AudioDerivationType(row["derivation_type"]),
            )
            for row in document["derived_assets"]
        )
        placements = tuple(
            PlacementReview(
                review_id=row["review_id"],
                candidate_id=row["candidate_id"],
                timeline_start_frame=int(row["timeline_start_frame"]),
                duration_frames=int(row["duration_frames"]),
                track_role=row["track_role"],
                decision=PlacementDecision(row["decision"]),
                gain_db=row.get("gain_db"),
            )
            for row in document["placements"]
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductError("ERR_AUDIO_SNAPSHOT_INVALID", "Audio Workspace snapshot contains invalid records", ProductErrorCategory.DATA_INTEGRITY) from exc
    registry = AudioWorkspaceRegistry()
    for item in decisions:
        registry.add_decision(item)
    for item in derived:
        registry.add_derived_asset(item)
    for item in placements:
        registry.add_placement(item)
    if len(registry.decisions) != len(document["decisions"]) or len(registry.derived_assets) != len(document["derived_assets"]) or len(registry.placements) != len(document["placements"]):
        raise ProductError("ERR_AUDIO_SNAPSHOT_DUPLICATE_ID", "Audio Workspace snapshot contains duplicate identities", ProductErrorCategory.DATA_INTEGRITY)
    return registry


class AudioWorkspaceSnapshotStore:
    @staticmethod
    def snapshot(registry: AudioWorkspaceRegistry) -> dict[str, Any]:
        return _body(registry)

    @staticmethod
    def load(path: str | Path) -> AudioWorkspaceRegistry:
        target = Path(path)
        if target.is_symlink() or not target.is_file():
            raise ProductError("ERR_AUDIO_SNAPSHOT_FILE_INVALID", "Audio Workspace snapshot must be a regular non-symlink file", ProductErrorCategory.VALIDATION)
        size = target.stat().st_size
        if size <= 0 or size > _MAX_BYTES:
            raise ProductError("ERR_AUDIO_SNAPSHOT_SIZE", "Audio Workspace snapshot size is outside the allowed bound", ProductErrorCategory.VALIDATION, details={"size_bytes": size})
        try:
            value = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_AUDIO_SNAPSHOT_READ", "Audio Workspace snapshot could not be read as UTF-8 JSON", ProductErrorCategory.DATA_INTEGRITY) from exc
        if not isinstance(value, dict):
            raise ProductError("ERR_AUDIO_SNAPSHOT_INVALID", "Audio Workspace snapshot root must be an object", ProductErrorCategory.DATA_INTEGRITY)
        return _parse(value)

    @staticmethod
    def save(path: str | Path, registry: AudioWorkspaceRegistry, *, expected_previous_snapshot_sha256: str | None = None) -> AtomicWriteResult:
        target = Path(path)
        if target.is_symlink():
            raise ProductError("ERR_AUDIO_SNAPSHOT_FILE_INVALID", "Refusing to replace a symlink Audio Workspace snapshot", ProductErrorCategory.SECURITY)
        if target.exists():
            if not target.is_file():
                raise ProductError("ERR_AUDIO_SNAPSHOT_FILE_INVALID", "Audio Workspace target must be a regular file", ProductErrorCategory.VALIDATION)
            if expected_previous_snapshot_sha256 is None:
                raise ProductError("ERR_AUDIO_SNAPSHOT_CAS_REQUIRED", "Replacing an Audio Workspace snapshot requires its exact previous checksum", ProductErrorCategory.AUTHORIZATION)
            current = _body(AudioWorkspaceSnapshotStore.load(target))["snapshot_sha256"]
            if current != expected_previous_snapshot_sha256:
                raise ProductError("ERR_AUDIO_SNAPSHOT_REVISION_CONFLICT", "Audio Workspace snapshot changed before save; reload before retry", ProductErrorCategory.STATE, details={"current_snapshot_sha256": current})
        elif expected_previous_snapshot_sha256 is not None:
            raise ProductError("ERR_AUDIO_SNAPSHOT_PREVIOUS_MISSING", "Expected previous Audio Workspace snapshot does not exist", ProductErrorCategory.STATE)
        document = _body(registry)
        return AtomicJsonWriter.write(target, document, validator=lambda value: _parse(value))
