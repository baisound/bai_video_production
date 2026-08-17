"""TASK-027 project-scoped Planning Workspace Product application.

The service promotes persisted Proposal/Scene state into the trusted Desktop
Shell. Human GO and Approved Plan -> Production Control installation are exact,
separate one-shot operations. Neither operation starts a Provider or NLE.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import secrets
from typing import Any, Callable, Iterable

from .approved_plan_orchestration import ApprovedPlanProductionControlInstaller, ApprovedPlanVerifier
from .approved_plan_trace import ApprovedPlanTraceValidator
from .blueprint_v2_world_lock import BlueprintV2WorldLockService
from .errors import ProductError, ProductErrorCategory
from .planning_workspace import Task027PlanningWorkspaceProjection, Task027PlanningWorkspaceService
from .production_control import EntityType, ProductionControlRegistry
from .production_blueprint_v2 import ProductionBlueprintV2
from .production_control_application import Task037ProductionControlApplication
from .production_control_store import ProductionControlSnapshotStore, _exclusive_snapshot_lock
from .production_proposal import (
    ProductionGoApprovalService,
    ProductionProposalRegistry,
    ProductionProposalRevision,
    ProposalSection,
    ReferenceAssetBinding,
)
from .production_proposal_store import ProductionProposalSnapshotStore


TokenFactory = Callable[[], str]
_PROPOSAL_NAME = "production-proposal.json"
_APPLICATION_LOCK_NAME = "task027-planning-application.json"


@dataclass(slots=True)
class _GoConfirmation:
    confirmation_id: str
    snapshot_sha256: str
    proposal_id: str
    proposal_revision: int
    reference_bindings: tuple[ReferenceAssetBinding, ...]
    cost_ceiling: str
    rights_warnings_acknowledged: bool
    consumed: bool = False


@dataclass(slots=True)
class _InstallConfirmation:
    confirmation_id: str
    proposal_snapshot_sha256: str
    production_snapshot_sha256: str
    plan_id: str
    proposal_id: str
    blueprint_sha256: str
    consumed: bool = False


@dataclass(slots=True)
class _RevisionConfirmation:
    confirmation_id: str
    snapshot_sha256: str
    proposal_id: str
    parent_proposal_sha256: str
    sections: tuple[ProposalSection, ...]
    consumed: bool = False


class Task027PlanningApplication:
    """Durable Planning/GO facade bound to one trusted Product project."""

    def __init__(
        self,
        *,
        project_root: str | Path,
        project_id: str,
        production_control: Task037ProductionControlApplication | None = None,
        token_factory: TokenFactory | None = None,
    ) -> None:
        root = Path(project_root)
        if root.is_symlink() or not root.is_dir():
            raise ProductError(
                "ERR_PLANNING_APPLICATION_PROJECT_ROOT_INVALID",
                "Planning project root must be an existing regular directory",
                ProductErrorCategory.VALIDATION,
            )
        if not isinstance(project_id, str) or not project_id.strip():
            raise ProductError(
                "ERR_PLANNING_APPLICATION_PROJECT_ID_INVALID",
                "Planning project_id must be non-empty text",
                ProductErrorCategory.VALIDATION,
            )
        if production_control is not None and (
            production_control.project_root != root or production_control.project_id != project_id
        ):
            raise ProductError(
                "ERR_PLANNING_APPLICATION_PRODUCTION_SCOPE_MISMATCH",
                "Planning and Production Control must use the same project root/id",
                ProductErrorCategory.SECURITY,
            )
        self.project_root = root
        self.project_id = project_id
        self.proposal_path = root / _PROPOSAL_NAME
        self._application_lock_target = root / _APPLICATION_LOCK_NAME
        self.production_control = production_control or Task037ProductionControlApplication(
            project_root=root,
            project_id=project_id,
        )
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._go_confirmations: dict[str, _GoConfirmation] = {}
        self._install_confirmations: dict[str, _InstallConfirmation] = {}
        self._revision_confirmations: dict[str, _RevisionConfirmation] = {}

    @staticmethod
    def _snapshot_hash(registry: ProductionProposalRegistry) -> str:
        return str(ProductionProposalSnapshotStore.snapshot(registry)["snapshot_sha256"])

    def _load(self) -> tuple[ProductionProposalRegistry, str, bool]:
        if self.proposal_path.is_symlink():
            raise ProductError("ERR_PROPOSAL_SNAPSHOT_FILE_INVALID", "Proposal snapshot cannot be a symlink", ProductErrorCategory.SECURITY)
        if self.proposal_path.exists():
            registry = ProductionProposalSnapshotStore.load(self.proposal_path)
            return registry, self._snapshot_hash(registry), True
        registry = ProductionProposalRegistry()
        return registry, self._snapshot_hash(registry), False

    @staticmethod
    def _require_expected(actual: str, expected: str, kind: str) -> None:
        if not isinstance(expected, str) or actual != expected:
            raise ProductError(
                "ERR_PLANNING_APPLICATION_SNAPSHOT_CONFLICT",
                f"{kind} snapshot changed; reload before applying the command",
                ProductErrorCategory.STATE,
                details={"snapshot_kind": kind, "current_snapshot_sha256": actual},
            )

    def _new_token(self, existing: dict[str, Any]) -> str:
        token = self._token_factory()
        if not isinstance(token, str) or not token.strip() or token in existing:
            raise ProductError(
                "ERR_PLANNING_APPLICATION_CONFIRMATION_TOKEN_INVALID",
                "Planning confirmation token is invalid",
                ProductErrorCategory.INTERNAL,
            )
        return token

    @staticmethod
    def _bindings(values: Iterable[dict[str, Any]]) -> tuple[ReferenceAssetBinding, ...]:
        try:
            rows = tuple(
                ReferenceAssetBinding(
                    reference_id=str(item["reference_id"]),
                    asset_id=str(item["asset_id"]),
                    asset_sha256=str(item["asset_sha256"]),
                )
                for item in values
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_PLANNING_APPLICATION_REFERENCE_BINDING_INVALID",
                "GO reference bindings are invalid",
                ProductErrorCategory.VALIDATION,
            ) from exc
        return rows

    def _installation(self, registry: ProductionProposalRegistry, workspace: dict[str, Any]) -> dict[str, Any]:
        production_workspace = self.production_control.snapshot()
        plan_row = workspace.get("approved_plan")
        if plan_row is None:
            return {"status": "GO_REQUIRED", "trace": None, "production": production_workspace}
        plan_id = str(plan_row["plan_id"])
        plan = registry.approved_plans[plan_id]
        proposal = next(
            item for item in registry.proposals[plan.proposal_id]
            if item.revision == plan.proposal_revision
        )
        production = (
            ProductionControlSnapshotStore.load(self.production_control.snapshot_path)
            if self.production_control.snapshot_path.exists()
            else ProductionControlRegistry()
        )
        has_plan_edge = any(
            edge.from_ref.entity_type is EntityType.PLAN and edge.from_ref.entity_id == plan_id
            for edge in production.edges.values()
        )
        if not has_plan_edge:
            world_lock = None
            if isinstance(proposal.blueprint, ProductionBlueprintV2):
                world_lock = BlueprintV2WorldLockService.project(
                    blueprint=proposal.blueprint,
                    approved_plan=plan,
                    registry=production,
                    project_id=self.project_id,
                )
                expected_slot_ids = {
                    row.slot_id for row in BlueprintV2WorldLockService.requirements(proposal.blueprint)
                }
                unrelated = sorted(set(production.slots) - expected_slot_ids)
                status = (
                    "OTHER_PRODUCTION_STATE" if unrelated
                    else "NOT_INSTALLED" if world_lock["status"] == "PASS"
                    else "WORLD_LOCK_REQUIRED"
                )
                return {
                    "status": status,
                    "trace": None,
                    "world_lock": world_lock,
                    "unrelated_slot_ids": unrelated,
                    "production": production_workspace,
                }
            status = "NOT_INSTALLED" if not production.slots else "OTHER_PRODUCTION_STATE"
            return {"status": status, "trace": None, "world_lock": None, "production": production_workspace}
        world_lock = None
        if isinstance(proposal.blueprint, ProductionBlueprintV2):
            world_lock = BlueprintV2WorldLockService.project(
                blueprint=proposal.blueprint,
                approved_plan=plan,
                registry=production,
                project_id=self.project_id,
            )
            if world_lock["status"] != "PASS":
                return {
                    "status": "WORLD_LOCK_STALE",
                    "trace": None,
                    "world_lock": world_lock,
                    "production": production_workspace,
                }
        trace = ApprovedPlanTraceValidator.validate(
            proposals=registry,
            plan_id=plan_id,
            production=production,
            project_id=self.project_id,
        )
        return {
            "status": "INSTALLED",
            "trace": trace.to_dict(),
            "world_lock": world_lock,
            "production": production_workspace,
        }

    def snapshot(self, *, proposal_id: str | None = None) -> dict[str, Any]:
        registry, snapshot_sha, persisted = self._load()
        proposal_ids = sorted(registry.proposals)
        selected = proposal_id
        if selected is None and proposal_ids:
            selected = proposal_ids[0]
        if selected is not None and selected not in registry.proposals:
            raise ProductError(
                "ERR_PLANNING_WORKSPACE_PROPOSAL_NOT_FOUND",
                "Selected Planning proposal does not exist",
                ProductErrorCategory.STATE,
            )
        workspace = None if selected is None else Task027PlanningWorkspaceProjection.build(registry, proposal_id=selected)
        installation = None if workspace is None else self._installation(registry, workspace)
        return {
            "application_version": "1.0.0",
            "task_owner": "TASK-027",
            "project_id": self.project_id,
            "snapshot_sha256": snapshot_sha,
            "persisted": persisted,
            "proposal_ids": proposal_ids,
            "selected_proposal_id": selected,
            "workspace": workspace,
            "installation": installation,
            "provider_execution_started": False,
            "paid_execution_authorized": False,
            "budget_reservation_created": False,
            "resolve_mutation_started": False,
            "publish_started": False,
        }

    @staticmethod
    def _revision_sections(values: Iterable[dict[str, Any]]) -> tuple[ProposalSection, ...]:
        if not isinstance(values, (list, tuple)):
            raise ProductError(
                "ERR_PLANNING_APPLICATION_REVISION_SECTIONS_INVALID",
                "Proposal revision sections must be an exact bounded list",
                ProductErrorCategory.VALIDATION,
            )
        rows = tuple(values)
        if not rows or len(rows) > 64:
            raise ProductError(
                "ERR_PLANNING_APPLICATION_REVISION_SECTIONS_INVALID",
                "Proposal revision sections must contain 1..64 rows",
                ProductErrorCategory.VALIDATION,
            )
        try:
            if any(not isinstance(item, dict) or set(item) != {"section_id", "kind", "title", "body"} for item in rows):
                raise ValueError("section fields are invalid")
            return tuple(
                ProposalSection(
                    section_id=item["section_id"],
                    kind=item["kind"],
                    title=item["title"],
                    body=item["body"],
                )
                for item in rows
            )
        except (TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_PLANNING_APPLICATION_REVISION_SECTIONS_INVALID",
                "Proposal revision sections are invalid",
                ProductErrorCategory.VALIDATION,
            ) from exc

    @staticmethod
    def _revision_candidate(
        latest: ProductionProposalRevision,
        sections: tuple[ProposalSection, ...],
    ) -> ProductionProposalRevision:
        expected_identity = [(item.section_id, item.kind) for item in latest.sections]
        actual_identity = [(item.section_id, item.kind) for item in sections]
        if actual_identity != expected_identity:
            raise ProductError(
                "ERR_PLANNING_APPLICATION_REVISION_SECTION_IDENTITY",
                "Proposal revision must preserve exact section order, IDs and kinds",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if [item.to_dict() for item in sections] == [item.to_dict() for item in latest.sections]:
            raise ProductError(
                "ERR_PLANNING_APPLICATION_REVISION_NO_CHANGE",
                "Proposal revision must change at least one title or body",
                ProductErrorCategory.VALIDATION,
            )
        return ProductionProposalRevision(
            proposal_id=latest.proposal_id,
            revision=latest.revision + 1,
            intent_sha256=latest.intent_sha256,
            blueprint=latest.blueprint,
            sections=sections,
            provider_policy=latest.provider_policy,
            estimated_cost_min=latest.estimated_cost_min,
            estimated_cost_max=latest.estimated_cost_max,
            currency=latest.currency,
            rights_warnings=latest.rights_warnings,
            parent_proposal_sha256=latest.to_dict()["proposal_sha256"],
        )

    def prepare_revision(
        self,
        *,
        proposal_id: str,
        sections: Iterable[dict[str, Any]],
        expected_snapshot_sha256: str,
    ) -> dict[str, Any]:
        registry, snapshot_sha, _ = self._load()
        self._require_expected(snapshot_sha, expected_snapshot_sha256, "Proposal")
        latest = registry.latest_proposal(proposal_id)
        parsed = self._revision_sections(sections)
        candidate = self._revision_candidate(latest, parsed)
        token = self._new_token(self._revision_confirmations)
        self._revision_confirmations[token] = _RevisionConfirmation(
            token,
            snapshot_sha,
            proposal_id,
            str(candidate.parent_proposal_sha256),
            parsed,
        )
        return {
            "confirmation_version": "1.0.0",
            "task_owner": "TASK-027",
            "confirmation_id": token,
            "project_id": self.project_id,
            "proposal": candidate.to_dict(),
            "human_final_authority_required": True,
            "provider_execution_started": False,
            "paid_execution_authorized": False,
            "budget_reservation_created": False,
            "resolve_mutation_started": False,
            "publish_started": False,
        }

    def apply_revision(self, *, confirmation_id: str) -> dict[str, Any]:
        pending = self._revision_confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError(
                "ERR_PLANNING_APPLICATION_REVISION_CONFIRMATION_INVALID",
                "Proposal revision confirmation is missing or already used",
                ProductErrorCategory.AUTHORIZATION,
            )
        pending.consumed = True
        with _exclusive_snapshot_lock(self._application_lock_target):
            registry, snapshot_sha, persisted = self._load()
            self._require_expected(snapshot_sha, pending.snapshot_sha256, "Proposal")
            latest = registry.latest_proposal(pending.proposal_id)
            if latest.to_dict()["proposal_sha256"] != pending.parent_proposal_sha256:
                raise ProductError(
                    "ERR_PLANNING_APPLICATION_REVISION_PARENT_STALE",
                    "Proposal changed after revision preparation",
                    ProductErrorCategory.STATE,
                )
            candidate = self._revision_candidate(latest, pending.sections)
            registry.add_proposal(candidate)
            ProductionProposalSnapshotStore.save(
                self.proposal_path,
                registry,
                expected_previous_snapshot_sha256=snapshot_sha if persisted else None,
            )
        return {
            "proposal": candidate.to_dict(),
            "application": self.snapshot(proposal_id=pending.proposal_id),
            "provider_execution_started": False,
            "paid_execution_authorized": False,
            "budget_reservation_created": False,
            "resolve_mutation_started": False,
            "publish_started": False,
        }

    def prepare_go(
        self,
        *,
        proposal_id: str,
        proposal_revision: int,
        reference_bindings: Iterable[dict[str, Any]],
        cost_ceiling: str,
        rights_warnings_acknowledged: bool,
        expected_snapshot_sha256: str,
    ) -> dict[str, Any]:
        registry, snapshot_sha, _ = self._load()
        self._require_expected(snapshot_sha, expected_snapshot_sha256, "Proposal")
        bindings = self._bindings(reference_bindings)
        token = self._new_token(self._go_confirmations)
        service = Task027PlanningWorkspaceService(
            registry,
            go_service=ProductionGoApprovalService(registry, token_factory=lambda: token),
        )
        prepared = service.prepare_go(
            proposal_id=proposal_id,
            proposal_revision=proposal_revision,
            reference_bindings=bindings,
            cost_ceiling=cost_ceiling,
            rights_warnings_acknowledged=rights_warnings_acknowledged,
        )
        self._go_confirmations[token] = _GoConfirmation(
            token,
            snapshot_sha,
            proposal_id,
            proposal_revision,
            bindings,
            str(cost_ceiling),
            bool(rights_warnings_acknowledged),
        )
        return {**prepared, "project_id": self.project_id, "proposal_snapshot_sha256": snapshot_sha}

    def approve_go(self, *, confirmation_id: str, approved_by: str) -> dict[str, Any]:
        pending = self._go_confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError("ERR_PLANNING_APPLICATION_CONFIRMATION_INVALID", "GO confirmation is missing or already used", ProductErrorCategory.AUTHORIZATION)
        pending.consumed = True
        with _exclusive_snapshot_lock(self._application_lock_target):
            registry, snapshot_sha, persisted = self._load()
            self._require_expected(snapshot_sha, pending.snapshot_sha256, "Proposal")
            service = Task027PlanningWorkspaceService(
                registry,
                go_service=ProductionGoApprovalService(registry, token_factory=lambda: confirmation_id),
            )
            service.prepare_go(
                proposal_id=pending.proposal_id,
                proposal_revision=pending.proposal_revision,
                reference_bindings=pending.reference_bindings,
                cost_ceiling=pending.cost_ceiling,
                rights_warnings_acknowledged=pending.rights_warnings_acknowledged,
            )
            result = service.approve_go(confirmation_id=confirmation_id, approved_by=approved_by)
            ProductionProposalSnapshotStore.save(
                self.proposal_path,
                registry,
                expected_previous_snapshot_sha256=snapshot_sha if persisted else None,
            )
        return {**result, "application": self.snapshot(proposal_id=pending.proposal_id)}

    def prepare_install_plan(
        self,
        *,
        plan_id: str,
        expected_proposal_snapshot_sha256: str,
        expected_production_snapshot_sha256: str,
    ) -> dict[str, Any]:
        registry, proposal_sha, _ = self._load()
        self._require_expected(proposal_sha, expected_proposal_snapshot_sha256, "Proposal")
        plan = registry.approved_plans.get(plan_id)
        if plan is None:
            raise ProductError("ERR_APPROVED_PLAN_NOT_FOUND", "Plan installation requires a registered Approved Plan", ProductErrorCategory.AUTHORIZATION)
        proposal = next(
            (item for item in registry.proposals.get(plan.proposal_id, ()) if item.revision == plan.proposal_revision),
            None,
        )
        if proposal is None:
            raise ProductError("ERR_APPROVED_PLAN_PROPOSAL_MISSING", "Approved Plan proposal revision is missing", ProductErrorCategory.DATA_INTEGRITY)
        ApprovedPlanVerifier.require_current(proposal_registry=registry, plan_id=plan_id, blueprint=proposal.blueprint)
        production = self.production_control.snapshot()
        self._require_expected(str(production["snapshot_sha256"]), expected_production_snapshot_sha256, "Production")
        installation = self._installation(registry, Task027PlanningWorkspaceProjection.build(registry, proposal_id=plan.proposal_id))
        if installation["status"] == "INSTALLED":
            raise ProductError("ERR_PLANNING_APPLICATION_PLAN_ALREADY_INSTALLED", "Approved Plan is already installed exactly", ProductErrorCategory.STATE)
        if installation["status"] == "OTHER_PRODUCTION_STATE":
            raise ProductError("ERR_PLANNING_APPLICATION_PRODUCTION_NOT_EMPTY", "Existing Production Control state belongs to another/unbound Plan", ProductErrorCategory.STATE)
        if installation["status"] == "WORLD_LOCK_REQUIRED":
            raise ProductError(
                "ERR_PLANNING_APPLICATION_WORLD_LOCK_REQUIRED",
                "Blueprint v2 Plan installation requires every exact reference Candidate to be LOCKED/CURRENT",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details=installation["world_lock"],
            )
        production_registry = (
            ProductionControlSnapshotStore.load(self.production_control.snapshot_path)
            if self.production_control.snapshot_path.exists()
            else ProductionControlRegistry()
        )
        ApprovedPlanProductionControlInstaller.compile(
            proposal_registry=registry,
            plan_id=plan_id,
            blueprint=proposal.blueprint,
            project_id=self.project_id,
            production_registry=production_registry,
        )
        token = self._new_token(self._install_confirmations)
        self._install_confirmations[token] = _InstallConfirmation(
            token,
            proposal_sha,
            str(production["snapshot_sha256"]),
            plan_id,
            plan.proposal_id,
            plan.blueprint_sha256,
        )
        return {
            "confirmation_version": "1.0.0",
            "task_owner": "TASK-027/TASK-037",
            "confirmation_id": token,
            "project_id": self.project_id,
            "plan_id": plan_id,
            "proposal_id": plan.proposal_id,
            "blueprint_id": plan.blueprint_id,
            "blueprint_sha256": plan.blueprint_sha256,
            "scene_count": len(proposal.blueprint.scenes),
            "world_lock": installation.get("world_lock"),
            "human_final_authority_required": True,
            "provider_execution_started": False,
            "resolve_mutation_started": False,
        }

    def apply_install_plan(self, *, confirmation_id: str) -> dict[str, Any]:
        pending = self._install_confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError("ERR_PLANNING_APPLICATION_INSTALL_CONFIRMATION_INVALID", "Plan install confirmation is missing or already used", ProductErrorCategory.AUTHORIZATION)
        pending.consumed = True
        registry, proposal_sha, _ = self._load()
        self._require_expected(proposal_sha, pending.proposal_snapshot_sha256, "Proposal")
        proposal = next(
            (item for item in registry.proposals.get(pending.proposal_id, ()) if item.blueprint.to_dict()["blueprint_sha256"] == pending.blueprint_sha256),
            None,
        )
        if proposal is None:
            raise ProductError("ERR_PLANNING_APPLICATION_INSTALL_CONFIRMATION_STALE", "Approved Plan Blueprint changed after install preparation", ProductErrorCategory.AUTHORIZATION)
        result = self.production_control.install_approved_plan(
            proposal_registry=registry,
            plan_id=pending.plan_id,
            blueprint=proposal.blueprint,
            expected_snapshot_sha256=pending.production_snapshot_sha256,
        )
        return {**result, "application": self.snapshot(proposal_id=pending.proposal_id)}
