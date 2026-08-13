from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from ai_video_production.desktop_editing_application import Task036EditingApplication
from ai_video_production.desktop_post_resolve_workflow import Task036PostResolveWorkflowFacade
from ai_video_production.desktop_resolve_workflow import Task036ResolveWorkflowFacade
from ai_video_production.errors import ProductError
from ai_video_production.media_probe import MediaProbeResult
from ai_video_production.render_qa import LoudnessMeasurement, LoudnessProfile, RenderQAService
from ai_video_production.resolve_assembly import ResolveAssemblyResult, ResolveAssetBindings
from ai_video_production.timebase import FrameRate


H = lambda ch: "sha256:" + ch * 64


class FakeProbe:
    def __init__(self, duration_us): self.duration_us = duration_us
    def probe(self, path):
        return MediaProbeResult(
            "mp4", self.duration_us, Path(path).stat().st_size, None,
            ({"codec_type":"video","codec_name":"h264"},{"codec_type":"audio","codec_name":"aac"}),
        )


class FakeLoudness:
    def analyze(self, path, *, profile): return LoudnessMeasurement(-16.0, -2.0, 4.0)


class FakeAdapter:
    def __init__(self): self.hash = None
    def applied_hash(self, timeline_name): return self.hash
    def assemble(self, plan, bindings):
        self.hash = plan.to_dict()["assembly_sha256"]
        return ResolveAssemblyResult(self.hash, plan.timeline_name, "APPLIED", False, "SKIPPED", "SKIPPED")


def workflow(tmp_path: Path):
    manifest = CutCandidateManifest(
        source_asset_id="ASSET-00000000000000000000000000",
        analysis_audio_sha256=H("1"), analysis_sample_rate=48_000,
        source_duration_us=4_000_000, config_sha256=H("2"), transcript_manifest_sha256=H("3"),
        candidates=(CutCandidate("cut-000001", CutCandidateKind.SILENCE, 1_000_000, 2_000_000, 90, ("SILENCE",)),),
        keep_blocks=(),
    )
    values = iter(("review", "approve", "resolve"))
    app = Task036EditingApplication.create(
        product_version="0.19.0", project_id="project-1", display_name="DbD 朝活",
        source_asset_sha256=H("4"), cut_manifest=manifest, token_factory=lambda: next(values),
    )
    app.review_candidate(candidate_id="cut-000001", decision="CUT")
    prepared = app.prepare_edit_plan_approval()
    app.approve_edit_plan(confirmation_id=prepared["confirmation_id"], draft_plan_sha256=prepared["draft_plan_sha256"], approved_by="owner")
    resolve = Task036ResolveWorkflowFacade(app)
    compiled = resolve.compile_assembly(timeline_rate=FrameRate(30))
    timeline = compiled["assembly_plan"]["timeline_name"]
    confirmation = resolve.prepare_apply(target_project="sandbox", target_timeline=timeline)
    source = tmp_path / "source.mp4"; source.write_bytes(b"source")
    resolve.apply(
        confirmation_id=confirmation["confirmation_id"], target_project="sandbox", target_timeline=timeline,
        adapter=FakeAdapter(), bindings=ResolveAssetBindings(source, FrameRate(30)),
    )
    return app, resolve


def passing_report(tmp_path: Path, resolve: Task036ResolveWorkflowFacade):
    assert resolve.assembly_plan is not None
    rate = resolve.assembly_plan.timeline_mapping.timeline_rate
    expected = resolve.assembly_plan.expected_duration_frames
    duration_us = int(round(expected * 1_000_000 * rate.denominator / rate.numerator))
    render = tmp_path / "render.mp4"; render.write_bytes(b"render-bytes")
    service = RenderQAService(media_probe=FakeProbe(duration_us), loudness_analyzer=FakeLoudness())
    report = service.verify(
        render, expected_duration_frames=expected, timeline_rate=rate,
        duration_tolerance_frames=2,
        loudness_profile=LoudnessProfile(target_lufs=-16.0, tolerance_lu=1.0, max_true_peak_dbtp=-1.0),
    )
    assert report.status == "PASS"
    return render, report


def test_native_render_request_is_exact_and_non_mutating(tmp_path: Path):
    app, resolve = workflow(tmp_path)
    facade = Task036PostResolveWorkflowFacade(app, resolve)
    request = facade.prepare_native_render_gate()
    assert request["status"] == "READY_FOR_REAL_RESOLVE_NATIVE_GATE"
    assert request["sandbox_project"] == "sandbox"
    assert request["timeline_name"].startswith("BAI_AUTO_")
    assert request["external_mutation_performed"] is False


def test_pass_render_qa_advances_to_handoff(tmp_path: Path):
    app, resolve = workflow(tmp_path)
    render, report = passing_report(tmp_path, resolve)
    facade = Task036PostResolveWorkflowFacade(app, resolve)
    result = facade.bind_render_qa(report)
    assert result["qa_status"] == "PASS"
    assert "handoff.create" in result["available_commands"]
    assert result["next_recommended_action"] == "handoff.create"


def test_mismatched_render_contract_is_rejected(tmp_path: Path):
    app, resolve = workflow(tmp_path)
    render, report = passing_report(tmp_path, resolve)
    # Rebuild a valid report at another rate; it must not bind to this assembly.
    other = RenderQAService(media_probe=FakeProbe(1_000_000), loudness_analyzer=FakeLoudness()).verify(
        render, expected_duration_frames=24, timeline_rate=FrameRate(24),
        duration_tolerance_frames=2,
        loudness_profile=LoudnessProfile(target_lufs=-16.0, tolerance_lu=1.0, max_true_peak_dbtp=-1.0),
    )
    facade = Task036PostResolveWorkflowFacade(app, resolve)
    with pytest.raises(ProductError) as exc:
        facade.bind_render_qa(other)
    assert exc.value.code in {"ERR_SHELL_RENDER_QA_DURATION_CONTRACT_MISMATCH", "ERR_SHELL_RENDER_QA_RATE_CONTRACT_MISMATCH"}


def test_editor_work_creation_is_wired_and_marks_handoff_complete(tmp_path: Path):
    app, resolve = workflow(tmp_path)
    render, report = passing_report(tmp_path, resolve)
    facade = Task036PostResolveWorkflowFacade(app, resolve)
    facade.bind_render_qa(report)
    destination = tmp_path / "handoffs"; destination.mkdir()
    result = facade.create_editor_handoff(destination, render_qa=report, render_path=render)
    root = Path(result["runtime_editor_work_root"])
    assert root.is_dir()
    assert (root / "editor-handoff-manifest.json").is_file()
    assert result["editing_session"]["current_stage"] == "HANDOFF"
    assert result["next_recommended_action"] == "NONE"
