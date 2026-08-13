from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from ai_video_production.edit_plan import CandidateReviewDecision, EditDecision, EditPlanService
from ai_video_production.errors import ProductError
from ai_video_production.resolve_assembly import ResolveAssemblyService
from ai_video_production.resolve_subtitle_handoff import ResolveSubtitleHandoffService
from ai_video_production.subtitle_edit_remap import SubtitleEditAction, SubtitleEditRemapService
from ai_video_production.subtitle_workspace import SrtWorkspaceCodec, SubtitleOrigin, SubtitleReviewState, SubtitleWorkspace, WorkspaceCue
from ai_video_production.timebase import FrameRate

ASSET_ID = "ASSET-00000000000000000000000042"
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def edit_plan():
    manifest = CutCandidateManifest(
        ASSET_ID, SHA_A, 48_000, 4_000_000, SHA_B, None,
        (CutCandidate("cut-000001", CutCandidateKind.SILENCE, 1_000_000, 2_000_000, 90, ("FFMPEG_SILENCEDETECT",)),),
        (),
    )
    return EditPlanService.build(manifest, reviews=(CandidateReviewDecision("cut-000001", EditDecision.CUT),), approve=True, approved_by="owner")


def approved_cue(cue_id, start_ms, end_ms, text):
    return WorkspaceCue(cue_id, start_ms, end_ms, text, text, SubtitleOrigin.HUMAN, SubtitleReviewState.APPROVED)


def test_cut_aware_subtitle_remap_at_24fps_moves_second_cue_one_second_earlier(tmp_path: Path):
    rate = FrameRate(24)
    ws = SubtitleWorkspace("subtitle-remap-test", 0, (
        approved_cue("alpha", 250, 750, "BAI subtitle alpha"),
        approved_cue("beta", 2250, 2950, "BAI subtitle beta"),
    ))
    subtitle_plan = ResolveSubtitleHandoffService.build(ws, timeline_rate=rate)
    plan = ResolveAssemblyService.compile(edit_plan(), timeline_rate=rate, subtitle_plan=subtitle_plan)
    assert [(c.action.value, c.timeline_start_frame, c.timeline_end_frame) for c in plan.subtitle_cues] == [
        ("KEEP", 6, 18),
        ("KEEP", 30, 47),
    ]
    source = tmp_path / "reviewed.srt"
    source.write_text(SrtWorkspaceCodec.render(ws), encoding="utf-8")
    derived = tmp_path / "derived.srt"
    SubtitleEditRemapService.verify_and_write_derived_srt(
        source, derived, cues=plan.subtitle_cues, timeline_rate=rate, timeline_origin_frame=0
    )
    text = derived.read_text(encoding="utf-8")
    assert "00:00:00,250 --> 00:00:00,750" in text
    assert "00:00:01,250 --> 00:00:01,958" in text


def test_cue_wholly_inside_cut_is_dropped():
    rate = FrameRate(24)
    ws = SubtitleWorkspace("subtitle-remap-drop", 0, (approved_cue("inside-cut", 1200, 1600, "drop me"),))
    subtitle_plan = ResolveSubtitleHandoffService.build(ws, timeline_rate=rate)
    plan = ResolveAssemblyService.compile(edit_plan(), timeline_rate=rate, subtitle_plan=subtitle_plan)
    assert plan.subtitle_cues[0].action is SubtitleEditAction.DROP_CUT
    assert plan.subtitle_cues[0].timeline_start_frame is None


def test_cue_crossing_cut_boundary_fails_closed_for_human_review():
    rate = FrameRate(24)
    ws = SubtitleWorkspace("subtitle-remap-cross", 0, (approved_cue("cross-cut", 750, 1250, "review me"),))
    subtitle_plan = ResolveSubtitleHandoffService.build(ws, timeline_rate=rate)
    with pytest.raises(ProductError) as exc:
        ResolveAssemblyService.compile(edit_plan(), timeline_rate=rate, subtitle_plan=subtitle_plan)
    assert exc.value.code == "ERR_RESOLVE_SUBTITLE_CUT_BOUNDARY_REVIEW_REQUIRED"
