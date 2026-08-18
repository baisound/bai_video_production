from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import json

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
from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.game_event_evidence import GameEvidence, GameEvidenceType, SourceFrameRange
from ai_video_production.game_event_store import GameIntelligenceStore
from ai_video_production.game_intelligence_shell import GameIntelligenceShellApplication
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.task036_native_dialog import Task036NativeDialogService
from ai_video_production.task036_shell_ui import Task036ShellBridge
from ai_video_production.task036_shell_v611 import HTML
from ai_video_production.timebase import FrameRate


def _populate(app: GameIntelligenceShellApplication) -> tuple[GameMatch, CanonicalGameEvent]:
    store = GameIntelligenceStore(app.database_path)
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
    store.put_match(match)
    evidence = GameEvidence(
        production_job_id=match.production_job_id,
        match_id=match.match_id,
        source_asset_id=match.source_asset_id,
        producer="task049.shell-fixture",
        producer_version="1.0.0",
        evidence_type=GameEvidenceType.VISION,
        source_range=SourceFrameRange(100, 120),
        confidence_milli=900,
    )
    store.append_evidence(evidence)
    event = CanonicalGameEvent(
        match_id=match.match_id,
        revision=1,
        event_type=GameEventType.WINDOW_VAULT,
        source_range=evidence.source_range,
        game_version=match.game_version,
        environment=match.environment,
        perspective=match.perspective,
        state={"fixture": True},
        confidence_milli=900,
        confirmation_state=EventConfirmationState.NEEDS_REVIEW,
        evidence_refs=(evidence.game_evidence_id,),
        review_status=EventReviewStatus.PENDING,
    )
    store.append_event(event)
    return match, event


def test_shell_application_snapshot_is_analysis_only_and_projects_review_queue(tmp_path: Path) -> None:
    app = GameIntelligenceShellApplication(tmp_path / "project")
    empty = app.snapshot()
    assert empty["available"] is True
    assert empty["matches"] == []
    assert empty["native_analysis_pipeline_connected"] is False
    assert empty["production_timeline_mutated"] is False
    assert empty["resolve_write_performed"] is False

    match, event = _populate(app)
    snapshot = app.snapshot(match.match_id)
    assert snapshot["selected_match_id"] == match.match_id
    assert snapshot["matches"][0]["event_count"] == 1
    assert snapshot["matches"][0]["pending_review_count"] == 1
    assert snapshot["events"][0]["event_id"] == event.event_id
    assert "CONFIRM" in snapshot["events"][0]["available_actions"]
    assert snapshot["events"][0]["evidence"][0]["producer"] == "task049.shell-fixture"


def test_shell_application_review_is_append_only_and_does_not_mutate_production(tmp_path: Path) -> None:
    app = GameIntelligenceShellApplication(tmp_path / "project")
    match, event = _populate(app)
    result = app.review(event_id=event.event_id, action="CONFIRM", notes="human confirmation")
    assert result["review_applied"] is True
    assert result["event"]["revision"] == 2
    assert result["event"]["confirmation_state"] == "CONFIRMED"
    assert result["production_timeline_mutated"] is False
    assert result["resolve_write_performed"] is False

    store = GameIntelligenceStore(app.database_path)
    assert store.get_event(event.event_id, revision=1).confirmation_state is EventConfirmationState.NEEDS_REVIEW
    assert store.get_event(event.event_id).confirmation_state is EventConfirmationState.CONFIRMED
    assert app.snapshot(match.match_id)["events"][0]["revision"] == 2


def test_shell_application_exports_to_new_analysis_only_child_and_refuses_overwrite(tmp_path: Path) -> None:
    app = GameIntelligenceShellApplication(tmp_path / "project")
    match, _ = _populate(app)
    destination = tmp_path / "exports"
    destination.mkdir()
    result = app.export_analysis(match_id=match.match_id, destination=destination)
    assert result["exported"] is True
    assert result["analysis_only"] is True
    assert result["host_path_persisted"] is False
    assert result["production_timeline_mutated"] is False
    assert result["resolve_write_performed"] is False
    assert {row["file_name"] for row in result["artifacts"]} == {
        "analysis.json", "events.jsonl", "events.csv", "report.md", "commentary.srt", "manifest.json"
    }
    export_root = destination / result["export_name"]
    assert export_root.is_dir()
    with pytest.raises(Exception, match="already exists"):
        app.export_analysis(match_id=match.match_id, destination=destination)


def test_task036_bridge_exposes_task049_snapshot_review_and_path_free_export(tmp_path: Path) -> None:
    app = GameIntelligenceShellApplication(tmp_path / "project")
    match, event = _populate(app)
    handoff = tmp_path / "handoff"
    handoff.mkdir()

    class Backend:
        def choose_open_media(self):
            return None
        def choose_project_folder(self):
            return None
        def choose_handoff_folder(self):
            return str(handoff)

    service = ShellApplicationService(product_version="0.21.0")
    bridge = Task036ShellBridge(
        service,
        native_dialog=Task036NativeDialogService(Backend()),
        game_intelligence_application=app,
    )
    snapshot = bridge.game_intelligence_snapshot({"match_id": match.match_id})
    assert snapshot["selected_match_id"] == match.match_id
    reviewed = bridge.game_intelligence_review({"event_id": event.event_id, "action": "CONFIRM"})
    assert reviewed["event"]["confirmation_state"] == "CONFIRMED"
    exported = bridge.game_intelligence_export({"match_id": match.match_id})
    assert exported["selected"] is True
    assert exported["host_path_persisted"] is False
    assert "host_path" not in exported
    assert all("host_path" not in row for row in exported["artifacts"])


def test_task036_bridge_export_cancel_is_effect_free(tmp_path: Path) -> None:
    app = GameIntelligenceShellApplication(tmp_path / "project")
    match, _ = _populate(app)

    class Backend:
        def choose_open_media(self):
            return None
        def choose_project_folder(self):
            return None
        def choose_handoff_folder(self):
            return None

    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        native_dialog=Task036NativeDialogService(Backend()),
        game_intelligence_application=app,
    )
    result = bridge.game_intelligence_export({"match_id": match.match_id})
    assert result == {
        "exported": False,
        "selected": False,
        "host_path_persisted": False,
        "production_timeline_mutated": False,
        "resolve_write_performed": False,
    }



class _FakeProvider:
    def generate_planning_text(self, profile, availability, request):
        allowed = json.loads(request.prompt)["allowed_facts"]
        fact = allowed[0]
        return SimpleNamespace(
            text=json.dumps({"text": fact["value"], "claims": [fact]}, ensure_ascii=False),
            provider_id="fake", model_id="fake-model", provider_request_id="req", route_id="planning-fake",
        )


def test_shell_llm_commentary_requires_explicit_authority_and_persists_validated_candidate(tmp_path: Path) -> None:
    settings = SimpleNamespace(profile=object(), availability=object())
    app = GameIntelligenceShellApplication(
        tmp_path / "project",
        connection_settings=settings,
        provider_execution_service=_FakeProvider(),
        trivia_database_path=tmp_path / "trivia.sqlite3",
    )
    match, event = _populate(app)
    app.review(event_id=event.event_id, action="CONFIRM")
    with pytest.raises(Exception, match="explicit Human authorization"):
        app.generate_commentary(event_id=event.event_id, execution_authorized=False)
    result = app.generate_commentary(event_id=event.event_id, execution_authorized=True)
    assert result["generated"] is True
    assert result["status"] == "VALIDATED"
    assert result["provider_execution_started"] is True
    assert result["production_timeline_mutated"] is False
    assert app.snapshot(match.match_id)["events"][0]["validated_commentary"]["candidate_id"] == result["candidate_id"]


def test_task036_bridge_exposes_explicitly_authorized_game_commentary_generation(tmp_path: Path) -> None:
    settings = SimpleNamespace(profile=object(), availability=object())
    app = GameIntelligenceShellApplication(
        tmp_path / "project", connection_settings=settings, provider_execution_service=_FakeProvider(),
        trivia_database_path=tmp_path / "trivia.sqlite3",
    )
    _, event = _populate(app)
    app.review(event_id=event.event_id, action="CONFIRM")
    bridge = Task036ShellBridge(ShellApplicationService(product_version="0.21.0"), game_intelligence_application=app)
    with pytest.raises(Exception, match="explicit Human authorization"):
        bridge.game_intelligence_generate_commentary({"event_id": event.event_id, "execution_authorized": False})
    result = bridge.game_intelligence_generate_commentary({"event_id": event.event_id, "execution_authorized": True})
    assert result["generated"] is True


def test_v611_shell_contains_additive_task049_workspace_without_changing_task036_base_contract() -> None:
    assert 'data-page="gameIntelligence" data-contract-extension="TASK-049"' in HTML
    assert 'data-nav="gameIntelligence" data-contract-extension="TASK-049"' in HTML
    assert 'id="gameMatchList"' in HTML
    assert 'id="gameEventList"' in HTML
    assert 'id="gameApproveButton"' in HTML
    assert 'id="gameCorrectButton"' in HTML
    assert 'id="gameRejectButton"' in HTML
    assert 'id="gameUnknownButton"' in HTML
    assert 'id="gameExportButton"' in HTML
    assert 'id="gameCommentaryButton"' in HTML
    assert "game_intelligence_snapshot" in HTML
    assert "game_intelligence_review" in HTML
    assert "game_intelligence_export" in HTML
    assert "game_intelligence_generate_commentary" in HTML
