"""Pure TASK-098 runtime-transcription control records and reducer.

This module performs no store, filesystem, thread, Provider, model, network,
UI, native, or private-media effect.  It validates immutable facts and derives
one body-free phase-only public projection.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
from importlib import resources
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, ClassVar, Mapping

from jsonschema import Draft202012Validator

from .ids import IdKind, validate_id, validate_project_id
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_NAME = "task098-runtime-transcription-control.schema.json"
CONTRACT_VERSION = "1.0.0"

CANCEL_REQUEST_DOMAIN = b"bvp.task098.runtime-transcription-cancel-request.v1\0"
CANCEL_OUTCOME_DOMAIN = b"bvp.task098.runtime-transcription-cancel-outcome.v1\0"
ADJUDICATION_DOMAIN = b"bvp.task098.runtime-transcription-adjudication.v1\0"
BARRIER_DOMAIN = b"bvp.task098.runtime-transcription-commit-barrier.v1\0"
ABSENCE_DOMAIN = b"bvp.task098.runtime-transcription-generation-absence.v1\0"
TERMINAL_COMMIT_DOMAIN = b"bvp.task098.runtime-transcription-terminal-commit.v1\0"
GUARD_DOMAIN = b"bvp.task098.task036-cross-version-guard.v1\0"

PHASES = frozenset({
    "NOT_STARTED", "ADMISSION", "PROVIDER_STARTING", "PROVIDER_RUNNING",
    "PUBLICATION_VALIDATING", "PUBLICATION_COMMITTING", "COMPLETED",
    "UNKNOWN_AFTER_DISCONNECT", "BLOCKED",
})
CANCEL_STATES = frozenset({
    "NOT_REQUESTED", "CANCEL_REQUESTED", "CANCELLED_BEFORE_PROVIDER_EFFECT",
    "CANCELLED_AFTER_COOPERATIVE_BOUNDARY", "STOP_NOT_CONFIRMED",
})
ADJUDICATION_STATES = frozenset({"NOT_REQUIRED", "REQUIRED", "CLOSED_FAILED_NO_REPLAY"})
ACTIONS = frozenset({"NONE", "REQUEST_CANCEL", "CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY"})
RECOVERY_STATES = frozenset({
    "PENDING_ADMISSION", "ACTIVE_UNKNOWN", "RECOVERABLE_PUBLICATION",
    "VERIFICATION_ONLY", "ADJUDICATION_REQUIRED_NO_PUBLICATION",
    "FAILED_TERMINAL", "CORRUPT_BLOCKED",
})
OPERATION_STATUSES = frozenset({"PENDING", "IN_PROGRESS", "PARTIAL", "COMPLETED", "FAILED"})

_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_ADMISSION = re.compile(r"task098-runtime-admission:v2:([0-9a-f]{64}):([0-9a-f]{64})")
_OWNER = re.compile(r"task098-runtime-owner:v2:([0-9a-f]{64})")


def _strict_bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise ValueError(f"{name} must be sha256:<64 lowercase hex>")
    return validate_sha256(value, field_name=name)


def _timestamp(value: Any, name: str) -> str:
    if not isinstance(value, str) or _TIME.fullmatch(value) is None:
        raise ValueError(f"{name} must be a second-precision UTC timestamp")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid UTC timestamp") from exc
    return value


def _operation_id(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an operation identifier")
    return validate_id(value, IdKind.OPERATION)


def _asset_id(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("source_asset_id must be an Asset identifier")
    return validate_id(value, IdKind.ASSET)


def _job_id(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("production_job_id must be a Job identifier")
    return validate_id(value, IdKind.JOB)


def _attempt(value: Any) -> int:
    if type(value) is not int or value < 1:
        raise ValueError("expected_attempt must be an integer of at least one")
    return value


def _admission(value: Any, *, source_sha256: str, decision_sha256: str) -> str:
    if not isinstance(value, str):
        raise ValueError("runtime_admission_ref is invalid")
    match = _ADMISSION.fullmatch(value)
    if match is None or match.group(1) != source_sha256.removeprefix("sha256:") or match.group(2) != decision_sha256.removeprefix("sha256:"):
        raise ValueError("runtime_admission_ref does not bind the supplied coordinates")
    return value


def _record_digest(value: Mapping[str, Any], domain: bytes) -> str:
    return sha256_bytes(domain + canonical_json_bytes({key: item for key, item in value.items() if key != "record_sha256"}))


def _schema(definition: str, value: Mapping[str, Any]) -> None:
    try:
        with resources.files("ai_video_production.schema_resources").joinpath(SCHEMA_NAME).open("r", encoding="utf-8") as source:
            document = json.load(source)
        validator = Draft202012Validator({"$schema": document["$schema"], "$defs": document["$defs"], "$ref": f"#/$defs/{definition}"})
        error = next(validator.iter_errors(dict(value)), None)
        if error is not None:
            raise ValueError(error.message)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("runtime transcription control schema validation failed") from exc


class _ImmutableRecord:
    __slots__ = ("_values",)
    FIELDS: ClassVar[tuple[str, ...]]
    DEFINITION: ClassVar[str]
    DOMAIN: ClassVar[bytes]

    def __init__(self, values: Mapping[str, Any]) -> None:
        if not isinstance(values, Mapping) or set(values) != set(self.FIELDS):
            raise ValueError(f"{type(self).__name__} fields are incomplete or unknown")
        _schema(self.DEFINITION, values)
        normalized = self._validate(dict(values))
        observed = _digest(normalized["record_sha256"], "record_sha256")
        if observed != _record_digest(normalized, self.DOMAIN):
            raise ValueError(f"{type(self).__name__} digest mismatch")
        object.__setattr__(self, "_values", MappingProxyType(normalized))

    def __getattr__(self, name: str) -> Any:
        try:
            return self._values[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable")

    @classmethod
    def _create(cls, body: Mapping[str, Any]) -> Any:
        values = dict(body)
        values["record_sha256"] = _record_digest(values, cls.DOMAIN)
        return cls(values)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Any:
        return cls(value)

    def to_dict(self) -> dict[str, Any]:
        return {key: self._values[key] for key in self.FIELDS}

    def __reduce__(self) -> tuple[type["_ImmutableRecord"], tuple[dict[str, Any]]]:
        """Rebuild through the validating constructor under Windows spawn."""

        return type(self), (self.to_dict(),)

    def _validate(self, values: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


def _common(values: dict[str, Any], *, prior: bool = False) -> None:
    if values["contract_version"] != CONTRACT_VERSION:
        raise ValueError("contract_version is invalid")
    _operation_id(values["runtime_operation_id"], "runtime_operation_id")
    _operation_id(values["slot_operation_id"], "slot_operation_id")
    source = _digest(values["source_asset_sha256"], "source_asset_sha256")
    admission_name = "prior_runtime_admission_ref" if prior else "runtime_admission_ref"
    admission = values[admission_name]
    if not isinstance(admission, str):
        raise ValueError(f"{admission_name} is invalid")
    match = _ADMISSION.fullmatch(admission)
    if match is None or match.group(1) != source.removeprefix("sha256:"):
        raise ValueError(f"{admission_name} does not bind the source")
    if "runtime_decision_sha256" in values:
        decision = _digest(values["runtime_decision_sha256"], "runtime_decision_sha256")
        if match.group(2) != decision.removeprefix("sha256:"):
            raise ValueError(f"{admission_name} does not bind the decision")
    if "runtime_request_sha256" in values:
        _digest(values["runtime_request_sha256"], "runtime_request_sha256")
    _attempt(values["expected_attempt"])


class RuntimeTranscriptionCancelRequestV1(_ImmutableRecord):
    FIELDS = ("contract_version", "cancel_request_id", "runtime_operation_id", "slot_operation_id", "source_asset_sha256", "runtime_admission_ref", "runtime_request_sha256", "runtime_decision_sha256", "expected_attempt", "requested_at", "no_replay", "record_sha256")
    DEFINITION = "cancel_request"
    DOMAIN = CANCEL_REQUEST_DOMAIN

    @classmethod
    def create(cls, **values: Any) -> "RuntimeTranscriptionCancelRequestV1":
        return cls._create({"contract_version": CONTRACT_VERSION, "no_replay": True, **values})

    def _validate(self, values: dict[str, Any]) -> dict[str, Any]:
        _common(values)
        _operation_id(values["cancel_request_id"], "cancel_request_id")
        _timestamp(values["requested_at"], "requested_at")
        if _strict_bool(values["no_replay"], "no_replay") is not True:
            raise ValueError("no_replay must be true")
        return values


class RuntimeTranscriptionCancelOutcomeV1(_ImmutableRecord):
    FIELDS = ("contract_version", "cancel_request_sha256", "runtime_operation_id", "slot_operation_id", "source_asset_sha256", "runtime_admission_ref", "runtime_request_sha256", "runtime_decision_sha256", "expected_attempt", "outcome", "provider_execution_started", "provider_stop_confirmed", "stop_evidence", "acknowledged_at", "no_replay", "record_sha256")
    DEFINITION = "cancel_outcome"
    DOMAIN = CANCEL_OUTCOME_DOMAIN
    MATRIX = {
        "CANCELLED_BEFORE_PROVIDER_EFFECT": (False, True, "PRE_PROVIDER"),
        "CANCELLED_AFTER_COOPERATIVE_BOUNDARY": (True, True, "COOPERATIVE_CHECKPOINT"),
    }

    @classmethod
    def create(cls, **values: Any) -> "RuntimeTranscriptionCancelOutcomeV1":
        return cls._create({"contract_version": CONTRACT_VERSION, "no_replay": True, **values})

    def _validate(self, values: dict[str, Any]) -> dict[str, Any]:
        _common(values)
        _digest(values["cancel_request_sha256"], "cancel_request_sha256")
        started = _strict_bool(values["provider_execution_started"], "provider_execution_started")
        stopped = _strict_bool(values["provider_stop_confirmed"], "provider_stop_confirmed")
        outcome = values["outcome"]
        if outcome == "STOP_NOT_CONFIRMED":
            if stopped or values["stop_evidence"] != "NONE":
                raise ValueError("STOP_NOT_CONFIRMED cannot claim stop evidence")
        elif outcome not in self.MATRIX or (started, stopped, values["stop_evidence"]) != self.MATRIX[outcome]:
            raise ValueError("cancel outcome is outside the closed matrix")
        _timestamp(values["acknowledged_at"], "acknowledged_at")
        if _strict_bool(values["no_replay"], "no_replay") is not True:
            raise ValueError("no_replay must be true")
        return values


class RuntimeTranscriptionAdjudicationDecisionV1(_ImmutableRecord):
    FIELDS = ("contract_version", "adjudication_id", "runtime_operation_id", "slot_operation_id", "source_asset_sha256", "runtime_admission_ref", "runtime_request_sha256", "runtime_decision_sha256", "expected_attempt", "decision", "provider_stop_attested", "stop_evidence", "decided_at", "no_replay", "record_sha256")
    DEFINITION = "adjudication_decision"
    DOMAIN = ADJUDICATION_DOMAIN

    @classmethod
    def create(cls, **values: Any) -> "RuntimeTranscriptionAdjudicationDecisionV1":
        return cls._create({"contract_version": CONTRACT_VERSION, "decision": "CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY", "provider_stop_attested": True, "stop_evidence": "HUMAN_ATTESTATION", "no_replay": True, **values})

    def _validate(self, values: dict[str, Any]) -> dict[str, Any]:
        _common(values)
        _operation_id(values["adjudication_id"], "adjudication_id")
        if values["decision"] != "CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY" or _strict_bool(values["provider_stop_attested"], "provider_stop_attested") is not True or values["stop_evidence"] != "HUMAN_ATTESTATION":
            raise ValueError("adjudication decision is outside the closed contract")
        _timestamp(values["decided_at"], "decided_at")
        if _strict_bool(values["no_replay"], "no_replay") is not True:
            raise ValueError("no_replay must be true")
        return values


class RuntimeTranscriptionCommitBarrierV1(_ImmutableRecord):
    FIELDS = ("contract_version", "runtime_operation_id", "slot_operation_id", "source_asset_sha256", "runtime_admission_ref", "expected_attempt", "barrier_owner", "closure_record_sha256", "acquired_at", "record_sha256")
    DEFINITION = "commit_barrier"
    DOMAIN = BARRIER_DOMAIN

    @classmethod
    def create(cls, **values: Any) -> "RuntimeTranscriptionCommitBarrierV1":
        return cls._create({"contract_version": CONTRACT_VERSION, **values})

    def _validate(self, values: dict[str, Any]) -> dict[str, Any]:
        _common(values)
        owner = values["barrier_owner"]
        closure = values["closure_record_sha256"]
        if owner == "PUBLICATION":
            if closure is not None:
                raise ValueError("publication barrier cannot bind a closure")
        elif owner == "TERMINAL_CLOSURE":
            _digest(closure, "closure_record_sha256")
        else:
            raise ValueError("barrier_owner is invalid")
        _timestamp(values["acquired_at"], "acquired_at")
        return values


class RuntimeTranscriptionGenerationAbsenceObservationV1(_ImmutableRecord):
    FIELDS = ("contract_version", "runtime_operation_id", "slot_operation_id", "source_asset_sha256", "runtime_admission_ref", "expected_attempt", "commit_barrier_sha256", "observation", "observed_at", "record_sha256")
    DEFINITION = "generation_absence"
    DOMAIN = ABSENCE_DOMAIN

    @classmethod
    def create(cls, **values: Any) -> "RuntimeTranscriptionGenerationAbsenceObservationV1":
        return cls._create({"contract_version": CONTRACT_VERSION, **values})

    def _validate(self, values: dict[str, Any]) -> dict[str, Any]:
        _common(values)
        _digest(values["commit_barrier_sha256"], "commit_barrier_sha256")
        if values["observation"] not in {"EXACT_GENERATION_ABSENT", "PRESENT_PARTIAL_OR_UNKNOWN"}:
            raise ValueError("generation observation is invalid")
        _timestamp(values["observed_at"], "observed_at")
        return values


class RuntimeTranscriptionTerminalClosureCommitV1(_ImmutableRecord):
    FIELDS = ("contract_version", "runtime_operation_id", "slot_operation_id", "source_asset_sha256", "prior_runtime_admission_ref", "expected_attempt", "closure_kind", "closure_record_sha256", "commit_barrier_sha256", "generation_absence_observation_sha256", "terminal_status", "terminal_result_ref", "operation_cas_committed", "slot_owner_verified", "committed_at", "no_replay", "record_sha256")
    DEFINITION = "terminal_commit"
    DOMAIN = TERMINAL_COMMIT_DOMAIN

    @classmethod
    def create(cls, **values: Any) -> "RuntimeTranscriptionTerminalClosureCommitV1":
        return cls._create({"contract_version": CONTRACT_VERSION, "terminal_status": "FAILED", "operation_cas_committed": True, "slot_owner_verified": True, "no_replay": True, **values})

    def _validate(self, values: dict[str, Any]) -> dict[str, Any]:
        _common(values, prior=True)
        closure_sha = _digest(values["closure_record_sha256"], "closure_record_sha256")
        _digest(values["commit_barrier_sha256"], "commit_barrier_sha256")
        _digest(values["generation_absence_observation_sha256"], "generation_absence_observation_sha256")
        if values["closure_kind"] == "CONFIRMED_CANCEL":
            expected = "task098-runtime-cancelled:v1:" + closure_sha.removeprefix("sha256:")
        elif values["closure_kind"] == "HUMAN_ADJUDICATED_FAILED":
            expected = "task098-runtime-adjudicated-failed:v1:" + closure_sha.removeprefix("sha256:")
        else:
            raise ValueError("closure_kind is invalid")
        if values["terminal_status"] != "FAILED" or values["terminal_result_ref"] != expected:
            raise ValueError("terminal closure identity is invalid")
        for name in ("operation_cas_committed", "slot_owner_verified", "no_replay"):
            if _strict_bool(values[name], name) is not True:
                raise ValueError(f"{name} must be true")
        _timestamp(values["committed_at"], "committed_at")
        return values


@dataclass(frozen=True, slots=True)
class RuntimeTranscriptionLeaseFactV1:
    production_job_id: str
    project_id: str
    source_asset_id: str
    source_asset_sha256: str
    operation_id: str
    command_type: str
    idempotency_key: str
    status: str
    attempt: int
    result_ref: str | None

    def __post_init__(self) -> None:
        _job_id(self.production_job_id)
        validate_project_id(self.project_id)
        _asset_id(self.source_asset_id)
        _digest(self.source_asset_sha256, "source_asset_sha256")
        _operation_id(self.operation_id, "operation_id")
        if not all(isinstance(value, str) for value in (self.command_type, self.idempotency_key, self.status)):
            raise ValueError("lease fact text fields are invalid")
        if type(self.attempt) is not int or self.attempt < 0:
            raise ValueError("lease attempt is invalid")
        if self.result_ref is not None and not isinstance(self.result_ref, str):
            raise ValueError("lease result_ref is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RuntimeTranscriptionLeaseFactV1":
        fields = tuple(cls.__dataclass_fields__)
        if not isinstance(value, Mapping) or set(value) != set(fields):
            raise ValueError("RuntimeTranscriptionLeaseFactV1 fields are incomplete or unknown")
        _schema("lease_fact", value)
        return cls(**{name: value[name] for name in fields})


@dataclass(frozen=True, slots=True)
class RuntimeTranscriptionReducerFactsV1:
    production_job_id: str
    project_id: str
    source_asset_id: str
    source_asset_sha256: str
    runtime_operation_id: str | None = None
    operation_status: str | None = None
    operation_attempt: int | None = None
    operation_result_ref: str | None = None
    slot_operation_id: str | None = None
    slot_status: str | None = None
    slot_result_ref: str | None = None
    recovery_state: str = "PENDING_ADMISSION"
    phase: str | None = None
    lease: RuntimeTranscriptionLeaseFactV1 | None = None
    cancel_request: RuntimeTranscriptionCancelRequestV1 | None = None
    cancel_outcome: RuntimeTranscriptionCancelOutcomeV1 | None = None
    adjudication: RuntimeTranscriptionAdjudicationDecisionV1 | None = None
    barrier: RuntimeTranscriptionCommitBarrierV1 | None = None
    generation_observation: RuntimeTranscriptionGenerationAbsenceObservationV1 | None = None
    terminal_commit: RuntimeTranscriptionTerminalClosureCommitV1 | None = None

    def __post_init__(self) -> None:
        _job_id(self.production_job_id)
        validate_project_id(self.project_id)
        _asset_id(self.source_asset_id)
        _digest(self.source_asset_sha256, "source_asset_sha256")
        operation_values = (self.runtime_operation_id, self.operation_status, self.operation_attempt)
        if any(value is not None for value in operation_values):
            if any(value is None for value in operation_values):
                raise ValueError("operation facts must be supplied together")
            _operation_id(self.runtime_operation_id, "runtime_operation_id")
            if self.operation_status not in OPERATION_STATUSES or type(self.operation_attempt) is not int or self.operation_attempt < 0:
                raise ValueError("operation facts are invalid")
        elif self.operation_result_ref is not None:
            raise ValueError("operation_result_ref requires an operation")
        slot_values = (self.slot_operation_id, self.slot_status, self.slot_result_ref)
        if any(value is not None for value in slot_values):
            if self.slot_operation_id is None or self.slot_status is None:
                raise ValueError("slot facts are incomplete")
            _operation_id(self.slot_operation_id, "slot_operation_id")
            if self.slot_status not in OPERATION_STATUSES:
                raise ValueError("slot status is invalid")
        if self.recovery_state not in RECOVERY_STATES:
            raise ValueError("recovery_state is invalid")
        if self.phase is not None and self.phase not in PHASES:
            raise ValueError("phase is invalid")


def _guard_key(facts: RuntimeTranscriptionReducerFactsV1) -> str:
    body = {
        "coordination_version": "1.0.0",
        "project_id": facts.project_id,
        "source_asset_id": facts.source_asset_id,
        "source_asset_sha256": facts.source_asset_sha256,
    }
    digest = hashlib.sha256(GUARD_DOMAIN + canonical_json_bytes(body)).hexdigest()
    return "task036-transcription-cross-version-" + digest


def _valid_lease(facts: RuntimeTranscriptionReducerFactsV1) -> bool:
    lease = facts.lease
    if lease is None:
        return False
    key = _guard_key(facts)
    digest = key.rsplit("-", 1)[-1]
    return (
        lease.production_job_id == facts.production_job_id
        and lease.project_id == facts.project_id
        and lease.source_asset_id == facts.source_asset_id
        and lease.source_asset_sha256 == facts.source_asset_sha256
        and lease.command_type == "task036.local_transcription.cross_version_guard.v1"
        and lease.idempotency_key == key
        and lease.status == "IN_PROGRESS"
        and lease.attempt == 0
        and lease.result_ref == "task098-runtime-owner:v2:" + digest
        and _OWNER.fullmatch(lease.result_ref or "") is not None
    )


def _projection(*, phase: str, cancel: str, adjudication: str, action: str, label: str,
                started: bool, known: bool, stopped: bool, evidence: str,
                release: bool) -> dict[str, Any]:
    if phase not in PHASES or cancel not in CANCEL_STATES or adjudication not in ADJUDICATION_STATES or action not in ACTIONS:
        raise AssertionError("internal control projection is outside closed enums")
    return {
        "control_mode": "PHASE_ONLY_V1",
        "phase": phase,
        "cancel_state": cancel,
        "adjudication_state": adjudication,
        "available_action": action,
        "status_label": label,
        "provider_execution_started": started,
        "provider_execution_known": known,
        "provider_stop_confirmed": stopped,
        "stop_evidence": evidence,
        "slot_release_allowed": release,
        "no_replay": True,
    }


def _blocked(*, adjudication: str = "NOT_REQUIRED", label: str = "状態が不正なため操作できません") -> dict[str, Any]:
    return _projection(phase="BLOCKED", cancel="STOP_NOT_CONFIRMED", adjudication=adjudication,
                       action="NONE", label=label, started=False, known=False,
                       stopped=False, evidence="NONE", release=False)


def _record_binds(record: Any, facts: RuntimeTranscriptionReducerFactsV1) -> bool:
    return (
        record.runtime_operation_id == facts.runtime_operation_id
        and record.slot_operation_id == facts.slot_operation_id
        and record.source_asset_sha256 == facts.source_asset_sha256
        and record.expected_attempt == facts.operation_attempt
    )


def reduce_runtime_transcription_control(facts: RuntimeTranscriptionReducerFactsV1) -> dict[str, Any]:
    """Reduce exact durable/observed facts to the closed public projection."""

    if type(facts) is not RuntimeTranscriptionReducerFactsV1:
        raise TypeError("facts must be RuntimeTranscriptionReducerFactsV1")
    records = (facts.cancel_request, facts.cancel_outcome, facts.adjudication,
               facts.barrier, facts.generation_observation, facts.terminal_commit)
    record_types = (
        RuntimeTranscriptionCancelRequestV1,
        RuntimeTranscriptionCancelOutcomeV1,
        RuntimeTranscriptionAdjudicationDecisionV1,
        RuntimeTranscriptionCommitBarrierV1,
        RuntimeTranscriptionGenerationAbsenceObservationV1,
        RuntimeTranscriptionTerminalClosureCommitV1,
    )
    if facts.lease is not None and type(facts.lease) is not RuntimeTranscriptionLeaseFactV1:
        return _blocked()
    if any(record is not None and type(record) is not expected for record, expected in zip(records, record_types)):
        return _blocked()
    if facts.runtime_operation_id is None:
        if facts.lease is not None or any(record is not None for record in records) or facts.slot_operation_id is not None:
            return _blocked()
        return _projection(phase="NOT_STARTED", cancel="NOT_REQUESTED", adjudication="NOT_REQUIRED",
                           action="NONE", label="音声認識は開始されていません", started=False,
                           known=True, stopped=False, evidence="NONE", release=False)
    if not _valid_lease(facts):
        return _blocked()
    slot_in_progress = facts.slot_status == "IN_PROGRESS" and facts.slot_result_ref == facts.runtime_operation_id
    slot_owned_or_released = facts.slot_status in {"IN_PROGRESS", "PENDING"} and facts.slot_result_ref == facts.runtime_operation_id
    admission_match = _ADMISSION.fullmatch(facts.operation_result_ref) if isinstance(facts.operation_result_ref, str) else None
    admission_ref = (
        admission_match is not None
        and admission_match.group(1) == facts.source_asset_sha256.removeprefix("sha256:")
    )
    publication_ref = isinstance(facts.operation_result_ref, str) and _DIGEST.fullmatch(facts.operation_result_ref) is not None
    if facts.operation_status == "PENDING":
        if facts.operation_attempt != 0 or facts.operation_result_ref is not None or facts.slot_operation_id is not None or any(record is not None for record in records):
            return _blocked()
    elif facts.operation_status == "IN_PROGRESS":
        if facts.operation_attempt < 1 or not admission_ref or facts.adjudication is not None or facts.terminal_commit is not None:
            return _blocked()
    elif facts.operation_status == "PARTIAL":
        if facts.operation_attempt < 1:
            return _blocked()
        if facts.recovery_state == "ADJUDICATION_REQUIRED_NO_PUBLICATION":
            if not admission_ref or facts.cancel_request is not None or facts.cancel_outcome is not None or facts.terminal_commit is not None:
                return _blocked()
            if facts.adjudication is None and (facts.barrier is not None or facts.generation_observation is not None):
                return _blocked()
            if facts.adjudication is not None and facts.barrier is None:
                return _blocked()
        elif facts.recovery_state == "RECOVERABLE_PUBLICATION":
            if not publication_ref or any(record is not None for record in records):
                return _blocked()
        else:
            return _blocked()
    elif facts.operation_status == "COMPLETED":
        if facts.operation_attempt < 1 or facts.recovery_state != "VERIFICATION_ONLY" or not publication_ref or any(record is not None for record in records):
            return _blocked()
    elif facts.operation_status == "FAILED":
        if facts.operation_attempt < 1 or (facts.terminal_commit is None and any(record is not None for record in records)):
            return _blocked()
    if facts.operation_status in {"IN_PROGRESS", "PARTIAL"} and not slot_in_progress:
        return _blocked()
    if facts.operation_status in {"COMPLETED", "FAILED"} and not slot_owned_or_released:
        return _blocked()
    if any(record is not None and not _record_binds(record, facts) for record in records):
        return _blocked()
    admissions = {
        getattr(record, "runtime_admission_ref", getattr(record, "prior_runtime_admission_ref", None))
        for record in records if record is not None
    }
    admissions.discard(None)
    request_digests = {
        record.runtime_request_sha256 for record in records
        if record is not None and hasattr(record, "runtime_request_sha256")
    }
    decision_digests = {
        record.runtime_decision_sha256 for record in records
        if record is not None and hasattr(record, "runtime_decision_sha256")
    }
    if len(admissions) > 1 or len(request_digests) > 1 or len(decision_digests) > 1:
        return _blocked()
    if (
        admissions
        and isinstance(facts.operation_result_ref, str)
        and _ADMISSION.fullmatch(facts.operation_result_ref) is not None
        and admissions != {facts.operation_result_ref}
    ):
        return _blocked()
    if facts.cancel_outcome is not None and (
        facts.cancel_request is None
        or facts.cancel_outcome.cancel_request_sha256 != facts.cancel_request.record_sha256
    ):
        return _blocked()
    if facts.adjudication is not None and (facts.cancel_request is not None or facts.cancel_outcome is not None):
        return _blocked()
    barrier = facts.barrier
    if barrier is not None and barrier.barrier_owner == "PUBLICATION" and any(
        record is not None for record in (
            facts.cancel_request, facts.cancel_outcome, facts.adjudication,
            facts.generation_observation, facts.terminal_commit,
        )
    ):
        return _blocked()
    if facts.generation_observation is not None and (
        barrier is None
        or barrier.barrier_owner != "TERMINAL_CLOSURE"
        or facts.generation_observation.commit_barrier_sha256 != barrier.record_sha256
    ):
        return _blocked()

    if facts.terminal_commit is not None:
        commit = facts.terminal_commit
        closure = facts.cancel_outcome if commit.closure_kind == "CONFIRMED_CANCEL" else facts.adjudication
        expected_ref = None if closure is None else (
            "task098-runtime-cancelled:v1:" if commit.closure_kind == "CONFIRMED_CANCEL"
            else "task098-runtime-adjudicated-failed:v1:"
        ) + closure.record_sha256.removeprefix("sha256:")
        if (
            closure is None or barrier is None or facts.generation_observation is None
            or barrier.barrier_owner != "TERMINAL_CLOSURE"
            or barrier.closure_record_sha256 != closure.record_sha256
            or commit.closure_record_sha256 != closure.record_sha256
            or commit.commit_barrier_sha256 != barrier.record_sha256
            or commit.generation_absence_observation_sha256 != facts.generation_observation.record_sha256
            or facts.generation_observation.observation != "EXACT_GENERATION_ABSENT"
            or facts.operation_status != "FAILED" or facts.operation_result_ref != expected_ref
            or commit.terminal_result_ref != expected_ref or not slot_owned_or_released
        ):
            return _blocked()
        if commit.closure_kind == "HUMAN_ADJUDICATED_FAILED":
            return _projection(phase="BLOCKED", cancel="STOP_NOT_CONFIRMED", adjudication="CLOSED_FAILED_NO_REPLAY",
                               action="NONE", label="Human確認により失敗終了しました（再実行なし）",
                               started=False, known=False, stopped=False, evidence="HUMAN_ATTESTATION", release=True)
        if facts.cancel_outcome.outcome == "CANCELLED_BEFORE_PROVIDER_EFFECT":
            return _projection(phase="BLOCKED", cancel=facts.cancel_outcome.outcome, adjudication="NOT_REQUIRED",
                               action="NONE", label="Provider開始前にキャンセルしました", started=False,
                               known=True, stopped=True, evidence="PRE_PROVIDER", release=True)
        if facts.cancel_outcome.outcome == "CANCELLED_AFTER_COOPERATIVE_BOUNDARY":
            return _projection(phase="BLOCKED", cancel=facts.cancel_outcome.outcome, adjudication="NOT_REQUIRED",
                               action="NONE", label="協調停止を確認してキャンセルしました", started=True,
                               known=True, stopped=True, evidence="COOPERATIVE_CHECKPOINT", release=True)
        return _blocked()

    if barrier is not None:
        if barrier.barrier_owner == "PUBLICATION" and facts.operation_result_ref == barrier.runtime_admission_ref:
            return _projection(phase="PUBLICATION_COMMITTING", cancel="NOT_REQUESTED", adjudication="NOT_REQUIRED",
                               action="NONE", label="結果の確定処理が開始されています", started=True,
                               known=True, stopped=False, evidence="NONE", release=False)
        if barrier.barrier_owner == "TERMINAL_CLOSURE":
            human = facts.adjudication is not None and barrier.closure_record_sha256 == facts.adjudication.record_sha256
            cancel = facts.cancel_outcome is not None and barrier.closure_record_sha256 == facts.cancel_outcome.record_sha256
            if human:
                return _projection(phase="BLOCKED", cancel="STOP_NOT_CONFIRMED", adjudication="REQUIRED",
                                   action="NONE", label="Human終了処理を安全に確定できません", started=False,
                                   known=False, stopped=False, evidence="HUMAN_ATTESTATION", release=False)
            if cancel:
                return _blocked(label="キャンセル終了処理を安全に確定できません")
        return _blocked()

    if facts.cancel_outcome is not None:
        if facts.cancel_outcome.outcome != "STOP_NOT_CONFIRMED":
            return _blocked()
        return _projection(phase="UNKNOWN_AFTER_DISCONNECT", cancel="STOP_NOT_CONFIRMED", adjudication="NOT_REQUIRED",
                           action="NONE", label="Provider停止を確認できません",
                           started=facts.cancel_outcome.provider_execution_started, known=True,
                           stopped=False, evidence="NONE", release=False)
    if facts.cancel_request is not None:
        observed = facts.phase or "UNKNOWN_AFTER_DISCONNECT"
        if observed not in {"ADMISSION", "PROVIDER_STARTING", "PROVIDER_RUNNING", "PUBLICATION_VALIDATING", "UNKNOWN_AFTER_DISCONNECT"}:
            return _blocked()
        started = observed in {"PROVIDER_RUNNING", "PUBLICATION_VALIDATING"}
        known = observed != "UNKNOWN_AFTER_DISCONNECT"
        return _projection(phase=observed, cancel="CANCEL_REQUESTED", adjudication="NOT_REQUIRED",
                           action="NONE", label="キャンセルを要求しました。停止確認中です",
                           started=started, known=known, stopped=False, evidence="NONE", release=False)

    if facts.operation_status == "PARTIAL" and facts.recovery_state == "ADJUDICATION_REQUIRED_NO_PUBLICATION" and slot_in_progress:
        return _projection(phase="UNKNOWN_AFTER_DISCONNECT", cancel="STOP_NOT_CONFIRMED", adjudication="REQUIRED",
                           action="CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY", label="Provider停止のHuman確認が必要です",
                           started=False, known=False, stopped=False, evidence="NONE", release=False)
    if facts.operation_status == "PARTIAL" and facts.recovery_state == "RECOVERABLE_PUBLICATION" and isinstance(facts.operation_result_ref, str) and _DIGEST.fullmatch(facts.operation_result_ref):
        return _projection(phase="PUBLICATION_COMMITTING", cancel="NOT_REQUESTED", adjudication="NOT_REQUIRED",
                           action="NONE", label="既存結果の復旧が必要です", started=True,
                           known=True, stopped=False, evidence="NONE", release=False)
    if facts.operation_status == "COMPLETED" and facts.recovery_state == "VERIFICATION_ONLY" and isinstance(facts.operation_result_ref, str) and _DIGEST.fullmatch(facts.operation_result_ref):
        return _projection(phase="COMPLETED", cancel="NOT_REQUESTED", adjudication="NOT_REQUIRED",
                           action="NONE", label="音声認識は完了しています", started=True,
                           known=True, stopped=False, evidence="NONE", release=False)
    if facts.operation_status == "IN_PROGRESS":
        rows = {
            "ADMISSION": (False, "REQUEST_CANCEL", "実行許可を確認中です"),
            "PROVIDER_STARTING": (False, "REQUEST_CANCEL", "音声認識を開始しています"),
            "PROVIDER_RUNNING": (True, "REQUEST_CANCEL", "音声認識を実行中です"),
            "PUBLICATION_VALIDATING": (True, "REQUEST_CANCEL", "結果を検証中です"),
        }
        if facts.phase in rows:
            started, action, label = rows[facts.phase]
            return _projection(phase=facts.phase, cancel="NOT_REQUESTED", adjudication="NOT_REQUIRED",
                               action=action, label=label, started=started, known=True,
                               stopped=False, evidence="NONE", release=False)
        if facts.phase == "PUBLICATION_COMMITTING":
            return _projection(phase="BLOCKED", cancel="STOP_NOT_CONFIRMED", adjudication="NOT_REQUIRED",
                               action="NONE", label="結果確定の排他状態を確認できません", started=True,
                               known=True, stopped=False, evidence="NONE", release=False)
        return _projection(phase="UNKNOWN_AFTER_DISCONNECT", cancel="STOP_NOT_CONFIRMED", adjudication="NOT_REQUIRED",
                           action="NONE", label="実行状態を確認できません", started=False,
                           known=False, stopped=False, evidence="NONE", release=False)
    if facts.operation_status == "PENDING" and facts.operation_attempt == 0:
        return _projection(phase="NOT_STARTED", cancel="NOT_REQUESTED", adjudication="NOT_REQUIRED",
                           action="NONE", label="開始待ちです", started=False, known=True,
                           stopped=False, evidence="NONE", release=False)
    if facts.operation_status == "FAILED":
        return _blocked(label="失敗状態を確認してください")
    return _blocked()


def validate_schema_mirror() -> None:
    root = Path(__file__).resolve().parents[2]
    canonical = (root / "schemas" / SCHEMA_NAME).read_bytes()
    packaged = resources.files("ai_video_production.schema_resources").joinpath(SCHEMA_NAME).read_bytes()
    if canonical != packaged:
        raise ValueError("runtime transcription control schema mirror differs")
