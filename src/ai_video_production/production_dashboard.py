"""Read-only Production Control dashboard projection for TASK-027/037..041.

The dashboard intentionally owns no mutation.  It validates the exact
Human-approved Plan trace and the cross-store Production bundle first, then
projects concise per-Scene operational status for the future unified Desktop
Application.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .approved_plan_trace import ApprovedPlanTraceValidator
from .audio_workspace import AudioWorkspaceRegistry, PlacementDecision
from .candidate_audit import CandidateAuditRegistry, HumanCandidateDecision
from .continuity_registry import ContinuityRegistry
from .errors import ProductError, ProductErrorCategory
from .production_budget import ProductionBudgetLedger
from .production_bundle_validation import ProductionBundleValidator
from .production_control import CandidateLifecycle, ProductionControlRegistry, SlotStatus
from .production_proposal import ProductionProposalRegistry
from .prompt_registry import GenerationResult, PromptGenerationRegistry
from .serialization import canonical_json_bytes, sha256_bytes


@dataclass(frozen=True, slots=True)
class SceneProductionSummary:
    scene_id: str
    narrative_role: str
    slot_count: int
    required_slot_count: int
    locked_slot_count: int
    empty_required_slot_count: int
    stale_slot_count: int
    candidate_count: int
    ready_for_audit_count: int
    audit_count: int
    human_decision_count: int
    regeneration_request_count: int
    generation_attempt_count: int
    failed_generation_count: int
    continuity_edge_count: int
    unresolved_continuity_count: int
    audio_placement_count: int
    pending_audio_placement_count: int
    attention_reasons: tuple[str, ...]

    @property
    def status(self) -> str:
        if self.attention_reasons:
            return "NEEDS_ATTENTION"
        if self.required_slot_count > 0 and self.locked_slot_count == self.required_slot_count:
            return "COMPLETE"
        return "IN_PROGRESS"

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "narrative_role": self.narrative_role,
            "status": self.status,
            "slot_count": self.slot_count,
            "required_slot_count": self.required_slot_count,
            "locked_slot_count": self.locked_slot_count,
            "empty_required_slot_count": self.empty_required_slot_count,
            "stale_slot_count": self.stale_slot_count,
            "candidate_count": self.candidate_count,
            "ready_for_audit_count": self.ready_for_audit_count,
            "audit_count": self.audit_count,
            "human_decision_count": self.human_decision_count,
            "regeneration_request_count": self.regeneration_request_count,
            "generation_attempt_count": self.generation_attempt_count,
            "failed_generation_count": self.failed_generation_count,
            "continuity_edge_count": self.continuity_edge_count,
            "unresolved_continuity_count": self.unresolved_continuity_count,
            "audio_placement_count": self.audio_placement_count,
            "pending_audio_placement_count": self.pending_audio_placement_count,
            "attention_reasons": list(self.attention_reasons),
        }


@dataclass(frozen=True, slots=True)
class ProductionDashboardReport:
    plan_id: str
    approved_plan_sha256: str
    project_id: str
    blueprint_id: str
    blueprint_title: str
    budget: dict[str, Any]
    bundle_validation_sha256: str
    plan_trace_sha256: str
    scenes: tuple[SceneProductionSummary, ...]

    @property
    def status(self) -> str:
        if any(scene.status == "NEEDS_ATTENTION" for scene in self.scenes):
            return "NEEDS_ATTENTION"
        if self.scenes and all(scene.status == "COMPLETE" for scene in self.scenes):
            return "COMPLETE"
        return "IN_PROGRESS"

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "report_version": "1.0.0",
            "task_owner": "TASK-027/TASK-037..041",
            "status": self.status,
            "plan_id": self.plan_id,
            "approved_plan_sha256": self.approved_plan_sha256,
            "project_id": self.project_id,
            "blueprint_id": self.blueprint_id,
            "blueprint_title": self.blueprint_title,
            "human_go_proven": True,
            "budget": dict(self.budget),
            "bundle_validation_sha256": self.bundle_validation_sha256,
            "plan_trace_sha256": self.plan_trace_sha256,
            "scene_count": len(self.scenes),
            "needs_attention_scene_count": sum(scene.status == "NEEDS_ATTENTION" for scene in self.scenes),
            "complete_scene_count": sum(scene.status == "COMPLETE" for scene in self.scenes),
            "scenes": [scene.to_dict() for scene in self.scenes],
            "read_only_projection": True,
            "provider_execution_started": False,
            "automatic_repair_performed": False,
            "automatic_regeneration_started": False,
            "human_final_authority_preserved": True,
        }
        body["report_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class ProductionDashboardProjection:
    """Build a deterministic operator projection from exact canonical state."""

    @staticmethod
    def _blueprint_for_plan(*, proposals: ProductionProposalRegistry, plan_id: str):
        plan = proposals.approved_plans.get(plan_id)
        if plan is None:
            raise ProductError(
                "ERR_PRODUCTION_DASHBOARD_PLAN_NOT_FOUND",
                "Production dashboard requires a registered Human-approved Plan",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        revisions = proposals.proposals.get(plan.proposal_id, ())
        matching = [row for row in revisions if row.revision == plan.proposal_revision]
        if len(matching) != 1:
            raise ProductError(
                "ERR_PRODUCTION_DASHBOARD_PROPOSAL_NOT_FOUND",
                "Approved Plan Proposal revision is missing from the proposal registry",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return plan, matching[0].blueprint

    @staticmethod
    def _require_budget_matches_plan(*, plan: Any, budget: ProductionBudgetLedger) -> None:
        if (
            budget.plan_id != plan.plan_id
            or budget.currency != plan.currency
            or budget.cost_ceiling != plan.cost_ceiling
        ):
            raise ProductError(
                "ERR_PRODUCTION_DASHBOARD_BUDGET_PLAN_MISMATCH",
                "Production budget does not match the exact Human-approved Plan",
                ProductErrorCategory.DATA_INTEGRITY,
            )

    @classmethod
    def build(
        cls,
        *,
        proposals: ProductionProposalRegistry,
        plan_id: str,
        project_id: str,
        budget: ProductionBudgetLedger,
        production: ProductionControlRegistry,
        audits: CandidateAuditRegistry,
        prompts: PromptGenerationRegistry,
        continuity: ContinuityRegistry,
        audio: AudioWorkspaceRegistry,
    ) -> ProductionDashboardReport:
        plan, blueprint = cls._blueprint_for_plan(proposals=proposals, plan_id=plan_id)
        cls._require_budget_matches_plan(plan=plan, budget=budget)

        plan_trace = ApprovedPlanTraceValidator.validate(
            proposals=proposals,
            plan_id=plan_id,
            production=production,
            project_id=project_id,
        ).to_dict()
        bundle = ProductionBundleValidator.validate(
            production=production,
            audits=audits,
            prompts=prompts,
            continuity=continuity,
            audio=audio,
            require_bound_pass_outputs=True,
        ).to_dict()

        scene_rows: list[SceneProductionSummary] = []
        for scene in blueprint.scenes:
            slots = sorted(
                (slot for slot in production.slots.values() if slot.scene_id == scene.scene_id),
                key=lambda item: item.slot_id,
            )
            slot_ids = {slot.slot_id for slot in slots}
            candidates = sorted(
                (candidate for candidate in production.candidates.values() if candidate.slot_id in slot_ids),
                key=lambda item: item.candidate_id,
            )
            candidate_ids = {candidate.candidate_id for candidate in candidates}
            scene_audits = [record for record in audits.audit_records.values() if record.candidate_id in candidate_ids]
            scene_decisions = [decision for decision in audits.decisions.values() if decision.candidate_id in candidate_ids]
            scene_attempts = [attempt for attempt in prompts.attempts.values() if attempt.slot_id in slot_ids]
            scene_continuity = [
                edge for edge in continuity.edges.values()
                if edge.from_scene_id == scene.scene_id or edge.to_scene_id == scene.scene_id
            ]
            unresolved_continuity = sum(
                1 for edge in scene_continuity
                if continuity.resolutions.get(edge.edge_id) is None
                or continuity.resolutions[edge.edge_id].status not in {"PASS", "HUMAN_APPROVED"}
            )
            scene_placements = [
                placement for placement in audio.placements.values()
                if placement.candidate_id in candidate_ids
            ]

            decisions_by_candidate: dict[str, list[Any]] = {}
            for decision in scene_decisions:
                decisions_by_candidate.setdefault(decision.candidate_id, []).append(decision)

            attention: set[str] = set()
            empty_required = sum(slot.required and slot.status is SlotStatus.EMPTY for slot in slots)
            stale_slots = sum(slot.status is SlotStatus.STALE for slot in slots)
            if empty_required:
                attention.add("REQUIRED_SLOT_EMPTY")
            if stale_slots:
                attention.add("STALE_SLOT")
            for candidate in candidates:
                if (
                    candidate.lifecycle_state is CandidateLifecycle.READY_FOR_AUDIT
                    and not decisions_by_candidate.get(candidate.candidate_id)
                ):
                    attention.add("HUMAN_AUDIT_DECISION_REQUIRED")
            if any(
                decision.decision is HumanCandidateDecision.NEEDS_REGENERATION
                for decision in scene_decisions
            ):
                attention.add("HUMAN_REGENERATION_REQUESTED")
            if any(attempt.result is GenerationResult.FAIL for attempt in scene_attempts):
                attention.add("GENERATION_FAILURE_RECORDED")
            if unresolved_continuity:
                attention.add("CONTINUITY_REVIEW_REQUIRED")
            if any(placement.decision is PlacementDecision.REVIEW for placement in scene_placements):
                attention.add("AUDIO_PLACEMENT_REVIEW_REQUIRED")

            scene_rows.append(SceneProductionSummary(
                scene_id=scene.scene_id,
                narrative_role=scene.narrative_role,
                slot_count=len(slots),
                required_slot_count=sum(slot.required for slot in slots),
                locked_slot_count=sum(slot.status is SlotStatus.LOCKED for slot in slots),
                empty_required_slot_count=empty_required,
                stale_slot_count=stale_slots,
                candidate_count=len(candidates),
                ready_for_audit_count=sum(
                    candidate.lifecycle_state is CandidateLifecycle.READY_FOR_AUDIT for candidate in candidates
                ),
                audit_count=len(scene_audits),
                human_decision_count=len(scene_decisions),
                regeneration_request_count=sum(
                    decision.decision is HumanCandidateDecision.NEEDS_REGENERATION
                    for decision in scene_decisions
                ),
                generation_attempt_count=len(scene_attempts),
                failed_generation_count=sum(attempt.result is GenerationResult.FAIL for attempt in scene_attempts),
                continuity_edge_count=len(scene_continuity),
                unresolved_continuity_count=unresolved_continuity,
                audio_placement_count=len(scene_placements),
                pending_audio_placement_count=sum(
                    placement.decision is PlacementDecision.REVIEW for placement in scene_placements
                ),
                attention_reasons=tuple(sorted(attention)),
            ))

        budget_dict = budget.to_dict()
        budget_summary = {
            "currency": budget.currency,
            "cost_ceiling": budget_dict["cost_ceiling"],
            "used_or_reserved": budget_dict["used_or_reserved"],
            "committed": budget_dict["committed"],
            "remaining": budget_dict["remaining"],
            "active_reservation_count": sum(row["status"] == "RESERVED" for row in budget_dict["reservations"]),
            "credit_purchase_authorized": False,
            "automatic_topup_authorized": False,
        }

        return ProductionDashboardReport(
            plan_id=plan.plan_id,
            approved_plan_sha256=plan.to_dict()["approved_plan_sha256"],
            project_id=project_id,
            blueprint_id=blueprint.blueprint_id,
            blueprint_title=blueprint.title,
            budget=budget_summary,
            bundle_validation_sha256=bundle["report_sha256"],
            plan_trace_sha256=plan_trace["report_sha256"],
            scenes=tuple(scene_rows),
        )
