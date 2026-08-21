from pathlib import Path
from types import SimpleNamespace

from ai_video_production.dbd_hud_calibration import FFmpegFrameInspector


def test_preview_uses_cached_probe_and_timestamp_seek(monkeypatch, tmp_path):
    source = tmp_path / "match.mp4"
    source.write_bytes(b"video-placeholder")
    calls = []

    def fake_run(cmd, **_kwargs):
        calls.append(list(cmd))
        if "ffprobe" in Path(cmd[0]).name.lower():
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    b'{"streams":[{"width":1920,"height":1080,'
                    b'"avg_frame_rate":"30000/1001","r_frame_rate":"30000/1001"}]}'
                ),
                stderr=b"",
            )
        target = Path(cmd[-1])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"P5\n64 64\n255\n" + bytes(4096))
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr("ai_video_production.dbd_hud_calibration.subprocess.run", fake_run)
    inspector = FFmpegFrameInspector()

    inspector.extract_preview_pgm(
        source_path=source,
        frame_index=300,
        output_path=tmp_path / "a.pgm",
    )
    inspector.extract_preview_pgm(
        source_path=source,
        frame_index=600,
        output_path=tmp_path / "b.pgm",
    )

    ffprobe_calls = [cmd for cmd in calls if "ffprobe" in Path(cmd[0]).name.lower()]
    ffmpeg_calls = [cmd for cmd in calls if "ffmpeg" in Path(cmd[0]).name.lower()]
    assert len(ffprobe_calls) == 1
    assert len(ffmpeg_calls) == 2
    assert all("-ss" in cmd for cmd in ffmpeg_calls)
    assert all(not any("select=eq" in part for part in cmd) for cmd in ffmpeg_calls)


def test_calibration_transport_preview_is_shared_persistent_background_and_coalesced():
    studio = Path("src/ai_video_production/dbd_training_studio.py").read_text(encoding="utf-8")
    shared = Path("src/ai_video_production/dbd_training_video_player.py").read_text(encoding="utf-8")
    worker = Path("src/ai_video_production/dbd_persistent_video_preview.py").read_text(encoding="utf-8")
    assert 'calibration_video_session = TkTrainingMediaSession(' in studio
    assert 'TkTrainingMediaPlayer(' in studio
    assert 'PersistentPreviewWorker' in shared
    assert 'self._pending = request' in worker
    assert 'if not stale:' in worker
    assert 'and not newer' not in worker
    assert 'PyAVPersistentFrameDecoder' in worker
