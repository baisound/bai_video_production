"""TASK-050 R3 training data review UI."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .dbd_safe_visual_learning import TrainingDataReviewService


def build_training_data_review_panel(parent: ttk.Frame, training_workspace) -> None:
    """Build a review list with relabel/delete controls.

    This operates on the existing VisualTrainingManifest. Delete/relabel always
    require an explicit selected row; delete also requires confirmation.
    """
    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(2, weight=1)

    ttk.Label(parent, text="学習データの確認", font=("TkDefaultFont", 12, "bold")).grid(
        row=0, column=0, sticky="w", pady=(0, 6)
    )
    ttk.Label(
        parent,
        text="誤ったCropやラベルをここで確認し、学習データから除外・修正できます。",
        wraplength=900,
    ).grid(row=1, column=0, sticky="w", pady=(0, 8))

    review = TrainingDataReviewService(training_workspace.visual)
    columns = ("domain", "label", "visibility", "image")
    tree = ttk.Treeview(parent, columns=columns, show="headings", height=18)
    tree.heading("domain", text="学習対象")
    tree.heading("label", text="正解ラベル")
    tree.heading("visibility", text="表示状態")
    tree.heading("image", text="画像")
    tree.column("domain", width=130, stretch=False)
    tree.column("label", width=220)
    tree.column("visibility", width=150, stretch=False)
    tree.column("image", width=500)
    tree.grid(row=2, column=0, sticky="nsew")

    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    scrollbar.grid(row=2, column=1, sticky="ns")
    tree.configure(yscrollcommand=scrollbar.set)

    row_map: dict[str, tuple[str, str]] = {}

    def visibility_from_notes(notes: str) -> str:
        for part in notes.split("|"):
            part = part.strip()
            if part.startswith("visibility="):
                value = part.split("=", 1)[1]
                return {
                    "VISIBLE": "通常表示",
                    "PARTIALLY_OCCLUDED": "一部隠れている",
                    "HIDDEN": "完全に隠れている",
                    "UNREADABLE": "読み取れない",
                    "UNKNOWN": "判定できない",
                }.get(value, value)
        return "未記録"

    def refresh() -> None:
        for iid in tree.get_children():
            tree.delete(iid)
        row_map.clear()
        for index, item in enumerate(training_workspace.visual.list()):
            iid = f"row-{index}"
            row_map[iid] = (item.image_path, item.label)
            tree.insert(
                "", "end", iid=iid,
                values=(item.domain.value, item.label, visibility_from_notes(item.notes), item.image_path),
            )

    def selected() -> tuple[str, str] | None:
        ids = tree.selection()
        if not ids:
            messagebox.showinfo("学習データを確認", "修正する学習データを1件選択してください。")
            return None
        return row_map.get(ids[0])

    def relabel() -> None:
        value = selected()
        if value is None:
            return
        image_path, old_label = value
        new_label = simpledialog.askstring(
            "正解ラベルを修正",
            f"現在: {old_label}\n\n新しい正解ラベルを入力してください。",
            parent=parent,
        )
        if not new_label:
            return
        if review.relabel_exact(image_path=image_path, old_label=old_label, new_label=new_label):
            refresh()

    def delete() -> None:
        value = selected()
        if value is None:
            return
        image_path, label = value
        if not messagebox.askyesno(
            "学習データから削除",
            f"この登録を学習データ一覧から削除しますか？\n\n{label}\n{image_path}\n\n元動画は削除しません。",
        ):
            return
        if review.delete_exact(image_path=image_path, label=label):
            refresh()

    buttons = ttk.Frame(parent)
    buttons.grid(row=3, column=0, sticky="w", pady=(8, 0))
    ttk.Button(buttons, text="一覧を更新", command=refresh).pack(side="left", padx=(0, 6))
    ttk.Button(buttons, text="正解ラベルを修正", command=relabel).pack(side="left", padx=6)
    ttk.Button(buttons, text="学習データから削除", command=delete).pack(side="left", padx=6)
    refresh()
