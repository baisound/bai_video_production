"""Pure fake-only capability observation and decision derivation for TASK-098.

This module deliberately knows no operating system, GPU, DLL, Provider, model,
network, download, store, or launcher.  The injected Protocol is the sole
boundary for the deterministic fake observations used by A2-R1a.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Protocol

from .faster_whisper_runtime_contract import (
    FasterWhisperRuntimeCapabilityObservationV1,
    FasterWhisperRuntimeDecisionV1,
    FasterWhisperRuntimeRequestV1,
)

_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_CPU_PAIR = ("cpu", "int8")
_CUDA_PAIR = ("cuda", "float16")


class FasterWhisperRuntimeCapabilityProbe(Protocol):
    """An injected fake-only capability probe; it performs no Product effects."""

    def supports(self, device: str, compute_type: str) -> bool:
        """Return the exact bool fact for one closed capability pair."""


def _expiry(observed_at: str, ttl_seconds: int) -> str:
    if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 300:
        raise ValueError("capability observation TTL must be an integer in 1..300 seconds")
    if not isinstance(observed_at, str) or not _TIME.fullmatch(observed_at):
        raise ValueError("observed_at must be a second-precision UTC RFC3339 timestamp")
    try:
        observed = datetime.fromisoformat(observed_at[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("observed_at must be a UTC RFC3339 timestamp") from exc
    return (observed + timedelta(seconds=ttl_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _probe(probe: FasterWhisperRuntimeCapabilityProbe, pair: tuple[str, str]) -> tuple[str, bool | None]:
    """Return (kind, fact), separating unavailable probe from invalid structure."""
    device, compute_type = pair
    if pair not in {_CPU_PAIR, _CUDA_PAIR}:
        return "RUNTIME_PROBE_INVALID", None
    try:
        supports = getattr(probe, "supports", None)
    except Exception:
        return "RUNTIME_PROBE_INVALID", None
    if not callable(supports):
        return "RUNTIME_PROBE_INVALID", None
    try:
        fact = supports(device, compute_type)
    except Exception:
        return "RUNTIME_PROBE_UNAVAILABLE", None
    if type(fact) is not bool:
        return "RUNTIME_PROBE_INVALID", None
    return "OBSERVED", fact


def collect_runtime_capability_observation(
    request: FasterWhisperRuntimeRequestV1,
    probe: FasterWhisperRuntimeCapabilityProbe,
    *,
    observed_at: str,
    ttl_seconds: int,
) -> FasterWhisperRuntimeCapabilityObservationV1:
    """Call only the exact allowed fake probe pairs and return one bound receipt."""
    if not isinstance(request, FasterWhisperRuntimeRequestV1):
        raise TypeError("request must be a validated FasterWhisperRuntimeRequestV1")
    request = FasterWhisperRuntimeRequestV1.from_dict(request.to_dict())
    expires_at = _expiry(observed_at, ttl_seconds)

    if request.requested_device == "cpu":
        outcome, available = _probe(probe, _CPU_PAIR)
        cpu = "AVAILABLE" if available is True else "UNAVAILABLE" if available is False else "UNKNOWN"
        return FasterWhisperRuntimeCapabilityObservationV1.create(
            request=request, probe_outcome=outcome, cpu_capability=cpu,
            cuda_capability="NOT_PROBED", observed_at=observed_at, expires_at=expires_at,
        )

    if request.requested_device == "cuda":
        outcome, available = _probe(probe, _CUDA_PAIR)
        cuda = "AVAILABLE" if available is True else "UNAVAILABLE" if available is False else "UNKNOWN"
        return FasterWhisperRuntimeCapabilityObservationV1.create(
            request=request, probe_outcome=outcome, cpu_capability="NOT_PROBED",
            cuda_capability=cuda, observed_at=observed_at, expires_at=expires_at,
        )

    cuda_outcome, cuda_available = _probe(probe, _CUDA_PAIR)
    if cuda_outcome != "OBSERVED":
        return FasterWhisperRuntimeCapabilityObservationV1.create(
            request=request, probe_outcome=cuda_outcome, cpu_capability="NOT_PROBED",
            cuda_capability="UNKNOWN", observed_at=observed_at, expires_at=expires_at,
        )
    if cuda_available is True:
        return FasterWhisperRuntimeCapabilityObservationV1.create(
            request=request, probe_outcome="OBSERVED", cpu_capability="NOT_PROBED",
            cuda_capability="AVAILABLE", observed_at=observed_at, expires_at=expires_at,
        )

    cpu_outcome, cpu_available = _probe(probe, _CPU_PAIR)
    if cpu_outcome != "OBSERVED":
        return FasterWhisperRuntimeCapabilityObservationV1.create(
            request=request, probe_outcome=cpu_outcome, cpu_capability="UNKNOWN",
            cuda_capability="UNAVAILABLE", observed_at=observed_at, expires_at=expires_at,
        )
    return FasterWhisperRuntimeCapabilityObservationV1.create(
        request=request, probe_outcome="OBSERVED",
        cpu_capability="AVAILABLE" if cpu_available else "UNAVAILABLE",
        cuda_capability="UNAVAILABLE", observed_at=observed_at, expires_at=expires_at,
    )


def resolve_runtime_decision(
    request: FasterWhisperRuntimeRequestV1,
    observation: FasterWhisperRuntimeCapabilityObservationV1,
) -> FasterWhisperRuntimeDecisionV1:
    """Derive the only valid A2-R0 decision from one request-bound observation."""
    if not isinstance(request, FasterWhisperRuntimeRequestV1):
        raise TypeError("request must be a validated FasterWhisperRuntimeRequestV1")
    if not isinstance(observation, FasterWhisperRuntimeCapabilityObservationV1):
        raise TypeError("observation must be a validated FasterWhisperRuntimeCapabilityObservationV1")
    request = FasterWhisperRuntimeRequestV1.from_dict(request.to_dict())
    observation = FasterWhisperRuntimeCapabilityObservationV1.from_dict(observation.to_dict(), request=request)
    if observation.probe_outcome != "OBSERVED":
        outcome, reason = "BLOCKED", observation.probe_outcome
    elif request.requested_device == "cpu":
        outcome, reason = (("READY_CPU", "REQUESTED_CPU_AVAILABLE")
                           if observation.cpu_capability == "AVAILABLE"
                           else ("BLOCKED", "CPU_UNAVAILABLE"))
    elif request.requested_device == "cuda":
        outcome, reason = (("READY_CUDA", "REQUESTED_CUDA_AVAILABLE")
                           if observation.cuda_capability == "AVAILABLE"
                           else ("BLOCKED", "CUDA_UNAVAILABLE"))
    elif observation.cuda_capability == "AVAILABLE":
        outcome, reason = "READY_CUDA", "AUTO_CUDA_AVAILABLE"
    elif observation.cpu_capability == "AVAILABLE":
        outcome, reason = "READY_CPU", "AUTO_CUDA_UNAVAILABLE_CPU_AVAILABLE"
    else:
        outcome, reason = "BLOCKED", "AUTO_NO_RUNTIME_AVAILABLE"
    return FasterWhisperRuntimeDecisionV1.create(
        request=request, outcome=outcome, reason_code=reason,
        capability_observation_sha256=observation.record_sha256,
        issued_at=observation.observed_at, expires_at=observation.expires_at,
    )


def evaluate_runtime_preflight(
    request: FasterWhisperRuntimeRequestV1,
    probe: FasterWhisperRuntimeCapabilityProbe,
    *,
    observed_at: str,
    ttl_seconds: int,
) -> tuple[FasterWhisperRuntimeCapabilityObservationV1, FasterWhisperRuntimeDecisionV1]:
    """Produce the immutable observation and its unique A2-R0 decision."""
    observation = collect_runtime_capability_observation(
        request, probe, observed_at=observed_at, ttl_seconds=ttl_seconds,
    )
    return observation, resolve_runtime_decision(request, observation)


__all__ = [
    "FasterWhisperRuntimeCapabilityProbe",
    "collect_runtime_capability_observation",
    "evaluate_runtime_preflight",
    "resolve_runtime_decision",
]
