from __future__ import annotations

from decimal import Decimal

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.planning_workspace import Task027PlanningWorkspaceService
from ai_video_production.production_blueprint import (
    AssetSourceStrategy, BlueprintReference, BlueprintScene, CameraMotion,
    GenerationRisk, ProductionBlueprint, ReferenceKind, ReferenceStatus,
)
from ai_video_production.production_proposal import (
    CreationIntent, ProductionGoApprovalService, ProductionProposalRegistry,
    ProductionProposalRevision, ProposalSection, ProviderPolicyBinding,
    ReferenceAssetBinding,
)
from ai_video_production.timebase import FrameRate

SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64


def setup_registry() -> ProductionProposalRegistry:
    registry = ProductionProposalRegistry()
    intent = CreationIntent(
        "INTENT-DEMO", 1, "Intro", "Viewers", "YouTube", "16:9", Decimal("10"),
        "Calm", "Explain", "ja-JP", budget_ceiling=Decimal("20"),
    )
    registry.add_intent(intent)
    refs = (
        BlueprintReference("PERSON-A", ReferenceKind.PERSON, ReferenceStatus.LOCKED, "person.png"),
        BlueprintReference("SPACE-A", ReferenceKind.SPACE, ReferenceStatus.AVAILABLE, "space.png"),
    )
    scene = BlueprintScene(
        "SC01", 0, 300, "Opening", AssetSourceStrategy.REUSE_EXISTING,
        GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, ("PERSON-A", "SPACE-A"),
    )
    bp = ProductionBlueprint("BP-DEMO-001", "Demo", FrameRate(30, 1), 300, refs, (scene,))
    registry.add_proposal(ProductionProposalRevision(
        "PROPOSAL-DEMO", 1, intent.to_dict()["intent_sha256"], bp,
        (
            ProposalSection("concept", "CONCEPT", "Concept", "First concept"),
            ProposalSection("script", "SCRIPT", "Script", "First script"),
        ),
        ProviderPolicyBinding("policy", "1", SHA_C), Decimal("2"), Decimal("10"), "USD",
    ))
    return registry


def reference_bindings():
    return (
        ReferenceAssetBinding("PERSON-A", "asset-person", SHA_A),
        ReferenceAssetBinding("SPACE-A", "asset-space", SHA_B),
    )


def test_planning_workspace_projects_latest_proposal_and_go_state() -> None:
    registry = setup_registry()
    go = ProductionGoApprovalService(registry, token_factory=lambda: "go")
    workspace = Task027PlanningWorkspaceService(registry, go_service=go)
    before = workspace.snapshot(proposal_id="PROPOSAL-DEMO")
    assert before["go_status"] == "GO_REQUIRED"
    assert before["changed_section_ids_from_previous"] == []
    prepared = workspace.prepare_go(
        proposal_id="PROPOSAL-DEMO", proposal_revision=1,
        reference_bindings=reference_bindings(), cost_ceiling=12,
        rights_warnings_acknowledged=False,
    )
    assert prepared["human_go_required"] is True
    result = workspace.approve_go(confirmation_id="go", approved_by="owner")
    assert result["workspace"]["go_status"] == "APPROVED"
    assert result["provider_execution_started"] is False
    assert result["resolve_mutation_started"] is False


def test_new_proposal_revision_requires_new_go_and_lists_changed_sections() -> None:
    registry = setup_registry()
    go = ProductionGoApprovalService(registry, token_factory=lambda: "go")
    workspace = Task027PlanningWorkspaceService(registry, go_service=go)
    workspace.prepare_go(
        proposal_id="PROPOSAL-DEMO", proposal_revision=1,
        reference_bindings=reference_bindings(), cost_ceiling=12,
        rights_warnings_acknowledged=False,
    )
    workspace.approve_go(confirmation_id="go", approved_by="owner")
    first = registry.latest_proposal("PROPOSAL-DEMO")
    registry.add_proposal(ProductionProposalRevision(
        "PROPOSAL-DEMO", 2, first.intent_sha256, first.blueprint,
        (
            ProposalSection("concept", "CONCEPT", "Concept", "First concept"),
            ProposalSection("script", "SCRIPT", "Script", "Revised script"),
        ),
        first.provider_policy, first.estimated_cost_min, first.estimated_cost_max,
        first.currency, parent_proposal_sha256=first.to_dict()["proposal_sha256"],
    ))
    state = workspace.snapshot(proposal_id="PROPOSAL-DEMO")
    assert state["latest_revision"] == 2
    assert state["go_status"] == "GO_REQUIRED"
    assert state["new_go_required_after_revision"] is True
    assert state["changed_section_ids_from_previous"] == ["script"]
    assert len(state["prior_approved_plan_ids"]) == 1


def test_planning_workspace_fails_if_registered_intent_state_is_missing() -> None:
    registry = setup_registry()
    registry.intents.clear()  # simulate damaged/recovered cross-store state
    workspace = Task027PlanningWorkspaceService(registry)
    with pytest.raises(ProductError) as exc:
        workspace.snapshot(proposal_id="PROPOSAL-DEMO")
    assert exc.value.code == "ERR_PLANNING_WORKSPACE_INTENT_MISSING"
