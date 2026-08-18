"""TASK-050 R6 Human Gold for HUD identity/visibility observations."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

from .dbd_hud_visibility import HudVisibility
from .dbd_observation_envelope import DbDObservationEnvelope


def _milli(n: int, d: int) -> int | None:
    return None if d == 0 else (n * 1000 + d // 2) // d


@dataclass(frozen=True, slots=True)
class HudObservationGoldCase:
    case_id: str
    observation_type: str
    frame_index: int
    expected_visibility: HudVisibility
    expected_entity_id: str | None
    expected_abstention: bool
    labeler_ref: str

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("case_id is required")
        if self.frame_index < 0:
            raise ValueError("frame_index must be non-negative")
        if not self.labeler_ref.strip():
            raise ValueError("labeler_ref is required")
        if self.expected_abstention and self.expected_entity_id is not None:
            raise ValueError("abstention Gold must not assert entity identity")
        if self.expected_visibility in {
            HudVisibility.HIDDEN,
            HudVisibility.UNREADABLE,
            HudVisibility.UNKNOWN,
        } and self.expected_entity_id is not None:
            raise ValueError("hidden/unreadable/unknown Gold must not require visible identity")


@dataclass(frozen=True, slots=True)
class HudObservationGoldReport:
    case_count: int
    visibility_correct: int
    visibility_accuracy_milli: int
    hidden_case_count: int
    hidden_correct: int
    hidden_detection_accuracy_milli: int | None
    partial_case_count: int
    partial_correct: int
    partial_occlusion_accuracy_milli: int | None
    unreadable_case_count: int
    unreadable_correct: int
    unreadable_accuracy_milli: int | None
    identity_evaluable_count: int
    identity_correct: int
    identity_accuracy_milli: int | None
    expected_abstention_count: int
    correct_abstention_count: int
    abstention_correctness_milli: int | None


class HudObservationGoldEvaluator:
    @staticmethod
    def evaluate(
        cases: Iterable[HudObservationGoldCase],
        observations: Iterable[DbDObservationEnvelope],
    ) -> HudObservationGoldReport:
        case_rows = tuple(cases)
        obs_rows = tuple(observations)
        by_key = {(obs.observation_type.value, obs.frame_start): obs for obs in obs_rows}
        if len(by_key) != len(obs_rows):
            raise ValueError("observations must be unique by observation_type/frame_start")

        visibility_correct = hidden_n = hidden_ok = 0
        partial_n = partial_ok = unreadable_n = unreadable_ok = 0
        identity_n = identity_ok = abstention_n = abstention_ok = 0

        for case in case_rows:
            obs = by_key.get((case.observation_type, case.frame_index))
            predicted_visibility = HudVisibility.UNKNOWN if obs is None else obs.visibility
            visibility_correct += int(predicted_visibility is case.expected_visibility)

            if case.expected_visibility is HudVisibility.HIDDEN:
                hidden_n += 1
                hidden_ok += int(predicted_visibility is HudVisibility.HIDDEN)
            elif case.expected_visibility is HudVisibility.PARTIALLY_OCCLUDED:
                partial_n += 1
                partial_ok += int(predicted_visibility is HudVisibility.PARTIALLY_OCCLUDED)
            elif case.expected_visibility is HudVisibility.UNREADABLE:
                unreadable_n += 1
                unreadable_ok += int(predicted_visibility is HudVisibility.UNREADABLE)

            if case.expected_entity_id is not None:
                identity_n += 1
                identity_ok += int(
                    obs is not None
                    and obs.visibility is HudVisibility.VISIBLE
                    and obs.entity_id == case.expected_entity_id
                )

            if case.expected_abstention:
                abstention_n += 1
                abstention_ok += int(
                    obs is None
                    or obs.entity_id is None
                    or obs.visibility is not HudVisibility.VISIBLE
                )

        count = len(case_rows)
        return HudObservationGoldReport(
            case_count=count,
            visibility_correct=visibility_correct,
            visibility_accuracy_milli=_milli(visibility_correct, count) or 0,
            hidden_case_count=hidden_n,
            hidden_correct=hidden_ok,
            hidden_detection_accuracy_milli=_milli(hidden_ok, hidden_n),
            partial_case_count=partial_n,
            partial_correct=partial_ok,
            partial_occlusion_accuracy_milli=_milli(partial_ok, partial_n),
            unreadable_case_count=unreadable_n,
            unreadable_correct=unreadable_ok,
            unreadable_accuracy_milli=_milli(unreadable_ok, unreadable_n),
            identity_evaluable_count=identity_n,
            identity_correct=identity_ok,
            identity_accuracy_milli=_milli(identity_ok, identity_n),
            expected_abstention_count=abstention_n,
            correct_abstention_count=abstention_ok,
            abstention_correctness_milli=_milli(abstention_ok, abstention_n),
        )
