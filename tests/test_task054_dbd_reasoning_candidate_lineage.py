"""Focused TASK-054 R2D-A pure composition and lineage tests."""
from __future__ import annotations

from dataclasses import replace
import inspect
import json
from pathlib import Path

import pytest

from ai_video_production.dbd_reasoning_candidate_lineage import (
    DbDReasoningCandidateComposer, DbDReasoningCandidateCreationResult,
)
from ai_video_production.game_commentary import FactValidationResult
from ai_video_production.ids import IdKind, generate_id
from test_task054_dbd_reasoning_policy_admission import _inputs


ROOT = Path(__file__).resolve().parents[1]


def _raw(context, *, text: str = "窓越え、しなやかです。", citation: str | None = None) -> bytes:
    citations = [] if citation is None else [citation]
    payload = {
        "schema_version": "1.0.0", "disposition": "PROPOSE",
        "observed_claims": [{"kind": "EVENT_OCCURRED", "key": "event.type", "value": "WINDOW_VAULT"}],
        "canonical_claims": [{"kind": "PERK_NAME", "key": "perk.name.perk_lithe", "value": "しなやか"}],
        "inferred_states": [], "tactical_interpretations": [], "commentary_outline": ["窓越え"],
        "commentary_text": text, "citations": citations, "uncertainty_codes": [],
        "style_metrics": {"density_milli": 500, "emotion_milli": 400, "tempo_milli": 600},
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()


def test_canonical_composition_creates_existing_candidate_and_body_safe_lineage() -> None:
    context, plan = _inputs()
    raw = _raw(context)
    result = DbDReasoningCandidateComposer().create(raw_output=raw, context=context, plan=plan)
    assert result.passed is True and result.candidate is not None and result.lineage is not None
    assert result.candidate.status.value == "VALIDATED"
    assert result.candidate.draft.provider_ref is None
    payload = result.lineage.to_dict()
    assert payload["candidate_id"] == result.candidate.candidate_id
    assert payload["commentary_candidate_sha256"] == result.candidate.to_dict()["commentary_candidate_sha256"]
    assert payload["fact_admission_receipt"]["passed"] is True
    assert payload["policy_admission_receipt"]["passed"] is True
    assert payload["proposal"]["proposal_sha256"] == payload["policy_admission_receipt"]["proposal_sha256"]
    encoded = json.dumps(payload, ensure_ascii=False)
    assert raw.decode() not in encoded and "credential" not in encoded.casefold()


@pytest.mark.parametrize(("raw_factory", "expected"), [
    (lambda context: b"{}", "PROPOSAL_SHAPE_INVALID"),
    (lambda context: _raw(context, text="42秒で窓を越えました。"), "UNSUPPORTED_NUMBER"),
    (lambda context: _raw(context, text="api_key=secret-value"), "DLP_POLICY_REJECTED"),
    (lambda context: _raw(context, citation="evidence://game/GEVD-00000000000000000000000000"), "REFERENCE_NOT_IN_CONTEXT"),
])
def test_each_admission_failure_returns_no_candidate_or_lineage(raw_factory, expected: str) -> None:
    context, plan = _inputs()
    result = DbDReasoningCandidateComposer().create(raw_output=raw_factory(context), context=context, plan=plan)
    assert result.passed is False and result.candidate is None and result.lineage is None
    assert expected in result.error_codes


def test_lineage_and_result_crossing_or_forge_fail_closed() -> None:
    context, plan = _inputs()
    result = DbDReasoningCandidateComposer().create(raw_output=_raw(context), context=context, plan=plan)
    assert result.lineage is not None and result.candidate is not None
    with pytest.raises(ValueError):
        replace(result.lineage, context_sha256="sha256:" + "0" * 64)
    with pytest.raises(ValueError):
        replace(result.lineage, lineage_sha256="sha256:" + "0" * 64)
    with pytest.raises(ValueError, match="root"):
        replace(result.lineage, parent_candidate_id=result.candidate.candidate_id)
    with pytest.raises(ValueError, match="candidate"):
        DbDReasoningCandidateCreationResult(True, (), result.raw_output_sha256, object(), result.lineage)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="bool"):
        replace(result, passed=1)  # type: ignore[arg-type]


def test_candidate_body_status_provider_and_coordinates_are_rechecked() -> None:
    context, plan = _inputs()
    result = DbDReasoningCandidateComposer().create(raw_output=_raw(context), context=context, plan=plan)
    assert result.candidate is not None and result.lineage is not None

    provider_candidate = replace(result.candidate, draft=replace(result.candidate.draft, provider_ref="provider://forged"))
    provider_lineage = replace(
        result.lineage,
        commentary_candidate_sha256=provider_candidate.to_dict()["commentary_candidate_sha256"],
        lineage_sha256="",
    )
    with pytest.raises(ValueError, match="mismatch"):
        DbDReasoningCandidateCreationResult(True, (), result.raw_output_sha256, provider_candidate, provider_lineage)

    rejected_candidate = replace(result.candidate, validation=FactValidationResult(False, ("FORGED",)))
    rejected_lineage = replace(
        result.lineage,
        commentary_candidate_sha256=rejected_candidate.to_dict()["commentary_candidate_sha256"],
        lineage_sha256="",
    )
    with pytest.raises(ValueError, match="mismatch"):
        DbDReasoningCandidateCreationResult(True, (), result.raw_output_sha256, rejected_candidate, rejected_lineage)

    wrong_coordinates = replace(
        result.lineage, match_id=generate_id(IdKind.GAME_MATCH), event_revision=99, lineage_sha256="",
    )
    with pytest.raises(ValueError, match="mismatch"):
        DbDReasoningCandidateCreationResult(True, (), result.raw_output_sha256, result.candidate, wrong_coordinates)


def test_composer_accepts_no_external_receipt_candidate_or_proposal_authority() -> None:
    parameters = tuple(inspect.signature(DbDReasoningCandidateComposer.create).parameters)
    assert parameters == ("self", "raw_output", "context", "plan")
    source = (ROOT / "src" / "ai_video_production" / "dbd_reasoning_candidate_lineage.py").read_text("utf-8")
    assert "DbDReasoningProposalParser().parse(raw_output)" in source
    assert "DbDReasoningFactAdmission().admit(context, plan, structural)" in source
    assert "DbDReasoningPolicyAdmission().admit(" in source
    assert "CommentaryCandidateStore" not in source and "sqlite" not in source.casefold()
    assert "open(" not in source and "provider_ref is not None" in source
