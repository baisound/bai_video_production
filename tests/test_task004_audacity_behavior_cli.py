from pathlib import Path
import wave

from ai_video_production.audacity_openvino_behavior_cli import _write_probe_wav


def test_synthetic_behavior_probe_sources_are_stereo_48k_and_deterministic(tmp_path):
    a = tmp_path / "a.wav"
    b = tmp_path / "b.wav"
    _write_probe_wav(a, kind="noise", seconds=0.05)
    _write_probe_wav(b, kind="noise", seconds=0.05)
    assert a.read_bytes() == b.read_bytes()
    with wave.open(str(a), "rb") as wav:
        assert wav.getnchannels() == 2
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 48000
        assert wav.getnframes() == 2400


def test_synthetic_music_probe_differs_from_noise_probe(tmp_path):
    noise = tmp_path / "noise.wav"
    music = tmp_path / "music.wav"
    _write_probe_wav(noise, kind="noise", seconds=0.05)
    _write_probe_wav(music, kind="music", seconds=0.05)
    assert noise.read_bytes() != music.read_bytes()


def test_behavior_cli_returns_failure_exit_when_structured_probe_report_is_not_ok(tmp_path, monkeypatch, capsys):
    import json
    import ai_video_production.audacity_openvino_behavior_cli as cli
    monkeypatch.setattr(cli, "_run", lambda evidence_root, timeout_seconds: {
        "ok": False,
        "noise_suppression": {"status": "PASS"},
        "music_separation_2_stem": {"status": "FAIL"},
    })
    rc = cli.main(["--evidence-root", str(tmp_path), "--timeout-seconds", "30"])
    assert rc == 2
    report = json.loads((tmp_path / "audacity-openvino-behavior.json").read_text(encoding="utf-8"))
    assert report["ok"] is False
