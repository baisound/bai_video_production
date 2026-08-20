"""Reusable Japanese-first DbD game-element selector for Training Studio."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
from typing import Callable

from .canonical_game_event import GameKnowledgeKind
from .dbd_entity_aliases import EntityAliasCatalog, EntityAliasResolution

_KIND_JA = {
    GameKnowledgeKind.PERK: "パーク",
    GameKnowledgeKind.KILLER: "キラー",
    GameKnowledgeKind.POWER: "能力",
    GameKnowledgeKind.MAP: "マップ",
    GameKnowledgeKind.REALM: "レルム",
    GameKnowledgeKind.TILE: "地形",
    GameKnowledgeKind.ADDON: "アドオン",
    GameKnowledgeKind.ITEM: "アイテム",
    GameKnowledgeKind.OFFERING: "オファリング",
    GameKnowledgeKind.CHARACTER: "キャラクター",
    GameKnowledgeKind.SURVIVOR: "サバイバー",
    GameKnowledgeKind.KNOWLEDGE: "ナレッジ系",
    GameKnowledgeKind.STATUS: "状態",
    GameKnowledgeKind.MECHANIC: "ゲーム仕様",
}

def open_game_element_selector(
    parent,
    *,
    catalog: EntityAliasCatalog,
    title: str,
    on_select: Callable[[EntityAliasResolution], None],
    expected_kind: GameKnowledgeKind | None = None,
    display_name_resolver: Callable[[EntityAliasResolution], str] | None = None,
    image_path_resolver: Callable[[EntityAliasResolution], str | None] | None = None,
    verified_only: bool = False,
) -> None:
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.geometry("760x470")
    dialog.minsize(620, 360)
    dialog.transient(parent)
    dialog.grab_set()
    dialog.columnconfigure(0, weight=1)
    dialog.rowconfigure(2, weight=1)

    header = ttk.Frame(dialog, padding=(12, 12, 12, 6))
    header.grid(row=0, column=0, sticky="ew")
    header.columnconfigure(0, weight=1)
    expected = "すべて" if expected_kind is None else _KIND_JA.get(expected_kind, expected_kind.value)
    ttk.Label(
        header,
        text=f"正式名・読み・英語名・略称・通称から検索できます。対象: {expected}",
        wraplength=700,
    ).grid(row=0, column=0, sticky="w")

    search_row = ttk.Frame(dialog, padding=(12, 4))
    search_row.grid(row=1, column=0, sticky="ew")
    search_row.columnconfigure(0, weight=1)
    query_var = tk.StringVar()
    query_entry = ttk.Entry(search_row, textvariable=query_var)
    query_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

    body = ttk.Frame(dialog, padding=(12, 4, 12, 12))
    body.grid(row=2, column=0, sticky="nsew")
    body.columnconfigure(0, weight=1)
    body.rowconfigure(0, weight=1)
    body.columnconfigure(2, weight=0)
    result_list = tk.Listbox(body, exportselection=False)
    result_scroll = ttk.Scrollbar(body, orient="vertical", command=result_list.yview)
    result_list.configure(yscrollcommand=result_scroll.set)
    result_list.grid(row=0, column=0, sticky="nsew")
    result_scroll.grid(row=0, column=1, sticky="ns")
    preview = ttk.Label(body, text="画像プレビュー", anchor="center", width=20)
    preview.grid(row=0, column=2, sticky="n", padx=(12, 0))
    preview._photo_ref = None  # type: ignore[attr-defined]

    status_var = tk.StringVar(
        value="検索語を入力して［検索］を押してください。例: 鋼の意志 / アイウィル / Iron Will"
    )
    ttk.Label(body, textvariable=status_var, wraplength=700).grid(
        row=1, column=0, columnspan=2, sticky="w", pady=(8, 0)
    )

    current_rows: list[EntityAliasResolution] = []

    def run_search(_event=None) -> None:
        query = query_var.get().strip()
        if not query:
            status_var.set("検索語を入力してください。")
            query_entry.focus_set()
            return
        if catalog.count() == 0:
            status_var.set(
                "検索用ゲーム要素が0件です。先に［ゲーム情報を取得］で候補を取り込み、"
                "Alias/Knowledgeを登録し、正解ラベル用途では内容を確認済みにしてください。"
            )
            return
        try:
            rows = catalog.search(
                query,
                knowledge_kind=expected_kind,
                verified_only=verified_only,
                limit=50,
            )
        except Exception as exc:
            messagebox.showerror(
                "ゲーム要素を検索できませんでした",
                "検索処理を完了できませんでした。\n\n"
                f"技術詳細: {type(exc).__name__}: {exc}",
                parent=dialog,
            )
            return
        current_rows[:] = rows
        result_list.delete(0, tk.END)
        for row in rows:
            kind = _KIND_JA.get(row.knowledge_kind, row.knowledge_kind.value)
            display = display_name_resolver(row) if display_name_resolver is not None else row.matched_text
            result_list.insert(tk.END, f"{display}  [{kind}]  {row.matched_text}")
        status_var.set(
            f"{len(rows)}件見つかりました。候補を選択して［このゲーム要素を使う］を押してください。"
            if rows
            else "一致する登録済みゲーム要素がありません。別の正式名・略称で検索してください。"
        )


    def update_preview(_event=None) -> None:
        selected = result_list.curselection()
        if not selected or image_path_resolver is None:
            preview.configure(image="", text="画像プレビュー")
            preview._photo_ref = None  # type: ignore[attr-defined]
            return
        row = current_rows[selected[0]]
        raw = image_path_resolver(row)
        if not raw:
            preview.configure(image="", text="画像なし")
            preview._photo_ref = None  # type: ignore[attr-defined]
            return
        path = Path(raw)
        try:
            try:
                from PIL import Image, ImageTk
                with Image.open(path) as opened:
                    image = opened.convert("RGBA"); image.thumbnail((180, 180)); photo = ImageTk.PhotoImage(image)
            except Exception:
                photo = tk.PhotoImage(file=str(path))
                factor = max(1, (max(photo.width(), photo.height()) + 159) // 160)
                if factor > 1:
                    photo = photo.subsample(factor, factor)
            preview.configure(image=photo, text="")
            preview._photo_ref = photo  # type: ignore[attr-defined]
        except Exception:
            preview.configure(image="", text=f"画像を表示できません\n{path.name}")
            preview._photo_ref = None  # type: ignore[attr-defined]

    def accept(_event=None) -> None:
        selected = result_list.curselection()
        if not selected:
            status_var.set("候補を1件選択してください。")
            return
        row = current_rows[selected[0]]
        on_select(row)
        dialog.destroy()

    ttk.Button(search_row, text="検索", command=run_search).grid(row=0, column=1)
    action_row = ttk.Frame(dialog, padding=(12, 0, 12, 12))
    action_row.grid(row=3, column=0, sticky="e")
    ttk.Button(action_row, text="キャンセル", command=dialog.destroy).pack(side="right", padx=(8, 0))
    ttk.Button(action_row, text="このゲーム要素を使う", command=accept).pack(side="right")

    query_entry.bind("<Return>", run_search)
    result_list.bind("<<ListboxSelect>>", update_preview)
    result_list.bind("<Double-Button-1>", accept)
    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.after(50, query_entry.focus_force)
