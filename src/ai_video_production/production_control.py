"""TASK-037/039 production-control domain foundation.

The module stores relationship state only.  It does not own media bytes, secure
ingest, file deletion, generation execution, or Human approval UI.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import re
from typing import Any, Iterable

from .errors import ProductError, ProductErrorCategory


_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,159}")
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _sha(value: str, name: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


class SlotKind(str, Enum):
    START_FRAME = "START_FRAME"
    END_FRAME = "END_FRAME"
    CHARACTER_REFERENCE = "CHARACTER_REFERENCE"
    SPACE_REFERENCE = "SPACE_REFERENCE"
    COMPOSITION_REFERENCE = "COMPOSITION_REFERENCE"
    VIDEO = "VIDEO"
    VFX = "VFX"
    SE = "SE"
    BGM = "BGM"
    NARRATION = "NARRATION"
    OTHER = "OTHER"


class SlotStatus(str, Enum):
    EMPTY = "EMPTY"
    CANDIDATES_AVAILABLE = "CANDIDATES_AVAILABLE"
    ACCEPTED = "ACCEPTED"
    LOCKED = "LOCKED"
    STALE = "STALE"


class StaleState(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"


class CandidateLifecycle(str, Enum):
    CREATED = "CREATED"
    READY_FOR_AUDIT = "READY_FOR_AUDIT"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    ALTERNATE_USE = "ALTERNATE_USE"
    LOCKED = "LOCKED"
    STALE = "STALE"


class DependencyKind(str, Enum):
    USES = "USES"
    DERIVED_FROM = "DERIVED_FROM"
    CONTINUITY = "CONTINUITY"
    GENERATED_FROM = "GENERATED_FROM"
    AUDITED_AGAINST = "AUDITED_AGAINST"


class EntityType(str, Enum):
    PLAN = "PLAN"
    SCENE = "SCENE"
    SLOT = "SLOT"
    CANDIDATE = "CANDIDATE"
    ASSET = "ASSET"
    CONTRACT = "CONTRACT"
    PROMPT = "PROMPT"


@dataclass(frozen=True, slots=True)
class EntityRef:
    entity_type: EntityType
    entity_id: str

    def __post_init__(self) -> None:
        _id(self.entity_id, "entity_id")

    @property
    def key(self) -> str:
        return f"{self.entity_type.value}:{self.entity_id}"


@dataclass(frozen=True, slots=True)
class SceneAssetSlot:
    slot_id: str
    project_id: str
    scene_id: str
    slot_kind: SlotKind
    required: bool
    status: SlotStatus = SlotStatus.EMPTY
    locked_candidate_id: str | None = None
    stale_state: StaleState = StaleState.CURRENT
    stale_root_cause_ref: str | None = None
    revision: int = 1

    def __post_init__(self) -> None:
        _id(self.slot_id, "slot_id")
        _id(self.project_id, "project_id")
        _id(self.scene_id, "scene_id")
        if self.locked_candidate_id is not None:
            _id(self.locked_candidate_id, "locked_candidate_id")
        if self.stale_root_cause_ref is not None:
            _id(self.stale_root_cause_ref, "stale_root_cause_ref")
        if self.revision < 1:
            raise ValueError("revision must be >= 1")
        if self.status is SlotStatus.LOCKED and self.locked_candidate_id is None:
            raise ValueError("LOCKED slot requires locked_candidate_id")
        if self.stale_state is StaleState.STALE and self.status is not SlotStatus.STALE:
            raise ValueError("STALE slot must use STALE status")

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "project_id": self.project_id,
            "scene_id": self.scene_id,
            "slot_kind": self.slot_kind.value,
            "required": self.required,
            "status": self.status.value,
            "locked_candidate_id": self.locked_candidate_id,
            "stale_state": self.stale_state.value,
            "stale_root_cause_ref": self.stale_root_cause_ref,
            "revision": self.revision,
        }


@dataclass(frozen=True, slots=True)
class AssetCandidate:
    candidate_id: str
    slot_id: str
    asset_id: str
    asset_sha256: str
    candidate_version: int
    lifecycle_state: CandidateLifecycle = CandidateLifecycle.CREATED
    generation_job_id: str | None = None
    parent_candidate_id: str | None = None
    supersedes: str | None = None

    def __post_init__(self) -> None:
        _id(self.candidate_id, "candidate_id")
        _id(self.slot_id, "slot_id")
        _id(self.asset_id, "asset_id")
        _sha(self.asset_sha256, "asset_sha256")
        if self.candidate_version < 1:
            raise ValueError("candidate_version must be >= 1")
        for name, value in (
            ("generation_job_id", self.generation_job_id),
            ("parent_candidate_id", self.parent_candidate_id),
            ("supersedes", self.supersedes),
        ):
            if value is not None:
                _id(value, name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "slot_id": self.slot_id,
            "asset_id": self.asset_id,
            "asset_sha256": self.asset_sha256,
            "candidate_version": self.candidate_version,
            "lifecycle_state": self.lifecycle_state.value,
            "generation_job_id": self.generation_job_id,
            "parent_candidate_id": self.parent_candidate_id,
            "supersedes": self.supersedes,
        }


@dataclass(frozen=True, slots=True)
class DependencyEdge:
    edge_id: str
    from_ref: EntityRef
    to_ref: EntityRef
    dependency_kind: DependencyKind
    from_hash: str | None = None
    continuity_boundary: str | None = None

    def __post_init__(self) -> None:
        _id(self.edge_id, "edge_id")
        if self.from_ref == self.to_ref:
            raise ValueError("dependency edge cannot self-reference")
        if self.from_hash is not None:
            _sha(self.from_hash, "from_hash")
        if self.continuity_boundary not in {None, "DIRECT_CONTINUATION", "SOFT_CONTINUITY", "DISCONTINUOUS"}:
            raise ValueError("continuity_boundary is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "from_entity_type": self.from_ref.entity_type.value,
            "from_entity_id": self.from_ref.entity_id,
            "from_hash": self.from_hash,
            "to_entity_type": self.to_ref.entity_type.value,
            "to_entity_id": self.to_ref.entity_id,
            "dependency_kind": self.dependency_kind.value,
            "continuity_boundary": self.continuity_boundary,
        }


@dataclass(frozen=True, slots=True)
class StalePropagationResult:
    root: EntityRef
    affected: tuple[EntityRef, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": {"type": self.root.entity_type.value, "id": self.root.entity_id},
            "affected": [{"type": item.entity_type.value, "id": item.entity_id} for item in self.affected],
            "automatic_regeneration_started": False,
            "human_resolution_required": bool(self.affected),
        }


_TRANSITIONS: dict[CandidateLifecycle, frozenset[CandidateLifecycle]] = {
    CandidateLifecycle.CREATED: frozenset({CandidateLifecycle.READY_FOR_AUDIT, CandidateLifecycle.STALE}),
    CandidateLifecycle.READY_FOR_AUDIT: frozenset({
        CandidateLifecycle.ACCEPTED,
        CandidateLifecycle.REJECTED,
        CandidateLifecycle.ALTERNATE_USE,
        CandidateLifecycle.STALE,
    }),
    CandidateLifecycle.ACCEPTED: frozenset({CandidateLifecycle.LOCKED, CandidateLifecycle.STALE}),
    CandidateLifecycle.LOCKED: frozenset({CandidateLifecycle.STALE}),
    CandidateLifecycle.REJECTED: frozenset(),
    CandidateLifecycle.ALTERNATE_USE: frozenset(),
    CandidateLifecycle.STALE: frozenset(),
}


class ProductionControlRegistry:
    """In-memory deterministic foundation for TASK-037/039 contracts.

    Persistence, cross-process locking and physical retention are deliberately out
    of scope for this foundation slice.
    """

    @staticmethod
    def _slot_candidate_edge_id(slot_id: str, candidate_id: str) -> str:
        digest = hashlib.sha256(f"{slot_id}\0{candidate_id}".encode("utf-8")).hexdigest()[:20]
        return f"dep:slot-candidate:{digest}"

    def __init__(self) -> None:
        self.slots: dict[str, SceneAssetSlot] = {}
        self.candidates: dict[str, AssetCandidate] = {}
        self.edges: dict[str, DependencyEdge] = {}

    def add_slot(self, slot: SceneAssetSlot) -> None:
        if slot.slot_id in self.slots:
            raise ProductError("ERR_PRODUCTION_SLOT_CONFLICT", "slot_id already exists", ProductErrorCategory.STATE)
        self.slots[slot.slot_id] = slot

    def add_candidate(self, candidate: AssetCandidate) -> SceneAssetSlot:
        slot = self.slots.get(candidate.slot_id)
        if slot is None:
            raise ProductError("ERR_PRODUCTION_SLOT_NOT_FOUND", "candidate slot does not exist", ProductErrorCategory.STATE)
        if candidate.candidate_id in self.candidates:
            raise ProductError("ERR_PRODUCTION_CANDIDATE_CONFLICT", "candidate_id already exists", ProductErrorCategory.STATE)
        versions = [item.candidate_version for item in self.candidates.values() if item.slot_id == candidate.slot_id]
        expected = (max(versions) + 1) if versions else 1
        if candidate.candidate_version != expected:
            raise ProductError(
                "ERR_PRODUCTION_CANDIDATE_VERSION_CONFLICT",
                "candidate_version must append without overwriting or gaps",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"expected_version": expected},
            )
        if slot.status in {SlotStatus.LOCKED, SlotStatus.STALE}:
            raise ProductError(
                "ERR_PRODUCTION_SLOT_NOT_MUTABLE",
                "cannot append Candidate to a locked or stale Slot without Human resolution",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        slot_ref = EntityRef(EntityType.SLOT, slot.slot_id)
        candidate_ref = EntityRef(EntityType.CANDIDATE, candidate.candidate_id)
        edge = DependencyEdge(
            edge_id=self._slot_candidate_edge_id(slot.slot_id, candidate.candidate_id),
            from_ref=slot_ref,
            to_ref=candidate_ref,
            dependency_kind=DependencyKind.USES,
            from_hash=candidate.asset_sha256,
        )
        if edge.edge_id in self.edges:
            raise ProductError(
                "ERR_PRODUCTION_DEPENDENCY_CONFLICT",
                "automatic Slot/Candidate dependency identity already exists",
                ProductErrorCategory.STATE,
            )
        if self._path_exists(candidate_ref, slot_ref):
            raise ProductError(
                "ERR_PRODUCTION_DEPENDENCY_CYCLE",
                "Candidate registration would create a dependency cycle",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        self.candidates[candidate.candidate_id] = candidate
        updated = replace(slot, status=SlotStatus.CANDIDATES_AVAILABLE, revision=slot.revision + 1)
        self.slots[slot.slot_id] = updated
        self.edges[edge.edge_id] = edge
        return updated

    def transition_candidate(self, candidate_id: str, target: CandidateLifecycle) -> AssetCandidate:
        current = self.candidates.get(candidate_id)
        if current is None:
            raise ProductError("ERR_PRODUCTION_CANDIDATE_NOT_FOUND", "candidate_id does not exist", ProductErrorCategory.STATE)
        if target not in _TRANSITIONS[current.lifecycle_state]:
            raise ProductError(
                "ERR_PRODUCTION_CANDIDATE_TRANSITION_INVALID",
                "Candidate lifecycle transition is not allowed",
                ProductErrorCategory.STATE,
                details={"from": current.lifecycle_state.value, "to": target.value},
            )
        updated = replace(current, lifecycle_state=target)
        self.candidates[candidate_id] = updated
        if target is CandidateLifecycle.ACCEPTED:
            slot = self.slots[current.slot_id]
            if slot.status not in {SlotStatus.LOCKED, SlotStatus.STALE}:
                self.slots[current.slot_id] = replace(slot, status=SlotStatus.ACCEPTED, revision=slot.revision + 1)
        return updated

    def lock_candidate(self, *, slot_id: str, candidate_id: str, expected_revision: int) -> SceneAssetSlot:
        slot = self.slots.get(slot_id)
        candidate = self.candidates.get(candidate_id)
        if slot is None or candidate is None or candidate.slot_id != slot_id:
            raise ProductError("ERR_PRODUCTION_LOCK_TARGET_INVALID", "Slot/Candidate lock target is invalid", ProductErrorCategory.STATE)
        if slot.revision != expected_revision:
            raise ProductError(
                "ERR_PRODUCTION_SLOT_REVISION_CONFLICT",
                "Slot changed before lock; reload Human review state",
                ProductErrorCategory.STATE,
                details={"current_revision": slot.revision},
            )
        if slot.stale_state is StaleState.STALE or candidate.lifecycle_state is CandidateLifecycle.STALE:
            raise ProductError("ERR_PRODUCTION_STALE_LOCK_BLOCKED", "STALE content cannot be locked", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        if candidate.lifecycle_state is not CandidateLifecycle.ACCEPTED:
            raise ProductError("ERR_PRODUCTION_CANDIDATE_NOT_ACCEPTED", "Candidate must be Human-accepted before lock", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        if slot.locked_candidate_id is not None:
            raise ProductError("ERR_PRODUCTION_SLOT_ALREADY_LOCKED", "Slot already has a locked Candidate", ProductErrorCategory.STATE)
        locked_candidate = replace(candidate, lifecycle_state=CandidateLifecycle.LOCKED)
        self.candidates[candidate_id] = locked_candidate
        updated = replace(
            slot,
            status=SlotStatus.LOCKED,
            locked_candidate_id=candidate_id,
            stale_state=StaleState.CURRENT,
            stale_root_cause_ref=None,
            revision=slot.revision + 1,
        )
        self.slots[slot_id] = updated
        return updated

    def _adjacency(self) -> dict[str, list[EntityRef]]:
        result: dict[str, list[EntityRef]] = {}
        for edge in self.edges.values():
            result.setdefault(edge.from_ref.key, []).append(edge.to_ref)
        for values in result.values():
            values.sort(key=lambda ref: ref.key)
        return result

    def _path_exists(self, start: EntityRef, target: EntityRef) -> bool:
        adjacency = self._adjacency()
        stack = [start]
        seen: set[str] = set()
        while stack:
            current = stack.pop()
            if current == target:
                return True
            if current.key in seen:
                continue
            seen.add(current.key)
            stack.extend(adjacency.get(current.key, ()))
        return False

    def add_dependency(self, edge: DependencyEdge) -> None:
        if edge.edge_id in self.edges:
            raise ProductError("ERR_PRODUCTION_DEPENDENCY_CONFLICT", "edge_id already exists", ProductErrorCategory.STATE)
        if self._path_exists(edge.to_ref, edge.from_ref):
            raise ProductError(
                "ERR_PRODUCTION_DEPENDENCY_CYCLE",
                "Dependency edge would create a cycle",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        self.edges[edge.edge_id] = edge

    def mark_stale(self, root: EntityRef, *, include_root: bool = False) -> StalePropagationResult:
        adjacency = self._adjacency()
        queue = ([root] if include_root else []) + list(adjacency.get(root.key, ()))
        seen: set[str] = set()
        affected: list[EntityRef] = []
        while queue:
            ref = queue.pop(0)
            if ref.key in seen:
                continue
            seen.add(ref.key)
            affected.append(ref)
            if ref.entity_type is EntityType.SLOT and ref.entity_id in self.slots:
                slot = self.slots[ref.entity_id]
                self.slots[ref.entity_id] = replace(
                    slot,
                    status=SlotStatus.STALE,
                    stale_state=StaleState.STALE,
                    stale_root_cause_ref=root.entity_id,
                    revision=slot.revision + 1,
                )
            elif ref.entity_type is EntityType.CANDIDATE and ref.entity_id in self.candidates:
                candidate = self.candidates[ref.entity_id]
                if candidate.lifecycle_state not in {CandidateLifecycle.REJECTED, CandidateLifecycle.ALTERNATE_USE}:
                    self.candidates[ref.entity_id] = replace(candidate, lifecycle_state=CandidateLifecycle.STALE)
            queue.extend(adjacency.get(ref.key, ()))
        return StalePropagationResult(root=root, affected=tuple(affected))

    def locked_asset_trace(self, slot_id: str) -> dict[str, Any]:
        slot = self.slots.get(slot_id)
        if slot is None or slot.locked_candidate_id is None:
            raise ProductError("ERR_PRODUCTION_SLOT_NOT_LOCKED", "Slot has no locked Candidate", ProductErrorCategory.STATE)
        candidate = self.candidates[slot.locked_candidate_id]
        return {
            "slot": slot.to_dict(),
            "candidate": candidate.to_dict(),
            "asset_id": candidate.asset_id,
            "asset_sha256": candidate.asset_sha256,
            "physical_delete_performed": False,
        }
