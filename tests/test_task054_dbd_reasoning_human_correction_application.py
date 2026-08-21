"""Focused TASK-054 R2D-C3 Human correction child-admission tests."""
from __future__ import annotations

from dataclasses import replace
import inspect
import json
from pathlib import Path
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.dbd_reasoning_candidate_lineage import DbDReasoningCandidateComposer
from ai_video_production.dbd_reasoning_human_correction_application import (
    DbDReasoningHumanCorrectionApplication, HumanCorrectionAppendResult, ResolvedHumanCorrectionSubmission,
    admit_reasoning_human_correction_submission,
)
from ai_video_production.dbd_reasoning_human_review import CurrentHumanReviewSnapshot
from ai_video_production.dbd_reasoning_human_review_application import (
    DbDReasoningHumanReviewApplication, HumanReviewHeadExpectation,
)
from ai_video_production.game_commentary import CommentaryCandidateStore
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from test_task054_dbd_reasoning_candidate_lineage import _raw
from test_task054_dbd_reasoning_human_review import _authority
from test_task054_dbd_reasoning_policy_admission import _inputs


ROOT = Path(__file__).resolve().parents[1]


class CurrentResolver:
    def __init__(self, current): self.current = current
    def resolve(self, candidate_id): return self.current


class Resolver:
    def __init__(self, value): self.value = value
    def resolve(self, opaque_ref): return self.value


def _submission(current, *, child_id="CAND-R2D00000000000000000000000", text="窓越え、しなやかに決めました。"):
    parent, lineage = current.leaf_candidate.to_dict(), current.leaf_lineage.to_dict()
    raw = _raw(current.context, text=text)
    record = {
        "schema_version": "1.0.0", "record_kind": "DBD_REASONING_HUMAN_CORRECTION_SUBMISSION",
        "correction_ref": "human-correction://dbd-review/01ARZ3NDEKTSV4RRFFQ69G5FAV",
        "reviewer_kind": "HUMAN", "one_shot": True,
        "submitted_at": "2026-08-22T00:06:00Z", "expires_at": "2026-08-22T00:20:00Z",
        "parent_candidate_id": current.root_candidate_id,
        "parent_candidate_sha256": parent["commentary_candidate_sha256"],
        "parent_lineage_sha256": lineage["lineage_sha256"],
        "correction_review_sha256": current.review_head_sha256,
        "correction_request_sha256": "sha256:" + "3" * 64,
        "context_sha256": current.context.to_dict()["context_sha256"],
        "commentary_plan_sha256": current.plan.to_dict()["commentary_plan_sha256"],
        "proposal_sha256": lineage["proposal"]["proposal_sha256"],
        "child_candidate_id": child_id, "child_created_at": "2026-08-22T00:06:00Z",
        "edited_output_sha256": sha256_bytes(raw),
        "evidence_ref": "human-evidence://dbd-review/sha256/" + "7" * 64,
        "evidence_sha256": "sha256:" + "7" * 64, "binding_sha256": "",
    }
    record["binding_sha256"] = sha256_bytes(canonical_json_bytes({key: value for key, value in record.items() if key != "binding_sha256"}))
    return record, raw


def _setup(tmp_path):
    context, plan = _inputs()
    root = DbDReasoningCandidateComposer().create(raw_output=_raw(context), context=context, plan=plan)
    assert root.candidate and root.lineage
    store = CommentaryCandidateStore(tmp_path / "correction.sqlite3")
    store.append_reasoning_bundle(root.candidate, root.lineage)
    current = CurrentHumanReviewSnapshot(root.candidate.candidate_id, root.candidate, root.lineage, context, plan, 0, None)
    resolver = CurrentResolver(current)
    revise = _authority(current, decision="REVISE")
    review_app = DbDReasoningHumanReviewApplication(store=store, authority_resolver=Resolver(revise), current_snapshot_resolver=resolver, clock=lambda: "2026-08-22T00:05:00Z")
    review = review_app.apply_review(candidate_id=root.candidate.candidate_id, confirmation_ref=revise["confirmation_ref"], expected_head=HumanReviewHeadExpectation(0, None)).review
    resolver.current = CurrentHumanReviewSnapshot(root.candidate.candidate_id, root.candidate, root.lineage, context, plan, 1, review.review_sha256)
    record, raw = _submission(resolver.current)
    app = DbDReasoningHumanCorrectionApplication(store=store, correction_resolver=Resolver(ResolvedHumanCorrectionSubmission(admit_reasoning_human_correction_submission(record), raw)), current_snapshot_resolver=resolver, clock=lambda: "2026-08-22T00:06:30Z")
    return plan, root, review, resolver, store, app, record


def test_correction_creates_atomic_child_and_is_exactly_idempotent(tmp_path) -> None:
    plan, root, review, resolver, store, app, record = _setup(tmp_path)
    result = app.apply_correction(parent_candidate_id=root.candidate.candidate_id, correction_ref=record["correction_ref"], expected_review_head=HumanReviewHeadExpectation(1, review.review_sha256))
    assert result.status == "APPENDED"
    assert result.candidate.to_dict()["schema_version"] == "1.2.0"
    assert result.lineage.to_dict()["schema_version"] == "1.1.0"
    assert store.export_jsonl(tmp_path / "before-child-review.jsonl", match_id=plan.match_id).read_text("utf-8") == ""
    retry = app.apply_correction(parent_candidate_id=root.candidate.candidate_id, correction_ref=record["correction_ref"], expected_review_head=HumanReviewHeadExpectation(1, review.review_sha256))
    assert retry.status == "IDEMPOTENT_EXISTING"
    with sqlite3.connect(store.path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 3
        text = conn.execute("SELECT payload_json FROM commentary_candidates WHERE candidate_id=?", (result.candidate.candidate_id,)).fetchone()[0]
        assert "窓越え、しなやかに決めました。" in text and "edited_output" not in text


def test_correction_rejects_stale_or_non_revise_and_public_store_bypass(tmp_path) -> None:
    _, root, review, resolver, store, app, record = _setup(tmp_path)
    with pytest.raises(Exception, match="head"):
        app.apply_correction(parent_candidate_id=root.candidate.candidate_id, correction_ref=record["correction_ref"], expected_review_head=HumanReviewHeadExpectation(0, None))
    assert "append_resolved_human_correction" not in dir(store)
    with pytest.raises(TypeError):
        store._append_resolved_human_correction(token=None, submission=None, current=None, child_candidate=None, child_lineage=None, expected_review_head=None)
    assert tuple(inspect.signature(DbDReasoningHumanCorrectionApplication.apply_correction).parameters) == ("self", "parent_candidate_id", "correction_ref", "expected_review_head")


def test_child_requires_its_own_approve_and_later_reject_revokes_export(tmp_path) -> None:
    plan, root, review, resolver, store, correction_app, record = _setup(tmp_path)
    child = correction_app.apply_correction(parent_candidate_id=root.candidate.candidate_id, correction_ref=record["correction_ref"], expected_review_head=HumanReviewHeadExpectation(1, review.review_sha256))
    child_current = CurrentHumanReviewSnapshot(child.candidate.candidate_id, child.candidate, child.lineage, resolver.current.context, resolver.current.plan, 0, None)
    resolver.current = child_current
    approve = _authority(child_current, confirmation_ref="human-confirmation://dbd-review/01ARZ3NDEKTSV4RRFFQ69G5FAW", confirmation_sha256="sha256:" + "4" * 64)
    review_app = DbDReasoningHumanReviewApplication(store=store, authority_resolver=Resolver(approve), current_snapshot_resolver=resolver, clock=lambda: "2026-08-22T00:07:00Z")
    approved = review_app.apply_review(candidate_id=child.candidate.candidate_id, confirmation_ref=approve["confirmation_ref"], expected_head=HumanReviewHeadExpectation(0, None)).review
    lines = store.export_jsonl(tmp_path / "child-approved.jsonl", match_id=plan.match_id).read_text("utf-8").splitlines()
    assert len(lines) == 1 and child.candidate.candidate_id in lines[0] and root.candidate.candidate_id not in lines[0]
    resolver.current = CurrentHumanReviewSnapshot(child.candidate.candidate_id, child.candidate, child.lineage, child_current.context, child_current.plan, 1, approved.review_sha256)
    reject = _authority(resolver.current, decision="REJECT", confirmation_ref="human-confirmation://dbd-review/01ARZ3NDEKTSV4RRFFQ69G5FAX", confirmation_sha256="sha256:" + "5" * 64, decided_at="2026-08-22T00:08:00Z", expires_at="2026-08-22T00:20:00Z")
    reject_app = DbDReasoningHumanReviewApplication(store=store, authority_resolver=Resolver(reject), current_snapshot_resolver=resolver, clock=lambda: "2026-08-22T00:09:00Z")
    reject_app.apply_review(candidate_id=child.candidate.candidate_id, confirmation_ref=reject["confirmation_ref"], expected_head=HumanReviewHeadExpectation(1, approved.review_sha256))
    assert store.export_jsonl(tmp_path / "child-rejected.jsonl", match_id=plan.match_id).read_text("utf-8") == ""


def test_correction_lineage_schema_mirrors_and_root_contract_stays_unchanged(tmp_path) -> None:
    _, root, review, _, _, app, record = _setup(tmp_path)
    child = app.apply_correction(parent_candidate_id=root.candidate.candidate_id, correction_ref=record["correction_ref"], expected_review_head=HumanReviewHeadExpectation(1, review.review_sha256))
    canonical = json.loads((ROOT / "schemas" / "dbd-reasoning-candidate-lineage.schema.json").read_text("utf-8"))
    mirror = json.loads((ROOT / "src" / "ai_video_production" / "schema_resources" / "dbd-reasoning-candidate-lineage.schema.json").read_text("utf-8"))
    assert canonical == mirror
    assert not list(Draft202012Validator(canonical).iter_errors(child.lineage.to_dict()))
    assert root.candidate.to_dict()["schema_version"] == "1.1.0"
    assert root.lineage.to_dict()["schema_version"] == "1.0.0"
    root_payload = root.lineage.to_dict()
    assert "correction_submission_ref" not in root_payload and "correction_submission_binding_sha256" not in root_payload
    assert len(root_payload) == 20
    root_body = {key: value for key, value in root_payload.items() if key != "lineage_sha256"}
    assert root_payload["lineage_sha256"] == sha256_bytes(canonical_json_bytes(root_body))
    assert not list(Draft202012Validator(canonical).iter_errors(root_payload))
    assert list(Draft202012Validator(canonical).iter_errors(dict(root_payload, correction_submission_ref=None)))
    assert list(Draft202012Validator(canonical).iter_errors({key: value for key, value in child.lineage.to_dict().items() if key != "correction_submission_ref"}))


def test_submission_is_exactly_readmitted_and_schema_mirrors(tmp_path) -> None:
    _, _, review, resolver, _, _, _ = _setup(tmp_path)
    record, raw = _submission(resolver.current)
    admitted = admit_reasoning_human_correction_submission(record)
    assert admitted.to_dict() == record
    blank = dict(record, binding_sha256="")
    with pytest.raises(ValueError, match="exact"):
        admit_reasoning_human_correction_submission(blank)
    canonical = json.loads((ROOT / "schemas" / "dbd-reasoning-human-correction-submission.schema.json").read_text("utf-8"))
    mirror = json.loads((ROOT / "src" / "ai_video_production" / "schema_resources" / "dbd-reasoning-human-correction-submission.schema.json").read_text("utf-8"))
    assert canonical == mirror and not list(Draft202012Validator(canonical).iter_errors(record))
    assert sha256_bytes(raw) == admitted.edited_output_sha256 and review.review_sha256 == admitted.correction_review_sha256


def test_stored_legacy_root_lineage_reads_and_exports_unchanged(tmp_path) -> None:
    context, plan = _inputs()
    root = DbDReasoningCandidateComposer().create(raw_output=_raw(context), context=context, plan=plan)
    assert root.candidate and root.lineage
    original = root.lineage.to_dict()
    store = CommentaryCandidateStore(tmp_path / "legacy-root.sqlite3")
    store.append_reasoning_bundle(root.candidate, root.lineage)
    assert store.get_reasoning_lineage(root.candidate.candidate_id) == original
    current = CurrentHumanReviewSnapshot(root.candidate.candidate_id, root.candidate, root.lineage, context, plan, 0, None)
    authority = _authority(current)
    DbDReasoningHumanReviewApplication(store=store, authority_resolver=Resolver(authority), current_snapshot_resolver=CurrentResolver(current), clock=lambda: "2026-08-22T00:05:00Z").apply_review(candidate_id=root.candidate.candidate_id, confirmation_ref=authority["confirmation_ref"], expected_head=HumanReviewHeadExpectation(0, None))
    assert store.export_jsonl(tmp_path / "legacy-root.jsonl", match_id=plan.match_id).read_text("utf-8") == canonical_json_bytes(root.candidate.to_dict()).decode("utf-8") + "\n"


def test_result_and_lineage_forges_fail_closed(tmp_path) -> None:
    _, root, review, _, _, app, record = _setup(tmp_path)
    result = app.apply_correction(parent_candidate_id=root.candidate.candidate_id, correction_ref=record["correction_ref"], expected_review_head=HumanReviewHeadExpectation(1, review.review_sha256))
    with pytest.raises(ValueError, match="match"):
        replace(result, candidate=root.candidate)
    with pytest.raises(ValueError, match="correction"):
        replace(result.lineage, correction_submission_ref=None, lineage_sha256="")
    with pytest.raises(ValueError, match="canonical"):
        HumanCorrectionAppendResult("APPENDED", result.candidate, result.lineage, object())  # type: ignore[arg-type]


def test_result_rejects_raw_created_context_plan_and_child_crossings(tmp_path) -> None:
    _, root, review, _, _, app, record = _setup(tmp_path)
    result = app.apply_correction(parent_candidate_id=root.candidate.candidate_id, correction_ref=record["correction_ref"], expected_review_head=HumanReviewHeadExpectation(1, review.review_sha256))
    forged_raw = replace(result.lineage, raw_output_sha256="sha256:" + "8" * 64, lineage_sha256="")
    with pytest.raises(ValueError, match="crosses"):
        HumanCorrectionAppendResult(result.status, result.candidate, forged_raw, result.submission)
    forged_candidate = replace(result.candidate, created_at="2026-08-22T00:06:01Z")
    forged_created = replace(result.lineage, commentary_candidate_sha256=forged_candidate.to_dict()["commentary_candidate_sha256"], lineage_sha256="")
    with pytest.raises(ValueError, match="crosses"):
        HumanCorrectionAppendResult(result.status, forged_candidate, forged_created, result.submission)
    for field_name in ("context_sha256", "commentary_plan_sha256"):
        with pytest.raises(ValueError):
            forged = replace(result.lineage, **{field_name: "sha256:" + "9" * 64, "lineage_sha256": ""})
            HumanCorrectionAppendResult(result.status, result.candidate, forged, result.submission)
    with pytest.raises(ValueError):
        forged_proposal = replace(result.lineage, proposal=root.lineage.proposal, lineage_sha256="")
        HumanCorrectionAppendResult(result.status, result.candidate, forged_proposal, result.submission)


@pytest.mark.parametrize(("raw_factory", "expected"), [
    (lambda context: b"{}", "PROPOSAL_SHAPE_INVALID"),
    (lambda context: _raw(context, citation="evidence://game/GEVD-00000000000000000000000000"), "REFERENCE_NOT_IN_CONTEXT"),
    (lambda context: _raw(context, text="api_key=secret"), "DLP_POLICY_REJECTED"),
])
def test_r2a_r2b_r2c_failures_leave_no_correction_rows(tmp_path, raw_factory, expected) -> None:
    _, root, review, resolver, store, app, record = _setup(tmp_path)
    bad_raw = raw_factory(resolver.current.context)
    bad = dict(record, edited_output_sha256=sha256_bytes(bad_raw), binding_sha256="")
    bad["binding_sha256"] = sha256_bytes(canonical_json_bytes({key: value for key, value in bad.items() if key != "binding_sha256"}))
    app._resolver = Resolver(ResolvedHumanCorrectionSubmission(admit_reasoning_human_correction_submission(bad), bad_raw))
    with pytest.raises(Exception, match=expected):
        app.apply_correction(parent_candidate_id=root.candidate.candidate_id, correction_ref=bad["correction_ref"], expected_review_head=HumanReviewHeadExpectation(1, review.review_sha256))
    with sqlite3.connect(store.path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM dbd_reasoning_candidate_lineage").fetchone()[0] == 1


def test_distinct_corrections_race_to_one_child_branch(tmp_path) -> None:
    _, root, review, resolver, store, app, record = _setup(tmp_path)
    alternate = dict(record, correction_ref="human-correction://dbd-review/01ARZ3NDEKTSV4RRFFQ69G5FAW", child_candidate_id="CAND-R2D11111111111111111111111", binding_sha256="")
    alternate["binding_sha256"] = sha256_bytes(canonical_json_bytes({key: value for key, value in alternate.items() if key != "binding_sha256"}))
    records = {
        record["correction_ref"]: ResolvedHumanCorrectionSubmission(admit_reasoning_human_correction_submission(record), _raw(resolver.current.context, text="窓越え、しなやかに決めました。")),
        alternate["correction_ref"]: ResolvedHumanCorrectionSubmission(admit_reasoning_human_correction_submission(alternate), _raw(resolver.current.context, text="窓越え、しなやかに決めました。")),
    }
    class MultiResolver:
        def resolve(self, value): return records[value]
    app._resolver = MultiResolver()
    def run(ref):
        try:
            return app.apply_correction(parent_candidate_id=root.candidate.candidate_id, correction_ref=ref, expected_review_head=HumanReviewHeadExpectation(1, review.review_sha256)).status
        except Exception as exc:
            return getattr(exc, "code", type(exc).__name__)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = tuple(pool.map(run, records))
    assert outcomes.count("APPENDED") == 1 and outcomes.count("ERR_DBD_CORRECTION_BRANCH_CONFLICT") == 1
    with sqlite3.connect(store.path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM dbd_reasoning_candidate_lineage").fetchone()[0] == 2


def test_post_insert_audit_failure_rolls_back_child_bundle(tmp_path, monkeypatch) -> None:
    _, root, review, _, store, app, record = _setup(tmp_path)
    original = store._audit_reasoning_lineage_rows
    calls = {"count": 0}
    def fail_after_insert(conn):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("injected post-insert audit failure")
        return original(conn)
    monkeypatch.setattr(store, "_audit_reasoning_lineage_rows", fail_after_insert)
    with pytest.raises(RuntimeError, match="post-insert"):
        app.apply_correction(parent_candidate_id=root.candidate.candidate_id, correction_ref=record["correction_ref"], expected_review_head=HumanReviewHeadExpectation(1, review.review_sha256))
    with sqlite3.connect(store.path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM commentary_candidates").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM dbd_reasoning_candidate_lineage").fetchone()[0] == 1


def test_grandchild_approval_exports_only_leaf_not_ancestors(tmp_path) -> None:
    plan, root, first_review, resolver, store, correction_app, first_record = _setup(tmp_path)
    child = correction_app.apply_correction(parent_candidate_id=root.candidate.candidate_id, correction_ref=first_record["correction_ref"], expected_review_head=HumanReviewHeadExpectation(1, first_review.review_sha256))
    child_current = CurrentHumanReviewSnapshot(child.candidate.candidate_id, child.candidate, child.lineage, resolver.current.context, resolver.current.plan, 0, None)
    resolver.current = child_current
    revise = _authority(child_current, decision="REVISE", confirmation_ref="human-confirmation://dbd-review/01ARZ3NDEKTSV4RRFFQ69G5FAW", confirmation_sha256="sha256:" + "4" * 64, decided_at="2026-08-22T00:07:00Z", expires_at="2026-08-22T00:20:00Z")
    review_app = DbDReasoningHumanReviewApplication(store=store, authority_resolver=Resolver(revise), current_snapshot_resolver=resolver, clock=lambda: "2026-08-22T00:07:30Z")
    child_revise = review_app.apply_review(candidate_id=child.candidate.candidate_id, confirmation_ref=revise["confirmation_ref"], expected_head=HumanReviewHeadExpectation(0, None)).review
    resolver.current = CurrentHumanReviewSnapshot(child.candidate.candidate_id, child.candidate, child.lineage, child_current.context, child_current.plan, 1, child_revise.review_sha256)
    second_record, second_raw = _submission(resolver.current, child_id="CAND-R2D22222222222222222222222", text="窓越え、しなやかに抜けました。")
    second_record.update(correction_ref="human-correction://dbd-review/01ARZ3NDEKTSV4RRFFQ69G5FAX", submitted_at="2026-08-22T00:08:00Z", expires_at="2026-08-22T00:20:00Z", binding_sha256="")
    second_record["binding_sha256"] = sha256_bytes(canonical_json_bytes({key: value for key, value in second_record.items() if key != "binding_sha256"}))
    correction_app._resolver = Resolver(ResolvedHumanCorrectionSubmission(admit_reasoning_human_correction_submission(second_record), second_raw))
    correction_app._clock = lambda: "2026-08-22T00:08:30Z"
    grandchild = correction_app.apply_correction(parent_candidate_id=child.candidate.candidate_id, correction_ref=second_record["correction_ref"], expected_review_head=HumanReviewHeadExpectation(1, child_revise.review_sha256))
    grand_current = CurrentHumanReviewSnapshot(grandchild.candidate.candidate_id, grandchild.candidate, grandchild.lineage, resolver.current.context, resolver.current.plan, 0, None)
    resolver.current = grand_current
    approve = _authority(grand_current, confirmation_ref="human-confirmation://dbd-review/01ARZ3NDEKTSV4RRFFQ69G5FAY", confirmation_sha256="sha256:" + "5" * 64, decided_at="2026-08-22T00:09:00Z", expires_at="2026-08-22T00:20:00Z")
    DbDReasoningHumanReviewApplication(store=store, authority_resolver=Resolver(approve), current_snapshot_resolver=resolver, clock=lambda: "2026-08-22T00:09:30Z").apply_review(candidate_id=grandchild.candidate.candidate_id, confirmation_ref=approve["confirmation_ref"], expected_head=HumanReviewHeadExpectation(0, None))
    lines = store.export_jsonl(tmp_path / "leaf.jsonl", match_id=plan.match_id).read_text("utf-8").splitlines()
    assert len(lines) == 1 and grandchild.candidate.candidate_id in lines[0]
    assert root.candidate.candidate_id not in lines[0] and child.candidate.candidate_id not in lines[0]
