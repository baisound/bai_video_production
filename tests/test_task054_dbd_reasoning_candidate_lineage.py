"""Focused TASK-054 R2D-A pure composition and lineage tests."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import inspect
import json
from pathlib import Path
import sqlite3

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.dbd_reasoning_candidate_lineage import (
    DbDReasoningCandidateComposer, DbDReasoningCandidateCreationResult,
    admit_reasoning_candidate_lineage_record,
)
from ai_video_production.game_commentary import CommentaryCandidate, CommentaryCandidateStore, FactValidationResult
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
    assert result.candidate.candidate_id.startswith("CAND-R2D")
    assert result.candidate.to_dict()["schema_version"] == "1.1.0"
    assert result.candidate.to_dict()["reasoning_origin"] == "TUNED_REASONING"
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


def test_serialized_lineage_is_exactly_readmitted_against_candidate_payload() -> None:
    context, plan = _inputs()
    result = DbDReasoningCandidateComposer().create(raw_output=_raw(context), context=context, plan=plan)
    assert result.candidate is not None and result.lineage is not None
    record = result.lineage.to_dict()
    candidate = result.candidate.to_dict()
    admitted = admit_reasoning_candidate_lineage_record(record, candidate_payload=candidate)
    assert admitted.to_dict() == record

    extra = dict(record, injected=True)
    with pytest.raises(ValueError, match="unknown"):
        admit_reasoning_candidate_lineage_record(extra, candidate_payload=candidate)
    changed = dict(record)
    changed["event_revision"] = 99
    with pytest.raises(ValueError):
        admit_reasoning_candidate_lineage_record(changed, candidate_payload=candidate)
    nested = json.loads(json.dumps(record))
    nested["policy_admission_receipt"]["passed"] = False
    with pytest.raises(ValueError):
        admit_reasoning_candidate_lineage_record(nested, candidate_payload=candidate)
    proposal = json.loads(json.dumps(record))
    proposal["proposal"]["commentary_text"] = "差替え"
    with pytest.raises(ValueError):
        admit_reasoning_candidate_lineage_record(proposal, candidate_payload=candidate)
    candidate_tamper = json.loads(json.dumps(candidate))
    candidate_tamper["draft"]["provider_ref"] = "provider://forged"
    with pytest.raises(ValueError):
        admit_reasoning_candidate_lineage_record(record, candidate_payload=candidate_tamper)
    bad_created = json.loads(json.dumps(candidate))
    bad_created["created_at"] = []
    bad_created_body = {key: value for key, value in bad_created.items() if key != "commentary_candidate_sha256"}
    bad_created["commentary_candidate_sha256"] = "sha256:" + sha256(json.dumps(bad_created_body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    with pytest.raises(ValueError, match="created_at"):
        admit_reasoning_candidate_lineage_record(record, candidate_payload=bad_created)
    bad_draft = json.loads(json.dumps(candidate))
    bad_draft["draft"]["schema_version"] = "9.9.9"
    draft_body = {key: value for key, value in bad_draft["draft"].items() if key != "commentary_draft_sha256"}
    bad_draft["draft"]["commentary_draft_sha256"] = "sha256:" + sha256(json.dumps(draft_body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    bad_draft_body = {key: value for key, value in bad_draft.items() if key != "commentary_candidate_sha256"}
    bad_draft["commentary_candidate_sha256"] = "sha256:" + sha256(json.dumps(bad_draft_body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    with pytest.raises(ValueError, match="draft"):
        admit_reasoning_candidate_lineage_record(record, candidate_payload=bad_draft)
    crossed = json.loads(json.dumps(candidate))
    crossed["plan"]["match_id"] = generate_id(IdKind.GAME_MATCH)
    plan_body = {key: value for key, value in crossed["plan"].items() if key != "commentary_plan_sha256"}
    crossed["plan"]["commentary_plan_sha256"] = "sha256:" + sha256(json.dumps(plan_body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    candidate_body = {key: value for key, value in crossed.items() if key != "commentary_candidate_sha256"}
    crossed["commentary_candidate_sha256"] = "sha256:" + sha256(json.dumps(candidate_body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    with pytest.raises(ValueError):
        admit_reasoning_candidate_lineage_record(record, candidate_payload=crossed)


def test_lineage_schema_mirror_and_runtime_conformance() -> None:
    canonical = ROOT / "schemas" / "dbd-reasoning-candidate-lineage.schema.json"
    mirror = ROOT / "src" / "ai_video_production" / "schema_resources" / "dbd-reasoning-candidate-lineage.schema.json"
    assert canonical.read_bytes() == mirror.read_bytes()
    schema = json.loads(canonical.read_text("utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    context, plan = _inputs()
    result = DbDReasoningCandidateComposer().create(raw_output=_raw(context), context=context, plan=plan)
    assert result.lineage is not None
    record = result.lineage.to_dict()
    assert list(validator.iter_errors(record)) == []
    nested_extra = json.loads(json.dumps(record))
    nested_extra["fact_admission_receipt"]["extra"] = True
    assert list(validator.iter_errors(nested_extra))


def test_store_v2_atomically_appends_reads_and_withholds_unreviewed_export(tmp_path: Path) -> None:
    context, plan = _inputs()
    result = DbDReasoningCandidateComposer().create(raw_output=_raw(context), context=context, plan=plan)
    assert result.candidate is not None and result.lineage is not None
    store = CommentaryCandidateStore(tmp_path / "commentary.sqlite3")
    with sqlite3.connect(store.path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 3
    store.append_reasoning_bundle(result.candidate, result.lineage)
    store.append_reasoning_bundle(result.candidate, result.lineage)
    assert store.get_reasoning_lineage(result.candidate.candidate_id) == result.lineage.to_dict()
    output = store.export_jsonl(tmp_path / "out.jsonl", match_id=plan.match_id)
    assert output.read_text("utf-8") == ""
    audit = store.export_jsonl(tmp_path / "audit.jsonl", match_id=plan.match_id, validated_only=False)
    assert len(audit.read_text("utf-8").splitlines()) == 1


def test_store_rejects_partial_bundle_and_detects_lineage_tamper(tmp_path: Path) -> None:
    context, plan = _inputs()
    result = DbDReasoningCandidateComposer().create(raw_output=_raw(context), context=context, plan=plan)
    assert result.candidate is not None and result.lineage is not None
    partial = CommentaryCandidateStore(tmp_path / "partial.sqlite3")
    with pytest.raises(Exception, match="lineage bundle"):
        partial.append(result.candidate)
    payload = result.candidate.to_dict()
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with sqlite3.connect(partial.path) as conn:
        conn.execute("INSERT INTO commentary_candidates VALUES(?,?,?,?,?,?,?,?)", (result.candidate.candidate_id, plan.match_id, plan.event_id, plan.event_revision, result.candidate.status.value, text, payload["commentary_candidate_sha256"], result.candidate.created_at))
    with pytest.raises(Exception, match="partial or conflicting"):
        partial.append_reasoning_bundle(result.candidate, result.lineage)
    assert partial.list_for_event(plan.event_id, validated_only=True) == ()
    assert partial.export_jsonl(tmp_path / "partial.jsonl", match_id=plan.match_id).read_text("utf-8") == ""
    with sqlite3.connect(partial.path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM dbd_reasoning_candidate_lineage").fetchone()[0] == 0

    with pytest.raises(ValueError, match="reserved R2D"):
        replace(result.candidate, reasoning_lineage_required=False)

    store = CommentaryCandidateStore(tmp_path / "tamper.sqlite3")
    store.append_reasoning_bundle(result.candidate, result.lineage)
    with sqlite3.connect(store.path) as conn:
        text = conn.execute("SELECT payload_json FROM dbd_reasoning_candidate_lineage").fetchone()[0]
        conn.execute("UPDATE dbd_reasoning_candidate_lineage SET payload_json=?", (text.replace('TUNED_REASONING', 'FORGED', 1),))
    with pytest.raises(Exception, match="lineage is invalid"):
        store.get_reasoning_lineage(result.candidate.candidate_id)

    column_store = CommentaryCandidateStore(tmp_path / "column-tamper.sqlite3")
    column_store.append_reasoning_bundle(result.candidate, result.lineage)
    with sqlite3.connect(column_store.path) as conn:
        conn.execute("UPDATE dbd_reasoning_candidate_lineage SET context_sha256=?", ("sha256:" + "0" * 64,))
    with pytest.raises(Exception, match="lineage is invalid"):
        column_store.append_reasoning_bundle(result.candidate, result.lineage)
    with pytest.raises(Exception, match="lineage is invalid"):
        column_store.get_reasoning_lineage(result.candidate.candidate_id)

    parent_store = CommentaryCandidateStore(tmp_path / "parent-tamper.sqlite3")
    parent_store.append_reasoning_bundle(result.candidate, result.lineage)
    with sqlite3.connect(parent_store.path) as conn:
        conn.execute("UPDATE dbd_reasoning_candidate_lineage SET parent_candidate_id=candidate_id")
    with pytest.raises(Exception, match="lineage is invalid"):
        parent_store.get_reasoning_lineage(result.candidate.candidate_id)

    shape_store = CommentaryCandidateStore(tmp_path / "shape-tamper.sqlite3")
    shape_store.append_reasoning_bundle(result.candidate, result.lineage)
    with sqlite3.connect(shape_store.path) as conn:
        text = conn.execute("SELECT payload_json FROM dbd_reasoning_candidate_lineage").fetchone()[0]
        value = json.loads(text)
        value["proposal"] = []
        conn.execute("UPDATE dbd_reasoning_candidate_lineage SET payload_json=?", (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),))
    with pytest.raises(Exception, match="lineage is invalid"):
        shape_store.get_reasoning_lineage(result.candidate.candidate_id)

    orphan_store = CommentaryCandidateStore(tmp_path / "orphan.sqlite3")
    lineage_payload = result.lineage.to_dict()
    lineage_text = json.dumps(lineage_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with sqlite3.connect(orphan_store.path) as conn:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("INSERT INTO dbd_reasoning_candidate_lineage VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
            result.lineage.candidate_id, None, result.lineage.match_id, result.lineage.event_id,
            result.lineage.event_revision, result.lineage.context_sha256, result.lineage.commentary_plan_sha256,
            result.lineage.structural_body_sha256, result.lineage.proposal.to_dict()["proposal_sha256"],
            lineage_text, result.lineage.lineage_sha256,
        ))
    with pytest.raises(Exception, match="foreign key"):
        orphan_store.export_jsonl(tmp_path / "orphan.jsonl", match_id=plan.match_id)

    candidate_column_store = CommentaryCandidateStore(tmp_path / "candidate-column-tamper.sqlite3")
    candidate_column_store.append_reasoning_bundle(result.candidate, result.lineage)
    with sqlite3.connect(candidate_column_store.path) as conn:
        conn.execute("UPDATE commentary_candidates SET event_revision=99")
    with pytest.raises(Exception, match="canonical payload/hash"):
        candidate_column_store.get_reasoning_lineage(result.candidate.candidate_id)
    with pytest.raises(Exception, match="canonical payload/hash"):
        candidate_column_store.append_reasoning_bundle(result.candidate, result.lineage)
    with pytest.raises(Exception, match="canonical payload/hash"):
        candidate_column_store.export_jsonl(tmp_path / "tampered.jsonl", match_id=plan.match_id)


def test_v1_store_migrates_additively_and_failed_migration_rolls_back(tmp_path: Path) -> None:
    context, plan = _inputs()
    result = DbDReasoningCandidateComposer().create(raw_output=_raw(context), context=context, plan=plan)
    assert result.candidate is not None
    legacy = CommentaryCandidate(plan, result.candidate.draft, result.candidate.validation)
    payload = legacy.to_dict()
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    path = tmp_path / "v1.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE store_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        conn.execute("CREATE TABLE commentary_candidates(candidate_id TEXT PRIMARY KEY,match_id TEXT NOT NULL,event_id TEXT NOT NULL,event_revision INTEGER NOT NULL,status TEXT NOT NULL,payload_json TEXT NOT NULL,payload_sha256 TEXT NOT NULL,created_at TEXT NOT NULL)")
        conn.execute("CREATE INDEX commentary_event_lookup ON commentary_candidates(event_id,event_revision,created_at,candidate_id)")
        conn.execute("INSERT INTO store_metadata VALUES('store_format','task049.game-commentary.sqlite')")
        conn.execute("INSERT INTO commentary_candidates VALUES(?,?,?,?,?,?,?,?)", (legacy.candidate_id, plan.match_id, plan.event_id, plan.event_revision, legacy.status.value, text, payload["commentary_candidate_sha256"], legacy.created_at))
        conn.execute("PRAGMA user_version=1")
    migrated = CommentaryCandidateStore(path)
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 3
        assert conn.execute("SELECT payload_json FROM commentary_candidates").fetchone()[0] == text
        assert conn.execute("SELECT COUNT(*) FROM dbd_reasoning_candidate_lineage").fetchone()[0] == 0
    assert len(migrated.list_for_event(plan.event_id)) == 1

    broken = tmp_path / "broken-v1.sqlite3"
    with sqlite3.connect(broken) as conn:
        conn.execute("CREATE TABLE store_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        conn.execute("CREATE TABLE commentary_candidates(candidate_id TEXT PRIMARY KEY,match_id TEXT NOT NULL,event_id TEXT NOT NULL,event_revision INTEGER NOT NULL,status TEXT NOT NULL,payload_json TEXT NOT NULL,payload_sha256 TEXT NOT NULL,created_at TEXT NOT NULL)")
        conn.execute("CREATE INDEX commentary_event_lookup ON commentary_candidates(event_id,event_revision,created_at,candidate_id)")
        conn.execute("CREATE TABLE dbd_reasoning_candidate_lineage(alien TEXT)")
        conn.execute("INSERT INTO store_metadata VALUES('store_format','task049.game-commentary.sqlite')")
        conn.execute("PRAGMA user_version=1")
    with pytest.raises(Exception):
        CommentaryCandidateStore(broken)
    with sqlite3.connect(broken) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        assert [row[1] for row in conn.execute("PRAGMA table_info(dbd_reasoning_candidate_lineage)")] == ["alien"]

    malformed_v2 = tmp_path / "malformed-v2.sqlite3"
    with sqlite3.connect(malformed_v2) as conn:
        conn.execute("CREATE TABLE store_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        conn.execute("CREATE TABLE commentary_candidates(candidate_id TEXT PRIMARY KEY,match_id TEXT NOT NULL,event_id TEXT NOT NULL,event_revision INTEGER NOT NULL,status TEXT NOT NULL,payload_json TEXT NOT NULL,payload_sha256 TEXT NOT NULL,created_at TEXT NOT NULL)")
        conn.execute("CREATE INDEX commentary_event_lookup ON commentary_candidates(event_id,event_revision,created_at,candidate_id)")
        conn.execute("CREATE TABLE dbd_reasoning_candidate_lineage(candidate_id BLOB PRIMARY KEY,parent_candidate_id BLOB,match_id BLOB,event_id BLOB,event_revision BLOB,context_sha256 BLOB,commentary_plan_sha256 BLOB,structural_body_sha256 BLOB,proposal_sha256 BLOB,payload_json BLOB,payload_sha256 BLOB)")
        conn.execute("CREATE INDEX dbd_reasoning_lineage_event_lookup ON dbd_reasoning_candidate_lineage(candidate_id)")
        conn.execute("INSERT INTO store_metadata VALUES('store_format','task049.game-commentary.sqlite')")
        conn.execute("PRAGMA user_version=2")
    with pytest.raises(Exception, match="table shape"):
        CommentaryCandidateStore(malformed_v2)
