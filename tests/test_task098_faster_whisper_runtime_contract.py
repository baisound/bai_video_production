from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from importlib import resources
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.faster_whisper_runtime_contract import (
    DECISION_DOMAIN,
    REQUEST_DOMAIN,
    FasterWhisperRuntimeDecisionV1,
    FasterWhisperRuntimeRequestV1,
    parse_runtime_decision,
    parse_runtime_request,
    validate_runtime_pair,
    validate_schema_mirror,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


CAPABILITY = "sha256:" + "c" * 64
OTHER_CAPABILITY = "sha256:" + "d" * 64
T0 = "2026-09-19T12:00:00Z"


def schema_document() -> dict:
    with resources.files("ai_video_production.schema_resources").joinpath(
        "faster-whisper-runtime-contract.schema.json"
    ).open("r", encoding="utf-8") as source:
        return json.load(source)


def assert_schema_valid(definition: str, value: dict) -> None:
    document = schema_document()
    validator = Draft202012Validator({
        "$schema": document["$schema"],
        "$defs": document["$defs"],
        "$ref": f"#/$defs/{definition}",
    })
    validator.validate(value)


def assert_schema_invalid(definition: str, value: dict) -> None:
    document = schema_document()
    with pytest.raises(Exception):
        validator = Draft202012Validator({
            "$schema": document["$schema"],
            "$defs": document["$defs"],
            "$ref": f"#/$defs/{definition}",
        })
        validator.validate(value)


def decision_for(request, outcome, reason, *, issued_at=T0, expires_at="2026-09-19T12:05:00Z", capability=CAPABILITY):
    return FasterWhisperRuntimeDecisionV1.create(
        request=request,
        outcome=outcome,
        reason_code=reason,
        capability_observation_sha256=capability,
        issued_at=issued_at,
        expires_at=expires_at,
    )


def test_schema_mirror_is_byte_identical_and_both_records_round_trip() -> None:
    validate_schema_mirror()
    root = Path(__file__).parents[1]
    assert (root / "schemas/faster-whisper-runtime-contract.schema.json").read_bytes() == (
        root / "src/ai_video_production/schema_resources/faster-whisper-runtime-contract.schema.json"
    ).read_bytes()

    request = FasterWhisperRuntimeRequestV1.create("auto")
    restored_request = parse_runtime_request(json.loads(json.dumps(request.to_dict())))
    assert restored_request.to_dict() == request.to_dict()
    assert canonical_json_bytes(restored_request.to_dict()) == canonical_json_bytes(request.to_dict())

    decision = decision_for(request, "READY_CPU", "AUTO_CUDA_UNAVAILABLE_CPU_AVAILABLE")
    restored_decision = parse_runtime_decision(json.loads(json.dumps(decision.to_dict())), request=request)
    assert restored_decision.to_dict() == decision.to_dict()
    assert canonical_json_bytes(restored_decision.to_dict()) == canonical_json_bytes(decision.to_dict())


def test_canonical_schema_root_validates_request_and_decision() -> None:
    document = schema_document()
    request = FasterWhisperRuntimeRequestV1.create("cpu")
    decision = decision_for(request, "READY_CPU", "REQUESTED_CPU_AVAILABLE")
    Draft202012Validator(document).validate(request.to_dict())
    Draft202012Validator(document).validate(decision.to_dict())


def test_public_projection_defs_validate_and_omit_private_fields() -> None:
    request = FasterWhisperRuntimeRequestV1.create("auto")
    decision = decision_for(request, "READY_CPU", "AUTO_CUDA_UNAVAILABLE_CPU_AVAILABLE")
    assert_schema_valid("request_public_projection", request.to_public_dict())
    assert_schema_valid("decision_public_projection", decision.to_public_dict())
    assert "record_sha256" not in decision.to_public_dict()
    assert "issued_at" not in decision.to_public_dict()


@pytest.mark.parametrize("field,value", [
    ("reason_code", "CUDA_UNAVAILABLE"),
    ("outcome", "READY_CUDA"),
    ("effective_device", "cuda"),
    ("effective_compute_type", "float16"),
    ("fallback_applied", True),
])
def test_schema_rejects_invalid_private_and_public_decision_cross_products(field, value) -> None:
    request = FasterWhisperRuntimeRequestV1.create("cpu")
    decision = decision_for(request, "READY_CPU", "REQUESTED_CPU_AVAILABLE")
    private = decision.to_dict()
    private[field] = value
    assert_schema_invalid("decision", private)
    public = decision.to_public_dict()
    public[field] = value
    assert_schema_invalid("decision_public_projection", public)


def test_request_digest_is_domain_separated_and_exact() -> None:
    request = FasterWhisperRuntimeRequestV1.create("cpu")
    body = {key: value for key, value in request.to_dict().items() if key != "record_sha256"}
    expected = sha256_bytes(REQUEST_DOMAIN + canonical_json_bytes(body))
    assert request.record_sha256 == expected
    assert request.record_sha256 != sha256_bytes(DECISION_DOMAIN + canonical_json_bytes(body))


def test_decision_digest_is_domain_separated_and_exact() -> None:
    request = FasterWhisperRuntimeRequestV1.create("cuda")
    decision = decision_for(request, "READY_CUDA", "REQUESTED_CUDA_AVAILABLE")
    body = {key: value for key, value in decision.to_dict().items() if key != "record_sha256"}
    assert decision.record_sha256 == sha256_bytes(DECISION_DOMAIN + canonical_json_bytes(body))
    assert decision.record_sha256 != sha256_bytes(REQUEST_DOMAIN + canonical_json_bytes(body))


@pytest.mark.parametrize("requested_device", ["cpu", "cuda", "auto"])
def test_complete_closed_outcome_matrix(requested_device: str) -> None:
    cases = {
        "cpu": [("READY_CPU", "REQUESTED_CPU_AVAILABLE", "cpu", "int8", False),
                ("BLOCKED", "CPU_UNAVAILABLE", None, None, False)],
        "cuda": [("READY_CUDA", "REQUESTED_CUDA_AVAILABLE", "cuda", "float16", False),
                 ("BLOCKED", "CUDA_UNAVAILABLE", None, None, False)],
        "auto": [("READY_CUDA", "AUTO_CUDA_AVAILABLE", "cuda", "float16", False),
                 ("READY_CPU", "AUTO_CUDA_UNAVAILABLE_CPU_AVAILABLE", "cpu", "int8", True),
                 ("BLOCKED", "AUTO_NO_RUNTIME_AVAILABLE", None, None, False)],
    }
    request = FasterWhisperRuntimeRequestV1.create(requested_device)
    for outcome, reason, device, compute, fallback in cases[requested_device]:
        decision = decision_for(request, outcome, reason)
        assert (decision.effective_device, decision.effective_compute_type, decision.fallback_applied) == (device, compute, fallback)


@pytest.mark.parametrize("requested_device", ["cpu", "cuda", "auto"])
@pytest.mark.parametrize("reason", ["RUNTIME_PROBE_UNAVAILABLE", "RUNTIME_PROBE_INVALID"])
def test_probe_error_matrix_is_closed_and_blocked(requested_device: str, reason: str) -> None:
    request = FasterWhisperRuntimeRequestV1.create(requested_device)
    decision = decision_for(request, "BLOCKED", reason)
    assert decision.effective_device is None
    assert decision.effective_compute_type is None
    assert decision.fallback_applied is False


@pytest.mark.parametrize(
    "requested_device,outcome,reason",
    [
        ("cpu", "READY_CUDA", "REQUESTED_CUDA_AVAILABLE"),
        ("cpu", "BLOCKED", "CUDA_UNAVAILABLE"),
        ("cuda", "READY_CPU", "REQUESTED_CPU_AVAILABLE"),
        ("cuda", "BLOCKED", "CPU_UNAVAILABLE"),
        ("auto", "READY_CPU", "REQUESTED_CPU_AVAILABLE"),
        ("auto", "READY_CUDA", "REQUESTED_CUDA_AVAILABLE"),
        ("auto", "BLOCKED", "AUTO_CUDA_UNAVAILABLE_CPU_AVAILABLE"),
        ("cpu", "READY_CPU", "RUNTIME_PROBE_INVALID"),
    ],
)
def test_invalid_cross_products_are_rejected(requested_device: str, outcome: str, reason: str) -> None:
    request = FasterWhisperRuntimeRequestV1.create(requested_device)
    with pytest.raises(ValueError):
        decision_for(request, outcome, reason)


def test_explicit_cuda_never_falls_back_and_cpu_never_claims_cuda_probe() -> None:
    cuda = FasterWhisperRuntimeRequestV1.create("cuda")
    cpu = FasterWhisperRuntimeRequestV1.create("cpu")
    with pytest.raises(ValueError):
        decision_for(cuda, "READY_CPU", "CUDA_UNAVAILABLE")
    with pytest.raises(ValueError):
        decision_for(cpu, "READY_CPU", "AUTO_CUDA_AVAILABLE")


def test_effect_and_execution_flags_are_fixed_false() -> None:
    request = FasterWhisperRuntimeRequestV1.create("cpu")
    assert request.model_download_authorized is False
    decision = decision_for(request, "READY_CPU", "REQUESTED_CPU_AVAILABLE")
    values = decision.to_dict()
    for field in ("model_load_started", "inference_started", "partial_output_present", "execution_authorized"):
        assert values[field] is False
        tampered = copy.deepcopy(values)
        tampered[field] = True
        with pytest.raises(ValueError):
            parse_runtime_decision(tampered, request=request)


@pytest.mark.parametrize("extra", [
    {"source_path": "C:\\private\\voice.wav"},
    {"transcript_body": "secret text"},
    {"exception_text": "traceback"},
    {"credential": "token"},
    {"model_locator": "C:\\models"},
    {"cache_locator": "..\\cache"},
    {"extra": {"arbitrary": True}},
])
def test_paths_bodies_credentials_and_unknown_fields_are_unrepresentable(extra: dict[str, object]) -> None:
    request = FasterWhisperRuntimeRequestV1.create("cpu")
    request_value = request.to_dict() | extra
    with pytest.raises(ValueError):
        parse_runtime_request(request_value)
    decision = decision_for(request, "READY_CPU", "REQUESTED_CPU_AVAILABLE")
    with pytest.raises(ValueError):
        parse_runtime_decision(decision.to_dict() | extra, request=request)


def test_tamper_is_rejected_even_when_shape_remains_valid() -> None:
    request = FasterWhisperRuntimeRequestV1.create("auto")
    request_value = request.to_dict()
    request_value["requested_device"] = "cuda"
    with pytest.raises(ValueError):
        parse_runtime_request(request_value)
    decision = decision_for(request, "READY_CPU", "AUTO_CUDA_UNAVAILABLE_CPU_AVAILABLE")
    decision_value = decision.to_dict()
    decision_value["fallback_applied"] = False
    with pytest.raises(ValueError):
        parse_runtime_decision(decision_value, request=request)


def test_public_projections_omit_digests_and_timestamps() -> None:
    request = FasterWhisperRuntimeRequestV1.create("auto")
    decision = decision_for(request, "READY_CUDA", "AUTO_CUDA_AVAILABLE")
    request_public = request.to_public_dict()
    decision_public = decision.to_public_dict()
    assert "record_sha256" not in request_public
    assert "record_sha256" not in decision_public
    assert "runtime_request_sha256" not in decision_public
    assert "capability_observation_sha256" not in decision_public
    assert "issued_at" not in decision_public and "expires_at" not in decision_public


@pytest.mark.parametrize("ttl", [0, 301, -1])
def test_ttl_must_be_between_one_and_three_hundred_seconds(ttl: int) -> None:
    request = FasterWhisperRuntimeRequestV1.create("cpu")
    issued = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)
    expires = issued + timedelta(seconds=ttl)
    with pytest.raises(ValueError):
        decision_for(request, "READY_CPU", "REQUESTED_CPU_AVAILABLE", expires_at=expires.strftime("%Y-%m-%dT%H:%M:%SZ"))


def test_freshness_is_issued_inclusive_and_expiry_exclusive() -> None:
    request = FasterWhisperRuntimeRequestV1.create("cpu")
    decision = decision_for(request, "READY_CPU", "REQUESTED_CPU_AVAILABLE")
    assert decision.is_fresh_at("2026-09-19T12:00:00Z") is True
    assert decision.is_fresh_at("2026-09-19T12:05:00Z") is False
    assert decision.is_fresh_at("2026-09-19T12:05:01Z") is False


def test_ttl_exact_boundaries_are_valid() -> None:
    request = FasterWhisperRuntimeRequestV1.create("cpu")
    for seconds, expires in ((1, "2026-09-19T12:00:01Z"), (300, "2026-09-19T12:05:00Z")):
        decision = decision_for(request, "READY_CPU", "REQUESTED_CPU_AVAILABLE", expires_at=expires)
        assert decision.is_fresh_at(T0) is True
        assert (datetime.fromisoformat(decision.expires_at.replace("Z", "+00:00")) - datetime.fromisoformat(T0.replace("Z", "+00:00"))).total_seconds() == seconds


def test_request_decision_pair_binding_is_exact() -> None:
    request = FasterWhisperRuntimeRequestV1.create("cpu")
    other = FasterWhisperRuntimeRequestV1.create("cuda")
    decision = decision_for(request, "READY_CPU", "REQUESTED_CPU_AVAILABLE")
    assert validate_runtime_pair(request, decision)[0].record_sha256 == request.record_sha256
    with pytest.raises(ValueError):
        validate_runtime_pair(other, decision)
    with pytest.raises(ValueError):
        validate_runtime_pair(request, decision_for(other, "READY_CUDA", "REQUESTED_CUDA_AVAILABLE"))


def test_parse_binds_cpu_digest_to_supplied_cuda_request_without_raw_device_escape() -> None:
    cpu = FasterWhisperRuntimeRequestV1.create("cpu")
    cuda = FasterWhisperRuntimeRequestV1.create("cuda")
    decision = decision_for(cpu, "READY_CPU", "REQUESTED_CPU_AVAILABLE")
    with pytest.raises(ValueError):
        parse_runtime_decision(decision.to_dict(), request=cuda)
    assert "requested_device" not in (parse_runtime_decision.__kwdefaults__ or {})
    assert "requested_device" not in (FasterWhisperRuntimeDecisionV1.from_dict.__kwdefaults__ or {})


def test_no_unvalidated_allocation_escape_hatch_exists() -> None:
    assert not hasattr(FasterWhisperRuntimeRequestV1, "_allocate_validated")
    assert not hasattr(FasterWhisperRuntimeDecisionV1, "_allocate_validated")


def test_direct_constructors_match_factory_for_valid_inputs() -> None:
    request_factory = FasterWhisperRuntimeRequestV1.create("cpu")
    request_direct = FasterWhisperRuntimeRequestV1("cpu", record_sha256=request_factory.record_sha256)
    assert request_direct.to_dict() == request_factory.to_dict()
    decision_factory = decision_for(request_factory, "READY_CPU", "REQUESTED_CPU_AVAILABLE")
    decision_direct = FasterWhisperRuntimeDecisionV1(
        request=request_factory, outcome="READY_CPU", reason_code="REQUESTED_CPU_AVAILABLE",
        capability_observation_sha256=CAPABILITY, issued_at=T0,
        expires_at="2026-09-19T12:05:00Z", record_sha256=decision_factory.record_sha256,
    )
    assert decision_direct.to_dict() == decision_factory.to_dict()


def test_public_dataclass_constructors_reject_invalid_state() -> None:
    """A frozen dataclass must not be an escape hatch around contract validation."""
    with pytest.raises((ValueError, TypeError)):
        FasterWhisperRuntimeRequestV1("not-a-device", "not-a-digest")
    with pytest.raises(ValueError):
        FasterWhisperRuntimeDecisionV1(
            request=FasterWhisperRuntimeRequestV1.create("cpu"), outcome="READY_CPU",
            reason_code="REQUESTED_CPU_AVAILABLE", capability_observation_sha256=CAPABILITY,
            issued_at=T0, expires_at="2026-09-19T12:05:00Z", record_sha256="not-a-digest",
        )
