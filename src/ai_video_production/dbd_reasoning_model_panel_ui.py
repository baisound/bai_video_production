"""TASK-054 Japanese model catalog, selection, and preflight panel."""

from __future__ import annotations

import threading
from queue import Empty, SimpleQueue
from typing import Callable

from .dbd_reasoning_local_runtime import (
    LocalReasoningRuntimeService,
    LocalRuntimePreflightSnapshot,
    RuntimeCheckStatus,
)
from .dbd_reasoning_model_panel import (
    ModelPanelSnapshot,
    format_ollama_runtime_status,
    unavailable_ollama_runtime_snapshot,
)
from .task036_ollama_runtime import OllamaRuntimeSnapshot


class ReasoningModelPanel:
    def __init__(
        self,
        parent,
        *,
        open_review: Callable[[], None],
        run_preflight: Callable[[], ModelPanelSnapshot] | None = None,
        runtime_service: LocalReasoningRuntimeService | None = None,
        runtime_snapshot_provider: Callable[[], OllamaRuntimeSnapshot] | None = None,
        background_preflight: bool = True,
        auto_preflight: bool = False,
    ) -> None:
        import tkinter as tk
        from tkinter import messagebox, ttk

        if run_preflight is None and runtime_service is None:
            raise ValueError("a model preflight boundary is required")
        self.run_preflight = run_preflight
        self.runtime_service = runtime_service
        self.runtime_snapshot_provider = runtime_snapshot_provider or unavailable_ollama_runtime_snapshot
        self.open_review = open_review
        self.background_preflight = bool(background_preflight)
        self.snapshot: ModelPanelSnapshot | None = None
        self.runtime_snapshot: LocalRuntimePreflightSnapshot | None = None
        self._preflight_running = False
        self._preflight_results: SimpleQueue[tuple[LocalRuntimePreflightSnapshot | None, object | None]] = SimpleQueue()
        self._candidate_by_label: dict[str, str] = {}

        self.frame = ttk.Frame(parent)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(2, weight=1)
        self.status_var = tk.StringVar(value="Model Catalogを読込中です。")
        ttk.Label(
            self.frame, text="解説AIモデル", font=("TkDefaultFont", 12, "bold")
        ).grid(row=0, column=0, sticky="w")

        selector = ttk.Frame(self.frame)
        selector.grid(row=1, column=0, sticky="ew", pady=(6, 4))
        selector.columnconfigure(1, weight=1)
        ttk.Label(selector, text="使用するModel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.selected_model_var = tk.StringVar(value="")
        self.model_selector = ttk.Combobox(
            selector, textvariable=self.selected_model_var, state="readonly", width=64,
        )
        self.model_selector.grid(row=0, column=1, sticky="ew")
        self.save_button = ttk.Button(
            selector, text="選択を保存", command=self._save_selection,
        )
        self.save_button.grid(row=0, column=2, sticky="e", padx=(8, 0))

        columns = ("name", "role", "state", "ja", "json", "gpu", "rights", "evaluation")
        self.tree = ttk.Treeview(self.frame, columns=columns, show="headings", height=5)
        self.tree.grid(row=2, column=0, sticky="nsew", pady=(2, 6))
        for key, title, width in (
            ("name", "表示名", 230), ("role", "役割", 110), ("state", "状態", 125),
            ("ja", "日本語", 70), ("json", "形式", 100), ("gpu", "必要GPU", 120),
            ("rights", "権利", 90), ("evaluation", "検証Evidence", 110),
        ):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, stretch=key == "name")

        ttk.Label(self.frame, textvariable=self.status_var, wraplength=1000).grid(
            row=3, column=0, sticky="w",
        )
        self.shared_runtime_status_var = tk.StringVar(value="共有Ollama状態を確認中です。")
        ttk.Label(
            self.frame, textvariable=self.shared_runtime_status_var, wraplength=1000,
        ).grid(row=4, column=0, sticky="w", pady=(4, 0))
        check_columns = ("item", "status", "reason", "next")
        self.check_tree = ttk.Treeview(
            self.frame, columns=check_columns, show="headings", height=8,
        )
        self.check_tree.grid(row=5, column=0, sticky="ew", pady=(6, 4))
        for key, title, width in (
            ("item", "確認項目", 165),
            ("status", "結果", 90),
            ("reason", "現在の状態", 350),
            ("next", "次の操作", 350),
        ):
            self.check_tree.heading(key, text=title)
            self.check_tree.column(key, width=width, stretch=key in {"reason", "next"})

        actions = ttk.Frame(self.frame)
        actions.grid(row=6, column=0, sticky="w", pady=(8, 0))
        self.preflight_button = ttk.Button(actions, text="事前チェック", command=self._preflight)
        self.preflight_button.pack(side="left", padx=(0, 6))
        self.execute_button = ttk.Button(
            actions, text="現在の実況・解説を確認", state="disabled", command=lambda: None,
        )
        self.execute_button.pack(side="left", padx=6)
        self.review_button = ttk.Button(
            actions, text="生成結果をレビュー", state="disabled", command=self.open_review,
        )
        self.review_button.pack(side="left", padx=6)
        ttk.Button(actions, text="詳細を見る", command=self._details).pack(side="left", padx=6)
        self._messagebox = messagebox
        self._refresh_shared_runtime_status()

        if self.runtime_service is None:
            self.model_selector.configure(state="disabled")
            self.save_button.configure(state="disabled")
            self.status_var.set("事前チェックを実行してください。モデル実行は既定で無効です。")
        else:
            self._load_catalog()
            if auto_preflight:
                self.frame.after(250, self._preflight)

    def grid(self, **kwargs) -> None:
        self.frame.grid(**kwargs)

    def _refresh_shared_runtime_status(self) -> None:
        try:
            snapshot = self.runtime_snapshot_provider()
            if not isinstance(snapshot, OllamaRuntimeSnapshot):
                raise ValueError("runtime snapshot provider returned an invalid value")
        except Exception:
            snapshot = unavailable_ollama_runtime_snapshot()
        self.shared_runtime_status_var.set(format_ollama_runtime_status(snapshot))

    def _load_catalog(self) -> None:
        assert self.runtime_service is not None
        try:
            selected = self.runtime_service.selected_candidate()
            candidates = self.runtime_service.candidates
        except Exception:
            self.status_var.set(
                "Model Catalogまたは保存済み選択の整合性を確認できません。選択と実行を停止しました。"
            )
            self.model_selector.configure(state="disabled")
            self.save_button.configure(state="disabled")
            self.preflight_button.configure(state="disabled")
            return
        self._candidate_by_label = {
            item.display_label: item.candidate_id for item in candidates
        }
        self.model_selector.configure(values=tuple(self._candidate_by_label))
        selected_label = next(
            label for label, candidate_id in self._candidate_by_label.items()
            if candidate_id == selected.candidate_id
        )
        self.selected_model_var.set(selected_label)
        self._populate_catalog(selected.candidate_id)
        self.status_var.set(
            "検証済みbase Model候補を表示しました。Dataset・学習Gateとは分離されています。"
        )

    def _populate_catalog(self, selected_candidate_id: str) -> None:
        assert self.runtime_service is not None
        self.tree.delete(*self.tree.get_children())
        for index, candidate in enumerate(self.runtime_service.candidates):
            state = "選択済み・実機検証待ち" if candidate.candidate_id == selected_candidate_id else "選択候補"
            self.tree.insert("", "end", iid=str(index), values=(
                candidate.display_label,
                "DbD実況・解説",
                state,
                "対応",
                "固定revision",
                "CUDA / 約7GiB空き",
                candidate.license_spdx,
                "R6B取得・smoke PASS",
            ))

    def _selected_candidate_id(self) -> str:
        candidate_id = self._candidate_by_label.get(self.selected_model_var.get())
        if candidate_id is None:
            raise ValueError("Model候補が選択されていません")
        return candidate_id

    def _save_selection(self) -> None:
        if self.runtime_service is None:
            return
        try:
            candidate_id = self._selected_candidate_id()
            receipt = self.runtime_service.save_selection(candidate_id)
        except Exception:
            self.status_var.set(
                "Model選択を安全に保存できませんでした。既存選択は変更していません。"
            )
            return
        self._populate_catalog(candidate_id)
        self.status_var.set(
            f"Model選択を保存しました。選択証跡: {receipt.receipt_id[-8:]}"
        )

    def show(self, snapshot: ModelPanelSnapshot) -> None:
        self.snapshot = snapshot
        self.runtime_snapshot = None
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

    def _preflight(self) -> None:
        self._refresh_shared_runtime_status()
        if self._preflight_running:
            self.status_var.set("事前チェックは実行中です。重複processは起動しません。")
            return
        if self.runtime_service is None:
            try:
                assert self.run_preflight is not None
                self.show(self.run_preflight())
            except Exception:
                self.status_var.set(
                    "事前チェックprocessを完了できませんでした。下の個別項目を確認してください。"
                )
                self._messagebox.showerror(
                    "解説AIの事前チェック",
                    "runtime接続がありません。Model・runtime・GPUの個別状態を確認してください。",
                )
            return

        try:
            candidate_id = self._selected_candidate_id()
        except ValueError as exc:
            self.status_var.set(str(exc))
            return
        self._preflight_running = True
        self.preflight_button.configure(state="disabled")
        self.check_tree.delete(*self.check_tree.get_children())
        self.status_var.set(
            "WSL・専用venv・package・Model hash・GPU・offline最小推論を確認中です。"
        )

        def execute() -> None:
            try:
                snapshot = self.runtime_service.preflight(candidate_id)
                error = None
            except Exception:
                snapshot = None
                error = True
            if self.background_preflight:
                self._preflight_results.put((snapshot, error))
            else:
                self._finish_runtime_preflight(snapshot, error)

        if self.background_preflight:
            threading.Thread(
                target=execute, name="task054-runtime-preflight", daemon=True,
            ).start()
            self.frame.after(100, self._poll_runtime_preflight)
        else:
            execute()

    def _poll_runtime_preflight(self) -> None:
        try:
            snapshot, error = self._preflight_results.get_nowait()
        except Empty:
            if self._preflight_running:
                self.frame.after(100, self._poll_runtime_preflight)
            return
        self._finish_runtime_preflight(snapshot, error)

    def _finish_runtime_preflight(
        self,
        snapshot: LocalRuntimePreflightSnapshot | None,
        error: object | None,
    ) -> None:
        self._preflight_running = False
        self.preflight_button.configure(state="normal")
        if error is not None or snapshot is None:
            self.status_var.set(
                "事前チェック結果を安全に受け取れませんでした。再downloadやinstallは行っていません。"
            )
            return
        self.runtime_snapshot = snapshot
        self.snapshot = None
        self.check_tree.delete(*self.check_tree.get_children())
        for index, check in enumerate(snapshot.checks):
            status = {
                RuntimeCheckStatus.PASS: "PASS",
                RuntimeCheckStatus.FAIL: "未完了",
                RuntimeCheckStatus.NOT_REQUIRED: "別Gate",
            }[check.status]
            self.check_tree.insert("", "end", iid=str(index), values=(
                check.label_ja, status, check.message_ja, check.next_action_ja,
            ))
        self.status_var.set(
            "事前チェック完了: Model runtimeを利用できます。"
            if snapshot.ready
            else "事前チェック未完了: 未完了の個別項目と次の操作を確認してください。"
        )
        # R3D execution remains a separate one-shot Human/authority boundary.
        self.execute_button.configure(state="disabled")
        self.review_button.configure(state="disabled")
        self._populate_catalog(snapshot.candidate_id)
        if snapshot.ready:
            first = self.tree.get_children()[0]
            values = list(self.tree.item(first, "values"))
            values[2] = "選択済み・runtime PASS"
            self.tree.item(first, values=values)

    def _details(self) -> None:
        if self.runtime_snapshot is not None:
            lines = [
                f"{item.label_ja}: {item.status.value} / {item.detail_code}"
                for item in self.runtime_snapshot.checks
            ]
            self._messagebox.showinfo(
                "解説AIモデルの詳細",
                "\n".join(lines)
                + "\n\n事前チェックはProvider実行・学習・Dataset採用を許可しません。"
            )
            return
        if self.snapshot is None:
            self._messagebox.showinfo(
                "解説AIモデルの詳細",
                "Model候補を選択し、事前チェックを実行してください。"
            )
            return
        decision = self.snapshot.route_decision
        route = "未解決" if decision is None else f"{decision.route_id} / {decision.model_id}"
        self._messagebox.showinfo(
            "解説AIモデルの詳細",
            f"経路: {route}\n実行可能: いいえ\n理由: {self.snapshot.execution_block_reason}\n"
            "事前チェックの成功は実行承認ではありません。",
        )


__all__ = ["ReasoningModelPanel"]
