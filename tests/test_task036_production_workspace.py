from __future__ import annotations

from ai_video_production.production_dashboard import ProductionDashboardReport, SceneProductionSummary
from ai_video_production.task036_production_workspace import Task036ProductionWorkspaceProjection


def summary(*, attention=()):
    return SceneProductionSummary(
        scene_id="SC01",
        narrative_role="opening",
        slot_count=4,
        required_slot_count=4,
        locked_slot_count=1,
        empty_required_slot_count=3,
        stale_slot_count=0,
        candidate_count=2,
        ready_for_audit_count=1,
        audit_count=1,
        human_decision_count=0,
        regeneration_request_count=0,
        generation_attempt_count=1,
        failed_generation_count=0,
        continuity_edge_count=0,
        unresolved_continuity_count=0,
        audio_placement_count=0,
        pending_audio_placement_count=0,
        attention_reasons=tuple(attention),
    )


def report(scene):
    return ProductionDashboardReport(
        plan_id="PLAN-AAAAAAAAAAAAAAAA",
        approved_plan_sha256="sha256:" + "a" * 64,
        project_id="project-1",
        blueprint_id="BP-DASH-001",
        blueprint_title="Demo",
        budget={"currency": "USD", "cost_ceiling": "10", "remaining": "8"},
        bundle_validation_sha256="sha256:" + "b" * 64,
        plan_trace_sha256="sha256:" + "c" * 64,
        scenes=(scene,),
    )


def test_task036_production_workspace_keeps_nle_canvas_primary_and_read_only() -> None:
    projection = Task036ProductionWorkspaceProjection.from_dashboard(
        report(summary(attention=("HUMAN_AUDIT_DECISION_REQUIRED",)))
    ).to_dict()
    assert projection["workspace"] == "PRODUCTION_CONTROL"
    assert projection["layout_contract"]["primary_canvas"] == "VIEWER_AND_TIMELINE"
    assert projection["layout_contract"]["ai_chat_is_primary_canvas"] is False
    assert projection["available_commands"] == []
    assert projection["read_only"] is True
    assert projection["provider_execution_started"] is False
    assert projection["scenes"][0]["attention_reasons"] == ["HUMAN_AUDIT_DECISION_REQUIRED"]


def test_task036_production_workspace_projection_is_deterministic() -> None:
    dashboard = report(summary(attention=("REQUIRED_SLOT_EMPTY",)))
    first = Task036ProductionWorkspaceProjection.from_dashboard(dashboard).to_dict()
    second = Task036ProductionWorkspaceProjection.from_dashboard(dashboard).to_dict()
    assert first == second
    assert first["projection_sha256"].startswith("sha256:")
