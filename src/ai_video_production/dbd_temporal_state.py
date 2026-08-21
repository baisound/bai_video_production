"""TASK-052 R3A deterministic temporal reconciliation for DbD HUD evidence.

Detector outputs are observations, not event truth.  This module owns only
profile-bound debounce, hysteresis, subject isolation, and contradiction
reporting.  CGEL production remains a downstream responsibility.
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from enum import Enum
from typing import Deque

from .dbd_observation_envelope import (
    DbDObservationEnvelope,
    SurvivorSignalKind,
)


class TemporalDecisionStatus(str, Enum):
    ABSTAINED = "ABSTAINED"
    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    UNCHANGED = "UNCHANGED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class DBDTemporalSignal(str, Enum):
    GENERATOR_REMAINING = "GENERATOR_REMAINING"
    CHASE_STATE = "CHASE_STATE"
    SURVIVOR_STATE = "SURVIVOR_STATE"
    HOOK_COUNT = "HOOK_COUNT"


class ChasePhase(str, Enum):
    NOT_CHASE = "NOT_CHASE"
    CHASE_CANDIDATE = "CHASE_CANDIDATE"
    CHASE_ACTIVE = "CHASE_ACTIVE"
    CHASE_END_CANDIDATE = "CHASE_END_CANDIDATE"


@dataclass(frozen=True, slots=True)
class SurvivorSubject:
    match_id: str
    survivor_slot: int

    def __post_init__(self) -> None:
        if not isinstance(self.match_id, str) or not self.match_id.strip() or len(self.match_id) > 256:
            raise ValueError("match_id must be bounded non-empty text")
        if isinstance(self.survivor_slot, bool) or not isinstance(self.survivor_slot, int) or not 0 <= self.survivor_slot <= 3:
            raise ValueError("survivor_slot must be 0..3")


@dataclass(frozen=True, slots=True)
class DBDTemporalProfile:
    profile_id: str
    profile_version: int
    minimum_confidence_milli: int = 700
    history_window_frames: int = 5
    generator_minimum_frames: int = 3
    survivor_state_minimum_frames: int = 2
    hook_count_minimum_frames: int = 2
    chase_start_frames: int = 2
    chase_end_frames: int = 3

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not self.profile_id.strip() or len(self.profile_id) > 128:
            raise ValueError("profile_id must be bounded non-empty text")
        if isinstance(self.profile_version, bool) or not isinstance(self.profile_version, int) or self.profile_version < 1:
            raise ValueError("profile_version must be positive")
        if isinstance(self.minimum_confidence_milli, bool) or not isinstance(self.minimum_confidence_milli, int) or not 0 <= self.minimum_confidence_milli <= 1000:
            raise ValueError("minimum_confidence_milli must be 0..1000")
        counts = (
            self.history_window_frames,
            self.generator_minimum_frames,
            self.survivor_state_minimum_frames,
            self.hook_count_minimum_frames,
            self.chase_start_frames,
            self.chase_end_frames,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in counts):
            raise ValueError("temporal frame thresholds must be positive integers")
        if any(value > self.history_window_frames for value in counts[1:3]):
            raise ValueError("vote thresholds must not exceed history_window_frames")


@dataclass(frozen=True, slots=True)
class TemporalDecision:
    status: TemporalDecisionStatus
    signal: DBDTemporalSignal
    match_id: str
    survivor_slot: int | None
    frame_index: int
    observed_value: str
    stable_value_before: str
    stable_value_after: str
    confidence_milli: int
    evidence_refs: tuple[str, ...]
    reason_codes: tuple[str, ...]


@dataclass(slots=True)
class _Candidate:
    value: str
    count: int
    confidence_total: int
    evidence_refs: list[str]


@dataclass(slots=True)
class _ChaseState:
    phase: ChasePhase = ChasePhase.NOT_CHASE
    streak: int = 0
    confidence_total: int = 0
    evidence_refs: list[str] | None = None

    def __post_init__(self) -> None:
        if self.evidence_refs is None:
            self.evidence_refs = []


class DBDTemporalStateMachines:
    """In-memory deterministic state machines scoped to one analysis stream."""

    _VALID_SURVIVOR_TRANSITIONS = {
        "HEALTHY": {"INJURED", "DOWNED", "HOOKED", "DEAD", "ESCAPED"},
        "INJURED": {"HEALTHY", "DOWNED", "HOOKED", "DEAD", "ESCAPED"},
        "DOWNED": {"INJURED", "HOOKED", "DEAD"},
        "HOOKED": {"INJURED", "DEAD"},
        "DEAD": set(),
        "ESCAPED": set(),
    }

    def __init__(self, profile: DBDTemporalProfile) -> None:
        if not isinstance(profile, DBDTemporalProfile):
            raise ValueError("profile must be a DBDTemporalProfile")
        self.profile = profile
        self._last_frames: dict[tuple[str, int | None, DBDTemporalSignal], int] = {}
        self._generator_values: dict[str, int] = {}
        self._generator_history: dict[str, Deque[tuple[int, int, str]]] = {}
        self._survivor_states: dict[SurvivorSubject, str] = {}
        self._hook_counts: dict[SurvivorSubject, int] = {}
        self._candidates: dict[tuple[SurvivorSubject, DBDTemporalSignal], _Candidate] = {}
        self._chases: dict[SurvivorSubject, _ChaseState] = {}

    @staticmethod
    def _validate_common(match_id: str, frame_index: int, confidence_milli: int, evidence_ref: str) -> None:
        if not isinstance(match_id, str) or not match_id.strip() or len(match_id) > 256:
            raise ValueError("match_id must be bounded non-empty text")
        if isinstance(frame_index, bool) or not isinstance(frame_index, int) or frame_index < 0:
            raise ValueError("frame_index must be non-negative")
        if isinstance(confidence_milli, bool) or not isinstance(confidence_milli, int) or not 0 <= confidence_milli <= 1000:
            raise ValueError("confidence_milli must be 0..1000")
        if not isinstance(evidence_ref, str) or not evidence_ref.strip() or len(evidence_ref) > 512:
            raise ValueError("evidence_ref must be bounded non-empty text")

    def _ordered(self, key: tuple[str, int | None, DBDTemporalSignal], frame_index: int) -> bool:
        previous = self._last_frames.get(key)
        if previous is not None and frame_index <= previous:
            return False
        self._last_frames[key] = frame_index
        return True

    @staticmethod
    def _decision(
        status: TemporalDecisionStatus,
        signal: DBDTemporalSignal,
        match_id: str,
        survivor_slot: int | None,
        frame_index: int,
        observed: str,
        before: str,
        after: str,
        confidence_milli: int,
        evidence_refs: tuple[str, ...],
        *reasons: str,
    ) -> TemporalDecision:
        return TemporalDecision(
            status=status,
            signal=signal,
            match_id=match_id,
            survivor_slot=survivor_slot,
            frame_index=frame_index,
            observed_value=observed,
            stable_value_before=before,
            stable_value_after=after,
            confidence_milli=confidence_milli,
            evidence_refs=tuple(sorted(set(evidence_refs))),
            reason_codes=tuple(sorted(set(reasons))),
        )

    def consume_generator_remaining(
        self,
        *,
        match_id: str,
        frame_index: int,
        remaining: int | None,
        confidence_milli: int,
        evidence_ref: str,
    ) -> TemporalDecision:
        self._validate_common(match_id, frame_index, confidence_milli, evidence_ref)
        signal = DBDTemporalSignal.GENERATOR_REMAINING
        key = (match_id, None, signal)
        before = str(self._generator_values.get(match_id, "UNKNOWN"))
        observed = "UNKNOWN" if remaining is None else str(remaining)
        if not self._ordered(key, frame_index):
            return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, signal, match_id, None, frame_index, observed, before, before, confidence_milli, (evidence_ref,), "OUT_OF_ORDER_FRAME")
        history = self._generator_history.setdefault(match_id, deque(maxlen=self.profile.history_window_frames))
        if remaining is not None and (isinstance(remaining, bool) or not isinstance(remaining, int) or not 0 <= remaining <= 5):
            history.clear()
            return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, signal, match_id, None, frame_index, observed, before, before, confidence_milli, (evidence_ref,), "INVALID_GENERATOR_REMAINING")
        if remaining is None or confidence_milli < self.profile.minimum_confidence_milli:
            history.clear()
            reason = "UNKNOWN_OBSERVATION" if remaining is None else "CONFIDENCE_BELOW_PROFILE_THRESHOLD"
            return self._decision(TemporalDecisionStatus.ABSTAINED, signal, match_id, None, frame_index, observed, before, before, confidence_milli, (evidence_ref,), reason)
        current = self._generator_values.get(match_id)
        if current is not None and remaining > current:
            history.clear()
            return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, signal, match_id, None, frame_index, observed, before, before, confidence_milli, (evidence_ref,), "GENERATOR_REMAINING_INCREASE")
        if current == remaining:
            history.clear()
            return self._decision(TemporalDecisionStatus.UNCHANGED, signal, match_id, None, frame_index, observed, before, before, confidence_milli, (evidence_ref,), "STABLE_VALUE_REOBSERVED")
        history.append((remaining, confidence_milli, evidence_ref))
        counts = Counter(value for value, _, _ in history)
        top_count = max(counts.values())
        winners = [value for value, count in counts.items() if count == top_count]
        if len(winners) != 1 or winners[0] != remaining or top_count < self.profile.generator_minimum_frames:
            return self._decision(TemporalDecisionStatus.CANDIDATE, signal, match_id, None, frame_index, observed, before, before, confidence_milli, (evidence_ref,), "TEMPORAL_MAJORITY_PENDING")
        winner = winners[0]
        winner_rows = [(confidence, ref) for value, confidence, ref in history if value == winner]
        effective = sum(confidence for confidence, _ in winner_rows) // len(winner_rows)
        refs = tuple(ref for _, ref in winner_rows)
        self._generator_values[match_id] = winner
        history.clear()
        return self._decision(TemporalDecisionStatus.CONFIRMED, signal, match_id, None, frame_index, observed, before, str(winner), effective, refs, "TEMPORAL_MAJORITY_CONFIRMED")

    def consume_survivor(self, observation: DbDObservationEnvelope) -> TemporalDecision:
        if not isinstance(observation, DbDObservationEnvelope):
            raise ValueError("observation must be a DbDObservationEnvelope")
        if observation.signal_kind is None:
            raise ValueError("observation must carry a Survivor signal")
        if observation.survivor_slot is None:
            raise ValueError("temporal reconciliation requires a known survivor_slot")
        subject = SurvivorSubject(observation.match_id or "", observation.survivor_slot)
        signal = DBDTemporalSignal(observation.signal_kind.value)
        frame = observation.source_frame
        if frame is None:
            raise ValueError("survivor observation requires source_frame")
        evidence_ref = observation.evidence_ref or observation.observation_id
        self._validate_common(subject.match_id, frame, observation.confidence_milli, evidence_ref)
        key = (subject.match_id, subject.survivor_slot, signal)
        before = self._stable_survivor_value(subject, signal)
        observed = observation.state or "UNKNOWN"
        if not self._ordered(key, frame):
            return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, signal, subject.match_id, subject.survivor_slot, frame, observed, before, before, observation.confidence_milli, (evidence_ref,), "OUT_OF_ORDER_FRAME")
        if observed == "UNKNOWN" or observation.confidence_milli < self.profile.minimum_confidence_milli:
            self._clear_incomplete(subject, signal)
            reason = "UNKNOWN_OBSERVATION" if observed == "UNKNOWN" else "CONFIDENCE_BELOW_PROFILE_THRESHOLD"
            return self._decision(TemporalDecisionStatus.ABSTAINED, signal, subject.match_id, subject.survivor_slot, frame, observed, before, self._stable_survivor_value(subject, signal), observation.confidence_milli, (evidence_ref,), reason)
        if signal is DBDTemporalSignal.CHASE_STATE:
            return self._consume_chase(subject, frame, observed, observation.confidence_milli, evidence_ref)
        if signal is DBDTemporalSignal.SURVIVOR_STATE:
            return self._consume_survivor_state(subject, frame, observed, observation.confidence_milli, evidence_ref)
        return self._consume_hook_count(subject, frame, observed, observation.confidence_milli, evidence_ref)

    def _stable_survivor_value(self, subject: SurvivorSubject, signal: DBDTemporalSignal) -> str:
        if signal is DBDTemporalSignal.CHASE_STATE:
            return self._chases.get(subject, _ChaseState()).phase.value
        if signal is DBDTemporalSignal.SURVIVOR_STATE:
            return self._survivor_states.get(subject, "UNKNOWN")
        return str(self._hook_counts.get(subject, "UNKNOWN"))

    def _clear_incomplete(self, subject: SurvivorSubject, signal: DBDTemporalSignal) -> None:
        self._candidates.pop((subject, signal), None)
        if signal is DBDTemporalSignal.CHASE_STATE:
            chase = self._chases.setdefault(subject, _ChaseState())
            if chase.phase is ChasePhase.CHASE_CANDIDATE:
                chase.phase = ChasePhase.NOT_CHASE
            elif chase.phase is ChasePhase.CHASE_END_CANDIDATE:
                chase.phase = ChasePhase.CHASE_ACTIVE
            chase.streak = 0
            chase.confidence_total = 0
            chase.evidence_refs = []

    def _consume_chase(self, subject: SurvivorSubject, frame: int, observed: str, confidence: int, evidence_ref: str) -> TemporalDecision:
        signal = DBDTemporalSignal.CHASE_STATE
        chase = self._chases.setdefault(subject, _ChaseState())
        before = chase.phase.value
        if observed not in {phase.value for phase in ChasePhase}:
            return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, signal, subject.match_id, subject.survivor_slot, frame, observed, before, before, confidence, (evidence_ref,), "INVALID_CHASE_STATE")
        active_evidence = observed in {ChasePhase.CHASE_CANDIDATE.value, ChasePhase.CHASE_ACTIVE.value}
        if chase.phase in {ChasePhase.NOT_CHASE, ChasePhase.CHASE_CANDIDATE}:
            if not active_evidence:
                chase.phase, chase.streak, chase.confidence_total, chase.evidence_refs = ChasePhase.NOT_CHASE, 0, 0, []
                status = TemporalDecisionStatus.UNCHANGED if before == ChasePhase.NOT_CHASE.value else TemporalDecisionStatus.CANDIDATE
                return self._decision(status, signal, subject.match_id, subject.survivor_slot, frame, observed, before, chase.phase.value, confidence, (evidence_ref,), "CHASE_START_NOT_SUSTAINED")
            chase.streak = chase.streak + 1 if chase.phase is ChasePhase.CHASE_CANDIDATE else 1
            chase.confidence_total = chase.confidence_total + confidence if chase.phase is ChasePhase.CHASE_CANDIDATE else confidence
            chase.evidence_refs = [*chase.evidence_refs, evidence_ref] if chase.phase is ChasePhase.CHASE_CANDIDATE else [evidence_ref]
            chase.phase = ChasePhase.CHASE_CANDIDATE
            if chase.streak >= self.profile.chase_start_frames:
                effective = chase.confidence_total // chase.streak
                refs = tuple(chase.evidence_refs)
                chase.phase, chase.streak, chase.confidence_total, chase.evidence_refs = ChasePhase.CHASE_ACTIVE, 0, 0, []
                return self._decision(TemporalDecisionStatus.CONFIRMED, signal, subject.match_id, subject.survivor_slot, frame, observed, before, chase.phase.value, effective, refs, "CHASE_START_CONFIRMED")
            return self._decision(TemporalDecisionStatus.CANDIDATE, signal, subject.match_id, subject.survivor_slot, frame, observed, before, chase.phase.value, confidence, tuple(chase.evidence_refs), "CHASE_START_PENDING")
        if active_evidence:
            chase.phase, chase.streak, chase.confidence_total, chase.evidence_refs = ChasePhase.CHASE_ACTIVE, 0, 0, []
            status = TemporalDecisionStatus.UNCHANGED if before == ChasePhase.CHASE_ACTIVE.value else TemporalDecisionStatus.CANDIDATE
            return self._decision(status, signal, subject.match_id, subject.survivor_slot, frame, observed, before, chase.phase.value, confidence, (evidence_ref,), "CHASE_END_NOT_SUSTAINED")
        chase.streak = chase.streak + 1 if chase.phase is ChasePhase.CHASE_END_CANDIDATE else 1
        chase.confidence_total = chase.confidence_total + confidence if chase.phase is ChasePhase.CHASE_END_CANDIDATE else confidence
        chase.evidence_refs = [*chase.evidence_refs, evidence_ref] if chase.phase is ChasePhase.CHASE_END_CANDIDATE else [evidence_ref]
        chase.phase = ChasePhase.CHASE_END_CANDIDATE
        if chase.streak >= self.profile.chase_end_frames:
            effective = chase.confidence_total // chase.streak
            refs = tuple(chase.evidence_refs)
            chase.phase, chase.streak, chase.confidence_total, chase.evidence_refs = ChasePhase.NOT_CHASE, 0, 0, []
            return self._decision(TemporalDecisionStatus.CONFIRMED, signal, subject.match_id, subject.survivor_slot, frame, observed, before, chase.phase.value, effective, refs, "CHASE_END_CONFIRMED")
        return self._decision(TemporalDecisionStatus.CANDIDATE, signal, subject.match_id, subject.survivor_slot, frame, observed, before, chase.phase.value, confidence, tuple(chase.evidence_refs), "CHASE_END_PENDING")

    def _debounce(self, subject: SurvivorSubject, signal: DBDTemporalSignal, value: str, confidence: int, evidence_ref: str, minimum: int) -> tuple[bool, int, tuple[str, ...]]:
        key = (subject, signal)
        candidate = self._candidates.get(key)
        if candidate is None or candidate.value != value:
            candidate = _Candidate(value, 0, 0, [])
            self._candidates[key] = candidate
        candidate.count += 1
        candidate.confidence_total += confidence
        candidate.evidence_refs.append(evidence_ref)
        if candidate.count < minimum:
            return False, confidence, (evidence_ref,)
        self._candidates.pop(key, None)
        return True, candidate.confidence_total // candidate.count, tuple(candidate.evidence_refs)

    def _consume_survivor_state(self, subject: SurvivorSubject, frame: int, observed: str, confidence: int, evidence_ref: str) -> TemporalDecision:
        signal = DBDTemporalSignal.SURVIVOR_STATE
        before = self._survivor_states.get(subject, "UNKNOWN")
        if observed not in self._VALID_SURVIVOR_TRANSITIONS:
            self._candidates.pop((subject, signal), None)
            return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, signal, subject.match_id, subject.survivor_slot, frame, observed, before, before, confidence, (evidence_ref,), "INVALID_SURVIVOR_STATE")
        if observed == before:
            self._candidates.pop((subject, signal), None)
            return self._decision(TemporalDecisionStatus.UNCHANGED, signal, subject.match_id, subject.survivor_slot, frame, observed, before, before, confidence, (evidence_ref,), "STABLE_VALUE_REOBSERVED")
        if before != "UNKNOWN" and observed not in self._VALID_SURVIVOR_TRANSITIONS[before]:
            self._candidates.pop((subject, signal), None)
            return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, signal, subject.match_id, subject.survivor_slot, frame, observed, before, before, confidence, (evidence_ref,), "INVALID_SURVIVOR_STATE_TRANSITION")
        ready, effective, refs = self._debounce(subject, signal, observed, confidence, evidence_ref, self.profile.survivor_state_minimum_frames)
        if not ready:
            return self._decision(TemporalDecisionStatus.CANDIDATE, signal, subject.match_id, subject.survivor_slot, frame, observed, before, before, confidence, refs, "SURVIVOR_STATE_PENDING")
        self._survivor_states[subject] = observed
        reasons = ["SURVIVOR_STATE_CONFIRMED"]
        if observed == "HOOKED" and before != "HOOKED":
            current = self._hook_counts.get(subject)
            if current is None:
                reasons.append("HOOK_COUNT_REMAINS_UNKNOWN")
            else:
                self._hook_counts[subject] = min(2, current + 1)
                reasons.append("HOOK_COUNT_ADVANCED_FROM_STATE")
        return self._decision(TemporalDecisionStatus.CONFIRMED, signal, subject.match_id, subject.survivor_slot, frame, observed, before, observed, effective, refs, *reasons)

    def _consume_hook_count(self, subject: SurvivorSubject, frame: int, observed: str, confidence: int, evidence_ref: str) -> TemporalDecision:
        signal = DBDTemporalSignal.HOOK_COUNT
        before_count = self._hook_counts.get(subject)
        before = str(before_count) if before_count is not None else "UNKNOWN"
        try:
            value = int(observed)
        except (TypeError, ValueError):
            value = -1
        if observed not in {"0", "1", "2"} or value < 0:
            self._candidates.pop((subject, signal), None)
            return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, signal, subject.match_id, subject.survivor_slot, frame, observed, before, before, confidence, (evidence_ref,), "INVALID_HOOK_COUNT")
        if before_count == value:
            self._candidates.pop((subject, signal), None)
            return self._decision(TemporalDecisionStatus.UNCHANGED, signal, subject.match_id, subject.survivor_slot, frame, observed, before, before, confidence, (evidence_ref,), "STABLE_VALUE_REOBSERVED")
        if before_count is not None and value < before_count:
            self._candidates.pop((subject, signal), None)
            return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, signal, subject.match_id, subject.survivor_slot, frame, observed, before, before, confidence, (evidence_ref,), "HOOK_COUNT_DECREASE")
        if before_count is not None and value > before_count + 1:
            self._candidates.pop((subject, signal), None)
            return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, signal, subject.match_id, subject.survivor_slot, frame, observed, before, before, confidence, (evidence_ref,), "HOOK_COUNT_JUMP")
        ready, effective, refs = self._debounce(subject, signal, observed, confidence, evidence_ref, self.profile.hook_count_minimum_frames)
        if not ready:
            return self._decision(TemporalDecisionStatus.CANDIDATE, signal, subject.match_id, subject.survivor_slot, frame, observed, before, before, confidence, refs, "HOOK_COUNT_PENDING")
        self._hook_counts[subject] = value
        return self._decision(TemporalDecisionStatus.CONFIRMED, signal, subject.match_id, subject.survivor_slot, frame, observed, before, observed, effective, refs, "HOOK_COUNT_CONFIRMED")

    def generator_remaining(self, match_id: str) -> int | None:
        return self._generator_values.get(match_id)

    def survivor_state(self, subject: SurvivorSubject) -> str:
        return self._survivor_states.get(subject, "UNKNOWN")

    def hook_count(self, subject: SurvivorSubject) -> int | None:
        return self._hook_counts.get(subject)

    def chase_phase(self, subject: SurvivorSubject) -> ChasePhase:
        return self._chases.get(subject, _ChaseState()).phase


__all__ = [
    "ChasePhase",
    "DBDTemporalProfile",
    "DBDTemporalSignal",
    "DBDTemporalStateMachines",
    "SurvivorSubject",
    "TemporalDecision",
    "TemporalDecisionStatus",
]
