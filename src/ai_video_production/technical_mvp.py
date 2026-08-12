"""Application-service boundary for the TASK-007 -> 010 -> 011 -> 012 editing MVP."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .cut_candidates import CutCandidateManifest
from .edit_plan import CandidateReviewDecision, EditPlan, EditPlanService
from .manual_handoff import EditorHandoffManifest, EditorHandoffService
from .render_qa import LoudnessProfile, RenderQAReport, RenderQAService
from .resolve_assembly import (
    AudioPlacement,
    ResolveAssemblyAdapter,
    ResolveAssemblyPlan,
    ResolveAssemblyResult,
    ResolveAssemblyService,
    ResolveAssetBindings,
)
from .resolve_subtitle_handoff import ResolveSubtitlePlacementPlan
from .timebase import FrameRate


@dataclass(slots=True)
class TechnicalMvpApplicationService:
    """Headless orchestration contract intended for the future unified Desktop Shell.

    The service intentionally owns no terminal/browser UX. Desktop workspaces can
    bind Project/Asset/Edit state to this API without changing TASK contracts.
    """

    render_qa_service: RenderQAService

    @classmethod
    def default(cls) -> "TechnicalMvpApplicationService":
        return cls(RenderQAService())

    def build_edit_plan(
        self,
        manifest: CutCandidateManifest,
        *,
        reviews: Iterable[CandidateReviewDecision],
        target_duration_us: int | None = None,
        approve: bool = False,
        approved_by: str | None = None,
    ) -> EditPlan:
        return EditPlanService.build(
            manifest,
            reviews=reviews,
            target_duration_us=target_duration_us,
            approve=approve,
            approved_by=approved_by,
        )

    def compile_resolve_assembly(
        self,
        edit_plan: EditPlan,
        *,
        timeline_rate: FrameRate,
        timeline_origin_frame: int = 0,
        subtitle_plan: ResolveSubtitlePlacementPlan | None = None,
        audio_placements: tuple[AudioPlacement, ...] = (),
    ) -> ResolveAssemblyPlan:
        return ResolveAssemblyService.compile(
            edit_plan,
            timeline_rate=timeline_rate,
            timeline_origin_frame=timeline_origin_frame,
            subtitle_plan=subtitle_plan,
            audio_placements=audio_placements,
        )

    def execute_resolve_assembly(
        self,
        plan: ResolveAssemblyPlan,
        *,
        adapter: ResolveAssemblyAdapter,
        bindings: ResolveAssetBindings,
        explicit_external_write_authorization: bool,
    ) -> ResolveAssemblyResult:
        return ResolveAssemblyService.execute(
            plan,
            adapter=adapter,
            bindings=bindings,
            explicit_external_write_authorization=explicit_external_write_authorization,
        )

    def verify_render(
        self,
        render_path: str | Path,
        *,
        assembly_plan: ResolveAssemblyPlan,
        duration_tolerance_frames: int = 2,
        loudness_profile: LoudnessProfile | None = LoudnessProfile(),
    ) -> RenderQAReport:
        return self.render_qa_service.verify(
            render_path,
            expected_duration_frames=assembly_plan.expected_duration_frames,
            timeline_rate=assembly_plan.timeline_mapping.timeline_rate,
            duration_tolerance_frames=duration_tolerance_frames,
            loudness_profile=loudness_profile,
        )

    def prepare_editor_handoff(
        self,
        destination_root: str | Path,
        *,
        edit_plan: EditPlan,
        assembly_result: ResolveAssemblyResult,
        render_qa: RenderQAReport,
        render_path: str | Path,
        subtitle_srt_path: str | Path | None = None,
        resolve_project_snapshot_path: str | Path | None = None,
        audio_roundtrip_exports: Iterable[str | Path] = (),
    ) -> tuple[Path, EditorHandoffManifest]:
        return EditorHandoffService.prepare(
            destination_root,
            edit_plan=edit_plan,
            assembly_result=assembly_result,
            render_qa=render_qa,
            render_path=render_path,
            subtitle_srt_path=subtitle_srt_path,
            resolve_project_snapshot_path=resolve_project_snapshot_path,
            audio_roundtrip_exports=audio_roundtrip_exports,
        )
