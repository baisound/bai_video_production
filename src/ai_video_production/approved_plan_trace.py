"""Read-only TASK-027 -> TASK-037 Approved Plan trace validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .approved_plan_orchestration import ApprovedPlanVerifier
from .errors import ProductError, ProductErrorCategory
from .production_control import DependencyKind, EntityType, ProductionControlRegistry
from .production_orchestrator import BlueprintProductionControlCompiler
from .production_proposal import ProductionProposalRegistry
from .serialization import canonical_json_bytes, sha256_bytes


@dataclass(frozen=True, slots=True)
class ApprovedPlanTraceReport:
    plan_id: str
    blueprint_id: str
    project_id: str
    scene_count: int
    slot_count: int

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "report_version": "1.0.0",
            "task_owner": "TASK-027/TASK-037",
            "status": "PASS",
            "plan_id": self.plan_id,
            "blueprint_id": self.blueprint_id,
            "project_id": self.project_id,
            "scene_count": self.scene_count,
            "slot_count": self.slot_count,
            "human_go_proven": True,
            "automatic_generation_started": False,
        }
        body["report_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class ApprovedPlanTraceValidator:
    @staticmethod
    def _matching_edge(
        production: ProductionControlRegistry,
        *,
        from_type: EntityType,
        from_id: str,
        to_type: EntityType,
        to_id: str,
        from_hash: str | None,
    ) -> bool:
        return any(
            edge.from_ref.entity_type is from_type
            and edge.from_ref.entity_id == from_id
            and edge.to_ref.entity_type is to_type
            and edge.to_ref.entity_id == to_id
            and edge.dependency_kind is DependencyKind.USES
            and edge.from_hash == from_hash
            for edge in production.edges.values()
        )

    @classmethod
    def validate(
        cls,
        *,
        proposals: ProductionProposalRegistry,
        plan_id: str,
        production: ProductionControlRegistry,
        project_id: str,
    ) -> ApprovedPlanTraceReport:
        plan = proposals.approved_plans.get(plan_id)
        if plan is None:
            raise ProductError(
                "ERR_APPROVED_PLAN_TRACE_PLAN_MISSING",
                "Approved Plan trace requires a registered immutable Plan",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        revisions = proposals.proposals.get(plan.proposal_id, [])
        matching = [item for item in revisions if item.revision == plan.proposal_revision]
        if len(matching) != 1:
            raise ProductError(
                "ERR_APPROVED_PLAN_TRACE_PROPOSAL_MISSING",
                "Approved Plan trace Proposal revision is missing",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        blueprint = matching[0].blueprint
        ApprovedPlanVerifier.require_current(proposal_registry=proposals, plan_id=plan_id, blueprint=blueprint)
        expected = BlueprintProductionControlCompiler.compile(blueprint, project_id=project_id)

        for slot in expected.slots:
            current = production.slots.get(slot.slot_id)
            if current is None:
                raise ProductError(
                    "ERR_APPROVED_PLAN_TRACE_SLOT_MISSING",
                    "Approved Blueprint Slot is missing from Production Control",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"slot_id": slot.slot_id},
                )
            if (
                current.project_id != slot.project_id
                or current.scene_id != slot.scene_id
                or current.slot_kind is not slot.slot_kind
                or current.required != slot.required
            ):
                raise ProductError(
                    "ERR_APPROVED_PLAN_TRACE_SLOT_MISMATCH",
                    "Production Slot semantic identity differs from the Approved Blueprint",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"slot_id": slot.slot_id},
                )

        approved_plan_sha = plan.to_dict()["approved_plan_sha256"]
        blueprint_sha = blueprint.to_dict()["blueprint_sha256"]
        for scene in blueprint.scenes:
            if not cls._matching_edge(
                production,
                from_type=EntityType.PLAN,
                from_id=plan.plan_id,
                to_type=EntityType.SCENE,
                to_id=scene.scene_id,
                from_hash=approved_plan_sha,
            ):
                raise ProductError(
                    "ERR_APPROVED_PLAN_TRACE_PLAN_SCENE_MISSING",
                    "Human-approved Plan -> Scene dependency is missing or has the wrong Plan hash",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"scene_id": scene.scene_id},
                )
            # Preserve Blueprint provenance separately from Human GO authority.
            if not cls._matching_edge(
                production,
                from_type=EntityType.PLAN,
                from_id=blueprint.blueprint_id,
                to_type=EntityType.SCENE,
                to_id=scene.scene_id,
                from_hash=blueprint_sha,
            ):
                raise ProductError(
                    "ERR_APPROVED_PLAN_TRACE_BLUEPRINT_SCENE_MISSING",
                    "Blueprint -> Scene provenance dependency is missing or has the wrong Blueprint hash",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"scene_id": scene.scene_id},
                )

        for slot in expected.slots:
            if not cls._matching_edge(
                production,
                from_type=EntityType.SCENE,
                from_id=slot.scene_id,
                to_type=EntityType.SLOT,
                to_id=slot.slot_id,
                from_hash=None,
            ):
                raise ProductError(
                    "ERR_APPROVED_PLAN_TRACE_SCENE_SLOT_MISSING",
                    "Approved Scene -> Slot dependency is missing",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"slot_id": slot.slot_id},
                )

        return ApprovedPlanTraceReport(plan.plan_id, blueprint.blueprint_id, project_id, len(blueprint.scenes), len(expected.slots))
