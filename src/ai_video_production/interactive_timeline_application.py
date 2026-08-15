"""Project-scoped prepare/apply boundary for TASK-044 Timeline edits."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import secrets
from typing import Callable, Iterable

from .atomic import AtomicJsonWriter
from .errors import ProductError, ProductErrorCategory
from .interactive_timeline import InteractiveTimeline, TimelineTrack, timeline_track_category
from .interactive_timeline_edit import (
    SnapAnchor,
    TimelineEditCommand,
    TimelineEditHistory,
    TimelineEditKind,
    TimelineEditProjector,
    TimelineEditRevision,
    TimelineSnapService,
)
from .interactive_timeline_store import (
    FORMAT_ID,
    FORMAT_VERSION,
    RELATIVE_PATH,
    TimelineEditSnapshotStore,
)
from .product_project import ProductProjectManifest, ProjectChildBinding
from .product_project_store import ProductProjectManifestStore
from .project_history import (
    ProjectCommandHistory, ProjectCommandHistoryStore, parse_project_command_history,
)
from .project_save import ProductProjectSaveCoordinator
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso

TokenFactory = Callable[[], str]


@dataclass(slots=True)
class _Confirmation:
    confirmation_id: str
    expected_manifest_sha256: str
    expected_history_sha256: str | None
    base_timeline_sha256: str
    command: TimelineEditCommand
    history_action: str
    consumed: bool = False


class Task044TimelineEditApplication:
    """Adds immutable Timeline revisions; no provider or native mutation occurs."""

    def __init__(self, *, project_root: str | Path, project_id: str,
                 token_factory: TokenFactory | None = None) -> None:
        self.project_root = Path(project_root).resolve(strict=True)
        self.project_id = project_id
        manifest = ProductProjectManifestStore.load(self.project_root)
        if manifest.project_id != project_id:
            raise ProductError("ERR_TIMELINE_EDIT_PROJECT_MISMATCH", "Project identity differs", ProductErrorCategory.SECURITY)
        self._recover_command_history()
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._pending: dict[str, _Confirmation] = {}

    @property
    def _history_recovery_path(self) -> Path:
        return ProductProjectManifestStore.path(self.project_root).with_name(
            "timeline-edit-command-recovery.json"
        )

    @staticmethod
    def _parse_history_recovery(document):
        fields = {"recovery_version", "project_id", "source_manifest_sha256",
                  "result_manifest_sha256", "expected_history_sha256", "history",
                  "recovery_sha256"}
        if not isinstance(document, dict) or set(document) != fields:
            raise ValueError("Timeline history recovery fields are not exact")
        claimed = document["recovery_sha256"]
        body = {key: value for key, value in document.items() if key != "recovery_sha256"}
        if claimed != sha256_bytes(canonical_json_bytes(body)) or document["recovery_version"] != "1.0.0":
            raise ValueError("Timeline history recovery checksum is invalid")
        parse_project_command_history(document["history"])
        return document

    def _write_history_recovery(self, *, source_manifest_sha256: str,
                                result_manifest_sha256: str,
                                expected_history_sha256: str | None,
                                history: ProjectCommandHistory) -> None:
        body = {"recovery_version": "1.0.0", "project_id": self.project_id,
                "source_manifest_sha256": source_manifest_sha256,
                "result_manifest_sha256": result_manifest_sha256,
                "expected_history_sha256": expected_history_sha256,
                "history": history.to_dict()}
        AtomicJsonWriter.write(
            self._history_recovery_path,
            {**body, "recovery_sha256": sha256_bytes(canonical_json_bytes(body))},
            validator=self._parse_history_recovery,
        )

    def _recover_command_history(self) -> None:
        path = self._history_recovery_path
        if not path.exists():
            return
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 8 * 1024 * 1024:
            raise ProductError("ERR_TIMELINE_EDIT_HISTORY_RECOVERY_INVALID", "Timeline history recovery is invalid", ProductErrorCategory.DATA_INTEGRITY)
        if ProductProjectSaveCoordinator().recovery_status(self.project_root)["required"]:
            raise ProductError("ERR_TIMELINE_EDIT_PROJECT_RECOVERY_PENDING", "Complete or roll back the Project save first", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        try:
            recovery = self._parse_history_recovery(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise ProductError("ERR_TIMELINE_EDIT_HISTORY_RECOVERY_INVALID", "Timeline history recovery is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
        if recovery["project_id"] != self.project_id:
            raise ProductError("ERR_TIMELINE_EDIT_HISTORY_RECOVERY_IDENTITY", "Recovery belongs to another Project", ProductErrorCategory.SECURITY)
        manifest = ProductProjectManifestStore.load(self.project_root)
        if manifest.project_manifest_sha256 == recovery["source_manifest_sha256"]:
            path.unlink()
            return
        if manifest.project_manifest_sha256 != recovery["result_manifest_sha256"]:
            raise ProductError("ERR_TIMELINE_EDIT_HISTORY_RECOVERY_CONFLICT", "Project moved beyond Timeline recovery", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        target_history = parse_project_command_history(recovery["history"])
        current_path = ProjectCommandHistoryStore.path(self.project_root)
        if current_path.exists():
            current = ProjectCommandHistoryStore.load(self.project_root)
            if current.history_sha256 == target_history.history_sha256:
                path.unlink()
                return
        ProjectCommandHistoryStore.save(
            self.project_root, target_history,
            expected_previous_history_sha256=recovery["expected_history_sha256"],
        )
        path.unlink()

    @property
    def snapshot_path(self) -> Path:
        return self.project_root / RELATIVE_PATH

    def _load(self, manifest: ProductProjectManifest) -> TimelineEditHistory:
        binding = next((item for item in manifest.child_bindings if item.identity == ("TASK-044", RELATIVE_PATH)), None)
        if binding is None:
            if self.snapshot_path.exists():
                raise ProductError("ERR_TIMELINE_EDIT_UNBOUND_CHILD", "Unbound Timeline edit child exists", ProductErrorCategory.SECURITY)
            return TimelineEditHistory(self.project_id, f"timeline-edit:{self.project_id}")
        if binding.format_id != FORMAT_ID or binding.format_version != FORMAT_VERSION:
            raise ProductError("ERR_TIMELINE_EDIT_FORMAT_MISMATCH", "Timeline edit format is unsupported", ProductErrorCategory.NOT_SUPPORTED)
        history = TimelineEditSnapshotStore.load(self.snapshot_path, expected_project_id=self.project_id)
        if sha256_bytes(TimelineEditSnapshotStore.serialize(history)) != binding.content_sha256:
            raise ProductError("ERR_TIMELINE_EDIT_BINDING_CHECKSUM", "Timeline edit child differs from Project binding", ProductErrorCategory.DATA_INTEGRITY)
        return history

    def _load_project_history(self) -> tuple[ProjectCommandHistory, str | None]:
        target = ProjectCommandHistoryStore.path(self.project_root)
        if not target.exists():
            return ProjectCommandHistory.create(self.project_id), None
        history = ProjectCommandHistoryStore.load(self.project_root)
        if history.project_id != self.project_id:
            raise ProductError("ERR_PROJECT_HISTORY_IDENTITY_CONFLICT", "Project history belongs to another Project", ProductErrorCategory.SECURITY)
        return history, history.history_sha256

    @staticmethod
    def _clip(timeline: InteractiveTimeline, clip_id: str):
        clip = next((item for item in timeline.clips if item.clip_id == clip_id), None)
        if clip is None:
            raise ProductError("ERR_TIMELINE_EDIT_CLIP_MISSING", "Timeline clip is missing", ProductErrorCategory.STATE)
        return clip

    @staticmethod
    def _snap(desired: int, tolerance: int, anchors: Iterable[SnapAnchor]):
        return TimelineSnapService.snap(desired, tolerance_frames=tolerance, anchors=anchors)

    def prepare_trim(self, *, timeline: InteractiveTimeline, clip_id: str, edge: str,
                     desired_frame: int, snap_tolerance_frames: int = 0,
                     snap_anchors: Iterable[SnapAnchor] = (), command_id: str,
                     expected_project_manifest_sha256: str) -> dict[str, object]:
        projected, _ = TimelineEditProjector.apply(timeline, self._load(ProductProjectManifestStore.load(self.project_root)))
        clip = self._clip(projected, clip_id)
        decision = self._snap(desired_frame, snap_tolerance_frames, snap_anchors)
        if edge == "start":
            kind, start, end = TimelineEditKind.TRIM_START, decision.effective_frame, clip.end_frame
        elif edge == "end":
            kind, start, end = TimelineEditKind.TRIM_END, clip.start_frame, decision.effective_frame
        else:
            raise ValueError("edge must be start or end")
        if start < 0 or end > timeline.duration_frames or end <= start:
            raise ProductError("ERR_TIMELINE_EDIT_RANGE", "Trim would create an invalid range", ProductErrorCategory.VALIDATION)
        command = TimelineEditCommand(command_id, kind, target_clip_id=clip_id,
            before_start_frame=clip.start_frame, before_end_frame=clip.end_frame,
            after_start_frame=start, after_end_frame=end, snap=decision)
        return self._prepare(timeline, command, expected_project_manifest_sha256, "APPLY")

    def prepare_move(self, *, timeline: InteractiveTimeline, clip_id: str, desired_start_frame: int,
                     snap_tolerance_frames: int = 0, snap_anchors: Iterable[SnapAnchor] = (),
                     command_id: str, expected_project_manifest_sha256: str) -> dict[str, object]:
        projected, _ = TimelineEditProjector.apply(timeline, self._load(ProductProjectManifestStore.load(self.project_root)))
        clip = self._clip(projected, clip_id)
        decision = self._snap(desired_start_frame, snap_tolerance_frames, snap_anchors)
        end = decision.effective_frame + (clip.end_frame - clip.start_frame)
        if decision.effective_frame < 0 or end > timeline.duration_frames:
            raise ProductError("ERR_TIMELINE_EDIT_RANGE", "Move would leave the Timeline", ProductErrorCategory.VALIDATION)
        command = TimelineEditCommand(command_id, TimelineEditKind.MOVE, target_clip_id=clip_id,
            before_start_frame=clip.start_frame, before_end_frame=clip.end_frame,
            after_start_frame=decision.effective_frame, after_end_frame=end, snap=decision)
        return self._prepare(timeline, command, expected_project_manifest_sha256, "APPLY")

    def prepare_add_track(self, *, timeline: InteractiveTimeline, track: TimelineTrack,
                          command_id: str, expected_project_manifest_sha256: str) -> dict[str, object]:
        projected, _ = TimelineEditProjector.apply(timeline, self._load(ProductProjectManifestStore.load(self.project_root)))
        if any(item.track_id == track.track_id for item in projected.tracks):
            raise ProductError("ERR_TIMELINE_TRACK_EXISTS", "Track already exists", ProductErrorCategory.STATE)
        return self._prepare(timeline, TimelineEditCommand(command_id, TimelineEditKind.ADD_TRACK, track=track),
                             expected_project_manifest_sha256, "APPLY")

    def prepare_remove_track(self, *, timeline: InteractiveTimeline, track_id: str,
                             command_id: str, expected_project_manifest_sha256: str) -> dict[str, object]:
        projected, _ = TimelineEditProjector.apply(timeline, self._load(ProductProjectManifestStore.load(self.project_root)))
        track = next((item for item in projected.tracks if item.track_id == track_id), None)
        category_count = 0 if track is None else sum(
            timeline_track_category(item) is timeline_track_category(track)
            for item in projected.tracks
        )
        if (track is None or track.minimum_required or category_count <= 1
                or any(item.track_id == track_id for item in projected.clips)):
            raise ProductError("ERR_TIMELINE_TRACK_REMOVE_BLOCKED", "Required, missing or non-empty track cannot be removed", ProductErrorCategory.STATE)
        command = TimelineEditCommand(command_id, TimelineEditKind.REMOVE_TRACK,
                                      target_track_id=track_id, track=track)
        return self._prepare(timeline, command, expected_project_manifest_sha256, "APPLY")

    def prepare_undo(self, *, timeline: InteractiveTimeline, command_id: str,
                     expected_project_manifest_sha256: str) -> dict[str, object]:
        project_history, _ = self._load_project_history()
        candidate = project_history.undo_candidate()
        if candidate is None or not candidate.command_kind.startswith("timeline."):
            raise ProductError("ERR_TIMELINE_EDIT_UNDO_EMPTY", "No Timeline edit is available to undo", ProductErrorCategory.STATE)
        edit_history = self._load(ProductProjectManifestStore.load(self.project_root))
        original = next((item.command for item in edit_history.revisions if item.command.command_id == candidate.target_identity), None)
        if original is None:
            raise ProductError("ERR_TIMELINE_EDIT_UNDO_TARGET", "Undo target is missing", ProductErrorCategory.DATA_INTEGRITY)
        return self._prepare(timeline, original.inverse(command_id=command_id), expected_project_manifest_sha256, "UNDO")

    def prepare_redo(self, *, timeline: InteractiveTimeline, command_id: str,
                     expected_project_manifest_sha256: str) -> dict[str, object]:
        project_history, _ = self._load_project_history()
        candidate = project_history.redo_candidate()
        if candidate is None or not candidate.command_kind.startswith("timeline."):
            raise ProductError("ERR_TIMELINE_EDIT_REDO_EMPTY", "No Timeline edit is available to redo", ProductErrorCategory.STATE)
        edit_history = self._load(ProductProjectManifestStore.load(self.project_root))
        original = next((item.command for item in edit_history.revisions if item.command.command_id == candidate.target_identity), None)
        if original is None:
            raise ProductError("ERR_TIMELINE_EDIT_REDO_TARGET", "Redo target is missing", ProductErrorCategory.DATA_INTEGRITY)
        projected, _ = TimelineEditProjector.apply(timeline, edit_history)
        if original.target_clip_id is not None:
            clip = self._clip(projected, original.target_clip_id)
            replay = TimelineEditCommand(command_id, original.kind, target_clip_id=clip.clip_id,
                before_start_frame=clip.start_frame, before_end_frame=clip.end_frame,
                after_start_frame=original.after_start_frame, after_end_frame=original.after_end_frame,
                snap=original.snap)
        elif original.kind is TimelineEditKind.ADD_TRACK:
            replay = TimelineEditCommand(command_id, original.kind, track=original.track)
        else:
            replay = TimelineEditCommand(command_id, original.kind,
                                         target_track_id=original.target_track_id, track=original.track)
        return self._prepare(timeline, replay, expected_project_manifest_sha256, "REDO")

    def _prepare(self, timeline: InteractiveTimeline, command: TimelineEditCommand,
                 expected_manifest: str, history_action: str) -> dict[str, object]:
        manifest = ProductProjectManifestStore.load(self.project_root)
        if manifest.project_manifest_sha256 != expected_manifest:
            raise ProductError("ERR_TIMELINE_EDIT_PROJECT_CONFLICT", "Project changed; reload first", ProductErrorCategory.STATE)
        if timeline.project_id != self.project_id:
            raise ProductError("ERR_TIMELINE_EDIT_PROJECT_MISMATCH", "Timeline belongs to another Project", ProductErrorCategory.SECURITY)
        history = self._load(manifest)
        TimelineEditProjector.apply(timeline, history)
        project_history, project_history_sha = self._load_project_history()
        if project_history.records and project_history.records[-1].result_manifest_sha256 != manifest.project_manifest_sha256:
            raise ProductError("ERR_PROJECT_HISTORY_SOURCE_CONFLICT", "Project history is not at current Manifest", ProductErrorCategory.STATE)
        token = self._token_factory()
        if not isinstance(token, str) or not token or token in self._pending:
            raise ProductError("ERR_TIMELINE_EDIT_CONFIRMATION_INVALID", "Confirmation identity is invalid", ProductErrorCategory.INTERNAL)
        self._pending[token] = _Confirmation(token, expected_manifest, project_history_sha,
                                             timeline.timeline_sha256, command, history_action)
        return {"confirmation_id": token, "command": command.to_dict(),
                "human_confirmation_required": True, "provider_execution_started": False,
                "external_mutation_started": False}

    def apply(self, *, confirmation_id: str, timeline: InteractiveTimeline) -> dict[str, object]:
        pending = self._pending.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError("ERR_TIMELINE_EDIT_CONFIRMATION_INVALID", "Confirmation is missing or consumed", ProductErrorCategory.AUTHORIZATION)
        pending.consumed = True
        manifest = ProductProjectManifestStore.load(self.project_root)
        if manifest.project_manifest_sha256 != pending.expected_manifest_sha256 or timeline.timeline_sha256 != pending.base_timeline_sha256:
            raise ProductError("ERR_TIMELINE_EDIT_PROJECT_CONFLICT", "Project or Timeline changed after preparation", ProductErrorCategory.STATE)
        history = self._load(manifest)
        TimelineEditProjector.apply(timeline, history)
        revision = TimelineEditRevision(
            self.project_id, history.history_id, len(history.revisions) + 1, timeline.timeline_sha256,
            pending.command, None if history.current is None else history.current.revision_sha256,
        )
        history.append(revision)
        TimelineEditProjector.apply(timeline, history)
        data = TimelineEditSnapshotStore.serialize(history)
        binding = ProjectChildBinding("TASK-044", RELATIVE_PATH, FORMAT_ID, FORMAT_VERSION,
                                      sha256_bytes(data), True, (timeline.timeline_sha256,))
        bindings = [item for item in manifest.child_bindings if item.identity != binding.identity] + [binding]
        target = ProductProjectManifest.create(
            project_id=manifest.project_id, project_revision=manifest.project_revision + 1,
            product_version=manifest.product_version, timebase=manifest.timebase,
            child_bindings=bindings, created_at=manifest.created_at,
            updated_at=max(manifest.updated_at, utc_now_iso()),
        )
        project_history, current_history_sha = self._load_project_history()
        if current_history_sha != pending.expected_history_sha256:
            raise ProductError("ERR_PROJECT_HISTORY_CAS_CONFLICT", "Project history changed after preparation", ProductErrorCategory.STATE)
        # The save coordinator deliberately requires an already-resolved parent
        # so a child path can never escape through a newly introduced symlink.
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        command_kind = f"timeline.{pending.command.kind.value.lower()}"
        if pending.history_action == "APPLY":
            updated_project_history = project_history.append_apply(
                command_kind=command_kind, target_identity=pending.command.command_id,
                source_manifest_sha256=manifest.project_manifest_sha256,
                result_manifest_sha256=target.project_manifest_sha256,
                source_revision=manifest.project_revision,
            )
        elif pending.history_action == "UNDO":
            updated_project_history = project_history.append_undo(
                source_manifest_sha256=manifest.project_manifest_sha256,
                result_manifest_sha256=target.project_manifest_sha256,
                source_revision=manifest.project_revision,
            )
        else:
            updated_project_history = project_history.append_redo(
                source_manifest_sha256=manifest.project_manifest_sha256,
                result_manifest_sha256=target.project_manifest_sha256,
                source_revision=manifest.project_revision,
            )
        self._write_history_recovery(
            source_manifest_sha256=manifest.project_manifest_sha256,
            result_manifest_sha256=target.project_manifest_sha256,
            expected_history_sha256=current_history_sha,
            history=updated_project_history,
        )
        saved = ProductProjectSaveCoordinator().save(
            self.project_root, target, {RELATIVE_PATH: data},
            expected_previous_manifest_sha256=manifest.project_manifest_sha256,
        )
        ProjectCommandHistoryStore.save(self.project_root, updated_project_history,
                                        expected_previous_history_sha256=current_history_sha)
        self._history_recovery_path.unlink()
        projected, in_out = TimelineEditProjector.apply(timeline, history)
        return {"project_manifest_sha256": saved.project_manifest_sha256,
                "timeline_revision": revision.revision, "timeline_revision_sha256": revision.revision_sha256,
                "project_history_sha256": updated_project_history.history_sha256,
                "projected_timeline_sha256": projected.timeline_sha256, "in_out": in_out,
                "provider_execution_started": False, "external_mutation_started": False}


__all__ = ["Task044TimelineEditApplication"]
