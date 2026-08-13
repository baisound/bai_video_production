from __future__ import annotations

import pytest

from ai_video_production.continuity_map import ContinuityBoundaryType, ContinuityEdge
from ai_video_production.continuity_registry import ContinuityProductionControlBinding, ContinuityRegistry
from ai_video_production.errors import ProductError
from ai_video_production.production_control import EntityRef, EntityType, ProductionControlRegistry, SceneAssetSlot, SlotKind, StaleState


SHA = "sha256:" + "a" * 64
SHA2 = "sha256:" + "b" * 64


def edge(boundary=ContinuityBoundaryType.DIRECT_CONTINUATION):
    return ContinuityEdge(
        "edge-1", "scene-1", "slot-end", "candidate-1", "asset-1", SHA,
        "scene-2", "slot-start", boundary,
    )


def test_direct_continuation_is_generation_safe_only_for_exact_asset_and_hash():
    registry = ContinuityRegistry(); registry.add_edge(edge())
    registry.inspect_target("edge-1", target_asset_id="asset-1", target_asset_sha256=SHA)
    assert registry.require_generation_safe("edge-1").status == "PASS"
    failed = registry.inspect_target("edge-1", target_asset_id="asset-2", target_asset_sha256=SHA2)
    assert failed.status == "FAIL"
    with pytest.raises(ProductError) as exc:
        registry.require_generation_safe("edge-1")
    assert exc.value.code == "ERR_CONTINUITY_GENERATION_BLOCKED"


def test_direct_continuation_cannot_be_human_overridden():
    registry = ContinuityRegistry(); registry.add_edge(edge())
    registry.inspect_target("edge-1", target_asset_id="asset-2", target_asset_sha256=SHA2)
    with pytest.raises(ProductError) as exc:
        registry.human_approve_soft("edge-1", approved_by="owner")
    assert exc.value.code == "ERR_CONTINUITY_HARD_RULE_NOT_OVERRIDABLE"


def test_soft_continuity_can_be_explicitly_human_approved():
    registry = ContinuityRegistry(); registry.add_edge(edge(ContinuityBoundaryType.SOFT_CONTINUITY))
    inspected = registry.inspect_target("edge-1", target_asset_id="asset-2", target_asset_sha256=SHA2)
    assert inspected.status == "HUMAN_REVIEW_REQUIRED"
    approved = registry.human_approve_soft("edge-1", approved_by="owner")
    assert approved.status == "HUMAN_APPROVED"
    assert registry.require_generation_safe("edge-1").human_approved_by == "owner"


def test_continuity_binding_reuses_task037_stale_propagation_without_regeneration():
    pc = ProductionControlRegistry()
    pc.add_slot(SceneAssetSlot("slot-end", "project-1", "scene-1", SlotKind.END_FRAME, True))
    pc.add_slot(SceneAssetSlot("slot-start", "project-1", "scene-2", SlotKind.START_FRAME, True))
    dependency = ContinuityProductionControlBinding.bind(pc, edge())
    assert dependency.continuity_boundary == "DIRECT_CONTINUATION"
    result = pc.mark_stale(EntityRef(EntityType.SLOT, "slot-end"))
    assert [item.key for item in result.affected] == ["SLOT:slot-start"]
    assert pc.slots["slot-start"].stale_state == StaleState.STALE
    assert result.to_dict()["automatic_regeneration_started"] is False
