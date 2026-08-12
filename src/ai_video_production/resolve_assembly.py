"""TASK-010 Resolve Assembly MVP with fail-closed ownership and idempotency gates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

from .edit_plan import EditPlan
from .errors import ProductError, ProductErrorCategory
from .resolve_loader import ResolveModuleLoader
from .resolve_subtitle_handoff import ResolveSubtitlePlacementPlan
from .serialization import canonical_json_bytes, sha256_bytes
from .timebase import FrameRate, FrameRounding
from .timeline_mapping import EditSegment, TimelineMappingPlan, TimelineMappingService


_AUTOMATION_PREFIX = "BAI_AUTO_"


@dataclass(frozen=True, slots=True)
class AudioPlacement:
    asset_id: str
    track_index: int
    timeline_start_frame: int
    duration_frames: int

    def __post_init__(self) -> None:
        if self.track_index < 1:
            raise ValueError("audio track_index must be >= 1")
        if self.timeline_start_frame < 0 or self.duration_frames <= 0:
            raise ValueError("audio placement must have a positive frame range")

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "track_index": self.track_index,
            "timeline_range_frames": {
                "start": self.timeline_start_frame,
                "end_exclusive": self.timeline_start_frame + self.duration_frames,
            },
        }


@dataclass(frozen=True, slots=True)
class ResolveAssemblyPlan:
    source_asset_id: str
    source_edit_plan_sha256: str
    timeline_name: str
    timeline_mapping: TimelineMappingPlan
    subtitle_plan_sha256: str | None
    subtitle_ready: bool
    audio_placements: tuple[AudioPlacement, ...]

    @property
    def expected_duration_frames(self) -> int:
        return self.timeline_mapping.duration_frames

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "assembly_plan_version": "1.0.0",
            "task_owner": "TASK-010",
            "source_asset_id": self.source_asset_id,
            "source_edit_plan_sha256": self.source_edit_plan_sha256,
            "timeline_name": self.timeline_name,
            "timeline_ownership": "AUTOMATION_OWNED",
            "timeline_mapping": self.timeline_mapping.to_dict(),
            "subtitle_plan_sha256": self.subtitle_plan_sha256,
            "subtitle_ready": self.subtitle_ready,
            "audio_placements": [item.to_dict() for item in self.audio_placements],
            "expected_duration_frames": self.expected_duration_frames,
            "idempotency_required": True,
            "external_write_requires_explicit_authorization": True,
        }
        body["assembly_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(frozen=True, slots=True)
class ResolveAssetBindings:
    source_media_path: Path
    source_frame_rate: FrameRate | None = None
    subtitle_srt_path: Path | None = None
    audio_paths: Mapping[str, Path] | None = None


@dataclass(frozen=True, slots=True)
class ResolveAssemblyResult:
    assembly_sha256: str
    timeline_name: str
    status: str
    reused_existing: bool
    subtitle_status: str
    audio_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": "1.0.0",
            "task_owner": "TASK-010",
            "assembly_sha256": self.assembly_sha256,
            "timeline_name": self.timeline_name,
            "status": self.status,
            "reused_existing": self.reused_existing,
            "subtitle_status": self.subtitle_status,
            "audio_status": self.audio_status,
        }


class ResolveAssemblyAdapter(Protocol):
    def applied_hash(self, timeline_name: str) -> str | None: ...

    def assemble(
        self,
        plan: ResolveAssemblyPlan,
        bindings: ResolveAssetBindings,
    ) -> ResolveAssemblyResult: ...


class ResolveAssemblyService:
    @staticmethod
    def compile(
        edit_plan: EditPlan,
        *,
        timeline_rate: FrameRate,
        timeline_origin_frame: int = 0,
        subtitle_plan: ResolveSubtitlePlacementPlan | None = None,
        audio_placements: tuple[AudioPlacement, ...] = (),
    ) -> ResolveAssemblyPlan:
        if not edit_plan.ready_for_assembly:
            raise ProductError(
                "ERR_RESOLVE_EDIT_PLAN_NOT_APPROVED",
                "Resolve assembly requires a fully reviewed and approved TASK-007 Edit Plan",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={"unresolved_count": len(edit_plan.unresolved_candidate_ids)},
            )
        edit_dict = edit_plan.to_dict()
        segments = tuple(
            EditSegment(
                placement_id=f"clip-{index:06d}",
                source_asset_id=edit_plan.source_asset_id,
                source_start_us=item.start_us,
                source_end_us=item.end_us,
            )
            for index, item in enumerate(edit_plan.keep_ranges, start=1)
        )
        mapping = TimelineMappingService.build(
            segments,
            timeline_rate=timeline_rate,
            timeline_origin_frame=timeline_origin_frame,
        )
        subtitle_hash: str | None = None
        subtitle_ready = False
        if subtitle_plan is not None:
            subtitle_dict = subtitle_plan.to_dict()
            subtitle_hash = subtitle_dict["plan_sha256"]
            subtitle_ready = subtitle_plan.ready_for_resolve_write
            if not subtitle_ready:
                raise ProductError(
                    "ERR_RESOLVE_SUBTITLE_REVIEW_REQUIRED",
                    "subtitle placement cannot be assembled before all cues are approved",
                    ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                )
            if subtitle_plan.timeline_rate != timeline_rate:
                raise ProductError(
                    "ERR_RESOLVE_SUBTITLE_RATE_MISMATCH",
                    "subtitle and edit timelines must use the same rational frame rate",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            if subtitle_plan.timeline_origin_frame != timeline_origin_frame:
                raise ProductError(
                    "ERR_RESOLVE_SUBTITLE_ORIGIN_MISMATCH",
                    "subtitle and edit timelines must share the same origin frame",
                    ProductErrorCategory.DATA_INTEGRITY,
                )

        preliminary = {
            "source_asset_id": edit_plan.source_asset_id,
            "source_edit_plan_sha256": edit_dict["plan_sha256"],
            "timeline_mapping_sha256": mapping.to_dict()["plan_sha256"],
            "subtitle_plan_sha256": subtitle_hash,
            "audio_placements": [item.to_dict() for item in audio_placements],
        }
        name_hash = sha256_bytes(canonical_json_bytes(preliminary)).split(":", 1)[1][:12]
        timeline_name = f"{_AUTOMATION_PREFIX}{name_hash.upper()}"
        return ResolveAssemblyPlan(
            source_asset_id=edit_plan.source_asset_id,
            source_edit_plan_sha256=edit_dict["plan_sha256"],
            timeline_name=timeline_name,
            timeline_mapping=mapping,
            subtitle_plan_sha256=subtitle_hash,
            subtitle_ready=subtitle_ready,
            audio_placements=audio_placements,
        )

    @staticmethod
    def execute(
        plan: ResolveAssemblyPlan,
        *,
        adapter: ResolveAssemblyAdapter,
        bindings: ResolveAssetBindings,
        explicit_external_write_authorization: bool,
    ) -> ResolveAssemblyResult:
        if not explicit_external_write_authorization:
            raise ProductError(
                "ERR_RESOLVE_WRITE_NOT_AUTHORIZED",
                "AUTO_ASSEMBLY requires explicit external-write authorization",
                ProductErrorCategory.AUTHORIZATION,
            )
        if not plan.timeline_name.startswith(_AUTOMATION_PREFIX):
            raise ProductError(
                "ERR_RESOLVE_TIMELINE_NOT_AUTOMATION_OWNED",
                "TASK-010 may mutate only an Automation-owned Timeline",
                ProductErrorCategory.AUTHORIZATION,
            )
        assembly_hash = plan.to_dict()["assembly_sha256"]
        observed = adapter.applied_hash(plan.timeline_name)
        if observed == assembly_hash:
            return ResolveAssemblyResult(
                assembly_hash,
                plan.timeline_name,
                "ALREADY_APPLIED",
                True,
                "UNCHANGED",
                "UNCHANGED",
            )
        if observed is not None and observed != assembly_hash:
            raise ProductError(
                "ERR_RESOLVE_AUTOMATION_TIMELINE_HASH_CONFLICT",
                "existing Automation-owned Timeline contains a different assembly marker",
                ProductErrorCategory.STATE,
                details={"timeline_name": plan.timeline_name},
            )
        return adapter.assemble(plan, bindings)


class ResolveScriptingAssemblyAdapter:
    """Bounded DaVinci Resolve scripting adapter.

    It creates a new deterministic BAI_AUTO_* Timeline and never clears/reuses a
    human Timeline. If a partial Timeline exists without a trusted marker, the
    adapter fails closed instead of appending duplicate media.
    """

    def __init__(self, loader: ResolveModuleLoader | None = None) -> None:
        self.loader = loader or ResolveModuleLoader()

    def _project(self) -> tuple[Any, Any]:
        resolve, _ = self.loader.connect()
        manager = getattr(resolve, "GetProjectManager", lambda: None)()
        project = getattr(manager, "GetCurrentProject", lambda: None)() if manager is not None else None
        if manager is None or project is None:
            raise ProductError(
                "ERR_RESOLVE_CURRENT_PROJECT_REQUIRED",
                "open the intended DaVinci Resolve Project before AUTO_ASSEMBLY",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                retryable=True,
            )
        return manager, project

    @staticmethod
    def _find_timeline(project: Any, timeline_name: str) -> Any | None:
        count_fn = getattr(project, "GetTimelineCount", None)
        get_fn = getattr(project, "GetTimelineByIndex", None)
        if not callable(count_fn) or not callable(get_fn):
            return None
        try:
            count = int(count_fn())
        except Exception:
            return None
        for index in range(1, count + 1):
            timeline = get_fn(index)
            if timeline is None:
                continue
            name_fn = getattr(timeline, "GetName", None)
            try:
                name = name_fn() if callable(name_fn) else None
            except Exception:
                name = None
            if name == timeline_name:
                return timeline
        return None

    @staticmethod
    def _marker_hash(timeline: Any) -> str | None:
        get_markers = getattr(timeline, "GetMarkers", None)
        if not callable(get_markers):
            return None
        try:
            markers = get_markers()
        except Exception:
            return None
        if not isinstance(markers, dict):
            return None
        for value in markers.values():
            if not isinstance(value, dict):
                continue
            if value.get("name") == "BAI AUTO ASSEMBLY":
                custom = value.get("customData")
                if isinstance(custom, str) and custom.startswith("sha256:"):
                    return custom
        return None

    def applied_hash(self, timeline_name: str) -> str | None:
        _, project = self._project()
        timeline = self._find_timeline(project, timeline_name)
        if timeline is None:
            return None
        marker = self._marker_hash(timeline)
        if marker is None:
            raise ProductError(
                "ERR_RESOLVE_PARTIAL_AUTOMATION_TIMELINE",
                "deterministic Automation Timeline exists without a verifiable assembly marker",
                ProductErrorCategory.STATE,
                details={"timeline_name": timeline_name},
            )
        return marker

    @staticmethod
    def _regular_path(path: Path, *, label: str) -> Path:
        target = Path(path)
        if target.is_symlink() or not target.is_file():
            raise ProductError(
                "ERR_RESOLVE_BINDING_INVALID",
                f"{label} must be a regular non-symlink file",
                ProductErrorCategory.VALIDATION,
            )
        return target.resolve()

    def assemble(self, plan: ResolveAssemblyPlan, bindings: ResolveAssetBindings) -> ResolveAssemblyResult:
        manager, project = self._project()
        media_pool = getattr(project, "GetMediaPool", lambda: None)()
        if media_pool is None:
            raise ProductError(
                "ERR_RESOLVE_MEDIA_POOL_UNAVAILABLE",
                "current Resolve Project does not expose a Media Pool",
                ProductErrorCategory.NOT_SUPPORTED,
            )
        if self._find_timeline(project, plan.timeline_name) is not None:
            raise ProductError(
                "ERR_RESOLVE_PARTIAL_AUTOMATION_TIMELINE",
                "Automation Timeline already exists without a completed idempotency marker",
                ProductErrorCategory.STATE,
                details={"timeline_name": plan.timeline_name},
            )

        source_path = self._regular_path(bindings.source_media_path, label="source media")
        source_frame_rate = bindings.source_frame_rate
        if source_frame_rate is None:
            raise ProductError(
                "ERR_RESOLVE_SOURCE_FRAME_RATE_REQUIRED",
                "AUTO_ASSEMBLY requires the probed source/normalized media frame rate; timeline rate cannot be substituted",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        import_media = getattr(media_pool, "ImportMedia", None)
        create_timeline = getattr(media_pool, "CreateEmptyTimeline", None)
        append = getattr(media_pool, "AppendToTimeline", None)
        if not all(callable(item) for item in (import_media, create_timeline, append)):
            raise ProductError(
                "ERR_RESOLVE_ASSEMBLY_API_UNAVAILABLE",
                "Resolve scripting API lacks required media/timeline assembly methods",
                ProductErrorCategory.NOT_SUPPORTED,
            )
        imported = import_media([str(source_path)])
        if not isinstance(imported, (list, tuple)) or len(imported) != 1:
            raise ProductError(
                "ERR_RESOLVE_SOURCE_IMPORT_FAILED",
                "source media import did not produce exactly one Media Pool item",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            )
        media_item = imported[0]
        timeline = create_timeline(plan.timeline_name)
        if timeline is None:
            raise ProductError(
                "ERR_RESOLVE_TIMELINE_CREATE_FAILED",
                "Resolve failed to create the Automation-owned Timeline",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            )
        set_current = getattr(project, "SetCurrentTimeline", None)
        if callable(set_current) and set_current(timeline) is False:
            raise ProductError(
                "ERR_RESOLVE_TIMELINE_SELECT_FAILED",
                "Resolve failed to select the new Automation-owned Timeline",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            )

        append_items: list[dict[str, Any]] = []
        for placement in plan.timeline_mapping.placements:
            source_start = source_frame_rate.us_to_frame(placement.mapped_start_us, rounding=FrameRounding.FLOOR)
            source_end_exclusive = source_frame_rate.us_to_frame(placement.mapped_end_us, rounding=FrameRounding.CEIL)
            if source_end_exclusive <= source_start:
                source_end_exclusive = source_start + 1
            append_items.append(
                {
                    "mediaPoolItem": media_item,
                    "startFrame": source_start,
                    # Resolve AppendToTimeline uses an inclusive source end frame.
                    "endFrame": source_end_exclusive - 1,
                    "recordFrame": placement.timeline_start_frame,
                    "mediaType": 1,
                }
            )
        appended = append(append_items)
        if append_items and (not isinstance(appended, (list, tuple)) or len(appended) != len(append_items)):
            raise ProductError(
                "ERR_RESOLVE_VIDEO_ASSEMBLY_FAILED",
                "Resolve did not confirm every planned video placement",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            )

        subtitle_status = "NOT_REQUESTED"
        if plan.subtitle_plan_sha256 is not None:
            if bindings.subtitle_srt_path is None:
                raise ProductError(
                    "ERR_RESOLVE_SUBTITLE_BINDING_REQUIRED",
                    "subtitle plan is present but no reviewed SRT binding was supplied",
                    ProductErrorCategory.VALIDATION,
                )
            subtitle_path = self._regular_path(bindings.subtitle_srt_path, label="subtitle SRT")
            import_timeline = getattr(timeline, "ImportIntoTimeline", None)
            if not callable(import_timeline):
                raise ProductError(
                    "ERR_RESOLVE_SUBTITLE_API_UNAVAILABLE",
                    "this Resolve version does not expose Timeline.ImportIntoTimeline for SRT placement",
                    ProductErrorCategory.NOT_SUPPORTED,
                )
            result = import_timeline(str(subtitle_path))
            if result is False or result is None:
                raise ProductError(
                    "ERR_RESOLVE_SUBTITLE_IMPORT_FAILED",
                    "Resolve did not confirm SRT import into the Automation Timeline",
                    ProductErrorCategory.EXTERNAL_DEPENDENCY,
                )
            subtitle_status = "IMPORTED"

        audio_status = "NOT_REQUESTED"
        if plan.audio_placements:
            audio_paths = dict(bindings.audio_paths or {})
            audio_items: dict[str, Any] = {}
            for placement in plan.audio_placements:
                path = audio_paths.get(placement.asset_id)
                if path is None:
                    raise ProductError(
                        "ERR_RESOLVE_AUDIO_BINDING_REQUIRED",
                        "audio placement is present but its Asset path binding is missing",
                        ProductErrorCategory.VALIDATION,
                        details={"asset_id": placement.asset_id},
                    )
                safe_path = self._regular_path(path, label="audio asset")
                values = import_media([str(safe_path)])
                if not isinstance(values, (list, tuple)) or len(values) != 1:
                    raise ProductError(
                        "ERR_RESOLVE_AUDIO_IMPORT_FAILED",
                        "audio Asset import did not produce exactly one Media Pool item",
                        ProductErrorCategory.EXTERNAL_DEPENDENCY,
                        details={"asset_id": placement.asset_id},
                    )
                audio_items[placement.asset_id] = values[0]
            rows = [
                {
                    "mediaPoolItem": audio_items[item.asset_id],
                    "startFrame": 0,
                    "endFrame": item.duration_frames - 1,
                    "recordFrame": item.timeline_start_frame,
                    "mediaType": 2,
                    "trackIndex": item.track_index,
                }
                for item in plan.audio_placements
            ]
            placed = append(rows)
            if not isinstance(placed, (list, tuple)) or len(placed) != len(rows):
                raise ProductError(
                    "ERR_RESOLVE_AUDIO_ASSEMBLY_FAILED",
                    "Resolve did not confirm every planned audio placement",
                    ProductErrorCategory.EXTERNAL_DEPENDENCY,
                )
            audio_status = "PLACED"

        assembly_hash = plan.to_dict()["assembly_sha256"]
        add_marker = getattr(timeline, "AddMarker", None)
        start_fn = getattr(timeline, "GetStartFrame", None)
        if not callable(add_marker):
            raise ProductError(
                "ERR_RESOLVE_IDEMPOTENCY_MARKER_UNAVAILABLE",
                "Resolve Timeline markers are required for TASK-010 idempotency",
                ProductErrorCategory.NOT_SUPPORTED,
            )
        start_frame = 0
        if callable(start_fn):
            observed = start_fn()
            if isinstance(observed, (int, float)):
                start_frame = int(observed)
        marker_result = add_marker(
            start_frame,
            "Blue",
            "BAI AUTO ASSEMBLY",
            "TASK-010 deterministic assembly marker",
            1,
            assembly_hash,
        )
        if marker_result is False:
            raise ProductError(
                "ERR_RESOLVE_IDEMPOTENCY_MARKER_FAILED",
                "Resolve failed to persist the assembly idempotency marker",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            )
        save = getattr(manager, "SaveProject", None)
        if callable(save) and save() is False:
            raise ProductError(
                "ERR_RESOLVE_PROJECT_SAVE_FAILED",
                "Resolve failed to save the Project after AUTO_ASSEMBLY",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            )
        return ResolveAssemblyResult(
            assembly_hash,
            plan.timeline_name,
            "APPLIED",
            False,
            subtitle_status,
            audio_status,
        )
