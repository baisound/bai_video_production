"""TASK-039 continuity registry, Human resolution and production-control binding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .continuity_map import (
    ContinuityBoundaryType,
    ContinuityEdge,
    ContinuityValidationResult,
    ContinuityValidationService,
)
from .errors import ProductError, ProductErrorCategory
from .production_control import (
    DependencyEdge,
    DependencyKind,
    EntityRef,
    EntityType,
    ProductionControlRegistry,
)
from .serialization import canonical_json_bytes, sha256_bytes


@dataclass(frozen=True, slots=True)
class ContinuityResolution:
    edge_id: str
    target_asset_id: str
    target_asset_sha256: str
    status: str
    validation_status: str
    human_approved_by: str | None = None
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"PASS", "HUMAN_APPROVED", "FAIL", "HUMAN_REVIEW_REQUIRED"}:
            raise ValueError("continuity resolution status is invalid")
        if self.status == "HUMAN_APPROVED" and not (self.human_approved_by and self.human_approved_by.strip()):
            raise ValueError("HUMAN_APPROVED continuity requires an approver")

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "target_asset_id": self.target_asset_id,
            "target_asset_sha256": self.target_asset_sha256,
            "status": self.status,
            "validation_status": self.validation_status,
            "human_approved_by": self.human_approved_by,
            "reason_code": self.reason_code,
        }


class ContinuityRegistry:
    """Deterministic continuity state.

    DIRECT_CONTINUATION remains a hard exact-Asset/hash contract and cannot be
    human-overridden. SOFT_CONTINUITY may be explicitly human-approved after
    inspection. DISCONTINUOUS resolves automatically.
    """

    def __init__(self) -> None:
        self.edges: dict[str, ContinuityEdge] = {}
        self.resolutions: dict[str, ContinuityResolution] = {}

    def add_edge(self, edge: ContinuityEdge) -> None:
        if edge.edge_id in self.edges:
            raise ProductError(
                "ERR_CONTINUITY_EDGE_CONFLICT",
                "continuity edge_id already exists",
                ProductErrorCategory.STATE,
            )
        self.edges[edge.edge_id] = edge

    def inspect_target(
        self,
        edge_id: str,
        *,
        target_asset_id: str,
        target_asset_sha256: str,
    ) -> ContinuityResolution:
        edge = self.edges.get(edge_id)
        if edge is None:
            raise ProductError(
                "ERR_CONTINUITY_EDGE_NOT_FOUND",
                "continuity edge does not exist",
                ProductErrorCategory.STATE,
            )
        result: ContinuityValidationResult = ContinuityValidationService.validate_locked_target(
            edge,
            target_asset_id=target_asset_id,
            target_asset_sha256=target_asset_sha256,
        )
        resolution = ContinuityResolution(
            edge_id=edge.edge_id,
            target_asset_id=target_asset_id,
            target_asset_sha256=target_asset_sha256,
            status=result.status,
            validation_status=result.status,
            reason_code=result.reason_code,
        )
        self.resolutions[edge_id] = resolution
        return resolution

    def human_approve_soft(self, edge_id: str, *, approved_by: str) -> ContinuityResolution:
        edge = self.edges.get(edge_id)
        current = self.resolutions.get(edge_id)
        if edge is None or current is None:
            raise ProductError(
                "ERR_CONTINUITY_REVIEW_STATE_REQUIRED",
                "Soft continuity approval requires an inspected target",
                ProductErrorCategory.STATE,
            )
        if edge.boundary_type is not ContinuityBoundaryType.SOFT_CONTINUITY:
            raise ProductError(
                "ERR_CONTINUITY_HARD_RULE_NOT_OVERRIDABLE",
                "Only SOFT_CONTINUITY may be resolved by Human inspection; DIRECT_CONTINUATION exact identity is mandatory",
                ProductErrorCategory.AUTHORIZATION,
            )
        if current.validation_status != "HUMAN_REVIEW_REQUIRED":
            raise ProductError(
                "ERR_CONTINUITY_HUMAN_APPROVAL_NOT_REQUIRED",
                "Current continuity state is not awaiting Human inspection",
                ProductErrorCategory.STATE,
            )
        if not approved_by.strip():
            raise ProductError(
                "ERR_CONTINUITY_APPROVER_REQUIRED",
                "Soft continuity approval requires a non-empty Human identity",
                ProductErrorCategory.AUTHORIZATION,
            )
        resolved = ContinuityResolution(
            edge_id=current.edge_id,
            target_asset_id=current.target_asset_id,
            target_asset_sha256=current.target_asset_sha256,
            status="HUMAN_APPROVED",
            validation_status=current.validation_status,
            human_approved_by=approved_by.strip(),
            reason_code=None,
        )
        self.resolutions[edge_id] = resolved
        return resolved

    def require_generation_safe(self, edge_id: str) -> ContinuityResolution:
        edge = self.edges.get(edge_id)
        current = self.resolutions.get(edge_id)
        if edge is None or current is None:
            raise ProductError(
                "ERR_CONTINUITY_GENERATION_BLOCKED",
                "Continuity target has not been inspected",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={"edge_id": edge_id},
            )
        if current.status in {"PASS", "HUMAN_APPROVED"}:
            return current
        raise ProductError(
            "ERR_CONTINUITY_GENERATION_BLOCKED",
            "Continuity boundary is unresolved for downstream generation",
            ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            details={"edge_id": edge_id, "status": current.status, "reason_code": current.reason_code},
        )

    def to_dict(self) -> dict[str, Any]:
        body = {
            "registry_version": "1.0.0",
            "task_owner": "TASK-039",
            "edges": [self.edges[key].to_dict() for key in sorted(self.edges)],
            "resolutions": [self.resolutions[key].to_dict() for key in sorted(self.resolutions)],
            "automatic_regeneration_started": False,
        }
        body["registry_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class ContinuityProductionControlBinding:
    """Map a continuity edge into TASK-037's stale dependency graph."""

    @staticmethod
    def bind(registry: ProductionControlRegistry, edge: ContinuityEdge) -> DependencyEdge:
        dependency = DependencyEdge(
            edge_id=f"continuity:{edge.edge_id}",
            from_ref=EntityRef(EntityType.SLOT, edge.from_slot_id),
            to_ref=EntityRef(EntityType.SLOT, edge.to_slot_id),
            dependency_kind=DependencyKind.CONTINUITY,
            from_hash=edge.from_asset_sha256,
            continuity_boundary=edge.boundary_type.value,
        )
        registry.add_dependency(dependency)
        return dependency
