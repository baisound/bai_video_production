from __future__ import annotations

from dataclasses import replace

import pytest

from ai_video_production.ai_connections import (
    AiConnectionProfile, AiWorkload, ConnectionAvailability, CostClass, ModelRoute,
    ProviderFamily, SelectionMode,
)
from ai_video_production.dbd_selective_vision import (
    SelectiveVisionAuthority, SelectiveVisionCandidate, SelectiveVisionPlanner,
    SelectiveVisionPlanStatus, SelectiveVisionTrigger,
)
from ai_video_production.dbd_vision_slices import NormalizedROI
from ai_video_production.game_event_evidence import SourceFrameRange


def _profile(*, enabled: bool = True) -> AiConnectionProfile:
    return AiConnectionProfile(
        "test-profile", "1", SelectionMode.AUTO,
        (ModelRoute(
            "vision-route", AiWorkload.IMAGE, ProviderFamily.OPENAI,
            "openai", "vision-model", CostClass.CLOUD_PAID_AI,
            capabilities=("DBD_SELECTIVE_VISION_ANALYSIS",), enabled=enabled,
        ),),
    )


def _candidate(*triggers: SelectiveVisionTrigger, confidence: int = 700) -> SelectiveVisionCandidate:
    return SelectiveVisionCandidate(
        "match-1", "asset-1", SourceFrameRange(100, 160),
        (NormalizedROI("survivor_hud", 0.7, 0.1, 0.25, 0.4),),
        triggers or (SelectiveVisionTrigger.TIER_CONTRADICTION,),
        ("evidence://game/one", "evidence://game/two"), confidence,
    )


def _authority() -> SelectiveVisionAuthority:
    return SelectiveVisionAuthority(True, "authorization://human/vision-1", 3)


def test_high_confidence_non_contradictory_tier_evidence_is_not_escalated() -> None:
    plan = SelectiveVisionPlanner().plan(
        _candidate(SelectiveVisionTrigger.GENERATOR_COMPLETION, confidence=950),
        _profile(), ConnectionAvailability(frozenset({"vision-route"})), _authority(),
    )
    assert plan.status is SelectiveVisionPlanStatus.NOT_ELIGIBLE
    assert plan.request is None
    assert plan.provider_dispatch_allowed is False


def test_missing_authority_fails_before_route_resolution_or_request_creation() -> None:
    plan = SelectiveVisionPlanner().plan(
        _candidate(), _profile(enabled=False), ConnectionAvailability(frozenset()),
    )
    assert plan.status is SelectiveVisionPlanStatus.AUTHORIZATION_REQUIRED
    assert plan.route_id is None
    assert plan.request is None
    assert plan.event_claim_allowed is False


def test_authorized_contradiction_uses_canonical_route_and_bounded_request() -> None:
    plan = SelectiveVisionPlanner().plan(
        _candidate(confidence=990), _profile(),
        ConnectionAvailability(frozenset({"vision-route"})), _authority(),
    )
    assert plan.status is SelectiveVisionPlanStatus.READY
    assert plan.route_id == "vision-route"
    assert plan.cost_class is CostClass.CLOUD_PAID_AI
    assert plan.provider_dispatch_allowed is True
    assert plan.event_claim_allowed is False
    assert plan.request is not None
    assert plan.request.capability == "DBD_SELECTIVE_VISION_ANALYSIS"
    assert plan.request.payload["source_range"] == {"start_frame": 100, "end_frame_exclusive": 160}
    assert plan.request.payload["response_contract"]["allow_abstention"] is True
    assert plan.request.payload["response_contract"]["event_claim_allowed"] is False


def test_authorized_but_unavailable_route_remains_non_dispatchable() -> None:
    plan = SelectiveVisionPlanner().plan(
        _candidate(), _profile(), ConnectionAvailability(frozenset()), _authority(),
    )
    assert plan.status is SelectiveVisionPlanStatus.ROUTE_UNAVAILABLE
    assert plan.request is None
    assert plan.provider_dispatch_allowed is False


def test_candidate_and_authority_bounds_reject_unsafe_inputs() -> None:
    with pytest.raises(ValueError, match="at most 300"):
        replace(_candidate(), source_range=SourceFrameRange(0, 301))
    with pytest.raises(ValueError, match="non-secret references"):
        replace(_candidate(), evidence_refs=("not-a-reference",))
    with pytest.raises(ValueError, match="must not carry"):
        replace(_candidate(), evidence_refs=("credential://provider/key",))
    with pytest.raises(ValueError, match="unique"):
        replace(_candidate(), evidence_refs=("evidence://same", "evidence://same"))
    with pytest.raises(ValueError, match="0..1000"):
        replace(_candidate(), tier_confidence_milli="700")
    with pytest.raises(ValueError, match="reference and positive"):
        SelectiveVisionAuthority(True, None, 0)
    with pytest.raises(ValueError, match="authorization://"):
        SelectiveVisionAuthority(False, "credential://must-not-be-used", 0)
