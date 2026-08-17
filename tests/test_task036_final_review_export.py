from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.durable_product_job import DurableProductJobStore
from ai_video_production.errors import ProductError
from ai_video_production.export_queue import (
    ExportAuthorityClass,
    ExportOutputContract,
    ExportPreparation,
    ExportPreset,
)
from ai_video_production.export_queue_application import ExportQueueApplication
from ai_video_production.final_review import FinalReviewApprovalReceipt
from ai_video_production.final_review_application import FinalReviewApprovalApplication
from ai_video_production.final_review_export_application import Task036FinalReviewExportApplication
from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


def h(char: str) -> str:
    return "sha256:" + char * 64


def readiness(*, production: str = "2", project_manifest: str | None = None) -> dict[str, object]:
    value: dict[str, object] = {
        "available": True,
        "projection_version": "1.0.0",
        "state": "READY_FOR_TYPED_FINAL_REVIEW",
        "project_id": "project-1",
        "source_snapshots": {
            "production": h(production), "audit": h("3"), "visual_handoff": h("4"),
            "timeline": h("5"), "project_manifest": project_manifest or h("6"),
        },
        "required_slot_count": 1,
        "audit_candidate_count": 0,
        "export_job_count": 0,
        "product_blockers": [],
        "external_gates": [{
            "gate_id": gate, "owner": owner, "state": "PASS", "receipt_sha256": h(char),
        } for gate, owner, char in zip(
            ("AUDIO_COMPLETION", "EDIT_PERSISTENCE", "PRIVACY", "RESOURCE", "RIGHTS_LICENSE"),
            ("DEVELOPER2", "TASK-044", "TASK-016", "TASK-020", "TASK-003/027"),
            "789ab", strict=True,
        )],
        "external_blockers": [],
        "delegated_audio_owner": "DEVELOPER2",
        "final_approval_created": False,
        "export_job_created": False,
        "render_or_publish_started": False,
        "human_decision_authorized": False,
    }
    value["projection_sha256"] = sha256_bytes(canonical_json_bytes({
        key: item for key, item in value.items() if key != "available"
    }))
    return value


def setup(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    manifest = ProductProjectManifest.create(
        project_id="project-1", project_revision=1, product_version="0.21.0",
        timebase=ProjectTimebase(30, 1), child_bindings=(),
        created_at="2026-08-17T07:00:00.000Z", updated_at="2026-08-17T07:00:00.000Z",
    )
    ProductProjectManifestStore.save(root, manifest)
    approvals = FinalReviewApprovalApplication(
        project_root=root, project_id="project-1",
        token_factory=lambda: "approval-confirmation",
        clock=lambda: "2026-08-17T07:01:00.000Z",
    )
    current = readiness(project_manifest=manifest.project_manifest_sha256)
    initial = approvals.snapshot(readiness=current)
    prepared = approvals.prepare_approval(
        readiness=current,
        expected_readiness_projection_sha256=str(current["projection_sha256"]),
        expected_snapshot_sha256=str(initial["snapshot_sha256"]),
    )
    approved = approvals.apply_approval(
        confirmation_id=str(prepared["confirmation_id"]),
        readiness=current,
        approved_by="owner-1",
    )
    receipt = FinalReviewApprovalReceipt.from_dict(approved["receipt"])
    queue = ExportQueueApplication(project_root=root, project_id="project-1")
    return manifest, approvals, receipt, queue, current


def preparation(manifest, receipt, *, target: str = "export:master") -> ExportPreparation:
    return ExportPreparation(
        project_id="project-1",
        project_manifest_sha256=manifest.project_manifest_sha256,
        product_version=manifest.product_version,
        timeline_plan_id="timeline-main",
        timeline_revision=1,
        timeline_sha256=h("5"),
        edit_plan_sha256=h("c"),
        assembly_plan_sha256=h("d"),
        final_approval=receipt,
        preset=ExportPreset(
            "preset-youtube-1080p", "1.0.0",
            ExportOutputContract(1920, 1080, 30, 1, 48000, 2, "mp4", "h264", "pcm"),
        ),
        output_target_identity=target,
        authority_class=ExportAuthorityClass.LOCAL_PACKAGE,
    )


def application(root: Path, *, token: str = "queue-confirmation"):
    manifest, approvals, receipt, queue, current = setup(root)
    selected = [preparation(manifest, receipt)]
    app = Task036FinalReviewExportApplication(
        project_id="project-1",
        final_review_application=approvals,
        export_application_provider=lambda: queue,
        preparation_provider=lambda exact_receipt: selected[0],
        token_factory=lambda: token,
    )
    return app, selected, current, manifest, receipt


def test_snapshot_exposes_only_logical_preparation_and_requires_confirmation(tmp_path: Path) -> None:
    app, _, current, _, _ = application(tmp_path)
    snapshot = app.snapshot(readiness=current)
    assert snapshot["state"] == "READY_FOR_EXPORT_QUEUE_CONFIRMATION"
    assert snapshot["queue_confirmation_ready"] is True
    assert snapshot["export_job_created"] is False
    assert snapshot["dispatch_or_render_started"] is False
    assert snapshot["host_output_path_persisted"] is False
    assert snapshot["preset"]["preset_id"] == "preset-youtube-1080p"
    assert str(tmp_path) not in json.dumps(snapshot)


def test_prepare_apply_creates_exactly_one_queued_job_without_dispatch(tmp_path: Path) -> None:
    app, _, current, _, _ = application(tmp_path)
    snapshot = app.snapshot(readiness=current)
    prepared = app.prepare_enqueue(
        readiness=current,
        expected_readiness_projection_sha256=str(snapshot["readiness_projection_sha256"]),
        expected_approval_snapshot_sha256=str(snapshot["approval_snapshot_sha256"]),
        expected_preparation_sha256=str(snapshot["preparation_sha256"]),
    )
    assert prepared["export_job_created"] is False
    result = app.apply_enqueue(
        confirmation_id=str(prepared["confirmation_id"]), readiness=current,
    )
    assert result["state"] == "QUEUED"
    assert result["export_job_created"] is True
    assert result["dispatch_or_render_started"] is False
    collection = DurableProductJobStore.load(tmp_path)
    assert len(collection.jobs) == 1
    assert collection.jobs[0].state.value == "QUEUED"
    assert app.snapshot(readiness=current)["state"] == "ALREADY_QUEUED"
    with pytest.raises(ProductError, match="missing or consumed"):
        app.apply_enqueue(confirmation_id=str(prepared["confirmation_id"]), readiness=current)


def test_readiness_or_private_preparation_change_invalidates_confirmation(tmp_path: Path) -> None:
    app, selected, current, manifest, receipt = application(tmp_path)
    snapshot = app.snapshot(readiness=current)
    prepared = app.prepare_enqueue(
        readiness=current,
        expected_readiness_projection_sha256=str(snapshot["readiness_projection_sha256"]),
        expected_approval_snapshot_sha256=str(snapshot["approval_snapshot_sha256"]),
        expected_preparation_sha256=str(snapshot["preparation_sha256"]),
    )
    selected[0] = preparation(manifest, receipt, target="export:alternate")
    with pytest.raises(ProductError, match="changed after confirmation"):
        app.apply_enqueue(confirmation_id=str(prepared["confirmation_id"]), readiness=current)

    other, _, other_current, _, _ = application(tmp_path / "other", token="other-confirmation")
    other_snapshot = other.snapshot(readiness=other_current)
    other_prepared = other.prepare_enqueue(
        readiness=other_current,
        expected_readiness_projection_sha256=str(other_snapshot["readiness_projection_sha256"]),
        expected_approval_snapshot_sha256=str(other_snapshot["approval_snapshot_sha256"]),
        expected_preparation_sha256=str(other_snapshot["preparation_sha256"]),
    )
    with pytest.raises(ProductError, match="readiness changed"):
        other.apply_enqueue(
            confirmation_id=str(other_prepared["confirmation_id"]),
            readiness=readiness(production="e"),
        )


def test_stale_or_cross_approval_preparation_fails_closed(tmp_path: Path) -> None:
    manifest, approvals, receipt, queue, current = setup(tmp_path)
    wrong = FinalReviewApprovalReceipt(
        receipt_id="wrong-approval", project_id=receipt.project_id,
        project_manifest_sha256=receipt.project_manifest_sha256,
        timeline_sha256=receipt.timeline_sha256,
        readiness_projection_sha256=receipt.readiness_projection_sha256,
        source_snapshot_sha256s=receipt.source_snapshot_sha256s,
        external_gate_receipt_sha256s=receipt.external_gate_receipt_sha256s,
        approved_by="owner-2", approved_at="2026-08-17T07:02:00.000Z",
    )
    app = Task036FinalReviewExportApplication(
        project_id="project-1", final_review_application=approvals,
        export_application_provider=lambda: queue,
        preparation_provider=lambda _: preparation(manifest, wrong),
    )
    with pytest.raises(ProductError, match="current exact approval"):
        app.snapshot(readiness=current)
    assert not DurableProductJobStore.path(tmp_path).exists()


def test_unbound_queue_is_read_only_unavailable(tmp_path: Path) -> None:
    manifest, approvals, receipt, _, current = setup(tmp_path)
    app = Task036FinalReviewExportApplication(
        project_id="project-1", final_review_application=approvals,
        export_application_provider=lambda: None,
        preparation_provider=lambda _: preparation(manifest, receipt),
    )
    snapshot = app.snapshot(readiness=current)
    assert snapshot["available"] is False
    assert snapshot["state"] == "ERR_FINAL_REVIEW_EXPORT_QUEUE_NOT_BOUND"
    assert snapshot["export_job_created"] is False
