"""TASK-039 Continuity Workspace projection and soft-boundary Human approval.

DIRECT_CONTINUATION remains a non-overridable exact Asset/hash contract.  Only
an inspected SOFT_CONTINUITY target can receive a one-shot Human approval, and
that approval is bound to the exact currently locked Production target bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
import secrets
from typing import Any, Callable

from .continuity_map import ContinuityBoundaryType
from .continuity_registry import ContinuityRegistry
from .errors import ProductError, ProductErrorCategory
from .production_control import CandidateLifecycle, ProductionControlRegistry, SlotStatus
from .serialization import canonical_json_bytes, sha256_bytes


TokenFactory = Callable[[], str]


def _resolution_hash(value: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(value))


@dataclass(slots=True)
class _ContinuityConfirmation:
    confirmation_id: str
    edge_id: str
    target_candidate_id: str
    target_asset_sha256: str
    resolution_sha256: str
    consumed: bool = False


class Task039ContinuityWorkspaceProjection:
    @staticmethod
    def build(*, continuity: ContinuityRegistry, production: ProductionControlRegistry) -> dict[str, Any]:
        rows = []
        for edge in sorted(continuity.edges.values(), key=lambda item: item.edge_id):
            source = production.candidates.get(edge.from_candidate_id)
            from_slot = production.slots.get(edge.from_slot_id)
            to_slot = production.slots.get(edge.to_slot_id)
            if source is None or from_slot is None or to_slot is None:
                raise ProductError(
                    "ERR_CONTINUITY_WORKSPACE_PRODUCTION_REFERENCE_MISSING",
                    "Continuity Workspace edge references missing Production state",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"edge_id": edge.edge_id},
                )
            if source.asset_id != edge.from_asset_id or source.asset_sha256 != edge.from_asset_sha256:
                raise ProductError(
                    "ERR_CONTINUITY_WORKSPACE_SOURCE_MISMATCH",
                    "Continuity source no longer matches exact Production Candidate bytes",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"edge_id": edge.edge_id},
                )
            resolution = continuity.resolutions.get(edge.edge_id)
            target_candidate = None
            if to_slot.locked_candidate_id is not None:
                target_candidate = production.candidates.get(to_slot.locked_candidate_id)
            human_action_available = (
                edge.boundary_type is ContinuityBoundaryType.SOFT_CONTINUITY
                and resolution is not None
                and resolution.validation_status == "HUMAN_REVIEW_REQUIRED"
                and resolution.status == "HUMAN_REVIEW_REQUIRED"
                and to_slot.status is SlotStatus.LOCKED
                and target_candidate is not None
                and target_candidate.lifecycle_state is CandidateLifecycle.LOCKED
                and target_candidate.asset_id == resolution.target_asset_id
                and target_candidate.asset_sha256 == resolution.target_asset_sha256
            )
            rows.append({
                **edge.to_dict(),
                "source_lifecycle_state": source.lifecycle_state.value,
                "target_slot_status": to_slot.status.value,
                "target_locked_candidate_id": to_slot.locked_candidate_id,
                "resolution": None if resolution is None else resolution.to_dict(),
                "human_soft_approval_available": human_action_available,
                "direct_continuation_human_override_allowed": False,
            })
        body: dict[str, Any] = {
            "projection_version": "1.0.0",
            "task_owner": "TASK-039",
            "edges": rows,
            "automatic_regeneration_started": False,
            "direct_continuation_human_override_allowed": False,
        }
        body["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class Task039ContinuityWorkspaceService:
    def __init__(
        self,
        *,
        continuity: ContinuityRegistry,
        production: ProductionControlRegistry,
        token_factory: TokenFactory | None = None,
    ) -> None:
        self.continuity = continuity
        self.production = production
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._confirmations: dict[str, _ContinuityConfirmation] = {}

    def snapshot(self) -> dict[str, Any]:
        return Task039ContinuityWorkspaceProjection.build(continuity=self.continuity, production=self.production)

    def prepare_soft_approval(self, *, edge_id: str) -> dict[str, Any]:
        edge = self.continuity.edges.get(edge_id)
        resolution = self.continuity.resolutions.get(edge_id)
        if edge is None or resolution is None:
            raise ProductError(
                "ERR_CONTINUITY_REVIEW_STATE_REQUIRED",
                "Soft continuity approval requires an inspected target",
                ProductErrorCategory.STATE,
            )
        if edge.boundary_type is not ContinuityBoundaryType.SOFT_CONTINUITY:
            raise ProductError(
                "ERR_CONTINUITY_HARD_RULE_NOT_OVERRIDABLE",
                "Only SOFT_CONTINUITY may be Human-approved",
                ProductErrorCategory.AUTHORIZATION,
            )
        if resolution.status != "HUMAN_REVIEW_REQUIRED" or resolution.validation_status != "HUMAN_REVIEW_REQUIRED":
            raise ProductError(
                "ERR_CONTINUITY_HUMAN_APPROVAL_NOT_REQUIRED",
                "Current continuity state is not awaiting Human inspection",
                ProductErrorCategory.STATE,
            )
        slot = self.production.slots.get(edge.to_slot_id)
        if slot is None or slot.status is not SlotStatus.LOCKED or slot.locked_candidate_id is None:
            raise ProductError(
                "ERR_CONTINUITY_WORKSPACE_TARGET_NOT_LOCKED",
                "Soft continuity approval requires the exact target Slot to be locked",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        candidate = self.production.candidates.get(slot.locked_candidate_id)
        if (
            candidate is None
            or candidate.lifecycle_state is not CandidateLifecycle.LOCKED
            or candidate.asset_id != resolution.target_asset_id
            or candidate.asset_sha256 != resolution.target_asset_sha256
        ):
            raise ProductError(
                "ERR_CONTINUITY_WORKSPACE_TARGET_MISMATCH",
                "Locked target Candidate does not match the inspected continuity target bytes",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        token = self._token_factory()
        if not isinstance(token, str) or not token.strip() or token in self._confirmations:
            raise ProductError(
                "ERR_CONTINUITY_WORKSPACE_CONFIRMATION_TOKEN_INVALID",
                "Continuity confirmation token factory returned an invalid token",
                ProductErrorCategory.INTERNAL,
            )
        resolution_sha = _resolution_hash(resolution.to_dict())
        self._confirmations[token] = _ContinuityConfirmation(
            token, edge_id, candidate.candidate_id, candidate.asset_sha256, resolution_sha
        )
        return {
            "confirmation_version": "1.0.0",
            "task_owner": "TASK-039",
            "confirmation_id": token,
            "edge_id": edge_id,
            "target_candidate_id": candidate.candidate_id,
            "target_asset_sha256": candidate.asset_sha256,
            "resolution_sha256": resolution_sha,
            "human_final_authority_required": True,
            "automatic_regeneration_started": False,
        }

    def apply_soft_approval(self, *, confirmation_id: str, approved_by: str) -> dict[str, Any]:
        pending = self._confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError(
                "ERR_CONTINUITY_WORKSPACE_CONFIRMATION_INVALID",
                "Continuity Human approval confirmation is missing or already used",
                ProductErrorCategory.AUTHORIZATION,
            )
        edge = self.continuity.edges.get(pending.edge_id)
        resolution = self.continuity.resolutions.get(pending.edge_id)
        if edge is None or resolution is None:
            raise ProductError(
                "ERR_CONTINUITY_WORKSPACE_CONFIRMATION_STALE",
                "Continuity state changed after Human confirmation was prepared",
                ProductErrorCategory.AUTHORIZATION,
            )
        slot = self.production.slots.get(edge.to_slot_id)
        candidate = None if slot is None or slot.locked_candidate_id is None else self.production.candidates.get(slot.locked_candidate_id)
        if (
            edge.boundary_type is not ContinuityBoundaryType.SOFT_CONTINUITY
            or resolution.status != "HUMAN_REVIEW_REQUIRED"
            or _resolution_hash(resolution.to_dict()) != pending.resolution_sha256
            or slot is None
            or slot.status is not SlotStatus.LOCKED
            or candidate is None
            or candidate.candidate_id != pending.target_candidate_id
            or candidate.lifecycle_state is not CandidateLifecycle.LOCKED
            or candidate.asset_sha256 != pending.target_asset_sha256
            or candidate.asset_id != resolution.target_asset_id
            or candidate.asset_sha256 != resolution.target_asset_sha256
        ):
            raise ProductError(
                "ERR_CONTINUITY_WORKSPACE_CONFIRMATION_STALE",
                "Continuity target changed after Human confirmation was prepared",
                ProductErrorCategory.AUTHORIZATION,
            )
        pending.consumed = True
        approved = self.continuity.human_approve_soft(pending.edge_id, approved_by=approved_by)
        return {
            "resolution": approved.to_dict(),
            "workspace": self.snapshot(),
            "automatic_regeneration_started": False,
        }
