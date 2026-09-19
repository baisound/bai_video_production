from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
import multiprocessing
import os
from pathlib import Path
import sqlite3

import pytest

from ai_video_production import ProfileSnapshot, SQLiteProductStore
from ai_video_production.errors import ProductError
from ai_video_production.faster_whisper_runtime_contract import FasterWhisperRuntimeRequestV1
from ai_video_production.faster_whisper_runtime_preflight import evaluate_runtime_preflight
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.serialization import canonical_json_bytes
from ai_video_production.task098_runtime_transcription_control import (
    RuntimeTranscriptionAdjudicationDecisionV1,
    RuntimeTranscriptionCancelOutcomeV1,
    RuntimeTranscriptionGenerationAbsenceObservationV1,
)
from ai_video_production.task098_runtime_transcription_coordination import (
    RuntimeTranscriptionCoordinatesV1,
    RuntimeTranscriptionCoordinatorV1,
    derive_cross_version_guard_key,
    derive_output_slot_key,
    derive_runtime_operation_key_v2,
)


T0 = datetime(2026, 9, 20, 6, 0, 0, tzinfo=timezone.utc)
T0_TEXT = "2026-09-20T06:00:00Z"
PROJECT = "task098-r2b1"
ASSET = "ASSET-" + "6" * 26
SOURCE_SHA = "sha256:" + "a" * 64
EXECUTION_SHA = "sha256:" + "d" * 64


class AvailableProbe:
    def supports(self, device: str, compute_type: str) -> bool:
        assert (device, compute_type) == ("cpu", "int8")
        return True


def _process_race_worker(database, output, job_id, coordinates, mode, barrier, queue):
    store = SQLiteProductStore(
        Path(database), require_existing=True, required_job_id=job_id, clock=lambda: T0,
    )
    coordinator = RuntimeTranscriptionCoordinatorV1(
        store=store, output_directory=Path(output), clock=lambda: T0,
    )
    try:
        barrier.wait(10)
        if mode == "cancel":
            coordinator.request_cancel(coordinates)
        else:
            coordinator.acquire_publication_barrier(
                coordinates,
                lambda _barrier: (
                    Path(output) / ".task036-publications" / coordinates.runtime_operation_id
                ).mkdir(parents=True),
            )
        queue.put(mode)
    except ProductError:
        queue.put("lost")
    finally:
        store.close()


def _process_close_worker(database, output, job_id, coordinates, barrier, queue):
    store = SQLiteProductStore(
        Path(database), require_existing=True, required_job_id=job_id, clock=lambda: T0,
    )
    coordinator = RuntimeTranscriptionCoordinatorV1(
        store=store, output_directory=Path(output), clock=lambda: T0,
    )
    try:
        barrier.wait(10)
        queue.put(coordinator.close_confirmed_cancel(coordinates).record_sha256)
    except ProductError as exc:
        queue.put(exc.code)
    finally:
        store.close()


def _process_human_race_worker(
    database, output, job_id, coordinates, decision, mode, barrier, queue,
):
    store = SQLiteProductStore(
        Path(database), require_existing=True, required_job_id=job_id, clock=lambda: T0,
    )
    coordinator = RuntimeTranscriptionCoordinatorV1(
        store=store, output_directory=Path(output), clock=lambda: T0,
    )
    try:
        barrier.wait(10)
        if mode == "human":
            coordinator.close_human_adjudication(coordinates, decision)
            queue.put("human")
        elif mode == "publication":
            coordinator.acquire_publication_barrier(coordinates, lambda _barrier: None)
            queue.put("unexpected")
        else:
            coordinator.request_cancel(coordinates)
            queue.put("unexpected")
    except ProductError:
        queue.put("stale-rejected" if mode != "human" else "human-failed")
    finally:
        store.close()


def make_runtime(tmp_path: Path, *, main_status: str = "IN_PROGRESS"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    output = tmp_path / "output"
    output.mkdir()
    store = SQLiteProductStore(tmp_path / "product.sqlite3", clock=lambda: T0)
    job = store.create_job(ProfileSnapshot.create("task098-r2b1", "1.0.0", {}).profile_snapshot_id)
    request = FasterWhisperRuntimeRequestV1.create("cpu")
    _observation, decision = evaluate_runtime_preflight(
        request, AvailableProbe(), observed_at=T0_TEXT, ttl_seconds=300,
    )
    operation_key = derive_runtime_operation_key_v2(
        project_id=PROJECT,
        source_asset_id=ASSET,
        source_asset_sha256=SOURCE_SHA,
        provider_id="faster-whisper",
        model_id="small",
        execution_config_sha256=EXECUTION_SHA,
        runtime_request=request,
    )
    lease_key = derive_cross_version_guard_key(
        project_id=PROJECT, source_asset_id=ASSET, source_asset_sha256=SOURCE_SHA,
    )
    lease, _ = store.reserve_operation(
        job.job_id, "task036.local_transcription.cross_version_guard.v1", lease_key,
    )
    lease, changed = store.compare_and_set_operation_status(
        lease.operation_id,
        expected_statuses=("PENDING",),
        expected_result_refs=(None,),
        expected_attempt=0,
        status="IN_PROGRESS",
        result_ref="task098-runtime-owner:v2:" + lease_key.rsplit("-", 1)[-1],
        replace_result_ref=True,
    )
    assert changed
    main, _ = store.reserve_operation(job.job_id, "task036.local_transcription.v2", operation_key)
    admission = (
        "task098-runtime-admission:v2:"
        + SOURCE_SHA.removeprefix("sha256:")
        + ":"
        + decision.record_sha256.removeprefix("sha256:")
    )
    main, changed = store.compare_and_set_operation_status(
        main.operation_id,
        expected_statuses=("PENDING",),
        expected_result_refs=(None,),
        expected_attempt=0,
        status=main_status,
        result_ref=admission,
        replace_result_ref=True,
        increment_attempt=True,
    )
    assert changed and main.attempt == 1
    slot_key = derive_output_slot_key(production_job_id=job.job_id, project_id=PROJECT)
    slot, _ = store.reserve_operation(
        job.job_id, "task036.local_transcription_output_slot", slot_key,
    )
    slot, changed = store.compare_and_set_operation_status(
        slot.operation_id,
        expected_statuses=("PENDING",),
        expected_result_refs=(None,),
        expected_attempt=0,
        status="IN_PROGRESS",
        result_ref=main.operation_id,
        replace_result_ref=True,
    )
    assert changed
    coordinates = RuntimeTranscriptionCoordinatesV1(
        production_job_id=job.job_id,
        project_id=PROJECT,
        source_asset_id=ASSET,
        source_asset_sha256=SOURCE_SHA,
        runtime_operation_id=main.operation_id,
        expected_attempt=1,
        runtime_admission_ref=admission,
        runtime_request=request,
        runtime_decision=decision,
        provider_id="faster-whisper",
        model_id="small",
        execution_config_sha256=EXECUTION_SHA,
        slot_operation_id=slot.operation_id,
        recovery_state=(
            "ADJUDICATION_REQUIRED_NO_PUBLICATION"
            if main_status == "PARTIAL" else "ACTIVE_UNKNOWN"
        ),
    )
    coordinator = RuntimeTranscriptionCoordinatorV1(
        store=store, output_directory=output, clock=lambda: T0,
    )
    return coordinator, store, coordinates, output


def make_cancel_outcome(coordinates, request, *, outcome="CANCELLED_BEFORE_PROVIDER_EFFECT"):
    values = {
        "CANCELLED_BEFORE_PROVIDER_EFFECT": (False, True, "PRE_PROVIDER"),
        "CANCELLED_AFTER_COOPERATIVE_BOUNDARY": (True, True, "COOPERATIVE_CHECKPOINT"),
        "STOP_NOT_CONFIRMED": (True, False, "NONE"),
    }
    started, stopped, evidence = values[outcome]
    return RuntimeTranscriptionCancelOutcomeV1.create(
        cancel_request_sha256=request.record_sha256,
        runtime_operation_id=coordinates.runtime_operation_id,
        slot_operation_id=coordinates.slot_operation_id,
        source_asset_sha256=coordinates.source_asset_sha256,
        runtime_admission_ref=coordinates.runtime_admission_ref,
        runtime_request_sha256=coordinates.runtime_request.record_sha256,
        runtime_decision_sha256=coordinates.runtime_decision.record_sha256,
        expected_attempt=coordinates.expected_attempt,
        outcome=outcome,
        provider_execution_started=started,
        provider_stop_confirmed=stopped,
        stop_evidence=evidence,
        acknowledged_at=T0_TEXT,
    )


def make_human_decision(coordinates):
    return RuntimeTranscriptionAdjudicationDecisionV1.create(
        adjudication_id=generate_id(IdKind.OPERATION),
        runtime_operation_id=coordinates.runtime_operation_id,
        slot_operation_id=coordinates.slot_operation_id,
        source_asset_sha256=coordinates.source_asset_sha256,
        runtime_admission_ref=coordinates.runtime_admission_ref,
        runtime_request_sha256=coordinates.runtime_request.record_sha256,
        runtime_decision_sha256=coordinates.runtime_decision.record_sha256,
        expected_attempt=coordinates.expected_attempt,
        decided_at=T0_TEXT,
    )


def test_worker_observation_does_not_reserve_absent_control(tmp_path: Path) -> None:
    coordinator, store, coordinates, _output = make_runtime(tmp_path)
    assert coordinator.observe_cancel_request(coordinates) is None
    assert store.find_operation(coordinates.production_job_id, coordinates.control_key) is None


def test_worker_stop_not_confirmed_binds_outcome_without_terminal_or_slot_release(
    tmp_path: Path,
) -> None:
    coordinator, store, coordinates, _output = make_runtime(tmp_path)
    coordinator.request_cancel(coordinates)
    first = coordinator.acknowledge_worker_cancel(
        coordinates, provider_execution_started=True, provider_stop_confirmed=False,
    )
    second = coordinator.acknowledge_worker_cancel(
        coordinates, provider_execution_started=True, provider_stop_confirmed=False,
    )
    assert first.to_dict() == second.to_dict()
    assert first.outcome == "STOP_NOT_CONFIRMED"
    main = store.get_operation(coordinates.runtime_operation_id)
    slot = store.get_operation(coordinates.slot_operation_id)
    assert (main.status, main.result_ref, main.attempt) == (
        "IN_PROGRESS", coordinates.runtime_admission_ref, coordinates.expected_attempt,
    )
    assert (slot.status, slot.result_ref) == ("IN_PROGRESS", coordinates.runtime_operation_id)


def test_worker_confirmed_pre_provider_cancel_is_idempotent_terminal_closure(
    tmp_path: Path,
) -> None:
    coordinator, store, coordinates, _output = make_runtime(tmp_path)
    coordinator.request_cancel(coordinates)
    first = coordinator.acknowledge_worker_cancel(
        coordinates, provider_execution_started=False, provider_stop_confirmed=True,
    )
    second = coordinator.acknowledge_worker_cancel(
        coordinates, provider_execution_started=False, provider_stop_confirmed=True,
    )
    assert first.to_dict() == second.to_dict()
    main = store.get_operation(coordinates.runtime_operation_id)
    slot = store.get_operation(coordinates.slot_operation_id)
    assert main.status == "FAILED"
    assert main.result_ref == (
        "task098-runtime-cancelled:v1:" + first.record_sha256.removeprefix("sha256:")
    )
    assert (slot.status, slot.result_ref) == ("PENDING", coordinates.runtime_operation_id)


def test_publication_completion_requires_main_digest_and_is_idempotent(tmp_path: Path) -> None:
    coordinator, store, coordinates, _output = make_runtime(tmp_path)
    digest = "sha256:" + "f" * 64
    barrier = coordinator.acquire_publication_barrier(coordinates, lambda _barrier: None)
    main, changed = store.compare_and_set_operation_status(
        coordinates.runtime_operation_id,
        expected_statuses=("IN_PROGRESS",),
        expected_result_refs=(coordinates.runtime_admission_ref,),
        expected_attempt=coordinates.expected_attempt,
        status="PARTIAL",
        result_ref=digest,
        replace_result_ref=True,
    )
    assert changed and main.result_ref == digest
    first = coordinator.complete_publication(coordinates, digest, barrier)
    second = coordinator.reconcile_publication(coordinates, digest)
    assert first.to_dict() == second.to_dict()
    control = store.find_operation(coordinates.production_job_id, coordinates.control_key)
    assert control is not None
    assert control.status == "COMPLETED"
    assert control.result_ref == (
        "task098-runtime-commit-barrier:v1:"
        + barrier.record_sha256.removeprefix("sha256:")
    )


def test_completed_publication_rejects_foreign_control_identity(tmp_path: Path) -> None:
    coordinator, store, coordinates, _output = make_runtime(tmp_path)
    digest = "sha256:" + "f" * 64
    barrier = coordinator.acquire_publication_barrier(coordinates, lambda _barrier: None)
    _main, changed = store.compare_and_set_operation_status(
        coordinates.runtime_operation_id,
        expected_statuses=("IN_PROGRESS",),
        expected_result_refs=(coordinates.runtime_admission_ref,),
        expected_attempt=coordinates.expected_attempt,
        status="PARTIAL",
        result_ref=digest,
        replace_result_ref=True,
    )
    assert changed
    coordinator.complete_publication(coordinates, digest, barrier)
    control = store.find_operation(coordinates.production_job_id, coordinates.control_key)
    assert control is not None
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "UPDATE operations SET command_type=? WHERE operation_id=?",
            ("foreign.publication.control", control.operation_id),
        )
    with pytest.raises(ProductError) as rejected:
        coordinator.complete_publication(coordinates, digest, barrier)
    assert rejected.value.code == "ERR_TASK098_CONTROL_CONFLICT"


def test_cancel_request_is_deterministic_and_idempotent(tmp_path: Path) -> None:
    coordinator, store, coordinates, output = make_runtime(tmp_path)
    first = coordinator.request_cancel(coordinates)
    second = coordinator.request_cancel(coordinates)
    assert first.to_dict() == second.to_dict()
    control = store.find_operation(coordinates.production_job_id, coordinates.control_key)
    assert control is not None
    assert first.cancel_request_id == control.operation_id
    assert first.requested_at == datetime.fromisoformat(
        control.created_at.removesuffix("Z") + "+00:00",
    ).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert control.status == "IN_PROGRESS" and control.result_ref == (
        "task098-runtime-cancel-request:v1:"
        + first.record_sha256.removeprefix("sha256:")
    )
    record = output / ".task036-runtime-control" / coordinates.runtime_operation_id / (
        "cancel-request-" + first.record_sha256.removeprefix("sha256:") + ".json"
    )
    assert record.is_file()


def test_publication_and_cancel_request_have_exactly_one_winner(tmp_path: Path) -> None:
    coordinator, store, coordinates, output = make_runtime(tmp_path)

    def cancel():
        try:
            coordinator.request_cancel(coordinates)
            return "cancel"
        except ProductError:
            return "lost"

    def publish():
        try:
            coordinator.acquire_publication_barrier(
                coordinates,
                lambda _barrier: (
                    output / ".task036-publications" / coordinates.runtime_operation_id
                ).mkdir(parents=True),
            )
            return "publication"
        except ProductError:
            return "lost"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = {pool.submit(cancel), pool.submit(publish)}
        outcomes = sorted(item.result() for item in results)
    assert outcomes.count("lost") == 1
    assert len({item for item in outcomes if item != "lost"}) == 1
    control = store.find_operation(coordinates.production_job_id, coordinates.control_key)
    assert control is not None and control.status == "IN_PROGRESS"


def test_publication_and_cancel_request_process_race_has_one_winner(tmp_path: Path) -> None:
    _coordinator, store, coordinates, output = make_runtime(tmp_path)
    database = store.path
    store.close()
    method = "fork" if "fork" in multiprocessing.get_all_start_methods() else "spawn"
    context = multiprocessing.get_context(method)
    barrier = context.Barrier(2)
    queue = context.Queue()
    processes = [
        context.Process(
            target=_process_race_worker,
            args=(str(database), str(output), coordinates.production_job_id, coordinates, mode, barrier, queue),
        )
        for mode in ("cancel", "publication")
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(15)
        assert process.exitcode == 0
    outcomes = sorted(queue.get(timeout=2) for _ in processes)
    assert outcomes.count("lost") == 1
    assert len({item for item in outcomes if item != "lost"}) == 1
    checked = SQLiteProductStore(
        database, require_existing=True, required_job_id=coordinates.production_job_id,
    )
    control = checked.find_operation(coordinates.production_job_id, coordinates.control_key)
    assert control is not None and control.status == "IN_PROGRESS"
    checked.close()


def test_each_publication_cancel_invocation_order_preserves_first_winner(tmp_path: Path) -> None:
    cancel_first, store_a, coordinates_a, _output_a = make_runtime(tmp_path / "cancel-first")
    request = cancel_first.request_cancel(coordinates_a)
    with pytest.raises(ProductError):
        cancel_first.acquire_publication_barrier(coordinates_a, lambda _barrier: None)
    control_a = store_a.find_operation(coordinates_a.production_job_id, coordinates_a.control_key)
    assert control_a is not None and control_a.result_ref == (
        "task098-runtime-cancel-request:v1:"
        + request.record_sha256.removeprefix("sha256:")
    )

    publication_first, store_b, coordinates_b, _output_b = make_runtime(tmp_path / "publication-first")
    barrier = publication_first.acquire_publication_barrier(coordinates_b, lambda _barrier: None)
    with pytest.raises(ProductError):
        publication_first.request_cancel(coordinates_b)
    control_b = store_b.find_operation(coordinates_b.production_job_id, coordinates_b.control_key)
    assert control_b is not None and control_b.result_ref == (
        "task098-runtime-commit-barrier:v1:"
        + barrier.record_sha256.removeprefix("sha256:")
    )


def test_confirmed_cancel_closes_main_then_control_then_releases_slot(tmp_path: Path) -> None:
    coordinator, store, coordinates, _output = make_runtime(tmp_path)
    request = coordinator.request_cancel(coordinates)
    outcome = coordinator.bind_cancel_outcome(
        coordinates, make_cancel_outcome(coordinates, request),
    )
    commit = coordinator.close_confirmed_cancel(coordinates)

    main = store.get_operation(coordinates.runtime_operation_id)
    control = store.find_operation(coordinates.production_job_id, coordinates.control_key)
    slot = store.get_operation(coordinates.slot_operation_id)
    assert main.status == "FAILED" and main.attempt == coordinates.expected_attempt
    assert main.result_ref == "task098-runtime-cancelled:v1:" + outcome.record_sha256.removeprefix("sha256:")
    assert control is not None and (control.status, control.result_ref) == (
        "COMPLETED",
        "task098-runtime-terminal-commit:v1:"
        + commit.record_sha256.removeprefix("sha256:"),
    )
    assert (slot.status, slot.result_ref) == ("PENDING", coordinates.runtime_operation_id)
    assert coordinator.close_confirmed_cancel(coordinates).record_sha256 == commit.record_sha256


def test_stop_not_confirmed_never_acquires_terminal_barrier(tmp_path: Path) -> None:
    coordinator, store, coordinates, _output = make_runtime(tmp_path)
    request = coordinator.request_cancel(coordinates)
    outcome = coordinator.bind_cancel_outcome(
        coordinates,
        make_cancel_outcome(coordinates, request, outcome="STOP_NOT_CONFIRMED"),
    )
    with pytest.raises(ProductError, match="not confirmed"):
        coordinator.close_confirmed_cancel(coordinates)
    control = store.find_operation(coordinates.production_job_id, coordinates.control_key)
    assert control is not None and (control.status, control.result_ref) == (
        "IN_PROGRESS",
        "task098-runtime-cancel-outcome:v1:"
        + outcome.record_sha256.removeprefix("sha256:"),
    )
    assert store.get_operation(coordinates.runtime_operation_id).status == "IN_PROGRESS"
    assert store.get_operation(coordinates.slot_operation_id).status == "IN_PROGRESS"


@pytest.mark.parametrize(
    "malformed_kind",
    ["bare", "wrong-kind", "wrong-version", "uppercase", "suffix"],
)
def test_malformed_cancel_request_control_ref_is_refused_without_main_or_slot_effect(
    malformed_kind: str, tmp_path: Path,
) -> None:
    coordinator, store, coordinates, _output = make_runtime(tmp_path)
    request = coordinator.request_cancel(coordinates)
    control = store.find_operation(coordinates.production_job_id, coordinates.control_key)
    assert control is not None and control.result_ref is not None
    digest = request.record_sha256.removeprefix("sha256:")
    malformed = {
        "bare": request.record_sha256,
        "wrong-kind": "task098-runtime-cancel-outcome:v1:" + digest,
        "wrong-version": "task098-runtime-cancel-request:v2:" + digest,
        "uppercase": "task098-runtime-cancel-request:v1:" + digest.upper(),
        "suffix": "task098-runtime-cancel-request:v1:" + digest + "x",
    }[malformed_kind]
    _corrupted, changed = store.compare_and_set_operation_status(
        control.operation_id,
        expected_statuses=("IN_PROGRESS",),
        expected_result_refs=(control.result_ref,),
        expected_attempt=0,
        status="IN_PROGRESS",
        result_ref=malformed,
        replace_result_ref=True,
    )
    assert changed
    main_before = store.get_operation(coordinates.runtime_operation_id)
    slot_before = store.get_operation(coordinates.slot_operation_id)

    with pytest.raises(ProductError, match="typed authoritative request"):
        coordinator.bind_cancel_outcome(
            coordinates, make_cancel_outcome(coordinates, request),
        )

    assert store.get_operation(coordinates.runtime_operation_id) == main_before
    assert store.get_operation(coordinates.slot_operation_id) == slot_before


def test_barrier_ref_drift_after_generation_observation_blocks_main_terminal_cas(
    tmp_path: Path,
) -> None:
    coordinator, store, coordinates, output = make_runtime(tmp_path)
    request = coordinator.request_cancel(coordinates)
    coordinator.bind_cancel_outcome(coordinates, make_cancel_outcome(coordinates, request))

    def drift(stage: str) -> None:
        if stage != "after_generation_observation":
            return
        control = store.find_operation(coordinates.production_job_id, coordinates.control_key)
        assert control is not None and control.status == "PARTIAL"
        assert control.result_ref is not None
        foreign_barrier_ref = "task098-runtime-commit-barrier:v1:" + "e" * 64
        assert foreign_barrier_ref != control.result_ref
        _drifted, changed = store.compare_and_set_operation_status(
            control.operation_id,
            expected_statuses=("PARTIAL",),
            expected_result_refs=(control.result_ref,),
            expected_attempt=0,
            status="PARTIAL",
            result_ref=foreign_barrier_ref,
            replace_result_ref=True,
        )
        assert changed

    with pytest.raises(ProductError, match="control row"):
        coordinator.close_confirmed_cancel(coordinates, fault_hook=drift)

    main = store.get_operation(coordinates.runtime_operation_id)
    slot = store.get_operation(coordinates.slot_operation_id)
    assert (main.status, main.result_ref, main.attempt) == (
        "IN_PROGRESS", coordinates.runtime_admission_ref, coordinates.expected_attempt,
    )
    assert (slot.status, slot.result_ref) == (
        "IN_PROGRESS", coordinates.runtime_operation_id,
    )
    control = store.find_operation(coordinates.production_job_id, coordinates.control_key)
    assert control is not None and (control.status, control.result_ref) == (
        "PARTIAL", "task098-runtime-commit-barrier:v1:" + "e" * 64,
    )
    assert not (
        output / ".task036-runtime-control" / coordinates.runtime_operation_id
        / "terminal-commit.json"
    ).exists()


def test_late_generation_after_first_observation_blocks_main_cas(tmp_path: Path) -> None:
    coordinator, store, coordinates, output = make_runtime(tmp_path)
    request = coordinator.request_cancel(coordinates)
    coordinator.bind_cancel_outcome(coordinates, make_cancel_outcome(coordinates, request))

    def inject(stage: str) -> None:
        if stage == "after_first_generation_observation":
            (output / ".task036-publications" / coordinates.runtime_operation_id).mkdir(parents=True)

    with pytest.raises(ProductError, match="absence"):
        coordinator.close_confirmed_cancel(coordinates, fault_hook=inject)
    assert store.get_operation(coordinates.runtime_operation_id).status == "IN_PROGRESS"
    assert store.get_operation(coordinates.slot_operation_id).status == "IN_PROGRESS"
    control = store.find_operation(coordinates.production_job_id, coordinates.control_key)
    assert control is not None and control.status == "PARTIAL"


def test_crash_after_main_cas_resumes_without_replay(tmp_path: Path) -> None:
    coordinator, store, coordinates, _output = make_runtime(tmp_path)
    request = coordinator.request_cancel(coordinates)
    coordinator.bind_cancel_outcome(coordinates, make_cancel_outcome(coordinates, request))

    def crash(stage: str) -> None:
        if stage == "after_main_cas":
            raise RuntimeError("injected crash")

    with pytest.raises(RuntimeError, match="injected crash"):
        coordinator.close_confirmed_cancel(coordinates, fault_hook=crash)
    assert store.get_operation(coordinates.runtime_operation_id).status == "FAILED"
    assert store.get_operation(coordinates.slot_operation_id).status == "IN_PROGRESS"
    resumed = coordinator.close_confirmed_cancel(coordinates)
    assert resumed.closure_kind == "CONFIRMED_CANCEL"
    assert store.get_operation(coordinates.slot_operation_id).status == "PENDING"


@pytest.mark.parametrize("crash_stage", [
    "after_terminal_barrier",
    "after_generation_observation",
    "after_terminal_commit_write",
    "after_control_commit",
    "after_slot_release",
])
def test_every_terminal_crash_boundary_resumes_exactly(crash_stage: str, tmp_path: Path) -> None:
    coordinator, store, coordinates, _output = make_runtime(tmp_path)
    request = coordinator.request_cancel(coordinates)
    coordinator.bind_cancel_outcome(coordinates, make_cancel_outcome(coordinates, request))

    def crash(stage: str) -> None:
        if stage == crash_stage:
            raise RuntimeError(crash_stage)

    with pytest.raises(RuntimeError, match=crash_stage):
        coordinator.close_confirmed_cancel(coordinates, fault_hook=crash)
    commit = coordinator.close_confirmed_cancel(coordinates)
    assert commit.closure_kind == "CONFIRMED_CANCEL"
    assert store.get_operation(coordinates.runtime_operation_id).status == "FAILED"
    assert store.get_operation(coordinates.slot_operation_id).status == "PENDING"
    control = store.find_operation(coordinates.production_job_id, coordinates.control_key)
    assert control is not None and control.status == "COMPLETED"


def test_duplicate_terminal_closure_threads_converge(tmp_path: Path) -> None:
    coordinator, store, coordinates, _output = make_runtime(tmp_path)
    request = coordinator.request_cancel(coordinates)
    coordinator.bind_cancel_outcome(coordinates, make_cancel_outcome(coordinates, request))
    with ThreadPoolExecutor(max_workers=2) as pool:
        commits = list(pool.map(lambda _index: coordinator.close_confirmed_cancel(coordinates), range(2)))
    assert commits[0].record_sha256 == commits[1].record_sha256
    assert store.get_operation(coordinates.slot_operation_id).status == "PENDING"


def test_duplicate_terminal_closure_processes_converge(tmp_path: Path) -> None:
    coordinator, store, coordinates, output = make_runtime(tmp_path)
    request = coordinator.request_cancel(coordinates)
    coordinator.bind_cancel_outcome(coordinates, make_cancel_outcome(coordinates, request))
    database = store.path
    store.close()
    method = "fork" if "fork" in multiprocessing.get_all_start_methods() else "spawn"
    context = multiprocessing.get_context(method)
    barrier = context.Barrier(2)
    queue = context.Queue()
    processes = [
        context.Process(
            target=_process_close_worker,
            args=(str(database), str(output), coordinates.production_job_id, coordinates, barrier, queue),
        )
        for _index in range(2)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(15)
        assert process.exitcode == 0
    digests = [queue.get(timeout=2) for _ in processes]
    assert digests[0] == digests[1]
    assert digests[0].startswith("sha256:")


def test_human_adjudication_requires_partial_and_closes_without_cancel(tmp_path: Path) -> None:
    coordinator, store, coordinates, _output = make_runtime(tmp_path, main_status="PARTIAL")
    decision = make_human_decision(coordinates)
    commit = coordinator.close_human_adjudication(coordinates, decision)
    assert commit.closure_kind == "HUMAN_ADJUDICATED_FAILED"
    assert store.get_operation(coordinates.runtime_operation_id).result_ref == (
        "task098-runtime-adjudicated-failed:v1:"
        + decision.record_sha256.removeprefix("sha256:")
    )
    assert store.get_operation(coordinates.slot_operation_id).status == "PENDING"


def test_publication_and_stale_cancel_have_zero_effect_after_human_partial(tmp_path: Path) -> None:
    coordinator, store, coordinates, _output = make_runtime(tmp_path, main_status="PARTIAL")
    with pytest.raises(ProductError):
        coordinator.request_cancel(coordinates)
    with pytest.raises(ProductError):
        coordinator.acquire_publication_barrier(coordinates, lambda _barrier: None)
    assert store.find_operation(coordinates.production_job_id, coordinates.control_key) is None
    commit = coordinator.close_human_adjudication(coordinates, make_human_decision(coordinates))
    assert commit.closure_kind == "HUMAN_ADJUDICATED_FAILED"


@pytest.mark.parametrize("stale_path", ["publication", "cancel"])
def test_human_closure_wins_stale_thread_race(stale_path: str, tmp_path: Path) -> None:
    coordinator, store, coordinates, _output = make_runtime(tmp_path, main_status="PARTIAL")
    decision = make_human_decision(coordinates)

    def stale():
        try:
            if stale_path == "publication":
                coordinator.acquire_publication_barrier(coordinates, lambda _barrier: None)
            else:
                coordinator.request_cancel(coordinates)
            return "unexpected"
        except ProductError:
            return "stale-rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        stale_future = pool.submit(stale)
        human_future = pool.submit(coordinator.close_human_adjudication, coordinates, decision)
    assert stale_future.result() == "stale-rejected"
    assert human_future.result().closure_kind == "HUMAN_ADJUDICATED_FAILED"
    assert store.get_operation(coordinates.slot_operation_id).status == "PENDING"


@pytest.mark.parametrize("stale_path", ["publication", "cancel"])
def test_human_closure_wins_stale_process_race(stale_path: str, tmp_path: Path) -> None:
    coordinator, store, coordinates, output = make_runtime(tmp_path, main_status="PARTIAL")
    decision = make_human_decision(coordinates)
    database = store.path
    store.close()
    method = "fork" if "fork" in multiprocessing.get_all_start_methods() else "spawn"
    context = multiprocessing.get_context(method)
    barrier = context.Barrier(2)
    queue = context.Queue()
    processes = [
        context.Process(
            target=_process_human_race_worker,
            args=(
                str(database), str(output), coordinates.production_job_id,
                coordinates, decision, mode, barrier, queue,
            ),
        )
        for mode in ("human", stale_path)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(15)
        assert process.exitcode == 0
    assert sorted(queue.get(timeout=2) for _ in processes) == ["human", "stale-rejected"]
    checked = SQLiteProductStore(
        database, require_existing=True, required_job_id=coordinates.production_job_id,
    )
    assert checked.get_operation(coordinates.slot_operation_id).status == "PENDING"
    checked.close()


def test_completed_resume_rejects_wrong_api_or_human_decision(tmp_path: Path) -> None:
    coordinator, _store, coordinates, _output = make_runtime(tmp_path, main_status="PARTIAL")
    decision = make_human_decision(coordinates)
    coordinator.close_human_adjudication(coordinates, decision)
    with pytest.raises(ProductError, match="commit anchor"):
        coordinator.close_confirmed_cancel(coordinates)
    foreign = make_human_decision(coordinates)
    assert foreign.record_sha256 != decision.record_sha256
    with pytest.raises(ProductError, match="chain"):
        coordinator.close_human_adjudication(coordinates, foreign)


def test_stale_attempt_cannot_close_re_admitted_main(tmp_path: Path) -> None:
    coordinator, store, coordinates, _output = make_runtime(tmp_path)
    request = coordinator.request_cancel(coordinates)
    coordinator.bind_cancel_outcome(coordinates, make_cancel_outcome(coordinates, request))
    main = store.get_operation(coordinates.runtime_operation_id)
    returned, changed = store.compare_and_set_operation_status(
        main.operation_id,
        expected_statuses=("IN_PROGRESS",),
        expected_result_refs=(coordinates.runtime_admission_ref,),
        expected_attempt=1,
        status="PENDING",
        result_ref=coordinates.runtime_admission_ref,
        replace_result_ref=True,
    )
    assert changed and returned.attempt == 1
    returned, changed = store.compare_and_set_operation_status(
        main.operation_id,
        expected_statuses=("PENDING",),
        expected_result_refs=(coordinates.runtime_admission_ref,),
        expected_attempt=1,
        status="IN_PROGRESS",
        result_ref=coordinates.runtime_admission_ref,
        replace_result_ref=True,
        increment_attempt=True,
    )
    assert changed and returned.attempt == 2
    with pytest.raises(ProductError, match="attempt|coordinate"):
        coordinator.close_confirmed_cancel(coordinates)
    assert store.get_operation(coordinates.runtime_operation_id).status == "IN_PROGRESS"


def test_tampered_authoritative_evidence_fails_closed(tmp_path: Path) -> None:
    coordinator, store, coordinates, output = make_runtime(tmp_path)
    request = coordinator.request_cancel(coordinates)
    record = output / ".task036-runtime-control" / coordinates.runtime_operation_id / (
        "cancel-request-" + request.record_sha256.removeprefix("sha256:") + ".json"
    )
    record.write_bytes(b"{}")
    with pytest.raises(ProductError, match="Evidence"):
        coordinator.request_cancel(coordinates)
    assert store.get_operation(coordinates.runtime_operation_id).status == "IN_PROGRESS"
    assert store.get_operation(coordinates.slot_operation_id).status == "IN_PROGRESS"


@pytest.mark.parametrize("corruption", ["missing", "oversized", "symlink"])
def test_missing_oversized_or_symlink_evidence_fails_closed(
    corruption: str, tmp_path: Path,
) -> None:
    coordinator, store, coordinates, output = make_runtime(tmp_path)
    request = coordinator.request_cancel(coordinates)
    record = output / ".task036-runtime-control" / coordinates.runtime_operation_id / (
        "cancel-request-" + request.record_sha256.removeprefix("sha256:") + ".json"
    )
    record.unlink()
    if corruption == "oversized":
        record.write_bytes(b"x" * (256 * 1024 + 1))
    elif corruption == "symlink":
        target = tmp_path / "foreign.json"
        target.write_bytes(canonical_json_bytes(request.to_dict()))
        try:
            record.symlink_to(target)
        except (OSError, NotImplementedError):
            pytest.skip("symlink creation is unavailable")
    with pytest.raises((ProductError, OSError)):
        coordinator.request_cancel(coordinates)
    assert store.get_operation(coordinates.runtime_operation_id).status == "IN_PROGRESS"
    assert store.get_operation(coordinates.slot_operation_id).status == "IN_PROGRESS"


def test_symlink_generation_lock_fails_before_control_cas(tmp_path: Path) -> None:
    coordinator, store, coordinates, output = make_runtime(tmp_path)
    operation_root = coordinator._evidence(coordinates).operation_root
    target = tmp_path / "foreign-lock"
    target.write_bytes(b"0")
    try:
        (operation_root / "generation-exclusion.lock").symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ProductError, match="lock"):
        coordinator.acquire_publication_barrier(coordinates, lambda _barrier: None)
    assert store.find_operation(coordinates.production_job_id, coordinates.control_key) is None
    assert store.get_operation(coordinates.runtime_operation_id).status == "IN_PROGRESS"
    assert output.is_dir()


def test_output_identity_replacement_blocks_absence_closure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator, store, coordinates, output = make_runtime(tmp_path)
    request = coordinator.request_cancel(coordinates)
    coordinator.bind_cancel_outcome(coordinates, make_cancel_outcome(coordinates, request))
    original = __import__(
        "ai_video_production.task098_runtime_transcription_coordination",
        fromlist=["_PinnedDirectory"],
    )._PinnedDirectory.child_exists
    replaced = False

    def replacing_child_exists(directory, name):
        nonlocal replaced
        result = original(directory, name)
        if name == ".task036-publications" and not replaced:
            replaced = True
            backup = output.with_name(output.name + "-replaced")
            output.rename(backup)
            output.mkdir()
        return result

    monkeypatch.setattr(
        "ai_video_production.task098_runtime_transcription_coordination._PinnedDirectory.child_exists",
        replacing_child_exists,
    )
    with pytest.raises(ProductError):
        coordinator.close_confirmed_cancel(coordinates)
    assert store.get_operation(coordinates.runtime_operation_id).status == "IN_PROGRESS"
    assert store.get_operation(coordinates.slot_operation_id).status == "IN_PROGRESS"


def test_main_cas_crash_then_slot_change_cannot_commit_control(tmp_path: Path) -> None:
    coordinator, store, coordinates, output = make_runtime(tmp_path)
    request = coordinator.request_cancel(coordinates)
    coordinator.bind_cancel_outcome(coordinates, make_cancel_outcome(coordinates, request))

    def crash(stage: str) -> None:
        if stage == "after_main_cas":
            raise RuntimeError("crash")

    with pytest.raises(RuntimeError):
        coordinator.close_confirmed_cancel(coordinates, fault_hook=crash)
    slot = store.get_operation(coordinates.slot_operation_id)
    _released, changed = store.compare_and_set_operation_status(
        slot.operation_id,
        expected_statuses=("IN_PROGRESS",),
        expected_result_refs=(coordinates.runtime_operation_id,),
        expected_attempt=slot.attempt,
        status="PENDING",
        result_ref=coordinates.runtime_operation_id,
        replace_result_ref=True,
    )
    assert changed
    with pytest.raises(ProductError, match="slot"):
        coordinator.close_confirmed_cancel(coordinates)
    control = store.find_operation(coordinates.production_job_id, coordinates.control_key)
    assert control is not None and control.status == "PARTIAL"
    assert not (
        output / ".task036-runtime-control" / coordinates.runtime_operation_id
        / "terminal-commit.json"
    ).exists()


def test_terminal_commit_write_then_slot_change_cannot_commit_control(tmp_path: Path) -> None:
    coordinator, store, coordinates, _output = make_runtime(tmp_path)
    request = coordinator.request_cancel(coordinates)
    coordinator.bind_cancel_outcome(coordinates, make_cancel_outcome(coordinates, request))

    def crash(stage: str) -> None:
        if stage == "after_terminal_commit_write":
            raise RuntimeError("crash")

    with pytest.raises(RuntimeError):
        coordinator.close_confirmed_cancel(coordinates, fault_hook=crash)
    slot = store.get_operation(coordinates.slot_operation_id)
    _released, changed = store.compare_and_set_operation_status(
        slot.operation_id,
        expected_statuses=("IN_PROGRESS",),
        expected_result_refs=(coordinates.runtime_operation_id,),
        expected_attempt=slot.attempt,
        status="PENDING",
        result_ref=coordinates.runtime_operation_id,
        replace_result_ref=True,
    )
    assert changed
    with pytest.raises(ProductError, match="slot"):
        coordinator.close_confirmed_cancel(coordinates)
    control = store.find_operation(coordinates.production_job_id, coordinates.control_key)
    assert control is not None and control.status == "PARTIAL"


def test_changed_completed_control_cannot_release_retained_slot(tmp_path: Path) -> None:
    coordinator, store, coordinates, _output = make_runtime(tmp_path)
    request = coordinator.request_cancel(coordinates)
    coordinator.bind_cancel_outcome(coordinates, make_cancel_outcome(coordinates, request))

    def crash(stage: str) -> None:
        if stage == "after_control_commit":
            raise RuntimeError("crash")

    with pytest.raises(RuntimeError):
        coordinator.close_confirmed_cancel(coordinates, fault_hook=crash)
    control = store.find_operation(coordinates.production_job_id, coordinates.control_key)
    assert control is not None and control.status == "COMPLETED" and control.result_ref
    _changed_control, changed = store.compare_and_set_operation_status(
        control.operation_id,
        expected_statuses=("COMPLETED",),
        expected_result_refs=(control.result_ref,),
        expected_attempt=0,
        status="FAILED",
        result_ref=control.result_ref,
        replace_result_ref=True,
    )
    assert changed
    with pytest.raises(ProductError):
        coordinator.close_confirmed_cancel(coordinates)
    assert store.get_operation(coordinates.slot_operation_id).status == "IN_PROGRESS"


def test_foreign_generation_anchor_blocks_resume(tmp_path: Path) -> None:
    coordinator, store, coordinates, output = make_runtime(tmp_path)
    request = coordinator.request_cancel(coordinates)
    coordinator.bind_cancel_outcome(coordinates, make_cancel_outcome(coordinates, request))

    def crash(stage: str) -> None:
        if stage == "after_generation_observation":
            raise RuntimeError("crash")

    with pytest.raises(RuntimeError):
        coordinator.close_confirmed_cancel(coordinates, fault_hook=crash)
    anchor = (
        output / ".task036-runtime-control" / coordinates.runtime_operation_id
        / "generation-absence.json"
    )
    foreign = RuntimeTranscriptionGenerationAbsenceObservationV1.create(
        runtime_operation_id=coordinates.runtime_operation_id,
        slot_operation_id=coordinates.slot_operation_id,
        source_asset_sha256=coordinates.source_asset_sha256,
        runtime_admission_ref=coordinates.runtime_admission_ref,
        expected_attempt=coordinates.expected_attempt,
        commit_barrier_sha256="sha256:" + "e" * 64,
        observation="EXACT_GENERATION_ABSENT",
        observed_at=T0_TEXT,
    )
    anchor.write_bytes(canonical_json_bytes(foreign.to_dict()))
    with pytest.raises(ProductError, match="barrier|Evidence|absence"):
        coordinator.close_confirmed_cancel(coordinates)
    assert store.get_operation(coordinates.runtime_operation_id).status == "IN_PROGRESS"


def test_foreign_coordinate_and_recovery_state_have_zero_effect(tmp_path: Path) -> None:
    coordinator, store, coordinates, _output = make_runtime(tmp_path, main_status="PARTIAL")
    wrong = replace(coordinates, recovery_state="ACTIVE_UNKNOWN")
    with pytest.raises(ValueError, match="adjudication recovery state"):
        coordinator.close_human_adjudication(wrong, make_human_decision(wrong))
    assert store.get_operation(coordinates.runtime_operation_id).status == "PARTIAL"
    assert store.get_operation(coordinates.slot_operation_id).status == "IN_PROGRESS"
