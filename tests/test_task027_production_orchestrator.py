from __future__ import annotations

import pytest

from ai_video_production.production_blueprint import (
    AssetSourceStrategy,
    BlueprintReference,
    BlueprintScene,
    CameraMotion,
    GenerationRisk,
    ProductionBlueprint,
    ReferenceKind,
    ReferenceStatus,
    SceneAudioPlan,
)
from ai_video_production.production_control import (
    AssetCandidate,
    CandidateLifecycle,
    ProductionControlRegistry,
    SlotKind,
)
from ai_video_production.production_orchestrator import (
    BlueprintProductionControlCompiler,
    GenerationQueueAdmissionService,
)
from ai_video_production.shot_feasibility import (
    CheckState,
    ContinuityType,
    SceneGenerationReferenceSpec,
    ShotFeasibilityGate,
    StartFrameSource,
)
from ai_video_production.timebase import FrameRate
from ai_video_production.errors import ProductError


SHA = "sha256:" + "a" * 64


def blueprint() -> ProductionBlueprint:
    refs = (BlueprintReference("REF-ROOM", ReferenceKind.SPACE, ReferenceStatus.LOCKED, "room.png"),)
    scenes = (
        BlueprintScene(
            "SC01", 0, 120, "opening", AssetSourceStrategy.AI_GENERATED,
            GenerationRisk.A_LOW_TEXT, CameraMotion.SUBTLE, ("REF-ROOM",),
            SceneAudioPlan(narration=True, sound_effects=("whoosh", "hit"), bgm=True),
        ),
        BlueprintScene(
            "SC02", 120, 240, "real demo", AssetSourceStrategy.REAL_CAPTURE,
            GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, ("REF-ROOM",),
            SceneAudioPlan(narration=False, sound_effects=(), bgm=False),
        ),
    )
    return ProductionBlueprint("BP-TEST01", "Test", FrameRate(30), 240, refs, scenes)


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
    }
    return ShotFeasibilityGate.assess(spec, human_reviewed_checks=checks)


def test_blueprint_compiles_stable_scene_asset_slots():
    plan = BlueprintProductionControlCompiler.compile(blueprint(), project_id="project-1")
    sc1 = [slot for slot in plan.slots if slot.scene_id == "SC01"]
    kinds = [slot.slot_kind for slot in sc1]
    assert kinds.count(SlotKind.VIDEO) == 1
    assert kinds.count(SlotKind.START_FRAME) == 1
    assert kinds.count(SlotKind.END_FRAME) == 1
    assert kinds.count(SlotKind.SE) == 2
    assert kinds.count(SlotKind.BGM) == 1
    assert kinds.count(SlotKind.NARRATION) == 1
    sc2 = [slot for slot in plan.slots if slot.scene_id == "SC02"]
    assert [slot.slot_kind for slot in sc2] == [SlotKind.VIDEO]
    assert plan.to_dict()["provider_execution_started"] is False


def test_generation_queue_blocks_until_required_input_slots_are_locked():
    plan = BlueprintProductionControlCompiler.compile(blueprint(), project_id="project-1")
    registry = ProductionControlRegistry(); BlueprintProductionControlCompiler.install(plan, registry)
    required = ("slot:SC01:START_FRAME",)
    result = GenerationQueueAdmissionService.evaluate(
        scene_id="SC01", slot_id="slot:SC01:VIDEO", plan_approved=True,
        feasibility=feasibility_pass(), required_input_slot_ids=required,
        registry=registry, cost_authorized=True,
    )
    assert result.status == "BLOCKED"
    assert result.missing_locked_slot_ids == required


def test_generation_queue_becomes_ready_only_after_human_accepted_lock_and_cost_authority():
    plan = BlueprintProductionControlCompiler.compile(blueprint(), project_id="project-1")
    registry = ProductionControlRegistry(); BlueprintProductionControlCompiler.install(plan, registry)
    candidate = AssetCandidate("candidate-start", "slot:SC01:START_FRAME", "asset-start", SHA, 1)
    registry.add_candidate(candidate)
    registry.transition_candidate("candidate-start", CandidateLifecycle.READY_FOR_AUDIT)
    registry.transition_candidate("candidate-start", CandidateLifecycle.ACCEPTED)
    slot = registry.slots["slot:SC01:START_FRAME"]
    registry.lock_candidate(slot_id=slot.slot_id, candidate_id="candidate-start", expected_revision=slot.revision)
    ready = GenerationQueueAdmissionService.require_ready(
        scene_id="SC01", slot_id="slot:SC01:VIDEO", plan_approved=True,
        feasibility=feasibility_pass(), required_input_slot_ids=(slot.slot_id,),
        registry=registry, cost_authorized=True,
    )
    assert ready.ready is True

    with pytest.raises(ProductError) as exc:
        GenerationQueueAdmissionService.require_ready(
            scene_id="SC01", slot_id="slot:SC01:VIDEO", plan_approved=True,
            feasibility=feasibility_pass(), required_input_slot_ids=(slot.slot_id,),
            registry=registry, cost_authorized=False,
        )
    assert exc.value.code == "ERR_GENERATION_QUEUE_NOT_READY"


def test_blueprint_install_creates_plan_scene_slot_trace_edges():
    plan = BlueprintProductionControlCompiler.compile(blueprint(), project_id="project-1")
    registry = ProductionControlRegistry(); BlueprintProductionControlCompiler.install(plan, registry)
    plan_scene = registry.edges["dep:BP-TEST01:SC01"]
    assert plan_scene.from_ref.entity_type.value == "PLAN"
    assert plan_scene.from_ref.entity_id == "BP-TEST01"
    assert plan_scene.to_ref.entity_type.value == "SCENE"
    slot_edge = registry.edges["dep:SC01:slot:SC01:START_FRAME"]
    assert slot_edge.from_ref.entity_id == "SC01"
    assert slot_edge.to_ref.entity_id == "slot:SC01:START_FRAME"
    assert plan.to_dict()["dependency_edges"]


def test_blueprint_plan_stale_propagates_through_scene_to_slots_without_auto_regeneration():
    plan = BlueprintProductionControlCompiler.compile(blueprint(), project_id="project-1")
    registry = ProductionControlRegistry(); BlueprintProductionControlCompiler.install(plan, registry)
    from ai_video_production.production_control import EntityRef, EntityType, SlotStatus
    result = registry.mark_stale(EntityRef(EntityType.PLAN, "BP-TEST01"))
    assert registry.slots["slot:SC01:START_FRAME"].status is SlotStatus.STALE
    assert registry.slots["slot:SC02:VIDEO"].status is SlotStatus.STALE
    assert result.to_dict()["automatic_regeneration_started"] is False


def test_generation_queue_rejects_unknown_target_slot_before_cost_or_provider_work():
    plan = BlueprintProductionControlCompiler.compile(blueprint(), project_id="project-1")
    registry = ProductionControlRegistry(); BlueprintProductionControlCompiler.install(plan, registry)
    with pytest.raises(ProductError) as exc:
        GenerationQueueAdmissionService.evaluate(
            scene_id="SC01", slot_id="slot:missing", plan_approved=True,
            feasibility=feasibility_pass(), required_input_slot_ids=(), registry=registry,
            cost_authorized=True,
        )
    assert exc.value.code == "ERR_GENERATION_TARGET_SLOT_NOT_FOUND"


def test_generation_queue_rejects_scene_slot_identity_mismatch():
    plan = BlueprintProductionControlCompiler.compile(blueprint(), project_id="project-1")
    registry = ProductionControlRegistry(); BlueprintProductionControlCompiler.install(plan, registry)
    with pytest.raises(ProductError) as exc:
        GenerationQueueAdmissionService.evaluate(
            scene_id="SC02", slot_id="slot:SC01:VIDEO", plan_approved=True,
            feasibility=feasibility_pass(), required_input_slot_ids=(), registry=registry,
            cost_authorized=True,
        )
    assert exc.value.code == "ERR_GENERATION_TARGET_SCENE_MISMATCH"


def test_generation_queue_rejects_locked_target_slot():
    plan = BlueprintProductionControlCompiler.compile(blueprint(), project_id="project-1")
    registry = ProductionControlRegistry(); BlueprintProductionControlCompiler.install(plan, registry)
    target = "slot:SC01:VIDEO"
    registry.add_candidate(AssetCandidate("candidate-video", target, "asset-video", SHA, 1))
    registry.transition_candidate("candidate-video", CandidateLifecycle.READY_FOR_AUDIT)
    registry.transition_candidate("candidate-video", CandidateLifecycle.ACCEPTED)
    slot = registry.slots[target]
    registry.lock_candidate(slot_id=target, candidate_id="candidate-video", expected_revision=slot.revision)
    with pytest.raises(ProductError) as exc:
        GenerationQueueAdmissionService.evaluate(
            scene_id="SC01", slot_id=target, plan_approved=True,
            feasibility=feasibility_pass(), required_input_slot_ids=(), registry=registry,
            cost_authorized=True,
        )
    assert exc.value.code == "ERR_GENERATION_TARGET_SLOT_NOT_MUTABLE"
