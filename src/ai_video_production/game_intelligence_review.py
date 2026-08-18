"""TASK-049 R6A Human Review backend/read model.

This module provides an application boundary for reviewing CGEL events without
owning or modifying the shared BVP V6 shell.  All changes are append-only Event
revisions plus GameEventReview records in the existing GameIntelligenceStore.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from .canonical_game_event import (
    CanonicalGameEvent,
    EventConfirmationState,
    EventReviewStatus,
    GameEventReview,
    GameEventType,
    GameReviewAction,
)
from .errors import ProductError, ProductErrorCategory
from .game_event_evidence import GameEvidence
from .game_event_store import GameIntelligenceStore
from .ids import IdKind, validate_id
from .serialization import utc_now_iso


@dataclass(frozen=True, slots=True)
class GameReviewQueueItem:
    event: CanonicalGameEvent
    evidence: tuple[GameEvidence, ...]
    reviews: tuple[GameEventReview, ...]

    @property
    def unresolved(self) -> bool:
        return (
            self.event.review_status is EventReviewStatus.PENDING
            or self.event.confirmation_state
            in {EventConfirmationState.UNKNOWN, EventConfirmationState.NEEDS_REVIEW, EventConfirmationState.POSSIBLE, EventConfirmationState.DETECTED}
        )


class GameIntelligenceReviewService:
    """Append-only Human review service for Game Intelligence events."""

    def __init__(self, store: GameIntelligenceStore) -> None:
        if not isinstance(store, GameIntelligenceStore):
            raise TypeError("store must be a GameIntelligenceStore")
        self.store = store

    def list_queue(self, match_id: str, *, pending_only: bool = False) -> tuple[GameReviewQueueItem, ...]:
        validate_id(match_id, IdKind.GAME_MATCH)
        items: list[GameReviewQueueItem] = []
        for event in self.store.list_events(match_id, latest_only=True):
            evidence = tuple(self.store.get_evidence(ref) for ref in event.evidence_refs)
            reviews = self.store.list_reviews(event.event_id)
            item = GameReviewQueueItem(event, evidence, reviews)
            if not pending_only or item.unresolved:
                items.append(item)
        return tuple(items)

    def approve_confirmed(self, event_id: str, *, reason_code: str = "HUMAN_APPROVED", notes: str = "") -> CanonicalGameEvent:
        original = self._latest(event_id)
        if original.confirmation_state is not EventConfirmationState.CONFIRMED:
            raise ProductError(
                "ERR_GAME_REVIEW_APPROVE_REQUIRES_CONFIRMED",
                "APPROVE is only valid for an already CONFIRMED Event; uncertain candidates must be explicitly confirmed/corrected",
                ProductErrorCategory.STATE,
            )
        if original.review_status is EventReviewStatus.HUMAN_APPROVED:
            raise ProductError("ERR_GAME_REVIEW_REDUNDANT", "Event is already Human-approved", ProductErrorCategory.STATE)
        revised = replace(
            original,
            revision=original.revision + 1,
            review_status=EventReviewStatus.HUMAN_APPROVED,
            created_at=utc_now_iso(),
        )
        review = self._review(
            original,
            revised,
            action=GameReviewAction.APPROVE,
            reason_code=reason_code,
            notes=notes,
        )
        self.store.append_event_and_review(revised, review)
        return revised

    def confirm_candidate(self, event_id: str, *, reason_code: str = "HUMAN_CONFIRM", notes: str = "") -> CanonicalGameEvent:
        original = self._latest(event_id)
        if original.event_type is GameEventType.UNKNOWN_EVENT:
            raise ProductError(
                "ERR_GAME_REVIEW_UNKNOWN_TYPE",
                "UNKNOWN_EVENT must be corrected to a concrete type before Human confirmation",
                ProductErrorCategory.STATE,
            )
        if original.confirmation_state is EventConfirmationState.CONFIRMED:
            return self.approve_confirmed(event_id, reason_code=reason_code, notes=notes)
        if original.confirmation_state is EventConfirmationState.REJECTED:
            raise ProductError("ERR_GAME_REVIEW_REJECTED", "Rejected Event must be corrected before confirmation", ProductErrorCategory.STATE)
        revised = replace(
            original,
            revision=original.revision + 1,
            confirmation_state=EventConfirmationState.CONFIRMED,
            review_status=EventReviewStatus.HUMAN_CORRECTED,
            created_at=utc_now_iso(),
        )
        review = self._review(
            original,
            revised,
            action=GameReviewAction.CORRECT,
            reason_code=reason_code,
            notes=notes,
        )
        self.store.append_event_and_review(revised, review)
        return revised

    def correct(
        self,
        event_id: str,
        *,
        corrected_event_type: GameEventType,
        corrected_confirmation_state: EventConfirmationState,
        reason_code: str = "HUMAN_CORRECT",
        notes: str = "",
    ) -> CanonicalGameEvent:
        if not isinstance(corrected_event_type, GameEventType):
            raise ValueError("corrected_event_type must be a GameEventType")
        if not isinstance(corrected_confirmation_state, EventConfirmationState):
            raise ValueError("corrected_confirmation_state must be an EventConfirmationState")
        original = self._latest(event_id)
        if (
            corrected_event_type is original.event_type
            and corrected_confirmation_state is original.confirmation_state
        ):
            raise ProductError("ERR_GAME_REVIEW_NO_CHANGE", "CORRECT requires an actual Event type/state change", ProductErrorCategory.VALIDATION)
        revised = replace(
            original,
            revision=original.revision + 1,
            event_type=corrected_event_type,
            confirmation_state=corrected_confirmation_state,
            review_status=EventReviewStatus.HUMAN_CORRECTED,
            created_at=utc_now_iso(),
        )
        review = self._review(
            original,
            revised,
            action=GameReviewAction.CORRECT,
            reason_code=reason_code,
            notes=notes,
        )
        self.store.append_event_and_review(revised, review)
        return revised

    def reject(self, event_id: str, *, reason_code: str = "HUMAN_REJECT", notes: str = "") -> CanonicalGameEvent:
        original = self._latest(event_id)
        if original.confirmation_state is EventConfirmationState.REJECTED and original.review_status is EventReviewStatus.HUMAN_REJECTED:
            raise ProductError("ERR_GAME_REVIEW_REDUNDANT", "Event is already Human-rejected", ProductErrorCategory.STATE)
        revised = replace(
            original,
            revision=original.revision + 1,
            confirmation_state=EventConfirmationState.REJECTED,
            review_status=EventReviewStatus.HUMAN_REJECTED,
            created_at=utc_now_iso(),
        )
        review = self._review(
            original,
            revised,
            action=GameReviewAction.REJECT,
            reason_code=reason_code,
            notes=notes,
        )
        self.store.append_event_and_review(revised, review)
        return revised

    def mark_unknown(self, event_id: str, *, reason_code: str = "HUMAN_UNKNOWN", notes: str = "") -> CanonicalGameEvent:
        original = self._latest(event_id)
        if original.confirmation_state is EventConfirmationState.UNKNOWN and original.event_type is GameEventType.UNKNOWN_EVENT:
            raise ProductError("ERR_GAME_REVIEW_REDUNDANT", "Event is already UNKNOWN", ProductErrorCategory.STATE)
        revised = replace(
            original,
            revision=original.revision + 1,
            event_type=GameEventType.UNKNOWN_EVENT,
            confirmation_state=EventConfirmationState.UNKNOWN,
            review_status=EventReviewStatus.HUMAN_CORRECTED,
            created_at=utc_now_iso(),
        )
        review = self._review(
            original,
            revised,
            action=GameReviewAction.MARK_UNKNOWN,
            reason_code=reason_code,
            notes=notes,
        )
        self.store.append_event_and_review(revised, review)
        return revised

    def _latest(self, event_id: str) -> CanonicalGameEvent:
        validate_id(event_id, IdKind.GAME_EVENT)
        return self.store.get_event(event_id)

    @staticmethod
    def _review(
        original: CanonicalGameEvent,
        revised: CanonicalGameEvent,
        *,
        action: GameReviewAction,
        reason_code: str,
        notes: str,
    ) -> GameEventReview:
        return GameEventReview(
            event_id=revised.event_id,
            event_revision=revised.revision,
            action=action,
            reviewer_kind="HUMAN",
            original_confirmation_state=original.confirmation_state,
            corrected_confirmation_state=revised.confirmation_state,
            original_event_type=original.event_type,
            corrected_event_type=revised.event_type,
            reason_code=reason_code,
            notes=notes,
        )


__all__ = ["GameIntelligenceReviewService", "GameReviewQueueItem"]
