from __future__ import annotations

import pytest

from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from ai_video_production.desktop_editing_coordinator import DesktopEditingCoordinator
from ai_video_production.desktop_pre_edit_binding import Task036PreEditBinding
from ai_video_production.errors import ProductError
from ai_video_production.subtitles import TranscriptManifest, TranscriptSegment

H = lambda ch: "sha256:" + ch * 64
ASSET = "ASSET-00000000000000000000000000"


def coordinator():
    c = DesktopEditingCoordinator.create(product_version="0.19.0", project_id="project-1", display_name="Project 1")
    c.bind_source(asset_id=ASSET, asset_sha256=H("a"))
    return c


def transcript(asset_id=ASSET):
    return TranscriptManifest(asset_id, "ja", "faster-whisper", "large-v3", (
        TranscriptSegment("seg-1", 0, 1_000_000, "こんにちは"),
        TranscriptSegment("seg-2", 1_500_000, 2_500_000, "テストです"),
    ))


def cut_manifest(transcript_sha, asset_id=ASSET):
    return CutCandidateManifest(
        asset_id, H("b"), 48_000, 3_000_000, H("c"), transcript_sha,
        (CutCandidate("cut-000001", CutCandidateKind.SILENCE, 1_000_000, 1_400_000, 90, ("SILENCE",)),),
        (),
    )


def test_completed_pre_edit_results_promote_into_integrated_review_application():
    c = coordinator(); binder = Task036PreEditBinding(c)
    t = transcript(); t_sha = t.to_dict()["manifest_sha256"]
    result = binder.bind_transcript(t)
    assert result["next_recommended_action"] == "subtitle.save"
    subtitle = binder.create_subtitle_workspace()
    assert subtitle["cue_count"] == 2
    app = binder.bind_cut_candidates(cut_manifest(t_sha))
    assert app.coordinator is c
    assert c.state.cut_candidate_manifest_sha256 == app.cut_manifest.to_dict()["manifest_sha256"]
    assert "edit_candidate.review" in c.snapshot().available_commands
    assert app.view_model()["transcript_rows"]


def test_transcript_source_mismatch_is_rejected_before_state_change():
    c = coordinator(); binder = Task036PreEditBinding(c)
    other = "ASSET-00000000000000000000000001"
    with pytest.raises(ProductError) as exc:
        binder.bind_transcript(transcript(other))
    assert exc.value.code == "ERR_SHELL_TRANSCRIPT_SOURCE_MISMATCH"
    assert c.state.transcript_sha256 is None


def test_cut_candidate_transcript_mismatch_is_fail_closed():
    c = coordinator(); binder = Task036PreEditBinding(c)
    t = transcript(); binder.bind_transcript(t)
    with pytest.raises(ProductError) as exc:
        binder.bind_cut_candidates(cut_manifest(H("f")))
    assert exc.value.code == "ERR_SHELL_CUT_TRANSCRIPT_MISMATCH"
    assert c.state.cut_candidate_manifest_sha256 is None
