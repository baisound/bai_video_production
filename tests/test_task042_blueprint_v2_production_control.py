from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from ai_video_production.approved_plan_orchestration import ApprovedPlanProductionControlInstaller
from ai_video_production.approved_plan_trace import ApprovedPlanTraceValidator
from ai_video_production.blueprint_v2_world_lock import BlueprintV2WorldLockService
from ai_video_production.errors import ProductError
from ai_video_production.planning_application import Task027PlanningApplication
from ai_video_production.production_blueprint import AssetSourceStrategy, CameraMotion, GenerationRisk
from ai_video_production.production_blueprint_v2 import (
    BlueprintSceneV2,
    CharacterLockBinding,
    CharacterRole,
    FrameIntent,
    FrameKind,
    FrameReferenceBinding,
    ProductionBlueprintV2,
)
from ai_video_production.production_control import (
    AssetCandidate,
    CandidateLifecycle,
    EntityRef,
    EntityType,
    ProductionControlRegistry,
    SceneAssetSlot,
    SlotKind,
    SlotStatus,
)
from ai_video_production.production_control_application import Task037ProductionControlApplication
from ai_video_production.production_control_store import ProductionControlSnapshotStore
from ai_video_production.production_proposal import (
    CreationIntent,
    ProductionGoApprovalService,
    ProductionProposalRegistry,
    ProductionProposalRevision,
    ProposalSection,
    ProviderPolicyBinding,
    ReferenceAssetBinding,
)
from ai_video_production.production_proposal_store import ProductionProposalSnapshotStore
from ai_video_production.timebase import FrameRate


H = lambda ch: "sha256:" + ch * 64


def frame(kind: FrameKind, suffix: str, sha: str) -> FrameIntent:
    return FrameIntent(
        kind,
        f"{kind.value} visual",
        "exact task axis",
        ("subject",),
        ("crew",),
        ("subject", "background"),
        "eye-level",
        FrameReferenceBinding((CharacterLockBinding(
            CharacterRole.PRIMARY,
            f"asset-{suffix}",
            sha,
            f"slot-ref-{suffix}",
            f"candidate-ref-{suffix}",
        ),)),
    )


def approved() -> tuple[ProductionProposalRegistry, ProductionBlueprintV2, str]:
    proposals = ProductionProposalRegistry()
    intent = CreationIntent(
        "INTENT-WORLD-LOCK",
        1,
        "Product introduction",
        "Viewers",
        "YouTube",
        "16:9",
        Decimal("10"),
        "Clear",
        "Explain exact WORLD LOCK",
        "ja-JP",
        budget_ceiling=Decimal("20"),
    )
    proposals.add_intent(intent)
    blueprint = ProductionBlueprintV2(
        "BP-WORLD-LOCK",
        "WORLD LOCK",
        FrameRate(30, 1),
        300,
        (BlueprintSceneV2(
            "SC01",
            0,
            300,
            "Opening",
            AssetSourceStrategy.AI_GENERATED,
            GenerationRisk.B_HEADLINE,
            CameraMotion.STATIC,
            frame(FrameKind.START, "start", H("a")),
            frame(FrameKind.END, "end", H("b")),
        ),),
    )
    proposals.add_proposal(ProductionProposalRevision(
        "PROPOSAL-WORLD-LOCK",
        1,
        intent.to_dict()["intent_sha256"],
        blueprint,
        (ProposalSection("concept", "CONCEPT", "Concept", "Exact WORLD LOCK."),),
        ProviderPolicyBinding("policy", "v1", H("c")),
        Decimal("1"),
        Decimal("10"),
        "USD",
    ))
    go = ProductionGoApprovalService(proposals, token_factory=lambda: "go-v2")
    go.prepare_go(
        proposal_id="PROPOSAL-WORLD-LOCK",
        proposal_revision=1,
        reference_bindings=tuple(
            ReferenceAssetBinding(row.reference_id, row.asset_id, row.asset_sha256)
            for row in BlueprintV2WorldLockService.requirements(blueprint)
        ),
        cost_ceiling="12",
        rights_warnings_acknowledged=False,
    )
    plan = go.approve_go(confirmation_id="go-v2", approved_by="owner")
    return proposals, blueprint, plan.plan_id


def world_registry(blueprint: ProductionBlueprintV2) -> ProductionControlRegistry:
    registry = ProductionControlRegistry()
    for row in BlueprintV2WorldLockService.requirements(blueprint):
        registry.add_slot(SceneAssetSlot(
            row.slot_id,
            "project-v2",
            "WORLD",
            row.expected_slot_kind,
            True,
        ))
        registry.add_candidate(AssetCandidate(
            row.candidate_id,
            row.slot_id,
            row.asset_id,
            row.asset_sha256,
            1,
        ))
        registry.transition_candidate(row.candidate_id, CandidateLifecycle.READY_FOR_AUDIT)
        registry.transition_candidate(row.candidate_id, CandidateLifecycle.ACCEPTED)
        slot = registry.slots[row.slot_id]
        registry.lock_candidate(
            slot_id=row.slot_id,
            candidate_id=row.candidate_id,
            expected_revision=slot.revision,
        )
    return registry


def test_v2_install_reuses_world_lock_and_connects_transitive_stale_graph() -> None:
    proposals, blueprint, plan_id = approved()
    production = world_registry(blueprint)
    control_plan = ApprovedPlanProductionControlInstaller.install(
        proposal_registry=proposals,
        plan_id=plan_id,
        blueprint=blueprint,
        project_id="project-v2",
        production_registry=production,
    )
    assert {slot.slot_kind for slot in control_plan.slots} == {
        SlotKind.VIDEO,
        SlotKind.START_FRAME,
        SlotKind.END_FRAME,
        SlotKind.BGM,
    }
    assert len(production.slots) == 6
    trace = ApprovedPlanTraceValidator.validate(
        proposals=proposals,
        plan_id=plan_id,
        production=production,
        project_id="project-v2",
    ).to_dict()
    assert trace["status"] == "PASS"
    assert trace["world_lock_binding_count"] == 2

    result = production.mark_stale(
        EntityRef(EntityType.SLOT, "slot-ref-start"),
        include_root=True,
    )
    assert "SLOT:slot:SC01:VIDEO" in [item.key for item in result.affected]
    assert production.slots["slot:SC01:VIDEO"].status is SlotStatus.STALE
    assert production.slots["slot:SC01:START_FRAME"].status is SlotStatus.STALE
    assert production.slots["slot:SC01:END_FRAME"].status is SlotStatus.STALE
    assert production.slots["slot-ref-end"].status is SlotStatus.LOCKED


def test_v2_install_conflict_leaves_caller_registry_unchanged() -> None:
    proposals, blueprint, plan_id = approved()
    production = world_registry(blueprint)
    production.add_slot(SceneAssetSlot(
        "slot:SC01:VIDEO",
        "project-v2",
        "SC01",
        SlotKind.VIDEO,
        True,
    ))
    before = ProductionControlSnapshotStore.snapshot(production)
    with pytest.raises(ProductError) as exc:
        ApprovedPlanProductionControlInstaller.install(
            proposal_registry=proposals,
            plan_id=plan_id,
            blueprint=blueprint,
            project_id="project-v2",
            production_registry=production,
        )
    assert exc.value.code == "ERR_PRODUCTION_SLOT_CONFLICT"
    assert ProductionControlSnapshotStore.snapshot(production) == before


def persist_foundation(root: Path):
    proposals, blueprint, plan_id = approved()
    ProductionProposalSnapshotStore.save(root / "production-proposal.json", proposals)
    ProductionControlSnapshotStore.save(root / "production-control.json", world_registry(blueprint))
    return proposals, blueprint, plan_id


def test_planning_prepare_apply_and_restart_preserve_exact_world_lock(tmp_path: Path) -> None:
    _, _, plan_id = persist_foundation(tmp_path)
    application = Task027PlanningApplication(
        project_root=tmp_path,
        project_id="project-v2",
        token_factory=lambda: "install-v2",
    )
    state = application.snapshot()
    assert state["installation"]["status"] == "NOT_INSTALLED"
    assert state["installation"]["world_lock"]["status"] == "PASS"
    prepared = application.prepare_install_plan(
        plan_id=plan_id,
        expected_proposal_snapshot_sha256=state["snapshot_sha256"],
        expected_production_snapshot_sha256=state["installation"]["production"]["snapshot_sha256"],
    )
    assert prepared["world_lock"]["status"] == "PASS"
    installed = application.apply_install_plan(confirmation_id="install-v2")
    assert installed["application"]["installation"]["status"] == "INSTALLED"
    reopened = Task027PlanningApplication(
        project_root=tmp_path,
        project_id="project-v2",
    ).snapshot()
    assert reopened["installation"]["status"] == "INSTALLED"
    assert reopened["installation"]["trace"]["world_lock_binding_count"] == 2


def test_planning_install_confirmation_is_consumed_after_world_lock_drift(tmp_path: Path) -> None:
    _, _, plan_id = persist_foundation(tmp_path)
    application = Task027PlanningApplication(
        project_root=tmp_path,
        project_id="project-v2",
        token_factory=lambda: "install-v2",
    )
    state = application.snapshot()
    application.prepare_install_plan(
        plan_id=plan_id,
        expected_proposal_snapshot_sha256=state["snapshot_sha256"],
        expected_production_snapshot_sha256=state["installation"]["production"]["snapshot_sha256"],
    )
    path = tmp_path / "production-control.json"
    production = ProductionControlSnapshotStore.load(path)
    previous = ProductionControlSnapshotStore.snapshot(production)["snapshot_sha256"]
    production.mark_stale(EntityRef(EntityType.SLOT, "slot-ref-start"), include_root=True)
    ProductionControlSnapshotStore.save(
        path,
        production,
        expected_previous_snapshot_sha256=previous,
    )
    with pytest.raises(ProductError) as stale:
        application.apply_install_plan(confirmation_id="install-v2")
    assert stale.value.code == "ERR_PRODUCTION_APPLICATION_SNAPSHOT_CONFLICT"
    with pytest.raises(ProductError) as consumed:
        application.apply_install_plan(confirmation_id="install-v2")
    assert consumed.value.code == "ERR_PLANNING_APPLICATION_INSTALL_CONFIRMATION_INVALID"


def test_installed_planning_restart_reports_stale_world_lock_without_crashing(tmp_path: Path) -> None:
    _, _, plan_id = persist_foundation(tmp_path)
    application = Task027PlanningApplication(
        project_root=tmp_path,
        project_id="project-v2",
        token_factory=lambda: "install-v2",
    )
    state = application.snapshot()
    application.prepare_install_plan(
        plan_id=plan_id,
        expected_proposal_snapshot_sha256=state["snapshot_sha256"],
        expected_production_snapshot_sha256=state["installation"]["production"]["snapshot_sha256"],
    )
    application.apply_install_plan(confirmation_id="install-v2")

    path = tmp_path / "production-control.json"
    production = ProductionControlSnapshotStore.load(path)
    previous = ProductionControlSnapshotStore.snapshot(production)["snapshot_sha256"]
    production.mark_stale(EntityRef(EntityType.SLOT, "slot-ref-start"), include_root=True)
    ProductionControlSnapshotStore.save(path, production, expected_previous_snapshot_sha256=previous)

    recovered = Task027PlanningApplication(
        project_root=tmp_path,
        project_id="project-v2",
    ).snapshot()
    assert recovered["installation"]["status"] == "WORLD_LOCK_STALE"
    assert recovered["installation"]["world_lock"]["recovery_required"] is True
    assert recovered["installation"]["trace"] is None
