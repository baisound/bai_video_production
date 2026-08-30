"""TASK-054 R5C Japanese model status/execute/review panel."""

from __future__ import annotations

from typing import Callable

from .dbd_reasoning_model_panel import (
    ModelPanelSnapshot, format_ollama_runtime_status, unavailable_ollama_runtime_snapshot,
)
from .task036_ollama_runtime import OllamaRuntimeSnapshot


class ReasoningModelPanel:
    def __init__(
        self,
        parent,
        *,
        run_preflight: Callable[[], ModelPanelSnapshot],
        open_review: Callable[[], None],
        runtime_snapshot_provider: Callable[[], OllamaRuntimeSnapshot] | None = None,
    ) -> None:
        import tkinter as tk
        from tkinter import messagebox, ttk

        self.run_preflight = run_preflight
        self.open_review = open_review
        self.runtime_snapshot_provider = runtime_snapshot_provider or unavailable_ollama_runtime_snapshot
        self.snapshot: ModelPanelSnapshot | None = None
        self.frame = ttk.Frame(parent)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)
        self.status_var = tk.StringVar(value="事前チェックを実行してください。モデル実行は既定で無効です。")
        self.runtime_status_var = tk.StringVar(value="共有Ollama状態を確認中です。")
        ttk.Label(self.frame, text="解説AIモデル", font=("TkDefaultFont", 12, "bold")).grid(row=0, column=0, sticky="w")
        columns = ("name", "role", "state", "ja", "json", "gpu", "rights", "evaluation")
        self.tree = ttk.Treeview(self.frame, columns=columns, show="headings", height=9)
        self.tree.grid(row=1, column=0, sticky="nsew", pady=(6, 6))
        for key, title, width in (
            ("name", "表示名", 150), ("role", "役割", 110), ("state", "状態", 100),
            ("ja", "日本語", 70), ("json", "JSON安定性", 100), ("gpu", "必要GPU", 80),
            ("rights", "権利", 80), ("evaluation", "最終評価", 90),
        ):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, stretch=key == "name")
        ttk.Label(self.frame, textvariable=self.status_var, wraplength=1000).grid(row=2, column=0, sticky="w")
        ttk.Label(self.frame, textvariable=self.runtime_status_var, wraplength=1000).grid(row=3, column=0, sticky="w", pady=(4, 0))
        actions = ttk.Frame(self.frame)
        actions.grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Button(actions, text="事前チェック", command=self._preflight).pack(side="left", padx=(0, 6))
        self.execute_button = ttk.Button(actions, text="現在の実況・解説を確認", state="disabled", command=lambda: None)
        self.execute_button.pack(side="left", padx=6)
        self.review_button = ttk.Button(actions, text="生成結果をレビュー", state="disabled", command=self.open_review)
        self.review_button.pack(side="left", padx=6)
        ttk.Button(actions, text="詳細を見る", command=self._details).pack(side="left", padx=6)
        self._messagebox = messagebox
        self._refresh_runtime_status()

    def grid(self, **kwargs) -> None:
        self.frame.grid(**kwargs)

    def show(self, snapshot: ModelPanelSnapshot) -> None:
        self.snapshot = snapshot
        self.runtime_status_var.set(format_ollama_runtime_status(snapshot.runtime_snapshot))
        self.tree.delete(*self.tree.get_children())
        for index, row in enumerate(snapshot.rows):
            self.tree.insert("", "end", iid=str(index), values=(
                f"{row.binding_id} r{row.revision}", row.role, row.state,
                "対応" if row.japanese_support else "非対応",
                "互換" if row.json_compatible else "非互換", row.required_gpu,
                "証跡あり" if row.rights_evidence_available else "未確認",
                "証跡あり" if row.evaluation_evidence_available else "未確認",
            ))
        self.status_var.set(f"{snapshot.status_message_ja} [{snapshot.status_code}]")
        self.execute_button.configure(state="normal" if snapshot.execution_enabled else "disabled")
        self.review_button.configure(state="normal" if snapshot.review_enabled else "disabled")

    def _refresh_runtime_status(self) -> None:
        try:
            snapshot = self.runtime_snapshot_provider()
            if not isinstance(snapshot, OllamaRuntimeSnapshot):
                raise ValueError("runtime snapshot provider returned an invalid value")
        except Exception:
            snapshot = unavailable_ollama_runtime_snapshot()
        self.runtime_status_var.set(format_ollama_runtime_status(snapshot))
    def _preflight(self) -> None:
        self._refresh_runtime_status()
        try:
            self.show(self.run_preflight())
        except Exception as exc:
            self.status_var.set("事前チェックを完了できませんでした。設定を確認してください。")
            self._messagebox.showerror("解説AIの事前チェック", f"技術詳細: {type(exc).__name__}: {exc}")

    def _details(self) -> None:
        if self.snapshot is None:
            self._messagebox.showinfo("解説AIモデルの詳細", "先に事前チェックを実行してください。")
            return
        decision = self.snapshot.route_decision
        route = "未解決" if decision is None else f"{decision.route_id} / {decision.model_id}"
        self._messagebox.showinfo(
            "解説AIモデルの詳細",
            f"経路: {route}\n実行可能: いいえ\n理由: {self.snapshot.execution_block_reason}\n"
            "事前チェックの成功は実行承認ではありません。",
        )


__all__ = ["ReasoningModelPanel"]
