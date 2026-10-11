"""TASK-111 explicit Human input bridge for immutable TASK-038 audits.

The controller owns no canonical store.  It binds one reviewed AuditRecord to
the exact Candidate/Asset and Production/Audit snapshots, then delegates the
only write to :meth:`Task038AuditApplication.record_audit` after a separate,
one-shot Human confirmation.  Candidate acceptance, rejection, LOCK, Provider
execution, and regeneration remain outside this boundary.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import math
import re
import secrets
from typing import Any

from .audit_application import Task038AuditApplication
from .candidate_audit import (
    AuditDimension,
    AuditFinding,
    AuditRecord,
    AuditorKind,
    CandidateAuditRegistry,
    FindingSeverity,
)
from .candidate_audit_store import CandidateAuditSnapshotStore
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes


_PUBLIC_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_SCORE_DIMENSIONS = {item.value for item in AuditDimension} | {"AESTHETIC"}
_FINDING_FIELDS = {
    "finding_id",
    "dimension",
    "severity",
    "code",
    "summary",
    "critical_violation",
}
_MAX_CONTRACT_REFS = 64
_MAX_DIMENSION_SCORES = len(_SCORE_DIMENSIONS)
_MAX_FINDINGS = 256
_MAX_FAILURE_CODES = 256
_MAX_ALTERNATE_USE_PROPOSALS = 64
_MAX_RECORD_BYTES = 1024 * 1024
_MAX_AUDIT_SNAPSHOT_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class _PendingAuditInput:
    confirmation_id: str
    record: AuditRecord
    asset_id: str
    production_snapshot_sha256: str
    audit_snapshot_sha256: str


class Task111AuditInputController:
    """Prepare and apply one exact immutable Audit input without new storage."""

    def __init__(
        self,
        application: Task038AuditApplication,
        *,
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        self._application = application
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._pending: dict[str, _PendingAuditInput] = {}

    @staticmethod
    def _error(code: str, message: str, category: ProductErrorCategory) -> ProductError:
        return ProductError(code, message, category)

    @classmethod
    def _invalid(cls) -> ProductError:
        return cls._error(
            "ERR_TASK111_AUDIT_INPUT_INVALID",
            "Audit input is invalid",
            ProductErrorCategory.VALIDATION,
        )

    @staticmethod
    def _text_sequence(value: object, *, maximum: int) -> tuple[str, ...]:
        if (
            not isinstance(value, Sequence)
            or isinstance(value, (str, bytes, bytearray))
            or len(value) > maximum
            or any(type(item) is not str for item in value)
        ):
            raise ValueError("invalid sequence")
        return tuple(value)

    @staticmethod
    def _optional_id(value: object) -> str | None:
        if value is None:
            return None
        if type(value) is not str or _PUBLIC_ID_RE.fullmatch(value) is None:
            raise ValueError("invalid optional id")
        return value

    @classmethod
    def _record(
        cls,
        *,
        audit_id: object,
        candidate_id: object,
        asset_sha256: object,
        auditor_id: object,
        auditor_version: object,
        contract_refs: object,
        dimension_scores: object,
        findings: object,
        failure_codes: object,
        alternate_use_proposals: object,
    ) -> AuditRecord:
        try:
            if (
                type(dimension_scores) is not dict
                or not dimension_scores
                or len(dimension_scores) > _MAX_DIMENSION_SCORES
            ):
                raise ValueError("invalid scores")
            scores: dict[str, float] = {}
            for key, value in dimension_scores.items():
                if (
                    type(key) is not str
                    or key not in _SCORE_DIMENSIONS
                    or type(value) not in (int, float)
                ):
                    raise ValueError("invalid score")
                score = float(value)
                if not math.isfinite(score) or not 0 <= score <= 100:
                    raise ValueError("invalid score")
                scores[key] = score
            if (
                not isinstance(findings, Sequence)
                or isinstance(findings, (str, bytes, bytearray))
                or len(findings) > _MAX_FINDINGS
            ):
                raise ValueError("invalid findings")
            parsed_findings: list[AuditFinding] = []
            for value in findings:
                if type(value) is not dict or set(value) != _FINDING_FIELDS:
                    raise ValueError("invalid finding")
                if type(value["critical_violation"]) is not bool:
                    raise ValueError("invalid critical flag")
                parsed_findings.append(
                    AuditFinding(
                        finding_id=value["finding_id"],
                        dimension=AuditDimension(value["dimension"]),
                        severity=FindingSeverity(value["severity"]),
                        code=value["code"],
                        summary=value["summary"],
                        critical_violation=value["critical_violation"],
                    )
                )
            parsed_contract_refs = cls._text_sequence(
                contract_refs, maximum=_MAX_CONTRACT_REFS
            )
            if not parsed_contract_refs:
                raise ValueError("missing contract refs")
            record = AuditRecord(
                audit_id=audit_id,
                candidate_id=candidate_id,
                asset_sha256=asset_sha256,
                contract_refs=parsed_contract_refs,
                auditor_kind=AuditorKind.HUMAN,
                auditor_id=auditor_id,
                auditor_version=cls._optional_id(auditor_version),
                dimension_scores=scores,
                findings=tuple(parsed_findings),
                failure_codes=cls._text_sequence(
                    failure_codes, maximum=_MAX_FAILURE_CODES
                ),
                alternate_use_proposals=cls._text_sequence(
                    alternate_use_proposals,
                    maximum=_MAX_ALTERNATE_USE_PROPOSALS,
                ),
            )
            if len(canonical_json_bytes(record.to_dict())) > _MAX_RECORD_BYTES:
                raise ValueError("record exceeds byte bound")
            return record
        except (
            AttributeError,
            KeyError,
            OverflowError,
            TypeError,
            UnicodeError,
            ValueError,
        ) as exc:
            raise cls._invalid() from exc

    def _snapshot(self) -> dict[str, Any]:
        try:
            return self._application.snapshot()
        except ProductError:
            raise
        except (OSError, UnicodeError) as exc:
            raise self._error(
                "ERR_TASK111_AUDIT_SNAPSHOT_UNAVAILABLE",
                "Audit Workspace could not be read; refresh before preparing again",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc

    def _require_snapshot_capacity(self, record: AuditRecord) -> None:
        try:
            if self._application.audit_path.exists():
                registry = CandidateAuditSnapshotStore.load(
                    self._application.audit_path
                )
            else:
                registry = CandidateAuditRegistry()
            registry.add_audit(record)
            projected = CandidateAuditSnapshotStore.snapshot(registry)
            projected_bytes = len(canonical_json_bytes(projected)) + 1
        except ProductError:
            raise
        except (OSError, UnicodeError) as exc:
            raise self._error(
                "ERR_TASK111_AUDIT_SNAPSHOT_UNAVAILABLE",
                "Audit Workspace could not be read; refresh before preparing again",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if projected_bytes > _MAX_AUDIT_SNAPSHOT_BYTES:
            raise self._error(
                "ERR_TASK111_AUDIT_SNAPSHOT_TOO_LARGE",
                "Audit input would exceed the Audit Workspace size limit",
                ProductErrorCategory.VALIDATION,
            )

    @staticmethod
    def _candidate(snapshot: Mapping[str, Any], candidate_id: object) -> Mapping[str, Any]:
        workspace = snapshot.get("workspace")
        candidates = workspace.get("candidates") if isinstance(workspace, Mapping) else None
        if not isinstance(candidates, list):
            raise ProductError(
                "ERR_TASK111_AUDIT_PROJECTION_INVALID",
                "Audit Workspace projection is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        matches = [row for row in candidates if isinstance(row, Mapping) and row.get("candidate_id") == candidate_id]
        if len(matches) != 1:
            raise ProductError(
                "ERR_TASK111_AUDIT_CANDIDATE_NOT_FOUND",
                "Audit Candidate was not found",
                ProductErrorCategory.STATE,
            )
        return matches[0]

    def prepare(
        self,
        *,
        audit_id: object,
        candidate_id: object,
        asset_id: object,
        asset_sha256: object,
        auditor_id: object,
        auditor_version: object,
        contract_refs: object,
        dimension_scores: object,
        findings: object,
        failure_codes: object,
        alternate_use_proposals: object,
        expected_production_snapshot_sha256: object,
        expected_audit_snapshot_sha256: object,
    ) -> dict[str, Any]:
        record = self._record(
            audit_id=audit_id,
            candidate_id=candidate_id,
            asset_sha256=asset_sha256,
            auditor_id=auditor_id,
            auditor_version=auditor_version,
            contract_refs=contract_refs,
            dimension_scores=dimension_scores,
            findings=findings,
            failure_codes=failure_codes,
            alternate_use_proposals=alternate_use_proposals,
        )
        snapshot = self._snapshot()
        if snapshot.get("recovery", {}).get("required") is True:
            raise self._error(
                "ERR_TASK111_AUDIT_RECOVERY_REQUIRED",
                "Complete Audit recovery before recording another Audit",
                ProductErrorCategory.STATE,
            )
        if (
            type(expected_production_snapshot_sha256) is not str
            or type(expected_audit_snapshot_sha256) is not str
            or expected_production_snapshot_sha256
            != snapshot.get("production_snapshot_sha256")
            or expected_audit_snapshot_sha256 != snapshot.get("audit_snapshot_sha256")
        ):
            raise self._error(
                "ERR_TASK111_AUDIT_SNAPSHOT_CONFLICT",
                "Audit input snapshots changed; refresh before preparing again",
                ProductErrorCategory.STATE,
            )
        candidate = self._candidate(snapshot, candidate_id)
        if candidate.get("lifecycle_state") != "READY_FOR_AUDIT":
            raise self._error(
                "ERR_TASK111_AUDIT_CANDIDATE_NOT_READY",
                "Candidate is not ready for Audit input",
                ProductErrorCategory.STATE,
            )
        if (
            type(asset_id) is not str
            or candidate.get("asset_id") != asset_id
            or candidate.get("asset_sha256") != asset_sha256
        ):
            raise self._error(
                "ERR_TASK111_AUDIT_ASSET_MISMATCH",
                "Audit input does not match the current Candidate Asset",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if candidate.get("audit_count") != 0:
            raise self._error(
                "ERR_TASK111_AUDIT_ALREADY_RECORDED",
                "Candidate already has an immutable Audit record",
                ProductErrorCategory.STATE,
            )
        self._require_snapshot_capacity(record)
        confirmation_id = self._token_factory()
        if (
            type(confirmation_id) is not str
            or not confirmation_id.strip()
            or len(confirmation_id) > 256
            or confirmation_id in self._pending
        ):
            raise self._error(
                "ERR_TASK111_AUDIT_CONFIRMATION_INVALID",
                "Audit input confirmation is invalid",
                ProductErrorCategory.INTERNAL,
            )
        pending = _PendingAuditInput(
            confirmation_id=confirmation_id,
            record=record,
            asset_id=asset_id,
            production_snapshot_sha256=expected_production_snapshot_sha256,
            audit_snapshot_sha256=expected_audit_snapshot_sha256,
        )
        self._pending[confirmation_id] = pending
        return {
            "task_owner": "TASK-111",
            "operation": "AUDIT_INPUT_PREPARE",
            "confirmation_id": confirmation_id,
            "candidate_id": record.candidate_id,
            "asset_id": asset_id,
            "asset_sha256": record.asset_sha256,
            "production_snapshot_sha256": expected_production_snapshot_sha256,
            "audit_snapshot_sha256": expected_audit_snapshot_sha256,
            "record": record.to_dict(),
            "canonical_write_started": False,
            "human_candidate_decision_recorded": False,
            "automatic_candidate_accept": False,
            "automatic_candidate_reject": False,
            "automatic_candidate_lock": False,
            "provider_execution_started": False,
        }

    def cancel(self, *, confirmation_id: object) -> dict[str, Any]:
        if type(confirmation_id) is not str or self._pending.pop(confirmation_id, None) is None:
            raise self._error(
                "ERR_TASK111_AUDIT_CONFIRMATION_INVALID",
                "Audit input confirmation is missing or already used",
                ProductErrorCategory.AUTHORIZATION,
            )
        return {
            "task_owner": "TASK-111",
            "operation": "AUDIT_INPUT_CANCEL",
            "status": "CANCELLED",
            "canonical_write_started": False,
            "human_candidate_decision_recorded": False,
            "provider_execution_started": False,
        }

    def apply(
        self,
        *,
        confirmation_id: object,
        explicit_human_confirmation: object,
    ) -> dict[str, Any]:
        if explicit_human_confirmation is not True:
            raise self._error(
                "ERR_TASK111_AUDIT_CONFIRMATION_REQUIRED",
                "Explicit Human confirmation is required",
                ProductErrorCategory.AUTHORIZATION,
            )
        if type(confirmation_id) is not str:
            pending = None
        else:
            pending = self._pending.pop(confirmation_id, None)
        if pending is None:
            raise self._error(
                "ERR_TASK111_AUDIT_CONFIRMATION_INVALID",
                "Audit input confirmation is missing or already used",
                ProductErrorCategory.AUTHORIZATION,
            )
        try:
            snapshot = self._application.record_audit(
                record=pending.record,
                expected_production_snapshot_sha256=pending.production_snapshot_sha256,
                expected_audit_snapshot_sha256=pending.audit_snapshot_sha256,
            )
        except ProductError:
            raise
        except OSError as exc:
            raise self._error(
                "ERR_TASK111_AUDIT_SAVE_FAILED",
                "Audit record could not be saved; refresh before preparing again",
                ProductErrorCategory.INTERNAL,
            ) from exc
        candidate = self._candidate(snapshot, pending.record.candidate_id)
        saved = [
            record
            for record in candidate.get("audit_history", [])
            if isinstance(record, Mapping)
            and record.get("audit_id") == pending.record.audit_id
        ]
        if (
            len(saved) != 1
            or saved[0].get("record_sha256")
            != pending.record.to_dict()["record_sha256"]
        ):
            raise self._error(
                "ERR_TASK111_AUDIT_READBACK_INVALID",
                "Saved Audit record could not be verified",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return {
            "task_owner": "TASK-111",
            "operation": "AUDIT_INPUT_APPLY",
            "status": "SAVED",
            "candidate_id": pending.record.candidate_id,
            "asset_id": pending.asset_id,
            "asset_sha256": pending.record.asset_sha256,
            "audit_id": pending.record.audit_id,
            "record_sha256": pending.record.to_dict()["record_sha256"],
            "audit": snapshot,
            "human_candidate_decision_recorded": False,
            "automatic_candidate_accept": False,
            "automatic_candidate_reject": False,
            "automatic_candidate_lock": False,
            "automatic_regeneration_started": False,
            "provider_execution_started": False,
        }


__all__ = ["Task111AuditInputController"]
