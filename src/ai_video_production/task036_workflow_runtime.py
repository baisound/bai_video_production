"""Bound runtime wiring for the TASK-036 minimum-editing desktop workflow.

The browser bridge may select an allowlisted action, but it never supplies host
paths, adapters, Resolve targets, Render QA objects, or external-write authority.
Those values are bound by the trusted desktop composition root before launch.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from .desktop_editing_application import Task036EditingApplication
from .desktop_post_resolve_workflow import Task036PostResolveWorkflowFacade
from .desktop_resolve_workflow import Task036ResolveWorkflowFacade
from .errors import ProductError, ProductErrorCategory
from .render_qa import RenderQAReport
from .resolve_assembly import ResolveAssemblyAdapter, ResolveAssetBindings
from .timebase import FrameRate


@dataclass(slots=True)
class Task036WorkflowRuntime:
    """Trusted, runtime-only bindings for the post-review W2 route."""

    application: Task036EditingApplication
    resolve: Task036ResolveWorkflowFacade
    post_resolve: Task036PostResolveWorkflowFacade
    resolve_adapter: ResolveAssemblyAdapter
    resolve_bindings: ResolveAssetBindings
    timeline_rate: FrameRate
    target_project: str
    render_qa: RenderQAReport | None = None
    render_path: Path | None = None
    handoff_destination: Path | None = None
    subtitle_srt_path: Path | None = None
    resolve_project_snapshot_path: Path | None = None
    audio_roundtrip_exports: tuple[Path, ...] = ()

    def __post_init__(self) -> None:
        if self.resolve.application is not self.application:
            raise ValueError("Resolve workflow must use the bound editing application")
        if self.post_resolve.application is not self.application or self.post_resolve.resolve is not self.resolve:
            raise ValueError("Post-Resolve workflow must use the bound editing/Resolve workflow")
        if not self.target_project.strip():
            raise ValueError("target_project must be non-empty")

    def status(self) -> dict[str, object]:
        plan = self.resolve.assembly_plan
        return {
            "available": True,
            "task_owner": "TASK-036",
            "next_recommended_action": self.application.coordinator.state.next_recommended_action,
            "assembly_prepared": plan is not None,
            "resolve_applied": self.application.coordinator.state.resolve_applied,
            "render_qa_bound": self.application.coordinator.state.render_qa_sha256 is not None,
            "handoff_complete": self.application.coordinator.state.handoff_manifest_sha256 is not None,
            "target_application": "DaVinci Resolve",
            "target_project": self.target_project,
            "target_timeline": None if plan is None else plan.timeline_name,
            "host_paths_exposed": False,
        }

    def compile_resolve_assembly(self) -> dict[str, object]:
        return self.resolve.compile_assembly(timeline_rate=self.timeline_rate)

    def prepare_resolve_apply(self) -> dict[str, object]:
        if self.resolve.assembly_plan is None:
            raise ProductError(
                "ERR_SHELL_RESOLVE_ASSEMBLY_REQUIRED",
                "Resolve apply preparation requires a compiled assembly",
                ProductErrorCategory.STATE,
            )
        return self.resolve.prepare_apply(
            target_project=self.target_project,
            target_timeline=self.resolve.assembly_plan.timeline_name,
        )

    def apply_resolve_assembly(self, confirmation_id: str) -> dict[str, object]:
        if self.resolve.assembly_plan is None:
            raise ProductError(
                "ERR_SHELL_RESOLVE_ASSEMBLY_REQUIRED",
                "Resolve apply requires a compiled assembly",
                ProductErrorCategory.STATE,
            )
        return self.resolve.apply(
            confirmation_id=confirmation_id,
            target_project=self.target_project,
            target_timeline=self.resolve.assembly_plan.timeline_name,
            adapter=self.resolve_adapter,
            bindings=self.resolve_bindings,
        )

    def prepare_native_render_gate(self) -> dict[str, object]:
        return self.post_resolve.prepare_native_render_gate()

    def bind_runtime_render_qa(self) -> dict[str, object]:
        if self.render_qa is None:
            raise ProductError(
                "ERR_SHELL_RUNTIME_RENDER_QA_NOT_BOUND",
                "No trusted runtime Render QA report is bound",
                ProductErrorCategory.STATE,
            )
        return self.post_resolve.bind_render_qa(self.render_qa)

    def create_editor_handoff(self) -> dict[str, object]:
        if self.render_qa is None or self.render_path is None or self.handoff_destination is None:
            raise ProductError(
                "ERR_SHELL_RUNTIME_HANDOFF_INPUT_NOT_BOUND",
                "Trusted runtime Render QA, render path and handoff destination are required",
                ProductErrorCategory.STATE,
            )
        return self.post_resolve.create_editor_handoff(
            self.handoff_destination,
            render_qa=self.render_qa,
            render_path=self.render_path,
            subtitle_srt_path=self.subtitle_srt_path,
            resolve_project_snapshot_path=self.resolve_project_snapshot_path,
            audio_roundtrip_exports=self.audio_roundtrip_exports,
        )
