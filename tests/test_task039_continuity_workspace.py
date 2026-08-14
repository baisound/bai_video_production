from __future__ import annotations

import pytest

from ai_video_production.continuity_map import ContinuityBoundaryType, ContinuityEdge
from ai_video_production.continuity_registry import ContinuityRegistry
from ai_video_production.continuity_workspace import Task039ContinuityWorkspaceService
from ai_video_production.errors import ProductError
from ai_video_production.production_control import AssetCandidate, CandidateLifecycle, ProductionControlRegistry, SceneAssetSlot, SlotKind

H1 = "sha256:" + "a" * 64
H2 = "sha256:" + "b" * 64


def setup(boundary=ContinuityBoundaryType.SOFT_CONTINUITY):
    production = ProductionControlRegistry()
    production.add_slot(SceneAssetSlot("slot-from", "project-1", "scene-1", SlotKind.END_FRAME, True))
    production.add_slot(SceneAssetSlot("slot-to", "project-1", "scene-2", SlotKind.START_FRAME, True))
    production.add_candidate(AssetCandidate("candidate-from", "slot-from", "asset-from", H1, 1))
    production.add_candidate(AssetCandidate("candidate-to", "slot-to", "asset-to", H2, 1))
    for cid in ("candidate-from", "candidate-to"):
        production.transition_candidate(cid, CandidateLifecycle.READY_FOR_AUDIT)
        production.transition_candidate(cid, CandidateLifecycle.ACCEPTED)
    for sid, cid in (("slot-from", "candidate-from"), ("slot-to", "candidate-to")):
        slot = production.slots[sid]
        production.lock_candidate(slot_id=sid, candidate_id=cid, expected_revision=slot.revision)
    continuity = ContinuityRegistry()
    continuity.add_edge(ContinuityEdge(
        "edge-1", "scene-1", "slot-from", "candidate-from", "asset-from", H1,
        "scene-2", "slot-to", boundary,
    ))
    continuity.inspect_target("edge-1", target_asset_id="asset-to", target_asset_sha256=H2)
    return production, continuity


def test_soft_continuity_projection_offers_human_approval_only_for_exact_locked_target():
    production, continuity = setup()
    service = Task039ContinuityWorkspaceService(continuity=continuity, production=production)
    row = service.snapshot()["edges"][0]
    assert row["human_soft_approval_available"] is True
    assert row["direct_continuation_human_override_allowed"] is False


def test_soft_approval_is_one_shot_and_generation_remains_separate():
    production, continuity = setup()
    service = Task039ContinuityWorkspaceService(continuity=continuity, production=production, token_factory=lambda: "soft-1")
    prepared = service.prepare_soft_approval(edge_id="edge-1")
    assert prepared["automatic_regeneration_started"] is False
    result = service.apply_soft_approval(confirmation_id="soft-1", approved_by="owner")
    assert result["resolution"]["status"] == "HUMAN_APPROVED"
    assert result["automatic_regeneration_started"] is False
    with pytest.raises(ProductError) as exc:
        service.apply_soft_approval(confirmation_id="soft-1", approved_by="owner")
    assert exc.value.code == "ERR_CONTINUITY_WORKSPACE_CONFIRMATION_INVALID"


def test_direct_continuation_never_exposes_human_override():
    production, continuity = setup(ContinuityBoundaryType.DIRECT_CONTINUATION)
    service = Task039ContinuityWorkspaceService(continuity=continuity, production=production, token_factory=lambda: "x")
    with pytest.raises(ProductError) as exc:
        service.prepare_soft_approval(edge_id="edge-1")
    assert exc.value.code == "ERR_CONTINUITY_HARD_RULE_NOT_OVERRIDABLE"


def test_confirmation_stales_if_locked_target_changes():
    production, continuity = setup()
    service = Task039ContinuityWorkspaceService(continuity=continuity, production=production, token_factory=lambda: "soft")
    service.prepare_soft_approval(edge_id="edge-1")
    production.candidates["candidate-to"] = AssetCandidate(
        "candidate-to", "slot-to", "asset-to", H2, 1, CandidateLifecycle.STALE
    )
    with pytest.raises(ProductError) as exc:
        service.apply_soft_approval(confirmation_id="soft", approved_by="owner")
    assert exc.value.code == "ERR_CONTINUITY_WORKSPACE_CONFIRMATION_STALE"
    with pytest.raises(ProductError) as exc:
        service.apply_soft_approval(confirmation_id="soft", approved_by="owner")
    assert exc.value.code == "ERR_CONTINUITY_WORKSPACE_CONFIRMATION_INVALID"
