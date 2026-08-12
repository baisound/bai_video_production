"""TASK-010 Windows/Resolve native acceptance harness.

This module is intentionally an internal validation harness, not a product UI.
It only mutates an explicitly named BAI_CAPABILITY_PROBE_* Resolve Project and
persists redacted Evidence without host absolute paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable

from .atomic import AtomicJsonWriter
from .cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from .edit_plan import CandidateReviewDecision, EditDecision, EditPlan, EditPlanService
from .errors import ProductError, ProductErrorCategory
from .resolve_assembly import (
    ResolveAssemblyPlan,
    ResolveAssemblyResult,
    ResolveAssemblyService,
    ResolveAssetBindings,
    ResolveScriptingAssemblyAdapter,
)
from .resolve_capabilities import authorize_mutation_probe
from .resolve_loader import ResolveModuleLoader
from .serialization import canonical_json_bytes, sha256_bytes
from .timebase import FrameRate


_SANDBOX_RE = re.compile(r"^BAI_CAPABILITY_PROBE_[A-Za-z0-9_-]+$")
_SHA = lambda ch: "sha256:" + ch * 64


@dataclass(frozen=True, slots=True)
class Task010NativeCase:
    case_id: str
    asset_id: str
    source_rate: FrameRate
    source_duration_us: int = 4_000_000
    cut_start_us: int = 1_000_000
    cut_end_us: int = 2_000_000

    def __post_init__(self) -> None:
        if not self.case_id or not re.fullmatch(r"[A-Z0-9_-]+", self.case_id):
            raise ValueError("case_id must be ASCII uppercase/digit/_/-")
        if self.source_duration_us <= 0:
            raise ValueError("source_duration_us must be positive")
        if not 0 <= self.cut_start_us < self.cut_end_us <= self.source_duration_us:
            raise ValueError("cut range must be within source duration")


def task010_native_cases() -> tuple[Task010NativeCase, ...]:
    return (
        Task010NativeCase(
            "SRC30_PROJECT_RATE",
            "ASSET-00000000000000000000000001",
            FrameRate(30),
        ),
        Task010NativeCase(
            "SRC60_PROJECT_RATE",
            "ASSET-00000000000000000000000002",
            FrameRate(60),
        ),
        Task010NativeCase(
            "SRC30000_1001_PROJECT_RATE",
            "ASSET-00000000000000000000000003",
            FrameRate(30_000, 1_001),
        ),
    )


def build_task010_edit_plan(case: Task010NativeCase, *, approved_by: str = "native-gate") -> EditPlan:
    upstream = CutCandidateManifest(
        case.asset_id,
        _SHA("a"),
        48_000,
        case.source_duration_us,
        _SHA("b"),
        None,
        (
            CutCandidate(
                "cut-000001",
                CutCandidateKind.SILENCE,
                case.cut_start_us,
                case.cut_end_us,
                90,
                ("FFMPEG_SILENCEDETECT",),
            ),
        ),
        (),
    )
    return EditPlanService.build(
        upstream,
        reviews=(CandidateReviewDecision("cut-000001", EditDecision.CUT),),
        approve=True,
        approved_by=approved_by,
    )


def build_task010_assembly_plan(
    case: Task010NativeCase,
    *,
    timeline_rate: FrameRate,
) -> tuple[EditPlan, ResolveAssemblyPlan]:
    edit_plan = build_task010_edit_plan(case)
    return edit_plan, ResolveAssemblyService.compile(edit_plan, timeline_rate=timeline_rate)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _rate_arg(rate: FrameRate) -> str:
    return rate.to_rational()


def _timeline_count(project: Any) -> int | None:
    fn = getattr(project, "GetTimelineCount", None)
    if not callable(fn):
        return None
    try:
        return int(fn())
    except Exception:
        return None


def _track_item_count(timeline: Any, track_type: str, track_index: int = 1) -> int | None:
    fn = getattr(timeline, "GetItemListInTrack", None)
    if not callable(fn):
        return None
    try:
        value = fn(track_type, track_index)
    except Exception:
        return None
    if isinstance(value, (list, tuple, dict)):
        return len(value)
    return None


def _item_track_type(item: Any) -> tuple[str | None, int | None]:
    fn = getattr(item, "GetTrackTypeAndIndex", None)
    if not callable(fn):
        return None, None
    try:
        value = fn()
    except Exception:
        return None, None
    if isinstance(value, dict):
        track_type = value.get("trackType") or value.get("track_type")
        index = value.get("trackIndex") or value.get("track_index")
        return (
            str(track_type).lower() if track_type is not None else None,
            int(index) if isinstance(index, (int, float)) else None,
        )
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        track_type, index = value[0], value[1]
        return (
            str(track_type).lower() if track_type is not None else None,
            int(index) if isinstance(index, (int, float)) else None,
        )
    return None, None


class Task010NativeGateRunner:
    """Execute bounded TASK-010 native Evidence in a Resolve sandbox Project."""

    def __init__(
        self,
        *,
        sandbox_project: str,
        evidence_root: str | Path,
        loader: ResolveModuleLoader | None = None,
        ffmpeg_executable: str = "ffmpeg",
        ffprobe_executable: str = "ffprobe",
        require_fresh_assembly: bool = True,
    ) -> None:
        if _SANDBOX_RE.fullmatch(sandbox_project) is None:
            raise ValueError("sandbox_project must match BAI_CAPABILITY_PROBE_* safe naming")
        self.sandbox_project = sandbox_project
        self.evidence_root = Path(evidence_root).expanduser().resolve()
        self.loader = loader or ResolveModuleLoader()
        self.ffmpeg_executable = ffmpeg_executable
        self.ffprobe_executable = ffprobe_executable
        self.require_fresh_assembly = require_fresh_assembly

    def _project(self) -> tuple[Any, Any, Any]:
        resolve, source = self.loader.connect()
        manager = getattr(resolve, "GetProjectManager", lambda: None)()
        project = getattr(manager, "GetCurrentProject", lambda: None)() if manager is not None else None
        if manager is None or project is None:
            raise ProductError(
                "ERR_TASK010_NATIVE_CURRENT_PROJECT_REQUIRED",
                "open the intended Resolve sandbox Project before native validation",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            )
        name_fn = getattr(project, "GetName", None)
        try:
            current_name = name_fn() if callable(name_fn) else None
        except Exception:
            current_name = None
        if not isinstance(current_name, str) or not current_name:
            raise ProductError(
                "ERR_TASK010_NATIVE_PROJECT_NAME_UNVERIFIED",
                "current Resolve Project name could not be verified",
                ProductErrorCategory.SECURITY,
            )
        authorize_mutation_probe(
            allow_mutation=True,
            sandbox_project=self.sandbox_project,
            current_project_name=current_name,
        )
        if current_name != self.sandbox_project:
            raise ProductError(
                "ERR_TASK010_NATIVE_SANDBOX_MISMATCH",
                "current Resolve Project does not exactly match the authorized sandbox",
                ProductErrorCategory.SECURITY,
                details={"expected": self.sandbox_project, "observed": current_name},
            )
        return resolve, manager, project

    @staticmethod
    def _run(argv: list[str], *, timeout_seconds: int = 120) -> subprocess.CompletedProcess[str]:
        try:
            proc = subprocess.run(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                check=False,
                shell=False,
            )
        except FileNotFoundError as exc:
            raise ProductError(
                "ERR_TASK010_NATIVE_TOOL_NOT_FOUND",
                f"required executable is unavailable: {argv[0]}",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ProductError(
                "ERR_TASK010_NATIVE_TOOL_TIMEOUT",
                f"native validation command timed out: {argv[0]}",
                ProductErrorCategory.TIMEOUT,
                retryable=True,
            ) from exc
        return proc

    def _generate_source(self, case: Task010NativeCase, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        seconds = f"{case.source_duration_us / 1_000_000:.6f}"
        rate = _rate_arg(case.source_rate)
        argv = [
            self.ffmpeg_executable,
            "-hide_banner",
            "-nostdin",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size=640x360:rate={rate}:duration={seconds}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=1000:sample_rate=48000:duration={seconds}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(target),
        ]
        proc = self._run(argv, timeout_seconds=180)
        if proc.returncode != 0 or not target.is_file() or target.stat().st_size <= 0:
            raise ProductError(
                "ERR_TASK010_NATIVE_SOURCE_GENERATION_FAILED",
                "FFmpeg could not generate the native validation source",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                details={"case_id": case.case_id, "ffmpeg_exit_code": proc.returncode},
            )

    def _probe_source(self, path: Path, expected_rate: FrameRate) -> dict[str, Any]:
        argv = [
            self.ffprobe_executable,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,avg_frame_rate,r_frame_rate,width,height",
            "-of",
            "json",
            str(path),
        ]
        proc = self._run(argv, timeout_seconds=60)
        if proc.returncode != 0:
            raise ProductError(
                "ERR_TASK010_NATIVE_SOURCE_PROBE_FAILED",
                "ffprobe failed to inspect generated source",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                details={"ffprobe_exit_code": proc.returncode},
            )
        try:
            doc = json.loads(proc.stdout)
            stream = doc["streams"][0]
            avg = FrameRate.parse(str(stream["avg_frame_rate"]))
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProductError(
                "ERR_TASK010_NATIVE_SOURCE_PROBE_INVALID",
                "ffprobe returned unusable source timing metadata",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if avg != expected_rate:
            raise ProductError(
                "ERR_TASK010_NATIVE_SOURCE_RATE_MISMATCH",
                "generated source frame rate does not match the requested native case",
                ProductErrorCategory.DATA_INTEGRITY,
                details={
                    "expected": expected_rate.to_rational(),
                    "observed": avg.to_rational(),
                },
            )
        return {
            "codec_name": stream.get("codec_name"),
            "avg_frame_rate": avg.to_rational(),
            "r_frame_rate": str(stream.get("r_frame_rate")),
            "width": stream.get("width"),
            "height": stream.get("height"),
            "sha256": _sha256_file(path),
            "size_bytes": path.stat().st_size,
        }

    def _inspect_assembly_timeline(
        self,
        *,
        project: Any,
        adapter: ResolveScriptingAssemblyAdapter,
        plan: ResolveAssemblyPlan,
    ) -> dict[str, Any]:
        timeline = adapter._find_timeline(project, plan.timeline_name)
        if timeline is None:
            raise ProductError(
                "ERR_TASK010_NATIVE_TIMELINE_MISSING",
                "expected BAI_AUTO timeline was not found after assembly",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"timeline_name": plan.timeline_name},
            )
        marker_hash = adapter._marker_hash(timeline)
        expected_hash = plan.to_dict()["assembly_sha256"]
        if marker_hash != expected_hash:
            raise ProductError(
                "ERR_TASK010_NATIVE_MARKER_MISMATCH",
                "assembly idempotency marker did not match the expected plan hash",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"timeline_name": plan.timeline_name},
            )

        start_fn = getattr(timeline, "GetStartFrame", None)
        end_fn = getattr(timeline, "GetEndFrame", None)
        start = start_fn() if callable(start_fn) else None
        end = end_fn() if callable(end_fn) else None
        return {
            "timeline_name": plan.timeline_name,
            "assembly_sha256": expected_hash,
            "marker_verified": True,
            "video_track_1_item_count": _track_item_count(timeline, "video", 1),
            "audio_track_1_item_count": _track_item_count(timeline, "audio", 1),
            "timeline_start_frame": start if isinstance(start, (int, float)) else None,
            "timeline_end_frame": end if isinstance(end, (int, float)) else None,
        }

    def _run_case(self, case: Task010NativeCase, *, source_dir: Path) -> dict[str, Any]:
        _, _, project = self._project()
        source = source_dir / f"{case.case_id.lower()}.mp4"
        self._generate_source(case, source)
        source_probe = self._probe_source(source, case.source_rate)

        adapter = ResolveScriptingAssemblyAdapter(self.loader)
        timeline_rate = adapter.current_project_timeline_rate()
        edit_plan, assembly_plan = build_task010_assembly_plan(case, timeline_rate=timeline_rate)
        before = _timeline_count(project)

        first = ResolveAssemblyService.execute(
            assembly_plan,
            adapter=adapter,
            bindings=ResolveAssetBindings(source, source_frame_rate=case.source_rate),
            explicit_external_write_authorization=True,
        )
        after_first = _timeline_count(project)
        timeline_evidence = self._inspect_assembly_timeline(
            project=project,
            adapter=adapter,
            plan=assembly_plan,
        )
        expected_keep_items = len(assembly_plan.timeline_mapping.placements)
        video_count = timeline_evidence["video_track_1_item_count"]
        audio_count = timeline_evidence["audio_track_1_item_count"]
        if video_count is not None and video_count < expected_keep_items:
            raise ProductError(
                "ERR_TASK010_NATIVE_SOURCE_VIDEO_NOT_PRESERVED",
                "native product assembly did not retain every planned source video keep range",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"case_id": case.case_id},
            )
        if audio_count is not None and audio_count < expected_keep_items:
            raise ProductError(
                "ERR_TASK010_NATIVE_SOURCE_AUDIO_NOT_PRESERVED",
                "native product assembly did not retain linked source audio for every keep range",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"case_id": case.case_id},
            )
        replay = ResolveAssemblyService.execute(
            assembly_plan,
            adapter=adapter,
            bindings=ResolveAssetBindings(source, source_frame_rate=case.source_rate),
            explicit_external_write_authorization=True,
        )
        after_replay = _timeline_count(project)

        if replay.status != "ALREADY_APPLIED" or not replay.reused_existing:
            raise ProductError(
                "ERR_TASK010_NATIVE_IDEMPOTENCY_REPLAY_FAILED",
                "second execution did not resolve to ALREADY_APPLIED",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"case_id": case.case_id, "status": replay.status},
            )
        if after_first is not None and after_replay is not None and after_first != after_replay:
            raise ProductError(
                "ERR_TASK010_NATIVE_IDEMPOTENCY_MUTATED",
                "idempotent replay changed the Resolve timeline count",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"case_id": case.case_id},
            )
        if self.require_fresh_assembly and first.status != "APPLIED":
            raise ProductError(
                "ERR_TASK010_NATIVE_FRESH_ASSEMBLY_REQUIRED",
                "native gate expected a fresh APPLIED assembly but found an existing deterministic timeline",
                ProductErrorCategory.STATE,
                details={"case_id": case.case_id, "status": first.status},
            )

        return {
            "case_id": case.case_id,
            "source_rate": case.source_rate.to_rational(),
            "timeline_rate": timeline_rate.to_rational(),
            "source_duration_us": case.source_duration_us,
            "cut_range_us": {
                "start": case.cut_start_us,
                "end_exclusive": case.cut_end_us,
            },
            "keep_ranges": [item.to_dict() for item in edit_plan.keep_ranges],
            "expected_duration_frames": assembly_plan.expected_duration_frames,
            "source_artifact": {
                "file_name": source.name,
                **source_probe,
            },
            "first_execution": first.to_dict(),
            "replay_execution": replay.to_dict(),
            "timeline_count_before": before,
            "timeline_count_after_first": after_first,
            "timeline_count_after_replay": after_replay,
            "timeline": timeline_evidence,
            "status": "PASS",
        }

    def _ensure_probe_timeline(self, project: Any, timeline_name: str) -> Any:
        adapter = ResolveScriptingAssemblyAdapter(self.loader)
        existing = adapter._find_timeline(project, timeline_name)
        if existing is not None:
            return existing
        media_pool = getattr(project, "GetMediaPool", lambda: None)()
        create = getattr(media_pool, "CreateEmptyTimeline", None) if media_pool is not None else None
        if not callable(create):
            raise ProductError(
                "ERR_TASK010_NATIVE_NEGATIVE_GATE_API_UNAVAILABLE",
                "Resolve cannot create an isolated negative-gate timeline",
                ProductErrorCategory.NOT_SUPPORTED,
            )
        timeline = create(timeline_name)
        if timeline is None:
            raise ProductError(
                "ERR_TASK010_NATIVE_NEGATIVE_GATE_TIMELINE_FAILED",
                "Resolve failed to create the isolated negative-gate timeline",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            )
        return timeline

    def _negative_gate_plan(self, asset_suffix: str) -> tuple[Task010NativeCase, ResolveAssemblyPlan]:
        case = Task010NativeCase(
            f"NEGATIVE_{asset_suffix}",
            f"ASSET-000000000000000000000000{asset_suffix}",
            FrameRate(30),
        )
        adapter = ResolveScriptingAssemblyAdapter(self.loader)
        _, plan = build_task010_assembly_plan(
            case,
            timeline_rate=adapter.current_project_timeline_rate(),
        )
        return case, plan

    def _run_partial_gate(self, source: Path) -> dict[str, Any]:
        _, _, project = self._project()
        case, plan = self._negative_gate_plan("90")
        timeline = self._ensure_probe_timeline(project, plan.timeline_name)
        adapter = ResolveScriptingAssemblyAdapter(self.loader)
        marker = adapter._marker_hash(timeline)
        if marker is not None:
            raise ProductError(
                "ERR_TASK010_NATIVE_PARTIAL_GATE_PRECONDITION",
                "partial-state test timeline already contains a trusted marker",
                ProductErrorCategory.STATE,
            )
        try:
            ResolveAssemblyService.execute(
                plan,
                adapter=adapter,
                bindings=ResolveAssetBindings(source, source_frame_rate=case.source_rate),
                explicit_external_write_authorization=True,
            )
        except ProductError as exc:
            if exc.code != "ERR_RESOLVE_PARTIAL_AUTOMATION_TIMELINE":
                raise
            return {"status": "PASS", "observed_error_code": exc.code, "timeline_name": plan.timeline_name}
        raise ProductError(
            "ERR_TASK010_NATIVE_PARTIAL_GATE_DID_NOT_FAIL",
            "partial Automation Timeline was not rejected",
            ProductErrorCategory.DATA_INTEGRITY,
        )

    def _run_conflict_gate(self, source: Path) -> dict[str, Any]:
        _, manager, project = self._project()
        case, plan = self._negative_gate_plan("91")
        timeline = self._ensure_probe_timeline(project, plan.timeline_name)
        adapter = ResolveScriptingAssemblyAdapter(self.loader)
        wrong_hash = _SHA("f")
        observed = adapter._marker_hash(timeline)
        if observed is None:
            add_marker = getattr(timeline, "AddMarker", None)
            start_fn = getattr(timeline, "GetStartFrame", None)
            if not callable(add_marker):
                raise ProductError(
                    "ERR_TASK010_NATIVE_CONFLICT_GATE_MARKER_API_UNAVAILABLE",
                    "Resolve marker API is unavailable for the conflict gate",
                    ProductErrorCategory.NOT_SUPPORTED,
                )
            start = start_fn() if callable(start_fn) else 0
            if not isinstance(start, (int, float)):
                start = 0
            if add_marker(
                int(start),
                "Blue",
                "BAI AUTO ASSEMBLY",
                "TASK-010 native conflict gate",
                1,
                wrong_hash,
            ) is False:
                raise ProductError(
                    "ERR_TASK010_NATIVE_CONFLICT_GATE_MARKER_FAILED",
                    "Resolve could not persist the conflict marker",
                    ProductErrorCategory.EXTERNAL_DEPENDENCY,
                )
            save = getattr(manager, "SaveProject", None)
            if callable(save):
                save()
        elif observed != wrong_hash:
            raise ProductError(
                "ERR_TASK010_NATIVE_CONFLICT_GATE_PRECONDITION",
                "conflict test timeline already contains an unexpected marker",
                ProductErrorCategory.STATE,
            )

        try:
            ResolveAssemblyService.execute(
                plan,
                adapter=adapter,
                bindings=ResolveAssetBindings(source, source_frame_rate=case.source_rate),
                explicit_external_write_authorization=True,
            )
        except ProductError as exc:
            if exc.code != "ERR_RESOLVE_AUTOMATION_TIMELINE_HASH_CONFLICT":
                raise
            return {"status": "PASS", "observed_error_code": exc.code, "timeline_name": plan.timeline_name}
        raise ProductError(
            "ERR_TASK010_NATIVE_CONFLICT_GATE_DID_NOT_FAIL",
            "conflicting Automation Timeline marker was not rejected",
            ProductErrorCategory.DATA_INTEGRITY,
        )

    @staticmethod
    def _find_media_pool_item_by_path(media_pool: Any, source: Path) -> Any | None:
        target = source.resolve()
        get_root = getattr(media_pool, "GetRootFolder", None)
        if not callable(get_root):
            return None
        try:
            root = get_root()
        except Exception:
            return None
        if root is None:
            return None

        stack = [root]
        seen: set[int] = set()
        while stack:
            folder = stack.pop()
            identity = id(folder)
            if identity in seen:
                continue
            seen.add(identity)

            get_clips = getattr(folder, "GetClipList", None)
            try:
                clips = get_clips() if callable(get_clips) else []
            except Exception:
                clips = []
            if isinstance(clips, dict):
                clip_iter = clips.values()
            elif isinstance(clips, (list, tuple)):
                clip_iter = clips
            else:
                clip_iter = ()

            for clip in clip_iter:
                get_prop = getattr(clip, "GetClipProperty", None)
                if not callable(get_prop):
                    continue
                try:
                    value = get_prop("File Path")
                except Exception:
                    continue
                if not isinstance(value, str) or not value.strip():
                    continue
                try:
                    observed = Path(value).expanduser().resolve()
                except (OSError, RuntimeError, ValueError):
                    continue
                if observed == target:
                    return clip

            get_subfolders = getattr(folder, "GetSubFolderList", None)
            try:
                subfolders = get_subfolders() if callable(get_subfolders) else []
            except Exception:
                subfolders = []
            if isinstance(subfolders, (list, tuple)):
                stack.extend(subfolders)

        return None

    def _run_linked_av_semantic_probe(self, source: Path, source_rate: FrameRate) -> dict[str, Any]:
        """Probe Resolve's optional-mediaType semantics without changing product code.

        The existing TASK-010 adapter explicitly requests mediaType=1 (video only).
        This probe appends the same A/V source with mediaType omitted and inspects
        whether Resolve creates both video and audio Timeline Items. The result is
        Evidence for the subsequent source-audio preservation design decision.
        """
        _, manager, project = self._project()
        media_pool = getattr(project, "GetMediaPool", lambda: None)()
        import_media = getattr(media_pool, "ImportMedia", None) if media_pool is not None else None
        create = getattr(media_pool, "CreateEmptyTimeline", None) if media_pool is not None else None
        append = getattr(media_pool, "AppendToTimeline", None) if media_pool is not None else None
        if not all(callable(fn) for fn in (import_media, create, append)):
            raise ProductError(
                "ERR_TASK010_NATIVE_AV_PROBE_API_UNAVAILABLE",
                "Resolve lacks required Media Pool methods for A/V semantic probe",
                ProductErrorCategory.NOT_SUPPORTED,
            )

        imported = import_media([str(source.resolve())])
        media_item = (
            imported[0]
            if isinstance(imported, (list, tuple)) and len(imported) == 1
            else self._find_media_pool_item_by_path(media_pool, source)
        )
        if media_item is None:
            raise ProductError(
                "ERR_TASK010_NATIVE_AV_PROBE_IMPORT_FAILED",
                "A/V semantic probe could neither import nor reuse the generated source",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            )
        seed = sha256_bytes(canonical_json_bytes({"source_sha256": _sha256_file(source), "probe": "LINKED_AV"}))
        timeline_name = "BAI_NATIVE_AV_" + seed.split(":", 1)[1][:12].upper()

        adapter = ResolveScriptingAssemblyAdapter(self.loader)
        timeline = adapter._find_timeline(project, timeline_name)
        if timeline is None:
            timeline = create(timeline_name)
            if timeline is None:
                raise ProductError(
                    "ERR_TASK010_NATIVE_AV_PROBE_TIMELINE_FAILED",
                    "Resolve failed to create the A/V semantic probe Timeline",
                    ProductErrorCategory.EXTERNAL_DEPENDENCY,
                )
            end_exclusive = source_rate.us_to_frame(1_000_000)
            rows = [{
                "mediaPoolItem": media_item,
                "startFrame": 0,
                "endFrame": max(0, end_exclusive - 1),
                "recordFrame": 0,
                # Intentionally omit mediaType: this is the behavior under test.
            }]
            appended = append(rows)
            if not isinstance(appended, (list, tuple)) or not appended:
                raise ProductError(
                    "ERR_TASK010_NATIVE_AV_PROBE_APPEND_FAILED",
                    "Resolve did not return Timeline Items for linked A/V probe",
                    ProductErrorCategory.EXTERNAL_DEPENDENCY,
                )
            returned_tracks = [
                {"track_type": kind, "track_index": index}
                for kind, index in (_item_track_type(item) for item in appended)
            ]
            save = getattr(manager, "SaveProject", None)
            if callable(save):
                save()
        else:
            returned_tracks = []

        video_count = _track_item_count(timeline, "video", 1)
        audio_count = _track_item_count(timeline, "audio", 1)
        audio_observed = (
            (audio_count is not None and audio_count > 0)
            or any(row["track_type"] == "audio" for row in returned_tracks)
        )
        video_observed = (
            (video_count is not None and video_count > 0)
            or any(row["track_type"] == "video" for row in returned_tracks)
        )
        status = "PASS" if audio_observed and video_observed else "FINDING"
        return {
            "status": status,
            "timeline_name": timeline_name,
            "media_type_omitted": True,
            "video_track_1_item_count": video_count,
            "audio_track_1_item_count": audio_count,
            "returned_item_tracks": returned_tracks,
            "video_observed": video_observed,
            "audio_observed": audio_observed,
            "finding_code": None if status == "PASS" else "SOURCE_LINKED_AV_SEMANTICS_UNVERIFIED",
        }

    def run(self, *, output_path: str | Path) -> dict[str, Any]:
        resolve, _, _ = self._project()
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        source_dir = self.evidence_root / "generated-sources"
        source_dir.mkdir(parents=True, exist_ok=True)

        cases = [self._run_case(case, source_dir=source_dir) for case in task010_native_cases()]
        canonical_source = source_dir / "src30_project_rate.mp4"
        partial = self._run_partial_gate(canonical_source)
        conflict = self._run_conflict_gate(canonical_source)
        linked_av = self._run_linked_av_semantic_probe(canonical_source, FrameRate(30))

        version_fn = getattr(resolve, "GetVersionString", None)
        product_fn = getattr(resolve, "GetProductName", None)
        version = version_fn() if callable(version_fn) else None
        product = product_fn() if callable(product_fn) else None

        all_case_pass = all(item["status"] == "PASS" for item in cases)
        critical_gate_pass = partial["status"] == "PASS" and conflict["status"] == "PASS"
        overall = "PASS" if all_case_pass and critical_gate_pass else "FAIL"
        if overall == "PASS" and linked_av["status"] != "PASS":
            overall = "PASS_WITH_FINDING"

        report = {
            "report_version": "1.0.0",
            "task_owner": "TASK-010",
            "gate": "NATIVE_VALIDATION_PHASE2",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sandbox_project": self.sandbox_project,
            "resolve": {
                "version": version,
                "product_name": product,
            },
            "cases": cases,
            "negative_gates": {
                "partial_timeline": partial,
                "hash_conflict": conflict,
            },
            "linked_av_semantic_probe": linked_av,
            "host_absolute_paths_persisted": False,
            "status": overall,
        }
        output = Path(output_path)
        if not output.is_absolute():
            output = self.evidence_root / output
        output = output.expanduser().resolve()
        if self.evidence_root not in output.parents and output != self.evidence_root:
            raise ProductError(
                "ERR_TASK010_NATIVE_OUTPUT_OUTSIDE_EVIDENCE_ROOT",
                "native Evidence output must remain under evidence_root",
                ProductErrorCategory.SECURITY,
            )
        AtomicJsonWriter.write(output, report)
        return report
