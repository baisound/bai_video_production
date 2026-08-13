from __future__ import annotations

import pytest

from ai_video_production.audio_workspace import (
    AudioCandidateDecision,
    AudioDecisionKind,
    AudioDerivationType,
    AudioDerivedAsset,
    AudioSlotKind,
    AudioWorkspaceRegistry,
    PlacementDecision,
    PlacementReview,
)


SHA1 = "sha256:" + "1" * 64
SHA2 = "sha256:" + "2" * 64


def test_strip_audio_is_recorded_as_non_destructive_derived_asset():
    derived = AudioDerivedAsset("asset-no-audio", "asset-original", SHA1, SHA2, AudioDerivationType.AUDIO_STRIPPED_VIDEO)
    body = derived.to_dict()
    assert body["destructive_source_write"] is False
    assert body["source_sha256"] == SHA1


def test_derived_asset_cannot_reuse_same_hash():
    with pytest.raises(ValueError):
        AudioDerivedAsset("asset-copy", "asset-original", SHA1, SHA1, AudioDerivationType.AUDIO_STRIPPED_VIDEO)


def test_visual_candidate_audio_can_be_stripped_without_rejecting_candidate_identity():
    registry = AudioWorkspaceRegistry()
    registry.add_decision(AudioCandidateDecision("decision-1", "candidate-1", AudioSlotKind.VFX_EMBEDDED_AUDIO, AudioDecisionKind.STRIP_AUDIO, "owner"))
    registry.add_derived_asset(AudioDerivedAsset("asset-no-audio", "asset-original", SHA1, SHA2, AudioDerivationType.AUDIO_STRIPPED_VIDEO))
    assert registry.decisions["decision-1"].decision is AudioDecisionKind.STRIP_AUDIO
    assert registry.derived_assets["asset-no-audio"].source_asset_id == "asset-original"


def test_only_human_accepted_placements_are_ready_for_downstream_assembly():
    registry = AudioWorkspaceRegistry()
    registry.add_placement(PlacementReview("review-1", "candidate-1", 100, 48, "SE"))
    assert registry.accepted_placements() == ()
    registry.replace_placement_decision("review-1", PlacementDecision.ACCEPT)
    assert [item.review_id for item in registry.accepted_placements()] == ["review-1"]
