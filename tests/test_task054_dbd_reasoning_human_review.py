"""Focused TASK-054 R2D-C1 inert Human-review contract tests."""
from __future__ import annotations

from dataclasses import replace
import inspect
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from ai_video_production.dbd_reasoning_candidate_lineage import DbDReasoningCandidateComposer
from ai_video_production.dbd_reasoning_human_review import (
    CurrentHumanReviewSnapshot, DbDReasoningHumanReviewRecord,
    HumanReviewDecision, admit_human_review,
    admit_reasoning_human_review_authority_record,
    admit_reasoning_human_review_record,
)
from ai_video_production.game_commentary import CommentaryCandidateStore
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from test_task054_dbd_reasoning_candidate_lineage import _raw
from test_task054_dbd_reasoning_policy_admission import _inputs


ROOT = Path(__file__).resolve().parents[1]
H1 = "sha256:" + "1" * 64


def _snapshot(*, head_revision: int = 0, head_sha: str | None = None):
    context, plan = _inputs()
    result = DbDReasoningCandidateComposer().create(raw_output=_raw(context), context=context, plan=plan)
    assert result.candidate is not None and result.lineage is not None
    current = CurrentHumanReviewSnapshot(
        result.candidate.candidate_id, result.candidate, result.lineage, context, plan,
        head_revision, head_sha,
    )
    return context, plan, result, current


def _rehash(record: dict[str, object]) -> dict[str, object]:
    body = {key: value for key, value in record.items() if key != "binding_sha256"}
    record["binding_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return record


def _authority(current: CurrentHumanReviewSnapshot, *, decision: str = "APPROVE", **overrides) -> dict[str, object]:
    candidate = current.leaf_candidate.to_dict()
    lineage = current.leaf_lineage
    record: dict[str, object] = {
        "schema_version": "1.0.0", "record_kind": "DBD_REASONING_HUMAN_REVIEW_AUTHORITY_BINDING",
        "contract_state": "BOUND_VERIFIED", "confirmation_ref": "human-confirmation://dbd-review/01ARZ3NDEKTSV4RRFFQ69G5FAV",
        "confirmation_revision": 1, "confirmation_sha256": H1, "reviewer_kind": "HUMAN",
        "decision": decision, "decided_at": "2026-08-22T00:00:00Z", "expires_at": "2026-08-22T00:10:00Z",
        "one_shot": True, "authority_evidence_ref": "human-evidence://dbd-review/sha256/" + "2" * 64,
        "authority_evidence_sha256": "sha256:" + "2" * 64,
        "root_candidate_id": current.root_candidate_id,
        "expected_leaf_candidate_id": current.leaf_candidate.candidate_id,
        "expected_leaf_candidate_sha256": candidate["commentary_candidate_sha256"],
        "expected_leaf_lineage_sha256": lineage.lineage_sha256,
        "expected_context_sha256": current.context.to_dict()["context_sha256"],
        "expected_commentary_plan_sha256": current.plan.to_dict()["commentary_plan_sha256"],
        "expected_proposal_sha256": lineage.proposal.to_dict()["proposal_sha256"],
        "expected_previous_review_revision": current.review_head_revision,
        "expected_previous_review_sha256": current.review_head_sha256,
        "reason_codes": [] if decision == "APPROVE" else ["HUMAN_REVIEW_DECISION"],
        "correction_request_sha256": "sha256:" + "3" * 64 if decision == "REVISE" else None,
        "binding_sha256": "",
    }
    record.update(overrides)
    return _rehash(record)


def _unresolved() -> dict[str, object]:
    record = _authority(_snapshot()[3])
    for key in tuple(record):
        if key not in {"schema_version", "record_kind", "contract_state", "binding_sha256"}:
            record[key] = None
    record["contract_state"] = "CANONICAL_REF_NOT_PROVIDED"
    return _rehash(record)


def test_approve_creates_only_inert_hash_chained_review_evidence() -> None:
    _, _, _, current = _snapshot()
    admitted = admit_human_review(
        authority_record=_authority(current), current=current, previous_review=None,
        evaluated_at="2026-08-22T00:05:00Z",
    )
    assert admitted.passed is True and admitted.review_record is not None
    record = admitted.review_record.to_dict()
    assert record["decision"] == "APPROVE" and record["review_revision"] == 1
    assert record["previous_review_sha256"] is None
    assert record["reviewed_at"] == "2026-08-22T00:00:00Z"
    assert "exportable" not in record and "approved_for_delivery" not in record
    assert not hasattr(admitted, "exportable") and not hasattr(admitted, "dispatch")


def test_second_review_requires_exact_current_head_and_previous_record() -> None:
    _, _, result, current = _snapshot()
    first = admit_human_review(
        authority_record=_authority(current), current=current, previous_review=None,
        evaluated_at="2026-08-22T00:05:00Z",
    ).review_record
    assert first is not None and result.candidate is not None and result.lineage is not None
    second_current = CurrentHumanReviewSnapshot(
        result.candidate.candidate_id, result.candidate, result.lineage,
        current.context, current.plan, 1, first.review_sha256,
    )
    second = admit_human_review(
        authority_record=_authority(
            second_current, decision="REVISE", decided_at="2026-08-22T00:05:30Z",
            confirmation_sha256="sha256:" + "4" * 64,
        ), current=second_current,
        previous_review=first, evaluated_at="2026-08-22T00:06:00Z",
    )
    assert second.passed is True and second.review_record is not None
    assert second.review_record.review_revision == 2
    assert second.review_record.previous_review_sha256 == first.review_sha256
    assert second.review_record.correction_request_sha256 is not None

    replay = admit_human_review(
        authority_record=_authority(second_current), current=second_current,
        previous_review=first, evaluated_at="2026-08-22T00:06:00Z",
    )
    assert replay.error_codes == ("HUMAN_CONFIRMATION_REPLAYED",)

    stale = admit_human_review(
        authority_record=_authority(current), current=second_current, previous_review=first,
        evaluated_at="2026-08-22T00:06:00Z",
    )
    assert stale.error_codes == ("CURRENT_COORDINATE_MISMATCH",) and stale.review_record is None


@pytest.mark.parametrize("field", [
    "expected_leaf_candidate_sha256", "expected_leaf_lineage_sha256", "expected_context_sha256",
    "expected_commentary_plan_sha256", "expected_proposal_sha256",
])
def test_current_coordinate_or_hash_crossing_fails_closed(field: str) -> None:
    _, _, _, current = _snapshot()
    authority = _authority(current)
    authority[field] = "sha256:" + "0" * 64
    _rehash(authority)
    result = admit_human_review(
        authority_record=authority, current=current, previous_review=None,
        evaluated_at="2026-08-22T00:05:00Z",
    )
    assert result.error_codes == ("CURRENT_COORDINATE_MISMATCH",) and result.review_record is None


def test_missing_unresolved_expired_or_nonhuman_authority_never_creates_review() -> None:
    _, _, _, current = _snapshot()
    unresolved = admit_human_review(
        authority_record=_unresolved(), current=current, previous_review=None,
        evaluated_at="2026-08-22T00:05:00Z",
    )
    assert unresolved.error_codes == ("HUMAN_AUTHORITY_NOT_BOUND",)
    expired = admit_human_review(
        authority_record=_authority(current), current=current, previous_review=None,
        evaluated_at="2026-08-22T00:10:00Z",
    )
    assert expired.error_codes == ("HUMAN_CONFIRMATION_EXPIRED",)
    ai = _authority(current, reviewer_kind="AI")
    rejected = admit_human_review(
        authority_record=ai, current=current, previous_review=None,
        evaluated_at="2026-08-22T00:05:00Z",
    )
    assert rejected.error_codes == ("AUTHORITY_BINDING_INVALID",)
    assert unresolved.review_record is expired.review_record is rejected.review_record is None


@pytest.mark.parametrize(("decision", "reasons", "correction", "valid"), [
    ("APPROVE", [], None, True), ("APPROVE", [], H1, False),
    ("REJECT", [], None, False), ("REJECT", ["NOT_USEFUL"], None, True),
    ("REVISE", ["FACTUAL_EDIT_REQUIRED"], None, False),
    ("REVISE", ["FACTUAL_EDIT_REQUIRED"], H1, True),
])
def test_decision_conditional_fields(decision: str, reasons: list[str], correction: str | None, valid: bool) -> None:
    _, _, _, current = _snapshot()
    record = _authority(current, decision=decision, reason_codes=reasons, correction_request_sha256=correction)
    if valid:
        assert admit_reasoning_human_review_authority_record(record).to_dict() == record
    else:
        with pytest.raises(ValueError):
            admit_reasoning_human_review_authority_record(record)


def test_review_record_hash_and_invariants_resist_replace_forge() -> None:
    _, _, _, current = _snapshot()
    review = admit_human_review(
        authority_record=_authority(current), current=current, previous_review=None,
        evaluated_at="2026-08-22T00:05:00Z",
    ).review_record
    assert review is not None
    with pytest.raises(ValueError, match="sha256"):
        replace(review, context_sha256="sha256:" + "0" * 64)
    with pytest.raises(ValueError, match="previous"):
        replace(review, review_revision=2, review_sha256="")
    with pytest.raises(ValueError, match="root and leaf"):
        replace(review, leaf_candidate_id="CAND-R2D" + "0" * 23, review_sha256="")


def test_review_hash_is_deterministic_for_same_human_confirmation() -> None:
    _, _, _, current = _snapshot()
    authority = _authority(current)
    first = admit_human_review(
        authority_record=authority, current=current, previous_review=None,
        evaluated_at="2026-08-22T00:05:00Z",
    ).review_record
    second = admit_human_review(
        authority_record=authority, current=current, previous_review=None,
        evaluated_at="2026-08-22T00:06:00Z",
    ).review_record
    assert first is not None and second is not None and first == second


def test_previous_review_full_coordinate_crossing_fails_closed() -> None:
    _, _, result, current = _snapshot()
    previous = admit_human_review(
        authority_record=_authority(current), current=current, previous_review=None,
        evaluated_at="2026-08-22T00:05:00Z",
    ).review_record
    assert previous is not None and result.candidate is not None and result.lineage is not None
    crossed = replace(
        previous, context_sha256="sha256:" + "8" * 64,
        commentary_plan_sha256="sha256:" + "9" * 64,
        proposal_sha256="sha256:" + "a" * 64, review_sha256="",
    )
    crossed_current = CurrentHumanReviewSnapshot(
        result.candidate.candidate_id, result.candidate, result.lineage,
        current.context, current.plan, crossed.review_revision, crossed.review_sha256,
    )
    result = admit_human_review(
        authority_record=_authority(
            crossed_current, decided_at="2026-08-22T00:05:30Z",
            confirmation_sha256="sha256:" + "4" * 64,
        ), current=crossed_current, previous_review=crossed,
        evaluated_at="2026-08-22T00:06:00Z",
    )
    assert result.error_codes == ("PREVIOUS_REVIEW_CROSSING",)


def test_runtime_rejects_nonreserved_candidate_identity_like_schema() -> None:
    _, _, _, current = _snapshot()
    authority = _authority(current, root_candidate_id=generate_id(IdKind.CANDIDATE))
    with pytest.raises(ValueError, match="reserved"):
        admit_reasoning_human_review_authority_record(authority)


@pytest.mark.parametrize(("field", "value"), [
    ("confirmation_ref", "human-confirmation://operator/sk-proj-secret"),
    ("confirmation_ref", "human-confirmation://dbd-review/John-Doe"),
    ("authority_evidence_ref", "human-evidence://operator/C:/Users/Alice/token.txt"),
    ("authority_evidence_ref", "human-evidence://dbd-review/sha256/ghp_secret"),
])
def test_authority_refs_are_opaque_positive_grammar_only(field: str, value: str) -> None:
    _, _, _, current = _snapshot()
    authority = _authority(current, **{field: value})
    with pytest.raises(ValueError, match="canonical body-free"):
        admit_reasoning_human_review_authority_record(authority)


def test_use_time_readmission_rejects_mutated_current_and_previous_objects() -> None:
    _, _, result, current = _snapshot()
    authority = _authority(current)
    original_match = current.leaf_lineage.match_id
    object.__setattr__(current.leaf_lineage, "match_id", "MATCH-" + "0" * 26)
    mutated_current = admit_human_review(
        authority_record=authority, current=current, previous_review=None,
        evaluated_at="2026-08-22T00:05:00Z",
    )
    assert mutated_current.error_codes == ("CURRENT_SNAPSHOT_INVALID",)
    object.__setattr__(current.leaf_lineage, "match_id", original_match)

    previous = admit_human_review(
        authority_record=_authority(current), current=current, previous_review=None,
        evaluated_at="2026-08-22T00:05:00Z",
    ).review_record
    assert previous is not None and result.candidate is not None and result.lineage is not None
    object.__setattr__(previous, "review_revision", 8)
    forged_head = CurrentHumanReviewSnapshot(
        result.candidate.candidate_id, result.candidate, result.lineage,
        current.context, current.plan, 8, previous.review_sha256,
    )
    forged_previous = admit_human_review(
        authority_record=_authority(
            forged_head, decided_at="2026-08-22T00:05:30Z",
            confirmation_sha256="sha256:" + "4" * 64,
        ), current=forged_head, previous_review=previous,
        evaluated_at="2026-08-22T00:06:00Z",
    )
    assert forged_previous.error_codes == ("PREVIOUS_REVIEW_INVALID",)


def test_schema_mirror_runtime_conformance_and_unknown_fields() -> None:
    canonical = ROOT / "schemas" / "dbd-reasoning-human-review.schema.json"
    mirror = ROOT / "src" / "ai_video_production" / "schema_resources" / "dbd-reasoning-human-review.schema.json"
    assert canonical.read_bytes() == mirror.read_bytes()
    schema = json.loads(canonical.read_text("utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    _, _, _, current = _snapshot()
    authority = _authority(current)
    review = admit_human_review(
        authority_record=authority, current=current, previous_review=None,
        evaluated_at="2026-08-22T00:05:00Z",
    ).review_record
    assert review is not None
    assert list(validator.iter_errors(authority)) == []
    assert list(validator.iter_errors(review.to_dict())) == []
    assert admit_reasoning_human_review_record(review.to_dict()) == review
    extra = dict(authority, approved=True)
    assert list(validator.iter_errors(extra))
    with pytest.raises(ValueError, match="unknown"):
        admit_reasoning_human_review_authority_record(extra)
    review_extra = dict(review.to_dict(), exportable=True)
    with pytest.raises(ValueError, match="unknown"):
        admit_reasoning_human_review_record(review_extra)
    review_tamper = dict(review.to_dict(), context_sha256="sha256:" + "0" * 64)
    with pytest.raises(ValueError, match="sha256"):
        admit_reasoning_human_review_record(review_tamper)


def test_c1_has_no_authority_minter_store_io_or_export_effect(tmp_path: Path) -> None:
    parameters = tuple(inspect.signature(admit_human_review).parameters)
    assert parameters == ("authority_record", "current", "previous_review", "evaluated_at")
    source = (ROOT / "src" / "ai_video_production" / "dbd_reasoning_human_review.py").read_text("utf-8")
    assert "def create_authority" not in source and "CommentaryCandidateStore" not in source
    assert "sqlite" not in source.casefold() and "open(" not in source and "provider" not in source.casefold()
    context, plan, composed, current = _snapshot()
    assert admit_human_review(
        authority_record=_authority(current), current=current, previous_review=None,
        evaluated_at="2026-08-22T00:05:00Z",
    ).passed
    store = CommentaryCandidateStore(tmp_path / "review-inert.sqlite3")
    assert composed.candidate is not None and composed.lineage is not None
    store.append_reasoning_bundle(composed.candidate, composed.lineage)
    assert store.export_jsonl(tmp_path / "out.jsonl", match_id=plan.match_id).read_text("utf-8") == ""


def test_persisted_review_contains_no_commentary_body_credentials_or_reviewer_pii() -> None:
    _, _, _, current = _snapshot()
    authority = _authority(current)
    review = admit_human_review(
        authority_record=authority, current=current, previous_review=None,
        evaluated_at="2026-08-22T00:05:00Z",
    ).review_record
    assert review is not None
    encoded = json.dumps(review.to_dict(), ensure_ascii=False).casefold()
    assert current.leaf_candidate.draft.text not in encoded
    assert all(term not in encoded for term in ("credential", "password", "api_key", "reviewer_ref", "raw_output"))
