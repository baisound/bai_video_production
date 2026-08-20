from __future__ import annotations

from dataclasses import replace

import pytest

from ai_video_production.canonical_game_event import (
    EventConfirmationState,
    EventReviewStatus,
    GameEnvironment,
    GameEventType,
    GameMatch,
    GameMatchStatus,
    GamePerspective,
)
from ai_video_production.dbd_event_resolver import (
    BoundedDBDEventProducer,
    DBDEventCandidate,
    DBDEventResolver,
    DBDHealthState,
    DBDObservationOrigin,
    DBDResolverState,
    DBDTriState,
    DBDVisualMarkerKind,
)
from ai_video_production.dbd_profile import DBDSignalKind
from ai_video_production.errors import ProductError
from ai_video_production.game_event_evidence import GameEvidence, GameEvidenceType, SourceFrameRange
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.timebase import FrameRate


def match() -> GameMatch:
    return GameMatch(
        production_job_id=generate_id(IdKind.JOB),
        source_asset_id=generate_id(IdKind.ASSET),
        game_profile_id="dead_by_daylight",
        game_profile_version="1.0.0",
        game_version="9.1.0",
        environment=GameEnvironment.LIVE,
        perspective=GamePerspective.SURVIVOR,
        source_rate=FrameRate(30000, 1001),
        status=GameMatchStatus.ANALYZING,
    )


def evidence(
    game_match: GameMatch,
    *,
    start: int,
    end: int,
    confidence: int = 950,
    evidence_type: GameEvidenceType = GameEvidenceType.STATE_TRANSITION,
) -> GameEvidence:
    return GameEvidence(
        production_job_id=game_match.production_job_id,
        match_id=game_match.match_id,
        source_asset_id=game_match.source_asset_id,
        producer="task049.r4-fixture",
        producer_version="1.0.0",
        evidence_type=evidence_type,
        source_range=SourceFrameRange(start, end),
        confidence_milli=confidence,
    )


def test_profile_signal_transition_to_confirmed_hook_and_unhook_sequence() -> None:
    game_match = match()
    producer = BoundedDBDEventProducer()
    hook_ev = evidence(game_match, start=100, end=110)
    unhook_ev = evidence(game_match, start=200, end=210)
    hook = producer.from_profile_signal_transition(
        match_id=game_match.match_id,
        signal_kind=DBDSignalKind.EVENT_HOOK,
        before=False,
        after=True,
        source_range=hook_ev.source_range,
        evidence_refs=(hook_ev.game_evidence_id,),
        confidence_milli=960,
    )
    unhook = producer.from_profile_signal_transition(
        match_id=game_match.match_id,
        signal_kind=DBDSignalKind.EVENT_RESCUE,
        before=False,
        after=True,
        source_range=unhook_ev.source_range,
        evidence_refs=(unhook_ev.game_evidence_id,),
        confidence_milli=950,
    )
    assert hook is not None and unhook is not None
    results = DBDEventResolver().resolve_candidates(
        game_match,
        (unhook, hook),
        {hook_ev.game_evidence_id: hook_ev, unhook_ev.game_evidence_id: unhook_ev},
    )
    assert [x.event.event_type for x in results] == [GameEventType.HOOK, GameEventType.UNHOOK]
    assert all(x.event.confirmation_state is EventConfirmationState.CONFIRMED for x in results)
    assert results[-1].state_after.survivor_hooked is DBDTriState.INACTIVE


def test_chase_start_end_state_machine_and_duplicate_start_needs_review() -> None:
    game_match = match()
    producer = BoundedDBDEventProducer()
    ev1 = evidence(game_match, start=10, end=20)
    ev2 = evidence(game_match, start=30, end=40)
    ev3 = evidence(game_match, start=50, end=60)
    start1 = producer.from_profile_signal_transition(
        match_id=game_match.match_id,
        signal_kind=DBDSignalKind.CHASE_INTENSITY,
        before=False,
        after=True,
        source_range=ev1.source_range,
        evidence_refs=(ev1.game_evidence_id,),
        confidence_milli=980,
    )
    duplicate = producer.from_profile_signal_transition(
        match_id=game_match.match_id,
        signal_kind=DBDSignalKind.CHASE_INTENSITY,
        before=False,
        after=True,
        source_range=ev2.source_range,
        evidence_refs=(ev2.game_evidence_id,),
        confidence_milli=980,
    )
    end = producer.from_profile_signal_transition(
        match_id=game_match.match_id,
        signal_kind=DBDSignalKind.CHASE_INTENSITY,
        before=True,
        after=False,
        source_range=ev3.source_range,
        evidence_refs=(ev3.game_evidence_id,),
        confidence_milli=980,
    )
    assert start1 is not None and duplicate is not None and end is not None
    results = DBDEventResolver().resolve_candidates(
        game_match,
        (start1, duplicate, end),
        {x.game_evidence_id: x for x in (ev1, ev2, ev3)},
    )
    assert results[0].event.confirmation_state is EventConfirmationState.CONFIRMED
    assert results[1].event.confirmation_state is EventConfirmationState.NEEDS_REVIEW
    assert "CHASE_ALREADY_ACTIVE" in results[1].reason_codes
    assert "STATE_NOT_ADVANCED" in results[1].reason_codes
    assert results[2].event.confirmation_state is EventConfirmationState.CONFIRMED
    assert results[2].state_after.chase_active is DBDTriState.INACTIVE


def test_visual_markers_cover_match_start_window_vault_and_pallet_drop() -> None:
    game_match = match()
    producer = BoundedDBDEventProducer()
    items = []
    evidence_map = {}
    for index, marker in enumerate(
        (DBDVisualMarkerKind.MATCH_START, DBDVisualMarkerKind.WINDOW_VAULT, DBDVisualMarkerKind.PALLET_DROP)
    ):
        ev = evidence(game_match, start=index * 100, end=index * 100 + 10, evidence_type=GameEvidenceType.VISION)
        evidence_map[ev.game_evidence_id] = ev
        items.append(
            producer.from_visual_marker(
                match_id=game_match.match_id,
                marker=marker,
                source_range=ev.source_range,
                evidence_refs=(ev.game_evidence_id,),
                confidence_milli=940,
            )
        )
    results = DBDEventResolver().resolve_candidates(game_match, items, evidence_map)
    assert [x.event.event_type for x in results] == [
        GameEventType.MATCH_START,
        GameEventType.WINDOW_VAULT,
        GameEventType.PALLET_DROP,
    ]
    assert all(x.event.review_status is EventReviewStatus.AUTO_ACCEPTED for x in results)


def test_health_transition_produces_injury_but_no_change_returns_none() -> None:
    game_match = match()
    ev = evidence(game_match, start=10, end=20, evidence_type=GameEvidenceType.HUD)
    producer = BoundedDBDEventProducer()
    candidate = producer.from_profile_signal_transition(
        match_id=game_match.match_id,
        signal_kind=DBDSignalKind.HUD_SURVIVOR_HEALTH,
        before=DBDHealthState.HEALTHY,
        after=DBDHealthState.INJURED,
        source_range=ev.source_range,
        evidence_refs=(ev.game_evidence_id,),
        confidence_milli=930,
    )
    assert candidate is not None
    result = DBDEventResolver().resolve_candidate(game_match, candidate, {ev.game_evidence_id: ev})
    assert result.event.event_type is GameEventType.INJURY
    assert result.event.confirmation_state is EventConfirmationState.CONFIRMED

    no_change = producer.from_profile_signal_transition(
        match_id=game_match.match_id,
        signal_kind=DBDSignalKind.HUD_SURVIVOR_HEALTH,
        before=DBDHealthState.INJURED,
        after=DBDHealthState.INJURED,
        source_range=ev.source_range,
        evidence_refs=(ev.game_evidence_id,),
        confidence_milli=930,
    )
    assert no_change is None


def test_low_confidence_becomes_unknown_event_and_does_not_advance_state() -> None:
    game_match = match()
    ev = evidence(game_match, start=10, end=20, confidence=500, evidence_type=GameEvidenceType.VISION)
    candidate = BoundedDBDEventProducer().from_visual_marker(
        match_id=game_match.match_id,
        marker=DBDVisualMarkerKind.MATCH_START,
        source_range=ev.source_range,
        evidence_refs=(ev.game_evidence_id,),
        confidence_milli=550,
    )
    result = DBDEventResolver().resolve_candidate(game_match, candidate, {ev.game_evidence_id: ev})
    assert result.event.event_type is GameEventType.UNKNOWN_EVENT
    assert result.event.confirmation_state is EventConfirmationState.UNKNOWN
    assert result.state_after.match_started is DBDTriState.UNKNOWN
    assert "CONFIDENCE_BELOW_REVIEW_THRESHOLD" in result.reason_codes


def test_medium_confidence_keeps_candidate_type_but_requires_review() -> None:
    game_match = match()
    ev = evidence(game_match, start=10, end=20, confidence=800, evidence_type=GameEvidenceType.VISION)
    candidate = BoundedDBDEventProducer().from_visual_marker(
        match_id=game_match.match_id,
        marker=DBDVisualMarkerKind.WINDOW_VAULT,
        source_range=ev.source_range,
        evidence_refs=(ev.game_evidence_id,),
        confidence_milli=820,
    )
    result = DBDEventResolver().resolve_candidate(game_match, candidate, {ev.game_evidence_id: ev})
    assert result.event.event_type is GameEventType.WINDOW_VAULT
    assert result.event.confirmation_state is EventConfirmationState.NEEDS_REVIEW
    assert result.event.review_status is EventReviewStatus.PENDING


def test_asr_only_and_llm_origin_cannot_auto_confirm() -> None:
    game_match = match()
    asr = evidence(game_match, start=10, end=20, confidence=990, evidence_type=GameEvidenceType.ASR)
    candidate = DBDEventCandidate(
        match_id=game_match.match_id,
        event_type=GameEventType.WINDOW_VAULT,
        source_range=asr.source_range,
        evidence_refs=(asr.game_evidence_id,),
        confidence_milli=990,
        origin=DBDObservationOrigin.ASR_INTERPRETATION,
        producer="task049.asr-interpretation",
        producer_version="1.0.0",
    )
    result = DBDEventResolver().resolve_candidate(game_match, candidate, {asr.game_evidence_id: asr})
    assert result.event.confirmation_state is EventConfirmationState.NEEDS_REVIEW
    assert "DIRECT_EVIDENCE_REQUIRED" in result.reason_codes
    assert "ORIGIN_REQUIRES_REVIEW" in result.reason_codes

    vision = evidence(game_match, start=10, end=20, confidence=990, evidence_type=GameEvidenceType.VISION)
    llm = replace(candidate, evidence_refs=(vision.game_evidence_id,), origin=DBDObservationOrigin.LLM_INFERENCE)
    result = DBDEventResolver().resolve_candidate(game_match, llm, {vision.game_evidence_id: vision})
    assert result.event.confirmation_state is EventConfirmationState.NEEDS_REVIEW
    assert "ORIGIN_REQUIRES_REVIEW" in result.reason_codes


def test_missing_cross_match_and_nonoverlapping_evidence_fail_closed() -> None:
    game_match = match()
    ev = evidence(game_match, start=10, end=20)
    candidate = BoundedDBDEventProducer().from_visual_marker(
        match_id=game_match.match_id,
        marker=DBDVisualMarkerKind.WINDOW_VAULT,
        source_range=ev.source_range,
        evidence_refs=(ev.game_evidence_id,),
        confidence_milli=950,
    )
    with pytest.raises(ProductError, match="missing Evidence"):
        DBDEventResolver().resolve_candidate(game_match, candidate, {})

    other = replace(game_match, match_id=generate_id(IdKind.GAME_MATCH))
    wrong_match_ev = replace(ev, match_id=other.match_id)
    with pytest.raises(ProductError, match="another Match"):
        DBDEventResolver().resolve_candidate(game_match, candidate, {ev.game_evidence_id: wrong_match_ev})

    nonoverlap = replace(ev, source_range=SourceFrameRange(100, 110))
    with pytest.raises(ProductError, match="temporally overlapping"):
        DBDEventResolver().resolve_candidate(game_match, candidate, {ev.game_evidence_id: nonoverlap})


def test_unsupported_task009_signal_does_not_silently_become_event() -> None:
    game_match = match()
    ev = evidence(game_match, start=10, end=20)
    with pytest.raises(ProductError, match="not admitted"):
        BoundedDBDEventProducer().from_profile_signal_transition(
            match_id=game_match.match_id,
            signal_kind=DBDSignalKind.HUD_GENERATOR_PROGRESS,
            before=False,
            after=True,
            source_range=ev.source_range,
            evidence_refs=(ev.game_evidence_id,),
            confidence_milli=950,
        )


def test_candidate_confidence_is_bounded_by_evidence_mean() -> None:
    game_match = match()
    a = evidence(game_match, start=10, end=20, confidence=1000, evidence_type=GameEvidenceType.VISION)
    b = evidence(game_match, start=10, end=20, confidence=600, evidence_type=GameEvidenceType.STATE_TRANSITION)
    candidate = BoundedDBDEventProducer().from_visual_marker(
        match_id=game_match.match_id,
        marker=DBDVisualMarkerKind.WINDOW_VAULT,
        source_range=SourceFrameRange(10, 20),
        evidence_refs=(a.game_evidence_id, b.game_evidence_id),
        confidence_milli=990,
    )
    result = DBDEventResolver().resolve_candidate(
        game_match,
        candidate,
        {a.game_evidence_id: a, b.game_evidence_id: b},
    )
    assert result.event.confidence_milli == 800
    assert result.event.confirmation_state is EventConfirmationState.NEEDS_REVIEW


def test_resolver_initial_state_can_block_impossible_unhook_without_repairing_state() -> None:
    game_match = match()
    ev = evidence(game_match, start=10, end=20)
    candidate = BoundedDBDEventProducer().from_profile_signal_transition(
        match_id=game_match.match_id,
        signal_kind=DBDSignalKind.EVENT_RESCUE,
        before=False,
        after=True,
        source_range=ev.source_range,
        evidence_refs=(ev.game_evidence_id,),
        confidence_milli=970,
    )
    assert candidate is not None
    initial = DBDResolverState(survivor_hooked=DBDTriState.INACTIVE)
    result = DBDEventResolver().resolve_candidate(game_match, candidate, {ev.game_evidence_id: ev}, state=initial)
    assert result.event.confirmation_state is EventConfirmationState.NEEDS_REVIEW
    assert result.state_after == initial
    assert "SURVIVOR_ALREADY_UNHOOKED" in result.reason_codes
