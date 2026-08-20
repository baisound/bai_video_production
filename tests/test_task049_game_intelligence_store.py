from __future__ import annotations

from dataclasses import replace
from importlib import resources
import json
from pathlib import Path
import sqlite3

import pytest

from ai_video_production.canonical_game_event import (
    CanonicalGameEvent,
    EventConfirmationState,
    EventReviewStatus,
    GameEnvironment,
    GameEventReview,
    GameEventType,
    GameMatch,
    GameMatchStatus,
    GamePerspective,
    GameReviewAction,
)
from ai_video_production.errors import ProductError
from ai_video_production.game_event_evidence import GameEvidence, GameEvidenceType, SourceFrameRange
from ai_video_production.game_event_store import GameIntelligenceStore
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.timebase import FrameRate


ROOT = Path(__file__).resolve().parents[1]


def make_match() -> GameMatch:
    return GameMatch(
        production_job_id=generate_id(IdKind.JOB),
        source_asset_id=generate_id(IdKind.ASSET),
        game_profile_id="dead_by_daylight",
        game_profile_version="1.0.0",
        game_version="9.1.0",
        environment=GameEnvironment.LIVE,
        perspective=GamePerspective.SURVIVOR,
        source_rate=FrameRate(60000, 2002),
        status=GameMatchStatus.ANALYZING,
    )


def make_evidence(game_match: GameMatch, *, start: int = 100, end: int = 130) -> GameEvidence:
    return GameEvidence(
        production_job_id=game_match.production_job_id,
        match_id=game_match.match_id,
        source_asset_id=game_match.source_asset_id,
        producer="task049.synthetic-fixture",
        producer_version="1.0.0",
        evidence_type=GameEvidenceType.VISION,
        source_range=SourceFrameRange(start, end),
        confidence_milli=900,
    )


def make_event(game_match: GameMatch, ev: GameEvidence, *, event_id: str | None = None, revision: int = 1, start: int = 100) -> CanonicalGameEvent:
    kwargs = {}
    if event_id is not None:
        kwargs["event_id"] = event_id
    return CanonicalGameEvent(
        match_id=game_match.match_id,
        revision=revision,
        event_type=GameEventType.WINDOW_VAULT,
        source_range=SourceFrameRange(start, start + 30),
        game_version=game_match.game_version,
        environment=game_match.environment,
        perspective=game_match.perspective,
        state={"generator_remaining": 3},
        confidence_milli=880,
        confirmation_state=EventConfirmationState.CONFIRMED,
        evidence_refs=(ev.game_evidence_id,),
        review_status=EventReviewStatus.AUTO_ACCEPTED,
        **kwargs,
    )


def approve(event: CanonicalGameEvent, *, review_id: str | None = None) -> GameEventReview:
    kwargs = {}
    if review_id is not None:
        kwargs["review_id"] = review_id
    return GameEventReview(
        event_id=event.event_id,
        event_revision=event.revision,
        action=GameReviewAction.APPROVE,
        reviewer_kind="HUMAN",
        original_confirmation_state=event.confirmation_state,
        corrected_confirmation_state=event.confirmation_state,
        original_event_type=event.event_type,
        corrected_event_type=event.event_type,
        reason_code="HUMAN_OK",
        **kwargs,
    )


def populated_store(tmp_path: Path) -> tuple[GameIntelligenceStore, GameMatch, GameEvidence, CanonicalGameEvent]:
    store = GameIntelligenceStore(tmp_path / "game-intelligence.sqlite3")
    game_match = make_match()
    store.put_match(game_match)
    ev = make_evidence(game_match)
    store.append_evidence(ev)
    game_event = make_event(game_match, ev)
    store.append_event(game_event)
    return store, game_match, ev, game_event


def test_store_initializes_versioned_schema_and_roundtrips_match(tmp_path: Path) -> None:
    store = GameIntelligenceStore(tmp_path / "game-intelligence.sqlite3")
    game_match = make_match()
    store.put_match(game_match)
    assert store.schema_version == "1.0.0"
    assert store.get_match(game_match.match_id).to_dict() == game_match.to_dict()
    with sqlite3.connect(store.path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        meta = dict(conn.execute("SELECT key, value FROM store_metadata"))
    assert meta["store_format"] == "task049.game-intelligence.sqlite"


def test_match_revisions_are_append_only_exactly_sequential_and_idempotent(tmp_path: Path) -> None:
    store = GameIntelligenceStore(tmp_path / "db.sqlite3")
    first = make_match()
    store.put_match(first)
    store.put_match(first)
    second = replace(first, analysis_revision=2, status=GameMatchStatus.NEEDS_REVIEW)
    store.put_match(second)
    assert store.get_match(first.match_id).analysis_revision == 2
    assert store.get_match(first.match_id, analysis_revision=1).status is GameMatchStatus.ANALYZING
    with pytest.raises(ProductError, match="advance exactly once"):
        store.put_match(replace(first, analysis_revision=4))
    with pytest.raises(ProductError, match="identity/source/timebase"):
        store.put_match(replace(second, analysis_revision=3, source_asset_id=generate_id(IdKind.ASSET)))


def test_evidence_requires_existing_matching_match_source_and_is_idempotent(tmp_path: Path) -> None:
    store = GameIntelligenceStore(tmp_path / "db.sqlite3")
    game_match = make_match()
    ev = make_evidence(game_match)
    with pytest.raises(ProductError, match="Match was not found"):
        store.append_evidence(ev)
    store.put_match(game_match)
    store.append_evidence(ev)
    store.append_evidence(ev)
    assert store.get_evidence(ev.game_evidence_id).to_dict() == ev.to_dict()
    with pytest.raises(ProductError, match="job/source Asset"):
        store.append_evidence(replace(ev, game_evidence_id=generate_id(IdKind.GAME_EVIDENCE), source_asset_id=generate_id(IdKind.ASSET)))


def test_event_requires_admitted_same_match_evidence_and_sequential_revisions(tmp_path: Path) -> None:
    store = GameIntelligenceStore(tmp_path / "db.sqlite3")
    game_match = make_match()
    store.put_match(game_match)
    ev = make_evidence(game_match)
    event = make_event(game_match, ev)
    with pytest.raises(ProductError, match="not present"):
        store.append_event(event)
    store.append_evidence(ev)
    store.append_event(event)
    store.append_event(event)
    revised = replace(event, revision=2, confidence_milli=920)
    store.append_event(revised)
    assert store.get_event(event.event_id).revision == 2
    assert [x.revision for x in store.list_events(game_match.match_id, latest_only=False)] == [1, 2]
    with pytest.raises(ProductError, match="advance exactly once"):
        store.append_event(replace(event, revision=4))


def test_event_rejects_cross_match_evidence(tmp_path: Path) -> None:
    store = GameIntelligenceStore(tmp_path / "db.sqlite3")
    a = make_match()
    b = replace(
        make_match(),
        production_job_id=a.production_job_id,
        source_asset_id=a.source_asset_id,
    )
    store.put_match(a)
    store.put_match(b)
    ev_b = make_evidence(b)
    store.append_evidence(ev_b)
    event_a = make_event(a, replace(ev_b, match_id=a.match_id))
    # The Event reference points at an existing Evidence ID whose stored Match is B.
    with pytest.raises(ProductError, match="another Match"):
        store.append_event(event_a)


def test_reviews_are_append_only_and_target_exact_event_revision(tmp_path: Path) -> None:
    store, game_match, ev, event = populated_store(tmp_path)
    review = approve(event)
    store.append_review(review)
    store.append_review(review)
    assert store.list_reviews(event.event_id)[0].to_dict() == review.to_dict()
    missing = replace(review, review_id=generate_id(IdKind.GAME_REVIEW), event_revision=2)
    with pytest.raises(ProductError, match="does not exist"):
        store.append_review(missing)


def test_atomic_event_review_bundle_rolls_back_on_review_conflict(tmp_path: Path) -> None:
    store, game_match, ev, first_event = populated_store(tmp_path)
    existing_review = approve(first_event)
    store.append_review(existing_review)

    second_event = make_event(game_match, ev, start=200)
    conflicting_review = approve(second_event, review_id=existing_review.review_id)
    with pytest.raises(ProductError, match="Review ID already exists"):
        store.append_event_and_review(second_event, conflicting_review)
    with pytest.raises(ProductError, match="was not found"):
        store.get_event(second_event.event_id)


def test_checkpoint_roundtrip_schema_and_resume_detects_state_change(tmp_path: Path) -> None:
    store, game_match, ev, event = populated_store(tmp_path)
    checkpoint = store.create_checkpoint(game_match.match_id, stage="EVENTS_RESOLVED", state={"cursor_frame": 130})
    assert store.latest_checkpoint(game_match.match_id).to_dict() == checkpoint.to_dict()
    validate_instance(checkpoint.to_dict(), ROOT / "schemas/game-intelligence-checkpoint.schema.json")
    store.assert_resume_compatible(checkpoint)

    later = make_evidence(game_match, start=300, end=330)
    store.append_evidence(later)
    with pytest.raises(ProductError, match="state changed"):
        store.assert_resume_compatible(checkpoint)


def test_checkpoint_schema_mirror_is_byte_identical(tmp_path: Path) -> None:
    public = (ROOT / "schemas/game-intelligence-checkpoint.schema.json").read_bytes()
    packaged = resources.files("ai_video_production").joinpath(
        "schema_resources", "game-intelligence-checkpoint.schema.json"
    ).read_bytes()
    assert public == packaged


def test_unknown_newer_store_version_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "future.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA user_version=99")
    with pytest.raises(ProductError) as caught:
        GameIntelligenceStore(path)
    assert caught.value.code == "ERR_GAME_STORE_VERSION_UNSUPPORTED"


def test_unversioned_foreign_sqlite_database_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "foreign.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE unrelated(x TEXT)")
    with pytest.raises(ProductError) as caught:
        GameIntelligenceStore(path)
    assert caught.value.code == "ERR_GAME_STORE_VERSION_UNKNOWN"


def test_corrupt_database_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.sqlite3"
    path.write_bytes(b"not a sqlite database")
    with pytest.raises(ProductError) as caught:
        GameIntelligenceStore(path)
    assert caught.value.code in {"ERR_GAME_STORE_OPEN", "ERR_GAME_STORE_CORRUPT"}


def test_corrupt_or_unknown_record_schema_fails_on_readback(tmp_path: Path) -> None:
    store = GameIntelligenceStore(tmp_path / "db.sqlite3")
    game_match = make_match()
    store.put_match(game_match)
    with sqlite3.connect(store.path) as conn:
        payload = game_match.to_dict()
        payload["schema_version"] = "2.0.0"
        conn.execute(
            "UPDATE match_revisions SET payload_json=? WHERE match_id=? AND analysis_revision=1",
            (json.dumps(payload), game_match.match_id),
        )
    with pytest.raises(ProductError) as caught:
        store.get_match(game_match.match_id)
    assert caught.value.code == "ERR_GAME_STORE_RECORD_INVALID"


def test_latest_event_listing_is_deterministic_by_source_range(tmp_path: Path) -> None:
    store = GameIntelligenceStore(tmp_path / "db.sqlite3")
    game_match = make_match()
    store.put_match(game_match)
    late_ev = make_evidence(game_match, start=200, end=230)
    early_ev = make_evidence(game_match, start=100, end=130)
    store.append_evidence(late_ev)
    store.append_evidence(early_ev)
    late = make_event(game_match, late_ev, start=200)
    early = make_event(game_match, early_ev, start=100)
    store.append_event(late)
    store.append_event(early)
    assert [item.event_id for item in store.list_events(game_match.match_id)] == [early.event_id, late.event_id]
