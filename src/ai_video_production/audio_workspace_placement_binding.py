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
from .timeline_audio import AudioFitPolicy
from .timeline_audio_store import TimelineAudioHistory


_ROLE_MAP = {
    "SOURCE": AudioPlacementRole.SOURCE,
    "SE": AudioPlacementRole.SE,
    "BGM": AudioPlacementRole.BGM,
    "AMBIENCE": AudioPlacementRole.AMBIENCE,
    "NARRATION": AudioPlacementRole.NARRATION,
    "MIX_STEM": AudioPlacementRole.MIX_STEM,
}


class AudioWorkspacePlacementBinding:
    @staticmethod
    def compile_current_timeline_placement(
        *, review_id: str, workspace: AudioWorkspaceRegistry,
        production: ProductionControlRegistry, timeline: TimelineAudioHistory,
        track_index: int, bed_mode: BedMode = BedMode.FULL,
    ) -> AudioPlacementPlan:
        review = workspace.placements.get(review_id)
        current = timeline.current_plan
        if review is None or review.timeline_binding is None or current is None:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_TIMELINE_BINDING_REQUIRED",
                "Current Timeline proof is required for Timeline compilation",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        binding = review.timeline_binding
        try:
            item = current.item(binding.item_id)
        except (KeyError, StopIteration) as exc:
            raise ProductError("ERR_AUDIO_PLACEMENT_TIMELINE_STALE", "Timeline item no longer exists", ProductErrorCategory.STATE) from exc
        if binding != current.placement_binding(item.item_id):
            raise ProductError("ERR_AUDIO_PLACEMENT_TIMELINE_STALE", "Timeline proof is not the exact current revision", ProductErrorCategory.STATE)
        if (review.timeline_start_frame, review.duration_frames, review.track_role) != (
            item.start_frame, item.end_frame - item.start_frame, item.role.value,
        ) or item.source.candidate_id != review.candidate_id:
            raise ProductError("ERR_AUDIO_PLACEMENT_TIMELINE_MISMATCH", "Placement differs from its Timeline item", ProductErrorCategory.DATA_INTEGRITY)
        fit = getattr(item, "fit_policy", AudioFitPolicy.EXACT)
        if fit is AudioFitPolicy.STRETCH:
            raise ProductError("ERR_AUDIO_PLACEMENT_STRETCH_NOT_SUPPORTED", "TASK-026 cannot execute STRETCH without an explicit adapter", ProductErrorCategory.NOT_SUPPORTED)
        duration = item.source.source_duration_frames
        if duration is None:
            raise ProductError("ERR_AUDIO_PLACEMENT_SOURCE_DURATION_REQUIRED", "Bound source duration is required", ProductErrorCategory.DATA_INTEGRITY)
        return AudioWorkspacePlacementBinding.compile_accepted_placement(
            review_id=review_id, workspace=workspace, production=production,
            track_index=track_index, source_duration_frames=duration,
            loop=fit is AudioFitPolicy.LOOP,
            fade_in_frames=getattr(item, "fade_in_frames", 0),
            fade_out_frames=getattr(item, "fade_out_frames", 0),
            bed_mode=bed_mode,
        )

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
