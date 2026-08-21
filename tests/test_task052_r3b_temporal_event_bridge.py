from __future__ import annotations

import pytest

from ai_video_production.canonical_game_event import (
    EventConfirmationState,
    GameEnvironment,
    GameEventType,
    GameMatch,
    GameMatchStatus,
    GamePerspective,
)
from ai_video_production.dbd_event_resolver import (
    DBDEventResolver,
    DBDTriState,
)
from ai_video_production.dbd_temporal_event_bridge import TemporalDecisionEventProducer
from ai_video_production.dbd_temporal_state import (
    DBDTemporalSignal,
    TemporalDecision,
    TemporalDecisionStatus,
)
from ai_video_production.game_event_evidence import (
    GameEvidence,
    GameEvidenceType,
    SourceFrameRange,
)
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.timebase import FrameRate


def game_match() -> GameMatch:
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


def evidence(match: GameMatch, start: int) -> GameEvidence:
    return GameEvidence(
        production_job_id=match.production_job_id,
        match_id=match.match_id,
        source_asset_id=match.source_asset_id,
        producer="task052.r3b-test",
        producer_version="1.0.0",
        evidence_type=GameEvidenceType.HUD,
        source_range=SourceFrameRange(start, start + 2),
        confidence_milli=960,
    )


def decision(
    match: GameMatch,
    evidence_ref: str,
    *,
    signal: DBDTemporalSignal,
    before: str,
    after: str,
    frame: int,
    slot: int | None,
    status: TemporalDecisionStatus = TemporalDecisionStatus.CONFIRMED,
) -> TemporalDecision:
    return TemporalDecision(
        status=status,
        signal=signal,
        match_id=match.match_id,
        survivor_slot=slot,
        frame_index=frame,
        observed_value=after,
        stable_value_before=before,
        stable_value_after=after,
        confidence_milli=950,
        evidence_refs=(evidence_ref,),
        reason_codes=("TEST_CONFIRMED",),
    )


@pytest.mark.parametrize(
    ("signal", "before", "after", "slot", "expected"),
    (
        (DBDTemporalSignal.GENERATOR_REMAINING, "5", "4", None, GameEventType.GENERATOR_COMPLETE),
        (DBDTemporalSignal.CHASE_STATE, "CHASE_CANDIDATE", "CHASE_ACTIVE", 0, GameEventType.CHASE_START),
        (DBDTemporalSignal.CHASE_STATE, "CHASE_END_CANDIDATE", "NOT_CHASE", 0, GameEventType.CHASE_END),
        (DBDTemporalSignal.SURVIVOR_STATE, "HEALTHY", "INJURED", 0, GameEventType.INJURY),
        (DBDTemporalSignal.SURVIVOR_STATE, "INJURED", "DOWNED", 0, GameEventType.DOWN),
        (DBDTemporalSignal.SURVIVOR_STATE, "DOWNED", "HOOKED", 0, GameEventType.HOOK),
        (DBDTemporalSignal.SURVIVOR_STATE, "HOOKED", "INJURED", 0, GameEventType.UNHOOK),
        (DBDTemporalSignal.SURVIVOR_STATE, "HOOKED", "DEAD", 0, GameEventType.KILL),
        (DBDTemporalSignal.SURVIVOR_STATE, "INJURED", "ESCAPED", 0, GameEventType.ESCAPE),
    ),
)
def test_confirmed_temporal_decisions_map_to_cgel_taxonomy(signal, before, after, slot, expected) -> None:
    match = game_match()
    ev = evidence(match, 10)
    candidate = TemporalDecisionEventProducer().from_decision(
        decision(match, ev.game_evidence_id, signal=signal, before=before, after=after, frame=10, slot=slot),
        source_range=ev.source_range,
    )
    assert candidate is not None
    assert candidate.event_type is expected
    assert candidate.survivor_slot == slot
    assert candidate.observation_state["temporal_status"] == "CONFIRMED"


def test_nonconfirmed_or_non_event_transition_cannot_create_candidate() -> None:
    match = game_match()
    ev = evidence(match, 10)
    producer = TemporalDecisionEventProducer()
    pending = decision(
        match, ev.game_evidence_id,
        signal=DBDTemporalSignal.CHASE_STATE,
        before="NOT_CHASE", after="CHASE_CANDIDATE", frame=10, slot=0,
        status=TemporalDecisionStatus.CANDIDATE,
    )
    recovery = decision(
        match, ev.game_evidence_id,
        signal=DBDTemporalSignal.SURVIVOR_STATE,
        before="INJURED", after="HEALTHY", frame=10, slot=0,
    )
    hook_count = decision(
        match, ev.game_evidence_id,
        signal=DBDTemporalSignal.HOOK_COUNT,
        before="0", after="1", frame=10, slot=0,
    )
    assert producer.from_decision(pending, source_range=ev.source_range) is None
    assert producer.from_decision(recovery, source_range=ev.source_range) is None
    assert producer.from_decision(hook_count, source_range=ev.source_range) is None


def test_bridge_requires_subject_and_source_range_containing_decision() -> None:
    match = game_match()
    ev = evidence(match, 10)
    producer = TemporalDecisionEventProducer()
    subjectless = decision(
        match, ev.game_evidence_id,
        signal=DBDTemporalSignal.CHASE_STATE,
        before="CHASE_CANDIDATE", after="CHASE_ACTIVE", frame=10, slot=None,
    )
    with pytest.raises(ValueError, match="survivor_slot"):
        producer.from_decision(subjectless, source_range=ev.source_range)
    with pytest.raises(ValueError, match="contain"):
        producer.from_decision(
            decision(
                match, ev.game_evidence_id,
                signal=DBDTemporalSignal.GENERATOR_REMAINING,
                before="5", after="4", frame=20, slot=None,
            ),
            source_range=ev.source_range,
        )


def test_resolver_chase_state_is_isolated_per_survivor() -> None:
    match = game_match()
    producer = TemporalDecisionEventProducer()
    rows = []
    evidence_by_id = {}
    for frame, slot in ((10, 0), (20, 1), (30, 0)):
        ev = evidence(match, frame)
        evidence_by_id[ev.game_evidence_id] = ev
        rows.append(producer.from_decision(
            decision(
                match, ev.game_evidence_id,
                signal=DBDTemporalSignal.CHASE_STATE,
                before="CHASE_CANDIDATE", after="CHASE_ACTIVE", frame=frame, slot=slot,
            ),
            source_range=ev.source_range,
        ))
    results = DBDEventResolver().resolve_candidates(match, rows, evidence_by_id)
    assert [result.event.confirmation_state for result in results] == [
        EventConfirmationState.CONFIRMED,
        EventConfirmationState.CONFIRMED,
        EventConfirmationState.NEEDS_REVIEW,
    ]
    final = results[-1].state_after
    assert final.survivor_state(0).chase_active is DBDTriState.ACTIVE
    assert final.survivor_state(1).chase_active is DBDTriState.ACTIVE
    assert final.chase_active is DBDTriState.UNKNOWN


def test_resolver_hook_state_is_isolated_per_survivor() -> None:
    match = game_match()
    producer = TemporalDecisionEventProducer()
    rows = []
    evidence_by_id = {}
    for frame, slot in ((10, 2), (20, 3)):
        ev = evidence(match, frame)
        evidence_by_id[ev.game_evidence_id] = ev
        rows.append(producer.from_decision(
            decision(
                match, ev.game_evidence_id,
                signal=DBDTemporalSignal.SURVIVOR_STATE,
                before="DOWNED", after="HOOKED", frame=frame, slot=slot,
            ),
            source_range=ev.source_range,
        ))
    results = DBDEventResolver().resolve_candidates(match, rows, evidence_by_id)
    assert all(result.event.confirmation_state is EventConfirmationState.CONFIRMED for result in results)
    final = results[-1].state_after
    assert final.survivor_state(2).survivor_hooked is DBDTriState.ACTIVE
    assert final.survivor_state(3).survivor_hooked is DBDTriState.ACTIVE
    assert final.survivor_hooked is DBDTriState.UNKNOWN


def test_generator_candidate_requires_admitted_direct_evidence() -> None:
    match = game_match()
    ev = evidence(match, 10)
    candidate = TemporalDecisionEventProducer().from_decision(
        decision(
            match, ev.game_evidence_id,
            signal=DBDTemporalSignal.GENERATOR_REMAINING,
            before="5", after="4", frame=10, slot=None,
        ),
        source_range=ev.source_range,
    )
    assert candidate is not None
    result = DBDEventResolver().resolve_candidate(match, candidate, {ev.game_evidence_id: ev})
    assert result.event.event_type is GameEventType.GENERATOR_COMPLETE
    assert result.event.confirmation_state is EventConfirmationState.CONFIRMED
