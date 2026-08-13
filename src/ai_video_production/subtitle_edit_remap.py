"""Edit-aware subtitle timing for TASK-010 Resolve assembly."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
from typing import Any, Iterable

from .errors import ProductError, ProductErrorCategory
from .resolve_subtitle_handoff import ResolveSubtitlePlacementPlan
from .serialization import sha256_bytes
from .subtitle_workspace import SrtWorkspaceCodec
from .timebase import FrameRate, FrameRounding
from .timeline_mapping import TimelineMappingPlan


class SubtitleEditAction(str, Enum):
    KEEP = "KEEP"
    DROP_CUT = "DROP_CUT"


@dataclass(frozen=True, slots=True)
class ResolveSubtitleAssemblyCue:
    cue_id: str
    source_start_frame: int
    source_end_frame: int
    timeline_start_frame: int | None
    timeline_end_frame: int | None
    text_sha256: str
    action: SubtitleEditAction

    def __post_init__(self) -> None:
        if self.source_start_frame < 0 or self.source_end_frame <= self.source_start_frame:
            raise ValueError("subtitle source frame range must be positive")
        if self.action is SubtitleEditAction.KEEP:
            if self.timeline_start_frame is None or self.timeline_end_frame is None:
                raise ValueError("kept subtitle cue requires a Timeline range")
            if self.timeline_start_frame < 0 or self.timeline_end_frame <= self.timeline_start_frame:
                raise ValueError("subtitle Timeline range must be positive")
        elif self.timeline_start_frame is not None or self.timeline_end_frame is not None:
            raise ValueError("dropped subtitle cue must not have a Timeline range")
        if not self.text_sha256.startswith("sha256:") or len(self.text_sha256) != 71:
            raise ValueError("subtitle text_sha256 is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "cue_id": self.cue_id,
            "source_range_frames": {
                "start": self.source_start_frame,
                "end_exclusive": self.source_end_frame,
            },
            "timeline_range_frames": None if self.timeline_start_frame is None else {
                "start": self.timeline_start_frame,
                "end_exclusive": self.timeline_end_frame,
            },
            "text_sha256": self.text_sha256,
            "action": self.action.value,
        }


class SubtitleEditRemapService:
    @staticmethod
    def build(
        subtitle_plan: ResolveSubtitlePlacementPlan,
        timeline_mapping: TimelineMappingPlan,
    ) -> tuple[ResolveSubtitleAssemblyCue, ...]:
        if subtitle_plan.timeline_rate != timeline_mapping.timeline_rate:
            raise ProductError(
                "ERR_RESOLVE_SUBTITLE_RATE_MISMATCH",
                "subtitle and edit timelines must use the same rational frame rate",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if subtitle_plan.timeline_origin_frame != timeline_mapping.timeline_origin_frame:
            raise ProductError(
                "ERR_RESOLVE_SUBTITLE_ORIGIN_MISMATCH",
                "subtitle and edit timelines must share the same origin frame",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if subtitle_plan.track_index != 1:
            raise ProductError(
                "ERR_RESOLVE_SUBTITLE_TRACK_UNVERIFIED",
                "TASK-010 native validation currently supports subtitle track 1 only",
                ProductErrorCategory.NOT_SUPPORTED,
                details={"track_index": subtitle_plan.track_index},
            )

        rate = timeline_mapping.timeline_rate
        origin = timeline_mapping.timeline_origin_frame
        keep_spans: list[tuple[int, int, Any]] = []
        for placement in timeline_mapping.placements:
            source_start = origin + rate.us_to_frame(
                placement.source_start_us, rounding=FrameRounding.FLOOR
            )
            source_end = source_start + (
                placement.timeline_end_frame - placement.timeline_start_frame
            )
            keep_spans.append((source_start, source_end, placement))

        out: list[ResolveSubtitleAssemblyCue] = []
        for cue in subtitle_plan.placements:
            intersections: list[tuple[int, int, Any, int]] = []
            for source_start, source_end, placement in keep_spans:
                left = max(cue.record_start_frame, source_start)
                right = min(cue.record_end_frame, source_end)
                if left < right:
                    intersections.append((left, right, placement, source_start))

            text_hash = sha256_bytes(cue.text.encode("utf-8"))
            if not intersections:
                out.append(ResolveSubtitleAssemblyCue(
                    cue.cue_id,
                    cue.record_start_frame,
                    cue.record_end_frame,
                    None,
                    None,
                    text_hash,
                    SubtitleEditAction.DROP_CUT,
                ))
                continue

            if len(intersections) != 1:
                raise ProductError(
                    "ERR_RESOLVE_SUBTITLE_CUT_BOUNDARY_REVIEW_REQUIRED",
                    "subtitle cue crosses multiple kept ranges and requires Human re-review",
                    ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                    details={"cue_id": cue.cue_id},
                )
            left, right, placement, source_start = intersections[0]
            if left != cue.record_start_frame or right != cue.record_end_frame:
                raise ProductError(
                    "ERR_RESOLVE_SUBTITLE_CUT_BOUNDARY_REVIEW_REQUIRED",
                    "subtitle cue intersects an approved cut boundary and requires Human re-review",
                    ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                    details={"cue_id": cue.cue_id},
                )
            timeline_start = placement.timeline_start_frame + (left - source_start)
            timeline_end = timeline_start + (right - left)
            if timeline_end > placement.timeline_end_frame:
                raise ProductError(
                    "ERR_RESOLVE_SUBTITLE_REMAP_OUT_OF_RANGE",
                    "edit-aware subtitle remap exceeded the compiled keep placement",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"cue_id": cue.cue_id},
                )
            out.append(ResolveSubtitleAssemblyCue(
                cue.cue_id,
                cue.record_start_frame,
                cue.record_end_frame,
                timeline_start,
                timeline_end,
                text_hash,
                SubtitleEditAction.KEEP,
            ))
        return tuple(out)

    @staticmethod
    def _start_ms(frame: int, *, rate: FrameRate, origin: int) -> int:
        us = rate.frame_to_us(frame - origin, rounding=FrameRounding.CEIL)
        return (us + 999) // 1000

    @staticmethod
    def _end_ms(frame: int, *, rate: FrameRate, origin: int) -> int:
        us = rate.frame_to_us(frame - origin, rounding=FrameRounding.FLOOR)
        return us // 1000

    @staticmethod
    def _format_ms(value: int) -> str:
        hours, rem = divmod(value, 3_600_000)
        minutes, rem = divmod(rem, 60_000)
        seconds, millis = divmod(rem, 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

    @staticmethod
    def verify_and_write_derived_srt(
        source_srt_path: str | Path,
        target_srt_path: str | Path,
        *,
        cues: Iterable[ResolveSubtitleAssemblyCue],
        timeline_rate: FrameRate,
        timeline_origin_frame: int,
    ) -> Path:
        source = Path(source_srt_path).expanduser().resolve()
        if source.is_symlink() or not source.is_file() or source.stat().st_size <= 0:
            raise ProductError(
                "ERR_RESOLVE_SUBTITLE_BINDING_INVALID",
                "reviewed subtitle binding must be a non-empty regular SRT file",
                ProductErrorCategory.VALIDATION,
            )
        target = Path(target_srt_path).expanduser()
        if target.exists() and target.is_symlink():
            raise ProductError(
                "ERR_RESOLVE_SUBTITLE_DERIVED_PATH_INVALID",
                "derived subtitle target must not be a symlink",
                ProductErrorCategory.VALIDATION,
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        target = target.resolve()
        if target == source:
            raise ProductError(
                "ERR_RESOLVE_SUBTITLE_DERIVED_PATH_CONFLICT",
                "derived subtitle target must not overwrite the reviewed source SRT",
                ProductErrorCategory.VALIDATION,
            )

        planned = tuple(cues)
        workspace = SrtWorkspaceCodec.import_path(source)
        if len(workspace.cues) != len(planned):
            raise ProductError(
                "ERR_RESOLVE_SUBTITLE_BINDING_MISMATCH",
                "reviewed SRT cue count does not match the approved subtitle plan",
                ProductErrorCategory.DATA_INTEGRITY,
            )

        rendered: list[str] = []
        output_index = 1
        for source_cue, planned_cue in zip(workspace.cues, planned):
            source_start = timeline_origin_frame + timeline_rate.us_to_frame(
                source_cue.start_ms * 1000, rounding=FrameRounding.FLOOR
            )
            source_end = timeline_origin_frame + timeline_rate.us_to_frame(
                source_cue.end_ms * 1000, rounding=FrameRounding.CEIL
            )
            if (
                source_start != planned_cue.source_start_frame
                or source_end != planned_cue.source_end_frame
                or sha256_bytes(source_cue.text.encode("utf-8")) != planned_cue.text_sha256
            ):
                raise ProductError(
                    "ERR_RESOLVE_SUBTITLE_BINDING_MISMATCH",
                    "reviewed SRT content/timing does not match the approved subtitle plan",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"cue_id": planned_cue.cue_id},
                )
            if planned_cue.action is SubtitleEditAction.DROP_CUT:
                continue
            assert planned_cue.timeline_start_frame is not None
            assert planned_cue.timeline_end_frame is not None
            start_ms = SubtitleEditRemapService._start_ms(
                planned_cue.timeline_start_frame,
                rate=timeline_rate,
                origin=timeline_origin_frame,
            )
            end_ms = SubtitleEditRemapService._end_ms(
                planned_cue.timeline_end_frame,
                rate=timeline_rate,
                origin=timeline_origin_frame,
            )
            if end_ms <= start_ms:
                raise ProductError(
                    "ERR_RESOLVE_SUBTITLE_DERIVED_TIMING_INVALID",
                    "derived subtitle cue collapsed below one millisecond",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"cue_id": planned_cue.cue_id},
                )
            rendered.append(
                f"{output_index}\n"
                f"{SubtitleEditRemapService._format_ms(start_ms)} --> "
                f"{SubtitleEditRemapService._format_ms(end_ms)}\n"
                f"{source_cue.text}"
            )
            output_index += 1

        payload = "\n\n".join(rendered) + ("\n" if rendered else "")
        tmp = target.with_suffix(target.suffix + ".tmp-bvp")
        tmp.write_text(payload, encoding="utf-8", newline="\n")
        os.replace(tmp, target)
        return target
