"""TASK-036 P-UX-2D2 typed Final Review approval receipt contract.

The contract records one explicit Human approval over an exact P-UX-2D1
readiness projection.  It owns no persistence, export, render or publication.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")
_SOURCE_KEYS = ("audit", "production", "project_manifest", "timeline", "visual_handoff")
_GATE_KEYS = ("AUDIO_COMPLETION", "EDIT_PERSISTENCE", "PRIVACY", "RESOURCE", "RIGHTS_LICENSE")


def _identity(value: object, name: str) -> str:
    if not isinstance(value, str) or not _IDENTITY.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


@dataclass(frozen=True, slots=True)
class FinalReviewApprovalReceipt:
    receipt_id: str
    project_id: str
    project_manifest_sha256: str
    timeline_sha256: str
    readiness_projection_sha256: str
    source_snapshot_sha256s: tuple[tuple[str, str], ...]
    external_gate_receipt_sha256s: tuple[tuple[str, str], ...]
    approved_by: str
    approved_at: str

    def __post_init__(self) -> None:
        _identity(self.receipt_id, "receipt_id")
        _identity(self.project_id, "project_id")
        _identity(self.approved_by, "approved_by")
        if not isinstance(self.approved_at, str) or not _TIMESTAMP.fullmatch(self.approved_at):
            raise ValueError("approved_at must be canonical UTC")
        for value, name in (
            (self.project_manifest_sha256, "project_manifest_sha256"),
            (self.timeline_sha256, "timeline_sha256"),
            (self.readiness_projection_sha256, "readiness_projection_sha256"),
        ):
            validate_sha256(value, field_name=name)
        self._validate_pairs(self.source_snapshot_sha256s, _SOURCE_KEYS, "source snapshot")
        self._validate_pairs(self.external_gate_receipt_sha256s, _GATE_KEYS, "external gate")
        if dict(self.source_snapshot_sha256s)["project_manifest"] != self.project_manifest_sha256:
            raise ValueError("approval crosses project manifest")
        if dict(self.source_snapshot_sha256s)["timeline"] != self.timeline_sha256:
            raise ValueError("approval crosses timeline")

    @staticmethod
    def _validate_pairs(
        pairs: tuple[tuple[str, str], ...], expected: tuple[str, ...], name: str,
    ) -> None:
        if not isinstance(pairs, tuple) or any(
            not isinstance(pair, tuple) or len(pair) != 2 for pair in pairs
        ):
            raise ValueError(f"{name} coordinates must be immutable pairs")
        keys = tuple(key for key, _ in pairs)
        if keys != expected:
            raise ValueError(f"{name} coordinates must equal the closed key set")
        for key, value in pairs:
            validate_sha256(value, field_name=f"{name} {key}")

    @classmethod
    def from_readiness(
        cls,
        readiness: Mapping[str, object],
        *,
        receipt_id: str,
        approved_by: str,
        approved_at: str,
    ) -> "FinalReviewApprovalReceipt":
        source = _mapping(readiness, "readiness")
        if source.get("available") is not True or source.get("state") != "READY_FOR_TYPED_FINAL_REVIEW":
            raise ValueError("Final Review approval requires exact ready state")
        if source.get("product_blockers") != [] or source.get("external_blockers") != []:
            raise ValueError("Final Review approval cannot contain blockers")
        if any(source.get(flag) is not False for flag in (
            "final_approval_created", "export_job_created", "render_or_publish_started",
            "human_decision_authorized",
        )):
            raise ValueError("readiness projection carries forbidden authority")
        project_id = _identity(source.get("project_id"), "readiness.project_id")
        snapshots = _mapping(source.get("source_snapshots"), "source_snapshots")
        if set(snapshots) != set(_SOURCE_KEYS):
            raise ValueError("source snapshot key set is incomplete")
        source_pairs = tuple((key, str(snapshots[key])) for key in _SOURCE_KEYS)
        gates = source.get("external_gates")
        if not isinstance(gates, (list, tuple)) or len(gates) != len(_GATE_KEYS):
            raise ValueError("external gate registry is incomplete")
        gate_map: dict[str, Mapping[str, object]] = {}
        for raw in gates:
            gate = _mapping(raw, "external gate")
            gate_id = gate.get("gate_id")
            if not isinstance(gate_id, str) or gate_id not in _GATE_KEYS or gate_id in gate_map:
                raise ValueError("external gate registry is not exact")
            if gate.get("state") != "PASS":
                raise ValueError("all external gates must PASS")
            gate_map[gate_id] = gate
        if set(gate_map) != set(_GATE_KEYS):
            raise ValueError("external gate registry is incomplete")
        gate_pairs = tuple((key, str(gate_map[key].get("receipt_sha256"))) for key in _GATE_KEYS)
        return cls(
            receipt_id=receipt_id,
            project_id=project_id,
            project_manifest_sha256=str(snapshots["project_manifest"]),
            timeline_sha256=str(snapshots["timeline"]),
            readiness_projection_sha256=str(source.get("projection_sha256")),
            source_snapshot_sha256s=source_pairs,
            external_gate_receipt_sha256s=gate_pairs,
            approved_by=approved_by,
            approved_at=approved_at,
        )

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "receipt_version": "1.0.0",
            "task_owner": "TASK-036/P-UX-2D2",
            "receipt_id": self.receipt_id,
            "project_id": self.project_id,
            "project_manifest_sha256": self.project_manifest_sha256,
            "timeline_sha256": self.timeline_sha256,
            "readiness_projection_sha256": self.readiness_projection_sha256,
            "source_snapshot_sha256s": dict(self.source_snapshot_sha256s),
            "external_gate_receipt_sha256s": dict(self.external_gate_receipt_sha256s),
            "decision": "APPROVE",
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "export_job_created": False,
            "render_or_publish_started": False,
        }
        return {**body, "final_approval_receipt_sha256": sha256_bytes(canonical_json_bytes(body))}

    @property
    def final_approval_receipt_sha256(self) -> str:
        return self.to_dict()["final_approval_receipt_sha256"]


__all__ = ["FinalReviewApprovalReceipt"]
