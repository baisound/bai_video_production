from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.final_review import FinalReviewApprovalReceipt
from ai_video_production.final_review_application import (
    FinalReviewApprovalApplication,
    _with_hash,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


def h(char: str) -> str:
    return "sha256:" + char * 64


def readiness(*, production: str = "2") -> dict[str, object]:
    value: dict[str, object] = {
        "available": True,
        "projection_version": "1.0.0",
        "state": "READY_FOR_TYPED_FINAL_REVIEW",
        "project_id": "project-1",
        "source_snapshots": {
            "production": h(production), "audit": h("3"), "visual_handoff": h("4"),
            "timeline": h("5"), "project_manifest": h("6"),
        },
        "required_slot_count": 1,
        "audit_candidate_count": 1,
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


def application(root: Path, tokens: list[str] | None = None, *, failure=None) -> FinalReviewApprovalApplication:
    values = iter(tokens or ["confirm-1", "confirm-2", "confirm-3"])
    return FinalReviewApprovalApplication(
        project_root=root,
        project_id="project-1",
        token_factory=lambda: next(values),
        clock=lambda: "2026-08-17T03:00:00.000Z",
        failure_injector=failure,
    )


def approve(app: FinalReviewApprovalApplication, value: dict[str, object]) -> dict[str, object]:
    snapshot = app.snapshot(readiness=value)
    prepared = app.prepare_approval(
        readiness=value,
        expected_readiness_projection_sha256=value["projection_sha256"],
        expected_snapshot_sha256=snapshot["snapshot_sha256"],
    )
    assert prepared["approval_persisted"] is False
    return app.apply_approval(
        confirmation_id=prepared["confirmation_id"], readiness=value, approved_by="owner-1",
    )


def test_append_only_approval_is_deterministic_current_and_effect_free(tmp_path: Path) -> None:
    app = application(tmp_path)
    initial = app.snapshot(readiness=readiness())
    assert initial["state"] == "NO_APPROVAL"
    result = approve(app, readiness())
    assert result["approval_revision"] == 1
    assert result["export_job_created"] is False
    assert result["render_or_publish_started"] is False

    restored = application(tmp_path).snapshot(readiness=readiness())
    assert restored["state"] == "APPROVED_CURRENT"
    assert restored["approval_current"] is True
    assert restored["latest_receipt"] == result["receipt"]
    assert restored["revision"] == 1


def test_confirmation_is_single_use_and_exact_readiness_is_not_reapproved(tmp_path: Path) -> None:
    app = application(tmp_path)
    current = readiness()
    snapshot = app.snapshot(readiness=current)
    prepared = app.prepare_approval(
        readiness=current,
        expected_readiness_projection_sha256=current["projection_sha256"],
        expected_snapshot_sha256=snapshot["snapshot_sha256"],
    )
    app.apply_approval(confirmation_id=prepared["confirmation_id"], readiness=current, approved_by="owner-1")
    with pytest.raises(ProductError, match="missing or consumed"):
        app.apply_approval(confirmation_id=prepared["confirmation_id"], readiness=current, approved_by="owner-1")
    with pytest.raises(ProductError, match="already approved"):
        app.prepare_approval(
            readiness=current,
            expected_readiness_projection_sha256=current["projection_sha256"],
            expected_snapshot_sha256=app.snapshot(readiness=current)["snapshot_sha256"],
        )


def test_changed_readiness_and_snapshot_cas_conflict_fail_closed(tmp_path: Path) -> None:
    first = application(tmp_path, ["first", "first-retry"])
    second = application(tmp_path, ["second"])
    current = readiness()
    empty_sha = first.snapshot(readiness=current)["snapshot_sha256"]
    pending = first.prepare_approval(
        readiness=current,
        expected_readiness_projection_sha256=current["projection_sha256"],
        expected_snapshot_sha256=empty_sha,
    )
    changed = readiness(production="c")
    with pytest.raises(ProductError, match="changed after confirmation"):
        first.apply_approval(confirmation_id=pending["confirmation_id"], readiness=changed, approved_by="owner-1")

    pending = first.prepare_approval(
        readiness=current,
        expected_readiness_projection_sha256=current["projection_sha256"],
        expected_snapshot_sha256=empty_sha,
    )
    approve(second, changed)
    with pytest.raises(ProductError, match="history changed after confirmation"):
        first.apply_approval(confirmation_id=pending["confirmation_id"], readiness=current, approved_by="owner-1")


def test_latest_approval_becomes_stale_when_current_sources_change(tmp_path: Path) -> None:
    app = application(tmp_path)
    approve(app, readiness())
    result = app.snapshot(readiness=readiness(production="c"))
    assert result["state"] == "APPROVAL_STALE"
    assert result["approval_current"] is False

    blocked = readiness()
    blocked["state"] = "BLOCKED_EXTERNAL_GATES"
    blocked["external_blockers"] = [{"code": "AUDIO_COMPLETION_STALE", "owner": "DEVELOPER2", "identity": None}]
    blocked["projection_sha256"] = sha256_bytes(canonical_json_bytes({
        key: item for key, item in blocked.items() if key not in {"available", "projection_sha256"}
    }))
    result = app.snapshot(readiness=blocked)
    assert result["state"] == "APPROVAL_STALE"
    assert result["approval_current"] is False


def test_tamper_symlink_and_atomic_failure_preserve_previous_state(tmp_path: Path) -> None:
    app = application(tmp_path)
    approve(app, readiness())
    original = app.snapshot_path.read_bytes()
    document = json.loads(original)
    document["approvals"][0]["receipt"]["approved_by"] = "attacker"
    app.snapshot_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProductError, match="checksum"):
        app.snapshot()
    app.snapshot_path.write_bytes(original)

    link_root = tmp_path / "link-root"
    try:
        link_root.symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable")
    with pytest.raises(ProductError, match="existing regular directory"):
        application(link_root)


def test_capacity_plus_one_rejects_without_overwriting_snapshot(tmp_path: Path) -> None:
    app = application(tmp_path, ["overflow"])
    rows = []
    for revision in range(1, 257):
        value = readiness(production=f"{revision:064x}"[-1])
        value["source_snapshots"]["production"] = "sha256:" + f"{revision:064x}"
        value["projection_sha256"] = sha256_bytes(canonical_json_bytes({
            key: item for key, item in value.items()
            if key not in {"available", "projection_sha256"}
        }))
        receipt = FinalReviewApprovalReceipt.from_readiness(
            value,
            receipt_id=f"final-{revision}",
            approved_by="owner-1",
            approved_at=f"2026-08-17T03:{revision // 60:02d}:{revision % 60:02d}.000Z",
        )
        rows.append({"approval_revision": revision, "receipt": receipt.to_dict()})
    document = _with_hash({
        "approval_snapshot_version": "1.0.0", "task_owner": "TASK-036/P-UX-2D3",
        "project_id": "project-1", "revision": 256, "approvals": rows,
        "export_job_created": False, "render_started": False, "publication_started": False,
    })
    app.snapshot_path.write_bytes(canonical_json_bytes(document) + b"\n")
    next_value = readiness(production="f")
    prepared = app.prepare_approval(
        readiness=next_value,
        expected_readiness_projection_sha256=next_value["projection_sha256"],
        expected_snapshot_sha256=document["snapshot_sha256"],
    )
    before = app.snapshot_path.read_bytes()
    with pytest.raises(ProductError, match="bounded maximum"):
        app.apply_approval(confirmation_id=prepared["confirmation_id"], readiness=next_value, approved_by="owner-1")
    assert app.snapshot_path.read_bytes() == before


def test_atomic_failure_leaves_no_approval_row(tmp_path: Path) -> None:
    def fail(stage: str, _path: Path) -> None:
        if stage == "before_replace":
            raise OSError("synthetic write failure")

    app = application(tmp_path, ["failure"], failure=fail)
    current = readiness()
    initial = app.snapshot(readiness=current)
    prepared = app.prepare_approval(
        readiness=current,
        expected_readiness_projection_sha256=current["projection_sha256"],
        expected_snapshot_sha256=initial["snapshot_sha256"],
    )
    with pytest.raises(OSError, match="synthetic write failure"):
        app.apply_approval(confirmation_id=prepared["confirmation_id"], readiness=current, approved_by="owner-1")
    assert app.snapshot(readiness=current)["state"] == "NO_APPROVAL"


def test_contract_surface_has_no_export_process_network_or_media_effect() -> None:
    source = (Path(__file__).parents[1] / "src" / "ai_video_production" / "final_review_application.py").read_text(encoding="utf-8")
    for forbidden in ("subprocess", "requests", "urllib", "socket", "ExportQueueApplication", "open("):
        assert forbidden not in source
