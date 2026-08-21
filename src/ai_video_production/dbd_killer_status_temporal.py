"""TASK-052 R3C1 killer-conditioned and status-effect temporal state."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re

from .dbd_temporal_state import TemporalDecisionStatus


_ID = re.compile(r"^[a-z][a-z0-9_]{1,127}$")


class EffectPolarity(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"


class EffectSourceKind(str, Enum):
    PERK = "PERK"
    KILLER_POWER = "KILLER_POWER"
    ITEM = "ITEM"
    ADDON = "ADDON"
    GAME_MECHANIC = "GAME_MECHANIC"
    UNKNOWN = "UNKNOWN"


class EffectTemporalDomain(str, Enum):
    KILLER_SPECIFIC_HUD = "KILLER_SPECIFIC_HUD"
    STATUS_EFFECT = "STATUS_EFFECT"


def _identifier(value: str, name: str) -> None:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"{name} must be a canonical lowercase identifier")


def _subject(match_id: str, survivor_slot: int | None) -> None:
    if not isinstance(match_id, str) or not match_id.strip() or len(match_id) > 256:
        raise ValueError("match_id must be bounded non-empty text")
    if survivor_slot is not None and (
        isinstance(survivor_slot, bool) or not isinstance(survivor_slot, int) or not 0 <= survivor_slot <= 3
    ):
        raise ValueError("survivor_slot must be 0..3 when known")


def _measurement(frame_index: int, confidence_milli: int, evidence_ref: str) -> None:
    if isinstance(frame_index, bool) or not isinstance(frame_index, int) or frame_index < 0:
        raise ValueError("frame_index must be non-negative")
    if isinstance(confidence_milli, bool) or not isinstance(confidence_milli, int) or not 0 <= confidence_milli <= 1000:
        raise ValueError("confidence_milli must be 0..1000")
    if not isinstance(evidence_ref, str) or not evidence_ref.strip() or len(evidence_ref) > 512:
        raise ValueError("evidence_ref must be bounded non-empty text")


@dataclass(frozen=True, slots=True)
class KillerEffectDefinition:
    killer_id: str
    effect_id: str
    survivor_scoped: bool
    max_stage: int | None = None
    stage_monotonic: bool = False
    progress_monotonic: bool = False

    def __post_init__(self) -> None:
        _identifier(self.killer_id, "killer_id")
        _identifier(self.effect_id, "effect_id")
        if not self.killer_id.startswith("killer_"):
            raise ValueError("killer_id must start with killer_")
        if not isinstance(self.survivor_scoped, bool):
            raise ValueError("survivor_scoped must be bool")
        if self.max_stage is not None and (
            isinstance(self.max_stage, bool) or not isinstance(self.max_stage, int) or self.max_stage < 1
        ):
            raise ValueError("max_stage must be positive when configured")


@dataclass(frozen=True, slots=True)
class StatusEffectDefinition:
    effect_id: str
    polarity: EffectPolarity
    source_kind: EffectSourceKind
    survivor_scoped: bool = True
    max_stack_or_level: int | None = None
    progress_monotonic: bool = False

    def __post_init__(self) -> None:
        _identifier(self.effect_id, "effect_id")
        if not isinstance(self.polarity, EffectPolarity) or not isinstance(self.source_kind, EffectSourceKind):
            raise ValueError("invalid status-effect enum")
        if self.source_kind is EffectSourceKind.UNKNOWN:
            raise ValueError("registered status effect source_kind cannot be UNKNOWN")
        if not isinstance(self.survivor_scoped, bool):
            raise ValueError("survivor_scoped must be bool")
        if self.max_stack_or_level is not None and (
            isinstance(self.max_stack_or_level, bool)
            or not isinstance(self.max_stack_or_level, int)
            or self.max_stack_or_level < 1
        ):
            raise ValueError("max_stack_or_level must be positive when configured")


@dataclass(frozen=True, slots=True)
class KillerStatusTemporalProfile:
    profile_id: str
    profile_version: int
    killer_effects: tuple[KillerEffectDefinition, ...]
    status_effects: tuple[StatusEffectDefinition, ...]
    minimum_confidence_milli: int = 700
    appearance_frames: int = 2
    disappearance_frames: int = 3
    value_frames: int = 2

    def __post_init__(self) -> None:
        _identifier(self.profile_id, "profile_id")
        if isinstance(self.profile_version, bool) or not isinstance(self.profile_version, int) or self.profile_version < 1:
            raise ValueError("profile_version must be positive")
        if isinstance(self.minimum_confidence_milli, bool) or not isinstance(self.minimum_confidence_milli, int) or not 0 <= self.minimum_confidence_milli <= 1000:
            raise ValueError("minimum_confidence_milli must be 0..1000")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in (self.appearance_frames, self.disappearance_frames, self.value_frames)):
            raise ValueError("temporal frame thresholds must be positive")
        killer_keys = tuple((item.killer_id, item.effect_id) for item in self.killer_effects)
        status_keys = tuple(item.effect_id for item in self.status_effects)
        if len(set(killer_keys)) != len(killer_keys) or len(set(status_keys)) != len(status_keys):
            raise ValueError("effect definitions must be unique")


@dataclass(frozen=True, slots=True)
class EffectTemporalState:
    active: bool | None = None
    stage: int | None = None
    progress_milli: int | None = None
    stack_or_level: int | None = None


@dataclass(frozen=True, slots=True)
class KillerSpecificObservation:
    match_id: str
    survivor_slot: int | None
    killer_id: str | None
    effect_id: str | None
    active: bool | None
    stage: int | None
    progress_milli: int | None
    confidence_milli: int
    frame_index: int
    evidence_ref: str

    def __post_init__(self) -> None:
        _subject(self.match_id, self.survivor_slot)
        _measurement(self.frame_index, self.confidence_milli, self.evidence_ref)
        if self.killer_id is not None:
            _identifier(self.killer_id, "killer_id")
        if self.effect_id is not None:
            _identifier(self.effect_id, "effect_id")
        if self.stage is not None and (isinstance(self.stage, bool) or not isinstance(self.stage, int) or self.stage < 0):
            raise ValueError("stage must be non-negative when known")
        if self.progress_milli is not None and (
            isinstance(self.progress_milli, bool) or not isinstance(self.progress_milli, int) or not 0 <= self.progress_milli <= 1000
        ):
            raise ValueError("progress_milli must be 0..1000 when known")


@dataclass(frozen=True, slots=True)
class StatusEffectObservation:
    match_id: str
    survivor_slot: int | None
    effect_id: str
    polarity: EffectPolarity
    source_kind: EffectSourceKind
    active: bool | None
    stack_or_level: int | None
    progress_milli: int | None
    confidence_milli: int
    frame_index: int
    evidence_ref: str

    def __post_init__(self) -> None:
        _subject(self.match_id, self.survivor_slot)
        _identifier(self.effect_id, "effect_id")
        _measurement(self.frame_index, self.confidence_milli, self.evidence_ref)
        if not isinstance(self.polarity, EffectPolarity) or not isinstance(self.source_kind, EffectSourceKind):
            raise ValueError("invalid status-effect enum")
        if self.stack_or_level is not None and (
            isinstance(self.stack_or_level, bool) or not isinstance(self.stack_or_level, int) or self.stack_or_level < 0
        ):
            raise ValueError("stack_or_level must be non-negative when known")
        if self.progress_milli is not None and (
            isinstance(self.progress_milli, bool) or not isinstance(self.progress_milli, int) or not 0 <= self.progress_milli <= 1000
        ):
            raise ValueError("progress_milli must be 0..1000 when known")


@dataclass(frozen=True, slots=True)
class EffectTemporalDecision:
    status: TemporalDecisionStatus
    domain: EffectTemporalDomain
    match_id: str
    survivor_slot: int | None
    effect_id: str
    frame_index: int
    state_before: EffectTemporalState
    state_after: EffectTemporalState
    confidence_milli: int
    evidence_refs: tuple[str, ...]
    reason_codes: tuple[str, ...]


@dataclass(slots=True)
class _Candidate:
    state: EffectTemporalState
    count: int
    confidence_total: int
    evidence_refs: list[str]


class KillerStatusTemporalStateMachines:
    def __init__(self, profile: KillerStatusTemporalProfile) -> None:
        if not isinstance(profile, KillerStatusTemporalProfile):
            raise ValueError("profile must be a KillerStatusTemporalProfile")
        self.profile = profile
        self._killer_defs = {(item.killer_id, item.effect_id): item for item in profile.killer_effects}
        self._status_defs = {item.effect_id: item for item in profile.status_effects}
        self._states: dict[tuple[EffectTemporalDomain, str, int | None, str], EffectTemporalState] = {}
        self._last_frames: dict[tuple[EffectTemporalDomain, str, int | None, str], int] = {}
        self._candidates: dict[tuple[EffectTemporalDomain, str, int | None, str], _Candidate] = {}

    def _decision(self, status, domain, match_id, slot, effect_id, frame, before, after, confidence, refs, *reasons):
        return EffectTemporalDecision(status, domain, match_id, slot, effect_id, frame, before, after, confidence, tuple(sorted(set(refs))), tuple(sorted(set(reasons))))

    def _consume(self, *, key, observed, confidence, frame, evidence_ref, monotonic_stage=False, monotonic_progress=False, max_stage=None, max_stack=None):
        domain, match_id, slot, effect_id = key
        before = self._states.get(key, EffectTemporalState())
        previous_frame = self._last_frames.get(key)
        if previous_frame is not None and frame <= previous_frame:
            self._candidates.pop(key, None)
            return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, domain, match_id, slot, effect_id, frame, before, before, confidence, (evidence_ref,), "OUT_OF_ORDER_FRAME")
        self._last_frames[key] = frame
        if confidence < self.profile.minimum_confidence_milli or observed.active is None:
            self._candidates.pop(key, None)
            reason = "CONFIDENCE_BELOW_PROFILE_THRESHOLD" if confidence < self.profile.minimum_confidence_milli else "UNKNOWN_OBSERVATION"
            return self._decision(TemporalDecisionStatus.ABSTAINED, domain, match_id, slot, effect_id, frame, before, before, confidence, (evidence_ref,), reason)
        if observed.active is False and any(value is not None for value in (observed.stage, observed.progress_milli, observed.stack_or_level)):
            self._candidates.pop(key, None)
            return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, domain, match_id, slot, effect_id, frame, before, before, confidence, (evidence_ref,), "INACTIVE_VALUE_CONTRADICTION")
        if max_stage is not None and observed.stage is not None and observed.stage > max_stage:
            self._candidates.pop(key, None)
            return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, domain, match_id, slot, effect_id, frame, before, before, confidence, (evidence_ref,), "STAGE_OUT_OF_RANGE")
        if max_stack is not None and observed.stack_or_level is not None and observed.stack_or_level > max_stack:
            self._candidates.pop(key, None)
            return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, domain, match_id, slot, effect_id, frame, before, before, confidence, (evidence_ref,), "STACK_OR_LEVEL_OUT_OF_RANGE")
        if before.active is True and observed.active is True:
            if monotonic_stage and before.stage is not None and observed.stage is not None and observed.stage < before.stage:
                self._candidates.pop(key, None)
                return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, domain, match_id, slot, effect_id, frame, before, before, confidence, (evidence_ref,), "STAGE_REGRESSION")
            if monotonic_progress and before.progress_milli is not None and observed.progress_milli is not None and observed.progress_milli < before.progress_milli:
                self._candidates.pop(key, None)
                return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, domain, match_id, slot, effect_id, frame, before, before, confidence, (evidence_ref,), "PROGRESS_REGRESSION")
        if observed == before:
            self._candidates.pop(key, None)
            return self._decision(TemporalDecisionStatus.UNCHANGED, domain, match_id, slot, effect_id, frame, before, before, confidence, (evidence_ref,), "STABLE_VALUE_REOBSERVED")
        minimum = self.profile.value_frames
        if observed.active is True and before.active is not True:
            minimum = self.profile.appearance_frames
        elif observed.active is False and before.active is not False:
            minimum = self.profile.disappearance_frames
        candidate = self._candidates.get(key)
        if candidate is None or candidate.state != observed:
            candidate = _Candidate(observed, 0, 0, [])
            self._candidates[key] = candidate
        candidate.count += 1
        candidate.confidence_total += confidence
        candidate.evidence_refs.append(evidence_ref)
        if candidate.count < minimum:
            return self._decision(TemporalDecisionStatus.CANDIDATE, domain, match_id, slot, effect_id, frame, before, before, confidence, tuple(candidate.evidence_refs), "TEMPORAL_CONFIRMATION_PENDING")
        self._candidates.pop(key, None)
        self._states[key] = observed
        reason = "EFFECT_APPEARED" if observed.active and before.active is not True else "EFFECT_DISAPPEARED" if observed.active is False and before.active is not False else "EFFECT_VALUE_CHANGED"
        return self._decision(TemporalDecisionStatus.CONFIRMED, domain, match_id, slot, effect_id, frame, before, observed, candidate.confidence_total // candidate.count, tuple(candidate.evidence_refs), reason)

    def consume_killer(self, observation: KillerSpecificObservation) -> EffectTemporalDecision:
        if not isinstance(observation, KillerSpecificObservation):
            raise ValueError("observation must be KillerSpecificObservation")
        domain = EffectTemporalDomain.KILLER_SPECIFIC_HUD
        before = EffectTemporalState()
        effect_id = observation.effect_id or "unknown_killer_effect"
        if observation.killer_id is None or observation.effect_id is None:
            return self._decision(TemporalDecisionStatus.ABSTAINED, domain, observation.match_id, observation.survivor_slot, effect_id, observation.frame_index, before, before, observation.confidence_milli, (observation.evidence_ref,), "UNKNOWN_KILLER")
        definition = self._killer_defs.get((observation.killer_id, observation.effect_id))
        if definition is None:
            known_elsewhere = any(effect_id == observation.effect_id for _, effect_id in self._killer_defs)
            status = TemporalDecisionStatus.NEEDS_REVIEW if known_elsewhere else TemporalDecisionStatus.ABSTAINED
            reason = "KILLER_EFFECT_NAMESPACE_MISMATCH" if known_elsewhere else "UNREGISTERED_KILLER_EFFECT"
            return self._decision(status, domain, observation.match_id, observation.survivor_slot, effect_id, observation.frame_index, before, before, observation.confidence_milli, (observation.evidence_ref,), reason)
        if definition.survivor_scoped != (observation.survivor_slot is not None):
            return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, domain, observation.match_id, observation.survivor_slot, effect_id, observation.frame_index, before, before, observation.confidence_milli, (observation.evidence_ref,), "EFFECT_SCOPE_MISMATCH")
        state = EffectTemporalState(observation.active, observation.stage, observation.progress_milli, None)
        key = (domain, observation.match_id, observation.survivor_slot, effect_id)
        return self._consume(key=key, observed=state, confidence=observation.confidence_milli, frame=observation.frame_index, evidence_ref=observation.evidence_ref, monotonic_stage=definition.stage_monotonic, monotonic_progress=definition.progress_monotonic, max_stage=definition.max_stage)

    def consume_status(self, observation: StatusEffectObservation) -> EffectTemporalDecision:
        if not isinstance(observation, StatusEffectObservation):
            raise ValueError("observation must be StatusEffectObservation")
        domain = EffectTemporalDomain.STATUS_EFFECT
        before = EffectTemporalState()
        definition = self._status_defs.get(observation.effect_id)
        if definition is None:
            return self._decision(TemporalDecisionStatus.ABSTAINED, domain, observation.match_id, observation.survivor_slot, observation.effect_id, observation.frame_index, before, before, observation.confidence_milli, (observation.evidence_ref,), "UNREGISTERED_STATUS_EFFECT")
        if definition.polarity is not observation.polarity or definition.source_kind is not observation.source_kind:
            return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, domain, observation.match_id, observation.survivor_slot, observation.effect_id, observation.frame_index, before, before, observation.confidence_milli, (observation.evidence_ref,), "STATUS_EFFECT_NAMESPACE_MISMATCH")
        if definition.survivor_scoped != (observation.survivor_slot is not None):
            return self._decision(TemporalDecisionStatus.NEEDS_REVIEW, domain, observation.match_id, observation.survivor_slot, observation.effect_id, observation.frame_index, before, before, observation.confidence_milli, (observation.evidence_ref,), "EFFECT_SCOPE_MISMATCH")
        state = EffectTemporalState(observation.active, None, observation.progress_milli, observation.stack_or_level)
        key = (domain, observation.match_id, observation.survivor_slot, observation.effect_id)
        return self._consume(key=key, observed=state, confidence=observation.confidence_milli, frame=observation.frame_index, evidence_ref=observation.evidence_ref, monotonic_progress=definition.progress_monotonic, max_stack=definition.max_stack_or_level)

    def state(self, domain: EffectTemporalDomain, match_id: str, survivor_slot: int | None, effect_id: str) -> EffectTemporalState:
        return self._states.get((domain, match_id, survivor_slot, effect_id), EffectTemporalState())


__all__ = [
    "EffectPolarity", "EffectSourceKind", "EffectTemporalDecision", "EffectTemporalDomain",
    "EffectTemporalState", "KillerEffectDefinition", "KillerSpecificObservation",
    "KillerStatusTemporalProfile", "KillerStatusTemporalStateMachines", "StatusEffectDefinition",
    "StatusEffectObservation",
]
