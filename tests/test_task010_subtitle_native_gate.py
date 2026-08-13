from __future__ import annotations

from ai_video_production.serialization import sha256_bytes
from ai_video_production.subtitle_edit_remap import ResolveSubtitleAssemblyCue, SubtitleEditAction
from ai_video_production.task010_subtitle_native_gate import inspect_subtitle_semantics


class Item:
    def __init__(self, start, end, name): self.start, self.end, self.name = start, end, name
    def GetStart(self): return self.start
    def GetEnd(self): return self.end
    def GetName(self): return self.name


class Timeline:
    def __init__(self, items, start=86400): self.items, self.start = items, start
    def GetStartFrame(self): return self.start
    def GetTrackCount(self, track_type): return 1
    def GetItemListInTrack(self, track_type, index): return self.items


def test_semantic_inspection_uses_timeline_start_as_absolute_offset():
    expected = (
        ResolveSubtitleAssemblyCue("a", 6, 18, 6, 18, sha256_bytes(b"BAI subtitle alpha"), SubtitleEditAction.KEEP),
        ResolveSubtitleAssemblyCue("b", 54, 71, 30, 47, sha256_bytes(b"BAI subtitle beta"), SubtitleEditAction.KEEP),
    )
    timeline = Timeline([
        Item(86406, 86418, "BAI subtitle alpha"),
        Item(86430, 86447, "BAI subtitle beta"),
    ])
    observed = inspect_subtitle_semantics(timeline, expected_cues=expected, timeline_origin_frame=0)
    assert observed.passed is True
    assert observed.timing_verified is True
    assert observed.text_verified is True
