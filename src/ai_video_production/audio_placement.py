"""TASK-026 deterministic audio placement / bed planning foundation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
import re
from typing import Any

from .errors import ProductError, ProductErrorCategory
from .resolve_assembly import AudioPlacement
from .serialization import canonical_json_bytes, sha256_bytes


_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")


class AudioPlacementRole(str, Enum):
    SOURCE = "SOURCE"
    SE = "SE"
    BGM = "BGM"
    AMBIENCE = "AMBIENCE"
    NARRATION = "NARRATION"
    MIX_STEM = "MIX_STEM"


class BedMode(str, Enum):
    PREVIEW = "PREVIEW"
    FULL = "FULL"


@dataclass(frozen=True, slots=True)
class SnapAnchor:
    frame: int
    reason: str

    def __post_init__(self) -> None:
        if self.frame < 0:
            raise ValueError("snap frame must be non-negative")
        if not self.reason.strip() or len(self.reason) > 160 or "\x00" in self.reason:
            raise ValueError("snap reason is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {"frame": self.frame, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class AudioPlacementRequest:
    asset_id: str
    role: AudioPlacementRole
    track_index: int
    source_duration_frames: int
    desired_start_frame: int
    desired_duration_frames: int
    snap_tolerance_frames: int = 0
    snap_anchors: tuple[SnapAnchor, ...] = ()
    loop: bool = False
    fade_in_frames: int = 0
    fade_out_frames: int = 0
    gain_db: float | None = None
    bed_mode: BedMode = BedMode.FULL

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.asset_id):
            raise ValueError("asset_id is invalid")
        if self.track_index < 1:
            raise ValueError("track_index must be >= 1")
        if self.source_duration_frames < 1 or self.desired_duration_frames < 1:
            raise ValueError("source/desired duration must be positive")
        if self.desired_start_frame < 0:
            raise ValueError("desired_start_frame must be non-negative")
        if not 0 <= self.snap_tolerance_frames <= 100_000:
            raise ValueError("snap_tolerance_frames is invalid")
        if self.fade_in_frames < 0 or self.fade_out_frames < 0:
            raise ValueError("fade frames must be non-negative")
        if self.fade_in_frames + self.fade_out_frames > self.desired_duration_frames:
            raise ValueError("combined fades cannot exceed desired duration")
        if self.gain_db is not None and not -120.0 <= self.gain_db <= 24.0:
            raise ValueError("gain_db must be -120..24")
        if self.role is AudioPlacementRole.NARRATION and self.loop:
            raise ValueError("narration placement cannot loop")


@dataclass(frozen=True, slots=True)
class AudioPlacementSegment:
    segment_index: int
    timeline_start_frame: int
    duration_frames: int
    source_start_frame: int = 0

    def __post_init__(self) -> None:
        if self.segment_index < 1 or self.timeline_start_frame < 0 or self.duration_frames < 1 or self.source_start_frame < 0:
            raise ValueError("audio segment is invalid")

    def to_dict(self) -> dict[str, int]:
        return {
            "segment_index": self.segment_index,
            "timeline_start_frame": self.timeline_start_frame,
            "duration_frames": self.duration_frames,
            "source_start_frame": self.source_start_frame,
        }


@dataclass(frozen=True, slots=True)
class AudioPlacementPlan:
    asset_id: str
    role: AudioPlacementRole
    track_index: int
    requested_start_frame: int
    effective_start_frame: int
    desired_duration_frames: int
    source_duration_frames: int
    snapped_to: SnapAnchor | None
    loop: bool
    fade_in_frames: int
    fade_out_frames: int
    gain_db: float | None
    bed_mode: BedMode
    segments: tuple[AudioPlacementSegment, ...]

    @property
    def task010_compatible(self) -> bool:
        gain_ok = self.gain_db is None or abs(self.gain_db) < 1e-12
        return self.fade_in_frames == 0 and self.fade_out_frames == 0 and gain_ok

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "plan_version": "1.0.0",
            "task_owner": "TASK-026",
            "resolve_execution_owner": "TASK-010",
            "asset_id": self.asset_id,
            "role": self.role.value,
            "track_index": self.track_index,
            "requested_start_frame": self.requested_start_frame,
            "effective_start_frame": self.effective_start_frame,
            "desired_duration_frames": self.desired_duration_frames,
            "source_duration_frames": self.source_duration_frames,
            "snapped_to": None if self.snapped_to is None else self.snapped_to.to_dict(),
            "loop": self.loop,
            "fade_in_frames": self.fade_in_frames,
            "fade_out_frames": self.fade_out_frames,
            "gain_db": self.gain_db,
            "bed_mode": self.bed_mode.value,
            "segments": [item.to_dict() for item in self.segments],
            "task010_compatible": self.task010_compatible,
            "external_write_authorized": False,
        }
        body["plan_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    def to_task010_audio_placements(self) -> tuple[AudioPlacement, ...]:
        if not self.task010_compatible:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_TASK010_FEATURE_GAP",
                "TASK-010 generic audio placement cannot silently drop fade/gain metadata",
                ProductErrorCategory.NOT_SUPPORTED,
                details={"fade_in_frames": self.fade_in_frames, "fade_out_frames": self.fade_out_frames, "gain_db": self.gain_db},
            )
        return tuple(
            AudioPlacement(
                asset_id=self.asset_id,
                track_index=self.track_index,
                timeline_start_frame=item.timeline_start_frame,
                duration_frames=item.duration_frames,
            )
            for item in self.segments
        )


class AudioPlacementService:
    @staticmethod
    def _snap(request: AudioPlacementRequest) -> tuple[int, SnapAnchor | None]:
        eligible = [
            item for item in request.snap_anchors
            if abs(item.frame - request.desired_start_frame) <= request.snap_tolerance_frames
        ]
        if not eligible:
            return request.desired_start_frame, None
        selected = min(eligible, key=lambda item: (abs(item.frame - request.desired_start_frame), item.frame, item.reason))
        return selected.frame, selected

    @classmethod
    def compile(cls, request: AudioPlacementRequest) -> AudioPlacementPlan:
        start, snapped = cls._snap(request)
        if request.desired_duration_frames > request.source_duration_frames and not request.loop:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_LOOP_REQUIRED",
                "Requested Audio bed is longer than the source Asset and loop is disabled",
                ProductErrorCategory.VALIDATION,
            )
        remaining = request.desired_duration_frames
        cursor = start
        segments: list[AudioPlacementSegment] = []
        index = 1
        while remaining > 0:
            duration = min(request.source_duration_frames, remaining)
            segments.append(AudioPlacementSegment(index, cursor, duration))
            remaining -= duration
            cursor += duration
            index += 1
        return AudioPlacementPlan(
            asset_id=request.asset_id,
            role=request.role,
            track_index=request.track_index,
            requested_start_frame=request.desired_start_frame,
            effective_start_frame=start,
            desired_duration_frames=request.desired_duration_frames,
            source_duration_frames=request.source_duration_frames,
            snapped_to=snapped,
            loop=request.loop,
            fade_in_frames=request.fade_in_frames,
            fade_out_frames=request.fade_out_frames,
            gain_db=request.gain_db,
            bed_mode=request.bed_mode,
            segments=tuple(segments),
        )
