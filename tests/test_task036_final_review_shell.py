from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.errors import ProductError
from ai_video_production.final_review_application import FinalReviewApprovalApplication
from ai_video_production.final_review_gate import (
    FinalReviewExternalGateReceipt,
    FinalReviewGateId,
    FinalReviewGateState,
)
from ai_video_production.task036_shell_ui import Task036ShellBridge


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
