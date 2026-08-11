"""Canonical subtitle placement handoff for TASK-010 Resolve execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .atomic import AtomicJsonWriter, AtomicWriteResult
from .serialization import canonical_json_bytes, sha256_bytes, sha256_json
from .subtitle_workspace import SubtitleReviewState, SubtitleWorkspace
from .timebase import FrameRate, FrameRounding


@dataclass(frozen=True, slots=True)
class ResolveSubtitlePlacement:
    cue_id: str
    record_start_frame: int
    record_end_frame: int
    text: str
    review_state: SubtitleReviewState

    def __post_init__(self) -> None:
        if self.record_start_frame < 0 or self.record_end_frame <= self.record_start_frame:
            raise ValueError("Resolve subtitle placement must contain at least one frame")

    def to_dict(self) -> dict[str, Any]:
        return {
            "cue_id": self.cue_id,
            "record_range_frames": {
                "start": self.record_start_frame,
                "end_exclusive": self.record_end_frame,
            },
            "text": self.text,
            "review_state": self.review_state.value,
        }


@dataclass(frozen=True, slots=True)
class ResolveSubtitlePlacementPlan:
    workspace_id: str
    workspace_revision: int
    source_workspace_sha256: str
    timeline_rate: FrameRate
    timeline_origin_frame: int
    track_index: int
    placements: tuple[ResolveSubtitlePlacement, ...]
    ready_for_resolve_write: bool

    def __post_init__(self) -> None:
        if self.workspace_revision < 0:
            raise ValueError("workspace_revision must be non-negative")
        if self.timeline_origin_frame < 0:
            raise ValueError("timeline_origin_frame must be >= 0")
        if self.track_index < 1:
            raise ValueError("track_index must be >= 1")
        previous_end = self.timeline_origin_frame
        ids: set[str] = set()
        for placement in self.placements:
            if placement.cue_id in ids:
                raise ValueError("duplicate cue_id in Resolve subtitle placement plan")
            if placement.record_start_frame < previous_end:
                raise ValueError(
                    "millisecond subtitle timing cannot be represented as non-overlapping timeline frames"
                )
            ids.add(placement.cue_id)
            previous_end = placement.record_end_frame

    def to_dict(self) -> dict[str, Any]:
        body = {
            "plan_version": "1.0.0",
            "workspace_id": self.workspace_id,
            "workspace_revision": self.workspace_revision,
            "source_workspace_sha256": self.source_workspace_sha256,
            "timeline_rate": {
                "numerator": self.timeline_rate.numerator,
                "denominator": self.timeline_rate.denominator,
            },
            "timeline_origin_frame": self.timeline_origin_frame,
            "track_index": self.track_index,
            "placements": [item.to_dict() for item in self.placements],
            "ready_for_resolve_write": self.ready_for_resolve_write,
            "handoff_owner": "TASK-006",
            "execution_owner": "TASK-010",
            "contains_private_subtitle_text": True,
        }
        body["plan_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class ResolveSubtitleHandoffService:
    """Compile human-reviewed Workspace timing into a private deterministic handoff."""

    @staticmethod
    def build(
        workspace: SubtitleWorkspace,
        *,
        timeline_rate: FrameRate,
        timeline_origin_frame: int = 0,
        track_index: int = 1,
    ) -> ResolveSubtitlePlacementPlan:
        if timeline_origin_frame < 0:
            raise ValueError("timeline_origin_frame must be >= 0")
        if track_index < 1:
            raise ValueError("track_index must be >= 1")
        placements: list[ResolveSubtitlePlacement] = []
        previous_end = 0
        for cue in workspace.cues:
            start_frame = timeline_origin_frame + timeline_rate.us_to_frame(
                cue.start_ms * 1000, rounding=FrameRounding.FLOOR
            )
            end_frame = timeline_origin_frame + timeline_rate.us_to_frame(
                cue.end_ms * 1000, rounding=FrameRounding.CEIL
            )
            if end_frame <= start_frame:
                raise ValueError(f"cue {cue.cue_id} collapses below one timeline frame")
            if start_frame < previous_end:
                raise ValueError(
                    "millisecond subtitle timing cannot be represented as non-overlapping timeline frames"
                )
            placement = ResolveSubtitlePlacement(
                cue_id=cue.cue_id,
                record_start_frame=start_frame,
                record_end_frame=end_frame,
                text=cue.text,
                review_state=cue.review_state,
            )
            placements.append(placement)
            previous_end = end_frame

        ready = bool(placements) and all(
            item.review_state is SubtitleReviewState.APPROVED for item in placements
        )
        return ResolveSubtitlePlacementPlan(
            workspace_id=workspace.workspace_id,
            workspace_revision=workspace.revision,
            source_workspace_sha256=sha256_json(workspace.to_dict()),
            timeline_rate=timeline_rate,
            timeline_origin_frame=timeline_origin_frame,
            track_index=track_index,
            placements=tuple(placements),
            ready_for_resolve_write=ready,
        )

    @staticmethod
    def write(
        path: str | Path,
        workspace: SubtitleWorkspace,
        *,
        timeline_rate: FrameRate,
        timeline_origin_frame: int = 0,
        track_index: int = 1,
    ) -> tuple[ResolveSubtitlePlacementPlan, AtomicWriteResult]:
        plan = ResolveSubtitleHandoffService.build(
            workspace,
            timeline_rate=timeline_rate,
            timeline_origin_frame=timeline_origin_frame,
            track_index=track_index,
        )
        result = AtomicJsonWriter.write(path, plan.to_dict())
        return plan, result
