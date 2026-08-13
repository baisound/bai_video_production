"""TASK-036 deterministic projection of editing-domain data into desktop UI rows/blocks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .cut_candidates import CutCandidate
from .edit_plan import EditDecision, EditPlan
from .subtitle_workspace import SubtitleWorkspace, WorkspaceCue


@dataclass(frozen=True, slots=True)
class TranscriptRow:
    row_id: str
    start_us: int
    end_us: int
    text: str
    review_state: str
    origin: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "start_us": self.start_us,
            "end_us": self.end_us,
            "text": self.text,
            "review_state": self.review_state,
            "origin": self.origin,
        }


@dataclass(frozen=True, slots=True)
class TimelineBlock:
    block_id: str
    track_id: str
    block_type: str
    start_us: int
    end_us: int
    label: str
    state: str
    source_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.start_us < 0 or self.end_us <= self.start_us:
            raise ValueError("timeline block range must be positive and end-exclusive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "track_id": self.track_id,
            "block_type": self.block_type,
            "start_us": self.start_us,
            "end_us": self.end_us,
            "label": self.label,
            "state": self.state,
            "source_ids": list(self.source_ids),
        }


@dataclass(frozen=True, slots=True)
class EditingProjection:
    source_duration_us: int
    transcript_rows: tuple[TranscriptRow, ...]
    timeline_blocks: tuple[TimelineBlock, ...]

    def __post_init__(self) -> None:
        if self.source_duration_us <= 0:
            raise ValueError("source_duration_us must be positive")
        for block in self.timeline_blocks:
            if block.end_us > self.source_duration_us:
                raise ValueError("timeline block exceeds source duration")

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_version": "1.0.0",
            "task_owner": "TASK-036",
            "source_duration_us": self.source_duration_us,
            "transcript_rows": [row.to_dict() for row in self.transcript_rows],
            "timeline_blocks": [block.to_dict() for block in self.timeline_blocks],
        }


class DesktopEditingProjectionService:
    """Convert existing Product artifacts to a transport-neutral NLE presentation model."""

    @staticmethod
    def transcript_rows(workspace: SubtitleWorkspace | None) -> tuple[TranscriptRow, ...]:
        if workspace is None:
            return ()
        return tuple(
            TranscriptRow(
                row_id=cue.cue_id,
                start_us=cue.start_ms * 1000,
                end_us=cue.end_ms * 1000,
                text=cue.text,
                review_state=cue.review_state.value,
                origin=cue.origin.value,
            )
            for cue in workspace.cues
        )

    @staticmethod
    def subtitle_blocks(workspace: SubtitleWorkspace | None) -> tuple[TimelineBlock, ...]:
        if workspace is None:
            return ()
        return tuple(
            TimelineBlock(
                block_id=f"subtitle:{cue.cue_id}",
                track_id="S1",
                block_type="SUBTITLE",
                start_us=cue.start_ms * 1000,
                end_us=cue.end_ms * 1000,
                label=cue.text,
                state=cue.review_state.value,
                source_ids=(cue.cue_id,),
            )
            for cue in workspace.cues
        )

    @staticmethod
    def candidate_blocks(
        candidates: Iterable[CutCandidate],
        *,
        edit_plan: EditPlan | None,
    ) -> tuple[TimelineBlock, ...]:
        decisions: Mapping[str, str]
        if edit_plan is None:
            decisions = {}
        else:
            decisions = {node.candidate_id: node.final_decision.value for node in edit_plan.graph_nodes}
        return tuple(
            TimelineBlock(
                block_id=f"cut:{candidate.candidate_id}",
                track_id="CUT_OVERLAY",
                block_type="CUT_CANDIDATE",
                start_us=candidate.start_us,
                end_us=candidate.end_us,
                label=candidate.kind.value,
                state=decisions.get(candidate.candidate_id, EditDecision.REVIEW.value),
                source_ids=(candidate.candidate_id,),
            )
            for candidate in candidates
        )

    @staticmethod
    def edit_plan_blocks(edit_plan: EditPlan | None) -> tuple[TimelineBlock, ...]:
        if edit_plan is None:
            return ()
        keep = tuple(
            TimelineBlock(
                block_id=f"keep:{item.range_id}",
                track_id="V1",
                block_type="KEEP_RANGE",
                start_us=item.start_us,
                end_us=item.end_us,
                label="KEEP",
                state=edit_plan.approval_state,
                source_ids=item.source_candidate_ids,
            )
            for item in edit_plan.keep_ranges
        )
        cuts = tuple(
            TimelineBlock(
                block_id=f"approved-cut:{item.range_id}",
                track_id="CUT_OVERLAY",
                block_type="CUT_RANGE",
                start_us=item.start_us,
                end_us=item.end_us,
                label="CUT",
                state=edit_plan.approval_state,
                source_ids=item.source_candidate_ids,
            )
            for item in edit_plan.cut_ranges
        )
        return keep + cuts

    @classmethod
    def build(
        cls,
        *,
        source_duration_us: int,
        subtitle_workspace: SubtitleWorkspace | None = None,
        cut_candidates: Iterable[CutCandidate] = (),
        edit_plan: EditPlan | None = None,
    ) -> EditingProjection:
        if source_duration_us <= 0:
            raise ValueError("source_duration_us must be positive")
        transcript = cls.transcript_rows(subtitle_workspace)
        blocks = (
            cls.subtitle_blocks(subtitle_workspace)
            + cls.candidate_blocks(cut_candidates, edit_plan=edit_plan)
            + cls.edit_plan_blocks(edit_plan)
        )
        blocks = tuple(sorted(blocks, key=lambda item: (item.start_us, item.track_id, item.block_id)))
        return EditingProjection(source_duration_us, transcript, blocks)
