"""Adapters from accepted TASK-036/TASK-042 truth into TASK-044 read models."""

from __future__ import annotations

from typing import Iterable

from .desktop_shell_projection import EditingProjection
from .interactive_timeline import (InteractiveTimeline, InteractiveTimelineClip,
    TimelineMediaKind, TimelineTrack, TimelineTrackRole)
from .serialization import canonical_json_bytes, sha256_bytes
from .timebase import FrameRate, FrameRounding
from .timeline_audio import TimelineAudioPlan, TimelineAudioRole


_LEGACY_TRACKS = {
    "V1": (0, TimelineTrackRole.VIDEO, TimelineMediaKind.VIDEO, "Video 1", True),
    "S1": (100, TimelineTrackRole.SUBTITLE, TimelineMediaKind.TEXT, "Subtitle 1", False),
    "CUT_OVERLAY": (200, TimelineTrackRole.OVERLAY, TimelineMediaKind.CONTROL, "Cut review", False),
}


class InteractiveTimelineProjectionService:
    @staticmethod
    def from_editing_projection(*, project_id: str, timeline_id: str,
                                timeline_rate: FrameRate,
                                projection: EditingProjection) -> InteractiveTimeline:
        duration = timeline_rate.us_to_frame(projection.source_duration_us, rounding=FrameRounding.CEIL)
        used = sorted({block.track_id for block in projection.timeline_blocks})
        tracks = []
        for fallback_order, track_id in enumerate(used, 300):
            order, role, media, label, required = _LEGACY_TRACKS.get(
                track_id, (fallback_order, TimelineTrackRole.OVERLAY, TimelineMediaKind.CONTROL, track_id, False))
            tracks.append(TimelineTrack(track_id, order, role, media, label, required))
        clips = []
        for block in projection.timeline_blocks:
            start = timeline_rate.us_to_frame(block.start_us, rounding=FrameRounding.FLOOR)
            end = timeline_rate.us_to_frame(block.end_us, rounding=FrameRounding.CEIL)
            source = block.to_dict()
            clips.append(InteractiveTimelineClip(
                clip_id="legacy:" + block.block_id,
                track_id=block.track_id,
                start_frame=start,
                end_frame=max(start + 1, end),
                source_owner="TASK-036",
                source_ref=block.block_id,
                source_sha256=sha256_bytes(canonical_json_bytes(source)),
                label=block.label,
                state=block.state,
                review_candidate_id=(block.source_ids[0] if block.block_type == "CUT_CANDIDATE" and block.source_ids else None),
            ))
        return InteractiveTimeline(project_id, timeline_id, timeline_rate, duration,
            tuple(sorted(tracks, key=lambda item: (item.order, item.track_id))), tuple(clips))

    @staticmethod
    def from_audio_plan(plan: TimelineAudioPlan) -> InteractiveTimeline:
        role_order = {TimelineAudioRole.NARRATION: 300, TimelineAudioRole.SE: 400,
                      TimelineAudioRole.BGM: 500, TimelineAudioRole.AMBIENCE: 600}
        lane_roles = {(item.lane_id, item.role) for item in plan.items}
        tracks = tuple(TimelineTrack(
            track_id=f"audio:{role.value.lower()}:{lane}",
            order=role_order[role] + index,
            role=TimelineTrackRole.AUDIO,
            media_kind=TimelineMediaKind.AUDIO,
            label=f"{role.value} / {lane}",
        ) for index, (lane, role) in enumerate(sorted(lane_roles, key=lambda value: (role_order[value[1]], value[0]))))
        track_by_lane = {(track.label.split(" / ", 1)[1], TimelineAudioRole(track.label.split(" / ", 1)[0])): track.track_id for track in tracks}
        clips = tuple(InteractiveTimelineClip(
            clip_id="audio:" + item.item_id,
            track_id=track_by_lane[(item.lane_id, item.role)],
            start_frame=item.start_frame,
            end_frame=item.end_frame,
            source_owner="TASK-042",
            source_ref=item.item_id,
            source_sha256=item.to_dict()["item_sha256"],
            label=item.role.value,
            state=getattr(item, "proposal_state", "CURRENT").value if hasattr(getattr(item, "proposal_state", None), "value") else "CURRENT",
        ) for item in plan.items)
        return InteractiveTimeline(plan.project_id, plan.plan_id, plan.timeline_rate,
                                   plan.target_duration_frames, tracks, clips)

    @staticmethod
    def compose(*timelines: InteractiveTimeline) -> InteractiveTimeline:
        if not timelines:
            raise ValueError("at least one Timeline is required")
        first = timelines[0]
        for item in timelines[1:]:
            if (item.project_id, item.timeline_id, item.timeline_rate, item.duration_frames) != (
                first.project_id, first.timeline_id, first.timeline_rate, first.duration_frames):
                raise ValueError("Timeline projections are not composable")
        by_track = {}
        clips = []
        for timeline in timelines:
            for track in timeline.tracks:
                current = by_track.get(track.track_id)
                if current is not None and current != track:
                    raise ValueError("track identity collision")
                by_track[track.track_id] = track
            clips.extend(timeline.clips)
        return InteractiveTimeline(first.project_id, first.timeline_id, first.timeline_rate,
            first.duration_frames, tuple(sorted(by_track.values(), key=lambda value: (value.order, value.track_id))), tuple(clips))


__all__ = ["InteractiveTimelineProjectionService"]
