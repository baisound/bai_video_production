"""Windows-friendly DbD Training Studio for single and bulk teacher-data intake."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import time
import threading
import queue
from typing import Sequence

from .canonical_game_event import GameEventType, GameKnowledgeKind
from .dbd_entity_aliases import (
    EntityAliasCatalog, EntityAliasRecord, EntityAliasReviewStatus, EntityAliasType,
)
from .dbd_kamigame_candidate_bridge import (
    index_kamigame_candidates_for_search,
    load_kamigame_candidate_summaries,
    sync_kamigame_review_catalog,
)
from .dbd_game_knowledge_catalog import GameKnowledgeReviewCatalog
from .dbd_map_intelligence import MapIntelligenceStore, MapRecord
from .dbd_video_analysis_workspace import DbDVideoAnalysisWorkspaceService
from .dbd_optional_roi_defaults import ensure_optional_roi_initialized
from .dbd_game_element_selector_ui import open_game_element_selector
from .dbd_training_form_support import (
    ENVIRONMENT_JA,
    EVENT_TYPE_JA,
    FIELD_HELP_JA,
    HUD_VISIBILITY_JA,
    LANGUAGE_JA,
    SOURCE_MODE_MANUAL_JA,
    SOURCE_MODE_URL_JA,
    SOURCE_MODE_VALUES_JA,
    TRIVIA_CATEGORIES,
    VISUAL_TRAINING_DOMAIN_JA,
    TrainingFieldValidationError,
    compose_source_ref,
    hud_visibility_display,
    validate_game_version_range,
    visual_domain_display,
)
from .dbd_perk_knowledge import PerkEnvironment
from .dbd_commentary_knowledge import TriviaSourceKind, TriviaStatus
from .dbd_trivia_operational import format_time_range
from .dbd_data_migration import DbDDataMigrationService
from .dbd_hud_calibration import DBDHudVideoProfileResolver, FFmpegFrameInspector, HudAnchorAligner, HudProfileRegistry
from .dbd_kamigame_collector import KamigameDbDKnowledgeCollector
from .dbd_vision_slices import DBDHudRoiProfile, GrayImage, NormalizedROI, FFmpegSliceExtractor
from .dbd_hud_calibration_editor import ROI_DISPLAY_JA, PixelRect, RoiPixelEditor
from .dbd_training_workspace import (
    DbDTrainingWorkspace,
    OcrVideoCandidate,
    OcrVocabularySample,
    VisualTrainingDomain,
    VisualTrainingSample,
    VisualVideoTrainingRequest,
    default_training_workspace_root,
)
from .dbd_safe_visual_learning import BatchVisualTarget, SafeVisualLearningService
from .dbd_hud_visibility import HudVisibility
from .dbd_training_video_player import (
    TkTrainingMediaPlayer, TkTrainingMediaSession,
)
from .dbd_training_ui_components import ScrollableForm, bind_media_minimum_height
from .dbd_persistent_video_preview import PersistentPreviewFrame, PreviewGeometry
from .dbd_training_diagnostics import get_diagnostic_logger
from .dbd_training_hud_binding import (
    ADDON_SLOT_LABELS,
    PERK_SLOT_LABELS,
    alias_choices,
    resolve_training_hud_profile,
    roi_pixel_rect,
    slot_specifications,
    training_roi,
)
from .dbd_notification_semantics import (
    NotificationSemanticRecord,
    NotificationSemanticStore,
    notification_signal_choices,
)
from .dbd_training_workspace import load_roi_profile, _visual_training_roi
from .dbd_training_studio_foundation_ui import (
    WorkspaceSelectionCancelled,
    build_foundation_tabs,
    choose_workspace_before_launch,
)
from .dbd_training_studio_foundation import resolve_workspace_runtime_profile
from .errors import ProductError
from .dbd_runtime_options import (
    WHISPER_MODEL_OPTIONS_JA, DEVICE_OPTIONS_JA, COMPUTE_OPTIONS_JA,
    display_for_value,
)
from .serialization import canonical_json_bytes, sha256_bytes

VISUAL_GROUP_PRESETS = ("normal", "active", "greyed", "hard-negative")
VISUAL_GROUP_HELP_JA = (
    "通常は normal のままでOK。active=発動中/強調、greyed=無効・グレー表示、"
    "hard-negative=見た目が似るが正解ではない誤認防止画像。"
)


def ensure_csv_templates(root: str | Path) -> tuple[Path, Path, Path, Path]:
    base = Path(root) / "templates"
    base.mkdir(parents=True, exist_ok=True)
    visual = base / "visual-training-template.csv"
    ocr = base / "upper-right-ocr-vocabulary-template.csv"
    trivia = base / "commentary-trivia-template.csv"
    video = base / "video-training-ranges-template.csv"
    if not visual.exists():
        with visual.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f); w.writerow(["domain","label","image_path","group","source_ref","notes"])
            w.writerow(["PERK_ICON","perk_windows_of_opportunity",r"D:\dbd-dataset\perk.png","normal","manual://owner",""])
    if not ocr.exists():
        with ocr.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f); w.writerow(["signal_id","phrase","locale","source_ref"])
            w.writerow(["CHASE","追跡","ja-JP","manual://owner"])
    if not trivia.exists():
        with trivia.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f); w.writerow(["title","text","category","tags","event_types","entity_refs","source_ref","environment","game_version_from","game_version_to","verify"])
            w.writerow(["窓枠の基本","窓枠はチェイスで距離を作る代表的な地形要素です。","BEGINNER","CHASE,WINDOW","WINDOW_VAULT","","manual://owner","LIVE","","","false"])
    if not video.exists():
        with video.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["domain","label","video_path","start_frame","end_frame_exclusive","frame_step","slot","group","source_ref","notes","roi_profile_path","max_samples"])
            w.writerow(["PERK_ICON","perk_windows_of_opportunity",r"D:\dbd-dataset\match.mp4","300","1800","60","0","normal","","sampled from owned recording","","500"])
    return visual, ocr, trivia, video


def launch_training_studio(argv: Sequence[str] | None = None) -> int:
    import argparse
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    parser = argparse.ArgumentParser(description="BAI DbD Training Studio")
    parser.add_argument("--workspace", default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)

    diagnostics = get_diagnostic_logger()
    diagnostics.emit(
        "APP_START",
        executable=sys.executable,
        frozen=bool(getattr(sys, "frozen", False)),
        diagnostics_enabled=diagnostics.enabled,
    )

    try:
        workspace_descriptor = choose_workspace_before_launch(args.workspace)
    except WorkspaceSelectionCancelled:
        return 0

    workspace = DbDTrainingWorkspace(workspace_descriptor.root_path)
    active_runtime = resolve_workspace_runtime_profile(workspace_descriptor)
    runtime_ffmpeg = active_runtime.ffmpeg.effective_path or "ffmpeg"
    runtime_ffprobe = active_runtime.ffprobe.effective_path or "ffprobe"
    runtime_tesseract = active_runtime.tesseract.effective_path or "tesseract"
    runtime_model_cache = active_runtime.faster_whisper_model_cache
    templates = ensure_csv_templates(workspace.root)
    entity_alias_catalog = EntityAliasCatalog(
        workspace.root / "knowledge" / "entity-aliases.sqlite"
    )
    game_knowledge_catalog = GameKnowledgeReviewCatalog(
        workspace.root / "knowledge" / "game-knowledge-review.json"
    )
    map_intelligence_store = MapIntelligenceStore(
        workspace.root / "knowledge" / "map-intelligence.json"
    )
    video_analysis_service = DbDVideoAnalysisWorkspaceService(
        workspace, ffprobe_executable=runtime_ffprobe, ffmpeg_executable=runtime_ffmpeg,
        tesseract_executable=runtime_tesseract, model_cache=runtime_model_cache,
    )
    safe_visual_learning = SafeVisualLearningService(
        workspace_root=workspace.root,
        manifest=workspace.visual,
    )
    notification_semantics = NotificationSemanticStore(
        workspace.root / "knowledge" / "upper-right-notification-semantics.json"
    )

    root = tk.Tk()
    root.title("BAI DbD Training Studio")
    root.geometry("1440x900")
    root.minsize(1180, 760)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(1, weight=1)

    header = ttk.Frame(root, padding=(12, 10, 12, 4))
    header.grid(row=0, column=0, sticky="ew")
    header.columnconfigure(1, weight=1)
    ttk.Label(header, text="現在のワークスペース").grid(row=0, column=0, sticky="w", padx=(0, 8))
    root_var = tk.StringVar(value=f"{workspace_descriptor.display_name} — {workspace.root}")
    ttk.Entry(header, textvariable=root_var, state="readonly").grid(row=0, column=1, sticky="ew")
    ttk.Label(header, text="学習データの保存先はワークスペースごとに管理されます").grid(row=1, column=1, sticky="w", pady=(4, 0))
    if diagnostics.enabled:
        ttk.Label(header, text="診断ログ: ON").grid(
            row=0, column=2, sticky="e", padx=(12, 0)
        )
        ttk.Label(
            header,
            text="diagnostics/latest.jsonl",
        ).grid(row=1, column=2, sticky="e", padx=(12, 0), pady=(4, 0))

    notebook = ttk.Notebook(root)
    notebook.grid(row=1, column=0, sticky="nsew", padx=12, pady=(4, 12))

    intro_tab, runtime_tab, review_tab = build_foundation_tabs(
        notebook,
        workspace=workspace_descriptor,
        training_workspace=workspace,
    )

    status = tk.StringVar(value="準備完了")
    ttk.Label(root, textvariable=status, anchor="w").grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))

    def show_operation_error(
        title: str,
        error_code: str,
        summary_ja: str,
        next_action_ja: str,
        exc: Exception,
    ) -> None:
        cause = exc.__cause__
        diagnostics.exception(
            "TRAINING_OPERATION_FAILED", exc,
            operation_title=title, error_code=error_code,
            cause_type=(type(cause).__name__ if cause is not None else None),
            cause_message=(str(cause)[:500] if cause is not None else None),
        )
        technical = f"{type(exc).__name__}: {exc}"
        if isinstance(exc, ProductError) and exc.details:
            technical += "\n" + " / ".join(
                f"{key}={value}" for key, value in sorted(exc.details.items())
            )
        messagebox.showerror(
            title,
            f"{summary_ja}\n\n"
            f"次にすること:\n{next_action_ja}\n\n"
            f"エラーコード: {error_code}\n\n"
            f"技術詳細:\n{technical}",
        )

    def report_message(title: str, report) -> None:
        lines = [f"登録: {report.accepted}件", f"除外: {report.rejected}件"]
        if report.errors:
            lines += ["", *report.errors[:12]]
            if len(report.errors) > 12:
                lines.append(f"... ほか {len(report.errors)-12}件")
        status.set(f"{title}: 登録={report.accepted} 除外={report.rejected}")
        (messagebox.showinfo if report.rejected == 0 else messagebox.showwarning)(title, "\n".join(lines))

    background_state = {"active": False}

    def run_background(title: str, fn, on_success) -> None:
        """Keep long jobs off Tk; worker threads never call Tk APIs directly."""
        if background_state["active"]:
            messagebox.showwarning(
                "処理を開始できません",
                "別の動画・OCR・音声解析処理を実行中です。完了してからもう一度実行してください。",
            )
            return
        background_state["active"] = True
        status.set(f"{title}: 実行中...")
        outcome: queue.Queue[tuple[str, object]] = queue.Queue(maxsize=1)

        def worker() -> None:
            try:
                outcome.put(("ok", fn()))
            except Exception as exc:
                outcome.put(("error", exc))

        def poll_outcome() -> None:
            try:
                kind, value = outcome.get_nowait()
            except queue.Empty:
                root.after(40, poll_outcome)
                return
            background_state["active"] = False
            if kind == "error":
                exc = value
                status.set(f"{title}: 失敗")
                cause = exc.__cause__
                diagnostics.exception(
                    "BACKGROUND_OPERATION_FAILED", exc,
                    operation_title=title,
                    product_error_code=(exc.code if isinstance(exc, ProductError) else None),
                    product_error_details=(exc.details if isinstance(exc, ProductError) else None),
                    cause_type=(type(cause).__name__ if cause is not None else None),
                    cause_message=(str(cause)[:500] if cause is not None else None),
                )
                detail = f"{type(exc).__name__}: {exc}"
                if isinstance(exc, ProductError):
                    detail = f"{exc.code}: {exc.message}"
                    if exc.details:
                        detail += "\n" + " / ".join(
                            f"{key}={value}" for key, value in sorted(exc.details.items())
                        )
                    if cause is not None:
                        detail += f"\n原因詳細: {type(cause).__name__}: {str(cause)[:500]}"
                messagebox.showerror(
                    title,
                    "処理を完了できませんでした。\n\n"
                    f"原因: {detail}\n\n"
                    "設定内容と実行環境を確認してください。\n"
                    "診断モードONの場合は diagnostics/latest.jsonl に詳細を記録しました。"
                )
                return
            on_success(value)

        threading.Thread(target=worker, name="dbd-training-background", daemon=True).start()
        root.after(40, poll_outcome)

    def choose_hud_profile_candidate(title: str, candidates: Sequence[str]) -> str | None:
        values = tuple(dict.fromkeys(str(item).strip() for item in candidates if str(item).strip()))
        if not values:
            return None
        modal = tk.Toplevel(root)
        modal.title(title)
        modal.transient(root)
        modal.grab_set()
        modal.resizable(False, False)
        result: dict[str, str | None] = {"value": None}
        selected = tk.StringVar(value=values[0])
        ttk.Label(
            modal,
            text=(
                "この動画に一致するHUD設定が複数あります。\n"
                "自動で決めず、今回の学習に使用する設定を選択してください。"
            ),
            justify="left", wraplength=520,
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 8))
        combo = ttk.Combobox(modal, textvariable=selected, values=values, state="readonly", width=46)
        combo.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=8)
        def accept() -> None:
            result["value"] = selected.get().strip() or None
            modal.destroy()
        ttk.Button(modal, text="キャンセル", command=modal.destroy).grid(row=2, column=0, sticky="e", padx=6, pady=(8, 14))
        ttk.Button(modal, text="このHUD設定を使用", command=accept).grid(row=2, column=1, sticky="w", padx=6, pady=(8, 14))
        modal.protocol("WM_DELETE_WINDOW", modal.destroy)
        root.wait_window(modal)
        return result["value"]

    def resolve_workflow_hud_profile(
        *,
        title: str,
        video_path: str,
        profile_var,
        frame_index: int,
        inspector: FFmpegFrameInspector,
    ):
        manual = profile_var.get().strip()
        try:
            return resolve_training_hud_profile(
                video_path=video_path, registry_root=workspace.root / "hud_profiles",
                manual_profile_path=manual or None, frame_index=frame_index, inspector=inspector,
            )
        except ProductError as exc:
            if manual or exc.code != "ERR_DBD_HUD_PROFILE_AMBIGUOUS":
                raise
            candidates = tuple(exc.details.get("candidates") or ())
            chosen = choose_hud_profile_candidate(title, candidates)
            if not chosen:
                raise ProductError(
                    "ERR_DBD_HUD_PROFILE_SELECTION_CANCELLED",
                    "HUD profile selection was cancelled",
                    exc.category,
                    details={"candidates": list(candidates)},
                ) from exc
            registry = HudProfileRegistry(workspace.root / "hud_profiles")
            profile_path = registry.profile_directory(chosen) / "profile.json"
            if not profile_path.is_file():
                raise ValueError("選択したHUD設定のprofile.jsonが見つかりません。")
            profile_var.set(str(profile_path.resolve()))
            diagnostics.emit(
                "HUD_PROFILE_DISAMBIGUATED",
                workflow=title, selected_profile=chosen, candidate_count=len(candidates),
            )
            return resolve_training_hud_profile(
                video_path=video_path, registry_root=workspace.root / "hud_profiles",
                manual_profile_path=str(profile_path), frame_index=frame_index, inspector=inspector,
            )

    # ---- Video batch learning tab --------------------------------------------
    # R7I: form controls are bounded to the upper half and scroll independently;
    # the lower half is the canonical media player so the full video remains
    # visible while the operator chooses exact learning frames.
    video_tab = ttk.Frame(notebook)
    notebook.add(video_tab, text="動画から一括学習")
    video_tab.columnconfigure(0, weight=1)
    video_tab.rowconfigure(0, weight=1)
    video_paned = ttk.Panedwindow(video_tab, orient="vertical")
    video_paned.grid(row=0, column=0, sticky="nsew")
    video_form_host = ttk.Frame(video_paned)
    video_form_host.columnconfigure(0, weight=1)
    video_form_host.rowconfigure(0, weight=1)
    video_media_host = ttk.Frame(video_paned, padding=8)
    video_media_host.columnconfigure(0, weight=1)
    video_media_host.rowconfigure(0, weight=1)
    video_paned.add(video_form_host, weight=1)
    video_paned.add(video_media_host, weight=1)
    video_scroll = ScrollableForm(video_form_host, padding=12)
    video_scroll.grid(row=0, column=0, sticky="nsew")
    video_form = video_scroll.inner
    video_form.columnconfigure(0, weight=1)
    video_form.columnconfigure(1, weight=1)

    bind_media_minimum_height(
        video_paned, media_first=False, minimum_fraction=0.55, minimum_pixels=400
    )

    video_vars = {
        "video": tk.StringVar(),
        "roi_profile": tk.StringVar(),
        "domain": tk.StringVar(value=VisualTrainingDomain.PERK_ICON.value),
        "group": tk.StringVar(value="normal"),
        "start": tk.StringVar(value="0"),
        "end": tk.StringVar(value="300"),
        "step": tk.StringVar(value="30"),
        "max_samples": tk.StringVar(value="500"),
        "ffmpeg": tk.StringVar(value=runtime_ffmpeg),
    }

    video_profile_binding = {"value": None}
    video_profile_status = tk.StringVar(
        value="使用中HUD設定: 動画と保存済みHUD設定から自動判定します。"
    )
    video_slot_rows: list[dict[str, object]] = []
    staged_video_samples: list[object] = []
    crop_preview_photos: list[object] = []
    crop_preview_widgets: list[object] = []

    # First tier is a real two-column layout: source/targets on the left and
    # extraction conditions/advanced HUD binding on the right. The entire tier
    # scrolls while the lower shared-media pane retains at least half the view.
    video_columns = ttk.Frame(video_form)
    video_columns.grid(row=0, column=0, columnspan=3, sticky="nsew")
    video_columns.columnconfigure(0, weight=1, uniform="video-batch")
    video_columns.columnconfigure(1, weight=1, uniform="video-batch")
    video_source_box = ttk.LabelFrame(video_columns, text="学習元と学習対象", padding=8)
    video_source_box.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    video_source_box.columnconfigure(1, weight=1)
    video_condition_box = ttk.LabelFrame(video_columns, text="学習条件", padding=8)
    video_condition_box.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    video_condition_box.columnconfigure(1, weight=1)

    ttk.Label(video_source_box, text="学習元動画（必須）").grid(row=0, column=0, sticky="w", pady=3)
    ttk.Entry(video_source_box, textvariable=video_vars["video"]).grid(row=0, column=1, sticky="ew", pady=3)

    def choose_video() -> None:
        chosen = filedialog.askopenfilename(
            title="学習元のDbD動画を選択",
            filetypes=[("Video","*.mp4 *.mkv *.mov *.avi *.webm"),("All files","*.*")],
        )
        if chosen:
            video_vars["video"].set(chosen)
            video_profile_binding["value"] = None
            video_profile_status.set(
                "使用中HUD設定: 次のプレビュー時に自動判定します。"
            )

    ttk.Button(video_source_box, text="参照", command=choose_video).grid(row=0, column=2, padx=(8,0))

    ttk.Label(video_condition_box, text="詳細設定：HUDプロファイルJSON（任意）").grid(
        row=2, column=0, sticky="w", pady=3
    )
    ttk.Entry(video_condition_box, textvariable=video_vars["roi_profile"]).grid(
        row=2, column=1, sticky="ew", pady=3
    )

    def choose_roi_profile() -> None:
        chosen = filedialog.askopenfilename(
            title="HUDプロファイルJSONを選択",
            filetypes=[("JSON","*.json"),("All files","*.*")],
        )
        if chosen:
            video_vars["roi_profile"].set(chosen)
            video_profile_binding["value"] = None
            video_profile_status.set(
                "使用中HUD設定: 手動指定を互換性確認してから使用します。"
            )

    ttk.Button(video_condition_box, text="参照", command=choose_roi_profile).grid(
        row=2, column=2, padx=(8,0)
    )
    ttk.Label(video_condition_box, textvariable=video_profile_status, wraplength=460).grid(
        row=3, column=0, columnspan=3, sticky="w", pady=(0,6)
    )

    ttk.Label(video_source_box, text="学習対象").grid(row=1, column=0, sticky="w", pady=3)
    video_domain_display = tk.StringVar(
        value=visual_domain_display(video_vars["domain"].get())
    )
    video_domain_reverse = {
        label: internal for internal, label in VISUAL_TRAINING_DOMAIN_JA.items()
    }
    video_domain_combo = ttk.Combobox(
        video_source_box,
        textvariable=video_domain_display,
        values=list(video_domain_reverse),
        state="readonly",
    )
    video_domain_combo.grid(row=1, column=1, columnspan=2, sticky="ew", pady=3)

    slot_frame = ttk.LabelFrame(
        video_source_box,
        text="学習スロットと正解ゲーム要素（候補はKnowledge/Aliasから表示）",
        padding=8,
    )
    slot_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(6,6))
    slot_frame.columnconfigure(1, weight=1)

    kind_map = {
        VisualTrainingDomain.PERK_ICON: GameKnowledgeKind.PERK,
        VisualTrainingDomain.ITEM_ICON: GameKnowledgeKind.ITEM,
        VisualTrainingDomain.ADDON_ICON: GameKnowledgeKind.ADDON,
        VisualTrainingDomain.KILLER_POWER: GameKnowledgeKind.POWER,
    }

    def clear_slot_frame() -> None:
        for child in slot_frame.winfo_children():
            child.destroy()
        video_slot_rows.clear()

    def set_slot_choice(row_state: dict[str, object], selected) -> None:
        row_state["entity_id"].set(selected.entity_id)
        row_state["display"].set(
            f"{selected.matched_text}  [{selected.entity_id}]"
        )

    def open_slot_search(row_state: dict[str, object], expected_kind) -> None:
        def selected(row) -> None:
            set_slot_choice(row_state, row)
        open_game_element_selector(
            root,
            catalog=entity_alias_catalog,
            title="学習するゲーム要素を選択",
            on_select=selected,
            expected_kind=expected_kind,
            verified_only=True,
        )

    def rebuild_video_slot_rows(_event=None) -> None:
        internal = video_domain_reverse.get(video_domain_display.get())
        if internal:
            video_vars["domain"].set(internal)
        domain = VisualTrainingDomain(video_vars["domain"].get())
        clear_slot_frame()
        specs = slot_specifications(domain)
        expected_kind = kind_map.get(domain)
        choices = (
            alias_choices(entity_alias_catalog, knowledge_kind=expected_kind)
            if expected_kind is not None
            else ()
        )
        display_to_choice = {choice.display_text: choice for choice in choices}

        for row_no, (slot, slot_label) in enumerate(specs):
            ttk.Label(slot_frame, text=slot_label).grid(
                row=row_no, column=0, sticky="w", padx=(0,8), pady=3
            )
            display_var = tk.StringVar()
            entity_id_var = tk.StringVar()

            row_state = {
                "slot": slot,
                "slot_label": slot_label,
                "display": display_var,
                "entity_id": entity_id_var,
            }
            video_slot_rows.append(row_state)

            if expected_kind is not None:
                combo = ttk.Combobox(
                    slot_frame,
                    textvariable=display_var,
                    values=list(display_to_choice),
                    state="readonly",
                )
                combo.grid(row=row_no, column=1, sticky="ew", pady=3)

                def sync_choice(_evt=None, rs=row_state, mapping=display_to_choice):
                    choice = mapping.get(rs["display"].get())
                    if choice is not None:
                        rs["entity_id"].set(choice.entity_id)

                combo.bind("<<ComboboxSelected>>", sync_choice)
                ttk.Button(
                    slot_frame,
                    text="検索",
                    command=lambda rs=row_state, kind=expected_kind: open_slot_search(rs, kind),
                ).grid(row=row_no, column=2, padx=(8,0))
            else:
                # SURVIVOR_HUD has no GameKnowledgeKind mapping. Keep a bounded
                # label field for compatibility with the existing visual manifest.
                ttk.Entry(
                    slot_frame,
                    textvariable=entity_id_var,
                ).grid(row=row_no, column=1, sticky="ew", pady=3)
                ttk.Label(
                    slot_frame,
                    text="例: survivor_slot",
                ).grid(row=row_no, column=2, sticky="w", padx=(8,0))

        if expected_kind is not None and not choices:
            ttk.Label(
                slot_frame,
                text="Knowledge/Alias候補がありません。先にゲーム情報を取得・検索用インデックスへ反映してください。",
            ).grid(row=len(specs), column=0, columnspan=3, sticky="w", pady=(6,0))

    video_domain_combo.bind("<<ComboboxSelected>>", rebuild_video_slot_rows)
    rebuild_video_slot_rows()

    video_visibility = tk.StringVar(value=HudVisibility.VISIBLE.value)
    video_visibility_display = tk.StringVar(
        value=hud_visibility_display(video_visibility.get())
    )
    video_visibility_reverse = {
        label: internal for internal, label in HUD_VISIBILITY_JA.items()
    }
    ttk.Label(video_condition_box, text="表示状態").grid(row=0, column=0, sticky="w", pady=3)
    video_visibility_combo = ttk.Combobox(
        video_condition_box,
        textvariable=video_visibility_display,
        values=list(video_visibility_reverse),
        state="readonly",
    )
    video_visibility_combo.grid(row=0, column=1, columnspan=2, sticky="ew", pady=3)

    def sync_video_visibility(_event=None) -> None:
        internal = video_visibility_reverse.get(video_visibility_display.get())
        if internal:
            video_visibility.set(internal)

    video_visibility_combo.bind("<<ComboboxSelected>>", sync_video_visibility)

    ttk.Label(video_condition_box, text="画像グループ").grid(row=1, column=0, sticky="w", pady=3)
    ttk.Combobox(
        video_condition_box, textvariable=video_vars["group"],
        values=VISUAL_GROUP_PRESETS, state="normal",
    ).grid(row=1, column=1, columnspan=2, sticky="ew", pady=3)
    ttk.Label(
        video_condition_box, text=VISUAL_GROUP_HELP_JA, wraplength=520,
    ).grid(row=2, column=1, columnspan=2, sticky="w", pady=(0, 4))

    range_frame = ttk.Frame(video_condition_box)
    range_frame.grid(row=4, column=1, columnspan=2, sticky="ew", pady=3)
    for idx in range(4):
        range_frame.columnconfigure(idx, weight=1)
    ttk.Label(video_condition_box, text="フレーム抽出範囲").grid(
        row=4, column=0, sticky="w", pady=3
    )
    ttk.Entry(range_frame, textvariable=video_vars["start"], width=10).grid(
        row=0,column=0,sticky="ew",padx=(0,4)
    )
    ttk.Entry(range_frame, textvariable=video_vars["end"], width=10).grid(
        row=0,column=1,sticky="ew",padx=4
    )
    ttk.Entry(range_frame, textvariable=video_vars["step"], width=10).grid(
        row=0,column=2,sticky="ew",padx=4
    )
    ttk.Entry(range_frame, textvariable=video_vars["max_samples"], width=10).grid(
        row=0,column=3,sticky="ew",padx=(4,0)
    )
    ttk.Label(
        range_frame,
        text="開始 / 終了（含まない） / 間隔 / 最大件数",
        anchor="center",
    ).grid(row=1,column=0,columnspan=4,sticky="ew")

    video_learning_result = tk.StringVar(
        value="手順: 動画を選択 → HUD設定を自動判定 → 各スロットの正解を選択 → Crop確認 → 一括登録"
    )
    ttk.Label(
        video_form,
        textvariable=video_learning_result,
        wraplength=900,
    ).grid(row=1,column=0,columnspan=3,sticky="w",pady=(8,4))

    # Canonical shared playback UI. Exact crop/profile resolution still uses
    # FFmpegFrameInspector below; preview playback never becomes training evidence.
    video_transport_inspector = FFmpegFrameInspector(ffmpeg_executable=runtime_ffmpeg, ffprobe_executable=runtime_ffprobe)
    video_learning_player = TkTrainingMediaPlayer(
        video_media_host,
        root=root,
        source_getter=lambda: video_vars["video"].get(),
        frame_getter=lambda: int(video_vars["start"].get() or "0"),
        frame_setter=lambda value: video_vars["start"].set(str(value)),
        status_setter=status.set,
        ffprobe_executable=runtime_ffprobe,
        diagnostics=diagnostics,
        diagnostic_feature="VIDEO_LEARNING",
        player_id="video-learning-player",
    )
    video_learning_player.grid(row=0, column=0, sticky="nsew")

    crop_preview_frame = ttk.LabelFrame(
        video_form,
        text="複数Cropプレビュー",
        padding=6,
    )
    crop_preview_frame.grid(
        row=2, column=0, columnspan=3, sticky="ew", pady=(6,6)
    )
    crop_preview_frame.columnconfigure(0, weight=1)

    def clear_crop_previews() -> None:
        for widget in crop_preview_widgets:
            try:
                widget.destroy()
            except Exception:
                pass
        crop_preview_widgets.clear()
        crop_preview_photos.clear()

    def active_slot_selections() -> list[tuple[int | None, str, str]]:
        selections = []
        for row_state in video_slot_rows:
            entity_id = row_state["entity_id"].get().strip()
            if entity_id:
                selections.append(
                    (
                        row_state["slot"],
                        row_state["slot_label"],
                        entity_id,
                    )
                )
        return selections

    def resolve_active_profile():
        source = video_vars["video"].get().strip()
        if not source:
            raise ValueError("先に学習元動画を選択してください。")
        binding = resolve_workflow_hud_profile(
            title="動画から一括学習",
            video_path=source,
            profile_var=video_vars["roi_profile"],
            frame_index=int(video_vars["start"].get() or "0"),
            inspector=video_transport_inspector,
        )
        video_profile_binding["value"] = binding
        mode_ja = "自動判定" if binding.mode == "AUTO" else "詳細指定"
        video_profile_status.set(
            "使用中HUD設定: "
            f"{binding.profile.profile_id} / v{binding.profile.profile_version} / "
            f"{binding.source_width}x{binding.source_height} / "
            f"{mode_ja} / score={binding.score_milli}"
        )
        return binding

    def discard_staged_video_samples() -> None:
        for staged in tuple(staged_video_samples):
            try:
                safe_visual_learning.discard(staged.staging_id)
            except Exception:
                pass
        staged_video_samples.clear()
        clear_crop_previews()

    def preview_video_learning() -> None:
        source = video_vars["video"].get().strip()
        if not source:
            messagebox.showwarning(
                "動画から一括学習",
                "先に学習元動画を選択してください。",
            )
            return
        selections = active_slot_selections()
        if not selections:
            messagebox.showwarning(
                "動画から一括学習",
                "登録するスロットのゲーム要素を1件以上選択してください。",
            )
            return

        try:
            start_frame = int(video_vars["start"].get())
            end_frame = int(video_vars["end"].get())
            frame_step = int(video_vars["step"].get())
            max_samples = int(video_vars["max_samples"].get())
            binding = resolve_active_profile()
            domain = VisualTrainingDomain(video_vars["domain"].get())
            group = video_vars["group"].get().strip() or "normal"
            visibility = HudVisibility(video_visibility.get())
            targets: list[BatchVisualTarget] = []
            target_labels: dict[str, str] = {}
            for slot, slot_label, entity_id in selections:
                roi = training_roi(binding.profile, domain, slot)
                rect = roi_pixel_rect(
                    binding.profile, domain=domain, slot=slot,
                    source_width=binding.source_width,
                    source_height=binding.source_height,
                )
                target_labels[roi.roi_id] = slot_label
                targets.append(
                    BatchVisualTarget(
                        domain=domain, label=entity_id, visibility=visibility, roi=roi,
                        group=group, notes=(
                            f"hud_profile={binding.profile.profile_id} "
                            f"roi={roi.roi_id} "
                            f"pixel={rect.x},{rect.y},{rect.width},{rect.height}"
                        ),
                    )
                )
        except Exception as exc:
            show_operation_error(
                "動画から一括学習", "ERR_DBD_VIDEO_BATCH_PREPARE",
                "一括学習の条件を準備できませんでした。",
                "動画、HUD設定、フレーム抽出範囲、最大件数を確認してください。", exc,
            )
            return

        discard_staged_video_samples()
        video_learning_result.set("指定範囲から正確なCrop候補を作成中です…")

        def completed(report) -> None:
            staged_video_samples.extend(report.staged)
            clear_crop_previews()
            preview_limit = 12
            for preview_row, staged in enumerate(report.staged[:preview_limit]):
                photo = tk.PhotoImage(file=staged.image_path)
                crop_preview_photos.append(photo)
                slot_label = target_labels.get(staged.roi_id, staged.roi_id)
                label = ttk.Label(
                    crop_preview_frame, image=photo,
                    text=(
                        f"frame={staged.source_frame} / {slot_label} / {staged.label}\n"
                        f"{staged.roi_id}"
                    ),
                    compound="top", anchor="center",
                )
                label.grid(
                    row=preview_row // 2, column=preview_row % 2,
                    sticky="nsew", padx=6, pady=6,
                )
                crop_preview_widgets.append(label)
            if report.total_samples > preview_limit:
                summary = ttk.Label(
                    crop_preview_frame,
                    text=(
                        f"全{report.total_samples}件中、先頭{preview_limit}件を表示しています。"
                        "登録前の正確なCropはすべてstagingに保持されています。"
                    ),
                    wraplength=760,
                )
                summary.grid(
                    row=(preview_limit + 1) // 2, column=0, columnspan=2,
                    sticky="w", padx=6, pady=6,
                )
                crop_preview_widgets.append(summary)
            video_learning_result.set(
                f"{report.frame_count}フレーム × {report.target_count}対象 = "
                f"{report.total_samples}件のCrop候補を作成しました。"
                "確認してから一括登録してください。"
            )
            status.set("動画から一括学習: 範囲Crop登録前プレビュー")

        run_background(
            "動画から一括学習",
            lambda: safe_visual_learning.preview_video_batch(
                video_path=source, start_frame=start_frame,
                end_frame_exclusive=end_frame, frame_step=frame_step,
                targets=tuple(targets), max_samples=max_samples,
            ),
            completed,
        )

    def confirm_video_learning() -> None:
        if not staged_video_samples:
            messagebox.showinfo(
                "動画から一括学習",
                "先に複数Cropプレビューを作成してください。",
            )
            return

        summary = "\n".join(
            f"- {item.roi_id}: {item.label}"
            for item in staged_video_samples
        )
        if not messagebox.askyesno(
            "学習データへ一括登録",
            f"この{len(staged_video_samples)}件のCropを登録しますか？\n\n{summary}",
        ):
            return

        accepted = duplicates = failed = 0
        failures = []
        for staged in tuple(staged_video_samples):
            try:
                if safe_visual_learning.confirm_register(staged):
                    accepted += 1
                else:
                    duplicates += 1
            except Exception as exc:
                failed += 1
                failures.append(
                    f"{staged.roi_id}: {type(exc).__name__}: {exc}"
                )

        staged_video_samples.clear()
        clear_crop_previews()
        refresh_visual_count()

        message = (
            f"登録={accepted}件 / 重複={duplicates}件 / 失敗={failed}件"
        )
        if failures:
            message += "\n\n" + "\n".join(failures[:10])
        (messagebox.showinfo if failed == 0 else messagebox.showwarning)(
            "動画から一括学習",
            message,
        )

    def import_video_ranges_csv() -> None:
        chosen = filedialog.askopenfilename(
            title="動画学習範囲CSVを選択",
            filetypes=[("CSV","*.csv"),("All files","*.*")],
        )
        if not chosen:
            return
        domain = VisualTrainingDomain(video_vars["domain"].get())
        run_background(
            "動画範囲CSV",
            lambda: workspace.import_video_training_csv(
                chosen,
                default_domain=domain,
                ffmpeg_executable=video_vars["ffmpeg"].get().strip() or "ffmpeg",
            ),
            lambda report: (
                report_message("動画範囲CSV", report),
                refresh_visual_count(),
            ),
        )

    video_buttons = ttk.Frame(video_form)
    video_buttons.grid(row=12,column=1,sticky="w",pady=8)
    ttk.Button(
        video_buttons,
        text="1. 全スロットのCropを確認",
        command=preview_video_learning,
    ).pack(side="left",padx=(0,6))
    ttk.Button(
        video_buttons,
        text="2. 確認したCropを一括登録",
        command=confirm_video_learning,
    ).pack(side="left",padx=6)
    ttk.Button(
        video_buttons,
        text="破棄",
        command=discard_staged_video_samples,
    ).pack(side="left",padx=6)

    ttk.Label(
        video_form,
        text=f"動画範囲CSVテンプレート: {templates[3]}",
        wraplength=900,
    ).grid(row=13,column=1,sticky="w",pady=(4,12))

    # ---- Image training data -------------------------------------------------
    visual_tab = ttk.Frame(notebook, padding=8)
    notebook.add(visual_tab, text="画像学習データ")
    visual_tab.columnconfigure(0, weight=1)
    visual_tab.rowconfigure(0, weight=1)

    visual_notebook = ttk.Notebook(visual_tab)
    visual_notebook.grid(row=0, column=0, sticky="nsew")
    visual_video_tab = ttk.Frame(visual_notebook)
    visual_manual_tab = ttk.Frame(visual_notebook, padding=12)
    visual_list_tab = ttk.Frame(visual_notebook, padding=12)
    visual_notebook.add(visual_video_tab, text="動画から登録")
    visual_notebook.add(visual_manual_tab, text="手動で登録")
    visual_notebook.add(visual_list_tab, text="登録済み一覧")

    visual_vars = {
        "domain": tk.StringVar(value=VisualTrainingDomain.PERK_ICON.value),
        "label": tk.StringVar(), "group": tk.StringVar(value="normal"),
        "video": tk.StringVar(), "frame": tk.StringVar(value="0"),
        "roi_profile": tk.StringVar(), "image": tk.StringVar(),
        "display_state": tk.StringVar(value=HudVisibility.VISIBLE.value),
        "selected_slot": tk.StringVar(),
    }
    visual_kind_map = {
        VisualTrainingDomain.PERK_ICON: GameKnowledgeKind.PERK,
        VisualTrainingDomain.ITEM_ICON: GameKnowledgeKind.ITEM,
        VisualTrainingDomain.ADDON_ICON: GameKnowledgeKind.ADDON,
    }
    visual_domain_labels = {
        "パーク": VisualTrainingDomain.PERK_ICON,
        "アイテム": VisualTrainingDomain.ITEM_ICON,
        "アドオン": VisualTrainingDomain.ADDON_ICON,
    }
    visual_domain_display_var = tk.StringVar(value="パーク")
    visual_slot_values: dict[int | None, dict[str, object]] = {}
    visual_source_mode = tk.StringVar(value=SOURCE_MODE_MANUAL_JA)
    visual_source_url = tk.StringVar()
    visual_crop_photo = {"value": None}
    visual_staged = {"value": None}
    visual_inspector = FFmpegFrameInspector(ffmpeg_executable=runtime_ffmpeg, ffprobe_executable=runtime_ffprobe)

    def visual_selected_domain() -> VisualTrainingDomain:
        return visual_domain_labels[visual_domain_display_var.get()]

    def choose_visual_video() -> None:
        chosen = filedialog.askopenfilename(
            title="学習元のDbD動画を選択",
            filetypes=[("Video", "*.mp4 *.mkv *.mov *.avi *.webm"), ("All files", "*.*")],
        )
        if chosen:
            visual_vars["video"].set(chosen)

    def choose_visual_profile() -> None:
        chosen = filedialog.askopenfilename(
            title="HUDプロファイルJSONを選択",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if chosen:
            visual_vars["roi_profile"].set(chosen)

    # Media-first upper half. The shared player owns the same 12 transport
    # actions, fit-to-view preview and audible 1x playback used everywhere.
    visual_video_tab.columnconfigure(0, weight=1)
    visual_video_tab.rowconfigure(0, weight=1)
    visual_video_paned = ttk.Panedwindow(visual_video_tab, orient="vertical")
    visual_video_paned.grid(row=0, column=0, sticky="nsew")
    visual_media_host = ttk.Frame(visual_video_paned, padding=8)
    visual_media_host.columnconfigure(0, weight=1)
    visual_media_host.rowconfigure(0, weight=1)
    visual_form_host = ttk.Frame(visual_video_paned)
    visual_form_host.columnconfigure(0, weight=1)
    visual_form_host.rowconfigure(0, weight=1)
    visual_video_paned.add(visual_media_host, weight=1)
    visual_video_paned.add(visual_form_host, weight=1)
    bind_media_minimum_height(
        visual_video_paned, media_first=True, minimum_fraction=0.6, minimum_pixels=420
    )

    def visual_media_header(parent) -> None:
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text="学習元動画（必須）").grid(row=0, column=0, sticky="w")
        ttk.Entry(parent, textvariable=visual_vars["video"]).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(parent, text="参照", command=choose_visual_video).grid(row=0, column=2)
        ttk.Label(parent, text="詳細設定：HUDプロファイルJSON（任意）").grid(row=1, column=0, sticky="w", pady=(4,0))
        ttk.Entry(parent, textvariable=visual_vars["roi_profile"]).grid(row=1, column=1, sticky="ew", padx=4, pady=(4,0))
        ttk.Button(parent, text="参照", command=choose_visual_profile).grid(row=1, column=2, pady=(4,0))

    visual_player = TkTrainingMediaPlayer(
        visual_media_host, root=root,
        source_getter=lambda: visual_vars["video"].get(),
        frame_getter=lambda: int(visual_vars["frame"].get() or "0"),
        frame_setter=lambda value: visual_vars["frame"].set(str(value)),
        status_setter=status.set, ffprobe_executable=runtime_ffprobe, diagnostics=diagnostics,
        diagnostic_feature="VISUAL_REGISTRATION", player_id="visual-registration-player",
        control_header_builder=visual_media_header,
    )
    visual_player.grid(row=0, column=0, sticky="nsew")

    visual_scroll = ScrollableForm(visual_form_host, padding=12)
    visual_scroll.grid(row=0, column=0, sticky="nsew")
    visual_form = visual_scroll.inner
    visual_form.columnconfigure(0, weight=1)
    visual_form.columnconfigure(1, weight=1)

    target_box = ttk.LabelFrame(visual_form, text="学習対象と正解ゲーム要素", padding=8)
    target_box.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 6))
    target_box.columnconfigure(1, weight=1)
    options_box = ttk.LabelFrame(visual_form, text="登録条件", padding=8)
    options_box.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 6))
    options_box.columnconfigure(1, weight=1)

    ttk.Label(target_box, text="学習対象").grid(row=0, column=0, sticky="w")
    ttk.Combobox(
        target_box, textvariable=visual_domain_display_var,
        values=list(visual_domain_labels), state="readonly",
    ).grid(row=0, column=1, sticky="ew", pady=3)
    slot_host = ttk.Frame(target_box)
    slot_host.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(6, 0))
    slot_host.columnconfigure(1, weight=1)

    def set_visual_slot(slot: int | None, entity_id: str, display_text: str) -> None:
        row = visual_slot_values[slot]
        row["entity_id"].set(entity_id)
        row["display"].set(display_text)
        visual_vars["selected_slot"].set("" if slot is None else str(slot))
        visual_vars["label"].set(entity_id)
        for current_slot, current in visual_slot_values.items():
            current["selected"].set(current_slot == slot)

    def open_visual_slot_search(slot: int | None) -> None:
        domain = visual_selected_domain()
        expected_kind = visual_kind_map[domain]
        def selected(choice) -> None:
            set_visual_slot(slot, choice.entity_id, f"{choice.matched_text}  [{choice.entity_id}]")
        open_game_element_selector(
            root, catalog=entity_alias_catalog,
            title="正解ゲーム要素を選択", on_select=selected,
            expected_kind=expected_kind, verified_only=True,
        )

    def rebuild_visual_slots(_event=None) -> None:
        visual_vars["domain"].set(visual_selected_domain().value)
        for child in slot_host.winfo_children():
            child.destroy()
        visual_slot_values.clear()
        specs = slot_specifications(visual_selected_domain())
        for row_no, (slot, label) in enumerate(specs):
            display = tk.StringVar()
            entity_id = tk.StringVar()
            selected = tk.BooleanVar(value=False)
            visual_slot_values[slot] = {
                "display": display, "entity_id": entity_id, "selected": selected,
            }
            ttk.Radiobutton(
                slot_host, text=label, variable=visual_vars["selected_slot"],
                value="" if slot is None else str(slot),
                command=lambda sl=slot: visual_vars["label"].set(
                    str(visual_slot_values[sl]["entity_id"].get())
                ),
            ).grid(row=row_no, column=0, sticky="w", pady=3)
            ttk.Entry(slot_host, textvariable=display, state="readonly").grid(
                row=row_no, column=1, sticky="ew", padx=4, pady=3
            )
            ttk.Button(
                slot_host, text="検索",
                command=lambda sl=slot: open_visual_slot_search(sl),
            ).grid(row=row_no, column=2, pady=3)
        if specs:
            first_slot = specs[0][0]
            visual_vars["selected_slot"].set("" if first_slot is None else str(first_slot))

    visual_domain_display_var.trace_add("write", lambda *_args: rebuild_visual_slots())
    rebuild_visual_slots()

    ttk.Label(options_box, text="表示状態").grid(row=0, column=0, sticky="w", pady=3)
    visual_visibility_display = tk.StringVar(value=hud_visibility_display(HudVisibility.VISIBLE.value))
    visual_visibility_reverse = {label: internal for internal, label in HUD_VISIBILITY_JA.items()}
    ttk.Combobox(
        options_box, textvariable=visual_visibility_display,
        values=list(visual_visibility_reverse), state="readonly",
    ).grid(row=0, column=1, sticky="ew", pady=3)
    ttk.Label(options_box, text="画像グループ").grid(row=1, column=0, sticky="w", pady=3)
    ttk.Combobox(
        options_box, textvariable=visual_vars["group"],
        values=VISUAL_GROUP_PRESETS, state="normal",
    ).grid(row=1, column=1, sticky="ew", pady=3)
    ttk.Label(options_box, text=VISUAL_GROUP_HELP_JA, wraplength=420).grid(
        row=2, column=1, sticky="w", pady=(0, 4)
    )
    ttk.Label(options_box, text="情報源").grid(row=3, column=0, sticky="w", pady=3)
    visual_source_row = ttk.Frame(options_box)
    visual_source_row.grid(row=3, column=1, sticky="ew")
    visual_source_row.columnconfigure(2, weight=1)
    visual_source_url_entry = ttk.Entry(visual_source_row, textvariable=visual_source_url, state="disabled")
    def sync_visual_source() -> None:
        visual_source_url_entry.configure(state="normal" if visual_source_mode.get() == SOURCE_MODE_URL_JA else "disabled")
    ttk.Radiobutton(visual_source_row, text=SOURCE_MODE_MANUAL_JA, variable=visual_source_mode, value=SOURCE_MODE_MANUAL_JA, command=sync_visual_source).grid(row=0, column=0)
    ttk.Radiobutton(visual_source_row, text=SOURCE_MODE_URL_JA, variable=visual_source_mode, value=SOURCE_MODE_URL_JA, command=sync_visual_source).grid(row=0, column=1)
    visual_source_url_entry.grid(row=0, column=2, sticky="ew", padx=(4, 0))
    ttk.Label(options_box, text="メモ").grid(row=4, column=0, sticky="nw", pady=3)
    visual_notes = tk.Text(options_box, height=4, wrap="word")
    visual_notes.grid(row=4, column=1, sticky="ew", pady=3)

    preview_box = ttk.LabelFrame(visual_form, text="正確なCrop確認", padding=8)
    preview_box.grid(row=1, column=0, columnspan=2, sticky="ew", pady=6)
    preview_box.columnconfigure(0, weight=1)
    visual_crop = ttk.Label(preview_box, text="現在フレームから正確なCropを確認してください。", anchor="center")
    visual_crop.grid(row=0, column=0, sticky="ew")
    visual_profile_status = tk.StringVar(value="HUD設定は動画から自動判定します。")
    ttk.Label(preview_box, textvariable=visual_profile_status).grid(row=1, column=0, sticky="w", pady=(4, 0))

    def selected_visual_slot() -> int | None:
        raw = visual_vars["selected_slot"].get()
        return None if raw == "" else int(raw)

    def preview_visual_from_video() -> None:
        label = visual_vars["label"].get().strip()
        if not label:
            messagebox.showwarning("画像学習データ", "検索ボタンから正解ゲーム要素を選択してください。")
            return
        try:
            source = visual_vars["video"].get().strip()
            frame_index = int(visual_vars["frame"].get() or "0")
            binding = resolve_workflow_hud_profile(
                title="画像学習データ", video_path=source,
                profile_var=visual_vars["roi_profile"],
                frame_index=frame_index, inspector=visual_inspector,
            )
            domain = visual_selected_domain()
            slot = selected_visual_slot()
            roi = training_roi(binding.profile, domain, slot)
            rect = roi_pixel_rect(
                binding.profile, domain=domain, slot=slot,
                source_width=binding.source_width, source_height=binding.source_height,
            )
            visibility = HudVisibility(
                visual_visibility_reverse.get(visual_visibility_display.get(), HudVisibility.VISIBLE.value)
            )
            staged = safe_visual_learning.preview_video_frame(
                domain=domain, label=label, visibility=visibility,
                video_path=source, frame_index=frame_index, roi=roi,
                group=visual_vars["group"].get().strip() or "normal",
                notes=visual_notes.get("1.0", "end").strip(),
                registration_origin="VIDEO_SINGLE",
            )
            visual_staged["value"] = staged
            photo = tk.PhotoImage(file=staged.image_path)
            visual_crop_photo["value"] = photo
            visual_crop.configure(
                image=photo,
                text=f"{roi.roi_id} / {label} / x={rect.x} y={rect.y} w={rect.width} h={rect.height}",
                compound="top",
            )
            visual_profile_status.set(
                f"使用中HUD設定: {binding.profile.profile_id} / {binding.source_width}x{binding.source_height}"
            )
        except Exception as exc:
            show_operation_error(
                "画像学習データ", "ERR_DBD_VISUAL_VIDEO_PREVIEW",
                "動画から登録画像を切り出せませんでした。",
                "動画、HUD設定、学習対象、スロットを確認してください。", exc,
            )

    def register_visual_from_video() -> None:
        staged = visual_staged["value"]
        if staged is None:
            messagebox.showinfo("画像学習データ", "先に切り出し範囲を確認してください。")
            return
        if messagebox.askyesno("画像学習データを登録", f"{staged.label} / {staged.roi_id} を登録しますか？"):
            safe_visual_learning.confirm_register(staged)
            visual_staged["value"] = None
            refresh_visual_list()

    visual_actions = ttk.Frame(preview_box)
    visual_actions.grid(row=2, column=0, sticky="w", pady=(6, 0))
    ttk.Button(visual_actions, text="1. 切り出し範囲を確認", command=preview_visual_from_video).pack(side="left", padx=(0, 6))
    ttk.Button(visual_actions, text="2. 確認した画像を登録", command=register_visual_from_video).pack(side="left")

    # Manual registration -----------------------------------------------------
    visual_manual_tab.columnconfigure(1, weight=1)
    manual_domain_display = tk.StringVar(value="パーク")
    manual_label_id = tk.StringVar()
    manual_label_display = tk.StringVar()
    manual_group = tk.StringVar(value="normal")
    manual_visibility_display = tk.StringVar(value=hud_visibility_display(HudVisibility.VISIBLE.value))
    manual_source_mode = tk.StringVar(value=SOURCE_MODE_MANUAL_JA)
    manual_source_url = tk.StringVar()
    manual_notes = tk.Text(visual_manual_tab, height=5, wrap="word")
    ttk.Label(visual_manual_tab, text="画像ファイル（必須）").grid(row=0, column=0, sticky="w", pady=3)
    ttk.Entry(visual_manual_tab, textvariable=visual_vars["image"]).grid(row=0, column=1, sticky="ew", pady=3)
    def choose_visual_image() -> None:
        chosen = filedialog.askopenfilename(title="登録する画像を選択")
        if chosen:
            visual_vars["image"].set(chosen)
    ttk.Button(visual_manual_tab, text="参照", command=choose_visual_image).grid(row=0, column=2, padx=(8, 0))
    ttk.Label(visual_manual_tab, text="学習対象").grid(row=1, column=0, sticky="w", pady=3)
    ttk.Combobox(visual_manual_tab, textvariable=manual_domain_display, values=list(visual_domain_labels), state="readonly").grid(row=1, column=1, sticky="ew", pady=3)
    ttk.Label(visual_manual_tab, text="正解ゲーム要素").grid(row=2, column=0, sticky="w", pady=3)
    ttk.Entry(visual_manual_tab, textvariable=manual_label_display, state="readonly").grid(row=2, column=1, sticky="ew", pady=3)
    def choose_manual_game_element() -> None:
        domain = visual_domain_labels[manual_domain_display.get()]
        def selected(choice) -> None:
            manual_label_id.set(choice.entity_id)
            manual_label_display.set(f"{choice.matched_text}  [{choice.entity_id}]")
        open_game_element_selector(
            root, catalog=entity_alias_catalog, title="正解ゲーム要素を選択",
            on_select=selected, expected_kind=visual_kind_map[domain], verified_only=True,
        )
    ttk.Button(visual_manual_tab, text="検索", command=choose_manual_game_element).grid(row=2, column=2, padx=(8, 0))
    ttk.Label(visual_manual_tab, text="表示状態").grid(row=3, column=0, sticky="w", pady=3)
    ttk.Combobox(
        visual_manual_tab, textvariable=manual_visibility_display,
        values=list(HUD_VISIBILITY_JA.values()), state="readonly",
    ).grid(row=3, column=1, sticky="ew", pady=3)
    ttk.Label(visual_manual_tab, text="画像グループ").grid(row=4, column=0, sticky="w", pady=3)
    ttk.Combobox(
        visual_manual_tab, textvariable=manual_group, values=VISUAL_GROUP_PRESETS, state="normal",
    ).grid(row=4, column=1, sticky="ew", pady=3)
    ttk.Label(visual_manual_tab, text=VISUAL_GROUP_HELP_JA, wraplength=700).grid(
        row=5, column=1, columnspan=2, sticky="w", pady=(0, 4)
    )
    ttk.Label(visual_manual_tab, text="情報源").grid(row=6, column=0, sticky="w", pady=3)
    manual_source_row = ttk.Frame(visual_manual_tab)
    manual_source_row.grid(row=6, column=1, columnspan=2, sticky="ew", pady=3)
    manual_source_row.columnconfigure(2, weight=1)
    manual_source_entry = ttk.Entry(manual_source_row, textvariable=manual_source_url, state="disabled")
    def sync_manual_visual_source() -> None:
        manual_source_entry.configure(
            state="normal" if manual_source_mode.get() == SOURCE_MODE_URL_JA else "disabled"
        )
    ttk.Radiobutton(
        manual_source_row, text=SOURCE_MODE_MANUAL_JA, variable=manual_source_mode,
        value=SOURCE_MODE_MANUAL_JA, command=sync_manual_visual_source,
    ).grid(row=0, column=0)
    ttk.Radiobutton(
        manual_source_row, text=SOURCE_MODE_URL_JA, variable=manual_source_mode,
        value=SOURCE_MODE_URL_JA, command=sync_manual_visual_source,
    ).grid(row=0, column=1)
    manual_source_entry.grid(row=0, column=2, sticky="ew", padx=(4, 0))
    ttk.Label(visual_manual_tab, text="メモ").grid(row=7, column=0, sticky="nw", pady=3)
    manual_notes.grid(row=7, column=1, columnspan=2, sticky="ew", pady=3)

    def register_manual_visual() -> None:
        try:
            image = Path(visual_vars["image"].get()).expanduser().resolve()
            if not image.is_file():
                raise ValueError("登録する画像ファイルを選択してください。")
            label = manual_label_id.get().strip()
            if not label:
                raise ValueError("正解ゲーム要素を検索して選択してください。")
            sample = VisualTrainingSample(
                domain=visual_domain_labels[manual_domain_display.get()],
                label=label, image_path=str(image),
                group=manual_group.get().strip() or "normal",
                source_ref=compose_source_ref(manual_source_mode.get(), manual_source_url.get()),
                notes=manual_notes.get("1.0", "end").strip(),
                registration_origin="MANUAL_IMAGE",
                display_state=visual_visibility_reverse.get(
                    manual_visibility_display.get(), HudVisibility.VISIBLE.value
                ),
            )
            if workspace.visual.append(sample):
                messagebox.showinfo("画像学習データ", "手動画像を登録しました。")
                refresh_visual_list()
            else:
                messagebox.showinfo("画像学習データ", "同一の登録済みデータがあります。")
        except Exception as exc:
            show_operation_error(
                "画像学習データ", "ERR_DBD_VISUAL_MANUAL_REGISTER",
                "手動画像を登録できませんでした。",
                "画像、学習対象、正解ゲーム要素を確認してください。", exc,
            )
    ttk.Button(visual_manual_tab, text="登録", command=register_manual_visual).grid(row=8, column=1, sticky="w", pady=8)

    # Registered list + direct modal editing ---------------------------------
    visual_list_tab.columnconfigure(0, weight=1)
    visual_list_tab.rowconfigure(1, weight=1)
    visual_list_filter = tk.StringVar()
    filter_row = ttk.Frame(visual_list_tab)
    filter_row.grid(row=0, column=0, sticky="ew", pady=(0, 6))
    filter_row.columnconfigure(1, weight=1)
    ttk.Label(filter_row, text="検索").grid(row=0, column=0, padx=(0, 4))
    ttk.Entry(filter_row, textvariable=visual_list_filter).grid(row=0, column=1, sticky="ew")
    visual_tree = ttk.Treeview(
        visual_list_tab,
        columns=("target", "label", "origin", "slot", "group", "source"),
        show="headings", height=12,
    )
    for key, title, width in (
        ("target", "学習対象", 110), ("label", "正解ゲーム要素", 200),
        ("origin", "登録方法", 110), ("slot", "スロット", 120),
        ("group", "画像グループ", 120), ("source", "情報源", 260),
    ):
        visual_tree.heading(key, text=title)
        visual_tree.column(key, width=width, stretch=True)
    visual_tree.grid(row=1, column=0, sticky="nsew")
    visual_rows: list[VisualTrainingSample] = []

    def refresh_visual_list(*_args) -> None:
        visual_tree.delete(*visual_tree.get_children())
        visual_rows.clear()
        needle = visual_list_filter.get().strip().casefold()
        for item in workspace.visual.list():
            if needle and needle not in f"{item.domain.value} {item.label} {item.group} {item.slot}".casefold():
                continue
            index = len(visual_rows)
            visual_rows.append(item)
            visual_tree.insert(
                "", "end", iid=str(index),
                values=(
                    visual_domain_display(item.domain.value), item.label,
                    item.registration_origin, item.slot or "-", item.group,
                    "手入力" if item.source_ref == "manual://owner" else item.source_ref,
                ),
            )
    visual_list_filter.trace_add("write", refresh_visual_list)

    def selected_visual() -> VisualTrainingSample | None:
        selected = visual_tree.selection()
        if not selected:
            return None
        index = int(selected[0])
        return visual_rows[index] if 0 <= index < len(visual_rows) else None

    def open_visual_edit_modal() -> None:
        original = selected_visual()
        if original is None:
            messagebox.showinfo("画像学習データ", "編集する登録済みデータを選択してください。")
            return
        modal = tk.Toplevel(root)
        modal.title("画像学習データを編集")
        modal.transient(root)
        modal.grab_set()
        modal.columnconfigure(1, weight=1)
        domain_display = tk.StringVar(value=next((k for k,v in visual_domain_labels.items() if v is original.domain), "パーク"))
        label_id = tk.StringVar(value=original.label)
        label_display = tk.StringVar(value=original.label)
        group = tk.StringVar(value=original.group)
        slot = tk.StringVar(value=original.slot)
        display_state = tk.StringVar(value=original.display_state)
        notes_widget = tk.Text(modal, height=5, wrap="word")
        notes_widget.insert("1.0", original.notes)
        ttk.Label(modal, text="学習対象").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        ttk.Combobox(modal, textvariable=domain_display, values=list(visual_domain_labels), state="readonly").grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        ttk.Label(modal, text="正解ゲーム要素").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        ttk.Entry(modal, textvariable=label_display, state="readonly").grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        def choose_edit_label() -> None:
            domain = visual_domain_labels[domain_display.get()]
            def picked(choice) -> None:
                label_id.set(choice.entity_id); label_display.set(f"{choice.matched_text}  [{choice.entity_id}]")
            open_game_element_selector(root, catalog=entity_alias_catalog, title="正解ゲーム要素を選択", on_select=picked, expected_kind=visual_kind_map[domain], verified_only=True)
        ttk.Button(modal, text="検索", command=choose_edit_label).grid(row=1, column=2, padx=10, pady=5)
        ttk.Label(modal, text="スロット").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        ttk.Entry(modal, textvariable=slot).grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        ttk.Label(modal, text="表示状態").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        ttk.Entry(modal, textvariable=display_state).grid(row=3, column=1, sticky="ew", padx=10, pady=5)
        ttk.Label(modal, text="画像グループ").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        ttk.Entry(modal, textvariable=group).grid(row=4, column=1, sticky="ew", padx=10, pady=5)
        ttk.Label(modal, text="メモ").grid(row=5, column=0, sticky="nw", padx=10, pady=5)
        notes_widget.grid(row=5, column=1, columnspan=2, sticky="ew", padx=10, pady=5)
        def save_edit() -> None:
            try:
                replacement = VisualTrainingSample(
                    domain=visual_domain_labels[domain_display.get()], label=label_id.get(),
                    image_path=original.image_path, group=group.get().strip() or "normal",
                    source_ref=original.source_ref, notes=notes_widget.get("1.0", "end").strip(),
                    registration_origin=original.registration_origin, slot=slot.get().strip(),
                    display_state=display_state.get().strip(), source_video=original.source_video,
                    source_frame=original.source_frame,
                )
                if not workspace.visual.replace(original, replacement):
                    raise ValueError("編集対象が現在の一覧に見つかりません。")
                modal.destroy(); refresh_visual_list()
            except Exception as exc:
                messagebox.showerror("編集できません", f"{type(exc).__name__}: {exc}", parent=modal)
        actions = ttk.Frame(modal)
        actions.grid(row=6, column=1, columnspan=2, sticky="e", padx=10, pady=10)
        ttk.Button(actions, text="キャンセル", command=modal.destroy).pack(side="left", padx=4)
        ttk.Button(actions, text="保存", command=save_edit).pack(side="left", padx=4)

    def delete_visual() -> None:
        item = selected_visual()
        if item and messagebox.askyesno("削除確認", f"{item.label} を削除しますか？"):
            workspace.visual.delete(item); refresh_visual_list()

    visual_list_actions = ttk.Frame(visual_list_tab)
    visual_list_actions.grid(row=2, column=0, sticky="w", pady=8)
    ttk.Button(visual_list_actions, text="編集", command=open_visual_edit_modal).pack(side="left", padx=(0, 6))
    ttk.Button(visual_list_actions, text="削除", command=delete_visual).pack(side="left")
    visual_tree.bind("<Double-1>", lambda _e: open_visual_edit_modal())
    refresh_visual_list()

    # ---- Upper-right notification learning ----------------------------------
    ocr_tab = ttk.Frame(notebook, padding=8)
    notebook.add(ocr_tab, text="右上通知を学習")
    ocr_tab.columnconfigure(0, weight=1)
    ocr_tab.rowconfigure(0, weight=1)
    ocr_notebook = ttk.Notebook(ocr_tab)
    ocr_notebook.grid(row=0, column=0, sticky="nsew")
    ocr_video_tab = ttk.Frame(ocr_notebook)
    ocr_manual_tab = ttk.Frame(ocr_notebook, padding=12)
    ocr_list_tab = ttk.Frame(ocr_notebook, padding=12)
    ocr_notebook.add(ocr_video_tab, text="動画から抽出")
    ocr_notebook.add(ocr_manual_tab, text="手動で登録")
    ocr_notebook.add(ocr_list_tab, text="登録済み一覧")

    ocr_video = tk.StringVar(); ocr_frame = tk.StringVar(value="0")
    ocr_profile = tk.StringVar(); ocr_tesseract = tk.StringVar(value=runtime_tesseract)
    ocr_phrase = tk.StringVar(); ocr_signal = tk.StringVar(value="CHASE")
    ocr_signal_display = tk.StringVar(); ocr_locale = tk.StringVar(value="ja-JP")
    ocr_inspector = FFmpegFrameInspector(ffmpeg_executable=runtime_ffmpeg, ffprobe_executable=runtime_ffprobe); ocr_candidates = []

    def choose_ocr_video() -> None:
        chosen = filedialog.askopenfilename(
            title="右上通知を学習するDbD動画を選択",
            filetypes=[("Video", "*.mp4 *.mkv *.mov *.avi *.webm"), ("All files", "*.*")],
        )
        if chosen:
            ocr_video.set(chosen)

    def choose_ocr_profile() -> None:
        chosen = filedialog.askopenfilename(
            title="HUDプロファイルJSONを選択",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if chosen:
            ocr_profile.set(chosen)

    ocr_video_tab.columnconfigure(0, weight=1)
    ocr_video_tab.rowconfigure(0, weight=1)
    ocr_paned = ttk.Panedwindow(ocr_video_tab, orient="vertical")
    ocr_paned.grid(row=0, column=0, sticky="nsew")
    ocr_media_host = ttk.Frame(ocr_paned, padding=8)
    ocr_media_host.columnconfigure(0, weight=1); ocr_media_host.rowconfigure(0, weight=1)
    ocr_form_host = ttk.Frame(ocr_paned)
    ocr_form_host.columnconfigure(0, weight=1); ocr_form_host.rowconfigure(0, weight=1)
    ocr_paned.add(ocr_media_host, weight=1); ocr_paned.add(ocr_form_host, weight=1)
    bind_media_minimum_height(ocr_paned, media_first=True, minimum_fraction=0.6, minimum_pixels=420)

    def ocr_media_header(parent) -> None:
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text="学習元動画（必須）").grid(row=0, column=0, sticky="w")
        ttk.Entry(parent, textvariable=ocr_video).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(parent, text="参照", command=choose_ocr_video).grid(row=0, column=2)
        ttk.Label(parent, text="詳細設定：HUDプロファイルJSON（任意）").grid(row=1, column=0, sticky="w", pady=(4,0))
        ttk.Entry(parent, textvariable=ocr_profile).grid(row=1, column=1, sticky="ew", padx=4, pady=(4,0))
        ttk.Button(parent, text="参照", command=choose_ocr_profile).grid(row=1, column=2, pady=(4,0))
        ttk.Label(parent, text="Tesseract").grid(row=2, column=0, sticky="w", pady=(4,0))
        ttk.Entry(parent, textvariable=ocr_tesseract).grid(row=2, column=1, sticky="ew", padx=4, pady=(4,0))

    ocr_player = TkTrainingMediaPlayer(
        ocr_media_host, root=root, source_getter=lambda: ocr_video.get(),
        frame_getter=lambda: int(ocr_frame.get() or "0"),
        frame_setter=lambda value: ocr_frame.set(str(value)),
        status_setter=status.set, ffprobe_executable=runtime_ffprobe, diagnostics=diagnostics,
        diagnostic_feature="NOTIFICATION_LEARNING", player_id="notification-learning-player",
        control_header_builder=ocr_media_header,
    )
    ocr_player.grid(row=0, column=0, sticky="nsew")

    ocr_scroll = ScrollableForm(ocr_form_host, padding=12)
    ocr_scroll.grid(row=0, column=0, sticky="nsew")
    ocr_form = ocr_scroll.inner
    ocr_form.columnconfigure(0, weight=1); ocr_form.columnconfigure(1, weight=1)
    extract_box = ttk.LabelFrame(ocr_form, text="OCR抽出", padding=8)
    extract_box.grid(row=0, column=0, sticky="nsew", padx=(0,6))
    extract_box.columnconfigure(0, weight=1)
    candidate_tree = ttk.Treeview(extract_box, columns=("frame","text"), show="headings", height=7)
    candidate_tree.heading("frame", text="フレーム"); candidate_tree.heading("text", text="OCR候補")
    candidate_tree.column("frame", width=90, stretch=False); candidate_tree.column("text", width=320, stretch=True)
    candidate_tree.grid(row=0, column=0, sticky="nsew")
    ttk.Button(extract_box, text="現在フレームからOCR候補を抽出", command=lambda: scan_current_ocr()).grid(row=1, column=0, sticky="w", pady=(6,0))

    confirm_box = ttk.LabelFrame(ocr_form, text="正解データを確認・修正", padding=8)
    confirm_box.grid(row=0, column=1, sticky="nsew", padx=(6,0))
    confirm_box.columnconfigure(1, weight=1)
    signal_map = {}
    ttk.Label(confirm_box, text="通知の種類").grid(row=0, column=0, sticky="w", pady=3)
    signal_combo = ttk.Combobox(confirm_box, textvariable=ocr_signal_display, state="readonly")
    signal_combo.grid(row=0, column=1, sticky="ew", pady=3)
    def refresh_signal() -> None:
        signal_map.clear(); signal_map.update(dict(notification_signal_choices(workspace.ocr.list())))
        signal_combo.configure(values=list(signal_map))
        if not ocr_signal_display.get() and signal_map:
            first = next(iter(signal_map)); ocr_signal_display.set(first); ocr_signal.set(signal_map[first])
    def sync_signal(_event=None) -> None:
        if ocr_signal_display.get() in signal_map:
            ocr_signal.set(signal_map[ocr_signal_display.get()])
    signal_combo.bind("<<ComboboxSelected>>", sync_signal)
    ttk.Label(confirm_box, text="OCR原文 / 修正文").grid(row=1, column=0, sticky="w", pady=3)
    ttk.Entry(confirm_box, textvariable=ocr_phrase).grid(row=1, column=1, sticky="ew", pady=3)
    ttk.Label(confirm_box, text="この通知の意味・説明").grid(row=2, column=0, sticky="nw", pady=3)
    ocr_meaning = tk.Text(confirm_box, height=4, wrap="word")
    ocr_meaning.grid(row=2, column=1, sticky="ew", pady=3)
    event_display = tk.StringVar(value="関連付けなし")
    event_map = {"関連付けなし":""}; event_map.update({label:event.value for event,label in EVENT_TYPE_JA.items()})
    ttk.Label(confirm_box, text="関連イベント").grid(row=3, column=0, sticky="w", pady=3)
    ttk.Combobox(confirm_box, textvariable=event_display, values=list(event_map), state="readonly").grid(row=3, column=1, sticky="ew", pady=3)
    source_mode = tk.StringVar(value=SOURCE_MODE_MANUAL_JA); source_url = tk.StringVar()
    ttk.Label(confirm_box, text="情報源").grid(row=4, column=0, sticky="w", pady=3)
    source_row = ttk.Frame(confirm_box); source_row.grid(row=4, column=1, sticky="ew"); source_row.columnconfigure(2, weight=1)
    url_entry = ttk.Entry(source_row, textvariable=source_url, state="disabled")
    def sync_source() -> None:
        url_entry.configure(state="normal" if source_mode.get()==SOURCE_MODE_URL_JA else "disabled")
    ttk.Radiobutton(source_row, text=SOURCE_MODE_MANUAL_JA, variable=source_mode, value=SOURCE_MODE_MANUAL_JA, command=sync_source).grid(row=0,column=0)
    ttk.Radiobutton(source_row, text=SOURCE_MODE_URL_JA, variable=source_mode, value=SOURCE_MODE_URL_JA, command=sync_source).grid(row=0,column=1)
    url_entry.grid(row=0,column=2,sticky="ew",padx=(4,0))

    def scan_current_ocr() -> None:
        try:
            source = ocr_video.get().strip()
            if not source:
                raise ValueError("先に学習元動画を選択してください。")
            frame = int(ocr_frame.get() or "0")
            binding = resolve_workflow_hud_profile(
                title="右上通知を学習", video_path=source,
                profile_var=ocr_profile, frame_index=frame, inspector=ocr_inspector,
            )
        except Exception as exc:
            show_operation_error(
                "右上通知を学習", "ERR_DBD_OCR_VIDEO_PREPARE",
                "OCR抽出条件を準備できませんでした。",
                "動画とHUD設定を確認してください。HUD候補が複数ある場合は使用する設定を選択してください。", exc,
            )
            return

        def completed(report) -> None:
            ocr_candidates[:] = report.candidates
            candidate_tree.delete(*candidate_tree.get_children())
            for index, item in enumerate(ocr_candidates):
                candidate_tree.insert(
                    "", "end", iid=str(index),
                    values=(item.frame_index, item.text or item.normalized_text),
                )
            status.set(f"右上通知OCR: 候補 {len(ocr_candidates)}件")
            if not ocr_candidates:
                messagebox.showinfo(
                    "右上通知を学習",
                    "現在フレームの右上通知ROIから文字候補を検出できませんでした。\n"
                    "通知が表示されているフレーム、HUD設定、Tesseract言語設定を確認してください。",
                )

        run_background(
            "右上通知OCR",
            lambda: workspace.scan_upper_right_ocr_from_video(
                video_path=source, start_frame=frame,
                end_frame_exclusive=frame + 1, frame_step=1,
                roi_profile_path=binding.profile_path,
                tesseract_executable=ocr_tesseract.get().strip() or runtime_tesseract,
                language=active_runtime.ocr_language or "jpn+eng", max_samples=1,
            ),
            completed,
        )

    def pick_candidate(_event=None) -> None:
        selected = candidate_tree.selection()
        if selected:
            ocr_phrase.set(ocr_candidates[int(selected[0])].text.strip())
    candidate_tree.bind("<<TreeviewSelect>>", pick_candidate)

    def save_ocr_from_form() -> None:
        try:
            ref = compose_source_ref(source_mode.get(), source_url.get())
            sample = OcrVocabularySample(ocr_signal.get(), ocr_phrase.get().strip(), ocr_locale.get(), ref)
            workspace.ocr.append(sample)
            notification_semantics.upsert(NotificationSemanticRecord(
                sample.signal_id, sample.phrase, ocr_meaning.get("1.0","end").strip(),
                event_map.get(event_display.get(), ""), ref,
            ))
            refresh_ocr_list()
        except Exception as exc:
            show_operation_error("右上通知を学習","ERR_DBD_OCR_REGISTER","通知を保存できませんでした。","通知の種類、表示文字、意味、情報源を確認してください。",exc)
    ttk.Button(confirm_box, text="登録", command=save_ocr_from_form).grid(row=5,column=1,sticky="w",pady=6)

    # Manual notification registration reuses the exact same canonical stores.
    ocr_manual_tab.columnconfigure(1, weight=1)
    manual_signal_display = tk.StringVar(); manual_signal = tk.StringVar(value="CHASE")
    manual_phrase = tk.StringVar(); manual_meaning = tk.Text(ocr_manual_tab,height=5,wrap="word")
    ttk.Label(ocr_manual_tab,text="通知の種類").grid(row=0,column=0,sticky="w",pady=3)
    manual_signal_combo = ttk.Combobox(ocr_manual_tab,textvariable=manual_signal_display,state="readonly")
    manual_signal_combo.grid(row=0,column=1,sticky="ew",pady=3)
    ttk.Label(ocr_manual_tab,text="画面表示文字").grid(row=1,column=0,sticky="w",pady=3)
    ttk.Entry(ocr_manual_tab,textvariable=manual_phrase).grid(row=1,column=1,sticky="ew",pady=3)
    ttk.Label(ocr_manual_tab,text="意味・説明").grid(row=2,column=0,sticky="nw",pady=3)
    manual_meaning.grid(row=2,column=1,sticky="ew",pady=3)
    def refresh_manual_signal() -> None:
        mapping = dict(notification_signal_choices(workspace.ocr.list()))
        manual_signal_combo.configure(values=list(mapping))
        if not manual_signal_display.get() and mapping:
            key=next(iter(mapping)); manual_signal_display.set(key); manual_signal.set(mapping[key])
        manual_signal_combo._bai_mapping = mapping
    def sync_manual_signal(_event=None) -> None:
        mapping=getattr(manual_signal_combo,"_bai_mapping",{})
        if manual_signal_display.get() in mapping:
            manual_signal.set(mapping[manual_signal_display.get()])
    manual_signal_combo.bind("<<ComboboxSelected>>",sync_manual_signal)
    def save_manual_ocr() -> None:
        try:
            sample=OcrVocabularySample(manual_signal.get(),manual_phrase.get().strip(),"ja-JP","manual://owner")
            workspace.ocr.append(sample)
            notification_semantics.upsert(NotificationSemanticRecord(sample.signal_id,sample.phrase,manual_meaning.get("1.0","end").strip(),"","manual://owner"))
            refresh_ocr_list(); refresh_manual_signal()
        except Exception as exc:
            show_operation_error("右上通知を学習","ERR_DBD_OCR_MANUAL_REGISTER","通知を登録できませんでした。","通知種類と表示文字を確認してください。",exc)
    ttk.Button(ocr_manual_tab,text="登録",command=save_manual_ocr).grid(row=3,column=1,sticky="w",pady=8)

    # Registered notification list + modal editing.
    ocr_list_tab.columnconfigure(0, weight=1); ocr_list_tab.rowconfigure(0, weight=1)
    ocr_tree = ttk.Treeview(ocr_list_tab,columns=("type","phrase","meaning"),show="headings",height=12)
    ocr_tree.heading("type",text="通知の種類"); ocr_tree.heading("phrase",text="画面表示文字"); ocr_tree.heading("meaning",text="意味・説明")
    ocr_tree.grid(row=0,column=0,sticky="nsew")
    ocr_rows=[]
    def refresh_ocr_list() -> None:
        refresh_signal(); refresh_manual_signal(); ocr_tree.delete(*ocr_tree.get_children()); ocr_rows.clear()
        for item in workspace.ocr.list():
            sem=notification_semantics.find(item.signal_id,item.phrase)
            label=next((k for k,v in signal_map.items() if v==item.signal_id),item.signal_id)
            index=len(ocr_rows); ocr_rows.append(item)
            ocr_tree.insert("","end",iid=str(index),values=(label,item.phrase,sem.meaning if sem else ""))
    def selected_ocr():
        selected=ocr_tree.selection()
        if not selected:return None
        index=int(selected[0]); return ocr_rows[index] if 0<=index<len(ocr_rows) else None
    def edit_ocr_modal() -> None:
        original=selected_ocr()
        if original is None:
            messagebox.showinfo("右上通知", "編集する通知を選択してください。"); return
        sem=notification_semantics.find(original.signal_id,original.phrase)
        modal=tk.Toplevel(root); modal.title("右上通知を編集"); modal.transient(root); modal.grab_set(); modal.columnconfigure(1,weight=1)
        signal=tk.StringVar(value=original.signal_id); phrase=tk.StringVar(value=original.phrase); meaning=tk.Text(modal,height=5,wrap="word")
        meaning.insert("1.0", sem.meaning if sem else "")
        ttk.Label(modal,text="Signal ID").grid(row=0,column=0,padx=10,pady=5,sticky="w"); ttk.Entry(modal,textvariable=signal).grid(row=0,column=1,padx=10,pady=5,sticky="ew")
        ttk.Label(modal,text="表示文字").grid(row=1,column=0,padx=10,pady=5,sticky="w"); ttk.Entry(modal,textvariable=phrase).grid(row=1,column=1,padx=10,pady=5,sticky="ew")
        ttk.Label(modal,text="意味・説明").grid(row=2,column=0,padx=10,pady=5,sticky="nw"); meaning.grid(row=2,column=1,padx=10,pady=5,sticky="ew")
        def save_edit() -> None:
            replacement=OcrVocabularySample(signal.get().strip().upper(),phrase.get().strip(),original.locale,original.source_ref)
            try:
                if not workspace.ocr.replace(original,replacement): raise ValueError("編集対象が見つかりません。")
                notification_semantics.delete(original.signal_id,original.phrase)
                notification_semantics.upsert(NotificationSemanticRecord(replacement.signal_id,replacement.phrase,meaning.get("1.0","end").strip(),sem.related_event_type if sem else "",replacement.source_ref))
                modal.destroy(); refresh_ocr_list()
            except Exception as exc: messagebox.showerror("編集できません",f"{type(exc).__name__}: {exc}",parent=modal)
        row=ttk.Frame(modal); row.grid(row=3,column=1,sticky="e",padx=10,pady=10)
        ttk.Button(row,text="キャンセル",command=modal.destroy).pack(side="left",padx=4); ttk.Button(row,text="保存",command=save_edit).pack(side="left",padx=4)
    def delete_ocr() -> None:
        item=selected_ocr()
        if item and messagebox.askyesno("削除確認",f"「{item.phrase}」を削除しますか？"):
            workspace.ocr.delete(item); notification_semantics.delete(item.signal_id,item.phrase); refresh_ocr_list()
    ocr_actions=ttk.Frame(ocr_list_tab); ocr_actions.grid(row=1,column=0,sticky="w",pady=8)
    ttk.Button(ocr_actions,text="編集",command=edit_ocr_modal).pack(side="left",padx=(0,6)); ttk.Button(ocr_actions,text="削除",command=delete_ocr).pack(side="left")
    ocr_tree.bind("<Double-1>",lambda _e:edit_ocr_modal())
    refresh_ocr_list()

    # ---- Trivia tab ----------------------------------------------------------
    trivia_tab = ttk.Frame(notebook, padding=8)
    notebook.add(trivia_tab, text="実況・豆知識を登録")
    trivia_tab.columnconfigure(0, weight=1)
    trivia_tab.rowconfigure(0, weight=1)

    trivia_notebook = ttk.Notebook(trivia_tab)
    trivia_notebook.grid(row=0, column=0, sticky="nsew")

    manual_tab = ttk.Frame(trivia_notebook, padding=12)
    mining_tab = ttk.Frame(trivia_notebook, padding=12)
    list_tab = ttk.Frame(trivia_notebook, padding=12)
    trivia_notebook.add(mining_tab, text="動画から候補を作る")
    trivia_notebook.add(manual_tab, text="手動で登録")
    trivia_notebook.add(list_tab, text="登録済み・候補一覧")

    manual_tab.columnconfigure(1, weight=1)
    manual_tab.columnconfigure(2, weight=1)
    mining_tab.columnconfigure(1, weight=1)
    list_tab.columnconfigure(0, weight=1)
    list_tab.rowconfigure(1, weight=1)

    trivia_title = tk.StringVar()
    trivia_category = tk.StringVar(value="GENERAL")
    trivia_tags = tk.StringVar()
    trivia_entities = tk.StringVar()
    trivia_source = tk.StringVar(value="manual://owner")
    trivia_env = tk.StringVar(value="LIVE")
    trivia_from = tk.StringVar()
    trivia_to = tk.StringVar()
    trivia_save_mode = tk.StringVar(value="候補として登録")
    trivia_editing_id = {"value": None}
    trivia_existing_source_ref = {"value": None}
    trivia_help = tk.StringVar(
        value="項目を選択すると、ここに説明と入力例を表示します。"
    )

    def set_trivia_help(key: str) -> None:
        title, description, example = FIELD_HELP_JA[key]
        trivia_help.set(f"{title}\n\n{description}\n\n{example}")

    ttk.Label(manual_tab, text="タイトル").grid(row=0, column=0, sticky="w", pady=3)
    ttk.Entry(manual_tab, textvariable=trivia_title).grid(row=0, column=1, sticky="ew", pady=3)

    ttk.Label(manual_tab, text="カテゴリ").grid(row=1, column=0, sticky="w", pady=3)
    category_display = tk.StringVar(value=TRIVIA_CATEGORIES["GENERAL"])
    category_reverse = {label:key for key,label in TRIVIA_CATEGORIES.items()}
    category_combo = ttk.Combobox(
        manual_tab,
        textvariable=category_display,
        values=list(category_reverse),
        state="readonly",
    )
    category_combo.grid(row=1, column=1, sticky="ew", pady=3)
    category_combo.bind(
        "<<ComboboxSelected>>",
        lambda _e: (
            trivia_category.set(category_reverse[category_display.get()]),
            set_trivia_help("category"),
        ),
    )

    ttk.Label(manual_tab, text="タグ").grid(row=2, column=0, sticky="w", pady=3)
    tag_entry = ttk.Entry(manual_tab, textvariable=trivia_tags)
    tag_entry.grid(row=2, column=1, sticky="ew", pady=3)
    tag_entry.bind("<FocusIn>", lambda _e: set_trivia_help("tags"))

    ttk.Label(manual_tab, text="使用する場面").grid(row=3, column=0, sticky="nw", pady=3)
    event_frame = ttk.Frame(manual_tab)
    event_frame.grid(row=3, column=1, sticky="ew", pady=3)
    event_vars = {}
    for index, event in enumerate(GameEventType):
        if event is GameEventType.UNKNOWN_EVENT:
            continue
        var = tk.BooleanVar(value=False)
        event_vars[event] = var
        ttk.Checkbutton(
            event_frame,
            text=EVENT_TYPE_JA[event],
            variable=var,
        ).grid(row=index // 3, column=index % 3, sticky="w", padx=(0, 8))

    ttk.Label(manual_tab, text="関連するゲーム要素").grid(row=4, column=0, sticky="w", pady=3)
    entity_frame = ttk.Frame(manual_tab)
    entity_frame.grid(row=4, column=1, sticky="ew", pady=3)
    entity_frame.columnconfigure(0, weight=1)
    ttk.Entry(entity_frame, textvariable=trivia_entities).grid(row=0, column=0, sticky="ew")

    def search_entity_alias() -> None:
        def selected(row) -> None:
            current = [x.strip() for x in trivia_entities.get().split(",") if x.strip()]
            if row.entity_id not in current:
                current.append(row.entity_id)
            trivia_entities.set(", ".join(current))
            status.set(f"ゲーム要素を追加: {row.matched_text} ({row.entity_id})")
        open_game_element_selector(
            root,
            catalog=entity_alias_catalog,
            title="豆知識に関連するゲーム要素を選択",
            on_select=selected,
            expected_kind=None,
        )

    ttk.Button(
        entity_frame,
        text="名前・略称から選択",
        command=search_entity_alias,
    ).grid(row=0, column=1, padx=(8, 0))

    trivia_source_mode = tk.StringVar(value=SOURCE_MODE_MANUAL_JA)
    trivia_source_url = tk.StringVar()
    trivia_source_frame = ttk.Frame(manual_tab)
    trivia_source_frame.grid(row=5, column=1, sticky="ew", pady=3)
    trivia_source_frame.columnconfigure(2, weight=1)
    ttk.Label(manual_tab, text="情報源").grid(row=5, column=0, sticky="w", pady=3)
    trivia_source_url_entry = ttk.Entry(
        trivia_source_frame,
        textvariable=trivia_source_url,
        state="disabled",
    )

    def sync_trivia_source() -> None:
        is_url = trivia_source_mode.get() == SOURCE_MODE_URL_JA
        trivia_source_url_entry.configure(state="normal" if is_url else "disabled")
        if not is_url:
            trivia_source.set("manual://owner")

    ttk.Radiobutton(
        trivia_source_frame,
        text=SOURCE_MODE_MANUAL_JA,
        variable=trivia_source_mode,
        value=SOURCE_MODE_MANUAL_JA,
        command=sync_trivia_source,
    ).grid(row=0, column=0, sticky="w", padx=(0, 8))
    ttk.Radiobutton(
        trivia_source_frame,
        text=SOURCE_MODE_URL_JA,
        variable=trivia_source_mode,
        value=SOURCE_MODE_URL_JA,
        command=sync_trivia_source,
    ).grid(row=0, column=1, sticky="w", padx=(0, 8))
    trivia_source_url_entry.grid(row=0, column=2, sticky="ew")

    ttk.Label(manual_tab, text="対象ゲームバージョン（開始）").grid(row=6, column=0, sticky="w", pady=3)
    ttk.Entry(manual_tab, textvariable=trivia_from).grid(row=6, column=1, sticky="ew", pady=3)
    ttk.Label(manual_tab, text="対象ゲームバージョン（終了）").grid(row=7, column=0, sticky="w", pady=3)
    ttk.Entry(manual_tab, textvariable=trivia_to).grid(row=7, column=1, sticky="ew", pady=3)

    ttk.Label(manual_tab, text="対象環境").grid(row=8, column=0, sticky="w", pady=3)
    env_display = tk.StringVar(value=ENVIRONMENT_JA[PerkEnvironment.LIVE])
    env_reverse = {label:env for env,label in ENVIRONMENT_JA.items()}
    env_combo = ttk.Combobox(
        manual_tab,
        textvariable=env_display,
        values=list(env_reverse),
        state="readonly",
    )
    env_combo.grid(row=8, column=1, sticky="ew", pady=3)
    env_combo.bind(
        "<<ComboboxSelected>>",
        lambda _e: (
            trivia_env.set(env_reverse[env_display.get()].value),
            set_trivia_help("environment"),
        ),
    )

    ttk.Label(manual_tab, text="登録状態").grid(row=9, column=0, sticky="w", pady=3)
    state_frame = ttk.Frame(manual_tab)
    state_frame.grid(row=9, column=1, sticky="w", pady=3)
    ttk.Radiobutton(
        state_frame,
        text="候補として登録",
        variable=trivia_save_mode,
        value="候補として登録",
    ).pack(side="left", padx=(0, 12))
    ttk.Radiobutton(
        state_frame,
        text="確認済みとして登録",
        variable=trivia_save_mode,
        value="確認済みとして登録",
    ).pack(side="left")

    ttk.Label(manual_tab, text="実況・豆知識本文").grid(row=10, column=0, sticky="nw", pady=3)
    trivia_text = tk.Text(manual_tab, height=9, wrap="word")
    trivia_text.grid(row=10, column=1, sticky="nsew", pady=3)

    help_box = ttk.LabelFrame(manual_tab, text="入力ヘルプ", padding=10)
    help_box.grid(row=0, column=2, rowspan=11, sticky="nsew", padx=(14, 0))
    ttk.Label(
        help_box,
        textvariable=trivia_help,
        justify="left",
        wraplength=300,
    ).pack(anchor="nw")

    def split(value: str) -> tuple[str, ...]:
        return tuple(x.strip() for x in value.split(",") if x.strip())

    def clear_trivia_form() -> None:
        trivia_editing_id["value"] = None
        trivia_existing_source_ref["value"] = None
        trivia_title.set("")
        trivia_tags.set("")
        trivia_entities.set("")
        trivia_from.set("")
        trivia_to.set("")
        trivia_text.delete("1.0", "end")
        trivia_save_mode.set("候補として登録")
        trivia_source_mode.set(SOURCE_MODE_MANUAL_JA)
        trivia_source_url.set("")
        sync_trivia_source()
        category_display.set(TRIVIA_CATEGORIES["GENERAL"])
        trivia_category.set("GENERAL")
        env_display.set(ENVIRONMENT_JA[PerkEnvironment.LIVE])
        trivia_env.set("LIVE")
        for var in event_vars.values():
            var.set(False)

    def source_ref_for_trivia_save() -> str:
        existing = trivia_existing_source_ref["value"]
        if (
            trivia_editing_id["value"]
            and isinstance(existing, str)
            and existing
            and not existing.startswith(("http://", "https://", "manual://"))
        ):
            return existing
        return compose_source_ref(
            trivia_source_mode.get(),
            trivia_source_url.get(),
        )

    def save_trivia_form() -> None:
        try:
            game_version_from, game_version_to = validate_game_version_range(
                trivia_from.get(),
                trivia_to.get(),
            )
            source_ref = source_ref_for_trivia_save()
            events = tuple(
                sorted(
                    (event for event,var in event_vars.items() if var.get()),
                    key=lambda x:x.value,
                )
            )
            verify = trivia_save_mode.get() == "確認済みとして登録"
            editing_id = trivia_editing_id["value"]
            if editing_id:
                workspace.trivia.revise(
                    editing_id,
                    title=trivia_title.get(),
                    text=trivia_text.get("1.0", "end").strip(),
                    source_ref=source_ref,
                    category=trivia_category.get(),
                    tags=split(trivia_tags.get()),
                    event_types=events,
                    entity_refs=split(trivia_entities.get()),
                    environment=PerkEnvironment(trivia_env.get()),
                    game_version_from=game_version_from,
                    game_version_to=game_version_to,
                    verify=verify,
                )
                message = "実況・豆知識を新しい履歴版として保存しました。"
            else:
                workspace.trivia.create_manual(
                    title=trivia_title.get(),
                    text=trivia_text.get("1.0", "end").strip(),
                    source_ref=source_ref,
                    category=trivia_category.get(),
                    tags=split(trivia_tags.get()),
                    event_types=events,
                    entity_refs=split(trivia_entities.get()),
                    environment=PerkEnvironment(trivia_env.get()),
                    game_version_from=game_version_from,
                    game_version_to=game_version_to,
                    verify=verify,
                )
                message = "実況・豆知識を登録しました。"
            clear_trivia_form()
            refresh_trivia_list()
            messagebox.showinfo("実況・豆知識", message)
        except TrainingFieldValidationError as exc:
            messagebox.showerror(
                "入力内容を確認してください",
                f"{exc.field_ja}の入力内容に問題があります。\n\n"
                f"{exc.guidance_ja}\n\n"
                f"入力値: {exc.value or '（空欄）'}",
            )
        except Exception as exc:
            show_operation_error(
                "実況・豆知識を保存できませんでした",
                "ERR_DBD_TRIVIA_REGISTER",
                "実況・豆知識を保存できませんでした。",
                "タイトル、本文、カテゴリ、対象環境、情報源を確認してください。",
                exc,
            )

    manual_buttons = ttk.Frame(manual_tab)
    manual_buttons.grid(row=11, column=1, sticky="w", pady=8)
    ttk.Button(
        manual_buttons,
        text="保存",
        command=save_trivia_form,
    ).pack(side="left", padx=(0, 6))
    ttk.Button(
        manual_buttons,
        text="入力をクリア",
        command=clear_trivia_form,
    ).pack(side="left")

    # Video candidate mining ---------------------------------------------------
    trivia_video = tk.StringVar()
    trivia_frame = tk.StringVar(value="0")
    trivia_model = tk.StringVar(value=active_runtime.default_whisper_model or "small")
    trivia_device = tk.StringVar(value=active_runtime.device or "auto")
    trivia_compute = tk.StringVar(value=active_runtime.compute_type or "int8")
    trivia_language = tk.StringVar(value="ja")
    trivia_allow_download = tk.BooleanVar(value=False)

    mining_tab.columnconfigure(0, weight=1)
    mining_tab.rowconfigure(0, weight=1)
    mining_paned = ttk.Panedwindow(mining_tab, orient="vertical")
    mining_paned.grid(row=0, column=0, sticky="nsew")
    mining_media_host = ttk.Frame(mining_paned, padding=8)
    mining_media_host.columnconfigure(0, weight=1); mining_media_host.rowconfigure(0, weight=1)
    mining_form_host = ttk.Frame(mining_paned)
    mining_form_host.columnconfigure(0, weight=1); mining_form_host.rowconfigure(0, weight=1)
    mining_paned.add(mining_media_host, weight=1); mining_paned.add(mining_form_host, weight=1)
    bind_media_minimum_height(mining_paned, media_first=True, minimum_fraction=0.6, minimum_pixels=420)

    def choose_trivia_video() -> None:
        chosen = filedialog.askopenfilename(
            title="実況・ゲームプレイ動画を選択",
            filetypes=[("Video","*.mp4 *.mkv *.mov *.avi *.webm"),("All files","*.*")],
        )
        if chosen:
            trivia_video.set(chosen)

    def trivia_media_header(parent) -> None:
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text="学習元動画（必須）").grid(row=0, column=0, sticky="w")
        ttk.Entry(parent, textvariable=trivia_video).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(parent, text="参照", command=choose_trivia_video).grid(row=0, column=2)
        ttk.Label(
            parent,
            text="通常再生では動画の音声も再生します。巻き戻し・早送り・フレーム送り中は音声をミュートします。",
            wraplength=360,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4,0))

    trivia_player = TkTrainingMediaPlayer(
        mining_media_host,
        root=root,
        source_getter=lambda: trivia_video.get(),
        frame_getter=lambda: int(trivia_frame.get() or "0"),
        frame_setter=lambda value: trivia_frame.set(str(value)),
        status_setter=status.set,
        ffprobe_executable=runtime_ffprobe,
        diagnostics=diagnostics,
        diagnostic_feature="TRIVIA_MINING",
        player_id="trivia-mining-player",
        control_header_builder=trivia_media_header,
    )
    trivia_player.grid(row=0, column=0, sticky="nsew")

    mining_scroll = ScrollableForm(mining_form_host, padding=12)
    mining_scroll.grid(row=0, column=0, sticky="nsew")
    mining_form = mining_scroll.inner
    mining_form.columnconfigure(0, weight=1)
    mining_form.columnconfigure(1, weight=1)
    ttk.Label(
        mining_form,
        text="動画を見ながら位置を確認し、文字起こしから実況・豆知識候補を抽出します。抽出結果は必ず候補のまま保存されます。",
        wraplength=950,
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,8))

    asr = ttk.LabelFrame(mining_form, text="文字起こし詳細設定", padding=8)
    asr.grid(row=1, column=0, columnspan=2, sticky="ew", pady=6)
    for index in range(4):
        asr.columnconfigure(index, weight=1)

    model_map = dict(WHISPER_MODEL_OPTIONS_JA)
    device_map = dict(DEVICE_OPTIONS_JA)
    compute_map = dict(COMPUTE_OPTIONS_JA)
    model_display = tk.StringVar(
        value=display_for_value(model_map, trivia_model.get(), "小（small・推奨）")
    )
    device_display = tk.StringVar(
        value=display_for_value(device_map, trivia_device.get(), "自動")
    )
    compute_display = tk.StringVar(
        value=display_for_value(compute_map, trivia_compute.get(), "省メモリ（int8）")
    )
    language_display = tk.StringVar(value="日本語")
    language_map = {"日本語":"ja", "自動判定":""}

    ttk.Combobox(asr,textvariable=model_display,values=list(model_map),state="readonly").grid(row=0,column=0,sticky="ew",padx=(0,3))
    ttk.Combobox(asr,textvariable=device_display,values=list(device_map),state="readonly").grid(row=0,column=1,sticky="ew",padx=3)
    ttk.Combobox(asr,textvariable=compute_display,values=list(compute_map),state="readonly").grid(row=0,column=2,sticky="ew",padx=3)
    ttk.Combobox(asr,textvariable=language_display,values=list(language_map),state="readonly").grid(row=0,column=3,sticky="ew",padx=(3,0))
    ttk.Label(asr,text="モデル / デバイス / 計算方式 / 言語",anchor="center").grid(row=1,column=0,columnspan=4,sticky="ew")
    ttk.Label(
        asr,
        text=f"モデルキャッシュ: {runtime_model_cache or '自動'}",
        foreground="#555555",
    ).grid(row=2,column=0,columnspan=4,sticky="w",pady=(4,0))

    def sync_asr_values() -> None:
        trivia_model.set(model_map[model_display.get()])
        trivia_device.set(device_map[device_display.get()])
        trivia_compute.set(compute_map[compute_display.get()])
        trivia_language.set(language_map[language_display.get()])

    ttk.Checkbutton(
        mining_form,
        text="必要なFasterWhisperモデルが無い場合は自動取得を許可",
        variable=trivia_allow_download,
    ).grid(row=3, column=0, columnspan=2, sticky="w", pady=3)

    def mine_trivia_video() -> None:
        video = trivia_video.get().strip()
        if not video:
            messagebox.showerror("動画から候補を抽出", "先に動画を選択してください。")
            return
        sync_asr_values()
        def done(report) -> None:
            refresh_trivia_list()
            trivia_notebook.select(list_tab)
            status.set(f"動画から候補を抽出: {report.mined_candidates}件")
            messagebox.showinfo(
                "動画から候補を抽出",
                f"候補を{report.mined_candidates}件抽出しました。\n\n"
                f"文字起こし: {report.transcript_path}\n"
                f"字幕: {report.subtitle_path}\n\n"
                "抽出候補は確認済みにはなりません。登録済み・候補一覧で確認してください。",
            )
        run_background(
            "動画から候補を抽出",
            lambda: workspace.mine_trivia_from_video(
                video_path=video, model=trivia_model.get(), device=trivia_device.get(),
                compute_type=trivia_compute.get(), language=trivia_language.get() or None,
                allow_model_download=trivia_allow_download.get(),
                cache_directory=runtime_model_cache,
            ),
            done,
        )

    def mine_trivia_transcript() -> None:
        chosen = filedialog.askopenfilename(
            title="既存の文字起こしJSONを選択",
            filetypes=[("JSON","*.json"),("All files","*.*")],
        )
        if not chosen:
            return
        def done(count) -> None:
            refresh_trivia_list(); trivia_notebook.select(list_tab)
            status.set(f"既存文字起こしから候補を抽出: {count}件")
            messagebox.showinfo("既存文字起こしから候補を抽出", f"候補を{count}件抽出しました。\n候補は自動的に確認済みにはなりません。")
        run_background("既存文字起こしから候補を抽出", lambda: workspace.mine_trivia_from_transcript(chosen), done)

    mining_buttons = ttk.Frame(mining_form)
    mining_buttons.grid(row=4, column=0, columnspan=2, sticky="w", pady=8)
    ttk.Button(mining_buttons,text="動画を文字起こしして候補を抽出",command=mine_trivia_video).pack(side="left",padx=(0,6))
    ttk.Button(mining_buttons,text="既存の文字起こしデータから候補を抽出",command=mine_trivia_transcript).pack(side="left")

    # Registered / candidate list ---------------------------------------------
    status_display = tk.StringVar(value="すべて")
    status_filter_map = {
        "すべて":None,
        "候補":TriviaStatus.CANDIDATE,
        "確認済み":TriviaStatus.VERIFIED,
        "却下":TriviaStatus.REJECTED,
        "削除済み":TriviaStatus.SUPERSEDED,
    }
    status_ja = {
        TriviaStatus.CANDIDATE:"候補",
        TriviaStatus.VERIFIED:"確認済み",
        TriviaStatus.REJECTED:"却下",
        TriviaStatus.SUPERSEDED:"削除済み",
    }
    source_kind_ja = {
        TriviaSourceKind.MANUAL:"手動",
        TriviaSourceKind.COMMENTARY_EXTRACTED:"実況から抽出",
        TriviaSourceKind.TRANSCRIPT_EXTRACTED:"文字起こしから抽出",
        TriviaSourceKind.OFFICIAL:"公式",
        TriviaSourceKind.COMMUNITY_REFERENCE:"コミュニティ参照",
    }

    filter_row = ttk.Frame(list_tab)
    filter_row.grid(row=0, column=0, sticky="ew", pady=(0, 6))
    ttk.Label(filter_row, text="表示").pack(side="left")
    status_combo = ttk.Combobox(
        filter_row,
        textvariable=status_display,
        values=list(status_filter_map),
        state="readonly",
        width=14,
    )
    status_combo.pack(side="left", padx=(6, 12))

    trivia_count = tk.StringVar()
    ttk.Label(filter_row, textvariable=trivia_count).pack(side="left")

    columns = (
        "status","title","body","entities","events","source","time"
    )
    trivia_tree = ttk.Treeview(
        list_tab,
        columns=columns,
        show="headings",
        height=12,
    )
    for key,title,width in (
        ("status","状態",90),
        ("title","タイトル",200),
        ("body","本文",320),
        ("entities","関連ゲーム要素",200),
        ("events","使用場面",180),
        ("source","情報源・動画",260),
        ("time","時間",120),
    ):
        trivia_tree.heading(key, text=title)
        trivia_tree.column(key, width=width, stretch=True)
    trivia_tree.grid(row=1, column=0, sticky="nsew")

    trivia_rows = []

    def refresh_trivia_list(_event=None) -> None:
        trivia_tree.delete(*trivia_tree.get_children())
        trivia_rows.clear()
        selected_status = status_filter_map.get(status_display.get())
        values = workspace.trivia.list_latest(status=selected_status)
        for entry in values:
            metadata = workspace.trivia_operational.get(entry.trivia_id)
            source = (
                metadata.source_video
                if metadata is not None and metadata.source_video
                else (
                    "手入力"
                    if entry.source_ref == "manual://owner"
                    else entry.source_ref
                )
            )
            events = ", ".join(
                EVENT_TYPE_JA.get(event, event.value)
                for event in entry.event_types
            )
            entities = ", ".join(entry.entity_refs)
            body = entry.text.replace("\n", " ")
            if len(body) > 120:
                body = body[:117] + "..."
            index = len(trivia_rows)
            trivia_rows.append(entry)
            trivia_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    status_ja[entry.status],
                    entry.title,
                    body,
                    entities,
                    events,
                    source,
                    format_time_range(metadata),
                ),
            )
        all_values = workspace.trivia.list_latest()
        candidate_count = sum(
            1 for x in all_values if x.status is TriviaStatus.CANDIDATE
        )
        verified_count = sum(
            1 for x in all_values if x.status is TriviaStatus.VERIFIED
        )
        trivia_count.set(
            f"表示={len(values)}件 / 候補={candidate_count}件 / 確認済み={verified_count}件"
        )

    status_combo.bind("<<ComboboxSelected>>", refresh_trivia_list)

    detail_text = tk.Text(list_tab, height=8, wrap="word", state="disabled")
    detail_text.grid(row=2, column=0, sticky="ew", pady=(6, 0))

    def selected_trivia():
        selected = trivia_tree.selection()
        if not selected:
            return None
        index = int(selected[0])
        return trivia_rows[index] if 0 <= index < len(trivia_rows) else None

    def show_trivia_detail(_event=None) -> None:
        entry = selected_trivia()
        detail_text.configure(state="normal")
        detail_text.delete("1.0", "end")
        if entry is not None:
            metadata = workspace.trivia_operational.get(entry.trivia_id)
            detail_text.insert(
                "1.0",
                f"状態: {status_ja[entry.status]}\n"
                f"取得方法: {source_kind_ja[entry.source_kind]}\n"
                f"タイトル: {entry.title}\n"
                f"本文: {entry.text}\n"
                f"関連ゲーム要素: {', '.join(entry.entity_refs) or 'なし'}\n"
                f"使用場面: {', '.join(EVENT_TYPE_JA.get(x,x.value) for x in entry.event_types) or 'なし'}\n"
                f"情報源: {entry.source_ref}\n"
                f"動画: {(metadata.source_video if metadata else '') or 'なし'}\n"
                f"時間: {format_time_range(metadata) or 'なし'}\n"
                f"Revision: {entry.revision}",
            )
        detail_text.configure(state="disabled")

    trivia_tree.bind("<<TreeviewSelect>>", show_trivia_detail)

    def edit_selected_trivia() -> None:
        entry = selected_trivia()
        if entry is None:
            messagebox.showinfo("実況・豆知識", "編集する項目を選択してください。")
            return
        modal = tk.Toplevel(root)
        modal.title("実況・豆知識を編集")
        modal.transient(root)
        modal.grab_set()
        modal.columnconfigure(1, weight=1)
        title_var = tk.StringVar(value=entry.title)
        category_var = tk.StringVar(value=entry.category)
        tags_var = tk.StringVar(value=", ".join(entry.tags))
        entities_var = tk.StringVar(value=", ".join(entry.entity_refs))
        from_var = tk.StringVar(value=entry.game_version_from or "")
        to_var = tk.StringVar(value=entry.game_version_to or "")
        env_var = tk.StringVar(value=entry.environment.value)
        verify_var = tk.BooleanVar(value=entry.status is TriviaStatus.VERIFIED)
        body_widget = tk.Text(modal, height=9, wrap="word")
        body_widget.insert("1.0", entry.text)
        ttk.Label(modal, text="タイトル").grid(row=0,column=0,sticky="w",padx=10,pady=4)
        ttk.Entry(modal, textvariable=title_var).grid(row=0,column=1,columnspan=2,sticky="ew",padx=10,pady=4)
        ttk.Label(modal, text="カテゴリ").grid(row=1,column=0,sticky="w",padx=10,pady=4)
        ttk.Combobox(modal,textvariable=category_var,values=list(TRIVIA_CATEGORIES),state="readonly").grid(row=1,column=1,columnspan=2,sticky="ew",padx=10,pady=4)
        ttk.Label(modal, text="タグ").grid(row=2,column=0,sticky="w",padx=10,pady=4)
        ttk.Entry(modal,textvariable=tags_var).grid(row=2,column=1,columnspan=2,sticky="ew",padx=10,pady=4)
        ttk.Label(modal, text="関連ゲーム要素").grid(row=3,column=0,sticky="w",padx=10,pady=4)
        ttk.Entry(modal,textvariable=entities_var).grid(row=3,column=1,sticky="ew",padx=10,pady=4)
        def pick_entity_for_modal() -> None:
            def selected(row) -> None:
                values=[x.strip() for x in entities_var.get().split(",") if x.strip()]
                if row.entity_id not in values: values.append(row.entity_id)
                entities_var.set(", ".join(values))
            open_game_element_selector(root,catalog=entity_alias_catalog,title="関連ゲーム要素を選択",on_select=selected,expected_kind=None)
        ttk.Button(modal,text="検索",command=pick_entity_for_modal).grid(row=3,column=2,padx=10,pady=4)
        ttk.Label(modal, text="対象Version").grid(row=4,column=0,sticky="w",padx=10,pady=4)
        version_row=ttk.Frame(modal); version_row.grid(row=4,column=1,columnspan=2,sticky="ew",padx=10,pady=4); version_row.columnconfigure(0,weight=1); version_row.columnconfigure(1,weight=1)
        ttk.Entry(version_row,textvariable=from_var).grid(row=0,column=0,sticky="ew",padx=(0,3)); ttk.Entry(version_row,textvariable=to_var).grid(row=0,column=1,sticky="ew",padx=(3,0))
        ttk.Label(modal,text="対象環境").grid(row=5,column=0,sticky="w",padx=10,pady=4)
        ttk.Combobox(modal,textvariable=env_var,values=[x.value for x in PerkEnvironment],state="readonly").grid(row=5,column=1,columnspan=2,sticky="ew",padx=10,pady=4)
        ttk.Label(modal,text="本文").grid(row=6,column=0,sticky="nw",padx=10,pady=4)
        body_widget.grid(row=6,column=1,columnspan=2,sticky="nsew",padx=10,pady=4)
        ttk.Checkbutton(modal,text="確認済みとして保存",variable=verify_var).grid(row=7,column=1,columnspan=2,sticky="w",padx=10,pady=4)
        def save_modal() -> None:
            try:
                game_from, game_to = validate_game_version_range(from_var.get(), to_var.get())
                workspace.trivia.revise(
                    entry.trivia_id,
                    title=title_var.get(), text=body_widget.get("1.0","end").strip(),
                    source_ref=entry.source_ref, category=category_var.get(),
                    tags=split(tags_var.get()), event_types=entry.event_types,
                    entity_refs=split(entities_var.get()), environment=PerkEnvironment(env_var.get()),
                    game_version_from=game_from, game_version_to=game_to,
                    verify=verify_var.get(),
                )
                modal.destroy(); refresh_trivia_list()
                status.set("実況・豆知識を新しい履歴版として保存しました。")
            except Exception as exc:
                messagebox.showerror("編集できません",f"{type(exc).__name__}: {exc}",parent=modal)
        actions=ttk.Frame(modal); actions.grid(row=8,column=1,columnspan=2,sticky="e",padx=10,pady=10)
        ttk.Button(actions,text="キャンセル",command=modal.destroy).pack(side="left",padx=4)
        ttk.Button(actions,text="保存",command=save_modal).pack(side="left",padx=4)

    def verify_selected_trivia() -> None:
        entry = selected_trivia()
        if entry is None:
            messagebox.showinfo("実況・豆知識","確認済みにする候補を選択してください。")
            return
        if entry.status is TriviaStatus.VERIFIED:
            messagebox.showinfo("実況・豆知識","この項目は既に確認済みです。")
            return
        if not messagebox.askyesno(
            "確認済みにする",
            f"「{entry.title}」を確認済みとして正式登録しますか？",
        ):
            return
        workspace.trivia.verify(entry.trivia_id)
        refresh_trivia_list()

    def reject_selected_trivia() -> None:
        entry = selected_trivia()
        if entry is None:
            return
        if not messagebox.askyesno(
            "候補を却下",
            f"「{entry.title}」を却下しますか？",
        ):
            return
        workspace.trivia.reject(entry.trivia_id)
        refresh_trivia_list()

    def duplicate_selected_trivia() -> None:
        entry = selected_trivia()
        if entry is None:
            return
        duplicated = workspace.trivia.duplicate(entry.trivia_id)
        workspace.trivia_operational.copy(
            entry.trivia_id,
            duplicated.trivia_id,
        )
        refresh_trivia_list()

    def delete_selected_trivia() -> None:
        entry = selected_trivia()
        if entry is None:
            return
        if not messagebox.askyesno(
            "削除確認",
            f"「{entry.title}」を一覧上で削除済みにしますか？\n"
            "監査履歴を守るため、過去Revision自体は消去しません。",
        ):
            return
        workspace.trivia.supersede(entry.trivia_id)
        refresh_trivia_list()

    action_row = ttk.Frame(list_tab)
    action_row.grid(row=3, column=0, sticky="w", pady=8)
    ttk.Button(
        action_row,
        text="詳細・編集",
        command=edit_selected_trivia,
    ).pack(side="left", padx=(0, 6))
    ttk.Button(
        action_row,
        text="確認済みにする",
        command=verify_selected_trivia,
    ).pack(side="left", padx=6)
    ttk.Button(
        action_row,
        text="複製",
        command=duplicate_selected_trivia,
    ).pack(side="left", padx=6)
    ttk.Button(
        action_row,
        text="却下",
        command=reject_selected_trivia,
    ).pack(side="left", padx=6)
    ttk.Button(
        action_row,
        text="削除（履歴は保持）",
        command=delete_selected_trivia,
    ).pack(side="left", padx=6)

    def import_trivia_csv() -> None:
        chosen = filedialog.askopenfilename(
            title="実況・豆知識CSVを選択",
            filetypes=[("CSV","*.csv"),("All files","*.*")],
        )
        if chosen:
            report_message(
                "実況・豆知識CSV取込",
                workspace.import_trivia_csv(chosen),
            )
            refresh_trivia_list()

    ttk.Button(
        manual_buttons,
        text="CSVから一括登録",
        command=import_trivia_csv,
    ).pack(side="left", padx=(6, 0))
    ttk.Label(
        manual_tab,
        text=f"CSVテンプレート: {templates[2]}",
        wraplength=900,
    ).grid(row=12, column=1, sticky="w", pady=(8, 0))

    refresh_trivia_list()

    # ---- HUD Calibration tab --------------------------------------------------
    # Upper pane: calibration inputs/fine tuning only. Lower pane: a horizontal
    # work area with the video preview on the left and transport/profile actions
    # on the right. This keeps the video and its controls visible together.
    calibration_page = ttk.Frame(notebook)
    notebook.add(calibration_page, text="HUD位置を設定")
    calibration_page.columnconfigure(0, weight=1)
    calibration_page.rowconfigure(0, weight=1)

    calibration_paned = ttk.Panedwindow(calibration_page, orient="vertical")
    calibration_paned.grid(row=0, column=0, sticky="nsew")

    calibration_controls_host = ttk.Frame(calibration_paned)
    calibration_controls_host.columnconfigure(0, weight=1)
    calibration_controls_host.rowconfigure(0, weight=1)
    calibration_preview_host = ttk.Frame(calibration_paned)
    calibration_preview_host.columnconfigure(0, weight=1)
    calibration_preview_host.rowconfigure(0, weight=1)
    calibration_paned.add(calibration_controls_host, weight=2)
    calibration_paned.add(calibration_preview_host, weight=3)
    bind_media_minimum_height(
        calibration_paned, media_first=False, minimum_fraction=0.55, minimum_pixels=360
    )

    calibration_media_paned = ttk.Panedwindow(
        calibration_preview_host, orient="horizontal"
    )
    calibration_media_paned.grid(row=0, column=0, sticky="nsew")
    calibration_video_host = ttk.Frame(calibration_media_paned)
    calibration_video_host.columnconfigure(0, weight=1)
    calibration_video_host.rowconfigure(0, weight=1)
    calibration_side_host = ttk.Frame(calibration_media_paned, padding=(8, 0, 0, 0))
    calibration_side_host.columnconfigure(0, weight=1)
    calibration_side_host.rowconfigure(0, weight=1)
    calibration_media_paned.add(calibration_video_host, weight=3)
    calibration_media_paned.add(calibration_side_host, weight=2)

    calibration_scroll_canvas = tk.Canvas(
        calibration_controls_host,
        highlightthickness=0,
        borderwidth=0,
    )
    calibration_vscroll = ttk.Scrollbar(
        calibration_controls_host,
        orient="vertical",
        command=calibration_scroll_canvas.yview,
    )
    calibration_hscroll = ttk.Scrollbar(
        calibration_controls_host,
        orient="horizontal",
        command=calibration_scroll_canvas.xview,
    )
    calibration_scroll_canvas.configure(
        yscrollcommand=calibration_vscroll.set,
        xscrollcommand=calibration_hscroll.set,
    )
    calibration_scroll_canvas.grid(row=0, column=0, sticky="nsew")
    calibration_vscroll.grid(row=0, column=1, sticky="ns")
    calibration_hscroll.grid(row=1, column=0, sticky="ew")

    calibration_tab = ttk.Frame(calibration_scroll_canvas, padding=12)
    calibration_window = calibration_scroll_canvas.create_window(
        (0, 0),
        window=calibration_tab,
        anchor="nw",
    )
    calibration_tab.columnconfigure(1, weight=1)

    def refresh_calibration_scrollregion(_event=None) -> None:
        calibration_scroll_canvas.configure(
            scrollregion=calibration_scroll_canvas.bbox("all")
        )

    def fit_calibration_width(event) -> None:
        requested_width = calibration_tab.winfo_reqwidth()
        calibration_scroll_canvas.itemconfigure(
            calibration_window,
            width=max(event.width, requested_width),
        )
        refresh_calibration_scrollregion()

    def calibration_mousewheel(event) -> None:
        if event.delta == 0:
            return
        direction = -1 if event.delta > 0 else 1
        calibration_scroll_canvas.yview_scroll(direction * 3, "units")

    calibration_tab.bind("<Configure>", refresh_calibration_scrollregion)
    calibration_scroll_canvas.bind("<Configure>", fit_calibration_width)
    calibration_scroll_canvas.bind(
        "<Enter>",
        lambda _event: calibration_scroll_canvas.bind_all(
            "<MouseWheel>",
            calibration_mousewheel,
        ),
    )
    calibration_scroll_canvas.bind(
        "<Leave>",
        lambda _event: calibration_scroll_canvas.unbind_all("<MouseWheel>"),
    )

    calibration_registry = HudProfileRegistry(workspace.root / "hud_profiles")
    calibration_inspector = FFmpegFrameInspector(ffmpeg_executable=runtime_ffmpeg, ffprobe_executable=runtime_ffprobe)
    calibration_vars = {
        "source": tk.StringVar(),
        "frame": tk.StringVar(value="0"),
        "profile_id": tk.StringVar(value="dbd-calibrated-16x9-v1"),
        "profile_version": tk.StringVar(value="1"),
        "ui_scale": tk.StringVar(value="100"),
        "game_from": tk.StringVar(),
        "game_to": tk.StringVar(),
        "target": tk.StringVar(value="bottom_right_perks"),
        "loaded_profile": tk.StringVar(),
    }
    calibration_state: dict[str, object] = {
        "preview_path": None,
        "preview_image": None,
        "source_geometry": None,
        "preview_geometry": None,
        "photo": None,
        "raw_photo": None,
        "preview_item": None,
        "display_offset": (0, 0),
        "rois": {},
        "drag_start": None,
    }

    target_ids = [
        "lower_left_survivor_hud", "lower_left_loadout_hud", "upper_right_notifications", "bottom_right_perks",
        *[f"survivor_slot_{i}" for i in range(4)],
        "item_slot", *[f"addon_slot_{i}" for i in range(2)],
        *[f"perk_slot_{i}" for i in range(4)],
        "heartbeat_hud",
        "killer_power_hud",
    ]

    def rois_from_profile(profile: DBDHudRoiProfile) -> dict[str, NormalizedROI]:
        rows = {
            profile.lower_left_survivor_hud.roi_id: profile.lower_left_survivor_hud,
            profile.upper_right_notifications.roi_id: profile.upper_right_notifications,
            profile.bottom_right_perks.roi_id: profile.bottom_right_perks,
        }
        if profile.lower_left_loadout_hud is not None:
            rows[profile.lower_left_loadout_hud.roi_id] = profile.lower_left_loadout_hud
        if profile.item_slot is not None:
            rows[profile.item_slot.roi_id] = profile.item_slot
        rows.update({item.roi_id: item for item in profile.addon_slots})
        rows.update({item.roi_id: item for item in profile.survivor_slots})
        rows.update({item.roi_id: item for item in profile.perk_slots})
        if profile.killer_power_hud is not None:
            rows[profile.killer_power_hud.roi_id] = profile.killer_power_hud
        if profile.heartbeat_hud is not None:
            rows[profile.heartbeat_hud.roi_id] = profile.heartbeat_hud
        return rows

    calibration_state["rois"] = rois_from_profile(DBDHudRoiProfile())
    calibration_state["rois"].setdefault("heartbeat_hud", NormalizedROI("heartbeat_hud", 0.31, 0.63, 0.18, 0.30))
    calibration_state["editor"] = None

    ttk.Label(calibration_tab, text="動画 / 静止画").grid(row=0, column=0, sticky="w", pady=3)
    ttk.Entry(calibration_tab, textvariable=calibration_vars["source"]).grid(row=0, column=1, sticky="ew", pady=3)
    def choose_calibration_source() -> None:
        chosen = filedialog.askopenfilename(
            title="DbD動画または静止画を選択",
            filetypes=[("Media", "*.mp4 *.mkv *.mov *.avi *.webm *.png *.jpg *.jpeg *.bmp *.pgm"), ("All files", "*.*")],
        )
        if chosen:
            calibration_vars["source"].set(chosen)
    ttk.Button(calibration_tab, text="参照", command=choose_calibration_source).grid(row=0, column=2, padx=(8, 0))

    ttk.Label(calibration_tab, text="フレーム位置（静止画は0）").grid(row=1, column=0, sticky="w", pady=3)
    ttk.Entry(calibration_tab, textvariable=calibration_vars["frame"]).grid(row=1, column=1, sticky="ew", pady=3)

    profile_meta = ttk.Frame(calibration_tab); profile_meta.grid(row=2, column=0, columnspan=3, sticky="ew", pady=3)
    for idx in range(6): profile_meta.columnconfigure(idx, weight=1)
    for idx, (label, key) in enumerate((("Profile ID", "profile_id"), ("Version", "profile_version"), ("UI Scale %", "ui_scale"), ("Game from", "game_from"), ("Game to", "game_to"))):
        ttk.Label(profile_meta, text=label).grid(row=0, column=idx, sticky="w", padx=(0, 4))
        ttk.Entry(profile_meta, textvariable=calibration_vars[key], width=18).grid(row=1, column=idx, sticky="ew", padx=(0, 6))

    target_row = ttk.Frame(calibration_tab); target_row.grid(row=3, column=0, columnspan=3, sticky="ew", pady=4)
    ttk.Label(target_row, text="調整する場所").pack(side="left")
    target_display_to_id = {ROI_DISPLAY_JA.get(item, item): item for item in target_ids}
    target_display_var = tk.StringVar(value=ROI_DISPLAY_JA.get(calibration_vars["target"].get(), calibration_vars["target"].get()))
    target_combo = ttk.Combobox(target_row, textvariable=target_display_var, values=list(target_display_to_id), state="readonly", width=34)
    target_combo.pack(side="left", padx=8)
    ttk.Label(target_row, text="ドラッグまたは1px/5px微調整で合わせます。").pack(side="left", padx=8)

    fine = ttk.LabelFrame(calibration_tab, text="位置の微調整", padding=8)
    fine.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(4, 4))
    fine.columnconfigure(0, weight=1)
    fine.columnconfigure(1, weight=1)

    # Left column: position, size, movement and history.
    move_panel = ttk.LabelFrame(fine, text="位置を移動", padding=8)
    move_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    move_panel.columnconfigure(0, weight=1)
    move_panel.columnconfigure(1, weight=1)

    xywh_vars = {name: tk.StringVar(value="") for name in ("x", "y", "w", "h")}
    xywh_grid = ttk.Frame(move_panel)
    xywh_grid.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
    for idx in range(4):
        xywh_grid.columnconfigure(idx * 2 + 1, weight=1)
    for col, (label, key) in enumerate((("X","x"),("Y","y"),("W","w"),("H","h"))):
        ttk.Label(xywh_grid, text=label).grid(row=0, column=col*2, padx=(0,2))
        ttk.Entry(xywh_grid, textvariable=xywh_vars[key], width=7).grid(
            row=0,
            column=col*2+1,
            sticky="ew",
            padx=(0,6),
        )

    def active_editor() -> RoiPixelEditor:
        editor = calibration_state.get("editor")
        if editor is None:
            raise ValueError("先にプレビューを表示してください。")
        return editor

    def ensure_selected_roi_ready() -> bool:
        editor = active_editor()
        roi_id = calibration_vars["target"].get()
        created = ensure_optional_roi_initialized(editor, roi_id)
        if created:
            calibration_state["rois"] = editor.rois
            status.set(
                f"{ROI_DISPLAY_JA.get(roi_id, roi_id)} は未設定だったため、"
                "中央に仮の初期範囲を作成しました。プレビューを見ながら調整してください。"
            )
        return created

    def refresh_roi_xywh() -> None:
        try:
            rect = active_editor().pixel_rect(calibration_vars["target"].get())
        except Exception:
            for var in xywh_vars.values():
                var.set("")
            return
        xywh_vars["x"].set(str(rect.x))
        xywh_vars["y"].set(str(rect.y))
        xywh_vars["w"].set(str(rect.width))
        xywh_vars["h"].set(str(rect.height))

    def sync_editor() -> None:
        calibration_state["rois"] = active_editor().rois
        refresh_roi_xywh()
        redraw_calibration_overlay()

    def apply_xywh() -> None:
        try:
            ensure_selected_roi_ready()
            active_editor().set_pixel_rect(
                calibration_vars["target"].get(),
                PixelRect(
                    int(xywh_vars["x"].get()),
                    int(xywh_vars["y"].get()),
                    int(xywh_vars["w"].get()),
                    int(xywh_vars["h"].get()),
                ),
            )
            sync_editor()
        except Exception as exc:
            show_operation_error(
                'HUD位置を設定',
                'ERR_DBD_HUD_CALIBRATION_EDIT',
                'HUD位置の調整処理を完了できませんでした。',
                '動画プレビュー、選択ROI、X/Y/W/Hの値を確認してください。',
                exc,
            )

    ttk.Button(
        move_panel,
        text="X / Y / W / H を適用",
        command=apply_xywh,
    ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

    def move_selected(dx=0, dy=0) -> None:
        try:
            ensure_selected_roi_ready()
            active_editor().move(
                calibration_vars["target"].get(),
                dx_px=dx,
                dy_px=dy,
            )
            sync_editor()
        except Exception as exc:
            show_operation_error(
                'HUD位置を設定',
                'ERR_DBD_HUD_CALIBRATION_EDIT',
                'HUD位置の調整処理を完了できませんでした。',
                '動画プレビュー、選択ROI、X/Y/W/Hの値を確認してください。',
                exc,
            )

    move_buttons = (
        ("← 5px", -5, 0), ("← 1px", -1, 0),
        ("↑ 5px", 0, -5), ("↑ 1px", 0, -1),
        ("↓ 1px", 0, 1), ("↓ 5px", 0, 5),
        ("→ 1px", 1, 0), ("→ 5px", 5, 0),
    )
    for idx, (label, dx, dy) in enumerate(move_buttons):
        ttk.Button(
            move_panel,
            text=label,
            command=lambda dx=dx,dy=dy: move_selected(dx,dy),
        ).grid(
            row=2 + idx // 2,
            column=idx % 2,
            sticky="ew",
            padx=(0,4) if idx % 2 == 0 else (4,0),
            pady=2,
        )

    history_row = ttk.Frame(move_panel)
    history_row.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8, 0))
    for idx in range(3):
        history_row.columnconfigure(idx, weight=1)

    def hist_action(name):
        try:
            ed = active_editor()
            if name == "undo":
                ed.undo()
            elif name == "redo":
                ed.redo()
            else:
                ed.reset(calibration_vars["target"].get())
            sync_editor()
        except Exception as exc:
            show_operation_error(
                'HUD位置を設定',
                'ERR_DBD_HUD_CALIBRATION_EDIT',
                'HUD位置の調整処理を完了できませんでした。',
                '動画プレビュー、選択ROI、X/Y/W/Hの値を確認してください。',
                exc,
            )

    ttk.Button(
        history_row,
        text="元に戻す",
        command=lambda:hist_action("undo"),
    ).grid(row=0,column=0,sticky="ew",padx=(0,3))
    ttk.Button(
        history_row,
        text="やり直す",
        command=lambda:hist_action("redo"),
    ).grid(row=0,column=1,sticky="ew",padx=3)
    ttk.Button(
        history_row,
        text="初期位置へ",
        command=lambda:hist_action("reset"),
    ).grid(row=0,column=2,sticky="ew",padx=(3,0))

    # Right column: edge adjustment.
    edge_panel = ttk.LabelFrame(fine, text="範囲の辺を調整", padding=8)
    edge_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    edge_panel.columnconfigure(0, weight=1)
    edge_panel.columnconfigure(1, weight=1)

    def edge_selected(edge, delta) -> None:
        kwargs = {
            "left":{"left_delta_px":delta},
            "top":{"top_delta_px":delta},
            "right":{"right_delta_px":delta},
            "bottom":{"bottom_delta_px":delta},
        }[edge]
        try:
            ensure_selected_roi_ready()
            active_editor().adjust_edges(
                calibration_vars["target"].get(),
                **kwargs,
            )
            sync_editor()
        except Exception as exc:
            show_operation_error(
                'HUD位置を設定',
                'ERR_DBD_HUD_CALIBRATION_EDIT',
                'HUD位置の調整処理を完了できませんでした。',
                '動画プレビュー、選択ROI、X/Y/W/Hの値を確認してください。',
                exc,
            )

    edge_buttons = (
        ("左辺 -1", "left", -1), ("左辺 +1", "left", 1),
        ("上辺 -1", "top", -1), ("上辺 +1", "top", 1),
        ("右辺 -1", "right", -1), ("右辺 +1", "right", 1),
        ("下辺 -1", "bottom", -1), ("下辺 +1", "bottom", 1),
    )
    for idx, (label, edge, delta) in enumerate(edge_buttons):
        ttk.Button(
            edge_panel,
            text=label,
            command=lambda e=edge,d=delta: edge_selected(e,d),
        ).grid(
            row=idx // 2,
            column=idx % 2,
            sticky="ew",
            padx=(0,4) if idx % 2 == 0 else (4,0),
            pady=2,
        )

    def select_target(_event=None):
        roi_id = target_display_to_id.get(target_display_var.get())
        if roi_id:
            calibration_vars["target"].set(roi_id)
            if calibration_state.get("editor") is not None:
                ensure_selected_roi_ready()
            refresh_roi_xywh()
            redraw_calibration_overlay()
    target_combo.bind("<<ComboboxSelected>>", select_target)

    # Lower-right operation area. The lower pane itself is split horizontally:
    # video preview on the left, video transport + HUD profile actions on right.
    calibration_ops = ttk.Frame(calibration_side_host)
    calibration_ops.grid(row=0, column=0, sticky="nsew")
    calibration_ops.columnconfigure(0, weight=1)

    seek = ttk.Frame(calibration_ops)
    seek.grid(row=0, column=0, sticky="new", pady=(0, 8))
    seek.columnconfigure(0, weight=1)
    calibration_transport_host = seek

    profile_actions = ttk.LabelFrame(
        calibration_ops,
        text="HUDプロファイル",
        padding=8,
    )
    profile_actions.grid(row=1, column=0, sticky="new")
    profile_actions.columnconfigure(0, weight=1)
    profile_actions.columnconfigure(1, weight=1)
    calibration_audio = ttk.LabelFrame(calibration_ops, text="音声", padding=8)
    calibration_audio.grid(row=2, column=0, sticky="new", pady=(8, 0))
    calibration_audio.columnconfigure(1, weight=1)
    calibration_volume = tk.IntVar(value=80)
    calibration_mute = tk.BooleanVar(value=False)
    ttk.Label(calibration_audio, text="🔊").grid(row=0, column=0, padx=(0,4))
    calibration_volume_scale = ttk.Scale(calibration_audio, from_=0, to=100, orient="horizontal", variable=calibration_volume)
    calibration_volume_scale.grid(row=0, column=1, sticky="ew")
    calibration_volume_text = ttk.Label(calibration_audio, text="80%", width=5)
    calibration_volume_text.grid(row=0, column=2, padx=4)

    preview_canvas_frame = ttk.Frame(calibration_video_host)
    preview_canvas_frame.grid(row=0, column=0, sticky="nsew")
    preview_canvas_frame.columnconfigure(0, weight=1)
    preview_canvas_frame.rowconfigure(0, weight=1)

    calibration_canvas = tk.Canvas(
        preview_canvas_frame,
        width=960,
        height=540,
        background="black",
        highlightthickness=1,
    )
    calibration_preview_vscroll = ttk.Scrollbar(
        preview_canvas_frame,
        orient="vertical",
        command=calibration_canvas.yview,
    )
    calibration_preview_hscroll = ttk.Scrollbar(
        preview_canvas_frame,
        orient="horizontal",
        command=calibration_canvas.xview,
    )
    calibration_canvas.configure(
        yscrollcommand=calibration_preview_vscroll.set,
        xscrollcommand=calibration_preview_hscroll.set,
    )
    calibration_canvas.grid(row=0, column=0, sticky="nsew")
    calibration_preview_vscroll.grid(row=0, column=1, sticky="ns")
    calibration_preview_hscroll.grid(row=1, column=0, sticky="ew")

    def redraw_calibration_overlay() -> None:
        calibration_canvas.delete("roi")
        geom = calibration_state.get("preview_geometry")
        if geom is None:
            return
        offset_x, offset_y = calibration_state.get("display_offset", (0, 0))
        width, height = geom.width, geom.height
        rois = calibration_state["rois"]
        for roi_id, roi in sorted(rois.items()):
            x1, y1 = offset_x + roi.x * width, offset_y + roi.y * height
            x2, y2 = offset_x + (roi.x + roi.width) * width, offset_y + (roi.y + roi.height) * height
            selected = roi_id == calibration_vars["target"].get()
            calibration_canvas.create_rectangle(
                x1, y1, x2, y2,
                outline="white" if selected else "#777777",
                width=3 if selected else 1, tags="roi",
            )
            calibration_canvas.create_text(
                x1 + 3, y1 + 3, text=ROI_DISPLAY_JA.get(roi_id, roi_id),
                anchor="nw", fill="white" if selected else "#999999", tags="roi",
            )

    def refit_calibration_preview(_event=None) -> None:
        raw_photo = calibration_state.get("raw_photo")
        if raw_photo is None:
            return
        viewport_width = max(160, calibration_canvas.winfo_width())
        viewport_height = max(90, calibration_canvas.winfo_height())
        raw_width, raw_height = raw_photo.width(), raw_photo.height()
        factor = max(
            1,
            int(max(
                (raw_width + viewport_width - 1) // viewport_width,
                (raw_height + viewport_height - 1) // viewport_height,
            )),
        )
        photo = raw_photo if factor == 1 else raw_photo.subsample(factor, factor)
        display_width, display_height = photo.width(), photo.height()
        offset_x = max(0, (viewport_width - display_width) // 2)
        offset_y = max(0, (viewport_height - display_height) // 2)
        calibration_state["photo"] = photo
        calibration_state["preview_geometry"] = PreviewGeometry(display_width, display_height)
        calibration_state["display_offset"] = (offset_x, offset_y)
        preview_item = calibration_state.get("preview_item")
        if preview_item is None:
            preview_item = calibration_canvas.create_image(
                offset_x, offset_y, image=photo, anchor="nw", tags="preview"
            )
            calibration_state["preview_item"] = preview_item
        else:
            calibration_canvas.coords(preview_item, offset_x, offset_y)
            calibration_canvas.itemconfigure(preview_item, image=photo)
        redraw_calibration_overlay()
        refresh_roi_xywh()
        calibration_canvas.configure(scrollregion=(0, 0, viewport_width, viewport_height))

    def apply_calibration_memory_preview(frame: PersistentPreviewFrame) -> None:
        """Paint a decoded frame on Tk without subprocess or preview-file I/O."""
        if Path(frame.source) != Path(calibration_vars["source"].get().strip()):
            diagnostics.emit(
                "FRAME_UI_STALE_SOURCE",
                feature="HUD_CALIBRATION",
                player_id="hud-calibration-player",
                source=frame.source,
            )
            return
        context = {
            "feature": "HUD_CALIBRATION",
            "player_id": "hud-calibration-player",
            "source": frame.source,
            "frame_index": frame.frame_index,
        }
        diagnostics.emit("TK_IMAGE_CREATE_STARTED", **context)
        try:
            photo = tk.PhotoImage(data=frame.tk_photo_data())
        except Exception as exc:
            diagnostics.exception("TK_IMAGE_CREATE_FAILED", exc, **context)
            raise
        diagnostics.emit(
            "TK_IMAGE_CREATED",
            image_width=photo.width(),
            image_height=photo.height(),
            **context,
        )
        source_geometry = frame.source_geometry
        preview_geometry = frame.preview_geometry
        calibration_state.update({
            "preview_path": None,
            "preview_image": GrayImage(
                preview_geometry.width, preview_geometry.height, frame.pixels
            ),
            "source_geometry": source_geometry,
            "preview_geometry": preview_geometry,
            "raw_photo": photo,
            "photo": photo,
        })
        calibration_state["editor"] = RoiPixelEditor(
            source_width=source_geometry.width,
            source_height=source_geometry.height,
            rois=calibration_state["rois"],
        )
        diagnostics.emit("TK_WIDGET_UPDATE_STARTED", **context)
        refit_calibration_preview()
        refresh_calibration_scrollregion()
        status.set(
            f"HUD位置を設定: {source_geometry.width}x{source_geometry.height} "
            f"frame={frame.frame_index}"
        )
        diagnostics.emit("TK_FRAME_PAINTED", **context)

    calibration_video_session = TkTrainingMediaSession(
        root=root,
        source_getter=lambda: calibration_vars["source"].get(),
        frame_getter=lambda: int(calibration_vars["frame"].get() or "0"),
        frame_setter=lambda value: calibration_vars["frame"].set(str(value)),
        on_frame=apply_calibration_memory_preview,
        status_setter=status.set,
        diagnostics=diagnostics,
        diagnostic_feature="HUD_CALIBRATION",
        player_id="hud-calibration-player",
    )

    calibration_fit_after = {"id": None}

    def schedule_calibration_decoder_fit(_event=None) -> None:
        after_id = calibration_fit_after.get("id")
        if after_id is not None:
            try:
                root.after_cancel(after_id)
            except Exception:
                pass

        def apply_bounds() -> None:
            calibration_fit_after["id"] = None
            calibration_video_session.set_preview_bounds(
                max(320, calibration_canvas.winfo_width()),
                max(180, calibration_canvas.winfo_height()),
                refresh=True,
            )

        calibration_fit_after["id"] = root.after(120, apply_bounds)

    def commit_calibration_volume(_event=None) -> None:
        value = int(round(calibration_volume.get()))
        calibration_volume_text.configure(text=f"{value}%")
        calibration_video_session.set_volume(value)

    def commit_calibration_mute() -> None:
        calibration_video_session.set_muted(bool(calibration_mute.get()))

    calibration_volume_scale.configure(command=lambda _value: calibration_volume_text.configure(text=f"{int(round(calibration_volume.get()))}%"))
    calibration_volume_scale.bind("<ButtonRelease-1>", commit_calibration_volume)
    ttk.Checkbutton(calibration_audio, text="ミュート", variable=calibration_mute, command=commit_calibration_mute).grid(row=0, column=3, padx=(6,0))

    def load_calibration_preview() -> None:
        source = calibration_vars["source"].get().strip()
        if not source:
            messagebox.showerror(
                "HUD位置を設定", "先に動画または静止画を選択してください。"
            )
            return
        try:
            frame_index = int(calibration_vars["frame"].get())
        except ValueError:
            messagebox.showerror("HUD位置を設定", "フレーム番号を整数で入力してください。")
            return
        status.set("HUD動画プレビューを読み込み中…")
        calibration_video_session.request_frame(frame_index)

    calibration_transport_bar = calibration_video_session.create_transport(
        calibration_transport_host,
        title="動画操作",
    )
    calibration_transport_bar.grid(row=0, column=0, sticky="ew")

    def calibration_press(event) -> None:
        calibration_state["drag_start"] = (event.x, event.y)

    def calibration_release(event) -> None:
        start = calibration_state.get("drag_start")
        geom = calibration_state.get("preview_geometry")
        if start is None or geom is None:
            return
        offset_x, offset_y = calibration_state.get("display_offset", (0, 0))
        x1, y1 = start[0] - offset_x, start[1] - offset_y
        x2, y2 = event.x - offset_x, event.y - offset_y
        left, top = max(0, min(x1, x2)), max(0, min(y1, y2))
        right, bottom = min(geom.width, max(x1, x2)), min(geom.height, max(y1, y2))
        if right - left < 4 or bottom - top < 4:
            messagebox.showwarning("HUD位置を設定", "調整範囲はプレビュー上で幅・高さとも4px以上にしてください。"); return
        roi_id = calibration_vars["target"].get()
        source_geom = calibration_state.get("source_geometry")
        try:
            if source_geom is None: raise ValueError("元動画の解像度を確認できません。")
            sx=source_geom.width/geom.width; sy=source_geom.height/geom.height
            active_editor().set_pixel_rect(roi_id, PixelRect(round(left*sx), round(top*sy), max(1,round((right-left)*sx)), max(1,round((bottom-top)*sy))))
            calibration_state["rois"] = active_editor().rois
        except Exception as exc:
            show_operation_error('HUD位置を設定', 'ERR_DBD_HUD_CALIBRATION_EDIT', 'HUD位置の調整処理を完了できませんでした。', '動画プレビュー、選択ROI、X/Y/W/Hの値を確認してください。', exc); return
        calibration_state["drag_start"] = None
        refresh_roi_xywh(); redraw_calibration_overlay()
        status.set(f"HUD位置を更新: {ROI_DISPLAY_JA.get(roi_id, roi_id)}")

    calibration_canvas.bind("<ButtonPress-1>", calibration_press)
    calibration_canvas.bind("<ButtonRelease-1>", calibration_release)
    calibration_canvas.bind("<Configure>", refit_calibration_preview, add="+")
    calibration_canvas.bind("<Configure>", schedule_calibration_decoder_fit, add="+")

    def build_calibrated_profile(*, with_anchors: bool) -> DBDHudRoiProfile:
        geometry = calibration_state.get("source_geometry")
        if geometry is None:
            raise ValueError("Load a calibration preview first")
        rois: dict[str, NormalizedROI] = calibration_state["rois"]
        profile_id = calibration_vars["profile_id"].get().strip()
        ui_text = calibration_vars["ui_scale"].get().strip()
        profile = DBDHudRoiProfile(
            profile_id=profile_id,
            profile_version=int(calibration_vars["profile_version"].get()),
            calibrated_frame_width=geometry.width,
            calibrated_frame_height=geometry.height,
            ui_scale_percent=None if not ui_text else int(ui_text),
            game_version_from=calibration_vars["game_from"].get().strip() or None,
            game_version_to=calibration_vars["game_to"].get().strip() or None,
            calibration_source_ref=calibration_vars["source"].get().strip(),
            anchors=(),
            lower_left_survivor_hud=rois["lower_left_survivor_hud"],
            upper_right_notifications=rois["upper_right_notifications"],
            bottom_right_perks=rois["bottom_right_perks"],
            lower_left_loadout_hud=rois.get("lower_left_loadout_hud"),
            item_slot=rois.get("item_slot"),
            addon_slots=tuple(rois[f"addon_slot_{i}"] for i in range(2)) if all(f"addon_slot_{i}" in rois for i in range(2)) else (),
            survivor_slots=tuple(rois[f"survivor_slot_{i}"] for i in range(4)),
            perk_slots=tuple(rois[f"perk_slot_{i}"] for i in range(4)),
            killer_power_hud=rois.get("killer_power_hud"),
            heartbeat_hud=rois.get("heartbeat_hud"),
        )
        if not with_anchors:
            return profile
        image = calibration_state.get("preview_image")
        if not isinstance(image, GrayImage):
            preview_path = calibration_state.get("preview_path")
            if preview_path is None:
                raise ValueError("Calibration preview is missing")
            image = GrayImage.read_pgm(preview_path)
        anchors = []
        for roi_id in ("lower_left_survivor_hud", "lower_left_loadout_hud", "upper_right_notifications", "bottom_right_perks", "killer_power_hud"):
            roi = rois.get(roi_id)
            if roi is not None:
                anchors.append(calibration_registry.store_anchor(profile_id=profile.profile_id, roi=roi, image=image, source_ref=profile.calibration_source_ref or "manual://hud-calibration"))
        return DBDHudRoiProfile.from_dict({**profile.to_dict(), "anchors": [anchor.to_dict() for anchor in anchors]})

    def refresh_calibration_profiles() -> None:
        profile_ids = [item.profile_id for item in calibration_registry.list_profiles()]
        calibration_profile_combo["values"] = profile_ids
        if profile_ids and not calibration_vars["loaded_profile"].get():
            calibration_vars["loaded_profile"].set(profile_ids[0])

    def save_calibration_profile() -> None:
        try:
            profile = build_calibrated_profile(with_anchors=True)
            path = calibration_registry.save(profile)
        except Exception as exc:
            show_operation_error('HUD Calibration', 'ERR_DBD_HUD_CALIBRATION', 'HUD位置設定の処理を完了できませんでした。', '動画、フレーム位置、HUDプロファイル、FFmpeg/FFprobe設定を確認してください。', exc); return
        refresh_calibration_profiles()
        calibration_vars["loaded_profile"].set(profile.profile_id)
        status.set(f"HUD設定を保存: {profile.profile_id}")
        messagebox.showinfo("HUD位置を設定", f"HUD設定を保存しました:\n{path}\n\nアンカー数: {len(profile.anchors)}")

    def load_calibration_profile() -> None:
        profile_id = calibration_vars["loaded_profile"].get().strip()
        if not profile_id:
            return
        try:
            profile = calibration_registry.load(profile_id)
        except Exception as exc:
            show_operation_error('HUD Calibration', 'ERR_DBD_HUD_CALIBRATION', 'HUD位置設定の処理を完了できませんでした。', '動画、フレーム位置、HUDプロファイル、FFmpeg/FFprobe設定を確認してください。', exc); return
        calibration_vars["profile_id"].set(profile.profile_id)
        calibration_vars["profile_version"].set(str(profile.profile_version))
        calibration_vars["ui_scale"].set("" if profile.ui_scale_percent is None else str(profile.ui_scale_percent))
        calibration_vars["game_from"].set(profile.game_version_from or "")
        calibration_vars["game_to"].set(profile.game_version_to or "")
        loaded_rois = rois_from_profile(profile)
        calibration_state["rois"] = loaded_rois

        # Loading a registered HUD profile starts a new edit session. The
        # previous editor may still contain default/older ROI positions; if it
        # remains attached, the first single-ROI adjustment calls sync_editor()
        # and writes those stale positions back over every non-selected ROI.
        source_geometry = calibration_state.get("source_geometry")
        editor = calibration_state.get("editor")
        if source_geometry is None:
            calibration_state["editor"] = None
        elif (
            editor is None
            or editor.source_width != source_geometry.width
            or editor.source_height != source_geometry.height
        ):
            calibration_state["editor"] = RoiPixelEditor(
                source_width=source_geometry.width,
                source_height=source_geometry.height,
                rois=loaded_rois,
            )
        else:
            editor.rebase(loaded_rois)

        refresh_roi_xywh()
        redraw_calibration_overlay()
        status.set(f"HUD設定を読み込み: {profile.profile_id}")

    def test_profile_resolution_and_anchor() -> None:
        source = calibration_vars["source"].get().strip()
        if not source:
            messagebox.showerror("HUD位置を設定", "先に動画を選択してください。")
            return
        try:
            frame_index = int(calibration_vars["frame"].get())
            ui_text = calibration_vars["ui_scale"].get().strip()
            ui_scale = None if not ui_text else int(ui_text)
            game_version = calibration_vars["game_from"].get().strip() or None
        except Exception as exc:
            show_operation_error(
                "HUD位置を設定", "ERR_DBD_HUD_CALIBRATION_INPUT",
                "自動補正テストの入力を確認できませんでした。",
                "フレーム位置、UI Scale、ゲームバージョンを確認してください。", exc,
            )
            return

        def execute_alignment():
            resolver = DBDHudVideoProfileResolver(
                calibration_registry, inspector=calibration_inspector,
            )
            resolution = resolver.resolve_video(
                video_path=source, frame_index=frame_index,
                ui_scale_percent=ui_scale, game_version=game_version,
            )
            geometry = calibration_inspector.probe_geometry(source)
            alignment = HudAnchorAligner(
                extractor=FFmpegSliceExtractor(runtime_ffmpeg)
            ).align(
                video_path=source, frame_index=frame_index, profile=resolution.profile,
                frame_width=geometry.width, frame_height=geometry.height,
                working_directory=workspace.root / "hud_profiles" / "_alignment-test",
            )
            return resolution, alignment

        def completed(result) -> None:
            resolution, alignment = result
            details = "\n".join(
                f"{item.roi_id}: dx={item.dx_normalized:.6f} "
                f"dy={item.dy_normalized:.6f} confidence={item.confidence_milli}"
                for item in alignment.corrections
            ) or "No anchors/correction required"
            status.set("HUD自動補正テスト: 完了")
            messagebox.showinfo(
                "HUD Profile resolution",
                f"Profile: {resolution.profile.profile_id}\n"
                f"Resolve score: {resolution.score_milli}\n"
                f"Anchor score: {alignment.confidence_milli}\n\n{details}",
            )

        run_background("HUD自動補正テスト", execute_alignment, completed)

    ttk.Button(
        profile_actions,
        text="プレビューを読み込む",
        command=load_calibration_preview,
    ).grid(row=0, column=0, sticky="ew", padx=(0,4), pady=2)
    ttk.Button(
        profile_actions,
        text="HUD設定を保存",
        command=save_calibration_profile,
    ).grid(row=0, column=1, sticky="ew", padx=(4,0), pady=2)
    ttk.Button(
        profile_actions,
        text="自動補正をテスト",
        command=test_profile_resolution_and_anchor,
    ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)

    ttk.Label(
        profile_actions,
        text="登録済みHUD設定",
    ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8,2))
    calibration_profile_combo = ttk.Combobox(
        profile_actions,
        textvariable=calibration_vars["loaded_profile"],
        state="readonly",
        width=34,
    )
    calibration_profile_combo.grid(
        row=3,
        column=0,
        sticky="ew",
        padx=(0,4),
        pady=2,
    )
    ttk.Button(
        profile_actions,
        text="読み込む",
        command=load_calibration_profile,
    ).grid(row=3, column=1, sticky="ew", padx=(4,0), pady=2)
    refresh_calibration_profiles()

    ttk.Label(
        calibration_tab,
        text=(
            "実行時はHUDプロファイルとアンカー補正を安全側で判定します。"
            "一致する設定がない、または補正の信頼度が不足する場合は、"
            "推測せずHUD位置の再設定を求めます。"
        ),
        wraplength=1100,
    ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(6, 0))

    # ---- Knowledge Source Import tab -----------------------------------------
    knowledge_import_tab = ttk.Frame(notebook, padding=12)
    notebook.add(knowledge_import_tab, text="ゲーム情報を取得")
    knowledge_import_tab.columnconfigure(0, weight=1)
    knowledge_import_tab.rowconfigure(4, weight=1)

    ttk.Label(
        knowledge_import_tab,
        text="DbDゲーム情報の取得・確認",
        font=("TkDefaultFont", 11, "bold"),
    ).grid(row=0, column=0, sticky="w", pady=(0, 4))
    ttk.Label(
        knowledge_import_tab,
        text=(
            "取得したHTMLは raw に証跡として保存します。外部攻略情報は『外部参考情報』として保存し、"
            "一覧では『取込候補』として表示します。内容を人が確認して『確認済み』にするまで、"
            "学習の正式な正解情報として自動採用しません。再取得で確認済み内容を勝手に上書きせず、"
            "差分は『更新候補あり』として扱います。"
        ),
        wraplength=1200,
    ).grid(row=1, column=0, sticky="w", pady=(0, 8))

    import_controls = ttk.Frame(knowledge_import_tab)
    import_controls.grid(row=2, column=0, sticky="ew")
    import_controls.columnconfigure(1, weight=1)

    kamigame_output = tk.StringVar(value=str(workspace.root / "knowledge-imports" / "kamigame"))
    kamigame_details = tk.BooleanVar(value=True)
    kamigame_map_details = tk.BooleanVar(value=True)
    kamigame_max_pages = tk.StringVar(value="20")
    kamigame_max_details = tk.StringVar(value="128")
    kamigame_max_map_details = tk.StringVar(value="128")
    kamigame_result = tk.StringVar(value="まだ取得結果を確認していません。")
    kamigame_inventory_status = tk.StringVar(value="候補一覧を読み込んでいます...")

    ttk.Label(import_controls, text="保存先").grid(row=0, column=0, sticky="w", pady=3)
    ttk.Entry(import_controls, textvariable=kamigame_output).grid(
        row=0, column=1, sticky="ew", pady=3, padx=(8, 8)
    )

    def choose_kamigame_output() -> None:
        chosen = filedialog.askdirectory(title="ゲーム情報候補の保存フォルダを選択")
        if chosen:
            kamigame_output.set(chosen)
            refresh_kamigame_inventory()

    ttk.Button(import_controls, text="参照", command=choose_kamigame_output).grid(
        row=0, column=2, sticky="w"
    )
    option_row = ttk.Frame(import_controls)
    option_row.grid(row=1, column=0, sticky="w", pady=3)
    ttk.Checkbutton(option_row,text="キラー詳細ページも取得",variable=kamigame_details).pack(side="left")
    ttk.Checkbutton(option_row,text="マップ詳細・画像も取得",variable=kamigame_map_details).pack(side="left",padx=(12,0))

    limits = ttk.Frame(import_controls)
    limits.grid(row=1, column=1, sticky="w", pady=3, padx=(8, 0))
    ttk.Label(limits, text="一覧上限").pack(side="left")
    ttk.Entry(limits, textvariable=kamigame_max_pages, width=7).pack(side="left", padx=(4, 12))
    ttk.Label(limits, text="キラー詳細上限").pack(side="left")
    ttk.Entry(limits, textvariable=kamigame_max_details, width=7).pack(side="left", padx=(4, 12))
    ttk.Label(limits, text="マップ詳細上限").pack(side="left")
    ttk.Entry(limits, textvariable=kamigame_max_map_details, width=7).pack(side="left", padx=(4, 0))

    ttk.Label(
        knowledge_import_tab,
        textvariable=kamigame_result,
        wraplength=1200,
    ).grid(row=3, column=0, sticky="w", pady=(8, 6))

    inventory_box = ttk.LabelFrame(
        knowledge_import_tab,
        text="取得済みゲーム情報（取込候補 / 確認済み）",
        padding=8,
    )
    inventory_box.grid(row=4, column=0, sticky="nsew", pady=(4, 6))
    inventory_box.columnconfigure(0, weight=1)
    inventory_box.rowconfigure(1, weight=1)

    ttk.Label(
        inventory_box,
        textvariable=kamigame_inventory_status,
    ).grid(row=0, column=0, sticky="w", pady=(0, 6))

    inventory_photos: dict[str, object] = {}

    def _knowledge_thumbnail(path_text: str, max_size: tuple[int, int] = (96, 72), rotation_deg: int = 0):
        path = Path(path_text) if path_text else None
        if path is None or not path.is_file():
            return None
        try:
            from PIL import Image, ImageTk
            with Image.open(path) as opened:
                image = opened.convert("RGBA")
                if rotation_deg % 360:
                    image = image.rotate(-rotation_deg, expand=True)
                image.thumbnail(max_size)
                return ImageTk.PhotoImage(image)
        except Exception:
            try:
                photo = tk.PhotoImage(file=str(path))
                factor = max(1, (max(photo.width() / max_size[0], photo.height() / max_size[1])))
                if factor > 1:
                    photo = photo.subsample(int(factor + 0.999), int(factor + 0.999))
                return photo
            except Exception:
                return None

    inventory_filter_row = ttk.Frame(inventory_box)
    inventory_filter_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 6))
    inventory_filter_row.columnconfigure(3, weight=1)
    inventory_kind_filter = tk.StringVar(value="すべて")
    inventory_keyword_filter = tk.StringVar()
    INVENTORY_KIND_JA = {
        GameKnowledgeKind.PERK:"パーク", GameKnowledgeKind.KILLER:"キラー", GameKnowledgeKind.ITEM:"アイテム",
        GameKnowledgeKind.ADDON:"アドオン", GameKnowledgeKind.MAP:"マップ", GameKnowledgeKind.REALM:"領域",
        GameKnowledgeKind.OFFERING:"オファリング", GameKnowledgeKind.POWER:"能力",
        GameKnowledgeKind.CHARACTER:"キャラクター", GameKnowledgeKind.SURVIVOR:"サバイバー",
        GameKnowledgeKind.KNOWLEDGE:"ナレッジ系", GameKnowledgeKind.TILE:"地形",
        GameKnowledgeKind.STATUS:"状態", GameKnowledgeKind.MECHANIC:"ゲーム仕様",
    }
    inventory_kind_values = ["すべて", *dict.fromkeys(INVENTORY_KIND_JA.values())]
    ttk.Label(inventory_filter_row, text="種別").grid(row=0, column=0, sticky="w")
    inventory_kind_combo = ttk.Combobox(
        inventory_filter_row, textvariable=inventory_kind_filter, values=inventory_kind_values,
        state="readonly", width=16,
    )
    inventory_kind_combo.grid(row=0, column=1, sticky="w", padx=(6, 16))
    ttk.Label(inventory_filter_row, text="キーワード検索").grid(row=0, column=2, sticky="w")
    inventory_keyword_entry = ttk.Entry(inventory_filter_row, textvariable=inventory_keyword_filter)
    inventory_keyword_entry.grid(row=0, column=3, sticky="ew", padx=(6, 0))

    inventory_tree = ttk.Treeview(
        inventory_box,
        columns=("kind", "name", "aliases", "status"),
        show="headings",
        height=14,
    )
    inventory_tree.heading("kind", text="種別")
    inventory_tree.heading("name", text="正式名")
    inventory_tree.heading("aliases", text="略称・通称")
    inventory_tree.heading("status", text="状態")
    inventory_tree.column("kind", width=100, stretch=False)
    inventory_tree.column("name", width=300)
    inventory_tree.column("aliases", width=390)
    inventory_tree.column("status", width=120, stretch=False)
    inventory_scroll = ttk.Scrollbar(inventory_box, orient="vertical", command=inventory_tree.yview)
    inventory_tree.configure(yscrollcommand=inventory_scroll.set)
    inventory_tree.grid(row=2, column=0, sticky="nsew")
    inventory_scroll.grid(row=2, column=1, sticky="ns")
    inventory_box.rowconfigure(2, weight=1)
    inventory_rows = {}
    REVIEW_STATUS_JA = {
        "CANDIDATE": "取込候補", "VERIFIED": "確認済み", "NEEDS_REVIEW": "要再確認",
        "UPDATE_AVAILABLE": "更新候補あり", "REJECTED": "却下", "DISABLED": "無効",
    }

    def _sync_candidate_alias_index(candidate) -> None:
        status = (
            EntityAliasReviewStatus.VERIFIED if candidate.review_status == "VERIFIED"
            else EntityAliasReviewStatus.REJECTED if candidate.review_status in {"REJECTED", "DISABLED"}
            else EntityAliasReviewStatus.CANDIDATE
        )
        records = [EntityAliasRecord(
            entity_id=candidate.candidate_id, knowledge_kind=candidate.knowledge_kind,
            alias_text=candidate.effective_name_ja, alias_type=EntityAliasType.OFFICIAL_NAME,
            priority=100, review_status=status, source_ref=candidate.source_page_url or "manual://owner",
        )]
        if candidate.effective_name_en:
            records.append(EntityAliasRecord(
                entity_id=candidate.candidate_id, knowledge_kind=candidate.knowledge_kind,
                alias_text=candidate.effective_name_en, alias_type=EntityAliasType.OFFICIAL_ENGLISH,
                priority=90, review_status=status, source_ref=candidate.source_page_url or "manual://owner",
            ))
        records.extend(EntityAliasRecord(
            entity_id=candidate.candidate_id, knowledge_kind=candidate.knowledge_kind,
            alias_text=alias, alias_type=EntityAliasType.COMMUNITY_NICKNAME,
            priority=80, review_status=status, source_ref="manual://owner" if candidate.manual_aliases_ja else (candidate.source_page_url or "manual://owner"),
        ) for alias in candidate.effective_aliases_ja)
        entity_alias_catalog.replace_entity_aliases(candidate.candidate_id, candidate.knowledge_kind, records)

    def _sync_map_records_from_catalog() -> None:
        for candidate in game_knowledge_catalog.list(kind=GameKnowledgeKind.MAP):
            details = candidate.details
            try:
                existing = map_intelligence_store.get(candidate.candidate_id)
                rotation, locked, note = existing.rotation_deg, existing.orientation_locked, existing.orientation_note
                offering = existing.offering_name
                features, unique_objects, favorability = existing.features, existing.unique_objects, existing.favorability
            except KeyError:
                rotation, locked, note, offering = 0, False, "", ""
                features = unique_objects = favorability = ""
            map_intelligence_store.upsert(MapRecord(
                map_id=candidate.candidate_id, map_name=candidate.effective_name_ja,
                image_path=candidate.effective_image, realm_name=str(details.get("realm_name_ja") or ""),
                offering_name=offering, features=features, unique_objects=unique_objects, favorability=favorability,
                pallet_text=str(details.get("pallet_text") or ""),
                area_m2=(None if details.get("area_m2") in {None, ""} else int(details["area_m2"])),
                size_class=str(details.get("size_class") or ""), enabled=candidate.enabled,
                rotation_deg=rotation, orientation_locked=locked, orientation_note=note,
            ))

    def refresh_kamigame_inventory() -> None:
        inventory_tree.delete(*inventory_tree.get_children()); inventory_rows.clear()
        out = Path(kamigame_output.get().strip())
        try:
            if out.joinpath("normalized").is_dir():
                sync_kamigame_review_catalog(game_knowledge_catalog, out)
            rows = game_knowledge_catalog.list()
            for candidate in rows:
                _sync_candidate_alias_index(candidate)
            _sync_map_records_from_catalog()
        except Exception as exc:
            kamigame_inventory_status.set(f"候補一覧を読み込めませんでした: {type(exc).__name__}: {exc}")
            return
        selected_kind = inventory_kind_filter.get().strip()
        needle = inventory_keyword_filter.get().strip().casefold()
        visible = []
        for row in rows:
            label = INVENTORY_KIND_JA.get(row.knowledge_kind, row.knowledge_kind.value)
            if selected_kind and selected_kind != "すべて" and label != selected_kind:
                continue
            details_text = " ".join(str(v) for v in row.details.values() if v not in {None, ""})
            hay = "\n".join((
                row.effective_name_ja, row.effective_name_en, *row.effective_aliases_ja,
                row.candidate_id, label, row.source_page_url, details_text,
            )).casefold()
            if needle and needle not in hay:
                continue
            visible.append((row, label))
        counts = {}
        for row, label in visible:
            inventory_rows[row.candidate_id] = row
            counts[label] = counts.get(label, 0) + 1
            inventory_tree.insert(
                "", "end", iid=row.candidate_id,
                values=(label, row.effective_name_ja, ", ".join(row.effective_aliases_ja) if row.effective_aliases_ja else "-", REVIEW_STATUS_JA.get(row.review_status,row.review_status)),
            )
        breakdown = " / ".join(f"{k} {v}" for k,v in sorted(counts.items()))
        kamigame_inventory_status.set(
            f"表示 {len(visible)} / 全{len(rows)}件（{breakdown or '該当なし'}） | 検索用Alias: {entity_alias_catalog.count()}件"
        )

    inventory_kind_combo.bind("<<ComboboxSelected>>", lambda _event: refresh_kamigame_inventory())
    inventory_keyword_entry.bind("<KeyRelease>", lambda _event: refresh_kamigame_inventory())

    def selected_knowledge_candidate():
        sel = inventory_tree.selection()
        return inventory_rows.get(sel[0]) if sel else None

    def edit_knowledge_candidate() -> None:
        row = selected_knowledge_candidate()
        if row is None:
            messagebox.showinfo("ゲーム情報", "編集する一覧行を1件選択してください。")
            return
        modal=tk.Toplevel(root); modal.title("ゲーム情報を編集・詳細確認"); modal.geometry("900x760"); modal.transient(root); modal.grab_set(); modal.columnconfigure(1,weight=1)
        name_ja=tk.StringVar(value=row.effective_name_ja); name_en=tk.StringVar(value=row.effective_name_en)
        aliases=tk.StringVar(value=", ".join(row.effective_aliases_ja)); image_path=tk.StringVar(value=row.effective_image); enabled=tk.BooleanVar(value=row.enabled)
        ttk.Label(modal,text="正式名称").grid(row=0,column=0,sticky="w",padx=10,pady=5); ttk.Entry(modal,textvariable=name_ja,width=52).grid(row=0,column=1,columnspan=2,sticky="ew",padx=10,pady=5)
        ttk.Label(modal,text="英語名").grid(row=1,column=0,sticky="w",padx=10,pady=5); ttk.Entry(modal,textvariable=name_en).grid(row=1,column=1,columnspan=2,sticky="ew",padx=10,pady=5)
        ttk.Label(modal,text="略称・通称").grid(row=2,column=0,sticky="w",padx=10,pady=5); ttk.Entry(modal,textvariable=aliases).grid(row=2,column=1,columnspan=2,sticky="ew",padx=10,pady=5)
        ttk.Label(modal,text="カンマ区切りで複数登録できます。例: アイウィル, 鋼, Iron Will",foreground="#666666").grid(row=3,column=1,columnspan=2,sticky="w",padx=10)

        image_frame=ttk.LabelFrame(modal,text="画像",padding=8); image_frame.grid(row=4,column=0,columnspan=3,sticky="ew",padx=10,pady=6); image_frame.columnconfigure(0,weight=1)
        image_ref={"photo":None}
        image_preview=ttk.Label(image_frame,text="画像なし",anchor="center"); image_preview.grid(row=0,column=0,columnspan=2,sticky="ew")
        image_path_label=ttk.Label(image_frame,textvariable=image_path,foreground="#555555",wraplength=760); image_path_label.grid(row=1,column=0,columnspan=2,sticky="w",pady=(6,4))
        def refresh_edit_image():
            photo=_knowledge_thumbnail(image_path.get(), (520, 260))
            image_ref["photo"]=photo
            image_preview.configure(image=photo or "", text="" if photo else "画像なし")
        def choose_image():
            chosen=filedialog.askopenfilename(title="差し替える画像を選択",filetypes=[("画像","*.png;*.jpg;*.jpeg;*.gif;*.pgm;*.ppm"),("すべて","*.*")])
            if chosen:
                image_path.set(chosen); refresh_edit_image()
        ttk.Button(image_frame,text="画像を差し替える",command=choose_image).grid(row=2,column=0,sticky="w")
        refresh_edit_image()

        details_box=ttk.LabelFrame(modal,text="取得した詳細情報",padding=8); details_box.grid(row=5,column=0,columnspan=3,sticky="nsew",padx=10,pady=6); details_box.columnconfigure(0,weight=1); details_box.rowconfigure(0,weight=1); modal.rowconfigure(5,weight=1)
        details_text=tk.Text(details_box,height=12,wrap="word")
        details_text.grid(row=0,column=0,sticky="nsew")
        detail_lines=[]
        for key,value in sorted(row.details.items()):
            if key.startswith("_"):
                continue
            if isinstance(value,(dict,list,tuple)):
                import json
                rendered=json.dumps(value,ensure_ascii=False,indent=2)
            else:
                rendered=str(value)
            detail_lines.append(f"{key}: {rendered}")
        detail_lines.extend((f"source_page_url: {row.source_page_url}", f"candidate_id: {row.candidate_id}"))
        details_text.insert("1.0","\n\n".join(detail_lines) if detail_lines else "詳細情報はありません。")
        details_text.configure(state="disabled")

        ttk.Checkbutton(modal,text="有効",variable=enabled).grid(row=6,column=1,sticky="w",padx=10,pady=5)
        ttk.Label(modal,text=f"確認状態: {REVIEW_STATUS_JA.get(row.review_status,row.review_status)} / 情報源: 外部参考情報",foreground="#555555").grid(row=7,column=0,columnspan=3,sticky="w",padx=10,pady=(6,2))
        def save_edit():
            try:
                updated=game_knowledge_catalog.edit(row.candidate_id,name_ja=name_ja.get(),name_en=name_en.get(),aliases_ja=aliases.get().split(','),image_path=image_path.get(),enabled=enabled.get())
                _sync_candidate_alias_index(updated)
                modal.destroy(); refresh_kamigame_inventory()
            except Exception as exc: messagebox.showerror("編集できません",f"{type(exc).__name__}: {exc}",parent=modal)
        action=ttk.Frame(modal); action.grid(row=8,column=0,columnspan=3,sticky="e",padx=10,pady=10)
        ttk.Button(action,text="キャンセル",command=modal.destroy).pack(side="left",padx=4); ttk.Button(action,text="保存",command=save_edit).pack(side="left",padx=4)

    def verify_knowledge_candidate() -> None:
        row=selected_knowledge_candidate()
        if row is None:
            messagebox.showinfo("ゲーム情報","確認する一覧行を1件選択してください。"); return
        if messagebox.askyesno("確認済みにする",f"『{row.effective_name_ja}』をTraining Studioの正しいゲーム情報として利用可能にしますか？"):
            updated=game_knowledge_catalog.set_status(row.candidate_id,"VERIFIED")
            _sync_candidate_alias_index(updated); refresh_kamigame_inventory()

    def show_map_detail() -> None:
        row=selected_knowledge_candidate()
        if row is None or row.knowledge_kind is not GameKnowledgeKind.MAP:
            messagebox.showinfo("マップ詳細","マップを1件選択してください。"); return
        record=map_intelligence_store.get(row.candidate_id)
        modal=tk.Toplevel(root); modal.title(f"マップ詳細 — {record.map_name}"); modal.geometry("900x720"); modal.transient(root); modal.grab_set(); modal.columnconfigure(0,weight=1); modal.columnconfigure(1,weight=1); modal.rowconfigure(1,weight=1)
        edit_on=tk.BooleanVar(value=False); rotation=tk.IntVar(value=record.rotation_deg); image_ref={"photo":None}
        image_box=ttk.LabelFrame(modal,text="Canonical Map Image / ↑ 上",padding=8); image_box.grid(row=0,column=0,rowspan=2,sticky="nsew",padx=10,pady=10); image_box.columnconfigure(0,weight=1); image_box.rowconfigure(0,weight=1)
        image_label=ttk.Label(image_box,text="マップ画像なし",anchor="center"); image_label.grid(row=0,column=0,sticky="nsew")
        def refresh_image():
            path=Path(record.image_path) if record.image_path else None
            photo=_knowledge_thumbnail(str(path) if path else "", (430, 430), rotation.get())
            if photo is not None:
                image_ref["photo"]=photo
                image_label.configure(image=photo,text=f"↑ Canonical Up / 表示回転 {rotation.get()}°",compound="top")
            elif path and path.is_file():
                image_label.configure(image="",text=f"画像を表示できません\n{path.name}\n↑ Canonical Up / 回転 {rotation.get()}°")
            else:
                image_label.configure(image="",text=f"画像未登録\n↑ Canonical Up / 回転 {rotation.get()}°")
        refresh_image()
        fields=ttk.Frame(modal); fields.grid(row=0,column=1,sticky="nsew",padx=10,pady=10); fields.columnconfigure(1,weight=1)
        values={
            "realm":tk.StringVar(value=record.realm_name),"offering":tk.StringVar(value=record.offering_name),
            "features":tk.StringVar(value=record.features),"objects":tk.StringVar(value=record.unique_objects),
            "favor":tk.StringVar(value=record.favorability),"pallet":tk.StringVar(value=record.pallet_text),
            "area":tk.StringVar(value="" if record.area_m2 is None else str(record.area_m2)),"size":tk.StringVar(value=record.size_class),
            "note":tk.StringVar(value=record.orientation_note),
        }
        ttk.Label(fields,text="マップ名").grid(row=0,column=0,sticky="w",pady=3); ttk.Label(fields,text=record.map_name,font=("TkDefaultFont",10,"bold")).grid(row=0,column=1,sticky="w",pady=3)
        ttk.Label(
            fields,
            text=(f"Map Image Training準備: Floor {len(record.floors)} / Region {len(record.regions)} / Landmark {len(record.landmarks)}。"
                  "教師データ契約はサバイバー1〜4・キラー視点、正規化u/v、Floor、Headingに対応。"),
            wraplength=420, foreground="#555555",
        ).grid(row=10,column=0,columnspan=2,sticky="w",pady=(8,0))
        for r,(label,key) in enumerate((("領域名","realm"),("オファリング情報","offering"),("特徴","features"),("固有オブジェクト","objects"),("有利度","favor"),("板","pallet"),("面積㎡","area"),("広さ","size"),("上下ロックのメモ","note")),start=1):
            ttk.Label(fields,text=label).grid(row=r,column=0,sticky="w",pady=3); ttk.Entry(fields,textvariable=values[key]).grid(row=r,column=1,sticky="ew",pady=3)
        controls=ttk.Frame(modal); controls.grid(row=2,column=0,columnspan=2,sticky="ew",padx=10,pady=(0,10))
        def rotate_right():
            if edit_on.get(): rotation.set((rotation.get()+90)%360); refresh_image()
        def save_map():
            try:
                area=int(values["area"].get()) if values["area"].get().strip() else None
                current=map_intelligence_store.get(row.candidate_id)
                map_intelligence_store.upsert(MapRecord(
                    map_id=current.map_id,map_name=current.map_name,image_path=current.image_path,realm_name=values["realm"].get(),offering_name=values["offering"].get(),features=values["features"].get(),unique_objects=values["objects"].get(),favorability=values["favor"].get(),pallet_text=values["pallet"].get(),area_m2=area,size_class=values["size"].get(),enabled=current.enabled,rotation_deg=rotation.get(),orientation_locked=not edit_on.get(),orientation_note=values["note"].get(),floors=current.floors,regions=current.regions,landmarks=current.landmarks,
                )); modal.destroy()
            except Exception as exc: messagebox.showerror("マップを保存できません",f"{type(exc).__name__}: {exc}",parent=modal)
        ttk.Checkbutton(controls,text="向きを編集 ON/OFF",variable=edit_on).pack(side="left",padx=(0,8)); ttk.Button(controls,text="↻ 右へ90°",command=rotate_right).pack(side="left",padx=8)
        ttk.Label(controls,text="OFFで保存すると現在の向きをCanonical Upとしてロックします。",foreground="#555555").pack(side="left",padx=8)
        ttk.Button(controls,text="保存して閉じる",command=save_map).pack(side="right")

    def index_kamigame_candidates() -> None:
        out = Path(kamigame_output.get().strip())
        try:
            report = index_kamigame_candidates_for_search(entity_alias_catalog, out)
        except Exception as exc:
            show_operation_error(
                "ゲーム情報を検索用に登録",
                "ERR_DBD_KAMIGAME_ALIAS_INDEX",
                "取得済みゲーム情報を検索用インデックスへ登録できませんでした。",
                "normalized/*.jsonl と検索用Aliasデータベースの状態を確認してください。",
                exc,
            )
            return
        refresh_kamigame_inventory()
        messagebox.showinfo(
            "ゲーム情報",
            (
                f"候補 {report.candidates}件を検索対象として反映しました。\n"
                f"Alias登録 {report.alias_records}件\n\n"
                "状態は『取込候補』のままです。人が確認するまで『確認済み』へ自動昇格しません。"
            ),
        )

    def collect_kamigame() -> None:
        try:
            out = Path(kamigame_output.get().strip())
            max_pages = int(kamigame_max_pages.get())
            max_details = int(kamigame_max_details.get())
            max_map_details = int(kamigame_max_map_details.get())
            if max_pages < 1 or max_details < 0 or max_map_details < 0:
                raise ValueError("limits must be positive")
        except Exception as exc:
            show_operation_error(
                "ゲーム情報を取得",
                "ERR_DBD_KNOWLEDGE_IMPORT",
                "ゲーム情報の候補を取得できませんでした。",
                "取得元、ネットワーク状態、保存先、取得上限を確認してください。",
                exc,
            )
            return

        def done(manifest) -> None:
            counts = manifest.get("counts", {})
            text = (
                f"取得完了: サバイバーパーク={counts.get('survivor_perks',0)} / "
                f"キラーパーク={counts.get('killer_perks',0)} / "
                f"キラー={counts.get('killers',0)} / "
                f"アイテム={counts.get('items',0)} / "
                f"アドオン={counts.get('addons',0)} / "
                f"マップ={counts.get('maps',0)} / "
                f"キラー詳細={counts.get('killer_details',0)}"
            )
            kamigame_result.set(text)
            try:
                post_started = time.monotonic()
                sync_started = time.monotonic()
                catalog_changed = sync_kamigame_review_catalog(game_knowledge_catalog, out)
                db_upsert_seconds = time.monotonic() - sync_started
                alias_started = time.monotonic()
                report = index_kamigame_candidates_for_search(
                    entity_alias_catalog,
                    out,
                )
                alias_seconds = time.monotonic() - alias_started
                post_seconds = time.monotonic() - post_started
                performance = manifest.setdefault("performance", {})
                elapsed = performance.setdefault("elapsed_seconds", {})
                elapsed["db_upsert"] = round(db_upsert_seconds, 6)
                elapsed["alias_index_update"] = round(alias_seconds, 6)
                elapsed["post_process"] = round(post_seconds, 6)
                elapsed["total_with_post_process"] = round(float(elapsed.get("total", 0.0)) + post_seconds, 6)
                perf_counts = performance.setdefault("counts", {})
                perf_counts["catalog_changed"] = int(catalog_changed)
                perf_counts["alias_records"] = int(report.alias_records)
                manifest_body = dict(manifest)
                manifest_body.pop("manifest_sha256", None)
                manifest["manifest_sha256"] = sha256_bytes(canonical_json_bytes(manifest_body))
                (out / "manifest.json").write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                text += (
                    f"\n検索用インデックス: 候補 {report.candidates}件 / "
                    f"Alias {report.alias_records}件"
                    f"\n取得時間: {elapsed.get('total_with_post_process', 0.0):.2f}秒 "
                    f"(HTML実取得 {perf_counts.get('html_requests', 0)} / "
                    f"同一実行cache hit {perf_counts.get('html_cache_hits', 0)})"
                )
                kamigame_result.set(text)
            except Exception as exc:
                kamigame_result.set(
                    text
                    + f"\n検索用インデックス反映のみ失敗: {type(exc).__name__}: {exc}"
                )
            refresh_kamigame_inventory()
            status.set("ゲーム情報候補の取得が完了しました")
            messagebox.showinfo(
                "ゲーム情報を取得",
                (
                    kamigame_result.get()
                    + "\n\nraw HTMLは証跡として保存され、"
                    "normalized JSONLが検索・レビュー用データです。"
                ),
            )

        run_background(
            "ゲーム情報を取得",
            lambda: KamigameDbDKnowledgeCollector(out).collect(
                follow_killer_details=kamigame_details.get(),
                max_pages=max_pages,
                max_killer_details=max_details,
                follow_map_details=kamigame_map_details.get(),
                max_map_details=max_map_details,
            ),
            done,
        )

    action_row = ttk.Frame(knowledge_import_tab)
    action_row.grid(row=5, column=0, sticky="w", pady=(4, 0))
    ttk.Button(
        action_row,
        text="ゲーム情報を取得",
        command=collect_kamigame,
    ).pack(side="left", padx=(0, 6))
    ttk.Button(
        action_row,
        text="取得済み候補を再読込",
        command=refresh_kamigame_inventory,
    ).pack(side="left", padx=6)
    ttk.Button(
        action_row,
        text="検索用インデックスへ反映",
        command=index_kamigame_candidates,
    ).pack(side="left", padx=6)
    ttk.Button(action_row,text="編集",command=edit_knowledge_candidate).pack(side="left",padx=6)
    ttk.Button(action_row,text="確認済みにする",command=verify_knowledge_candidate).pack(side="left",padx=6)
    ttk.Button(action_row,text="マップ詳細",command=show_map_detail).pack(side="left",padx=6)

    inventory_tree.bind("<Double-1>", lambda _e: edit_knowledge_candidate())
    refresh_kamigame_inventory()

    # ---- Video analysis -> editing information tab ---------------------------
    analysis_tab = ttk.Frame(notebook, padding=12)
    notebook.add(analysis_tab, text="動画を解析・編集情報を出力")
    analysis_tab.columnconfigure(0, weight=1); analysis_tab.rowconfigure(0, weight=1)
    analysis_notebook=ttk.Notebook(analysis_tab); analysis_notebook.grid(row=0,column=0,sticky="nsew")
    analysis_run_tab=ttk.Frame(analysis_notebook,padding=8); analysis_result_tab=ttk.Frame(analysis_notebook,padding=8)
    analysis_notebook.add(analysis_run_tab,text="解析"); analysis_notebook.add(analysis_result_tab,text="解析結果")
    analysis_run_tab.columnconfigure(0,weight=1); analysis_run_tab.rowconfigure(0,weight=1)

    analysis_top=ttk.Frame(analysis_run_tab); analysis_top.grid(row=0,column=0,sticky="nsew"); analysis_top.columnconfigure(0,weight=3); analysis_top.columnconfigure(1,weight=2); analysis_top.rowconfigure(0,weight=1,minsize=420)
    analysis_media=ttk.Frame(analysis_top); analysis_media.grid(row=0,column=0,sticky="nsew",padx=(0,8)); analysis_media.columnconfigure(0,weight=1); analysis_media.rowconfigure(0,weight=1)
    analysis_side=ttk.LabelFrame(analysis_top,text="解析動画・出力先・動画操作",padding=8); analysis_side.grid(row=0,column=1,sticky="nsew"); analysis_side.columnconfigure(1,weight=1)

    analysis_video=tk.StringVar(); analysis_frame=tk.StringVar(value="0"); analysis_dest=tk.StringVar(value=str(workspace.root / "analysis-exports"))
    analysis_model=tk.StringVar(value=active_runtime.default_whisper_model or "small"); analysis_device=tk.StringVar(value=active_runtime.device or "auto"); analysis_compute=tk.StringVar(value=active_runtime.compute_type or "int8")
    analysis_model_display=tk.StringVar(value=display_for_value(WHISPER_MODEL_OPTIONS_JA,analysis_model.get(),"小（small・推奨）"))
    analysis_device_display=tk.StringVar(value=display_for_value(DEVICE_OPTIONS_JA,analysis_device.get(),"自動"))
    analysis_compute_display=tk.StringVar(value=display_for_value(COMPUTE_OPTIONS_JA,analysis_compute.get(),"省メモリ（int8）"))
    analysis_download=tk.BooleanVar(value=False); analysis_interval=tk.StringVar(value="2.0"); analysis_status=tk.StringVar(value="動画を選択して解析してください。")
    def choose_analysis_video():
        chosen=filedialog.askopenfilename(title="解析するDbD動画を選択",filetypes=[("動画","*.mp4;*.mkv;*.mov;*.webm;*.avi"),("すべて","*.*")])
        if chosen: analysis_video.set(chosen); analysis_player.open_source(chosen)
    def choose_analysis_dest():
        chosen=filedialog.askdirectory(title="編集情報の出力先を選択")
        if chosen: analysis_dest.set(chosen)
    for row,(label,var,chooser) in enumerate((("解析動画",analysis_video,choose_analysis_video),("出力先",analysis_dest,choose_analysis_dest))):
        ttk.Label(analysis_side,text=label).grid(row=row,column=0,sticky="w",pady=3); ttk.Entry(analysis_side,textvariable=var).grid(row=row,column=1,sticky="ew",pady=3); ttk.Button(analysis_side,text="参照",command=chooser).grid(row=row,column=2,sticky="w",padx=(6,0),pady=3)

    analysis_settings=ttk.LabelFrame(analysis_run_tab,text="設定",padding=8); analysis_settings.grid(row=1,column=0,sticky="ew",pady=(8,0));
    for i in range(4): analysis_settings.columnconfigure(i,weight=1)
    ttk.Label(analysis_settings,text="文字起こしモデル").grid(row=0,column=0,sticky="w"); ttk.Label(analysis_settings,text="デバイス").grid(row=0,column=1,sticky="w"); ttk.Label(analysis_settings,text="計算方式").grid(row=0,column=2,sticky="w"); ttk.Label(analysis_settings,text="OCR間隔(秒)").grid(row=0,column=3,sticky="w")
    ttk.Combobox(analysis_settings,textvariable=analysis_model_display,values=list(WHISPER_MODEL_OPTIONS_JA),state="readonly").grid(row=1,column=0,sticky="ew",padx=(0,4))
    ttk.Combobox(analysis_settings,textvariable=analysis_device_display,values=list(DEVICE_OPTIONS_JA),state="readonly").grid(row=1,column=1,sticky="ew",padx=4)
    ttk.Combobox(analysis_settings,textvariable=analysis_compute_display,values=list(COMPUTE_OPTIONS_JA),state="readonly").grid(row=1,column=2,sticky="ew",padx=4)
    ttk.Entry(analysis_settings,textvariable=analysis_interval,width=10).grid(row=1,column=3,sticky="ew",padx=(4,0))
    ttk.Checkbutton(analysis_settings,text="モデルが無い場合のダウンロードを今回だけ許可",variable=analysis_download).grid(row=2,column=0,columnspan=4,sticky="w",pady=(6,2))
    ttk.Label(analysis_settings,text="実行環境プロファイルの保存値を初期値として使用します。",foreground="#555555").grid(row=3,column=0,columnspan=4,sticky="w")

    analysis_result_tab.columnconfigure(0,weight=1); analysis_result_tab.rowconfigure(1,weight=1)
    ttk.Label(analysis_result_tab,textvariable=analysis_status,wraplength=1000).grid(row=0,column=0,sticky="w",pady=(0,6))
    findings_tree=ttk.Treeview(analysis_result_tab,columns=("time","kind","label","score","text"),show="headings",height=16); findings_tree.grid(row=1,column=0,sticky="nsew")
    for key,title,width in (("time","時間",90),("kind","種別",120),("label","ラベル",120),("score","見どころ",80),("text","内容",520)):
        findings_tree.heading(key,text=title); findings_tree.column(key,width=width,stretch=True)

    analysis_player=TkTrainingMediaPlayer(analysis_media,root=root,source_getter=lambda:analysis_video.get(),frame_getter=lambda:int(analysis_frame.get() or "0"),frame_setter=lambda value:analysis_frame.set(str(value)),status_setter=status.set,ffprobe_executable=runtime_ffprobe,diagnostics=diagnostics,diagnostic_feature="VIDEO_ANALYSIS_EXPORT",player_id="video-analysis-player")
    analysis_player.grid(row=0,column=0,sticky="nsew")
    def run_video_analysis():
        source=analysis_video.get().strip(); dest=analysis_dest.get().strip()
        if not source or not dest: messagebox.showerror("動画解析","解析動画と出力先を指定してください。"); return
        try: interval=float(analysis_interval.get())
        except ValueError: messagebox.showerror("動画解析","OCR間隔は数値で指定してください。"); return
        analysis_model.set(WHISPER_MODEL_OPTIONS_JA[analysis_model_display.get()]); analysis_device.set(DEVICE_OPTIONS_JA[analysis_device_display.get()]); analysis_compute.set(COMPUTE_OPTIONS_JA[analysis_compute_display.get()])
        run_id=Path(source).stem + "-editing-intelligence"
        target=Path(dest)/run_id
        if target.exists():
            from datetime import datetime
            target=Path(dest)/(run_id+"-"+datetime.now().strftime("%Y%m%d-%H%M%S"))
        analysis_status.set("解析中…文字起こしと右上通知OCRを実行しています。")
        def execute():
            return video_analysis_service.analyze(video_path=source,destination=target,model=analysis_model.get(),device=analysis_device.get(),compute_type=analysis_compute.get(),allow_model_download=analysis_download.get(),ocr_interval_seconds=interval)
        def done(result):
            findings_tree.delete(*findings_tree.get_children())
            findings=result["analysis"].get("findings",[])
            for idx,row in enumerate(findings):
                ms=int(row.get("start_ms",0)); minute=ms//60000; second=(ms%60000)/1000
                text=str(row.get("text","")).replace("\n"," "); text=text if len(text)<=100 else text[:97]+"..."
                findings_tree.insert("","end",iid=str(idx),values=(f"{minute:02d}:{second:05.2f}",row.get("kind",""),row.get("label",""),row.get("highlight_score",0),text))
            manifest=result["manifest"]; analysis_status.set(f"解析完了: {manifest.get('finding_count',0)}件 / {result['root']}")
            analysis_notebook.select(analysis_result_tab)
            messagebox.showinfo("動画解析・編集情報出力",f"解析と出力が完了しました。\n\n{result['root']}\n\n発言 {manifest.get('speech_count',0)}件 / 通知 {manifest.get('notification_count',0)}件")
        run_background("動画解析・編集情報出力",execute,done)
    ttk.Button(analysis_settings,text="動画を解析して編集情報を出力",command=run_video_analysis).grid(row=4,column=0,columnspan=4,sticky="ew",pady=(8,2))

    # ---- Backup / Restore tab ------------------------------------------------
    migration_tab = ttk.Frame(notebook, padding=12)
    notebook.add(migration_tab, text="バックアップ・復元")
    migration_tab.columnconfigure(1, weight=1)
    ttk.Label(
        migration_tab,
        text="別PCへの移行用。Project Game Intelligence / Training data / Triviaをchecksum付きZIPに保存します。",
        wraplength=900,
    ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
    ttk.Label(
        migration_tab,
        text="Restore前はBAI Video Production / Trivia Editorを閉じてください。API Key / Credential / private keyは対象外です。",
        wraplength=900,
    ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 12))

    migration_project = tk.StringVar()
    include_project = tk.BooleanVar(value=False)
    include_training = tk.BooleanVar(value=True)
    include_trivia = tk.BooleanVar(value=True)
    ttk.Checkbutton(migration_tab, text="プロジェクトのゲーム情報", variable=include_project).grid(row=2, column=0, sticky="w", pady=3)
    ttk.Entry(migration_tab, textvariable=migration_project).grid(row=2, column=1, sticky="ew", padx=(8, 8), pady=3)
    def choose_migration_project() -> None:
        chosen = filedialog.askdirectory(title="BAI Video Productionプロジェクトフォルダを選択")
        if chosen:
            migration_project.set(chosen)
            include_project.set(True)
    ttk.Button(migration_tab, text="プロジェクトフォルダを選択", command=choose_migration_project).grid(row=2, column=2, sticky="e", pady=3)

    ttk.Checkbutton(migration_tab, text="Training Studioワークスペース（画像 / CSV / インデックス / OCR / 文字起こし / 豆知識）", variable=include_training).grid(row=3, column=0, columnspan=3, sticky="w", pady=3)
    ttk.Checkbutton(migration_tab, text="Trivia Editor共有知識データベース", variable=include_trivia).grid(row=4, column=0, columnspan=3, sticky="w", pady=3)

    migration_last_bundle = tk.StringVar()
    ttk.Label(migration_tab, text="バックアップ / 復元ZIP").grid(row=5, column=0, sticky="w", pady=(12, 3))
    ttk.Entry(migration_tab, textvariable=migration_last_bundle, state="readonly").grid(row=5, column=1, sticky="ew", padx=(8, 8), pady=(12, 3))

    def migration_service() -> DbDDataMigrationService:
        return DbDDataMigrationService(training_root=workspace.root)

    def selected_project_or_none() -> str | None:
        value = migration_project.get().strip()
        return value or None

    def create_migration_backup() -> None:
        if not any((include_project.get(), include_training.get(), include_trivia.get())):
            messagebox.showerror("Backup", "Select at least one data scope.")
            return
        if include_project.get() and not selected_project_or_none():
            messagebox.showerror("Backup", "Select the BAI Video Production project folder or turn off Project Game Intelligence.")
            return
        chosen = filedialog.asksaveasfilename(
            title="Save DbD migration backup",
            defaultextension=".zip",
            filetypes=[("Migration ZIP", "*.zip")],
            initialfile="bvp-dbd-data-migration.zip",
        )
        if not chosen:
            return
        def done(receipt) -> None:
            migration_last_bundle.set(str(receipt.path))
            status.set(f"Migration backup: {receipt.entry_count} files")
            messagebox.showinfo(
                "Backup complete",
                f"Backup: {receipt.path}\nFiles: {receipt.entry_count}\nBytes: {receipt.total_bytes}\nManifest: {receipt.manifest_sha256}\n\nCredentials are not included.",
            )
        run_background(
            "DbD data backup",
            lambda: migration_service().create_backup(
                chosen,
                project_root=selected_project_or_none(),
                include_project=include_project.get(),
                include_training=include_training.get(),
                include_trivia=include_trivia.get(),
            ),
            done,
        )

    def choose_restore_bundle() -> str | None:
        chosen = filedialog.askopenfilename(title="Select DbD migration backup", filetypes=[("Migration ZIP", "*.zip"), ("All files", "*.*")])
        if chosen:
            migration_last_bundle.set(chosen)
        return chosen or None

    def preview_migration_restore() -> None:
        chosen = choose_restore_bundle()
        if not chosen:
            return
        try:
            preview = migration_service().preview_restore(chosen, project_root=selected_project_or_none())
        except Exception as exc:
            show_operation_error('Restore preview failed', 'ERR_DBD_RESTORE_PREVIEW', 'バックアップ内容を事前確認できませんでした。', 'ZIPファイル、保存先、バックアップの整合性を確認してください。', exc)
            return
        if preview.requires_project_root:
            messagebox.showwarning("Restore preview", "This backup contains Project Game Intelligence data. Select the destination BVP project folder and preview again.")
            return
        conflict_text = "\n".join(preview.conflicts[:12]) if preview.conflicts else "None"
        if len(preview.conflicts) > 12:
            conflict_text += f"\n... and {len(preview.conflicts)-12} more"
        messagebox.showinfo(
            "Restore preview",
            f"Bundle: {preview.bundle_id}\nFiles: {preview.entry_count}\nBytes: {preview.total_bytes}\nScopes: {', '.join(preview.scopes)}\nConflicts: {len(preview.conflicts)}\n{conflict_text}\n\nNo files were changed.",
        )

    def restore_migration_bundle() -> None:
        chosen = migration_last_bundle.get().strip()
        if not chosen:
            chosen = choose_restore_bundle() or ""
        if not chosen:
            return
        try:
            preview = migration_service().preview_restore(chosen, project_root=selected_project_or_none())
        except Exception as exc:
            show_operation_error('Restore failed', 'ERR_DBD_RESTORE', 'バックアップから復元できませんでした。', '事前確認結果、競合ファイル、保存先への書き込み権限を確認してください。', exc)
            return
        if preview.requires_project_root:
            messagebox.showerror("Restore", "Select the destination BAI Video Production project folder first.")
            return
        replace = bool(preview.conflicts)
        details = (
            f"Restore {preview.entry_count} files from backup?\n\n"
            f"Conflicting existing files: {len(preview.conflicts)}\n"
            "If conflicts exist, a pre-restore safety backup is created automatically.\n"
            "Close BAI Video Production / Trivia Editor before continuing."
        )
        if not messagebox.askyesno("Confirm restore", details):
            return
        def done(receipt) -> None:
            try:
                refresh_visual(); refresh_ocr(); refresh_trivia()
            except Exception:
                pass
            status.set(f"Restore complete: {receipt.restored_files} files")
            safety = str(receipt.safety_backup_path) if receipt.safety_backup_path else "Not required"
            messagebox.showinfo(
                "Restore complete",
                f"Restored: {receipt.restored_files}\nReplaced: {receipt.replaced_files}\nNew: {receipt.new_files}\nSafety backup: {safety}\n\nRestart Training Studio before continuing normal work.",
            )
        run_background(
            "DbD data restore",
            lambda: migration_service().restore(
                chosen,
                project_root=selected_project_or_none(),
                allow_replace=replace,
                create_safety_backup=True,
            ),
            done,
        )

    migration_buttons = ttk.Frame(migration_tab)
    migration_buttons.grid(row=6, column=0, columnspan=3, sticky="w", pady=(12, 6))
    ttk.Button(migration_buttons, text="バックアップZIPを作成", command=create_migration_backup).pack(side="left", padx=(0, 6))
    ttk.Button(migration_buttons, text="復元内容を確認", command=preview_migration_restore).pack(side="left", padx=6)
    ttk.Button(migration_buttons, text="復元", command=restore_migration_bundle).pack(side="left", padx=6)

    ttk.Label(
        migration_tab,
        text=f"Training data: {workspace.root}\nGlobal Trivia: {migration_service().trivia_database_path}\nRestore safety backups: {migration_service().safety_backup_root}",
        wraplength=900,
    ).grid(row=7, column=0, columnspan=3, sticky="w", pady=(12, 0))

    # Operational order defined by TASK-050. ttk.Notebook.insert moves an
    # already-managed tab without recreating widgets or changing their state.
    ordered_tabs = (
        intro_tab,
        runtime_tab,
        knowledge_import_tab,
        calibration_page,
        video_tab,
        visual_tab,
        ocr_tab,
        trivia_tab,
        review_tab,
        migration_tab,
    )
    for index, tab in enumerate(ordered_tabs):
        notebook.insert(index, tab)

    try:
        root.mainloop()
    finally:
        diagnostics.emit("APP_EXIT")
        diagnostics.close()
    return 0


def main() -> int:
    return launch_training_studio()


if __name__ == "__main__":
    raise SystemExit(main())
