"""TASK-036 P-UX-2D5 Final Review to durable Export Queue boundary."""

from __future__ import annotations

from dataclasses import dataclass
import json
import secrets
from typing import Any, Callable, Mapping

from .durable_product_job import DurableProductJobStore
from .errors import ProductError, ProductErrorCategory
from .export_queue import ExportPreparation
from .export_queue_application import ExportQueueApplication
from .final_review import FinalReviewApprovalReceipt
from .final_review_application import FinalReviewApprovalApplication
from .product_project_store import ProductProjectManifestStore
from .serialization import canonical_json_bytes


ExportApplicationProvider = Callable[[], ExportQueueApplication | None]
ExportPreparationProvider = Callable[[FinalReviewApprovalReceipt], ExportPreparation]
TokenFactory = Callable[[], str]


@dataclass(slots=True)
class _PendingEnqueue:
    confirmation_id: str
    readiness_projection_sha256: str
    approval_snapshot_sha256: str
    approval_receipt_sha256: str
    preparation_sha256: str
    frozen_readiness: dict[str, object]
    consumed: bool = False


class Task036FinalReviewExportApplication:
    """Creates one queued Export job; it never dispatches or renders it."""

    def __init__(
        self,
        *,
        project_id: str,
        final_review_application: FinalReviewApprovalApplication,
        export_application_provider: ExportApplicationProvider,
        preparation_provider: ExportPreparationProvider,
        token_factory: TokenFactory | None = None,
    ) -> None:
        if final_review_application.project_id != project_id:
            raise ValueError("Final Review application crosses Project scope")
        if not callable(export_application_provider) or not callable(preparation_provider):
            raise ValueError("Export application and preparation providers must be callable")
        self.project_id = project_id
        self._final_review = final_review_application
        self._export_application_provider = export_application_provider
        self._preparation_provider = preparation_provider
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._pending: dict[str, _PendingEnqueue] = {}

    def _application(self) -> ExportQueueApplication:
        application = self._export_application_provider()
        if application is None:
            raise ProductError(
                "ERR_FINAL_REVIEW_EXPORT_QUEUE_NOT_BOUND",
                "Durable Export Queue is not bound to this Project",
                ProductErrorCategory.STATE,
            )
        if application.project_id != self.project_id:
            raise ProductError(
                "ERR_FINAL_REVIEW_EXPORT_PROJECT_MISMATCH",
                "Durable Export Queue crosses Project scope",
                ProductErrorCategory.SECURITY,
            )
        return application

    def _preparation(
        self, *, readiness: Mapping[str, object]
    ) -> tuple[dict[str, Any], FinalReviewApprovalReceipt, ExportPreparation, ExportQueueApplication]:
        approval = self._final_review.snapshot(readiness=readiness)
        if approval.get("approval_current") is not True:
            raise ProductError(
                "ERR_FINAL_REVIEW_EXPORT_APPROVAL_NOT_CURRENT",
                "A current typed Final Review approval is required",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        try:
            receipt = FinalReviewApprovalReceipt.from_dict(approval.get("latest_receipt"))
            preparation = self._preparation_provider(receipt)
        except ProductError:
            raise
        except (TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_FINAL_REVIEW_EXPORT_PREPARATION_INVALID",
                "Private Export preparation provider returned invalid data",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if not isinstance(preparation, ExportPreparation):
            raise ProductError(
                "ERR_FINAL_REVIEW_EXPORT_PREPARATION_INVALID",
                "Private Export preparation provider must return ExportPreparation",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if preparation.project_id != self.project_id or preparation.final_approval != receipt:
            raise ProductError(
                "ERR_FINAL_REVIEW_EXPORT_PREPARATION_MISMATCH",
                "Export preparation does not consume the current exact approval",
                ProductErrorCategory.SECURITY,
            )
        application = self._application()
        manifest = ProductProjectManifestStore.load(application.project_root)
        if (
            manifest.project_id != self.project_id
            or manifest.project_manifest_sha256 != preparation.project_manifest_sha256
            or manifest.product_version != preparation.product_version
        ):
            raise ProductError(
                "ERR_FINAL_REVIEW_EXPORT_PREPARATION_STALE",
                "Project changed; create a new Export preparation",
                ProductErrorCategory.STATE,
            )
        return approval, receipt, preparation, application

    @staticmethod
    def _already_queued(application: ExportQueueApplication, preparation: ExportPreparation) -> bool:
        path = DurableProductJobStore.path(application.project_root)
        if not path.exists():
            return False
        collection = DurableProductJobStore.load(application.project_root)
        return any(
            job.kind == "EXPORT"
            and job.target_identity == preparation.output_target_identity
            and dict(job.input_hashes) == dict(preparation.input_hashes)
            for job in collection.jobs
        )

    def snapshot(self, *, readiness: Mapping[str, object]) -> dict[str, Any]:
        try:
            approval, receipt, preparation, application = self._preparation(readiness=readiness)
        except ProductError as exc:
            if exc.code in {
                "ERR_FINAL_REVIEW_EXPORT_APPROVAL_NOT_CURRENT",
                "ERR_FINAL_REVIEW_EXPORT_QUEUE_NOT_BOUND",
            }:
                return {
                    "available": False,
                    "state": exc.code,
                    "queue_confirmation_ready": False,
                    "export_job_created": False,
                    "dispatch_or_render_started": False,
                    "host_output_path_persisted": False,
                }
            raise
        already_queued = self._already_queued(application, preparation)
        return {
            "available": True,
            "state": "ALREADY_QUEUED" if already_queued else "READY_FOR_EXPORT_QUEUE_CONFIRMATION",
            "project_id": self.project_id,
            "readiness_projection_sha256": receipt.readiness_projection_sha256,
            "approval_snapshot_sha256": approval["snapshot_sha256"],
            "approval_receipt_sha256": receipt.final_approval_receipt_sha256,
            "preparation_sha256": preparation.preparation_sha256,
            "preset": preparation.preset.to_dict(),
            "output_target_identity": preparation.output_target_identity,
            "authority_class": preparation.authority_class.value,
            "queue_confirmation_ready": not already_queued,
            "export_job_created": already_queued,
            "dispatch_or_render_started": False,
            "host_output_path_persisted": False,
        }

    def prepare_enqueue(
        self,
        *,
        readiness: Mapping[str, object],
        expected_readiness_projection_sha256: str,
        expected_approval_snapshot_sha256: str,
        expected_preparation_sha256: str,
    ) -> dict[str, Any]:
        snapshot = self.snapshot(readiness=readiness)
        if snapshot.get("queue_confirmation_ready") is not True:
            raise ProductError(
                "ERR_FINAL_REVIEW_EXPORT_NOT_READY",
                "Export Queue insertion is not ready",
                ProductErrorCategory.STATE,
            )
        expected = (
            ("readiness_projection_sha256", expected_readiness_projection_sha256),
            ("approval_snapshot_sha256", expected_approval_snapshot_sha256),
            ("preparation_sha256", expected_preparation_sha256),
        )
        if any(snapshot[name] != value for name, value in expected):
            raise ProductError(
                "ERR_FINAL_REVIEW_EXPORT_PREPARE_STALE",
                "Final Review or Export preparation changed before confirmation",
                ProductErrorCategory.STATE,
            )
        token = self._token_factory()
        if not isinstance(token, str) or not token or token in self._pending:
            raise ProductError(
                "ERR_FINAL_REVIEW_EXPORT_CONFIRMATION_INVALID",
                "Export Queue confirmation identity is invalid",
                ProductErrorCategory.INTERNAL,
            )
        frozen = dict(json.loads(canonical_json_bytes(readiness).decode("utf-8")))
        self._pending[token] = _PendingEnqueue(
            token,
            str(snapshot["readiness_projection_sha256"]),
            str(snapshot["approval_snapshot_sha256"]),
            str(snapshot["approval_receipt_sha256"]),
            str(snapshot["preparation_sha256"]),
            frozen,
        )
        return {
            "confirmation_id": token,
            "project_id": self.project_id,
            "preparation_sha256": snapshot["preparation_sha256"],
            "preset": snapshot["preset"],
            "output_target_identity": snapshot["output_target_identity"],
            "human_confirmation_required": True,
            "export_job_created": False,
            "dispatch_or_render_started": False,
            "host_output_path_persisted": False,
        }

    def apply_enqueue(
        self, *, confirmation_id: str, readiness: Mapping[str, object]
    ) -> dict[str, Any]:
        pending = self._pending.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError(
                "ERR_FINAL_REVIEW_EXPORT_CONFIRMATION_INVALID",
                "Export Queue confirmation is missing or consumed",
                ProductErrorCategory.AUTHORIZATION,
            )
        pending.consumed = True
        if canonical_json_bytes(readiness) != canonical_json_bytes(pending.frozen_readiness):
            raise ProductError(
                "ERR_FINAL_REVIEW_EXPORT_CONFIRMATION_STALE",
                "Final Review readiness changed after confirmation",
                ProductErrorCategory.AUTHORIZATION,
            )
        snapshot = self.snapshot(readiness=readiness)
        if (
            snapshot.get("queue_confirmation_ready") is not True
            or snapshot.get("readiness_projection_sha256") != pending.readiness_projection_sha256
            or snapshot.get("approval_snapshot_sha256") != pending.approval_snapshot_sha256
            or snapshot.get("approval_receipt_sha256") != pending.approval_receipt_sha256
            or snapshot.get("preparation_sha256") != pending.preparation_sha256
        ):
            raise ProductError(
                "ERR_FINAL_REVIEW_EXPORT_CONFIRMATION_STALE",
                "Final Review approval or Export preparation changed after confirmation",
                ProductErrorCategory.AUTHORIZATION,
            )
        _, _, preparation, application = self._preparation(readiness=readiness)
        job = application.enqueue(preparation)
        return {
            "job_id": job.job_id,
            "operation_identity": job.operation_identity,
            "state": job.state.value,
            "state_version": job.state_version,
            "preparation_sha256": preparation.preparation_sha256,
            "export_job_created": True,
            "dispatch_or_render_started": False,
            "host_output_path_persisted": False,
        }


__all__ = ["Task036FinalReviewExportApplication"]
