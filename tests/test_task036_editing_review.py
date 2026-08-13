from __future__ import annotations

import pytest

from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from ai_video_production.desktop_editing_review import ReviewWorkspaceState, Task036ReviewFacade
from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.errors import ProductError


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


def facade(tokens=None) -> Task036ReviewFacade:
    token_values = iter(tokens or ("tok-1", "tok-2", "tok-3", "tok-4"))
    shell = ShellApplicationService(product_version="0.19.0", token_factory=lambda: next(token_values))
    shell.open_project_context(project_id="project-1", display_name="Project 1")
    return Task036ReviewFacade(shell, ReviewWorkspaceState(manifest()))


def test_select_candidate_syncs_playhead_to_candidate_start():
    value = facade()
    result = value.select_candidate("cut-000002")
    assert result["selected_candidate_id"] == "cut-000002"
    assert result["playhead_us"] == 4_000_000


def test_seek_rejects_outside_source_duration():
    value = facade()
    with pytest.raises(ProductError) as exc:
        value.seek(10_000_001)
    assert exc.value.code == "ERR_SHELL_PLAYHEAD_OUT_OF_RANGE"


def test_cut_keep_click_is_explicit_human_decision_without_second_modal():
    value = facade()
    result = value.review_candidate(candidate_id="cut-000001", decision="CUT")
    assert result["receipt"]["command_type"] == "edit_candidate.review"
    assert result["receipt"]["category"] == "HUMAN_FINAL_AUTHORITY"
    assert result["review"]["reviewed_count"] == 1
    assert result["review"]["unresolved_count"] == 1
    candidate = next(item for item in result["review"]["candidates"] if item["candidate_id"] == "cut-000001")
    assert candidate["review_state"] == "CUT"


def test_review_decision_invalidates_other_pending_confirmation():
    value = facade(tokens=("r1", "r2", "plan-before", "r3", "r4"))
    # resolve all candidates first, then create plan confirmation
    value.review_candidate(candidate_id="cut-000001", decision="CUT")
    value.review_candidate(candidate_id="cut-000002", decision="KEEP")
    prepared = value.prepare_plan_approval()
    # changing the review after summary advances shell context and invalidates the plan token
    value.review_candidate(candidate_id="cut-000002", decision="CUT")
    with pytest.raises(ProductError) as exc:
        value.approve_plan(
            confirmation_id=prepared["confirmation_id"],
            approved_by="owner",
            draft_plan_sha256=prepared["draft_plan_sha256"],
        )
    assert exc.value.code in {"ERR_SHELL_EDIT_PLAN_DRAFT_STALE", "ERR_SHELL_CONFIRMATION_INVALID", "ERR_SHELL_CONFIRMATION_STALE"}


def test_plan_approval_requires_every_candidate_reviewed():
    value = facade()
    value.review_candidate(candidate_id="cut-000001", decision="KEEP")
    with pytest.raises(ProductError) as exc:
        value.prepare_plan_approval()
    assert exc.value.code == "ERR_SHELL_EDIT_PLAN_REVIEW_INCOMPLETE"


def test_plan_approval_is_separate_human_gate_and_produces_approved_plan():
    value = facade()
    value.review_candidate(candidate_id="cut-000001", decision="CUT")
    value.review_candidate(candidate_id="cut-000002", decision="KEEP")
    prepared = value.prepare_plan_approval()
    assert prepared["cut_count"] == 1
    result = value.approve_plan(
        confirmation_id=prepared["confirmation_id"],
        approved_by="owner",
        draft_plan_sha256=prepared["draft_plan_sha256"],
    )
    assert result["receipt"]["command_type"] == "edit_plan.approve"
    assert result["review"]["approved_plan"]["approval_state"] == "APPROVED"
    assert result["review"]["approved_plan"]["cut_count"] == 1


def test_cut_override_must_stay_inside_candidate():
    value = facade()
    with pytest.raises(ProductError) as exc:
        value.review_candidate(
            candidate_id="cut-000001",
            decision="CUT",
            override_start_us=500_000,
            override_end_us=1_500_000,
        )
    assert exc.value.code == "ERR_EDIT_PLAN_OVERRIDE_OUTSIDE_CANDIDATE"
