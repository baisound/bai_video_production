from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.desktop_shell import CommandCategory, ShellApplicationService
from ai_video_production.durable_product_job import (
    DurableProductJobService, DurableProductJobState, DurableProductJobStore,
)
from ai_video_production.errors import ProductError
from ai_video_production.export_queue import (
    ExportAuthorityClass, ExportDispatchResult, ExportOutputContract,
    ExportPreparation, ExportPreset,
)
from ai_video_production.export_queue_application import ExportQueueApplication
from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.serialization import sha256_bytes

CREATED = "2026-08-15T00:00:00.000Z"


def checksum(label: str) -> str:
    return sha256_bytes(label.encode())


def setup_project(root: Path) -> ProductProjectManifest:
    manifest = ProductProjectManifest.create(
        project_id="project-1", project_revision=1, product_version="0.20.1",
        timebase=ProjectTimebase(30, 1), child_bindings=(),
        created_at=CREATED, updated_at=CREATED,
    )
    ProductProjectManifestStore.save(root, manifest)
    return manifest


def preparation(manifest: ProductProjectManifest, *, target: str = "export:master") -> ExportPreparation:
    output = ExportOutputContract(1920, 1080, 30, 1, 48000, 2, "mp4", "h264", "pcm")
    preset = ExportPreset("preset-master", "1.0.0", output)
    return ExportPreparation(
        "project-1", manifest.project_manifest_sha256, manifest.product_version,
        "timeline-main", 3, checksum("timeline"), checksum("edit"), checksum("assembly"),
        preset, target, ExportAuthorityClass.RESOLVE_RENDER,
        "resolve-project-main", "resolve-timeline-main", 0, "USD", "local-free",
    )


def ready(app: ExportQueueApplication, prep: ExportPreparation):
    queued = app.enqueue(prep)
    return app.preflight(job_id=queued.job_id, preparation=prep)


def test_contract_is_hash_bound_and_rejects_host_output_target(tmp_path: Path) -> None:
    manifest = setup_project(tmp_path)
    prep = preparation(manifest)
    document = prep.to_dict()
    assert document["host_output_path_persisted"] is False
    assert document["external_mutation_authorized"] is False
    assert set(prep.input_hashes) == {"project_manifest", "timeline", "edit_plan", "assembly_plan", "preset"}
    with pytest.raises(ValueError):
        preparation(manifest, target="C:/Users/user/final.mp4")
    with pytest.raises(ValueError):
        ExportOutputContract(1920, 1080, True, 1, 48000, 2, "mp4", "h264", "pcm")


def test_enqueue_is_idempotent_and_durable_record_has_no_host_path(tmp_path: Path) -> None:
    manifest = setup_project(tmp_path)
    prep = preparation(manifest)
    app = ExportQueueApplication(project_root=tmp_path, project_id="project-1")
    first = app.enqueue(prep)
    second = app.enqueue(prep)
    assert first == second
    document = json.loads(DurableProductJobStore.path(tmp_path).read_text(encoding="utf-8"))
    assert len(document["jobs"]) == 1
    assert "C:" not in json.dumps(document)
    assert first.state is DurableProductJobState.QUEUED


def test_preflight_revalidates_exact_manifest_and_marks_stale_for_reprepare(tmp_path: Path) -> None:
    first = setup_project(tmp_path)
    prep = preparation(first)
    app = ExportQueueApplication(project_root=tmp_path, project_id="project-1")
    queued = app.enqueue(prep)
    second = ProductProjectManifest.create(
        project_id=first.project_id, project_revision=2, product_version=first.product_version,
        timebase=first.timebase, child_bindings=first.child_bindings,
        created_at=first.created_at, updated_at="2026-08-15T00:01:00.000Z",
    )
    ProductProjectManifestStore.save(tmp_path, second,
        expected_previous_manifest_sha256=first.project_manifest_sha256)
    stale = app.preflight(job_id=queued.job_id, preparation=prep)
    assert stale.state is DurableProductJobState.HUMAN_REQUIRED
    assert stale.error_code == "ERR_PRODUCT_JOB_INPUT_STALE"
    assert stale.recovery_actions == ("CANCEL", "MARK_FAILED", "RESUME_PREFLIGHT")


def test_dispatch_writes_dispatching_before_side_effect_and_binds_render_qa(tmp_path: Path) -> None:
    manifest = setup_project(tmp_path)
    prep = preparation(manifest)
    app = ExportQueueApplication(project_root=tmp_path, project_id="project-1",
                                 token_factory=lambda: "confirm-export")
    job = ready(app, prep)
    confirmation = app.prepare_dispatch(job_id=job.job_id, preparation=prep)
    observed = []

    def dispatch(current, exact_prep, destination):
        observed.append((DurableProductJobStore.load(tmp_path).get(current.job_id).state,
                         exact_prep.preparation_sha256, destination))
        return ExportDispatchResult("SUCCEEDED", "render:master", checksum("qa"), True, 0)

    final = app.apply_dispatch(
        confirmation_id=confirmation["confirmation_id"], preparation=prep,
        private_destination=tmp_path / "private" / "final.mp4", dispatcher=dispatch,
    )
    assert observed[0][0] is DurableProductJobState.DISPATCHING
    assert final.state is DurableProductJobState.SUCCEEDED
    assert final.result_ref.startswith("export-result:")
    assert str(tmp_path) not in final.result_ref
    with pytest.raises(ProductError) as exc:
        app.apply_dispatch(confirmation_id=confirmation["confirmation_id"], preparation=prep,
                           private_destination=tmp_path / "x.mp4", dispatcher=dispatch)
    assert exc.value.code == "ERR_EXPORT_CONFIRMATION_INVALID"


def test_interrupted_dispatch_recovers_unknown_and_cannot_be_cancelled(tmp_path: Path) -> None:
    manifest = setup_project(tmp_path)
    prep = preparation(manifest)
    app = ExportQueueApplication(project_root=tmp_path, project_id="project-1",
                                 token_factory=lambda: "confirm-crash")
    job = ready(app, prep)
    confirmation = app.prepare_dispatch(job_id=job.job_id, preparation=prep)

    def crash(*_args):
        raise RuntimeError("native process disappeared")

    with pytest.raises(RuntimeError):
        app.apply_dispatch(confirmation_id=confirmation["confirmation_id"], preparation=prep,
                           private_destination=tmp_path / "final.mp4", dispatcher=crash)
    with pytest.raises(ProductError) as exc:
        app.cancel(job_id=job.job_id, expected_state_version=4)
    assert exc.value.code == "ERR_EXPORT_CANCEL_UNSAFE"
    recovered = DurableProductJobService().recover_interrupted(tmp_path)
    assert recovered[0].state is DurableProductJobState.UNKNOWN
    assert recovered[0].recovery_actions == ("ACCEPT_PROVEN_SUCCESS", "MARK_FAILED", "REQUIRE_HUMAN")


def test_execute_all_never_issues_blanket_confirmation(tmp_path: Path) -> None:
    manifest = setup_project(tmp_path)
    app = ExportQueueApplication(project_root=tmp_path, project_id="project-1")
    first = preparation(manifest, target="export:master")
    second = preparation(manifest, target="export:proxy")
    first_job = ready(app, first)
    second_job = ready(app, second)
    result = app.prepare_execute_all({first_job.job_id: first, second_job.job_id: second})
    assert result["blanket_confirmation_issued"] is False
    assert len(result["items"]) == 2
    assert all(item["individual_confirmation_required"] for item in result["items"])


def test_shell_export_authority_categories() -> None:
    assert ShellApplicationService.command_spec("export.prepare").category is CommandCategory.READ_ONLY
    assert ShellApplicationService.command_spec("export.enqueue").category is CommandCategory.LOCAL_DURABLE
    assert ShellApplicationService.command_spec("export.dispatch.apply").category is CommandCategory.EXTERNAL_MUTATION
    assert ShellApplicationService.command_spec("export.reconcile").category is CommandCategory.HUMAN_FINAL_AUTHORITY
