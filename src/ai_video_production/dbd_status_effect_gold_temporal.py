"""Human Gold evaluation and temporal routing for Status Effect recognition."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping, Sequence

from .dbd_hud_visibility import HudVisibility
from .dbd_killer_status_temporal import (
    EffectPolarity,
    EffectSourceKind,
    EffectTemporalDecision,
    KillerStatusTemporalStateMachines,
    StatusEffectDefinition,
    StatusEffectObservation,
)
from .dbd_recorded_video_recognition import DBDFrameRecognition
from .dbd_status_effect_recognition import StatusIconRecognition, StatusIconRecognitionStatus
from .dbd_status_icon_segmentation import StatusIconSegmentationStatus
from .dbd_temporal_state import TemporalDecisionStatus


def _milli(numerator: int, denominator: int) -> int | None:
    return None if denominator == 0 else (numerator * 1000 + denominator // 2) // denominator


@dataclass(frozen=True, slots=True)
class StatusEffectGoldCase:
    case_id: str
    match_id: str
    frame_index: int
    polarity: EffectPolarity
    ordinal: int
    expected_status: StatusIconRecognitionStatus
    expected_effect_id: str | None
    expected_source_kind: EffectSourceKind
    expected_visibility: HudVisibility
    labeler_ref: str

    def __post_init__(self) -> None:
        if not self.case_id.strip() or len(self.case_id) > 256:
            raise ValueError("case_id must be bounded text")
        if not self.match_id.strip() or len(self.match_id) > 256:
            raise ValueError("match_id must be bounded text")
        if self.frame_index < 0 or self.ordinal < 0:
            raise ValueError("Gold frame and ordinal must be non-negative")
        if not isinstance(self.polarity, EffectPolarity) or not isinstance(self.expected_status, StatusIconRecognitionStatus):
            raise ValueError("invalid Status Effect Gold enum")
        if not isinstance(self.expected_source_kind, EffectSourceKind) or not isinstance(self.expected_visibility, HudVisibility):
            raise ValueError("invalid Status Effect Gold source or visibility")
        if not self.labeler_ref.strip() or len(self.labeler_ref) > 1024:
            raise ValueError("labeler_ref must be bounded text")
        if self.expected_status is StatusIconRecognitionStatus.IDENTIFIED:
            if self.expected_effect_id is None or self.expected_source_kind is EffectSourceKind.UNKNOWN:
                raise ValueError("identified Gold requires effect identity and source")
            if self.expected_visibility is not HudVisibility.VISIBLE:
                raise ValueError("identified Gold requires VISIBLE")
        elif self.expected_effect_id is not None or self.expected_source_kind is not EffectSourceKind.UNKNOWN:
            raise ValueError("non-identified Gold cannot claim identity or source")


@dataclass(frozen=True, slots=True)
class StatusEffectGoldReport:
    case_count: int
    status_correct: int
    status_accuracy_milli: int
    identity_evaluable_count: int
    identity_correct: int
    identity_accuracy_milli: int | None
    polarity_correct: int
    polarity_accuracy_milli: int
    source_evaluable_count: int
    source_correct: int
    source_accuracy_milli: int | None
    visibility_correct: int
    visibility_accuracy_milli: int
    abstention_evaluable_count: int
    abstention_correct: int
    abstention_correctness_milli: int | None


class StatusEffectGoldEvaluator:
    @staticmethod
    def evaluate(
        cases: Iterable[StatusEffectGoldCase],
        observations: Iterable[tuple[str, int, StatusIconRecognition]],
    ) -> StatusEffectGoldReport:
        case_rows = tuple(cases)
        observation_rows = tuple(observations)
        case_keys = tuple(
            (item.match_id, item.frame_index, item.polarity, item.ordinal)
            for item in case_rows
        )
        if len(set(case_keys)) != len(case_keys):
            raise ValueError("Status Effect Gold cases must have unique coordinates")
        if len({item.case_id for item in case_rows}) != len(case_rows):
            raise ValueError("Status Effect Gold case_id values must be unique")
        by_key = {
            (match_id, frame_index, item.polarity, item.ordinal): item
            for match_id, frame_index, item in observation_rows
        }
        if len(by_key) != len(observation_rows):
            raise ValueError("Status Effect Gold observations must have unique coordinates")
        status_ok = identity_n = identity_ok = polarity_ok = 0
        source_n = source_ok = visibility_ok = abstention_n = abstention_ok = 0
        for case in case_rows:
            item = by_key.get((case.match_id, case.frame_index, case.polarity, case.ordinal))
            predicted_status = StatusIconRecognitionStatus.ABSTAINED if item is None else item.status
            status_ok += int(predicted_status is case.expected_status)
            polarity_ok += int(item is not None and item.polarity is case.polarity)
            predicted_visibility = HudVisibility.UNKNOWN if item is None else item.visibility
            visibility_ok += int(predicted_visibility is case.expected_visibility)
            if case.expected_effect_id is not None:
                identity_n += 1
                identity_ok += int(item is not None and item.effect_id == case.expected_effect_id)
                source_n += 1
                source_ok += int(item is not None and item.source_kind is case.expected_source_kind)
            if case.expected_status is not StatusIconRecognitionStatus.IDENTIFIED:
                abstention_n += 1
                abstention_ok += int(item is None or item.effect_id is None)
        count = len(case_rows)
        return StatusEffectGoldReport(
            count, status_ok, _milli(status_ok, count) or 0,
            identity_n, identity_ok, _milli(identity_ok, identity_n),
            polarity_ok, _milli(polarity_ok, count) or 0,
            source_n, source_ok, _milli(source_ok, source_n),
            visibility_ok, _milli(visibility_ok, count) or 0,
            abstention_n, abstention_ok, _milli(abstention_ok, abstention_n),
        )


@dataclass(frozen=True, slots=True)
class StatusEffectHumanCorrection:
    case_id: str
    original_status: StatusIconRecognitionStatus
    original_effect_id: str | None
    corrected_status: StatusIconRecognitionStatus
    corrected_effect_id: str | None
    reviewer_ref: str
    reason: str
    provenance_ref: str

    def __post_init__(self) -> None:
        for name in ("case_id", "reviewer_ref", "reason", "provenance_ref"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip() or len(value) > 1024:
                raise ValueError(f"{name} must be bounded text")
        if (self.original_status is StatusIconRecognitionStatus.IDENTIFIED) != (self.original_effect_id is not None):
            raise ValueError("original review identity and status must agree")
        if (self.corrected_status is StatusIconRecognitionStatus.IDENTIFIED) != (self.corrected_effect_id is not None):
            raise ValueError("corrected review identity and status must agree")


class StatusEffectTemporalRouteStatus(str, Enum):
    OBSERVED = "OBSERVED"
    ABSENCE_OBSERVED = "ABSENCE_OBSERVED"
    ABSTAINED = "ABSTAINED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


@dataclass(frozen=True, slots=True)
class StatusEffectTemporalRoute:
    status: StatusEffectTemporalRouteStatus
    polarity: EffectPolarity
    ordinal: int | None
    effect_id: str | None
    evidence_ref: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StatusEffectTemporalBatchResult:
    frame_index: int
    decisions: tuple[EffectTemporalDecision, ...]
    routes: tuple[StatusEffectTemporalRoute, ...]


class StatusEffectTemporalBridge:
    """Route R5B frame recognition into R3C without guessing through UNKNOWN."""

    def __init__(
        self,
        machines: KillerStatusTemporalStateMachines,
        *,
        definitions: Sequence[StatusEffectDefinition],
        absence_confidence_milli: int = 900,
    ) -> None:
        if not isinstance(machines, KillerStatusTemporalStateMachines):
            raise ValueError("machines must be KillerStatusTemporalStateMachines")
        self.machines = machines
        definitions = tuple(definitions)
        if any(not isinstance(item, StatusEffectDefinition) for item in definitions):
            raise ValueError("definitions must contain StatusEffectDefinition values")
        self.definitions = {item.effect_id: item for item in definitions}
        if not self.definitions or len(self.definitions) != len(definitions):
            raise ValueError("definitions must be non-empty and unique")
        if definitions != machines.profile.status_effects:
            raise ValueError("definitions must exactly match the temporal profile")
        if not 0 <= absence_confidence_milli <= 1000:
            raise ValueError("absence_confidence_milli must be 0..1000")
        self.absence_confidence_milli = absence_confidence_milli
        self._tracked: dict[tuple[str, int | None, EffectPolarity], set[str]] = {}

    @staticmethod
    def _artifact_ref(frame: DBDFrameRecognition, roi_id: str) -> str:
        artifact = next((item for item in frame.slice_artifacts if item.roi_id == roi_id), None)
        return (
            artifact.evidence_ref
            if artifact is not None
            else f"recognition://status-effect-region-evidence-unavailable/{roi_id}/{frame.frame_index}"
        )

    def consume_frame(
        self,
        frame: DBDFrameRecognition,
        *,
        match_id: str,
        survivor_slots: Mapping[str, int] | None = None,
    ) -> StatusEffectTemporalBatchResult:
        if not isinstance(frame, DBDFrameRecognition):
            raise ValueError("frame must be DBDFrameRecognition")
        if not isinstance(match_id, str) or not match_id.strip() or len(match_id) > 256:
            raise ValueError("match_id must be bounded text")
        decisions: list[EffectTemporalDecision] = []
        routes: list[StatusEffectTemporalRoute] = []
        visible: dict[tuple[int | None, EffectPolarity], set[str]] = {}
        survivor_slots = {} if survivor_slots is None else survivor_slots
        if not isinstance(survivor_slots, Mapping):
            raise ValueError("survivor_slots must be a mapping")
        if any(
            effect_id not in self.definitions
            or not isinstance(slot, int)
            or isinstance(slot, bool)
            or not 0 <= slot <= 3
            for effect_id, slot in survivor_slots.items()
        ):
            raise ValueError("survivor_slots must map registered effects to slots 0..3")
        routed_keys: set[tuple[EffectPolarity, int]] = set()
        recognition_keys = tuple((item.polarity, item.ordinal) for item in frame.status_effects)
        if len(set(recognition_keys)) != len(recognition_keys):
            raise ValueError("Status Effect recognitions must have unique coordinates")

        for item in frame.status_effects:
            if item.status is not StatusIconRecognitionStatus.IDENTIFIED or item.effect_id is None:
                route_status = (
                    StatusEffectTemporalRouteStatus.NEEDS_REVIEW
                    if item.status is StatusIconRecognitionStatus.CONTRADICTION
                    else StatusEffectTemporalRouteStatus.ABSTAINED
                )
                routes.append(StatusEffectTemporalRoute(
                    route_status, item.polarity, item.ordinal, None,
                    item.evidence_ref, item.reason_codes,
                ))
                continue
            definition = self.definitions.get(item.effect_id)
            if definition is None:
                routes.append(StatusEffectTemporalRoute(
                    StatusEffectTemporalRouteStatus.NEEDS_REVIEW, item.polarity,
                    item.ordinal, item.effect_id, item.evidence_ref,
                    ("UNREGISTERED_STATUS_EFFECT",),
                ))
                continue
            if definition.polarity is not item.polarity or definition.source_kind is not item.source_kind:
                routes.append(StatusEffectTemporalRoute(
                    StatusEffectTemporalRouteStatus.NEEDS_REVIEW, item.polarity,
                    item.ordinal, item.effect_id, item.evidence_ref,
                    ("STATUS_EFFECT_NAMESPACE_MISMATCH",),
                ))
                continue
            slot = survivor_slots.get(item.effect_id)
            if definition.survivor_scoped != (slot is not None):
                routes.append(StatusEffectTemporalRoute(
                    StatusEffectTemporalRouteStatus.NEEDS_REVIEW, item.polarity,
                    item.ordinal, item.effect_id, item.evidence_ref,
                    ("EFFECT_SCOPE_MISMATCH",),
                ))
                continue
            observation = item.to_temporal_observation(
                match_id=match_id, frame_index=frame.frame_index, survivor_slot=slot,
            )
            decision = self.machines.consume_status(observation)
            decisions.append(decision)
            if decision.status in {TemporalDecisionStatus.ABSTAINED, TemporalDecisionStatus.NEEDS_REVIEW}:
                routes.append(StatusEffectTemporalRoute(
                    StatusEffectTemporalRouteStatus.NEEDS_REVIEW, item.polarity,
                    item.ordinal, item.effect_id, item.evidence_ref,
                    decision.reason_codes,
                ))
                continue
            routed_keys.add((item.polarity, item.ordinal))
            visible.setdefault((slot, item.polarity), set()).add(item.effect_id)
            self._tracked.setdefault((match_id, slot, item.polarity), set()).add(item.effect_id)
            routes.append(StatusEffectTemporalRoute(
                StatusEffectTemporalRouteStatus.OBSERVED, item.polarity,
                item.ordinal, item.effect_id, item.evidence_ref,
                ("STATUS_EFFECT_OBSERVATION_ROUTED",),
            ))

        for region in frame.status_effect_regions:
            has_artifact = any(item.roi_id == region.region_roi_id for item in frame.slice_artifacts)
            reliable = has_artifact and (region.status is StatusIconSegmentationStatus.EMPTY or (
                region.status is StatusIconSegmentationStatus.SEGMENTED
                and all(
                    (region.polarity, candidate.ordinal) in routed_keys
                    for candidate in region.candidates
                )
            ))
            if not reliable:
                routes.append(StatusEffectTemporalRoute(
                    StatusEffectTemporalRouteStatus.ABSTAINED, region.polarity,
                    None, None, self._artifact_ref(frame, region.region_roi_id),
                    ("STATUS_EFFECT_REGION_NOT_IDENTITY_COMPLETE",),
                ))
                continue
            tracked_keys = [
                key for key in self._tracked
                if key[0] == match_id and key[2] is region.polarity
            ]
            for key in tracked_keys:
                _, slot, polarity = key
                missing = self._tracked[key] - visible.get((slot, polarity), set())
                for effect_id in sorted(missing):
                    definition = self.definitions[effect_id]
                    evidence_ref = self._artifact_ref(frame, region.region_roi_id)
                    observation = StatusEffectObservation(
                        match_id, slot, effect_id, polarity, definition.source_kind,
                        False, None, None, self.absence_confidence_milli,
                        frame.frame_index, evidence_ref,
                    )
                    decision = self.machines.consume_status(observation)
                    decisions.append(decision)
                    routes.append(StatusEffectTemporalRoute(
                        StatusEffectTemporalRouteStatus.ABSENCE_OBSERVED,
                        polarity, None, effect_id, evidence_ref,
                        ("STATUS_EFFECT_ABSENCE_ROUTED",),
                    ))
                    if (
                        decision.status in {TemporalDecisionStatus.CONFIRMED, TemporalDecisionStatus.UNCHANGED}
                        and decision.state_after.active is False
                    ):
                        self._tracked[key].discard(effect_id)
        return StatusEffectTemporalBatchResult(
            frame.frame_index, tuple(decisions), tuple(routes),
        )


__all__ = [
    "StatusEffectGoldCase", "StatusEffectGoldEvaluator", "StatusEffectGoldReport",
    "StatusEffectHumanCorrection", "StatusEffectTemporalBatchResult",
    "StatusEffectTemporalBridge", "StatusEffectTemporalRoute", "StatusEffectTemporalRouteStatus",
]
