"""User-visible startup boundary for the frozen TASK-036 Windows application."""

from __future__ import annotations

import ctypes
from typing import Callable, Sequence

from .errors import ProductError
from .task036_native_probe import Task036NativeProbe
from .task036_shell_cli import main as shell_main


ErrorPresenter = Callable[[str, str], None]


def show_native_error(title: str, message: str) -> None:
    """Show an actionable error even though the frozen executable has no console."""

    ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)


def _error_message(exc: ProductError) -> str:
    recovery = exc.details.get("recovery_action")
    download_url = exc.details.get("download_url")
    lines = [exc.message, "", f"Error code: {exc.code}"]
    if recovery:
        lines.extend(("", f"Recovery: {recovery}"))
    if download_url:
        lines.append(str(download_url))
    return "\n".join(lines)


def packaged_main(
    argv: Sequence[str] | None = None,
    *,
    probe: Task036NativeProbe | None = None,
    presenter: ErrorPresenter = show_native_error,
    app_main: Callable[[list[str] | None], int] = shell_main,
) -> int:
    try:
        (probe or Task036NativeProbe()).require_ready()
        return app_main(None if argv is None else list(argv))
    except ProductError as exc:
        presenter("BAI Video Production could not start", _error_message(exc))
        return 2
    except Exception:
        presenter(
            "BAI Video Production could not start",
            "The desktop application could not start. Reinstall the application or contact support.\n\n"
            "Error code: ERR_TASK036_PACKAGED_STARTUP",
        )
        return 2
