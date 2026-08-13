from __future__ import annotations

from pathlib import Path
import wave

import pytest

from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from ai_video_production.edit_plan import CandidateReviewDecision, EditDecision, EditPlanService
from ai_video_production.errors import ProductError
from ai_video_production.manual_handoff import EditorHandoffService
from ai_video_production.media_probe import MediaProbeResult
from ai_video_production.render_qa import RenderQAReport
from ai_video_production.resolve_assembly import ResolveAssemblyResult
from ai_video_production.timebase import FrameRate

ASSET_ID = "ASSET-00000000000000000000000000"
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def approved_plan():
    manifest = CutCandidateManifest(
        ASSET_ID, SHA_A, 48000, 3_000_000, SHA_B, None,
        (CutCandidate("cut-000001", CutCandidateKind.SILENCE, 1_000_000, 1_500_000, 90, ("FFMPEG_SILENCEDETECT",)),),
        (),
    )
    return EditPlanService.build(
        manifest,
        reviews=(CandidateReviewDecision("cut-000001", EditDecision.KEEP),),
        approve=True,
        approved_by="owner",
    )


def qa_for(path: Path) -> RenderQAReport:
    import hashlib
    digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    probe = MediaProbeResult(
        "mp4", 3_000_000, path.stat().st_size, None,
        ({"codec_type": "video"}, {"codec_type": "audio"}),
    )
    return RenderQAReport(
        digest, path.stat().st_size, probe, None, None, 90, FrameRate(30), 2,
        ({"check": "NON_EMPTY_ARTIFACT", "status": "PASS"},),
    )


def write_wav(path: Path, *, rate=48000, seconds=3):
    with wave.open(str(path), "wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(b"\x00\x00\x00\x00" * rate * seconds)


def test_prepare_editor_work_is_deterministic_relative_and_qa_gated(tmp_path: Path):
    render = tmp_path / "master.mp4"
    render.write_bytes(b"master-render")
    audio = tmp_path / "mix-export.wav"
    write_wav(audio)
    edit_plan = approved_plan()
    assembly = ResolveAssemblyResult("sha256:" + "c" * 64, "BAI_AUTO_TEST", "APPLIED", False, "IMPORTED", "NOT_REQUESTED")
    qa = qa_for(render)
    root, manifest = EditorHandoffService.prepare(
        tmp_path / "handoff",
        edit_plan=edit_plan,
        assembly_result=assembly,
        render_qa=qa,
        render_path=render,
        audio_roundtrip_exports=(audio,),
    )
    payload = manifest.to_dict()
    assert root.name.startswith("EDITOR_WORK_")
    assert payload["absolute_paths_persisted"] is False
    assert payload["cubase_roundtrip"]["automatic_project_conversion_promised"] is False
    assert (root / "RENDER" / "master.mp4").is_file()
    assert (root / "AUDIO_ROUNDTRIP" / "EXPORT" / "01_mix-export.wav").is_file()

    returned = tmp_path / "cubase-return.wav"
    write_wav(returned)
    record = EditorHandoffService.register_cubase_return(root, returned, expected_duration_us=3_000_000)
    assert record["status"] == "ACCEPTED"
    assert record["sample_rate"] == 48000
    assert (root / record["relative_path"]).is_file()


def test_cubase_return_rejects_wrong_sample_rate(tmp_path: Path):
    render = tmp_path / "master.mp4"
    render.write_bytes(b"master-render")
    export = tmp_path / "export.wav"
    write_wav(export)
    root, _ = EditorHandoffService.prepare(
        tmp_path / "handoff",
        edit_plan=approved_plan(),
        assembly_result=ResolveAssemblyResult("sha256:" + "c" * 64, "BAI_AUTO_TEST", "APPLIED", False, "NOT_REQUESTED", "NOT_REQUESTED"),
        render_qa=qa_for(render),
        render_path=render,
        audio_roundtrip_exports=(export,),
    )
    returned = tmp_path / "bad.wav"
    write_wav(returned, rate=44100)
    with pytest.raises(ProductError) as exc:
        EditorHandoffService.register_cubase_return(root, returned, expected_duration_us=3_000_000)
    assert exc.value.code == "ERR_HANDOFF_AUDIO_RETURN_SAMPLE_RATE"


def test_invalid_optional_source_is_rejected_before_editor_work_publication(tmp_path: Path):
    render = tmp_path / "master.mp4"
    render.write_bytes(b"master-render")
    empty_subtitle = tmp_path / "empty.srt"
    empty_subtitle.write_bytes(b"")
    destination = tmp_path / "handoff"
    with pytest.raises(ProductError) as exc:
        EditorHandoffService.prepare(
            destination,
            edit_plan=approved_plan(),
            assembly_result=ResolveAssemblyResult(
                "sha256:" + "c" * 64,
                "BAI_AUTO_TEST",
                "APPLIED",
                False,
                "ALL_CUES_DROPPED_BY_EDIT",
                "NOT_REQUESTED",
            ),
            render_qa=qa_for(render),
            render_path=render,
            subtitle_srt_path=empty_subtitle,
        )
    assert exc.value.code == "ERR_HANDOFF_SOURCE_INVALID"
    assert not destination.exists()
