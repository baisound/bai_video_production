from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
import re
from typing import Literal

from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, validate_id

_DRIVE_OR_UNC = re.compile(r"^(?:[A-Za-z]:|\\\\)")
_OBJECT_ROOT = re.compile(r"^[a-z][a-z0-9+.-]*://[^/].*$", re.I)


@dataclass(frozen=True, slots=True)
class PathMapping:
    logical_prefix: str
    wsl_root: Path
    windows_root: PureWindowsPath | None = None
    object_root: str | None = None

    def __post_init__(self) -> None:
        if self.logical_prefix not in {"asset://", "job://"}:
            raise ValueError("logical_prefix must be asset:// or job://")
        if not self.wsl_root.is_absolute():
            raise ValueError("wsl_root must be absolute")
        if self.object_root is not None:
            root = self.object_root.rstrip("/")
            if not _OBJECT_ROOT.fullmatch(root):
                raise ValueError("object_root must be an absolute object-storage URI")
            object.__setattr__(self, "object_root", root)


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
        if not relative or relative.startswith(("/", "\\")):
            raise ProductError("ERR_SECURITY_PATH_DENIED", "invalid logical URI", ProductErrorCategory.SECURITY)
        if "\x00" in relative or "\\" in relative or _DRIVE_OR_UNC.match(relative):
            raise ProductError("ERR_SECURITY_PATH_DENIED", "path escape syntax is forbidden", ProductErrorCategory.SECURITY)
        parts = relative.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise ProductError("ERR_SECURITY_PATH_DENIED", "path traversal is forbidden", ProductErrorCategory.SECURITY)
        try:
            validate_id(parts[0], IdKind.JOB)
        except ValueError as exc:
            raise ProductError(
                "ERR_SECURITY_PATH_DENIED",
                "logical URI must be scoped by a valid Production Job ID",
                ProductErrorCategory.SECURITY,
            ) from exc
        return relative

    def _mapping(self, logical_uri: str) -> tuple[PathMapping, str]:
        for prefix, mapping in self._mappings.items():
            if logical_uri.startswith(prefix):
                return mapping, self._relative(logical_uri, prefix)
        raise ProductError("ERR_SECURITY_PATH_DENIED", "logical URI prefix is not allowlisted", ProductErrorCategory.SECURITY)

    def assert_job_scope(self, logical_uri: str, job_id: str) -> str:
        validate_id(job_id, IdKind.JOB)
        mapping, relative = self._mapping(logical_uri)
        del mapping
        if relative.split("/", 1)[0] != job_id:
            raise ProductError(
                "ERR_SECURITY_PATH_DENIED",
                "logical URI does not belong to the requested Production Job",
                ProductErrorCategory.SECURITY,
            )
        return logical_uri

    def resolve(
        self,
        logical_uri: str,
        *,
        environment: Literal["wsl", "windows", "object"] = "wsl",
    ) -> Path | PureWindowsPath | str:
        mapping, relative = self._mapping(logical_uri)
        if environment == "windows":
            if mapping.windows_root is None:
                raise ProductError("ERR_SECURITY_PATH_UNRESOLVED", "Windows mapping is unavailable", ProductErrorCategory.SECURITY)
            # Lexical translation only. The Windows execution owner MUST repeat
            # canonical/symlink checks on the Windows host before I/O.
            return mapping.windows_root.joinpath(*relative.split("/"))
        if environment == "object":
            if mapping.object_root is None:
                raise ProductError("ERR_SECURITY_PATH_UNRESOLVED", "Object-storage mapping is unavailable", ProductErrorCategory.SECURITY)
            return mapping.object_root + "/" + relative

        root = mapping.wsl_root.resolve(strict=False)
        candidate = (root / relative).resolve(strict=False)
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ProductError("ERR_SECURITY_PATH_DENIED", "resolved path escapes allowlisted root", ProductErrorCategory.SECURITY) from exc
        return candidate


@dataclass(frozen=True, slots=True)
class SourcePathPolicy:
    """Runtime allowlist for raw source paths entering the Ingest boundary.

    Raw environment paths are permitted only at this boundary and are never
    copied into canonical manifests/evidence. The caller must configure one or
    more trusted import roots explicitly.
    """

    allowed_roots: tuple[Path, ...]

    def __post_init__(self) -> None:
        if not self.allowed_roots:
            raise ValueError("at least one allowed source root is required")
        normalized: list[Path] = []
        for root in self.allowed_roots:
            if not root.is_absolute():
                raise ValueError("allowed source roots must be absolute")
            try:
                resolved = root.resolve(strict=True)
            except FileNotFoundError as exc:
                raise ValueError(f"allowed source root does not exist: {root}") from exc
            if not resolved.is_dir():
                raise ValueError(f"allowed source root is not a directory: {root}")
            normalized.append(resolved)
        object.__setattr__(self, "allowed_roots", tuple(normalized))

    def authorize_file(self, path: str | Path) -> Path:
        raw = Path(path)
        if "\x00" in str(raw):
            raise ProductError("ERR_SECURITY_PATH_DENIED", "source path contains NUL", ProductErrorCategory.SECURITY)
        if raw.is_symlink():
            raise ProductError("ERR_SECURITY_PATH_DENIED", "source file symlinks are not accepted for ingest", ProductErrorCategory.SECURITY)
        try:
            resolved = raw.resolve(strict=True)
        except FileNotFoundError as exc:
            raise ProductError("ERR_INPUT_SOURCE_NOT_FOUND", "ingest source file does not exist", ProductErrorCategory.VALIDATION) from exc
        if not resolved.is_file():
            raise ProductError("ERR_INPUT_SOURCE_NOT_FILE", "ingest source must be a regular file", ProductErrorCategory.VALIDATION)
        allowed = False
        for root in self.allowed_roots:
            try:
                resolved.relative_to(root)
                allowed = True
                break
            except ValueError:
                continue
        if not allowed:
            raise ProductError(
                "ERR_SECURITY_PATH_DENIED",
                "source path is outside the configured ingest allowlist",
                ProductErrorCategory.SECURITY,
            )
        return resolved
