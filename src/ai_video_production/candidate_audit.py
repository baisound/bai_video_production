"""TASK-038 immutable Candidate audit and Human decision foundation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Mapping

from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes


_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


class AuditorKind(str, Enum):
    AI = "AI"
    HUMAN = "HUMAN"


class FindingSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuditDimension(str, Enum):
    CONTRACT = "CONTRACT"
    IDENTITY = "IDENTITY"
    GEOMETRY = "GEOMETRY"
    CONTINUITY = "CONTINUITY"
    TECHNICAL = "TECHNICAL"
    AUDIO = "AUDIO"
    COMPOSITION = "COMPOSITION"
    POLICY = "POLICY"


class HumanCandidateDecision(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    ALTERNATE_USE = "ALTERNATE_USE"
    NEEDS_REGENERATION = "NEEDS_REGENERATION"


@dataclass(frozen=True, slots=True)
class AuditFinding:
    finding_id: str
    dimension: AuditDimension
    severity: FindingSeverity
    code: str
    summary: str
    critical_violation: bool = False

    def __post_init__(self) -> None:
        _id(self.finding_id, "finding_id")
        _id(self.code, "code")
        if not self.summary.strip() or len(self.summary) > 2000 or "\x00" in self.summary:
            raise ValueError("summary is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "dimension": self.dimension.value,
            "severity": self.severity.value,
            "code": self.code,
            "summary": self.summary,
            "critical_violation": self.critical_violation,
        }


@dataclass(frozen=True, slots=True)
class AuditRecord:
    audit_id: str
    candidate_id: str
    asset_sha256: str
    contract_refs: tuple[str, ...]
    auditor_kind: AuditorKind
    auditor_id: str
    auditor_version: str | None
    dimension_scores: Mapping[str, float]
    findings: tuple[AuditFinding, ...]
    failure_codes: tuple[str, ...]
    alternate_use_proposals: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _id(self.audit_id, "audit_id")
        _id(self.candidate_id, "candidate_id")
        if not _SHA_RE.fullmatch(self.asset_sha256):
            raise ValueError("asset_sha256 is invalid")
        _id(self.auditor_id, "auditor_id")
        if len(set(self.contract_refs)) != len(self.contract_refs):
            raise ValueError("duplicate contract_refs")
        for value in self.contract_refs + self.failure_codes:
            _id(value, "reference")
        for name, score in self.dimension_scores.items():
            _id(str(name), "dimension score key")
            if isinstance(score, bool) or not 0 <= float(score) <= 100:
                raise ValueError("dimension score must be 0..100")
        for proposal in self.alternate_use_proposals:
            if not proposal.strip() or len(proposal) > 1000:
                raise ValueError("alternate use proposal is invalid")

    @property
    def critical_violation(self) -> bool:
        return any(item.critical_violation for item in self.findings)

    def to_dict(self) -> dict[str, Any]:
        body = {
            "record_version": "1.0.0",
            "task_owner": "TASK-038",
            "audit_id": self.audit_id,
            "candidate_id": self.candidate_id,
            "asset_sha256": self.asset_sha256,
            "contract_refs": list(self.contract_refs),
            "auditor_kind": self.auditor_kind.value,
            "auditor_id": self.auditor_id,
            "auditor_version": self.auditor_version,
            "dimension_scores": dict(sorted((key, float(value)) for key, value in self.dimension_scores.items())),
            "findings": [item.to_dict() for item in self.findings],
            "failure_codes": list(self.failure_codes),
            "alternate_use_proposals": list(self.alternate_use_proposals),
            "critical_violation": self.critical_violation,
        }
        body["record_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(frozen=True, slots=True)
class HumanDecision:
    decision_id: str
    candidate_id: str
    audit_refs: tuple[str, ...]
    decision: HumanCandidateDecision
    actor_id: str
    reason_codes: tuple[str, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        _id(self.decision_id, "decision_id")
        _id(self.candidate_id, "candidate_id")
        _id(self.actor_id, "actor_id")
        if not self.audit_refs or len(set(self.audit_refs)) != len(self.audit_refs):
            raise ValueError("audit_refs must be non-empty and unique")
        for value in self.audit_refs + self.reason_codes:
            _id(value, "reference")
        if self.notes is not None and (len(self.notes) > 4000 or "\x00" in self.notes):
            raise ValueError("notes are invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_version": "1.0.0",
            "task_owner": "TASK-038",
            "decision_id": self.decision_id,
            "candidate_id": self.candidate_id,
            "audit_refs": list(self.audit_refs),
            "decision": self.decision.value,
            "actor_id": self.actor_id,
            "reason_codes": list(self.reason_codes),
            "notes": self.notes,
            "ai_score_is_human_decision": False,
        }


class CandidateAuditRegistry:
    def __init__(self) -> None:
        self.audit_records: dict[str, AuditRecord] = {}
        self.decisions: dict[str, HumanDecision] = {}

    def add_audit(self, record: AuditRecord) -> None:
        if record.audit_id in self.audit_records:
            raise ProductError("ERR_AUDIT_RECORD_CONFLICT", "audit_id already exists", ProductErrorCategory.STATE)
        self.audit_records[record.audit_id] = record

    def add_human_decision(self, decision: HumanDecision) -> None:
        if decision.decision_id in self.decisions:
            raise ProductError("ERR_AUDIT_DECISION_CONFLICT", "decision_id already exists", ProductErrorCategory.STATE)
        referenced = []
        for audit_id in decision.audit_refs:
            audit = self.audit_records.get(audit_id)
            if audit is None:
                raise ProductError("ERR_AUDIT_REFERENCE_NOT_FOUND", "Human decision references an unknown audit", ProductErrorCategory.DATA_INTEGRITY)
            if audit.candidate_id != decision.candidate_id:
                raise ProductError("ERR_AUDIT_CANDIDATE_MISMATCH", "Human decision audit belongs to a different Candidate", ProductErrorCategory.DATA_INTEGRITY)
            referenced.append(audit)
        self.decisions[decision.decision_id] = decision

    def candidate_history(self, candidate_id: str) -> dict[str, Any]:
        audits = [item for item in self.audit_records.values() if item.candidate_id == candidate_id]
        decisions = [item for item in self.decisions.values() if item.candidate_id == candidate_id]
        audits.sort(key=lambda item: item.audit_id)
        decisions.sort(key=lambda item: item.decision_id)
        return {
            "candidate_id": candidate_id,
            "audits": [item.to_dict() for item in audits],
            "human_decisions": [item.to_dict() for item in decisions],
            "human_final_authority_preserved": True,
        }
