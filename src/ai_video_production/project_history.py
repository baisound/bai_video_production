"""TASK-043 bounded command history, Autosave and verified Project backups."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Mapping

from .atomic import AtomicJsonWriter, AtomicWriteResult
from .errors import ProductError, ProductErrorCategory
from .product_project import ProductProjectManifest, parse_product_project_manifest, sha256_file_exact
from .product_project_store import ProductProjectManifestStore, _exclusive_project_lock, _manifest_path, _project_root
from .project_save import ProductProjectSaveCoordinator
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso, validate_sha256


_HISTORY_VERSION = "1.0.0"
_MAX_HISTORY_BYTES = 8 * 1024 * 1024
_MAX_RECORDS = 2048
_MAX_BACKUP_CHILD_BYTES = 64 * 1024 * 1024
_MAX_BACKUP_BYTES = 256 * 1024 * 1024
_IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_FORBIDDEN_SNAPSHOT_TERMS = ("credential", "secret", "token", "password", "private-key", "vault")


def _timestamp(value: str, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{field_name} must be a UTC ISO-8601 timestamp")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{field_name} must be UTC")
    return parsed


class ProjectCommandAction(str, Enum):
    APPLY = "APPLY"
    UNDO = "UNDO"
    REDO = "REDO"


@dataclass(frozen=True, slots=True)
class ProjectCommandRecord:
    record_id: str
    action: ProjectCommandAction
    command_kind: str
    target_identity: str
    source_manifest_sha256: str
    result_manifest_sha256: str
    source_revision: int
    result_revision: int
    compensates_record_id: str | None
    stale_target_ids: tuple[str, ...]
    recorded_at: str
    record_sha256: str

    def __post_init__(self) -> None:
        if not self.record_id.startswith("history-") or len(self.record_id) != 72:
            raise ValueError("record_id is invalid")
        if not _IDENTITY_RE.fullmatch(self.command_kind) or not _IDENTITY_RE.fullmatch(self.target_identity):
            raise ValueError("command or target identity is invalid")
        validate_sha256(self.source_manifest_sha256, field_name="source_manifest_sha256")
        validate_sha256(self.result_manifest_sha256, field_name="result_manifest_sha256")
        if (
            isinstance(self.source_revision, bool)
            or isinstance(self.result_revision, bool)
            or not isinstance(self.source_revision, int)
            or not isinstance(self.result_revision, int)
            or self.source_revision < 1
            or self.result_revision != self.source_revision + 1
        ):
            raise ValueError("history revision must advance exactly once")
        if self.action is ProjectCommandAction.APPLY and self.compensates_record_id is not None:
            raise ValueError("APPLY must not compensate another record")
        if self.action is not ProjectCommandAction.APPLY and (
            not isinstance(self.compensates_record_id, str) or not self.compensates_record_id.startswith("history-")
        ):
            raise ValueError("UNDO/REDO must identify the compensated record")
        if tuple(sorted(set(self.stale_target_ids))) != self.stale_target_ids:
            raise ValueError("stale_target_ids must be unique and sorted")
        if len(self.stale_target_ids) > 256 or any(not _IDENTITY_RE.fullmatch(value) for value in self.stale_target_ids):
            raise ValueError("stale_target_ids are invalid")
        _timestamp(self.recorded_at, "recorded_at")
        validate_sha256(self.record_sha256, field_name="record_sha256")
        if self.record_id != "history-" + sha256_bytes(canonical_json_bytes(self._identity_body())).split(":", 1)[1]:
            raise ValueError("record_id does not match command identity")
        if self.record_sha256 != sha256_bytes(canonical_json_bytes(self._body())):
            raise ValueError("record_sha256 does not match record body")

    @classmethod
    def create(
        cls,
        *,
        action: ProjectCommandAction,
        command_kind: str,
        target_identity: str,
        source_manifest_sha256: str,
        result_manifest_sha256: str,
        source_revision: int,
        compensates_record_id: str | None = None,
        stale_target_ids: tuple[str, ...] = (),
        recorded_at: str | None = None,
    ) -> "ProjectCommandRecord":
        values: dict[str, Any] = {
            "action": action,
            "command_kind": command_kind,
            "target_identity": target_identity,
            "source_manifest_sha256": source_manifest_sha256,
            "result_manifest_sha256": result_manifest_sha256,
            "source_revision": source_revision,
            "result_revision": source_revision + 1,
            "compensates_record_id": compensates_record_id,
            "stale_target_ids": tuple(sorted(set(stale_target_ids))),
            "recorded_at": recorded_at or utc_now_iso(),
        }
        identity = _record_identity_body(**values)
        record_id = "history-" + sha256_bytes(canonical_json_bytes(identity)).split(":", 1)[1]
        body = _record_body(record_id=record_id, **values)
        return cls(record_id=record_id, record_sha256=sha256_bytes(canonical_json_bytes(body)), **values)

    def _identity_body(self) -> dict[str, object]:
        return _record_identity_body(
            action=self.action, command_kind=self.command_kind, target_identity=self.target_identity,
            source_manifest_sha256=self.source_manifest_sha256, result_manifest_sha256=self.result_manifest_sha256,
            source_revision=self.source_revision, result_revision=self.result_revision,
            compensates_record_id=self.compensates_record_id, stale_target_ids=self.stale_target_ids,
            recorded_at=self.recorded_at,
        )

    def _body(self) -> dict[str, object]:
        return _record_body(record_id=self.record_id, **self._identity_body())

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "record_sha256": self.record_sha256}


def _record_identity_body(**values: Any) -> dict[str, object]:
    return {
        "action": values["action"].value if isinstance(values["action"], ProjectCommandAction) else values["action"],
        "command_kind": values["command_kind"], "target_identity": values["target_identity"],
        "source_manifest_sha256": values["source_manifest_sha256"],
        "result_manifest_sha256": values["result_manifest_sha256"],
        "source_revision": values["source_revision"], "result_revision": values["result_revision"],
        "compensates_record_id": values["compensates_record_id"],
        "stale_target_ids": list(values["stale_target_ids"]), "recorded_at": values["recorded_at"],
    }


def _record_body(*, record_id: str, **values: Any) -> dict[str, object]:
    return {
        "record_id": record_id, **_record_identity_body(**values),
        "authority": {"product_local_only": True, "external_replay_authorized": False, "evidence_deletion_authorized": False},
    }


@dataclass(frozen=True, slots=True)
class ProjectCommandHistory:
    project_id: str
    records: tuple[ProjectCommandRecord, ...]
    history_sha256: str

    def __post_init__(self) -> None:
        if not _IDENTITY_RE.fullmatch(self.project_id) or len(self.records) > _MAX_RECORDS:
            raise ValueError("history project identity or size is invalid")
        if len({record.record_id for record in self.records}) != len(self.records):
            raise ValueError("history contains duplicate record identities")
        self._replay()
        validate_sha256(self.history_sha256, field_name="history_sha256")
        if self.history_sha256 != sha256_bytes(canonical_json_bytes(self._body())):
            raise ValueError("history_sha256 does not match history body")

    @classmethod
    def create(cls, project_id: str) -> "ProjectCommandHistory":
        body = _history_body(project_id, ())
        return cls(project_id, (), sha256_bytes(canonical_json_bytes(body)))

    def append_apply(
        self, *, command_kind: str, target_identity: str,
        source_manifest_sha256: str, result_manifest_sha256: str,
        source_revision: int, stale_target_ids: tuple[str, ...] = (), recorded_at: str | None = None,
    ) -> "ProjectCommandHistory":
        return self._append(ProjectCommandRecord.create(
            action=ProjectCommandAction.APPLY, command_kind=command_kind, target_identity=target_identity,
            source_manifest_sha256=source_manifest_sha256, result_manifest_sha256=result_manifest_sha256,
            source_revision=source_revision, stale_target_ids=stale_target_ids, recorded_at=recorded_at,
        ))

    def append_undo(
        self, *, source_manifest_sha256: str, result_manifest_sha256: str,
        source_revision: int, stale_target_ids: tuple[str, ...] = (), recorded_at: str | None = None,
    ) -> "ProjectCommandHistory":
        candidate = self.undo_candidate()
        if candidate is None:
            raise ProductError("ERR_PROJECT_HISTORY_UNDO_EMPTY", "No Product-local command is available to undo", ProductErrorCategory.STATE)
        return self._append(ProjectCommandRecord.create(
            action=ProjectCommandAction.UNDO, command_kind=candidate.command_kind,
            target_identity=candidate.target_identity, source_manifest_sha256=source_manifest_sha256,
            result_manifest_sha256=result_manifest_sha256, source_revision=source_revision,
            compensates_record_id=candidate.record_id, stale_target_ids=stale_target_ids, recorded_at=recorded_at,
        ))

    def append_redo(
        self, *, source_manifest_sha256: str, result_manifest_sha256: str,
        source_revision: int, stale_target_ids: tuple[str, ...] = (), recorded_at: str | None = None,
    ) -> "ProjectCommandHistory":
        original, undo = self._redo_candidate_pair()
        if original is None or undo is None:
            raise ProductError("ERR_PROJECT_HISTORY_REDO_EMPTY", "No Product-local command is available to redo", ProductErrorCategory.STATE)
        return self._append(ProjectCommandRecord.create(
            action=ProjectCommandAction.REDO, command_kind=original.command_kind,
            target_identity=original.target_identity, source_manifest_sha256=source_manifest_sha256,
            result_manifest_sha256=result_manifest_sha256, source_revision=source_revision,
            compensates_record_id=undo.record_id, stale_target_ids=stale_target_ids, recorded_at=recorded_at,
        ))

    def undo_candidate(self) -> ProjectCommandRecord | None:
        active, _redo = self._replay()
        return active[-1] if active else None

    def redo_candidate(self) -> ProjectCommandRecord | None:
        original, _undo = self._redo_candidate_pair()
        return original

    def _redo_candidate_pair(self) -> tuple[ProjectCommandRecord | None, ProjectCommandRecord | None]:
        _active, redo = self._replay()
        return redo[-1] if redo else (None, None)

    def _append(self, record: ProjectCommandRecord) -> "ProjectCommandHistory":
        if len(self.records) >= _MAX_RECORDS:
            raise ProductError("ERR_PROJECT_HISTORY_LIMIT", "Command history reached its evidence-preserving bound", ProductErrorCategory.RESOURCE_EXHAUSTED)
        if self.records:
            previous = self.records[-1]
            if (record.source_revision, record.source_manifest_sha256) != (previous.result_revision, previous.result_manifest_sha256):
                raise ProductError("ERR_PROJECT_HISTORY_SOURCE_CONFLICT", "Command history source does not match its last result", ProductErrorCategory.STATE)
        records = self.records + (record,)
        body = _history_body(self.project_id, records)
        return ProjectCommandHistory(self.project_id, records, sha256_bytes(canonical_json_bytes(body)))

    def _replay(self) -> tuple[list[ProjectCommandRecord], list[tuple[ProjectCommandRecord, ProjectCommandRecord]]]:
        active: list[ProjectCommandRecord] = []
        redo: list[tuple[ProjectCommandRecord, ProjectCommandRecord]] = []
        previous: ProjectCommandRecord | None = None
        by_id: dict[str, ProjectCommandRecord] = {}
        for record in self.records:
            if previous and (record.source_revision, record.source_manifest_sha256) != (previous.result_revision, previous.result_manifest_sha256):
                raise ValueError("history manifest chain is discontinuous")
            if record.action is ProjectCommandAction.APPLY:
                active.append(record)
                redo.clear()
            elif record.action is ProjectCommandAction.UNDO:
                if not active or record.compensates_record_id != active[-1].record_id:
                    raise ValueError("UNDO does not compensate the active command")
                original = active.pop()
                redo.append((original, record))
            else:
                if not redo or record.compensates_record_id != redo[-1][1].record_id:
                    raise ValueError("REDO does not compensate the pending UNDO")
                redo.pop()
                active.append(record)
            by_id[record.record_id] = record
            previous = record
        return active, redo

    def _body(self) -> dict[str, object]:
        return _history_body(self.project_id, self.records)

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "history_sha256": self.history_sha256}


def _history_body(project_id: str, records: tuple[ProjectCommandRecord, ...]) -> dict[str, object]:
    return {
        "history_version": _HISTORY_VERSION, "project_id": project_id,
        "records": [record.to_dict() for record in records],
        "authority": {"product_local_only": True, "external_replay_authorized": False, "evidence_deletion_authorized": False},
    }


def parse_project_command_history(document: Mapping[str, Any]) -> ProjectCommandHistory:
    fields = {"history_version", "project_id", "records", "authority", "history_sha256"}
    authority = {"product_local_only": True, "external_replay_authorized": False, "evidence_deletion_authorized": False}
    if not isinstance(document, Mapping) or set(document) != fields or document.get("history_version") != _HISTORY_VERSION:
        raise ProductError("ERR_PROJECT_HISTORY_INVALID", "Project command history version or fields are invalid", ProductErrorCategory.DATA_INTEGRITY)
    if document.get("authority") != authority:
        raise ProductError("ERR_PROJECT_HISTORY_AUTHORITY", "Project command history violates authority boundaries", ProductErrorCategory.SECURITY)
    try:
        rows = document["records"]
        if not isinstance(rows, list):
            raise ValueError("records must be an array")
        records = tuple(ProjectCommandRecord(
            record_id=row["record_id"], action=ProjectCommandAction(row["action"]),
            command_kind=row["command_kind"], target_identity=row["target_identity"],
            source_manifest_sha256=row["source_manifest_sha256"], result_manifest_sha256=row["result_manifest_sha256"],
            source_revision=row["source_revision"], result_revision=row["result_revision"],
            compensates_record_id=row["compensates_record_id"], stale_target_ids=tuple(row["stale_target_ids"]),
            recorded_at=row["recorded_at"], record_sha256=row["record_sha256"],
        ) for row in rows)
        expected_record_fields = {
            "record_id", "action", "command_kind", "target_identity",
            "source_manifest_sha256", "result_manifest_sha256", "source_revision",
            "result_revision", "compensates_record_id", "stale_target_ids",
            "recorded_at", "authority", "record_sha256",
        }
        for row in rows:
            if set(row) != expected_record_fields:
                raise ValueError("record fields are not exact")
            if row.get("authority") != authority:
                raise ValueError("record authority is invalid")
        return ProjectCommandHistory(document["project_id"], records, document["history_sha256"])
    except ProductError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductError("ERR_PROJECT_HISTORY_INVALID", "Project command history contains invalid values", ProductErrorCategory.DATA_INTEGRITY) from exc


class ProjectCommandHistoryStore:
    @staticmethod
    def path(project_root: str | Path, *, create: bool = False) -> Path:
        return _manifest_path(project_root, create_control_dir=create).with_name("history.json")

    @staticmethod
    def load(project_root: str | Path) -> ProjectCommandHistory:
        target = ProjectCommandHistoryStore.path(project_root)
        if target.is_symlink() or not target.is_file() or not 0 < target.stat().st_size <= _MAX_HISTORY_BYTES:
            raise ProductError("ERR_PROJECT_HISTORY_FILE_INVALID", "Project command history file is invalid", ProductErrorCategory.DATA_INTEGRITY)
        try:
            return parse_project_command_history(json.loads(target.read_text(encoding="utf-8")))
        except ProductError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_PROJECT_HISTORY_READ", "Project command history could not be read", ProductErrorCategory.DATA_INTEGRITY) from exc

    @staticmethod
    def save(project_root: str | Path, history: ProjectCommandHistory, *, expected_previous_history_sha256: str | None = None) -> AtomicWriteResult:
        target = ProjectCommandHistoryStore.path(project_root, create=True)
        with _exclusive_project_lock(_manifest_path(project_root, create_control_dir=True)):
            if target.exists():
                current = ProjectCommandHistoryStore.load(project_root)
                if expected_previous_history_sha256 != current.history_sha256:
                    raise ProductError("ERR_PROJECT_HISTORY_CAS_CONFLICT", "Command history changed before save", ProductErrorCategory.STATE)
            elif expected_previous_history_sha256 is not None:
                raise ProductError("ERR_PROJECT_HISTORY_PREVIOUS_MISSING", "Expected command history is missing", ProductErrorCategory.STATE)
            return AtomicJsonWriter.write(target, history.to_dict(), validator=parse_project_command_history)


@dataclass(frozen=True, slots=True)
class ProjectAutosavePolicy:
    debounce_seconds: int = 30
    quiescence_seconds: int = 5
    max_snapshots: int = 10

    def __post_init__(self) -> None:
        if not 1 <= self.debounce_seconds <= 3600 or not 1 <= self.quiescence_seconds <= 300 or not 1 <= self.max_snapshots <= 100:
            raise ValueError("Autosave policy is outside bounded limits")


@dataclass(frozen=True, slots=True)
class ProjectAutosaveResult:
    state: str
    manifest: ProductProjectManifest | None = None
    snapshot_path: Path | None = None


class ProductProjectAutosaveCoordinator:
    def __init__(self, policy: ProjectAutosavePolicy | None = None) -> None:
        self.policy = policy or ProjectAutosavePolicy()

    def autosave(
        self, project_root: str | Path, target_manifest: ProductProjectManifest,
        child_documents: Mapping[str, bytes], *, expected_previous_manifest_sha256: str,
        last_edit_at: str, previous_autosave_at: str | None = None, now: str | None = None,
    ) -> ProjectAutosaveResult:
        current_time = _timestamp(now or utc_now_iso(), "now")
        if (current_time - _timestamp(last_edit_at, "last_edit_at")).total_seconds() < self.policy.quiescence_seconds:
            return ProjectAutosaveResult("SKIPPED_NOT_QUIESCENT")
        if previous_autosave_at and (current_time - _timestamp(previous_autosave_at, "previous_autosave_at")).total_seconds() < self.policy.debounce_seconds:
            return ProjectAutosaveResult("SKIPPED_DEBOUNCE")
        _assert_snapshot_safe(target_manifest)
        saved = ProductProjectSaveCoordinator().save(
            project_root, target_manifest, child_documents,
            expected_previous_manifest_sha256=expected_previous_manifest_sha256,
        )
        directory = _control_subdir(project_root, "autosave", create=True)
        snapshot = directory / f"autosave-{saved.project_manifest_sha256.split(':', 1)[1]}.json"
        AtomicJsonWriter.write(snapshot, saved.to_dict(), validator=parse_product_project_manifest)
        _rotate_files(directory, "autosave-*.json", self.policy.max_snapshots)
        return ProjectAutosaveResult("SAVED", saved, snapshot)


@dataclass(frozen=True, slots=True)
class ProjectBackupPreview:
    backup_id: str
    backup_revision: int
    current_revision: int
    backup_manifest_sha256: str
    current_manifest_sha256: str
    exact_current_identity_required: bool = True


class ProductProjectBackupStore:
    @staticmethod
    def create(project_root: str | Path, *, max_backups: int = 10, created_at: str | None = None) -> str:
        if not 1 <= max_backups <= 100:
            raise ValueError("max_backups must be between 1 and 100")
        root = _project_root(project_root)
        lock_target = _manifest_path(root, create_control_dir=True)
        with _exclusive_project_lock(lock_target):
            ProductProjectSaveCoordinator._require_no_pending_recovery(root)
            manifest = ProductProjectManifestStore.load(root)
            _assert_snapshot_safe(manifest)
            backup_id = "backup-" + manifest.project_manifest_sha256.split(":", 1)[1]
            backups = _control_subdir(root, "backups", create=True)
            target = backups / backup_id
            if target.exists():
                ProductProjectBackupStore._load_verified(root, backup_id)
                return backup_id
            temporary = Path(tempfile.mkdtemp(prefix=".backup-", dir=backups))
            total = 0
            try:
                AtomicJsonWriter.write(temporary / "project.json", manifest.to_dict(), validator=parse_product_project_manifest)
                for binding in manifest.child_bindings:
                    source = ProductProjectSaveCoordinator._safe_child_target(root, binding.relative_path)
                    if not source.exists() and not binding.required:
                        continue
                    if source.is_symlink() or not source.is_file() or sha256_file_exact(source) != binding.content_sha256:
                        raise ProductError("ERR_PROJECT_BACKUP_CHILD_CONFLICT", "Project child is unavailable or changed", ProductErrorCategory.DATA_INTEGRITY, details={"relative_path": binding.relative_path})
                    child_size = source.stat().st_size
                    if child_size > _MAX_BACKUP_CHILD_BYTES:
                        raise ProductError("ERR_PROJECT_BACKUP_CHILD_SIZE", "Project backup child exceeds the bounded size", ProductErrorCategory.RESOURCE_EXHAUSTED, details={"relative_path": binding.relative_path})
                    total += child_size
                    if total > _MAX_BACKUP_BYTES:
                        raise ProductError("ERR_PROJECT_BACKUP_SIZE", "Project backup exceeds the bounded total", ProductErrorCategory.RESOURCE_EXHAUSTED)
                    destination = temporary / "children" / Path(*binding.relative_path.split("/"))
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with source.open("rb") as source_handle, destination.open("xb") as target_handle:
                        shutil.copyfileobj(source_handle, target_handle, length=1024 * 1024)
                        target_handle.flush()
                        os.fsync(target_handle.fileno())
                metadata = {
                    "backup_version": "1.0.0", "backup_id": backup_id,
                    "project_id": manifest.project_id, "created_at": created_at or utc_now_iso(),
                    "manifest_sha256": manifest.project_manifest_sha256, "total_child_bytes": total,
                    "authority": {"external_replay_authorized": False, "destructive_restore_authorized": False},
                }
                metadata["backup_sha256"] = sha256_bytes(canonical_json_bytes(metadata))
                AtomicJsonWriter.write(temporary / "backup.json", metadata)
                os.replace(temporary, target)
            except Exception:
                shutil.rmtree(temporary, ignore_errors=True)
                raise
            _rotate_directories(backups, "backup-*", max_backups)
            return backup_id

    @staticmethod
    def preview_restore(project_root: str | Path, backup_id: str) -> ProjectBackupPreview:
        root = _project_root(project_root)
        backup = ProductProjectBackupStore._load_verified(root, backup_id)
        current = ProductProjectManifestStore.load(root)
        if current.project_id != backup.project_id:
            raise ProductError("ERR_PROJECT_BACKUP_IDENTITY_CONFLICT", "Backup belongs to another Project", ProductErrorCategory.SECURITY)
        return ProjectBackupPreview(
            backup_id, backup.project_revision, current.project_revision,
            backup.project_manifest_sha256, current.project_manifest_sha256,
        )

    @staticmethod
    def restore(project_root: str | Path, backup_id: str, *, expected_current_manifest_sha256: str) -> ProductProjectManifest:
        root = _project_root(project_root)
        backup = ProductProjectBackupStore._load_verified(root, backup_id)
        current = ProductProjectManifestStore.load(root)
        if current.project_manifest_sha256 != expected_current_manifest_sha256:
            raise ProductError("ERR_PROJECT_BACKUP_RESTORE_CONFLICT", "Project changed after restore preview", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        if current.project_id != backup.project_id:
            raise ProductError("ERR_PROJECT_BACKUP_IDENTITY_CONFLICT", "Backup belongs to another Project", ProductErrorCategory.SECURITY)
        if {item.identity for item in current.child_bindings} != {item.identity for item in backup.child_bindings}:
            raise ProductError("ERR_PROJECT_BACKUP_BINDING_CONFLICT", "Restore would add or remove child bindings", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        documents: dict[str, bytes] = {}
        directory = _backup_directory(root, backup_id)
        for binding in backup.child_bindings:
            source = directory / "children" / Path(*binding.relative_path.split("/"))
            if source.exists():
                documents[binding.relative_path] = source.read_bytes()
        updated_at = utc_now_iso()
        if _timestamp(updated_at, "updated_at") < _timestamp(current.updated_at, "current.updated_at"):
            updated_at = current.updated_at
        target = ProductProjectManifest.create(
            project_id=current.project_id, project_revision=current.project_revision + 1,
            product_version=current.product_version, timebase=backup.timebase,
            child_bindings=backup.child_bindings, created_at=current.created_at,
            updated_at=updated_at,
        )
        return ProductProjectSaveCoordinator().save(
            root, target, documents,
            expected_previous_manifest_sha256=expected_current_manifest_sha256,
        )

    @staticmethod
    def _load_verified(root: Path, backup_id: str) -> ProductProjectManifest:
        directory = _backup_directory(root, backup_id)
        metadata_path = directory / "backup.json"
        manifest_path = directory / "project.json"
        if metadata_path.is_symlink() or manifest_path.is_symlink() or not metadata_path.is_file() or not manifest_path.is_file():
            raise ProductError("ERR_PROJECT_BACKUP_INVALID", "Backup metadata or manifest is invalid", ProductErrorCategory.DATA_INTEGRITY)
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            expected_fields = {
                "backup_version", "backup_id", "project_id", "created_at", "manifest_sha256",
                "total_child_bytes", "authority", "backup_sha256",
            }
            if not isinstance(metadata, dict) or set(metadata) != expected_fields:
                raise ValueError("backup metadata fields are not exact")
            checksum = metadata.pop("backup_sha256")
            if (
                checksum != sha256_bytes(canonical_json_bytes(metadata))
                or metadata.get("backup_version") != "1.0.0"
                or metadata.get("backup_id") != backup_id
                or metadata.get("authority") != {"external_replay_authorized": False, "destructive_restore_authorized": False}
            ):
                raise ValueError("backup checksum or identity mismatch")
            _timestamp(metadata["created_at"], "backup.created_at")
            manifest = parse_product_project_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
            if metadata.get("manifest_sha256") != manifest.project_manifest_sha256 or metadata.get("project_id") != manifest.project_id:
                raise ValueError("backup manifest checksum mismatch")
            total = 0
            for binding in manifest.child_bindings:
                child = directory / "children" / Path(*binding.relative_path.split("/"))
                if child.exists() and (
                    child.is_symlink()
                    or not child.is_file()
                    or not child.resolve(strict=True).is_relative_to(directory.resolve(strict=True))
                    or child.stat().st_size > _MAX_BACKUP_CHILD_BYTES
                    or sha256_file_exact(child) != binding.content_sha256
                ):
                    raise ValueError("backup child checksum mismatch")
                if binding.required and not child.is_file():
                    raise ValueError("required backup child is missing")
                if child.is_file():
                    total += child.stat().st_size
            if total != metadata.get("total_child_bytes") or total > _MAX_BACKUP_BYTES:
                raise ValueError("backup total size mismatch")
            return manifest
        except ProductError:
            raise
        except (KeyError, OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise ProductError("ERR_PROJECT_BACKUP_INVALID", "Backup verification failed", ProductErrorCategory.DATA_INTEGRITY) from exc


def _assert_snapshot_safe(manifest: ProductProjectManifest) -> None:
    for binding in manifest.child_bindings:
        identity = f"{binding.domain_owner}/{binding.relative_path}".casefold()
        if any(term in identity for term in _FORBIDDEN_SNAPSHOT_TERMS):
            raise ProductError("ERR_PROJECT_SNAPSHOT_PRIVATE_BINDING", "Private credential/token material cannot enter Autosave or Backup", ProductErrorCategory.SECURITY, details={"relative_path": binding.relative_path})


def _control_subdir(project_root: str | Path, name: str, *, create: bool = False) -> Path:
    root = _project_root(project_root)
    control = _manifest_path(root, create_control_dir=create).parent
    target = control / name
    if create and not target.exists():
        target.mkdir(mode=0o700)
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        raise ProductError("ERR_PROJECT_SNAPSHOT_PATH_INVALID", "Project snapshot directory is invalid", ProductErrorCategory.SECURITY)
    return target


def _backup_directory(root: Path, backup_id: str) -> Path:
    if not re.fullmatch(r"backup-[0-9a-f]{64}", backup_id):
        raise ProductError("ERR_PROJECT_BACKUP_ID_INVALID", "Backup identity is invalid", ProductErrorCategory.VALIDATION)
    directory = _control_subdir(root, "backups") / backup_id
    if directory.is_symlink() or not directory.is_dir():
        raise ProductError("ERR_PROJECT_BACKUP_INVALID", "Backup directory is invalid", ProductErrorCategory.DATA_INTEGRITY)
    return directory


def _rotate_files(directory: Path, pattern: str, retain: int) -> None:
    candidates = sorted((path for path in directory.glob(pattern) if path.is_file() and not path.is_symlink()), key=lambda path: (path.stat().st_mtime_ns, path.name))
    for path in candidates[:-retain]:
        path.unlink()


def _rotate_directories(directory: Path, pattern: str, retain: int) -> None:
    candidates = sorted((path for path in directory.glob(pattern) if path.is_dir() and not path.is_symlink()), key=lambda path: (path.stat().st_mtime_ns, path.name))
    for path in candidates[:-retain]:
        shutil.rmtree(path)
