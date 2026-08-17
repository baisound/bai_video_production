"""Pure Dataset preparation and engine-recipe admission for P-VS-4B R1.

This module compiles body-free metadata only.  It does not read audio, adopt a
Dataset, create a durable Job, acquire/load a model, reserve resources, or
dispatch training.
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


SCHEMA_ID = "bai.task046.voice-model-builder-dataset-engine-admission.v1"
MAX_ITEMS = 4096
MAX_SELECTED_FRAMES = 48_000 * 60 * 120
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_REASON_RE = re.compile(r"[A-Z][A-Z0-9_]{1,95}")


class ContractState(str, Enum):
    CANONICAL_REF_NOT_PROVIDED = "CANONICAL_REF_NOT_PROVIDED"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class FactState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class TrainingMode(str, Enum):
    FULL_FINE_TUNE = "FULL_FINE_TUNE"
    PARAMETER_EFFICIENT_FINE_TUNE = "PARAMETER_EFFICIENT_FINE_TUNE"
    ADAPTER_OR_LORA = "ADAPTER_OR_LORA"


class LicenseState(str, Enum):
    APPROVED_FOR_SYNTHETIC_TECHNICAL_TEST = "APPROVED_FOR_SYNTHETIC_TECHNICAL_TEST"
    LEGAL_REVIEW_REQUIRED = "LEGAL_REVIEW_REQUIRED"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"


class ProposalState(str, Enum):
    BLOCKED = "BLOCKED"
    READY_FOR_OWNER_HUMAN_GATE = "READY_FOR_OWNER_HUMAN_GATE"


def _expect(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    if "\\" in value or value.startswith("/") or re.match(r"^[A-Za-z]:/", value) or any(part == ".." for part in value.split("/")):
        raise ValueError(f"{name} must be a contained logical identifier")
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


def _reasons(value: Any) -> None:
    if not isinstance(value, list) or len(value) > 32 or len(value) != len(set(value)):
        raise ValueError("reason_codes must be a unique bounded list")
    if any(not isinstance(item, str) or not _REASON_RE.fullmatch(item) for item in value):
        raise ValueError("reason_codes contain an invalid value")


def _digest_body(value: Mapping[str, Any], field: str) -> str:
    return sha256_bytes(canonical_json_bytes({key: item for key, item in value.items() if key != field}))


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


def _validate_manifest(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "manifest_id", "revision", "parent_manifest_sha256", "workflow_sha256",
        "authority_kind", "ordered_items", "selected_unique_frames", "sample_rate_hz",
        "synthetic_input_only", "owner_audio_used", "dataset_adoption_started",
        "training_input_snapshot_issued", "created_at", "manifest_sha256",
    }
    _expect(value, fields, "SyntheticDatasetPreparationManifest")
    _id(value["manifest_id"], "manifest_id")
    if not isinstance(value["revision"], int) or value["revision"] < 1:
        raise ValueError("revision is invalid")
    _sha(value["parent_manifest_sha256"], "parent_manifest_sha256", nullable=True)
    if (value["revision"] == 1) != (value["parent_manifest_sha256"] is None):
        raise ValueError("manifest parent/revision lineage mismatch")
    _sha(value["workflow_sha256"], "workflow_sha256")
    if value["authority_kind"] != "APPROVED_SYNTHETIC_TEST_AUTHORITY":
        raise ValueError("R1 accepts synthetic test authority only")
    items = value["ordered_items"]
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_ITEMS:
        raise ValueError("ordered_items are invalid")
    seen_ids: set[str] = set()
    intervals: dict[str, list[tuple[int, int]]] = {}
    total = 0
    for index, item in enumerate(items):
        _expect(item, {"order_index", "item_id", "wav_inspection_receipt_sha256", "source_sha256", "start_frame", "end_frame", "approved_label_sha256"}, "selection item")
        if item["order_index"] != index:
            raise ValueError("item order must be contiguous")
        _id(item["item_id"], "item_id")
        if item["item_id"] in seen_ids:
            raise ValueError("item_id must be unique")
        seen_ids.add(item["item_id"])
        for name in ("wav_inspection_receipt_sha256", "source_sha256", "approved_label_sha256"):
            _sha(item[name], name)
        start, end = item["start_frame"], item["end_frame"]
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
            raise ValueError("sample range must be non-empty half-open frames")
        prior = intervals.setdefault(item["source_sha256"], [])
        if any(start < old_end and old_start < end for old_start, old_end in prior):
            raise ValueError("overlapping ranges from one source are forbidden")
        prior.append((start, end))
        total += end - start
    if not isinstance(value["selected_unique_frames"], int) or value["selected_unique_frames"] != total or total > MAX_SELECTED_FRAMES:
        raise ValueError("selected_unique_frames mismatch or cap exceeded")
    if value["sample_rate_hz"] != 48_000:
        raise ValueError("Dataset preparation requires canonical 48 kHz frames")
    for name, expected in (
        ("synthetic_input_only", True), ("owner_audio_used", False),
        ("dataset_adoption_started", False), ("training_input_snapshot_issued", False),
    ):
        if value[name] is not expected:
            raise ValueError(f"{name} must be {expected}")
    _timestamp(value["created_at"], "created_at")
    _verify_digest(value, "manifest_sha256")


def _validate_engine(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "binding_id", "contract_state", "engine_id", "engine_revision",
        "package_sha256", "model_id", "model_revision", "weight_sha256", "runtime_sha256",
        "recipe_revision", "recipe_sha256", "training_mode", "official_recipe_state",
        "representative_step_state", "target_resource_state", "checkpoint_compatibility_state",
        "license_state", "license_evidence_sha256", "admission_state", "evaluated_at", "binding_sha256",
    }
    _expect(value, fields, "EngineRecipeAdmissionBinding")
    _id(value["binding_id"], "binding_id")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    _enum(TrainingMode, value["training_mode"], "training_mode")
    facts = tuple(_enum(FactState, value[name], name) for name in (
        "official_recipe_state", "representative_step_state", "target_resource_state",
        "checkpoint_compatibility_state",
    ))
    license_state = _enum(LicenseState, value["license_state"], "license_state")
    admission = _enum(FactState, value["admission_state"], "admission_state")
    bound_fields = (
        "engine_id", "engine_revision", "package_sha256", "model_id", "model_revision",
        "weight_sha256", "runtime_sha256", "recipe_revision", "recipe_sha256",
        "license_evidence_sha256", "evaluated_at",
    )
    if state is ContractState.BOUND_VERIFIED:
        for name in ("engine_id", "engine_revision", "model_id", "model_revision", "recipe_revision"):
            _id(value[name], name)
        for name in ("package_sha256", "weight_sha256", "runtime_sha256", "recipe_sha256", "license_evidence_sha256"):
            _sha(value[name], name)
        _timestamp(value["evaluated_at"], "evaluated_at")
    elif any(value[name] is not None for name in bound_fields):
        raise ValueError("unresolved engine admission must not invent canonical fields")
    eligible = state is ContractState.BOUND_VERIFIED and all(fact is FactState.PASS for fact in facts) and license_state is LicenseState.APPROVED_FOR_SYNTHETIC_TECHNICAL_TEST
    if (admission is FactState.PASS) != eligible:
        raise ValueError("admission_state PASS requires bound exact recipe/resource/checkpoint and approved license")
    _verify_digest(value, "binding_sha256")


def _validate_proposal(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "proposal_id", "dataset_manifest_sha256", "engine_admission_sha256",
        "output_destination_binding_sha256", "engine_binding_state", "engine_admission_state", "durable_job_binding_state", "rights_consent_state",
        "proposal_state", "reason_codes", "owner_human_gate_required", "dispatch_started",
        "gpu_reserved", "training_started", "artifact_written", "created_at", "proposal_sha256",
    }
    _expect(value, fields, "TrainingExecutionProposal")
    _id(value["proposal_id"], "proposal_id")
    for name in ("dataset_manifest_sha256", "engine_admission_sha256", "output_destination_binding_sha256"):
        _sha(value[name], name)
    engine_binding = _enum(ContractState, value["engine_binding_state"], "engine_binding_state")
    engine_admission = _enum(FactState, value["engine_admission_state"], "engine_admission_state")
    job = _enum(ContractState, value["durable_job_binding_state"], "durable_job_binding_state")
    rights = _enum(FactState, value["rights_consent_state"], "rights_consent_state")
    state = _enum(ProposalState, value["proposal_state"], "proposal_state")
    _reasons(value["reason_codes"])
    ready = engine_binding is ContractState.BOUND_VERIFIED and engine_admission is FactState.PASS and job is ContractState.BOUND_VERIFIED and rights is FactState.PASS
    if (state is ProposalState.READY_FOR_OWNER_HUMAN_GATE) != ready:
        raise ValueError("proposal_state does not match current prerequisites")
    if ready and value["reason_codes"]:
        raise ValueError("ready proposal cannot retain blockers")
    if not ready and not value["reason_codes"]:
        raise ValueError("blocked proposal requires reason codes")
    if value["owner_human_gate_required"] is not True:
        raise ValueError("Owner Human Gate is always required")
    for name in ("dispatch_started", "gpu_reserved", "training_started", "artifact_written"):
        if value[name] is not False:
            raise ValueError(f"{name} must remain false")
    _timestamp(value["created_at"], "created_at")
    _verify_digest(value, "proposal_sha256")


_VALIDATORS = {
    "SyntheticDatasetPreparationManifest": _validate_manifest,
    "EngineRecipeAdmissionBinding": _validate_engine,
    "TrainingExecutionProposal": _validate_proposal,
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


class SyntheticDatasetPreparationManifest(_Record):
    RECORD_TYPE = "SyntheticDatasetPreparationManifest"


class EngineRecipeAdmissionBinding(_Record):
    RECORD_TYPE = "EngineRecipeAdmissionBinding"


class TrainingExecutionProposal(_Record):
    RECORD_TYPE = "TrainingExecutionProposal"


def compile_dataset_manifest(
    *, manifest_id: str, revision: int, parent_manifest_sha256: str | None,
    workflow_sha256: str, ordered_items: list[Mapping[str, Any]], created_at: str,
) -> SyntheticDatasetPreparationManifest:
    selected = sum(item["end_frame"] - item["start_frame"] for item in ordered_items)
    body = {
        "record_type": "SyntheticDatasetPreparationManifest",
        "manifest_id": manifest_id,
        "revision": revision,
        "parent_manifest_sha256": parent_manifest_sha256,
        "workflow_sha256": workflow_sha256,
        "authority_kind": "APPROVED_SYNTHETIC_TEST_AUTHORITY",
        "ordered_items": [dict(item) for item in ordered_items],
        "selected_unique_frames": selected,
        "sample_rate_hz": 48_000,
        "synthetic_input_only": True,
        "owner_audio_used": False,
        "dataset_adoption_started": False,
        "training_input_snapshot_issued": False,
        "created_at": created_at,
    }
    return SyntheticDatasetPreparationManifest(add_record_digest(body, "manifest_sha256"))


def compile_training_proposal(
    *, proposal_id: str, dataset_manifest: Mapping[str, Any], engine_admission: Mapping[str, Any],
    output_destination_binding_sha256: str, durable_job_binding_state: str,
    rights_consent_state: str, created_at: str,
) -> TrainingExecutionProposal:
    manifest = validate_record(dataset_manifest, expected_type="SyntheticDatasetPreparationManifest")
    engine = validate_record(engine_admission, expected_type="EngineRecipeAdmissionBinding")
    job = _enum(ContractState, durable_job_binding_state, "durable_job_binding_state")
    rights = _enum(FactState, rights_consent_state, "rights_consent_state")
    reasons: list[str] = []
    if engine["contract_state"] != "BOUND_VERIFIED":
        reasons.append("ENGINE_RECIPE_NOT_BOUND")
    if engine["admission_state"] != "PASS":
        reasons.append("ENGINE_RECIPE_NOT_ADMITTED")
    if job is not ContractState.BOUND_VERIFIED:
        reasons.append("DURABLE_JOB_NOT_BOUND")
    if rights is not FactState.PASS:
        reasons.append("RIGHTS_CONSENT_NOT_PASS")
    ready = not reasons
    body = {
        "record_type": "TrainingExecutionProposal",
        "proposal_id": proposal_id,
        "dataset_manifest_sha256": manifest["manifest_sha256"],
        "engine_admission_sha256": engine["binding_sha256"],
        "output_destination_binding_sha256": output_destination_binding_sha256,
        "engine_binding_state": engine["contract_state"],
        "engine_admission_state": engine["admission_state"],
        "durable_job_binding_state": durable_job_binding_state,
        "rights_consent_state": rights_consent_state,
        "proposal_state": "READY_FOR_OWNER_HUMAN_GATE" if ready else "BLOCKED",
        "reason_codes": reasons,
        "owner_human_gate_required": True,
        "dispatch_started": False,
        "gpu_reserved": False,
        "training_started": False,
        "artifact_written": False,
        "created_at": created_at,
    }
    return TrainingExecutionProposal(add_record_digest(body, "proposal_sha256"))


def public_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    record = validate_record(value)
    if record["record_type"] == "SyntheticDatasetPreparationManifest":
        return {
            "record_type": record["record_type"],
            "item_count": len(record["ordered_items"]),
            "synthetic_input_only": True,
            "dataset_adoption_started": False,
        }
    if record["record_type"] == "EngineRecipeAdmissionBinding":
        return {
            "record_type": record["record_type"],
            "contract_state": record["contract_state"],
            "admission_state": record["admission_state"],
            "training_mode": record["training_mode"],
            "license_state": record["license_state"],
            "effect_authorized": False,
        }
    return {
        "record_type": record["record_type"],
        "proposal_state": record["proposal_state"],
        "reason_codes": list(record["reason_codes"]),
        "owner_human_gate_required": True,
        "dispatch_started": False,
    }


def assert_no_effect_surface() -> None:
    module = inspect.getmodule(assert_no_effect_surface)
    forbidden_imports = {"pathlib", "os", "subprocess", "socket", "requests", "urllib", "torch"}
    if module is None or forbidden_imports.intersection(module.__dict__):
        raise AssertionError("effect-capable import detected")
