"""Bound runtime wiring for the TASK-036 minimum-editing desktop workflow.

The browser bridge may select an allowlisted action, but it never supplies host
paths, adapters, Resolve targets, Render QA objects, or external-write authority.
Those values are bound by the trusted desktop composition root before launch.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib
from pathlib import Path
from .desktop_editing_application import Task036EditingApplication
from .desktop_post_resolve_workflow import Task036PostResolveWorkflowFacade
from .desktop_resolve_workflow import Task036ResolveWorkflowFacade
from .desktop_shell import ShellCommand
from .errors import ProductError, ProductErrorCategory
from .export_queue import ExportAuthorityClass, ExportDispatchResult, ExportPreparation
from .durable_product_job import DurableProductJob, DurableProductJobState
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

    @staticmethod
    def _artifact_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return "sha256:" + digest.hexdigest()

    @staticmethod
    def _validate_output_contract(
        report: RenderQAReport, preparation: ExportPreparation,
    ) -> None:
        output = preparation.preset.output
        probe = report.media_probe
        video = next((item for item in probe.streams if item.get("codec_type") == "video"), None)
        audio = next((item for item in probe.streams if item.get("codec_type") == "audio"), None)
        expected_rate = Fraction(output.frame_rate_numerator, output.frame_rate_denominator)
        observed_rate = None
        if video is not None:
            rate = video.get("avg_frame_rate") or video.get("r_frame_rate")
            try:
                observed_rate = None if rate is None else Fraction(str(rate))
            except (ValueError, ZeroDivisionError):
                observed_rate = None
        containers = set((probe.format_name or "").split(","))
        checks = {
            "container": output.container in containers,
            "video_stream": video is not None,
            "video_width": video is not None and video.get("width") == output.width,
            "video_height": video is not None and video.get("height") == output.height,
            "video_codec": video is not None and video.get("codec_name") == output.video_codec,
            "frame_rate": observed_rate == expected_rate,
            "audio_stream": audio is not None,
            "audio_sample_rate": audio is not None and audio.get("sample_rate") == output.audio_sample_rate_hz,
            "audio_channels": audio is not None and audio.get("channels") == output.audio_channels,
            "audio_codec": audio is not None and audio.get("codec_name") == output.audio_codec,
        }
        failed = tuple(name for name, passed in checks.items() if not passed)
        if failed:
            raise ProductError(
                "ERR_TASK036_EXPORT_OUTPUT_CONTRACT",
                "Rendered artifact does not satisfy the exact Export output contract",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"failed_checks": failed},
            )

    def dispatch_export(
        self,
        job: DurableProductJob,
        preparation: ExportPreparation,
        destination: Path,
    ) -> ExportDispatchResult:
        """Run one queue-confirmed native render through the existing port."""

        if job.state is not DurableProductJobState.DISPATCHING:
            raise ProductError(
                "ERR_TASK036_EXPORT_DISPATCH_STATE",
                "Native Export requires a durably DISPATCHING Job",
                ProductErrorCategory.STATE,
            )
        if preparation.authority_class is not ExportAuthorityClass.RESOLVE_RENDER:
            raise ProductError(
                "ERR_TASK036_EXPORT_AUTHORITY_CLASS",
                "The bound native renderer accepts only RESOLVE_RENDER preparations",
                ProductErrorCategory.AUTHORIZATION,
            )
        if self.native_render_port is None:
            raise ProductError(
                "ERR_SHELL_NATIVE_RENDER_PORT_NOT_BOUND",
                "Trusted TASK-011 native render port is not bound",
                ProductErrorCategory.STATE,
            )
        plan = self.resolve.assembly_plan
        if plan is None:
            raise ProductError(
                "ERR_SHELL_RESOLVE_ASSEMBLY_REQUIRED",
                "Native Export requires the exact applied Resolve assembly",
                ProductErrorCategory.STATE,
            )
        plan_body = plan.to_dict()
        if (
            preparation.resolve_project_identity != self.target_project
            or preparation.resolve_timeline_identity != plan.timeline_name
            or preparation.assembly_plan_sha256 != plan_body["assembly_sha256"]
            or preparation.edit_plan_sha256 != plan.source_edit_plan_sha256
        ):
            raise ProductError(
                "ERR_TASK036_EXPORT_PREPARATION_MISMATCH",
                "Export preparation does not match the applied Resolve assembly",
                ProductErrorCategory.STATE,
            )
        # Existing facade verifies that the exact assembly is already applied.
        self.post_resolve.prepare_native_render_gate()
        target = Path(destination)
        if target.is_symlink() or not target.is_absolute():
            raise ProductError(
                "ERR_EXPORT_PRIVATE_DESTINATION",
                "Launcher-private destination is invalid",
                ProductErrorCategory.SECURITY,
            )
        target = target.resolve(strict=False)
        # TASK-011 requires a fresh, dedicated ``render-output`` directory.
        # Bind both its Evidence root and report to this exact durable Job so a
        # successful prior export cannot poison a later job and no old bytes are
        # ever deleted or silently reused.
        if target.name != "render-output":
            raise ProductError(
                "ERR_EXPORT_PRIVATE_DESTINATION",
                "Launcher-private destination is not a dedicated render-output directory",
                ProductErrorCategory.SECURITY,
            )
        job_port = self.native_render_port
        if isinstance(job_port, Task036Task011NativeRenderPort):
            job_evidence_root = target.parent
            job_port = replace(
                job_port,
                evidence_root=job_evidence_root,
                report_path=job_evidence_root / "task011-native-report.json",
            )
        completion = job_port.execute(
            sandbox_project=self.target_project,
            timeline_name=plan.timeline_name,
            expected_duration_frames=plan.expected_duration_frames,
            timeline_rate=plan.timeline_mapping.timeline_rate,
            assembly_sha256=str(plan_body["assembly_sha256"]),
        )
        artifact = completion.render_path
        if (
            artifact.is_symlink()
            or not artifact.is_file()
            or artifact.stat().st_size <= 0
            or artifact.resolve().parent != target
        ):
            raise ProductError(
                "ERR_TASK036_EXPORT_ARTIFACT_BOUNDARY",
                "TASK-011 returned an artifact outside the launcher-private destination",
                ProductErrorCategory.SECURITY,
            )
        report = completion.render_qa
        actual_sha256 = self._artifact_sha256(artifact)
        if (
            report.status != "PASS"
            or report.artifact_sha256 != actual_sha256
            or report.artifact_size_bytes != artifact.stat().st_size
        ):
            raise ProductError(
                "ERR_TASK036_EXPORT_QA_MISMATCH",
                "TASK-011 Render QA does not match the exact output bytes",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        self._validate_output_contract(report, preparation)
        self.render_qa = report
        self.render_path = artifact
        self.post_resolve.bind_render_qa(report)
        return ExportDispatchResult(
            "SUCCEEDED",
            result_identity="render-artifact:" + actual_sha256.split(":", 1)[1],
            render_qa_sha256=str(report.to_dict()["report_sha256"]),
            render_qa_passed=True,
            actual_cost=None,
        )

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
