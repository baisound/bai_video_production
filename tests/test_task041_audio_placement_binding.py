from __future__ import annotations

import pytest

from ai_video_production.audio_workspace import AudioWorkspaceRegistry, PlacementDecision, PlacementReview
from ai_video_production.audio_workspace_placement_binding import AudioWorkspacePlacementBinding
from ai_video_production.errors import ProductError
from ai_video_production.production_control import AssetCandidate, CandidateLifecycle, ProductionControlRegistry, SceneAssetSlot, SlotKind


SHA = "sha256:" + "a" * 64


def production(*, lock=True):
    r = ProductionControlRegistry()
    r.add_slot(SceneAssetSlot("slot-1", "project-1", "scene-1", SlotKind.BGM, True))
    r.add_candidate(AssetCandidate("candidate-1", "slot-1", "asset-bgm", SHA, 1))
    r.transition_candidate("candidate-1", CandidateLifecycle.READY_FOR_AUDIT)
    r.transition_candidate("candidate-1", CandidateLifecycle.ACCEPTED)
    if lock:
        slot = r.slots["slot-1"]
        r.lock_candidate(slot_id="slot-1", candidate_id="candidate-1", expected_revision=slot.revision)
    return r


def workspace(decision=PlacementDecision.ACCEPT, *, gain_db=None):
    r = AudioWorkspaceRegistry()
    r.add_placement(PlacementReview("placement-1", "candidate-1", 120, 300, "BGM", decision, gain_db))
    return r


def test_human_accepted_locked_audio_candidate_compiles_task026_plan():
    plan = AudioWorkspacePlacementBinding.compile_accepted_placement(
        review_id="placement-1", workspace=workspace(), production=production(),
        track_index=4, source_duration_frames=300,
    )
    assert plan.asset_id == "asset-bgm"
    assert plan.effective_start_frame == 120
    assert plan.desired_duration_frames == 300
    assert plan.role.value == "BGM"
    assert plan.task010_compatible is True


def test_unaccepted_placement_cannot_compile():
    with pytest.raises(ProductError) as exc:
        AudioWorkspacePlacementBinding.compile_accepted_placement(
            review_id="placement-1", workspace=workspace(PlacementDecision.REVIEW), production=production(),
            track_index=4, source_duration_frames=300,
        )
    assert exc.value.code == "ERR_AUDIO_PLACEMENT_HUMAN_ACCEPT_REQUIRED"


def test_unlocked_candidate_cannot_be_used_as_production_audio_input():
    with pytest.raises(ProductError) as exc:
        AudioWorkspacePlacementBinding.compile_accepted_placement(
            review_id="placement-1", workspace=workspace(), production=production(lock=False),
            track_index=4, source_duration_frames=300,
        )
    assert exc.value.code == "ERR_AUDIO_PLACEMENT_CANDIDATE_NOT_LOCKED"


def test_review_gain_is_preserved_and_task010_gap_remains_explicit():
    plan = AudioWorkspacePlacementBinding.compile_accepted_placement(
        review_id="placement-1", workspace=workspace(gain_db=-6.0), production=production(),
        track_index=4, source_duration_frames=300,
    )
    assert plan.gain_db == -6.0
    assert plan.task010_compatible is False
    with pytest.raises(ProductError) as exc:
        plan.to_task010_audio_placements()
    assert exc.value.code == "ERR_AUDIO_PLACEMENT_TASK010_FEATURE_GAP"
