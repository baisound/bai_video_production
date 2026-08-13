"""TASK-039 continuity-boundary validation foundation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any

from .errors import ProductError, ProductErrorCategory


_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _sha(value: str, name: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


class ContinuityBoundaryType(str, Enum):
    DIRECT_CONTINUATION = "DIRECT_CONTINUATION"
    SOFT_CONTINUITY = "SOFT_CONTINUITY"
    DISCONTINUOUS = "DISCONTINUOUS"


@dataclass(frozen=True, slots=True)
class ContinuityEdge:
    edge_id: str
    from_scene_id: str
    from_slot_id: str
    from_candidate_id: str
    from_asset_id: str
    from_asset_sha256: str
    to_scene_id: str
    to_slot_id: str
    boundary_type: ContinuityBoundaryType
    character_contract_refs: tuple[str, ...] = ()
    space_contract_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name, value in (
            ("edge_id", self.edge_id),
            ("from_scene_id", self.from_scene_id),
            ("from_slot_id", self.from_slot_id),
            ("from_candidate_id", self.from_candidate_id),
            ("from_asset_id", self.from_asset_id),
            ("to_scene_id", self.to_scene_id),
            ("to_slot_id", self.to_slot_id),
        ):
            _id(value, name)
        _sha(self.from_asset_sha256, "from_asset_sha256")
        for value in self.character_contract_refs + self.space_contract_refs:
            _id(value, "contract_ref")
        if self.from_scene_id == self.to_scene_id and self.from_slot_id == self.to_slot_id:
            raise ValueError("continuity edge cannot target the same Scene Slot")

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "from_scene_id": self.from_scene_id,
            "from_slot_id": self.from_slot_id,
            "from_candidate_id": self.from_candidate_id,
            "from_asset_id": self.from_asset_id,
            "from_asset_sha256": self.from_asset_sha256,
            "to_scene_id": self.to_scene_id,
            "to_slot_id": self.to_slot_id,
            "boundary_type": self.boundary_type.value,
            "character_contract_refs": list(self.character_contract_refs),
            "space_contract_refs": list(self.space_contract_refs),
        }


@dataclass(frozen=True, slots=True)
class ContinuityValidationResult:
    edge_id: str
    status: str
    exact_asset_identity_required: bool
    exact_asset_identity_pass: bool | None
    human_review_required: bool
    reason_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "status": self.status,
            "exact_asset_identity_required": self.exact_asset_identity_required,
            "exact_asset_identity_pass": self.exact_asset_identity_pass,
            "human_review_required": self.human_review_required,
            "reason_code": self.reason_code,
        }


class ContinuityValidationService:
    @staticmethod
    def validate_locked_target(
        edge: ContinuityEdge,
        *,
        target_asset_id: str,
        target_asset_sha256: str,
    ) -> ContinuityValidationResult:
        _id(target_asset_id, "target_asset_id")
        _sha(target_asset_sha256, "target_asset_sha256")

        if edge.boundary_type is ContinuityBoundaryType.DISCONTINUOUS:
            return ContinuityValidationResult(edge.edge_id, "PASS", False, None, False)

        if edge.boundary_type is ContinuityBoundaryType.SOFT_CONTINUITY:
            return ContinuityValidationResult(
                edge.edge_id,
                "HUMAN_REVIEW_REQUIRED",
                False,
                None,
                True,
                "SOFT_CONTINUITY_REQUIRES_INSPECTION",
            )

        exact = target_asset_id == edge.from_asset_id and target_asset_sha256 == edge.from_asset_sha256
        if not exact:
            return ContinuityValidationResult(
                edge.edge_id,
                "FAIL",
                True,
                False,
                True,
                "DIRECT_CONTINUATION_ASSET_MISMATCH",
            )
        return ContinuityValidationResult(edge.edge_id, "PASS", True, True, False)

    @staticmethod
    def require_generation_safe(result: ContinuityValidationResult) -> None:
        if result.status == "PASS" and not result.human_review_required:
            return
        raise ProductError(
            "ERR_CONTINUITY_GENERATION_BLOCKED",
            "Required continuity boundary is not resolved for downstream generation",
            ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            details={"edge_id": result.edge_id, "status": result.status, "reason_code": result.reason_code},
        )
