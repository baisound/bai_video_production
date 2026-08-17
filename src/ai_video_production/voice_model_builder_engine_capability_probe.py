"""Body-free engine capability probe contracts for TASK-046/P-VS-4B R2.

The module validates plans and externally supplied probe facts.  It performs no
download, installation, model load, training step, GPU reservation, or artifact
write.
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


SCHEMA_ID = "bai.task046.voice-model-builder-engine-capability-probe.v1"
MAX_PHASES = 6
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")


class TrainingMode(str, Enum):
    FULL_FINE_TUNE = "FULL_FINE_TUNE"
    PARAMETER_EFFICIENT_FINE_TUNE = "PARAMETER_EFFICIENT_FINE_TUNE"
    ADAPTER_OR_LORA = "ADAPTER_OR_LORA"


class ProbePhase(str, Enum):
    PACKAGE_VERIFY = "PACKAGE_VERIFY"
    MODEL_LOAD = "MODEL_LOAD"
    REPRESENTATIVE_STEP = "REPRESENTATIVE_STEP"
    CHECKPOINT_ROUNDTRIP = "CHECKPOINT_ROUNDTRIP"
    OOM_SAFE_FAILURE_RECOVERY = "OOM_SAFE_FAILURE_RECOVERY"
    THERMAL_DURATION = "THERMAL_DURATION"


class FactState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ProbeState(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED_KNOWN = "FAILED_KNOWN"
    UNKNOWN = "UNKNOWN"


class EvidenceState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


def _expect(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    if "\\" in value or value.startswith("/") or re.match(r"^[A-Za-z]:/", value) or any(part == ".." for part in value.split("/")):
        raise ValueError(f"{name} must be a contained logical identifier")
    return value


def _sha(value: Any, name: str) -> str:
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


def _ordered_phases(value: Any) -> tuple[ProbePhase, ...]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_PHASES or len(value) != len(set(value)):
        raise ValueError("requested_phases must be a unique bounded list")
    phases = tuple(_enum(ProbePhase, item, "requested phase") for item in value)
    canonical = tuple(phase for phase in ProbePhase if phase in phases)
    if phases != canonical:
        raise ValueError("requested_phases must use canonical order")
    return phases


def _validate_plan(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "plan_id", "revision", "parent_plan_sha256", "authority_kind",
        "engine_id", "engine_revision", "package_sha256", "model_id", "model_revision",
        "weight_manifest_sha256", "runtime_sha256", "recipe_revision", "recipe_sha256",
        "training_mode", "probe_profile_revision", "probe_profile_sha256",
        "target_resource_profile_sha256", "requested_phases", "synthetic_input_only",
        "owner_audio_used", "download_started", "install_started", "model_load_started",
        "training_step_started", "created_at", "plan_sha256",
    }
    _expect(value, fields, "EngineCapabilityProbePlan")
    for name in ("plan_id", "engine_id", "engine_revision", "model_id", "model_revision", "recipe_revision", "probe_profile_revision"):
        _id(value[name], name)
    if not isinstance(value["revision"], int) or value["revision"] < 1:
        raise ValueError("revision is invalid")
    parent = value["parent_plan_sha256"]
    if parent is not None:
        _sha(parent, "parent_plan_sha256")
    if (value["revision"] == 1) != (parent is None):
        raise ValueError("plan parent/revision lineage mismatch")
    for name in ("package_sha256", "weight_manifest_sha256", "runtime_sha256", "recipe_sha256", "probe_profile_sha256", "target_resource_profile_sha256"):
        _sha(value[name], name)
    _enum(TrainingMode, value["training_mode"], "training_mode")
    _ordered_phases(value["requested_phases"])
    if value["authority_kind"] != "APPROVED_SYNTHETIC_TEST_AUTHORITY":
        raise ValueError("R2 accepts synthetic test authority only")
    for name, expected in (
        ("synthetic_input_only", True), ("owner_audio_used", False),
        ("download_started", False), ("install_started", False),
        ("model_load_started", False), ("training_step_started", False),
    ):
        if value[name] is not expected:
            raise ValueError(f"{name} must be {expected}")
    _timestamp(value["created_at"], "created_at")
    _verify_digest(value, "plan_sha256")


def _validate_receipt(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "receipt_id", "plan_sha256", "training_mode", "requested_phases",
        "phase_results", "probe_state", "peak_vram_bytes", "peak_ram_bytes",
        "optimizer_state_bytes", "checkpoint_bytes", "free_disk_floor_bytes",
        "duration_milliseconds", "max_temperature_millidegrees_c", "measurement_profile_sha256",
        "process_reconciliation_state", "synthetic_input_only", "owner_audio_used",
        "probe_execution_performed_by_module", "training_run_dispatched",
        "model_candidate_registered", "observed_at", "receipt_sha256",
    }
    _expect(value, fields, "EngineCapabilityProbeReceipt")
    _id(value["receipt_id"], "receipt_id")
    _sha(value["plan_sha256"], "plan_sha256")
    _enum(TrainingMode, value["training_mode"], "training_mode")
    phases = _ordered_phases(value["requested_phases"])
    results = value["phase_results"]
    if not isinstance(results, list) or len(results) != len(phases):
        raise ValueError("phase_results must cover each requested phase exactly once")
    states: list[FactState] = []
    for index, (result, phase) in enumerate(zip(results, phases, strict=True)):
        _expect(result, {"order_index", "phase", "state", "evidence_sha256"}, "phase result")
        if result["order_index"] != index or result["phase"] != phase.value:
            raise ValueError("phase_results order or identity mismatch")
        state = _enum(FactState, result["state"], "phase state")
        states.append(state)
        _sha(result["evidence_sha256"], "evidence_sha256")
    probe_state = _enum(ProbeState, value["probe_state"], "probe_state")
    process_state = _enum(FactState, value["process_reconciliation_state"], "process_reconciliation_state")
    all_states = states + [process_state]
    expected = ProbeState.UNKNOWN if any(state in (FactState.UNKNOWN, FactState.NOT_APPLICABLE) for state in all_states) else (ProbeState.FAILED_KNOWN if any(state in (FactState.FAIL, FactState.NOT_SUPPORTED) for state in all_states) else ProbeState.COMPLETED)
    if probe_state is not expected:
        raise ValueError("probe_state does not match phase facts")
    for name in ("peak_vram_bytes", "peak_ram_bytes", "optimizer_state_bytes", "checkpoint_bytes", "free_disk_floor_bytes", "duration_milliseconds", "max_temperature_millidegrees_c"):
        item = value[name]
        if item is not None and (not isinstance(item, int) or item < 0):
            raise ValueError(f"{name} must be a non-negative integer or null")
    state_by_phase = {phase: state for phase, state in zip(phases, states, strict=True)}
    if state_by_phase.get(ProbePhase.REPRESENTATIVE_STEP) is FactState.PASS:
        required = ("peak_vram_bytes", "peak_ram_bytes", "optimizer_state_bytes", "duration_milliseconds")
        if any(value[name] is None for name in required):
            raise ValueError("representative step PASS requires exact resource measurements")
    if state_by_phase.get(ProbePhase.CHECKPOINT_ROUNDTRIP) is FactState.PASS and value["checkpoint_bytes"] is None:
        raise ValueError("checkpoint PASS requires checkpoint_bytes")
    if state_by_phase.get(ProbePhase.THERMAL_DURATION) is FactState.PASS and (value["free_disk_floor_bytes"] is None or value["max_temperature_millidegrees_c"] is None):
        raise ValueError("thermal duration PASS requires disk and temperature measurements")
    _sha(value["measurement_profile_sha256"], "measurement_profile_sha256")
    for name, expected_bool in (
        ("synthetic_input_only", True), ("owner_audio_used", False),
        ("probe_execution_performed_by_module", False), ("training_run_dispatched", False),
        ("model_candidate_registered", False),
    ):
        if value[name] is not expected_bool:
            raise ValueError(f"{name} must be {expected_bool}")
    _timestamp(value["observed_at"], "observed_at")
    _verify_digest(value, "receipt_sha256")


def _validate_projection(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "projection_id", "probe_receipt_sha256", "training_mode",
        "package_verification_state", "model_load_state", "representative_step_state",
        "target_resource_state", "checkpoint_compatibility_state", "recovery_state", "process_reconciliation_state",
        "thermal_duration_state", "load_only_proves_training", "evidence_state",
        "engine_admission_issued", "training_dispatched", "created_at", "projection_sha256",
    }
    _expect(value, fields, "EngineAdmissionEvidenceProjection")
    _id(value["projection_id"], "projection_id")
    _sha(value["probe_receipt_sha256"], "probe_receipt_sha256")
    _enum(TrainingMode, value["training_mode"], "training_mode")
    facts = tuple(_enum(FactState, value[name], name) for name in (
        "package_verification_state", "model_load_state", "representative_step_state",
        "target_resource_state", "checkpoint_compatibility_state", "recovery_state",
        "thermal_duration_state", "process_reconciliation_state",
    ))
    evidence = _enum(EvidenceState, value["evidence_state"], "evidence_state")
    expected = EvidenceState.UNKNOWN if FactState.UNKNOWN in facts or FactState.NOT_APPLICABLE in facts else (EvidenceState.FAIL if any(fact in (FactState.FAIL, FactState.NOT_SUPPORTED) for fact in facts) else EvidenceState.PASS)
    if evidence is not expected:
        raise ValueError("evidence_state does not match exact phase evidence")
    if value["load_only_proves_training"] is not False:
        raise ValueError("model load alone never proves training feasibility")
    if value["engine_admission_issued"] is not False or value["training_dispatched"] is not False:
        raise ValueError("projection cannot issue admission or dispatch training")
    _timestamp(value["created_at"], "created_at")
    _verify_digest(value, "projection_sha256")


_VALIDATORS = {
    "EngineCapabilityProbePlan": _validate_plan,
    "EngineCapabilityProbeReceipt": _validate_receipt,
    "EngineAdmissionEvidenceProjection": _validate_projection,
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


class EngineCapabilityProbePlan(_Record):
    RECORD_TYPE = "EngineCapabilityProbePlan"


class EngineCapabilityProbeReceipt(_Record):
    RECORD_TYPE = "EngineCapabilityProbeReceipt"


class EngineAdmissionEvidenceProjection(_Record):
    RECORD_TYPE = "EngineAdmissionEvidenceProjection"


def validate_receipt_against_plan(plan: Mapping[str, Any], receipt: Mapping[str, Any]) -> dict[str, Any]:
    planned = validate_record(plan, expected_type="EngineCapabilityProbePlan")
    observed = validate_record(receipt, expected_type="EngineCapabilityProbeReceipt")
    if observed["plan_sha256"] != planned["plan_sha256"]:
        raise ValueError("receipt plan_sha256 does not match exact plan")
    if observed["training_mode"] != planned["training_mode"]:
        raise ValueError("receipt training_mode does not match exact plan")
    if observed["requested_phases"] != planned["requested_phases"]:
        raise ValueError("receipt requested_phases do not match exact plan")
    return observed


def compile_probe_plan(**values: Any) -> EngineCapabilityProbePlan:
    body = {
        "record_type": "EngineCapabilityProbePlan",
        **values,
        "authority_kind": "APPROVED_SYNTHETIC_TEST_AUTHORITY",
        "synthetic_input_only": True,
        "owner_audio_used": False,
        "download_started": False,
        "install_started": False,
        "model_load_started": False,
        "training_step_started": False,
    }
    return EngineCapabilityProbePlan(add_record_digest(body, "plan_sha256"))


def compile_evidence_projection(*, projection_id: str, receipt: Mapping[str, Any], target_resource_state: str, created_at: str) -> EngineAdmissionEvidenceProjection:
    record = validate_record(receipt, expected_type="EngineCapabilityProbeReceipt")
    states = {item["phase"]: item["state"] for item in record["phase_results"]}
    def state(phase: ProbePhase) -> str:
        return states.get(phase.value, "NOT_APPLICABLE")
    facts = [state(ProbePhase.PACKAGE_VERIFY), state(ProbePhase.MODEL_LOAD), state(ProbePhase.REPRESENTATIVE_STEP), target_resource_state, state(ProbePhase.CHECKPOINT_ROUNDTRIP), state(ProbePhase.OOM_SAFE_FAILURE_RECOVERY), state(ProbePhase.THERMAL_DURATION), record["process_reconciliation_state"]]
    evidence = "UNKNOWN" if "UNKNOWN" in facts or "NOT_APPLICABLE" in facts else ("FAIL" if "FAIL" in facts or "NOT_SUPPORTED" in facts else "PASS")
    body = {
        "record_type": "EngineAdmissionEvidenceProjection",
        "projection_id": projection_id,
        "probe_receipt_sha256": record["receipt_sha256"],
        "training_mode": record["training_mode"],
        "package_verification_state": facts[0],
        "model_load_state": facts[1],
        "representative_step_state": facts[2],
        "target_resource_state": facts[3],
        "checkpoint_compatibility_state": facts[4],
        "recovery_state": facts[5],
        "thermal_duration_state": facts[6],
        "process_reconciliation_state": facts[7],
        "load_only_proves_training": False,
        "evidence_state": evidence,
        "engine_admission_issued": False,
        "training_dispatched": False,
        "created_at": created_at,
    }
    return EngineAdmissionEvidenceProjection(add_record_digest(body, "projection_sha256"))


def public_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    record = validate_record(value)
    if record["record_type"] == "EngineCapabilityProbePlan":
        return {"record_type": record["record_type"], "training_mode": record["training_mode"], "requested_phases": list(record["requested_phases"]), "effect_started": False}
    if record["record_type"] == "EngineCapabilityProbeReceipt":
        return {"record_type": record["record_type"], "training_mode": record["training_mode"], "probe_state": record["probe_state"], "phase_states": [item["state"] for item in record["phase_results"]], "owner_audio_used": False}
    return {"record_type": record["record_type"], "training_mode": record["training_mode"], "evidence_state": record["evidence_state"], "engine_admission_issued": False, "training_dispatched": False}


def assert_no_effect_surface() -> None:
    module = inspect.getmodule(assert_no_effect_surface)
    forbidden = {"pathlib", "os", "subprocess", "socket", "requests", "urllib", "torch", "transformers"}
    if module is None or forbidden.intersection(module.__dict__):
        raise AssertionError("effect-capable import detected")
