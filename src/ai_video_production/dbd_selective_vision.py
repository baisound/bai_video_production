"""Selective, fail-closed Tier 4 Vision escalation planning for DbD evidence."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re

from .ai_connections import (
    AiConnectionProfile, AiConnectionResolver, AiWorkload, ConnectionAvailability,
    CostClass, ModelRoute,
)
from .capability_execution import CapabilityExecutionRequest
from .dbd_vision_slices import NormalizedROI
from .errors import ProductError
from .game_event_evidence import SourceFrameRange


_SAFE_REF = re.compile(r"^[a-z][a-z0-9+.-]*://[^\s]{1,1000}$")
_AUTH_REF = re.compile(r"^authorization://[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_SUBJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_FORBIDDEN_EVIDENCE_SCHEMES = {"authorization", "credential", "secret"}
_CAPABILITY = "DBD_SELECTIVE_VISION_ANALYSIS"


class SelectiveVisionTrigger(str, Enum):
    CHASE_BOUNDARY_AMBIGUITY = "CHASE_BOUNDARY_AMBIGUITY"
    PRE_DOWN_MOMENT = "PRE_DOWN_MOMENT"
    RESCUE_MOMENT = "RESCUE_MOMENT"
    GENERATOR_COMPLETION = "GENERATOR_COMPLETION"
    MAJOR_TACTICAL_DECISION = "MAJOR_TACTICAL_DECISION"
    TIER_CONTRADICTION = "TIER_CONTRADICTION"


class SelectiveVisionPlanStatus(str, Enum):
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    AUTHORIZATION_REQUIRED = "AUTHORIZATION_REQUIRED"
    ROUTE_UNAVAILABLE = "ROUTE_UNAVAILABLE"
    READY = "READY"


@dataclass(frozen=True, slots=True)
class SelectiveVisionCandidate:
    match_id: str
    source_asset_id: str
    source_range: SourceFrameRange
    rois: tuple[NormalizedROI, ...]
    triggers: tuple[SelectiveVisionTrigger, ...]
    evidence_refs: tuple[str, ...]
    tier_confidence_milli: int

    def __post_init__(self) -> None:
        if not _SUBJECT_ID.fullmatch(self.match_id) or not _SUBJECT_ID.fullmatch(self.source_asset_id):
            raise ValueError("match_id and source_asset_id must be bounded safe identifiers")
        if not isinstance(self.source_range, SourceFrameRange):
            raise ValueError("source_range must be a SourceFrameRange")
        if self.source_range.duration_frames > 300:
            raise ValueError("selective Vision window must be at most 300 frames")
        if not 1 <= len(self.rois) <= 8 or any(not isinstance(x, NormalizedROI) for x in self.rois):
            raise ValueError("selective Vision requires 1..8 normalized ROIs")
        if len({x.roi_id for x in self.rois}) != len(self.rois):
            raise ValueError("ROI ids must be unique")
        if not self.triggers or len(set(self.triggers)) != len(self.triggers):
            raise ValueError("triggers must be non-empty and unique")
        if any(not isinstance(x, SelectiveVisionTrigger) for x in self.triggers):
            raise ValueError("invalid selective Vision trigger")
        if not self.evidence_refs or len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ValueError("evidence_refs must be non-empty and unique")
        if any(not _SAFE_REF.fullmatch(x) for x in self.evidence_refs):
            raise ValueError("evidence_refs must be bounded non-secret references")
        if any(x.split(":", 1)[0] in _FORBIDDEN_EVIDENCE_SCHEMES for x in self.evidence_refs):
            raise ValueError("evidence_refs must not carry authority, credentials, or secrets")
        if (
            isinstance(self.tier_confidence_milli, bool)
            or not isinstance(self.tier_confidence_milli, int)
            or not 0 <= self.tier_confidence_milli <= 1000
        ):
            raise ValueError("tier_confidence_milli must be 0..1000")


@dataclass(frozen=True, slots=True)
class SelectiveVisionAuthority:
    explicitly_authorized: bool = False
    authorization_ref: str | None = None
    cost_ceiling_units: int = 0

    def __post_init__(self) -> None:
        if self.authorization_ref is not None and not _AUTH_REF.fullmatch(self.authorization_ref):
            raise ValueError("authorization_ref must use authorization:// and contain no secret")
        if isinstance(self.cost_ceiling_units, bool) or not 0 <= self.cost_ceiling_units <= 10000:
            raise ValueError("cost_ceiling_units must be 0..10000")
        if self.explicitly_authorized and (self.authorization_ref is None or self.cost_ceiling_units < 1):
            raise ValueError("explicit authorization requires reference and positive cost ceiling")


@dataclass(frozen=True, slots=True)
class SelectiveVisionPlan:
    status: SelectiveVisionPlanStatus
    reason_codes: tuple[str, ...]
    route_id: str | None = None
    provider_id: str | None = None
    model_id: str | None = None
    cost_class: CostClass | None = None
    request: CapabilityExecutionRequest | None = None
    provider_dispatch_allowed: bool = False
    event_claim_allowed: bool = False


class SelectiveVisionPlanner:
    """Create an execution proposal; this class never invokes a provider."""

    def __init__(self, *, maximum_auto_confidence_milli: int = 920) -> None:
        if not 0 <= maximum_auto_confidence_milli <= 1000:
            raise ValueError("maximum_auto_confidence_milli must be 0..1000")
        self.maximum_auto_confidence_milli = maximum_auto_confidence_milli

    def plan(
        self,
        candidate: SelectiveVisionCandidate,
        profile: AiConnectionProfile,
        availability: ConnectionAvailability,
        authority: SelectiveVisionAuthority = SelectiveVisionAuthority(),
    ) -> SelectiveVisionPlan:
        if not isinstance(candidate, SelectiveVisionCandidate):
            raise ValueError("candidate must be SelectiveVisionCandidate")
        contradiction = SelectiveVisionTrigger.TIER_CONTRADICTION in candidate.triggers
        if not contradiction and candidate.tier_confidence_milli >= self.maximum_auto_confidence_milli:
            return SelectiveVisionPlan(
                SelectiveVisionPlanStatus.NOT_ELIGIBLE,
                ("TIER_1_TO_3_EVIDENCE_ALREADY_SUFFICIENT",),
            )
        if not authority.explicitly_authorized:
            return SelectiveVisionPlan(
                SelectiveVisionPlanStatus.AUTHORIZATION_REQUIRED,
                ("EXPLICIT_VISION_EXECUTION_AUTHORIZATION_REQUIRED",),
            )
        try:
            route = AiConnectionResolver.resolve(
                profile, AiWorkload.IMAGE, availability,
                required_capabilities=(_CAPABILITY,),
            )
        except ProductError:
            return SelectiveVisionPlan(
                SelectiveVisionPlanStatus.ROUTE_UNAVAILABLE,
                ("CANONICAL_VISION_PROVIDER_ROUTE_UNAVAILABLE",),
            )
        request = self._request(candidate, authority, route)
        return SelectiveVisionPlan(
            SelectiveVisionPlanStatus.READY,
            ("BOUNDED_SELECTIVE_VISION_PROPOSAL",),
            route_id=route.route_id,
            provider_id=route.provider_id,
            model_id=route.model_id,
            cost_class=route.cost_class,
            request=request,
            provider_dispatch_allowed=True,
            event_claim_allowed=False,
        )

    @staticmethod
    def _request(
        candidate: SelectiveVisionCandidate,
        authority: SelectiveVisionAuthority,
        route: ModelRoute,
    ) -> CapabilityExecutionRequest:
        payload = {
            "schema_version": "1.0.0",
            "match_id": candidate.match_id,
            "source_asset_id": candidate.source_asset_id,
            "source_range": candidate.source_range.to_dict(),
            "rois": [
                {"roi_id": x.roi_id, "x": x.x, "y": x.y, "width": x.width, "height": x.height}
                for x in candidate.rois
            ],
            "triggers": [x.value for x in candidate.triggers],
            "evidence_refs": list(candidate.evidence_refs),
            "tier_confidence_milli": candidate.tier_confidence_milli,
            "authorization_ref": authority.authorization_ref,
            "cost_ceiling_units": authority.cost_ceiling_units,
            "selected_route_id": route.route_id,
            "response_contract": {
                "allow_abstention": True,
                "require_evidence_refs": True,
                "event_claim_allowed": False,
            },
        }
        return CapabilityExecutionRequest(
            workload=AiWorkload.IMAGE,
            capability=_CAPABILITY,
            payload=payload,
            timeout_seconds=120,
        )


__all__ = [
    "SelectiveVisionAuthority", "SelectiveVisionCandidate", "SelectiveVisionPlan",
    "SelectiveVisionPlanner", "SelectiveVisionPlanStatus", "SelectiveVisionTrigger",
]
