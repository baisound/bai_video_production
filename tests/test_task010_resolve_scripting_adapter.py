from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from ai_video_production.edit_plan import CandidateReviewDecision, EditDecision, EditPlanService
from ai_video_production.errors import ProductError
from ai_video_production.resolve_assembly import ResolveAssemblyService, ResolveAssetBindings, ResolveScriptingAssemblyAdapter
from ai_video_production.timebase import FrameRate

ASSET_ID = "ASSET-00000000000000000000000000"
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def approved_plan():
    manifest = CutCandidateManifest(
        ASSET_ID, SHA_A, 48_000, 4_000_000, SHA_B, None,
        (CutCandidate("cut-000001", CutCandidateKind.SILENCE, 1_000_000, 2_000_000, 90, ("FFMPEG_SILENCEDETECT",)),),
        (),
    )
    edit = EditPlanService.build(
        manifest,
        reviews=(CandidateReviewDecision("cut-000001", EditDecision.CUT),),
        approve=True,
        approved_by="owner",
    )
    return ResolveAssemblyService.compile(edit, timeline_rate=FrameRate(30))


class Timeline:
    def __init__(self, name: str, marker_hash: str | None = None, timeline_rate: str = "30", start_frame: int = 86_400):
        self.name = name
        self.timeline_rate = timeline_rate
        self.start_frame = start_frame
        self.markers = {}
        if marker_hash:
            self.markers[0] = {"name": "BAI AUTO ASSEMBLY", "customData": marker_hash}
    def GetName(self): return self.name
    def GetMarkers(self): return self.markers
    def GetStartFrame(self): return self.start_frame
    def GetSetting(self, key): return self.timeline_rate if key == "timelineFrameRate" else ""
    def AddMarker(self, frame, color, name, note, duration, custom):
        self.markers[frame] = {"name": name, "customData": custom}
        return True


class MediaPool:
    def __init__(self, project):
        self.project = project
        self.append_rows = []
    def ImportMedia(self, paths): return [object() for _ in paths]
    def CreateEmptyTimeline(self, name):
        timeline = Timeline(name, timeline_rate=self.project.timeline_rate)
        self.project.timelines.append(timeline)
        return timeline
    def AppendToTimeline(self, rows):
        self.append_rows.extend(rows)
        return [object() for _ in rows]


class Project:
    def __init__(self, timelines=(), timeline_rate: str = "30"):
        self.timelines = list(timelines)
        self.timeline_rate = timeline_rate
        self.media_pool = MediaPool(self)
    def GetTimelineCount(self): return len(self.timelines)
    def GetTimelineByIndex(self, index): return self.timelines[index - 1]
    def GetMediaPool(self): return self.media_pool
    def GetSetting(self, key): return self.timeline_rate if key == "timelineFrameRate" else ""
    def SetCurrentTimeline(self, timeline): return True


class Manager:
    def __init__(self, project): self.project = project
    def GetCurrentProject(self): return self.project
    def SaveProject(self): return True


class Resolve:
    def __init__(self, project): self.manager = Manager(project)
    def GetProjectManager(self): return self.manager


class Loader:
    def __init__(self, project): self.resolve = Resolve(project)
    def connect(self): return self.resolve, object()


def test_adapter_requires_source_rate_before_any_timeline_mutation(tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    project = Project()
    adapter = ResolveScriptingAssemblyAdapter(Loader(project))
    with pytest.raises(ProductError) as exc:
        ResolveAssemblyService.execute(
            approved_plan(), adapter=adapter,
            bindings=ResolveAssetBindings(source),
            explicit_external_write_authorization=True,
        )
    assert exc.value.code == "ERR_RESOLVE_SOURCE_FRAME_RATE_REQUIRED"
    assert project.timelines == []


def test_adapter_uses_source_rate_and_writes_idempotency_marker(tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    project = Project()
    adapter = ResolveScriptingAssemblyAdapter(Loader(project))
    plan = approved_plan()
    result = ResolveAssemblyService.execute(
        plan, adapter=adapter,
        bindings=ResolveAssetBindings(source, source_frame_rate=FrameRate(60)),
        explicit_external_write_authorization=True,
    )
    assert result.status == "APPLIED"
    assert project.timelines[0].name == plan.timeline_name
    assert adapter.applied_hash(plan.timeline_name) == plan.to_dict()["assembly_sha256"]
    # First kept second maps to 60 source frames, while the timeline remains 30 fps.
    assert project.media_pool.append_rows[0]["endFrame"] == 59
    # Primary source placement must no longer request video-only mediaType=1.
    assert "mediaType" not in project.media_pool.append_rows[0]
    assert "mediaType" not in project.media_pool.append_rows[1]
    # Resolve Timelines commonly start at 01:00:00:00. Planned frames are
    # relative to the Plan origin and must be offset by the real start frame.
    assert [row["recordFrame"] for row in project.media_pool.append_rows] == [86_400, 86_430]
    assert plan.to_dict()["assembly_plan_version"] == "1.3.0"
    assert plan.to_dict()["record_frame_basis"] == "RESOLVE_TIMELINE_START_RELATIVE"


def test_existing_deterministic_timeline_without_marker_fails_closed(tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    plan = approved_plan()
    project = Project((Timeline(plan.timeline_name),))
    adapter = ResolveScriptingAssemblyAdapter(Loader(project))
    with pytest.raises(ProductError) as exc:
        ResolveAssemblyService.execute(
            plan, adapter=adapter,
            bindings=ResolveAssetBindings(source, source_frame_rate=FrameRate(30)),
            explicit_external_write_authorization=True,
        )
    assert exc.value.code == "ERR_RESOLVE_PARTIAL_AUTOMATION_TIMELINE"
    assert len(project.timelines) == 1


def test_adapter_rejects_plan_rate_mismatch_before_media_or_timeline_mutation(tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    project = Project(timeline_rate="24")
    adapter = ResolveScriptingAssemblyAdapter(Loader(project))
    with pytest.raises(ProductError) as exc:
        ResolveAssemblyService.execute(
            approved_plan(),
            adapter=adapter,
            bindings=ResolveAssetBindings(source, source_frame_rate=FrameRate(30)),
            explicit_external_write_authorization=True,
        )
    assert exc.value.code == "ERR_RESOLVE_PROJECT_TIMELINE_RATE_MISMATCH"
    assert project.timelines == []
    assert project.media_pool.append_rows == []


def test_adapter_reads_common_resolve_fractional_rate_aliases():
    assert ResolveScriptingAssemblyAdapter._resolve_rate_from_setting("23.976") == FrameRate(24_000, 1_001)
    assert ResolveScriptingAssemblyAdapter._resolve_rate_from_setting("29.97") == FrameRate(30_000, 1_001)
    assert ResolveScriptingAssemblyAdapter._resolve_rate_from_setting("59.94") == FrameRate(60_000, 1_001)
