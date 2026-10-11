from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.audit_application import Task038AuditApplication
from ai_video_production.candidate_audit import (
    AuditRecord,
    AuditorKind,
    CandidateAuditRegistry,
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
from ai_video_production.serialization import canonical_json_bytes
from ai_video_production.task111_audit_input_controller import Task111AuditInputController


ASSET_SHA = "sha256:" + "a" * 64


def _seed_ready_candidate(root: Path) -> Task038AuditApplication:
    production = ProductionControlRegistry()
    production.add_slot(
        SceneAssetSlot("slot-1", "project-1", "scene-1", SlotKind.START_FRAME, True)
    )
    production.add_candidate(
        AssetCandidate("candidate-1", "slot-1", "asset-1", ASSET_SHA, 1)
    )
    production.transition_candidate("candidate-1", CandidateLifecycle.READY_FOR_AUDIT)
    ProductionControlSnapshotStore.save(root / "production-control.json", production)
    return Task038AuditApplication(project_root=root, project_id="project-1")


def _input(snapshot: dict[str, object]) -> dict[str, object]:
    return {
        "audit_id": "audit-human-1",
        "candidate_id": "candidate-1",
        "asset_id": "asset-1",
        "asset_sha256": ASSET_SHA,
        "auditor_id": "desktop-owner",
        "auditor_version": None,
        "contract_refs": ["visual-contract-1"],
        "dimension_scores": {"CONTRACT": 92.0, "COMPOSITION": 88.0},
        "findings": [
            {
                "finding_id": "finding-1",
                "dimension": "GEOMETRY",
                "severity": "WARNING",
                "code": "DEPTH_REVIEWED",
                "summary": "Depth order was reviewed by the operator.",
                "critical_violation": False,
            }
        ],
        "failure_codes": [],
        "alternate_use_proposals": [],
        "expected_production_snapshot_sha256": snapshot[
            "production_snapshot_sha256"
        ],
        "expected_audit_snapshot_sha256": snapshot["audit_snapshot_sha256"],
    }


def test_prepare_apply_and_reopen_persist_one_human_audit_without_decision(
    tmp_path: Path,
) -> None:
    application = _seed_ready_candidate(tmp_path)
    controller = Task111AuditInputController(
        application, token_factory=lambda: "audit-input-confirm-1"
    )
    initial = application.snapshot()

    prepared = controller.prepare(**_input(initial))
    assert prepared["confirmation_id"] == "audit-input-confirm-1"
    assert prepared["candidate_id"] == "candidate-1"
    assert prepared["asset_id"] == "asset-1"
    assert prepared["asset_sha256"] == ASSET_SHA
    assert prepared["record"]["auditor_kind"] == "HUMAN"
    assert prepared["record"]["record_sha256"].startswith("sha256:")
    assert application.snapshot()["workspace"]["candidates"][0]["audit_count"] == 0

    result = controller.apply(
        confirmation_id="audit-input-confirm-1",
        explicit_human_confirmation=True,
    )
    assert result["status"] == "SAVED"
    assert result["human_candidate_decision_recorded"] is False
    assert result["automatic_candidate_accept"] is False
    assert result["automatic_candidate_reject"] is False
    assert result["automatic_candidate_lock"] is False
    assert result["provider_execution_started"] is False

    reopened = Task038AuditApplication(
        project_root=tmp_path, project_id="project-1"
    ).snapshot()
    row = reopened["workspace"]["candidates"][0]
    assert row["audit_count"] == 1
    assert row["human_audit_count"] == 1
    assert row["human_decision"] is None
    assert row["lifecycle_state"] == "READY_FOR_AUDIT"
    assert row["audit_history"][0]["audit_id"] == "audit-human-1"

    with pytest.raises(ProductError) as exc:
        controller.apply(
            confirmation_id="audit-input-confirm-1",
            explicit_human_confirmation=True,
        )
    assert exc.value.code == "ERR_TASK111_AUDIT_CONFIRMATION_INVALID"


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("asset_id", "other-asset", "ERR_TASK111_AUDIT_ASSET_MISMATCH"),
        (
            "asset_sha256",
            "sha256:" + "b" * 64,
            "ERR_TASK111_AUDIT_ASSET_MISMATCH",
        ),
        (
            "expected_production_snapshot_sha256",
            "sha256:" + "c" * 64,
            "ERR_TASK111_AUDIT_SNAPSHOT_CONFLICT",
        ),
        (
            "expected_audit_snapshot_sha256",
            "sha256:" + "d" * 64,
            "ERR_TASK111_AUDIT_SNAPSHOT_CONFLICT",
        ),
    ],
)
def test_prepare_fails_closed_on_wrong_identity_or_snapshot(
    tmp_path: Path, field: str, value: str, code: str
) -> None:
    application = _seed_ready_candidate(tmp_path)
    controller = Task111AuditInputController(application)
    values = _input(application.snapshot())
    values[field] = value
    with pytest.raises(ProductError) as exc:
        controller.prepare(**values)
    assert exc.value.code == code
    assert "other-asset" not in str(exc.value)
    assert not (tmp_path / "candidate-audit.json").exists()


def test_prepare_rejects_invalid_or_second_audit_without_echoing_input(
    tmp_path: Path,
) -> None:
    application = _seed_ready_candidate(tmp_path)
    controller = Task111AuditInputController(
        application, token_factory=iter(("confirm-1", "confirm-2")).__next__
    )
    values = _input(application.snapshot())
    values["findings"] = [{"summary": "private://do-not-echo"}]
    with pytest.raises(ProductError) as exc:
        controller.prepare(**values)
    assert exc.value.code == "ERR_TASK111_AUDIT_INPUT_INVALID"
    assert "private://do-not-echo" not in str(exc.value)

    prepared = controller.prepare(**_input(application.snapshot()))
    controller.apply(
        confirmation_id=prepared["confirmation_id"],
        explicit_human_confirmation=True,
    )
    with pytest.raises(ProductError) as exc:
        controller.prepare(**_input(application.snapshot()))
    assert exc.value.code == "ERR_TASK111_AUDIT_ALREADY_RECORDED"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("contract_refs", []),
        ("contract_refs", [f"contract-{index}" for index in range(65)]),
        ("dimension_scores", {}),
        ("dimension_scores", {"CONTRACT": "92"}),
        ("dimension_scores", {"CONTRACT": 10**1000}),
        ("dimension_scores", {"CONTRACT": float("nan")}),
        ("dimension_scores", {"CONTRACT": float("inf")}),
        ("findings", [{}] * 257),
        (
            "findings",
            [
                {
                    "finding_id": "finding-surrogate",
                    "dimension": "GEOMETRY",
                    "severity": "WARNING",
                    "code": "SURROGATE_REVIEW",
                    "summary": "\ud800",
                    "critical_violation": False,
                }
            ],
        ),
        ("failure_codes", [f"failure-{index}" for index in range(257)]),
        (
            "alternate_use_proposals",
            [f"proposal-{index}" for index in range(65)],
        ),
    ],
)
def test_prepare_rejects_empty_malformed_or_unbounded_review_input(
    tmp_path: Path, field: str, value: object
) -> None:
    application = _seed_ready_candidate(tmp_path)
    controller = Task111AuditInputController(application)
    values = _input(application.snapshot())
    values[field] = value

    with pytest.raises(ProductError) as exc:
        controller.prepare(**values)

    assert exc.value.code == "ERR_TASK111_AUDIT_INPUT_INVALID"
    assert not (tmp_path / "candidate-audit.json").exists()


def test_prepare_rejects_real_projected_oversize_before_write_and_reopens(
    tmp_path: Path,
) -> None:
    application = _seed_ready_candidate(tmp_path)
    registry = CandidateAuditRegistry()
    proposals = tuple("x" * 1000 for _ in range(64))
    index = 0
    while (
        len(canonical_json_bytes(CandidateAuditSnapshotStore.snapshot(registry))) + 1
        < 8_000_000
    ):
        registry.add_audit(
            AuditRecord(
                audit_id=f"filler-audit-{index}",
                candidate_id=f"filler-candidate-{index}",
                asset_sha256="sha256:" + f"{index:064x}"[-64:],
                contract_refs=("visual-contract-1",),
                auditor_kind=AuditorKind.HUMAN,
                auditor_id="desktop-owner",
                auditor_version=None,
                dimension_scores={"CONTRACT": 90.0},
                findings=(),
                failure_codes=(),
                alternate_use_proposals=proposals,
            )
        )
        index += 1
    audit_path = tmp_path / "candidate-audit.json"
    CandidateAuditSnapshotStore.save(audit_path, registry)
    before = audit_path.read_bytes()
    assert len(before) <= 8 * 1024 * 1024
    CandidateAuditSnapshotStore.load(audit_path)

    values = _input(application.snapshot())
    values["findings"] = [
        {
            "finding_id": f"finding-{item}",
            "dimension": "GEOMETRY",
            "severity": "WARNING",
            "code": f"REVIEWED_{item}",
            "summary": "y" * 2000,
            "critical_violation": False,
        }
        for item in range(256)
    ]
    controller = Task111AuditInputController(application)
    with pytest.raises(ProductError) as exc:
        controller.prepare(**values)

    assert exc.value.code == "ERR_TASK111_AUDIT_SNAPSHOT_TOO_LARGE"
    assert audit_path.read_bytes() == before
    reopened = CandidateAuditSnapshotStore.load(audit_path)
    assert len(reopened.audit_records) == index
    assert application.snapshot()["workspace"]["candidates"][0]["audit_count"] == 0


def test_save_failure_is_public_safe_one_shot_and_reopen_remains_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = _seed_ready_candidate(tmp_path)
    controller = Task111AuditInputController(
        application, token_factory=lambda: "confirm-fail"
    )
    prepared = controller.prepare(**_input(application.snapshot()))

    original = CandidateAuditSnapshotStore.save

    def fail(*args, **kwargs):
        raise OSError("private://operator/path/secret")

    monkeypatch.setattr(CandidateAuditSnapshotStore, "save", fail)
    with pytest.raises(ProductError) as exc:
        controller.apply(
            confirmation_id=prepared["confirmation_id"],
            explicit_human_confirmation=True,
        )
    assert exc.value.code == "ERR_TASK111_AUDIT_SAVE_FAILED"
    assert "private://operator/path/secret" not in str(exc.value)

    monkeypatch.setattr(CandidateAuditSnapshotStore, "save", original)
    reopened = Task038AuditApplication(
        project_root=tmp_path, project_id="project-1"
    ).snapshot()
    assert reopened["workspace"]["candidates"][0]["audit_count"] == 0
    with pytest.raises(ProductError) as exc:
        controller.apply(
            confirmation_id="confirm-fail",
            explicit_human_confirmation=True,
        )
    assert exc.value.code == "ERR_TASK111_AUDIT_CONFIRMATION_INVALID"


def test_apply_requires_literal_explicit_human_confirmation(tmp_path: Path) -> None:
    application = _seed_ready_candidate(tmp_path)
    controller = Task111AuditInputController(
        application, token_factory=lambda: "confirm-1"
    )
    controller.prepare(**_input(application.snapshot()))
    for value in (False, 1, "true", None):
        with pytest.raises(ProductError) as exc:
            controller.apply(
                confirmation_id="confirm-1",
                explicit_human_confirmation=value,
            )
        assert exc.value.code == "ERR_TASK111_AUDIT_CONFIRMATION_REQUIRED"
