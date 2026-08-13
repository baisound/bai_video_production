"""Trusted TASK-011 native-render port for the TASK-036 desktop runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import ProductError, ProductErrorCategory
from .render_qa import LoudnessProfile, RenderQAReport, RenderQAService
from .resolve_loader import ResolveModuleLoader
from .task011_native_render_gate import Task011NativeRenderGateRunner, Task011NativeRenderRequest
from .timebase import FrameRate


@dataclass(frozen=True, slots=True)
class NativeRenderCompletion:
    render_qa: RenderQAReport
    render_path: Path
    native_evidence_report_sha256: str


@dataclass(slots=True)
class Task036Task011NativeRenderPort:
    """Run one bounded TASK-011 render using Python-only configuration."""

    evidence_root: Path
    report_path: Path
    duration_tolerance_frames: int = 2
    timeout_seconds: int = 1800
    poll_interval_seconds: float = 1.0
    render_format: str | None = None
    render_codec: str | None = None
    loudness_profile: LoudnessProfile | None = LoudnessProfile()
    loader: ResolveModuleLoader | Any | None = None
    qa_service: RenderQAService | Any | None = None

    @property
    def destination_label(self) -> str:
        return self.evidence_root.name

    @staticmethod
    def _single_render_artifact(render_directory: Path) -> Path:
        files = tuple(
            item
            for item in render_directory.iterdir()
            if item.is_file() and not item.is_symlink() and item.stat().st_size > 0
        )
        if len(files) != 1:
            raise ProductError(
                "ERR_TASK036_NATIVE_RENDER_ARTIFACT_AMBIGUOUS",
                "TASK-011 completion did not leave exactly one trusted render artifact",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"artifact_count": len(files)},
            )
        return files[0]

    def execute(
        self,
        *,
        sandbox_project: str,
        timeline_name: str,
        expected_duration_frames: int,
        timeline_rate: FrameRate,
        assembly_sha256: str,
    ) -> NativeRenderCompletion:
        request = Task011NativeRenderRequest(
            sandbox_project=sandbox_project,
            timeline_name=timeline_name,
            expected_duration_frames=expected_duration_frames,
            evidence_root=self.evidence_root,
            assembly_sha256=assembly_sha256,
            duration_tolerance_frames=self.duration_tolerance_frames,
            timeout_seconds=self.timeout_seconds,
            poll_interval_seconds=self.poll_interval_seconds,
            render_format=self.render_format,
            render_codec=self.render_codec,
            loudness_profile=self.loudness_profile,
        )
        runner = Task011NativeRenderGateRunner(
            request,
            loader=self.loader,
            qa_service=self.qa_service,
        )
        native_report = runner.run(
            explicit_external_write_authorization=True,
            output_path=self.report_path,
        )
        render_path = self._single_render_artifact(self.evidence_root.resolve() / "render-output")
        qa = runner.qa_service.verify(
            render_path,
            expected_duration_frames=expected_duration_frames,
            timeline_rate=timeline_rate,
            duration_tolerance_frames=self.duration_tolerance_frames,
            require_video=True,
            require_audio=True,
            loudness_profile=self.loudness_profile,
        )
        if qa.to_dict()["report_sha256"] != native_report["qa_report"]["report_sha256"]:
            raise ValueError("TASK-011 runtime QA identity changed during trusted binding")
        return NativeRenderCompletion(
            qa,
            render_path,
            str(native_report["report_sha256"]),
        )
