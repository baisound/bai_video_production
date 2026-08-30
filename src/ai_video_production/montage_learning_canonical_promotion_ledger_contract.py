"""Pure TASK-058 P1C-C canonical promotion ledger candidate contract.

The module evaluates caller-supplied immutable candidate ledgers and structural
CAS coordinates.  It performs no filesystem operation, persistence, Product
Project binding, monotonic anchoring, receipt minting, or runtime promotion.
"""
from __future__ import annotations

import copy
from enum import Enum
import re
from types import MappingProxyType
from typing import Any, Mapping

from .montage_learning_durable_staging_readback import (
    NONAUTHORITATIVE_DURABLE_STAGING_READBACK_PROJECTION,
    READBACK_DOMAIN,
    RECORD_TYPE as READBACK_RECORD_TYPE,
    SCHEMA_VERSION as READBACK_SCHEMA_VERSION,
    TASK_OWNER as READBACK_TASK_OWNER,
    MontageLearningDurableStagingReadback,
)
from .montage_learning_bridge_contracts import EXACT_CONTRACT_PROFILE
from .montage_learning_canonical_preflight import (
    derive_canonical_evidence_id,
    derive_human_binding_sha256,
)
from .montage_learning_receipt_contracts import (
    derive_montage_learning_idempotency_key_sha256,
)
from .serialization import canonical_json_bytes, sha256_bytes


SCHEMA_VERSION = "1.0.0"
SCHEMA_ID = (
    "https://baisound.dev/schemas/"
    "montage-learning-canonical-promotion-ledger-candidate.schema.json"
)
TASK_OWNER = "TASK-058"
CONTRACT_STATE = "SOURCE_REVALIDATION_REQUIRED"
CANONICAL_STATE = "NOT_MINTED"
_KEY_DOMAIN = b"TASK058_MONTAGE_LEARNING_CANONICAL_LEDGER_KEY_P1CC_V1\0"
_ENTRY_DOMAIN = b"TASK058_MONTAGE_LEARNING_CANONICAL_LEDGER_ENTRY_P1CC_V1\0"
_CHAIN_DOMAIN = b"TASK058_MONTAGE_LEARNING_CANONICAL_LEDGER_CHAIN_P1CC_V1\0"
_LEDGER_DOMAIN = b"TASK058_MONTAGE_LEARNING_CANONICAL_LEDGER_P1CC_V1\0"
_CAS_DOMAIN = b"TASK058_MONTAGE_LEARNING_CANONICAL_LEDGER_CAS_P1CC_V1\0"
_EVALUATION_DOMAIN = b"TASK058_MONTAGE_LEARNING_CANONICAL_LEDGER_EVAL_P1CC_V1\0"
EMPTY_CHAIN_SHA256 = sha256_bytes(_CHAIN_DOMAIN + canonical_json_bytes([]))
_TOKEN = object()
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_MAX_ENTRIES = 4096
_MAX_JSON_NODES = (_MAX_ENTRIES + 1) * 64 + 1024
_PLATFORM_SECURITY_MODELS = frozenset({
    "WINDOWS_PINNED_HANDLE_READ_V1",
    "POSIX_OPENAT_NOFOLLOW_READ_V1",
})


class AppendDecision(str, Enum):
    APPEND_CANDIDATE = "APPEND_CANDIDATE"
    DUPLICATE_CANDIDATE = "DUPLICATE_CANDIDATE"
    ID_COLLISION_REJECTED = "ID_COLLISION_REJECTED"
    STALE_CAS_REJECTED = "STALE_CAS_REJECTED"


_AUTHORITY_FLAGS = MappingProxyType({
    "raw_source_revalidated_under_canonical_transaction": False,
    "canonical_project_root_verified": False,
    "canonical_store_origin_verified": False,
    "canonical_store_commit_verified": False,
    "monotonic_anchor_verified": False,
    "rollback_detection_authority_created": False,
    "receipt_mint_authorized": False,
    "canonical_admission_authority_created": False,
    "automatic_learning_promotion_authorized": False,
})
_EFFECT_FLAGS = MappingProxyType({
    "filesystem_read": False,
    "filesystem_written": False,
    "project_manifest_written": False,
    "receipt_minted": False,
    "timeline_mutated": False,
    "resolve_written": False,
    "network_accessed": False,
    "provider_called": False,
    "process_started": False,
    "release_started": False,
    "deployment_started": False,
    "production_activated": False,
})


def _snapshot_exact_json(value: object, name: str) -> Any:
    seen: set[int] = set()
    node_count = 0

    def visit(item: object, path: str, depth: int) -> Any:
        nonlocal node_count
        node_count += 1
        if node_count > _MAX_JSON_NODES or depth > 32:
            raise ValueError(f"{name} exceeds the bounded JSON tree")
        if item is None or type(item) in {str, bool, int}:
            return item
        if isinstance(item, Mapping):
            if type(item) is not dict:
                raise ValueError(f"{path} must use an exact built-in dict")
            identity = id(item)
            if identity in seen:
                raise ValueError(f"{path} contains a container cycle")
            seen.add(identity)
            try:
                result: dict[str, Any] = {}
                for key, nested in item.items():
                    if type(key) is not str:
                        raise ValueError(f"{path} contains a non-string key")
                    result[key] = visit(nested, f"{path}.{key}", depth + 1)
                return result
            finally:
                seen.remove(identity)
        if isinstance(item, list):
            if type(item) is not list:
                raise ValueError(f"{path} must use an exact built-in list")
            identity = id(item)
            if identity in seen:
                raise ValueError(f"{path} contains a container cycle")
            seen.add(identity)
            try:
                return [
                    visit(nested, f"{path}[{index}]", depth + 1)
                    for index, nested in enumerate(item)
                ]
            finally:
                seen.remove(identity)
        raise ValueError(f"{path} contains an unsupported JSON value type")

    return visit(value, name, 0)


def _exact(value: object, fields: set[str], name: str) -> Mapping[str, Any]:
    snapshot = _snapshot_exact_json(value, name)
    if type(snapshot) is not dict or set(snapshot) != fields:
        raise ValueError(f"{name} fields are incomplete or unknown")
    return snapshot

def _identifier(value: object, name: str) -> str:
    if type(value) is not str or _ID_RE.fullmatch(value) is None:
        raise ValueError(f"{name} is invalid")
    return value


def _digest(value: object, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str or _DIGEST_RE.fullmatch(value) is None:
        raise ValueError(f"{name} is invalid")
    return value


def _integer(value: object, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value <= _MAX_ENTRIES:
        raise ValueError(f"{name} is outside the bounded range")
    return value


def _positive_integer(value: object, name: str) -> int:
    if type(value) is not int or not 1 <= value <= 2_147_483_647:
        raise ValueError(f"{name} must be a positive bounded integer")
    return value


def _freeze(value: Any) -> Any:
    if type(value) is dict:
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze(item) for item in value)
    if value is None or type(value) in {str, bool, int}:
        return value
    raise ValueError("validated JSON tree contains an unsupported value type")

def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw(item) for item in value]
    return value


def _without(value: Mapping[str, Any], *fields: str) -> dict[str, Any]:
    omitted = set(fields)
    return {
        key: copy.deepcopy(item)
        for key, item in value.items()
        if key not in omitted
    }


def _domain_hash(domain: bytes, value: Mapping[str, Any]) -> str:
    return sha256_bytes(domain + canonical_json_bytes(value))


def _ledger_key(
    project_id: str, canonical_store_id: str, owner_scope_hash: str,
) -> str:
    return _domain_hash(_KEY_DOMAIN, {
        "project_id": project_id,
        "canonical_store_id": canonical_store_id,
        "owner_scope_hash": owner_scope_hash,
    })


def _false_maps(value: Mapping[str, Any], name: str) -> None:
    for field, expected in (
        ("authority_flags", _AUTHORITY_FLAGS),
        ("effect_flags", _EFFECT_FLAGS),
    ):
        supplied = value[field]
        if (
            type(supplied) is not dict
            or set(supplied) != set(expected)
            or any(supplied[key] is not False for key in expected)
        ):
            boundary = "authority" if field == "authority_flags" else "effect"
            raise ValueError(f"{name} {boundary} boundary is invalid")


class _SealedRecord:
    __slots__ = ("_data",)

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _TOKEN:
            raise TypeError(f"{type(self).__name__} must use a validated factory")
        object.__setattr__(self, "_data", data)

    def __setattr__(self, name: str, value: Any) -> None:
        del name, value
        raise AttributeError(f"{type(self).__name__} is immutable")

    def __reduce__(self) -> object:
        raise TypeError("serialize the validated dictionary, not the typed object")

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


_ENTRY_FIELDS = {
    "schema_version", "record_type", "task_owner", "project_id",
    "canonical_store_id", "owner_scope_hash", "ledger_key_sha256",
    "entry_revision", "parent_entry_sha256", "prior_chain_sha256",
    "source_record_id", "source_sha256", "proposal_sha256",
    "approved_plan_sha256", "idempotency_key_sha256", "staging_store_id",
    "staging_store_revision", "staging_entry_sha256", "staging_ledger_sha256",
    "staging_file_identity_sha256", "staging_readback_sha256",
    "staging_platform_security_model",
    "canonical_evidence_id", "canonical_evidence_sha256",
    "human_binding_sha256", "negative_feedback_preserved", "candidate_state",
    "canonical_state", "authority_flags", "effect_flags", "entry_sha256",
    "chain_sha256",
}


class MontageLearningCanonicalLedgerEntryCandidate(_SealedRecord):
    RECORD_TYPE = "MONTAGE_LEARNING_CANONICAL_PROMOTION_LEDGER_ENTRY_CANDIDATE"

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any],
    ) -> "MontageLearningCanonicalLedgerEntryCandidate":
        body = _exact(value, _ENTRY_FIELDS, cls.RECORD_TYPE)
        if (
            body["schema_version"] != SCHEMA_VERSION
            or body["record_type"] != cls.RECORD_TYPE
            or body["task_owner"] != TASK_OWNER
        ):
            raise ValueError("entry identity/version is invalid")
        project_id = _identifier(body["project_id"], "project_id")
        store_id = _identifier(body["canonical_store_id"], "canonical_store_id")
        scope = _digest(body["owner_scope_hash"], "owner_scope_hash")
        expected_key = _ledger_key(project_id, store_id, scope)
        if body["ledger_key_sha256"] != expected_key:
            raise ValueError("entry ledger key mismatch")
        revision = _integer(body["entry_revision"], "entry_revision", minimum=1)
        parent = _digest(body["parent_entry_sha256"], "parent_entry_sha256", nullable=True)
        prior_chain = _digest(body["prior_chain_sha256"], "prior_chain_sha256")
        if (revision == 1) != (parent is None):
            raise ValueError("entry genesis/parent invariant is invalid")
        if revision == 1 and prior_chain != EMPTY_CHAIN_SHA256:
            raise ValueError("entry genesis chain is invalid")
        for field in (
            "source_record_id", "staging_store_id", "canonical_evidence_id",
        ):
            _identifier(body[field], field)
        for field in (
            "source_sha256", "proposal_sha256", "approved_plan_sha256",
            "idempotency_key_sha256", "staging_entry_sha256",
            "staging_ledger_sha256", "staging_file_identity_sha256",
            "staging_readback_sha256", "canonical_evidence_sha256",
            "human_binding_sha256",
        ):
            _digest(body[field], field)
        _positive_integer(body["staging_store_revision"], "staging_store_revision")
        if body["staging_platform_security_model"] not in _PLATFORM_SECURITY_MODELS:
            raise ValueError("staging platform security model is invalid")
        if type(body["negative_feedback_preserved"]) is not bool:
            raise ValueError("negative_feedback_preserved must be boolean")
        if body["candidate_state"] != CONTRACT_STATE or body["canonical_state"] != CANONICAL_STATE:
            raise ValueError("entry state cannot claim canonical minting")
        _false_maps(body, "entry")
        expected_entry = _domain_hash(
            _ENTRY_DOMAIN, _without(body, "entry_sha256", "chain_sha256")
        )
        if body["entry_sha256"] != expected_entry:
            raise ValueError("entry digest mismatch")
        expected_chain = _domain_hash(_CHAIN_DOMAIN, {
            "prior_chain_sha256": prior_chain,
            "entry_sha256": expected_entry,
        })
        if body["chain_sha256"] != expected_chain:
            raise ValueError("entry chain digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(body))), _token=_TOKEN)


_LEDGER_FIELDS = {
    "schema_version", "record_type", "task_owner", "project_id",
    "canonical_store_id", "owner_scope_hash", "ledger_key_sha256",
    "ledger_revision", "entry_count", "latest_entry_sha256", "chain_sha256",
    "entries", "contract_state", "canonical_state", "persistence_observed",
    "store_origin_authenticated", "project_manifest_binding_verified",
    "monotonic_anchor_present", "rollback_detection_authority_created",
    "consumer_revalidation_required", "authority_flags", "effect_flags",
    "ledger_sha256",
}


class MontageLearningCanonicalLedgerCandidate(_SealedRecord):
    RECORD_TYPE = "MONTAGE_LEARNING_CANONICAL_PROMOTION_LEDGER_CANDIDATE"

    @classmethod
    def empty(
        cls, *, project_id: str, canonical_store_id: str, owner_scope_hash: str,
    ) -> "MontageLearningCanonicalLedgerCandidate":
        project = _identifier(project_id, "project_id")
        store = _identifier(canonical_store_id, "canonical_store_id")
        scope = _digest(owner_scope_hash, "owner_scope_hash")
        body: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": cls.RECORD_TYPE,
            "task_owner": TASK_OWNER,
            "project_id": project,
            "canonical_store_id": store,
            "owner_scope_hash": scope,
            "ledger_key_sha256": _ledger_key(project, store, scope),
            "ledger_revision": 0,
            "entry_count": 0,
            "latest_entry_sha256": None,
            "chain_sha256": EMPTY_CHAIN_SHA256,
            "entries": [],
            "contract_state": CONTRACT_STATE,
            "canonical_state": CANONICAL_STATE,
            "persistence_observed": False,
            "store_origin_authenticated": False,
            "project_manifest_binding_verified": False,
            "monotonic_anchor_present": False,
            "rollback_detection_authority_created": False,
            "consumer_revalidation_required": True,
            "authority_flags": dict(_AUTHORITY_FLAGS),
            "effect_flags": dict(_EFFECT_FLAGS),
        }
        body["ledger_sha256"] = _domain_hash(_LEDGER_DOMAIN, body)
        return cls.from_dict(body)

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any],
    ) -> "MontageLearningCanonicalLedgerCandidate":
        body = _exact(value, _LEDGER_FIELDS, cls.RECORD_TYPE)
        if (
            body["schema_version"] != SCHEMA_VERSION
            or body["record_type"] != cls.RECORD_TYPE
            or body["task_owner"] != TASK_OWNER
        ):
            raise ValueError("ledger identity/version is invalid")
        project = _identifier(body["project_id"], "project_id")
        store = _identifier(body["canonical_store_id"], "canonical_store_id")
        scope = _digest(body["owner_scope_hash"], "owner_scope_hash")
        key_sha = _ledger_key(project, store, scope)
        if body["ledger_key_sha256"] != key_sha:
            raise ValueError("ledger key mismatch")
        revision = _integer(body["ledger_revision"], "ledger_revision")
        count = _integer(body["entry_count"], "entry_count")
        if revision != count:
            raise ValueError("ledger revision must equal entry count")
        if type(body["entries"]) is not list or len(body["entries"]) != count:
            raise ValueError("ledger entries/count mismatch")
        latest = _digest(body["latest_entry_sha256"], "latest_entry_sha256", nullable=True)
        chain = _digest(body["chain_sha256"], "chain_sha256")
        previous_entry: str | None = None
        previous_chain = EMPTY_CHAIN_SHA256
        identities: dict[str, set[str]] = {
            "idempotency_key_sha256": set(),
            "source_record_id": set(),
            "canonical_evidence_id": set(),
        }
        parsed_entries: list[dict[str, Any]] = []
        for expected_revision, raw_entry in enumerate(body["entries"], 1):
            entry = MontageLearningCanonicalLedgerEntryCandidate.from_dict(
                raw_entry
            ).to_dict()
            if (
                entry["project_id"] != project
                or entry["canonical_store_id"] != store
                or entry["owner_scope_hash"] != scope
                or entry["ledger_key_sha256"] != key_sha
                or entry["entry_revision"] != expected_revision
                or entry["parent_entry_sha256"] != previous_entry
                or entry["prior_chain_sha256"] != previous_chain
            ):
                raise ValueError("ledger entry chain/scope mismatch")
            for field, seen in identities.items():
                identity = entry[field]
                if identity in seen:
                    raise ValueError(f"ledger contains duplicate {field}")
                seen.add(identity)
            previous_entry = entry["entry_sha256"]
            previous_chain = entry["chain_sha256"]
            parsed_entries.append(entry)
        if count == 0:
            if latest is not None or chain != EMPTY_CHAIN_SHA256:
                raise ValueError("empty ledger sentinel mismatch")
        elif latest != previous_entry or chain != previous_chain:
            raise ValueError("ledger latest/chain mismatch")
        if body["contract_state"] != CONTRACT_STATE or body["canonical_state"] != CANONICAL_STATE:
            raise ValueError("ledger state cannot claim canonical minting")
        for field in (
            "persistence_observed", "store_origin_authenticated",
            "project_manifest_binding_verified", "monotonic_anchor_present",
            "rollback_detection_authority_created",
        ):
            if body[field] is not False:
                raise ValueError(f"{field} must remain false")
        if body["consumer_revalidation_required"] is not True:
            raise ValueError("consumer revalidation must remain required")
        _false_maps(body, "ledger")
        expected_hash = _domain_hash(_LEDGER_DOMAIN, _without(body, "ledger_sha256"))
        if body["ledger_sha256"] != expected_hash:
            raise ValueError("ledger digest mismatch")
        normalized = copy.deepcopy(dict(body))
        normalized["entries"] = parsed_entries
        return cls(_freeze(normalized), _token=_TOKEN)


_CAS_FIELDS = {
    "schema_version", "record_type", "task_owner", "ledger_key_sha256",
    "expected_ledger_revision", "expected_latest_entry_sha256",
    "expected_chain_sha256", "expected_ledger_sha256",
    "expectation_is_authority", "expectation_sha256",
}


class MontageLearningCanonicalLedgerCasExpectation(_SealedRecord):
    RECORD_TYPE = "MONTAGE_LEARNING_CANONICAL_PROMOTION_LEDGER_CAS_EXPECTATION"

    @classmethod
    def for_ledger(
        cls, ledger: MontageLearningCanonicalLedgerCandidate,
    ) -> "MontageLearningCanonicalLedgerCasExpectation":
        parsed = _ledger(ledger).to_dict()
        body: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": cls.RECORD_TYPE,
            "task_owner": TASK_OWNER,
            "ledger_key_sha256": parsed["ledger_key_sha256"],
            "expected_ledger_revision": parsed["ledger_revision"],
            "expected_latest_entry_sha256": parsed["latest_entry_sha256"],
            "expected_chain_sha256": parsed["chain_sha256"],
            "expected_ledger_sha256": parsed["ledger_sha256"],
            "expectation_is_authority": False,
        }
        body["expectation_sha256"] = _domain_hash(_CAS_DOMAIN, body)
        return cls.from_dict(body)

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any],
    ) -> "MontageLearningCanonicalLedgerCasExpectation":
        body = _exact(value, _CAS_FIELDS, cls.RECORD_TYPE)
        if (
            body["schema_version"] != SCHEMA_VERSION
            or body["record_type"] != cls.RECORD_TYPE
            or body["task_owner"] != TASK_OWNER
        ):
            raise ValueError("CAS identity/version is invalid")
        for field in (
            "ledger_key_sha256", "expected_chain_sha256", "expected_ledger_sha256",
        ):
            _digest(body[field], field)
        revision = _integer(body["expected_ledger_revision"], "expected_ledger_revision")
        latest = _digest(
            body["expected_latest_entry_sha256"],
            "expected_latest_entry_sha256",
            nullable=True,
        )
        if (revision == 0) != (latest is None):
            raise ValueError("CAS latest/revision sentinel mismatch")
        if body["expectation_is_authority"] is not False:
            raise ValueError("CAS expectation cannot be authority")
        expected_hash = _domain_hash(_CAS_DOMAIN, _without(body, "expectation_sha256"))
        if body["expectation_sha256"] != expected_hash:
            raise ValueError("CAS expectation digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(body))), _token=_TOKEN)


_EVALUATION_FIELDS = {
    "schema_version", "record_type", "task_owner", "decision", "reason_codes",
    "ledger_key_sha256", "observed_ledger_revision",
    "observed_latest_entry_sha256", "observed_chain_sha256",
    "observed_ledger_sha256", "incoming_source_record_id",
    "incoming_idempotency_key_sha256", "incoming_canonical_evidence_id",
    "incoming_readback_sha256", "expectation_sha256",
    "existing_entry_sha256", "proposed_ledger", "contract_state",
    "canonical_state", "authority_flags", "effect_flags", "evaluation_sha256",
}


class MontageLearningCanonicalAppendEvaluation(_SealedRecord):
    RECORD_TYPE = "MONTAGE_LEARNING_CANONICAL_PROMOTION_APPEND_EVALUATION"

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any],
    ) -> "MontageLearningCanonicalAppendEvaluation":
        body = _exact(value, _EVALUATION_FIELDS, cls.RECORD_TYPE)
        if (
            body["schema_version"] != SCHEMA_VERSION
            or body["record_type"] != cls.RECORD_TYPE
            or body["task_owner"] != TASK_OWNER
        ):
            raise ValueError("evaluation identity/version is invalid")
        try:
            decision = AppendDecision(body["decision"])
        except (TypeError, ValueError) as exc:
            raise ValueError("evaluation decision is invalid") from exc
        if type(body["reason_codes"]) is not list or body["reason_codes"] != [decision.value]:
            raise ValueError("evaluation reasons are not canonical")
        _digest(body["ledger_key_sha256"], "ledger_key_sha256")
        revision = _integer(body["observed_ledger_revision"], "observed_ledger_revision")
        latest = _digest(
            body["observed_latest_entry_sha256"],
            "observed_latest_entry_sha256",
            nullable=True,
        )
        if (revision == 0) != (latest is None):
            raise ValueError("evaluation latest/revision sentinel mismatch")
        for field in (
            "observed_chain_sha256", "observed_ledger_sha256",
            "incoming_idempotency_key_sha256", "incoming_readback_sha256",
            "expectation_sha256",
        ):
            _digest(body[field], field)
        _identifier(body["incoming_source_record_id"], "incoming_source_record_id")
        _identifier(body["incoming_canonical_evidence_id"], "incoming_canonical_evidence_id")
        existing = _digest(body["existing_entry_sha256"], "existing_entry_sha256", nullable=True)
        proposed = body["proposed_ledger"]
        if decision is AppendDecision.APPEND_CANDIDATE:
            if existing is not None or type(proposed) is not dict:
                raise ValueError("append evaluation result shape is invalid")
            parsed_ledger = MontageLearningCanonicalLedgerCandidate.from_dict(proposed).to_dict()
            if parsed_ledger["ledger_revision"] != revision + 1:
                raise ValueError("proposed ledger revision is invalid")
            if parsed_ledger["ledger_key_sha256"] != body["ledger_key_sha256"]:
                raise ValueError("proposed ledger key is invalid")
            prior_body = _without(parsed_ledger, "ledger_sha256")
            prior_body["entries"] = prior_body["entries"][:-1]
            prior_body["ledger_revision"] = revision
            prior_body["entry_count"] = revision
            prior_body["latest_entry_sha256"] = body["observed_latest_entry_sha256"]
            prior_body["chain_sha256"] = body["observed_chain_sha256"]
            if (
                _domain_hash(_LEDGER_DOMAIN, prior_body)
                != body["observed_ledger_sha256"]
            ):
                raise ValueError("proposed ledger prior state is invalid")
            latest_entry = parsed_ledger["entries"][-1]
            if (
                latest_entry["parent_entry_sha256"]
                != body["observed_latest_entry_sha256"]
                or latest_entry["prior_chain_sha256"]
                != body["observed_chain_sha256"]
                or latest_entry["source_record_id"]
                != body["incoming_source_record_id"]
                or latest_entry["idempotency_key_sha256"]
                != body["incoming_idempotency_key_sha256"]
                or latest_entry["canonical_evidence_id"]
                != body["incoming_canonical_evidence_id"]
                or latest_entry["staging_readback_sha256"]
                != body["incoming_readback_sha256"]
            ):
                raise ValueError("proposed ledger does not bind evaluation coordinates")
            proposed = parsed_ledger
        else:
            if proposed is not None:
                raise ValueError("non-append evaluation cannot propose a ledger")
            if decision in {
                AppendDecision.DUPLICATE_CANDIDATE,
                AppendDecision.ID_COLLISION_REJECTED,
            } and existing is None:
                raise ValueError("duplicate/collision requires existing entry")
            if decision is AppendDecision.STALE_CAS_REJECTED and existing is not None:
                raise ValueError("stale CAS cannot classify an entry")
        if body["contract_state"] != CONTRACT_STATE or body["canonical_state"] != CANONICAL_STATE:
            raise ValueError("evaluation state cannot claim canonical minting")
        _false_maps(body, "evaluation")
        expected_hash = _domain_hash(
            _EVALUATION_DOMAIN, _without(body, "evaluation_sha256")
        )
        if body["evaluation_sha256"] != expected_hash:
            raise ValueError("evaluation digest mismatch")
        normalized = copy.deepcopy(dict(body))
        normalized["proposed_ledger"] = proposed
        return cls(_freeze(normalized), _token=_TOKEN)


def _ledger(value: object) -> MontageLearningCanonicalLedgerCandidate:
    if type(value) is not MontageLearningCanonicalLedgerCandidate:
        raise TypeError("ledger must be an exact validated ledger candidate")
    return MontageLearningCanonicalLedgerCandidate.from_dict(value.to_dict())


def _expectation(value: object) -> MontageLearningCanonicalLedgerCasExpectation:
    if type(value) is not MontageLearningCanonicalLedgerCasExpectation:
        raise TypeError("expectation must be an exact validated CAS expectation")
    return MontageLearningCanonicalLedgerCasExpectation.from_dict(value.to_dict())


_READBACK_FIELDS = {
    "schema_version", "record_type", "task_owner", "source_contract_profile",
    "project_id", "store_id", "store_revision", "ledger_sha256",
    "staging_file_identity_sha256", "platform_security_model", "source_record_id",
    "source_sha256", "owner_scope_hash", "proposal_sha256",
    "approved_plan_sha256", "idempotency_key_sha256", "staging_entry_sha256",
    "canonical_evidence_id", "canonical_evidence_sha256", "human_binding_sha256",
    "admission_state", "projection_structure_valid", "raw_delivery_recompiled",
    "handle_bound_file_read_verified", "staging_membership_verified",
    "staging_store_path_identity_verified", "staging_store_origin_verified",
    "project_root_canonical_ownership_verified", "source_lineage_origin_verified",
    "human_binding_origin_verified",
    "hostile_ancestor_namespace_race_protection_verified",
    "point_in_time_readback_only", "post_return_state_guaranteed", "do_not_learn",
    "negative_feedback_preserved", "monotonic_project_anchor_verified",
    "rollback_detection_authority_created", "canonical_store_written",
    "canonical_store_commit_sha256", "receipt_minted",
    "canonical_admission_authority_created",
    "automatic_learning_promotion_authorized", "timeline_mutation_authorized",
    "resolve_write_authorized", "external_effect_authorized", "readback_sha256",
}


def _readback(value: object) -> dict[str, Any]:
    if type(value) is not MontageLearningDurableStagingReadback:
        raise TypeError("readback must be an exact in-process P1C-B result")
    body = dict(_exact(value.to_dict(), _READBACK_FIELDS, "P1C-B readback"))
    if (
        body["schema_version"] != READBACK_SCHEMA_VERSION
        or body["record_type"] != READBACK_RECORD_TYPE
        or body["task_owner"] != READBACK_TASK_OWNER
        or body["source_contract_profile"] != EXACT_CONTRACT_PROFILE
        or body["admission_state"]
        != NONAUTHORITATIVE_DURABLE_STAGING_READBACK_PROJECTION
    ):
        raise ValueError("P1C-B readback identity/version is invalid")
    for field in (
        "project_id", "store_id", "source_record_id", "canonical_evidence_id",
    ):
        _identifier(body[field], field)
    for field in (
        "ledger_sha256", "staging_file_identity_sha256", "source_sha256",
        "owner_scope_hash", "proposal_sha256", "approved_plan_sha256",
        "idempotency_key_sha256", "staging_entry_sha256",
        "canonical_evidence_sha256", "human_binding_sha256", "readback_sha256",
    ):
        _digest(body[field], field)
    _positive_integer(body["store_revision"], "store_revision")
    if body["platform_security_model"] not in _PLATFORM_SECURITY_MODELS:
        raise ValueError("P1C-B platform security model is invalid")
    true_fields = (
        "projection_structure_valid", "raw_delivery_recompiled",
        "handle_bound_file_read_verified", "staging_membership_verified",
        "staging_store_path_identity_verified", "point_in_time_readback_only",
    )
    false_fields = (
        "staging_store_origin_verified", "project_root_canonical_ownership_verified",
        "source_lineage_origin_verified", "human_binding_origin_verified",
        "hostile_ancestor_namespace_race_protection_verified",
        "post_return_state_guaranteed", "do_not_learn",
        "monotonic_project_anchor_verified", "rollback_detection_authority_created",
        "canonical_store_written", "receipt_minted",
        "canonical_admission_authority_created",
        "automatic_learning_promotion_authorized", "timeline_mutation_authorized",
        "resolve_write_authorized", "external_effect_authorized",
    )
    if any(body[field] is not True for field in true_fields):
        raise ValueError("P1C-B readback positive invariants are invalid")
    if any(body[field] is not False for field in false_fields):
        raise ValueError("P1C-B readback authority boundary is invalid")
    if type(body["negative_feedback_preserved"]) is not bool:
        raise ValueError("P1C-B negative feedback marker is invalid")
    if body["canonical_store_commit_sha256"] is not None:
        raise ValueError("P1C-B cannot contain a canonical store commit")
    expected_idempotency = derive_montage_learning_idempotency_key_sha256(
        source_contract_profile=EXACT_CONTRACT_PROFILE,
        source_record_id=body["source_record_id"],
        source_sha256=body["source_sha256"],
        owner_scope_hash=body["owner_scope_hash"],
    )
    expected_evidence_id = derive_canonical_evidence_id(body["source_sha256"])
    expected_human_binding = derive_human_binding_sha256(
        project_id=body["project_id"],
        source_record_id=body["source_record_id"],
        owner_scope_hash=body["owner_scope_hash"],
        proposal_sha256=body["proposal_sha256"],
        approved_plan_sha256=body["approved_plan_sha256"],
        evidence_sha256=body["source_sha256"],
    )
    if (
        body["idempotency_key_sha256"] != expected_idempotency
        or body["canonical_evidence_id"] != expected_evidence_id
        or body["canonical_evidence_sha256"] != body["source_sha256"]
        or body["human_binding_sha256"] != expected_human_binding
    ):
        raise ValueError("P1C-B derived coordinates are inconsistent")
    unsigned = _without(body, "readback_sha256")
    if body["readback_sha256"] != sha256_bytes(
        READBACK_DOMAIN + canonical_json_bytes(unsigned)
    ):
        raise ValueError("P1C-B readback digest mismatch")
    return body


def _build_entry(
    ledger: dict[str, Any], readback: dict[str, Any],
) -> MontageLearningCanonicalLedgerEntryCandidate:
    revision = ledger["ledger_revision"] + 1
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": MontageLearningCanonicalLedgerEntryCandidate.RECORD_TYPE,
        "task_owner": TASK_OWNER,
        "project_id": ledger["project_id"],
        "canonical_store_id": ledger["canonical_store_id"],
        "owner_scope_hash": ledger["owner_scope_hash"],
        "ledger_key_sha256": ledger["ledger_key_sha256"],
        "entry_revision": revision,
        "parent_entry_sha256": ledger["latest_entry_sha256"],
        "prior_chain_sha256": ledger["chain_sha256"],
        "source_record_id": readback["source_record_id"],
        "source_sha256": readback["source_sha256"],
        "proposal_sha256": readback["proposal_sha256"],
        "approved_plan_sha256": readback["approved_plan_sha256"],
        "idempotency_key_sha256": readback["idempotency_key_sha256"],
        "staging_store_id": readback["store_id"],
        "staging_store_revision": readback["store_revision"],
        "staging_entry_sha256": readback["staging_entry_sha256"],
        "staging_ledger_sha256": readback["ledger_sha256"],
        "staging_file_identity_sha256": readback["staging_file_identity_sha256"],
        "staging_readback_sha256": readback["readback_sha256"],
        "staging_platform_security_model": readback["platform_security_model"],
        "canonical_evidence_id": readback["canonical_evidence_id"],
        "canonical_evidence_sha256": readback["canonical_evidence_sha256"],
        "human_binding_sha256": readback["human_binding_sha256"],
        "negative_feedback_preserved": readback["negative_feedback_preserved"],
        "candidate_state": CONTRACT_STATE,
        "canonical_state": CANONICAL_STATE,
        "authority_flags": dict(_AUTHORITY_FLAGS),
        "effect_flags": dict(_EFFECT_FLAGS),
    }
    body["entry_sha256"] = _domain_hash(_ENTRY_DOMAIN, body)
    body["chain_sha256"] = _domain_hash(_CHAIN_DOMAIN, {
        "prior_chain_sha256": body["prior_chain_sha256"],
        "entry_sha256": body["entry_sha256"],
    })
    return MontageLearningCanonicalLedgerEntryCandidate.from_dict(body)


def _append_ledger(
    ledger: dict[str, Any], entry: MontageLearningCanonicalLedgerEntryCandidate,
) -> MontageLearningCanonicalLedgerCandidate:
    entry_body = entry.to_dict()
    body = _without(ledger, "ledger_sha256")
    body["entries"] = [*body["entries"], entry_body]
    body["ledger_revision"] = entry_body["entry_revision"]
    body["entry_count"] = len(body["entries"])
    body["latest_entry_sha256"] = entry_body["entry_sha256"]
    body["chain_sha256"] = entry_body["chain_sha256"]
    body["ledger_sha256"] = _domain_hash(_LEDGER_DOMAIN, body)
    return MontageLearningCanonicalLedgerCandidate.from_dict(body)


def _evaluation(
    *, decision: AppendDecision, ledger: dict[str, Any], readback: dict[str, Any],
    expectation: dict[str, Any], existing_entry_sha256: str | None,
    proposed_ledger: MontageLearningCanonicalLedgerCandidate | None,
) -> MontageLearningCanonicalAppendEvaluation:
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": MontageLearningCanonicalAppendEvaluation.RECORD_TYPE,
        "task_owner": TASK_OWNER,
        "decision": decision.value,
        "reason_codes": [decision.value],
        "ledger_key_sha256": ledger["ledger_key_sha256"],
        "observed_ledger_revision": ledger["ledger_revision"],
        "observed_latest_entry_sha256": ledger["latest_entry_sha256"],
        "observed_chain_sha256": ledger["chain_sha256"],
        "observed_ledger_sha256": ledger["ledger_sha256"],
        "incoming_source_record_id": readback["source_record_id"],
        "incoming_idempotency_key_sha256": readback["idempotency_key_sha256"],
        "incoming_canonical_evidence_id": readback["canonical_evidence_id"],
        "incoming_readback_sha256": readback["readback_sha256"],
        "expectation_sha256": expectation["expectation_sha256"],
        "existing_entry_sha256": existing_entry_sha256,
        "proposed_ledger": None if proposed_ledger is None else proposed_ledger.to_dict(),
        "contract_state": CONTRACT_STATE,
        "canonical_state": CANONICAL_STATE,
        "authority_flags": dict(_AUTHORITY_FLAGS),
        "effect_flags": dict(_EFFECT_FLAGS),
    }
    body["evaluation_sha256"] = _domain_hash(_EVALUATION_DOMAIN, body)
    return MontageLearningCanonicalAppendEvaluation.from_dict(body)


_EXACT_COORDINATE_FIELDS = (
    "source_record_id", "source_sha256", "proposal_sha256",
    "approved_plan_sha256", "idempotency_key_sha256", "staging_store_id",
    "staging_store_revision", "staging_entry_sha256", "staging_ledger_sha256",
    "staging_file_identity_sha256", "staging_readback_sha256",
    "staging_platform_security_model",
    "canonical_evidence_id", "canonical_evidence_sha256", "human_binding_sha256",
    "negative_feedback_preserved",
)


def evaluate_montage_learning_canonical_append(
    ledger: MontageLearningCanonicalLedgerCandidate,
    expectation: MontageLearningCanonicalLedgerCasExpectation,
    readback: MontageLearningDurableStagingReadback,
) -> MontageLearningCanonicalAppendEvaluation:
    """Evaluate one structural append without performing a mutable side effect."""

    parsed_ledger = _ledger(ledger).to_dict()
    parsed_expectation = _expectation(expectation).to_dict()
    parsed_readback = _readback(readback)
    cas_matches = (
        parsed_expectation["ledger_key_sha256"] == parsed_ledger["ledger_key_sha256"]
        and parsed_expectation["expected_ledger_revision"] == parsed_ledger["ledger_revision"]
        and parsed_expectation["expected_latest_entry_sha256"] == parsed_ledger["latest_entry_sha256"]
        and parsed_expectation["expected_chain_sha256"] == parsed_ledger["chain_sha256"]
        and parsed_expectation["expected_ledger_sha256"] == parsed_ledger["ledger_sha256"]
    )
    if not cas_matches or (
        parsed_readback["project_id"] != parsed_ledger["project_id"]
        or parsed_readback["owner_scope_hash"] != parsed_ledger["owner_scope_hash"]
    ):
        return _evaluation(
            decision=AppendDecision.STALE_CAS_REJECTED,
            ledger=parsed_ledger,
            readback=parsed_readback,
            expectation=parsed_expectation,
            existing_entry_sha256=None,
            proposed_ledger=None,
        )
    incoming = {
        "source_record_id": parsed_readback["source_record_id"],
        "source_sha256": parsed_readback["source_sha256"],
        "proposal_sha256": parsed_readback["proposal_sha256"],
        "approved_plan_sha256": parsed_readback["approved_plan_sha256"],
        "idempotency_key_sha256": parsed_readback["idempotency_key_sha256"],
        "staging_store_id": parsed_readback["store_id"],
        "staging_store_revision": parsed_readback["store_revision"],
        "staging_entry_sha256": parsed_readback["staging_entry_sha256"],
        "staging_ledger_sha256": parsed_readback["ledger_sha256"],
        "staging_file_identity_sha256": parsed_readback["staging_file_identity_sha256"],
        "staging_readback_sha256": parsed_readback["readback_sha256"],
        "staging_platform_security_model": parsed_readback["platform_security_model"],
        "canonical_evidence_id": parsed_readback["canonical_evidence_id"],
        "canonical_evidence_sha256": parsed_readback["canonical_evidence_sha256"],
        "human_binding_sha256": parsed_readback["human_binding_sha256"],
        "negative_feedback_preserved": parsed_readback["negative_feedback_preserved"],
    }
    identity_fields = (
        "idempotency_key_sha256", "source_record_id", "canonical_evidence_id",
    )
    for existing in parsed_ledger["entries"]:
        if all(existing[field] == incoming[field] for field in _EXACT_COORDINATE_FIELDS):
            return _evaluation(
                decision=AppendDecision.DUPLICATE_CANDIDATE,
                ledger=parsed_ledger,
                readback=parsed_readback,
                expectation=parsed_expectation,
                existing_entry_sha256=existing["entry_sha256"],
                proposed_ledger=None,
            )
        if any(existing[field] == incoming[field] for field in identity_fields):
            return _evaluation(
                decision=AppendDecision.ID_COLLISION_REJECTED,
                ledger=parsed_ledger,
                readback=parsed_readback,
                expectation=parsed_expectation,
                existing_entry_sha256=existing["entry_sha256"],
                proposed_ledger=None,
            )
    if parsed_ledger["entry_count"] >= _MAX_ENTRIES:
        raise ValueError("canonical ledger candidate reached its bounded entry limit")
    proposed = _append_ledger(parsed_ledger, _build_entry(parsed_ledger, parsed_readback))
    return _evaluation(
        decision=AppendDecision.APPEND_CANDIDATE,
        ledger=parsed_ledger,
        readback=parsed_readback,
        expectation=parsed_expectation,
        existing_entry_sha256=None,
        proposed_ledger=proposed,
    )


__all__ = [
    "CANONICAL_STATE",
    "CONTRACT_STATE",
    "EMPTY_CHAIN_SHA256",
    "SCHEMA_ID",
    "SCHEMA_VERSION",
    "AppendDecision",
    "MontageLearningCanonicalAppendEvaluation",
    "MontageLearningCanonicalLedgerCandidate",
    "MontageLearningCanonicalLedgerCasExpectation",
    "MontageLearningCanonicalLedgerEntryCandidate",
    "evaluate_montage_learning_canonical_append",
]
