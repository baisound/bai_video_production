"""TASK-017 body-free Storage Lifecycle / GC metadata contracts.

The module evaluates immutable retention facts and validates externally issued
authorization/effect receipts.  It never lists a filesystem, archives, moves,
overwrites or deletes bytes, mutates an Asset, or dispatches a storage job.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from typing import Any, Mapping, Sequence

from .assets import RetentionClass
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_ID = "bai.task017.storage-lifecycle-gc.v1"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_REASON_RE = re.compile(r"[A-Z][A-Z0-9_]{1,95}")
_PRIVATE_TERMS = ("credential", "password", "secret", "token", "private-key")


class ObservationState(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    UNKNOWN = "UNKNOWN"


class HoldState(str, Enum):
    CLEAR = "CLEAR"
    ACTIVE = "ACTIVE"
    UNKNOWN = "UNKNOWN"


class LifecycleDecision(str, Enum):
    KEEP = "KEEP"
    ARCHIVE_PROPOSED = "ARCHIVE_PROPOSED"
    DELETE_PROPOSED = "DELETE_PROPOSED"
    NO_ACTION_ALREADY_ABSENT = "NO_ACTION_ALREADY_ABSENT"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class StorageEffect(str, Enum):
    ARCHIVE = "ARCHIVE"
    DELETE = "DELETE"


class ContractState(str, Enum):
    CANONICAL_REF_NOT_PROVIDED = "CANONICAL_REF_NOT_PROVIDED"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class AuthorityKind(str, Enum):
    OWNER_HUMAN_GATE = "OWNER_HUMAN_GATE"
    APPROVED_SYNTHETIC_TEST_AUTHORITY = "APPROVED_SYNTHETIC_TEST_AUTHORITY"


class EffectGateDecision(str, Enum):
    READY_FOR_EXTERNAL_EFFECT = "READY_FOR_EXTERNAL_EFFECT"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class EffectResult(str, Enum):
    VERIFIED_ARCHIVED = "VERIFIED_ARCHIVED"
    VERIFIED_DELETED = "VERIFIED_DELETED"
    FAILED_KNOWN = "FAILED_KNOWN"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


def _id(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} is invalid")
    folded = value.casefold()
    if (
        "\\" in value
        or value.startswith("/")
        or any(part == ".." for part in value.split("/"))
        or any(term in folded for term in _PRIVATE_TERMS)
    ):
        raise ValueError(f"{name} violates the body-free identity boundary")
    if not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
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


def _seconds_between(earlier: str, later: str) -> int:
    first = datetime.fromisoformat(earlier[:-1] + "+00:00")
    second = datetime.fromisoformat(later[:-1] + "+00:00")
    return int((second - first).total_seconds())


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


def _hash(body: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(body))


def _strict_reasons(values: Sequence[str]) -> tuple[str, ...]:
    result = tuple(values)
    if len(result) > 32 or len(result) != len(set(result)):
        raise ValueError("reason_codes must be unique and bounded")
    if any(not isinstance(item, str) or not _REASON_RE.fullmatch(item) for item in result):
        raise ValueError("reason_codes contain an invalid value")
    return result


@dataclass(frozen=True)
class RetentionRule:
    retention_class: RetentionClass
    archive_after_seconds: int | None
    delete_after_seconds: int | None

    def __post_init__(self) -> None:
        retention_class = _enum(RetentionClass, self.retention_class, "retention_class")
        object.__setattr__(self, "retention_class", retention_class)
        if retention_class is RetentionClass.LEGAL_HOLD:
            if self.archive_after_seconds is not None or self.delete_after_seconds is not None:
                raise ValueError("LEGAL_HOLD thresholds must be null")
            return
        archive = _positive_int(self.archive_after_seconds, "archive_after_seconds")
        delete = _positive_int(self.delete_after_seconds, "delete_after_seconds")
        if delete <= archive:
            raise ValueError("delete_after_seconds must be greater than archive_after_seconds")

    def to_dict(self) -> dict[str, Any]:
        return {
            "retention_class": self.retention_class.value,
            "archive_after_seconds": self.archive_after_seconds,
            "delete_after_seconds": self.delete_after_seconds,
        }


@dataclass(frozen=True)
class StorageRetentionPolicyRevision:
    project_id: str
    policy_id: str
    revision: int
    parent_revision_sha256: str | None
    created_at: str
    max_observation_age_seconds: int
    rules: tuple[RetentionRule, ...]
    policy_revision_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_ID,
            "record_type": "StorageRetentionPolicyRevision",
            "task_owner": "TASK-017",
            "project_id": self.project_id,
            "policy_id": self.policy_id,
            "revision": self.revision,
            "parent_revision_sha256": self.parent_revision_sha256,
            "created_at": self.created_at,
            "max_observation_age_seconds": self.max_observation_age_seconds,
            "rules": [rule.to_dict() for rule in self.rules],
            "automatic_effect_authorized": False,
            "policy_revision_sha256": self.policy_revision_sha256,
        }


def compile_retention_policy(
    *,
    project_id: str,
    policy_id: str,
    revision: int,
    parent_revision_sha256: str | None,
    created_at: str,
    max_observation_age_seconds: int,
    rules: Sequence[RetentionRule],
) -> StorageRetentionPolicyRevision:
    project_id = _id(project_id, "project_id")
    policy_id = _id(policy_id, "policy_id")
    revision = _positive_int(revision, "revision")
    if revision == 1 and parent_revision_sha256 is not None:
        raise ValueError("revision 1 must not have a parent")
    if revision > 1 and parent_revision_sha256 is None:
        raise ValueError("revision > 1 requires a parent")
    if parent_revision_sha256 is not None:
        parent_revision_sha256 = _digest(parent_revision_sha256, "parent_revision_sha256")
    created_at = _timestamp(created_at, "created_at")
    maximum_age = _positive_int(max_observation_age_seconds, "max_observation_age_seconds")
    normalized = tuple(rules)
    expected = tuple(RetentionClass)
    if tuple(rule.retention_class for rule in normalized) != expected:
        raise ValueError("rules must contain every RetentionClass in canonical order")
    body = {
        "schema": SCHEMA_ID,
        "record_type": "StorageRetentionPolicyRevision",
        "task_owner": "TASK-017",
        "project_id": project_id,
        "policy_id": policy_id,
        "revision": revision,
        "parent_revision_sha256": parent_revision_sha256,
        "created_at": created_at,
        "max_observation_age_seconds": maximum_age,
        "rules": [rule.to_dict() for rule in normalized],
        "automatic_effect_authorized": False,
    }
    return StorageRetentionPolicyRevision(
        project_id, policy_id, revision, parent_revision_sha256, created_at,
        maximum_age, normalized, _hash(body),
    )


@dataclass(frozen=True)
class StorageObjectObservationReceipt:
    project_id: str
    observation_id: str
    object_ref: str
    object_revision_sha256: str
    asset_record_sha256: str
    retention_class: RetentionClass
    observation_state: ObservationState
    observed_at: str
    last_used_at: str | None
    storage_bytes: int | None
    active_reference_count: int | None
    pending_job_reference_count: int | None
    legal_hold_state: HoldState
    privacy_hold_state: HoldState
    inventory_profile_ref: str
    inventory_profile_sha256: str
    observation_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_ID,
            "record_type": "StorageObjectObservationReceipt",
            "task_owner": "TASK-017",
            "project_id": self.project_id,
            "observation_id": self.observation_id,
            "object_ref": self.object_ref,
            "object_revision_sha256": self.object_revision_sha256,
            "asset_record_sha256": self.asset_record_sha256,
            "retention_class": self.retention_class.value,
            "observation_state": self.observation_state.value,
            "observed_at": self.observed_at,
            "last_used_at": self.last_used_at,
            "storage_bytes": self.storage_bytes,
            "active_reference_count": self.active_reference_count,
            "pending_job_reference_count": self.pending_job_reference_count,
            "legal_hold_state": self.legal_hold_state.value,
            "privacy_hold_state": self.privacy_hold_state.value,
            "inventory_profile_ref": self.inventory_profile_ref,
            "inventory_profile_sha256": self.inventory_profile_sha256,
            "observation_performed_by_module": False,
            "path_body_persisted": False,
            "media_body_persisted": False,
            "observation_sha256": self.observation_sha256,
        }


def compile_storage_observation(
    *,
    project_id: str,
    observation_id: str,
    object_ref: str,
    object_revision_sha256: str,
    asset_record_sha256: str,
    retention_class: RetentionClass,
    observation_state: ObservationState,
    observed_at: str,
    last_used_at: str | None,
    storage_bytes: int | None,
    active_reference_count: int | None,
    pending_job_reference_count: int | None,
    legal_hold_state: HoldState,
    privacy_hold_state: HoldState,
    inventory_profile_ref: str,
    inventory_profile_sha256: str,
) -> StorageObjectObservationReceipt:
    project_id = _id(project_id, "project_id")
    observation_id = _id(observation_id, "observation_id")
    object_ref = _id(object_ref, "object_ref")
    object_revision_sha256 = _digest(object_revision_sha256, "object_revision_sha256")
    asset_record_sha256 = _digest(asset_record_sha256, "asset_record_sha256")
    retention_class = _enum(RetentionClass, retention_class, "retention_class")
    observation_state = _enum(ObservationState, observation_state, "observation_state")
    observed_at = _timestamp(observed_at, "observed_at")
    legal_hold_state = _enum(HoldState, legal_hold_state, "legal_hold_state")
    privacy_hold_state = _enum(HoldState, privacy_hold_state, "privacy_hold_state")
    inventory_profile_ref = _id(inventory_profile_ref, "inventory_profile_ref")
    inventory_profile_sha256 = _digest(inventory_profile_sha256, "inventory_profile_sha256")
    if observation_state is ObservationState.UNKNOWN:
        if any(value is not None for value in (last_used_at, storage_bytes, active_reference_count, pending_job_reference_count)):
            raise ValueError("UNKNOWN observation must not invent measured facts")
        if legal_hold_state is not HoldState.UNKNOWN or privacy_hold_state is not HoldState.UNKNOWN:
            raise ValueError("UNKNOWN observation requires unknown hold states")
    else:
        if last_used_at is None:
            raise ValueError("known observation requires last_used_at")
        last_used_at = _timestamp(last_used_at, "last_used_at")
        if _seconds_between(last_used_at, observed_at) < 0:
            raise ValueError("last_used_at cannot be after observed_at")
        storage_bytes = _positive_int(storage_bytes, "storage_bytes", allow_zero=True)
        active_reference_count = _positive_int(active_reference_count, "active_reference_count", allow_zero=True)
        pending_job_reference_count = _positive_int(pending_job_reference_count, "pending_job_reference_count", allow_zero=True)
    body = {
        "schema": SCHEMA_ID, "record_type": "StorageObjectObservationReceipt", "task_owner": "TASK-017",
        "project_id": project_id, "observation_id": observation_id, "object_ref": object_ref,
        "object_revision_sha256": object_revision_sha256, "asset_record_sha256": asset_record_sha256,
        "retention_class": retention_class.value, "observation_state": observation_state.value,
        "observed_at": observed_at, "last_used_at": last_used_at, "storage_bytes": storage_bytes,
        "active_reference_count": active_reference_count, "pending_job_reference_count": pending_job_reference_count,
        "legal_hold_state": legal_hold_state.value, "privacy_hold_state": privacy_hold_state.value,
        "inventory_profile_ref": inventory_profile_ref, "inventory_profile_sha256": inventory_profile_sha256,
        "observation_performed_by_module": False,
        "path_body_persisted": False, "media_body_persisted": False,
    }
    return StorageObjectObservationReceipt(
        project_id, observation_id, object_ref, object_revision_sha256, asset_record_sha256,
        retention_class, observation_state, observed_at, last_used_at, storage_bytes,
        active_reference_count, pending_job_reference_count, legal_hold_state, privacy_hold_state,
        inventory_profile_ref, inventory_profile_sha256, _hash(body),
    )


@dataclass(frozen=True)
class StorageDispositionDecisionReceipt:
    project_id: str
    decision_id: str
    policy_revision_sha256: str
    observation_sha256: str
    evaluated_at: str
    decision: LifecycleDecision
    proposed_effect: StorageEffect | None
    reason_codes: tuple[str, ...]
    decision_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_ID,
            "record_type": "StorageDispositionDecisionReceipt",
            "task_owner": "TASK-017",
            "project_id": self.project_id,
            "decision_id": self.decision_id,
            "policy_revision_sha256": self.policy_revision_sha256,
            "observation_sha256": self.observation_sha256,
            "evaluated_at": self.evaluated_at,
            "decision": self.decision.value,
            "proposed_effect": None if self.proposed_effect is None else self.proposed_effect.value,
            "reason_codes": list(self.reason_codes),
            "effect_started": False,
            "automatic_delete_authorized": False,
            "decision_sha256": self.decision_sha256,
        }


def compile_storage_disposition(
    *,
    project_id: str,
    decision_id: str,
    policy: StorageRetentionPolicyRevision,
    observation: StorageObjectObservationReceipt,
    evaluated_at: str,
) -> StorageDispositionDecisionReceipt:
    project_id = _id(project_id, "project_id")
    decision_id = _id(decision_id, "decision_id")
    evaluated_at = _timestamp(evaluated_at, "evaluated_at")
    if policy.project_id != project_id or observation.project_id != project_id:
        raise ValueError("project binding mismatch")
    decision: LifecycleDecision
    effect: StorageEffect | None = None
    reasons: tuple[str, ...]
    observation_age = _seconds_between(observation.observed_at, evaluated_at)
    if observation_age < 0 or observation_age > policy.max_observation_age_seconds:
        decision, reasons = LifecycleDecision.UNKNOWN, ("OBSERVATION_STALE_OR_FUTURE",)
    elif observation.observation_state is ObservationState.UNKNOWN:
        decision, reasons = LifecycleDecision.UNKNOWN, ("OBSERVATION_UNKNOWN",)
    elif observation.legal_hold_state is HoldState.UNKNOWN or observation.privacy_hold_state is HoldState.UNKNOWN:
        decision, reasons = LifecycleDecision.UNKNOWN, ("HOLD_STATE_UNKNOWN",)
    elif observation.observation_state is ObservationState.ABSENT:
        decision, reasons = LifecycleDecision.NO_ACTION_ALREADY_ABSENT, ("OBJECT_ALREADY_ABSENT",)
    elif (
        observation.retention_class is RetentionClass.LEGAL_HOLD
        or observation.legal_hold_state is HoldState.ACTIVE
        or observation.privacy_hold_state is HoldState.ACTIVE
    ):
        decision, reasons = LifecycleDecision.BLOCKED, ("HOLD_ACTIVE",)
    elif observation.active_reference_count or observation.pending_job_reference_count:
        decision, reasons = LifecycleDecision.KEEP, ("ACTIVE_REFERENCE_EXISTS",)
    else:
        rule = next(rule for rule in policy.rules if rule.retention_class is observation.retention_class)
        age = _seconds_between(observation.last_used_at, evaluated_at)  # type: ignore[arg-type]
        if age >= rule.delete_after_seconds:  # type: ignore[operator]
            decision, effect, reasons = LifecycleDecision.DELETE_PROPOSED, StorageEffect.DELETE, ("RETENTION_DELETE_THRESHOLD_REACHED",)
        elif age >= rule.archive_after_seconds:  # type: ignore[operator]
            decision, effect, reasons = LifecycleDecision.ARCHIVE_PROPOSED, StorageEffect.ARCHIVE, ("RETENTION_ARCHIVE_THRESHOLD_REACHED",)
        else:
            decision, reasons = LifecycleDecision.KEEP, ("RETENTION_WINDOW_ACTIVE",)
    reasons = _strict_reasons(reasons)
    body = {
        "schema": SCHEMA_ID, "record_type": "StorageDispositionDecisionReceipt", "task_owner": "TASK-017",
        "project_id": project_id, "decision_id": decision_id,
        "policy_revision_sha256": policy.policy_revision_sha256,
        "observation_sha256": observation.observation_sha256, "evaluated_at": evaluated_at,
        "decision": decision.value, "proposed_effect": None if effect is None else effect.value,
        "reason_codes": list(reasons), "effect_started": False, "automatic_delete_authorized": False,
    }
    return StorageDispositionDecisionReceipt(
        project_id, decision_id, policy.policy_revision_sha256, observation.observation_sha256,
        evaluated_at, decision, effect, reasons, _hash(body),
    )


@dataclass(frozen=True)
class StorageEffectAuthorizationBinding:
    contract_state: ContractState
    authorization_id: str | None
    authorization_revision: int | None
    authorization_sha256: str | None
    authority_kind: AuthorityKind | None
    project_id: str | None
    object_ref: str | None
    object_revision_sha256: str | None
    decision_sha256: str | None
    effect: StorageEffect | None
    issued_at: str | None
    expires_at: str | None
    one_shot: bool | None
    evidence_ref: str | None
    evidence_sha256: str | None

    def __post_init__(self) -> None:
        state = _enum(ContractState, self.contract_state, "contract_state")
        object.__setattr__(self, "contract_state", state)
        values = (
            self.authorization_id, self.authorization_revision, self.authorization_sha256,
            self.authority_kind, self.project_id, self.object_ref, self.object_revision_sha256,
            self.decision_sha256, self.effect, self.issued_at, self.expires_at, self.one_shot,
            self.evidence_ref, self.evidence_sha256,
        )
        if state is ContractState.BOUND_VERIFIED and any(value is None for value in values):
            raise ValueError("BOUND_VERIFIED authorization fields are incomplete")
        if state is not ContractState.BOUND_VERIFIED and any(value is not None for value in values):
            raise ValueError("unresolved authorization must not invent canonical fields")
        if state is ContractState.BOUND_VERIFIED:
            for field in ("authorization_id", "project_id", "object_ref", "evidence_ref"):
                object.__setattr__(self, field, _id(getattr(self, field), field))
            for field in ("authorization_sha256", "object_revision_sha256", "decision_sha256", "evidence_sha256"):
                object.__setattr__(self, field, _digest(getattr(self, field), field))
            _positive_int(self.authorization_revision, "authorization_revision")
            object.__setattr__(self, "authority_kind", _enum(AuthorityKind, self.authority_kind, "authority_kind"))
            object.__setattr__(self, "effect", _enum(StorageEffect, self.effect, "effect"))
            object.__setattr__(self, "issued_at", _timestamp(self.issued_at, "issued_at"))
            object.__setattr__(self, "expires_at", _timestamp(self.expires_at, "expires_at"))
            if _seconds_between(self.issued_at, self.expires_at) <= 0:  # type: ignore[arg-type]
                raise ValueError("authorization expiry must be after issuance")
            if self.one_shot is not True:
                raise ValueError("authorization must be one-shot")

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "StorageEffectAuthorizationBinding",
            "contract_state": self.contract_state.value,
            "authorization_id": self.authorization_id,
            "authorization_revision": self.authorization_revision,
            "authorization_sha256": self.authorization_sha256,
            "authority_kind": None if self.authority_kind is None else self.authority_kind.value,
            "project_id": self.project_id,
            "object_ref": self.object_ref,
            "object_revision_sha256": self.object_revision_sha256,
            "decision_sha256": self.decision_sha256,
            "effect": None if self.effect is None else self.effect.value,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "one_shot": self.one_shot,
            "evidence_ref": self.evidence_ref,
            "evidence_sha256": self.evidence_sha256,
        }


def classify_effect_gate(
    *,
    policy: StorageRetentionPolicyRevision,
    observation: StorageObjectObservationReceipt,
    decision: StorageDispositionDecisionReceipt,
    authorization: StorageEffectAuthorizationBinding,
    evaluated_at: str,
) -> EffectGateDecision:
    evaluated_at = _timestamp(evaluated_at, "evaluated_at")
    if authorization.contract_state in {ContractState.CANONICAL_REF_NOT_PROVIDED, ContractState.UNKNOWN}:
        return EffectGateDecision.UNKNOWN
    if authorization.contract_state is ContractState.MISMATCH:
        return EffectGateDecision.BLOCKED
    if decision.proposed_effect is None or decision.decision not in {LifecycleDecision.ARCHIVE_PROPOSED, LifecycleDecision.DELETE_PROPOSED}:
        return EffectGateDecision.BLOCKED
    try:
        verify_storage_record_hash(policy.to_dict())
        verify_storage_record_hash(observation.to_dict())
        verify_storage_record_hash(decision.to_dict())
    except ValueError:
        return EffectGateDecision.BLOCKED
    if (
        policy.project_id != decision.project_id
        or decision.policy_revision_sha256 != policy.policy_revision_sha256
        or decision.observation_sha256 != observation.observation_sha256
        or authorization.project_id != decision.project_id
        or authorization.object_ref != observation.object_ref
        or authorization.object_revision_sha256 != observation.object_revision_sha256
        or authorization.decision_sha256 != decision.decision_sha256
        or authorization.effect is not decision.proposed_effect
        or _seconds_between(observation.observed_at, evaluated_at) < 0
        or _seconds_between(observation.observed_at, evaluated_at) > policy.max_observation_age_seconds
        or _seconds_between(authorization.issued_at, evaluated_at) < 0  # type: ignore[arg-type]
        or _seconds_between(evaluated_at, authorization.expires_at) <= 0  # type: ignore[arg-type]
    ):
        return EffectGateDecision.BLOCKED
    return EffectGateDecision.READY_FOR_EXTERNAL_EFFECT


@dataclass(frozen=True)
class StorageEffectReceiptBinding:
    contract_state: ContractState
    receipt_ref: str | None
    receipt_sha256: str | None
    project_id: str | None
    object_ref: str | None
    object_revision_sha256: str | None
    decision_sha256: str | None
    authorization_sha256: str | None
    effect: StorageEffect | None
    result: EffectResult | None
    observed_at: str | None
    before_observation_sha256: str | None
    after_observation_sha256: str | None
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        state = _enum(ContractState, self.contract_state, "contract_state")
        object.__setattr__(self, "contract_state", state)
        bound_values = (
            self.receipt_ref, self.receipt_sha256, self.project_id, self.object_ref,
            self.object_revision_sha256, self.decision_sha256, self.authorization_sha256,
            self.effect, self.result, self.observed_at, self.before_observation_sha256,
        )
        if state is ContractState.BOUND_VERIFIED and any(value is None for value in bound_values):
            raise ValueError("BOUND_VERIFIED effect receipt fields are incomplete")
        if state is not ContractState.BOUND_VERIFIED:
            if any(value is not None for value in (*bound_values, self.after_observation_sha256)) or self.reason_codes:
                raise ValueError("unresolved effect receipt must not invent canonical fields")
            return
        for field in ("receipt_ref", "project_id", "object_ref"):
            object.__setattr__(self, field, _id(getattr(self, field), field))
        for field in (
            "receipt_sha256", "object_revision_sha256", "decision_sha256",
            "authorization_sha256", "before_observation_sha256",
        ):
            object.__setattr__(self, field, _digest(getattr(self, field), field))
        object.__setattr__(self, "effect", _enum(StorageEffect, self.effect, "effect"))
        object.__setattr__(self, "result", _enum(EffectResult, self.result, "result"))
        object.__setattr__(self, "observed_at", _timestamp(self.observed_at, "observed_at"))
        object.__setattr__(self, "reason_codes", _strict_reasons(self.reason_codes))
        if self.result in {EffectResult.VERIFIED_ARCHIVED, EffectResult.VERIFIED_DELETED}:
            if self.after_observation_sha256 is None:
                raise ValueError("verified effect requires after observation")
            object.__setattr__(self, "after_observation_sha256", _digest(self.after_observation_sha256, "after_observation_sha256"))
            if (self.effect is StorageEffect.ARCHIVE) != (self.result is EffectResult.VERIFIED_ARCHIVED):
                raise ValueError("effect/result mismatch")
        elif self.after_observation_sha256 is not None:
            raise ValueError("non-verified result cannot claim after observation")
        if self.result is EffectResult.UNKNOWN and "EXTERNAL_STATE_UNKNOWN" not in self.reason_codes:
            raise ValueError("UNKNOWN result requires EXTERNAL_STATE_UNKNOWN")

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "StorageEffectReceiptBinding",
            "contract_state": self.contract_state.value,
            "receipt_ref": self.receipt_ref,
            "receipt_sha256": self.receipt_sha256,
            "project_id": self.project_id,
            "object_ref": self.object_ref,
            "object_revision_sha256": self.object_revision_sha256,
            "decision_sha256": self.decision_sha256,
            "authorization_sha256": self.authorization_sha256,
            "effect": None if self.effect is None else self.effect.value,
            "result": None if self.result is None else self.result.value,
            "observed_at": self.observed_at,
            "before_observation_sha256": self.before_observation_sha256,
            "after_observation_sha256": self.after_observation_sha256,
            "reason_codes": list(self.reason_codes),
            "effect_performed_by_module": False,
            "automatic_retry_authorized": False,
        }


def verify_storage_record_hash(value: Mapping[str, Any]) -> None:
    if not isinstance(value, Mapping):
        raise ValueError("record must be an object")
    record_type = value.get("record_type")
    hash_field = {
        "StorageRetentionPolicyRevision": "policy_revision_sha256",
        "StorageObjectObservationReceipt": "observation_sha256",
        "StorageDispositionDecisionReceipt": "decision_sha256",
    }.get(record_type)
    if hash_field is None:
        raise ValueError("record_type is unsupported")
    supplied = _digest(value.get(hash_field), hash_field)
    body = dict(value)
    body.pop(hash_field)
    if _hash(body) != supplied:
        raise ValueError(f"{hash_field} mismatch")


def public_storage_projection(value: StorageDispositionDecisionReceipt | StorageEffectReceiptBinding) -> dict[str, Any]:
    if isinstance(value, StorageDispositionDecisionReceipt):
        return {
            "schema": SCHEMA_ID, "record_type": "StorageDispositionPublicProjection",
            "decision": value.decision.value, "proposed_effect": None if value.proposed_effect is None else value.proposed_effect.value,
            "reason_codes": list(value.reason_codes), "private_coordinate_suppressed": True,
            "effect_started": False,
        }
    return {
        "schema": SCHEMA_ID, "record_type": "StorageEffectPublicProjection",
        "contract_state": value.contract_state.value,
        "effect": None if value.effect is None else value.effect.value,
        "result": None if value.result is None else value.result.value,
        "reason_codes": list(value.reason_codes), "private_coordinate_suppressed": True,
        "effect_performed_by_module": False, "automatic_retry_authorized": False,
    }
