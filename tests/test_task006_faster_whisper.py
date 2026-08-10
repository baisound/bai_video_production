from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
import json
from pathlib import Path

import pytest

from ai_video_production import (
    FasterWhisperConfig, FasterWhisperProvider, LocalTranscriptionService,
)
from ai_video_production.errors import ProductError
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.subtitles import AsrRequest
from ai_video_production.transcription_cli import main
from ai_video_production.schema_contracts import validate_instance


@dataclass
class RawSegment:
    start: float
    end: float
    text: str


class FakeInfo:
    language = "ja"


class FakeModel:
    def __init__(self, model: str, **kwargs) -> None:
        self.model = model
        self.kwargs = kwargs

    def transcribe(self, path: str, **kwargs):
        return iter([
            RawSegment(0.1, 1.25, " こんにちは "),
            RawSegment(1.2, 2.0, "次の字幕です"),
            RawSegment(2.0, 2.1, "   "),
        ]), FakeInfo()


def test_provider_is_local_only_by_default_and_normalizes_segments(tmp_path: Path) -> None:
    media = tmp_path / "sample.wav"
    media.write_bytes(b"fixture")
    captured = {}

    def factory(model: str, **kwargs):
        captured.update({"model": model, **kwargs})
        return FakeModel(model, **kwargs)

    provider = FasterWhisperProvider(FasterWhisperConfig(), model_factory=factory)
    transcript = provider.transcribe(AsrRequest(generate_id(IdKind.ASSET), str(media)))
    assert captured["local_files_only"] is True
    assert transcript.language == "ja"
    assert [(s.start_us, s.end_us, s.text) for s in transcript.segments] == [
        (100_000, 1_250_000, "こんにちは"),
        (1_250_000, 2_000_000, "次の字幕です"),
    ]


def test_explicit_download_authorization_and_cache_are_forwarded(tmp_path: Path) -> None:
    media = tmp_path / "sample.mp4"
    media.write_bytes(b"fixture")
    seen = {}

    def factory(model: str, **kwargs):
        seen.update(kwargs)
        return FakeModel(model, **kwargs)

    config = FasterWhisperConfig(allow_model_download=True, cache_directory=str(tmp_path / "cache"))
    FasterWhisperProvider(config, model_factory=factory).transcribe(
        AsrRequest(generate_id(IdKind.ASSET), str(media), "ja")
    )
    assert seen["local_files_only"] is False
    assert seen["download_root"] == str((tmp_path / "cache").resolve())


def test_publication_writes_private_transcript_srt_and_text_free_report(tmp_path: Path) -> None:
    media = tmp_path / "sample.wav"
    media.write_bytes(b"fixture")
    provider = FasterWhisperProvider(FasterWhisperConfig(), model_factory=FakeModel)
    result = LocalTranscriptionService.run(media, tmp_path / "out", provider=provider)
    transcript = json.loads(result.transcript_path.read_text(encoding="utf-8"))
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert transcript["segments"][0]["text"] == "こんにちは"
    assert "こんにちは" in result.subtitle_path.read_text(encoding="utf-8")
    assert "こんにちは" not in result.report_path.read_text(encoding="utf-8")
    assert report["network_used_for_inference"] is False
    assert report["model_download_authorized"] is False
    assert report["segment_count"] == 2
    canonical = Path(__file__).parents[1] / "schemas" / "transcription-report.schema.json"
    validate_instance(report, canonical)
    packaged = resources.files("ai_video_production").joinpath("schema_resources", canonical.name)
    assert json.loads(canonical.read_text(encoding="utf-8")) == json.loads(packaged.read_text(encoding="utf-8"))


def test_missing_media_and_missing_optional_dependency_are_normalized(tmp_path: Path, monkeypatch) -> None:
    provider = FasterWhisperProvider(FasterWhisperConfig())
    with pytest.raises(ProductError) as missing:
        provider.transcribe(AsrRequest(generate_id(IdKind.ASSET), str(tmp_path / "missing.wav")))
    assert missing.value.code == "ERR_ASR_MEDIA_NOT_FOUND"

    media = tmp_path / "sample.wav"
    media.write_bytes(b"fixture")
    monkeypatch.setattr("ai_video_production.faster_whisper_asr.importlib.import_module", lambda _name: (_ for _ in ()).throw(ImportError()))
    with pytest.raises(ProductError) as dependency:
        provider.transcribe(AsrRequest(generate_id(IdKind.ASSET), str(media)))
    assert dependency.value.code == "ERR_FASTER_WHISPER_NOT_INSTALLED"


def test_cli_fails_without_writing_outputs_for_missing_media(tmp_path: Path, capsys) -> None:
    output = tmp_path / "out"
    assert main([str(tmp_path / "missing.wav"), "--output-dir", str(output)]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "ERR_ASR_MEDIA_NOT_FOUND"
    assert not output.exists()


def test_config_rejects_unbounded_or_unsafe_values() -> None:
    with pytest.raises(ValueError, match="beam_size"):
        FasterWhisperConfig(beam_size=0)
    with pytest.raises(ValueError, match="device"):
        FasterWhisperConfig(device="remote")


def test_local_model_path_is_not_disclosed_as_manifest_model_id(tmp_path: Path) -> None:
    provider = FasterWhisperProvider(FasterWhisperConfig(model=str(tmp_path / "private-model")), model_factory=FakeModel)
    assert provider.model_id.startswith("local-model-")
    assert str(tmp_path) not in provider.model_id
