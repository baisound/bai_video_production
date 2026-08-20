from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from threading import Barrier

import pytest

from ai_video_production.desktop_shell import CommandCategory, ShellApplicationService
from ai_video_production.durable_product_job import (
    DurableProductJobCollection, DurableProductJobService, DurableProductJobState,
    DurableProductJobStore,
)
from ai_video_production.errors import ProductError
from ai_video_production.export_queue import (
    ExportAuthorityClass, ExportDispatchResult, ExportOutputContract,
    ExportPreparation, ExportPreset,
)
from ai_video_production.export_queue_application import ExportQueueApplication
from ai_video_production.final_review import FinalReviewApprovalReceipt
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


def preparation(
    manifest: ProductProjectManifest, *, target: str = "export:master", approval_suffix: str = "1",
) -> ExportPreparation:
    output = ExportOutputContract(1920, 1080, 30, 1, 48000, 2, "mp4", "h264", "pcm")
    preset = ExportPreset("preset-master", "1.0.0", output)
    final_approval = FinalReviewApprovalReceipt(
        receipt_id=f"final-review-{approval_suffix}", project_id="project-1",
        project_manifest_sha256=manifest.project_manifest_sha256,
        timeline_sha256=checksum("timeline"), readiness_projection_sha256=checksum(f"readiness-{approval_suffix}"),
        source_snapshot_sha256s=(
            ("audit", checksum("audit")), ("production", checksum("production")),
            ("project_manifest", manifest.project_manifest_sha256),
            ("timeline", checksum("timeline")), ("visual_handoff", checksum("visual_handoff")),
        ),
        external_gate_receipt_sha256s=tuple((key, checksum(key)) for key in (
            "AUDIO_COMPLETION", "EDIT_PERSISTENCE", "PRIVACY", "RESOURCE", "RIGHTS_LICENSE",
        )),
        approved_by="owner-1", approved_at=f"2026-08-17T02:00:0{approval_suffix}.000Z",
    )
    return ExportPreparation(
        "project-1", manifest.project_manifest_sha256, manifest.product_version,
        "timeline-main", 3, checksum("timeline"), checksum("edit"), checksum("assembly"),
        final_approval, preset, target, ExportAuthorityClass.RESOLVE_RENDER,
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
    assert set(prep.input_hashes) == {
        "project_manifest", "timeline", "edit_plan", "assembly_plan", "final_approval", "preset",
        "export_profile",
    }
    assert document["export_profile_sha256"] == prep.input_hashes["export_profile"]
    assert prep.to_dict()["final_approval_receipt_sha256"] == prep.final_approval.final_approval_receipt_sha256
    with pytest.raises(ValueError):
        preparation(manifest, target="C:/Users/user/final.mp4")
    with pytest.raises(ValueError):
        ExportOutputContract(1920, 1080, True, 1, 48000, 2, "mp4", "h264", "pcm")


def test_export_preparation_rejects_cross_scope_final_approval(tmp_path: Path) -> None:
    manifest = setup_project(tmp_path)
    current = preparation(manifest)
    other = FinalReviewApprovalReceipt(
        receipt_id="final-review-other", project_id="other-project",
        project_manifest_sha256=manifest.project_manifest_sha256,
        timeline_sha256=current.timeline_sha256,
        readiness_projection_sha256=checksum("other-readiness"),
        source_snapshot_sha256s=(
            ("audit", checksum("audit")), ("production", checksum("production")),
            ("project_manifest", manifest.project_manifest_sha256),
            ("timeline", current.timeline_sha256), ("visual_handoff", checksum("visual")),
        ),
        external_gate_receipt_sha256s=current.final_approval.external_gate_receipt_sha256s,
        approved_by="owner-1", approved_at="2026-08-17T02:00:01.000Z",
    )
    with pytest.raises(ValueError, match="crosses Final Review Project"):
        ExportPreparation(
            current.project_id, current.project_manifest_sha256, current.product_version,
            current.timeline_plan_id, current.timeline_revision, current.timeline_sha256,
            current.edit_plan_sha256, current.assembly_plan_sha256, other,
            current.preset, current.output_target_identity, current.authority_class,
            current.resolve_project_identity, current.resolve_timeline_identity,
            current.estimated_cost, current.currency, current.estimate_source,
        )


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


def test_final_approval_is_exclusive_across_app_instances_and_threads(tmp_path: Path) -> None:
    manifest = setup_project(tmp_path)
    first = preparation(manifest, target="export:master")
    second = preparation(manifest, target="export:alternate")
    apps = (
        ExportQueueApplication(project_root=tmp_path, project_id="project-1"),
        ExportQueueApplication(project_root=tmp_path, project_id="project-1"),
    )
    start = Barrier(2)

    def enqueue_once(app: ExportQueueApplication, prep: ExportPreparation):
        start.wait()
        try:
            return ("success", app.enqueue(prep))
        except ProductError as exc:
            return ("error", exc)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda pair: enqueue_once(*pair), zip(apps, (first, second), strict=True)))
    successes = [value for state, value in results if state == "success"]
    failures = [value for state, value in results if state == "error"]
    assert len(successes) == 1
    assert len(failures) == 1
    assert failures[0].code == "ERR_PRODUCT_JOB_EXCLUSIVE_INPUT_CONFLICT"
    assert apps[0].jobs_for_final_approval(first.final_approval.final_approval_receipt_sha256) == tuple(successes)


def test_explicit_startup_recovery_recovers_interrupted_export_once_without_dispatch_or_store_creation(tmp_path: Path) -> None:
    manifest = setup_project(tmp_path)
    no_store = ExportQueueApplication(project_root=tmp_path, project_id="project-1")
    assert no_store.recover_interrupted_on_startup() == ()
    assert no_store.jobs_for_final_approval(checksum("missing-approval")) == ()
    assert not DurableProductJobStore.path(tmp_path).exists()

    prep = preparation(manifest)
    app = ExportQueueApplication(project_root=tmp_path, project_id="project-1")
    ready_job = ready(app, prep)
    dispatching = app.jobs.transition(
        tmp_path, ready_job.job_id, DurableProductJobState.DISPATCHING,
        expected_state_version=ready_job.state_version,
    )
    analysis = app.jobs.enqueue(
        tmp_path, kind="LOCAL_ANALYSIS", target_identity="analysis:startup-recovery",
        input_hashes={"source": checksum("startup-analysis")},
    )
    analysis = app.jobs.transition(
        tmp_path, analysis.job_id, DurableProductJobState.PREFLIGHT,
        expected_state_version=analysis.state_version,
    )
    analysis = app.jobs.transition(
        tmp_path, analysis.job_id, DurableProductJobState.READY,
        expected_state_version=analysis.state_version,
    )
    analysis = app.jobs.transition(
        tmp_path, analysis.job_id, DurableProductJobState.DISPATCHING,
        expected_state_version=analysis.state_version,
    )
    restarted = ExportQueueApplication(project_root=tmp_path, project_id="project-1")
    recovered = restarted.recover_interrupted_on_startup()
    assert len(recovered) == 1
    assert recovered[0].state is DurableProductJobState.UNKNOWN
    assert recovered[0].state_version == dispatching.state_version + 1
    assert DurableProductJobStore.load(tmp_path).get(analysis.job_id) == analysis
    second_restart = ExportQueueApplication(project_root=tmp_path, project_id="project-1")
    assert second_restart.recover_interrupted_on_startup() == ()
    assert second_restart.jobs_for_final_approval(prep.final_approval.final_approval_receipt_sha256) == recovered


def test_existing_export_application_rejects_checksum_valid_other_project_manifest_and_jobs(tmp_path: Path) -> None:
    manifest = setup_project(tmp_path)
    app = ExportQueueApplication(project_root=tmp_path, project_id="project-1")
    app.enqueue(preparation(manifest))
    manifest_path = ProductProjectManifestStore.path(tmp_path)
    manifest_path.unlink()
    ProductProjectManifestStore.save(
        tmp_path,
        ProductProjectManifest.create(
            project_id="other-project", project_revision=1, product_version="0.20.1",
            timebase=ProjectTimebase(30, 1), child_bindings=(),
            created_at=CREATED, updated_at=CREATED,
        ),
    )
    DurableProductJobStore._save_unlocked(
        tmp_path, DurableProductJobCollection.create("other-project"),
    )
    for operation in (
        lambda: app.jobs_for_final_approval(checksum("approval")),
        app.recover_interrupted_on_startup,
        lambda: app.enqueue(preparation(manifest)),
    ):
        with pytest.raises(ProductError) as exc:
            operation()
        assert exc.value.code == "ERR_PRODUCT_JOB_PROJECT_CONFLICT"


@pytest.mark.parametrize("dangling", [False, True])
def test_explicit_startup_recovery_fails_closed_for_valid_and_dangling_job_store_symlinks(
    tmp_path: Path, dangling: bool,
) -> None:
    manifest = setup_project(tmp_path)
    app = ExportQueueApplication(project_root=tmp_path, project_id="project-1")
    app.enqueue(preparation(manifest))
    store_path = DurableProductJobStore.path(tmp_path)
    real_path = store_path.with_name("jobs-real.json")
    try:
        if dangling:
            store_path.unlink()
            store_path.symlink_to(store_path.with_name("missing-jobs.json"))
        else:
            store_path.replace(real_path)
            store_path.symlink_to(real_path)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ProductError) as exc:
        ExportQueueApplication(project_root=tmp_path, project_id="project-1").recover_interrupted_on_startup()
    assert exc.value.code == "ERR_PRODUCT_JOB_STORE_FILE"


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


def test_dispatch_confirmation_can_be_cancelled_without_job_mutation(tmp_path: Path) -> None:
    manifest = setup_project(tmp_path)
    prep = preparation(manifest)
    app = ExportQueueApplication(
        project_root=tmp_path, project_id="project-1",
        token_factory=lambda: "confirm-cancel",
    )
    job = ready(app, prep)
    confirmation = app.prepare_dispatch(job_id=job.job_id, preparation=prep)
    cancelled = app.cancel_dispatch(confirmation_id=str(confirmation["confirmation_id"]))
    assert cancelled["cancelled"] is True
    assert DurableProductJobStore.load(tmp_path).get(job.job_id).state is DurableProductJobState.READY
    with pytest.raises(ProductError) as exc:
        app.apply_dispatch(
            confirmation_id=str(confirmation["confirmation_id"]), preparation=prep,
            private_destination=tmp_path / "final.mp4",
            dispatcher=lambda *_: ExportDispatchResult("RUNNING"),
        )
    assert exc.value.code == "ERR_EXPORT_CONFIRMATION_INVALID"


def test_parallel_dispatch_confirmation_is_admitted_exactly_once(tmp_path: Path) -> None:
    manifest = setup_project(tmp_path)
    prep = preparation(manifest)
    app = ExportQueueApplication(
        project_root=tmp_path, project_id="project-1",
        token_factory=lambda: "confirm-parallel",
    )
    job = ready(app, prep)
    confirmation = app.prepare_dispatch(job_id=job.job_id, preparation=prep)
    calls = 0

    def dispatch(*_args):
        nonlocal calls
        calls += 1
        return ExportDispatchResult("RUNNING")

    def apply():
        try:
            return app.apply_dispatch(
                confirmation_id=str(confirmation["confirmation_id"]),
                preparation=prep,
                private_destination=tmp_path / "final.mp4",
                dispatcher=dispatch,
            ).state.value
        except ProductError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(lambda _: apply(), range(2)))
    assert sorted(results) == ["ERR_EXPORT_CONFIRMATION_INVALID", "RUNNING"]
    assert calls == 1


def test_dispatch_confirmation_storage_is_bounded_and_cancel_releases_capacity(tmp_path: Path) -> None:
    manifest = setup_project(tmp_path)
    prep = preparation(manifest)
    tokens = iter(f"confirm-{index}" for index in range(258))
    app = ExportQueueApplication(
        project_root=tmp_path, project_id="project-1", token_factory=lambda: next(tokens),
    )
    job = ready(app, prep)
    confirmations = tuple(
        app.prepare_dispatch(job_id=job.job_id, preparation=prep)
        for _ in range(256)
    )
    with pytest.raises(ProductError) as exc:
        app.prepare_dispatch(job_id=job.job_id, preparation=prep)
    assert exc.value.code == "ERR_EXPORT_CONFIRMATION_CAPACITY"
    app.cancel_dispatch(confirmation_id=str(confirmations[0]["confirmation_id"]))
    replacement = app.prepare_dispatch(job_id=job.job_id, preparation=prep)
    assert replacement["confirmation_id"] == "confirm-257"


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


def unknown(app: ExportQueueApplication, prep: ExportPreparation):
    job = ready(app, prep)
    dispatching = app.jobs.transition(
        app.project_root, job.job_id, DurableProductJobState.DISPATCHING,
        expected_state_version=job.state_version,
    )
    return app.jobs.transition(
        app.project_root, job.job_id, DurableProductJobState.UNKNOWN,
        expected_state_version=dispatching.state_version,
        error_code="ERR_PRODUCT_JOB_RESTART_UNKNOWN",
    )


def test_unknown_reconciliation_requires_render_qa_and_binds_proven_success(tmp_path: Path) -> None:
    manifest = setup_project(tmp_path)
    prep = preparation(manifest)
    app = ExportQueueApplication(project_root=tmp_path, project_id="project-1")
    job = unknown(app, prep)
    with pytest.raises(ProductError) as exc:
        app.reconcile(job_id=job.job_id, expected_state_version=job.state_version,
                      action="ACCEPT_PROVEN_SUCCESS")
    assert exc.value.code == "ERR_EXPORT_RECONCILE_PROOF_REQUIRED"
    result = ExportDispatchResult(
        "SUCCEEDED", result_identity="resolve-render:master",
        render_qa_sha256=checksum("render-qa"), render_qa_passed=True,
    )
    reconciled = app.reconcile(
        job_id=job.job_id, expected_state_version=job.state_version,
        action="ACCEPT_PROVEN_SUCCESS", result=result,
    )
    assert reconciled.state is DurableProductJobState.SUCCEEDED
    assert reconciled.result_ref == result.durable_result_ref


@pytest.mark.parametrize(
    ("action", "expected"),
    (("MARK_FAILED", DurableProductJobState.FAILED),
     ("REQUIRE_HUMAN", DurableProductJobState.HUMAN_REQUIRED)),
)
def test_unknown_reconciliation_never_replays_external_work(
    tmp_path: Path, action: str, expected: DurableProductJobState,
) -> None:
    manifest = setup_project(tmp_path)
    prep = preparation(manifest)
    app = ExportQueueApplication(project_root=tmp_path, project_id="project-1")
    job = unknown(app, prep)
    reconciled = app.reconcile(
        job_id=job.job_id, expected_state_version=job.state_version, action=action,
    )
    assert reconciled.state is expected
    assert reconciled.attempt == job.attempt


def test_execute_all_never_issues_blanket_confirmation(tmp_path: Path) -> None:
    manifest = setup_project(tmp_path)
    app = ExportQueueApplication(project_root=tmp_path, project_id="project-1")
    first = preparation(manifest, target="export:master")
    second = preparation(manifest, target="export:proxy", approval_suffix="2")
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
