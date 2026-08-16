"""TASK-021 provider-neutral, body-free operations dashboard contracts.

The module validates immutable source projections and classifies operational
attention.  It never reads source stores, controls jobs or applications, sends
alerts, opens private details, or performs a production effect.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, ClassVar, Mapping, Sequence

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_ID = "bai.task021.integrated-dashboard-operations.v1"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_REASON_RE = re.compile(r"[A-Z][A-Z0-9_]{1,95}")
_MAX_SOURCES = 256
_MAX_ITEMS = 4096
_MAX_ALERTS = 1024
_MAX_INCIDENTS = 1024
_MAX_PROPOSALS = 256
_MAX_REASONS = 64
_MAX_PAGE_SIZE = 200


class ContractState(str, Enum):
    CANONICAL_REF_NOT_PROVIDED = "CANONICAL_REF_NOT_PROVIDED"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class FreshnessState(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"
    UNKNOWN = "UNKNOWN"


class DashboardSourceKind(str, Enum):
    PRODUCTION_DASHBOARD = "PRODUCTION_DASHBOARD"
    DURABLE_JOB = "DURABLE_JOB"
    CHECKPOINT = "CHECKPOINT"
    AUDIT = "AUDIT"
    RESOURCE = "RESOURCE"
    PRIVACY_PUBLIC = "PRIVACY_PUBLIC"
    EVIDENCE = "EVIDENCE"


class DurableJobViewState(str, Enum):
    QUEUED = "QUEUED"
    PREFLIGHT = "PREFLIGHT"
    READY = "READY"
    DISPATCHING = "DISPATCHING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"


class EvidenceResultState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    UNKNOWN = "UNKNOWN"


class DashboardIncidentState(str, Enum):
    ACTIVE = "ACTIVE"
    RESOLVED_PROVEN = "RESOLVED_PROVEN"
    UNKNOWN = "UNKNOWN"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class AlertLifecycle(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED_PROVEN = "RESOLVED_PROVEN"
    SUPPRESSED_BY_POLICY = "SUPPRESSED_BY_POLICY"
    UNKNOWN = "UNKNOWN"


class CoverageState(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class DashboardSnapshotState(str, Enum):
    ACTION_REQUIRED = "ACTION_REQUIRED"
    DEGRADED = "DEGRADED"
    NO_ACTIVE_INCIDENT_PROVEN = "NO_ACTIVE_INCIDENT_PROVEN"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class QuerySortOrder(str, Enum):
    UPDATED_AT_ASC = "UPDATED_AT_ASC"
    UPDATED_AT_DESC = "UPDATED_AT_DESC"
    SEVERITY_DESC_UPDATED_AT_ASC = "SEVERITY_DESC_UPDATED_AT_ASC"


class DashboardOperationKind(str, Enum):
    ACK_ALERT = "ACK_ALERT"
    REQUEST_RECONCILE = "REQUEST_RECONCILE"
    REQUEST_PAUSE = "REQUEST_PAUSE"
    REQUEST_CANCEL = "REQUEST_CANCEL"
    REQUEST_RESUME = "REQUEST_RESUME"
    OPEN_HUMAN_REVIEW = "OPEN_HUMAN_REVIEW"
    REQUEST_PRIVATE_DETAIL = "REQUEST_PRIVATE_DETAIL"


class OperationProposalState(str, Enum):
    PROPOSED = "PROPOSED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class HumanOperationDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REVISE = "REVISE"


class ExternalExecutionState(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


def _id(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    folded = value.casefold()
    if (
        "\\" in value or value.startswith("/") or re.match(r"^[A-Za-z]:/", value)
        or ".." in value.split("/")
        or any(term in folded for term in ("credential", "password", "secret", "private-key", "access-token"))
    ):
        raise ValueError(f"{name} violates the body-free boundary")
    return value


def _digest(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a SHA-256 digest")
    return validate_sha256(value, field_name=name)


def _time(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{name} must be UTC RFC3339")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be UTC RFC3339") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{name} must be UTC RFC3339")
    return value


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value[:-1] + "+00:00")


def _enum(kind: type[Enum], value: Any, name: str) -> Enum:
    try:
        return kind(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


def _keys(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _int(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} is outside its cap")
    return value


def _ordered_unique(
    values: Any, name: str, limit: int, *, digest: bool = False,
    enum: type[Enum] | None = None, sorted_required: bool = False,
) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{name} must be an ordered array")
    result = tuple(values)
    if len(result) > limit or len(result) != len(set(result)):
        raise ValueError(f"{name} must be unique and bounded")
    if sorted_required and result != tuple(sorted(result)):
        raise ValueError(f"{name} must use canonical sorted order")
    for item in result:
        if digest:
            _digest(item, name)
        elif enum is not None:
            _enum(enum, item, name)
        else:
            _id(item, name)
    return result


def _reasons(values: Any) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        raise ValueError("reason_codes must be an ordered array")
    result = tuple(values)
    if len(result) > _MAX_REASONS or len(result) != len(set(result)):
        raise ValueError("reason_codes must be unique and bounded")
    if any(not isinstance(item, str) or not _REASON_RE.fullmatch(item) for item in result):
        raise ValueError("reason_codes contains an invalid reason")
    return result


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return copy.deepcopy(value)


def _hashed(body: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(body))
    result["record_sha256"] = sha256_bytes(canonical_json_bytes(result))
    return result


def _check_hash(value: Mapping[str, Any]) -> None:
    supplied = _digest(value["record_sha256"], "record_sha256")
    body = {key: copy.deepcopy(item) for key, item in value.items() if key != "record_sha256"}
    if supplied != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError("record_sha256 mismatch")


def _revision(value: Mapping[str, Any], name: str) -> None:
    revision = _int(value["revision"], f"{name}.revision", 1, 2_147_483_647)
    parent = _digest(value["parent_record_sha256"], "parent_record_sha256", nullable=True)
    if (revision == 1) != (parent is None):
        raise ValueError(f"{name} parent/revision mismatch")


def _policy(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "policy_id", "revision", "parent_record_sha256",
        "max_source_age_seconds", "max_page_size", "max_sources", "max_items",
        "max_alerts", "max_incidents", "authority_ref", "authority_sha256",
        "effective_at", "expires_at", "record_sha256",
    }
    _keys(value, fields, "DashboardProjectionPolicyRevision")
    _id(value["policy_id"], "policy_id")
    _revision(value, "policy")
    _int(value["max_source_age_seconds"], "max_source_age_seconds", 1, 31_536_000)
    _int(value["max_page_size"], "max_page_size", 1, _MAX_PAGE_SIZE)
    _int(value["max_sources"], "max_sources", 1, _MAX_SOURCES)
    _int(value["max_items"], "max_items", 1, _MAX_ITEMS)
    _int(value["max_alerts"], "max_alerts", 1, _MAX_ALERTS)
    _int(value["max_incidents"], "max_incidents", 1, _MAX_INCIDENTS)
    _id(value["authority_ref"], "authority_ref")
    _digest(value["authority_sha256"], "authority_sha256")
    effective = _time(value["effective_at"], "effective_at")
    expires = _time(value["expires_at"], "expires_at", nullable=True)
    if expires is not None and _dt(expires) <= _dt(effective):
        raise ValueError("expires_at must follow effective_at")


def _source(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "source_id", "source_kind", "contract_state", "source_ref",
        "source_sha256", "source_revision", "observed_at", "freshness_state",
        "validity_state", "public_projection_only", "body_included",
        "private_path_included", "record_sha256",
    }
    _keys(value, fields, "DashboardSourceBinding")
    _id(value["source_id"], "source_id")
    kind = _enum(DashboardSourceKind, value["source_kind"], "source_kind")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    freshness = _enum(FreshnessState, value["freshness_state"], "freshness_state")
    validity = _enum(FreshnessState, value["validity_state"], "validity_state")
    if value["body_included"] is not False or value["private_path_included"] is not False:
        raise ValueError("Dashboard source must be body/path free")
    if not isinstance(value["public_projection_only"], bool):
        raise ValueError("public_projection_only must be boolean")
    if kind is DashboardSourceKind.PRIVACY_PUBLIC and value["public_projection_only"] is not True:
        raise ValueError("Privacy source must use its canonical public projection")
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in ("source_ref", "source_sha256", "source_revision", "observed_at")):
            raise ValueError("unresolved source invents canonical fields")
        if freshness is not FreshnessState.UNKNOWN or validity is not FreshnessState.UNKNOWN:
            raise ValueError("unresolved source must remain UNKNOWN")
        return
    _id(value["source_ref"], "source_ref", nullable=True)
    _digest(value["source_sha256"], "source_sha256", nullable=True)
    if value["source_revision"] is not None:
        _int(value["source_revision"], "source_revision", 1, 2_147_483_647)
    _time(value["observed_at"], "observed_at", nullable=True)
    if state is ContractState.BOUND_VERIFIED and any(
        value[field] is None for field in ("source_ref", "source_sha256", "source_revision", "observed_at")
    ):
        raise ValueError("BOUND_VERIFIED source is incomplete")


def _query(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "query_id", "project_id", "source_kinds", "state_filters",
        "page_size", "cursor_sha256", "sort_order", "body_included", "record_sha256",
    }
    _keys(value, fields, "DashboardQueryIntent")
    _id(value["query_id"], "query_id")
    _id(value["project_id"], "project_id")
    _ordered_unique(
        value["source_kinds"], "source_kinds", len(DashboardSourceKind),
        enum=DashboardSourceKind, sorted_required=True,
    )
    _ordered_unique(value["state_filters"], "state_filters", 32, sorted_required=True)
    _int(value["page_size"], "page_size", 1, _MAX_PAGE_SIZE)
    _digest(value["cursor_sha256"], "cursor_sha256", nullable=True)
    _enum(QuerySortOrder, value["sort_order"], "sort_order")
    if value["body_included"] is not False:
        raise ValueError("Dashboard query must be body-free")


def _job(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "view_id", "source_binding_sha256", "job_sha256",
        "operation_identity", "job_state", "state_version", "attempt", "updated_at",
        "freshness_state", "reason_codes", "effect_started_by_dashboard", "record_sha256",
    }
    _keys(value, fields, "DashboardJobReadModel")
    _id(value["view_id"], "view_id")
    _digest(value["source_binding_sha256"], "source_binding_sha256")
    _digest(value["job_sha256"], "job_sha256")
    _id(value["operation_identity"], "operation_identity")
    _enum(DurableJobViewState, value["job_state"], "job_state")
    _int(value["state_version"], "state_version", 1, 2_147_483_647)
    _int(value["attempt"], "attempt", 0, 2_147_483_647)
    _time(value["updated_at"], "updated_at")
    _enum(FreshnessState, value["freshness_state"], "freshness_state")
    _reasons(value["reason_codes"])
    if value["effect_started_by_dashboard"] is not False:
        raise ValueError("Dashboard cannot start a Job effect")


def _evidence(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "view_id", "source_binding_sha256", "evidence_record_type",
        "evidence_sha256", "result_state", "observed_at", "freshness_state",
        "reason_codes", "body_included", "record_sha256",
    }
    _keys(value, fields, "DashboardEvidenceReadModel")
    _id(value["view_id"], "view_id")
    _digest(value["source_binding_sha256"], "source_binding_sha256")
    _id(value["evidence_record_type"], "evidence_record_type")
    _digest(value["evidence_sha256"], "evidence_sha256")
    _enum(EvidenceResultState, value["result_state"], "result_state")
    _time(value["observed_at"], "observed_at")
    _enum(FreshnessState, value["freshness_state"], "freshness_state")
    _reasons(value["reason_codes"])
    if value["body_included"] is not False:
        raise ValueError("Evidence read model must be body-free")


def _incident(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "view_id", "source_binding_sha256", "incident_id",
        "incident_state", "severity", "observed_at", "resolved_receipt_sha256",
        "freshness_state", "reason_codes", "absence_assumed_healthy", "record_sha256",
    }
    _keys(value, fields, "DashboardIncidentReadModel")
    _id(value["view_id"], "view_id")
    _digest(value["source_binding_sha256"], "source_binding_sha256")
    _id(value["incident_id"], "incident_id")
    state = _enum(DashboardIncidentState, value["incident_state"], "incident_state")
    _enum(AlertSeverity, value["severity"], "severity")
    _time(value["observed_at"], "observed_at")
    _digest(value["resolved_receipt_sha256"], "resolved_receipt_sha256", nullable=True)
    if (state is DashboardIncidentState.RESOLVED_PROVEN) != (value["resolved_receipt_sha256"] is not None):
        raise ValueError("resolved incident requires an exact receipt only")
    _enum(FreshnessState, value["freshness_state"], "freshness_state")
    _reasons(value["reason_codes"])
    if value["absence_assumed_healthy"] is not False:
        raise ValueError("incident absence cannot be assumed healthy")


def _alert(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "alert_id", "policy_sha256", "subject_sha256", "incident_sha256",
        "severity", "lifecycle", "acknowledgement_receipt_sha256", "reason_codes",
        "classified_at", "effect_started_by_dashboard", "record_sha256",
    }
    _keys(value, fields, "DashboardAlertClassificationReceipt")
    _id(value["alert_id"], "alert_id")
    for field in ("policy_sha256", "subject_sha256"):
        _digest(value[field], field)
    _digest(value["incident_sha256"], "incident_sha256", nullable=True)
    _enum(AlertSeverity, value["severity"], "severity")
    lifecycle = _enum(AlertLifecycle, value["lifecycle"], "lifecycle")
    _digest(value["acknowledgement_receipt_sha256"], "acknowledgement_receipt_sha256", nullable=True)
    if (lifecycle is AlertLifecycle.ACKNOWLEDGED) != (value["acknowledgement_receipt_sha256"] is not None):
        raise ValueError("ACKNOWLEDGED requires its exact receipt and is not resolution")
    _reasons(value["reason_codes"])
    _time(value["classified_at"], "classified_at")
    if value["effect_started_by_dashboard"] is not False:
        raise ValueError("Dashboard cannot send an alert effect")


def _snapshot(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "snapshot_id", "revision", "parent_record_sha256", "project_id",
        "policy_sha256", "query_sha256", "source_binding_hashes", "job_view_hashes",
        "evidence_view_hashes", "incident_view_hashes", "alert_hashes", "coverage_state",
        "snapshot_state", "source_watermark_sha256", "generated_at", "body_included",
        "private_detail_included", "effect_started_by_dashboard", "record_sha256",
    }
    _keys(value, fields, "IntegratedDashboardSnapshotRevision")
    _id(value["snapshot_id"], "snapshot_id")
    _revision(value, "snapshot")
    _id(value["project_id"], "project_id")
    _digest(value["policy_sha256"], "policy_sha256")
    _digest(value["query_sha256"], "query_sha256")
    sources = _ordered_unique(
        value["source_binding_hashes"], "source_binding_hashes", _MAX_SOURCES,
        digest=True, sorted_required=True,
    )
    if not sources:
        raise ValueError("snapshot requires a source binding")
    _ordered_unique(
        value["job_view_hashes"], "job_view_hashes", _MAX_ITEMS,
        digest=True, sorted_required=True,
    )
    _ordered_unique(
        value["evidence_view_hashes"], "evidence_view_hashes", _MAX_ITEMS,
        digest=True, sorted_required=True,
    )
    incidents = _ordered_unique(
        value["incident_view_hashes"], "incident_view_hashes", _MAX_INCIDENTS,
        digest=True, sorted_required=True,
    )
    _ordered_unique(
        value["alert_hashes"], "alert_hashes", _MAX_ALERTS,
        digest=True, sorted_required=True,
    )
    coverage = _enum(CoverageState, value["coverage_state"], "coverage_state")
    state = _enum(DashboardSnapshotState, value["snapshot_state"], "snapshot_state")
    _digest(value["source_watermark_sha256"], "source_watermark_sha256")
    _time(value["generated_at"], "generated_at")
    if state is DashboardSnapshotState.NO_ACTIVE_INCIDENT_PROVEN and coverage is not CoverageState.COMPLETE:
        raise ValueError("no-active-incident state requires complete coverage")
    if any(value[field] is not False for field in ("body_included", "private_detail_included", "effect_started_by_dashboard")):
        raise ValueError("Dashboard snapshot must remain public/body-free/no-effect")


def _proposal(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "proposal_id", "revision", "parent_record_sha256", "snapshot_sha256",
        "operation_kind", "target_source_sha256", "expected_target_state_version",
        "precondition_hashes", "proposal_state", "reason_codes", "created_at", "expires_at",
        "proposal_only", "execution_started", "record_sha256",
    }
    _keys(value, fields, "DashboardOperationProposalRevision")
    _id(value["proposal_id"], "proposal_id")
    _revision(value, "proposal")
    _digest(value["snapshot_sha256"], "snapshot_sha256")
    _enum(DashboardOperationKind, value["operation_kind"], "operation_kind")
    _digest(value["target_source_sha256"], "target_source_sha256")
    if value["expected_target_state_version"] is not None:
        _int(value["expected_target_state_version"], "expected_target_state_version", 1, 2_147_483_647)
    _ordered_unique(
        value["precondition_hashes"], "precondition_hashes", 64,
        digest=True, sorted_required=True,
    )
    _enum(OperationProposalState, value["proposal_state"], "proposal_state")
    _reasons(value["reason_codes"])
    created = _time(value["created_at"], "created_at")
    expires = _time(value["expires_at"], "expires_at")
    if _dt(expires) <= _dt(created):
        raise ValueError("proposal expires_at must follow created_at")
    if value["proposal_only"] is not True or value["execution_started"] is not False:
        raise ValueError("Dashboard operation must remain proposal-only")


def _human(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "contract_state", "confirmation_id", "confirmation_revision",
        "confirmation_sha256", "proposal_sha256", "snapshot_sha256", "target_source_sha256",
        "operation_kind", "reviewer_kind", "decision", "decided_at", "expires_at",
        "one_shot", "consumed", "evidence_ref", "evidence_sha256", "record_sha256",
    }
    _keys(value, fields, "HumanOperationConfirmationBinding")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    nullable = fields - {"record_type", "contract_state", "record_sha256"}
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in nullable):
            raise ValueError("unresolved Human binding invents fields")
        return
    for field in ("confirmation_id", "evidence_ref"):
        _id(value[field], field, nullable=True)
    for field in ("confirmation_sha256", "proposal_sha256", "snapshot_sha256", "target_source_sha256", "evidence_sha256"):
        _digest(value[field], field, nullable=True)
    if value["confirmation_revision"] is not None:
        _int(value["confirmation_revision"], "confirmation_revision", 1, 2_147_483_647)
    if value["operation_kind"] is not None:
        _enum(DashboardOperationKind, value["operation_kind"], "operation_kind")
    if value["reviewer_kind"] not in {"HUMAN", None}:
        raise ValueError("reviewer_kind must be HUMAN")
    if value["decision"] is not None:
        _enum(HumanOperationDecision, value["decision"], "decision")
    _time(value["decided_at"], "decided_at", nullable=True)
    _time(value["expires_at"], "expires_at", nullable=True)
    if value["one_shot"] not in {True, False, None} or value["consumed"] not in {True, False, None}:
        raise ValueError("one_shot/consumed must be boolean or null")
    if state is ContractState.BOUND_VERIFIED:
        if any(value[field] is None for field in nullable):
            raise ValueError("BOUND_VERIFIED Human confirmation is incomplete")
        if value["one_shot"] is not True:
            raise ValueError("Human confirmation must be one-shot")
        if _dt(value["expires_at"]) <= _dt(value["decided_at"]):
            raise ValueError("confirmation expires_at must follow decided_at")


def _execution(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "contract_state", "receipt_id", "receipt_ref", "receipt_sha256",
        "proposal_sha256", "confirmation_sha256", "operation_identity", "external_state",
        "observed_at", "canonical_persistence_verified", "effect_started_by_dashboard",
        "record_sha256",
    }
    _keys(value, fields, "DashboardExecutionReceiptBinding")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    nullable = fields - {"record_type", "contract_state", "effect_started_by_dashboard", "record_sha256"}
    if value["effect_started_by_dashboard"] is not False:
        raise ValueError("Dashboard cannot execute an operation")
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in nullable):
            raise ValueError("unresolved execution receipt invents fields")
        return
    for field in ("receipt_id", "receipt_ref", "operation_identity"):
        _id(value[field], field, nullable=True)
    for field in ("receipt_sha256", "proposal_sha256", "confirmation_sha256"):
        _digest(value[field], field, nullable=True)
    if value["external_state"] is not None:
        external = _enum(ExternalExecutionState, value["external_state"], "external_state")
    else:
        external = None
    _time(value["observed_at"], "observed_at", nullable=True)
    if value["canonical_persistence_verified"] not in {True, False, None}:
        raise ValueError("canonical_persistence_verified must be boolean or null")
    if state is ContractState.BOUND_VERIFIED:
        if any(value[field] is None for field in nullable):
            raise ValueError("BOUND_VERIFIED execution receipt is incomplete")
        if external is ExternalExecutionState.ACCEPTED and value["canonical_persistence_verified"] is not True:
            raise ValueError("ACCEPTED requires canonical persistence proof")


_VALIDATORS = {
    "DashboardProjectionPolicyRevision": _policy,
    "DashboardSourceBinding": _source,
    "DashboardQueryIntent": _query,
    "DashboardJobReadModel": _job,
    "DashboardEvidenceReadModel": _evidence,
    "DashboardIncidentReadModel": _incident,
    "DashboardAlertClassificationReceipt": _alert,
    "IntegratedDashboardSnapshotRevision": _snapshot,
    "DashboardOperationProposalRevision": _proposal,
    "HumanOperationConfirmationBinding": _human,
    "DashboardExecutionReceiptBinding": _execution,
}


@dataclass(frozen=True, slots=True)
class _Record:
    data: Mapping[str, Any]
    RECORD_TYPE: ClassVar[str]

    @classmethod
    def create(cls, **fields: Any) -> "_Record":
        return cls.from_dict(_hashed({"record_type": cls.RECORD_TYPE, **copy.deepcopy(fields)}))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "_Record":
        if value.get("record_type") != cls.RECORD_TYPE:
            raise ValueError(f"record_type must be {cls.RECORD_TYPE}")
        _VALIDATORS[cls.RECORD_TYPE](value)
        _check_hash(value)
        return cls(_freeze(value))

    @property
    def record_sha256(self) -> str:
        return self.data["record_sha256"]

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.data)


class DashboardProjectionPolicyRevision(_Record): RECORD_TYPE = "DashboardProjectionPolicyRevision"
class DashboardSourceBinding(_Record): RECORD_TYPE = "DashboardSourceBinding"
class DashboardQueryIntent(_Record): RECORD_TYPE = "DashboardQueryIntent"
class DashboardJobReadModel(_Record): RECORD_TYPE = "DashboardJobReadModel"
class DashboardEvidenceReadModel(_Record): RECORD_TYPE = "DashboardEvidenceReadModel"
class DashboardIncidentReadModel(_Record): RECORD_TYPE = "DashboardIncidentReadModel"
class DashboardAlertClassificationReceipt(_Record): RECORD_TYPE = "DashboardAlertClassificationReceipt"
class IntegratedDashboardSnapshotRevision(_Record): RECORD_TYPE = "IntegratedDashboardSnapshotRevision"
class DashboardOperationProposalRevision(_Record): RECORD_TYPE = "DashboardOperationProposalRevision"
class HumanOperationConfirmationBinding(_Record): RECORD_TYPE = "HumanOperationConfirmationBinding"
class DashboardExecutionReceiptBinding(_Record): RECORD_TYPE = "DashboardExecutionReceiptBinding"


_CLASSES = {cls.RECORD_TYPE: cls for cls in (
    DashboardProjectionPolicyRevision, DashboardSourceBinding, DashboardQueryIntent,
    DashboardJobReadModel, DashboardEvidenceReadModel, DashboardIncidentReadModel,
    DashboardAlertClassificationReceipt, IntegratedDashboardSnapshotRevision,
    DashboardOperationProposalRevision, HumanOperationConfirmationBinding,
    DashboardExecutionReceiptBinding,
)}


def validate_record(value: Mapping[str, Any]) -> _Record:
    try:
        return _CLASSES[value.get("record_type")].from_dict(value)
    except (KeyError, TypeError) as exc:
        raise ValueError("unknown TASK-021 record_type") from exc


def classify_alert(
    *, alert_id: str, policy: DashboardProjectionPolicyRevision, subject: _Record,
    classified_at: str, incident: DashboardIncidentReadModel | None = None,
    acknowledgement_receipt_sha256: str | None = None,
) -> DashboardAlertClassificationReceipt:
    """Classify one already-observed subject; it sends or resolves nothing."""
    data = subject.to_dict()
    freshness = data.get("freshness_state", FreshnessState.UNKNOWN.value)
    reasons: list[str] = []
    incident_hash: str | None = None
    if freshness != FreshnessState.CURRENT.value:
        severity, lifecycle = AlertSeverity.UNKNOWN, AlertLifecycle.UNKNOWN
        reasons.append(f"SUBJECT_{freshness}")
    elif incident is not None:
        incident_data = incident.to_dict()
        incident_hash = incident.record_sha256
        incident_state = DashboardIncidentState(incident_data["incident_state"])
        if incident_state is DashboardIncidentState.ACTIVE:
            severity = AlertSeverity(incident_data["severity"])
            lifecycle = AlertLifecycle.OPEN
            reasons.append("ACTIVE_INCIDENT")
        elif incident_state is DashboardIncidentState.RESOLVED_PROVEN:
            severity, lifecycle = AlertSeverity.INFO, AlertLifecycle.RESOLVED_PROVEN
            reasons.append("INCIDENT_RESOLUTION_PROVEN")
        else:
            severity, lifecycle = AlertSeverity.UNKNOWN, AlertLifecycle.UNKNOWN
            reasons.append("INCIDENT_STATE_UNKNOWN")
    elif data.get("job_state") in {DurableJobViewState.FAILED.value, DurableJobViewState.HUMAN_REQUIRED.value}:
        severity, lifecycle = AlertSeverity.HIGH, AlertLifecycle.OPEN
        reasons.append("JOB_ATTENTION_REQUIRED")
    elif data.get("job_state") == DurableJobViewState.UNKNOWN.value or data.get("result_state") in {
        EvidenceResultState.UNKNOWN.value, EvidenceResultState.NOT_SUPPORTED.value,
    }:
        severity, lifecycle = AlertSeverity.UNKNOWN, AlertLifecycle.UNKNOWN
        reasons.append("SOURCE_RESULT_UNKNOWN")
    elif data.get("result_state") == EvidenceResultState.FAIL.value:
        severity, lifecycle = AlertSeverity.HIGH, AlertLifecycle.OPEN
        reasons.append("EVIDENCE_FAILURE")
    else:
        severity, lifecycle = AlertSeverity.INFO, AlertLifecycle.SUPPRESSED_BY_POLICY
        reasons.append("NO_ALERT_CONDITION_CLASSIFIED")
    if acknowledgement_receipt_sha256 is not None:
        _digest(acknowledgement_receipt_sha256, "acknowledgement_receipt_sha256")
        if lifecycle is not AlertLifecycle.OPEN:
            raise ValueError("only an OPEN alert can be acknowledged")
        lifecycle = AlertLifecycle.ACKNOWLEDGED
        reasons.append("ACKNOWLEDGED_NOT_RESOLVED")
    return DashboardAlertClassificationReceipt.create(
        alert_id=alert_id, policy_sha256=policy.record_sha256,
        subject_sha256=subject.record_sha256, incident_sha256=incident_hash,
        severity=severity.value, lifecycle=lifecycle.value,
        acknowledgement_receipt_sha256=acknowledgement_receipt_sha256,
        reason_codes=list(dict.fromkeys(reasons)), classified_at=classified_at,
        effect_started_by_dashboard=False,
    )


def build_snapshot(
    *, snapshot_id: str, revision: int, parent_record_sha256: str | None,
    project_id: str, policy: DashboardProjectionPolicyRevision, query: DashboardQueryIntent,
    sources: Sequence[DashboardSourceBinding], jobs: Sequence[DashboardJobReadModel],
    evidence: Sequence[DashboardEvidenceReadModel], incidents: Sequence[DashboardIncidentReadModel],
    alerts: Sequence[DashboardAlertClassificationReceipt], coverage_state: str,
    source_watermark_sha256: str, generated_at: str,
) -> IntegratedDashboardSnapshotRevision:
    policy_data = policy.to_dict()
    query_data = query.to_dict()
    generated = _time(generated_at, "generated_at")
    if query_data["project_id"] != project_id:
        raise ValueError("query project does not match snapshot project")
    if query_data["page_size"] > policy_data["max_page_size"]:
        raise ValueError("query page size exceeds current policy")
    if _dt(generated) < _dt(policy_data["effective_at"]) or (
        policy_data["expires_at"] is not None
        and _dt(generated) >= _dt(policy_data["expires_at"])
    ):
        raise ValueError("snapshot policy is not current at generation time")
    if len(sources) > policy_data["max_sources"] or len(jobs) + len(evidence) > policy_data["max_items"]:
        raise ValueError("snapshot exceeds policy item caps")
    if len(alerts) > policy_data["max_alerts"] or len(incidents) > policy_data["max_incidents"]:
        raise ValueError("snapshot exceeds policy alert/incident caps")
    if len({item.record_sha256 for item in sources}) != len(sources):
        raise ValueError("source bindings must be unique")
    source_data = [item.to_dict() for item in sources]
    selected_kinds = set(query_data["source_kinds"])
    if any(item["source_kind"] not in selected_kinds for item in source_data):
        raise ValueError("source kind is outside the exact query")
    source_hashes = {item.record_sha256 for item in sources}
    read_models = [*jobs, *evidence, *incidents]
    if any(item.to_dict()["source_binding_sha256"] not in source_hashes for item in read_models):
        raise ValueError("read model is not bound to an exact selected source")
    subject_hashes = {item.record_sha256 for item in read_models}
    incident_hashes = {item.record_sha256 for item in incidents}
    for alert in alerts:
        alert_data = alert.to_dict()
        if alert_data["subject_sha256"] not in subject_hashes:
            raise ValueError("alert subject is outside the exact snapshot")
        if alert_data["incident_sha256"] is not None and alert_data["incident_sha256"] not in incident_hashes:
            raise ValueError("alert incident is outside the exact snapshot")
    if any(_dt(item["observed_at"]) > _dt(generated) for item in source_data):
        raise ValueError("source observation cannot be in the snapshot future")
    if any(item["contract_state"] != ContractState.BOUND_VERIFIED.value for item in source_data):
        state = DashboardSnapshotState.UNKNOWN
    elif any(item["validity_state"] == FreshnessState.INVALIDATED.value for item in source_data):
        state = DashboardSnapshotState.STALE
    elif any(item["freshness_state"] == FreshnessState.INVALIDATED.value for item in source_data):
        state = DashboardSnapshotState.STALE
    elif any(
        item["freshness_state"] == FreshnessState.STALE.value
        or item["validity_state"] == FreshnessState.STALE.value
        or (_dt(generated) - _dt(item["observed_at"])).total_seconds() > policy_data["max_source_age_seconds"]
        for item in source_data
    ):
        state = DashboardSnapshotState.STALE
    elif any(
        item["freshness_state"] == FreshnessState.UNKNOWN.value
        or item["validity_state"] == FreshnessState.UNKNOWN.value
        for item in source_data
    ):
        state = DashboardSnapshotState.UNKNOWN
    elif any(item.to_dict()["incident_state"] == DashboardIncidentState.ACTIVE.value for item in incidents):
        state = DashboardSnapshotState.ACTION_REQUIRED
    elif any(item.to_dict()["lifecycle"] in {AlertLifecycle.OPEN.value, AlertLifecycle.ACKNOWLEDGED.value} for item in alerts):
        state = DashboardSnapshotState.ACTION_REQUIRED
    elif any(item.to_dict()["job_state"] in {
        DurableJobViewState.FAILED.value, DurableJobViewState.HUMAN_REQUIRED.value,
    } for item in jobs):
        state = DashboardSnapshotState.ACTION_REQUIRED
    elif any(item.to_dict()["job_state"] == DurableJobViewState.UNKNOWN.value for item in jobs) or any(
        item.to_dict()["result_state"] in {EvidenceResultState.UNKNOWN.value, EvidenceResultState.NOT_SUPPORTED.value}
        for item in evidence
    ):
        state = DashboardSnapshotState.UNKNOWN
    elif any(item.to_dict()["job_state"] in {
        DurableJobViewState.QUEUED.value, DurableJobViewState.PREFLIGHT.value,
        DurableJobViewState.READY.value, DurableJobViewState.DISPATCHING.value,
        DurableJobViewState.RUNNING.value,
    } for item in jobs):
        state = DashboardSnapshotState.DEGRADED
    elif CoverageState(coverage_state) is CoverageState.COMPLETE:
        state = DashboardSnapshotState.NO_ACTIVE_INCIDENT_PROVEN
    else:
        state = DashboardSnapshotState.UNKNOWN
    return IntegratedDashboardSnapshotRevision.create(
        snapshot_id=snapshot_id, revision=revision, parent_record_sha256=parent_record_sha256,
        project_id=project_id, policy_sha256=policy.record_sha256, query_sha256=query.record_sha256,
        source_binding_hashes=sorted(item.record_sha256 for item in sources),
        job_view_hashes=sorted(item.record_sha256 for item in jobs),
        evidence_view_hashes=sorted(item.record_sha256 for item in evidence),
        incident_view_hashes=sorted(item.record_sha256 for item in incidents),
        alert_hashes=sorted(item.record_sha256 for item in alerts), coverage_state=coverage_state,
        snapshot_state=state.value, source_watermark_sha256=source_watermark_sha256,
        generated_at=generated_at, body_included=False, private_detail_included=False,
        effect_started_by_dashboard=False,
    )


def operation_admission_report(
    *, proposal: DashboardOperationProposalRevision,
    confirmation: HumanOperationConfirmationBinding | None,
    execution_receipt: DashboardExecutionReceiptBinding | None,
    evaluated_at: str,
) -> dict[str, Any]:
    """Return no-effect admissibility metadata, never an operation command."""
    now = _time(evaluated_at, "evaluated_at")
    p = proposal.to_dict()
    reasons: list[str] = []
    admissible = True
    if p["proposal_state"] != OperationProposalState.PROPOSED.value or _dt(p["expires_at"]) <= _dt(now):
        admissible = False
        reasons.append("PROPOSAL_NOT_CURRENT")
    confirmation_sha: str | None = None
    if confirmation is None:
        admissible = False
        reasons.append("HUMAN_CONFIRMATION_NOT_BOUND")
    else:
        c = confirmation.to_dict()
        confirmation_sha = confirmation.record_sha256
        exact = (
            c["contract_state"] == ContractState.BOUND_VERIFIED.value
            and c["proposal_sha256"] == proposal.record_sha256
            and c["snapshot_sha256"] == p["snapshot_sha256"]
            and c["target_source_sha256"] == p["target_source_sha256"]
            and c["operation_kind"] == p["operation_kind"]
            and c["reviewer_kind"] == "HUMAN"
            and c["decision"] == HumanOperationDecision.APPROVE.value
            and c["one_shot"] is True and c["consumed"] is False
            and _dt(c["expires_at"]) > _dt(now)
        )
        if not exact:
            admissible = False
            reasons.append("HUMAN_CONFIRMATION_MISMATCH_OR_EXPIRED")
    result = "NOT_DISPATCHED"
    if execution_receipt is not None:
        receipt = execution_receipt.to_dict()
        exact_receipt = (
            receipt["contract_state"] == ContractState.BOUND_VERIFIED.value
            and receipt["proposal_sha256"] == proposal.record_sha256
            and receipt["confirmation_sha256"] == confirmation_sha
        )
        if not exact_receipt:
            admissible = False
            result = "UNKNOWN"
            reasons.append("EXECUTION_RECEIPT_MISMATCH")
        else:
            result = receipt["external_state"]
            if result == ExternalExecutionState.UNKNOWN.value:
                reasons.append("EXTERNAL_RESULT_UNKNOWN_NO_REPLAY")
    return {
        "proposal_sha256": proposal.record_sha256,
        "human_confirmation_sha256": confirmation_sha,
        "gate_decision": (
            "READY_FOR_EXTERNAL_HUMAN_GATE"
            if admissible and execution_receipt is None
            else "RESULT_RECORDED" if execution_receipt is not None else "BLOCKED"
        ),
        "external_result_state": result,
        "reason_codes": list(dict.fromkeys(reasons)),
        "dispatch_started": False,
        "process_started": False,
        "app_operation_started": False,
        "alert_sent": False,
        "production_effect_started": False,
    }


def private_projection(record: _Record) -> dict[str, Any]:
    return record.to_dict()


def public_projection(record: _Record) -> dict[str, Any]:
    data = record.to_dict()
    result: dict[str, Any] = {
        "record_type": data["record_type"], "record_sha256": data["record_sha256"],
        "body_included": False, "private_detail_included": False,
        "low_count_details_included": False,
    }
    for field in (
        "contract_state", "freshness_state", "validity_state", "job_state", "result_state",
        "incident_state", "severity", "lifecycle", "coverage_state", "snapshot_state",
        "proposal_state", "decision", "external_state", "proposal_only",
        "effect_started_by_dashboard", "execution_started",
    ):
        if field in data:
            result[field] = data[field]
    if "reason_codes" in data:
        result["reason_codes"] = list(data["reason_codes"])
    return result


EFFECT_SURFACE = MappingProxyType({
    "source_store_read": False,
    "source_store_mutation": False,
    "job_queue_process_app_control": False,
    "network_provider_operation": False,
    "alert_notification_send": False,
    "private_body_path_credential_read": False,
    "release_deploy_production": False,
})


__all__ = [
    "AlertLifecycle", "AlertSeverity", "ContractState", "CoverageState",
    "DashboardAlertClassificationReceipt", "DashboardEvidenceReadModel",
    "DashboardExecutionReceiptBinding", "DashboardIncidentReadModel",
    "DashboardIncidentState", "DashboardJobReadModel", "DashboardOperationKind",
    "DashboardOperationProposalRevision", "DashboardProjectionPolicyRevision",
    "DashboardQueryIntent", "DashboardSnapshotState", "DashboardSourceBinding",
    "DashboardSourceKind", "DurableJobViewState", "EFFECT_SURFACE",
    "EvidenceResultState", "ExternalExecutionState", "FreshnessState",
    "HumanOperationConfirmationBinding", "HumanOperationDecision",
    "IntegratedDashboardSnapshotRevision", "OperationProposalState", "QuerySortOrder",
    "build_snapshot", "classify_alert", "operation_admission_report",
    "private_projection", "public_projection", "validate_record",
]
