"""TASK-014 Local Primary narration preflight metadata contract.

This module is intentionally non-executing.  It validates body-free bindings and
classifies whether an exact local narration plan may be shown at the Owner Human
Gate.  It never loads a model, reads audio, resolves a credential, reserves a GPU,
contacts a provider, renders narration, or publishes an Asset.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Mapping
import copy
import re

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .voice_profile_revision import ConsentReference, ConsentState


SCHEMA_ID = "bai.task014.local-primary-narration-preflight.v1"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")


class ContractState(str, Enum):
    CANONICAL_REF_NOT_PROVIDED = "CANONICAL_REF_NOT_PROVIDED"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class LocalNarrationRouteMode(str, Enum):
    ZERO_SHOT_LOCAL = "ZERO_SHOT_LOCAL"
    FINE_TUNED_LOCAL = "FINE_TUNED_LOCAL"


class NarrationIntendedUsage(str, Enum):
    PREVIEW = "PREVIEW"
    FULL_RENDER = "FULL_RENDER"


class PreflightDecision(str, Enum):
    READY_FOR_OWNER_HUMAN_GATE = "READY_FOR_OWNER_HUMAN_GATE"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


def _id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _timestamp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{name} must be an RFC3339 UTC timestamp")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be an RFC3339 UTC timestamp") from exc
    return value


def _expect_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _enum(enum_type: type[Enum], value: Any, name: str) -> Enum:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


def _digest(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a SHA-256 digest")
    return validate_sha256(value, field_name=name)


def _copy(value: Mapping[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(dict(value))


def _null_when_unresolved(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    if any(value[field] is not None for field in fields):
        raise ValueError(f"{name} unresolved binding must not invent canonical fields")


def _validate_script_text_binding(value: Mapping[str, Any]) -> None:
    expected = {
        "text_owner", "approved_text_revision_ref", "approved_text_revision_sha256",
        "source_text_binding_sha256", "approved", "body_persisted",
    }
    _expect_keys(value, expected, "ScriptTextRevisionBinding")
    if value["text_owner"] not in {"TASK-006", "TASK-006/SRT"}:
        raise ValueError("text_owner is not canonical")
    _id(value["approved_text_revision_ref"], "approved_text_revision_ref")
    _digest(value["approved_text_revision_sha256"], "approved_text_revision_sha256")
    _digest(value["source_text_binding_sha256"], "source_text_binding_sha256")
    if not isinstance(value["approved"], bool):
        raise ValueError("approved must be boolean")
    if value["body_persisted"] is not False:
        raise ValueError("script/text body must not be persisted")


def _validate_voice_profile_binding(value: Mapping[str, Any]) -> None:
    expected = {
        "contract_state", "voice_profile_id", "canonical_narration_profile_sha256",
        "revision", "parent_revision_sha256", "voice_profile_revision_sha256",
        "consent", "current_consent_state", "current_consent_evaluation_sha256",
        "canonical_evidence_ref", "canonical_evidence_sha256",
    }
    _expect_keys(value, expected, "VoiceProfileRevisionBinding")
    state = _enum(ContractState, value["contract_state"], "voice profile contract_state")
    nullable = expected - {"contract_state"}
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        _null_when_unresolved(value, nullable, "VoiceProfileRevisionBinding")
        return
    for field in ("voice_profile_id", "canonical_evidence_ref"):
        if value[field] is not None:
            _id(value[field], field)
    for field in (
        "canonical_narration_profile_sha256", "parent_revision_sha256",
        "voice_profile_revision_sha256", "current_consent_evaluation_sha256",
        "canonical_evidence_sha256",
    ):
        _digest(value[field], field, nullable=True)
    revision = value["revision"]
    if revision is not None:
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            raise ValueError("voice profile revision must be >= 1")
        if revision == 1 and value["parent_revision_sha256"] is not None:
            raise ValueError("first VoiceProfileRevision cannot have a parent")
        if revision > 1 and value["parent_revision_sha256"] is None:
            raise ValueError("later VoiceProfileRevision requires a parent")
    if value["consent"] is not None:
        ConsentReference.from_dict(value["consent"])
    if value["current_consent_state"] is not None:
        _enum(ConsentState, value["current_consent_state"], "current_consent_state")
    if state is ContractState.BOUND_VERIFIED:
        required = nullable - {"parent_revision_sha256"}
        if any(value[field] is None for field in required):
            raise ValueError("BOUND_VERIFIED VoiceProfileRevisionBinding is incomplete")


def _validate_engine_binding(value: Mapping[str, Any], mode: LocalNarrationRouteMode) -> None:
    expected = {
        "contract_state", "route_mode", "engine_id", "engine_revision_sha256", "model_artifact_id",
        "model_artifact_sha256", "runtime_id", "runtime_sha256", "code_revision_sha256",
        "license_state", "license_evidence_ref", "license_evidence_sha256",
        "capability_probe_state", "capability_probe_ref", "capability_probe_sha256",
    }
    _expect_keys(value, expected, "EngineAdmissionBinding")
    state = _enum(ContractState, value["contract_state"], "engine contract_state")
    nullable = expected - {"contract_state"}
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        _null_when_unresolved(value, nullable, "EngineAdmissionBinding")
        return
    if value["route_mode"] is not None:
        bound_mode = _enum(LocalNarrationRouteMode, value["route_mode"], "engine route_mode")
        if bound_mode is not mode:
            raise ValueError("engine route_mode mismatch")
    for field in (
        "engine_id", "model_artifact_id", "runtime_id", "license_evidence_ref",
        "capability_probe_ref",
    ):
        if value[field] is not None:
            _id(value[field], field)
    for field in (
        "engine_revision_sha256", "model_artifact_sha256", "runtime_sha256",
        "code_revision_sha256", "license_evidence_sha256", "capability_probe_sha256",
    ):
        _digest(value[field], field, nullable=True)
    license_states = {
        "COMMERCIAL_ALLOWED", "NONCOMMERCIAL_ONLY", "RESTRICTED",
        "LEGAL_REVIEW_REQUIRED", "REVOKED", "UNKNOWN",
    }
    if value["license_state"] is not None and value["license_state"] not in license_states:
        raise ValueError("license_state is invalid")
    if value["capability_probe_state"] is not None and value["capability_probe_state"] not in {
        "VERIFIED", "FAILED", "UNKNOWN",
    }:
        raise ValueError("capability_probe_state is invalid")
    if state is ContractState.BOUND_VERIFIED and any(value[field] is None for field in nullable):
        raise ValueError("BOUND_VERIFIED EngineAdmissionBinding is incomplete")


def _validate_resource_binding(value: Mapping[str, Any], mode: LocalNarrationRouteMode) -> None:
    expected = {
        "contract_state", "route_mode", "resource_profile_ref", "resource_profile_sha256",
        "result", "evidence_ref", "evidence_sha256",
    }
    _expect_keys(value, expected, "ResourceFeasibilityBinding")
    state = _enum(ContractState, value["contract_state"], "resource contract_state")
    nullable = expected - {"contract_state"}
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        _null_when_unresolved(value, nullable, "ResourceFeasibilityBinding")
        return
    if value["route_mode"] is not None:
        bound_mode = _enum(LocalNarrationRouteMode, value["route_mode"], "resource route_mode")
        if bound_mode is not mode:
            raise ValueError("resource route_mode mismatch")
    for field in ("resource_profile_ref", "evidence_ref"):
        if value[field] is not None:
            _id(value[field], field)
    for field in ("resource_profile_sha256", "evidence_sha256"):
        _digest(value[field], field, nullable=True)
    if value["result"] is not None and value["result"] not in {"PASS", "FAIL", "UNKNOWN"}:
        raise ValueError("resource result is invalid")
    if state is ContractState.BOUND_VERIFIED and any(value[field] is None for field in nullable):
        raise ValueError("BOUND_VERIFIED ResourceFeasibilityBinding is incomplete")


def _validate_rights_binding(value: Mapping[str, Any], usage: NarrationIntendedUsage) -> None:
    expected = {
        "contract_state", "usage_class", "state", "evidence_ref", "evidence_sha256",
        "evaluated_at",
    }
    _expect_keys(value, expected, "NarrationRightsBinding")
    state = _enum(ContractState, value["contract_state"], "rights contract_state")
    nullable = expected - {"contract_state"}
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        _null_when_unresolved(value, nullable, "NarrationRightsBinding")
        return
    expected_usage = "LOCAL_NARRATION_PREVIEW" if usage is NarrationIntendedUsage.PREVIEW else "LOCAL_NARRATION_FULL_RENDER"
    if value["usage_class"] is not None and value["usage_class"] != expected_usage:
        raise ValueError("rights usage_class mismatch")
    if value["state"] is not None and value["state"] not in {
        "PASS", "LEGAL_REVIEW_REQUIRED", "REVOKED", "MISMATCH", "UNKNOWN",
    }:
        raise ValueError("rights state is invalid")
    if value["evidence_ref"] is not None:
        _id(value["evidence_ref"], "rights evidence_ref")
    _digest(value["evidence_sha256"], "rights evidence_sha256", nullable=True)
    if value["evaluated_at"] is not None:
        _timestamp(value["evaluated_at"], "rights evaluated_at")
    if state is ContractState.BOUND_VERIFIED and any(value[field] is None for field in nullable):
        raise ValueError("BOUND_VERIFIED NarrationRightsBinding is incomplete")


def _validate_zero_shot_binding(value: Mapping[str, Any]) -> None:
    expected = {
        "contract_state", "asset_id", "asset_checksum_sha256",
        "asset_revision_binding_ref", "asset_revision_binding_sha256",
        "reference_profile_ref", "reference_profile_sha256",
        "consent_current_evaluation_sha256", "rights_current_evaluation_sha256",
        "audio_body_persisted",
    }
    _expect_keys(value, expected, "ZeroShotReferenceBinding")
    state = _enum(ContractState, value["contract_state"], "zero-shot contract_state")
    if value["audio_body_persisted"] is not False:
        raise ValueError("zero-shot reference must remain body-free")
    nullable = expected - {"contract_state", "audio_body_persisted"}
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        _null_when_unresolved(value, nullable, "ZeroShotReferenceBinding")
        return
    for field in ("asset_id", "asset_revision_binding_ref", "reference_profile_ref"):
        if value[field] is not None:
            _id(value[field], field)
    for field in nullable - {"asset_id", "asset_revision_binding_ref", "reference_profile_ref"}:
        _digest(value[field], field, nullable=True)
    if state is ContractState.BOUND_VERIFIED and any(value[field] is None for field in nullable):
        raise ValueError("BOUND_VERIFIED ZeroShotReferenceBinding is incomplete")


def _validate_fine_tuned_binding(value: Mapping[str, Any]) -> None:
    expected = {
        "contract_state", "dataset_revision_id", "dataset_revision_sha256",
        "training_input_snapshot_id", "training_input_snapshot_sha256",
        "model_candidate_revision_id", "model_candidate_revision_sha256",
        "model_artifact_binding_ref", "model_artifact_binding_sha256",
        "owner_model_approval_decision_ref", "owner_model_approval_decision_sha256",
        "consent_current_evaluation_sha256", "rights_current_evaluation_sha256",
        "dataset_body_persisted", "model_bytes_persisted",
    }
    _expect_keys(value, expected, "FineTunedModelBinding")
    state = _enum(ContractState, value["contract_state"], "fine-tuned contract_state")
    if value["dataset_body_persisted"] is not False or value["model_bytes_persisted"] is not False:
        raise ValueError("fine-tuned binding must remain body-free")
    nullable = expected - {"contract_state", "dataset_body_persisted", "model_bytes_persisted"}
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        _null_when_unresolved(value, nullable, "FineTunedModelBinding")
        return
    id_fields = {
        "dataset_revision_id", "training_input_snapshot_id", "model_candidate_revision_id",
        "model_artifact_binding_ref", "owner_model_approval_decision_ref",
    }
    for field in id_fields:
        if value[field] is not None:
            _id(value[field], field)
    for field in nullable - id_fields:
        _digest(value[field], field, nullable=True)
    if state is ContractState.BOUND_VERIFIED and any(value[field] is None for field in nullable):
        raise ValueError("BOUND_VERIFIED FineTunedModelBinding is incomplete")


def _state_reason(prefix: str, state: ContractState) -> tuple[str, bool]:
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        return f"{prefix}_CANONICAL_REF_NOT_PROVIDED", True
    if state is ContractState.UNKNOWN:
        return f"{prefix}_UNKNOWN", True
    if state is ContractState.MISMATCH:
        return f"{prefix}_MISMATCH", False
    return "", False


def _classify(
    *,
    mode: LocalNarrationRouteMode,
    usage: NarrationIntendedUsage,
    script: Mapping[str, Any],
    voice: Mapping[str, Any],
    engine: Mapping[str, Any],
    resource: Mapping[str, Any],
    rights: Mapping[str, Any],
    route_binding: Mapping[str, Any],
) -> tuple[PreflightDecision, tuple[str, ...]]:
    blocked: list[str] = []
    unknown: list[str] = []
    if script["approved"] is not True:
        blocked.append("SCRIPT_TEXT_NOT_APPROVED")
    for prefix, binding in (
        ("VOICE_PROFILE", voice), ("ENGINE", engine), ("RESOURCE", resource),
        ("RIGHTS", rights), ("ZERO_SHOT_REFERENCE" if mode is LocalNarrationRouteMode.ZERO_SHOT_LOCAL else "FINE_TUNED_MODEL", route_binding),
    ):
        reason, is_unknown = _state_reason(prefix, ContractState(binding["contract_state"]))
        if reason:
            (unknown if is_unknown else blocked).append(reason)
    if ContractState(voice["contract_state"]) is ContractState.BOUND_VERIFIED:
        consent = ConsentReference.from_dict(voice["consent"])
        current = ConsentState(voice["current_consent_state"])
        if consent.state is ConsentState.UNKNOWN or current is ConsentState.UNKNOWN:
            unknown.append("CONSENT_CURRENT_STATE_UNKNOWN")
        elif consent.state is not ConsentState.ACTIVE or current is not ConsentState.ACTIVE:
            blocked.append("CONSENT_REVOKED_OR_INACTIVE")
        if not consent.subject_verified:
            blocked.append("CONSENT_SUBJECT_NOT_VERIFIED")
        if "OWNER_NARRATION_LOCAL" not in consent.allowed_usage_classes:
            blocked.append("CONSENT_USAGE_NOT_ALLOWED")
    if ContractState(engine["contract_state"]) is ContractState.BOUND_VERIFIED:
        if engine["capability_probe_state"] == "UNKNOWN":
            unknown.append("ENGINE_CAPABILITY_UNKNOWN")
        elif engine["capability_probe_state"] != "VERIFIED":
            blocked.append("ENGINE_CAPABILITY_FAILED")
        if engine["license_state"] in {"UNKNOWN", "LEGAL_REVIEW_REQUIRED"}:
            unknown.append("ENGINE_LICENSE_NOT_DECIDED")
        elif engine["license_state"] != "COMMERCIAL_ALLOWED":
            blocked.append("ENGINE_LICENSE_NOT_ADMITTED")
    if ContractState(resource["contract_state"]) is ContractState.BOUND_VERIFIED:
        if resource["result"] == "UNKNOWN":
            unknown.append("RESOURCE_FEASIBILITY_UNKNOWN")
        elif resource["result"] != "PASS":
            blocked.append("RESOURCE_FEASIBILITY_FAILED")
    if ContractState(rights["contract_state"]) is ContractState.BOUND_VERIFIED:
        if rights["state"] in {"UNKNOWN", "LEGAL_REVIEW_REQUIRED"}:
            unknown.append("RIGHTS_NOT_DECIDED")
        elif rights["state"] != "PASS":
            blocked.append("RIGHTS_NOT_ADMITTED")
    if blocked:
        return PreflightDecision.BLOCKED, tuple(sorted(set(blocked + unknown)))
    if unknown:
        return PreflightDecision.UNKNOWN, tuple(sorted(set(unknown)))
    return PreflightDecision.READY_FOR_OWNER_HUMAN_GATE, ()


@dataclass(frozen=True, slots=True)
class LocalPrimaryNarrationPreflight:
    project_id: str
    preflight_id: str
    created_at: str
    route_mode: LocalNarrationRouteMode
    intended_usage: NarrationIntendedUsage
    script_text_binding: Mapping[str, Any]
    voice_profile_revision_binding: Mapping[str, Any]
    engine_admission_binding: Mapping[str, Any]
    resource_feasibility_binding: Mapping[str, Any]
    rights_evaluation_binding: Mapping[str, Any]
    zero_shot_reference_binding: Mapping[str, Any] | None
    fine_tuned_model_binding: Mapping[str, Any] | None
    decision: PreflightDecision
    reason_codes: tuple[str, ...]

    def _body(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_ID,
            "task_owner": "TASK-014",
            "project_id": self.project_id,
            "preflight_id": self.preflight_id,
            "created_at": self.created_at,
            "route_mode": self.route_mode.value,
            "intended_usage": self.intended_usage.value,
            "script_text_binding": _copy(self.script_text_binding),
            "voice_profile_revision_binding": _copy(self.voice_profile_revision_binding),
            "engine_admission_binding": _copy(self.engine_admission_binding),
            "resource_feasibility_binding": _copy(self.resource_feasibility_binding),
            "rights_evaluation_binding": _copy(self.rights_evaluation_binding),
            "zero_shot_reference_binding": None if self.zero_shot_reference_binding is None else _copy(self.zero_shot_reference_binding),
            "fine_tuned_model_binding": None if self.fine_tuned_model_binding is None else _copy(self.fine_tuned_model_binding),
            "decision": self.decision.value,
            "reason_codes": list(self.reason_codes),
            "script_body_persisted": False,
            "audio_body_persisted": False,
            "credential_value_persisted": False,
            "absolute_path_persisted": False,
            "execution_started": False,
            "model_loaded": False,
            "gpu_reserved": False,
            "asset_published": False,
        }

    @property
    def preflight_sha256(self) -> str:
        return sha256_bytes(canonical_json_bytes(self._body()))

    def to_private_dict(self) -> dict[str, Any]:
        body = self._body()
        body["preflight_sha256"] = self.preflight_sha256
        return body

    def to_public_dict(self) -> dict[str, Any]:
        body = {
            "schema": SCHEMA_ID,
            "task_owner": "TASK-014",
            "project_id": self.project_id,
            "preflight_id": self.preflight_id,
            "route_mode": self.route_mode.value,
            "intended_usage": self.intended_usage.value,
            "decision": self.decision.value,
            "reason_codes": list(self.reason_codes),
            "voice_profile_binding_state": self.voice_profile_revision_binding["contract_state"],
            "engine_binding_state": self.engine_admission_binding["contract_state"],
            "resource_binding_state": self.resource_feasibility_binding["contract_state"],
            "rights_binding_state": self.rights_evaluation_binding["contract_state"],
            "private_reference_persisted": False,
            "text_digest_persisted": False,
            "audio_hash_persisted": False,
            "credential_value_persisted": False,
            "absolute_path_persisted": False,
            "execution_started": False,
        }
        body["public_projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


def compile_local_primary_preflight(
    *,
    project_id: str,
    preflight_id: str,
    created_at: str,
    route_mode: LocalNarrationRouteMode,
    intended_usage: NarrationIntendedUsage,
    script_text_binding: Mapping[str, Any],
    voice_profile_revision_binding: Mapping[str, Any],
    engine_admission_binding: Mapping[str, Any],
    resource_feasibility_binding: Mapping[str, Any],
    rights_evaluation_binding: Mapping[str, Any],
    zero_shot_reference_binding: Mapping[str, Any] | None,
    fine_tuned_model_binding: Mapping[str, Any] | None,
) -> LocalPrimaryNarrationPreflight:
    _id(project_id, "project_id")
    _id(preflight_id, "preflight_id")
    _timestamp(created_at, "created_at")
    if not isinstance(route_mode, LocalNarrationRouteMode):
        raise ValueError("route_mode must be a LocalNarrationRouteMode")
    if not isinstance(intended_usage, NarrationIntendedUsage):
        raise ValueError("intended_usage must be a NarrationIntendedUsage")
    _validate_script_text_binding(script_text_binding)
    _validate_voice_profile_binding(voice_profile_revision_binding)
    _validate_engine_binding(engine_admission_binding, route_mode)
    _validate_resource_binding(resource_feasibility_binding, route_mode)
    _validate_rights_binding(rights_evaluation_binding, intended_usage)
    if route_mode is LocalNarrationRouteMode.ZERO_SHOT_LOCAL:
        if zero_shot_reference_binding is None or fine_tuned_model_binding is not None:
            raise ValueError("ZERO_SHOT_LOCAL requires only ZeroShotReferenceBinding")
        _validate_zero_shot_binding(zero_shot_reference_binding)
        route_binding = zero_shot_reference_binding
    else:
        if fine_tuned_model_binding is None or zero_shot_reference_binding is not None:
            raise ValueError("FINE_TUNED_LOCAL requires only FineTunedModelBinding")
        _validate_fine_tuned_binding(fine_tuned_model_binding)
        route_binding = fine_tuned_model_binding
    decision, reasons = _classify(
        mode=route_mode,
        usage=intended_usage,
        script=script_text_binding,
        voice=voice_profile_revision_binding,
        engine=engine_admission_binding,
        resource=resource_feasibility_binding,
        rights=rights_evaluation_binding,
        route_binding=route_binding,
    )
    return LocalPrimaryNarrationPreflight(
        project_id=project_id,
        preflight_id=preflight_id,
        created_at=created_at,
        route_mode=route_mode,
        intended_usage=intended_usage,
        script_text_binding=_copy(script_text_binding),
        voice_profile_revision_binding=_copy(voice_profile_revision_binding),
        engine_admission_binding=_copy(engine_admission_binding),
        resource_feasibility_binding=_copy(resource_feasibility_binding),
        rights_evaluation_binding=_copy(rights_evaluation_binding),
        zero_shot_reference_binding=None if zero_shot_reference_binding is None else _copy(zero_shot_reference_binding),
        fine_tuned_model_binding=None if fine_tuned_model_binding is None else _copy(fine_tuned_model_binding),
        decision=decision,
        reason_codes=reasons,
    )


def parse_local_primary_preflight(value: Mapping[str, Any]) -> LocalPrimaryNarrationPreflight:
    expected = {
        "schema", "task_owner", "project_id", "preflight_id", "created_at", "route_mode",
        "intended_usage", "script_text_binding", "voice_profile_revision_binding",
        "engine_admission_binding", "resource_feasibility_binding", "rights_evaluation_binding",
        "zero_shot_reference_binding", "fine_tuned_model_binding", "decision", "reason_codes",
        "script_body_persisted", "audio_body_persisted", "credential_value_persisted",
        "absolute_path_persisted", "execution_started", "model_loaded", "gpu_reserved",
        "asset_published", "preflight_sha256",
    }
    _expect_keys(value, expected, "LocalPrimaryNarrationPreflight")
    if value["schema"] != SCHEMA_ID or value["task_owner"] != "TASK-014":
        raise ValueError("unsupported LocalPrimaryNarrationPreflight identity")
    for field in (
        "script_body_persisted", "audio_body_persisted", "credential_value_persisted",
        "absolute_path_persisted", "execution_started", "model_loaded", "gpu_reserved",
        "asset_published",
    ):
        if value[field] is not False:
            raise ValueError(f"{field} violates the non-executing boundary")
    reasons = value["reason_codes"]
    if not isinstance(reasons, list) or any(not isinstance(item, str) for item in reasons):
        raise ValueError("reason_codes must be a string list")
    compiled = compile_local_primary_preflight(
        project_id=value["project_id"],
        preflight_id=value["preflight_id"],
        created_at=value["created_at"],
        route_mode=LocalNarrationRouteMode(value["route_mode"]),
        intended_usage=NarrationIntendedUsage(value["intended_usage"]),
        script_text_binding=value["script_text_binding"],
        voice_profile_revision_binding=value["voice_profile_revision_binding"],
        engine_admission_binding=value["engine_admission_binding"],
        resource_feasibility_binding=value["resource_feasibility_binding"],
        rights_evaluation_binding=value["rights_evaluation_binding"],
        zero_shot_reference_binding=value["zero_shot_reference_binding"],
        fine_tuned_model_binding=value["fine_tuned_model_binding"],
    )
    if compiled.decision.value != value["decision"] or list(compiled.reason_codes) != reasons:
        raise ValueError("preflight classification mismatch")
    if compiled.preflight_sha256 != value["preflight_sha256"]:
        raise ValueError("preflight checksum mismatch")
    return compiled


__all__ = [
    "ContractState", "LocalNarrationRouteMode", "NarrationIntendedUsage",
    "PreflightDecision", "LocalPrimaryNarrationPreflight",
    "compile_local_primary_preflight", "parse_local_primary_preflight",
]
