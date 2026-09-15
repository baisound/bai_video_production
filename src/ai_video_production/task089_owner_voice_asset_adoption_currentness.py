"""TASK-089's deliberately non-live owner-voice adoption fixture ABI.

This module is a closed JSON contract.  It has no store, path, clock, process,
network, custody backend, or Asset-ingest dependency.  Its only foreign owner
dependency is TASK-082's already-pure receipt/event parser and currentness
derivation.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import gzip
import hashlib
import json
import re
from typing import Any, Mapping, Sequence
from weakref import WeakKeyDictionary

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .serialization import canonical_json_bytes, sha256_bytes
from .task082_owner_voice_private_media_custody import (
    ArtifactClass,
    CurrentnessState,
    PrivateMediaCustodyReceipt,
    PrivateMediaGenerationEvent,
    Task082Reason,
    derive_generation_currentness,
)

SCHEMA_ID = "bai.task089.owner-voice-asset-adoption-currentness.nonlive.v1"
SCHEMA_VERSION = 1
TASK_OWNER = "TASK-089"
MAX_JSON_BYTES = 1_048_576
MAX_DEPTH = 20
MAX_NODES = 32_768
MAX_FIELDS = 128
MAX_ARRAY = 256
MAX_STRING_BYTES = 4096

# These are gzip/base64 copies of the two pinned, locally reviewed schema
# resources.  Parsing a fixture never reads a schema path and the registry has
# exactly the imported TASK-082 resource; it consequently cannot fall back to
# URI/network discovery.
_TASK089_SCHEMA_GZIP_B64 = "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"
_TASK082_SCHEMA_GZIP_B64 = "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"

_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOKEN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_PROJECT = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
_TIME = re.compile(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})\.([0-9]{6})Z$")
_OWNER_TIME = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$")
_ID = re.compile(r"^(JOB|ASSET|OP)-[0-9A-HJKMNP-TV-Z]{26}$")

_COMMON = (
    "record_type", "schema_version", "adapter_owner_task", "canonical_asset_owner_task",
    "fixture_only", "authority_created", "execution_authorized", "owner_port_contract_status",
    "private_media_effect_count", "asset_adoption_count", "record_sha256",
)
_FIELDS = {
    "Task089SubjectFixtureV1": ("fixture_case", "project_id", "production_job_id", "project_revision", "owner_subject_revision"),
    "Task089PurposeGrantFixtureV1": ("subject_sha256", "scope", "operation", "output_role", "decision", "policy_revision", "grant_revision", "issued_at", "expires_at", "q1_readback_sha256"),
    "Task089ProducerOutputFixtureV1": ("subject_sha256", "grant_sha256", "producer_task", "producer_output_role", "asset_role", "producer_operation_id", "output_sequence", "content_sha256", "media", "upstream_producer_sha256", "q1_readback_sha256"),
    "Task089CustodyFixtureV1": ("producer_sha256", "custody_receipt", "generation_events"),
    "Task089AdoptionRequestFixtureV1": ("subject_sha256", "producer_sha256", "custody_sha256", "grant_sha256", "adoption_operation_id", "expected_registry_generation", "predecessor_registration_sha256", "semantic_key_sha256"),
    "Task089RegistrationFixtureV1": ("request_sha256", "outcome", "registry_generation", "asset_snapshot"),
    "Task089CurrentReadbackFixtureV1": ("request_sha256", "registration_sha256", "observation_kind", "observed_subject_sha256", "observed_grant_sha256", "observed_registry_generation", "selected_asset_id", "selected_registration_sha256", "observed_custody_sha256", "fixture_session", "observed_at", "fresh_until"),
}
_OUTPUT_FIELDS = {
    "Task089AdoptionAssessmentFixtureV1": ("request_sha256", "readback_sha256", "registration_sha256", "fixture_state", "reason_code", "guard_status", "required_owner_contracts"),
    "Task089Q2PairHandoffFixtureV1": ("subject_sha256", "q1_readback_sha256", "q2_producer_operation_id", "processed_request_sha256", "processed_readback_sha256", "copy_request_sha256", "copy_readback_sha256", "processed_assessment_sha256", "copy_assessment_sha256", "consumer_owner_task", "terminal_binding_status"),
}
_ROLE = {
    "RAW_CAPTURE": ("TASK-047", "TASK047_RAW_CAPTURE_OUTPUT", "CAPTURE_RAW_PUBLISH", "OWNER_VOICE_CAPTURE", ArtifactClass.RAW_CAPTURE),
    "CANONICAL_PCM": ("TASK-047", "TASK047_CANONICAL_PCM_OUTPUT", "CAPTURE_CANONICAL_PUBLISH", "OWNER_VOICE_CAPTURE", ArtifactClass.CANONICAL_PCM),
    "PROCESSED_SPEECH_CONTINUOUS": ("TASK-048", "TASK048_SPEECH_CONTINUOUS_OUTPUT", "QUALITY_SPEECH_CONTINUOUS_PUBLISH", "OWNER_VOICE_DATA_PREPARATION", ArtifactClass.PROCESSED_SPEECH_CONTINUOUS),
    "TRAINING_COPY": ("TASK-048", "TASK048_TRAINING_COPY_OUTPUT", "QUALITY_TRAINING_COPY_PUBLISH", "OWNER_VOICE_DATA_PREPARATION", ArtifactClass.TRAINING_COPY),
}
_GRANT_OPERATION = {
    "RAW_CAPTURE": "CAPTURE_RAW_PUBLISH",
    "CANONICAL_PCM": "CAPTURE_CANONICAL_PUBLISH",
    "PROCESSED_SPEECH_CONTINUOUS": "QUALITY_FINISHING",
    "TRAINING_COPY": "TRAINING_COPY_CREATION",
}
_NOMINAL_BYTES: WeakKeyDictionary[object, bytes] = WeakKeyDictionary()


def _pinned_schema(encoded: str, expected_sha256: str) -> dict[str, Any]:
    try:
        raw = gzip.decompress(base64.b64decode(encoded, validate=True))
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ValueError("pinned schema hash mismatch")
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, ValueError, TypeError):
        raise RuntimeError("TASK-089 pinned schema bootstrap failed") from None
    if type(parsed) is not dict:
        raise RuntimeError("TASK-089 pinned schema bootstrap failed")
    return parsed


_PINNED_TASK082_SCHEMA = _pinned_schema(
    _TASK082_SCHEMA_GZIP_B64,
    "575ce090367528dc6184b0a030f503ea6bfd56a1bbe32a18f4fe61a12fe914dc",
)
_PINNED_TASK089_SCHEMA = _pinned_schema(
    _TASK089_SCHEMA_GZIP_B64,
    "29d8ff8c4c73abff29d6a6e2d758cb1a3510ac25620aea9f1dc2b5e05178354e",
)
_LOCAL_SCHEMA_VALIDATOR = Draft202012Validator(
    _PINNED_TASK089_SCHEMA,
    registry=Registry().with_resource(
        _PINNED_TASK082_SCHEMA["$id"], Resource.from_contents(_PINNED_TASK082_SCHEMA)
    ),
)
class Task089ContractError(ValueError):
    """Public failure: exactly one fixed, body-free code."""
    _CODES = {"MALFORMED_FIXTURE", "REFERENCE_MISMATCH", "CYCLIC_FIXTURE", "ROLE_MISMATCH", "PAIR_MISMATCH"}
    def __init__(self, code: str) -> None:
        self.code = code if code in self._CODES else "MALFORMED_FIXTURE"
        super().__init__(self.code)


def _fail(code: str = "MALFORMED_FIXTURE") -> None:
    raise Task089ContractError(code) from None


def _digest(value: Any, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str or not _DIGEST.fullmatch(value):
        _fail()
    return value


def _integer(value: Any, low: int = 0, high: int = 2_147_483_647) -> int:
    if type(value) is not int or not low <= value <= high:
        _fail()
    return value


def _time(value: Any) -> datetime:
    if type(value) is not str or not _TIME.fullmatch(value):
        _fail()
    try:
        result = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        _fail()
    if result.year < 2000:
        _fail()
    return result


def _owner_time(value: Any) -> datetime:
    """Parse only the already-owned TASK-082 UTC grammar; never rewrite it."""
    if type(value) is not str or not _OWNER_TIME.fullmatch(value):
        _fail()
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        _fail()


def _record_digest(record_type: str, value: Mapping[str, Any]) -> str:
    body = {key: item for key, item in value.items() if key != "record_sha256"}
    return sha256_bytes(b"BAI:TASK089:NONLIVE:" + record_type.encode("ascii") + b":V1\0" + canonical_json_bytes(body))


def _bundle_digest(value: Mapping[str, Any]) -> str:
    return sha256_bytes(b"BAI:TASK089:NONLIVE:Task089FixtureBundleV1:V1\0" + canonical_json_bytes({k: v for k, v in value.items() if k != "bundle_sha256"}))


def _semantic_key(value: Mapping[str, Any]) -> str:
    body = {k: v for k, v in value.items() if k not in _COMMON + ("adoption_operation_id", "semantic_key_sha256")}
    return sha256_bytes(b"BAI:TASK089:FIXTURE_ADOPTION_KEY:V1\0" + canonical_json_bytes(body))


def _strict_payload(payload: bytes | str) -> dict[str, Any]:
    if type(payload) is bytes:
        if len(payload) > MAX_JSON_BYTES or payload.startswith(b"\xef\xbb\xbf"):
            _fail()
        try:
            text = payload.decode("utf-8", "strict")
        except UnicodeError:
            _fail()
    elif type(payload) is str:
        try:
            encoded = payload.encode("utf-8", "strict")
        except UnicodeError:
            _fail()
        if len(encoded) > MAX_JSON_BYTES or payload.startswith("\ufeff"):
            _fail()
        text = payload
    else:
        _fail()
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                _fail()
            result[key] = value
        return result
    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=lambda _: _fail())
    except Task089ContractError:
        raise
    except (ValueError, TypeError, RecursionError):
        _fail()
    if type(value) is not dict:
        _fail()
    pending: list[tuple[Any, int]] = [(value, 1)]
    nodes = 0
    while pending:
        current, depth = pending.pop()
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            _fail()
        if type(current) is str:
            try:
                if len(current.encode("utf-8", "strict")) > MAX_STRING_BYTES or any(ord(c) < 32 for c in current):
                    _fail()
            except UnicodeError:
                _fail()
        elif type(current) is dict:
            if len(current) > MAX_FIELDS or any(type(k) is not str for k in current):
                _fail()
            pending.extend((v, depth + 1) for v in current.values())
        elif type(current) is list:
            if len(current) > MAX_ARRAY:
                _fail()
            pending.extend((v, depth + 1) for v in current)
        elif current is not None and type(current) not in {bool, int, float}:
            _fail()
        elif type(current) is float:
            _fail()
    return value


def _local_schema_admission(body: dict[str, Any]) -> None:
    """Apply the closed, pinned schema before semantic/digest validation."""
    if body.get("record_type") != "Task089FixtureBundleV1":
        _fail()
    try:
        if next(_LOCAL_SCHEMA_VALIDATOR.iter_errors(body), None) is not None:
            _fail()
    except Task089ContractError:
        raise
    except Exception:
        # The frozen registry contains only in-memory reviewed resources.  A
        # bootstrap/validation fault must never become a permissive parser.
        _fail()


def _exact_builtin_tree(value: Any, depth: int = 1) -> bool:
    """Reject forged state before invoking mapping, iterator, or JSON hooks."""
    if depth > MAX_DEPTH:
        return False
    if value is None or type(value) in {str, bool, int}:
        return True
    if type(value) is list:
        return len(value) <= MAX_ARRAY and all(_exact_builtin_tree(item, depth + 1) for item in value)
    if type(value) is dict:
        return len(value) <= MAX_FIELDS and all(type(key) is str and _exact_builtin_tree(item, depth + 1) for key, item in value.items())
    return False


class _Nominal:
    """A nominal output is an unforgeable handle to module-private bytes.

    No instance slot may hold the serialized body: ordinary or object-level
    assignment therefore cannot replace, delete, then restore a valid state.
    The weak registry is intentionally the only provenance location.
    """
    __slots__ = ("__weakref__",)
    def __init__(self, *_: Any, **__: Any) -> None:
        _fail()
    def __setattr__(self, name: str, value: Any) -> None:
        _fail()
    def __delattr__(self, name: str) -> None:
        _fail()
    def to_dict(self) -> dict[str, Any]:
        if type(self) not in {Task089AdoptionAssessment, Task089Q2PairHandoff}:
            _fail()
        body = _NOMINAL_BYTES.get(self)
        if type(body) is not bytes:
            _fail()
        try:
            result = json.loads(body.decode("utf-8"))
        except (UnicodeError, ValueError, TypeError):
            _fail()
        if not _exact_builtin_tree(result) or canonical_json_bytes(result) != body:
            _fail()
        _validate_nominal_output(result, type(self))
        return result
    def __reduce__(self) -> Any:
        raise TypeError("MALFORMED_FIXTURE")
    def __getattr__(self, name: str) -> Any:
        if type(self) not in {Task089AdoptionAssessment, Task089Q2PairHandoff}:
            _fail()
        if type(name) is not str:
            _fail()
        body = self.to_dict()
        if name in body:
            return body[name]
        raise AttributeError(name)


class Task089AdoptionAssessment(_Nominal):
    __slots__ = ()
    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("MALFORMED_FIXTURE")


class Task089Q2PairHandoff(_Nominal):
    __slots__ = ()
    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("MALFORMED_FIXTURE")


class Task089FixtureBundle:
    __slots__ = ("__weakref__",)
    def __init__(self, *_: Any, **__: Any) -> None:
        _fail()
    def __setattr__(self, name: str, value: Any) -> None:
        _fail()
    def __delattr__(self, name: str) -> None:
        _fail()
    def to_dict(self) -> dict[str, Any]:
        if type(self) is not Task089FixtureBundle:
            _fail()
        body = _NOMINAL_BYTES.get(self)
        if type(body) is not bytes:
            _fail()
        try:
            result = json.loads(body.decode("utf-8"))
        except (UnicodeError, ValueError, TypeError):
            _fail()
        if not _exact_builtin_tree(result) or canonical_json_bytes(result) != body:
            _fail()
        _validate_bundle_mapping(result)
        return result
    def __reduce__(self) -> Any:
        raise TypeError("MALFORMED_FIXTURE")
    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("MALFORMED_FIXTURE")
    def __getattr__(self, name: str) -> Any:
        if type(self) is not Task089FixtureBundle:
            _fail()
        if type(name) is not str:
            _fail()
        body = self.to_dict()
        if name == "records":
            return tuple(body["records"])
        if name in body:
            return body[name]
        raise AttributeError(name)


def _new_output(cls: type[_Nominal], body: Mapping[str, Any]) -> _Nominal:
    if cls not in {Task089AdoptionAssessment, Task089Q2PairHandoff}:
        _fail()
    result = object.__new__(cls)
    encoded = canonical_json_bytes(dict(body))
    _NOMINAL_BYTES[result] = encoded
    return result


def _new_bundle(body: Mapping[str, Any]) -> Task089FixtureBundle:
    result = object.__new__(Task089FixtureBundle)
    encoded = canonical_json_bytes(dict(body))
    _NOMINAL_BYTES[result] = encoded
    return result


def _common(record: Mapping[str, Any], kind: str, extras: Sequence[str]) -> None:
    if set(record) != set(_COMMON + tuple(extras)):
        _fail()
    if (record.get("record_type") != kind or type(record.get("schema_version")) is not int or record.get("schema_version") != 1 or record.get("adapter_owner_task") != TASK_OWNER or record.get("canonical_asset_owner_task") != "TASK-003" or record.get("fixture_only") is not True or record.get("authority_created") is not False or record.get("execution_authorized") is not False or record.get("owner_port_contract_status") != "NOT_BOUND" or type(record.get("private_media_effect_count")) is not int or record.get("private_media_effect_count") != 0 or type(record.get("asset_adoption_count")) is not int or record.get("asset_adoption_count") != 0):
        _fail()
    if _digest(record.get("record_sha256")) != _record_digest(kind, record):
        _fail()


def _media(value: Any, role: str) -> None:
    if type(value) is not dict or set(value) != {"format", "sample_rate_hz", "channels", "sample_count"}:
        _fail()
    if value["format"] not in {"PCM_S16LE", "PCM_S24LE", "FLOAT32LE"} or _integer(value["sample_rate_hz"], 8000, 192000) is None or _integer(value["channels"], 1, 8) is None or _integer(value["sample_count"], 1, 1_382_400_000) is None:
        _fail()
    if role != "RAW_CAPTURE" and (value["format"], value["sample_rate_hz"], value["channels"]) != ("PCM_S24LE", 48000, 1):
        _fail("ROLE_MISMATCH")


def _refs(record: Mapping[str, Any]) -> tuple[str, ...]:
    k = record["record_type"]
    if k == "Task089PurposeGrantFixtureV1": return (record["subject_sha256"],) + ((record["q1_readback_sha256"],) if record["q1_readback_sha256"] else ())
    if k == "Task089ProducerOutputFixtureV1": return tuple(x for x in (record["subject_sha256"], record["grant_sha256"], record["upstream_producer_sha256"], record["q1_readback_sha256"]) if x)
    if k == "Task089CustodyFixtureV1": return (record["producer_sha256"],)
    if k == "Task089AdoptionRequestFixtureV1": return tuple(x for x in (record["subject_sha256"], record["producer_sha256"], record["custody_sha256"], record["grant_sha256"], record["predecessor_registration_sha256"]) if x)
    if k == "Task089RegistrationFixtureV1": return (record["request_sha256"],)
    if k == "Task089CurrentReadbackFixtureV1": return tuple(x for x in (record["request_sha256"], record["registration_sha256"], record["observed_subject_sha256"], record["observed_grant_sha256"], record["selected_registration_sha256"], record["observed_custody_sha256"]) if x)
    return ()


def _validate_record(record: Mapping[str, Any], index: Mapping[str, Mapping[str, Any]]) -> None:
    kind = record.get("record_type")
    if type(kind) is not str or kind not in _FIELDS:
        _fail()
    _common(record, kind, _FIELDS[kind])
    if kind == "Task089SubjectFixtureV1":
        if type(record["fixture_case"]) is not str or not _TOKEN.fullmatch(record["fixture_case"]) or not record["fixture_case"].startswith("fixture-") or type(record["project_id"]) is not str or not _PROJECT.fullmatch(record["project_id"]) or type(record["production_job_id"]) is not str or not _ID.fullmatch(record["production_job_id"]) or not record["production_job_id"].startswith("JOB-"):
            _fail()
        _integer(record["project_revision"], 1); _integer(record["owner_subject_revision"], 1); return
    for digest in _refs(record): _digest(digest)
    if kind == "Task089PurposeGrantFixtureV1":
        if record["output_role"] not in _ROLE or record["scope"] != _ROLE[record["output_role"]][3] or record["operation"] != _GRANT_OPERATION[record["output_role"]] or record["decision"] not in {"ALLOW", "DENY", "UNKNOWN"}:
            _fail("ROLE_MISMATCH")
        if record["output_role"] in {"RAW_CAPTURE", "CANONICAL_PCM"} and record["q1_readback_sha256"] is not None:
            _fail()
        _integer(record["policy_revision"], 1); _integer(record["grant_revision"], 1)
        if _time(record["issued_at"]) >= _time(record["expires_at"]): _fail()
    elif kind == "Task089ProducerOutputFixtureV1":
        role = record["asset_role"]
        if role not in _ROLE or (record["producer_task"], record["producer_output_role"]) != _ROLE[role][:2] or type(record["producer_operation_id"]) is not str or not (_ID.fullmatch(record["producer_operation_id"]) and record["producer_operation_id"].startswith("OP-")):
            _fail("ROLE_MISMATCH")
        _integer(record["output_sequence"], 1); _digest(record["content_sha256"]); _media(record["media"], role)
    elif kind == "Task089CustodyFixtureV1":
        if type(record["generation_events"]) is not list or not 1 <= len(record["generation_events"]) <= 64 or type(record["custody_receipt"]) is not dict:
            _fail()
        try:
            receipt = PrivateMediaCustodyReceipt.from_mapping(record["custody_receipt"])
            events = [PrivateMediaGenerationEvent.from_mapping(x) for x in record["generation_events"]]
        except Exception:
            _fail()
        if receipt.generation_event_sha256 not in {x.event_sha256 for x in events} or receipt.event_head_sha256 != receipt.generation_event_sha256:
            _fail("REFERENCE_MISMATCH")
    elif kind == "Task089AdoptionRequestFixtureV1":
        if type(record["adoption_operation_id"]) is not str or not (_ID.fullmatch(record["adoption_operation_id"]) and record["adoption_operation_id"].startswith("OP-")):
            _fail()
        _integer(record["expected_registry_generation"]); _digest(record["predecessor_registration_sha256"], True)
        if record["semantic_key_sha256"] != _semantic_key(record): _fail()
    elif kind == "Task089RegistrationFixtureV1":
        if record["outcome"] not in {"REGISTERED", "REJECTED_NO_WRITE", "COMPLETION_UNKNOWN"}: _fail()
        _integer(record["registry_generation"])
        snap = record["asset_snapshot"]
        if record["outcome"] == "REGISTERED":
            if type(snap) is not dict or set(snap) != {"asset_id", "production_job_id", "asset_type", "asset_role", "logical_uri", "checksum", "asset_version", "producer_operation_id", "custody_receipt_sha256"}: _fail()
            if type(snap["asset_id"]) is not str or not (snap["asset_id"].startswith("ASSET-") and _ID.fullmatch(snap["asset_id"])) or type(snap["production_job_id"]) is not str or not (snap["production_job_id"].startswith("JOB-") and _ID.fullmatch(snap["production_job_id"])) or snap["asset_type"] != "AUDIO" or snap["asset_role"] not in _ROLE or type(snap["logical_uri"]) is not str or not snap["logical_uri"].startswith("asset://") or type(snap["producer_operation_id"]) is not str or not (snap["producer_operation_id"].startswith("OP-") and _ID.fullmatch(snap["producer_operation_id"])): _fail()
            _digest(snap["checksum"]); _digest(snap["custody_receipt_sha256"]); _integer(snap["asset_version"], 1)
        elif snap is not None: _fail()
    elif kind == "Task089CurrentReadbackFixtureV1":
        if type(record["fixture_session"]) is not str or not (_TOKEN.fullmatch(record["fixture_session"]) and record["fixture_session"].startswith("fixture-")) or _time(record["observed_at"]) >= _time(record["fresh_until"]): _fail()
        arm = record["observation_kind"]
        if arm not in {"SNAPSHOT", "NO_WRITE", "UNRESOLVED", "UNAVAILABLE", "RESTARTED"}: _fail()
        nulls = ("observed_subject_sha256", "observed_grant_sha256", "observed_registry_generation", "selected_asset_id", "selected_registration_sha256", "observed_custody_sha256")
        if arm in {"UNAVAILABLE", "RESTARTED"}:
            if record["registration_sha256"] is not None or any(record[x] is not None for x in nulls): _fail()
        elif arm == "UNRESOLVED":
            if record["registration_sha256"] is None or any(record[x] is not None for x in ("observed_subject_sha256", "observed_grant_sha256", "selected_asset_id", "selected_registration_sha256", "observed_custody_sha256")) or type(record["observed_registry_generation"]) is not int: _fail()
        elif arm == "NO_WRITE":
            if record["registration_sha256"] is None or any(record[x] is None for x in ("observed_subject_sha256", "observed_grant_sha256", "observed_registry_generation", "observed_custody_sha256")) or record["selected_asset_id"] is not None or record["selected_registration_sha256"] is not None: _fail()
        else:
            if any(record[x] is None for x in ("registration_sha256", "observed_subject_sha256", "observed_grant_sha256", "observed_registry_generation", "selected_asset_id", "selected_registration_sha256", "observed_custody_sha256")): _fail()
        for key in ("registration_sha256", "observed_subject_sha256", "observed_grant_sha256", "selected_registration_sha256", "observed_custody_sha256"): _digest(record[key], True)
        if record["observed_registry_generation"] is not None: _integer(record["observed_registry_generation"])


def _validate_owner_event_chain(event_maps: Sequence[Mapping[str, Any]]) -> None:
    """Check all TASK-082 transitions without treating a stale window as shape.

    The imported parser authenticates each event.  This narrow graph pass makes
    every supplied transition accountable even when an earlier immutable window
    is stale (the owner currentness derivation intentionally short-circuits in
    that case).  Window eligibility remains root assessment policy.
    """
    try:
        events = [PrivateMediaGenerationEvent.from_mapping(event) for event in event_maps]
    except Exception:
        _fail()
    if not events:
        _fail("REFERENCE_MISMATCH")
    first = events[0]
    lineage = (
        first.logical_slot_ref, first.artifact_class, first.owner_subject_revision_sha256,
        first.purpose, first.consent_rights_revision_sha256,
    )
    previous: PrivateMediaGenerationEvent | None = None
    previous_time: datetime | None = None
    current_generation: int | None = None
    current_publish: str | None = None
    last_generation = 0
    for revision, event in enumerate(events, 1):
        if (
            event.event_revision != revision
            or event.predecessor_event_sha256 != (None if previous is None else previous.event_sha256)
            or (event.logical_slot_ref, event.artifact_class, event.owner_subject_revision_sha256,
                event.purpose, event.consent_rights_revision_sha256) != lineage
        ):
            _fail("REFERENCE_MISMATCH")
        observed = _owner_time(event.observed_at)
        if previous_time is not None and observed < previous_time:
            _fail("REFERENCE_MISMATCH")
        if event.event_kind.value == "GENERATION_PUBLISHED":
            if event.published_generation_revision != last_generation + 1:
                _fail("REFERENCE_MISMATCH")
            last_generation = event.published_generation_revision
            current_generation, current_publish = last_generation, event.event_sha256
        elif (
            current_generation is None
            or event.target_generation_revision != current_generation
            or event.target_publish_event_sha256 != current_publish
        ):
            _fail("REFERENCE_MISMATCH")
        else:
            current_generation, current_publish = None, None
        previous, previous_time = event, observed


def _validate_relations(index: Mapping[str, Mapping[str, Any]], bundle: Mapping[str, Any]) -> None:
    def ref(d: str, kind: str) -> Mapping[str, Any]:
        value = index.get(d)
        if value is None or value["record_type"] != kind: _fail("REFERENCE_MISMATCH")
        return value
    typed_digests: set[str] = set(index)
    for record in index.values():
        if record["record_type"] == "Task089AdoptionRequestFixtureV1":
            typed_digests.add(record["semantic_key_sha256"])
        if record["record_type"] == "Task089CustodyFixtureV1":
            receipt = record["custody_receipt"]
            typed_digests.update({receipt["receipt_sha256"], receipt["custody_binding_sha256"]})
            for event in record["generation_events"]:
                typed_digests.add(event["event_sha256"])
                if event["custody_binding_sha256"] is not None:
                    typed_digests.add(event["custody_binding_sha256"])
    for record in index.values():
        if record["record_type"] == "Task089ProducerOutputFixtureV1" and record["content_sha256"] in typed_digests:
            _fail("REFERENCE_MISMATCH")
    for d, rec in index.items():
        kind = rec["record_type"]
        if kind == "Task089PurposeGrantFixtureV1":
            s = ref(rec["subject_sha256"], "Task089SubjectFixtureV1")
            if rec["q1_readback_sha256"] is not None:
                o = ref(rec["q1_readback_sha256"], "Task089CurrentReadbackFixtureV1")
                q_r = ref(o["request_sha256"], "Task089AdoptionRequestFixtureV1")
                q_p = ref(q_r["producer_sha256"], "Task089ProducerOutputFixtureV1")
                if o["observation_kind"] != "SNAPSHOT" or q_p["asset_role"] != "CANONICAL_PCM" or q_r["subject_sha256"] != s["record_sha256"]: _fail("REFERENCE_MISMATCH")
        elif kind == "Task089ProducerOutputFixtureV1":
            s = ref(rec["subject_sha256"], "Task089SubjectFixtureV1"); g = ref(rec["grant_sha256"], "Task089PurposeGrantFixtureV1")
            if g["subject_sha256"] != s["record_sha256"] or g["output_role"] != rec["asset_role"]: _fail("ROLE_MISMATCH")
            if rec["asset_role"] == "RAW_CAPTURE" and (rec["upstream_producer_sha256"] is not None or rec["q1_readback_sha256"] is not None): _fail("REFERENCE_MISMATCH")
            if rec["asset_role"] == "CANONICAL_PCM":
                p = ref(rec["upstream_producer_sha256"], "Task089ProducerOutputFixtureV1")
                if p["asset_role"] != "RAW_CAPTURE": _fail("ROLE_MISMATCH")
                if p["subject_sha256"] != s["record_sha256"] or rec["q1_readback_sha256"] is not None: _fail("REFERENCE_MISMATCH")
            if rec["asset_role"] in {"PROCESSED_SPEECH_CONTINUOUS", "TRAINING_COPY"}:
                q = ref(rec["q1_readback_sha256"], "Task089CurrentReadbackFixtureV1")
                q_r = ref(q["request_sha256"], "Task089AdoptionRequestFixtureV1")
                q_p = ref(q_r["producer_sha256"], "Task089ProducerOutputFixtureV1")
                if q["observation_kind"] != "SNAPSHOT" or g["q1_readback_sha256"] != q["record_sha256"] or q_r["subject_sha256"] != s["record_sha256"] or q_p["asset_role"] != "CANONICAL_PCM": _fail("REFERENCE_MISMATCH")
                if rec["asset_role"] == "PROCESSED_SPEECH_CONTINUOUS" and rec["upstream_producer_sha256"] is not None: _fail()
                if rec["asset_role"] == "TRAINING_COPY":
                    upstream = ref(rec["upstream_producer_sha256"], "Task089ProducerOutputFixtureV1")
                    if upstream["asset_role"] != "PROCESSED_SPEECH_CONTINUOUS": _fail("ROLE_MISMATCH")
                    if upstream["subject_sha256"] != s["record_sha256"] or upstream["q1_readback_sha256"] != q["record_sha256"]: _fail("REFERENCE_MISMATCH")
        elif kind == "Task089CustodyFixtureV1":
            p = ref(rec["producer_sha256"], "Task089ProducerOutputFixtureV1")
            g = ref(p["grant_sha256"], "Task089PurposeGrantFixtureV1")
            s = ref(p["subject_sha256"], "Task089SubjectFixtureV1")
            receipt = PrivateMediaCustodyReceipt.from_mapping(rec["custody_receipt"])
            event_maps = rec["generation_events"]
            _validate_owner_event_chain(event_maps)
            publications = [x for x in event_maps if x.get("event_sha256") == receipt.generation_event_sha256]
            published = publications[0] if len(publications) == 1 else None
            media_digest = sha256_bytes(b"BAI:TASK089:FIXTURE_MEDIA:V1\0" + canonical_json_bytes(p["media"]))
            if (receipt.content_sha256 != p["content_sha256"] or receipt.media_metadata_sha256 != media_digest or receipt.artifact_class is not _ROLE[p["asset_role"]][4] or receipt.purpose != _ROLE[p["asset_role"]][2] or receipt.owner_subject_revision_sha256 != s["record_sha256"] or receipt.consent_rights_revision_sha256 != g["record_sha256"] or published is None or published["event_kind"] != "GENERATION_PUBLISHED" or published["published_generation_revision"] != receipt.generation_revision or published["logical_slot_ref"] != receipt.logical_slot_ref or receipt.event_head_sha256 != published["event_sha256"] or published["opaque_artifact_id"] != receipt.opaque_artifact_id or published["artifact_class"] != receipt.artifact_class.value or published["purpose"] != receipt.purpose or published["owner_subject_revision_sha256"] != receipt.owner_subject_revision_sha256 or published["consent_rights_revision_sha256"] != receipt.consent_rights_revision_sha256 or published["custody_binding_sha256"] != receipt.custody_binding_sha256 or published["content_sha256"] != receipt.content_sha256 or published["media_metadata_sha256"] != receipt.media_metadata_sha256 or published["opened_physical_identity_sha256"] != receipt.opened_physical_identity_sha256 or published["cipher_backend_identity_sha256"] != receipt.cipher_backend_identity_sha256 or published["observed_at"] != receipt.observed_at or published["fresh_until"] != receipt.fresh_until): _fail("REFERENCE_MISMATCH")
        elif kind == "Task089AdoptionRequestFixtureV1":
            p = ref(rec["producer_sha256"], "Task089ProducerOutputFixtureV1"); c = ref(rec["custody_sha256"], "Task089CustodyFixtureV1"); g = ref(rec["grant_sha256"], "Task089PurposeGrantFixtureV1"); s = ref(rec["subject_sha256"], "Task089SubjectFixtureV1")
            if p["subject_sha256"] != s["record_sha256"] or p["grant_sha256"] != g["record_sha256"] or c["producer_sha256"] != p["record_sha256"]: _fail("REFERENCE_MISMATCH")
            receipt = PrivateMediaCustodyReceipt.from_mapping(c["custody_receipt"])
            events = c["generation_events"]
            def tombstone_for(event: Mapping[str, Any], generation: int, published_sha256: str) -> bool:
                return event["event_kind"] in {"GENERATION_REVOKED", "GENERATION_QUARANTINED", "GENERATION_EXPIRED"} and event["target_generation_revision"] == generation and event["target_publish_event_sha256"] == published_sha256
            if rec["predecessor_registration_sha256"] is None:
                if receipt.generation_revision != 1 or receipt.predecessor_receipt_sha256 is not None or len(events) not in {1, 2} or events[0]["event_sha256"] != receipt.generation_event_sha256 or events[0]["event_kind"] != "GENERATION_PUBLISHED" or events[0]["event_revision"] != 1 or events[0]["predecessor_event_sha256"] is not None or events[0]["published_generation_revision"] != 1 or (len(events) == 2 and not tombstone_for(events[1], 1, events[0]["event_sha256"])): _fail("REFERENCE_MISMATCH")
            else:
                a = ref(rec["predecessor_registration_sha256"], "Task089RegistrationFixtureV1")
                if a["outcome"] != "REGISTERED": _fail("REFERENCE_MISMATCH")
                old_r = ref(a["request_sha256"], "Task089AdoptionRequestFixtureV1"); old_c = ref(old_r["custody_sha256"], "Task089CustodyFixtureV1")
                old_receipt = PrivateMediaCustodyReceipt.from_mapping(old_c["custody_receipt"])
                old_events = old_c["generation_events"]; new_events = c["generation_events"]
                old_p = ref(old_r["producer_sha256"], "Task089ProducerOutputFixtureV1")
                suffix = new_events[len(old_events):]
                position = 0
                if old_events[-1]["event_kind"] == "GENERATION_PUBLISHED" and suffix and tombstone_for(suffix[0], old_receipt.generation_revision, old_receipt.generation_event_sha256):
                    position = 1
                if position >= len(suffix) or suffix[position]["event_sha256"] != receipt.generation_event_sha256 or suffix[position]["event_kind"] != "GENERATION_PUBLISHED" or suffix[position]["published_generation_revision"] != receipt.generation_revision:
                    _fail("REFERENCE_MISMATCH")
                position += 1
                if position < len(suffix) and tombstone_for(suffix[position], receipt.generation_revision, receipt.generation_event_sha256):
                    position += 1
                if receipt.generation_revision != old_receipt.generation_revision + 1 or receipt.predecessor_receipt_sha256 != old_receipt.receipt_sha256 or a["asset_snapshot"]["custody_receipt_sha256"] != old_receipt.receipt_sha256 or canonical_json_bytes(old_events) != canonical_json_bytes(new_events[:len(old_events)]) or position != len(suffix) or old_r["subject_sha256"] != rec["subject_sha256"] or old_r["grant_sha256"] != rec["grant_sha256"] or old_receipt.logical_slot_ref != receipt.logical_slot_ref or old_p["asset_role"] != p["asset_role"] or old_p["record_sha256"] == p["record_sha256"] or (old_p["producer_operation_id"], old_p["output_sequence"]) == (p["producer_operation_id"], p["output_sequence"]) or (old_p["producer_operation_id"] == p["producer_operation_id"] and p["output_sequence"] <= old_p["output_sequence"]) or a["registry_generation"] > rec["expected_registry_generation"]: _fail("REFERENCE_MISMATCH")
        elif kind == "Task089RegistrationFixtureV1":
            r = ref(rec["request_sha256"], "Task089AdoptionRequestFixtureV1")
            if rec["outcome"] == "REGISTERED":
                p = ref(r["producer_sha256"], "Task089ProducerOutputFixtureV1"); c = ref(r["custody_sha256"], "Task089CustodyFixtureV1"); snap = rec["asset_snapshot"]
                receipt = PrivateMediaCustodyReceipt.from_mapping(c["custody_receipt"])
                expected_uri = f"asset://{p and ref(p['subject_sha256'], 'Task089SubjectFixtureV1')['production_job_id']}/owner-voice/{p['asset_role'].lower()}/{snap['asset_id']}"
                if rec["registry_generation"] != r["expected_registry_generation"] + 1 or snap["production_job_id"] != ref(p["subject_sha256"], "Task089SubjectFixtureV1")["production_job_id"] or snap["asset_role"] != p["asset_role"] or snap["checksum"] != p["content_sha256"] or snap["producer_operation_id"] != r["adoption_operation_id"] or snap["custody_receipt_sha256"] != receipt.receipt_sha256 or snap["asset_version"] != 1 or snap["logical_uri"] != expected_uri: _fail("REFERENCE_MISMATCH")
            elif rec["outcome"] == "REJECTED_NO_WRITE" and rec["registry_generation"] != r["expected_registry_generation"]: _fail("REFERENCE_MISMATCH")
            elif rec["outcome"] == "COMPLETION_UNKNOWN" and rec["registry_generation"] not in {r["expected_registry_generation"], r["expected_registry_generation"] + 1}: _fail("REFERENCE_MISMATCH")
        elif kind == "Task089CurrentReadbackFixtureV1":
            r = ref(rec["request_sha256"], "Task089AdoptionRequestFixtureV1")
            if rec["observed_subject_sha256"] is not None:
                ref(rec["observed_subject_sha256"], "Task089SubjectFixtureV1")
            if rec["observed_grant_sha256"] is not None:
                ref(rec["observed_grant_sha256"], "Task089PurposeGrantFixtureV1")
            if rec["observed_custody_sha256"] is not None:
                ref(rec["observed_custody_sha256"], "Task089CustodyFixtureV1")
            if rec["observation_kind"] in {"SNAPSHOT", "NO_WRITE", "UNRESOLVED"}:
                a = ref(rec["registration_sha256"], "Task089RegistrationFixtureV1")
                if a["request_sha256"] != r["record_sha256"]: _fail("REFERENCE_MISMATCH")
                if rec["observation_kind"] == "SNAPSHOT":
                    selected = ref(rec["selected_registration_sha256"], "Task089RegistrationFixtureV1")
                    if a["outcome"] != "REGISTERED" or selected["outcome"] != "REGISTERED" or rec["selected_asset_id"] != selected["asset_snapshot"]["asset_id"] or rec["observed_registry_generation"] != selected["registry_generation"]: _fail("REFERENCE_MISMATCH")
                    selected_r = ref(selected["request_sha256"], "Task089AdoptionRequestFixtureV1")
                    ancestor = r
                    # A second supplied result for this exact R is structurally
                    # observable; assessment classifies it as a conflict rather
                    # than hiding it behind a false non-ancestor error.
                    allowed_selected = {
                        candidate["record_sha256"] for candidate in index.values()
                        if candidate["record_type"] == "Task089RegistrationFixtureV1"
                        and candidate["request_sha256"] == r["record_sha256"]
                    }
                    lineage = ancestor
                    while lineage["predecessor_registration_sha256"] is not None:
                        predecessor_a = ref(lineage["predecessor_registration_sha256"], "Task089RegistrationFixtureV1")
                        allowed_selected.add(predecessor_a["record_sha256"])
                        lineage = ref(predecessor_a["request_sha256"], "Task089AdoptionRequestFixtureV1")
                    if selected["record_sha256"] not in allowed_selected:
                        _fail("REFERENCE_MISMATCH")
                    while selected_r["record_sha256"] != ancestor["record_sha256"] and ancestor["predecessor_registration_sha256"] is not None:
                        ancestor_a = ref(ancestor["predecessor_registration_sha256"], "Task089RegistrationFixtureV1")
                        ancestor = ref(ancestor_a["request_sha256"], "Task089AdoptionRequestFixtureV1")
                    if selected_r["record_sha256"] != ancestor["record_sha256"] or selected_r["subject_sha256"] != r["subject_sha256"] or index[selected_r["producer_sha256"]]["asset_role"] != index[r["producer_sha256"]]["asset_role"]: _fail("REFERENCE_MISMATCH")
                elif rec["observation_kind"] == "NO_WRITE":
                    if a["outcome"] != "REJECTED_NO_WRITE" or rec["observed_subject_sha256"] != r["subject_sha256"] or rec["observed_grant_sha256"] != r["grant_sha256"] or rec["observed_custody_sha256"] != r["custody_sha256"] or rec["observed_registry_generation"] != a["registry_generation"]: _fail("REFERENCE_MISMATCH")
                elif rec["observation_kind"] == "UNRESOLVED" and (a["outcome"] != "COMPLETION_UNKNOWN" or rec["observed_registry_generation"] != a["registry_generation"]): _fail("REFERENCE_MISMATCH")
    # graph cycles are invalid even when every named edge exists.
    visiting: set[str] = set(); done: set[str] = set()
    def walk(d: str) -> None:
        if d in visiting: _fail("CYCLIC_FIXTURE")
        if d in done: return
        visiting.add(d)
        for child in _refs(index[d]): walk(child)
        visiting.remove(d); done.add(d)
    for d in index: walk(d)


def _validate_bundle_mapping(body: Mapping[str, Any]) -> None:
    if type(body) is not dict:
        _fail()
    expected = {"record_type", "schema_version", "fixture_case", "fixture_session", "observed_at", "records", "fixture_only", "authority_created", "execution_authorized", "owner_port_contract_status", "bundle_sha256"}
    if set(body) != expected or body.get("record_type") != "Task089FixtureBundleV1" or type(body.get("schema_version")) is not int or body.get("schema_version") != 1 or body.get("fixture_only") is not True or body.get("authority_created") is not False or body.get("execution_authorized") is not False or body.get("owner_port_contract_status") != "NOT_BOUND" or type(body.get("fixture_case")) is not str or not (_TOKEN.fullmatch(body["fixture_case"]) and body["fixture_case"].startswith("fixture-")) or type(body.get("fixture_session")) is not str or not (_TOKEN.fullmatch(body["fixture_session"]) and body["fixture_session"].startswith("fixture-")) or _time(body.get("observed_at")) is None or type(body.get("records")) is not list or not 1 <= len(body["records"]) <= 256 or _digest(body.get("bundle_sha256")) != _bundle_digest(body): _fail()
    index: dict[str, Mapping[str, Any]] = {}
    for rec in body["records"]:
        if type(rec) is not dict: _fail()
        _validate_record(rec, index)
        if rec["record_sha256"] in index: _fail("REFERENCE_MISMATCH")
        index[rec["record_sha256"]] = rec
    for rec in index.values():
        if rec["record_type"] == "Task089SubjectFixtureV1" and rec["fixture_case"] != body["fixture_case"]: _fail("REFERENCE_MISMATCH")
    _validate_relations(index, body)


def _validate_nominal_output(body: Mapping[str, Any], cls: type[Any]) -> None:
    if type(body) is not dict:
        _fail()
    if cls is Task089AdoptionAssessment:
        _common(body, "Task089AdoptionAssessmentFixtureV1", _OUTPUT_FIELDS["Task089AdoptionAssessmentFixtureV1"])
        if body["fixture_state"] not in {"CONSISTENT_REGISTERED", "NOT_READY", "UNKNOWN", "STALE", "CONFLICT"} or body["reason_code"] not in {"FIXTURE_RELATIONS_MATCH", "REGISTRATION_REJECTED", "OUTCOME_UNKNOWN", "SESSION_NOT_CURRENT", "CURRENTNESS_MISMATCH", "PURPOSE_NOT_ALLOWED", "SEMANTIC_CONFLICT"} or body["guard_status"] != "UNAVAILABLE" or body["required_owner_contracts"] != ["CANONICAL_ASSET", "PRIVATE_CUSTODY", "PURPOSE_CONSENT", "OWNER_SUBJECT"]:
            _fail()
    elif cls is Task089Q2PairHandoff:
        _common(body, "Task089Q2PairHandoffFixtureV1", _OUTPUT_FIELDS["Task089Q2PairHandoffFixtureV1"])
        if body["consumer_owner_task"] != "TASK-090" or body["terminal_binding_status"] != "NOT_BOUND":
            _fail()
    else:
        _fail()


def parse_fixture_bundle(payload: bytes | str) -> Task089FixtureBundle:
    body = _strict_payload(payload)
    _local_schema_admission(body)
    _validate_bundle_mapping(body)
    return _new_bundle(body)


def _revalidated(bundle: Task089FixtureBundle) -> tuple[dict[str, Any], dict[str, Mapping[str, Any]]]:
    if type(bundle) is not Task089FixtureBundle: _fail()
    parsed = parse_fixture_bundle(canonical_json_bytes(bundle.to_dict()))
    body = parsed.to_dict()
    return body, {r["record_sha256"]: r for r in body["records"]}


def _closure(index: Mapping[str, Mapping[str, Any]], roots: Sequence[str]) -> set[str]:
    closure: set[str] = set(); pending = list(roots)
    while pending:
        d = pending.pop()
        if d in closure: continue
        rec = index.get(d)
        if rec is None: _fail("REFERENCE_MISMATCH")
        closure.add(d); pending.extend(_refs(rec))
        if rec["record_type"] == "Task089AdoptionRequestFixtureV1":
            coord = _coordinate(rec, index)
            for other in index.values():
                if other["record_type"] == "Task089AdoptionRequestFixtureV1" and (other["semantic_key_sha256"] == rec["semantic_key_sha256"] or _coordinate(other, index) == coord): pending.append(other["record_sha256"])
                if other["record_type"] == "Task089RegistrationFixtureV1" and other["request_sha256"] == rec["record_sha256"]: pending.append(other["record_sha256"])
        if rec["record_type"] == "Task089RegistrationFixtureV1":
            for other in index.values():
                if other["record_type"] == "Task089RegistrationFixtureV1" and other["request_sha256"] == rec["request_sha256"]: pending.append(other["record_sha256"])
                if rec["outcome"] == "REGISTERED" and other["record_type"] == "Task089RegistrationFixtureV1" and other["outcome"] == "REGISTERED" and (other["asset_snapshot"]["asset_id"] == rec["asset_snapshot"]["asset_id"] or other["asset_snapshot"]["logical_uri"] == rec["asset_snapshot"]["logical_uri"]): pending.append(other["record_sha256"])
        if rec["record_type"] == "Task089CustodyFixtureV1":
            for other in index.values():
                if other["record_type"] == "Task089CustodyFixtureV1" and other["producer_sha256"] == rec["producer_sha256"]: pending.append(other["record_sha256"])
    return closure


def _coordinate(r: Mapping[str, Any], index: Mapping[str, Mapping[str, Any]]) -> tuple[str, str, str, str, str]:
    p = index[r["producer_sha256"]]
    return (r["subject_sha256"], r["producer_sha256"], r["custody_sha256"], r["grant_sha256"], p["asset_role"])


def _assessment_body(bundle: Mapping[str, Any], index: Mapping[str, Mapping[str, Any]], r: Mapping[str, Any], o: Mapping[str, Any]) -> dict[str, Any]:
    registration = o["registration_sha256"]
    state: str; reason: str
    regs = [x for x in index.values() if x["record_type"] == "Task089RegistrationFixtureV1"]
    requests = [x for x in index.values() if x["record_type"] == "Task089AdoptionRequestFixtureV1"]
    registered = [x for x in regs if x["outcome"] == "REGISTERED"]
    producer_custody_counts: dict[str, int] = {}
    for custody in (x for x in index.values() if x["record_type"] == "Task089CustodyFixtureV1"):
        producer_custody_counts[custody["producer_sha256"]] = producer_custody_counts.get(custody["producer_sha256"], 0) + 1
    custody_conflict = any(count > 1 for count in producer_custody_counts.values())
    request_result_counts: dict[str, int] = {}
    for result in regs:
        request_result_counts[result["request_sha256"]] = request_result_counts.get(result["request_sha256"], 0) + 1
    historical_result_conflict = any(count > 1 for count in request_result_counts.values())
    asset_conflict = len({x["asset_snapshot"]["asset_id"] for x in registered}) != len(registered) or len({x["asset_snapshot"]["logical_uri"] for x in registered}) != len(registered)
    requests_by_digest = {q["record_sha256"]: q for q in requests}
    coordinate_registered_counts: dict[tuple[str, str, str, str, str], int] = {}
    for result in registered:
        request = requests_by_digest[result["request_sha256"]]
        coordinate = _coordinate(request, index)
        coordinate_registered_counts[coordinate] = coordinate_registered_counts.get(coordinate, 0) + 1
    semantic_key_operations: dict[str, set[str]] = {}
    for request in requests:
        semantic_key_operations.setdefault(request["semantic_key_sha256"], set()).add(request["adoption_operation_id"])
    same_key_operation_conflict = any(len(operations) > 1 for operations in semantic_key_operations.values())
    same_output_conflict = any(count > 1 for count in coordinate_registered_counts.values())
    if custody_conflict or historical_result_conflict or asset_conflict or same_output_conflict or same_key_operation_conflict:
        state, reason = "CONFLICT", "SEMANTIC_CONFLICT"
    elif o["observation_kind"] == "RESTARTED" or o["fixture_session"] != bundle["fixture_session"]:
        state, reason = "UNKNOWN", "SESSION_NOT_CURRENT"
    elif o["observation_kind"] in {"UNAVAILABLE", "UNRESOLVED"}:
        state, reason = "UNKNOWN", "OUTCOME_UNKNOWN"
    elif _time(o["observed_at"]) > _time(bundle["observed_at"]) or _time(bundle["observed_at"]) >= _time(o["fresh_until"]):
        state, reason = "STALE", "CURRENTNESS_MISMATCH"
    else:
        p = index[r["producer_sha256"]]; g = index[r["grant_sha256"]]; c = index[r["custody_sha256"]]
        if g["decision"] != "ALLOW": state, reason = "NOT_READY", "PURPOSE_NOT_ALLOWED"
        elif o["observation_kind"] == "NO_WRITE": state, reason = "NOT_READY", "REGISTRATION_REJECTED"
        else:
            selected = index[o["selected_registration_sha256"]]
            receipt = PrivateMediaCustodyReceipt.from_mapping(c["custody_receipt"])
            events = [PrivateMediaGenerationEvent.from_mapping(x) for x in c["generation_events"]]
            current = derive_generation_currentness(events, observed_at=bundle["observed_at"], expected_event_head_sha256=events[-1].event_sha256, expected_event_count=len(events), expected_current_custody_binding_sha256=receipt.custody_binding_sha256)
            q1_good = True
            if g["q1_readback_sha256"] is not None:
                q1_o = index[g["q1_readback_sha256"]]
                q1_r = index[q1_o["request_sha256"]]
                q1_e = _assessment_body(bundle, index, q1_r, q1_o)
                q1_p = index[q1_r["producer_sha256"]]
                q1_good = q1_e["fixture_state"] == "CONSISTENT_REGISTERED" and q1_p["asset_role"] == "CANONICAL_PCM" and q1_r["subject_sha256"] == r["subject_sha256"]
            good = selected["record_sha256"] == registration and o["selected_asset_id"] == selected["asset_snapshot"]["asset_id"] and o["observed_subject_sha256"] == r["subject_sha256"] and o["observed_grant_sha256"] == r["grant_sha256"] and o["observed_custody_sha256"] == r["custody_sha256"] and _time(g["issued_at"]) <= _time(o["observed_at"]) <= _time(bundle["observed_at"]) < _time(g["expires_at"]) and _owner_time(receipt.observed_at) <= _time(bundle["observed_at"]) < _owner_time(receipt.fresh_until) and current.state is CurrentnessState.CURRENT and q1_good
            state, reason = ("CONSISTENT_REGISTERED", "FIXTURE_RELATIONS_MATCH") if good else ("STALE", "CURRENTNESS_MISMATCH")
    body = {"record_type": "Task089AdoptionAssessmentFixtureV1", "schema_version": 1, "adapter_owner_task": TASK_OWNER, "canonical_asset_owner_task": "TASK-003", "fixture_only": True, "authority_created": False, "execution_authorized": False, "owner_port_contract_status": "NOT_BOUND", "private_media_effect_count": 0, "asset_adoption_count": 0, "request_sha256": r["record_sha256"], "readback_sha256": o["record_sha256"], "registration_sha256": registration, "fixture_state": state, "reason_code": reason, "guard_status": "UNAVAILABLE", "required_owner_contracts": ["CANONICAL_ASSET", "PRIVATE_CUSTODY", "PURPOSE_CONSENT", "OWNER_SUBJECT"], "record_sha256": None}
    body["record_sha256"] = _record_digest(body["record_type"], body)
    return body


def assess_adoption_fixture(bundle: Task089FixtureBundle, *, request_sha256: str, readback_sha256: str) -> Task089AdoptionAssessment:
    body, index = _revalidated(bundle); _digest(request_sha256); _digest(readback_sha256)
    r = index.get(request_sha256); o = index.get(readback_sha256)
    if r is None or o is None or r["record_type"] != "Task089AdoptionRequestFixtureV1" or o["record_type"] != "Task089CurrentReadbackFixtureV1" or o["request_sha256"] != request_sha256: _fail("REFERENCE_MISMATCH")
    if _closure(index, [request_sha256, readback_sha256]) != set(index): _fail("REFERENCE_MISMATCH")
    return _new_output(Task089AdoptionAssessment, _assessment_body(body, index, r, o))


def build_q2_pair_handoff_fixture(bundle: Task089FixtureBundle, *, processed_request_sha256: str, processed_readback_sha256: str, copy_request_sha256: str, copy_readback_sha256: str) -> Task089Q2PairHandoff:
    body, index = _revalidated(bundle)
    roots = (processed_request_sha256, processed_readback_sha256, copy_request_sha256, copy_readback_sha256)
    for d in roots: _digest(d)
    prs, pro, crs, cro = (index.get(d) for d in roots)
    if any(x is None for x in (prs, pro, crs, cro)) or prs["record_type"] != "Task089AdoptionRequestFixtureV1" or crs["record_type"] != "Task089AdoptionRequestFixtureV1" or pro["record_type"] != "Task089CurrentReadbackFixtureV1" or cro["record_type"] != "Task089CurrentReadbackFixtureV1": _fail("PAIR_MISMATCH")
    if pro["request_sha256"] != prs["record_sha256"] or cro["request_sha256"] != crs["record_sha256"]:
        _fail("PAIR_MISMATCH")
    if _closure(index, roots) != set(index): _fail("PAIR_MISMATCH")
    pa = _assessment_body(body, index, prs, pro); ca = _assessment_body(body, index, crs, cro)
    if pa["fixture_state"] != "CONSISTENT_REGISTERED" or ca["fixture_state"] != "CONSISTENT_REGISTERED":
        _fail("PAIR_MISMATCH")
    pp = index[prs["producer_sha256"]]; cp = index[crs["producer_sha256"]]
    pg = index[pp["grant_sha256"]]; cg = index[cp["grant_sha256"]]
    p_registration = index[pro["registration_sha256"]]; c_registration = index[cro["registration_sha256"]]
    p_custody = index[prs["custody_sha256"]]; c_custody = index[crs["custody_sha256"]]
    if pp["asset_role"] != "PROCESSED_SPEECH_CONTINUOUS" or cp["asset_role"] != "TRAINING_COPY" or cp["upstream_producer_sha256"] != pp["record_sha256"] or pp["producer_operation_id"] != cp["producer_operation_id"] or pg["policy_revision"] != cg["policy_revision"] or p_registration["asset_snapshot"]["asset_id"] == c_registration["asset_snapshot"]["asset_id"] or p_registration["asset_snapshot"]["logical_uri"] == c_registration["asset_snapshot"]["logical_uri"] or p_custody["custody_receipt"]["receipt_sha256"] == c_custody["custody_receipt"]["receipt_sha256"] or len({prs["record_sha256"], pro["record_sha256"], crs["record_sha256"], cro["record_sha256"], pp["record_sha256"], cp["record_sha256"]}) != 6: _fail("PAIR_MISMATCH")
    q1 = pp["q1_readback_sha256"]
    if q1 != cp["q1_readback_sha256"] or index[prs["subject_sha256"]]["record_sha256"] != index[crs["subject_sha256"]]["record_sha256"]: _fail("PAIR_MISMATCH")
    body_out = {"record_type": "Task089Q2PairHandoffFixtureV1", "schema_version": 1, "adapter_owner_task": TASK_OWNER, "canonical_asset_owner_task": "TASK-003", "fixture_only": True, "authority_created": False, "execution_authorized": False, "owner_port_contract_status": "NOT_BOUND", "private_media_effect_count": 0, "asset_adoption_count": 0, "subject_sha256": prs["subject_sha256"], "q1_readback_sha256": q1, "q2_producer_operation_id": pp["producer_operation_id"], "processed_request_sha256": processed_request_sha256, "processed_readback_sha256": processed_readback_sha256, "copy_request_sha256": copy_request_sha256, "copy_readback_sha256": copy_readback_sha256, "processed_assessment_sha256": pa["record_sha256"], "copy_assessment_sha256": ca["record_sha256"], "consumer_owner_task": "TASK-090", "terminal_binding_status": "NOT_BOUND", "record_sha256": None}
    body_out["record_sha256"] = _record_digest(body_out["record_type"], body_out)
    return _new_output(Task089Q2PairHandoff, body_out)


__all__ = ["Task089ContractError", "Task089FixtureBundle", "Task089AdoptionAssessment", "Task089Q2PairHandoff", "parse_fixture_bundle", "assess_adoption_fixture", "build_q2_pair_handoff_fixture"]
