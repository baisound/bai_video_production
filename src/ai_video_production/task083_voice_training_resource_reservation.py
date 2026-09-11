"""TASK-083 body-free voice-training resource reservation contract.

This module is deliberately effect-free.  It compiles and validates public
metadata, and provides an in-memory fixture state machine for fault tests.  It
does not inspect hardware, reserve CPU/GPU/RAM/VRAM/disk, create a process,
start training, persist a ledger, or mint training authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import copy
import json
from pathlib import PureWindowsPath
import re
from threading import RLock
from types import MappingProxyType
from typing import Any, ClassVar, Mapping

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .voice_dataset_revision import TrainingInputSnapshot
from .voice_training_run import ExecutionResourceReservationBinding, TrainingDurableJobBinding


SCHEMA_ID = "bai.task083.voice-training-resource-reservation.v1"
SCHEMA_VERSION = 1
CANONICAL_OWNER_TASK = "TASK-083"
RECEIPT_ROLE = "TRAINING_RESOURCE_RESERVATION"
MAX_SECURITY_JSON_BYTES = 65_536
MAX_SECURITY_JSON_DEPTH = 16

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
)
_PLAN_DOMAIN = b"BAI:TASK-083:RESOURCE-RESERVATION-PLAN:V1\x00"
_OBSERVATION_DOMAIN = b"BAI:TASK-083:FIXTURE-OBSERVATION:V1\x00"
_RECEIPT_DOMAIN = b"BAI:TASK-083:RESOURCE-RESERVATION-RECEIPT:V1\x00"
_READBACK_DOMAIN = b"BAI:TASK-083:RESOURCE-RESERVATION-READBACK:V1\x00"
_DECISION_DOMAIN = b"BAI:TASK-083:RESOURCE-RESERVATION-DECISION:V1\x00"
_PRODUCTION_ADMISSION_DOMAIN = b"BAI:TASK-083:PRODUCTION-RESERVATION-ADMISSION:V1\x00"
_NEGATIVE_ACK_DOMAIN = b"BAI:TASK-083:FIXTURE-DURABLE-NEGATIVE-ACK:V1\x00"
_FACTORY_KEY = object()


class ReservationState(str, Enum):
    PREPARED = "PREPARED"
    RESERVED = "RESERVED"
    CONSUMPTION_STARTED = "CONSUMPTION_STARTED"
    CONSUMED = "CONSUMED"
    EXPIRED = "EXPIRED"
    CONSUMPTION_UNKNOWN = "CONSUMPTION_UNKNOWN"
    FAILED_CLOSED = "FAILED_CLOSED"


class FixtureDecision(str, Enum):
    READY_FIXTURE_ONLY = "READY_FIXTURE_ONLY"
    BLOCKED = "BLOCKED"


_ALLOWED_TRANSITIONS: dict[ReservationState, frozenset[ReservationState]] = {
    ReservationState.PREPARED: frozenset(
        {ReservationState.RESERVED, ReservationState.EXPIRED, ReservationState.FAILED_CLOSED}
    ),
    ReservationState.RESERVED: frozenset(
        {
            ReservationState.CONSUMPTION_STARTED,
            ReservationState.EXPIRED,
            ReservationState.FAILED_CLOSED,
        }
    ),
    ReservationState.CONSUMPTION_STARTED: frozenset(
        {
            ReservationState.CONSUMED,
            ReservationState.CONSUMPTION_UNKNOWN,
            ReservationState.FAILED_CLOSED,
        }
    ),
    ReservationState.CONSUMED: frozenset(),
    ReservationState.EXPIRED: frozenset(),
    ReservationState.CONSUMPTION_UNKNOWN: frozenset(),
    ReservationState.FAILED_CLOSED: frozenset(),
}

_RESOURCE_FIELDS = ("cpu_units", "ram_bytes", "vram_bytes", "disk_bytes")
_COMMON_BINDING_FIELDS = {
    "project_id",
    "job_id",
    "job_revision_sha256",
    "run_id",
    "training_input_snapshot_sha256",
    "recipe_revision_sha256",
    "backend_id",
    "backend_build_sha256",
    "runtime_sha256",
    "device_profile_sha256",
    "policy_revision_sha256",
}


def _validate_state_revision(state: ReservationState, revision: int, *, allow_prepared: bool) -> None:
    allowed = {
        ReservationState.PREPARED: {0} if allow_prepared else set(),
        ReservationState.RESERVED: {1},
        ReservationState.CONSUMPTION_STARTED: {2},
        ReservationState.CONSUMED: {3},
        ReservationState.EXPIRED: {1, 2},
        ReservationState.CONSUMPTION_UNKNOWN: {3},
        ReservationState.FAILED_CLOSED: {1, 2, 3},
    }[state]
    if revision not in allowed:
        raise ValueError("reservation state/revision mismatch")


def _validate_production_state_flags(value: Mapping[str, Any], state: ReservationState) -> None:
    live_expected = state in {
        ReservationState.RESERVED,
        ReservationState.CONSUMPTION_STARTED,
    }
    if value["live_capability_present"] is not live_expected:
        raise ValueError("production live capability/state mismatch")
    if state is ReservationState.CONSUMPTION_UNKNOWN:
        if value["training_dispatched"] is not None or value["training_started"] is not None:
            raise ValueError("ambiguous post-burn training flags must remain null/UNKNOWN")
    else:
        started_expected = state is ReservationState.CONSUMED
        if (
            value["training_dispatched"] is not started_expected
            or value["training_started"] is not started_expected
        ):
            raise ValueError("production training flags/state mismatch")
    if "native_reservation_invoked" in value and value["native_reservation_invoked"] is not True:
        raise ValueError("production record requires native reservation invocation")


def _expect_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} is invalid")
    lowered = value.lower()
    if lowered.startswith(("file:", "http:", "https:")) or value.startswith(("/", "\\")):
        raise ValueError(f"{name} must be a body-free logical identifier")
    if PureWindowsPath(value).drive or ".." in re.split(r"[\\/]", value):
        raise ValueError(f"{name} must not contain a host/private path")
    if not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be SHA-256")
    return validate_sha256(value, field_name=name)


def _integer(value: Any, name: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _boolean(value: Any, name: str, *, exact: bool | None = None) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be boolean")
    if exact is not None and value is not exact:
        raise ValueError(f"{name} must be {str(exact).lower()}")
    return value


def _timestamp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _TIMESTAMP_RE.fullmatch(value):
        raise ValueError(f"{name} must be RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be RFC3339 UTC") from exc
    if parsed.utcoffset() is None:
        raise ValueError(f"{name} must be RFC3339 UTC")
    return value


def _timestamp_value(value: str) -> datetime:
    _timestamp(value, "timestamp")
    return datetime.fromisoformat(value[:-1] + "+00:00")


def _timestamp_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _digest(value: Mapping[str, Any], field: str, domain: bytes) -> str:
    body = copy.deepcopy(dict(value))
    body.pop(field, None)
    return sha256_bytes(domain + canonical_json_bytes(body))


def _with_digest(value: Mapping[str, Any], field: str, domain: bytes) -> dict[str, Any]:
    body = copy.deepcopy(dict(value))
    body[field] = _digest(body, field, domain)
    return body


def _verify_digest(value: Mapping[str, Any], field: str, domain: bytes) -> None:
    if _sha(value[field], field) != _digest(value, field, domain):
        raise ValueError(f"{field} mismatch")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _validate_resources(value: Mapping[str, Any], name: str) -> dict[str, int]:
    _expect_keys(value, set(_RESOURCE_FIELDS), name)
    return {field: _integer(value[field], f"{name}.{field}", minimum=1) for field in _RESOURCE_FIELDS}


def _validate_common_binding(value: Mapping[str, Any]) -> None:
    for field in _COMMON_BINDING_FIELDS:
        if field.endswith("sha256"):
            _sha(value[field], field)
        else:
            _identifier(value[field], field)


def _validate_plan(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type",
        "schema_version",
        "canonical_owner_task",
        "project_id",
        "job_id",
        "job_operation_id",
        "job_revision",
        "job_revision_sha256",
        "job_binding_sha256",
        "run_id",
        "training_input_snapshot_ref",
        "training_input_snapshot_sha256",
        "dataset_id",
        "recipe_revision_ref",
        "recipe_revision_sha256",
        "backend_id",
        "backend_build_sha256",
        "runtime_revision",
        "runtime_sha256",
        "device_profile_ref",
        "device_profile_sha256",
        "capability_admission_sha256",
        "resource_floor",
        "resource_ceiling",
        "policy_revision_sha256",
        "cpu_unit",
        "memory_unit",
        "durable_job_source_state",
        "voice_training_workload_id",
        "voice_training_workload_mapping_state",
        "issued_at",
        "expires_at",
        "fixture_only",
        "authority_created",
        "audio_body_persisted",
        "environment_body_persisted",
        "native_reservation_invoked",
        "training_dispatched",
        "resource_effect_count",
        "production_eligible",
        "plan_sha256",
    }
    _expect_keys(value, expected, "Task083ResourceReservationPlanV1")
    if value["record_type"] != "Task083ResourceReservationPlanV1":
        raise ValueError("plan record_type is invalid")
    if value["schema_version"] != SCHEMA_VERSION or value["canonical_owner_task"] != CANONICAL_OWNER_TASK:
        raise ValueError("plan discriminator is invalid")
    _validate_common_binding(value)
    for field in (
        "job_operation_id",
        "training_input_snapshot_ref",
        "dataset_id",
        "recipe_revision_ref",
        "runtime_revision",
        "device_profile_ref",
    ):
        _identifier(value[field], field)
    _integer(value["job_revision"], "job_revision", minimum=1)
    _sha(value["job_binding_sha256"], "job_binding_sha256")
    _sha(value["capability_admission_sha256"], "capability_admission_sha256")
    if value["cpu_unit"] != "LOGICAL_PROCESSOR" or value["memory_unit"] != "BYTES":
        raise ValueError("resource units are invalid")
    if value["durable_job_source_state"] != "NOT_AVAILABLE_CURRENT_SOURCE":
        raise ValueError("current durable Job source gap must remain explicit")
    if value["voice_training_workload_id"] != "audio.voice.local":
        raise ValueError("voice training workload identity is invalid")
    if value["voice_training_workload_mapping_state"] != "DISABLED_UNTIL_MAPPED":
        raise ValueError("current voice training workload gap must remain explicit")
    floor = _validate_resources(value["resource_floor"], "resource_floor")
    ceiling = _validate_resources(value["resource_ceiling"], "resource_ceiling")
    if any(floor[field] > ceiling[field] for field in _RESOURCE_FIELDS):
        raise ValueError("resource floor exceeds ceiling")
    issued = _timestamp_value(_timestamp(value["issued_at"], "issued_at"))
    expires = _timestamp_value(_timestamp(value["expires_at"], "expires_at"))
    if expires <= issued:
        raise ValueError("plan expiry must be after issue time")
    for field in (
        "fixture_only",
        "authority_created",
        "audio_body_persisted",
        "environment_body_persisted",
        "native_reservation_invoked",
        "training_dispatched",
        "production_eligible",
    ):
        _boolean(value[field], field, exact=(field == "fixture_only"))
    _integer(value["resource_effect_count"], "resource_effect_count")
    if any(
        value[field]
        for field in (
            "authority_created",
            "audio_body_persisted",
            "environment_body_persisted",
            "native_reservation_invoked",
            "training_dispatched",
            "production_eligible",
        )
    ) or value["resource_effect_count"] != 0:
        raise ValueError("effect-free plan cannot claim authority, bodies, reservation, or dispatch")
    _verify_digest(value, "plan_sha256", _PLAN_DOMAIN)


def _validate_observation(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type",
        "schema_version",
        "fixture_only",
        "plan_sha256",
        *_COMMON_BINDING_FIELDS,
        "granted_resources",
        "thermal_state",
        "power_state",
        "gpu_present",
        "live_capability_present",
        "observed_at",
        "fresh_until",
        "native_observation_invoked",
        "raw_hardware_body_persisted",
        "observation_sha256",
    }
    _expect_keys(value, expected, "Task083FixtureResourceObservationV1")
    if value["record_type"] != "Task083FixtureResourceObservationV1" or value["schema_version"] != 1:
        raise ValueError("fixture observation discriminator is invalid")
    _boolean(value["fixture_only"], "fixture_only", exact=True)
    _sha(value["plan_sha256"], "plan_sha256")
    _validate_common_binding(value)
    _validate_resources(value["granted_resources"], "granted_resources")
    if value["thermal_state"] not in {"PASS", "FAIL", "UNKNOWN"}:
        raise ValueError("thermal_state is invalid")
    if value["power_state"] not in {"PASS", "FAIL", "UNKNOWN"}:
        raise ValueError("power_state is invalid")
    _boolean(value["gpu_present"], "gpu_present")
    _boolean(value["live_capability_present"], "live_capability_present")
    _timestamp(value["observed_at"], "observed_at")
    observed_at = _timestamp_value(value["observed_at"])
    fresh_until = _timestamp_value(_timestamp(value["fresh_until"], "fresh_until"))
    if fresh_until < observed_at:
        raise ValueError("fixture observation freshness window is invalid")
    _boolean(value["native_observation_invoked"], "native_observation_invoked", exact=False)
    _boolean(value["raw_hardware_body_persisted"], "raw_hardware_body_persisted", exact=False)
    _verify_digest(value, "observation_sha256", _OBSERVATION_DOMAIN)


def _validate_receipt(value: Mapping[str, Any], *, fixture: bool) -> None:
    expected = {
        "record_type",
        "schema_version",
        "canonical_owner_task",
        "receipt_role",
        "reservation_id",
        "request_id",
        "plan_sha256",
        "h3_authorization_v2_sha256",
        "task084_destination_plan_sha256",
        "compound_operation_id",
        "compound_operation_sha256",
        "compound_stage",
        *_COMMON_BINDING_FIELDS,
        "state",
        "reservation_revision",
        "previous_receipt_sha256",
        "durable_negative_acknowledgement_sha256",
        "granted_resources",
        "thermal_state",
        "power_state",
        "reason_codes",
        "event_at",
        "expires_at",
        "fixture_only",
        "authority_created",
        "live_capability_restorable",
        "live_capability_present",
        "production_backend_invoked",
        "native_reservation_invoked",
        "training_dispatched",
        "training_started",
        "resource_effect_count",
        "receipt_sha256",
    }
    _expect_keys(value, expected, "Task083ExecutionResourceReservationReceiptV1")
    if (
        value["record_type"]
        != (
            "Task083FixtureExecutionResourceReservationReceiptV1"
            if fixture
            else "Task083ExecutionResourceReservationReceiptV1"
        )
        or value["schema_version"] != SCHEMA_VERSION
        or value["canonical_owner_task"] != CANONICAL_OWNER_TASK
        or value["receipt_role"] != RECEIPT_ROLE
    ):
        raise ValueError("receipt discriminator is invalid")
    for field in ("reservation_id", "request_id"):
        _identifier(value[field], field)
    _sha(value["plan_sha256"], "plan_sha256")
    if fixture:
        for field in (
            "h3_authorization_v2_sha256",
            "task084_destination_plan_sha256",
            "compound_operation_id",
            "compound_operation_sha256",
        ):
            if value[field] is not None:
                raise ValueError("fixture receipt must not invent production lineage")
        if value["compound_stage"] != "FIXTURE_ONLY":
            raise ValueError("fixture receipt compound_stage must be FIXTURE_ONLY")
    else:
        for field in (
            "h3_authorization_v2_sha256",
            "task084_destination_plan_sha256",
            "compound_operation_sha256",
        ):
            _sha(value[field], field)
        _identifier(value["compound_operation_id"], "compound_operation_id")
        if value["compound_stage"] not in {
            "RESERVATION_ACTIVATED",
            "RESERVATION_CONSUMPTION_STARTED",
            "TRAINING_DISPATCH_ACKNOWLEDGED",
            "TRAINING_DISPATCH_NOT_STARTED",
            "TRAINING_DISPATCH_UNKNOWN",
        }:
            raise ValueError("production receipt compound_stage is invalid")
    _validate_common_binding(value)
    try:
        state = ReservationState(value["state"])
    except (TypeError, ValueError) as exc:
        raise ValueError("reservation state is invalid") from exc
    revision = _integer(value["reservation_revision"], "reservation_revision", minimum=1)
    _validate_state_revision(state, revision, allow_prepared=False)
    previous = value["previous_receipt_sha256"]
    if revision == 1:
        if previous is not None:
            raise ValueError("first receipt cannot have a previous receipt")
    else:
        _sha(previous, "previous_receipt_sha256")
    negative_ack_sha256 = value["durable_negative_acknowledgement_sha256"]
    if state is ReservationState.FAILED_CLOSED and revision == 3:
        _sha(negative_ack_sha256, "durable_negative_acknowledgement_sha256")
    elif negative_ack_sha256 is not None:
        raise ValueError("durable negative acknowledgement is valid only for rev3 FAILED_CLOSED")
    _validate_resources(value["granted_resources"], "granted_resources")
    if value["thermal_state"] not in {"PASS", "FAIL", "UNKNOWN"}:
        raise ValueError("thermal_state is invalid")
    if value["power_state"] not in {"PASS", "FAIL", "UNKNOWN"}:
        raise ValueError("power_state is invalid")
    reasons = value["reason_codes"]
    if not isinstance(reasons, list) or len(reasons) > 32:
        raise ValueError("reason_codes must be a bounded list")
    for reason in reasons:
        _identifier(reason, "reason_code")
    if reasons != sorted(set(reasons)):
        raise ValueError("reason_codes must be sorted and unique")
    _timestamp(value["event_at"], "event_at")
    _timestamp(value["expires_at"], "expires_at")
    _boolean(value["fixture_only"], "fixture_only", exact=fixture)
    for field in (
        "authority_created",
        "live_capability_restorable",
        "live_capability_present",
        "production_backend_invoked",
        "native_reservation_invoked",
    ):
        _boolean(value[field], field, exact=False if fixture else None)
    if fixture:
        _boolean(value["training_dispatched"], "training_dispatched", exact=False)
        _boolean(value["training_started"], "training_started", exact=False)
    elif state is not ReservationState.CONSUMPTION_UNKNOWN:
        _boolean(value["training_dispatched"], "training_dispatched")
        _boolean(value["training_started"], "training_started")
    _integer(value["resource_effect_count"], "resource_effect_count")
    if fixture and value["resource_effect_count"] != 0:
        raise ValueError("fixture receipt resource_effect_count must be zero")
    if not fixture:
        if value["resource_effect_count"] < 1 or not value["production_backend_invoked"]:
            raise ValueError("production receipt requires a real backend effect")
        if value["authority_created"] or value["live_capability_restorable"]:
            raise ValueError("serialized production receipt cannot itself create/restorable authority")
        _validate_production_state_flags(value, state)
        expected_stage = {
            ReservationState.RESERVED: "RESERVATION_ACTIVATED",
            ReservationState.CONSUMPTION_STARTED: "RESERVATION_CONSUMPTION_STARTED",
            ReservationState.CONSUMED: "TRAINING_DISPATCH_ACKNOWLEDGED",
            ReservationState.EXPIRED: "TRAINING_DISPATCH_NOT_STARTED",
            ReservationState.FAILED_CLOSED: "TRAINING_DISPATCH_NOT_STARTED",
            ReservationState.CONSUMPTION_UNKNOWN: "TRAINING_DISPATCH_UNKNOWN",
        }.get(state)
        if expected_stage is None or value["compound_stage"] != expected_stage:
            raise ValueError("production receipt state/compound_stage mismatch")
    _verify_digest(value, "receipt_sha256", _RECEIPT_DOMAIN)


def _validate_readback(value: Mapping[str, Any], *, fixture: bool) -> None:
    expected = {
        "record_type",
        "schema_version",
        "canonical_owner_task",
        "receipt_role",
        "reservation_id",
        "plan_sha256",
        "h3_authorization_v2_sha256",
        "task084_destination_plan_sha256",
        "compound_operation_id",
        "compound_operation_sha256",
        "compound_stage",
        *_COMMON_BINDING_FIELDS,
        "state",
        "reservation_revision",
        "head_receipt_sha256",
        "event_count",
        "read_back_at",
        "fixture_only",
        "authority_created",
        "live_capability_present",
        "live_capability_restorable",
        "production_backend_invoked",
        "training_dispatched",
        "training_started",
        "resource_effect_count",
        "readback_sha256",
    }
    _expect_keys(value, expected, "Task083ResourceReservationReadbackV1")
    if (
        value["record_type"]
        != (
            "Task083FixtureResourceReservationReadbackV1"
            if fixture
            else "Task083ResourceReservationReadbackV1"
        )
        or value["schema_version"] != 1
        or value["canonical_owner_task"] != CANONICAL_OWNER_TASK
        or value["receipt_role"] != RECEIPT_ROLE
    ):
        raise ValueError("readback discriminator is invalid")
    _identifier(value["reservation_id"], "reservation_id")
    _sha(value["plan_sha256"], "plan_sha256")
    if fixture:
        for field in (
            "h3_authorization_v2_sha256",
            "task084_destination_plan_sha256",
            "compound_operation_id",
            "compound_operation_sha256",
        ):
            if value[field] is not None:
                raise ValueError("fixture readback must not invent production lineage")
        if value["compound_stage"] != "FIXTURE_ONLY":
            raise ValueError("fixture readback compound_stage must be FIXTURE_ONLY")
    else:
        for field in (
            "h3_authorization_v2_sha256",
            "task084_destination_plan_sha256",
            "compound_operation_sha256",
        ):
            _sha(value[field], field)
        _identifier(value["compound_operation_id"], "compound_operation_id")
        _identifier(value["compound_stage"], "compound_stage")
    _validate_common_binding(value)
    try:
        state = ReservationState(value["state"])
    except (TypeError, ValueError) as exc:
        raise ValueError("readback state is invalid") from exc
    revision = _integer(value["reservation_revision"], "reservation_revision")
    event_count = _integer(value["event_count"], "event_count")
    _validate_state_revision(state, revision, allow_prepared=True)
    if revision != event_count:
        raise ValueError("readback revision/event_count mismatch")
    if revision == 0:
        if value["head_receipt_sha256"] is not None:
            raise ValueError("empty readback cannot claim a head receipt")
        if value["state"] != ReservationState.PREPARED.value:
            raise ValueError("empty readback must be PREPARED")
    else:
        _sha(value["head_receipt_sha256"], "head_receipt_sha256")
    _timestamp(value["read_back_at"], "read_back_at")
    _boolean(value["fixture_only"], "fixture_only", exact=fixture)
    _boolean(value["authority_created"], "authority_created", exact=False)
    _boolean(
        value["live_capability_present"],
        "live_capability_present",
        exact=False if fixture else None,
    )
    _boolean(value["live_capability_restorable"], "live_capability_restorable", exact=False)
    _boolean(
        value["production_backend_invoked"],
        "production_backend_invoked",
        exact=False if fixture else None,
    )
    if fixture:
        _boolean(value["training_dispatched"], "training_dispatched", exact=False)
        _boolean(value["training_started"], "training_started", exact=False)
    elif state is not ReservationState.CONSUMPTION_UNKNOWN:
        _boolean(value["training_dispatched"], "training_dispatched")
        _boolean(value["training_started"], "training_started")
    _integer(value["resource_effect_count"], "resource_effect_count")
    if fixture and value["resource_effect_count"] != 0:
        raise ValueError("fixture readback resource_effect_count must be zero")
    if not fixture and (
        value["resource_effect_count"] < 1 or not value["production_backend_invoked"]
    ):
        raise ValueError("production readback requires a real backend effect")
    if not fixture:
        _validate_production_state_flags(value, state)
        expected_stage = {
            ReservationState.RESERVED: "RESERVATION_ACTIVATED",
            ReservationState.CONSUMPTION_STARTED: "RESERVATION_CONSUMPTION_STARTED",
            ReservationState.CONSUMED: "TRAINING_DISPATCH_ACKNOWLEDGED",
            ReservationState.EXPIRED: "TRAINING_DISPATCH_NOT_STARTED",
            ReservationState.FAILED_CLOSED: "TRAINING_DISPATCH_NOT_STARTED",
            ReservationState.CONSUMPTION_UNKNOWN: "TRAINING_DISPATCH_UNKNOWN",
        }.get(state)
        if expected_stage is None or value["compound_stage"] != expected_stage:
            raise ValueError("production readback state/compound_stage mismatch")
    _verify_digest(value, "readback_sha256", _READBACK_DOMAIN)


def _validate_decision(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type",
        "schema_version",
        "canonical_owner_task",
        "plan_sha256",
        "observation_sha256",
        "decision",
        "reason_codes",
        "evaluated_at",
        "fixture_only",
        "authority_created",
        "native_reservation_invoked",
        "training_dispatched",
        "resource_effect_count",
        "decision_sha256",
    }
    _expect_keys(value, expected, "Task083ResourceReservationDecisionV1")
    if (
        value["record_type"] != "Task083ResourceReservationDecisionV1"
        or value["schema_version"] != 1
        or value["canonical_owner_task"] != CANONICAL_OWNER_TASK
    ):
        raise ValueError("decision discriminator is invalid")
    _sha(value["plan_sha256"], "plan_sha256")
    _sha(value["observation_sha256"], "observation_sha256")
    try:
        FixtureDecision(value["decision"])
    except (TypeError, ValueError) as exc:
        raise ValueError("fixture decision is invalid") from exc
    reasons = value["reason_codes"]
    if not isinstance(reasons, list) or reasons != sorted(set(reasons)) or len(reasons) > 32:
        raise ValueError("decision reason_codes must be sorted, unique, and bounded")
    for reason in reasons:
        _identifier(reason, "reason_code")
    if value["decision"] == FixtureDecision.READY_FIXTURE_ONLY.value and reasons:
        raise ValueError("READY_FIXTURE_ONLY cannot contain blocking reasons")
    if value["decision"] == FixtureDecision.BLOCKED.value and not reasons:
        raise ValueError("BLOCKED requires a reason")
    _timestamp(value["evaluated_at"], "evaluated_at")
    _boolean(value["fixture_only"], "fixture_only", exact=True)
    for field in ("authority_created", "native_reservation_invoked", "training_dispatched"):
        _boolean(value[field], field, exact=False)
    _integer(value["resource_effect_count"], "resource_effect_count")
    if value["resource_effect_count"] != 0:
        raise ValueError("fixture decision resource_effect_count must be zero")
    _verify_digest(value, "decision_sha256", _DECISION_DOMAIN)


def _validate_production_admission(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type",
        "schema_version",
        "canonical_owner_task",
        "plan_sha256",
        "decision",
        "reason_codes",
        "evaluated_at",
        "fixture_only",
        "authority_created",
        "native_reservation_invoked",
        "training_dispatched",
        "production_eligible",
        "resource_effect_count",
        "admission_sha256",
    }
    _expect_keys(value, expected, "Task083ProductionReservationAdmissionV1")
    if (
        value["record_type"] != "Task083ProductionReservationAdmissionV1"
        or value["schema_version"] != 1
        or value["canonical_owner_task"] != CANONICAL_OWNER_TASK
        or value["decision"] != "BLOCKED"
    ):
        raise ValueError("production admission discriminator/decision is invalid")
    _sha(value["plan_sha256"], "plan_sha256")
    expected_reasons = [
        "COMPOUND_OPERATION_NOT_BOUND",
        "DURABLE_JOB_SOURCE_NOT_AVAILABLE",
        "H3_AUTHORIZATION_V2_NOT_PRESENT",
        "NATIVE_BACKEND_NOT_IMPLEMENTED",
        "TASK084_DESTINATION_PLAN_NOT_BOUND",
        "VOICE_TRAINING_WORKLOAD_NOT_MAPPED",
    ]
    if value["reason_codes"] != expected_reasons:
        raise ValueError("production admission must preserve current dependency blockers")
    _timestamp(value["evaluated_at"], "evaluated_at")
    _boolean(value["fixture_only"], "fixture_only", exact=True)
    for field in (
        "authority_created",
        "native_reservation_invoked",
        "training_dispatched",
        "production_eligible",
    ):
        _boolean(value[field], field, exact=False)
    _integer(value["resource_effect_count"], "resource_effect_count")
    if value["resource_effect_count"] != 0:
        raise ValueError("production admission evaluation must be effect-free")
    _verify_digest(value, "admission_sha256", _PRODUCTION_ADMISSION_DOMAIN)


def _validate_fixture_negative_acknowledgement(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type",
        "schema_version",
        "canonical_owner_task",
        "reservation_id",
        "acknowledgement_id",
        "plan_sha256",
        "job_revision_sha256",
        "consumption_started_revision",
        "consumption_started_receipt_sha256",
        "process_not_started",
        "job_head_unchanged",
        "live_lease_released",
        "observed_at",
        "fixture_only",
        "production_backend_invoked",
        "training_started",
        "resource_effect_count",
        "acknowledgement_sha256",
    }
    _expect_keys(value, expected, "Task083FixtureDurableNegativeAcknowledgementV1")
    if (
        value["record_type"] != "Task083FixtureDurableNegativeAcknowledgementV1"
        or value["schema_version"] != 1
        or value["canonical_owner_task"] != CANONICAL_OWNER_TASK
    ):
        raise ValueError("negative acknowledgement discriminator is invalid")
    _identifier(value["reservation_id"], "reservation_id")
    _identifier(value["acknowledgement_id"], "acknowledgement_id")
    _sha(value["plan_sha256"], "plan_sha256")
    _sha(value["job_revision_sha256"], "job_revision_sha256")
    _integer(value["consumption_started_revision"], "consumption_started_revision", minimum=2)
    _sha(value["consumption_started_receipt_sha256"], "consumption_started_receipt_sha256")
    for field in ("process_not_started", "job_head_unchanged", "live_lease_released"):
        _boolean(value[field], field, exact=True)
    _timestamp(value["observed_at"], "observed_at")
    _boolean(value["fixture_only"], "fixture_only", exact=True)
    _boolean(value["production_backend_invoked"], "production_backend_invoked", exact=False)
    _boolean(value["training_started"], "training_started", exact=False)
    _integer(value["resource_effect_count"], "resource_effect_count")
    if value["resource_effect_count"] != 0:
        raise ValueError("fixture negative acknowledgement must remain effect-free")
    _verify_digest(value, "acknowledgement_sha256", _NEGATIVE_ACK_DOMAIN)


_VALIDATORS = {
    "Task083ResourceReservationPlanV1": _validate_plan,
    "Task083FixtureResourceObservationV1": _validate_observation,
    "Task083FixtureExecutionResourceReservationReceiptV1": lambda value: _validate_receipt(
        value, fixture=True
    ),
    "Task083ExecutionResourceReservationReceiptV1": lambda value: _validate_receipt(
        value, fixture=False
    ),
    "Task083FixtureResourceReservationReadbackV1": lambda value: _validate_readback(
        value, fixture=True
    ),
    "Task083ResourceReservationReadbackV1": lambda value: _validate_readback(
        value, fixture=False
    ),
    "Task083ResourceReservationDecisionV1": _validate_decision,
    "Task083ProductionReservationAdmissionV1": _validate_production_admission,
    "Task083FixtureDurableNegativeAcknowledgementV1": _validate_fixture_negative_acknowledgement,
}


def validate_record(value: Mapping[str, Any], *, expected_type: str | None = None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("record must be an object")
    record_type = value.get("record_type")
    if record_type not in _VALIDATORS:
        raise ValueError("record_type is unknown")
    if expected_type is not None and record_type != expected_type:
        raise ValueError(f"expected {expected_type}")
    body = copy.deepcopy(dict(value))
    _VALIDATORS[record_type](body)
    return body


def _json_depth(value: Any, *, depth: int = 1) -> int:
    if depth > MAX_SECURITY_JSON_DEPTH:
        raise ValueError("security JSON exceeds maximum depth")
    if isinstance(value, Mapping):
        for item in value.values():
            _json_depth(item, depth=depth + 1)
    elif isinstance(value, list):
        for item in value:
            _json_depth(item, depth=depth + 1)
    return depth


def parse_security_json(raw: bytes, *, expected_type: str | None = None) -> dict[str, Any]:
    """Parse one strict UTF-8, closed TASK-083 record."""

    if type(raw) is not bytes or not raw or len(raw) > MAX_SECURITY_JSON_BYTES:
        raise ValueError("security JSON bytes are empty, non-bytes, or oversized")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("security JSON must not contain a BOM")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("security JSON must be strict UTF-8") from exc
    if text != text.strip():
        raise ValueError("security JSON must not contain leading or trailing bytes")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise ValueError("security JSON contains a duplicate key")
            result[key] = item
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"security JSON constant {value} is forbidden")

    try:
        parsed = json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise ValueError("security JSON is not one complete JSON value") from exc
    _json_depth(parsed)
    return validate_record(parsed, expected_type=expected_type)


@dataclass(frozen=True, slots=True)
class _CanonicalRecord:
    data: Mapping[str, Any]
    RECORD_TYPE: ClassVar[str]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "data",
            _freeze(validate_record(self.data, expected_type=self.RECORD_TYPE)),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "_CanonicalRecord":
        return cls(value)

    @classmethod
    def from_json_bytes(cls, raw: bytes) -> "_CanonicalRecord":
        return cls(parse_security_json(raw, expected_type=cls.RECORD_TYPE))

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.data)

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


class Task083ResourceReservationPlanV1(_CanonicalRecord):
    RECORD_TYPE = "Task083ResourceReservationPlanV1"


class Task083FixtureResourceObservationV1(_CanonicalRecord):
    RECORD_TYPE = "Task083FixtureResourceObservationV1"


class Task083FixtureExecutionResourceReservationReceiptV1(_CanonicalRecord):
    RECORD_TYPE = "Task083FixtureExecutionResourceReservationReceiptV1"


class Task083ExecutionResourceReservationReceiptV1(_CanonicalRecord):
    RECORD_TYPE = "Task083ExecutionResourceReservationReceiptV1"


class Task083FixtureResourceReservationReadbackV1(_CanonicalRecord):
    RECORD_TYPE = "Task083FixtureResourceReservationReadbackV1"


class Task083ResourceReservationReadbackV1(_CanonicalRecord):
    RECORD_TYPE = "Task083ResourceReservationReadbackV1"


class Task083ResourceReservationDecisionV1(_CanonicalRecord):
    RECORD_TYPE = "Task083ResourceReservationDecisionV1"


class Task083ProductionReservationAdmissionV1(_CanonicalRecord):
    RECORD_TYPE = "Task083ProductionReservationAdmissionV1"


class Task083FixtureDurableNegativeAcknowledgementV1(_CanonicalRecord):
    RECORD_TYPE = "Task083FixtureDurableNegativeAcknowledgementV1"


def compile_resource_reservation_plan(
    *,
    training_input_snapshot: Mapping[str, Any],
    training_job_binding: Mapping[str, Any],
    run_id: str,
    training_input_snapshot_ref: str,
    recipe_revision_ref: str,
    recipe_revision_sha256: str,
    backend_id: str,
    backend_build_sha256: str,
    runtime_revision: str,
    runtime_sha256: str,
    device_profile_ref: str,
    device_profile_sha256: str,
    capability_admission_sha256: str,
    resource_floor: Mapping[str, Any],
    resource_ceiling: Mapping[str, Any],
    policy_revision_sha256: str,
    issued_at: str,
    expires_at: str,
) -> Task083ResourceReservationPlanV1:
    """Compile a body-free plan from current TASK-046 bindings."""

    snapshot = TrainingInputSnapshot.from_dict(training_input_snapshot).to_dict()
    job = TrainingDurableJobBinding.from_dict(training_job_binding).to_dict()
    if job["contract_state"] != "BOUND_VERIFIED":
        raise ValueError("training Job/head must be BOUND_VERIFIED")
    if job["job_kind"] != "VOICE_MODEL_TRAINING":
        raise ValueError("training Job kind must be VOICE_MODEL_TRAINING")
    if snapshot["project_id"] is None or snapshot["dataset_id"] is None:
        raise ValueError("training input snapshot identity is incomplete")
    if snapshot["audio_body_persisted"] or snapshot["text_body_persisted"]:
        raise ValueError("training input snapshot must remain body-free")
    body = {
        "record_type": "Task083ResourceReservationPlanV1",
        "schema_version": SCHEMA_VERSION,
        "canonical_owner_task": CANONICAL_OWNER_TASK,
        "project_id": snapshot["project_id"],
        "job_id": job["job_id"],
        "job_operation_id": job["operation_id"],
        "job_revision": job["job_revision"],
        "job_revision_sha256": job["job_revision_sha256"],
        "job_binding_sha256": job["binding_sha256"],
        "run_id": run_id,
        "training_input_snapshot_ref": training_input_snapshot_ref,
        "training_input_snapshot_sha256": snapshot["snapshot_sha256"],
        "dataset_id": snapshot["dataset_id"],
        "recipe_revision_ref": recipe_revision_ref,
        "recipe_revision_sha256": recipe_revision_sha256,
        "backend_id": backend_id,
        "backend_build_sha256": backend_build_sha256,
        "runtime_revision": runtime_revision,
        "runtime_sha256": runtime_sha256,
        "device_profile_ref": device_profile_ref,
        "device_profile_sha256": device_profile_sha256,
        "capability_admission_sha256": capability_admission_sha256,
        "resource_floor": copy.deepcopy(dict(resource_floor)),
        "resource_ceiling": copy.deepcopy(dict(resource_ceiling)),
        "policy_revision_sha256": policy_revision_sha256,
        "cpu_unit": "LOGICAL_PROCESSOR",
        "memory_unit": "BYTES",
        "durable_job_source_state": "NOT_AVAILABLE_CURRENT_SOURCE",
        "voice_training_workload_id": "audio.voice.local",
        "voice_training_workload_mapping_state": "DISABLED_UNTIL_MAPPED",
        "issued_at": issued_at,
        "expires_at": expires_at,
        "fixture_only": True,
        "authority_created": False,
        "audio_body_persisted": False,
        "environment_body_persisted": False,
        "native_reservation_invoked": False,
        "training_dispatched": False,
        "resource_effect_count": 0,
        "production_eligible": False,
    }
    return Task083ResourceReservationPlanV1(_with_digest(body, "plan_sha256", _PLAN_DOMAIN))


def compile_fixture_observation(
    plan: Mapping[str, Any] | Task083ResourceReservationPlanV1,
    *,
    granted_resources: Mapping[str, Any],
    thermal_state: str,
    power_state: str,
    gpu_present: bool,
    live_capability_present: bool,
    observed_at: str,
    fresh_until: str,
) -> Task083FixtureResourceObservationV1:
    parsed = _coerce_plan(plan)
    body = {
        "record_type": "Task083FixtureResourceObservationV1",
        "schema_version": 1,
        "fixture_only": True,
        "plan_sha256": parsed["plan_sha256"],
        **{field: parsed[field] for field in _COMMON_BINDING_FIELDS},
        "granted_resources": copy.deepcopy(dict(granted_resources)),
        "thermal_state": thermal_state,
        "power_state": power_state,
        "gpu_present": gpu_present,
        "live_capability_present": live_capability_present,
        "observed_at": observed_at,
        "fresh_until": fresh_until,
        "native_observation_invoked": False,
        "raw_hardware_body_persisted": False,
    }
    return Task083FixtureResourceObservationV1(
        _with_digest(body, "observation_sha256", _OBSERVATION_DOMAIN)
    )


def _coerce_plan(
    value: Mapping[str, Any] | Task083ResourceReservationPlanV1,
) -> dict[str, Any]:
    if type(value) is Task083ResourceReservationPlanV1:
        return value.to_dict()
    if not isinstance(value, Mapping):
        raise ValueError("plan must be a canonical TASK-083 plan")
    return Task083ResourceReservationPlanV1.from_dict(value).to_dict()


def _coerce_observation(
    value: Mapping[str, Any] | Task083FixtureResourceObservationV1,
) -> dict[str, Any]:
    if type(value) is Task083FixtureResourceObservationV1:
        return value.to_dict()
    if not isinstance(value, Mapping):
        raise ValueError("observation must be a canonical TASK-083 fixture observation")
    return Task083FixtureResourceObservationV1.from_dict(value).to_dict()


def evaluate_fixture_reservation(
    plan: Mapping[str, Any] | Task083ResourceReservationPlanV1,
    observation: Mapping[str, Any] | Task083FixtureResourceObservationV1,
    *,
    evaluated_at: str,
) -> Task083ResourceReservationDecisionV1:
    parsed_plan = _coerce_plan(plan)
    observed = _coerce_observation(observation)
    now = _timestamp_value(_timestamp(evaluated_at, "evaluated_at"))
    reasons: set[str] = set()
    if observed["plan_sha256"] != parsed_plan["plan_sha256"]:
        reasons.add("PLAN_MISMATCH")
    for field in _COMMON_BINDING_FIELDS:
        if observed[field] != parsed_plan[field]:
            reasons.add(f"{field.upper()}_MISMATCH")
    issued = _timestamp_value(parsed_plan["issued_at"])
    expires = _timestamp_value(parsed_plan["expires_at"])
    observed_at = _timestamp_value(observed["observed_at"])
    fresh_until = _timestamp_value(observed["fresh_until"])
    if now < issued or observed_at < issued:
        reasons.add("CLOCK_ROLLBACK")
    if now >= expires or observed_at >= expires:
        reasons.add("PLAN_EXPIRED")
    if observed_at > now:
        reasons.add("OBSERVATION_FROM_FUTURE")
    if now >= fresh_until:
        reasons.add("OBSERVATION_STALE")
    granted = observed["granted_resources"]
    for field in _RESOURCE_FIELDS:
        if granted[field] < parsed_plan["resource_floor"][field]:
            reasons.add(f"{field.upper()}_BELOW_FLOOR")
        if granted[field] > parsed_plan["resource_ceiling"][field]:
            reasons.add(f"{field.upper()}_ABOVE_CEILING")
    if not observed["gpu_present"]:
        reasons.add("GPU_DISAPPEARED")
    if not observed["live_capability_present"]:
        reasons.add("LIVE_CAPABILITY_MISSING")
    if observed["thermal_state"] != "PASS":
        reasons.add("THERMAL_NOT_PASS")
    if observed["power_state"] != "PASS":
        reasons.add("POWER_NOT_PASS")
    body = {
        "record_type": "Task083ResourceReservationDecisionV1",
        "schema_version": 1,
        "canonical_owner_task": CANONICAL_OWNER_TASK,
        "plan_sha256": parsed_plan["plan_sha256"],
        "observation_sha256": observed["observation_sha256"],
        "decision": (
            FixtureDecision.BLOCKED.value if reasons else FixtureDecision.READY_FIXTURE_ONLY.value
        ),
        "reason_codes": sorted(reasons),
        "evaluated_at": evaluated_at,
        "fixture_only": True,
        "authority_created": False,
        "native_reservation_invoked": False,
        "training_dispatched": False,
        "resource_effect_count": 0,
    }
    return Task083ResourceReservationDecisionV1(
        _with_digest(body, "decision_sha256", _DECISION_DOMAIN)
    )


def compile_production_reservation_admission(
    plan: Mapping[str, Any] | Task083ResourceReservationPlanV1,
    *,
    evaluated_at: str,
) -> Task083ProductionReservationAdmissionV1:
    """Return the current-source production boundary, which is always blocked.

    TASK-043 cannot yet create a VOICE_MODEL_TRAINING Product Job, TASK-066
    has not mapped ``audio.voice.local``, the Windows backend is outside this
    unit, and the compound H3 V2 lineage does not exist.  A self-consistent
    body-free binding cannot erase those source gaps.
    """

    parsed = _coerce_plan(plan)
    body = {
        "record_type": "Task083ProductionReservationAdmissionV1",
        "schema_version": 1,
        "canonical_owner_task": CANONICAL_OWNER_TASK,
        "plan_sha256": parsed["plan_sha256"],
        "decision": "BLOCKED",
        "reason_codes": [
            "COMPOUND_OPERATION_NOT_BOUND",
            "DURABLE_JOB_SOURCE_NOT_AVAILABLE",
            "H3_AUTHORIZATION_V2_NOT_PRESENT",
            "NATIVE_BACKEND_NOT_IMPLEMENTED",
            "TASK084_DESTINATION_PLAN_NOT_BOUND",
            "VOICE_TRAINING_WORKLOAD_NOT_MAPPED",
        ],
        "evaluated_at": evaluated_at,
        "fixture_only": True,
        "authority_created": False,
        "native_reservation_invoked": False,
        "training_dispatched": False,
        "production_eligible": False,
        "resource_effect_count": 0,
    }
    return Task083ProductionReservationAdmissionV1(
        _with_digest(body, "admission_sha256", _PRODUCTION_ADMISSION_DOMAIN)
    )


class Task083FixtureReservationLedger:
    """Sealed in-memory fault-test ledger; never a production capability."""

    __slots__ = (
        "_plan",
        "_reservation_id",
        "_state",
        "_events",
        "_requests",
        "_negative_acknowledgements",
        "_last_observed_at",
        "_lock",
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("Task083FixtureReservationLedger cannot be subclassed")

    def __init__(
        self,
        key: object,
        plan: Task083ResourceReservationPlanV1,
        reservation_id: str,
    ) -> None:
        if key is not _FACTORY_KEY or type(plan) is not Task083ResourceReservationPlanV1:
            raise TypeError("fixture ledger must be created by open_fixture_reservation")
        self._plan = plan
        self._reservation_id = _identifier(reservation_id, "reservation_id")
        self._state = ReservationState.PREPARED
        self._events: list[Task083FixtureExecutionResourceReservationReceiptV1] = []
        self._requests: dict[str, str] = {}
        self._negative_acknowledgements: dict[str, tuple[int, str]] = {}
        self._last_observed_at = _timestamp_value(plan.to_dict()["issued_at"])
        self._lock = RLock()

    def __reduce__(self) -> object:
        raise TypeError("fixture ledger is process-local and not serializable")

    @property
    def state(self) -> ReservationState:
        return self._state

    @property
    def resource_effect_count(self) -> int:
        return 0

    def _request_digest(self, action: str, payload: Mapping[str, Any]) -> str:
        return sha256_bytes(
            canonical_json_bytes(
                {"domain": "TASK-083-FIXTURE-REQUEST-V1", "action": action, **dict(payload)}
            )
        )

    def _duplicate(
        self, request_id: str, digest: str, *, read_back_at: str
    ) -> Task083FixtureResourceReservationReadbackV1 | None:
        previous = self._requests.get(request_id)
        if previous is None:
            return None
        if previous != digest:
            raise ValueError("request_id replay payload mismatch")
        candidate = _timestamp_value(read_back_at)
        monotonic_readback = max(candidate, self._last_observed_at)
        return self.readback(read_back_at=_timestamp_text(monotonic_readback))

    def _append(
        self,
        *,
        target: ReservationState,
        request_id: str,
        request_digest: str,
        observed_at: str,
        granted_resources: Mapping[str, Any],
        thermal_state: str,
        power_state: str,
        reasons: list[str],
        durable_negative_acknowledgement_sha256: str | None = None,
    ) -> Task083FixtureExecutionResourceReservationReceiptV1:
        if target not in _ALLOWED_TRANSITIONS[self._state]:
            raise ValueError(f"transition {self._state.value} -> {target.value} is forbidden")
        event_time = _timestamp_value(observed_at)
        if event_time < self._last_observed_at:
            event_time = self._last_observed_at
            reasons = [*reasons, "CLOCK_ROLLBACK"]
        observed_at = _timestamp_text(event_time)
        plan = self._plan.to_dict()
        previous = self._events[-1].to_dict()["receipt_sha256"] if self._events else None
        body = {
            "record_type": "Task083FixtureExecutionResourceReservationReceiptV1",
            "schema_version": 1,
            "canonical_owner_task": CANONICAL_OWNER_TASK,
            "receipt_role": RECEIPT_ROLE,
            "reservation_id": self._reservation_id,
            "request_id": request_id,
            "plan_sha256": plan["plan_sha256"],
            "h3_authorization_v2_sha256": None,
            "task084_destination_plan_sha256": None,
            "compound_operation_id": None,
            "compound_operation_sha256": None,
            "compound_stage": "FIXTURE_ONLY",
            **{field: plan[field] for field in _COMMON_BINDING_FIELDS},
            "state": target.value,
            "reservation_revision": len(self._events) + 1,
            "previous_receipt_sha256": previous,
            "durable_negative_acknowledgement_sha256": durable_negative_acknowledgement_sha256,
            "granted_resources": copy.deepcopy(dict(granted_resources)),
            "thermal_state": thermal_state,
            "power_state": power_state,
            "reason_codes": sorted(set(reasons)),
            "event_at": observed_at,
            "expires_at": plan["expires_at"],
            "fixture_only": True,
            "authority_created": False,
            "live_capability_restorable": False,
            "live_capability_present": False,
            "production_backend_invoked": False,
            "native_reservation_invoked": False,
            "training_dispatched": False,
            "training_started": False,
            "resource_effect_count": 0,
        }
        receipt = Task083FixtureExecutionResourceReservationReceiptV1(
            _with_digest(body, "receipt_sha256", _RECEIPT_DOMAIN)
        )
        self._events.append(receipt)
        self._requests[request_id] = request_digest
        self._state = target
        self._last_observed_at = _timestamp_value(observed_at)
        return receipt

    def reserve(
        self,
        *,
        request_id: str,
        observation: Mapping[str, Any] | Task083FixtureResourceObservationV1,
        evaluated_at: str,
    ) -> Task083FixtureExecutionResourceReservationReceiptV1 | Task083FixtureResourceReservationReadbackV1:
        with self._lock:
            observed = _coerce_observation(observation)
            decision = evaluate_fixture_reservation(self._plan, observed, evaluated_at=evaluated_at).to_dict()
            digest = self._request_digest(
                "RESERVE",
                {"observation_sha256": observed["observation_sha256"], "evaluated_at": evaluated_at},
            )
            duplicate = self._duplicate(
                _identifier(request_id, "request_id"), digest, read_back_at=evaluated_at
            )
            if duplicate is not None:
                return duplicate
            if self._state is not ReservationState.PREPARED:
                raise ValueError("reservation can be issued only from PREPARED")
            target = (
                ReservationState.RESERVED
                if decision["decision"] == FixtureDecision.READY_FIXTURE_ONLY.value
                else ReservationState.FAILED_CLOSED
            )
            return self._append(
                target=target,
                request_id=request_id,
                request_digest=digest,
                observed_at=evaluated_at,
                granted_resources=observed["granted_resources"],
                thermal_state=observed["thermal_state"],
                power_state=observed["power_state"],
                reasons=decision["reason_codes"],
            )

    def begin_fixture_consumption(
        self,
        *,
        request_id: str,
        expected_revision: int,
        expected_receipt_sha256: str,
        observation: Mapping[str, Any] | Task083FixtureResourceObservationV1,
        observed_at: str,
    ) -> Task083FixtureExecutionResourceReservationReceiptV1 | Task083FixtureResourceReservationReadbackV1:
        with self._lock:
            observed = _coerce_observation(observation)
            digest = self._request_digest(
                "BEGIN_CONSUMPTION",
                {
                    "expected_revision": expected_revision,
                    "expected_receipt_sha256": expected_receipt_sha256,
                    "observation_sha256": observed["observation_sha256"],
                    "observed_at": observed_at,
                },
            )
            duplicate = self._duplicate(
                _identifier(request_id, "request_id"), digest, read_back_at=observed_at
            )
            if duplicate is not None:
                return duplicate
            if self._state is not ReservationState.RESERVED or not self._events:
                raise ValueError("consumption requires RESERVED state")
            head = self._events[-1].to_dict()
            if expected_revision != head["reservation_revision"] or expected_receipt_sha256 != head["receipt_sha256"]:
                raise ValueError("reservation CAS head mismatch")
            decision = evaluate_fixture_reservation(self._plan, observed, evaluated_at=observed_at).to_dict()
            if _timestamp_value(observed_at) < self._last_observed_at:
                decision["reason_codes"] = sorted(set(decision["reason_codes"]) | {"CLOCK_ROLLBACK"})
                decision["decision"] = FixtureDecision.BLOCKED.value
            if decision["decision"] != FixtureDecision.READY_FIXTURE_ONLY.value:
                return self._append(
                    target=ReservationState.FAILED_CLOSED,
                    request_id=request_id,
                    request_digest=digest,
                    observed_at=observed_at,
                    granted_resources=observed["granted_resources"],
                    thermal_state=observed["thermal_state"],
                    power_state=observed["power_state"],
                    reasons=decision["reason_codes"],
                )
            return self._append(
                target=ReservationState.CONSUMPTION_STARTED,
                request_id=request_id,
                request_digest=digest,
                observed_at=observed_at,
                granted_resources=observed["granted_resources"],
                thermal_state=observed["thermal_state"],
                power_state=observed["power_state"],
                reasons=["FIXTURE_BURN_ONLY", "H3_V2_NOT_PRESENT", "TRAINING_DISPATCH_BLOCKED"],
            )

    def issue_fixture_durable_negative_acknowledgement(
        self,
        *,
        acknowledgement_id: str,
        expected_revision: int,
        expected_receipt_sha256: str,
        observed_at: str,
    ) -> Task083FixtureDurableNegativeAcknowledgementV1:
        with self._lock:
            if self._state is not ReservationState.CONSUMPTION_STARTED or not self._events:
                raise ValueError("negative acknowledgement requires CONSUMPTION_STARTED state")
            head = self._events[-1].to_dict()
            if (
                expected_revision != head["reservation_revision"]
                or expected_receipt_sha256 != head["receipt_sha256"]
            ):
                raise ValueError("negative acknowledgement CAS head mismatch")
            if _timestamp_value(observed_at) < self._last_observed_at:
                raise ValueError("negative acknowledgement clock rollback")
            plan = self._plan.to_dict()
            body = {
                "record_type": "Task083FixtureDurableNegativeAcknowledgementV1",
                "schema_version": 1,
                "canonical_owner_task": CANONICAL_OWNER_TASK,
                "reservation_id": self._reservation_id,
                "acknowledgement_id": acknowledgement_id,
                "plan_sha256": plan["plan_sha256"],
                "job_revision_sha256": plan["job_revision_sha256"],
                "consumption_started_revision": head["reservation_revision"],
                "consumption_started_receipt_sha256": head["receipt_sha256"],
                "process_not_started": True,
                "job_head_unchanged": True,
                "live_lease_released": True,
                "observed_at": observed_at,
                "fixture_only": True,
                "production_backend_invoked": False,
                "training_started": False,
                "resource_effect_count": 0,
            }
            acknowledgement = Task083FixtureDurableNegativeAcknowledgementV1(
                _with_digest(body, "acknowledgement_sha256", _NEGATIVE_ACK_DOMAIN)
            )
            self._negative_acknowledgements[
                acknowledgement.to_dict()["acknowledgement_sha256"]
            ] = (head["reservation_revision"], head["receipt_sha256"])
            return acknowledgement

    def finish_fixture_consumption(
        self,
        *,
        request_id: str,
        expected_revision: int,
        expected_receipt_sha256: str,
        acknowledged: bool | None,
        observed_at: str,
        negative_acknowledgement: (
            Task083FixtureDurableNegativeAcknowledgementV1 | None
        ) = None,
    ) -> Task083FixtureExecutionResourceReservationReceiptV1 | Task083FixtureResourceReservationReadbackV1:
        with self._lock:
            if type(acknowledged) not in {bool, type(None)}:
                raise ValueError("acknowledged must be true, false, or null")
            if negative_acknowledgement is not None and type(
                negative_acknowledgement
            ) is not Task083FixtureDurableNegativeAcknowledgementV1:
                raise ValueError("negative acknowledgement must be issued by this fixture ledger")
            negative_ack = (
                None if negative_acknowledgement is None else negative_acknowledgement.to_dict()
            )
            if acknowledged is not False and negative_ack is not None:
                raise ValueError("negative acknowledgement is valid only for an exact negative reply")
            digest = self._request_digest(
                "FINISH_CONSUMPTION",
                {
                    "expected_revision": expected_revision,
                    "expected_receipt_sha256": expected_receipt_sha256,
                    "acknowledged": acknowledged,
                    "observed_at": observed_at,
                    "negative_acknowledgement_sha256": (
                        None if negative_ack is None else negative_ack["acknowledgement_sha256"]
                    ),
                },
            )
            duplicate = self._duplicate(
                _identifier(request_id, "request_id"), digest, read_back_at=observed_at
            )
            if duplicate is not None:
                return duplicate
            if self._state is not ReservationState.CONSUMPTION_STARTED or not self._events:
                raise ValueError("finish requires CONSUMPTION_STARTED state")
            head = self._events[-1].to_dict()
            if expected_revision != head["reservation_revision"] or expected_receipt_sha256 != head["receipt_sha256"]:
                raise ValueError("reservation CAS head mismatch")
            rollback = _timestamp_value(observed_at) < self._last_observed_at
            if acknowledged is True and not rollback:
                target = ReservationState.CONSUMED
                reasons = ["EXACT_FIXTURE_ACKNOWLEDGEMENT"]
            elif acknowledged is False and negative_ack is not None and not rollback:
                plan = self._plan.to_dict()
                if (
                    negative_ack["reservation_id"] != self._reservation_id
                    or negative_ack["plan_sha256"] != plan["plan_sha256"]
                    or negative_ack["job_revision_sha256"] != plan["job_revision_sha256"]
                    or _timestamp_value(negative_ack["observed_at"]) > _timestamp_value(observed_at)
                    or _timestamp_value(negative_ack["observed_at"]) < self._last_observed_at
                    or negative_ack["consumption_started_revision"] != head["reservation_revision"]
                    or negative_ack["consumption_started_receipt_sha256"] != head["receipt_sha256"]
                    or self._negative_acknowledgements.get(
                        negative_ack["acknowledgement_sha256"]
                    )
                    != (head["reservation_revision"], head["receipt_sha256"])
                ):
                    raise ValueError("durable negative acknowledgement binding/currentness mismatch")
                target = ReservationState.FAILED_CLOSED
                reasons = [
                    "DURABLE_NEGATIVE_ACKNOWLEDGEMENT",
                    "JOB_HEAD_UNCHANGED",
                    "LIVE_LEASE_RELEASED",
                    "PROCESS_NOT_STARTED",
                ]
            else:
                target = ReservationState.CONSUMPTION_UNKNOWN
                reasons = [
                    "AMBIGUOUS_AFTER_BURN",
                    *(
                        ["DURABLE_NEGATIVE_ACKNOWLEDGEMENT_MISSING"]
                        if acknowledged is False and negative_ack is None
                        else []
                    ),
                    *(["CLOCK_ROLLBACK"] if rollback else []),
                ]
            receipt = self._append(
                target=target,
                request_id=request_id,
                request_digest=digest,
                observed_at=observed_at,
                granted_resources=head["granted_resources"],
                thermal_state=head["thermal_state"],
                power_state=head["power_state"],
                reasons=reasons,
                durable_negative_acknowledgement_sha256=(
                    negative_ack["acknowledgement_sha256"]
                    if target is ReservationState.FAILED_CLOSED and negative_ack is not None
                    else None
                ),
            )
            if target is ReservationState.FAILED_CLOSED and negative_ack is not None:
                del self._negative_acknowledgements[negative_ack["acknowledgement_sha256"]]
            return receipt

    def expire(
        self, *, request_id: str, observed_at: str
    ) -> Task083FixtureExecutionResourceReservationReceiptV1 | Task083FixtureResourceReservationReadbackV1:
        with self._lock:
            digest = self._request_digest("EXPIRE", {"observed_at": observed_at})
            duplicate = self._duplicate(
                _identifier(request_id, "request_id"), digest, read_back_at=observed_at
            )
            if duplicate is not None:
                return duplicate
            if self._state not in {ReservationState.PREPARED, ReservationState.RESERVED}:
                raise ValueError("terminal or post-burn expiry transition is forbidden")
            if _timestamp_value(observed_at) < _timestamp_value(self._plan.to_dict()["expires_at"]):
                raise ValueError("reservation has not expired")
            head = self._events[-1].to_dict() if self._events else None
            resources = head["granted_resources"] if head else self._plan.to_dict()["resource_floor"]
            return self._append(
                target=ReservationState.EXPIRED,
                request_id=request_id,
                request_digest=digest,
                observed_at=observed_at,
                granted_resources=resources,
                thermal_state=head["thermal_state"] if head else "UNKNOWN",
                power_state=head["power_state"] if head else "UNKNOWN",
                reasons=["RESERVATION_EXPIRED"],
            )

    def restart_readback(
        self,
        *,
        request_id: str,
        live_capability_present: bool,
        observed_at: str,
    ) -> Task083FixtureExecutionResourceReservationReceiptV1 | Task083FixtureResourceReservationReadbackV1:
        with self._lock:
            _boolean(live_capability_present, "live_capability_present")
            digest = self._request_digest(
                "RESTART_READBACK",
                {"live_capability_present": live_capability_present, "observed_at": observed_at},
            )
            duplicate = self._duplicate(
                _identifier(request_id, "request_id"), digest, read_back_at=observed_at
            )
            if duplicate is not None:
                return duplicate
            if self._state is ReservationState.RESERVED and not live_capability_present:
                head = self._events[-1].to_dict()
                return self._append(
                    target=ReservationState.FAILED_CLOSED,
                    request_id=request_id,
                    request_digest=digest,
                    observed_at=observed_at,
                    granted_resources=head["granted_resources"],
                    thermal_state=head["thermal_state"],
                    power_state=head["power_state"],
                    reasons=["LIVE_CAPABILITY_MISSING_AFTER_RESTART"],
                )
            if self._state is ReservationState.CONSUMPTION_STARTED:
                head = self._events[-1].to_dict()
                return self._append(
                    target=ReservationState.CONSUMPTION_UNKNOWN,
                    request_id=request_id,
                    request_digest=digest,
                    observed_at=observed_at,
                    granted_resources=head["granted_resources"],
                    thermal_state=head["thermal_state"],
                    power_state=head["power_state"],
                    reasons=["RESTART_AFTER_BURN"],
                )
            readback = self.readback(read_back_at=observed_at)
            self._requests[request_id] = digest
            return readback

    def readback(self, *, read_back_at: str) -> Task083FixtureResourceReservationReadbackV1:
        with self._lock:
            if _timestamp_value(read_back_at) < self._last_observed_at:
                raise ValueError("readback clock rollback")
            plan = self._plan.to_dict()
            head = self._events[-1].to_dict() if self._events else None
            body = {
                "record_type": "Task083FixtureResourceReservationReadbackV1",
                "schema_version": 1,
                "canonical_owner_task": CANONICAL_OWNER_TASK,
                "receipt_role": RECEIPT_ROLE,
                "reservation_id": self._reservation_id,
                "plan_sha256": plan["plan_sha256"],
                "h3_authorization_v2_sha256": None,
                "task084_destination_plan_sha256": None,
                "compound_operation_id": None,
                "compound_operation_sha256": None,
                "compound_stage": "FIXTURE_ONLY",
                **{field: plan[field] for field in _COMMON_BINDING_FIELDS},
                "state": self._state.value,
                "reservation_revision": len(self._events),
                "head_receipt_sha256": None if head is None else head["receipt_sha256"],
                "event_count": len(self._events),
                "read_back_at": read_back_at,
                "fixture_only": True,
                "authority_created": False,
                # A serialized fixture readback never exports a live capability.
                "live_capability_present": False,
                "live_capability_restorable": False,
                "production_backend_invoked": False,
                "training_dispatched": False,
                "training_started": False,
                "resource_effect_count": 0,
            }
            return Task083FixtureResourceReservationReadbackV1(
                _with_digest(body, "readback_sha256", _READBACK_DOMAIN)
            )


def open_fixture_reservation(
    plan: Mapping[str, Any] | Task083ResourceReservationPlanV1,
    *,
    reservation_id: str,
) -> Task083FixtureReservationLedger:
    parsed = Task083ResourceReservationPlanV1(_coerce_plan(plan))
    return Task083FixtureReservationLedger(_FACTORY_KEY, parsed, reservation_id)


def project_legacy_execution_resource_reservation_binding(
    receipt: Mapping[str, Any] | Task083FixtureExecutionResourceReservationReceiptV1,
    *,
    receipt_ref: str,
) -> dict[str, Any]:
    """Project only the current TASK-046 legacy fields, never authority."""

    if type(receipt) is Task083FixtureExecutionResourceReservationReceiptV1:
        parsed = receipt.to_dict()
    elif isinstance(receipt, Mapping):
        parsed = Task083FixtureExecutionResourceReservationReceiptV1.from_dict(receipt).to_dict()
    else:
        raise ValueError("receipt must be a canonical TASK-083 receipt")
    _identifier(receipt_ref, "receipt_ref")
    body = {
        "record_type": "ExecutionResourceReservationBinding",
        "contract_state": "UNKNOWN",
        "reservation_id": None,
        "receipt_ref": receipt_ref,
        "receipt_sha256": parsed["receipt_sha256"],
        "gpu_ref": None,
        "cpu_units": None,
        "ram_bytes": None,
        "vram_bytes": None,
        "disk_bytes": None,
        "thermal_state": "UNKNOWN",
        "power_state": "UNKNOWN",
        "admission_state": "UNKNOWN",
        "issued_at": None,
        "expires_at": None,
    }
    body["binding_sha256"] = sha256_bytes(canonical_json_bytes(body))
    # Validate against the actual TASK-046 closed legacy consumer contract.
    return ExecutionResourceReservationBinding.from_dict(body).to_dict()
