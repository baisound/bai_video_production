"""TASK-038 crash-safe persistence for immutable Candidate audits and Human decisions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .atomic import AtomicJsonWriter, AtomicWriteResult
from .candidate_audit import (
    AuditDimension,
    AuditFinding,
    AuditRecord,
    AuditorKind,
    CandidateAuditRegistry,
    FindingSeverity,
    HumanCandidateDecision,
    HumanDecision,
)
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes


_MAX_BYTES = 8 * 1024 * 1024


def _body(registry: CandidateAuditRegistry) -> dict[str, Any]:
    body: dict[str, Any] = {
        "snapshot_version": "1.0.0",
        "task_owner": "TASK-038",
        "audits": [registry.audit_records[key].to_dict() for key in sorted(registry.audit_records)],
        "human_decisions": [registry.decisions[key].to_dict() for key in sorted(registry.decisions)],
        "asset_bytes_embedded": False,
        "physical_delete_authority": False,
    }
    body["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def _parse(document: dict[str, Any]) -> CandidateAuditRegistry:
    if document.get("snapshot_version") != "1.0.0":
        raise ProductError("ERR_AUDIT_SNAPSHOT_VERSION", "Unsupported audit snapshot version", ProductErrorCategory.DATA_INTEGRITY)
    expected = document.get("snapshot_sha256")
    body = {k: v for k, v in document.items() if k != "snapshot_sha256"}
    if expected != sha256_bytes(canonical_json_bytes(body)):
        raise ProductError("ERR_AUDIT_SNAPSHOT_CHECKSUM", "Audit snapshot checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
    if document.get("asset_bytes_embedded") is not False or document.get("physical_delete_authority") is not False:
        raise ProductError("ERR_AUDIT_SNAPSHOT_BOUNDARY", "Audit snapshot violates asset/retention boundaries", ProductErrorCategory.SECURITY)
    try:
        audit_rows = document["audits"]
        decision_rows = document["human_decisions"]
        if not isinstance(audit_rows, list) or not isinstance(decision_rows, list):
            raise TypeError("rows must be lists")
        audits = []
        for row in audit_rows:
            findings = tuple(
                AuditFinding(
                    finding_id=item["finding_id"],
                    dimension=AuditDimension(item["dimension"]),
                    severity=FindingSeverity(item["severity"]),
                    code=item["code"],
                    summary=item["summary"],
                    critical_violation=bool(item.get("critical_violation", False)),
                )
                for item in row["findings"]
            )
            record = AuditRecord(
                audit_id=row["audit_id"],
                candidate_id=row["candidate_id"],
                asset_sha256=row["asset_sha256"],
                contract_refs=tuple(row.get("contract_refs", [])),
                auditor_kind=AuditorKind(row["auditor_kind"]),
                auditor_id=row["auditor_id"],
                auditor_version=row.get("auditor_version"),
                dimension_scores=dict(row.get("dimension_scores", {})),
                findings=findings,
                failure_codes=tuple(row.get("failure_codes", [])),
                alternate_use_proposals=tuple(row.get("alternate_use_proposals", [])),
            )
            if row.get("record_sha256") != record.to_dict()["record_sha256"]:
                raise ProductError("ERR_AUDIT_RECORD_CHECKSUM", "Audit record checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
            audits.append(record)
        decisions = tuple(
            HumanDecision(
                decision_id=row["decision_id"],
                candidate_id=row["candidate_id"],
                audit_refs=tuple(row["audit_refs"]),
                decision=HumanCandidateDecision(row["decision"]),
                actor_id=row["actor_id"],
                reason_codes=tuple(row.get("reason_codes", [])),
                notes=row.get("notes"),
            )
            for row in decision_rows
        )
    except ProductError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductError("ERR_AUDIT_SNAPSHOT_INVALID", "Audit snapshot contains invalid records", ProductErrorCategory.DATA_INTEGRITY) from exc

    registry = CandidateAuditRegistry()
    for record in audits:
        registry.add_audit(record)
    for decision in decisions:
        registry.add_human_decision(decision)
    if len(registry.audit_records) != len(audit_rows) or len(registry.decisions) != len(decision_rows):
        raise ProductError("ERR_AUDIT_SNAPSHOT_DUPLICATE_ID", "Audit snapshot contains duplicate identities", ProductErrorCategory.DATA_INTEGRITY)
    return registry


class CandidateAuditSnapshotStore:
    @staticmethod
    def snapshot(registry: CandidateAuditRegistry) -> dict[str, Any]:
        return _body(registry)

    @staticmethod
    def load(path: str | Path) -> CandidateAuditRegistry:
        target = Path(path)
        if target.is_symlink() or not target.is_file():
            raise ProductError("ERR_AUDIT_SNAPSHOT_FILE_INVALID", "Audit snapshot must be a regular non-symlink file", ProductErrorCategory.VALIDATION)
        size = target.stat().st_size
        if size <= 0 or size > _MAX_BYTES:
            raise ProductError("ERR_AUDIT_SNAPSHOT_SIZE", "Audit snapshot size is outside the allowed bound", ProductErrorCategory.VALIDATION, details={"size_bytes": size})
        try:
            value = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_AUDIT_SNAPSHOT_READ", "Audit snapshot could not be read as UTF-8 JSON", ProductErrorCategory.DATA_INTEGRITY) from exc
        if not isinstance(value, dict):
            raise ProductError("ERR_AUDIT_SNAPSHOT_INVALID", "Audit snapshot root must be an object", ProductErrorCategory.DATA_INTEGRITY)
        return _parse(value)

    @staticmethod
    def save(path: str | Path, registry: CandidateAuditRegistry, *, expected_previous_snapshot_sha256: str | None = None) -> AtomicWriteResult:
        target = Path(path)
        if target.is_symlink():
            raise ProductError("ERR_AUDIT_SNAPSHOT_FILE_INVALID", "Refusing to replace a symlink audit snapshot", ProductErrorCategory.SECURITY)
        if target.exists():
            if not target.is_file():
                raise ProductError("ERR_AUDIT_SNAPSHOT_FILE_INVALID", "Audit snapshot target must be a regular file", ProductErrorCategory.VALIDATION)
            if expected_previous_snapshot_sha256 is None:
                raise ProductError("ERR_AUDIT_SNAPSHOT_CAS_REQUIRED", "Replacing an audit snapshot requires its exact previous checksum", ProductErrorCategory.AUTHORIZATION)
            current = _body(CandidateAuditSnapshotStore.load(target))["snapshot_sha256"]
            if current != expected_previous_snapshot_sha256:
                raise ProductError("ERR_AUDIT_SNAPSHOT_REVISION_CONFLICT", "Audit snapshot changed before save; reload before retry", ProductErrorCategory.STATE, details={"current_snapshot_sha256": current})
        elif expected_previous_snapshot_sha256 is not None:
            raise ProductError("ERR_AUDIT_SNAPSHOT_PREVIOUS_MISSING", "Expected previous audit snapshot does not exist", ProductErrorCategory.STATE)
        document = _body(registry)
        return AtomicJsonWriter.write(target, document, validator=lambda value: _parse(value))
