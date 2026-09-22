"""Pure TASK-098 A4-R2a media-runtime request and observation reducer.

This module defines an injected Port shape but never invokes it. It accepts no
path, opens no media, allocates no audio device, and creates no canonical
TASK-041 receipt or review-completion claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Protocol

from .audio_workspace_media_review import (
    AudioMediaReviewIntent,
    AudioMediaReviewPolicyRevision,
    AudioMediaSourceBinding,
    PlaybackWaveformCapabilityBinding,
    classify_review_admission,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .task098_review_workspace_contract import (
    MAX_DURATION_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
)
from .task098_review_workspace_coordinator import ReviewWorkspaceViewModel


MAX_WAVEFORM_POINT_COUNT = 100_000
_OPERATION_ORDER = ("AUDITION", "WAVEFORM_VIEW")
_REASON_CODES = frozenset(
    {
        "AUDITION_NOT_OBSERVED",
        "CANCELLED_BY_RUNTIME",
        "PORT_NOT_BOUND",
        "REQUEST_IDENTITY_MISMATCH",
        "RUNTIME_DISCONNECTED",
        "RUNTIME_FAILED",
        "UNREQUESTED_AUDITION_OBSERVED",
        "UNREQUESTED_WAVEFORM_OBSERVED",
        "WAVEFORM_NOT_OBSERVED",
    }
)


class ReviewMediaRuntimeState(str, Enum):
    NOT_BOUND = "NOT_BOUND"
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED_KNOWN = "FAILED_KNOWN"
    CANCELLED_SAFE = "CANCELLED_SAFE"
    UNKNOWN_AFTER_DISCONNECT = "UNKNOWN_AFTER_DISCONNECT"


def _integer(value: Any, name: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} is outside the supported range")
    return value


def _reasons(value: tuple[str, ...]) -> None:
    if (
        not isinstance(value, tuple)
        or tuple(sorted(set(value))) != value
        or any(code not in _REASON_CODES for code in value)
    ):
        raise ValueError("reason_codes must be closed, unique, and ordered")


@dataclass(frozen=True, slots=True)
class ReviewMediaRuntimeRequest:
    policy_sha256: str
    source_binding_sha256: str
    source_asset_id: str
    capability_binding_sha256: str
    intent_sha256: str
    requested_operations: tuple[str, ...]
    sample_rate_hz: int
    source_duration_samples: int
    range_start_sample: int
    range_end_sample_exclusive: int
    request_sha256: str

    def __post_init__(self) -> None:
        for name, value in (
            ("policy_sha256", self.policy_sha256),
            ("source_binding_sha256", self.source_binding_sha256),
            ("capability_binding_sha256", self.capability_binding_sha256),
            ("intent_sha256", self.intent_sha256),
            ("request_sha256", self.request_sha256),
        ):
            validate_sha256(value, field_name=name)
        if not isinstance(self.source_asset_id, str) or not self.source_asset_id:
            raise ValueError("source_asset_id is invalid")
        if (
            not isinstance(self.requested_operations, tuple)
            or self.requested_operations
            != tuple(item for item in _OPERATION_ORDER if item in self.requested_operations)
            or not self.requested_operations
        ):
            raise ValueError("requested_operations are invalid")
        if self.sample_rate_hz != REQUIRED_SAMPLE_RATE_HZ:
            raise ValueError("sample_rate_hz must remain 48000")
        duration = _integer(
            self.source_duration_samples,
            "source_duration_samples",
            minimum=1,
            maximum=MAX_DURATION_SAMPLES,
        )
        start = _integer(
            self.range_start_sample,
            "range_start_sample",
            minimum=0,
            maximum=duration - 1,
        )
        end = _integer(
            self.range_end_sample_exclusive,
            "range_end_sample_exclusive",
            minimum=1,
            maximum=duration,
        )
        if end <= start:
            raise ValueError("runtime range must be non-empty and half-open")
        body = {
            "policy_sha256": self.policy_sha256,
            "source_binding_sha256": self.source_binding_sha256,
            "source_asset_id": self.source_asset_id,
            "capability_binding_sha256": self.capability_binding_sha256,
            "intent_sha256": self.intent_sha256,
            "requested_operations": list(self.requested_operations),
            "sample_rate_hz": self.sample_rate_hz,
            "source_duration_samples": self.source_duration_samples,
            "range_start_sample": self.range_start_sample,
            "range_end_sample_exclusive": self.range_end_sample_exclusive,
        }
        if self.request_sha256 != sha256_bytes(canonical_json_bytes(body)):
            raise ValueError("request_sha256 does not match the request")


class ReviewMediaRuntimePort(Protocol):
    """A4-R2b implementation point; A4-R2a never invokes this protocol."""

    def execute(
        self, request: ReviewMediaRuntimeRequest
    ) -> "ReviewMediaRuntimeObservation": ...


@dataclass(frozen=True, slots=True)
class ReviewMediaRuntimeObservation:
    request_sha256: str
    state: ReviewMediaRuntimeState
    runtime_connected: bool
    playback_observed: bool
    waveform_observed: bool
    waveform_point_count: int | None
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        validate_sha256(self.request_sha256, field_name="request_sha256")
        if not isinstance(self.state, ReviewMediaRuntimeState):
            raise ValueError("state is invalid")
        if any(
            type(value) is not bool
            for value in (
                self.runtime_connected,
                self.playback_observed,
                self.waveform_observed,
            )
        ):
            raise ValueError("runtime observation flags must be booleans")
        _reasons(self.reason_codes)
        if self.waveform_observed:
            _integer(
                self.waveform_point_count,
                "waveform_point_count",
                minimum=1,
                maximum=MAX_WAVEFORM_POINT_COUNT,
            )
        elif self.waveform_point_count is not None:
            raise ValueError("waveform metadata requires waveform observation")

        if self.state is ReviewMediaRuntimeState.READY:
            if not self.runtime_connected or self.playback_observed or self.waveform_observed or self.reason_codes:
                raise ValueError("READY observation is inconsistent")
        elif self.state is ReviewMediaRuntimeState.RUNNING:
            if not self.runtime_connected or self.reason_codes:
                raise ValueError("RUNNING observation is inconsistent")
        elif self.state is ReviewMediaRuntimeState.SUCCEEDED:
            if not self.runtime_connected or self.reason_codes:
                raise ValueError("SUCCEEDED observation is inconsistent")
        elif self.state is ReviewMediaRuntimeState.FAILED_KNOWN:
            if (
                not self.runtime_connected
                or self.playback_observed
                or self.waveform_observed
                or self.reason_codes != ("RUNTIME_FAILED",)
            ):
                raise ValueError("FAILED_KNOWN observation is inconsistent")
        elif self.state is ReviewMediaRuntimeState.CANCELLED_SAFE:
            if (
                not self.runtime_connected
                or self.playback_observed
                or self.waveform_observed
                or self.reason_codes != ("CANCELLED_BY_RUNTIME",)
            ):
                raise ValueError("CANCELLED_SAFE observation is inconsistent")
        elif self.state is ReviewMediaRuntimeState.UNKNOWN_AFTER_DISCONNECT:
            if (
                self.runtime_connected
                or self.playback_observed
                or self.waveform_observed
                or self.reason_codes != ("RUNTIME_DISCONNECTED",)
            ):
                raise ValueError("UNKNOWN_AFTER_DISCONNECT observation is inconsistent")
        else:
            raise ValueError("NOT_BOUND is coordinator-only")


@dataclass(frozen=True, slots=True)
class ReviewMediaRuntimeStatus:
    state: ReviewMediaRuntimeState
    audition_requested: bool
    waveform_requested: bool
    playback_observed: bool
    waveform_observed: bool
    waveform_point_count: int | None
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.state, ReviewMediaRuntimeState):
            raise ValueError("state is invalid")
        if any(
            type(value) is not bool
            for value in (
                self.audition_requested,
                self.waveform_requested,
                self.playback_observed,
                self.waveform_observed,
            )
        ):
            raise ValueError("runtime status flags must be booleans")
        _reasons(self.reason_codes)
        if self.waveform_observed:
            _integer(
                self.waveform_point_count,
                "waveform_point_count",
                minimum=1,
                maximum=MAX_WAVEFORM_POINT_COUNT,
            )
        elif self.waveform_point_count is not None:
            raise ValueError("waveform metadata requires waveform observation")
        if self.state is ReviewMediaRuntimeState.NOT_BOUND:
            if self.reason_codes != ("PORT_NOT_BOUND",) or self.playback_observed or self.waveform_observed:
                raise ValueError("NOT_BOUND status is inconsistent")
        elif self.state is ReviewMediaRuntimeState.READY:
            if self.reason_codes or self.playback_observed or self.waveform_observed:
                raise ValueError("READY status is inconsistent")
        elif self.state is ReviewMediaRuntimeState.RUNNING:
            if (
                self.reason_codes
                or (self.playback_observed and not self.audition_requested)
                or (self.waveform_observed and not self.waveform_requested)
            ):
                raise ValueError("RUNNING status is inconsistent")
        elif self.state is ReviewMediaRuntimeState.SUCCEEDED:
            if (
                self.reason_codes
                or self.playback_observed is not self.audition_requested
                or self.waveform_observed is not self.waveform_requested
            ):
                raise ValueError("SUCCEEDED status is inconsistent")
        elif self.state is ReviewMediaRuntimeState.FAILED_KNOWN:
            invalid = {
                "PORT_NOT_BOUND",
                "CANCELLED_BY_RUNTIME",
                "RUNTIME_DISCONNECTED",
            }
            if (
                not self.reason_codes
                or invalid.intersection(self.reason_codes)
                or self.playback_observed
                or self.waveform_observed
            ):
                raise ValueError("FAILED_KNOWN status is inconsistent")
        elif self.state is ReviewMediaRuntimeState.CANCELLED_SAFE:
            if (
                self.reason_codes != ("CANCELLED_BY_RUNTIME",)
                or self.playback_observed
                or self.waveform_observed
            ):
                raise ValueError("CANCELLED_SAFE status is inconsistent")
        elif self.state is ReviewMediaRuntimeState.UNKNOWN_AFTER_DISCONNECT:
            if (
                self.reason_codes != ("RUNTIME_DISCONNECTED",)
                or self.playback_observed
                or self.waveform_observed
            ):
                raise ValueError("UNKNOWN_AFTER_DISCONNECT status is inconsistent")

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "projection_version": "1.0.0",
            "task_owner": "TASK-098",
            "runtime_state": self.state.value,
            "audition_requested": self.audition_requested,
            "waveform_requested": self.waveform_requested,
            "playback_observed": self.playback_observed,
            "waveform_observed": self.waveform_observed,
            "waveform_point_count": self.waveform_point_count,
            "reason_codes": list(self.reason_codes),
            "canonical_receipt_created": False,
            "review_completion_claimed": False,
            "review_state_persisted": False,
            "human_decision_authorized": False,
            "media_mutation_started": False,
        }


def build_review_media_runtime_request(
    *,
    policy: AudioMediaReviewPolicyRevision,
    source: AudioMediaSourceBinding,
    capability: PlaybackWaveformCapabilityBinding,
    intent: AudioMediaReviewIntent,
    view_model: ReviewWorkspaceViewModel,
    evaluated_at: str,
) -> ReviewMediaRuntimeRequest:
    if (
        type(policy) is not AudioMediaReviewPolicyRevision
        or type(source) is not AudioMediaSourceBinding
        or type(capability) is not PlaybackWaveformCapabilityBinding
        or type(intent) is not AudioMediaReviewIntent
        or type(view_model) is not ReviewWorkspaceViewModel
    ):
        raise ValueError("runtime request inputs are invalid")
    source_data = source.to_dict()
    capability_data = capability.to_dict()
    intent_data = intent.to_dict()
    requested = tuple(intent_data["requested_operations"])
    try:
        admission = classify_review_admission(
            policy=policy,
            source=source,
            capability=capability,
            intent=intent,
            evaluated_at=evaluated_at,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("runtime request admission is not proven") from exc
    if (
        admission["decision"] != "READY_FOR_HUMAN_REVIEW"
        or source.record_sha256 != view_model.source_binding_sha256
        or source_data["asset_id"] != view_model.source_asset_id
        or intent.record_sha256 != view_model.intent_sha256
        or intent_data["source_binding_sha256"] != source.record_sha256
        or intent_data["capability_binding_sha256"] != capability.record_sha256
        or source_data["contract_state"] != "BOUND_VERIFIED"
        or source_data["rights_state"] != "PASS"
        or source_data["sample_rate_hz"] != REQUIRED_SAMPLE_RATE_HZ
        or source_data["duration_samples"] != view_model.viewport.source_duration_samples
        or capability_data["contract_state"] != "BOUND_VERIFIED"
        or capability_data["decode_state"] != "SUPPORTED"
        or capability_data["sample_accurate_range_state"] != "SUPPORTED"
        or ("AUDITION" in requested and capability_data["player_state"] != "SUPPORTED")
        or ("WAVEFORM_VIEW" in requested and capability_data["waveform_state"] != "SUPPORTED")
        or intent_data["range_start_sample"] != view_model.viewport.waveform_start_sample
        or intent_data["range_end_sample"]
        != view_model.viewport.waveform_start_sample + view_model.viewport.waveform_span_samples
    ):
        raise ValueError("runtime request exact identity is not proven")
    body = {
        "policy_sha256": policy.record_sha256,
        "source_binding_sha256": source.record_sha256,
        "source_asset_id": source_data["asset_id"],
        "capability_binding_sha256": capability.record_sha256,
        "intent_sha256": intent.record_sha256,
        "requested_operations": list(requested),
        "sample_rate_hz": REQUIRED_SAMPLE_RATE_HZ,
        "source_duration_samples": source_data["duration_samples"],
        "range_start_sample": intent_data["range_start_sample"],
        "range_end_sample_exclusive": intent_data["range_end_sample"],
    }
    request_sha256 = sha256_bytes(canonical_json_bytes(body))
    return ReviewMediaRuntimeRequest(
        policy_sha256=policy.record_sha256,
        source_binding_sha256=source.record_sha256,
        source_asset_id=source_data["asset_id"],
        capability_binding_sha256=capability.record_sha256,
        intent_sha256=intent.record_sha256,
        requested_operations=requested,
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
        source_duration_samples=source_data["duration_samples"],
        range_start_sample=intent_data["range_start_sample"],
        range_end_sample_exclusive=intent_data["range_end_sample"],
        request_sha256=request_sha256,
    )


def reduce_review_media_runtime(
    request: ReviewMediaRuntimeRequest,
    observation: ReviewMediaRuntimeObservation | None = None,
) -> ReviewMediaRuntimeStatus:
    if type(request) is not ReviewMediaRuntimeRequest:
        raise ValueError("request is invalid")
    audition_requested = "AUDITION" in request.requested_operations
    waveform_requested = "WAVEFORM_VIEW" in request.requested_operations
    if observation is None:
        return ReviewMediaRuntimeStatus(
            ReviewMediaRuntimeState.NOT_BOUND,
            audition_requested,
            waveform_requested,
            False,
            False,
            None,
            ("PORT_NOT_BOUND",),
        )
    if type(observation) is not ReviewMediaRuntimeObservation:
        raise ValueError("observation is invalid")
    if observation.request_sha256 != request.request_sha256:
        return ReviewMediaRuntimeStatus(
            ReviewMediaRuntimeState.FAILED_KNOWN,
            audition_requested,
            waveform_requested,
            False,
            False,
            None,
            ("REQUEST_IDENTITY_MISMATCH",),
        )

    reasons: set[str] = set()
    if observation.playback_observed and not audition_requested:
        reasons.add("UNREQUESTED_AUDITION_OBSERVED")
    if observation.waveform_observed and not waveform_requested:
        reasons.add("UNREQUESTED_WAVEFORM_OBSERVED")
    if observation.state is ReviewMediaRuntimeState.SUCCEEDED:
        if audition_requested and not observation.playback_observed:
            reasons.add("AUDITION_NOT_OBSERVED")
        if waveform_requested and not observation.waveform_observed:
            reasons.add("WAVEFORM_NOT_OBSERVED")
    if reasons:
        return ReviewMediaRuntimeStatus(
            ReviewMediaRuntimeState.FAILED_KNOWN,
            audition_requested,
            waveform_requested,
            False,
            False,
            None,
            tuple(sorted(reasons)),
        )
    return ReviewMediaRuntimeStatus(
        observation.state,
        audition_requested,
        waveform_requested,
        observation.playback_observed,
        observation.waveform_observed,
        observation.waveform_point_count,
        observation.reason_codes,
    )


EFFECT_SURFACE = MappingProxyType(
    {
        "asset_lookup": False,
        "filesystem_read": False,
        "audio_decode": False,
        "audio_device_allocation": False,
        "playback": False,
        "waveform_generation": False,
        "task041_receipt_write": False,
        "review_state_persistence": False,
        "human_decision_authorized": False,
        "media_mutation": False,
    }
)


__all__ = [
    "EFFECT_SURFACE",
    "MAX_WAVEFORM_POINT_COUNT",
    "ReviewMediaRuntimeObservation",
    "ReviewMediaRuntimePort",
    "ReviewMediaRuntimeRequest",
    "ReviewMediaRuntimeState",
    "ReviewMediaRuntimeStatus",
    "build_review_media_runtime_request",
    "reduce_review_media_runtime",
]
