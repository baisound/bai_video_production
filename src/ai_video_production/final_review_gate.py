"""Typed external Gate bindings for TASK-036 P-UX-2D4.

These records validate already-issued authority receipts.  They do not create
the underlying Audio, edit, privacy, resource or rights decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Mapping, Sequence

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")


class FinalReviewGateId(str, Enum):
    AUDIO_COMPLETION = "AUDIO_COMPLETION"
    EDIT_PERSISTENCE = "EDIT_PERSISTENCE"
    PRIVACY = "PRIVACY"
    RESOURCE = "RESOURCE"
    RIGHTS_LICENSE = "RIGHTS_LICENSE"


class FinalReviewGateState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"
    REVOKED = "REVOKED"


_GATE_OWNERS = {
    FinalReviewGateId.AUDIO_COMPLETION: "DEVELOPER2",
    FinalReviewGateId.EDIT_PERSISTENCE: "TASK-044",
    FinalReviewGateId.PRIVACY: "TASK-016",
    FinalReviewGateId.RESOURCE: "TASK-020",
    FinalReviewGateId.RIGHTS_LICENSE: "TASK-003/027",
}


def _identity(value: object, name: str) -> str:
    if not isinstance(value, str) or not _IDENTITY.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


@dataclass(frozen=True, slots=True)
class FinalReviewExternalGateReceipt:
    """Canonical wrapper around one independently issued Gate receipt."""

    gate_id: FinalReviewGateId
    source_authority_owner: str
    project_id: str
    timeline_sha256: str
    source_receipt_id: str
    source_receipt_sha256: str
    state: FinalReviewGateState
    evaluated_at: str
    current_valid: bool
    invalidation_epoch: int

    def __post_init__(self) -> None:
        if not isinstance(self.gate_id, FinalReviewGateId):
            raise ValueError("gate_id is invalid")
        if self.source_authority_owner != _GATE_OWNERS[self.gate_id]:
            raise ValueError("external Gate owner does not match the closed registry")
        _identity(self.project_id, "project_id")
        _identity(self.source_receipt_id, "source_receipt_id")
        validate_sha256(self.timeline_sha256, field_name="timeline_sha256")
        validate_sha256(self.source_receipt_sha256, field_name="source_receipt_sha256")
        if not isinstance(self.state, FinalReviewGateState):
            raise ValueError("state is invalid")
        if not isinstance(self.evaluated_at, str) or not _TIMESTAMP.fullmatch(self.evaluated_at):
            raise ValueError("evaluated_at must be canonical UTC")
        if not isinstance(self.current_valid, bool):
            raise ValueError("current_valid must be boolean")
        if (self.state is FinalReviewGateState.PASS) != self.current_valid:
            raise ValueError("only a current-valid PASS receipt may close a Gate")
        if (isinstance(self.invalidation_epoch, bool)
                or not isinstance(self.invalidation_epoch, int)
                or self.invalidation_epoch < 0):
            raise ValueError("invalidation_epoch must be a non-negative integer")
        if self.state in {FinalReviewGateState.STALE, FinalReviewGateState.REVOKED}:
            if self.invalidation_epoch < 1:
                raise ValueError("stale or revoked Gate receipts require an invalidation epoch")
        elif self.invalidation_epoch != 0:
            raise ValueError("only stale or revoked Gate receipts carry an invalidation epoch")

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "FinalReviewExternalGateReceipt":
        if not isinstance(value, Mapping):
            raise ValueError("external Gate receipt must be a mapping")
        expected = {
            "receipt_version", "task_owner", "gate_id", "source_authority_owner",
            "project_id", "timeline_sha256", "source_receipt_id",
            "source_receipt_sha256", "state", "evaluated_at", "current_valid",
            "invalidation_epoch", "authority_effect_created", "receipt_sha256",
        }
        if set(value) != expected:
            raise ValueError("external Gate receipt fields are not exact")
        if value.get("receipt_version") != "1.0.0" or value.get("task_owner") != "TASK-036/P-UX-2D4":
            raise ValueError("external Gate receipt version or owner is invalid")
        if value.get("authority_effect_created") is not False:
            raise ValueError("external Gate wrapper claims prohibited authority")
        try:
            receipt = cls(
                gate_id=FinalReviewGateId(value.get("gate_id")),
                source_authority_owner=value.get("source_authority_owner"),
                project_id=value.get("project_id"),
                timeline_sha256=value.get("timeline_sha256"),
                source_receipt_id=value.get("source_receipt_id"),
                source_receipt_sha256=value.get("source_receipt_sha256"),
                state=FinalReviewGateState(value.get("state")),
                evaluated_at=value.get("evaluated_at"),
                current_valid=value.get("current_valid"),
                invalidation_epoch=value.get("invalidation_epoch"),
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("external Gate receipt contains an invalid closed value") from exc
        if receipt.to_dict() != dict(value):
            raise ValueError("external Gate receipt checksum or canonical body mismatch")
        return receipt

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "receipt_version": "1.0.0",
            "task_owner": "TASK-036/P-UX-2D4",
            "gate_id": self.gate_id.value,
            "source_authority_owner": self.source_authority_owner,
            "project_id": self.project_id,
            "timeline_sha256": self.timeline_sha256,
            "source_receipt_id": self.source_receipt_id,
            "source_receipt_sha256": self.source_receipt_sha256,
            "state": self.state.value,
            "evaluated_at": self.evaluated_at,
            "current_valid": self.current_valid,
            "invalidation_epoch": self.invalidation_epoch,
            "authority_effect_created": False,
        }
        return {**body, "receipt_sha256": sha256_bytes(canonical_json_bytes(body))}

    def to_readiness_dict(self) -> dict[str, object]:
        return {
            "gate_id": self.gate_id.value,
            "project_id": self.project_id,
            "timeline_sha256": self.timeline_sha256,
            "state": self.state.value,
            "receipt_sha256": self.to_dict()["receipt_sha256"],
        }


def validate_external_gate_receipts(
    receipts: Sequence[FinalReviewExternalGateReceipt],
) -> tuple[FinalReviewExternalGateReceipt, ...]:
    if not isinstance(receipts, Sequence) or isinstance(receipts, (str, bytes)) or len(receipts) > 5:
        raise ValueError("external Gate receipt collection is not bounded")
    result = tuple(receipts)
    if any(not isinstance(item, FinalReviewExternalGateReceipt) for item in result):
        raise ValueError("external Gate receipts must use the typed contract")
    gate_ids = [item.gate_id for item in result]
    if len(set(gate_ids)) != len(gate_ids):
        raise ValueError("external Gate receipt collection contains a duplicate")
    return tuple(sorted(result, key=lambda item: item.gate_id.value))


__all__ = [
    "FinalReviewExternalGateReceipt", "FinalReviewGateId", "FinalReviewGateState",
    "validate_external_gate_receipts",
]
