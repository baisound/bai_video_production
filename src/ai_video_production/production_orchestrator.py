"""TASK-027 production-control bridge foundation.

Compiles the existing ProductionBlueprint into stable Scene Asset Slots and
performs generation admission checks without executing any provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .errors import ProductError, ProductErrorCategory
from .production_blueprint import AssetSourceStrategy, ProductionBlueprint
from .production_blueprint_v2 import ProductionBlueprintV2
from .production_control import (
    DependencyEdge,
    DependencyKind,
    EntityRef,
    EntityType,
    ProductionControlRegistry,
    SceneAssetSlot,
    SlotKind,
    SlotStatus,
)
from .prompt_registry import GenerationAdmission
from .shot_feasibility import AssessmentStatus, ShotFeasibilityAssessment


@dataclass(frozen=True, slots=True)
class BlueprintControlPlan:
    blueprint_id: str
    blueprint_sha256: str
    project_id: str
    slots: tuple[SceneAssetSlot, ...]
    dependency_edges: tuple[DependencyEdge, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_version": "1.0.0",
            "task_owner": "TASK-027",
            "blueprint_id": self.blueprint_id,
            "blueprint_sha256": self.blueprint_sha256,
            "project_id": self.project_id,
            "slots": [slot.to_dict() for slot in self.slots],
            "dependency_edges": [edge.to_dict() for edge in self.dependency_edges],
            "provider_execution_started": False,
        }


class BlueprintProductionControlCompiler:
    """Create deterministic production-control slots from a validated Blueprint."""

    @staticmethod
    def _slot_id(scene_id: str, kind: str, index: int | None = None) -> str:
        suffix = f":{index:02d}" if index is not None else ""
        return f"slot:{scene_id}:{kind}{suffix}"

    @classmethod
    def compile(
        cls,
        blueprint: ProductionBlueprint | ProductionBlueprintV2,
        *,
        project_id: str,
    ) -> BlueprintControlPlan:
        if not project_id.strip():
            raise ValueError("project_id must be non-empty")
        slots: list[SceneAssetSlot] = []
        for scene in blueprint.scenes:
            slots.append(SceneAssetSlot(
                cls._slot_id(scene.scene_id, "VIDEO"), project_id, scene.scene_id, SlotKind.VIDEO, True
            ))
            if scene.source_strategy is AssetSourceStrategy.AI_GENERATED:
                slots.append(SceneAssetSlot(
                    cls._slot_id(scene.scene_id, "START_FRAME"), project_id, scene.scene_id, SlotKind.START_FRAME, True
                ))
                slots.append(SceneAssetSlot(
                    cls._slot_id(scene.scene_id, "END_FRAME"), project_id, scene.scene_id, SlotKind.END_FRAME, True
                ))
            if scene.audio.narration:
                slots.append(SceneAssetSlot(
                    cls._slot_id(scene.scene_id, "NARRATION"), project_id, scene.scene_id, SlotKind.NARRATION, True
                ))
            if scene.audio.bgm:
                slots.append(SceneAssetSlot(
                    cls._slot_id(scene.scene_id, "BGM"), project_id, scene.scene_id, SlotKind.BGM, True
                ))
            for index, _intent in enumerate(scene.audio.sound_effects, 1):
                slots.append(SceneAssetSlot(
                    cls._slot_id(scene.scene_id, "SE", index), project_id, scene.scene_id, SlotKind.SE, True
                ))
        ids = [item.slot_id for item in slots]
        if len(ids) != len(set(ids)):
            raise ProductError(
                "ERR_BLUEPRINT_SLOT_ID_CONFLICT",
                "Blueprint produced duplicate production-control Slot identities",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        edges: list[DependencyEdge] = []
        seen_scenes: set[str] = set()
        for slot in slots:
            if slot.scene_id not in seen_scenes:
                edges.append(DependencyEdge(
                    edge_id=f"dep:{blueprint.blueprint_id}:{slot.scene_id}",
                    from_ref=EntityRef(EntityType.PLAN, blueprint.blueprint_id),
                    to_ref=EntityRef(EntityType.SCENE, slot.scene_id),
                    dependency_kind=DependencyKind.USES,
                    from_hash=blueprint.to_dict()["blueprint_sha256"],
                ))
                seen_scenes.add(slot.scene_id)
            edges.append(DependencyEdge(
                edge_id=f"dep:{slot.scene_id}:{slot.slot_id}",
                from_ref=EntityRef(EntityType.SCENE, slot.scene_id),
                to_ref=EntityRef(EntityType.SLOT, slot.slot_id),
                dependency_kind=DependencyKind.USES,
            ))
        return BlueprintControlPlan(
            blueprint_id=blueprint.blueprint_id,
            blueprint_sha256=blueprint.to_dict()["blueprint_sha256"],
            project_id=project_id,
            slots=tuple(slots),
            dependency_edges=tuple(edges),
        )

    @staticmethod
    def install(plan: BlueprintControlPlan, registry: ProductionControlRegistry) -> None:
        for slot in plan.slots:
            registry.add_slot(slot)
        for edge in plan.dependency_edges:
            registry.add_dependency(edge)


@dataclass(frozen=True, slots=True)
class GenerationQueueAdmissionResult:
    scene_id: str
    slot_id: str
    status: str
    missing_locked_slot_ids: tuple[str, ...]
    feasibility_status: str
    cost_authorized: bool
    cost_required: bool

    @property
    def ready(self) -> bool:
        return self.status == "GENERATION_READY"

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "slot_id": self.slot_id,
            "status": self.status,
            "missing_locked_slot_ids": list(self.missing_locked_slot_ids),
            "feasibility_status": self.feasibility_status,
            "cost_authorized": self.cost_authorized,
            "cost_required": self.cost_required,
            "provider_execution_started": False,
        }


class GenerationQueueAdmissionService:
    """Bridge TASK-013/037/040 admission rules before high-cost generation."""

    @staticmethod
    def evaluate(
        *,
        scene_id: str,
        slot_id: str,
        plan_approved: bool,
        feasibility: ShotFeasibilityAssessment,
        required_input_slot_ids: Iterable[str],
        registry: ProductionControlRegistry,
        cost_authorized: bool,
        cost_required: bool = True,
    ) -> GenerationQueueAdmissionResult:
        target = registry.slots.get(slot_id)
        if target is None:
            raise ProductError(
                "ERR_GENERATION_TARGET_SLOT_NOT_FOUND",
                "Generation target Slot does not exist in Production Control",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if target.scene_id != scene_id:
            raise ProductError(
                "ERR_GENERATION_TARGET_SCENE_MISMATCH",
                "Generation target Slot belongs to a different Scene",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"target_scene_id": target.scene_id},
            )
        if target.status in {SlotStatus.LOCKED, SlotStatus.STALE}:
            raise ProductError(
                "ERR_GENERATION_TARGET_SLOT_NOT_MUTABLE",
                "Generation cannot append output to a locked or stale target Slot",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={"slot_status": target.status.value},
            )
        required = tuple(dict.fromkeys(required_input_slot_ids))
        missing = tuple(
            slot for slot in required
            if slot not in registry.slots
            or registry.slots[slot].locked_candidate_id is None
            or registry.slots[slot].stale_state.value != "CURRENT"
        )
        gate = GenerationAdmission(
            plan_approved=plan_approved,
            feasibility_pass=feasibility.status is AssessmentStatus.PASS,
            required_inputs_locked=not missing,
            cost_authorized=(cost_authorized or not cost_required),
        )
        return GenerationQueueAdmissionResult(
            scene_id=scene_id,
            slot_id=slot_id,
            status="GENERATION_READY" if gate.ready else "BLOCKED",
            missing_locked_slot_ids=missing,
            feasibility_status=feasibility.status.value,
            cost_authorized=cost_authorized,
            cost_required=cost_required,
        )

    @classmethod
    def require_ready(cls, **kwargs: Any) -> GenerationQueueAdmissionResult:
        result = cls.evaluate(**kwargs)
        if result.ready:
            return result
        raise ProductError(
            "ERR_GENERATION_QUEUE_NOT_READY",
            "Scene generation is blocked by Plan/Feasibility/Lock/Cost prerequisites",
            ProductErrorCategory.AUTHORIZATION,
            details=result.to_dict(),
        )
