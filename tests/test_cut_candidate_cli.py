from __future__ import annotations

import json
from pathlib import Path
import wave

from ai_video_production import cut_candidate_cli
from ai_video_production.cut_candidates import SilenceRange


ASSET_ID = "ASSET-00000000000000000000000000"


def write_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(16000)
        out.writeframes(b"\x01\x00" * 32000)


class FakeDetector:
    def __init__(self, executable="ffmpeg"):
        self.executable = executable

    def detect(self, source, *, duration_us, config):
        return (SilenceRange(500_000, 1_500_000),)


def test_cli_publishes_review_only_manifest(tmp_path, monkeypatch, capsys):
    audio = tmp_path / "a.wav"
    write_wav(audio)
    monkeypatch.setattr(cut_candidate_cli, "FfmpegSilenceDetector", FakeDetector)
    rc = cut_candidate_cli.main([
        str(audio),
        "--output-dir", str(tmp_path / "out"),
        "--source-asset-id", ASSET_ID,
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["auto_apply_authorized"] is False
    assert (tmp_path / "out" / "cut-candidates.json").exists()


def test_cli_invalid_input_is_structured_error(tmp_path, capsys):
    rc = cut_candidate_cli.main([
        str(tmp_path / "missing.wav"),
        "--output-dir", str(tmp_path / "out"),
        "--source-asset-id", "bad",
    ])
    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "ERR_CUT_INPUT"
