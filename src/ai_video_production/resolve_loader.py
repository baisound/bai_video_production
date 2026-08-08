from __future__ import annotations

from dataclasses import dataclass
import importlib
import os
from pathlib import Path
import platform
import sys
from types import ModuleType
from typing import Iterable

from .errors import ProductError, ProductErrorCategory

_ENV_MODULE_DIR = "RESOLVE_SCRIPT_MODULE_DIR"
_ENV_API_ROOT = "RESOLVE_SCRIPT_API"


@dataclass(frozen=True, slots=True)
class ResolveModuleDiscovery:
    module: ModuleType
    source_kind: str


class ResolveModuleLoader:
    """Discover the locally installed DaVinci Resolve scripting module.

    The loader never downloads or installs code.  It prefers the caller's
    configured Python path and then narrowly scoped local installation paths.
    Full host paths are intentionally not part of the public discovery result.
    """

    def __init__(self, *, platform_name: str | None = None, environ: dict[str, str] | None = None) -> None:
        self.platform_name = platform_name or platform.system()
        self.environ = dict(os.environ if environ is None else environ)

    def _candidate_dirs(self) -> Iterable[tuple[str, Path]]:
        explicit = self.environ.get(_ENV_MODULE_DIR)
        if explicit:
            yield "EXPLICIT_MODULE_DIR", Path(explicit)

        api_root = self.environ.get(_ENV_API_ROOT)
        if api_root:
            root = Path(api_root)
            yield "RESOLVE_SCRIPT_API", root / "Modules"
            yield "RESOLVE_SCRIPT_API", root

        if self.platform_name == "Windows":
            program_data = self.environ.get("PROGRAMDATA")
            if program_data:
                yield (
                    "WINDOWS_PROGRAMDATA",
                    Path(program_data)
                    / "Blackmagic Design"
                    / "DaVinci Resolve"
                    / "Support"
                    / "Developer"
                    / "Scripting"
                    / "Modules",
                )
        elif self.platform_name == "Darwin":
            yield (
                "MACOS_SYSTEM",
                Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"),
            )
        else:
            yield "LINUX_OPT", Path("/opt/resolve/Developer/Scripting/Modules")

    @staticmethod
    def _import_existing() -> ModuleType | None:
        try:
            return importlib.import_module("DaVinciResolveScript")
        except ModuleNotFoundError as exc:
            # Only a missing bridge module means "not found". A missing dependency
            # imported *by* the bridge is an import failure and must not be hidden.
            if exc.name == "DaVinciResolveScript":
                return None
            raise

    def discover(self) -> ResolveModuleDiscovery:
        try:
            existing = self._import_existing()
        except (ImportError, OSError) as exc:
            raise ProductError(
                "ERR_RESOLVE_SCRIPT_MODULE_IMPORT_FAILED",
                "DaVinci Resolve scripting module was found but could not be imported",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                retryable=False,
                details={"exception_type": type(exc).__name__, "platform": self.platform_name},
            ) from exc
        if existing is not None:
            return ResolveModuleDiscovery(existing, "PYTHON_IMPORT_PATH")

        original = list(sys.path)
        try:
            for source_kind, candidate in self._candidate_dirs():
                if not candidate.is_dir():
                    continue
                sys.path.insert(0, str(candidate))
                try:
                    module = importlib.import_module("DaVinciResolveScript")
                except ModuleNotFoundError as exc:
                    sys.path.pop(0)
                    if exc.name == "DaVinciResolveScript":
                        continue
                    raise ProductError(
                        "ERR_RESOLVE_SCRIPT_MODULE_IMPORT_FAILED",
                        "DaVinci Resolve scripting module dependency could not be imported",
                        ProductErrorCategory.EXTERNAL_DEPENDENCY,
                        retryable=False,
                        details={"exception_type": type(exc).__name__, "platform": self.platform_name},
                    ) from exc
                except (ImportError, OSError) as exc:
                    sys.path.pop(0)
                    raise ProductError(
                        "ERR_RESOLVE_SCRIPT_MODULE_IMPORT_FAILED",
                        "DaVinci Resolve scripting module was found but could not be imported",
                        ProductErrorCategory.EXTERNAL_DEPENDENCY,
                        retryable=False,
                        details={"exception_type": type(exc).__name__, "platform": self.platform_name},
                    ) from exc
                return ResolveModuleDiscovery(module, source_kind)
        finally:
            # Do not leave probe-only host paths in process-wide import state.
            sys.path[:] = original

        raise ProductError(
            "ERR_RESOLVE_SCRIPT_MODULE_NOT_FOUND",
            "DaVinci Resolve scripting module could not be discovered locally",
            ProductErrorCategory.EXTERNAL_DEPENDENCY,
            retryable=False,
            details={"platform": self.platform_name},
        )

    def connect(self) -> tuple[object, str]:
        discovery = self.discover()
        scriptapp = getattr(discovery.module, "scriptapp", None)
        if not callable(scriptapp):
            raise ProductError(
                "ERR_RESOLVE_SCRIPTAPP_MISSING",
                "DaVinci Resolve scripting module does not expose scriptapp",
                ProductErrorCategory.NOT_SUPPORTED,
                details={"module_source_kind": discovery.source_kind},
            )
        try:
            resolve = scriptapp("Resolve")
        except Exception as exc:  # native scripting bridge exceptions vary by version
            raise ProductError(
                "ERR_RESOLVE_CONNECT_FAILED",
                "DaVinci Resolve scripting connection failed",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                retryable=True,
                details={
                    "exception_type": type(exc).__name__,
                    "module_source_kind": discovery.source_kind,
                },
            ) from exc
        if resolve is None:
            raise ProductError(
                "ERR_RESOLVE_NOT_AVAILABLE",
                "DaVinci Resolve is not available through the scripting bridge",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                retryable=True,
                details={"module_source_kind": discovery.source_kind},
            )
        return resolve, discovery.source_kind
