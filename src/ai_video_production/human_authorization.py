"""Effect-zero public fixtures for TASK-071 Human authorization contracts.

This module intentionally has no live Human broker, ticket issuer, persistence,
native UI, process, or capability factory.  Its public values are display or
fixture data only and cannot authorize an effect.
"""

from __future__ import annotations

import json
import math
import re
from hashlib import sha256
from datetime import UTC, datetime
from enum import Enum
from types import MappingProxyType
from typing import Final, Mapping, TypeAlias


HUMAN_BROKER_CORE_FIXTURE_V1: Final = "HUMAN_BROKER_CORE_FIXTURE_V1"
HUMAN_ACTION_ABI_V1: Final = "HUMAN_ACTION_ABI_V1"
HUMAN_DISPLAY_PROJECTION_V1: Final = "HUMAN_DISPLAY_PROJECTION_V1"
_REJECTED_EFFECT_ZERO: Final = "REJECTED_EFFECT0"
_MAX_FIXTURE_BYTES: Final = 65_536
_MAX_FIXTURE_DEPTH: Final = 16
_SHA256_RE: Final = re.compile(r"sha256:[0-9a-f]{64}\Z")
_RESERVATION_ID_RE: Final = re.compile(r"har-[0-9a-f]{32}\Z")
_DECISION_ID_RE: Final = re.compile(r"hde-[0-9a-f]{32}\Z")
_AUDIT_ID_RE: Final = re.compile(r"harc-[0-9a-f]{32}\Z")
_CANONICAL_UTC_RE: Final = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")

FrozenJson: TypeAlias = str | int | float | bool | None | tuple["FrozenJson", ...] | Mapping[str, "FrozenJson"]


class HumanAction(Enum):
    """The only action names frozen by the effect-zero fixture boundary."""

    PREFERENCE_PROMOTE = "PREFERENCE_PROMOTE"
    PREFERENCE_ROLLBACK = "PREFERENCE_ROLLBACK"
    CONNECTOR_ACTIVATE = "CONNECTOR_ACTIVATE"
    CONNECTOR_DEACTIVATE = "CONNECTOR_DEACTIVATE"


_ACTIONS = frozenset(item.value for item in HumanAction)
_RESERVATION_FIELDS: Final = frozenset((
    "schema_version", "record_kind", "reservation_id", "action", "operation_id",
    "action_plan_sha256", "issued_at", "expires_at", "invocation_budget",
    "authority_created", "effect_performed", "native_user_presence_verified",
))
_DECISION_FIELDS: Final = frozenset((
    "schema_version", "record_kind", "decision_event_id", "reservation_id",
    "reservation_sha256", "action", "decision", "occurred_at", "authority_created",
    "effect_performed", "native_user_presence_verified",
))
_AUDIT_FIELDS: Final = frozenset((
    "schema_version", "record_kind", "audit_receipt_id", "reservation_id",
    "reservation_sha256", "decision_event_id", "decision_event_sha256", "action",
    "outcome", "authority_created", "effect_performed", "native_user_presence_verified",
))
_DECISIONS: Final = frozenset(("AUDIT_ONLY", "REJECTED", "EXPIRED", "REPLAY_REJECTED"))


def _catalog_text(action: HumanAction, /) -> tuple[str, str, str, str, str]:
    if action is HumanAction.PREFERENCE_PROMOTE:
        return ("PREFERENCE_PROMOTE", "学習設定を採用します", "確認済みの学習設定を採用候補として記録します。", "現在の学習設定", "確認した学習設定")
    if action is HumanAction.PREFERENCE_ROLLBACK:
        return ("PREFERENCE_ROLLBACK", "学習設定を以前の版へ戻します", "以前の版へ戻す候補を記録します。履歴は削除しません。", "現在の学習設定", "確認した以前の学習設定")
    if action is HumanAction.CONNECTOR_ACTIVATE:
        return ("CONNECTOR_ACTIVATE", "学習コネクターを有効にします", "有効化の確認候補を記録します。ここでは接続を変更しません。", "連携は無効です", "連携を有効にする候補")
    if action is HumanAction.CONNECTOR_DEACTIVATE:
        return ("CONNECTOR_DEACTIVATE", "学習コネクターを無効にします", "無効化の確認候補を記録します。学習データは削除しません。", "連携は有効です", "連携を無効にする候補")
    raise ValueError(_REJECTED_EFFECT_ZERO)


def project_human_action_for_audit(action: HumanAction, /) -> tuple[tuple[str, str | bool], ...]:
    """Return immutable, non-authoritative product text for one closed action."""

    if type(action) is not HumanAction:
        raise ValueError(_REJECTED_EFFECT_ZERO)
    action_name, title_ja, explanation_ja, current_ja, target_ja = _catalog_text(action)
    return (
        ("fixture_version", HUMAN_BROKER_CORE_FIXTURE_V1),
        ("action_abi", HUMAN_ACTION_ABI_V1),
        ("action", action_name),
        ("title_ja", title_ja),
        ("explanation_ja", explanation_ja),
        ("current_state_label_ja", current_ja),
        ("target_state_label_ja", target_ja),
        ("authority_created", False),
        ("effect_performed", False),
        ("native_user_presence_verified", False),
    )


def _reject_constant(_: str) -> None:
    raise ValueError(_REJECTED_EFFECT_ZERO)


def _parse_finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(_REJECTED_EFFECT_ZERO)
    return value


def _parse_canonical_utc(value: object) -> datetime:
    if type(value) is not str:
        raise ValueError(_REJECTED_EFFECT_ZERO)
    if _CANONICAL_UTC_RE.fullmatch(value) is None:
        raise ValueError(_REJECTED_EFFECT_ZERO)
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as error:
        raise ValueError(_REJECTED_EFFECT_ZERO) from error


def _require_pattern(value: object, pattern: re.Pattern[str]) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise ValueError(_REJECTED_EFFECT_ZERO)
    return value


def _canonical_document_sha256(document: dict[str, object]) -> str:
    try:
        encoded = json.dumps(
            document,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ValueError(_REJECTED_EFFECT_ZERO) from error
    return f"sha256:{sha256(encoded).hexdigest()}"


def _require_effect_zero_document(
    document: dict[str, object],
    *,
    fields: frozenset[str],
    kind: str,
) -> None:
    if type(document) is not dict or set(document) != fields:
        raise ValueError(_REJECTED_EFFECT_ZERO)
    if document.get("schema_version") != "1.0.0" or document.get("record_kind") != kind:
        raise ValueError(_REJECTED_EFFECT_ZERO)
    if type(document.get("action")) is not str or document["action"] not in _ACTIONS:
        raise ValueError(_REJECTED_EFFECT_ZERO)
    for flag in ("authority_created", "effect_performed", "native_user_presence_verified"):
        if document.get(flag) is not False:
            raise ValueError(_REJECTED_EFFECT_ZERO)


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(_REJECTED_EFFECT_ZERO)
        result[key] = value
    return result


def _freeze_json(value: object, depth: int = 0) -> FrozenJson:
    if depth > _MAX_FIXTURE_DEPTH:
        raise ValueError(_REJECTED_EFFECT_ZERO)
    if type(value) is str:
        try:
            value.encode("utf-8", "strict")
        except UnicodeEncodeError as error:
            raise ValueError(_REJECTED_EFFECT_ZERO) from error
        return value
    if value is None or type(value) in {int, float, bool}:
        return value
    if type(value) is list:
        return tuple(_freeze_json(item, depth + 1) for item in value)
    if type(value) is dict:
        for key in value:
            if type(key) is not str:
                raise ValueError(_REJECTED_EFFECT_ZERO)
            try:
                key.encode("utf-8", "strict")
            except UnicodeEncodeError as error:
                raise ValueError(_REJECTED_EFFECT_ZERO) from error
        return MappingProxyType({key: _freeze_json(item, depth + 1) for key, item in value.items()})
    raise ValueError(_REJECTED_EFFECT_ZERO)


def decode_effect_zero_fixture_json(raw: str | bytes, /) -> Mapping[str, FrozenJson]:
    """Strictly decode bounded fixture JSON without creating any authority.

    Duplicate keys, non-finite numbers, BOM-prefixed input, trailing data and
    non-object documents are rejected before callers can use fixture data.
    """

    if type(raw) is bytes:
        if len(raw) > _MAX_FIXTURE_BYTES:
            raise ValueError(_REJECTED_EFFECT_ZERO)
        try:
            text = raw.decode("utf-8", "strict")
        except UnicodeDecodeError as error:
            raise ValueError(_REJECTED_EFFECT_ZERO) from error
    elif type(raw) is str:
        try:
            encoded = raw.encode("utf-8", "strict")
        except UnicodeEncodeError as error:
            raise ValueError(_REJECTED_EFFECT_ZERO) from error
        if len(encoded) > _MAX_FIXTURE_BYTES:
            raise ValueError(_REJECTED_EFFECT_ZERO)
        text = raw
    else:
        raise ValueError(_REJECTED_EFFECT_ZERO)
    if text.startswith("\ufeff"):
        raise ValueError(_REJECTED_EFFECT_ZERO)
    try:
        document = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
            parse_float=_parse_finite_float,
            strict=True,
        )
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(_REJECTED_EFFECT_ZERO) from error
    frozen = _freeze_json(document)
    if not isinstance(frozen, Mapping):
        raise ValueError(_REJECTED_EFFECT_ZERO)
    return frozen


def project_fixture_chain_for_audit(
    reservation: dict[str, object],
    decision_event: dict[str, object],
    audit_receipt: dict[str, object],
    /,
) -> tuple[tuple[str, str | bool], ...]:
    """Check a closed fixture chain and return an effect-zero audit projection.

    This validates only relationships needed by fixtures.  It records no replay
    state and intentionally cannot issue a ticket, capability, or authorization.
    """

    _require_effect_zero_document(reservation, fields=_RESERVATION_FIELDS, kind="HUMAN_AUTHORIZATION_RESERVATION_V1")
    _require_effect_zero_document(decision_event, fields=_DECISION_FIELDS, kind="HUMAN_AUTHORIZATION_DECISION_EVENT_V1")
    _require_effect_zero_document(audit_receipt, fields=_AUDIT_FIELDS, kind="HUMAN_AUTHORIZATION_AUDIT_RECEIPT_V1")
    action = reservation["action"]
    _require_pattern(reservation["reservation_id"], _RESERVATION_ID_RE)
    _require_pattern(decision_event["decision_event_id"], _DECISION_ID_RE)
    _require_pattern(audit_receipt["audit_receipt_id"], _AUDIT_ID_RE)
    for document, field in (
        (reservation, "action_plan_sha256"),
        (decision_event, "reservation_sha256"),
        (audit_receipt, "reservation_sha256"),
        (audit_receipt, "decision_event_sha256"),
    ):
        _require_pattern(document[field], _SHA256_RE)
    if type(reservation["operation_id"]) is not str or re.fullmatch(r"hop-[0-9a-f]{32}", reservation["operation_id"]) is None:
        raise ValueError(_REJECTED_EFFECT_ZERO)
    if type(reservation["invocation_budget"]) is not int or reservation["invocation_budget"] != 1:
        raise ValueError(_REJECTED_EFFECT_ZERO)
    if (
        type(decision_event["decision"]) is not str
        or decision_event["decision"] not in _DECISIONS
        or audit_receipt["outcome"] != decision_event["decision"]
    ):
        raise ValueError(_REJECTED_EFFECT_ZERO)
    if (
        decision_event["action"] != action
        or audit_receipt["action"] != action
        or decision_event["reservation_id"] != reservation["reservation_id"]
        or audit_receipt["reservation_id"] != reservation["reservation_id"]
        or audit_receipt["decision_event_id"] != decision_event["decision_event_id"]
    ):
        raise ValueError(_REJECTED_EFFECT_ZERO)
    reservation_sha256 = _canonical_document_sha256(reservation)
    decision_event_sha256 = _canonical_document_sha256(decision_event)
    if (
        decision_event["reservation_sha256"] != reservation_sha256
        or audit_receipt["reservation_sha256"] != reservation_sha256
        or audit_receipt["decision_event_sha256"] != decision_event_sha256
    ):
        raise ValueError(_REJECTED_EFFECT_ZERO)
    issued_at = _parse_canonical_utc(reservation.get("issued_at"))
    expires_at = _parse_canonical_utc(reservation.get("expires_at"))
    occurred_at = _parse_canonical_utc(decision_event.get("occurred_at"))
    if not (issued_at <= occurred_at <= expires_at):
        raise ValueError(_REJECTED_EFFECT_ZERO)
    return (
        ("fixture_version", HUMAN_BROKER_CORE_FIXTURE_V1),
        ("action", action),
        ("chain_status", "AUDIT_ONLY"),
        ("authority_created", False),
        ("effect_performed", False),
        ("native_user_presence_verified", False),
    )


__all__ = (
    "HUMAN_ACTION_ABI_V1",
    "HUMAN_BROKER_CORE_FIXTURE_V1",
    "HUMAN_DISPLAY_PROJECTION_V1",
    "HumanAction",
    "decode_effect_zero_fixture_json",
    "project_fixture_chain_for_audit",
    "project_human_action_for_audit",
)
