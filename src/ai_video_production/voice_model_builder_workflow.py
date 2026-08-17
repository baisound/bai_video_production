"""Pure TASK-046/P-VS-4B OBS-to-model-to-Master workflow contract.

The module composes canonical coordinates owned by TASK-047, P-QC-1A,
TASK-003, P-VS-3B, P-VS-4A and TASK-014.  It never reads a WAV, creates a
Dataset or Job, starts training/rendering, writes an artifact, or approves a
model/Master.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import inspect
import re
from types import MappingProxyType
from typing import Any, ClassVar, Mapping

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_ID = "bai.task046.voice-model-builder-workflow.v1"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_REASON_RE = re.compile(r"[A-Z][A-Z0-9_]{1,95}")
_PRIVATE_TERMS = ("credential", "password", "secret", "private-key", "raw-audio")


class ContractState(str, Enum):
    CANONICAL_REF_NOT_PROVIDED = "CANONICAL_REF_NOT_PROVIDED"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class SourceKind(str, Enum):
    OBS_CAPTURE_SESSION = "OBS_CAPTURE_SESSION"
    QUALITY_EVALUATION = "QUALITY_EVALUATION"
    TASK003_ASSET_REVISION = "TASK003_ASSET_REVISION"
    TRAINING_INPUT_SNAPSHOT = "TRAINING_INPUT_SNAPSHOT"
    TRAINING_RUN_REVISION = "TRAINING_RUN_REVISION"
    MODEL_CANDIDATE_REVISION = "MODEL_CANDIDATE_REVISION"
    OWNER_MODEL_APPROVAL = "OWNER_MODEL_APPROVAL"
    NARRATION_RENDER_ADMISSION = "NARRATION_RENDER_ADMISSION"


class CueState(str, Enum):
    PENDING = "PENDING"
    EXTERNAL_RENDER_REQUESTED = "EXTERNAL_RENDER_REQUESTED"
    RENDERED_BOUND = "RENDERED_BOUND"
    FAILED_KNOWN = "FAILED_KNOWN"
    UNKNOWN = "UNKNOWN"


class WorkflowState(str, Enum):
    RECORDINGS_REVIEW_REQUIRED = "RECORDINGS_REVIEW_REQUIRED"
    DATASET_PROPOSAL_READY = "DATASET_PROPOSAL_READY"
    DATASET_ADOPTION_BLOCKED = "DATASET_ADOPTION_BLOCKED"
    TRAINING_RECIPE_NOT_VERIFIED = "TRAINING_RECIPE_NOT_VERIFIED"
    READY_FOR_OWNER_TRAINING_CONFIRMATION = "READY_FOR_OWNER_TRAINING_CONFIRMATION"
    TRAINING_IN_PROGRESS = "TRAINING_IN_PROGRESS"
    TRAINING_COMPLETED_ARTIFACT_UNBOUND = "TRAINING_COMPLETED_ARTIFACT_UNBOUND"
    MODEL_CANDIDATE_REGISTERED = "MODEL_CANDIDATE_REGISTERED"
    EVALUATION_PENDING = "EVALUATION_PENDING"
    EVALUATED_CANDIDATE = "EVALUATED_CANDIDATE"
    OWNER_APPROVED = "OWNER_APPROVED"
    STYLE_CUES_PENDING = "STYLE_CUES_PENDING"
    MASTER_ASSEMBLY_PENDING = "MASTER_ASSEMBLY_PENDING"
    MASTER_REVIEW_REQUIRED = "MASTER_REVIEW_REQUIRED"
    MASTER_ACCEPTED = "MASTER_ACCEPTED"
    MASTER_REJECTED = "MASTER_REJECTED"
    FAILED_KNOWN = "FAILED_KNOWN"
    UNKNOWN = "UNKNOWN"


class OperationKind(str, Enum):
    DATASET_ADOPTION = "DATASET_ADOPTION"
    TRAINING_DISPATCH = "TRAINING_DISPATCH"
    STYLE_CUE_RENDER = "STYLE_CUE_RENDER"
    MASTER_ASSEMBLY = "MASTER_ASSEMBLY"


class FactState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


def _id(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    folded = value.casefold()
    if (
        "\\" in value
        or value.startswith("/")
        or re.match(r"^[A-Za-z]:/", value) is not None
        or any(p == ".." for p in value.split("/"))
    ):
        raise ValueError(f"{name} must be a contained logical identifier")
    if any(term in folded for term in _PRIVATE_TERMS):
        raise ValueError(f"{name} violates the body-free boundary")
    return value


def _sha(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be SHA-256")
    return validate_sha256(value, field_name=name)


def _timestamp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{name} must be RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be RFC3339 UTC") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{name} must be UTC")
    return value


def _enum(kind: type[Enum], value: Any, name: str) -> Enum:
    try:
        return kind(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


def _expect(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _reasons(value: Any) -> None:
    if not isinstance(value, list) or len(value) > 64 or len(value) != len(set(value)):
        raise ValueError("reason_codes must be a unique bounded list")
    if any(not isinstance(item, str) or not _REASON_RE.fullmatch(item) for item in value):
        raise ValueError("reason_codes contain an invalid value")


def _digest_body(value: Mapping[str, Any], field: str) -> str:
    return sha256_bytes(canonical_json_bytes({k: v for k, v in value.items() if k != field}))


def add_record_digest(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = dict(value)
    result[field] = _digest_body(result, field)
    return result


def _verify_digest(value: Mapping[str, Any], field: str) -> None:
    _sha(value[field], field)
    if value[field] != _digest_body(value, field):
        raise ValueError(f"{field} mismatch")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


def _validate_source(value: Mapping[str, Any]) -> None:
    fields = {"record_type", "contract_state", "source_kind", "canonical_ref", "canonical_revision", "canonical_sha256", "current_valid", "evaluated_at", "binding_sha256"}
    _expect(value, fields, "CanonicalSourceBinding")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    _enum(SourceKind, value["source_kind"], "source_kind")
    if state is ContractState.BOUND_VERIFIED:
        _id(value["canonical_ref"], "canonical_ref")
        if not isinstance(value["canonical_revision"], int) or value["canonical_revision"] < 1:
            raise ValueError("canonical_revision is invalid")
        _sha(value["canonical_sha256"], "canonical_sha256")
        if value["current_valid"] is not True:
            raise ValueError("BOUND_VERIFIED source must be current_valid")
        _timestamp(value["evaluated_at"], "evaluated_at")
    elif any(value[k] is not None for k in ("canonical_ref", "canonical_revision", "canonical_sha256", "current_valid", "evaluated_at")):
        raise ValueError("unresolved source must not invent canonical fields")
    _verify_digest(value, "binding_sha256")


def _validate_cue(value: Mapping[str, Any]) -> None:
    fields = {"record_type", "cue_id", "revision", "parent_cue_sha256", "workflow_id", "order_index", "script_revision_sha256", "text_start", "text_end", "style_direction_sha256", "model_candidate_sha256", "voice_profile_revision_sha256", "render_admission_sha256", "state", "external_render_receipt_ref", "external_render_receipt_sha256", "cue_artifact_ref", "cue_artifact_sha256", "audio_body_persisted", "created_at", "cue_sha256"}
    _expect(value, fields, "StyleCueRevision")
    for name in ("cue_id", "workflow_id"):
        _id(value[name], name)
    if not isinstance(value["revision"], int) or value["revision"] < 1:
        raise ValueError("revision is invalid")
    _sha(value["parent_cue_sha256"], "parent_cue_sha256", nullable=True)
    if (value["revision"] == 1) != (value["parent_cue_sha256"] is None):
        raise ValueError("cue parent/revision lineage mismatch")
    if not isinstance(value["order_index"], int) or value["order_index"] < 0:
        raise ValueError("order_index is invalid")
    for name in ("text_start", "text_end"):
        if not isinstance(value[name], int) or value[name] < 0:
            raise ValueError(f"{name} is invalid")
    if value["text_end"] <= value["text_start"]:
        raise ValueError("Cue text range must be non-empty")
    for name in ("script_revision_sha256", "style_direction_sha256", "model_candidate_sha256", "voice_profile_revision_sha256", "render_admission_sha256"):
        _sha(value[name], name)
    state = _enum(CueState, value["state"], "state")
    output = (value["external_render_receipt_ref"], value["external_render_receipt_sha256"], value["cue_artifact_ref"], value["cue_artifact_sha256"])
    if state is CueState.RENDERED_BOUND:
        _id(output[0], "external_render_receipt_ref")
        _sha(output[1], "external_render_receipt_sha256")
        _id(output[2], "cue_artifact_ref")
        _sha(output[3], "cue_artifact_sha256")
    elif any(item is not None for item in output):
        raise ValueError("unrendered Cue cannot claim receipt/artifact")
    if value["audio_body_persisted"] is not False:
        raise ValueError("Cue metadata cannot persist audio")
    _timestamp(value["created_at"], "created_at")
    _verify_digest(value, "cue_sha256")


def _validate_policy(value: Mapping[str, Any]) -> None:
    fields = {"record_type", "contract_state", "sample_rate_hz", "channels", "sample_format", "pause_policy_sha256", "loudness_policy_state", "loudness_policy_sha256", "boundary_policy_state", "boundary_policy_sha256", "identity_policy_state", "identity_policy_sha256", "max_crossfade_samples", "policy_sha256"}
    _expect(value, fields, "MasterAssemblyPolicyBinding")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    policy_states = tuple(_enum(ContractState, value[k], k) for k in ("loudness_policy_state", "boundary_policy_state", "identity_policy_state"))
    if value["sample_rate_hz"] != 48000 or value["channels"] != 1 or value["sample_format"] != "PCM_S24LE":
        raise ValueError("Master canonical format must be 48 kHz / 24-bit integer PCM / mono")
    if not isinstance(value["max_crossfade_samples"], int) or not 0 <= value["max_crossfade_samples"] <= 48000:
        raise ValueError("max_crossfade_samples is invalid")
    digests = ("pause_policy_sha256", "loudness_policy_sha256", "boundary_policy_sha256", "identity_policy_sha256")
    if state is ContractState.BOUND_VERIFIED and all(s is ContractState.BOUND_VERIFIED for s in policy_states):
        for name in digests:
            _sha(value[name], name)
    elif any(value[name] is not None for name in digests):
        raise ValueError("unresolved policy must not invent policy digests")
    _verify_digest(value, "policy_sha256")


def _validate_master(value: Mapping[str, Any]) -> None:
    fields = {"record_type", "master_id", "revision", "parent_master_sha256", "workflow_id", "ordered_cue_sha256", "model_candidate_sha256", "voice_profile_revision_sha256", "assembly_policy_sha256", "external_assembly_receipt_ref", "external_assembly_receipt_sha256", "master_artifact_ref", "master_artifact_sha256", "format_state", "boundary_state", "loudness_state", "identity_continuity_state", "style_state", "owner_acceptance", "audio_body_persisted", "asset_adoption_started", "publication_started", "created_at", "master_sha256"}
    _expect(value, fields, "MasterWavCandidateRevision")
    for name in ("master_id", "workflow_id"):
        _id(value[name], name)
    if not isinstance(value["revision"], int) or value["revision"] < 1:
        raise ValueError("revision is invalid")
    _sha(value["parent_master_sha256"], "parent_master_sha256", nullable=True)
    if (value["revision"] == 1) != (value["parent_master_sha256"] is None):
        raise ValueError("Master parent/revision lineage mismatch")
    cues = value["ordered_cue_sha256"]
    if not isinstance(cues, list) or not 2 <= len(cues) <= 4096 or len(cues) != len(set(cues)):
        raise ValueError("Master requires at least two unique ordered Cues")
    for cue in cues:
        _sha(cue, "ordered_cue_sha256")
    for name in ("model_candidate_sha256", "voice_profile_revision_sha256", "assembly_policy_sha256"):
        _sha(value[name], name)
    receipt = (value["external_assembly_receipt_ref"], value["external_assembly_receipt_sha256"], value["master_artifact_ref"], value["master_artifact_sha256"])
    facts = tuple(_enum(FactState, value[k], k) for k in ("format_state", "boundary_state", "loudness_state", "identity_continuity_state", "style_state"))
    acceptance = value["owner_acceptance"]
    if acceptance not in {"PENDING", "ACCEPTED", "REJECTED"}:
        raise ValueError("owner_acceptance is invalid")
    if any(item is not None for item in receipt):
        _id(receipt[0], "external_assembly_receipt_ref")
        _sha(receipt[1], "external_assembly_receipt_sha256")
        _id(receipt[2], "master_artifact_ref")
        _sha(receipt[3], "master_artifact_sha256")
    if acceptance == "ACCEPTED" and (not all(f is FactState.PASS for f in facts) or any(item is None for item in receipt)):
        raise ValueError("Master acceptance requires bound artifact and all QA PASS")
    for name in ("audio_body_persisted", "asset_adoption_started", "publication_started"):
        if value[name] is not False:
            raise ValueError(f"{name} must remain false")
    _timestamp(value["created_at"], "created_at")
    _verify_digest(value, "master_sha256")


def _validate_workflow(value: Mapping[str, Any]) -> None:
    fields = {"record_type", "workflow_id", "revision", "parent_workflow_sha256", "project_id", "source_bindings", "state", "ordered_cue_sha256", "master_candidate_sha256", "reason_codes", "created_at", "dataset_effect_started", "training_started", "render_started", "workflow_sha256"}
    _expect(value, fields, "VerticalSliceWorkflowRevision")
    for name in ("workflow_id", "project_id"):
        _id(value[name], name)
    if not isinstance(value["revision"], int) or value["revision"] < 1:
        raise ValueError("revision is invalid")
    _sha(value["parent_workflow_sha256"], "parent_workflow_sha256", nullable=True)
    if (value["revision"] == 1) != (value["parent_workflow_sha256"] is None):
        raise ValueError("workflow parent/revision lineage mismatch")
    sources = value["source_bindings"]
    if not isinstance(sources, list) or not 1 <= len(sources) <= 32:
        raise ValueError("source_bindings are invalid")
    kinds: set[str] = set()
    for source in sources:
        validated = validate_record(source, expected_type="CanonicalSourceBinding")
        if validated["source_kind"] in kinds:
            raise ValueError("source_kind must be unique")
        kinds.add(validated["source_kind"])
    _enum(WorkflowState, value["state"], "state")
    cues = value["ordered_cue_sha256"]
    if not isinstance(cues, list) or len(cues) > 4096 or len(cues) != len(set(cues)):
        raise ValueError("ordered Cue list is invalid")
    for cue in cues:
        _sha(cue, "ordered_cue_sha256")
    _sha(value["master_candidate_sha256"], "master_candidate_sha256", nullable=True)
    _reasons(value["reason_codes"])
    _timestamp(value["created_at"], "created_at")
    for name in ("dataset_effect_started", "training_started", "render_started"):
        if value[name] is not False:
            raise ValueError(f"{name} must remain false")
    _verify_digest(value, "workflow_sha256")


def _validate_request(value: Mapping[str, Any]) -> None:
    fields = {"record_type", "request_id", "operation_kind", "workflow_sha256", "subject_sha256", "authorization_binding_sha256", "idempotency_key", "request_state", "dispatch_started", "created_at", "request_sha256"}
    _expect(value, fields, "ExternalOperationRequest")
    _id(value["request_id"], "request_id")
    _enum(OperationKind, value["operation_kind"], "operation_kind")
    for name in ("workflow_sha256", "subject_sha256", "authorization_binding_sha256"):
        _sha(value[name], name)
    _id(value["idempotency_key"], "idempotency_key")
    if value["request_state"] != "PROPOSAL_ONLY" or value["dispatch_started"] is not False:
        raise ValueError("application service can only create an undispatched proposal")
    _timestamp(value["created_at"], "created_at")
    _verify_digest(value, "request_sha256")


_VALIDATORS = {
    "CanonicalSourceBinding": _validate_source,
    "StyleCueRevision": _validate_cue,
    "MasterAssemblyPolicyBinding": _validate_policy,
    "MasterWavCandidateRevision": _validate_master,
    "VerticalSliceWorkflowRevision": _validate_workflow,
    "ExternalOperationRequest": _validate_request,
}


def validate_record(value: Mapping[str, Any], *, expected_type: str | None = None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("record must be an object")
    record_type = value.get("record_type")
    if expected_type is not None and record_type != expected_type:
        raise ValueError("record_type mismatch")
    validator = _VALIDATORS.get(record_type)
    if validator is None:
        raise ValueError("record_type is unknown")
    copy = _thaw(value)
    validator(copy)
    return copy


@dataclass(frozen=True, slots=True)
class _Record:
    data: Mapping[str, Any]
    RECORD_TYPE: ClassVar[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", _freeze(validate_record(self.data, expected_type=self.RECORD_TYPE)))

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.data)

    def canonical_json(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


class CanonicalSourceBinding(_Record): RECORD_TYPE = "CanonicalSourceBinding"
class StyleCueRevision(_Record): RECORD_TYPE = "StyleCueRevision"
class MasterAssemblyPolicyBinding(_Record): RECORD_TYPE = "MasterAssemblyPolicyBinding"
class MasterWavCandidateRevision(_Record): RECORD_TYPE = "MasterWavCandidateRevision"
class VerticalSliceWorkflowRevision(_Record): RECORD_TYPE = "VerticalSliceWorkflowRevision"
class ExternalOperationRequest(_Record): RECORD_TYPE = "ExternalOperationRequest"


def compile_operation_request(*, request_id: str, operation_kind: str, workflow: Mapping[str, Any], subject_sha256: str, authorization_binding_sha256: str, idempotency_key: str, created_at: str) -> ExternalOperationRequest:
    validated = validate_record(workflow, expected_type="VerticalSliceWorkflowRevision")
    body = {
        "record_type": "ExternalOperationRequest",
        "request_id": request_id,
        "operation_kind": operation_kind,
        "workflow_sha256": validated["workflow_sha256"],
        "subject_sha256": subject_sha256,
        "authorization_binding_sha256": authorization_binding_sha256,
        "idempotency_key": idempotency_key,
        "request_state": "PROPOSAL_ONLY",
        "dispatch_started": False,
        "created_at": created_at,
    }
    return ExternalOperationRequest(add_record_digest(body, "request_sha256"))


def validate_workflow_transition(previous: Mapping[str, Any], current: Mapping[str, Any]) -> None:
    old = validate_record(previous, expected_type="VerticalSliceWorkflowRevision")
    new = validate_record(current, expected_type="VerticalSliceWorkflowRevision")
    if old["workflow_id"] != new["workflow_id"] or new["revision"] != old["revision"] + 1:
        raise ValueError("workflow revision identity/sequence mismatch")
    if new["parent_workflow_sha256"] != old["workflow_sha256"]:
        raise ValueError("workflow parent CAS mismatch")


def beginner_projection(workflow: Mapping[str, Any]) -> dict[str, Any]:
    value = validate_record(workflow, expected_type="VerticalSliceWorkflowRevision")
    labels = {
        "RECORDINGS_REVIEW_REQUIRED": "録音を確認してください",
        "DATASET_PROPOSAL_READY": "学習に使う録音候補を確認できます",
        "READY_FOR_OWNER_TRAINING_CONFIRMATION": "学習開始の確認待ちです",
        "TRAINING_IN_PROGRESS": "学習処理中です",
        "OWNER_APPROVED": "モデルがOwner承認済みです",
        "STYLE_CUES_PENDING": "スタイル別音声の準備中です",
        "MASTER_REVIEW_REQUIRED": "完成候補を試聴してください",
        "MASTER_ACCEPTED": "完成音声が承認されました",
        "UNKNOWN": "状態を確認できません",
    }
    return {
        "workflow_id": value["workflow_id"],
        "revision": value["revision"],
        "state": value["state"],
        "friendly_ja": labels.get(value["state"], value["state"]),
        "reason_codes": list(value["reason_codes"]),
        "cue_count": len(value["ordered_cue_sha256"]),
        "master_candidate_present": value["master_candidate_sha256"] is not None,
        "effect_authorized": False,
    }


def assert_no_effect_surface() -> None:
    source = inspect.getsource(inspect.getmodule(assert_no_effect_surface))
    forbidden_tokens = tuple(
        left + right
        for left, right in (
            ("import ", "requests"),
            ("import ", "subprocess"),
            ("import ", "socket"),
            ("import ", "torch"),
            ("from ", "pathlib"),
            ("op", "en("),
        )
    )
    for forbidden in forbidden_tokens:
        if forbidden in source:
            raise AssertionError(f"forbidden effect surface: {forbidden}")
