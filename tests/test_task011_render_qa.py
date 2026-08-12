from __future__ import annotations

from pathlib import Path

from ai_video_production.media_probe import MediaProbeResult
from ai_video_production.render_qa import LoudnessMeasurement, LoudnessProfile, RenderQAService
from ai_video_production.timebase import FrameRate


class FakeProbe:
    def __init__(self, duration_us=3_000_000, *, audio=True, video=True):
        self.duration_us = duration_us
        self.audio = audio
        self.video = video
    def probe(self, path):
        streams = []
        if self.video:
            streams.append({"codec_type": "video", "codec_name": "h264"})
        if self.audio:
            streams.append({"codec_type": "audio", "codec_name": "aac"})
        return MediaProbeResult("mp4", self.duration_us, Path(path).stat().st_size, None, tuple(streams))


class FakeLoudness:
    def __init__(self, measurement):
        self.measurement = measurement
    def analyze(self, path, *, profile):
        return self.measurement


def test_render_qa_passes_duration_stream_and_loudness_checks(tmp_path: Path):
    render = tmp_path / "render.mp4"
    render.write_bytes(b"render-bytes")
    service = RenderQAService(
        media_probe=FakeProbe(),
        loudness_analyzer=FakeLoudness(LoudnessMeasurement(-15.5, -1.5, 5.0)),
    )
    report = service.verify(
        render,
        expected_duration_frames=90,
        timeline_rate=FrameRate(30),
        loudness_profile=LoudnessProfile(target_lufs=-16.0, tolerance_lu=1.0, max_true_peak_dbtp=-1.0),
    )
    assert report.status == "PASS"
    assert report.to_dict()["render_path_persisted"] is False
    assert report.to_dict()["artifact_sha256"].startswith("sha256:")


def test_render_qa_reports_fail_without_throwing_for_quality_miss(tmp_path: Path):
    render = tmp_path / "render.mp4"
    render.write_bytes(b"render-bytes")
    service = RenderQAService(
        media_probe=FakeProbe(duration_us=2_000_000),
        loudness_analyzer=FakeLoudness(LoudnessMeasurement(-10.0, 0.0, 5.0)),
    )
    report = service.verify(
        render,
        expected_duration_frames=90,
        timeline_rate=FrameRate(30),
        duration_tolerance_frames=1,
        loudness_profile=LoudnessProfile(target_lufs=-16.0, tolerance_lu=1.0, max_true_peak_dbtp=-1.0),
    )
    assert report.status == "FAIL"
    statuses = {item["check"]: item["status"] for item in report.checks}
    assert statuses["DURATION"] == "FAIL"
    assert statuses["INTEGRATED_LOUDNESS"] == "FAIL"
    assert statuses["TRUE_PEAK"] == "FAIL"
