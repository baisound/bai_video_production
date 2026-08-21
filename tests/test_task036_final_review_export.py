from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from threading import Barrier

import pytest

from ai_video_production.durable_product_job import (
    DurableProductJobCollection,
    DurableProductJobState,
    DurableProductJobStore,
)
from ai_video_production.errors import ProductError
from ai_video_production.export_queue import (
    ExportAuthorityClass,
    ExportOutputContract,
    ExportPreparation,
    ExportPreset,
)
from ai_video_production.export_queue_application import ExportQueueApplication
from ai_video_production.final_review import FinalReviewApprovalReceipt
from ai_video_production.final_review_application import FinalReviewApprovalApplication
from ai_video_production.final_review_export_application import Task036FinalReviewExportApplication
from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


def h(char: str) -> str:
    return "sha256:" + char * 64


def readiness(*, production: str = "2", project_manifest: str | None = None) -> dict[str, object]:
    value: dict[str, object] = {
        "available": True,
        "projection_version": "1.0.0",
        "state": "READY_FOR_TYPED_FINAL_REVIEW",
        "project_id": "project-1",
        "source_snapshots": {
            "production": h(production), "audit": h("3"), "visual_handoff": h("4"),
            "timeline": h("5"), "project_manifest": project_manifest or h("6"),
        },
        "required_slot_count": 1,
        "audit_candidate_count": 0,
        "export_job_count": 0,
        "product_blockers": [],
        "external_gates": [{
            "gate_id": gate, "owner": owner, "state": "PASS", "receipt_sha256": h(char),
        } for gate, owner, char in zip(
            ("AUDIO_COMPLETION", "EDIT_PERSISTENCE", "PRIVACY", "RESOURCE", "RIGHTS_LICENSE"),
            ("DEVELOPER2", "TASK-044", "TASK-016", "TASK-020", "TASK-003/027"),
            "789ab", strict=True,
        )],
        "external_blockers": [],
        "delegated_audio_owner": "DEVELOPER2",
        "final_approval_created": False,
        "export_job_created": False,
        "render_or_publish_started": False,
        "human_decision_authorized": False,
    }
    value["projection_sha256"] = sha256_bytes(canonical_json_bytes({
        key: item for key, item in value.items() if key != "available"
    }))
    return value


def setup(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    manifest = ProductProjectManifest.create(
        project_id="project-1", project_revision=1, product_version="0.21.0",
        timebase=ProjectTimebase(30, 1), child_bindings=(),
        created_at="2026-08-17T07:00:00.000Z", updated_at="2026-08-17T07:00:00.000Z",
    )
    ProductProjectManifestStore.save(root, manifest)
    approvals = FinalReviewApprovalApplication(
        project_root=root, project_id="project-1",
        token_factory=lambda: "approval-confirmation",
        clock=lambda: "2026-08-17T07:01:00.000Z",
    )
    current = readiness(project_manifest=manifest.project_manifest_sha256)
    initial = approvals.snapshot(readiness=current)
    prepared = approvals.prepare_approval(
        readiness=current,
        expected_readiness_projection_sha256=str(current["projection_sha256"]),
        expected_snapshot_sha256=str(initial["snapshot_sha256"]),
    )
    approved = approvals.apply_approval(
        confirmation_id=str(prepared["confirmation_id"]),
        readiness=current,
        approved_by="owner-1",
    )
    receipt = FinalReviewApprovalReceipt.from_dict(approved["receipt"])
    queue = ExportQueueApplication(project_root=root, project_id="project-1")
    return manifest, approvals, receipt, queue, current


def preparation(manifest, receipt, *, target: str = "export:master") -> ExportPreparation:
    return ExportPreparation(
        project_id="project-1",
        project_manifest_sha256=manifest.project_manifest_sha256,
        product_version=manifest.product_version,
        timeline_plan_id="timeline-main",
        timeline_revision=1,
        timeline_sha256=h("5"),
        edit_plan_sha256=h("c"),
        assembly_plan_sha256=h("d"),
        final_approval=receipt,
        preset=ExportPreset(
            "preset-youtube-1080p", "1.0.0",
            ExportOutputContract(1920, 1080, 30, 1, 48000, 2, "mp4", "h264", "pcm"),
        ),
        output_target_identity=target,
        authority_class=ExportAuthorityClass.LOCAL_PACKAGE,
    )


def application(root: Path, *, token: str = "queue-confirmation"):
    manifest, approvals, receipt, queue, current = setup(root)
    selected = [preparation(manifest, receipt)]
    app = Task036FinalReviewExportApplication(
        project_id="project-1",
        final_review_application=approvals,
        export_application_provider=lambda: queue,
        preparation_provider=lambda exact_receipt: selected[0],
        token_factory=lambda: token,
    )
    return app, selected, current, manifest, receipt


def test_snapshot_exposes_only_logical_preparation_and_requires_confirmation(tmp_path: Path) -> None:
    app, _, current, _, _ = application(tmp_path)
    snapshot = app.snapshot(readiness=current)
    assert snapshot["state"] == "READY_FOR_EXPORT_QUEUE_CONFIRMATION"
    assert snapshot["queue_confirmation_ready"] is True
    assert snapshot["export_job_created"] is False
    assert snapshot["side_effect_started_by_this_call"] is False
    assert snapshot["host_output_path_persisted"] is False
    assert snapshot["preset"]["preset_id"] == "preset-youtube-1080p"
    assert str(tmp_path) not in json.dumps(snapshot)


def test_prepare_apply_creates_exactly_one_queued_job_without_dispatch(tmp_path: Path) -> None:
    app, _, current, _, _ = application(tmp_path)
    snapshot = app.snapshot(readiness=current)
    prepared = app.prepare_enqueue(
        readiness=current,
        expected_readiness_projection_sha256=str(snapshot["readiness_projection_sha256"]),
        expected_approval_snapshot_sha256=str(snapshot["approval_snapshot_sha256"]),
        expected_preparation_sha256=str(snapshot["preparation_sha256"]),
    )
    assert prepared["export_job_created"] is False
    result = app.apply_enqueue(
        confirmation_id=str(prepared["confirmation_id"]), readiness=current,
    )
    assert result["state"] == "QUEUED"
    assert result["export_job_created"] is True
    assert result["side_effect_started_by_this_call"] is False
    collection = DurableProductJobStore.load(tmp_path)
    assert len(collection.jobs) == 1
    assert collection.jobs[0].state.value == "QUEUED"
    existing = app.snapshot(readiness=current)
    assert existing["state"] == "EXISTING_EXPORT_JOB"
    assert existing["existing_job_state"] == "QUEUED"
    assert existing["job_id"] == result["job_id"]
    with pytest.raises(ProductError, match="missing or consumed"):
        app.apply_enqueue(confirmation_id=str(prepared["confirmation_id"]), readiness=current)


def test_dispatch_repreparation_survives_restart_and_binds_exact_job(tmp_path: Path) -> None:
    app, selected, current, _, _ = application(tmp_path)
    queued = _enqueue_once(app, current)
    restarted = Task036FinalReviewExportApplication(
        project_id=app.project_id,
        final_review_application=FinalReviewApprovalApplication(
            project_root=tmp_path, project_id=app.project_id,
        ),
        export_application_provider=lambda: ExportQueueApplication(
            project_root=tmp_path, project_id=app.project_id,
        ),
        preparation_provider=lambda _receipt: selected[0],
    )
    rebound = restarted.preparation_for_dispatch(job_id=str(queued["job_id"]))
    assert rebound.preparation_sha256 == selected[0].preparation_sha256
    with pytest.raises(ProductError) as exc:
        restarted.preparation_for_dispatch(job_id="product-job-" + "0" * 64)
    assert exc.value.code == "ERR_FINAL_REVIEW_EXPORT_EXISTING_JOB_CONFLICT"


def test_readiness_or_private_preparation_change_invalidates_confirmation(tmp_path: Path) -> None:
    app, selected, current, manifest, receipt = application(tmp_path)
    snapshot = app.snapshot(readiness=current)
    prepared = app.prepare_enqueue(
        readiness=current,
        expected_readiness_projection_sha256=str(snapshot["readiness_projection_sha256"]),
        expected_approval_snapshot_sha256=str(snapshot["approval_snapshot_sha256"]),
        expected_preparation_sha256=str(snapshot["preparation_sha256"]),
    )
    selected[0] = preparation(manifest, receipt, target="export:alternate")
    with pytest.raises(ProductError, match="changed after confirmation"):
        app.apply_enqueue(confirmation_id=str(prepared["confirmation_id"]), readiness=current)

    other, _, other_current, _, _ = application(tmp_path / "other", token="other-confirmation")
    other_snapshot = other.snapshot(readiness=other_current)
    other_prepared = other.prepare_enqueue(
        readiness=other_current,
        expected_readiness_projection_sha256=str(other_snapshot["readiness_projection_sha256"]),
        expected_approval_snapshot_sha256=str(other_snapshot["approval_snapshot_sha256"]),
        expected_preparation_sha256=str(other_snapshot["preparation_sha256"]),
    )
    with pytest.raises(ProductError, match="readiness changed"):
        other.apply_enqueue(
            confirmation_id=str(other_prepared["confirmation_id"]),
            readiness=readiness(production="e"),
        )


def test_stale_or_cross_approval_preparation_fails_closed(tmp_path: Path) -> None:
    manifest, approvals, receipt, queue, current = setup(tmp_path)
    wrong = FinalReviewApprovalReceipt(
        receipt_id="wrong-approval", project_id=receipt.project_id,
        project_manifest_sha256=receipt.project_manifest_sha256,
        timeline_sha256=receipt.timeline_sha256,
        readiness_projection_sha256=receipt.readiness_projection_sha256,
        source_snapshot_sha256s=receipt.source_snapshot_sha256s,
        external_gate_receipt_sha256s=receipt.external_gate_receipt_sha256s,
        approved_by="owner-2", approved_at="2026-08-17T07:02:00.000Z",
    )
    app = Task036FinalReviewExportApplication(
        project_id="project-1", final_review_application=approvals,
        export_application_provider=lambda: queue,
        preparation_provider=lambda _: preparation(manifest, wrong),
    )
    with pytest.raises(ProductError, match="current exact approval"):
        app.snapshot(readiness=current)
    assert not DurableProductJobStore.path(tmp_path).exists()


def test_unbound_queue_is_read_only_unavailable(tmp_path: Path) -> None:
    manifest, approvals, receipt, _, current = setup(tmp_path)
    app = Task036FinalReviewExportApplication(
        project_id="project-1", final_review_application=approvals,
        export_application_provider=lambda: None,
        preparation_provider=lambda _: preparation(manifest, receipt),
    )
    snapshot = app.snapshot(readiness=current)
    assert snapshot["available"] is False
    assert snapshot["state"] == "ERR_FINAL_REVIEW_EXPORT_QUEUE_NOT_BOUND"
    assert snapshot["export_job_created"] is False


def _stale_after_export(current: dict[str, object]) -> dict[str, object]:
    stale = dict(current)
    stale["export_job_count"] = 1
    stale["product_blockers"] = [{"code": "UNSCOPED_EXPORT_JOB_PRESENT"}]
    stale["projection_sha256"] = sha256_bytes(canonical_json_bytes({
        key: value for key, value in stale.items() if key != "available" and key != "projection_sha256"
    }))
    return stale


def _enqueue_once(app: Task036FinalReviewExportApplication, current: dict[str, object]) -> dict[str, object]:
    snapshot = app.snapshot(readiness=current)
    prepared = app.prepare_enqueue(
        readiness=current,
        expected_readiness_projection_sha256=str(snapshot["readiness_projection_sha256"]),
        expected_approval_snapshot_sha256=str(snapshot["approval_snapshot_sha256"]),
        expected_preparation_sha256=str(snapshot["preparation_sha256"]),
    )
    return app.apply_enqueue(confirmation_id=str(prepared["confirmation_id"]), readiness=current)


@pytest.mark.parametrize(
    ("target_state", "transitions"),
    (
        (DurableProductJobState.QUEUED, ()),
        (DurableProductJobState.PREFLIGHT, (DurableProductJobState.PREFLIGHT,)),
        (DurableProductJobState.READY, (DurableProductJobState.PREFLIGHT, DurableProductJobState.READY)),
        (DurableProductJobState.DISPATCHING, (DurableProductJobState.PREFLIGHT, DurableProductJobState.READY, DurableProductJobState.DISPATCHING)),
        (DurableProductJobState.RUNNING, (DurableProductJobState.PREFLIGHT, DurableProductJobState.READY, DurableProductJobState.DISPATCHING, DurableProductJobState.RUNNING)),
        (DurableProductJobState.SUCCEEDED, (DurableProductJobState.PREFLIGHT, DurableProductJobState.READY, DurableProductJobState.DISPATCHING, DurableProductJobState.SUCCEEDED)),
        (DurableProductJobState.FAILED, (DurableProductJobState.PREFLIGHT, DurableProductJobState.FAILED)),
        (DurableProductJobState.CANCELLED, (DurableProductJobState.CANCELLED,)),
        (DurableProductJobState.UNKNOWN, (DurableProductJobState.PREFLIGHT, DurableProductJobState.READY, DurableProductJobState.DISPATCHING, DurableProductJobState.UNKNOWN)),
        (DurableProductJobState.HUMAN_REQUIRED, (DurableProductJobState.PREFLIGHT, DurableProductJobState.HUMAN_REQUIRED)),
    ),
)
def test_stale_final_review_projects_existing_export_job_state_truthfully(
    tmp_path: Path, target_state: DurableProductJobState, transitions: tuple[DurableProductJobState, ...]
) -> None:
    app, _, current, _, _ = application(tmp_path)
    result = _enqueue_once(app, current)
    job = DurableProductJobStore.load(tmp_path).jobs[0]
    for state in transitions:
        kwargs: dict[str, object] = {}
        if state is DurableProductJobState.SUCCEEDED:
            kwargs["result_ref"] = "result-export-1"
        elif state in {DurableProductJobState.FAILED, DurableProductJobState.UNKNOWN, DurableProductJobState.HUMAN_REQUIRED}:
            kwargs["error_code"] = "ERR_PRODUCT_JOB_TEST_STATE"
        job = app._application().jobs.transition(
            tmp_path, job.job_id, state, expected_state_version=job.state_version, **kwargs
        )
    snapshot = app.snapshot(readiness=_stale_after_export(current))
    assert snapshot["state"] == "EXISTING_EXPORT_JOB"
    assert snapshot["existing_job_state"] == target_state.value
    assert snapshot["job_id"] == result["job_id"]
    assert snapshot["operation_identity"] == result["operation_identity"]
    assert snapshot["state_version"] == job.state_version
    assert snapshot["target_identity"] == job.target_identity
    assert "preset" not in snapshot
    assert "preparation_sha256" not in snapshot
    assert "authority_class" not in snapshot
    assert snapshot["queue_confirmation_ready"] is False
    assert snapshot["export_job_created"] is True
    assert "dispatch_or_render_started" not in snapshot
    assert snapshot["side_effect_started_by_this_call"] is False
    assert snapshot["host_output_path_persisted"] is False
    assert len(DurableProductJobStore.load(tmp_path).jobs) == 1


def test_stale_final_review_without_existing_export_job_remains_unavailable(tmp_path: Path) -> None:
    app, _, current, _, _ = application(tmp_path)
    snapshot = app.snapshot(readiness=_stale_after_export(current))
    assert snapshot["available"] is False
    assert snapshot["state"] == "ERR_FINAL_REVIEW_EXPORT_APPROVAL_NOT_CURRENT"
    assert snapshot["queue_confirmation_ready"] is False
    assert snapshot["export_job_created"] is False
    assert not DurableProductJobStore.path(tmp_path).exists()


def test_stale_snapshot_never_calls_private_provider_and_survives_provider_change(
    tmp_path: Path,
) -> None:
    app, _, current, _, _ = application(tmp_path)
    queued = _enqueue_once(app, current)
    calls = 0

    def unavailable_provider(_: FinalReviewApprovalReceipt) -> ExportPreparation:
        nonlocal calls
        calls += 1
        raise AssertionError("stale durable projection must not call private provider")

    # This represents a process restart after provider configuration changes.
    restarted = Task036FinalReviewExportApplication(
        project_id=app.project_id,
        final_review_application=app._final_review,
        export_application_provider=app._export_application_provider,
        preparation_provider=unavailable_provider,
    )
    snapshot = restarted.snapshot(readiness=_stale_after_export(current))
    assert calls == 0
    assert snapshot == {
        "available": True,
        "state": "EXISTING_EXPORT_JOB",
        "job_id": queued["job_id"],
        "operation_identity": queued["operation_identity"],
        "target_identity": "export:master",
        "existing_job_state": "QUEUED",
        "state_version": 1,
        "queue_confirmation_ready": False,
        "export_job_created": True,
        "side_effect_started_by_this_call": False,
        "host_output_path_persisted": False,
    }


def test_multiple_durable_jobs_for_one_approval_fail_closed_without_provider(tmp_path: Path) -> None:
    app, _, current, _, receipt = application(tmp_path)
    _enqueue_once(app, current)
    queue = app._application()
    original = DurableProductJobStore.load(tmp_path).jobs[0]
    queue.jobs.enqueue(
        tmp_path,
        kind="EXPORT",
        target_identity="export:conflicting-target",
        input_hashes=dict(original.input_hashes),
    )
    calls = 0

    def forbidden_provider(_: FinalReviewApprovalReceipt) -> ExportPreparation:
        nonlocal calls
        calls += 1
        raise AssertionError("conflict projection must not call private provider")

    app._preparation_provider = forbidden_provider
    snapshot = app.snapshot(readiness=_stale_after_export(current))
    assert receipt.final_approval_receipt_sha256 == dict(original.input_hashes)["final_approval"]
    assert calls == 0
    assert snapshot["available"] is False
    assert snapshot["state"] == "ERR_FINAL_REVIEW_EXPORT_EXISTING_JOB_CONFLICT"
    assert snapshot["queue_confirmation_ready"] is False
    assert snapshot["existing_export_job_count"] == 2
    assert "export_job_created" not in snapshot
    assert "dispatch_or_render_started" not in snapshot


def test_pending_confirmation_cancel_and_bounded_eviction_fail_closed(tmp_path: Path) -> None:
    tokens = iter(f"queue-confirmation-{index}" for index in range(300))
    app, _, current, _, _ = application(tmp_path, token="unused")
    app._token_factory = lambda: next(tokens)
    snapshot = app.snapshot(readiness=current)
    expected = {
        "expected_readiness_projection_sha256": str(snapshot["readiness_projection_sha256"]),
        "expected_approval_snapshot_sha256": str(snapshot["approval_snapshot_sha256"]),
        "expected_preparation_sha256": str(snapshot["preparation_sha256"]),
    }
    first = app.prepare_enqueue(readiness=current, **expected)
    app.apply_enqueue(confirmation_id=str(first["confirmation_id"]), readiness=current)
    assert not app._pending
    pending_app, _, pending_current, _, _ = application(tmp_path / "pending", token="unused")
    pending_app._token_factory = lambda: next(tokens)
    pending_snapshot = pending_app.snapshot(readiness=pending_current)
    pending_expected = {
        "expected_readiness_projection_sha256": str(pending_snapshot["readiness_projection_sha256"]),
        "expected_approval_snapshot_sha256": str(pending_snapshot["approval_snapshot_sha256"]),
        "expected_preparation_sha256": str(pending_snapshot["preparation_sha256"]),
    }
    pending = [pending_app.prepare_enqueue(readiness=pending_current, **pending_expected) for _ in range(256)]
    evicted = pending_app.prepare_enqueue(readiness=pending_current, **pending_expected)
    assert len(pending_app._pending) == 256
    assert str(pending[0]["confirmation_id"]) not in pending_app._pending
    with pytest.raises(ProductError, match="missing or consumed"):
        pending_app.apply_enqueue(confirmation_id=str(pending[0]["confirmation_id"]), readiness=pending_current)
    cancelled = pending_app.cancel_enqueue(confirmation_id=str(evicted["confirmation_id"]))
    assert cancelled["cancelled"] is True
    assert cancelled["export_job_created"] is False
    with pytest.raises(ProductError, match="missing or consumed"):
        pending_app.apply_enqueue(confirmation_id=str(evicted["confirmation_id"]), readiness=pending_current)
    assert not DurableProductJobStore.path(tmp_path / "pending").exists()


def test_apply_uses_private_preparation_once_and_fails_closed_on_provider_drift(tmp_path: Path) -> None:
    app, selected, current, manifest, receipt = application(tmp_path)
    calls = 0

    def drifting_provider(_: FinalReviewApprovalReceipt) -> ExportPreparation:
        nonlocal calls
        calls += 1
        return selected[0] if calls <= 3 else preparation(manifest, receipt, target="export:drifted")

    app._preparation_provider = drifting_provider
    snapshot = app.snapshot(readiness=current)
    prepared = app.prepare_enqueue(
        readiness=current,
        expected_readiness_projection_sha256=str(snapshot["readiness_projection_sha256"]),
        expected_approval_snapshot_sha256=str(snapshot["approval_snapshot_sha256"]),
        expected_preparation_sha256=str(snapshot["preparation_sha256"]),
    )
    # snapshot + prepare each obtain their own preview.  If apply evaluated the
    # provider twice, its fourth call would enqueue the drifted target.
    result = app.apply_enqueue(confirmation_id=str(prepared["confirmation_id"]), readiness=current)
    assert calls == 3
    assert result["job_id"]
    jobs = DurableProductJobStore.load(tmp_path).jobs
    assert len(jobs) == 1
    assert jobs[0].target_identity == "export:master"


def test_concurrent_apply_consumes_one_confirmation_exactly_once(tmp_path: Path) -> None:
    app, _, current, _, _ = application(tmp_path)
    snapshot = app.snapshot(readiness=current)
    prepared = app.prepare_enqueue(
        readiness=current,
        expected_readiness_projection_sha256=str(snapshot["readiness_projection_sha256"]),
        expected_approval_snapshot_sha256=str(snapshot["approval_snapshot_sha256"]),
        expected_preparation_sha256=str(snapshot["preparation_sha256"]),
    )

    def apply() -> dict[str, object] | ProductError:
        try:
            return app.apply_enqueue(confirmation_id=str(prepared["confirmation_id"]), readiness=current)
        except ProductError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = [future.result() for future in (executor.submit(apply), executor.submit(apply))]
    successes = [item for item in results if not isinstance(item, ProductError)]
    failures = [item for item in results if isinstance(item, ProductError)]
    assert len(successes) == 1
    assert len(failures) == 1
    assert failures[0].code == "ERR_FINAL_REVIEW_EXPORT_CONFIRMATION_INVALID"
    assert len(DurableProductJobStore.load(tmp_path).jobs) == 1


def test_distinct_confirmations_and_preparations_admit_exactly_one_job_per_approval(tmp_path: Path) -> None:
    manifest, approvals, receipt, first_queue, current = setup(tmp_path)
    second_queue = ExportQueueApplication(project_root=tmp_path, project_id="project-1")
    first = Task036FinalReviewExportApplication(
        project_id="project-1", final_review_application=approvals,
        export_application_provider=lambda: first_queue,
        preparation_provider=lambda _: preparation(manifest, receipt, target="export:master"),
        token_factory=lambda: "first-confirmation",
    )
    second = Task036FinalReviewExportApplication(
        project_id="project-1", final_review_application=approvals,
        export_application_provider=lambda: second_queue,
        preparation_provider=lambda _: preparation(manifest, receipt, target="export:alternate"),
        token_factory=lambda: "second-confirmation",
    )

    def prepare(app: Task036FinalReviewExportApplication) -> dict[str, object]:
        snapshot = app.snapshot(readiness=current)
        return app.prepare_enqueue(
            readiness=current,
            expected_readiness_projection_sha256=str(snapshot["readiness_projection_sha256"]),
            expected_approval_snapshot_sha256=str(snapshot["approval_snapshot_sha256"]),
            expected_preparation_sha256=str(snapshot["preparation_sha256"]),
        )

    prepared = (prepare(first), prepare(second))
    start = Barrier(2)

    def apply(app: Task036FinalReviewExportApplication, confirmation: str):
        start.wait()
        try:
            return app.apply_enqueue(confirmation_id=confirmation, readiness=current)
        except ProductError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(
            lambda pair: apply(*pair),
            zip((first, second), tuple(str(item["confirmation_id"]) for item in prepared), strict=True),
        ))
    successes = [item for item in results if not isinstance(item, ProductError)]
    failures = [item for item in results if isinstance(item, ProductError)]
    assert len(successes) == 1
    assert len(failures) == 1
    assert failures[0].code == "ERR_PRODUCT_JOB_EXCLUSIVE_INPUT_CONFLICT"
    jobs = first_queue.jobs_for_final_approval(receipt.final_approval_receipt_sha256)
    assert len(jobs) == 1
    assert jobs[0].job_id == successes[0]["job_id"]
    assert all(item["side_effect_started_by_this_call"] is False for item in successes)


def test_checksum_valid_cross_project_collection_fails_closed_via_task044_query(tmp_path: Path) -> None:
    app, _, current, _, _ = application(tmp_path)
    manifest_path = ProductProjectManifestStore.path(tmp_path)
    manifest_path.unlink()
    ProductProjectManifestStore.save(
        tmp_path,
        ProductProjectManifest.create(
            project_id="other-project", project_revision=1, product_version="0.20.1",
            timebase=ProjectTimebase(30, 1), child_bindings=(),
            created_at="2026-08-17T07:00:00.000Z", updated_at="2026-08-17T07:00:00.000Z",
        ),
    )
    DurableProductJobStore._save_unlocked(
        tmp_path,
        DurableProductJobCollection.create("other-project"),
    )
    with pytest.raises(ProductError) as exc:
        app.snapshot(readiness=current)
    assert exc.value.code == "ERR_PRODUCT_JOB_PROJECT_CONFLICT"


@pytest.mark.parametrize("target_kind", ("dangling", "valid"))
def test_symlinked_durable_job_store_fails_closed_before_exists(
    tmp_path: Path, target_kind: str
) -> None:
    app, _, current, _, _ = application(tmp_path)
    store_path = DurableProductJobStore.path(tmp_path)
    if target_kind == "valid":
        _enqueue_once(app, current)
        real_path = store_path.with_name("jobs-real.json")
        store_path.replace(real_path)
        store_path.symlink_to(real_path)
    else:
        store_path.symlink_to(store_path.with_name("missing-jobs.json"))
    with pytest.raises(ProductError) as exc:
        app.snapshot(readiness=_stale_after_export(current))
    assert exc.value.code == "ERR_PRODUCT_JOB_STORE_FILE"
