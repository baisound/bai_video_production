from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ai_video_production.canonical_game_event import (
    CanonicalGameEvent,
    EventConfirmationState,
    EventReviewStatus,
    GameEnvironment,
    GameEventType,
    GameKnowledgeKind,
    GameKnowledgeRef,
    GameMatch,
    GameMatchStatus,
    GamePerspective,
)
from ai_video_production.dbd_perk_knowledge import (
    DbDPerkKnowledgeStore,
    PerkEnvironment,
    PerkIdentity,
    PerkKnowledgeSource,
    PerkLocalization,
    PerkRevision,
    PerkRevisionStatus,
    PerkRole,
    PerkSourceAuthority,
)
from ai_video_production.game_commentary import (
    CommentaryCandidate,
    CommentaryCandidateStore,
    CommentaryClaim,
    CommentaryClaimKind,
    CommentaryDisposition,
    CommentaryDraft,
    CommentaryFactValidator,
    CommentaryPlanner,
)
from ai_video_production.game_event_evidence import GameEvidence, GameEvidenceType, SourceFrameRange
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.serialization import sha256_bytes
from ai_video_production.timebase import FrameRate


def perk_store(tmp_path: Path) -> DbDPerkKnowledgeStore:
    store = DbDPerkKnowledgeStore(tmp_path / "perks.sqlite3")
    store.put_identity(PerkIdentity("perk_survivor_example", "example", PerkRole.SURVIVOR, introduced_version="9.0.0"))
    store.put_localization(PerkLocalization("perk_survivor_example", "ja-JP", "テストパーク"))
    store.put_source(PerkKnowledgeSource(
        source_id="src.patch.9.1.0", source_type="official_patch_note", authority=PerkSourceAuthority.OFFICIAL_PATCH_NOTE,
        environment=PerkEnvironment.LIVE, uri="source://bhvr/patch", retrieved_at="2026-08-18T00:00:00Z", locale="ja-JP",
        content_sha256=sha256_bytes(b"synthetic commentary source"),
    ))
    store.put_revision(PerkRevision(
        revision_id="PERKREV-001", perk_id="perk_survivor_example", game_version_from="9.0.0", environment=PerkEnvironment.LIVE,
        status=PerkRevisionStatus.VERIFIED, source_ids=("src.patch.9.1.0",), official_effect_ja="窓を越えた後に3秒間だけ移動速度が上がるテスト用効果。",
        structured_effect={"duration_seconds": 3, "status": "HASTE"}, tags=("CHASE", "WINDOW"),
    ))
    return store


def event_with_optional_perk(store: DbDPerkKnowledgeStore, *, confirmation: EventConfirmationState = EventConfirmationState.CONFIRMED, review: EventReviewStatus = EventReviewStatus.AUTO_ACCEPTED, event_type: GameEventType = GameEventType.WINDOW_VAULT, bind_perk: bool = True, activation: bool = False) -> CanonicalGameEvent:
    match = GameMatch(
        production_job_id=generate_id(IdKind.JOB), source_asset_id=generate_id(IdKind.ASSET), game_profile_id="dead_by_daylight",
        game_profile_version="1.0.0", game_version="9.1.0", environment=GameEnvironment.LIVE, perspective=GamePerspective.SURVIVOR,
        source_rate=FrameRate(30000, 1001), status=GameMatchStatus.ANALYZING,
    )
    ev = GameEvidence(
        production_job_id=match.production_job_id, match_id=match.match_id, source_asset_id=match.source_asset_id,
        producer="task049.commentary-fixture", producer_version="1.0.0", evidence_type=GameEvidenceType.VISION,
        source_range=SourceFrameRange(100, 110), confidence_milli=950,
    )
    state = {"fixture": True}
    if activation:
        state["perk_activations"] = [{"perk_id": "perk_survivor_example", "state": "CONFIRMED"}]
    item = CanonicalGameEvent(
        match_id=match.match_id, revision=1, event_type=event_type, source_range=ev.source_range, game_version=match.game_version,
        environment=match.environment, perspective=match.perspective, state=state, confidence_milli=940,
        confirmation_state=confirmation, evidence_refs=(ev.game_evidence_id,), review_status=review,
    )
    return store.bind_event(item, "perk_survivor_example") if bind_perk else item


def claim_for(plan, kind: CommentaryClaimKind) -> CommentaryClaim:
    fact = next(x for x in plan.facts if x.kind is kind)
    return CommentaryClaim(fact.kind, fact.key, fact.value)


def test_planner_proposes_only_confirmed_admitted_significant_event(tmp_path: Path) -> None:
    store = perk_store(tmp_path)
    event = event_with_optional_perk(store)
    plan = CommentaryPlanner().plan(event, perk_store=store, language="ja-JP")
    assert plan.disposition is CommentaryDisposition.PROPOSE
    assert plan.priority_milli == 720
    assert {x.kind for x in plan.facts} == {CommentaryClaimKind.EVENT_OCCURRED, CommentaryClaimKind.PERK_NAME, CommentaryClaimKind.PERK_EFFECT}
    assert plan.knowledge_ref_sha256s == tuple(sorted(plan.knowledge_ref_sha256s))


def test_planner_abstains_on_uncertain_rejected_unknown_or_low_priority_event(tmp_path: Path) -> None:
    store = perk_store(tmp_path)
    uncertain = event_with_optional_perk(store, confirmation=EventConfirmationState.NEEDS_REVIEW, review=EventReviewStatus.PENDING)
    plan = CommentaryPlanner().plan(uncertain, perk_store=store)
    assert plan.disposition is CommentaryDisposition.ABSTAIN
    assert "EVENT_NOT_CONFIRMED" in plan.reason_codes

    rejected = event_with_optional_perk(store, review=EventReviewStatus.HUMAN_REJECTED)
    assert CommentaryPlanner().plan(rejected, perk_store=store).disposition is CommentaryDisposition.ABSTAIN

    low = event_with_optional_perk(store, event_type=GameEventType.MATCH_START, bind_perk=False)
    low_plan = CommentaryPlanner().plan(low)
    assert low_plan.disposition is CommentaryDisposition.ABSTAIN
    assert "LOW_COMMENTARY_PRIORITY" in low_plan.reason_codes


def test_stale_or_incompatible_knowledge_ref_forces_abstention(tmp_path: Path) -> None:
    store = perk_store(tmp_path)
    event = event_with_optional_perk(store)
    bad_ref = replace(event.knowledge_refs[0], revision_id="PERKREV-STALE")
    stale = replace(event, revision=event.revision + 1, knowledge_refs=(bad_ref,))
    plan = CommentaryPlanner().plan(stale, perk_store=store)
    assert plan.disposition is CommentaryDisposition.ABSTAIN
    assert "KNOWLEDGE_REVISION_MISMATCH" in plan.reason_codes


def test_fact_validator_accepts_claims_supported_by_plan(tmp_path: Path) -> None:
    store = perk_store(tmp_path)
    plan = CommentaryPlanner().plan(event_with_optional_perk(store), perk_store=store)
    draft = CommentaryDraft(
        "この場面では窓越えが起き、テストパークの効果は3秒です。",
        tuple(sorted((claim_for(plan, CommentaryClaimKind.EVENT_OCCURRED), claim_for(plan, CommentaryClaimKind.PERK_NAME), claim_for(plan, CommentaryClaimKind.PERK_EFFECT)), key=lambda x: (x.kind.value, x.key, x.value))),
        provider_ref="provider://synthetic-test",
    )
    result = CommentaryFactValidator().validate(plan, draft)
    assert result.passed is True
    candidate = CommentaryCandidate(plan, draft, result)
    assert candidate.status.value == "VALIDATED"


def test_fact_validator_rejects_fabricated_number_and_effect(tmp_path: Path) -> None:
    store = perk_store(tmp_path)
    plan = CommentaryPlanner().plan(event_with_optional_perk(store), perk_store=store)
    fake_effect = CommentaryClaim(CommentaryClaimKind.PERK_EFFECT, "perk.effect.perk_survivor_example", "5秒間加速する")
    draft = CommentaryDraft(
        "このパークは5秒間加速します。",
        (fake_effect,),
    )
    result = CommentaryFactValidator().validate(plan, draft)
    assert result.passed is False
    assert "UNSUPPORTED_PERK_EFFECT_CLAIM" in result.errors
    assert "UNSUPPORTED_NUMBER:5" in result.errors


def test_perk_activation_claim_is_forbidden_without_confirmed_timeline_activation(tmp_path: Path) -> None:
    store = perk_store(tmp_path)
    plan = CommentaryPlanner().plan(event_with_optional_perk(store, activation=False), perk_store=store)
    claim = CommentaryClaim(CommentaryClaimKind.PERK_ACTIVATION, "perk.activation.perk_survivor_example", "CONFIRMED")
    result = CommentaryFactValidator().validate(plan, CommentaryDraft("パークが発動しました。", (claim,)))
    assert result.passed is False
    assert "UNSUPPORTED_PERK_ACTIVATION_CLAIM" in result.errors

    activation_plan = CommentaryPlanner().plan(event_with_optional_perk(store, activation=True), perk_store=store)
    activation_claim = claim_for(activation_plan, CommentaryClaimKind.PERK_ACTIVATION)
    assert CommentaryFactValidator().validate(activation_plan, CommentaryDraft("パークが発動しました。", (activation_claim,))).passed is True


def test_abstaining_plan_cannot_validate_prose(tmp_path: Path) -> None:
    store = perk_store(tmp_path)
    event = event_with_optional_perk(store, confirmation=EventConfirmationState.NEEDS_REVIEW, review=EventReviewStatus.PENDING)
    plan = CommentaryPlanner().plan(event, perk_store=store)
    result = CommentaryFactValidator().validate(plan, CommentaryDraft("断定文です。", ()))
    assert result.passed is False
    assert "PLAN_ABSTAINS" in result.errors


def test_commentary_candidate_store_is_append_only_and_exports_only_validated_by_default(tmp_path: Path) -> None:
    store = perk_store(tmp_path)
    plan = CommentaryPlanner().plan(event_with_optional_perk(store), perk_store=store)
    valid_draft = CommentaryDraft("窓越えが起きました。", (claim_for(plan, CommentaryClaimKind.EVENT_OCCURRED),))
    validator = CommentaryFactValidator()
    valid = CommentaryCandidate(plan, valid_draft, validator.validate(plan, valid_draft))
    invalid_draft = CommentaryDraft("99秒です。", ())
    invalid = CommentaryCandidate(plan, invalid_draft, validator.validate(plan, invalid_draft))

    candidate_store = CommentaryCandidateStore(tmp_path / "commentary.sqlite3")
    candidate_store.append(valid)
    candidate_store.append(valid)
    candidate_store.append(invalid)
    assert len(candidate_store.list_for_event(plan.event_id)) == 2
    assert len(candidate_store.list_for_event(plan.event_id, validated_only=True)) == 1
    output = candidate_store.export_jsonl(tmp_path / "out" / "commentary.jsonl", match_id=plan.match_id)
    lines = output.read_text("utf-8").splitlines()
    assert len(lines) == 1
    assert '"status":"VALIDATED"' in lines[0]


def test_commentary_store_rejects_foreign_sqlite(tmp_path: Path) -> None:
    import sqlite3

    path = tmp_path / "foreign.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE alien(id TEXT)")
    with pytest.raises(Exception, match="not an admitted Commentary store"):
        CommentaryCandidateStore(path)


def test_fact_validator_requires_claims_and_rejects_unbound_status_or_activation_language(tmp_path: Path) -> None:
    store = perk_store(tmp_path)
    plan = CommentaryPlanner().plan(event_with_optional_perk(store), perk_store=store)
    no_claims = CommentaryFactValidator().validate(plan, CommentaryDraft("窓越えが起きました。", ()))
    assert "CLAIMS_REQUIRED" in no_claims.errors

    event_claim = claim_for(plan, CommentaryClaimKind.EVENT_OCCURRED)
    status = CommentaryFactValidator().validate(plan, CommentaryDraft("EXPOSEDになりました。", (event_claim,)))
    assert "UNSUPPORTED_STATUS:EXPOSED" in status.errors

    activation = CommentaryFactValidator().validate(plan, CommentaryDraft("パークが発動しました。", (event_claim,)))
    assert "ACTIVATION_LANGUAGE_REQUIRES_CLAIM" in activation.errors


def test_commentary_store_detects_nested_payload_tamper(tmp_path: Path) -> None:
    import sqlite3

    store = perk_store(tmp_path)
    plan = CommentaryPlanner().plan(event_with_optional_perk(store), perk_store=store)
    draft = CommentaryDraft("窓越えが起きました。", (claim_for(plan, CommentaryClaimKind.EVENT_OCCURRED),))
    validator = CommentaryFactValidator()
    candidate = CommentaryCandidate(plan, draft, validator.validate(plan, draft))
    candidate_store = CommentaryCandidateStore(tmp_path / "commentary.sqlite3")
    candidate_store.append(candidate)
    with sqlite3.connect(candidate_store.path) as conn:
        row = conn.execute("SELECT payload_json FROM commentary_candidates WHERE candidate_id=?", (candidate.candidate_id,)).fetchone()
        payload = row[0].replace('WINDOW_VAULT', 'HOOK', 1)
        conn.execute("UPDATE commentary_candidates SET payload_json=? WHERE candidate_id=?", (payload, candidate.candidate_id))
    with pytest.raises(Exception, match="canonical payload/hash is invalid"):
        candidate_store.list_for_event(plan.event_id)
