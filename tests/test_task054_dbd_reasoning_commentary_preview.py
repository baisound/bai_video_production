from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.canonical_game_event import (
    CanonicalGameEvent, EventConfirmationState, EventReviewStatus, GameEnvironment,
    GameEventType, GameMatch, GameMatchStatus, GamePerspective,
)
from ai_video_production.dbd_reasoning_commentary_preview import (
    CommentaryPreviewStatus, PreviewMediaBindingStatus, compile_commentary_preview,
)
from ai_video_production.dbd_reasoning_commentary_preview_ui import (
    KIND_JA, STATUS_JA, format_preview_time,
)
from ai_video_production.game_commentary import (
    CommentaryCandidate, CommentaryCandidateStore, CommentaryClaim, CommentaryClaimKind,
    CommentaryDraft, CommentaryFactValidator, CommentaryPlanner,
)
from ai_video_production.game_event_evidence import GameEvidence, GameEvidenceType, SourceFrameRange
from ai_video_production.game_event_store import GameIntelligenceStore
from ai_video_production.game_intelligence_export import GameIntelligenceAnalysisExporter
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.timebase import FrameRate


def _analysis(tmp_path: Path) -> dict:
    store = GameIntelligenceStore(tmp_path / "game.sqlite3")
    commentary_store = CommentaryCandidateStore(tmp_path / "commentary.sqlite3")
    match = GameMatch(
        production_job_id=generate_id(IdKind.JOB), source_asset_id=generate_id(IdKind.ASSET),
        game_profile_id="dead_by_daylight", game_profile_version="1.0.0", game_version="9.1.0",
        environment=GameEnvironment.LIVE, perspective=GamePerspective.SURVIVOR,
        source_rate=FrameRate(30000, 1001), status=GameMatchStatus.ANALYZING,
    )
    evidence = GameEvidence(
        production_job_id=match.production_job_id, match_id=match.match_id,
        source_asset_id=match.source_asset_id, producer="task054.r5b-fixture",
        producer_version="1.0.0", evidence_type=GameEvidenceType.VISION,
        source_range=SourceFrameRange(300, 330), confidence_milli=950,
    )
    event = CanonicalGameEvent(
        match_id=match.match_id, revision=1, event_type=GameEventType.WINDOW_VAULT,
        source_range=evidence.source_range, game_version=match.game_version,
        environment=match.environment, perspective=match.perspective, state={"fixture": True},
        confidence_milli=940, confirmation_state=EventConfirmationState.CONFIRMED,
        evidence_refs=(evidence.game_evidence_id,), review_status=EventReviewStatus.HUMAN_APPROVED,
    )
    store.put_match(match)
    store.append_evidence(evidence)
    store.append_event(event)
    plan = CommentaryPlanner().plan(event, language="ja-JP")
    fact = next(item for item in plan.facts if item.kind is CommentaryClaimKind.EVENT_OCCURRED)
    draft = CommentaryDraft("ここで窓越えが起きました。", (CommentaryClaim(fact.kind, fact.key, fact.value),))
    commentary_store.append(CommentaryCandidate(plan, draft, CommentaryFactValidator().validate(plan, draft)))
    files = GameIntelligenceAnalysisExporter.export(
        store=store, commentary_store=commentary_store, match_id=match.match_id,
        destination=tmp_path / "export",
    )
    return json.loads(files["json"].read_text(encoding="utf-8"))


def _rehash(record: dict, checksum_field: str) -> None:
    body = {key: value for key, value in record.items() if key != checksum_field}
    record[checksum_field] = sha256_bytes(canonical_json_bytes(body))


def _schema() -> dict:
    return json.loads(Path("schemas/dbd-reasoning-commentary-preview.schema.json").read_text(encoding="utf-8"))


def test_compile_ready_preview_is_exact_time_aligned_and_non_learning(tmp_path: Path) -> None:
    preview = compile_commentary_preview(
        _analysis(tmp_path), preview_id="preview-r5b-001", video_duration_ms=60_000,
        media_binding_status=PreviewMediaBindingStatus.CANONICAL_ASSET_BOUND,
    )
    record = preview.to_dict()

    assert preview.status is CommentaryPreviewStatus.READY
    assert len(preview.blocks) == 1
    assert (preview.blocks[0].start_ms, preview.blocks[0].end_ms) == (10_010, 11_011)
    assert record["session_mode"] == "PREVIEW_NO_LEARNING"
    assert record["training_eligible"] is False
    assert record["dataset_mutated"] is False
    assert record["binding_mutated"] is False
    assert record["training_started"] is False
    assert record["provider_execution_performed"] is False
    assert record["production_timeline_mutated"] is False
    assert not list(Draft202012Validator(_schema()).iter_errors(record))


def test_unverified_operator_video_is_truthfully_not_confirmed(tmp_path: Path) -> None:
    preview = compile_commentary_preview(
        _analysis(tmp_path), preview_id="preview-r5b-002", video_duration_ms=60_000,
        media_binding_status=PreviewMediaBindingStatus.OPERATOR_SELECTED_UNVERIFIED,
    )
    assert preview.status is CommentaryPreviewStatus.NOT_CONFIRMED_MEDIA_IDENTITY


def test_no_validated_commentary_has_explicit_empty_status(tmp_path: Path) -> None:
    analysis = _analysis(tmp_path)
    analysis["validated_commentary"] = []
    _rehash(analysis, "analysis_export_sha256")
    preview = compile_commentary_preview(
        analysis, preview_id="preview-r5b-003", video_duration_ms=60_000,
        media_binding_status=PreviewMediaBindingStatus.CANONICAL_ASSET_BOUND,
    )
    assert preview.status is CommentaryPreviewStatus.NO_VALIDATED_COMMENTARY
    assert preview.blocks == ()


def test_analysis_or_nested_candidate_tampering_fails_closed(tmp_path: Path) -> None:
    analysis = _analysis(tmp_path)
    analysis["validated_commentary"][0]["draft"]["text"] = "改ざん"
    _rehash(analysis, "analysis_export_sha256")

    with pytest.raises(ValueError, match="commentary_candidate_sha256"):
        compile_commentary_preview(
            analysis, preview_id="preview-r5b-004", video_duration_ms=60_000,
            media_binding_status=PreviewMediaBindingStatus.CANONICAL_ASSET_BOUND,
        )


def test_multiple_candidates_for_one_event_requires_human_selection(tmp_path: Path) -> None:
    analysis = _analysis(tmp_path)
    duplicate = json.loads(json.dumps(analysis["validated_commentary"][0]))
    duplicate["candidate_id"] = generate_id(IdKind.CANDIDATE)
    _rehash(duplicate, "commentary_candidate_sha256")
    analysis["validated_commentary"].append(duplicate)
    _rehash(analysis, "analysis_export_sha256")

    with pytest.raises(ValueError, match="Human selection"):
        compile_commentary_preview(
            analysis, preview_id="preview-r5b-005", video_duration_ms=60_000,
            media_binding_status=PreviewMediaBindingStatus.CANONICAL_ASSET_BOUND,
        )


def test_block_outside_selected_video_duration_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="exceeds video duration"):
        compile_commentary_preview(
            _analysis(tmp_path), preview_id="preview-r5b-006", video_duration_ms=10_500,
            media_binding_status=PreviewMediaBindingStatus.CANONICAL_ASSET_BOUND,
        )


def test_rehashed_unknown_event_field_fails_exact_boundary(tmp_path: Path) -> None:
    analysis = _analysis(tmp_path)
    event = analysis["events"][0]
    event["unexpected"] = "not-canonical"
    _rehash(event, "event_sha256")
    _rehash(analysis, "analysis_export_sha256")

    with pytest.raises(ValueError, match="event fields are not exact"):
        compile_commentary_preview(
            analysis, preview_id="preview-r5b-007", video_duration_ms=60_000,
            media_binding_status=PreviewMediaBindingStatus.CANONICAL_ASSET_BOUND,
        )


def test_candidate_for_absent_event_revision_fails_closed(tmp_path: Path) -> None:
    analysis = _analysis(tmp_path)
    candidate = analysis["validated_commentary"][0]
    candidate["event_revision"] = 2
    candidate["plan"]["event_revision"] = 2
    _rehash(candidate["plan"], "commentary_plan_sha256")
    _rehash(candidate, "commentary_candidate_sha256")
    _rehash(analysis, "analysis_export_sha256")

    with pytest.raises(ValueError, match="absent event revision"):
        compile_commentary_preview(
            analysis, preview_id="preview-r5b-008", video_duration_ms=60_000,
            media_binding_status=PreviewMediaBindingStatus.CANONICAL_ASSET_BOUND,
        )


def test_schema_mirror_and_japanese_preview_copy_are_exact() -> None:
    assert Path("schemas/dbd-reasoning-commentary-preview.schema.json").read_bytes() == Path(
        "src/ai_video_production/schema_resources/dbd-reasoning-commentary-preview.schema.json"
    ).read_bytes()
    assert format_preview_time(61_234) == "01:01.234"
    assert set(KIND_JA.values()) == {"実況", "解説", "戦術", "反応"}
    assert "同一性は未確認" in STATUS_JA[CommentaryPreviewStatus.NOT_CONFIRMED_MEDIA_IDENTITY]
