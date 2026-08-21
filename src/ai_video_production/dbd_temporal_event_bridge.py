"""TASK-052 R3B bridge from confirmed temporal decisions to CGEL candidates."""
from __future__ import annotations

from .canonical_game_event import GameEventType
from .dbd_event_resolver import DBDEventCandidate, DBDObservationOrigin
from .dbd_temporal_state import (
    ChasePhase,
    DBDTemporalSignal,
    TemporalDecision,
    TemporalDecisionStatus,
)
from .game_event_evidence import SourceFrameRange
from .schema_contracts import SemVer


class TemporalDecisionEventProducer:
    """Map only confirmed, traceable temporal transitions to event candidates."""

    def __init__(
        self,
        *,
        producer: str = "task052.temporal-event-bridge",
        producer_version: str = "1.0.0",
    ) -> None:
        if not isinstance(producer, str) or not producer.strip() or len(producer) > 128:
            raise ValueError("producer must be bounded non-empty text")
        SemVer.parse(producer_version)
        self.producer = producer
        self.producer_version = producer_version

    def from_decision(
        self,
        decision: TemporalDecision,
        *,
        source_range: SourceFrameRange,
    ) -> DBDEventCandidate | None:
        if not isinstance(decision, TemporalDecision):
            raise ValueError("decision must be a TemporalDecision")
        if not isinstance(source_range, SourceFrameRange):
            raise ValueError("source_range must be a SourceFrameRange")
        if decision.status is not TemporalDecisionStatus.CONFIRMED:
            return None
        if not decision.evidence_refs:
            raise ValueError("confirmed temporal decision requires evidence_refs")
        if not source_range.start_frame <= decision.frame_index < source_range.end_frame_exclusive:
            raise ValueError("source_range must contain the decision frame")

        event_type = self._event_type(decision)
        if event_type is None:
            return None
        if event_type in {
            GameEventType.CHASE_START,
            GameEventType.CHASE_END,
            GameEventType.INJURY,
            GameEventType.DOWN,
            GameEventType.HOOK,
            GameEventType.UNHOOK,
            GameEventType.KILL,
            GameEventType.ESCAPE,
        } and decision.survivor_slot is None:
            raise ValueError("survivor event requires survivor_slot")

        return DBDEventCandidate(
            match_id=decision.match_id,
            event_type=event_type,
            source_range=source_range,
            evidence_refs=decision.evidence_refs,
            confidence_milli=decision.confidence_milli,
            origin=DBDObservationOrigin.PROFILE_SIGNAL,
            producer=self.producer,
            producer_version=self.producer_version,
            observation_state={
                "temporal_signal": decision.signal.value,
                "temporal_status": decision.status.value,
                "stable_value_before": decision.stable_value_before,
                "stable_value_after": decision.stable_value_after,
                "temporal_reason_codes": list(decision.reason_codes),
            },
            survivor_slot=decision.survivor_slot,
        )

    @staticmethod
    def _event_type(decision: TemporalDecision) -> GameEventType | None:
        before = decision.stable_value_before
        after = decision.stable_value_after
        if decision.signal is DBDTemporalSignal.GENERATOR_REMAINING:
            try:
                return GameEventType.GENERATOR_COMPLETE if int(after) < int(before) else None
            except ValueError:
                return None
        if decision.signal is DBDTemporalSignal.CHASE_STATE:
            if after == ChasePhase.CHASE_ACTIVE.value:
                return GameEventType.CHASE_START
            if after == ChasePhase.NOT_CHASE.value and before == ChasePhase.CHASE_END_CANDIDATE.value:
                return GameEventType.CHASE_END
            return None
        if decision.signal is not DBDTemporalSignal.SURVIVOR_STATE or before == "UNKNOWN":
            return None
        if before == "HEALTHY" and after == "INJURED":
            return GameEventType.INJURY
        if after == "DOWNED" and before in {"HEALTHY", "INJURED"}:
            return GameEventType.DOWN
        if after == "HOOKED" and before != "HOOKED":
            return GameEventType.HOOK
        if before == "HOOKED" and after in {"HEALTHY", "INJURED"}:
            return GameEventType.UNHOOK
        if after == "DEAD" and before != "DEAD":
            return GameEventType.KILL
        if after == "ESCAPED" and before != "ESCAPED":
            return GameEventType.ESCAPE
        return None


__all__ = ["TemporalDecisionEventProducer"]
