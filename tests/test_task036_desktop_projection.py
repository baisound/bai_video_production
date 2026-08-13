from __future__ import annotations

from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind
from ai_video_production.desktop_shell_projection import DesktopEditingProjectionService
from ai_video_production.edit_plan import CandidateGraphNode, EditDecision, EditPlan, PlannedRange
from ai_video_production.subtitle_workspace import (
    SubtitleOrigin,
    SubtitleReviewState,
    SubtitleWorkspace,
    WorkspaceCue,
)


def workspace() -> SubtitleWorkspace:
    return SubtitleWorkspace(
        "op_TEST123",
        2,
        (
            WorkspaceCue("cue-000001", 0, 4000, "こんにちは", "こんにちは", SubtitleOrigin.ASR, SubtitleReviewState.APPROVED),
            WorkspaceCue("cue-000002", 4000, 8000, "今日も配信です", "今日も配信です", SubtitleOrigin.ASR),
        ),
    )


def candidate() -> CutCandidate:
    return CutCandidate(
        "cut-000001",
        CutCandidateKind.SILENCE,
        8_000_000,
        9_000_000,
        91,
        ("SILENCE",),
    )


def plan() -> EditPlan:
    node = CandidateGraphNode(
        "cut-000001",
        "SILENCE",
        8_000_000,
        9_000_000,
        91,
        ("SILENCE",),
        EditDecision.CUT,
        EditDecision.CUT,
        8_000_000,
        9_000_000,
    )
    return EditPlan(
        source_asset_id="ast_00000000000000000000000000",
        source_duration_us=10_000_000,
        source_candidate_manifest_sha256="sha256:" + "a" * 64,
        target_duration_us=None,
        graph_nodes=(node,),
        graph_edges=(),
        keep_ranges=(PlannedRange("keep-1", 0, 8_000_000), PlannedRange("keep-2", 9_000_000, 10_000_000)),
        cut_ranges=(PlannedRange("cut-range-1", 8_000_000, 9_000_000, ("cut-000001",)),),
        approval_state="APPROVED",
        approved_by="human",
    )


def test_projection_exposes_transcript_and_subtitle_blocks():
    result = DesktopEditingProjectionService.build(source_duration_us=10_000_000, subtitle_workspace=workspace())
    body = result.to_dict()
    assert body["transcript_rows"][0]["text"] == "こんにちは"
    subtitles = [item for item in body["timeline_blocks"] if item["block_type"] == "SUBTITLE"]
    assert len(subtitles) == 2
    assert subtitles[0]["track_id"] == "S1"


def test_projection_maps_cut_candidate_review_state_without_plan():
    result = DesktopEditingProjectionService.build(source_duration_us=10_000_000, cut_candidates=(candidate(),))
    cut = next(item for item in result.timeline_blocks if item.block_type == "CUT_CANDIDATE")
    assert cut.state == "REVIEW"
    assert cut.track_id == "CUT_OVERLAY"


def test_projection_maps_human_decision_and_approved_keep_cut_ranges():
    result = DesktopEditingProjectionService.build(
        source_duration_us=10_000_000,
        cut_candidates=(candidate(),),
        edit_plan=plan(),
    )
    body = result.to_dict()
    candidate_block = next(item for item in body["timeline_blocks"] if item["block_type"] == "CUT_CANDIDATE")
    assert candidate_block["state"] == "CUT"
    assert len([item for item in body["timeline_blocks"] if item["block_type"] == "KEEP_RANGE"]) == 2
    approved_cut = next(item for item in body["timeline_blocks"] if item["block_type"] == "CUT_RANGE")
    assert approved_cut["state"] == "APPROVED"
