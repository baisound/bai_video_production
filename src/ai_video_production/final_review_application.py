"""P-UX-2D3 durable Final Review approval application.

The application stores explicit Human approval receipts with append-only CAS
semantics.  It does not create Export jobs or grant render/publication authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
from typing import Any, Callable, Mapping

from .atomic import AtomicJsonWriter, FailureInjector, exclusive_file_update_lock
from .errors import ProductError, ProductErrorCategory
from .final_review import FinalReviewApprovalReceipt
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


TokenFactory = Callable[[], str]
Clock = Callable[[], str]
_SNAPSHOT_NAME = "final-review-approvals.json"
_MAX_BYTES = 2 * 1024 * 1024
_MAX_APPROVALS = 256


def _with_hash(value: Mapping[str, Any]) -> dict[str, Any]:
    body = {key: item for key, item in value.items() if key != "snapshot_sha256"}
    return {**body, "snapshot_sha256": sha256_bytes(canonical_json_bytes(body))}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(slots=True)
class _PendingApproval:
    confirmation_id: str
    readiness: dict[str, Any]
    readiness_projection_sha256: str
    expected_snapshot_sha256: str
    consumed: bool = False


class FinalReviewApprovalApplication:
    """Project-scoped prepare/apply boundary for one exact readiness revision."""

    def __init__(
        self,
        *,
        project_root: str | Path,
        project_id: str,
        token_factory: TokenFactory | None = None,
        clock: Clock | None = None,
        failure_injector: FailureInjector | None = None,
    ) -> None:
        root = Path(project_root)
        if root.is_symlink() or not root.is_dir():
            raise ProductError(
                "ERR_FINAL_REVIEW_PROJECT_ROOT_INVALID",
                "Final Review project root must be an existing regular directory",
                ProductErrorCategory.VALIDATION,
            )
        if not isinstance(project_id, str) or not project_id.strip():
            raise ProductError(
                "ERR_FINAL_REVIEW_PROJECT_ID_INVALID",
                "Final Review project_id must be non-empty text",
                ProductErrorCategory.VALIDATION,
            )
        self.project_root = root
        self.project_id = project_id
        self.snapshot_path = root / _SNAPSHOT_NAME
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._clock = clock or _utc_now
        self._failure_injector = failure_injector
        self._pending: dict[str, _PendingApproval] = {}

    def _empty(self) -> dict[str, Any]:
        return _with_hash({
            "approval_snapshot_version": "1.0.0",
            "task_owner": "TASK-036/P-UX-2D3",
            "project_id": self.project_id,
            "revision": 0,
            "approvals": [],
            "export_job_created": False,
            "render_started": False,
            "publication_started": False,
        })

    def _validate_document(self, value: Any) -> None:
        expected = {
            "approval_snapshot_version", "task_owner", "project_id", "revision",
            "approvals", "export_job_created", "render_started",
            "publication_started", "snapshot_sha256",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise ProductError("ERR_FINAL_REVIEW_SNAPSHOT_INVALID", "Final Review snapshot fields are invalid", ProductErrorCategory.DATA_INTEGRITY)
        if value.get("approval_snapshot_version") != "1.0.0" or value.get("task_owner") != "TASK-036/P-UX-2D3":
            raise ProductError("ERR_FINAL_REVIEW_SNAPSHOT_INVALID", "Final Review snapshot version or owner is invalid", ProductErrorCategory.DATA_INTEGRITY)
        if value.get("project_id") != self.project_id:
            raise ProductError("ERR_FINAL_REVIEW_PROJECT_MISMATCH", "Final Review snapshot belongs to another Project", ProductErrorCategory.SECURITY)
        if value.get("snapshot_sha256") != _with_hash(value)["snapshot_sha256"]:
            raise ProductError("ERR_FINAL_REVIEW_SNAPSHOT_CHECKSUM", "Final Review snapshot checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
        if any(value.get(name) is not False for name in ("export_job_created", "render_started", "publication_started")):
            raise ProductError("ERR_FINAL_REVIEW_AUTHORITY_BOUNDARY", "Final Review snapshot claims prohibited effects", ProductErrorCategory.SECURITY)
        rows = value.get("approvals")
        revision = value.get("revision")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0 or not isinstance(rows, list):
            raise ProductError("ERR_FINAL_REVIEW_SNAPSHOT_INVALID", "Final Review revision or rows are invalid", ProductErrorCategory.DATA_INTEGRITY)
        if revision != len(rows) or len(rows) > _MAX_APPROVALS:
            raise ProductError("ERR_FINAL_REVIEW_REVISION_INVALID", "Final Review append-only revision is invalid", ProductErrorCategory.DATA_INTEGRITY)
        receipt_ids: set[str] = set()
        receipt_hashes: set[str] = set()
        for expected_revision, row in enumerate(rows, 1):
            if not isinstance(row, dict) or set(row) != {"approval_revision", "receipt"} or row.get("approval_revision") != expected_revision:
                raise ProductError("ERR_FINAL_REVIEW_ROW_INVALID", "Final Review approval row is invalid", ProductErrorCategory.DATA_INTEGRITY)
            try:
                receipt = FinalReviewApprovalReceipt.from_dict(row.get("receipt"))
            except (TypeError, ValueError) as exc:
                raise ProductError("ERR_FINAL_REVIEW_RECEIPT_INVALID", "Stored Final Review receipt is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
            if receipt.project_id != self.project_id:
                raise ProductError("ERR_FINAL_REVIEW_PROJECT_MISMATCH", "Stored Final Review receipt crosses Project scope", ProductErrorCategory.SECURITY)
            digest = receipt.final_approval_receipt_sha256
            if receipt.receipt_id in receipt_ids or digest in receipt_hashes:
                raise ProductError("ERR_FINAL_REVIEW_RECEIPT_DUPLICATE", "Stored Final Review receipt is duplicated", ProductErrorCategory.DATA_INTEGRITY)
            receipt_ids.add(receipt.receipt_id)
            receipt_hashes.add(digest)

    def _load(self) -> dict[str, Any]:
        target = self.snapshot_path
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ProductError("ERR_FINAL_REVIEW_SNAPSHOT_FILE_INVALID", "Final Review snapshot must be a regular non-symlink file", ProductErrorCategory.SECURITY)
        if not target.exists():
            return self._empty()
        size = target.stat().st_size
        if size <= 0 or size > _MAX_BYTES:
            raise ProductError("ERR_FINAL_REVIEW_SNAPSHOT_SIZE", "Final Review snapshot size is outside the bounded limit", ProductErrorCategory.DATA_INTEGRITY)
        try:
            value = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_FINAL_REVIEW_SNAPSHOT_READ", "Final Review snapshot could not be read", ProductErrorCategory.DATA_INTEGRITY) from exc
        self._validate_document(value)
        return value

    @staticmethod
    def _validate_readiness(readiness: Mapping[str, object]) -> FinalReviewApprovalReceipt:
        try:
            return FinalReviewApprovalReceipt.from_readiness(
                readiness,
                receipt_id="final-review-validation",
                approved_by="final-review-validator",
                approved_at="2000-01-01T00:00:00.000Z",
            )
        except (TypeError, ValueError) as exc:
            raise ProductError("ERR_FINAL_REVIEW_NOT_READY", "Final Review readiness is not approvable", ProductErrorCategory.HUMAN_REVIEW_REQUIRED) from exc

    def _readiness_coordinate(self, readiness: Mapping[str, object]) -> str:
        if not isinstance(readiness, Mapping):
            raise ProductError("ERR_FINAL_REVIEW_READINESS_INVALID", "Final Review readiness must be a mapping", ProductErrorCategory.DATA_INTEGRITY)
        projection_sha256 = readiness.get("projection_sha256")
        try:
            validate_sha256(projection_sha256, field_name="readiness.projection_sha256")
        except ValueError as exc:
            raise ProductError("ERR_FINAL_REVIEW_READINESS_INVALID", "Final Review readiness identity is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
        body = {
            key: value for key, value in readiness.items()
            if key not in {"available", "projection_sha256"}
        }
        if projection_sha256 != sha256_bytes(canonical_json_bytes(body)):
            raise ProductError("ERR_FINAL_REVIEW_READINESS_CHECKSUM", "Final Review readiness checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
        if readiness.get("project_id") != self.project_id:
            raise ProductError("ERR_FINAL_REVIEW_PROJECT_MISMATCH", "Final Review readiness belongs to another Project", ProductErrorCategory.SECURITY)
        return str(projection_sha256)

    def prepare_approval(
        self,
        *,
        readiness: Mapping[str, object],
        expected_readiness_projection_sha256: str,
        expected_snapshot_sha256: str,
    ) -> dict[str, Any]:
        probe = self._validate_readiness(readiness)
        validate_sha256(expected_readiness_projection_sha256, field_name="expected_readiness_projection_sha256")
        validate_sha256(expected_snapshot_sha256, field_name="expected_snapshot_sha256")
        if probe.project_id != self.project_id:
            raise ProductError("ERR_FINAL_REVIEW_PROJECT_MISMATCH", "Final Review readiness belongs to another Project", ProductErrorCategory.SECURITY)
        if probe.readiness_projection_sha256 != expected_readiness_projection_sha256:
            raise ProductError("ERR_FINAL_REVIEW_READINESS_STALE", "Final Review readiness changed before preparation", ProductErrorCategory.STATE)
        snapshot = self._load()
        if snapshot["snapshot_sha256"] != expected_snapshot_sha256:
            raise ProductError("ERR_FINAL_REVIEW_SNAPSHOT_CONFLICT", "Final Review approval history changed; reload first", ProductErrorCategory.STATE)
        if any(row["receipt"]["readiness_projection_sha256"] == probe.readiness_projection_sha256 for row in snapshot["approvals"]):
            raise ProductError("ERR_FINAL_REVIEW_ALREADY_APPROVED", "This exact Final Review readiness is already approved", ProductErrorCategory.STATE)
        token = self._token_factory()
        if not isinstance(token, str) or not token or token in self._pending:
            raise ProductError("ERR_FINAL_REVIEW_CONFIRMATION_INVALID", "Final Review confirmation identity is invalid", ProductErrorCategory.INTERNAL)
        frozen = json.loads(canonical_json_bytes(readiness).decode("utf-8"))
        self._pending[token] = _PendingApproval(
            token, frozen, probe.readiness_projection_sha256, expected_snapshot_sha256,
        )
        return {
            "confirmation_id": token,
            "project_id": self.project_id,
            "readiness_projection_sha256": probe.readiness_projection_sha256,
            "expected_snapshot_sha256": expected_snapshot_sha256,
            "human_confirmation_required": True,
            "approval_persisted": False,
            "export_job_created": False,
            "render_or_publish_started": False,
        }

    def apply_approval(
        self,
        *,
        confirmation_id: str,
        readiness: Mapping[str, object],
        approved_by: str,
    ) -> dict[str, Any]:
        pending = self._pending.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError("ERR_FINAL_REVIEW_CONFIRMATION_INVALID", "Final Review confirmation is missing or consumed", ProductErrorCategory.AUTHORIZATION)
        pending.consumed = True
        if canonical_json_bytes(readiness) != canonical_json_bytes(pending.readiness):
            raise ProductError("ERR_FINAL_REVIEW_READINESS_STALE", "Final Review readiness changed after confirmation", ProductErrorCategory.AUTHORIZATION)
        probe = self._validate_readiness(readiness)
        if probe.readiness_projection_sha256 != pending.readiness_projection_sha256:
            raise ProductError("ERR_FINAL_REVIEW_READINESS_STALE", "Final Review readiness identity changed after confirmation", ProductErrorCategory.AUTHORIZATION)
        approved_at = self._clock()
        with exclusive_file_update_lock(self.snapshot_path):
            snapshot = self._load()
            if snapshot["snapshot_sha256"] != pending.expected_snapshot_sha256:
                raise ProductError("ERR_FINAL_REVIEW_SNAPSHOT_CONFLICT", "Final Review approval history changed after confirmation", ProductErrorCategory.STATE)
            if len(snapshot["approvals"]) >= _MAX_APPROVALS:
                raise ProductError("ERR_FINAL_REVIEW_CAPACITY", "Final Review approval history reached its bounded maximum", ProductErrorCategory.STATE)
            if any(row["receipt"]["readiness_projection_sha256"] == probe.readiness_projection_sha256 for row in snapshot["approvals"]):
                raise ProductError("ERR_FINAL_REVIEW_ALREADY_APPROVED", "This exact Final Review readiness is already approved", ProductErrorCategory.STATE)
            revision = int(snapshot["revision"]) + 1
            seed = {
                "project_id": self.project_id,
                "readiness_projection_sha256": probe.readiness_projection_sha256,
                "approved_by": approved_by,
                "approved_at": approved_at,
                "approval_revision": revision,
            }
            receipt_id = "FINAL-" + sha256_bytes(canonical_json_bytes(seed)).split(":", 1)[1][:24].upper()
            try:
                receipt = FinalReviewApprovalReceipt.from_readiness(
                    readiness, receipt_id=receipt_id, approved_by=approved_by, approved_at=approved_at,
                )
            except (TypeError, ValueError) as exc:
                raise ProductError("ERR_FINAL_REVIEW_APPROVAL_INVALID", "Final Review approval identity or time is invalid", ProductErrorCategory.VALIDATION) from exc
            document = _with_hash({
                **{key: value for key, value in snapshot.items() if key not in {"snapshot_sha256", "revision", "approvals"}},
                "revision": revision,
                "approvals": [*snapshot["approvals"], {"approval_revision": revision, "receipt": receipt.to_dict()}],
            })
            result = AtomicJsonWriter.write(
                self.snapshot_path,
                document,
                validator=self._validate_document,
                failure_injector=self._failure_injector,
            )
        return {
            "approval_revision": revision,
            "receipt": receipt.to_dict(),
            "snapshot_sha256": document["snapshot_sha256"],
            "bytes_written": result.bytes_written,
            "export_job_created": False,
            "render_or_publish_started": False,
        }

    def snapshot(self, *, readiness: Mapping[str, object] | None = None) -> dict[str, Any]:
        document = self._load()
        state = "NO_APPROVAL" if not document["approvals"] else "CURRENT_READINESS_UNBOUND"
        current = False
        if readiness is not None:
            current_projection_sha256 = self._readiness_coordinate(readiness)
            if not document["approvals"]:
                state = "NO_APPROVAL"
            else:
                latest = FinalReviewApprovalReceipt.from_dict(document["approvals"][-1]["receipt"])
                current = latest.readiness_projection_sha256 == current_projection_sha256
                state = "APPROVED_CURRENT" if current else "APPROVAL_STALE"
        return {
            "available": True,
            "project_id": self.project_id,
            "revision": document["revision"],
            "state": state,
            "approval_current": current,
            "latest_receipt": None if not document["approvals"] else document["approvals"][-1]["receipt"],
            "snapshot_sha256": document["snapshot_sha256"],
            "max_approvals": _MAX_APPROVALS,
            "human_confirmation_required": True,
            "export_job_created": False,
            "render_or_publish_started": False,
        }


__all__ = ["FinalReviewApprovalApplication"]
