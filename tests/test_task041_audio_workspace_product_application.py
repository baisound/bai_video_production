from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.audio_workspace_application import Task041AudioWorkspaceApplication
from ai_video_production.errors import ProductError
from ai_video_production.production_control import (
    AssetCandidate,
    CandidateLifecycle,
    ProductionControlRegistry,
    SceneAssetSlot,
    SlotKind,
)
from ai_video_production.production_control_application import Task037ProductionControlApplication
from ai_video_production.production_control_store import ProductionControlSnapshotStore


SHA = "sha256:" + "a" * 64


def persisted_production(root: Path, *, locked: bool = True) -> Task037ProductionControlApplication:
    registry = ProductionControlRegistry()
    registry.add_slot(SceneAssetSlot("slot-bgm", "project-1", "scene-1", SlotKind.BGM, True))
    registry.add_candidate(AssetCandidate("candidate-bgm", "slot-bgm", "asset-bgm", SHA, 1))
    registry.transition_candidate("candidate-bgm", CandidateLifecycle.READY_FOR_AUDIT)
    registry.transition_candidate("candidate-bgm", CandidateLifecycle.ACCEPTED)
    if locked:
        registry.lock_candidate(
            slot_id="slot-bgm",
            candidate_id="candidate-bgm",
            expected_revision=registry.slots["slot-bgm"].revision,
        )
    ProductionControlSnapshotStore.save(root / "production-control.json", registry)
    return Task037ProductionControlApplication(project_root=root, project_id="project-1")


def application(root: Path, *, locked: bool = True):
    production = persisted_production(root, locked=locked)
    tokens = iter(("placement-confirm", "decision-confirm"))
    app = Task041AudioWorkspaceApplication(
        project_root=root,
        project_id="project-1",
        production_control=production,
        token_factory=lambda: next(tokens),
    )
    return app, production


def register_placement(app: Task041AudioWorkspaceApplication):
    state = app.snapshot()
    prepared = app.prepare_placement(
        review_id="review-bgm",
        candidate_id="candidate-bgm",
        timeline_start_frame=100,
        duration_frames=240,
        track_role="BGM",
        gain_db=-6.0,
        expected_production_snapshot_sha256=state["production_snapshot_sha256"],
        expected_audio_snapshot_sha256=state["audio_snapshot_sha256"],
    )
    assert prepared["task026_compile_started"] is False
    assert prepared["resolve_mutation_started"] is False
    return app.apply_placement(confirmation_id=prepared["confirmation_id"])


def test_product_application_persists_audio_review_and_human_accept(tmp_path: Path):
    app, production = application(tmp_path)
    state = register_placement(app)
    assert state["workspace"]["placements"][0]["decision"] == "REVIEW"
    assert state["provider_execution_started"] is False
    assert state["derived_media_write_started"] is False
    assert state["task026_compile_started"] is False
    assert state["resolve_mutation_started"] is False
    assert state["cubase_mutation_started"] is False

    prepared = app.prepare_placement_decision(
        review_id="review-bgm",
        decision="ACCEPT",
        expected_production_snapshot_sha256=state["production_snapshot_sha256"],
        expected_audio_snapshot_sha256=state["audio_snapshot_sha256"],
    )
    accepted = app.apply_placement_decision(confirmation_id=prepared["confirmation_id"])
    assert accepted["workspace"]["placements"][0]["decision"] == "ACCEPT"

    reopened = Task041AudioWorkspaceApplication(
        project_root=tmp_path,
        project_id="project-1",
        production_control=production,
    ).snapshot()
    assert reopened["workspace"]["placements"][0]["decision"] == "ACCEPT"
    assert reopened["available_audio_candidates"][0]["placement_registered"] is True


def test_placement_confirmation_fails_closed_when_production_changes(tmp_path: Path):
    app, _production = application(tmp_path)
    state = app.snapshot()
    prepared = app.prepare_placement(
        review_id="review-bgm",
        candidate_id="candidate-bgm",
        timeline_start_frame=100,
        duration_frames=240,
        track_role="BGM",
        gain_db=None,
        expected_production_snapshot_sha256=state["production_snapshot_sha256"],
        expected_audio_snapshot_sha256=state["audio_snapshot_sha256"],
    )
    path = tmp_path / "production-control.json"
    registry = ProductionControlSnapshotStore.load(path)
    old_sha = ProductionControlSnapshotStore.snapshot(registry)["snapshot_sha256"]
    registry.add_slot(SceneAssetSlot("slot-se", "project-1", "scene-1", SlotKind.SE, False))
    ProductionControlSnapshotStore.save(path, registry, expected_previous_snapshot_sha256=old_sha)

    with pytest.raises(ProductError) as exc:
        app.apply_placement(confirmation_id=prepared["confirmation_id"])
    assert exc.value.code == "ERR_AUDIO_WORKSPACE_SNAPSHOT_CONFLICT"
    assert not (tmp_path / "audio-workspace.json").exists()


def test_audio_role_and_locked_accept_boundaries_are_fail_closed(tmp_path: Path):
    app, _production = application(tmp_path, locked=False)
    state = app.snapshot()
    with pytest.raises(ProductError) as exc:
        app.prepare_placement(
            review_id="review-wrong",
            candidate_id="candidate-bgm",
            timeline_start_frame=0,
            duration_frames=100,
            track_role="SE",
            gain_db=None,
            expected_production_snapshot_sha256=state["production_snapshot_sha256"],
            expected_audio_snapshot_sha256=state["audio_snapshot_sha256"],
        )
    assert exc.value.code == "ERR_AUDIO_WORKSPACE_SLOT_ROLE"

    state = register_placement(app)
    with pytest.raises(ProductError) as exc:
        app.prepare_placement_decision(
            review_id="review-bgm",
            decision="ACCEPT",
            expected_production_snapshot_sha256=state["production_snapshot_sha256"],
            expected_audio_snapshot_sha256=state["audio_snapshot_sha256"],
        )
    assert exc.value.code == "ERR_AUDIO_WORKSPACE_ACCEPT_REQUIRES_LOCKED_CANDIDATE"


def test_concurrent_audio_writer_cannot_overwrite_first_placement(tmp_path: Path):
    production = persisted_production(tmp_path)
    first = Task041AudioWorkspaceApplication(
        project_root=tmp_path,
        project_id="project-1",
        production_control=production,
        token_factory=lambda: "first-confirm",
    )
    second = Task041AudioWorkspaceApplication(
        project_root=tmp_path,
        project_id="project-1",
        production_control=production,
        token_factory=lambda: "second-confirm",
    )
    state = first.snapshot()
    common = {
        "candidate_id": "candidate-bgm",
        "timeline_start_frame": 10,
        "duration_frames": 100,
        "track_role": "BGM",
        "gain_db": None,
        "expected_production_snapshot_sha256": state["production_snapshot_sha256"],
        "expected_audio_snapshot_sha256": state["audio_snapshot_sha256"],
    }
    first_prepared = first.prepare_placement(review_id="review-first", **common)
    second_prepared = second.prepare_placement(review_id="review-second", **common)
    first.apply_placement(confirmation_id=first_prepared["confirmation_id"])
    with pytest.raises(ProductError) as exc:
        second.apply_placement(confirmation_id=second_prepared["confirmation_id"])
    assert exc.value.code == "ERR_AUDIO_WORKSPACE_SNAPSHOT_CONFLICT"
    reopened = first.snapshot()
    assert [row["review_id"] for row in reopened["workspace"]["placements"]] == ["review-first"]
