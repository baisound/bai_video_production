"""Focused TASK-054 R2C policy-admission tests."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

import pytest

from ai_video_production.canonical_game_event import (
    CanonicalGameEvent, EventConfirmationState, EventReviewStatus, GameEnvironment,
    GameEventType, GameKnowledgeKind, GameKnowledgeRef, GameMatch, GameMatchStatus, GamePerspective,
)
from ai_video_production.dbd_reasoning_admission import DbDReasoningFactAdmission
from ai_video_production.dbd_reasoning_context import DbDReasoningContextAssembler, DbDReasoningContextPolicy
from ai_video_production.dbd_reasoning_contracts import RagChunk, ReasoningSessionMode
from ai_video_production.dbd_reasoning_policy_admission import ContextReferenceIndex, DbDReasoningPolicyAdmission, ReasoningPolicyAdmissionResult
from ai_video_production.dbd_reasoning_validation import DbDReasoningProposalParser
from ai_video_production.game_commentary import CommentaryClaimKind, CommentaryDisposition, CommentaryFact, CommentaryPlan
from ai_video_production.game_event_evidence import GameEvidence, GameEvidenceType, SourceFrameRange
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.timebase import FrameRate


SHA = "sha256:" + "a" * 64
ROOT = Path(__file__).resolve().parents[1]


def _inputs():
    match_id = generate_id(IdKind.GAME_MATCH)
    evidence = GameEvidence(
        production_job_id=generate_id(IdKind.JOB), source_asset_id=generate_id(IdKind.ASSET), match_id=match_id,
        producer="task054.r2c.fixture", producer_version="1.0.0", evidence_type=GameEvidenceType.VISION,
        source_range=SourceFrameRange(100, 140), confidence_milli=950,
    )
    knowledge = GameKnowledgeRef(
        GameKnowledgeKind.PERK, "perk_lithe", "PERKREV-001", GameEnvironment.LIVE,
        "9.0.0", "source://bhvr/perks/lithe", "9.2.0",
    )
    event = CanonicalGameEvent(
        match_id=match_id, revision=2, event_type=GameEventType.WINDOW_VAULT,
        source_range=SourceFrameRange(110, 130), game_version="9.1.0", environment=GameEnvironment.LIVE,
        perspective=GamePerspective.SURVIVOR, state={}, confidence_milli=900,
        confirmation_state=EventConfirmationState.CONFIRMED, evidence_refs=(evidence.game_evidence_id,),
        knowledge_refs=(knowledge,), review_status=EventReviewStatus.AUTO_ACCEPTED,
    )
    plan = CommentaryPlan(
        match_id=match_id, event_id=event.event_id, event_revision=2, language="ja-JP",
        disposition=CommentaryDisposition.PROPOSE, priority_milli=700, reason_codes=(),
        facts=(
            CommentaryFact(CommentaryClaimKind.EVENT_OCCURRED, "event.type", "WINDOW_VAULT"),
            CommentaryFact(CommentaryClaimKind.PERK_NAME, "perk.name.perk_lithe", "しなやか"),
        ), evidence_refs=(evidence.game_evidence_id,),
        knowledge_ref_sha256s=(knowledge.to_dict()["knowledge_ref_sha256"],),
    )
    match = GameMatch(
        production_job_id=evidence.production_job_id, source_asset_id=evidence.source_asset_id,
        game_profile_id="dead_by_daylight", game_profile_version="1.0.0", game_version=event.game_version,
        environment=event.environment, perspective=event.perspective, source_rate=FrameRate(30, 1),
        status=GameMatchStatus.ANALYZING, match_id=match_id,
    )
    evidence_map = {evidence.game_evidence_id: evidence}
    evidence_sha = {evidence.game_evidence_id: evidence.to_dict()["game_evidence_sha256"]}
    context = DbDReasoningContextAssembler().assemble(
        event=event, match=match, commentary_plan=plan, evidence_by_id=evidence_map,
        evidence_sha256_by_id=evidence_sha, current_evidence_sha256_by_id=evidence_sha,
        knowledge_refs=(knowledge,), trivia_entries=(), rag_results=(), policy=DbDReasoningContextPolicy(locale="ja-JP"),
        current_event_revision=event.revision, current_event_sha256=event.to_dict()["event_sha256"],
        timeline_sha256=SHA, current_timeline_sha256=SHA, session_mode=ReasoningSessionMode.PREVIEW_NO_LEARNING,
        speech_budget_ms=3000, style_profile_ref="style://dbd-ja-balanced",
    )
    return context, plan


def _proposal(context, *, text="窓越え、しなやかです。", citations=None, inferences=None, metrics=None, uncertainty=None):
    evidence_ref = f"evidence://game/{context.evidence_refs[0]}"
    payload = {
        "schema_version": "1.0.0", "disposition": "PROPOSE",
        "observed_claims": [{"kind": "EVENT_OCCURRED", "key": "event.type", "value": "WINDOW_VAULT"}],
        "canonical_claims": [{"kind": "PERK_NAME", "key": "perk.name.perk_lithe", "value": "しなやか"}],
        "inferred_states": inferences or [], "tactical_interpretations": [], "commentary_outline": ["窓越え"],
        "commentary_text": text, "citations": citations if citations is not None else [],
        "uncertainty_codes": uncertainty or [],
        "style_metrics": metrics or {"density_milli": 500, "emotion_milli": 400, "tempo_milli": 600},
    }
    result = DbDReasoningProposalParser().parse(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode())
    assert result.quarantined_proposal is not None
    return result.quarantined_proposal, evidence_ref


def _admit(context, plan, structural):
    fact = DbDReasoningFactAdmission().admit(context, plan, structural)
    return DbDReasoningPolicyAdmission().admit(context=context, plan=plan, structural=structural, fact_result=fact)


def test_context_reference_index_is_deterministic_and_exact() -> None:
    context, _ = _inputs()
    first = ContextReferenceIndex.from_context(context)
    second = ContextReferenceIndex.from_context(context)
    assert first == second
    assert f"evidence://game/{context.evidence_refs[0]}" in first.references
    assert f"knowledge://sha256/{context.knowledge_ref_sha256s[0].removeprefix('sha256:')}" in first.references


def test_rag_cannot_collide_with_canonical_reference_namespace() -> None:
    context, _ = _inputs()
    text = "retrieved data"
    chunk = RagChunk(
        f"evidence://game/{context.evidence_refs[0]}", "MANUAL", "ADMITTED", "9.0.0:9.2.0",
        "VERIFIED", text, "sha256:" + sha256(text.encode()).hexdigest(), "UNTRUSTED_DATA",
    )
    collision = replace(context, rag_chunks=(chunk,))
    with pytest.raises(ValueError, match="collides"):
        ContextReferenceIndex.from_context(collision)
    reserved = replace(chunk, source_ref="provider://model/gpt")
    with pytest.raises(ValueError, match="reserved"):
        ContextReferenceIndex.from_context(replace(context, rag_chunks=(reserved,)))
    digest = context.knowledge_ref_sha256s[0].removeprefix("sha256:")
    for masquerade in (
        f"KNOWLEDGE://sha256/{digest}", f"knowledge://SHA256/{digest}",
        "knowledge://sha256/" + "b" * 64, "knowledge://dbd/a/../b", "knowledge://dbd/a%2Fb",
    ):
        disguised = replace(chunk, source_ref=masquerade)
        with pytest.raises(ValueError, match="knowledge|noncanonical|aliasing|collides"):
            ContextReferenceIndex.from_context(replace(context, rag_chunks=(disguised,)))
    first = replace(chunk, source_ref="trivia://TRIV-01ARZ3NDEKTSV4RRFFQ69G5FAV/r1")
    second = replace(chunk, source_ref="trivia://triv-01ARZ3NDEKTSV4RRFFQ69G5FAV/r1")
    duplicate_identity = replace(context, rag_chunks=tuple(sorted((first, second), key=lambda item: item.source_ref)))
    with pytest.raises(ValueError, match="identity"):
        ContextReferenceIndex.from_context(duplicate_identity)


def test_pass_rechecks_r2b_and_only_then_creates_canonical_proposal() -> None:
    context, plan = _inputs()
    evidence_ref = f"evidence://game/{context.evidence_refs[0]}"
    structural, _ = _proposal(context, citations=[evidence_ref], inferences=[{
        "statement": "追跡が続く可能性があります。", "qualifier": "LIKELY", "confidence_milli": 750,
        "supporting_refs": [evidence_ref],
    }])
    result = _admit(context, plan, structural)
    assert result.receipt.passed is True and result.proposal is not None
    assert result.proposal.to_dict()["proposal_sha256"] == result.receipt.proposal_sha256
    receipt = result.receipt.to_dict()
    assert "commentary_text" not in receipt and "citations" not in receipt and "claims" not in receipt


def test_fact_result_is_recomputed_and_cannot_be_used_as_authority_token() -> None:
    context, plan = _inputs()
    structural, _ = _proposal(context)
    other, _ = _proposal(context, text="別の安全な解説です。")
    foreign_fact = DbDReasoningFactAdmission().admit(context, plan, other)
    result = DbDReasoningPolicyAdmission().admit(context=context, plan=plan, structural=structural, fact_result=foreign_fact)
    assert result.receipt.passed is False
    assert "FACT_ADMISSION_RESULT_MISMATCH" in result.receipt.error_codes


@pytest.mark.parametrize("case", ["unknown", "not_cited", "likely_without_ref", "likely_low"])
def test_reference_membership_citation_completeness_and_likely_floor(case: str) -> None:
    context, plan = _inputs()
    allowed = f"evidence://game/{context.evidence_refs[0]}"
    refs = [] if case == "likely_without_ref" else [allowed]
    confidence = 699 if case == "likely_low" else 750
    citations = [] if case in {"not_cited", "likely_without_ref"} else refs
    if case == "unknown":
        refs = citations = ["evidence://game/GEVD-00000000000000000000000000"]
    structural, _ = _proposal(context, citations=citations, inferences=[{
        "statement": "戦術上の仮説です。", "qualifier": "LIKELY", "confidence_milli": confidence,
        "supporting_refs": refs,
    }])
    result = _admit(context, plan, structural)
    assert result.receipt.passed is False
    expected = {
        "unknown": "REFERENCE_NOT_IN_CONTEXT", "not_cited": "SUPPORTING_REFERENCE_NOT_CITED",
        "likely_without_ref": "LIKELY_REQUIRES_SUPPORTED_CONFIDENCE", "likely_low": "LIKELY_REQUIRES_SUPPORTED_CONFIDENCE",
    }[case]
    assert expected in result.receipt.error_codes


@pytest.mark.parametrize("unsafe", [
    "api_key=secret-value", "Bearer abcdefghijklmnop", "AKIAABCDEFGHIJKLMNOP",
    "eyJabcdefghij.abcdefghij.abcdefghij", "chain.of.thought", "tool invocation",
    "<analysis>private</analysis>", "<tool>call</tool>", "<provider>openai</provider>",
    "route/id", "provider/value", "provider.name=demo", "provider=openai", "model=gpt", "route=local",
    "api key is hunter2", "password hunter2", "sk/live/secretvalue",
    "C:/Users/name/secret.txt", "~/secret/file", "\\Windows\\secret.txt", "/秘密", "/ユーザー/秘密/file",
    "https://example.com/private", "www.example.com/private", "example.com/private", "mailto:user@example.com",
    "data:text/plain,hello", "ipfs:QmSafeReference", "magnet:?xt=urn:btih:abcdef", "javascript:alert",
    "example.xyz/private", "dbd.gg/build", "provider: openai", "model: gpt", "route: local",
    "glpat-abcdefghijklmnopqrstuv", "hf_abcdefghijklmnopqrstuvwxyz",
    "Bearer sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "sk-sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
    "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
    "abcdefghijklmnopqrstuvwxyzabcdef",
    "AbC9dEf8GhJ7kLm6NpQ5rSt4UvW3xYz2",
])
def test_dlp_rejects_secrets_execution_metadata_paths_and_text_urls(unsafe: str) -> None:
    context, plan = _inputs()
    structural, _ = _proposal(context, text=f"解説 {unsafe}")
    result = _admit(context, plan, structural)
    assert result.receipt.passed is False
    assert "DLP_POLICY_REJECTED" in result.receipt.error_codes


@pytest.mark.parametrize("safe", [
    "窓越えから追跡が続きます。", "オンとオフを切り替えます。", "段階1から段階2です。",
    "状況: 追跡中です。", "Note: safe commentary.",
    "GEVT-01ARZ3NDEKTSV4RRFFQ69G5FAV の場面です。",
    "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa を照合済みです。",
    "123e4567-e89b-12d3-a456-426614174000 を識別子として確認しました。",
])
def test_dlp_keeps_normal_japanese_and_canonical_identifiers(safe: str) -> None:
    context, plan = _inputs()
    structural, _ = _proposal(context, text=safe)
    result = _admit(context, plan, structural)
    assert "DLP_POLICY_REJECTED" not in result.receipt.error_codes


def test_uncertainty_speech_style_and_receipt_forge_fail_closed() -> None:
    context, plan = _inputs()
    structural, _ = _proposal(context, uncertainty=["MODEL_UNCERTAIN"])
    assert "UNCERTAINTY_NOT_IN_CONTEXT" in _admit(context, plan, structural).receipt.error_codes
    structural, _ = _proposal(context, metrics={"density_milli": 901, "emotion_milli": 400, "tempo_milli": 600})
    assert "STYLE_POLICY_EXCEEDED" in _admit(context, plan, structural).receipt.error_codes
    forbidden_context = replace(context, forbidden_claims=("PATCH_CLAIM",))
    for wording in ("patch claim", "patch-claim", "ｐａｔｃｈ　ｃｌａｉｍ"):
        structural, _ = _proposal(forbidden_context, text=wording)
        assert "FORBIDDEN_CLAIM" in _admit(forbidden_context, plan, structural).receipt.error_codes
    tiny_budget = replace(context, speech_budget_ms=1)
    structural, _ = _proposal(tiny_budget)
    assert "SPEECH_BUDGET_EXCEEDED" in _admit(tiny_budget, plan, structural).receipt.error_codes
    structural, _ = _proposal(context)
    passed = _admit(context, plan, structural)
    with pytest.raises(ValueError, match="bool"):
        replace(passed.receipt, passed=1)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        replace(passed.receipt, receipt_sha256="sha256:" + "0" * 64)
    assert passed.proposal is not None
    with pytest.raises(ValueError):
        ReasoningPolicyAdmissionResult(passed.receipt, replace(passed.proposal, commentary_text="差替え"))
    class FakeProposal:
        def to_dict(self):
            return {"proposal_sha256": passed.receipt.proposal_sha256}
    with pytest.raises(ValueError, match="DbDReasoningProposal"):
        ReasoningPolicyAdmissionResult(passed.receipt, FakeProposal())  # type: ignore[arg-type]


def test_r2c_has_no_candidate_store_provider_or_io() -> None:
    source = (ROOT / "src" / "ai_video_production" / "dbd_reasoning_policy_admission.py").read_text(encoding="utf-8")
    assert "CommentaryCandidate" not in source and "CandidateStore" not in source
    assert "sqlite" not in source.casefold() and "open(" not in source
    assert "DbDReasoningFactAdmission().admit(context, plan, structural)" in source
