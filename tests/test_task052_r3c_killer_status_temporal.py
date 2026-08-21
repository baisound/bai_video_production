from __future__ import annotations

from dataclasses import replace

from ai_video_production.dbd_killer_status_temporal import (
    EffectPolarity, EffectSourceKind, EffectTemporalDomain, KillerEffectDefinition,
    KillerSpecificObservation, KillerStatusTemporalProfile, KillerStatusTemporalStateMachines,
    StatusEffectDefinition, StatusEffectObservation,
)
from ai_video_production.dbd_temporal_state import TemporalDecisionStatus


def profile() -> KillerStatusTemporalProfile:
    return KillerStatusTemporalProfile(
        profile_id="dbd_r3c_test", profile_version=1,
        killer_effects=(
            KillerEffectDefinition("killer_onryo", "condemn", True, max_stage=7, stage_monotonic=True, progress_monotonic=True),
            KillerEffectDefinition("killer_ghost_face", "mark_progress", True, progress_monotonic=False),
        ),
        status_effects=(
            StatusEffectDefinition("haste", EffectPolarity.POSITIVE, EffectSourceKind.PERK, max_stack_or_level=3),
            StatusEffectDefinition("exposed", EffectPolarity.NEGATIVE, EffectSourceKind.KILLER_POWER),
        ),
    )


def killer(frame: int, **changes) -> KillerSpecificObservation:
    values = dict(match_id="match-1", survivor_slot=0, killer_id="killer_onryo", effect_id="condemn", active=True, stage=2, progress_milli=300, confidence_milli=900, frame_index=frame, evidence_ref=f"k-{frame}")
    values.update(changes)
    return KillerSpecificObservation(**values)


def status(frame: int, **changes) -> StatusEffectObservation:
    values = dict(match_id="match-1", survivor_slot=0, effect_id="haste", polarity=EffectPolarity.POSITIVE, source_kind=EffectSourceKind.PERK, active=True, stack_or_level=1, progress_milli=None, confidence_milli=900, frame_index=frame, evidence_ref=f"s-{frame}")
    values.update(changes)
    return StatusEffectObservation(**values)


def test_unknown_killer_abstains_and_wrong_killer_namespace_needs_review() -> None:
    machine = KillerStatusTemporalStateMachines(profile())
    unknown = machine.consume_killer(killer(1, killer_id=None, effect_id=None, active=None, stage=None, progress_milli=None))
    mismatch = machine.consume_killer(killer(2, killer_id="killer_ghost_face"))
    assert unknown.status is TemporalDecisionStatus.ABSTAINED
    assert mismatch.status is TemporalDecisionStatus.NEEDS_REVIEW
    assert mismatch.reason_codes == ("KILLER_EFFECT_NAMESPACE_MISMATCH",)


def test_killer_effect_appearance_and_value_change_are_temporally_confirmed() -> None:
    machine = KillerStatusTemporalStateMachines(profile())
    first = machine.consume_killer(killer(1))
    appeared = machine.consume_killer(killer(2))
    value1 = machine.consume_killer(killer(3, stage=3, progress_milli=500))
    value2 = machine.consume_killer(killer(4, stage=3, progress_milli=500))
    assert first.status is TemporalDecisionStatus.CANDIDATE
    assert appeared.status is TemporalDecisionStatus.CONFIRMED
    assert appeared.reason_codes == ("EFFECT_APPEARED",)
    assert value1.status is TemporalDecisionStatus.CANDIDATE
    assert value2.status is TemporalDecisionStatus.CONFIRMED
    assert value2.state_after.stage == 3


def test_monotonic_killer_progress_regression_needs_review_without_mutation() -> None:
    machine = KillerStatusTemporalStateMachines(profile())
    machine.consume_killer(killer(1)); machine.consume_killer(killer(2))
    regression = machine.consume_killer(killer(3, stage=1, progress_milli=200))
    assert regression.status is TemporalDecisionStatus.NEEDS_REVIEW
    assert "STAGE_REGRESSION" in regression.reason_codes
    assert machine.state(EffectTemporalDomain.KILLER_SPECIFIC_HUD, "match-1", 0, "condemn").stage == 2


def test_contradiction_clears_incomplete_value_candidate() -> None:
    machine = KillerStatusTemporalStateMachines(profile())
    machine.consume_killer(killer(1)); machine.consume_killer(killer(2))
    pending = machine.consume_killer(killer(3, stage=3, progress_milli=500))
    contradiction = machine.consume_killer(killer(4, stage=1, progress_milli=200))
    after = machine.consume_killer(killer(5, stage=3, progress_milli=500))
    assert pending.status is TemporalDecisionStatus.CANDIDATE
    assert contradiction.status is TemporalDecisionStatus.NEEDS_REVIEW
    assert after.status is TemporalDecisionStatus.CANDIDATE


def test_nonmonotonic_killer_profile_allows_progress_decay_after_debounce() -> None:
    machine = KillerStatusTemporalStateMachines(profile())
    base = killer(1, killer_id="killer_ghost_face", effect_id="mark_progress", stage=None, progress_milli=700)
    machine.consume_killer(base); machine.consume_killer(replace(base, frame_index=2, evidence_ref="k-2"))
    lower = replace(base, frame_index=3, progress_milli=400, evidence_ref="k-3")
    machine.consume_killer(lower)
    changed = machine.consume_killer(replace(lower, frame_index=4, evidence_ref="k-4"))
    assert changed.status is TemporalDecisionStatus.CONFIRMED
    assert changed.state_after.progress_milli == 400


def test_positive_and_negative_status_effects_are_independent_multi_object_state() -> None:
    machine = KillerStatusTemporalStateMachines(profile())
    for frame in (1, 2):
        haste = machine.consume_status(status(frame))
        exposed = machine.consume_status(status(frame, effect_id="exposed", polarity=EffectPolarity.NEGATIVE, source_kind=EffectSourceKind.KILLER_POWER, stack_or_level=None, evidence_ref=f"e-{frame}"))
    assert haste.status is TemporalDecisionStatus.CONFIRMED
    assert exposed.status is TemporalDecisionStatus.CONFIRMED
    assert machine.state(EffectTemporalDomain.STATUS_EFFECT, "match-1", 0, "haste").active is True
    assert machine.state(EffectTemporalDomain.STATUS_EFFECT, "match-1", 0, "exposed").active is True


def test_status_effect_disappearance_uses_longer_hysteresis() -> None:
    machine = KillerStatusTemporalStateMachines(profile())
    machine.consume_status(status(1)); machine.consume_status(status(2))
    for frame in (3, 4):
        pending = machine.consume_status(status(frame, active=False, stack_or_level=None, progress_milli=None))
        assert pending.status is TemporalDecisionStatus.CANDIDATE
    gone = machine.consume_status(status(5, active=False, stack_or_level=None, progress_milli=None))
    assert gone.status is TemporalDecisionStatus.CONFIRMED
    assert gone.reason_codes == ("EFFECT_DISAPPEARED",)


def test_status_polarity_hard_negative_and_unregistered_icon_fail_closed() -> None:
    machine = KillerStatusTemporalStateMachines(profile())
    mismatch = machine.consume_status(status(1, polarity=EffectPolarity.NEGATIVE))
    unknown = machine.consume_status(status(2, effect_id="unknown_icon"))
    assert mismatch.status is TemporalDecisionStatus.NEEDS_REVIEW
    assert mismatch.reason_codes == ("STATUS_EFFECT_NAMESPACE_MISMATCH",)
    assert unknown.status is TemporalDecisionStatus.ABSTAINED


def test_low_confidence_and_out_of_order_do_not_advance_effect_state() -> None:
    machine = KillerStatusTemporalStateMachines(profile())
    low = machine.consume_status(status(10, confidence_milli=699))
    replay = machine.consume_status(status(9))
    assert low.status is TemporalDecisionStatus.ABSTAINED
    assert replay.status is TemporalDecisionStatus.NEEDS_REVIEW
    assert machine.state(EffectTemporalDomain.STATUS_EFFECT, "match-1", 0, "haste").active is None
