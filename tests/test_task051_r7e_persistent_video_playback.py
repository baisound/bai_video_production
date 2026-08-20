from __future__ import annotations

import sys
import threading
import time
from types import SimpleNamespace

from ai_video_production.dbd_persistent_video_preview import (
    PersistentPreviewFrame,
    PersistentPreviewWorker,
    PreviewGeometry,
    PyAVPersistentFrameDecoder,
)
from ai_video_production.dbd_video_transport import (
    VideoTransportMetadata,
    VideoTransportState,
    playback_frame_for_elapsed,
)


def metadata(fps: int = 30, frames: int = 300) -> VideoTransportMetadata:
    return VideoTransportMetadata(fps, 1, frames / fps, frames)


def test_playback_clock_is_wall_time_based_and_clamped():
    meta = metadata()
    assert playback_frame_for_elapsed(
        meta,
        anchor_frame=10,
        state=VideoTransportState.PLAYING,
        elapsed_seconds=1.0,
    ) == 40
    assert playback_frame_for_elapsed(
        meta,
        anchor_frame=10,
        state=VideoTransportState.FAST_FORWARDING,
        elapsed_seconds=1.0,
    ) == 130
    assert playback_frame_for_elapsed(
        meta,
        anchor_frame=40,
        state=VideoTransportState.REWINDING,
        elapsed_seconds=2.0,
    ) == 0
    assert playback_frame_for_elapsed(
        meta,
        anchor_frame=290,
        state=VideoTransportState.PLAYING,
        elapsed_seconds=2.0,
    ) == 299


def test_preview_frame_builds_in_memory_binary_pgm():
    frame = PersistentPreviewFrame(
        source="match.mp4",
        frame_index=7,
        source_geometry=PreviewGeometry(1920, 1080),
        preview_geometry=PreviewGeometry(64, 64),
        pixels=bytes([123]) * 4096,
    )
    raw = frame.pgm_bytes()
    assert raw.startswith(b"P5\n64 64\n255\n")
    assert raw.endswith(bytes([123]) * 4096)
    assert frame.tk_photo_data()


def test_worker_delivers_completed_progress_while_coalescing_pending_requests():
    first_started = threading.Event()
    release_first = threading.Event()
    delivered = []
    done = threading.Event()

    class FakeDecoder:
        def __init__(self, source, _metadata):
            self.source = source
            self.closed = False

        def get_frame(self, frame_index):
            if frame_index == 1:
                first_started.set()
                assert release_first.wait(2)
            return SimpleNamespace(source=self.source, frame_index=frame_index)

        def close(self):
            self.closed = True

    worker = PersistentPreviewWorker(
        decoder_factory=lambda source, meta: FakeDecoder(source, meta)
    )
    try:
        worker.request(
            source="match.mp4",
            frame_index=1,
            metadata=metadata(),
            callback=lambda frame, error: delivered.append((frame, error)),
        )
        assert first_started.wait(2)
        worker.request(
            source="match.mp4",
            frame_index=2,
            metadata=metadata(),
            callback=lambda frame, error: (
                delivered.append((frame, error)),
                done.set(),
            ),
        )
        release_first.set()
        assert done.wait(2)
        assert [item[0].frame_index for item in delivered] == [1, 2]
        assert all(item[1] is None for item in delivered)
    finally:
        worker.close()


def test_worker_invalidates_old_source_generation():
    blocked = threading.Event()
    release = threading.Event()
    delivered = []
    done = threading.Event()

    class FakeDecoder:
        def __init__(self, source, _metadata):
            self.source = source

        def get_frame(self, frame_index):
            if self.source.endswith("a.mp4"):
                blocked.set()
                assert release.wait(2)
            return SimpleNamespace(source=self.source, frame_index=frame_index)

        def close(self):
            pass

    worker = PersistentPreviewWorker(
        decoder_factory=lambda source, meta: FakeDecoder(source, meta)
    )
    try:
        worker.request(
            source="a.mp4",
            frame_index=10,
            metadata=metadata(),
            callback=lambda frame, error: delivered.append((frame, error)),
        )
        assert blocked.wait(2)
        worker.request(
            source="b.mp4",
            frame_index=20,
            metadata=metadata(),
            callback=lambda frame, error: (
                delivered.append((frame, error)),
                done.set(),
            ),
        )
        release.set()
        assert done.wait(2)
        assert len(delivered) == 1
        assert delivered[0][0].source.endswith("b.mp4")
        assert delivered[0][0].frame_index == 20
    finally:
        worker.close()


def test_pyav_decoder_keeps_container_open_seeks_and_uses_recent_ring(monkeypatch, tmp_path):
    source = tmp_path / "match.mp4"
    source.write_bytes(b"placeholder")
    open_count = 0
    reformat_count = 0

    class FakePlane:
        def __init__(self, width, height, value):
            self.line_size = width + 4
            rows = []
            for _ in range(height):
                rows.append(bytes([value]) * width + b"PAD!")
            self.raw = b"".join(rows)

        def __bytes__(self):
            return self.raw

    class FakeFrame:
        def __init__(self, index, width=1920, height=1080):
            self.index = index
            self.time = index / 30
            self.pts = index
            self._width = width
            self._height = height
            self.planes = []

        def reformat(self, *, width, height, format):
            nonlocal reformat_count
            reformat_count += 1
            assert format == "gray"
            converted = SimpleNamespace()
            converted.planes = [FakePlane(width, height, self.index % 251)]
            return converted

    class FakeStream:
        def __init__(self):
            self.codec_context = SimpleNamespace(width=1920, height=1080)
            self.time_base = 1 / 30
            self.start_time = 0
            self.thread_type = None

    class FakeStreams:
        def __init__(self, stream):
            self.video = [stream]

    class FakeContainer:
        def __init__(self):
            self.stream = FakeStream()
            self.streams = FakeStreams(self.stream)
            self.position = 0
            self.closed = False
            self.seek_calls = []

        def decode(self, _stream):
            start = self.position
            for index in range(start, 120):
                self.position = index + 1
                yield FakeFrame(index)

        def seek(self, timestamp, *, stream, backward, any_frame):
            assert stream is self.stream and backward and not any_frame
            self.seek_calls.append(timestamp)
            self.position = max(0, int(timestamp) - 2)

        def close(self):
            self.closed = True

    container = FakeContainer()

    def fake_open(path):
        nonlocal open_count
        assert str(path) == str(source)
        open_count += 1
        return container

    monkeypatch.setitem(sys.modules, "av", SimpleNamespace(open=fake_open))
    decoder = PyAVPersistentFrameDecoder(source, metadata(frames=120), ring_size=12)
    try:
        f10 = decoder.get_frame(10)
        assert f10.frame_index == 10
        assert len(f10.pixels) == f10.preview_geometry.width * f10.preview_geometry.height
        # The previous frame was cached while walking to target 10, so back-step
        # does not reopen or seek the source.
        seek_count = len(container.seek_calls)
        f9 = decoder.get_frame(9)
        assert f9.frame_index == 9
        assert len(container.seek_calls) == seek_count
        before_jump_conversions = reformat_count
        f80 = decoder.get_frame(80)
        assert f80.frame_index == 80
        assert len(container.seek_calls) > seek_count
        # Catch-up conversion is bounded to the immediate predecessor + target,
        # rather than reformating every skipped frame.
        assert reformat_count <= before_jump_conversions + 2
        assert open_count == 1
    finally:
        decoder.close()
    assert container.closed
