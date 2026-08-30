from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import gc
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import time
from typing import Any

from .assets import AssetRecord, AssetType, AudioRightsStatus, PermissionState, RetentionClass, RightsStatus
from .checkpoint import CheckpointRecord
from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, generate_id, validate_id
from .serialization import utc_now_iso
from .state import JobStateSnapshot, ProductionJobState

_BASE_SCHEMA_VERSION = 1
_V2_SCHEMA_VERSION = 2
_SCHEMA_VERSION = 3
_MAX_EXISTING_DATABASE_BYTES = 512 * 1024 * 1024
_MAX_EXISTING_WAL_BYTES = 256 * 1024 * 1024
_EXISTING_VALIDATION_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class OperationRecord:
    operation_id: str
    job_id: str
    command_type: str
    idempotency_key: str
    status: str
    attempt: int
    created_at: str
    updated_at: str | None = None
    last_error_code: str | None = None
    result_ref: str | None = None


@dataclass(frozen=True, slots=True)
class ManifestRecord:
    manifest_id: str
    job_id: str
    manifest_type: str
    version: int
    uri: str
    checksum: str
    schema_version: str
    status: str = "COMMITTED"
    operation_id: str | None = None


@dataclass(frozen=True, slots=True)
class AssetPage:
    """Bounded keyset page for large Asset Library projections."""

    items: tuple[AssetRecord, ...]
    limit: int
    next_cursor: str | None

    @property
    def has_more(self) -> bool:
        return self.next_cursor is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "limit": self.limit,
            "next_cursor": self.next_cursor,
            "has_more": self.has_more,
        }


class SQLiteProductStore:
    def __init__(self, path: str | Path, *, require_existing: bool = False, required_job_id: str | None = None) -> None:
        self.path = Path(path)
        self._require_existing = require_existing
        self._pinned_database_identity: tuple[int, int] | None = None
        self._database_pin_fd: int | None = None
        if require_existing:
            try:
                invalid_path = (
                    self.path.is_symlink()
                    or not self.path.is_file()
                    or self.path.stat().st_size <= 0
                )
            except OSError:
                invalid_path = True
            if invalid_path:
                raise ProductError(
                    "ERR_STORE_EXISTING_DATABASE_REQUIRED",
                    "Existing Product database must be a non-empty regular non-symlink file",
                    ProductErrorCategory.SECURITY,
                )
            # A sqlite Connection context manager commits or rolls back but does
            # not close the native handle.  Finalize unreachable handles before
            # pinning so a delayed WAL checkpoint cannot mutate the admitted
            # database while its stable validation copy is being produced.
            gc.collect()
            try:
                descriptor = os.open(
                    self.path,
                    os.O_RDWR | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0),
                )
                try:
                    opened = os.fstat(descriptor)
                    if (
                        not stat.S_ISREG(opened.st_mode)
                        or opened.st_size <= 0
                        or opened.st_size > _MAX_EXISTING_DATABASE_BYTES
                    ):
                        raise OSError("database is not a regular file")
                    header = os.read(descriptor, 100)
                    self._pinned_database_identity = (opened.st_dev, opened.st_ino)
                    self._database_pin_fd = descriptor
                except BaseException:
                    os.close(descriptor)
                    raise
                if header[:16] != b"SQLite format 3\x00" or header[18:20] != b"\x02\x02":
                    raise sqlite3.DatabaseError("database is not a current WAL database")
                with self._connect_existing_validation() as conn:
                    self._validate_existing_database(conn)
                    if required_job_id is not None:
                        validate_id(required_job_id, IdKind.JOB)
                        row = conn.execute(
                            "SELECT 1 FROM production_jobs WHERE job_id=?",
                            (required_job_id,),
                        ).fetchone()
                        if row is None:
                            raise ProductError(
                                "ERR_STORE_EXISTING_JOB_REQUIRED",
                                "Existing Product database lacks the configured Product Job",
                                ProductErrorCategory.STATE,
                            )
            except ProductError:
                self.close()
                raise
            except (OSError, sqlite3.DatabaseError) as exc:
                self.close()
                raise ProductError(
                    "ERR_STORE_EXISTING_DATABASE_INVALID",
                    "Existing Product database is invalid",
                    ProductErrorCategory.DATA_INTEGRITY,
                ) from exc
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._initialize()

    def _connect(self) -> sqlite3.Connection:
        if self._require_existing:
            self._require_pinned_database_identity()
            pinned = self._database_pin_fd
            if pinned is None:
                raise ProductError(
                    "ERR_STORE_EXISTING_DATABASE_IDENTITY",
                    "Existing Product database is no longer pinned",
                    ProductErrorCategory.SECURITY,
                )
            # sqlite3.Connection context managers do not close their handles;
            # collect unreachable prior connections before assigning identity
            # to the descriptor opened by this exact connect operation.
            gc.collect()
            descriptor_snapshot = self._process_descriptor_snapshot()
            database_uri = f"{self.path.resolve(strict=True).as_uri()}?mode=rw"
            conn = sqlite3.connect(database_uri, timeout=5.0, uri=True)
            try:
                self._require_pinned_database_identity()
                self._require_connection_database_identity(descriptor_snapshot)
            except Exception:
                conn.close()
                raise
        else:
            conn = sqlite3.connect(self.path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        if not self._require_existing:
            conn.execute("PRAGMA journal_mode=WAL")
        return conn

    @contextmanager
    def _managed_connection(self):
        """Commit or roll back, then deterministically close the SQLite handle."""
        conn = self._connect()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @staticmethod
    def _process_descriptor_snapshot() -> dict[int, tuple[int, int]] | None:
        directory = Path("/proc/self/fd")
        if os.name != "posix" or not directory.is_dir():
            return None
        result: dict[int, tuple[int, int]] = {}
        for entry in directory.iterdir():
            try:
                descriptor = int(entry.name)
                observed = os.fstat(descriptor)
            except (OSError, ValueError):
                continue
            result[descriptor] = (observed.st_dev, observed.st_ino)
        return result

    def _require_connection_database_identity(
        self,
        before: dict[int, tuple[int, int]] | None,
    ) -> None:
        # Windows' retained CRT descriptor denies rename/delete. On Linux/WSL,
        # prove the sqlite connection itself opened the admitted inode; checking
        # only the pathname before/after permits an attacker to swap it back.
        if before is None:
            return
        expected = self._pinned_database_identity
        pin = self._database_pin_fd
        after = self._process_descriptor_snapshot()
        if expected is None or after is None:
            raise ProductError(
                "ERR_STORE_EXISTING_DATABASE_IDENTITY",
                "SQLite connection identity cannot be established",
                ProductErrorCategory.SECURITY,
            )
        newly_opened = {
            descriptor: identity
            for descriptor, identity in after.items()
            if descriptor != pin and before.get(descriptor) != identity
        }
        if expected not in newly_opened.values():
            raise ProductError(
                "ERR_STORE_EXISTING_DATABASE_IDENTITY",
                "SQLite connected to a different Product database",
                ProductErrorCategory.SECURITY,
            )

    def close(self) -> None:
        descriptor = self._database_pin_fd
        self._database_pin_fd = None
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass

    def __del__(self) -> None:
        self.close()

    def _require_pinned_database_identity(self) -> None:
        descriptor = self._database_pin_fd
        if descriptor is None:
            raise ProductError(
                "ERR_STORE_EXISTING_DATABASE_IDENTITY",
                "Existing Product database is no longer pinned",
                ProductErrorCategory.SECURITY,
            )
        try:
            current = self.path.lstat()
            pinned = os.fstat(descriptor)
        except OSError as exc:
            raise ProductError(
                "ERR_STORE_EXISTING_DATABASE_IDENTITY",
                "Existing Product database identity changed",
                ProductErrorCategory.SECURITY,
            ) from exc
        if (
            self.path.is_symlink()
            or not stat.S_ISREG(current.st_mode)
            or self._pinned_database_identity != (current.st_dev, current.st_ino)
            or self._pinned_database_identity != (pinned.st_dev, pinned.st_ino)
        ):
            raise ProductError(
                "ERR_STORE_EXISTING_DATABASE_IDENTITY",
                "Existing Product database identity changed",
                ProductErrorCategory.SECURITY,
            )

    @staticmethod
    def _copy_stable_file(source: Path, target: Path, *, max_bytes: int) -> None:
        if source.is_symlink() or not source.is_file():
            raise OSError("database family member is not a regular file")
        descriptor = os.open(
            source,
            os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            before = os.fstat(descriptor)
            if before.st_size <= 0 or before.st_size > max_bytes:
                raise OSError("database family member exceeds its validation bound")
            with target.open("xb") as output:
                while True:
                    chunk = os.read(descriptor, 1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
        ):
            raise OSError("database family member changed during validation copy")

    def _copy_pinned_database(self, target: Path) -> None:
        descriptor = self._database_pin_fd
        if descriptor is None:
            raise OSError("database is not pinned")
        before = os.fstat(descriptor)
        if before.st_size <= 0 or before.st_size > _MAX_EXISTING_DATABASE_BYTES:
            raise OSError("database exceeds its validation bound")
        position = os.lseek(descriptor, 0, os.SEEK_CUR)
        copied_hash = hashlib.sha256()
        try:
            os.lseek(descriptor, 0, os.SEEK_SET)
            with target.open("xb") as output:
                while True:
                    chunk = os.read(descriptor, 1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    copied_hash.update(chunk)
            os.lseek(descriptor, 0, os.SEEK_SET)
            observed_hash = hashlib.sha256()
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                observed_hash.update(chunk)
        finally:
            os.lseek(descriptor, position, os.SEEK_SET)
        after = os.fstat(descriptor)
        if (
            (before.st_dev, before.st_ino, before.st_size)
            != (after.st_dev, after.st_ino, after.st_size)
            or copied_hash.digest() != observed_hash.digest()
        ):
            raise OSError("database changed during validation copy")

    @contextmanager
    def _connect_existing_validation(self):
        self._require_pinned_database_identity()
        with tempfile.TemporaryDirectory(prefix="bai-product-admission-") as directory:
            copy_path = Path(directory) / "product.sqlite3"
            self._copy_pinned_database(copy_path)
            # WAL is durable database state; SHM is ephemeral coordination and
            # must be recreated for the isolated validation copy.
            for suffix in ("-wal",):
                source = self.path.with_name(self.path.name + suffix)
                if source.exists() or source.is_symlink():
                    self._copy_stable_file(
                        source,
                        copy_path.with_name(copy_path.name + suffix),
                        max_bytes=_MAX_EXISTING_WAL_BYTES,
                    )
            self._require_pinned_database_identity()
            conn = sqlite3.connect(copy_path, timeout=5.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            deadline = time.monotonic() + _EXISTING_VALIDATION_TIMEOUT_SECONDS
            conn.set_progress_handler(
                lambda: 1 if time.monotonic() > deadline else 0,
                10_000,
            )
            try:
                yield conn
            finally:
                conn.close()

    @staticmethod
    def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}

    @staticmethod
    def _schema_fingerprint(conn: sqlite3.Connection) -> tuple[Any, ...]:
        objects = tuple(
            tuple(row)
            for row in conn.execute(
                "SELECT type,name,tbl_name FROM sqlite_master "
                "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
            ).fetchall()
        )
        tables = tuple(row[1] for row in objects if row[0] == "table")
        table_shapes = tuple(
            (
                table,
                tuple(tuple(row[1:6]) for row in conn.execute(f"PRAGMA table_info({table})")),
                tuple(tuple(row[2:8]) for row in conn.execute(f"PRAGMA foreign_key_list({table})")),
                tuple(
                    (
                        tuple(row[1:5]),
                        tuple(tuple(info[1:6]) for info in conn.execute(f"PRAGMA index_xinfo({row[1]})")),
                    )
                    for row in conn.execute(f"PRAGMA index_list({table})")
                ),
            )
            for table in tables
        )
        return objects, table_shapes

    @classmethod
    def _validate_existing_database(cls, conn: sqlite3.Connection) -> None:
        with tempfile.TemporaryDirectory(prefix="bai-product-schema-") as directory:
            canonical_path = Path(directory) / "canonical.sqlite3"
            canonical_store = cls(canonical_path)
            try:
                with canonical_store._managed_connection() as canonical:
                    expected = cls._schema_fingerprint(canonical)
            finally:
                canonical_store.close()
        versions = tuple(
            int(row[0])
            for row in conn.execute("SELECT version FROM schema_migrations ORDER BY version")
        )
        integrity = tuple(row[0] for row in conn.execute("PRAGMA integrity_check"))
        foreign_keys = tuple(tuple(row) for row in conn.execute("PRAGMA foreign_key_check"))
        if (
            cls._schema_fingerprint(conn) != expected
            or versions != (_BASE_SCHEMA_VERSION, _V2_SCHEMA_VERSION, _SCHEMA_VERSION)
            or integrity != ("ok",)
            or foreign_keys
        ):
            raise ProductError(
                "ERR_STORE_EXISTING_DATABASE_INVALID",
                "Existing Product database schema or journal mode is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )

    @staticmethod
    def _add_column_if_missing(conn: sqlite3.Connection, table: str, name: str, ddl: str) -> None:
        if name not in SQLiteProductStore._column_names(conn, table):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")

    def _initialize(self) -> None:
        with self._managed_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
              version INTEGER PRIMARY KEY,
              applied_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS production_jobs (
              job_id TEXT PRIMARY KEY,
              state TEXT NOT NULL,
              state_version INTEGER NOT NULL,
              profile_snapshot_id TEXT NOT NULL,
              resume_to_state TEXT,
              last_error_code TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS assets (
              asset_id TEXT PRIMARY KEY,
              job_id TEXT NOT NULL REFERENCES production_jobs(job_id),
              type TEXT NOT NULL,
              logical_uri TEXT NOT NULL,
              checksum TEXT NOT NULL,
              rights_status TEXT NOT NULL,
              owner TEXT NOT NULL,
              retention_class TEXT NOT NULL,
              human_lock INTEGER NOT NULL,
              UNIQUE(job_id, logical_uri, checksum)
            );
            CREATE TABLE IF NOT EXISTS asset_versions (
              asset_version_id TEXT PRIMARY KEY,
              asset_id TEXT NOT NULL REFERENCES assets(asset_id),
              version INTEGER NOT NULL,
              checksum TEXT NOT NULL,
              producer_operation_id TEXT,
              UNIQUE(asset_id, version)
            );
            CREATE TABLE IF NOT EXISTS manifests (
              manifest_id TEXT PRIMARY KEY,
              job_id TEXT NOT NULL REFERENCES production_jobs(job_id),
              type TEXT NOT NULL,
              version INTEGER NOT NULL,
              uri TEXT NOT NULL,
              checksum TEXT NOT NULL,
              schema_version TEXT NOT NULL,
              UNIQUE(job_id, type, version)
            );
            CREATE TABLE IF NOT EXISTS operations (
              operation_id TEXT PRIMARY KEY,
              job_id TEXT NOT NULL REFERENCES production_jobs(job_id),
              command_type TEXT NOT NULL,
              idempotency_key TEXT NOT NULL,
              status TEXT NOT NULL,
              attempt INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              UNIQUE(job_id, idempotency_key)
            );
            CREATE TABLE IF NOT EXISTS checkpoints (
              checkpoint_id TEXT PRIMARY KEY,
              job_id TEXT NOT NULL REFERENCES production_jobs(job_id),
              stage TEXT NOT NULL,
              input_hash TEXT NOT NULL,
              output_hash TEXT NOT NULL,
              resume_state TEXT NOT NULL,
              profile_snapshot_id TEXT NOT NULL,
              manifest_hashes_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS approvals (
              approval_id TEXT PRIMARY KEY,
              job_id TEXT NOT NULL REFERENCES production_jobs(job_id),
              gate TEXT NOT NULL,
              plan_version INTEGER NOT NULL,
              approver TEXT NOT NULL,
              decision TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evidence (
              evidence_id TEXT PRIMARY KEY,
              job_id TEXT NOT NULL REFERENCES production_jobs(job_id),
              category TEXT NOT NULL,
              uri TEXT NOT NULL,
              checksum TEXT NOT NULL,
              operation_id TEXT,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cost_ledger (
              cost_id TEXT PRIMARY KEY,
              job_id TEXT NOT NULL REFERENCES production_jobs(job_id),
              provider TEXT NOT NULL,
              estimated TEXT,
              reserved TEXT,
              actual TEXT,
              currency TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS profiles (
              profile_id TEXT NOT NULL,
              version TEXT NOT NULL,
              status TEXT NOT NULL,
              config_uri TEXT NOT NULL,
              checksum TEXT NOT NULL,
              PRIMARY KEY(profile_id, version)
            );
            CREATE TABLE IF NOT EXISTS decisions (
              decision_id TEXT PRIMARY KEY,
              status TEXT NOT NULL,
              question TEXT NOT NULL,
              decision TEXT NOT NULL,
              affected_tasks TEXT NOT NULL
            );
            """)
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (_BASE_SCHEMA_VERSION, utc_now_iso()),
            )
            self._apply_v2_migration(conn)
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (_V2_SCHEMA_VERSION, utc_now_iso()),
            )
            self._apply_v3_migration(conn)
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (_SCHEMA_VERSION, utc_now_iso()),
            )

    def _apply_v2_migration(self, conn: sqlite3.Connection) -> None:
        # Additive migration only. Existing TASK-001 rows remain readable and
        # receive fail-safe/legacy-compatible defaults without rewriting IDs or
        # historical Evidence.
        additions = {
            "original_name": "TEXT",
            "commercial_use": "TEXT NOT NULL DEFAULT 'UNKNOWN'",
            "derivative_allowed": "TEXT NOT NULL DEFAULT 'UNKNOWN'",
            "reuse_allowed": "TEXT NOT NULL DEFAULT 'ALLOWED'",
            "audio_rights_status": "TEXT NOT NULL DEFAULT 'NOT_APPLICABLE'",
            "source_ref": "TEXT",
            "source_project": "TEXT",
            "attribution": "TEXT",
            "territory_json": "TEXT NOT NULL DEFAULT '[]'",
            "rights_valid_until": "TEXT",
            "publication_restrictions_json": "TEXT NOT NULL DEFAULT '[]'",
            "approved_segments_json": "TEXT NOT NULL DEFAULT '[]'",
            "media_metadata_json": "TEXT NOT NULL DEFAULT '{}'",
            "generation_provenance_json": "TEXT NOT NULL DEFAULT '{}'",
            "evidence_refs_json": "TEXT NOT NULL DEFAULT '[]'",
            "perceptual_hash": "TEXT",
            "audio_fingerprint": "TEXT",
        }
        for name, ddl in additions.items():
            self._add_column_if_missing(conn, "assets", name, ddl)
        self._add_column_if_missing(conn, "operations", "updated_at", "TEXT")
        self._add_column_if_missing(conn, "operations", "last_error_code", "TEXT")
        self._add_column_if_missing(conn, "operations", "result_ref", "TEXT")
        self._add_column_if_missing(conn, "manifests", "status", "TEXT NOT NULL DEFAULT 'COMMITTED'")
        self._add_column_if_missing(conn, "manifests", "operation_id", "TEXT")
        try:
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_assets_job_checksum ON assets(job_id, checksum)")
        except sqlite3.IntegrityError as exc:
            raise ProductError(
                "ERR_INTEGRITY_ASSET_DUPLICATE_MIGRATION",
                "existing Asset Registry contains duplicate checksums for the same Production Job",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc

    @staticmethod
    def _apply_v3_migration(conn: sqlite3.Connection) -> None:
        # Keyset pagination must not materialize a complete large Asset Library.
        # This additive index changes no Asset identity or historical row.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_assets_job_asset_id ON assets(job_id, asset_id)"
        )

    def schema_versions(self) -> tuple[int, ...]:
        with self._connect() as conn:
            rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
        return tuple(int(row[0]) for row in rows)

    def create_job(self, profile_snapshot_id: str, *, job_id: str | None = None) -> JobStateSnapshot:
        job_id = job_id or generate_id(IdKind.JOB)
        validate_id(job_id, IdKind.JOB)
        validate_id(profile_snapshot_id, IdKind.PROFILE_SNAPSHOT)
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO production_jobs(job_id,state,state_version,profile_snapshot_id,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                (job_id, ProductionJobState.CREATED.value, 1, profile_snapshot_id, now, now),
            )
        return self.get_job_state(job_id)

    def get_job_state(self, job_id: str) -> JobStateSnapshot:
        validate_id(job_id, IdKind.JOB)
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM production_jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            raise ProductError("ERR_INPUT_JOB_NOT_FOUND", "production job not found", ProductErrorCategory.VALIDATION)
        return JobStateSnapshot(
            row["job_id"], ProductionJobState(row["state"]), int(row["state_version"]), row["profile_snapshot_id"],
            ProductionJobState(row["resume_to_state"]) if row["resume_to_state"] else None,
            row["last_error_code"],
        )

    def _transition_job_state(
        self,
        job_id: str,
        *,
        from_state: ProductionJobState,
        to_state: ProductionJobState,
        expected_version: int,
        resume_to_state: ProductionJobState | None,
        last_error_code: str | None,
    ) -> JobStateSnapshot:
        now = utc_now_iso()
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE production_jobs SET state=?,state_version=state_version+1,resume_to_state=?,last_error_code=?,updated_at=? "
                "WHERE job_id=? AND state=? AND state_version=?",
                (
                    to_state.value,
                    resume_to_state.value if resume_to_state else None,
                    last_error_code,
                    now,
                    job_id,
                    from_state.value,
                    expected_version,
                ),
            )
            if cur.rowcount != 1:
                raise ProductError("ERR_STATE_STALE_REVISION", "concurrent job state mutation detected", ProductErrorCategory.STATE)
        return self.get_job_state(job_id)

    def _resume_job_state(
        self,
        job_id: str,
        *,
        from_state: ProductionJobState,
        target_state: ProductionJobState,
        expected_version: int,
    ) -> JobStateSnapshot:
        """Commit the logical side->RESUMING->target bridge atomically."""
        now = utc_now_iso()
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE production_jobs SET state=?,state_version=state_version+2,resume_to_state=NULL,last_error_code=NULL,updated_at=? "
                "WHERE job_id=? AND state=? AND state_version=? AND resume_to_state=?",
                (target_state.value, now, job_id, from_state.value, expected_version, target_state.value),
            )
            if cur.rowcount != 1:
                raise ProductError(
                    "ERR_STATE_STALE_REVISION",
                    "concurrent or incompatible resume mutation detected",
                    ProductErrorCategory.STATE,
                )
        return self.get_job_state(job_id)

    @staticmethod
    def _asset_insert_values(record: AssetRecord) -> tuple[Any, ...]:
        return (
            record.asset_id,
            record.production_job_id,
            record.asset_type.value,
            record.logical_uri,
            record.checksum,
            record.rights_status.value,
            record.owner,
            record.retention_class.value,
            int(record.human_lock),
            record.original_name,
            record.commercial_use.value,
            record.derivative_allowed.value,
            record.reuse_allowed.value,
            record.audio_rights_status.value,
            record.source_ref,
            record.source_project,
            record.attribution,
            json.dumps(list(record.territory), ensure_ascii=False, separators=(",", ":")),
            record.rights_valid_until,
            json.dumps(list(record.publication_restrictions), ensure_ascii=False, separators=(",", ":")),
            json.dumps([x.to_dict() for x in record.approved_segments], ensure_ascii=False, separators=(",", ":")),
            json.dumps(record.media_metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            json.dumps(record.generation_provenance, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            json.dumps(list(record.evidence_refs), ensure_ascii=False, separators=(",", ":")),
            record.perceptual_hash,
            record.audio_fingerprint,
        )

    def register_asset(self, record: AssetRecord, *, producer_operation_id: str | None = None) -> None:
        if producer_operation_id is not None:
            validate_id(producer_operation_id, IdKind.OPERATION)
        with self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO assets(
                      asset_id,job_id,type,logical_uri,checksum,rights_status,owner,retention_class,human_lock,
                      original_name,commercial_use,derivative_allowed,reuse_allowed,audio_rights_status,
                      source_ref,source_project,attribution,territory_json,rights_valid_until,
                      publication_restrictions_json,approved_segments_json,media_metadata_json,
                      generation_provenance_json,evidence_refs_json,perceptual_hash,audio_fingerprint
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    self._asset_insert_values(record),
                )
                conn.execute(
                    "INSERT INTO asset_versions(asset_version_id,asset_id,version,checksum,producer_operation_id) VALUES (?,?,?,?,?)",
                    (generate_id(IdKind.ASSET_VERSION), record.asset_id, 1, record.checksum, producer_operation_id),
                )
            except sqlite3.IntegrityError as exc:
                raise ProductError(
                    "ERR_INTEGRITY_ASSET_REGISTRY_CONFLICT",
                    "Asset Registry uniqueness or Job binding conflict",
                    ProductErrorCategory.DATA_INTEGRITY,
                ) from exc

    @staticmethod
    def _row_to_asset(row: sqlite3.Row) -> AssetRecord:
        value = {
            "asset_id": row["asset_id"],
            "production_job_id": row["job_id"],
            "asset_type": row["type"],
            "logical_uri": row["logical_uri"],
            "checksum": row["checksum"],
            "rights_status": row["rights_status"],
            "owner": row["owner"],
            "retention_class": row["retention_class"],
            "human_lock": bool(row["human_lock"]),
            "original_name": row["original_name"],
            "commercial_use": row["commercial_use"],
            "derivative_allowed": row["derivative_allowed"],
            "reuse_allowed": row["reuse_allowed"],
            "audio_rights_status": row["audio_rights_status"],
            "source_ref": row["source_ref"],
            "source_project": row["source_project"],
            "attribution": row["attribution"],
            "territory": json.loads(row["territory_json"]),
            "rights_valid_until": row["rights_valid_until"],
            "publication_restrictions": json.loads(row["publication_restrictions_json"]),
            "approved_segments": json.loads(row["approved_segments_json"]),
            "media_metadata": json.loads(row["media_metadata_json"]),
            "generation_provenance": json.loads(row["generation_provenance_json"]),
            "evidence_refs": json.loads(row["evidence_refs_json"]),
            "perceptual_hash": row["perceptual_hash"],
            "audio_fingerprint": row["audio_fingerprint"],
        }
        return AssetRecord.from_dict(value)

    def get_asset(self, asset_id: str) -> AssetRecord:
        validate_id(asset_id, IdKind.ASSET)
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM assets WHERE asset_id=?", (asset_id,)).fetchone()
        if row is None:
            raise ProductError("ERR_INPUT_ASSET_NOT_FOUND", "asset not found", ProductErrorCategory.VALIDATION)
        return self._row_to_asset(row)

    def find_asset_by_checksum(self, job_id: str, checksum: str) -> AssetRecord | None:
        validate_id(job_id, IdKind.JOB)
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM assets WHERE job_id=? AND checksum=?", (job_id, checksum)).fetchone()
        return self._row_to_asset(row) if row is not None else None

    def find_asset_by_operation(self, operation_id: str) -> AssetRecord | None:
        validate_id(operation_id, IdKind.OPERATION)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT a.* FROM assets a JOIN asset_versions v ON v.asset_id=a.asset_id "
                "WHERE v.producer_operation_id=? ORDER BY v.version DESC LIMIT 1",
                (operation_id,),
            ).fetchone()
        return self._row_to_asset(row) if row is not None else None

    def list_assets(self, job_id: str) -> tuple[AssetRecord, ...]:
        validate_id(job_id, IdKind.JOB)
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM assets WHERE job_id=? ORDER BY asset_id", (job_id,)).fetchall()
        return tuple(self._row_to_asset(row) for row in rows)

    def list_assets_page(
        self,
        job_id: str,
        *,
        limit: int = 100,
        after_asset_id: str | None = None,
    ) -> AssetPage:
        """Return a stable, bounded keyset page ordered by Asset identity.

        The cursor is the last returned Asset ID. This intentionally does not
        claim snapshot isolation across concurrent inserts; consumers that need
        an exact snapshot must bind a higher-level Project/Job revision.
        """

        validate_id(job_id, IdKind.JOB)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
            raise ValueError("asset page limit must be between 1 and 200")
        if after_asset_id is not None:
            validate_id(after_asset_id, IdKind.ASSET)
        with self._connect() as conn:
            if after_asset_id is None:
                rows = conn.execute(
                    "SELECT * FROM assets WHERE job_id=? ORDER BY asset_id LIMIT ?",
                    (job_id, limit + 1),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM assets WHERE job_id=? AND asset_id>? ORDER BY asset_id LIMIT ?",
                    (job_id, after_asset_id, limit + 1),
                ).fetchall()
        has_more = len(rows) > limit
        visible = rows[:limit]
        items = tuple(self._row_to_asset(row) for row in visible)
        cursor = items[-1].asset_id if has_more and items else None
        return AssetPage(items=items, limit=limit, next_cursor=cursor)

    def reserve_operation(self, job_id: str, command_type: str, idempotency_key: str) -> tuple[OperationRecord, bool]:
        validate_id(job_id, IdKind.JOB)
        if not command_type.strip():
            raise ValueError("command_type must be non-empty")
        if not idempotency_key or len(idempotency_key) > 200:
            raise ValueError("idempotency_key must be 1-200 characters")
        op_id = generate_id(IdKind.OPERATION)
        now = utc_now_iso()
        with self._managed_connection() as conn:
            try:
                conn.execute(
                    "INSERT INTO operations(operation_id,job_id,command_type,idempotency_key,status,attempt,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                    (op_id, job_id, command_type, idempotency_key, "PENDING", 0, now, now),
                )
                created = True
            except sqlite3.IntegrityError:
                row = conn.execute(
                    "SELECT * FROM operations WHERE job_id=? AND idempotency_key=?",
                    (job_id, idempotency_key),
                ).fetchone()
                if row is None:
                    raise
                if row["command_type"] != command_type:
                    raise ProductError(
                        "ERR_INTEGRITY_IDEMPOTENCY_COMMAND_CONFLICT",
                        "idempotency key is already bound to a different command",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
                created = False
            else:
                row = conn.execute("SELECT * FROM operations WHERE operation_id=?", (op_id,)).fetchone()
        assert row is not None
        return self._row_to_operation(row), created

    @staticmethod
    def _row_to_operation(row: sqlite3.Row) -> OperationRecord:
        return OperationRecord(
            row["operation_id"], row["job_id"], row["command_type"], row["idempotency_key"], row["status"],
            int(row["attempt"]), row["created_at"], row["updated_at"], row["last_error_code"], row["result_ref"],
        )

    def get_operation(self, operation_id: str) -> OperationRecord:
        validate_id(operation_id, IdKind.OPERATION)
        with self._managed_connection() as conn:
            row = conn.execute("SELECT * FROM operations WHERE operation_id=?", (operation_id,)).fetchone()
        if row is None:
            raise ProductError("ERR_INPUT_OPERATION_NOT_FOUND", "operation not found", ProductErrorCategory.VALIDATION)
        return self._row_to_operation(row)

    def find_operation(self, job_id: str, idempotency_key: str) -> OperationRecord | None:
        """Read one durable operation coordinate without creating it."""

        validate_id(job_id, IdKind.JOB)
        if not idempotency_key or len(idempotency_key) > 200:
            raise ValueError("idempotency_key must be 1-200 characters")
        with self._managed_connection() as conn:
            row = conn.execute(
                "SELECT * FROM operations WHERE job_id=? AND idempotency_key=?",
                (job_id, idempotency_key),
            ).fetchone()
        return None if row is None else self._row_to_operation(row)

    def compare_and_set_operation_status(
        self,
        operation_id: str,
        *,
        expected_statuses: tuple[str, ...],
        status: str,
        last_error_code: str | None = None,
        increment_attempt: bool = False,
        result_ref: str | None = None,
        expected_result_refs: tuple[str | None, ...] | None = None,
        replace_result_ref: bool = False,
    ) -> tuple[OperationRecord, bool]:
        """Atomically admit exactly one caller from an explicit status set."""

        validate_id(operation_id, IdKind.OPERATION)
        allowed = {"PENDING", "IN_PROGRESS", "PARTIAL", "COMPLETED", "FAILED"}
        if not expected_statuses or any(item not in allowed for item in expected_statuses):
            raise ValueError("expected_statuses are invalid")
        if status not in allowed:
            raise ValueError("unsupported operation status")
        for value in (
            *((expected_result_refs or ())),
            result_ref,
        ):
            if value is None:
                continue
            if (
                not isinstance(value, str)
                or not value
                or len(value) > 2048
                or "\x00" in value
            ):
                raise ValueError("operation result_ref is invalid")
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise ValueError("operation result_ref is invalid") from exc
        placeholders = ",".join("?" for _ in expected_statuses)
        result_predicate = ""
        result_parameters: list[str] = []
        if expected_result_refs is not None:
            if not expected_result_refs:
                raise ValueError("expected_result_refs must not be empty")
            non_null = [item for item in expected_result_refs if item is not None]
            clauses = []
            if any(item is None for item in expected_result_refs):
                clauses.append("result_ref IS NULL")
            if non_null:
                clauses.append("result_ref IN (" + ",".join("?" for _ in non_null) + ")")
                result_parameters.extend(non_null)
            result_predicate = " AND (" + " OR ".join(clauses) + ")"
        result_assignment = "result_ref=?" if replace_result_ref else "result_ref=COALESCE(?, result_ref)"
        now = utc_now_iso()
        with self._managed_connection() as conn:
            cursor = conn.execute(
                f"UPDATE operations SET status=?, last_error_code=?, updated_at=?, "
                f"attempt=attempt+?, {result_assignment} "
                f"WHERE operation_id=? AND status IN ({placeholders}){result_predicate}",
                (
                    status, last_error_code, now, 1 if increment_attempt else 0,
                    result_ref, operation_id, *expected_statuses, *result_parameters,
                ),
            )
            row = conn.execute(
                "SELECT * FROM operations WHERE operation_id=?", (operation_id,),
            ).fetchone()
        if row is None:
            raise ProductError("ERR_INPUT_OPERATION_NOT_FOUND", "operation not found", ProductErrorCategory.VALIDATION)
        return self._row_to_operation(row), cursor.rowcount == 1

    def update_operation_status(
        self,
        operation_id: str,
        status: str,
        *,
        last_error_code: str | None = None,
        increment_attempt: bool = False,
        result_ref: str | None = None,
    ) -> OperationRecord:
        validate_id(operation_id, IdKind.OPERATION)
        if status not in {"PENDING", "IN_PROGRESS", "PARTIAL", "COMPLETED", "FAILED"}:
            raise ValueError("unsupported operation status")
        now = utc_now_iso()
        with self._managed_connection() as conn:
            cur = conn.execute(
                "UPDATE operations SET status=?, last_error_code=?, updated_at=?, attempt=attempt+?, result_ref=COALESCE(?, result_ref) WHERE operation_id=?",
                (status, last_error_code, now, 1 if increment_attempt else 0, result_ref, operation_id),
            )
            if cur.rowcount != 1:
                raise ProductError("ERR_INPUT_OPERATION_NOT_FOUND", "operation not found", ProductErrorCategory.VALIDATION)
            row = conn.execute("SELECT * FROM operations WHERE operation_id=?", (operation_id,)).fetchone()
        assert row is not None
        return self._row_to_operation(row)

    def next_manifest_version(self, job_id: str, manifest_type: str) -> int:
        validate_id(job_id, IdKind.JOB)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(version),0) FROM manifests WHERE job_id=? AND type=?",
                (job_id, manifest_type),
            ).fetchone()
        return int(row[0]) + 1

    def reserve_manifest(
        self,
        *,
        job_id: str,
        manifest_type: str,
        schema_version: str,
        operation_id: str,
        uri_pattern: str,
    ) -> ManifestRecord:
        """Reserve a unique manifest revision before any filesystem write.

        SQLite BEGIN IMMEDIATE serializes version allocation. A crash may leave
        a PENDING/FAILED row and a revision gap, but an already-committed
        revision is never reused or overwritten.
        """
        validate_id(job_id, IdKind.JOB)
        validate_id(operation_id, IdKind.OPERATION)
        if "{version" not in uri_pattern:
            raise ValueError("uri_pattern must contain a {version...} field")
        manifest_id = generate_id(IdKind.MANIFEST)
        pending_checksum = "sha256:" + "0" * 64
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT COALESCE(MAX(version),0) FROM manifests WHERE job_id=? AND type=?",
                (job_id, manifest_type),
            ).fetchone()
            version = int(row[0]) + 1
            uri = uri_pattern.format(version=version)
            conn.execute(
                "INSERT INTO manifests(manifest_id,job_id,type,version,uri,checksum,schema_version,status,operation_id) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    manifest_id, job_id, manifest_type, version, uri, pending_checksum,
                    schema_version, "PENDING", operation_id,
                ),
            )
        return ManifestRecord(
            manifest_id, job_id, manifest_type, version, uri, pending_checksum,
            schema_version, "PENDING", operation_id,
        )

    def finalize_manifest(self, manifest_id: str, checksum: str) -> ManifestRecord:
        validate_id(manifest_id, IdKind.MANIFEST)
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE manifests SET checksum=?, status='COMMITTED' WHERE manifest_id=? AND status='PENDING'",
                (checksum, manifest_id),
            )
            if cur.rowcount != 1:
                raise ProductError(
                    "ERR_INTEGRITY_MANIFEST_FINALIZE_CONFLICT",
                    "manifest reservation is missing or no longer pending",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            row = conn.execute("SELECT * FROM manifests WHERE manifest_id=?", (manifest_id,)).fetchone()
        assert row is not None
        return self._row_to_manifest(row)

    def fail_manifest(self, manifest_id: str) -> None:
        validate_id(manifest_id, IdKind.MANIFEST)
        with self._connect() as conn:
            conn.execute(
                "UPDATE manifests SET status='FAILED' WHERE manifest_id=? AND status='PENDING'",
                (manifest_id,),
            )

    def register_manifest(self, record: ManifestRecord) -> None:
        """Compatibility helper for callers that already own a committed revision."""
        validate_id(record.manifest_id, IdKind.MANIFEST)
        validate_id(record.job_id, IdKind.JOB)
        if record.version < 1:
            raise ValueError("manifest version must be >= 1")
        with self._connect() as conn:
            try:
                conn.execute(
                    "INSERT INTO manifests(manifest_id,job_id,type,version,uri,checksum,schema_version,status,operation_id) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        record.manifest_id, record.job_id, record.manifest_type, record.version, record.uri,
                        record.checksum, record.schema_version, record.status, record.operation_id,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ProductError(
                    "ERR_INTEGRITY_MANIFEST_REGISTRY_CONFLICT",
                    "manifest registry version conflict",
                    ProductErrorCategory.DATA_INTEGRITY,
                ) from exc

    @staticmethod
    def _row_to_manifest(row: sqlite3.Row) -> ManifestRecord:
        return ManifestRecord(
            row["manifest_id"], row["job_id"], row["type"], int(row["version"]), row["uri"],
            row["checksum"], row["schema_version"], row["status"], row["operation_id"],
        )

    def latest_manifest(self, job_id: str, manifest_type: str) -> ManifestRecord | None:
        validate_id(job_id, IdKind.JOB)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM manifests WHERE job_id=? AND type=? AND status='COMMITTED' ORDER BY version DESC LIMIT 1",
                (job_id, manifest_type),
            ).fetchone()
        return self._row_to_manifest(row) if row is not None else None

    def find_manifest_by_operation(self, operation_id: str, manifest_type: str | None = None) -> ManifestRecord | None:
        validate_id(operation_id, IdKind.OPERATION)
        with self._connect() as conn:
            if manifest_type is None:
                row = conn.execute(
                    "SELECT * FROM manifests WHERE operation_id=? AND status='COMMITTED' ORDER BY version DESC LIMIT 1",
                    (operation_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM manifests WHERE operation_id=? AND type=? AND status='COMMITTED' ORDER BY version DESC LIMIT 1",
                    (operation_id, manifest_type),
                ).fetchone()
        return self._row_to_manifest(row) if row is not None else None

    def has_evidence_for_operation(self, operation_id: str, category: str | None = None) -> bool:
        validate_id(operation_id, IdKind.OPERATION)
        with self._connect() as conn:
            if category is None:
                row = conn.execute("SELECT 1 FROM evidence WHERE operation_id=? LIMIT 1", (operation_id,)).fetchone()
            else:
                row = conn.execute("SELECT 1 FROM evidence WHERE operation_id=? AND category=? LIMIT 1", (operation_id, category)).fetchone()
        return row is not None

    def register_evidence_index(
        self,
        *,
        evidence_id: str,
        job_id: str,
        category: str,
        uri: str,
        checksum: str,
        operation_id: str | None,
        created_at: str,
    ) -> None:
        validate_id(evidence_id, IdKind.EVIDENCE)
        validate_id(job_id, IdKind.JOB)
        if operation_id is not None:
            validate_id(operation_id, IdKind.OPERATION)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO evidence(evidence_id,job_id,category,uri,checksum,operation_id,created_at) VALUES (?,?,?,?,?,?,?)",
                (evidence_id, job_id, category, uri, checksum, operation_id, created_at),
            )

    def save_checkpoint(self, checkpoint: CheckpointRecord) -> None:
        with self._connect() as conn:
            job = conn.execute(
                "SELECT profile_snapshot_id FROM production_jobs WHERE job_id=?",
                (checkpoint.production_job_id,),
            ).fetchone()
            if job is None:
                raise ProductError("ERR_INPUT_JOB_NOT_FOUND", "production job not found", ProductErrorCategory.VALIDATION)
            if job["profile_snapshot_id"] != checkpoint.profile_snapshot_id:
                raise ProductError(
                    "ERR_INTEGRITY_CHECKPOINT_PROFILE_MISMATCH",
                    "checkpoint profile snapshot is not the immutable profile bound to the job",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            conn.execute(
                "INSERT INTO checkpoints(checkpoint_id,job_id,stage,input_hash,output_hash,resume_state,profile_snapshot_id,manifest_hashes_json,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    checkpoint.checkpoint_id,
                    checkpoint.production_job_id,
                    checkpoint.stage,
                    checkpoint.input_hash,
                    checkpoint.output_hash,
                    checkpoint.resume_state,
                    checkpoint.profile_snapshot_id,
                    json.dumps(dict(checkpoint.manifest_hashes), sort_keys=True),
                    checkpoint.created_at,
                ),
            )

    def table_names(self) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return {row[0] for row in rows}
