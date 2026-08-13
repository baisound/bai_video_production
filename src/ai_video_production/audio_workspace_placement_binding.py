"""TASK-041 Human placement review -> TASK-026 placement-plan binding."""

from __future__ import annotations

from .audio_placement import (
    AudioPlacementPlan,
    AudioPlacementRequest,
    AudioPlacementRole,
    AudioPlacementService,
    BedMode,
)
from .audio_workspace import AudioWorkspaceRegistry, PlacementDecision
from .errors import ProductError, ProductErrorCategory
from .production_control import CandidateLifecycle, ProductionControlRegistry


_ROLE_MAP = {
    "SOURCE": AudioPlacementRole.SOURCE,
    "SE": AudioPlacementRole.SE,
    "BGM": AudioPlacementRole.BGM,
    "NARRATION": AudioPlacementRole.NARRATION,
    "MIX_STEM": AudioPlacementRole.MIX_STEM,
}


class AudioWorkspacePlacementBinding:
    @staticmethod
    def compile_accepted_placement(
        *,
        review_id: str,
        workspace: AudioWorkspaceRegistry,
        production: ProductionControlRegistry,
        track_index: int,
        source_duration_frames: int,
        loop: bool = False,
        fade_in_frames: int = 0,
        fade_out_frames: int = 0,
        bed_mode: BedMode = BedMode.FULL,
    ) -> AudioPlacementPlan:
        review = workspace.placements.get(review_id)
        if review is None:
            raise ProductError("ERR_AUDIO_PLACEMENT_NOT_FOUND", "review_id does not exist", ProductErrorCategory.STATE)
        if review.decision is not PlacementDecision.ACCEPT:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_HUMAN_ACCEPT_REQUIRED",
                "Audio placement must be Human-accepted before compilation",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        candidate = production.candidates.get(review.candidate_id)
        if candidate is None:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_CANDIDATE_NOT_FOUND",
                "Audio placement Candidate does not exist in Production Control",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if candidate.lifecycle_state is not CandidateLifecycle.LOCKED:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_CANDIDATE_NOT_LOCKED",
                "Audio placement requires a locked Production Candidate",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={"lifecycle_state": candidate.lifecycle_state.value},
            )
        return AudioPlacementService.compile(AudioPlacementRequest(
            asset_id=candidate.asset_id,
            role=_ROLE_MAP[review.track_role],
            track_index=track_index,
            source_duration_frames=source_duration_frames,
            desired_start_frame=review.timeline_start_frame,
            desired_duration_frames=review.duration_frames,
            loop=loop,
            fade_in_frames=fade_in_frames,
            fade_out_frames=fade_out_frames,
            gain_db=review.gain_db,
            bed_mode=bed_mode,
        ))
