from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from ai_video_production.approved_plan_orchestration import ApprovedPlanProductionControlInstaller
from ai_video_production.audio_workspace import AudioWorkspaceRegistry
from ai_video_production.audio_workspace_store import AudioWorkspaceSnapshotStore
from ai_video_production.candidate_audit import CandidateAuditRegistry
from ai_video_production.candidate_audit_store import CandidateAuditSnapshotStore
from ai_video_production.continuity_registry import ContinuityRegistry
from ai_video_production.continuity_registry_store import ContinuityRegistryStore
from ai_video_production.errors import ProductError
from ai_video_production.planning_production_bundle import PlanningProductionBundleStore
from ai_video_production.production_blueprint import AssetSourceStrategy, BlueprintScene, CameraMotion, GenerationRisk, ProductionBlueprint
from ai_video_production.production_budget import ProductionBudgetLedger
from ai_video_production.production_budget_store import ProductionBudgetSnapshotStore
from ai_video_production.production_bundle_store import ProductionBundleManifestStore
from ai_video_production.production_control import ProductionControlRegistry
from ai_video_production.production_control_store import ProductionControlSnapshotStore
from ai_video_production.production_proposal import (
    CreationIntent, ProductionGoApprovalService, ProductionProposalRegistry,
    ProductionProposalRevision, ProposalSection, ProviderPolicyBinding,
)
from ai_video_production.production_proposal_store import ProductionProposalSnapshotStore
from ai_video_production.production_session_bundle import ProductionSessionBundleStore
from ai_video_production.prompt_registry import PromptEntity, PromptGenerationRegistry
from ai_video_production.prompt_registry_store import PromptRegistrySnapshotStore
from ai_video_production.timebase import FrameRate

POLICY_SHA = "sha256:" + "c" * 64
PROMPT_SHA = "sha256:" + "d" * 64


def write_state(root: Path):
    proposals = ProductionProposalRegistry()
    intent = CreationIntent("INTENT-SESSION", 1, "Intro", "Viewers", "YouTube", "16:9", Decimal("2"), "Calm", "Explain", "ja-JP", budget_ceiling=Decimal("5"))
    proposals.add_intent(intent)
    scene = BlueprintScene("SC01", 0, 60, "opening", AssetSourceStrategy.AI_GENERATED, GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, ())
    blueprint = ProductionBlueprint("BP-SESSION1", "Session", FrameRate(30), 60, (), (scene,))
    proposals.add_proposal(ProductionProposalRevision(
        "PROPOSAL-SESSION", 1, intent.to_dict()["intent_sha256"], blueprint,
        (ProposalSection("concept", "CONCEPT", "Concept", "Opening"),),
        ProviderPolicyBinding("policy", "1", POLICY_SHA), Decimal("1"), Decimal("2"), "USD",
    ))
    go = ProductionGoApprovalService(proposals, token_factory=lambda: "go")
    go.prepare_go(proposal_id="PROPOSAL-SESSION", proposal_revision=1, reference_bindings=(), cost_ceiling="3", rights_warnings_acknowledged=False)
    plan = go.approve_go(confirmation_id="go", approved_by="owner")
    budget = ProductionBudgetLedger.from_approved_plan(plan)
    production = ProductionControlRegistry()
    ApprovedPlanProductionControlInstaller.install(proposal_registry=proposals, plan_id=plan.plan_id, blueprint=blueprint, project_id="project-1", production_registry=production)

    audits = CandidateAuditRegistry()
    prompts = PromptGenerationRegistry()
    continuity = ContinuityRegistry()
    audio = AudioWorkspaceRegistry()

    ProductionProposalSnapshotStore.save(
        root / "production-proposal.json",
        proposals,
        project_id="project-1",
    )
    ProductionBudgetSnapshotStore.save(root / "production-budget.json", budget)
    ProductionControlSnapshotStore.save(root / "production-control.json", production)
    CandidateAuditSnapshotStore.save(root / "candidate-audit.json", audits)
    PromptRegistrySnapshotStore.save(root / "prompt-registry.json", prompts)
    ContinuityRegistryStore.save(root / "continuity-registry.json", continuity)
    AudioWorkspaceSnapshotStore.save(root / "audio-workspace.json", audio)

    planning_doc = PlanningProductionBundleStore.build(proposals=proposals, plan_id=plan.plan_id, budget=budget, production=production, project_id="project-1")
    PlanningProductionBundleStore.save(root / "planning-production-bundle.json", planning_doc)
    production_doc = ProductionBundleManifestStore.build(production=production, audits=audits, prompts=prompts, continuity=continuity, audio=audio)
    ProductionBundleManifestStore.save(root / "production-bundle.json", production_doc)
    session_doc = ProductionSessionBundleStore.build(planning_manifest=planning_doc, production_manifest=production_doc)
    ProductionSessionBundleStore.save(root / "production-session.json", session_doc)
    return proposals, plan, budget, production, audits, prompts, continuity, audio, session_doc


def test_production_session_bundle_recovers_upstream_and_downstream_on_same_production_snapshot(tmp_path: Path) -> None:
    _proposals, plan, _budget, _production, _audits, _prompts, _continuity, _audio, session_doc = write_state(tmp_path)
    recovered = ProductionSessionBundleStore.recover(tmp_path)
    assert recovered.planning.trace.plan_id == plan.plan_id
    assert recovered.production.validation.to_dict()["status"] == "PASS"
    assert recovered.manifest_sha256 == session_doc["manifest_sha256"]


def test_production_session_bundle_rejects_changed_downstream_manifest(tmp_path: Path) -> None:
    _proposals, _plan, _budget, production, audits, prompts, continuity, audio, _session_doc = write_state(tmp_path)
    old_prompt = PromptRegistrySnapshotStore.snapshot(prompts)["snapshot_sha256"]
    prompts.add_prompt(PromptEntity("prompt-1", 1, "future", PROMPT_SHA, "profile", "1", ("keep",), scene_id="SC01", slot_id="slot:SC01:VIDEO"))
    PromptRegistrySnapshotStore.save(tmp_path / "prompt-registry.json", prompts, expected_previous_snapshot_sha256=old_prompt)
    old_manifest = ProductionBundleManifestStore.load_document(tmp_path / "production-bundle.json")
    new_manifest = ProductionBundleManifestStore.build(production=production, audits=audits, prompts=prompts, continuity=continuity, audio=audio)
    ProductionBundleManifestStore.save(
        tmp_path / "production-bundle.json", new_manifest,
        expected_previous_manifest_sha256=old_manifest["manifest_sha256"],
    )
    with pytest.raises(ProductError) as exc:
        ProductionSessionBundleStore.recover(tmp_path)
    assert exc.value.code == "ERR_PRODUCTION_SESSION_CHILD_MANIFEST_CHANGED"
