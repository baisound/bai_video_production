"""TASK-036 read-only Production Control workspace projection.

The projection adapts the cross-task ProductionDashboardReport into a compact
NLE side-panel model.  Timeline/Viewer remain the primary editing canvas; this
module intentionally exposes no mutation commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .production_dashboard import ProductionDashboardReport, SceneProductionSummary
from .serialization import canonical_json_bytes, sha256_bytes


@dataclass(frozen=True, slots=True)
class ProductionWorkspaceSceneRow:
    scene_id: str
    narrative_role: str
    status: str
    locked_slots: int
    required_slots: int
    candidate_count: int
    attention_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "narrative_role": self.narrative_role,
            "status": self.status,
            "locked_slots": self.locked_slots,
            "required_slots": self.required_slots,
            "candidate_count": self.candidate_count,
            "attention_reasons": list(self.attention_reasons),
        }


@dataclass(frozen=True, slots=True)
class Task036ProductionWorkspaceProjection:
    plan_id: str
    plan_sha256: str
    status: str
    budget: dict[str, Any]
    scenes: tuple[ProductionWorkspaceSceneRow, ...]

    @classmethod
    def from_dashboard(cls, report: ProductionDashboardReport) -> "Task036ProductionWorkspaceProjection":
        return cls(
            plan_id=report.plan_id,
            plan_sha256=report.approved_plan_sha256,
            status=report.status,
            budget=dict(report.budget),
            scenes=tuple(cls._scene_row(scene) for scene in report.scenes),
        )

    @staticmethod
    def _scene_row(scene: SceneProductionSummary) -> ProductionWorkspaceSceneRow:
        return ProductionWorkspaceSceneRow(
            scene_id=scene.scene_id,
            narrative_role=scene.narrative_role,
            status=scene.status,
            locked_slots=scene.locked_slot_count,
            required_slots=scene.required_slot_count,
            candidate_count=scene.candidate_count,
            attention_reasons=scene.attention_reasons,
        )

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "projection_version": "1.0.0",
            "task_owner": "TASK-036",
            "workspace": "PRODUCTION_CONTROL",
            "status": self.status,
            "plan_id": self.plan_id,
            "plan_sha256": self.plan_sha256,
            "budget": dict(self.budget),
            "scenes": [scene.to_dict() for scene in self.scenes],
            "layout_contract": {
                "primary_canvas": "VIEWER_AND_TIMELINE",
                "production_control_role": "SIDEPANEL_OR_WORKSPACE",
                "ai_chat_is_primary_canvas": False,
            },
            "available_commands": [],
            "read_only": True,
            "automatic_repair_performed": False,
            "provider_execution_started": False,
        }
        body["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body
