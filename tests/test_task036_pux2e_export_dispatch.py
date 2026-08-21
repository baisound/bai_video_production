from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.durable_product_job import DurableProductJobState, DurableProductJobStore
from ai_video_production.errors import ProductError
from ai_video_production.export_queue import (
    ExportAuthorityClass,
    ExportDispatchResult,
    ExportOutputContract,
    ExportPreparation,
    ExportPreset,
)
from ai_video_production.export_queue_application import ExportQueueApplication
from ai_video_production.final_review import FinalReviewApprovalReceipt
from ai_video_production.interactive_timeline import (
    InteractiveTimeline,
    TimelineMediaKind,
    TimelineTrack,
    TimelineTrackRole,
)
from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.task036_shell_ui import Task036ShellBridge
from ai_video_production.task044_nle_shell import Task044NleShellController
from ai_video_production.timebase import FrameRate


def h(char: str) -> str:
    return "sha256:" + char * 64


def setup(root: Path):
    root.mkdir()
    manifest = ProductProjectManifest.create(
        project_id="project-1",
        project_revision=1,
        product_version="0.22.0",
        timebase=ProjectTimebase(30, 1),
        child_bindings=(),
        created_at="2026-08-21T00:00:00.000Z",
        updated_at="2026-08-21T00:00:00.000Z",
    )
    ProductProjectManifestStore.save(root, manifest)
    receipt = FinalReviewApprovalReceipt(
        receipt_id="FINAL-EXPORT-DISPATCH-1",
        project_id="project-1",
        project_manifest_sha256=manifest.project_manifest_sha256,
        timeline_sha256=h("1"),
        readiness_projection_sha256=h("2"),
        source_snapshot_sha256s=(
            ("audit", h("3")),
            ("production", h("4")),
            ("project_manifest", manifest.project_manifest_sha256),
            ("timeline", h("1")),
            ("visual_handoff", h("5")),
        ),
        external_gate_receipt_sha256s=(
            ("AUDIO_COMPLETION", h("6")),
            ("EDIT_PERSISTENCE", h("7")),
            ("PRIVACY", h("8")),
            ("RESOURCE", h("9")),
            ("RIGHTS_LICENSE", h("a")),
        ),
        approved_by="owner",
        approved_at="2026-08-21T00:01:00.000Z",
    )
    preparation = ExportPreparation(
        project_id="project-1",
        project_manifest_sha256=manifest.project_manifest_sha256,
        product_version=manifest.product_version,
        timeline_plan_id="timeline-main",
        timeline_revision=1,
        timeline_sha256=h("1"),
        edit_plan_sha256=h("b"),
        assembly_plan_sha256=h("c"),
        final_approval=receipt,
        preset=ExportPreset(
            "preset-offline",
            "1.0.0",
            ExportOutputContract(1920, 1080, 30, 1, 48000, 2, "mp4", "h264", "aac"),
        ),
        output_target_identity="export:master",
        authority_class=ExportAuthorityClass.LOCAL_PACKAGE,
    )
    application = ExportQueueApplication(
        project_root=root, project_id="project-1", token_factory=lambda: "dispatch-confirmation",
    )
    job = application.enqueue(preparation)
    timeline = InteractiveTimeline(
        "project-1",
        "timeline-main",
        FrameRate(30),
        30,
        (TimelineTrack("V1", 0, TimelineTrackRole.VIDEO, TimelineMediaKind.VIDEO, "Video", True),),
        (),
    )
    return application, preparation, job, timeline


def shell_for(
    application: ExportQueueApplication,
    preparation: ExportPreparation,
    timeline: InteractiveTimeline,
    dispatcher,
    destination: Path,
) -> Task036ShellBridge:
    service = ShellApplicationService(product_version="0.22.0")
    service.open_project_context(project_id="project-1", display_name="Project 1")
    controller = Task044NleShellController(
        timeline=timeline,
        export_application=application,
        export_preparation_provider=lambda _job_id: preparation,
        export_destination_provider=lambda _job_id, _preparation: destination,
        export_dispatcher=dispatcher,
    )
    return Task036ShellBridge(service, nle_controller=controller)


def test_shell_preflight_confirmation_and_dispatch_update_same_job_without_path(tmp_path: Path) -> None:
    application, preparation, queued, timeline = setup(tmp_path / "project")
    observed = []

    def dispatch(job, exact, destination):
        observed.append((job.state, exact.preparation_sha256, destination))
        return ExportDispatchResult(
            "SUCCEEDED", "render-artifact:" + "d" * 64, h("e"), True,
        )

    shell = shell_for(application, preparation, timeline, dispatch, tmp_path / "private-output")
    preflight = shell.export_queue_preflight({"job_id": queued.job_id})
    assert preflight["state"] == "READY"
    prepared = shell.export_queue_prepare_dispatch({"job_id": queued.job_id})
    with pytest.raises(ProductError) as exc:
        shell.export_queue_apply_dispatch({
            "confirmation_id": prepared["confirmation_id"],
            "destination": "C:/injected.mp4",
        })
    assert exc.value.code == "ERR_NLE_SHELL_REQUEST_INVALID"
    completed = shell.export_queue_apply_dispatch({
        "confirmation_id": prepared["confirmation_id"],
    })
    assert completed["state"] == "SUCCEEDED"
    assert completed["result_identity"] == "render-artifact:" + "d" * 64
    assert completed["render_qa_sha256"] == h("e")
    assert completed["host_output_path_persisted"] is False
    assert str(tmp_path) not in str(completed)
    assert observed == [(
        DurableProductJobState.DISPATCHING,
        preparation.preparation_sha256,
        tmp_path / "private-output",
    )]
    stored = DurableProductJobStore.load(tmp_path / "project").get(queued.job_id)
    assert stored.state is DurableProductJobState.SUCCEEDED
    with pytest.raises(ProductError) as replay:
        shell.export_queue_apply_dispatch({"confirmation_id": prepared["confirmation_id"]})
    assert replay.value.code == "ERR_EXPORT_CONFIRMATION_INVALID"


def test_shell_dispatch_cancel_keeps_ready_job_and_consumes_confirmation(tmp_path: Path) -> None:
    application, preparation, queued, timeline = setup(tmp_path / "project")
    calls = []
    shell = shell_for(
        application, preparation, timeline,
        lambda *_args: calls.append(True) or ExportDispatchResult("RUNNING"),
        tmp_path / "private-output",
    )
    shell.export_queue_preflight({"job_id": queued.job_id})
    prepared = shell.export_queue_prepare_dispatch({"job_id": queued.job_id})
    cancelled = shell.export_queue_cancel_dispatch({
        "confirmation_id": prepared["confirmation_id"],
    })
    assert cancelled["cancelled"] is True
    assert DurableProductJobStore.load(tmp_path / "project").get(queued.job_id).state is DurableProductJobState.READY
    assert calls == []


def test_private_destination_failure_consumes_both_confirmation_layers(tmp_path: Path) -> None:
    application, preparation, queued, timeline = setup(tmp_path / "project")
    service = ShellApplicationService(product_version="0.22.0")
    service.open_project_context(project_id="project-1", display_name="Project 1")

    def unavailable_destination(_job_id, _preparation):
        raise RuntimeError("private destination unavailable")

    controller = Task044NleShellController(
        timeline=timeline,
        export_application=application,
        export_preparation_provider=lambda _job_id: preparation,
        export_destination_provider=unavailable_destination,
        export_dispatcher=lambda *_args: ExportDispatchResult("RUNNING"),
    )
    shell = Task036ShellBridge(service, nle_controller=controller)
    shell.export_queue_preflight({"job_id": queued.job_id})
    prepared = shell.export_queue_prepare_dispatch({"job_id": queued.job_id})
    with pytest.raises(RuntimeError, match="destination unavailable"):
        shell.export_queue_apply_dispatch({"confirmation_id": prepared["confirmation_id"]})
    with pytest.raises(ProductError) as exc:
        application.cancel_dispatch(confirmation_id=str(prepared["confirmation_id"]))
    assert exc.value.code == "ERR_EXPORT_CONFIRMATION_INVALID"
    assert DurableProductJobStore.load(tmp_path / "project").get(queued.job_id).state is DurableProductJobState.READY


def test_dispatch_reconstructs_preparation_and_consumes_stale_confirmation(tmp_path: Path) -> None:
    application, preparation, queued, timeline = setup(tmp_path / "project")
    current = preparation
    service = ShellApplicationService(product_version="0.22.0")
    service.open_project_context(project_id="project-1", display_name="Project 1")
    controller = Task044NleShellController(
        timeline=timeline, export_application=application,
        export_preparation_provider=lambda _job_id: current,
        export_destination_provider=lambda _job_id, _preparation: tmp_path / "private-output",
        export_dispatcher=lambda *_args: ExportDispatchResult("RUNNING"),
    )
    shell = Task036ShellBridge(service, nle_controller=controller)
    shell.export_queue_preflight({"job_id": queued.job_id})
    confirmation = shell.export_queue_prepare_dispatch({"job_id": queued.job_id})
    current = replace(preparation, output_target_identity="export:changed-after-confirmation")
    with pytest.raises(ProductError) as exc:
        shell.export_queue_apply_dispatch({"confirmation_id": confirmation["confirmation_id"]})
    assert exc.value.code == "ERR_NLE_SHELL_EXPORT_CONFIRMATION_STALE"
    with pytest.raises(ProductError) as consumed:
        application.cancel_dispatch(confirmation_id=str(confirmation["confirmation_id"]))
    assert consumed.value.code == "ERR_EXPORT_CONFIRMATION_INVALID"
    assert DurableProductJobStore.load(tmp_path / "project").get(queued.job_id).state is DurableProductJobState.READY


def test_private_destination_is_bound_per_job_for_sequential_dispatches(tmp_path: Path) -> None:
    application, first_preparation, first_job, timeline = setup(tmp_path / "project")
    second_receipt = replace(first_preparation.final_approval, receipt_id="FINAL-EXPORT-DISPATCH-2")
    second_preparation = replace(
        first_preparation, final_approval=second_receipt,
        output_target_identity="export:second",
    )
    second_job = application.enqueue(second_preparation)
    preparations = {
        first_job.job_id: first_preparation,
        second_job.job_id: second_preparation,
    }
    destinations: list[Path] = []
    controller = Task044NleShellController(
        timeline=timeline, export_application=application,
        export_preparation_provider=lambda job_id: preparations[job_id],
        export_destination_provider=lambda job_id, _preparation: (
            tmp_path / "private-output" / job_id
        ),
        export_dispatcher=lambda _job, _preparation, destination: (
            destinations.append(destination)
            or ExportDispatchResult("SUCCEEDED", "render-artifact:" + "f" * 64, h("e"), True)
        ),
    )
    service = ShellApplicationService(product_version="0.22.0")
    service.open_project_context(project_id="project-1", display_name="Project 1")
    shell = Task036ShellBridge(service, nle_controller=controller)
    for job in (first_job, second_job):
        shell.export_queue_preflight({"job_id": job.job_id})
        confirmation = shell.export_queue_prepare_dispatch({"job_id": job.job_id})
        assert shell.export_queue_apply_dispatch({"confirmation_id": confirmation["confirmation_id"]})["state"] == "SUCCEEDED"
    assert destinations == [
        tmp_path / "private-output" / first_job.job_id,
        tmp_path / "private-output" / second_job.job_id,
    ]


def test_dispatch_crash_recovers_unknown_without_automatic_replay(tmp_path: Path) -> None:
    root = tmp_path / "project"
    application, preparation, queued, timeline = setup(root)
    calls = 0

    def crash(*_args):
        nonlocal calls
        calls += 1
        raise RuntimeError("synthetic renderer disappeared")

    shell = shell_for(application, preparation, timeline, crash, tmp_path / "private-output")
    shell.export_queue_preflight({"job_id": queued.job_id})
    prepared = shell.export_queue_prepare_dispatch({"job_id": queued.job_id})
    with pytest.raises(RuntimeError, match="disappeared"):
        shell.export_queue_apply_dispatch({"confirmation_id": prepared["confirmation_id"]})
    assert DurableProductJobStore.load(root).get(queued.job_id).state is DurableProductJobState.DISPATCHING
    restarted = ExportQueueApplication(project_root=root, project_id="project-1")
    recovered = restarted.recover_interrupted_on_startup()
    assert recovered[0].state is DurableProductJobState.UNKNOWN
    assert recovered[0].recovery_actions == (
        "ACCEPT_PROVEN_SUCCESS", "MARK_FAILED", "REQUIRE_HUMAN",
    )
    assert calls == 1
