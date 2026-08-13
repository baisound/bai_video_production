"""TASK-013 Visual Compliance Gate foundation.

The gate evaluates structured inspection facts against a versioned contract. It
never calls a vision/provider model itself and never turns aesthetic quality into
an approval when a required contract condition fails.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Mapping, Iterable

from .errors import ProductError, ProductErrorCategory
from .prompt_registry import RegenerationStrategy
from .serialization import canonical_json_bytes, sha256_bytes


_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _sha(value: str, name: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


class VisualCheckState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNVERIFIED = "UNVERIFIED"


class CoordinateConvention(str, Enum):
    VIEWER = "VIEWER"
    SUBJECT = "SUBJECT"
    EXPLICIT_MIXED = "EXPLICIT_MIXED"


class VisualDecision(str, Enum):
    ELIGIBLE_FOR_HUMAN_APPROVAL = "ELIGIBLE_FOR_HUMAN_APPROVAL"
    REJECT = "REJECT"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class VisualContractCheck:
    check_id: str
    description: str
    critical: bool

    def __post_init__(self) -> None:
        _id(self.check_id, "check_id")
        if not self.description.strip() or len(self.description) > 1000 or "\x00" in self.description:
            raise ValueError("description is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {"check_id": self.check_id, "description": self.description, "critical": self.critical}


@dataclass(frozen=True, slots=True)
class VisualComplianceContract:
    contract_id: str
    contract_version: int
    scene_id: str
    checks: tuple[VisualContractCheck, ...]
    coordinate_convention: CoordinateConvention
    character_contract_ref: str | None = None
    continuity_contract_ref: str | None = None

    def __post_init__(self) -> None:
        _id(self.contract_id, "contract_id")
        _id(self.scene_id, "scene_id")
        if self.contract_version < 1:
            raise ValueError("contract_version must be >= 1")
        if not self.checks:
            raise ValueError("visual compliance contract requires checks")
        ids = [item.check_id for item in self.checks]
        if len(ids) != len(set(ids)):
            raise ValueError("visual compliance check IDs must be unique")
        for name, value in (
            ("character_contract_ref", self.character_contract_ref),
            ("continuity_contract_ref", self.continuity_contract_ref),
        ):
            if value is not None:
                _id(value, name)

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "contract_schema_version": "1.0.0",
            "task_owner": "TASK-013",
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "scene_id": self.scene_id,
            "coordinate_convention": self.coordinate_convention.value,
            "character_contract_ref": self.character_contract_ref,
            "continuity_contract_ref": self.continuity_contract_ref,
            "checks": [item.to_dict() for item in self.checks],
        }
        body["contract_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(frozen=True, slots=True)
class VisualScoreSet:
    contract_compliance: float
    character_consistency: float
    composition: float
    aesthetic: float

    def __post_init__(self) -> None:
        for value in (self.contract_compliance, self.character_consistency, self.composition, self.aesthetic):
            if isinstance(value, bool) or not 0.0 <= value <= 1.0:
                raise ValueError("visual scores must be 0..1")

    @property
    def weighted_score(self) -> float:
        return (
            self.contract_compliance * 0.50
            + self.character_consistency * 0.20
            + self.composition * 0.20
            + self.aesthetic * 0.10
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "contract_compliance": self.contract_compliance,
            "character_consistency": self.character_consistency,
            "composition": self.composition,
            "aesthetic": self.aesthetic,
            "weighted_score": round(self.weighted_score, 6),
        }


@dataclass(frozen=True, slots=True)
class VisualInspectionReport:
    candidate_id: str
    candidate_asset_sha256: str
    contract_id: str
    contract_version: int
    contract_sha256: str
    checks: Mapping[str, VisualCheckState]
    scores: VisualScoreSet
    failure_codes: tuple[str, ...]
    inspector_kind: str
    inspector_model_ref: str | None

    def __post_init__(self) -> None:
        _id(self.candidate_id, "candidate_id")
        _sha(self.candidate_asset_sha256, "candidate_asset_sha256")
        _id(self.contract_id, "contract_id")
        _sha(self.contract_sha256, "contract_sha256")
        if self.contract_version < 1:
            raise ValueError("contract_version must be >= 1")
        if not self.inspector_kind.strip() or len(self.inspector_kind) > 100:
            raise ValueError("inspector_kind is invalid")
        if self.inspector_model_ref is not None and (not self.inspector_model_ref.strip() or len(self.inspector_model_ref) > 300):
            raise ValueError("inspector_model_ref is invalid")
        for code in self.failure_codes:
            _id(code, "failure_code")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "inspection_version": "1.0.0",
            "task_owner": "TASK-013",
            "candidate_id": self.candidate_id,
            "candidate_asset_sha256": self.candidate_asset_sha256,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "contract_sha256": self.contract_sha256,
            "checks": {key: self.checks[key].value for key in sorted(self.checks)},
            "scores": self.scores.to_dict(),
            "failure_codes": list(self.failure_codes),
            "inspector_kind": self.inspector_kind,
            "inspector_model_ref": self.inspector_model_ref,
            "candidate_path_persisted": False,
            "human_approval_recorded": False,
        }
        body["inspection_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(frozen=True, slots=True)
class VisualComplianceDecision:
    decision: VisualDecision
    critical_pass: bool
    failed_check_ids: tuple[str, ...]
    unverified_check_ids: tuple[str, ...]
    inspection: VisualInspectionReport

    @property
    def eligible_for_human_approval(self) -> bool:
        return self.decision is VisualDecision.ELIGIBLE_FOR_HUMAN_APPROVAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_version": "1.0.0",
            "task_owner": "TASK-013",
            "decision": self.decision.value,
            "critical_pass": self.critical_pass,
            "failed_check_ids": list(self.failed_check_ids),
            "unverified_check_ids": list(self.unverified_check_ids),
            "eligible_for_human_approval": self.eligible_for_human_approval,
            "inspection": self.inspection.to_dict(),
            "automatic_asset_approval": False,
        }


class VisualComplianceGate:
    @staticmethod
    def evaluate(
        contract: VisualComplianceContract,
        *,
        candidate_id: str,
        candidate_asset_sha256: str,
        observed_checks: Mapping[str, VisualCheckState],
        scores: VisualScoreSet,
        failure_codes: Iterable[str] = (),
        inspector_kind: str,
        inspector_model_ref: str | None = None,
    ) -> VisualComplianceDecision:
        expected = {item.check_id for item in contract.checks}
        if set(observed_checks) != expected:
            raise ProductError(
                "ERR_VISUAL_COMPLIANCE_CHECK_SET_MISMATCH",
                "Visual inspection must report every contract check exactly once",
                ProductErrorCategory.DATA_INTEGRITY,
                details={
                    "missing": sorted(expected - set(observed_checks)),
                    "unexpected": sorted(set(observed_checks) - expected),
                },
            )
        contract_hash = contract.to_dict()["contract_sha256"]
        failed = tuple(item.check_id for item in contract.checks if observed_checks[item.check_id] is VisualCheckState.FAIL)
        unverified = tuple(item.check_id for item in contract.checks if observed_checks[item.check_id] is VisualCheckState.UNVERIFIED)
        critical_failed = tuple(item.check_id for item in contract.checks if item.critical and observed_checks[item.check_id] is VisualCheckState.FAIL)
        if failed:
            decision = VisualDecision.REJECT
        elif unverified:
            decision = VisualDecision.HUMAN_REVIEW_REQUIRED
        else:
            decision = VisualDecision.ELIGIBLE_FOR_HUMAN_APPROVAL
        inspection = VisualInspectionReport(
            candidate_id=candidate_id,
            candidate_asset_sha256=candidate_asset_sha256,
            contract_id=contract.contract_id,
            contract_version=contract.contract_version,
            contract_sha256=contract_hash,
            checks=dict(observed_checks),
            scores=scores,
            failure_codes=tuple(dict.fromkeys(failure_codes)),
            inspector_kind=inspector_kind,
            inspector_model_ref=inspector_model_ref,
        )
        return VisualComplianceDecision(
            decision=decision,
            critical_pass=not critical_failed,
            failed_check_ids=failed,
            unverified_check_ids=unverified,
            inspection=inspection,
        )

    @staticmethod
    def require_human_approval_eligible(decision: VisualComplianceDecision) -> None:
        if decision.eligible_for_human_approval:
            return
        category = ProductErrorCategory.HUMAN_REVIEW_REQUIRED if decision.decision is VisualDecision.HUMAN_REVIEW_REQUIRED else ProductErrorCategory.VALIDATION
        raise ProductError(
            "ERR_VISUAL_COMPLIANCE_NOT_ELIGIBLE",
            "Candidate does not satisfy the Visual Compliance contract",
            category,
            details={
                "decision": decision.decision.value,
                "failed_check_ids": list(decision.failed_check_ids),
                "unverified_check_ids": list(decision.unverified_check_ids),
            },
        )


class AdaptiveVisualRegenerationPlanner:
    @staticmethod
    def next_strategy(
        reports: Iterable[VisualInspectionReport],
        *,
        current_strategy: RegenerationStrategy,
        repeated_failure_threshold: int = 2,
    ) -> RegenerationStrategy:
        if repeated_failure_threshold < 2:
            raise ValueError("repeated_failure_threshold must be >= 2")
        rows = tuple(reports)
        if not rows or not rows[-1].failure_codes:
            return current_strategy
        target = set(rows[-1].failure_codes)
        streak = 0
        for row in reversed(rows):
            if not target.intersection(row.failure_codes):
                break
            streak += 1
        if streak < repeated_failure_threshold:
            return current_strategy
        return RegenerationStrategy(min(int(current_strategy) + 1, int(RegenerationStrategy.HUMAN_COMPOSITION_FIX)))
