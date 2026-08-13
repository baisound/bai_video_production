"""TASK-036 post-Resolve application-service wiring for TASK-011/TASK-012.

The native render itself remains behind the TASK-011 real Resolve gate.  This
facade prepares that exact native request, binds a verified RenderQAReport back
into the desktop workflow, and creates the deterministic TASK-012 EDITOR_WORK
handoff after QA passes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .desktop_editing_application import Task036EditingApplication
from .desktop_resolve_workflow import Task036ResolveWorkflowFacade
from .desktop_shell import ShellCommand
from .errors import ProductError, ProductErrorCategory
from .manual_handoff import EditorHandoffService
from .render_qa import RenderQAReport
from .serialization import canonical_json_bytes, sha256_bytes


def _handoff_intent_hash(destination_root: str | Path, render_qa: RenderQAReport) -> str:
    return sha256_bytes(canonical_json_bytes({
        "destination_name": Path(destination_root).name,
        "render_qa_report_sha256": render_qa.to_dict()["report_sha256"],
    }))


@dataclass(slots=True)
class Task036PostResolveWorkflowFacade:
    application: Task036EditingApplication
    resolve: Task036ResolveWorkflowFacade

    def _plan_and_result(self):
        edit_plan = self.application.review.approved_plan
        assembly_plan = self.resolve.assembly_plan
        assembly_result = self.resolve.assembly_result
        if edit_plan is None or assembly_plan is None or assembly_result is None:
            raise ProductError(
                "ERR_SHELL_RESOLVE_APPLY_REQUIRED",
                "Post-Resolve workflow requires the approved Edit Plan and completed TASK-010 apply result",
                ProductErrorCategory.STATE,
            )
        state = self.application.coordinator.state
        if not state.resolve_applied or state.resolve_assembly_sha256 != assembly_plan.to_dict()["assembly_sha256"]:
            raise ProductError(
                "ERR_SHELL_RESOLVE_APPLY_REQUIRED",
                "Desktop session has not recorded the exact completed Resolve assembly",
                ProductErrorCategory.STATE,
            )
        return edit_plan, assembly_plan, assembly_result

    def prepare_native_render_gate(self) -> dict[str, Any]:
        _, assembly_plan, _ = self._plan_and_result()
        project = self.application.shell.project
        if project is None or not project.resolve_project_name or not project.resolve_timeline_name:
            raise ProductError(
                "ERR_SHELL_RESOLVE_TARGET_REQUIRED",
                "Native render requires the exact bound Resolve Project and Timeline",
                ProductErrorCategory.STATE,
            )
        if project.resolve_timeline_name != assembly_plan.timeline_name:
            raise ProductError(
                "ERR_SHELL_RESOLVE_TARGET_INVALID",
                "Bound Resolve Timeline no longer matches the applied assembly",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        rate = assembly_plan.timeline_mapping.timeline_rate
        return {
            "request_version": "1.0.0",
            "task_owner": "TASK-036",
            "native_gate_owner": "TASK-011",
            "status": "READY_FOR_REAL_RESOLVE_NATIVE_GATE",
            "sandbox_project": project.resolve_project_name,
            "timeline_name": project.resolve_timeline_name,
            "expected_duration_frames": assembly_plan.expected_duration_frames,
            "timeline_rate": {"numerator": rate.numerator, "denominator": rate.denominator},
            "explicit_external_write_authorization_required": True,
            "external_mutation_performed": False,
        }

    def bind_render_qa(self, report: RenderQAReport) -> dict[str, Any]:
        _, assembly_plan, _ = self._plan_and_result()
        if report.expected_duration_frames != assembly_plan.expected_duration_frames:
            raise ProductError(
                "ERR_SHELL_RENDER_QA_DURATION_CONTRACT_MISMATCH",
                "Render QA expected duration does not match the applied Resolve assembly",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if report.timeline_rate != assembly_plan.timeline_mapping.timeline_rate:
            raise ProductError(
                "ERR_SHELL_RENDER_QA_RATE_CONTRACT_MISMATCH",
                "Render QA Timeline rate does not match the applied Resolve assembly",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        report_sha = report.to_dict()["report_sha256"]
        self.application.coordinator.bind_render_qa(report_sha256=report_sha, status=report.status)
        return {
            "task_owner": "TASK-036",
            "operation": "RENDER_QA_BIND",
            "report_sha256": report_sha,
            "qa_status": report.status,
            "editing_session": self.application.coordinator.state.to_dict(),
            "available_commands": list(self.application.shell.snapshot().available_commands),
            "next_recommended_action": self.application.coordinator.state.next_recommended_action,
        }

    def create_editor_handoff(
        self,
        destination_root: str | Path,
        *,
        render_qa: RenderQAReport,
        render_path: str | Path,
        subtitle_srt_path: str | Path | None = None,
        resolve_project_snapshot_path: str | Path | None = None,
        audio_roundtrip_exports: Iterable[str | Path] = (),
    ) -> dict[str, Any]:
        edit_plan, _, assembly_result = self._plan_and_result()
        state = self.application.coordinator.state
        report_sha = render_qa.to_dict()["report_sha256"]
        if state.render_qa_sha256 != report_sha or state.render_qa_status != "PASS":
            raise ProductError(
                "ERR_SHELL_RENDER_QA_PASS_REQUIRED",
                "EDITOR_WORK creation requires the exact PASS Render QA currently bound to the desktop session",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        project = self.application.shell.project
        if project is None:
            raise ProductError("ERR_SHELL_PROJECT_REQUIRED", "No Project is open", ProductErrorCategory.STATE)
        intent_hash = _handoff_intent_hash(destination_root, render_qa)
        hashes = {
            "edit_plan_sha256": edit_plan.to_dict()["plan_sha256"],
            "assembly_sha256": assembly_result.assembly_sha256,
            "render_qa_report_sha256": report_sha,
            "handoff_intent_sha256": intent_hash,
        }
        command = ShellCommand(
            command_id=f"handoff-create-{project.context_revision}",
            command_type="handoff.create",
            project_id=project.project_id,
            expected_context_revision=project.context_revision,
            expected_upstream_hashes=hashes,
            payload={
                "destination_name": Path(destination_root).name,
                "render_qa_report_sha256": report_sha,
            },
        )
        runtime: dict[str, Any] = {}

        def execute(_: ShellCommand) -> Mapping[str, Any]:
            root, manifest = EditorHandoffService.prepare(
                destination_root,
                edit_plan=edit_plan,
                assembly_result=assembly_result,
                render_qa=render_qa,
                render_path=render_path,
                subtitle_srt_path=subtitle_srt_path,
                resolve_project_snapshot_path=resolve_project_snapshot_path,
                audio_roundtrip_exports=audio_roundtrip_exports,
            )
            manifest_sha = manifest.to_dict()["manifest_sha256"]
            self.application.coordinator.bind_handoff(manifest_sha)
            runtime["root"] = root
            return {
                "handoff_id": manifest.handoff_id,
                "manifest_sha256": manifest_sha,
                "absolute_path_persisted": False,
                "editing_session": self.application.coordinator.state.to_dict(),
            }

        receipt = self.application.shell.dispatch(command, executor=execute)
        return {
            "receipt": receipt,
            "runtime_editor_work_root": str(runtime["root"]),
            "runtime_path_persisted": False,
            "editing_session": self.application.coordinator.state.to_dict(),
            "next_recommended_action": self.application.coordinator.state.next_recommended_action,
        }
