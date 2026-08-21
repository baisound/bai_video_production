from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.export_queue import (
    ExportAuthorityClass,
    ExportOutputContract,
    ExportPreparation,
    ExportPreset,
)
from ai_video_production.export_queue_application import ExportQueueApplication
from ai_video_production.errors import ProductError
from ai_video_production.final_review_application import FinalReviewApprovalApplication
from ai_video_production.final_review_gate import (
    FinalReviewExternalGateReceipt,
    FinalReviewGateId,
    FinalReviewGateState,
)
from ai_video_production.interactive_timeline import InteractiveTimeline
from ai_video_production.interactive_timeline_application import Task044TimelineEditApplication
from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.task044_nle_shell import Task044NleShellController
from ai_video_production.task044_edit_persistence_receipt import Task044EditPersistenceReceipt
from ai_video_production.task036_shell_ui import Task036ShellBridge
from ai_video_production.timebase import FrameRate


def h(char: str) -> str:
    return "sha256:" + char * 64


def gates() -> tuple[FinalReviewExternalGateReceipt, ...]:
    owners = {
        FinalReviewGateId.AUDIO_COMPLETION: "DEVELOPER2",
        FinalReviewGateId.EDIT_PERSISTENCE: "TASK-044",
        FinalReviewGateId.PRIVACY: "TASK-016",
        FinalReviewGateId.RESOURCE: "TASK-020",
        FinalReviewGateId.RIGHTS_LICENSE: "TASK-003/027",
    }
    return tuple(
        FinalReviewExternalGateReceipt(
            gate_id=gate_id,
            source_authority_owner=owners[gate_id],
            project_id="project-1",
            timeline_sha256=h("4"),
            source_receipt_id=f"source-{index}",
            source_receipt_sha256=h(str(index)),
            state=FinalReviewGateState.PASS,
            evaluated_at="2026-08-17T06:00:00.000Z",
            current_valid=True,
            invalidation_epoch=0,
        )
        for index, gate_id in enumerate(FinalReviewGateId, 5)
    )


def bind_ready_sources(monkeypatch: pytest.MonkeyPatch, bridge: Task036ShellBridge) -> None:
    monkeypatch.setattr(bridge, "production_snapshot", lambda args=None: {
        "available": True, "project_id": "project-1", "snapshot_sha256": h("1"),
        "slots": [{"slot_id": "slot-1", "required": True, "status": "LOCKED", "stale_state": "CURRENT"}],
    })
    monkeypatch.setattr(bridge, "audit_snapshot", lambda args=None: {
        "available": True, "project_id": "project-1",
        "production_snapshot_sha256": h("1"), "audit_snapshot_sha256": h("2"),
        "recovery": {"required": False}, "workspace": {"candidates": []},
    })
    monkeypatch.setattr(bridge, "visual_generation_handoff_snapshot", lambda args=None: {
        "available": True, "project_id": "project-1",
        "source_snapshots": {"production": h("1")}, "projection_sha256": h("3"),
        "all_required_visual_slots_adopted": True, "required_blocker_count": 0,
    })
    monkeypatch.setattr(bridge, "interactive_timeline_snapshot", lambda args=None: {
        "available": True, "projected_timeline_sha256": h("4"),
        "project_manifest_sha256": h("a"),
    })
    monkeypatch.setattr(bridge, "export_queue_snapshot", lambda args=None: {
        "available": True, "rows": [],
    })


def app(root: Path) -> FinalReviewApprovalApplication:
    return FinalReviewApprovalApplication(
        project_root=root,
        project_id="project-1",
        token_factory=lambda: "confirm-final-1",
        clock=lambda: "2026-08-17T06:30:00.000Z",
    )


def test_shell_final_review_export_cancel_rejects_malformed_and_unbound_without_effect() -> None:
    bridge = Task036ShellBridge(ShellApplicationService(product_version="0.21.0"))
    snapshot = bridge.final_review_export_snapshot({})
    assert snapshot["state"] == "PRIVATE_EXPORT_PREPARATION_UNBOUND"
    assert snapshot["export_job_created"] is False
    assert snapshot["side_effect_started_by_this_call"] is False
    for malformed in (None, {}, {"expected_readiness_projection_sha256": "a"}):
        with pytest.raises(ProductError, match="preparation request is invalid"):
            bridge.final_review_export_prepare(malformed)
    for malformed in (None, {}, {"confirmation_id": 1}, {"confirmation_id": "one", "extra": "no"}):
        with pytest.raises(ProductError, match="apply request is invalid"):
            bridge.final_review_export_apply(malformed)
    for malformed in (None, {}, {"confirmation_id": 1}, {"confirmation_id": "one", "extra": "no"}):
        with pytest.raises(ProductError, match="cancellation request is invalid"):
            bridge.final_review_export_cancel(malformed)
    with pytest.raises(ProductError, match="not bound"):
        bridge.final_review_export_prepare({
            "expected_readiness_projection_sha256": "readiness",
            "expected_approval_snapshot_sha256": "approval",
            "expected_preparation_sha256": "preparation",
        })
    with pytest.raises(ProductError, match="not bound"):
        bridge.final_review_export_apply({"confirmation_id": "confirmation-1"})
    with pytest.raises(ProductError, match="not bound"):
        bridge.final_review_export_cancel({"confirmation_id": "confirmation-1"})

    calls: list[str] = []

    class CancelOnly:
        def cancel_enqueue(self, *, confirmation_id: str) -> dict[str, object]:
            calls.append(confirmation_id)
            return {
                "confirmation_id": confirmation_id,
                "cancelled": True,
                "export_job_created": False,
                "side_effect_started_by_this_call": False,
                "host_output_path_persisted": False,
            }

    bridge._final_review_export_application = CancelOnly()  # type: ignore[assignment]
    result = bridge.final_review_export_cancel({"confirmation_id": "confirmation-1"})
    assert calls == ["confirmation-1"]
    assert result["cancelled"] is True
    assert result["export_job_created"] is False


def test_shell_binds_exact_external_gates_and_applies_one_current_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        final_review_application=app(tmp_path),
        final_review_external_gate_provider=gates,
    )
    bind_ready_sources(monkeypatch, bridge)
    initial = bridge.final_review_snapshot({})
    assert initial["available"] is True
    assert initial["readiness"]["state"] == "READY_FOR_TYPED_FINAL_REVIEW"
    assert [row["state"] for row in initial["readiness"]["external_gates"]] == ["PASS"] * 5
    assert initial["approval"]["state"] == "NO_APPROVAL"
    prepared = bridge.final_review_prepare({
        "expected_readiness_projection_sha256": initial["readiness"]["projection_sha256"],
        "expected_approval_snapshot_sha256": initial["approval"]["snapshot_sha256"],
    })
    assert prepared["approval_persisted"] is False
    assert prepared["export_job_created"] is False
    result = bridge.final_review_apply({
        "confirmation_id": prepared["confirmation_id"],
        "approved_by": "owner-1",
    })
    assert result["approval_revision"] == 1
    assert result["export_job_created"] is False
    assert result["render_or_publish_started"] is False
    current = bridge.final_review_snapshot({})
    assert current["approval"]["state"] == "APPROVED_CURRENT"
    assert current["approval"]["approval_current"] is True


def test_shell_never_infers_missing_gate_or_unbound_approval_application(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        final_review_application=app(tmp_path),
        final_review_external_gate_provider=lambda: gates()[:-1],
    )
    bind_ready_sources(monkeypatch, bridge)
    snapshot = bridge.final_review_snapshot({})
    assert snapshot["readiness"]["state"] == "BLOCKED_EXTERNAL_GATES"
    with pytest.raises(ProductError, match="not approvable"):
        bridge.final_review_prepare({
            "expected_readiness_projection_sha256": snapshot["readiness"]["projection_sha256"],
            "expected_approval_snapshot_sha256": snapshot["approval"]["snapshot_sha256"],
        })

    unbound = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        final_review_external_gate_provider=gates,
    )
    bind_ready_sources(monkeypatch, unbound)
    unbound_snapshot = unbound.final_review_snapshot({})
    assert unbound_snapshot["approval"]["state"] == "APPROVAL_APPLICATION_UNBOUND"
    with pytest.raises(ProductError, match="not bound"):
        unbound.final_review_prepare({
            "expected_readiness_projection_sha256": unbound_snapshot["readiness"]["projection_sha256"],
            "expected_approval_snapshot_sha256": h("f"),
        })


def test_gate_provider_is_rechecked_and_revocation_invalidates_pending_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = list(gates())
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        final_review_application=app(tmp_path),
        final_review_external_gate_provider=lambda: tuple(current),
    )
    bind_ready_sources(monkeypatch, bridge)
    initial = bridge.final_review_snapshot({})
    prepared = bridge.final_review_prepare({
        "expected_readiness_projection_sha256": initial["readiness"]["projection_sha256"],
        "expected_approval_snapshot_sha256": initial["approval"]["snapshot_sha256"],
    })
    old = current[0]
    current[0] = FinalReviewExternalGateReceipt(
        gate_id=old.gate_id,
        source_authority_owner=old.source_authority_owner,
        project_id=old.project_id,
        timeline_sha256=old.timeline_sha256,
        source_receipt_id=old.source_receipt_id,
        source_receipt_sha256=old.source_receipt_sha256,
        state=FinalReviewGateState.REVOKED,
        evaluated_at="2026-08-17T06:31:00.000Z",
        current_valid=False,
        invalidation_epoch=1,
    )
    with pytest.raises(ProductError, match="changed after confirmation"):
        bridge.final_review_apply({
            "confirmation_id": prepared["confirmation_id"],
            "approved_by": "owner-1",
        })
    refreshed = bridge.final_review_snapshot({})
    assert refreshed["readiness"]["state"] == "BLOCKED_EXTERNAL_GATES"
    assert refreshed["readiness"]["external_gates"][0]["state"] == "REVOKED"


def test_shell_rejects_raw_or_duplicate_external_gate_injection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        final_review_external_gate_provider=lambda: (gates()[0].to_dict(),),  # type: ignore[return-value]
    )
    bind_ready_sources(monkeypatch, raw)
    with pytest.raises(ProductError, match="invalid receipts"):
        raw.final_review_readiness_snapshot({})
    duplicate = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        final_review_external_gate_provider=lambda: (gates()[0], gates()[0]),
    )
    bind_ready_sources(monkeypatch, duplicate)
    with pytest.raises(ProductError, match="invalid receipts"):
        duplicate.final_review_readiness_snapshot({})


def test_shell_uses_canonical_task044_receipt_and_rejects_edit_substitution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = Task044EditPersistenceReceipt(
        receipt_id="task044-edit-persistence-r1", project_id="project-1",
        timeline_sha256=h("4"), project_manifest_sha256=h("b"),
        edit_snapshot_sha256=h("c"), snapshot_version="1.0.0",
        history_id="timeline-edit:project-1", current_revision=1,
        current_revision_sha256=h("d"),
        evaluated_at="2026-08-17T06:00:00.000Z",
    )
    external = tuple(
        row for row in gates()
        if row.gate_id is not FinalReviewGateId.EDIT_PERSISTENCE
    )
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        final_review_external_gate_provider=lambda: external,
        final_review_edit_persistence_provider=lambda: source,
    )
    bind_ready_sources(monkeypatch, bridge)
    readiness = bridge.final_review_readiness_snapshot({})
    edit = next(
        row for row in readiness["external_gates"]
        if row["gate_id"] == "EDIT_PERSISTENCE"
    )
    assert edit["state"] == "PASS"
    assert readiness["state"] == "READY_FOR_TYPED_FINAL_REVIEW"

    substituted = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        final_review_external_gate_provider=gates,
        final_review_edit_persistence_provider=lambda: source,
    )
    bind_ready_sources(monkeypatch, substituted)
    with pytest.raises(ProductError) as exc:
        substituted.final_review_readiness_snapshot({})
    assert exc.value.code == "ERR_FINAL_REVIEW_EDIT_PERSISTENCE_AUTHORITY_SUBSTITUTION"


def test_shell_final_review_to_actual_task044_export_queue_is_exact_and_stale_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = ProductProjectManifest.create(
        project_id="project-1", project_revision=1, product_version="0.21.0",
        timebase=ProjectTimebase(30, 1), child_bindings=(),
        created_at="2026-08-17T06:00:00.000Z", updated_at="2026-08-17T06:00:00.000Z",
    )
    ProductProjectManifestStore.save(tmp_path, manifest)
    approvals = FinalReviewApprovalApplication(
        project_root=tmp_path, project_id="project-1",
        token_factory=iter(("approval-confirmation",)).__next__,
        clock=lambda: "2026-08-17T06:30:00.000Z",
    )
    timeline = InteractiveTimeline("project-1", "timeline-1", FrameRate(30), 30, (), ())
    queue = ExportQueueApplication(project_root=tmp_path, project_id="project-1")
    controller = Task044NleShellController(
        timeline=timeline,
        edit_application=Task044TimelineEditApplication(project_root=tmp_path, project_id="project-1"),
        export_application=queue,
    )
    provider_calls = 0

    def export_preparation(receipt):
        nonlocal provider_calls
        provider_calls += 1
        return ExportPreparation(
            project_id="project-1",
            project_manifest_sha256=manifest.project_manifest_sha256,
            product_version=manifest.product_version,
            timeline_plan_id="timeline-1",
            timeline_revision=1,
            timeline_sha256=timeline.timeline_sha256,
            edit_plan_sha256=h("c"),
            assembly_plan_sha256=h("d"),
            final_approval=receipt,
            preset=ExportPreset(
                "preset-master", "1.0.0",
                ExportOutputContract(1920, 1080, 30, 1, 48000, 2, "mp4", "h264", "pcm"),
            ),
            output_target_identity="export:master",
            authority_class=ExportAuthorityClass.LOCAL_PACKAGE,
        )

    owners = {
        FinalReviewGateId.AUDIO_COMPLETION: "DEVELOPER2",
        FinalReviewGateId.EDIT_PERSISTENCE: "TASK-044",
        FinalReviewGateId.PRIVACY: "TASK-016",
        FinalReviewGateId.RESOURCE: "TASK-020",
        FinalReviewGateId.RIGHTS_LICENSE: "TASK-003/027",
    }

    def exact_gates():
        return tuple(
            FinalReviewExternalGateReceipt(
                gate_id=gate_id,
                source_authority_owner=owners[gate_id],
                project_id="project-1",
                timeline_sha256=timeline.timeline_sha256,
                source_receipt_id=f"source-{index}",
                source_receipt_sha256=h(str(index)),
                state=FinalReviewGateState.PASS,
                evaluated_at="2026-08-17T06:00:00.000Z",
                current_valid=True,
                invalidation_epoch=0,
            )
            for index, gate_id in enumerate(FinalReviewGateId, 5)
        )

    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        nle_controller=controller,
        final_review_application=approvals,
        final_review_external_gate_provider=exact_gates,
        final_review_export_preparation_provider=export_preparation,
    )
    monkeypatch.setattr(bridge, "production_snapshot", lambda args=None: {
        "available": True, "project_id": "project-1", "snapshot_sha256": h("1"),
        "slots": [{"slot_id": "slot-1", "required": True, "status": "LOCKED", "stale_state": "CURRENT"}],
    })
    monkeypatch.setattr(bridge, "audit_snapshot", lambda args=None: {
        "available": True, "project_id": "project-1",
        "production_snapshot_sha256": h("1"), "audit_snapshot_sha256": h("2"),
        "recovery": {"required": False}, "workspace": {"candidates": []},
    })
    monkeypatch.setattr(bridge, "visual_generation_handoff_snapshot", lambda args=None: {
        "available": True, "project_id": "project-1",
        "source_snapshots": {"production": h("1")}, "projection_sha256": h("3"),
        "all_required_visual_slots_adopted": True, "required_blocker_count": 0,
    })

    initial = bridge.final_review_snapshot({})
    assert initial["readiness"]["state"] == "READY_FOR_TYPED_FINAL_REVIEW"
    approval = bridge.final_review_prepare({
        "expected_readiness_projection_sha256": initial["readiness"]["projection_sha256"],
        "expected_approval_snapshot_sha256": initial["approval"]["snapshot_sha256"],
    })
    bridge.final_review_apply({"confirmation_id": approval["confirmation_id"], "approved_by": "owner-1"})
    ready = bridge.final_review_export_snapshot({})
    prepared = bridge.final_review_export_prepare({
        "expected_readiness_projection_sha256": ready["readiness_projection_sha256"],
        "expected_approval_snapshot_sha256": ready["approval_snapshot_sha256"],
        "expected_preparation_sha256": ready["preparation_sha256"],
    })
    queued = bridge.final_review_export_apply({"confirmation_id": prepared["confirmation_id"]})
    rows = bridge.export_queue_snapshot({})["rows"]
    assert len(rows) == 1 and rows[0]["job_id"] == queued["job_id"]
    calls_before_existing = provider_calls
    existing = bridge.final_review_export_snapshot({})
    assert existing["state"] == "EXISTING_EXPORT_JOB"
    assert existing["existing_job_state"] == "QUEUED"
    assert provider_calls == calls_before_existing
    assert existing["side_effect_started_by_this_call"] is False
    assert existing["host_output_path_persisted"] is False
    assert len(queue.jobs_for_final_approval(ready["approval_receipt_sha256"])) == 1
    assert str(tmp_path) not in str(existing)
