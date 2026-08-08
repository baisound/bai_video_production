from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
import re
from typing import Literal

from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, validate_id

_DRIVE_OR_UNC = re.compile(r"^(?:[A-Za-z]:|\\\\)")

@dataclass(frozen=True, slots=True)
class PathMapping:
    logical_prefix: str
    wsl_root: Path
    windows_root: PureWindowsPath | None = None

    def __post_init__(self) -> None:
        if self.logical_prefix not in {"asset://", "job://"}:
            raise ValueError("logical_prefix must be asset:// or job://")
        if not self.wsl_root.is_absolute():
            raise ValueError("wsl_root must be absolute")

class LogicalPathResolver:
    def __init__(self, mappings: list[PathMapping]) -> None:
        if not mappings:
            raise ValueError("at least one path mapping is required")
        self._mappings = {m.logical_prefix: m for m in mappings}
        if len(self._mappings) != len(mappings):
            raise ValueError("duplicate logical_prefix")

    @staticmethod
    def _relative(logical_uri: str, prefix: str) -> str:
        relative = logical_uri[len(prefix):]
        if not relative or relative.startswith(('/', '\\')):
            raise ProductError("ERR_SECURITY_PATH_DENIED", "invalid logical URI", ProductErrorCategory.SECURITY)
        if "\x00" in relative or "\\" in relative or _DRIVE_OR_UNC.match(relative):
            raise ProductError("ERR_SECURITY_PATH_DENIED", "path escape syntax is forbidden", ProductErrorCategory.SECURITY)
        parts = relative.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise ProductError("ERR_SECURITY_PATH_DENIED", "path traversal is forbidden", ProductErrorCategory.SECURITY)
        try:
            validate_id(parts[0], IdKind.JOB)
        except ValueError as exc:
            raise ProductError("ERR_SECURITY_PATH_DENIED", "logical URI must be scoped by a valid Production Job ID", ProductErrorCategory.SECURITY) from exc
        return relative

    def _mapping(self, logical_uri: str) -> tuple[PathMapping, str]:
        for prefix, mapping in self._mappings.items():
            if logical_uri.startswith(prefix):
                return mapping, self._relative(logical_uri, prefix)
        raise ProductError("ERR_SECURITY_PATH_DENIED", "logical URI prefix is not allowlisted", ProductErrorCategory.SECURITY)

    def resolve(self, logical_uri: str, *, environment: Literal["wsl", "windows"] = "wsl") -> Path | PureWindowsPath:
        mapping, relative = self._mapping(logical_uri)
        if environment == "windows":
            if mapping.windows_root is None:
                raise ProductError("ERR_SECURITY_PATH_UNRESOLVED", "Windows mapping is unavailable", ProductErrorCategory.SECURITY)
            # Lexical translation only. The Windows execution owner MUST repeat
            # canonical/symlink checks on the Windows host before I/O.
            return mapping.windows_root.joinpath(*relative.split("/"))

        root = mapping.wsl_root.resolve(strict=False)
        candidate = (root / relative).resolve(strict=False)
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ProductError("ERR_SECURITY_PATH_DENIED", "resolved path escapes allowlisted root", ProductErrorCategory.SECURITY) from exc
        return candidate
