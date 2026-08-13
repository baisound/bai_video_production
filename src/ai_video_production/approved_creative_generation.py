"""TASK-013 creative-generation planner bound to TASK-027 Human GO and budget.

This is the preferred orchestration boundary for new-video generation.  It
removes the public raw ``plan_approved`` boolean and proves the exact approved
AI Connection Profile before compiling a provider-neutral generation plan.
Provider execution is still not performed here.
"""

from __future__ import annotations

from typing import Iterable

from .ai_connections import AiConnectionProfile, ConnectionAvailability
from .approved_plan_orchestration import ApprovedPlanVerifier
from .creative_generation import CreativeGenerationPlan, CreativeGenerationPlanner, CreativeGenerationRequest
from .errors import ProductError, ProductErrorCategory
from .production_blueprint import ProductionBlueprint
from .production_budget import ProductionBudgetLedger
from .production_control import ProductionControlRegistry
from .production_proposal import ProductionProposalRegistry
from .shot_feasibility import ShotFeasibilityAssessment


class ApprovedCreativeGenerationPlanner:
    @staticmethod
    def _verify_profile(plan: object, profile: AiConnectionProfile) -> None:
        binding = plan.provider_policy  # ApprovedProductionPlan by verifier contract
        if (
            binding.policy_id != profile.profile_id
            or binding.policy_version != profile.profile_version
            or binding.policy_sha256 != profile.to_dict()["profile_sha256"]
        ):
            raise ProductError(
                "ERR_APPROVED_GENERATION_PROFILE_MISMATCH",
                "Active AI Connection Profile differs from the exact profile approved by Human GO",
                ProductErrorCategory.AUTHORIZATION,
            )

    @classmethod
    def compile(
        cls,
        request: CreativeGenerationRequest,
        *,
        profile: AiConnectionProfile,
        availability: ConnectionAvailability,
        proposal_registry: ProductionProposalRegistry,
        approved_plan_id: str,
        blueprint: ProductionBlueprint,
        feasibility: ShotFeasibilityAssessment,
        production_registry: ProductionControlRegistry,
        budget_ledger: ProductionBudgetLedger | None = None,
        budget_operation_id: str | None = None,
        extra_required_capabilities: Iterable[str] = (),
    ) -> CreativeGenerationPlan:
        approved = ApprovedPlanVerifier.require_current(
            proposal_registry=proposal_registry,
            plan_id=approved_plan_id,
            blueprint=blueprint,
        )
        cls._verify_profile(approved, profile)
        plan = CreativeGenerationPlanner.compile(
            request,
            profile=profile,
            availability=availability,
            plan_approved=True,
            feasibility=feasibility,
            registry=production_registry,
            extra_required_capabilities=extra_required_capabilities,
        )
        if plan.paid_execution_required:
            if not request.explicit_paid_execution_authorization:
                # Preserve the more specific planner error semantics.
                CreativeGenerationPlanner.require_provider_execution_authorized(plan)
            if budget_ledger is None or not budget_operation_id:
                raise ProductError(
                    "ERR_APPROVED_GENERATION_BUDGET_RESERVATION_REQUIRED",
                    "Paid creative generation requires a reservation in the Approved Production Plan budget ledger",
                    ProductErrorCategory.AUTHORIZATION,
                )
            if (
                budget_ledger.plan_id != approved.plan_id
                or budget_ledger.currency != approved.currency
                or budget_ledger.cost_ceiling != approved.cost_ceiling
            ):
                raise ProductError(
                    "ERR_APPROVED_GENERATION_BUDGET_MISMATCH",
                    "Creative generation budget ledger differs from the exact Human-approved Plan",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            budget_ledger.require_reserved(operation_id=budget_operation_id)
        return plan
