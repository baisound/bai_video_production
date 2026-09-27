"""TASK-100 pure local Owner-voice catalog admission contracts.

This module validates body-free metadata and composes the existing TASK-013
local-audio inventory.  It performs no file, model, runtime, network, process,
credential, audio, or authority effect.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
import re
from types import MappingProxyType
from typing import Any, Mapping

from .ai_connections import ProviderFamily
from .local_audio_model_inventory import (
    AudioModelPurpose,
    AutomationReadiness,
    InstalledState,
    InventoryCurrentness,
    InventorySource,
    LocalAudioModelInventory,
    LocalAudioModelObservation,
    LocalFreeLicenseState,
    RuntimeReadiness,
    compile_local_audio_model_inventory,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


CANDIDATE_VERSION = "LOCAL_VOICE_CATALOG_CANDIDATE_V1"
ASSESSMENT_VERSION = "LOCAL_VOICE_CATALOG_ASSESSMENT_V1"
ADMISSION_VERSION = "LOCAL_VOICE_CATALOG_ADMISSION_V1"
MAX_SECURITY_JSON_BYTES = 131_072
MAX_SECURITY_JSON_DEPTH = 12

_CANDIDATE_DOMAIN = b"BAI:TASK-100:LOCAL-VOICE-CATALOG-CANDIDATE:V1\0"
_ASSESSMENT_DOMAIN = b"BAI:TASK-100:LOCAL-VOICE-CATALOG-ASSESSMENT:V1\0"
_ADMISSION_DOMAIN = b"BAI:TASK-100:LOCAL-VOICE-CATALOG-ADMISSION:V1\0"
_FACTORY_KEY = object()
_PUBLIC_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,95}$")
_TIMESTAMP_RE = re.compile(
    r"^(?:(?:(?!0000)[0-9]{4})-"
    r"(?:(?:0[13578]|1[02])-(?:0[1-9]|[12][0-9]|3[01])|"
    r"(?:0[469]|11)-(?:0[1-9]|[12][0-9]|30)|"
    r"02-(?:0[1-9]|1[0-9]|2[0-8]))|"
    r"(?:(?!0000)(?:[0-9]{2}(?:0[48]|[2468][048]|[13579][26])|"
    r"(?:0[48]|[2468][048]|[13579][26])00))-02-29)"
    r"T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]{1,6})?Z$"
)

_CANDIDATE_FIELDS = {
    "contract_version", "record_type", "candidate_id", "revision",
    "predecessor_sha256", "provider_id", "engine_id", "model_id",
    "runtime_build_sha256", "model_pair_sha256", "sovits_sha256",
    "gpt_sha256", "voice_profile_revision_sha256",
    "model_candidate_revision_sha256", "custody_provenance",
    "consent_currentness_sha256", "h4_approval_sha256",
    "license_evidence_sha256", "installed_binding_sha256",
    "capability_map_sha256", "execution_port_id",
    "producer_readback_set_sha256", "observation_source", "observed_at",
    "expires_at", "candidate_sha256",
}
_CUSTODY_FIELDS = {
    "variant", "producer_task", "receipt_type", "receipt_sha256",
    "readback_type", "readback_sha256",
}
_ASSESSMENT_FIELDS = {
    "assessment_version", "candidate_sha256", "producer_readback_set_sha256",
    "evaluated_at", "installed_state", "runtime_readiness",
    "runtime_instance_id", "inventory_currentness", "license_state",
    "automation_readiness", "producer_authenticity",
    "custody_contract_state", "required_producer_currentness",
    "assessment_sha256",
}
_CURRENTNESS_KEYS = (
    "LINEAGE", "CUSTODY", "CONSENT", "H4_APPROVAL", "INSTALLED_BINDING",
    "CAPABILITY_MAP", "EXECUTION_PORT",
)


class ObservationSource(str, Enum):
    VERIFIED_PRODUCER_READBACK = "VERIFIED_PRODUCER_READBACK"
    FIXTURE_ONLY = "FIXTURE_ONLY"


class CustodyVariant(str, Enum):
    EXISTING_MODEL_IMPORT = "EXISTING_MODEL_IMPORT"
    TRAINING_TERMINAL = "TRAINING_TERMINAL"


class ProducerAuthenticity(str, Enum):
    VERIFIED = "VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"


class CustodyContractState(str, Enum):
    ACCEPTED = "ACCEPTED"
    PROPOSED_FIXTURE_ONLY = "PROPOSED_FIXTURE_ONLY"


class ProducerCurrentness(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"


class CatalogAdmissionState(str, Enum):
    ADMITTED = "ADMITTED_CATALOG_CANDIDATE"
    BLOCKED = "BLOCKED_CATALOG_CANDIDATE"
    FIXTURE_ONLY = "FIXTURE_ONLY_CANDIDATE"


def _exact(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields are not exact")


def _public_id(value: Any, name: str, *, model: bool = False) -> str:
    pattern = _MODEL_ID_RE if model else _PUBLIC_ID_RE
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"{name} is not a valid opaque identifier")
    lowered = value.casefold()
    if (
        "\\" in value
        or "/" in value
        or "://" in lowered
        or lowered.startswith(("file:", "http:", "https:"))
    ):
        raise ValueError(f"{name} must not contain a path or URI")
    if model and re.match(r"^[A-Za-z]:", value):
        raise ValueError(f"{name} must not be drive-qualified")
    return value


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a SHA-256 string")
    return validate_sha256(value, field_name=name)


def _integer(value: Any, name: str, *, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= 2_147_483_647:
        raise ValueError(f"{name} is outside the accepted integer range")
    return value


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not _TIMESTAMP_RE.fullmatch(value):
        raise ValueError(f"{name} must be a calendar-valid UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be a calendar-valid UTC timestamp") from exc
    return parsed


def _digest(body: Mapping[str, Any], field: str, domain: bytes) -> str:
    value = copy.deepcopy(dict(body))
    value.pop(field, None)
    return sha256_bytes(domain + canonical_json_bytes(value))


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


def _verify_digest(body: Mapping[str, Any], field: str, domain: bytes) -> None:
    _sha(body.get(field), field)
    if body[field] != _digest(body, field, domain):
        raise ValueError(f"{field} does not match canonical content")


@dataclass(frozen=True, slots=True)
class CustodyProvenanceV1:
    variant: CustodyVariant
    producer_task: str
    receipt_type: str
    receipt_sha256: str
    readback_type: str
    readback_sha256: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CustodyProvenanceV1":
        _exact(value, _CUSTODY_FIELDS, "custody_provenance")
        try:
            variant = CustodyVariant(value["variant"])
        except (TypeError, ValueError) as exc:
            raise ValueError("custody variant is unsupported") from exc
        expected = {
            CustodyVariant.EXISTING_MODEL_IMPORT: (
                "TASK-101", "ExistingModelImportCustodyReceiptV1",
                "ExistingModelImportCustodyReadbackV1",
            ),
            CustodyVariant.TRAINING_TERMINAL: (
                "TASK-084", "Task084ModelArtifactCustodyReceiptV1",
                "Task084CustodyReadbackV1",
            ),
        }[variant]
        actual = (value["producer_task"], value["receipt_type"], value["readback_type"])
        if actual != expected:
            raise ValueError("custody producer/type does not match its variant")
        return cls(
            variant=variant,
            producer_task=expected[0],
            receipt_type=expected[1],
            receipt_sha256=_sha(value["receipt_sha256"], "receipt_sha256"),
            readback_type=expected[2],
            readback_sha256=_sha(value["readback_sha256"], "readback_sha256"),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "variant": self.variant.value,
            "producer_task": self.producer_task,
            "receipt_type": self.receipt_type,
            "receipt_sha256": self.receipt_sha256,
            "readback_type": self.readback_type,
            "readback_sha256": self.readback_sha256,
        }


@dataclass(frozen=True, slots=True, init=False)
class LocalVoiceCatalogCandidateV1:
    data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _FACTORY_KEY:
            raise TypeError("LocalVoiceCatalogCandidateV1 must be created by its validated factory")
        object.__setattr__(self, "data", data)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LocalVoiceCatalogCandidateV1":
        body = copy.deepcopy(dict(value))
        _exact(body, _CANDIDATE_FIELDS, "LocalVoiceCatalogCandidateV1")
        if body["contract_version"] != CANDIDATE_VERSION or body["record_type"] != "LocalVoiceCatalogCandidateV1":
            raise ValueError("candidate discriminator mismatch")
        for field in ("candidate_id", "provider_id", "engine_id", "execution_port_id"):
            _public_id(body[field], field)
        _public_id(body["model_id"], "model_id", model=True)
        revision = _integer(body["revision"], "revision")
        predecessor = body["predecessor_sha256"]
        if (revision == 1 and predecessor is not None) or (revision > 1 and predecessor is None):
            raise ValueError("predecessor_sha256 does not match revision")
        if predecessor is not None:
            _sha(predecessor, "predecessor_sha256")
        for field in (
            "runtime_build_sha256", "model_pair_sha256", "sovits_sha256",
            "gpt_sha256", "voice_profile_revision_sha256",
            "model_candidate_revision_sha256", "consent_currentness_sha256",
            "h4_approval_sha256", "license_evidence_sha256",
            "installed_binding_sha256", "capability_map_sha256",
            "producer_readback_set_sha256",
        ):
            _sha(body[field], field)
        custody = CustodyProvenanceV1.from_dict(body["custody_provenance"])
        body["custody_provenance"] = custody.to_dict()
        try:
            ObservationSource(body["observation_source"])
        except (TypeError, ValueError) as exc:
            raise ValueError("observation_source is unsupported") from exc
        observed = _timestamp(body["observed_at"], "observed_at")
        expires = _timestamp(body["expires_at"], "expires_at")
        if observed >= expires:
            raise ValueError("candidate observation must precede expiry")
        _verify_digest(body, "candidate_sha256", _CANDIDATE_DOMAIN)
        return cls(_freeze(body), _token=_FACTORY_KEY)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.data)

    @property
    def candidate_sha256(self) -> str:
        return str(self.data["candidate_sha256"])


@dataclass(frozen=True, slots=True, init=False)
class LocalVoiceCatalogAssessmentV1:
    data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _FACTORY_KEY:
            raise TypeError("LocalVoiceCatalogAssessmentV1 must be created by its validated factory")
        object.__setattr__(self, "data", data)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LocalVoiceCatalogAssessmentV1":
        body = copy.deepcopy(dict(value))
        _exact(body, _ASSESSMENT_FIELDS, "LocalVoiceCatalogAssessmentV1")
        if body["assessment_version"] != ASSESSMENT_VERSION:
            raise ValueError("assessment discriminator mismatch")
        _sha(body["candidate_sha256"], "candidate_sha256")
        _sha(body["producer_readback_set_sha256"], "producer_readback_set_sha256")
        _timestamp(body["evaluated_at"], "evaluated_at")
        enum_fields = (
            ("installed_state", InstalledState),
            ("runtime_readiness", RuntimeReadiness),
            ("inventory_currentness", InventoryCurrentness),
            ("license_state", LocalFreeLicenseState),
            ("automation_readiness", AutomationReadiness),
            ("producer_authenticity", ProducerAuthenticity),
            ("custody_contract_state", CustodyContractState),
        )
        for field, kind in enum_fields:
            try:
                kind(body[field])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{field} is unsupported") from exc
        runtime_id = body["runtime_instance_id"]
        if body["runtime_readiness"] == RuntimeReadiness.READY.value:
            _public_id(runtime_id, "runtime_instance_id")
        elif runtime_id is not None:
            raise ValueError("non-ready assessment must not bind runtime_instance_id")
        currentness = body["required_producer_currentness"]
        _exact(currentness, set(_CURRENTNESS_KEYS), "required_producer_currentness")
        for key in _CURRENTNESS_KEYS:
            try:
                ProducerCurrentness(currentness[key])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{key} currentness is unsupported") from exc
        _verify_digest(body, "assessment_sha256", _ASSESSMENT_DOMAIN)
        return cls(_freeze(body), _token=_FACTORY_KEY)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.data)


@dataclass(frozen=True, slots=True, init=False)
class LocalVoiceCatalogAdmissionV1:
    data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _FACTORY_KEY:
            raise TypeError("LocalVoiceCatalogAdmissionV1 is compiler-created only")
        object.__setattr__(self, "data", data)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.data)


@dataclass(frozen=True, slots=True)
class CompiledLocalVoiceCatalogAdmissionV1:
    admission: LocalVoiceCatalogAdmissionV1
    inventory: LocalAudioModelInventory


def create_local_voice_catalog_candidate(**fields: Any) -> LocalVoiceCatalogCandidateV1:
    body = {"contract_version": CANDIDATE_VERSION, "record_type": "LocalVoiceCatalogCandidateV1", **fields}
    body["candidate_sha256"] = _digest(body, "candidate_sha256", _CANDIDATE_DOMAIN)
    return LocalVoiceCatalogCandidateV1.from_dict(body)


def create_local_voice_catalog_assessment(**fields: Any) -> LocalVoiceCatalogAssessmentV1:
    body = {"assessment_version": ASSESSMENT_VERSION, **fields}
    body["assessment_sha256"] = _digest(body, "assessment_sha256", _ASSESSMENT_DOMAIN)
    return LocalVoiceCatalogAssessmentV1.from_dict(body)


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("security JSON contains duplicate object keys")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite number {value} is forbidden")


def _depth(value: Any) -> int:
    maximum = 0
    pending: list[tuple[Any, int]] = [(value, 0)]
    while pending:
        current, depth = pending.pop()
        if isinstance(current, Mapping):
            next_depth = depth + 1
            maximum = max(maximum, next_depth)
            pending.extend((item, next_depth) for item in current.values())
        elif isinstance(current, list):
            next_depth = depth + 1
            maximum = max(maximum, next_depth)
            pending.extend((item, next_depth) for item in current)
        if maximum > MAX_SECURITY_JSON_DEPTH:
            return maximum
    return maximum


def parse_local_voice_catalog_candidate_json(payload: bytes) -> LocalVoiceCatalogCandidateV1:
    if not isinstance(payload, bytes) or not payload or len(payload) > MAX_SECURITY_JSON_BYTES or payload.startswith(b"\xef\xbb\xbf"):
        raise ValueError("candidate JSON is empty, oversized, non-bytes, or contains BOM")
    try:
        text = payload.decode("utf-8", errors="strict")
        decoder = json.JSONDecoder(object_pairs_hook=_pairs_no_duplicates, parse_constant=_reject_constant)
        value, end = decoder.raw_decode(text)
    except RecursionError as exc:
        raise ValueError("candidate JSON has excessive depth") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("candidate JSON is invalid") from exc
    if end != len(text) or _depth(value) > MAX_SECURITY_JSON_DEPTH:
        raise ValueError("candidate JSON has trailing data or excessive depth")
    if not isinstance(value, Mapping):
        raise ValueError("candidate JSON root must be an object")
    return LocalVoiceCatalogCandidateV1.from_dict(value)


def _assessment_observation(candidate: LocalVoiceCatalogCandidateV1, assessment: LocalVoiceCatalogAssessmentV1) -> LocalAudioModelObservation:
    c, a = candidate.data, assessment.data
    runtime = RuntimeReadiness(a["runtime_readiness"])
    automation = AutomationReadiness(a["automation_readiness"])
    return LocalAudioModelObservation(
        candidate_id=c["candidate_id"], purpose=AudioModelPurpose.NARRATION,
        workload=None, provider_family=ProviderFamily.LOCAL_OPEN_SOURCE,
        provider_id=c["provider_id"], model_id=c["model_id"], route_id=None,
        installed_state=InstalledState(a["installed_state"]),
        runtime_readiness=runtime,
        currentness=InventoryCurrentness(a["inventory_currentness"]),
        license_state=LocalFreeLicenseState(a["license_state"]),
        automation_readiness=automation, source=InventorySource.PINNED_CONTRACT,
        runtime_instance_id=a["runtime_instance_id"] if runtime is RuntimeReadiness.READY else None,
        execution_port_id=c["execution_port_id"] if automation is AutomationReadiness.SCRIPTABLE else None,
        evidence_sha256=candidate.candidate_sha256,
    )


def _blocked_observation(candidate: LocalVoiceCatalogCandidateV1) -> LocalAudioModelObservation:
    c = candidate.data
    return LocalAudioModelObservation(
        candidate_id=c["candidate_id"], purpose=AudioModelPurpose.NARRATION,
        workload=None, provider_family=ProviderFamily.LOCAL_OPEN_SOURCE,
        provider_id=c["provider_id"], model_id=c["model_id"], route_id=None,
        installed_state=InstalledState.UNKNOWN, runtime_readiness=RuntimeReadiness.UNKNOWN,
        currentness=InventoryCurrentness.UNKNOWN,
        license_state=LocalFreeLicenseState.UNKNOWN,
        automation_readiness=AutomationReadiness.UNSUPPORTED,
        source=InventorySource.HISTORICAL_EVIDENCE,
        runtime_instance_id=None, execution_port_id=None,
        evidence_sha256=candidate.candidate_sha256,
    )


def compile_local_voice_catalog_admission(
    candidate: LocalVoiceCatalogCandidateV1 | Mapping[str, Any],
    assessment: LocalVoiceCatalogAssessmentV1 | Mapping[str, Any],
) -> CompiledLocalVoiceCatalogAdmissionV1:
    candidate_body = candidate.to_dict() if isinstance(candidate, LocalVoiceCatalogCandidateV1) else candidate
    assessment_body = assessment.to_dict() if isinstance(assessment, LocalVoiceCatalogAssessmentV1) else assessment
    cand = LocalVoiceCatalogCandidateV1.from_dict(candidate_body)
    assess = LocalVoiceCatalogAssessmentV1.from_dict(assessment_body)
    c, a = cand.data, assess.data
    if a["candidate_sha256"] != c["candidate_sha256"] or a["producer_readback_set_sha256"] != c["producer_readback_set_sha256"]:
        raise ValueError("assessment does not bind the exact candidate/readback set")
    observed = _timestamp(c["observed_at"], "observed_at")
    evaluated = _timestamp(a["evaluated_at"], "evaluated_at")
    expires = _timestamp(c["expires_at"], "expires_at")
    if not observed <= evaluated < expires:
        raise ValueError("assessment evaluation time is outside candidate validity")

    supplied_inventory = compile_local_audio_model_inventory((_assessment_observation(cand, assess),))
    reasons: list[str] = []
    if c["observation_source"] == ObservationSource.FIXTURE_ONLY.value:
        reasons.append("FIXTURE_ONLY_SOURCE")
    if a["producer_authenticity"] != ProducerAuthenticity.VERIFIED.value:
        reasons.append("PRODUCER_AUTHENTICITY_NOT_VERIFIED")
    if a["custody_contract_state"] != CustodyContractState.ACCEPTED.value:
        reasons.append("CUSTODY_CONTRACT_NOT_ACCEPTED")
    for key in _CURRENTNESS_KEYS:
        state = ProducerCurrentness(a["required_producer_currentness"][key])
        if state is not ProducerCurrentness.CURRENT:
            reasons.append(f"{key}_{state.value}")
    reasons.extend(supplied_inventory.candidates[0].disabled_reasons)
    reasons = list(dict.fromkeys(reasons))
    if len(reasons) > 16 or any(not _REASON_RE.fullmatch(item) for item in reasons):
        raise ValueError("admission reason set is outside the closed bound")

    if c["observation_source"] == ObservationSource.FIXTURE_ONLY.value:
        state = CatalogAdmissionState.FIXTURE_ONLY
    elif reasons:
        state = CatalogAdmissionState.BLOCKED
    else:
        state = CatalogAdmissionState.ADMITTED
    final_observation = supplied_inventory.candidates[0].observation if state is CatalogAdmissionState.ADMITTED else _blocked_observation(cand)
    inventory = compile_local_audio_model_inventory((final_observation,))
    public_inventory = inventory.to_public_dict()
    inventory_candidate = public_inventory["candidates"][0]
    body: dict[str, Any] = {
        "contract_version": ADMISSION_VERSION,
        "record_type": "LocalVoiceCatalogAdmissionV1",
        "candidate_sha256": c["candidate_sha256"],
        "producer_readback_set_sha256": c["producer_readback_set_sha256"],
        "assessment_sha256": a["assessment_sha256"],
        "candidate_observed_at": c["observed_at"],
        "evaluated_at": a["evaluated_at"],
        "candidate_expires_at": c["expires_at"],
        "admission_state": state.value,
        "reason_codes": reasons,
        "inventory_candidate_sha256": inventory_candidate["candidate_sha256"],
        "inventory_sha256": public_inventory["inventory_sha256"],
        "consumer_live_eligible": False,
        "consumer_currentness_required": True,
        "replayable_authority": False,
        "execution_authorized": False,
        "load_lease_created": False,
        "runtime_started": False,
        "model_downloaded": False,
        "host_path_persisted": False,
        "private_body_persisted": False,
        "resource_effect_count": 0,
    }
    body["admission_sha256"] = _digest(body, "admission_sha256", _ADMISSION_DOMAIN)
    return CompiledLocalVoiceCatalogAdmissionV1(
        LocalVoiceCatalogAdmissionV1(_freeze(body), _token=_FACTORY_KEY),
        inventory,
    )


__all__ = [
    "ADMISSION_VERSION", "ASSESSMENT_VERSION", "CANDIDATE_VERSION",
    "CatalogAdmissionState", "CompiledLocalVoiceCatalogAdmissionV1",
    "CustodyContractState", "CustodyVariant", "LocalVoiceCatalogAdmissionV1",
    "LocalVoiceCatalogAssessmentV1", "LocalVoiceCatalogCandidateV1",
    "ObservationSource", "ProducerAuthenticity", "ProducerCurrentness",
    "compile_local_voice_catalog_admission", "create_local_voice_catalog_assessment",
    "create_local_voice_catalog_candidate", "parse_local_voice_catalog_candidate_json",
]
