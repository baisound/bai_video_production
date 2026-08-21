"""Current typed TASK-044 receipt for durable Timeline edit persistence."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from .interactive_timeline_store import SUPPORTED_FORMAT_VERSIONS
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")


def _identity(value: object, name: str) -> str:
    if not isinstance(value, str) or not _IDENTITY.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


@dataclass(frozen=True, slots=True)
class Task044EditPersistenceReceipt:
    """Read-only proof derived from the latest manifest-bound edit revision."""

    receipt_id: str
    project_id: str
    timeline_sha256: str
    project_manifest_sha256: str
    edit_snapshot_sha256: str
    snapshot_version: str
    history_id: str
    current_revision: int
    current_revision_sha256: str
    evaluated_at: str

    def __post_init__(self) -> None:
        _identity(self.receipt_id, "receipt_id")
        _identity(self.project_id, "project_id")
        _identity(self.history_id, "history_id")
        for name in (
            "timeline_sha256", "project_manifest_sha256", "edit_snapshot_sha256",
            "current_revision_sha256",
        ):
            validate_sha256(getattr(self, name), field_name=name)
        if self.snapshot_version not in SUPPORTED_FORMAT_VERSIONS:
            raise ValueError("snapshot_version is unsupported")
        if (
            isinstance(self.current_revision, bool)
            or not isinstance(self.current_revision, int)
            or self.current_revision < 1
        ):
            raise ValueError("current_revision must be positive")
        if not isinstance(self.evaluated_at, str) or not _TIMESTAMP.fullmatch(self.evaluated_at):
            raise ValueError("evaluated_at must be canonical UTC")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "receipt_version": "1.0.0",
            "task_owner": "TASK-044/P-NLE-2",
            "receipt_id": self.receipt_id,
            "project_id": self.project_id,
            "timeline_sha256": self.timeline_sha256,
            "project_manifest_sha256": self.project_manifest_sha256,
            "edit_snapshot_sha256": self.edit_snapshot_sha256,
            "snapshot_version": self.snapshot_version,
            "history_id": self.history_id,
            "current_revision": self.current_revision,
            "current_revision_sha256": self.current_revision_sha256,
            "evaluated_at": self.evaluated_at,
            "state": "CURRENT",
            "current_valid": True,
            "authority_effect_created": False,
        }
        return {**body, "receipt_sha256": sha256_bytes(canonical_json_bytes(body))}

    @property
    def receipt_sha256(self) -> str:
        return self.to_dict()["receipt_sha256"]

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "Task044EditPersistenceReceipt":
        expected = {
            "receipt_version", "task_owner", "receipt_id", "project_id",
            "timeline_sha256", "project_manifest_sha256", "edit_snapshot_sha256",
            "snapshot_version", "history_id", "current_revision",
            "current_revision_sha256", "evaluated_at", "state", "current_valid",
            "authority_effect_created", "receipt_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("edit persistence receipt fields are not exact")
        if (
            value.get("receipt_version") != "1.0.0"
            or value.get("task_owner") != "TASK-044/P-NLE-2"
            or value.get("state") != "CURRENT"
            or value.get("current_valid") is not True
            or value.get("authority_effect_created") is not False
        ):
            raise ValueError("edit persistence receipt authority is invalid")
        try:
            receipt = cls(
                receipt_id=value.get("receipt_id"),
                project_id=value.get("project_id"),
                timeline_sha256=value.get("timeline_sha256"),
                project_manifest_sha256=value.get("project_manifest_sha256"),
                edit_snapshot_sha256=value.get("edit_snapshot_sha256"),
                snapshot_version=value.get("snapshot_version"),
                history_id=value.get("history_id"),
                current_revision=value.get("current_revision"),
                current_revision_sha256=value.get("current_revision_sha256"),
                evaluated_at=value.get("evaluated_at"),
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("edit persistence receipt contains an invalid value") from exc
        if receipt.to_dict() != dict(value):
            raise ValueError("edit persistence receipt checksum is invalid")
        return receipt


__all__ = ["Task044EditPersistenceReceipt"]
