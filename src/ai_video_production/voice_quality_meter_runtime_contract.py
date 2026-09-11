"""TASK-048 scalar-only window projection over an exclusively leased public P1 store.

This synchronous route can perform Project child integrity hashing. It supplies
neither temporal freshness nor capture/emergency scheduling guarantees. The host
must exclusively use the leased store through this controller, and explicitly
close the controller before reusing that store. JSON documents are diagnostics,
not capabilities. No Project/policy write or audio semantic decode is performed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
import json
import math
import re
import threading
from typing import Any
import uuid

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .ids import validate_project_id
from .serialization import canonical_json_bytes, sha256_bytes
from .voice_quality_meter_display_policy import (
    MeterDisplayPolicyRevision, PeakObservation, PeakObservationState,
    classify_meter_band,
)
from .voice_quality_meter_policy_store import (
    MeterPolicyProjectStore, MeterPolicyQueryContext, MeterPolicyReadResult,
    MeterPolicyReadStatus, MeterPolicySnapshot,
)

SCHEMA_NAME = "voice-quality-meter-runtime.schema.json"
SCHEMA_URI = "https://bai-video-production.local/schemas/" + SCHEMA_NAME
OBSERVATION_RECORD_TYPE = "Task048MeterRuntimeObservationV1"
REQUEST_RECORD_TYPE = "Task048MeterRuntimeWindowRequestV1"
PROJECTION_RECORD_TYPE = "Task048MeterRuntimeDecisionProjectionV1"
OBSERVATION_DOMAIN = b"TASK048_METER_RUNTIME_OBSERVATION_V1\0"
REQUEST_DOMAIN = b"TASK048_METER_RUNTIME_WINDOW_REQUEST_V1\0"
PROJECTION_DOMAIN = b"TASK048_METER_RUNTIME_DECISION_PROJECTION_V1\0"
MAX_INTEGER = 9_007_199_254_740_991
MAX_WINDOWS = 65_536
MAX_CONSUMER_EPOCHS = 4_096
MAX_SESSIONS = 64
MAX_LEASES = 64
OBSERVED_CLIP_DBFS = -0.0008686323961501121
SCOPE_LABEL = "今回の観測窓に対する方針照合"
KNOWN_CAPTURE_POINT = "TASK047_CONTROLLER_RECEIVED_FLOAT32_PRE_DRAW"

_RECORDS = {
    "observation": (OBSERVATION_RECORD_TYPE, OBSERVATION_DOMAIN, "observation_sha256", 16_384),
    "request": (REQUEST_RECORD_TYPE, REQUEST_DOMAIN, "request_sha256", 24_576),
    "projection": (PROJECTION_RECORD_TYPE, PROJECTION_DOMAIN, "projection_sha256", 49_152),
}
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_PROJECT = re.compile(r"[a-z][a-z0-9-]{2,63}")
_POLICY_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_MATCHED = MeterPolicyReadStatus.PROJECT_HEAD_MATCHED_SNAPSHOT.value
_POLICY_REASONS = {
    "NOT_BOUND": "POLICY_NOT_BOUND", "REVOKED": "POLICY_REVOKED",
    "STALE": "POLICY_STALE", "MISMATCH": "POLICY_MISMATCH",
    "RECOVERY_REQUIRED": "PROJECT_RECOVERY_REQUIRED",
    "ROLLBACK_UNCERTAIN": "PROJECT_ROLLBACK_UNCERTAIN",
    "INVALID": "POLICY_INVALID", "READBACK_FAILED": "POLICY_READBACK_FAILED",
}
_OBSERVATION_REASONS = {
    "INVALID_NUMERIC": "OBSERVATION_INVALID_NUMERIC",
    "COUNTS_UNAVAILABLE": "OBSERVATION_COUNTS_UNAVAILABLE",
    "INVALID_NONFINITE": "OBSERVATION_NONFINITE",
    "CAPTURE_POINT_UNKNOWN": "CAPTURE_POINT_UNKNOWN",
    "LOSS_REPORTED": "OBSERVATION_LOSS", "LOSS_UNKNOWN": "OBSERVATION_LOSS_UNKNOWN",
    "PAUSED": "OBSERVATION_PAUSED", "NO_INPUT": "OBSERVATION_NO_INPUT",
}
_LABELS = {
    "BELOW_TARGET": "目標未満", "TARGET": "目標範囲", "ABOVE_TARGET": "目標超過",
    "WARNING": "警告", "TRUE_CLIP": "クリップ", "UNCONFIRMED": "適正判定 未確定",
}
_AUTHORITY = dict.fromkeys((
    "authority_created", "quality_pass_issued", "capture_authorized",
    "gain_change_authorized", "hardware_or_obs_setting_changed",
    "consent_asset_training_model_authorized", "temporal_freshness_confirmed",
    "production_authorized", "provider_invoked",
    "capture_path_noninterference_confirmed", "emergency_stop_noninterference_confirmed",
), False)
_IO_BOUNDARY = {
    "audio_semantic_decode_executed": False, "audio_used_as_policy_input": False,
    "project_integrity_hash_reads_possible": True, "policy_or_project_write_executed": False,
    "capture_transport_api_invoked": False, "emergency_stop_api_invoked": False,
}
_REASONS = frozenset((
    "INVALID_JSON", "LIMIT_EXCEEDED", "SCHEMA_INVALID", "INVALID_NUMBER",
    "INVALID_OBSERVATION", "DIGEST_MISMATCH", "RECORD_TYPE_MISMATCH",
    "CONTEXT_MISMATCH", "EPOCH_MISMATCH", "IDENTITY_COLLISION", "TICKET_INVALID",
    "TICKET_CONSUMED", "WINDOW_STALE", "RUNTIME_CLOSED", "RUNTIME_BUSY",
    "SESSION_HISTORY_REGRESSION", "CAPACITY_EXHAUSTED", "INTERNAL_ERROR", "NOT_SUPPORTED",
))


class MeterRuntimeContractError(ValueError):
    """Closed safe error: never carries input, path, or provider exception text."""

    def __init__(self, reason: str) -> None:
        self.reason = reason if type(reason) is str and reason in _REASONS else "INTERNAL_ERROR"
        self.code = "ERR_TASK048_METER_RUNTIME_" + self.reason
        super().__init__(self.code)


def _fail(reason: str) -> Any:
    raise MeterRuntimeContractError(reason)


def _public(operation: Any, *args: Any) -> Any:
    # Raise outside the exception handler: no sensitive implicit exception context.
    reason = None
    try:
        return operation(*args)
    except MeterRuntimeContractError as error:
        reason = error.reason
    except Exception:
        reason = "INTERNAL_ERROR"
    raise MeterRuntimeContractError(reason)


def _integer(value: Any, minimum: int = 0, maximum: int = MAX_INTEGER) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        _fail("INVALID_NUMBER")
    return value


def _uuid(value: Any) -> str:
    if type(value) is not str or not _UUID.fullmatch(value):
        _fail("EPOCH_MISMATCH")
    return value


def _digest(value: Any) -> str:
    if type(value) is not str or not _DIGEST.fullmatch(value):
        _fail("DIGEST_MISMATCH")
    return value


def _context(document: dict[str, Any]) -> MeterPolicyQueryContext:
    if type(document) is not dict or set(document) != {
        "project_id", "session_id", "consumer_epoch", "window_sequence", "request_id",
    }:
        _fail("CONTEXT_MISMATCH")
    project = document["project_id"]
    if type(project) is not str or not _PROJECT.fullmatch(project):
        _fail("CONTEXT_MISMATCH")
    validate_project_id(project)
    _uuid(document["session_id"])
    _uuid(document["consumer_epoch"])
    _uuid(document["request_id"])
    _integer(document["window_sequence"], 1)
    return MeterPolicyQueryContext(**document)


def _snapshot(value: Any, *, schema: bool = False) -> Any:
    """Bound, exact built-in snapshot; no user conversion/iteration hooks."""
    nodes = 0
    max_depth, max_nodes, max_string = (48, 16_384, 1024) if schema else (12, 4096, 256)

    def visit(item: Any, depth: int) -> Any:
        nonlocal nodes
        nodes += 1
        if nodes > max_nodes or depth > max_depth:
            _fail("LIMIT_EXCEEDED")
        kind = type(item)
        if kind is str:
            if len(item) > max_string:
                _fail("LIMIT_EXCEEDED")
            if any(0xD800 <= ord(char) <= 0xDFFF for char in item):
                _fail("INVALID_JSON")
            return item
        if kind is dict:
            if len(item) > (16_384 if schema else 64):
                _fail("LIMIT_EXCEEDED")
            result = {}
            for key, child in item.items():
                if type(key) is not str:
                    _fail("SCHEMA_INVALID")
                result[visit(key, depth + 1)] = visit(child, depth + 1)
            return result
        if kind is list and schema:
            return [visit(child, depth + 1) for child in item]
        if item is None or kind is bool:
            return item
        if kind is int:
            if not schema:
                _integer(item)
            return item
        if kind is float:
            if not math.isfinite(item):
                _fail("INVALID_NUMBER")
            return item
        _fail("RECORD_TYPE_MISMATCH")
    return visit(value, 0)


def _preflight(text: str, *, schema: bool) -> None:
    """Lexical bounds before json.loads can build a recursive object graph."""
    maximum_depth, maximum_nodes = (48, 16_384) if schema else (12, 4096)
    stack: list[str] = []
    nodes = 0
    index = 0
    while index < len(text):
        char = text[index]
        if char in " \t\r\n,:":
            index += 1
            continue
        if char in "}]":
            if not stack or stack.pop() != ("{" if char == "}" else "["):
                _fail("INVALID_JSON")
            index += 1
            continue
        if len(stack) > maximum_depth:
            _fail("LIMIT_EXCEEDED")
        nodes += 1
        if nodes > maximum_nodes:
            _fail("LIMIT_EXCEEDED")
        if char in "{[":
            if char == "[" and not schema:
                _fail("SCHEMA_INVALID")
            stack.append(char)
            index += 1
        elif char == '"':
            index += 1
            while index < len(text):
                char = text[index]
                index += 1
                if char == "\\":
                    index += 1
                elif char == '"':
                    break
            else:
                _fail("INVALID_JSON")
        else:
            while index < len(text) and text[index] not in " \t\r\n,:{}[]":
                index += 1
    if stack:
        _fail("INVALID_JSON")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("INVALID_JSON")
        result[key] = value
    return result


def _decode(data: bytes, limit: int, *, schema: bool = False) -> dict[str, Any]:
    if type(data) is not bytes:
        _fail("RECORD_TYPE_MISMATCH")
    if len(data) > limit:
        _fail("LIMIT_EXCEEDED")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeError:
        text = None
    if text is None or text.startswith("\ufeff"):
        _fail("INVALID_JSON")
    _preflight(text, schema=schema)
    failure = False
    try:
        document = json.loads(
            text, object_pairs_hook=_pairs,
            parse_constant=lambda _value: _fail("INVALID_NUMBER"),
        )
    except (ValueError, OverflowError, RecursionError) as error:
        if isinstance(error, MeterRuntimeContractError):
            raise
        failure = True
    if failure:
        _fail("INVALID_JSON")
    if type(document) is not dict:
        _fail("RECORD_TYPE_MISMATCH")
    return _snapshot(document, schema=schema)


def _canonical(document: dict[str, Any]) -> bytes:
    # Snapshot already excludes nonfinite numbers and all non-built-in objects.
    json.dumps(document, allow_nan=False)
    return canonical_json_bytes(document)


def _hash(entrypoint: str, document: dict[str, Any]) -> str:
    _, domain, field_name, _ = _RECORDS[entrypoint]
    return sha256_bytes(domain + _canonical({k: v for k, v in document.items() if k != field_name}))


_SCHEMA_ENTRYPOINTS: dict[str, Draft202012Validator] | None = None


def _load_entrypoints() -> dict[str, Draft202012Validator]:
    with resources.files("ai_video_production.schema_resources").joinpath(SCHEMA_NAME).open("rb") as source:
        data = source.read(131_073)
    schema = _decode(data, 131_072, schema=True)
    if (schema.get("$id") != SCHEMA_URI or schema.get("$ref") != "#/$defs/projection"
            or schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"):
        _fail("SCHEMA_INVALID")

    def local(value: Any, root: bool = False) -> None:
        if type(value) is dict:
            if "$id" in value and not root:
                _fail("SCHEMA_INVALID")
            if "$dynamicRef" in value or "$recursiveRef" in value:
                _fail("SCHEMA_INVALID")
            if "$ref" in value:
                ref = value["$ref"]
                if type(ref) is not str or not ref.startswith("#/$defs/") or ref[8:] not in schema["$defs"]:
                    _fail("SCHEMA_INVALID")
            for child in value.values():
                local(child)
        elif type(value) is list:
            for child in value:
                local(child)
    local(schema, True)
    Draft202012Validator.check_schema(schema)
    result = {}
    for entrypoint in _RECORDS:
        wrapper = {
            "$schema": schema["$schema"], "$defs": schema["$defs"],
            "$ref": "#/$defs/" + entrypoint,
        }
        Draft202012Validator.check_schema(wrapper)
        result[entrypoint] = Draft202012Validator(wrapper)
    return result


def _schema(entrypoint: str, document: dict[str, Any]) -> None:
    global _SCHEMA_ENTRYPOINTS
    try:
        if _SCHEMA_ENTRYPOINTS is None:
            _SCHEMA_ENTRYPOINTS = _load_entrypoints()
        invalid = next(_SCHEMA_ENTRYPOINTS[entrypoint].iter_errors(document), None) is not None
    except (MeterRuntimeContractError, OSError, ValueError, TypeError, KeyError, SchemaError):
        invalid = True
    if invalid:
        _fail("SCHEMA_INVALID")


def _policy(document: dict[str, Any]) -> MeterDisplayPolicyRevision:
    _integer(document["schema_version"], 1, 1)
    _integer(document["policy_revision"], 1, 1024)
    if not _POLICY_REF.fullmatch(document["policy_ref"]):
        _fail("SCHEMA_INVALID")
    for name in ("target_floor_dbfs", "target_ceiling_dbfs", "warning_dbfs", "true_clip_dbfs"):
        if type(document[name]) is not float or not math.isfinite(document[name]) or document[name] > 0:
            _fail("INVALID_NUMBER")
    _digest(document["policy_revision_sha256"])
    if document["predecessor_policy_sha256"] is not None:
        _digest(document["predecessor_policy_sha256"])
    invalid = False
    try:
        policy = MeterDisplayPolicyRevision.from_dict(document)
        invalid = _canonical(policy.to_dict()) != _canonical(document)
    except (TypeError, ValueError):
        invalid = True
    if invalid:
        _fail("SCHEMA_INVALID")
    return policy


def _peak_less(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left["state"] == "LINEAR_ZERO":
        return right["state"] == "FINITE"
    if right["state"] == "LINEAR_ZERO":
        return False
    return left["value_dbfs"] < right["value_dbfs"]


def _usable(peak: dict[str, Any]) -> bool:
    return peak["state"] in {"FINITE", "LINEAR_ZERO"}


def _observation(document: dict[str, Any]) -> None:
    window, session = document["window_counts"], document["session_counts"]
    peak, rms, session_peak = (document[name] for name in ("window_peak", "window_rms", "session_peak"))
    for metric in (peak, rms, session_peak):
        if metric["state"] == "FINITE":
            if type(metric["value_dbfs"]) is not float or not math.isfinite(metric["value_dbfs"]):
                _fail("INVALID_NUMBER")
        elif metric["value_dbfs"] is not None:
            _fail("INVALID_OBSERVATION")
    for counts, metrics in ((window, (peak, rms)), (session, (session_peak,))):
        if counts["state"] != "VALID":
            if any(value is not None for key, value in counts.items() if key != "state"):
                _fail("INVALID_OBSERVATION")
            continue
        for name, value in counts.items():
            if name != "state":
                _integer(value)
        finite, clips = counts["finite_sample_values"], counts["clip_sample_values"]
        if clips > finite:
            _fail("INVALID_OBSERVATION")
        for metric in metrics:
            if (finite == 0 and metric["state"] not in {"NO_VALUE", "INVALID", "OVERFLOW"}
                    or finite > 0 and metric["state"] == "NO_VALUE"):
                _fail("INVALID_OBSERVATION")
        if metrics[0]["state"] == "LINEAR_ZERO" and clips != 0:
            _fail("INVALID_OBSERVATION")
        if document["capture_point"] == KNOWN_CAPTURE_POINT and _usable(metrics[0]):
            clip_exists = (metrics[0]["state"] == "FINITE"
                           and metrics[0]["value_dbfs"] >= OBSERVED_CLIP_DBFS)
            if (clips > 0) != clip_exists:
                _fail("INVALID_OBSERVATION")
    if _usable(peak) and _usable(rms):
        if peak["state"] != rms["state"] or _peak_less(peak, rms):
            _fail("INVALID_OBSERVATION")
    if _usable(peak) and _usable(session_peak) and _peak_less(session_peak, peak):
        _fail("INVALID_OBSERVATION")
    if window["state"] == session["state"] == "VALID":
        if any(session[name] < window[name] for name in ("finite_sample_values", "clip_sample_values")):
            _fail("INVALID_OBSERVATION")


def _observation_state(document: dict[str, Any]) -> str:
    metrics = [document[name] for name in ("window_peak", "window_rms", "session_peak")]
    counts = [document["window_counts"], document["session_counts"]]
    if any(item["state"] in {"INVALID", "OVERFLOW"} for item in metrics) or any(
            item["state"] == "COUNTER_OVERFLOW" for item in counts):
        return "INVALID_NUMERIC"
    if any(item["state"] == "UNAVAILABLE" for item in counts):
        return "COUNTS_UNAVAILABLE"
    window = document["window_counts"]
    if window["nonfinite_sample_values"] > 0:
        return "INVALID_NONFINITE"
    if document["capture_point"] == "UNKNOWN":
        return "CAPTURE_POINT_UNKNOWN"
    if document["window_loss_state"] == "LOSS_REPORTED":
        return "LOSS_REPORTED"
    if document["window_loss_state"] == "UNKNOWN":
        return "LOSS_UNKNOWN"
    if document["paused"]:
        return "PAUSED"
    if window["finite_sample_values"] == 0:
        return "NO_INPUT"
    if document["window_peak"]["state"] == "LINEAR_ZERO":
        return "MEASURED_LINEAR_ZERO"
    return "MEASURED"


def _decision(document: dict[str, Any], policy_observation: dict[str, Any]) -> tuple[str, str, str, str]:
    state = _observation_state(document)
    status = policy_observation["effective_status"]
    if status != _MATCHED:
        band, reason = "UNCONFIRMED", _POLICY_REASONS[status]
    elif state in _OBSERVATION_REASONS:
        band, reason = "UNCONFIRMED", _OBSERVATION_REASONS[state]
    else:
        policy = _policy(policy_observation["policy_document"])
        observation = PeakObservation(
            PeakObservationState(state), document["window_peak"]["value_dbfs"],
            document["window_counts"]["finite_sample_values"],
        )
        band = classify_meter_band(policy, observation).value
        reason = "WINDOW_POLICY_CLASSIFIED"
    return state, band, reason, _LABELS[band]


def _validate(entrypoint: str, document: dict[str, Any]) -> dict[str, Any]:
    record_type, _, digest_field, _ = _RECORDS[entrypoint]
    if document.get("record_type") != record_type:
        _fail("RECORD_TYPE_MISMATCH")
    _schema(entrypoint, document)
    _integer(document["schema_version"], 1, 1)
    _context(document["query_context"])
    if entrypoint == "observation":
        _observation(document)
    else:
        _uuid(document["runtime_epoch"])
        _uuid(document["policy_producer_epoch"])
        _validate("observation", document["observation"])
        if document["query_context"] != document["observation"]["query_context"]:
            _fail("CONTEXT_MISMATCH")
        if entrypoint == "projection":
            _projection(document)
    _digest(document[digest_field])
    if document[digest_field] != _hash(entrypoint, document):
        _fail("DIGEST_MISMATCH")
    return document


def _projection(document: dict[str, Any]) -> None:
    observation = document["policy_observation"]
    initial, final = observation["initial_status"], observation["final_status"]
    matched = initial == final == _MATCHED
    if (observation["effective_status"] != (final if final != _MATCHED else initial)
            or observation["window_policy_matched"] is not matched):
        _fail("SCHEMA_INVALID")
    if matched:
        identity = observation["identity"]
        if type(identity) is not dict or type(observation["policy_document"]) is not dict:
            _fail("SCHEMA_INVALID")
        for name in ("project_revision", "state_revision"):
            _integer(identity[name], 1)
        for name in ("project_manifest_sha256", "child_sha256", "selected_policy_sha256"):
            _digest(identity[name])
        _uuid(identity["producer_epoch"])
        policy = _policy(observation["policy_document"])
        if (identity["project_id"] != document["query_context"]["project_id"]
                or identity["producer_epoch"] != document["policy_producer_epoch"]
                or identity["selected_policy_sha256"] != policy.to_dict()["policy_revision_sha256"]):
            _fail("CONTEXT_MISMATCH")
    elif observation["identity"] is not None or observation["policy_document"] is not None:
        _fail("SCHEMA_INVALID")
    if tuple(document[name] for name in ("observation_state", "display_band", "reason_code", "operator_label")) != _decision(
            document["observation"], observation):
        _fail("SCHEMA_INVALID")
    for field_name, expected in (("authority", _AUTHORITY), ("io_boundary", _IO_BOUNDARY)):
        if set(document[field_name]) != set(expected) or any(
                document[field_name][key] is not value for key, value in expected.items()):
            _fail("SCHEMA_INVALID")
    if (document["scope_label"] != SCOPE_LABEL or document["window_only"] is not True
            or document["live_admission_serialized"] is not False):
        _fail("SCHEMA_INVALID")
    request = {
        key: document[key] for key in (
            "schema_version", "canonical_owner_task", "query_context",
            "runtime_epoch", "policy_producer_epoch", "observation",
        )
    }
    request["record_type"] = REQUEST_RECORD_TYPE
    _digest(document["request_sha256"])
    if _hash("request", request) != document["request_sha256"]:
        _fail("DIGEST_MISMATCH")


def _parse(entrypoint: str, data: bytes) -> dict[str, Any]:
    return _validate(entrypoint, _decode(data, _RECORDS[entrypoint][3]))


def _serialize(entrypoint: str, document: dict[str, Any]) -> bytes:
    snapshot = _snapshot(document)
    if type(snapshot) is not dict:
        _fail("RECORD_TYPE_MISMATCH")
    _validate(entrypoint, snapshot)
    data = _canonical(snapshot)
    if len(data) > _RECORDS[entrypoint][3]:
        _fail("LIMIT_EXCEEDED")
    return data


def parse_meter_runtime_observation(data: bytes) -> dict[str, Any]:
    return _public(_parse, "observation", data)


def parse_meter_runtime_request(data: bytes) -> dict[str, Any]:
    return _public(_parse, "request", data)


def parse_meter_runtime_projection(data: bytes) -> dict[str, Any]:
    return _public(_parse, "projection", data)


def serialize_meter_runtime_observation(document: dict[str, Any]) -> bytes:
    return _public(_serialize, "observation", document)


def serialize_meter_runtime_request(document: dict[str, Any]) -> bytes:
    return _public(_serialize, "request", document)


def serialize_meter_runtime_projection(document: dict[str, Any]) -> bytes:
    return _public(_serialize, "projection", document)


class _Nonserializable:
    __slots__ = ()

    def __setattr__(self, name: str, value: Any) -> None:
        _fail("NOT_SUPPORTED")

    def __copy__(self) -> Any:
        _fail("NOT_SUPPORTED")

    def __deepcopy__(self, memo: Any) -> Any:
        _fail("NOT_SUPPORTED")

    def __reduce__(self) -> Any:
        _fail("NOT_SUPPORTED")

    def __reduce_ex__(self, protocol: Any) -> Any:
        _fail("NOT_SUPPORTED")

    def __getstate__(self) -> Any:
        _fail("NOT_SUPPORTED")

    def __setstate__(self, state: Any) -> Any:
        _fail("NOT_SUPPORTED")


class MeterWindowTicket(_Nonserializable):
    __slots__ = ("_owner", "_context_bytes", "_runtime", "_producer")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        _fail("NOT_SUPPORTED")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        _fail("NOT_SUPPORTED")

    @property
    def query_context(self) -> MeterPolicyQueryContext:
        return _public(_ticket_context, self)

    @property
    def runtime_epoch(self) -> str:
        return _public(_ticket_value, self, "_runtime")

    @property
    def policy_producer_epoch(self) -> str:
        return _public(_ticket_value, self, "_producer")


class MeterRuntimeProjection(_Nonserializable):
    __slots__ = ("_owner", "_document")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        _fail("NOT_SUPPORTED")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        _fail("NOT_SUPPORTED")

    def to_dict(self) -> dict[str, Any]:
        return _public(_projection_dict, self)


@dataclass(slots=True)
class _Lease:
    controller: MeterRuntimeController
    store: MeterPolicyProjectStore
    project_id: str
    producer_epoch: str
    runtime_epoch: str
    closing: bool = False
    generation: int = 0
    session: str | None = None
    consumer: str | None = None
    epochs: set[str] = field(default_factory=set)
    sessions: set[str] = field(default_factory=set)
    request_ids: set[str] = field(default_factory=set)
    sequence: int = 0
    ticket: MeterWindowTicket | None = None
    ticket_signature: tuple[bytes, str, str] | None = None
    ticket_state: str = "EMPTY"
    projection: MeterRuntimeProjection | None = None
    projection_bytes: bytes | None = None
    evaluation: object | None = None
    evaluation_ticket: MeterWindowTicket | None = None
    finite_floor: int = 0
    clip_floor: int = 0
    peak_floor: dict[str, Any] | None = None
    history_latch: str | None = None


_GUARD = threading.RLock()
_LEASES: list[_Lease] = []


def _state(controller: Any, *, allow_closed: bool = False) -> _Lease:
    if type(controller) is not MeterRuntimeController:
        _fail("TICKET_INVALID")
    state = getattr(controller, "_lease", None)
    if type(state) is not _Lease or state.controller is not controller:
        _fail("TICKET_INVALID")
    if state.closing:
        if allow_closed:
            return state
        _fail("RUNTIME_CLOSED")
    if not any(item is state for item in _LEASES):
        _fail("TICKET_INVALID")
    # Exact-owner close is always available, including after a violated host pin
    # precondition. Pin drift must not make the lease impossible to relinquish.
    if not allow_closed and (state.store.project_id != state.project_id
                             or state.store.producer_epoch != state.producer_epoch):
        _clear(state)
        state.consumer = None
        _fail("EPOCH_MISMATCH")
    return state


def _clear(state: _Lease) -> None:
    state.generation += 1
    state.ticket = None
    state.ticket_signature = None
    state.ticket_state = "EMPTY"
    state.projection = None
    state.projection_bytes = None


def _release(state: _Lease) -> None:
    if state.closing and state.evaluation is None:
        for index, registered in enumerate(_LEASES):
            if registered is state and registered.controller is state.controller and registered.store is state.store:
                del _LEASES[index]
                return


def _ticket_check(state: _Lease, ticket: Any, *, unused: bool) -> None:
    if type(ticket) is not MeterWindowTicket:
        _fail("TICKET_INVALID")
    if state.ticket is not ticket:
        _fail("WINDOW_STALE")
    signature = (ticket._context_bytes, ticket._runtime, ticket._producer)
    if (ticket._owner is not state.controller or any(
            type(actual) is not expected for actual, expected in zip(signature, (bytes, str, str)))
            or signature != state.ticket_signature):
        _fail("TICKET_INVALID")
    if unused and state.ticket_state != "UNUSED":
        _fail("TICKET_CONSUMED")


def _ticket_value(ticket: MeterWindowTicket, name: str) -> Any:
    with _GUARD:
        state = _state(ticket._owner)
        _ticket_check(state, ticket, unused=False)
        return getattr(ticket, name)


def _ticket_context(ticket: MeterWindowTicket) -> MeterPolicyQueryContext:
    return _context(json.loads(_ticket_value(ticket, "_context_bytes")))


def _projection_dict(projection: MeterRuntimeProjection) -> dict[str, Any]:
    with _GUARD:
        if type(projection) is not MeterRuntimeProjection:
            _fail("TICKET_INVALID")
        state = _state(projection._owner)
        if (state.projection is not projection or type(projection._document) is not bytes
                or projection._document != state.projection_bytes):
            _fail("TICKET_INVALID")
        data = projection._document
    return _parse("projection", data)


def _history(state: _Lease, observation: dict[str, Any]) -> None:
    if state.history_latch is not None:
        _fail(state.history_latch)
    finite, clips = state.finite_floor, state.clip_floor
    peak = state.peak_floor
    window, session = observation["window_counts"], observation["session_counts"]
    if window["state"] == "VALID":
        finite += window["finite_sample_values"]
        clips += window["clip_sample_values"]
    if finite > MAX_INTEGER or clips > MAX_INTEGER:
        state.history_latch = "CAPACITY_EXHAUSTED"
        _fail(state.history_latch)
    if session["state"] == "VALID":
        if session["finite_sample_values"] < finite or session["clip_sample_values"] < clips:
            state.history_latch = "SESSION_HISTORY_REGRESSION"
            _fail(state.history_latch)
        finite, clips = session["finite_sample_values"], session["clip_sample_values"]
    window_peak, session_peak = observation["window_peak"], observation["session_peak"]
    if _usable(window_peak) and (peak is None or _peak_less(peak, window_peak)):
        peak = window_peak
    if _usable(session_peak):
        if peak is not None and _peak_less(session_peak, peak):
            state.history_latch = "SESSION_HISTORY_REGRESSION"
            _fail(state.history_latch)
        peak = session_peak
    state.finite_floor, state.clip_floor = finite, clips
    state.peak_floor = None if peak is None else dict(peak)


def _read_result(result: Any, state: _Lease, context: MeterPolicyQueryContext) -> tuple[str, MeterPolicySnapshot | None]:
    """Validate public result shape; P1 revalidate owns actual snapshot admission."""
    try:
        if type(result) is not MeterPolicyReadResult or type(result.status) is not MeterPolicyReadStatus:
            return "MISMATCH", None
        status = result.status.value
        if status != _MATCHED:
            return status, None
        snapshot = result.snapshot
        if type(snapshot) is not MeterPolicySnapshot or type(snapshot.context) is not MeterPolicyQueryContext:
            return "MISMATCH", None
        if (snapshot.producer_epoch != state.producer_epoch
                or snapshot.project_id != state.project_id
                or _context(snapshot.context.to_dict()).to_dict() != context.to_dict()
                or type(snapshot.policy) is not MeterDisplayPolicyRevision):
            return "MISMATCH", None
        _integer(snapshot.project_revision, 1)
        _integer(snapshot.state_revision, 1)
        _digest(snapshot.project_manifest_sha256)
        _digest(snapshot.child_sha256)
        _digest(snapshot.selected_policy_sha256)
        policy = _policy(_snapshot(snapshot.policy.to_dict()))
        if policy.to_dict()["policy_revision_sha256"] != snapshot.selected_policy_sha256:
            return "MISMATCH", None
    except (AttributeError, TypeError, ValueError):
        return "MISMATCH", None
    return status, snapshot


def _read(state: _Lease, context: MeterPolicyQueryContext, snapshot: MeterPolicySnapshot | None = None) -> tuple[str, MeterPolicySnapshot | None]:
    try:
        result = (state.store.read_snapshot(context) if snapshot is None
                  else state.store.revalidate(snapshot, context))
    except Exception:
        return "READBACK_FAILED", None
    return _read_result(result, state, context)


def _build_projection(request: dict[str, Any], initial: str, final: str, snapshot: MeterPolicySnapshot | None) -> bytes:
    matched = initial == final == _MATCHED
    identity, policy = None, None
    if matched:
        assert snapshot is not None
        identity = {name: getattr(snapshot, name) for name in (
            "project_id", "project_revision", "project_manifest_sha256", "child_sha256",
            "state_revision", "selected_policy_sha256", "producer_epoch",
        )}
        policy = snapshot.policy.to_dict()
    policy_observation = {
        "initial_status": initial, "final_status": final,
        "effective_status": final if final != _MATCHED else initial,
        "window_policy_matched": matched, "identity": identity, "policy_document": policy,
    }
    observation_state, band, reason, label = _decision(request["observation"], policy_observation)
    document = {key: request[key] for key in (
        "schema_version", "canonical_owner_task", "query_context", "runtime_epoch",
        "policy_producer_epoch", "request_sha256", "observation",
    )}
    document.update({
        "record_type": PROJECTION_RECORD_TYPE, "observation_state": observation_state,
        "policy_observation": policy_observation, "display_band": band, "reason_code": reason,
        "operator_label": label, "scope_label": SCOPE_LABEL, "window_only": True,
        "live_admission_serialized": False, "authority": dict(_AUTHORITY),
        "io_boundary": dict(_IO_BOUNDARY),
    })
    document["projection_sha256"] = _hash("projection", document)
    return _serialize("projection", document)


class MeterRuntimeController(_Nonserializable):
    """One exact P1 store lease. Explicit close is mandatory; GC cannot release it."""

    __slots__ = ("_lease",)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        _fail("NOT_SUPPORTED")

    def __init__(self, store: MeterPolicyProjectStore) -> None:
        _public(self._initialize, store)

    def _initialize(self, store: MeterPolicyProjectStore) -> None:
        if type(self) is not MeterRuntimeController or hasattr(self, "_lease"):
            _fail("NOT_SUPPORTED")
        if type(store) is not MeterPolicyProjectStore:
            _fail("RECORD_TYPE_MISMATCH")
        state = None
        with _GUARD:
            if any(item.store is store for item in _LEASES):
                _fail("RUNTIME_BUSY")
            if len(_LEASES) >= MAX_LEASES:
                _fail("CAPACITY_EXHAUSTED")
            project_id, epoch = store.project_id, _uuid(store.producer_epoch)
            if type(project_id) is not str or not _PROJECT.fullmatch(project_id):
                _fail("CONTEXT_MISMATCH")
            try:
                state = _Lease(self, store, project_id, epoch, _uuid(str(uuid.uuid4())))
                _LEASES.append(state)
                object.__setattr__(self, "_lease", state)
            except BaseException:
                if state is not None:
                    state.closing = True
                    _release(state)
                raise

    @property
    def runtime_epoch(self) -> str:
        with _GUARD:
            return _state(self).runtime_epoch

    @property
    def policy_producer_epoch(self) -> str:
        with _GUARD:
            return _state(self).producer_epoch

    @property
    def project_id(self) -> str:
        with _GUARD:
            return _state(self).project_id

    def activate_consumer(self, *, session_id: str, consumer_epoch: str) -> None:
        _public(self._activate, session_id, consumer_epoch)

    def _activate(self, session_id: str, consumer_epoch: str) -> None:
        with _GUARD:
            state = _state(self)
            _clear(state)
            state.consumer = None
            session_id, consumer_epoch = _uuid(session_id), _uuid(consumer_epoch)
            if consumer_epoch in state.epochs or (session_id in state.sessions and state.session != session_id):
                _fail("EPOCH_MISMATCH")
            if len(state.epochs) >= MAX_CONSUMER_EPOCHS or (
                    session_id not in state.sessions and len(state.sessions) >= MAX_SESSIONS):
                _fail("CAPACITY_EXHAUSTED")
            if session_id != state.session:
                state.finite_floor = state.clip_floor = 0
                state.peak_floor = None
                state.history_latch = None
            state.session, state.consumer = session_id, consumer_epoch
            state.epochs.add(consumer_epoch)
            state.sessions.add(session_id)
            state.sequence = 0
            state.request_ids = set()

    def begin_window(self) -> MeterWindowTicket:
        return _public(self._begin)

    def _begin(self) -> MeterWindowTicket:
        with _GUARD:
            state = _state(self)
            _clear(state)
            if state.consumer is None or state.session is None:
                _fail("CONTEXT_MISMATCH")
            if state.sequence >= MAX_WINDOWS or len(state.request_ids) >= MAX_WINDOWS:
                _fail("CAPACITY_EXHAUSTED")
            request_id = _uuid(str(uuid.uuid4()))
            if request_id in state.request_ids:
                state.consumer = None
                _fail("IDENTITY_COLLISION")
            context = MeterPolicyQueryContext(
                state.project_id, state.session, state.consumer, state.sequence + 1, request_id,
            )
            ticket = object.__new__(MeterWindowTicket)
            context_bytes = _canonical(context.to_dict())
            for name, value in (
                ("_owner", self), ("_context_bytes", context_bytes),
                ("_runtime", state.runtime_epoch), ("_producer", state.producer_epoch),
            ):
                object.__setattr__(ticket, name, value)
            state.sequence += 1
            state.request_ids.add(request_id)
            state.ticket = ticket
            state.ticket_signature = (context_bytes, state.runtime_epoch, state.producer_epoch)
            state.ticket_state = "UNUSED"
            return ticket

    def invalidate(self, reason: str) -> None:
        _public(self._invalidate, reason)

    def _invalidate(self, reason: str) -> None:
        if type(reason) is not str or reason not in {
            "PROJECT_CHANGED", "READBACK_UNAVAILABLE", "TIMEOUT", "PAUSED", "RESUMED",
            "RECONNECT", "HOST_RESTORE_UNCERTAIN",
        }:
            _fail("NOT_SUPPORTED")
        with _GUARD:
            state = _state(self)
            _clear(state)
            if reason == "RECONNECT":
                state.consumer = None
            if reason == "HOST_RESTORE_UNCERTAIN":
                state.closing = True
                _release(state)

    def close(self) -> None:
        _public(self._close)

    def _close(self) -> None:
        with _GUARD:
            state = _state(self, allow_closed=True)
            if not state.closing:
                _clear(state)
                state.closing = True
            _release(state)

    def project(self, ticket: MeterWindowTicket, request_bytes: bytes) -> MeterRuntimeProjection:
        return _public(self._project, ticket, request_bytes)

    def _project(self, ticket: MeterWindowTicket, request_bytes: bytes) -> MeterRuntimeProjection:
        state = None
        generation = None
        associated = False
        invocation = object()
        completed = False

        def current() -> None:
            assert state is not None
            _state(self)
            if (state.generation != generation or state.ticket is not ticket):
                _fail("WINDOW_STALE")
            _ticket_check(state, ticket, unused=False)
            if state.evaluation is not invocation:
                _fail("TICKET_CONSUMED")

        try:
            with _GUARD:
                state = _state(self)
                _ticket_check(state, ticket, unused=True)
                generation = state.generation
                associated = True
                context = _context(json.loads(state.ticket_signature[0]))
                runtime_epoch, producer_epoch = state.runtime_epoch, state.producer_epoch
            if type(request_bytes) is not bytes:
                _fail("RECORD_TYPE_MISMATCH")
            request = parse_meter_runtime_request(request_bytes)
            if request["query_context"] != context.to_dict():
                _fail("CONTEXT_MISMATCH")
            if (request["runtime_epoch"] != runtime_epoch or request["policy_producer_epoch"] != producer_epoch):
                _fail("EPOCH_MISMATCH")
            with _GUARD:
                _state(self)
                if state.generation != generation:
                    _fail("WINDOW_STALE")
                _ticket_check(state, ticket, unused=True)
                if state.evaluation is not None:
                    _fail("RUNTIME_BUSY")
                state.evaluation = invocation
                state.evaluation_ticket = ticket
                state.ticket_state = "EVALUATING"
                _history(state, request["observation"])
            initial, snapshot = _read(state, context)
            with _GUARD:
                current()
            # Failure snapshots cannot be rehabilitated; final read is diagnostic.
            final, final_snapshot = _read(state, context, snapshot if initial == _MATCHED else None)
            data = _build_projection(request, initial, final, final_snapshot)
            with _GUARD:
                current()
                projection = object.__new__(MeterRuntimeProjection)
                object.__setattr__(projection, "_owner", self)
                object.__setattr__(projection, "_document", data)
                state.ticket_state = "CONSUMED"
                state.projection = projection
                state.projection_bytes = data
                completed = True
            return projection
        finally:
            with _GUARD:
                if state is not None:
                    owns_slot = state.evaluation is invocation
                    another_owns_ticket = (
                        state.evaluation is not None and not owns_slot
                        and state.evaluation_ticket is ticket
                    )
                    if (associated and not completed and not another_owns_ticket
                            and (owns_slot or state.ticket_state == "UNUSED")
                            and state.ticket is ticket and state.generation == generation):
                        _clear(state)
                    if owns_slot:
                        state.evaluation = None
                        state.evaluation_ticket = None
                    _release(state)


__all__ = [
    "MeterRuntimeContractError", "MeterRuntimeController", "MeterWindowTicket",
    "MeterRuntimeProjection", "OBSERVATION_RECORD_TYPE", "REQUEST_RECORD_TYPE",
    "PROJECTION_RECORD_TYPE", "OBSERVATION_DOMAIN", "REQUEST_DOMAIN", "PROJECTION_DOMAIN",
    "OBSERVED_CLIP_DBFS", "KNOWN_CAPTURE_POINT", "SCOPE_LABEL",
    "parse_meter_runtime_observation", "parse_meter_runtime_request",
    "parse_meter_runtime_projection", "serialize_meter_runtime_observation",
    "serialize_meter_runtime_request", "serialize_meter_runtime_projection",
]
