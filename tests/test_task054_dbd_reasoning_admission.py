"""Focused TASK-054 R2B existing Fact Validator bridge tests."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from ai_video_production.canonical_game_event import (
    CanonicalGameEvent, EventConfirmationState, EventReviewStatus, GameEnvironment,
    GameEventType, GameKnowledgeKind, GameKnowledgeRef, GameMatch, GameMatchStatus, GamePerspective,
)
from ai_video_production.dbd_reasoning_admission import (
    DbDReasoningFactAdmission, ReasoningFactAdmissionResult,
)
from ai_video_production.dbd_reasoning_context import DbDReasoningContextAssembler, DbDReasoningContextPolicy
from ai_video_production.dbd_reasoning_contracts import ContextFreshness, ReasoningSessionMode
from ai_video_production.dbd_reasoning_validation import DbDReasoningProposalParser
from ai_video_production.game_commentary import CommentaryClaimKind, CommentaryDisposition, CommentaryDraft, CommentaryFact, CommentaryPlan
from ai_video_production.game_event_evidence import GameEvidence, GameEvidenceType, SourceFrameRange
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.timebase import FrameRate


SHA = "sha256:" + "a" * 64
ROOT = Path(__file__).resolve().parents[1]


def _inputs():
    match_id = generate_id(IdKind.GAME_MATCH)
    evidence = GameEvidence(
        production_job_id=generate_id(IdKind.JOB), source_asset_id=generate_id(IdKind.ASSET), match_id=match_id,
        producer="task054.r2b.fixture", producer_version="1.0.0", evidence_type=GameEvidenceType.VISION,
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
        ),
        evidence_refs=(evidence.game_evidence_id,), knowledge_ref_sha256s=(knowledge.to_dict()["knowledge_ref_sha256"],),
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


def _proposal(*, disposition: str = "PROPOSE", observed=None, canonical=None, text: str = "窓越え、しなやかです。"):
    payload = {
        "schema_version": "1.0.0", "disposition": disposition,
        "observed_claims": observed if observed is not None else [{"kind": "EVENT_OCCURRED", "key": "event.type", "value": "WINDOW_VAULT"}],
        "canonical_claims": canonical if canonical is not None else [{"kind": "PERK_NAME", "key": "perk.name.perk_lithe", "value": "しなやか"}],
        "inferred_states": [], "tactical_interpretations": [], "commentary_outline": [] if disposition == "ABSTAIN" else ["窓越え"],
        "commentary_text": "" if disposition == "ABSTAIN" else text, "citations": [], "uncertainty_codes": [],
        "style_metrics": {"density_milli": 500, "emotion_milli": 400, "tempo_milli": 600},
    }
    result = DbDReasoningProposalParser().parse(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode())
    assert result.quarantined_proposal is not None
    return result.quarantined_proposal


def test_exact_copy_uses_existing_fact_validator_and_emits_body_free_receipt() -> None:
    context, plan = _inputs()
    result = DbDReasoningFactAdmission().admit(context, plan, _proposal())
    assert result.receipt.passed is True
    assert result.draft is not None and result.draft.provider_ref is None
    assert [(claim.kind.value, claim.key, claim.value) for claim in result.draft.claims] == [
        ("EVENT_OCCURRED", "event.type", "WINDOW_VAULT"),
        ("PERK_NAME", "perk.name.perk_lithe", "しなやか"),
    ]
    receipt = result.receipt.to_dict()
    assert receipt["commentary_draft_sha256"] == result.draft.to_dict()["commentary_draft_sha256"]
    assert "commentary_text" not in receipt and "claims" not in receipt


@pytest.mark.parametrize(("proposal", "code"), [
    (_proposal(observed=[{"kind": "PERK_NAME", "key": "perk.name.perk_lithe", "value": "しなやか"}], canonical=[]), "OBSERVED_FACT_NOT_EXACT"),
    (_proposal(canonical=[{"kind": "PERK_NAME", "key": "perk.name.perk_lithe", "value": "別名"}]), "CANONICAL_FACT_NOT_EXACT"),
    (_proposal(observed=[], canonical=[], text="断定文です。"), "CLAIMS_REQUIRED"),
    (_proposal(text="42秒で窓を越えました。"), "UNSUPPORTED_NUMBER"),
    (_proposal(text="パークが発動しました。"), "ACTIVATION_LANGUAGE_REQUIRES_CLAIM"),
])
def test_membership_and_existing_fact_validator_fail_closed(proposal, code: str) -> None:
    context, plan = _inputs()
    result = DbDReasoningFactAdmission().admit(context, plan, proposal)
    assert result.receipt.passed is False and result.draft is None
    assert code in result.receipt.error_codes
    if code == "UNSUPPORTED_NUMBER":
        assert result.existing_validation is not None
        assert "UNSUPPORTED_NUMBER:42" in result.existing_validation.errors
        assert all("42" not in receipt_code for receipt_code in result.receipt.error_codes)


def test_context_plan_and_disposition_boundaries_fail_closed() -> None:
    context, plan = _inputs()
    stale = replace(context, freshness=ContextFreshness.STALE)
    assert "CONTEXT_NOT_DISPATCHABLE" in DbDReasoningFactAdmission().admit(stale, plan, _proposal()).receipt.error_codes
    wrong_language = replace(plan, language="en-US")
    assert "PLAN_CONTEXT_COORDINATE_MISMATCH" in DbDReasoningFactAdmission().admit(context, wrong_language, _proposal()).receipt.error_codes
    wrong_dependencies = replace(plan, knowledge_ref_sha256s=())
    assert "PLAN_CONTEXT_DEPENDENCY_MISMATCH" in DbDReasoningFactAdmission().admit(context, wrong_dependencies, _proposal()).receipt.error_codes
    review = _proposal(disposition="REVIEW_REQUIRED")
    assert DbDReasoningFactAdmission().admit(context, plan, review).receipt.error_codes == ("STRUCTURAL_DISPOSITION_NOT_PROPOSE",)
    abstain = _proposal(disposition="ABSTAIN", observed=[], canonical=[])
    assert DbDReasoningFactAdmission().admit(context, plan, abstain).receipt.error_codes == ("STRUCTURAL_DISPOSITION_NOT_PROPOSE",)


def test_receipt_and_result_cannot_be_forged_or_mismatched() -> None:
    context, plan = _inputs()
    result = DbDReasoningFactAdmission().admit(context, plan, _proposal())
    with pytest.raises(ValueError):
        replace(result.receipt, schema_version="999.0.0")
    with pytest.raises(ValueError):
        replace(result.receipt, receipt_sha256="sha256:" + "0" * 64)
    with pytest.raises(ValueError):
        replace(result.receipt, passed=False, error_codes=("FORGED",))
    with pytest.raises(ValueError, match="bool"):
        replace(result.receipt, passed=1)  # type: ignore[arg-type]
    assert result.draft is not None
    different = CommentaryDraft("別の本文です。", result.draft.claims)
    with pytest.raises(ValueError):
        ReasoningFactAdmissionResult(result.receipt, different)
    provider_draft = CommentaryDraft(result.draft.text, result.draft.claims, "provider://synthetic")
    provider_receipt = replace(result.receipt, commentary_draft_sha256=provider_draft.to_dict()["commentary_draft_sha256"], receipt_sha256="")
    with pytest.raises(ValueError, match="provider_ref"):
        ReasoningFactAdmissionResult(provider_receipt, provider_draft, result.existing_validation)


def test_r2b_has_no_candidate_store_provider_or_io_and_invokes_existing_validator() -> None:
    source = (ROOT / "src" / "ai_video_production" / "dbd_reasoning_admission.py").read_text(encoding="utf-8")
    assert "CommentaryFactValidator().validate(plan, draft)" in source
    assert "CommentaryCandidate" not in source
    assert "CandidateStore" not in source
    assert "sqlite" not in source.casefold()
    assert "open(" not in source
