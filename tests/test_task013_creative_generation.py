from __future__ import annotations

import pytest

from ai_video_production.ai_connections import (
    AiConnectionProfile,
    AiWorkload,
    ConnectionAvailability,
    CostClass,
    ModelRoute,
    ProviderFamily,
    SelectionMode,
)
from ai_video_production.creative_generation import (
    CreativeGenerationMode,
    CreativeGenerationPlanner,
    CreativeGenerationRequest,
)
from ai_video_production.errors import ProductError
from ai_video_production.production_control import ProductionControlRegistry, SceneAssetSlot, SlotKind
from ai_video_production.prompt_registry import PromptEntity
from ai_video_production.shot_feasibility import (
    CheckState,
    ContinuityType,
    SceneGenerationReferenceSpec,
    ShotFeasibilityGate,
    StartFrameSource,
)


SHA = "sha256:" + "a" * 64


def feasibility_pass():
    spec = SceneGenerationReferenceSpec(
        "SC01", ContinuityType.CUT, True, "CHAR-1", ("ASSET-CHAR",),
        "ASSET-ROOM", "ASSET-SHOT", None, ("FACE", "MONITOR"),
        "THREE_QUARTER", "DESK_FRONT", StartFrameSource.NEW,
    )
    checks = {
        "subject_position_exists": CheckState.PASS,
        "orientation_camera_compatible": CheckState.PASS,
        "required_visible_coexists": CheckState.PASS,
        "prohibited_change_not_required": CheckState.PASS,
        "shot_reference_matches_final_camera": CheckState.PASS,
        "task_axis_valid": CheckState.PASS,
        "depth_order_valid": CheckState.PASS,
        "occlusion_valid": CheckState.PASS,
        "furniture_integrity_valid": CheckState.PASS,
        "room_anchor_integrity_valid": CheckState.PASS,
        "production_gear_absent": CheckState.PASS,
        "character_identity_valid": CheckState.PASS,
    }
    return ShotFeasibilityGate.assess(spec, human_reviewed_checks=checks)


def prompt(profile_id="profile", version="1"):
    return PromptEntity(
        "prompt-sc01", 1, "SC01 video", SHA, profile_id, version,
        ("preserve_character",), scene_id="SC01", slot_id="slot:SC01:VIDEO",
        input_asset_hashes=(SHA,),
    )


def route(*, route_id="local-video", cost=CostClass.LOCAL_FREE_AI, capability="IMAGE_TO_VIDEO", credential_ref=None):
    return ModelRoute(
        route_id, AiWorkload.VIDEO, ProviderFamily.COMFYUI if cost is CostClass.LOCAL_FREE_AI else ProviderFamily.RUNWAY,
        "provider", "model", cost, credential_ref=credential_ref, capabilities=(capability,),
    )


def registry():
    value = ProductionControlRegistry()
    value.add_slot(SceneAssetSlot("slot:SC01:VIDEO", "project-1", "SC01", SlotKind.VIDEO, True))
    return value


def test_local_free_route_compiles_without_paid_execution_authorization():
    profile = AiConnectionProfile("profile", "1", SelectionMode.AUTO, (route(),))
    request = CreativeGenerationRequest(
        "req-1", "SC01", "slot:SC01:VIDEO", CreativeGenerationMode.IMAGE_TO_VIDEO,
        prompt(), "rights://project-1/sc01", explicit_paid_execution_authorization=False,
    )
    plan = CreativeGenerationPlanner.compile(
        request, profile=profile,
        availability=ConnectionAvailability(frozenset({"local-video"})),
        plan_approved=True, feasibility=feasibility_pass(), registry=registry(),
    )
    assert plan.ready_for_provider_execution is True
    assert plan.paid_execution_required is False
    data = plan.to_dict()
    assert data["provider_execution_started"] is False
    assert data["prompt"]["body_embedded"] is False
    assert data["selected_route"]["credential_ref_persisted"] is False
    assert data == plan.to_dict()


def test_cloud_paid_route_fails_closed_without_explicit_paid_authorization():
    paid = route(
        route_id="cloud-video", cost=CostClass.CLOUD_PAID_AI,
        credential_ref="credential://runway/default",
    )
    profile = AiConnectionProfile("profile", "1", SelectionMode.AUTO, (paid,))
    request = CreativeGenerationRequest(
        "req-2", "SC01", "slot:SC01:VIDEO", CreativeGenerationMode.IMAGE_TO_VIDEO,
        prompt(), "rights://project-1/sc01", explicit_paid_execution_authorization=False,
    )
    plan = CreativeGenerationPlanner.compile(
        request, profile=profile,
        availability=ConnectionAvailability(
            frozenset({"cloud-video"}), frozenset({"credential://runway/default"})
        ),
        plan_approved=True, feasibility=feasibility_pass(), registry=registry(),
    )
    assert plan.ready_for_provider_execution is False
    assert plan.paid_execution_required is True
    assert plan.to_dict()["provider_execution_started"] is False
    with pytest.raises(ProductError) as exc:
        CreativeGenerationPlanner.require_provider_execution_authorized(plan)
    assert exc.value.code == "ERR_GENERATION_PAID_EXECUTION_NOT_AUTHORIZED"


def test_cloud_paid_route_is_plan_ready_only_when_paid_execution_is_explicitly_authorized():
    paid = route(
        route_id="cloud-video", cost=CostClass.CLOUD_PAID_AI,
        credential_ref="credential://runway/default",
    )
    profile = AiConnectionProfile("profile", "1", SelectionMode.AUTO, (paid,))
    request = CreativeGenerationRequest(
        "req-3", "SC01", "slot:SC01:VIDEO", CreativeGenerationMode.IMAGE_TO_VIDEO,
        prompt(), "rights://project-1/sc01", explicit_paid_execution_authorization=True,
    )
    plan = CreativeGenerationPlanner.compile(
        request, profile=profile,
        availability=ConnectionAvailability(
            frozenset({"cloud-video"}), frozenset({"credential://runway/default"})
        ),
        plan_approved=True, feasibility=feasibility_pass(), registry=registry(),
    )
    assert plan.paid_execution_required is True
    assert plan.ready_for_provider_execution is True
    CreativeGenerationPlanner.require_provider_execution_authorized(plan)


def test_prompt_profile_must_match_active_connection_profile_exactly():
    profile = AiConnectionProfile("profile", "1", SelectionMode.AUTO, (route(),))
    request = CreativeGenerationRequest(
        "req-4", "SC01", "slot:SC01:VIDEO", CreativeGenerationMode.IMAGE_TO_VIDEO,
        prompt(profile_id="other"), "rights://project-1/sc01",
    )
    with pytest.raises(ProductError) as exc:
        CreativeGenerationPlanner.compile(
            request, profile=profile,
            availability=ConnectionAvailability(frozenset({"local-video"})),
            plan_approved=True, feasibility=feasibility_pass(), registry=registry(),
        )
    assert exc.value.code == "ERR_GENERATION_PROFILE_ID_MISMATCH"


def test_required_capability_is_enforced_by_route_resolver():
    wrong = route(capability="TEXT_TO_VIDEO")
    profile = AiConnectionProfile("profile", "1", SelectionMode.AUTO, (wrong,))
    request = CreativeGenerationRequest(
        "req-5", "SC01", "slot:SC01:VIDEO", CreativeGenerationMode.IMAGE_TO_VIDEO,
        prompt(), "rights://project-1/sc01",
    )
    with pytest.raises(ProductError) as exc:
        CreativeGenerationPlanner.compile(
            request, profile=profile,
            availability=ConnectionAvailability(frozenset({"local-video"})),
            plan_approved=True, feasibility=feasibility_pass(), registry=registry(),
        )
    assert exc.value.code == "ERR_PROVIDER_ROUTE_UNAVAILABLE"


def test_request_rejects_prompt_bound_to_another_scene_or_slot():
    other_prompt = PromptEntity(
        "prompt-other", 1, "other", SHA, "profile", "1", ("keep",),
        scene_id="SC02", slot_id="slot:SC02:VIDEO",
    )
    with pytest.raises(ValueError, match="scene_id"):
        CreativeGenerationRequest(
            "req-6", "SC01", "slot:SC01:VIDEO", CreativeGenerationMode.IMAGE_TO_VIDEO,
            other_prompt, "rights://project-1/sc01",
        )
