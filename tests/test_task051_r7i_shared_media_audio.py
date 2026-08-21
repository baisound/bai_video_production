from pathlib import Path, PureWindowsPath

from ai_video_production.dbd_training_audio import FfplayAudioController
from ai_video_production.dbd_training_video_player import TkTrainingMediaSession
from ai_video_production.dbd_video_transport import (
    BUTTON_LAYOUT,
    VideoTransportEvent,
    VideoTransportState,
)


class FakeProcess:
    def __init__(self):
        self.returncode = None
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def kill(self):
        self.killed = True
        self.returncode = 0

    def wait(self, timeout=None):
        return self.returncode


class FakeDiagnostics:
    def __init__(self):
        self.events = []

    def emit(self, event, **fields):
        self.events.append((event, fields))

    def exception(self, event, exc, **fields):
        self.events.append((event, {**fields, "exception": type(exc).__name__}))


class FakeRoot:
    def bind(self, *_args, **_kwargs):
        return None


class FakeWorker:
    def invalidate(self):
        return None

    def close(self, *, join_timeout=1.0):
        return None


class FakeAudio:
    def __init__(self):
        self.available = True
        self.plays = []
        self.stops = 0
        self.closed = False
        self.volume = None
        self.muted = None

    def set_volume(self, value):
        self.volume = value

    def set_muted(self, value):
        self.muted = value

    def play(self, source, *, start_seconds=0.0):
        self.plays.append((source, start_seconds))
        return True

    def restart(self, source, *, start_seconds):
        self.plays.append((source, start_seconds))
        return True

    def stop(self):
        self.stops += 1

    def close(self):
        self.closed = True


def test_ffplay_controller_starts_source_audio_at_transport_position(monkeypatch, tmp_path):
    source = tmp_path / "match.mp4"
    source.write_bytes(b"placeholder")
    diagnostics = FakeDiagnostics()
    calls = []
    process = FakeProcess()

    monkeypatch.setattr(
        "ai_video_production.dbd_training_audio.shutil.which",
        lambda value: r"C:\\ffmpeg\\ffplay.exe" if value == "ffplay" else None,
    )

    controller = FfplayAudioController(
        diagnostics=diagnostics,
        popen_factory=lambda cmd, **kwargs: calls.append((cmd, kwargs)) or process,
    )
    controller.set_volume(73)
    assert controller.play(str(source), start_seconds=12.5) is True

    cmd, kwargs = calls[-1]
    assert PureWindowsPath(cmd[0]).name.lower() == "ffplay.exe"
    assert "-nodisp" in cmd and "-autoexit" in cmd
    assert cmd[cmd.index("-ss") + 1] == "12.500000"
    assert cmd[cmd.index("-volume") + 1] == "73"
    assert cmd[-1] == str(source)
    assert "stdin" in kwargs and "stdout" in kwargs and "stderr" in kwargs

    controller.stop()
    assert process.terminated is True
    assert any(event == "AUDIO_OUTPUT_STARTED" for event, _ in diagnostics.events)
    assert any(event == "AUDIO_OUTPUT_STOPPED" for event, _ in diagnostics.events)


def test_shared_media_session_plays_audio_only_during_normal_playback(tmp_path):
    source = tmp_path / "match.mp4"
    source.write_bytes(b"placeholder")
    audio = FakeAudio()
    session = TkTrainingMediaSession(
        root=FakeRoot(),
        source_getter=lambda: str(source),
        frame_getter=lambda: 0,
        frame_setter=lambda _value: None,
        on_frame=lambda _frame: None,
        worker=FakeWorker(),
        audio_controller=audio,
        diagnostics=FakeDiagnostics(),
    )

    session._on_transport_state(
        VideoTransportEvent("play", VideoTransportState.PLAYING, 30, 1.0, str(source))
    )
    assert audio.plays[-1] == (str(source), 1.0)

    for state, action in (
        (VideoTransportState.STOPPED, "stop"),
        (VideoTransportState.REWINDING, "rewind"),
        (VideoTransportState.FAST_FORWARDING, "fast_forward"),
    ):
        before = audio.stops
        session._on_transport_state(VideoTransportEvent(action, state, 30, 1.0, str(source)))
        assert audio.stops == before + 1

    session.close()
    assert audio.closed is True


def test_shared_media_transport_keeps_all_twelve_required_controls():
    labels = tuple(label for _key, label in BUTTON_LAYOUT)
    assert labels == (
        "最初へ", "巻き戻し", "停止", "再生", "早送り", "最後へ",
        "-10秒", "-1秒", "-1フレーム", "+1フレーム", "+1秒", "+10秒",
    )
