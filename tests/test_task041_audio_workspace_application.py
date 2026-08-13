from __future__ import annotations

import pytest

from ai_video_production.audio_workspace import AudioWorkspaceRegistry, PlacementDecision, PlacementReview
from ai_video_production.audio_workspace_application import Task041AudioWorkspaceService
from ai_video_production.errors import ProductError
from ai_video_production.production_control import AssetCandidate, CandidateLifecycle, ProductionControlRegistry, SceneAssetSlot, SlotKind

SHA = "sha256:" + "a" * 64


def production(*, locked=True):
    value = ProductionControlRegistry()
    value.add_slot(SceneAssetSlot("slot-1", "project-1", "scene-1", SlotKind.BGM, True))
    value.add_candidate(AssetCandidate("candidate-1", "slot-1", "asset-bgm", SHA, 1))
    value.transition_candidate("candidate-1", CandidateLifecycle.READY_FOR_AUDIT)
    value.transition_candidate("candidate-1", CandidateLifecycle.ACCEPTED)
    if locked:
        slot = value.slots["slot-1"]
        value.lock_candidate(slot_id="slot-1", candidate_id="candidate-1", expected_revision=slot.revision)
    return value


def workspace():
    value = AudioWorkspaceRegistry()
    value.add_placement(PlacementReview("review-1", "candidate-1", 100, 240, "BGM", gain_db=-6.0))
    return value


def test_projection_surfaces_locked_candidate_and_preserves_gain():
    service = Task041AudioWorkspaceService(workspace=workspace(), production=production())
    row = service.snapshot()["placements"][0]
    assert row["candidate_lifecycle_state"] == "LOCKED"
    assert row["gain_db"] == -6.0
    assert row["available_human_actions"] == ["ACCEPT", "REJECT", "ALTERNATE_USE"]
    assert row["task026_compile_started"] is False


def test_human_accept_is_one_shot_and_does_not_compile_or_mutate_resolve():
    ws = workspace()
    service = Task041AudioWorkspaceService(workspace=ws, production=production(), token_factory=lambda: "accept-1")
    prepared = service.prepare_placement_decision(review_id="review-1", decision="ACCEPT")
    assert prepared["gain_db"] == -6.0
    assert ws.placements["review-1"].decision is PlacementDecision.REVIEW
    result = service.apply_placement_decision(confirmation_id="accept-1")
    assert ws.placements["review-1"].decision is PlacementDecision.ACCEPT
    assert result["task026_compile_started"] is False
    assert result["resolve_mutation_started"] is False
    with pytest.raises(ProductError) as exc:
        service.apply_placement_decision(confirmation_id="accept-1")
    assert exc.value.code == "ERR_AUDIO_WORKSPACE_CONFIRMATION_INVALID"


def test_accept_is_not_offered_or_authorized_for_unlocked_candidate():
    service = Task041AudioWorkspaceService(workspace=workspace(), production=production(locked=False), token_factory=lambda: "x")
    row = service.snapshot()["placements"][0]
    assert "ACCEPT" not in row["available_human_actions"]
    with pytest.raises(ProductError) as exc:
        service.prepare_placement_decision(review_id="review-1", decision="ACCEPT")
    assert exc.value.code == "ERR_AUDIO_WORKSPACE_ACCEPT_REQUIRES_LOCKED_CANDIDATE"


def test_confirmation_stales_when_placement_changes_after_prepare():
    ws = workspace()
    service = Task041AudioWorkspaceService(workspace=ws, production=production(), token_factory=lambda: "reject-1")
    service.prepare_placement_decision(review_id="review-1", decision="REJECT")
    ws.placements["review-1"] = PlacementReview("review-1", "candidate-1", 101, 240, "BGM", gain_db=-6.0)
    with pytest.raises(ProductError) as exc:
        service.apply_placement_decision(confirmation_id="reject-1")
    assert exc.value.code == "ERR_AUDIO_WORKSPACE_CONFIRMATION_STALE"
    assert ws.placements["review-1"].decision is PlacementDecision.REVIEW
