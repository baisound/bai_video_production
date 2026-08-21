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
    TimelineTrackCategory,
    TimelineTrackRole,
    timeline_track_category,
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
    TimelineSourceBinding,
)
from ai_video_production.interactive_timeline_store import (
    FORMAT_VERSION_V1_1,
    RELATIVE_PATH,
    TimelineEditSnapshotStore,
    parse_timeline_edit_history,
)
from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.project_history import ProjectCommandAction, ProjectCommandHistoryStore
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task044_nle_shell import Task044NleShellController
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


def source_binding(suffix: str) -> TimelineSourceBinding:
    return TimelineSourceBinding(
        project_id="project-1",
        production_snapshot_sha256=sha256_bytes(f"production-{suffix}".encode()),
        scene_id="scene-1",
        slot_id="slot-IMAGE-1",
        candidate_id=f"candidate-{suffix}",
        asset_id=f"asset-{suffix}",
        asset_sha256=sha256_bytes(f"asset-{suffix}".encode()),
        product_job_id="job-1",
        generation_execution_id=f"execution-{suffix}",
        queue_entry_id=f"queue-{suffix}",
    )


def placed_clip(suffix: str, *, clip_id: str = "placed-clip") -> InteractiveTimelineClip:
    binding = source_binding(suffix)
    return InteractiveTimelineClip(
        clip_id, "video-main", 60, 90, "TASK-003", binding.asset_id,
        binding.asset_sha256, f"Placed {suffix}", "PLACED_LOCKED_ASSET",
        binding.candidate_id,
    )


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


def test_v1_0_snapshot_bytes_and_hash_remain_frozen() -> None:
    base = timeline()
    history = TimelineEditHistory("project-1", "history-1")
    history.append(TimelineEditRevision(
        "project-1", "history-1", 1, base.timeline_sha256,
        TimelineEditCommand(
            "cmd-1", TimelineEditKind.MOVE, target_clip_id="clip-1",
            before_start_frame=10, before_end_frame=40,
            after_start_frame=20, after_end_frame=50,
        ),
    ))
    document = json.loads(TimelineEditSnapshotStore.serialize(history))
    assert document["snapshot_version"] == "1.0.0"
    assert document["snapshot_sha256"] == "sha256:9f210f9518dce1521e502a139070bb86dc6eb5e5e771f33326eaea603731cf15"
    assert document["revisions"][0]["revision_sha256"] == "sha256:5129f517f3d781353d42580c774d5d39dc63496b645303a0220eaa80c09ff637"
    assert document["revisions"][0]["command"]["command_sha256"] == "sha256:6f535287b747c7f7234afd81d8140de7351b099b1a331344f31caa473c371bbf"


def test_v1_1_binding_pairs_project_inverse_and_round_trip() -> None:
    base = timeline()
    binding_a = source_binding("a")
    binding_b = source_binding("b")
    clip_a = placed_clip("a")
    clip_b = InteractiveTimelineClip(
        clip_a.clip_id, clip_a.track_id, clip_a.start_frame, clip_a.end_frame,
        "TASK-003", binding_b.asset_id, binding_b.asset_sha256, "Placed b",
        "PLACED_LOCKED_ASSET", binding_b.candidate_id,
    )
    insert = TimelineEditCommand(
        "insert-a", TimelineEditKind.INSERT_CLIP,
        after_clip=clip_a, after_source_binding=binding_a,
    )
    replace = TimelineEditCommand(
        "replace-b", TimelineEditKind.REPLACE_CLIP,
        before_clip=clip_a, after_clip=clip_b,
        before_source_binding=binding_a, after_source_binding=binding_b,
    )
    undo = replace.inverse(command_id="undo-replace")
    history = TimelineEditHistory("project-1", "history-v11")
    history.append(TimelineEditRevision(
        "project-1", "history-v11", 1, base.timeline_sha256, insert,
        revision_version=FORMAT_VERSION_V1_1,
    ))
    history.append(TimelineEditRevision(
        "project-1", "history-v11", 2, base.timeline_sha256, replace,
        previous_revision_sha256=history.current.revision_sha256,
        revision_version=FORMAT_VERSION_V1_1,
    ))
    history.append(TimelineEditRevision(
        "project-1", "history-v11", 3, base.timeline_sha256, undo,
        previous_revision_sha256=history.current.revision_sha256,
        revision_version=FORMAT_VERSION_V1_1,
    ))
    serialized = TimelineEditSnapshotStore.serialize(history)
    restored = parse_timeline_edit_history(json.loads(serialized))
    projected, _in_out, bindings = TimelineEditProjector.apply_with_source_bindings(base, restored)
    assert json.loads(serialized)["snapshot_version"] == FORMAT_VERSION_V1_1
    assert next(item for item in projected.clips if item.clip_id == clip_a.clip_id) == clip_a
    assert bindings[clip_a.clip_id] == binding_a
    assert restored.revisions[1].command.before_source_binding == binding_a
    assert restored.revisions[1].command.after_source_binding == binding_b


def test_v1_1_legacy_replace_restores_null_binding_and_version_cannot_downgrade() -> None:
    base = timeline()
    before = base.clips[0]
    binding = source_binding("b")
    after = InteractiveTimelineClip(
        before.clip_id, before.track_id, before.start_frame, before.end_frame,
        "TASK-003", binding.asset_id, binding.asset_sha256, "Generated",
        "PLACED_LOCKED_ASSET", binding.candidate_id,
    )
    replacement = TimelineEditCommand(
        "replace-legacy", TimelineEditKind.REPLACE_CLIP,
        before_clip=before, after_clip=after,
        before_source_binding=None, after_source_binding=binding,
    )
    history = TimelineEditHistory("project-1", "history-v11")
    history.append(TimelineEditRevision(
        "project-1", "history-v11", 1, base.timeline_sha256, replacement,
        revision_version=FORMAT_VERSION_V1_1,
    ))
    inverse = replacement.inverse(command_id="undo-legacy")
    history.append(TimelineEditRevision(
        "project-1", "history-v11", 2, base.timeline_sha256, inverse,
        previous_revision_sha256=history.current.revision_sha256,
        revision_version=FORMAT_VERSION_V1_1,
    ))
    projected, _in_out, bindings = TimelineEditProjector.apply_with_source_bindings(base, history)
    assert projected.clips[0] == before
    assert bindings[before.clip_id] is None
    with pytest.raises(ProductError) as exc:
        history.append(TimelineEditRevision(
            "project-1", "history-v11", 3, base.timeline_sha256,
            TimelineEditCommand(
                "move-after-v11", TimelineEditKind.MOVE, target_clip_id=before.clip_id,
                before_start_frame=before.start_frame, before_end_frame=before.end_frame,
                after_start_frame=20, after_end_frame=50,
            ),
            previous_revision_sha256=history.current.revision_sha256,
        ))
    assert exc.value.code == "ERR_TIMELINE_EDIT_HISTORY_VERSION_DOWNGRADE"


@pytest.mark.parametrize("field,value", [
    ("candidate_id", "candidate-foreign"),
    ("project_id", "project-foreign"),
])
def test_checksum_valid_foreign_source_binding_fails_closed(field: str, value: str) -> None:
    base = timeline()
    binding = source_binding("a")
    clip = placed_clip("a")
    history = TimelineEditHistory("project-1", "history-v11")
    history.append(TimelineEditRevision(
        "project-1", "history-v11", 1, base.timeline_sha256,
        TimelineEditCommand(
            "insert-a", TimelineEditKind.INSERT_CLIP,
            after_clip=clip, after_source_binding=binding,
        ),
        revision_version=FORMAT_VERSION_V1_1,
    ))
    document = json.loads(TimelineEditSnapshotStore.serialize(history))
    command = document["revisions"][0]["command"]
    command["after_source_binding"][field] = value
    command_body = {key: item for key, item in command.items() if key != "command_sha256"}
    command["command_sha256"] = sha256_bytes(canonical_json_bytes(command_body))
    revision = document["revisions"][0]
    revision_body = {key: item for key, item in revision.items() if key != "revision_sha256"}
    revision["revision_sha256"] = sha256_bytes(canonical_json_bytes(revision_body))
    snapshot_body = {key: item for key, item in document.items() if key != "snapshot_sha256"}
    document["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(snapshot_body))
    with pytest.raises(ProductError) as exc:
        parse_timeline_edit_history(document)
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
    with pytest.raises(ProductError) as exc:
        app.prepare_remove_track(
            timeline=base, track_id="audio-spare", command_id="remove-last-audio",
            expected_project_manifest_sha256=current.project_manifest_sha256,
        )
    assert exc.value.code == "ERR_TIMELINE_TRACK_REMOVE_BLOCKED"
    added = TimelineTrack("audio-second", 2, TimelineTrackRole.AUDIO, TimelineMediaKind.AUDIO, "Audio 2")
    inverse = TimelineEditCommand(
        "add-audio", TimelineEditKind.ADD_TRACK, track=added,
    ).inverse(command_id="undo-add-audio")
    assert inverse.kind is TimelineEditKind.REMOVE_TRACK
    assert inverse.track == added
    controller = Task044NleShellController(timeline=base, edit_application=app)
    prepared_add = controller.prepare_add_track({
        "category": "VIDEO", "command_id": "add-video-two",
        "expected_project_manifest_sha256": current.project_manifest_sha256,
        "expected_timeline_sha256": base.timeline_sha256,
    })
    controller.apply_edit({"confirmation_id": prepared_add["confirmation_id"]})
    after_add = ProductProjectManifestStore.load(tmp_path)
    assert any(item["track_id"] == "V1" for item in controller.snapshot()["projection"]["tracks"])
    prepared_remove = controller.prepare_remove_track({
        "track_id": "V1", "command_id": "remove-video-two",
        "expected_project_manifest_sha256": after_add.project_manifest_sha256,
        "expected_timeline_sha256": base.timeline_sha256,
    })
    controller.apply_edit({"confirmation_id": prepared_remove["confirmation_id"]})
    assert all(item["track_id"] != "V1" for item in controller.snapshot()["projection"]["tracks"])
    assert ShellApplicationService.command_spec("timeline.edit.prepare").category is CommandCategory.READ_ONLY
    assert ShellApplicationService.command_spec("timeline.edit.apply").category is CommandCategory.HUMAN_FINAL_AUTHORITY
    assert ShellApplicationService.command_spec("timeline.in_out.update").category is CommandCategory.LOCAL_REVERSIBLE
    assert ShellApplicationService.command_spec("timeline.track.apply").category is CommandCategory.HUMAN_FINAL_AUTHORITY


def test_each_v6_track_category_keeps_its_last_track() -> None:
    tracks = (
        TimelineTrack("V1", 1, TimelineTrackRole.VIDEO, TimelineMediaKind.VIDEO, "Video"),
        TimelineTrack("S1", 2, TimelineTrackRole.SUBTITLE, TimelineMediaKind.TEXT, "Subtitle"),
        TimelineTrack("A1", 3, TimelineTrackRole.AUDIO, TimelineMediaKind.AUDIO, "Audio"),
        TimelineTrack("SE1", 4, TimelineTrackRole.AUDIO, TimelineMediaKind.AUDIO, "SE"),
        TimelineTrack("BGM1", 5, TimelineTrackRole.AUDIO, TimelineMediaKind.AUDIO, "BGM"),
    )
    expected = (
        TimelineTrackCategory.VIDEO,
        TimelineTrackCategory.SUBTITLE,
        TimelineTrackCategory.AUDIO,
        TimelineTrackCategory.SE,
        TimelineTrackCategory.BGM,
    )
    assert tuple(timeline_track_category(track) for track in tracks) == expected
    base = InteractiveTimeline(
        "project-1", "timeline-categories", FrameRate(30, 1), 300, tracks, (),
    )
    for revision, track in enumerate(tracks, start=1):
        history = TimelineEditHistory("project-1", f"history-{revision}")
        history.append(TimelineEditRevision(
            "project-1", f"history-{revision}", 1, base.timeline_sha256,
            TimelineEditCommand(
                f"remove-{track.track_id}", TimelineEditKind.REMOVE_TRACK,
                target_track_id=track.track_id, track=track,
            ),
        ))
        with pytest.raises(ProductError) as exc:
            TimelineEditProjector.apply(base, history)
        assert exc.value.code == "ERR_TIMELINE_TRACK_REMOVE_BLOCKED"
