from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from importlib import resources
import json
from pathlib import Path

import pytest

from ai_video_production.canonical_game_event import (
    CanonicalGameEvent,
    EventConfirmationState,
    EventReviewStatus,
    GameEnvironment,
    GameEventReview,
    GameEventType,
    GameKnowledgeKind,
    GameKnowledgeRef,
    GameMatch,
    GameMatchStatus,
    GamePerspective,
    GameReviewAction,
)
from ai_video_production.canonical_game_event_timeline import CanonicalGameEventTimeline
from ai_video_production.game_event_evidence import (
    GameEvidence,
    GameEvidenceType,
    SourceFrameRange,
)
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.timebase import FrameRate


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_NAMES = (
    "game-match.schema.json",
    "game-evidence.schema.json",
    "game-knowledge-ref.schema.json",
    "canonical-game-event.schema.json",
    "game-event-review.schema.json",
    "canonical-game-event-timeline.schema.json",
)


def match() -> GameMatch:
    return GameMatch(
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


def evidence(game_match: GameMatch, *, start: int = 100, end: int = 130) -> GameEvidence:
    return GameEvidence(
        production_job_id=game_match.production_job_id,
        match_id=game_match.match_id,
        source_asset_id=game_match.source_asset_id,
        producer="task049.synthetic-fixture",
        producer_version="1.0.0",
        evidence_type=GameEvidenceType.VISION,
        source_range=SourceFrameRange(start, end),
        confidence_milli=910,
    )


def knowledge() -> GameKnowledgeRef:
    return GameKnowledgeRef(
        GameKnowledgeKind.PERK,
        "perk_lithe",
        "PERKREV-001",
        GameEnvironment.LIVE,
        "9.0.0",
        "source://bhvr/perks/lithe/9.0.0",
    )


def event(game_match: GameMatch, game_evidence: GameEvidence, *, start: int = 100, end: int = 130) -> CanonicalGameEvent:
    return CanonicalGameEvent(
        match_id=game_match.match_id,
        revision=1,
        event_type=GameEventType.WINDOW_VAULT,
        source_range=SourceFrameRange(start, end),
        game_version=game_match.game_version,
        environment=game_match.environment,
        perspective=game_match.perspective,
        state={"generator_remaining": 3},
        confidence_milli=870,
        confirmation_state=EventConfirmationState.CONFIRMED,
        evidence_refs=(game_evidence.game_evidence_id,),
        knowledge_refs=(knowledge(),),
        review_status=EventReviewStatus.AUTO_ACCEPTED,
    )


def test_task049_id_kinds_use_normal_product_identifier_rules() -> None:
    for kind in (
        IdKind.GAME_MATCH,
        IdKind.GAME_EVENT,
        IdKind.GAME_EVIDENCE,
        IdKind.GAME_REVIEW,
    ):
        value = generate_id(kind)
        assert value.startswith(kind.value + "-")
        assert len(value.rsplit("-", 1)[1]) == 26


def test_source_frame_range_is_exact_end_exclusive_and_uses_task022_rate() -> None:
    source = SourceFrameRange(0, 300)
    rate = FrameRate(30000, 1001)
    assert source.duration_frames == 300
    assert rate.to_rational() == "30000/1001"
    assert source.to_microsecond_range(rate) == {
        "start": 0,
        "end_exclusive": 10_010_000,
    }
    with pytest.raises(ValueError, match="end-exclusive"):
        SourceFrameRange(100, 100)
    with pytest.raises(ValueError, match="integer"):
        SourceFrameRange(1.5, 2)  # type: ignore[arg-type]


def test_match_is_immutable_deterministic_and_schema_valid() -> None:
    item = match()
    payload = item.to_dict()
    assert payload == item.to_dict()
    assert payload["source_rate"] == {"numerator": 30000, "denominator": 1001}
    body = dict(payload)
    claimed = body.pop("match_sha256")
    assert claimed == sha256_bytes(canonical_json_bytes(body))
    validate_instance(payload, ROOT / "schemas/game-match.schema.json")
    with pytest.raises(FrozenInstanceError):
        item.analysis_revision = 2  # type: ignore[misc]


def test_game_evidence_is_bounded_typed_and_schema_valid() -> None:
    game_match = match()
    item = evidence(game_match)
    payload = item.to_dict()
    assert payload["confidence_milli"] == 910
    assert payload["artifact_ref"] is None
    validate_instance(payload, ROOT / "schemas/game-evidence.schema.json")
    with pytest.raises(ValueError, match="0..1000"):
        replace(item, confidence_milli=1001)
    with pytest.raises(ValueError, match="GameEvidenceType"):
        replace(item, evidence_type="VISION")  # type: ignore[arg-type]


def test_knowledge_ref_is_revisioned_provenance_not_mutable_fact_body() -> None:
    item = knowledge()
    payload = item.to_dict()
    assert set(payload) == {
        "schema_version",
        "knowledge_kind",
        "entity_id",
        "revision_id",
        "environment",
        "game_version_from",
        "game_version_to",
        "source_provenance_ref",
        "knowledge_ref_sha256",
    }
    assert "official_effect" not in payload
    validate_instance(payload, ROOT / "schemas/game-knowledge-ref.schema.json")


def test_canonical_event_requires_evidence_and_rejects_plain_string_enums() -> None:
    game_match = match()
    ev = evidence(game_match)
    item = event(game_match, ev)
    validate_instance(item.to_dict(), ROOT / "schemas/canonical-game-event.schema.json")
    with pytest.raises(ValueError, match="at least one"):
        replace(item, evidence_refs=())
    with pytest.raises(ValueError, match="GameEventType"):
        replace(item, event_type="WINDOW_VAULT")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="EventConfirmationState"):
        replace(item, confirmation_state="CONFIRMED")  # type: ignore[arg-type]


def test_event_state_must_be_json_serializable() -> None:
    game_match = match()
    ev = evidence(game_match)
    item = event(game_match, ev)
    with pytest.raises(ValueError, match="canonical-JSON serializable"):
        replace(item, state={"bad": object()})


def test_review_action_semantics_fail_closed() -> None:
    game_match = match()
    ev = evidence(game_match)
    item = event(game_match, ev)
    approved = GameEventReview(
        event_id=item.event_id,
        event_revision=item.revision,
        action=GameReviewAction.APPROVE,
        reviewer_kind="HUMAN",
        original_confirmation_state=item.confirmation_state,
        corrected_confirmation_state=item.confirmation_state,
        original_event_type=item.event_type,
        corrected_event_type=item.event_type,
        reason_code="HUMAN_OK",
    )
    validate_instance(approved.to_dict(), ROOT / "schemas/game-event-review.schema.json")
    with pytest.raises(ValueError, match="APPROVE cannot change"):
        replace(approved, corrected_event_type=GameEventType.PALLET_DROP)
    with pytest.raises(ValueError, match="REJECT must"):
        replace(
            approved,
            action=GameReviewAction.REJECT,
            corrected_confirmation_state=EventConfirmationState.CONFIRMED,
        )


def test_timeline_canonicalizes_order_and_rejects_cross_match_events() -> None:
    game_match = match()
    ev1 = evidence(game_match, start=200, end=220)
    ev2 = evidence(game_match, start=100, end=120)
    later = event(game_match, ev1, start=200, end=220)
    earlier = replace(
        event(game_match, ev2, start=100, end=120),
        event_type=GameEventType.CHASE_START,
        knowledge_refs=(),
    )
    timeline = CanonicalGameEventTimeline.create(game_match, (later, earlier))
    assert [x.event_id for x in timeline.events] == [earlier.event_id, later.event_id]
    validate_instance(
        timeline.to_dict(), ROOT / "schemas/canonical-game-event-timeline.schema.json"
    )

    other_match = replace(game_match, match_id=generate_id(IdKind.GAME_MATCH))
    wrong = replace(earlier, match_id=other_match.match_id)
    with pytest.raises(ValueError, match="match_id"):
        CanonicalGameEventTimeline.create(game_match, (wrong,))


def test_timeline_rejects_duplicate_event_revisions() -> None:
    game_match = match()
    ev = evidence(game_match)
    item = event(game_match, ev)
    with pytest.raises(ValueError, match="one revision"):
        CanonicalGameEventTimeline.create(game_match, (item, item))


def test_schema_mirrors_are_byte_identical_and_meta_valid() -> None:
    for name in SCHEMA_NAMES:
        public = (ROOT / "schemas" / name).read_bytes()
        packaged = resources.files("ai_video_production").joinpath(
            "schema_resources", name
        ).read_bytes()
        assert public == packaged
        schema = json.loads(public)
        # The helper checks both the schema meta-contract and a concrete
        # instance in the individual tests.
        from jsonschema import Draft202012Validator

        Draft202012Validator.check_schema(schema)


def test_json_schema_does_not_offer_decimal_fps_field() -> None:
    schema = json.loads((ROOT / "schemas/game-match.schema.json").read_text("utf-8"))
    source_rate = schema["properties"]["source_rate"]
    assert set(source_rate["properties"]) == {"numerator", "denominator"}
    assert "fps" not in source_rate["properties"]


def test_task009_contract_remains_separate_from_task049_core() -> None:
    source = (ROOT / "src/ai_video_production/dbd_profile.py").read_text("utf-8")
    assert "timeline_mutation_authorized\": False" in source
    assert "runtime_feature_producer_state\": \"NOT_SELECTED\"" in source
    assert "canonical_game_event" not in source
