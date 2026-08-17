"""TASK-046/P-VS-4A body-free Training Run and Model Candidate contract.

The module validates immutable metadata and produces pure admission reports.
It does not create Jobs, reserve resources, start a process, train or load a
model, persist/merge artifacts, analyze audio, approve a model, or publish it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Mapping
import copy
import re

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_ID = "bai.task046.voice-training-run.v1"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")


class ContractState(str, Enum):
    CANONICAL_REF_NOT_PROVIDED = "CANONICAL_REF_NOT_PROVIDED"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class TrainingMode(str, Enum):
    FULL_FINE_TUNE = "FULL_FINE_TUNE"
    PARAMETER_EFFICIENT_FINE_TUNE = "PARAMETER_EFFICIENT_FINE_TUNE"
    ADAPTER_OR_LORA = "ADAPTER_OR_LORA"


class TrainingRunState(str, Enum):
    DRAFT = "DRAFT"
    PREFLIGHT_PENDING = "PREFLIGHT_PENDING"
    BLOCKED = "BLOCKED"
    READY_FOR_OWNER_HUMAN_GATE = "READY_FOR_OWNER_HUMAN_GATE"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    CHECKPOINTED = "CHECKPOINTED"
    PAUSED_SAFE = "PAUSED_SAFE"
    STOP_REQUESTED = "STOP_REQUESTED"
    TRAINING_COMPLETED_ARTIFACT_UNBOUND = "TRAINING_COMPLETED_ARTIFACT_UNBOUND"
    MODEL_CANDIDATE_REGISTERED = "MODEL_CANDIDATE_REGISTERED"
    EVALUATION_PENDING = "EVALUATION_PENDING"
    EVALUATED_CANDIDATE = "EVALUATED_CANDIDATE"
    FAILED_KNOWN = "FAILED_KNOWN"
    UNKNOWN = "UNKNOWN"
    CANCELLED_SAFE = "CANCELLED_SAFE"


class ArtifactKind(str, Enum):
    FULL_MODEL = "FULL_MODEL"
    PEFT_ADAPTER = "PEFT_ADAPTER"
    LORA_ADAPTER = "LORA_ADAPTER"
    MERGED_MODEL = "MERGED_MODEL"
    ENGINE_NATIVE_BUNDLE = "ENGINE_NATIVE_BUNDLE"
    UNKNOWN = "UNKNOWN"


class MergeState(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNMERGED = "UNMERGED"
    MERGED_VERIFIED = "MERGED_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class DecisionState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


def _expect_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _id(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _sha(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be SHA-256")
    return validate_sha256(value, field_name=name)


def _timestamp(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{name} must be RFC3339 UTC")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be RFC3339 UTC") from exc
    return value


def _integer(value: Any, name: str, *, minimum: int = 0, nullable: bool = False) -> int | None:
    if value is None and nullable:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _boolean(value: Any, name: str, *, exact: bool | None = None) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be boolean")
    if exact is not None and value is not exact:
        raise ValueError(f"{name} must be {str(exact).lower()}")
    return value


def _enum(enum_type: type[Enum], value: Any, name: str) -> Enum:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


def _digest_payload(value: Mapping[str, Any], digest_field: str) -> str:
    body = copy.deepcopy(dict(value))
    body.pop(digest_field, None)
    return sha256_bytes(canonical_json_bytes(body))


def add_record_digest(value: Mapping[str, Any], digest_field: str) -> dict[str, Any]:
    body = copy.deepcopy(dict(value))
    body[digest_field] = _digest_payload(body, digest_field)
    return body


def _verify_digest(value: Mapping[str, Any], digest_field: str) -> None:
    if _sha(value[digest_field], digest_field) != _digest_payload(value, digest_field):
        raise ValueError(f"{digest_field} mismatch")


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


def _validate_reason_codes(value: Any) -> None:
    if not isinstance(value, list) or len(value) > 64:
        raise ValueError("reason_codes must be a bounded list")
    for item in value:
        _id(item, "reason_code")
    if value != sorted(set(value)):
        raise ValueError("reason_codes must be sorted and unique")


def _validate_structured_binding(
    value: Mapping[str, Any],
    *,
    name: str,
    digest_field: str,
    fields: set[str],
    id_fields: set[str] = frozenset(),
    sha_fields: set[str] = frozenset(),
    timestamp_fields: set[str] = frozenset(),
) -> ContractState:
    expected = {"record_type", "contract_state", digest_field} | fields
    _expect_keys(value, expected, name)
    state = _enum(ContractState, value["contract_state"], "contract_state")
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in fields):
            raise ValueError(f"{name} unresolved state must not invent canonical fields")
    elif state is ContractState.BOUND_VERIFIED:
        if any(value[field] is None for field in fields):
            raise ValueError(f"{name} BOUND_VERIFIED fields are incomplete")
    for field in id_fields:
        _id(value[field], field, nullable=state is not ContractState.BOUND_VERIFIED)
    for field in sha_fields:
        _sha(value[field], field, nullable=state is not ContractState.BOUND_VERIFIED)
    for field in timestamp_fields:
        _timestamp(value[field], field, nullable=state is not ContractState.BOUND_VERIFIED)
    _verify_digest(value, digest_field)
    return state


def _validate_engine(value: Mapping[str, Any]) -> None:
    fields = {
        "engine_id", "engine_repository_ref", "engine_commit_sha256",
        "package_lock_sha256", "training_mode", "capability_state",
        "license_state", "base_model_id", "base_model_revision",
        "base_model_sha256", "runtime_revision", "runtime_sha256",
        "code_revision", "code_sha256", "weight_revision", "weight_sha256",
        "tokenizer_sha256", "codec_sha256", "vocoder_sha256", "config_sha256",
        "target_probe_profile_ref", "target_probe_profile_sha256",
        "evidence_ref", "evidence_sha256",
    }
    state = _validate_structured_binding(
        value, name="EngineAdmissionBinding", digest_field="binding_sha256",
        fields=fields,
        id_fields={
            "engine_id", "engine_repository_ref", "base_model_id",
            "base_model_revision", "runtime_revision", "code_revision",
            "weight_revision", "target_probe_profile_ref", "evidence_ref",
        },
        sha_fields={field for field in fields if field.endswith("sha256")},
    )
    if state is ContractState.BOUND_VERIFIED:
        _enum(TrainingMode, value["training_mode"], "training_mode")
        if value["capability_state"] not in {"ADMITTED", "BLOCKED", "PROBE_REQUIRED", "UNKNOWN"}:
            raise ValueError("capability_state is invalid")
        if value["license_state"] not in {"PASS", "LEGAL_REVIEW_REQUIRED", "UNKNOWN", "REVOKED", "MISMATCH"}:
            raise ValueError("license_state is invalid")


def _validate_output_destination(value: Mapping[str, Any]) -> None:
    fields = {
        "canonical_owner_ref", "canonical_owner_sha256", "storage_policy_ref",
        "storage_policy_sha256", "logical_uri", "encryption_policy_sha256",
        "recovery_policy_sha256", "retention_policy_sha256",
        "disk_quota_admission_ref", "disk_quota_admission_sha256",
        "allowed_artifact_classes", "public_exposure",
    }
    state = _validate_structured_binding(
        value, name="OutputArtifactDestinationBinding", digest_field="binding_sha256",
        fields=fields,
        id_fields={"canonical_owner_ref", "storage_policy_ref", "logical_uri", "disk_quota_admission_ref"},
        sha_fields={field for field in fields if field.endswith("sha256")},
    )
    if state is ContractState.BOUND_VERIFIED:
        if not isinstance(value["allowed_artifact_classes"], list) or not value["allowed_artifact_classes"]:
            raise ValueError("allowed_artifact_classes must be non-empty")
        for item in value["allowed_artifact_classes"]:
            if item not in {"CHECKPOINT", "MODEL_OUTPUT", "LOG", "EVALUATION_OUTPUT"}:
                raise ValueError("allowed_artifact_classes is invalid")
        if value["allowed_artifact_classes"] != sorted(set(value["allowed_artifact_classes"])):
            raise ValueError("allowed_artifact_classes must be sorted and unique")
        _boolean(value["public_exposure"], "public_exposure", exact=False)
        if value["logical_uri"].startswith(("/", "\\", "file:", "http:", "https:")) or ".." in value["logical_uri"].split("/"):
            raise ValueError("logical_uri must be private logical identity without traversal")


def _validate_feasibility(value: Mapping[str, Any]) -> None:
    fields = {
        "mode", "recipe_revision_ref", "recipe_revision_sha256",
        "probe_profile_ref", "probe_profile_sha256", "target_gpu_ref",
        "target_vram_bytes", "peak_vram_bytes", "peak_ram_bytes",
        "optimizer_overhead_bytes", "checkpoint_overhead_bytes",
        "representative_batch", "representative_sequence_units",
        "thermal_floor_state", "disk_floor_state", "oom_recovery_state",
        "expected_duration_seconds", "headroom_policy_ref",
        "headroom_policy_sha256", "admission_state", "evidence_ref",
        "evidence_sha256",
    }
    state = _validate_structured_binding(
        value, name="TargetResourceFeasibilityBinding", digest_field="binding_sha256",
        fields=fields,
        id_fields={
            "recipe_revision_ref", "probe_profile_ref", "target_gpu_ref",
            "headroom_policy_ref", "evidence_ref",
        },
        sha_fields={field for field in fields if field.endswith("sha256")},
    )
    if state is ContractState.BOUND_VERIFIED:
        _enum(TrainingMode, value["mode"], "mode")
        for field in (
            "target_vram_bytes", "peak_vram_bytes", "peak_ram_bytes",
            "optimizer_overhead_bytes", "checkpoint_overhead_bytes",
            "representative_batch", "representative_sequence_units",
            "expected_duration_seconds",
        ):
            _integer(value[field], field, minimum=1)
        for field in ("thermal_floor_state", "disk_floor_state", "oom_recovery_state"):
            if value[field] not in {"PASS", "FAIL", "UNKNOWN"}:
                raise ValueError(f"{field} is invalid")
        if value["admission_state"] not in {"ADMITTED", "BLOCKED", "PROBE_REQUIRED", "UNKNOWN"}:
            raise ValueError("admission_state is invalid")
        if value["admission_state"] == "ADMITTED" and any(value[field] != "PASS" for field in ("thermal_floor_state", "disk_floor_state", "oom_recovery_state")):
            raise ValueError("feasibility cannot be ADMITTED with non-PASS floors/recovery")


def _validate_reservation(value: Mapping[str, Any]) -> None:
    fields = {
        "reservation_id", "receipt_ref", "receipt_sha256", "gpu_ref",
        "cpu_units", "ram_bytes", "vram_bytes", "disk_bytes",
        "thermal_state", "power_state", "admission_state", "issued_at",
        "expires_at",
    }
    state = _validate_structured_binding(
        value, name="ExecutionResourceReservationBinding", digest_field="binding_sha256",
        fields=fields, id_fields={"reservation_id", "receipt_ref", "gpu_ref"},
        sha_fields={"receipt_sha256"}, timestamp_fields={"issued_at", "expires_at"},
    )
    if state is ContractState.BOUND_VERIFIED:
        for field in ("cpu_units", "ram_bytes", "vram_bytes", "disk_bytes"):
            _integer(value[field], field, minimum=1)
        if value["thermal_state"] not in {"PASS", "FAIL", "UNKNOWN"} or value["power_state"] not in {"PASS", "FAIL", "UNKNOWN"}:
            raise ValueError("reservation thermal/power state is invalid")
        if value["admission_state"] not in {"ADMITTED", "BLOCKED", "UNKNOWN"}:
            raise ValueError("reservation admission_state is invalid")


def _validate_job(value: Mapping[str, Any]) -> None:
    fields = {
        "job_id", "operation_id", "idempotency_key", "job_kind",
        "job_revision", "job_revision_sha256", "job_state",
        "canonical_job_evidence_ref", "canonical_job_evidence_sha256",
        "identity_shared_with_dataset_adoption_job",
    }
    state = _validate_structured_binding(
        value, name="TrainingDurableJobBinding", digest_field="binding_sha256",
        fields=fields,
        id_fields={"job_id", "operation_id", "idempotency_key", "job_kind", "job_state", "canonical_job_evidence_ref"},
        sha_fields={"job_revision_sha256", "canonical_job_evidence_sha256"},
    )
    if state is ContractState.BOUND_VERIFIED:
        _integer(value["job_revision"], "job_revision", minimum=1)
        if value["job_kind"] != "VOICE_MODEL_TRAINING":
            raise ValueError("Training Job cannot reuse PROJECT_MAINTENANCE or Dataset Adoption identity")
        _boolean(value["identity_shared_with_dataset_adoption_job"], "identity_shared_with_dataset_adoption_job", exact=False)


def _validate_authorization(value: Mapping[str, Any]) -> None:
    fields = {
        "authorization_id", "authorization_revision", "authorization_sha256",
        "authority_kind", "project_id", "run_intent_sha256",
        "run_revision_sha256", "training_input_snapshot_sha256",
        "engine_admission_sha256", "config_sha256",
        "current_consent_rights_license_sha256", "scope", "issued_at",
        "expires_at", "one_shot", "replay_policy", "evidence_ref",
        "evidence_sha256",
    }
    state = _validate_structured_binding(
        value, name="TrainingExecutionAuthorizationBinding", digest_field="binding_sha256",
        fields=fields,
        id_fields={
            "authorization_id", "authority_kind", "project_id", "scope",
            "replay_policy", "evidence_ref",
        },
        sha_fields={field for field in fields if field.endswith("sha256")},
        timestamp_fields={"issued_at", "expires_at"},
    )
    if state is ContractState.BOUND_VERIFIED:
        _integer(value["authorization_revision"], "authorization_revision", minimum=1)
        if value["authority_kind"] != "OWNER_HUMAN_GATE":
            raise ValueError("training authorization requires Owner Human Gate")
        if value["scope"] not in {"START", "RESUME"}:
            raise ValueError("authorization scope is invalid")
        _boolean(value["one_shot"], "one_shot", exact=True)
        if value["replay_policy"] != "NO_REPLAY":
            raise ValueError("authorization replay policy must be NO_REPLAY")


def _validate_current_use_rights(value: Mapping[str, Any]) -> None:
    fields = {
        "evaluation_ref", "evaluation_sha256", "consent_state",
        "training_data_rights_state", "reference_audio_rights_state",
        "output_rights_state", "license_state", "evaluated_at",
    }
    state = _validate_structured_binding(
        value, name="CurrentUseRightsBinding", digest_field="binding_sha256",
        fields=fields, id_fields={"evaluation_ref"}, sha_fields={"evaluation_sha256"},
        timestamp_fields={"evaluated_at"},
    )
    if state is ContractState.BOUND_VERIFIED:
        allowed = {"PASS", "LEGAL_REVIEW_REQUIRED", "UNKNOWN", "REVOKED", "MISMATCH"}
        for field in (
            "consent_state", "training_data_rights_state",
            "reference_audio_rights_state", "output_rights_state", "license_state",
        ):
            if value[field] not in allowed:
                raise ValueError(f"{field} is invalid")


def _validate_evaluation_snapshot(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "snapshot_id", "revision", "parent_snapshot_sha256",
        "project_id", "selection_policy_ref", "selection_policy_sha256",
        "selected_items", "private_equivalence_index_sha256", "created_at",
        "audio_body_persisted", "text_body_persisted", "snapshot_sha256",
    }
    _expect_keys(value, expected, "EvaluationInputSnapshot")
    for field in ("snapshot_id", "project_id", "selection_policy_ref"):
        _id(value[field], field)
    _integer(value["revision"], "revision", minimum=1)
    _sha(value["parent_snapshot_sha256"], "parent_snapshot_sha256", nullable=True)
    if value["revision"] == 1 and value["parent_snapshot_sha256"] is not None:
        raise ValueError("first EvaluationInputSnapshot has no parent")
    if value["revision"] > 1 and value["parent_snapshot_sha256"] is None:
        raise ValueError("later EvaluationInputSnapshot requires parent")
    _sha(value["selection_policy_sha256"], "selection_policy_sha256")
    _sha(value["private_equivalence_index_sha256"], "private_equivalence_index_sha256")
    _timestamp(value["created_at"], "created_at")
    if not isinstance(value["selected_items"], list) or not value["selected_items"] or len(value["selected_items"]) > 4096:
        raise ValueError("selected_items must be a bounded non-empty list")
    item_keys = {
        "source_kind", "item_ref", "item_sha256", "dataset_member_entry_sha256",
        "asset_revision_ref", "asset_revision_sha256", "asset_checksum_sha256",
        "sample_start", "sample_end", "consent_evaluation_sha256",
        "evaluation_rights_sha256", "reference_rights_sha256",
        "output_rights_sha256", "approved_labels_sha256",
        "provenance_equivalence_sha256",
    }
    identities: list[tuple[str, int, int]] = []
    for item in value["selected_items"]:
        _expect_keys(item, item_keys, "EvaluationInputItem")
        if item["source_kind"] not in {"PVS3B_DATASET_MEMBER", "TASK003_ASSET_REVISION"}:
            raise ValueError("evaluation source_kind is invalid")
        for field in ("item_ref", "asset_revision_ref"):
            _id(item[field], field)
        for field in item_keys:
            if field.endswith("sha256"):
                _sha(item[field], field, nullable=field == "dataset_member_entry_sha256")
        if item["source_kind"] == "PVS3B_DATASET_MEMBER" and item["dataset_member_entry_sha256"] is None:
            raise ValueError("PVS3B evaluation item requires captured member binding")
        start = _integer(item["sample_start"], "sample_start")
        end = _integer(item["sample_end"], "sample_end", minimum=1)
        if end <= start:
            raise ValueError("evaluation range must be non-empty half-open interval")
        identities.append((item["asset_revision_sha256"], start, end))
    if identities != sorted(set(identities)):
        raise ValueError("evaluation items must be sorted and unique by Asset/range")
    for previous, current in zip(identities, identities[1:]):
        if previous[0] == current[0] and current[1] < previous[2]:
            raise ValueError("evaluation Asset sample ranges must not overlap")
    _boolean(value["audio_body_persisted"], "audio_body_persisted", exact=False)
    _boolean(value["text_body_persisted"], "text_body_persisted", exact=False)
    _verify_digest(value, "snapshot_sha256")


def _validate_contamination(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "training_input_snapshot_ref", "training_input_snapshot_sha256",
        "evaluation_input_snapshot_ref", "evaluation_input_snapshot_sha256",
        "identity_non_overlap", "asset_mapping_non_overlap", "checksum_non_overlap",
        "sample_range_non_overlap", "source_lineage_non_overlap",
        "semantic_policy_state", "semantic_policy_ref", "semantic_policy_sha256",
        "semantic_decision", "decision", "reason_codes", "proof_sha256",
    }
    _expect_keys(value, expected, "ContaminationProofBinding")
    for field in ("training_input_snapshot_ref", "evaluation_input_snapshot_ref"):
        _id(value[field], field)
    for field in ("training_input_snapshot_sha256", "evaluation_input_snapshot_sha256"):
        _sha(value[field], field)
    checks = (
        "identity_non_overlap", "asset_mapping_non_overlap", "checksum_non_overlap",
        "sample_range_non_overlap", "source_lineage_non_overlap",
    )
    for field in checks:
        _boolean(value[field], field)
    state = _enum(ContractState, value["semantic_policy_state"], "semantic_policy_state")
    _id(value["semantic_policy_ref"], "semantic_policy_ref", nullable=state is not ContractState.BOUND_VERIFIED)
    _sha(value["semantic_policy_sha256"], "semantic_policy_sha256", nullable=state is not ContractState.BOUND_VERIFIED)
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED and any(value[field] is not None for field in ("semantic_policy_ref", "semantic_policy_sha256")):
        raise ValueError("unhosted semantic policy must not invent canonical fields")
    if value["semantic_decision"] not in {"PASS", "FAIL", "UNKNOWN"}:
        raise ValueError("semantic_decision is invalid")
    decision = _enum(DecisionState, value["decision"], "decision")
    _validate_reason_codes(value["reason_codes"])
    can_pass = all(value[field] for field in checks) and state is ContractState.BOUND_VERIFIED and value["semantic_decision"] == "PASS"
    if decision is DecisionState.PASS and not can_pass:
        raise ValueError("contamination PASS requires identity/Asset/checksum/range/lineage and semantic proof")
    _verify_digest(value, "proof_sha256")


def _validate_intent(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "run_intent_id", "revision", "parent_intent_sha256",
        "project_id", "training_mode", "training_input_snapshot_ref",
        "training_input_snapshot_sha256", "evaluation_input_snapshot_ref",
        "evaluation_input_snapshot_sha256", "contamination_proof_binding",
        "engine_admission_binding", "output_artifact_destination_binding",
        "target_resource_feasibility_binding", "current_use_rights_binding",
        "current_consent_rights_license_sha256",
        "config_sha256", "created_at", "audio_body_persisted",
        "text_body_persisted", "execution_authorized", "intent_sha256",
    }
    _expect_keys(value, expected, "TrainingRunIntent")
    for field in ("run_intent_id", "project_id", "training_input_snapshot_ref", "evaluation_input_snapshot_ref"):
        _id(value[field], field)
    _integer(value["revision"], "revision", minimum=1)
    _sha(value["parent_intent_sha256"], "parent_intent_sha256", nullable=True)
    if (value["revision"] == 1) != (value["parent_intent_sha256"] is None):
        raise ValueError("TrainingRunIntent parent/revision mismatch")
    _enum(TrainingMode, value["training_mode"], "training_mode")
    for field in (
        "training_input_snapshot_sha256", "evaluation_input_snapshot_sha256",
        "current_consent_rights_license_sha256", "config_sha256",
    ):
        _sha(value[field], field)
    validate_record(value["contamination_proof_binding"], expected_type="ContaminationProofBinding")
    validate_record(value["engine_admission_binding"], expected_type="EngineAdmissionBinding")
    validate_record(value["output_artifact_destination_binding"], expected_type="OutputArtifactDestinationBinding")
    validate_record(value["target_resource_feasibility_binding"], expected_type="TargetResourceFeasibilityBinding")
    validate_record(value["current_use_rights_binding"], expected_type="CurrentUseRightsBinding")
    if value["current_use_rights_binding"]["binding_sha256"] != value["current_consent_rights_license_sha256"]:
        raise ValueError("current rights binding hash mismatch")
    if value["contamination_proof_binding"]["training_input_snapshot_sha256"] != value["training_input_snapshot_sha256"] or value["contamination_proof_binding"]["evaluation_input_snapshot_sha256"] != value["evaluation_input_snapshot_sha256"]:
        raise ValueError("Intent snapshot hashes must match contamination proof")
    if value["engine_admission_binding"]["contract_state"] == "BOUND_VERIFIED" and value["engine_admission_binding"]["training_mode"] != value["training_mode"]:
        raise ValueError("Engine admission training_mode mismatch")
    if value["target_resource_feasibility_binding"]["contract_state"] == "BOUND_VERIFIED" and value["target_resource_feasibility_binding"]["mode"] != value["training_mode"]:
        raise ValueError("Resource feasibility mode cannot be reused across training modes")
    _timestamp(value["created_at"], "created_at")
    for field in ("audio_body_persisted", "text_body_persisted", "execution_authorized"):
        _boolean(value[field], field, exact=False)
    _verify_digest(value, "intent_sha256")


def _validate_checkpoint(value: Mapping[str, Any]) -> None:
    fields = {
        "checkpoint_id", "checkpoint_revision", "canonical_owner_ref",
        "canonical_owner_sha256", "persistence_receipt_ref",
        "persistence_receipt_sha256", "artifact_checksum_sha256",
        "training_input_snapshot_sha256", "base_model_sha256", "runtime_sha256",
        "code_sha256", "config_sha256", "license_evaluation_sha256",
        "consent_evaluation_sha256", "training_step", "optimizer_state_sha256",
        "resume_compatibility_sha256", "resume_decision", "logical_uri",
    }
    state = _validate_structured_binding(
        value, name="CheckpointArtifactBinding", digest_field="binding_sha256",
        fields=fields,
        id_fields={"checkpoint_id", "canonical_owner_ref", "persistence_receipt_ref", "logical_uri"},
        sha_fields={field for field in fields if field.endswith("sha256")},
    )
    if state is ContractState.BOUND_VERIFIED:
        _integer(value["checkpoint_revision"], "checkpoint_revision", minimum=1)
        _integer(value["training_step"], "training_step", minimum=1)
        if value["resume_decision"] not in {"ACCEPT", "BLOCKED", "MISMATCH", "UNKNOWN"}:
            raise ValueError("resume_decision is invalid")
        if value["logical_uri"].startswith(("/", "\\", "file:")):
            raise ValueError("checkpoint must use logical URI, not absolute path")


def _validate_process_observation(value: Mapping[str, Any]) -> None:
    fields = {
        "process_observation_id", "job_id", "process_identity_sha256",
        "observation_state", "gpu_process_present", "observed_at",
        "evidence_ref", "evidence_sha256",
    }
    state = _validate_structured_binding(
        value, name="GPUProcessObservationBinding", digest_field="binding_sha256",
        fields=fields, id_fields={"process_observation_id", "job_id", "evidence_ref"},
        sha_fields={"process_identity_sha256", "evidence_sha256"}, timestamp_fields={"observed_at"},
    )
    if state is ContractState.BOUND_VERIFIED:
        if value["observation_state"] not in {"OBSERVED", "NOT_FOUND", "UNKNOWN"}:
            raise ValueError("observation_state is invalid")
        if value["gpu_process_present"] not in {True, False, None}:
            raise ValueError("gpu_process_present is invalid")
        if value["observation_state"] == "UNKNOWN" and value["gpu_process_present"] is not None:
            raise ValueError("UNKNOWN process observation cannot claim presence")


def _validate_compute_receipt(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "receipt_id", "run_intent_sha256", "run_revision_sha256",
        "job_binding_sha256", "compute_state", "last_checkpoint_binding_sha256",
        "started_at", "terminal_at", "reason_codes", "artifact_registered",
        "receipt_sha256",
    }
    _expect_keys(value, expected, "TrainingComputeTerminalReceipt")
    _id(value["receipt_id"], "receipt_id")
    for field in ("run_intent_sha256", "run_revision_sha256", "job_binding_sha256"):
        _sha(value[field], field)
    _sha(value["last_checkpoint_binding_sha256"], "last_checkpoint_binding_sha256", nullable=True)
    if value["compute_state"] not in {"COMPLETED", "FAILED", "UNKNOWN", "CANCELLED"}:
        raise ValueError("compute_state is invalid")
    _timestamp(value["started_at"], "started_at")
    _timestamp(value["terminal_at"], "terminal_at")
    _validate_reason_codes(value["reason_codes"])
    _boolean(value["artifact_registered"], "artifact_registered", exact=False)
    _verify_digest(value, "receipt_sha256")


def _validate_artifact(value: Mapping[str, Any]) -> None:
    fields = {
        "artifact_id", "artifact_kind", "canonical_owner_ref",
        "canonical_owner_sha256", "persistence_receipt_ref",
        "persistence_receipt_sha256", "artifact_checksum_sha256",
        "artifact_manifest_sha256", "artifact_index_sha256", "component_checksums",
        "serialization_format", "base_model_id", "base_model_revision",
        "base_model_sha256", "base_model_license_sha256", "adapter_format",
        "adapter_config_sha256", "merge_state", "merge_provenance_receipt_ref",
        "merge_provenance_receipt_sha256", "engine_sha256", "runtime_sha256",
        "tokenizer_sha256", "codec_sha256", "vocoder_sha256", "config_sha256",
        "load_compatibility_evidence_ref", "load_compatibility_evidence_sha256",
        "load_compatibility_state", "license_inheritance_state", "logical_uri",
    }
    _expect_keys(value, {"record_type", "contract_state", "binding_sha256"} | fields, "ModelArtifactBinding")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    state_dependent = {
        "adapter_format", "adapter_config_sha256", "merge_provenance_receipt_ref",
        "merge_provenance_receipt_sha256",
    }
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in fields):
            raise ValueError("ModelArtifactBinding unresolved state must not invent canonical fields")
    elif state is ContractState.BOUND_VERIFIED:
        required = fields - state_dependent
        if any(value[field] is None for field in required):
            raise ValueError("ModelArtifactBinding BOUND_VERIFIED fields are incomplete")
    id_fields = {
        "artifact_id", "canonical_owner_ref", "persistence_receipt_ref",
        "serialization_format", "base_model_id", "base_model_revision",
        "adapter_format", "merge_provenance_receipt_ref",
        "load_compatibility_evidence_ref", "logical_uri",
    }
    for field in id_fields:
        _id(value[field], field, nullable=True)
    for field in {field for field in fields if field.endswith("sha256")}:
        _sha(value[field], field, nullable=True)
    _verify_digest(value, "binding_sha256")
    if state is not ContractState.BOUND_VERIFIED:
        return
    kind = _enum(ArtifactKind, value["artifact_kind"], "artifact_kind")
    merge_state = _enum(MergeState, value["merge_state"], "merge_state")
    if not isinstance(value["component_checksums"], list) or not value["component_checksums"]:
        raise ValueError("component_checksums must be non-empty")
    for item in value["component_checksums"]:
        _sha(item, "component_checksum")
    if value["component_checksums"] != sorted(set(value["component_checksums"])):
        raise ValueError("component_checksums must be sorted and unique")
    adapter_fields = ("adapter_format", "adapter_config_sha256")
    merge_fields = ("merge_provenance_receipt_ref", "merge_provenance_receipt_sha256")
    if kind is ArtifactKind.FULL_MODEL:
        if any(value[field] is not None for field in adapter_fields + merge_fields) or merge_state is not MergeState.NOT_APPLICABLE:
            raise ValueError("FULL_MODEL adapter/merge fields must be NOT_APPLICABLE")
    elif kind in {ArtifactKind.PEFT_ADAPTER, ArtifactKind.LORA_ADAPTER}:
        if any(value[field] is None for field in adapter_fields) or any(value[field] is not None for field in merge_fields) or merge_state is not MergeState.UNMERGED:
            raise ValueError("adapter artifact requires exact unmerged composition")
        _id(value["adapter_format"], "adapter_format")
        _sha(value["adapter_config_sha256"], "adapter_config_sha256")
    elif kind is ArtifactKind.MERGED_MODEL:
        if any(value[field] is None for field in adapter_fields + merge_fields) or merge_state is not MergeState.MERGED_VERIFIED:
            raise ValueError("MERGED_MODEL requires base+adapter merge provenance")
    elif kind is ArtifactKind.UNKNOWN:
        raise ValueError("UNKNOWN artifact kind cannot be BOUND_VERIFIED")
    if value["load_compatibility_state"] not in {"PASS", "FAIL", "UNKNOWN", "MISMATCH"}:
        raise ValueError("load_compatibility_state is invalid")
    if value["license_inheritance_state"] not in {"PASS", "LEGAL_REVIEW_REQUIRED", "UNKNOWN", "REVOKED", "MISMATCH"}:
        raise ValueError("license_inheritance_state is invalid")
    if value["logical_uri"].startswith(("/", "\\", "file:")):
        raise ValueError("artifact must use logical URI")


def _validate_candidate(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "candidate_id", "revision", "parent_candidate_sha256",
        "run_intent_sha256", "compute_terminal_receipt_sha256",
        "model_artifact_binding", "candidate_state", "current_consent_rights_license_sha256",
        "created_at", "model_use_authorized", "production_use_authorized",
        "candidate_sha256",
    }
    _expect_keys(value, expected, "ModelCandidateRevision")
    _id(value["candidate_id"], "candidate_id")
    _integer(value["revision"], "revision", minimum=1)
    _sha(value["parent_candidate_sha256"], "parent_candidate_sha256", nullable=True)
    for field in ("run_intent_sha256", "compute_terminal_receipt_sha256", "current_consent_rights_license_sha256"):
        _sha(value[field], field)
    validate_record(value["model_artifact_binding"], expected_type="ModelArtifactBinding")
    if value["model_artifact_binding"]["contract_state"] != "BOUND_VERIFIED":
        raise ValueError("ModelCandidate registration requires BOUND_VERIFIED artifact")
    if value["candidate_state"] not in {"REGISTERED", "EVALUATION_PENDING", "EVALUATED", "STALE", "REJECTED"}:
        raise ValueError("candidate_state is invalid")
    _timestamp(value["created_at"], "created_at")
    _boolean(value["model_use_authorized"], "model_use_authorized", exact=False)
    _boolean(value["production_use_authorized"], "production_use_authorized", exact=False)
    _verify_digest(value, "candidate_sha256")


def _validate_evaluation_receipt(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "evaluation_id", "candidate_sha256", "model_artifact_binding_sha256",
        "evaluation_input_snapshot_sha256", "contamination_proof_sha256",
        "similarity_decision", "pronunciation_decision", "style_emotion_whisper_decision",
        "long_form_decision", "artifact_integrity_decision", "threshold_policy_state",
        "threshold_policy_ref", "threshold_policy_sha256", "held_out_decision",
        "overall_decision", "current_consent_rights_license_sha256",
        "evaluated_at", "audio_analysis_executed", "receipt_sha256",
    }
    _expect_keys(value, expected, "EvaluationReceipt")
    _id(value["evaluation_id"], "evaluation_id")
    for field in (
        "candidate_sha256", "model_artifact_binding_sha256",
        "evaluation_input_snapshot_sha256", "contamination_proof_sha256",
        "current_consent_rights_license_sha256",
    ):
        _sha(value[field], field)
    for field in (
        "similarity_decision", "pronunciation_decision", "style_emotion_whisper_decision",
        "long_form_decision", "artifact_integrity_decision", "held_out_decision",
        "overall_decision",
    ):
        _enum(DecisionState, value[field], field)
    state = _enum(ContractState, value["threshold_policy_state"], "threshold_policy_state")
    _id(value["threshold_policy_ref"], "threshold_policy_ref", nullable=state is not ContractState.BOUND_VERIFIED)
    _sha(value["threshold_policy_sha256"], "threshold_policy_sha256", nullable=state is not ContractState.BOUND_VERIFIED)
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED and any(value[field] is not None for field in ("threshold_policy_ref", "threshold_policy_sha256")):
        raise ValueError("unhosted threshold policy must not invent canonical fields")
    decisions = (
        value["similarity_decision"], value["pronunciation_decision"],
        value["style_emotion_whisper_decision"], value["long_form_decision"],
        value["artifact_integrity_decision"], value["held_out_decision"],
    )
    if value["overall_decision"] == "PASS" and (state is not ContractState.BOUND_VERIFIED or any(item != "PASS" for item in decisions)):
        raise ValueError("Evaluation PASS requires hosted thresholds and all dimensions PASS")
    _timestamp(value["evaluated_at"], "evaluated_at")
    _boolean(value["audio_analysis_executed"], "audio_analysis_executed", exact=False)
    _verify_digest(value, "receipt_sha256")


def _validate_owner_approval(value: Mapping[str, Any]) -> None:
    fields = {
        "decision_id", "decision_revision", "candidate_sha256",
        "evaluation_receipt_sha256", "model_artifact_binding_sha256",
        "artifact_composition_sha256", "current_consent_rights_license_sha256",
        "decision", "decided_at", "reviewer_kind", "human_gate_evidence_ref",
        "human_gate_evidence_sha256",
    }
    state = _validate_structured_binding(
        value, name="OwnerModelApprovalDecisionBinding", digest_field="binding_sha256",
        fields=fields,
        id_fields={"decision_id", "reviewer_kind", "human_gate_evidence_ref"},
        sha_fields={field for field in fields if field.endswith("sha256")},
        timestamp_fields={"decided_at"},
    )
    if state is ContractState.BOUND_VERIFIED:
        _integer(value["decision_revision"], "decision_revision", minimum=1)
        if value["decision"] not in {"APPROVE", "REJECT", "RETEST"}:
            raise ValueError("Owner decision is invalid")
        if value["reviewer_kind"] != "OWNER":
            raise ValueError("Owner approval requires reviewer_kind OWNER")


def _validate_run_revision(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "run_revision_id", "revision", "parent_revision_sha256",
        "run_intent_sha256", "state", "durable_job_binding",
        "resource_reservation_binding", "execution_authorization_binding",
        "process_observation_binding", "checkpoint_artifact_binding",
        "compute_terminal_receipt_sha256", "model_candidate_sha256",
        "evaluation_receipt_sha256", "owner_approval_binding_sha256",
        "reason_codes", "created_at", "execution_started", "revision_sha256",
    }
    _expect_keys(value, expected, "TrainingRunRevision")
    _id(value["run_revision_id"], "run_revision_id")
    _integer(value["revision"], "revision", minimum=1)
    _sha(value["parent_revision_sha256"], "parent_revision_sha256", nullable=True)
    if (value["revision"] == 1) != (value["parent_revision_sha256"] is None):
        raise ValueError("TrainingRunRevision parent/revision mismatch")
    _sha(value["run_intent_sha256"], "run_intent_sha256")
    state = _enum(TrainingRunState, value["state"], "state")
    validate_record(value["durable_job_binding"], expected_type="TrainingDurableJobBinding")
    validate_record(value["resource_reservation_binding"], expected_type="ExecutionResourceReservationBinding")
    validate_record(value["execution_authorization_binding"], expected_type="TrainingExecutionAuthorizationBinding")
    validate_record(value["process_observation_binding"], expected_type="GPUProcessObservationBinding")
    validate_record(value["checkpoint_artifact_binding"], expected_type="CheckpointArtifactBinding")
    for field in (
        "compute_terminal_receipt_sha256", "model_candidate_sha256",
        "evaluation_receipt_sha256", "owner_approval_binding_sha256",
    ):
        _sha(value[field], field, nullable=True)
    if state in {TrainingRunState.QUEUED, TrainingRunState.RUNNING}:
        if value["durable_job_binding"]["contract_state"] != "BOUND_VERIFIED":
            raise ValueError("QUEUED/RUNNING requires TrainingDurableJobBinding")
        if value["resource_reservation_binding"]["contract_state"] != "BOUND_VERIFIED":
            raise ValueError("QUEUED/RUNNING requires live resource reservation")
        if value["execution_authorization_binding"]["contract_state"] != "BOUND_VERIFIED":
            raise ValueError("QUEUED/RUNNING requires Owner execution authorization")
    if state is TrainingRunState.TRAINING_COMPLETED_ARTIFACT_UNBOUND and value["compute_terminal_receipt_sha256"] is None:
        raise ValueError("training completion requires compute terminal receipt")
    if state in {TrainingRunState.MODEL_CANDIDATE_REGISTERED, TrainingRunState.EVALUATION_PENDING, TrainingRunState.EVALUATED_CANDIDATE} and value["model_candidate_sha256"] is None:
        raise ValueError("candidate lifecycle requires ModelCandidateRevision")
    if state is TrainingRunState.EVALUATED_CANDIDATE and value["evaluation_receipt_sha256"] is None:
        raise ValueError("EVALUATED_CANDIDATE requires EvaluationReceipt")
    _validate_reason_codes(value["reason_codes"])
    _timestamp(value["created_at"], "created_at")
    _boolean(value["execution_started"], "execution_started")
    if state in {TrainingRunState.DRAFT, TrainingRunState.PREFLIGHT_PENDING, TrainingRunState.BLOCKED, TrainingRunState.READY_FOR_OWNER_HUMAN_GATE}:
        _boolean(value["execution_started"], "execution_started", exact=False)
    _verify_digest(value, "revision_sha256")


def _validate_report(value: Mapping[str, Any], name: str) -> None:
    expected = {
        "record_type", "run_intent_sha256", "run_revision_sha256", "decision",
        "reason_codes", "evaluated_at", "dispatch_started", "gpu_process_started",
        "training_started", "report_sha256",
    }
    _expect_keys(value, expected, name)
    _sha(value["run_intent_sha256"], "run_intent_sha256")
    _sha(value["run_revision_sha256"], "run_revision_sha256", nullable=name == "TrainingPreflightReport")
    _enum(DecisionState, value["decision"], "decision")
    _validate_reason_codes(value["reason_codes"])
    _timestamp(value["evaluated_at"], "evaluated_at")
    for field in ("dispatch_started", "gpu_process_started", "training_started"):
        _boolean(value[field], field, exact=False)
    _verify_digest(value, "report_sha256")


_VALIDATORS: dict[str, Callable[[Mapping[str, Any]], None]] = {
    "EngineAdmissionBinding": _validate_engine,
    "OutputArtifactDestinationBinding": _validate_output_destination,
    "TargetResourceFeasibilityBinding": _validate_feasibility,
    "ExecutionResourceReservationBinding": _validate_reservation,
    "TrainingDurableJobBinding": _validate_job,
    "TrainingExecutionAuthorizationBinding": _validate_authorization,
    "CurrentUseRightsBinding": _validate_current_use_rights,
    "EvaluationInputSnapshot": _validate_evaluation_snapshot,
    "ContaminationProofBinding": _validate_contamination,
    "TrainingRunIntent": _validate_intent,
    "TrainingRunRevision": _validate_run_revision,
    "TrainingComputeTerminalReceipt": _validate_compute_receipt,
    "CheckpointArtifactBinding": _validate_checkpoint,
    "GPUProcessObservationBinding": _validate_process_observation,
    "ModelArtifactBinding": _validate_artifact,
    "ModelCandidateRevision": _validate_candidate,
    "EvaluationReceipt": _validate_evaluation_receipt,
    "OwnerModelApprovalDecisionBinding": _validate_owner_approval,
    "TrainingPreflightReport": lambda value: _validate_report(value, "TrainingPreflightReport"),
    "TrainingDispatchAdmissionReport": lambda value: _validate_report(value, "TrainingDispatchAdmissionReport"),
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


@dataclass(frozen=True, slots=True)
class _CanonicalRecord:
    data: Mapping[str, Any]
    RECORD_TYPE: ClassVar[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", _freeze(validate_record(self.data, expected_type=self.RECORD_TYPE)))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "_CanonicalRecord":
        return cls(value)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.data)

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


class EngineAdmissionBinding(_CanonicalRecord): RECORD_TYPE = "EngineAdmissionBinding"
class OutputArtifactDestinationBinding(_CanonicalRecord): RECORD_TYPE = "OutputArtifactDestinationBinding"
class TargetResourceFeasibilityBinding(_CanonicalRecord): RECORD_TYPE = "TargetResourceFeasibilityBinding"
class ExecutionResourceReservationBinding(_CanonicalRecord): RECORD_TYPE = "ExecutionResourceReservationBinding"
class TrainingDurableJobBinding(_CanonicalRecord): RECORD_TYPE = "TrainingDurableJobBinding"
class TrainingExecutionAuthorizationBinding(_CanonicalRecord): RECORD_TYPE = "TrainingExecutionAuthorizationBinding"
class CurrentUseRightsBinding(_CanonicalRecord): RECORD_TYPE = "CurrentUseRightsBinding"
class EvaluationInputSnapshot(_CanonicalRecord): RECORD_TYPE = "EvaluationInputSnapshot"
class ContaminationProofBinding(_CanonicalRecord): RECORD_TYPE = "ContaminationProofBinding"
class TrainingRunIntent(_CanonicalRecord): RECORD_TYPE = "TrainingRunIntent"
class TrainingRunRevision(_CanonicalRecord): RECORD_TYPE = "TrainingRunRevision"
class TrainingComputeTerminalReceipt(_CanonicalRecord): RECORD_TYPE = "TrainingComputeTerminalReceipt"
class CheckpointArtifactBinding(_CanonicalRecord): RECORD_TYPE = "CheckpointArtifactBinding"
class GPUProcessObservationBinding(_CanonicalRecord): RECORD_TYPE = "GPUProcessObservationBinding"
class ModelArtifactBinding(_CanonicalRecord): RECORD_TYPE = "ModelArtifactBinding"
class ModelCandidateRevision(_CanonicalRecord): RECORD_TYPE = "ModelCandidateRevision"
class EvaluationReceipt(_CanonicalRecord): RECORD_TYPE = "EvaluationReceipt"
class OwnerModelApprovalDecisionBinding(_CanonicalRecord): RECORD_TYPE = "OwnerModelApprovalDecisionBinding"
class TrainingPreflightReport(_CanonicalRecord): RECORD_TYPE = "TrainingPreflightReport"
class TrainingDispatchAdmissionReport(_CanonicalRecord): RECORD_TYPE = "TrainingDispatchAdmissionReport"


def _binding_pass(value: Mapping[str, Any]) -> bool:
    return value.get("contract_state") == ContractState.BOUND_VERIFIED.value


def evaluate_preflight(intent: Mapping[str, Any], *, evaluated_at: str) -> TrainingPreflightReport:
    parsed = TrainingRunIntent.from_dict(intent).to_dict()
    reasons: set[str] = set()
    engine = parsed["engine_admission_binding"]
    destination = parsed["output_artifact_destination_binding"]
    feasibility = parsed["target_resource_feasibility_binding"]
    contamination = parsed["contamination_proof_binding"]
    rights = parsed["current_use_rights_binding"]
    if not _binding_pass(engine): reasons.add("ENGINE_BINDING_UNRESOLVED")
    elif engine["capability_state"] != "ADMITTED": reasons.add("ENGINE_MODE_NOT_ADMITTED")
    if _binding_pass(engine) and engine["license_state"] != "PASS": reasons.add("LICENSE_NOT_CURRENT_PASS")
    if not _binding_pass(destination): reasons.add("OUTPUT_DESTINATION_UNRESOLVED")
    if not _binding_pass(feasibility): reasons.add("TARGET_FEASIBILITY_UNRESOLVED")
    elif feasibility["admission_state"] != "ADMITTED": reasons.add("TARGET_MODE_FEASIBILITY_NOT_ADMITTED")
    if contamination["decision"] != "PASS": reasons.add("CONTAMINATION_NOT_PROVEN_PASS")
    if not _binding_pass(rights):
        reasons.add("CURRENT_RIGHTS_CONSENT_LICENSE_UNRESOLVED")
    elif any(
        rights[field] != "PASS"
        for field in (
            "consent_state", "training_data_rights_state",
            "reference_audio_rights_state", "output_rights_state", "license_state",
        )
    ):
        reasons.add("CURRENT_RIGHTS_CONSENT_LICENSE_NOT_PASS")
    decision = DecisionState.PASS if not reasons else DecisionState.BLOCKED
    report = add_record_digest({
        "record_type": "TrainingPreflightReport",
        "run_intent_sha256": parsed["intent_sha256"],
        "run_revision_sha256": None,
        "decision": decision.value,
        "reason_codes": sorted(reasons),
        "evaluated_at": _timestamp(evaluated_at, "evaluated_at"),
        "dispatch_started": False,
        "gpu_process_started": False,
        "training_started": False,
    }, "report_sha256")
    return TrainingPreflightReport.from_dict(report)


def evaluate_dispatch_admission(
    intent: Mapping[str, Any],
    revision: Mapping[str, Any],
    *,
    now: str,
) -> TrainingDispatchAdmissionReport:
    parsed_intent = TrainingRunIntent.from_dict(intent).to_dict()
    parsed_revision = TrainingRunRevision.from_dict(revision).to_dict()
    if parsed_revision["run_intent_sha256"] != parsed_intent["intent_sha256"]:
        raise ValueError("run revision is not bound to intent")
    reasons: set[str] = set(evaluate_preflight(parsed_intent, evaluated_at=now).to_dict()["reason_codes"])
    job = parsed_revision["durable_job_binding"]
    reservation = parsed_revision["resource_reservation_binding"]
    authorization = parsed_revision["execution_authorization_binding"]
    if not _binding_pass(job): reasons.add("TRAINING_DURABLE_JOB_UNRESOLVED")
    if not _binding_pass(reservation): reasons.add("EXECUTION_RESERVATION_UNRESOLVED")
    else:
        if reservation["admission_state"] != "ADMITTED": reasons.add("EXECUTION_RESERVATION_NOT_ADMITTED")
        if datetime.fromisoformat(reservation["expires_at"][:-1] + "+00:00") <= datetime.fromisoformat(now[:-1] + "+00:00"):
            reasons.add("EXECUTION_RESERVATION_EXPIRED")
    if not _binding_pass(authorization): reasons.add("OWNER_EXECUTION_GATE_UNRESOLVED")
    else:
        if authorization["scope"] != "START": reasons.add("AUTHORIZATION_SCOPE_MISMATCH")
        if authorization["run_intent_sha256"] != parsed_intent["intent_sha256"]: reasons.add("AUTHORIZATION_INTENT_MISMATCH")
        if authorization["run_revision_sha256"] != parsed_revision["parent_revision_sha256"]: reasons.add("AUTHORIZATION_REVISION_MISMATCH")
        if datetime.fromisoformat(authorization["expires_at"][:-1] + "+00:00") <= datetime.fromisoformat(now[:-1] + "+00:00"):
            reasons.add("AUTHORIZATION_EXPIRED")
    decision = DecisionState.PASS if not reasons else DecisionState.BLOCKED
    report = add_record_digest({
        "record_type": "TrainingDispatchAdmissionReport",
        "run_intent_sha256": parsed_intent["intent_sha256"],
        "run_revision_sha256": parsed_revision["revision_sha256"],
        "decision": decision.value,
        "reason_codes": sorted(reasons),
        "evaluated_at": _timestamp(now, "now"),
        "dispatch_started": False,
        "gpu_process_started": False,
        "training_started": False,
    }, "report_sha256")
    return TrainingDispatchAdmissionReport.from_dict(report)


def evaluate_resume_admission(
    intent: Mapping[str, Any],
    checkpoint_binding: Mapping[str, Any],
    authorization_binding: Mapping[str, Any],
    current_use_rights_binding: Mapping[str, Any],
    *,
    now: str,
) -> TrainingDispatchAdmissionReport:
    parsed_intent = TrainingRunIntent.from_dict(intent).to_dict()
    checkpoint = CheckpointArtifactBinding.from_dict(checkpoint_binding).to_dict()
    authorization = TrainingExecutionAuthorizationBinding.from_dict(authorization_binding).to_dict()
    rights = CurrentUseRightsBinding.from_dict(current_use_rights_binding).to_dict()
    reasons: set[str] = set(evaluate_preflight(parsed_intent, evaluated_at=now).to_dict()["reason_codes"])
    if not _binding_pass(checkpoint):
        reasons.add("CHECKPOINT_CANONICAL_BINDING_UNRESOLVED")
    else:
        expected = {
            "training_input_snapshot_sha256": parsed_intent["training_input_snapshot_sha256"],
            "base_model_sha256": parsed_intent["engine_admission_binding"]["base_model_sha256"],
            "runtime_sha256": parsed_intent["engine_admission_binding"]["runtime_sha256"],
            "code_sha256": parsed_intent["engine_admission_binding"]["code_sha256"],
            "config_sha256": parsed_intent["config_sha256"],
        }
        for field, expected_value in expected.items():
            if checkpoint[field] != expected_value:
                reasons.add(f"CHECKPOINT_{field.upper()}_MISMATCH")
        if checkpoint["resume_decision"] != "ACCEPT":
            reasons.add("CHECKPOINT_RESUME_NOT_ACCEPTED")
    if not _binding_pass(rights):
        reasons.add("RESUME_RIGHTS_CONSENT_LICENSE_UNRESOLVED")
    elif rights["binding_sha256"] != parsed_intent["current_consent_rights_license_sha256"]:
        reasons.add("RESUME_RIGHTS_CONSENT_LICENSE_STALE")
    elif any(
        rights[field] != "PASS"
        for field in (
            "consent_state", "training_data_rights_state",
            "reference_audio_rights_state", "output_rights_state", "license_state",
        )
    ):
        reasons.add("RESUME_RIGHTS_CONSENT_LICENSE_NOT_PASS")
    if not _binding_pass(authorization):
        reasons.add("RESUME_OWNER_GATE_UNRESOLVED")
    else:
        if authorization["scope"] != "RESUME": reasons.add("RESUME_AUTHORIZATION_SCOPE_MISMATCH")
        if authorization["run_intent_sha256"] != parsed_intent["intent_sha256"]: reasons.add("RESUME_AUTHORIZATION_INTENT_MISMATCH")
        if authorization["current_consent_rights_license_sha256"] != rights["binding_sha256"]: reasons.add("RESUME_AUTHORIZATION_RIGHTS_MISMATCH")
        if datetime.fromisoformat(authorization["expires_at"][:-1] + "+00:00") <= datetime.fromisoformat(now[:-1] + "+00:00"):
            reasons.add("RESUME_AUTHORIZATION_EXPIRED")
    decision = DecisionState.PASS if not reasons else DecisionState.BLOCKED
    report = add_record_digest({
        "record_type": "TrainingDispatchAdmissionReport",
        "run_intent_sha256": parsed_intent["intent_sha256"],
        "run_revision_sha256": authorization.get("run_revision_sha256") or parsed_intent["intent_sha256"],
        "decision": decision.value, "reason_codes": sorted(reasons),
        "evaluated_at": _timestamp(now, "now"), "dispatch_started": False,
        "gpu_process_started": False, "training_started": False,
    }, "report_sha256")
    return TrainingDispatchAdmissionReport.from_dict(report)


def training_dispatch_projection(intent: Mapping[str, Any]) -> dict[str, Any]:
    """Return the bounded training-side projection without evaluation item details."""

    parsed = TrainingRunIntent.from_dict(intent).to_dict()
    return {
        "record_type": "TrainingDispatchProjection",
        "run_intent_sha256": parsed["intent_sha256"],
        "training_mode": parsed["training_mode"],
        "training_input_snapshot_ref": parsed["training_input_snapshot_ref"],
        "training_input_snapshot_sha256": parsed["training_input_snapshot_sha256"],
        "evaluation_input_snapshot_ref": parsed["evaluation_input_snapshot_ref"],
        "evaluation_input_snapshot_sha256": parsed["evaluation_input_snapshot_sha256"],
        "contamination_decision": parsed["contamination_proof_binding"]["decision"],
        "contamination_proof_sha256": parsed["contamination_proof_binding"]["proof_sha256"],
        "engine_admission_sha256": parsed["engine_admission_binding"]["binding_sha256"],
        "config_sha256": parsed["config_sha256"],
        "evaluation_item_details_included": False,
        "dispatch_started": False,
        "training_started": False,
    }


_TRANSITIONS: dict[TrainingRunState, set[TrainingRunState]] = {
    TrainingRunState.DRAFT: {TrainingRunState.PREFLIGHT_PENDING, TrainingRunState.CANCELLED_SAFE},
    TrainingRunState.PREFLIGHT_PENDING: {TrainingRunState.BLOCKED, TrainingRunState.READY_FOR_OWNER_HUMAN_GATE, TrainingRunState.UNKNOWN},
    TrainingRunState.BLOCKED: {TrainingRunState.PREFLIGHT_PENDING, TrainingRunState.CANCELLED_SAFE},
    TrainingRunState.READY_FOR_OWNER_HUMAN_GATE: {TrainingRunState.QUEUED, TrainingRunState.BLOCKED, TrainingRunState.CANCELLED_SAFE},
    TrainingRunState.QUEUED: {TrainingRunState.RUNNING, TrainingRunState.STOP_REQUESTED, TrainingRunState.UNKNOWN, TrainingRunState.CANCELLED_SAFE},
    TrainingRunState.RUNNING: {TrainingRunState.CHECKPOINTED, TrainingRunState.PAUSED_SAFE, TrainingRunState.STOP_REQUESTED, TrainingRunState.TRAINING_COMPLETED_ARTIFACT_UNBOUND, TrainingRunState.FAILED_KNOWN, TrainingRunState.UNKNOWN},
    TrainingRunState.CHECKPOINTED: {TrainingRunState.RUNNING, TrainingRunState.PAUSED_SAFE, TrainingRunState.STOP_REQUESTED, TrainingRunState.UNKNOWN},
    TrainingRunState.PAUSED_SAFE: {TrainingRunState.RUNNING, TrainingRunState.STOP_REQUESTED, TrainingRunState.CANCELLED_SAFE, TrainingRunState.UNKNOWN},
    TrainingRunState.STOP_REQUESTED: {TrainingRunState.PAUSED_SAFE, TrainingRunState.CANCELLED_SAFE, TrainingRunState.FAILED_KNOWN, TrainingRunState.UNKNOWN},
    TrainingRunState.TRAINING_COMPLETED_ARTIFACT_UNBOUND: {TrainingRunState.MODEL_CANDIDATE_REGISTERED, TrainingRunState.FAILED_KNOWN, TrainingRunState.UNKNOWN},
    TrainingRunState.MODEL_CANDIDATE_REGISTERED: {TrainingRunState.EVALUATION_PENDING, TrainingRunState.FAILED_KNOWN},
    TrainingRunState.EVALUATION_PENDING: {TrainingRunState.EVALUATED_CANDIDATE, TrainingRunState.FAILED_KNOWN, TrainingRunState.UNKNOWN},
    TrainingRunState.EVALUATED_CANDIDATE: set(),
    TrainingRunState.FAILED_KNOWN: set(),
    TrainingRunState.UNKNOWN: {TrainingRunState.PAUSED_SAFE, TrainingRunState.CHECKPOINTED, TrainingRunState.TRAINING_COMPLETED_ARTIFACT_UNBOUND, TrainingRunState.FAILED_KNOWN},
    TrainingRunState.CANCELLED_SAFE: set(),
}


def validate_state_transition(previous: Mapping[str, Any], current: Mapping[str, Any]) -> None:
    old = TrainingRunRevision.from_dict(previous).to_dict()
    new = TrainingRunRevision.from_dict(current).to_dict()
    if new["revision"] != old["revision"] + 1 or new["parent_revision_sha256"] != old["revision_sha256"]:
        raise ValueError("revision transition is not append-only CAS lineage")
    if new["run_intent_sha256"] != old["run_intent_sha256"]:
        raise ValueError("TrainingRunIntent is immutable across run revisions")
    old_state = TrainingRunState(old["state"])
    new_state = TrainingRunState(new["state"])
    if new_state not in _TRANSITIONS[old_state]:
        raise ValueError(f"invalid training state transition {old_state.value}->{new_state.value}")


def classify_unknown_reconciliation(
    job_binding: Mapping[str, Any],
    process_observation: Mapping[str, Any],
    checkpoint_binding: Mapping[str, Any],
) -> DecisionState:
    job = TrainingDurableJobBinding.from_dict(job_binding).to_dict()
    process = GPUProcessObservationBinding.from_dict(process_observation).to_dict()
    checkpoint = CheckpointArtifactBinding.from_dict(checkpoint_binding).to_dict()
    if not all(_binding_pass(item) for item in (job, process)):
        return DecisionState.UNKNOWN
    if process["observation_state"] == "UNKNOWN":
        return DecisionState.UNKNOWN
    if process["gpu_process_present"] is True:
        return DecisionState.BLOCKED
    if not _binding_pass(checkpoint) or checkpoint["resume_decision"] != "ACCEPT":
        return DecisionState.BLOCKED
    return DecisionState.PASS


def evaluate_candidate_evaluation_admission(candidate: Mapping[str, Any]) -> DecisionState:
    parsed = ModelCandidateRevision.from_dict(candidate).to_dict()
    artifact = parsed["model_artifact_binding"]
    if artifact["contract_state"] != ContractState.BOUND_VERIFIED.value:
        return DecisionState.BLOCKED
    if artifact["load_compatibility_state"] != "PASS":
        return DecisionState.BLOCKED
    if artifact["license_inheritance_state"] != "PASS":
        return DecisionState.BLOCKED
    if parsed["candidate_state"] in {"STALE", "REJECTED"}:
        return DecisionState.BLOCKED
    return DecisionState.PASS


def evaluate_owner_approval_current_use(
    candidate: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    approval: Mapping[str, Any],
    *,
    current_consent_rights_license_sha256: str,
) -> DecisionState:
    parsed_candidate = ModelCandidateRevision.from_dict(candidate).to_dict()
    parsed_evaluation = EvaluationReceipt.from_dict(evaluation).to_dict()
    parsed_approval = OwnerModelApprovalDecisionBinding.from_dict(approval).to_dict()
    current_hash = _sha(current_consent_rights_license_sha256, "current_consent_rights_license_sha256")
    if evaluate_candidate_evaluation_admission(parsed_candidate) is not DecisionState.PASS:
        return DecisionState.BLOCKED
    if parsed_evaluation["overall_decision"] != "PASS":
        return DecisionState.BLOCKED
    artifact_sha = parsed_candidate["model_artifact_binding"]["binding_sha256"]
    if parsed_evaluation["candidate_sha256"] != parsed_candidate["candidate_sha256"] or parsed_evaluation["model_artifact_binding_sha256"] != artifact_sha:
        return DecisionState.BLOCKED
    if parsed_approval["contract_state"] != ContractState.BOUND_VERIFIED.value or parsed_approval["decision"] != "APPROVE":
        return DecisionState.BLOCKED
    if parsed_approval["candidate_sha256"] != parsed_candidate["candidate_sha256"] or parsed_approval["evaluation_receipt_sha256"] != parsed_evaluation["receipt_sha256"] or parsed_approval["model_artifact_binding_sha256"] != artifact_sha:
        return DecisionState.BLOCKED
    if parsed_approval["current_consent_rights_license_sha256"] != current_hash or parsed_candidate["current_consent_rights_license_sha256"] != current_hash or parsed_evaluation["current_consent_rights_license_sha256"] != current_hash:
        return DecisionState.BLOCKED
    return DecisionState.PASS


def public_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    parsed = validate_record(value)
    blocked_fragments = ("selected_items", "logical_uri", "component_checksums")
    private_suffixes = ("_ref", "_sha256")
    def project(item: Any) -> Any:
        if isinstance(item, Mapping):
            result: dict[str, Any] = {}
            for key, nested in item.items():
                if key in blocked_fragments or key.endswith(private_suffixes):
                    continue
                result[key] = project(nested)
            return result
        if isinstance(item, list):
            return [project(nested) for nested in item]
        return item
    result = project(parsed)
    result["projection"] = "PUBLIC_BODY_FREE"
    return result


def assert_no_effect_surface() -> None:
    """Static sentinel used by tests to document the intentionally pure surface."""

    forbidden = {"open", "requests", "subprocess", "socket", "torch", "transformers"}
    if forbidden & set(globals()):
        raise AssertionError("effectful runtime surface detected")
