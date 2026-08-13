from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from ai_video_production.desktop_editing_application import Task036EditingApplication
from ai_video_production.desktop_post_resolve_workflow import Task036PostResolveWorkflowFacade
from ai_video_production.desktop_resolve_workflow import Task036ResolveWorkflowFacade
from ai_video_production.errors import ProductError
from ai_video_production.media_probe import MediaProbeResult
from ai_video_production.render_qa import RenderQAReport
from ai_video_production.resolve_assembly import ResolveAssemblyResult, ResolveAssetBindings
from ai_video_production.task036_native_render_port import NativeRenderCompletion
from ai_video_production.task036_shell_ui import Task036ShellBridge
from ai_video_production.task036_workflow_runtime import Task036WorkflowRuntime
from ai_video_production.timebase import FrameRate


H = lambda ch: "sha256:" + ch * 64


class Adapter:
    def __init__(self):
        self.hash = None
        self.calls = 0

    def applied_hash(self, timeline_name):
        return self.hash

    def assemble(self, plan, bindings):
        self.calls += 1
        self.hash = plan.to_dict()["assembly_sha256"]
        return ResolveAssemblyResult(self.hash, plan.timeline_name, "APPLIED", False, "SKIPPED", "SKIPPED")


class NativeRenderPort:
    destination_label = "phase-g-native-render"

    def __init__(self, tmp_path: Path):
        self.tmp_path = tmp_path
        self.calls = []

    def execute(self, **kwargs):
        self.calls.append(kwargs)
        render = self.tmp_path / "render.mp4"
        render.write_bytes(b"render")
        report = RenderQAReport(
            H("9"),
            render.stat().st_size,
            MediaProbeResult(
                "mp4",
                3_000_000,
                render.stat().st_size,
                None,
                ({"codec_type": "video"}, {"codec_type": "audio"}),
            ),
            None,
            None,
            kwargs["expected_duration_frames"],
            kwargs["timeline_rate"],
            2,
            ({"check": "fixture", "status": "PASS"},),
        )
        return NativeRenderCompletion(report, render, H("8"))


def runtime(tmp_path: Path):
    manifest = CutCandidateManifest(
        "ASSET-00000000000000000000000000", H("1"), 48_000, 4_000_000, H("2"), H("3"),
        (CutCandidate("cut-000001", CutCandidateKind.SILENCE, 1_000_000, 2_000_000, 90, ("SILENCE",)),), (),
    )
    tokens = iter(("review", "approve", "resolve", "render"))
    app = Task036EditingApplication.create(
        product_version="0.19.0", project_id="project-1", display_name="Sandbox",
        source_asset_sha256=H("4"), cut_manifest=manifest, token_factory=lambda: next(tokens),
    )
    app.review_candidate(candidate_id="cut-000001", decision="CUT")
    approval = app.prepare_edit_plan_approval()
    app.approve_edit_plan(
        confirmation_id=approval["confirmation_id"], draft_plan_sha256=approval["draft_plan_sha256"], approved_by="owner",
    )
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    resolve = Task036ResolveWorkflowFacade(app)
    post = Task036PostResolveWorkflowFacade(app, resolve)
    adapter = Adapter()
    value = Task036WorkflowRuntime(
        app,
        resolve,
        post,
        adapter,
        ResolveAssetBindings(source, FrameRate(30)),
        FrameRate(30),
        "BAI_PHASE_G_SANDBOX",
    )
    return value, adapter


def test_bridge_wires_fixed_runtime_target_through_one_shot_resolve_apply(tmp_path: Path):
    value, adapter = runtime(tmp_path)
    bridge = Task036ShellBridge(value.application.shell, application=value.application, workflow_runtime=value)
    assert bridge.workflow_status({})["next_recommended_action"] == "resolve.assembly.prepare"
    compiled = bridge.compile_resolve_assembly({})
    assert compiled["external_mutation_performed"] is False
    prepared = bridge.prepare_resolve_apply({})
    assert prepared["target_project"] == "BAI_PHASE_G_SANDBOX"
    result = bridge.apply_resolve_assembly({"confirmation_id": prepared["confirmation_id"]})
    assert adapter.calls == 1
    assert result["editing_session"]["resolve_applied"] is True
    assert bridge.workflow_status()["next_recommended_action"] == "render.start"


def test_bridge_never_accepts_adapter_target_or_host_path_from_javascript(tmp_path: Path):
    value, adapter = runtime(tmp_path)
    bridge = Task036ShellBridge(value.application.shell, application=value.application, workflow_runtime=value)
    bridge.compile_resolve_assembly()
    prepared = bridge.prepare_resolve_apply()
    with pytest.raises(ProductError) as exc:
        bridge.apply_resolve_assembly({
            "confirmation_id": prepared["confirmation_id"],
            "target_project": "HumanProject",
            "source_path": "C:/arbitrary.mp4",
        })
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"
    assert adapter.calls == 0


def test_unbound_runtime_is_visible_but_fails_closed():
    manifest = CutCandidateManifest(
        "ASSET-00000000000000000000000000", H("1"), 48_000, 4_000_000, H("2"), H("3"), (), (),
    )
    app = Task036EditingApplication.create(
        product_version="0.19.0", project_id="project-1", display_name="Sandbox",
        source_asset_sha256=H("4"), cut_manifest=manifest,
    )
    bridge = Task036ShellBridge(app.shell, application=app)
    assert bridge.workflow_status() == {"available": False}
    with pytest.raises(ProductError) as exc:
        bridge.compile_resolve_assembly()
    assert exc.value.code == "ERR_TASK036_WORKFLOW_RUNTIME_NOT_BOUND"


def test_native_render_uses_exact_one_shot_confirmation_and_binds_qa(tmp_path: Path):
    value, adapter = runtime(tmp_path)
    native = NativeRenderPort(tmp_path)
    value.native_render_port = native
    bridge = Task036ShellBridge(value.application.shell, application=value.application, workflow_runtime=value)
    bridge.compile_resolve_assembly()
    apply_confirmation = bridge.prepare_resolve_apply()
    bridge.apply_resolve_assembly({"confirmation_id": apply_confirmation["confirmation_id"]})

    prepared = bridge.prepare_native_render_confirmation({})
    assert prepared["target_project"] == "BAI_PHASE_G_SANDBOX"
    assert prepared["target_timeline"].startswith("BAI_AUTO_")
    assert prepared["destination"] == "phase-g-native-render"
    result = bridge.execute_native_render({"confirmation_id": prepared["confirmation_id"]})

    assert len(native.calls) == 1
    assert result["external_mutation_performed"] is True
    assert result["render_artifact_path_persisted"] is False
    assert value.render_path == tmp_path / "render.mp4"
    assert value.render_qa is not None
    assert bridge.workflow_status()["next_recommended_action"] == "handoff.create"

    with pytest.raises(ProductError) as exc:
        bridge.execute_native_render({"confirmation_id": prepared["confirmation_id"]})
    assert exc.value.code in {"ERR_SHELL_COMMAND_NOT_AVAILABLE_IN_STAGE", "ERR_SHELL_CONFIRMATION_INVALID"}


def test_native_render_bridge_rejects_javascript_target_or_destination(tmp_path: Path):
    value, _ = runtime(tmp_path)
    value.native_render_port = NativeRenderPort(tmp_path)
    bridge = Task036ShellBridge(value.application.shell, application=value.application, workflow_runtime=value)
    bridge.compile_resolve_assembly()
    apply_confirmation = bridge.prepare_resolve_apply()
    bridge.apply_resolve_assembly({"confirmation_id": apply_confirmation["confirmation_id"]})
    prepared = bridge.prepare_native_render_confirmation()
    with pytest.raises(ProductError) as exc:
        bridge.execute_native_render(
            {
                "confirmation_id": prepared["confirmation_id"],
                "target_project": "HumanProject",
                "destination": "C:/arbitrary",
            }
        )
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"
    assert value.native_render_port.calls == []
