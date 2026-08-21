"""Python-owned TASK-044 NLE view/controller for the existing TASK-036 Shell."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Mapping

from .durable_product_job import DurableProductJob, DurableProductJobState, DurableProductJobStore, durable_job_shell_projection
from .errors import ProductError, ProductErrorCategory
from .export_queue import ExportDispatchResult, ExportPreparation
from .export_queue_application import DispatchCallback, ExportQueueApplication
from .interactive_timeline import (
    InteractiveTimeline, TimelineFitMode, TimelineInteractionReducer,
    TimelineInteractionState, TimelineMediaKind, TimelineTrack,
    TimelineTrackCategory, TimelineTrackRole, TimelineViewport,
    TimelineWindowProjector, timeline_track_category,
)
from .interactive_timeline_application import Task044TimelineEditApplication
from .interactive_timeline_edit import SnapAnchor, SnapKind
from .product_project_store import ProductProjectManifestStore


ExportPreparationProvider = Callable[[str], ExportPreparation]
ExportDestinationProvider = Callable[[str, ExportPreparation], str | Path]
_MAX_PENDING_DISPATCH_PREPARATIONS = 256


def _frame(value: object, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", f"{name} is invalid", ProductErrorCategory.VALIDATION)
    return value


class Task044NleShellController:
    """Keeps reversible interaction in Python and delegates durable truth to applications."""

    def __init__(self, *, timeline: InteractiveTimeline,
                 edit_application: Task044TimelineEditApplication | None = None,
                 export_application: ExportQueueApplication | None = None,
                 export_preparations: Mapping[str, ExportPreparation] | None = None,
                 export_preparation_provider: ExportPreparationProvider | None = None,
                 export_destination_provider: ExportDestinationProvider | None = None,
                 export_dispatcher: DispatchCallback | None = None) -> None:
        self.timeline = timeline
        self.edit_application = edit_application
        self.export_application = export_application
        self.export_preparations = dict(export_preparations or {})
        self.export_preparation_provider = export_preparation_provider
        self.export_destination_provider = export_destination_provider
        self.export_dispatcher = export_dispatcher
        self._pending_dispatch_preparations: dict[str, tuple[str, ExportPreparation]] = {}
        self._pending_dispatch_lock = Lock()
        self._track_presentation: dict[str, dict[str, object]] = {}
        self.interaction = TimelineInteractionState(timeline.project_id, timeline.timeline_sha256, 0)
        self.viewport = TimelineViewport.fit(
            start_frame=0, end_frame=timeline.duration_frames, viewport_width_px=1200,
            rate=timeline.timeline_rate, mode=TimelineFitMode.ENTIRE,
            visible_track_count=min(8, max(1, len(timeline.tracks))),
        )

    def _effective_timeline(self) -> InteractiveTimeline:
        if self.edit_application is None:
            return self.timeline
        manifest = ProductProjectManifestStore.load(self.edit_application.project_root)
        history = self.edit_application._load(manifest)
        from .interactive_timeline_edit import TimelineEditProjector
        return TimelineEditProjector.apply(self.timeline, history)[0]

    def snapshot(self, args: Any = None) -> dict[str, Any]:
        args = {} if args is None else args
        if not isinstance(args, dict) or set(args) - {"clip_offset", "max_clips"}:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Timeline snapshot request is invalid", ProductErrorCategory.VALIDATION)
        offset = _frame(args.get("clip_offset", 0), "clip_offset")
        maximum = _frame(args.get("max_clips", 500), "max_clips", minimum=1)
        if maximum > 500:
            raise ProductError(
                "ERR_NLE_SHELL_REQUEST_INVALID", "Timeline DOM page exceeds 500 clips",
                ProductErrorCategory.VALIDATION,
            )
        timeline = self._effective_timeline()
        manifest_sha256 = None
        if self.edit_application is not None:
            manifest_sha256 = ProductProjectManifestStore.load(
                self.edit_application.project_root
            ).project_manifest_sha256
        projection = TimelineWindowProjector.project(timeline, self.viewport,
                                                     clip_offset=offset, max_clips=maximum)
        projection_payload = projection.to_dict(rate=timeline.timeline_rate)
        for track_payload in projection_payload["tracks"]:
            track = next(item for item in timeline.tracks if item.track_id == track_payload["track_id"])
            state = self._track_presentation.setdefault(track.track_id, {
                "visible": True, "locked": False, "muted": False,
                "solo": False, "height": 44,
            })
            track_payload.update({
                "category": timeline_track_category(track).value,
                "visible": state["visible"],
                "locked": state["locked"],
                "muted": state["muted"],
                "solo": state["solo"],
                "height": state["height"],
                "mute_solo_applicable": track.media_kind is TimelineMediaKind.AUDIO,
                "remove_available": (
                    self.edit_application is not None
                    and not bool(state["locked"])
                    and not any(item.track_id == track.track_id for item in timeline.clips)
                    and sum(timeline_track_category(item) is timeline_track_category(track)
                            for item in timeline.tracks) > 1
                    and not track.minimum_required
                ),
            })
        return {"available": True, "task_owner": "TASK-044/P-NLE-4",
                "timeline_id": timeline.timeline_id,
                "timeline_sha256": self.timeline.timeline_sha256,
                "projected_timeline_sha256": timeline.timeline_sha256,
                "project_manifest_sha256": manifest_sha256,
                "duration_frames": timeline.duration_frames,
                "total_track_count": len(timeline.tracks),
                "timeline_rate": {"numerator": timeline.timeline_rate.numerator,
                                  "denominator": timeline.timeline_rate.denominator},
                "interaction": self.interaction.to_dict(),
                "projection": projection_payload,
                "track_categories": [item.value for item in (
                    TimelineTrackCategory.VIDEO, TimelineTrackCategory.SUBTITLE,
                    TimelineTrackCategory.AUDIO, TimelineTrackCategory.SE,
                    TimelineTrackCategory.BGM,
                )],
                "track_mutation_available": self.edit_application is not None,
                "durable_state_in_javascript": False,
                "external_mutation_started": False}

    def update_track_state(self, args: Any) -> dict[str, Any]:
        required = {"track_id", "state", "value", "expected_timeline_sha256"}
        if not isinstance(args, dict) or set(args) != required:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Track state request is invalid", ProductErrorCategory.VALIDATION)
        if args["expected_timeline_sha256"] != self.timeline.timeline_sha256:
            raise ProductError("ERR_NLE_SHELL_TIMELINE_STALE", "Timeline changed; reload first", ProductErrorCategory.STATE)
        track = next((item for item in self._effective_timeline().tracks if item.track_id == args["track_id"]), None)
        if track is None:
            raise ProductError("ERR_NLE_SHELL_TRACK_MISSING", "Timeline track is missing", ProductErrorCategory.STATE)
        state_name = str(args["state"]).upper()
        if state_name not in {"VISIBLE", "LOCKED", "MUTED", "SOLO", "HEIGHT"}:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Track state is not allowlisted", ProductErrorCategory.VALIDATION)
        if state_name in {"MUTED", "SOLO"} and track.media_kind is not TimelineMediaKind.AUDIO:
            raise ProductError("ERR_NLE_SHELL_TRACK_STATE_NOT_APPLICABLE", "Mute/Solo is available only for audio tracks", ProductErrorCategory.VALIDATION)
        if state_name == "HEIGHT":
            height = _frame(args["value"], "value", minimum=30)
            if height > 92:
                raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Track height is outside 30..92", ProductErrorCategory.VALIDATION)
            value: object = height
        else:
            if not isinstance(args["value"], bool):
                raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Track state value must be boolean", ProductErrorCategory.VALIDATION)
            value = args["value"]
        state = self._track_presentation.setdefault(track.track_id, {
            "visible": True, "locked": False, "muted": False,
            "solo": False, "height": 44,
        })
        state[state_name.lower()] = value
        return self.snapshot()

    def update_track_height(self, args: Any) -> dict[str, Any]:
        required = {"height", "expected_timeline_sha256"}
        if not isinstance(args, dict) or set(args) != required:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Track height request is invalid", ProductErrorCategory.VALIDATION)
        if args["expected_timeline_sha256"] != self.timeline.timeline_sha256:
            raise ProductError("ERR_NLE_SHELL_TIMELINE_STALE", "Timeline changed; reload first", ProductErrorCategory.STATE)
        height = _frame(args["height"], "height", minimum=30)
        if height > 92:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Track height is outside 30..92", ProductErrorCategory.VALIDATION)
        for track in self._effective_timeline().tracks:
            state = self._track_presentation.setdefault(track.track_id, {
                "visible": True, "locked": False, "muted": False,
                "solo": False, "height": 44,
            })
            state["height"] = height
        return self.snapshot()

    def prepare_add_track(self, args: Any) -> dict[str, object]:
        required = {"category", "command_id", "expected_project_manifest_sha256", "expected_timeline_sha256"}
        if self.edit_application is None:
            raise ProductError("ERR_NLE_SHELL_EDIT_NOT_BOUND", "Timeline edit application is unavailable", ProductErrorCategory.STATE)
        if not isinstance(args, dict) or set(args) != required:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Add-track request is invalid", ProductErrorCategory.VALIDATION)
        if args["expected_timeline_sha256"] != self.timeline.timeline_sha256:
            raise ProductError("ERR_NLE_SHELL_TIMELINE_STALE", "Timeline changed; reload first", ProductErrorCategory.STATE)
        try:
            category = TimelineTrackCategory(str(args["category"]))
        except ValueError as exc:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Track category is invalid", ProductErrorCategory.VALIDATION) from exc
        definitions = {
            TimelineTrackCategory.VIDEO: ("V", 0, TimelineTrackRole.VIDEO, TimelineMediaKind.VIDEO, "Video"),
            TimelineTrackCategory.SUBTITLE: ("S", 100, TimelineTrackRole.SUBTITLE, TimelineMediaKind.TEXT, "Subtitle"),
            TimelineTrackCategory.AUDIO: ("A", 300, TimelineTrackRole.AUDIO, TimelineMediaKind.AUDIO, "Audio"),
            TimelineTrackCategory.SE: ("SE", 400, TimelineTrackRole.AUDIO, TimelineMediaKind.AUDIO, "SE"),
            TimelineTrackCategory.BGM: ("BGM", 500, TimelineTrackRole.AUDIO, TimelineMediaKind.AUDIO, "BGM"),
        }
        if category not in definitions:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Track category is not addable", ProductErrorCategory.VALIDATION)
        prefix, order_base, role, media, label = definitions[category]
        timeline = self._effective_timeline()
        sequence = 1
        existing = {item.track_id for item in timeline.tracks}
        while f"{prefix}{sequence}" in existing:
            sequence += 1
        track = TimelineTrack(f"{prefix}{sequence}", order_base + sequence, role, media, f"{label} {sequence}")
        return self.edit_application.prepare_add_track(
            timeline=self.timeline, track=track, command_id=str(args["command_id"]),
            expected_project_manifest_sha256=str(args["expected_project_manifest_sha256"]),
        )

    def prepare_remove_track(self, args: Any) -> dict[str, object]:
        required = {"track_id", "command_id", "expected_project_manifest_sha256", "expected_timeline_sha256"}
        if self.edit_application is None:
            raise ProductError("ERR_NLE_SHELL_EDIT_NOT_BOUND", "Timeline edit application is unavailable", ProductErrorCategory.STATE)
        if not isinstance(args, dict) or set(args) != required:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Remove-track request is invalid", ProductErrorCategory.VALIDATION)
        if args["expected_timeline_sha256"] != self.timeline.timeline_sha256:
            raise ProductError("ERR_NLE_SHELL_TIMELINE_STALE", "Timeline changed; reload first", ProductErrorCategory.STATE)
        state = self._track_presentation.get(str(args["track_id"]), {})
        if state.get("locked") is True:
            raise ProductError("ERR_TIMELINE_TRACK_LOCKED", "Locked track cannot be removed", ProductErrorCategory.STATE)
        return self.edit_application.prepare_remove_track(
            timeline=self.timeline, track_id=str(args["track_id"]),
            command_id=str(args["command_id"]),
            expected_project_manifest_sha256=str(args["expected_project_manifest_sha256"]),
        )

    def select(self, args: Any) -> dict[str, Any]:
        required = {"clip_id", "extend", "expected_timeline_sha256"}
        if not isinstance(args, dict) or set(args) != required or not isinstance(args["extend"], bool):
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Timeline selection request is invalid", ProductErrorCategory.VALIDATION)
        if args["expected_timeline_sha256"] != self.timeline.timeline_sha256:
            raise ProductError("ERR_NLE_SHELL_TIMELINE_STALE", "Timeline changed; reload first", ProductErrorCategory.STATE)
        timeline = self._effective_timeline()
        clip = next((item for item in timeline.clips if item.clip_id == args["clip_id"]), None)
        if clip is None:
            raise ProductError("ERR_NLE_SHELL_CLIP_MISSING", "Timeline clip is missing", ProductErrorCategory.STATE)
        self.interaction = TimelineInteractionReducer.select_clip(self.interaction, clip, extend=args["extend"])
        return self.snapshot()

    def seek(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"frame", "expected_timeline_sha256"}:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Timeline seek request is invalid", ProductErrorCategory.VALIDATION)
        if args["expected_timeline_sha256"] != self.timeline.timeline_sha256:
            raise ProductError("ERR_NLE_SHELL_TIMELINE_STALE", "Timeline changed; reload first", ProductErrorCategory.STATE)
        self.interaction = TimelineInteractionReducer.seek(
            self.interaction, frame=_frame(args["frame"], "frame"),
            timeline_duration_frames=self.timeline.duration_frames,
        )
        return self.snapshot()

    def set_in_out(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"in_frame", "out_frame"}:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "IN/OUT request is invalid", ProductErrorCategory.VALIDATION)
        self.interaction = TimelineInteractionReducer.set_in_out(
            self.interaction, in_frame=_frame(args["in_frame"], "in_frame"),
            out_frame=_frame(args["out_frame"], "out_frame", minimum=1),
        )
        return self.snapshot()

    def update_viewport(self, args: Any) -> dict[str, Any]:
        required = {"start_frame", "end_frame", "scale_numerator", "scale_denominator",
                    "first_track_index", "visible_track_count"}
        if not isinstance(args, dict) or set(args) != required:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Viewport request is invalid", ProductErrorCategory.VALIDATION)
        timeline = self._effective_timeline()
        start = _frame(args["start_frame"], "start_frame")
        end = _frame(args["end_frame"], "end_frame", minimum=1)
        first_track = _frame(args["first_track_index"], "first_track_index")
        visible_tracks = _frame(args["visible_track_count"], "visible_track_count", minimum=1)
        if end <= start or end > timeline.duration_frames or first_track >= len(timeline.tracks) or visible_tracks > 64:
            raise ProductError(
                "ERR_NLE_SHELL_REQUEST_INVALID", "Viewport is outside the bounded Timeline",
                ProductErrorCategory.VALIDATION,
            )
        scale = Fraction(
            _frame(args["scale_numerator"], "scale_numerator", minimum=1),
            _frame(args["scale_denominator"], "scale_denominator", minimum=1),
        )
        self.viewport = TimelineViewport(
            start, end,
            scale.numerator, scale.denominator,
            first_track, visible_tracks,
        )
        return self.snapshot()

    def fit(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"mode", "viewport_width_px"}:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Fit request is invalid", ProductErrorCategory.VALIDATION)
        try:
            mode = TimelineFitMode(args["mode"])
        except (TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_NLE_SHELL_REQUEST_INVALID", "Fit mode is invalid",
                ProductErrorCategory.VALIDATION,
            ) from exc
        if mode not in {TimelineFitMode.ENTIRE, TimelineFitMode.SELECTION}:
            raise ProductError(
                "ERR_NLE_SHELL_REQUEST_INVALID", "Fit mode is not allowlisted",
                ProductErrorCategory.VALIDATION,
            )
        start, end = 0, self.timeline.duration_frames
        if mode is TimelineFitMode.SELECTION:
            selected = [item for item in self._effective_timeline().clips
                        if item.clip_id in self.interaction.selected_clip_ids]
            if not selected:
                raise ProductError("ERR_NLE_SHELL_SELECTION_EMPTY", "Fit Selection requires selected clips", ProductErrorCategory.STATE)
            start, end = min(item.start_frame for item in selected), max(item.end_frame for item in selected)
        self.viewport = TimelineViewport.fit(
            start_frame=start, end_frame=end,
            viewport_width_px=_frame(args["viewport_width_px"], "viewport_width_px", minimum=1),
            rate=self.timeline.timeline_rate, mode=mode,
            first_track_index=self.viewport.first_track_index,
            visible_track_count=self.viewport.visible_track_count,
        )
        return self.snapshot()

    def prepare_trim(self, args: Any) -> dict[str, Any]:
        required = {"clip_id", "edge", "desired_frame", "command_id",
                    "expected_project_manifest_sha256", "expected_timeline_sha256"}
        if self.edit_application is None:
            raise ProductError("ERR_NLE_SHELL_EDIT_NOT_BOUND", "Timeline edit application is unavailable", ProductErrorCategory.STATE)
        if not isinstance(args, dict) or set(args) != required:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Trim request is invalid", ProductErrorCategory.VALIDATION)
        if args["expected_timeline_sha256"] != self.timeline.timeline_sha256:
            raise ProductError("ERR_NLE_SHELL_TIMELINE_STALE", "Timeline changed; reload first", ProductErrorCategory.STATE)
        projected = self._effective_timeline()
        clip = next((item for item in projected.clips if item.clip_id == str(args["clip_id"])), None)
        if clip is not None and self._track_presentation.get(clip.track_id, {}).get("locked") is True:
            raise ProductError("ERR_TIMELINE_TRACK_LOCKED", "Locked track cannot be edited", ProductErrorCategory.STATE)
        anchors = (SnapAnchor("playhead", self.interaction.playhead_frame, SnapKind.PLAYHEAD, 0),)
        return self.edit_application.prepare_trim(
            timeline=self.timeline, clip_id=str(args["clip_id"]), edge=str(args["edge"]),
            desired_frame=_frame(args["desired_frame"], "desired_frame"),
            snap_tolerance_frames=2, snap_anchors=anchors, command_id=str(args["command_id"]),
            expected_project_manifest_sha256=str(args["expected_project_manifest_sha256"]),
        )

    def apply_edit(self, args: Any) -> dict[str, Any]:
        if self.edit_application is None:
            raise ProductError(
                "ERR_NLE_SHELL_EDIT_NOT_BOUND", "Timeline edit application is unavailable",
                ProductErrorCategory.STATE,
            )
        if not isinstance(args, dict) or set(args) != {"confirmation_id"}:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Timeline apply request is invalid", ProductErrorCategory.VALIDATION)
        return self.edit_application.apply(confirmation_id=str(args["confirmation_id"]), timeline=self.timeline)

    def _export_preparation(self, job_id: str) -> ExportPreparation:
        preparation = self.export_preparations.get(job_id)
        if preparation is None and self.export_preparation_provider is not None:
            preparation = self.export_preparation_provider(job_id)
        if preparation is None:
            raise ProductError(
                "ERR_NLE_SHELL_EXPORT_REPREPARE_REQUIRED",
                "The exact private Export preparation is not bound; re-prepare this item",
                ProductErrorCategory.STATE,
            )
        if not isinstance(preparation, ExportPreparation):
            raise ProductError(
                "ERR_NLE_SHELL_EXPORT_PREPARATION_INVALID",
                "Private Export preparation provider returned invalid data",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return preparation

    def export_preflight(self, args: Any) -> dict[str, Any]:
        if self.export_application is None:
            raise ProductError("ERR_NLE_SHELL_EXPORT_NOT_BOUND", "Export Queue is unavailable", ProductErrorCategory.STATE)
        if not isinstance(args, dict) or set(args) != {"job_id"}:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Export preflight request is invalid", ProductErrorCategory.VALIDATION)
        job_id = str(args["job_id"])
        job = self.export_application.preflight(
            job_id=job_id, preparation=self._export_preparation(job_id),
        )
        return {
            "job_id": job.job_id,
            "state": job.state.value,
            "state_version": job.state_version,
            "external_mutation_started": False,
        }

    def export_prepare_dispatch(self, args: Any) -> dict[str, object]:
        if self.export_application is None:
            raise ProductError("ERR_NLE_SHELL_EXPORT_NOT_BOUND", "Export Queue is unavailable", ProductErrorCategory.STATE)
        if not isinstance(args, dict) or set(args) != {"job_id"}:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Export preparation request is invalid", ProductErrorCategory.VALIDATION)
        job_id = str(args["job_id"])
        preparation = self._export_preparation(job_id)
        confirmation = self.export_application.prepare_dispatch(
            job_id=job_id, preparation=preparation,
        )
        token = str(confirmation["confirmation_id"])
        with self._pending_dispatch_lock:
            if len(self._pending_dispatch_preparations) >= _MAX_PENDING_DISPATCH_PREPARATIONS:
                self.export_application.cancel_dispatch(confirmation_id=token)
                raise ProductError(
                    "ERR_NLE_SHELL_EXPORT_CONFIRMATION_CAPACITY",
                    "Export dispatch confirmation capacity is exhausted",
                    ProductErrorCategory.STATE,
                )
            self._pending_dispatch_preparations[token] = (job_id, preparation)
        return confirmation

    def export_apply_dispatch(self, args: Any) -> dict[str, Any]:
        if self.export_application is None:
            raise ProductError("ERR_NLE_SHELL_EXPORT_NOT_BOUND", "Export Queue is unavailable", ProductErrorCategory.STATE)
        if not isinstance(args, dict) or set(args) != {"confirmation_id"} or not isinstance(args["confirmation_id"], str):
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Export dispatch request is invalid", ProductErrorCategory.VALIDATION)
        if self.export_destination_provider is None or self.export_dispatcher is None:
            raise ProductError(
                "ERR_NLE_SHELL_EXPORT_DISPATCH_NOT_BOUND",
                "Private Export destination or dispatcher is unavailable",
                ProductErrorCategory.STATE,
            )
        token = args["confirmation_id"]
        with self._pending_dispatch_lock:
            pending = self._pending_dispatch_preparations.pop(token, None)
        if pending is None:
            raise ProductError(
                "ERR_EXPORT_CONFIRMATION_INVALID",
                "Export confirmation is missing or consumed",
                ProductErrorCategory.AUTHORIZATION,
            )
        job_id, confirmed_preparation = pending
        try:
            preparation = self._export_preparation(job_id)
            if preparation != confirmed_preparation:
                raise ProductError(
                    "ERR_NLE_SHELL_EXPORT_CONFIRMATION_STALE",
                    "Final Review approval or private Export preparation changed after confirmation",
                    ProductErrorCategory.AUTHORIZATION,
                )
            private_destination = self.export_destination_provider(job_id, preparation)
        except BaseException:
            # The controller token is already consumed. Keep the application
            # confirmation in sync even when the private launcher binding fails.
            self.export_application.cancel_dispatch(confirmation_id=token)
            raise
        captured: list[ExportDispatchResult] = []

        def dispatch(
            job: DurableProductJob, exact: ExportPreparation, destination: Path,
        ) -> ExportDispatchResult:
            result = self.export_dispatcher(job, exact, destination)
            captured.append(result)
            return result

        job = self.export_application.apply_dispatch(
            confirmation_id=token,
            preparation=preparation,
            private_destination=private_destination,
            dispatcher=dispatch,
        )
        result = captured[0] if captured else None
        return {
            "job_id": job.job_id,
            "operation_identity": job.operation_identity,
            "state": job.state.value,
            "state_version": job.state_version,
            "result_ref": job.result_ref,
            "result_identity": None if result is None else result.result_identity,
            "render_qa_sha256": None if result is None else result.render_qa_sha256,
            "render_qa_passed": None if result is None else result.render_qa_passed,
            "external_mutation_started": True,
            "host_output_path_persisted": False,
        }

    def export_cancel_dispatch(self, args: Any) -> dict[str, Any]:
        if self.export_application is None:
            raise ProductError("ERR_NLE_SHELL_EXPORT_NOT_BOUND", "Export Queue is unavailable", ProductErrorCategory.STATE)
        if not isinstance(args, dict) or set(args) != {"confirmation_id"} or not isinstance(args["confirmation_id"], str):
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Export dispatch cancellation request is invalid", ProductErrorCategory.VALIDATION)
        token = args["confirmation_id"]
        with self._pending_dispatch_lock:
            pending = self._pending_dispatch_preparations.pop(token, None)
        if pending is None:
            raise ProductError(
                "ERR_EXPORT_CONFIRMATION_INVALID",
                "Export confirmation is missing or consumed",
                ProductErrorCategory.AUTHORIZATION,
            )
        return dict(self.export_application.cancel_dispatch(confirmation_id=token))

    def export_cancel(self, args: Any) -> dict[str, Any]:
        if self.export_application is None:
            raise ProductError("ERR_NLE_SHELL_EXPORT_NOT_BOUND", "Export Queue is unavailable", ProductErrorCategory.STATE)
        if not isinstance(args, dict) or set(args) != {"job_id", "expected_state_version"}:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Export cancel request is invalid", ProductErrorCategory.VALIDATION)
        job = self.export_application.cancel(
            job_id=str(args["job_id"]),
            expected_state_version=_frame(args["expected_state_version"], "expected_state_version", minimum=1),
        )
        return {"job_id": job.job_id, "state": job.state.value,
                "state_version": job.state_version, "external_mutation_started": False}

    def export_reconcile(self, args: Any) -> dict[str, Any]:
        if self.export_application is None:
            raise ProductError("ERR_NLE_SHELL_EXPORT_NOT_BOUND", "Export Queue is unavailable", ProductErrorCategory.STATE)
        required = {"job_id", "expected_state_version", "action", "result_identity", "render_qa_sha256"}
        if not isinstance(args, dict) or set(args) != required:
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Export recovery request is invalid", ProductErrorCategory.VALIDATION)
        action = str(args["action"])
        result = None
        if action == "ACCEPT_PROVEN_SUCCESS":
            try:
                result = ExportDispatchResult(
                    "SUCCEEDED", result_identity=str(args["result_identity"]),
                    render_qa_sha256=str(args["render_qa_sha256"]), render_qa_passed=True,
                )
            except ValueError as exc:
                raise ProductError(
                    "ERR_NLE_SHELL_EXPORT_PROOF_INVALID",
                    "Export result or Render QA proof is invalid",
                    ProductErrorCategory.VALIDATION,
                ) from exc
        elif args["result_identity"] is not None or args["render_qa_sha256"] is not None:
            raise ProductError(
                "ERR_NLE_SHELL_REQUEST_INVALID", "Non-success recovery cannot include result proof",
                ProductErrorCategory.VALIDATION,
            )
        job = self.export_application.reconcile(
            job_id=str(args["job_id"]),
            expected_state_version=_frame(args["expected_state_version"], "expected_state_version", minimum=1),
            action=action, result=result,
        )
        return {"job_id": job.job_id, "state": job.state.value,
                "state_version": job.state_version, "external_replay_started": False}

    def export_snapshot(self, args: Any = None) -> dict[str, Any]:
        if args not in (None, {}):
            raise ProductError("ERR_NLE_SHELL_REQUEST_INVALID", "Export snapshot request is invalid", ProductErrorCategory.VALIDATION)
        if self.export_application is None:
            return {"available": False, "rows": []}
        path = DurableProductJobStore.path(self.export_application.project_root)
        if not path.exists():
            return {"available": True, "rows": [], "blanket_execute_all_authorized": False}
        collection = DurableProductJobStore.load(self.export_application.project_root)
        rows = []
        for job in collection.jobs:
            shell = durable_job_shell_projection(job).to_dict()
            rows.append({**shell, "operation_identity": job.operation_identity,
                         "state_version": job.state_version,
                         "recovery_actions": list(job.recovery_actions),
                         "individual_confirmation_required": job.state is DurableProductJobState.READY})
        return {"available": True, "rows": rows,
                "blanket_execute_all_authorized": False,
                "host_output_path_persisted": False}


__all__ = ["Task044NleShellController"]
