from __future__ import annotations

from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from ai_video_production.desktop_editing_application import Task036EditingApplication


H = lambda ch: "sha256:" + ch * 64


def manifest() -> CutCandidateManifest:
    return CutCandidateManifest(
        source_asset_id="ASSET-00000000000000000000000000",
        analysis_audio_sha256=H("1"),
        analysis_sample_rate=48_000,
        source_duration_us=10_000_000,
        config_sha256=H("2"),
        transcript_manifest_sha256=H("3"),
        candidates=(
            CutCandidate("cut-000001", CutCandidateKind.SILENCE, 1_000_000, 2_000_000, 90, ("SILENCE",)),
            CutCandidate("cut-000002", CutCandidateKind.FILLER, 4_000_000, 4_500_000, 75, ("FILLER",)),
        ),
        keep_blocks=(),
    )


def application() -> Task036EditingApplication:
    tokens = iter(("r1", "r2", "approve"))
    return Task036EditingApplication.create(
        product_version="0.19.0",
        project_id="project-1",
        display_name="DbD 朝活",
        source_asset_sha256=H("4"),
        cut_manifest=manifest(),
        token_factory=lambda: next(tokens),
    )


def test_application_bootstrap_binds_real_stage_context_and_review_surface():
    app = application()
    assert app.coordinator.state.cut_candidate_manifest_sha256 == manifest().to_dict()["manifest_sha256"]
    assert "edit_candidate.review" in app.shell.snapshot().available_commands
    assert "resolve.assembly.prepare" not in app.shell.snapshot().available_commands
    vm = app.view_model()
    assert len(vm["timeline_tracks"]["CUT_OVERLAY"]) == 2


def test_review_gesture_is_immediately_reflected_in_timeline_projection():
    app = application()
    app.review_candidate(candidate_id="cut-000001", decision="CUT")
    vm = app.view_model()
    block = next(item for item in vm["timeline_tracks"]["CUT_OVERLAY"] if item["block_id"] == "cut:cut-000001")
    assert block["state"] == "CUT"


def test_final_plan_approval_advances_coordinator_command_surface():
    app = application()
    app.review_candidate(candidate_id="cut-000001", decision="CUT")
    app.review_candidate(candidate_id="cut-000002", decision="KEEP")
    prepared = app.prepare_edit_plan_approval()
    result = app.approve_edit_plan(
        confirmation_id=prepared["confirmation_id"],
        draft_plan_sha256=prepared["draft_plan_sha256"],
        approved_by="owner",
    )
    assert result["editing_session"]["edit_plan_approved"] is True
    assert "resolve.assembly.prepare" in result["available_commands"]
    assert result["next_recommended_action"] == "resolve.assembly.prepare"
    vm = app.view_model()
    assert any(item["block_type"] == "CUT_RANGE" and item["state"] == "APPROVED" for item in vm["timeline_tracks"]["CUT_OVERLAY"])
