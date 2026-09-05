"""Pure synthetic UNKNOWN inference receipt for TASK-073 composition tests.

This module deliberately has no inference, audio, provider, process, or filesystem
surface.  Its only product is a body-free fixture receipt that cannot be promoted
to authority or production eligibility.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256

TASK_OWNER = "TASK-075"
RECEIPT_TYPE = "TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1"
SCHEMA_VERSION = 1
PRODUCER_STATE = "UNKNOWN"

RECEIPT_FIELDS = (
    "owner_task",
    "receipt_type",
    "schema_version",
    "opaque_ref",
    "receipt_sha256",
    "producer_build_sha256",
    "producer_state",
    "candidate_id",
    "candidate_sha256",
    "project_id",
    "project_manifest_sha256",
    "installed_session_sha256",
    "operation_plan_sha256",
    "quick_clone_flow_sha256",
    "revision",
    "head_sha256",
    "observed_at",
    "expires_at",
    "current",
    "fixture_only",
    "authority_created",
    "production_eligible",
)

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9][A-Za-z0-9_-]*)*$")
_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")
_HASH_DOMAIN = "TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1.receipt_sha256.v1"


def _identifier(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or len(value) > 200 or not _ID.fullmatch(value):
        raise ValueError(f"{field_name} is invalid or exposes a location")
    return value


def _digest(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} is invalid")
    return validate_sha256(value, field_name=field_name)


def _timestamp(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _TIME.fullmatch(value):
        raise ValueError(f"{field_name} must be canonical RFC3339 UTC")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError(f"{field_name} must be canonical RFC3339 UTC") from error
    return value


def _content_hash(value: Mapping[str, Any]) -> str:
    payload = {field: value[field] for field in RECEIPT_FIELDS if field != "receipt_sha256"}
    return sha256_bytes(canonical_json_bytes({"domain": _HASH_DOMAIN, "receipt": payload}))


def _normalize(value: Mapping[str, Any], *, verify_hash: bool) -> dict[str, Any]:
    if not isinstance(value, Mapping) or tuple(value) != RECEIPT_FIELDS:
        raise ValueError("receipt fields are incomplete, unknown, or reordered")
    result = copy.deepcopy(dict(value))

    if (
        result["owner_task"],
        result["receipt_type"],
        result["schema_version"],
        result["producer_state"],
    ) != (TASK_OWNER, RECEIPT_TYPE, SCHEMA_VERSION, PRODUCER_STATE):
        raise ValueError("receipt identity or producer state is invalid")

    _identifier(result["opaque_ref"], "opaque_ref")
    _identifier(result["project_id"], "project_id")
    for field in (
        "receipt_sha256",
        "producer_build_sha256",
        "project_manifest_sha256",
        "installed_session_sha256",
        "operation_plan_sha256",
        "quick_clone_flow_sha256",
        "head_sha256",
    ):
        _digest(result[field], field)
    if isinstance(result["revision"], bool) or not isinstance(result["revision"], int):
        raise ValueError("revision must be a positive bounded integer")
    if not 1 <= result["revision"] <= 2_147_483_647:
        raise ValueError("revision must be a positive bounded integer")
    _timestamp(result["observed_at"], "observed_at")

    if result["candidate_id"] is not None or result["candidate_sha256"] is not None:
        raise ValueError("synthetic UNKNOWN inference receipt cannot identify a candidate")
    if result["expires_at"] is not None:
        raise ValueError("synthetic UNKNOWN inference receipt cannot declare an expiry")
    if result["current"] is not True:
        raise ValueError("synthetic UNKNOWN inference receipt must be current")
    if result["fixture_only"] is not True:
        raise ValueError("synthetic UNKNOWN inference receipt must remain fixture-only")
    if result["authority_created"] is not False:
        raise ValueError("synthetic UNKNOWN inference receipt cannot create authority")
    if result["production_eligible"] is not False:
        raise ValueError("synthetic UNKNOWN inference receipt cannot be production eligible")

    expected_hash = _content_hash(result)
    if verify_hash and result["receipt_sha256"] != expected_hash:
        raise ValueError("receipt_sha256 does not match canonical fixture content")
    result["receipt_sha256"] = expected_hash
    return result


@dataclass(frozen=True)
class Task075SyntheticExecutionResultFixture:
    """Validated, immutable projection of one synthetic UNKNOWN result receipt."""

    _value: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_value",
            MappingProxyType(_normalize(self._value, verify_hash=True)),
        )

    @classmethod
    def create(
        cls,
        *,
        opaque_ref: str,
        producer_build_sha256: str,
        project_id: str,
        project_manifest_sha256: str,
        installed_session_sha256: str,
        operation_plan_sha256: str,
        quick_clone_flow_sha256: str,
        revision: int,
        head_sha256: str,
        observed_at: str,
    ) -> "Task075SyntheticExecutionResultFixture":
        body: dict[str, Any] = {
            "owner_task": TASK_OWNER,
            "receipt_type": RECEIPT_TYPE,
            "schema_version": SCHEMA_VERSION,
            "opaque_ref": opaque_ref,
            "receipt_sha256": "sha256:" + "0" * 64,
            "producer_build_sha256": producer_build_sha256,
            "producer_state": PRODUCER_STATE,
            "candidate_id": None,
            "candidate_sha256": None,
            "project_id": project_id,
            "project_manifest_sha256": project_manifest_sha256,
            "installed_session_sha256": installed_session_sha256,
            "operation_plan_sha256": operation_plan_sha256,
            "quick_clone_flow_sha256": quick_clone_flow_sha256,
            "revision": revision,
            "head_sha256": head_sha256,
            "observed_at": observed_at,
            "expires_at": None,
            "current": True,
            "fixture_only": True,
            "authority_created": False,
            "production_eligible": False,
        }
        instance = object.__new__(cls)
        object.__setattr__(
            instance,
            "_value",
            MappingProxyType(_normalize(body, verify_hash=False)),
        )
        return instance

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Task075SyntheticExecutionResultFixture":
        return cls(value)

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(dict(self._value))


__all__ = [
    "PRODUCER_STATE",
    "RECEIPT_FIELDS",
    "RECEIPT_TYPE",
    "SCHEMA_VERSION",
    "TASK_OWNER",
    "Task075SyntheticExecutionResultFixture",
]
