from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ai_video_production.faster_whisper_asr import FasterWhisperConfig, FasterWhisperProvider
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.subtitles import AsrRequest


class FakeModel:
    def __init__(self) -> None:
        self.calls = 0

    def transcribe(self, path, **kwargs):
        self.calls += 1
        return (), SimpleNamespace(language="ja")


def test_faster_whisper_model_is_reused_across_chunk_calls(tmp_path: Path) -> None:
    media_a = tmp_path / "a.wav"
    media_b = tmp_path / "b.wav"
    media_a.write_bytes(b"a")
    media_b.write_bytes(b"b")
    model = FakeModel()
    factory_calls: list[tuple] = []

    def factory(*args, **kwargs):
        factory_calls.append((args, kwargs))
        return model

    provider = FasterWhisperProvider(
        FasterWhisperConfig(model="small"),
        model_factory=factory,
    )
    asset_id = generate_id(IdKind.ASSET)
    provider.transcribe(AsrRequest(asset_id, str(media_a), "ja"))
    provider.transcribe(AsrRequest(asset_id, str(media_b), "ja"))

    assert len(factory_calls) == 1
    assert model.calls == 2
