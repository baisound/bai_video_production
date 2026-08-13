"""TASK-036 application-service wiring for TASK-010 Resolve assembly.

The facade compiles an approved Edit Plan without external mutation, then binds
an exact one-shot Shell confirmation to the Resolve Project/Timeline target
before calling the injected TASK-010 adapter.  It does not create its own NLE
logic and it never bypasses TASK-010 idempotency/ownership checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .desktop_editing_application import Task036EditingApplication
from .desktop_shell import ShellCommand
from .errors import ProductError, ProductErrorCategory
from .resolve_assembly import (
    AudioPlacement,
    ResolveAssemblyAdapter,
    ResolveAssemblyPlan,
    ResolveAssemblyResult,
    ResolveAssemblyService,
    ResolveAssetBindings,
)
from .resolve_subtitle_handoff import ResolveSubtitlePlacementPlan
from .serialization import canonical_json_bytes, sha256_bytes
from .timebase import FrameRate


def _target_hash(project: str, timeline: str) -> str:
    return sha256_bytes(canonical_json_bytes({"target_project": project, "target_timeline": timeline}))


@dataclass(slots=True)
class Task036ResolveWorkflowFacade:
    application: Task036EditingApplication
    assembly_plan: ResolveAssemblyPlan | None = None
    assembly_result: ResolveAssemblyResult | None = None

    def _approved_plan(self):
        plan = self.application.review.approved_plan
        state = self.application.coordinator.state
        if plan is None or not state.edit_plan_approved or state.edit_plan_sha256 != plan.to_dict()["plan_sha256"]:
            raise ProductError(
                "ERR_SHELL_APPROVED_EDIT_PLAN_REQUIRED",
                "Resolve preparation requires the exact human-approved Edit Plan in the current desktop session",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        return plan

    def compile_assembly(
        self,
        *,
        timeline_rate: FrameRate,
        timeline_origin_frame: int = 0,
        subtitle_plan: ResolveSubtitlePlacementPlan | None = None,
        audio_placements: tuple[AudioPlacement, ...] = (),
    ) -> dict[str, Any]:
        plan = ResolveAssemblyService.compile(
            self._approved_plan(),
            timeline_rate=timeline_rate,
            timeline_origin_frame=timeline_origin_frame,
            subtitle_plan=subtitle_plan,
            audio_placements=audio_placements,
        )
        self.assembly_plan = plan
        self.application.coordinator.bind_resolve_assembly(plan.to_dict()["assembly_sha256"])
        return {
            "task_owner": "TASK-036",
            "operation": "RESOLVE_ASSEMBLY_PREPARE",
            "external_mutation_performed": False,
            "assembly_plan": plan.to_dict(),
            "editing_session": self.application.coordinator.state.to_dict(),
            "available_commands": list(self.application.shell.snapshot().available_commands),
        }

    def prepare_apply(self, *, target_project: str, target_timeline: str) -> dict[str, Any]:
        if self.assembly_plan is None:
            raise ProductError(
                "ERR_SHELL_RESOLVE_ASSEMBLY_REQUIRED",
                "Prepare Resolve assembly before requesting apply authorization",
                ProductErrorCategory.STATE,
            )
        if not target_project.strip() or target_timeline != self.assembly_plan.timeline_name:
            raise ProductError(
                "ERR_SHELL_RESOLVE_TARGET_INVALID",
                "Resolve apply target must name the exact prepared Automation-owned Timeline and a non-empty Project",
                ProductErrorCategory.VALIDATION,
            )
        current_project = self.application.shell.project
        if current_project is None:
            raise ProductError("ERR_SHELL_PROJECT_REQUIRED", "No Project is open", ProductErrorCategory.STATE)
        if (
            current_project.resolve_project_name != target_project
            or current_project.resolve_timeline_name != target_timeline
        ):
            self.application.shell.bind_resolve_target(
                resolve_project_name=target_project,
                resolve_timeline_name=target_timeline,
            )
        assembly_sha = self.assembly_plan.to_dict()["assembly_sha256"]
        hashes = {
            "edit_plan_sha256": self.application.coordinator.state.edit_plan_sha256 or "",
            "assembly_sha256": assembly_sha,
            "resolve_target_sha256": _target_hash(target_project, target_timeline),
        }
        confirmation = self.application.shell.prepare_confirmation(
            command_type="resolve.assembly.apply",
            expected_upstream_hashes=hashes,
            target_application="DaVinci Resolve",
            target_project=target_project,
            target_timeline=target_timeline,
            destination="AUTOMATION_OWNED_TIMELINE",
        )
        return {
            **confirmation,
            "assembly_sha256": assembly_sha,
            "target_project": target_project,
            "target_timeline": target_timeline,
            "external_mutation_performed": False,
        }

    def apply(
        self,
        *,
        confirmation_id: str,
        target_project: str,
        target_timeline: str,
        adapter: ResolveAssemblyAdapter,
        bindings: ResolveAssetBindings,
    ) -> dict[str, Any]:
        if self.assembly_plan is None:
            raise ProductError(
                "ERR_SHELL_RESOLVE_ASSEMBLY_REQUIRED",
                "Resolve apply requires a prepared assembly plan",
                ProductErrorCategory.STATE,
            )
        if target_timeline != self.assembly_plan.timeline_name or not target_project.strip():
            raise ProductError(
                "ERR_SHELL_RESOLVE_TARGET_INVALID",
                "Resolve apply target no longer matches the prepared Automation-owned Timeline",
                ProductErrorCategory.AUTHORIZATION,
            )
        project = self.application.shell.project
        if project is None:
            raise ProductError("ERR_SHELL_PROJECT_REQUIRED", "No Project is open", ProductErrorCategory.STATE)
        assembly_sha = self.assembly_plan.to_dict()["assembly_sha256"]
        hashes = {
            "edit_plan_sha256": self.application.coordinator.state.edit_plan_sha256 or "",
            "assembly_sha256": assembly_sha,
            "resolve_target_sha256": _target_hash(target_project, target_timeline),
        }
        command = ShellCommand(
            command_id=f"resolve-apply-{project.context_revision}",
            command_type="resolve.assembly.apply",
            project_id=project.project_id,
            expected_context_revision=project.context_revision,
            expected_upstream_hashes=hashes,
            payload={
                "assembly_sha256": assembly_sha,
                "target_project": target_project,
                "target_timeline": target_timeline,
            },
            confirmation_id=confirmation_id,
        )

        def execute(_: ShellCommand) -> Mapping[str, Any]:
            result: ResolveAssemblyResult = ResolveAssemblyService.execute(
                self.assembly_plan,
                adapter=adapter,
                bindings=bindings,
                explicit_external_write_authorization=True,
            )
            self.assembly_result = result
            if result.status not in {"APPLIED", "ALREADY_APPLIED"}:
                raise ProductError(
                    "ERR_SHELL_RESOLVE_APPLY_RESULT_INVALID",
                    "TASK-010 returned a non-terminal Resolve assembly result",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"status": result.status},
                )
            self.application.coordinator.mark_resolve_applied()
            return {
                "resolve_result": result.to_dict(),
                "editing_session": self.application.coordinator.state.to_dict(),
            }

        receipt = self.application.shell.dispatch(command, executor=execute)
        return {
            "receipt": receipt,
            "editing_session": self.application.coordinator.state.to_dict(),
            "available_commands": list(self.application.shell.snapshot().available_commands),
            "next_recommended_action": self.application.coordinator.state.next_recommended_action,
        }
