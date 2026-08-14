"""TASK-037 crash-safe snapshot persistence for production-control relationship state.

The store persists only TASK-037/039 relationship metadata. Media bytes remain
owned by the canonical Asset Registry. Existing snapshots require an exact
compare-and-swap checksum before replacement.
"""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
from typing import Any, Iterator

from .atomic import AtomicJsonWriter, AtomicWriteResult
from .errors import ProductError, ProductErrorCategory
from .production_control import (
    AssetCandidate,
    CandidateLifecycle,
    DependencyEdge,
    DependencyKind,
    EntityRef,
    EntityType,
    ProductionControlRegistry,
    SceneAssetSlot,
    SlotKind,
    SlotStatus,
    StaleState,
)
from .serialization import canonical_json_bytes, sha256_bytes


_MAX_SNAPSHOT_BYTES = 16 * 1024 * 1024


@contextmanager
def _exclusive_snapshot_lock(target: Path) -> Iterator[None]:
    """Serialize the CAS check and replace across local Product processes."""

    lock_path = target.with_name(f".{target.name}.lock")
    if lock_path.is_symlink() or (lock_path.exists() and not lock_path.is_file()):
        raise ProductError(
            "ERR_PRODUCTION_SNAPSHOT_LOCK_INVALID",
            "Production-control lock must be a regular non-symlink file",
            ProductErrorCategory.SECURITY,
        )
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        locked = False
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            locked = True
            yield
        finally:
            if locked:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _body(registry: ProductionControlRegistry) -> dict[str, Any]:
    body: dict[str, Any] = {
        "snapshot_version": "1.0.0",
        "task_owner": "TASK-037",
        "slots": [registry.slots[key].to_dict() for key in sorted(registry.slots)],
        "candidates": [registry.candidates[key].to_dict() for key in sorted(registry.candidates)],
        "dependencies": [registry.edges[key].to_dict() for key in sorted(registry.edges)],
        "media_bytes_embedded": False,
        "physical_delete_authority": False,
    }
    body["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def _parse(document: dict[str, Any]) -> ProductionControlRegistry:
    if document.get("snapshot_version") != "1.0.0":
        raise ProductError("ERR_PRODUCTION_SNAPSHOT_VERSION", "Unsupported production-control snapshot version", ProductErrorCategory.DATA_INTEGRITY)
    expected = document.get("snapshot_sha256")
    body = {key: value for key, value in document.items() if key != "snapshot_sha256"}
    actual = sha256_bytes(canonical_json_bytes(body))
    if expected != actual:
        raise ProductError("ERR_PRODUCTION_SNAPSHOT_CHECKSUM", "Production-control snapshot checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
    if document.get("media_bytes_embedded") is not False or document.get("physical_delete_authority") is not False:
        raise ProductError("ERR_PRODUCTION_SNAPSHOT_BOUNDARY", "Production-control snapshot violates storage/retention boundaries", ProductErrorCategory.SECURITY)

    try:
        slots = {
            row["slot_id"]: SceneAssetSlot(
                slot_id=row["slot_id"],
                project_id=row["project_id"],
                scene_id=row["scene_id"],
                slot_kind=SlotKind(row["slot_kind"]),
                required=bool(row["required"]),
                status=SlotStatus(row["status"]),
                locked_candidate_id=row.get("locked_candidate_id"),
                stale_state=StaleState(row.get("stale_state", "CURRENT")),
                stale_root_cause_ref=row.get("stale_root_cause_ref"),
                revision=int(row.get("revision", 1)),
            )
            for row in document["slots"]
        }
        candidates = {
            row["candidate_id"]: AssetCandidate(
                candidate_id=row["candidate_id"],
                slot_id=row["slot_id"],
                asset_id=row["asset_id"],
                asset_sha256=row["asset_sha256"],
                candidate_version=int(row["candidate_version"]),
                lifecycle_state=CandidateLifecycle(row["lifecycle_state"]),
                generation_job_id=row.get("generation_job_id"),
                parent_candidate_id=row.get("parent_candidate_id"),
                supersedes=row.get("supersedes"),
            )
            for row in document["candidates"]
        }
        edges = {
            row["edge_id"]: DependencyEdge(
                edge_id=row["edge_id"],
                from_ref=EntityRef(EntityType(row["from_entity_type"]), row["from_entity_id"]),
                to_ref=EntityRef(EntityType(row["to_entity_type"]), row["to_entity_id"]),
                dependency_kind=DependencyKind(row["dependency_kind"]),
                from_hash=row.get("from_hash"),
                continuity_boundary=row.get("continuity_boundary"),
            )
            for row in document["dependencies"]
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductError("ERR_PRODUCTION_SNAPSHOT_INVALID", "Production-control snapshot contains invalid records", ProductErrorCategory.DATA_INTEGRITY) from exc

    if len(slots) != len(document["slots"]) or len(candidates) != len(document["candidates"]) or len(edges) != len(document["dependencies"]):
        raise ProductError("ERR_PRODUCTION_SNAPSHOT_DUPLICATE_ID", "Production-control snapshot contains duplicate identities", ProductErrorCategory.DATA_INTEGRITY)

    for candidate in candidates.values():
        if candidate.slot_id not in slots:
            raise ProductError("ERR_PRODUCTION_SNAPSHOT_ORPHAN_CANDIDATE", "Candidate references a missing Scene Asset Slot", ProductErrorCategory.DATA_INTEGRITY)
    for slot in slots.values():
        if slot.locked_candidate_id is not None:
            candidate = candidates.get(slot.locked_candidate_id)
            expected_lifecycle = (
                CandidateLifecycle.STALE if slot.status is SlotStatus.STALE else CandidateLifecycle.LOCKED
            )
            if (
                candidate is None
                or candidate.slot_id != slot.slot_id
                or candidate.lifecycle_state is not expected_lifecycle
            ):
                raise ProductError("ERR_PRODUCTION_SNAPSHOT_LOCK_INCONSISTENT", "Locked Slot/Candidate relationship is inconsistent", ProductErrorCategory.DATA_INTEGRITY)

    registry = ProductionControlRegistry()
    registry.slots.update(slots)
    registry.candidates.update(candidates)
    # Reuse domain cycle validation instead of trusting serialized graph order.
    for edge_id in sorted(edges):
        registry.add_dependency(edges[edge_id])
    return registry


class ProductionControlSnapshotStore:
    @staticmethod
    def snapshot(registry: ProductionControlRegistry) -> dict[str, Any]:
        return _body(registry)

    @staticmethod
    def load(path: str | Path) -> ProductionControlRegistry:
        target = Path(path)
        if target.is_symlink() or not target.is_file():
            raise ProductError("ERR_PRODUCTION_SNAPSHOT_FILE_INVALID", "Snapshot must be a regular non-symlink file", ProductErrorCategory.VALIDATION)
        size = target.stat().st_size
        if size <= 0 or size > _MAX_SNAPSHOT_BYTES:
            raise ProductError("ERR_PRODUCTION_SNAPSHOT_SIZE", "Snapshot size is outside the allowed bound", ProductErrorCategory.VALIDATION, details={"size_bytes": size})
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_PRODUCTION_SNAPSHOT_READ", "Snapshot could not be read as UTF-8 JSON", ProductErrorCategory.DATA_INTEGRITY) from exc
        if not isinstance(document, dict):
            raise ProductError("ERR_PRODUCTION_SNAPSHOT_INVALID", "Snapshot root must be an object", ProductErrorCategory.DATA_INTEGRITY)
        return _parse(document)

    @staticmethod
    def save(
        path: str | Path,
        registry: ProductionControlRegistry,
        *,
        expected_previous_snapshot_sha256: str | None = None,
    ) -> AtomicWriteResult:
        target = Path(path)
        with _exclusive_snapshot_lock(target):
            if target.is_symlink():
                raise ProductError("ERR_PRODUCTION_SNAPSHOT_FILE_INVALID", "Refusing to replace a symlink snapshot path", ProductErrorCategory.SECURITY)
            if target.exists():
                if not target.is_file():
                    raise ProductError("ERR_PRODUCTION_SNAPSHOT_FILE_INVALID", "Snapshot target must be a regular file", ProductErrorCategory.VALIDATION)
                if expected_previous_snapshot_sha256 is None:
                    raise ProductError(
                        "ERR_PRODUCTION_SNAPSHOT_CAS_REQUIRED",
                        "Replacing an existing snapshot requires its exact previous checksum",
                        ProductErrorCategory.AUTHORIZATION,
                    )
                current = ProductionControlSnapshotStore.snapshot(ProductionControlSnapshotStore.load(target))["snapshot_sha256"]
                if current != expected_previous_snapshot_sha256:
                    raise ProductError(
                        "ERR_PRODUCTION_SNAPSHOT_REVISION_CONFLICT",
                        "Production-control snapshot changed before save; reload before retry",
                        ProductErrorCategory.STATE,
                        details={"current_snapshot_sha256": current},
                    )
            elif expected_previous_snapshot_sha256 is not None:
                raise ProductError(
                    "ERR_PRODUCTION_SNAPSHOT_PREVIOUS_MISSING",
                    "Expected previous snapshot does not exist",
                    ProductErrorCategory.STATE,
                )

            document = _body(registry)
            return AtomicJsonWriter.write(target, document, validator=lambda value: _parse(value))
