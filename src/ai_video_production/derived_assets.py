from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
from typing import Any

from .assets import (
    AssetRecord, AssetType, AudioRightsStatus, PermissionState, RetentionClass, RightsStatus,
)
from .errors import ProductError, ProductErrorCategory
from .paths import LogicalPathResolver
from .store import SQLiteProductStore

_SAFE_NAMESPACE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_SAFE_SUFFIX = re.compile(r"^\.[A-Za-z0-9]{1,10}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def make_read_only(path: Path) -> None:
    path.chmod(path.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def directory_fsync(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


@dataclass(frozen=True, slots=True)
class DerivedAssetSpec:
    production_job_id: str
    namespace: str
    asset_type: AssetType
    owner: str
    rights_status: RightsStatus = RightsStatus.UNKNOWN
    retention_class: RetentionClass = RetentionClass.STANDARD
    commercial_use: PermissionState = PermissionState.UNKNOWN
    derivative_allowed: PermissionState = PermissionState.UNKNOWN
    reuse_allowed: PermissionState = PermissionState.UNKNOWN
    audio_rights_status: AudioRightsStatus = AudioRightsStatus.NOT_APPLICABLE
    generation_provenance: dict[str, Any] | None = None
    media_metadata: dict[str, Any] | None = None
    source_ref: str | None = None
    source_project: str | None = None
    attribution: str | None = None
    publication_restrictions: tuple[str, ...] = ()


class DerivedAssetPublisher:
    """Single checksum-addressed publication path for TASK-004 local outputs."""

    def __init__(self, *, store: SQLiteProductStore, resolver: LogicalPathResolver) -> None:
        self.store = store
        self.resolver = resolver

    @staticmethod
    def _validate_source(source: Path) -> Path:
        if source.is_symlink():
            raise ProductError("ERR_SECURITY_DERIVED_SOURCE_SYMLINK", "derived source symlinks are forbidden", ProductErrorCategory.SECURITY)
        try:
            resolved = source.resolve(strict=True)
        except FileNotFoundError as exc:
            raise ProductError("ERR_INPUT_DERIVED_OUTPUT_MISSING", "derived output file is missing", ProductErrorCategory.VALIDATION) from exc
        if not resolved.is_file():
            raise ProductError("ERR_INPUT_DERIVED_OUTPUT_NOT_FILE", "derived output must be a regular file", ProductErrorCategory.VALIDATION)
        if resolved.stat().st_size <= 0:
            raise ProductError("ERR_INPUT_DERIVED_OUTPUT_EMPTY", "derived output must not be empty", ProductErrorCategory.VALIDATION)
        return resolved

    def publish(self, source: str | Path, spec: DerivedAssetSpec, *, operation_id: str) -> AssetRecord:
        if not _SAFE_NAMESPACE.fullmatch(spec.namespace):
            raise ValueError("namespace must be lowercase safe token")
        src = self._validate_source(Path(source))
        checksum = sha256_file(src)
        existing = self.store.find_asset_by_checksum(spec.production_job_id, checksum)
        if existing is not None:
            target = self.resolver.resolve(existing.logical_uri)
            if not isinstance(target, Path) or not target.exists() or sha256_file(target) != existing.checksum:
                raise ProductError(
                    "ERR_INTEGRITY_REGISTERED_ASSET_CHECKSUM_MISMATCH",
                    "existing checksum-deduplicated Asset is missing or tampered",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"asset_id": existing.asset_id},
                )
            return existing

        suffix = src.suffix.lower() if _SAFE_SUFFIX.fullmatch(src.suffix) else ".bin"
        hexsum = checksum.removeprefix("sha256:")
        logical_uri = f"asset://{spec.production_job_id}/derived/{spec.namespace}/{hexsum}{suffix}"
        self.resolver.assert_job_scope(logical_uri, spec.production_job_id)
        target = self.resolver.resolve(logical_uri)
        assert isinstance(target, Path)
        target.parent.mkdir(parents=True, exist_ok=True)
        staging = target.parent / f".{operation_id}.part"
        staging.unlink(missing_ok=True)
        try:
            with src.open("rb") as inp, staging.open("xb") as out:
                shutil.copyfileobj(inp, out, 4 * 1024 * 1024)
                out.flush()
                os.fsync(out.fileno())
            if sha256_file(staging) != checksum:
                raise ProductError("ERR_INTEGRITY_DERIVED_COPY_MISMATCH", "derived staged copy checksum changed", ProductErrorCategory.DATA_INTEGRITY)
            if target.exists():
                if sha256_file(target) != checksum:
                    raise ProductError("ERR_INTEGRITY_DERIVED_TARGET_COLLISION", "derived target collision", ProductErrorCategory.DATA_INTEGRITY)
                staging.unlink(missing_ok=True)
            else:
                os.replace(staging, target)
                directory_fsync(target.parent)
            make_read_only(target)

            record = AssetRecord(
                production_job_id=spec.production_job_id,
                asset_type=spec.asset_type,
                logical_uri=logical_uri,
                checksum=checksum,
                rights_status=spec.rights_status,
                owner=spec.owner,
                original_name=src.name,
                retention_class=spec.retention_class,
                commercial_use=spec.commercial_use,
                derivative_allowed=spec.derivative_allowed,
                reuse_allowed=spec.reuse_allowed,
                audio_rights_status=spec.audio_rights_status,
                source_ref=spec.source_ref,
                source_project=spec.source_project,
                attribution=spec.attribution,
                publication_restrictions=spec.publication_restrictions,
                generation_provenance=dict(spec.generation_provenance or {}),
                media_metadata=dict(spec.media_metadata or {}),
            )
            try:
                self.store.register_asset(record, producer_operation_id=operation_id)
                return record
            except ProductError as exc:
                if exc.code != "ERR_INTEGRITY_ASSET_REGISTRY_CONFLICT":
                    raise
                concurrent = self.store.find_asset_by_checksum(spec.production_job_id, checksum)
                if concurrent is None:
                    raise
                return concurrent
        finally:
            staging.unlink(missing_ok=True)
