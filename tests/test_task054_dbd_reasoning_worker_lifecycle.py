from __future__ import annotations

from dataclasses import replace
import subprocess

import pytest

from ai_video_production.dbd_reasoning_operation_view import OperationFailureView, OperationStage
from ai_video_production.dbd_reasoning_worker_lifecycle import (
    NoConsoleWorkerProcessController,
    WorkerLaunchSpec,
    WorkerLifecycleRegistry,
    WorkerLifecycleRecord,
    WorkerRequest,
    WorkerResourceCeiling,
    no_console_popen_options,
    sanitized_worker_environment,
)
from ai_video_production.errors import ProductError


SHA = "sha256:" + "a" * 64
IDEMPOTENCY = "task054-idempotency-" + "b" * 64
AUTHORITY_REF = "authorization://task054/01ARZ3NDEKTSV4RRFFQ69G5FAV"
CHECKPOINT = "task054-checkpoint://sha256/" + "c" * 64


def _request(**changes: object) -> WorkerRequest:
    values: dict[str, object] = {
        "workspace_id": "workspace-dbd",
        "action_kind": "OFFLINE_FIXTURE",
        "idempotency_key": IDEMPOTENCY,
        "expected_dataset_revision": 3,
        "expected_binding_revision": 4,
        "plan_sha256": SHA,
        "authorization_ref": AUTHORITY_REF,
        "resource_ceiling": WorkerResourceCeiling(3600, 8192, 1024 * 1024),
        "retry_external_or_paid": False,
        "total_units": 100,
    }
    values.update(changes)
    return WorkerRequest(**values)


def _failure() -> OperationFailureView:
    return OperationFailureView(
        error_code="ERR_TASK054_RESOURCE_LIMIT",
        what_happened_ja="設定された資源上限で安全に停止しました。",
        data_safety_ja="入力Datasetは変更されていません。",
        saved_evidence_ja="最後の検証済みCheckpointを保持しました。",
        next_safe_action_ja="小さい計画を確認できます。",
        retry_effect_ja="自動再試行は行いません。",
        technical_details="resource ceiling reached",
        retry_external_or_paid=False,
    )


def _running() -> WorkerLifecycleRecord:
    queued = WorkerLifecycleRecord.create(_request())
    return queued.start(expected_revision=queued.state_revision)


def test_request_identity_is_deterministic_and_cannot_grant_authority() -> None:
    first = _request()
    second = _request()
    assert first.request_sha256 == second.request_sha256
    assert first.operation_id == second.operation_id
    assert first.operation_id.startswith("task054-operation-")
    with pytest.raises(ValueError, match="cannot grant"):
        replace(first, authority_effect="EXECUTE")


def test_progress_is_monotonic_and_stale_actions_fail_closed() -> None:
    running = _running()
    progressed = running.update_progress(
        expected_revision=running.state_revision,
        phase_label_ja="入力を検証中", current=25,
        elapsed_seconds=10, estimated_remaining_seconds=30,
    )
    assert progressed.to_view().progress_milli == 250
    with pytest.raises(ProductError) as stale:
        progressed.update_progress(
            expected_revision=running.state_revision,
            phase_label_ja="古い更新", current=30,
            elapsed_seconds=11, estimated_remaining_seconds=20,
        )
    assert stale.value.code == "ERR_TASK054_WORKER_STALE_REVISION"
    with pytest.raises(ProductError) as regression:
        progressed.update_progress(
            expected_revision=progressed.state_revision,
            phase_label_ja="逆行", current=24,
            elapsed_seconds=11, estimated_remaining_seconds=20,
        )
    assert regression.value.code == "ERR_TASK054_WORKER_PROGRESS_REGRESSION"


def test_checkpoint_then_cancel_preserves_verified_checkpoint() -> None:
    running = _running().update_progress(
        expected_revision=2, phase_label_ja="学習候補を処理中",
        current=20, elapsed_seconds=20, estimated_remaining_seconds=80,
    )
    checking = running.begin_checkpoint(expected_revision=running.state_revision)
    saved = checking.checkpoint_saved(
        expected_revision=checking.state_revision, checkpoint_ref=CHECKPOINT,
    )
    cancelling = saved.request_cancel(expected_revision=saved.state_revision)
    assert cancelling.stage is OperationStage.CANCELLING
    assert cancelling.to_view().cancel_available is False
    cancelled = cancelling.finish_cancel(expected_revision=cancelling.state_revision)
    assert cancelled.stage is OperationStage.CANCELLED
    assert cancelled.checkpoint_ref == CHECKPOINT
    assert cancelled.estimated_remaining_seconds == 0


def test_cancel_after_progress_requires_checkpoint() -> None:
    running = _running().update_progress(
        expected_revision=2, phase_label_ja="処理中", current=1,
        elapsed_seconds=1, estimated_remaining_seconds=99,
    )
    cancelling = running.request_cancel(expected_revision=running.state_revision)
    with pytest.raises(ProductError) as exc:
        cancelling.finish_cancel(expected_revision=cancelling.state_revision)
    assert exc.value.code == "ERR_TASK054_WORKER_CANCEL_CHECKPOINT_REQUIRED"


def test_queued_cancel_is_immediate_and_idempotent_duplicate_is_not_a_transition() -> None:
    queued = WorkerLifecycleRecord.create(_request())
    cancelled = queued.request_cancel(expected_revision=queued.state_revision)
    assert cancelled.stage is OperationStage.CANCELLED
    with pytest.raises(ProductError) as exc:
        cancelled.request_cancel(expected_revision=cancelled.state_revision)
    assert exc.value.code == "ERR_TASK054_WORKER_TRANSITION"


def test_failure_with_checkpoint_requires_recovery_but_without_it_is_terminal() -> None:
    running = _running()
    failed = running.fail(
        expected_revision=running.state_revision, failure=_failure(), elapsed_seconds=2,
    )
    assert failed.stage is OperationStage.FAILED
    assert failed.to_view().recovery_plan_available is False

    running = _running().update_progress(
        expected_revision=2, phase_label_ja="処理中", current=10,
        elapsed_seconds=5, estimated_remaining_seconds=45,
    )
    checking = running.begin_checkpoint(expected_revision=running.state_revision)
    running = checking.checkpoint_saved(
        expected_revision=checking.state_revision, checkpoint_ref=CHECKPOINT,
    )
    recovery = running.fail(
        expected_revision=running.state_revision, failure=_failure(), elapsed_seconds=6,
    )
    assert recovery.stage is OperationStage.RECOVERY_REQUIRED
    assert recovery.to_view().recovery_plan_available is True


def test_resource_ceiling_stops_without_retry_and_preserves_checkpoint() -> None:
    running = _running().update_progress(
        expected_revision=2, phase_label_ja="処理中", current=10,
        elapsed_seconds=5, estimated_remaining_seconds=45,
    )
    unchanged = running.enforce_resource_ceiling(
        expected_revision=running.state_revision,
        elapsed_seconds=6, peak_memory_mib=1024, output_bytes=100,
    )
    assert unchanged is running
    checking = running.begin_checkpoint(expected_revision=running.state_revision)
    running = checking.checkpoint_saved(
        expected_revision=checking.state_revision, checkpoint_ref=CHECKPOINT,
    )
    stopped = running.enforce_resource_ceiling(
        expected_revision=running.state_revision,
        elapsed_seconds=3601, peak_memory_mib=8192, output_bytes=1024,
    )
    assert stopped.stage is OperationStage.RECOVERY_REQUIRED
    assert stopped.failure is not None
    assert stopped.failure.error_code == "ERR_TASK054_RESOURCE_LIMIT"
    assert stopped.failure.retry_external_or_paid is False


def test_registry_reuses_exact_click_and_rejects_conflict_and_stale_commit() -> None:
    registry = WorkerLifecycleRegistry()
    request = _request()
    queued, created = registry.reserve(request)
    duplicate, duplicate_created = registry.reserve(_request())
    assert created is True
    assert duplicate_created is False
    assert duplicate is queued
    with pytest.raises(ProductError) as conflict:
        registry.reserve(_request(expected_dataset_revision=4))
    assert conflict.value.code == "ERR_TASK054_WORKER_IDEMPOTENCY_CONFLICT"

    running = queued.start(expected_revision=queued.state_revision)
    registry.commit(running, expected_previous_revision=queued.state_revision)
    progressed = running.update_progress(
        expected_revision=running.state_revision,
        phase_label_ja="処理中", current=1,
        elapsed_seconds=1, estimated_remaining_seconds=9,
    )
    registry.commit(progressed, expected_previous_revision=running.state_revision)
    with pytest.raises(ProductError) as stale:
        registry.commit(progressed, expected_previous_revision=running.state_revision)
    assert stale.value.code == "ERR_TASK054_WORKER_STALE_REVISION"

def test_complete_is_exact_terminal_transition() -> None:
    running = _running()
    completed = running.complete(expected_revision=running.state_revision, elapsed_seconds=12)
    assert completed.current == completed.request.total_units
    assert completed.stage is OperationStage.COMPLETED
    with pytest.raises(ProductError):
        completed.complete(expected_revision=completed.state_revision, elapsed_seconds=13)


def test_windows_popen_options_are_no_console_and_never_shell() -> None:
    options = no_console_popen_options(platform_name="nt")
    assert options["creationflags"] == getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    assert options["stdin"] is subprocess.DEVNULL
    assert options["stdout"] is subprocess.DEVNULL
    assert options["stderr"] is subprocess.DEVNULL
    assert options["shell"] is False
    assert "OPENAI_API_KEY" not in options["env"]
    assert "creationflags" not in no_console_popen_options(platform_name="posix")



def test_worker_environment_and_arguments_do_not_transport_secrets() -> None:
    environment = sanitized_worker_environment({
        "PATH": "C:\\safe", "SYSTEMROOT": "C:\\Windows",
        "OPENAI_API_KEY": "forbidden", "PASSWORD": "forbidden",
    })
    assert environment == {"PATH": "C:\\safe", "SYSTEMROOT": "C:\\Windows"}
    with pytest.raises(ValueError, match="secret-like"):
        WorkerLaunchSpec("C:\\BVP\\worker.exe", ("--api-key=forbidden",))
    with pytest.raises(ValueError, match="invalid character"):
        WorkerLaunchSpec("C:\\BVP\\worker.exe", ("line\nbreak",))
    safe = WorkerLaunchSpec(
        "C:\\BVP\\worker.exe", ("--authorization-ref", AUTHORITY_REF),
    )
    assert safe.arguments[-1] == AUTHORITY_REF

class _FakeProcess:
    def __init__(self, *, timeout_once: bool = False) -> None:
        self.return_code: int | None = None
        self.terminated = False
        self.killed = False
        self.timeout_once = timeout_once

    def poll(self):
        return self.return_code

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, *, timeout: float):
        if self.timeout_once:
            self.timeout_once = False
            raise subprocess.TimeoutExpired("fixture", timeout)
        self.return_code = -9 if self.killed else 0
        return self.return_code

    def kill(self) -> None:
        self.killed = True


def test_process_controller_uses_argument_vector_and_bounded_kill_fallback() -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []
    process = _FakeProcess(timeout_once=True)

    def factory(command, **kwargs):
        calls.append((command, kwargs))
        return process

    controller = NoConsoleWorkerProcessController(popen_factory=factory)
    spec = WorkerLaunchSpec("C:\\Program Files\\BVP\\worker.exe", ("--fixture", "safe"))
    controller.start(spec)
    assert calls[0][0] == [spec.executable, "--fixture", "safe"]
    assert calls[0][1]["shell"] is False
    with pytest.raises(ProductError) as duplicate:
        controller.start(spec)
    assert duplicate.value.code == "ERR_TASK054_WORKER_ALREADY_RUNNING"
    controller.stop(timeout_seconds=0.1)
    assert process.terminated is True
    assert process.killed is True
