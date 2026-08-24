"""TASK-054 R5B reusable Tk view for a time-aligned Commentary Preview."""

from __future__ import annotations

from typing import Callable

from .dbd_reasoning_commentary_preview import (
    CommentaryPreview,
    CommentaryPreviewKind,
    CommentaryPreviewStatus,
)


KIND_JA = {
    CommentaryPreviewKind.PLAY_BY_PLAY: "実況",
    CommentaryPreviewKind.EXPLANATION: "解説",
    CommentaryPreviewKind.TACTICAL: "戦術",
    CommentaryPreviewKind.REACTION: "反応",
}

STATUS_JA = {
    CommentaryPreviewStatus.READY: "確認できます",
    CommentaryPreviewStatus.NO_VALIDATED_COMMENTARY: "検証済みの実況・解説はまだありません",
    CommentaryPreviewStatus.NOT_CONFIRMED_MEDIA_IDENTITY: "表示動画とCanonical Assetの同一性は未確認です",
}


def format_preview_time(milliseconds: int) -> str:
    minutes, remainder = divmod(int(milliseconds), 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{minutes:02d}:{seconds:02d}.{millis:03d}"


class CommentaryPreviewPanel:
    def __init__(self, parent, *, seek_to_ms: Callable[[int], None]) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.seek_to_ms = seek_to_ms
        self.preview: CommentaryPreview | None = None
        self.commentary_visible = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="実況・解説の生成結果を読み込むと、動画の時刻に沿って表示します。")
        self.footer_var = tk.StringVar(
            value="学習データ: 変更なし / モデル: 変更なし / この確認結果から自動学習: しない"
        )
        self.frame = ttk.Frame(parent)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(2, weight=1)

        ttk.Label(self.frame, text="現在の実況・解説", font=("TkDefaultFont", 12, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(self.frame, textvariable=self.status_var, wraplength=1000).grid(
            row=1, column=0, sticky="w", pady=(4, 8)
        )
        columns = ("time", "kind", "text", "confidence", "validation")
        self.tree = ttk.Treeview(self.frame, columns=columns, show="headings", height=14)
        self.tree.grid(row=2, column=0, sticky="nsew")
        for key, title, width in (
            ("time", "開始–終了", 160), ("kind", "種類", 70), ("text", "実況・解説", 620),
            ("confidence", "確度", 80), ("validation", "検証", 90),
        ):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, stretch=key == "text")
        self.tree.bind("<<TreeviewSelect>>", self._seek_selected, add="+")

        actions = ttk.Frame(self.frame)
        actions.grid(row=3, column=0, sticky="ew", pady=(8, 4))
        ttk.Button(actions, text="前の解説", command=lambda: self._move(-1)).pack(side="left", padx=(0, 4))
        ttk.Button(actions, text="前後10秒", command=self._seek_context).pack(side="left", padx=4)
        ttk.Button(actions, text="次の解説", command=lambda: self._move(1)).pack(side="left", padx=4)
        ttk.Radiobutton(
            actions, text="解説あり", variable=self.commentary_visible, value=True,
            command=self._refresh_rows,
        ).pack(side="left", padx=(20, 4))
        ttk.Radiobutton(
            actions, text="解説なし", variable=self.commentary_visible, value=False,
            command=self._refresh_rows,
        ).pack(side="left", padx=4)
        ttk.Label(actions, text="音声合成は別Gate。ここでは本文とタイミングを比較します。", foreground="#555555").pack(
            side="left", padx=(16, 0)
        )
        ttk.Label(self.frame, textvariable=self.footer_var).grid(row=4, column=0, sticky="w", pady=(4, 0))

    def grid(self, **kwargs) -> None:
        self.frame.grid(**kwargs)

    def show(self, preview: CommentaryPreview) -> None:
        if not isinstance(preview, CommentaryPreview):
            raise ValueError("preview must be CommentaryPreview")
        self.preview = preview
        self.status_var.set(f"{STATUS_JA[preview.status]} / {len(preview.blocks)}件")
        self._refresh_rows()

    def _refresh_rows(self) -> None:
        self.tree.delete(*self.tree.get_children())
        if self.preview is None:
            return
        visible = bool(self.commentary_visible.get())
        for index, block in enumerate(self.preview.blocks):
            self.tree.insert(
                "", "end", iid=str(index), values=(
                    f"{format_preview_time(block.start_ms)}–{format_preview_time(block.end_ms)}",
                    KIND_JA[block.kind], block.text if visible else "（解説なしで比較中）",
                    f"{block.confidence_milli}/1000", block.validation_status,
                ),
            )

    def _selected_index(self) -> int | None:
        selected = self.tree.selection()
        return int(selected[0]) if selected else None

    def _seek_selected(self, _event=None) -> None:
        index = self._selected_index()
        if self.preview is not None and index is not None:
            self.seek_to_ms(self.preview.blocks[index].start_ms)

    def _seek_context(self) -> None:
        index = self._selected_index()
        if self.preview is not None and index is not None:
            self.seek_to_ms(max(0, self.preview.blocks[index].start_ms - 10_000))

    def _move(self, delta: int) -> None:
        if self.preview is None or not self.preview.blocks:
            return
        current = self._selected_index()
        target = 0 if current is None else min(max(0, current + delta), len(self.preview.blocks) - 1)
        self.tree.selection_set(str(target))
        self.tree.focus(str(target))
        self.tree.see(str(target))
        self._seek_selected()


__all__ = ["CommentaryPreviewPanel", "KIND_JA", "STATUS_JA", "format_preview_time"]
