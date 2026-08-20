"""TASK-044 P-NLE-3 durable Export Queue application boundary."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import secrets
from typing import Callable

from .durable_product_job import (
    DurableProductJob, DurableProductJobService, DurableProductJobState,
    DurableProductJobStore,
)
from .errors import ProductError, ProductErrorCategory
from .export_queue import ExportDispatchResult, ExportPreparation
from .product_project_store import ProductProjectManifestStore

TokenFactory = Callable[[], str]
DispatchCallback = Callable[[DurableProductJob, ExportPreparation, Path], ExportDispatchResult]


@dataclass(slots=True)
class _DispatchConfirmation:
    confirmation_id: str
    job_id: str
    expected_state_version: int
    preparation_sha256: str
    consumed: bool = False


class ExportQueueApplication:
    def __init__(self, *, project_root: str | Path, project_id: str,
                 token_factory: TokenFactory | None = None) -> None:
        self.project_root = Path(project_root).resolve(strict=True)
        self.project_id = project_id
        manifest = ProductProjectManifestStore.load(self.project_root)
        if manifest.project_id != project_id:
            raise ProductError("ERR_EXPORT_PROJECT_MISMATCH", "Export queue belongs to another Project", ProductErrorCategory.SECURITY)
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._pending: dict[str, _DispatchConfirmation] = {}
        self.jobs = DurableProductJobService()

    def _validate_current(self, preparation: ExportPreparation) -> None:
        manifest = ProductProjectManifestStore.load(self.project_root)
        if manifest.project_id != self.project_id:
            raise ProductError("ERR_PRODUCT_JOB_PROJECT_CONFLICT", "Export queue belongs to another Project", ProductErrorCategory.SECURITY)
        if preparation.project_id != self.project_id:
            raise ProductError("ERR_EXPORT_PROJECT_MISMATCH", "Export preparation belongs to another Project", ProductErrorCategory.SECURITY)
        if (manifest.project_manifest_sha256 != preparation.project_manifest_sha256
                or manifest.product_version != preparation.product_version):
            raise ProductError("ERR_EXPORT_STALE_REPREPARE_REQUIRED", "Project changed; create a new Export preparation", ProductErrorCategory.STATE)

    def enqueue(self, preparation: ExportPreparation) -> DurableProductJob:
        self._validate_current(preparation)
        return self.jobs.enqueue(
            self.project_root, kind="EXPORT",
            target_identity=preparation.output_target_identity,
            input_hashes=preparation.input_hashes,
            estimated_cost=preparation.estimated_cost,
            currency=preparation.currency,
            estimate_source=preparation.estimate_source,
            exclusive_input_name="final_approval",
            expected_project_id=self.project_id,
        )

    def jobs_for_final_approval(
        self, final_approval_receipt_sha256: str,
    ) -> tuple[DurableProductJob, ...]:
        """Read exact EXPORT jobs already bound to one typed Final Review receipt."""

        return self.jobs.query_by_input_binding(
            self.project_root,
            kind="EXPORT",
            input_name="final_approval",
            input_sha256=final_approval_receipt_sha256,
            expected_project_id=self.project_id,
        )

    def recover_interrupted_on_startup(self) -> tuple[DurableProductJob, ...]:
        """Explicit startup recovery; never infer a restart from construction."""

        store_path = DurableProductJobStore.path(self.project_root)
        if not store_path.exists() and not store_path.is_symlink():
            return ()
        return self.jobs.recover_interrupted(
            self.project_root, kind="EXPORT", expected_project_id=self.project_id,
        )

    def _job(self, job_id: str) -> DurableProductJob:
        collection = DurableProductJobStore.load(self.project_root)
        if collection.project_id != self.project_id:
            raise ProductError("ERR_PRODUCT_JOB_PROJECT_CONFLICT", "Export jobs belong to another Project", ProductErrorCategory.SECURITY)
        return collection.get(job_id)

    @staticmethod
    def _matches(job: DurableProductJob, preparation: ExportPreparation) -> bool:
        return (job.kind == "EXPORT"
                and job.target_identity == preparation.output_target_identity
                and dict(job.input_hashes) == dict(preparation.input_hashes))

    def preflight(self, *, job_id: str, preparation: ExportPreparation) -> DurableProductJob:
        job = self._job(job_id)
        if job.state is not DurableProductJobState.QUEUED:
            raise ProductError("ERR_EXPORT_PREFLIGHT_STATE", "Only a queued Export can enter preflight", ProductErrorCategory.STATE)
        job = self.jobs.transition(self.project_root, job.job_id, DurableProductJobState.PREFLIGHT,
                                   expected_state_version=job.state_version)
        try:
            self._validate_current(preparation)
            if not self._matches(job, preparation):
                raise ProductError("ERR_EXPORT_STALE_REPREPARE_REQUIRED", "Export inputs differ from the queued operation", ProductErrorCategory.STATE)
        except ProductError as exc:
            if exc.category is ProductErrorCategory.SECURITY:
                raise
            return self.jobs.transition(
                self.project_root, job.job_id, DurableProductJobState.HUMAN_REQUIRED,
                expected_state_version=job.state_version,
                error_code="ERR_PRODUCT_JOB_INPUT_STALE",
            )
        return self.jobs.transition(self.project_root, job.job_id, DurableProductJobState.READY,
                                    expected_state_version=job.state_version)

    def prepare_dispatch(self, *, job_id: str, preparation: ExportPreparation) -> dict[str, object]:
        self._validate_current(preparation)
        job = self._job(job_id)
        if job.state is not DurableProductJobState.READY or not self._matches(job, preparation):
            raise ProductError("ERR_EXPORT_DISPATCH_STALE", "Export is not ready for this exact preparation", ProductErrorCategory.STATE)
        token = self._token_factory()
        if not isinstance(token, str) or not token or token in self._pending:
            raise ProductError("ERR_EXPORT_CONFIRMATION_INVALID", "Export confirmation identity is invalid", ProductErrorCategory.INTERNAL)
        self._pending[token] = _DispatchConfirmation(
            token, job.job_id, job.state_version, preparation.preparation_sha256,
        )
        return {"confirmation_id": token, "job_id": job.job_id,
                "operation_identity": job.operation_identity,
                "preparation_sha256": preparation.preparation_sha256,
                "human_confirmation_required": True,
                "blanket_execute_all_authorized": False,
                "external_mutation_started": False}

    def apply_dispatch(self, *, confirmation_id: str, preparation: ExportPreparation,
                       private_destination: str | Path,
                       dispatcher: DispatchCallback) -> DurableProductJob:
        pending = self._pending.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError("ERR_EXPORT_CONFIRMATION_INVALID", "Export confirmation is missing or consumed", ProductErrorCategory.AUTHORIZATION)
        pending.consumed = True
        self._validate_current(preparation)
        job = self._job(pending.job_id)
        if (job.state_version != pending.expected_state_version
                or preparation.preparation_sha256 != pending.preparation_sha256
                or not self._matches(job, preparation)):
            raise ProductError("ERR_EXPORT_CONFIRMATION_STALE", "Export changed after confirmation", ProductErrorCategory.AUTHORIZATION)
        destination = Path(private_destination)
        if not destination.is_absolute() or ".." in destination.parts:
            raise ProductError("ERR_EXPORT_PRIVATE_DESTINATION", "Launcher-private destination is invalid", ProductErrorCategory.SECURITY)
        dispatching = self.jobs.transition(
            self.project_root, job.job_id, DurableProductJobState.DISPATCHING,
            expected_state_version=job.state_version,
        )
        result = dispatcher(dispatching, preparation, destination)
        if not isinstance(result, ExportDispatchResult):
            raise ProductError("ERR_EXPORT_DISPATCH_RESULT", "Dispatcher returned an invalid result", ProductErrorCategory.DATA_INTEGRITY)
        if result.state == "RUNNING":
            return self.jobs.transition(self.project_root, job.job_id, DurableProductJobState.RUNNING,
                                        expected_state_version=dispatching.state_version)
        if result.state == "SUCCEEDED":
            return self.jobs.transition(self.project_root, job.job_id, DurableProductJobState.SUCCEEDED,
                                        expected_state_version=dispatching.state_version,
                                        result_ref=result.durable_result_ref,
                                        actual_cost=result.actual_cost)
        raise ProductError("ERR_EXPORT_DISPATCH_RESULT", "Dispatcher returned an unsupported result", ProductErrorCategory.DATA_INTEGRITY)

    def cancel(self, *, job_id: str, expected_state_version: int) -> DurableProductJob:
        job = self._job(job_id)
        if job.state not in {DurableProductJobState.QUEUED, DurableProductJobState.PREFLIGHT, DurableProductJobState.READY}:
            raise ProductError("ERR_EXPORT_CANCEL_UNSAFE", "Export may have an ambiguous external side effect", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        return self.jobs.transition(self.project_root, job.job_id, DurableProductJobState.CANCELLED,
                                    expected_state_version=expected_state_version)

    def reconcile(self, *, job_id: str, expected_state_version: int,
                  action: str, result: ExportDispatchResult | None = None) -> DurableProductJob:
        """Apply one explicit Human recovery decision to one UNKNOWN Export."""

        job = self._job(job_id)
        if job.state is not DurableProductJobState.UNKNOWN:
            raise ProductError(
                "ERR_EXPORT_RECONCILE_STATE", "Only an UNKNOWN Export can be reconciled",
                ProductErrorCategory.STATE,
            )
        if action == "ACCEPT_PROVEN_SUCCESS":
            if result is None or result.state != "SUCCEEDED":
                raise ProductError(
                    "ERR_EXPORT_RECONCILE_PROOF_REQUIRED",
                    "Passing Render QA Evidence and exact result identity are required",
                    ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                )
            return self.jobs.transition(
                self.project_root, job.job_id, DurableProductJobState.SUCCEEDED,
                expected_state_version=expected_state_version,
                recovery_action=action, result_ref=result.durable_result_ref,
                actual_cost=result.actual_cost,
            )
        if result is not None:
            raise ProductError(
                "ERR_EXPORT_RECONCILE_PROOF_UNEXPECTED",
                "Result proof is valid only for proven success",
                ProductErrorCategory.VALIDATION,
            )
        target = {
            "MARK_FAILED": DurableProductJobState.FAILED,
            "REQUIRE_HUMAN": DurableProductJobState.HUMAN_REQUIRED,
        }.get(action)
        if target is None:
            raise ProductError(
                "ERR_EXPORT_RECONCILE_ACTION", "Export recovery action is invalid",
                ProductErrorCategory.VALIDATION,
            )
        return self.jobs.transition(
            self.project_root, job.job_id, target,
            expected_state_version=expected_state_version,
            recovery_action=action,
            error_code=("ERR_PRODUCT_JOB_RECONCILED_FAILED" if target is DurableProductJobState.FAILED
                        else "ERR_PRODUCT_JOB_HUMAN_RECONCILIATION_REQUIRED"),
        )

    def prepare_execute_all(self, preparations: dict[str, ExportPreparation]) -> dict[str, object]:
        rows = []
        for job_id in sorted(preparations):
            preparation = preparations[job_id]
            self._validate_current(preparation)
            job = self._job(job_id)
            if job.state is DurableProductJobState.READY and self._matches(job, preparation):
                rows.append({"job_id": job_id,
                             "preparation_sha256": preparation.preparation_sha256,
                             "individual_confirmation_required": True})
        return {"items": rows, "blanket_confirmation_issued": False,
                "external_mutation_started": False}


__all__ = ["ExportQueueApplication"]
