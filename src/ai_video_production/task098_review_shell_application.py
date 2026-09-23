"""Human-confirmed local Shell adapter for TASK-098 A6 WAV review."""

from __future__ import annotations

from dataclasses import dataclass
import re
import secrets
import threading
import time
from typing import Callable

from .audio_workspace_media_review import (
    AudioMediaReviewIntent,
    AudioMediaReviewPolicyRevision,
    AudioMediaSourceBinding,
    PlaybackWaveformCapabilityBinding,
)
from .errors import ProductError, ProductErrorCategory
from .task098_review_media_runtime_contract import (
    ReviewMediaRuntimeRequest,
    ReviewMediaRuntimeState,
    build_review_media_runtime_request,
    reduce_review_media_runtime,
)
from .task098_review_media_runtime_windows import RegistryBoundReviewMediaRuntimePort
from .task098_review_workspace_coordinator import ReviewWorkspaceViewModel


MAX_SHELL_WAVEFORM_POINTS = 2_048
MAX_PENDING_CONFIRMATIONS = 8
CONFIRMATION_TTL_SECONDS = 300
_CONFIRMATION_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")


@dataclass(frozen=True, slots=True)
class Task098ReviewShellBinding:
    policy: AudioMediaReviewPolicyRevision
    source: AudioMediaSourceBinding
    capability: PlaybackWaveformCapabilityBinding
    intent: AudioMediaReviewIntent
    view_model: ReviewWorkspaceViewModel
    evaluated_at: str

    def __post_init__(self) -> None:
        expected = (
            (self.policy, AudioMediaReviewPolicyRevision),
            (self.source, AudioMediaSourceBinding),
            (self.capability, PlaybackWaveformCapabilityBinding),
            (self.intent, AudioMediaReviewIntent),
            (self.view_model, ReviewWorkspaceViewModel),
        )
        if any(type(value) is not kind for value, kind in expected):
            raise ValueError("review Shell binding is invalid")
        if not isinstance(self.evaluated_at, str) or not self.evaluated_at:
            raise ValueError("review Shell evaluation time is invalid")

    def request(self) -> ReviewMediaRuntimeRequest:
        request = build_review_media_runtime_request(
            policy=self.policy,
            source=self.source,
            capability=self.capability,
            intent=self.intent,
            view_model=self.view_model,
            evaluated_at=self.evaluated_at,
        )
        if request.requested_operations != ("AUDITION", "WAVEFORM_VIEW"):
            raise ValueError("A6 Shell review requires audition and waveform")
        return request


@dataclass(frozen=True, slots=True)
class _PendingConfirmation:
    request: ReviewMediaRuntimeRequest
    expires_at: float


def _closed_error(code: str, message: str, category: ProductErrorCategory) -> ProductError:
    return ProductError(code, message, category)


def _confirmation_id(value: object) -> str:
    if not isinstance(value, str) or _CONFIRMATION_ID.fullmatch(value) is None:
        raise _closed_error(
            "ERR_TASK098_REVIEW_CONFIRMATION_INVALID",
            "Universal WAV Review confirmation is invalid",
            ProductErrorCategory.VALIDATION,
        )
    return value


class Task098ReviewShellApplication:
    """One-use Human confirmation around the registry-bound review runtime."""

    def __init__(
        self,
        *,
        binding_provider: Callable[[], Task098ReviewShellBinding],
        runtime: RegistryBoundReviewMediaRuntimePort,
        monotonic: Callable[[], float] = time.monotonic,
        identity: Callable[[], str] = lambda: secrets.token_urlsafe(24),
    ) -> None:
        if not callable(binding_provider) or type(runtime) is not RegistryBoundReviewMediaRuntimePort:
            raise ValueError("review Shell application dependencies are invalid")
        if not callable(monotonic) or not callable(identity):
            raise ValueError("review Shell application clock or identity is invalid")
        self._binding_provider = binding_provider
        self._runtime = runtime
        self._monotonic = monotonic
        self._identity = identity
        self._lock = threading.Lock()
        self._operation_lock = threading.Lock()
        self._pending: dict[str, _PendingConfirmation] = {}
        self._closed = False

    def _ensure_open(self) -> None:
        with self._lock:
            if self._closed:
                raise _closed_error(
                    "ERR_TASK098_REVIEW_RUNTIME_CLOSED",
                    "Universal WAV Review runtime is closed",
                    ProductErrorCategory.STATE,
                )

    def close(self) -> None:
        """Close the process-local confirmation/runtime lifetime."""

        with self._operation_lock:
            with self._lock:
                self._closed = True
                self._pending.clear()

    def __enter__(self) -> "Task098ReviewShellApplication":
        self._ensure_open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _binding(self) -> Task098ReviewShellBinding:
        self._ensure_open()
        try:
            binding = self._binding_provider()
            if type(binding) is not Task098ReviewShellBinding:
                raise ValueError("binding type is invalid")
            binding.__post_init__()
            binding.request()
            return binding
        except Exception:
            raise _closed_error(
                "ERR_TASK098_REVIEW_BINDING_INVALID",
                "Universal WAV Review binding is unavailable",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from None

    def view_model(self) -> ReviewWorkspaceViewModel:
        return self._binding().view_model

    def prepare(self) -> dict[str, object]:
        request = self._binding().request()
        now = self._monotonic()
        with self._lock:
            if self._closed:
                raise _closed_error(
                    "ERR_TASK098_REVIEW_RUNTIME_CLOSED",
                    "Universal WAV Review runtime is closed",
                    ProductErrorCategory.STATE,
                )
            self._pending = {
                key: value for key, value in self._pending.items() if value.expires_at > now
            }
            if len(self._pending) >= MAX_PENDING_CONFIRMATIONS:
                raise _closed_error(
                    "ERR_TASK098_REVIEW_CONFIRMATION_CAPACITY",
                    "Universal WAV Review confirmation capacity is reached",
                    ProductErrorCategory.STATE,
                )
            try:
                confirmation_id = self._identity()
            except Exception:
                raise _closed_error(
                    "ERR_TASK098_REVIEW_CONFIRMATION_INVALID",
                    "Universal WAV Review confirmation could not be created",
                    ProductErrorCategory.STATE,
                ) from None
            if (
                not isinstance(confirmation_id, str)
                or _CONFIRMATION_ID.fullmatch(confirmation_id) is None
                or confirmation_id in self._pending
            ):
                raise _closed_error(
                    "ERR_TASK098_REVIEW_CONFIRMATION_INVALID",
                    "Universal WAV Review confirmation could not be created",
                    ProductErrorCategory.STATE,
                )
            self._pending[confirmation_id] = _PendingConfirmation(
                request=request,
                expires_at=now + CONFIRMATION_TTL_SECONDS,
            )
        return {
            "task_owner": "TASK-098",
            "confirmation_id": confirmation_id,
            "status_label": "private音声を再生して波形を表示",
            "warning": (
                "canonical Assetの選択範囲をローカルで再生し、波形を一時表示します。"
                "Asset・Review・TASK-041の状態は変更しません。"
            ),
            "expires_in_seconds": CONFIRMATION_TTL_SECONDS,
        }

    def cancel(self, confirmation_id: str) -> dict[str, object]:
        confirmation_id = _confirmation_id(confirmation_id)
        with self._lock:
            if self._closed:
                raise _closed_error(
                    "ERR_TASK098_REVIEW_RUNTIME_CLOSED",
                    "Universal WAV Review runtime is closed",
                    ProductErrorCategory.STATE,
                )
            removed = self._pending.pop(confirmation_id, None) is not None
        return {
            "task_owner": "TASK-098",
            "status": "CANCELLED" if removed else "NOT_PENDING",
            "media_effect_started": False,
        }

    def apply(self, confirmation_id: str) -> dict[str, object]:
        confirmation_id = _confirmation_id(confirmation_id)
        with self._operation_lock:
            now = self._monotonic()
            with self._lock:
                if self._closed:
                    raise _closed_error(
                        "ERR_TASK098_REVIEW_RUNTIME_CLOSED",
                        "Universal WAV Review runtime is closed",
                        ProductErrorCategory.STATE,
                    )
                pending = self._pending.pop(confirmation_id, None)
            if pending is None or pending.expires_at <= now:
                raise _closed_error(
                    "ERR_TASK098_REVIEW_CONFIRMATION_EXPIRED",
                    "Universal WAV Review confirmation is unavailable",
                    ProductErrorCategory.STATE,
                )
            current = self._binding().request()
            if current != pending.request:
                raise _closed_error(
                    "ERR_TASK098_REVIEW_BINDING_STALE",
                    "Universal WAV Review binding changed after confirmation",
                    ProductErrorCategory.STATE,
                )
            try:
                observation, envelope = self._runtime.execute_with_ephemeral_waveform(
                    current
                )
                status = reduce_review_media_runtime(current, observation)
                if any(
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or not 0 <= value <= 1_000
                    for value in envelope
                ) or len(envelope) > MAX_SHELL_WAVEFORM_POINTS:
                    raise ValueError("private waveform envelope is invalid")
                if (
                    status.state is ReviewMediaRuntimeState.SUCCEEDED
                    and status.waveform_observed
                    and not envelope
                ):
                    raise ValueError("successful waveform has no display envelope")
                if status.state is not ReviewMediaRuntimeState.SUCCEEDED and envelope:
                    raise ValueError("failed runtime returned a waveform envelope")
            except ProductError:
                raise
            except Exception:
                raise _closed_error(
                    "ERR_TASK098_REVIEW_RUNTIME_INVALID",
                    "Universal WAV Review runtime result is invalid",
                    ProductErrorCategory.DATA_INTEGRITY,
                ) from None
        return {
            **status.to_public_dict(),
            "waveform_envelope_milli": list(envelope),
            "waveform_ephemeral": True,
            "audio_body_exposed": False,
            "private_identity_exposed": False,
        }


__all__ = [
    "CONFIRMATION_TTL_SECONDS",
    "MAX_PENDING_CONFIRMATIONS",
    "MAX_SHELL_WAVEFORM_POINTS",
    "Task098ReviewShellApplication",
    "Task098ReviewShellBinding",
]
