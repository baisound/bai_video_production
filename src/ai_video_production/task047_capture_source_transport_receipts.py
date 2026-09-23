"""Strict, non-admitting parser for TASK-047 capture source/transport receipts.

This module validates wire shape and internal lineage only. A matching digest
does not authenticate a producer or establish current recording authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib import resources
import json
import re
from types import MappingProxyType
from typing import Any, Mapping

from jsonschema import Draft202012Validator


SCHEMA_NAME = "task047-capture-source-transport-receipts.schema.json"
MAX_WIRE_BYTES = 64 * 1024
STRUCTURAL_ASSESSMENT = "STRUCTURAL_VALID_ONLY"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,99}", re.ASCII)
_HASH_RE = re.compile(r"[0-9a-f]{64}", re.ASCII)
_ID_FIELDS = (
    "project_id", "recording_session_id", "segment_attempt_id",
    "operation_id", "idempotency_key", "capture_job_id",
)
_DOMAINS = {
    "CaptureSourceCurrentnessReceiptV1": b"TASK047_CAPTURE_SOURCE_CURRENTNESS_V1\0INITIAL\0",
    "CaptureTransportIntegrityReceiptV2": b"TASK047_CAPTURE_TRANSPORT_INTEGRITY_V2\0",
}
_LINEAGE_FIELDS = (
    "project_id",
    "recording_session_id",
    "segment_attempt_id",
    "operation_id",
    "idempotency_key",
    "owner_subject_binding_sha256",
    "consent_evaluation_sha256",
    "producer_code_sha256",
    "runtime_sha256",
    "trusted_time_binding_sha256",
    "capture_job_id",
    "capture_job_revision_sha256",
    "capture_job_predecessor_readback_sha256",
)
_SOURCE_INTEGER_FIELDS = ("schema_version", "source_sample_rate_hz", "source_channel_count")
_TRANSPORT_INTEGER_FIELDS = (
    "schema_version",
    "first_packet_sequence",
    "last_packet_sequence",
    "observed_packet_count",
    "accepted_packet_count",
    "source_frame_count",
    "source_sample_count",
    "first_source_timestamp_ns",
    "last_source_timestamp_ns",
    "gap_count",
    "duplicate_count",
    "reorder_count",
    "overrun_count",
    "reconnect_count",
    "nonfinite_sample_count",
)


class Task047ReceiptError(ValueError):
    """Public-safe closed error without input details."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class ParsedCaptureReceipt:
    record_type: str
    receipt_sha256: str
    assessment: str
    fields: Mapping[str, Any]


def _fail(code: str) -> None:
    raise Task047ReceiptError(code)


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_FIELD")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    _fail("NONFINITE_NUMBER")


def _schema() -> Mapping[str, Any]:
    text = resources.files("ai_video_production.schema_resources").joinpath(
        SCHEMA_NAME
    ).read_text(encoding="utf-8")
    return json.loads(text)


_VALIDATOR = Draft202012Validator(_schema())


def _canonical_bytes(record: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            dict(record), ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        _fail("MALFORMED_RECORD")


def _digest(record: Mapping[str, Any]) -> str:
    record_type = record.get("record_type")
    if type(record_type) is not str or record_type not in _DOMAINS:
        _fail("UNSUPPORTED_VERSION")
    domain = _DOMAINS[record_type]
    body = {key: value for key, value in record.items() if key != "receipt_sha256"}
    return sha256(domain + _canonical_bytes(body)).hexdigest()


def _parse_time(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        _fail("INVALID_TIME")


def _validate_record(record: dict[str, Any]) -> ParsedCaptureReceipt:
    record_type = record.get("record_type")
    if type(record_type) is not str or record_type not in _DOMAINS:
        _fail("UNSUPPORTED_VERSION")
    if next(_VALIDATOR.iter_errors(record), None) is not None:
        _fail("INVALID_SHAPE")
    if any(type(key) is not str for key in record):
        _fail("INVALID_SHAPE")
    if any(_ID_RE.fullmatch(record[field]) is None for field in _ID_FIELDS):
        _fail("INVALID_SHAPE")
    if any(
        _HASH_RE.fullmatch(value) is None
        for key, value in record.items()
        if key.endswith("_sha256") and value is not None
    ):
        _fail("INVALID_SHAPE")
    integer_fields = (
        _SOURCE_INTEGER_FIELDS
        if record_type == "CaptureSourceCurrentnessReceiptV1"
        else _TRANSPORT_INTEGER_FIELDS
    )
    if any(type(record[field]) is not int for field in integer_fields):
        _fail("INVALID_SHAPE")
    created_at = _parse_time(record["created_at"])
    observed_at = _parse_time(record["observed_at"])
    fresh_until = _parse_time(record["fresh_until"])
    if not created_at <= observed_at < fresh_until:
        _fail("INVALID_TIME_ORDER")
    if record["receipt_sha256"] != _digest(record):
        _fail("DIGEST_MISMATCH")
    if record_type == "CaptureTransportIntegrityReceiptV2":
        if record["source_receipt_sha256"] != record["predecessor_receipt_sha256"]:
            _fail("PREDECESSOR_MISMATCH")
        if record["last_packet_sequence"] < record["first_packet_sequence"]:
            _fail("PACKET_RANGE_INVALID")
        if record["accepted_packet_count"] > record["observed_packet_count"]:
            _fail("PACKET_COUNT_INVALID")
        if record["accepted_packet_count"] > (
            record["last_packet_sequence"] - record["first_packet_sequence"] + 1
        ):
            _fail("PACKET_COUNT_INVALID")
        if record["last_source_timestamp_ns"] < record["first_source_timestamp_ns"]:
            _fail("SOURCE_TIME_ORDER_INVALID")
    return ParsedCaptureReceipt(
        record_type=record_type,
        receipt_sha256=record["receipt_sha256"],
        assessment=STRUCTURAL_ASSESSMENT,
        fields=MappingProxyType(record),
    )


def parse_source_transport_receipt(raw: bytes | str) -> ParsedCaptureReceipt:
    """Parse a body-free receipt without admitting it as current or authentic."""

    if type(raw) is bytes:
        if len(raw) > MAX_WIRE_BYTES:
            _fail("WIRE_TOO_LARGE")
        try:
            text = raw.decode("utf-8", "strict")
        except UnicodeError:
            _fail("INVALID_UTF8")
    elif type(raw) is str:
        try:
            size = len(raw.encode("utf-8", "strict"))
        except UnicodeError:
            _fail("INVALID_UTF8")
        if size > MAX_WIRE_BYTES:
            _fail("WIRE_TOO_LARGE")
        text = raw
    else:
        _fail("INVALID_INPUT")
    try:
        record = json.loads(
            text, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant
        )
    except Task047ReceiptError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        _fail("MALFORMED_JSON")
    if type(record) is not dict:
        _fail("INVALID_SHAPE")
    return _validate_record(record)


def validate_source_transport_pair(
    source: ParsedCaptureReceipt, transport: ParsedCaptureReceipt,
) -> str:
    """Check two parsed records' lineage; return structural status only."""

    if type(source) is not ParsedCaptureReceipt or type(transport) is not ParsedCaptureReceipt:
        _fail("INVALID_INPUT")
    if type(source.fields) is not MappingProxyType or type(transport.fields) is not MappingProxyType:
        _fail("INVALID_INPUT")
    checked_source = _validate_record(dict(source.fields))
    checked_transport = _validate_record(dict(transport.fields))
    if (
        source.record_type != checked_source.record_type
        or source.receipt_sha256 != checked_source.receipt_sha256
        or source.assessment != STRUCTURAL_ASSESSMENT
        or transport.record_type != checked_transport.record_type
        or transport.receipt_sha256 != checked_transport.receipt_sha256
        or transport.assessment != STRUCTURAL_ASSESSMENT
    ):
        _fail("INVALID_INPUT")
    if source.record_type != "CaptureSourceCurrentnessReceiptV1" or (
        transport.record_type != "CaptureTransportIntegrityReceiptV2"
    ):
        _fail("PAIR_TYPE_MISMATCH")
    if transport.fields["predecessor_receipt_sha256"] != source.receipt_sha256:
        _fail("PREDECESSOR_MISMATCH")
    if any(source.fields[key] != transport.fields[key] for key in _LINEAGE_FIELDS):
        _fail("LINEAGE_MISMATCH")
    if transport.fields["source_sample_count"] != (
        transport.fields["source_frame_count"] * source.fields["source_channel_count"]
    ):
        _fail("SAMPLE_COUNT_MISMATCH")
    source_observed = _parse_time(source.fields["observed_at"])
    if _parse_time(transport.fields["created_at"]) < source_observed:
        _fail("SOURCE_TIME_ORDER_INVALID")
    if _parse_time(transport.fields["fresh_until"]) > _parse_time(
        source.fields["fresh_until"]
    ):
        _fail("FRESHNESS_EXCEEDS_SOURCE")
    return STRUCTURAL_ASSESSMENT
