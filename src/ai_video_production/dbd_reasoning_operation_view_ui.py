"""TASK-054 R5E accessible Japanese progress/cancel/error/recovery panel."""

from __future__ import annotations

from collections.abc import Callable

from .dbd_reasoning_operation_view import TrainingStudioOperationSnapshot, format_duration_ja


class TrainingStudioOperationPanel:
    def __init__(
        self,
        parent,
        *,
        on_cancel_request: Callable[[str, int], None],
        on_resume_plan_request: Callable[[str, int, str], None],
    ) -> None:
        import tkinter as tk
        from tkinter import messagebox, ttk

        if not callable(on_cancel_request) or not callable(on_resume_plan_request):
            raise ValueError("operation callbacks must be callable")
        self._on_cancel = on_cancel_request
        self._on_resume_plan = on_resume_plan_request
        self._snapshot: TrainingStudioOperationSnapshot | None = None
        self._messagebox = messagebox
        self.frame = ttk.LabelFrame(parent, text="処理状況", padding=10)
        self.frame.columnconfigure(0, weight=1)
        self.status_var = tk.StringVar(value="処理はありません。")
        self.phase_var = tk.StringVar(value="")
        self.time_var = tk.StringVar(value="経過: 0秒 / 残り: 未確認")
        ttk.Label(self.frame, textvariable=self.status_var, font=("TkDefaultFont", 11, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(self.frame, textvariable=self.phase_var).grid(row=1, column=0, sticky="w", pady=(2, 4))
        self.progress = ttk.Progressbar(self.frame, maximum=1000, mode="determinate")
        self.progress.grid(row=2, column=0, columnspan=3, sticky="ew")
        ttk.Label(self.frame, textvariable=self.time_var).grid(row=3, column=0, sticky="w", pady=(4, 8))
        self.cancel_button = ttk.Button(self.frame, text="安全にキャンセル", command=self._cancel)
        self.cancel_button.grid(row=4, column=1, padx=(8, 0))
        self.resume_button = ttk.Button(self.frame, text="検証済みCheckpointから再開計画を作る", command=self._resume)
        self.resume_button.grid(row=4, column=2, padx=(8, 0))
        self.details_button = ttk.Button(self.frame, text="技術詳細", command=self._details)
        self.details_button.grid(row=4, column=0, sticky="w")
        self.cancel_button.state(["disabled"])
        self.resume_button.state(["disabled"])
        self.details_button.state(["disabled"])

    def grid(self, **kwargs) -> None:
        self.frame.grid(**kwargs)

    def show(self, snapshot: TrainingStudioOperationSnapshot) -> None:
        if not isinstance(snapshot, TrainingStudioOperationSnapshot):
            raise ValueError("snapshot must be TrainingStudioOperationSnapshot")
        self._snapshot = snapshot
        self.status_var.set(f"{snapshot.status_label_ja}  {snapshot.current}/{snapshot.total}")
        self.phase_var.set(snapshot.phase_label_ja)
        self.progress.configure(value=snapshot.progress_milli)
        self.time_var.set(
            f"経過: {format_duration_ja(snapshot.elapsed_seconds)} / "
            f"残り目安: {format_duration_ja(snapshot.estimated_remaining_seconds)}"
        )
        self.cancel_button.state(["!disabled"] if snapshot.cancel_available else ["disabled"])
        self.resume_button.state(["!disabled"] if snapshot.recovery_plan_available else ["disabled"])
        self.details_button.state(["!disabled"] if snapshot.failure is not None else ["disabled"])

    def _cancel(self) -> None:
        snapshot = self._snapshot
        if snapshot is None or not snapshot.cancel_available:
            return
        if not self._messagebox.askyesno(
            "安全にキャンセル",
            "現在の処理を安全な境界で停止します。検証済みCheckpointは保持されます。続けますか？",
        ):
            return
        self._on_cancel(snapshot.operation_id, snapshot.state_revision)

    def _resume(self) -> None:
        snapshot = self._snapshot
        if snapshot is None or not snapshot.recovery_plan_available or snapshot.checkpoint_ref is None:
            return
        self._on_resume_plan(snapshot.operation_id, snapshot.state_revision, snapshot.checkpoint_ref)

    def _details(self) -> None:
        snapshot = self._snapshot
        if snapshot is None or snapshot.failure is None:
            return
        failure = snapshot.failure
        retry = "再試行で費用または外部送信が発生する可能性があります。" if failure.retry_external_or_paid else "再試行による費用・外部送信はありません。"
        self._messagebox.showerror(
            f"処理エラー {failure.error_code}",
            f"何が起きたか: {failure.what_happened_ja}\n\n"
            f"データは安全か: {failure.data_safety_ja}\n\n"
            f"保存されたもの: {failure.saved_evidence_ja}\n\n"
            f"次の安全な操作: {failure.next_safe_action_ja}\n\n"
            f"再試行: {failure.retry_effect_ja}\n{retry}\n\n"
            f"技術詳細:\n{failure.technical_details}",
        )


__all__ = ["TrainingStudioOperationPanel"]
