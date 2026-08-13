from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.production_control import (
    AssetCandidate,
    CandidateLifecycle,
    DependencyEdge,
    DependencyKind,
    EntityRef,
    EntityType,
    ProductionControlRegistry,
    SceneAssetSlot,
    SlotKind,
)
from ai_video_production.production_control_store import ProductionControlSnapshotStore
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


SHA = "sha256:" + "a" * 64


def populated_registry():
    r = ProductionControlRegistry()
    r.add_slot(SceneAssetSlot("slot:SC01:VIDEO", "project-1", "SC01", SlotKind.VIDEO, True))
    r.add_candidate(AssetCandidate("candidate-1", "slot:SC01:VIDEO", "asset-1", SHA, 1))
    r.transition_candidate("candidate-1", CandidateLifecycle.READY_FOR_AUDIT)
    r.transition_candidate("candidate-1", CandidateLifecycle.ACCEPTED)
    slot = r.slots["slot:SC01:VIDEO"]
    r.lock_candidate(slot_id=slot.slot_id, candidate_id="candidate-1", expected_revision=slot.revision)
    r.add_dependency(DependencyEdge(
        "edge-1", EntityRef(EntityType.PLAN, "plan-1"), EntityRef(EntityType.SLOT, "slot:SC01:VIDEO"), DependencyKind.USES,
    ))
    return r


def test_snapshot_round_trip_is_deterministic_and_preserves_locked_trace(tmp_path: Path):
    path = tmp_path / "production-control.json"
    registry = populated_registry()
    first = ProductionControlSnapshotStore.snapshot(registry)
    ProductionControlSnapshotStore.save(path, registry)
    loaded = ProductionControlSnapshotStore.load(path)
    second = ProductionControlSnapshotStore.snapshot(loaded)
    assert first == second
    assert loaded.locked_asset_trace("slot:SC01:VIDEO")["asset_sha256"] == SHA


def test_existing_snapshot_requires_compare_and_swap_checksum(tmp_path: Path):
    path = tmp_path / "production-control.json"
    registry = populated_registry()
    ProductionControlSnapshotStore.save(path, registry)
    with pytest.raises(ProductError) as exc:
        ProductionControlSnapshotStore.save(path, registry)
    assert exc.value.code == "ERR_PRODUCTION_SNAPSHOT_CAS_REQUIRED"


def test_compare_and_swap_rejects_stale_writer(tmp_path: Path):
    path = tmp_path / "production-control.json"
    registry = populated_registry()
    ProductionControlSnapshotStore.save(path, registry)
    with pytest.raises(ProductError) as exc:
        ProductionControlSnapshotStore.save(path, registry, expected_previous_snapshot_sha256="sha256:" + "b" * 64)
    assert exc.value.code == "ERR_PRODUCTION_SNAPSHOT_REVISION_CONFLICT"


def test_exact_previous_checksum_allows_atomic_replacement(tmp_path: Path):
    path = tmp_path / "production-control.json"
    registry = populated_registry()
    ProductionControlSnapshotStore.save(path, registry)
    checksum = ProductionControlSnapshotStore.snapshot(registry)["snapshot_sha256"]
    registry.add_slot(SceneAssetSlot("slot:SC02:VIDEO", "project-1", "SC02", SlotKind.VIDEO, True))
    ProductionControlSnapshotStore.save(path, registry, expected_previous_snapshot_sha256=checksum)
    loaded = ProductionControlSnapshotStore.load(path)
    assert "slot:SC02:VIDEO" in loaded.slots


def test_checksum_tampering_is_detected(tmp_path: Path):
    path = tmp_path / "production-control.json"
    registry = populated_registry()
    ProductionControlSnapshotStore.save(path, registry)
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["slots"][0]["required"] = False
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        ProductionControlSnapshotStore.load(path)
    assert exc.value.code == "ERR_PRODUCTION_SNAPSHOT_CHECKSUM"


def test_orphan_candidate_is_rejected_even_with_recomputed_checksum(tmp_path: Path):
    path = tmp_path / "production-control.json"
    doc = ProductionControlSnapshotStore.snapshot(populated_registry())
    doc["slots"] = []
    body = {key: value for key, value in doc.items() if key != "snapshot_sha256"}
    doc["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        ProductionControlSnapshotStore.load(path)
    assert exc.value.code == "ERR_PRODUCTION_SNAPSHOT_ORPHAN_CANDIDATE"


def test_symlink_snapshot_path_is_rejected(tmp_path: Path):
    target = tmp_path / "real.json"
    ProductionControlSnapshotStore.save(target, populated_registry())
    link = tmp_path / "link.json"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink unavailable")
    with pytest.raises(ProductError) as exc:
        ProductionControlSnapshotStore.load(link)
    assert exc.value.code == "ERR_PRODUCTION_SNAPSHOT_FILE_INVALID"
