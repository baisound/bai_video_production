from __future__ import annotations

from importlib import resources
from pathlib import Path

from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from ai_video_production.edit_plan import CandidateReviewDecision, EditDecision, EditPlanService
from ai_video_production.manual_handoff import EditorHandoffManifest, HandoffFile
from ai_video_production.media_probe import MediaProbeResult
from ai_video_production.render_qa import LoudnessMeasurement, LoudnessProfile, RenderQAReport
from ai_video_production.resolve_assembly import ResolveAssemblyService
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.timebase import FrameRate

ASSET_ID = "ASSET-00000000000000000000000000"
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def docs():
    upstream = CutCandidateManifest(
        ASSET_ID, SHA_A, 48_000, 3_000_000, SHA_B, None,
        (CutCandidate("cut-000001", CutCandidateKind.SILENCE, 1_000_000, 1_500_000, 90, ("FFMPEG_SILENCEDETECT",)),), (),
    )
    edit = EditPlanService.build(
        upstream,
        reviews=(CandidateReviewDecision("cut-000001", EditDecision.CUT),),
        approve=True,
        approved_by="owner",
    )
    assembly = ResolveAssemblyService.compile(edit, timeline_rate=FrameRate(30))
    probe = MediaProbeResult("mp4", 2_500_000, 10, None, ({"codec_type": "video"}, {"codec_type": "audio"}))
    qa = RenderQAReport(
        SHA_A, 10, probe, LoudnessMeasurement(-16.0, -1.5, 4.0), LoudnessProfile(),
        75, FrameRate(30), 2, ({"check": "NON_EMPTY_ARTIFACT", "status": "PASS"},),
    )
    qa_hash = qa.to_dict()["report_sha256"]
    handoff = EditorHandoffManifest(
        "EDITOR_WORK_123456789ABC", edit.to_dict()["plan_sha256"], assembly.to_dict()["assembly_sha256"], qa_hash,
        (HandoffFile("RENDER_MASTER", "RENDER/master.mp4", SHA_B, 10),), False,
    )
    return edit.to_dict(), assembly.to_dict(), qa.to_dict(), handoff.to_dict()


def test_new_contracts_validate_and_packaged_copies_are_identical():
    names = [
        "edit-plan.schema.json",
        "resolve-assembly-plan.schema.json",
        "render-qa-report.schema.json",
        "editor-handoff-manifest.schema.json",
    ]
    for document, name in zip(docs(), names, strict=True):
        canonical = Path("schemas") / name
        validate_instance(document, canonical)
        packaged = resources.files("ai_video_production").joinpath("schema_resources", name).read_text(encoding="utf-8")
        assert packaged == canonical.read_text(encoding="utf-8")
