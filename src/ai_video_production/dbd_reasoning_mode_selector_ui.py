"""TASK-054 R5A always-visible Japanese reasoning-mode selector."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .dbd_reasoning_contracts import ReasoningSessionMode
from .dbd_reasoning_mode_selection import (
    ReasoningModeSelectionReceipt,
    ReasoningModeSelectionService,
    ReasoningModeSelectionStore,
)


MODE_LABEL_JA = {
    ReasoningSessionMode.PREVIEW_NO_LEARNING: "確認モード（学習しない）",
    ReasoningSessionMode.LEARNING: "学習モード",
}

MODE_EXPLANATION_JA = {
    ReasoningSessionMode.PREVIEW_NO_LEARNING: (
        "この操作ではモデルも学習素材も変更されません。確認結果から自動学習もしません。"
    ),
    ReasoningSessionMode.LEARNING: (
        "学習候補を準備するモードです。選択だけでは学習・外部送信・モデル変更を実行しません。"
    ),
}


def build_reasoning_mode_selector_panel(
    parent,
    *,
    workspace_id: str,
    workspace_root: str | Path,
    is_operation_active: Callable[[], bool],
):
    """Build the global selector without granting any downstream authority."""

    import tkinter as tk
    from tkinter import messagebox, ttk

    service = ReasoningModeSelectionService(
        workspace_id=workspace_id,
        store=ReasoningModeSelectionStore(workspace_root),
    )
    panel = ttk.LabelFrame(parent, text="解説AIの動作モード", padding=(12, 8))
    panel.columnconfigure(2, weight=1)
    selected_var = tk.StringVar(value=ReasoningSessionMode.PREVIEW_NO_LEARNING.value)
    explanation_var = tk.StringVar(value=MODE_EXPLANATION_JA[ReasoningSessionMode.PREVIEW_NO_LEARNING])
    receipt_var = tk.StringVar(value="選択証跡: 未記録（既定は確認モード）")
    state: dict[str, ReasoningModeSelectionReceipt | None] = {"receipt": None}
    active_mode = {"value": ReasoningSessionMode.PREVIEW_NO_LEARNING}

    try:
        latest = service.store.latest(workspace_id=workspace_id)
        mode = latest.selected_mode if latest is not None else ReasoningSessionMode.PREVIEW_NO_LEARNING
        state["receipt"] = latest
        selected_var.set(mode.value)
        explanation_var.set(MODE_EXPLANATION_JA[mode])
        active_mode["value"] = mode
        if latest is not None:
            receipt_var.set(f"選択証跡: {latest.selected_at} / {latest.receipt_id[-8:]}")
        load_error: Exception | None = None
    except Exception as exc:
        load_error = exc
        receipt_var.set("選択証跡を確認できません。安全のためモード変更を停止しました。")

    buttons: list[object] = []

    def apply_selection(mode: ReasoningSessionMode) -> None:
        previous_value = active_mode["value"].value
        try:
            receipt = service.select(mode, operation_active=bool(is_operation_active()))
        except RuntimeError:
            selected_var.set(previous_value)
            messagebox.showwarning(
                "動作モードを変更できません",
                "解析または学習処理の実行中はモードを変更できません。完了後にもう一度選択してください。",
            )
            return
        except Exception as exc:
            selected_var.set(previous_value)
            messagebox.showerror(
                "動作モードを保存できません",
                "選択証跡を安全に保存できなかったため、モードを変更しませんでした。\n\n"
                f"技術詳細: {type(exc).__name__}: {exc}",
            )
            return
        state["receipt"] = receipt
        active_mode["value"] = mode
        explanation_var.set(MODE_EXPLANATION_JA[mode])
        receipt_var.set(f"選択証跡: {receipt.selected_at} / {receipt.receipt_id[-8:]}")

    for column, mode in enumerate(ReasoningSessionMode):
        button = ttk.Radiobutton(
            panel,
            text=MODE_LABEL_JA[mode],
            value=mode.value,
            variable=selected_var,
            command=lambda selected=mode: apply_selection(selected),
        )
        button.grid(row=0, column=column, sticky="w", padx=(0, 18))
        buttons.append(button)

    ttk.Label(panel, textvariable=explanation_var, wraplength=760).grid(
        row=0, column=2, sticky="w", padx=(4, 12)
    )
    ttk.Label(panel, textvariable=receipt_var, foreground="#555555").grid(
        row=1, column=0, columnspan=3, sticky="w", pady=(6, 0)
    )

    def show_details() -> None:
        receipt = state["receipt"]
        if receipt is None:
            messagebox.showinfo(
                "動作モードの選択証跡",
                "まだ選択証跡はありません。既定の確認モードは学習を行いません。",
            )
            return
        messagebox.showinfo(
            "動作モードの選択証跡",
            f"モード: {MODE_LABEL_JA[receipt.selected_mode]}\n"
            f"選択日時: {receipt.selected_at}\n"
            f"証跡ID: {receipt.receipt_id}\n"
            f"証跡SHA-256: {receipt.to_dict()['receipt_sha256']}\n\n"
            "この選択は学習・外部送信・Dataset変更・モデル変更を許可しません。",
        )

    ttk.Button(panel, text="詳細", command=show_details).grid(row=1, column=3, sticky="e", padx=(8, 0))
    if load_error is not None:
        for button in buttons:
            button.configure(state="disabled")
        explanation_var.set("証跡の整合性を確認できないため、既存状態を変更しません。")

    return panel


__all__ = [
    "MODE_EXPLANATION_JA", "MODE_LABEL_JA", "build_reasoning_mode_selector_panel",
]
