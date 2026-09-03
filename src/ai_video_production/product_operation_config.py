"""TASK-072-A authority-zero audit view of operation-specific config v2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .product_operation_broker import (
    _fail,
    _require_action,
    _require_exact_fields,
    _require_opaque_id,
    _require_sha256,
    _require_sha256_tuple,
    _sha256_json,
    _strict_json_object,
)


__all__ = (
    "OperationConfigAuditV2",
    "validate_operation_config_audit",
)


_MESSAGE_TYPE = "BvpOperationSpecificConfig"
# A1 admits only command names already frozen by the installed generic D2S
# contract. Other action profiles remain request/audit values until their
# separately owned command binding is supplied; this module does not guess it.
_COMMAND_BINDINGS = (
    ("D2S_VALIDATE", "SKILL_D2S_ADAPTER_V1", "validate"),
    ("D2S_EMIT_PROPOSAL", "SKILL_D2S_ADAPTER_V1", "emit-proposal"),
    ("D2S_FEEDBACK_TO_LEARNING", "SKILL_D2S_ADAPTER_V1", "feedback-to-learning"),
    ("D2S_ROUND_TRIP", "SKILL_D2S_ADAPTER_V1", "round-trip"),
    ("D2S_CONVERT_FRAME", "SKILL_D2S_ADAPTER_V1", "convert-frame"),
    ("D2S_VALIDATE_TASK056_SIDECAR", "SKILL_D2S_ADAPTER_V1", "validate-task056-sidecar"),
    ("D2S_CONNECTOR_STATUS", "SKILL_D2S_ADAPTER_V1", "connector-status"),
    ("D2S_PUBLISH_LEARNING", "SKILL_D2S_ADAPTER_V1", "publish-learning"),
    ("D2S_LOAD_PROFILE", "SKILL_D2S_ADAPTER_V1", "load-profile"),
)


def _expected_command(
    profile: str,
    bindings: tuple[tuple[str, str, str], ...] = _COMMAND_BINDINGS,
) -> tuple[str, str] | None:
    for bound_profile, command, subcommand in bindings:
        if profile == bound_profile:
            return command, subcommand
    return None


@dataclass(frozen=True, slots=True)
class OperationConfigAuditV2:
    contract_profile: str
    command: str
    subcommand: str
    operation_id: str
    ticket_id: str
    install_instance_id: str
    upstream_receipt_sha256: tuple[str, ...]
    expected_input_sha256: str
    expected_record_sha256: str
    expected_profile_sha256: str
    expected_delivery_sha256: str
    expected_result_sha256: str
    product_build_sha256: str
    adapter_build_sha256: str
    config_projection_build_sha256: str
    issue_monotonic_ms: int
    deadline_monotonic_ms: int
    expiry_utc: str
    config_sha256: str
    invocation_budget: int = 1
    distribution_config_mutated: bool = False
    authority_created: bool = False
    message_type: str = _MESSAGE_TYPE
    schema_version: str = "2.0.0"

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("TASK072_CONFIG_REJECTED")

    def __post_init__(self) -> None:
        _require_action(self.contract_profile, code="TASK072_CONFIG_REJECTED")
        if (self.command, self.subcommand) != _expected_command(self.contract_profile):
            raise _fail("TASK072_CONFIG_REJECTED")
        for value in (self.operation_id, self.ticket_id, self.install_instance_id):
            _require_opaque_id(value, code="TASK072_CONFIG_REJECTED")
        if len(self.operation_id) != 32 or len(self.ticket_id) != 32:
            raise _fail("TASK072_CONFIG_REJECTED")
        if any(
            character not in "0123456789abcdef"
            for character in self.operation_id + self.ticket_id
        ):
            raise _fail("TASK072_CONFIG_REJECTED")
        if type(self.upstream_receipt_sha256) is not tuple:
            raise _fail("TASK072_CONFIG_REJECTED")
        _require_sha256_tuple(
            self.upstream_receipt_sha256, code="TASK072_CONFIG_REJECTED"
        )
        for value in (
            self.expected_input_sha256,
            self.expected_record_sha256,
            self.expected_profile_sha256,
            self.expected_delivery_sha256,
            self.expected_result_sha256,
            self.product_build_sha256,
            self.adapter_build_sha256,
            self.config_projection_build_sha256,
            self.config_sha256,
        ):
            _require_sha256(value, code="TASK072_CONFIG_REJECTED")
        if (
            type(self.issue_monotonic_ms) is not int
            or type(self.deadline_monotonic_ms) is not int
            or not 0 <= self.issue_monotonic_ms < self.deadline_monotonic_ms <= 2**63 - 1
        ):
            raise _fail("TASK072_CONFIG_REJECTED")
        if not _valid_utc(self.expiry_utc):
            raise _fail("TASK072_CONFIG_REJECTED")
        if (
            self.invocation_budget != 1
            or self.distribution_config_mutated is not False
            or self.authority_created is not False
            or self.message_type != _MESSAGE_TYPE
            or self.schema_version != "2.0.0"
            or self.config_sha256
            != _sha256_json(self._body(), code="TASK072_CONFIG_REJECTED")
        ):
            raise _fail("TASK072_CONFIG_REJECTED")

    def _body(self) -> dict[str, Any]:
        return {
            "adapter_build_sha256": self.adapter_build_sha256,
            "authority_created": False,
            "command": self.command,
            "config_projection_build_sha256": self.config_projection_build_sha256,
            "contract_profile": self.contract_profile,
            "deadline_monotonic_ms": self.deadline_monotonic_ms,
            "distribution_config_mutated": False,
            "expected_delivery_sha256": self.expected_delivery_sha256,
            "expected_input_sha256": self.expected_input_sha256,
            "expected_profile_sha256": self.expected_profile_sha256,
            "expected_record_sha256": self.expected_record_sha256,
            "expected_result_sha256": self.expected_result_sha256,
            "expiry_utc": self.expiry_utc,
            "install_instance_id": self.install_instance_id,
            "invocation_budget": 1,
            "issue_monotonic_ms": self.issue_monotonic_ms,
            "message_type": self.message_type,
            "operation_id": self.operation_id,
            "product_build_sha256": self.product_build_sha256,
            "schema_version": self.schema_version,
            "subcommand": self.subcommand,
            "ticket_id": self.ticket_id,
            "upstream_receipt_sha256": list(self.upstream_receipt_sha256),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._body(), "config_sha256": self.config_sha256}


def _valid_utc(value: object) -> bool:
    if type(value) is not str or len(value) != 20:
        return False
    if (
        value[4:5] != "-"
        or value[7:8] != "-"
        or value[10:11] != "T"
        or value[13:14] != ":"
        or value[16:17] != ":"
        or value[19:] != "Z"
    ):
        return False
    digits = value[0:4] + value[5:7] + value[8:10] + value[11:13] + value[14:16] + value[17:19]
    if not digits.isascii() or not digits.isdigit():
        return False
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return True


def validate_operation_config_audit(payload: bytes) -> OperationConfigAuditV2:
    """Strictly parse an immutable config v2 audit document from exact bytes."""

    value = _strict_json_object(payload, code="TASK072_CONFIG_REJECTED")
    _require_exact_fields(
        value,
        frozenset(
            {
                "adapter_build_sha256",
                "authority_created",
                "command",
                "config_projection_build_sha256",
                "config_sha256",
                "contract_profile",
                "deadline_monotonic_ms",
                "distribution_config_mutated",
                "expected_delivery_sha256",
                "expected_input_sha256",
                "expected_profile_sha256",
                "expected_record_sha256",
                "expected_result_sha256",
                "expiry_utc",
                "install_instance_id",
                "invocation_budget",
                "issue_monotonic_ms",
                "message_type",
                "operation_id",
                "product_build_sha256",
                "schema_version",
                "subcommand",
                "ticket_id",
                "upstream_receipt_sha256",
            }
        ),
        code="TASK072_CONFIG_REJECTED",
    )
    converted = dict(value)
    if type(value["upstream_receipt_sha256"]) is not list:
        raise _fail("TASK072_CONFIG_REJECTED")
    converted["upstream_receipt_sha256"] = tuple(value["upstream_receipt_sha256"])
    return OperationConfigAuditV2(**converted)
