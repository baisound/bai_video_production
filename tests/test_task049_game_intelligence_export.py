from __future__ import annotations

import csv
import io
import json
from pathlib import Path

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
    CommentaryCandidateStore,
    CommentaryClaim,
    CommentaryClaimKind,
    CommentaryDraft,
    CommentaryFactValidator,
    CommentaryPlanner,
)
from ai_video_production.game_event_evidence import GameEvidence, GameEvidenceType, SourceFrameRange
from ai_video_production.game_event_store import GameIntelligenceStore
from ai_video_production.game_intelligence_export import GameIntelligenceAnalysisExporter
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.timebase import FrameRate


def populated(tmp_path: Path, *, confirmation: EventConfirmationState = EventConfirmationState.CONFIRMED, review: EventReviewStatus = EventReviewStatus.HUMAN_APPROVED):
    store = GameIntelligenceStore(tmp_path / "game.sqlite3")
    commentary_store = CommentaryCandidateStore(tmp_path / "commentary.sqlite3")
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
        producer="task049.export-fixture",
        producer_version="1.0.0",
        evidence_type=GameEvidenceType.VISION,
        source_range=SourceFrameRange(300, 330),
        confidence_milli=950,
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
        confirmation_state=confirmation,
        evidence_refs=(evidence.game_evidence_id,),
        review_status=review,
    )
    store.put_match(match)
    store.append_evidence(evidence)
    store.append_event(event)

    candidate = None
    plan = CommentaryPlanner().plan(event, language="ja-JP")
    if plan.facts:
        fact = next(item for item in plan.facts if item.kind is CommentaryClaimKind.EVENT_OCCURRED)
        draft = CommentaryDraft("ここで窓越えが起きました。", (CommentaryClaim(fact.kind, fact.key, fact.value),))
        validation = CommentaryFactValidator().validate(plan, draft)
        candidate = CommentaryCandidate(plan, draft, validation)
        commentary_store.append(candidate)
    return store, commentary_store, match, event, candidate


def test_analysis_export_writes_all_required_formats_and_manifest_hashes(tmp_path: Path) -> None:
    store, commentary_store, match, event, candidate = populated(tmp_path)
    files = GameIntelligenceAnalysisExporter.export(
        store=store,
        commentary_store=commentary_store,
        match_id=match.match_id,
        destination=tmp_path / "export",
    )
    assert set(files) == {"json", "jsonl", "csv", "markdown", "srt", "manifest"}
    assert all(path.exists() for path in files.values())

    analysis = json.loads(files["json"].read_text("utf-8"))
    body = dict(analysis)
    digest = body.pop("analysis_export_sha256")
    assert digest == sha256_bytes(canonical_json_bytes(body))
    assert analysis["analysis_only"] is True
    assert analysis["production_timeline_mutated"] is False
    assert analysis["resolve_write_performed"] is False
    assert analysis["match"]["match_id"] == match.match_id
    assert analysis["events"][0]["event_id"] == event.event_id
    assert analysis["validated_commentary"][0]["candidate_id"] == candidate.candidate_id

    manifest = json.loads(files["manifest"].read_text("utf-8"))
    manifest_body = dict(manifest)
    manifest_digest = manifest_body.pop("manifest_sha256")
    assert manifest_digest == sha256_bytes(canonical_json_bytes(manifest_body))
    assert {item["filename"] for item in manifest["artifacts"]} == {
        "analysis.json", "events.jsonl", "events.csv", "report.md", "commentary.srt"
    }
    for item in manifest["artifacts"]:
        assert item["sha256"] == sha256_bytes((tmp_path / "export" / item["filename"]).read_bytes())


def test_export_jsonl_csv_markdown_are_deterministic_latest_event_views(tmp_path: Path) -> None:
    store, commentary_store, match, event, _ = populated(tmp_path)
    newer = CanonicalGameEvent(
        match_id=event.match_id,
        event_id=event.event_id,
        revision=2,
        event_type=GameEventType.WINDOW_VAULT,
        source_range=event.source_range,
        game_version=event.game_version,
        environment=event.environment,
        perspective=event.perspective,
        state={"fixture": True, "reviewed": True},
        confidence_milli=970,
        confirmation_state=EventConfirmationState.CONFIRMED,
        evidence_refs=event.evidence_refs,
        review_status=EventReviewStatus.HUMAN_CORRECTED,
    )
    store.append_event(newer)
    files = GameIntelligenceAnalysisExporter.export(
        store=store,
        commentary_store=commentary_store,
        match_id=match.match_id,
        destination=tmp_path / "export",
    )
    jsonl = files["jsonl"].read_text("utf-8").splitlines()
    assert len(jsonl) == 1
    assert json.loads(jsonl[0])["revision"] == 2

    rows = list(csv.DictReader(io.StringIO(files["csv"].read_text("utf-8"))))
    assert len(rows) == 1
    assert rows[0]["revision"] == "2"
    assert rows[0]["commentary_candidate_id"] == ""  # old-revision commentary is not silently reused
    assert "HUMAN_CORRECTED" in files["markdown"].read_text("utf-8")


def test_srt_uses_exact_rational_source_clock_and_validated_current_commentary(tmp_path: Path) -> None:
    store, commentary_store, match, event, _ = populated(tmp_path)
    files = GameIntelligenceAnalysisExporter.export(
        store=store,
        commentary_store=commentary_store,
        match_id=match.match_id,
        destination=tmp_path / "export",
    )
    text = files["srt"].read_text("utf-8")
    micros = event.source_range.to_microsecond_range(match.source_rate)
    start_ms = micros["start"] // 1000
    end_ms = (micros["end_exclusive"] + 999) // 1000

    def fmt(ms: int) -> str:
        h, rem = divmod(ms, 3_600_000)
        m, rem = divmod(rem, 60_000)
        s, x = divmod(rem, 1_000)
        return f"{h:02d}:{m:02d}:{s:02d},{x:03d}"

    assert f"{fmt(start_ms)} --> {fmt(end_ms)}" in text
    assert "ここで窓越えが起きました。" in text


def test_uncertain_event_is_exported_for_analysis_but_not_as_srt_commentary(tmp_path: Path) -> None:
    store, commentary_store, match, event, candidate = populated(
        tmp_path,
        confirmation=EventConfirmationState.NEEDS_REVIEW,
        review=EventReviewStatus.PENDING,
    )
    assert candidate is None  # R7 planner abstains and produces no speakable candidate
    files = GameIntelligenceAnalysisExporter.export(
        store=store,
        commentary_store=commentary_store,
        match_id=match.match_id,
        destination=tmp_path / "export",
    )
    assert '"confirmation_state":"NEEDS_REVIEW"' in files["jsonl"].read_text("utf-8")
    assert files["srt"].read_text("utf-8") == ""


def test_multiple_validated_current_commentary_candidates_fail_closed(tmp_path: Path) -> None:
    store, commentary_store, match, event, candidate = populated(tmp_path)
    assert candidate is not None
    second = CommentaryCandidate(candidate.plan, candidate.draft, candidate.validation)
    commentary_store.append(second)
    with pytest.raises(ValueError, match="multiple VALIDATED"):
        GameIntelligenceAnalysisExporter.export(
            store=store,
            commentary_store=commentary_store,
            match_id=match.match_id,
            destination=tmp_path / "export",
        )


def test_export_can_finish_without_commentary_store(tmp_path: Path) -> None:
    store, _, match, _, _ = populated(tmp_path)
    files = GameIntelligenceAnalysisExporter.export(
        store=store,
        match_id=match.match_id,
        destination=tmp_path / "export",
    )
    assert files["srt"].read_text("utf-8") == ""
    analysis = json.loads(files["json"].read_text("utf-8"))
    assert analysis["validated_commentary"] == []


def test_export_rejects_symlink_destination(tmp_path: Path) -> None:
    store, _, match, _, _ = populated(tmp_path)
    actual = tmp_path / "actual"
    actual.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(actual, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable on this host")
    with pytest.raises(ValueError, match="must not be a symlink"):
        GameIntelligenceAnalysisExporter.export(
            store=store,
            match_id=match.match_id,
            destination=link,
        )
