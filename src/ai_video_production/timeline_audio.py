"""TASK-042 frame-authoritative Timeline audio intent.

This module is metadata-only. Provider, Resolve and Cubase execution remain
outside its authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Iterable, Mapping

from .serialization import canonical_json_bytes, sha256_bytes
from .timebase import FrameRate, FrameRounding


_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_REF_RE = re.compile(r"(?:bai-text|project)://[A-Za-z0-9][A-Za-z0-9._:/-]{0,499}")
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _sha(value: str, name: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _integer(value: object, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} is invalid")
    return value


class TimelineAudioRole(str, Enum):
    NARRATION = "NARRATION"
    SE = "SE"
    BGM = "BGM"
    AMBIENCE = "AMBIENCE"


class AudioSourceIntent(str, Enum):
    IMPORTED = "IMPORTED"
    EXISTING_ASSET = "EXISTING_ASSET"
    GENERATION_INTENT = "GENERATION_INTENT"


class AudioFitPolicy(str, Enum):
    EXACT = "EXACT"
    TRIM = "TRIM"
    LOOP = "LOOP"
    STRETCH = "STRETCH"


class NarrationCueOrigin(str, Enum):
    SCENE_PROPOSAL = "SCENE_PROPOSAL"
    TASK014_ALIGNMENT = "TASK014_ALIGNMENT"
    SRT_IMPORT = "SRT_IMPORT"
    HUMAN = "HUMAN"


class SrtProposalState(str, Enum):
    READY = "READY"
    CONFLICT = "CONFLICT"


class TimelineItemKind(str, Enum):
    MUSIC_PLAN = "MUSIC_PLAN"
    NARRATION_CUE = "NARRATION_CUE"
    AUDIO_CUE = "AUDIO_CUE"
    AUDIO_RANGE = "AUDIO_RANGE"


@dataclass(frozen=True, slots=True)
class AudioSourceBinding:
    slot_id: str
    source_intent: AudioSourceIntent
    candidate_id: str | None = None
    asset_id: str | None = None
    asset_sha256: str | None = None
    source_duration_frames: int | None = None

    def __post_init__(self) -> None:
        _id(self.slot_id, "slot_id")
        values = (self.candidate_id, self.asset_id, self.asset_sha256, self.source_duration_frames)
        if any(value is not None for value in values) != all(value is not None for value in values):
            raise ValueError("Candidate/Asset/source-duration binding must be complete")
        if self.candidate_id is not None:
            _id(self.candidate_id, "candidate_id")
            _id(self.asset_id or "", "asset_id")
            _sha(self.asset_sha256 or "", "asset_sha256")
            _integer(self.source_duration_frames, "source_duration_frames", minimum=1)

    @property
    def candidate_bound(self) -> bool:
        return self.candidate_id is not None

    def to_dict(self) -> dict[str, Any]:
        return {"slot_id": self.slot_id, "source_intent": self.source_intent.value,
                "candidate_id": self.candidate_id, "asset_id": self.asset_id,
                "asset_sha256": self.asset_sha256,
                "source_duration_frames": self.source_duration_frames}


@dataclass(frozen=True, slots=True)
class TimelinePlacementBinding:
    plan_id: str
    plan_revision: int
    plan_sha256: str
    item_id: str
    item_sha256: str
    blueprint_sha256: str

    def __post_init__(self) -> None:
        _id(self.plan_id, "plan_id")
        _integer(self.plan_revision, "plan_revision", minimum=1)
        _id(self.item_id, "item_id")
        for name in ("plan_sha256", "item_sha256", "blueprint_sha256"):
            _sha(getattr(self, name), name)

    def to_dict(self) -> dict[str, Any]:
        return {"plan_id": self.plan_id, "plan_revision": self.plan_revision,
                "plan_sha256": self.plan_sha256, "item_id": self.item_id,
                "item_sha256": self.item_sha256, "blueprint_sha256": self.blueprint_sha256}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TimelinePlacementBinding":
        if set(value) != {"plan_id", "plan_revision", "plan_sha256", "item_id", "item_sha256", "blueprint_sha256"}:
            raise ValueError("Timeline placement binding fields are not exact")
        return cls(value["plan_id"], value["plan_revision"], value["plan_sha256"],
                   value["item_id"], value["item_sha256"], value["blueprint_sha256"])


def _common(item_id: str, lane_id: str, start: int, end: int, source: AudioSourceBinding) -> None:
    _id(item_id, "item_id")
    _id(lane_id, "lane_id")
    _integer(start, "start_frame")
    _integer(end, "end_frame", minimum=1)
    if end <= start or not isinstance(source, AudioSourceBinding):
        raise ValueError("Timeline audio range/source is invalid")


def _mix(duration: int, fade_in: int, fade_out: int, gain: float | None) -> None:
    _integer(fade_in, "fade_in_frames")
    _integer(fade_out, "fade_out_frames")
    if fade_in + fade_out > duration:
        raise ValueError("fade range is invalid")
    if gain is not None and (isinstance(gain, bool) or not isinstance(gain, (int, float)) or not -120 <= gain <= 24):
        raise ValueError("gain_db must be -120..24")


def _item_dict(item: "TimelineAudioItem", extra: Mapping[str, Any]) -> dict[str, Any]:
    body = {"item_kind": item.kind.value, "item_id": item.item_id, "role": item.role.value,
            "lane_id": item.lane_id, "start_frame": item.start_frame, "end_frame": item.end_frame,
            "source": item.source.to_dict(), **extra}
    body["item_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


@dataclass(frozen=True, slots=True)
class MusicPlan:
    item_id: str; lane_id: str; start_frame: int; end_frame: int; source: AudioSourceBinding
    fit_policy: AudioFitPolicy = AudioFitPolicy.EXACT
    fade_in_frames: int = 0; fade_out_frames: int = 0; gain_db: float | None = None
    whole_timeline: bool = False; transition_group_id: str | None = None
    kind = TimelineItemKind.MUSIC_PLAN
    role = TimelineAudioRole.BGM

    def __post_init__(self) -> None:
        _common(self.item_id, self.lane_id, self.start_frame, self.end_frame, self.source)
        _mix(self.end_frame - self.start_frame, self.fade_in_frames, self.fade_out_frames, self.gain_db)
        if not isinstance(self.whole_timeline, bool): raise ValueError("whole_timeline must be boolean")
        if self.transition_group_id is not None: _id(self.transition_group_id, "transition_group_id")

    def to_dict(self) -> dict[str, Any]:
        return _item_dict(self, {"fit_policy": self.fit_policy.value, "fade_in_frames": self.fade_in_frames,
            "fade_out_frames": self.fade_out_frames, "gain_db": self.gain_db,
            "whole_timeline": self.whole_timeline, "transition_group_id": self.transition_group_id})


@dataclass(frozen=True, slots=True)
class NarrationCue:
    item_id: str; lane_id: str; scene_id: str; start_frame: int; end_frame: int
    text_ref: str; text_sha256: str; origin: NarrationCueOrigin; source: AudioSourceBinding
    proposal_state: SrtProposalState = SrtProposalState.READY
    conflict_codes: tuple[str, ...] = (); gain_db: float | None = None
    kind = TimelineItemKind.NARRATION_CUE
    role = TimelineAudioRole.NARRATION

    def __post_init__(self) -> None:
        _common(self.item_id, self.lane_id, self.start_frame, self.end_frame, self.source)
        _id(self.scene_id, "scene_id")
        if not isinstance(self.text_ref, str) or not _REF_RE.fullmatch(self.text_ref): raise ValueError("text_ref is invalid")
        _sha(self.text_sha256, "text_sha256"); _mix(self.end_frame-self.start_frame, 0, 0, self.gain_db)
        for code in self.conflict_codes: _id(code, "conflict_code")
        if (self.proposal_state is SrtProposalState.READY) == bool(self.conflict_codes):
            raise ValueError("proposal state/conflicts are inconsistent")

    def to_dict(self) -> dict[str, Any]:
        return _item_dict(self, {"scene_id": self.scene_id, "text_ref": self.text_ref,
            "text_sha256": self.text_sha256, "text_body_persisted": False, "origin": self.origin.value,
            "proposal_state": self.proposal_state.value, "conflict_codes": list(self.conflict_codes), "gain_db": self.gain_db})


@dataclass(frozen=True, slots=True)
class AudioCue:
    item_id: str; lane_id: str; start_frame: int; duration_frames: int; source: AudioSourceBinding
    gain_db: float | None = None
    kind = TimelineItemKind.AUDIO_CUE
    role = TimelineAudioRole.SE
    @property
    def end_frame(self) -> int: return self.start_frame + self.duration_frames
    def __post_init__(self) -> None:
        _integer(self.duration_frames, "duration_frames", minimum=1)
        _common(self.item_id, self.lane_id, self.start_frame, self.end_frame, self.source)
        _mix(self.duration_frames, 0, 0, self.gain_db)
    def to_dict(self) -> dict[str, Any]: return _item_dict(self, {"duration_frames": self.duration_frames, "gain_db": self.gain_db})


@dataclass(frozen=True, slots=True)
class AudioRange:
    item_id: str; lane_id: str; role: TimelineAudioRole; start_frame: int; end_frame: int; source: AudioSourceBinding
    fit_policy: AudioFitPolicy = AudioFitPolicy.EXACT
    fade_in_frames: int = 0; fade_out_frames: int = 0; gain_db: float | None = None
    kind = TimelineItemKind.AUDIO_RANGE
    def __post_init__(self) -> None:
        if self.role not in {TimelineAudioRole.BGM, TimelineAudioRole.AMBIENCE}: raise ValueError("AudioRange role is invalid")
        _common(self.item_id, self.lane_id, self.start_frame, self.end_frame, self.source)
        _mix(self.end_frame-self.start_frame, self.fade_in_frames, self.fade_out_frames, self.gain_db)
    def to_dict(self) -> dict[str, Any]:
        return _item_dict(self, {"fit_policy": self.fit_policy.value, "fade_in_frames": self.fade_in_frames,
            "fade_out_frames": self.fade_out_frames, "gain_db": self.gain_db})


TimelineAudioItem = MusicPlan | NarrationCue | AudioCue | AudioRange


@dataclass(frozen=True, slots=True)
class TimelineAudioPlan:
    project_id: str; plan_id: str; revision: int; blueprint_id: str; blueprint_sha256: str
    timeline_rate: FrameRate; target_duration_frames: int; items: tuple[TimelineAudioItem, ...]
    previous_plan_sha256: str | None = None

    def __post_init__(self) -> None:
        _id(self.project_id, "project_id"); _id(self.plan_id, "plan_id"); _id(self.blueprint_id, "blueprint_id")
        _sha(self.blueprint_sha256, "blueprint_sha256"); _integer(self.revision, "revision", minimum=1)
        _integer(self.target_duration_frames, "target_duration_frames", minimum=1)
        if not isinstance(self.timeline_rate, FrameRate): raise ValueError("timeline_rate is invalid")
        if (self.revision == 1) != (self.previous_plan_sha256 is None): raise ValueError("previous plan chain is invalid")
        if self.previous_plan_sha256 is not None: _sha(self.previous_plan_sha256, "previous_plan_sha256")
        if len({item.item_id for item in self.items}) != len(self.items): raise ValueError("item IDs must be unique")
        for item in self.items:
            if item.end_frame > self.target_duration_frames: raise ValueError("item exceeds target duration")
            if isinstance(item, MusicPlan) and item.whole_timeline and (item.start_frame != 0 or item.end_frame != self.target_duration_frames):
                raise ValueError("whole-timeline MusicPlan must cover the exact Timeline")
        by_lane: dict[tuple[TimelineAudioRole, str], list[TimelineAudioItem]] = {}
        for item in self.items: by_lane.setdefault((item.role, item.lane_id), []).append(item)
        for (role, _lane), rows in by_lane.items():
            rows.sort(key=lambda row: (row.start_frame, row.end_frame, row.item_id))
            for left, right in zip(rows, rows[1:]):
                allowed = (role is TimelineAudioRole.BGM and isinstance(left, MusicPlan) and isinstance(right, MusicPlan)
                           and left.transition_group_id is not None and left.transition_group_id == right.transition_group_id)
                if right.start_frame < left.end_frame and not allowed: raise ValueError(f"overlap is not allowed on {role.value} lane")

    def item(self, item_id: str) -> TimelineAudioItem:
        return next(item for item in self.items if item.item_id == item_id)

    def to_dict(self) -> dict[str, Any]:
        body = {"timeline_audio_plan_version": "1.0.0", "task_owner": "TASK-042/P-V6-4",
          "project_id": self.project_id, "plan_id": self.plan_id, "revision": self.revision,
          "previous_plan_sha256": self.previous_plan_sha256, "blueprint_id": self.blueprint_id,
          "blueprint_sha256": self.blueprint_sha256,
          "timeline_rate": {"numerator": self.timeline_rate.numerator, "denominator": self.timeline_rate.denominator},
          "target_duration_frames": self.target_duration_frames,
          "items": [item.to_dict() for item in sorted(self.items, key=lambda row: row.item_id)],
          "timeline_frames_authoritative": True, "srt_timing_authoritative": False,
          "provider_execution_started": False, "candidate_mutation_started": False,
          "task026_compile_started": False, "resolve_mutation_started": False, "cubase_mutation_started": False}
        body["plan_sha256"] = sha256_bytes(canonical_json_bytes(body)); return body

    @property
    def plan_sha256(self) -> str: return self.to_dict()["plan_sha256"]
    def placement_binding(self, item_id: str) -> TimelinePlacementBinding:
        item = self.item(item_id)
        return TimelinePlacementBinding(self.plan_id, self.revision, self.plan_sha256, item.item_id,
                                        item.to_dict()["item_sha256"], self.blueprint_sha256)


@dataclass(frozen=True, slots=True)
class ImportedSrtCue:
    cue_index: int; start_ms: int; end_ms: int; text_ref: str; text_sha256: str; scene_id: str
    def __post_init__(self) -> None:
        _integer(self.cue_index, "cue_index", minimum=1); _integer(self.start_ms, "start_ms")
        _integer(self.end_ms, "end_ms", minimum=1)
        if self.end_ms <= self.start_ms or not _REF_RE.fullmatch(self.text_ref): raise ValueError("SRT cue is invalid")
        _sha(self.text_sha256, "text_sha256"); _id(self.scene_id, "scene_id")


@dataclass(frozen=True, slots=True)
class SrtCueProposal:
    cue_index: int; scene_id: str; start_frame: int; end_frame: int; text_ref: str; text_sha256: str
    start_rounding_delta_us: int; end_rounding_delta_us: int; state: SrtProposalState; conflict_codes: tuple[str, ...]
    def to_dict(self) -> dict[str, Any]:
        return {"cue_index": self.cue_index, "scene_id": self.scene_id, "start_frame": self.start_frame,
          "end_frame": self.end_frame, "text_ref": self.text_ref, "text_sha256": self.text_sha256,
          "text_body_persisted": False, "start_rounding_delta_us": self.start_rounding_delta_us,
          "end_rounding_delta_us": self.end_rounding_delta_us, "state": self.state.value,
          "conflict_codes": list(self.conflict_codes)}


@dataclass(frozen=True, slots=True)
class SrtProposal:
    source_srt_sha256: str; blueprint_sha256: str; cues: tuple[SrtCueProposal, ...]
    def __post_init__(self) -> None: _sha(self.source_srt_sha256, "source_srt_sha256"); _sha(self.blueprint_sha256, "blueprint_sha256")
    @property
    def state(self) -> SrtProposalState:
        return SrtProposalState.CONFLICT if any(c.state is SrtProposalState.CONFLICT for c in self.cues) else SrtProposalState.READY
    def to_dict(self) -> dict[str, Any]:
        body = {"srt_proposal_version": "1.0.0", "source_srt_sha256": self.source_srt_sha256,
          "blueprint_sha256": self.blueprint_sha256, "state": self.state.value,
          "cues": [cue.to_dict() for cue in self.cues], "srt_body_persisted": False,
          "scene_timing_mutation_authorized": False}
        body["proposal_sha256"] = sha256_bytes(canonical_json_bytes(body)); return body


class SrtProposalService:
    @staticmethod
    def import_cues(cues: Iterable[ImportedSrtCue], *, source_srt_sha256: str, blueprint_sha256: str,
                    timeline_rate: FrameRate, target_duration_frames: int,
                    scene_ranges: Mapping[str, tuple[int, int]]) -> SrtProposal:
        _sha(source_srt_sha256, "source_srt_sha256"); _sha(blueprint_sha256, "blueprint_sha256")
        rows: list[SrtCueProposal] = []; previous_end = 0
        for cue in sorted(tuple(cues), key=lambda value: value.cue_index):
            start_us, end_us = cue.start_ms*1000, cue.end_ms*1000
            start = timeline_rate.us_to_frame(start_us, rounding=FrameRounding.FLOOR)
            end = timeline_rate.us_to_frame(end_us, rounding=FrameRounding.CEIL)
            conflicts: list[str] = []; scene_range = scene_ranges.get(cue.scene_id)
            if scene_range is None: conflicts.append("SCENE_NOT_FOUND")
            elif start < scene_range[0] or end > scene_range[1]: conflicts.append("CUE_CROSSES_SCENE_BOUNDARY")
            if end <= start or end > target_duration_frames: conflicts.append("CUE_OUTSIDE_TIMELINE")
            if start < previous_end: conflicts.append("NARRATION_OVERLAP")
            previous_end = max(previous_end, end)
            rows.append(SrtCueProposal(cue.cue_index, cue.scene_id, start, end, cue.text_ref, cue.text_sha256,
                timeline_rate.frame_to_us(start, rounding=FrameRounding.NEAREST)-start_us,
                timeline_rate.frame_to_us(end, rounding=FrameRounding.NEAREST)-end_us,
                SrtProposalState.CONFLICT if conflicts else SrtProposalState.READY, tuple(sorted(set(conflicts)))))
        return SrtProposal(source_srt_sha256, blueprint_sha256, tuple(rows))


__all__ = ["AudioCue", "AudioFitPolicy", "AudioRange", "AudioSourceBinding", "AudioSourceIntent",
 "ImportedSrtCue", "MusicPlan", "NarrationCue", "NarrationCueOrigin", "SrtCueProposal", "SrtProposal",
 "SrtProposalService", "SrtProposalState", "TimelineAudioPlan", "TimelineAudioRole", "TimelinePlacementBinding"]
