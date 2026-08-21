from __future__ import annotations

from dataclasses import replace

import pytest

from ai_video_production.dbd_hud_visibility import HudVisibility
from ai_video_production.dbd_killer_status_temporal import (
    EffectPolarity,
    EffectSourceKind,
    EffectTemporalDomain,
    KillerStatusTemporalProfile,
    KillerStatusTemporalStateMachines,
    StatusEffectDefinition,
)
from ai_video_production.dbd_recorded_video_recognition import DBDFrameRecognition, SliceArtifact
from ai_video_production.dbd_status_effect_gold_temporal import (
    StatusEffectGoldCase,
    StatusEffectGoldEvaluator,
    StatusEffectHumanCorrection,
    StatusEffectTemporalBridge,
    StatusEffectTemporalRouteStatus,
)
from ai_video_production.dbd_status_effect_recognition import (
    StatusIconRecognition,
    StatusIconRecognitionStatus,
)
from ai_video_production.dbd_status_icon_segmentation import (
    StatusIconSegmentCandidate,
    StatusIconSegmentationResult,
    StatusIconSegmentationStatus,
)
from ai_video_production.dbd_temporal_state import TemporalDecisionStatus
from ai_video_production.dbd_vision_slices import NormalizedROI


DEFINITIONS = (
    StatusEffectDefinition(
        "status_bloodlust", EffectPolarity.POSITIVE, EffectSourceKind.GAME_MECHANIC,
        survivor_scoped=False,
    ),
    StatusEffectDefinition(
        "status_hindered", EffectPolarity.NEGATIVE, EffectSourceKind.PERK,
        survivor_scoped=False,
    ),
    StatusEffectDefinition(
        "status_exhausted", EffectPolarity.NEGATIVE, EffectSourceKind.PERK,
        survivor_scoped=True,
    ),
)


def _candidate(polarity: EffectPolarity, ordinal: int = 0) -> StatusIconSegmentCandidate:
    region = (
        "bottom_right_positive_effects"
        if polarity is EffectPolarity.POSITIVE else "bottom_right_negative_effects"
    )
    return StatusIconSegmentCandidate(
        ordinal, polarity, region,
        NormalizedROI(f"{region}/segment_{ordinal}", 0.1, 0.1, 0.3, 0.3),
        20, 900, "sha256:" + f"{ordinal + 1:x}" * 64,
    )


def _recognized(
    polarity: EffectPolarity,
    *,
    effect_id: str = "status_bloodlust",
    source_kind: EffectSourceKind = EffectSourceKind.GAME_MECHANIC,
    status: StatusIconRecognitionStatus = StatusIconRecognitionStatus.IDENTIFIED,
) -> StatusIconRecognition:
    region = (
        "bottom_right_positive_effects"
        if polarity is EffectPolarity.POSITIVE else "bottom_right_negative_effects"
    )
    identified = status is StatusIconRecognitionStatus.IDENTIFIED
    return StatusIconRecognition(
        0, region, polarity, status,
        effect_id if identified else None,
        source_kind if identified else EffectSourceKind.UNKNOWN,
        HudVisibility.VISIBLE if identified else HudVisibility.UNKNOWN,
        900, (), f"recognition://status/{polarity.value}/0",
        ("STATUS_EFFECT_IDENTITY_MATCHED",) if identified else ("STATUS_EFFECT_IDENTITY_UNKNOWN",),
    )


def _frame(
    index: int,
    *,
    polarity: EffectPolarity = EffectPolarity.POSITIVE,
    recognition: StatusIconRecognition | None = None,
    status: StatusIconSegmentationStatus = StatusIconSegmentationStatus.SEGMENTED,
    include_artifact: bool = True,
) -> DBDFrameRecognition:
    candidate = _candidate(polarity)
    region_id = candidate.region_roi_id
    segmentation = StatusIconSegmentationResult(
        polarity, region_id, status,
        (candidate,) if status is StatusIconSegmentationStatus.SEGMENTED else (),
        (
            ("STATUS_ICON_COMPONENTS_SEGMENTED",)
            if status is StatusIconSegmentationStatus.SEGMENTED
            else ("NO_STATUS_ICON_COMPONENTS",)
        ),
    )
    artifacts = (
        (SliceArtifact(region_id, index, "sha256:" + "a" * 64),)
        if include_artifact else ()
    )
    return DBDFrameRecognition(
        index, (), (), None, None, artifacts,
        status_effect_regions=(segmentation,),
        status_effects=(() if recognition is None else (recognition,)),
    )


def _bridge(*, appearance: int = 1, disappearance: int = 2) -> StatusEffectTemporalBridge:
    profile = KillerStatusTemporalProfile(
        "status_gold_temporal", 1, (), DEFINITIONS,
        minimum_confidence_milli=700,
        appearance_frames=appearance,
        disappearance_frames=disappearance,
        value_frames=1,
    )
    machines = KillerStatusTemporalStateMachines(profile)
    return StatusEffectTemporalBridge(machines, definitions=DEFINITIONS)


def test_gold_reports_identity_polarity_source_visibility_and_abstention() -> None:
    identified = _recognized(EffectPolarity.POSITIVE)
    hard_negative = _recognized(
        EffectPolarity.NEGATIVE,
        status=StatusIconRecognitionStatus.HARD_NEGATIVE,
    )
    cases = (
        StatusEffectGoldCase(
            "case-1", "match-gold", 10, EffectPolarity.POSITIVE, 0,
            StatusIconRecognitionStatus.IDENTIFIED, "status_bloodlust",
            EffectSourceKind.GAME_MECHANIC, HudVisibility.VISIBLE, "human://gold/a",
        ),
        StatusEffectGoldCase(
            "case-2", "match-gold", 11, EffectPolarity.NEGATIVE, 0,
            StatusIconRecognitionStatus.HARD_NEGATIVE, None,
            EffectSourceKind.UNKNOWN, HudVisibility.UNKNOWN, "human://gold/b",
        ),
        StatusEffectGoldCase(
            "case-3", "match-gold", 12, EffectPolarity.POSITIVE, 0,
            StatusIconRecognitionStatus.ABSTAINED, None,
            EffectSourceKind.UNKNOWN, HudVisibility.UNKNOWN, "human://gold/c",
        ),
    )
    report = StatusEffectGoldEvaluator.evaluate(
        cases,
        (("match-gold", 10, identified), ("match-gold", 11, hard_negative)),
    )
    assert report.case_count == 3
    assert report.status_accuracy_milli == 1000
    assert report.identity_accuracy_milli == 1000
    assert report.source_accuracy_milli == 1000
    assert report.visibility_accuracy_milli == 1000
    assert report.abstention_correctness_milli == 1000


def test_gold_rejects_duplicate_case_coordinates_and_ids() -> None:
    case = StatusEffectGoldCase(
        "gold-1", "match-a", 1, EffectPolarity.POSITIVE, 0,
        StatusIconRecognitionStatus.ABSTAINED, None, EffectSourceKind.UNKNOWN,
        HudVisibility.UNKNOWN, "labeler://human/a",
    )
    with pytest.raises(ValueError, match="coordinates"):
        StatusEffectGoldEvaluator.evaluate((case, case), ())
    with pytest.raises(ValueError, match="case_id"):
        StatusEffectGoldEvaluator.evaluate((case, replace(case, frame_index=2)), ())


def test_human_correction_retains_original_corrected_reviewer_reason_and_provenance() -> None:
    correction = StatusEffectHumanCorrection(
        "case-review", StatusIconRecognitionStatus.ABSTAINED, None,
        StatusIconRecognitionStatus.IDENTIFIED, "status_bloodlust",
        "human://reviewer/owner", "目視でアイコンを確認", "video://owned#frame=20",
    )
    assert correction.original_effect_id is None
    assert correction.corrected_effect_id == "status_bloodlust"
    with pytest.raises(ValueError, match="identity and status"):
        replace(correction, corrected_effect_id=None)


def test_identified_effect_routes_active_then_reliable_empty_routes_temporal_disappearance() -> None:
    bridge = _bridge()
    first = bridge.consume_frame(
        _frame(1, recognition=_recognized(EffectPolarity.POSITIVE)),
        match_id="match-temporal",
    )
    assert first.decisions[0].status is TemporalDecisionStatus.CONFIRMED
    assert first.decisions[0].state_after.active is True
    assert first.routes[0].status is StatusEffectTemporalRouteStatus.OBSERVED

    second = bridge.consume_frame(
        _frame(2, status=StatusIconSegmentationStatus.EMPTY),
        match_id="match-temporal",
    )
    assert second.decisions[0].status is TemporalDecisionStatus.CANDIDATE
    assert second.routes[0].status is StatusEffectTemporalRouteStatus.ABSENCE_OBSERVED
    third = bridge.consume_frame(
        _frame(3, status=StatusIconSegmentationStatus.EMPTY),
        match_id="match-temporal",
    )
    assert third.decisions[0].status is TemporalDecisionStatus.CONFIRMED
    assert third.decisions[0].state_after.active is False
    assert bridge.machines.state(
        EffectTemporalDomain.STATUS_EFFECT, "match-temporal", None, "status_bloodlust",
    ).active is False


@pytest.mark.parametrize("include_artifact", (True, False))
def test_unknown_or_missing_exact_region_evidence_never_implies_disappearance(include_artifact: bool) -> None:
    bridge = _bridge()
    bridge.consume_frame(
        _frame(1, recognition=_recognized(EffectPolarity.POSITIVE)),
        match_id="match-unknown",
    )
    unknown = _recognized(
        EffectPolarity.POSITIVE,
        status=StatusIconRecognitionStatus.ABSTAINED,
    )
    result = bridge.consume_frame(
        _frame(2, recognition=unknown, include_artifact=include_artifact),
        match_id="match-unknown",
    )
    assert result.decisions == ()
    assert all(route.status is not StatusEffectTemporalRouteStatus.ABSENCE_OBSERVED for route in result.routes)
    assert bridge.machines.state(
        EffectTemporalDomain.STATUS_EFFECT, "match-unknown", None, "status_bloodlust",
    ).active is True


def test_survivor_scoped_effect_requires_exact_subject_before_temporal_routing() -> None:
    bridge = _bridge()
    exhausted = _recognized(
        EffectPolarity.NEGATIVE,
        effect_id="status_exhausted",
        source_kind=EffectSourceKind.PERK,
    )
    missing = bridge.consume_frame(
        _frame(5, polarity=EffectPolarity.NEGATIVE, recognition=exhausted),
        match_id="match-subject",
    )
    assert missing.decisions == ()
    assert missing.routes[0].status is StatusEffectTemporalRouteStatus.NEEDS_REVIEW
    assert missing.routes[0].reason_codes == ("EFFECT_SCOPE_MISMATCH",)

    routed = bridge.consume_frame(
        _frame(6, polarity=EffectPolarity.NEGATIVE, recognition=exhausted),
        match_id="match-subject",
        survivor_slots={"status_exhausted": 2},
    )
    assert routed.decisions[0].status is TemporalDecisionStatus.CONFIRMED
    assert routed.decisions[0].survivor_slot == 2


def test_temporal_bridge_rejects_profile_drift_duplicate_coordinates_and_bad_slots() -> None:
    profile = KillerStatusTemporalProfile(
        "status_profile", 1, (), DEFINITIONS,
        minimum_confidence_milli=700, appearance_frames=1,
        disappearance_frames=2, value_frames=1,
    )
    machines = KillerStatusTemporalStateMachines(profile)
    with pytest.raises(ValueError, match="exactly match"):
        StatusEffectTemporalBridge(machines, definitions=DEFINITIONS[:-1])

    bridge = StatusEffectTemporalBridge(machines, definitions=DEFINITIONS)
    observed = _recognized(EffectPolarity.POSITIVE)
    duplicate = replace(observed, evidence_ref="recognition://status/duplicate")
    with pytest.raises(ValueError, match="unique polarity/ordinal"):
        replace(_frame(1, recognition=observed), status_effects=(observed, duplicate))
    with pytest.raises(ValueError, match="slots 0..3"):
        bridge.consume_frame(
            _frame(1, recognition=observed), match_id="match-a",
            survivor_slots={"status_exhausted": 4},
        )


def test_temporal_bridge_does_not_track_recognizer_namespace_contradiction() -> None:
    bridge = _bridge(appearance=1, disappearance=1)
    mismatched = _recognized(
        EffectPolarity.POSITIVE,
        source_kind=EffectSourceKind.PERK,
    )
    result = bridge.consume_frame(_frame(1, recognition=mismatched), match_id="match-a")
    assert result.decisions == ()
    assert result.routes[0].status is StatusEffectTemporalRouteStatus.NEEDS_REVIEW
    assert result.routes[0].reason_codes == ("STATUS_EFFECT_NAMESPACE_MISMATCH",)
    empty = bridge.consume_frame(
        _frame(2, recognition=None, status=StatusIconSegmentationStatus.EMPTY),
        match_id="match-a",
    )
    assert all(route.status is not StatusEffectTemporalRouteStatus.ABSENCE_OBSERVED for route in empty.routes)
