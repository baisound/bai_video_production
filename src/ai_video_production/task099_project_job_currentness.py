"""TASK-099 pure Project/Job currentness V2 contracts.

The module validates body-free records and drives an injected fake/trusted port.
It contains no filesystem, clock, process, network, or native implementation.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
import re
from types import MappingProxyType
from typing import Any, Mapping, Protocol

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


MAX_RECORD_BYTES = 131_072
MAX_LARGE_RECORD_BYTES = 4_194_304
MAX_PHASE_ENVELOPE_BYTES = 4_718_592
MAX_JSON_DEPTH = 16
MAX_HEADS = 4_096

INDEX_VERSION = "PROJECT_JOB_CURRENTNESS_INDEX_V2"
READBACK_VERSION = "PROJECT_JOB_CURRENTNESS_READBACK_V2"
CANDIDATE_VERSION = "PROJECT_JOB_HEAD_CANDIDATE_V2"
REQUEST_VERSION = "PROJECT_JOB_CURRENTNESS_TRANSACTION_REQUEST_V2"
PROPOSAL_VERSION = "PROJECT_MANIFEST_SUCCESSOR_PROPOSAL_V2"
RESULT_VERSION = "PROJECT_JOB_CURRENTNESS_TRANSACTION_RESULT_V2"
SNAPSHOT_VERSION = "PROJECT_JOB_CURRENTNESS_SNAPSHOT_V2"

_DOMAINS = {
    "index": b"BAI:TASK-099:PROJECT-JOB-CURRENTNESS-INDEX:V2\0",
    "readback": b"BAI:TASK-099:PROJECT-JOB-CURRENTNESS-READBACK:V2\0",
    "candidate": b"BAI:TASK-099:PROJECT-JOB-HEAD-CANDIDATE:V2\0",
    "request": b"BAI:TASK-099:PROJECT-JOB-CURRENTNESS-TRANSACTION-REQUEST:V2\0",
    "proposal": b"BAI:TASK-099:PROJECT-MANIFEST-SUCCESSOR-PROPOSAL:V2\0",
    "result": b"BAI:TASK-099:PROJECT-JOB-CURRENTNESS-TRANSACTION-RESULT:V2\0",
    "snapshot": b"BAI:TASK-099:PROJECT-JOB-CURRENTNESS-SNAPSHOT:V2\0",
    "phase": b"BAI:TASK-099:PROJECT-JOB-CURRENTNESS-PHASE-RESULT:V2\0",
    "event": b"BAI:TASK-099:TASK076-EVENT-COORDINATE:V2\0",
    "state": b"BAI:TASK-099:PROJECT-CURRENTNESS-STATE-COORDINATE:V2\0",
    "observation": b"BAI:TASK-099:PROJECT-CURRENTNESS-OBSERVATION:V2\0",
}
_FACTORY_KEY = object()
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_TIMESTAMP_RE = re.compile(
    r"^(?:(?:(?!0000)[0-9]{4})-(?:(?:0[13578]|1[02])-(?:0[1-9]|[12][0-9]|3[01])|"
    r"(?:0[469]|11)-(?:0[1-9]|[12][0-9]|30)|02-(?:0[1-9]|1[0-9]|2[0-8]))|"
    r"(?:(?!0000)(?:[0-9]{2}(?:0[48]|[2468][048]|[13579][26])|(?:0[48]|[2468][048]|[13579][26])00))-02-29)"
    r"T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]{1,6})?Z$"
)

EVENT_KINDS = frozenset({
    "RESERVED", "PREPARED", "READY", "DISPATCHING", "IN_FLIGHT",
    "SUCCEEDED", "FAILED_KNOWN", "BURNED_UNKNOWN", "CANCELLED_SAFE", "HUMAN_REQUIRED",
})
REASON_CODES = frozenset({
    "MALFORMED_INPUT", "EXPIRED_CURRENTNESS", "FIXTURE_ONLY_EVIDENCE",
    "PRODUCER_NOT_AUTHENTICATED", "PROJECT_BINDING_MISMATCH", "SEMANTIC_KEY_MISMATCH",
    "NAMESPACE_MISMATCH", "OPERATION_MISMATCH", "BUILD_SECURITY_MISMATCH",
    "CANDIDATE_PREDECESSOR_MISMATCH", "STALE_PRIOR_READBACK", "CURRENTNESS_EPOCH_CHANGED",
    "PHYSICAL_IDENTITY_CHANGED", "SECURITY_IDENTITY_DRIFT", "INDEX_PROPOSAL_MISMATCH",
    "MANIFEST_PROPOSAL_MISMATCH", "CONCURRENT_SUCCESSOR", "INDEX_PUBLISH_UNKNOWN",
    "MANIFEST_COMMIT_UNKNOWN", "SUCCESSOR_READBACK_FAILED", "SAME_OPERATION_HISTORY_UNKNOWN",
    "SAME_OPERATION_COMMIT_SUPERSEDED", "BACKEND_BLOCKED", "LEASE_RELEASE_WARNING",
})


class EvidenceSource(str, Enum):
    TRUSTED = "TRUSTED_BACKEND"
    FIXTURE = "FIXTURE_ONLY"


class TransactionState(str, Enum):
    COMMITTED = "COMMITTED_WITH_READBACK"
    CONFLICT = "CONFLICT_NO_WRITE"
    BLOCKED = "BLOCKED_NO_WRITE"
    UNKNOWN = "COMMIT_OUTCOME_UNKNOWN"


def _exact(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields are not exact")


def _bounded(value: Mapping[str, Any], name: str, *, large: bool = False) -> None:
    limit = MAX_LARGE_RECORD_BYTES if large else MAX_RECORD_BYTES
    try:
        encoded = canonical_json_bytes(value)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError(f"{name} is not canonical JSON") from exc
    if not encoded or len(encoded) > limit:
        raise ValueError(f"{name} is outside its byte bound")
    pending: list[tuple[Any, int]] = [(value, 0)]
    while pending:
        current, depth = pending.pop()
        if depth > MAX_JSON_DEPTH: raise ValueError(f"{name} exceeds depth bound")
        if isinstance(current, Mapping): pending.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, (list, tuple)): pending.extend((item, depth + 1) for item in current)
        elif isinstance(current, str) and len(current.encode("utf-8")) > 512: raise ValueError(f"{name} contains oversized text")


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be SHA-256")
    return validate_sha256(value, field_name=name)


def _id(value: Any, name: str, *, reference: bool = False) -> str:
    pattern = _REF_RE if reference else _ID_RE
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"{name} is not a valid opaque identifier")
    lowered = value.casefold()
    if "/" in value or "\\" in value or "://" in lowered or re.match(r"^[a-z][a-z0-9+.-]*:", lowered):
        raise ValueError(f"{name} must not be a path or URI")
    return value


def _positive(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 2_147_483_647:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _time(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not _TIMESTAMP_RE.fullmatch(value):
        raise ValueError(f"{name} must be a calendar-valid UTC timestamp")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be a calendar-valid UTC timestamp") from exc


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _digest(body: Mapping[str, Any], field: str, domain: bytes) -> str:
    value = copy.deepcopy(dict(body))
    value.pop(field, None)
    return sha256_bytes(domain + canonical_json_bytes(value))


def _verify_digest(body: Mapping[str, Any], field: str, domain: bytes) -> None:
    _sha(body.get(field), field)
    if body[field] != _digest(body, field, domain):
        raise ValueError(f"{field} does not match canonical content")


@dataclass(frozen=True, slots=True, init=False)
class ContractRecord:
    kind: str
    data: Mapping[str, Any]

    def __init__(self, kind: str, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _FACTORY_KEY:
            raise TypeError("ContractRecord must be created by a validated parser")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "data", data)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.data)


_EVENT_FIELDS = {"task076_namespace", "task076_event_contract_version", "operation_id", "event_sequence", "coordinate_sha256"}


def validate_event_coordinate(value: Mapping[str, Any]) -> dict[str, Any]:
    _bounded(value, "event_coordinate"); body = copy.deepcopy(dict(value)); _exact(body, _EVENT_FIELDS, "event_coordinate")
    _id(body["task076_namespace"], "task076_namespace")
    if body["task076_event_contract_version"] != "DURABLE_PRODUCT_JOB_EVENT_V2":
        raise ValueError("TASK-076 event contract version is unsupported")
    _id(body["operation_id"], "operation_id"); _positive(body["event_sequence"], "event_sequence")
    _verify_digest(body, "coordinate_sha256", _DOMAINS["event"])
    return body


_CANDIDATE_FIELDS = {
    "candidate_contract_version", "record_type", "project_id", "job_semantic_key_sha256",
    "namespace_plan_set_sha256", "task076_profile_id", "task076_profile_version",
    "task076_event_contract_version", "event_coordinate", "event_sha256",
    "event_physical_identity_ref", "predecessor_event_coordinate", "predecessor_event_sha256",
    "predecessor_event_physical_identity_ref", "event_kind", "event_sequence",
    "task076_candidate_readback_sha256", "task068_plan_sha256", "task068_publish_receipt_sha256",
    "task068_pinned_readback_sha256", "consumer_operation_id", "install_build_binding_sha256",
    "security_reader_binding_sha256", "producer_issuer_binding_sha256", "evidence_source",
    "observed_at", "expires_at", "candidate_sha256",
}


def parse_candidate(value: Mapping[str, Any]) -> ContractRecord:
    _bounded(value, "ProjectJobHeadCandidateV2"); body = copy.deepcopy(dict(value)); _exact(body, _CANDIDATE_FIELDS, "ProjectJobHeadCandidateV2")
    if body["candidate_contract_version"] != CANDIDATE_VERSION or body["record_type"] != "ProjectJobHeadCandidateV2":
        raise ValueError("candidate discriminator mismatch")
    for field in ("project_id", "consumer_operation_id"):
        _id(body[field], field)
    for field in ("job_semantic_key_sha256", "namespace_plan_set_sha256", "event_sha256",
                  "task076_candidate_readback_sha256", "task068_plan_sha256", "task068_publish_receipt_sha256",
                  "task068_pinned_readback_sha256", "install_build_binding_sha256",
                  "security_reader_binding_sha256", "producer_issuer_binding_sha256"):
        _sha(body[field], field)
    if (body["task076_profile_id"], body["task076_profile_version"], body["task076_event_contract_version"]) != (
        "DURABLE_PRODUCT_JOB_EVENT_V2", "2.0.0", "DURABLE_PRODUCT_JOB_EVENT_V2"):
        raise ValueError("TASK-076 profile/version is unsupported")
    event = validate_event_coordinate(body["event_coordinate"]); body["event_coordinate"] = event
    sequence = _positive(body["event_sequence"], "event_sequence")
    if sequence != event["event_sequence"] or body["event_kind"] not in EVENT_KINDS:
        raise ValueError("candidate event kind/sequence is invalid")
    predecessor_values = (body["predecessor_event_coordinate"], body["predecessor_event_sha256"], body["predecessor_event_physical_identity_ref"])
    if sequence == 1:
        if body["event_kind"] != "RESERVED" or predecessor_values != (None, None, None):
            raise ValueError("first candidate must be RESERVED without predecessor")
    else:
        if any(item is None for item in predecessor_values):
            raise ValueError("later candidate requires exact predecessor")
        body["predecessor_event_coordinate"] = validate_event_coordinate(body["predecessor_event_coordinate"])
        _sha(body["predecessor_event_sha256"], "predecessor_event_sha256")
        _id(body["predecessor_event_physical_identity_ref"], "predecessor_event_physical_identity_ref", reference=True)
    _id(body["event_physical_identity_ref"], "event_physical_identity_ref", reference=True)
    EvidenceSource(body["evidence_source"])
    if _time(body["observed_at"], "observed_at") >= _time(body["expires_at"], "expires_at"):
        raise ValueError("candidate validity interval is empty")
    _verify_digest(body, "candidate_sha256", _DOMAINS["candidate"])
    return ContractRecord("candidate", _freeze(body), _token=_FACTORY_KEY)


def _validate_head(value: Mapping[str, Any]) -> dict[str, Any]:
    body = copy.deepcopy(dict(value)); variant = body.get("variant")
    common = {"variant", "index_state", "index_revision", "index_sha256", "index_physical_identity_ref"}
    if variant == "ABSENT_JOB_HEAD":
        _exact(body, common | {"absence_proof_sha256"}, "ABSENT_JOB_HEAD")
        if body["index_state"] == "UNINITIALIZED":
            if (body["index_revision"], body["index_sha256"], body["index_physical_identity_ref"]) != (None, None, None):
                raise ValueError("uninitialized index fields must be null")
        elif body["index_state"] == "PRESENT":
            _positive(body["index_revision"], "index_revision"); _sha(body["index_sha256"], "index_sha256")
            _id(body["index_physical_identity_ref"], "index_physical_identity_ref", reference=True)
        else:
            raise ValueError("index_state is unsupported")
        _sha(body["absence_proof_sha256"], "absence_proof_sha256")
    elif variant == "SELECTED_JOB_HEAD":
        fields = common | {"event_coordinate", "event_sha256", "event_physical_identity_ref",
                           "predecessor_event_coordinate", "predecessor_event_sha256",
                           "predecessor_event_physical_identity_ref", "selection_proof_sha256"}
        _exact(body, fields, "SELECTED_JOB_HEAD")
        if body["index_state"] != "PRESENT": raise ValueError("selected head requires present index")
        _positive(body["index_revision"], "index_revision"); _sha(body["index_sha256"], "index_sha256")
        _id(body["index_physical_identity_ref"], "index_physical_identity_ref", reference=True)
        event = validate_event_coordinate(body["event_coordinate"]); body["event_coordinate"] = event
        _sha(body["event_sha256"], "event_sha256"); _id(body["event_physical_identity_ref"], "event_physical_identity_ref", reference=True)
        predecessor = (body["predecessor_event_coordinate"], body["predecessor_event_sha256"], body["predecessor_event_physical_identity_ref"])
        if event["event_sequence"] == 1:
            if predecessor != (None, None, None): raise ValueError("first selected head predecessor must be null")
        else:
            if any(item is None for item in predecessor): raise ValueError("selected head predecessor is incomplete")
            body["predecessor_event_coordinate"] = validate_event_coordinate(body["predecessor_event_coordinate"])
            _sha(body["predecessor_event_sha256"], "predecessor_event_sha256")
            _id(body["predecessor_event_physical_identity_ref"], "predecessor_event_physical_identity_ref", reference=True)
        _sha(body["selection_proof_sha256"], "selection_proof_sha256")
    else:
        raise ValueError("head variant is unsupported")
    return body


_READBACK_FIELDS = {
    "contract_version", "record_type", "project_id", "manifest_revision", "manifest_sha256",
    "predecessor_manifest_sha256", "manifest_physical_identity_ref", "project_root_identity_ref",
    "job_semantic_key_sha256", "head", "namespace_plan_set_sha256", "consumer_operation_id",
    "install_build_binding_sha256", "security_reader_binding_sha256", "producer_issuer_binding_sha256",
    "evidence_source", "currentness_capability", "trusted_currentness_coordinate", "readback_sha256",
}


def parse_readback(value: Mapping[str, Any]) -> ContractRecord:
    _bounded(value, "ProjectJobCurrentnessReadbackV2"); body = copy.deepcopy(dict(value)); _exact(body, _READBACK_FIELDS, "ProjectJobCurrentnessReadbackV2")
    if body["contract_version"] != READBACK_VERSION or body["record_type"] != "ProjectJobCurrentnessReadbackV2":
        raise ValueError("readback discriminator mismatch")
    _id(body["project_id"], "project_id"); revision = _positive(body["manifest_revision"], "manifest_revision")
    _sha(body["manifest_sha256"], "manifest_sha256")
    if revision == 1:
        if body["predecessor_manifest_sha256"] is not None: raise ValueError("revision 1 predecessor must be null")
    else: _sha(body["predecessor_manifest_sha256"], "predecessor_manifest_sha256")
    for field in ("manifest_physical_identity_ref", "project_root_identity_ref"):
        _id(body[field], field, reference=True)
    for field in ("job_semantic_key_sha256", "namespace_plan_set_sha256", "install_build_binding_sha256",
                  "security_reader_binding_sha256", "producer_issuer_binding_sha256"):
        _sha(body[field], field)
    _id(body["consumer_operation_id"], "consumer_operation_id")
    source = EvidenceSource(body["evidence_source"])
    capability = body["currentness_capability"]
    if (source is EvidenceSource.FIXTURE and capability != "FIXTURE_ONLY") or capability not in {"CURRENT", "FIXTURE_ONLY"}:
        raise ValueError("evidence source/currentness capability mismatch")
    body["head"] = _validate_head(body["head"])
    coordinate = copy.deepcopy(dict(body["trusted_currentness_coordinate"])); _exact(coordinate, {"state", "observation"}, "trusted_currentness_coordinate")
    state = copy.deepcopy(dict(coordinate["state"])); _exact(state, {"authority_instance_id", "epoch_id", "manifest_generation_sequence", "state_coordinate_sha256"}, "state")
    _id(state["authority_instance_id"], "authority_instance_id"); _id(state["epoch_id"], "epoch_id"); _positive(state["manifest_generation_sequence"], "manifest_generation_sequence")
    state_preimage = {**{key: state[key] for key in ("authority_instance_id", "epoch_id", "manifest_generation_sequence")},
                      **{key: body[key] for key in ("project_id", "project_root_identity_ref", "manifest_revision", "manifest_sha256", "manifest_physical_identity_ref")}}
    if _sha(state["state_coordinate_sha256"], "state_coordinate_sha256") != sha256_bytes(_DOMAINS["state"] + canonical_json_bytes(state_preimage)):
        raise ValueError("state coordinate digest mismatch")
    observation = copy.deepcopy(dict(coordinate["observation"])); _exact(observation, {"observation_sequence", "observed_at", "expires_at", "clock_binding_sha256", "observation_sha256"}, "observation")
    _positive(observation["observation_sequence"], "observation_sequence"); _sha(observation["clock_binding_sha256"], "clock_binding_sha256")
    if _time(observation["observed_at"], "observed_at") >= _time(observation["expires_at"], "expires_at"): raise ValueError("observation validity interval is empty")
    obs_preimage = {key: observation[key] for key in ("clock_binding_sha256", "expires_at", "observation_sequence", "observed_at")}
    obs_preimage["state_coordinate_sha256"] = state["state_coordinate_sha256"]
    if _sha(observation["observation_sha256"], "observation_sha256") != sha256_bytes(_DOMAINS["observation"] + canonical_json_bytes(obs_preimage)):
        raise ValueError("observation digest mismatch")
    body["trusted_currentness_coordinate"] = {"state": state, "observation": observation}
    _verify_digest(body, "readback_sha256", _DOMAINS["readback"])
    return ContractRecord("readback", _freeze(body), _token=_FACTORY_KEY)


_INDEX_FIELDS = {"contract_version", "record_type", "project_id", "index_revision", "predecessor_index_sha256",
                 "predecessor_manifest_sha256", "namespace_plan_set_sha256", "task076_profile_id",
                 "task076_profile_version", "consumer_operation_id", "install_build_binding_sha256",
                 "security_reader_binding_sha256", "producer_issuer_binding_sha256", "evidence_source", "heads", "index_sha256"}


def parse_index(value: Mapping[str, Any]) -> ContractRecord:
    _bounded(value, "ProjectJobCurrentnessIndexV2", large=True); body = copy.deepcopy(dict(value)); _exact(body, _INDEX_FIELDS, "ProjectJobCurrentnessIndexV2")
    if body["contract_version"] != INDEX_VERSION or body["record_type"] != "ProjectJobCurrentnessIndexV2": raise ValueError("index discriminator mismatch")
    _id(body["project_id"], "project_id"); revision = _positive(body["index_revision"], "index_revision")
    if revision == 1:
        if body["predecessor_index_sha256"] is not None: raise ValueError("first index predecessor must be null")
    else: _sha(body["predecessor_index_sha256"], "predecessor_index_sha256")
    for field in ("predecessor_manifest_sha256", "namespace_plan_set_sha256", "install_build_binding_sha256", "security_reader_binding_sha256", "producer_issuer_binding_sha256"):
        _sha(body[field], field)
    if (body["task076_profile_id"], body["task076_profile_version"]) != ("DURABLE_PRODUCT_JOB_EVENT_V2", "2.0.0"): raise ValueError("index profile unsupported")
    _id(body["consumer_operation_id"], "consumer_operation_id"); EvidenceSource(body["evidence_source"])
    heads = body["heads"]
    if not isinstance(heads, list) or len(heads) > MAX_HEADS: raise ValueError("heads outside bound")
    normalized = []
    for row in heads:
        if not isinstance(row, Mapping): raise ValueError("head row must be object")
        item = copy.deepcopy(dict(row)); _exact(item, {"job_semantic_key_sha256", "task076_profile_id", "task076_profile_version", "event_coordinate", "event_sha256", "event_physical_identity_ref", "predecessor_event_coordinate", "predecessor_event_sha256", "predecessor_event_physical_identity_ref", "event_sequence"}, "index head")
        _sha(item["job_semantic_key_sha256"], "job_semantic_key_sha256")
        if (item["task076_profile_id"], item["task076_profile_version"]) != ("DURABLE_PRODUCT_JOB_EVENT_V2", "2.0.0"): raise ValueError("head profile unsupported")
        event = validate_event_coordinate(item["event_coordinate"]); item["event_coordinate"] = event
        if _positive(item["event_sequence"], "event_sequence") != event["event_sequence"]: raise ValueError("head sequence mismatch")
        _sha(item["event_sha256"], "event_sha256"); _id(item["event_physical_identity_ref"], "event_physical_identity_ref", reference=True)
        if item["event_sequence"] == 1:
            if (item["predecessor_event_coordinate"], item["predecessor_event_sha256"], item["predecessor_event_physical_identity_ref"]) != (None, None, None): raise ValueError("first head predecessor must be null")
        else:
            item["predecessor_event_coordinate"] = validate_event_coordinate(item["predecessor_event_coordinate"])
            _sha(item["predecessor_event_sha256"], "predecessor_event_sha256"); _id(item["predecessor_event_physical_identity_ref"], "predecessor_event_physical_identity_ref", reference=True)
        normalized.append(item)
    keys = [row["job_semantic_key_sha256"] for row in normalized]
    if keys != sorted(keys) or len(keys) != len(set(keys)): raise ValueError("heads must be sorted and unique")
    body["heads"] = normalized; _verify_digest(body, "index_sha256", _DOMAINS["index"])
    return ContractRecord("index", _freeze(body), _token=_FACTORY_KEY)


def compile_successor_index(prior: ContractRecord | None, readback: ContractRecord, candidate: ContractRecord) -> ContractRecord:
    rb = parse_readback(readback.to_dict() if isinstance(readback, ContractRecord) else readback).to_dict()
    cand = parse_candidate(candidate.to_dict() if isinstance(candidate, ContractRecord) else candidate).to_dict()
    prior_body = None if prior is None else parse_index(prior.to_dict() if isinstance(prior, ContractRecord) else prior).to_dict()
    for field in ("project_id", "job_semantic_key_sha256", "namespace_plan_set_sha256", "consumer_operation_id", "install_build_binding_sha256", "security_reader_binding_sha256", "producer_issuer_binding_sha256", "evidence_source"):
        if field in rb and field in cand and rb[field] != cand[field]: raise ValueError(f"{field} binding mismatch")
    head = rb["head"]
    if prior_body is not None:
        for field in ("project_id", "namespace_plan_set_sha256", "consumer_operation_id", "install_build_binding_sha256", "security_reader_binding_sha256", "producer_issuer_binding_sha256", "evidence_source"):
            if prior_body[field] != cand[field] or prior_body[field] != rb[field]:
                raise ValueError(f"prior index {field} binding mismatch")
    if head["variant"] == "ABSENT_JOB_HEAD":
        if cand["event_kind"] != "RESERVED" or cand["event_sequence"] != 1: raise ValueError("absent head accepts first RESERVED only")
        if head["index_state"] == "UNINITIALIZED":
            if prior_body is not None: raise ValueError("uninitialized head cannot have prior index")
            revision, predecessor, heads = 1, None, []
        else:
            if prior_body is None or prior_body["index_sha256"] != head["index_sha256"]: raise ValueError("present absence requires exact index")
            if head["index_revision"] != prior_body["index_revision"] or any(item["job_semantic_key_sha256"] == cand["job_semantic_key_sha256"] for item in prior_body["heads"]):
                raise ValueError("absence proof conflicts with the full prior index")
            revision, predecessor, heads = prior_body["index_revision"] + 1, prior_body["index_sha256"], prior_body["heads"]
    else:
        if prior_body is None or prior_body["index_sha256"] != head["index_sha256"]: raise ValueError("selected head requires exact prior index")
        selected_rows = [item for item in prior_body["heads"] if item["job_semantic_key_sha256"] == cand["job_semantic_key_sha256"]]
        if head["index_revision"] != prior_body["index_revision"] or len(selected_rows) != 1:
            raise ValueError("selected head conflicts with the full prior index")
        selected_row = selected_rows[0]
        for field in ("event_coordinate", "event_sha256", "event_physical_identity_ref", "predecessor_event_coordinate", "predecessor_event_sha256", "predecessor_event_physical_identity_ref"):
            if head[field] != selected_row[field]: raise ValueError("selected head does not match the prior index row")
        if cand["event_sequence"] != head["event_coordinate"]["event_sequence"] + 1 or cand["predecessor_event_sha256"] != head["event_sha256"] or cand["predecessor_event_coordinate"] != head["event_coordinate"] or cand["predecessor_event_physical_identity_ref"] != head["event_physical_identity_ref"]:
            raise ValueError("candidate predecessor does not match selected head")
        revision, predecessor, heads = prior_body["index_revision"] + 1, prior_body["index_sha256"], prior_body["heads"]
    row = {key: cand[key] for key in ("job_semantic_key_sha256", "task076_profile_id", "task076_profile_version", "event_coordinate", "event_sha256", "event_physical_identity_ref", "predecessor_event_coordinate", "predecessor_event_sha256", "predecessor_event_physical_identity_ref", "event_sequence")}
    next_heads = [item for item in heads if item["job_semantic_key_sha256"] != cand["job_semantic_key_sha256"]] + [row]
    next_heads.sort(key=lambda item: item["job_semantic_key_sha256"])
    body = {"contract_version": INDEX_VERSION, "record_type": "ProjectJobCurrentnessIndexV2", "project_id": cand["project_id"], "index_revision": revision, "predecessor_index_sha256": predecessor, "predecessor_manifest_sha256": rb["manifest_sha256"], "namespace_plan_set_sha256": cand["namespace_plan_set_sha256"], "task076_profile_id": cand["task076_profile_id"], "task076_profile_version": cand["task076_profile_version"], "consumer_operation_id": cand["consumer_operation_id"], "install_build_binding_sha256": cand["install_build_binding_sha256"], "security_reader_binding_sha256": cand["security_reader_binding_sha256"], "producer_issuer_binding_sha256": cand["producer_issuer_binding_sha256"], "evidence_source": cand["evidence_source"], "heads": next_heads}
    body["index_sha256"] = _digest(body, "index_sha256", _DOMAINS["index"])
    return parse_index(body)


def parse_security_json(payload: bytes, *, large: bool = False) -> Mapping[str, Any]:
    limit = MAX_LARGE_RECORD_BYTES if large else MAX_RECORD_BYTES
    if not isinstance(payload, bytes) or not payload or len(payload) > limit or payload.startswith(b"\xef\xbb\xbf"):
        raise ValueError("JSON payload is empty, oversized, non-bytes, or contains BOM")
    def pairs(rows: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in rows:
            if key in result: raise ValueError("JSON contains duplicate object keys")
            result[key] = value
        return result
    def constant(value: str) -> None: raise ValueError(f"non-finite number {value} is forbidden")
    try:
        text = payload.decode("utf-8", errors="strict")
        value, end = json.JSONDecoder(object_pairs_hook=pairs, parse_constant=constant,
                                      parse_float=lambda raw: constant(raw)).raw_decode(text)
    except RecursionError as exc: raise ValueError("JSON has excessive depth") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc: raise ValueError("JSON is invalid") from exc
    if end != len(text): raise ValueError("JSON has trailing data")
    pending = [(value, 0)]
    while pending:
        current, depth = pending.pop()
        if isinstance(current, Mapping): pending.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list): pending.extend((item, depth + 1) for item in current)
        if depth > MAX_JSON_DEPTH: raise ValueError("JSON has excessive depth")
    if not isinstance(value, Mapping): raise ValueError("JSON root must be an object")
    return value


PHASES = ("OPEN", "PIN_CANDIDATE", "ACQUIRE", "REREAD", "VALIDATE_PROPOSAL", "PUBLISH_INDEX", "COMMIT", "READ_SUCCESSOR", "QUERY_OPERATION", "RELEASE")
PHASE_STATUSES = {
    "OPEN": frozenset({"OPENED"}), "PIN_CANDIDATE": frozenset({"PINNED"}),
    "ACQUIRE": frozenset({"ACQUIRED"}), "REREAD": frozenset({"REREAD"}),
    "VALIDATE_PROPOSAL": frozenset({"PROPOSAL_ACCEPTED_NO_WRITE", "PROPOSAL_REJECTED_NO_WRITE"}),
    "PUBLISH_INDEX": frozenset({"PUBLISHED", "NOT_PUBLISHED", "UNKNOWN"}),
    "COMMIT": frozenset({"COMMIT_RESULT"}), "READ_SUCCESSOR": frozenset({"READ"}),
    "QUERY_OPERATION": frozenset({"QUERY"}), "RELEASE": frozenset({"RELEASED", "RELEASE_WARNING"}),
}
_PHASE_FIELDS = {"phase_result_version", "record_type", "phase", "transaction_id", "request_sha256",
                 "backend_operation_witness_sha256", "evidence_source", "producer_issuer_binding_sha256",
                 "issuer_admission", "phase_status", "no_manifest_write_proven",
                 "manifest_commit_observation", "reason_code", "payload", "phase_result_sha256"}


def parse_phase_result(value: Mapping[str, Any], *, expected_phase: str) -> ContractRecord:
    _bounded(value, "ProjectJobCurrentnessPhaseResultV2", large=expected_phase in {"OPEN", "REREAD", "VALIDATE_PROPOSAL"}); body = copy.deepcopy(dict(value)); _exact(body, _PHASE_FIELDS, "ProjectJobCurrentnessPhaseResultV2")
    if body["phase_result_version"] != "PROJECT_JOB_CURRENTNESS_PHASE_RESULT_V2" or body["record_type"] != "ProjectJobCurrentnessPhaseResultV2" or body["phase"] != expected_phase or expected_phase not in PHASES:
        raise ValueError("phase discriminator mismatch")
    _id(body["transaction_id"], "transaction_id"); _sha(body["request_sha256"], "request_sha256")
    _sha(body["backend_operation_witness_sha256"], "backend_operation_witness_sha256")
    EvidenceSource(body["evidence_source"]); _sha(body["producer_issuer_binding_sha256"], "producer_issuer_binding_sha256")
    if body["issuer_admission"] not in {"ACCEPTED", "NOT_ACCEPTED"}: raise ValueError("issuer admission unsupported")
    if body["phase_status"] not in PHASE_STATUSES[expected_phase]: raise ValueError("phase status unsupported")
    if not isinstance(body["no_manifest_write_proven"], bool): raise ValueError("no_manifest_write_proven must be boolean")
    if body["manifest_commit_observation"] not in {"COMMITTED", "NOT_COMMITTED", "UNKNOWN"}: raise ValueError("manifest observation unsupported")
    if body["reason_code"] is not None and body["reason_code"] not in REASON_CODES: raise ValueError("phase reason unsupported")
    if not isinstance(body["payload"], Mapping): raise ValueError("phase payload must be object")
    payload = copy.deepcopy(dict(body["payload"])); body["payload"] = payload
    if expected_phase in {"OPEN", "REREAD"}:
        _exact(payload, {"snapshot"}, f"{expected_phase} payload"); payload["snapshot"] = parse_snapshot(payload["snapshot"]).to_dict()
    elif expected_phase == "PIN_CANDIDATE":
        _exact(payload, {"candidate_sha256", "candidate_readback_sha256", "event_physical_identity_ref", "predecessor_event_physical_identity_ref"}, "PIN_CANDIDATE payload")
        _sha(payload["candidate_sha256"], "candidate_sha256"); _sha(payload["candidate_readback_sha256"], "candidate_readback_sha256")
        _id(payload["event_physical_identity_ref"], "event_physical_identity_ref", reference=True)
        if payload["predecessor_event_physical_identity_ref"] is not None: _id(payload["predecessor_event_physical_identity_ref"], "predecessor_event_physical_identity_ref", reference=True)
    elif expected_phase == "ACQUIRE":
        _exact(payload, {"lease_ref", "project_root_identity_ref", "manifest_physical_identity_ref", "state_coordinate_sha256"}, "ACQUIRE payload")
        for field in ("lease_ref", "project_root_identity_ref", "manifest_physical_identity_ref"): _id(payload[field], field, reference=True)
        _sha(payload["state_coordinate_sha256"], "state_coordinate_sha256")
    elif expected_phase == "VALIDATE_PROPOSAL":
        fields = {"proposal_sha256", "successor_manifest_sha256", "index_sha256", "prior_project_invariant_fields_sha256", "successor_project_invariant_fields_sha256", "prior_unrelated_child_bindings_sha256", "successor_unrelated_child_bindings_sha256"}
        _exact(payload, fields, "VALIDATE_PROPOSAL payload")
        for field in fields: _sha(payload[field], field)
    elif expected_phase == "PUBLISH_INDEX":
        _exact(payload, {"publication_state", "index_sha256", "index_physical_identity_ref"}, "PUBLISH_INDEX payload")
        if payload["publication_state"] not in {"PUBLISHED_ORPHAN_SAFE", "NOT_PUBLISHED", "UNKNOWN"}: raise ValueError("publication state unsupported")
        _sha(payload["index_sha256"], "index_sha256")
        if payload["index_physical_identity_ref"] is not None: _id(payload["index_physical_identity_ref"], "index_physical_identity_ref", reference=True)
    elif expected_phase in {"COMMIT", "QUERY_OPERATION"}:
        _exact(payload, {"witness_state", "successor_manifest_sha256", "successor_manifest_physical_identity_ref"}, f"{expected_phase} payload")
        if payload["witness_state"] not in {"SAME_OPERATION_COMMITTED_CURRENT", "SAME_OPERATION_COMMITTED_SUPERSEDED", "SAME_OPERATION_NOT_COMMITTED", "SAME_OPERATION_HISTORY_UNKNOWN"}: raise ValueError("operation witness unsupported")
        if payload["successor_manifest_sha256"] is not None: _sha(payload["successor_manifest_sha256"], "successor_manifest_sha256")
        if payload["successor_manifest_physical_identity_ref"] is not None: _id(payload["successor_manifest_physical_identity_ref"], "successor_manifest_physical_identity_ref", reference=True)
    elif expected_phase == "READ_SUCCESSOR":
        _exact(payload, {"readback"}, "READ_SUCCESSOR payload"); payload["readback"] = parse_readback(payload["readback"]).to_dict()
    elif expected_phase == "RELEASE":
        _exact(payload, {"release_state"}, "RELEASE payload")
        if payload["release_state"] not in {"RELEASED", "RELEASE_WARNING"}: raise ValueError("release state unsupported")
        if body["phase_status"] != payload["release_state"]:
            raise ValueError("release status/payload contradiction")
    if expected_phase == "VALIDATE_PROPOSAL" and (
        body["no_manifest_write_proven"] is not True or body["manifest_commit_observation"] != "NOT_COMMITTED"
    ):
        raise ValueError("proposal validation must prove no manifest write")
    if expected_phase == "PUBLISH_INDEX":
        expected_publication = {"PUBLISHED": "PUBLISHED_ORPHAN_SAFE", "NOT_PUBLISHED": "NOT_PUBLISHED", "UNKNOWN": "UNKNOWN"}[body["phase_status"]]
        if payload["publication_state"] != expected_publication:
            raise ValueError("publish status/payload contradiction")
        if body["phase_status"] == "UNKNOWN":
            if body["manifest_commit_observation"] != "UNKNOWN" or body["no_manifest_write_proven"] is not False:
                raise ValueError("unknown publication evidence is contradictory")
        elif body["manifest_commit_observation"] != "NOT_COMMITTED" or body["no_manifest_write_proven"] is not True:
            raise ValueError("known publication must prove no manifest write")
        if (payload["publication_state"] == "PUBLISHED_ORPHAN_SAFE") != (payload["index_physical_identity_ref"] is not None):
            raise ValueError("publication physical identity contradiction")
    if expected_phase in {"COMMIT", "QUERY_OPERATION"}:
        witness = payload["witness_state"]
        committed = witness in {"SAME_OPERATION_COMMITTED_CURRENT", "SAME_OPERATION_COMMITTED_SUPERSEDED"}
        no_commit = witness == "SAME_OPERATION_NOT_COMMITTED"
        if committed:
            if body["manifest_commit_observation"] != "COMMITTED" or body["no_manifest_write_proven"] is not False or payload["successor_manifest_sha256"] is None or payload["successor_manifest_physical_identity_ref"] is None:
                raise ValueError("committed witness envelope is contradictory")
        elif no_commit:
            if body["manifest_commit_observation"] != "NOT_COMMITTED" or body["no_manifest_write_proven"] is not True or payload["successor_manifest_sha256"] is not None or payload["successor_manifest_physical_identity_ref"] is not None:
                raise ValueError("no-commit witness envelope is contradictory")
        elif body["manifest_commit_observation"] != "UNKNOWN" or body["no_manifest_write_proven"] is not False or payload["successor_manifest_sha256"] is not None or payload["successor_manifest_physical_identity_ref"] is not None:
            raise ValueError("unknown witness envelope is contradictory")
    if expected_phase == "READ_SUCCESSOR" and body["manifest_commit_observation"] != "COMMITTED":
        raise ValueError("successor read must preserve committed observation")
    _verify_digest(body, "phase_result_sha256", _DOMAINS["phase"])
    return ContractRecord("phase", _freeze(body), _token=_FACTORY_KEY)


def create_phase_result(*, phase: str, transaction_id: str, request_sha256: str, evidence_source: str,
                        producer_issuer_binding_sha256: str, phase_status: str, payload: Mapping[str, Any],
                        issuer_admission: str = "NOT_ACCEPTED", no_manifest_write_proven: bool = False,
                        manifest_commit_observation: str = "NOT_COMMITTED", reason_code: str | None = None) -> dict[str, Any]:
    body = {"phase_result_version": "PROJECT_JOB_CURRENTNESS_PHASE_RESULT_V2", "record_type": "ProjectJobCurrentnessPhaseResultV2",
            "phase": phase, "transaction_id": transaction_id, "request_sha256": request_sha256,
            "backend_operation_witness_sha256": sha256_bytes(_DOMAINS["phase"] + canonical_json_bytes({"phase": phase, "transaction_id": transaction_id, "status": phase_status})),
            "evidence_source": evidence_source, "producer_issuer_binding_sha256": producer_issuer_binding_sha256,
            "issuer_admission": issuer_admission, "phase_status": phase_status, "no_manifest_write_proven": no_manifest_write_proven,
            "manifest_commit_observation": manifest_commit_observation, "reason_code": reason_code, "payload": copy.deepcopy(dict(payload))}
    body["phase_result_sha256"] = _digest(body, "phase_result_sha256", _DOMAINS["phase"])
    return body


class ProjectJobCurrentnessBackendV2(Protocol):
    def open_prior(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def pin_candidate(self, request: Mapping[str, Any], candidate: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def acquire_exclusive(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def reread_under_lease(self, request: Mapping[str, Any], lease_ref: str) -> Mapping[str, Any]: ...
    def validate_successor_proposal(self, request: Mapping[str, Any], index: Mapping[str, Any], proposal: Mapping[str, Any], lease_ref: str) -> Mapping[str, Any]: ...
    def publish_index_generation(self, request: Mapping[str, Any], index: Mapping[str, Any], lease_ref: str) -> Mapping[str, Any]: ...
    def commit_manifest_successor(self, request: Mapping[str, Any], index_readback: Mapping[str, Any], lease_ref: str) -> Mapping[str, Any]: ...
    def read_successor(self, request: Mapping[str, Any], lease_ref: str) -> Mapping[str, Any]: ...
    def query_operation(self, transaction_id: str, request_sha256: str) -> Mapping[str, Any]: ...
    def release(self, request: Mapping[str, Any], lease_ref: str) -> Mapping[str, Any]: ...


def classify_operation_witness(witness: Mapping[str, Any]) -> tuple[TransactionState, str, str]:
    state = witness.get("witness_state")
    if state == "SAME_OPERATION_COMMITTED_CURRENT": return TransactionState.COMMITTED, "COMMITTED", "SELECTED"
    if state == "SAME_OPERATION_COMMITTED_SUPERSEDED": return TransactionState.UNKNOWN, "COMMITTED", "SUPERSEDED_PRESERVED"
    if state == "SAME_OPERATION_NOT_COMMITTED": return TransactionState.CONFLICT, "NOT_COMMITTED", "ORPHAN_PRESERVED"
    return TransactionState.UNKNOWN, "UNKNOWN", "UNKNOWN"


_PROPOSAL_FIELDS = {
    "proposal_version", "record_type", "project_id", "project_format_id", "project_format_version",
    "prior_manifest_revision", "prior_manifest_sha256", "prior_manifest_physical_identity_ref",
    "successor_manifest_revision", "predecessor_manifest_sha256", "successor_manifest_sha256",
    "updated_at", "prior_project_invariant_fields_sha256", "successor_project_invariant_fields_sha256",
    "prior_unrelated_child_bindings_sha256", "successor_unrelated_child_bindings_sha256",
    "prior_task099_child_binding", "successor_task099_child_binding", "evidence_source",
    "producer_issuer_binding_sha256", "proposal_sha256",
}


def parse_proposal(value: Mapping[str, Any]) -> ContractRecord:
    _bounded(value, "ProjectManifestSuccessorProposalV2", large=True); body = copy.deepcopy(dict(value)); _exact(body, _PROPOSAL_FIELDS, "ProjectManifestSuccessorProposalV2")
    if body["proposal_version"] != PROPOSAL_VERSION or body["record_type"] != "ProjectManifestSuccessorProposalV2": raise ValueError("proposal discriminator mismatch")
    for field in ("project_id", "project_format_id", "project_format_version"): _id(body[field], field)
    prior = _positive(body["prior_manifest_revision"], "prior_manifest_revision")
    if _positive(body["successor_manifest_revision"], "successor_manifest_revision") != prior + 1: raise ValueError("successor manifest revision must advance once")
    for field in ("prior_manifest_sha256", "predecessor_manifest_sha256", "successor_manifest_sha256",
                  "prior_project_invariant_fields_sha256", "successor_project_invariant_fields_sha256",
                  "prior_unrelated_child_bindings_sha256", "successor_unrelated_child_bindings_sha256",
                  "producer_issuer_binding_sha256"):
        _sha(body[field], field)
    if body["predecessor_manifest_sha256"] != body["prior_manifest_sha256"]: raise ValueError("proposal predecessor mismatch")
    if body["prior_project_invariant_fields_sha256"] != body["successor_project_invariant_fields_sha256"] or body["prior_unrelated_child_bindings_sha256"] != body["successor_unrelated_child_bindings_sha256"]: raise ValueError("proposal changes unrelated Project content")
    _id(body["prior_manifest_physical_identity_ref"], "prior_manifest_physical_identity_ref", reference=True)
    _time(body["updated_at"], "updated_at"); EvidenceSource(body["evidence_source"])
    prior_binding = body["prior_task099_child_binding"]
    if prior_binding is not None:
        _exact(prior_binding, {"content_sha256"}, "prior_task099_child_binding")
        _sha(prior_binding["content_sha256"], "prior TASK-099 content_sha256")
    successor_binding = body["successor_task099_child_binding"]
    if not isinstance(successor_binding, Mapping): raise ValueError("successor TASK-099 binding is required")
    _exact(successor_binding, {"content_sha256"}, "successor_task099_child_binding")
    _sha(successor_binding["content_sha256"], "successor TASK-099 content_sha256")
    _verify_digest(body, "proposal_sha256", _DOMAINS["proposal"])
    return ContractRecord("proposal", _freeze(body), _token=_FACTORY_KEY)


_REQUEST_FIELDS = {
    "request_version", "record_type", "transaction_id", "project_id", "job_semantic_key_sha256",
    "prior_readback_sha256", "prior_state_coordinate_sha256", "candidate_sha256",
    "candidate_readback_sha256", "manifest_successor_proposal_sha256", "successor_manifest_revision",
    "successor_index_revision", "successor_index_sha256", "namespace_plan_set_sha256",
    "consumer_operation_id", "install_build_binding_sha256", "security_reader_binding_sha256",
    "requested_at", "expires_at", "request_sha256",
}


def parse_request(value: Mapping[str, Any]) -> ContractRecord:
    _bounded(value, "ProjectJobCurrentnessTransactionRequestV2"); body = copy.deepcopy(dict(value)); _exact(body, _REQUEST_FIELDS, "ProjectJobCurrentnessTransactionRequestV2")
    if body["request_version"] != REQUEST_VERSION or body["record_type"] != "ProjectJobCurrentnessTransactionRequestV2": raise ValueError("request discriminator mismatch")
    for field in ("transaction_id", "project_id", "consumer_operation_id"): _id(body[field], field)
    for field in ("job_semantic_key_sha256", "prior_readback_sha256", "prior_state_coordinate_sha256",
                  "candidate_sha256", "candidate_readback_sha256", "manifest_successor_proposal_sha256",
                  "successor_index_sha256", "namespace_plan_set_sha256", "install_build_binding_sha256",
                  "security_reader_binding_sha256"):
        _sha(body[field], field)
    _positive(body["successor_manifest_revision"], "successor_manifest_revision"); _positive(body["successor_index_revision"], "successor_index_revision")
    if _time(body["requested_at"], "requested_at") >= _time(body["expires_at"], "expires_at"): raise ValueError("request validity interval is empty")
    _verify_digest(body, "request_sha256", _DOMAINS["request"])
    return ContractRecord("request", _freeze(body), _token=_FACTORY_KEY)


def create_digested_record(body: Mapping[str, Any], *, kind: str, field: str) -> dict[str, Any]:
    """Create a deterministic test/producer record before strict parsing."""
    if kind not in _DOMAINS: raise ValueError("unsupported digest kind")
    value = copy.deepcopy(dict(body)); value[field] = _digest(value, field, _DOMAINS[kind]); return value


_SNAPSHOT_FIELDS = {
    "snapshot_version", "record_type", "readback", "index_state", "index",
    "manifest_canonical_sha256", "manifest_physical_identity_ref",
    "project_invariant_fields_sha256", "unrelated_child_bindings_sha256",
    "task099_child_binding_state", "producer_issuer_binding_sha256",
    "evidence_source", "snapshot_sha256",
}


def parse_snapshot(value: Mapping[str, Any]) -> ContractRecord:
    _bounded(value, "ProjectJobCurrentnessSnapshotV2", large=True)
    body = copy.deepcopy(dict(value)); _exact(body, _SNAPSHOT_FIELDS, "ProjectJobCurrentnessSnapshotV2")
    if body["snapshot_version"] != SNAPSHOT_VERSION or body["record_type"] != "ProjectJobCurrentnessSnapshotV2":
        raise ValueError("snapshot discriminator mismatch")
    readback = parse_readback(body["readback"]).to_dict(); body["readback"] = readback
    for field in ("manifest_canonical_sha256", "project_invariant_fields_sha256",
                  "unrelated_child_bindings_sha256", "producer_issuer_binding_sha256"):
        _sha(body[field], field)
    _id(body["manifest_physical_identity_ref"], "manifest_physical_identity_ref", reference=True)
    source = EvidenceSource(body["evidence_source"])
    if source.value != readback["evidence_source"] or body["producer_issuer_binding_sha256"] != readback["producer_issuer_binding_sha256"]:
        raise ValueError("snapshot producer binding mismatch")
    if (body["manifest_canonical_sha256"], body["manifest_physical_identity_ref"]) != (readback["manifest_sha256"], readback["manifest_physical_identity_ref"]):
        raise ValueError("snapshot manifest binding mismatch")
    if body["index_state"] == "UNINITIALIZED":
        if body["index"] is not None or body["task099_child_binding_state"] != "ABSENT":
            raise ValueError("uninitialized snapshot must have no TASK-099 binding")
        if readback["head"]["variant"] != "ABSENT_JOB_HEAD" or readback["head"]["index_state"] != "UNINITIALIZED":
            raise ValueError("uninitialized snapshot conflicts with readback")
    elif body["index_state"] == "PRESENT":
        index = parse_index(body["index"]).to_dict(); body["index"] = index
        if body["task099_child_binding_state"] != "PRESENT" or index["project_id"] != readback["project_id"]:
            raise ValueError("present snapshot binding mismatch")
        head = readback["head"]
        if head["index_state"] != "PRESENT" or (head["index_revision"], head["index_sha256"]) != (index["index_revision"], index["index_sha256"]):
            raise ValueError("snapshot index conflicts with readback")
    else:
        raise ValueError("snapshot index_state unsupported")
    _verify_digest(body, "snapshot_sha256", _DOMAINS["snapshot"])
    return ContractRecord("snapshot", _freeze(body), _token=_FACTORY_KEY)


_RESULT_FIELDS = {
    "result_version", "record_type", "transaction_id", "request_sha256", "candidate_sha256",
    "prior_readback_sha256", "successor_readback_sha256", "outcome_evidence_sha256", "transaction_state", "evidence_source",
    "producer_issuer_binding_sha256", "currentness_capability", "live_currentness_eligible",
    "manifest_commit_observation", "index_disposition", "reason_codes", "retry_authorized",
    "blind_replay_authorized", "job_effect_authorized", "cleanup_authorized",
    "release_deploy_production_authorized", "result_sha256",
}


def parse_result(value: Mapping[str, Any]) -> ContractRecord:
    _bounded(value, "ProjectJobCurrentnessTransactionResultV2")
    body = copy.deepcopy(dict(value)); _exact(body, _RESULT_FIELDS, "ProjectJobCurrentnessTransactionResultV2")
    if body["result_version"] != RESULT_VERSION or body["record_type"] != "ProjectJobCurrentnessTransactionResultV2":
        raise ValueError("result discriminator mismatch")
    _id(body["transaction_id"], "transaction_id")
    for field in ("request_sha256", "candidate_sha256", "prior_readback_sha256", "outcome_evidence_sha256", "producer_issuer_binding_sha256"):
        _sha(body[field], field)
    if body["successor_readback_sha256"] is not None: _sha(body["successor_readback_sha256"], "successor_readback_sha256")
    state = TransactionState(body["transaction_state"]); source = EvidenceSource(body["evidence_source"])
    if body["currentness_capability"] not in {"CURRENT", "FIXTURE_ONLY"}: raise ValueError("result capability unsupported")
    if not isinstance(body["live_currentness_eligible"], bool): raise ValueError("live eligibility must be boolean")
    if body["manifest_commit_observation"] not in {"COMMITTED", "NOT_COMMITTED", "UNKNOWN"}: raise ValueError("manifest observation unsupported")
    if body["index_disposition"] not in {"SELECTED", "NOT_PUBLISHED", "ORPHAN_PRESERVED", "SUPERSEDED_PRESERVED", "UNKNOWN"}: raise ValueError("index disposition unsupported")
    reasons = body["reason_codes"]
    if not isinstance(reasons, list) or len(reasons) > 24 or len(set(reasons)) != len(reasons) or any(code not in REASON_CODES for code in reasons): raise ValueError("result reason set invalid")
    for field in ("retry_authorized", "blind_replay_authorized", "job_effect_authorized", "cleanup_authorized", "release_deploy_production_authorized"):
        if body[field] is not False: raise ValueError(f"{field} must remain false")
    if state is TransactionState.COMMITTED:
        if body["successor_readback_sha256"] is None or body["manifest_commit_observation"] != "COMMITTED" or body["index_disposition"] != "SELECTED": raise ValueError("committed result lacks confirmed successor")
    elif state in {TransactionState.CONFLICT, TransactionState.BLOCKED}:
        if body["successor_readback_sha256"] is not None or body["manifest_commit_observation"] != "NOT_COMMITTED": raise ValueError("no-write result is inconsistent")
    elif body["successor_readback_sha256"] is not None or body["manifest_commit_observation"] not in {"COMMITTED", "UNKNOWN"}:
        raise ValueError("unknown result has an invalid success projection")
    expected_capability = "CURRENT" if source is EvidenceSource.TRUSTED and state is TransactionState.COMMITTED else "FIXTURE_ONLY"
    expected_live = expected_capability == "CURRENT"
    if body["live_currentness_eligible"] is not expected_live or body["currentness_capability"] != expected_capability:
        raise ValueError("result evidence/capability mismatch")
    _verify_digest(body, "result_sha256", _DOMAINS["result"])
    return ContractRecord("result", _freeze(body), _token=_FACTORY_KEY)


def project_public_result(result: ContractRecord | Mapping[str, Any], *, project_id: str,
                          job_semantic_key_sha256: str, current_event_sha256: str | None = None) -> Mapping[str, Any]:
    parsed = parse_result(result.to_dict() if isinstance(result, ContractRecord) else result).to_dict()
    _id(project_id, "project_id"); _sha(job_semantic_key_sha256, "job_semantic_key_sha256")
    if current_event_sha256 is not None: _sha(current_event_sha256, "current_event_sha256")
    if parsed["transaction_state"] != TransactionState.COMMITTED.value: current_event_sha256 = None
    return MappingProxyType({key: value for key, value in {
        "project_id": project_id, "job_semantic_key_sha256": job_semantic_key_sha256,
        "transaction_state": parsed["transaction_state"], "evidence_source": parsed["evidence_source"],
        "live_currentness_eligible": parsed["live_currentness_eligible"], "current_event_sha256": current_event_sha256,
        "reason_codes": tuple(parsed["reason_codes"]), "result_sha256": parsed["result_sha256"],
        "successor_readback_sha256": parsed["successor_readback_sha256"],
    }.items()})


def _result(
    request: Mapping[str, Any], candidate: Mapping[str, Any], prior: Mapping[str, Any],
    *, state: TransactionState, successor: Mapping[str, Any] | None,
    manifest_observation: str, index_disposition: str, reason_codes: list[str], outcome_evidence_sha256: str,
) -> ContractRecord:
    if len(reason_codes) > 24 or len(set(reason_codes)) != len(reason_codes) or any(code not in REASON_CODES for code in reason_codes): raise ValueError("result reason set is invalid")
    source = request.get("evidence_source", candidate["evidence_source"])
    capability = "CURRENT" if source == EvidenceSource.TRUSTED.value and state is TransactionState.COMMITTED else "FIXTURE_ONLY"
    body = {
        "result_version": RESULT_VERSION, "record_type": "ProjectJobCurrentnessTransactionResultV2",
        "transaction_id": request["transaction_id"], "request_sha256": request["request_sha256"],
        "candidate_sha256": candidate["candidate_sha256"], "prior_readback_sha256": prior["readback_sha256"],
        "successor_readback_sha256": None if successor is None else successor["readback_sha256"],
        "outcome_evidence_sha256": _sha(outcome_evidence_sha256, "outcome_evidence_sha256"),
        "transaction_state": state.value, "evidence_source": source,
        "producer_issuer_binding_sha256": candidate["producer_issuer_binding_sha256"],
        "currentness_capability": capability, "live_currentness_eligible": capability == "CURRENT",
        "manifest_commit_observation": manifest_observation, "index_disposition": index_disposition,
        "reason_codes": reason_codes, "retry_authorized": False, "blind_replay_authorized": False,
        "job_effect_authorized": False, "cleanup_authorized": False,
        "release_deploy_production_authorized": False,
    }
    body["result_sha256"] = _digest(body, "result_sha256", _DOMAINS["result"])
    return parse_result(body)


def execute_transaction(
    request: ContractRecord | Mapping[str, Any], candidate: ContractRecord | Mapping[str, Any],
    prior_readback: ContractRecord | Mapping[str, Any], prior_index: ContractRecord | Mapping[str, Any] | None,
    proposal: ContractRecord | Mapping[str, Any], backend: ProjectJobCurrentnessBackendV2,
) -> ContractRecord:
    req = parse_request(request.to_dict() if isinstance(request, ContractRecord) else request).to_dict()
    cand = parse_candidate(candidate.to_dict() if isinstance(candidate, ContractRecord) else candidate).to_dict()
    prior = parse_readback(prior_readback.to_dict() if isinstance(prior_readback, ContractRecord) else prior_readback)
    prop = parse_proposal(proposal.to_dict() if isinstance(proposal, ContractRecord) else proposal).to_dict()
    index = compile_successor_index(prior_index, prior, ContractRecord("candidate", _freeze(cand), _token=_FACTORY_KEY)).to_dict()
    bindings = ((req["project_id"], cand["project_id"], prior.data["project_id"], prop["project_id"]),
                (req["job_semantic_key_sha256"], cand["job_semantic_key_sha256"], prior.data["job_semantic_key_sha256"]),
                (req["namespace_plan_set_sha256"], cand["namespace_plan_set_sha256"], prior.data["namespace_plan_set_sha256"]),
                (req["consumer_operation_id"], cand["consumer_operation_id"], prior.data["consumer_operation_id"]),
                (req["install_build_binding_sha256"], cand["install_build_binding_sha256"], prior.data["install_build_binding_sha256"]),
                (req["security_reader_binding_sha256"], cand["security_reader_binding_sha256"], prior.data["security_reader_binding_sha256"]))
    if any(len(set(values)) != 1 for values in bindings): raise ValueError("transaction bindings do not agree")
    if req["prior_readback_sha256"] != prior.data["readback_sha256"] or req["candidate_sha256"] != cand["candidate_sha256"] or req["manifest_successor_proposal_sha256"] != prop["proposal_sha256"] or req["successor_index_sha256"] != index["index_sha256"] or req["successor_index_revision"] != index["index_revision"] or req["successor_manifest_revision"] != prop["successor_manifest_revision"]:
        raise ValueError("request does not bind compiled inputs")
    if req["prior_state_coordinate_sha256"] != prior.data["trusted_currentness_coordinate"]["state"]["state_coordinate_sha256"] or req["candidate_readback_sha256"] != cand["task076_candidate_readback_sha256"]:
        raise ValueError("request does not bind producer readbacks")
    if (prop["prior_manifest_revision"], prop["prior_manifest_sha256"], prop["prior_manifest_physical_identity_ref"]) != (
        prior.data["manifest_revision"], prior.data["manifest_sha256"], prior.data["manifest_physical_identity_ref"]
    ):
        raise ValueError("proposal does not bind the exact prior manifest")
    successor_binding = prop["successor_task099_child_binding"]
    if not isinstance(successor_binding, Mapping) or successor_binding.get("content_sha256") != index["index_sha256"]:
        raise ValueError("proposal does not bind the compiled index")
    if prop["evidence_source"] != cand["evidence_source"] or prop["producer_issuer_binding_sha256"] != cand["producer_issuer_binding_sha256"]:
        raise ValueError("proposal producer binding mismatch")
    requested = _time(req["requested_at"], "requested_at")
    if not (_time(cand["observed_at"], "candidate observed_at") <= requested < _time(cand["expires_at"], "candidate expires_at")):
        raise ValueError("candidate is not current for the request")
    observation = prior.data["trusted_currentness_coordinate"]["observation"]
    if not (_time(observation["observed_at"], "readback observed_at") <= requested < _time(observation["expires_at"], "readback expires_at")):
        raise ValueError("prior readback is not current for the request")
    def phase(name: str, raw: Mapping[str, Any]) -> dict[str, Any]:
        result = parse_phase_result(raw, expected_phase=name).to_dict()
        if result["transaction_id"] != req["transaction_id"] or result["request_sha256"] != req["request_sha256"]:
            raise ValueError("phase result operation binding mismatch")
        if result["evidence_source"] != cand["evidence_source"] or result["producer_issuer_binding_sha256"] != cand["producer_issuer_binding_sha256"]:
            raise ValueError("phase producer binding mismatch")
        if cand["evidence_source"] == EvidenceSource.TRUSTED.value and result["issuer_admission"] != "ACCEPTED":
            raise ValueError("trusted phase issuer is not admitted")
        return result

    expected_prior_index = None if prior_index is None else parse_index(prior_index.to_dict() if isinstance(prior_index, ContractRecord) else prior_index).to_dict()
    open_result = phase("OPEN", backend.open_prior(req))
    open_payload = open_result["payload"]
    _exact(open_payload, {"snapshot"}, "OPEN payload")
    opened = parse_snapshot(open_payload["snapshot"]).to_dict()
    if opened["readback"] != prior.to_dict() or opened["index"] != expected_prior_index:
        raise ValueError("OPEN snapshot does not bind the prior readback")
    pin_result = phase("PIN_CANDIDATE", backend.pin_candidate(req, cand))
    pin_payload = pin_result["payload"]
    _exact(pin_payload, {"candidate_sha256", "candidate_readback_sha256", "event_physical_identity_ref", "predecessor_event_physical_identity_ref"}, "PIN payload")
    if (pin_payload["candidate_sha256"], pin_payload["candidate_readback_sha256"], pin_payload["event_physical_identity_ref"], pin_payload["predecessor_event_physical_identity_ref"]) != (cand["candidate_sha256"], cand["task076_candidate_readback_sha256"], cand["event_physical_identity_ref"], cand["predecessor_event_physical_identity_ref"]):
        raise ValueError("PIN result does not bind candidate identity")
    acquire_result = phase("ACQUIRE", backend.acquire_exclusive(req)); acquire_payload = acquire_result["payload"]
    _exact(acquire_payload, {"lease_ref", "project_root_identity_ref", "manifest_physical_identity_ref", "state_coordinate_sha256"}, "ACQUIRE payload")
    lease_ref = _id(acquire_payload["lease_ref"], "lease_ref", reference=True)
    if (acquire_payload["project_root_identity_ref"], acquire_payload["manifest_physical_identity_ref"], acquire_payload["state_coordinate_sha256"]) != (prior.data["project_root_identity_ref"], prior.data["manifest_physical_identity_ref"], req["prior_state_coordinate_sha256"]):
        raise ValueError("lease binds a different Project state")
    released = False
    release_succeeded = False
    def release_lease() -> bool:
        nonlocal released, release_succeeded
        if released: return release_succeeded
        released = True
        try:
            release_result = phase("RELEASE", backend.release(req, lease_ref))
            release_succeeded = release_result["payload"]["release_state"] == "RELEASED"
        except BaseException:
            release_succeeded = False
        return release_succeeded
    def finish(*, state: TransactionState, successor: Mapping[str, Any] | None,
               manifest_observation: str, index_disposition: str, reason_codes: list[str],
               outcome_evidence_sha256: str) -> ContractRecord:
        reasons = list(reason_codes)
        if not release_lease() and "LEASE_RELEASE_WARNING" not in reasons:
            reasons.append("LEASE_RELEASE_WARNING")
        return _result(req, cand, prior.to_dict(), state=state, successor=successor,
                       manifest_observation=manifest_observation, index_disposition=index_disposition,
                       reason_codes=reasons, outcome_evidence_sha256=outcome_evidence_sha256)
    def guarded(name: str, operation: Any) -> dict[str, Any]:
        try:
            return phase(name, operation())
        except BaseException:
            release_lease()
            raise
    def stable_snapshot(snapshot: Mapping[str, Any]) -> bool:
        left, right = copy.deepcopy(opened), copy.deepcopy(dict(snapshot))
        for item in (left, right):
            item.pop("snapshot_sha256", None)
            item["readback"].pop("readback_sha256", None)
            item["readback"]["trusted_currentness_coordinate"].pop("observation", None)
        return left == right

    reread_result = guarded("REREAD", lambda: backend.reread_under_lease(req, lease_ref)); reread_snapshot = reread_result["payload"]["snapshot"]
    reread = reread_snapshot["readback"]
    reread_observation = reread["trusted_currentness_coordinate"]["observation"]
    opened_observation = opened["readback"]["trusted_currentness_coordinate"]["observation"]
    same_prior = stable_snapshot(reread_snapshot) and reread["trusted_currentness_coordinate"]["state"]["state_coordinate_sha256"] == req["prior_state_coordinate_sha256"]
    fresh_prior = (
        reread_observation["observation_sequence"] >= opened_observation["observation_sequence"]
        and _time(reread_observation["observed_at"], "reread observed_at") >= _time(opened_observation["observed_at"], "opened observed_at")
    )
    if not same_prior or not fresh_prior:
        if reread_result["no_manifest_write_proven"] is True and reread_result["manifest_commit_observation"] == "NOT_COMMITTED":
            return finish(state=TransactionState.CONFLICT, successor=None, manifest_observation="NOT_COMMITTED", index_disposition="NOT_PUBLISHED", reason_codes=["STALE_PRIOR_READBACK"], outcome_evidence_sha256=reread_result["phase_result_sha256"])
        return finish(state=TransactionState.UNKNOWN, successor=None, manifest_observation="UNKNOWN", index_disposition="UNKNOWN", reason_codes=["SAME_OPERATION_HISTORY_UNKNOWN"], outcome_evidence_sha256=reread_result["phase_result_sha256"])
    validate_result = guarded("VALIDATE_PROPOSAL", lambda: backend.validate_successor_proposal(req, index, prop, lease_ref)); validate_payload = validate_result["payload"]
    digest_fields = ("prior_project_invariant_fields_sha256", "successor_project_invariant_fields_sha256", "prior_unrelated_child_bindings_sha256", "successor_unrelated_child_bindings_sha256")
    _exact(validate_payload, {"proposal_sha256", "successor_manifest_sha256", "index_sha256", *digest_fields}, "VALIDATE_PROPOSAL payload")
    expected_validate = {"proposal_sha256": prop["proposal_sha256"], "successor_manifest_sha256": prop["successor_manifest_sha256"], "index_sha256": index["index_sha256"], **{field: prop[field] for field in digest_fields}}
    if validate_result["phase_status"] != "PROPOSAL_ACCEPTED_NO_WRITE" or validate_payload != expected_validate:
        if validate_result["phase_status"] == "PROPOSAL_REJECTED_NO_WRITE" and validate_result["no_manifest_write_proven"] is True and validate_result["manifest_commit_observation"] == "NOT_COMMITTED":
            return finish(state=TransactionState.BLOCKED, successor=None, manifest_observation="NOT_COMMITTED", index_disposition="NOT_PUBLISHED", reason_codes=["MANIFEST_PROPOSAL_MISMATCH"], outcome_evidence_sha256=validate_result["phase_result_sha256"])
        return finish(state=TransactionState.UNKNOWN, successor=None, manifest_observation="UNKNOWN", index_disposition="UNKNOWN", reason_codes=["SAME_OPERATION_HISTORY_UNKNOWN"], outcome_evidence_sha256=validate_result["phase_result_sha256"])
    publish_result = guarded("PUBLISH_INDEX", lambda: backend.publish_index_generation(req, index, lease_ref)); publish_payload = publish_result["payload"]
    _exact(publish_payload, {"publication_state", "index_sha256", "index_physical_identity_ref"}, "PUBLISH_INDEX payload")
    if publish_payload["index_sha256"] != index["index_sha256"] or publish_payload["publication_state"] != "PUBLISHED_ORPHAN_SAFE":
        return finish(state=TransactionState.UNKNOWN, successor=None, manifest_observation="UNKNOWN", index_disposition="UNKNOWN", reason_codes=["INDEX_PUBLISH_UNKNOWN"], outcome_evidence_sha256=publish_result["phase_result_sha256"])
    _id(publish_payload["index_physical_identity_ref"], "index_physical_identity_ref", reference=True)
    try:
        commit_result = phase("COMMIT", backend.commit_manifest_successor(req, publish_payload, lease_ref))
    except BaseException:
        seam_evidence = sha256_bytes(_DOMAINS["result"] + canonical_json_bytes({"request_sha256": req["request_sha256"], "seam": "COMMIT_EXCEPTION"}))
        return finish(state=TransactionState.UNKNOWN, successor=None, manifest_observation="UNKNOWN", index_disposition="ORPHAN_PRESERVED", reason_codes=["MANIFEST_COMMIT_UNKNOWN"], outcome_evidence_sha256=seam_evidence)
    response = commit_result["payload"]
    _exact(response, {"witness_state", "successor_manifest_sha256", "successor_manifest_physical_identity_ref"}, "COMMIT payload")
    if response["successor_manifest_sha256"] is not None and response["successor_manifest_sha256"] != prop["successor_manifest_sha256"]:
        return finish(state=TransactionState.UNKNOWN, successor=None, manifest_observation="UNKNOWN", index_disposition="ORPHAN_PRESERVED", reason_codes=["MANIFEST_COMMIT_UNKNOWN"], outcome_evidence_sha256=commit_result["phase_result_sha256"])
    state, manifest, disposition = classify_operation_witness(response)
    outcome_evidence = commit_result["phase_result_sha256"]
    if response["witness_state"] == "SAME_OPERATION_HISTORY_UNKNOWN":
        try:
            query_result = phase("QUERY_OPERATION", backend.query_operation(req["transaction_id"], req["request_sha256"]))
        except BaseException:
            return finish(state=TransactionState.UNKNOWN, successor=None, manifest_observation="UNKNOWN", index_disposition="ORPHAN_PRESERVED", reason_codes=["SAME_OPERATION_HISTORY_UNKNOWN"], outcome_evidence_sha256=outcome_evidence)
        response = query_result["payload"]; outcome_evidence = query_result["phase_result_sha256"]
        if response["successor_manifest_sha256"] is not None and response["successor_manifest_sha256"] != prop["successor_manifest_sha256"]:
            return finish(state=TransactionState.UNKNOWN, successor=None, manifest_observation="COMMITTED", index_disposition="ORPHAN_PRESERVED", reason_codes=["MANIFEST_COMMIT_UNKNOWN"], outcome_evidence_sha256=outcome_evidence)
        state, manifest, disposition = classify_operation_witness(response)
        if state is TransactionState.CONFLICT and (query_result["no_manifest_write_proven"] is not True or query_result["manifest_commit_observation"] != "NOT_COMMITTED"):
            state, manifest, disposition = TransactionState.UNKNOWN, "UNKNOWN", "UNKNOWN"
    if state is TransactionState.COMMITTED:
        try:
            read_result = phase("READ_SUCCESSOR", backend.read_successor(req, lease_ref)); successor = read_result["payload"]["readback"]
        except BaseException:
            return finish(state=TransactionState.UNKNOWN, successor=None, manifest_observation="COMMITTED", index_disposition="ORPHAN_PRESERVED", reason_codes=["SUCCESSOR_READBACK_FAILED"], outcome_evidence_sha256=outcome_evidence)
        successor_state = successor["trusted_currentness_coordinate"]["state"]; prior_state = prior.data["trusted_currentness_coordinate"]["state"]
        successor_observation = successor["trusted_currentness_coordinate"]["observation"]
        expected_capability = "CURRENT" if cand["evidence_source"] == EvidenceSource.TRUSTED.value else "FIXTURE_ONLY"
        successor_ok = (
            (successor["project_id"], successor["job_semantic_key_sha256"], successor["namespace_plan_set_sha256"], successor["consumer_operation_id"], successor["install_build_binding_sha256"], successor["security_reader_binding_sha256"], successor["producer_issuer_binding_sha256"], successor["evidence_source"], successor["currentness_capability"])
            == (cand["project_id"], cand["job_semantic_key_sha256"], cand["namespace_plan_set_sha256"], cand["consumer_operation_id"], cand["install_build_binding_sha256"], cand["security_reader_binding_sha256"], cand["producer_issuer_binding_sha256"], cand["evidence_source"], expected_capability)
            and successor["project_root_identity_ref"] == prior.data["project_root_identity_ref"]
            and (successor["manifest_revision"], successor["manifest_sha256"], successor["predecessor_manifest_sha256"]) == (prop["successor_manifest_revision"], prop["successor_manifest_sha256"], prop["prior_manifest_sha256"])
            and response["successor_manifest_physical_identity_ref"] == successor["manifest_physical_identity_ref"]
            and (successor_state["authority_instance_id"], successor_state["epoch_id"], successor_state["manifest_generation_sequence"]) == (prior_state["authority_instance_id"], prior_state["epoch_id"], prior_state["manifest_generation_sequence"] + 1)
            and successor_observation["observation_sequence"] >= reread_observation["observation_sequence"]
            and _time(successor_observation["observed_at"], "successor observed_at") >= _time(reread_observation["observed_at"], "reread observed_at")
            and successor["head"]["variant"] == "SELECTED_JOB_HEAD"
            and (successor["head"]["index_revision"], successor["head"]["index_sha256"], successor["head"]["index_physical_identity_ref"]) == (index["index_revision"], index["index_sha256"], publish_payload["index_physical_identity_ref"])
            and (successor["head"]["event_coordinate"], successor["head"]["event_sha256"], successor["head"]["event_physical_identity_ref"]) == (cand["event_coordinate"], cand["event_sha256"], cand["event_physical_identity_ref"])
            and (successor["head"]["predecessor_event_coordinate"], successor["head"]["predecessor_event_sha256"], successor["head"]["predecessor_event_physical_identity_ref"]) == (cand["predecessor_event_coordinate"], cand["predecessor_event_sha256"], cand["predecessor_event_physical_identity_ref"])
        )
        if not successor_ok:
            return finish(state=TransactionState.UNKNOWN, successor=None, manifest_observation="COMMITTED", index_disposition="ORPHAN_PRESERVED", reason_codes=["SUCCESSOR_READBACK_FAILED"], outcome_evidence_sha256=read_result["phase_result_sha256"])
        return finish(state=state, successor=successor, manifest_observation=manifest, index_disposition=disposition, reason_codes=[] if cand["evidence_source"] == EvidenceSource.TRUSTED.value else ["FIXTURE_ONLY_EVIDENCE"], outcome_evidence_sha256=read_result["phase_result_sha256"])
    reason = "SAME_OPERATION_COMMIT_SUPERSEDED" if response.get("witness_state") == "SAME_OPERATION_COMMITTED_SUPERSEDED" else ("CONCURRENT_SUCCESSOR" if state is TransactionState.CONFLICT else "SAME_OPERATION_HISTORY_UNKNOWN")
    return finish(state=state, successor=None, manifest_observation=manifest, index_disposition=disposition, reason_codes=[reason], outcome_evidence_sha256=outcome_evidence)
