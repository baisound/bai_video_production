"""Portable backup / restore for TASK-049 DbD Game Intelligence user data.

The bundle is intended for machine migration, not as a replacement for the
existing Product Project backup history.  It packages only bounded DbD data
surfaces and deliberately excludes provider credentials / API secrets.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import tempfile
from typing import Iterable, Iterator
import uuid
import zipfile

from .dbd_training_workspace import default_training_workspace_root
from .dbd_trivia_editor import default_trivia_database_path
from .serialization import canonical_json_bytes, sha256_bytes


_BUNDLE_FORMAT = "bvp.dbd-data-migration"
_SCHEMA_VERSION = "1.0.0"
_MANIFEST_MEMBER = "manifest.json"
_DATA_PREFIX = "data/"
_PROJECT_SCOPE = "project-game-intelligence"
_TRAINING_SCOPE = "training-workspace"
_TRIVIA_SCOPE = "global-trivia"
_MAX_FILES = 100_000
_MAX_TOTAL_BYTES = 50 * 1024 * 1024 * 1024
_MAX_FILE_BYTES = 8 * 1024 * 1024 * 1024
_SECRET_NAMES = {
    ".env",
    "credentials.json",
    "credential.json",
    "secrets.json",
    "secret.json",
    "api-keys.json",
    "api-key.json",
}
_SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
_SQLITE_SUFFIXES = {".sqlite", ".sqlite3", ".db"}


class DbDDataMigrationError(ValueError):
    """Raised when a migration bundle is unsafe, corrupt, or incompatible."""


@dataclass(frozen=True)
class MigrationEntry:
    logical_path: str
    scope: str
    size_bytes: int
    sha256: str
    sqlite_snapshot: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "logical_path": self.logical_path,
            "scope": self.scope,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "sqlite_snapshot": self.sqlite_snapshot,
        }


@dataclass(frozen=True)
class MigrationBackupReceipt:
    bundle_id: str
    path: Path
    entry_count: int
    total_bytes: int
    scopes: tuple[str, ...]
    excluded_paths: tuple[str, ...]
    manifest_sha256: str


@dataclass(frozen=True)
class MigrationRestorePreview:
    bundle_id: str
    path: Path
    entry_count: int
    total_bytes: int
    scopes: tuple[str, ...]
    conflicts: tuple[str, ...]
    requires_project_root: bool
    manifest_sha256: str


@dataclass(frozen=True)
class MigrationRestoreReceipt:
    bundle_id: str
    restored_files: int
    replaced_files: int
    new_files: int
    safety_backup_path: Path | None
    manifest_sha256: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _local_product_root() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    root = Path(local) if local else Path.home() / ".local" / "share"
    return root / "BAI Video Production"


def default_restore_safety_root() -> Path:
    return _local_product_root() / "migration-restore-backups"


def _is_secret_path(path: Path) -> bool:
    name = path.name.lower()
    if name in _SECRET_NAMES or path.suffix.lower() in _SECRET_SUFFIXES:
        return True
    return name.startswith(".env.") or "credential" in name or "api-key" in name


def _safe_relative_path(value: str) -> PurePosixPath:
    p = PurePosixPath(value)
    if p.is_absolute() or not p.parts or any(part in {"", ".", ".."} for part in p.parts):
        raise DbDDataMigrationError(f"unsafe logical path: {value}")
    if ":" in p.parts[0] or "\\" in value:
        raise DbDDataMigrationError(f"unsafe logical path: {value}")
    return p


def _hash_file(path: Path) -> tuple[int, str]:
    size = 0
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    return size, "sha256:" + digest.hexdigest()


def _copy_stream(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as src, target.open("wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)


def _sqlite_snapshot(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        source_conn = sqlite3.connect(f"file:{source.resolve().as_posix()}?mode=ro", uri=True, timeout=5.0)
        try:
            dest_conn = sqlite3.connect(target)
            try:
                source_conn.backup(dest_conn)
                dest_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                dest_conn.commit()
            finally:
                dest_conn.close()
        finally:
            source_conn.close()
    except sqlite3.DatabaseError as exc:
        raise DbDDataMigrationError(f"cannot snapshot SQLite database {source}: {exc}") from exc


def _iter_source_files(root: Path) -> Iterator[Path]:
    if not root.exists():
        return
    if root.is_symlink():
        raise DbDDataMigrationError(f"migration source root must not be a symlink: {root}")
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise DbDDataMigrationError(f"migration source contains symlink: {path}")
        if path.is_file():
            # SQLite sidecars are transient; the canonical DB is snapshotted instead.
            if path.name.endswith("-wal") or path.name.endswith("-shm"):
                continue
            yield path


class DbDDataMigrationService:
    """Creates and restores portable, checksum-verified DbD data bundles."""

    def __init__(
        self,
        *,
        training_root: str | Path | None = None,
        trivia_database_path: str | Path | None = None,
        safety_backup_root: str | Path | None = None,
    ) -> None:
        self.training_root = Path(training_root) if training_root is not None else default_training_workspace_root()
        self.trivia_database_path = Path(trivia_database_path) if trivia_database_path is not None else default_trivia_database_path()
        self.safety_backup_root = Path(safety_backup_root) if safety_backup_root is not None else default_restore_safety_root()

    @staticmethod
    def _project_state_root(project_root: str | Path) -> Path:
        return Path(project_root) / ".bvp" / "game-intelligence"

    def _sources(
        self,
        *,
        project_root: str | Path | None,
        include_project: bool,
        include_training: bool,
        include_trivia: bool,
    ) -> list[tuple[str, Path, bool]]:
        sources: list[tuple[str, Path, bool]] = []
        if include_project:
            if project_root is None:
                raise DbDDataMigrationError("project_root is required when project Game Intelligence data is selected")
            sources.append((_PROJECT_SCOPE, self._project_state_root(project_root), True))
        if include_training:
            sources.append((_TRAINING_SCOPE, self.training_root, True))
        if include_trivia:
            sources.append((_TRIVIA_SCOPE, self.trivia_database_path, False))
        return sources

    def create_backup(
        self,
        output_path: str | Path,
        *,
        project_root: str | Path | None = None,
        include_project: bool = True,
        include_training: bool = True,
        include_trivia: bool = True,
    ) -> MigrationBackupReceipt:
        output = Path(output_path)
        if output.suffix.lower() != ".zip":
            output = output.with_suffix(".zip")
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists() and output.is_symlink():
            raise DbDDataMigrationError("backup output must not be a symlink")

        selected_scopes: list[str] = []
        excluded: list[str] = []
        entries: list[MigrationEntry] = []
        total_bytes = 0
        seen_logical: set[str] = set()

        with tempfile.TemporaryDirectory(prefix="bvp-dbd-migration-backup-") as temp_name:
            staging = Path(temp_name)
            staged_files: list[tuple[MigrationEntry, Path]] = []
            for scope, source, is_directory in self._sources(
                project_root=project_root,
                include_project=include_project,
                include_training=include_training,
                include_trivia=include_trivia,
            ):
                selected_scopes.append(scope)
                if not source.exists():
                    continue
                source = source.resolve()
                files: Iterable[Path]
                if is_directory:
                    files = _iter_source_files(source)
                else:
                    if source.is_symlink():
                        raise DbDDataMigrationError(f"migration source must not be a symlink: {source}")
                    files = (source,) if source.is_file() else ()

                for file_path in files:
                    rel = file_path.relative_to(source).as_posix() if is_directory else file_path.name
                    logical = f"{scope}/{rel}"
                    _safe_relative_path(logical)
                    if logical in seen_logical:
                        raise DbDDataMigrationError(f"duplicate migration logical path: {logical}")
                    seen_logical.add(logical)
                    if _is_secret_path(file_path):
                        excluded.append(logical)
                        continue
                    if len(entries) >= _MAX_FILES:
                        raise DbDDataMigrationError("backup exceeds maximum file count")

                    staged = staging / logical
                    sqlite_snapshot = file_path.suffix.lower() in _SQLITE_SUFFIXES
                    if sqlite_snapshot:
                        _sqlite_snapshot(file_path, staged)
                    else:
                        _copy_stream(file_path, staged)
                    size, checksum = _hash_file(staged)
                    if size > _MAX_FILE_BYTES:
                        raise DbDDataMigrationError(f"backup file exceeds bounded size: {logical}")
                    total_bytes += size
                    if total_bytes > _MAX_TOTAL_BYTES:
                        raise DbDDataMigrationError("backup exceeds bounded total size")
                    entry = MigrationEntry(logical, scope, size, checksum, sqlite_snapshot)
                    entries.append(entry)
                    staged_files.append((entry, staged))

            bundle_id = "dbd-migration-" + uuid.uuid4().hex
            manifest_payload = {
                "format": _BUNDLE_FORMAT,
                "schema_version": _SCHEMA_VERSION,
                "bundle_id": bundle_id,
                "created_at": _utc_now(),
                "writer_quiescence_required": True,
                "credentials_included": False,
                "scopes": sorted(set(selected_scopes)),
                "entry_count": len(entries),
                "total_bytes": total_bytes,
                "excluded_paths": sorted(excluded),
                "entries": [entry.to_dict() for entry in entries],
            }
            manifest_sha = sha256_bytes(canonical_json_bytes(manifest_payload))
            manifest = {**manifest_payload, "manifest_sha256": manifest_sha}

            temporary = output.with_name(output.name + ".tmp-" + uuid.uuid4().hex)
            try:
                with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
                    for entry, staged in staged_files:
                        archive.write(staged, arcname=_DATA_PREFIX + entry.logical_path)
                    archive.writestr(_MANIFEST_MEMBER, canonical_json_bytes(manifest))
                os.replace(temporary, output)
            finally:
                if temporary.exists():
                    temporary.unlink(missing_ok=True)

        return MigrationBackupReceipt(
            bundle_id=bundle_id,
            path=output,
            entry_count=len(entries),
            total_bytes=total_bytes,
            scopes=tuple(sorted(set(selected_scopes))),
            excluded_paths=tuple(sorted(excluded)),
            manifest_sha256=manifest_sha,
        )

    @staticmethod
    def _load_verified_manifest(bundle_path: str | Path) -> tuple[dict[str, object], tuple[MigrationEntry, ...]]:
        bundle = Path(bundle_path)
        if not bundle.is_file() or bundle.is_symlink():
            raise DbDDataMigrationError("migration bundle must be a regular ZIP file")
        try:
            with zipfile.ZipFile(bundle, "r") as archive:
                names = archive.namelist()
                if len(names) != len(set(names)):
                    raise DbDDataMigrationError("migration bundle contains duplicate archive members")
                if _MANIFEST_MEMBER not in names:
                    raise DbDDataMigrationError("migration bundle manifest is missing")
                raw_manifest = archive.read(_MANIFEST_MEMBER)
                manifest = json.loads(raw_manifest.decode("utf-8"))
        except (zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DbDDataMigrationError(f"invalid migration bundle: {exc}") from exc
        if not isinstance(manifest, dict):
            raise DbDDataMigrationError("migration manifest must be an object")
        if manifest.get("format") != _BUNDLE_FORMAT or manifest.get("schema_version") != _SCHEMA_VERSION:
            raise DbDDataMigrationError("unsupported migration bundle format or schema version")
        recorded_manifest_sha = str(manifest.get("manifest_sha256", ""))
        payload = dict(manifest)
        payload.pop("manifest_sha256", None)
        actual_manifest_sha = sha256_bytes(canonical_json_bytes(payload))
        if recorded_manifest_sha != actual_manifest_sha:
            raise DbDDataMigrationError("migration manifest checksum mismatch")
        if manifest.get("credentials_included") is not False:
            raise DbDDataMigrationError("migration bundle credential policy is invalid")

        raw_entries = manifest.get("entries")
        if not isinstance(raw_entries, list):
            raise DbDDataMigrationError("migration manifest entries must be a list")
        entries: list[MigrationEntry] = []
        logical_seen: set[str] = set()
        total_bytes = 0
        for item in raw_entries:
            if not isinstance(item, dict):
                raise DbDDataMigrationError("migration entry must be an object")
            logical = str(item.get("logical_path", ""))
            p = _safe_relative_path(logical)
            scope = str(item.get("scope", ""))
            if p.parts[0] != scope or scope not in {_PROJECT_SCOPE, _TRAINING_SCOPE, _TRIVIA_SCOPE}:
                raise DbDDataMigrationError(f"migration entry scope mismatch: {logical}")
            if logical in logical_seen:
                raise DbDDataMigrationError(f"duplicate migration logical path: {logical}")
            logical_seen.add(logical)
            size = int(item.get("size_bytes", -1))
            checksum = str(item.get("sha256", ""))
            if size < 0 or size > _MAX_FILE_BYTES or not checksum.startswith("sha256:") or len(checksum) != 71:
                raise DbDDataMigrationError(f"invalid migration entry metadata: {logical}")
            total_bytes += size
            if total_bytes > _MAX_TOTAL_BYTES:
                raise DbDDataMigrationError("migration bundle exceeds bounded total size")
            entries.append(MigrationEntry(logical, scope, size, checksum, bool(item.get("sqlite_snapshot", False))))
        if len(entries) > _MAX_FILES:
            raise DbDDataMigrationError("migration bundle exceeds maximum file count")
        if int(manifest.get("entry_count", -1)) != len(entries) or int(manifest.get("total_bytes", -1)) != total_bytes:
            raise DbDDataMigrationError("migration manifest aggregate counts do not match entries")

        expected_members = {_MANIFEST_MEMBER, *(_DATA_PREFIX + entry.logical_path for entry in entries)}
        with zipfile.ZipFile(bundle, "r") as archive:
            actual_members = set(archive.namelist())
        if actual_members != expected_members:
            raise DbDDataMigrationError("migration bundle contains unexpected or missing members")
        return manifest, tuple(entries)

    @staticmethod
    def _assert_safe_destination(root: Path, destination: Path) -> None:
        root = root.expanduser()
        if root.exists() and root.is_symlink():
            raise DbDDataMigrationError(f"restore root must not be a symlink: {root}")
        current = root
        try:
            relative = destination.relative_to(root)
        except ValueError as exc:
            raise DbDDataMigrationError(f"restore destination escapes its root: {destination}") from exc
        for part in relative.parts[:-1]:
            current = current / part
            if current.exists() and current.is_symlink():
                raise DbDDataMigrationError(f"restore destination traverses symlink: {current}")

    def _destination_for(self, entry: MigrationEntry, *, project_root: str | Path | None) -> Path:
        p = _safe_relative_path(entry.logical_path)
        rel = Path(*p.parts[1:])
        if entry.scope == _TRAINING_SCOPE:
            root = self.training_root
            destination = root / rel
        elif entry.scope == _TRIVIA_SCOPE:
            if len(p.parts) != 2:
                raise DbDDataMigrationError("global trivia entry must contain exactly one file")
            root = self.trivia_database_path.parent
            destination = self.trivia_database_path
        elif entry.scope == _PROJECT_SCOPE:
            if project_root is None:
                raise DbDDataMigrationError("project_root is required to restore project Game Intelligence data")
            project = Path(project_root)
            if project.exists() and project.is_symlink():
                raise DbDDataMigrationError(f"project root must not be a symlink: {project}")
            root = self._project_state_root(project_root)
            destination = root / rel
        else:
            raise DbDDataMigrationError(f"unsupported restore scope: {entry.scope}")
        self._assert_safe_destination(root, destination)
        return destination

    @staticmethod
    def _verify_archive_payloads(bundle_path: str | Path, entries: tuple[MigrationEntry, ...]) -> None:
        bundle = Path(bundle_path)
        try:
            with zipfile.ZipFile(bundle, "r") as archive:
                for entry in entries:
                    digest = hashlib.sha256()
                    size = 0
                    with archive.open(_DATA_PREFIX + entry.logical_path, "r") as src:
                        while True:
                            chunk = src.read(1024 * 1024)
                            if not chunk:
                                break
                            size += len(chunk)
                            if size > _MAX_FILE_BYTES:
                                raise DbDDataMigrationError(f"migration entry exceeds bounded size: {entry.logical_path}")
                            digest.update(chunk)
                    checksum = "sha256:" + digest.hexdigest()
                    if size != entry.size_bytes or checksum != entry.sha256:
                        raise DbDDataMigrationError(f"migration entry checksum mismatch: {entry.logical_path}")
        except zipfile.BadZipFile as exc:
            raise DbDDataMigrationError(f"invalid migration bundle: {exc}") from exc

    def preview_restore(self, bundle_path: str | Path, *, project_root: str | Path | None = None) -> MigrationRestorePreview:
        manifest, entries = self._load_verified_manifest(bundle_path)
        self._verify_archive_payloads(bundle_path, entries)
        scopes = tuple(str(x) for x in manifest.get("scopes", []))
        requires_project = _PROJECT_SCOPE in scopes and project_root is None
        conflicts: list[str] = []
        if not requires_project:
            for entry in entries:
                destination = self._destination_for(entry, project_root=project_root)
                if destination.exists():
                    if destination.is_symlink() or not destination.is_file():
                        conflicts.append(entry.logical_path + " [unsafe destination]")
                        continue
                    size, checksum = _hash_file(destination)
                    if size != entry.size_bytes or checksum != entry.sha256:
                        conflicts.append(entry.logical_path)
        return MigrationRestorePreview(
            bundle_id=str(manifest["bundle_id"]),
            path=Path(bundle_path),
            entry_count=len(entries),
            total_bytes=sum(x.size_bytes for x in entries),
            scopes=scopes,
            conflicts=tuple(conflicts),
            requires_project_root=requires_project,
            manifest_sha256=str(manifest["manifest_sha256"]),
        )

    def _verify_and_stage(self, bundle_path: Path, entries: tuple[MigrationEntry, ...], staging: Path) -> dict[str, Path]:
        staged: dict[str, Path] = {}
        with zipfile.ZipFile(bundle_path, "r") as archive:
            for entry in entries:
                member = _DATA_PREFIX + entry.logical_path
                target = staging / entry.logical_path
                target.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                size = 0
                with archive.open(member, "r") as src, target.open("wb") as dst:
                    while True:
                        chunk = src.read(1024 * 1024)
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > _MAX_FILE_BYTES:
                            raise DbDDataMigrationError(f"staged file exceeds bounded size: {entry.logical_path}")
                        digest.update(chunk)
                        dst.write(chunk)
                checksum = "sha256:" + digest.hexdigest()
                if size != entry.size_bytes or checksum != entry.sha256:
                    raise DbDDataMigrationError(f"migration entry checksum mismatch: {entry.logical_path}")
                staged[entry.logical_path] = target
        return staged

    def restore(
        self,
        bundle_path: str | Path,
        *,
        project_root: str | Path | None = None,
        allow_replace: bool = False,
        create_safety_backup: bool = True,
    ) -> MigrationRestoreReceipt:
        preview = self.preview_restore(bundle_path, project_root=project_root)
        if preview.requires_project_root:
            raise DbDDataMigrationError("project_root is required for this migration bundle")
        if preview.conflicts and not allow_replace:
            raise DbDDataMigrationError(
                "restore would replace existing data; preview conflicts and explicitly authorize replacement first"
            )
        manifest, entries = self._load_verified_manifest(bundle_path)
        safety_backup: Path | None = None
        if preview.conflicts and allow_replace and create_safety_backup:
            self.safety_backup_root.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            safety_backup = self.safety_backup_root / f"pre-restore-{stamp}-{uuid.uuid4().hex[:8]}.zip"
            self.create_backup(
                safety_backup,
                project_root=project_root,
                include_project=_PROJECT_SCOPE in preview.scopes,
                include_training=_TRAINING_SCOPE in preview.scopes,
                include_trivia=_TRIVIA_SCOPE in preview.scopes,
            )

        bundle = Path(bundle_path)
        with tempfile.TemporaryDirectory(prefix="bvp-dbd-migration-restore-") as temp_name:
            temp = Path(temp_name)
            staged = self._verify_and_stage(bundle, entries, temp / "staged")
            rollback_root = temp / "rollback"
            replaced: list[tuple[Path, Path]] = []
            created: list[Path] = []
            try:
                for entry in entries:
                    destination = self._destination_for(entry, project_root=project_root)
                    if destination.exists():
                        if destination.is_symlink() or not destination.is_file():
                            raise DbDDataMigrationError(f"unsafe restore destination: {destination}")
                        rollback = rollback_root / entry.logical_path
                        _copy_stream(destination, rollback)
                        replaced.append((destination, rollback))
                    else:
                        created.append(destination)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    replacement = staged[entry.logical_path]
                    tmp_target = destination.with_name(destination.name + ".restore-" + uuid.uuid4().hex)
                    _copy_stream(replacement, tmp_target)
                    os.replace(tmp_target, destination)
                    if entry.sqlite_snapshot:
                        Path(str(destination) + "-wal").unlink(missing_ok=True)
                        Path(str(destination) + "-shm").unlink(missing_ok=True)
            except Exception:
                for path in reversed(created):
                    path.unlink(missing_ok=True)
                for destination, rollback in reversed(replaced):
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    _copy_stream(rollback, destination)
                raise

        return MigrationRestoreReceipt(
            bundle_id=str(manifest["bundle_id"]),
            restored_files=len(entries),
            replaced_files=len(replaced),
            new_files=len(created),
            safety_backup_path=safety_backup,
            manifest_sha256=str(manifest["manifest_sha256"]),
        )
