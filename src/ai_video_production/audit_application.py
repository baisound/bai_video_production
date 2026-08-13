"""TASK-038 durable project-scoped Audit Workspace application.

Human decisions span the immutable Audit store and TASK-037 Production Control.
This service records the exact intended transition before either store changes,
then requires explicit recovery if the process stops between the two writes.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import secrets
from typing import Any, Callable

from .atomic import AtomicJsonWriter
from .audit_production_binding import AuditProductionControlBinding
from .audit_workspace import Task038AuditWorkspaceProjection, Task038AuditWorkspaceService
from .candidate_audit import AuditRecord, CandidateAuditRegistry, HumanCandidateDecision, HumanDecision
from .candidate_audit_store import CandidateAuditSnapshotStore
from .errors import ProductError, ProductErrorCategory
from .production_control import CandidateLifecycle, ProductionControlRegistry
from .production_control_store import ProductionControlSnapshotStore, _exclusive_snapshot_lock
from .serialization import canonical_json_bytes, sha256_bytes


TokenFactory = Callable[[], str]
FailureInjector = Callable[[str], None]
_PRODUCTION_NAME = "production-control.json"
_AUDIT_NAME = "candidate-audit.json"
_TRANSACTION_NAME = "task038-decision-transaction.json"
_MAX_TRANSACTION_BYTES = 128 * 1024


@dataclass(slots=True)
class _PendingDecision:
    confirmation_id: str
    production_sha256: str
    audit_sha256: str
    candidate_id: str
    decision: str
    consumed: bool = False


class Task038AuditApplication:
    """Durable authority boundary for Candidate audits and Human decisions."""

    def __init__(
        self,
        *,
        project_root: str | Path,
        project_id: str,
        token_factory: TokenFactory | None = None,
        failure_injector: FailureInjector | None = None,
    ) -> None:
        root = Path(project_root)
        if root.is_symlink() or not root.is_dir():
            raise ProductError(
                "ERR_AUDIT_APPLICATION_PROJECT_ROOT_INVALID",
                "Audit project root must be an existing regular directory",
                ProductErrorCategory.VALIDATION,
            )
        if not isinstance(project_id, str) or not project_id.strip():
            raise ProductError(
                "ERR_AUDIT_APPLICATION_PROJECT_ID_INVALID",
                "Audit project_id must be non-empty text",
                ProductErrorCategory.VALIDATION,
            )
        self.project_root = root
        self.project_id = project_id
        self.production_path = root / _PRODUCTION_NAME
        self.audit_path = root / _AUDIT_NAME
        self.transaction_path = root / _TRANSACTION_NAME
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._failure_injector = failure_injector
        self._confirmations: dict[str, _PendingDecision] = {}

    @staticmethod
    def _production_hash(registry: ProductionControlRegistry) -> str:
        return str(ProductionControlSnapshotStore.snapshot(registry)["snapshot_sha256"])

    @staticmethod
    def _audit_hash(registry: CandidateAuditRegistry) -> str:
        return str(CandidateAuditSnapshotStore.snapshot(registry)["snapshot_sha256"])

    def _load_production(self) -> tuple[ProductionControlRegistry, str, bool]:
        if self.production_path.is_symlink():
            raise ProductError("ERR_PRODUCTION_SNAPSHOT_FILE_INVALID", "Production snapshot cannot be a symlink", ProductErrorCategory.SECURITY)
        if self.production_path.exists():
            registry = ProductionControlSnapshotStore.load(self.production_path)
            foreign = sorted(slot.slot_id for slot in registry.slots.values() if slot.project_id != self.project_id)
            if foreign:
                raise ProductError(
                    "ERR_AUDIT_APPLICATION_PROJECT_MISMATCH",
                    "Production snapshot contains Slots from another project",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"foreign_slot_ids": foreign},
                )
            return registry, self._production_hash(registry), True
        registry = ProductionControlRegistry()
        return registry, self._production_hash(registry), False

    def _load_audits(self) -> tuple[CandidateAuditRegistry, str, bool]:
        if self.audit_path.is_symlink():
            raise ProductError("ERR_AUDIT_SNAPSHOT_FILE_INVALID", "Audit snapshot cannot be a symlink", ProductErrorCategory.SECURITY)
        if self.audit_path.exists():
            registry = CandidateAuditSnapshotStore.load(self.audit_path)
            return registry, self._audit_hash(registry), True
        registry = CandidateAuditRegistry()
        return registry, self._audit_hash(registry), False

    @staticmethod
    def _require_expected(actual: str, expected: str, kind: str) -> None:
        if not isinstance(expected, str) or expected != actual:
            raise ProductError(
                "ERR_AUDIT_APPLICATION_SNAPSHOT_CONFLICT",
                f"{kind} snapshot changed; reload before applying the command",
                ProductErrorCategory.STATE,
                details={"current_snapshot_sha256": actual, "snapshot_kind": kind},
            )

    @staticmethod
    def _transaction_body(value: dict[str, Any]) -> dict[str, Any]:
        body = {key: item for key, item in value.items() if key != "transaction_sha256"}
        body["transaction_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def _validate_transaction(cls, value: Any) -> None:
        if not isinstance(value, dict) or value.get("transaction_version") != "1.0.0":
            raise ProductError("ERR_AUDIT_TRANSACTION_INVALID", "Audit transaction is invalid", ProductErrorCategory.DATA_INTEGRITY)
        expected = value.get("transaction_sha256")
        actual = cls._transaction_body(value)["transaction_sha256"]
        if expected != actual:
            raise ProductError("ERR_AUDIT_TRANSACTION_CHECKSUM", "Audit transaction checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
        required = {
            "transaction_id", "project_id", "state", "confirmation_id_sha256", "candidate_id",
            "decision", "actor_id", "notes", "audit_refs", "old_production_sha256",
            "new_production_sha256", "old_audit_sha256", "new_audit_sha256", "decision_id",
        }
        if not required.issubset(value) or value["state"] not in {"PREPARED", "COMMITTED", "ABANDONED"}:
            raise ProductError("ERR_AUDIT_TRANSACTION_INVALID", "Audit transaction fields are invalid", ProductErrorCategory.DATA_INTEGRITY)

    def _write_transaction(self, value: dict[str, Any]) -> dict[str, Any]:
        document = self._transaction_body(value)
        AtomicJsonWriter.write(self.transaction_path, document, validator=self._validate_transaction)
        return document

    def _load_transaction(self) -> dict[str, Any] | None:
        target = self.transaction_path
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ProductError("ERR_AUDIT_TRANSACTION_FILE_INVALID", "Audit transaction must be a regular non-symlink file", ProductErrorCategory.SECURITY)
        if not target.exists():
            return None
        size = target.stat().st_size
        if size <= 0 or size > _MAX_TRANSACTION_BYTES:
            raise ProductError("ERR_AUDIT_TRANSACTION_SIZE", "Audit transaction size is outside the allowed bound", ProductErrorCategory.DATA_INTEGRITY)
        try:
            value = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_AUDIT_TRANSACTION_READ", "Audit transaction could not be read", ProductErrorCategory.DATA_INTEGRITY) from exc
        self._validate_transaction(value)
        if value["project_id"] != self.project_id:
            raise ProductError("ERR_AUDIT_TRANSACTION_PROJECT_MISMATCH", "Audit transaction belongs to another project", ProductErrorCategory.DATA_INTEGRITY)
        return value

    def _recovery_state(self, transaction: dict[str, Any] | None, production_sha: str, audit_sha: str) -> dict[str, Any]:
        if transaction is None or transaction["state"] != "PREPARED":
            return {"required": False, "state": None, "available_actions": []}
        old_p, new_p = transaction["old_production_sha256"], transaction["new_production_sha256"]
        old_a, new_a = transaction["old_audit_sha256"], transaction["new_audit_sha256"]
        if audit_sha == old_a and production_sha == old_p:
            state, actions = "OLD_OLD", ["COMPLETE", "ABANDON"]
        elif audit_sha == new_a and production_sha == old_p and old_p != new_p:
            state, actions = "AUDIT_NEW_PRODUCTION_OLD", ["COMPLETE"]
        elif audit_sha == old_a and production_sha == new_p and old_p != new_p:
            state, actions = "AUDIT_OLD_PRODUCTION_NEW", ["COMPLETE"]
        elif audit_sha == new_a and production_sha == new_p:
            state, actions = "NEW_NEW", ["FINALIZE"]
        else:
            state, actions = "UNKNOWN_MIXTURE", []
        return {
            "required": True,
            "state": state,
            "transaction_id": transaction["transaction_id"],
            "candidate_id": transaction["candidate_id"],
            "decision": transaction["decision"],
            "available_actions": actions,
        }

    def snapshot(self, *, scene_id: str | None = None) -> dict[str, Any]:
        production, production_sha, production_persisted = self._load_production()
        audits, audit_sha, audit_persisted = self._load_audits()
        recovery = self._recovery_state(self._load_transaction(), production_sha, audit_sha)
        workspace = Task038AuditWorkspaceProjection.build(production=production, audits=audits, scene_id=scene_id)
        if recovery["required"]:
            for candidate in workspace["candidates"]:
                candidate["available_human_actions"] = []
        return {
            "application_version": "1.0.0",
            "task_owner": "TASK-038",
            "project_id": self.project_id,
            "production_snapshot_sha256": production_sha,
            "audit_snapshot_sha256": audit_sha,
            "production_persisted": production_persisted,
            "audit_persisted": audit_persisted,
            "recovery": recovery,
            "workspace": workspace,
            "human_final_authority_preserved": True,
            "automatic_regeneration_started": False,
            "physical_delete_requested": False,
        }

    def record_audit(
        self,
        *,
        record: AuditRecord,
        expected_production_snapshot_sha256: str,
        expected_audit_snapshot_sha256: str,
    ) -> dict[str, Any]:
        with _exclusive_snapshot_lock(self.transaction_path):
            production, production_sha, _ = self._load_production()
            audits, audit_sha, audit_persisted = self._load_audits()
            self._require_expected(production_sha, expected_production_snapshot_sha256, "Production")
            self._require_expected(audit_sha, expected_audit_snapshot_sha256, "Audit")
            if self._recovery_state(self._load_transaction(), production_sha, audit_sha)["required"]:
                raise ProductError("ERR_AUDIT_APPLICATION_RECOVERY_REQUIRED", "Complete Audit recovery before recording another Audit", ProductErrorCategory.STATE)
            candidate = production.candidates.get(record.candidate_id)
            if candidate is None or candidate.lifecycle_state is not CandidateLifecycle.READY_FOR_AUDIT:
                raise ProductError("ERR_AUDIT_APPLICATION_CANDIDATE_NOT_READY", "Candidate must be explicitly READY_FOR_AUDIT before recording an Audit", ProductErrorCategory.STATE)
            AuditProductionControlBinding.record_audit(production, audits, record)
            CandidateAuditSnapshotStore.save(
                self.audit_path,
                audits,
                expected_previous_snapshot_sha256=audit_sha if audit_persisted else None,
            )
        return self.snapshot()

    def prepare_human_decision(
        self,
        *,
        candidate_id: str,
        decision: str,
        expected_production_snapshot_sha256: str,
        expected_audit_snapshot_sha256: str,
    ) -> dict[str, Any]:
        production, production_sha, _ = self._load_production()
        audits, audit_sha, _ = self._load_audits()
        self._require_expected(production_sha, expected_production_snapshot_sha256, "Production")
        self._require_expected(audit_sha, expected_audit_snapshot_sha256, "Audit")
        if self._recovery_state(self._load_transaction(), production_sha, audit_sha)["required"]:
            raise ProductError("ERR_AUDIT_APPLICATION_RECOVERY_REQUIRED", "Complete Audit recovery before preparing another decision", ProductErrorCategory.STATE)
        token = self._token_factory()
        service = Task038AuditWorkspaceService(production=production, audits=audits, token_factory=lambda: token)
        prepared = service.prepare_human_decision(candidate_id=candidate_id, decision=decision)
        if token in self._confirmations or not token.strip():
            raise ProductError("ERR_AUDIT_APPLICATION_CONFIRMATION_TOKEN_INVALID", "Audit confirmation token is invalid", ProductErrorCategory.INTERNAL)
        self._confirmations[token] = _PendingDecision(token, production_sha, audit_sha, candidate_id, decision)
        return {
            **prepared,
            "project_id": self.project_id,
            "production_snapshot_sha256": production_sha,
            "audit_snapshot_sha256": audit_sha,
        }

    def _inject(self, stage: str) -> None:
        if self._failure_injector is not None:
            self._failure_injector(stage)

    def apply_human_decision(self, *, confirmation_id: str, actor_id: str, notes: str | None = None) -> dict[str, Any]:
        pending = self._confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError("ERR_AUDIT_APPLICATION_CONFIRMATION_INVALID", "Audit confirmation is missing or already used", ProductErrorCategory.AUTHORIZATION)
        pending.consumed = True
        with _exclusive_snapshot_lock(self.transaction_path):
            production, production_sha, production_persisted = self._load_production()
            audits, audit_sha, audit_persisted = self._load_audits()
            self._require_expected(production_sha, pending.production_sha256, "Production")
            self._require_expected(audit_sha, pending.audit_sha256, "Audit")
            if self._recovery_state(self._load_transaction(), production_sha, audit_sha)["required"]:
                raise ProductError("ERR_AUDIT_APPLICATION_RECOVERY_REQUIRED", "Complete Audit recovery before applying another decision", ProductErrorCategory.STATE)
            service = Task038AuditWorkspaceService(production=production, audits=audits, token_factory=lambda: confirmation_id)
            service.prepare_human_decision(candidate_id=pending.candidate_id, decision=pending.decision)
            result = service.apply_human_decision(confirmation_id=confirmation_id, actor_id=actor_id, notes=notes)
            decision = result["decision"]
            new_production_sha = self._production_hash(production)
            new_audit_sha = self._audit_hash(audits)
            transaction = self._write_transaction({
                "transaction_version": "1.0.0",
                "task_owner": "TASK-038",
                "transaction_id": f"txn-{sha256_bytes(confirmation_id.encode('utf-8'))[:24]}",
                "project_id": self.project_id,
                "state": "PREPARED",
                "confirmation_id_sha256": sha256_bytes(confirmation_id.encode("utf-8")),
                "candidate_id": pending.candidate_id,
                "decision_id": decision["decision_id"],
                "decision": pending.decision,
                "actor_id": actor_id,
                "notes": notes,
                "audit_refs": decision["audit_refs"],
                "old_production_sha256": production_sha,
                "new_production_sha256": new_production_sha,
                "old_audit_sha256": audit_sha,
                "new_audit_sha256": new_audit_sha,
            })
            self._inject("after_transaction_prepare")
            CandidateAuditSnapshotStore.save(self.audit_path, audits, expected_previous_snapshot_sha256=audit_sha if audit_persisted else None)
            self._inject("after_audit_save")
            ProductionControlSnapshotStore.save(self.production_path, production, expected_previous_snapshot_sha256=production_sha if production_persisted else None)
            self._inject("after_production_save")
            transaction["state"] = "COMMITTED"
            self._write_transaction(transaction)
        return {**result, "application": self.snapshot()}

    @staticmethod
    def _decision_from_transaction(transaction: dict[str, Any]) -> HumanDecision:
        return HumanDecision(
            decision_id=str(transaction["decision_id"]),
            candidate_id=str(transaction["candidate_id"]),
            audit_refs=tuple(str(item) for item in transaction["audit_refs"]),
            decision=HumanCandidateDecision(str(transaction["decision"])),
            actor_id=str(transaction["actor_id"]),
            notes=transaction.get("notes"),
        )

    @staticmethod
    def _apply_production_only(production: ProductionControlRegistry, decision: HumanDecision) -> None:
        target = {
            HumanCandidateDecision.ACCEPT: CandidateLifecycle.ACCEPTED,
            HumanCandidateDecision.REJECT: CandidateLifecycle.REJECTED,
            HumanCandidateDecision.ALTERNATE_USE: CandidateLifecycle.ALTERNATE_USE,
            HumanCandidateDecision.NEEDS_REGENERATION: None,
        }[decision.decision]
        candidate = production.candidates.get(decision.candidate_id)
        if candidate is None or candidate.lifecycle_state is not CandidateLifecycle.READY_FOR_AUDIT:
            raise ProductError("ERR_AUDIT_RECOVERY_PRODUCTION_STATE_INVALID", "Prepared Production transition no longer applies", ProductErrorCategory.DATA_INTEGRITY)
        if target is not None:
            production.transition_candidate(decision.candidate_id, target)

    def apply_recovery(self, *, action: str) -> dict[str, Any]:
        with _exclusive_snapshot_lock(self.transaction_path):
            transaction = self._load_transaction()
            if transaction is None or transaction["state"] != "PREPARED":
                raise ProductError("ERR_AUDIT_RECOVERY_NOT_REQUIRED", "No prepared Audit decision requires recovery", ProductErrorCategory.STATE)
            production, production_sha, production_persisted = self._load_production()
            audits, audit_sha, audit_persisted = self._load_audits()
            recovery = self._recovery_state(transaction, production_sha, audit_sha)
            if action not in recovery["available_actions"]:
                raise ProductError("ERR_AUDIT_RECOVERY_ACTION_INVALID", "Recovery action is not allowed for the exact persisted state", ProductErrorCategory.AUTHORIZATION, details={"recovery_state": recovery["state"]})
            if action == "ABANDON":
                transaction["state"] = "ABANDONED"
                self._write_transaction(transaction)
                return self.snapshot()
            if action == "FINALIZE":
                transaction["state"] = "COMMITTED"
                self._write_transaction(transaction)
                return self.snapshot()

            decision = self._decision_from_transaction(transaction)
            old_a, new_a = transaction["old_audit_sha256"], transaction["new_audit_sha256"]
            old_p, new_p = transaction["old_production_sha256"], transaction["new_production_sha256"]
            if audit_sha == old_a and production_sha == old_p:
                AuditProductionControlBinding.apply_human_decision(production, audits, decision)
            elif audit_sha == new_a and production_sha == old_p:
                self._apply_production_only(production, decision)
            elif audit_sha == old_a and production_sha == new_p:
                audits.add_human_decision(decision)
            else:
                raise ProductError("ERR_AUDIT_RECOVERY_STATE_UNKNOWN", "Prepared Audit transaction does not match either exact store state", ProductErrorCategory.DATA_INTEGRITY)
            if self._audit_hash(audits) != new_a or self._production_hash(production) != new_p:
                raise ProductError("ERR_AUDIT_RECOVERY_RESULT_MISMATCH", "Recovered state does not match the prepared exact result", ProductErrorCategory.DATA_INTEGRITY)
            if audit_sha == old_a:
                CandidateAuditSnapshotStore.save(self.audit_path, audits, expected_previous_snapshot_sha256=audit_sha if audit_persisted else None)
            if production_sha == old_p and old_p != new_p:
                ProductionControlSnapshotStore.save(self.production_path, production, expected_previous_snapshot_sha256=production_sha if production_persisted else None)
            transaction["state"] = "COMMITTED"
            self._write_transaction(transaction)
        return self.snapshot()
