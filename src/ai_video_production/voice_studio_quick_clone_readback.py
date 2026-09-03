"""Body-free Quick Clone read-back composition for TASK-046.

The adapter composes existing canonical metadata only.  It can bind a
TASK-003-Asset Quick Clone flow to an exact TASK-014 zero-shot preflight and an
optional paired TASK-046 synthetic WAV fixture request/receipt.  TASK-046
private references and TASK-048 quality evidence remain explicitly unbound
until their canonical bridges exist.  The adapter never reads audio or text,
resolves a host path, loads a model, dispatches execution, plays media, adopts
a profile/Asset, or connects the unified desktop shell.

Synthetic WAV evidence is development-fixture evidence only.  It is never a
TASK-014 narration result, does not bind its Gate 3 workflow/ModelCandidate
coordinates to a Quick Clone flow, and cannot make the product flow ready.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from typing import Any, Mapping, Sequence

from .owner_narration_local_primary import (
    LocalNarrationRouteMode,
    LocalPrimaryNarrationPreflight,
    NarrationIntendedUsage,
    PreflightDecision,
    parse_local_primary_preflight,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .voice_model_builder_runtime import validate_record as validate_runtime_record
from .voice_studio_quick_clone import (
    ComputePreference,
    ComputeResolutionState,
    ExecutionState,
    MODEL_CONFIGURATION_ACCESS,
    MODEL_CONFIGURATION_SOURCE,
    OwnerListeningState,
    PreviewAssetAdoptionState,
    ProfileAdoptionState,
    QualityState,
    QuickCloneFlowRevision,
    ReferenceRetentionState,
    ResultAdmissionState,
    RuntimeAggregateState,
    SetupState,
    SourceKind,
)


SCHEMA_ID = "bai.task046.voice-studio-quick-clone-readback.v1"
CONTRACT_VERSION = "1.0.0"
UNIFIED_DESKTOP_BINDING_STATE = "NOT_BOUND"
TRUSTED_TIME_BINDING_STATE = "NOT_BOUND"
SYNTHETIC_FIXTURE_FLOW_BINDING_STATE = "NOT_BOUND"
MAX_SYNTHETIC_PREVIEW_FRAMES = 48_000 * 60

_FLOW_ID_RE = re.compile(r"quick-clone:[A-Za-z0-9][A-Za-z0-9._-]{0,243}")
_REASON_RE = re.compile(r"[A-Z][A-Z0-9_]{1,95}")
_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
_DRIVE_RE = re.compile(r"^[A-Za-z]:")

_LICENSE_STATES = {
    "COMMERCIAL_ALLOWED",
    "NONCOMMERCIAL_ONLY",
    "RESTRICTED",
    "LEGAL_REVIEW_REQUIRED",
    "REVOKED",
    "UNKNOWN",
}
_CAPABILITY_STATES = {"VERIFIED", "FAILED", "UNKNOWN"}


class ModelBindingState(str, Enum):
    NOT_BOUND = "NOT_BOUND"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class CalibrationBindingState(str, Enum):
    CANONICAL_REF_NOT_PROVIDED = "CANONICAL_REF_NOT_PROVIDED"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class SyntheticFixtureState(str, Enum):
    NOT_PROVIDED = "NOT_PROVIDED"
    DEVELOPMENT_FIXTURE_ONLY = "DEVELOPMENT_FIXTURE_ONLY"


def _logical_id(value: Any, name: str) -> str:
    if name != "flow_id":
        raise AssertionError(f"no closed logical namespace is defined for {name}")
    if (
        not isinstance(value, str)
        or len(value) > 256
        or not _FLOW_ID_RE.fullmatch(value)
    ):
        raise ValueError(f"{name} is invalid")
    return value


def _sha(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be SHA-256")
    return validate_sha256(value, field_name=name)


def _timestamp_value(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{name} must be RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be RFC3339 UTC") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{name} must be UTC")
    return parsed


def _timestamp(value: Any, name: str) -> str:
    _timestamp_value(value, name)
    return value


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(dict(value)))


def _reject_host_paths(value: Any, name: str) -> None:
    """Reject path/URI-shaped values even when an upstream logical-id is loose."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            _reject_host_paths(item, f"{name}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            _reject_host_paths(item, f"{name}[{index}]")
        return
    if not isinstance(value, str):
        return
    if (
        "\\" in value
        or value.startswith("/")
        or _DRIVE_RE.match(value)
        or _URI_RE.match(value)
        or value.lower().startswith("file:")
        or any(part == ".." for part in value.split("/"))
    ):
        raise ValueError(f"{name} contains a host/private path or URI")


def _reason_codes(value: tuple[str, ...]) -> tuple[str, ...]:
    if (
        not isinstance(value, tuple)
        or len(value) > 96
        or len(value) != len(set(value))
        or value != tuple(sorted(value))
    ):
        raise ValueError("reason_codes must be a sorted unique bounded tuple")
    if any(not isinstance(item, str) or not _REASON_RE.fullmatch(item) for item in value):
        raise ValueError("reason_codes contain an invalid value")
    return value


def _wire_reason_codes(value: Any, name: str) -> tuple[str, ...]:
    """Admit only the JSON-array representation used by the wire schema."""
    if type(value) is not list or any(type(item) is not str for item in value):
        raise ValueError(f"{name} must be a JSON array of strings")
    return tuple(value)


def _strict_json_integer(value: Any, name: str) -> int:
    """Reject bool and coercible values at imported JSON integer boundaries."""
    if type(value) is not int:
        raise ValueError(f"{name} must be a JSON integer")
    return value


def _unbound_calibration_projection() -> dict[str, Any]:
    return {
        "contract_state": "CANONICAL_REF_NOT_PROVIDED",
        "analyzer_profile_ref": None,
        "analyzer_profile_sha256": None,
        "calibration_receipt_ref": None,
        "calibration_receipt_sha256": None,
        "result": None,
        "threshold_profile_revision": None,
        "capture_chain_sha256": None,
        "measured_at": None,
    }


def _model_binding_state(contract_state: str) -> ModelBindingState:
    if contract_state == "CANONICAL_REF_NOT_PROVIDED":
        return ModelBindingState.NOT_BOUND
    try:
        return ModelBindingState(contract_state)
    except ValueError as exc:
        raise ValueError("TASK-014 engine contract_state is invalid") from exc


def _duration_us(sample_count: int) -> int:
    return (sample_count * 1_000_000 + 24_000) // 48_000


def _derive_reason_codes(
    *,
    source_kind: SourceKind,
    flow_reason_codes: tuple[str, ...],
    preflight_decision: PreflightDecision | None,
    model_binding_state: ModelBindingState,
    model_license_state: str | None,
    model_capability_probe_state: str | None,
    compute_resolution_state: ComputeResolutionState,
    runtime_aggregate_state: RuntimeAggregateState,
    calibration_contract_state: CalibrationBindingState,
    calibration_result: str | None,
    synthetic_fixture_state: SyntheticFixtureState,
) -> tuple[str, ...]:
    reasons = set(flow_reason_codes)
    reasons.update(
        {
            "TASK014_RESULT_PRODUCER_NOT_BOUND",
            "TRUSTED_TIME_NOT_BOUND",
            "UNIFIED_DESKTOP_READBACK_NOT_CONNECTED",
        }
    )
    if source_kind is SourceKind.TASK046_PRIVATE_REFERENCE:
        reasons.add("TASK014_PRIVATE_REFERENCE_BINDING_NOT_AVAILABLE")
    if preflight_decision is None:
        reasons.add("TASK014_PREFLIGHT_NOT_BOUND")
    elif preflight_decision is PreflightDecision.BLOCKED:
        reasons.add("TASK014_PREFLIGHT_BLOCKED")
    elif preflight_decision is PreflightDecision.UNKNOWN:
        reasons.add("TASK014_PREFLIGHT_UNKNOWN")

    if model_binding_state is not ModelBindingState.BOUND_VERIFIED:
        reasons.add(f"MODEL_SELECTION_{model_binding_state.value}")
    if model_license_state is not None and model_license_state != "COMMERCIAL_ALLOWED":
        reasons.add("MODEL_LICENSE_NOT_COMMERCIAL_ALLOWED")
    if (
        model_capability_probe_state is not None
        and model_capability_probe_state != "VERIFIED"
    ):
        reasons.add("MODEL_CAPABILITY_NOT_VERIFIED")
    if compute_resolution_state not in {
        ComputeResolutionState.GPU_READY,
        ComputeResolutionState.CPU_READY,
    }:
        reasons.add(f"COMPUTE_ROUTE_{compute_resolution_state.value}")
    if runtime_aggregate_state is not RuntimeAggregateState.BOUND_VERIFIED:
        reasons.add(f"RUNTIME_AGGREGATE_{runtime_aggregate_state.value}")

    if calibration_contract_state is CalibrationBindingState.CANONICAL_REF_NOT_PROVIDED:
        reasons.add("REFERENCE_CALIBRATION_NOT_BOUND")
    elif calibration_contract_state is not CalibrationBindingState.BOUND_VERIFIED:
        reasons.add(f"REFERENCE_CALIBRATION_{calibration_contract_state.value}")
    elif calibration_result != "PASS":
        reasons.add(f"REFERENCE_CALIBRATION_{calibration_result}")

    if synthetic_fixture_state is SyntheticFixtureState.DEVELOPMENT_FIXTURE_ONLY:
        reasons.add("SYNTHETIC_FIXTURE_DEVELOPMENT_ONLY")
        reasons.add("SYNTHETIC_FIXTURE_FLOW_NOT_BOUND")
    return tuple(sorted(reasons))


@dataclass(frozen=True, slots=True)
class QuickCloneReadbackReceipt:
    flow_id: str
    flow_revision: int
    flow_revision_sha256: str
    generated_at: str
    source_kind: SourceKind
    setup_state: SetupState
    execution_state: ExecutionState
    compute_preference: ComputePreference
    compute_resolution_state: ComputeResolutionState
    runtime_aggregate_state: RuntimeAggregateState
    result_admission_state: ResultAdmissionState
    output_quality_state: QualityState
    owner_listening_state: OwnerListeningState
    profile_adoption_state: ProfileAdoptionState
    preview_asset_adoption_state: PreviewAssetAdoptionState
    reference_retention_state: ReferenceRetentionState
    flow_reason_codes: tuple[str, ...]
    task014_preflight_sha256: str | None
    task014_preflight_decision: PreflightDecision | None
    model_selection_binding_sha256: str
    model_binding_state: ModelBindingState
    model_route_mode: LocalNarrationRouteMode | None
    model_license_state: str | None
    model_capability_probe_state: str | None
    calibration_binding_sha256: str
    calibration_contract_state: CalibrationBindingState
    calibration_result: str | None
    calibration_receipt_sha256: str | None
    synthetic_fixture_state: SyntheticFixtureState
    synthetic_fixture_request_sha256: str | None
    synthetic_fixture_receipt_sha256: str | None
    synthetic_fixture_output_sha256: str | None
    synthetic_fixture_format_state: str | None
    synthetic_fixture_sample_count: int | None
    synthetic_fixture_duration_us: int | None
    synthetic_boundary_analysis_state: str | None
    synthetic_loudness_analysis_state: str | None
    synthetic_style_analysis_state: str | None
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        _logical_id(self.flow_id, "flow_id")
        if (
            not isinstance(self.flow_revision, int)
            or isinstance(self.flow_revision, bool)
            or self.flow_revision < 1
        ):
            raise ValueError("flow_revision must be an integer >= 1")
        _sha(self.flow_revision_sha256, "flow_revision_sha256")
        _timestamp(self.generated_at, "generated_at")
        enum_fields = (
            (SetupState, self.setup_state, "setup_state"),
            (SourceKind, self.source_kind, "source_kind"),
            (ExecutionState, self.execution_state, "execution_state"),
            (ComputePreference, self.compute_preference, "compute_preference"),
            (
                ComputeResolutionState,
                self.compute_resolution_state,
                "compute_resolution_state",
            ),
            (
                RuntimeAggregateState,
                self.runtime_aggregate_state,
                "runtime_aggregate_state",
            ),
            (ResultAdmissionState, self.result_admission_state, "result_admission_state"),
            (QualityState, self.output_quality_state, "output_quality_state"),
            (OwnerListeningState, self.owner_listening_state, "owner_listening_state"),
            (ProfileAdoptionState, self.profile_adoption_state, "profile_adoption_state"),
            (
                PreviewAssetAdoptionState,
                self.preview_asset_adoption_state,
                "preview_asset_adoption_state",
            ),
            (
                ReferenceRetentionState,
                self.reference_retention_state,
                "reference_retention_state",
            ),
            (ModelBindingState, self.model_binding_state, "model_binding_state"),
            (
                CalibrationBindingState,
                self.calibration_contract_state,
                "calibration_contract_state",
            ),
            (SyntheticFixtureState, self.synthetic_fixture_state, "synthetic_fixture_state"),
        )
        for enum_type, value, name in enum_fields:
            if not isinstance(value, enum_type):
                raise ValueError(f"{name} is invalid")
        _reason_codes(self.flow_reason_codes)
        _reason_codes(self.reason_codes)
        if self.setup_state is SetupState.FAILED and not self.flow_reason_codes:
            raise ValueError("FAILED setup requires flow_reason_codes")
        _sha(self.model_selection_binding_sha256, "model_selection_binding_sha256")
        _sha(self.calibration_binding_sha256, "calibration_binding_sha256")

        has_preflight = self.task014_preflight_sha256 is not None
        if has_preflight:
            if self.source_kind is not SourceKind.TASK003_ASSET:
                raise ValueError(
                    "TASK-014 V1 cannot bind a TASK-046 private reference"
                )
            _sha(self.task014_preflight_sha256, "task014_preflight_sha256")
            if not isinstance(self.task014_preflight_decision, PreflightDecision):
                raise ValueError("bound preflight requires an exact decision")
            if self.model_route_mode is not LocalNarrationRouteMode.ZERO_SHOT_LOCAL:
                raise ValueError("read-back accepts zero-shot local preflight only")
            if (
                self.model_license_state is not None
                and self.model_license_state not in _LICENSE_STATES
            ):
                raise ValueError("model_license_state is invalid")
            if (
                self.model_capability_probe_state is not None
                and self.model_capability_probe_state not in _CAPABILITY_STATES
            ):
                raise ValueError("model_capability_probe_state is invalid")
            if self.model_binding_state is ModelBindingState.BOUND_VERIFIED and (
                self.model_license_state is None
                or self.model_capability_probe_state is None
            ):
                raise ValueError("verified model binding requires license and capability facts")
        elif any(
            value is not None
            for value in (
                self.task014_preflight_decision,
                self.model_route_mode,
                self.model_license_state,
                self.model_capability_probe_state,
            )
        ) or self.model_binding_state is not ModelBindingState.NOT_BOUND:
            raise ValueError("unbound preflight must not invent model facts")

        if (
            self.calibration_contract_state
            is not CalibrationBindingState.CANONICAL_REF_NOT_PROVIDED
            or self.calibration_result is not None
            or self.calibration_receipt_sha256 is not None
        ):
            raise ValueError(
                "TASK-048 source bridge is not bound; calibration must remain unbound"
            )

        fixture_values = (
            self.synthetic_fixture_request_sha256,
            self.synthetic_fixture_receipt_sha256,
            self.synthetic_fixture_output_sha256,
            self.synthetic_fixture_format_state,
            self.synthetic_fixture_sample_count,
            self.synthetic_fixture_duration_us,
            self.synthetic_boundary_analysis_state,
            self.synthetic_loudness_analysis_state,
            self.synthetic_style_analysis_state,
        )
        if self.synthetic_fixture_state is SyntheticFixtureState.NOT_PROVIDED:
            if any(value is not None for value in fixture_values):
                raise ValueError("missing synthetic fixture must not invent facts")
        else:
            _sha(self.synthetic_fixture_request_sha256, "synthetic_fixture_request_sha256")
            _sha(self.synthetic_fixture_receipt_sha256, "synthetic_fixture_receipt_sha256")
            _sha(self.synthetic_fixture_output_sha256, "synthetic_fixture_output_sha256")
            if self.synthetic_fixture_format_state != "PASS":
                raise ValueError("synthetic fixture format must PASS")
            if (
                not isinstance(self.synthetic_fixture_sample_count, int)
                or isinstance(self.synthetic_fixture_sample_count, bool)
                or not 1 <= self.synthetic_fixture_sample_count <= MAX_SYNTHETIC_PREVIEW_FRAMES
            ):
                raise ValueError("synthetic fixture sample count is outside the preview cap")
            if self.synthetic_fixture_duration_us != _duration_us(
                self.synthetic_fixture_sample_count
            ):
                raise ValueError("synthetic fixture duration does not match sample count")
            if {
                self.synthetic_boundary_analysis_state,
                self.synthetic_loudness_analysis_state,
                self.synthetic_style_analysis_state,
            } != {"UNKNOWN"}:
                raise ValueError("synthetic fixture cannot invent analyzer PASS")

        expected_reasons = _derive_reason_codes(
            source_kind=self.source_kind,
            flow_reason_codes=self.flow_reason_codes,
            preflight_decision=self.task014_preflight_decision,
            model_binding_state=self.model_binding_state,
            model_license_state=self.model_license_state,
            model_capability_probe_state=self.model_capability_probe_state,
            compute_resolution_state=self.compute_resolution_state,
            runtime_aggregate_state=self.runtime_aggregate_state,
            calibration_contract_state=self.calibration_contract_state,
            calibration_result=self.calibration_result,
            synthetic_fixture_state=self.synthetic_fixture_state,
        )
        if self.reason_codes != expected_reasons:
            raise ValueError("reason_codes do not match exact read-back facts")
        if (
            self.result_admission_state is not ResultAdmissionState.NOT_BOUND
            or self.execution_state
            not in {ExecutionState.DRAFT, ExecutionState.PREFLIGHT_BLOCKED}
            or self.output_quality_state is not QualityState.NOT_AVAILABLE
            or self.owner_listening_state is not OwnerListeningState.NOT_AVAILABLE
            or self.profile_adoption_state is not ProfileAdoptionState.NOT_AVAILABLE
            or self.preview_asset_adoption_state
            is not PreviewAssetAdoptionState.NOT_AVAILABLE
        ):
            raise ValueError("read-back cannot claim a product result or adoption state")

    def _body(self) -> dict[str, Any]:
        return {
            "schema_id": SCHEMA_ID,
            "contract_version": CONTRACT_VERSION,
            "record_type": "QuickCloneReadbackReceipt",
            "task_owner": "TASK-046",
            "model_configuration_source": MODEL_CONFIGURATION_SOURCE,
            "model_configuration_access": MODEL_CONFIGURATION_ACCESS,
            "voice_model_selector_present": False,
            "task014_result_admission_producer_state": "NOT_BOUND",
            "unified_desktop_binding_state": UNIFIED_DESKTOP_BINDING_STATE,
            "trusted_time_binding_state": TRUSTED_TIME_BINDING_STATE,
            "synthetic_fixture_flow_binding_state": (
                SYNTHETIC_FIXTURE_FLOW_BINDING_STATE
            ),
            "flow_id": self.flow_id,
            "flow_revision": self.flow_revision,
            "flow_revision_sha256": self.flow_revision_sha256,
            "generated_at": self.generated_at,
            "route": "ZERO_SHOT",
            "mode": "PREVIEW",
            "source_kind": self.source_kind.value,
            "setup_state": self.setup_state.value,
            "execution_state": self.execution_state.value,
            "compute_preference": self.compute_preference.value,
            "compute_resolution_state": self.compute_resolution_state.value,
            "runtime_aggregate_state": self.runtime_aggregate_state.value,
            "result_admission_state": self.result_admission_state.value,
            "output_quality_state": self.output_quality_state.value,
            "owner_listening_state": self.owner_listening_state.value,
            "profile_adoption_state": self.profile_adoption_state.value,
            "preview_asset_adoption_state": self.preview_asset_adoption_state.value,
            "reference_retention_state": self.reference_retention_state.value,
            "flow_reason_codes": list(self.flow_reason_codes),
            "task014_preflight_sha256": self.task014_preflight_sha256,
            "task014_preflight_decision": (
                self.task014_preflight_decision.value
                if self.task014_preflight_decision is not None
                else None
            ),
            "model_selection_binding_sha256": self.model_selection_binding_sha256,
            "model_binding_state": self.model_binding_state.value,
            "model_route_mode": (
                self.model_route_mode.value if self.model_route_mode is not None else None
            ),
            "model_license_state": self.model_license_state,
            "model_capability_probe_state": self.model_capability_probe_state,
            "calibration_binding_sha256": self.calibration_binding_sha256,
            "calibration_contract_state": self.calibration_contract_state.value,
            "calibration_result": self.calibration_result,
            "calibration_receipt_sha256": self.calibration_receipt_sha256,
            "synthetic_fixture_state": self.synthetic_fixture_state.value,
            "synthetic_fixture_request_sha256": self.synthetic_fixture_request_sha256,
            "synthetic_fixture_receipt_sha256": self.synthetic_fixture_receipt_sha256,
            "synthetic_fixture_output_sha256": self.synthetic_fixture_output_sha256,
            "synthetic_fixture_format_state": self.synthetic_fixture_format_state,
            "synthetic_fixture_sample_count": self.synthetic_fixture_sample_count,
            "synthetic_fixture_duration_us": self.synthetic_fixture_duration_us,
            "synthetic_boundary_analysis_state": self.synthetic_boundary_analysis_state,
            "synthetic_loudness_analysis_state": self.synthetic_loudness_analysis_state,
            "synthetic_style_analysis_state": self.synthetic_style_analysis_state,
            "reason_codes": list(self.reason_codes),
            "product_result_bound": False,
            "model_loaded": False,
            "audio_body_persisted": False,
            "text_body_persisted": False,
            "host_path_persisted": False,
            "secret_persisted": False,
            "execution_authorized": False,
            "playback_authorized": False,
            "profile_adoption_authorized": False,
            "asset_publication_authorized": False,
            "automatic_retry_authorized": False,
        }

    @property
    def readback_sha256(self) -> str:
        return _canonical_sha256(self._body())

    def to_dict(self) -> dict[str, Any]:
        body = self._body()
        body["readback_sha256"] = self.readback_sha256
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "QuickCloneReadbackReceipt":
        expected = set(cls._record_fields())
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("QuickCloneReadbackReceipt fields are incomplete or unknown")
        if (
            value["schema_id"] != SCHEMA_ID
            or value["contract_version"] != CONTRACT_VERSION
            or value["record_type"] != "QuickCloneReadbackReceipt"
            or value["task_owner"] != "TASK-046"
            or value["model_configuration_source"]
            != MODEL_CONFIGURATION_SOURCE
            or value["model_configuration_access"]
            != MODEL_CONFIGURATION_ACCESS
            or value["voice_model_selector_present"] is not False
            or value["task014_result_admission_producer_state"] != "NOT_BOUND"
            or value["unified_desktop_binding_state"]
            != UNIFIED_DESKTOP_BINDING_STATE
            or value["trusted_time_binding_state"] != TRUSTED_TIME_BINDING_STATE
            or value["synthetic_fixture_flow_binding_state"]
            != SYNTHETIC_FIXTURE_FLOW_BINDING_STATE
            or value["route"] != "ZERO_SHOT"
            or value["mode"] != "PREVIEW"
        ):
            raise ValueError("QuickCloneReadbackReceipt identity is invalid")
        for field in (
            "product_result_bound",
            "model_loaded",
            "audio_body_persisted",
            "text_body_persisted",
            "host_path_persisted",
            "secret_persisted",
            "execution_authorized",
            "playback_authorized",
            "profile_adoption_authorized",
            "asset_publication_authorized",
            "automatic_retry_authorized",
        ):
            if value[field] is not False:
                raise ValueError(f"{field} violates the no-effect read-back boundary")
        receipt = cls(
            flow_id=value["flow_id"],
            flow_revision=value["flow_revision"],
            flow_revision_sha256=value["flow_revision_sha256"],
            generated_at=value["generated_at"],
            source_kind=SourceKind(value["source_kind"]),
            setup_state=SetupState(value["setup_state"]),
            execution_state=ExecutionState(value["execution_state"]),
            compute_preference=ComputePreference(value["compute_preference"]),
            compute_resolution_state=ComputeResolutionState(
                value["compute_resolution_state"]
            ),
            runtime_aggregate_state=RuntimeAggregateState(
                value["runtime_aggregate_state"]
            ),
            result_admission_state=ResultAdmissionState(
                value["result_admission_state"]
            ),
            output_quality_state=QualityState(value["output_quality_state"]),
            owner_listening_state=OwnerListeningState(value["owner_listening_state"]),
            profile_adoption_state=ProfileAdoptionState(
                value["profile_adoption_state"]
            ),
            preview_asset_adoption_state=PreviewAssetAdoptionState(
                value["preview_asset_adoption_state"]
            ),
            reference_retention_state=ReferenceRetentionState(
                value["reference_retention_state"]
            ),
            flow_reason_codes=_wire_reason_codes(
                value["flow_reason_codes"],
                "flow_reason_codes",
            ),
            task014_preflight_sha256=value["task014_preflight_sha256"],
            task014_preflight_decision=(
                PreflightDecision(value["task014_preflight_decision"])
                if value["task014_preflight_decision"] is not None
                else None
            ),
            model_selection_binding_sha256=value["model_selection_binding_sha256"],
            model_binding_state=ModelBindingState(value["model_binding_state"]),
            model_route_mode=(
                LocalNarrationRouteMode(value["model_route_mode"])
                if value["model_route_mode"] is not None
                else None
            ),
            model_license_state=value["model_license_state"],
            model_capability_probe_state=value["model_capability_probe_state"],
            calibration_binding_sha256=value["calibration_binding_sha256"],
            calibration_contract_state=CalibrationBindingState(
                value["calibration_contract_state"]
            ),
            calibration_result=value["calibration_result"],
            calibration_receipt_sha256=value["calibration_receipt_sha256"],
            synthetic_fixture_state=SyntheticFixtureState(
                value["synthetic_fixture_state"]
            ),
            synthetic_fixture_request_sha256=value[
                "synthetic_fixture_request_sha256"
            ],
            synthetic_fixture_receipt_sha256=value[
                "synthetic_fixture_receipt_sha256"
            ],
            synthetic_fixture_output_sha256=value[
                "synthetic_fixture_output_sha256"
            ],
            synthetic_fixture_format_state=value["synthetic_fixture_format_state"],
            synthetic_fixture_sample_count=value["synthetic_fixture_sample_count"],
            synthetic_fixture_duration_us=value["synthetic_fixture_duration_us"],
            synthetic_boundary_analysis_state=value[
                "synthetic_boundary_analysis_state"
            ],
            synthetic_loudness_analysis_state=value[
                "synthetic_loudness_analysis_state"
            ],
            synthetic_style_analysis_state=value["synthetic_style_analysis_state"],
            reason_codes=_wire_reason_codes(value["reason_codes"], "reason_codes"),
        )
        if value["readback_sha256"] != receipt.readback_sha256:
            raise ValueError("readback_sha256 mismatch")
        return receipt

    @staticmethod
    def _record_fields() -> tuple[str, ...]:
        return (
            "schema_id",
            "contract_version",
            "record_type",
            "task_owner",
            "model_configuration_source",
            "model_configuration_access",
            "voice_model_selector_present",
            "task014_result_admission_producer_state",
            "unified_desktop_binding_state",
            "trusted_time_binding_state",
            "synthetic_fixture_flow_binding_state",
            "flow_id",
            "flow_revision",
            "flow_revision_sha256",
            "generated_at",
            "route",
            "mode",
            "source_kind",
            "setup_state",
            "execution_state",
            "compute_preference",
            "compute_resolution_state",
            "runtime_aggregate_state",
            "result_admission_state",
            "output_quality_state",
            "owner_listening_state",
            "profile_adoption_state",
            "preview_asset_adoption_state",
            "reference_retention_state",
            "flow_reason_codes",
            "task014_preflight_sha256",
            "task014_preflight_decision",
            "model_selection_binding_sha256",
            "model_binding_state",
            "model_route_mode",
            "model_license_state",
            "model_capability_probe_state",
            "calibration_binding_sha256",
            "calibration_contract_state",
            "calibration_result",
            "calibration_receipt_sha256",
            "synthetic_fixture_state",
            "synthetic_fixture_request_sha256",
            "synthetic_fixture_receipt_sha256",
            "synthetic_fixture_output_sha256",
            "synthetic_fixture_format_state",
            "synthetic_fixture_sample_count",
            "synthetic_fixture_duration_us",
            "synthetic_boundary_analysis_state",
            "synthetic_loudness_analysis_state",
            "synthetic_style_analysis_state",
            "reason_codes",
            "product_result_bound",
            "model_loaded",
            "audio_body_persisted",
            "text_body_persisted",
            "host_path_persisted",
            "secret_persisted",
            "execution_authorized",
            "playback_authorized",
            "profile_adoption_authorized",
            "asset_publication_authorized",
            "automatic_retry_authorized",
            "readback_sha256",
        )


def compile_quick_clone_readback(
    *,
    flow: Mapping[str, Any] | QuickCloneFlowRevision,
    task014_preflight: Mapping[str, Any] | LocalPrimaryNarrationPreflight | None,
    calibration_projection: Mapping[str, Any] | None,
    synthetic_fixture_request: Mapping[str, Any] | None,
    synthetic_fixture_receipt: Mapping[str, Any] | None,
    generated_at: str,
) -> QuickCloneReadbackReceipt:
    """Compile a display-only receipt from exact upstream metadata."""
    revision = (
        flow
        if isinstance(flow, QuickCloneFlowRevision)
        else QuickCloneFlowRevision.from_dict(flow)
    )
    if type(revision) is not QuickCloneFlowRevision:
        raise ValueError("fixture-only revisions cannot enter Product read-back")
    _reject_host_paths(revision.to_dict(), "flow")
    generated_at_value = _timestamp_value(generated_at, "generated_at")
    flow_created_at = _timestamp_value(revision.created_at, "flow.created_at")
    if flow_created_at > generated_at_value:
        raise ValueError("flow.created_at must not be later than generated_at")

    parsed_preflight: LocalPrimaryNarrationPreflight | None = None
    model_state = ModelBindingState.NOT_BOUND
    model_route: LocalNarrationRouteMode | None = None
    model_license: str | None = None
    model_capability: str | None = None
    preflight_decision: PreflightDecision | None = None
    preflight_sha256: str | None = None
    if task014_preflight is None:
        if revision.preflight_sha256 is not None:
            raise ValueError("flow preflight_sha256 requires the exact TASK-014 preflight")
    else:
        if revision.source_kind is not SourceKind.TASK003_ASSET:
            raise ValueError("TASK-014 V1 cannot bind a TASK-046 private reference")
        private = (
            task014_preflight.to_private_dict()
            if isinstance(task014_preflight, LocalPrimaryNarrationPreflight)
            else dict(task014_preflight)
        )
        _reject_host_paths(private, "task014_preflight")
        parsed_preflight = parse_local_primary_preflight(private)
        preflight_created_at = _timestamp_value(
            parsed_preflight.created_at,
            "task014_preflight.created_at",
        )
        if preflight_created_at > flow_created_at:
            raise ValueError("TASK-014 preflight must not postdate the Quick Clone flow")
        if preflight_created_at > generated_at_value:
            raise ValueError("TASK-014 preflight must not postdate the read-back")
        if revision.preflight_sha256 is None:
            raise ValueError("TASK-014 preflight cannot be attached to an unbound flow")
        if parsed_preflight.preflight_sha256 != revision.preflight_sha256:
            raise ValueError("TASK-014 preflight digest does not match Quick Clone flow")
        if (
            parsed_preflight.route_mode is not LocalNarrationRouteMode.ZERO_SHOT_LOCAL
            or parsed_preflight.intended_usage is not NarrationIntendedUsage.PREVIEW
        ):
            raise ValueError("Quick Clone read-back requires ZERO_SHOT_LOCAL PREVIEW")

        reference = parsed_preflight.zero_shot_reference_binding
        if reference is None:
            raise ValueError("TASK-014 zero-shot reference binding is missing")
        if _canonical_sha256(dict(reference)) != revision.source_binding_sha256:
            raise ValueError(
                "zero-shot reference revision/profile/consent/rights binding mismatch"
            )
        script_text = parsed_preflight.script_text_binding
        if (
            script_text.get("source_text_binding_sha256")
            != revision.preview_text_sha256
        ):
            raise ValueError("preview text binding does not match TASK-014 preflight")

        engine = dict(parsed_preflight.engine_admission_binding)
        engine_binding_sha256 = _canonical_sha256(engine)
        if engine_binding_sha256 != revision.model_selection_binding_sha256:
            raise ValueError("model selection binding does not match TASK-014 preflight")
        voice = parsed_preflight.voice_profile_revision_binding
        profile_sha = voice.get("voice_profile_revision_sha256")
        if (
            profile_sha is not None
            and profile_sha != revision.preview_profile_revision_sha256
        ):
            raise ValueError("VoiceProfile revision is stale or mismatched")
        consent_sha = voice.get("current_consent_evaluation_sha256")
        if consent_sha is not None and consent_sha != revision.consent_binding_sha256:
            raise ValueError("consent evaluation is stale or mismatched")

        preflight_sha256 = parsed_preflight.preflight_sha256
        preflight_decision = parsed_preflight.decision
        model_state = _model_binding_state(engine["contract_state"])
        model_route = parsed_preflight.route_mode
        model_license = engine["license_state"]
        model_capability = engine["capability_probe_state"]

    if calibration_projection is not None:
        raise ValueError("canonical TASK-048 source bridge is not bound")
    calibration = _unbound_calibration_projection()
    calibration_state = CalibrationBindingState(calibration["contract_state"])
    calibration_sha256 = _canonical_sha256(calibration)

    fixture_state = SyntheticFixtureState.NOT_PROVIDED
    fixture_request_sha256: str | None = None
    fixture_receipt_sha256: str | None = None
    fixture_output_sha256: str | None = None
    fixture_format_state: str | None = None
    fixture_sample_count: int | None = None
    fixture_duration_us: int | None = None
    fixture_boundary: str | None = None
    fixture_loudness: str | None = None
    fixture_style: str | None = None
    if (synthetic_fixture_request is None) != (synthetic_fixture_receipt is None):
        raise ValueError("synthetic fixture requires an exact request/receipt pair")
    if synthetic_fixture_request is not None and synthetic_fixture_receipt is not None:
        _reject_host_paths(synthetic_fixture_request, "synthetic_fixture_request")
        _reject_host_paths(synthetic_fixture_receipt, "synthetic_fixture_receipt")
        request = validate_runtime_record(
            synthetic_fixture_request,
            expected_type="SyntheticMasterAssemblyRequest",
        )
        fixture = validate_runtime_record(
            synthetic_fixture_receipt,
            expected_type="SyntheticMasterAssemblyReceipt",
        )
        _strict_json_integer(request["max_total_frames"], "request.max_total_frames")
        for index, item in enumerate(request["ordered_inputs"]):
            _strict_json_integer(
                item["order_index"],
                f"request.ordered_inputs[{index}].order_index",
            )
            _strict_json_integer(
                item["pause_after_samples"],
                f"request.ordered_inputs[{index}].pause_after_samples",
            )
        for field in (
            "output_bytes",
            "sample_rate_hz",
            "channels",
            "sample_width_bytes",
            "frame_count",
            "duration_numerator",
            "duration_denominator",
            "inserted_silence_samples",
        ):
            _strict_json_integer(fixture[field], f"fixture.{field}")
        expected_cues = [item["cue_sha256"] for item in request["ordered_inputs"]]
        if fixture["request_sha256"] != request["request_sha256"]:
            raise ValueError("synthetic fixture request_sha256 mismatch")
        if fixture["ordered_cue_sha256"] != expected_cues:
            raise ValueError("synthetic fixture ordered Cues mismatch")
        if fixture["output_logical_ref"] != request["output_logical_ref"]:
            raise ValueError("synthetic fixture output logical ref mismatch")
        if request["max_total_frames"] > MAX_SYNTHETIC_PREVIEW_FRAMES:
            raise ValueError("synthetic fixture request exceeds the 60 second preview cap")
        if fixture["frame_count"] > request["max_total_frames"]:
            raise ValueError("synthetic fixture output exceeds the request frame cap")
        if fixture["frame_count"] > MAX_SYNTHETIC_PREVIEW_FRAMES:
            raise ValueError("synthetic fixture output exceeds the 60 second preview cap")
        request_created_at = _timestamp_value(
            request["created_at"],
            "synthetic_fixture_request.created_at",
        )
        fixture_completed_at = _timestamp_value(
            fixture["completed_at"],
            "synthetic_fixture_receipt.completed_at",
        )
        if fixture_completed_at < request_created_at:
            raise ValueError("synthetic fixture receipt must not predate its request")
        if fixture_completed_at > generated_at_value:
            raise ValueError("synthetic fixture receipt must not postdate the read-back")
        fixture_state = SyntheticFixtureState.DEVELOPMENT_FIXTURE_ONLY
        fixture_request_sha256 = request["request_sha256"]
        fixture_receipt_sha256 = fixture["receipt_sha256"]
        fixture_output_sha256 = fixture["output_sha256"]
        fixture_format_state = fixture["format_state"]
        fixture_sample_count = fixture["frame_count"]
        fixture_duration_us = _duration_us(fixture["frame_count"])
        fixture_boundary = fixture["boundary_analysis_state"]
        fixture_loudness = fixture["loudness_analysis_state"]
        fixture_style = fixture["style_analysis_state"]

    reasons = _derive_reason_codes(
        source_kind=revision.source_kind,
        flow_reason_codes=revision.reason_codes,
        preflight_decision=preflight_decision,
        model_binding_state=model_state,
        model_license_state=model_license,
        model_capability_probe_state=model_capability,
        compute_resolution_state=revision.compute_resolution_state,
        runtime_aggregate_state=revision.runtime_aggregate_state,
        calibration_contract_state=calibration_state,
        calibration_result=calibration["result"],
        synthetic_fixture_state=fixture_state,
    )
    return QuickCloneReadbackReceipt(
        flow_id=revision.flow_id,
        flow_revision=revision.revision,
        flow_revision_sha256=revision.flow_revision_sha256,
        generated_at=generated_at,
        source_kind=revision.source_kind,
        setup_state=revision.setup_state,
        execution_state=revision.execution_state,
        compute_preference=revision.compute_preference,
        compute_resolution_state=revision.compute_resolution_state,
        runtime_aggregate_state=revision.runtime_aggregate_state,
        result_admission_state=revision.result_admission_state,
        output_quality_state=revision.quality_state,
        owner_listening_state=revision.owner_listening_state,
        profile_adoption_state=revision.profile_adoption_state,
        preview_asset_adoption_state=revision.preview_asset_adoption_state,
        reference_retention_state=revision.reference_retention_state,
        flow_reason_codes=revision.reason_codes,
        task014_preflight_sha256=preflight_sha256,
        task014_preflight_decision=preflight_decision,
        model_selection_binding_sha256=revision.model_selection_binding_sha256,
        model_binding_state=model_state,
        model_route_mode=model_route,
        model_license_state=model_license,
        model_capability_probe_state=model_capability,
        calibration_binding_sha256=calibration_sha256,
        calibration_contract_state=calibration_state,
        calibration_result=calibration["result"],
        calibration_receipt_sha256=calibration["calibration_receipt_sha256"],
        synthetic_fixture_state=fixture_state,
        synthetic_fixture_request_sha256=fixture_request_sha256,
        synthetic_fixture_receipt_sha256=fixture_receipt_sha256,
        synthetic_fixture_output_sha256=fixture_output_sha256,
        synthetic_fixture_format_state=fixture_format_state,
        synthetic_fixture_sample_count=fixture_sample_count,
        synthetic_fixture_duration_us=fixture_duration_us,
        synthetic_boundary_analysis_state=fixture_boundary,
        synthetic_loudness_analysis_state=fixture_loudness,
        synthetic_style_analysis_state=fixture_style,
        reason_codes=reasons,
    )


def _ui_guidance_ja(receipt: QuickCloneReadbackReceipt) -> dict[str, Any]:
    if receipt.setup_state is SetupState.FAILED:
        readiness = "FAILED"
        status = "音声モデルの確認に失敗しました。中央AI設定で状態を確認してください。"
        next_action = "中央AI設定を確認してから手動で再試行してください。"
        settings_cta = "中央AI設定を開く"
    elif receipt.setup_state is SetupState.NOT_INSTALLED:
        readiness = "NOT_INSTALLED"
        status = "音声モデル実行環境が未導入です。中央AI設定で導入状態を確認してください。"
        next_action = "中央AI設定を開いて音声モデル実行環境を確認してください。"
        settings_cta = "中央AI設定を開く"
    elif receipt.setup_state is SetupState.INSTALL_APPROVAL_REQUIRED:
        readiness = "BLOCKED"
        status = "音声モデル実行環境の導入にはOwner承認が必要です。"
        next_action = "中央AI設定で導入内容を確認し、Owner承認を取得してください。"
        settings_cta = "中央AI設定を開く"
    elif receipt.setup_state is SetupState.VERIFYING:
        readiness = "VERIFYING"
        status = "音声モデルを確認しています。確認完了まで実行できません。"
        next_action = "確認が完了してから正本receiptを再読込してください。"
        settings_cta = None
    elif receipt.setup_state is SetupState.OFFLINE_BUNDLE_REQUIRED:
        readiness = "BLOCKED"
        status = "音声モデル実行環境の確認には承認済みオフラインbundleが必要です。"
        next_action = "中央AI設定で承認済みオフラインbundleの状態を確認してください。"
        settings_cta = "中央AI設定を開く"
    elif receipt.setup_state is SetupState.RESTART_REQUIRED:
        readiness = "BLOCKED"
        status = "音声モデル実行環境の確認を完了するには再起動が必要です。"
        next_action = "作業状態を保存し、準備ができてから手動で再起動してください。"
        settings_cta = None
    elif receipt.setup_state is SetupState.LOCKED_PRIVATE_DATA:
        readiness = "BLOCKED"
        status = "必要な非公開音声データがロックされています。"
        next_action = "非公開データの正当なアクセス状態を確認してください。"
        settings_cta = None
    elif receipt.setup_state is SetupState.BLOCKED:
        readiness = "BLOCKED"
        status = "音声モデルの準備がブロックされています。表示された理由を確認してください。"
        next_action = "正本receiptの理由を確認し、必要な前提を解消してください。"
        settings_cta = None
    elif receipt.setup_state is SetupState.UNKNOWN:
        readiness = "UNKNOWN"
        status = "音声モデルの状態を確認できません。自動再試行はしません。"
        next_action = "正本receiptを再読込し、中央AI設定を確認してください。"
        settings_cta = "中央AI設定を開く"
    elif receipt.model_binding_state is ModelBindingState.NOT_BOUND:
        readiness = "NOT_INSTALLED"
        status = "音声モデルが未設定です。中央AI設定でモデルを選択してください。"
        next_action = "中央AI設定を開いて音声モデルを設定してください。"
        settings_cta = "中央AI設定を開く"
    elif (
        receipt.model_capability_probe_state == "FAILED"
        or receipt.model_binding_state is ModelBindingState.MISMATCH
        or receipt.model_license_state
        in {"NONCOMMERCIAL_ONLY", "RESTRICTED", "REVOKED"}
    ):
        readiness = "FAILED"
        status = "音声モデルの確認に失敗しました。中央AI設定で状態を確認してください。"
        next_action = "中央AI設定を確認してから手動で再試行してください。"
        settings_cta = "中央AI設定を開く"
    elif (
        receipt.model_capability_probe_state == "UNKNOWN"
        or receipt.model_binding_state is ModelBindingState.UNKNOWN
        or receipt.model_license_state in {"UNKNOWN", "LEGAL_REVIEW_REQUIRED"}
    ):
        readiness = "UNKNOWN"
        status = "音声モデルの状態を確認できません。自動再試行はしません。"
        next_action = "正本receiptを再読込し、中央AI設定を確認してください。"
        settings_cta = "中央AI設定を開く"
    elif receipt.task014_preflight_decision is PreflightDecision.BLOCKED:
        readiness = "READY"
        status = "実行前確認でブロックされています。表示された理由を確認してください。"
        next_action = "表示された理由と正本receiptを確認し、必要な前提を解消してください。"
        settings_cta = None
    elif receipt.task014_preflight_decision is PreflightDecision.UNKNOWN:
        readiness = "READY"
        status = "実行前確認の状態を確認できません。自動再試行はしません。"
        next_action = "表示された理由と正本receiptを再確認してください。"
        settings_cta = None
    elif (
        receipt.setup_state is SetupState.READY
        and receipt.task014_preflight_decision
        is PreflightDecision.READY_FOR_OWNER_HUMAN_GATE
        and receipt.model_binding_state is ModelBindingState.BOUND_VERIFIED
        and receipt.model_license_state == "COMMERCIAL_ALLOWED"
        and receipt.model_capability_probe_state == "VERIFIED"
    ):
        readiness = "READY"
        status = "音声モデルの準備確認が完了しました。"
        next_action = "不足している正本receiptとHuman Gateを確認してください。"
        settings_cta = None
    else:
        readiness = "UNKNOWN"
        status = "音声モデルの状態を確認できません。自動再試行はしません。"
        next_action = "正本receiptを再読込し、中央AI設定を確認してください。"
        settings_cta = "中央AI設定を開く"
    return {
        "model_readiness_state": readiness,
        "status_message_ja": status,
        "settings_cta_label_ja": settings_cta,
        "settings_cta_target": "SETTINGS_AI" if settings_cta else None,
        "cancel_action_label_ja": "キャンセル",
        "retry_action_label_ja": "再試行",
        "retry_requires_confirmation": True,
        "next_action_ja": next_action,
    }


def public_projection(
    value: Mapping[str, Any] | QuickCloneReadbackReceipt,
) -> dict[str, Any]:
    """Return log-safe UI facts without refs, digests, timestamps, text, or audio."""
    receipt = (
        value
        if isinstance(value, QuickCloneReadbackReceipt)
        else QuickCloneReadbackReceipt.from_dict(value)
    )
    has_fixture = (
        receipt.synthetic_fixture_state
        is SyntheticFixtureState.DEVELOPMENT_FIXTURE_ONLY
    )
    projection = {
        "record_type": "QuickCloneReadbackPublicProjection",
        "contract_version": CONTRACT_VERSION,
        "flow_revision": receipt.flow_revision,
        "model_configuration_source": MODEL_CONFIGURATION_SOURCE,
        "model_configuration_access": MODEL_CONFIGURATION_ACCESS,
        "voice_model_selector_present": False,
        "route": "ZERO_SHOT",
        "mode": "PREVIEW",
        "task014_result_admission_producer_state": "NOT_BOUND",
        "unified_desktop_binding_state": UNIFIED_DESKTOP_BINDING_STATE,
        "trusted_time_binding_state": TRUSTED_TIME_BINDING_STATE,
        "trusted_currentness_verified": False,
        "canonical_receipt_currentness_state": (
            "UNKNOWN"
            if receipt.execution_state is ExecutionState.UNKNOWN
            or receipt.runtime_aggregate_state is RuntimeAggregateState.UNKNOWN
            else "NOT_BOUND"
        ),
        "synthetic_fixture_flow_binding_state": (
            SYNTHETIC_FIXTURE_FLOW_BINDING_STATE
        ),
        "source_kind": receipt.source_kind.value,
        "setup_state": receipt.setup_state.value,
        "execution_state": receipt.execution_state.value,
        "compute_preference": receipt.compute_preference.value,
        "compute_resolution_state": receipt.compute_resolution_state.value,
        "runtime_aggregate_state": receipt.runtime_aggregate_state.value,
        "result_admission_state": receipt.result_admission_state.value,
        "output_quality_state": receipt.output_quality_state.value,
        "owner_listening_state": receipt.owner_listening_state.value,
        "profile_adoption_state": receipt.profile_adoption_state.value,
        "preview_asset_adoption_state": receipt.preview_asset_adoption_state.value,
        "reference_retention_state": receipt.reference_retention_state.value,
        "task014_preflight_decision": (
            receipt.task014_preflight_decision.value
            if receipt.task014_preflight_decision is not None
            else None
        ),
        "model_binding_state": receipt.model_binding_state.value,
        "model_route_mode": (
            receipt.model_route_mode.value if receipt.model_route_mode is not None else None
        ),
        "model_license_state": receipt.model_license_state,
        "model_capability_probe_state": receipt.model_capability_probe_state,
        "model_loaded": False,
        "reference_calibration_contract_state": (
            receipt.calibration_contract_state.value
        ),
        "reference_calibration_result": receipt.calibration_result,
        "synthetic_fixture_state": receipt.synthetic_fixture_state.value,
        "synthetic_fixture_format_state": receipt.synthetic_fixture_format_state,
        "synthetic_fixture_sample_rate_hz": 48_000 if has_fixture else None,
        "synthetic_fixture_channels": 1 if has_fixture else None,
        "synthetic_fixture_sample_format": "PCM_S24LE" if has_fixture else None,
        "synthetic_fixture_sample_count": receipt.synthetic_fixture_sample_count,
        "synthetic_fixture_duration_us": receipt.synthetic_fixture_duration_us,
        "synthetic_boundary_analysis_state": (
            receipt.synthetic_boundary_analysis_state
        ),
        "synthetic_loudness_analysis_state": (
            receipt.synthetic_loudness_analysis_state
        ),
        "synthetic_style_analysis_state": receipt.synthetic_style_analysis_state,
        "synthetic_fixture_request_receipt_pair_verified": has_fixture,
        "synthetic_fixture_is_product_result": False,
        "product_result_bound": False,
        "execution_enabled": False,
        "product_preview_playback_ready": False,
        "profile_save_ready": False,
        "asset_publication_ready": False,
        "reason_code_count": len(receipt.reason_codes),
        "has_blocking_reason": bool(receipt.reason_codes),
        "private_identity_exposed": False,
        "audio_body_exposed": False,
        "text_body_exposed": False,
        "host_path_exposed": False,
        "secret_exposed": False,
        "digest_identity_exposed": False,
        "external_effect_authorized": False,
        "automatic_retry_authorized": False,
    }
    projection.update(_ui_guidance_ja(receipt))
    return projection


def assert_no_effect_surface() -> None:
    forbidden = {
        "os",
        "pathlib",
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "torch",
        "transformers",
        "soundfile",
        "wave",
    }
    if forbidden & set(globals()):
        raise AssertionError("effect-capable runtime surface detected")


__all__ = [
    "CalibrationBindingState",
    "CONTRACT_VERSION",
    "MAX_SYNTHETIC_PREVIEW_FRAMES",
    "ModelBindingState",
    "QuickCloneReadbackReceipt",
    "SCHEMA_ID",
    "SYNTHETIC_FIXTURE_FLOW_BINDING_STATE",
    "SyntheticFixtureState",
    "TRUSTED_TIME_BINDING_STATE",
    "UNIFIED_DESKTOP_BINDING_STATE",
    "assert_no_effect_surface",
    "compile_quick_clone_readback",
    "public_projection",
]
