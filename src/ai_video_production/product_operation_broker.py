"""TASK-072-A public, authority-zero Product operation audit contracts.

This module intentionally contains no broker, ticket, channel, filesystem, or
child-process effect.  Its public values are immutable audit projections only.
The Product-private one-use authority described by TASK-072 is implemented by
later units and must never be reconstructed from these values.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
import re
import secrets
from typing import Any, Final, Mapping, Sequence


__all__ = (
    "ProductOperationRequestV1",
    "ProductOperationAuthorizationResolutionV1",
    "ProductOperationAuditReceiptV1",
    "ProductOperationTerminalStatusV1",
    "create_product_operation_request",
    "read_product_operation_status",
)


_SCHEMA_VERSION: Final = "1.0.0"
_REQUEST_MESSAGE: Final = "BvpProductOperationRequest"
_AUTHORIZATION_MESSAGE: Final = "BvpProductOperationAuthorizationResolution"
_AUDIT_RECEIPT_MESSAGE: Final = "BvpProductOperationAuditReceipt"
_TERMINAL_MESSAGE: Final = "BvpProductOperationTerminalStatus"
_MAX_RAW_BYTES: Final = 64 * 1024
_MAX_DEPTH: Final = 8
_MAX_OBJECT_MEMBERS: Final = 64
_MAX_ARRAY_ITEMS: Final = 64
_MAX_NODES: Final = 512
_MAX_STRING_BYTES: Final = 4096
_MAX_STRING_CODEPOINTS: Final = 4096
_OPAQUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")

_ACTION_PROFILES: Final = frozenset(
    {
        "INSTALL_AUTHORITY_PAIR_WRITE",
        "MIGRATION_CA_A_EXECUTE",
        "PROFILE_BIND_CA_B_EXECUTE",
        "GPU_REQUIRED_LAUNCH",
        "D2S_VALIDATE",
        "D2S_EMIT_PROPOSAL",
        "D2S_FEEDBACK_TO_LEARNING",
        "D2S_ROUND_TRIP",
        "D2S_CONVERT_FRAME",
        "D2S_VALIDATE_TASK056_SIDECAR",
        "D2S_CONNECTOR_STATUS",
        "D2S_PUBLISH_LEARNING",
        "PRODUCT_BROKER_TERMINAL_QUERY",
        "D2S_LOAD_PROFILE",
        "PRODUCT_D2S_ROUNDTRIP_E2E_VERIFY",
        "ACTIVATION_CONFIG_FINALIZE",
    }
)

_STABLE_CODES: Final = frozenset(
    {
        "TASK072_AUTHORIZATION_REJECTED",
        "TASK072_AUTHORIZATION_NC",
        "TASK072_RESERVATION_COLLISION",
        "TASK072_RESERVATION_UNKNOWN",
        "TASK072_TICKET_CONSUMED",
        "TASK072_TICKET_EXPIRED",
        "TASK072_SESSION_MISMATCH",
        "TASK072_CHANNEL_REJECTED",
        "TASK072_CONFIG_REJECTED",
        "TASK072_COMPLETION_UNKNOWN",
    }
)

_DURABLE_STATES: Final = frozenset(
    {
        "REQUESTED",
        "AUTHORIZED",
        "RESERVED",
        "ISSUED",
        "CONFIG_READY",
        "CHILD_BOUND",
        "IN_FLIGHT",
        "COMMITTED",
        "REJECTED",
        "BURNED",
        "BURNED_UNKNOWN",
        "BURNED_BY_SESSION_MISMATCH",
    }
)


class ProductOperationContractError(ValueError):
    """Body-free stable validation failure (deliberately not exported)."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class _DuplicateKey(ValueError):
    pass


def _fail(code: str) -> ProductOperationContractError:
    return ProductOperationContractError(code)


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey
        result[key] = value
    return result


def _reject_constant(_: str) -> Any:
    raise ValueError


def _strict_json_object(
    payload: bytes, *, code: str = "TASK072_AUTHORIZATION_REJECTED"
) -> dict[str, Any]:
    if type(payload) is not bytes:
        raise _fail(code)
    if not payload or len(payload) > _MAX_RAW_BYTES or payload.startswith(b"\xef\xbb\xbf"):
        raise _fail(code)
    try:
        text = payload.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_pairs_without_duplicates,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError, RecursionError, MemoryError):
        raise _fail(code) from None
    if type(value) is not dict:
        raise _fail(code)
    _validate_tree(value, code=code)
    return value


def _validate_tree(value: Any, *, code: str) -> None:
    nodes = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > _MAX_NODES or depth > _MAX_DEPTH:
            raise _fail(code)
        current_type = type(current)
        if current_type is dict:
            if len(current) > _MAX_OBJECT_MEMBERS:
                raise _fail(code)
            for key, child in current.items():
                _validate_string(key, code=code)
                stack.append((child, depth + 1))
        elif current_type is list:
            if len(current) > _MAX_ARRAY_ITEMS:
                raise _fail(code)
            stack.extend((child, depth + 1) for child in current)
        elif current_type is str:
            _validate_string(current, code=code)
        elif current_type is float:
            if not math.isfinite(current):
                raise _fail(code)
        elif current_type is int:
            if not -(2**63) <= current <= 2**63 - 1:
                raise _fail(code)
        elif current is None or current_type is bool:
            continue
        else:
            raise _fail(code)


def _validate_string(value: str, *, code: str) -> None:
    if type(value) is not str or len(value) > _MAX_STRING_CODEPOINTS:
        raise _fail(code)
    if any(ord(character) < 32 for character in value):
        raise _fail(code)
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeError:
        raise _fail(code) from None
    if len(encoded) > _MAX_STRING_BYTES:
        raise _fail(code)


def _canonical_json_bytes(
    value: Mapping[str, Any], *, code: str = "TASK072_AUTHORIZATION_REJECTED"
) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError, MemoryError):
        raise _fail(code) from None


def _sha256_json(
    value: Mapping[str, Any], *, code: str = "TASK072_AUTHORIZATION_REJECTED"
) -> str:
    return "sha256:" + hashlib.sha256(
        _canonical_json_bytes(value, code=code)
    ).hexdigest()


def _require_exact_fields(
    value: Mapping[str, Any],
    expected: frozenset[str],
    *,
    code: str = "TASK072_AUTHORIZATION_REJECTED",
) -> None:
    if type(value) is not dict or frozenset(value) != expected:
        raise _fail(code)


def _require_sha256(
    value: object, *, code: str = "TASK072_AUTHORIZATION_REJECTED"
) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise _fail(code)
    return value


def _require_opaque_id(
    value: object, *, code: str = "TASK072_AUTHORIZATION_REJECTED"
) -> str:
    if type(value) is not str or _OPAQUE_ID.fullmatch(value) is None:
        raise _fail(code)
    if (
        any(token in value for token in ("/", "\\", "://"))
        or re.match(r"^[A-Za-z]:", value) is not None
    ):
        raise _fail(code)
    return value


def _require_action(
    value: object, *, code: str = "TASK072_AUTHORIZATION_REJECTED"
) -> str:
    if type(value) is not str or value not in _ACTION_PROFILES:
        raise _fail(code)
    return value


def _require_utc(value: object, *, code: str) -> str:
    if type(value) is not str or len(value) != 20:
        raise _fail(code)
    if (
        value[4:5] != "-"
        or value[7:8] != "-"
        or value[10:11] != "T"
        or value[13:14] != ":"
        or value[16:17] != ":"
        or value[19:] != "Z"
    ):
        raise _fail(code)
    digits = (
        value[0:4]
        + value[5:7]
        + value[8:10]
        + value[11:13]
        + value[14:16]
        + value[17:19]
    )
    if not digits.isascii() or not digits.isdigit():
        raise _fail(code)
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise _fail(code) from None
    return value


def _require_sha256_tuple(
    value: object, *, code: str = "TASK072_AUTHORIZATION_REJECTED"
) -> tuple[str, ...]:
    if type(value) not in {tuple, list}:
        raise _fail(code)
    if len(value) > 32:
        raise _fail(code)
    result = tuple(_require_sha256(item, code=code) for item in value)
    if len(set(result)) != len(result):
        raise _fail(code)
    return result


@dataclass(frozen=True, slots=True)
class ProductOperationRequestV1:
    request_id: str
    action_profile: str
    upstream_receipt_sha256: tuple[str, ...] = ()
    requested_state: str = "REQUESTED"
    authority_created: bool = False
    message_type: str = _REQUEST_MESSAGE
    schema_version: str = _SCHEMA_VERSION

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("TASK072_AUTHORIZATION_REJECTED")

    def __post_init__(self) -> None:
        _require_opaque_id(self.request_id)
        _require_action(self.action_profile)
        if type(self.upstream_receipt_sha256) is not tuple:
            raise _fail("TASK072_AUTHORIZATION_REJECTED")
        _require_sha256_tuple(self.upstream_receipt_sha256)
        if (
            self.requested_state != "REQUESTED"
            or self.authority_created is not False
            or self.message_type != _REQUEST_MESSAGE
            or self.schema_version != _SCHEMA_VERSION
        ):
            raise _fail("TASK072_AUTHORIZATION_REJECTED")

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_profile": self.action_profile,
            "authority_created": False,
            "message_type": self.message_type,
            "request_id": self.request_id,
            "requested_state": self.requested_state,
            "schema_version": self.schema_version,
            "upstream_receipt_sha256": list(self.upstream_receipt_sha256),
        }


@dataclass(frozen=True, slots=True)
class ProductOperationAuthorizationResolutionV1:
    request_id: str
    action_profile: str
    resolution: str
    stable_code: str
    reservation_created: bool
    ticket_created: bool
    resolution_sha256: str
    authority_created: bool = False
    message_type: str = _AUTHORIZATION_MESSAGE
    schema_version: str = _SCHEMA_VERSION

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("TASK072_AUTHORIZATION_REJECTED")

    def __post_init__(self) -> None:
        _require_opaque_id(self.request_id)
        _require_action(self.action_profile)
        if type(self.resolution) is not str or self.resolution not in {
            "REJECTED",
            "NOT_CONFIRMED",
        }:
            raise _fail("TASK072_AUTHORIZATION_REJECTED")
        expected_code = {
            "REJECTED": "TASK072_AUTHORIZATION_REJECTED",
            "NOT_CONFIRMED": "TASK072_AUTHORIZATION_NC",
        }[self.resolution]
        if self.stable_code != expected_code:
            raise _fail("TASK072_AUTHORIZATION_REJECTED")
        if (
            self.reservation_created is not False
            or self.ticket_created is not False
            or self.authority_created is not False
            or self.message_type != _AUTHORIZATION_MESSAGE
            or self.schema_version != _SCHEMA_VERSION
        ):
            raise _fail("TASK072_AUTHORIZATION_REJECTED")
        _require_sha256(self.resolution_sha256)
        if self.resolution_sha256 != _sha256_json(self._body()):
            raise _fail("TASK072_AUTHORIZATION_REJECTED")

    def _body(self) -> dict[str, Any]:
        return {
            "action_profile": self.action_profile,
            "authority_created": False,
            "message_type": self.message_type,
            "request_id": self.request_id,
            "reservation_created": False,
            "resolution": self.resolution,
            "schema_version": self.schema_version,
            "stable_code": self.stable_code,
            "ticket_created": False,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._body(), "resolution_sha256": self.resolution_sha256}


@dataclass(frozen=True, slots=True)
class ProductOperationAuditReceiptV1:
    action_profile: str
    terminal_state: str
    stable_code: str | None
    event_revision: int
    event_utc: str
    operation_commitment_sha256: str
    ticket_commitment_sha256: str
    event_commitment_sha256: str
    config_commitment_sha256: str
    result_sha256: str
    upstream_receipt_count: int
    downstream_receipt_count: int
    consumer_effect_observed: bool
    receipt_sha256: str
    authority_created: bool = False
    message_type: str = _AUDIT_RECEIPT_MESSAGE
    schema_version: str = _SCHEMA_VERSION

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("TASK072_COMPLETION_UNKNOWN")

    def __post_init__(self) -> None:
        _require_action(self.action_profile, code="TASK072_COMPLETION_UNKNOWN")
        if type(self.terminal_state) is not str or self.terminal_state not in {
            "COMMITTED",
            "REJECTED",
            "BURNED_UNKNOWN",
        }:
            raise _fail("TASK072_COMPLETION_UNKNOWN")
        if self.terminal_state == "COMMITTED":
            if self.stable_code is not None:
                raise _fail("TASK072_COMPLETION_UNKNOWN")
        elif type(self.stable_code) is not str or self.stable_code not in _STABLE_CODES:
            raise _fail("TASK072_COMPLETION_UNKNOWN")
        for value in (
            self.operation_commitment_sha256,
            self.ticket_commitment_sha256,
            self.event_commitment_sha256,
            self.config_commitment_sha256,
            self.result_sha256,
            self.receipt_sha256,
        ):
            _require_sha256(value, code="TASK072_COMPLETION_UNKNOWN")
        for value in (self.upstream_receipt_count, self.downstream_receipt_count):
            if type(value) is not int or not 0 <= value <= 32:
                raise _fail("TASK072_COMPLETION_UNKNOWN")
        if (
            type(self.event_revision) is not int
            or not 1 <= self.event_revision <= 2147483647
        ):
            raise _fail("TASK072_COMPLETION_UNKNOWN")
        _require_utc(self.event_utc, code="TASK072_COMPLETION_UNKNOWN")
        if (
            type(self.consumer_effect_observed) is not bool
            or self.authority_created is not False
            or self.consumer_effect_observed
            is not (self.terminal_state == "COMMITTED")
            or self.message_type != _AUDIT_RECEIPT_MESSAGE
            or self.schema_version != _SCHEMA_VERSION
            or self.receipt_sha256
            != _sha256_json(self._body(), code="TASK072_COMPLETION_UNKNOWN")
        ):
            raise _fail("TASK072_COMPLETION_UNKNOWN")

    def _body(self) -> dict[str, Any]:
        return {
            "action_profile": self.action_profile,
            "authority_created": False,
            "config_commitment_sha256": self.config_commitment_sha256,
            "consumer_effect_observed": self.consumer_effect_observed,
            "downstream_receipt_count": self.downstream_receipt_count,
            "event_commitment_sha256": self.event_commitment_sha256,
            "event_revision": self.event_revision,
            "event_utc": self.event_utc,
            "message_type": self.message_type,
            "operation_commitment_sha256": self.operation_commitment_sha256,
            "result_sha256": self.result_sha256,
            "schema_version": self.schema_version,
            "stable_code": self.stable_code,
            "terminal_state": self.terminal_state,
            "ticket_commitment_sha256": self.ticket_commitment_sha256,
            "upstream_receipt_count": self.upstream_receipt_count,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._body(), "receipt_sha256": self.receipt_sha256}


@dataclass(frozen=True, slots=True)
class ProductOperationTerminalStatusV1:
    operation_commitment_sha256: str
    durable_state: str
    stable_code: str | None
    terminal: bool
    committed: bool
    effect_confirmed: bool
    status_sha256: str
    authority_created: bool = False
    message_type: str = _TERMINAL_MESSAGE
    schema_version: str = _SCHEMA_VERSION

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("TASK072_COMPLETION_UNKNOWN")

    def __post_init__(self) -> None:
        _require_sha256(
            self.operation_commitment_sha256, code="TASK072_COMPLETION_UNKNOWN"
        )
        _require_sha256(self.status_sha256, code="TASK072_COMPLETION_UNKNOWN")
        if type(self.durable_state) is not str or self.durable_state not in _DURABLE_STATES:
            raise _fail("TASK072_COMPLETION_UNKNOWN")
        if any(
            type(value) is not bool
            for value in (self.terminal, self.committed, self.effect_confirmed)
        ):
            raise _fail("TASK072_COMPLETION_UNKNOWN")
        terminal_expected = self.durable_state in {
            "COMMITTED",
            "REJECTED",
            "BURNED",
            "BURNED_UNKNOWN",
            "BURNED_BY_SESSION_MISMATCH",
        }
        if self.durable_state == "COMMITTED" or not terminal_expected:
            if self.stable_code is not None:
                raise _fail("TASK072_COMPLETION_UNKNOWN")
        elif type(self.stable_code) is not str or self.stable_code not in _STABLE_CODES:
            raise _fail("TASK072_COMPLETION_UNKNOWN")
        if (
            self.terminal is not terminal_expected
            or self.committed is not (self.durable_state == "COMMITTED")
            or self.effect_confirmed is not self.committed
            or self.authority_created is not False
            or self.message_type != _TERMINAL_MESSAGE
            or self.schema_version != _SCHEMA_VERSION
            or self.status_sha256
            != _sha256_json(self._body(), code="TASK072_COMPLETION_UNKNOWN")
        ):
            raise _fail("TASK072_COMPLETION_UNKNOWN")

    def _body(self) -> dict[str, Any]:
        return {
            "authority_created": False,
            "committed": self.committed,
            "durable_state": self.durable_state,
            "effect_confirmed": self.effect_confirmed,
            "message_type": self.message_type,
            "operation_commitment_sha256": self.operation_commitment_sha256,
            "schema_version": self.schema_version,
            "stable_code": self.stable_code,
            "terminal": self.terminal,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._body(), "status_sha256": self.status_sha256}


def create_product_operation_request(
    *, action_profile: str, upstream_receipt_sha256: Sequence[str] = ()
) -> ProductOperationRequestV1:
    """Create a non-authoritative Product UI request projection."""

    if type(upstream_receipt_sha256) not in {tuple, list}:
        raise _fail("TASK072_AUTHORIZATION_REJECTED")
    receipts = _require_sha256_tuple(upstream_receipt_sha256)
    request = ProductOperationRequestV1(
        request_id="request-" + secrets.token_hex(16),
        action_profile=_require_action(action_profile),
        upstream_receipt_sha256=receipts,
    )
    return request


def _authorization_resolution_from_bytes(
    payload: bytes,
) -> ProductOperationAuthorizationResolutionV1:
    value = _strict_json_object(payload, code="TASK072_AUTHORIZATION_REJECTED")
    _require_exact_fields(
        value,
        frozenset(
            {
                "action_profile",
                "authority_created",
                "message_type",
                "request_id",
                "reservation_created",
                "resolution",
                "resolution_sha256",
                "schema_version",
                "stable_code",
                "ticket_created",
            }
        ),
    )
    return ProductOperationAuthorizationResolutionV1(**value)


def _audit_receipt_from_bytes(payload: bytes) -> ProductOperationAuditReceiptV1:
    value = _strict_json_object(payload, code="TASK072_COMPLETION_UNKNOWN")
    _require_exact_fields(
        value,
        frozenset(
            {
                "action_profile",
                "authority_created",
                "config_commitment_sha256",
                "consumer_effect_observed",
                "downstream_receipt_count",
                "event_commitment_sha256",
                "event_revision",
                "event_utc",
                "message_type",
                "operation_commitment_sha256",
                "receipt_sha256",
                "result_sha256",
                "schema_version",
                "stable_code",
                "terminal_state",
                "ticket_commitment_sha256",
                "upstream_receipt_count",
            }
        ),
        code="TASK072_COMPLETION_UNKNOWN",
    )
    return ProductOperationAuditReceiptV1(**value)


def read_product_operation_status(payload: bytes) -> ProductOperationTerminalStatusV1:
    """Strictly parse one public terminal-status byte document.

    The function reads no path and creates no broker/ticket authority.
    """

    value = _strict_json_object(payload, code="TASK072_COMPLETION_UNKNOWN")
    _require_exact_fields(
        value,
        frozenset(
            {
                "authority_created",
                "committed",
                "durable_state",
                "effect_confirmed",
                "message_type",
                "operation_commitment_sha256",
                "schema_version",
                "stable_code",
                "status_sha256",
                "terminal",
            }
        ),
        code="TASK072_COMPLETION_UNKNOWN",
    )
    return ProductOperationTerminalStatusV1(**value)
