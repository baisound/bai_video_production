from __future__ import annotations

import pytest

from ai_video_production.desktop_editing_session import EditingSessionState, EditingStage
from ai_video_production.errors import ProductError


H = lambda ch: "sha256:" + ch * 64


def test_minimum_editing_state_progression_and_available_commands():
    state = EditingSessionState("project-1")
    assert state.current_stage is EditingStage.PROJECT
    assert state.next_recommended_action == "media.choose_and_ingest"

    state = state.bind_source(asset_id="asset-1", asset_sha256=H("1"))
    assert state.current_stage is EditingStage.MEDIA
    assert "transcription.start" in state.available_commands()

    state = state.bind_transcript(H("2"))
    assert state.current_stage is EditingStage.TRANSCRIPT
    assert "cut_candidates.generate" in state.available_commands()

    state = state.bind_subtitle_workspace(H("3"))
    state = state.bind_cut_candidates(H("4"))
    assert state.current_stage is EditingStage.CUT_REVIEW
    assert "edit_plan.approve" in state.available_commands()

    state = state.bind_edit_plan(plan_sha256=H("5"), approved=True)
    assert "resolve.assembly.prepare" in state.available_commands()
    state = state.bind_resolve_assembly(H("6"))
    assert "resolve.assembly.apply" in state.available_commands()
    state = state.mark_resolve_applied()
    assert "render.start" in state.available_commands()
    state = state.bind_render_qa(report_sha256=H("7"), status="PASS")
    assert "handoff.create" in state.available_commands()
    state = state.bind_handoff(H("8"))
    assert state.current_stage is EditingStage.HANDOFF
    assert state.next_recommended_action == "NONE"


def test_source_change_invalidates_every_downstream_identity():
    state = EditingSessionState("project-1").bind_source(asset_id="asset-1", asset_sha256=H("1"))
    state = state.bind_transcript(H("2")).bind_subtitle_workspace(H("3")).bind_cut_candidates(H("4"))
    state = state.bind_edit_plan(plan_sha256=H("5"), approved=True).bind_resolve_assembly(H("6")).mark_resolve_applied()
    state = state.bind_render_qa(report_sha256=H("7"), status="PASS").bind_handoff(H("8"))
    changed = state.bind_source(asset_id="asset-2", asset_sha256=H("9"))
    assert changed.source_asset_id == "asset-2"
    assert changed.transcript_sha256 is None
    assert changed.edit_plan_sha256 is None
    assert changed.resolve_assembly_sha256 is None
    assert changed.render_qa_sha256 is None
    assert changed.handoff_manifest_sha256 is None


def test_unapproved_edit_plan_cannot_compile_resolve_stage():
    state = EditingSessionState("project-1").bind_source(asset_id="asset-1", asset_sha256=H("1"))
    state = state.bind_transcript(H("2")).bind_cut_candidates(H("4"))
    state = state.bind_edit_plan(plan_sha256=H("5"), approved=False)
    with pytest.raises(ProductError) as exc:
        state.bind_resolve_assembly(H("6"))
    assert exc.value.code == "ERR_SHELL_APPROVED_EDIT_PLAN_REQUIRED"


def test_failed_render_qa_blocks_handoff():
    state = EditingSessionState("project-1").bind_source(asset_id="asset-1", asset_sha256=H("1"))
    state = state.bind_transcript(H("2")).bind_cut_candidates(H("4"))
    state = state.bind_edit_plan(plan_sha256=H("5"), approved=True).bind_resolve_assembly(H("6")).mark_resolve_applied()
    state = state.bind_render_qa(report_sha256=H("7"), status="FAIL")
    with pytest.raises(ProductError) as exc:
        state.bind_handoff(H("8"))
    assert exc.value.code == "ERR_SHELL_RENDER_QA_PASS_REQUIRED"
