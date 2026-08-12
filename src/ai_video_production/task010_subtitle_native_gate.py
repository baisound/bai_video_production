"""TASK-010 edit-aware subtitle semantic native validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import subprocess
from typing import Any

from .atomic import AtomicJsonWriter
from .cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from .edit_plan import CandidateReviewDecision, EditDecision, EditPlanService
from .errors import ProductError, ProductErrorCategory
from .resolve_assembly import ResolveAssemblyService, ResolveAssetBindings, ResolveScriptingAssemblyAdapter
from .resolve_capabilities import authorize_mutation_probe
from .resolve_loader import ResolveModuleLoader
from .resolve_subtitle_handoff import ResolveSubtitleHandoffService
from .serialization import sha256_bytes
from .subtitle_edit_remap import SubtitleEditAction
from .subtitle_workspace import SrtWorkspaceCodec, SubtitleOrigin, SubtitleReviewState, SubtitleWorkspace, WorkspaceCue
from .timebase import FrameRate

_SHA = lambda ch: "sha256:" + ch * 64


@dataclass(frozen=True, slots=True)
class SubtitleSemanticObservation:
    subtitle_track_count: int
    item_count: int
    timing_verified: bool
    text_verified: bool
    items: tuple[dict[str, Any], ...]

    @property
    def passed(self) -> bool:
        return self.subtitle_track_count >= 1 and self.item_count >= 1 and self.timing_verified and self.text_verified


def _approved_edit_plan():
    manifest = CutCandidateManifest(
        "ASSET-00000000000000000000000031", _SHA("a"), 48_000, 4_000_000, _SHA("b"), None,
        (CutCandidate("cut-000001", CutCandidateKind.SILENCE, 1_000_000, 2_000_000, 90, ("FFMPEG_SILENCEDETECT",)),),
        (),
    )
    return EditPlanService.build(
        manifest,
        reviews=(CandidateReviewDecision("cut-000001", EditDecision.CUT),),
        approve=True,
        approved_by="native-subtitle-gate",
    )


def _approved_subtitle_workspace() -> SubtitleWorkspace:
    return SubtitleWorkspace(
        "TASK010-SUBTITLE-NATIVE",
        0,
        (
            WorkspaceCue("native-sub-001", 250, 750, "BAI subtitle alpha", "BAI subtitle alpha", SubtitleOrigin.HUMAN, SubtitleReviewState.APPROVED),
            WorkspaceCue("native-sub-002", 2250, 2950, "BAI subtitle beta", "BAI subtitle beta", SubtitleOrigin.HUMAN, SubtitleReviewState.APPROVED),
        ),
    )


def inspect_subtitle_semantics(timeline: Any, *, expected_cues: tuple[Any, ...], timeline_origin_frame: int) -> SubtitleSemanticObservation:
    track_count = int(timeline.GetTrackCount("subtitle"))
    items = timeline.GetItemListInTrack("subtitle", 1) if track_count >= 1 else []
    items = items if isinstance(items, (list, tuple)) else []
    timeline_start = int(timeline.GetStartFrame())
    expected = [cue for cue in expected_cues if cue.action is SubtitleEditAction.KEEP]
    observations: list[dict[str, Any]] = []
    timing_ok = len(items) == len(expected)
    text_ok = len(items) == len(expected)
    for item, cue in zip(items, expected):
        start = int(item.GetStart()) - timeline_start + timeline_origin_frame
        end = int(item.GetEnd()) - timeline_start + timeline_origin_frame
        name = str(item.GetName())
        observations.append({"cue_id": cue.cue_id, "name": name, "relative_start_frame": start, "relative_end_frame": end})
        timing_ok = timing_ok and start == cue.timeline_start_frame and end == cue.timeline_end_frame
        text_ok = text_ok and sha256_bytes(name.encode("utf-8")) == cue.text_sha256
    return SubtitleSemanticObservation(track_count, len(items), timing_ok, text_ok, tuple(observations))


class Task010SubtitleNativeGateRunner:
    def __init__(self, *, sandbox_project: str, evidence_root: str | Path, loader: ResolveModuleLoader | None = None, ffmpeg_executable: str = "ffmpeg") -> None:
        if not sandbox_project.startswith("BAI_CAPABILITY_PROBE_"):
            raise ValueError("sandbox_project must use BAI_CAPABILITY_PROBE_* prefix")
        self.sandbox_project = sandbox_project
        self.evidence_root = Path(evidence_root).expanduser().resolve()
        self.loader = loader or ResolveModuleLoader()
        self.ffmpeg_executable = ffmpeg_executable

    def _project(self) -> tuple[Any, Any, Any]:
        resolve, _ = self.loader.connect()
        manager = resolve.GetProjectManager()
        project = manager.GetCurrentProject() if manager is not None else None
        if manager is None or project is None:
            raise ProductError("ERR_TASK010_SUBTITLE_CURRENT_PROJECT_REQUIRED", "open the intended subtitle sandbox Project", ProductErrorCategory.EXTERNAL_DEPENDENCY)
        name = project.GetName()
        authorize_mutation_probe(allow_mutation=True, sandbox_project=self.sandbox_project, current_project_name=name)
        if name != self.sandbox_project:
            raise ProductError("ERR_TASK010_SUBTITLE_SANDBOX_MISMATCH", "current Resolve Project does not exactly match subtitle sandbox", ProductErrorCategory.SECURITY)
        return resolve, manager, project

    def _generate_source(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run([
            self.ffmpeg_executable, "-hide_banner", "-nostdin", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30:duration=4",
            "-f", "lavfi", "-i", "sine=frequency=880:sample_rate=48000:duration=4",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path),
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", shell=False, timeout=180, check=False)
        if proc.returncode != 0 or not path.is_file() or path.stat().st_size <= 0:
            raise ProductError("ERR_TASK010_SUBTITLE_SOURCE_GENERATION_FAILED", "could not generate subtitle native source fixture", ProductErrorCategory.EXTERNAL_DEPENDENCY, details={"ffmpeg_exit_code": proc.returncode})

    def run(self, *, output_path: str | Path) -> dict[str, Any]:
        resolve, _, project = self._project()
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        adapter = ResolveScriptingAssemblyAdapter(self.loader)
        project_rate = adapter.current_project_timeline_rate()
        source = self.evidence_root / "generated-sources" / "subtitle-source.mp4"
        self._generate_source(source)
        workspace = _approved_subtitle_workspace()
        subtitle_plan = ResolveSubtitleHandoffService.build(workspace, timeline_rate=project_rate, timeline_origin_frame=0, track_index=1)
        srt_path = self.evidence_root / "subtitle-fixture.srt"
        srt_path.write_text(SrtWorkspaceCodec.render(workspace), encoding="utf-8", newline="\n")
        derived = self.evidence_root / "subtitle-derived-edit-aware.srt"
        assembly_plan = ResolveAssemblyService.compile(_approved_edit_plan(), timeline_rate=project_rate, subtitle_plan=subtitle_plan)
        result = ResolveAssemblyService.execute(
            assembly_plan,
            adapter=adapter,
            bindings=ResolveAssetBindings(source, source_frame_rate=FrameRate(30), subtitle_srt_path=srt_path, subtitle_derived_srt_path=derived),
            explicit_external_write_authorization=True,
        )
        timeline = adapter._find_timeline(project, assembly_plan.timeline_name)
        if timeline is None:
            raise ProductError("ERR_TASK010_SUBTITLE_TIMELINE_MISSING", "subtitle Automation Timeline was not found after execution", ProductErrorCategory.DATA_INTEGRITY)
        observation = inspect_subtitle_semantics(timeline, expected_cues=assembly_plan.subtitle_cues, timeline_origin_frame=assembly_plan.timeline_mapping.timeline_origin_frame)
        status = "PASS" if observation.passed else "FAIL"
        report = {
            "report_version": "2.0.0",
            "task_owner": "TASK-010",
            "gate": "SUBTITLE_NATIVE_SEMANTIC_VALIDATION",
            "status": status,
            "decision": "EDIT_AWARE_SUBTITLE_SEMANTICS_VALIDATED" if status == "PASS" else "SUBTITLE_SEMANTICS_NOT_PROVEN",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sandbox_project": self.sandbox_project,
            "project_timeline_rate": project_rate.to_rational(),
            "assembly": result.to_dict(),
            "subtitle": {
                "source_plan_sha256": subtitle_plan.to_dict()["plan_sha256"],
                "source_cue_count": len(subtitle_plan.placements),
                "kept_cue_count": sum(c.action is SubtitleEditAction.KEEP for c in assembly_plan.subtitle_cues),
                "dropped_cue_count": sum(c.action is SubtitleEditAction.DROP_CUT for c in assembly_plan.subtitle_cues),
                "derived_srt_file_name": derived.name,
                "planned_cues": [c.to_dict() for c in assembly_plan.subtitle_cues],
            },
            "observation": {
                "subtitle_track_count": observation.subtitle_track_count,
                "item_count": observation.item_count,
                "timing_verified": observation.timing_verified,
                "text_verified": observation.text_verified,
                "items": list(observation.items),
            },
            "host_absolute_paths_persisted": False,
        }
        output = Path(output_path)
        if not output.is_absolute():
            output = self.evidence_root / output
        AtomicJsonWriter.write(output.expanduser().resolve(), report)
        return report
