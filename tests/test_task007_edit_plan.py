from __future__ import annotations

import pytest

from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from ai_video_production.edit_plan import CandidateReviewDecision, EditDecision, EditPlanService
from ai_video_production.errors import ProductError

ASSET_ID = "ASSET-00000000000000000000000000"
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def manifest() -> CutCandidateManifest:
    return CutCandidateManifest(
        source_asset_id=ASSET_ID,
        analysis_audio_sha256=SHA_A,
        analysis_sample_rate=48000,
        source_duration_us=10_000_000,
        config_sha256=SHA_B,
        transcript_manifest_sha256=None,
        candidates=(
            CutCandidate("cut-000001", CutCandidateKind.SILENCE, 1_000_000, 2_000_000, 90, ("FFMPEG_SILENCEDETECT",)),
            CutCandidate("cut-000002", CutCandidateKind.FILLER, 4_000_000, 4_500_000, 70, ("FILLER_ONLY_SEGMENT",)),
        ),
        keep_blocks=(),
    )


def test_draft_is_deterministic_and_never_auto_authorizes_external_write():
    first = EditPlanService.build(manifest())
    second = EditPlanService.build(manifest())
    assert first.to_dict() == second.to_dict()
    assert first.unresolved_candidate_ids == ("cut-000001", "cut-000002")
    assert first.ready_for_assembly is False
    assert first.to_dict()["automatic_external_write_authorized"] is False
    assert first.to_dict()["candidate_graph"]["edges"] == [
        {"from": "START", "to": "cut-000001"},
        {"from": "cut-000001", "to": "cut-000002"},
        {"from": "cut-000002", "to": "END"},
    ]


def test_human_review_and_plan_approval_build_keep_ranges():
    reviews = (
        CandidateReviewDecision("cut-000001", EditDecision.CUT),
        CandidateReviewDecision("cut-000002", EditDecision.KEEP),
    )
    plan = EditPlanService.build(manifest(), reviews=reviews, approve=True, approved_by="owner")
    assert plan.ready_for_assembly is True
    assert [(item.start_us, item.end_us) for item in plan.cut_ranges] == [(1_000_000, 2_000_000)]
    assert [(item.start_us, item.end_us) for item in plan.keep_ranges] == [
        (0, 1_000_000),
        (2_000_000, 10_000_000),
    ]
    assert plan.projected_duration_us == 9_000_000
    assert plan.to_dict()["approval_state"] == "APPROVED"


def test_approval_fails_closed_until_every_candidate_has_human_decision():
    with pytest.raises(ProductError) as exc:
        EditPlanService.build(
            manifest(),
            reviews=(CandidateReviewDecision("cut-000001", EditDecision.CUT),),
            approve=True,
            approved_by="owner",
        )
    assert exc.value.code == "ERR_EDIT_PLAN_HUMAN_REVIEW_REQUIRED"


def test_target_duration_orders_proposals_by_strength_but_does_not_approve_them():
    plan = EditPlanService.build(manifest(), target_duration_us=9_200_000)
    nodes = {item.candidate_id: item for item in plan.graph_nodes}
    assert nodes["cut-000001"].proposed_decision is EditDecision.CUT
    assert nodes["cut-000002"].proposed_decision is EditDecision.KEEP
    assert all(item.final_decision is EditDecision.REVIEW for item in plan.graph_nodes)


def test_cut_override_is_bounded_to_original_candidate():
    plan = EditPlanService.build(
        manifest(),
        reviews=(
            CandidateReviewDecision("cut-000001", EditDecision.CUT, 1_200_000, 1_800_000),
            CandidateReviewDecision("cut-000002", EditDecision.KEEP),
        ),
        approve=True,
        approved_by="owner",
    )
    assert [(item.start_us, item.end_us) for item in plan.cut_ranges] == [(1_200_000, 1_800_000)]
    with pytest.raises(ProductError) as exc:
        EditPlanService.build(
            manifest(),
            reviews=(
                CandidateReviewDecision("cut-000001", EditDecision.CUT, 900_000, 1_800_000),
                CandidateReviewDecision("cut-000002", EditDecision.KEEP),
            ),
        )
    assert exc.value.code == "ERR_EDIT_PLAN_OVERRIDE_OUTSIDE_CANDIDATE"
