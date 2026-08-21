"""Project-scoped prepare/apply boundary for TASK-044 Timeline edits."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import secrets
from threading import Lock
from typing import Any, Callable, ContextManager, Iterable, Mapping

from .atomic import AtomicJsonWriter
from .errors import ProductError, ProductErrorCategory
from .interactive_timeline import InteractiveTimeline, TimelineTrack, timeline_track_category
from .interactive_timeline_edit import (
    SnapAnchor,
    TimelineEditCommand,
    TimelineEditHistory,
    TimelineEditKind,
    TimelineEditProjector,
    TimelineEditRevision,
    TimelineSnapService,
)
from .interactive_timeline_store import (
    FORMAT_ID,
    FORMAT_VERSION,
    FORMAT_VERSION_V1_1,
    RELATIVE_PATH,
    SUPPORTED_FORMAT_VERSIONS,
    TimelineEditSnapshotStore,
)
from .product_project import ProductProjectManifest, ProjectChildBinding
from .product_project_store import ProductProjectManifestStore
from .project_history import (
    ProjectCommandAction, ProjectCommandHistory, ProjectCommandHistoryStore,
    parse_project_command_history,
)
from .project_save import (
    ProductProjectSaveCoordinator,
    ProjectSaveJournalStore,
    ProjectSaveParticipantOutcome,
    ProjectSaveParticipantPlan,
    ProjectSaveParticipantResult,
)
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso, validate_sha256
from .task044_edit_persistence_receipt import Task044EditPersistenceReceipt

TokenFactory = Callable[[], str]
CommitGuardFactory = Callable[[], ContextManager[None]]
PlacementGuardResolver = Callable[[TimelineEditCommand], CommitGuardFactory]
_MAX_PENDING_CONFIRMATIONS = 256
_MAX_HISTORY_RECOVERY_BYTES = 8 * 1024 * 1024
_HISTORY_PARTICIPANT_ID = "TASK044/TIMELINE-HISTORY"
_HISTORY_PARTICIPANT_VERSION = "1.0.0"
_HISTORY_RECOVERY_VERSION = "1.1.0"


@dataclass(slots=True)
class _Confirmation:
    confirmation_id: str
    expected_manifest_sha256: str
    expected_history_sha256: str | None
    base_timeline_sha256: str
    command: TimelineEditCommand
    history_action: str
    commit_guard: CommitGuardFactory | None = None


class _TimelineHistoryParticipant:
    participant_id = _HISTORY_PARTICIPANT_ID
    participant_version = _HISTORY_PARTICIPANT_VERSION

    def __init__(
        self,
        *,
        project_id: str,
        recovery_path: Path,
        expected_history_sha256: str | None = None,
        target_history: ProjectCommandHistory | None = None,
    ) -> None:
        self.project_id = project_id
        self.recovery_path = recovery_path
        self.expected_history_sha256 = expected_history_sha256
        self.target_history = target_history

    @staticmethod
    def _body(
        *,
        project_id: str,
        transaction_id: str,
        plan: ProjectSaveParticipantPlan,
        expected_history_sha256: str | None,
        target_history: ProjectCommandHistory,
    ) -> dict[str, object]:
        return {
            "recovery_version": _HISTORY_RECOVERY_VERSION,
            "participant_id": _HISTORY_PARTICIPANT_ID,
            "participant_version": _HISTORY_PARTICIPANT_VERSION,
            "project_id": project_id,
            "transaction_id": transaction_id,
            "binding_sha256": plan.binding_sha256,
            "source_manifest_sha256": plan.source_manifest_sha256,
            "target_manifest_sha256": plan.target_manifest_sha256,
            "expected_history_sha256": expected_history_sha256,
            "target_history": target_history.to_dict(),
        }

    @classmethod
    def parse_recovery(cls, document: Mapping[str, Any]) -> dict[str, object]:
        fields = {
            "recovery_version", "participant_id", "participant_version",
            "project_id", "transaction_id", "binding_sha256",
            "source_manifest_sha256", "target_manifest_sha256",
            "expected_history_sha256", "target_history", "recovery_sha256",
        }
        if not isinstance(document, Mapping) or set(document) != fields:
            raise ValueError("Timeline participant recovery fields are not exact")
        if (
            document["recovery_version"] != _HISTORY_RECOVERY_VERSION
            or document["participant_id"] != _HISTORY_PARTICIPANT_ID
            or document["participant_version"] != _HISTORY_PARTICIPANT_VERSION
        ):
            raise ValueError("Timeline participant recovery identity is invalid")
        if (
            not isinstance(document["transaction_id"], str)
            or re.fullmatch(r"save-[0-9a-f]{64}", document["transaction_id"]) is None
        ):
            raise ValueError("Timeline participant transaction identity is invalid")
        for name in (
            "binding_sha256", "source_manifest_sha256",
            "target_manifest_sha256", "recovery_sha256",
        ):
            validate_sha256(document[name], field_name=name)
        if document["expected_history_sha256"] is not None:
            validate_sha256(
                document["expected_history_sha256"],
                field_name="expected_history_sha256",
            )
        target_history = parse_project_command_history(document["target_history"])
        if target_history.project_id != document["project_id"]:
            raise ValueError("Timeline participant history belongs to another Project")
        body = {key: value for key, value in document.items() if key != "recovery_sha256"}
        if document["recovery_sha256"] != sha256_bytes(canonical_json_bytes(body)):
            raise ValueError("Timeline participant recovery checksum is invalid")
        return {**document, "target_history_object": target_history}

    def _load_recovery(self) -> dict[str, object]:
        path = self.recovery_path
        if (
            path.is_symlink()
            or not path.is_file()
            or not 0 < path.stat().st_size <= _MAX_HISTORY_RECOVERY_BYTES
        ):
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_INVALID",
                "Timeline participant recovery is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        try:
            return self.parse_recovery(json.loads(path.read_text(encoding="utf-8")))
        except ProductError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_INVALID",
                "Timeline participant recovery is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc

    def _require_scope(
        self,
        recovery: Mapping[str, object],
        transaction_id: str,
        plan: ProjectSaveParticipantPlan,
        prepared_receipt_sha256: str,
    ) -> ProjectCommandHistory:
        if (
            recovery["project_id"] != self.project_id
            or recovery["transaction_id"] != transaction_id
            or recovery["binding_sha256"] != plan.binding_sha256
            or recovery["source_manifest_sha256"] != plan.source_manifest_sha256
            or recovery["target_manifest_sha256"] != plan.target_manifest_sha256
            or recovery["recovery_sha256"] != prepared_receipt_sha256
        ):
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_CONFLICT",
                "Timeline participant recovery differs from the Project transaction",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        history = recovery["target_history_object"]
        if (
            not isinstance(history, ProjectCommandHistory)
            or history.history_sha256 != plan.target_content_sha256
            or recovery["expected_history_sha256"] != plan.source_content_sha256
        ):
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_CONFLICT",
                "Timeline participant history differs from its immutable plan",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return history

    @staticmethod
    def _current_history(project_root: Path, project_id: str) -> tuple[ProjectCommandHistory | None, str | None]:
        path = ProjectCommandHistoryStore.path(project_root)
        if path.is_symlink():
            raise ProductError(
                "ERR_PROJECT_HISTORY_FILE_INVALID",
                "Project command history file is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if not path.exists():
            return None, None
        history = ProjectCommandHistoryStore.load(project_root)
        if history.project_id != project_id:
            raise ProductError(
                "ERR_PROJECT_HISTORY_IDENTITY_CONFLICT",
                "Project history belongs to another Project",
                ProductErrorCategory.SECURITY,
            )
        return history, history.history_sha256

    def plan_locked(
        self,
        project_root: Path,
        source_manifest: ProductProjectManifest,
        target_manifest: ProductProjectManifest,
    ) -> ProjectSaveParticipantPlan:
        if self.target_history is None:
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_PARTICIPANT_UNPREPARED",
                "Timeline history participant lacks its target history",
                ProductErrorCategory.INTERNAL,
            )
        _history, current_sha = self._current_history(project_root, self.project_id)
        if current_sha != self.expected_history_sha256:
            raise ProductError(
                "ERR_PROJECT_HISTORY_CAS_CONFLICT",
                "Project history changed before Project save",
                ProductErrorCategory.STATE,
            )
        return ProjectSaveParticipantPlan.create(
            participant_id=self.participant_id,
            participant_version=self.participant_version,
            project_id=self.project_id,
            source_manifest_sha256=source_manifest.project_manifest_sha256,
            target_manifest_sha256=target_manifest.project_manifest_sha256,
            source_content_sha256=current_sha,
            target_content_sha256=self.target_history.history_sha256,
        )

    def prepare_locked(
        self,
        project_root: Path,
        transaction_id: str,
        plan: ProjectSaveParticipantPlan,
    ) -> str:
        if self.target_history is None:
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_PARTICIPANT_UNPREPARED",
                "Timeline history participant lacks its target history",
                ProductErrorCategory.INTERNAL,
            )
        body = self._body(
            project_id=self.project_id,
            transaction_id=transaction_id,
            plan=plan,
            expected_history_sha256=self.expected_history_sha256,
            target_history=self.target_history,
        )
        document = {**body, "recovery_sha256": sha256_bytes(canonical_json_bytes(body))}
        if self.recovery_path.exists():
            current = self._load_recovery()
            if current["recovery_sha256"] != document["recovery_sha256"]:
                raise ProductError(
                    "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_CONFLICT",
                    "Another Timeline history recovery already exists",
                    ProductErrorCategory.STATE,
                )
            return str(document["recovery_sha256"])
        AtomicJsonWriter.write(
            self.recovery_path,
            document,
            validator=self.parse_recovery,
        )
        return str(document["recovery_sha256"])

    def _delete_exact(self, expected_receipt_sha256: str) -> None:
        current = self._load_recovery()
        if current["recovery_sha256"] != expected_receipt_sha256:
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_CONFLICT",
                "Timeline history recovery changed before cleanup",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        self.recovery_path.unlink()

    def reconcile_locked(
        self,
        project_root: Path,
        transaction_id: str,
        plan: ProjectSaveParticipantPlan,
        prepared_receipt_sha256: str,
        outcome: ProjectSaveParticipantOutcome,
    ) -> ProjectSaveParticipantResult:
        _current, current_sha = self._current_history(project_root, self.project_id)
        if not self.recovery_path.exists():
            expected_sha = (
                plan.target_content_sha256
                if outcome is ProjectSaveParticipantOutcome.COMPLETE
                else plan.source_content_sha256
            )
            if current_sha != expected_sha:
                raise ProductError(
                    "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_CONFLICT",
                    "Timeline participant recovery is missing before reconciliation",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            return ProjectSaveParticipantResult.create(
                participant_id=self.participant_id,
                binding_sha256=plan.binding_sha256,
                transaction_id=transaction_id,
                outcome=outcome,
                result_content_sha256=current_sha,
            )
        recovery = self._load_recovery()
        target = self._require_scope(
            recovery, transaction_id, plan, prepared_receipt_sha256,
        )
        if outcome is ProjectSaveParticipantOutcome.COMPLETE:
            if current_sha != target.history_sha256:
                if current_sha != plan.source_content_sha256:
                    raise ProductError(
                        "ERR_PROJECT_HISTORY_CAS_CONFLICT",
                        "Project history changed before participant completion",
                        ProductErrorCategory.STATE,
                    )
                ProjectCommandHistoryStore._save_unlocked(
                    project_root,
                    target,
                    expected_previous_history_sha256=plan.source_content_sha256,
                )
            result_sha = target.history_sha256
        else:
            if current_sha != plan.source_content_sha256:
                raise ProductError(
                    "ERR_PROJECT_HISTORY_CAS_CONFLICT",
                    "Project history changed before participant rollback",
                    ProductErrorCategory.STATE,
                )
            result_sha = current_sha
        self._delete_exact(prepared_receipt_sha256)
        return ProjectSaveParticipantResult.create(
            participant_id=self.participant_id,
            binding_sha256=plan.binding_sha256,
            transaction_id=transaction_id,
            outcome=outcome,
            result_content_sha256=result_sha,
        )

    def abort_prejournal_locked(
        self,
        project_root: Path,
        transaction_id: str,
        plan: ProjectSaveParticipantPlan,
        prepared_receipt_sha256: str,
    ) -> None:
        recovery = self._load_recovery()
        self._require_scope(recovery, transaction_id, plan, prepared_receipt_sha256)
        self._delete_exact(prepared_receipt_sha256)

    def reconcile_orphan_locked(
        self,
        project_root: Path,
        current_manifest: ProductProjectManifest,
    ) -> str | None:
        if not self.recovery_path.exists():
            return None
        recovery = self._load_recovery()
        if recovery["project_id"] != self.project_id:
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_IDENTITY",
                "Timeline history recovery belongs to another Project",
                ProductErrorCategory.SECURITY,
            )
        if current_manifest.project_manifest_sha256 != recovery["source_manifest_sha256"]:
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_CONFLICT",
                "Orphan recovery cannot be removed after Project state changed",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        receipt = str(recovery["recovery_sha256"])
        self._delete_exact(receipt)
        return receipt


class Task044TimelineEditApplication:
    """Adds immutable Timeline revisions; no provider or native mutation occurs."""

    def __init__(self, *, project_root: str | Path, project_id: str,
                 token_factory: TokenFactory | None = None,
                 save_coordinator: ProductProjectSaveCoordinator | None = None,
                 placement_guard_resolver: PlacementGuardResolver | None = None) -> None:
        self.project_root = Path(project_root).resolve(strict=True)
        self.project_id = project_id
        manifest = ProductProjectManifestStore.load(self.project_root)
        if manifest.project_id != project_id:
            raise ProductError("ERR_TIMELINE_EDIT_PROJECT_MISMATCH", "Project identity differs", ProductErrorCategory.SECURITY)
        self._save_coordinator = save_coordinator or ProductProjectSaveCoordinator()
        self._participant = _TimelineHistoryParticipant(
            project_id=project_id,
            recovery_path=ProductProjectManifestStore.path(self.project_root).with_name(
                "timeline-edit-command-recovery.json"
            ),
        )
        self._recover_command_history()
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._placement_guard_resolver = placement_guard_resolver
        self._pending: dict[str, _Confirmation] = {}
        self._pending_lock = Lock()

    @property
    def _history_recovery_path(self) -> Path:
        return ProductProjectManifestStore.path(self.project_root).with_name(
            "timeline-edit-command-recovery.json"
        )

    @staticmethod
    def _parse_history_recovery(document):
        fields = {"recovery_version", "project_id", "source_manifest_sha256",
                  "result_manifest_sha256", "expected_history_sha256", "history",
                  "recovery_sha256"}
        if not isinstance(document, dict) or set(document) != fields:
            raise ValueError("Timeline history recovery fields are not exact")
        claimed = document["recovery_sha256"]
        body = {key: value for key, value in document.items() if key != "recovery_sha256"}
        if claimed != sha256_bytes(canonical_json_bytes(body)) or document["recovery_version"] != "1.0.0":
            raise ValueError("Timeline history recovery checksum is invalid")
        parse_project_command_history(document["history"])
        return document

    def _write_history_recovery(self, *, source_manifest_sha256: str,
                                result_manifest_sha256: str,
                                expected_history_sha256: str | None,
                                history: ProjectCommandHistory) -> None:
        body = {"recovery_version": "1.0.0", "project_id": self.project_id,
                "source_manifest_sha256": source_manifest_sha256,
                "result_manifest_sha256": result_manifest_sha256,
                "expected_history_sha256": expected_history_sha256,
                "history": history.to_dict()}
        AtomicJsonWriter.write(
            self._history_recovery_path,
            {**body, "recovery_sha256": sha256_bytes(canonical_json_bytes(body))},
            validator=self._parse_history_recovery,
        )

    def _recover_command_history(self) -> None:
        path = self._history_recovery_path
        if not path.exists():
            return
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 8 * 1024 * 1024:
            raise ProductError("ERR_TIMELINE_EDIT_HISTORY_RECOVERY_INVALID", "Timeline history recovery is invalid", ProductErrorCategory.DATA_INTEGRITY)
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise ProductError("ERR_TIMELINE_EDIT_HISTORY_RECOVERY_INVALID", "Timeline history recovery is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
        if isinstance(document, Mapping) and document.get("recovery_version") == _HISTORY_RECOVERY_VERSION:
            try:
                _TimelineHistoryParticipant.parse_recovery(document)
            except (TypeError, ValueError) as exc:
                raise ProductError(
                    "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_INVALID",
                    "Timeline participant recovery is invalid",
                    ProductErrorCategory.DATA_INTEGRITY,
                ) from exc
            if self._save_coordinator.recovery_status(self.project_root)["required"]:
                return
            self._save_coordinator.reconcile_participant_orphan(
                self.project_root,
                participant=self._participant,
            )
            return
        if self._save_coordinator.recovery_status(self.project_root)["required"]:
            raise ProductError("ERR_TIMELINE_EDIT_PROJECT_RECOVERY_PENDING", "Complete or roll back the Project save first", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        try:
            recovery = self._parse_history_recovery(document)
        except (TypeError, ValueError) as exc:
            raise ProductError("ERR_TIMELINE_EDIT_HISTORY_RECOVERY_INVALID", "Timeline history recovery is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
        if recovery["project_id"] != self.project_id:
            raise ProductError("ERR_TIMELINE_EDIT_HISTORY_RECOVERY_IDENTITY", "Recovery belongs to another Project", ProductErrorCategory.SECURITY)
        manifest = ProductProjectManifestStore.load(self.project_root)
        if manifest.project_manifest_sha256 == recovery["source_manifest_sha256"]:
            path.unlink()
            return
        if manifest.project_manifest_sha256 != recovery["result_manifest_sha256"]:
            raise ProductError("ERR_TIMELINE_EDIT_HISTORY_RECOVERY_CONFLICT", "Project moved beyond Timeline recovery", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        target_history = parse_project_command_history(recovery["history"])
        current_path = ProjectCommandHistoryStore.path(self.project_root)
        if current_path.exists():
            current = ProjectCommandHistoryStore.load(self.project_root)
            if current.history_sha256 == target_history.history_sha256:
                path.unlink()
                return
        ProjectCommandHistoryStore.save(
            self.project_root, target_history,
            expected_previous_history_sha256=recovery["expected_history_sha256"],
        )
        path.unlink()

    @property
    def snapshot_path(self) -> Path:
        return self.project_root / RELATIVE_PATH

    def project_with_source_bindings(
        self,
        timeline: InteractiveTimeline,
    ) -> tuple[InteractiveTimeline, dict[str, int | None], dict[str, object | None], str]:
        """Read the current bound edit history and retain its typed source map."""

        manifest = ProductProjectManifestStore.load(self.project_root)
        history = self._load(manifest)
        projected, in_out, bindings = TimelineEditProjector.apply_with_source_bindings(
            timeline,
            history,
        )
        return projected, in_out, bindings, manifest.project_manifest_sha256

    def current_edit_persistence_receipt(
        self,
        timeline: InteractiveTimeline,
    ) -> Task044EditPersistenceReceipt | None:
        """Read the latest current TASK-044 revision without creating new truth."""

        self._require_no_history_recovery()
        manifest = ProductProjectManifestStore.load(self.project_root)
        if manifest.project_id != self.project_id:
            raise ProductError(
                "ERR_TIMELINE_EDIT_PROJECT_MISMATCH",
                "Project identity differs",
                ProductErrorCategory.SECURITY,
            )
        self._save_coordinator.require_current_integrity(self.project_root, manifest)
        history = self._load(manifest)
        current = history.current
        if current is None:
            return None
        projected, _in_out, _bindings = TimelineEditProjector.apply_with_source_bindings(
            timeline,
            history,
        )
        binding = next(
            item for item in manifest.child_bindings
            if item.identity == ("TASK-044", RELATIVE_PATH)
        )
        live = ProductProjectManifestStore.load(self.project_root)
        if live.project_manifest_sha256 != manifest.project_manifest_sha256:
            raise ProductError(
                "ERR_TIMELINE_EDIT_RECEIPT_STALE",
                "Project changed during Timeline receipt evaluation",
                ProductErrorCategory.STATE,
            )
        self._save_coordinator.require_current_integrity(self.project_root, live)
        self._require_no_history_recovery()
        return Task044EditPersistenceReceipt(
            receipt_id=f"task044-edit-persistence-r{current.revision}",
            project_id=self.project_id,
            timeline_sha256=projected.timeline_sha256,
            project_manifest_sha256=manifest.project_manifest_sha256,
            edit_snapshot_sha256=binding.content_sha256,
            snapshot_version=binding.format_version,
            history_id=history.history_id,
            current_revision=current.revision,
            current_revision_sha256=current.revision_sha256,
            evaluated_at=manifest.updated_at,
        )

    def _require_no_history_recovery(self) -> None:
        path = self._history_recovery_path
        if path.is_symlink():
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_INVALID",
                "Timeline command history recovery path is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if path.exists() and not path.is_file():
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_INVALID",
                "Timeline command history recovery path is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if path.exists():
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_PENDING",
                "Timeline command history recovery must finish first",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )

    def _load(self, manifest: ProductProjectManifest) -> TimelineEditHistory:
        binding = next((item for item in manifest.child_bindings if item.identity == ("TASK-044", RELATIVE_PATH)), None)
        if binding is None:
            if self.snapshot_path.exists():
                raise ProductError("ERR_TIMELINE_EDIT_UNBOUND_CHILD", "Unbound Timeline edit child exists", ProductErrorCategory.SECURITY)
            return TimelineEditHistory(self.project_id, f"timeline-edit:{self.project_id}")
        if binding.format_id != FORMAT_ID or binding.format_version not in SUPPORTED_FORMAT_VERSIONS:
            raise ProductError("ERR_TIMELINE_EDIT_FORMAT_MISMATCH", "Timeline edit format is unsupported", ProductErrorCategory.NOT_SUPPORTED)
        history = TimelineEditSnapshotStore.load(self.snapshot_path, expected_project_id=self.project_id)
        serialized = TimelineEditSnapshotStore.serialize(history)
        snapshot_version = json.loads(serialized)["snapshot_version"]
        if snapshot_version != binding.format_version:
            raise ProductError(
                "ERR_TIMELINE_EDIT_FORMAT_MISMATCH",
                "Timeline edit binding version differs from the serialized snapshot",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if sha256_bytes(serialized) != binding.content_sha256:
            raise ProductError("ERR_TIMELINE_EDIT_BINDING_CHECKSUM", "Timeline edit child differs from Project binding", ProductErrorCategory.DATA_INTEGRITY)
        self._command_index(history)
        return history

    @staticmethod
    def _command_index(history: TimelineEditHistory) -> dict[str, TimelineEditCommand]:
        commands: dict[str, TimelineEditCommand] = {}
        for row in history.revisions:
            command_id = row.command.command_id
            if command_id in commands:
                raise ProductError(
                    "ERR_TIMELINE_EDIT_COMMAND_DUPLICATE",
                    "Timeline edit command identity is duplicated",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            commands[command_id] = row.command
        return commands

    @staticmethod
    def _command_semantics(command: TimelineEditCommand) -> dict[str, object]:
        value = command.to_dict().copy()
        value.pop("command_id", None)
        value.pop("command_sha256", None)
        return value

    def _validate_project_history_binding(
        self,
        edit_history: TimelineEditHistory,
        project_history: ProjectCommandHistory,
    ) -> None:
        timeline_records = tuple(
            record
            for record in project_history.records
            if record.command_kind.startswith("timeline.")
        )
        if len(timeline_records) != len(edit_history.revisions):
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_BINDING_CONFLICT",
                "Timeline edits and Project history have different lengths",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        originals: dict[str, TimelineEditCommand] = {}
        for record, revision in zip(timeline_records, edit_history.revisions, strict=True):
            command = revision.command
            if record.action is ProjectCommandAction.APPLY:
                if (
                    record.target_identity != command.command_id
                    or record.command_kind != f"timeline.{command.kind.value.lower()}"
                ):
                    raise ProductError(
                        "ERR_TIMELINE_EDIT_HISTORY_BINDING_CONFLICT",
                        "Timeline APPLY record does not match its edit revision",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
                originals[record.target_identity] = command
                continue
            original = originals.get(record.target_identity)
            if (
                original is None
                or record.command_kind != f"timeline.{original.kind.value.lower()}"
            ):
                raise ProductError(
                    "ERR_TIMELINE_EDIT_HISTORY_BINDING_CONFLICT",
                    "Timeline compensation target does not match an APPLY revision",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            expected = (
                original.inverse(command_id=command.command_id)
                if record.action is ProjectCommandAction.UNDO
                else original
            )
            if self._command_semantics(command) != self._command_semantics(expected):
                raise ProductError(
                    "ERR_TIMELINE_EDIT_HISTORY_BINDING_CONFLICT",
                    "Timeline compensation revision differs from its target",
                    ProductErrorCategory.DATA_INTEGRITY,
                )

    def _load_project_history(self) -> tuple[ProjectCommandHistory, str | None]:
        target = ProjectCommandHistoryStore.path(self.project_root)
        if not target.exists():
            return ProjectCommandHistory.create(self.project_id), None
        history = ProjectCommandHistoryStore.load(self.project_root)
        if history.project_id != self.project_id:
            raise ProductError("ERR_PROJECT_HISTORY_IDENTITY_CONFLICT", "Project history belongs to another Project", ProductErrorCategory.SECURITY)
        return history, history.history_sha256

    def history_control_snapshot(self, timeline: InteractiveTimeline) -> dict[str, object]:
        """Project the current body-free Undo/Redo controls without mutation."""

        self._require_no_history_recovery()
        manifest = ProductProjectManifestStore.load(self.project_root)
        if manifest.project_id != self.project_id or timeline.project_id != self.project_id:
            raise ProductError(
                "ERR_TIMELINE_EDIT_PROJECT_MISMATCH",
                "Timeline or Manifest belongs to another Project",
                ProductErrorCategory.SECURITY,
            )
        self._save_coordinator.require_current_integrity(self.project_root, manifest)
        edit_history = self._load(manifest)
        TimelineEditProjector.apply(timeline, edit_history)
        project_history, history_sha256 = self._load_project_history()
        self._validate_project_history_binding(edit_history, project_history)
        if project_history.records and (
            project_history.records[-1].result_manifest_sha256
            != manifest.project_manifest_sha256
        ):
            raise ProductError(
                "ERR_PROJECT_HISTORY_SOURCE_CONFLICT",
                "Project history is not at current Manifest",
                ProductErrorCategory.STATE,
            )
        commands = self._command_index(edit_history)

        def project(candidate: object) -> dict[str, object]:
            if candidate is None:
                return {"available": False}
            command_kind = getattr(candidate, "command_kind", None)
            target_identity = getattr(candidate, "target_identity", None)
            command = commands.get(target_identity) if isinstance(target_identity, str) else None
            if (
                not isinstance(command_kind, str)
                or not command_kind.startswith("timeline.")
                or not isinstance(target_identity, str)
                or command is None
                or command_kind != f"timeline.{command.kind.value.lower()}"
            ):
                return {"available": False}
            return {
                "available": True,
                "command_kind": command_kind,
                "target_identity": target_identity,
            }

        live_manifest = ProductProjectManifestStore.load(self.project_root)
        _live_history, live_history_sha256 = self._load_project_history()
        if (
            live_manifest.project_manifest_sha256 != manifest.project_manifest_sha256
            or live_history_sha256 != history_sha256
        ):
            raise ProductError(
                "ERR_TIMELINE_EDIT_CONTROL_STALE",
                "Project or command history changed during control evaluation",
                ProductErrorCategory.STATE,
            )
        self._save_coordinator.require_current_integrity(self.project_root, live_manifest)
        self._require_no_history_recovery()
        return {
            "available": True,
            "project_history_sha256": history_sha256,
            "undo": project(project_history.undo_candidate()),
            "redo": project(project_history.redo_candidate()),
            "provider_execution_started": False,
            "external_mutation_started": False,
        }

    @staticmethod
    def _clip(timeline: InteractiveTimeline, clip_id: str):
        clip = next((item for item in timeline.clips if item.clip_id == clip_id), None)
        if clip is None:
            raise ProductError("ERR_TIMELINE_EDIT_CLIP_MISSING", "Timeline clip is missing", ProductErrorCategory.STATE)
        return clip

    @staticmethod
    def _snap(desired: int, tolerance: int, anchors: Iterable[SnapAnchor]):
        return TimelineSnapService.snap(desired, tolerance_frames=tolerance, anchors=anchors)

    def prepare_trim(self, *, timeline: InteractiveTimeline, clip_id: str, edge: str,
                     desired_frame: int, snap_tolerance_frames: int = 0,
                     snap_anchors: Iterable[SnapAnchor] = (), command_id: str,
                     expected_project_manifest_sha256: str) -> dict[str, object]:
        projected, _ = TimelineEditProjector.apply(timeline, self._load(ProductProjectManifestStore.load(self.project_root)))
        clip = self._clip(projected, clip_id)
        decision = self._snap(desired_frame, snap_tolerance_frames, snap_anchors)
        if edge == "start":
            kind, start, end = TimelineEditKind.TRIM_START, decision.effective_frame, clip.end_frame
        elif edge == "end":
            kind, start, end = TimelineEditKind.TRIM_END, clip.start_frame, decision.effective_frame
        else:
            raise ValueError("edge must be start or end")
        if start < 0 or end > timeline.duration_frames or end <= start:
            raise ProductError("ERR_TIMELINE_EDIT_RANGE", "Trim would create an invalid range", ProductErrorCategory.VALIDATION)
        command = TimelineEditCommand(command_id, kind, target_clip_id=clip_id,
            before_start_frame=clip.start_frame, before_end_frame=clip.end_frame,
            after_start_frame=start, after_end_frame=end, snap=decision)
        return self._prepare(timeline, command, expected_project_manifest_sha256, "APPLY")

    def prepare_move(self, *, timeline: InteractiveTimeline, clip_id: str, desired_start_frame: int,
                     snap_tolerance_frames: int = 0, snap_anchors: Iterable[SnapAnchor] = (),
                     command_id: str, expected_project_manifest_sha256: str) -> dict[str, object]:
        projected, _ = TimelineEditProjector.apply(timeline, self._load(ProductProjectManifestStore.load(self.project_root)))
        clip = self._clip(projected, clip_id)
        decision = self._snap(desired_start_frame, snap_tolerance_frames, snap_anchors)
        end = decision.effective_frame + (clip.end_frame - clip.start_frame)
        if decision.effective_frame < 0 or end > timeline.duration_frames:
            raise ProductError("ERR_TIMELINE_EDIT_RANGE", "Move would leave the Timeline", ProductErrorCategory.VALIDATION)
        command = TimelineEditCommand(command_id, TimelineEditKind.MOVE, target_clip_id=clip_id,
            before_start_frame=clip.start_frame, before_end_frame=clip.end_frame,
            after_start_frame=decision.effective_frame, after_end_frame=end, snap=decision)
        return self._prepare(timeline, command, expected_project_manifest_sha256, "APPLY")

    def prepare_add_track(self, *, timeline: InteractiveTimeline, track: TimelineTrack,
                          command_id: str, expected_project_manifest_sha256: str) -> dict[str, object]:
        projected, _ = TimelineEditProjector.apply(timeline, self._load(ProductProjectManifestStore.load(self.project_root)))
        if any(item.track_id == track.track_id for item in projected.tracks):
            raise ProductError("ERR_TIMELINE_TRACK_EXISTS", "Track already exists", ProductErrorCategory.STATE)
        return self._prepare(timeline, TimelineEditCommand(command_id, TimelineEditKind.ADD_TRACK, track=track),
                             expected_project_manifest_sha256, "APPLY")

    def prepare_remove_track(self, *, timeline: InteractiveTimeline, track_id: str,
                             command_id: str, expected_project_manifest_sha256: str) -> dict[str, object]:
        projected, _ = TimelineEditProjector.apply(timeline, self._load(ProductProjectManifestStore.load(self.project_root)))
        track = next((item for item in projected.tracks if item.track_id == track_id), None)
        category_count = 0 if track is None else sum(
            timeline_track_category(item) is timeline_track_category(track)
            for item in projected.tracks
        )
        if (track is None or track.minimum_required or category_count <= 1
                or any(item.track_id == track_id for item in projected.clips)):
            raise ProductError("ERR_TIMELINE_TRACK_REMOVE_BLOCKED", "Required, missing or non-empty track cannot be removed", ProductErrorCategory.STATE)
        command = TimelineEditCommand(command_id, TimelineEditKind.REMOVE_TRACK,
                                      target_track_id=track_id, track=track)
        return self._prepare(timeline, command, expected_project_manifest_sha256, "APPLY")

    def prepare_undo(self, *, timeline: InteractiveTimeline, command_id: str,
                     expected_project_manifest_sha256: str,
                     expected_project_history_sha256: str | None = None) -> dict[str, object]:
        project_history, project_history_sha256 = self._load_project_history()
        if (
            expected_project_history_sha256 is not None
            and project_history_sha256 != expected_project_history_sha256
        ):
            raise ProductError(
                "ERR_PROJECT_HISTORY_CAS_CONFLICT",
                "Project history changed; reload first",
                ProductErrorCategory.STATE,
            )
        candidate = project_history.undo_candidate()
        if candidate is None or not candidate.command_kind.startswith("timeline."):
            raise ProductError("ERR_TIMELINE_EDIT_UNDO_EMPTY", "No Timeline edit is available to undo", ProductErrorCategory.STATE)
        edit_history = self._load(ProductProjectManifestStore.load(self.project_root))
        self._validate_project_history_binding(edit_history, project_history)
        original = next((item.command for item in edit_history.revisions if item.command.command_id == candidate.target_identity), None)
        if original is None:
            raise ProductError("ERR_TIMELINE_EDIT_UNDO_TARGET", "Undo target is missing", ProductErrorCategory.DATA_INTEGRITY)
        if candidate.command_kind != f"timeline.{original.kind.value.lower()}":
            raise ProductError(
                "ERR_TIMELINE_EDIT_UNDO_TARGET",
                "Undo target kind differs from Project history",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return self._prepare(
            timeline,
            original.inverse(command_id=command_id),
            expected_project_manifest_sha256,
            "UNDO",
            expected_project_history_sha256=project_history_sha256,
        )

    def prepare_redo(self, *, timeline: InteractiveTimeline, command_id: str,
                     expected_project_manifest_sha256: str,
                     expected_project_history_sha256: str | None = None) -> dict[str, object]:
        project_history, project_history_sha256 = self._load_project_history()
        if (
            expected_project_history_sha256 is not None
            and project_history_sha256 != expected_project_history_sha256
        ):
            raise ProductError(
                "ERR_PROJECT_HISTORY_CAS_CONFLICT",
                "Project history changed; reload first",
                ProductErrorCategory.STATE,
            )
        candidate = project_history.redo_candidate()
        if candidate is None or not candidate.command_kind.startswith("timeline."):
            raise ProductError("ERR_TIMELINE_EDIT_REDO_EMPTY", "No Timeline edit is available to redo", ProductErrorCategory.STATE)
        edit_history = self._load(ProductProjectManifestStore.load(self.project_root))
        self._validate_project_history_binding(edit_history, project_history)
        original = next((item.command for item in edit_history.revisions if item.command.command_id == candidate.target_identity), None)
        if original is None:
            raise ProductError("ERR_TIMELINE_EDIT_REDO_TARGET", "Redo target is missing", ProductErrorCategory.DATA_INTEGRITY)
        if candidate.command_kind != f"timeline.{original.kind.value.lower()}":
            raise ProductError(
                "ERR_TIMELINE_EDIT_REDO_TARGET",
                "Redo target kind differs from Project history",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        projected, _ = TimelineEditProjector.apply(timeline, edit_history)
        if original.kind in {
            TimelineEditKind.INSERT_CLIP,
            TimelineEditKind.REMOVE_CLIP,
            TimelineEditKind.REPLACE_CLIP,
        }:
            replay = TimelineEditCommand(
                command_id=command_id,
                kind=original.kind,
                target_clip_id=original.target_clip_id,
                before_clip=original.before_clip,
                after_clip=original.after_clip,
                before_source_binding=original.before_source_binding,
                after_source_binding=original.after_source_binding,
            )
        elif original.target_clip_id is not None:
            clip = self._clip(projected, original.target_clip_id)
            replay = TimelineEditCommand(command_id, original.kind, target_clip_id=clip.clip_id,
                before_start_frame=clip.start_frame, before_end_frame=clip.end_frame,
                after_start_frame=original.after_start_frame, after_end_frame=original.after_end_frame,
                snap=original.snap)
        elif original.kind is TimelineEditKind.ADD_TRACK:
            replay = TimelineEditCommand(command_id, original.kind, track=original.track)
        else:
            replay = TimelineEditCommand(command_id, original.kind,
                                         target_track_id=original.target_track_id, track=original.track)
        commit_guard = None
        if replay.kind in {
            TimelineEditKind.INSERT_CLIP,
            TimelineEditKind.REPLACE_CLIP,
        } and replay.after_source_binding is not None:
            if self._placement_guard_resolver is None:
                raise ProductError(
                    "ERR_TIMELINE_EDIT_PLACEMENT_GUARD_REQUIRED",
                    "Placement redo requires the current visual Asset guard",
                    ProductErrorCategory.NOT_SUPPORTED,
                )
            commit_guard = self._placement_guard_resolver(replay)
        return self._prepare(
            timeline,
            replay,
            expected_project_manifest_sha256,
            "REDO",
            commit_guard,
            expected_project_history_sha256=project_history_sha256,
        )

    def prepare_placement(
        self,
        *,
        timeline: InteractiveTimeline,
        command: TimelineEditCommand,
        expected_project_manifest_sha256: str,
    ) -> dict[str, object]:
        if command.kind not in {TimelineEditKind.INSERT_CLIP, TimelineEditKind.REPLACE_CLIP}:
            raise ProductError(
                "ERR_TIMELINE_EDIT_PLACEMENT_COMMAND_INVALID",
                "Visual Asset placement accepts only INSERT_CLIP or REPLACE_CLIP",
                ProductErrorCategory.VALIDATION,
            )
        if self._placement_guard_resolver is None:
            raise ProductError(
                "ERR_TIMELINE_EDIT_PLACEMENT_GUARD_REQUIRED",
                "Visual Asset placement guard is unavailable",
                ProductErrorCategory.NOT_SUPPORTED,
            )
        return self._prepare(
            timeline,
            command,
            expected_project_manifest_sha256,
            "APPLY",
            self._placement_guard_resolver(command),
        )

    def _prepare(self, timeline: InteractiveTimeline, command: TimelineEditCommand,
                 expected_manifest: str, history_action: str,
                 commit_guard: CommitGuardFactory | None = None, *,
                 expected_project_history_sha256: str | None = None) -> dict[str, object]:
        manifest = ProductProjectManifestStore.load(self.project_root)
        if manifest.project_manifest_sha256 != expected_manifest:
            raise ProductError("ERR_TIMELINE_EDIT_PROJECT_CONFLICT", "Project changed; reload first", ProductErrorCategory.STATE)
        if timeline.project_id != self.project_id:
            raise ProductError("ERR_TIMELINE_EDIT_PROJECT_MISMATCH", "Timeline belongs to another Project", ProductErrorCategory.SECURITY)
        history = self._load(manifest)
        TimelineEditProjector.apply(timeline, history)
        project_history, project_history_sha = self._load_project_history()
        self._validate_project_history_binding(history, project_history)
        if (
            expected_project_history_sha256 is not None
            and project_history_sha != expected_project_history_sha256
        ):
            raise ProductError(
                "ERR_PROJECT_HISTORY_CAS_CONFLICT",
                "Project history changed while preparing the edit",
                ProductErrorCategory.STATE,
            )
        if project_history.records and project_history.records[-1].result_manifest_sha256 != manifest.project_manifest_sha256:
            raise ProductError("ERR_PROJECT_HISTORY_SOURCE_CONFLICT", "Project history is not at current Manifest", ProductErrorCategory.STATE)
        if command.command_id in self._command_index(history):
            raise ProductError(
                "ERR_TIMELINE_EDIT_COMMAND_DUPLICATE",
                "Timeline edit command identity was already used",
                ProductErrorCategory.STATE,
            )
        with self._pending_lock:
            if len(self._pending) >= _MAX_PENDING_CONFIRMATIONS:
                raise ProductError(
                    "ERR_TIMELINE_EDIT_CONFIRMATION_CAPACITY",
                    "Timeline edit confirmation capacity is exhausted",
                    ProductErrorCategory.STATE,
                )
            token = self._token_factory()
            if not isinstance(token, str) or not token or token in self._pending:
                raise ProductError("ERR_TIMELINE_EDIT_CONFIRMATION_INVALID", "Confirmation identity is invalid", ProductErrorCategory.INTERNAL)
            self._pending[token] = _Confirmation(
                token, expected_manifest, project_history_sha,
                timeline.timeline_sha256, command, history_action, commit_guard,
            )
        return {"confirmation_id": token, "command": command.to_dict(),
                "human_confirmation_required": True, "provider_execution_started": False,
                "external_mutation_started": False}

    def apply(self, *, confirmation_id: str, timeline: InteractiveTimeline) -> dict[str, object]:
        if not isinstance(confirmation_id, str) or not confirmation_id:
            raise ProductError(
                "ERR_TIMELINE_EDIT_CONFIRMATION_INVALID",
                "Confirmation identity is invalid",
                ProductErrorCategory.VALIDATION,
            )
        with self._pending_lock:
            pending = self._pending.pop(confirmation_id, None)
        if pending is None:
            raise ProductError("ERR_TIMELINE_EDIT_CONFIRMATION_INVALID", "Confirmation is missing or consumed", ProductErrorCategory.AUTHORIZATION)
        manifest = ProductProjectManifestStore.load(self.project_root)
        if manifest.project_manifest_sha256 != pending.expected_manifest_sha256 or timeline.timeline_sha256 != pending.base_timeline_sha256:
            raise ProductError("ERR_TIMELINE_EDIT_PROJECT_CONFLICT", "Project or Timeline changed after preparation", ProductErrorCategory.STATE)
        history = self._load(manifest)
        TimelineEditProjector.apply(timeline, history)
        revision_version = (
            FORMAT_VERSION_V1_1
            if history.current is not None and history.current.revision_version == FORMAT_VERSION_V1_1
            or pending.command.kind in {
                TimelineEditKind.INSERT_CLIP,
                TimelineEditKind.REMOVE_CLIP,
                TimelineEditKind.REPLACE_CLIP,
            }
            else FORMAT_VERSION
        )
        revision = TimelineEditRevision(
            self.project_id, history.history_id, len(history.revisions) + 1, timeline.timeline_sha256,
            pending.command, None if history.current is None else history.current.revision_sha256,
            revision_version=revision_version,
        )
        history.append(revision)
        TimelineEditProjector.apply(timeline, history)
        data = TimelineEditSnapshotStore.serialize(history)
        snapshot_version = json.loads(data)["snapshot_version"]
        binding = ProjectChildBinding("TASK-044", RELATIVE_PATH, FORMAT_ID, snapshot_version,
                                      sha256_bytes(data), True, (timeline.timeline_sha256,))
        bindings = [item for item in manifest.child_bindings if item.identity != binding.identity] + [binding]
        target = ProductProjectManifest.create(
            project_id=manifest.project_id, project_revision=manifest.project_revision + 1,
            product_version=manifest.product_version, timebase=manifest.timebase,
            child_bindings=bindings, created_at=manifest.created_at,
            updated_at=max(manifest.updated_at, utc_now_iso()),
        )
        project_history, current_history_sha = self._load_project_history()
        self._validate_project_history_binding(self._load(manifest), project_history)
        if current_history_sha != pending.expected_history_sha256:
            raise ProductError("ERR_PROJECT_HISTORY_CAS_CONFLICT", "Project history changed after preparation", ProductErrorCategory.STATE)
        # The save coordinator deliberately requires an already-resolved parent
        # so a child path can never escape through a newly introduced symlink.
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        command_kind = f"timeline.{pending.command.kind.value.lower()}"
        if pending.history_action == "APPLY":
            updated_project_history = project_history.append_apply(
                command_kind=command_kind, target_identity=pending.command.command_id,
                source_manifest_sha256=manifest.project_manifest_sha256,
                result_manifest_sha256=target.project_manifest_sha256,
                source_revision=manifest.project_revision,
            )
        elif pending.history_action == "UNDO":
            updated_project_history = project_history.append_undo(
                source_manifest_sha256=manifest.project_manifest_sha256,
                result_manifest_sha256=target.project_manifest_sha256,
                source_revision=manifest.project_revision,
            )
        else:
            updated_project_history = project_history.append_redo(
                source_manifest_sha256=manifest.project_manifest_sha256,
                result_manifest_sha256=target.project_manifest_sha256,
                source_revision=manifest.project_revision,
            )
        participant = None
        if snapshot_version == FORMAT_VERSION_V1_1:
            participant = _TimelineHistoryParticipant(
                project_id=self.project_id,
                recovery_path=self._history_recovery_path,
                expected_history_sha256=current_history_sha,
                target_history=updated_project_history,
            )
        else:
            self._write_history_recovery(
                source_manifest_sha256=manifest.project_manifest_sha256,
                result_manifest_sha256=target.project_manifest_sha256,
                expected_history_sha256=current_history_sha,
                history=updated_project_history,
            )
        saved = self._save_coordinator.save(
            self.project_root, target, {RELATIVE_PATH: data},
            expected_previous_manifest_sha256=manifest.project_manifest_sha256,
            participant=participant,
            commit_guard=pending.commit_guard,
        )
        if participant is None:
            ProjectCommandHistoryStore.save(
                self.project_root,
                updated_project_history,
                expected_previous_history_sha256=current_history_sha,
            )
            self._history_recovery_path.unlink()
        projected, in_out = TimelineEditProjector.apply(timeline, history)
        return {"project_manifest_sha256": saved.project_manifest_sha256,
                "timeline_revision": revision.revision, "timeline_revision_sha256": revision.revision_sha256,
                "project_history_sha256": updated_project_history.history_sha256,
                "projected_timeline_sha256": projected.timeline_sha256, "in_out": in_out,
                "provider_execution_started": False, "external_mutation_started": False}

    def cancel(self, *, confirmation_id: str) -> dict[str, object]:
        if not isinstance(confirmation_id, str) or not confirmation_id:
            raise ProductError(
                "ERR_TIMELINE_EDIT_CONFIRMATION_INVALID",
                "Confirmation identity is invalid",
                ProductErrorCategory.VALIDATION,
            )
        with self._pending_lock:
            pending = self._pending.pop(confirmation_id, None)
        if pending is None:
            raise ProductError(
                "ERR_TIMELINE_EDIT_CONFIRMATION_INVALID",
                "Confirmation is missing or consumed",
                ProductErrorCategory.AUTHORIZATION,
            )
        return {
            "confirmation_id": confirmation_id,
            "cancelled": True,
            "provider_execution_started": False,
            "external_mutation_started": False,
        }

    def project_save_recovery_status(self) -> dict[str, object]:
        status = self._save_coordinator.recovery_status(self.project_root)
        return {
            **status,
            "history_reconciliation_pending": bool(
                status.get("participant_required")
                and status.get("participant_id") == _HISTORY_PARTICIPANT_ID
            ),
        }

    def recover_project_save(
        self,
        *,
        transaction_id: str,
        action: str,
        commit_guard: CommitGuardFactory | None = None,
    ) -> dict[str, object]:
        if not isinstance(transaction_id, str) or not transaction_id:
            raise ProductError(
                "ERR_TIMELINE_EDIT_RECOVERY_REQUEST_INVALID",
                "Project save recovery transaction is invalid",
                ProductErrorCategory.VALIDATION,
            )
        status = self._save_coordinator.recovery_status(self.project_root)
        if not status["required"] or status.get("transaction_id") != transaction_id:
            raise ProductError(
                "ERR_TIMELINE_EDIT_RECOVERY_STALE",
                "Project save recovery is missing or changed",
                ProductErrorCategory.STATE,
            )
        if status.get("participant_id") != _HISTORY_PARTICIPANT_ID:
            raise ProductError(
                "ERR_TIMELINE_EDIT_RECOVERY_PARTICIPANT",
                "Project save recovery does not belong to Timeline history",
                ProductErrorCategory.NOT_SUPPORTED,
            )
        available = tuple(status["available_actions"])
        if commit_guard is None and action in {"COMPLETE", "FINALIZE"}:
            commit_guard = self._placement_recovery_guard()
        if action in {"COMPLETE", "FINALIZE"}:
            if action not in available:
                raise ProductError(
                    "ERR_TIMELINE_EDIT_RECOVERY_ACTION",
                    "Requested Project save recovery action is unavailable",
                    ProductErrorCategory.STATE,
                )
            manifest = self._save_coordinator.recover_complete(
                self.project_root,
                transaction_id=transaction_id,
                participant=self._participant,
                commit_guard=commit_guard,
            )
        elif action == "ROLLBACK":
            if action not in available:
                raise ProductError(
                    "ERR_TIMELINE_EDIT_RECOVERY_ACTION",
                    "Requested Project save recovery action is unavailable",
                    ProductErrorCategory.STATE,
                )
            manifest = self._save_coordinator.recover_rollback(
                self.project_root,
                transaction_id=transaction_id,
                participant=self._participant,
                commit_guard=commit_guard,
            )
        else:
            raise ProductError(
                "ERR_TIMELINE_EDIT_RECOVERY_ACTION",
                "Project save recovery action is invalid",
                ProductErrorCategory.VALIDATION,
            )
        history, history_sha = self._load_project_history()
        return {
            "transaction_id": transaction_id,
            "action": action,
            "project_manifest_sha256": manifest.project_manifest_sha256,
            "project_history_sha256": history_sha,
            "project_history_record_count": len(history.records),
            "provider_execution_started": False,
            "external_mutation_started": False,
        }

    def _placement_recovery_guard(self) -> CommitGuardFactory | None:
        """Resolve only the exact pending APPLY/REDO placement guard."""

        journal = ProjectSaveJournalStore.load(self.project_root)
        if journal.participant_plan is None or journal.participant_plan.participant_id != _HISTORY_PARTICIPANT_ID:
            raise ProductError(
                "ERR_TIMELINE_EDIT_RECOVERY_PARTICIPANT",
                "Project save recovery does not belong to Timeline history",
                ProductErrorCategory.NOT_SUPPORTED,
            )
        if self._history_recovery_path.exists():
            recovery = self._participant._load_recovery()
            target_project_history = recovery["target_history_object"]
        else:
            # The participant sidecar is consumed before its COMPLETE result is
            # journaled.  If that final journal write is interrupted, the
            # canonical Project history is the only remaining target body.
            target_project_history = ProjectCommandHistoryStore.load(self.project_root)
            if target_project_history.history_sha256 != journal.participant_plan.target_content_sha256:
                raise ProductError(
                    "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_INVALID",
                    "Timeline participant target history differs from its journal plan",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
        if not isinstance(target_project_history, ProjectCommandHistory):
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_INVALID",
                "Timeline participant target history is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if not target_project_history.records:
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_INVALID",
                "Timeline participant target history is empty",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        record = target_project_history.records[-1]
        if record.action.value == "UNDO":
            return None
        entry = next((item for item in journal.entries if item.relative_path == RELATIVE_PATH), None)
        if entry is None:
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_INVALID",
                "Timeline participant target child is missing",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        current_manifest = ProductProjectManifestStore.load(self.project_root)
        if current_manifest.project_manifest_sha256 == journal.target_manifest.project_manifest_sha256:
            target_path = self.snapshot_path
        else:
            target_path = self.project_root / ".bai-project" / Path(*entry.staged_relative_path.split("/"))
        target_history = TimelineEditSnapshotStore.load(
            target_path,
            expected_project_id=self.project_id,
        )
        if sha256_bytes(TimelineEditSnapshotStore.serialize(target_history)) != entry.target_sha256:
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_INVALID",
                "Timeline participant target child differs from its journal",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        command = next(
            (
                item.command for item in reversed(target_history.revisions)
                if item.command.command_id == record.target_identity
            ),
            None,
        )
        if command is None:
            raise ProductError(
                "ERR_TIMELINE_EDIT_HISTORY_RECOVERY_INVALID",
                "Timeline participant target command is missing",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if (
            command.kind in {TimelineEditKind.INSERT_CLIP, TimelineEditKind.REPLACE_CLIP}
            and command.after_source_binding is not None
        ):
            if self._placement_guard_resolver is None:
                raise ProductError(
                    "ERR_TIMELINE_EDIT_PLACEMENT_GUARD_REQUIRED",
                    "Placement recovery requires the current visual Asset guard",
                    ProductErrorCategory.NOT_SUPPORTED,
                )
            return self._placement_guard_resolver(command)
        return None


__all__ = ["Task044TimelineEditApplication"]
