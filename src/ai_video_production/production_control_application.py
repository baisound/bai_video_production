"""TASK-037 durable Product Application Service.

Every durable command reloads the current canonical snapshot, checks the exact
caller-visible checksum and publishes through the existing atomic CAS store.  A
failed save therefore cannot leave an authoritative long-lived in-memory state.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import secrets
from typing import Any, Callable

from .approved_plan_orchestration import ApprovedPlanProductionControlInstaller
from .errors import ProductError, ProductErrorCategory
from .production_control import (
    AssetCandidate,
    CandidateLifecycle,
    ProductionControlRegistry,
)
from .production_control_store import ProductionControlSnapshotStore
from .production_blueprint import ProductionBlueprint
from .production_blueprint_v2 import ProductionBlueprintV2
from .production_proposal import ProductionProposalRegistry
from .task037_production_workspace import Task037ProductionWorkspaceProjection


TokenFactory = Callable[[], str]
_SNAPSHOT_NAME = "production-control.json"


@dataclass(slots=True)
class _LockConfirmation:
    confirmation_id: str
    project_id: str
    snapshot_sha256: str
    slot_id: str
    slot_revision: int
    candidate_id: str
    asset_sha256: str
    consumed: bool = False


class Task037ProductionControlApplication:
    def __init__(
        self,
        *,
        project_root: str | Path,
        project_id: str,
        token_factory: TokenFactory | None = None,
    ) -> None:
        root = Path(project_root)
        if root.is_symlink() or not root.is_dir():
            raise ProductError(
                "ERR_PRODUCTION_APPLICATION_PROJECT_ROOT_INVALID",
                "Production Control project root must be an existing regular directory",
                ProductErrorCategory.VALIDATION,
            )
        if not isinstance(project_id, str) or not project_id.strip():
            raise ProductError(
                "ERR_PRODUCTION_APPLICATION_PROJECT_ID_INVALID",
                "Production Control project_id must be non-empty text",
                ProductErrorCategory.VALIDATION,
            )
        self.project_root = root
        self.project_id = project_id
        self.snapshot_path = root / _SNAPSHOT_NAME
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._confirmations: dict[str, _LockConfirmation] = {}

    @staticmethod
    def _snapshot_hash(registry: ProductionControlRegistry) -> str:
        return ProductionControlSnapshotStore.snapshot(registry)["snapshot_sha256"]

    def _require_project_scope(self, registry: ProductionControlRegistry) -> None:
        foreign = sorted(
            slot.slot_id for slot in registry.slots.values() if slot.project_id != self.project_id
        )
        if foreign:
            raise ProductError(
                "ERR_PRODUCTION_APPLICATION_PROJECT_MISMATCH",
                "Production Control snapshot contains Slots from another project",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"foreign_slot_ids": foreign},
            )

    def _load(self) -> tuple[ProductionControlRegistry, str, bool]:
        if self.snapshot_path.is_symlink():
            raise ProductError(
                "ERR_PRODUCTION_SNAPSHOT_FILE_INVALID",
                "Production Control snapshot cannot be a symlink",
                ProductErrorCategory.SECURITY,
            )
        if self.snapshot_path.exists():
            registry = ProductionControlSnapshotStore.load(self.snapshot_path)
            self._require_project_scope(registry)
            return registry, self._snapshot_hash(registry), True
        registry = ProductionControlRegistry()
        return registry, self._snapshot_hash(registry), False

    @staticmethod
    def _require_expected(actual: str, expected: str) -> None:
        if not isinstance(expected, str) or expected != actual:
            raise ProductError(
                "ERR_PRODUCTION_APPLICATION_SNAPSHOT_CONFLICT",
                "Production Control changed; reload before applying the command",
                ProductErrorCategory.STATE,
                details={"current_snapshot_sha256": actual},
            )

    def _save(
        self,
        registry: ProductionControlRegistry,
        *,
        previous_sha256: str,
        previously_persisted: bool,
    ) -> None:
        ProductionControlSnapshotStore.save(
            self.snapshot_path,
            registry,
            expected_previous_snapshot_sha256=previous_sha256 if previously_persisted else None,
        )

    def snapshot(self) -> dict[str, Any]:
        registry, snapshot_sha, persisted = self._load()
        return Task037ProductionWorkspaceProjection.build(
            registry=registry,
            project_id=self.project_id,
            snapshot_sha256=snapshot_sha,
            persisted=persisted,
        )

    def install_approved_plan(
        self,
        *,
        proposal_registry: ProductionProposalRegistry,
        plan_id: str,
        blueprint: ProductionBlueprint | ProductionBlueprintV2,
        expected_snapshot_sha256: str,
    ) -> dict[str, Any]:
        registry, current_sha, persisted = self._load()
        self._require_expected(current_sha, expected_snapshot_sha256)
        control_plan = ApprovedPlanProductionControlInstaller.install(
            proposal_registry=proposal_registry,
            plan_id=plan_id,
            blueprint=blueprint,
            project_id=self.project_id,
            production_registry=registry,
        )
        self._save(registry, previous_sha256=current_sha, previously_persisted=persisted)
        return {"control_plan": control_plan.to_dict(), "workspace": self.snapshot()}

    def register_candidate(
        self,
        *,
        candidate_id: str,
        slot_id: str,
        asset_id: str,
        asset_sha256: str,
        expected_snapshot_sha256: str,
        generation_job_id: str | None = None,
        parent_candidate_id: str | None = None,
        supersedes: str | None = None,
    ) -> dict[str, Any]:
        registry, current_sha, persisted = self._load()
        self._require_expected(current_sha, expected_snapshot_sha256)
        for field, reference in (
            ("parent_candidate_id", parent_candidate_id),
            ("supersedes", supersedes),
        ):
            if reference is None:
                continue
            prior = registry.candidates.get(reference)
            if prior is None or prior.slot_id != slot_id:
                raise ProductError(
                    "ERR_PRODUCTION_APPLICATION_CANDIDATE_LINEAGE_INVALID",
                    "Candidate lineage must reference an existing Candidate in the same Slot",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"field": field, "reference": reference},
                )
        versions = [item.candidate_version for item in registry.candidates.values() if item.slot_id == slot_id]
        candidate = AssetCandidate(
            candidate_id=candidate_id,
            slot_id=slot_id,
            asset_id=asset_id,
            asset_sha256=asset_sha256,
            candidate_version=(max(versions) + 1) if versions else 1,
            generation_job_id=generation_job_id,
            parent_candidate_id=parent_candidate_id,
            supersedes=supersedes,
        )
        registry.add_candidate(candidate)
        self._save(registry, previous_sha256=current_sha, previously_persisted=persisted)
        return {"candidate": candidate.to_dict(), "workspace": self.snapshot()}

    def mark_ready_for_audit(
        self,
        *,
        candidate_id: str,
        expected_snapshot_sha256: str,
    ) -> dict[str, Any]:
        registry, current_sha, persisted = self._load()
        self._require_expected(current_sha, expected_snapshot_sha256)
        candidate = registry.transition_candidate(candidate_id, CandidateLifecycle.READY_FOR_AUDIT)
        self._save(registry, previous_sha256=current_sha, previously_persisted=persisted)
        return {"candidate": candidate.to_dict(), "workspace": self.snapshot()}

    def prepare_lock(
        self,
        *,
        slot_id: str,
        candidate_id: str,
        expected_snapshot_sha256: str,
    ) -> dict[str, Any]:
        registry, current_sha, _ = self._load()
        self._require_expected(current_sha, expected_snapshot_sha256)
        slot = registry.slots.get(slot_id)
        candidate = registry.candidates.get(candidate_id)
        if slot is None or candidate is None or candidate.slot_id != slot_id:
            raise ProductError(
                "ERR_PRODUCTION_LOCK_TARGET_INVALID",
                "Slot/Candidate lock target is invalid",
                ProductErrorCategory.STATE,
            )
        if candidate.lifecycle_state is not CandidateLifecycle.ACCEPTED:
            raise ProductError(
                "ERR_PRODUCTION_CANDIDATE_NOT_ACCEPTED",
                "TASK-038 Human ACCEPT is required before preparing a lock",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        token = self._token_factory()
        if not isinstance(token, str) or not token.strip() or token in self._confirmations:
            raise ProductError(
                "ERR_PRODUCTION_APPLICATION_CONFIRMATION_TOKEN_INVALID",
                "Production lock confirmation token factory returned an invalid token",
                ProductErrorCategory.INTERNAL,
            )
        pending = _LockConfirmation(
            confirmation_id=token,
            project_id=self.project_id,
            snapshot_sha256=current_sha,
            slot_id=slot.slot_id,
            slot_revision=slot.revision,
            candidate_id=candidate.candidate_id,
            asset_sha256=candidate.asset_sha256,
        )
        self._confirmations[token] = pending
        return {
            "confirmation_version": "1.0.0",
            "task_owner": "TASK-037",
            "confirmation_id": token,
            "project_id": self.project_id,
            "snapshot_sha256": current_sha,
            "slot_id": slot.slot_id,
            "slot_revision": slot.revision,
            "candidate_id": candidate.candidate_id,
            "asset_id": candidate.asset_id,
            "asset_sha256": candidate.asset_sha256,
            "human_final_authority_required": True,
            "physical_delete_requested": False,
            "provider_execution_started": False,
            "resolve_mutation_started": False,
        }

    def apply_lock(self, *, confirmation_id: str) -> dict[str, Any]:
        pending = self._confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError(
                "ERR_PRODUCTION_APPLICATION_CONFIRMATION_INVALID",
                "Production lock confirmation is missing or already used",
                ProductErrorCategory.AUTHORIZATION,
            )
        # A Human-final confirmation is one-shot even when the attempt fails
        # because state changed after preparation.  Never allow a stale token
        # to become valid again after a later state restoration.
        pending.consumed = True
        registry, current_sha, persisted = self._load()
        slot = registry.slots.get(pending.slot_id)
        candidate = registry.candidates.get(pending.candidate_id)
        if (
            pending.project_id != self.project_id
            or current_sha != pending.snapshot_sha256
            or slot is None
            or candidate is None
            or candidate.slot_id != pending.slot_id
            or slot.revision != pending.slot_revision
            or candidate.asset_sha256 != pending.asset_sha256
            or candidate.lifecycle_state is not CandidateLifecycle.ACCEPTED
        ):
            raise ProductError(
                "ERR_PRODUCTION_APPLICATION_CONFIRMATION_STALE",
                "Production state changed after the Human lock confirmation was prepared",
                ProductErrorCategory.AUTHORIZATION,
            )
        locked = registry.lock_candidate(
            slot_id=pending.slot_id,
            candidate_id=pending.candidate_id,
            expected_revision=pending.slot_revision,
        )
        self._save(registry, previous_sha256=current_sha, previously_persisted=persisted)
        return {"slot": locked.to_dict(), "workspace": self.snapshot()}
