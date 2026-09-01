"""TASK-074 body-free Owner Voice route-selection contracts.

This module validates immutable metadata only.  It does not own a Project
database, open media, load a model, issue Human authority, or start execution.
The real store adapter is intentionally outside TASK074-B.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from types import MappingProxyType
from typing import Any, Mapping, Protocol
import unicodedata

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SELECTION_CONTRACT_VERSION = "VOICE_PROFILE_ROUTE_SELECTION_V1"
EPHEMERAL_CONTRACT_VERSION = "VOICE_PROFILE_ROUTE_SELECTION_EPHEMERAL_FIXTURE_V1"
CURRENTNESS_CONTRACT_VERSION = "VOICE_ROUTE_SELECTION_CURRENTNESS_EVALUATION_V1"
CAS_REQUEST_CONTRACT_VERSION = "VOICE_ROUTE_SELECTION_CAS_REQUEST_V1"
CAS_READBACK_CONTRACT_VERSION = "VOICE_ROUTE_SELECTION_CAS_READBACK_V1"

_SELECTION_DOMAIN = b"TASK074_VOICE_PROFILE_ROUTE_SELECTION_V1\0"
_EPHEMERAL_DOMAIN = b"TASK074_VOICE_PROFILE_ROUTE_SELECTION_EPHEMERAL_FIXTURE_V1\0"
_CURRENTNESS_DOMAIN = b"TASK074_VOICE_ROUTE_SELECTION_CURRENTNESS_EVALUATION_V1\0"
_CURRENTNESS_READBACK_SET_DOMAIN = b"TASK074_VOICE_ROUTE_SELECTION_CURRENTNESS_READBACK_SET_V1\0"
_CAS_REQUEST_DOMAIN = b"TASK074_VOICE_ROUTE_SELECTION_CAS_REQUEST_V1\0"
_CAS_READBACK_DOMAIN = b"TASK074_VOICE_ROUTE_SELECTION_CAS_READBACK_V1\0"
_CONSTRUCTION_TOKEN = object()
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9][A-Za-z0-9_-]*)*$")
_PUBLIC_ROUTE_KEY_RE = re.compile(r"^narration(?:\.[a-z0-9][a-z0-9_-]*){2,7}$")
_REASON_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,95}$")
_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")


class RouteMode(str, Enum):
    ZERO_SHOT_LOCAL = "ZERO_SHOT_LOCAL"
    FINE_TUNED_LOCAL = "FINE_TUNED_LOCAL"


class SourceRequirement(str, Enum):
    PRIVATE_REFERENCE_REQUIRED = "PRIVATE_REFERENCE_REQUIRED"
    MODEL_CANDIDATE_REQUIRED = "MODEL_CANDIDATE_REQUIRED"


class ComputePreference(str, Enum):
    AUTO = "AUTO"
    CPU = "CPU"
    GPU = "GPU"


class ProducerBindingState(str, Enum):
    CURRENT = "CURRENT"
    MISSING = "MISSING"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    UNAPPROVED = "UNAPPROVED"
    NOT_CONFIRMED = "NOT_CONFIRMED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class CurrentnessResult(str, Enum):
    RUNNABLE = "RUNNABLE"
    NOT_RUNNABLE = "NOT_RUNNABLE"
    NOT_CONFIRMED = "NOT_CONFIRMED"


class CASOutcome(str, Enum):
    COMMITTED = "COMMITTED"
    CONFLICT = "CONFLICT"
    NOT_CONFIRMED = "NOT_CONFIRMED"


_FALSE_BOUNDARY_FLAGS = MappingProxyType(
    {
        "authority_created": False,
        "runtime_loaded": False,
        "model_downloaded": False,
        "model_probed": False,
        "training_started": False,
        "inference_started": False,
        "audio_body_persisted": False,
        "path_persisted": False,
    }
)

_FIXTURE_READBACK_BOUNDARY = MappingProxyType(
    {
        "producer_binding_state": "NOT_BOUND",
        "fixture_only": True,
        "canonical_producer_acceptance_state": "NOT_CONFIRMED",
        "canonical_producer_readback": False,
        "execution_ready": False,
    }
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


def _validate_false_flags(value: Mapping[str, Any]) -> None:
    for key, expected in _FALSE_BOUNDARY_FLAGS.items():
        if value[key] is not expected:
            raise ValueError(f"{key} must remain false")


def _validate_route_union(value: Mapping[str, Any]) -> tuple[RouteMode, SourceRequirement]:
    mode = _enum(RouteMode, value["route_mode"], "route_mode")
    requirement = _enum(SourceRequirement, value["source_requirement"], "source_requirement")
    model_revision = _digest(
        value["model_candidate_revision_sha256"],
        "model_candidate_revision_sha256",
        nullable=True,
    )
    model_currentness = _digest(
        value["model_candidate_currentness_sha256"],
        "model_candidate_currentness_sha256",
        nullable=True,
    )
    if mode is RouteMode.ZERO_SHOT_LOCAL:
        if requirement is not SourceRequirement.PRIVATE_REFERENCE_REQUIRED:
            raise ValueError("zero-shot route requires PRIVATE_REFERENCE_REQUIRED")
        if model_revision is not None or model_currentness is not None:
            raise ValueError("zero-shot route cannot carry ModelCandidate fields")
    else:
        if requirement is not SourceRequirement.MODEL_CANDIDATE_REQUIRED:
            raise ValueError("fine-tuned route requires MODEL_CANDIDATE_REQUIRED")
        if model_revision is None or model_currentness is None:
            raise ValueError("fine-tuned route requires exact ModelCandidate bindings")
    return mode, requirement  # type: ignore[return-value]


@dataclass(frozen=True, slots=True, init=False)
class VoiceProfileRouteSelection:
    """One immutable durable selection revision; never a runtime capability."""

    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("VoiceProfileRouteSelection must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        project_manifest_revision_sha256: str,
        voice_profile_id: str,
        voice_profile_revision: int,
        voice_profile_revision_sha256: str,
        consent_revision_sha256: str,
        consent_current_evaluation_sha256: str,
        consent_evaluated_at: str,
        consent_expires_at: str,
        selection_revision: int,
        predecessor_selection_sha256: str | None,
        route_mode: RouteMode,
        public_route_key: str,
        installed_route_binding_sha256: str,
        local_audio_model_inventory_revision_sha256: str,
        local_audio_model_inventory_entry_sha256: str,
        model_license_evidence_sha256: str,
        source_requirement: SourceRequirement,
        model_candidate_revision_sha256: str | None,
        model_candidate_currentness_sha256: str | None,
        compute_preference_ref: ComputePreference,
        created_at: str,
    ) -> "VoiceProfileRouteSelection":
        if not isinstance(route_mode, RouteMode):
            raise ValueError("route_mode must use RouteMode")
        if not isinstance(source_requirement, SourceRequirement):
            raise ValueError("source_requirement must use SourceRequirement")
        if not isinstance(compute_preference_ref, ComputePreference):
            raise ValueError("compute_preference_ref must use ComputePreference")
        body: dict[str, Any] = {
            "contract_version": SELECTION_CONTRACT_VERSION,
            "record_type": "VoiceProfileRouteSelection",
            "project_id": project_id,
            "project_manifest_revision_sha256": project_manifest_revision_sha256,
            "voice_profile_id": voice_profile_id,
            "voice_profile_revision": voice_profile_revision,
            "voice_profile_revision_sha256": voice_profile_revision_sha256,
            "consent_revision_sha256": consent_revision_sha256,
            "consent_current_evaluation_sha256": consent_current_evaluation_sha256,
            "consent_evaluated_at": consent_evaluated_at,
            "consent_expires_at": consent_expires_at,
            "selection_revision": selection_revision,
            "predecessor_selection_sha256": predecessor_selection_sha256,
            "route_mode": route_mode.value,
            "public_route_key": public_route_key,
            "installed_route_binding_sha256": installed_route_binding_sha256,
            "local_audio_model_inventory_revision_sha256": local_audio_model_inventory_revision_sha256,
            "local_audio_model_inventory_entry_sha256": local_audio_model_inventory_entry_sha256,
            "model_license_evidence_sha256": model_license_evidence_sha256,
            "source_requirement": source_requirement.value,
            "model_candidate_revision_sha256": model_candidate_revision_sha256,
            "model_candidate_currentness_sha256": model_candidate_currentness_sha256,
            "compute_preference_ref": compute_preference_ref.value,
            "saved": True,
            "created_at": created_at,
            **dict(_FALSE_BOUNDARY_FLAGS),
        }
        body["selection_sha256"] = sha256_bytes(_SELECTION_DOMAIN + canonical_json_bytes(body))
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VoiceProfileRouteSelection":
        fields = {
            "contract_version", "record_type", "project_id",
            "project_manifest_revision_sha256", "voice_profile_id",
            "voice_profile_revision", "voice_profile_revision_sha256",
            "consent_revision_sha256", "consent_current_evaluation_sha256",
            "consent_evaluated_at", "consent_expires_at", "selection_revision",
            "predecessor_selection_sha256", "route_mode", "public_route_key",
            "installed_route_binding_sha256",
            "local_audio_model_inventory_revision_sha256",
            "local_audio_model_inventory_entry_sha256", "model_license_evidence_sha256",
            "source_requirement", "model_candidate_revision_sha256",
            "model_candidate_currentness_sha256", "compute_preference_ref", "saved",
            "created_at", *set(_FALSE_BOUNDARY_FLAGS), "selection_sha256",
        }
        _exact(value, fields, "VoiceProfileRouteSelection")
        if value["contract_version"] != SELECTION_CONTRACT_VERSION or value["record_type"] != "VoiceProfileRouteSelection":
            raise ValueError("selection identity/version is invalid")
        _identifier(value["project_id"], "project_id")
        _identifier(value["voice_profile_id"], "voice_profile_id")
        _public_route_key(value["public_route_key"])
        _positive(value["voice_profile_revision"], "voice_profile_revision")
        revision = _positive(value["selection_revision"], "selection_revision")
        for name in (
            "project_manifest_revision_sha256", "voice_profile_revision_sha256",
            "consent_revision_sha256", "consent_current_evaluation_sha256",
            "installed_route_binding_sha256", "local_audio_model_inventory_revision_sha256",
            "local_audio_model_inventory_entry_sha256", "model_license_evidence_sha256",
        ):
            _digest(value[name], name)
        predecessor = _digest(value["predecessor_selection_sha256"], "predecessor_selection_sha256", nullable=True)
        if (revision == 1) != (predecessor is None):
            raise ValueError("selection genesis/predecessor invariant is invalid")
        evaluated = _timestamp(value["consent_evaluated_at"], "consent_evaluated_at")
        expires = _timestamp(value["consent_expires_at"], "consent_expires_at")
        created = _timestamp(value["created_at"], "created_at")
        if expires <= evaluated:
            raise ValueError("consent expiry must follow its evaluation")
        if created < evaluated:
            raise ValueError("selection creation cannot predate consent evaluation")
        _validate_route_union(value)
        _enum(ComputePreference, value["compute_preference_ref"], "compute_preference_ref")
        if value["saved"] is not True:
            raise ValueError("durable selection must have saved=true")
        _validate_false_flags(value)
        expected = _hash(_SELECTION_DOMAIN, value, "selection_sha256")
        if value["selection_sha256"] != expected:
            raise ValueError("selection digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    @property
    def route_mode(self) -> RouteMode:
        return RouteMode(self._data["route_mode"])

    @property
    def selection_sha256(self) -> str:
        return self._data["selection_sha256"]

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


@dataclass(frozen=True, slots=True, init=False)
class VoiceProfileRouteSelectionEphemeralFixture:
    """Serializable metadata fixture that deliberately grants no authority."""

    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("ephemeral fixture must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        fixture_id: str,
        project_id: str,
        voice_profile_id: str,
        voice_profile_revision_sha256: str,
        consent_current_evaluation_sha256: str,
        route_mode: RouteMode,
        public_route_key: str,
        installed_route_binding_sha256: str,
        local_audio_model_inventory_entry_sha256: str,
        model_license_evidence_sha256: str,
        source_requirement: SourceRequirement,
        model_candidate_revision_sha256: str | None,
        model_candidate_currentness_sha256: str | None,
        compute_preference_ref: ComputePreference,
        created_at: str,
    ) -> "VoiceProfileRouteSelectionEphemeralFixture":
        body: dict[str, Any] = {
            "contract_version": EPHEMERAL_CONTRACT_VERSION,
            "record_type": "VoiceProfileRouteSelectionEphemeralFixture",
            "fixture_id": fixture_id,
            "project_id": project_id,
            "voice_profile_id": voice_profile_id,
            "voice_profile_revision_sha256": voice_profile_revision_sha256,
            "consent_current_evaluation_sha256": consent_current_evaluation_sha256,
            "route_mode": route_mode.value if isinstance(route_mode, RouteMode) else route_mode,
            "public_route_key": public_route_key,
            "installed_route_binding_sha256": installed_route_binding_sha256,
            "local_audio_model_inventory_entry_sha256": local_audio_model_inventory_entry_sha256,
            "model_license_evidence_sha256": model_license_evidence_sha256,
            "source_requirement": source_requirement.value if isinstance(source_requirement, SourceRequirement) else source_requirement,
            "model_candidate_revision_sha256": model_candidate_revision_sha256,
            "model_candidate_currentness_sha256": model_candidate_currentness_sha256,
            "compute_preference_ref": compute_preference_ref.value if isinstance(compute_preference_ref, ComputePreference) else compute_preference_ref,
            "saved": False,
            "fixture_only": True,
            "executable": False,
            "created_at": created_at,
            **dict(_FALSE_BOUNDARY_FLAGS),
        }
        body["fixture_sha256"] = sha256_bytes(_EPHEMERAL_DOMAIN + canonical_json_bytes(body))
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VoiceProfileRouteSelectionEphemeralFixture":
        fields = {
            "contract_version", "record_type", "fixture_id", "project_id", "voice_profile_id",
            "voice_profile_revision_sha256", "consent_current_evaluation_sha256", "route_mode",
            "public_route_key", "installed_route_binding_sha256",
            "local_audio_model_inventory_entry_sha256", "model_license_evidence_sha256",
            "source_requirement", "model_candidate_revision_sha256",
            "model_candidate_currentness_sha256", "compute_preference_ref", "saved",
            "fixture_only", "executable", "created_at", *set(_FALSE_BOUNDARY_FLAGS),
            "fixture_sha256",
        }
        _exact(value, fields, "VoiceProfileRouteSelectionEphemeralFixture")
        if value["contract_version"] != EPHEMERAL_CONTRACT_VERSION or value["record_type"] != "VoiceProfileRouteSelectionEphemeralFixture":
            raise ValueError("ephemeral fixture identity/version is invalid")
        for name in ("fixture_id", "project_id", "voice_profile_id"):
            _identifier(value[name], name)
        _public_route_key(value["public_route_key"])
        for name in (
            "voice_profile_revision_sha256", "consent_current_evaluation_sha256",
            "installed_route_binding_sha256", "local_audio_model_inventory_entry_sha256",
            "model_license_evidence_sha256",
        ):
            _digest(value[name], name)
        _validate_route_union(value)
        _enum(ComputePreference, value["compute_preference_ref"], "compute_preference_ref")
        _timestamp(value["created_at"], "created_at")
        if value["saved"] is not False or value["fixture_only"] is not True or value["executable"] is not False:
            raise ValueError("ephemeral fixture must remain unsaved and non-executable")
        _validate_false_flags(value)
        if value["fixture_sha256"] != _hash(_EPHEMERAL_DOMAIN, value, "fixture_sha256"):
            raise ValueError("ephemeral fixture digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


_CURRENTNESS_FIELDS = (
    "project_state", "voice_profile_state", "consent_state", "inventory_state",
    "license_state", "installed_route_state", "model_candidate_revision_state",
    "model_candidate_currentness_state",
)
_CURRENTNESS_READBACK_FIELDS = tuple(
    name.removesuffix("_state") + "_readback_sha256" for name in _CURRENTNESS_FIELDS
)


def _classify_currentness(
    route_mode: RouteMode,
    states: Mapping[str, ProducerBindingState],
    *,
    consent_fresh: bool,
) -> tuple[CurrentnessResult, tuple[str, ...]]:
    model_names = {"model_candidate_revision_state", "model_candidate_currentness_state"}
    reasons: list[str] = []
    for name in _CURRENTNESS_FIELDS:
        state = states[name]
        if name in model_names and route_mode is RouteMode.ZERO_SHOT_LOCAL:
            if state is not ProducerBindingState.NOT_APPLICABLE:
                reasons.append(f"{name.upper()}_MUST_BE_NOT_APPLICABLE")
            continue
        if state is ProducerBindingState.CURRENT:
            continue
        reasons.append(f"{name.upper()}_{state.value}")
    if not consent_fresh:
        reasons.append("CONSENT_EXPIRED_AT_EVALUATION")
    if not reasons:
        return CurrentnessResult.RUNNABLE, ()
    if any(states[name] is ProducerBindingState.NOT_CONFIRMED for name in _CURRENTNESS_FIELDS):
        return CurrentnessResult.NOT_CONFIRMED, tuple(sorted(reasons))
    return CurrentnessResult.NOT_RUNNABLE, tuple(sorted(reasons))


@dataclass(frozen=True, slots=True, init=False)
class VoiceRouteSelectionCurrentnessEvaluation:
    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("currentness evaluation must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        selection: VoiceProfileRouteSelection,
        evaluated_at: str,
        trusted_time_receipt_sha256: str,
        producer_readback_sha256s: Mapping[str, str | None],
        project_state: ProducerBindingState,
        voice_profile_state: ProducerBindingState,
        consent_state: ProducerBindingState,
        inventory_state: ProducerBindingState,
        license_state: ProducerBindingState,
        installed_route_state: ProducerBindingState,
        model_candidate_revision_state: ProducerBindingState,
        model_candidate_currentness_state: ProducerBindingState,
    ) -> "VoiceRouteSelectionCurrentnessEvaluation":
        if not isinstance(selection, VoiceProfileRouteSelection):
            raise TypeError("selection must be VoiceProfileRouteSelection")
        states = {
            name: value
            for name, value in {
                "project_state": project_state,
                "voice_profile_state": voice_profile_state,
                "consent_state": consent_state,
                "inventory_state": inventory_state,
                "license_state": license_state,
                "installed_route_state": installed_route_state,
                "model_candidate_revision_state": model_candidate_revision_state,
                "model_candidate_currentness_state": model_candidate_currentness_state,
            }.items()
        }
        if not all(isinstance(value, ProducerBindingState) for value in states.values()):
            raise ValueError("currentness states must use ProducerBindingState")
        selection_value = selection.to_dict()
        evaluated = _timestamp(evaluated_at, "evaluated_at")
        selection_created = _timestamp(selection_value["created_at"], "selection.created_at")
        consent_evaluated = _timestamp(
            selection_value["consent_evaluated_at"],
            "selection.consent_evaluated_at",
        )
        consent_expires = _timestamp(selection_value["consent_expires_at"], "consent_expires_at")
        if evaluated < selection_created or evaluated < consent_evaluated:
            raise ValueError("currentness trusted time predates its bound selection/Consent evidence")
        _digest(trusted_time_receipt_sha256, "trusted_time_receipt_sha256")
        if not isinstance(producer_readback_sha256s, Mapping) or set(producer_readback_sha256s) != set(_CURRENTNESS_READBACK_FIELDS):
            raise ValueError("producer currentness readback set is incomplete or unknown")
        readbacks: dict[str, str | None] = {}
        model_readback_fields = {
            "model_candidate_revision_readback_sha256",
            "model_candidate_currentness_readback_sha256",
        }
        for name in _CURRENTNESS_READBACK_FIELDS:
            readback = _digest(producer_readback_sha256s[name], name, nullable=True)
            if selection.route_mode is RouteMode.ZERO_SHOT_LOCAL and name in model_readback_fields:
                if readback is not None:
                    raise ValueError("zero-shot currentness cannot carry ModelCandidate readback")
            elif readback is None:
                raise ValueError(f"{name} requires an exact typed producer readback")
            readbacks[name] = readback
        result, reasons = _classify_currentness(
            selection.route_mode,
            states,
            consent_fresh=evaluated < consent_expires,
        )
        readback_set_sha256 = sha256_bytes(
            _CURRENTNESS_READBACK_SET_DOMAIN
            + canonical_json_bytes(
                {
                    "selection_sha256": selection.selection_sha256,
                    "route_mode": selection.route_mode.value,
                    "selection_created_at": selection_value["created_at"],
                    "consent_evaluated_at": selection_value["consent_evaluated_at"],
                    "evaluated_at": evaluated_at,
                    "trusted_time_receipt_sha256": trusted_time_receipt_sha256,
                    **readbacks,
                }
            )
        )
        body: dict[str, Any] = {
            "contract_version": CURRENTNESS_CONTRACT_VERSION,
            "record_type": "VoiceRouteSelectionCurrentnessEvaluation",
            "selection_sha256": selection.selection_sha256,
            "route_mode": selection.route_mode.value,
            "project_manifest_revision_sha256": selection_value["project_manifest_revision_sha256"],
            "voice_profile_revision_sha256": selection_value["voice_profile_revision_sha256"],
            "consent_current_evaluation_sha256": selection_value["consent_current_evaluation_sha256"],
            "selection_created_at": selection_value["created_at"],
            "consent_evaluated_at": selection_value["consent_evaluated_at"],
            "consent_expires_at": selection_value["consent_expires_at"],
            "installed_route_binding_sha256": selection_value["installed_route_binding_sha256"],
            "local_audio_model_inventory_entry_sha256": selection_value["local_audio_model_inventory_entry_sha256"],
            "model_license_evidence_sha256": selection_value["model_license_evidence_sha256"],
            "model_candidate_revision_sha256": selection_value["model_candidate_revision_sha256"],
            "model_candidate_currentness_sha256": selection_value["model_candidate_currentness_sha256"],
            "trusted_time_receipt_sha256": trusted_time_receipt_sha256,
            **readbacks,
            "producer_readback_set_sha256": readback_set_sha256,
            **{name: value.value for name, value in states.items()},
            "runnable_current": result is CurrentnessResult.RUNNABLE,
            "result": result.value,
            "reason_codes": list(reasons),
            "evaluated_at": evaluated_at,
            "evaluation_authority_kind": "EVIDENCE_ONLY",
            "authority_created": False,
            "execution_authorized": False,
        }
        body["currentness_evaluation_sha256"] = sha256_bytes(_CURRENTNESS_DOMAIN + canonical_json_bytes(body))
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VoiceRouteSelectionCurrentnessEvaluation":
        fields = {
            "contract_version", "record_type", "selection_sha256", "route_mode",
            "project_manifest_revision_sha256", "voice_profile_revision_sha256",
            "consent_current_evaluation_sha256", "selection_created_at",
            "consent_evaluated_at", "consent_expires_at",
            "installed_route_binding_sha256", "local_audio_model_inventory_entry_sha256",
            "model_license_evidence_sha256", "model_candidate_revision_sha256",
            "model_candidate_currentness_sha256", "trusted_time_receipt_sha256",
            *_CURRENTNESS_READBACK_FIELDS, "producer_readback_set_sha256",
            *_CURRENTNESS_FIELDS, "runnable_current", "result", "reason_codes",
            "evaluated_at", "evaluation_authority_kind", "authority_created", "execution_authorized",
            "currentness_evaluation_sha256",
        }
        _exact(value, fields, "VoiceRouteSelectionCurrentnessEvaluation")
        if value["contract_version"] != CURRENTNESS_CONTRACT_VERSION or value["record_type"] != "VoiceRouteSelectionCurrentnessEvaluation":
            raise ValueError("currentness identity/version is invalid")
        _digest(value["selection_sha256"], "selection_sha256")
        for name in (
            "project_manifest_revision_sha256", "voice_profile_revision_sha256",
            "consent_current_evaluation_sha256", "installed_route_binding_sha256",
            "local_audio_model_inventory_entry_sha256", "model_license_evidence_sha256",
            "trusted_time_receipt_sha256", "producer_readback_set_sha256",
        ):
            _digest(value[name], name)
        for name in ("model_candidate_revision_sha256", "model_candidate_currentness_sha256"):
            _digest(value[name], name, nullable=True)
        mode = _enum(RouteMode, value["route_mode"], "route_mode")
        states = {name: _enum(ProducerBindingState, value[name], name) for name in _CURRENTNESS_FIELDS}
        evaluated = _timestamp(value["evaluated_at"], "evaluated_at")
        selection_created = _timestamp(value["selection_created_at"], "selection_created_at")
        consent_evaluated = _timestamp(value["consent_evaluated_at"], "consent_evaluated_at")
        consent_expires = _timestamp(value["consent_expires_at"], "consent_expires_at")
        if evaluated < selection_created or evaluated < consent_evaluated:
            raise ValueError("currentness trusted time predates its bound selection/Consent evidence")
        readbacks = {
            name: _digest(value[name], name, nullable=True)
            for name in _CURRENTNESS_READBACK_FIELDS
        }
        model_readback_fields = {
            "model_candidate_revision_readback_sha256",
            "model_candidate_currentness_readback_sha256",
        }
        if mode is RouteMode.ZERO_SHOT_LOCAL:
            if any(readbacks[name] is not None for name in model_readback_fields):
                raise ValueError("zero-shot currentness cannot carry ModelCandidate readback")
            if value["model_candidate_revision_sha256"] is not None or value["model_candidate_currentness_sha256"] is not None:
                raise ValueError("zero-shot currentness cannot carry ModelCandidate binding")
        else:
            if any(readbacks[name] is None for name in model_readback_fields):
                raise ValueError("fine-tuned currentness requires ModelCandidate readbacks")
            if value["model_candidate_revision_sha256"] is None or value["model_candidate_currentness_sha256"] is None:
                raise ValueError("fine-tuned currentness requires ModelCandidate bindings")
        if any(readbacks[name] is None for name in set(_CURRENTNESS_READBACK_FIELDS) - model_readback_fields):
            raise ValueError("applicable producer currentness readback is missing")
        expected_readback_set = sha256_bytes(
            _CURRENTNESS_READBACK_SET_DOMAIN
            + canonical_json_bytes(
                {
                    "selection_sha256": value["selection_sha256"],
                    "route_mode": value["route_mode"],
                    "selection_created_at": value["selection_created_at"],
                    "consent_evaluated_at": value["consent_evaluated_at"],
                    "evaluated_at": value["evaluated_at"],
                    "trusted_time_receipt_sha256": value["trusted_time_receipt_sha256"],
                    **readbacks,
                }
            )
        )
        if value["producer_readback_set_sha256"] != expected_readback_set:
            raise ValueError("producer currentness readback set digest mismatch")
        result, reasons = _classify_currentness(
            mode,
            states,
            consent_fresh=evaluated < consent_expires,
        )  # type: ignore[arg-type]
        if value["result"] != result.value or value["runnable_current"] is not (result is CurrentnessResult.RUNNABLE):
            raise ValueError("currentness classification mismatch")
        if not isinstance(value["reason_codes"], list):
            raise ValueError("currentness reason codes must be a list")
        for reason in value["reason_codes"]:
            _reason_code(reason)
        if value["reason_codes"] != list(reasons):
            raise ValueError("currentness reason codes mismatch")
        if value["evaluation_authority_kind"] != "EVIDENCE_ONLY":
            raise ValueError("currentness evaluation cannot be an authority bearer")
        if value["authority_created"] is not False or value["execution_authorized"] is not False:
            raise ValueError("currentness evaluation cannot create authority")
        if value["currentness_evaluation_sha256"] != _hash(
            _CURRENTNESS_DOMAIN, value, "currentness_evaluation_sha256"
        ):
            raise ValueError("currentness evaluation digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    @property
    def runnable_current(self) -> bool:
        return self._data["runnable_current"]

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


@dataclass(frozen=True, slots=True, init=False)
class VoiceRouteSelectionCASRequest:
    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("CAS request must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        selection: VoiceProfileRouteSelection,
        expected_project_transaction_head_sha256: str,
        expected_selection_head_sha256: str | None,
    ) -> "VoiceRouteSelectionCASRequest":
        if not isinstance(selection, VoiceProfileRouteSelection):
            raise TypeError("selection must be VoiceProfileRouteSelection")
        body: dict[str, Any] = {
            "contract_version": CAS_REQUEST_CONTRACT_VERSION,
            "record_type": "VoiceRouteSelectionCASRequest",
            "operation_id": operation_id,
            "selection_sha256": selection.selection_sha256,
            "selection_revision": selection.to_dict()["selection_revision"],
            "expected_project_transaction_head_sha256": expected_project_transaction_head_sha256,
            "expected_selection_head_sha256": expected_selection_head_sha256,
            "caller_path_present": False,
            "caller_connection_present": False,
            "caller_transaction_present": False,
            "caller_time_present": False,
            "caller_current_head_override_present": False,
            "authority_created": False,
            "execution_authorized": False,
        }
        body["cas_request_sha256"] = sha256_bytes(_CAS_REQUEST_DOMAIN + canonical_json_bytes(body))
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VoiceRouteSelectionCASRequest":
        fields = {
            "contract_version", "record_type", "operation_id", "selection_sha256",
            "selection_revision", "expected_project_transaction_head_sha256",
            "expected_selection_head_sha256", "caller_path_present",
            "caller_connection_present", "caller_transaction_present", "caller_time_present",
            "caller_current_head_override_present", "authority_created", "execution_authorized",
            "cas_request_sha256",
        }
        _exact(value, fields, "VoiceRouteSelectionCASRequest")
        if value["contract_version"] != CAS_REQUEST_CONTRACT_VERSION or value["record_type"] != "VoiceRouteSelectionCASRequest":
            raise ValueError("CAS request identity/version is invalid")
        _identifier(value["operation_id"], "operation_id")
        _digest(value["selection_sha256"], "selection_sha256")
        revision = _positive(value["selection_revision"], "selection_revision")
        _digest(value["expected_project_transaction_head_sha256"], "expected_project_transaction_head_sha256")
        expected_selection = _digest(value["expected_selection_head_sha256"], "expected_selection_head_sha256", nullable=True)
        if (revision == 1) != (expected_selection is None):
            raise ValueError("CAS expected selection head does not match revision")
        for name in (
            "caller_path_present", "caller_connection_present", "caller_transaction_present",
            "caller_time_present", "caller_current_head_override_present", "authority_created",
            "execution_authorized",
        ):
            if value[name] is not False:
                raise ValueError(f"{name} must remain false")
        if value["cas_request_sha256"] != _hash(_CAS_REQUEST_DOMAIN, value, "cas_request_sha256"):
            raise ValueError("CAS request digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


@dataclass(frozen=True, slots=True, init=False)
class VoiceRouteSelectionCASReadback:
    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("CAS readback must use create/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def create(
        cls,
        *,
        request: VoiceRouteSelectionCASRequest,
        outcome: CASOutcome,
        result_project_transaction_head_sha256: str,
        result_selection_head_sha256: str | None,
        committed_selection_sha256: str | None,
        pinned_store_identity_sha256: str,
        pinned_readback_match: bool,
        readback_at: str,
    ) -> "VoiceRouteSelectionCASReadback":
        if not isinstance(request, VoiceRouteSelectionCASRequest) or not isinstance(outcome, CASOutcome):
            raise TypeError("request/outcome types are invalid")
        request_data = request.to_dict()
        body: dict[str, Any] = {
            "contract_version": CAS_READBACK_CONTRACT_VERSION,
            "record_type": "VoiceRouteSelectionCASReadback",
            "operation_id": request_data["operation_id"],
            "cas_request_sha256": request_data["cas_request_sha256"],
            "requested_selection_sha256": request_data["selection_sha256"],
            "outcome": outcome.value,
            "result_project_transaction_head_sha256": result_project_transaction_head_sha256,
            "result_selection_head_sha256": result_selection_head_sha256,
            "committed_selection_sha256": committed_selection_sha256,
            "pinned_store_identity_sha256": pinned_store_identity_sha256,
            "pinned_readback_match": pinned_readback_match,
            "readback_at": readback_at,
            "automatic_retry_started": False,
            "authority_created": False,
            "execution_authorized": False,
            **dict(_FIXTURE_READBACK_BOUNDARY),
        }
        body["cas_readback_sha256"] = sha256_bytes(_CAS_READBACK_DOMAIN + canonical_json_bytes(body))
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VoiceRouteSelectionCASReadback":
        fields = {
            "contract_version", "record_type", "operation_id", "cas_request_sha256",
            "requested_selection_sha256", "outcome", "result_project_transaction_head_sha256",
            "result_selection_head_sha256", "committed_selection_sha256",
            "pinned_store_identity_sha256", "pinned_readback_match", "readback_at",
            "automatic_retry_started", "authority_created", "execution_authorized",
            *set(_FIXTURE_READBACK_BOUNDARY),
            "cas_readback_sha256",
        }
        _exact(value, fields, "VoiceRouteSelectionCASReadback")
        if value["contract_version"] != CAS_READBACK_CONTRACT_VERSION or value["record_type"] != "VoiceRouteSelectionCASReadback":
            raise ValueError("CAS readback identity/version is invalid")
        _identifier(value["operation_id"], "operation_id")
        for name in (
            "cas_request_sha256", "requested_selection_sha256",
            "result_project_transaction_head_sha256", "pinned_store_identity_sha256",
        ):
            _digest(value[name], name)
        result_head = _digest(value["result_selection_head_sha256"], "result_selection_head_sha256", nullable=True)
        committed = _digest(value["committed_selection_sha256"], "committed_selection_sha256", nullable=True)
        outcome = _enum(CASOutcome, value["outcome"], "outcome")
        if not isinstance(value["pinned_readback_match"], bool):
            raise ValueError("pinned_readback_match must be boolean")
        if outcome is CASOutcome.COMMITTED:
            if committed != value["requested_selection_sha256"] or result_head != committed or value["pinned_readback_match"] is not True:
                raise ValueError("committed CAS readback is not an exact pinned match")
        elif committed is not None:
            raise ValueError("non-committed CAS readback cannot carry a committed selection")
        _timestamp(value["readback_at"], "readback_at")
        for name in ("automatic_retry_started", "authority_created", "execution_authorized"):
            if value[name] is not False:
                raise ValueError(f"{name} must remain false")
        for name, expected in _FIXTURE_READBACK_BOUNDARY.items():
            if value[name] != expected:
                raise ValueError(f"{name} cannot claim a canonical TASK074-C producer")
        if value["cas_readback_sha256"] != _hash(_CAS_READBACK_DOMAIN, value, "cas_readback_sha256"):
            raise ValueError("CAS readback digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


def validate_route_selection_cas_readback(
    request: VoiceRouteSelectionCASRequest,
    selection: VoiceProfileRouteSelection,
    readback: VoiceRouteSelectionCASReadback,
) -> None:
    """Validate exact request/selection/readback lineage without doing a save."""

    if not all(
        (
            isinstance(request, VoiceRouteSelectionCASRequest),
            isinstance(selection, VoiceProfileRouteSelection),
            isinstance(readback, VoiceRouteSelectionCASReadback),
        )
    ):
        raise TypeError("CAS lineage inputs use the wrong typed contracts")
    request_data = request.to_dict()
    selection_data = selection.to_dict()
    readback_data = readback.to_dict()
    if request_data["selection_sha256"] != selection_data["selection_sha256"]:
        raise ValueError("CAS request/selection digest mismatch")
    if request_data["selection_revision"] != selection_data["selection_revision"]:
        raise ValueError("CAS request/selection revision mismatch")
    if request_data["expected_selection_head_sha256"] != selection_data["predecessor_selection_sha256"]:
        raise ValueError("CAS request does not bind the selection predecessor")
    if (
        readback_data["operation_id"] != request_data["operation_id"]
        or readback_data["cas_request_sha256"] != request_data["cas_request_sha256"]
        or readback_data["requested_selection_sha256"] != selection_data["selection_sha256"]
    ):
        raise ValueError("CAS readback lineage mismatch")


class VoiceRouteSelectionStorePort(Protocol):
    """TASK-043-owned capability shape; TASK074-B provides no implementation."""

    def compare_and_append(
        self,
        request: VoiceRouteSelectionCASRequest,
        selection: VoiceProfileRouteSelection,
    ) -> Mapping[str, Any]: ...


__all__ = [
    "CASOutcome",
    "ComputePreference",
    "CurrentnessResult",
    "ProducerBindingState",
    "RouteMode",
    "SourceRequirement",
    "VoiceProfileRouteSelection",
    "VoiceProfileRouteSelectionEphemeralFixture",
    "VoiceRouteSelectionCASReadback",
    "VoiceRouteSelectionCASRequest",
    "VoiceRouteSelectionCurrentnessEvaluation",
    "VoiceRouteSelectionStorePort",
    "validate_route_selection_cas_readback",
]
