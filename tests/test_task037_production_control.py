from __future__ import annotations

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
    SlotStatus,
    StaleState,
)


SHA = "sha256:" + "a" * 64


def registry_with_slot() -> ProductionControlRegistry:
    registry = ProductionControlRegistry()
    registry.add_slot(SceneAssetSlot("slot-1", "project-1", "scene-1", SlotKind.VIDEO, True))
    return registry


def candidate(version: int = 1, candidate_id: str = "candidate-1") -> AssetCandidate:
    return AssetCandidate(candidate_id, "slot-1", f"asset-{version}", SHA, version)


def test_candidate_versions_are_append_only_without_gaps():
    registry = registry_with_slot()
    registry.add_candidate(candidate())
    with pytest.raises(ProductError) as exc:
        registry.add_candidate(candidate(3, "candidate-3"))
    assert exc.value.code == "ERR_PRODUCTION_CANDIDATE_VERSION_CONFLICT"


def test_human_accept_then_expected_revision_lock_is_required():
    registry = registry_with_slot()
    slot = registry.add_candidate(candidate())
    registry.transition_candidate("candidate-1", CandidateLifecycle.READY_FOR_AUDIT)
    registry.transition_candidate("candidate-1", CandidateLifecycle.ACCEPTED)
    current = registry.slots["slot-1"]
    assert current.status == SlotStatus.ACCEPTED
    with pytest.raises(ProductError) as exc:
        registry.lock_candidate(slot_id="slot-1", candidate_id="candidate-1", expected_revision=slot.revision)
    assert exc.value.code == "ERR_PRODUCTION_SLOT_REVISION_CONFLICT"
    locked = registry.lock_candidate(slot_id="slot-1", candidate_id="candidate-1", expected_revision=current.revision)
    assert locked.status == SlotStatus.LOCKED
    assert registry.candidates["candidate-1"].lifecycle_state == CandidateLifecycle.LOCKED


def test_rejected_candidate_is_not_physically_deleted_or_reaccepted():
    registry = registry_with_slot()
    registry.add_candidate(candidate())
    registry.transition_candidate("candidate-1", CandidateLifecycle.READY_FOR_AUDIT)
    rejected = registry.transition_candidate("candidate-1", CandidateLifecycle.REJECTED)
    assert rejected.candidate_id in registry.candidates
    with pytest.raises(ProductError) as exc:
        registry.transition_candidate("candidate-1", CandidateLifecycle.ACCEPTED)
    assert exc.value.code == "ERR_PRODUCTION_CANDIDATE_TRANSITION_INVALID"


def test_dependency_cycle_is_rejected():
    registry = ProductionControlRegistry()
    a = EntityRef(EntityType.SCENE, "scene-a")
    b = EntityRef(EntityType.SCENE, "scene-b")
    registry.add_dependency(DependencyEdge("edge-1", a, b, DependencyKind.USES))
    with pytest.raises(ProductError) as exc:
        registry.add_dependency(DependencyEdge("edge-2", b, a, DependencyKind.USES))
    assert exc.value.code == "ERR_PRODUCTION_DEPENDENCY_CYCLE"


def test_stale_propagates_transitively_without_regeneration():
    registry = registry_with_slot()
    registry.add_candidate(candidate())
    upstream = EntityRef(EntityType.CONTRACT, "contract-1")
    slot_ref = EntityRef(EntityType.SLOT, "slot-1")
    candidate_ref = EntityRef(EntityType.CANDIDATE, "candidate-1")
    registry.add_dependency(DependencyEdge("edge-1", upstream, slot_ref, DependencyKind.USES))
    registry.add_dependency(DependencyEdge("edge-2", slot_ref, candidate_ref, DependencyKind.GENERATED_FROM))
    result = registry.mark_stale(upstream)
    assert [item.key for item in result.affected] == ["SLOT:slot-1", "CANDIDATE:candidate-1"]
    assert registry.slots["slot-1"].stale_state == StaleState.STALE
    assert registry.candidates["candidate-1"].lifecycle_state == CandidateLifecycle.STALE
    assert result.to_dict()["automatic_regeneration_started"] is False


def test_candidate_registration_automatically_binds_slot_dependency_for_stale_propagation():
    registry = registry_with_slot()
    registry.add_candidate(candidate())
    root = EntityRef(EntityType.CONTRACT, "contract-auto")
    slot_ref = EntityRef(EntityType.SLOT, "slot-1")
    registry.add_dependency(DependencyEdge("edge-auto-upstream", root, slot_ref, DependencyKind.USES))
    result = registry.mark_stale(root)
    assert [item.key for item in result.affected] == ["SLOT:slot-1", "CANDIDATE:candidate-1"]
    assert registry.candidates["candidate-1"].lifecycle_state is CandidateLifecycle.STALE
    automatic = [edge for edge in registry.edges.values() if edge.to_ref == EntityRef(EntityType.CANDIDATE, "candidate-1")]
    assert any(edge.from_ref == slot_ref for edge in automatic)
