"""TASK-036 P-UX-2D1 deterministic Final Review readiness projection.

This module composes existing Product receipts.  It owns no approval, export,
render, publication or Human-decision authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from .serialization import canonical_json_bytes, sha256_bytes


_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")
_REQUIRED_EXTERNAL_GATES = (
    "AUDIO_COMPLETION",
    "EDIT_PERSISTENCE",
    "PRIVACY",
    "RESOURCE",
    "RIGHTS_LICENSE",
)
_GATE_OWNERS = {
    "AUDIO_COMPLETION": "DEVELOPER2",
    "EDIT_PERSISTENCE": "TASK-044",
    "PRIVACY": "TASK-016",
    "RESOURCE": "TASK-020",
    "RIGHTS_LICENSE": "TASK-003/027",
}
_MAX_SLOTS = 256
_MAX_CANDIDATES = 1024
_MAX_EXPORT_ROWS = 256


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def _rows(value: object, name: str, maximum: int) -> Sequence[object]:
    if not isinstance(value, (list, tuple)) or len(value) > maximum:
        raise ValueError(f"{name} must be a bounded sequence")
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 256:
        raise ValueError(f"{name} must be non-empty bounded text")
    return value


def _sha(value: object, name: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise ValueError(f"{name} must be a canonical SHA-256")
    return value


def _available(source: Mapping[str, object], name: str) -> None:
    if source.get("available") is not True:
        raise ValueError(f"{name} source must be available")


def _production_slots(production: Mapping[str, object]) -> Sequence[object]:
    slots = production.get("slots")
    if slots is None:
        slots = _mapping(production.get("workspace", {}), "production.workspace").get("slots", [])
    return _rows(slots, "production slots", _MAX_SLOTS)


def _blocker(code: str, owner: str, identity: str | None = None) -> dict[str, object]:
    return {"code": code, "owner": owner, "identity": identity}


class Task036FinalReviewReadinessProjection:
    """Project exact Final Review blockers without manufacturing approval."""

    @classmethod
    def project(
        cls,
        *,
        production_snapshot: Mapping[str, object],
        audit_snapshot: Mapping[str, object],
        visual_handoff_snapshot: Mapping[str, object],
        timeline_snapshot: Mapping[str, object],
        export_snapshot: Mapping[str, object],
        external_gate_receipts: Sequence[Mapping[str, object]] = (),
    ) -> dict[str, Any]:
        production = _mapping(production_snapshot, "production_snapshot")
        audit = _mapping(audit_snapshot, "audit_snapshot")
        visual = _mapping(visual_handoff_snapshot, "visual_handoff_snapshot")
        timeline = _mapping(timeline_snapshot, "timeline_snapshot")
        export = _mapping(export_snapshot, "export_snapshot")
        for name, source in (
            ("production", production), ("audit", audit), ("visual", visual),
            ("timeline", timeline), ("export", export),
        ):
            _available(source, name)

        project_id = _text(production.get("project_id"), "production.project_id")
        production_sha = _sha(production.get("snapshot_sha256"), "production snapshot")
        if _text(audit.get("project_id"), "audit.project_id") != project_id:
            raise ValueError("audit crosses project scope")
        if _sha(audit.get("production_snapshot_sha256"), "audit production snapshot") != production_sha:
            raise ValueError("audit crosses production snapshot")
        audit_sha = _sha(audit.get("audit_snapshot_sha256"), "audit snapshot")
        if _text(visual.get("project_id"), "visual.project_id") != project_id:
            raise ValueError("visual handoff crosses project scope")
        visual_sources = _mapping(visual.get("source_snapshots"), "visual source snapshots")
        if _sha(visual_sources.get("production"), "visual production snapshot") != production_sha:
            raise ValueError("visual handoff crosses production snapshot")
        visual_sha = _sha(visual.get("projection_sha256"), "visual projection")
        timeline_sha = _sha(timeline.get("projected_timeline_sha256"), "projected timeline")
        project_manifest_sha = timeline.get("project_manifest_sha256")
        if project_manifest_sha is not None:
            project_manifest_sha = _sha(project_manifest_sha, "project manifest")

        product_blockers: list[dict[str, object]] = []
        slots = [_mapping(row, "production slot") for row in _production_slots(production)]
        slot_ids: set[str] = set()
        required_slots = []
        for slot in slots:
            slot_id = _text(slot.get("slot_id"), "slot.slot_id")
            if slot_id in slot_ids:
                raise ValueError("duplicate production slot")
            slot_ids.add(slot_id)
            if bool(slot.get("required", False)):
                required_slots.append(slot)
                status = _text(slot.get("status"), "slot.status")
                if status != "LOCKED":
                    product_blockers.append(_blocker("REQUIRED_SLOT_NOT_LOCKED", "TASK-037", slot_id))
            if slot.get("status") == "STALE" or slot.get("stale_state") == "STALE":
                product_blockers.append(_blocker("STALE_PRODUCTION_SLOT", "TASK-037", slot_id))
        if not required_slots:
            product_blockers.append(_blocker("REQUIRED_SLOT_SET_EMPTY", "TASK-037"))

        workspace = _mapping(audit.get("workspace", {}), "audit.workspace")
        candidates = [_mapping(row, "audit candidate") for row in _rows(
            workspace.get("candidates", []), "audit candidates", _MAX_CANDIDATES,
        )]
        candidate_ids: set[str] = set()
        for candidate in candidates:
            candidate_id = _text(candidate.get("candidate_id"), "candidate.candidate_id")
            if candidate_id in candidate_ids:
                raise ValueError("duplicate audit candidate")
            candidate_ids.add(candidate_id)
            if _rows(candidate.get("available_human_actions", []), "available human actions", 16):
                product_blockers.append(_blocker("HUMAN_ASSET_DECISION_REQUIRED", "TASK-038", candidate_id))
            if candidate.get("critical_violation") is True:
                product_blockers.append(_blocker("CRITICAL_AUDIT_VIOLATION", "TASK-038", candidate_id))
        if _mapping(audit.get("recovery", {}), "audit.recovery").get("required") is True:
            product_blockers.append(_blocker("AUDIT_RECOVERY_REQUIRED", "TASK-038"))

        if visual.get("all_required_visual_slots_adopted") is not True:
            product_blockers.append(_blocker("VISUAL_HANDOFF_INCOMPLETE", "TASK-036/TASK-013"))
        blocker_count = visual.get("required_blocker_count")
        if isinstance(blocker_count, bool) or not isinstance(blocker_count, int) or blocker_count < 0:
            raise ValueError("visual required blocker count must be a non-negative integer")
        if blocker_count:
            product_blockers.append(_blocker("VISUAL_REQUIRED_BLOCKERS_PRESENT", "TASK-036/TASK-013"))
        if project_manifest_sha is None:
            product_blockers.append(_blocker("TIMELINE_PROJECT_MANIFEST_UNBOUND", "TASK-043/044"))

        export_rows = [_mapping(row, "export row") for row in _rows(
            export.get("rows", []), "export rows", _MAX_EXPORT_ROWS,
        )]
        export_ids: set[str] = set()
        for row in export_rows:
            job_id = _text(row.get("job_id"), "export.job_id")
            if job_id in export_ids:
                raise ValueError("duplicate export job")
            export_ids.add(job_id)
        if export_rows:
            product_blockers.append(_blocker("UNSCOPED_EXPORT_JOB_PRESENT", "TASK-044"))

        gates: dict[str, Mapping[str, object]] = {}
        for raw in _rows(external_gate_receipts, "external gate receipts", len(_REQUIRED_EXTERNAL_GATES)):
            receipt = _mapping(raw, "external gate receipt")
            gate_id = _text(receipt.get("gate_id"), "gate.gate_id")
            if gate_id not in _REQUIRED_EXTERNAL_GATES:
                raise ValueError("unknown external gate")
            if gate_id in gates:
                raise ValueError("duplicate external gate")
            if _text(receipt.get("project_id"), "gate.project_id") != project_id:
                raise ValueError("external gate crosses project scope")
            if _sha(receipt.get("timeline_sha256"), "gate timeline") != timeline_sha:
                raise ValueError("external gate crosses timeline scope")
            _sha(receipt.get("receipt_sha256"), "gate receipt")
            state = _text(receipt.get("state"), "gate.state")
            if state not in {"PASS", "FAIL", "UNKNOWN", "STALE", "REVOKED"}:
                raise ValueError("external gate state is not closed")
            gates[gate_id] = receipt

        external_blockers: list[dict[str, object]] = []
        gate_rows = []
        for gate_id in _REQUIRED_EXTERNAL_GATES:
            receipt = gates.get(gate_id)
            state = "MISSING" if receipt is None else str(receipt["state"])
            gate_rows.append({
                "gate_id": gate_id,
                "owner": _GATE_OWNERS[gate_id],
                "state": state,
                "receipt_sha256": None if receipt is None else receipt["receipt_sha256"],
            })
            if state != "PASS":
                external_blockers.append(_blocker(f"{gate_id}_{state}", _GATE_OWNERS[gate_id]))

        product_blockers.sort(key=lambda item: (str(item["code"]), str(item["identity"] or "")))
        external_blockers.sort(key=lambda item: str(item["code"]))
        state = (
            "BLOCKED_PRODUCT_GATES" if product_blockers
            else "BLOCKED_EXTERNAL_GATES" if external_blockers
            else "READY_FOR_TYPED_FINAL_REVIEW"
        )
        body: dict[str, Any] = {
            "projection_version": "1.0.0",
            "project_id": project_id,
            "state": state,
            "source_snapshots": {
                "production": production_sha,
                "audit": audit_sha,
                "visual_handoff": visual_sha,
                "timeline": timeline_sha,
                "project_manifest": project_manifest_sha,
            },
            "required_slot_count": len(required_slots),
            "audit_candidate_count": len(candidates),
            "export_job_count": len(export_rows),
            "product_blockers": product_blockers,
            "external_gates": gate_rows,
            "external_blockers": external_blockers,
            "delegated_audio_owner": "DEVELOPER2",
            "final_approval_created": False,
            "export_job_created": False,
            "render_or_publish_started": False,
            "human_decision_authorized": False,
        }
        body["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


__all__ = ["Task036FinalReviewReadinessProjection"]
