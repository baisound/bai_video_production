from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from importlib import resources
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.task047_capture_source_transport_receipts import (
    ParsedCaptureReceipt,
    Task047ReceiptError,
    parse_source_transport_receipt,
    validate_source_transport_pair,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_NAME = "task047-capture-source-transport-receipts.schema.json"
SOURCE_DOMAIN = b"TASK047_CAPTURE_SOURCE_CURRENTNESS_V1\0INITIAL\0"
TRANSPORT_DOMAIN = b"TASK047_CAPTURE_TRANSPORT_INTEGRITY_V2\0"


def _hash(value: str) -> str:
    return sha256(value.encode("ascii")).hexdigest()


def _with_digest(record: dict) -> dict:
    copy = dict(record)
    copy.pop("receipt_sha256", None)
    domain = SOURCE_DOMAIN if copy["record_type"] == "CaptureSourceCurrentnessReceiptV1" else TRANSPORT_DOMAIN
    preimage = json.dumps(copy, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    copy["receipt_sha256"] = sha256(domain + preimage).hexdigest()
    return copy


def _source() -> dict:
    return _with_digest({
        "record_type": "CaptureSourceCurrentnessReceiptV1",
        "schema_version": 1,
        "project_id": "project-1",
        "recording_session_id": "session-1",
        "segment_attempt_id": "attempt-1",
        "operation_id": "capture:1",
        "idempotency_key": "idem-1",
        "owner_subject_binding_sha256": _hash("subject"),
        "consent_evaluation_sha256": _hash("consent"),
        "producer_code_sha256": _hash("code"),
        "runtime_sha256": _hash("runtime"),
        "trusted_time_binding_sha256": _hash("time"),
        "capture_job_id": "job-1",
        "capture_job_revision_sha256": _hash("revision"),
        "capture_job_predecessor_readback_sha256": _hash("predecessor"),
        "created_at": "2026-09-23T01:00:00.000000Z",
        "observed_at": "2026-09-23T01:00:01.000000Z",
        "fresh_until": "2026-09-23T01:10:00.000000Z",
        "predecessor_receipt_sha256": None,
        "source_binding_sha256": _hash("source"),
        "obs_build_sha256": _hash("build"),
        "obs_process_identity_sha256": _hash("process"),
        "source_graph_sha256": _hash("graph"),
        "source_sample_format": "FLOAT32_PLANAR",
        "source_sample_rate_hz": 48000,
        "source_channel_count": 2,
        "measurement_point": "POST_FILTER",
        "source_classification": "OWNER_SELECTED_ISOLATED_MIC",
        "source_currentness_state": "BOUND_VERIFIED",
    })


def _transport(source: dict | None = None) -> dict:
    source = _source() if source is None else source
    return _with_digest({
        **{key: source[key] for key in (
            "project_id", "recording_session_id", "segment_attempt_id", "operation_id",
            "idempotency_key", "owner_subject_binding_sha256", "consent_evaluation_sha256",
            "producer_code_sha256", "runtime_sha256", "trusted_time_binding_sha256",
            "capture_job_id", "capture_job_revision_sha256",
            "capture_job_predecessor_readback_sha256", "fresh_until",
        )},
        "record_type": "CaptureTransportIntegrityReceiptV2",
        "schema_version": 2,
        "created_at": "2026-09-23T01:00:02.000000Z",
        "observed_at": "2026-09-23T01:00:03.000000Z",
        "predecessor_receipt_sha256": source["receipt_sha256"],
        "source_receipt_sha256": source["receipt_sha256"],
        "hmac_key_epoch_sha256": _hash("epoch"),
        "first_packet_sequence": 10,
        "last_packet_sequence": 11,
        "observed_packet_count": 2,
        "accepted_packet_count": 2,
        "source_frame_count": 960,
        "source_sample_count": 1920,
        "first_source_timestamp_ns": 1000000,
        "last_source_timestamp_ns": 1020000,
        "gap_count": 0,
        "duplicate_count": 0,
        "reorder_count": 0,
        "overrun_count": 0,
        "reconnect_count": 0,
        "nonfinite_sample_count": 0,
        "transport_verification_state": "BOUND_VERIFIED",
    })


def _wire(record: dict) -> bytes:
    return json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _assert_code(raw: bytes | str, code: str) -> None:
    with pytest.raises(Task047ReceiptError) as exc:
        parse_source_transport_receipt(raw)
    assert exc.value.code == code
    assert str(exc.value) == code


def test_schema_is_valid_and_mirror_is_byte_identical() -> None:
    canonical = (ROOT / "schemas" / SCHEMA_NAME).read_bytes()
    packaged = resources.files("ai_video_production.schema_resources").joinpath(SCHEMA_NAME).read_bytes()
    assert canonical == packaged
    Draft202012Validator.check_schema(json.loads(canonical))


def test_valid_pair_is_structural_only_and_digest_is_independently_recomputed() -> None:
    source = _source()
    transport = _transport(source)
    parsed_source = parse_source_transport_receipt(_wire(source))
    parsed_transport = parse_source_transport_receipt(_wire(transport))
    assert parsed_source.receipt_sha256 == source["receipt_sha256"]
    assert parsed_transport.receipt_sha256 == transport["receipt_sha256"]
    assert parsed_source.assessment == "STRUCTURAL_VALID_ONLY"
    assert validate_source_transport_pair(parsed_source, parsed_transport) == "STRUCTURAL_VALID_ONLY"
    with pytest.raises(TypeError):
        parsed_source.fields["project_id"] = "different"


@pytest.mark.parametrize("raw,code", [
    (b'{"record_type":1,"record_type":2}', "DUPLICATE_FIELD"),
    (b'{"value":NaN}', "NONFINITE_NUMBER"),
    (b"\xff", "INVALID_UTF8"),
    (b"{}" + b" " * (64 * 1024), "WIRE_TOO_LARGE"),
    (b"[]", "INVALID_SHAPE"),
    (b"{", "MALFORMED_JSON"),
], ids=["duplicate", "nonfinite", "invalid-utf8", "wire-too-large", "array", "malformed"])
def test_wire_rejections(raw: bytes, code: str) -> None:
    _assert_code(raw, code)


@pytest.mark.parametrize("field,value,code", [
    ("record_type", "ForeignReceiptV1", "UNSUPPORTED_VERSION"),
    ("record_type", [], "UNSUPPORTED_VERSION"),
    ("schema_version", 2, "INVALID_SHAPE"),
    ("schema_version", 1.0, "INVALID_SHAPE"),
    ("project_id", "C:\\private", "INVALID_SHAPE"),
    ("source_sample_format", "PCM24", "INVALID_SHAPE"),
    ("source_sample_rate_hz", 0, "INVALID_SHAPE"),
    ("source_sample_rate_hz", 48000.0, "INVALID_SHAPE"),
    ("source_channel_count", True, "INVALID_SHAPE"),
    ("created_at", "2026-02-30T01:00:00.000000Z", "INVALID_TIME"),
    ("fresh_until", "2026-09-23T01:00:01.000000Z", "INVALID_TIME_ORDER"),
])
def test_source_rejects_closed_contract_violations(field: str, value: object, code: str) -> None:
    source = _source()
    source[field] = value
    _assert_code(_wire(_with_digest(source)), code)


def test_unknown_field_and_digest_tampering_fail_closed() -> None:
    source = _source()
    source["private_path"] = "C:\\private\\audio.wav"
    _assert_code(_wire(_with_digest(source)), "INVALID_SHAPE")
    source = _source()
    source["source_binding_sha256"] = _hash("tampered")
    _assert_code(_wire(source), "DIGEST_MISMATCH")


@pytest.mark.parametrize("field,value,code", [
    ("source_receipt_sha256", _hash("other"), "PREDECESSOR_MISMATCH"),
    ("last_packet_sequence", 9, "PACKET_RANGE_INVALID"),
    ("accepted_packet_count", 3, "PACKET_COUNT_INVALID"),
    ("accepted_packet_count", 2.0, "INVALID_SHAPE"),
    ("last_source_timestamp_ns", 1, "SOURCE_TIME_ORDER_INVALID"),
    ("transport_verification_state", "SUCCESS", "INVALID_SHAPE"),
])
def test_transport_rejects_invalid_facts(field: str, value: object, code: str) -> None:
    transport = _transport()
    transport[field] = value
    _assert_code(_wire(_with_digest(transport)), code)


@pytest.mark.parametrize("field,value,code", [
    ("project_id", "different", "LINEAGE_MISMATCH"),
    ("recording_session_id", "different", "LINEAGE_MISMATCH"),
    ("segment_attempt_id", "different", "LINEAGE_MISMATCH"),
    ("operation_id", "different", "LINEAGE_MISMATCH"),
    ("idempotency_key", "different", "LINEAGE_MISMATCH"),
    ("owner_subject_binding_sha256", _hash("different"), "LINEAGE_MISMATCH"),
    ("consent_evaluation_sha256", _hash("different"), "LINEAGE_MISMATCH"),
    ("producer_code_sha256", _hash("different"), "LINEAGE_MISMATCH"),
    ("runtime_sha256", _hash("different"), "LINEAGE_MISMATCH"),
    ("trusted_time_binding_sha256", _hash("different"), "LINEAGE_MISMATCH"),
    ("capture_job_id", "different", "LINEAGE_MISMATCH"),
    ("capture_job_revision_sha256", _hash("different"), "LINEAGE_MISMATCH"),
    ("capture_job_predecessor_readback_sha256", _hash("different"), "LINEAGE_MISMATCH"),
    ("source_sample_count", 960, "SAMPLE_COUNT_MISMATCH"),
    ("fresh_until", "2026-09-23T01:11:00.000000Z", "FRESHNESS_EXCEEDS_SOURCE"),
])
def test_pair_rejects_cross_record_mismatch(field: str, value: object, code: str) -> None:
    source = parse_source_transport_receipt(_wire(_source()))
    transport = _transport()
    transport[field] = value
    parsed_transport = parse_source_transport_receipt(_wire(_with_digest(transport)))
    with pytest.raises(Task047ReceiptError) as exc:
        validate_source_transport_pair(source, parsed_transport)
    assert exc.value.code == code


def test_pair_rejects_transport_observation_before_source() -> None:
    source = parse_source_transport_receipt(_wire(_source()))
    transport = _transport()
    transport["created_at"] = "2026-09-23T00:59:59.000000Z"
    transport["observed_at"] = "2026-09-23T01:00:00.000000Z"
    parsed_transport = parse_source_transport_receipt(_wire(_with_digest(transport)))
    with pytest.raises(Task047ReceiptError) as exc:
        validate_source_transport_pair(source, parsed_transport)
    assert exc.value.code == "SOURCE_TIME_ORDER_INVALID"


def test_non_success_transport_remains_structural_only() -> None:
    source = parse_source_transport_receipt(_wire(_source()))
    transport = _transport()
    transport["accepted_packet_count"] = 0
    transport["source_frame_count"] = 0
    transport["source_sample_count"] = 0
    transport["gap_count"] = 1
    transport["transport_verification_state"] = "MISMATCH"
    parsed_transport = parse_source_transport_receipt(_wire(_with_digest(transport)))
    assert validate_source_transport_pair(source, parsed_transport) == "STRUCTURAL_VALID_ONLY"


def test_pair_rejects_forged_parsed_result_and_wrong_predecessor() -> None:
    source_record = _source()
    transport_record = _transport(source_record)
    source = parse_source_transport_receipt(_wire(source_record))
    transport = parse_source_transport_receipt(_wire(transport_record))
    with pytest.raises(Task047ReceiptError) as exc:
        validate_source_transport_pair(replace(source, receipt_sha256=_hash("forge")), transport)
    assert exc.value.code == "INVALID_INPUT"
    with pytest.raises(Task047ReceiptError) as exc:
        validate_source_transport_pair(replace(source, fields=None), transport)
    assert exc.value.code == "INVALID_INPUT"
    transport_record["source_receipt_sha256"] = _hash("other")
    transport_record["predecessor_receipt_sha256"] = _hash("other")
    wrong = parse_source_transport_receipt(_wire(_with_digest(transport_record)))
    with pytest.raises(Task047ReceiptError) as exc:
        validate_source_transport_pair(source, wrong)
    assert exc.value.code == "PREDECESSOR_MISMATCH"
