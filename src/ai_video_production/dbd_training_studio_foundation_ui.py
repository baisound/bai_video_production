"""TASK-050 startup and foundation tabs for BAI DbD Training Studio."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .dbd_training_studio_foundation import (
    RuntimeEnvironmentProfile,
    RuntimeProfileStore,
    WorkspaceDescriptor,
    WorkspaceRegistry,
    WorkspaceService,
    legacy_training_workspace_root,
)
from .dbd_training_studio_i18n import UserFacingError
from .dbd_workspace_management_ui import build_workspace_management_panel
from .dbd_training_review_ui import build_training_data_review_panel


class WorkspaceSelectionCancelled(RuntimeError):
    pass


def _show_error(error: UserFacingError) -> None:
    detail = f"\n\n詳細:\n{error.technical_details}" if error.technical_details else ""
    messagebox.showerror(error.title_ja, error.message() + detail)


def choose_workspace_before_launch(explicit_path: str | None) -> WorkspaceDescriptor:
    """Resolve an explicit/default Workspace or show the first-launch chooser."""
    registry = WorkspaceRegistry()
    service = WorkspaceService(registry)

    if explicit_path:
        path = Path(explicit_path).expanduser()
        return service.open(path) if service.marker_path(path).is_file() else service.adopt_existing(path)

    candidate = registry.default_candidate()
    if candidate is not None:
        try:
            return service.open(candidate)
        except Exception:
            # Do not fail launch solely because a previous machine-local path
            # disappeared. Fall through to explicit user selection.
            pass

    selector = tk.Tk()
    selector.title("BAI DbD Training Studio - ワークスペース")
    selector.geometry("620x360")
    selector.minsize(560, 320)
    selector.columnconfigure(0, weight=1)

    result: dict[str, WorkspaceDescriptor | None] = {"workspace": None}

    title = ttk.Label(selector, text="学習データの保存場所を設定", font=("TkDefaultFont", 14, "bold"))
    title.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 8))
    ttk.Label(
        selector,
        text=(
            "最初に、DbDの学習データを保存するワークスペースを選びます。\n"
            "Cドライブ固定ではありません。D: や E:、任意のフォルダを選択できます。"
        ),
        justify="left",
    ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 16))

    legacy = legacy_training_workspace_root()
    if legacy.is_dir():
        ttk.Label(
            selector,
            text=f"以前の保存場所が見つかりました:\n{legacy}",
            justify="left",
        ).grid(row=2, column=0, sticky="w", padx=20, pady=(0, 12))

    buttons = ttk.Frame(selector)
    buttons.grid(row=3, column=0, sticky="ew", padx=20, pady=8)
    buttons.columnconfigure((0, 1), weight=1)

    def create_new() -> None:
        name = simpledialog.askstring(
            "新しいワークスペース",
            "ワークスペース名を入力してください。\n例: DBD大会学習",
            parent=selector,
        )
        if not name:
            return
        parent = filedialog.askdirectory(
            title="ワークスペースを作成する親フォルダを選択",
            parent=selector,
        )
        if not parent:
            return
        try:
            result["workspace"] = service.create(display_name=name, parent_directory=parent)
        except Exception as exc:
            _show_error(UserFacingError(
                "ERR_DBD_WORKSPACE_CREATE",
                "ワークスペースを作成できませんでした",
                "指定した場所にワークスペースを作成できませんでした。",
                "保存先とワークスペース名を確認し、別の場所も試してください。",
                f"{type(exc).__name__}: {exc}",
            ))
            return
        selector.destroy()

    def open_existing() -> None:
        chosen = filedialog.askdirectory(
            title="既存のDbDワークスペースを選択",
            parent=selector,
        )
        if not chosen:
            return
        try:
            path = Path(chosen)
            result["workspace"] = (
                service.open(path)
                if service.marker_path(path).is_file()
                else service.adopt_existing(path)
            )
        except Exception as exc:
            _show_error(UserFacingError(
                "ERR_DBD_WORKSPACE_OPEN",
                "ワークスペースを開けませんでした",
                "選択したフォルダをワークスペースとして開けませんでした。",
                "別のフォルダを選ぶか、workspace.json の状態を確認してください。",
                f"{type(exc).__name__}: {exc}",
            ))
            return
        selector.destroy()

    ttk.Button(buttons, text="新しいワークスペースを作る", command=create_new).grid(
        row=0, column=0, sticky="ew", padx=(0, 6), ipady=8
    )
    ttk.Button(buttons, text="既存のワークスペースを開く", command=open_existing).grid(
        row=0, column=1, sticky="ew", padx=(6, 0), ipady=8
    )

    if legacy.is_dir():
        def use_legacy() -> None:
            try:
                result["workspace"] = (
                    service.open(legacy)
                    if service.marker_path(legacy).is_file()
                    else service.adopt_existing(legacy, display_name="既存のDbD学習データ")
                )
            except Exception as exc:
                _show_error(UserFacingError(
                    "ERR_DBD_WORKSPACE_ADOPT",
                    "以前の学習データを開けませんでした",
                    "以前の保存場所をワークスペースとして登録できませんでした。",
                    "フォルダへの書き込み権限とファイル状態を確認してください。",
                    f"{type(exc).__name__}: {exc}",
                ))
                return
            selector.destroy()

        ttk.Button(
            selector,
            text="以前の保存場所をそのまま使う",
            command=use_legacy,
        ).grid(row=4, column=0, sticky="w", padx=20, pady=8)

    ttk.Label(
        selector,
        text="ワークスペースには学習画像、HUD設定、OCR、豆知識、Human Gold等が保存されます。",
        foreground="#555555",
        wraplength=560,
    ).grid(row=5, column=0, sticky="w", padx=20, pady=(20, 8))

    def cancelled() -> None:
        selector.destroy()

    selector.protocol("WM_DELETE_WINDOW", cancelled)
    selector.mainloop()

    if result["workspace"] is None:
        raise WorkspaceSelectionCancelled("workspace selection cancelled")
    return result["workspace"]


def build_foundation_tabs(
    notebook: ttk.Notebook,
    *,
    workspace: WorkspaceDescriptor,
    training_workspace,
) -> tuple[ttk.Frame, ttk.Frame, ttk.Frame]:
    intro_tab = ttk.Frame(notebook, padding=16)
    runtime_tab = ttk.Frame(notebook, padding=16)
    review_tab = ttk.Frame(notebook, padding=16)
    notebook.add(intro_tab, text="はじめに")
    notebook.add(runtime_tab, text="実行環境を設定")
    notebook.add(review_tab, text="学習データを確認")

    # Introduction
    intro_tab.columnconfigure(0, weight=1)
    ttk.Label(intro_tab, text="DbD Training Studio", font=("TkDefaultFont", 14, "bold")).grid(
        row=0, column=0, sticky="w", pady=(0, 12)
    )
    ttk.Label(
        intro_tab,
        text=(
            f"現在のワークスペース: {workspace.display_name}\n"
            f"保存場所: {workspace.root_path}\n\n"
            "推奨順序:\n"
            "1. 実行環境を確認\n"
            "2. ゲーム情報を取得\n"
            "3. HUD位置を設定\n"
            "4. 動画または画像から学習\n"
            "5. 学習データを確認"
        ),
        justify="left",
        wraplength=900,
    ).grid(row=1, column=0, sticky="nw")

    build_workspace_management_panel(intro_tab, workspace=workspace)

    # Runtime profile
    runtime_tab.columnconfigure(1, weight=1)
    store = RuntimeProfileStore()
    detected = store.autodetect()
    runtime_state = {"profile": detected}

    runtime_vars = {
        "name": tk.StringVar(value="標準環境"),
        "ffmpeg": tk.StringVar(value=detected.ffmpeg.effective_path or ""),
        "ffprobe": tk.StringVar(value=detected.ffprobe.effective_path or ""),
        "tesseract": tk.StringVar(value=detected.tesseract.effective_path or ""),
        "model_cache": tk.StringVar(value=detected.faster_whisper_model_cache or ""),
        "model": tk.StringVar(value=detected.default_whisper_model),
        "device": tk.StringVar(value=detected.device),
        "compute": tk.StringVar(value=detected.compute_type),
        "ocr_language": tk.StringVar(value=detected.ocr_language),
    }

    rows = (
        ("Python", tk.StringVar(value=detected.python_executable), True),
        ("FFmpeg", runtime_vars["ffmpeg"], False),
        ("FFprobe", runtime_vars["ffprobe"], False),
        ("Tesseract", runtime_vars["tesseract"], False),
        ("FasterWhisperモデル保存先", runtime_vars["model_cache"], False),
        ("既定Whisperモデル", runtime_vars["model"], False),
        ("デバイス", runtime_vars["device"], False),
        ("計算方式", runtime_vars["compute"], False),
        ("OCR言語", runtime_vars["ocr_language"], False),
    )
    ttk.Label(runtime_tab, text="実行環境プロファイル", font=("TkDefaultFont", 12, "bold")).grid(
        row=0, column=0, columnspan=3, sticky="w", pady=(0, 10)
    )
    for row_no, (label, var, readonly) in enumerate(rows, start=1):
        ttk.Label(runtime_tab, text=label).grid(row=row_no, column=0, sticky="w", pady=3)
        ttk.Entry(runtime_tab, textvariable=var, state="readonly" if readonly else "normal").grid(
            row=row_no, column=1, sticky="ew", pady=3, padx=(8, 8)
        )
        if label in {"FFmpeg", "FFprobe", "Tesseract"}:
            def browse(target=var, title=label) -> None:
                chosen = filedialog.askopenfilename(title=f"{title}の実行ファイルを選択")
                if chosen:
                    target.set(chosen)
            ttk.Button(runtime_tab, text="変更", command=browse).grid(row=row_no, column=2, sticky="w")

    status_text = (
        f"FFmpeg: {'✓' if detected.ffmpeg.health == 'AVAILABLE' else '×'}   "
        f"FFprobe: {'✓' if detected.ffprobe.health == 'AVAILABLE' else '×'}   "
        f"Tesseract: {'✓' if detected.tesseract.health == 'AVAILABLE' else '×'}   "
        f"FasterWhisper: {'✓' if detected.faster_whisper_package_version else '×'}"
    )
    runtime_status = tk.StringVar(value=status_text)
    ttk.Label(runtime_tab, textvariable=runtime_status).grid(
        row=10, column=0, columnspan=3, sticky="w", pady=(10, 4)
    )

    def save_runtime() -> None:
        from .dbd_training_studio_foundation import RuntimeTool
        profile_id = "default"
        profile = RuntimeEnvironmentProfile(
            profile_id=profile_id,
            display_name=runtime_vars["name"].get().strip() or "標準環境",
            python_executable=detected.python_executable,
            ffmpeg=RuntimeTool("ffmpeg", runtime_vars["ffmpeg"].get().strip() or None, "USER_OVERRIDE", "AVAILABLE" if runtime_vars["ffmpeg"].get().strip() else "MISSING"),
            ffprobe=RuntimeTool("ffprobe", runtime_vars["ffprobe"].get().strip() or None, "USER_OVERRIDE", "AVAILABLE" if runtime_vars["ffprobe"].get().strip() else "MISSING"),
            tesseract=RuntimeTool("tesseract", runtime_vars["tesseract"].get().strip() or None, "USER_OVERRIDE", "AVAILABLE" if runtime_vars["tesseract"].get().strip() else "MISSING"),
            faster_whisper_package_version=detected.faster_whisper_package_version,
            faster_whisper_model_cache=runtime_vars["model_cache"].get().strip() or None,
            default_whisper_model=runtime_vars["model"].get().strip() or "small",
            device=runtime_vars["device"].get().strip() or "auto",
            compute_type=runtime_vars["compute"].get().strip() or "int8",
            ocr_language=runtime_vars["ocr_language"].get().strip() or "jpn+eng",
        )
        try:
            path = store.save(profile)
            WorkspaceService().set_runtime_profile(workspace, profile.profile_id)
        except Exception as exc:
            _show_error(UserFacingError(
                "ERR_DBD_RUNTIME_PROFILE_SAVE",
                "実行環境プロファイルを保存できませんでした",
                "指定した実行環境設定を保存できませんでした。",
                "パスと書き込み権限を確認してください。",
                f"{type(exc).__name__}: {exc}",
            ))
            return
        messagebox.showinfo("実行環境", f"実行環境プロファイルを保存しました。\n{path}")

    ttk.Button(runtime_tab, text="この実行環境を保存", command=save_runtime).grid(
        row=11, column=0, columnspan=3, sticky="w", pady=(8, 0)
    )

    # Training data review - R3 operational maintenance.
    build_training_data_review_panel(review_tab, training_workspace)

    return intro_tab, runtime_tab, review_tab
