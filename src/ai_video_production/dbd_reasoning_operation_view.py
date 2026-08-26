"""TASK-054 R5E immutable progress, cancellation and recovery presentation contract."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


_OPERATION_RE = re.compile(r"task054-operation-[0-9a-f]{64}")
_CHECKPOINT_RE = re.compile(r"task054-checkpoint://sha256/[0-9a-f]{64}")
_ERROR_RE = re.compile(r"ERR_TASK054_[A-Z0-9_]{2,80}")
_SENSITIVE = re.compile(
    r"(?i)(?:api[_-]?key|authorization\s*:|bearer\s+|credential|password\s*=|private[_-]?key|secret\s*=|token\s*=)"
)


class OperationStage(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    CHECKPOINTING = "CHECKPOINTING"
    CANCELLING = "CANCELLING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


def _bounded_text(value: str, field_name: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{field_name} is invalid")
    if "\x00" in value or _SENSITIVE.search(value):
        raise ValueError(f"{field_name} violates the safe display boundary")
    return value


@dataclass(frozen=True, slots=True)
class OperationFailureView:
    error_code: str
    what_happened_ja: str
    data_safety_ja: str
    saved_evidence_ja: str
    next_safe_action_ja: str
    retry_effect_ja: str
    technical_details: str
    retry_external_or_paid: bool

    def __post_init__(self) -> None:
        if not isinstance(self.error_code, str) or not _ERROR_RE.fullmatch(self.error_code):
            raise ValueError("error_code is invalid")
        for name in (
            "what_happened_ja", "data_safety_ja", "saved_evidence_ja",
            "next_safe_action_ja", "retry_effect_ja",
        ):
            _bounded_text(getattr(self, name), name, maximum=500)
        _bounded_text(self.technical_details, "technical_details", maximum=8_000)
        if not isinstance(self.retry_external_or_paid, bool):
            raise ValueError("retry_external_or_paid must be boolean")


@dataclass(frozen=True, slots=True)
class TrainingStudioOperationSnapshot:
    operation_id: str
    state_revision: int
    stage: OperationStage
    phase_label_ja: str
    current: int
    total: int
    elapsed_seconds: int
    estimated_remaining_seconds: int | None
    checkpoint_ref: str | None = None
    failure: OperationFailureView | None = None
    authority_effect: str = "PRESENTATION_ONLY_NO_EXECUTION_AUTHORITY"

    def __post_init__(self) -> None:
        if not isinstance(self.operation_id, str) or not _OPERATION_RE.fullmatch(self.operation_id):
            raise ValueError("operation_id is invalid")
        if isinstance(self.state_revision, bool) or not isinstance(self.state_revision, int) or self.state_revision < 1:
            raise ValueError("state_revision must be positive")
        if not isinstance(self.stage, OperationStage):
            raise ValueError("stage is invalid")
        _bounded_text(self.phase_label_ja, "phase_label_ja", maximum=80)
        for name in ("current", "total", "elapsed_seconds"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.total < 1 or self.current > self.total:
            raise ValueError("progress counters are invalid")
        if self.estimated_remaining_seconds is not None and (
            isinstance(self.estimated_remaining_seconds, bool)
            or not isinstance(self.estimated_remaining_seconds, int)
            or self.estimated_remaining_seconds < 0
        ):
            raise ValueError("estimated_remaining_seconds is invalid")
        if self.stage in {OperationStage.COMPLETED, OperationStage.FAILED, OperationStage.CANCELLED} and self.estimated_remaining_seconds not in {None, 0}:
            raise ValueError("terminal stage cannot retain a remaining estimate")
        if self.checkpoint_ref is not None and (
            not isinstance(self.checkpoint_ref, str) or not _CHECKPOINT_RE.fullmatch(self.checkpoint_ref)
        ):
            raise ValueError("checkpoint_ref is invalid")
        if self.stage is OperationStage.QUEUED and self.current != 0:
            raise ValueError("QUEUED progress must be zero")
        if self.stage is OperationStage.COMPLETED and self.current != self.total:
            raise ValueError("COMPLETED progress must equal total")
        failure_stages = {OperationStage.FAILED, OperationStage.RECOVERY_REQUIRED}
        if self.failure is not None and not isinstance(self.failure, OperationFailureView):
            raise ValueError("failure details are invalid")
        if (self.stage in failure_stages) != (self.failure is not None):
            raise ValueError("failure details must exist exactly for failure/recovery stages")
        if self.stage is OperationStage.RECOVERY_REQUIRED and self.checkpoint_ref is None:
            raise ValueError("recovery requires a verified checkpoint reference")
        if self.authority_effect != "PRESENTATION_ONLY_NO_EXECUTION_AUTHORITY":
            raise ValueError("R5E cannot grant execution authority")

    @property
    def progress_milli(self) -> int:
        return self.current * 1000 // self.total

    @property
    def cancel_available(self) -> bool:
        return self.stage in {
            OperationStage.QUEUED,
            OperationStage.RUNNING,
            OperationStage.CHECKPOINTING,
        }

    @property
    def recovery_plan_available(self) -> bool:
        return self.stage is OperationStage.RECOVERY_REQUIRED and self.checkpoint_ref is not None

    @property
    def status_label_ja(self) -> str:
        return {
            OperationStage.QUEUED: "待機中",
            OperationStage.RUNNING: "処理中",
            OperationStage.CHECKPOINTING: "Checkpointを安全に保存中",
            OperationStage.CANCELLING: "安全な境界でキャンセル中",
            OperationStage.COMPLETED: "完了",
            OperationStage.FAILED: "停止しました",
            OperationStage.CANCELLED: "キャンセル済み",
            OperationStage.RECOVERY_REQUIRED: "再開計画が必要",
        }[self.stage]


def format_duration_ja(seconds: int | None) -> str:
    if seconds is None:
        return "未確認"
    if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds < 0:
        raise ValueError("seconds is invalid")
    minutes, remainder = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}時間{minutes}分"
    if minutes:
        return f"{minutes}分{remainder}秒"
    return f"{remainder}秒"


__all__ = [
    "OperationFailureView", "OperationStage", "TrainingStudioOperationSnapshot",
    "format_duration_ja",
]
