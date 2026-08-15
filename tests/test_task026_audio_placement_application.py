from pathlib import Path

import pytest

from ai_video_production.audio_placement_application import Task026AudioPlacementApplication
from ai_video_production.audio_workspace import AudioWorkspaceRegistry, PlacementDecision, PlacementReview
from ai_video_production.audio_workspace_store import AudioWorkspaceSnapshotStore
from ai_video_production.errors import ProductError
from ai_video_production.product_project import ProductProjectManifest, ProjectChildBinding, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.production_control import (
    AssetCandidate,
    CandidateLifecycle,
    ProductionControlRegistry,
    SceneAssetSlot,
    SlotKind,
)
from ai_video_production.production_control_store import ProductionControlSnapshotStore
from ai_video_production.serialization import sha256_bytes
from ai_video_production.timebase import FrameRate
from ai_video_production.timeline_audio import AudioSourceBinding, AudioSourceIntent, MusicPlan, TimelineAudioPlan
from ai_video_production.timeline_audio_application import Task042TimelineAudioApplication


ASSET_SHA = "sha256:" + "2" * 64
CREATED = "2026-08-15T00:00:00.000Z"


def locked_production() -> ProductionControlRegistry:
    registry = ProductionControlRegistry()
    registry.add_slot(SceneAssetSlot("slot-bgm", "project-1", "scene-1", SlotKind.BGM, True))
    registry.add_candidate(AssetCandidate("candidate-1", "slot-bgm", "asset-1", ASSET_SHA, 1))
    registry.transition_candidate("candidate-1", CandidateLifecycle.READY_FOR_AUDIT)
    registry.transition_candidate("candidate-1", CandidateLifecycle.ACCEPTED)
    registry.lock_candidate(
        slot_id="slot-bgm",
        candidate_id="candidate-1",
        expected_revision=registry.slots["slot-bgm"].revision,
    )
    return registry


def setup_runnable_project(root: Path) -> None:
    blueprint = b'{"blueprint":true}'
    child = root / "state/blueprint.json"
    child.parent.mkdir()
    child.write_bytes(blueprint)
    blueprint_sha = sha256_bytes(blueprint)
    manifest = ProductProjectManifest.create(
        project_id="project-1",
        project_revision=1,
        product_version="0.21.0",
        timebase=ProjectTimebase(30, 1),
        child_bindings=(ProjectChildBinding(
            "TASK-042", "state/blueprint.json", "bai.test-blueprint", "1.0.0",
            blueprint_sha, True,
        ),),
        created_at=CREATED,
        updated_at=CREATED,
    )
    ProductProjectManifestStore.save(root, manifest)
    production = locked_production()
    ProductionControlSnapshotStore.save(root / "production-control.json", production)
    source = AudioSourceBinding(
        "slot-bgm", AudioSourceIntent.EXISTING_ASSET,
        "candidate-1", "asset-1", ASSET_SHA, 300,
    )
    item = MusicPlan(
        "music-1", "bgm-1", 0, 300, source,
        whole_timeline=True,
    )
    plan = TimelineAudioPlan(
        "project-1", "timeline-1", 1, "blueprint-1", blueprint_sha,
        FrameRate(30), 300, (item,),
    )
    timeline = Task042TimelineAudioApplication(
        project_root=root, project_id="project-1", token_factory=lambda: "timeline-confirm"
    )
    prepared = timeline.prepare_plan(
        plan=plan,
        production=production,
        expected_project_manifest_sha256=manifest.project_manifest_sha256,
    )
    timeline.apply_plan(confirmation_id=prepared["confirmation_id"])
    audio = AudioWorkspaceRegistry()
    audio.add_placement(PlacementReview(
        "review-1", "candidate-1", 0, 300, "BGM", PlacementDecision.ACCEPT,
        timeline_binding=plan.placement_binding("music-1"),
    ))
    AudioWorkspaceSnapshotStore.save(root / "audio-workspace.json", audio)


def prepare(app: Task026AudioPlacementApplication, snapshot: dict) -> dict:
    return app.prepare_compilation(
        review_id="review-1",
        track_index=2,
        bed_mode="FULL",
        expected_project_manifest_sha256=snapshot["project_manifest_sha256"],
        expected_production_snapshot_sha256=snapshot["production_snapshot_sha256"],
        expected_audio_snapshot_sha256=snapshot["audio_snapshot_sha256"],
        expected_timeline_snapshot_sha256=snapshot["timeline_snapshot_sha256"],
        expected_history_snapshot_sha256=snapshot["history_snapshot_sha256"],
    )


def test_compile_persists_restarts_current_and_is_idempotent(tmp_path: Path) -> None:
    setup_runnable_project(tmp_path)
    app = Task026AudioPlacementApplication(
        project_root=tmp_path, project_id="project-1", token_factory=lambda: "compile-1"
    )
    initial = app.snapshot()
    assert initial["reviews"][0]["runnable"] is True
    confirmation = prepare(app, initial)
    assert confirmation["estimated_cost"] == 0
    assert confirmation["resolve_mutation_started"] is False
    result = app.apply_compilation(confirmation_id=confirmation["confirmation_id"])
    assert result["apply_result"]["appended"] is True

    restarted = Task026AudioPlacementApplication(
        project_root=tmp_path, project_id="project-1", token_factory=lambda: "compile-2"
    )
    current = restarted.snapshot()
    assert current["records"][0]["currentness"] == "CURRENT"
    assert current["reviews"][0]["current_compilation_ids"] == [
        current["records"][0]["compilation_id"]
    ]
    before_revision = current["project_revision"]
    again = prepare(restarted, current)
    duplicate = restarted.apply_compilation(confirmation_id=again["confirmation_id"])
    assert duplicate["apply_result"]["idempotent"] is True
    assert duplicate["snapshot"]["project_revision"] == before_revision


def test_upstream_change_marks_history_stale_and_consumes_confirmation(tmp_path: Path) -> None:
    setup_runnable_project(tmp_path)
    app = Task026AudioPlacementApplication(
        project_root=tmp_path, project_id="project-1", token_factory=lambda: "compile-stale"
    )
    initial = app.snapshot()
    confirmation = prepare(app, initial)
    audio = AudioWorkspaceSnapshotStore.load(tmp_path / "audio-workspace.json")
    audio.add_placement(PlacementReview(
        "review-2", "candidate-1", 0, 300, "BGM", PlacementDecision.REVIEW,
    ))
    AudioWorkspaceSnapshotStore.save(
        tmp_path / "audio-workspace.json",
        audio,
        expected_previous_snapshot_sha256=initial["audio_snapshot_sha256"],
    )
    with pytest.raises(ProductError, match="Audio changed"):
        app.apply_compilation(confirmation_id=confirmation["confirmation_id"])
    with pytest.raises(ProductError, match="already consumed"):
        app.apply_compilation(confirmation_id=confirmation["confirmation_id"])


def test_unbound_history_is_rejected(tmp_path: Path) -> None:
    setup_runnable_project(tmp_path)
    path = tmp_path / "state/audio-placement-history.json"
    path.write_text("{}", encoding="utf-8")
    app = Task026AudioPlacementApplication(project_root=tmp_path, project_id="project-1")
    with pytest.raises(ProductError, match="Unbound"):
        app.snapshot()
