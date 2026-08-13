"""TASK-041 Audio Workspace projection and Human placement-decision boundary.

The application surface remains non-destructive.  It can confirm placement
review decisions, but it never writes media, starts a DAW, compiles TASK-026,
or mutates Resolve by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
import secrets
from typing import Any, Callable

from .audio_workspace import AudioWorkspaceRegistry, PlacementDecision, PlacementReview
from .errors import ProductError, ProductErrorCategory
from .production_control import CandidateLifecycle, ProductionControlRegistry
from .serialization import canonical_json_bytes, sha256_bytes


TokenFactory = Callable[[], str]


@dataclass(slots=True)
class _PlacementConfirmation:
    confirmation_id: str
    review_id: str
    candidate_id: str
    candidate_asset_sha256: str
    placement_sha256: str
    decision: PlacementDecision
    consumed: bool = False


def _placement_hash(review: PlacementReview) -> str:
    return sha256_bytes(canonical_json_bytes(review.to_dict()))


class Task041AudioWorkspaceProjection:
    @staticmethod
    def build(*, workspace: AudioWorkspaceRegistry, production: ProductionControlRegistry) -> dict[str, Any]:
        placements = []
        for review in sorted(workspace.placements.values(), key=lambda item: item.review_id):
            candidate = production.candidates.get(review.candidate_id)
            if candidate is None:
                raise ProductError(
                    "ERR_AUDIO_WORKSPACE_CANDIDATE_NOT_FOUND",
                    "Audio Workspace placement references a missing Production Candidate",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"review_id": review.review_id},
                )
            available = []
            if review.decision is PlacementDecision.REVIEW:
                if candidate.lifecycle_state is CandidateLifecycle.LOCKED:
                    available.append(PlacementDecision.ACCEPT.value)
                available += [PlacementDecision.REJECT.value, PlacementDecision.ALTERNATE_USE.value]
            placements.append({
                **review.to_dict(),
                "candidate_asset_id": candidate.asset_id,
                "candidate_asset_sha256": candidate.asset_sha256,
                "candidate_lifecycle_state": candidate.lifecycle_state.value,
                "available_human_actions": available,
                "task026_compile_started": False,
                "resolve_mutation_started": False,
            })
        body: dict[str, Any] = {
            "projection_version": "1.0.0",
            "task_owner": "TASK-041",
            "placements": placements,
            "candidate_decisions": [workspace.decisions[key].to_dict() for key in sorted(workspace.decisions)],
            "derived_assets": [workspace.derived_assets[key].to_dict() for key in sorted(workspace.derived_assets)],
            "destructive_source_write_authority": False,
            "task026_compile_started": False,
            "resolve_mutation_started": False,
        }
        body["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class Task041AudioWorkspaceService:
    def __init__(
        self,
        *,
        workspace: AudioWorkspaceRegistry,
        production: ProductionControlRegistry,
        token_factory: TokenFactory | None = None,
    ) -> None:
        self.workspace = workspace
        self.production = production
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._confirmations: dict[str, _PlacementConfirmation] = {}

    def snapshot(self) -> dict[str, Any]:
        return Task041AudioWorkspaceProjection.build(workspace=self.workspace, production=self.production)

    def prepare_placement_decision(self, *, review_id: str, decision: str) -> dict[str, Any]:
        try:
            decision_kind = PlacementDecision(decision)
        except ValueError as exc:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_PLACEMENT_DECISION_INVALID",
                "Unknown Audio placement decision",
                ProductErrorCategory.VALIDATION,
            ) from exc
        if decision_kind is PlacementDecision.REVIEW:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_PLACEMENT_DECISION_INVALID",
                "REVIEW is an initial state, not a Human final placement action",
                ProductErrorCategory.VALIDATION,
            )
        review = self.workspace.placements.get(review_id)
        if review is None:
            raise ProductError("ERR_AUDIO_PLACEMENT_NOT_FOUND", "review_id does not exist", ProductErrorCategory.STATE)
        if review.decision is not PlacementDecision.REVIEW:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_PLACEMENT_ALREADY_DECIDED",
                "Audio placement already has a Human decision",
                ProductErrorCategory.STATE,
            )
        candidate = self.production.candidates.get(review.candidate_id)
        if candidate is None:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_CANDIDATE_NOT_FOUND",
                "Audio placement Candidate does not exist in Production Control",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if decision_kind is PlacementDecision.ACCEPT and candidate.lifecycle_state is not CandidateLifecycle.LOCKED:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_ACCEPT_REQUIRES_LOCKED_CANDIDATE",
                "Human ACCEPT placement requires a locked Production Candidate",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={"lifecycle_state": candidate.lifecycle_state.value},
            )
        token = self._token_factory()
        if not isinstance(token, str) or not token.strip() or token in self._confirmations:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_CONFIRMATION_TOKEN_INVALID",
                "Audio placement confirmation token factory returned an invalid token",
                ProductErrorCategory.INTERNAL,
            )
        confirmation = _PlacementConfirmation(
            confirmation_id=token,
            review_id=review_id,
            candidate_id=candidate.candidate_id,
            candidate_asset_sha256=candidate.asset_sha256,
            placement_sha256=_placement_hash(review),
            decision=decision_kind,
        )
        self._confirmations[token] = confirmation
        return {
            "confirmation_version": "1.0.0",
            "task_owner": "TASK-041",
            "confirmation_id": token,
            "review_id": review_id,
            "candidate_id": candidate.candidate_id,
            "candidate_asset_sha256": candidate.asset_sha256,
            "placement_sha256": confirmation.placement_sha256,
            "decision": decision_kind.value,
            "gain_db": review.gain_db,
            "timeline_start_frame": review.timeline_start_frame,
            "duration_frames": review.duration_frames,
            "human_final_authority_required": True,
            "task026_compile_started": False,
            "resolve_mutation_started": False,
        }

    def apply_placement_decision(self, *, confirmation_id: str) -> dict[str, Any]:
        pending = self._confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_CONFIRMATION_INVALID",
                "Audio placement confirmation is missing or already used",
                ProductErrorCategory.AUTHORIZATION,
            )
        review = self.workspace.placements.get(pending.review_id)
        candidate = self.production.candidates.get(pending.candidate_id)
        if (
            review is None
            or candidate is None
            or review.candidate_id != pending.candidate_id
            or review.decision is not PlacementDecision.REVIEW
            or _placement_hash(review) != pending.placement_sha256
            or candidate.asset_sha256 != pending.candidate_asset_sha256
            or (pending.decision is PlacementDecision.ACCEPT and candidate.lifecycle_state is not CandidateLifecycle.LOCKED)
        ):
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_CONFIRMATION_STALE",
                "Audio placement or Candidate changed after Human confirmation was prepared",
                ProductErrorCategory.AUTHORIZATION,
            )
        pending.consumed = True
        updated = self.workspace.replace_placement_decision(pending.review_id, pending.decision)
        return {
            "placement": updated.to_dict(),
            "workspace": self.snapshot(),
            "task026_compile_started": False,
            "resolve_mutation_started": False,
        }
