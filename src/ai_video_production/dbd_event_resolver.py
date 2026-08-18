"""TASK-049 R4 bounded Dead by Daylight event producer/resolver.

The R4 contract is intentionally deterministic and accuracy-neutral.  It turns
already-produced typed observations plus admitted CGEL Evidence into candidate
Canonical Game Events.  It does not perform computer vision, media I/O, LLM
calls, game-process access, or Production Timeline mutation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping

from .canonical_game_event import (
    CanonicalGameEvent,
    EventConfirmationState,
    EventReviewStatus,
    GameEventType,
    GameMatch,
)
from .dbd_profile import DBDSignalKind
from .errors import ProductError, ProductErrorCategory
from .game_event_evidence import GameEvidence, GameEvidenceType, SourceFrameRange
from .schema_contracts import SemVer
from .serialization import canonical_json_bytes


class DBDObservationOrigin(str, Enum):
    PROFILE_SIGNAL = "PROFILE_SIGNAL"
    VISUAL_MARKER = "VISUAL_MARKER"
    AUDIO_RULE = "AUDIO_RULE"
    ASR_INTERPRETATION = "ASR_INTERPRETATION"
    LLM_INFERENCE = "LLM_INFERENCE"


class DBDVisualMarkerKind(str, Enum):
    MATCH_START = "MATCH_START"
    WINDOW_VAULT = "WINDOW_VAULT"
    PALLET_DROP = "PALLET_DROP"


class DBDHealthState(str, Enum):
    HEALTHY = "HEALTHY"
    INJURED = "INJURED"
    DOWNED = "DOWNED"
    HOOKED = "HOOKED"
    DEAD = "DEAD"
    ESCAPED = "ESCAPED"


class DBDTriState(str, Enum):
    UNKNOWN = "UNKNOWN"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


def _validation(code: str, message: str, **details: Any) -> ProductError:
    return ProductError(code, message, ProductErrorCategory.VALIDATION, False, details=details)


def _require_milli(value: int, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1000:
        raise ValueError(f"{field_name} must be an integer in 0..1000")
    return value


def _json_object(value: Mapping[str, Any], *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
    result = dict(value)
    try:
        canonical_json_bytes(result)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be canonical-JSON serializable") from exc
    return result


def _ranges_overlap(left: SourceFrameRange, right: SourceFrameRange) -> bool:
    return (
        left.start_frame < right.end_frame_exclusive
        and right.start_frame < left.end_frame_exclusive
    )


@dataclass(frozen=True, slots=True)
class DBDEventCandidate:
    """Ephemeral, non-canonical event candidate produced from bounded signals."""

    match_id: str
    event_type: GameEventType
    source_range: SourceFrameRange
    evidence_refs: tuple[str, ...]
    confidence_milli: int
    origin: DBDObservationOrigin
    producer: str
    producer_version: str
    observation_state: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.match_id, str) or not self.match_id:
            raise ValueError("match_id must be non-empty")
        if not isinstance(self.event_type, GameEventType):
            raise ValueError("event_type must be a GameEventType")
        if not isinstance(self.source_range, SourceFrameRange):
            raise ValueError("source_range must be a SourceFrameRange")
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs:
            raise ValueError("evidence_refs must be a non-empty tuple")
        if any(not isinstance(ref, str) or not ref for ref in self.evidence_refs):
            raise ValueError("evidence_refs must contain non-empty identifiers")
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ValueError("evidence_refs must be unique")
        _require_milli(self.confidence_milli, field_name="confidence_milli")
        if not isinstance(self.origin, DBDObservationOrigin):
            raise ValueError("origin must be a DBDObservationOrigin")
        if not isinstance(self.producer, str) or not self.producer.strip() or len(self.producer) > 128:
            raise ValueError("producer must be a bounded non-empty string")
        SemVer.parse(self.producer_version)
        object.__setattr__(
            self,
            "observation_state",
            _json_object(self.observation_state, field_name="observation_state"),
        )


@dataclass(frozen=True, slots=True)
class DBDResolutionPolicy:
    auto_confirm_milli: int = 900
    needs_review_milli: int = 600

    def __post_init__(self) -> None:
        _require_milli(self.auto_confirm_milli, field_name="auto_confirm_milli")
        _require_milli(self.needs_review_milli, field_name="needs_review_milli")
        if self.needs_review_milli >= self.auto_confirm_milli:
            raise ValueError("needs_review_milli must be lower than auto_confirm_milli")


@dataclass(frozen=True, slots=True)
class DBDResolverState:
    match_started: DBDTriState = DBDTriState.UNKNOWN
    chase_active: DBDTriState = DBDTriState.UNKNOWN
    survivor_hooked: DBDTriState = DBDTriState.UNKNOWN

    def __post_init__(self) -> None:
        for name in ("match_started", "chase_active", "survivor_hooked"):
            if not isinstance(getattr(self, name), DBDTriState):
                raise ValueError(f"{name} must be a DBDTriState")

    def to_dict(self) -> dict[str, str]:
        return {
            "match_started": self.match_started.value,
            "chase_active": self.chase_active.value,
            "survivor_hooked": self.survivor_hooked.value,
        }


@dataclass(frozen=True, slots=True)
class DBDResolutionResult:
    event: CanonicalGameEvent
    state_after: DBDResolverState
    reason_codes: tuple[str, ...]


class BoundedDBDEventProducer:
    """Compile explicit bounded signals into non-canonical event candidates.

    This producer performs no detection.  Its inputs are already-observed signal
    transitions/markers supplied by a detector, synthetic fixture, or another
    admitted upstream component.
    """

    def __init__(self, *, producer: str = "task049.bounded-dbd-producer", producer_version: str = "1.0.0") -> None:
        if not isinstance(producer, str) or not producer.strip():
            raise ValueError("producer must be non-empty")
        SemVer.parse(producer_version)
        self.producer = producer
        self.producer_version = producer_version

    def from_profile_signal_transition(
        self,
        *,
        match_id: str,
        signal_kind: DBDSignalKind,
        before: bool | DBDHealthState,
        after: bool | DBDHealthState,
        source_range: SourceFrameRange,
        evidence_refs: tuple[str, ...],
        confidence_milli: int,
    ) -> DBDEventCandidate | None:
        if not isinstance(signal_kind, DBDSignalKind):
            raise ValueError("signal_kind must be a DBDSignalKind")

        event_type: GameEventType | None = None
        observation_state: dict[str, Any] = {
            "signal_kind": signal_kind.value,
            "before": before.value if isinstance(before, Enum) else before,
            "after": after.value if isinstance(after, Enum) else after,
        }

        if signal_kind is DBDSignalKind.CHASE_INTENSITY:
            if not isinstance(before, bool) or not isinstance(after, bool):
                raise ValueError("CHASE_INTENSITY transition values must be bool")
            if before is False and after is True:
                event_type = GameEventType.CHASE_START
            elif before is True and after is False:
                event_type = GameEventType.CHASE_END
        elif signal_kind is DBDSignalKind.EVENT_HOOK:
            if not isinstance(before, bool) or not isinstance(after, bool):
                raise ValueError("EVENT_HOOK transition values must be bool")
            if before is False and after is True:
                event_type = GameEventType.HOOK
        elif signal_kind is DBDSignalKind.EVENT_RESCUE:
            if not isinstance(before, bool) or not isinstance(after, bool):
                raise ValueError("EVENT_RESCUE transition values must be bool")
            if before is False and after is True:
                event_type = GameEventType.UNHOOK
        elif signal_kind is DBDSignalKind.HUD_SURVIVOR_HEALTH:
            if not isinstance(before, DBDHealthState) or not isinstance(after, DBDHealthState):
                raise ValueError("HUD_SURVIVOR_HEALTH transition values must be DBDHealthState")
            if before is DBDHealthState.HEALTHY and after is DBDHealthState.INJURED:
                event_type = GameEventType.INJURY
            elif after is DBDHealthState.DOWNED and before in {DBDHealthState.HEALTHY, DBDHealthState.INJURED}:
                event_type = GameEventType.DOWN
            elif after is DBDHealthState.HOOKED and before is not DBDHealthState.HOOKED:
                event_type = GameEventType.HOOK
            elif before is DBDHealthState.HOOKED and after in {DBDHealthState.HEALTHY, DBDHealthState.INJURED}:
                event_type = GameEventType.UNHOOK
            elif after is DBDHealthState.DEAD and before is not DBDHealthState.DEAD:
                event_type = GameEventType.KILL
            elif after is DBDHealthState.ESCAPED and before is not DBDHealthState.ESCAPED:
                event_type = GameEventType.ESCAPE
        else:
            raise _validation(
                "ERR_DBD_SIGNAL_NOT_EVENT_PRODUCER",
                "The TASK-009 signal kind is not admitted as an R4 event producer",
                signal_kind=signal_kind.value,
            )

        if event_type is None:
            return None
        return DBDEventCandidate(
            match_id=match_id,
            event_type=event_type,
            source_range=source_range,
            evidence_refs=evidence_refs,
            confidence_milli=confidence_milli,
            origin=DBDObservationOrigin.PROFILE_SIGNAL,
            producer=self.producer,
            producer_version=self.producer_version,
            observation_state=observation_state,
        )

    def from_visual_marker(
        self,
        *,
        match_id: str,
        marker: DBDVisualMarkerKind,
        source_range: SourceFrameRange,
        evidence_refs: tuple[str, ...],
        confidence_milli: int,
    ) -> DBDEventCandidate:
        if not isinstance(marker, DBDVisualMarkerKind):
            raise ValueError("marker must be a DBDVisualMarkerKind")
        event_type = GameEventType(marker.value)
        return DBDEventCandidate(
            match_id=match_id,
            event_type=event_type,
            source_range=source_range,
            evidence_refs=evidence_refs,
            confidence_milli=confidence_milli,
            origin=DBDObservationOrigin.VISUAL_MARKER,
            producer=self.producer,
            producer_version=self.producer_version,
            observation_state={"visual_marker": marker.value},
        )


class DBDEventResolver:
    _AUTO_CONFIRM_ORIGINS = {
        DBDObservationOrigin.PROFILE_SIGNAL,
        DBDObservationOrigin.VISUAL_MARKER,
        DBDObservationOrigin.AUDIO_RULE,
    }
    _DIRECT_EVIDENCE_TYPES = {
        GameEvidenceType.VISION,
        GameEvidenceType.HUD,
        GameEvidenceType.AUDIO,
        GameEvidenceType.STATE_TRANSITION,
        GameEvidenceType.HUMAN_REVIEW,
    }

    def __init__(self, policy: DBDResolutionPolicy | None = None) -> None:
        self.policy = policy or DBDResolutionPolicy()

    def resolve_candidates(
        self,
        match: GameMatch,
        candidates: Iterable[DBDEventCandidate],
        evidence_by_id: Mapping[str, GameEvidence],
        *,
        initial_state: DBDResolverState | None = None,
    ) -> tuple[DBDResolutionResult, ...]:
        if not isinstance(match, GameMatch):
            raise ValueError("match must be a GameMatch")
        state = initial_state or DBDResolverState()
        ordered = sorted(
            tuple(candidates),
            key=lambda item: (
                item.source_range.start_frame,
                item.source_range.end_frame_exclusive,
                item.event_type.value,
                item.producer,
            ),
        )
        results: list[DBDResolutionResult] = []
        for candidate in ordered:
            result = self.resolve_candidate(match, candidate, evidence_by_id, state=state)
            results.append(result)
            state = result.state_after
        return tuple(results)

    def resolve_candidate(
        self,
        match: GameMatch,
        candidate: DBDEventCandidate,
        evidence_by_id: Mapping[str, GameEvidence],
        *,
        state: DBDResolverState | None = None,
    ) -> DBDResolutionResult:
        if not isinstance(match, GameMatch):
            raise ValueError("match must be a GameMatch")
        if not isinstance(candidate, DBDEventCandidate):
            raise ValueError("candidate must be a DBDEventCandidate")
        if candidate.match_id != match.match_id:
            raise _validation(
                "ERR_DBD_CANDIDATE_MATCH_MISMATCH",
                "DbD event candidate belongs to another Match",
            )
        if not isinstance(evidence_by_id, Mapping):
            raise ValueError("evidence_by_id must be a mapping")

        admitted: list[GameEvidence] = []
        for ref in candidate.evidence_refs:
            evidence = evidence_by_id.get(ref)
            if evidence is None:
                raise _validation(
                    "ERR_DBD_EVENT_EVIDENCE_MISSING",
                    "DbD event candidate references missing Evidence",
                    game_evidence_id=ref,
                )
            if not isinstance(evidence, GameEvidence):
                raise ValueError("evidence_by_id values must be GameEvidence")
            if evidence.match_id != match.match_id:
                raise _validation(
                    "ERR_DBD_EVENT_EVIDENCE_MATCH_MISMATCH",
                    "DbD event candidate references Evidence from another Match",
                    game_evidence_id=ref,
                )
            if evidence.production_job_id != match.production_job_id or evidence.source_asset_id != match.source_asset_id:
                raise _validation(
                    "ERR_DBD_EVENT_EVIDENCE_LINEAGE_MISMATCH",
                    "DbD event Evidence does not match the admitted Match source lineage",
                    game_evidence_id=ref,
                )
            admitted.append(evidence)

        if not any(_ranges_overlap(candidate.source_range, item.source_range) for item in admitted):
            raise _validation(
                "ERR_DBD_EVENT_EVIDENCE_TIME_MISMATCH",
                "DbD event candidate has no temporally overlapping admitted Evidence",
            )

        effective_confidence = min(
            candidate.confidence_milli,
            sum(item.confidence_milli for item in admitted) // len(admitted),
        )
        direct_evidence = any(item.evidence_type in self._DIRECT_EVIDENCE_TYPES for item in admitted)
        current_state = state or DBDResolverState()
        transition_valid, transition_reason, next_state = self._evaluate_transition(current_state, candidate.event_type)

        reasons: list[str] = []
        if not transition_valid:
            reasons.append(transition_reason)
        if candidate.origin not in self._AUTO_CONFIRM_ORIGINS:
            reasons.append("ORIGIN_REQUIRES_REVIEW")
        if not direct_evidence:
            reasons.append("DIRECT_EVIDENCE_REQUIRED")

        can_auto_confirm = (
            transition_valid
            and candidate.origin in self._AUTO_CONFIRM_ORIGINS
            and direct_evidence
            and effective_confidence >= self.policy.auto_confirm_milli
        )

        if can_auto_confirm:
            event_type = candidate.event_type
            confirmation = EventConfirmationState.CONFIRMED
            review_status = EventReviewStatus.AUTO_ACCEPTED
            state_after = next_state
            reasons.append("AUTO_CONFIRM_POLICY_PASS")
        elif effective_confidence < self.policy.needs_review_milli:
            event_type = GameEventType.UNKNOWN_EVENT
            confirmation = EventConfirmationState.UNKNOWN
            review_status = EventReviewStatus.PENDING
            state_after = current_state
            reasons.append("CONFIDENCE_BELOW_REVIEW_THRESHOLD")
        else:
            event_type = candidate.event_type
            confirmation = EventConfirmationState.NEEDS_REVIEW
            review_status = EventReviewStatus.PENDING
            state_after = current_state
            if effective_confidence < self.policy.auto_confirm_milli:
                reasons.append("CONFIDENCE_BELOW_AUTO_CONFIRM_THRESHOLD")
            if not transition_valid:
                reasons.append("STATE_NOT_ADVANCED")

        event_state: dict[str, Any] = {
            "candidate_event_type": candidate.event_type.value,
            "observation_origin": candidate.origin.value,
            "producer": candidate.producer,
            "producer_version": candidate.producer_version,
            "resolver_reason_codes": sorted(set(reasons)),
            "resolver_state_before": current_state.to_dict(),
            "resolver_state_after": state_after.to_dict(),
            "observation": dict(candidate.observation_state),
        }
        event = CanonicalGameEvent(
            match_id=match.match_id,
            revision=1,
            event_type=event_type,
            source_range=candidate.source_range,
            game_version=match.game_version,
            environment=match.environment,
            perspective=match.perspective,
            state=event_state,
            confidence_milli=effective_confidence,
            confirmation_state=confirmation,
            evidence_refs=candidate.evidence_refs,
            review_status=review_status,
        )
        return DBDResolutionResult(event, state_after, tuple(sorted(set(reasons))))

    @staticmethod
    def _evaluate_transition(
        state: DBDResolverState,
        event_type: GameEventType,
    ) -> tuple[bool, str, DBDResolverState]:
        if event_type is GameEventType.MATCH_START:
            if state.match_started is DBDTriState.ACTIVE:
                return False, "DUPLICATE_MATCH_START", state
            return True, "MATCH_START_APPLIED", DBDResolverState(
                match_started=DBDTriState.ACTIVE,
                chase_active=state.chase_active,
                survivor_hooked=state.survivor_hooked,
            )
        if event_type is GameEventType.CHASE_START:
            if state.chase_active is DBDTriState.ACTIVE:
                return False, "CHASE_ALREADY_ACTIVE", state
            return True, "CHASE_START_APPLIED", DBDResolverState(
                match_started=state.match_started,
                chase_active=DBDTriState.ACTIVE,
                survivor_hooked=state.survivor_hooked,
            )
        if event_type is GameEventType.CHASE_END:
            if state.chase_active is DBDTriState.INACTIVE:
                return False, "CHASE_ALREADY_INACTIVE", state
            return True, "CHASE_END_APPLIED", DBDResolverState(
                match_started=state.match_started,
                chase_active=DBDTriState.INACTIVE,
                survivor_hooked=state.survivor_hooked,
            )
        if event_type is GameEventType.HOOK:
            if state.survivor_hooked is DBDTriState.ACTIVE:
                return False, "SURVIVOR_ALREADY_HOOKED", state
            return True, "HOOK_APPLIED", DBDResolverState(
                match_started=state.match_started,
                chase_active=state.chase_active,
                survivor_hooked=DBDTriState.ACTIVE,
            )
        if event_type is GameEventType.UNHOOK:
            if state.survivor_hooked is DBDTriState.INACTIVE:
                return False, "SURVIVOR_ALREADY_UNHOOKED", state
            return True, "UNHOOK_APPLIED", DBDResolverState(
                match_started=state.match_started,
                chase_active=state.chase_active,
                survivor_hooked=DBDTriState.INACTIVE,
            )
        if event_type in {
            GameEventType.INJURY,
            GameEventType.WINDOW_VAULT,
            GameEventType.PALLET_DROP,
            GameEventType.UNKNOWN_EVENT,
        }:
            return True, "NO_STATE_TRANSITION", state
        return False, "UNSUPPORTED_EVENT_TRANSITION", state


__all__ = [
    "BoundedDBDEventProducer",
    "DBDEventCandidate",
    "DBDEventResolver",
    "DBDHealthState",
    "DBDObservationOrigin",
    "DBDResolutionPolicy",
    "DBDResolutionResult",
    "DBDResolverState",
    "DBDTriState",
    "DBDVisualMarkerKind",
]
