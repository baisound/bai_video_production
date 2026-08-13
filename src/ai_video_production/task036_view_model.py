"""TASK-036 transport-neutral view model for the professional NLE shell."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .desktop_shell import ShellSnapshot
from .desktop_shell_projection import EditingProjection, TimelineBlock


def _clock(microseconds: int) -> str:
    if microseconds < 0:
        raise ValueError("microseconds must be >= 0")
    milliseconds = microseconds // 1000
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


@dataclass(frozen=True, slots=True)
class Task036DesktopViewModel:
    shell: ShellSnapshot
    projection: EditingProjection | None = None

    @staticmethod
    def _block(block: TimelineBlock, duration_us: int) -> dict[str, Any]:
        left = (block.start_us / duration_us) * 100.0
        width = ((block.end_us - block.start_us) / duration_us) * 100.0
        return {
            **block.to_dict(),
            "start_label": _clock(block.start_us),
            "end_label": _clock(block.end_us),
            "left_percent": round(left, 6),
            "width_percent": round(width, 6),
        }

    def to_dict(self) -> dict[str, Any]:
        shell = self.shell.to_dict()
        if self.projection is None:
            transcript_rows: list[dict[str, Any]] = []
            timeline_tracks: dict[str, list[dict[str, Any]]] = {}
            duration_us = None
            duration_label = None
        else:
            duration_us = self.projection.source_duration_us
            duration_label = _clock(duration_us)
            transcript_rows = [
                {
                    **row.to_dict(),
                    "start_label": _clock(row.start_us),
                    "end_label": _clock(row.end_us),
                }
                for row in self.projection.transcript_rows
            ]
            timeline_tracks = {}
            for block in self.projection.timeline_blocks:
                timeline_tracks.setdefault(block.track_id, []).append(self._block(block, duration_us))
        return {
            "view_model_version": "1.0.0",
            "task_owner": "TASK-036",
            "visual_contract": "VREW_PREMIERE_RESOLVE_NLE",
            "shell": shell,
            "source_duration_us": duration_us,
            "source_duration_label": duration_label,
            "transcript_rows": transcript_rows,
            "timeline_tracks": timeline_tracks,
            "ai_chat_is_primary_canvas": False,
        }
