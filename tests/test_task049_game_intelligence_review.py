from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.canonical_game_event import (
    CanonicalGameEvent,
    EventConfirmationState,
    EventReviewStatus,
    GameEnvironment,
    GameEventType,
    GameMatch,
    GameMatchStatus,
    GamePerspective,
)
from ai_video_production.errors import ProductError
from ai_video_production.game_event_evidence import GameEvidence, GameEvidenceType, SourceFrameRange
from ai_video_production.game_event_store import GameIntelligenceStore
from ai_video_production.game_intelligence_review import GameIntelligenceReviewService
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.timebase import FrameRate


def fixture_store(tmp_path: Path, *, state: EventConfirmationState = EventConfirmationState.NEEDS_REVIEW, event_type: GameEventType = GameEventType.WINDOW_VAULT, review_status: EventReviewStatus = EventReviewStatus.PENDING) -> tuple[GameIntelligenceStore, CanonicalGameEvent, GameEvidence]:
    store = GameIntelligenceStore(tmp_path / "game.sqlite3")
    match = GameMatch(
        production_job_id=generate_id(IdKind.JOB),
        source_asset_id=generate_id(IdKind.ASSET),
        game_profile_id="dead_by_daylight",
        game_profile_version="1.0.0",
        game_version="9.1.0",
        environment=GameEnvironment.LIVE,
        perspective=GamePerspective.SURVIVOR,
        source_rate=FrameRate(30000, 1001),
        status=GameMatchStatus.ANALYZING,
    )
    store.put_match(match)
    evidence = GameEvidence(
        production_job_id=match.production_job_id,
        match_id=match.match_id,
        source_asset_id=match.source_asset_id,
        producer="task049.review-fixture",
        producer_version="1.0.0",
        evidence_type=GameEvidenceType.VISION,
        source_range=SourceFrameRange(100, 110),
        confidence_milli=800,
    )
    store.append_evidence(evidence)
    event = CanonicalGameEvent(
        match_id=match.match_id,
        revision=1,
        event_type=event_type,
        source_range=evidence.source_range,
        game_version=match.game_version,
        environment=match.environment,
        perspective=match.perspective,
        state={"fixture": True},
        confidence_milli=800,
        confirmation_state=state,
        evidence_refs=(evidence.game_evidence_id,),
        review_status=review_status,
    )
    store.append_event(event)
    return store, event, evidence


def test_review_queue_is_read_only_projection_with_evidence_and_history(tmp_path: Path) -> None:
    store, event, evidence = fixture_store(tmp_path)
    service = GameIntelligenceReviewService(store)
    items = service.list_queue(event.match_id, pending_only=True)
    assert len(items) == 1
    assert items[0].event.event_id == event.event_id
    assert items[0].evidence == (evidence,)
    assert items[0].reviews == ()
    assert items[0].unresolved is True
    assert store.get_event(event.event_id).revision == 1


def test_confirm_candidate_creates_append_only_event_revision_and_review(tmp_path: Path) -> None:
    store, event, _ = fixture_store(tmp_path)
    service = GameIntelligenceReviewService(store)
    revised = service.confirm_candidate(event.event_id)
    assert revised.revision == 2
    assert revised.confirmation_state is EventConfirmationState.CONFIRMED
    assert revised.review_status is EventReviewStatus.HUMAN_CORRECTED
    assert store.get_event(event.event_id).revision == 2
    assert store.get_event(event.event_id, revision=1).confirmation_state is EventConfirmationState.NEEDS_REVIEW
    reviews = store.list_reviews(event.event_id)
    assert len(reviews) == 1
    assert reviews[0].event_revision == 2
    assert reviews[0].corrected_confirmation_state is EventConfirmationState.CONFIRMED


def test_approve_confirmed_does_not_rewrite_detection_state(tmp_path: Path) -> None:
    store, event, _ = fixture_store(
        tmp_path,
        state=EventConfirmationState.CONFIRMED,
        review_status=EventReviewStatus.AUTO_ACCEPTED,
    )
    revised = GameIntelligenceReviewService(store).approve_confirmed(event.event_id)
    assert revised.confirmation_state is EventConfirmationState.CONFIRMED
    assert revised.review_status is EventReviewStatus.HUMAN_APPROVED
    assert store.list_reviews(event.event_id)[0].action.value == "APPROVE"


def test_approve_uncertain_event_requires_explicit_confirmation(tmp_path: Path) -> None:
    store, event, _ = fixture_store(tmp_path)
    with pytest.raises(ProductError, match="already CONFIRMED"):
        GameIntelligenceReviewService(store).approve_confirmed(event.event_id)


def test_correct_changes_type_and_preserves_old_revision(tmp_path: Path) -> None:
    store, event, _ = fixture_store(tmp_path)
    revised = GameIntelligenceReviewService(store).correct(
        event.event_id,
        corrected_event_type=GameEventType.PALLET_DROP,
        corrected_confirmation_state=EventConfirmationState.CONFIRMED,
    )
    assert revised.event_type is GameEventType.PALLET_DROP
    assert revised.confirmation_state is EventConfirmationState.CONFIRMED
    assert store.get_event(event.event_id, revision=1).event_type is GameEventType.WINDOW_VAULT
    assert store.list_reviews(event.event_id)[0].corrected_event_type is GameEventType.PALLET_DROP


def test_reject_and_mark_unknown_are_explicit_append_only_actions(tmp_path: Path) -> None:
    store, event, _ = fixture_store(tmp_path)
    service = GameIntelligenceReviewService(store)
    rejected = service.reject(event.event_id)
    assert rejected.confirmation_state is EventConfirmationState.REJECTED
    assert rejected.review_status is EventReviewStatus.HUMAN_REJECTED
    unknown = service.mark_unknown(event.event_id)
    assert unknown.revision == 3
    assert unknown.event_type is GameEventType.UNKNOWN_EVENT
    assert unknown.confirmation_state is EventConfirmationState.UNKNOWN
    assert [r.action.value for r in store.list_reviews(event.event_id)] == ["REJECT", "MARK_UNKNOWN"]


def test_unknown_event_must_be_corrected_before_confirmation(tmp_path: Path) -> None:
    store, event, _ = fixture_store(tmp_path, event_type=GameEventType.UNKNOWN_EVENT, state=EventConfirmationState.UNKNOWN)
    service = GameIntelligenceReviewService(store)
    with pytest.raises(ProductError, match="corrected to a concrete type"):
        service.confirm_candidate(event.event_id)
    corrected = service.correct(
        event.event_id,
        corrected_event_type=GameEventType.HOOK,
        corrected_confirmation_state=EventConfirmationState.CONFIRMED,
    )
    assert corrected.event_type is GameEventType.HOOK


def test_pending_queue_excludes_human_resolved_event(tmp_path: Path) -> None:
    store, event, _ = fixture_store(tmp_path)
    service = GameIntelligenceReviewService(store)
    service.confirm_candidate(event.event_id)
    assert service.list_queue(event.match_id, pending_only=True) == ()
    assert len(service.list_queue(event.match_id)) == 1
