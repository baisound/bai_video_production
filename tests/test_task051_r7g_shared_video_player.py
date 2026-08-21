from pathlib import Path

from ai_video_production.dbd_persistent_video_preview import (
    PersistentPreviewFrame,
    PreviewGeometry,
)
from ai_video_production.dbd_training_video_player import TkTrainingMediaSession
from ai_video_production.dbd_video_transport import VideoTransportMetadata


class FakeRoot:
    def __init__(self):
        self.bound = []

    def after(self, _delay, callback):
        callback()
        return "after-id"

    def bind(self, event, callback, add=None):
        self.bound.append((event, callback, add))


class FakeWorker:
    def __init__(self):
        self.requests = []
        self.closed = False
        self.invalidated = False

    def request(self, **kwargs):
        self.requests.append(kwargs)
        return 0

    def invalidate(self):
        self.invalidated = True

    def close(self, *, join_timeout=1.0):
        self.closed = True


def metadata():
    return VideoTransportMetadata(30, 1, 10.0, 300)


def frame(source: str, index: int) -> PersistentPreviewFrame:
    geom = PreviewGeometry(2, 2)
    return PersistentPreviewFrame(source, index, geom, geom, b"\x00\x01\x02\x03")


def test_session_caches_metadata_and_delivers_latest_source_on_ui_thread():
    root = FakeRoot()
    worker = FakeWorker()
    source = {"value": "a.mp4"}
    current_frame = {"value": 0}
    delivered = []
    probes = []

    session = TkTrainingMediaSession(
        root=root,
        source_getter=lambda: source["value"],
        frame_getter=lambda: current_frame["value"],
        frame_setter=lambda value: current_frame.__setitem__("value", value),
        on_frame=delivered.append,
        worker=worker,
        metadata_getter=lambda value: probes.append(value) or metadata(),
    )

    session.request_frame(10)
    session.request_frame(11)
    assert probes == ["a.mp4"]
    assert len(worker.requests) == 2

    worker.requests[0]["callback"](frame("a.mp4", 10), None)
    assert delivered == []  # worker never paints Tk directly
    assert session._drain_mailbox_once() is True
    assert [item.frame_index for item in delivered] == [10]

    source["value"] = "b.mp4"
    # Completion from the previous source must not paint into the new tab state.
    worker.requests[1]["callback"](frame("a.mp4", 11), None)
    assert session._drain_mailbox_once() is True
    assert [item.frame_index for item in delivered] == [10]

    session.request_frame(20)
    assert probes == ["a.mp4", "b.mp4"]
    worker.requests[2]["callback"](frame("b.mp4", 20), None)
    assert session._drain_mailbox_once() is True
    assert [item.frame_index for item in delivered] == [10, 20]

    session.close()
    assert worker.closed is True


def test_training_studio_routes_all_video_surfaces_through_shared_player_contract():
    root = Path(__file__).resolve().parents[1]
    studio = (root / "src" / "ai_video_production" / "dbd_training_studio.py").read_text(encoding="utf-8")
    shared = (root / "src" / "ai_video_production" / "dbd_training_video_player.py").read_text(encoding="utf-8")

    assert "TkTrainingMediaPlayer" in studio
    assert "TkTrainingMediaSession" in studio  # HUD uses the shared media session directly for ROI overlays
    assert studio.count("TkTrainingMediaPlayer(") == 5
    assert studio.count("TkTrainingMediaSession(") == 1

    for old_name in (
        "render_video_transport_frame",
        "render_visual_frame",
        "render_ocr_frame",
        "render_trivia_frame",
        "queue_calibration_transport_preview",
    ):
        assert old_name not in studio

    assert "PersistentPreviewWorker" in shared
    assert "TkVideoTransportBar" in shared
    assert "probe_video_metadata" in shared
    assert "preview playback never becomes training evidence" in studio
