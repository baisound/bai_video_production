"""Crash-safe append-only persistence for TASK-042 Quick intent authority."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .atomic import AtomicJsonWriter, AtomicWriteResult
from .errors import ProductError, ProductErrorCategory
from .production_control_store import _exclusive_snapshot_lock
from .quick_generation import QuickGenerationIntent, QuickGenerationRegistry
from .serialization import canonical_json_bytes, sha256_bytes


_MAX_BYTES = 8 * 1024 * 1024
_FIELDS = {
    "snapshot_version", "task_owner", "project_id", "revision", "intents",
    "approved_plan_authority_claimed", "human_go_authority_claimed",
    "provider_execution_authorized", "candidate_creation_authorized", "snapshot_sha256",
}


def _body(registry: QuickGenerationRegistry) -> dict[str, Any]:
    body: dict[str, Any] = {
        "snapshot_version": "1.0.0", "task_owner": "TASK-042",
        "project_id": registry.project_id, "revision": len(registry.intents),
        "intents": [row.to_dict() for row in registry.intents],
        "approved_plan_authority_claimed": False, "human_go_authority_claimed": False,
        "provider_execution_authorized": False, "candidate_creation_authorized": False,
    }
    body["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def _parse(document: dict[str, Any], project_id: str) -> QuickGenerationRegistry:
    if not isinstance(document, dict) or set(document) != _FIELDS or document.get("snapshot_version") != "1.0.0" or document.get("task_owner") != "TASK-042" or document.get("project_id") != project_id:
        raise ProductError("ERR_QUICK_SNAPSHOT_INVALID", "Quick snapshot identity/fields are invalid", ProductErrorCategory.DATA_INTEGRITY)
    expected = document.get("snapshot_sha256")
    body = {key: value for key, value in document.items() if key != "snapshot_sha256"}
    if expected != sha256_bytes(canonical_json_bytes(body)):
        raise ProductError("ERR_QUICK_SNAPSHOT_CHECKSUM", "Quick snapshot checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
    if any(document.get(name) is not False for name in (
        "approved_plan_authority_claimed", "human_go_authority_claimed",
        "provider_execution_authorized", "candidate_creation_authorized",
    )):
        raise ProductError("ERR_QUICK_SNAPSHOT_AUTHORITY", "Quick snapshot claims prohibited authority", ProductErrorCategory.SECURITY)
    rows = document.get("intents")
    if not isinstance(rows, list) or isinstance(document.get("revision"), bool) or document.get("revision") != len(rows):
        raise ProductError("ERR_QUICK_SNAPSHOT_REVISION", "Quick snapshot revision is invalid", ProductErrorCategory.DATA_INTEGRITY)
    registry = QuickGenerationRegistry(project_id)
    try:
        for raw in rows:
            intent = QuickGenerationIntent.from_dict(raw)
            if intent.expected_quick_snapshot_sha256 != _body(registry)["snapshot_sha256"]:
                raise ProductError("ERR_QUICK_SNAPSHOT_CHAIN", "Quick append-only snapshot chain is invalid", ProductErrorCategory.DATA_INTEGRITY)
            registry.add_intent(intent)
    except ProductError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductError("ERR_QUICK_SNAPSHOT_INVALID", "Quick snapshot contains an invalid intent", ProductErrorCategory.DATA_INTEGRITY) from exc
    if _body(registry)["snapshot_sha256"] != expected:
        raise ProductError("ERR_QUICK_SNAPSHOT_DOMAIN_HASH", "Quick snapshot identity changed during recovery", ProductErrorCategory.DATA_INTEGRITY)
    return registry


class QuickGenerationSnapshotStore:
    @staticmethod
    def snapshot(registry: QuickGenerationRegistry) -> dict[str, Any]:
        return _body(registry)

    @staticmethod
    def load(path: str | Path, *, project_id: str) -> QuickGenerationRegistry:
        target = Path(path)
        if target.is_symlink() or not target.is_file():
            raise ProductError("ERR_QUICK_SNAPSHOT_FILE_INVALID", "Quick snapshot must be a regular non-symlink file", ProductErrorCategory.VALIDATION)
        size = target.stat().st_size
        if size <= 0 or size > _MAX_BYTES:
            raise ProductError("ERR_QUICK_SNAPSHOT_SIZE", "Quick snapshot size is outside the allowed bound", ProductErrorCategory.VALIDATION, details={"size_bytes": size})
        try:
            value = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_QUICK_SNAPSHOT_READ", "Quick snapshot could not be read as UTF-8 JSON", ProductErrorCategory.DATA_INTEGRITY) from exc
        return _parse(value, project_id)

    @staticmethod
    def save(
        path: str | Path, registry: QuickGenerationRegistry, *,
        expected_previous_snapshot_sha256: str | None = None,
    ) -> AtomicWriteResult:
        target = Path(path)
        with _exclusive_snapshot_lock(target):
            if target.is_symlink():
                raise ProductError("ERR_QUICK_SNAPSHOT_FILE_INVALID", "Refusing to replace a symlink Quick snapshot", ProductErrorCategory.SECURITY)
            if target.exists():
                if not target.is_file():
                    raise ProductError("ERR_QUICK_SNAPSHOT_FILE_INVALID", "Quick snapshot target must be a regular file", ProductErrorCategory.VALIDATION)
                if expected_previous_snapshot_sha256 is None:
                    raise ProductError("ERR_QUICK_SNAPSHOT_CAS_REQUIRED", "Replacing Quick snapshot requires exact previous checksum", ProductErrorCategory.AUTHORIZATION)
                current = _body(QuickGenerationSnapshotStore.load(target, project_id=registry.project_id))["snapshot_sha256"]
                if current != expected_previous_snapshot_sha256:
                    raise ProductError("ERR_QUICK_SNAPSHOT_REVISION_CONFLICT", "Quick snapshot changed before save", ProductErrorCategory.STATE, details={"current_snapshot_sha256": current})
            elif expected_previous_snapshot_sha256 is not None:
                raise ProductError("ERR_QUICK_SNAPSHOT_PREVIOUS_MISSING", "Expected previous Quick snapshot does not exist", ProductErrorCategory.STATE)
            return AtomicJsonWriter.write(target, _body(registry), validator=lambda value: _parse(value, registry.project_id))


__all__ = ["QuickGenerationSnapshotStore"]
