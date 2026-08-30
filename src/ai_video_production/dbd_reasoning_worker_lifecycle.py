"""TASK-054 R5F bounded no-console worker lifecycle.

The state machine is Product-local and side-effect free.  Process launch is a
separate injected boundary so tests never start a real model or training job.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import os
from pathlib import Path, PureWindowsPath
import re
import subprocess
import threading
from typing import Callable

from .dbd_reasoning_operation_view import (
    OperationFailureView,
    OperationStage,
    TrainingStudioOperationSnapshot,
)
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
_ACTION_RE = re.compile(r"[A-Z][A-Z0-9_]{2,63}")


_IDENTITY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}")
_SECRET_ARGUMENT_RE = re.compile(r"(?i)(?:api[_-]?key|bearer|password|private[_-]?key|secret|token)")
_WORKER_ENV_ALLOWLIST = frozenset({
    "COMSPEC", "PATH", "PATHEXT", "PYTHONIOENCODING", "PYTHONUTF8", "SYSTEMROOT", "TEMP", "TMP", "WINDIR",
})
_IDEMPOTENCY_RE = re.compile(r"task054-idempotency-[0-9a-f]{64}")
_AUTHORITY_REF_RE = re.compile(r"authorization://task054/[0-9A-HJKMNP-TV-Z]{26}")
_MAX_ARGUMENTS = 64
_MAX_ARGUMENT_BYTES = 16_384


def _lifecycle_error(code: str, message: str) -> ProductError:
    return ProductError(code, message, ProductErrorCategory.STATE)


@dataclass(frozen=True, slots=True)
class WorkerResourceCeiling:
    max_seconds: int
    max_memory_mib: int
    max_output_bytes: int

    def __post_init__(self) -> None:
        limits = {
            "max_seconds": (1, 7 * 24 * 60 * 60),
            "max_memory_mib": (128, 1024 * 1024),
            "max_output_bytes": (1, 1024 * 1024 * 1024),
        }
        for name, (minimum, maximum) in limits.items():
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
                raise ValueError(f"{name} is outside the R5F ceiling")

    def to_dict(self) -> dict[str, int]:
        return {
            "max_seconds": self.max_seconds,
            "max_memory_mib": self.max_memory_mib,
            "max_output_bytes": self.max_output_bytes,
        }


@dataclass(frozen=True, slots=True)
class WorkerRequest:
    workspace_id: str
    idempotency_key: str
    action_kind: str
    expected_dataset_revision: int
    expected_binding_revision: int
    plan_sha256: str
    authorization_ref: str
    resource_ceiling: WorkerResourceCeiling
    retry_external_or_paid: bool
    total_units: int
    cancel_policy: str = "AT_VERIFIED_CHECKPOINT"
    authority_effect: str = "REQUEST_ONLY_NO_EXECUTION_AUTHORITY"

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, str) or not _IDENTITY_RE.fullmatch(self.workspace_id):
            raise ValueError("workspace_id is invalid")
        if not isinstance(self.action_kind, str) or not _ACTION_RE.fullmatch(self.action_kind):
            raise ValueError("action_kind is invalid")
        if not isinstance(self.idempotency_key, str) or not _IDEMPOTENCY_RE.fullmatch(self.idempotency_key):
            raise ValueError("idempotency_key is invalid")
        for name in ("expected_dataset_revision", "expected_binding_revision", "total_units"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be positive")
        validate_sha256(self.plan_sha256, field_name="plan_sha256")
        if not isinstance(self.authorization_ref, str) or not _AUTHORITY_REF_RE.fullmatch(self.authorization_ref):
            raise ValueError("authorization_ref is invalid")
        if not isinstance(self.resource_ceiling, WorkerResourceCeiling):
            raise ValueError("resource_ceiling is invalid")
        if self.cancel_policy != "AT_VERIFIED_CHECKPOINT":
            raise ValueError("cancel_policy is fixed")
        if self.authority_effect != "REQUEST_ONLY_NO_EXECUTION_AUTHORITY":
            raise ValueError("R5F request cannot grant execution authority")
        if not isinstance(self.retry_external_or_paid, bool):
            raise ValueError("retry_external_or_paid must be boolean")

    def _body(self) -> dict[str, object]:
        return {
            "workspace_id": self.workspace_id,
            "idempotency_key": self.idempotency_key,
            "expected_dataset_revision": self.expected_dataset_revision,
            "expected_binding_revision": self.expected_binding_revision,
            "plan_sha256": self.plan_sha256,
            "authorization_ref": self.authorization_ref,
            "action_kind": self.action_kind,
            "resource_ceiling": self.resource_ceiling.to_dict(),
            "retry_external_or_paid": self.retry_external_or_paid,
            "total_units": self.total_units,
            "cancel_policy": self.cancel_policy,
            "authority_effect": self.authority_effect,
        }

    @property
    def request_sha256(self) -> str:
        return sha256_bytes(canonical_json_bytes(self._body()))

    @property
    def operation_id(self) -> str:
        return "task054-operation-" + self.request_sha256.split(":", 1)[1]


@dataclass(frozen=True, slots=True)
class WorkerLifecycleRecord:
    request: WorkerRequest
    stage: OperationStage
    state_revision: int
    phase_label_ja: str
    current: int
    elapsed_seconds: int
    estimated_remaining_seconds: int | None
    checkpoint_ref: str | None = None
    failure: OperationFailureView | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request, WorkerRequest):
            raise ValueError("request is invalid")
        TrainingStudioOperationSnapshot(
            operation_id=self.request.operation_id,
            state_revision=self.state_revision,
            stage=self.stage,
            phase_label_ja=self.phase_label_ja,
            current=self.current,
            total=self.request.total_units,
            elapsed_seconds=self.elapsed_seconds,
            estimated_remaining_seconds=self.estimated_remaining_seconds,
            checkpoint_ref=self.checkpoint_ref,
            failure=self.failure,
        )

    @classmethod
    def create(cls, request: WorkerRequest) -> "WorkerLifecycleRecord":
        return cls(request, OperationStage.QUEUED, 1, "開始待ち", 0, 0, None)

    def _require_revision(self, expected_revision: int) -> None:
        if expected_revision != self.state_revision:
            raise _lifecycle_error(
                "ERR_TASK054_WORKER_STALE_REVISION",
                "Worker state changed; reload before applying the action",
            )

    def _require_stage(self, *allowed: OperationStage) -> None:
        if self.stage not in allowed:
            raise _lifecycle_error(
                "ERR_TASK054_WORKER_TRANSITION",
                "Worker lifecycle transition is invalid",
            )

    def start(self, *, expected_revision: int) -> "WorkerLifecycleRecord":
        self._require_revision(expected_revision)
        self._require_stage(OperationStage.QUEUED)
        return replace(
            self, stage=OperationStage.RUNNING, state_revision=self.state_revision + 1,
            phase_label_ja="処理を開始しました", estimated_remaining_seconds=None,
        )

    def update_progress(
        self, *, expected_revision: int, phase_label_ja: str, current: int,
        elapsed_seconds: int, estimated_remaining_seconds: int | None,
    ) -> "WorkerLifecycleRecord":
        self._require_revision(expected_revision)
        self._require_stage(OperationStage.RUNNING)
        if current < self.current:
            raise _lifecycle_error(
                "ERR_TASK054_WORKER_PROGRESS_REGRESSION",
                "Worker progress cannot move backwards",
            )
        if elapsed_seconds < self.elapsed_seconds:
            raise _lifecycle_error(
                "ERR_TASK054_WORKER_ELAPSED_REGRESSION",
                "Worker elapsed time cannot move backwards",
            )
        if current >= self.request.total_units:
            raise _lifecycle_error(
                "ERR_TASK054_WORKER_PROGRESS_TERMINAL",
                "Use the complete transition for terminal progress",
            )
        return replace(
            self, state_revision=self.state_revision + 1, phase_label_ja=phase_label_ja,
            current=current, elapsed_seconds=elapsed_seconds,
            estimated_remaining_seconds=estimated_remaining_seconds,
        )

    def begin_checkpoint(self, *, expected_revision: int) -> "WorkerLifecycleRecord":
        self._require_revision(expected_revision)
        self._require_stage(OperationStage.RUNNING)
        return replace(
            self, stage=OperationStage.CHECKPOINTING,
            state_revision=self.state_revision + 1,
            phase_label_ja="Checkpointを安全に保存中",
        )

    def checkpoint_saved(
        self, *, expected_revision: int, checkpoint_ref: str,
    ) -> "WorkerLifecycleRecord":
        self._require_revision(expected_revision)
        self._require_stage(OperationStage.CHECKPOINTING)
        return replace(
            self, stage=OperationStage.RUNNING,
            state_revision=self.state_revision + 1,
            phase_label_ja="Checkpointを保存しました",
            checkpoint_ref=checkpoint_ref,
        )

    def request_cancel(self, *, expected_revision: int) -> "WorkerLifecycleRecord":
        self._require_revision(expected_revision)
        self._require_stage(OperationStage.QUEUED, OperationStage.RUNNING, OperationStage.CHECKPOINTING)
        if self.stage is OperationStage.QUEUED:
            return replace(
                self, stage=OperationStage.CANCELLED,
                state_revision=self.state_revision + 1,
                phase_label_ja="開始前にキャンセルしました",
                estimated_remaining_seconds=0,
            )
        return replace(
            self, stage=OperationStage.CANCELLING,
            state_revision=self.state_revision + 1,
            phase_label_ja="安全な境界でキャンセル中",
        )

    def finish_cancel(
        self, *, expected_revision: int, checkpoint_ref: str | None = None,
    ) -> "WorkerLifecycleRecord":
        self._require_revision(expected_revision)
        self._require_stage(OperationStage.CANCELLING)
        verified = checkpoint_ref or self.checkpoint_ref
        if self.current > 0 and verified is None:
            raise _lifecycle_error(
                "ERR_TASK054_WORKER_CANCEL_CHECKPOINT_REQUIRED",
                "Cancellation after progress requires a verified checkpoint",
            )
        return replace(
            self, stage=OperationStage.CANCELLED,
            state_revision=self.state_revision + 1,
            phase_label_ja="安全にキャンセルしました",
            estimated_remaining_seconds=0,
            checkpoint_ref=verified,
        )

    def complete(self, *, expected_revision: int, elapsed_seconds: int) -> "WorkerLifecycleRecord":
        self._require_revision(expected_revision)
        self._require_stage(OperationStage.RUNNING)
        if elapsed_seconds < self.elapsed_seconds:
            raise _lifecycle_error(
                "ERR_TASK054_WORKER_ELAPSED_REGRESSION",
                "Worker elapsed time cannot move backwards",
            )
        return replace(
            self, stage=OperationStage.COMPLETED,
            state_revision=self.state_revision + 1,
            phase_label_ja="処理が完了しました", current=self.request.total_units,
            elapsed_seconds=elapsed_seconds, estimated_remaining_seconds=0,
        )

    def enforce_resource_ceiling(
        self, *, expected_revision: int, elapsed_seconds: int,
        peak_memory_mib: int, output_bytes: int,
    ) -> "WorkerLifecycleRecord":
        self._require_revision(expected_revision)
        self._require_stage(
            OperationStage.RUNNING, OperationStage.CHECKPOINTING,
            OperationStage.CANCELLING,
        )
        for name, value in (
            ("elapsed_seconds", elapsed_seconds),
            ("peak_memory_mib", peak_memory_mib),
            ("output_bytes", output_bytes),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be non-negative")
        if elapsed_seconds < self.elapsed_seconds:
            raise _lifecycle_error(
                "ERR_TASK054_WORKER_ELAPSED_REGRESSION",
                "Worker elapsed time cannot move backwards",
            )
        ceiling = self.request.resource_ceiling
        breaches = []
        if elapsed_seconds > ceiling.max_seconds:
            breaches.append("TIME")
        if peak_memory_mib > ceiling.max_memory_mib:
            breaches.append("MEMORY")
        if output_bytes > ceiling.max_output_bytes:
            breaches.append("OUTPUT")
        if not breaches:
            return self
        failure = OperationFailureView(
            error_code="ERR_TASK054_RESOURCE_LIMIT",
            what_happened_ja="設定された資源上限に到達したため安全に停止しました。",
            data_safety_ja="入力Datasetと既存Bindingは変更されていません。",
            saved_evidence_ja=(
                "最後の検証済みCheckpointを保持しています。"
                if self.checkpoint_ref else "検証済みCheckpointはまだありません。"
            ),
            next_safe_action_ja="上限と処理計画を確認し、小さい計画を作成できます。",
            retry_effect_ja="変更した計画は確認後にだけ再実行できます。",
            technical_details="resource ceiling exceeded: " + ",".join(breaches),
            retry_external_or_paid=self.request.retry_external_or_paid,
        )
        return self.fail(
            expected_revision=expected_revision, failure=failure,
            elapsed_seconds=elapsed_seconds,
        )

    def fail(
        self, *, expected_revision: int, failure: OperationFailureView,
        elapsed_seconds: int,
    ) -> "WorkerLifecycleRecord":
        self._require_revision(expected_revision)
        self._require_stage(
            OperationStage.RUNNING, OperationStage.CHECKPOINTING,
            OperationStage.CANCELLING,
        )
        if elapsed_seconds < self.elapsed_seconds:
            raise _lifecycle_error(
                "ERR_TASK054_WORKER_ELAPSED_REGRESSION",
                "Worker elapsed time cannot move backwards",
            )
        stage = OperationStage.RECOVERY_REQUIRED if self.checkpoint_ref else OperationStage.FAILED
        return replace(
            self, stage=stage, state_revision=self.state_revision + 1,
            phase_label_ja="安全に停止しました", elapsed_seconds=elapsed_seconds,
            estimated_remaining_seconds=0 if stage is OperationStage.FAILED else None,
            failure=failure,
        )

    def to_view(self) -> TrainingStudioOperationSnapshot:
        return TrainingStudioOperationSnapshot(
            operation_id=self.request.operation_id,
            state_revision=self.state_revision, stage=self.stage,
            phase_label_ja=self.phase_label_ja, current=self.current,
            total=self.request.total_units, elapsed_seconds=self.elapsed_seconds,
            estimated_remaining_seconds=self.estimated_remaining_seconds,
            checkpoint_ref=self.checkpoint_ref, failure=self.failure,
        )


class WorkerLifecycleRegistry:
    """In-process exact-idempotency owner; durable replay is verified in R7."""

    def __init__(self) -> None:
        self._records: dict[str, WorkerLifecycleRecord] = {}
        self._lock = threading.RLock()

    def reserve(self, request: WorkerRequest) -> tuple[WorkerLifecycleRecord, bool]:
        if not isinstance(request, WorkerRequest):
            raise ValueError("request must be WorkerRequest")
        with self._lock:
            current = self._records.get(request.idempotency_key)
            if current is not None:
                if current.request.request_sha256 != request.request_sha256:
                    raise ProductError(
                        "ERR_TASK054_WORKER_IDEMPOTENCY_CONFLICT",
                        "Idempotency key is already bound to different exact inputs",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
                return current, False
            record = WorkerLifecycleRecord.create(request)
            self._records[request.idempotency_key] = record
            return record, True

    def commit(
        self, record: WorkerLifecycleRecord, *, expected_previous_revision: int,
    ) -> WorkerLifecycleRecord:
        if not isinstance(record, WorkerLifecycleRecord):
            raise ValueError("record must be WorkerLifecycleRecord")
        with self._lock:
            current = self._records.get(record.request.idempotency_key)
            if current is None or current.request.request_sha256 != record.request.request_sha256:
                raise ProductError(
                    "ERR_TASK054_WORKER_REGISTRY_IDENTITY",
                    "Worker registry identity does not match the reserved operation",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            if current.state_revision != expected_previous_revision:
                raise _lifecycle_error(
                    "ERR_TASK054_WORKER_STALE_REVISION",
                    "Worker registry changed before commit",
                )
            if record.state_revision != expected_previous_revision + 1:
                raise _lifecycle_error(
                    "ERR_TASK054_WORKER_REVISION_SEQUENCE",
                    "Worker registry commit must advance exactly one revision",
                )
            self._records[record.request.idempotency_key] = record
            return record


@dataclass(frozen=True, slots=True)
class WorkerLaunchSpec:
    executable: str
    arguments: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.executable, str) or not self.executable:
            raise ValueError("worker executable is invalid")
        if "\x00" in self.executable or "\n" in self.executable or "\r" in self.executable:
            raise ValueError("worker executable contains an invalid character")
        if not (Path(self.executable).is_absolute() or PureWindowsPath(self.executable).drive):
            raise ValueError("worker executable must be absolute")
        if not isinstance(self.arguments, tuple) or len(self.arguments) > _MAX_ARGUMENTS:
            raise ValueError("worker arguments are invalid or outside bounds")
        if sum(len(item.encode("utf-8")) for item in self.arguments) > _MAX_ARGUMENT_BYTES:
            raise ValueError("worker arguments exceed the byte ceiling")
        if any(not isinstance(item, str) or "\x00" in item or "\n" in item or "\r" in item for item in self.arguments):
            raise ValueError("worker argument contains an invalid character")


        if any(_SECRET_ARGUMENT_RE.search(item) for item in self.arguments):
            raise ValueError("secret-like material is not allowed in worker arguments")
def sanitized_worker_environment(source: dict[str, str] | None = None) -> dict[str, str]:
    values = os.environ if source is None else source
    if not isinstance(values, dict) and source is not None:
        raise ValueError("worker environment source must be a dictionary")
    return {key: str(value) for key, value in values.items() if key.upper() in _WORKER_ENV_ALLOWLIST}




def no_console_popen_options(*, platform_name: str | None = None) -> dict[str, object]:
    platform = platform_name or os.name
    options: dict[str, object] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "shell": False,
        "env": sanitized_worker_environment(),
    }
    if platform == "nt":
        options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return options


class NoConsoleWorkerProcessController:
    def __init__(self, *, popen_factory: Callable[..., subprocess.Popen] = subprocess.Popen) -> None:
        self._popen_factory = popen_factory
        self._process: subprocess.Popen | None = None
        self._lock = threading.RLock()

    def start(self, spec: WorkerLaunchSpec) -> None:
        if not isinstance(spec, WorkerLaunchSpec):
            raise ValueError("spec must be WorkerLaunchSpec")
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                raise _lifecycle_error(
                    "ERR_TASK054_WORKER_ALREADY_RUNNING",
                    "A bounded worker process is already running",
                )
            try:
                self._process = self._popen_factory(
                    [spec.executable, *spec.arguments], **no_console_popen_options(),
                )
            except Exception as exc:
                raise ProductError(
                    "ERR_TASK054_WORKER_START_FAILED",
                    "The bounded worker process could not start",
                    ProductErrorCategory.EXTERNAL_DEPENDENCY,
                ) from exc

    def poll(self) -> int | None:
        with self._lock:
            return None if self._process is None else self._process.poll()

    def stop(self, *, timeout_seconds: float = 1.0) -> None:
        if timeout_seconds <= 0 or timeout_seconds > 30:
            raise ValueError("timeout_seconds is outside bounds")
        with self._lock:
            process = self._process
            self._process = None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=timeout_seconds)

    def close(self) -> None:
        self.stop()


__all__ = [
    "NoConsoleWorkerProcessController", "WorkerLaunchSpec", "WorkerLifecycleRecord",
    "WorkerLifecycleRegistry", "WorkerRequest", "WorkerResourceCeiling",
    "no_console_popen_options", "sanitized_worker_environment",
]
