"""TASK-014 body-free Local Primary narration render admission contract.

This module is intentionally pure.  It binds the already-hosted Local Primary
preflight to exact resource, durable-job, output-destination and Owner Human
Gate evidence.  It does not load a model, reserve a device, create a Job, read
or write audio, render narration, publish an Asset or dispatch an operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from typing import Any, Mapping

from .owner_narration_local_primary import LocalNarrationRouteMode, NarrationIntendedUsage
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_ID = "bai.task014.local-primary-narration-render-admission.v1"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_REASON_RE = re.compile(r"[A-Z][A-Z0-9_]{1,95}")
_PRIVATE_TERMS = ("credential", "password", "secret", "token", "private-key")


class ContractState(str, Enum):
    CANONICAL_REF_NOT_PROVIDED = "CANONICAL_REF_NOT_PROVIDED"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class PreflightDecision(str, Enum):
    READY_FOR_OWNER_HUMAN_GATE = "READY_FOR_OWNER_HUMAN_GATE"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class ResourceGateDecision(str, Enum):
    ADMITTED = "ADMITTED"
    DENIED = "DENIED"
    UNKNOWN = "UNKNOWN"


class DurableJobState(str, Enum):
    REGISTERED = "REGISTERED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    UNKNOWN = "UNKNOWN"


class RenderAuthorizationScope(str, Enum):
    PREVIEW_RENDER = "PREVIEW_RENDER"
    FULL_RENDER = "FULL_RENDER"


class AuthorityKind(str, Enum):
    OWNER_HUMAN_GATE = "OWNER_HUMAN_GATE"
    APPROVED_SYNTHETIC_TEST_AUTHORITY = "APPROVED_SYNTHETIC_TEST_AUTHORITY"


class RenderAdmissionDecision(str, Enum):
    READY_FOR_EXTERNAL_DISPATCH_GATE = "READY_FOR_EXTERNAL_DISPATCH_GATE"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


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


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a SHA-256 digest")
    return validate_sha256(value, field_name=name)


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


def _enum(enum_type: type[Enum], value: Any, name: str) -> Enum:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


def _expect_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _nullable_id(value: Any, name: str) -> str | None:
    return None if value is None else _id(value, name)


def _nullable_digest(value: Any, name: str) -> str | None:
    return None if value is None else _digest(value, name)


def _nullable_timestamp(value: Any, name: str) -> str | None:
    return None if value is None else _timestamp(value, name)


def _binding_nullability(state: ContractState, values: tuple[Any, ...], name: str) -> None:
    if state is ContractState.BOUND_VERIFIED:
        if any(value is None for value in values):
            raise ValueError(f"{name} BOUND_VERIFIED fields are incomplete")
    elif any(value is not None for value in values):
        raise ValueError(f"{name} unresolved state must not invent canonical fields")


def _hash(body: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(body))


@dataclass(frozen=True)
class LocalPrimaryPreflightBinding:
    contract_state: ContractState
    preflight_id: str | None
    preflight_sha256: str | None
    route_mode: LocalNarrationRouteMode | None
    intended_usage: NarrationIntendedUsage | None
    script_text_revision_sha256: str | None
    voice_profile_revision_sha256: str | None
    decision: PreflightDecision | None
    evaluated_at: str | None
    expires_at: str | None

    def __post_init__(self) -> None:
        state = _enum(ContractState, self.contract_state, "preflight contract_state")
        object.__setattr__(self, "contract_state", state)
        object.__setattr__(self, "preflight_id", _nullable_id(self.preflight_id, "preflight_id"))
        object.__setattr__(self, "preflight_sha256", _nullable_digest(self.preflight_sha256, "preflight_sha256"))
        route = None if self.route_mode is None else _enum(LocalNarrationRouteMode, self.route_mode, "preflight route_mode")
        usage = None if self.intended_usage is None else _enum(NarrationIntendedUsage, self.intended_usage, "preflight intended_usage")
        decision = None if self.decision is None else _enum(PreflightDecision, self.decision, "preflight decision")
        object.__setattr__(self, "route_mode", route)
        object.__setattr__(self, "intended_usage", usage)
        object.__setattr__(self, "script_text_revision_sha256", _nullable_digest(self.script_text_revision_sha256, "preflight script_text_revision_sha256"))
        object.__setattr__(self, "voice_profile_revision_sha256", _nullable_digest(self.voice_profile_revision_sha256, "preflight voice_profile_revision_sha256"))
        object.__setattr__(self, "decision", decision)
        object.__setattr__(self, "evaluated_at", _nullable_timestamp(self.evaluated_at, "preflight evaluated_at"))
        object.__setattr__(self, "expires_at", _nullable_timestamp(self.expires_at, "preflight expires_at"))
        _binding_nullability(state, (self.preflight_id, self.preflight_sha256, route, usage, self.script_text_revision_sha256, self.voice_profile_revision_sha256, decision, self.evaluated_at, self.expires_at), "LocalPrimaryPreflightBinding")

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_state": self.contract_state.value,
            "preflight_id": self.preflight_id,
            "preflight_sha256": self.preflight_sha256,
            "route_mode": None if self.route_mode is None else self.route_mode.value,
            "intended_usage": None if self.intended_usage is None else self.intended_usage.value,
            "script_text_revision_sha256": self.script_text_revision_sha256,
            "voice_profile_revision_sha256": self.voice_profile_revision_sha256,
            "decision": None if self.decision is None else self.decision.value,
            "evaluated_at": self.evaluated_at,
            "expires_at": self.expires_at,
        }


@dataclass(frozen=True)
class ResourceAdmissionBinding:
    contract_state: ContractState
    resource_gate_id: str | None
    resource_gate_sha256: str | None
    operation_scope: str | None
    route_mode: LocalNarrationRouteMode | None
    preflight_sha256: str | None
    decision: ResourceGateDecision | None
    evaluated_at: str | None
    expires_at: str | None

    def __post_init__(self) -> None:
        state = _enum(ContractState, self.contract_state, "resource contract_state")
        object.__setattr__(self, "contract_state", state)
        object.__setattr__(self, "resource_gate_id", _nullable_id(self.resource_gate_id, "resource_gate_id"))
        object.__setattr__(self, "resource_gate_sha256", _nullable_digest(self.resource_gate_sha256, "resource_gate_sha256"))
        scope = None if self.operation_scope is None else _id(self.operation_scope, "resource operation_scope")
        route = None if self.route_mode is None else _enum(LocalNarrationRouteMode, self.route_mode, "resource route_mode")
        object.__setattr__(self, "route_mode", route)
        object.__setattr__(self, "preflight_sha256", _nullable_digest(self.preflight_sha256, "resource preflight_sha256"))
        decision = None if self.decision is None else _enum(ResourceGateDecision, self.decision, "resource decision")
        object.__setattr__(self, "operation_scope", scope)
        object.__setattr__(self, "decision", decision)
        object.__setattr__(self, "evaluated_at", _nullable_timestamp(self.evaluated_at, "resource evaluated_at"))
        object.__setattr__(self, "expires_at", _nullable_timestamp(self.expires_at, "resource expires_at"))
        _binding_nullability(state, (self.resource_gate_id, self.resource_gate_sha256, scope, route, self.preflight_sha256, decision, self.evaluated_at, self.expires_at), "ResourceAdmissionBinding")

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_state": self.contract_state.value,
            "resource_gate_id": self.resource_gate_id,
            "resource_gate_sha256": self.resource_gate_sha256,
            "operation_scope": self.operation_scope,
            "route_mode": None if self.route_mode is None else self.route_mode.value,
            "preflight_sha256": self.preflight_sha256,
            "decision": None if self.decision is None else self.decision.value,
            "evaluated_at": self.evaluated_at,
            "expires_at": self.expires_at,
        }


@dataclass(frozen=True)
class DurableNarrationJobBinding:
    contract_state: ContractState
    job_id: str | None
    job_revision: int | None
    job_revision_sha256: str | None
    operation_identity_sha256: str | None
    idempotency_key_sha256: str | None
    job_state: DurableJobState | None

    def __post_init__(self) -> None:
        state = _enum(ContractState, self.contract_state, "job contract_state")
        object.__setattr__(self, "contract_state", state)
        object.__setattr__(self, "job_id", _nullable_id(self.job_id, "job_id"))
        if self.job_revision is not None and (isinstance(self.job_revision, bool) or not isinstance(self.job_revision, int) or self.job_revision < 1):
            raise ValueError("job_revision must be an integer >= 1")
        object.__setattr__(self, "job_revision_sha256", _nullable_digest(self.job_revision_sha256, "job_revision_sha256"))
        object.__setattr__(self, "operation_identity_sha256", _nullable_digest(self.operation_identity_sha256, "operation_identity_sha256"))
        object.__setattr__(self, "idempotency_key_sha256", _nullable_digest(self.idempotency_key_sha256, "idempotency_key_sha256"))
        job_state = None if self.job_state is None else _enum(DurableJobState, self.job_state, "job_state")
        object.__setattr__(self, "job_state", job_state)
        _binding_nullability(state, (self.job_id, self.job_revision, self.job_revision_sha256, self.operation_identity_sha256, self.idempotency_key_sha256, job_state), "DurableNarrationJobBinding")

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_state": self.contract_state.value,
            "job_id": self.job_id,
            "job_revision": self.job_revision,
            "job_revision_sha256": self.job_revision_sha256,
            "operation_identity_sha256": self.operation_identity_sha256,
            "idempotency_key_sha256": self.idempotency_key_sha256,
            "job_state": None if self.job_state is None else self.job_state.value,
        }


@dataclass(frozen=True)
class OutputStagingDestinationBinding:
    contract_state: ContractState
    destination_id: str | None
    storage_owner_ref: str | None
    storage_policy_sha256: str | None
    quota_admission_sha256: str | None
    recovery_policy_sha256: str | None
    retention_policy_sha256: str | None
    allowed_artifact_class: str | None
    public_exposure: bool | None

    def __post_init__(self) -> None:
        state = _enum(ContractState, self.contract_state, "destination contract_state")
        object.__setattr__(self, "contract_state", state)
        object.__setattr__(self, "destination_id", _nullable_id(self.destination_id, "destination_id"))
        object.__setattr__(self, "storage_owner_ref", _nullable_id(self.storage_owner_ref, "storage_owner_ref"))
        object.__setattr__(self, "storage_policy_sha256", _nullable_digest(self.storage_policy_sha256, "storage_policy_sha256"))
        object.__setattr__(self, "quota_admission_sha256", _nullable_digest(self.quota_admission_sha256, "quota_admission_sha256"))
        object.__setattr__(self, "recovery_policy_sha256", _nullable_digest(self.recovery_policy_sha256, "recovery_policy_sha256"))
        object.__setattr__(self, "retention_policy_sha256", _nullable_digest(self.retention_policy_sha256, "retention_policy_sha256"))
        artifact = None if self.allowed_artifact_class is None else _id(self.allowed_artifact_class, "allowed_artifact_class")
        object.__setattr__(self, "allowed_artifact_class", artifact)
        if self.public_exposure is not None and not isinstance(self.public_exposure, bool):
            raise ValueError("public_exposure must be boolean or null")
        _binding_nullability(state, (self.destination_id, self.storage_owner_ref, self.storage_policy_sha256, self.quota_admission_sha256, self.recovery_policy_sha256, self.retention_policy_sha256, artifact, self.public_exposure), "OutputStagingDestinationBinding")
        if state is ContractState.BOUND_VERIFIED:
            if artifact != "STAGED_NARRATION_PCM_WAV_48000_MONO" or self.public_exposure is not False:
                raise ValueError("destination must be private 48 kHz mono staged narration")

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_state": self.contract_state.value,
            "destination_id": self.destination_id,
            "storage_owner_ref": self.storage_owner_ref,
            "storage_policy_sha256": self.storage_policy_sha256,
            "quota_admission_sha256": self.quota_admission_sha256,
            "recovery_policy_sha256": self.recovery_policy_sha256,
            "retention_policy_sha256": self.retention_policy_sha256,
            "allowed_artifact_class": self.allowed_artifact_class,
            "public_exposure": self.public_exposure,
        }


@dataclass(frozen=True)
class ExecutionAuthorizationBinding:
    contract_state: ContractState
    authorization_id: str | None
    authorization_revision: int | None
    authorization_sha256: str | None
    authority_kind: AuthorityKind | None
    project_id: str | None
    admission_id: str | None
    admission_revision: int | None
    route_mode: LocalNarrationRouteMode | None
    intended_usage: NarrationIntendedUsage | None
    script_text_revision_sha256: str | None
    voice_profile_revision_sha256: str | None
    preflight_sha256: str | None
    resource_gate_sha256: str | None
    job_revision_sha256: str | None
    destination_policy_sha256: str | None
    scope: RenderAuthorizationScope | None
    issued_at: str | None
    expires_at: str | None
    one_shot: bool | None
    evidence_ref: str | None
    evidence_sha256: str | None

    def __post_init__(self) -> None:
        state = _enum(ContractState, self.contract_state, "authorization contract_state")
        object.__setattr__(self, "contract_state", state)
        for field in ("authorization_id", "project_id", "admission_id", "evidence_ref"):
            object.__setattr__(self, field, _nullable_id(getattr(self, field), field))
        for field in ("authorization_sha256", "script_text_revision_sha256", "voice_profile_revision_sha256", "preflight_sha256", "resource_gate_sha256", "job_revision_sha256", "destination_policy_sha256", "evidence_sha256"):
            object.__setattr__(self, field, _nullable_digest(getattr(self, field), field))
        for field in ("authorization_revision", "admission_revision"):
            value = getattr(self, field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 1):
                raise ValueError(f"{field} must be an integer >= 1")
        authority = None if self.authority_kind is None else _enum(AuthorityKind, self.authority_kind, "authority_kind")
        route = None if self.route_mode is None else _enum(LocalNarrationRouteMode, self.route_mode, "authorization route_mode")
        usage = None if self.intended_usage is None else _enum(NarrationIntendedUsage, self.intended_usage, "authorization intended_usage")
        scope = None if self.scope is None else _enum(RenderAuthorizationScope, self.scope, "authorization scope")
        object.__setattr__(self, "authority_kind", authority)
        object.__setattr__(self, "route_mode", route)
        object.__setattr__(self, "intended_usage", usage)
        object.__setattr__(self, "scope", scope)
        object.__setattr__(self, "issued_at", _nullable_timestamp(self.issued_at, "authorization issued_at"))
        object.__setattr__(self, "expires_at", _nullable_timestamp(self.expires_at, "authorization expires_at"))
        if self.one_shot is not None and not isinstance(self.one_shot, bool):
            raise ValueError("one_shot must be boolean or null")
        values = tuple(getattr(self, field) for field in (
            "authorization_id", "authorization_revision", "authorization_sha256", "authority_kind",
            "project_id", "admission_id", "admission_revision", "route_mode", "intended_usage",
            "script_text_revision_sha256", "voice_profile_revision_sha256", "preflight_sha256", "resource_gate_sha256", "job_revision_sha256",
            "destination_policy_sha256", "scope", "issued_at", "expires_at", "one_shot",
            "evidence_ref", "evidence_sha256",
        ))
        _binding_nullability(state, values, "ExecutionAuthorizationBinding")
        if state is ContractState.BOUND_VERIFIED and self.one_shot is not True:
            raise ValueError("execution authorization must be one-shot")

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_state": self.contract_state.value,
            "authorization_id": self.authorization_id,
            "authorization_revision": self.authorization_revision,
            "authorization_sha256": self.authorization_sha256,
            "authority_kind": None if self.authority_kind is None else self.authority_kind.value,
            "project_id": self.project_id,
            "admission_id": self.admission_id,
            "admission_revision": self.admission_revision,
            "route_mode": None if self.route_mode is None else self.route_mode.value,
            "intended_usage": None if self.intended_usage is None else self.intended_usage.value,
            "script_text_revision_sha256": self.script_text_revision_sha256,
            "voice_profile_revision_sha256": self.voice_profile_revision_sha256,
            "preflight_sha256": self.preflight_sha256,
            "resource_gate_sha256": self.resource_gate_sha256,
            "job_revision_sha256": self.job_revision_sha256,
            "destination_policy_sha256": self.destination_policy_sha256,
            "scope": None if self.scope is None else self.scope.value,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "one_shot": self.one_shot,
            "evidence_ref": self.evidence_ref,
            "evidence_sha256": self.evidence_sha256,
        }


@dataclass(frozen=True)
class LocalPrimaryNarrationRenderAdmission:
    project_id: str
    admission_id: str
    revision: int
    parent_revision_sha256: str | None
    created_at: str
    route_mode: LocalNarrationRouteMode
    intended_usage: NarrationIntendedUsage
    script_text_revision_id: str
    script_text_revision_sha256: str
    voice_profile_revision_id: str
    voice_profile_revision_sha256: str
    preflight_binding: LocalPrimaryPreflightBinding
    resource_admission_binding: ResourceAdmissionBinding
    durable_job_binding: DurableNarrationJobBinding
    output_destination_binding: OutputStagingDestinationBinding
    execution_authorization_binding: ExecutionAuthorizationBinding
    decision: RenderAdmissionDecision
    reason_codes: tuple[str, ...]
    admission_sha256: str

    def _body(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_ID,
            "record_type": "LocalPrimaryNarrationRenderAdmission",
            "task_owner": "TASK-014",
            "project_id": self.project_id,
            "admission_id": self.admission_id,
            "revision": self.revision,
            "parent_revision_sha256": self.parent_revision_sha256,
            "created_at": self.created_at,
            "route_mode": self.route_mode.value,
            "intended_usage": self.intended_usage.value,
            "script_text_revision_id": self.script_text_revision_id,
            "script_text_revision_sha256": self.script_text_revision_sha256,
            "voice_profile_revision_id": self.voice_profile_revision_id,
            "voice_profile_revision_sha256": self.voice_profile_revision_sha256,
            "preflight_binding": self.preflight_binding.to_dict(),
            "resource_admission_binding": self.resource_admission_binding.to_dict(),
            "durable_job_binding": self.durable_job_binding.to_dict(),
            "output_destination_binding": self.output_destination_binding.to_dict(),
            "execution_authorization_binding": self.execution_authorization_binding.to_dict(),
            "decision": self.decision.value,
            "reason_codes": list(self.reason_codes),
            "script_body_persisted": False,
            "audio_body_persisted": False,
            "credential_value_persisted": False,
            "absolute_path_persisted": False,
            "execution_started": False,
            "job_dispatched": False,
            "model_loaded": False,
            "gpu_reserved": False,
            "audio_rendered": False,
            "asset_published": False,
        }

    def to_private_dict(self) -> dict[str, Any]:
        result = self._body()
        result["admission_sha256"] = self.admission_sha256
        return result

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_ID,
            "record_type": "LocalPrimaryNarrationRenderAdmissionPublicProjection",
            "task_owner": "TASK-014",
            "route_mode": self.route_mode.value,
            "intended_usage": self.intended_usage.value,
            "decision": self.decision.value,
            "reason_codes": list(self.reason_codes),
            "private_binding_count": 5,
            "script_body_persisted": False,
            "audio_body_persisted": False,
            "credential_value_persisted": False,
            "absolute_path_persisted": False,
            "execution_started": False,
            "job_dispatched": False,
            "model_loaded": False,
            "gpu_reserved": False,
            "audio_rendered": False,
            "asset_published": False,
        }


def _classify(
    *,
    project_id: str,
    admission_id: str,
    revision: int,
    created_at: str,
    route_mode: LocalNarrationRouteMode,
    intended_usage: NarrationIntendedUsage,
    script_text_revision_sha256: str,
    voice_profile_revision_sha256: str,
    preflight: LocalPrimaryPreflightBinding,
    resource: ResourceAdmissionBinding,
    job: DurableNarrationJobBinding,
    destination: OutputStagingDestinationBinding,
    authorization: ExecutionAuthorizationBinding,
) -> tuple[RenderAdmissionDecision, tuple[str, ...]]:
    bindings = (preflight, resource, job, destination, authorization)
    states = tuple(binding.contract_state for binding in bindings)
    if any(state in {ContractState.CANONICAL_REF_NOT_PROVIDED, ContractState.UNKNOWN} for state in states):
        return RenderAdmissionDecision.UNKNOWN, ("BINDING_UNRESOLVED",)
    if any(state is ContractState.MISMATCH for state in states):
        return RenderAdmissionDecision.BLOCKED, ("BINDING_MISMATCH",)
    reasons: list[str] = []
    if (
        preflight.route_mode is not route_mode
        or preflight.intended_usage is not intended_usage
        or preflight.script_text_revision_sha256 != script_text_revision_sha256
        or preflight.voice_profile_revision_sha256 != voice_profile_revision_sha256
    ):
        reasons.append("PREFLIGHT_SCOPE_MISMATCH")
    if preflight.decision is not PreflightDecision.READY_FOR_OWNER_HUMAN_GATE:
        reasons.append("PREFLIGHT_NOT_READY")
    if preflight.expires_at is not None and preflight.expires_at <= created_at:
        reasons.append("PREFLIGHT_EXPIRED")
    if (
        resource.operation_scope != "LOCAL_NARRATION_RENDER"
        or resource.route_mode is not route_mode
        or resource.preflight_sha256 != preflight.preflight_sha256
        or resource.decision is not ResourceGateDecision.ADMITTED
    ):
        reasons.append("RESOURCE_NOT_ADMITTED")
    if resource.expires_at is not None and resource.expires_at <= created_at:
        reasons.append("RESOURCE_RECEIPT_EXPIRED")
    if job.job_state is not DurableJobState.REGISTERED:
        reasons.append("DURABLE_JOB_NOT_REGISTERED")
    expected_operation_identity = render_operation_identity_sha256(
        project_id=project_id,
        admission_id=admission_id,
        admission_revision=revision,
        route_mode=route_mode,
        intended_usage=intended_usage,
        script_text_revision_sha256=script_text_revision_sha256,
        voice_profile_revision_sha256=voice_profile_revision_sha256,
        preflight_sha256=preflight.preflight_sha256,
        destination_policy_sha256=destination.storage_policy_sha256,
    )
    if job.operation_identity_sha256 != expected_operation_identity:
        reasons.append("DURABLE_JOB_IDENTITY_MISMATCH")
    expected_scope = RenderAuthorizationScope.PREVIEW_RENDER if intended_usage is NarrationIntendedUsage.PREVIEW else RenderAuthorizationScope.FULL_RENDER
    if (
        authorization.project_id != project_id
        or authorization.admission_id != admission_id
        or authorization.admission_revision != revision
        or authorization.route_mode is not route_mode
        or authorization.intended_usage is not intended_usage
        or authorization.script_text_revision_sha256 != script_text_revision_sha256
        or authorization.voice_profile_revision_sha256 != voice_profile_revision_sha256
        or authorization.preflight_sha256 != preflight.preflight_sha256
        or authorization.resource_gate_sha256 != resource.resource_gate_sha256
        or authorization.job_revision_sha256 != job.job_revision_sha256
        or authorization.destination_policy_sha256 != destination.storage_policy_sha256
        or authorization.scope is not expected_scope
    ):
        reasons.append("AUTHORIZATION_SCOPE_MISMATCH")
    if authorization.expires_at is not None and authorization.expires_at <= created_at:
        reasons.append("AUTHORIZATION_EXPIRED")
    if reasons:
        return RenderAdmissionDecision.BLOCKED, tuple(reasons)
    return RenderAdmissionDecision.READY_FOR_EXTERNAL_DISPATCH_GATE, ()


def render_operation_identity_sha256(
    *,
    project_id: str,
    admission_id: str,
    admission_revision: int,
    route_mode: LocalNarrationRouteMode,
    intended_usage: NarrationIntendedUsage,
    script_text_revision_sha256: str,
    voice_profile_revision_sha256: str,
    preflight_sha256: str | None,
    destination_policy_sha256: str | None,
) -> str:
    """Return the exact idempotent operation identity for the external Job owner."""
    body = {
        "schema": SCHEMA_ID,
        "operation_type": "LOCAL_PRIMARY_NARRATION_RENDER",
        "project_id": _id(project_id, "project_id"),
        "admission_id": _id(admission_id, "admission_id"),
        "admission_revision": admission_revision,
        "route_mode": _enum(LocalNarrationRouteMode, route_mode, "route_mode").value,
        "intended_usage": _enum(NarrationIntendedUsage, intended_usage, "intended_usage").value,
        "script_text_revision_sha256": _digest(script_text_revision_sha256, "script_text_revision_sha256"),
        "voice_profile_revision_sha256": _digest(voice_profile_revision_sha256, "voice_profile_revision_sha256"),
        "preflight_sha256": _digest(preflight_sha256, "preflight_sha256"),
        "destination_policy_sha256": _digest(destination_policy_sha256, "destination_policy_sha256"),
    }
    if isinstance(admission_revision, bool) or not isinstance(admission_revision, int) or admission_revision < 1:
        raise ValueError("admission_revision must be an integer >= 1")
    return _hash(body)


def compile_render_admission(
    *,
    project_id: str,
    admission_id: str,
    revision: int,
    parent_revision_sha256: str | None,
    created_at: str,
    route_mode: LocalNarrationRouteMode,
    intended_usage: NarrationIntendedUsage,
    script_text_revision_id: str,
    script_text_revision_sha256: str,
    voice_profile_revision_id: str,
    voice_profile_revision_sha256: str,
    preflight_binding: LocalPrimaryPreflightBinding,
    resource_admission_binding: ResourceAdmissionBinding,
    durable_job_binding: DurableNarrationJobBinding,
    output_destination_binding: OutputStagingDestinationBinding,
    execution_authorization_binding: ExecutionAuthorizationBinding,
) -> LocalPrimaryNarrationRenderAdmission:
    project_id = _id(project_id, "project_id")
    admission_id = _id(admission_id, "admission_id")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise ValueError("revision must be an integer >= 1")
    if revision == 1 and parent_revision_sha256 is not None:
        raise ValueError("revision 1 must not have a parent")
    if revision > 1 and parent_revision_sha256 is None:
        raise ValueError("revision > 1 requires parent_revision_sha256")
    parent_revision_sha256 = _nullable_digest(parent_revision_sha256, "parent_revision_sha256")
    created_at = _timestamp(created_at, "created_at")
    route_mode = _enum(LocalNarrationRouteMode, route_mode, "route_mode")
    intended_usage = _enum(NarrationIntendedUsage, intended_usage, "intended_usage")
    script_text_revision_id = _id(script_text_revision_id, "script_text_revision_id")
    script_text_revision_sha256 = _digest(script_text_revision_sha256, "script_text_revision_sha256")
    voice_profile_revision_id = _id(voice_profile_revision_id, "voice_profile_revision_id")
    voice_profile_revision_sha256 = _digest(voice_profile_revision_sha256, "voice_profile_revision_sha256")
    decision, reasons = _classify(
        project_id=project_id,
        admission_id=admission_id,
        revision=revision,
        created_at=created_at,
        route_mode=route_mode,
        intended_usage=intended_usage,
        script_text_revision_sha256=script_text_revision_sha256,
        voice_profile_revision_sha256=voice_profile_revision_sha256,
        preflight=preflight_binding,
        resource=resource_admission_binding,
        job=durable_job_binding,
        destination=output_destination_binding,
        authorization=execution_authorization_binding,
    )
    draft = LocalPrimaryNarrationRenderAdmission(
        project_id, admission_id, revision, parent_revision_sha256, created_at,
        route_mode, intended_usage, script_text_revision_id, script_text_revision_sha256,
        voice_profile_revision_id, voice_profile_revision_sha256, preflight_binding,
        resource_admission_binding, durable_job_binding, output_destination_binding,
        execution_authorization_binding, decision, reasons, "sha256:" + "0" * 64,
    )
    return LocalPrimaryNarrationRenderAdmission(
        project_id, admission_id, revision, parent_revision_sha256, created_at,
        route_mode, intended_usage, script_text_revision_id, script_text_revision_sha256,
        voice_profile_revision_id, voice_profile_revision_sha256, preflight_binding,
        resource_admission_binding, durable_job_binding, output_destination_binding,
        execution_authorization_binding, decision, reasons, _hash(draft._body()),
    )


def _parse_preflight(value: Mapping[str, Any]) -> LocalPrimaryPreflightBinding:
    expected = {"contract_state", "preflight_id", "preflight_sha256", "route_mode", "intended_usage", "script_text_revision_sha256", "voice_profile_revision_sha256", "decision", "evaluated_at", "expires_at"}
    _expect_keys(value, expected, "LocalPrimaryPreflightBinding")
    return LocalPrimaryPreflightBinding(**value)


def _parse_resource(value: Mapping[str, Any]) -> ResourceAdmissionBinding:
    expected = {"contract_state", "resource_gate_id", "resource_gate_sha256", "operation_scope", "route_mode", "preflight_sha256", "decision", "evaluated_at", "expires_at"}
    _expect_keys(value, expected, "ResourceAdmissionBinding")
    return ResourceAdmissionBinding(**value)


def _parse_job(value: Mapping[str, Any]) -> DurableNarrationJobBinding:
    expected = {"contract_state", "job_id", "job_revision", "job_revision_sha256", "operation_identity_sha256", "idempotency_key_sha256", "job_state"}
    _expect_keys(value, expected, "DurableNarrationJobBinding")
    return DurableNarrationJobBinding(**value)


def _parse_destination(value: Mapping[str, Any]) -> OutputStagingDestinationBinding:
    expected = {"contract_state", "destination_id", "storage_owner_ref", "storage_policy_sha256", "quota_admission_sha256", "recovery_policy_sha256", "retention_policy_sha256", "allowed_artifact_class", "public_exposure"}
    _expect_keys(value, expected, "OutputStagingDestinationBinding")
    return OutputStagingDestinationBinding(**value)


def _parse_authorization(value: Mapping[str, Any]) -> ExecutionAuthorizationBinding:
    expected = {
        "contract_state", "authorization_id", "authorization_revision", "authorization_sha256",
        "authority_kind", "project_id", "admission_id", "admission_revision", "route_mode",
        "intended_usage", "script_text_revision_sha256", "voice_profile_revision_sha256", "preflight_sha256",
        "resource_gate_sha256", "job_revision_sha256", "destination_policy_sha256", "scope", "issued_at",
        "expires_at", "one_shot", "evidence_ref", "evidence_sha256",
    }
    _expect_keys(value, expected, "ExecutionAuthorizationBinding")
    return ExecutionAuthorizationBinding(**value)


def parse_render_admission(value: Mapping[str, Any]) -> LocalPrimaryNarrationRenderAdmission:
    expected = {
        "schema", "record_type", "task_owner", "project_id", "admission_id", "revision",
        "parent_revision_sha256", "created_at", "route_mode", "intended_usage",
        "script_text_revision_id", "script_text_revision_sha256", "voice_profile_revision_id",
        "voice_profile_revision_sha256", "preflight_binding", "resource_admission_binding",
        "durable_job_binding", "output_destination_binding", "execution_authorization_binding",
        "decision", "reason_codes", "script_body_persisted", "audio_body_persisted",
        "credential_value_persisted", "absolute_path_persisted", "execution_started",
        "job_dispatched", "model_loaded", "gpu_reserved", "audio_rendered", "asset_published",
        "admission_sha256",
    }
    _expect_keys(value, expected, "LocalPrimaryNarrationRenderAdmission")
    if value["schema"] != SCHEMA_ID or value["record_type"] != "LocalPrimaryNarrationRenderAdmission" or value["task_owner"] != "TASK-014":
        raise ValueError("record identity is invalid")
    for field in (
        "script_body_persisted", "audio_body_persisted", "credential_value_persisted",
        "absolute_path_persisted", "execution_started", "job_dispatched", "model_loaded",
        "gpu_reserved", "audio_rendered", "asset_published",
    ):
        if value[field] is not False:
            raise ValueError(f"{field} must remain false")
    reasons = value["reason_codes"]
    if not isinstance(reasons, list) or len(reasons) > 32 or len(reasons) != len(set(reasons)) or any(not isinstance(item, str) or not _REASON_RE.fullmatch(item) for item in reasons):
        raise ValueError("reason_codes are invalid")
    compiled = compile_render_admission(
        project_id=value["project_id"], admission_id=value["admission_id"], revision=value["revision"],
        parent_revision_sha256=value["parent_revision_sha256"], created_at=value["created_at"],
        route_mode=value["route_mode"], intended_usage=value["intended_usage"],
        script_text_revision_id=value["script_text_revision_id"],
        script_text_revision_sha256=value["script_text_revision_sha256"],
        voice_profile_revision_id=value["voice_profile_revision_id"],
        voice_profile_revision_sha256=value["voice_profile_revision_sha256"],
        preflight_binding=_parse_preflight(value["preflight_binding"]),
        resource_admission_binding=_parse_resource(value["resource_admission_binding"]),
        durable_job_binding=_parse_job(value["durable_job_binding"]),
        output_destination_binding=_parse_destination(value["output_destination_binding"]),
        execution_authorization_binding=_parse_authorization(value["execution_authorization_binding"]),
    )
    if value["decision"] != compiled.decision.value or tuple(reasons) != compiled.reason_codes:
        raise ValueError("render admission classification mismatch")
    supplied_hash = _digest(value["admission_sha256"], "admission_sha256")
    if supplied_hash != compiled.admission_sha256:
        raise ValueError("render admission checksum mismatch")
    return compiled


def canonical_render_admission_json(value: LocalPrimaryNarrationRenderAdmission) -> bytes:
    return canonical_json_bytes(value.to_private_dict())
