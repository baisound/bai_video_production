"""TASK-036 P-UX-2C1 deterministic visual-generation handoff projection.

This module composes existing Product snapshots.  It owns no durable state and
does not authorize generation, Human decisions, Asset publication or editing.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from .serialization import canonical_json_bytes, sha256_bytes


_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")
_VISUAL_SLOT_KINDS = frozenset({
    "START_FRAME", "END_FRAME", "CHARACTER_REFERENCE", "SPACE_REFERENCE",
    "COMPOSITION_REFERENCE", "VIDEO", "VFX",
})
_ADOPTED_SLOT_STATES = frozenset({"ACCEPTED", "LOCKED"})
_MAX_SLOTS = 256
_MAX_ROWS = 1024


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def _rows(value: object, name: str, maximum: int = _MAX_ROWS) -> Sequence[object]:
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


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _unique(rows: Sequence[object], key_name: str, label: str) -> dict[str, Mapping[str, object]]:
    result: dict[str, Mapping[str, object]] = {}
    for raw in rows:
        row = _mapping(raw, label)
        key = _text(row.get(key_name), f"{label}.{key_name}")
        if key in result:
            raise ValueError(f"duplicate {label} {key_name}")
        result[key] = row
    return result


def _production_slots(production: Mapping[str, object]) -> Sequence[object]:
    slots = production.get("slots")
    if slots is None:
        workspace = _mapping(production.get("workspace", {}), "production.workspace")
        slots = workspace.get("slots", [])
    return _rows(slots, "production slots", _MAX_SLOTS)


def _latest_prompts(prompt: Mapping[str, object]) -> tuple[dict[str, Mapping[str, object]], dict[str, int]]:
    grouped: dict[str, list[Mapping[str, object]]] = {}
    for raw in _rows(prompt.get("prompts", []), "prompts"):
        row = _mapping(raw, "prompt")
        slot_id = _text(row.get("slot_id"), "prompt.slot_id")
        version = _positive_int(row.get("prompt_version"), "prompt.prompt_version")
        grouped.setdefault(slot_id, []).append(row)
    latest: dict[str, Mapping[str, object]] = {}
    stale: dict[str, int] = {}
    for slot_id, values in grouped.items():
        versions = [int(row["prompt_version"]) for row in values]
        if len(versions) != len(set(versions)):
            raise ValueError("duplicate prompt version for slot")
        selected = max(values, key=lambda row: int(row["prompt_version"]))
        latest[slot_id] = selected
        stale[slot_id] = len(values) - 1
    return latest, stale


def _latest_by(rows: Sequence[object], identity: str, label: str) -> dict[str, Mapping[str, object]]:
    latest: dict[str, Mapping[str, object]] = {}
    for raw in rows:
        row = _mapping(raw, label)
        key = _text(row.get(identity), f"{label}.{identity}")
        if key in latest:
            raise ValueError(f"duplicate {label} {identity}")
        latest[key] = row
    return latest


def _slot_state(
    *,
    slot: Mapping[str, object],
    feasibility: Mapping[str, object] | None,
    prompt: Mapping[str, object] | None,
    queue_entry: Mapping[str, object] | None,
    execution: Mapping[str, object] | None,
    eligible_output: Mapping[str, object] | None,
    adoption: Mapping[str, object] | None,
) -> tuple[str, list[str]]:
    status = _text(slot.get("status"), "slot.status")
    candidates = [_mapping(item, "candidate") for item in _rows(slot.get("candidates", []), "candidates")]
    current_candidates = [item for item in candidates if item.get("lifecycle_state") in {"ACCEPTED", "LOCKED"}]
    if status == "STALE" or slot.get("stale_state") == "STALE":
        return "STALE_BLOCKED", ["SLOT_STALE"]
    if feasibility is None:
        return "FEASIBILITY_REQUIRED", ["FEASIBILITY_RECEIPT_MISSING"]
    feasibility_state = _text(feasibility.get("feasibility_status"), "feasibility_status")
    if feasibility_state != "PASS":
        return "FEASIBILITY_BLOCKED", [f"FEASIBILITY_{feasibility_state}"]
    if prompt is None:
        return "PROMPT_REQUIRED", ["PROMPT_RECEIPT_MISSING"]
    if status in _ADOPTED_SLOT_STATES:
        if len(current_candidates) != 1:
            return "CORRUPT_OR_INCOMPLETE", ["ADOPTED_CANDIDATE_NOT_EXACT1"]
        return f"{status}_ASSET", []
    if adoption is not None:
        state = _text(adoption.get("state"), "adoption.state")
        if state == "READY_FOR_AUDIT":
            return "READY_FOR_AUDIT", ["HUMAN_ASSET_DECISION_REQUIRED"]
        if state == "FAILED_KNOWN":
            return "ADOPTION_FAILED_KNOWN", ["ADOPTION_FAILED_KNOWN"]
        return "ADOPTION_RECOVERY_REQUIRED", ["ADOPTION_RECOVERY_REQUIRED"]
    if execution is not None:
        state = _text(execution.get("state"), "execution.state")
        if state == "COMPLETED":
            if eligible_output is None:
                return "OUTPUT_ADOPTION_UNKNOWN", ["OUTPUT_ADOPTION_RECEIPT_MISSING"]
            adoption_status = _text(eligible_output.get("adoption_status"), "eligible_output.adoption_status")
            if adoption_status == "READY":
                return "OUTPUT_READY_FOR_ADOPTION", ["OUTPUT_ADOPTION_REQUIRED"]
            return "OUTPUT_ADOPTION_BLOCKED", [adoption_status]
        if state == "DISPATCHING":
            return "EXECUTION_RECOVERY_REQUIRED", ["NO_AUTOMATIC_RETRY"]
        if state == "FAILED_KNOWN":
            return "EXECUTION_FAILED_KNOWN", ["EXECUTION_FAILED_KNOWN"]
        if state == "UNKNOWN":
            return "EXECUTION_UNKNOWN", ["EXECUTION_UNKNOWN"]
        return "EXECUTION_IN_PROGRESS", ["EXECUTION_TERMINAL_REQUIRED"]
    if queue_entry is not None:
        return "QUEUED_NOT_EXECUTED", ["SEPARATE_EXECUTION_CONFIRMATION_REQUIRED"]
    return "PROMPT_READY", ["QUEUE_ADMISSION_REQUIRED"]


class Task036VisualGenerationHandoffProjection:
    """Build an immutable, fail-closed visual lineage from existing receipts."""

    @classmethod
    def project(
        cls,
        *,
        production_snapshot: Mapping[str, object],
        safety_snapshot: Mapping[str, object],
        prompt_snapshot: Mapping[str, object],
        queue_snapshot: Mapping[str, object],
    ) -> dict[str, Any]:
        production = _mapping(production_snapshot, "production_snapshot")
        safety = _mapping(safety_snapshot, "safety_snapshot")
        prompt = _mapping(prompt_snapshot, "prompt_snapshot")
        queue = _mapping(queue_snapshot, "queue_snapshot")
        project_id = _text(production.get("project_id"), "project_id")
        for name, source in (("safety", safety), ("prompt", prompt), ("queue", queue)):
            if _text(source.get("project_id"), f"{name}.project_id") != project_id:
                raise ValueError(f"{name} crosses project scope")
        source_snapshots = {
            "production": _sha(production.get("snapshot_sha256"), "production snapshot"),
            "safety": _sha(safety.get("safety_snapshot_sha256"), "safety snapshot"),
            "prompt": _sha(prompt.get("prompt_snapshot_sha256"), "prompt snapshot"),
            "queue": _sha(queue.get("queue_snapshot_sha256"), "queue snapshot"),
        }
        execution_control = _mapping(queue.get("execution_control", {}), "execution_control")
        adoption_control = _mapping(queue.get("output_adoption_control", {}), "output_adoption_control")
        for name, source in (("execution", execution_control), ("adoption", adoption_control)):
            if _text(source.get("project_id"), f"{name}.project_id") != project_id:
                raise ValueError(f"{name} crosses project scope")
        if _sha(execution_control.get("queue_snapshot_sha256"), "execution queue snapshot") != source_snapshots["queue"]:
            raise ValueError("execution crosses queue snapshot")
        source_snapshots["execution"] = _sha(execution_control.get("execution_snapshot_sha256"), "execution snapshot")
        source_snapshots["adoption"] = _sha(adoption_control.get("adoption_snapshot_sha256"), "adoption snapshot")

        all_slots = _unique(_production_slots(production), "slot_id", "slot")
        slots = {key: row for key, row in all_slots.items() if _text(row.get("slot_kind"), "slot.slot_kind") in _VISUAL_SLOT_KINDS}
        feasibility: dict[str, Mapping[str, object]] = {}
        for raw in _rows(safety.get("scenes", []), "safety scenes", _MAX_SLOTS):
            row = _mapping(raw, "safety scene")
            scene = _mapping(row.get("scene"), "safety scene identity")
            scene_id = _text(scene.get("scene_id"), "safety scene_id")
            if scene_id in feasibility:
                raise ValueError("duplicate safety scene")
            feasibility[scene_id] = row
        prompts, stale_prompt_counts = _latest_prompts(prompt)
        if any(slot_id not in all_slots for slot_id in prompts):
            raise ValueError("prompt references an unknown production slot")
        queue_rows = _rows(queue.get("entries", []), "queue entries")
        queue_by_prompt: dict[tuple[str, int], Mapping[str, object]] = {}
        for raw in queue_rows:
            row = _mapping(raw, "queue entry")
            key = (_text(row.get("prompt_id"), "queue.prompt_id"), _positive_int(row.get("prompt_version"), "queue.prompt_version"))
            if key in queue_by_prompt:
                raise ValueError("duplicate queue entry for prompt version")
            queue_by_prompt[key] = row
        executions = _latest_by(_rows(execution_control.get("latest_executions", []), "executions"), "queue_entry_id", "execution")
        eligible = _unique(_rows(adoption_control.get("eligible_completed_outputs", []), "eligible outputs"), "execution_id", "eligible output")
        adoptions = _latest_by(_rows(adoption_control.get("latest_adoptions", []), "adoptions"), "execution_id", "adoption")

        rows: list[dict[str, Any]] = []
        for slot_id, slot in sorted(slots.items(), key=lambda item: (_text(item[1].get("scene_id"), "slot.scene_id"), item[0])):
            scene_id = _text(slot.get("scene_id"), "slot.scene_id")
            current_prompt = prompts.get(slot_id)
            queue_entry = None
            if current_prompt is not None:
                if _text(current_prompt.get("scene_id"), "prompt.scene_id") != scene_id:
                    raise ValueError("prompt crosses scene scope")
                queue_entry = queue_by_prompt.get((_text(current_prompt.get("prompt_id"), "prompt.prompt_id"), int(current_prompt["prompt_version"])))
                if queue_entry is not None and (_text(queue_entry.get("slot_id"), "queue.slot_id") != slot_id or _text(queue_entry.get("scene_id"), "queue.scene_id") != scene_id):
                    raise ValueError("queue entry crosses scene or slot scope")
            execution = executions.get(_text(queue_entry.get("queue_entry_id"), "queue.queue_entry_id")) if queue_entry is not None else None
            eligible_output = eligible.get(_text(execution.get("execution_id"), "execution.execution_id")) if execution is not None else None
            adoption = adoptions.get(_text(execution.get("execution_id"), "execution.execution_id")) if execution is not None else None
            state, blockers = _slot_state(
                slot=slot, feasibility=feasibility.get(scene_id), prompt=current_prompt,
                queue_entry=queue_entry, execution=execution,
                eligible_output=eligible_output, adoption=adoption,
            )
            rows.append({
                "scene_id": scene_id,
                "slot_id": slot_id,
                "slot_kind": _text(slot.get("slot_kind"), "slot.slot_kind"),
                "required": bool(slot.get("required", False)),
                "state": state,
                "blockers": blockers,
                "prompt_id": current_prompt.get("prompt_id") if current_prompt else None,
                "prompt_version": current_prompt.get("prompt_version") if current_prompt else None,
                "stale_prompt_count": stale_prompt_counts.get(slot_id, 0),
                "queue_entry_id": queue_entry.get("queue_entry_id") if queue_entry else None,
                "execution_id": execution.get("execution_id") if execution else None,
                "adoption_id": adoption.get("adoption_id") if adoption else None,
            })

        adopted_states = {"ACCEPTED_ASSET", "LOCKED_ASSET"}
        required_rows = [row for row in rows if row["required"]]
        body: dict[str, Any] = {
            "projection_version": "1.0.0",
            "project_id": project_id,
            "source_snapshots": source_snapshots,
            "rows": rows,
            "visual_slot_count": len(rows),
            "required_visual_slot_count": len(required_rows),
            "required_blocker_count": sum(row["state"] not in adopted_states for row in required_rows),
            "all_required_visual_slots_adopted": bool(required_rows) and all(row["state"] in adopted_states for row in required_rows),
            "delegated_audio_owner": "DEVELOPER2",
            "audio_slot_counted": 0,
            "durable_state_owned": False,
            "provider_execution_authorized": False,
            "human_decision_created": False,
            "asset_or_timeline_mutation_started": False,
        }
        body["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


__all__ = ["Task036VisualGenerationHandoffProjection"]
