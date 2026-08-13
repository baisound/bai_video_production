from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from ai_video_production.desktop_editing_application import Task036EditingApplication
from ai_video_production.desktop_resolve_workflow import Task036ResolveWorkflowFacade
from ai_video_production.errors import ProductError
from ai_video_production.resolve_assembly import ResolveAssemblyResult, ResolveAssetBindings
from ai_video_production.timebase import FrameRate


H = lambda ch: "sha256:" + ch * 64


def application() -> Task036EditingApplication:
    manifest = CutCandidateManifest(
        source_asset_id="ASSET-00000000000000000000000000",
        analysis_audio_sha256=H("1"),
        analysis_sample_rate=48_000,
        source_duration_us=10_000_000,
        config_sha256=H("2"),
        transcript_manifest_sha256=H("3"),
        candidates=(CutCandidate("cut-000001", CutCandidateKind.SILENCE, 1_000_000, 2_000_000, 90, ("SILENCE",)),),
        keep_blocks=(),
    )
    values = iter(("review", "approve", "resolve"))
    app = Task036EditingApplication.create(
        product_version="0.19.0",
        project_id="project-1",
        display_name="DbD 朝活",
        source_asset_sha256=H("4"),
        cut_manifest=manifest,
        token_factory=lambda: next(values),
    )
    app.review_candidate(candidate_id="cut-000001", decision="CUT")
    prepared = app.prepare_edit_plan_approval()
    app.approve_edit_plan(
        confirmation_id=prepared["confirmation_id"],
        draft_plan_sha256=prepared["draft_plan_sha256"],
        approved_by="owner",
    )
    return app


class FakeAdapter:
    def __init__(self):
        self.hash = None
        self.calls = 0

    def applied_hash(self, timeline_name):
        return self.hash

    def assemble(self, plan, bindings):
        self.calls += 1
        self.hash = plan.to_dict()["assembly_sha256"]
        return ResolveAssemblyResult(self.hash, plan.timeline_name, "APPLIED", False, "SKIPPED", "SKIPPED")


def test_prepare_compile_is_non_mutating_and_advances_to_apply_stage():
    app = application()
    facade = Task036ResolveWorkflowFacade(app)
    result = facade.compile_assembly(timeline_rate=FrameRate(30))
    assert result["external_mutation_performed"] is False
    assert result["assembly_plan"]["timeline_name"].startswith("BAI_AUTO_")
    assert "resolve.assembly.apply" in result["available_commands"]
    assert "render.start" not in result["available_commands"]


def test_apply_requires_exact_prepared_automation_timeline():
    app = application()
    facade = Task036ResolveWorkflowFacade(app)
    result = facade.compile_assembly(timeline_rate=FrameRate(30))
    with pytest.raises(ProductError) as exc:
        facade.prepare_apply(target_project="sandbox", target_timeline="Human Timeline")
    assert exc.value.code == "ERR_SHELL_RESOLVE_TARGET_INVALID"
    assert result["assembly_plan"]["timeline_name"] != "Human Timeline"


def test_target_change_after_confirmation_is_rejected_before_adapter_call(tmp_path: Path):
    app = application()
    facade = Task036ResolveWorkflowFacade(app)
    compiled = facade.compile_assembly(timeline_rate=FrameRate(30))
    timeline = compiled["assembly_plan"]["timeline_name"]
    prepared = facade.prepare_apply(target_project="sandbox-A", target_timeline=timeline)
    adapter = FakeAdapter()
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    with pytest.raises(ProductError) as exc:
        facade.apply(
            confirmation_id=prepared["confirmation_id"],
            target_project="sandbox-B",
            target_timeline=timeline,
            adapter=adapter,
            bindings=ResolveAssetBindings(source, FrameRate(30)),
        )
    assert exc.value.code == "ERR_SHELL_CONFIRMATION_STALE"
    assert adapter.calls == 0


def test_confirmed_apply_uses_task010_contract_and_advances_to_render(tmp_path: Path):
    app = application()
    facade = Task036ResolveWorkflowFacade(app)
    compiled = facade.compile_assembly(timeline_rate=FrameRate(30))
    timeline = compiled["assembly_plan"]["timeline_name"]
    prepared = facade.prepare_apply(target_project="sandbox", target_timeline=timeline)
    adapter = FakeAdapter()
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    result = facade.apply(
        confirmation_id=prepared["confirmation_id"],
        target_project="sandbox",
        target_timeline=timeline,
        adapter=adapter,
        bindings=ResolveAssetBindings(source, FrameRate(30)),
    )
    assert adapter.calls == 1
    assert result["editing_session"]["resolve_applied"] is True
    assert "render.start" in result["available_commands"]
    assert result["next_recommended_action"] == "render.start"


def test_confirmation_is_one_shot_even_when_task010_apply_is_idempotent(tmp_path: Path):
    app = application()
    facade = Task036ResolveWorkflowFacade(app)
    compiled = facade.compile_assembly(timeline_rate=FrameRate(30))
    timeline = compiled["assembly_plan"]["timeline_name"]
    prepared = facade.prepare_apply(target_project="sandbox", target_timeline=timeline)
    adapter = FakeAdapter()
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    bindings = ResolveAssetBindings(source, FrameRate(30))
    facade.apply(
        confirmation_id=prepared["confirmation_id"],
        target_project="sandbox",
        target_timeline=timeline,
        adapter=adapter,
        bindings=bindings,
    )
    with pytest.raises(ProductError) as exc:
        facade.apply(
            confirmation_id=prepared["confirmation_id"],
            target_project="sandbox",
            target_timeline=timeline,
            adapter=adapter,
            bindings=bindings,
        )
    assert exc.value.code in {"ERR_SHELL_CONTEXT_STALE", "ERR_SHELL_CONFIRMATION_INVALID", "ERR_SHELL_COMMAND_NOT_AVAILABLE_IN_STAGE"}


def test_prepare_apply_binds_resolve_target_into_shell_context():
    app = application()
    facade = Task036ResolveWorkflowFacade(app)
    compiled = facade.compile_assembly(timeline_rate=FrameRate(30))
    timeline = compiled["assembly_plan"]["timeline_name"]
    facade.prepare_apply(target_project="sandbox", target_timeline=timeline)
    assert app.shell.project.resolve_project_name == "sandbox"
    assert app.shell.project.resolve_timeline_name == timeline
