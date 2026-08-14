"""TASK-039 durable Continuity Product application.

Continuity Edge registration is an exact recoverable transaction across the
Continuity Registry and TASK-037 Production Control. No operation regenerates,
deletes or mutates media/NLE state.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import secrets
from typing import Any, Callable

from .atomic import AtomicJsonWriter
from .continuity_map import ContinuityBoundaryType, ContinuityEdge
from .continuity_registry import ContinuityProductionControlBinding, ContinuityRegistry
from .continuity_registry_store import ContinuityRegistryStore
from .continuity_workspace import Task039ContinuityWorkspaceProjection, Task039ContinuityWorkspaceService
from .errors import ProductError, ProductErrorCategory
from .production_control import CandidateLifecycle, EntityRef, EntityType, ProductionControlRegistry, SlotKind, SlotStatus
from .production_control_application import Task037ProductionControlApplication
from .production_control_store import ProductionControlSnapshotStore, _exclusive_snapshot_lock
from .serialization import canonical_json_bytes, sha256_bytes


TokenFactory = Callable[[], str]
FailureInjector = Callable[[str], None]
_CONTINUITY_NAME = "continuity-registry.json"
_TRANSACTION_NAME = "task039-edge-transaction.json"
_MAX_TRANSACTION_BYTES = 128 * 1024
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")
_TRANSACTION_FIELDS = {
    "transaction_version", "task_owner", "transaction_id", "project_id", "state",
    "confirmation_id_sha256", "edge", "old_continuity_sha256", "new_continuity_sha256",
    "old_production_sha256", "new_production_sha256", "transaction_sha256",
}
_EDGE_FIELDS = {
    "edge_id", "from_scene_id", "from_slot_id", "from_candidate_id", "from_asset_id",
    "from_asset_sha256", "to_scene_id", "to_slot_id", "boundary_type",
    "character_contract_refs", "space_contract_refs",
}


@dataclass(slots=True)
class _PendingEdge:
    confirmation_id: str
    edge: ContinuityEdge
    old_continuity_sha256: str
    new_continuity_sha256: str
    old_production_sha256: str
    new_production_sha256: str
    consumed: bool = False


@dataclass(slots=True)
class _PendingSoftApproval:
    confirmation_id: str
    edge_id: str
    continuity_sha256: str
    production_sha256: str
    consumed: bool = False


class Task039ContinuityApplication:
    def __init__(
        self,
        *,
        project_root: str | Path,
        project_id: str,
        production_control: Task037ProductionControlApplication | None = None,
        token_factory: TokenFactory | None = None,
        failure_injector: FailureInjector | None = None,
    ) -> None:
        root = Path(project_root)
        if root.is_symlink() or not root.is_dir():
            raise ProductError("ERR_CONTINUITY_APPLICATION_PROJECT_ROOT_INVALID", "Continuity project root must be an existing regular directory", ProductErrorCategory.VALIDATION)
        if not isinstance(project_id, str) or not project_id.strip():
            raise ProductError("ERR_CONTINUITY_APPLICATION_PROJECT_ID_INVALID", "Continuity project_id must be non-empty text", ProductErrorCategory.VALIDATION)
        if production_control is not None and (
            production_control.project_root != root or production_control.project_id != project_id
        ):
            raise ProductError("ERR_CONTINUITY_APPLICATION_PRODUCTION_SCOPE_MISMATCH", "Continuity and Production Control must use the same project root/id", ProductErrorCategory.SECURITY)
        self.project_root = root
        self.project_id = project_id
        self.production_control = production_control or Task037ProductionControlApplication(project_root=root, project_id=project_id)
        self.continuity_path = root / _CONTINUITY_NAME
        self.transaction_path = root / _TRANSACTION_NAME
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._failure_injector = failure_injector
        self._edge_confirmations: dict[str, _PendingEdge] = {}
        self._soft_confirmations: dict[str, _PendingSoftApproval] = {}

    @staticmethod
    def _production_hash(registry: ProductionControlRegistry) -> str:
        return str(ProductionControlSnapshotStore.snapshot(registry)["snapshot_sha256"])

    @staticmethod
    def _continuity_hash(registry: ContinuityRegistry) -> str:
        return str(ContinuityRegistryStore.snapshot(registry)["registry_sha256"])

    def _load_production(self) -> tuple[ProductionControlRegistry, str, bool]:
        target = self.production_control.snapshot_path
        if target.exists():
            registry = ProductionControlSnapshotStore.load(target)
            foreign = sorted(slot.slot_id for slot in registry.slots.values() if slot.project_id != self.project_id)
            if foreign:
                raise ProductError("ERR_CONTINUITY_APPLICATION_PROJECT_MISMATCH", "Production contains foreign project Slots", ProductErrorCategory.DATA_INTEGRITY, details={"foreign_slot_ids": foreign})
            return registry, self._production_hash(registry), True
        registry = ProductionControlRegistry()
        return registry, self._production_hash(registry), False

    def _load_continuity(self) -> tuple[ContinuityRegistry, str, bool]:
        target = self.continuity_path
        if target.exists():
            registry = ContinuityRegistryStore.recover(target)
            return registry, self._continuity_hash(registry), True
        registry = ContinuityRegistry()
        return registry, self._continuity_hash(registry), False

    @staticmethod
    def _require_expected(actual: str, expected: str, kind: str) -> None:
        if not isinstance(expected, str) or actual != expected:
            raise ProductError("ERR_CONTINUITY_APPLICATION_SNAPSHOT_CONFLICT", f"{kind} snapshot changed; reload before applying the command", ProductErrorCategory.STATE, details={"snapshot_kind": kind, "current_snapshot_sha256": actual})

    def _new_token(self, existing: dict[str, Any]) -> str:
        token = self._token_factory()
        if not isinstance(token, str) or not token.strip() or token in existing:
            raise ProductError("ERR_CONTINUITY_APPLICATION_CONFIRMATION_TOKEN_INVALID", "Continuity confirmation token is invalid", ProductErrorCategory.INTERNAL)
        return token

    @staticmethod
    def _transaction_body(value: dict[str, Any]) -> dict[str, Any]:
        body = {key: item for key, item in value.items() if key != "transaction_sha256"}
        body["transaction_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def _validate_transaction(cls, value: Any) -> None:
        if (
            not isinstance(value, dict)
            or set(value) != _TRANSACTION_FIELDS
            or value.get("transaction_version") != "1.0.0"
            or value.get("task_owner") != "TASK-039"
        ):
            raise ProductError("ERR_CONTINUITY_TRANSACTION_INVALID", "Continuity transaction is invalid", ProductErrorCategory.DATA_INTEGRITY)
        if value.get("transaction_sha256") != cls._transaction_body(value)["transaction_sha256"]:
            raise ProductError("ERR_CONTINUITY_TRANSACTION_CHECKSUM", "Continuity transaction checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
        hashes = (
            value["confirmation_id_sha256"], value["old_continuity_sha256"],
            value["new_continuity_sha256"], value["old_production_sha256"],
            value["new_production_sha256"],
        )
        if (
            not isinstance(value["transaction_id"], str)
            or not value["transaction_id"].strip()
            or not isinstance(value["project_id"], str)
            or not value["project_id"].strip()
            or value["state"] not in {"PREPARED", "COMMITTED", "ABANDONED"}
            or not all(isinstance(item, str) and _SHA_RE.fullmatch(item) for item in hashes)
        ):
            raise ProductError("ERR_CONTINUITY_TRANSACTION_INVALID", "Continuity transaction fields are invalid", ProductErrorCategory.DATA_INTEGRITY)
        cls._edge_from_dict(value["edge"])

    def _write_transaction(self, value: dict[str, Any]) -> dict[str, Any]:
        document = self._transaction_body(value)
        AtomicJsonWriter.write(self.transaction_path, document, validator=self._validate_transaction)
        return document

    def _load_transaction(self) -> dict[str, Any] | None:
        target = self.transaction_path
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ProductError("ERR_CONTINUITY_TRANSACTION_FILE_INVALID", "Continuity transaction must be a regular non-symlink file", ProductErrorCategory.SECURITY)
        if not target.exists():
            return None
        size = target.stat().st_size
        if size <= 0 or size > _MAX_TRANSACTION_BYTES:
            raise ProductError("ERR_CONTINUITY_TRANSACTION_SIZE", "Continuity transaction size is outside the allowed bound", ProductErrorCategory.DATA_INTEGRITY)
        try:
            value = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_CONTINUITY_TRANSACTION_READ", "Continuity transaction could not be read", ProductErrorCategory.DATA_INTEGRITY) from exc
        self._validate_transaction(value)
        if value["project_id"] != self.project_id:
            raise ProductError("ERR_CONTINUITY_TRANSACTION_PROJECT_MISMATCH", "Continuity transaction belongs to another project", ProductErrorCategory.DATA_INTEGRITY)
        return value

    @staticmethod
    def _edge_from_dict(raw: dict[str, Any]) -> ContinuityEdge:
        try:
            if not isinstance(raw, dict) or set(raw) != _EDGE_FIELDS:
                raise ValueError("Continuity Edge fields are not exact")
            if not isinstance(raw["character_contract_refs"], list) or not isinstance(raw["space_contract_refs"], list):
                raise ValueError("Continuity Edge contract refs must be arrays")
            if not all(isinstance(item, str) for item in raw["character_contract_refs"] + raw["space_contract_refs"]):
                raise ValueError("Continuity Edge contract refs must be text")
            return ContinuityEdge(
                edge_id=raw["edge_id"], from_scene_id=raw["from_scene_id"],
                from_slot_id=raw["from_slot_id"], from_candidate_id=raw["from_candidate_id"],
                from_asset_id=raw["from_asset_id"], from_asset_sha256=raw["from_asset_sha256"],
                to_scene_id=raw["to_scene_id"], to_slot_id=raw["to_slot_id"],
                boundary_type=ContinuityBoundaryType(raw["boundary_type"]),
                character_contract_refs=tuple(raw["character_contract_refs"]),
                space_contract_refs=tuple(raw["space_contract_refs"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProductError("ERR_CONTINUITY_TRANSACTION_EDGE_INVALID", "Continuity transaction Edge is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc

    @staticmethod
    def _recovery_state(transaction: dict[str, Any] | None, continuity_sha: str, production_sha: str) -> dict[str, Any]:
        if transaction is None or transaction["state"] != "PREPARED":
            return {"required": False, "state": None, "available_actions": []}
        old_c, new_c = transaction["old_continuity_sha256"], transaction["new_continuity_sha256"]
        old_p, new_p = transaction["old_production_sha256"], transaction["new_production_sha256"]
        if continuity_sha == old_c and production_sha == old_p:
            state, actions = "OLD_OLD", ["COMPLETE", "ABANDON"]
        elif continuity_sha == new_c and production_sha == old_p:
            state, actions = "CONTINUITY_NEW_PRODUCTION_OLD", ["COMPLETE"]
        elif continuity_sha == old_c and production_sha == new_p:
            state, actions = "CONTINUITY_OLD_PRODUCTION_NEW", ["COMPLETE"]
        elif continuity_sha == new_c and production_sha == new_p:
            state, actions = "NEW_NEW", ["FINALIZE"]
        else:
            state, actions = "UNKNOWN_MIXTURE", []
        return {"required": True, "state": state, "transaction_id": transaction["transaction_id"], "edge_id": transaction["edge"]["edge_id"], "available_actions": actions}

    def snapshot(self) -> dict[str, Any]:
        production, production_sha, production_persisted = self._load_production()
        continuity, continuity_sha, continuity_persisted = self._load_continuity()
        recovery = self._recovery_state(self._load_transaction(), continuity_sha, production_sha)
        workspace = Task039ContinuityWorkspaceProjection.build(continuity=continuity, production=production)
        for row in workspace["edges"]:
            resolution = row["resolution"]
            row["generation_safe"] = (
                not recovery["required"]
                and row["target_slot_status"] != "STALE"
                and resolution is not None
                and resolution["status"] in {"PASS", "HUMAN_APPROVED"}
            )
            if recovery["required"]:
                row["human_soft_approval_available"] = False
        return {
            "application_version": "1.0.0", "task_owner": "TASK-039", "project_id": self.project_id,
            "production_snapshot_sha256": production_sha, "continuity_snapshot_sha256": continuity_sha,
            "production_persisted": production_persisted, "continuity_persisted": continuity_persisted,
            "recovery": recovery, "workspace": workspace,
            "automatic_regeneration_started": False, "physical_delete_requested": False,
            "provider_execution_started": False, "resolve_mutation_started": False,
        }

    @staticmethod
    def _derive_edge(
        production: ProductionControlRegistry,
        *, edge_id: str, from_slot_id: str, to_slot_id: str, boundary_type: str,
        character_contract_refs: tuple[str, ...], space_contract_refs: tuple[str, ...],
    ) -> ContinuityEdge:
        source_slot = production.slots.get(from_slot_id)
        target_slot = production.slots.get(to_slot_id)
        if source_slot is None or target_slot is None:
            raise ProductError("ERR_CONTINUITY_APPLICATION_SLOT_NOT_FOUND", "Continuity Edge Slots must exist in Production Control", ProductErrorCategory.STATE)
        if source_slot.project_id != target_slot.project_id or source_slot.scene_id == target_slot.scene_id:
            raise ProductError("ERR_CONTINUITY_APPLICATION_SCENE_SCOPE", "Continuity Edge must connect distinct Scenes in the same project", ProductErrorCategory.DATA_INTEGRITY)
        if source_slot.slot_kind is not SlotKind.END_FRAME or target_slot.slot_kind is not SlotKind.START_FRAME:
            raise ProductError("ERR_CONTINUITY_APPLICATION_SLOT_KIND", "Continuity Edge must connect END_FRAME to START_FRAME", ProductErrorCategory.DATA_INTEGRITY)
        if source_slot.status is not SlotStatus.LOCKED or source_slot.locked_candidate_id is None:
            raise ProductError("ERR_CONTINUITY_APPLICATION_SOURCE_NOT_LOCKED", "Continuity source End Slot must be locked", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        source = production.candidates.get(source_slot.locked_candidate_id)
        if source is None or source.lifecycle_state is not CandidateLifecycle.LOCKED:
            raise ProductError("ERR_CONTINUITY_APPLICATION_SOURCE_MISMATCH", "Continuity source locked Candidate is inconsistent", ProductErrorCategory.DATA_INTEGRITY)
        try:
            kind = ContinuityBoundaryType(boundary_type)
        except ValueError as exc:
            raise ProductError("ERR_CONTINUITY_APPLICATION_BOUNDARY_INVALID", "Continuity boundary type is invalid", ProductErrorCategory.VALIDATION) from exc
        return ContinuityEdge(
            edge_id=edge_id, from_scene_id=source_slot.scene_id, from_slot_id=source_slot.slot_id,
            from_candidate_id=source.candidate_id, from_asset_id=source.asset_id,
            from_asset_sha256=source.asset_sha256, to_scene_id=target_slot.scene_id,
            to_slot_id=target_slot.slot_id, boundary_type=kind,
            character_contract_refs=character_contract_refs, space_contract_refs=space_contract_refs,
        )

    def prepare_register_edge(
        self, *, edge_id: str, from_slot_id: str, to_slot_id: str, boundary_type: str,
        character_contract_refs: tuple[str, ...], space_contract_refs: tuple[str, ...],
        expected_production_snapshot_sha256: str, expected_continuity_snapshot_sha256: str,
    ) -> dict[str, Any]:
        production, production_sha, _ = self._load_production()
        continuity, continuity_sha, _ = self._load_continuity()
        self._require_expected(production_sha, expected_production_snapshot_sha256, "Production")
        self._require_expected(continuity_sha, expected_continuity_snapshot_sha256, "Continuity")
        if self._recovery_state(self._load_transaction(), continuity_sha, production_sha)["required"]:
            raise ProductError("ERR_CONTINUITY_APPLICATION_RECOVERY_REQUIRED", "Complete Continuity recovery before registering another Edge", ProductErrorCategory.STATE)
        edge = self._derive_edge(
            production, edge_id=edge_id, from_slot_id=from_slot_id, to_slot_id=to_slot_id,
            boundary_type=boundary_type, character_contract_refs=character_contract_refs,
            space_contract_refs=space_contract_refs,
        )
        continuity.add_edge(edge)
        ContinuityProductionControlBinding.bind(production, edge)
        token = self._new_token(self._edge_confirmations)
        pending = _PendingEdge(token, edge, continuity_sha, self._continuity_hash(continuity), production_sha, self._production_hash(production))
        self._edge_confirmations[token] = pending
        return {
            "confirmation_version": "1.0.0", "task_owner": "TASK-039", "confirmation_id": token,
            "project_id": self.project_id, "edge": edge.to_dict(),
            "old_continuity_sha256": pending.old_continuity_sha256, "new_continuity_sha256": pending.new_continuity_sha256,
            "old_production_sha256": pending.old_production_sha256, "new_production_sha256": pending.new_production_sha256,
            "human_final_authority_required": True, "automatic_regeneration_started": False,
        }

    def _inject(self, stage: str) -> None:
        if self._failure_injector is not None:
            self._failure_injector(stage)

    def apply_register_edge(self, *, confirmation_id: str) -> dict[str, Any]:
        pending = self._edge_confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError("ERR_CONTINUITY_APPLICATION_CONFIRMATION_INVALID", "Continuity Edge confirmation is missing or already used", ProductErrorCategory.AUTHORIZATION)
        pending.consumed = True
        with _exclusive_snapshot_lock(self.transaction_path):
            production, production_sha, production_persisted = self._load_production()
            continuity, continuity_sha, continuity_persisted = self._load_continuity()
            self._require_expected(production_sha, pending.old_production_sha256, "Production")
            self._require_expected(continuity_sha, pending.old_continuity_sha256, "Continuity")
            if self._recovery_state(self._load_transaction(), continuity_sha, production_sha)["required"]:
                raise ProductError("ERR_CONTINUITY_APPLICATION_RECOVERY_REQUIRED", "Complete Continuity recovery before applying another Edge", ProductErrorCategory.STATE)
            continuity.add_edge(pending.edge)
            ContinuityProductionControlBinding.bind(production, pending.edge)
            if self._continuity_hash(continuity) != pending.new_continuity_sha256 or self._production_hash(production) != pending.new_production_sha256:
                raise ProductError("ERR_CONTINUITY_APPLICATION_CONFIRMATION_STALE", "Continuity Edge result changed after preparation", ProductErrorCategory.AUTHORIZATION)
            transaction = self._write_transaction({
                "transaction_version": "1.0.0", "task_owner": "TASK-039",
                "transaction_id": "txn-" + sha256_bytes(confirmation_id.encode("utf-8"))[7:31],
                "project_id": self.project_id, "state": "PREPARED",
                "confirmation_id_sha256": sha256_bytes(confirmation_id.encode("utf-8")), "edge": pending.edge.to_dict(),
                "old_continuity_sha256": continuity_sha, "new_continuity_sha256": pending.new_continuity_sha256,
                "old_production_sha256": production_sha, "new_production_sha256": pending.new_production_sha256,
            })
            self._inject("after_transaction_prepare")
            ContinuityRegistryStore.save(self.continuity_path, continuity, expected_previous_registry_sha256=continuity_sha if continuity_persisted else None)
            self._inject("after_continuity_save")
            ProductionControlSnapshotStore.save(self.production_control.snapshot_path, production, expected_previous_snapshot_sha256=production_sha if production_persisted else None)
            self._inject("after_production_save")
            transaction["state"] = "COMMITTED"
            self._write_transaction(transaction)
        return self.snapshot()

    def inspect_locked_target(
        self, *, edge_id: str, expected_production_snapshot_sha256: str,
        expected_continuity_snapshot_sha256: str,
    ) -> dict[str, Any]:
        with _exclusive_snapshot_lock(self.transaction_path):
            production, production_sha, _ = self._load_production()
            continuity, continuity_sha, continuity_persisted = self._load_continuity()
            self._require_expected(production_sha, expected_production_snapshot_sha256, "Production")
            self._require_expected(continuity_sha, expected_continuity_snapshot_sha256, "Continuity")
            if self._recovery_state(self._load_transaction(), continuity_sha, production_sha)["required"]:
                raise ProductError("ERR_CONTINUITY_APPLICATION_RECOVERY_REQUIRED", "Complete Continuity recovery before inspection", ProductErrorCategory.STATE)
            edge = continuity.edges.get(edge_id)
            if edge is None:
                raise ProductError("ERR_CONTINUITY_EDGE_NOT_FOUND", "Continuity Edge does not exist", ProductErrorCategory.STATE)
            if edge_id in continuity.resolutions:
                raise ProductError("ERR_CONTINUITY_APPLICATION_ALREADY_INSPECTED", "Immutable Continuity Edge already has inspection Evidence", ProductErrorCategory.STATE)
            slot = production.slots.get(edge.to_slot_id)
            candidate = None if slot is None or slot.locked_candidate_id is None else production.candidates.get(slot.locked_candidate_id)
            if slot is None or slot.status is not SlotStatus.LOCKED or candidate is None or candidate.lifecycle_state is not CandidateLifecycle.LOCKED:
                raise ProductError("ERR_CONTINUITY_APPLICATION_TARGET_NOT_LOCKED", "Continuity target Start Slot must have an exact locked Candidate", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
            resolution = continuity.inspect_target(edge_id, target_asset_id=candidate.asset_id, target_asset_sha256=candidate.asset_sha256)
            ContinuityRegistryStore.save(self.continuity_path, continuity, expected_previous_registry_sha256=continuity_sha if continuity_persisted else None)
        return {"resolution": resolution.to_dict(), "application": self.snapshot()}

    def prepare_soft_approval(
        self, *, edge_id: str, expected_production_snapshot_sha256: str,
        expected_continuity_snapshot_sha256: str,
    ) -> dict[str, Any]:
        production, production_sha, _ = self._load_production()
        continuity, continuity_sha, _ = self._load_continuity()
        self._require_expected(production_sha, expected_production_snapshot_sha256, "Production")
        self._require_expected(continuity_sha, expected_continuity_snapshot_sha256, "Continuity")
        if self._recovery_state(self._load_transaction(), continuity_sha, production_sha)["required"]:
            raise ProductError("ERR_CONTINUITY_APPLICATION_RECOVERY_REQUIRED", "Complete Continuity recovery before Human approval", ProductErrorCategory.STATE)
        token = self._new_token(self._soft_confirmations)
        service = Task039ContinuityWorkspaceService(continuity=continuity, production=production, token_factory=lambda: token)
        prepared = service.prepare_soft_approval(edge_id=edge_id)
        self._soft_confirmations[token] = _PendingSoftApproval(token, edge_id, continuity_sha, production_sha)
        return {**prepared, "project_id": self.project_id, "continuity_snapshot_sha256": continuity_sha, "production_snapshot_sha256": production_sha}

    def apply_soft_approval(self, *, confirmation_id: str, approved_by: str) -> dict[str, Any]:
        pending = self._soft_confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError("ERR_CONTINUITY_APPLICATION_SOFT_CONFIRMATION_INVALID", "Continuity soft approval is missing or already used", ProductErrorCategory.AUTHORIZATION)
        pending.consumed = True
        with _exclusive_snapshot_lock(self.transaction_path):
            production, production_sha, _ = self._load_production()
            continuity, continuity_sha, continuity_persisted = self._load_continuity()
            self._require_expected(production_sha, pending.production_sha256, "Production")
            self._require_expected(continuity_sha, pending.continuity_sha256, "Continuity")
            if self._recovery_state(self._load_transaction(), continuity_sha, production_sha)["required"]:
                raise ProductError("ERR_CONTINUITY_APPLICATION_RECOVERY_REQUIRED", "Complete Continuity recovery before Human approval", ProductErrorCategory.STATE)
            service = Task039ContinuityWorkspaceService(continuity=continuity, production=production, token_factory=lambda: confirmation_id)
            service.prepare_soft_approval(edge_id=pending.edge_id)
            result = service.apply_soft_approval(confirmation_id=confirmation_id, approved_by=approved_by)
            ContinuityRegistryStore.save(self.continuity_path, continuity, expected_previous_registry_sha256=continuity_sha if continuity_persisted else None)
        return {**result, "application": self.snapshot()}

    def propagate_stale(
        self, *, root_slot_id: str, expected_production_snapshot_sha256: str,
        expected_continuity_snapshot_sha256: str,
    ) -> dict[str, Any]:
        with _exclusive_snapshot_lock(self.transaction_path):
            production, production_sha, production_persisted = self._load_production()
            continuity, continuity_sha, _ = self._load_continuity()
            self._require_expected(production_sha, expected_production_snapshot_sha256, "Production")
            self._require_expected(continuity_sha, expected_continuity_snapshot_sha256, "Continuity")
            if self._recovery_state(self._load_transaction(), continuity_sha, production_sha)["required"]:
                raise ProductError("ERR_CONTINUITY_APPLICATION_RECOVERY_REQUIRED", "Complete Continuity recovery before STALE propagation", ProductErrorCategory.STATE)
            if root_slot_id not in production.slots or not any(edge.from_slot_id == root_slot_id for edge in continuity.edges.values()):
                raise ProductError("ERR_CONTINUITY_APPLICATION_STALE_ROOT_INVALID", "STALE root must be a registered Continuity source Slot", ProductErrorCategory.STATE)
            result = production.mark_stale(EntityRef(EntityType.SLOT, root_slot_id), include_root=True)
            ProductionControlSnapshotStore.save(self.production_control.snapshot_path, production, expected_previous_snapshot_sha256=production_sha if production_persisted else None)
        return {"propagation": result.to_dict(), "application": self.snapshot(), "automatic_regeneration_started": False}

    def apply_recovery(self, *, action: str) -> dict[str, Any]:
        with _exclusive_snapshot_lock(self.transaction_path):
            transaction = self._load_transaction()
            if transaction is None or transaction["state"] != "PREPARED":
                raise ProductError("ERR_CONTINUITY_RECOVERY_NOT_REQUIRED", "No prepared Continuity transaction requires recovery", ProductErrorCategory.STATE)
            production, production_sha, production_persisted = self._load_production()
            continuity, continuity_sha, continuity_persisted = self._load_continuity()
            recovery = self._recovery_state(transaction, continuity_sha, production_sha)
            if action not in recovery["available_actions"]:
                raise ProductError("ERR_CONTINUITY_RECOVERY_ACTION_INVALID", "Recovery action is not allowed for the exact persisted state", ProductErrorCategory.AUTHORIZATION, details={"recovery_state": recovery["state"]})
            if action == "ABANDON":
                transaction["state"] = "ABANDONED"; self._write_transaction(transaction); return self.snapshot()
            if action == "FINALIZE":
                transaction["state"] = "COMMITTED"; self._write_transaction(transaction); return self.snapshot()
            edge = self._edge_from_dict(transaction["edge"])
            old_c, new_c = transaction["old_continuity_sha256"], transaction["new_continuity_sha256"]
            old_p, new_p = transaction["old_production_sha256"], transaction["new_production_sha256"]
            if continuity_sha == old_c:
                continuity.add_edge(edge)
            if production_sha == old_p:
                ContinuityProductionControlBinding.bind(production, edge)
            if self._continuity_hash(continuity) != new_c or self._production_hash(production) != new_p:
                raise ProductError("ERR_CONTINUITY_RECOVERY_RESULT_MISMATCH", "Recovered Continuity state does not match the prepared result", ProductErrorCategory.DATA_INTEGRITY)
            if continuity_sha == old_c:
                ContinuityRegistryStore.save(self.continuity_path, continuity, expected_previous_registry_sha256=continuity_sha if continuity_persisted else None)
            if production_sha == old_p:
                ProductionControlSnapshotStore.save(self.production_control.snapshot_path, production, expected_previous_snapshot_sha256=production_sha if production_persisted else None)
            transaction["state"] = "COMMITTED"
            self._write_transaction(transaction)
        return self.snapshot()


__all__ = ["Task039ContinuityApplication"]
