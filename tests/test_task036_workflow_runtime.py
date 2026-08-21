from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from ai_video_production.desktop_editing_application import Task036EditingApplication
from ai_video_production.desktop_post_resolve_workflow import Task036PostResolveWorkflowFacade
from ai_video_production.desktop_resolve_workflow import Task036ResolveWorkflowFacade
from ai_video_production.errors import ProductError
from ai_video_production.durable_product_job import DurableProductJob, DurableProductJobState
from ai_video_production.export_queue import (
    ExportAuthorityClass,
    ExportOutputContract,
    ExportPreparation,
    ExportPreset,
)
from ai_video_production.final_review import FinalReviewApprovalReceipt
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


class ExportNativeRenderPort:
    destination_label = "render-output"

    def __init__(self, destination: Path):
        self.destination = destination
        self.calls = 0

    def execute(self, **kwargs):
        self.calls += 1
        self.destination.mkdir(parents=True, exist_ok=True)
        artifact = self.destination / "master.mp4"
        artifact.write_bytes(b"synthetic-offline-export-bytes")
        digest = "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest()
        report = RenderQAReport(
            digest,
            artifact.stat().st_size,
            MediaProbeResult(
                "mov,mp4,m4a,3gp,3g2,mj2",
                4_000_000,
                artifact.stat().st_size,
                None,
                (
                    {
                        "codec_type": "video", "codec_name": "h264",
                        "width": 1920, "height": 1080, "avg_frame_rate": "30/1",
                    },
                    {
                        "codec_type": "audio", "codec_name": "aac",
                        "sample_rate": 48000, "channels": 2,
                    },
                ),
            ),
            None,
            None,
            kwargs["expected_duration_frames"],
            kwargs["timeline_rate"],
            2,
            ({"check": "synthetic-offline", "status": "PASS"},),
        )
        return NativeRenderCompletion(report, artifact, H("8"))


def _export_preparation(value: Task036WorkflowRuntime) -> ExportPreparation:
    plan = value.resolve.assembly_plan
    assert plan is not None
    receipt = FinalReviewApprovalReceipt(
        receipt_id="FINAL-RUNTIME-EXPORT",
        project_id="project-1",
        project_manifest_sha256=H("6"),
        timeline_sha256=H("7"),
        readiness_projection_sha256=H("8"),
        source_snapshot_sha256s=(
            ("audit", H("1")), ("production", H("2")),
            ("project_manifest", H("6")), ("timeline", H("7")),
            ("visual_handoff", H("3")),
        ),
        external_gate_receipt_sha256s=(
            ("AUDIO_COMPLETION", H("4")), ("EDIT_PERSISTENCE", H("5")),
            ("PRIVACY", H("6")), ("RESOURCE", H("7")),
            ("RIGHTS_LICENSE", H("8")),
        ),
        approved_by="owner",
        approved_at="2026-08-21T00:00:00.000Z",
    )
    return ExportPreparation(
        project_id="project-1",
        project_manifest_sha256=H("6"),
        product_version="0.22.0",
        timeline_plan_id="timeline-main",
        timeline_revision=1,
        timeline_sha256=H("7"),
        edit_plan_sha256=plan.source_edit_plan_sha256,
        assembly_plan_sha256=plan.to_dict()["assembly_sha256"],
        final_approval=receipt,
        preset=ExportPreset(
            "preset-synthetic-offline", "1.0.0",
            ExportOutputContract(1920, 1080, 30, 1, 48000, 2, "mp4", "h264", "aac"),
        ),
        output_target_identity="export:master",
        authority_class=ExportAuthorityClass.RESOLVE_RENDER,
        resolve_project_identity=value.target_project,
        resolve_timeline_identity=plan.timeline_name,
    )


def test_queue_confirmed_export_reuses_native_port_and_validates_exact_output(tmp_path: Path):
    value, _adapter = runtime(tmp_path)
    value.compile_resolve_assembly()
    applied = value.prepare_resolve_apply()
    value.apply_resolve_assembly(str(applied["confirmation_id"]))
    destination = tmp_path / "render-output"
    native = ExportNativeRenderPort(destination)
    value.native_render_port = native
    preparation = _export_preparation(value)
    job = DurableProductJob.create(
        kind="EXPORT", target_identity=preparation.output_target_identity,
        input_hashes=preparation.input_hashes,
        created_at="2026-08-21T00:00:01.000Z",
    )
    job = job.transition(DurableProductJobState.PREFLIGHT, updated_at="2026-08-21T00:00:02.000Z")
    job = job.transition(DurableProductJobState.READY, updated_at="2026-08-21T00:00:03.000Z")
    job = job.transition(DurableProductJobState.DISPATCHING, updated_at="2026-08-21T00:00:04.000Z")
    result = value.dispatch_export(job, preparation, destination)
    artifact = destination / "master.mp4"
    expected = hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert result.state == "SUCCEEDED"
    assert result.result_identity == "render-artifact:" + expected
    assert result.render_qa_sha256 == value.render_qa.to_dict()["report_sha256"]
    assert value.render_path == artifact
    assert native.calls == 1


def test_queue_confirmed_export_rejects_media_contract_mismatch(tmp_path: Path):
    value, _adapter = runtime(tmp_path)
    value.compile_resolve_assembly()
    applied = value.prepare_resolve_apply()
    value.apply_resolve_assembly(str(applied["confirmation_id"]))
    destination = tmp_path / "render-output"
    native = ExportNativeRenderPort(destination)
    value.native_render_port = native
    preparation = _export_preparation(value)
    bad = replace(
        preparation,
        preset=ExportPreset(
            "preset-wrong-size", "1.0.0",
            ExportOutputContract(3840, 2160, 30, 1, 48000, 2, "mp4", "h264", "aac"),
        ),
    )
    job = DurableProductJob.create(
        kind="EXPORT", target_identity=bad.output_target_identity,
        input_hashes=bad.input_hashes, created_at="2026-08-21T00:00:01.000Z",
    )
    job = job.transition(DurableProductJobState.PREFLIGHT, updated_at="2026-08-21T00:00:02.000Z")
    job = job.transition(DurableProductJobState.READY, updated_at="2026-08-21T00:00:03.000Z")
    job = job.transition(DurableProductJobState.DISPATCHING, updated_at="2026-08-21T00:00:04.000Z")
    with pytest.raises(ProductError) as exc:
        value.dispatch_export(job, bad, destination)
    assert exc.value.code == "ERR_TASK036_EXPORT_OUTPUT_CONTRACT"
