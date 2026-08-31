"""User-visible startup boundary for the frozen TASK-036 Windows application."""

from __future__ import annotations

import ctypes
import re
import sys
from typing import Callable, Sequence

from .errors import ProductError
from .task036_native_probe import Task036NativeProbe
from .task036_shell_cli import run as shell_run
from .task036_single_instance import Task036SingleInstanceGuard


ErrorPresenter = Callable[[str, str], None]
AppMain = Callable[[list[str] | None], int]


_SAFE_ERROR_CODE = re.compile(r"^ERR_[A-Z0-9_]{1,96}$")
_STARTUP_GUIDANCE: dict[str, tuple[str, str]] = {
    "ERR_TASK036_WEBVIEW2_RUNTIME_REQUIRED": (
        "画面表示に必要なWebView2 Runtimeが見つかりません。",
        "WebView2 Runtimeをインストールまたは修復してから、もう一度起動してください。",
    ),
    "ERR_TASK036_PYWEBVIEW_NOT_INSTALLED": (
        "画面を開くためのアプリ部品が不足しています。",
        "BAI Video Productionを再インストールしてから、もう一度起動してください。",
    ),
    "ERR_TASK036_WINDOWS_REQUIRED": (
        "このアプリはWindowsでのみ起動できます。",
        "Windows上のインストール済みBAI Video Productionから起動してください。",
    ),
    "ERR_TASK036_INSTALL_PATH_TOO_LONG": (
        "アプリの保存場所が長すぎるため起動できません。",
        "アプリを短いローカル保存先へ移すか再インストールしてから、もう一度起動してください。",
    ),
    "ERR_TASK036_ALREADY_RUNNING": (
        "BAI Video Productionは既に起動しています。",
        "既に開いているウィンドウを確認してください。",
    ),
    "ERR_TASK036_FIRST_RUN_STORAGE_UNAVAILABLE": (
        "初回プロジェクトの保存先を利用できません。",
        "Windowsのアプリ保存先が書き込み可能か確認してから、もう一度起動してください。",
    ),
    "ERR_TASK036_FIRST_RUN_PATH_UNSAFE": (
        "初回プロジェクトの保存先を安全に確認できません。",
        "別のローカル保存先を選べる状態にしてから、もう一度起動してください。",
    ),
    "ERR_TASK036_FIRST_RUN_CONFIG_UNSAFE": (
        "初回プロジェクト設定を安全に確認できません。",
        "設定の保存先を確認してから、もう一度起動してください。",
    ),
    "ERR_TASK036_FIRST_RUN_CONFIG_WRITE_FAILED": (
        "初回プロジェクト設定を保存できません。",
        "保存先の空き容量と書き込み権限を確認してから、もう一度起動してください。",
    ),
    "ERR_TASK036_FIRST_RUN_CONFIG_INVALID": (
        "初回プロジェクト設定を読み込めません。",
        "設定を変更せず、サポートへエラーコードをお知らせください。",
    ),
    "ERR_TASK036_FIRST_RUN_CONFIG_IDENTITY": (
        "初回プロジェクト設定の識別情報が一致しません。",
        "設定を変更せず、サポートへエラーコードをお知らせください。",
    ),
    "ERR_TASK036_FIRST_RUN_DISPLAY_NAME_UNKNOWN": (
        "初回プロジェクト名を安全に更新できません。",
        "既存の設定を変更せず、サポートへエラーコードをお知らせください。",
    ),
    "ERR_TASK036_PACKAGED_APP_NONZERO": (
        "アプリの準備中に処理が完了しませんでした。",
        "もう一度起動してください。繰り返す場合はサポートへエラーコードをお知らせください。",
    ),
}


def show_native_error(title: str, message: str) -> None:
    """Show an actionable error even though the frozen executable has no console."""

    ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)


def _safe_error_code(code: str) -> str:
    return code if _SAFE_ERROR_CODE.fullmatch(code) else "ERR_TASK036_PACKAGED_STARTUP"


def _error_message(exc: ProductError) -> str:
    code = _safe_error_code(exc.code)
    reason, next_action = _STARTUP_GUIDANCE.get(
        code,
        (
            "アプリの起動準備を完了できませんでした。",
            "もう一度起動してください。繰り返す場合はサポートへエラーコードをお知らせください。",
        ),
    )
    return f"{reason}\n\n次の操作: {next_action}\n\nエラーコード: {code}"


def _present_safely(presenter: ErrorPresenter, message: str) -> None:
    try:
        presenter("BAI Video Productionを起動できません", message)
    except Exception:
        # A failed native presenter must never retain the single-instance lease
        # or turn a bounded startup failure into a hung process.
        return


def _packaged_shell_main(argv: list[str] | None) -> int:
    shell_run(argv)
    return 0


def packaged_main(
    argv: Sequence[str] | None = None,
    *,
    probe: Task036NativeProbe | None = None,
    instance_guard: Task036SingleInstanceGuard | None = None,
    presenter: ErrorPresenter = show_native_error,
    app_main: AppMain | None = None,
) -> int:
    effective_argv = list(sys.argv[1:] if argv is None else argv)
    if effective_argv[:1] == ["--bvp-installer-bridge"]:
        try:
            from .montage_learning_installer_cli import main as bridge_installer_main

            return bridge_installer_main(effective_argv[1:])
        except SystemExit as exc:
            return int(exc.code) if isinstance(exc.code, int) else 2
        except Exception:
            return 3
    try:
        (probe or Task036NativeProbe()).require_ready()
        with (instance_guard or Task036SingleInstanceGuard()).acquire():
            runner = app_main if app_main is not None else _packaged_shell_main
            result = runner(
                None if argv is None else list(argv)
            )
            if type(result) is not int or result != 0:
                raise ProductError(
                    "ERR_TASK036_PACKAGED_APP_NONZERO",
                    "packaged application returned a non-success result",
                )
            return 0
    except ProductError as exc:
        _present_safely(presenter, _error_message(exc))
        return 2
    except ValueError:
        _present_safely(
            presenter,
            "起動方法を確認できませんでした。\n\n"
            "次の操作: ショートカットまたは通常のアプリアイコンから、もう一度起動してください。\n\n"
            "エラーコード: ERR_TASK036_SHELL_CLI",
        )
        return 2
    except Exception:
        _present_safely(
            presenter,
            "アプリを起動できませんでした。\n\n"
            "次の操作: もう一度起動してください。繰り返す場合はアプリを再インストールするか、"
            "サポートへエラーコードをお知らせください。\n\n"
            "エラーコード: ERR_TASK036_PACKAGED_STARTUP",
        )
        return 2
