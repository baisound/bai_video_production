"""TASK-051 R6 unified Training Studio review panel.

This view is intentionally a review surface over existing stores. It does not
create competing canonical game truth.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import csv
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from .canonical_game_event import GameKnowledgeKind
from .dbd_commentary_knowledge import TriviaStatus
from .dbd_entity_aliases import EntityAliasCatalog
from .dbd_game_element_selector_ui import open_game_element_selector
from .dbd_game_knowledge_catalog import GameKnowledgeReviewCatalog
from .dbd_safe_visual_learning import TrainingDataReviewService
from .dbd_training_form_support import VISUAL_TRAINING_DOMAIN_JA
from .dbd_notification_semantics import NotificationSemanticStore, notification_signal_label


ALIAS_STATUS_JA = {
    "CANDIDATE": "取込候補",
    "VERIFIED": "確認済み",
    "NEEDS_REVIEW": "要再確認",
    "UPDATE_AVAILABLE": "更新候補あり",
    "REJECTED": "却下",
    "DISABLED": "無効",
}
ALIAS_TYPE_JA = {
    "OFFICIAL_NAME": "正式名称",
    "OFFICIAL_ENGLISH": "英語正式名称",
    "READING": "読み",
    "COMMUNITY_SHORT_NAME": "一般的な略称",
    "COMMUNITY_NICKNAME": "通称",
    "ASR_VARIANT": "音声認識ゆれ",
    "COMMON_MISSPELLING": "よくある表記ゆれ",
}
TRIVIA_STATUS_JA = {
    TriviaStatus.CANDIDATE: "候補",
    TriviaStatus.VERIFIED: "確認済み",
    TriviaStatus.REJECTED: "却下",
    TriviaStatus.SUPERSEDED: "削除済み",
}


@dataclass(frozen=True, slots=True)
class ReviewCounts:
    alias_total: int = 0
    alias_candidate: int = 0
    alias_verified: int = 0
    visual_total: int = 0
    ocr_total: int = 0
    trivia_total: int = 0
    trivia_candidate: int = 0
    trivia_verified: int = 0
    human_gold_total: int = 0

    @property
    def total_registered(self) -> int:
        return (
            self.alias_total
            + self.visual_total
            + self.ocr_total
            + self.trivia_total
            + self.human_gold_total
        )


def _alias_rows(workspace_root: Path) -> tuple[tuple[str, ...], ...]:
    path = workspace_root / "knowledge" / "entity-aliases.sqlite"
    if not path.is_file():
        return ()
    with closing(sqlite3.connect(path)) as conn:
        rows = conn.execute(
            """SELECT entity_id, knowledge_kind, alias_text, alias_type,
                      review_status, source_ref
               FROM entity_alias
               ORDER BY
                 CASE review_status
                   WHEN 'CANDIDATE' THEN 0
                   WHEN 'VERIFIED' THEN 1
                   ELSE 2
                 END,
                 knowledge_kind, alias_text, entity_id"""
        ).fetchall()
    return tuple(tuple(str(value or "") for value in row) for row in rows)


def _alias_counts(workspace_root: Path) -> tuple[int, int, int]:
    rows = _alias_rows(workspace_root)
    return (
        len(rows),
        sum(1 for row in rows if row[4] == "CANDIDATE"),
        sum(1 for row in rows if row[4] == "VERIFIED"),
    )


def _count_rows_in_file(path: Path) -> int:
    if not path.is_file():
        return 0
    suffix = path.suffix.lower()
    try:
        if suffix == ".jsonl":
            return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        if suffix == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                return max(0, sum(1 for _ in csv.reader(handle)) - 1)
    except (OSError, UnicodeError, csv.Error):
        return 0
    return 0


def _human_gold_files(workspace_root: Path) -> tuple[Path, ...]:
    """Bounded known-location inventory; never recursively scan the workspace."""
    candidates: list[Path] = []
    directories = (
        workspace_root / "human-gold",
        workspace_root / "human_gold",
        workspace_root / "knowledge" / "human-gold",
        workspace_root / "knowledge" / "human_gold",
    )
    for directory in directories:
        if not directory.is_dir():
            continue
        for pattern in ("*.jsonl", "*.csv"):
            candidates.extend(sorted(directory.glob(pattern)))
    for pattern in (
        "human-gold*.jsonl",
        "human-gold*.csv",
        "human_gold*.jsonl",
        "human_gold*.csv",
    ):
        candidates.extend(sorted(workspace_root.glob(pattern)))
    unique: dict[str, Path] = {}
    for path in candidates:
        unique[str(path.resolve())] = path
    return tuple(unique.values())


def collect_review_counts(training_workspace) -> ReviewCounts:
    root = Path(training_workspace.root)
    alias_total, alias_candidate, alias_verified = _alias_counts(root)
    trivia = training_workspace.trivia.list_latest()
    gold_files = _human_gold_files(root)
    return ReviewCounts(
        alias_total=alias_total,
        alias_candidate=alias_candidate,
        alias_verified=alias_verified,
        visual_total=len(training_workspace.visual.list()),
        ocr_total=len(training_workspace.ocr.list()),
        trivia_total=len(trivia),
        trivia_candidate=sum(1 for row in trivia if row.status is TriviaStatus.CANDIDATE),
        trivia_verified=sum(1 for row in trivia if row.status is TriviaStatus.VERIFIED),
        human_gold_total=sum(_count_rows_in_file(path) for path in gold_files),
    )


def _empty_state(parent, text: str) -> ttk.Label:
    label = ttk.Label(parent, text=text, foreground="#666666", wraplength=900)
    label.pack(anchor="w", padx=8, pady=12)
    return label


def build_training_data_review_panel(parent: ttk.Frame, training_workspace) -> Callable[[], None]:
    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(2, weight=1)

    ttk.Label(
        parent,
        text="学習・登録データを確認",
        font=("TkDefaultFont", 12, "bold"),
    ).grid(row=0, column=0, sticky="w", pady=(0, 4))
    ttk.Label(
        parent,
        text=(
            "ゲーム情報、画像・Crop、右上通知、実況・豆知識、Human Gold / その他を"
            "同じ場所で確認します。候補と確認済みを混同せず、データ種別に合った操作だけを表示します。"
        ),
        wraplength=950,
    ).grid(row=1, column=0, sticky="w", pady=(0, 8))

    review_notebook = ttk.Notebook(parent)
    review_notebook.grid(row=2, column=0, sticky="nsew")

    summary_tab = ttk.Frame(review_notebook, padding=12)
    game_tab = ttk.Frame(review_notebook, padding=12)
    visual_tab = ttk.Frame(review_notebook, padding=12)
    ocr_tab = ttk.Frame(review_notebook, padding=12)
    trivia_tab = ttk.Frame(review_notebook, padding=12)
    gold_tab = ttk.Frame(review_notebook, padding=12)
    review_notebook.add(summary_tab, text="すべて")
    review_notebook.add(game_tab, text="ゲーム情報")
    review_notebook.add(visual_tab, text="画像・Crop学習")
    review_notebook.add(ocr_tab, text="右上通知")
    review_notebook.add(trivia_tab, text="実況・豆知識")
    review_notebook.add(gold_tab, text="Human Gold / その他")

    # Summary -----------------------------------------------------------------
    summary_tab.columnconfigure(0, weight=1)
    summary_frame = ttk.Frame(summary_tab)
    summary_frame.grid(row=0, column=0, sticky="ew")
    summary_frame.columnconfigure(1, weight=1)
    summary_vars = {
        "game": tk.StringVar(),
        "visual": tk.StringVar(),
        "ocr": tk.StringVar(),
        "trivia": tk.StringVar(),
        "gold": tk.StringVar(),
        "total": tk.StringVar(),
    }
    for row_no, (title, key) in enumerate(
        (
            ("ゲーム情報 / Alias", "game"),
            ("画像・Crop学習", "visual"),
            ("右上通知", "ocr"),
            ("実況・豆知識", "trivia"),
            ("Human Gold / その他", "gold"),
            ("総登録件数", "total"),
        )
    ):
        ttk.Label(summary_frame, text=title).grid(
            row=row_no, column=0, sticky="w", padx=(0, 16), pady=5
        )
        ttk.Label(
            summary_frame,
            textvariable=summary_vars[key],
            font=("TkDefaultFont", 10, "bold"),
        ).grid(row=row_no, column=1, sticky="w", pady=5)

    ttk.Label(
        summary_tab,
        text=(
            "※ 件数は「このワークスペースで現在確認できる登録」です。"
            "候補は確認済みデータとは別に数えます。"
        ),
        foreground="#666666",
        wraplength=900,
    ).grid(row=1, column=0, sticky="w", pady=(12, 0))

    # Game information / aliases ---------------------------------------------
    game_tab.columnconfigure(0, weight=1)
    game_tab.rowconfigure(1, weight=1)
    game_status = tk.StringVar()
    ttk.Label(
        game_tab,
        textvariable=game_status,
        wraplength=900,
    ).grid(row=0, column=0, sticky="w", pady=(0, 6))
    game_tree = ttk.Treeview(
        game_tab,
        columns=("status","kind","alias","type","entity","source"),
        show="headings",
        height=14,
    )
    for key, title, width in (
        ("status","状態",80),
        ("kind","種類",110),
        ("alias","名称・別名",220),
        ("type","Alias種別",140),
        ("entity","ゲーム要素ID",220),
        ("source","情報源",300),
    ):
        game_tree.heading(key, text=title)
        game_tree.column(key, width=width, stretch=True)
    game_tree.grid(row=1, column=0, sticky="nsew")
    game_rows: list[tuple[str, ...]] = []

    def refresh_game() -> None:
        game_tree.delete(*game_tree.get_children())
        game_rows.clear()
        for index, row in enumerate(_alias_rows(Path(training_workspace.root))):
            game_rows.append(row)
            game_tree.insert(
                "", "end", iid=str(index),
                values=(
                    ALIAS_STATUS_JA.get(row[4], row[4]),
                    row[1],
                    row[2],
                    ALIAS_TYPE_JA.get(row[3], row[3]),
                    row[0],
                    "手入力" if row[5] == "manual://owner" else row[5],
                ),
            )
        total, candidate, verified = _alias_counts(Path(training_workspace.root))
        game_status.set(
            f"登録={total}件 / 候補={candidate}件 / 確認済み={verified}件"
            if total
            else "ゲーム情報 / Aliasはまだ登録されていません。"
        )

    def selected_game_row():
        selected = game_tree.selection()
        if not selected:
            return None
        index = int(selected[0])
        return game_rows[index] if 0 <= index < len(game_rows) else None

    def set_alias_status(new_status: str) -> None:
        row = selected_game_row()
        if row is None:
            messagebox.showinfo("ゲーム情報", "対象を1件選択してください。")
            return
        if not messagebox.askyesno(
            "ゲーム情報を確認",
            f"「{row[2]}」を「{ALIAS_STATUS_JA[new_status]}」に変更しますか？\n\n"
            "Aliasは検索・音声認識の補助情報であり、Canonical Game Knowledgeそのものは変更しません。",
        ):
            return
        path = Path(training_workspace.root) / "knowledge" / "entity-aliases.sqlite"
        with closing(sqlite3.connect(path)) as conn:
            with conn:
                conn.execute(
                    """UPDATE entity_alias SET review_status=?
                       WHERE entity_id=? AND knowledge_kind=? AND alias_text=?
                         AND alias_type=?""",
                    (new_status, row[0], row[1], row[2], row[3]),
                )
        refresh_game()
        refresh_summary()

    game_buttons = ttk.Frame(game_tab)
    game_buttons.grid(row=2, column=0, sticky="w", pady=(8, 0))
    ttk.Button(game_buttons, text="この一覧を再読み込み", command=refresh_game).pack(side="left", padx=(0, 6))
    ttk.Button(
        game_buttons,
        text="確認済みにする",
        command=lambda: set_alias_status("VERIFIED"),
    ).pack(side="left", padx=6)
    ttk.Button(
        game_buttons,
        text="却下",
        command=lambda: set_alias_status("REJECTED"),
    ).pack(side="left", padx=6)

    # Visual/Crop --------------------------------------------------------------
    visual_tab.columnconfigure(0, weight=1)
    visual_tab.rowconfigure(2, weight=1)
    visual_status = tk.StringVar()
    visual_filters = ttk.Frame(visual_tab)
    visual_filters.grid(row=0, column=0, sticky="ew", pady=(0, 6))
    visual_filters.columnconfigure(3, weight=1)
    ttk.Label(visual_filters, text="学習対象").grid(row=0, column=0, sticky="w")
    visual_domain_filter = tk.StringVar(value="すべて")
    domain_values = ["すべて", *VISUAL_TRAINING_DOMAIN_JA.values()]
    ttk.Combobox(visual_filters, textvariable=visual_domain_filter, values=domain_values, state="readonly", width=20).grid(row=0, column=1, sticky="w", padx=(6, 16))
    ttk.Label(visual_filters, text="キーワード").grid(row=0, column=2, sticky="w")
    visual_query = tk.StringVar()
    visual_query_entry = ttk.Entry(visual_filters, textvariable=visual_query)
    visual_query_entry.grid(row=0, column=3, sticky="ew", padx=(6, 8))
    ttk.Button(visual_filters, text="検索", command=lambda: refresh_visual()).grid(row=0, column=4, sticky="w")
    ttk.Label(visual_tab, textvariable=visual_status).grid(row=1, column=0, sticky="w", pady=(0, 6))

    visual_tree = ttk.Treeview(
        visual_tab,
        columns=("target","label","visibility","group","source","path"),
        show="tree headings",
        height=14,
    )
    visual_tree.heading("#0", text="画像")
    visual_tree.column("#0", width=110, stretch=False)
    for key, title, width in (
        ("target","学習対象",130),
        ("label","正解ラベル",220),
        ("visibility","表示状態",130),
        ("group","画像グループ",120),
        ("source","情報源",220),
        ("path","画像・Crop",300),
    ):
        visual_tree.heading(key, text=title)
        visual_tree.column(key, width=width, stretch=True)
    visual_tree.grid(row=2, column=0, sticky="nsew")
    visual_scroll = ttk.Scrollbar(visual_tab, orient="vertical", command=visual_tree.yview)
    visual_tree.configure(yscrollcommand=visual_scroll.set)
    visual_scroll.grid(row=2, column=1, sticky="ns")
    visual_rows = []
    visual_photos: dict[str, tk.PhotoImage] = {}
    visual_review = TrainingDataReviewService(training_workspace.visual)
    alias_catalog = EntityAliasCatalog(Path(training_workspace.root) / "knowledge" / "entity-aliases.sqlite")
    knowledge_catalog = GameKnowledgeReviewCatalog(Path(training_workspace.root) / "knowledge" / "game-knowledge-review.json")

    def visibility_from_notes(notes: str) -> str:
        for part in notes.split("|"):
            part = part.strip()
            if part.startswith("visibility="):
                value = part.split("=", 1)[1]
                return {
                    "VISIBLE":"通常表示",
                    "PARTIALLY_OCCLUDED":"一部隠れている",
                    "HIDDEN":"完全に隠れている",
                    "UNREADABLE":"読み取れない",
                    "UNKNOWN":"判定できない",
                }.get(value, value)
        return "未記録"

    def entity_display_name(entity_id: str) -> str:
        for row in _alias_rows(Path(training_workspace.root)):
            if row[0] == entity_id and row[3] == "OFFICIAL_NAME":
                return row[2]
        return entity_id

    def candidate_image(entity_id: str) -> str | None:
        try:
            value = knowledge_catalog.get(entity_id).effective_image
            return value or None
        except Exception:
            return None

    def visual_kind(item) -> GameKnowledgeKind | None:
        return {
            "PERK_ICON": GameKnowledgeKind.PERK,
            "ITEM_ICON": GameKnowledgeKind.ITEM,
            "ADDON_ICON": GameKnowledgeKind.ADDON,
            "KILLER_POWER": GameKnowledgeKind.POWER,
        }.get(item.domain.value)

    def load_thumbnail(iid: str, path_text: str) -> tk.PhotoImage | None:
        path = Path(path_text)
        if not path.is_file():
            return None
        try:
            try:
                from PIL import Image, ImageTk
                with Image.open(path) as opened:
                    image = opened.convert("RGBA"); image.thumbnail((96, 96)); photo = ImageTk.PhotoImage(image)
            except Exception:
                photo = tk.PhotoImage(file=str(path))
                factor = max(1, (max(photo.width(), photo.height()) + 95) // 96)
                if factor > 1: photo = photo.subsample(factor, factor)
            visual_photos[iid] = photo
            return photo
        except Exception:
            return None

    def refresh_visual() -> None:
        visual_tree.delete(*visual_tree.get_children())
        visual_rows.clear(); visual_photos.clear()
        values = training_workspace.visual.list()
        domain_filter = visual_domain_filter.get().strip()
        needle = visual_query.get().strip().casefold()
        shown = 0
        for item in values:
            target_ja = VISUAL_TRAINING_DOMAIN_JA.get(item.domain.value, item.domain.value)
            label_name = entity_display_name(item.label)
            if domain_filter != "すべて" and target_ja != domain_filter:
                continue
            hay = "\n".join((target_ja, item.label, label_name, item.group, item.notes, item.source_ref, Path(item.image_path).name)).casefold()
            if needle and needle not in hay:
                continue
            index = len(visual_rows); iid = str(index); visual_rows.append(item)
            photo = load_thumbnail(iid, item.image_path)
            visual_tree.insert(
                "", "end", iid=iid, text=("" if photo else "画像なし"), image=(photo or ""),
                values=(
                    target_ja,
                    label_name,
                    visibility_from_notes(item.notes),
                    item.group,
                    "手入力" if item.source_ref == "manual://owner" else item.source_ref,
                    item.image_path,
                ),
            )
            shown += 1
        visual_status.set(
            f"登録済み画像・Crop: {len(values)}件 / 表示 {shown}件"
            if values else "画像・Crop学習データはまだ登録されていません。"
        )

    def selected_visual():
        selected = visual_tree.selection()
        if not selected:
            return None
        index = int(selected[0])
        return visual_rows[index] if 0 <= index < len(visual_rows) else None

    def preview_visual() -> None:
        item = selected_visual()
        if item is None:
            messagebox.showinfo("画像・Crop学習", "画像を確認するデータを1件選択してください。")
            return
        modal = tk.Toplevel(parent); modal.title("画像・Cropプレビュー"); modal.transient(parent); modal.grab_set()
        try:
            try:
                from PIL import Image, ImageTk
                with Image.open(item.image_path) as opened:
                    image=opened.convert("RGBA"); image.thumbnail((960,720)); photo=ImageTk.PhotoImage(image)
            except Exception:
                photo = tk.PhotoImage(file=item.image_path)
                factor = max(1, (max(photo.width(), photo.height()) + 719) // 720)
                if factor > 1: photo = photo.subsample(factor, factor)
            label = ttk.Label(modal, image=photo); label.image = photo  # type: ignore[attr-defined]
            label.pack(padx=12, pady=12)
        except Exception as exc:
            ttk.Label(modal, text=f"画像を表示できません。\n{item.image_path}\n{type(exc).__name__}: {exc}").pack(padx=20, pady=20)
        ttk.Button(modal, text="閉じる", command=modal.destroy).pack(pady=(0, 12))

    def relabel_visual() -> None:
        item = selected_visual()
        if item is None:
            messagebox.showinfo("画像・Crop学習", "修正するデータを1件選択してください。")
            return
        def selected_resolution(resolution) -> None:
            if visual_review.relabel_exact(image_path=item.image_path, old_label=item.label, new_label=resolution.entity_id):
                refresh_visual(); refresh_summary()
        open_game_element_selector(
            parent, catalog=alias_catalog, title="正解ラベルを画像・名称から選択",
            on_select=selected_resolution, expected_kind=visual_kind(item),
            display_name_resolver=lambda row: entity_display_name(row.entity_id),
            image_path_resolver=lambda row: candidate_image(row.entity_id), verified_only=True,
        )

    def delete_visual() -> None:
        item = selected_visual()
        if item is None: return
        if not messagebox.askyesno("画像・Crop学習から削除", f"{entity_display_name(item.label)}\n{item.image_path}\n\nこの登録を学習データから削除しますか？"):
            return
        if visual_review.delete_exact(image_path=item.image_path, label=item.label):
            refresh_visual(); refresh_summary()

    visual_domain_filter.trace_add("write", lambda *_: refresh_visual())
    visual_query_entry.bind("<Return>", lambda _e: refresh_visual())
    visual_buttons = ttk.Frame(visual_tab)
    visual_buttons.grid(row=3, column=0, sticky="w", pady=(8, 0))
    ttk.Button(visual_buttons, text="この一覧を再読み込み", command=refresh_visual).pack(side="left", padx=(0, 6))
    ttk.Button(visual_buttons, text="画像を大きく表示", command=preview_visual).pack(side="left", padx=6)
    ttk.Button(visual_buttons, text="正解ラベルを選び直す", command=relabel_visual).pack(side="left", padx=6)
    ttk.Button(visual_buttons, text="学習データから削除", command=delete_visual).pack(side="left", padx=6)

    # OCR ---------------------------------------------------------------------
    ocr_tab.columnconfigure(0, weight=1)
    ocr_tab.rowconfigure(1, weight=1)
    ocr_status = tk.StringVar()
    ttk.Label(ocr_tab, textvariable=ocr_status).grid(row=0, column=0, sticky="w", pady=(0, 6))
    ocr_tree = ttk.Treeview(
        ocr_tab,
        columns=("signal","phrase","meaning","language","source"),
        show="headings",
        height=14,
    )
    for key, title, width in (
        ("signal","通知の種類",190),
        ("phrase","画面表示文字",280),
        ("meaning","意味・説明",320),
        ("language","言語",90),
        ("source","情報源",260),
    ):
        ocr_tree.heading(key, text=title)
        ocr_tree.column(key, width=width, stretch=True)
    ocr_tree.grid(row=1, column=0, sticky="nsew")
    ocr_rows = []
    ocr_semantics = NotificationSemanticStore(
        Path(training_workspace.root) / "knowledge" / "upper-right-notification-semantics.json"
    )

    def refresh_ocr() -> None:
        ocr_tree.delete(*ocr_tree.get_children())
        ocr_rows.clear()
        values = training_workspace.ocr.list()
        for index, item in enumerate(values):
            ocr_rows.append(item)
            semantic = ocr_semantics.find(item.signal_id, item.phrase)
            ocr_tree.insert(
                "", "end", iid=str(index),
                values=(
                    notification_signal_label(item.signal_id),
                    item.phrase,
                    semantic.meaning if semantic else "",
                    "日本語" if item.locale == "ja-JP" else item.locale,
                    "手入力" if item.source_ref == "manual://owner" else item.source_ref,
                ),
            )
        ocr_status.set(
            f"登録済み右上通知: {len(values)}件"
            if values
            else "右上通知データはまだ登録されていません。"
        )

    def selected_ocr():
        selected = ocr_tree.selection()
        if not selected:
            return None
        index = int(selected[0])
        return ocr_rows[index] if 0 <= index < len(ocr_rows) else None

    def delete_ocr() -> None:
        item = selected_ocr()
        if item is None:
            return
        if not messagebox.askyesno(
            "右上通知を削除",
            f"「{item.phrase}」を登録済み通知から削除しますか？",
        ):
            return
        training_workspace.ocr.delete(item)
        refresh_ocr()
        refresh_summary()

    ocr_buttons = ttk.Frame(ocr_tab)
    ocr_buttons.grid(row=2, column=0, sticky="w", pady=(8, 0))
    ttk.Button(ocr_buttons, text="この一覧を再読み込み", command=refresh_ocr).pack(side="left", padx=(0, 6))
    ttk.Button(ocr_buttons, text="選択通知を削除", command=delete_ocr).pack(side="left", padx=6)
    ttk.Label(
        ocr_tab,
        text="内容の編集・OCR再取得は「右上通知を学習」タブで行えます。",
        foreground="#666666",
    ).grid(row=3, column=0, sticky="w", pady=(8, 0))

    # Trivia ------------------------------------------------------------------
    trivia_tab.columnconfigure(0, weight=1)
    trivia_tab.rowconfigure(1, weight=1)
    trivia_status = tk.StringVar()
    ttk.Label(trivia_tab, textvariable=trivia_status).grid(
        row=0, column=0, sticky="w", pady=(0, 6)
    )
    trivia_tree = ttk.Treeview(
        trivia_tab,
        columns=("status","title","body","source"),
        show="headings",
        height=14,
    )
    for key, title, width in (
        ("status","状態",100),
        ("title","タイトル",220),
        ("body","本文",420),
        ("source","情報源",320),
    ):
        trivia_tree.heading(key, text=title)
        trivia_tree.column(key, width=width, stretch=True)
    trivia_tree.grid(row=1, column=0, sticky="nsew")
    trivia_rows = []

    def refresh_trivia() -> None:
        trivia_tree.delete(*trivia_tree.get_children())
        trivia_rows.clear()
        values = training_workspace.trivia.list_latest()
        for index, entry in enumerate(values):
            trivia_rows.append(entry)
            body = entry.text.replace("\n", " ")
            if len(body) > 140:
                body = body[:137] + "..."
            trivia_tree.insert(
                "", "end", iid=str(index),
                values=(
                    TRIVIA_STATUS_JA[entry.status],
                    entry.title,
                    body,
                    "手入力" if entry.source_ref == "manual://owner" else entry.source_ref,
                ),
            )
        candidate = sum(1 for x in values if x.status is TriviaStatus.CANDIDATE)
        verified = sum(1 for x in values if x.status is TriviaStatus.VERIFIED)
        trivia_status.set(
            f"登録={len(values)}件 / 候補={candidate}件 / 確認済み={verified}件"
            if values
            else "実況・豆知識はまだ登録されていません。"
        )

    def selected_trivia():
        selected = trivia_tree.selection()
        if not selected:
            return None
        index = int(selected[0])
        return trivia_rows[index] if 0 <= index < len(trivia_rows) else None

    def verify_trivia() -> None:
        entry = selected_trivia()
        if entry is None:
            return
        if entry.status is TriviaStatus.VERIFIED:
            messagebox.showinfo("実況・豆知識", "この項目は既に確認済みです。")
            return
        if messagebox.askyesno(
            "実況・豆知識を確認済みにする",
            f"「{entry.title}」を確認済みとして正式登録しますか？",
        ):
            training_workspace.trivia.verify(entry.trivia_id)
            refresh_trivia()
            refresh_summary()

    def reject_trivia() -> None:
        entry = selected_trivia()
        if entry is None:
            return
        if messagebox.askyesno(
            "実況・豆知識を却下",
            f"「{entry.title}」を却下しますか？",
        ):
            training_workspace.trivia.reject(entry.trivia_id)
            refresh_trivia()
            refresh_summary()

    trivia_buttons = ttk.Frame(trivia_tab)
    trivia_buttons.grid(row=2, column=0, sticky="w", pady=(8, 0))
    ttk.Button(trivia_buttons, text="この一覧を再読み込み", command=refresh_trivia).pack(side="left", padx=(0, 6))
    ttk.Button(trivia_buttons, text="確認済みにする", command=verify_trivia).pack(side="left", padx=6)
    ttk.Button(trivia_buttons, text="却下", command=reject_trivia).pack(side="left", padx=6)
    ttk.Label(
        trivia_tab,
        text="本文・カテゴリ・関連ゲーム要素の編集は「実況・豆知識を登録」タブで履歴を保持したまま行えます。",
        foreground="#666666",
        wraplength=900,
    ).grid(row=3, column=0, sticky="w", pady=(8, 0))

    # Human Gold / externally supplied human-corrected evidence ---------------
    gold_tab.columnconfigure(0, weight=1)
    gold_tab.rowconfigure(2, weight=1)
    gold_status = tk.StringVar()
    ttk.Label(gold_tab, textvariable=gold_status, wraplength=900).grid(
        row=0, column=0, sticky="w", pady=(0, 8)
    )
    ttk.Label(
        gold_tab,
        text=(
            "Human Goldは、人が別工程で正解確認・修正した外部教師データ/Evidenceを指します。"
            "現時点のTraining StudioにはHuman Goldを新規登録する専用操作はなく、"
            "ワークスペース内の既知のhuman-gold保存場所に置かれたCSV/JSONLを確認するレビュー領域です。"
            "Human Goldの正式な保存契約は今後の専用登録Workflowで定義し、この画面はそれまで外部Evidenceの確認に限定します。"
        ),
        foreground="#555555", wraplength=900,
    ).grid(row=1, column=0, sticky="w", pady=(0, 8))
    gold_tree = ttk.Treeview(
        gold_tab,
        columns=("file","rows"),
        show="headings",
        height=12,
    )
    gold_tree.heading("file", text="検出したHuman Gold / その他ファイル")
    gold_tree.heading("rows", text="行数")
    gold_tree.column("file", width=720, stretch=True)
    gold_tree.column("rows", width=100, stretch=False)
    gold_tree.grid(row=2, column=0, sticky="nsew")

    def refresh_gold() -> None:
        gold_tree.delete(*gold_tree.get_children())
        files = _human_gold_files(Path(training_workspace.root))
        total = 0
        for index, path in enumerate(files):
            rows = _count_rows_in_file(path)
            total += rows
            gold_tree.insert("", "end", iid=str(index), values=(str(path), rows))
        gold_status.set(
            f"Human Gold / その他: {total}件 / {len(files)}ファイル"
            if files
            else (
                "このワークスペースの既知のHuman Gold保存場所には対象ファイルがありません。"
                "Training Studio内の通常登録データとは別系統の外部正解Evidenceです。"
            )
        )

    ttk.Button(gold_tab, text="この一覧を再読み込み", command=refresh_gold).grid(
        row=3, column=0, sticky="w", pady=(8, 0)
    )

    # Unified refresh ----------------------------------------------------------
    def refresh_summary() -> None:
        counts = collect_review_counts(training_workspace)
        summary_vars["game"].set(
            f"{counts.alias_total}件（候補 {counts.alias_candidate} / 確認済み {counts.alias_verified}）"
        )
        summary_vars["visual"].set(f"{counts.visual_total}件")
        summary_vars["ocr"].set(f"{counts.ocr_total}件")
        summary_vars["trivia"].set(
            f"{counts.trivia_total}件（候補 {counts.trivia_candidate} / 確認済み {counts.trivia_verified}）"
        )
        summary_vars["gold"].set(f"{counts.human_gold_total}件")
        summary_vars["total"].set(f"{counts.total_registered}件")

    def refresh_all() -> None:
        refresh_game()
        refresh_visual()
        refresh_ocr()
        refresh_trivia()
        refresh_gold()
        refresh_summary()

    ttk.Button(
        parent,
        text="全タブを再読み込み",
        command=refresh_all,
    ).grid(row=3, column=0, sticky="w", pady=(8, 0))

    def refresh_when_review_tab_changes(_event=None) -> None:
        # Always read canonical stores on review navigation; registration tabs
        # never need to push duplicate state into this review surface.
        refresh_all()

    review_notebook.bind("<<NotebookTabChanged>>", refresh_when_review_tab_changes, add="+")
    refresh_all()
    return refresh_all
