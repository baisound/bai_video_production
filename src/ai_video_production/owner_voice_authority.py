"""TASK-074 body-free Owner Voice authority/status contracts.

The records here are validation and handoff shapes.  They never mint a Human
authorization, operation ticket, private capability, or execution authority.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from types import MappingProxyType
from typing import Any, Mapping, Sequence
import unicodedata

from .owner_voice_private_reference import MEDIA_POLICY_SHA256
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .voice_profile_route_selection import ComputePreference, RouteMode


REGISTRY_AMENDMENT_CONTRACT_VERSION = "TASK074_OWNER_VOICE_REGISTRY_AMENDMENT_V1"
COMPLETION_CONTRACT_VERSION = "TASK074_OWNER_VOICE_AUTHORITY_COMPLETION_RECEIPT_V1"
PUBLIC_CONTRACT_VERSION = "TASK074_OWNER_VOICE_AUTHORITY_PUBLIC_V1"
EXECUTION_INPUT_CONTRACT_VERSION = "TASK074_TO_TASK075_EXECUTION_INPUT_V2"
HUMAN_ACTION_REGISTRY_VERSION = "HUMAN_ACTION_REGISTRY_V2"
OPERATION_PROFILE_REGISTRY_VERSION = "ACTION_REGISTRY_V2"

_REGISTRY_DOMAIN = b"TASK074_OWNER_VOICE_REGISTRY_AMENDMENT_V1\0"
_COMPLETION_DOMAIN = b"TASK074_OWNER_VOICE_AUTHORITY_COMPLETION_RECEIPT_V1\0"
_PUBLIC_DOMAIN = b"TASK074_OWNER_VOICE_AUTHORITY_PUBLIC_V1\0"
_EXECUTION_INPUT_DOMAIN = b"TASK074_TO_TASK075_EXECUTION_INPUT_V2\0"
_ZERO_SHOT_LINEAGE_DOMAIN = b"TASK074_TO_TASK075_ZERO_SHOT_COMPOSITE_LINEAGE_V2\0"
_CONSTRUCTION_TOKEN = object()
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9][A-Za-z0-9_-]*)*$")
_PUBLIC_ROUTE_KEY_RE = re.compile(r"^narration(?:\.[a-z0-9][a-z0-9_-]*){2,7}$")
_REASON_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,95}$")
_ALIAS_RE = re.compile(r"^[^\x00-\x1f\x7f]{1,80}$")
_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")


class CompletionClass(str, Enum):
    TASK074_IMPLEMENTATION_COMPLETE = "TASK074_IMPLEMENTATION_COMPLETE"
    P0V_OWNER_REFERENCE_VERIFIED = "P0V_OWNER_REFERENCE_VERIFIED"


class PersistenceState(str, Enum):
    DURABLE_VERIFIED = "DURABLE_VERIFIED"
    EPHEMERAL_NOT_EXECUTABLE = "EPHEMERAL_NOT_EXECUTABLE"


class PrivateReferenceState(str, Enum):
    PREPARED_VERIFIED = "PREPARED_VERIFIED"
    NOT_REQUIRED = "NOT_REQUIRED"
    REVOKED = "REVOKED"
    NOT_CONFIRMED = "NOT_CONFIRMED"


class PublicReferenceStatus(str, Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    PREPARATION_REQUIRED = "PREPARATION_REQUIRED"
    READY = "READY"
    REVOKED = "REVOKED"
    NOT_REQUIRED = "NOT_REQUIRED"
    NOT_CONFIRMED = "NOT_CONFIRMED"


class DurabilityVariant(str, Enum):
    DURABLE_SELECTION_HANDOFF_V1 = "DURABLE_SELECTION_HANDOFF_V1"
    TASK074_ONE_OPERATION_EXECUTION_HANDOFF_V1 = "TASK074_ONE_OPERATION_EXECUTION_HANDOFF_V1"


class RouteInputVariant(str, Enum):
    ZERO_SHOT_REFERENCE_INPUT_V2 = "ZERO_SHOT_REFERENCE_INPUT_V2"
    FINE_TUNED_MODEL_INPUT_V2 = "FINE_TUNED_MODEL_INPUT_V2"


_COMPLETION_FALSE_FLAGS = MappingProxyType(
    {
        "human_authorization_created": False,
        "operation_ticket_created": False,
        "execution_authorized": False,
        "model_downloaded": False,
        "model_loaded": False,
        "model_probed": False,
        "training_started": False,
        "inference_started": False,
        "playback_started": False,
        "wav_created": False,
        "asset_adopted": False,
        "timeline_mutated": False,
        "export_started": False,
        "private_body_present": False,
        "path_present": False,
        "secret_present": False,
        "production_eligible": False,
    }
)


_HUMAN_ACTION_ROWS = (
    {
        "action_code": "OWNER_VOICE_REFERENCE_PREPARE_V1",
        "purpose": "PRIVATE_REFERENCE_PAIR_PREPARATION",
        "effect_ceiling": "ONE_PREPARE_OPERATION",
    },
    {
        "action_code": "OWNER_VOICE_LOCAL_INFERENCE_V1",
        "purpose": "TASK075_LOCAL_SYNTHESIS",
        "effect_ceiling": "ONE_INFERENCE_OPERATION",
    },
    {
        "action_code": "OWNER_VOICE_LISTENING_DECISION_V1",
        "purpose": "TASK041_LISTENING_DECISION",
        "effect_ceiling": "ONE_DECISION",
    },
    {
        "action_code": "OWNER_VOICE_REGENERATE_V1",
        "purpose": "NEW_NARRATION_ATTEMPT",
        "effect_ceiling": "ONE_NEW_ATTEMPT",
    },
    {
        "action_code": "OWNER_VOICE_REFERENCE_REVOKE_V1",
        "purpose": "REFERENCE_CAPABILITY_INVALIDATION",
        "effect_ceiling": "ONE_REVOKE_TRANSITION",
    },
    {
        "action_code": "OWNER_VOICE_REFERENCE_PURGE_V1",
        "purpose": "EXACT_OWNED_DERIVATIVE_PURGE",
        "effect_ceiling": "ONE_BOUNDED_PURGE",
    },
)


_OPERATION_PROFILE_ROWS = (
    {"profile": "task074.owner_voice.reference.prepare", "consumer": "TASK-074"},
    {"profile": "task074.owner_voice.profile_route.select", "consumer": "TASK-074"},
    {"profile": "task075.owner_voice.local.inference", "consumer": "TASK-075"},
    {"profile": "task075.owner_voice.private.playback", "consumer": "TASK-075"},
    {"profile": "task041.owner_voice.listening.decision", "consumer": "TASK-041"},
    {"profile": "task014.owner_voice.regenerate", "consumer": "TASK-014"},
    {"profile": "task074.owner_voice.reference.revoke", "consumer": "TASK-074"},
    {"profile": "task074.owner_voice.reference.purge", "consumer": "TASK-074"},
)


def _exact(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} is invalid")
    if len(value) > 200:
        raise ValueError(f"{name} exceeds 200 characters")
    normalized = unicodedata.normalize("NFKC", value)
    if (
        any(token in normalized for token in ("/", "\\", ":"))
        or normalized.startswith(".")
        or normalized.endswith(".")
        or ".." in normalized
    ):
        raise ValueError(f"{name} must not be a host path or URI")
    if not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _public_route_key(value: Any) -> str:
    identifier = _identifier(value, "public_route_key")
    if not _PUBLIC_ROUTE_KEY_RE.fullmatch(identifier):
        raise ValueError("public_route_key is outside the closed narration inventory grammar")
    return identifier


def _reason_code(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("reason_code is invalid")
    normalized = unicodedata.normalize("NFKC", value)
    if any(token in normalized for token in ("/", "\\", ":", ".")):
        raise ValueError("reason_code must not contain a host path, URI, or file name")
    if not _REASON_CODE_RE.fullmatch(value):
        raise ValueError("reason_code is outside the closed public grammar")
    return value


def _alias(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ALIAS_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    normalized = unicodedata.normalize("NFKC", value)
    if any(token in normalized for token in ("/", "\\", ":", "..")):
        raise ValueError(f"{name} must not contain a host location")
    return value


def _digest(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} is invalid")
    return validate_sha256(value, field_name=name)


def _positive(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 2_147_483_647:
        raise ValueError(f"{name} must be a positive bounded integer")
    return value


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not _TIME_RE.fullmatch(value):
        raise ValueError(f"{name} must be canonical UTC")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be canonical UTC") from exc


def _enum(kind: type[Enum], value: Any, name: str) -> Enum:
    try:
        return kind(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


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


def _without(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    return {key: copy.deepcopy(item) for key, item in value.items() if key != field}


def _hash(domain: bytes, value: Mapping[str, Any], field: str) -> str:
    return sha256_bytes(domain + canonical_json_bytes(_without(value, field)))


@dataclass(frozen=True, slots=True, init=False)
class OwnerVoiceRegistryAmendmentProposal:
    """Closed TASK-071/072 amendment proposal, explicitly not producer authority."""

    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("registry amendment must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        amendment_id: str,
        design_receipt_sha256: str,
        created_at: str,
    ) -> "OwnerVoiceRegistryAmendmentProposal":
        body: dict[str, Any] = {
            "contract_version": REGISTRY_AMENDMENT_CONTRACT_VERSION,
            "record_type": "OwnerVoiceRegistryAmendmentProposal",
            "amendment_id": amendment_id,
            "human_action_registry_version": HUMAN_ACTION_REGISTRY_VERSION,
            "operation_profile_registry_version": OPERATION_PROFILE_REGISTRY_VERSION,
            "human_action_rows": copy.deepcopy(list(_HUMAN_ACTION_ROWS)),
            "operation_profile_rows": copy.deepcopy(list(_OPERATION_PROFILE_ROWS)),
            "design_receipt_sha256": design_receipt_sha256,
            "task071_producer_acceptance_state": "NOT_CONFIRMED",
            "task072_producer_acceptance_state": "NOT_CONFIRMED",
            "status_only": True,
            "authority_created": False,
            "operation_ticket_created": False,
            "effect_started": False,
            "created_at": created_at,
        }
        body["registry_amendment_sha256"] = sha256_bytes(_REGISTRY_DOMAIN + canonical_json_bytes(body))
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OwnerVoiceRegistryAmendmentProposal":
        fields = {
            "contract_version", "record_type", "amendment_id",
            "human_action_registry_version", "operation_profile_registry_version",
            "human_action_rows", "operation_profile_rows", "design_receipt_sha256",
            "task071_producer_acceptance_state", "task072_producer_acceptance_state",
            "status_only", "authority_created", "operation_ticket_created", "effect_started",
            "created_at", "registry_amendment_sha256",
        }
        _exact(value, fields, "OwnerVoiceRegistryAmendmentProposal")
        if value["contract_version"] != REGISTRY_AMENDMENT_CONTRACT_VERSION or value["record_type"] != "OwnerVoiceRegistryAmendmentProposal":
            raise ValueError("registry amendment identity/version is invalid")
        _identifier(value["amendment_id"], "amendment_id")
        if value["human_action_registry_version"] != HUMAN_ACTION_REGISTRY_VERSION or value["operation_profile_registry_version"] != OPERATION_PROFILE_REGISTRY_VERSION:
            raise ValueError("registry versions are outside the closed amendment")
        if value["human_action_rows"] != list(_HUMAN_ACTION_ROWS) or value["operation_profile_rows"] != list(_OPERATION_PROFILE_ROWS):
            raise ValueError("registry amendment rows are incomplete, reordered or unknown")
        _digest(value["design_receipt_sha256"], "design_receipt_sha256")
        if value["task071_producer_acceptance_state"] != "NOT_CONFIRMED" or value["task072_producer_acceptance_state"] != "NOT_CONFIRMED":
            raise ValueError("TASK074-B cannot claim producer acceptance")
        if value["status_only"] is not True:
            raise ValueError("registry amendment must remain status-only")
        for name in ("authority_created", "operation_ticket_created", "effect_started"):
            if value[name] is not False:
                raise ValueError(f"{name} must remain false")
        _timestamp(value["created_at"], "created_at")
        if value["registry_amendment_sha256"] != _hash(_REGISTRY_DOMAIN, value, "registry_amendment_sha256"):
            raise ValueError("registry amendment digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


def _validate_completion_route(value: Mapping[str, Any]) -> RouteMode:
    mode = _enum(RouteMode, value["route_mode"], "route_mode")
    private_state = _enum(PrivateReferenceState, value["private_reference_state"], "private_reference_state")
    reference_fields = (
        "reference_lifecycle_snapshot_sha256", "reference_preparation_receipt_sha256",
        "reference_capability_binding_sha256", "reference_media_policy_sha256",
        "reference_transcript_binding_receipt_sha256",
    )
    model_fields = ("model_candidate_revision_sha256", "model_candidate_currentness_sha256")
    for name in (*reference_fields, *model_fields):
        _digest(value[name], name, nullable=True)
    if mode is RouteMode.ZERO_SHOT_LOCAL:
        if any(value[name] is not None for name in model_fields):
            raise ValueError("zero-shot completion cannot carry ModelCandidate bindings")
        if private_state is PrivateReferenceState.NOT_REQUIRED:
            raise ValueError("zero-shot completion cannot mark reference NOT_REQUIRED")
        if private_state is PrivateReferenceState.PREPARED_VERIFIED:
            if any(value[name] is None for name in reference_fields):
                raise ValueError("prepared zero-shot completion requires every reference binding")
            if value["reference_media_policy_sha256"] != MEDIA_POLICY_SHA256:
                raise ValueError("prepared zero-shot completion has wrong media policy")
        elif any(value[name] is not None for name in reference_fields[1:]):
            raise ValueError("non-prepared zero-shot completion cannot retain executable reference bindings")
    else:
        if private_state is not PrivateReferenceState.NOT_REQUIRED:
            raise ValueError("fine-tuned completion requires reference NOT_REQUIRED")
        if any(value[name] is not None for name in reference_fields):
            raise ValueError("fine-tuned completion cannot carry reference bindings")
        if any(value[name] is None for name in model_fields):
            raise ValueError("fine-tuned completion requires exact ModelCandidate bindings")
    return mode  # type: ignore[return-value]


@dataclass(frozen=True, slots=True, init=False)
class Task074OwnerVoiceAuthorityCompletionReceipt:
    """Status-only completion receipt; never TASK-075 execution authority."""

    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("completion receipt must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        completion_id: str,
        completion_class: CompletionClass,
        project_id: str,
        project_manifest_revision_sha256: str,
        installed_startup_context_binding_sha256: str,
        voice_profile_id: str,
        voice_profile_revision: int,
        voice_profile_revision_sha256: str,
        consent_current_evaluation_sha256: str,
        route_mode: RouteMode,
        route_selection_revision: int,
        route_selection_sha256: str,
        route_selection_store_receipt_sha256: str | None,
        reference_lifecycle_snapshot_sha256: str | None,
        reference_preparation_receipt_sha256: str | None,
        reference_capability_binding_sha256: str | None,
        reference_media_policy_sha256: str | None,
        reference_transcript_binding_receipt_sha256: str | None,
        model_candidate_revision_sha256: str | None,
        model_candidate_currentness_sha256: str | None,
        human_action_registry_receipt_sha256: str,
        operation_profile_registry_receipt_sha256: str,
        persistence_state: PersistenceState,
        private_reference_state: PrivateReferenceState,
        owner_reference_verified: bool,
        issued_at: str,
        expires_at: str,
    ) -> "Task074OwnerVoiceAuthorityCompletionReceipt":
        if completion_class is not CompletionClass.TASK074_IMPLEMENTATION_COMPLETE:
            raise ValueError(
                "TASK074-B fixture factory cannot claim P0V Owner reference verification"
            )
        body: dict[str, Any] = {
            "contract_version": COMPLETION_CONTRACT_VERSION,
            "record_type": "Task074OwnerVoiceAuthorityCompletionReceipt",
            "task_id": "TASK-074",
            "completion_id": completion_id,
            "completion_class": completion_class.value if isinstance(completion_class, CompletionClass) else completion_class,
            "project_id": project_id,
            "project_manifest_revision_sha256": project_manifest_revision_sha256,
            "installed_startup_context_binding_sha256": installed_startup_context_binding_sha256,
            "voice_profile_id": voice_profile_id,
            "voice_profile_revision": voice_profile_revision,
            "voice_profile_revision_sha256": voice_profile_revision_sha256,
            "consent_current_evaluation_sha256": consent_current_evaluation_sha256,
            "route_mode": route_mode.value if isinstance(route_mode, RouteMode) else route_mode,
            "route_selection_revision": route_selection_revision,
            "route_selection_sha256": route_selection_sha256,
            "route_selection_store_receipt_sha256": route_selection_store_receipt_sha256,
            "reference_lifecycle_snapshot_sha256": reference_lifecycle_snapshot_sha256,
            "reference_preparation_receipt_sha256": reference_preparation_receipt_sha256,
            "reference_capability_binding_sha256": reference_capability_binding_sha256,
            "reference_media_policy_sha256": reference_media_policy_sha256,
            "reference_transcript_binding_receipt_sha256": reference_transcript_binding_receipt_sha256,
            "model_candidate_revision_sha256": model_candidate_revision_sha256,
            "model_candidate_currentness_sha256": model_candidate_currentness_sha256,
            "human_action_registry_version": HUMAN_ACTION_REGISTRY_VERSION,
            "operation_profile_registry_version": OPERATION_PROFILE_REGISTRY_VERSION,
            "human_action_registry_receipt_sha256": human_action_registry_receipt_sha256,
            "operation_profile_registry_receipt_sha256": operation_profile_registry_receipt_sha256,
            "persistence_state": persistence_state.value if isinstance(persistence_state, PersistenceState) else persistence_state,
            "private_reference_state": private_reference_state.value if isinstance(private_reference_state, PrivateReferenceState) else private_reference_state,
            "receipt_authority_kind": "STATUS_ONLY",
            "owner_reference_verified": owner_reference_verified,
            "producer_binding_state": "NOT_BOUND",
            "fixture_only": True,
            "canonical_producer_readback": False,
            "execution_ready": False,
            "task046_owner_acceptance_sha256": None,
            "task071_owner_acceptance_sha256": None,
            "task072_owner_acceptance_sha256": None,
            "task075_owner_acceptance_sha256": None,
            "task076_owner_acceptance_sha256": None,
            "issued_at": issued_at,
            "expires_at": expires_at,
            **dict(_COMPLETION_FALSE_FLAGS),
        }
        body["completion_sha256"] = sha256_bytes(_COMPLETION_DOMAIN + canonical_json_bytes(body))
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Task074OwnerVoiceAuthorityCompletionReceipt":
        fields = {
            "contract_version", "record_type", "task_id", "completion_id", "completion_class",
            "project_id", "project_manifest_revision_sha256",
            "installed_startup_context_binding_sha256", "voice_profile_id",
            "voice_profile_revision", "voice_profile_revision_sha256",
            "consent_current_evaluation_sha256", "route_mode", "route_selection_revision",
            "route_selection_sha256", "route_selection_store_receipt_sha256",
            "reference_lifecycle_snapshot_sha256", "reference_preparation_receipt_sha256",
            "reference_capability_binding_sha256", "reference_media_policy_sha256",
            "reference_transcript_binding_receipt_sha256", "model_candidate_revision_sha256",
            "model_candidate_currentness_sha256", "human_action_registry_version",
            "operation_profile_registry_version", "human_action_registry_receipt_sha256",
            "operation_profile_registry_receipt_sha256", "persistence_state",
            "private_reference_state", "receipt_authority_kind", "owner_reference_verified",
            "producer_binding_state", "fixture_only", "canonical_producer_readback",
            "execution_ready", "task046_owner_acceptance_sha256",
            "task071_owner_acceptance_sha256", "task072_owner_acceptance_sha256",
            "task075_owner_acceptance_sha256", "task076_owner_acceptance_sha256",
            "issued_at", "expires_at", *set(_COMPLETION_FALSE_FLAGS), "completion_sha256",
        }
        _exact(value, fields, "Task074OwnerVoiceAuthorityCompletionReceipt")
        if (
            value["contract_version"] != COMPLETION_CONTRACT_VERSION
            or value["record_type"] != "Task074OwnerVoiceAuthorityCompletionReceipt"
            or value["task_id"] != "TASK-074"
        ):
            raise ValueError("completion receipt identity/version is invalid")
        for name in ("completion_id", "project_id", "voice_profile_id"):
            _identifier(value[name], name)
        for name in (
            "project_manifest_revision_sha256", "installed_startup_context_binding_sha256",
            "voice_profile_revision_sha256", "consent_current_evaluation_sha256",
            "route_selection_sha256", "human_action_registry_receipt_sha256",
            "operation_profile_registry_receipt_sha256",
        ):
            _digest(value[name], name)
        _positive(value["voice_profile_revision"], "voice_profile_revision")
        _positive(value["route_selection_revision"], "route_selection_revision")
        _digest(value["route_selection_store_receipt_sha256"], "route_selection_store_receipt_sha256", nullable=True)
        mode = _validate_completion_route(value)
        completion_class = _enum(CompletionClass, value["completion_class"], "completion_class")
        persistence = _enum(PersistenceState, value["persistence_state"], "persistence_state")
        if value["human_action_registry_version"] != HUMAN_ACTION_REGISTRY_VERSION or value["operation_profile_registry_version"] != OPERATION_PROFILE_REGISTRY_VERSION:
            raise ValueError("completion receipt registry versions are invalid")
        if value["receipt_authority_kind"] != "STATUS_ONLY":
            raise ValueError("completion receipt cannot be an authority bearer")
        for name in (
            "task046_owner_acceptance_sha256", "task071_owner_acceptance_sha256",
            "task072_owner_acceptance_sha256", "task075_owner_acceptance_sha256",
            "task076_owner_acceptance_sha256",
        ):
            _digest(value[name], name, nullable=True)
        if any(
            value[name] is not None
            for name in (
                "task046_owner_acceptance_sha256", "task071_owner_acceptance_sha256",
                "task072_owner_acceptance_sha256", "task075_owner_acceptance_sha256",
                "task076_owner_acceptance_sha256",
            )
        ):
            raise ValueError("TASK074-B fixture cannot claim canonical producer acceptance")
        if (
            value["producer_binding_state"] != "NOT_BOUND"
            or value["fixture_only"] is not True
            or value["canonical_producer_readback"] is not False
            or value["execution_ready"] is not False
        ):
            raise ValueError("TASK074-B completion must remain a producer-unbound fixture")
        if not isinstance(value["owner_reference_verified"], bool):
            raise ValueError("owner_reference_verified must be boolean")
        if completion_class is CompletionClass.TASK074_IMPLEMENTATION_COMPLETE:
            if value["owner_reference_verified"] is not False:
                raise ValueError("implementation completion cannot claim real Owner reference verification")
        else:
            raise ValueError("P0V Owner reference verification requires the separate TASK074-D Human Gate")
        if persistence is PersistenceState.DURABLE_VERIFIED:
            if value["route_selection_store_receipt_sha256"] is None:
                raise ValueError("durable completion requires the exact store receipt")
        elif value["route_selection_store_receipt_sha256"] is not None:
            raise ValueError("ephemeral completion cannot carry a store receipt")
        issued = _timestamp(value["issued_at"], "issued_at")
        expires = _timestamp(value["expires_at"], "expires_at")
        if expires <= issued:
            raise ValueError("completion expiry must follow issue time")
        for name, expected in _COMPLETION_FALSE_FLAGS.items():
            if value[name] is not expected:
                raise ValueError(f"{name} must remain false")
        if value["completion_sha256"] != _hash(_COMPLETION_DOMAIN, value, "completion_sha256"):
            raise ValueError("completion receipt digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


@dataclass(frozen=True, slots=True, init=False)
class OwnerVoiceAuthorityPublicProjection:
    """Strict allowlist projection.  It contains no private-derived digest."""

    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("public projection must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        route_label: str,
        public_route_key: str,
        route_mode: RouteMode,
        compute_preference: ComputePreference,
        saved: bool,
        reference_status: PublicReferenceStatus,
        runnable_candidate: bool,
        reason_codes: Sequence[str],
        profile_display_alias: str,
    ) -> "OwnerVoiceAuthorityPublicProjection":
        body: dict[str, Any] = {
            "contract_version": PUBLIC_CONTRACT_VERSION,
            "record_type": "OwnerVoiceAuthorityPublicProjection",
            "route_label": route_label,
            "public_route_key": public_route_key,
            "route_mode": route_mode.value if isinstance(route_mode, RouteMode) else route_mode,
            "compute_preference": compute_preference.value if isinstance(compute_preference, ComputePreference) else compute_preference,
            "saved": saved,
            "reference_status": reference_status.value if isinstance(reference_status, PublicReferenceStatus) else reference_status,
            "runnable_candidate": runnable_candidate,
            "reason_codes": sorted(set(reason_codes)),
            "profile_display_alias": profile_display_alias,
            "human_action_registry_version": HUMAN_ACTION_REGISTRY_VERSION,
            "operation_profile_registry_version": OPERATION_PROFILE_REGISTRY_VERSION,
            "authority_created": False,
            "execution_authorized": False,
            "private_body_present": False,
            "path_present": False,
        }
        body["public_projection_sha256"] = sha256_bytes(_PUBLIC_DOMAIN + canonical_json_bytes(body))
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OwnerVoiceAuthorityPublicProjection":
        fields = {
            "contract_version", "record_type", "route_label", "public_route_key",
            "route_mode", "compute_preference", "saved", "reference_status",
            "runnable_candidate", "reason_codes", "profile_display_alias",
            "human_action_registry_version", "operation_profile_registry_version",
            "authority_created", "execution_authorized", "private_body_present",
            "path_present", "public_projection_sha256",
        }
        _exact(value, fields, "OwnerVoiceAuthorityPublicProjection")
        if value["contract_version"] != PUBLIC_CONTRACT_VERSION or value["record_type"] != "OwnerVoiceAuthorityPublicProjection":
            raise ValueError("public projection identity/version is invalid")
        _alias(value["route_label"], "route_label")
        _public_route_key(value["public_route_key"])
        mode = _enum(RouteMode, value["route_mode"], "route_mode")
        _enum(ComputePreference, value["compute_preference"], "compute_preference")
        status = _enum(PublicReferenceStatus, value["reference_status"], "reference_status")
        if not isinstance(value["saved"], bool) or not isinstance(value["runnable_candidate"], bool):
            raise ValueError("public saved/runnable flags must be boolean")
        reasons = value["reason_codes"]
        if not isinstance(reasons, list) or len(reasons) > 64 or reasons != sorted(set(reasons)):
            raise ValueError("public reason codes must be unique canonical order with at most 64 items")
        for reason in reasons:
            _reason_code(reason)
        expected_ready_status = (
            PublicReferenceStatus.READY
            if mode is RouteMode.ZERO_SHOT_LOCAL
            else PublicReferenceStatus.NOT_REQUIRED
        )
        if mode is RouteMode.ZERO_SHOT_LOCAL and status is PublicReferenceStatus.NOT_REQUIRED:
            raise ValueError("zero-shot public projection cannot mark reference NOT_REQUIRED")
        if mode is RouteMode.FINE_TUNED_LOCAL and status is not PublicReferenceStatus.NOT_REQUIRED:
            raise ValueError("fine-tuned public projection requires reference NOT_REQUIRED")
        if value["runnable_candidate"]:
            if value["saved"] is not True or status is not expected_ready_status or reasons:
                raise ValueError("runnable public projection requires saved ready state without reasons")
        elif not reasons:
            raise ValueError("non-runnable public projection requires at least one reason code")
        if status is not expected_ready_status and value["runnable_candidate"] is not False:
            raise ValueError("blocked public reference status cannot be runnable")
        _alias(value["profile_display_alias"], "profile_display_alias")
        if value["human_action_registry_version"] != HUMAN_ACTION_REGISTRY_VERSION or value["operation_profile_registry_version"] != OPERATION_PROFILE_REGISTRY_VERSION:
            raise ValueError("public registry versions are invalid")
        for name in ("authority_created", "execution_authorized", "private_body_present", "path_present"):
            if value[name] is not False:
                raise ValueError(f"{name} must remain false")
        if value["public_projection_sha256"] != _hash(_PUBLIC_DOMAIN, value, "public_projection_sha256"):
            raise ValueError("public projection digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


_ZERO_SHOT_FIELDS = {
    "variant", "reference_lifecycle_snapshot_sha256", "pair_ledger_sha256",
    "reference_capability_v2_binding_sha256", "media_policy_sha256",
    "transcript_binding_receipt_sha256", "reference_roles",
    "worker_delegation_sha256", "task072_begin_readback_sha256",
    "begin_nonce_binding_sha256", "task076_worker_process_readback_sha256",
    "child_process_binding_sha256", "lease_state", "model_candidate_revision_sha256",
    "model_candidate_currentness_sha256", "installed_route_binding_sha256",
    "model_license_evidence_sha256", "semantic_operation_key", "owner_operation_id",
    "reference_domain_snapshot_sha256", "reference_version_fence_sha256",
    "current_v2_lease_identity_sha256", "attachment_sha256",
    "task076_external_binding_slot_sha256", "task076_armed_vector_sha256",
    "task076_bootstrap_waiting_readback_sha256", "task076_job_object_custody_readback_sha256",
    "task076_external_input_bound_readback_sha256",
    "task076_external_input_validated_readback_sha256",
    "producer_binding_state", "executable", "composite_child_lineage_sha256",
}


def _zero_shot_lineage_sha256(value: Mapping[str, Any]) -> str:
    return sha256_bytes(
        _ZERO_SHOT_LINEAGE_DOMAIN
        + canonical_json_bytes(
            {key: copy.deepcopy(item) for key, item in value.items() if key != "composite_child_lineage_sha256"}
        )
    )


def _validate_zero_shot_input(value: Mapping[str, Any]) -> None:
    _exact(value, _ZERO_SHOT_FIELDS, "ZERO_SHOT_REFERENCE_INPUT_V2")
    if value["variant"] != RouteInputVariant.ZERO_SHOT_REFERENCE_INPUT_V2.value:
        raise ValueError("zero-shot input discriminator is invalid")
    for name in ("semantic_operation_key", "owner_operation_id"):
        _identifier(value[name], name)
    for name in (
        "reference_lifecycle_snapshot_sha256", "pair_ledger_sha256",
        "reference_capability_v2_binding_sha256", "transcript_binding_receipt_sha256",
        "worker_delegation_sha256", "task072_begin_readback_sha256",
        "begin_nonce_binding_sha256", "task076_worker_process_readback_sha256",
        "child_process_binding_sha256", "reference_domain_snapshot_sha256",
        "reference_version_fence_sha256", "current_v2_lease_identity_sha256",
        "attachment_sha256", "task076_external_binding_slot_sha256",
        "task076_armed_vector_sha256", "task076_bootstrap_waiting_readback_sha256",
        "task076_job_object_custody_readback_sha256",
        "task076_external_input_bound_readback_sha256",
        "task076_external_input_validated_readback_sha256",
    ):
        _digest(value[name], name)
    identities = [
        value["attachment_sha256"], value["begin_nonce_binding_sha256"],
        value["child_process_binding_sha256"], value["task076_armed_vector_sha256"],
        value["task076_bootstrap_waiting_readback_sha256"],
    ]
    if len(set(identities)) != len(identities):
        raise ValueError("zero-shot attachment/begin/child/vector identities must be independent")
    if value["media_policy_sha256"] != MEDIA_POLICY_SHA256:
        raise ValueError("zero-shot input media policy mismatch")
    if value["reference_roles"] != ["REFERENCE_AUDIO_READ_HANDLE", "REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE"]:
        raise ValueError("zero-shot input requires the exact ordered two-role set")
    if value["lease_state"] != "CHILD_PAIR_READY":
        raise ValueError("zero-shot input requires exact CHILD_PAIR_READY")
    for name in (
        "model_candidate_revision_sha256", "model_candidate_currentness_sha256",
        "installed_route_binding_sha256", "model_license_evidence_sha256",
    ):
        if value[name] is not None:
            raise ValueError("zero-shot input cannot carry ModelCandidate fields")
    if value["producer_binding_state"] != "NOT_BOUND" or value["executable"] is not False:
        raise ValueError("TASK074-B zero-shot fixture must remain producer-unbound and non-executable")
    if value["composite_child_lineage_sha256"] != _zero_shot_lineage_sha256(value):
        raise ValueError("zero-shot composite child lineage digest mismatch")


def _validate_fine_tuned_input(value: Mapping[str, Any]) -> None:
    _exact(value, _ZERO_SHOT_FIELDS, "FINE_TUNED_MODEL_INPUT_V2")
    if value["variant"] != RouteInputVariant.FINE_TUNED_MODEL_INPUT_V2.value:
        raise ValueError("fine-tuned input discriminator is invalid")
    _identifier(value["semantic_operation_key"], "semantic_operation_key")
    if value["owner_operation_id"] is not None:
        raise ValueError("fine-tuned input cannot carry Owner reference operation identity")
    for name in (
        "model_candidate_revision_sha256", "model_candidate_currentness_sha256",
        "installed_route_binding_sha256", "model_license_evidence_sha256",
    ):
        _digest(value[name], name)
    for name in (
        "reference_lifecycle_snapshot_sha256", "pair_ledger_sha256",
        "reference_capability_v2_binding_sha256", "media_policy_sha256",
        "transcript_binding_receipt_sha256", "worker_delegation_sha256",
        "task072_begin_readback_sha256", "begin_nonce_binding_sha256",
        "task076_worker_process_readback_sha256", "child_process_binding_sha256",
        "lease_state", "reference_domain_snapshot_sha256", "reference_version_fence_sha256",
        "current_v2_lease_identity_sha256", "attachment_sha256",
        "task076_external_binding_slot_sha256", "task076_armed_vector_sha256",
        "task076_bootstrap_waiting_readback_sha256", "task076_job_object_custody_readback_sha256",
        "task076_external_input_bound_readback_sha256",
        "task076_external_input_validated_readback_sha256", "composite_child_lineage_sha256",
    ):
        if value[name] is not None:
            raise ValueError("fine-tuned input cannot carry reference/delegation fields")
    if value["reference_roles"] != []:
        raise ValueError("fine-tuned input reference role set must be empty")
    if value["producer_binding_state"] != "NOT_BOUND" or value["executable"] is not False:
        raise ValueError("TASK074-B fine-tuned fixture must remain producer-unbound and non-executable")


@dataclass(frozen=True, slots=True, init=False)
class Task074ToTask075ExecutionInputV2:
    """Body-free ABI mapping; a mapping cannot reconstruct live authority."""

    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("execution input must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        handoff_id: str,
        durability_variant: DurabilityVariant,
        route_mode: RouteMode,
        semantic_operation_key: str,
        aggregate_currentness_lease_binding_sha256: str,
        expected_product_build_sha256: str,
        worker_protocol_version: str,
        durable_completion_receipt_sha256: str | None,
        durable_selection_sha256: str | None,
        durable_currentness_sha256: str | None,
        live_route_plan_sha256: str | None,
        live_route_plan_lease_sha256: str | None,
        task072_ticket_sha256: str | None,
        live_currentness_fingerprint_sha256: str | None,
        zero_shot_input: Mapping[str, Any] | None,
        fine_tuned_input: Mapping[str, Any] | None,
        task046_owner_acceptance_sha256: str | None,
        task072_owner_acceptance_sha256: str | None,
        task075_owner_acceptance_sha256: str | None,
        task076_owner_acceptance_sha256: str | None,
        created_at: str,
    ) -> "Task074ToTask075ExecutionInputV2":
        zero_value = None if zero_shot_input is None else copy.deepcopy(dict(zero_shot_input))
        if zero_value is not None:
            zero_value["composite_child_lineage_sha256"] = _zero_shot_lineage_sha256(zero_value)
        body: dict[str, Any] = {
            "contract_version": EXECUTION_INPUT_CONTRACT_VERSION,
            "record_type": "Task074ToTask075ExecutionInputV2",
            "handoff_id": handoff_id,
            "durability_variant": durability_variant.value if isinstance(durability_variant, DurabilityVariant) else durability_variant,
            "route_mode": route_mode.value if isinstance(route_mode, RouteMode) else route_mode,
            "semantic_operation_key": semantic_operation_key,
            "aggregate_currentness_lease_binding_sha256": aggregate_currentness_lease_binding_sha256,
            "expected_consumer": "TASK-075",
            "expected_product_build_sha256": expected_product_build_sha256,
            "worker_protocol_version": worker_protocol_version,
            "durable_completion_receipt_sha256": durable_completion_receipt_sha256,
            "durable_selection_sha256": durable_selection_sha256,
            "durable_currentness_sha256": durable_currentness_sha256,
            "live_route_plan_sha256": live_route_plan_sha256,
            "live_route_plan_lease_sha256": live_route_plan_lease_sha256,
            "task072_ticket_sha256": task072_ticket_sha256,
            "live_currentness_fingerprint_sha256": live_currentness_fingerprint_sha256,
            "zero_shot_input": zero_value,
            "fine_tuned_input": None if fine_tuned_input is None else copy.deepcopy(dict(fine_tuned_input)),
            "task046_owner_acceptance_sha256": task046_owner_acceptance_sha256,
            "task072_owner_acceptance_sha256": task072_owner_acceptance_sha256,
            "task075_owner_acceptance_sha256": task075_owner_acceptance_sha256,
            "task076_owner_acceptance_sha256": task076_owner_acceptance_sha256,
            "producer_binding_state": "NOT_BOUND",
            "fixture_only": True,
            "execution_ready": False,
            "g11_structurally_complete": False,
            "authority_created": False,
            "execution_authorized": False,
            "body_present": False,
            "path_present": False,
            "secret_present": False,
            "created_at": created_at,
        }
        body["execution_input_sha256"] = sha256_bytes(_EXECUTION_INPUT_DOMAIN + canonical_json_bytes(body))
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Task074ToTask075ExecutionInputV2":
        fields = {
            "contract_version", "record_type", "handoff_id", "durability_variant", "route_mode",
            "semantic_operation_key", "aggregate_currentness_lease_binding_sha256",
            "expected_consumer", "expected_product_build_sha256", "worker_protocol_version",
            "durable_completion_receipt_sha256", "durable_selection_sha256",
            "durable_currentness_sha256", "live_route_plan_sha256",
            "live_route_plan_lease_sha256", "task072_ticket_sha256",
            "live_currentness_fingerprint_sha256", "zero_shot_input", "fine_tuned_input",
            "task046_owner_acceptance_sha256", "task072_owner_acceptance_sha256",
            "task075_owner_acceptance_sha256", "task076_owner_acceptance_sha256",
            "producer_binding_state", "fixture_only", "execution_ready",
            "g11_structurally_complete", "authority_created",
            "execution_authorized", "body_present", "path_present", "secret_present",
            "created_at", "execution_input_sha256",
        }
        _exact(value, fields, "Task074ToTask075ExecutionInputV2")
        if value["contract_version"] != EXECUTION_INPUT_CONTRACT_VERSION or value["record_type"] != "Task074ToTask075ExecutionInputV2":
            raise ValueError("execution input identity/version is invalid")
        for name in ("handoff_id", "semantic_operation_key", "worker_protocol_version"):
            _identifier(value[name], name)
        if value["expected_consumer"] != "TASK-075":
            raise ValueError("execution input consumer is not TASK-075")
        for name in (
            "aggregate_currentness_lease_binding_sha256", "expected_product_build_sha256",
        ):
            _digest(value[name], name)
        durability = _enum(DurabilityVariant, value["durability_variant"], "durability_variant")
        mode = _enum(RouteMode, value["route_mode"], "route_mode")
        durable_fields = (
            "durable_completion_receipt_sha256", "durable_selection_sha256",
            "durable_currentness_sha256",
        )
        live_fields = (
            "live_route_plan_sha256", "live_route_plan_lease_sha256", "task072_ticket_sha256",
            "live_currentness_fingerprint_sha256",
        )
        for name in (
            *durable_fields, *live_fields, "task046_owner_acceptance_sha256",
            "task072_owner_acceptance_sha256", "task075_owner_acceptance_sha256",
            "task076_owner_acceptance_sha256",
        ):
            _digest(value[name], name, nullable=True)
        if durability is DurabilityVariant.DURABLE_SELECTION_HANDOFF_V1:
            if any(value[name] is None for name in durable_fields) or any(value[name] is not None for name in live_fields):
                raise ValueError("durable handoff outer union is incomplete or mixed")
        else:
            if any(value[name] is None for name in live_fields) or any(value[name] is not None for name in durable_fields):
                raise ValueError("live handoff outer union is incomplete or mixed")
        if mode is RouteMode.ZERO_SHOT_LOCAL:
            if value["zero_shot_input"] is None or value["fine_tuned_input"] is not None:
                raise ValueError("zero-shot inner route union is incomplete or mixed")
            _validate_zero_shot_input(value["zero_shot_input"])
            if value["zero_shot_input"]["semantic_operation_key"] != value["semantic_operation_key"]:
                raise ValueError("zero-shot composite lineage semantic operation mismatch")
        else:
            if value["fine_tuned_input"] is None or value["zero_shot_input"] is not None:
                raise ValueError("fine-tuned inner route union is incomplete or mixed")
            _validate_fine_tuned_input(value["fine_tuned_input"])
            if value["fine_tuned_input"]["semantic_operation_key"] != value["semantic_operation_key"]:
                raise ValueError("fine-tuned semantic operation mismatch")
            if value["task072_owner_acceptance_sha256"] is not None or value["task076_owner_acceptance_sha256"] is not None:
                raise ValueError("fine-tuned input cannot carry Owner-voice child producer acceptances")
        if any(
            value[name] is not None
            for name in (
                "task046_owner_acceptance_sha256", "task072_owner_acceptance_sha256",
                "task075_owner_acceptance_sha256", "task076_owner_acceptance_sha256",
            )
        ):
            raise ValueError("TASK074-B fixture cannot claim canonical producer Owner acceptance")
        if (
            value["producer_binding_state"] != "NOT_BOUND"
            or value["fixture_only"] is not True
            or value["execution_ready"] is not False
            or value["g11_structurally_complete"] is not False
        ):
            raise ValueError("TASK074-B execution input must remain producer-unbound fixture evidence")
        for name in ("authority_created", "execution_authorized", "body_present", "path_present", "secret_present"):
            if value[name] is not False:
                raise ValueError(f"{name} must remain false")
        _timestamp(value["created_at"], "created_at")
        if value["execution_input_sha256"] != _hash(_EXECUTION_INPUT_DOMAIN, value, "execution_input_sha256"):
            raise ValueError("execution input digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


__all__ = [
    "CompletionClass",
    "DurabilityVariant",
    "HUMAN_ACTION_REGISTRY_VERSION",
    "OPERATION_PROFILE_REGISTRY_VERSION",
    "OwnerVoiceAuthorityPublicProjection",
    "OwnerVoiceRegistryAmendmentProposal",
    "PersistenceState",
    "PrivateReferenceState",
    "PublicReferenceStatus",
    "RouteInputVariant",
    "Task074OwnerVoiceAuthorityCompletionReceipt",
    "Task074ToTask075ExecutionInputV2",
]
