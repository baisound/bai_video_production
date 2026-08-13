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
from typing import Any, Callable, Mapping


ModuleFinder = Callable[[str], Any]


@dataclass(frozen=True, slots=True)
class Task036NativeProbeReport:
    platform_name: str
    pywebview_available: bool
    webview2_runtime_candidates: tuple[str, ...]

    @property
    def ready_to_launch_layout_spike(self) -> bool:
        return self.platform_name == "Windows" and self.pywebview_available and bool(self.webview2_runtime_candidates)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": "1.0.0",
            "task_owner": "TASK-036",
            "gate": "NATIVE_SHELL_PREFLIGHT",
            "platform": self.platform_name,
            "pywebview_available": self.pywebview_available,
            "webview2_runtime_candidate_count": len(self.webview2_runtime_candidates),
            "webview2_runtime_candidates": list(self.webview2_runtime_candidates),
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
    ) -> None:
        self.platform_name = platform_name or platform.system()
        self.environ = dict(os.environ if environ is None else environ)
        self.module_finder = module_finder or importlib.util.find_spec

    def _webview2_candidates(self) -> tuple[str, ...]:
        if self.platform_name != "Windows":
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
        )
