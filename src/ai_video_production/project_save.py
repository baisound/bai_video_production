"""TASK-043 coordinated Project save journal and deterministic recovery."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from contextlib import nullcontext
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Callable, ContextManager, Mapping, Protocol

from .atomic import AtomicJsonWriter, AtomicWriteResult
from .errors import ProductError, ProductErrorCategory
from .product_project import (
    ProductProjectManifest,
    parse_product_project_manifest,
    sha256_file_exact,
    validate_project_relative_path,
)
from .product_project_store import (
    ProductProjectManifestStore,
    _exclusive_project_lock,
    _manifest_path,
    _project_root,
)
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso, validate_sha256


FailureInjector = Callable[[str, Path], None]
_JOURNAL_VERSION = "1.0.0"
_PARTICIPANT_JOURNAL_VERSION = "1.1.0"
_MAX_JOURNAL_BYTES = 8 * 1024 * 1024
_MAX_CHILD_BYTES = 64 * 1024 * 1024
_MAX_TOTAL_STAGED_BYTES = 256 * 1024 * 1024
_PARTICIPANT_ID = re.compile(r"[A-Z][A-Z0-9]*(?:[-./][A-Z0-9]+){1,7}")
_PARTICIPANT_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")


class ProjectSaveState(str, Enum):
    PREPARING = "PREPARING"
    STAGED = "STAGED"
    VALIDATED = "VALIDATED"
    COMMITTING = "COMMITTING"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    COMMITTED = "COMMITTED"
    ABANDONED = "ABANDONED"


class ProjectSaveParticipantOutcome(str, Enum):
    COMPLETE = "COMPLETE"
    ROLLBACK = "ROLLBACK"


@dataclass(frozen=True, slots=True)
class ProjectSaveParticipantPlan:
    participant_id: str
    participant_version: str
    project_id: str
    source_manifest_sha256: str
    target_manifest_sha256: str
    source_content_sha256: str | None
    target_content_sha256: str
    binding_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.participant_id, str) or not _PARTICIPANT_ID.fullmatch(self.participant_id):
            raise ValueError("participant_id is invalid")
        if not isinstance(self.participant_version, str) or not _PARTICIPANT_VERSION.fullmatch(self.participant_version):
            raise ValueError("participant_version is invalid")
        if not isinstance(self.project_id, str) or not self.project_id:
            raise ValueError("participant project_id is invalid")
        for name in ("source_manifest_sha256", "target_manifest_sha256", "target_content_sha256"):
            validate_sha256(getattr(self, name), field_name=name)
        if self.source_content_sha256 is not None:
            validate_sha256(self.source_content_sha256, field_name="source_content_sha256")
        validate_sha256(self.binding_sha256, field_name="binding_sha256")
        if self.binding_sha256 != sha256_bytes(canonical_json_bytes(self._body())):
            raise ValueError("participant binding checksum mismatch")

    @classmethod
    def create(
        cls,
        *,
        participant_id: str,
        participant_version: str,
        project_id: str,
        source_manifest_sha256: str,
        target_manifest_sha256: str,
        source_content_sha256: str | None,
        target_content_sha256: str,
    ) -> "ProjectSaveParticipantPlan":
        values = {
            "participant_id": participant_id,
            "participant_version": participant_version,
            "project_id": project_id,
            "source_manifest_sha256": source_manifest_sha256,
            "target_manifest_sha256": target_manifest_sha256,
            "source_content_sha256": source_content_sha256,
            "target_content_sha256": target_content_sha256,
        }
        return cls(**values, binding_sha256=sha256_bytes(canonical_json_bytes(values)))

    def _body(self) -> dict[str, object]:
        return {
            "participant_id": self.participant_id,
            "participant_version": self.participant_version,
            "project_id": self.project_id,
            "source_manifest_sha256": self.source_manifest_sha256,
            "target_manifest_sha256": self.target_manifest_sha256,
            "source_content_sha256": self.source_content_sha256,
            "target_content_sha256": self.target_content_sha256,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "binding_sha256": self.binding_sha256}


@dataclass(frozen=True, slots=True)
class ProjectSaveParticipantResult:
    participant_id: str
    binding_sha256: str
    transaction_id: str
    outcome: ProjectSaveParticipantOutcome
    result_content_sha256: str | None
    receipt_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.participant_id, str) or not _PARTICIPANT_ID.fullmatch(self.participant_id):
            raise ValueError("participant result identity is invalid")
        if not isinstance(self.transaction_id, str) or not re.fullmatch(r"save-[0-9a-f]{64}", self.transaction_id):
            raise ValueError("participant transaction identity is invalid")
        if not isinstance(self.outcome, ProjectSaveParticipantOutcome):
            raise ValueError("participant outcome is invalid")
        for name in ("binding_sha256", "receipt_sha256"):
            validate_sha256(getattr(self, name), field_name=name)
        if self.result_content_sha256 is not None:
            validate_sha256(self.result_content_sha256, field_name="result_content_sha256")
        if self.receipt_sha256 != sha256_bytes(canonical_json_bytes(self._body())):
            raise ValueError("participant result checksum mismatch")

    @classmethod
    def create(
        cls,
        *,
        participant_id: str,
        binding_sha256: str,
        transaction_id: str,
        outcome: ProjectSaveParticipantOutcome,
        result_content_sha256: str | None,
    ) -> "ProjectSaveParticipantResult":
        values = {
            "participant_id": participant_id,
            "binding_sha256": binding_sha256,
            "transaction_id": transaction_id,
            "outcome": outcome,
            "result_content_sha256": result_content_sha256,
        }
        body = {**values, "outcome": outcome.value}
        return cls(**values, receipt_sha256=sha256_bytes(canonical_json_bytes(body)))

    def _body(self) -> dict[str, object]:
        return {
            "participant_id": self.participant_id,
            "binding_sha256": self.binding_sha256,
            "transaction_id": self.transaction_id,
            "outcome": self.outcome.value,
            "result_content_sha256": self.result_content_sha256,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "receipt_sha256": self.receipt_sha256}


class ProjectSaveParticipant(Protocol):
    participant_id: str
    participant_version: str

    def plan_locked(
        self,
        project_root: Path,
        source_manifest: ProductProjectManifest,
        target_manifest: ProductProjectManifest,
    ) -> ProjectSaveParticipantPlan: ...

    def prepare_locked(
        self,
        project_root: Path,
        transaction_id: str,
        plan: ProjectSaveParticipantPlan,
    ) -> str: ...

    def reconcile_locked(
        self,
        project_root: Path,
        transaction_id: str,
        plan: ProjectSaveParticipantPlan,
        prepared_receipt_sha256: str,
        outcome: ProjectSaveParticipantOutcome,
    ) -> ProjectSaveParticipantResult: ...

    def abort_prejournal_locked(
        self,
        project_root: Path,
        transaction_id: str,
        plan: ProjectSaveParticipantPlan,
        prepared_receipt_sha256: str,
    ) -> None: ...

    def reconcile_orphan_locked(
        self,
        project_root: Path,
        current_manifest: ProductProjectManifest,
    ) -> str | None: ...


@dataclass(frozen=True, slots=True)
class ProjectSaveEntry:
    relative_path: str
    before_sha256: str | None
    target_sha256: str
    staged_relative_path: str
    backup_relative_path: str | None
    committed: bool = False

    def __post_init__(self) -> None:
        validate_project_relative_path(self.relative_path)
        validate_project_relative_path(self.staged_relative_path)
        if self.backup_relative_path is not None:
            validate_project_relative_path(self.backup_relative_path)
        if self.before_sha256 is not None:
            validate_sha256(self.before_sha256, field_name="before_sha256")
        validate_sha256(self.target_sha256, field_name="target_sha256")
        if not isinstance(self.committed, bool):
            raise ValueError("committed must be boolean")

    def to_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "before_sha256": self.before_sha256,
            "target_sha256": self.target_sha256,
            "staged_relative_path": self.staged_relative_path,
            "backup_relative_path": self.backup_relative_path,
            "committed": self.committed,
        }


@dataclass(frozen=True, slots=True)
class ProjectSaveJournal:
    journal_version: str
    transaction_id: str
    project_id: str
    source_manifest_sha256: str
    target_manifest: ProductProjectManifest
    state: ProjectSaveState
    entries: tuple[ProjectSaveEntry, ...]
    journal_revision: int
    created_at: str
    updated_at: str
    last_error_code: str | None
    participant_plan: ProjectSaveParticipantPlan | None
    participant_prepared_receipt_sha256: str | None
    participant_result: ProjectSaveParticipantResult | None
    journal_sha256: str

    def __post_init__(self) -> None:
        if not self.transaction_id.startswith("save-") or len(self.transaction_id) != 69:
            raise ValueError("transaction_id is invalid")
        if self.journal_version not in {_JOURNAL_VERSION, _PARTICIPANT_JOURNAL_VERSION}:
            raise ValueError("journal_version is invalid")
        if self.project_id != self.target_manifest.project_id:
            raise ValueError("journal project identity mismatch")
        validate_sha256(self.source_manifest_sha256, field_name="source_manifest_sha256")
        if isinstance(self.journal_revision, bool) or not isinstance(self.journal_revision, int) or self.journal_revision < 1:
            raise ValueError("journal_revision must be positive")
        _validate_utc_timestamp(self.created_at, "created_at")
        _validate_utc_timestamp(self.updated_at, "updated_at")
        paths = [entry.relative_path.casefold() for entry in self.entries]
        if len(paths) != len(set(paths)):
            raise ValueError("journal entries contain duplicate paths")
        if self.last_error_code is not None and not self.last_error_code.startswith("ERR_"):
            raise ValueError("last_error_code must be a Product error code")
        if self.journal_version == _JOURNAL_VERSION:
            if any(value is not None for value in (
                self.participant_plan,
                self.participant_prepared_receipt_sha256,
                self.participant_result,
            )):
                raise ValueError("v1.0 journal cannot carry a participant")
        else:
            if self.participant_plan is None or self.participant_prepared_receipt_sha256 is None:
                raise ValueError("v1.1 journal requires a prepared participant")
            validate_sha256(
                self.participant_prepared_receipt_sha256,
                field_name="participant_prepared_receipt_sha256",
            )
            if (
                self.participant_plan.project_id != self.project_id
                or self.participant_plan.source_manifest_sha256 != self.source_manifest_sha256
                or self.participant_plan.target_manifest_sha256
                != self.target_manifest.project_manifest_sha256
            ):
                raise ValueError("participant plan crosses Project save scope")
            if self.participant_result is not None and (
                self.participant_result.participant_id != self.participant_plan.participant_id
                or self.participant_result.binding_sha256 != self.participant_plan.binding_sha256
                or self.participant_result.transaction_id != self.transaction_id
            ):
                raise ValueError("participant result crosses its plan")
            if self.state is ProjectSaveState.COMMITTED and (
                self.participant_result is None
                or self.participant_result.outcome is not ProjectSaveParticipantOutcome.COMPLETE
            ):
                raise ValueError("committed participant journal lacks COMPLETE result")
            if self.state is ProjectSaveState.ABANDONED and (
                self.participant_result is None
                or self.participant_result.outcome is not ProjectSaveParticipantOutcome.ROLLBACK
            ):
                raise ValueError("abandoned participant journal lacks ROLLBACK result")
        target_by_path = {binding.relative_path: binding for binding in self.target_manifest.child_bindings}
        for entry in self.entries:
            binding = target_by_path.get(entry.relative_path)
            if binding is None or binding.content_sha256 != entry.target_sha256:
                raise ValueError("journal entry is not bound by the target manifest")
            expected_staged = f"staging/{self.transaction_id}/new/{entry.relative_path}"
            expected_backup = None if entry.before_sha256 is None else f"staging/{self.transaction_id}/backup/{entry.relative_path}"
            if entry.staged_relative_path != expected_staged or entry.backup_relative_path != expected_backup:
                raise ValueError("journal staging/backup path escapes its transaction scope")
        expected_transaction_id = _save_transaction_id(
            self.project_id,
            self.source_manifest_sha256,
            self.target_manifest.project_manifest_sha256,
            {entry.relative_path: entry.target_sha256 for entry in self.entries},
            participant_binding_sha256=(
                None if self.participant_plan is None else self.participant_plan.binding_sha256
            ),
        )
        if self.transaction_id != expected_transaction_id:
            raise ValueError("transaction_id does not match the save operation identity")
        validate_sha256(self.journal_sha256, field_name="journal_sha256")
        if sha256_bytes(canonical_json_bytes(self._body())) != self.journal_sha256:
            raise ValueError("journal_sha256 does not match the journal body")

    @classmethod
    def create(
        cls,
        *,
        transaction_id: str,
        source_manifest_sha256: str,
        target_manifest: ProductProjectManifest,
        entries: tuple[ProjectSaveEntry, ...],
        participant_plan: ProjectSaveParticipantPlan | None = None,
        participant_prepared_receipt_sha256: str | None = None,
    ) -> "ProjectSaveJournal":
        now = utc_now_iso()
        return _journal(
            journal_version=(
                _JOURNAL_VERSION if participant_plan is None else _PARTICIPANT_JOURNAL_VERSION
            ),
            transaction_id=transaction_id,
            project_id=target_manifest.project_id,
            source_manifest_sha256=source_manifest_sha256,
            target_manifest=target_manifest,
            state=ProjectSaveState.PREPARING,
            entries=entries,
            journal_revision=1,
            created_at=now,
            updated_at=now,
            last_error_code=None,
            participant_plan=participant_plan,
            participant_prepared_receipt_sha256=participant_prepared_receipt_sha256,
            participant_result=None,
        )

    def transition(
        self,
        state: ProjectSaveState,
        *,
        entries: tuple[ProjectSaveEntry, ...] | None = None,
        last_error_code: str | None = None,
    ) -> "ProjectSaveJournal":
        allowed = {
            ProjectSaveState.PREPARING: {ProjectSaveState.STAGED, ProjectSaveState.RECOVERY_REQUIRED, ProjectSaveState.ABANDONED},
            ProjectSaveState.STAGED: {ProjectSaveState.VALIDATED, ProjectSaveState.RECOVERY_REQUIRED, ProjectSaveState.ABANDONED},
            ProjectSaveState.VALIDATED: {ProjectSaveState.COMMITTING, ProjectSaveState.RECOVERY_REQUIRED, ProjectSaveState.ABANDONED},
            ProjectSaveState.COMMITTING: {
                ProjectSaveState.COMMITTING,
                ProjectSaveState.RECOVERY_REQUIRED,
                ProjectSaveState.COMMITTED,
                ProjectSaveState.ABANDONED,
            },
            ProjectSaveState.RECOVERY_REQUIRED: {ProjectSaveState.COMMITTING, ProjectSaveState.ABANDONED, ProjectSaveState.COMMITTED},
            ProjectSaveState.COMMITTED: set(),
            ProjectSaveState.ABANDONED: set(),
        }
        if state not in allowed[self.state]:
            raise ValueError(f"invalid Project save transition {self.state.value} -> {state.value}")
        return _journal(
            journal_version=self.journal_version,
            transaction_id=self.transaction_id,
            project_id=self.project_id,
            source_manifest_sha256=self.source_manifest_sha256,
            target_manifest=self.target_manifest,
            state=state,
            entries=self.entries if entries is None else entries,
            journal_revision=self.journal_revision + 1,
            created_at=self.created_at,
            updated_at=utc_now_iso(),
            last_error_code=last_error_code,
            participant_plan=self.participant_plan,
            participant_prepared_receipt_sha256=self.participant_prepared_receipt_sha256,
            participant_result=self.participant_result,
        )

    def record_participant_result(
        self,
        result: ProjectSaveParticipantResult,
    ) -> "ProjectSaveJournal":
        if self.journal_version != _PARTICIPANT_JOURNAL_VERSION:
            raise ValueError("v1.0 journal cannot record a participant result")
        if self.participant_result is not None and self.participant_result != result:
            raise ValueError("participant result conflicts with the durable result")
        return _journal(
            journal_version=self.journal_version,
            transaction_id=self.transaction_id,
            project_id=self.project_id,
            source_manifest_sha256=self.source_manifest_sha256,
            target_manifest=self.target_manifest,
            state=self.state,
            entries=self.entries,
            journal_revision=self.journal_revision + 1,
            created_at=self.created_at,
            updated_at=utc_now_iso(),
            last_error_code=self.last_error_code,
            participant_plan=self.participant_plan,
            participant_prepared_receipt_sha256=self.participant_prepared_receipt_sha256,
            participant_result=result,
        )

    def _body(self) -> dict[str, object]:
        return _journal_body(
            journal_version=self.journal_version,
            transaction_id=self.transaction_id,
            project_id=self.project_id,
            source_manifest_sha256=self.source_manifest_sha256,
            target_manifest=self.target_manifest,
            state=self.state,
            entries=self.entries,
            journal_revision=self.journal_revision,
            created_at=self.created_at,
            updated_at=self.updated_at,
            last_error_code=self.last_error_code,
            participant_plan=self.participant_plan,
            participant_prepared_receipt_sha256=self.participant_prepared_receipt_sha256,
            participant_result=self.participant_result,
        )

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "journal_sha256": self.journal_sha256}


def _journal(**values: Any) -> ProjectSaveJournal:
    body = _journal_body(**values)
    return ProjectSaveJournal(**values, journal_sha256=sha256_bytes(canonical_json_bytes(body)))


def _journal_body(
    *,
    journal_version: str,
    transaction_id: str,
    project_id: str,
    source_manifest_sha256: str,
    target_manifest: ProductProjectManifest,
    state: ProjectSaveState,
    entries: tuple[ProjectSaveEntry, ...],
    journal_revision: int,
    created_at: str,
    updated_at: str,
    last_error_code: str | None,
    participant_plan: ProjectSaveParticipantPlan | None,
    participant_prepared_receipt_sha256: str | None,
    participant_result: ProjectSaveParticipantResult | None,
) -> dict[str, object]:
    body: dict[str, object] = {
        "journal_version": journal_version,
        "transaction_id": transaction_id,
        "project_id": project_id,
        "source_manifest_sha256": source_manifest_sha256,
        "target_manifest": target_manifest.to_dict(),
        "state": state.value,
        "entries": [entry.to_dict() for entry in entries],
        "journal_revision": journal_revision,
        "created_at": created_at,
        "updated_at": updated_at,
        "last_error_code": last_error_code,
        "authority": {"external_replay_authorized": False, "migration_apply_authorized": False},
    }
    if journal_version == _PARTICIPANT_JOURNAL_VERSION:
        body.update({
            "participant_plan": None if participant_plan is None else participant_plan.to_dict(),
            "participant_prepared_receipt_sha256": participant_prepared_receipt_sha256,
            "participant_result": None if participant_result is None else participant_result.to_dict(),
        })
    return body


def _parse_participant_plan(value: Mapping[str, Any]) -> ProjectSaveParticipantPlan:
    fields = {
        "participant_id", "participant_version", "project_id",
        "source_manifest_sha256", "target_manifest_sha256",
        "source_content_sha256", "target_content_sha256", "binding_sha256",
    }
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError("participant plan fields are not exact")
    return ProjectSaveParticipantPlan(**{name: value[name] for name in fields})


def _parse_participant_result(value: Mapping[str, Any] | None) -> ProjectSaveParticipantResult | None:
    if value is None:
        return None
    fields = {
        "participant_id", "binding_sha256", "transaction_id", "outcome",
        "result_content_sha256", "receipt_sha256",
    }
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError("participant result fields are not exact")
    return ProjectSaveParticipantResult(
        participant_id=value["participant_id"],
        binding_sha256=value["binding_sha256"],
        transaction_id=value["transaction_id"],
        outcome=ProjectSaveParticipantOutcome(value["outcome"]),
        result_content_sha256=value["result_content_sha256"],
        receipt_sha256=value["receipt_sha256"],
    )


def parse_project_save_journal(document: Mapping[str, Any]) -> ProjectSaveJournal:
    if not isinstance(document, Mapping):
        raise ProductError("ERR_PROJECT_SAVE_JOURNAL_INVALID", "Project save journal root must be an object", ProductErrorCategory.DATA_INTEGRITY)
    version = document.get("journal_version")
    fields_v1 = {
        "journal_version", "transaction_id", "project_id", "source_manifest_sha256",
        "target_manifest", "state", "entries", "journal_revision", "created_at",
        "updated_at", "last_error_code", "authority", "journal_sha256",
    }
    fields_v1_1 = fields_v1 | {
        "participant_plan", "participant_prepared_receipt_sha256", "participant_result",
    }
    if (
        (version == _JOURNAL_VERSION and set(document) != fields_v1)
        or (version == _PARTICIPANT_JOURNAL_VERSION and set(document) != fields_v1_1)
        or version not in {_JOURNAL_VERSION, _PARTICIPANT_JOURNAL_VERSION}
    ):
        raise ProductError("ERR_PROJECT_SAVE_JOURNAL_VERSION", "Project save journal version/fields are unsupported", ProductErrorCategory.DATA_INTEGRITY)
    if document.get("authority") != {"external_replay_authorized": False, "migration_apply_authorized": False}:
        raise ProductError("ERR_PROJECT_SAVE_JOURNAL_AUTHORITY", "Project save journal violates authority boundaries", ProductErrorCategory.SECURITY)
    try:
        raw_entries = document["entries"]
        if not isinstance(raw_entries, list):
            raise ValueError("entries must be an array")
        entries = tuple(ProjectSaveEntry(
            relative_path=row["relative_path"], before_sha256=row["before_sha256"],
            target_sha256=row["target_sha256"], staged_relative_path=row["staged_relative_path"],
            backup_relative_path=row["backup_relative_path"], committed=row["committed"],
        ) for row in raw_entries)
        participant_plan = (
            None
            if version == _JOURNAL_VERSION
            else _parse_participant_plan(document["participant_plan"])
        )
        participant_result = (
            None
            if version == _JOURNAL_VERSION
            else _parse_participant_result(document["participant_result"])
        )
        return ProjectSaveJournal(
            journal_version=version,
            transaction_id=document["transaction_id"], project_id=document["project_id"],
            source_manifest_sha256=document["source_manifest_sha256"],
            target_manifest=parse_product_project_manifest(document["target_manifest"]),
            state=ProjectSaveState(document["state"]), entries=entries,
            journal_revision=document["journal_revision"], created_at=document["created_at"],
            updated_at=document["updated_at"], last_error_code=document["last_error_code"],
            participant_plan=participant_plan,
            participant_prepared_receipt_sha256=(
                None
                if version == _JOURNAL_VERSION
                else document["participant_prepared_receipt_sha256"]
            ),
            participant_result=participant_result,
            journal_sha256=document["journal_sha256"],
        )
    except ProductError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductError("ERR_PROJECT_SAVE_JOURNAL_INVALID", "Project save journal contains invalid values", ProductErrorCategory.DATA_INTEGRITY) from exc


class ProjectSaveJournalStore:
    @staticmethod
    def path(project_root: str | Path, *, create_control_dir: bool = False) -> Path:
        return _manifest_path(project_root, create_control_dir=create_control_dir).with_name("save-journal.json")

    @staticmethod
    def load(project_root: str | Path) -> ProjectSaveJournal:
        target = ProjectSaveJournalStore.path(project_root)
        if target.is_symlink() or not target.is_file():
            raise ProductError("ERR_PROJECT_SAVE_JOURNAL_FILE_INVALID", "Project save journal must be a regular non-symlink file", ProductErrorCategory.VALIDATION)
        if not 0 < target.stat().st_size <= _MAX_JOURNAL_BYTES:
            raise ProductError("ERR_PROJECT_SAVE_JOURNAL_SIZE", "Project save journal size is outside the allowed bound", ProductErrorCategory.VALIDATION)
        try:
            value = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_PROJECT_SAVE_JOURNAL_READ", "Project save journal could not be read", ProductErrorCategory.DATA_INTEGRITY) from exc
        return parse_project_save_journal(value)

    @staticmethod
    def save(project_root: str | Path, journal: ProjectSaveJournal) -> AtomicWriteResult:
        return AtomicJsonWriter.write(ProjectSaveJournalStore.path(project_root, create_control_dir=True), journal.to_dict(), validator=parse_project_save_journal)


class ProductProjectSaveCoordinator:
    def __init__(self, *, failure_injector: FailureInjector | None = None) -> None:
        self.failure_injector = failure_injector

    def save(
        self,
        project_root: str | Path,
        target_manifest: ProductProjectManifest,
        child_documents: Mapping[str, bytes],
        *,
        expected_previous_manifest_sha256: str,
        participant: ProjectSaveParticipant | None = None,
        commit_guard: Callable[[], ContextManager[None]] | None = None,
    ) -> ProductProjectManifest:
        root = _project_root(project_root)
        lock_target = _manifest_path(root, create_control_dir=True)
        with _exclusive_project_lock(lock_target):
            guard = nullcontext() if commit_guard is None else commit_guard()
            if not hasattr(guard, "__enter__") or not hasattr(guard, "__exit__"):
                raise ProductError(
                    "ERR_PROJECT_SAVE_COMMIT_GUARD_INVALID",
                    "Project save commit guard is invalid",
                    ProductErrorCategory.INTERNAL,
                )
            with guard:
                return self._save_locked(
                    root,
                    target_manifest,
                    child_documents,
                    expected_previous_manifest_sha256=expected_previous_manifest_sha256,
                    participant=participant,
                )

    def _save_locked(
        self,
        root: Path,
        target_manifest: ProductProjectManifest,
        child_documents: Mapping[str, bytes],
        *,
        expected_previous_manifest_sha256: str,
        participant: ProjectSaveParticipant | None,
    ) -> ProductProjectManifest:
        self._require_no_pending_recovery(root)
        current = ProductProjectManifestStore.load(root)
        self._require_manifest_transition(current, target_manifest, expected_previous_manifest_sha256)
        normalized = self._validate_documents(root, current, target_manifest, child_documents)
        plan = None
        if participant is not None:
            plan = participant.plan_locked(root, current, target_manifest)
            self._validate_participant(participant, plan, current, target_manifest)
        transaction_id = self._transaction_id(
            current,
            target_manifest,
            normalized,
            participant_binding_sha256=None if plan is None else plan.binding_sha256,
        )
        entries = self._prepare_entries(root, transaction_id, current, target_manifest, normalized)
        prepared_receipt = None
        if participant is not None:
            prepared_receipt = participant.prepare_locked(root, transaction_id, plan)
            validate_sha256(prepared_receipt, field_name="participant_prepared_receipt_sha256")
        journal = ProjectSaveJournal.create(
            transaction_id=transaction_id,
            source_manifest_sha256=current.project_manifest_sha256,
            target_manifest=target_manifest,
            entries=entries,
            participant_plan=plan,
            participant_prepared_receipt_sha256=prepared_receipt,
        )
        try:
            ProjectSaveJournalStore.save(root, journal)
        except Exception:
            if participant is not None and not self._journal_matches(root, transaction_id):
                participant.abort_prejournal_locked(root, transaction_id, plan, prepared_receipt)
            raise
        try:
            self._stage_documents(root, journal, normalized)
            journal = journal.transition(ProjectSaveState.STAGED)
            ProjectSaveJournalStore.save(root, journal)
            self._inject("after_journal_staged", root)
            self._validate_staging(root, journal)
            journal = journal.transition(ProjectSaveState.VALIDATED)
            ProjectSaveJournalStore.save(root, journal)
            self._inject("after_journal_validated", root)
            self._revalidate_source(root, current, journal)
            journal = journal.transition(ProjectSaveState.COMMITTING)
            ProjectSaveJournalStore.save(root, journal)
            journal = self._commit_children(root, journal)
            self._inject("before_manifest_commit", root)
            ProductProjectManifestStore._save_unlocked(
                root,
                target_manifest,
                expected_previous_manifest_sha256=current.project_manifest_sha256,
            )
            self._inject("after_manifest_commit", root)
            if participant is not None:
                result = participant.reconcile_locked(
                    root,
                    transaction_id,
                    plan,
                    prepared_receipt,
                    ProjectSaveParticipantOutcome.COMPLETE,
                )
                self._validate_participant_result(journal, result, ProjectSaveParticipantOutcome.COMPLETE)
                journal = journal.record_participant_result(result)
                ProjectSaveJournalStore.save(root, journal)
            journal = journal.transition(ProjectSaveState.COMMITTED)
            ProjectSaveJournalStore.save(root, journal)
            return target_manifest
        except Exception as exc:
            self._mark_recovery_required(root, journal, exc)
            raise

    def recovery_status(self, project_root: str | Path) -> dict[str, object]:
        root = _project_root(project_root)
        path = ProjectSaveJournalStore.path(root)
        if not path.exists():
            return {"required": False, "state": "NONE", "available_actions": []}
        journal = ProjectSaveJournalStore.load(root)
        if journal.state in {ProjectSaveState.COMMITTED, ProjectSaveState.ABANDONED}:
            return {"required": False, "state": journal.state.value, "transaction_id": journal.transaction_id, "available_actions": []}
        current = ProductProjectManifestStore.load(root)
        if (
            journal.participant_result is not None
            and journal.participant_result.outcome is ProjectSaveParticipantOutcome.ROLLBACK
        ):
            actions = ["ROLLBACK"]
        elif (
            journal.participant_result is not None
            and journal.participant_result.outcome is ProjectSaveParticipantOutcome.COMPLETE
        ):
            actions = ["FINALIZE"]
        else:
            actions = ["FINALIZE"] if current.project_manifest_sha256 == journal.target_manifest.project_manifest_sha256 else ["COMPLETE", "ROLLBACK"]
        return {
            "required": True,
            "state": journal.state.value,
            "transaction_id": journal.transaction_id,
            "available_actions": actions,
            "participant_required": journal.participant_plan is not None,
            "participant_id": (
                None if journal.participant_plan is None else journal.participant_plan.participant_id
            ),
        }

    def reconcile_participant_orphan(
        self,
        project_root: str | Path,
        *,
        participant: ProjectSaveParticipant,
    ) -> dict[str, object]:
        """Reconcile a participant receipt left before the first journal write."""
        root = _project_root(project_root)
        lock_target = _manifest_path(root, create_control_dir=True)
        with _exclusive_project_lock(lock_target):
            path = ProjectSaveJournalStore.path(root)
            if path.exists():
                journal = ProjectSaveJournalStore.load(root)
                if journal.state not in {ProjectSaveState.COMMITTED, ProjectSaveState.ABANDONED}:
                    raise ProductError(
                        "ERR_PROJECT_SAVE_RECOVERY_REQUIRED",
                        "Project save recovery must finish before orphan reconciliation",
                        ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                    )
            current = ProductProjectManifestStore.load(root)
            receipt = participant.reconcile_orphan_locked(root, current)
            if receipt is not None:
                validate_sha256(receipt, field_name="orphan_receipt_sha256")
            return {
                "participant_id": participant.participant_id,
                "reconciled": receipt is not None,
                "orphan_receipt_sha256": receipt,
            }

    def require_current_integrity(
        self,
        project_root: str | Path,
        manifest: ProductProjectManifest,
    ) -> None:
        """Fail closed unless the manifest and every bound child are current."""
        root = _project_root(project_root)
        if self.recovery_status(root)["required"]:
            raise ProductError(
                "ERR_PROJECT_SAVE_RECOVERY_REQUIRED",
                "Complete or roll back the interrupted Project save first",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        live = ProductProjectManifestStore.load(root)
        if live.project_manifest_sha256 != manifest.project_manifest_sha256:
            raise ProductError(
                "ERR_PROJECT_SAVE_REVISION_CONFLICT",
                "Project manifest changed during integrity validation",
                ProductErrorCategory.STATE,
            )
        self._validate_target_children(root, manifest)

    def recover_complete(
        self,
        project_root: str | Path,
        *,
        transaction_id: str,
        participant: ProjectSaveParticipant | None = None,
        commit_guard: Callable[[], ContextManager[None]] | None = None,
    ) -> ProductProjectManifest:
        root = _project_root(project_root)
        lock_target = _manifest_path(root, create_control_dir=True)
        with _exclusive_project_lock(lock_target):
            guard = nullcontext() if commit_guard is None else commit_guard()
            with guard:
                journal = self._require_recovery(root, transaction_id)
                self._require_participant(journal, participant)
                if (
                    journal.participant_result is not None
                    and journal.participant_result.outcome is not ProjectSaveParticipantOutcome.COMPLETE
                ):
                    raise ProductError(
                        "ERR_PROJECT_SAVE_PARTICIPANT_OUTCOME_CONFLICT",
                        "A rolled-back participant transaction cannot be completed",
                        ProductErrorCategory.STATE,
                    )
                current = ProductProjectManifestStore.load(root)
                if current.project_manifest_sha256 == journal.target_manifest.project_manifest_sha256:
                    self._validate_target_children(root, journal.target_manifest)
                    committing = journal
                    result_manifest = current
                else:
                    if current.project_manifest_sha256 != journal.source_manifest_sha256:
                        raise ProductError("ERR_PROJECT_SAVE_RECOVERY_MANIFEST_CONFLICT", "Current manifest is neither the source nor target transaction revision", ProductErrorCategory.STATE)
                    committing = journal.transition(ProjectSaveState.COMMITTING)
                    ProjectSaveJournalStore.save(root, committing)
                    committing = self._commit_children(root, committing)
                    ProductProjectManifestStore._save_unlocked(
                        root,
                        committing.target_manifest,
                        expected_previous_manifest_sha256=committing.source_manifest_sha256,
                    )
                    result_manifest = committing.target_manifest
                if participant is not None:
                    result = participant.reconcile_locked(
                        root,
                        transaction_id,
                        committing.participant_plan,
                        committing.participant_prepared_receipt_sha256,
                        ProjectSaveParticipantOutcome.COMPLETE,
                    )
                    self._validate_participant_result(
                        committing,
                        result,
                        ProjectSaveParticipantOutcome.COMPLETE,
                    )
                    committing = committing.record_participant_result(result)
                    ProjectSaveJournalStore.save(root, committing)
                final = committing.transition(ProjectSaveState.COMMITTED)
                ProjectSaveJournalStore.save(root, final)
                return result_manifest

    def recover_rollback(
        self,
        project_root: str | Path,
        *,
        transaction_id: str,
        participant: ProjectSaveParticipant | None = None,
        commit_guard: Callable[[], ContextManager[None]] | None = None,
    ) -> ProductProjectManifest:
        root = _project_root(project_root)
        lock_target = _manifest_path(root, create_control_dir=True)
        with _exclusive_project_lock(lock_target):
            guard = nullcontext() if commit_guard is None else commit_guard()
            with guard:
                return self._recover_rollback_locked(root, transaction_id, participant)

    def _recover_rollback_locked(
        self,
        root: Path,
        transaction_id: str,
        participant: ProjectSaveParticipant | None,
    ) -> ProductProjectManifest:
        journal = self._require_recovery(root, transaction_id)
        self._require_participant(journal, participant)
        if (
            journal.participant_result is not None
            and journal.participant_result.outcome is not ProjectSaveParticipantOutcome.ROLLBACK
        ):
            raise ProductError(
                "ERR_PROJECT_SAVE_PARTICIPANT_OUTCOME_CONFLICT",
                "A completed participant transaction cannot be rolled back",
                ProductErrorCategory.STATE,
            )
        current = ProductProjectManifestStore.load(root)
        if current.project_manifest_sha256 == journal.target_manifest.project_manifest_sha256:
            raise ProductError("ERR_PROJECT_SAVE_ROLLBACK_AFTER_MANIFEST", "Committed manifest cannot be rolled back without a new restore transaction", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        if current.project_manifest_sha256 != journal.source_manifest_sha256:
            raise ProductError("ERR_PROJECT_SAVE_RECOVERY_MANIFEST_CONFLICT", "Current manifest changed outside the interrupted transaction", ProductErrorCategory.STATE)
        for entry in reversed(journal.entries):
            target = self._safe_child_target(root, entry.relative_path, create_parent=True)
            if entry.before_sha256 is None:
                if target.exists():
                    if target.is_symlink() or sha256_file_exact(target) != entry.target_sha256:
                        raise ProductError("ERR_PROJECT_SAVE_ROLLBACK_CHILD_CONFLICT", "New child changed before rollback", ProductErrorCategory.STATE, details={"relative_path": entry.relative_path})
                    target.unlink()
            else:
                backup = self._internal_path(root, entry.backup_relative_path)
                if not backup.is_file() or sha256_file_exact(backup) != entry.before_sha256:
                    raise ProductError("ERR_PROJECT_SAVE_ROLLBACK_BACKUP_INVALID", "Project save backup is missing or changed", ProductErrorCategory.DATA_INTEGRITY, details={"relative_path": entry.relative_path})
                if target.exists() and not target.is_symlink():
                    actual = sha256_file_exact(target)
                    if actual not in {entry.before_sha256, entry.target_sha256}:
                        raise ProductError("ERR_PROJECT_SAVE_ROLLBACK_CHILD_CONFLICT", "Child changed outside the interrupted transaction", ProductErrorCategory.STATE, details={"relative_path": entry.relative_path})
                self._replace_from_stage(backup, target)
        if participant is not None:
            result = participant.reconcile_locked(
                root,
                transaction_id,
                journal.participant_plan,
                journal.participant_prepared_receipt_sha256,
                ProjectSaveParticipantOutcome.ROLLBACK,
            )
            self._validate_participant_result(
                journal,
                result,
                ProjectSaveParticipantOutcome.ROLLBACK,
            )
            journal = journal.record_participant_result(result)
            ProjectSaveJournalStore.save(root, journal)
        final = journal.transition(ProjectSaveState.ABANDONED)
        ProjectSaveJournalStore.save(root, final)
        return current

    @staticmethod
    def _validate_participant(
        participant: ProjectSaveParticipant,
        plan: ProjectSaveParticipantPlan,
        current: ProductProjectManifest,
        target: ProductProjectManifest,
    ) -> None:
        if not isinstance(plan, ProjectSaveParticipantPlan):
            raise ProductError(
                "ERR_PROJECT_SAVE_PARTICIPANT_PLAN_INVALID",
                "Project save participant plan is invalid",
                ProductErrorCategory.INTERNAL,
            )
        if (
            participant.participant_id != plan.participant_id
            or participant.participant_version != plan.participant_version
            or plan.project_id != current.project_id
            or plan.source_manifest_sha256 != current.project_manifest_sha256
            or plan.target_manifest_sha256 != target.project_manifest_sha256
        ):
            raise ProductError(
                "ERR_PROJECT_SAVE_PARTICIPANT_SCOPE_CONFLICT",
                "Project save participant crosses the save operation",
                ProductErrorCategory.SECURITY,
            )

    @staticmethod
    def _require_participant(
        journal: ProjectSaveJournal,
        participant: ProjectSaveParticipant | None,
    ) -> None:
        plan = journal.participant_plan
        if plan is None:
            if participant is not None:
                raise ProductError(
                    "ERR_PROJECT_SAVE_PARTICIPANT_UNEXPECTED",
                    "A v1.0 Project save cannot use a recovery participant",
                    ProductErrorCategory.VALIDATION,
                )
            return
        if (
            participant is None
            or participant.participant_id != plan.participant_id
            or participant.participant_version != plan.participant_version
        ):
            raise ProductError(
                "ERR_PROJECT_SAVE_PARTICIPANT_REQUIRED",
                "The exact Project save participant is required for recovery",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={"participant_id": plan.participant_id},
            )

    @staticmethod
    def _validate_participant_result(
        journal: ProjectSaveJournal,
        result: ProjectSaveParticipantResult,
        outcome: ProjectSaveParticipantOutcome,
    ) -> None:
        plan = journal.participant_plan
        if (
            not isinstance(result, ProjectSaveParticipantResult)
            or plan is None
            or result.participant_id != plan.participant_id
            or result.binding_sha256 != plan.binding_sha256
            or result.transaction_id != journal.transaction_id
            or result.outcome is not outcome
            or result.result_content_sha256
            != (
                plan.target_content_sha256
                if outcome is ProjectSaveParticipantOutcome.COMPLETE
                else plan.source_content_sha256
            )
        ):
            raise ProductError(
                "ERR_PROJECT_SAVE_PARTICIPANT_RESULT_INVALID",
                "Project save participant returned an invalid result",
                ProductErrorCategory.DATA_INTEGRITY,
            )

    @staticmethod
    def _journal_matches(root: Path, transaction_id: str) -> bool:
        path = ProjectSaveJournalStore.path(root)
        if not path.exists():
            return False
        try:
            return ProjectSaveJournalStore.load(root).transaction_id == transaction_id
        except ProductError:
            return True

    @staticmethod
    def _require_manifest_transition(current: ProductProjectManifest, target: ProductProjectManifest, expected: str) -> None:
        if current.project_manifest_sha256 != expected:
            raise ProductError("ERR_PROJECT_SAVE_REVISION_CONFLICT", "Project manifest changed before save", ProductErrorCategory.STATE)
        if current.project_id != target.project_id or current.created_at != target.created_at:
            raise ProductError("ERR_PROJECT_SAVE_IDENTITY_CONFLICT", "Project identity cannot change", ProductErrorCategory.STATE)
        if target.project_revision != current.project_revision + 1:
            raise ProductError("ERR_PROJECT_SAVE_REVISION_INVALID", "Project revision must advance exactly once", ProductErrorCategory.STATE)
        current_identities = {item.identity for item in current.child_bindings}
        target_identities = {item.identity for item in target.child_bindings}
        if not current_identities <= target_identities:
            raise ProductError("ERR_PROJECT_SAVE_BINDING_REMOVAL_REQUIRES_MIGRATION", "Removing child bindings requires an explicit migration plan", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)

    def _validate_documents(
        self,
        root: Path,
        current: ProductProjectManifest,
        target: ProductProjectManifest,
        child_documents: Mapping[str, bytes],
    ) -> dict[str, bytes]:
        normalized: dict[str, bytes] = {}
        target_by_path = {item.relative_path: item for item in target.child_bindings}
        for path, data in child_documents.items():
            canonical = validate_project_relative_path(path)
            if canonical not in target_by_path:
                raise ProductError("ERR_PROJECT_SAVE_UNBOUND_CHILD", "Child document is not bound by the target manifest", ProductErrorCategory.AUTHORIZATION, details={"relative_path": canonical})
            if not isinstance(data, bytes) or len(data) > _MAX_CHILD_BYTES:
                raise ProductError("ERR_PROJECT_SAVE_CHILD_SIZE", "Child document bytes are invalid or exceed the bound", ProductErrorCategory.RESOURCE_EXHAUSTED, details={"relative_path": canonical})
            if sha256_bytes(data) != target_by_path[canonical].content_sha256:
                raise ProductError("ERR_PROJECT_SAVE_CHILD_CHECKSUM", "Child document checksum does not match the target binding", ProductErrorCategory.DATA_INTEGRITY, details={"relative_path": canonical})
            normalized[canonical] = data
        if sum(len(data) for data in normalized.values()) > _MAX_TOTAL_STAGED_BYTES:
            raise ProductError("ERR_PROJECT_SAVE_TOTAL_SIZE", "Staged Project save exceeds the bounded total", ProductErrorCategory.RESOURCE_EXHAUSTED)
        for binding in target.child_bindings:
            if binding.relative_path in normalized:
                continue
            target_path = self._safe_child_target(root, binding.relative_path)
            if not target_path.exists():
                if binding.required:
                    raise ProductError("ERR_PROJECT_SAVE_REQUIRED_CHILD_MISSING", "Required target child is missing", ProductErrorCategory.DATA_INTEGRITY, details={"relative_path": binding.relative_path})
                continue
            if target_path.is_symlink() or not target_path.is_file() or sha256_file_exact(target_path) != binding.content_sha256:
                raise ProductError("ERR_PROJECT_SAVE_UNSTAGED_CHILD_CONFLICT", "Unstaged child does not match the target binding", ProductErrorCategory.STATE, details={"relative_path": binding.relative_path})
        for binding in current.child_bindings:
            target_path = self._safe_child_target(root, binding.relative_path)
            if not target_path.exists():
                if binding.required:
                    raise ProductError("ERR_PROJECT_SAVE_SOURCE_CHILD_MISSING", "Required source child is missing", ProductErrorCategory.DATA_INTEGRITY, details={"relative_path": binding.relative_path})
                continue
            if target_path.is_symlink() or not target_path.is_file() or sha256_file_exact(target_path) != binding.content_sha256:
                raise ProductError("ERR_PROJECT_SAVE_SOURCE_CHILD_CONFLICT", "Source child changed outside the current manifest", ProductErrorCategory.STATE, details={"relative_path": binding.relative_path})
        return normalized

    @staticmethod
    def _transaction_id(
        current: ProductProjectManifest,
        target: ProductProjectManifest,
        documents: Mapping[str, bytes],
        *,
        participant_binding_sha256: str | None = None,
    ) -> str:
        return _save_transaction_id(
            current.project_id,
            current.project_manifest_sha256,
            target.project_manifest_sha256,
            {path: sha256_bytes(data) for path, data in documents.items()},
            participant_binding_sha256=participant_binding_sha256,
        )

    def _prepare_entries(
        self,
        root: Path,
        transaction_id: str,
        current: ProductProjectManifest,
        target: ProductProjectManifest,
        documents: Mapping[str, bytes],
    ) -> tuple[ProjectSaveEntry, ...]:
        current_by_path = {item.relative_path: item for item in current.child_bindings}
        target_by_path = {item.relative_path: item for item in target.child_bindings}
        entries = []
        for path in sorted(documents):
            before = current_by_path.get(path)
            entries.append(ProjectSaveEntry(
                relative_path=path,
                before_sha256=None if before is None else before.content_sha256,
                target_sha256=target_by_path[path].content_sha256,
                staged_relative_path=f"staging/{transaction_id}/new/{path}",
                backup_relative_path=None if before is None else f"staging/{transaction_id}/backup/{path}",
            ))
        return tuple(entries)

    def _stage_documents(self, root: Path, journal: ProjectSaveJournal, documents: Mapping[str, bytes]) -> None:
        for entry in journal.entries:
            staged = self._internal_path(root, entry.staged_relative_path, create_parent=True)
            self._write_new_bytes(staged, documents[entry.relative_path])
            if entry.backup_relative_path is not None:
                source = self._safe_child_target(root, entry.relative_path)
                backup = self._internal_path(root, entry.backup_relative_path, create_parent=True)
                self._copy_new_file(source, backup)
        self._inject("after_staging_files", root)

    def _validate_staging(self, root: Path, journal: ProjectSaveJournal) -> None:
        for entry in journal.entries:
            staged = self._internal_path(root, entry.staged_relative_path)
            if not staged.is_file() or sha256_file_exact(staged) != entry.target_sha256:
                raise ProductError("ERR_PROJECT_SAVE_STAGING_INVALID", "Staged child is missing or changed", ProductErrorCategory.DATA_INTEGRITY, details={"relative_path": entry.relative_path})
            if entry.backup_relative_path is not None:
                backup = self._internal_path(root, entry.backup_relative_path)
                if not backup.is_file() or sha256_file_exact(backup) != entry.before_sha256:
                    raise ProductError("ERR_PROJECT_SAVE_BACKUP_INVALID", "Staged backup is missing or changed", ProductErrorCategory.DATA_INTEGRITY, details={"relative_path": entry.relative_path})

    def _revalidate_source(self, root: Path, current: ProductProjectManifest, journal: ProjectSaveJournal) -> None:
        live = ProductProjectManifestStore.load(root)
        if live.project_manifest_sha256 != current.project_manifest_sha256:
            raise ProductError("ERR_PROJECT_SAVE_REVISION_CONFLICT", "Project manifest changed before commit", ProductErrorCategory.STATE)
        for entry in journal.entries:
            target = self._safe_child_target(root, entry.relative_path)
            if entry.before_sha256 is None:
                if target.exists():
                    raise ProductError("ERR_PROJECT_SAVE_NEW_CHILD_CONFLICT", "New child appeared before commit", ProductErrorCategory.STATE, details={"relative_path": entry.relative_path})
            elif not target.is_file() or target.is_symlink() or sha256_file_exact(target) != entry.before_sha256:
                raise ProductError("ERR_PROJECT_SAVE_SOURCE_CHILD_CONFLICT", "Source child changed before commit", ProductErrorCategory.STATE, details={"relative_path": entry.relative_path})

    def _validate_target_children(self, root: Path, manifest: ProductProjectManifest) -> None:
        for binding in manifest.child_bindings:
            target = self._safe_child_target(root, binding.relative_path)
            if not target.exists():
                if binding.required:
                    raise ProductError("ERR_PROJECT_SAVE_RECOVERY_TARGET_MISSING", "Committed manifest has a missing required child", ProductErrorCategory.DATA_INTEGRITY, details={"relative_path": binding.relative_path})
                continue
            if target.is_symlink() or not target.is_file() or sha256_file_exact(target) != binding.content_sha256:
                raise ProductError("ERR_PROJECT_SAVE_RECOVERY_TARGET_CONFLICT", "Committed manifest child is missing or changed", ProductErrorCategory.DATA_INTEGRITY, details={"relative_path": binding.relative_path})

    def _commit_children(self, root: Path, journal: ProjectSaveJournal) -> ProjectSaveJournal:
        current = journal
        entries = list(current.entries)
        for index, entry in enumerate(entries):
            target = self._safe_child_target(root, entry.relative_path, create_parent=True)
            if target.exists() and not target.is_symlink() and sha256_file_exact(target) == entry.target_sha256:
                entries[index] = replace(entry, committed=True)
            else:
                if target.exists():
                    if target.is_symlink() or entry.before_sha256 is None or sha256_file_exact(target) != entry.before_sha256:
                        raise ProductError("ERR_PROJECT_SAVE_CHILD_COMMIT_CONFLICT", "Child changed before commit/recovery", ProductErrorCategory.STATE, details={"relative_path": entry.relative_path})
                staged = self._internal_path(root, entry.staged_relative_path)
                if not staged.is_file() or sha256_file_exact(staged) != entry.target_sha256:
                    raise ProductError("ERR_PROJECT_SAVE_STAGING_INVALID", "Staged child is unavailable for commit", ProductErrorCategory.DATA_INTEGRITY, details={"relative_path": entry.relative_path})
                self._replace_from_stage(staged, target)
                entries[index] = replace(entry, committed=True)
            current = current.transition(ProjectSaveState.COMMITTING, entries=tuple(entries))
            ProjectSaveJournalStore.save(root, current)
            self._inject("after_child_replace", root)
        return current

    @staticmethod
    def _replace_from_stage(source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, raw = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        temporary = Path(raw)
        try:
            with source.open("rb") as source_handle, os.fdopen(fd, "wb") as target_handle:
                shutil.copyfileobj(source_handle, target_handle, length=1024 * 1024)
                target_handle.flush()
                os.fsync(target_handle.fileno())
            os.replace(temporary, target)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    @staticmethod
    def _write_new_bytes(target: Path, data: bytes) -> None:
        expected = sha256_bytes(data)
        if target.exists() or target.is_symlink():
            if not target.is_symlink() and target.is_file() and sha256_file_exact(target) == expected:
                return
            raise ProductError("ERR_PROJECT_SAVE_STAGING_COLLISION", "Staging target already exists with different content", ProductErrorCategory.STATE)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())

    @staticmethod
    def _copy_new_file(source: Path, target: Path) -> None:
        expected = sha256_file_exact(source)
        if target.exists() or target.is_symlink():
            if not target.is_symlink() and target.is_file() and sha256_file_exact(target) == expected:
                return
            raise ProductError("ERR_PROJECT_SAVE_STAGING_COLLISION", "Backup target already exists with different content", ProductErrorCategory.STATE)
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as source_handle, target.open("xb") as target_handle:
            shutil.copyfileobj(source_handle, target_handle, length=1024 * 1024)
            target_handle.flush()
            os.fsync(target_handle.fileno())

    @staticmethod
    def _safe_child_target(root: Path, relative_path: str, *, create_parent: bool = False) -> Path:
        validate_project_relative_path(relative_path)
        target = root.joinpath(*relative_path.split("/"))
        cursor = root
        for part in relative_path.split("/")[:-1]:
            cursor = cursor / part
            if cursor.exists() and (cursor.is_symlink() or not cursor.is_dir()):
                raise ProductError("ERR_PROJECT_SAVE_CHILD_PATH_INVALID", "Child parent path is not a regular directory", ProductErrorCategory.SECURITY, details={"relative_path": relative_path})
            if create_parent and not cursor.exists():
                cursor.mkdir()
        if target.is_symlink():
            raise ProductError("ERR_PROJECT_SAVE_CHILD_PATH_INVALID", "Child target must not be a symlink", ProductErrorCategory.SECURITY, details={"relative_path": relative_path})
        resolved_parent = target.parent.resolve(strict=True)
        if not resolved_parent.is_relative_to(root):
            raise ProductError("ERR_PROJECT_SAVE_CHILD_PATH_INVALID", "Child target escapes the Project root", ProductErrorCategory.SECURITY, details={"relative_path": relative_path})
        return target

    @staticmethod
    def _internal_path(root: Path, relative_path: str | None, *, create_parent: bool = False) -> Path:
        if relative_path is None:
            raise ProductError("ERR_PROJECT_SAVE_INTERNAL_PATH_INVALID", "Required internal Project path is absent", ProductErrorCategory.INTERNAL)
        validate_project_relative_path(relative_path)
        target = root / ".bai-project" / Path(*relative_path.split("/"))
        control = root / ".bai-project"
        if control.is_symlink() or not control.is_dir():
            raise ProductError("ERR_PROJECT_FORMAT_CONTROL_DIR_INVALID", "Project control directory is invalid", ProductErrorCategory.SECURITY)
        cursor = control
        for part in relative_path.split("/")[:-1]:
            cursor = cursor / part
            if cursor.exists() and (cursor.is_symlink() or not cursor.is_dir()):
                raise ProductError("ERR_PROJECT_SAVE_INTERNAL_PATH_INVALID", "Internal Project path is invalid", ProductErrorCategory.SECURITY)
            if create_parent and not cursor.exists():
                cursor.mkdir()
        if target.is_symlink() or not target.parent.resolve(strict=True).is_relative_to(control.resolve(strict=True)):
            raise ProductError("ERR_PROJECT_SAVE_INTERNAL_PATH_INVALID", "Internal Project path escapes the control directory", ProductErrorCategory.SECURITY)
        return target

    @staticmethod
    def _require_no_pending_recovery(root: Path) -> None:
        path = ProjectSaveJournalStore.path(root)
        if path.exists():
            journal = ProjectSaveJournalStore.load(root)
            if journal.state not in {ProjectSaveState.COMMITTED, ProjectSaveState.ABANDONED}:
                raise ProductError("ERR_PROJECT_SAVE_RECOVERY_REQUIRED", "An interrupted Project save must be recovered before a new save", ProductErrorCategory.HUMAN_REVIEW_REQUIRED, details={"transaction_id": journal.transaction_id, "state": journal.state.value})

    @staticmethod
    def _require_recovery(root: Path, transaction_id: str) -> ProjectSaveJournal:
        journal = ProjectSaveJournalStore.load(root)
        if journal.transaction_id != transaction_id:
            raise ProductError("ERR_PROJECT_SAVE_RECOVERY_IDENTITY", "Recovery transaction identity does not match", ProductErrorCategory.AUTHORIZATION)
        if journal.state in {ProjectSaveState.COMMITTED, ProjectSaveState.ABANDONED}:
            raise ProductError("ERR_PROJECT_SAVE_RECOVERY_NOT_REQUIRED", "Project save transaction is already terminal", ProductErrorCategory.STATE)
        return journal

    @staticmethod
    def _mark_recovery_required(root: Path, journal: ProjectSaveJournal, exc: Exception) -> None:
        if journal.state in {ProjectSaveState.COMMITTED, ProjectSaveState.ABANDONED}:
            try:
                durable = ProjectSaveJournalStore.load(root)
            except ProductError:
                return
            if (
                durable.transaction_id != journal.transaction_id
                or durable.state in {ProjectSaveState.COMMITTED, ProjectSaveState.ABANDONED}
            ):
                return
            journal = durable
        code = exc.code if isinstance(exc, ProductError) else "ERR_PROJECT_SAVE_INTERRUPTED"
        try:
            recovery = journal.transition(ProjectSaveState.RECOVERY_REQUIRED, last_error_code=code)
        except ValueError:
            return
        ProjectSaveJournalStore.save(root, recovery)

    def _inject(self, stage: str, root: Path) -> None:
        if self.failure_injector is not None:
            self.failure_injector(stage, root)


def _validate_utc_timestamp(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{field_name} must be a UTC ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid ISO-8601 timestamp") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{field_name} must be UTC")


def _save_transaction_id(
    project_id: str,
    source_manifest_sha256: str,
    target_manifest_sha256: str,
    document_hashes: Mapping[str, str],
    *,
    participant_binding_sha256: str | None = None,
) -> str:
    identity = {
        "project_id": project_id,
        "source_manifest_sha256": source_manifest_sha256,
        "target_manifest_sha256": target_manifest_sha256,
        "documents": dict(sorted(document_hashes.items())),
    }
    if participant_binding_sha256 is not None:
        validate_sha256(participant_binding_sha256, field_name="participant_binding_sha256")
        identity["participant_binding_sha256"] = participant_binding_sha256
    return "save-" + sha256_bytes(canonical_json_bytes(identity)).split(":", 1)[1]
