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
from .desktop_shell import ShellCommand
from .errors import ProductError, ProductErrorCategory
from .render_qa import RenderQAReport
from .resolve_assembly import ResolveAssemblyAdapter, ResolveAssetBindings
from .serialization import canonical_json_bytes, sha256_bytes
from .task036_native_render_port import Task036Task011NativeRenderPort
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
    native_render_port: Task036Task011NativeRenderPort | None = None
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

    def _native_render_hashes(self) -> dict[str, str]:
        plan = self.resolve.assembly_plan
        if plan is None:
            raise ProductError(
                "ERR_SHELL_RESOLVE_ASSEMBLY_REQUIRED",
                "Native render requires the exact applied Resolve assembly",
                ProductErrorCategory.STATE,
            )
        target = {
            "project": self.target_project,
            "timeline": plan.timeline_name,
            "expected_duration_frames": plan.expected_duration_frames,
            "timeline_rate": plan.timeline_mapping.timeline_rate.to_rational(),
        }
        return {
            "assembly_sha256": plan.to_dict()["assembly_sha256"],
            "render_target_sha256": sha256_bytes(canonical_json_bytes(target)),
        }

    def prepare_native_render_confirmation(self) -> dict[str, object]:
        if self.native_render_port is None:
            raise ProductError(
                "ERR_SHELL_NATIVE_RENDER_PORT_NOT_BOUND",
                "Trusted TASK-011 native render port is not bound",
                ProductErrorCategory.STATE,
            )
        gate = self.post_resolve.prepare_native_render_gate()
        confirmation = self.application.shell.prepare_confirmation(
            command_type="render.start",
            expected_upstream_hashes=self._native_render_hashes(),
            target_application="DaVinci Resolve",
            target_project=str(gate["sandbox_project"]),
            target_timeline=str(gate["timeline_name"]),
            destination=self.native_render_port.destination_label,
        )
        return {**gate, **confirmation}

    def execute_native_render(self, confirmation_id: str) -> dict[str, object]:
        if self.native_render_port is None:
            raise ProductError(
                "ERR_SHELL_NATIVE_RENDER_PORT_NOT_BOUND",
                "Trusted TASK-011 native render port is not bound",
                ProductErrorCategory.STATE,
            )
        plan = self.resolve.assembly_plan
        project = self.application.shell.project
        if plan is None or project is None:
            raise ProductError(
                "ERR_SHELL_RESOLVE_ASSEMBLY_REQUIRED",
                "Native render requires the exact applied Resolve assembly",
                ProductErrorCategory.STATE,
            )
        command = ShellCommand(
            command_id=f"render-start-{project.context_revision}",
            command_type="render.start",
            project_id=project.project_id,
            expected_context_revision=project.context_revision,
            expected_upstream_hashes=self._native_render_hashes(),
            payload={
                "sandbox_project": self.target_project,
                "timeline_name": plan.timeline_name,
                "evidence_destination": self.native_render_port.destination_label,
            },
            confirmation_id=confirmation_id,
        )

        def execute(_: ShellCommand) -> dict[str, object]:
            completion = self.native_render_port.execute(
                sandbox_project=self.target_project,
                timeline_name=plan.timeline_name,
                expected_duration_frames=plan.expected_duration_frames,
                timeline_rate=plan.timeline_mapping.timeline_rate,
                assembly_sha256=plan.to_dict()["assembly_sha256"],
            )
            self.render_qa = completion.render_qa
            self.render_path = completion.render_path
            binding = self.post_resolve.bind_render_qa(completion.render_qa)
            return {
                "native_evidence_report_sha256": completion.native_evidence_report_sha256,
                "render_artifact_path_persisted": False,
                "qa_binding": binding,
            }

        receipt = self.application.shell.dispatch(command, executor=execute)
        return {
            "task_owner": "TASK-036",
            "operation": "NATIVE_RENDER_AND_QA_BIND",
            "receipt": receipt,
            "render_artifact_path_persisted": False,
            "external_mutation_performed": True,
            "editing_session": self.application.coordinator.state.to_dict(),
            "next_recommended_action": self.application.coordinator.state.next_recommended_action,
        }

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
