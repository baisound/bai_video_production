"""TASK-043 crash-safe manifest store with exact compare-and-swap."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
from typing import Iterator

from .atomic import AtomicJsonWriter, AtomicWriteResult
from .errors import ProductError, ProductErrorCategory
from .product_project import ProductProjectManifest, parse_product_project_manifest


_MAX_MANIFEST_BYTES = 4 * 1024 * 1024
_CONTROL_DIR = ".bai-project"
_MANIFEST_NAME = "project.json"


def _project_root(value: str | Path) -> Path:
    root = Path(value)
    if root.is_symlink() or not root.is_dir():
        raise ProductError("ERR_PROJECT_FORMAT_ROOT_INVALID", "Project root must be an existing regular directory", ProductErrorCategory.SECURITY)
    return root.resolve(strict=True)


def _manifest_path(value: str | Path, *, create_control_dir: bool = False) -> Path:
    root = _project_root(value)
    control = root / _CONTROL_DIR
    if create_control_dir and not control.exists():
        control.mkdir(mode=0o700)
    if control.is_symlink() or (control.exists() and not control.is_dir()):
        raise ProductError("ERR_PROJECT_FORMAT_CONTROL_DIR_INVALID", "Project control directory must not be a symlink", ProductErrorCategory.SECURITY)
    return control / _MANIFEST_NAME


@contextmanager
def _exclusive_project_lock(target: Path) -> Iterator[None]:
    lock_path = target.with_name(f".{target.name}.lock")
    if lock_path.is_symlink() or (lock_path.exists() and not lock_path.is_file()):
        raise ProductError("ERR_PROJECT_SAVE_LOCK_INVALID", "Project lock must be a regular non-symlink file", ProductErrorCategory.SECURITY)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        locked = False
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            locked = True
            yield
        finally:
            if locked:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class ProductProjectManifestStore:
    @staticmethod
    def path(project_root: str | Path) -> Path:
        return _manifest_path(project_root)

    @staticmethod
    def load(project_root: str | Path) -> ProductProjectManifest:
        target = _manifest_path(project_root)
        if target.is_symlink() or not target.is_file():
            raise ProductError("ERR_PROJECT_FORMAT_FILE_INVALID", "Project manifest must be a regular non-symlink file", ProductErrorCategory.VALIDATION)
        size = target.stat().st_size
        if size <= 0 or size > _MAX_MANIFEST_BYTES:
            raise ProductError("ERR_PROJECT_FORMAT_SIZE", "Project manifest size is outside the allowed bound", ProductErrorCategory.VALIDATION, details={"size_bytes": size})
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_PROJECT_FORMAT_READ", "Project manifest could not be read as UTF-8 JSON", ProductErrorCategory.DATA_INTEGRITY) from exc
        return parse_product_project_manifest(document)

    @staticmethod
    def save(
        project_root: str | Path,
        manifest: ProductProjectManifest,
        *,
        expected_previous_manifest_sha256: str | None = None,
    ) -> AtomicWriteResult:
        target = _manifest_path(project_root, create_control_dir=True)
        with _exclusive_project_lock(target):
            if target.is_symlink() or (target.exists() and not target.is_file()):
                raise ProductError("ERR_PROJECT_FORMAT_FILE_INVALID", "Refusing an invalid Project manifest target", ProductErrorCategory.SECURITY)
            if target.exists():
                if expected_previous_manifest_sha256 is None:
                    raise ProductError("ERR_PROJECT_SAVE_CAS_REQUIRED", "Replacing a Project manifest requires its exact checksum", ProductErrorCategory.AUTHORIZATION)
                current = ProductProjectManifestStore.load(project_root)
                if current.project_manifest_sha256 != expected_previous_manifest_sha256:
                    raise ProductError("ERR_PROJECT_SAVE_REVISION_CONFLICT", "Project manifest changed before save", ProductErrorCategory.STATE, details={"current_manifest_sha256": current.project_manifest_sha256})
                if manifest.project_id != current.project_id or manifest.created_at != current.created_at:
                    raise ProductError("ERR_PROJECT_SAVE_IDENTITY_CONFLICT", "Project identity or creation timestamp cannot change", ProductErrorCategory.STATE)
                if manifest.project_revision != current.project_revision + 1:
                    raise ProductError("ERR_PROJECT_SAVE_REVISION_INVALID", "Project revision must advance exactly once", ProductErrorCategory.STATE)
            elif expected_previous_manifest_sha256 is not None:
                raise ProductError("ERR_PROJECT_SAVE_PREVIOUS_MISSING", "Expected previous Project manifest does not exist", ProductErrorCategory.STATE)
            elif manifest.project_revision != 1:
                raise ProductError("ERR_PROJECT_SAVE_REVISION_INVALID", "First Project manifest revision must be 1", ProductErrorCategory.STATE)
            return AtomicJsonWriter.write(target, manifest.to_dict(), validator=parse_product_project_manifest)

