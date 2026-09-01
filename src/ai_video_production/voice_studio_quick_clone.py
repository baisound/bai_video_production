"""Body-free TASK-046 Quick Clone UI and lifecycle contract.

This module validates metadata that an application may display after reading
canonical receipts owned by other Tasks.  It does not open audio, resolve host
paths, download or load a model, dispatch a job, play audio, write a WAV, adopt
an Asset, or delete private material.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from typing import Any, Mapping

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_ID = "bai.task046.voice-studio-quick-clone.v1"
CONTRACT_VERSION = "1.0.0"
MAX_PREVIEW_TEXT_CODE_POINTS = 200
MAX_PREVIEW_DURATION_SECONDS = 60
SAMPLE_RATE_HZ = 48_000
CHANNELS = 1
SAMPLE_FORMAT = "PCM_S24LE"
INTENDED_ARTIFACT = "STAGED_NARRATION_PCM_WAV_48000_MONO"
_FLOW_ID_RE = re.compile(r"quick-clone:[A-Za-z0-9][A-Za-z0-9._-]{0,243}")
_STAGED_WAV_REF_RE = re.compile(
    r"staged-narration:[A-Za-z0-9][A-Za-z0-9._-]{0,127}"
    r"(?:/[A-Za-z0-9][A-Za-z0-9._-]{0,127})*/"
    r"[A-Za-z0-9][A-Za-z0-9_-]{0,119}\.wav"
)
_ASSET_REF_RE = re.compile(
    r"asset:[A-Za-z0-9][A-Za-z0-9._-]{0,127}"
    r"(?:/[A-Za-z0-9][A-Za-z0-9._-]{0,127})*"
)
_REASON_RE = re.compile(r"[A-Z][A-Z0-9_]{1,95}")


class SetupState(str, Enum):
    NOT_INSTALLED = "NOT_INSTALLED"
    INSTALL_APPROVAL_REQUIRED = "INSTALL_APPROVAL_REQUIRED"
    VERIFYING = "VERIFYING"
    READY = "READY"
    OFFLINE_BUNDLE_REQUIRED = "OFFLINE_BUNDLE_REQUIRED"
    RESTART_REQUIRED = "RESTART_REQUIRED"
    LOCKED_PRIVATE_DATA = "LOCKED_PRIVATE_DATA"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class ExecutionState(str, Enum):
    DRAFT = "DRAFT"
    PREFLIGHT_BLOCKED = "PREFLIGHT_BLOCKED"
    READY_FOR_CONFIRMATION = "READY_FOR_CONFIRMATION"
    DISPATCHING = "DISPATCHING"
    RUNNING = "RUNNING"
    READY_FOR_QA_REVIEW = "READY_FOR_QA_REVIEW"
    FAILED_KNOWN = "FAILED_KNOWN"
    UNKNOWN = "UNKNOWN"


class QualityState(str, Enum):
    NOT_AVAILABLE = "NOT_AVAILABLE"
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class OwnerListeningState(str, Enum):
    NOT_AVAILABLE = "NOT_AVAILABLE"
    REQUIRED = "REQUIRED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class ProfileAdoptionState(str, Enum):
    NOT_AVAILABLE = "NOT_AVAILABLE"
    SAVE_DECISION_REQUIRED = "SAVE_DECISION_REQUIRED"
    SAVED_LOCAL_CANDIDATE = "SAVED_LOCAL_CANDIDATE"
    PROFILE_NOT_SAVED = "PROFILE_NOT_SAVED"
    STALE = "STALE"
    REVOKED = "REVOKED"


class PreviewAssetAdoptionState(str, Enum):
    NOT_AVAILABLE = "NOT_AVAILABLE"
    PUBLISH_DECISION_REQUIRED = "PUBLISH_DECISION_REQUIRED"
    ASSET_NOT_PUBLISHED = "ASSET_NOT_PUBLISHED"
    ASSET_PUBLISHED_RESTRICTED = "ASSET_PUBLISHED_RESTRICTED"
    STALE = "STALE"
    REVOKED = "REVOKED"


class ReferenceRetentionState(str, Enum):
    UNDECIDED = "UNDECIDED"
    RETAIN_PRIVATE_REFERENCE = "RETAIN_PRIVATE_REFERENCE"
    DO_NOT_RETAIN_PRIVATE_REFERENCE = "DO_NOT_RETAIN_PRIVATE_REFERENCE"
    RETENTION_REVOKED = "RETENTION_REVOKED"
    EXPIRED = "EXPIRED"


class ComputePreference(str, Enum):
    AUTO = "AUTO"
    GPU = "GPU"
    CPU = "CPU"


class ComputeResolutionState(str, Enum):
    NOT_RESOLVED = "NOT_RESOLVED"
    GPU_READY = "GPU_READY"
    CPU_READY = "CPU_READY"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class ModelExecutionPolicy(str, Enum):
    CUDA_ONLY = "CUDA_ONLY"
    CPU_ALLOWED = "CPU_ALLOWED"


class RuntimeAggregateState(str, Enum):
    NOT_BOUND = "NOT_BOUND"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class ResultAdmissionState(str, Enum):
    NOT_BOUND = "NOT_BOUND"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class SourceKind(str, Enum):
    TASK003_ASSET = "TASK003_ASSET"
    TASK046_PRIVATE_REFERENCE = "TASK046_PRIVATE_REFERENCE"


_TRANSITIONS: dict[ExecutionState, frozenset[ExecutionState]] = {
    ExecutionState.DRAFT: frozenset(
        {ExecutionState.DRAFT, ExecutionState.PREFLIGHT_BLOCKED, ExecutionState.READY_FOR_CONFIRMATION}
    ),
    ExecutionState.PREFLIGHT_BLOCKED: frozenset(
        {ExecutionState.PREFLIGHT_BLOCKED, ExecutionState.READY_FOR_CONFIRMATION}
    ),
    ExecutionState.READY_FOR_CONFIRMATION: frozenset(
        {ExecutionState.PREFLIGHT_BLOCKED, ExecutionState.DISPATCHING}
    ),
    ExecutionState.DISPATCHING: frozenset(
        {
            ExecutionState.RUNNING,
            ExecutionState.READY_FOR_QA_REVIEW,
            ExecutionState.FAILED_KNOWN,
            ExecutionState.UNKNOWN,
        }
    ),
    ExecutionState.RUNNING: frozenset(
        {ExecutionState.READY_FOR_QA_REVIEW, ExecutionState.FAILED_KNOWN, ExecutionState.UNKNOWN}
    ),
    ExecutionState.READY_FOR_QA_REVIEW: frozenset({ExecutionState.READY_FOR_QA_REVIEW}),
    ExecutionState.FAILED_KNOWN: frozenset(),
    ExecutionState.UNKNOWN: frozenset(
        {ExecutionState.UNKNOWN, ExecutionState.READY_FOR_QA_REVIEW, ExecutionState.FAILED_KNOWN}
    ),
}

_QUALITY_TRANSITIONS: dict[QualityState, frozenset[QualityState]] = {
    QualityState.NOT_AVAILABLE: frozenset({QualityState.NOT_AVAILABLE, QualityState.PENDING}),
    QualityState.PENDING: frozenset(
        {QualityState.PENDING, QualityState.PASS, QualityState.FAIL, QualityState.UNKNOWN}
    ),
    QualityState.PASS: frozenset({QualityState.PASS}),
    QualityState.FAIL: frozenset({QualityState.FAIL}),
    QualityState.UNKNOWN: frozenset({QualityState.UNKNOWN}),
}

_LISTENING_TRANSITIONS: dict[OwnerListeningState, frozenset[OwnerListeningState]] = {
    OwnerListeningState.NOT_AVAILABLE: frozenset(
        {OwnerListeningState.NOT_AVAILABLE, OwnerListeningState.REQUIRED}
    ),
    OwnerListeningState.REQUIRED: frozenset(
        {
            OwnerListeningState.REQUIRED,
            OwnerListeningState.ACCEPTED,
            OwnerListeningState.REJECTED,
        }
    ),
    OwnerListeningState.ACCEPTED: frozenset({OwnerListeningState.ACCEPTED}),
    OwnerListeningState.REJECTED: frozenset({OwnerListeningState.REJECTED}),
}

_PROFILE_ADOPTION_TRANSITIONS: dict[ProfileAdoptionState, frozenset[ProfileAdoptionState]] = {
    ProfileAdoptionState.NOT_AVAILABLE: frozenset(
        {
            ProfileAdoptionState.NOT_AVAILABLE,
            ProfileAdoptionState.SAVE_DECISION_REQUIRED,
            ProfileAdoptionState.PROFILE_NOT_SAVED,
        }
    ),
    ProfileAdoptionState.SAVE_DECISION_REQUIRED: frozenset(
        {
            ProfileAdoptionState.SAVE_DECISION_REQUIRED,
            ProfileAdoptionState.SAVED_LOCAL_CANDIDATE,
            ProfileAdoptionState.PROFILE_NOT_SAVED,
        }
    ),
    ProfileAdoptionState.SAVED_LOCAL_CANDIDATE: frozenset(
        {
            ProfileAdoptionState.SAVED_LOCAL_CANDIDATE,
            ProfileAdoptionState.STALE,
            ProfileAdoptionState.REVOKED,
        }
    ),
    ProfileAdoptionState.PROFILE_NOT_SAVED: frozenset({ProfileAdoptionState.PROFILE_NOT_SAVED}),
    ProfileAdoptionState.STALE: frozenset({ProfileAdoptionState.STALE}),
    ProfileAdoptionState.REVOKED: frozenset({ProfileAdoptionState.REVOKED}),
}

_ASSET_ADOPTION_TRANSITIONS: dict[
    PreviewAssetAdoptionState, frozenset[PreviewAssetAdoptionState]
] = {
    PreviewAssetAdoptionState.NOT_AVAILABLE: frozenset(
        {
            PreviewAssetAdoptionState.NOT_AVAILABLE,
            PreviewAssetAdoptionState.PUBLISH_DECISION_REQUIRED,
            PreviewAssetAdoptionState.ASSET_NOT_PUBLISHED,
        }
    ),
    PreviewAssetAdoptionState.PUBLISH_DECISION_REQUIRED: frozenset(
        {
            PreviewAssetAdoptionState.PUBLISH_DECISION_REQUIRED,
            PreviewAssetAdoptionState.ASSET_NOT_PUBLISHED,
            PreviewAssetAdoptionState.ASSET_PUBLISHED_RESTRICTED,
        }
    ),
    PreviewAssetAdoptionState.ASSET_NOT_PUBLISHED: frozenset(
        {PreviewAssetAdoptionState.ASSET_NOT_PUBLISHED}
    ),
    PreviewAssetAdoptionState.ASSET_PUBLISHED_RESTRICTED: frozenset(
        {
            PreviewAssetAdoptionState.ASSET_PUBLISHED_RESTRICTED,
            PreviewAssetAdoptionState.STALE,
            PreviewAssetAdoptionState.REVOKED,
        }
    ),
    PreviewAssetAdoptionState.STALE: frozenset({PreviewAssetAdoptionState.STALE}),
    PreviewAssetAdoptionState.REVOKED: frozenset({PreviewAssetAdoptionState.REVOKED}),
}

_RETENTION_TRANSITIONS: dict[ReferenceRetentionState, frozenset[ReferenceRetentionState]] = {
    ReferenceRetentionState.UNDECIDED: frozenset(ReferenceRetentionState),
    ReferenceRetentionState.RETAIN_PRIVATE_REFERENCE: frozenset(
        {
            ReferenceRetentionState.RETAIN_PRIVATE_REFERENCE,
            ReferenceRetentionState.RETENTION_REVOKED,
            ReferenceRetentionState.EXPIRED,
        }
    ),
    ReferenceRetentionState.DO_NOT_RETAIN_PRIVATE_REFERENCE: frozenset(
        {ReferenceRetentionState.DO_NOT_RETAIN_PRIVATE_REFERENCE}
    ),
    ReferenceRetentionState.RETENTION_REVOKED: frozenset(
        {ReferenceRetentionState.RETENTION_REVOKED}
    ),
    ReferenceRetentionState.EXPIRED: frozenset({ReferenceRetentionState.EXPIRED}),
}

_RESULT_ADMISSION_TRANSITIONS: dict[ResultAdmissionState, frozenset[ResultAdmissionState]] = {
    ResultAdmissionState.NOT_BOUND: frozenset(ResultAdmissionState),
    ResultAdmissionState.BOUND_VERIFIED: frozenset({ResultAdmissionState.BOUND_VERIFIED}),
    ResultAdmissionState.MISMATCH: frozenset({ResultAdmissionState.MISMATCH}),
    ResultAdmissionState.UNKNOWN: frozenset(
        {
            ResultAdmissionState.UNKNOWN,
            ResultAdmissionState.BOUND_VERIFIED,
            ResultAdmissionState.MISMATCH,
        }
    ),
}


def _logical_id(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    patterns = {
        "flow_id": _FLOW_ID_RE,
        "staged_wav_ref": _STAGED_WAV_REF_RE,
        "preview_asset_ref": _ASSET_REF_RE,
    }
    pattern = patterns.get(name)
    if pattern is None:
        raise AssertionError(f"no closed logical namespace is defined for {name}")
    if (
        not isinstance(value, str)
        or len(value) > 256
        or not pattern.fullmatch(value)
    ):
        raise ValueError(f"{name} is invalid")
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


def _duration_us(sample_count: int) -> int:
    return (sample_count * 1_000_000 + SAMPLE_RATE_HZ // 2) // SAMPLE_RATE_HZ


def _reason_codes(value: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(value, tuple) or len(value) > 64 or len(value) != len(set(value)):
        raise ValueError("reason_codes must be a unique bounded tuple")
    if value != tuple(sorted(value)):
        raise ValueError("reason_codes must be sorted")
    if any(not isinstance(item, str) or not _REASON_RE.fullmatch(item) for item in value):
        raise ValueError("reason_codes contain an invalid value")
    return value


@dataclass(frozen=True, slots=True)
class QuickCloneFlowRevision:
    flow_id: str
    revision: int
    parent_revision_sha256: str | None
    created_at: str
    source_kind: SourceKind
    setup_state: SetupState
    execution_state: ExecutionState
    quality_state: QualityState
    owner_listening_state: OwnerListeningState
    profile_adoption_state: ProfileAdoptionState
    preview_asset_adoption_state: PreviewAssetAdoptionState
    reference_retention_state: ReferenceRetentionState
    compute_preference: ComputePreference
    compute_resolution_state: ComputeResolutionState
    model_execution_policy: ModelExecutionPolicy
    runtime_aggregate_state: RuntimeAggregateState
    result_admission_state: ResultAdmissionState
    source_binding_sha256: str
    consent_binding_sha256: str
    reference_transcript_sha256: str
    preview_text_sha256: str
    preview_text_code_points: int
    preview_profile_revision_sha256: str
    model_selection_binding_sha256: str
    runtime_aggregate_binding_sha256: str | None
    preflight_sha256: str | None = None
    one_shot_authorization_sha256: str | None = None
    durable_job_sha256: str | None = None
    render_operation_identity_sha256: str | None = None
    result_receipt_sha256: str | None = None
    result_admission_receipt_sha256: str | None = None
    result_render_operation_identity_sha256: str | None = None
    result_preview_profile_revision_sha256: str | None = None
    result_model_selection_binding_sha256: str | None = None
    result_runtime_aggregate_binding_sha256: str | None = None
    result_output_sha256: str | None = None
    result_route: str | None = None
    result_replay: bool | None = None
    quality_receipt_sha256: str | None = None
    owner_listening_receipt_sha256: str | None = None
    staged_wav_ref: str | None = None
    staged_wav_sha256: str | None = None
    sample_count: int | None = None
    duration_us: int | None = None
    saved_profile_revision_sha256: str | None = None
    profile_adoption_receipt_sha256: str | None = None
    profile_currentness_receipt_sha256: str | None = None
    preview_asset_ref: str | None = None
    preview_asset_sha256: str | None = None
    asset_adoption_receipt_sha256: str | None = None
    preview_asset_currentness_receipt_sha256: str | None = None
    reference_retention_decision_sha256: str | None = None
    reference_retention_currentness_receipt_sha256: str | None = None
    reconciliation_receipt_sha256: str | None = None
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _logical_id(self.flow_id, "flow_id")
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 1:
            raise ValueError("revision must be an integer >= 1")
        _sha(self.parent_revision_sha256, "parent_revision_sha256", nullable=True)
        if (self.revision == 1) != (self.parent_revision_sha256 is None):
            raise ValueError("revision parent binding is invalid")
        _timestamp(self.created_at, "created_at")
        for enum_type, value, name in (
            (SourceKind, self.source_kind, "source_kind"),
            (SetupState, self.setup_state, "setup_state"),
            (ExecutionState, self.execution_state, "execution_state"),
            (QualityState, self.quality_state, "quality_state"),
            (OwnerListeningState, self.owner_listening_state, "owner_listening_state"),
            (ProfileAdoptionState, self.profile_adoption_state, "profile_adoption_state"),
            (PreviewAssetAdoptionState, self.preview_asset_adoption_state, "preview_asset_adoption_state"),
            (ReferenceRetentionState, self.reference_retention_state, "reference_retention_state"),
            (ComputePreference, self.compute_preference, "compute_preference"),
            (ComputeResolutionState, self.compute_resolution_state, "compute_resolution_state"),
            (ModelExecutionPolicy, self.model_execution_policy, "model_execution_policy"),
            (RuntimeAggregateState, self.runtime_aggregate_state, "runtime_aggregate_state"),
            (ResultAdmissionState, self.result_admission_state, "result_admission_state"),
        ):
            if not isinstance(value, enum_type):
                raise ValueError(f"{name} is invalid")
        for name in (
            "source_binding_sha256",
            "consent_binding_sha256",
            "reference_transcript_sha256",
            "preview_text_sha256",
            "preview_profile_revision_sha256",
            "model_selection_binding_sha256",
        ):
            _sha(getattr(self, name), name)
        for name in (
            "runtime_aggregate_binding_sha256",
            "preflight_sha256",
            "one_shot_authorization_sha256",
            "durable_job_sha256",
            "render_operation_identity_sha256",
            "result_receipt_sha256",
            "result_admission_receipt_sha256",
            "result_render_operation_identity_sha256",
            "result_preview_profile_revision_sha256",
            "result_model_selection_binding_sha256",
            "result_runtime_aggregate_binding_sha256",
            "result_output_sha256",
            "quality_receipt_sha256",
            "owner_listening_receipt_sha256",
            "staged_wav_sha256",
            "saved_profile_revision_sha256",
            "profile_adoption_receipt_sha256",
            "profile_currentness_receipt_sha256",
            "preview_asset_sha256",
            "asset_adoption_receipt_sha256",
            "preview_asset_currentness_receipt_sha256",
            "reference_retention_decision_sha256",
            "reference_retention_currentness_receipt_sha256",
            "reconciliation_receipt_sha256",
        ):
            _sha(getattr(self, name), name, nullable=True)
        for name in ("staged_wav_ref", "preview_asset_ref"):
            _logical_id(getattr(self, name), name, nullable=True)
        if self.result_route not in {None, "ZERO_SHOT"}:
            raise ValueError("result_route must be ZERO_SHOT when bound")
        if self.result_replay not in {None, False}:
            raise ValueError("result replay is forbidden")
        if (
            not isinstance(self.preview_text_code_points, int)
            or isinstance(self.preview_text_code_points, bool)
            or not 1 <= self.preview_text_code_points <= MAX_PREVIEW_TEXT_CODE_POINTS
        ):
            raise ValueError("preview_text_code_points is outside the bounded preview policy")
        _reason_codes(self.reason_codes)
        self._validate_setup()
        self._validate_execution()
        self._validate_result_and_review()
        self._validate_adoption()

    def _task014_result_admission_producer_state(self) -> str:
        """Return the immutable current Product producer state."""
        return "NOT_BOUND"

    def _validate_setup(self) -> None:
        if self.runtime_aggregate_state is RuntimeAggregateState.BOUND_VERIFIED:
            _sha(
                self.runtime_aggregate_binding_sha256,
                "runtime_aggregate_binding_sha256",
            )
        elif self.runtime_aggregate_binding_sha256 is not None:
            raise ValueError("unverified runtime cannot bind a runtime aggregate digest")
        if self.compute_resolution_state is ComputeResolutionState.CPU_READY:
            if self.model_execution_policy is ModelExecutionPolicy.CUDA_ONLY:
                raise ValueError("CUDA_ONLY model cannot resolve to CPU_READY")
            if self.compute_preference is ComputePreference.GPU:
                raise ValueError("GPU preference cannot resolve to CPU_READY")
        if (
            self.compute_resolution_state is ComputeResolutionState.GPU_READY
            and self.compute_preference is ComputePreference.CPU
        ):
            raise ValueError("CPU preference cannot resolve to GPU_READY")
        if self.setup_state is SetupState.READY:
            if self.runtime_aggregate_state is not RuntimeAggregateState.BOUND_VERIFIED:
                raise ValueError("READY setup requires a verified runtime aggregate")
            if self.compute_resolution_state not in {
                ComputeResolutionState.GPU_READY,
                ComputeResolutionState.CPU_READY,
            }:
                raise ValueError("READY setup requires an admitted compute route")
            if (
                self.model_execution_policy is ModelExecutionPolicy.CUDA_ONLY
                and self.compute_resolution_state is not ComputeResolutionState.GPU_READY
            ):
                raise ValueError("CUDA_ONLY setup requires GPU_READY")

    def _validate_execution(self) -> None:
        if (
            self._task014_result_admission_producer_state() != "BOUND_VERIFIED"
            and self.execution_state
            not in {ExecutionState.DRAFT, ExecutionState.PREFLIGHT_BLOCKED}
        ):
            raise ValueError(
                "execution is blocked while TASK-014 result admission producer is NOT_BOUND"
            )
        if self.execution_state is ExecutionState.DRAFT:
            if any(
                value is not None
                for value in (
                    self.preflight_sha256,
                    self.one_shot_authorization_sha256,
                    self.durable_job_sha256,
                    self.render_operation_identity_sha256,
                )
            ):
                raise ValueError("DRAFT cannot claim preflight or execution bindings")
        else:
            _sha(self.preflight_sha256, "preflight_sha256")
        ready_or_later = {
            ExecutionState.READY_FOR_CONFIRMATION,
            ExecutionState.DISPATCHING,
            ExecutionState.RUNNING,
            ExecutionState.READY_FOR_QA_REVIEW,
            ExecutionState.FAILED_KNOWN,
            ExecutionState.UNKNOWN,
        }
        if self.execution_state in ready_or_later:
            if self.setup_state is not SetupState.READY:
                raise ValueError("execution readiness requires READY setup")
            _sha(self.one_shot_authorization_sha256, "one_shot_authorization_sha256")
        dispatched = {
            ExecutionState.DISPATCHING,
            ExecutionState.RUNNING,
            ExecutionState.READY_FOR_QA_REVIEW,
            ExecutionState.FAILED_KNOWN,
            ExecutionState.UNKNOWN,
        }
        if self.execution_state in dispatched:
            _sha(self.durable_job_sha256, "durable_job_sha256")
            _sha(
                self.render_operation_identity_sha256,
                "render_operation_identity_sha256",
            )
        elif (
            self.durable_job_sha256 is not None
            or self.render_operation_identity_sha256 is not None
        ):
            raise ValueError("pre-dispatch state cannot claim a Job or operation identity")
        if self.execution_state in {
            ExecutionState.PREFLIGHT_BLOCKED,
            ExecutionState.FAILED_KNOWN,
            ExecutionState.UNKNOWN,
        } and not self.reason_codes:
            raise ValueError("blocked, failed, and unknown states require reason_codes")

    def _validate_result_and_review(self) -> None:
        has_result = self.result_receipt_sha256 is not None
        if (
            self.result_admission_state is ResultAdmissionState.BOUND_VERIFIED
            or has_result
        ) and self._task014_result_admission_producer_state() != "BOUND_VERIFIED":
            raise ValueError(
                "canonical TASK-014 result admission producer is NOT_BOUND"
            )
        result_values = (
            self.result_admission_receipt_sha256,
            self.result_render_operation_identity_sha256,
            self.result_preview_profile_revision_sha256,
            self.result_model_selection_binding_sha256,
            self.result_runtime_aggregate_binding_sha256,
            self.result_output_sha256,
            self.result_route,
            self.result_replay,
            self.staged_wav_ref,
            self.staged_wav_sha256,
            self.sample_count,
            self.duration_us,
        )
        if has_result != (
            self.result_admission_state is ResultAdmissionState.BOUND_VERIFIED
        ):
            raise ValueError("result requires a verified TASK-014 admission binding")
        if self.execution_state is ExecutionState.READY_FOR_QA_REVIEW:
            if self.result_admission_state is not ResultAdmissionState.BOUND_VERIFIED:
                raise ValueError("READY_FOR_QA_REVIEW requires verified result admission")
        elif has_result:
            raise ValueError("only READY_FOR_QA_REVIEW may bind a result receipt")
        if (
            self.result_admission_state is ResultAdmissionState.MISMATCH
            and self.execution_state is not ExecutionState.FAILED_KNOWN
        ):
            raise ValueError("result admission MISMATCH must fail known")
        if (
            self.result_admission_state is ResultAdmissionState.UNKNOWN
            and self.execution_state is not ExecutionState.UNKNOWN
        ):
            raise ValueError("unknown result admission must remain UNKNOWN")
        if not has_result:
            if any(value is not None for value in result_values):
                raise ValueError("result metadata requires verified result admission")
            if self.quality_state is not QualityState.NOT_AVAILABLE:
                raise ValueError("quality cannot be claimed before a result")
            if self.owner_listening_state is not OwnerListeningState.NOT_AVAILABLE:
                raise ValueError("Owner listening cannot be claimed before a result")
            if self.quality_receipt_sha256 is not None or self.owner_listening_receipt_sha256 is not None:
                raise ValueError("review receipts require a result")
            return
        _sha(
            self.result_admission_receipt_sha256,
            "result_admission_receipt_sha256",
        )
        if (
            self.result_render_operation_identity_sha256
            != self.render_operation_identity_sha256
        ):
            raise ValueError("result operation identity mismatch")
        if (
            self.result_preview_profile_revision_sha256
            != self.preview_profile_revision_sha256
        ):
            raise ValueError("result VoiceProfile revision mismatch")
        if (
            self.result_model_selection_binding_sha256
            != self.model_selection_binding_sha256
        ):
            raise ValueError("result model binding mismatch")
        if (
            self.result_runtime_aggregate_binding_sha256
            != self.runtime_aggregate_binding_sha256
        ):
            raise ValueError("result runtime binding mismatch")
        if self.result_route != "ZERO_SHOT":
            raise ValueError("result route mismatch")
        if self.result_replay is not False:
            raise ValueError("result must prove replay=false")
        _logical_id(self.staged_wav_ref, "staged_wav_ref")
        _sha(self.staged_wav_sha256, "staged_wav_sha256")
        if self.result_output_sha256 != self.staged_wav_sha256:
            raise ValueError("result output hash mismatch")
        if (
            not isinstance(self.sample_count, int)
            or isinstance(self.sample_count, bool)
            or not 1 <= self.sample_count <= SAMPLE_RATE_HZ * MAX_PREVIEW_DURATION_SECONDS
        ):
            raise ValueError("sample_count is outside the bounded preview policy")
        if self.duration_us != _duration_us(self.sample_count):
            raise ValueError("duration_us does not match the exact sample count")
        if self.quality_state is QualityState.NOT_AVAILABLE:
            raise ValueError("result requires an explicit quality state")
        if self.quality_state in {QualityState.PASS, QualityState.FAIL, QualityState.UNKNOWN}:
            _sha(self.quality_receipt_sha256, "quality_receipt_sha256")
        elif self.quality_receipt_sha256 is not None:
            raise ValueError("PENDING quality cannot claim a terminal receipt")
        if self.owner_listening_state in {OwnerListeningState.ACCEPTED, OwnerListeningState.REJECTED}:
            _sha(self.owner_listening_receipt_sha256, "owner_listening_receipt_sha256")
        elif self.owner_listening_receipt_sha256 is not None:
            raise ValueError("nonterminal listening state cannot claim a receipt")
        if self.owner_listening_state is OwnerListeningState.ACCEPTED and self.quality_state is not QualityState.PASS:
            raise ValueError("Owner acceptance requires quality PASS")

    def _validate_adoption(self) -> None:
        reviewed_and_accepted = (
            self.quality_state is QualityState.PASS
            and self.owner_listening_state is OwnerListeningState.ACCEPTED
        )
        terminal_review = (
            self.quality_state in {QualityState.PASS, QualityState.FAIL}
            and self.owner_listening_state
            in {OwnerListeningState.ACCEPTED, OwnerListeningState.REJECTED}
        )
        positive_profile_states = {
            ProfileAdoptionState.SAVE_DECISION_REQUIRED,
            ProfileAdoptionState.SAVED_LOCAL_CANDIDATE,
            ProfileAdoptionState.STALE,
            ProfileAdoptionState.REVOKED,
        }
        positive_asset_states = {
            PreviewAssetAdoptionState.PUBLISH_DECISION_REQUIRED,
            PreviewAssetAdoptionState.ASSET_PUBLISHED_RESTRICTED,
            PreviewAssetAdoptionState.STALE,
            PreviewAssetAdoptionState.REVOKED,
        }
        if (
            self.profile_adoption_state in positive_profile_states
            or self.preview_asset_adoption_state in positive_asset_states
        ) and not reviewed_and_accepted:
            raise ValueError("positive adoption requires QA PASS and Owner acceptance")
        if (
            self.profile_adoption_state is ProfileAdoptionState.PROFILE_NOT_SAVED
            or self.preview_asset_adoption_state
            is PreviewAssetAdoptionState.ASSET_NOT_PUBLISHED
        ) and not terminal_review:
            raise ValueError("negative adoption requires a terminal review")
        if self.profile_adoption_state is ProfileAdoptionState.SAVED_LOCAL_CANDIDATE:
            if self.reference_retention_state is not ReferenceRetentionState.RETAIN_PRIVATE_REFERENCE:
                raise ValueError("saving a reusable local profile requires reference retention")
            _sha(self.saved_profile_revision_sha256, "saved_profile_revision_sha256")
            _sha(self.profile_adoption_receipt_sha256, "profile_adoption_receipt_sha256")
        elif self.profile_adoption_state is ProfileAdoptionState.PROFILE_NOT_SAVED:
            if self.saved_profile_revision_sha256 is not None:
                raise ValueError("PROFILE_NOT_SAVED cannot bind a saved profile")
            _sha(self.profile_adoption_receipt_sha256, "profile_adoption_receipt_sha256")
        elif self.profile_adoption_state in {ProfileAdoptionState.STALE, ProfileAdoptionState.REVOKED}:
            _sha(self.saved_profile_revision_sha256, "saved_profile_revision_sha256")
            _sha(self.profile_adoption_receipt_sha256, "profile_adoption_receipt_sha256")
            expected_retention = (
                ReferenceRetentionState.EXPIRED
                if self.profile_adoption_state is ProfileAdoptionState.STALE
                else ReferenceRetentionState.RETENTION_REVOKED
            )
            if self.reference_retention_state is not expected_retention:
                raise ValueError("profile currentness does not match reference retention")
        elif self.saved_profile_revision_sha256 is not None or self.profile_adoption_receipt_sha256 is not None:
            raise ValueError("profile coordinates require a terminal profile decision")
        if self.profile_adoption_state in {
            ProfileAdoptionState.STALE,
            ProfileAdoptionState.REVOKED,
        }:
            _sha(
                self.profile_currentness_receipt_sha256,
                "profile_currentness_receipt_sha256",
            )
        elif self.profile_currentness_receipt_sha256 is not None:
            raise ValueError("profile currentness receipt requires STALE or REVOKED")
        if self.preview_asset_adoption_state is PreviewAssetAdoptionState.ASSET_PUBLISHED_RESTRICTED:
            _logical_id(self.preview_asset_ref, "preview_asset_ref")
            _sha(self.preview_asset_sha256, "preview_asset_sha256")
            _sha(self.asset_adoption_receipt_sha256, "asset_adoption_receipt_sha256")
        elif self.preview_asset_adoption_state in {
            PreviewAssetAdoptionState.ASSET_NOT_PUBLISHED,
            PreviewAssetAdoptionState.STALE,
            PreviewAssetAdoptionState.REVOKED,
        }:
            if self.preview_asset_adoption_state is PreviewAssetAdoptionState.ASSET_NOT_PUBLISHED and (
                self.preview_asset_ref is not None or self.preview_asset_sha256 is not None
            ):
                raise ValueError("ASSET_NOT_PUBLISHED cannot bind an Asset")
            if self.preview_asset_adoption_state in {
                PreviewAssetAdoptionState.STALE,
                PreviewAssetAdoptionState.REVOKED,
            }:
                _logical_id(self.preview_asset_ref, "preview_asset_ref")
                _sha(self.preview_asset_sha256, "preview_asset_sha256")
            _sha(self.asset_adoption_receipt_sha256, "asset_adoption_receipt_sha256")
        elif any(
            value is not None
            for value in (self.preview_asset_ref, self.preview_asset_sha256, self.asset_adoption_receipt_sha256)
        ):
            raise ValueError("Asset coordinates require a terminal Asset decision")
        if self.preview_asset_adoption_state in {
            PreviewAssetAdoptionState.STALE,
            PreviewAssetAdoptionState.REVOKED,
        }:
            _sha(
                self.preview_asset_currentness_receipt_sha256,
                "preview_asset_currentness_receipt_sha256",
            )
        elif self.preview_asset_currentness_receipt_sha256 is not None:
            raise ValueError("Asset currentness receipt requires STALE or REVOKED")
        if self.reference_retention_state is ReferenceRetentionState.UNDECIDED:
            if self.reference_retention_decision_sha256 is not None:
                raise ValueError("UNDECIDED retention cannot claim a decision receipt")
        else:
            _sha(self.reference_retention_decision_sha256, "reference_retention_decision_sha256")
        if self.reference_retention_state in {
            ReferenceRetentionState.RETENTION_REVOKED,
            ReferenceRetentionState.EXPIRED,
        }:
            _sha(
                self.reference_retention_currentness_receipt_sha256,
                "reference_retention_currentness_receipt_sha256",
            )
        elif self.reference_retention_currentness_receipt_sha256 is not None:
            raise ValueError("retention currentness receipt requires revocation or expiry")
        if (
            self.reference_retention_state is ReferenceRetentionState.DO_NOT_RETAIN_PRIVATE_REFERENCE
            and self.profile_adoption_state is ProfileAdoptionState.SAVED_LOCAL_CANDIDATE
        ):
            raise ValueError("non-retained reference cannot produce a reusable profile")

    def _body(self) -> dict[str, Any]:
        has_result = self.result_receipt_sha256 is not None
        return {
            "schema_id": SCHEMA_ID,
            "contract_version": CONTRACT_VERSION,
            "record_type": "QuickCloneFlowRevision",
            "task_owner": "TASK-046",
            "task014_result_admission_producer_state": (
                self._task014_result_admission_producer_state()
            ),
            "flow_id": self.flow_id,
            "revision": self.revision,
            "parent_revision_sha256": self.parent_revision_sha256,
            "created_at": self.created_at,
            "route": "ZERO_SHOT",
            "mode": "PREVIEW",
            "intended_artifact": INTENDED_ARTIFACT,
            "source_kind": self.source_kind.value,
            "setup_state": self.setup_state.value,
            "execution_state": self.execution_state.value,
            "quality_state": self.quality_state.value,
            "owner_listening_state": self.owner_listening_state.value,
            "profile_adoption_state": self.profile_adoption_state.value,
            "preview_asset_adoption_state": self.preview_asset_adoption_state.value,
            "reference_retention_state": self.reference_retention_state.value,
            "compute_preference": self.compute_preference.value,
            "compute_resolution_state": self.compute_resolution_state.value,
            "model_execution_policy": self.model_execution_policy.value,
            "runtime_aggregate_state": self.runtime_aggregate_state.value,
            "result_admission_state": self.result_admission_state.value,
            "source_binding_sha256": self.source_binding_sha256,
            "consent_binding_sha256": self.consent_binding_sha256,
            "reference_transcript_sha256": self.reference_transcript_sha256,
            "preview_text_sha256": self.preview_text_sha256,
            "preview_text_code_points": self.preview_text_code_points,
            "preview_profile_revision_sha256": self.preview_profile_revision_sha256,
            "model_selection_binding_sha256": self.model_selection_binding_sha256,
            "runtime_aggregate_binding_sha256": self.runtime_aggregate_binding_sha256,
            "preflight_sha256": self.preflight_sha256,
            "one_shot_authorization_sha256": self.one_shot_authorization_sha256,
            "durable_job_sha256": self.durable_job_sha256,
            "render_operation_identity_sha256": self.render_operation_identity_sha256,
            "result_receipt_sha256": self.result_receipt_sha256,
            "result_admission_receipt_sha256": self.result_admission_receipt_sha256,
            "result_render_operation_identity_sha256": (
                self.result_render_operation_identity_sha256
            ),
            "result_preview_profile_revision_sha256": (
                self.result_preview_profile_revision_sha256
            ),
            "result_model_selection_binding_sha256": (
                self.result_model_selection_binding_sha256
            ),
            "result_runtime_aggregate_binding_sha256": (
                self.result_runtime_aggregate_binding_sha256
            ),
            "result_output_sha256": self.result_output_sha256,
            "result_route": self.result_route,
            "result_replay": self.result_replay,
            "quality_receipt_sha256": self.quality_receipt_sha256,
            "owner_listening_receipt_sha256": self.owner_listening_receipt_sha256,
            "staged_wav_ref": self.staged_wav_ref,
            "staged_wav_sha256": self.staged_wav_sha256,
            "sample_rate_hz": SAMPLE_RATE_HZ if has_result else None,
            "channels": CHANNELS if has_result else None,
            "sample_format": SAMPLE_FORMAT if has_result else None,
            "sample_count": self.sample_count,
            "duration_us": self.duration_us,
            "saved_profile_revision_sha256": self.saved_profile_revision_sha256,
            "profile_adoption_receipt_sha256": self.profile_adoption_receipt_sha256,
            "profile_currentness_receipt_sha256": (
                self.profile_currentness_receipt_sha256
            ),
            "preview_asset_ref": self.preview_asset_ref,
            "preview_asset_sha256": self.preview_asset_sha256,
            "asset_adoption_receipt_sha256": self.asset_adoption_receipt_sha256,
            "preview_asset_currentness_receipt_sha256": (
                self.preview_asset_currentness_receipt_sha256
            ),
            "reference_retention_decision_sha256": self.reference_retention_decision_sha256,
            "reference_retention_currentness_receipt_sha256": (
                self.reference_retention_currentness_receipt_sha256
            ),
            "reconciliation_receipt_sha256": self.reconciliation_receipt_sha256,
            "reason_codes": list(self.reason_codes),
            "private_body_embedded": False,
            "host_path_persisted": False,
            "secret_persisted": False,
            "effect_authorized": False,
            "automatic_retry_authorized": False,
            "physical_delete_authorized": False,
        }

    @property
    def flow_revision_sha256(self) -> str:
        return sha256_bytes(canonical_json_bytes(self._body()))

    def to_dict(self) -> dict[str, Any]:
        body = self._body()
        body["flow_revision_sha256"] = self.flow_revision_sha256
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "QuickCloneFlowRevision":
        return cls._from_dict_for_producer_state(
            value,
            expected_producer_state="NOT_BOUND",
        )

    @classmethod
    def _from_dict_for_producer_state(
        cls,
        value: Mapping[str, Any],
        *,
        expected_producer_state: str,
    ) -> "QuickCloneFlowRevision":
        expected = set(cls._record_fields())
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("QuickCloneFlowRevision fields are incomplete or unknown")
        if (
            value["schema_id"] != SCHEMA_ID
            or value["contract_version"] != CONTRACT_VERSION
            or value["record_type"] != "QuickCloneFlowRevision"
            or value["task_owner"] != "TASK-046"
            or value["task014_result_admission_producer_state"]
            != expected_producer_state
            or value["route"] != "ZERO_SHOT"
            or value["mode"] != "PREVIEW"
            or value["intended_artifact"] != INTENDED_ARTIFACT
        ):
            raise ValueError("QuickCloneFlowRevision identity is invalid")
        for field in (
            "private_body_embedded",
            "host_path_persisted",
            "secret_persisted",
            "effect_authorized",
            "automatic_retry_authorized",
            "physical_delete_authorized",
        ):
            if value[field] is not False:
                raise ValueError("QuickCloneFlowRevision violates the no-effect boundary")
        has_result = value["result_receipt_sha256"] is not None
        expected_format = (
            (SAMPLE_RATE_HZ, CHANNELS, SAMPLE_FORMAT)
            if has_result
            else (None, None, None)
        )
        if (value["sample_rate_hz"], value["channels"], value["sample_format"]) != expected_format:
            raise ValueError("staged WAV format is invalid")
        revision = cls(
            flow_id=value["flow_id"],
            revision=value["revision"],
            parent_revision_sha256=value["parent_revision_sha256"],
            created_at=value["created_at"],
            source_kind=SourceKind(value["source_kind"]),
            setup_state=SetupState(value["setup_state"]),
            execution_state=ExecutionState(value["execution_state"]),
            quality_state=QualityState(value["quality_state"]),
            owner_listening_state=OwnerListeningState(value["owner_listening_state"]),
            profile_adoption_state=ProfileAdoptionState(value["profile_adoption_state"]),
            preview_asset_adoption_state=PreviewAssetAdoptionState(value["preview_asset_adoption_state"]),
            reference_retention_state=ReferenceRetentionState(value["reference_retention_state"]),
            compute_preference=ComputePreference(value["compute_preference"]),
            compute_resolution_state=ComputeResolutionState(value["compute_resolution_state"]),
            model_execution_policy=ModelExecutionPolicy(value["model_execution_policy"]),
            runtime_aggregate_state=RuntimeAggregateState(value["runtime_aggregate_state"]),
            result_admission_state=ResultAdmissionState(value["result_admission_state"]),
            source_binding_sha256=value["source_binding_sha256"],
            consent_binding_sha256=value["consent_binding_sha256"],
            reference_transcript_sha256=value["reference_transcript_sha256"],
            preview_text_sha256=value["preview_text_sha256"],
            preview_text_code_points=value["preview_text_code_points"],
            preview_profile_revision_sha256=value["preview_profile_revision_sha256"],
            model_selection_binding_sha256=value["model_selection_binding_sha256"],
            runtime_aggregate_binding_sha256=value["runtime_aggregate_binding_sha256"],
            preflight_sha256=value["preflight_sha256"],
            one_shot_authorization_sha256=value["one_shot_authorization_sha256"],
            durable_job_sha256=value["durable_job_sha256"],
            render_operation_identity_sha256=value["render_operation_identity_sha256"],
            result_receipt_sha256=value["result_receipt_sha256"],
            result_admission_receipt_sha256=value["result_admission_receipt_sha256"],
            result_render_operation_identity_sha256=value[
                "result_render_operation_identity_sha256"
            ],
            result_preview_profile_revision_sha256=value[
                "result_preview_profile_revision_sha256"
            ],
            result_model_selection_binding_sha256=value[
                "result_model_selection_binding_sha256"
            ],
            result_runtime_aggregate_binding_sha256=value[
                "result_runtime_aggregate_binding_sha256"
            ],
            result_output_sha256=value["result_output_sha256"],
            result_route=value["result_route"],
            result_replay=value["result_replay"],
            quality_receipt_sha256=value["quality_receipt_sha256"],
            owner_listening_receipt_sha256=value["owner_listening_receipt_sha256"],
            staged_wav_ref=value["staged_wav_ref"],
            staged_wav_sha256=value["staged_wav_sha256"],
            sample_count=value["sample_count"],
            duration_us=value["duration_us"],
            saved_profile_revision_sha256=value["saved_profile_revision_sha256"],
            profile_adoption_receipt_sha256=value["profile_adoption_receipt_sha256"],
            profile_currentness_receipt_sha256=value[
                "profile_currentness_receipt_sha256"
            ],
            preview_asset_ref=value["preview_asset_ref"],
            preview_asset_sha256=value["preview_asset_sha256"],
            asset_adoption_receipt_sha256=value["asset_adoption_receipt_sha256"],
            preview_asset_currentness_receipt_sha256=value[
                "preview_asset_currentness_receipt_sha256"
            ],
            reference_retention_decision_sha256=value["reference_retention_decision_sha256"],
            reference_retention_currentness_receipt_sha256=value[
                "reference_retention_currentness_receipt_sha256"
            ],
            reconciliation_receipt_sha256=value["reconciliation_receipt_sha256"],
            reason_codes=tuple(value["reason_codes"]),
        )
        if value["flow_revision_sha256"] != revision.flow_revision_sha256:
            raise ValueError("flow_revision_sha256 mismatch")
        return revision

    @staticmethod
    def _record_fields() -> tuple[str, ...]:
        return (
            "schema_id", "contract_version", "record_type", "task_owner",
            "task014_result_admission_producer_state", "flow_id",
            "revision", "parent_revision_sha256", "created_at", "route", "mode",
            "intended_artifact", "source_kind", "setup_state", "execution_state",
            "quality_state", "owner_listening_state", "profile_adoption_state",
            "preview_asset_adoption_state", "reference_retention_state",
            "compute_preference", "compute_resolution_state", "model_execution_policy",
            "runtime_aggregate_state", "result_admission_state", "source_binding_sha256",
            "consent_binding_sha256",
            "reference_transcript_sha256", "preview_text_sha256", "preview_text_code_points",
            "preview_profile_revision_sha256", "model_selection_binding_sha256",
            "runtime_aggregate_binding_sha256",
            "preflight_sha256", "one_shot_authorization_sha256", "durable_job_sha256",
            "render_operation_identity_sha256", "result_receipt_sha256",
            "result_admission_receipt_sha256", "result_render_operation_identity_sha256",
            "result_preview_profile_revision_sha256", "result_model_selection_binding_sha256",
            "result_runtime_aggregate_binding_sha256", "result_output_sha256",
            "result_route", "result_replay", "quality_receipt_sha256",
            "owner_listening_receipt_sha256", "staged_wav_ref", "staged_wav_sha256",
            "sample_rate_hz", "channels", "sample_format", "sample_count", "duration_us",
            "saved_profile_revision_sha256", "profile_adoption_receipt_sha256",
            "profile_currentness_receipt_sha256",
            "preview_asset_ref", "preview_asset_sha256", "asset_adoption_receipt_sha256",
            "preview_asset_currentness_receipt_sha256",
            "reference_retention_decision_sha256",
            "reference_retention_currentness_receipt_sha256",
            "reconciliation_receipt_sha256",
            "reason_codes", "private_body_embedded", "host_path_persisted",
            "secret_persisted", "effect_authorized", "automatic_retry_authorized",
            "physical_delete_authorized", "flow_revision_sha256",
        )


@dataclass(frozen=True, slots=True)
class QuickCloneFutureSemanticFixture(QuickCloneFlowRevision):
    """Fixture-only future-state vector; never a Product/readback projection."""

    def _task014_result_admission_producer_state(self) -> str:
        return "BOUND_VERIFIED"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "QuickCloneFutureSemanticFixture":
        raise ValueError("future semantic fixtures require explicit fixture ingress")

    @classmethod
    def from_fixture_dict(
        cls,
        value: Mapping[str, Any],
    ) -> "QuickCloneFutureSemanticFixture":
        return cls._from_dict_for_producer_state(
            value,
            expected_producer_state="BOUND_VERIFIED",
        )


def validate_flow_transition(
    previous: Mapping[str, Any] | QuickCloneFlowRevision,
    current: Mapping[str, Any] | QuickCloneFlowRevision,
) -> None:
    old = previous if isinstance(previous, QuickCloneFlowRevision) else QuickCloneFlowRevision.from_dict(previous)
    new = current if isinstance(current, QuickCloneFlowRevision) else QuickCloneFlowRevision.from_dict(current)
    if type(old) is not type(new) or type(old) not in {
        QuickCloneFlowRevision,
        QuickCloneFutureSemanticFixture,
    }:
        raise ValueError("production and fixture revision types cannot cross")
    if new.flow_id != old.flow_id or new.revision != old.revision + 1:
        raise ValueError("flow revision identity/sequence mismatch")
    if new.parent_revision_sha256 != old.flow_revision_sha256:
        raise ValueError("flow parent CAS mismatch")
    if datetime.fromisoformat(new.created_at[:-1] + "+00:00") < datetime.fromisoformat(
        old.created_at[:-1] + "+00:00"
    ):
        raise ValueError("flow revision created_at cannot move backwards")
    immutable = (
        "source_kind",
        "source_binding_sha256",
        "consent_binding_sha256",
        "reference_transcript_sha256",
        "preview_text_sha256",
        "preview_text_code_points",
        "preview_profile_revision_sha256",
        "model_selection_binding_sha256",
        "compute_preference",
        "model_execution_policy",
    )
    if any(getattr(new, field) != getattr(old, field) for field in immutable):
        raise ValueError("Quick Clone immutable input binding changed")
    if new.execution_state not in _TRANSITIONS[old.execution_state]:
        raise ValueError(
            f"invalid Quick Clone transition {old.execution_state.value}->{new.execution_state.value}"
        )
    state_transitions = (
        (_QUALITY_TRANSITIONS, old.quality_state, new.quality_state, "quality_state"),
        (
            _LISTENING_TRANSITIONS,
            old.owner_listening_state,
            new.owner_listening_state,
            "owner_listening_state",
        ),
        (
            _PROFILE_ADOPTION_TRANSITIONS,
            old.profile_adoption_state,
            new.profile_adoption_state,
            "profile_adoption_state",
        ),
        (
            _ASSET_ADOPTION_TRANSITIONS,
            old.preview_asset_adoption_state,
            new.preview_asset_adoption_state,
            "preview_asset_adoption_state",
        ),
        (
            _RETENTION_TRANSITIONS,
            old.reference_retention_state,
            new.reference_retention_state,
            "reference_retention_state",
        ),
        (
            _RESULT_ADMISSION_TRANSITIONS,
            old.result_admission_state,
            new.result_admission_state,
            "result_admission_state",
        ),
    )
    for transition_map, old_state, new_state, field in state_transitions:
        if new_state not in transition_map[old_state]:
            raise ValueError(f"{field} cannot rewind or cross a terminal decision")
    if old.preflight_sha256 is not None and (
        new.compute_resolution_state != old.compute_resolution_state
        or new.runtime_aggregate_state != old.runtime_aggregate_state
    ):
        raise ValueError("admitted compute/runtime state cannot change after preflight")
    bound_once = (
        "runtime_aggregate_binding_sha256",
        "preflight_sha256",
        "one_shot_authorization_sha256",
        "durable_job_sha256",
        "render_operation_identity_sha256",
        "result_receipt_sha256",
        "result_admission_receipt_sha256",
        "result_render_operation_identity_sha256",
        "result_preview_profile_revision_sha256",
        "result_model_selection_binding_sha256",
        "result_runtime_aggregate_binding_sha256",
        "result_output_sha256",
        "result_route",
        "result_replay",
        "quality_receipt_sha256",
        "owner_listening_receipt_sha256",
        "staged_wav_ref",
        "staged_wav_sha256",
        "sample_count",
        "duration_us",
        "saved_profile_revision_sha256",
        "profile_adoption_receipt_sha256",
        "profile_currentness_receipt_sha256",
        "preview_asset_ref",
        "preview_asset_sha256",
        "asset_adoption_receipt_sha256",
        "preview_asset_currentness_receipt_sha256",
        "reference_retention_decision_sha256",
        "reference_retention_currentness_receipt_sha256",
        "reconciliation_receipt_sha256",
    )
    for field in bound_once:
        old_value = getattr(old, field)
        if old_value is not None and getattr(new, field) != old_value:
            raise ValueError(f"{field} cannot change once bound")
    closes_unknown = (
        old.execution_state is ExecutionState.UNKNOWN
        and new.execution_state
        in {ExecutionState.READY_FOR_QA_REVIEW, ExecutionState.FAILED_KNOWN}
    )
    introduces_reconciliation = (
        old.reconciliation_receipt_sha256 is None
        and new.reconciliation_receipt_sha256 is not None
    )
    if closes_unknown and not introduces_reconciliation:
        raise ValueError("UNKNOWN reconciliation requires an exact receipt")
    if introduces_reconciliation and not closes_unknown:
        raise ValueError("reconciliation receipt may only close UNKNOWN")


def public_projection(value: Mapping[str, Any] | QuickCloneFlowRevision) -> dict[str, Any]:
    revision = value if isinstance(value, QuickCloneFlowRevision) else QuickCloneFlowRevision.from_dict(value)
    if type(revision) is not QuickCloneFlowRevision:
        raise ValueError("fixture-only revisions cannot produce a Product projection")
    has_result = revision.result_receipt_sha256 is not None
    return {
        "record_type": "QuickClonePublicProjection",
        "contract_version": CONTRACT_VERSION,
        "flow_id": revision.flow_id,
        "revision": revision.revision,
        "task014_result_admission_producer_state": "NOT_BOUND",
        "route": "ZERO_SHOT",
        "mode": "PREVIEW",
        "setup_state": revision.setup_state.value,
        "execution_state": revision.execution_state.value,
        "quality_state": revision.quality_state.value,
        "owner_listening_state": revision.owner_listening_state.value,
        "profile_adoption_state": revision.profile_adoption_state.value,
        "preview_asset_adoption_state": revision.preview_asset_adoption_state.value,
        "reference_retention_state": revision.reference_retention_state.value,
        "compute_preference": revision.compute_preference.value,
        "compute_resolution_state": revision.compute_resolution_state.value,
        "runtime_aggregate_state": revision.runtime_aggregate_state.value,
        "result_admission_state": revision.result_admission_state.value,
        "preview_text_code_points": revision.preview_text_code_points,
        "has_staged_preview": has_result,
        "result_binding_verified": (
            revision.result_admission_state is ResultAdmissionState.BOUND_VERIFIED
        ),
        "sample_rate_hz": SAMPLE_RATE_HZ if has_result else None,
        "channels": CHANNELS if has_result else None,
        "sample_format": SAMPLE_FORMAT if has_result else None,
        "sample_count": revision.sample_count,
        "duration_us": revision.duration_us,
        "reason_codes": list(revision.reason_codes),
        "can_confirm_one_shot": revision.execution_state is ExecutionState.READY_FOR_CONFIRMATION,
        "preview_ready_for_external_playback": has_result,
        "can_save_profile": (
            revision.profile_adoption_state is ProfileAdoptionState.SAVE_DECISION_REQUIRED
            and revision.reference_retention_state is ReferenceRetentionState.RETAIN_PRIVATE_REFERENCE
        ),
        "can_publish_preview_asset": (
            revision.preview_asset_adoption_state
            is PreviewAssetAdoptionState.PUBLISH_DECISION_REQUIRED
        ),
        "profile_save_and_asset_publish_are_independent": True,
        "no_save_implies_physical_delete": False,
        "effect_authorized": False,
        "automatic_retry_authorized": False,
        "audio_body_included": False,
        "text_body_included": False,
        "host_path_included": False,
    }


def assert_no_effect_surface() -> None:
    forbidden = {
        "os", "pathlib", "subprocess", "socket", "requests", "torch",
        "transformers", "soundfile", "wave",
    }
    if forbidden & set(globals()):
        raise AssertionError("effectful runtime surface detected")
