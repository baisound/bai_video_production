from __future__ import annotations

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.shot_feasibility import (
    AssessmentStatus,
    CheckState,
    ContinuityType,
    SceneGenerationReferenceSpec,
    ShotFeasibilityGate,
    StartFrameSource,
)


SHA = "sha256:" + "a" * 64


def spec(**overrides):
    values = dict(
        scene_id="P01",
        continuity_type=ContinuityType.CUT,
        character_required=True,
        character_identity_profile_id="CHAR-1",
        character_reference_asset_ids=("ASSET-CHAR",),
        room_master_asset_id="ASSET-ROOM",
        room_shot_reference_asset_id="ASSET-SHOT",
        style_reference_asset_id=None,
        required_visible=("FACE", "NOTEBOOK", "MONITOR"),
        subject_orientation="THREE_QUARTER_FRONT_TO_CAMERA",
        camera_semantic="DESK_FRONT_LEFT",
        start_frame_source=StartFrameSource.NEW,
        prohibited_changes=("ADD_DESK", "MOVE_FURNITURE"),
    )
    values.update(overrides)
    return SceneGenerationReferenceSpec(**values)


def all_human_pass():
    return {
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


def test_deterministic_contract_alone_never_claims_geometry_pass():
    assessment = ShotFeasibilityGate.assess(spec())
    assert assessment.status is AssessmentStatus.REVIEW_REQUIRED
    assert assessment.to_dict()["automatic_geometry_proof_claimed"] is False


def test_human_reviewed_structural_pass_becomes_generation_ready():
    assessment = ShotFeasibilityGate.assess(spec(), human_reviewed_checks=all_human_pass())
    assert assessment.status is AssessmentStatus.PASS
    ShotFeasibilityGate.require_generation_ready(assessment)
    assert assessment.to_dict()["reference_spec_sha256"] == spec().to_dict()["reference_spec_sha256"]
    assert assessment.to_dict()["assessment_sha256"] == assessment.to_dict()["assessment_sha256"]


def test_promotion_checks_are_required_and_partial_review_never_passes():
    checks = all_human_pass()
    checks.pop("depth_order_valid")
    assessment = ShotFeasibilityGate.assess(spec(), human_reviewed_checks=checks)
    assert assessment.status is AssessmentStatus.REVIEW_REQUIRED


def test_required_new_desk_fails_gate_even_when_other_checks_pass():
    checks = all_human_pass()
    checks["prohibited_change_not_required"] = CheckState.FAIL
    assessment = ShotFeasibilityGate.assess(spec(), human_reviewed_checks=checks, blocking_reasons=("PROHIBITED_GEOMETRY_CHANGE_REQUIRED",))
    assert assessment.status is AssessmentStatus.FAIL
    with pytest.raises(ProductError) as exc:
        ShotFeasibilityGate.require_generation_ready(assessment)
    assert exc.value.code == "ERR_SHOT_FEASIBILITY_NOT_READY"


def test_room_overview_without_scene_shot_reference_fails_character_in_room_contract():
    assessment = ShotFeasibilityGate.assess(spec(room_shot_reference_asset_id=None), human_reviewed_checks=all_human_pass())
    assert assessment.status is AssessmentStatus.FAIL
    assert "REFERENCE_ROLE_CONFLICT" in assessment.blocking_reasons


def test_direct_continuation_requires_exact_previous_end_asset_and_hash():
    direct = spec(
        continuity_type=ContinuityType.DIRECT_CONTINUATION,
        start_frame_source=StartFrameSource.PREV_END,
        previous_end_asset_id="ASSET-END",
        previous_end_sha256=SHA,
        start_asset_id="ASSET-END",
        start_asset_sha256=SHA,
    )
    assessment = ShotFeasibilityGate.assess(direct, human_reviewed_checks=all_human_pass())
    assert assessment.status is AssessmentStatus.PASS


def test_direct_continuation_new_start_generation_fails_and_human_cannot_override_contract():
    direct = spec(
        continuity_type=ContinuityType.DIRECT_CONTINUATION,
        start_frame_source=StartFrameSource.NEW,
        previous_end_asset_id="ASSET-END",
        previous_end_sha256=SHA,
        start_asset_id="ASSET-NEW",
        start_asset_sha256="sha256:" + "b" * 64,
    )
    checks = all_human_pass() | {"continuity_contract_valid": CheckState.PASS}
    assessment = ShotFeasibilityGate.assess(direct, human_reviewed_checks=checks)
    assert assessment.status is AssessmentStatus.FAIL
    assert assessment.checks["continuity_contract_valid"] is CheckState.FAIL
