"""TASK-042 Blueprint v2 WORLD LOCK projection over TASK-037 truth.

The module creates no second lock store.  It deterministically verifies the
immutable Blueprint/Approved Plan identities against the current Production
Control Slot/Candidate registry and exposes dependency edges for existing
TASK-037 stale propagation.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any

from .errors import ProductError, ProductErrorCategory
from .production_blueprint_v2 import (
    AssetLockBinding,
    CharacterLockBinding,
    FrameKind,
    ProductionBlueprintV2,
)
from .production_control import (
    CandidateLifecycle,
    DependencyEdge,
    DependencyKind,
    EntityRef,
    EntityType,
    ProductionControlRegistry,
    SlotKind,
    SlotStatus,
    StaleState,
)
from .production_proposal import ApprovedProductionPlan
from .serialization import canonical_json_bytes, sha256_bytes


@dataclass(frozen=True, slots=True)
class WorldLockRequirement:
    reference_id: str
    scene_id: str
    frame_kind: FrameKind
    reference_role: str
    expected_slot_kind: SlotKind
    slot_id: str
    candidate_id: str
    asset_id: str
    asset_sha256: str

    def to_dict(self) -> dict[str, str]:
        return {
            "reference_id": self.reference_id,
            "scene_id": self.scene_id,
            "frame_kind": self.frame_kind.value,
            "reference_role": self.reference_role,
            "expected_slot_kind": self.expected_slot_kind.value,
            "slot_id": self.slot_id,
            "candidate_id": self.candidate_id,
            "asset_id": self.asset_id,
            "asset_sha256": self.asset_sha256,
        }


class BlueprintV2WorldLockService:
    """Project Blueprint v2 frame references onto current TASK-037 state."""

    @staticmethod
    def _requirement(
        *,
        reference_id: str,
        scene_id: str,
        frame_kind: FrameKind,
        reference_role: str,
        expected_slot_kind: SlotKind,
        binding: AssetLockBinding | CharacterLockBinding,
    ) -> WorldLockRequirement:
        return WorldLockRequirement(
            reference_id=reference_id,
            scene_id=scene_id,
            frame_kind=frame_kind,
            reference_role=reference_role,
            expected_slot_kind=expected_slot_kind,
            slot_id=binding.slot_id,
            candidate_id=binding.candidate_id,
            asset_id=binding.asset_id,
            asset_sha256=binding.asset_sha256,
        )

    @classmethod
    def requirements(cls, blueprint: ProductionBlueprintV2) -> tuple[WorldLockRequirement, ...]:
        if not isinstance(blueprint, ProductionBlueprintV2):
            raise TypeError("blueprint must be a ProductionBlueprintV2")
        rows: list[WorldLockRequirement] = []
        for scene in blueprint.scenes:
            for frame_kind, intent in (
                (FrameKind.START, scene.start_frame_intent),
                (FrameKind.END, scene.end_frame_intent),
            ):
                prefix = f"{scene.scene_id}:{frame_kind.value}"
                for index, binding in enumerate(intent.binding.character_locks):
                    rows.append(cls._requirement(
                        reference_id=f"{prefix}:CHARACTER:{index}",
                        scene_id=scene.scene_id,
                        frame_kind=frame_kind,
                        reference_role=f"CHARACTER:{binding.role.value}:{index}",
                        expected_slot_kind=SlotKind.CHARACTER_REFERENCE,
                        binding=binding,
                    ))
                if intent.binding.space_lock is not None:
                    rows.append(cls._requirement(
                        reference_id=f"{prefix}:SPACE",
                        scene_id=scene.scene_id,
                        frame_kind=frame_kind,
                        reference_role="SPACE",
                        expected_slot_kind=SlotKind.SPACE_REFERENCE,
                        binding=intent.binding.space_lock,
                    ))
                if intent.binding.composition_lock is not None:
                    rows.append(cls._requirement(
                        reference_id=f"{prefix}:COMPOSITION",
                        scene_id=scene.scene_id,
                        frame_kind=frame_kind,
                        reference_role="COMPOSITION",
                        expected_slot_kind=SlotKind.COMPOSITION_REFERENCE,
                        binding=intent.binding.composition_lock,
                    ))
        reference_ids = [row.reference_id for row in rows]
        if len(reference_ids) != len(set(reference_ids)):
            raise ProductError(
                "ERR_BLUEPRINT_V2_WORLD_LOCK_REFERENCE_DUPLICATE",
                "Blueprint v2 produced duplicate deterministic frame reference paths",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return tuple(rows)

    @staticmethod
    def _go_bindings(plan: ApprovedProductionPlan) -> dict[str, tuple[str, str]]:
        result: dict[str, tuple[str, str]] = {}
        for binding in plan.reference_bindings:
            if binding.reference_id in result:
                raise ProductError(
                    "ERR_BLUEPRINT_V2_WORLD_LOCK_GO_DUPLICATE",
                    "Approved Plan contains duplicate frame reference paths",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            result[binding.reference_id] = (binding.asset_id, binding.asset_sha256)
        return result

    @classmethod
    def project(
        cls,
        *,
        blueprint: ProductionBlueprintV2,
        approved_plan: ApprovedProductionPlan,
        registry: ProductionControlRegistry,
        project_id: str,
    ) -> dict[str, Any]:
        if not isinstance(approved_plan, ApprovedProductionPlan):
            raise TypeError("approved_plan must be an ApprovedProductionPlan")
        if not isinstance(registry, ProductionControlRegistry):
            raise TypeError("registry must be a ProductionControlRegistry")
        if not isinstance(project_id, str) or not project_id.strip():
            raise ValueError("project_id must be non-empty")
        if (
            approved_plan.blueprint_id != blueprint.blueprint_id
            or approved_plan.blueprint_sha256 != blueprint.to_dict()["blueprint_sha256"]
        ):
            raise ProductError(
                "ERR_BLUEPRINT_V2_WORLD_LOCK_PLAN_MISMATCH",
                "WORLD LOCK projection requires the exact Approved Plan Blueprint",
                ProductErrorCategory.DATA_INTEGRITY,
            )

        requirements = cls.requirements(blueprint)
        expected = {row.reference_id: (row.asset_id, row.asset_sha256) for row in requirements}
        actual = cls._go_bindings(approved_plan)
        global_blockers: list[str] = []
        if set(expected) != set(actual):
            global_blockers.append("GO_REFERENCE_SET_MISMATCH")
        if any(actual.get(key) != value for key, value in expected.items()):
            global_blockers.append("GO_REFERENCE_IDENTITY_MISMATCH")

        projected: list[dict[str, Any]] = []
        for requirement in requirements:
            blockers: list[str] = []
            slot = registry.slots.get(requirement.slot_id)
            candidate = registry.candidates.get(requirement.candidate_id)
            if slot is None:
                blockers.append("SLOT_MISSING")
            else:
                if slot.project_id != project_id:
                    blockers.append("SLOT_PROJECT_MISMATCH")
                if slot.slot_kind is not requirement.expected_slot_kind:
                    blockers.append("SLOT_ROLE_MISMATCH")
                if slot.status is not SlotStatus.LOCKED:
                    blockers.append("SLOT_NOT_LOCKED")
                if slot.stale_state is not StaleState.CURRENT:
                    blockers.append("SLOT_STALE")
                if slot.locked_candidate_id != requirement.candidate_id:
                    blockers.append("LOCKED_CANDIDATE_MISMATCH")
            if candidate is None:
                blockers.append("CANDIDATE_MISSING")
            else:
                if candidate.slot_id != requirement.slot_id:
                    blockers.append("CANDIDATE_SLOT_MISMATCH")
                if candidate.lifecycle_state is not CandidateLifecycle.LOCKED:
                    blockers.append("CANDIDATE_NOT_LOCKED")
                if candidate.asset_id != requirement.asset_id:
                    blockers.append("ASSET_ID_MISMATCH")
                if candidate.asset_sha256 != requirement.asset_sha256:
                    blockers.append("ASSET_CHECKSUM_MISMATCH")
            go_identity = actual.get(requirement.reference_id)
            if go_identity is None:
                blockers.append("GO_REFERENCE_MISSING")
            elif go_identity != (requirement.asset_id, requirement.asset_sha256):
                blockers.append("GO_REFERENCE_IDENTITY_MISMATCH")
            projected.append({
                **requirement.to_dict(),
                "slot_revision": None if slot is None else slot.revision,
                "slot_status": None if slot is None else slot.status.value,
                "slot_stale_state": None if slot is None else slot.stale_state.value,
                "candidate_lifecycle_state": None if candidate is None else candidate.lifecycle_state.value,
                "status": "LOCKED_CURRENT" if not blockers else "BLOCKED",
                "blockers": sorted(set(blockers)),
            })

        blockers = sorted(set(global_blockers).union(
            blocker for row in projected for blocker in row["blockers"]
        ))
        body: dict[str, Any] = {
            "projection_version": "1.0.0",
            "task_owner": "TASK-042/TASK-037",
            "project_id": project_id,
            "plan_id": approved_plan.plan_id,
            "approved_plan_sha256": approved_plan.to_dict()["approved_plan_sha256"],
            "blueprint_id": blueprint.blueprint_id,
            "blueprint_sha256": blueprint.to_dict()["blueprint_sha256"],
            "status": "PASS" if not blockers else "BLOCKED",
            "recovery_required": bool(blockers),
            "blockers": blockers,
            "bindings": projected,
            "binding_count": len(projected),
            "world_lock_store_created": False,
            "human_lock_inferred_from_go": False,
            "provider_execution_started": False,
            "automatic_regeneration_started": False,
        }
        body["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def require_current(cls, **kwargs: Any) -> dict[str, Any]:
        projection = cls.project(**kwargs)
        if projection["status"] == "PASS":
            return projection
        raise ProductError(
            "ERR_BLUEPRINT_V2_WORLD_LOCK_NOT_CURRENT",
            "Blueprint v2 production use requires every exact reference Candidate to be LOCKED/CURRENT",
            ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            details=projection,
        )

    @classmethod
    def dependency_edges(
        cls,
        *,
        blueprint: ProductionBlueprintV2,
        approved_plan: ApprovedProductionPlan,
        registry: ProductionControlRegistry,
        project_id: str,
    ) -> tuple[DependencyEdge, ...]:
        cls.require_current(
            blueprint=blueprint,
            approved_plan=approved_plan,
            registry=registry,
            project_id=project_id,
        )
        distinct: dict[tuple[str, str], WorldLockRequirement] = {}
        for requirement in cls.requirements(blueprint):
            distinct.setdefault((requirement.scene_id, requirement.candidate_id), requirement)
        edges: list[DependencyEdge] = []
        for (scene_id, candidate_id), requirement in sorted(distinct.items()):
            digest = hashlib.sha256(
                f"{blueprint.blueprint_id}\0{scene_id}\0{candidate_id}".encode("utf-8")
            ).hexdigest()[:24]
            edges.append(DependencyEdge(
                edge_id=f"dep:world-lock:{digest}",
                from_ref=EntityRef(EntityType.CANDIDATE, candidate_id),
                to_ref=EntityRef(EntityType.SCENE, scene_id),
                dependency_kind=DependencyKind.USES,
                from_hash=requirement.asset_sha256,
            ))
        return tuple(edges)
