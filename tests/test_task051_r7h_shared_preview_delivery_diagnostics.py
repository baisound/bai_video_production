from __future__ import annotations

import json
from pathlib import Path
import threading
import time

import pytest

from ai_video_production.dbd_persistent_video_preview import PersistentPreviewFrame, PreviewGeometry
from ai_video_production.dbd_training_diagnostics import (
    DiagnosticLogger,
    LATEST_LOG_NAME,
    MARKER_NAME,
)
from ai_video_production.dbd_training_video_player import TkTrainingVideoSession
from ai_video_production.dbd_video_transport import VideoTransportMetadata


class FakeRoot:
    def __init__(self):
        self.bound = []
        self.after_calls = []
        self.cancelled = []

    def bind(self, event, callback, add=None):
        self.bound.append((event, callback, add))

    def after(self, delay, callback):
        self.after_calls.append((delay, callback, threading.get_ident()))
        return f"after-{len(self.after_calls)}"

    def after_cancel(self, value):
        self.cancelled.append(value)


class FakeWorker:
    def __init__(self):
        self.requests = []
        self.closed = False

    def request(self, **kwargs):
        self.requests.append(kwargs)
        return 0

    def invalidate(self):
        pass

    def close(self, *, join_timeout=1.0):
        self.closed = True


def metadata():
    return VideoTransportMetadata(30, 1, 10.0, 300)


def preview(source="clip.mp4", index=5):
    geom = PreviewGeometry(2, 2)
    return PersistentPreviewFrame(source, index, geom, geom, b"\x00\x40\x80\xff")


def _wait_for_diagnostic_events(
    latest: Path,
    expected_events: set[str],
    *,
    timeout: float = 5.0,
) -> list[dict]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            lines = latest.read_text(encoding="utf-8").splitlines()
            records = [json.loads(line) for line in lines]
        except (FileNotFoundError, json.JSONDecodeError):
            records = []
        if expected_events.issubset({row.get("event") for row in records}):
            return records
        time.sleep(0.01)
    pytest.fail(
        f"diagnostic events were not written within {timeout:.1f}s: {sorted(expected_events)}"
    )


def test_worker_callback_only_deposits_mailbox_until_ui_thread_drains(tmp_path):
    root = FakeRoot()
    worker = FakeWorker()
    delivered = []
    main_thread = threading.get_ident()
    session = TkTrainingVideoSession(
        root=root,
        source_getter=lambda: "clip.mp4",
        frame_getter=lambda: 5,
        frame_setter=lambda _value: None,
        on_frame=lambda frame: delivered.append((frame.frame_index, threading.get_ident())),
        worker=worker,
        metadata_getter=lambda _source: metadata(),
        diagnostics=DiagnosticLogger(application_dir=tmp_path),
        diagnostic_feature="TEST",
        player_id="mailbox-test",
    )

    session.request_frame(5)
    assert len(worker.requests) == 1

    callback = worker.requests[0]["callback"]
    thread = threading.Thread(target=lambda: callback(preview(), None), name="fake-decoder")
    thread.start(); thread.join()

    assert delivered == []
    assert root.after_calls == []  # fake/non-Tk root: worker never schedules Tk
    assert session._drain_mailbox_once() is True
    assert delivered == [(5, main_thread)]
    session.close()


def test_latest_frame_mailbox_replaces_older_completed_frame(tmp_path):
    root = FakeRoot(); worker = FakeWorker(); delivered = []
    session = TkTrainingVideoSession(
        root=root,
        source_getter=lambda: "clip.mp4",
        frame_getter=lambda: 0,
        frame_setter=lambda _value: None,
        on_frame=lambda frame: delivered.append(frame.frame_index),
        worker=worker,
        metadata_getter=lambda _source: metadata(),
        diagnostics=DiagnosticLogger(application_dir=tmp_path),
    )
    session.request_frame(1); session.request_frame(2)
    worker.requests[0]["callback"](preview(index=1), None)
    worker.requests[1]["callback"](preview(index=2), None)
    assert session._drain_mailbox_once() is True
    assert delivered == [2]
    session.close()


def test_diagnostics_marker_enables_async_jsonl_and_redacts_paths(tmp_path):
    (tmp_path / MARKER_NAME).write_text("", encoding="utf-8")
    logger = DiagnosticLogger(application_dir=tmp_path, queue_limit=32)
    assert logger.enabled is True
    logger.emit("FRAME_REQUESTED", source=tmp_path / "secret-folder" / "video.mp4", frame_index=9)
    logger.exception("SAMPLE_ERROR", ValueError("boom"), video_path=tmp_path / "private.mp4")
    logger.close(join_timeout=2.0)

    latest = tmp_path / "diagnostics" / LATEST_LOG_NAME
    records = _wait_for_diagnostic_events(
        latest, {"DIAGNOSTICS_ENABLED", "FRAME_REQUESTED", "SAMPLE_ERROR"}
    )
    events = {row["event"] for row in records}
    assert "DIAGNOSTICS_ENABLED" in events
    assert "FRAME_REQUESTED" in events
    assert "SAMPLE_ERROR" in events
    text = latest.read_text(encoding="utf-8")
    assert "secret-folder" not in text
    assert "video.mp4|sha256:" in text
    assert "private.mp4|sha256:" in text


def test_diagnostics_without_marker_creates_no_directory(tmp_path):
    logger = DiagnosticLogger(application_dir=tmp_path)
    assert logger.enabled is False
    logger.emit("IGNORED")
    logger.close()
    assert not (tmp_path / "diagnostics").exists()


def test_real_tk_photoimage_pgm_render_contract_when_display_available():
    import tkinter as tk

    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk display unavailable: {exc}")
    root.withdraw()
    try:
        pgm = b"P5\n2 2\n255\n" + bytes((0, 85, 170, 255))
        photo = tk.PhotoImage(data=pgm)
        label = tk.Label(root, image=photo)
        label.pack()
        root.update_idletasks()
        assert photo.width() == 2
        assert photo.height() == 2
    finally:
        root.destroy()


def test_r7h_contract_has_no_worker_to_tk_after_bridge():
    root = Path(__file__).resolve().parents[1]
    player = (root / "src/ai_video_production/dbd_training_video_player.py").read_text(encoding="utf-8")
    diagnostics = (root / "src/ai_video_production/dbd_training_diagnostics.py").read_text(encoding="utf-8")
    assert "_LatestFrameMailbox" in player
    assert "self._mailbox.put" in player
    assert "self._drain_mailbox_once()" in player
    assert "FRAME_MAILBOX_PUT" in player
    assert "TK_FRAME_PAINTED" in player
    assert "BAI_DIAGNOSTICS.ENABLE" in diagnostics
    assert "latest.jsonl" in diagnostics
