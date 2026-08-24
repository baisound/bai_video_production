from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ai_video_production.dbd_reasoning_operation_view import (
    OperationFailureView,
    OperationStage,
    TrainingStudioOperationSnapshot,
    format_duration_ja,
)


OPERATION_ID = "task054-operation-" + "a" * 64
CHECKPOINT_REF = "task054-checkpoint://sha256/" + "b" * 64


def _failure() -> OperationFailureView:
    return OperationFailureView(
        error_code="ERR_TASK054_RUNTIME_UNAVAILABLE",
        what_happened_ja="実行環境を確認できなかったため停止しました。",
        data_safety_ja="入力と既存Datasetは変更されていません。",
        saved_evidence_ja="事前確認の結果を保持しています。",
        next_safe_action_ja="環境を確認してから再開計画を作成できます。",
        retry_effect_ja="この操作から自動再試行は行いません。",
        technical_details="runtime probe returned NOT_AVAILABLE",
        retry_external_or_paid=False,
    )


def _snapshot(**changes: object) -> TrainingStudioOperationSnapshot:
    values: dict[str, object] = {
        "operation_id": OPERATION_ID,
        "state_revision": 3,
        "stage": OperationStage.RUNNING,
        "phase_label_ja": "Datasetを検証中",
        "current": 25,
        "total": 100,
        "elapsed_seconds": 65,
        "estimated_remaining_seconds": 195,
    }
    values.update(changes)
    return TrainingStudioOperationSnapshot(**values)


def test_running_snapshot_projects_bounded_progress_and_safe_cancel() -> None:
    snapshot = _snapshot()
    assert snapshot.progress_milli == 250
    assert snapshot.cancel_available is True
    assert snapshot.recovery_plan_available is False
    assert snapshot.status_label_ja == "処理中"
    assert format_duration_ja(snapshot.elapsed_seconds) == "1分5秒"


def test_cancelling_is_visible_but_cannot_repeat_cancel() -> None:
    snapshot = _snapshot(stage=OperationStage.CANCELLING)
    assert snapshot.cancel_available is False
    assert snapshot.status_label_ja == "安全な境界でキャンセル中"


def test_recovery_requires_failure_and_verified_checkpoint() -> None:
    with pytest.raises(ValueError, match="verified checkpoint"):
        _snapshot(stage=OperationStage.RECOVERY_REQUIRED, failure=_failure())
    snapshot = _snapshot(
        stage=OperationStage.RECOVERY_REQUIRED,
        failure=_failure(),
        checkpoint_ref=CHECKPOINT_REF,
    )
    assert snapshot.recovery_plan_available is True
    assert snapshot.cancel_available is False


def test_failure_details_exist_only_on_failure_or_recovery() -> None:
    with pytest.raises(ValueError, match="exactly"):
        _snapshot(stage=OperationStage.FAILED, estimated_remaining_seconds=0)
    with pytest.raises(ValueError, match="exactly"):
        _snapshot(failure=_failure())
    with pytest.raises(ValueError, match="details are invalid"):
        _snapshot(stage=OperationStage.FAILED, failure="forged", estimated_remaining_seconds=0)


def test_terminal_and_queued_progress_fail_closed() -> None:
    with pytest.raises(ValueError, match="QUEUED progress"):
        _snapshot(stage=OperationStage.QUEUED)
    with pytest.raises(ValueError, match="COMPLETED progress"):
        _snapshot(stage=OperationStage.COMPLETED, estimated_remaining_seconds=0)
    completed = _snapshot(
        stage=OperationStage.COMPLETED,
        current=100,
        estimated_remaining_seconds=0,
    )
    assert completed.progress_milli == 1000
    assert completed.cancel_available is False
    with pytest.raises(ValueError, match="remaining estimate"):
        replace(completed, estimated_remaining_seconds=1)


def test_snapshot_cannot_grant_execution_authority() -> None:
    with pytest.raises(ValueError, match="cannot grant"):
        replace(_snapshot(), authority_effect="EXECUTION_ALLOWED")


def test_failure_technical_details_reject_sensitive_material() -> None:
    with pytest.raises(ValueError, match="safe display boundary"):
        replace(_failure(), technical_details="Authorization: Bearer abc")


def test_invalid_progress_and_estimate_fail_closed() -> None:
    with pytest.raises(ValueError, match="progress counters"):
        _snapshot(current=101)
    with pytest.raises(ValueError, match="estimated_remaining_seconds"):
        _snapshot(estimated_remaining_seconds=-1)
    with pytest.raises(ValueError, match="seconds is invalid"):
        format_duration_ja(True)


def test_panel_copy_answers_failure_questions_and_binds_stale_safe_actions() -> None:
    source = Path("src/ai_video_production/dbd_reasoning_operation_view_ui.py").read_text(encoding="utf-8")
    for label in (
        "何が起きたか", "データは安全か", "保存されたもの", "次の安全な操作", "再試行",
        "安全にキャンセル", "検証済みCheckpointから再開計画を作る", "技術詳細",
    ):
        assert label in source
    assert "snapshot.operation_id, snapshot.state_revision" in source
    assert "自動再試行" not in source
