"""TASK-027 Planning Workspace projection over intent/proposal/GO state.

The workspace is read-oriented except for delegating the explicit one-shot GO
boundary.  It does not invoke planning/generation providers or mutate Resolve.
"""

from __future__ import annotations

from typing import Any, Iterable

from .errors import ProductError, ProductErrorCategory
from .production_proposal import (
    ProductionGoApprovalService,
    ProductionProposalRegistry,
    ReferenceAssetBinding,
)
from .serialization import canonical_json_bytes, sha256_bytes


class Task027PlanningWorkspaceProjection:
    @staticmethod
    def _section_hash(section: dict[str, Any]) -> str:
        return sha256_bytes(canonical_json_bytes(section))

    @classmethod
    def build(cls, registry: ProductionProposalRegistry, *, proposal_id: str) -> dict[str, Any]:
        revisions = registry.proposals.get(proposal_id)
        if not revisions:
            raise ProductError(
                "ERR_PLANNING_WORKSPACE_PROPOSAL_NOT_FOUND",
                "Planning Workspace requires an existing Production Proposal",
                ProductErrorCategory.STATE,
            )
        latest = revisions[-1]
        latest_dict = latest.to_dict()
        previous = revisions[-2].to_dict() if len(revisions) > 1 else None
        previous_sections = {} if previous is None else {
            item["section_id"]: cls._section_hash(item) for item in previous["sections"]
        }
        latest_sections = {
            item["section_id"]: cls._section_hash(item) for item in latest_dict["sections"]
        }
        changed_sections = [] if previous is None else sorted(
            key for key in set(previous_sections) | set(latest_sections)
            if previous_sections.get(key) != latest_sections.get(key)
        )
        exact_plan = next(
            (
                plan for plan in registry.approved_plans.values()
                if plan.proposal_id == latest.proposal_id
                and plan.proposal_revision == latest.revision
                and plan.proposal_sha256 == latest_dict["proposal_sha256"]
                and plan.blueprint_sha256 == latest.blueprint.to_dict()["blueprint_sha256"]
            ),
            None,
        )
        prior_approved = sorted(
            (
                plan for plan in registry.approved_plans.values()
                if plan.proposal_id == proposal_id
            ),
            key=lambda plan: (plan.proposal_revision, plan.plan_id),
        )
        intent = next(
            (
                item for item in registry.intents.values()
                if item.to_dict()["intent_sha256"] == latest.intent_sha256
            ),
            None,
        )
        if intent is None:
            raise ProductError(
                "ERR_PLANNING_WORKSPACE_INTENT_MISSING",
                "Latest Production Proposal references a missing Creation Intent",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        body: dict[str, Any] = {
            "projection_version": "1.0.0",
            "task_owner": "TASK-027",
            "proposal_id": proposal_id,
            "latest_revision": latest.revision,
            "latest_proposal_sha256": latest_dict["proposal_sha256"],
            "creation_intent": intent.to_dict(),
            "sections": latest_dict["sections"],
            "changed_section_ids_from_previous": changed_sections,
            "blueprint": latest_dict["blueprint"],
            "provider_policy": latest_dict["provider_policy"],
            "estimated_cost_range": latest_dict["estimated_cost_range"],
            "rights_warnings": latest_dict["rights_warnings"],
            "go_status": "APPROVED" if exact_plan is not None else "GO_REQUIRED",
            "approved_plan": None if exact_plan is None else exact_plan.to_dict(),
            "prior_approved_plan_ids": [plan.plan_id for plan in prior_approved],
            "new_go_required_after_revision": exact_plan is None and bool(prior_approved),
            "provider_execution_started": False,
            "resolve_mutation_started": False,
        }
        body["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class Task027PlanningWorkspaceService:
    def __init__(
        self,
        registry: ProductionProposalRegistry,
        *,
        go_service: ProductionGoApprovalService | None = None,
    ) -> None:
        self.registry = registry
        self.go_service = go_service or ProductionGoApprovalService(registry)

    def snapshot(self, *, proposal_id: str) -> dict[str, Any]:
        return Task027PlanningWorkspaceProjection.build(self.registry, proposal_id=proposal_id)

    def prepare_go(
        self,
        *,
        proposal_id: str,
        proposal_revision: int,
        reference_bindings: Iterable[ReferenceAssetBinding],
        cost_ceiling: str | int | float,
        rights_warnings_acknowledged: bool,
    ) -> dict[str, Any]:
        return self.go_service.prepare_go(
            proposal_id=proposal_id,
            proposal_revision=proposal_revision,
            reference_bindings=reference_bindings,
            cost_ceiling=cost_ceiling,
            rights_warnings_acknowledged=rights_warnings_acknowledged,
        )

    def approve_go(self, *, confirmation_id: str, approved_by: str) -> dict[str, Any]:
        plan = self.go_service.approve_go(confirmation_id=confirmation_id, approved_by=approved_by)
        return {
            "approved_plan": plan.to_dict(),
            "workspace": self.snapshot(proposal_id=plan.proposal_id),
            "provider_execution_started": False,
            "resolve_mutation_started": False,
        }
