"""TASK-020 provider-neutral resource admission and monitoring metadata.

The module is deliberately pure.  It validates body-free facts, evaluates an
immutable policy and classifies externally supplied runtime evidence.  It does
not inspect the host, reserve resources, launch or terminate processes, contact
the network, or dispatch an application operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Sequence
import copy
import re

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_ID = "bai.task020.resource-admission-monitoring.v1"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_REASON_RE = re.compile(r"[A-Z][A-Z0-9_]{1,95}")
_PRIVATE_TERMS = ("credential", "password", "secret", "token", "private-key")


class MetricValueState(str, Enum):
    DECLARED = "DECLARED"
    MEASURED = "MEASURED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    INSUFFICIENT_INPUT = "INSUFFICIENT_INPUT"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class ResourceMetricKind(str, Enum):
    CPU_AVAILABLE_MILLICORES = "CPU_AVAILABLE_MILLICORES"
    RAM_AVAILABLE_BYTES = "RAM_AVAILABLE_BYTES"
    VRAM_AVAILABLE_BYTES = "VRAM_AVAILABLE_BYTES"
    DISK_AVAILABLE_BYTES = "DISK_AVAILABLE_BYTES"
    NETWORK_REACHABLE = "NETWORK_REACHABLE"
    PROCESS_INSTANCE_COUNT = "PROCESS_INSTANCE_COUNT"
    APP_INSTANCE_COUNT = "APP_INSTANCE_COUNT"


class ThresholdComparison(str, Enum):
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"
    EQUAL = "EQUAL"


class AdmissionDecision(str, Enum):
    ADMITTED = "ADMITTED"
    DENIED = "DENIED"
    UNKNOWN = "UNKNOWN"


class RuntimeWatermarkState(str, Enum):
    WITHIN_ADMITTED_BOUNDS = "WITHIN_ADMITTED_BOUNDS"
    BREACH = "BREACH"
    UNKNOWN = "UNKNOWN"


class ResourceIncidentState(str, Enum):
    CONFIRMED = "CONFIRMED"
    UNKNOWN = "UNKNOWN"


class ResourceIncidentKind(str, Enum):
    THRESHOLD_BREACH = "THRESHOLD_BREACH"
    STALE_EVIDENCE = "STALE_EVIDENCE"
    PROCESS_CARDINALITY = "PROCESS_CARDINALITY"
    APP_CARDINALITY = "APP_CARDINALITY"
    OBSERVATION_ERROR = "OBSERVATION_ERROR"


class ContractState(str, Enum):
    CANONICAL_REF_NOT_PROVIDED = "CANONICAL_REF_NOT_PROVIDED"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class OperationScope(str, Enum):
    LOCAL_ANALYSIS = "LOCAL_ANALYSIS"
    LOCAL_GENERATION = "LOCAL_GENERATION"
    VOICE_CAPTURE = "VOICE_CAPTURE"
    VOICE_TRAINING = "VOICE_TRAINING"
    EXPORT = "EXPORT"
    APPLICATION_PROBE = "APPLICATION_PROBE"


class OperationGateDecision(str, Enum):
    READY_FOR_EXTERNAL_HUMAN_GATE = "READY_FOR_EXTERNAL_HUMAN_GATE"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


_UNIT_BY_KIND = {
    ResourceMetricKind.CPU_AVAILABLE_MILLICORES: "millicores",
    ResourceMetricKind.RAM_AVAILABLE_BYTES: "bytes",
    ResourceMetricKind.VRAM_AVAILABLE_BYTES: "bytes",
    ResourceMetricKind.DISK_AVAILABLE_BYTES: "bytes",
    ResourceMetricKind.NETWORK_REACHABLE: "boolean-int",
    ResourceMetricKind.PROCESS_INSTANCE_COUNT: "count",
    ResourceMetricKind.APP_INSTANCE_COUNT: "count",
}


def _id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    folded = value.casefold()
    if (
        "\\" in value
        or value.startswith("/")
        or any(part == ".." for part in value.split("/"))
        or any(term in folded for term in _PRIVATE_TERMS)
    ):
        raise ValueError(f"{name} violates the body-free identity boundary")
    return value


def _timestamp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{name} must be an RFC3339 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be an RFC3339 UTC timestamp") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{name} must be UTC")
    return value


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a SHA-256 digest")
    return validate_sha256(value, field_name=name)


def _positive_int(value: Any, name: str, *, allow_zero: bool = False) -> int:
    floor = 0 if allow_zero else 1
    if isinstance(value, bool) or not isinstance(value, int) or value < floor:
        raise ValueError(f"{name} must be an integer >= {floor}")
    return value


def _enum(enum_type: type[Enum], value: Any, name: str) -> Enum:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


def _expect_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _reasons(values: Any, name: str) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{name} must be an ordered array")
    result = tuple(values)
    if len(result) > 64 or len(set(result)) != len(result):
        raise ValueError(f"{name} must be unique and bounded")
    if any(not isinstance(item, str) or not _REASON_RE.fullmatch(item) for item in result):
        raise ValueError(f"{name} contains an invalid reason code")
    return result


def _record_hash(body: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(body))


def _with_hash(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = copy.deepcopy(dict(body))
    result[field] = _record_hash(body)
    return result


def _validate_hash(value: Mapping[str, Any], field: str) -> None:
    supplied = _digest(value[field], field)
    body = {key: copy.deepcopy(item) for key, item in value.items() if key != field}
    if supplied != _record_hash(body):
        raise ValueError(f"{field} does not match the canonical record body")


@dataclass(frozen=True, slots=True)
class ResourceMetricFact:
    metric_kind: ResourceMetricKind
    value_state: MetricValueState
    value_int: int | None
    unit: str
    observed_at: str
    source_profile_ref: str
    source_profile_sha256: str
    metric_fact_sha256: str

    @classmethod
    def create(
        cls,
        *,
        metric_kind: ResourceMetricKind,
        value_state: MetricValueState,
        value_int: int | None,
        observed_at: str,
        source_profile_ref: str,
        source_profile_sha256: str,
    ) -> "ResourceMetricFact":
        body = {
            "metric_kind": metric_kind.value,
            "value_state": value_state.value,
            "value_int": value_int,
            "unit": _UNIT_BY_KIND[metric_kind],
            "observed_at": observed_at,
            "source_profile_ref": source_profile_ref,
            "source_profile_sha256": source_profile_sha256,
        }
        return cls.from_dict(_with_hash(body, "metric_fact_sha256"))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ResourceMetricFact":
        expected = {
            "metric_kind", "value_state", "value_int", "unit", "observed_at",
            "source_profile_ref", "source_profile_sha256", "metric_fact_sha256",
        }
        _expect_keys(value, expected, "ResourceMetricFact")
        kind = _enum(ResourceMetricKind, value["metric_kind"], "metric_kind")
        state = _enum(MetricValueState, value["value_state"], "value_state")
        if value["unit"] != _UNIT_BY_KIND[kind]:
            raise ValueError("metric unit does not match metric_kind")
        measured = state is MetricValueState.MEASURED
        if measured:
            _positive_int(value["value_int"], "value_int", allow_zero=True)
            if kind is ResourceMetricKind.NETWORK_REACHABLE and value["value_int"] not in {0, 1}:
                raise ValueError("NETWORK_REACHABLE value must be 0 or 1")
        elif value["value_int"] is not None:
            raise ValueError("only MEASURED facts may carry a value")
        _timestamp(value["observed_at"], "observed_at")
        _id(value["source_profile_ref"], "source_profile_ref")
        _digest(value["source_profile_sha256"], "source_profile_sha256")
        _validate_hash(value, "metric_fact_sha256")
        return cls(
            metric_kind=kind,
            value_state=state,
            value_int=value["value_int"],
            unit=value["unit"],
            observed_at=value["observed_at"],
            source_profile_ref=value["source_profile_ref"],
            source_profile_sha256=value["source_profile_sha256"],
            metric_fact_sha256=value["metric_fact_sha256"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_kind": self.metric_kind.value,
            "value_state": self.value_state.value,
            "value_int": self.value_int,
            "unit": self.unit,
            "observed_at": self.observed_at,
            "source_profile_ref": self.source_profile_ref,
            "source_profile_sha256": self.source_profile_sha256,
            "metric_fact_sha256": self.metric_fact_sha256,
        }


@dataclass(frozen=True, slots=True)
class ResourceThreshold:
    metric_kind: ResourceMetricKind
    comparison: ThresholdComparison
    threshold_value_int: int
    unit: str
    required: bool

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ResourceThreshold":
        expected = {"metric_kind", "comparison", "threshold_value_int", "unit", "required"}
        _expect_keys(value, expected, "ResourceThreshold")
        kind = _enum(ResourceMetricKind, value["metric_kind"], "threshold metric_kind")
        comparison = _enum(ThresholdComparison, value["comparison"], "comparison")
        _positive_int(value["threshold_value_int"], "threshold_value_int", allow_zero=True)
        if value["unit"] != _UNIT_BY_KIND[kind]:
            raise ValueError("threshold unit does not match metric_kind")
        if not isinstance(value["required"], bool):
            raise ValueError("required must be boolean")
        return cls(kind, comparison, value["threshold_value_int"], value["unit"], value["required"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_kind": self.metric_kind.value,
            "comparison": self.comparison.value,
            "threshold_value_int": self.threshold_value_int,
            "unit": self.unit,
            "required": self.required,
        }


def _thresholds(values: Any) -> tuple[ResourceThreshold, ...]:
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("thresholds must be a non-empty ordered array")
    result = tuple(ResourceThreshold.from_dict(item) for item in values)
    keys = tuple(item.metric_kind.value for item in result)
    if keys != tuple(sorted(keys)) or len(set(keys)) != len(keys):
        raise ValueError("thresholds must be unique and sorted by metric_kind")
    return result


def _facts(values: Any) -> tuple[ResourceMetricFact, ...]:
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("facts must be a non-empty ordered array")
    result = tuple(ResourceMetricFact.from_dict(item) for item in values)
    keys = tuple(item.metric_kind.value for item in result)
    if keys != tuple(sorted(keys)) or len(set(keys)) != len(keys):
        raise ValueError("facts must be unique and sorted by metric_kind")
    return result


@dataclass(frozen=True, slots=True)
class ResourceAdmissionPolicyRevision:
    value: Mapping[str, Any]

    HASH_FIELD = "policy_revision_sha256"
    RECORD_TYPE = "ResourceAdmissionPolicyRevision"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ResourceAdmissionPolicyRevision":
        expected = {
            "schema", "record_type", "task_owner", "project_id", "policy_id", "revision",
            "parent_revision_sha256", "created_at", "max_fact_age_seconds", "thresholds",
            "collector_body_persisted", "effect_authorized", cls.HASH_FIELD,
        }
        _expect_keys(value, expected, cls.RECORD_TYPE)
        if value["schema"] != SCHEMA_ID or value["record_type"] != cls.RECORD_TYPE or value["task_owner"] != "TASK-020":
            raise ValueError("policy identity is invalid")
        _id(value["project_id"], "project_id")
        _id(value["policy_id"], "policy_id")
        revision = _positive_int(value["revision"], "revision")
        if revision == 1:
            if value["parent_revision_sha256"] is not None:
                raise ValueError("first policy revision cannot have a parent")
        else:
            _digest(value["parent_revision_sha256"], "parent_revision_sha256")
        _timestamp(value["created_at"], "created_at")
        _positive_int(value["max_fact_age_seconds"], "max_fact_age_seconds")
        _thresholds(value["thresholds"])
        if value["collector_body_persisted"] is not False or value["effect_authorized"] is not False:
            raise ValueError("policy must remain body-free and non-authorizing")
        _validate_hash(value, cls.HASH_FIELD)
        return cls(copy.deepcopy(dict(value)))

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(dict(self.value))


@dataclass(frozen=True, slots=True)
class ResourcePreflightObservationReceipt:
    value: Mapping[str, Any]

    HASH_FIELD = "observation_receipt_sha256"
    RECORD_TYPE = "ResourcePreflightObservationReceipt"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ResourcePreflightObservationReceipt":
        expected = {
            "schema", "record_type", "task_owner", "project_id", "observation_receipt_id",
            "operation_identity", "operation_input_sha256", "target_kind", "target_ref",
            "target_revision_sha256", "policy_id", "policy_revision_sha256", "observed_at",
            "facts", "collector_executed_by_module", "operation_started", cls.HASH_FIELD,
        }
        _expect_keys(value, expected, cls.RECORD_TYPE)
        if value["schema"] != SCHEMA_ID or value["record_type"] != cls.RECORD_TYPE or value["task_owner"] != "TASK-020":
            raise ValueError("observation identity is invalid")
        for field in ("project_id", "observation_receipt_id", "operation_identity", "target_kind", "target_ref", "policy_id"):
            _id(value[field], field)
        for field in ("operation_input_sha256", "target_revision_sha256", "policy_revision_sha256"):
            _digest(value[field], field)
        _timestamp(value["observed_at"], "observed_at")
        facts = _facts(value["facts"])
        if any(fact.observed_at != value["observed_at"] for fact in facts):
            raise ValueError("all preflight facts must share observed_at")
        if value["collector_executed_by_module"] is not False or value["operation_started"] is not False:
            raise ValueError("observation receipt cannot claim an effect")
        _validate_hash(value, cls.HASH_FIELD)
        return cls(copy.deepcopy(dict(value)))

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(dict(self.value))


@dataclass(frozen=True, slots=True)
class ResourceAdmissionDecisionReceipt:
    value: Mapping[str, Any]

    HASH_FIELD = "admission_decision_sha256"
    RECORD_TYPE = "ResourceAdmissionDecisionReceipt"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ResourceAdmissionDecisionReceipt":
        expected = {
            "schema", "record_type", "task_owner", "project_id", "decision_id",
            "operation_identity", "policy_revision_sha256", "observation_receipt_sha256",
            "evaluated_at", "decision", "reason_codes", "reservation_started",
            "dispatch_started", "execution_authorized", cls.HASH_FIELD,
        }
        _expect_keys(value, expected, cls.RECORD_TYPE)
        if value["schema"] != SCHEMA_ID or value["record_type"] != cls.RECORD_TYPE or value["task_owner"] != "TASK-020":
            raise ValueError("decision identity is invalid")
        for field in ("project_id", "decision_id", "operation_identity"):
            _id(value[field], field)
        _digest(value["policy_revision_sha256"], "policy_revision_sha256")
        _digest(value["observation_receipt_sha256"], "observation_receipt_sha256")
        _timestamp(value["evaluated_at"], "evaluated_at")
        decision = _enum(AdmissionDecision, value["decision"], "decision")
        reasons = _reasons(value["reason_codes"], "reason_codes")
        if decision is AdmissionDecision.ADMITTED and reasons:
            raise ValueError("ADMITTED cannot carry reason_codes")
        if decision is not AdmissionDecision.ADMITTED and not reasons:
            raise ValueError("non-ADMITTED decision requires reason_codes")
        for field in ("reservation_started", "dispatch_started", "execution_authorized"):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        _validate_hash(value, cls.HASH_FIELD)
        return cls(copy.deepcopy(dict(value)))

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(dict(self.value))


@dataclass(frozen=True, slots=True)
class RuntimeResourceWatermarkReceipt:
    value: Mapping[str, Any]

    HASH_FIELD = "watermark_receipt_sha256"
    RECORD_TYPE = "RuntimeResourceWatermarkReceipt"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RuntimeResourceWatermarkReceipt":
        expected = {
            "schema", "record_type", "task_owner", "project_id", "watermark_receipt_id",
            "operation_identity", "policy_revision_sha256", "admission_decision_sha256",
            "sequence", "window_started_at", "window_ended_at", "facts", "state",
            "reason_codes", "collector_executed_by_module", "process_control_started",
            "app_operation_started", cls.HASH_FIELD,
        }
        _expect_keys(value, expected, cls.RECORD_TYPE)
        if value["schema"] != SCHEMA_ID or value["record_type"] != cls.RECORD_TYPE or value["task_owner"] != "TASK-020":
            raise ValueError("watermark identity is invalid")
        for field in ("project_id", "watermark_receipt_id", "operation_identity"):
            _id(value[field], field)
        for field in ("policy_revision_sha256", "admission_decision_sha256"):
            _digest(value[field], field)
        _positive_int(value["sequence"], "sequence")
        start = datetime.fromisoformat(_timestamp(value["window_started_at"], "window_started_at")[:-1] + "+00:00")
        end = datetime.fromisoformat(_timestamp(value["window_ended_at"], "window_ended_at")[:-1] + "+00:00")
        if end < start:
            raise ValueError("watermark window end precedes start")
        _facts(value["facts"])
        state = _enum(RuntimeWatermarkState, value["state"], "state")
        reasons = _reasons(value["reason_codes"], "reason_codes")
        if state is RuntimeWatermarkState.WITHIN_ADMITTED_BOUNDS and reasons:
            raise ValueError("healthy watermark cannot carry reason_codes")
        if state is not RuntimeWatermarkState.WITHIN_ADMITTED_BOUNDS and not reasons:
            raise ValueError("non-healthy watermark requires reason_codes")
        for field in ("collector_executed_by_module", "process_control_started", "app_operation_started"):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        _validate_hash(value, cls.HASH_FIELD)
        return cls(copy.deepcopy(dict(value)))

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(dict(self.value))


@dataclass(frozen=True, slots=True)
class ResourceIncidentReceipt:
    value: Mapping[str, Any]

    HASH_FIELD = "incident_receipt_sha256"
    RECORD_TYPE = "ResourceIncidentReceipt"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ResourceIncidentReceipt":
        expected = {
            "schema", "record_type", "task_owner", "project_id", "incident_receipt_id",
            "operation_identity", "watermark_receipt_sha256", "detected_at", "state",
            "incident_kind", "affected_metrics", "reason_codes", "termination_requested",
            "process_kill_started", "app_stop_started", cls.HASH_FIELD,
        }
        _expect_keys(value, expected, cls.RECORD_TYPE)
        if value["schema"] != SCHEMA_ID or value["record_type"] != cls.RECORD_TYPE or value["task_owner"] != "TASK-020":
            raise ValueError("incident identity is invalid")
        for field in ("project_id", "incident_receipt_id", "operation_identity"):
            _id(value[field], field)
        _digest(value["watermark_receipt_sha256"], "watermark_receipt_sha256")
        _timestamp(value["detected_at"], "detected_at")
        _enum(ResourceIncidentState, value["state"], "incident state")
        _enum(ResourceIncidentKind, value["incident_kind"], "incident_kind")
        if not isinstance(value["affected_metrics"], list) or not value["affected_metrics"]:
            raise ValueError("affected_metrics must be non-empty")
        metrics = tuple(_enum(ResourceMetricKind, item, "affected metric") for item in value["affected_metrics"])
        keys = tuple(item.value for item in metrics)
        if keys != tuple(sorted(keys)) or len(set(keys)) != len(keys):
            raise ValueError("affected_metrics must be unique and sorted")
        if not _reasons(value["reason_codes"], "reason_codes"):
            raise ValueError("incident requires reason_codes")
        for field in ("termination_requested", "process_kill_started", "app_stop_started"):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        _validate_hash(value, cls.HASH_FIELD)
        return cls(copy.deepcopy(dict(value)))

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(dict(self.value))


@dataclass(frozen=True, slots=True)
class ResourceOperationGateBinding:
    value: Mapping[str, Any]

    HASH_FIELD = "operation_gate_binding_sha256"
    RECORD_TYPE = "ResourceOperationGateBinding"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ResourceOperationGateBinding":
        expected = {
            "schema", "record_type", "task_owner", "project_id", "binding_id",
            "operation_identity", "operation_scope", "contract_state", "decision_ref",
            "admission_decision_sha256", "admission_decision", "gate_decision", "reason_codes",
            "execution_authorized", "reservation_started", "dispatch_started", "process_started",
            "app_launched", cls.HASH_FIELD,
        }
        _expect_keys(value, expected, cls.RECORD_TYPE)
        if value["schema"] != SCHEMA_ID or value["record_type"] != cls.RECORD_TYPE or value["task_owner"] != "TASK-020":
            raise ValueError("operation gate identity is invalid")
        for field in ("project_id", "binding_id", "operation_identity"):
            _id(value[field], field)
        _enum(OperationScope, value["operation_scope"], "operation_scope")
        contract = _enum(ContractState, value["contract_state"], "contract_state")
        admission = value["admission_decision"]
        if admission is not None:
            _enum(AdmissionDecision, admission, "admission_decision")
        gate = _enum(OperationGateDecision, value["gate_decision"], "gate_decision")
        reasons = _reasons(value["reason_codes"], "reason_codes")
        if contract is ContractState.CANONICAL_REF_NOT_PROVIDED:
            if value["decision_ref"] is not None or value["admission_decision_sha256"] is not None or admission is not None:
                raise ValueError("unresolved gate must not invent canonical decision fields")
            if gate is not OperationGateDecision.UNKNOWN or reasons != ("CANONICAL_REF_NOT_PROVIDED",):
                raise ValueError("unresolved gate must remain UNKNOWN")
        else:
            if value["decision_ref"] is not None:
                _id(value["decision_ref"], "decision_ref")
            if value["admission_decision_sha256"] is not None:
                _digest(value["admission_decision_sha256"], "admission_decision_sha256")
            if contract is ContractState.BOUND_VERIFIED and (
                value["decision_ref"] is None or value["admission_decision_sha256"] is None or admission is None
            ):
                raise ValueError("BOUND_VERIFIED gate is incomplete")
        if gate is OperationGateDecision.READY_FOR_EXTERNAL_HUMAN_GATE:
            if contract is not ContractState.BOUND_VERIFIED or admission != AdmissionDecision.ADMITTED.value or reasons:
                raise ValueError("ready gate requires exact admitted binding")
        elif not reasons:
            raise ValueError("non-ready gate requires reason_codes")
        for field in ("execution_authorized", "reservation_started", "dispatch_started", "process_started", "app_launched"):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        _validate_hash(value, cls.HASH_FIELD)
        return cls(copy.deepcopy(dict(value)))

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(dict(self.value))


_RECORDS = {
    ResourceAdmissionPolicyRevision.RECORD_TYPE: ResourceAdmissionPolicyRevision,
    ResourcePreflightObservationReceipt.RECORD_TYPE: ResourcePreflightObservationReceipt,
    ResourceAdmissionDecisionReceipt.RECORD_TYPE: ResourceAdmissionDecisionReceipt,
    RuntimeResourceWatermarkReceipt.RECORD_TYPE: RuntimeResourceWatermarkReceipt,
    ResourceIncidentReceipt.RECORD_TYPE: ResourceIncidentReceipt,
    ResourceOperationGateBinding.RECORD_TYPE: ResourceOperationGateBinding,
}


def parse_resource_record(value: Mapping[str, Any]) -> Any:
    if not isinstance(value, Mapping):
        raise ValueError("resource record must be an object")
    record_type = value.get("record_type")
    parser = _RECORDS.get(record_type)
    if parser is None:
        raise ValueError("record_type is not a canonical TASK-020 type")
    return parser.from_dict(value)


def canonical_record_digest(value: Mapping[str, Any]) -> str:
    record = parse_resource_record(value)
    return getattr(record, "value")[record.HASH_FIELD]


def validate_policy_successor(
    parent_value: Mapping[str, Any], candidate_value: Mapping[str, Any]
) -> ResourceAdmissionPolicyRevision:
    parent = ResourceAdmissionPolicyRevision.from_dict(parent_value).to_dict()
    candidate = ResourceAdmissionPolicyRevision.from_dict(candidate_value).to_dict()
    if candidate["project_id"] != parent["project_id"] or candidate["policy_id"] != parent["policy_id"]:
        raise ValueError("policy successor identity mismatch")
    if candidate["revision"] != parent["revision"] + 1:
        raise ValueError("policy successor revision must increment by one")
    if candidate["parent_revision_sha256"] != parent["policy_revision_sha256"]:
        raise ValueError("policy successor parent hash mismatch")
    parent_at = datetime.fromisoformat(parent["created_at"][:-1] + "+00:00")
    candidate_at = datetime.fromisoformat(candidate["created_at"][:-1] + "+00:00")
    if candidate_at <= parent_at:
        raise ValueError("policy successor timestamp must advance")
    return ResourceAdmissionPolicyRevision.from_dict(candidate)


def _fact_map(facts: Sequence[ResourceMetricFact]) -> dict[ResourceMetricKind, ResourceMetricFact]:
    return {fact.metric_kind: fact for fact in facts}


def _threshold_passes(threshold: ResourceThreshold, value: int) -> bool:
    if threshold.comparison is ThresholdComparison.GREATER_THAN_OR_EQUAL:
        return value >= threshold.threshold_value_int
    if threshold.comparison is ThresholdComparison.LESS_THAN_OR_EQUAL:
        return value <= threshold.threshold_value_int
    return value == threshold.threshold_value_int


def _classify_facts(
    policy: Mapping[str, Any],
    facts: Sequence[ResourceMetricFact],
    *,
    evaluated_at: str,
) -> tuple[AdmissionDecision, list[str]]:
    evaluated = datetime.fromisoformat(_timestamp(evaluated_at, "evaluated_at")[:-1] + "+00:00")
    reasons: list[str] = []
    decision = AdmissionDecision.ADMITTED
    mapped = _fact_map(facts)
    source_hashes = {fact.source_profile_sha256 for fact in facts}
    if len(source_hashes) != 1:
        decision = AdmissionDecision.UNKNOWN
        reasons.append("MIXED_SOURCE_PROFILE")
    for threshold in _thresholds(policy["thresholds"]):
        fact = mapped.get(threshold.metric_kind)
        prefix = threshold.metric_kind.value
        if fact is None:
            if threshold.required:
                decision = AdmissionDecision.UNKNOWN
                reasons.append(f"{prefix}_MISSING")
            continue
        observed = datetime.fromisoformat(fact.observed_at[:-1] + "+00:00")
        age_seconds = (evaluated - observed).total_seconds()
        if age_seconds < 0 or age_seconds > policy["max_fact_age_seconds"]:
            decision = AdmissionDecision.UNKNOWN
            reasons.append(f"{prefix}_STALE_OR_FUTURE")
            continue
        if fact.value_state is not MetricValueState.MEASURED:
            if threshold.required:
                decision = AdmissionDecision.UNKNOWN
                reasons.append(f"{prefix}_{fact.value_state.value}")
            continue
        assert fact.value_int is not None
        if not _threshold_passes(threshold, fact.value_int):
            decision = AdmissionDecision.DENIED
            reasons.append(f"{prefix}_THRESHOLD_NOT_MET")
    if any(reason.endswith("THRESHOLD_NOT_MET") for reason in reasons):
        decision = AdmissionDecision.DENIED
    return decision, sorted(set(reasons))


def evaluate_admission(
    policy_value: Mapping[str, Any],
    observation_value: Mapping[str, Any],
    *,
    decision_id: str,
    evaluated_at: str,
) -> ResourceAdmissionDecisionReceipt:
    policy = ResourceAdmissionPolicyRevision.from_dict(policy_value).to_dict()
    observation = ResourcePreflightObservationReceipt.from_dict(observation_value).to_dict()
    if policy["project_id"] != observation["project_id"]:
        raise ValueError("policy and observation project mismatch")
    if policy["policy_id"] != observation["policy_id"]:
        raise ValueError("policy and observation policy_id mismatch")
    if policy["policy_revision_sha256"] != observation["policy_revision_sha256"]:
        raise ValueError("observation is not bound to the exact policy revision")
    _timestamp(evaluated_at, "evaluated_at")
    decision, reasons = _classify_facts(policy, _facts(observation["facts"]), evaluated_at=evaluated_at)
    body = {
        "schema": SCHEMA_ID,
        "record_type": ResourceAdmissionDecisionReceipt.RECORD_TYPE,
        "task_owner": "TASK-020",
        "project_id": policy["project_id"],
        "decision_id": _id(decision_id, "decision_id"),
        "operation_identity": observation["operation_identity"],
        "policy_revision_sha256": policy["policy_revision_sha256"],
        "observation_receipt_sha256": observation["observation_receipt_sha256"],
        "evaluated_at": evaluated_at,
        "decision": decision.value,
        "reason_codes": reasons,
        "reservation_started": False,
        "dispatch_started": False,
        "execution_authorized": False,
    }
    return ResourceAdmissionDecisionReceipt.from_dict(_with_hash(body, ResourceAdmissionDecisionReceipt.HASH_FIELD))


def classify_runtime_watermark(
    policy_value: Mapping[str, Any],
    admission_value: Mapping[str, Any],
    facts: Sequence[Mapping[str, Any]],
    *,
    watermark_receipt_id: str,
    sequence: int,
    window_started_at: str,
    window_ended_at: str,
) -> RuntimeResourceWatermarkReceipt:
    policy = ResourceAdmissionPolicyRevision.from_dict(policy_value).to_dict()
    admission = ResourceAdmissionDecisionReceipt.from_dict(admission_value).to_dict()
    if policy["project_id"] != admission["project_id"]:
        raise ValueError("policy and admission project mismatch")
    if policy["policy_revision_sha256"] != admission["policy_revision_sha256"]:
        raise ValueError("admission is not bound to the exact policy revision")
    if admission["decision"] != AdmissionDecision.ADMITTED.value:
        raise ValueError("runtime watermark requires an ADMITTED decision")
    parsed_facts = _facts(facts)
    classified, reasons = _classify_facts(policy, parsed_facts, evaluated_at=window_ended_at)
    state = {
        AdmissionDecision.ADMITTED: RuntimeWatermarkState.WITHIN_ADMITTED_BOUNDS,
        AdmissionDecision.DENIED: RuntimeWatermarkState.BREACH,
        AdmissionDecision.UNKNOWN: RuntimeWatermarkState.UNKNOWN,
    }[classified]
    body = {
        "schema": SCHEMA_ID,
        "record_type": RuntimeResourceWatermarkReceipt.RECORD_TYPE,
        "task_owner": "TASK-020",
        "project_id": policy["project_id"],
        "watermark_receipt_id": _id(watermark_receipt_id, "watermark_receipt_id"),
        "operation_identity": admission["operation_identity"],
        "policy_revision_sha256": policy["policy_revision_sha256"],
        "admission_decision_sha256": admission["admission_decision_sha256"],
        "sequence": sequence,
        "window_started_at": window_started_at,
        "window_ended_at": window_ended_at,
        "facts": [fact.to_dict() for fact in parsed_facts],
        "state": state.value,
        "reason_codes": reasons,
        "collector_executed_by_module": False,
        "process_control_started": False,
        "app_operation_started": False,
    }
    return RuntimeResourceWatermarkReceipt.from_dict(
        _with_hash(body, RuntimeResourceWatermarkReceipt.HASH_FIELD)
    )


def derive_incident(
    watermark_value: Mapping[str, Any],
    *,
    incident_receipt_id: str,
    detected_at: str,
) -> ResourceIncidentReceipt:
    watermark = RuntimeResourceWatermarkReceipt.from_dict(watermark_value).to_dict()
    if watermark["state"] == RuntimeWatermarkState.WITHIN_ADMITTED_BOUNDS.value:
        raise ValueError("healthy watermark cannot produce an incident")
    reasons = tuple(watermark["reason_codes"])
    fact_kinds = tuple(fact["metric_kind"] for fact in watermark["facts"])
    affected = sorted(
        kind for kind in fact_kinds if any(reason.startswith(kind + "_") for reason in reasons)
    )
    if not affected:
        affected = sorted(fact_kinds)
    if any(reason.startswith("APP_INSTANCE_COUNT_") for reason in reasons):
        kind = ResourceIncidentKind.APP_CARDINALITY
    elif any(reason.startswith("PROCESS_INSTANCE_COUNT_") for reason in reasons):
        kind = ResourceIncidentKind.PROCESS_CARDINALITY
    elif any("STALE_OR_FUTURE" in reason for reason in reasons):
        kind = ResourceIncidentKind.STALE_EVIDENCE
    elif watermark["state"] == RuntimeWatermarkState.BREACH.value:
        kind = ResourceIncidentKind.THRESHOLD_BREACH
    else:
        kind = ResourceIncidentKind.OBSERVATION_ERROR
    body = {
        "schema": SCHEMA_ID,
        "record_type": ResourceIncidentReceipt.RECORD_TYPE,
        "task_owner": "TASK-020",
        "project_id": watermark["project_id"],
        "incident_receipt_id": _id(incident_receipt_id, "incident_receipt_id"),
        "operation_identity": watermark["operation_identity"],
        "watermark_receipt_sha256": watermark["watermark_receipt_sha256"],
        "detected_at": detected_at,
        "state": (
            ResourceIncidentState.CONFIRMED.value
            if watermark["state"] == RuntimeWatermarkState.BREACH.value
            else ResourceIncidentState.UNKNOWN.value
        ),
        "incident_kind": kind.value,
        "affected_metrics": affected,
        "reason_codes": list(reasons),
        "termination_requested": False,
        "process_kill_started": False,
        "app_stop_started": False,
    }
    return ResourceIncidentReceipt.from_dict(_with_hash(body, ResourceIncidentReceipt.HASH_FIELD))


def classify_operation_gate(
    *,
    project_id: str,
    binding_id: str,
    operation_identity: str,
    operation_scope: OperationScope,
    contract_state: ContractState,
    decision_ref: str | None,
    admission_decision_sha256: str | None,
    admission_decision: AdmissionDecision | None,
) -> ResourceOperationGateBinding:
    if contract_state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        gate = OperationGateDecision.UNKNOWN
        reasons = ["CANONICAL_REF_NOT_PROVIDED"]
    elif contract_state is ContractState.BOUND_VERIFIED and admission_decision is AdmissionDecision.ADMITTED:
        gate = OperationGateDecision.READY_FOR_EXTERNAL_HUMAN_GATE
        reasons = []
    elif contract_state is ContractState.UNKNOWN or admission_decision is AdmissionDecision.UNKNOWN:
        gate = OperationGateDecision.UNKNOWN
        reasons = ["ADMISSION_UNKNOWN"]
    else:
        gate = OperationGateDecision.BLOCKED
        reasons = ["ADMISSION_NOT_VERIFIED_OR_DENIED"]
    body = {
        "schema": SCHEMA_ID,
        "record_type": ResourceOperationGateBinding.RECORD_TYPE,
        "task_owner": "TASK-020",
        "project_id": _id(project_id, "project_id"),
        "binding_id": _id(binding_id, "binding_id"),
        "operation_identity": _id(operation_identity, "operation_identity"),
        "operation_scope": operation_scope.value,
        "contract_state": contract_state.value,
        "decision_ref": decision_ref,
        "admission_decision_sha256": admission_decision_sha256,
        "admission_decision": admission_decision.value if admission_decision is not None else None,
        "gate_decision": gate.value,
        "reason_codes": reasons,
        "execution_authorized": False,
        "reservation_started": False,
        "dispatch_started": False,
        "process_started": False,
        "app_launched": False,
    }
    return ResourceOperationGateBinding.from_dict(_with_hash(body, ResourceOperationGateBinding.HASH_FIELD))


def private_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    return parse_resource_record(value).to_dict()


def public_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    result = parse_resource_record(value).to_dict()
    private_fields = {
        "target_ref", "source_profile_ref", "decision_ref", "operation_input_sha256",
        "target_revision_sha256", "source_profile_sha256", "value_int",
    }

    def scrub(item: Any) -> Any:
        if isinstance(item, dict):
            return {key: scrub(child) for key, child in item.items() if key not in private_fields}
        if isinstance(item, list):
            return [scrub(child) for child in item]
        return copy.deepcopy(item)

    projection = scrub(result)
    projection["projection"] = "PUBLIC_BODY_FREE"
    return projection


def module_effect_surface() -> dict[str, bool]:
    return {
        "os_collector": False,
        "resource_reservation": False,
        "scheduler": False,
        "process_control": False,
        "app_operation": False,
        "filesystem_effect": False,
        "network_effect": False,
        "provider_effect": False,
    }
