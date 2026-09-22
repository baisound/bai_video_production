from __future__ import annotations

import copy
import json
from importlib import resources

import pytest
from jsonschema import Draft202012Validator

from ai_video_production import faster_whisper_runtime_preflight as preflight
from ai_video_production.faster_whisper_runtime_contract import (
    OBSERVATION_DOMAIN,
    FasterWhisperRuntimeCapabilityObservationV1,
    FasterWhisperRuntimeRequestV1,
    parse_runtime_capability_observation,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


T0 = "2026-09-19T12:00:00Z"
T1 = "2026-09-19T12:00:01Z"
T5 = "2026-09-19T12:05:00Z"
CAPABILITY_PAIRS = {("cpu", "int8"), ("cuda", "float16")}


class RecordingProbe:
    def __init__(self, values: dict[tuple[str, str], object]) -> None:
        self.values = values
        self.calls: list[tuple[str, str]] = []
        self.effect_count = 0

    def supports(self, device: str, compute_type: str) -> object:
        self.effect_count += 1
        self.calls.append((device, compute_type))
        value = self.values[(device, compute_type)]
        if isinstance(value, BaseException):
            raise value
        return value


class MissingSupports:
    pass


class RaisingSupportsProperty:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    @property
    def supports(self):
        raise RuntimeError("supports property is unavailable")


class RaisingSupportsGetattribute:
    def __init__(self) -> None:
        object.__setattr__(self, "calls", [])

    def __getattribute__(self, name: str):
        if name == "supports":
            raise RuntimeError("supports attribute is unavailable")
        return object.__getattribute__(self, name)


def schema_document() -> dict:
    with resources.files("ai_video_production.schema_resources").joinpath(
        "faster-whisper-runtime-contract.schema.json"
    ).open("r", encoding="utf-8") as source:
        return json.load(source)


def assert_observation_schema_valid(value: dict) -> None:
    document = schema_document()
    Draft202012Validator(document).validate(value)
    Draft202012Validator({
        "$schema": document["$schema"],
        "$defs": document["$defs"],
        "$ref": "#/$defs/observation",
    }).validate(value)


def request(device: str) -> FasterWhisperRuntimeRequestV1:
    return FasterWhisperRuntimeRequestV1.create(device)


def observation_for(
    device: str,
    probe_outcome: str,
    cpu_capability: str,
    cuda_capability: str,
    *,
    expires_at: str = T5,
) -> FasterWhisperRuntimeCapabilityObservationV1:
    return FasterWhisperRuntimeCapabilityObservationV1.create(
        request=request(device),
        probe_outcome=probe_outcome,
        cpu_capability=cpu_capability,
        cuda_capability=cuda_capability,
        observed_at=T0,
        expires_at=expires_at,
    )


def test_observation_schema_hash_mirror_round_trip_and_private_flags() -> None:
    observation = observation_for("auto", "OBSERVED", "AVAILABLE", "UNAVAILABLE")
    value = observation.to_dict()
    assert_observation_schema_valid(value)
    assert observation.record_sha256 == sha256_bytes(
        OBSERVATION_DOMAIN
        + canonical_json_bytes({key: item for key, item in value.items() if key != "record_sha256"})
    )
    restored = parse_runtime_capability_observation(value, request=request("auto"))
    assert restored.to_dict() == value
    assert canonical_json_bytes(restored.to_dict()) == canonical_json_bytes(value)
    assert value["model_load_started"] is False
    assert value["inference_started"] is False
    assert value["network_used"] is False
    assert value["model_download_authorized"] is False


@pytest.mark.parametrize("field,value", [
    ("cpu_capability", "UNAVAILABLE"),
    ("record_sha256", "sha256:" + "0" * 64),
    ("runtime_request_sha256", "sha256:" + "1" * 64),
])
def test_observation_tamper_is_rejected_even_when_shape_remains_valid(field: str, value: str) -> None:
    observation = observation_for("cpu", "OBSERVED", "AVAILABLE", "NOT_PROBED")
    tampered = copy.deepcopy(observation.to_dict())
    tampered[field] = value
    with pytest.raises(ValueError):
        parse_runtime_capability_observation(tampered, request=request("cpu"))


def test_observation_unknown_fields_and_execution_effects_are_unrepresentable() -> None:
    observation = observation_for("cuda", "OBSERVED", "NOT_PROBED", "AVAILABLE")
    for extra in (
        {"source_path": "C:\\private\\voice.wav"},
        {"provider": "FasterWhisperProvider"},
        {"network_used": True},
        {"model_load_started": True},
        {"inference_started": True},
        {"model_download_authorized": True},
    ):
        tampered = observation.to_dict() | extra
        with pytest.raises(ValueError):
            parse_runtime_capability_observation(tampered, request=request("cuda"))


def test_observation_requires_the_same_validated_request_object_semantics() -> None:
    cpu = request("cpu")
    cuda = request("cuda")
    observation = FasterWhisperRuntimeCapabilityObservationV1.create(
        request=cpu,
        probe_outcome="OBSERVED",
        cpu_capability="AVAILABLE",
        cuda_capability="NOT_PROBED",
        observed_at=T0,
        expires_at=T5,
    )
    with pytest.raises(ValueError):
        parse_runtime_capability_observation(observation.to_dict(), request=cuda)
    with pytest.raises(TypeError):
        parse_runtime_capability_observation(observation.to_dict(), request=object())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        FasterWhisperRuntimeCapabilityObservationV1.create(
            request=cpu.record_sha256,  # type: ignore[arg-type]
            probe_outcome="OBSERVED",
            cpu_capability="AVAILABLE",
            cuda_capability="NOT_PROBED",
            observed_at=T0,
            expires_at=T5,
        )


@pytest.mark.parametrize(
    "device,probe_outcome,cpu_capability,cuda_capability",
    [
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
    ],
)
def test_all_request_specific_observation_rows_are_schema_and_runtime_valid(
    device: str, probe_outcome: str, cpu_capability: str, cuda_capability: str,
) -> None:
    observation = observation_for(device, probe_outcome, cpu_capability, cuda_capability)
    assert_observation_schema_valid(observation.to_dict())
    assert parse_runtime_capability_observation(
        observation.to_dict(), request=request(device)
    ).to_dict() == observation.to_dict()


@pytest.mark.parametrize("device", ["cpu", "cuda", "auto"])
@pytest.mark.parametrize("ttl_seconds", [1, 300])
def test_preflight_accepts_exact_ttl_boundaries(device: str, ttl_seconds: int) -> None:
    probe = RecordingProbe({("cpu", "int8"): True, ("cuda", "float16"): True})
    observation, decision = preflight.evaluate_runtime_preflight(
        request(device), probe, observed_at=T0, ttl_seconds=ttl_seconds
    )
    assert observation.expires_at == (T1 if ttl_seconds == 1 else T5)
    assert decision.issued_at == observation.observed_at
    assert decision.expires_at == observation.expires_at


@pytest.mark.parametrize("ttl_seconds", [0, 301, True, 1.0, "1"])
def test_preflight_rejects_invalid_ttl_without_probe_effect(ttl_seconds: object) -> None:
    probe = RecordingProbe({("cpu", "int8"): True, ("cuda", "float16"): True})
    with pytest.raises(ValueError):
        preflight.collect_runtime_capability_observation(
            request("cpu"), probe, observed_at=T0, ttl_seconds=ttl_seconds  # type: ignore[arg-type]
        )
    assert probe.calls == []
    assert probe.effect_count == 0


@pytest.mark.parametrize("device", ["cpu", "cuda", "auto"])
def test_observation_and_decision_freshness_is_issued_inclusive_and_expiry_exclusive(device: str) -> None:
    probe = RecordingProbe({("cpu", "int8"): True, ("cuda", "float16"): True})
    observation, decision = preflight.evaluate_runtime_preflight(
        request(device), probe, observed_at=T0, ttl_seconds=300
    )
    assert observation.is_fresh_at(T0) is True
    assert observation.is_fresh_at(T5) is False
    assert decision.is_fresh_at(T0) is True
    assert decision.is_fresh_at(T5) is False


@pytest.mark.parametrize(
    "device,values,expected_calls,expected_observation,expected_decision",
    [
        ("cpu", {("cpu", "int8"): True}, [("cpu", "int8")],
         ("OBSERVED", "AVAILABLE", "NOT_PROBED"), ("READY_CPU", "REQUESTED_CPU_AVAILABLE", False)),
        ("cpu", {("cpu", "int8"): False}, [("cpu", "int8")],
         ("OBSERVED", "UNAVAILABLE", "NOT_PROBED"), ("BLOCKED", "CPU_UNAVAILABLE", False)),
        ("cuda", {("cuda", "float16"): True}, [("cuda", "float16")],
         ("OBSERVED", "NOT_PROBED", "AVAILABLE"), ("READY_CUDA", "REQUESTED_CUDA_AVAILABLE", False)),
        ("cuda", {("cuda", "float16"): False}, [("cuda", "float16")],
         ("OBSERVED", "NOT_PROBED", "UNAVAILABLE"), ("BLOCKED", "CUDA_UNAVAILABLE", False)),
        ("auto", {("cuda", "float16"): True, ("cpu", "int8"): False}, [("cuda", "float16")],
         ("OBSERVED", "NOT_PROBED", "AVAILABLE"), ("READY_CUDA", "AUTO_CUDA_AVAILABLE", False)),
        ("auto", {("cuda", "float16"): False, ("cpu", "int8"): True}, [("cuda", "float16"), ("cpu", "int8")],
         ("OBSERVED", "AVAILABLE", "UNAVAILABLE"), ("READY_CPU", "AUTO_CUDA_UNAVAILABLE_CPU_AVAILABLE", True)),
        ("auto", {("cuda", "float16"): False, ("cpu", "int8"): False}, [("cuda", "float16"), ("cpu", "int8")],
         ("OBSERVED", "UNAVAILABLE", "UNAVAILABLE"), ("BLOCKED", "AUTO_NO_RUNTIME_AVAILABLE", False)),
    ],
)
def test_exact_probe_pairs_order_and_unique_decision(
    device: str,
    values: dict[tuple[str, str], object],
    expected_calls: list[tuple[str, str]],
    expected_observation: tuple[str, str, str],
    expected_decision: tuple[str, str, bool],
) -> None:
    probe = RecordingProbe(values)
    req = request(device)
    observation, decision = preflight.evaluate_runtime_preflight(
        req, probe, observed_at=T0, ttl_seconds=300
    )
    assert probe.calls == expected_calls
    assert set(probe.calls) <= CAPABILITY_PAIRS
    assert (observation.probe_outcome, observation.cpu_capability, observation.cuda_capability) == expected_observation
    assert (decision.outcome, decision.reason_code, decision.fallback_applied) == expected_decision
    assert decision.runtime_request_sha256 == req.record_sha256
    assert decision.capability_observation_sha256 == observation.record_sha256
    assert (decision.issued_at, decision.expires_at) == (observation.observed_at, observation.expires_at)


@pytest.mark.parametrize(
    "device,values,expected_outcome,expected_reason,expected_calls",
    [
        ("cpu", {("cpu", "int8"): RuntimeError("cpu")}, "BLOCKED", "RUNTIME_PROBE_UNAVAILABLE", [("cpu", "int8")]),
        ("cuda", {("cuda", "float16"): RuntimeError("cuda")}, "BLOCKED", "RUNTIME_PROBE_UNAVAILABLE", [("cuda", "float16")]),
        ("auto", {("cuda", "float16"): RuntimeError("cuda"), ("cpu", "int8"): True}, "BLOCKED", "RUNTIME_PROBE_UNAVAILABLE", [("cuda", "float16")]),
        ("auto", {("cuda", "float16"): False, ("cpu", "int8"): RuntimeError("cpu")}, "BLOCKED", "RUNTIME_PROBE_UNAVAILABLE", [("cuda", "float16"), ("cpu", "int8")]),
    ],
)
def test_probe_exceptions_are_blocked_and_never_fallback(
    device: str, values: dict[tuple[str, str], object], expected_outcome: str,
    expected_reason: str, expected_calls: list[tuple[str, str]],
) -> None:
    probe = RecordingProbe(values)
    observation, decision = preflight.evaluate_runtime_preflight(
        request(device), probe, observed_at=T0, ttl_seconds=300
    )
    assert probe.calls == expected_calls
    assert decision.outcome == expected_outcome
    assert decision.reason_code == expected_reason
    assert decision.fallback_applied is False
    assert observation.cpu_capability != "AVAILABLE"


@pytest.mark.parametrize(
    "device,values,expected_reason,expected_calls",
    [
        ("cpu", {("cpu", "int8"): "yes"}, "RUNTIME_PROBE_INVALID", [("cpu", "int8")]),
        ("cuda", {("cuda", "float16"): 1}, "RUNTIME_PROBE_INVALID", [("cuda", "float16")]),
        ("auto", {("cuda", "float16"): "yes", ("cpu", "int8"): True}, "RUNTIME_PROBE_INVALID", [("cuda", "float16")]),
        ("auto", {("cuda", "float16"): False, ("cpu", "int8"): 1}, "RUNTIME_PROBE_INVALID", [("cuda", "float16"), ("cpu", "int8")]),
    ],
)
def test_non_boolean_probe_results_are_invalid_blocked_and_never_fallback(
    device: str, values: dict[tuple[str, str], object], expected_reason: str,
    expected_calls: list[tuple[str, str]],
) -> None:
    probe = RecordingProbe(values)
    observation, decision = preflight.evaluate_runtime_preflight(
        request(device), probe, observed_at=T0, ttl_seconds=300
    )
    assert probe.calls == expected_calls
    assert observation.probe_outcome == "RUNTIME_PROBE_INVALID"
    assert decision.outcome == "BLOCKED"
    assert decision.reason_code == expected_reason
    assert decision.fallback_applied is False


def test_missing_supports_is_invalid_without_any_external_effect() -> None:
    req = request("auto")
    observation, decision = preflight.evaluate_runtime_preflight(
        req, MissingSupports(), observed_at=T0, ttl_seconds=300  # type: ignore[arg-type]
    )
    assert observation.probe_outcome == "RUNTIME_PROBE_INVALID"
    assert observation.cpu_capability == "NOT_PROBED"
    assert observation.cuda_capability == "UNKNOWN"
    assert decision.outcome == "BLOCKED"
    assert decision.fallback_applied is False


@pytest.mark.parametrize("probe_type", [RaisingSupportsProperty, RaisingSupportsGetattribute])
def test_supports_lookup_exception_is_invalid_blocked_and_does_not_call_auto_cpu(probe_type) -> None:
    """A broken probe object must never escape as a raw exception or enable fallback."""
    probe = probe_type()
    observation, decision = preflight.evaluate_runtime_preflight(
        request("auto"), probe, observed_at=T0, ttl_seconds=300
    )
    assert observation.probe_outcome == "RUNTIME_PROBE_INVALID"
    assert observation.cpu_capability == "NOT_PROBED"
    assert observation.cuda_capability == "UNKNOWN"
    assert decision.outcome == "BLOCKED"
    assert decision.reason_code == "RUNTIME_PROBE_INVALID"
    assert decision.fallback_applied is False
    assert probe.calls == []


def test_invalid_internal_pair_is_fail_closed() -> None:
    probe = RecordingProbe({})
    assert preflight._probe(probe, ("cuda", "int8")) == ("RUNTIME_PROBE_INVALID", None)
    assert probe.calls == []
    assert probe.effect_count == 0


_ALLOWED_OBSERVATION_ROWS = {
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


def _valid_observation_base(device: str) -> dict:
    values = {
        "cpu": ("OBSERVED", "AVAILABLE", "NOT_PROBED"),
        "cuda": ("OBSERVED", "NOT_PROBED", "AVAILABLE"),
        "auto": ("OBSERVED", "NOT_PROBED", "AVAILABLE"),
    }
    probe_outcome, cpu_capability, cuda_capability = values[device]
    return observation_for(
        device, probe_outcome, cpu_capability, cuda_capability
    ).to_dict()


def _schema_valid_request_specific_forbidden_rows() -> list[tuple[str, str, str, str]]:
    """Enumerate every globally schema-valid row outside the request-specific matrix."""
    rows: list[tuple[str, str, str, str]] = []
    for device in ("cpu", "cuda", "auto"):
        base = _valid_observation_base(device)
        for probe_outcome in ("OBSERVED", "RUNTIME_PROBE_UNAVAILABLE", "RUNTIME_PROBE_INVALID"):
            for cpu_capability in ("AVAILABLE", "UNAVAILABLE", "NOT_PROBED", "UNKNOWN"):
                for cuda_capability in ("AVAILABLE", "UNAVAILABLE", "NOT_PROBED", "UNKNOWN"):
                    row = (device, probe_outcome, cpu_capability, cuda_capability)
                    if row in _ALLOWED_OBSERVATION_ROWS:
                        continue
                    candidate = base | {
                        "probe_outcome": probe_outcome,
                        "cpu_capability": cpu_capability,
                        "cuda_capability": cuda_capability,
                    }
                    try:
                        assert_observation_schema_valid(candidate)
                    except Exception:
                        continue
                    rows.append(row)
    return rows


_FORBIDDEN_REQUEST_SPECIFIC_ROWS = _schema_valid_request_specific_forbidden_rows()


def test_forbidden_request_specific_row_inventory_is_exact() -> None:
    assert len(_FORBIDDEN_REQUEST_SPECIFIC_ROWS) == 21
    assert len(set(_FORBIDDEN_REQUEST_SPECIFIC_ROWS)) == 21


@pytest.mark.parametrize("device,probe_outcome,cpu_capability,cuda_capability", _FORBIDDEN_REQUEST_SPECIFIC_ROWS)
def test_schema_valid_but_request_specific_forbidden_rows_are_rejected(
    device: str, probe_outcome: str, cpu_capability: str, cuda_capability: str,
) -> None:
    base = _valid_observation_base(device)
    candidate = base | {
        "probe_outcome": probe_outcome,
        "cpu_capability": cpu_capability,
        "cuda_capability": cuda_capability,
    }
    candidate["record_sha256"] = sha256_bytes(
        OBSERVATION_DOMAIN
        + canonical_json_bytes({key: item for key, item in candidate.items() if key != "record_sha256"})
    )
    assert_observation_schema_valid(candidate)
    with pytest.raises(ValueError):
        parse_runtime_capability_observation(candidate, request=request(device))


def test_resolver_rejects_observation_bound_to_a_different_request() -> None:
    cpu = request("cpu")
    cuda = request("cuda")
    observation = FasterWhisperRuntimeCapabilityObservationV1.create(
        request=cpu,
        probe_outcome="OBSERVED",
        cpu_capability="AVAILABLE",
        cuda_capability="NOT_PROBED",
        observed_at=T0,
        expires_at=T5,
    )
    with pytest.raises(ValueError):
        preflight.resolve_runtime_decision(cuda, observation)


def test_recomputed_digest_cannot_relabel_a_schema_valid_row_for_another_request() -> None:
    cpu = request("cpu")
    auto = request("auto")
    original = FasterWhisperRuntimeCapabilityObservationV1.create(
        request=cpu,
        probe_outcome="OBSERVED",
        cpu_capability="AVAILABLE",
        cuda_capability="NOT_PROBED",
        observed_at=T0,
        expires_at=T5,
    )
    candidate = original.to_dict() | {"runtime_request_sha256": auto.record_sha256}
    candidate["record_sha256"] = sha256_bytes(
        OBSERVATION_DOMAIN
        + canonical_json_bytes({key: item for key, item in candidate.items() if key != "record_sha256"})
    )
    assert_observation_schema_valid(candidate)
    with pytest.raises(ValueError):
        parse_runtime_capability_observation(candidate, request=auto)


@pytest.mark.parametrize("device", ["cpu", "cuda", "auto"])
def test_explicit_device_does_not_cross_probe_and_auto_fallback_is_unique(device: str) -> None:
    probe = RecordingProbe({("cpu", "int8"): True, ("cuda", "float16"): False})
    observation, decision = preflight.evaluate_runtime_preflight(
        request(device), probe, observed_at=T0, ttl_seconds=300
    )
    if device == "cpu":
        assert probe.calls == [("cpu", "int8")]
        assert decision.effective_device == "cpu"
        assert decision.fallback_applied is False
    elif device == "cuda":
        assert probe.calls == [("cuda", "float16")]
        assert decision.outcome == "BLOCKED"
        assert decision.fallback_applied is False
    else:
        assert probe.calls == [("cuda", "float16"), ("cpu", "int8")]
        assert decision.effective_device == "cpu"
        assert decision.fallback_applied is True
    assert all(pair in CAPABILITY_PAIRS for pair in probe.calls)
    assert observation.model_load_started is False
    assert observation.inference_started is False
    assert observation.network_used is False
    assert observation.model_download_authorized is False
