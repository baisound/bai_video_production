"""Pure TASK-098 FasterWhisper preflight request and decision contracts.

This module intentionally has no runtime probe, Provider, model, inference, or
filesystem behaviour.  A decision is a body-free, short-lived observation
receipt; it is not execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
import re
from typing import Any, ClassVar, Mapping

from jsonschema import Draft202012Validator

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256

SCHEMA_NAME = "faster-whisper-runtime-contract.schema.json"
SCHEMA_VERSION = "1.0.0"
REQUEST_RECORD_TYPE = "FasterWhisperRuntimeRequestV1"
DECISION_RECORD_TYPE = "FasterWhisperRuntimeDecisionV1"
OBSERVATION_RECORD_TYPE = "FasterWhisperRuntimeCapabilityObservationV1"
REQUEST_DOMAIN = b"bvp.task098.faster-whisper-runtime-request.v1\0"
DECISION_DOMAIN = b"bvp.task098.faster-whisper-runtime-decision.v1\0"
OBSERVATION_DOMAIN = b"bvp.task098.faster-whisper-runtime-capability.v1\0"
COMPUTE_POLICY = "UWR_BALANCED_V1"
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

_REQUEST_FIELDS = frozenset(("record_type", "schema_version", "requested_device", "compute_policy", "model_download_authorized", "record_sha256"))
_DECISION_FIELDS = frozenset(("record_type", "schema_version", "runtime_request_sha256", "outcome", "reason_code", "effective_device", "effective_compute_type", "fallback_applied", "capability_observation_sha256", "issued_at", "expires_at", "model_load_started", "inference_started", "partial_output_present", "execution_authorized", "record_sha256"))
_OBSERVATION_FIELDS = frozenset(("record_type", "schema_version", "runtime_request_sha256", "probe_outcome", "cpu_capability", "cuda_capability", "observed_at", "expires_at", "model_load_started", "inference_started", "network_used", "model_download_authorized", "record_sha256"))
_MATRIX = {
    ("cpu", "READY_CPU", "REQUESTED_CPU_AVAILABLE"): ("cpu", "int8", False),
    ("cpu", "BLOCKED", "CPU_UNAVAILABLE"): (None, None, False),
    ("cuda", "READY_CUDA", "REQUESTED_CUDA_AVAILABLE"): ("cuda", "float16", False),
    ("cuda", "BLOCKED", "CUDA_UNAVAILABLE"): (None, None, False),
    ("auto", "READY_CUDA", "AUTO_CUDA_AVAILABLE"): ("cuda", "float16", False),
    ("auto", "READY_CPU", "AUTO_CUDA_UNAVAILABLE_CPU_AVAILABLE"): ("cpu", "int8", True),
    ("auto", "BLOCKED", "AUTO_NO_RUNTIME_AVAILABLE"): (None, None, False),
}
for _device in ("cpu", "cuda", "auto"):
    for _reason in ("RUNTIME_PROBE_UNAVAILABLE", "RUNTIME_PROBE_INVALID"):
        _MATRIX[(_device, "BLOCKED", _reason)] = (None, None, False)

_OBSERVATION_MATRIX = {
    ("cpu", "OBSERVED", "AVAILABLE", "NOT_PROBED"),
    ("cpu", "OBSERVED", "UNAVAILABLE", "NOT_PROBED"),
    ("cpu", "RUNTIME_PROBE_UNAVAILABLE", "UNKNOWN", "NOT_PROBED"),
    ("cpu", "RUNTIME_PROBE_INVALID", "UNKNOWN", "NOT_PROBED"),
    ("cuda", "OBSERVED", "NOT_PROBED", "AVAILABLE"),
    ("cuda", "OBSERVED", "NOT_PROBED", "UNAVAILABLE"),
    ("cuda", "RUNTIME_PROBE_UNAVAILABLE", "NOT_PROBED", "UNKNOWN"),
    ("cuda", "RUNTIME_PROBE_INVALID", "NOT_PROBED", "UNKNOWN"),
    ("auto", "OBSERVED", "NOT_PROBED", "AVAILABLE"),
    ("auto", "OBSERVED", "AVAILABLE", "UNAVAILABLE"),
    ("auto", "OBSERVED", "UNAVAILABLE", "UNAVAILABLE"),
    ("auto", "RUNTIME_PROBE_UNAVAILABLE", "NOT_PROBED", "UNKNOWN"),
    ("auto", "RUNTIME_PROBE_INVALID", "NOT_PROBED", "UNKNOWN"),
    ("auto", "RUNTIME_PROBE_UNAVAILABLE", "UNKNOWN", "UNAVAILABLE"),
    ("auto", "RUNTIME_PROBE_INVALID", "UNKNOWN", "UNAVAILABLE"),
}


def _exact(value: Mapping[str, Any], fields: frozenset[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise ValueError(f"{name} must be sha256:<64 lowercase hex>")
    return validate_sha256(value, field_name=name)


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not _TIME.fullmatch(value):
        raise ValueError(f"{name} must be a second-precision UTC RFC3339 timestamp")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be a UTC RFC3339 timestamp") from exc


def _body_digest(value: Mapping[str, Any], domain: bytes) -> str:
    return sha256_bytes(domain + canonical_json_bytes({key: item for key, item in value.items() if key != "record_sha256"}))


def _schema(name: str, value: Mapping[str, Any]) -> None:
    try:
        with resources.files("ai_video_production.schema_resources").joinpath(SCHEMA_NAME).open("rb") as source:
            document = __import__("json").load(source)
        validator = Draft202012Validator({"$schema": document["$schema"], "$defs": document["$defs"], "$ref": f"#/$defs/{name}"})
        if next(validator.iter_errors(dict(value)), None) is not None:
            raise ValueError("schema validation failed")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("runtime contract schema validation failed") from exc


@dataclass(frozen=True, slots=True, init=False)
class FasterWhisperRuntimeRequestV1:
    requested_device: str
    record_sha256: str
    record_type: ClassVar[str] = REQUEST_RECORD_TYPE
    schema_version: ClassVar[str] = SCHEMA_VERSION
    compute_policy: ClassVar[str] = COMPUTE_POLICY
    model_download_authorized: ClassVar[bool] = False

    def __init__(self, requested_device: str, *, record_sha256: str | None = None) -> None:
        if requested_device not in {"auto", "cpu", "cuda"}:
            raise ValueError("request policy is outside the closed contract")
        body = {"record_type": REQUEST_RECORD_TYPE, "schema_version": SCHEMA_VERSION,
                "requested_device": requested_device, "compute_policy": COMPUTE_POLICY,
                "model_download_authorized": False}
        expected = _body_digest(body, REQUEST_DOMAIN)
        if record_sha256 is not None and _digest(record_sha256, "record_sha256") != expected:
            raise ValueError("request digest mismatch")
        object.__setattr__(self, "requested_device", requested_device)
        object.__setattr__(self, "record_sha256", expected)

    @classmethod
    def create(cls, requested_device: str) -> "FasterWhisperRuntimeRequestV1":
        return cls(requested_device)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FasterWhisperRuntimeRequestV1":
        _exact(value, _REQUEST_FIELDS, REQUEST_RECORD_TYPE)
        _schema("request", value)
        if value["record_type"] != REQUEST_RECORD_TYPE or value["schema_version"] != SCHEMA_VERSION:
            raise ValueError("request identity/version is invalid")
        if value["requested_device"] not in {"auto", "cpu", "cuda"} or value["compute_policy"] != COMPUTE_POLICY:
            raise ValueError("request policy is outside the closed contract")
        if value["model_download_authorized"] is not False:
            raise ValueError("model download is not authorized")
        digest = _digest(value["record_sha256"], "record_sha256")
        if digest != _body_digest(value, REQUEST_DOMAIN):
            raise ValueError("request digest mismatch")
        return cls(value["requested_device"], record_sha256=digest)

    def to_dict(self) -> dict[str, Any]:
        return {"record_type": REQUEST_RECORD_TYPE, "schema_version": SCHEMA_VERSION,
                "requested_device": self.requested_device, "compute_policy": COMPUTE_POLICY,
                "model_download_authorized": False, "record_sha256": self.record_sha256}

    def to_public_dict(self) -> dict[str, Any]:
        return {"record_type": REQUEST_RECORD_TYPE, "schema_version": SCHEMA_VERSION,
                "requested_device": self.requested_device, "compute_policy": COMPUTE_POLICY,
                "model_download_authorized": False}


@dataclass(frozen=True, slots=True, init=False)
class FasterWhisperRuntimeCapabilityObservationV1:
    """Request-bound, body-free capability observation with a closed TTL window."""

    runtime_request_sha256: str
    probe_outcome: str
    cpu_capability: str
    cuda_capability: str
    observed_at: str
    expires_at: str
    record_sha256: str
    record_type: ClassVar[str] = OBSERVATION_RECORD_TYPE
    schema_version: ClassVar[str] = SCHEMA_VERSION
    model_load_started: ClassVar[bool] = False
    inference_started: ClassVar[bool] = False
    network_used: ClassVar[bool] = False
    model_download_authorized: ClassVar[bool] = False

    def __init__(self, *, request: FasterWhisperRuntimeRequestV1, probe_outcome: str,
                 cpu_capability: str, cuda_capability: str, observed_at: str,
                 expires_at: str, record_sha256: str | None = None) -> None:
        if not isinstance(request, FasterWhisperRuntimeRequestV1):
            raise TypeError("request must be a validated FasterWhisperRuntimeRequestV1")
        request = FasterWhisperRuntimeRequestV1.from_dict(request.to_dict())
        if (request.requested_device, probe_outcome, cpu_capability, cuda_capability) not in _OBSERVATION_MATRIX:
            raise ValueError("capability observation is outside the closed request matrix")
        observed, expires = _timestamp(observed_at, "observed_at"), _timestamp(expires_at, "expires_at")
        if not 1 <= (expires - observed).total_seconds() <= 300:
            raise ValueError("capability observation TTL must be 1..300 seconds")
        body = {
            "record_type": OBSERVATION_RECORD_TYPE,
            "schema_version": SCHEMA_VERSION,
            "runtime_request_sha256": request.record_sha256,
            "probe_outcome": probe_outcome,
            "cpu_capability": cpu_capability,
            "cuda_capability": cuda_capability,
            "observed_at": observed_at,
            "expires_at": expires_at,
            "model_load_started": False,
            "inference_started": False,
            "network_used": False,
            "model_download_authorized": False,
        }
        expected = _body_digest(body, OBSERVATION_DOMAIN)
        if record_sha256 is not None and _digest(record_sha256, "record_sha256") != expected:
            raise ValueError("capability observation digest mismatch")
        for name, item in body.items():
            if name not in {"record_type", "schema_version", "model_load_started", "inference_started", "network_used", "model_download_authorized"}:
                object.__setattr__(self, name, item)
        object.__setattr__(self, "record_sha256", expected)

    @classmethod
    def create(cls, *, request: FasterWhisperRuntimeRequestV1, probe_outcome: str,
               cpu_capability: str, cuda_capability: str, observed_at: str,
               expires_at: str) -> "FasterWhisperRuntimeCapabilityObservationV1":
        return cls(request=request, probe_outcome=probe_outcome,
                   cpu_capability=cpu_capability, cuda_capability=cuda_capability,
                   observed_at=observed_at, expires_at=expires_at)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], *, request: FasterWhisperRuntimeRequestV1) -> "FasterWhisperRuntimeCapabilityObservationV1":
        _exact(value, _OBSERVATION_FIELDS, OBSERVATION_RECORD_TYPE)
        _schema("observation", value)
        if value["record_type"] != OBSERVATION_RECORD_TYPE or value["schema_version"] != SCHEMA_VERSION:
            raise ValueError("capability observation identity/version is invalid")
        if not isinstance(request, FasterWhisperRuntimeRequestV1):
            raise TypeError("request must be a validated FasterWhisperRuntimeRequestV1")
        request = FasterWhisperRuntimeRequestV1.from_dict(request.to_dict())
        if value["runtime_request_sha256"] != request.record_sha256:
            raise ValueError("capability observation does not bind the supplied runtime request")
        _digest(value["runtime_request_sha256"], "runtime_request_sha256")
        if (request.requested_device, value["probe_outcome"], value["cpu_capability"], value["cuda_capability"]) not in _OBSERVATION_MATRIX:
            raise ValueError("capability observation is outside the closed request matrix")
        if any(value[flag] is not False for flag in ("model_load_started", "inference_started", "network_used", "model_download_authorized")):
            raise ValueError("capability observation cannot represent execution, network, or download")
        observed, expires = _timestamp(value["observed_at"], "observed_at"), _timestamp(value["expires_at"], "expires_at")
        if not 1 <= (expires - observed).total_seconds() <= 300:
            raise ValueError("capability observation TTL must be 1..300 seconds")
        digest = _digest(value["record_sha256"], "record_sha256")
        if digest != _body_digest(value, OBSERVATION_DOMAIN):
            raise ValueError("capability observation digest mismatch")
        return cls(request=request, probe_outcome=value["probe_outcome"],
                   cpu_capability=value["cpu_capability"], cuda_capability=value["cuda_capability"],
                   observed_at=value["observed_at"], expires_at=value["expires_at"],
                   record_sha256=digest)

    def is_fresh_at(self, evaluated_at: str) -> bool:
        evaluated = _timestamp(evaluated_at, "evaluated_at")
        return _timestamp(self.observed_at, "observed_at") <= evaluated < _timestamp(self.expires_at, "expires_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": OBSERVATION_RECORD_TYPE,
            "schema_version": SCHEMA_VERSION,
            "runtime_request_sha256": self.runtime_request_sha256,
            "probe_outcome": self.probe_outcome,
            "cpu_capability": self.cpu_capability,
            "cuda_capability": self.cuda_capability,
            "observed_at": self.observed_at,
            "expires_at": self.expires_at,
            "model_load_started": False,
            "inference_started": False,
            "network_used": False,
            "model_download_authorized": False,
            "record_sha256": self.record_sha256,
        }


@dataclass(frozen=True, slots=True, init=False)
class FasterWhisperRuntimeDecisionV1:
    runtime_request_sha256: str
    outcome: str
    reason_code: str
    effective_device: str | None
    effective_compute_type: str | None
    fallback_applied: bool
    capability_observation_sha256: str
    issued_at: str
    expires_at: str
    record_sha256: str
    record_type: ClassVar[str] = DECISION_RECORD_TYPE
    schema_version: ClassVar[str] = SCHEMA_VERSION
    model_load_started: ClassVar[bool] = False
    inference_started: ClassVar[bool] = False
    partial_output_present: ClassVar[bool] = False
    execution_authorized: ClassVar[bool] = False

    def __init__(self, *, request: FasterWhisperRuntimeRequestV1, outcome: str,
                 reason_code: str, capability_observation_sha256: str, issued_at: str,
                 expires_at: str, record_sha256: str | None = None) -> None:
        if not isinstance(request, FasterWhisperRuntimeRequestV1):
            raise TypeError("request must be a validated FasterWhisperRuntimeRequestV1")
        request = FasterWhisperRuntimeRequestV1.from_dict(request.to_dict())
        _digest(capability_observation_sha256, "capability_observation_sha256")
        expected = _MATRIX.get((request.requested_device, outcome, reason_code))
        if expected is None:
            raise ValueError("decision is outside the closed outcome matrix")
        issued, expires = _timestamp(issued_at, "issued_at"), _timestamp(expires_at, "expires_at")
        if not 1 <= (expires - issued).total_seconds() <= 300:
            raise ValueError("decision TTL must be 1..300 seconds")
        effective_device, effective_compute_type, fallback_applied = expected
        body = {"record_type": DECISION_RECORD_TYPE, "schema_version": SCHEMA_VERSION,
                "runtime_request_sha256": request.record_sha256, "outcome": outcome,
                "reason_code": reason_code, "effective_device": effective_device,
                "effective_compute_type": effective_compute_type, "fallback_applied": fallback_applied,
                "capability_observation_sha256": capability_observation_sha256,
                "issued_at": issued_at, "expires_at": expires_at,
                "model_load_started": False, "inference_started": False,
                "partial_output_present": False, "execution_authorized": False}
        expected_digest = _body_digest(body, DECISION_DOMAIN)
        if record_sha256 is not None and _digest(record_sha256, "record_sha256") != expected_digest:
            raise ValueError("decision digest mismatch")
        for name, value in body.items():
            if name != "record_type" and name != "schema_version" and name not in {"model_load_started", "inference_started", "partial_output_present", "execution_authorized"}:
                object.__setattr__(self, name, value)
        object.__setattr__(self, "record_sha256", expected_digest)

    @classmethod
    def create(cls, *, request: FasterWhisperRuntimeRequestV1, outcome: str,
               reason_code: str, capability_observation_sha256: str, issued_at: str,
               expires_at: str) -> "FasterWhisperRuntimeDecisionV1":
        return cls(request=request, outcome=outcome, reason_code=reason_code,
                   capability_observation_sha256=capability_observation_sha256,
                   issued_at=issued_at, expires_at=expires_at)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], *, request: FasterWhisperRuntimeRequestV1) -> "FasterWhisperRuntimeDecisionV1":
        _exact(value, _DECISION_FIELDS, DECISION_RECORD_TYPE)
        _schema("decision", value)
        if value["record_type"] != DECISION_RECORD_TYPE or value["schema_version"] != SCHEMA_VERSION:
            raise ValueError("decision identity/version is invalid")
        if not isinstance(request, FasterWhisperRuntimeRequestV1):
            raise TypeError("request must be a validated FasterWhisperRuntimeRequestV1")
        request = FasterWhisperRuntimeRequestV1.from_dict(request.to_dict())
        _digest(value["runtime_request_sha256"], "runtime_request_sha256")
        _digest(value["capability_observation_sha256"], "capability_observation_sha256")
        expected = _MATRIX.get((request.requested_device, value["outcome"], value["reason_code"]))
        if expected is None or (value["effective_device"], value["effective_compute_type"], value["fallback_applied"]) != expected:
            raise ValueError("decision is outside the closed outcome matrix")
        if value["runtime_request_sha256"] != request.record_sha256:
            raise ValueError("decision does not bind the supplied runtime request")
        if any(value[flag] is not False for flag in ("model_load_started", "inference_started", "partial_output_present", "execution_authorized")):
            raise ValueError("A2-R0 cannot represent started, partial, or authorized execution")
        issued, expires = _timestamp(value["issued_at"], "issued_at"), _timestamp(value["expires_at"], "expires_at")
        ttl = (expires - issued).total_seconds()
        if not 1 <= ttl <= 300:
            raise ValueError("decision TTL must be 1..300 seconds")
        digest = _digest(value["record_sha256"], "record_sha256")
        if digest != _body_digest(value, DECISION_DOMAIN):
            raise ValueError("decision digest mismatch")
        return cls(request=request, outcome=value["outcome"], reason_code=value["reason_code"],
                   capability_observation_sha256=value["capability_observation_sha256"],
                   issued_at=value["issued_at"], expires_at=value["expires_at"], record_sha256=digest)

    def is_fresh_at(self, evaluated_at: str) -> bool:
        evaluated = _timestamp(evaluated_at, "evaluated_at")
        return _timestamp(self.issued_at, "issued_at") <= evaluated < _timestamp(self.expires_at, "expires_at")

    def to_dict(self) -> dict[str, Any]:
        return {"record_type": DECISION_RECORD_TYPE, "schema_version": SCHEMA_VERSION,
                "runtime_request_sha256": self.runtime_request_sha256, "outcome": self.outcome,
                "reason_code": self.reason_code, "effective_device": self.effective_device,
                "effective_compute_type": self.effective_compute_type, "fallback_applied": self.fallback_applied,
                "capability_observation_sha256": self.capability_observation_sha256,
                "issued_at": self.issued_at, "expires_at": self.expires_at,
                "model_load_started": False, "inference_started": False,
                "partial_output_present": False, "execution_authorized": False,
                "record_sha256": self.record_sha256}

    def to_public_dict(self) -> dict[str, Any]:
        return {"record_type": DECISION_RECORD_TYPE, "schema_version": SCHEMA_VERSION,
                "outcome": self.outcome, "reason_code": self.reason_code,
                "effective_device": self.effective_device, "effective_compute_type": self.effective_compute_type,
                "fallback_applied": self.fallback_applied, "model_load_started": False,
                "inference_started": False, "partial_output_present": False,
                "execution_authorized": False}


def parse_runtime_request(value: Mapping[str, Any]) -> FasterWhisperRuntimeRequestV1:
    return FasterWhisperRuntimeRequestV1.from_dict(value)


def parse_runtime_decision(value: Mapping[str, Any], *, request: FasterWhisperRuntimeRequestV1) -> FasterWhisperRuntimeDecisionV1:
    return FasterWhisperRuntimeDecisionV1.from_dict(value, request=request)


def parse_runtime_capability_observation(value: Mapping[str, Any], *, request: FasterWhisperRuntimeRequestV1) -> FasterWhisperRuntimeCapabilityObservationV1:
    return FasterWhisperRuntimeCapabilityObservationV1.from_dict(value, request=request)


def validate_runtime_pair(request: FasterWhisperRuntimeRequestV1,
                          decision: FasterWhisperRuntimeDecisionV1) -> tuple[FasterWhisperRuntimeRequestV1, FasterWhisperRuntimeDecisionV1]:
    """Validate a decision against its one stable semantic request identity."""
    if not isinstance(request, FasterWhisperRuntimeRequestV1) or not isinstance(decision, FasterWhisperRuntimeDecisionV1):
        raise TypeError("request and decision must use the exact runtime contract types")
    parsed_request = FasterWhisperRuntimeRequestV1.from_dict(request.to_dict())
    parsed_decision = FasterWhisperRuntimeDecisionV1.from_dict(decision.to_dict(), request=parsed_request)
    return parsed_request, parsed_decision


def validate_schema_mirror() -> None:
    """Fail closed unless source and packaged schema bytes are identical."""
    with resources.files("ai_video_production.schema_resources").joinpath(SCHEMA_NAME).open("rb") as source:
        packaged = source.read()
    source_path = Path(__file__).resolve().parents[2] / "schemas" / SCHEMA_NAME
    try:
        source_bytes = source_path.read_bytes()
    except OSError as exc:
        raise ValueError("runtime contract source schema is unavailable") from exc
    if not packaged or source_bytes != packaged:
        raise ValueError("runtime contract schema mirror is not byte-identical")


__all__ = ["COMPUTE_POLICY", "DECISION_RECORD_TYPE", "FasterWhisperRuntimeCapabilityObservationV1",
           "FasterWhisperRuntimeDecisionV1", "FasterWhisperRuntimeRequestV1",
           "OBSERVATION_RECORD_TYPE", "REQUEST_RECORD_TYPE", "SCHEMA_VERSION",
           "parse_runtime_capability_observation", "parse_runtime_decision",
           "parse_runtime_request", "validate_runtime_pair", "validate_schema_mirror"]
