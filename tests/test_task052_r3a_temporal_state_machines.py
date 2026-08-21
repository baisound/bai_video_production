from __future__ import annotations

import pytest

from ai_video_production.dbd_observation_envelope import (
    ObservationProvenance,
    SurvivorSignalKind,
    survivor_signal_to_observation,
)
from ai_video_production.dbd_temporal_state import (
    ChasePhase,
    DBDTemporalProfile,
    DBDTemporalStateMachines,
    SurvivorSubject,
    TemporalDecisionStatus,
)


def profile(**changes: int) -> DBDTemporalProfile:
    values = {
        "profile_id": "hud-temporal-test",
        "profile_version": 1,
        "minimum_confidence_milli": 700,
        "history_window_frames": 5,
        "generator_minimum_frames": 3,
        "survivor_state_minimum_frames": 2,
        "hook_count_minimum_frames": 2,
        "chase_start_frames": 2,
        "chase_end_frames": 3,
    }
    values.update(changes)
    return DBDTemporalProfile(**values)


def observation(kind: SurvivorSignalKind, value: str, frame: int, *, slot: int = 0, confidence: int = 900, match_id: str = "match-1"):
    provenance = ObservationProvenance(
        workspace_id="workspace-1",
        runtime_profile_id="runtime-1",
        hud_profile_id="hud-1",
        hud_profile_version=1,
        roi_id=f"survivor_slot_{slot}",
        detector_version="detector-1",
    )
    return survivor_signal_to_observation(
        observation_id=f"obs-{match_id}-{slot}-{kind.value}-{frame}",
        match_id=match_id,
        survivor_slot=slot,
        signal_kind=kind,
        value=value,
        confidence_milli=confidence,
        source_frame=frame,
        provenance=provenance,
        evidence_ref=f"evidence-{frame}",
    )


def test_profile_rejects_vote_threshold_larger_than_window() -> None:
    with pytest.raises(ValueError, match="vote thresholds"):
        profile(generator_minimum_frames=6)


def test_generator_temporal_majority_confirms_decrease_and_rejects_increase() -> None:
    machine = DBDTemporalStateMachines(profile())
    statuses = []
    for frame, value in enumerate((5, 4, 5, 5), start=1):
        statuses.append(machine.consume_generator_remaining(match_id="match-1", frame_index=frame, remaining=value, confidence_milli=900, evidence_ref=f"e-{frame}").status)
    assert statuses[-1] is TemporalDecisionStatus.CONFIRMED
    assert machine.generator_remaining("match-1") == 5

    for frame in (5, 6, 7):
        result = machine.consume_generator_remaining(match_id="match-1", frame_index=frame, remaining=4, confidence_milli=900, evidence_ref=f"e-{frame}")
    assert result.status is TemporalDecisionStatus.CONFIRMED
    assert machine.generator_remaining("match-1") == 4

    contradiction = machine.consume_generator_remaining(match_id="match-1", frame_index=8, remaining=5, confidence_milli=990, evidence_ref="e-8")
    assert contradiction.status is TemporalDecisionStatus.NEEDS_REVIEW
    assert contradiction.reason_codes == ("GENERATOR_REMAINING_INCREASE",)
    assert machine.generator_remaining("match-1") == 4


def test_generator_invalid_unknown_and_low_confidence_never_confirm() -> None:
    machine = DBDTemporalStateMachines(profile(generator_minimum_frames=1))
    unknown = machine.consume_generator_remaining(match_id="match-1", frame_index=1, remaining=None, confidence_milli=950, evidence_ref="e-1")
    low = machine.consume_generator_remaining(match_id="match-1", frame_index=2, remaining=5, confidence_milli=699, evidence_ref="e-2")
    invalid = machine.consume_generator_remaining(match_id="match-1", frame_index=3, remaining=6, confidence_milli=950, evidence_ref="e-3")
    assert (unknown.status, low.status, invalid.status) == (
        TemporalDecisionStatus.ABSTAINED,
        TemporalDecisionStatus.ABSTAINED,
        TemporalDecisionStatus.NEEDS_REVIEW,
    )
    assert machine.generator_remaining("match-1") is None


def test_chase_hysteresis_follows_all_phases() -> None:
    machine = DBDTemporalStateMachines(profile())
    subject = SurvivorSubject("match-1", 0)
    first = machine.consume_survivor(observation(SurvivorSignalKind.CHASE_STATE, "CHASE_ACTIVE", 1))
    start = machine.consume_survivor(observation(SurvivorSignalKind.CHASE_STATE, "CHASE_ACTIVE", 2))
    end1 = machine.consume_survivor(observation(SurvivorSignalKind.CHASE_STATE, "NOT_CHASE", 3))
    end2 = machine.consume_survivor(observation(SurvivorSignalKind.CHASE_STATE, "NOT_CHASE", 4))
    end3 = machine.consume_survivor(observation(SurvivorSignalKind.CHASE_STATE, "NOT_CHASE", 5))
    assert first.stable_value_after == ChasePhase.CHASE_CANDIDATE.value
    assert start.status is TemporalDecisionStatus.CONFIRMED
    assert start.evidence_refs == ("evidence-1", "evidence-2")
    assert end1.stable_value_after == ChasePhase.CHASE_END_CANDIDATE.value
    assert end2.status is TemporalDecisionStatus.CANDIDATE
    assert end3.status is TemporalDecisionStatus.CONFIRMED
    assert machine.chase_phase(subject) is ChasePhase.NOT_CHASE


def test_chase_state_is_isolated_by_survivor_subject() -> None:
    machine = DBDTemporalStateMachines(profile(chase_start_frames=1))
    confirmed = machine.consume_survivor(observation(SurvivorSignalKind.CHASE_STATE, "CHASE_ACTIVE", 1, slot=2))
    assert confirmed.status is TemporalDecisionStatus.CONFIRMED
    assert machine.chase_phase(SurvivorSubject("match-1", 2)) is ChasePhase.CHASE_ACTIVE
    assert machine.chase_phase(SurvivorSubject("match-1", 1)) is ChasePhase.NOT_CHASE


def test_survivor_state_accepts_recovery_and_rejects_terminal_transition() -> None:
    machine = DBDTemporalStateMachines(profile())
    subject = SurvivorSubject("match-1", 0)
    for frame in (1, 2):
        machine.consume_survivor(observation(SurvivorSignalKind.SURVIVOR_STATE, "DOWNED", frame))
    for frame in (3, 4):
        recovered = machine.consume_survivor(observation(SurvivorSignalKind.SURVIVOR_STATE, "INJURED", frame))
    assert recovered.status is TemporalDecisionStatus.CONFIRMED
    for frame in (5, 6):
        machine.consume_survivor(observation(SurvivorSignalKind.SURVIVOR_STATE, "DEAD", frame))
    for frame in (7, 8):
        invalid = machine.consume_survivor(observation(SurvivorSignalKind.SURVIVOR_STATE, "HEALTHY", frame))
    assert invalid.status is TemporalDecisionStatus.NEEDS_REVIEW
    assert invalid.reason_codes == ("INVALID_SURVIVOR_STATE_TRANSITION",)
    assert machine.survivor_state(subject) == "DEAD"


def test_hook_state_advances_only_same_subject_count_and_hud_reconciles() -> None:
    machine = DBDTemporalStateMachines(profile())
    slot0 = SurvivorSubject("match-1", 0)
    slot1 = SurvivorSubject("match-1", 1)
    for frame in (1, 2):
        machine.consume_survivor(observation(SurvivorSignalKind.HOOK_COUNT, "0", frame, slot=0))
        machine.consume_survivor(observation(SurvivorSignalKind.SURVIVOR_STATE, "DOWNED", frame, slot=0))
    for frame in (3, 4):
        result = machine.consume_survivor(observation(SurvivorSignalKind.SURVIVOR_STATE, "HOOKED", frame, slot=0))
    assert "HOOK_COUNT_ADVANCED_FROM_STATE" in result.reason_codes
    assert machine.hook_count(slot0) == 1
    assert machine.hook_count(slot1) is None
    same = machine.consume_survivor(observation(SurvivorSignalKind.HOOK_COUNT, "1", 5, slot=0))
    assert same.status is TemporalDecisionStatus.UNCHANGED
    for frame in (6, 7):
        advanced = machine.consume_survivor(observation(SurvivorSignalKind.HOOK_COUNT, "2", frame, slot=0))
    assert advanced.status is TemporalDecisionStatus.CONFIRMED
    assert machine.hook_count(slot0) == 2
    assert machine.hook_count(slot1) is None


def test_hooked_without_known_count_baseline_keeps_count_unknown() -> None:
    machine = DBDTemporalStateMachines(profile())
    subject = SurvivorSubject("match-1", 2)
    for frame in (1, 2):
        result = machine.consume_survivor(observation(SurvivorSignalKind.SURVIVOR_STATE, "HOOKED", frame, slot=2))
    assert result.status is TemporalDecisionStatus.CONFIRMED
    assert "HOOK_COUNT_REMAINS_UNKNOWN" in result.reason_codes
    assert machine.hook_count(subject) is None


def test_hook_count_decrease_and_jump_require_review_without_state_change() -> None:
    machine = DBDTemporalStateMachines(profile(hook_count_minimum_frames=1))
    subject = SurvivorSubject("match-1", 3)
    machine.consume_survivor(observation(SurvivorSignalKind.HOOK_COUNT, "0", 1, slot=3))
    jump = machine.consume_survivor(observation(SurvivorSignalKind.HOOK_COUNT, "2", 2, slot=3))
    assert jump.status is TemporalDecisionStatus.NEEDS_REVIEW
    assert machine.hook_count(subject) == 0
    machine.consume_survivor(observation(SurvivorSignalKind.HOOK_COUNT, "1", 3, slot=3))
    decrease = machine.consume_survivor(observation(SurvivorSignalKind.HOOK_COUNT, "0", 4, slot=3))
    assert decrease.status is TemporalDecisionStatus.NEEDS_REVIEW
    assert machine.hook_count(subject) == 1


def test_unknown_low_confidence_and_out_of_order_do_not_mutate_survivor_state() -> None:
    machine = DBDTemporalStateMachines(profile(survivor_state_minimum_frames=1))
    subject = SurvivorSubject("match-1", 0)
    confirmed = machine.consume_survivor(observation(SurvivorSignalKind.SURVIVOR_STATE, "HEALTHY", 10))
    low = machine.consume_survivor(observation(SurvivorSignalKind.SURVIVOR_STATE, "INJURED", 11, confidence=699))
    replay = machine.consume_survivor(observation(SurvivorSignalKind.SURVIVOR_STATE, "INJURED", 10))
    assert confirmed.status is TemporalDecisionStatus.CONFIRMED
    assert low.status is TemporalDecisionStatus.ABSTAINED
    assert replay.status is TemporalDecisionStatus.NEEDS_REVIEW
    assert machine.survivor_state(subject) == "HEALTHY"
