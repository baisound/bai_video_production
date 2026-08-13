"""TASK-036 read-only Windows native-shell preflight.

The probe never installs pywebview/WebView2 and never claims a renderer passed
native acceptance. It only determines whether the native layout spike can be
attempted on the current host.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import os
from pathlib import Path
import platform
import re
import sys
from typing import Any, Callable, Mapping

from .errors import ProductError, ProductErrorCategory


ModuleFinder = Callable[[str], Any]


MAX_SUPPORTED_EXECUTABLE_PATH_CHARS = 166
WEBVIEW2_DOWNLOAD_URL = "https://developer.microsoft.com/microsoft-edge/webview2/"


@dataclass(frozen=True, slots=True)
class Task036NativeProbeReport:
    platform_name: str
    pywebview_available: bool
    webview2_runtime_candidates: tuple[str, ...]
    executable_path: str
    executable_path_chars: int
    max_supported_executable_path_chars: int
    fixed_webview2_runtime_requested: bool

    @property
    def install_path_supported(self) -> bool:
        return self.executable_path_chars <= self.max_supported_executable_path_chars

    @property
    def ready_to_launch_layout_spike(self) -> bool:
        return (
            self.platform_name == "Windows"
            and self.pywebview_available
            and bool(self.webview2_runtime_candidates)
            and self.install_path_supported
        )

    @property
    def blocking_reasons(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if self.platform_name != "Windows":
            reasons.append("UNSUPPORTED_PLATFORM")
        if not self.pywebview_available:
            reasons.append("PYWEBVIEW_MISSING")
        if not self.webview2_runtime_candidates:
            reasons.append("WEBVIEW2_RUNTIME_MISSING")
        if not self.install_path_supported:
            reasons.append("INSTALL_PATH_TOO_LONG")
        return tuple(reasons)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": "1.1.0",
            "task_owner": "TASK-036",
            "gate": "NATIVE_SHELL_PREFLIGHT",
            "platform": self.platform_name,
            "pywebview_available": self.pywebview_available,
            "webview2_runtime_candidate_count": len(self.webview2_runtime_candidates),
            "webview2_runtime_candidates": list(self.webview2_runtime_candidates),
            "fixed_webview2_runtime_requested": self.fixed_webview2_runtime_requested,
            "executable_path": self.executable_path,
            "executable_path_chars": self.executable_path_chars,
            "max_supported_executable_path_chars": self.max_supported_executable_path_chars,
            "install_path_supported": self.install_path_supported,
            "blocking_reasons": list(self.blocking_reasons),
            "ready_to_launch_layout_spike": self.ready_to_launch_layout_spike,
            "renderer_native_validated": False,
            "dependency_install_performed": False,
        }


class Task036NativeProbe:
    def __init__(
        self,
        *,
        platform_name: str | None = None,
        environ: Mapping[str, str] | None = None,
        module_finder: ModuleFinder | None = None,
        executable_path: str | Path | None = None,
        max_supported_executable_path_chars: int = MAX_SUPPORTED_EXECUTABLE_PATH_CHARS,
    ) -> None:
        self.platform_name = platform_name or platform.system()
        self.environ = dict(os.environ if environ is None else environ)
        self.module_finder = module_finder or importlib.util.find_spec
        self.executable_path = str(Path(executable_path or sys.executable).resolve())
        self.max_supported_executable_path_chars = max_supported_executable_path_chars

    def _webview2_candidates(self) -> tuple[str, ...]:
        if self.platform_name != "Windows":
            return ()
        fixed_runtime = self.environ.get("WEBVIEW2_BROWSER_EXECUTABLE_FOLDER")
        if fixed_runtime is not None:
            fixed_path = Path(fixed_runtime)
            if fixed_path.is_dir() and (fixed_path / "msedgewebview2.exe").is_file():
                return (str(fixed_path),)
            return ()
        roots: list[Path] = []
        for key in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
            raw = self.environ.get(key)
            if not raw:
                continue
            base = Path(raw)
            if key == "LOCALAPPDATA":
                roots.append(base / "Microsoft" / "EdgeWebView" / "Application")
            else:
                roots.append(base / "Microsoft" / "EdgeWebView" / "Application")
        found: list[str] = []
        for root in roots:
            if not root.is_dir():
                continue
            versions = sorted(
                (
                    item
                    for item in root.iterdir()
                    if item.is_dir() and re.fullmatch(r"\d+(?:\.\d+)*", item.name)
                ),
                key=lambda path: tuple(int(part) for part in path.name.split(".")),
                reverse=True,
            )
            if versions:
                found.append(str(versions[0]))
            else:
                found.append(str(root))
        return tuple(dict.fromkeys(found))

    def run(self) -> Task036NativeProbeReport:
        try:
            pywebview = self.module_finder("webview") is not None
        except (ImportError, ValueError, AttributeError):
            pywebview = False
        return Task036NativeProbeReport(
            platform_name=self.platform_name,
            pywebview_available=pywebview,
            webview2_runtime_candidates=self._webview2_candidates(),
            executable_path=self.executable_path,
            executable_path_chars=len(self.executable_path),
            max_supported_executable_path_chars=self.max_supported_executable_path_chars,
            fixed_webview2_runtime_requested="WEBVIEW2_BROWSER_EXECUTABLE_FOLDER" in self.environ,
        )

    def require_ready(self) -> Task036NativeProbeReport:
        report = self.run()
        if report.platform_name != "Windows":
            raise ProductError(
                "ERR_TASK036_WINDOWS_REQUIRED",
                "BAI Video Production desktop Shell requires Windows.",
                ProductErrorCategory.NOT_SUPPORTED,
            )
        if not report.pywebview_available:
            raise ProductError(
                "ERR_TASK036_PYWEBVIEW_NOT_INSTALLED",
                "The packaged desktop Shell is incomplete. Reinstall BAI Video Production.",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            )
        if not report.webview2_runtime_candidates:
            raise ProductError(
                "ERR_TASK036_WEBVIEW2_RUNTIME_REQUIRED",
                "Microsoft Edge WebView2 Runtime is required. Install or repair WebView2, then start the app again.",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                retryable=True,
                details={
                    "recovery_action": "Install or repair Microsoft Edge WebView2 Runtime and retry.",
                    "download_url": WEBVIEW2_DOWNLOAD_URL,
                    "automatic_install_performed": False,
                },
            )
        if not report.install_path_supported:
            raise ProductError(
                "ERR_TASK036_INSTALL_PATH_TOO_LONG",
                f"The application path is too long ({report.executable_path_chars} characters). Move BAI Video Production to a shorter local folder and retry.",
                ProductErrorCategory.VALIDATION,
                details={
                    "maximum_supported_executable_path_chars": report.max_supported_executable_path_chars,
                    "actual_executable_path_chars": report.executable_path_chars,
                    "recovery_action": "Move the complete application folder to a shorter local path.",
                },
            )
        return report
