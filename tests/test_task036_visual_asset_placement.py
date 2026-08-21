from __future__ import annotations

import copy
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest

from ai_video_production.assets import (
    AssetRecord,
    AssetType,
    AudioRightsStatus,
    PermissionState,
    RetentionClass,
    RightsStatus,
)
from ai_video_production.errors import ProductError
from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.interactive_timeline import (
    InteractiveTimeline,
    InteractiveTimelineClip,
    TimelineMediaKind,
    TimelineTrack,
    TimelineTrackRole,
)
from ai_video_production.interactive_timeline_application import Task044TimelineEditApplication
from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.project_history import ProjectCommandHistoryStore
from ai_video_production.project_save import ProductProjectSaveCoordinator
from ai_video_production.serialization import sha256_bytes
from ai_video_production.task036_visual_asset_placement import (
    Task036VisualAssetPlacementApplication,
)
from ai_video_production.task036_shell_ui import Task036ShellBridge
from ai_video_production.task044_nle_shell import Task044NleShellController
from ai_video_production.timebase import FrameRate


CREATED = "2026-08-21T00:00:00.000Z"


def h(value: str) -> str:
    return sha256_bytes(value.encode())


def setup_project(root: Path) -> ProductProjectManifest:
    manifest = ProductProjectManifest.create(
        project_id="project-1",
        project_revision=1,
        product_version="0.22.0",
        timebase=ProjectTimebase(30, 1),
        child_bindings=(),
        created_at=CREATED,
        updated_at=CREATED,
    )
    ProductProjectManifestStore.save(root, manifest)
    return manifest


def timeline() -> InteractiveTimeline:
    return InteractiveTimeline(
        "project-1",
        "timeline-1",
        FrameRate(30, 1),
        300,
        (
            TimelineTrack("video-main", 0, TimelineTrackRole.VIDEO, TimelineMediaKind.VIDEO, "Video", True),
            TimelineTrack("overlay-main", 1, TimelineTrackRole.OVERLAY, TimelineMediaKind.VIDEO, "Overlay"),
        ),
        (
            InteractiveTimelineClip(
                "legacy-clip", "video-main", 10, 40, "TASK-007", "segment-1",
                h("legacy"), "Legacy", "APPROVED",
            ),
        ),
    )


class Fixture:
    def __init__(
        self,
        root: Path,
        *,
        save_coordinator: ProductProjectSaveCoordinator | None = None,
    ) -> None:
        self.manifest = setup_project(root)
        self.job_id = generate_id(IdKind.JOB)
        self.asset_id = generate_id(IdKind.ASSET)
        self.execution_id = "execution-image-1"
        self.queue_entry_id = "queue-image-1"
        self.asset = AssetRecord(
            production_job_id=self.job_id,
            asset_type=AssetType.IMAGE,
            logical_uri=f"asset://{self.job_id}/generated/result.png",
            checksum=h("png-bytes"),
            rights_status=RightsStatus.UNKNOWN,
            owner="TASK-027",
            asset_id=self.asset_id,
            retention_class=RetentionClass.STANDARD,
            human_lock=False,
            generation_provenance={
                "kind": "TASK013_COMPLETED_LOCAL_GENERATION",
                "execution_id": self.execution_id,
                "queue_entry_id": self.queue_entry_id,
                "prompt_id": "prompt-1",
                "prompt_version": 1,
                "prompt_sha256": h("prompt"),
                "provider_id": "comfy",
                "model_id": "flux-dev",
                "provider_operation_id": "provider-operation-1",
                "output_sha256": h("png-bytes"),
                "provider_execution_replayed": False,
                "paid_execution_authorized": False,
            },
            commercial_use=PermissionState.UNKNOWN,
            derivative_allowed=PermissionState.UNKNOWN,
            reuse_allowed=PermissionState.UNKNOWN,
            audio_rights_status=AudioRightsStatus.NOT_APPLICABLE,
            source_ref="job://logical-output",
            source_project="project-1",
            publication_restrictions=(
                "HUMAN_RIGHTS_REVIEW_REQUIRED",
                "PUBLICATION_NOT_AUTHORIZED",
            ),
        )
        self.production = {
            "available": True,
            "project_id": "project-1",
            "snapshot_sha256": h("production-1"),
            "slots": [{
                "slot_id": "slot-image-1",
                "project_id": "project-1",
                "scene_id": "scene-1",
                "slot_kind": "START_FRAME",
                "required": True,
                "status": "LOCKED",
                "locked_candidate_id": "candidate-image-1",
                "stale_state": "CURRENT",
                "candidates": [{
                    "candidate_id": "candidate-image-1",
                    "slot_id": "slot-image-1",
                    "asset_id": self.asset_id,
                    "asset_sha256": self.asset.checksum,
                    "candidate_version": 1,
                    "lifecycle_state": "LOCKED",
                    "generation_job_id": self.execution_id,
                }],
            }],
        }
        self.placement: Task036VisualAssetPlacementApplication | None = None
        timeline_app = Task044TimelineEditApplication(
            project_root=root,
            project_id="project-1",
            token_factory=lambda: "confirmation-1",
            save_coordinator=save_coordinator,
            placement_guard_resolver=lambda command: self.placement.commit_guard_for_command(command),
        )

        @contextmanager
        def production_guard(expected_sha: str):
            if self.production["snapshot_sha256"] != expected_sha:
                raise ProductError("ERR_TEST_PRODUCTION_DRIFT", "Production changed")
            yield self.production

        self.placement = Task036VisualAssetPlacementApplication(
            project_id="project-1",
            product_job_id=self.job_id,
            production_snapshot_provider=lambda: self.production,
            production_guard_factory=production_guard,
            asset_provider=lambda asset_id: self.asset if asset_id == self.asset_id else None,
            timeline_application=timeline_app,
        )


def test_insert_is_deterministic_committed_and_projects_current_source(tmp_path: Path) -> None:
    fixture = Fixture(tmp_path)
    base = timeline()
    prepared = fixture.placement.prepare_insert(
        timeline=base,
        candidate_id="candidate-image-1",
        target_track_id="overlay-main",
        start_frame=60,
        end_frame=90,
        command_id="insert-image-1",
        expected_project_manifest_sha256=fixture.manifest.project_manifest_sha256,
        expected_production_snapshot_sha256=fixture.production["snapshot_sha256"],
    )
    command = prepared["command"]
    assert command["after_clip"]["clip_id"].startswith("visual-")
    assert len(command["after_clip"]["clip_id"]) == 71
    assert command["after_clip"]["label"] == "scene-1 / START_FRAME"
    assert command["after_clip"]["state"] == "PLACED_LOCKED_ASSET"
    result = fixture.placement.apply(confirmation_id=prepared["confirmation_id"], timeline=base)
    assert result["timeline_revision"] == 1

    snapshot = fixture.placement.snapshot(timeline=base)
    assert snapshot["placement_count"] == 1
    assert snapshot["stale_placement_count"] == 0
    assert snapshot["placements"][0]["state"] == "CURRENT"
    assert snapshot["rights_approved"] is False
    assert snapshot["publication_authorized"] is False


def test_replace_preserves_clip_identity_track_and_range(tmp_path: Path) -> None:
    fixture = Fixture(tmp_path)
    base = timeline()
    prepared = fixture.placement.prepare_replace(
        timeline=base,
        candidate_id="candidate-image-1",
        target_clip_id="legacy-clip",
        command_id="replace-image-1",
        expected_project_manifest_sha256=fixture.manifest.project_manifest_sha256,
        expected_production_snapshot_sha256=fixture.production["snapshot_sha256"],
    )
    before = prepared["command"]["before_clip"]
    after = prepared["command"]["after_clip"]
    assert (after["clip_id"], after["track_id"], after["start_frame"], after["end_frame"]) == (
        before["clip_id"], before["track_id"], before["start_frame"], before["end_frame"],
    )
    fixture.placement.apply(confirmation_id=prepared["confirmation_id"], timeline=base)
    snapshot = fixture.placement.snapshot(timeline=base)
    assert snapshot["placements"][0]["clip_id"] == "legacy-clip"


def test_production_drift_after_prepare_is_rejected_before_timeline_commit(tmp_path: Path) -> None:
    fixture = Fixture(tmp_path)
    base = timeline()
    prepared = fixture.placement.prepare_insert(
        timeline=base,
        candidate_id="candidate-image-1",
        target_track_id="video-main",
        start_frame=60,
        end_frame=90,
        command_id="insert-drift",
        expected_project_manifest_sha256=fixture.manifest.project_manifest_sha256,
        expected_production_snapshot_sha256=fixture.production["snapshot_sha256"],
    )
    fixture.production["snapshot_sha256"] = h("production-2")
    fixture.production["slots"][0]["status"] = "STALE"
    fixture.production["slots"][0]["stale_state"] = "STALE"
    with pytest.raises(ProductError):
        fixture.placement.apply(confirmation_id=prepared["confirmation_id"], timeline=base)
    assert ProductProjectManifestStore.load(tmp_path).project_revision == 1
    assert not fixture.placement._timeline_application.snapshot_path.exists()


def test_project_save_finalize_rechecks_current_visual_source(tmp_path: Path) -> None:
    def fail_after_manifest(stage: str, _root: Path) -> None:
        if stage == "after_manifest_commit":
            raise OSError("interrupted after Manifest commit")

    fixture = Fixture(
        tmp_path,
        save_coordinator=ProductProjectSaveCoordinator(failure_injector=fail_after_manifest),
    )
    original_production = copy.deepcopy(fixture.production)
    base = timeline()
    prepared = fixture.placement.prepare_insert(
        timeline=base,
        candidate_id="candidate-image-1",
        target_track_id="overlay-main",
        start_frame=60,
        end_frame=90,
        command_id="insert-recovery-guard",
        expected_project_manifest_sha256=fixture.manifest.project_manifest_sha256,
        expected_production_snapshot_sha256=fixture.production["snapshot_sha256"],
    )
    with pytest.raises(OSError):
        fixture.placement.apply(confirmation_id=prepared["confirmation_id"], timeline=base)
    recovery = fixture.placement.snapshot(timeline=base)["project_save_recovery"]
    assert recovery["required"] is True
    assert recovery["available_actions"] == ["FINALIZE"]

    fixture.production["snapshot_sha256"] = h("production-drift-during-recovery")
    fixture.production["slots"][0]["status"] = "STALE"
    fixture.production["slots"][0]["stale_state"] = "STALE"
    with pytest.raises(ProductError):
        fixture.placement.recover_project_save(
            transaction_id=recovery["transaction_id"],
            action="FINALIZE",
        )
    assert not ProjectCommandHistoryStore.path(tmp_path).exists()

    fixture.production = original_production
    recovered = fixture.placement.recover_project_save(
        transaction_id=recovery["transaction_id"],
        action="FINALIZE",
    )
    assert recovered["project_history_record_count"] == 1
    assert fixture.placement.snapshot(timeline=base)["project_save_recovery"]["required"] is False


def test_insert_undo_redo_reuses_exact_binding_and_rechecks_source(tmp_path: Path) -> None:
    fixture = Fixture(tmp_path)
    base = timeline()
    prepared = fixture.placement.prepare_insert(
        timeline=base,
        candidate_id="candidate-image-1",
        target_track_id="overlay-main",
        start_frame=60,
        end_frame=90,
        command_id="insert-undo-redo",
        expected_project_manifest_sha256=fixture.manifest.project_manifest_sha256,
        expected_production_snapshot_sha256=fixture.production["snapshot_sha256"],
    )
    fixture.placement.apply(confirmation_id=prepared["confirmation_id"], timeline=base)
    first_manifest = ProductProjectManifestStore.load(tmp_path)
    undo = fixture.placement._timeline_application.prepare_undo(
        timeline=base,
        command_id="undo-insert",
        expected_project_manifest_sha256=first_manifest.project_manifest_sha256,
    )
    fixture.placement.apply(confirmation_id=undo["confirmation_id"], timeline=base)
    assert fixture.placement.snapshot(timeline=base)["placement_count"] == 0

    second_manifest = ProductProjectManifestStore.load(tmp_path)
    redo = fixture.placement._timeline_application.prepare_redo(
        timeline=base,
        command_id="redo-insert",
        expected_project_manifest_sha256=second_manifest.project_manifest_sha256,
    )
    fixture.placement.apply(confirmation_id=redo["confirmation_id"], timeline=base)
    snapshot = fixture.placement.snapshot(timeline=base)
    assert snapshot["placement_count"] == 1
    assert snapshot["placements"][0]["state"] == "CURRENT"


def test_later_locked_candidate_does_not_make_old_placement_current(tmp_path: Path) -> None:
    fixture = Fixture(tmp_path)
    base = timeline()
    prepared = fixture.placement.prepare_insert(
        timeline=base,
        candidate_id="candidate-image-1",
        target_track_id="video-main",
        start_frame=60,
        end_frame=90,
        command_id="insert-old-source",
        expected_project_manifest_sha256=fixture.manifest.project_manifest_sha256,
        expected_production_snapshot_sha256=fixture.production["snapshot_sha256"],
    )
    fixture.placement.apply(confirmation_id=prepared["confirmation_id"], timeline=base)
    slot = fixture.production["slots"][0]
    slot["locked_candidate_id"] = "candidate-new"
    slot["candidates"][0]["lifecycle_state"] = "STALE"
    slot["candidates"].append({
        "candidate_id": "candidate-new",
        "slot_id": slot["slot_id"],
        "asset_id": generate_id(IdKind.ASSET),
        "asset_sha256": h("new-asset"),
        "candidate_version": 2,
        "lifecycle_state": "LOCKED",
        "generation_job_id": "execution-image-2",
    })
    fixture.production["snapshot_sha256"] = h("production-new-lock")
    snapshot = fixture.placement.snapshot(timeline=base)
    assert snapshot["stale_placement_count"] == 1
    assert snapshot["placements"][0]["state"] == "STALE"


def test_public_shell_insert_reads_back_same_canonical_clip(tmp_path: Path) -> None:
    fixture = Fixture(tmp_path)
    base = timeline()
    controller = Task044NleShellController(
        timeline=base,
        edit_application=fixture.placement._timeline_application,
        visual_asset_placement=fixture.placement,
    )
    service = ShellApplicationService(product_version="0.22.0")
    service.open_project_context(project_id="project-1", display_name="Project 1")
    bridge = Task036ShellBridge(service, nle_controller=controller)
    prepared = bridge.visual_asset_placement_prepare_insert({
        "candidate_id": "candidate-image-1",
        "target_track_id": "overlay-main",
        "start_frame": 60,
        "end_frame": 90,
        "command_id": "shell-insert",
        "expected_project_manifest_sha256": fixture.manifest.project_manifest_sha256,
        "expected_production_snapshot_sha256": fixture.production["snapshot_sha256"],
    })
    bridge.visual_asset_placement_apply({"confirmation_id": prepared["confirmation_id"]})
    timeline_snapshot = bridge.interactive_timeline_snapshot({"clip_offset": 0, "max_clips": 500})
    placed = next(row for row in timeline_snapshot["projection"]["clips"] if row["clip_id"].startswith("visual-"))
    assert placed["source_ref"] == fixture.asset.asset_id
    assert placed["source_sha256"] == fixture.asset.checksum
    assert placed["review_candidate_id"] == "candidate-image-1"
    placement_snapshot = bridge.visual_asset_placement_snapshot({})
    assert placement_snapshot["placements"][0]["clip_id"] == placed["clip_id"]
    assert placement_snapshot["provider_execution_started"] is False
    assert placement_snapshot["publication_authorized"] is False


@pytest.mark.parametrize(
    "mutate",
    [
        lambda fixture: setattr(fixture, "asset", replace(fixture.asset, rights_status=RightsStatus.OWNED)),
        lambda fixture: setattr(fixture, "asset", replace(fixture.asset, reuse_allowed=PermissionState.ALLOWED)),
        lambda fixture: setattr(fixture, "asset", replace(
            fixture.asset, publication_restrictions=("PUBLICATION_NOT_AUTHORIZED",),
        )),
        lambda fixture: fixture.asset.generation_provenance.update(extra="unexpected"),
        lambda fixture: fixture.production["slots"][0].update(status="STALE", stale_state="STALE"),
    ],
)
def test_non_exact_locked_generated_image_profile_is_ineligible(
    tmp_path: Path, mutate
) -> None:
    fixture = Fixture(tmp_path)
    mutate(fixture)
    with pytest.raises(ProductError):
        fixture.placement.prepare_insert(
            timeline=timeline(),
            candidate_id="candidate-image-1",
            target_track_id="video-main",
            start_frame=60,
            end_frame=90,
            command_id="insert-rejected",
            expected_project_manifest_sha256=fixture.manifest.project_manifest_sha256,
            expected_production_snapshot_sha256=fixture.production["snapshot_sha256"],
        )
