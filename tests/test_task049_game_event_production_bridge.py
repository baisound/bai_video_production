from __future__ import annotations

from dataclasses import replace

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
from ai_video_production.game_commentary import (
    CommentaryCandidate,
    CommentaryClaim,
    CommentaryClaimKind,
    CommentaryDraft,
    CommentaryFactValidator,
    CommentaryPlanner,
)
from ai_video_production.game_event_evidence import GameEvidence, GameEvidenceType, SourceFrameRange
from ai_video_production.game_event_production_bridge import (
    GameEventToProductionBridge,
    GameProductionProposalKind,
)
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.timebase import FrameRate


def fixture() -> tuple[GameMatch, CanonicalGameEvent, CommentaryCandidate]:
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
    evidence = GameEvidence(
        production_job_id=match.production_job_id,
        match_id=match.match_id,
        source_asset_id=match.source_asset_id,
        producer="task049.bridge-fixture",
        producer_version="1.0.0",
        evidence_type=GameEvidenceType.VISION,
        source_range=SourceFrameRange(900, 960),
        confidence_milli=960,
    )
    event = CanonicalGameEvent(
        match_id=match.match_id,
        revision=1,
        event_type=GameEventType.WINDOW_VAULT,
        source_range=evidence.source_range,
        game_version=match.game_version,
        environment=match.environment,
        perspective=match.perspective,
        state={"fixture": True},
        confidence_milli=940,
        confirmation_state=EventConfirmationState.CONFIRMED,
        evidence_refs=(evidence.game_evidence_id,),
        review_status=EventReviewStatus.HUMAN_APPROVED,
    )
    plan = CommentaryPlanner().plan(event, language="ja-JP")
    fact = next(item for item in plan.facts if item.kind is CommentaryClaimKind.EVENT_OCCURRED)
    draft = CommentaryDraft(
        "ここで窓越えが起きました。",
        (CommentaryClaim(fact.kind, fact.key, fact.value),),
    )
    validation = CommentaryFactValidator().validate(plan, draft)
    assert validation.passed
    return match, event, CommentaryCandidate(plan, draft, validation)


def test_bridge_compiles_side_effect_free_highlight_narration_and_subtitle_proposals() -> None:
    match, event, commentary = fixture()
    bundle = GameEventToProductionBridge.compile(match=match, event=event, commentary=commentary)

    assert tuple(item.kind for item in bundle.items) == (
        GameProductionProposalKind.HIGHLIGHT,
        GameProductionProposalKind.NARRATION,
        GameProductionProposalKind.SUBTITLE,
    )
    assert bundle.items[0].text is None
    assert bundle.items[1].text == commentary.draft.text
    assert bundle.items[2].text == commentary.draft.text
    assert all(item.source_range == event.source_range for item in bundle.items)

    payload = bundle.to_dict()
    assert payload["authority_state"] == "PROPOSAL_ONLY"
    assert payload["requires_human_adoption"] is True
    assert payload["production_timeline_mutated"] is False
    assert payload["resolve_write_performed"] is False
    assert payload["external_write_authorized"] is False
    assert payload["source_rate"] == {"numerator": 30000, "denominator": 1001}
    body = dict(payload)
    digest = body.pop("bridge_bundle_sha256")
    assert digest == sha256_bytes(canonical_json_bytes(body))


def test_bridge_preserves_exact_event_commentary_evidence_and_hash_lineage() -> None:
    match, event, commentary = fixture()
    bundle = GameEventToProductionBridge.compile(match=match, event=event, commentary=commentary)
    assert bundle.match_id == match.match_id
    assert bundle.event_id == event.event_id
    assert bundle.event_revision == event.revision
    assert bundle.source_asset_id == match.source_asset_id
    assert bundle.event_sha256 == event.to_dict()["event_sha256"]
    assert bundle.commentary_candidate_id == commentary.candidate_id
    assert bundle.commentary_candidate_sha256 == commentary.to_dict()["commentary_candidate_sha256"]
    assert bundle.evidence_refs == tuple(sorted(event.evidence_refs))
    assert bundle.knowledge_ref_sha256s == ()


def test_bridge_rejects_unconfirmed_or_unreviewed_event() -> None:
    match, event, commentary = fixture()
    with pytest.raises(ValueError, match="CONFIRMED"):
        GameEventToProductionBridge.compile(
            match=match,
            event=replace(event, confirmation_state=EventConfirmationState.NEEDS_REVIEW),
            commentary=commentary,
        )
    with pytest.raises(ValueError, match="review status"):
        GameEventToProductionBridge.compile(
            match=match,
            event=replace(event, review_status=EventReviewStatus.PENDING),
            commentary=commentary,
        )


def test_bridge_rejects_rejected_commentary_candidate() -> None:
    match, event, commentary = fixture()
    bad_draft = CommentaryDraft("99秒です。", ())
    bad_validation = CommentaryFactValidator().validate(commentary.plan, bad_draft)
    rejected = CommentaryCandidate(commentary.plan, bad_draft, bad_validation)
    with pytest.raises(ValueError, match="VALIDATED"):
        GameEventToProductionBridge.compile(match=match, event=event, commentary=rejected)


def test_bridge_rejects_event_or_match_lineage_mismatch() -> None:
    match, event, commentary = fixture()
    other = replace(match, match_id=generate_id(IdKind.GAME_MATCH))
    with pytest.raises(ValueError, match="match lineage mismatch"):
        GameEventToProductionBridge.compile(match=other, event=event, commentary=commentary)

    newer_event = replace(event, revision=2)
    with pytest.raises(ValueError, match="event/commentary lineage mismatch"):
        GameEventToProductionBridge.compile(match=match, event=newer_event, commentary=commentary)


def test_bridge_rejects_commentary_evidence_lineage_drift() -> None:
    match, event, commentary = fixture()
    drifted_plan = replace(
        commentary.plan,
        evidence_refs=(generate_id(IdKind.GAME_EVIDENCE),),
    )
    drifted = CommentaryCandidate(drifted_plan, commentary.draft, commentary.validation)
    with pytest.raises(ValueError, match="Evidence lineage"):
        GameEventToProductionBridge.compile(match=match, event=event, commentary=drifted)


def test_highlight_item_cannot_smuggle_text() -> None:
    from ai_video_production.game_event_production_bridge import GameProductionProposalItem

    with pytest.raises(ValueError, match="must not carry"):
        GameProductionProposalItem(
            GameProductionProposalKind.HIGHLIGHT,
            SourceFrameRange(1, 2),
            "hidden mutation intent",
        )
