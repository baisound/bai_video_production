from __future__ import annotations

from pathlib import Path
import json

import pytest

from ai_video_production.audit_application import Task038AuditApplication
from ai_video_production.candidate_audit import (
    AuditDimension,
    AuditFinding,
    AuditRecord,
    AuditorKind,
    FindingSeverity,
)
from ai_video_production.candidate_audit_store import CandidateAuditSnapshotStore
from ai_video_production.errors import ProductError
from ai_video_production.production_control import (
    AssetCandidate,
    CandidateLifecycle,
    ProductionControlRegistry,
    SceneAssetSlot,
    SlotKind,
)
from ai_video_production.production_control_store import ProductionControlSnapshotStore


SHA = "sha256:" + "a" * 64


def seed_ready_candidate(root: Path) -> None:
    production = ProductionControlRegistry()
    production.add_slot(SceneAssetSlot("slot-1", "project-1", "scene-1", SlotKind.START_FRAME, True))
    production.add_candidate(AssetCandidate("candidate-1", "slot-1", "asset-1", SHA, 1))
    production.transition_candidate("candidate-1", CandidateLifecycle.READY_FOR_AUDIT)
    ProductionControlSnapshotStore.save(root / "production-control.json", production)


def audit_record(audit_id: str = "audit-1") -> AuditRecord:
    return AuditRecord(
        audit_id,
        "candidate-1",
        SHA,
        ("contract-1",),
        AuditorKind.AI,
        "vision-judge",
        "v1",
        {"CONTRACT": 92.0, "COMPOSITION": 88.0},
        (AuditFinding("finding-1", AuditDimension.GEOMETRY, FindingSeverity.CRITICAL, "DEPTH_REVERSED", "wrong depth", True),),
        ("DEPTH_REVERSED",),
        ("Use as an intentionally distorted insert",),
    )


def prepared_app(root: Path, **kwargs) -> Task038AuditApplication:
    seed_ready_candidate(root)
    app = Task038AuditApplication(project_root=root, project_id="project-1", token_factory=lambda: "confirm-1", **kwargs)
    snapshot = app.snapshot()
    app.record_audit(
        record=audit_record(),
        expected_production_snapshot_sha256=snapshot["production_snapshot_sha256"],
        expected_audit_snapshot_sha256=snapshot["audit_snapshot_sha256"],
    )
    return app


def prepare_accept(app: Task038AuditApplication) -> dict:
    snapshot = app.snapshot()
    return app.prepare_human_decision(
        candidate_id="candidate-1",
        decision="ACCEPT",
        expected_production_snapshot_sha256=snapshot["production_snapshot_sha256"],
        expected_audit_snapshot_sha256=snapshot["audit_snapshot_sha256"],
    )


def test_durable_accept_preserves_separate_human_authority_and_history(tmp_path: Path) -> None:
    app = prepared_app(tmp_path)
    prepared = prepare_accept(app)
    assert prepared["critical_violation_present"] is True
    result = app.apply_human_decision(confirmation_id="confirm-1", actor_id="owner", notes="reviewed")
    assert result["production_binding"]["lifecycle_after"] == "ACCEPTED"
    reopened = Task038AuditApplication(project_root=tmp_path, project_id="project-1").snapshot()
    assert reopened["recovery"]["required"] is False
    row = reopened["workspace"]["candidates"][0]
    assert row["human_decision"] == "ACCEPT"
    assert row["critical_violation"] is True
    assert CandidateAuditSnapshotStore.load(tmp_path / "candidate-audit.json").decisions
    with pytest.raises(ProductError) as exc:
        app.apply_human_decision(confirmation_id="confirm-1", actor_id="owner")
    assert exc.value.code == "ERR_AUDIT_APPLICATION_CONFIRMATION_INVALID"


def test_crash_after_audit_save_requires_explicit_exact_completion(tmp_path: Path) -> None:
    def fail(stage: str) -> None:
        if stage == "after_audit_save":
            raise RuntimeError("simulated crash")

    app = prepared_app(tmp_path, failure_injector=fail)
    prepare_accept(app)
    with pytest.raises(RuntimeError, match="simulated crash"):
        app.apply_human_decision(confirmation_id="confirm-1", actor_id="owner")

    reopened = Task038AuditApplication(project_root=tmp_path, project_id="project-1")
    recovery = reopened.snapshot()["recovery"]
    assert recovery["state"] == "AUDIT_NEW_PRODUCTION_OLD"
    assert recovery["available_actions"] == ["COMPLETE"]
    completed = reopened.apply_recovery(action="COMPLETE")
    assert completed["recovery"]["required"] is False
    assert completed["workspace"]["candidates"][0]["lifecycle_state"] == "ACCEPTED"


def test_crash_after_prepare_can_be_abandoned_without_applying_decision(tmp_path: Path) -> None:
    def fail(stage: str) -> None:
        if stage == "after_transaction_prepare":
            raise RuntimeError("simulated crash")

    app = prepared_app(tmp_path, failure_injector=fail)
    prepare_accept(app)
    with pytest.raises(RuntimeError):
        app.apply_human_decision(confirmation_id="confirm-1", actor_id="owner")
    reopened = Task038AuditApplication(project_root=tmp_path, project_id="project-1")
    assert reopened.snapshot()["recovery"]["state"] == "OLD_OLD"
    result = reopened.apply_recovery(action="ABANDON")
    row = result["workspace"]["candidates"][0]
    assert row["lifecycle_state"] == "READY_FOR_AUDIT"
    assert row["human_decision"] is None


def test_stale_snapshot_and_cross_project_state_fail_closed(tmp_path: Path) -> None:
    app = prepared_app(tmp_path)
    stale = app.snapshot()["audit_snapshot_sha256"]
    current = app.snapshot()
    app.record_audit(
        record=audit_record("audit-2"),
        expected_production_snapshot_sha256=current["production_snapshot_sha256"],
        expected_audit_snapshot_sha256=current["audit_snapshot_sha256"],
    )
    with pytest.raises(ProductError) as exc:
        app.prepare_human_decision(
            candidate_id="candidate-1",
            decision="REJECT",
            expected_production_snapshot_sha256=app.snapshot()["production_snapshot_sha256"],
            expected_audit_snapshot_sha256=stale,
        )
    assert exc.value.code == "ERR_AUDIT_APPLICATION_SNAPSHOT_CONFLICT"
    with pytest.raises(ProductError) as exc:
        Task038AuditApplication(project_root=tmp_path, project_id="different-project").snapshot()
    assert exc.value.code == "ERR_AUDIT_APPLICATION_PROJECT_MISMATCH"


def test_crash_after_both_stores_requires_exact_finalize_only(tmp_path: Path) -> None:
    def fail(stage: str) -> None:
        if stage == "after_production_save":
            raise RuntimeError("simulated crash")

    app = prepared_app(tmp_path, failure_injector=fail)
    prepare_accept(app)
    with pytest.raises(RuntimeError):
        app.apply_human_decision(confirmation_id="confirm-1", actor_id="owner")
    reopened = Task038AuditApplication(project_root=tmp_path, project_id="project-1")
    assert reopened.snapshot()["recovery"]["state"] == "NEW_NEW"
    assert reopened.snapshot()["recovery"]["available_actions"] == ["FINALIZE"]
    assert reopened.apply_recovery(action="FINALIZE")["recovery"]["required"] is False


def test_unknown_partial_state_has_no_automatic_recovery_action(tmp_path: Path) -> None:
    def fail(stage: str) -> None:
        if stage == "after_audit_save":
            raise RuntimeError("simulated crash")

    app = prepared_app(tmp_path, failure_injector=fail)
    prepare_accept(app)
    with pytest.raises(RuntimeError):
        app.apply_human_decision(confirmation_id="confirm-1", actor_id="owner")
    production_path = tmp_path / "production-control.json"
    production = ProductionControlSnapshotStore.load(production_path)
    old = ProductionControlSnapshotStore.snapshot(production)["snapshot_sha256"]
    production.add_candidate(AssetCandidate("candidate-2", "slot-1", "asset-2", "sha256:" + "b" * 64, 2))
    ProductionControlSnapshotStore.save(production_path, production, expected_previous_snapshot_sha256=old)

    reopened = Task038AuditApplication(project_root=tmp_path, project_id="project-1")
    recovery = reopened.snapshot()["recovery"]
    assert recovery["state"] == "UNKNOWN_MIXTURE"
    assert recovery["available_actions"] == []
    with pytest.raises(ProductError) as exc:
        reopened.apply_recovery(action="COMPLETE")
    assert exc.value.code == "ERR_AUDIT_RECOVERY_ACTION_INVALID"


def test_transaction_checksum_tamper_is_rejected(tmp_path: Path) -> None:
    def fail(stage: str) -> None:
        if stage == "after_transaction_prepare":
            raise RuntimeError("simulated crash")

    app = prepared_app(tmp_path, failure_injector=fail)
    prepare_accept(app)
    with pytest.raises(RuntimeError):
        app.apply_human_decision(confirmation_id="confirm-1", actor_id="owner")
    path = tmp_path / "task038-decision-transaction.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["decision"] = "REJECT"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        Task038AuditApplication(project_root=tmp_path, project_id="project-1").snapshot()
    assert exc.value.code == "ERR_AUDIT_TRANSACTION_CHECKSUM"
