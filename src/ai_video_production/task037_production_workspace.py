"""TASK-037 user-facing Production Control projection.

The projection contains relationship metadata only.  It never embeds host paths,
media bytes, provider execution state or physical-delete controls.
"""

from __future__ import annotations

from typing import Any

from .errors import ProductError, ProductErrorCategory
from .production_control import CandidateLifecycle, ProductionControlRegistry, SlotStatus
from .serialization import canonical_json_bytes, sha256_bytes


class Task037ProductionWorkspaceProjection:
    @staticmethod
    def build(
        *,
        registry: ProductionControlRegistry,
        project_id: str,
        snapshot_sha256: str,
        persisted: bool,
    ) -> dict[str, Any]:
        foreign = sorted(
            slot.slot_id for slot in registry.slots.values() if slot.project_id != project_id
        )
        if foreign:
            raise ProductError(
                "ERR_PRODUCTION_WORKSPACE_PROJECT_MISMATCH",
                "Production Control snapshot contains Slots from another project",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"foreign_slot_ids": foreign},
            )

        slots: list[dict[str, Any]] = []
        for slot in sorted(registry.slots.values(), key=lambda item: (item.scene_id, item.slot_id)):
            candidates = sorted(
                (item for item in registry.candidates.values() if item.slot_id == slot.slot_id),
                key=lambda item: (item.candidate_version, item.candidate_id),
            )
            candidate_rows = []
            for candidate in candidates:
                actions: list[str] = []
                if candidate.lifecycle_state is CandidateLifecycle.CREATED:
                    actions.append("MARK_READY_FOR_AUDIT")
                elif (
                    candidate.lifecycle_state is CandidateLifecycle.ACCEPTED
                    and slot.status is SlotStatus.ACCEPTED
                    and slot.locked_candidate_id is None
                ):
                    actions.append("PREPARE_LOCK")
                candidate_rows.append({
                    **candidate.to_dict(),
                    "available_actions": actions,
                    "physical_delete_available": False,
                })
            slot_actions = []
            if slot.status not in {SlotStatus.LOCKED, SlotStatus.STALE}:
                slot_actions.append("REGISTER_CANDIDATE")
            slots.append({
                **slot.to_dict(),
                "candidates": candidate_rows,
                "available_actions": slot_actions,
            })

        body: dict[str, Any] = {
            "projection_version": "1.0.0",
            "task_owner": "TASK-037",
            "workspace": "PRODUCTION_CONTROL",
            "project_id": project_id,
            "snapshot_sha256": snapshot_sha256,
            "persisted": persisted,
            "slots": slots,
            "slot_count": len(slots),
            "candidate_count": len(registry.candidates),
            "locked_slot_count": sum(slot.status is SlotStatus.LOCKED for slot in registry.slots.values()),
            "stale_slot_count": sum(slot.status is SlotStatus.STALE for slot in registry.slots.values()),
            "human_final_authority_preserved": True,
            "media_bytes_embedded": False,
            "physical_delete_available": False,
            "provider_execution_started": False,
            "automatic_regeneration_started": False,
            "resolve_mutation_started": False,
        }
        body["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body
