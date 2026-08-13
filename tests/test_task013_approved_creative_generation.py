from __future__ import annotations

from decimal import Decimal

import pytest

from ai_video_production.ai_connections import (
    AiConnectionProfile, AiWorkload, ConnectionAvailability, CostClass,
    ModelRoute, ProviderFamily, SelectionMode,
)
from ai_video_production.approved_creative_generation import ApprovedCreativeGenerationPlanner
from ai_video_production.approved_plan_orchestration import ApprovedPlanProductionControlInstaller
from ai_video_production.creative_generation import CreativeGenerationMode, CreativeGenerationRequest
from ai_video_production.errors import ProductError
from ai_video_production.production_blueprint import (
    AssetSourceStrategy, BlueprintScene, CameraMotion, GenerationRisk, ProductionBlueprint,
)
from ai_video_production.production_budget import ProductionBudgetLedger
from ai_video_production.production_control import ProductionControlRegistry
from ai_video_production.production_proposal import (
    CreationIntent, ProductionGoApprovalService, ProductionProposalRegistry,
    ProductionProposalRevision, ProposalSection, ProviderPolicyBinding,
)
from ai_video_production.prompt_registry import PromptEntity
from ai_video_production.shot_feasibility import CheckState, ShotFeasibilityAssessment
from ai_video_production.timebase import FrameRate

SHA = "sha256:" + "a" * 64


def route(*, paid: bool):
    return ModelRoute(
        "cloud" if paid else "local", AiWorkload.VIDEO,
        ProviderFamily.RUNWAY if paid else ProviderFamily.COMFYUI,
        "provider", "model", CostClass.CLOUD_PAID_AI if paid else CostClass.LOCAL_FREE_AI,
        credential_ref="credential://runway/default" if paid else None,
        capabilities=("IMAGE_TO_VIDEO",),
    )


def profile(*, paid: bool, version: str = "1"):
    return AiConnectionProfile("profile", version, SelectionMode.AUTO, (route(paid=paid),))


def feasibility():
    names = (
        "subject_position_exists", "orientation_camera_compatible", "required_visible_coexists",
        "prohibited_change_not_required", "shot_reference_matches_final_camera",
        "reference_roles_valid", "continuity_contract_valid",
    )
    return ShotFeasibilityAssessment("SC01", {name: CheckState.PASS for name in names}, "TEST")


def approved(active_profile: AiConnectionProfile):
    proposals = ProductionProposalRegistry()
    intent = CreationIntent(
        "INTENT-GEN", 1, "Intro", "Viewers", "YouTube", "16:9", Decimal("2"),
        "Calm", "Opening", "ja-JP", budget_ceiling=Decimal("10"),
    )
    proposals.add_intent(intent)
    scene = BlueprintScene(
        "SC01", 0, 60, "opening", AssetSourceStrategy.AI_GENERATED,
        GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, (),
    )
    blueprint = ProductionBlueprint("BP-GEN001", "Gen", FrameRate(30), 60, (), (scene,))
    proposals.add_proposal(ProductionProposalRevision(
        "PROPOSAL-GEN", 1, intent.to_dict()["intent_sha256"], blueprint,
        (ProposalSection("concept", "CONCEPT", "Concept", "Opening"),),
        ProviderPolicyBinding(active_profile.profile_id, active_profile.profile_version, active_profile.to_dict()["profile_sha256"]),
        Decimal("1"), Decimal("5"), "USD",
    ))
    go = ProductionGoApprovalService(proposals, token_factory=lambda: "go")
    go.prepare_go(
        proposal_id="PROPOSAL-GEN", proposal_revision=1, reference_bindings=(),
        cost_ceiling="6", rights_warnings_acknowledged=False,
    )
    plan = go.approve_go(confirmation_id="go", approved_by="owner")
    production = ProductionControlRegistry()
    ApprovedPlanProductionControlInstaller.install(
        proposal_registry=proposals, plan_id=plan.plan_id, blueprint=blueprint,
        project_id="project-1", production_registry=production,
    )
    return proposals, blueprint, plan, production


def request(active_profile: AiConnectionProfile, *, paid_authorized: bool):
    prompt = PromptEntity(
        "prompt-1", 1, "scene", SHA, active_profile.profile_id, active_profile.profile_version,
        ("keep",), scene_id="SC01", slot_id="slot:SC01:VIDEO",
    )
    return CreativeGenerationRequest(
        "request-1", "SC01", "slot:SC01:VIDEO", CreativeGenerationMode.IMAGE_TO_VIDEO,
        prompt, "rights://project-1/sc01", explicit_paid_execution_authorization=paid_authorized,
    )


def test_approved_local_generation_compiles_without_paid_budget_reservation() -> None:
    active = profile(paid=False)
    proposals, bp, plan, production = approved(active)
    result = ApprovedCreativeGenerationPlanner.compile(
        request(active, paid_authorized=False), profile=active,
        availability=ConnectionAvailability(frozenset({"local"})),
        proposal_registry=proposals, approved_plan_id=plan.plan_id, blueprint=bp,
        feasibility=feasibility(), production_registry=production,
    )
    assert result.ready_for_provider_execution is True
    assert result.paid_execution_required is False
    assert result.to_dict()["provider_execution_started"] is False


def test_approved_paid_generation_requires_explicit_authorization_and_budget_reservation() -> None:
    active = profile(paid=True)
    proposals, bp, plan, production = approved(active)
    availability = ConnectionAvailability(frozenset({"cloud"}), frozenset({"credential://runway/default"}))
    with pytest.raises(ProductError) as exc:
        ApprovedCreativeGenerationPlanner.compile(
            request(active, paid_authorized=False), profile=active, availability=availability,
            proposal_registry=proposals, approved_plan_id=plan.plan_id, blueprint=bp,
            feasibility=feasibility(), production_registry=production,
        )
    assert exc.value.code == "ERR_GENERATION_PAID_EXECUTION_NOT_AUTHORIZED"

    with pytest.raises(ProductError) as exc:
        ApprovedCreativeGenerationPlanner.compile(
            request(active, paid_authorized=True), profile=active, availability=availability,
            proposal_registry=proposals, approved_plan_id=plan.plan_id, blueprint=bp,
            feasibility=feasibility(), production_registry=production,
        )
    assert exc.value.code == "ERR_APPROVED_GENERATION_BUDGET_RESERVATION_REQUIRED"

    ledger = ProductionBudgetLedger.from_approved_plan(plan)
    ledger.reserve(operation_id="request-1", estimated_amount="2")
    result = ApprovedCreativeGenerationPlanner.compile(
        request(active, paid_authorized=True), profile=active, availability=availability,
        proposal_registry=proposals, approved_plan_id=plan.plan_id, blueprint=bp,
        feasibility=feasibility(), production_registry=production,
        budget_ledger=ledger, budget_operation_id="request-1",
    )
    assert result.ready_for_provider_execution is True
    assert result.paid_execution_authorized is True


def test_approved_generation_rejects_connection_profile_drift_after_go() -> None:
    approved_profile = profile(paid=False, version="1")
    proposals, bp, plan, production = approved(approved_profile)
    drifted = profile(paid=False, version="2")
    with pytest.raises(ProductError) as exc:
        ApprovedCreativeGenerationPlanner.compile(
            request(drifted, paid_authorized=False), profile=drifted,
            availability=ConnectionAvailability(frozenset({"local"})),
            proposal_registry=proposals, approved_plan_id=plan.plan_id, blueprint=bp,
            feasibility=feasibility(), production_registry=production,
        )
    assert exc.value.code == "ERR_APPROVED_GENERATION_PROFILE_MISMATCH"
