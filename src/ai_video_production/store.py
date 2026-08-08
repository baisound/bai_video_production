from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any

from .assets import AssetRecord
from .checkpoint import CheckpointRecord
from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, generate_id, validate_id
from .serialization import utc_now_iso
from .state import JobStateSnapshot, ProductionJobState

_SCHEMA_VERSION = 1

@dataclass(frozen=True, slots=True)
class OperationRecord:
    operation_id: str
    job_id: str
    command_type: str
    idempotency_key: str
    status: str
    attempt: int
    created_at: str

class SQLiteProductStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
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
            conn.execute("INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)", (_SCHEMA_VERSION, utc_now_iso()))

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

    def _transition_job_state(self, job_id: str, *, from_state: ProductionJobState, to_state: ProductionJobState,
                              expected_version: int, resume_to_state: ProductionJobState | None,
                              last_error_code: str | None) -> JobStateSnapshot:
        now = utc_now_iso()
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE production_jobs SET state=?,state_version=state_version+1,resume_to_state=?,last_error_code=?,updated_at=? "
                "WHERE job_id=? AND state=? AND state_version=?",
                (to_state.value, resume_to_state.value if resume_to_state else None, last_error_code, now,
                 job_id, from_state.value, expected_version),
            )
            if cur.rowcount != 1:
                raise ProductError("ERR_STATE_STALE_REVISION", "concurrent job state mutation detected", ProductErrorCategory.STATE)
        return self.get_job_state(job_id)

    def _resume_job_state(self, job_id: str, *, from_state: ProductionJobState, target_state: ProductionJobState,
                          expected_version: int) -> JobStateSnapshot:
        """Commit the logical side->RESUMING->target bridge atomically.

        RESUMING is deliberately not left as a durable crash point. Two state
        revisions are consumed so optimistic-concurrency observers can still
        detect that two logical transitions occurred.
        """
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

    def register_asset(self, record: AssetRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO assets(asset_id,job_id,type,logical_uri,checksum,rights_status,owner,retention_class,human_lock) VALUES (?,?,?,?,?,?,?,?,?)",
                (record.asset_id, record.production_job_id, record.asset_type.value, record.logical_uri,
                 record.checksum, record.rights_status.value, record.owner, record.retention_class.value, int(record.human_lock)),
            )

    def reserve_operation(self, job_id: str, command_type: str, idempotency_key: str) -> tuple[OperationRecord, bool]:
        validate_id(job_id, IdKind.JOB)
        if not idempotency_key or len(idempotency_key) > 200:
            raise ValueError("idempotency_key must be 1-200 characters")
        op_id = generate_id(IdKind.OPERATION)
        now = utc_now_iso()
        with self._connect() as conn:
            try:
                conn.execute(
                    "INSERT INTO operations(operation_id,job_id,command_type,idempotency_key,status,attempt,created_at) VALUES (?,?,?,?,?,?,?)",
                    (op_id, job_id, command_type, idempotency_key, "PENDING", 0, now),
                )
                created = True
            except sqlite3.IntegrityError:
                row = conn.execute("SELECT * FROM operations WHERE job_id=? AND idempotency_key=?", (job_id, idempotency_key)).fetchone()
                if row is None:
                    raise
                created = False
            else:
                row = conn.execute("SELECT * FROM operations WHERE operation_id=?", (op_id,)).fetchone()
        assert row is not None
        return OperationRecord(row["operation_id"], row["job_id"], row["command_type"], row["idempotency_key"], row["status"], int(row["attempt"]), row["created_at"]), created

    def save_checkpoint(self, checkpoint: CheckpointRecord) -> None:
        import json
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
                (checkpoint.checkpoint_id, checkpoint.production_job_id, checkpoint.stage, checkpoint.input_hash,
                 checkpoint.output_hash, checkpoint.resume_state, checkpoint.profile_snapshot_id,
                 json.dumps(dict(checkpoint.manifest_hashes), sort_keys=True), checkpoint.created_at),
            )

    def table_names(self) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return {row[0] for row in rows}
