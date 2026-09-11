"""TASK-048 Project-bound, transaction-only meter display-policy state.

The only writer is the public Project save coordinator. Its integrity checks
may hash arbitrary bound child bytes (including audio); this module does not
decode audio, use audio as policy input, or grant execution/currentness authority
from serialized receipts. Live snapshots are local, context-bound read results,
not fixture seals, trusted-time proofs, or transport authentication.
"""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
from importlib import resources
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import Any, Iterator, Mapping
import uuid
import weakref

from jsonschema import Draft202012Validator

from .errors import ProductError, ProductErrorCategory
from .ids import validate_project_id
from .product_project import ProductProjectManifest, ProjectChildBinding
from .product_project_store import ProductProjectManifestStore
from .project_save import ProductProjectSaveCoordinator, ProjectSaveJournalStore
from .schema_contracts import validate_instance
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso
from .voice_quality_meter_display_policy import MeterDisplayPolicyRevision


CHILD_PATH = "voice-quality/meter-policy-state.json"
CHILD_FORMAT = "bai-video-production.voice-quality-meter-policy-state"
CHILD_VERSION = "1.0.0"
SCHEMA_NAME = "voice-quality-meter-policy-state.schema.json"
SCHEMA_URI = "https://bai-video-production.local/schemas/voice-quality-meter-policy-state.schema.json"
MAX_INTEGER = 9_007_199_254_740_991
MAX_CHILD_BYTES = 4_194_304
MAX_REQUEST_BYTES = 4_096
MAX_EVENTS = 4_096
MAX_POLICIES = 1_024
MAX_DEPTH = 16
MAX_NODES = 131_072
MAX_STRING = 256
REQUEST_DOMAIN = b"TASK048_METER_POLICY_OPERATION_REQUEST_V1\0"
EVENT_DOMAIN = b"TASK048_METER_POLICY_OPERATION_EVENT_V1\0"
STATE_DOMAIN = b"TASK048_METER_POLICY_PROJECT_CHILD_V1\0"
RECEIPT_DOMAIN = b"TASK048_METER_POLICY_OPERATION_RECEIPT_V1\0"
READBACK_DOMAIN = b"TASK048_METER_POLICY_READBACK_EVIDENCE_V1\0"
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_PUBLIC_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_ENTRYPOINTS = frozenset({"state", "request", "policy", "operation_receipt", "readback_evidence"})
_TERMINAL = frozenset({"COMMITTED", "ABANDONED"})
_AUTHORITY = {
    "authority_created": False,
    "quality_pass_issued": False,
    "capture_gain_obs_authorized": False,
    "consent_asset_training_authorized": False,
    "temporal_freshness_confirmed": False,
    "production_authorized": False,
}
_IO_BOUNDARY = {
    "audio_semantic_decode_executed": False,
    "audio_used_as_policy_input": False,
    "project_integrity_hash_reads_possible": True,
}
_SNAPSHOT_CONSTRUCTOR = object()


class MeterPolicyStoreError(ProductError):
    """Public-safe failure: never retain input bodies or host paths in details."""

    def __init__(self, reason: str, *, operation_id: str | None = None) -> None:
        super().__init__(
            f"ERR_TASK048_METER_{reason}",
            f"Meter policy operation failed: {reason}",
            ProductErrorCategory.STATE,
            False,
            operation_id=operation_id,
        )
        self.reason = reason


def _fail(reason: str) -> None:
    raise MeterPolicyStoreError(reason)


def _positive(value: Any, *, maximum: int = MAX_INTEGER, minimum: int = 1) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        _fail("INVALID_INTEGER")
    return value


def _uuid(value: Any) -> str:
    if type(value) is not str or _UUID.fullmatch(value) is None:
        _fail("INVALID_UUID")
    return value


def _digest(value: Any) -> str:
    if type(value) is not str or _DIGEST.fullmatch(value) is None:
        _fail("INVALID_DIGEST")
    return value


def _project_id(value: Any) -> str:
    if type(value) is not str:
        _fail("INVALID_PROJECT_ID")
    try:
        return validate_project_id(value)
    except (TypeError, ValueError):
        raise MeterPolicyStoreError("INVALID_PROJECT_ID") from None


def _snapshot_json(
    value: Any,
    *,
    max_depth: int = MAX_DEPTH,
    max_nodes: int = MAX_NODES,
    max_string: int = MAX_STRING,
) -> Any:
    """Copy exact built-in JSON types without invoking caller serialization."""
    nodes = 0
    active: set[int] = set()

    def visit(item: Any, depth: int) -> Any:
        nonlocal nodes
        nodes += 1
        if nodes > max_nodes or depth > max_depth:
            _fail("JSON_LIMIT")
        kind = type(item)
        if item is None or kind is bool:
            return item
        if kind is int:
            if item.bit_length() > 4096:
                _fail("JSON_LIMIT")
            return item
        if kind is float:
            if not math.isfinite(item):
                _fail("NONFINITE")
            return item
        if kind is str:
            if len(item) > max_string:
                _fail("JSON_LIMIT")
            try:
                item.encode("utf-8", "strict")
            except UnicodeError:
                raise MeterPolicyStoreError("INVALID_UTF8") from None
            return item
        if kind not in {dict, list}:
            _fail("INVALID_JSON_TYPE")
        if id(item) in active:
            _fail("JSON_CYCLE")
        active.add(id(item))
        try:
            if kind is list:
                return [visit(child, depth + 1) for child in item]
            result: dict[str, Any] = {}
            for key, child in item.items():
                if type(key) is not str:
                    _fail("INVALID_JSON_KEY")
                visit(key, depth + 1)
                result[key] = visit(child, depth + 1)
            return result
        finally:
            active.remove(id(item))

    try:
        return visit(value, 0)
    except RecursionError:
        raise MeterPolicyStoreError("JSON_LIMIT") from None


def _reject_constant(_value: str) -> None:
    _fail("NONFINITE")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_KEY")
        result[key] = value
    return result


def _strict_document(
    data: bytes,
    *,
    limit: int = MAX_CHILD_BYTES,
    max_depth: int = MAX_DEPTH,
    max_nodes: int = MAX_NODES,
    max_string: int = MAX_STRING,
) -> dict[str, Any]:
    if type(data) is not bytes or not 0 < len(data) <= limit:
        _fail("BYTE_LIMIT")
    if data.startswith(b"\xef\xbb\xbf"):
        _fail("BOM")
    try:
        decoded = data.decode("utf-8", "strict")
        document = json.loads(decoded, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)
    except (UnicodeError, ValueError, RecursionError):
        raise MeterPolicyStoreError("INVALID_JSON") from None
    result = _snapshot_json(document, max_depth=max_depth, max_nodes=max_nodes, max_string=max_string)
    if type(result) is not dict:
        _fail("INVALID_JSON_ROOT")
    return result


def _document(value: Any, *, limit: int = MAX_CHILD_BYTES) -> dict[str, Any]:
    if type(value) is bytes:
        return _strict_document(value, limit=limit)
    copied = _snapshot_json(value)
    if type(copied) is not dict:
        _fail("INVALID_JSON_ROOT")
    if not 0 < len(canonical_json_bytes(copied)) <= limit:
        _fail("BYTE_LIMIT")
    return copied


def _record_hash(domain: bytes, document: Mapping[str, Any], field: str) -> str:
    return sha256_bytes(domain + canonical_json_bytes({key: value for key, value in document.items() if key != field}))


def _check_hash(domain: bytes, document: dict[str, Any], field: str) -> None:
    if _digest(document.get(field)) != _record_hash(domain, document, field):
        _fail("DIGEST_MISMATCH")


def _require_local_refs(value: Any, *, root: bool = True) -> None:
    if type(value) is dict:
        if not root and "$id" in value:
            _fail("SCHEMA_REFERENCE")
        if "$ref" in value and (
            type(value["$ref"]) is not str or not value["$ref"].startswith("#/$defs/")
        ):
            _fail("SCHEMA_REFERENCE")
        for child in value.values():
            _require_local_refs(child, root=False)
    elif type(value) is list:
        for child in value:
            _require_local_refs(child, root=False)


def _load_entrypoints() -> dict[str, dict[str, Any]]:
    data = resources.files("ai_video_production.schema_resources").joinpath(SCHEMA_NAME).read_bytes()
    schema = _strict_document(data, max_depth=64, max_nodes=MAX_NODES, max_string=1024)
    if schema.get("$id") != SCHEMA_URI or schema.get("$ref") != "#/$defs/state":
        _fail("SCHEMA_IDENTITY")
    _require_local_refs(schema)
    Draft202012Validator.check_schema(schema)
    result = {}
    for entrypoint in sorted(_ENTRYPOINTS):
        wrapper = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": deepcopy(schema["$defs"]),
            "$ref": f"#/$defs/{entrypoint}",
        }
        Draft202012Validator.check_schema(wrapper)
        result[entrypoint] = wrapper
    return result


_SCHEMA_ENTRYPOINTS: dict[str, dict[str, Any]] | None = None


def _validate(entrypoint: str, document: dict[str, Any]) -> None:
    global _SCHEMA_ENTRYPOINTS
    if entrypoint not in _ENTRYPOINTS:
        _fail("SCHEMA_ENTRYPOINT")
    if _SCHEMA_ENTRYPOINTS is None:
        _SCHEMA_ENTRYPOINTS = _load_entrypoints()
    try:
        validate_instance(document, _SCHEMA_ENTRYPOINTS[entrypoint])
    except (ValueError, TypeError, KeyError):
        raise MeterPolicyStoreError("SCHEMA_INVALID") from None
    # JSON Schema's integer type also permits integral floats. This wire format
    # deliberately requires exact integer representations instead.
    if "schema_version" in document:
        _positive(document["schema_version"], maximum=1)


def _policy(document: dict[str, Any], *, schema_validated: bool = False) -> MeterDisplayPolicyRevision:
    if not schema_validated:
        _validate("policy", document)
    _positive(document["schema_version"], maximum=1)
    _positive(document["policy_revision"], maximum=MAX_POLICIES)
    if type(document["policy_ref"]) is not str or not _PUBLIC_ID.fullmatch(document["policy_ref"]):
        _fail("INVALID_POLICY_REF")
    for field in ("target_floor_dbfs", "target_ceiling_dbfs", "warning_dbfs", "true_clip_dbfs"):
        value = document[field]
        if type(value) is not float or not math.isfinite(value) or value > 0:
            _fail("INVALID_POLICY_NUMBER")
    try:
        policy = MeterDisplayPolicyRevision.from_dict(document)
    except (ValueError, TypeError, OverflowError):
        raise MeterPolicyStoreError("POLICY_INVALID") from None
    if canonical_json_bytes(policy.to_dict()) != canonical_json_bytes(document):
        _fail("POLICY_NONCANONICAL")
    return policy


def parse_meter_policy_operation_request(data: bytes) -> dict[str, Any]:
    document = _strict_document(data, limit=MAX_REQUEST_BYTES)
    return _validate_request(document)


def _validate_request(document: dict[str, Any], *, schema_validated: bool = False) -> dict[str, Any]:
    if len(canonical_json_bytes(document)) > MAX_REQUEST_BYTES:
        _fail("BYTE_LIMIT")
    if not schema_validated:
        _validate("request", document)
    _positive(document["schema_version"], maximum=1)
    _project_id(document["project_id"])
    _uuid(document["operation_id"])
    _positive(document["expected_project_revision"])
    _digest(document["expected_project_manifest_sha256"])
    if document["expected_child_sha256"] is not None:
        _digest(document["expected_child_sha256"])
    if document["expected_project_revision"] == MAX_INTEGER:
        _fail("PROJECT_REVISION_OVERFLOW")
    _check_hash(REQUEST_DOMAIN, document, "request_sha256")
    if document["action"] == "BOOTSTRAP":
        if not _PUBLIC_ID.fullmatch(document["payload"]["policy_ref"]):
            _fail("INVALID_POLICY_REF")
    elif document["action"] == "PUBLISH_POLICY":
        _policy(document["payload"]["policy_document"], schema_validated=schema_validated)
    else:
        _digest(document["payload"]["policy_revision_sha256"])
    return document


def serialize_meter_policy_operation_request(request: Mapping[str, Any]) -> bytes:
    document = _validate_request(_document(request, limit=MAX_REQUEST_BYTES))
    return canonical_json_bytes(document)


def _state_fields(
    project_id: str,
    policy_ref: str,
    count: int,
    published: list[str],
    selected: str | None,
    revoked: set[str],
) -> dict[str, Any]:
    return {
        "record_type": "Task048MeterPolicyProjectChildV1",
        "schema_version": 1,
        "project_id": project_id,
        "policy_ref": policy_ref,
        "state_revision": count,
        "published_policy_revision": len(published),
        "published_policy_sha256": published[-1] if published else None,
        "selected_policy_sha256": selected,
        "revoked_policy_sha256s": sorted(revoked),
        "io_boundary": dict(_IO_BOUNDARY),
    }


@dataclass(frozen=True, slots=True)
class _Replay:
    policies: dict[str, MeterDisplayPolicyRevision]
    operations: dict[str, dict[str, Any]]


def _replay(document: dict[str, Any]) -> _Replay:
    """Replay every event, hashing each previous canonical prefix incrementally."""
    _positive(document["state_revision"], maximum=MAX_EVENTS)
    _positive(document["published_policy_revision"], minimum=0, maximum=MAX_POLICIES)
    if document["state_revision"] != len(document["events"]):
        _fail("STATE_REVISION")
    project_id = _project_id(document["project_id"])
    policy_ref = document["policy_ref"]
    if not _PUBLIC_ID.fullmatch(policy_ref):
        _fail("INVALID_POLICY_REF")
    policies: dict[str, MeterDisplayPolicyRevision] = {}
    operations: dict[str, dict[str, Any]] = {}
    published: list[str] = []
    selected = None
    revoked: set[str] = set()
    previous_event = None
    previous_child = None
    previous_project_revision = 0
    # authority/canonical_owner_task/events are the first three sorted keys.
    prefix = b'{"authority":' + canonical_json_bytes(_AUTHORITY) + b',"canonical_owner_task":"TASK-048","events":['
    raw_prefix = hashlib.sha256(prefix)
    state_prefix = hashlib.sha256(STATE_DOMAIN + prefix)
    expected_fields: dict[str, Any] = {}
    for sequence, event in enumerate(document["events"], 1):
        _positive(event["schema_version"], maximum=1)
        if _positive(event["sequence"], maximum=MAX_EVENTS) != sequence:
            _fail("EVENT_SEQUENCE")
        if event["previous_event_sha256"] != previous_event:
            _fail("EVENT_PREDECESSOR")
        _check_hash(EVENT_DOMAIN, event, "event_sha256")
        request = _validate_request(event["request"], schema_validated=True)
        operation_id = request["operation_id"]
        if operation_id in operations:
            _fail("DUPLICATE_OPERATION")
        if request["project_id"] != project_id:
            _fail("PROJECT_MISMATCH")
        if request["expected_project_revision"] < previous_project_revision + 1:
            _fail("PROJECT_REVISION_CHAIN")
        if request["expected_child_sha256"] != previous_child:
            _fail("CHILD_PREDECESSOR")
        action = request["action"]
        payload = request["payload"]
        if sequence == 1:
            if action != "BOOTSTRAP" or payload["policy_ref"] != policy_ref:
                _fail("BOOTSTRAP_REQUIRED")
        elif action == "BOOTSTRAP":
            _fail("BOOTSTRAP_DUPLICATE")
        elif action == "PUBLISH_POLICY":
            policy = _policy(payload["policy_document"], schema_validated=True)
            policy_hash = payload["policy_document"]["policy_revision_sha256"]
            if (
                policy.policy_ref != policy_ref
                or policy.policy_revision != len(published) + 1
                or policy.predecessor_policy_sha256 != (published[-1] if published else None)
                or policy_hash in policies
            ):
                _fail("POLICY_CHAIN")
            published.append(policy_hash)
            policies[policy_hash] = policy
        elif action == "SELECT_POLICY":
            target = payload["policy_revision_sha256"]
            if not published or target != published[-1] or target in revoked:
                _fail("SELECTION_INVALID")
            if selected == target:
                _fail("NO_CHANGE")
            selected = target
        elif action == "REVOKE_POLICY":
            target = payload["policy_revision_sha256"]
            if target not in policies:
                _fail("REVOCATION_UNKNOWN")
            if target in revoked:
                _fail("ALREADY_REVOKED")
            revoked.add(target)
        else:
            _fail("ACTION_INVALID")
        operations[operation_id] = event
        event_bytes = (b"," if sequence > 1 else b"") + canonical_json_bytes(event)
        raw_prefix.update(event_bytes)
        state_prefix.update(event_bytes)
        expected_fields = _state_fields(project_id, policy_ref, sequence, published, selected, revoked)
        body_tail = b"]," + canonical_json_bytes(expected_fields)[1:]
        state_hasher = state_prefix.copy()
        state_hasher.update(body_tail)
        expected_fields["state_sha256"] = "sha256:" + state_hasher.hexdigest()
        full_hasher = raw_prefix.copy()
        full_hasher.update(b"]," + canonical_json_bytes(expected_fields)[1:])
        previous_child = "sha256:" + full_hasher.hexdigest()
        previous_event = event["event_sha256"]
        previous_project_revision = request["expected_project_revision"]
    actual_fields = {key: value for key, value in document.items() if key not in {"authority", "canonical_owner_task", "events"}}
    if canonical_json_bytes(actual_fields) != canonical_json_bytes(expected_fields):
        _fail("STATE_REPLAY_MISMATCH")
    return _Replay(policies, operations)


def _binding(manifest: ProductProjectManifest, *, absent_ok: bool = False) -> ProjectChildBinding | None:
    matches = []
    for binding in manifest.child_bindings:
        path_match = binding.relative_path.casefold() == CHILD_PATH.casefold()
        format_match = binding.format_id == CHILD_FORMAT
        if path_match or format_match:
            matches.append(binding)
    if not matches and absent_ok:
        return None
    if len(matches) != 1:
        _fail("BINDING_CONFLICT")
    binding = matches[0]
    if (
        binding.domain_owner != "TASK-048"
        or binding.relative_path != CHILD_PATH
        or binding.format_id != CHILD_FORMAT
        or binding.format_version != CHILD_VERSION
        or binding.required is not True
        or binding.dependency_hashes != ()
    ):
        _fail("BINDING_CONFLICT")
    return binding


def _validate_state(document: dict[str, Any], manifest: ProductProjectManifest) -> _Replay:
    if type(manifest) is not ProductProjectManifest:
        _fail("MANIFEST_TYPE")
    _validate("state", document)
    _check_hash(STATE_DOMAIN, document, "state_sha256")
    replay = _replay(document)
    binding = _binding(manifest)
    if manifest.project_id != document["project_id"]:
        _fail("PROJECT_MISMATCH")
    expected_result_revision = document["events"][-1]["request"]["expected_project_revision"] + 1
    if manifest.project_revision < expected_result_revision:
        _fail("FUTURE_PROJECT_REVISION")
    _positive(manifest.project_revision)
    if binding is None or binding.content_sha256 != sha256_bytes(canonical_json_bytes(document)):
        _fail("CHILD_CHECKSUM")
    return replay


def parse_meter_policy_state(data: bytes, *, enclosing_manifest: ProductProjectManifest) -> dict[str, Any]:
    document = _strict_document(data)
    if canonical_json_bytes(document) != data:
        _fail("CHILD_NONCANONICAL")
    _validate_state(document, enclosing_manifest)
    return document


def serialize_meter_policy_state(state: Mapping[str, Any], *, enclosing_manifest: ProductProjectManifest) -> bytes:
    document = _document(state)
    _validate_state(document, enclosing_manifest)
    return canonical_json_bytes(document)


def _validate_receipt(document: dict[str, Any]) -> dict[str, Any]:
    _validate("operation_receipt", document)
    _project_id(document["project_id"])
    _uuid(document["operation_id"])
    for field in ("request_sha256", "event_sha256", "observed_project_manifest_sha256", "observed_child_sha256"):
        _digest(document[field])
    _positive(document["committed_state_revision"], maximum=MAX_EVENTS)
    _positive(document["committed_project_revision"], minimum=2)
    _positive(document["observed_project_revision"], minimum=2)
    if document["observed_project_revision"] < document["committed_project_revision"]:
        _fail("FUTURE_PROJECT_REVISION")
    _check_hash(RECEIPT_DOMAIN, document, "receipt_sha256")
    return document


def parse_meter_policy_operation_receipt(data: bytes) -> dict[str, Any]:
    return _validate_receipt(_strict_document(data, limit=MAX_REQUEST_BYTES))


def serialize_meter_policy_operation_receipt(receipt: Mapping[str, Any]) -> bytes:
    return canonical_json_bytes(_validate_receipt(_document(receipt, limit=MAX_REQUEST_BYTES)))


@dataclass(frozen=True, slots=True)
class MeterPolicyQueryContext:
    project_id: str
    session_id: str
    consumer_epoch: str
    window_sequence: int
    request_id: str

    def __post_init__(self) -> None:
        _project_id(self.project_id)
        _uuid(self.session_id)
        _uuid(self.consumer_epoch)
        _positive(self.window_sequence)
        _uuid(self.request_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "session_id": self.session_id,
            "consumer_epoch": self.consumer_epoch,
            "window_sequence": self.window_sequence,
            "request_id": self.request_id,
        }


def _context(value: MeterPolicyQueryContext) -> dict[str, Any]:
    if type(value) is not MeterPolicyQueryContext:
        _fail("CONTEXT_MISMATCH")
    document = _snapshot_json(value.to_dict())
    MeterPolicyQueryContext(**document)
    return document


def _validate_readback(document: dict[str, Any]) -> dict[str, Any]:
    _validate("readback_evidence", document)
    _project_id(document["project_id"])
    _uuid(document["producer_epoch"])
    context = MeterPolicyQueryContext(**document["query_context"])
    if context.project_id != document["project_id"]:
        _fail("CONTEXT_MISMATCH")
    if document["status"] == "PROJECT_HEAD_MATCHED_SNAPSHOT":
        _positive(document["project_revision"])
        _positive(document["state_revision"], maximum=MAX_EVENTS)
        for field in ("project_manifest_sha256", "child_sha256", "selected_policy_sha256"):
            _digest(document[field])
    _check_hash(READBACK_DOMAIN, document, "evidence_sha256")
    return document


def parse_meter_policy_readback_evidence(data: bytes) -> dict[str, Any]:
    return _validate_readback(_strict_document(data, limit=MAX_REQUEST_BYTES))


def serialize_meter_policy_readback_evidence(evidence: Mapping[str, Any]) -> bytes:
    return canonical_json_bytes(_validate_readback(_document(evidence, limit=MAX_REQUEST_BYTES)))


def _identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def _safe_stat(path: Path, *, directory: bool | None = None, missing_ok: bool = False) -> os.stat_result | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        if missing_ok:
            return None
        raise MeterPolicyStoreError("PATH_MISSING") from None
    except OSError:
        raise MeterPolicyStoreError("PATH_READ_FAILED") from None
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        _fail("REPARSE_PATH")
    if directory is True and not stat.S_ISDIR(info.st_mode):
        _fail("DIRECTORY_INVALID")
    if directory is False and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
        _fail("FILE_INVALID")
    return info


def _root_pins(root: Path) -> tuple[tuple[Path, tuple[int, int]], ...]:
    if not root.is_absolute() or ".." in root.parts:
        _fail("ROOT_INVALID")
    pins = []
    for ancestor in (root, *root.parents):
        info = _safe_stat(ancestor, directory=True)
        assert info is not None
        # os.path also supports Windows on Python 3.11, where Path.is_mount
        # raises NotImplementedError. Never skip the mount-placement check.
        if os.path.ismount(ancestor) and (root == ancestor or root.parent == ancestor):
            _fail("DRIVE_ROOT_PLACEMENT")
        pins.append((ancestor, _identity(info)))
    if root == Path(root.anchor) or root.parent == Path(root.anchor):
        _fail("DRIVE_ROOT_PLACEMENT")
    if root.resolve(strict=True) != root:
        _fail("ROOT_ALIAS")
    return tuple(pins)


def _case_exact(parent: Path, name: str) -> None:
    """Inspect only the exact target component, never discover media recursively."""
    try:
        with os.scandir(parent) as entries:
            for count, entry in enumerate(entries, 1):
                if count > 4096:
                    _fail("DIRECTORY_LIMIT")
                if entry.name.casefold() == name.casefold() and entry.name != name:
                    _fail("CASE_ALIAS")
    except OSError:
        raise MeterPolicyStoreError("PATH_READ_FAILED") from None


def _guard_path(root: Path, relative_path: str) -> os.stat_result | None:
    parts = relative_path.split("/")
    if not parts or any(part in {"", ".", ".."} or "\\" in part or ":" in part for part in parts):
        _fail("PATH_INVALID")
    cursor = root
    for index, part in enumerate(parts):
        _case_exact(cursor, part)
        cursor = cursor / part
        info = _safe_stat(cursor, directory=True if index < len(parts) - 1 else False, missing_ok=True)
        if info is None:
            return None
        if not cursor.resolve(strict=True).is_relative_to(root):
            _fail("PATH_ESCAPE")
    return info


def _read_file(path: Path, *, limit: int) -> tuple[bytes, tuple[int, int]]:
    before = _safe_stat(path, directory=False)
    assert before is not None
    if not 0 < before.st_size <= limit:
        _fail("BYTE_LIMIT")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as handle:
            opened = os.fstat(handle.fileno())
            if _identity(opened) != _identity(before) or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                _fail("PATH_IDENTITY_CHANGED")
            data = handle.read(limit + 1)
            after_handle = os.fstat(handle.fileno())
        after = _safe_stat(path, directory=False)
    except OSError:
        raise MeterPolicyStoreError("READBACK_FAILED") from None
    if after is None or (
        _identity(after) != _identity(before)
        or _identity(after_handle) != _identity(before)
        or before.st_size != after_handle.st_size
        or before.st_mtime_ns != after_handle.st_mtime_ns
        or after.st_mtime_ns != after_handle.st_mtime_ns
        or len(data) != before.st_size
    ):
        _fail("READ_CHANGED")
    if not 0 < len(data) <= limit:
        _fail("BYTE_LIMIT")
    return data, _identity(before)


@dataclass(frozen=True, slots=True)
class _View:
    manifest: ProductProjectManifest
    manifest_identity: tuple[int, int]
    journal_identity: tuple[str, tuple[int, int]] | None
    child_bytes: bytes | None
    child_identity: tuple[int, int] | None
    state: dict[str, Any] | None

    @property
    def child_sha256(self) -> str | None:
        return None if self.child_bytes is None else sha256_bytes(self.child_bytes)

    def consistency_key(self) -> tuple[Any, ...]:
        return (
            self.manifest.project_manifest_sha256,
            self.manifest.project_revision,
            self.manifest_identity,
            self.journal_identity,
            self.child_sha256,
            self.child_identity,
        )


class MeterPolicyReadStatus(str, Enum):
    PROJECT_HEAD_MATCHED_SNAPSHOT = "PROJECT_HEAD_MATCHED_SNAPSHOT"
    NOT_BOUND = "NOT_BOUND"
    REVOKED = "REVOKED"
    STALE = "STALE"
    MISMATCH = "MISMATCH"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    ROLLBACK_UNCERTAIN = "ROLLBACK_UNCERTAIN"
    INVALID = "INVALID"
    READBACK_FAILED = "READBACK_FAILED"


class MeterPolicySnapshot:
    """Immutable, nonserializable read result; only its issuing store admits it."""

    __slots__ = (
        "project_id", "project_revision", "project_manifest_sha256", "child_sha256",
        "state_revision", "selected_policy_sha256", "producer_epoch", "context",
        "policy", "_token", "__weakref__",
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("meter policy snapshots cannot be subclassed")

    def __init__(self, *, view: _View, context: MeterPolicyQueryContext, producer_epoch: str, token: object, constructor: object) -> None:
        if constructor is not _SNAPSHOT_CONSTRUCTOR or view.state is None:
            _fail("SNAPSHOT_FACTORY_REQUIRED")
        state = view.state
        selected = state["selected_policy_sha256"]
        policy_documents = [
            event["request"]["payload"]["policy_document"]
            for event in state["events"] if event["request"]["action"] == "PUBLISH_POLICY"
        ]
        policy = next((_policy(document) for document in policy_documents if document["policy_revision_sha256"] == selected), None)
        if policy is None or selected in state["revoked_policy_sha256s"]:
            _fail("SELECTION_INVALID")
        values = {
            "project_id": view.manifest.project_id,
            "project_revision": view.manifest.project_revision,
            "project_manifest_sha256": view.manifest.project_manifest_sha256,
            "child_sha256": view.child_sha256,
            "state_revision": state["state_revision"],
            "selected_policy_sha256": selected,
            "producer_epoch": producer_epoch,
            "context": context,
            "policy": policy,
            "_token": token,
        }
        for key, value in values.items():
            object.__setattr__(self, key, value)

    def __setattr__(self, name: str, value: Any) -> None:
        raise TypeError("meter policy snapshots are immutable")

    def __copy__(self) -> Any:
        raise TypeError("meter policy snapshots cannot be copied")

    def __deepcopy__(self, memo: dict[int, Any]) -> Any:
        raise TypeError("meter policy snapshots cannot be copied")

    def __reduce__(self) -> Any:
        raise TypeError("meter policy snapshots cannot be serialized")

    def __reduce_ex__(self, protocol: int) -> Any:
        raise TypeError("meter policy snapshots cannot be serialized")


def _snapshot_signature(snapshot: MeterPolicySnapshot) -> tuple[Any, ...]:
    return (
        snapshot.project_id, snapshot.project_revision, snapshot.project_manifest_sha256,
        snapshot.child_sha256, snapshot.state_revision, snapshot.selected_policy_sha256,
        snapshot.producer_epoch, canonical_json_bytes(_context(snapshot.context)),
        canonical_json_bytes(snapshot.policy.to_dict()),
    )


@dataclass(frozen=True, slots=True)
class MeterPolicyReadResult:
    status: MeterPolicyReadStatus
    snapshot: MeterPolicySnapshot | None
    _evidence_bytes: bytes | None = None

    def to_dict(self) -> dict[str, Any] | None:
        """Return past-read diagnostic evidence, never a serialized live snapshot."""
        if self._evidence_bytes is None:
            return None
        return parse_meter_policy_readback_evidence(self._evidence_bytes)


class MeterPolicyProjectStore:
    """One existing Project, one producer epoch; construction/read never writes."""

    def __init__(
        self,
        project_root: str | Path,
        project_id: str,
        *,
        coordinator: ProductProjectSaveCoordinator | None = None,
    ) -> None:
        self._root = Path(project_root)
        self._pins = _root_pins(self._root)
        self.project_id = _project_id(project_id)
        self._coordinator = coordinator if coordinator is not None else ProductProjectSaveCoordinator()
        self._epoch = str(uuid.uuid4())
        self._token = object()
        self._closed = False
        self._high_water: tuple[int, str, int] | None = None
        self._admitted: weakref.WeakKeyDictionary[MeterPolicySnapshot, tuple[Any, ...]] = weakref.WeakKeyDictionary()
        self._residuals: list[str] = []

    def __copy__(self) -> Any:
        raise TypeError("meter policy stores cannot be copied")

    def __deepcopy__(self, memo: dict[int, Any]) -> Any:
        raise TypeError("meter policy stores cannot be copied")

    def __getstate__(self) -> Any:
        raise TypeError("meter policy stores cannot be serialized")

    def __reduce__(self) -> Any:
        raise TypeError("meter policy stores cannot be serialized")

    def __reduce_ex__(self, protocol: int) -> Any:
        raise TypeError("meter policy stores cannot be serialized")

    @property
    def producer_epoch(self) -> str:
        return self._epoch

    @property
    def residuals(self) -> tuple[str, ...]:
        """Body-free reasons for intentionally retained operation directories."""
        return tuple(self._residuals)

    def _require_open(self) -> None:
        if self._closed:
            _fail("STORE_CLOSED")
        for path, expected in self._pins:
            info = _safe_stat(path, directory=True)
            if info is None or _identity(info) != expected:
                _fail("ROOT_IDENTITY_CHANGED")

    def _manifest(self) -> tuple[ProductProjectManifest, tuple[int, int]]:
        _guard_path(self._root, ".bai-project/project.json")
        path = ProductProjectManifestStore.path(self._root)
        data, identity = _read_file(path, limit=4 * 1024 * 1024)
        parsed = _strict_document(data, max_depth=64, max_nodes=524288, max_string=4 * 1024 * 1024)
        try:
            manifest = ProductProjectManifestStore.load(self._root)
        except (ProductError, OSError, ValueError, TypeError):
            raise MeterPolicyStoreError("PROJECT_INVALID") from None
        after = _safe_stat(path, directory=False)
        if after is None or _identity(after) != identity or canonical_json_bytes(parsed) != canonical_json_bytes(manifest.to_dict()):
            _fail("READ_CHANGED")
        if manifest.project_id != self.project_id:
            _fail("PROJECT_MISMATCH")
        _positive(manifest.project_revision)
        return manifest, identity

    def _journal(self) -> tuple[str, tuple[int, int]] | None:
        info = _guard_path(self._root, ".bai-project/save-journal.json")
        if info is None:
            return None
        path = ProjectSaveJournalStore.path(self._root)
        data, identity = _read_file(path, limit=8 * 1024 * 1024)
        parsed = _strict_document(data, limit=8 * 1024 * 1024, max_depth=64, max_nodes=524288, max_string=8 * 1024 * 1024)
        try:
            journal = ProjectSaveJournalStore.load(self._root)
        except (ProductError, OSError, ValueError, TypeError):
            raise MeterPolicyStoreError("JOURNAL_INVALID") from None
        after = _safe_stat(path, directory=False)
        if after is None or _identity(after) != identity or canonical_json_bytes(parsed) != canonical_json_bytes(journal.to_dict()):
            _fail("READ_CHANGED")
        if journal.state.value not in _TERMINAL:
            _fail("RECOVERY_REQUIRED")
        return sha256_bytes(data), identity

    def _read_once(self) -> _View:
        self._require_open()
        manifest, manifest_identity = self._manifest()
        journal_identity = self._journal()
        binding = _binding(manifest, absent_ok=True)
        for child in manifest.child_bindings:
            _guard_path(self._root, child.relative_path)
        try:
            self._coordinator.require_current_integrity(self._root, manifest)
        except ProductError as exc:
            if exc.code == "ERR_PROJECT_SAVE_RECOVERY_REQUIRED":
                raise MeterPolicyStoreError("RECOVERY_REQUIRED") from None
            if exc.code == "ERR_PROJECT_SAVE_REVISION_CONFLICT":
                raise MeterPolicyStoreError("READ_CHANGED") from None
            raise MeterPolicyStoreError("PROJECT_INTEGRITY") from None
        except (OSError, ValueError, TypeError):
            raise MeterPolicyStoreError("READBACK_FAILED") from None
        child_info = _guard_path(self._root, CHILD_PATH)
        if binding is None:
            if child_info is not None:
                _fail("FOREIGN_CHILD")
            return _View(manifest, manifest_identity, journal_identity, None, None, None)
        data, identity = _read_file(self._root / CHILD_PATH, limit=MAX_CHILD_BYTES)
        state = parse_meter_policy_state(data, enclosing_manifest=manifest)
        return _View(manifest, manifest_identity, journal_identity, data, identity, state)

    def _collect(self) -> _View:
        first = self._read_once()
        second = self._read_once()
        if first.consistency_key() != second.consistency_key() or first.child_bytes != second.child_bytes:
            _fail("READ_CHANGED")
        domain_revision = 0 if second.state is None else second.state["state_revision"]
        if self._high_water is not None:
            prior_revision, prior_hash, prior_domain = self._high_water
            if (
                second.manifest.project_revision < prior_revision
                or domain_revision < prior_domain
                or (second.manifest.project_revision == prior_revision and second.manifest.project_manifest_sha256 != prior_hash)
            ):
                _fail("ROLLBACK_UNCERTAIN")
        self._high_water = (second.manifest.project_revision, second.manifest.project_manifest_sha256, domain_revision)
        return second

    @staticmethod
    def _event(view: _View, operation_id: str) -> dict[str, Any] | None:
        if view.state is None:
            return None
        return next((event for event in view.state["events"] if event["request"]["operation_id"] == operation_id), None)

    @staticmethod
    def _matching_event(view: _View, request: dict[str, Any]) -> dict[str, Any] | None:
        event = MeterPolicyProjectStore._event(view, request["operation_id"])
        if event is not None and (
            event["request"]["request_sha256"] != request["request_sha256"]
            or canonical_json_bytes(event["request"]) != canonical_json_bytes(request)
        ):
            _fail("IDEMPOTENCY_CONFLICT")
        return event

    @staticmethod
    def _receipt(view: _View, event: dict[str, Any], observation: str) -> dict[str, Any]:
        document = {
            "record_type": "Task048MeterPolicyOperationReceiptV1",
            "schema_version": 1,
            "project_id": view.manifest.project_id,
            "operation_id": event["request"]["operation_id"],
            "request_sha256": event["request"]["request_sha256"],
            "event_sha256": event["event_sha256"],
            "committed_state_revision": event["sequence"],
            "committed_project_revision": event["request"]["expected_project_revision"] + 1,
            "observation": observation,
            "observed_project_revision": view.manifest.project_revision,
            "observed_project_manifest_sha256": view.manifest.project_manifest_sha256,
            "observed_child_sha256": view.child_sha256,
            "authority_created": False,
            "current_selection_proven": False,
            "io_boundary": dict(_IO_BOUNDARY),
        }
        document["receipt_sha256"] = _record_hash(RECEIPT_DOMAIN, document, "receipt_sha256")
        return parse_meter_policy_operation_receipt(serialize_meter_policy_operation_receipt(document))

    def read_operation_receipt(self, operation_id: str, expected_request: Mapping[str, Any] | bytes) -> dict[str, Any]:
        request = _validate_request(_document(expected_request, limit=MAX_REQUEST_BYTES))
        if _uuid(operation_id) != request["operation_id"] or request["project_id"] != self.project_id:
            _fail("IDEMPOTENCY_CONFLICT")
        view = self._collect()
        event = self._matching_event(view, request)
        if event is None:
            _fail("NOT_APPLIED_AT_READ_POINT")
        return self._receipt(view, event, "ALREADY_APPLIED")

    @staticmethod
    def _next_state(view: _View, request: dict[str, Any]) -> dict[str, Any]:
        old = view.state
        if old is None:
            if request["action"] != "BOOTSTRAP":
                _fail("BOOTSTRAP_REQUIRED")
            state = {
                "authority": dict(_AUTHORITY),
                "canonical_owner_task": "TASK-048",
                "events": [],
                **_state_fields(view.manifest.project_id, request["payload"]["policy_ref"], 0, [], None, set()),
            }
        else:
            state = deepcopy(old)
        if len(state["events"]) >= MAX_EVENTS:
            _fail("CAPACITY_EXHAUSTED")
        event = {
            "record_type": "Task048MeterPolicyOperationEventV1",
            "schema_version": 1,
            "sequence": len(state["events"]) + 1,
            "previous_event_sha256": state["events"][-1]["event_sha256"] if state["events"] else None,
            "request": request,
        }
        event["event_sha256"] = _record_hash(EVENT_DOMAIN, event, "event_sha256")
        state["events"].append(event)
        state["state_revision"] = len(state["events"])
        action = request["action"]
        if action == "PUBLISH_POLICY":
            state["published_policy_revision"] += 1
            state["published_policy_sha256"] = request["payload"]["policy_document"]["policy_revision_sha256"]
        elif action == "SELECT_POLICY":
            state["selected_policy_sha256"] = request["payload"]["policy_revision_sha256"]
        elif action == "REVOKE_POLICY":
            state["revoked_policy_sha256s"] = sorted(set(state["revoked_policy_sha256s"]) | {request["payload"]["policy_revision_sha256"]})
        state["state_sha256"] = _record_hash(STATE_DOMAIN, state, "state_sha256")
        state = _document(state)
        _validate("state", state)
        _replay(state)
        return state

    @staticmethod
    def _next_manifest(view: _View, state: dict[str, Any]) -> ProductProjectManifest:
        existing = _binding(view.manifest, absent_ok=True)
        binding = ProjectChildBinding("TASK-048", CHILD_PATH, CHILD_FORMAT, CHILD_VERSION, sha256_bytes(canonical_json_bytes(state)), True)
        bindings = [item for item in view.manifest.child_bindings if item is not existing] + [binding]
        now = utc_now_iso()
        try:
            if type(now) is not str or not now.endswith("Z"):
                _fail("CLOCK_METADATA")
            current_instant = datetime.fromisoformat(view.manifest.updated_at[:-1] + "+00:00")
            now_instant = datetime.fromisoformat(now[:-1] + "+00:00")
            if now_instant.utcoffset() != timezone.utc.utcoffset(None):
                _fail("CLOCK_METADATA")
            updated = view.manifest.updated_at if current_instant >= now_instant else now
            return ProductProjectManifest.create(
                project_id=view.manifest.project_id,
                project_revision=view.manifest.project_revision + 1,
                product_version=view.manifest.product_version,
                timebase=view.manifest.timebase,
                child_bindings=bindings,
                created_at=view.manifest.created_at,
                updated_at=updated,
            )
        except (ValueError, TypeError, OverflowError):
            raise MeterPolicyStoreError("CLOCK_METADATA") from None

    def _cleanup_parent(self, created: tuple[int, int], source: _View) -> None:
        """Called only while the public coordinator still holds its Project lock."""
        directory = self._root / "voice-quality"
        try:
            self._require_open()
            current, _ = self._manifest()
            self._journal()  # Pending, malformed, or unreadable is uncertainty.
            if current.project_manifest_sha256 != source.manifest.project_manifest_sha256:
                _fail("CLEANUP_COMMIT_UNCERTAIN")
            _case_exact(self._root, "voice-quality")
            info = _safe_stat(directory, directory=True)
            if info is None or _identity(info) != created:
                _fail("CLEANUP_IDENTITY_CHANGED")
            with os.scandir(directory) as children:
                if next(children, None) is not None:
                    _fail("CLEANUP_NONEMPTY")
            info = _safe_stat(directory, directory=True)
            if info is None or _identity(info) != created:
                _fail("CLEANUP_IDENTITY_CHANGED")
            directory.rmdir()  # Atomic empty-only removal; no recursive cleanup.
        except (MeterPolicyStoreError, OSError):
            self._residuals.append("VOICE_QUALITY_DIRECTORY_RETAINED_UNCERTAIN")

    def apply(self, request: Mapping[str, Any] | bytes) -> dict[str, Any]:
        request_document = _validate_request(_document(request, limit=MAX_REQUEST_BYTES))
        if request_document["project_id"] != self.project_id:
            _fail("PROJECT_MISMATCH")
        source = self._collect()
        duplicate = self._matching_event(source, request_document)
        if duplicate is not None:
            return self._receipt(source, duplicate, "ALREADY_APPLIED")
        if (
            source.manifest.project_revision != request_document["expected_project_revision"]
            or source.manifest.project_manifest_sha256 != request_document["expected_project_manifest_sha256"]
            or source.child_sha256 != request_document["expected_child_sha256"]
        ):
            _fail("CAS_CONFLICT")
        state = self._next_state(source, request_document)
        target = self._next_manifest(source, state)
        child_bytes = serialize_meter_policy_state(state, enclosing_manifest=target)
        precommit_conflict: MeterPolicyStoreError | None = None

        @contextmanager
        def commit_guard() -> Iterator[None]:
            nonlocal precommit_conflict
            self._require_open()
            current = self._collect()
            if current.consistency_key() != source.consistency_key() or current.child_bytes != source.child_bytes:
                precommit_conflict = MeterPolicyStoreError("CAS_CONFLICT")
                raise precommit_conflict
            directory = self._root / "voice-quality"
            _case_exact(self._root, "voice-quality")
            parent_info = _safe_stat(directory, directory=True, missing_ok=True)
            created = None
            if parent_info is None:
                if source.state is not None or request_document["action"] != "BOOTSTRAP":
                    _fail("DIRECTORY_MISSING")
                try:
                    directory.mkdir()  # One known level, inside Project lock.
                    created_info = _safe_stat(directory, directory=True)
                    assert created_info is not None
                    created = _identity(created_info)
                except BaseException:
                    # A successful mkdir followed by unreadable/replaced metadata
                    # has no trustworthy ownership identity for cleanup. Preserve
                    # it and disclose uncertainty even if mkdir's reply was lost.
                    self._residuals.append("VOICE_QUALITY_DIRECTORY_CREATION_UNCERTAIN")
                    raise
            try:
                yield
            except BaseException:
                if created is not None:
                    self._cleanup_parent(created, source)
                raise

        try:
            self._coordinator.save(
                self._root,
                target,
                {CHILD_PATH: child_bytes},
                expected_previous_manifest_sha256=source.manifest.project_manifest_sha256,
                commit_guard=commit_guard,
            )
        except Exception as exc:
            # Only the exact conflict issued before this guard yielded proves
            # that this request did not enter the write phase. A similarly
            # named exception from the coordinator may follow a real commit.
            if exc is precommit_conflict:
                raise
            raise MeterPolicyStoreError("COMMIT_NOT_CONFIRMED", operation_id=request_document["operation_id"]) from None
        try:
            observed = self._collect()
            event = self._matching_event(observed, request_document)
            if event is None:
                _fail("COMMIT_NOT_CONFIRMED")
            return self._receipt(observed, event, "APPLIED")
        except Exception:
            raise MeterPolicyStoreError("COMMIT_NOT_CONFIRMED", operation_id=request_document["operation_id"]) from None

    def _result(
        self,
        status: MeterPolicyReadStatus,
        context: MeterPolicyQueryContext | None,
        view: _View | None = None,
    ) -> MeterPolicyReadResult:
        snapshot = None
        if status is MeterPolicyReadStatus.PROJECT_HEAD_MATCHED_SNAPSHOT:
            assert context is not None and view is not None
            snapshot = MeterPolicySnapshot(view=view, context=context, producer_epoch=self._epoch, token=self._token, constructor=_SNAPSHOT_CONSTRUCTOR)
            self._admitted[snapshot] = _snapshot_signature(snapshot)
        if context is None:
            return MeterPolicyReadResult(status, snapshot)
        evidence: dict[str, Any] = {
            "record_type": "Task048MeterPolicyReadbackEvidenceV1",
            "schema_version": 1,
            "project_id": context.project_id,
            "status": status.value,
            "project_revision": None if snapshot is None else snapshot.project_revision,
            "project_manifest_sha256": None if snapshot is None else snapshot.project_manifest_sha256,
            "child_sha256": None if snapshot is None else snapshot.child_sha256,
            "state_revision": None if snapshot is None else snapshot.state_revision,
            "selected_policy_sha256": None if snapshot is None else snapshot.selected_policy_sha256,
            "query_context": context.to_dict(),
            "producer_epoch": self._epoch,
            "live_admission_serialized": False,
            "authority_created": False,
            "temporal_freshness_confirmed": False,
            "io_boundary": dict(_IO_BOUNDARY),
        }
        evidence["evidence_sha256"] = _record_hash(READBACK_DOMAIN, evidence, "evidence_sha256")
        return MeterPolicyReadResult(status, snapshot, serialize_meter_policy_readback_evidence(evidence))

    @staticmethod
    def _error_status(exc: MeterPolicyStoreError) -> MeterPolicyReadStatus:
        if exc.reason == "RECOVERY_REQUIRED":
            return MeterPolicyReadStatus.RECOVERY_REQUIRED
        if exc.reason == "ROLLBACK_UNCERTAIN":
            return MeterPolicyReadStatus.ROLLBACK_UNCERTAIN
        if exc.reason in {"READ_CHANGED", "CAS_CONFLICT"}:
            return MeterPolicyReadStatus.STALE
        if exc.reason in {"READBACK_FAILED", "PATH_READ_FAILED", "PATH_MISSING"}:
            return MeterPolicyReadStatus.READBACK_FAILED
        if exc.reason in {"STORE_CLOSED", "PROJECT_MISMATCH", "CONTEXT_MISMATCH", "ROOT_IDENTITY_CHANGED"}:
            return MeterPolicyReadStatus.MISMATCH
        return MeterPolicyReadStatus.INVALID

    def read_snapshot(self, context: MeterPolicyQueryContext) -> MeterPolicyReadResult:
        try:
            context_document = _context(context)
        except (ProductError, TypeError, AttributeError):
            return self._result(MeterPolicyReadStatus.MISMATCH, None)
        if context_document["project_id"] != self.project_id:
            return self._result(MeterPolicyReadStatus.MISMATCH, context)
        try:
            view = self._collect()
            if view.state is None or view.state["selected_policy_sha256"] is None:
                return self._result(MeterPolicyReadStatus.NOT_BOUND, context)
            if view.state["selected_policy_sha256"] in view.state["revoked_policy_sha256s"]:
                return self._result(MeterPolicyReadStatus.REVOKED, context)
            return self._result(MeterPolicyReadStatus.PROJECT_HEAD_MATCHED_SNAPSHOT, context, view)
        except MeterPolicyStoreError as exc:
            return self._result(self._error_status(exc), context)
        except (OSError, ValueError, TypeError):
            return self._result(MeterPolicyReadStatus.READBACK_FAILED, context)

    def revalidate(self, snapshot: MeterPolicySnapshot, expected_context: MeterPolicyQueryContext) -> MeterPolicyReadResult:
        try:
            expected_document = _context(expected_context)
        except (ProductError, TypeError, AttributeError):
            return self._result(MeterPolicyReadStatus.MISMATCH, None)
        try:
            if (
                type(snapshot) is not MeterPolicySnapshot
                or self._closed
                or snapshot._token is not self._token
                or snapshot.producer_epoch != self._epoch
                or self._admitted.get(snapshot) != _snapshot_signature(snapshot)
                or canonical_json_bytes(expected_document) != canonical_json_bytes(_context(snapshot.context))
            ):
                return self._result(MeterPolicyReadStatus.MISMATCH, expected_context)
        except (ProductError, AttributeError, TypeError, ValueError):
            return self._result(MeterPolicyReadStatus.MISMATCH, expected_context)
        try:
            view = self._collect()
            if view.state is not None and snapshot.selected_policy_sha256 in view.state["revoked_policy_sha256s"]:
                return self._result(MeterPolicyReadStatus.REVOKED, expected_context)
            if (
                view.state is None
                or view.manifest.project_revision != snapshot.project_revision
                or view.manifest.project_manifest_sha256 != snapshot.project_manifest_sha256
                or view.child_sha256 != snapshot.child_sha256
                or view.state["state_revision"] != snapshot.state_revision
                or view.state["selected_policy_sha256"] != snapshot.selected_policy_sha256
            ):
                return self._result(MeterPolicyReadStatus.STALE, expected_context)
            return self._result(MeterPolicyReadStatus.PROJECT_HEAD_MATCHED_SNAPSHOT, expected_context, view)
        except MeterPolicyStoreError as exc:
            return self._result(self._error_status(exc), expected_context)
        except (OSError, ValueError, TypeError):
            return self._result(MeterPolicyReadStatus.READBACK_FAILED, expected_context)

    def close(self) -> None:
        self._closed = True
        self._admitted.clear()
