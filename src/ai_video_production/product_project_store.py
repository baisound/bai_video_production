"""TASK-043 crash-safe manifest store with exact compare-and-swap."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
from typing import Any, Iterator, Mapping

from .atomic import AtomicJsonWriter, AtomicWriteResult
from .errors import ProductError, ProductErrorCategory
from .product_project import ProductProjectManifest, parse_product_project_manifest
from .serialization import canonical_json_bytes, sha256_bytes
from .task102_project_manifest_transaction import parse_private_request
from .task102_project_writer_migration import (
    DEFAULT_PMST_WRITER_MIGRATION_ROUTER,
    PmstWriterMigrationRouter,
)


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
        pmst_router: PmstWriterMigrationRouter | None = None,
        pmst_route_id: str = "PMST-R001",
        pmst_private_request: Mapping[str, Any] | None = None,
    ) -> AtomicWriteResult:
        router = pmst_router or DEFAULT_PMST_WRITER_MIGRATION_ROUTER
        if pmst_private_request is not None:
            ProductProjectManifestStore._validate_pmst_request(
                project_root,
                pmst_private_request,
                manifest,
                expected_previous_manifest_sha256=expected_previous_manifest_sha256,
            )
            result = router.execute(
                project_root,
                route_id=pmst_route_id,
                private_request=pmst_private_request,
            )
            if result.data["status"] != "COMMITTED_WITH_READBACK":
                raise ProductError(
                    "ERR_PMST_MANIFEST_NOT_COMMITTED",
                    "PMST did not report a committed manifest with readback",
                    ProductErrorCategory.STATE,
                    details={"route_id": pmst_route_id, "status": result.data["status"]},
                )
            try:
                live = ProductProjectManifestStore.load(project_root)
            except ProductError as exc:
                raise ProductError(
                    "ERR_PMST_MANIFEST_READBACK_INVALID",
                    "PMST manifest readback is missing or invalid",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"route_id": pmst_route_id},
                ) from exc
            if live.project_manifest_sha256 != manifest.project_manifest_sha256:
                raise ProductError(
                    "ERR_PMST_MANIFEST_READBACK_MISMATCH",
                    "PMST manifest readback does not match the requested successor",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"route_id": pmst_route_id},
                )
            document = canonical_json_bytes(live.to_dict())
            return AtomicWriteResult(
                _manifest_path(project_root),
                sha256_bytes(document),
                len(document) + 1,
            )
        router.require_legacy_access(
            project_root,
            route_id=pmst_route_id,
            access_kind="MUTATION",
        )
        target = _manifest_path(project_root, create_control_dir=True)
        with _exclusive_project_lock(target):
            return ProductProjectManifestStore._save_unlocked(
                project_root,
                manifest,
                expected_previous_manifest_sha256=expected_previous_manifest_sha256,
                pmst_router=router,
                pmst_route_id=pmst_route_id,
            )

    @staticmethod
    def _save_unlocked(
        project_root: str | Path,
        manifest: ProductProjectManifest,
        *,
        expected_previous_manifest_sha256: str | None,
        pmst_router: PmstWriterMigrationRouter | None = None,
        pmst_route_id: str = "PMST-R001",
    ) -> AtomicWriteResult:
        """Save while the caller holds the Project lock.

        This is package-internal and exists for the multi-store save coordinator.
        """
        router = pmst_router or DEFAULT_PMST_WRITER_MIGRATION_ROUTER
        router.require_legacy_access(
            project_root,
            route_id=pmst_route_id,
            access_kind="MUTATION",
        )
        target = _manifest_path(project_root, create_control_dir=True)
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

    @staticmethod
    def _validate_pmst_request(
        project_root: str | Path,
        private_request: Mapping[str, Any],
        manifest: ProductProjectManifest,
        *,
        expected_previous_manifest_sha256: str | None,
    ) -> None:
        try:
            request = parse_private_request(private_request)
        except (TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_PMST_PRIVATE_REQUEST_INVALID",
                "PMST manifest request is invalid",
                ProductErrorCategory.VALIDATION,
            ) from exc
        intent = request.to_dict()["intent"]
        payload = intent["payload"]
        if payload.get("successor_manifest") != manifest.to_dict():
            raise ProductError(
                "ERR_PMST_MANIFEST_REQUEST_MISMATCH",
                "PMST request successor does not match the supplied manifest",
                ProductErrorCategory.SECURITY,
            )
        kind = intent["operation_kind"]
        if expected_previous_manifest_sha256 is None:
            matches = kind == "MANIFEST_CREATE_V1" and manifest.project_revision == 1
            if _manifest_path(project_root).exists():
                matches = False
        else:
            matches = (
                kind == "MANIFEST_TRANSITION_V1"
                and payload.get("prior_manifest_sha256") == expected_previous_manifest_sha256
            )
            if matches:
                try:
                    current = ProductProjectManifestStore.load(project_root)
                except ProductError:
                    matches = False
                else:
                    matches = (
                        current.project_manifest_sha256 == expected_previous_manifest_sha256
                        and current.project_id == manifest.project_id
                        and current.created_at == manifest.created_at
                        and manifest.project_revision == current.project_revision + 1
                    )
        if not matches:
            raise ProductError(
                "ERR_PMST_MANIFEST_PREDECESSOR_MISMATCH",
                "PMST request does not match the supplied manifest predecessor",
                ProductErrorCategory.SECURITY,
            )

