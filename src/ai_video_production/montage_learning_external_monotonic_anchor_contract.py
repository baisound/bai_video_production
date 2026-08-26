"""Pure TASK-058 P1C-D external monotonic anchor candidate contract.

The records in this module are structural candidates only.  They do not read or
write an external anchor, authenticate its origin, persist a canonical ledger,
create rollback authority, or mint a public receipt.
"""
from __future__ import annotations

import copy
from enum import Enum
import re
from types import MappingProxyType
from typing import Any, Mapping

from .montage_learning_canonical_promotion_ledger_contract import (
    MontageLearningCanonicalLedgerCandidate,
)
from .serialization import canonical_json_bytes, sha256_bytes


SCHEMA_VERSION = "1.0.0"
SCHEMA_ID = (
    "https://baisound.dev/schemas/"
    "montage-learning-external-monotonic-anchor-candidate.schema.json"
)
TASK_OWNER = "TASK-058"
CONTRACT_STATE = "EXTERNAL_ANCHOR_REVALIDATION_REQUIRED"
ANCHOR_STATE = "NOT_ESTABLISHED"
_ANCHOR_DOMAIN = b"TASK058_MONTAGE_LEARNING_EXTERNAL_ANCHOR_P1CD_V1\0"
_EXPECTATION_DOMAIN = b"TASK058_MONTAGE_LEARNING_EXTERNAL_ANCHOR_CAS_P1CD_V1\0"
_EVALUATION_DOMAIN = b"TASK058_MONTAGE_LEARNING_EXTERNAL_ANCHOR_EVAL_P1CD_V1\0"
_TOKEN = object()
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_MAX_REVISION = 4096
_MAX_JSON_NODES = 1024


class AnchorDecision(str, Enum):
    BOOTSTRAP_CANDIDATE = "BOOTSTRAP_CANDIDATE"
    ADVANCE_CANDIDATE = "ADVANCE_CANDIDATE"
    UNCHANGED_CANDIDATE = "UNCHANGED_CANDIDATE"
    ROLLBACK_REJECTED = "ROLLBACK_REJECTED"
    FORK_REJECTED = "FORK_REJECTED"
    SCOPE_MISMATCH_REJECTED = "SCOPE_MISMATCH_REJECTED"
    STALE_ANCHOR_REJECTED = "STALE_ANCHOR_REJECTED"


_AUTHORITY_FLAGS = MappingProxyType({
    "raw_source_revalidated_under_canonical_transaction": False,
    "canonical_project_transaction_held": False,
    "canonical_store_commit_verified": False,
    "external_monotonic_anchor_verified": False,
    "external_anchor_origin_authenticated": False,
    "rollback_detection_authority_created": False,
    "public_v2_receipt_mint_authorized": False,
    "canonical_admission_authority_created": False,
    "automatic_learning_promotion_authorized": False,
})
_EFFECT_FLAGS = MappingProxyType({
    "filesystem_read": False,
    "filesystem_written": False,
    "canonical_ledger_written": False,
    "external_anchor_read": False,
    "external_anchor_written": False,
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
        if node_count > _MAX_JSON_NODES or depth > 16:
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


def _revision(value: object, name: str, *, nullable: bool = False) -> int | None:
    if value is None and nullable:
        return None
    if type(value) is not int or not 0 <= value <= _MAX_REVISION:
        raise ValueError(f"{name} is outside the bounded range")
    return value


def _positive_revision(value: object, name: str) -> int:
    if type(value) is not int or not 1 <= value <= _MAX_REVISION:
        raise ValueError(f"{name} is outside the positive bounded range")
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
            raise TypeError("record construction is internal; use a validated factory")
        object.__setattr__(self, "_data", data)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("record is immutable")

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


def _ledger(value: object) -> dict[str, Any]:
    if type(value) is not MontageLearningCanonicalLedgerCandidate:
        raise TypeError("ledger must be an exact validated P1C-C ledger candidate")
    return MontageLearningCanonicalLedgerCandidate.from_dict(value.to_dict()).to_dict()


def _ledger_coordinates(ledger: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "project_id": ledger["project_id"],
        "canonical_store_id": ledger["canonical_store_id"],
        "owner_scope_hash": ledger["owner_scope_hash"],
        "ledger_key_sha256": ledger["ledger_key_sha256"],
        "anchored_ledger_revision": ledger["ledger_revision"],
        "anchored_latest_entry_sha256": ledger["latest_entry_sha256"],
        "anchored_chain_sha256": ledger["chain_sha256"],
        "anchored_ledger_sha256": ledger["ledger_sha256"],
    }


_ANCHOR_FIELDS = {
    "schema_version", "record_type", "task_owner", "project_id",
    "canonical_store_id", "owner_scope_hash", "ledger_key_sha256",
    "anchor_revision", "anchored_ledger_revision",
    "anchored_latest_entry_sha256", "anchored_chain_sha256",
    "anchored_ledger_sha256", "previous_anchor_sha256",
    "contract_state", "anchor_state", "external_anchor_observed",
    "external_anchor_origin_authenticated", "canonical_store_commit_verified",
    "rollback_detection_authority_created", "consumer_revalidation_required",
    "authority_flags", "effect_flags", "anchor_sha256",
}


class MontageLearningExternalMonotonicAnchorCandidate(_SealedRecord):
    RECORD_TYPE = "MONTAGE_LEARNING_EXTERNAL_MONOTONIC_ANCHOR_CANDIDATE"

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any],
    ) -> "MontageLearningExternalMonotonicAnchorCandidate":
        body = _exact(value, _ANCHOR_FIELDS, cls.RECORD_TYPE)
        if (
            body["schema_version"] != SCHEMA_VERSION
            or body["record_type"] != cls.RECORD_TYPE
            or body["task_owner"] != TASK_OWNER
        ):
            raise ValueError("anchor candidate identity/version is invalid")
        _identifier(body["project_id"], "project_id")
        _identifier(body["canonical_store_id"], "canonical_store_id")
        for field in (
            "owner_scope_hash", "ledger_key_sha256", "anchored_chain_sha256",
            "anchored_ledger_sha256", "anchor_sha256",
        ):
            _digest(body[field], field)
        anchor_revision = _positive_revision(body["anchor_revision"], "anchor_revision")
        ledger_revision = _positive_revision(
            body["anchored_ledger_revision"], "anchored_ledger_revision"
        )
        latest = _digest(
            body["anchored_latest_entry_sha256"],
            "anchored_latest_entry_sha256",
        )
        previous = _digest(
            body["previous_anchor_sha256"], "previous_anchor_sha256", nullable=True
        )
        if (anchor_revision == 1) != (previous is None):
            raise ValueError("anchor predecessor/revision sentinel mismatch")
        if ledger_revision < anchor_revision:
            raise ValueError("anchor revision cannot exceed anchored ledger revision")
        if latest is None:
            raise ValueError("anchor candidate requires a non-empty ledger")
        if (
            body["contract_state"] != CONTRACT_STATE
            or body["anchor_state"] != ANCHOR_STATE
        ):
            raise ValueError("anchor candidate cannot claim establishment")
        for field in (
            "external_anchor_observed", "external_anchor_origin_authenticated",
            "canonical_store_commit_verified",
            "rollback_detection_authority_created",
        ):
            if body[field] is not False:
                raise ValueError(f"{field} must remain false")
        if body["consumer_revalidation_required"] is not True:
            raise ValueError("consumer revalidation must remain required")
        _false_maps(body, "anchor candidate")
        expected_hash = _domain_hash(_ANCHOR_DOMAIN, _without(body, "anchor_sha256"))
        if body["anchor_sha256"] != expected_hash:
            raise ValueError("anchor candidate digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(body))), _token=_TOKEN)


_EXPECTATION_FIELDS = {
    "schema_version", "record_type", "task_owner", "ledger_key_sha256",
    "expected_anchor_revision", "expected_anchor_sha256",
    "expected_anchored_ledger_revision", "expected_anchored_chain_sha256",
    "expected_anchored_ledger_sha256", "expectation_is_authority",
    "expectation_sha256",
}


class MontageLearningExternalMonotonicAnchorExpectation(_SealedRecord):
    RECORD_TYPE = "MONTAGE_LEARNING_EXTERNAL_MONOTONIC_ANCHOR_EXPECTATION"

    @classmethod
    def for_absent_anchor(
        cls, ledger: MontageLearningCanonicalLedgerCandidate,
    ) -> "MontageLearningExternalMonotonicAnchorExpectation":
        parsed = _ledger(ledger)
        body: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": cls.RECORD_TYPE,
            "task_owner": TASK_OWNER,
            "ledger_key_sha256": parsed["ledger_key_sha256"],
            "expected_anchor_revision": 0,
            "expected_anchor_sha256": None,
            "expected_anchored_ledger_revision": None,
            "expected_anchored_chain_sha256": None,
            "expected_anchored_ledger_sha256": None,
            "expectation_is_authority": False,
        }
        body["expectation_sha256"] = _domain_hash(_EXPECTATION_DOMAIN, body)
        return cls.from_dict(body)

    @classmethod
    def for_anchor(
        cls, anchor: MontageLearningExternalMonotonicAnchorCandidate,
    ) -> "MontageLearningExternalMonotonicAnchorExpectation":
        parsed = _anchor(anchor)
        body: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": cls.RECORD_TYPE,
            "task_owner": TASK_OWNER,
            "ledger_key_sha256": parsed["ledger_key_sha256"],
            "expected_anchor_revision": parsed["anchor_revision"],
            "expected_anchor_sha256": parsed["anchor_sha256"],
            "expected_anchored_ledger_revision": parsed["anchored_ledger_revision"],
            "expected_anchored_chain_sha256": parsed["anchored_chain_sha256"],
            "expected_anchored_ledger_sha256": parsed["anchored_ledger_sha256"],
            "expectation_is_authority": False,
        }
        body["expectation_sha256"] = _domain_hash(_EXPECTATION_DOMAIN, body)
        return cls.from_dict(body)

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any],
    ) -> "MontageLearningExternalMonotonicAnchorExpectation":
        body = _exact(value, _EXPECTATION_FIELDS, cls.RECORD_TYPE)
        if (
            body["schema_version"] != SCHEMA_VERSION
            or body["record_type"] != cls.RECORD_TYPE
            or body["task_owner"] != TASK_OWNER
        ):
            raise ValueError("anchor expectation identity/version is invalid")
        _digest(body["ledger_key_sha256"], "ledger_key_sha256")
        revision = _revision(body["expected_anchor_revision"], "expected_anchor_revision")
        anchor_sha = _digest(
            body["expected_anchor_sha256"], "expected_anchor_sha256", nullable=True
        )
        ledger_revision = _revision(
            body["expected_anchored_ledger_revision"],
            "expected_anchored_ledger_revision",
            nullable=True,
        )
        chain = _digest(
            body["expected_anchored_chain_sha256"],
            "expected_anchored_chain_sha256",
            nullable=True,
        )
        ledger_sha = _digest(
            body["expected_anchored_ledger_sha256"],
            "expected_anchored_ledger_sha256",
            nullable=True,
        )
        absent = revision == 0
        if absent != (anchor_sha is None):
            raise ValueError("anchor expectation revision/hash sentinel mismatch")
        nullable_coordinates = (ledger_revision, chain, ledger_sha)
        if absent and any(item is not None for item in nullable_coordinates):
            raise ValueError("anchor expectation ledger sentinel mismatch")
        if not absent and any(item is None for item in nullable_coordinates):
            raise ValueError("anchor expectation ledger sentinel mismatch")
        if not absent and ledger_revision < revision:
            raise ValueError("anchor expectation revision ordering is invalid")
        if body["expectation_is_authority"] is not False:
            raise ValueError("anchor expectation cannot be authority")
        expected_hash = _domain_hash(
            _EXPECTATION_DOMAIN, _without(body, "expectation_sha256")
        )
        if body["expectation_sha256"] != expected_hash:
            raise ValueError("anchor expectation digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(body))), _token=_TOKEN)


_EVALUATION_FIELDS = {
    "schema_version", "record_type", "task_owner", "decision", "reason_codes",
    "ledger_key_sha256", "observed_anchor_revision", "observed_anchor_sha256",
    "observed_ledger_revision", "observed_latest_entry_sha256",
    "observed_chain_sha256", "observed_ledger_sha256",
    "proposed_ledger_revision", "proposed_latest_entry_sha256",
    "proposed_chain_sha256", "proposed_ledger_sha256", "expectation_sha256",
    "existing_anchor_sha256", "proposed_anchor", "contract_state",
    "anchor_state", "authority_flags", "effect_flags", "evaluation_sha256",
}


class MontageLearningExternalMonotonicAnchorEvaluation(_SealedRecord):
    RECORD_TYPE = "MONTAGE_LEARNING_EXTERNAL_MONOTONIC_ANCHOR_EVALUATION"

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any],
    ) -> "MontageLearningExternalMonotonicAnchorEvaluation":
        body = _exact(value, _EVALUATION_FIELDS, cls.RECORD_TYPE)
        if (
            body["schema_version"] != SCHEMA_VERSION
            or body["record_type"] != cls.RECORD_TYPE
            or body["task_owner"] != TASK_OWNER
        ):
            raise ValueError("anchor evaluation identity/version is invalid")
        try:
            decision = AnchorDecision(body["decision"])
        except (TypeError, ValueError) as exc:
            raise ValueError("anchor evaluation decision is invalid") from exc
        if type(body["reason_codes"]) is not list or body["reason_codes"] != [decision.value]:
            raise ValueError("anchor evaluation reasons are not canonical")
        _digest(body["ledger_key_sha256"], "ledger_key_sha256")
        observed_anchor_revision = _revision(
            body["observed_anchor_revision"], "observed_anchor_revision"
        )
        observed_anchor_sha = _digest(
            body["observed_anchor_sha256"], "observed_anchor_sha256", nullable=True
        )
        observed_ledger_revision = _revision(
            body["observed_ledger_revision"], "observed_ledger_revision", nullable=True
        )
        observed_latest = _digest(
            body["observed_latest_entry_sha256"],
            "observed_latest_entry_sha256",
            nullable=True,
        )
        observed_chain = _digest(
            body["observed_chain_sha256"], "observed_chain_sha256", nullable=True
        )
        observed_ledger_sha = _digest(
            body["observed_ledger_sha256"], "observed_ledger_sha256", nullable=True
        )
        if (observed_anchor_revision == 0) != (observed_anchor_sha is None):
            raise ValueError("evaluation observed anchor sentinel mismatch")
        observed_absent = observed_anchor_revision == 0
        observed_coordinates = (
            observed_ledger_revision, observed_latest, observed_chain,
            observed_ledger_sha,
        )
        if observed_absent and any(
            item is not None for item in observed_coordinates
        ):
            raise ValueError("evaluation observed ledger sentinel mismatch")
        if not observed_absent and any(
            item is None for item in observed_coordinates
        ):
            raise ValueError("evaluation observed ledger sentinel mismatch")
        proposed_revision = _positive_revision(
            body["proposed_ledger_revision"], "proposed_ledger_revision"
        )
        for field in (
            "proposed_latest_entry_sha256", "proposed_chain_sha256",
            "proposed_ledger_sha256", "expectation_sha256",
        ):
            _digest(body[field], field)
        existing = _digest(
            body["existing_anchor_sha256"], "existing_anchor_sha256", nullable=True
        )
        proposed_anchor = body["proposed_anchor"]
        creates_candidate = decision in {
            AnchorDecision.BOOTSTRAP_CANDIDATE,
            AnchorDecision.ADVANCE_CANDIDATE,
        }
        if creates_candidate:
            if type(proposed_anchor) is not dict:
                raise ValueError("successful evaluation requires an anchor candidate")
            parsed_anchor = MontageLearningExternalMonotonicAnchorCandidate.from_dict(
                proposed_anchor
            ).to_dict()
            expected_anchor_revision = observed_anchor_revision + 1
            if (
                parsed_anchor["ledger_key_sha256"] != body["ledger_key_sha256"]
                or parsed_anchor["anchor_revision"] != expected_anchor_revision
                or parsed_anchor["anchored_ledger_revision"] != proposed_revision
                or parsed_anchor["anchored_latest_entry_sha256"]
                != body["proposed_latest_entry_sha256"]
                or parsed_anchor["anchored_chain_sha256"]
                != body["proposed_chain_sha256"]
                or parsed_anchor["anchored_ledger_sha256"]
                != body["proposed_ledger_sha256"]
                or parsed_anchor["previous_anchor_sha256"] != observed_anchor_sha
            ):
                raise ValueError("proposed anchor does not bind evaluation coordinates")
            if decision is AnchorDecision.BOOTSTRAP_CANDIDATE and not observed_absent:
                raise ValueError("bootstrap evaluation requires an absent anchor")
            if decision is AnchorDecision.ADVANCE_CANDIDATE and observed_absent:
                raise ValueError("advance evaluation requires an existing anchor")
            proposed_anchor = parsed_anchor
        elif proposed_anchor is not None:
            raise ValueError("non-success evaluation cannot propose an anchor")
        if decision is AnchorDecision.BOOTSTRAP_CANDIDATE and existing is not None:
            raise ValueError("bootstrap cannot report an existing anchor")
        if not observed_absent and existing != observed_anchor_sha:
            raise ValueError("evaluation existing anchor mismatch")
        if observed_absent and existing is not None:
            raise ValueError("absent evaluation cannot report an existing anchor")
        if decision is AnchorDecision.ADVANCE_CANDIDATE and (
            observed_ledger_revision is None
            or proposed_revision <= observed_ledger_revision
        ):
            raise ValueError("advance evaluation revision ordering is invalid")
        if decision is AnchorDecision.UNCHANGED_CANDIDATE and (
            observed_ledger_revision is None
            or proposed_revision != observed_ledger_revision
            or body["proposed_latest_entry_sha256"] != observed_latest
            or body["proposed_chain_sha256"] != observed_chain
            or body["proposed_ledger_sha256"] != observed_ledger_sha
        ):
            raise ValueError("unchanged evaluation coordinates are invalid")
        if decision is AnchorDecision.ROLLBACK_REJECTED and (
            observed_ledger_revision is None
            or proposed_revision >= observed_ledger_revision
        ):
            raise ValueError("rollback evaluation revision ordering is invalid")
        if decision is AnchorDecision.FORK_REJECTED and (
            observed_ledger_revision is None
            or proposed_revision < observed_ledger_revision
            or (
                proposed_revision == observed_ledger_revision
                and body["proposed_ledger_sha256"] == observed_ledger_sha
            )
        ):
            raise ValueError("fork evaluation coordinates are invalid")
        if body["contract_state"] != CONTRACT_STATE or body["anchor_state"] != ANCHOR_STATE:
            raise ValueError("evaluation cannot claim anchor establishment")
        _false_maps(body, "anchor evaluation")
        expected_hash = _domain_hash(
            _EVALUATION_DOMAIN, _without(body, "evaluation_sha256")
        )
        if body["evaluation_sha256"] != expected_hash:
            raise ValueError("anchor evaluation digest mismatch")
        normalized = copy.deepcopy(dict(body))
        normalized["proposed_anchor"] = proposed_anchor
        return cls(_freeze(normalized), _token=_TOKEN)


def _anchor(value: object) -> dict[str, Any]:
    if type(value) is not MontageLearningExternalMonotonicAnchorCandidate:
        raise TypeError("anchor must be an exact validated anchor candidate")
    return MontageLearningExternalMonotonicAnchorCandidate.from_dict(
        value.to_dict()
    ).to_dict()


def _expectation(value: object) -> dict[str, Any]:
    if type(value) is not MontageLearningExternalMonotonicAnchorExpectation:
        raise TypeError("expectation must be an exact validated anchor expectation")
    return MontageLearningExternalMonotonicAnchorExpectation.from_dict(
        value.to_dict()
    ).to_dict()


def _anchor_for_ledger(
    ledger: Mapping[str, Any],
    *,
    anchor_revision: int,
    previous_anchor_sha256: str | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": MontageLearningExternalMonotonicAnchorCandidate.RECORD_TYPE,
        "task_owner": TASK_OWNER,
        **_ledger_coordinates(ledger),
        "anchor_revision": anchor_revision,
        "previous_anchor_sha256": previous_anchor_sha256,
        "contract_state": CONTRACT_STATE,
        "anchor_state": ANCHOR_STATE,
        "external_anchor_observed": False,
        "external_anchor_origin_authenticated": False,
        "canonical_store_commit_verified": False,
        "rollback_detection_authority_created": False,
        "consumer_revalidation_required": True,
        "authority_flags": dict(_AUTHORITY_FLAGS),
        "effect_flags": dict(_EFFECT_FLAGS),
    }
    body["anchor_sha256"] = _domain_hash(_ANCHOR_DOMAIN, body)
    return MontageLearningExternalMonotonicAnchorCandidate.from_dict(body).to_dict()


def _evaluation(
    *,
    decision: AnchorDecision,
    proposed_ledger: Mapping[str, Any],
    expectation: Mapping[str, Any],
    current_anchor: Mapping[str, Any] | None,
    current_ledger: Mapping[str, Any] | None,
    proposed_anchor: Mapping[str, Any] | None,
) -> MontageLearningExternalMonotonicAnchorEvaluation:
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": MontageLearningExternalMonotonicAnchorEvaluation.RECORD_TYPE,
        "task_owner": TASK_OWNER,
        "decision": decision.value,
        "reason_codes": [decision.value],
        "ledger_key_sha256": proposed_ledger["ledger_key_sha256"],
        "observed_anchor_revision": (
            0 if current_anchor is None else current_anchor["anchor_revision"]
        ),
        "observed_anchor_sha256": (
            None if current_anchor is None else current_anchor["anchor_sha256"]
        ),
        "observed_ledger_revision": (
            None if current_ledger is None else current_ledger["ledger_revision"]
        ),
        "observed_latest_entry_sha256": (
            None if current_ledger is None else current_ledger["latest_entry_sha256"]
        ),
        "observed_chain_sha256": (
            None if current_ledger is None else current_ledger["chain_sha256"]
        ),
        "observed_ledger_sha256": (
            None if current_ledger is None else current_ledger["ledger_sha256"]
        ),
        "proposed_ledger_revision": proposed_ledger["ledger_revision"],
        "proposed_latest_entry_sha256": proposed_ledger["latest_entry_sha256"],
        "proposed_chain_sha256": proposed_ledger["chain_sha256"],
        "proposed_ledger_sha256": proposed_ledger["ledger_sha256"],
        "expectation_sha256": expectation["expectation_sha256"],
        "existing_anchor_sha256": (
            None if current_anchor is None else current_anchor["anchor_sha256"]
        ),
        "proposed_anchor": (
            None if proposed_anchor is None else copy.deepcopy(dict(proposed_anchor))
        ),
        "contract_state": CONTRACT_STATE,
        "anchor_state": ANCHOR_STATE,
        "authority_flags": dict(_AUTHORITY_FLAGS),
        "effect_flags": dict(_EFFECT_FLAGS),
    }
    body["evaluation_sha256"] = _domain_hash(_EVALUATION_DOMAIN, body)
    return MontageLearningExternalMonotonicAnchorEvaluation.from_dict(body)


def _expectation_matches(
    expectation: Mapping[str, Any], current_anchor: Mapping[str, Any] | None,
) -> bool:
    if current_anchor is None:
        return (
            expectation["expected_anchor_revision"] == 0
            and expectation["expected_anchor_sha256"] is None
            and expectation["expected_anchored_ledger_revision"] is None
            and expectation["expected_anchored_chain_sha256"] is None
            and expectation["expected_anchored_ledger_sha256"] is None
        )
    return (
        expectation["ledger_key_sha256"] == current_anchor["ledger_key_sha256"]
        and expectation["expected_anchor_revision"] == current_anchor["anchor_revision"]
        and expectation["expected_anchor_sha256"] == current_anchor["anchor_sha256"]
        and expectation["expected_anchored_ledger_revision"]
        == current_anchor["anchored_ledger_revision"]
        and expectation["expected_anchored_chain_sha256"]
        == current_anchor["anchored_chain_sha256"]
        and expectation["expected_anchored_ledger_sha256"]
        == current_anchor["anchored_ledger_sha256"]
    )


def _anchor_binds_ledger(
    anchor: Mapping[str, Any], ledger: Mapping[str, Any],
) -> bool:
    return (
        anchor["project_id"] == ledger["project_id"]
        and anchor["canonical_store_id"] == ledger["canonical_store_id"]
        and anchor["owner_scope_hash"] == ledger["owner_scope_hash"]
        and anchor["ledger_key_sha256"] == ledger["ledger_key_sha256"]
        and anchor["anchored_ledger_revision"] == ledger["ledger_revision"]
        and anchor["anchored_latest_entry_sha256"] == ledger["latest_entry_sha256"]
        and anchor["anchored_chain_sha256"] == ledger["chain_sha256"]
        and anchor["anchored_ledger_sha256"] == ledger["ledger_sha256"]
    )


def _same_scope(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return all(
        left[field] == right[field]
        for field in (
            "project_id", "canonical_store_id", "owner_scope_hash",
            "ledger_key_sha256",
        )
    )


def _is_exact_extension(
    current: Mapping[str, Any], proposed: Mapping[str, Any],
) -> bool:
    count = current["entry_count"]
    return (
        proposed["entry_count"] > count
        and proposed["entries"][:count] == current["entries"]
    )


def evaluate_montage_learning_external_monotonic_anchor(
    current_anchor: MontageLearningExternalMonotonicAnchorCandidate | None,
    expectation: MontageLearningExternalMonotonicAnchorExpectation,
    current_ledger: MontageLearningCanonicalLedgerCandidate | None,
    proposed_ledger: MontageLearningCanonicalLedgerCandidate,
) -> MontageLearningExternalMonotonicAnchorEvaluation:
    """Evaluate a structural anchor transition without reading or writing one."""

    parsed_expectation = _expectation(expectation)
    proposed = _ledger(proposed_ledger)
    if proposed["ledger_revision"] == 0:
        raise ValueError("an external anchor candidate requires a non-empty ledger")
    parsed_anchor = None if current_anchor is None else _anchor(current_anchor)
    parsed_current = None if current_ledger is None else _ledger(current_ledger)

    if (parsed_anchor is None) != (parsed_current is None):
        raise ValueError("current anchor and current ledger must be supplied together")
    if not _expectation_matches(parsed_expectation, parsed_anchor):
        return _evaluation(
            decision=AnchorDecision.STALE_ANCHOR_REJECTED,
            proposed_ledger=proposed,
            expectation=parsed_expectation,
            current_anchor=parsed_anchor,
            current_ledger=parsed_current,
            proposed_anchor=None,
        )
    if parsed_expectation["ledger_key_sha256"] != proposed["ledger_key_sha256"]:
        return _evaluation(
            decision=AnchorDecision.SCOPE_MISMATCH_REJECTED,
            proposed_ledger=proposed,
            expectation=parsed_expectation,
            current_anchor=parsed_anchor,
            current_ledger=parsed_current,
            proposed_anchor=None,
        )
    if parsed_anchor is None:
        candidate = _anchor_for_ledger(
            proposed, anchor_revision=1, previous_anchor_sha256=None
        )
        return _evaluation(
            decision=AnchorDecision.BOOTSTRAP_CANDIDATE,
            proposed_ledger=proposed,
            expectation=parsed_expectation,
            current_anchor=None,
            current_ledger=None,
            proposed_anchor=candidate,
        )
    assert parsed_current is not None
    if not _anchor_binds_ledger(parsed_anchor, parsed_current):
        raise ValueError("current anchor does not bind the supplied current ledger")
    if not _same_scope(parsed_current, proposed):
        return _evaluation(
            decision=AnchorDecision.SCOPE_MISMATCH_REJECTED,
            proposed_ledger=proposed,
            expectation=parsed_expectation,
            current_anchor=parsed_anchor,
            current_ledger=parsed_current,
            proposed_anchor=None,
        )
    if proposed["ledger_revision"] < parsed_current["ledger_revision"]:
        decision = AnchorDecision.ROLLBACK_REJECTED
        candidate = None
    elif proposed["ledger_revision"] == parsed_current["ledger_revision"]:
        if proposed["ledger_sha256"] == parsed_current["ledger_sha256"]:
            decision = AnchorDecision.UNCHANGED_CANDIDATE
        else:
            decision = AnchorDecision.FORK_REJECTED
        candidate = None
    elif not _is_exact_extension(parsed_current, proposed):
        decision = AnchorDecision.FORK_REJECTED
        candidate = None
    else:
        decision = AnchorDecision.ADVANCE_CANDIDATE
        candidate = _anchor_for_ledger(
            proposed,
            anchor_revision=parsed_anchor["anchor_revision"] + 1,
            previous_anchor_sha256=parsed_anchor["anchor_sha256"],
        )
    return _evaluation(
        decision=decision,
        proposed_ledger=proposed,
        expectation=parsed_expectation,
        current_anchor=parsed_anchor,
        current_ledger=parsed_current,
        proposed_anchor=candidate,
    )


__all__ = [
    "ANCHOR_STATE",
    "CONTRACT_STATE",
    "SCHEMA_ID",
    "SCHEMA_VERSION",
    "AnchorDecision",
    "MontageLearningExternalMonotonicAnchorCandidate",
    "MontageLearningExternalMonotonicAnchorEvaluation",
    "MontageLearningExternalMonotonicAnchorExpectation",
    "evaluate_montage_learning_external_monotonic_anchor",
]
