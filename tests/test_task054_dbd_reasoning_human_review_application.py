"""Focused TASK-054 R2D-C2 Store v3 and Human review application tests."""
from __future__ import annotations

import inspect
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from ai_video_production.dbd_reasoning_candidate_lineage import DbDReasoningCandidateComposer
from ai_video_production.dbd_reasoning_human_review import CurrentHumanReviewSnapshot
from ai_video_production.dbd_reasoning_human_review_application import (
    DbDReasoningHumanReviewApplication, HumanReviewHeadExpectation,
)
from ai_video_production.game_commentary import CommentaryCandidateStore
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from test_task054_dbd_reasoning_candidate_lineage import _raw
from test_task054_dbd_reasoning_human_review import _authority
from test_task054_dbd_reasoning_policy_admission import _inputs


class AuthorityResolver:
    def __init__(self, record): self.record = record
    def resolve(self, confirmation_ref): return self.record


class CurrentResolver:
    def __init__(self, current): self.current = current
    def resolve(self, candidate_id): return self.current


class FailingResolver:
    def resolve(self, value): raise RuntimeError("secret provider detail")


def _setup(tmp_path):
    context, plan = _inputs()
    composed = DbDReasoningCandidateComposer().create(raw_output=_raw(context), context=context, plan=plan)
    assert composed.candidate is not None and composed.lineage is not None
    current = CurrentHumanReviewSnapshot(composed.candidate.candidate_id, composed.candidate, composed.lineage, context, plan, 0, None)
    store = CommentaryCandidateStore(tmp_path / "reviews.sqlite3")
    store.append_reasoning_bundle(composed.candidate, composed.lineage)
    return context, plan, composed, current, store


def test_fresh_store_v3_and_approve_is_application_only_and_export_gated(tmp_path) -> None:
    _, plan, composed, current, store = _setup(tmp_path)
    with sqlite3.connect(store.path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 3
    assert store.export_jsonl(tmp_path / "before.jsonl", match_id=plan.match_id).read_text("utf-8") == ""
    authority = _authority(current)
    app = DbDReasoningHumanReviewApplication(
        store=store, authority_resolver=AuthorityResolver(authority),
        current_snapshot_resolver=CurrentResolver(current), clock=lambda: "2026-08-22T00:05:00Z",
    )
    result = app.apply_review(
        candidate_id=composed.candidate.candidate_id,
        confirmation_ref=authority["confirmation_ref"], expected_head=HumanReviewHeadExpectation(0, None),
    )
    assert result.status == "APPENDED"
    assert store.get_reasoning_human_review_head(composed.candidate.candidate_id) == result.review.to_dict()
    assert len(store.list_for_event(plan.event_id, validated_only=True)) == 1
    assert len(store.export_jsonl(tmp_path / "approved.jsonl", match_id=plan.match_id).read_text("utf-8").splitlines()) == 1


def test_exact_retry_is_idempotent_and_new_confirmation_reject_revokes_export(tmp_path) -> None:
    context, plan, composed, current, store = _setup(tmp_path)
    resolver = CurrentResolver(current)
    authority_resolver = AuthorityResolver(_authority(current))
    app = DbDReasoningHumanReviewApplication(
        store=store, authority_resolver=authority_resolver,
        current_snapshot_resolver=resolver, clock=lambda: "2026-08-22T00:05:00Z",
    )
    first = app.apply_review(candidate_id=composed.candidate.candidate_id, confirmation_ref=authority_resolver.record["confirmation_ref"], expected_head=HumanReviewHeadExpectation(0, None))
    retry = app.apply_review(candidate_id=composed.candidate.candidate_id, confirmation_ref=authority_resolver.record["confirmation_ref"], expected_head=HumanReviewHeadExpectation(0, None))
    assert retry.status == "IDEMPOTENT_EXISTING" and retry.review == first.review

    current2 = CurrentHumanReviewSnapshot(composed.candidate.candidate_id, composed.candidate, composed.lineage, context, plan, 1, first.review.review_sha256)
    resolver.current = current2
    authority_resolver.record = _authority(
        current2, decision="REJECT", confirmation_ref="human-confirmation://dbd-review/01ARZ3NDEKTSV4RRFFQ69G5FAW",
        confirmation_sha256="sha256:" + "4" * 64, decided_at="2026-08-22T00:04:30Z",
    )
    second = app.apply_review(candidate_id=composed.candidate.candidate_id, confirmation_ref=authority_resolver.record["confirmation_ref"], expected_head=HumanReviewHeadExpectation(1, first.review.review_sha256))
    assert second.review.review_revision == 2 and second.review.decision.value == "REJECT"
    assert store.export_jsonl(tmp_path / "rejected.jsonl", match_id=plan.match_id).read_text("utf-8") == ""


def test_stale_head_crossing_ref_and_raw_review_bypass_fail_closed(tmp_path) -> None:
    _, _, composed, current, store = _setup(tmp_path)
    authority = _authority(current)
    app = DbDReasoningHumanReviewApplication(store=store, authority_resolver=AuthorityResolver(authority), current_snapshot_resolver=CurrentResolver(current), clock=lambda: "2026-08-22T00:05:00Z")
    with pytest.raises(Exception, match="head"):
        app.apply_review(candidate_id=composed.candidate.candidate_id, confirmation_ref=authority["confirmation_ref"], expected_head=HumanReviewHeadExpectation(1, "sha256:" + "9" * 64))
    with pytest.raises(ValueError, match="requested"):
        app.apply_review(candidate_id=composed.candidate.candidate_id, confirmation_ref="human-confirmation://dbd-review/01ARZ3NDEKTSV4RRFFQ69G5FAW", expected_head=HumanReviewHeadExpectation(0, None))
    assert "append_reasoning_human_review" not in dir(store)
    with pytest.raises(TypeError):
        store._append_resolved_human_review(authority=None, current=current, expected_head=HumanReviewHeadExpectation(0, None), evaluated_at="2026-08-22T00:05:00Z")
    with pytest.raises(Exception, match="registration"):
        store._configure_reasoning_review_current_resolver(object(), CurrentResolver(current))
    assert tuple(inspect.signature(DbDReasoningHumanReviewApplication.apply_review).parameters) == ("self", "candidate_id", "confirmation_ref", "expected_head")


def test_review_payload_or_redundant_column_tamper_is_detected(tmp_path) -> None:
    _, _, composed, current, store = _setup(tmp_path)
    authority = _authority(current)
    app = DbDReasoningHumanReviewApplication(store=store, authority_resolver=AuthorityResolver(authority), current_snapshot_resolver=CurrentResolver(current), clock=lambda: "2026-08-22T00:05:00Z")
    review = app.apply_review(candidate_id=composed.candidate.candidate_id, confirmation_ref=authority["confirmation_ref"], expected_head=HumanReviewHeadExpectation(0, None)).review
    with sqlite3.connect(store.path) as conn:
        conn.execute("UPDATE dbd_reasoning_human_reviews SET context_sha256=?", ("sha256:" + "0" * 64,))
    with pytest.raises(Exception, match="review is invalid"):
        store.get_reasoning_human_review(review.review_sha256)

    _, _, composed2, current2, crossed_store = _setup(tmp_path / "crossed")
    authority2 = _authority(current2)
    app2 = DbDReasoningHumanReviewApplication(store=crossed_store, authority_resolver=AuthorityResolver(authority2), current_snapshot_resolver=CurrentResolver(current2), clock=lambda: "2026-08-22T00:05:00Z")
    admitted2 = app2.apply_review(candidate_id=composed2.candidate.candidate_id, confirmation_ref=authority2["confirmation_ref"], expected_head=HumanReviewHeadExpectation(0, None)).review
    with sqlite3.connect(crossed_store.path) as conn:
        payload = json.loads(conn.execute("SELECT payload_json FROM dbd_reasoning_human_reviews").fetchone()[0])
        payload["proposal_sha256"] = "sha256:" + "a" * 64
        body = {key: value for key, value in payload.items() if key != "review_sha256"}
        payload["review_sha256"] = sha256_bytes(canonical_json_bytes(body))
        text = canonical_json_bytes(payload).decode("utf-8")
        conn.execute("UPDATE dbd_reasoning_human_reviews SET review_sha256=?,proposal_sha256=?,payload_json=?,payload_sha256=?", (payload["review_sha256"], payload["proposal_sha256"], text, payload["review_sha256"]))
    with pytest.raises(Exception, match="review is invalid"):
        crossed_store.get_reasoning_human_review(payload["review_sha256"])


def test_v2_migrates_without_rewriting_existing_payload_bytes(tmp_path) -> None:
    _, _, composed, _, store = _setup(tmp_path)
    with sqlite3.connect(store.path) as conn:
        candidate_before = conn.execute("SELECT payload_json FROM commentary_candidates").fetchone()[0]
        lineage_before = conn.execute("SELECT payload_json FROM dbd_reasoning_candidate_lineage").fetchone()[0]
        conn.execute("DROP TABLE dbd_reasoning_human_reviews")
        conn.execute("PRAGMA user_version=2")
    migrated = CommentaryCandidateStore(store.path)
    with sqlite3.connect(migrated.path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 3
        assert conn.execute("SELECT payload_json FROM commentary_candidates").fetchone()[0] == candidate_before
        assert conn.execute("SELECT payload_json FROM dbd_reasoning_candidate_lineage").fetchone()[0] == lineage_before


def test_v3_rejects_cascade_or_nonexact_review_foreign_key(tmp_path) -> None:
    path = tmp_path / "cascade-v3.sqlite3"
    CommentaryCandidateStore(path)
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TABLE dbd_reasoning_human_reviews")
        conn.execute("CREATE TABLE dbd_reasoning_human_reviews(review_sha256 TEXT PRIMARY KEY,root_candidate_id TEXT NOT NULL REFERENCES dbd_reasoning_candidate_lineage(candidate_id),leaf_candidate_id TEXT NOT NULL REFERENCES dbd_reasoning_candidate_lineage(candidate_id),leaf_candidate_sha256 TEXT NOT NULL,leaf_lineage_sha256 TEXT NOT NULL,match_id TEXT NOT NULL,event_id TEXT NOT NULL,event_revision INTEGER NOT NULL,context_sha256 TEXT NOT NULL,commentary_plan_sha256 TEXT NOT NULL,proposal_sha256 TEXT NOT NULL,review_revision INTEGER NOT NULL,previous_review_sha256 TEXT,decision TEXT NOT NULL,authority_binding_sha256 TEXT NOT NULL,confirmation_sha256 TEXT NOT NULL UNIQUE,reviewed_at TEXT NOT NULL,payload_json TEXT NOT NULL,payload_sha256 TEXT NOT NULL,UNIQUE(root_candidate_id,review_revision),UNIQUE(root_candidate_id,previous_review_sha256),UNIQUE(root_candidate_id,review_sha256),FOREIGN KEY(root_candidate_id,previous_review_sha256) REFERENCES dbd_reasoning_human_reviews(root_candidate_id,review_sha256) ON DELETE CASCADE)")
        conn.execute("CREATE INDEX dbd_reasoning_review_root_lookup ON dbd_reasoning_human_reviews(root_candidate_id,review_revision DESC,review_sha256)")
        conn.execute("CREATE INDEX dbd_reasoning_review_event_lookup ON dbd_reasoning_human_reviews(event_id,event_revision,root_candidate_id)")
    with pytest.raises(Exception, match="foreign keys"):
        CommentaryCandidateStore(path)


def test_resolver_and_clock_failures_are_body_free_and_current_drift_rejects(tmp_path) -> None:
    _, _, composed, current, store = _setup(tmp_path)
    authority = _authority(current)
    with pytest.raises(Exception, match="authority could not be resolved") as caught:
        DbDReasoningHumanReviewApplication(store=store, authority_resolver=FailingResolver(), current_snapshot_resolver=CurrentResolver(current), clock=lambda: "2026-08-22T00:05:00Z").apply_review(candidate_id=composed.candidate.candidate_id, confirmation_ref=authority["confirmation_ref"], expected_head=HumanReviewHeadExpectation(0, None))
    assert "secret provider detail" not in str(caught.value)

    other_store = CommentaryCandidateStore(tmp_path / "current-fail.sqlite3")
    other_store.append_reasoning_bundle(composed.candidate, composed.lineage)
    with pytest.raises(Exception, match="Current reasoning review snapshot"):
        DbDReasoningHumanReviewApplication(store=other_store, authority_resolver=AuthorityResolver(authority), current_snapshot_resolver=FailingResolver(), clock=lambda: "2026-08-22T00:05:00Z").apply_review(candidate_id=composed.candidate.candidate_id, confirmation_ref=authority["confirmation_ref"], expected_head=HumanReviewHeadExpectation(0, None))

    clock_store = CommentaryCandidateStore(tmp_path / "clock-fail.sqlite3")
    clock_store.append_reasoning_bundle(composed.candidate, composed.lineage)
    with pytest.raises(Exception, match="clock is unavailable"):
        DbDReasoningHumanReviewApplication(store=clock_store, authority_resolver=AuthorityResolver(authority), current_snapshot_resolver=CurrentResolver(current), clock=lambda: (_ for _ in ()).throw(RuntimeError("clock secret"))).apply_review(candidate_id=composed.candidate.candidate_id, confirmation_ref=authority["confirmation_ref"], expected_head=HumanReviewHeadExpectation(0, None))


def test_concurrent_different_confirmations_allow_one_head_append(tmp_path) -> None:
    _, _, composed, current, store = _setup(tmp_path)
    a = _authority(current)
    b = _authority(current, confirmation_ref="human-confirmation://dbd-review/01ARZ3NDEKTSV4RRFFQ69G5FAW", confirmation_sha256="sha256:" + "4" * 64)
    class MultiAuthority:
        def resolve(self, ref): return a if ref == a["confirmation_ref"] else b
    app = DbDReasoningHumanReviewApplication(store=store, authority_resolver=MultiAuthority(), current_snapshot_resolver=CurrentResolver(current), clock=lambda: "2026-08-22T00:05:00Z")
    def run(ref):
        try:
            return app.apply_review(candidate_id=composed.candidate.candidate_id, confirmation_ref=ref, expected_head=HumanReviewHeadExpectation(0, None)).status
        except Exception as exc:
            return getattr(exc, "code", type(exc).__name__)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(run, (a["confirmation_ref"], b["confirmation_ref"])))
    assert results.count("APPENDED") == 1 and results.count("ERR_DBD_REVIEW_HEAD_CONFLICT") == 1
    assert len(store.list_reasoning_human_reviews(composed.candidate.candidate_id)) == 1


def test_v2_to_v3_failure_rolls_back_version_and_alien_table(tmp_path) -> None:
    _, _, _, _, store = _setup(tmp_path)
    with sqlite3.connect(store.path) as conn:
        conn.execute("DROP TABLE dbd_reasoning_human_reviews")
        conn.execute("CREATE TABLE dbd_reasoning_human_reviews(alien TEXT)")
        conn.execute("PRAGMA user_version=2")
    with pytest.raises(Exception):
        CommentaryCandidateStore(store.path)
    with sqlite3.connect(store.path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
        assert [row[1] for row in conn.execute("PRAGMA table_info(dbd_reasoning_human_reviews)")] == ["alien"]


def test_newer_v4_store_is_rejected_without_mutation(tmp_path) -> None:
    path = tmp_path / "newer.sqlite3"
    CommentaryCandidateStore(path)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA user_version=4")
    with pytest.raises(Exception, match="newer schema"):
        CommentaryCandidateStore(path)
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 4


def test_fresh_v3_validation_failure_rolls_back_all_tables(tmp_path, monkeypatch) -> None:
    path = tmp_path / "fresh-failure.sqlite3"
    def fail(conn): raise sqlite3.DatabaseError("injected validation failure")
    monkeypatch.setattr(CommentaryCandidateStore, "_validate_v3_schema", staticmethod(fail))
    with pytest.raises(Exception, match="corrupt or unreadable"):
        CommentaryCandidateStore(path)
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 0
        assert conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []


def test_rehashed_confirmation_content_conflict_is_not_idempotent(tmp_path) -> None:
    _, _, composed, current, store = _setup(tmp_path)
    authority = _authority(current)
    app = DbDReasoningHumanReviewApplication(store=store, authority_resolver=AuthorityResolver(authority), current_snapshot_resolver=CurrentResolver(current), clock=lambda: "2026-08-22T00:05:00Z")
    app.apply_review(candidate_id=composed.candidate.candidate_id, confirmation_ref=authority["confirmation_ref"], expected_head=HumanReviewHeadExpectation(0, None))
    with sqlite3.connect(store.path) as conn:
        payload = json.loads(conn.execute("SELECT payload_json FROM dbd_reasoning_human_reviews").fetchone()[0])
        payload["decision"], payload["reason_codes"] = "REJECT", ["FORGED_DECISION"]
        body = {key: value for key, value in payload.items() if key != "review_sha256"}
        payload["review_sha256"] = sha256_bytes(canonical_json_bytes(body))
        text = canonical_json_bytes(payload).decode("utf-8")
        conn.execute("UPDATE dbd_reasoning_human_reviews SET review_sha256=?,decision=?,payload_json=?,payload_sha256=?", (payload["review_sha256"], "REJECT", text, payload["review_sha256"]))
    with pytest.raises(Exception, match="already consumed"):
        app.apply_review(candidate_id=composed.candidate.candidate_id, confirmation_ref=authority["confirmation_ref"], expected_head=HumanReviewHeadExpectation(0, None))


def test_latest_revise_removes_previously_approved_candidate(tmp_path) -> None:
    context, plan, composed, current, store = _setup(tmp_path)
    authority_resolver = AuthorityResolver(_authority(current))
    current_resolver = CurrentResolver(current)
    app = DbDReasoningHumanReviewApplication(store=store, authority_resolver=authority_resolver, current_snapshot_resolver=current_resolver, clock=lambda: "2026-08-22T00:05:00Z")
    first = app.apply_review(candidate_id=composed.candidate.candidate_id, confirmation_ref=authority_resolver.record["confirmation_ref"], expected_head=HumanReviewHeadExpectation(0, None)).review
    assert len(store.list_for_event(plan.event_id, validated_only=True)) == 1
    current_resolver.current = CurrentHumanReviewSnapshot(composed.candidate.candidate_id, composed.candidate, composed.lineage, context, plan, 1, first.review_sha256)
    authority_resolver.record = _authority(current_resolver.current, decision="REVISE", confirmation_ref="human-confirmation://dbd-review/01ARZ3NDEKTSV4RRFFQ69G5FAW", confirmation_sha256="sha256:" + "4" * 64, decided_at="2026-08-22T00:04:30Z")
    app.apply_review(candidate_id=composed.candidate.candidate_id, confirmation_ref=authority_resolver.record["confirmation_ref"], expected_head=HumanReviewHeadExpectation(1, first.review_sha256))
    assert store.list_for_event(plan.event_id, validated_only=True) == ()
