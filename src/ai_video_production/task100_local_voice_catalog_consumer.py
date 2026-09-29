"""TASK-100 pure local-voice catalog consumer readback.

The compiler binds already validated TASK-100, TASK-074 and TASK-014 records.
It performs no filesystem, model, runtime, process, network, audio or Product
mutation and never creates execution authority.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
import re
from types import MappingProxyType
from typing import Any, Mapping

from .local_audio_model_inventory import LocalAudioModelInventory
from .owner_narration_local_primary import (
    LocalNarrationRouteMode,
    LocalPrimaryNarrationPreflight,
    PreflightDecision,
    parse_local_primary_preflight,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .task100_local_voice_catalog_admission import (
    CatalogAdmissionState,
    CompiledLocalVoiceCatalogAdmissionV1,
    LocalVoiceCatalogAdmissionV1,
    LocalVoiceCatalogAssessmentV1,
    LocalVoiceCatalogCandidateV1,
    compile_local_voice_catalog_admission,
)
from .voice_profile_route_selection import (
    CurrentnessResult,
    RouteMode,
    SourceRequirement,
    VoiceProfileRouteSelection,
    VoiceRouteSelectionCurrentnessEvaluation,
)


CONSUMER_READBACK_VERSION = "LOCAL_VOICE_CATALOG_CONSUMER_READBACK_V1"

_READBACK_DOMAIN = b"BAI:TASK-100:LOCAL-VOICE-CATALOG-CONSUMER-READBACK:V1\0"
_CONSTRUCTION_TOKEN = object()
_PUBLIC_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
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

_REASONS = {
    "CATALOG_ADMISSION_NOT_ADMITTED",
    "INVENTORY_CANDIDATE_NOT_SELECTABLE",
    "ROUTE_CURRENTNESS_NOT_RUNNABLE",
    "NARRATION_PREFLIGHT_NOT_READY",
}
_FALSE_FIELDS = {
    "authority_created",
    "execution_authorized",
    "load_lease_created",
    "runtime_started",
    "model_loaded",
    "inference_started",
    "audio_body_persisted",
    "host_path_persisted",
}
_READBACK_FIELDS = {
    "contract_version",
    "record_type",
    "candidate_sha256",
    "assessment_sha256",
    "admission_sha256",
    "producer_readback_set_sha256",
    "inventory_sha256",
    "inventory_candidate_sha256",
    "route_selection_sha256",
    "route_currentness_evaluation_sha256",
    "route_currentness_readback_set_sha256",
    "narration_preflight_sha256",
    "project_id",
    "voice_profile_id",
    "voice_profile_revision_sha256",
    "model_candidate_revision_sha256",
    "installed_binding_sha256",
    "license_evidence_sha256",
    "model_pair_sha256",
    "engine_id",
    "evaluated_at",
    "consumer_live_eligible",
    "reason_codes",
    "authority_kind",
    *_FALSE_FIELDS,
    "resource_effect_count",
    "consumer_readback_sha256",
}


def _exact(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields are not exact")


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a SHA-256 string")
    return validate_sha256(value, field_name=name)


def _public_id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _PUBLIC_ID_RE.fullmatch(value):
        raise ValueError(f"{name} is not a valid opaque identifier")
    if "\\" in value or "/" in value or "://" in value.casefold():
        raise ValueError(f"{name} must not contain a path or URI")
    return value


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not _TIMESTAMP_RE.fullmatch(value):
        raise ValueError(f"{name} must be a calendar-valid UTC timestamp")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be a calendar-valid UTC timestamp") from exc


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


def _digest(value: Mapping[str, Any]) -> str:
    body = copy.deepcopy(dict(value))
    body.pop("consumer_readback_sha256", None)
    return sha256_bytes(_READBACK_DOMAIN + canonical_json_bytes(body))


@dataclass(frozen=True, slots=True, init=False)
class LocalVoiceCatalogConsumerReadbackV1:
    _data: Mapping[str, Any]

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("consumer readback must use compile/from_dict")
        object.__setattr__(self, "_data", data)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LocalVoiceCatalogConsumerReadbackV1":
        body = copy.deepcopy(dict(value))
        _exact(body, _READBACK_FIELDS, "LocalVoiceCatalogConsumerReadbackV1")
        if (
            body["contract_version"] != CONSUMER_READBACK_VERSION
            or body["record_type"] != "LocalVoiceCatalogConsumerReadbackV1"
        ):
            raise ValueError("consumer readback discriminator mismatch")
        for field in (
            "candidate_sha256",
            "assessment_sha256",
            "admission_sha256",
            "producer_readback_set_sha256",
            "inventory_sha256",
            "inventory_candidate_sha256",
            "route_selection_sha256",
            "route_currentness_evaluation_sha256",
            "route_currentness_readback_set_sha256",
            "narration_preflight_sha256",
            "voice_profile_revision_sha256",
            "model_candidate_revision_sha256",
            "installed_binding_sha256",
            "license_evidence_sha256",
            "model_pair_sha256",
        ):
            _sha(body[field], field)
        for field in ("project_id", "voice_profile_id", "engine_id"):
            _public_id(body[field], field)
        _timestamp(body["evaluated_at"], "evaluated_at")
        reasons = body["reason_codes"]
        if (
            not isinstance(reasons, list)
            or len(reasons) > len(_REASONS)
            or len(reasons) != len(set(reasons))
            or any(not isinstance(reason, str) or not _REASON_RE.fullmatch(reason) for reason in reasons)
            or any(reason not in _REASONS for reason in reasons)
        ):
            raise ValueError("consumer reason_codes are outside the closed set")
        if not isinstance(body["consumer_live_eligible"], bool):
            raise ValueError("consumer_live_eligible must be boolean")
        if body["consumer_live_eligible"] is (bool(reasons)):
            raise ValueError("consumer eligibility and reasons are inconsistent")
        if body["authority_kind"] != "EVIDENCE_ONLY":
            raise ValueError("consumer readback cannot carry authority")
        for field in _FALSE_FIELDS:
            if body[field] is not False:
                raise ValueError(f"{field} must remain false")
        if isinstance(body["resource_effect_count"], bool) or body["resource_effect_count"] != 0:
            raise ValueError("resource_effect_count must remain zero")
        _sha(body["consumer_readback_sha256"], "consumer_readback_sha256")
        if body["consumer_readback_sha256"] != _digest(body):
            raise ValueError("consumer readback digest mismatch")
        return cls(_freeze(body), _token=_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)

    @property
    def consumer_live_eligible(self) -> bool:
        return bool(self._data["consumer_live_eligible"])


def _require_same(actual: Any, expected: Any, message: str) -> None:
    if actual != expected:
        raise ValueError(message)


def compile_local_voice_catalog_consumer_readback(
    *,
    candidate: LocalVoiceCatalogCandidateV1,
    assessment: LocalVoiceCatalogAssessmentV1,
    compiled_admission: CompiledLocalVoiceCatalogAdmissionV1,
    route_selection: VoiceProfileRouteSelection,
    route_currentness: VoiceRouteSelectionCurrentnessEvaluation,
    narration_preflight: LocalPrimaryNarrationPreflight,
    evaluated_at: str,
) -> LocalVoiceCatalogConsumerReadbackV1:
    """Bind exact source records into a non-executing consumer readback."""

    if not isinstance(candidate, LocalVoiceCatalogCandidateV1):
        raise TypeError("candidate must be LocalVoiceCatalogCandidateV1")
    if not isinstance(assessment, LocalVoiceCatalogAssessmentV1):
        raise TypeError("assessment must be LocalVoiceCatalogAssessmentV1")
    if not isinstance(compiled_admission, CompiledLocalVoiceCatalogAdmissionV1):
        raise TypeError("compiled_admission must be CompiledLocalVoiceCatalogAdmissionV1")
    if not isinstance(compiled_admission.admission, LocalVoiceCatalogAdmissionV1):
        raise TypeError("compiled_admission.admission must be LocalVoiceCatalogAdmissionV1")
    if not isinstance(compiled_admission.inventory, LocalAudioModelInventory):
        raise TypeError("compiled_admission.inventory must be LocalAudioModelInventory")
    if not isinstance(route_selection, VoiceProfileRouteSelection):
        raise TypeError("route_selection must be VoiceProfileRouteSelection")
    if not isinstance(route_currentness, VoiceRouteSelectionCurrentnessEvaluation):
        raise TypeError("route_currentness must be VoiceRouteSelectionCurrentnessEvaluation")
    if not isinstance(narration_preflight, LocalPrimaryNarrationPreflight):
        raise TypeError("narration_preflight must be LocalPrimaryNarrationPreflight")

    # TASK-014's historical dataclass remains publicly constructible. Reparse
    # its full private projection so a hand-built instance cannot bypass the
    # producer's structural and classification checks.
    narration_preflight = parse_local_primary_preflight(narration_preflight.to_private_dict())

    candidate_data = candidate.to_dict()
    assessment_data = assessment.to_dict()
    expected_compiled = compile_local_voice_catalog_admission(candidate, assessment)
    admission_data = compiled_admission.admission.to_dict()
    inventory_data = compiled_admission.inventory.to_public_dict()
    if admission_data != expected_compiled.admission.to_dict():
        raise ValueError("compiled admission is not the canonical candidate/assessment result")
    if inventory_data != expected_compiled.inventory.to_public_dict():
        raise ValueError("compiled inventory is not the canonical candidate/assessment result")
    selection_data = route_selection.to_dict()
    currentness_data = route_currentness.to_dict()
    preflight_data = narration_preflight.to_private_dict()

    _require_same(admission_data["candidate_sha256"], candidate_data["candidate_sha256"], "admission/candidate mismatch")
    _require_same(assessment_data["candidate_sha256"], candidate_data["candidate_sha256"], "assessment/candidate mismatch")
    _require_same(admission_data["assessment_sha256"], assessment_data["assessment_sha256"], "admission/assessment mismatch")
    _require_same(
        admission_data["producer_readback_set_sha256"],
        candidate_data["producer_readback_set_sha256"],
        "admission/candidate producer readback mismatch",
    )
    _require_same(
        assessment_data["producer_readback_set_sha256"],
        candidate_data["producer_readback_set_sha256"],
        "assessment/candidate producer readback mismatch",
    )
    _require_same(admission_data["inventory_sha256"], inventory_data["inventory_sha256"], "admission/inventory mismatch")
    if len(inventory_data["candidates"]) != 1:
        raise ValueError("compiled admission must carry one exact narration candidate")
    inventory_candidate = inventory_data["candidates"][0]
    _require_same(
        admission_data["inventory_candidate_sha256"],
        inventory_candidate["candidate_sha256"],
        "admission/inventory candidate mismatch",
    )
    for field in ("candidate_id", "provider_id", "model_id"):
        _require_same(inventory_candidate[field], candidate_data[field], f"inventory/candidate {field} mismatch")
    if admission_data["admission_state"] == CatalogAdmissionState.ADMITTED.value:
        _require_same(
            inventory_candidate["execution_port_id"],
            candidate_data["execution_port_id"],
            "inventory/candidate execution_port_id mismatch",
        )
    _require_same(inventory_candidate["evidence_sha256"], candidate_data["candidate_sha256"], "inventory evidence mismatch")
    _require_same(inventory_candidate["purpose"], "NARRATION", "consumer inventory is not narration")

    if route_selection.route_mode is not RouteMode.FINE_TUNED_LOCAL:
        raise ValueError("LVC-C1 requires a fine-tuned TASK-074 route")
    _require_same(selection_data["source_requirement"], SourceRequirement.MODEL_CANDIDATE_REQUIRED.value, "route source requirement mismatch")
    _require_same(selection_data["voice_profile_revision_sha256"], candidate_data["voice_profile_revision_sha256"], "route voice-profile mismatch")
    _require_same(selection_data["consent_current_evaluation_sha256"], candidate_data["consent_currentness_sha256"], "route Consent currentness mismatch")
    _require_same(selection_data["installed_route_binding_sha256"], candidate_data["installed_binding_sha256"], "route installed-binding mismatch")
    _require_same(selection_data["local_audio_model_inventory_revision_sha256"], admission_data["inventory_sha256"], "route inventory revision mismatch")
    _require_same(selection_data["local_audio_model_inventory_entry_sha256"], admission_data["inventory_candidate_sha256"], "route inventory entry mismatch")
    _require_same(selection_data["model_license_evidence_sha256"], candidate_data["license_evidence_sha256"], "route license mismatch")
    _require_same(selection_data["model_candidate_revision_sha256"], candidate_data["model_candidate_revision_sha256"], "route ModelCandidate mismatch")

    for currentness_field, selection_field in (
        ("selection_sha256", "selection_sha256"),
        ("route_mode", "route_mode"),
        ("project_manifest_revision_sha256", "project_manifest_revision_sha256"),
        ("voice_profile_revision_sha256", "voice_profile_revision_sha256"),
        ("consent_current_evaluation_sha256", "consent_current_evaluation_sha256"),
        ("selection_created_at", "created_at"),
        ("consent_evaluated_at", "consent_evaluated_at"),
        ("consent_expires_at", "consent_expires_at"),
        ("installed_route_binding_sha256", "installed_route_binding_sha256"),
        ("local_audio_model_inventory_entry_sha256", "local_audio_model_inventory_entry_sha256"),
        ("model_license_evidence_sha256", "model_license_evidence_sha256"),
        ("model_candidate_revision_sha256", "model_candidate_revision_sha256"),
        ("model_candidate_currentness_sha256", "model_candidate_currentness_sha256"),
    ):
        _require_same(
            currentness_data[currentness_field],
            selection_data[selection_field],
            f"route currentness {currentness_field} mismatch",
        )
    for field, candidate_field in (
        ("voice_profile_revision_sha256", "voice_profile_revision_sha256"),
        ("installed_route_binding_sha256", "installed_binding_sha256"),
        ("model_license_evidence_sha256", "license_evidence_sha256"),
        ("model_candidate_revision_sha256", "model_candidate_revision_sha256"),
    ):
        _require_same(currentness_data[field], candidate_data[candidate_field], f"route currentness {field} mismatch")
    _require_same(
        currentness_data["local_audio_model_inventory_entry_sha256"],
        admission_data["inventory_candidate_sha256"],
        "route currentness inventory entry mismatch",
    )

    if narration_preflight.route_mode is not LocalNarrationRouteMode.FINE_TUNED_LOCAL:
        raise ValueError("LVC-C1 requires a fine-tuned TASK-014 preflight")
    _require_same(preflight_data["project_id"], selection_data["project_id"], "preflight Project mismatch")
    voice = preflight_data["voice_profile_revision_binding"]
    engine = preflight_data["engine_admission_binding"]
    fine_tuned = preflight_data["fine_tuned_model_binding"]
    if fine_tuned is None:
        raise ValueError("fine-tuned preflight binding is missing")
    _require_same(voice["voice_profile_id"], selection_data["voice_profile_id"], "preflight voice-profile ID mismatch")
    _require_same(voice["voice_profile_revision_sha256"], candidate_data["voice_profile_revision_sha256"], "preflight voice-profile revision mismatch")
    _require_same(engine["engine_id"], candidate_data["engine_id"], "preflight engine mismatch")
    _require_same(engine["model_artifact_id"], candidate_data["model_id"], "preflight model identity mismatch")
    _require_same(engine["model_artifact_sha256"], candidate_data["model_pair_sha256"], "preflight model pair mismatch")
    _require_same(engine["runtime_sha256"], candidate_data["runtime_build_sha256"], "preflight runtime mismatch")
    _require_same(engine["license_evidence_sha256"], candidate_data["license_evidence_sha256"], "preflight license mismatch")
    _require_same(engine["capability_probe_sha256"], candidate_data["capability_map_sha256"], "preflight capability mismatch")
    _require_same(fine_tuned["model_candidate_revision_sha256"], candidate_data["model_candidate_revision_sha256"], "preflight ModelCandidate mismatch")
    _require_same(fine_tuned["model_artifact_binding_sha256"], candidate_data["installed_binding_sha256"], "preflight installed binding mismatch")
    _require_same(fine_tuned["owner_model_approval_decision_sha256"], candidate_data["h4_approval_sha256"], "preflight H4 approval mismatch")
    _require_same(fine_tuned["consent_current_evaluation_sha256"], candidate_data["consent_currentness_sha256"], "preflight Consent currentness mismatch")

    observed = _timestamp(candidate_data["observed_at"], "candidate.observed_at")
    assessment_time = _timestamp(assessment_data["evaluated_at"], "assessment.evaluated_at")
    selection_time = _timestamp(selection_data["created_at"], "route_selection.created_at")
    currentness_time = _timestamp(currentness_data["evaluated_at"], "route_currentness.evaluated_at")
    preflight_time = _timestamp(preflight_data["created_at"], "narration_preflight.created_at")
    trusted_time = _timestamp(evaluated_at, "evaluated_at")
    expires = _timestamp(candidate_data["expires_at"], "candidate.expires_at")
    consent_expires = _timestamp(selection_data["consent_expires_at"], "route_selection.consent_expires_at")
    if not observed <= assessment_time <= selection_time <= currentness_time <= trusted_time < expires:
        raise ValueError("consumer evidence times are outside the candidate validity window")
    if trusted_time >= consent_expires:
        raise ValueError("consumer trusted time is outside the TASK-074 Consent validity window")
    if not observed <= preflight_time <= trusted_time:
        raise ValueError("narration preflight time is outside the candidate validity window")

    reasons: list[str] = []
    if admission_data["admission_state"] != CatalogAdmissionState.ADMITTED.value:
        reasons.append("CATALOG_ADMISSION_NOT_ADMITTED")
    if inventory_candidate["selectable"] is not True:
        reasons.append("INVENTORY_CANDIDATE_NOT_SELECTABLE")
    if currentness_data["result"] != CurrentnessResult.RUNNABLE.value or currentness_data["runnable_current"] is not True:
        reasons.append("ROUTE_CURRENTNESS_NOT_RUNNABLE")
    if narration_preflight.decision is not PreflightDecision.READY_FOR_OWNER_HUMAN_GATE:
        reasons.append("NARRATION_PREFLIGHT_NOT_READY")
    reasons = list(dict.fromkeys(reasons))

    body: dict[str, Any] = {
        "contract_version": CONSUMER_READBACK_VERSION,
        "record_type": "LocalVoiceCatalogConsumerReadbackV1",
        "candidate_sha256": candidate_data["candidate_sha256"],
        "assessment_sha256": assessment_data["assessment_sha256"],
        "admission_sha256": admission_data["admission_sha256"],
        "producer_readback_set_sha256": candidate_data["producer_readback_set_sha256"],
        "inventory_sha256": admission_data["inventory_sha256"],
        "inventory_candidate_sha256": admission_data["inventory_candidate_sha256"],
        "route_selection_sha256": selection_data["selection_sha256"],
        "route_currentness_evaluation_sha256": currentness_data["currentness_evaluation_sha256"],
        "route_currentness_readback_set_sha256": currentness_data["producer_readback_set_sha256"],
        "narration_preflight_sha256": preflight_data["preflight_sha256"],
        "project_id": selection_data["project_id"],
        "voice_profile_id": selection_data["voice_profile_id"],
        "voice_profile_revision_sha256": candidate_data["voice_profile_revision_sha256"],
        "model_candidate_revision_sha256": candidate_data["model_candidate_revision_sha256"],
        "installed_binding_sha256": candidate_data["installed_binding_sha256"],
        "license_evidence_sha256": candidate_data["license_evidence_sha256"],
        "model_pair_sha256": candidate_data["model_pair_sha256"],
        "engine_id": candidate_data["engine_id"],
        "evaluated_at": evaluated_at,
        "consumer_live_eligible": not reasons,
        "reason_codes": reasons,
        "authority_kind": "EVIDENCE_ONLY",
        **{field: False for field in _FALSE_FIELDS},
        "resource_effect_count": 0,
    }
    body["consumer_readback_sha256"] = _digest(body)
    return LocalVoiceCatalogConsumerReadbackV1.from_dict(body)


__all__ = [
    "CONSUMER_READBACK_VERSION",
    "LocalVoiceCatalogConsumerReadbackV1",
    "compile_local_voice_catalog_consumer_readback",
]
