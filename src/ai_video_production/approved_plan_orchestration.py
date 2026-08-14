"""TASK-027 approved-plan bridge into Production Control and generation admission.

The public orchestration boundary accepts an immutable Approved Production Plan
rather than a raw ``plan_approved=True`` boolean.  Provider execution remains
separately authorized at the later TASK-013/028 execution boundary.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from .blueprint_v2_world_lock import BlueprintV2WorldLockService
from .errors import ProductError, ProductErrorCategory
from .production_blueprint import ProductionBlueprint
from .production_blueprint_v2 import ProductionBlueprintV2
from .production_control import (
    DependencyEdge,
    DependencyKind,
    EntityRef,
    EntityType,
    ProductionControlRegistry,
)
from .production_orchestrator import (
    BlueprintControlPlan,
    BlueprintProductionControlCompiler,
    GenerationQueueAdmissionResult,
    GenerationQueueAdmissionService,
)
from .production_proposal import ApprovedProductionPlan, ProductionProposalRegistry
from .shot_feasibility import ShotFeasibilityAssessment


class ApprovedPlanVerifier:
    @staticmethod
    def require_current(
        *,
        proposal_registry: ProductionProposalRegistry,
        plan_id: str,
        blueprint: ProductionBlueprint | ProductionBlueprintV2,
    ) -> ApprovedProductionPlan:
        plan = proposal_registry.approved_plans.get(plan_id)
        if plan is None:
            raise ProductError(
                "ERR_APPROVED_PLAN_NOT_FOUND",
                "Generation/Production Control requires a registered Approved Production Plan",
                ProductErrorCategory.AUTHORIZATION,
            )
        blueprint_sha = blueprint.to_dict()["blueprint_sha256"]
        if plan.blueprint_id != blueprint.blueprint_id or plan.blueprint_sha256 != blueprint_sha:
            raise ProductError(
                "ERR_APPROVED_PLAN_BLUEPRINT_MISMATCH",
                "Approved Production Plan does not bind the supplied exact Blueprint",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"plan_blueprint_id": plan.blueprint_id, "supplied_blueprint_id": blueprint.blueprint_id},
            )
        revisions = proposal_registry.proposals.get(plan.proposal_id, [])
        matching = [item for item in revisions if item.revision == plan.proposal_revision]
        if len(matching) != 1:
            raise ProductError(
                "ERR_APPROVED_PLAN_PROPOSAL_MISSING",
                "Approved Production Plan references a missing Proposal revision",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        proposal = matching[0]
        if (
            proposal.to_dict()["proposal_sha256"] != plan.proposal_sha256
            or proposal.intent_sha256 != plan.intent_sha256
            or proposal.blueprint.to_dict()["blueprint_sha256"] != plan.blueprint_sha256
            or proposal.provider_policy != plan.provider_policy
        ):
            raise ProductError(
                "ERR_APPROVED_PLAN_PROPOSAL_MISMATCH",
                "Approved Production Plan no longer matches exact Proposal/Intent/Provider policy identity",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return plan


class ApprovedPlanProductionControlInstaller:
    @classmethod
    def compile(
        cls,
        *,
        proposal_registry: ProductionProposalRegistry,
        plan_id: str,
        blueprint: ProductionBlueprint | ProductionBlueprintV2,
        project_id: str,
        production_registry: ProductionControlRegistry | None = None,
    ) -> BlueprintControlPlan:
        plan = ApprovedPlanVerifier.require_current(
            proposal_registry=proposal_registry,
            plan_id=plan_id,
            blueprint=blueprint,
        )
        if isinstance(blueprint, ProductionBlueprintV2):
            if production_registry is None:
                raise ProductError(
                    "ERR_BLUEPRINT_V2_WORLD_LOCK_REGISTRY_REQUIRED",
                    "Blueprint v2 compilation requires the exact current Production Control registry",
                    ProductErrorCategory.AUTHORIZATION,
                )
            BlueprintV2WorldLockService.require_current(
                blueprint=blueprint,
                approved_plan=plan,
                registry=production_registry,
                project_id=project_id,
            )
        return BlueprintProductionControlCompiler.compile(blueprint, project_id=project_id)

    @classmethod
    def install(
        cls,
        *,
        proposal_registry: ProductionProposalRegistry,
        plan_id: str,
        blueprint: ProductionBlueprint | ProductionBlueprintV2,
        project_id: str,
        production_registry: ProductionControlRegistry,
    ) -> BlueprintControlPlan:
        plan = ApprovedPlanVerifier.require_current(
            proposal_registry=proposal_registry,
            plan_id=plan_id,
            blueprint=blueprint,
        )
        control_plan = cls.compile(
            proposal_registry=proposal_registry,
            plan_id=plan_id,
            blueprint=blueprint,
            project_id=project_id,
            production_registry=production_registry,
        )
        # Apply the complete graph to an isolated copy.  A conflict/cycle can
        # therefore never leave the caller-visible registry partially changed.
        working = deepcopy(production_registry)
        BlueprintProductionControlCompiler.install(control_plan, working)
        if isinstance(blueprint, ProductionBlueprintV2):
            for edge in BlueprintV2WorldLockService.dependency_edges(
                blueprint=blueprint,
                approved_plan=plan,
                registry=production_registry,
                project_id=project_id,
            ):
                working.add_dependency(edge)
        # Keep the Blueprint trace while adding the true Human-approved Plan node.
        # This lets PRODUCT-CONTROL-001 prove Approved Plan -> Scene -> Slot, rather
        # than treating an unapproved Blueprint alone as final Plan authority.
        approved_plan_sha = plan.to_dict()["approved_plan_sha256"]
        for scene in blueprint.scenes:
            working.add_dependency(DependencyEdge(
                edge_id=f"dep:approved:{plan.plan_id}:{scene.scene_id}",
                from_ref=EntityRef(EntityType.PLAN, plan.plan_id),
                to_ref=EntityRef(EntityType.SCENE, scene.scene_id),
                dependency_kind=DependencyKind.USES,
                from_hash=approved_plan_sha,
            ))
        production_registry.slots.clear()
        production_registry.slots.update(working.slots)
        production_registry.candidates.clear()
        production_registry.candidates.update(working.candidates)
        production_registry.edges.clear()
        production_registry.edges.update(working.edges)
        return control_plan


class ApprovedPlanGenerationAdmissionService:
    """Derive the Plan-approval bit from exact immutable GO evidence."""

    @classmethod
    def evaluate(
        cls,
        *,
        proposal_registry: ProductionProposalRegistry,
        plan_id: str,
        blueprint: ProductionBlueprint | ProductionBlueprintV2,
        scene_id: str,
        slot_id: str,
        feasibility: ShotFeasibilityAssessment,
        required_input_slot_ids: Iterable[str],
        production_registry: ProductionControlRegistry,
        prompt_provider_policy_sha256: str,
        explicit_paid_execution_authorization: bool,
        cost_required: bool = True,
    ) -> GenerationQueueAdmissionResult:
        plan = ApprovedPlanVerifier.require_current(
            proposal_registry=proposal_registry,
            plan_id=plan_id,
            blueprint=blueprint,
        )
        required_inputs = tuple(dict.fromkeys(required_input_slot_ids))
        if isinstance(blueprint, ProductionBlueprintV2):
            target = production_registry.slots.get(slot_id)
            existing_projects = {
                production_registry.slots[row.slot_id].project_id
                for row in BlueprintV2WorldLockService.requirements(blueprint)
                if row.slot_id in production_registry.slots
            }
            project_id = target.project_id if target is not None else (
                next(iter(existing_projects)) if len(existing_projects) == 1 else "unknown-project"
            )
            BlueprintV2WorldLockService.require_current(
                blueprint=blueprint,
                approved_plan=plan,
                registry=production_registry,
                project_id=project_id,
            )
            required_inputs = tuple(dict.fromkeys((
                *required_inputs,
                *(row.slot_id for row in BlueprintV2WorldLockService.requirements(blueprint)),
            )))
        if plan.provider_policy.policy_sha256 != prompt_provider_policy_sha256:
            raise ProductError(
                "ERR_APPROVED_PLAN_PROVIDER_POLICY_MISMATCH",
                "Generation Prompt/Route policy does not match the Human-approved Production Plan policy",
                ProductErrorCategory.AUTHORIZATION,
            )
        return GenerationQueueAdmissionService.evaluate(
            scene_id=scene_id,
            slot_id=slot_id,
            plan_approved=True,
            feasibility=feasibility,
            required_input_slot_ids=required_inputs,
            registry=production_registry,
            cost_authorized=explicit_paid_execution_authorization,
            cost_required=cost_required,
        )

    @classmethod
    def require_ready(cls, **kwargs: Any) -> GenerationQueueAdmissionResult:
        result = cls.evaluate(**kwargs)
        if result.ready:
            return result
        raise ProductError(
            "ERR_APPROVED_PLAN_GENERATION_NOT_READY",
            "Approved-plan generation is blocked by feasibility/input-lock/paid-execution gates",
            ProductErrorCategory.AUTHORIZATION,
            details=result.to_dict(),
        )


class BudgetedApprovedPlanGenerationAdmissionService:
    """Require both Human GO and an active total-budget reservation for paid work."""

    @classmethod
    def require_ready(
        cls,
        *,
        budget_ledger: Any,
        budget_operation_id: str,
        **kwargs: Any,
    ) -> GenerationQueueAdmissionResult:
        from .production_budget import ProductionBudgetLedger

        if not isinstance(budget_ledger, ProductionBudgetLedger):
            raise TypeError("budget_ledger must be a ProductionBudgetLedger")
        plan_id = kwargs.get("plan_id")
        proposal_registry = kwargs.get("proposal_registry")
        blueprint = kwargs.get("blueprint")
        if not isinstance(proposal_registry, ProductionProposalRegistry) or not isinstance(blueprint, (ProductionBlueprint, ProductionBlueprintV2)):
            raise TypeError("proposal_registry and blueprint are required")
        plan = ApprovedPlanVerifier.require_current(
            proposal_registry=proposal_registry,
            plan_id=plan_id,
            blueprint=blueprint,
        )
        if (
            budget_ledger.plan_id != plan.plan_id
            or budget_ledger.currency != plan.currency
            or budget_ledger.cost_ceiling != plan.cost_ceiling
        ):
            raise ProductError(
                "ERR_PRODUCTION_BUDGET_PLAN_MISMATCH",
                "Paid generation budget ledger does not match the exact Human-approved Production Plan ceiling/currency",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        budget_ledger.require_reserved(operation_id=budget_operation_id)
        call = dict(kwargs)
        call["explicit_paid_execution_authorization"] = True
        call["cost_required"] = True
        result = ApprovedPlanGenerationAdmissionService.require_ready(**call)
        return result
