"""Crash-safe TASK-027/TASK-037 planning-to-production bundle manifest.

Pins exact Proposal/GO, total Budget, and Production Control snapshots that were
validated together.  This is upstream of the existing TASK-037..041 bundle and
never repairs a mixed snapshot set automatically.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .approved_plan_trace import ApprovedPlanTraceReport, ApprovedPlanTraceValidator
from .atomic import AtomicJsonWriter, AtomicWriteResult
from .errors import ProductError, ProductErrorCategory
from .production_budget import ProductionBudgetLedger
from .production_budget_store import ProductionBudgetSnapshotStore
from .production_control import ProductionControlRegistry
from .production_control_store import ProductionControlSnapshotStore
from .production_proposal import ProductionProposalRegistry
from .production_proposal_store import ProductionProposalSnapshotStore
from .serialization import canonical_json_bytes, sha256_bytes


_MAX_BYTES = 1024 * 1024
_FILES = {
    "proposals": "production-proposal.json",
    "budget": "production-budget.json",
    "production": "production-control.json",
}


@dataclass(frozen=True, slots=True)
class PlanningProductionBundleState:
    proposals: ProductionProposalRegistry
    budget: ProductionBudgetLedger
    production: ProductionControlRegistry
    trace: ApprovedPlanTraceReport
    manifest_sha256: str


def _hashes(*, proposals: ProductionProposalRegistry, budget: ProductionBudgetLedger, production: ProductionControlRegistry) -> dict[str, str]:
    return {
        "proposals": ProductionProposalSnapshotStore.snapshot(proposals)["snapshot_sha256"],
        "budget": ProductionBudgetSnapshotStore.snapshot(budget)["snapshot_sha256"],
        "production": ProductionControlSnapshotStore.snapshot(production)["snapshot_sha256"],
    }


def _validate_budget_plan(*, proposals: ProductionProposalRegistry, plan_id: str, budget: ProductionBudgetLedger) -> None:
    plan = proposals.approved_plans.get(plan_id)
    if plan is None:
        raise ProductError("ERR_PLANNING_BUNDLE_PLAN_MISSING", "Planning bundle requires a registered Approved Production Plan", ProductErrorCategory.DATA_INTEGRITY)
    if budget.plan_id != plan.plan_id or budget.currency != plan.currency or budget.cost_ceiling != plan.cost_ceiling:
        raise ProductError(
            "ERR_PLANNING_BUNDLE_BUDGET_PLAN_MISMATCH",
            "Production budget ledger does not match exact Approved Plan ceiling/currency",
            ProductErrorCategory.DATA_INTEGRITY,
        )


def _manifest(*, plan_id: str, project_id: str, hashes: dict[str, str], trace_sha256: str) -> dict[str, Any]:
    if set(hashes) != set(_FILES):
        raise ValueError("planning bundle hashes must contain every canonical store")
    body: dict[str, Any] = {
        "bundle_version": "1.0.0",
        "task_owner": "TASK-027/TASK-037",
        "plan_id": plan_id,
        "project_id": project_id,
        "stores": {
            key: {"relative_path": _FILES[key], "snapshot_sha256": hashes[key]}
            for key in sorted(_FILES)
        },
        "trace_sha256": trace_sha256,
        "automatic_repair_authorized": False,
        "automatic_generation_authorized": False,
        "provider_execution_authorized": False,
    }
    body["manifest_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def _parse(document: dict[str, Any]) -> tuple[str, str, dict[str, str], str]:
    if document.get("bundle_version") != "1.0.0" or document.get("task_owner") != "TASK-027/TASK-037":
        raise ProductError("ERR_PLANNING_BUNDLE_MANIFEST_VERSION", "Unsupported planning-production bundle manifest", ProductErrorCategory.DATA_INTEGRITY)
    expected = document.get("manifest_sha256")
    body = {key: value for key, value in document.items() if key != "manifest_sha256"}
    if expected != sha256_bytes(canonical_json_bytes(body)):
        raise ProductError("ERR_PLANNING_BUNDLE_MANIFEST_CHECKSUM", "Planning-production bundle manifest checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
    if any(document.get(key) is not False for key in (
        "automatic_repair_authorized", "automatic_generation_authorized", "provider_execution_authorized"
    )):
        raise ProductError("ERR_PLANNING_BUNDLE_MANIFEST_BOUNDARY", "Planning-production bundle cannot grant repair/generation/provider authority", ProductErrorCategory.SECURITY)
    plan_id = document.get("plan_id")
    project_id = document.get("project_id")
    trace_sha = document.get("trace_sha256")
    if not isinstance(plan_id, str) or not plan_id or not isinstance(project_id, str) or not project_id:
        raise ProductError("ERR_PLANNING_BUNDLE_MANIFEST_ID", "Planning-production bundle plan/project identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
    if not isinstance(trace_sha, str) or not trace_sha.startswith("sha256:") or len(trace_sha) != 71:
        raise ProductError("ERR_PLANNING_BUNDLE_MANIFEST_TRACE", "Planning-production bundle trace identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
    stores = document.get("stores")
    if not isinstance(stores, dict) or set(stores) != set(_FILES):
        raise ProductError("ERR_PLANNING_BUNDLE_MANIFEST_STORES", "Planning-production bundle must pin every canonical store", ProductErrorCategory.DATA_INTEGRITY)
    hashes: dict[str, str] = {}
    for key, filename in _FILES.items():
        row = stores.get(key)
        if not isinstance(row, dict) or row.get("relative_path") != filename:
            raise ProductError("ERR_PLANNING_BUNDLE_MANIFEST_PATH", "Planning-production bundle uses fixed relative store names", ProductErrorCategory.SECURITY, details={"store": key})
        value = row.get("snapshot_sha256")
        if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
            raise ProductError("ERR_PLANNING_BUNDLE_MANIFEST_HASH", "Planning-production bundle snapshot checksum is invalid", ProductErrorCategory.DATA_INTEGRITY, details={"store": key})
        hashes[key] = value
    return plan_id, project_id, hashes, trace_sha


class PlanningProductionBundleStore:
    @staticmethod
    def build(
        *,
        proposals: ProductionProposalRegistry,
        plan_id: str,
        budget: ProductionBudgetLedger,
        production: ProductionControlRegistry,
        project_id: str,
    ) -> dict[str, Any]:
        _validate_budget_plan(proposals=proposals, plan_id=plan_id, budget=budget)
        trace = ApprovedPlanTraceValidator.validate(
            proposals=proposals, plan_id=plan_id, production=production, project_id=project_id,
        )
        return _manifest(
            plan_id=plan_id,
            project_id=project_id,
            hashes=_hashes(proposals=proposals, budget=budget, production=production),
            trace_sha256=trace.to_dict()["report_sha256"],
        )

    @staticmethod
    def save(path: str | Path, document: dict[str, Any], *, expected_previous_manifest_sha256: str | None = None) -> AtomicWriteResult:
        _parse(document)
        target = Path(path)
        if target.is_symlink():
            raise ProductError("ERR_PLANNING_BUNDLE_MANIFEST_FILE_INVALID", "Refusing to replace a symlink planning-production manifest", ProductErrorCategory.SECURITY)
        if target.exists():
            if not target.is_file():
                raise ProductError("ERR_PLANNING_BUNDLE_MANIFEST_FILE_INVALID", "Planning-production manifest target must be a regular file", ProductErrorCategory.VALIDATION)
            if expected_previous_manifest_sha256 is None:
                raise ProductError("ERR_PLANNING_BUNDLE_MANIFEST_CAS_REQUIRED", "Replacing planning-production manifest requires exact previous checksum", ProductErrorCategory.AUTHORIZATION)
            current = PlanningProductionBundleStore.load_document(target)
            if current["manifest_sha256"] != expected_previous_manifest_sha256:
                raise ProductError("ERR_PLANNING_BUNDLE_MANIFEST_REVISION_CONFLICT", "Planning-production manifest changed before save", ProductErrorCategory.STATE)
        elif expected_previous_manifest_sha256 is not None:
            raise ProductError("ERR_PLANNING_BUNDLE_MANIFEST_PREVIOUS_MISSING", "Expected previous planning-production manifest does not exist", ProductErrorCategory.STATE)
        return AtomicJsonWriter.write(target, document, validator=lambda value: _parse(value))

    @staticmethod
    def load_document(path: str | Path) -> dict[str, Any]:
        target = Path(path)
        if target.is_symlink() or not target.is_file():
            raise ProductError("ERR_PLANNING_BUNDLE_MANIFEST_FILE_INVALID", "Planning-production manifest must be a regular non-symlink file", ProductErrorCategory.VALIDATION)
        size = target.stat().st_size
        if size <= 0 or size > _MAX_BYTES:
            raise ProductError("ERR_PLANNING_BUNDLE_MANIFEST_SIZE", "Planning-production manifest size is outside the allowed bound", ProductErrorCategory.VALIDATION)
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_PLANNING_BUNDLE_MANIFEST_READ", "Planning-production manifest could not be read as UTF-8 JSON", ProductErrorCategory.DATA_INTEGRITY) from exc
        if not isinstance(document, dict):
            raise ProductError("ERR_PLANNING_BUNDLE_MANIFEST_INVALID", "Planning-production manifest root must be an object", ProductErrorCategory.DATA_INTEGRITY)
        _parse(document)
        return document

    @staticmethod
    def recover(root: str | Path, *, manifest_name: str = "planning-production-bundle.json") -> PlanningProductionBundleState:
        directory = Path(root)
        if directory.is_symlink() or not directory.is_dir():
            raise ProductError("ERR_PLANNING_BUNDLE_ROOT_INVALID", "Planning-production root must be an existing regular non-symlink directory", ProductErrorCategory.VALIDATION)
        if manifest_name != "planning-production-bundle.json":
            raise ProductError("ERR_PLANNING_BUNDLE_MANIFEST_NAME", "Planning-production recovery uses the fixed canonical manifest name", ProductErrorCategory.SECURITY)
        document = PlanningProductionBundleStore.load_document(directory / manifest_name)
        plan_id, project_id, expected, expected_trace = _parse(document)
        proposals = ProductionProposalSnapshotStore.load(directory / _FILES["proposals"])
        budget = ProductionBudgetSnapshotStore.load(directory / _FILES["budget"])
        production = ProductionControlSnapshotStore.load(directory / _FILES["production"])
        observed = _hashes(proposals=proposals, budget=budget, production=production)
        if observed != expected:
            changed = sorted(key for key in _FILES if observed[key] != expected[key])
            raise ProductError(
                "ERR_PLANNING_BUNDLE_SNAPSHOT_SET_CHANGED",
                "Planning-production snapshot set no longer matches the validated manifest",
                ProductErrorCategory.STATE,
                details={"changed_stores": changed, "automatic_repair_performed": False},
            )
        _validate_budget_plan(proposals=proposals, plan_id=plan_id, budget=budget)
        trace = ApprovedPlanTraceValidator.validate(
            proposals=proposals, plan_id=plan_id, production=production, project_id=project_id,
        )
        if trace.to_dict()["report_sha256"] != expected_trace:
            raise ProductError("ERR_PLANNING_BUNDLE_TRACE_CHANGED", "Approved Plan trace changed without a new validated bundle manifest", ProductErrorCategory.STATE)
        return PlanningProductionBundleState(proposals, budget, production, trace, document["manifest_sha256"])
