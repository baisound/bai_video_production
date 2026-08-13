from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.production_control import CandidateLifecycle
from ai_video_production.production_control_application import Task037ProductionControlApplication
from ai_video_production.production_control_store import ProductionControlSnapshotStore
from ai_video_production.production_blueprint import (
    AssetSourceStrategy,
    BlueprintScene,
    CameraMotion,
    GenerationRisk,
    ProductionBlueprint,
)
from ai_video_production.production_proposal import (
    CreationIntent,
    ProductionGoApprovalService,
    ProductionProposalRegistry,
    ProductionProposalRevision,
    ProposalSection,
    ProviderPolicyBinding,
)
from ai_video_production.timebase import FrameRate


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
POLICY_SHA = "sha256:" + "c" * 64
SLOT_ID = "slot:SC01:VIDEO"


def app(tmp_path: Path, *, token: str = "confirm-lock-1") -> Task037ProductionControlApplication:
    return Task037ProductionControlApplication(
        project_root=tmp_path,
        project_id="project-1",
        token_factory=lambda: token,
    )


def approved_plan():
    proposals = ProductionProposalRegistry()
    intent = CreationIntent(
        "INTENT-DEMO", 1, "Intro", "Viewers", "YouTube", "16:9", Decimal("10"),
        "Calm", "Explain", "ja-JP", budget_ceiling=Decimal("20"),
    )
    proposals.add_intent(intent)
    scene = BlueprintScene(
        "SC01", 0, 300, "Opening", AssetSourceStrategy.REAL_CAPTURE,
        GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, (),
    )
    blueprint = ProductionBlueprint("BP-DEMO-001", "Demo", FrameRate(30, 1), 300, (), (scene,))
    proposal = ProductionProposalRevision(
        "PROPOSAL-DEMO", 1, intent.to_dict()["intent_sha256"], blueprint,
        (ProposalSection("concept", "CONCEPT", "Concept", "Opening"),),
        ProviderPolicyBinding("policy", "1", POLICY_SHA), Decimal("1"), Decimal("10"), "USD",
    )
    proposals.add_proposal(proposal)
    go = ProductionGoApprovalService(proposals, token_factory=lambda: "go")
    go.prepare_go(
        proposal_id="PROPOSAL-DEMO", proposal_revision=1, reference_bindings=(),
        cost_ceiling="12", rights_warnings_acknowledged=False,
    )
    plan = go.approve_go(confirmation_id="go", approved_by="owner")
    return proposals, blueprint, plan


def install_plan(service: Task037ProductionControlApplication) -> dict:
    proposals, blueprint, plan = approved_plan()
    return service.install_approved_plan(
        proposal_registry=proposals,
        plan_id=plan.plan_id,
        blueprint=blueprint,
        expected_snapshot_sha256=service.snapshot()["snapshot_sha256"],
    )


def slot_row(workspace: dict, slot_id: str = SLOT_ID) -> dict:
    return next(row for row in workspace["slots"] if row["slot_id"] == slot_id)


def add_candidate(
    service: Task037ProductionControlApplication,
    *,
    candidate_id: str = "candidate-1",
    asset_sha256: str = SHA_A,
) -> dict:
    return service.register_candidate(
        candidate_id=candidate_id,
        slot_id=SLOT_ID,
        asset_id=f"asset-{candidate_id}",
        asset_sha256=asset_sha256,
        expected_snapshot_sha256=service.snapshot()["snapshot_sha256"],
    )


def accept_candidate_outside_task037(service: Task037ProductionControlApplication, candidate_id: str) -> None:
    registry = ProductionControlSnapshotStore.load(service.snapshot_path)
    previous = ProductionControlSnapshotStore.snapshot(registry)["snapshot_sha256"]
    if registry.candidates[candidate_id].lifecycle_state is CandidateLifecycle.CREATED:
        registry.transition_candidate(candidate_id, CandidateLifecycle.READY_FOR_AUDIT)
    registry.transition_candidate(candidate_id, CandidateLifecycle.ACCEPTED)
    ProductionControlSnapshotStore.save(
        service.snapshot_path,
        registry,
        expected_previous_snapshot_sha256=previous,
    )


def test_empty_workspace_is_deterministic_and_path_free(tmp_path: Path) -> None:
    service = app(tmp_path)
    first = service.snapshot()
    second = service.snapshot()
    assert first == second
    assert first["persisted"] is False
    assert first["slots"] == []
    assert str(tmp_path) not in json.dumps(first)
    assert first["physical_delete_available"] is False
    assert first["provider_execution_started"] is False
    assert first["resolve_mutation_started"] is False


def test_install_approved_plan_persists_exact_trace_and_disallows_loose_slot_creation(tmp_path: Path) -> None:
    service = app(tmp_path)
    result = install_plan(service)
    assert service.snapshot_path.name == "production-control.json"
    assert result["workspace"]["persisted"] is True
    assert result["control_plan"]["project_id"] == "project-1"
    assert slot_row(result["workspace"])["slot_id"] == SLOT_ID
    assert not hasattr(service, "create_slot")
    reopened = app(tmp_path).snapshot()
    assert reopened == result["workspace"]


def test_stale_expected_snapshot_fails_without_mutation(tmp_path: Path) -> None:
    service = app(tmp_path)
    stale = service.snapshot()["snapshot_sha256"]
    install_plan(service)
    proposals, blueprint, plan = approved_plan()
    with pytest.raises(ProductError) as exc:
        service.install_approved_plan(
            proposal_registry=proposals,
            plan_id=plan.plan_id,
            blueprint=blueprint,
            expected_snapshot_sha256=stale,
        )
    assert exc.value.code == "ERR_PRODUCTION_APPLICATION_SNAPSHOT_CONFLICT"
    assert SLOT_ID in {row["slot_id"] for row in service.snapshot()["slots"]}


def test_candidate_versions_append_and_do_not_overwrite(tmp_path: Path) -> None:
    service = app(tmp_path)
    install_plan(service)
    first = add_candidate(service)
    second = add_candidate(service, candidate_id="candidate-2", asset_sha256=SHA_B)
    assert first["candidate"]["candidate_version"] == 1
    assert second["candidate"]["candidate_version"] == 2
    rows = slot_row(service.snapshot())["candidates"]
    assert [row["candidate_id"] for row in rows] == ["candidate-1", "candidate-2"]


def test_mark_ready_for_audit_is_durable_but_does_not_accept(tmp_path: Path) -> None:
    service = app(tmp_path)
    install_plan(service)
    add_candidate(service)
    result = service.mark_ready_for_audit(
        candidate_id="candidate-1",
        expected_snapshot_sha256=service.snapshot()["snapshot_sha256"],
    )
    assert result["candidate"]["lifecycle_state"] == "READY_FOR_AUDIT"
    row = slot_row(app(tmp_path).snapshot())["candidates"][0]
    assert row["lifecycle_state"] == "READY_FOR_AUDIT"
    assert "PREPARE_LOCK" not in row["available_actions"]


def test_prepare_lock_requires_task038_acceptance(tmp_path: Path) -> None:
    service = app(tmp_path)
    install_plan(service)
    add_candidate(service)
    with pytest.raises(ProductError) as exc:
        service.prepare_lock(
            slot_id=SLOT_ID,
            candidate_id="candidate-1",
            expected_snapshot_sha256=service.snapshot()["snapshot_sha256"],
        )
    assert exc.value.code == "ERR_PRODUCTION_CANDIDATE_NOT_ACCEPTED"


def test_candidate_lineage_must_reference_existing_candidate_in_same_slot(tmp_path: Path) -> None:
    service = app(tmp_path)
    install_plan(service)
    with pytest.raises(ProductError) as exc:
        service.register_candidate(
            candidate_id="candidate-2",
            slot_id=SLOT_ID,
            asset_id="asset-2",
            asset_sha256=SHA_B,
            parent_candidate_id="missing-candidate",
            expected_snapshot_sha256=service.snapshot()["snapshot_sha256"],
        )
    assert exc.value.code == "ERR_PRODUCTION_APPLICATION_CANDIDATE_LINEAGE_INVALID"
    assert slot_row(service.snapshot())["candidates"] == []


def test_confirmed_lock_is_exact_one_shot_and_persisted(tmp_path: Path) -> None:
    service = app(tmp_path)
    install_plan(service)
    add_candidate(service)
    accept_candidate_outside_task037(service, "candidate-1")
    prepared = service.prepare_lock(
        slot_id=SLOT_ID,
        candidate_id="candidate-1",
        expected_snapshot_sha256=service.snapshot()["snapshot_sha256"],
    )
    assert prepared["asset_sha256"] == SHA_A
    assert prepared["human_final_authority_required"] is True
    result = service.apply_lock(confirmation_id=prepared["confirmation_id"])
    assert result["slot"]["status"] == "LOCKED"
    assert result["slot"]["locked_candidate_id"] == "candidate-1"
    assert app(tmp_path).snapshot()["locked_slot_count"] == 1
    with pytest.raises(ProductError) as exc:
        service.apply_lock(confirmation_id=prepared["confirmation_id"])
    assert exc.value.code == "ERR_PRODUCTION_APPLICATION_CONFIRMATION_INVALID"


def test_lock_confirmation_fails_closed_after_snapshot_change(tmp_path: Path) -> None:
    service = app(tmp_path)
    install_plan(service)
    add_candidate(service)
    accept_candidate_outside_task037(service, "candidate-1")
    prepared = service.prepare_lock(
        slot_id=SLOT_ID,
        candidate_id="candidate-1",
        expected_snapshot_sha256=service.snapshot()["snapshot_sha256"],
    )
    registry = ProductionControlSnapshotStore.load(service.snapshot_path)
    previous = ProductionControlSnapshotStore.snapshot(registry)["snapshot_sha256"]
    registry.add_slot(registry.slots[SLOT_ID].__class__(
        slot_id="slot-2",
        project_id="project-1",
        scene_id="scene-2",
        slot_kind=registry.slots[SLOT_ID].slot_kind,
        required=False,
    ))
    ProductionControlSnapshotStore.save(
        service.snapshot_path,
        registry,
        expected_previous_snapshot_sha256=previous,
    )
    with pytest.raises(ProductError) as exc:
        service.apply_lock(confirmation_id=prepared["confirmation_id"])
    assert exc.value.code == "ERR_PRODUCTION_APPLICATION_CONFIRMATION_STALE"
    with pytest.raises(ProductError) as replay:
        service.apply_lock(confirmation_id=prepared["confirmation_id"])
    assert replay.value.code == "ERR_PRODUCTION_APPLICATION_CONFIRMATION_INVALID"
    assert service.snapshot()["locked_slot_count"] == 0


def test_cross_project_snapshot_is_rejected(tmp_path: Path) -> None:
    first = app(tmp_path)
    install_plan(first)
    other = Task037ProductionControlApplication(project_root=tmp_path, project_id="project-2")
    with pytest.raises(ProductError) as exc:
        other.snapshot()
    assert exc.value.code == "ERR_PRODUCTION_APPLICATION_PROJECT_MISMATCH"


def test_snapshot_tamper_fails_closed(tmp_path: Path) -> None:
    service = app(tmp_path)
    install_plan(service)
    document = json.loads(service.snapshot_path.read_text(encoding="utf-8"))
    document["slots"][0]["scene_id"] = "scene-tampered"
    service.snapshot_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        service.snapshot()
    assert exc.value.code == "ERR_PRODUCTION_SNAPSHOT_CHECKSUM"
