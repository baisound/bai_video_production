"""TASK-054 R5D Japanese read-only Dataset/evaluation panel."""

from __future__ import annotations

from .dbd_reasoning_dataset_evaluation_view import DatasetEvaluationSnapshot


class DatasetEvaluationPanel:
    def __init__(self, parent) -> None:
        import tkinter as tk
        from tkinter import messagebox, ttk

        self.snapshot: DatasetEvaluationSnapshot | None = None
        self.frame = ttk.Frame(parent)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(2, weight=1)
        self.summary_var = tk.StringVar(value="Datasetと評価Evidenceを読み込んでください。")
        ttk.Label(self.frame, text="学習素材とモデル評価", font=("TkDefaultFont", 12, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(self.frame, textvariable=self.summary_var, wraplength=1000).grid(row=1, column=0, sticky="w", pady=(4, 8))
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.grid(row=2, column=0, sticky="nsew")
        dataset = ttk.Frame(self.notebook, padding=8)
        evaluation = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(dataset, text="Dataset監査")
        self.notebook.add(evaluation, text="モデル比較")
        dataset.columnconfigure(0, weight=1)
        dataset.rowconfigure(0, weight=1)
        evaluation.columnconfigure(0, weight=1)
        evaluation.rowconfigure(0, weight=1)
        self.split_tree = ttk.Treeview(dataset, columns=("split", "total", "eligible", "review", "locked"), show="headings")
        self.split_tree.grid(row=0, column=0, sticky="nsew")
        for key, title in (("split", "Split"), ("total", "件数"), ("eligible", "候補"), ("review", "要確認"), ("locked", "編集")):
            self.split_tree.heading(key, text=title)
        ttk.Label(dataset, text="Test splitの期待文は表示せず、通常画面から移動・編集できません。", foreground="#555555").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.arm_tree = ttk.Treeview(evaluation, columns=("arm", "status", "samples", "schema", "citation", "replay", "negative"), show="headings")
        self.arm_tree.grid(row=0, column=0, sticky="nsew")
        for key, title in (("arm", "モデル"), ("status", "状態"), ("samples", "件数"), ("schema", "JSON"), ("citation", "引用"), ("replay", "再現性"), ("negative", "話さない判断")):
            self.arm_tree.heading(key, text=title)
        ttk.Label(self.frame, text="Dataset採用: 不可 / モデル昇格: Owner判断が必要 / この画面はEvidence閲覧専用").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Button(self.frame, text="Evidence詳細", command=self._details).grid(row=3, column=1, padx=(8, 0))
        self._messagebox = messagebox

    def grid(self, **kwargs) -> None:
        self.frame.grid(**kwargs)

    def show(self, snapshot: DatasetEvaluationSnapshot) -> None:
        if not isinstance(snapshot, DatasetEvaluationSnapshot):
            raise ValueError("snapshot must be DatasetEvaluationSnapshot")
        self.snapshot = snapshot
        self.split_tree.delete(*self.split_tree.get_children())
        for index, item in enumerate(snapshot.splits):
            self.split_tree.insert("", "end", iid=str(index), values=(
                item.split.value, item.total_count, item.eligible_count,
                item.needs_review_count, "固定" if not item.editable else "可能",
            ))
        self.arm_tree.delete(*self.arm_tree.get_children())
        for index, item in enumerate(snapshot.evaluation_arms):
            self.arm_tree.insert("", "end", iid=str(index), values=(
                item.arm, item.status, item.sample_count, f"{item.schema_valid_milli}/1000",
                f"{item.citation_coverage_milli}/1000", f"{item.replay_stability_milli}/1000",
                "未確認" if item.safe_negative_abstention_milli is None else f"{item.safe_negative_abstention_milli}/1000",
            ))
        self.summary_var.set(
            f"Dataset {snapshot.manifest_id} r{snapshot.manifest_revision} / "
            f"漏洩監査 {snapshot.leakage_status} / offline評価 {snapshot.evaluation_status.value} / "
            f"blind review {snapshot.blind_review_status.value} / promotion候補 {snapshot.promotion_status}"
        )

    def _details(self) -> None:
        if self.snapshot is None:
            self._messagebox.showinfo("Evidence詳細", "先にDataset Evidenceを読み込んでください。")
            return
        self._messagebox.showinfo(
            "Evidence詳細",
            f"Manifest SHA-256: {self.snapshot.manifest_sha256}\n"
            f"漏洩finding: {self.snapshot.leakage_finding_count}件\n"
            f"Blind sample: {self.snapshot.blind_sample_count}件\n"
            "閲覧結果からDataset採用やモデル昇格は実行されません。",
        )


__all__ = ["DatasetEvaluationPanel"]
