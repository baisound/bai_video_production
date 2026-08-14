from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.desktop_shell import CommandCategory, ShellApplicationService
from ai_video_production.errors import ProductError
from ai_video_production.interactive_timeline import (
    InteractiveTimeline,
    InteractiveTimelineClip,
    TimelineMediaKind,
    TimelineTrack,
    TimelineTrackRole,
)
from ai_video_production.interactive_timeline_application import Task044TimelineEditApplication
from ai_video_production.interactive_timeline_edit import (
    SnapAnchor,
    SnapKind,
    TimelineEditCommand,
    TimelineEditHistory,
    TimelineEditKind,
    TimelineEditProjector,
    TimelineEditRevision,
    TimelineSnapService,
)
from ai_video_production.interactive_timeline_store import (
    RELATIVE_PATH,
    TimelineEditSnapshotStore,
    parse_timeline_edit_history,
)
from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.project_history import ProjectCommandAction, ProjectCommandHistoryStore
from ai_video_production.serialization import sha256_bytes
from ai_video_production.timebase import FrameRate

CREATED = "2026-08-15T00:00:00.000Z"


def setup_project(root: Path) -> ProductProjectManifest:
    manifest = ProductProjectManifest.create(
        project_id="project-1", project_revision=1, product_version="0.20.1",
        timebase=ProjectTimebase(30, 1), child_bindings=(), created_at=CREATED,
        updated_at=CREATED,
    )
    ProductProjectManifestStore.save(root, manifest)
    return manifest


def timeline() -> InteractiveTimeline:
    tracks = (
        TimelineTrack("video-main", 0, TimelineTrackRole.VIDEO, TimelineMediaKind.VIDEO, "Video", True),
        TimelineTrack("audio-spare", 1, TimelineTrackRole.AUDIO, TimelineMediaKind.AUDIO, "Spare"),
    )
    clips = (InteractiveTimelineClip(
        "clip-1", "video-main", 10, 40, "TASK-007", "segment-1",
        sha256_bytes(b"source"), "Clip 1", "APPROVED",
    ),)
    return InteractiveTimeline("project-1", "timeline-1", FrameRate(30, 1), 300, tracks, clips)


def test_snap_is_frame_exact_and_ties_use_priority_then_identity() -> None:
    anchors = (
        SnapAnchor("scene-b", 102, SnapKind.SCENE_BOUNDARY, 2),
        SnapAnchor("marker-a", 98, SnapKind.MARKER, 1),
        SnapAnchor("marker-b", 102, SnapKind.MARKER, 1),
    )
    decision = TimelineSnapService.snap(100, tolerance_frames=2, anchors=anchors)
    assert decision.effective_frame == 98
    assert decision.anchor.anchor_id == "marker-a"
    with pytest.raises(ValueError):
        TimelineSnapService.snap(True, tolerance_frames=2, anchors=anchors)
    with pytest.raises(ValueError):
        TimelineSnapService.snap(10, tolerance_frames=1.5, anchors=anchors)


def test_projector_rejects_stale_ranges_and_protected_track_removal() -> None:
    base = timeline()
    history = TimelineEditHistory("project-1", "history-1")
    command = TimelineEditCommand(
        "cmd-1", TimelineEditKind.TRIM_START, target_clip_id="clip-1",
        before_start_frame=9, before_end_frame=40, after_start_frame=12, after_end_frame=40,
    )
    history.append(TimelineEditRevision("project-1", "history-1", 1, base.timeline_sha256, command))
    with pytest.raises(ProductError) as exc:
        TimelineEditProjector.apply(base, history)
    assert exc.value.code == "ERR_TIMELINE_EDIT_TARGET_STALE"

    protected = TimelineEditHistory("project-1", "history-2")
    protected.append(TimelineEditRevision(
        "project-1", "history-2", 1, base.timeline_sha256,
        TimelineEditCommand("cmd-2", TimelineEditKind.REMOVE_TRACK,
                            target_track_id="video-main", track=base.tracks[0]),
    ))
    with pytest.raises(ProductError) as exc:
        TimelineEditProjector.apply(base, protected)
    assert exc.value.code == "ERR_TIMELINE_TRACK_REMOVE_BLOCKED"


def test_snapshot_is_exact_append_only_and_tamper_evident() -> None:
    base = timeline()
    history = TimelineEditHistory("project-1", "history-1")
    history.append(TimelineEditRevision(
        "project-1", "history-1", 1, base.timeline_sha256,
        TimelineEditCommand("cmd-1", TimelineEditKind.MOVE, target_clip_id="clip-1",
                            before_start_frame=10, before_end_frame=40,
                            after_start_frame=20, after_end_frame=50),
    ))
    data = TimelineEditSnapshotStore.serialize(history)
    assert parse_timeline_edit_history(json.loads(data)).current.revision == 1
    changed = json.loads(data)
    changed["current_revision"] = 2
    with pytest.raises(ProductError) as exc:
        parse_timeline_edit_history(changed)
    assert exc.value.code == "ERR_TIMELINE_EDIT_SNAPSHOT_INVALID"


def test_trim_apply_reopen_undo_redo_and_exact_project_history(tmp_path: Path) -> None:
    current = setup_project(tmp_path)
    base = timeline()
    tokens = iter(("confirm-apply", "confirm-undo", "confirm-redo"))
    app = Task044TimelineEditApplication(
        project_root=tmp_path, project_id="project-1", token_factory=lambda: next(tokens)
    )
    prepared = app.prepare_trim(
        timeline=base, clip_id="clip-1", edge="start", desired_frame=14,
        snap_tolerance_frames=2,
        snap_anchors=(SnapAnchor("scene-1", 15, SnapKind.SCENE_BOUNDARY, 1),),
        command_id="trim-1", expected_project_manifest_sha256=current.project_manifest_sha256,
    )
    applied = app.apply(confirmation_id=prepared["confirmation_id"], timeline=base)
    assert applied["timeline_revision"] == 1
    assert applied["external_mutation_started"] is False
    first = ProductProjectManifestStore.load(tmp_path)
    assert first.project_revision == 2
    assert (tmp_path / RELATIVE_PATH).is_file()
    projected, _ = TimelineEditProjector.apply(base, app._load(first))
    assert projected.clips[0].start_frame == 15

    undo = app.prepare_undo(
        timeline=base, command_id="undo-1",
        expected_project_manifest_sha256=first.project_manifest_sha256,
    )
    app.apply(confirmation_id=undo["confirmation_id"], timeline=base)
    second = ProductProjectManifestStore.load(tmp_path)
    projected, _ = TimelineEditProjector.apply(base, app._load(second))
    assert projected.clips[0].start_frame == 10

    redo = app.prepare_redo(
        timeline=base, command_id="redo-1",
        expected_project_manifest_sha256=second.project_manifest_sha256,
    )
    app.apply(confirmation_id=redo["confirmation_id"], timeline=base)
    final = ProductProjectManifestStore.load(tmp_path)
    projected, _ = TimelineEditProjector.apply(base, app._load(final))
    assert projected.clips[0].start_frame == 15
    records = ProjectCommandHistoryStore.load(tmp_path).records
    assert [item.action for item in records] == [
        ProjectCommandAction.APPLY, ProjectCommandAction.UNDO, ProjectCommandAction.REDO,
    ]
    assert [item.source_revision for item in records] == [1, 2, 3]


def test_confirmation_and_manifest_cas_fail_closed(tmp_path: Path) -> None:
    current = setup_project(tmp_path)
    base = timeline()
    app = Task044TimelineEditApplication(
        project_root=tmp_path, project_id="project-1", token_factory=lambda: "confirm-once"
    )
    prepared = app.prepare_move(
        timeline=base, clip_id="clip-1", desired_start_frame=20, command_id="move-1",
        expected_project_manifest_sha256=current.project_manifest_sha256,
    )
    app.apply(confirmation_id=prepared["confirmation_id"], timeline=base)
    with pytest.raises(ProductError) as exc:
        app.apply(confirmation_id=prepared["confirmation_id"], timeline=base)
    assert exc.value.code == "ERR_TIMELINE_EDIT_CONFIRMATION_INVALID"


def test_reopen_completes_command_history_after_post_manifest_interruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current = setup_project(tmp_path)
    base = timeline()
    app = Task044TimelineEditApplication(
        project_root=tmp_path, project_id="project-1", token_factory=lambda: "confirm-recovery"
    )
    prepared = app.prepare_move(
        timeline=base, clip_id="clip-1", desired_start_frame=20, command_id="move-recovery",
        expected_project_manifest_sha256=current.project_manifest_sha256,
    )
    original = ProjectCommandHistoryStore.save
    monkeypatch.setattr(ProjectCommandHistoryStore, "save", staticmethod(lambda *args, **kwargs: (_ for _ in ()).throw(OSError("interrupted"))))
    with pytest.raises(OSError):
        app.apply(confirmation_id=prepared["confirmation_id"], timeline=base)
    assert ProductProjectManifestStore.load(tmp_path).project_revision == 2
    monkeypatch.setattr(ProjectCommandHistoryStore, "save", staticmethod(original))
    Task044TimelineEditApplication(project_root=tmp_path, project_id="project-1")
    history = ProjectCommandHistoryStore.load(tmp_path)
    assert len(history.records) == 1
    assert history.records[0].target_identity == "move-recovery"


def test_track_guards_and_shell_authority_categories(tmp_path: Path) -> None:
    current = setup_project(tmp_path)
    base = timeline()
    app = Task044TimelineEditApplication(project_root=tmp_path, project_id="project-1")
    with pytest.raises(ProductError) as exc:
        app.prepare_remove_track(
            timeline=base, track_id="video-main", command_id="remove-main",
            expected_project_manifest_sha256=current.project_manifest_sha256,
        )
    assert exc.value.code == "ERR_TIMELINE_TRACK_REMOVE_BLOCKED"
    assert ShellApplicationService.command_spec("timeline.edit.prepare").category is CommandCategory.READ_ONLY
    assert ShellApplicationService.command_spec("timeline.edit.apply").category is CommandCategory.HUMAN_FINAL_AUTHORITY
    assert ShellApplicationService.command_spec("timeline.in_out.update").category is CommandCategory.LOCAL_REVERSIBLE
    assert ShellApplicationService.command_spec("timeline.track.apply").category is CommandCategory.HUMAN_FINAL_AUTHORITY
