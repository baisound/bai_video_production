from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.errors import ProductError, ProductErrorCategory
from ai_video_production.faster_whisper_asr import FasterWhisperConfig
from ai_video_production.large_media_transcription import (
    ChunkedTranscriptionConfig,
    ResumableTranscriptionService,
    TranscriptionChunk,
    build_chunk_plan,
)
from ai_video_production.media_probe import MediaProbeResult
from ai_video_production.subtitles import TranscriptManifest, TranscriptSegment


class FakeProbe:
    def __init__(self, duration_us: int) -> None:
        self.duration_us = duration_us

    def probe(self, path: str | Path) -> MediaProbeResult:
        return MediaProbeResult(
            format_name="fake",
            duration_us=self.duration_us,
            size_bytes=Path(path).stat().st_size,
            bit_rate=None,
            streams=({"codec_type": "audio", "duration_us": self.duration_us},),
        )


class FakeExtractor:
    def __init__(self) -> None:
        self.chunks: list[str] = []

    def extract(self, source: Path, chunk: TranscriptionChunk, target: Path) -> None:
        self.chunks.append(chunk.chunk_id)
        target.write_bytes(b"fake wav")


class FakeProvider:
    provider_id = "fake-asr"
    model_id = "fake-model"

    def __init__(self, *, fail_on_call: int | None = None) -> None:
        self.config = FasterWhisperConfig(model="small", allow_model_download=False)
        self.fail_on_call = fail_on_call
        self.calls = 0

    def transcribe(self, request):
        self.calls += 1
        if self.fail_on_call == self.calls:
            raise ProductError(
                "ERR_FAKE_ASR_FAILURE",
                "synthetic interruption",
                ProductErrorCategory.TRANSIENT,
                retryable=True,
            )
        language = request.language or "ja"
        return TranscriptManifest(
            request.source_asset_id,
            language,
            self.provider_id,
            self.model_id,
            (TranscriptSegment("seg-000001", 2_500_000, 3_500_000, "private phrase"),),
        )


def config() -> ChunkedTranscriptionConfig:
    return ChunkedTranscriptionConfig(chunk_seconds=10, overlap_seconds=2)


def test_chunk_plan_is_deterministic_and_core_ranges_do_not_overlap() -> None:
    chunks, first_hash = build_chunk_plan(25_000_000, config())
    again, second_hash = build_chunk_plan(25_000_000, config())
    assert chunks == again
    assert first_hash == second_hash
    assert [(x.core_start_us, x.core_end_us) for x in chunks] == [
        (0, 10_000_000),
        (10_000_000, 20_000_000),
        (20_000_000, 25_000_000),
    ]
    assert chunks[1].extraction_start_us == 8_000_000
    assert chunks[1].extraction_end_us == 22_000_000


def test_chunked_run_publishes_private_outputs_and_removes_work_state(tmp_path: Path) -> None:
    media = tmp_path / "source.bin"
    media.write_bytes(b"media")
    output = tmp_path / "out"
    provider = FakeProvider()
    extractor = FakeExtractor()

    result = ResumableTranscriptionService.run(
        media, output, provider=provider, config=config(),
        probe=FakeProbe(25_000_000), extractor=extractor,
    )

    assert provider.calls == 3
    assert extractor.chunks == ["chunk-000001", "chunk-000002", "chunk-000003"]
    assert len(result.transcript.segments) == 3
    assert result.transcript_path.is_file()
    assert result.subtitle_path.is_file()
    assert not (output / ".bai-transcription-work").exists()
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report["execution_mode"] == "CHUNKED_RESUMABLE"
    assert report["chunk_count"] == 3
    assert report["resumed_chunk_count"] == 0
    assert "private phrase" not in result.report_path.read_text(encoding="utf-8")


def test_interrupted_run_requires_explicit_resume_and_reuses_verified_partial(tmp_path: Path) -> None:
    media = tmp_path / "source.bin"
    media.write_bytes(b"media")
    output = tmp_path / "out"

    with pytest.raises(ProductError, match="synthetic interruption"):
        ResumableTranscriptionService.run(
            media, output, provider=FakeProvider(fail_on_call=2), config=config(),
            probe=FakeProbe(25_000_000), extractor=FakeExtractor(),
        )

    checkpoint = output / ".bai-transcription-work" / "checkpoint.json"
    assert checkpoint.is_file()
    with pytest.raises(ProductError) as required:
        ResumableTranscriptionService.run(
            media, output, provider=FakeProvider(), config=config(),
            probe=FakeProbe(25_000_000), extractor=FakeExtractor(),
        )
    assert required.value.code == "ERR_ASR_RESUME_REQUIRED"

    resumed = FakeProvider()
    result = ResumableTranscriptionService.run(
        media, output, provider=resumed, config=config(),
        probe=FakeProbe(25_000_000), extractor=FakeExtractor(), resume=True,
    )
    assert resumed.calls == 2
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report["resumed_chunk_count"] == 1


def test_resume_rejects_changed_source_hash(tmp_path: Path) -> None:
    media = tmp_path / "source.bin"
    media.write_bytes(b"media")
    output = tmp_path / "out"

    with pytest.raises(ProductError):
        ResumableTranscriptionService.run(
            media, output, provider=FakeProvider(fail_on_call=2), config=config(),
            probe=FakeProbe(25_000_000), extractor=FakeExtractor(),
        )

    media.write_bytes(b"changed-media")
    with pytest.raises(ProductError) as mismatch:
        ResumableTranscriptionService.run(
            media, output, provider=FakeProvider(), config=config(),
            probe=FakeProbe(25_000_000), extractor=FakeExtractor(), resume=True,
        )
    assert mismatch.value.code == "ERR_INTEGRITY_CHECKPOINT_MISMATCH"
    assert "source_sha256" in mismatch.value.details["mismatch_fields"]


def test_checkpoint_is_text_free_but_private_partial_contains_transcript(tmp_path: Path) -> None:
    media = tmp_path / "source.bin"
    media.write_bytes(b"media")
    output = tmp_path / "out"

    with pytest.raises(ProductError):
        ResumableTranscriptionService.run(
            media, output, provider=FakeProvider(fail_on_call=2), config=config(),
            probe=FakeProbe(25_000_000), extractor=FakeExtractor(),
        )

    work = output / ".bai-transcription-work"
    checkpoint_text = (work / "checkpoint.json").read_text(encoding="utf-8")
    partial_text = (work / "partials" / "chunk-000001.json").read_text(encoding="utf-8")
    assert "private phrase" not in checkpoint_text
    assert '"contains_transcript_text":false' in checkpoint_text
    assert "private phrase" in partial_text


def test_restart_discards_unfinished_state_and_recomputes_all_chunks(tmp_path: Path) -> None:
    media = tmp_path / "source.bin"
    media.write_bytes(b"media")
    output = tmp_path / "out"

    with pytest.raises(ProductError):
        ResumableTranscriptionService.run(
            media, output, provider=FakeProvider(fail_on_call=2), config=config(),
            probe=FakeProbe(25_000_000), extractor=FakeExtractor(),
        )

    provider = FakeProvider()
    ResumableTranscriptionService.run(
        media, output, provider=provider, config=config(),
        probe=FakeProbe(25_000_000), extractor=FakeExtractor(), restart=True,
    )
    assert provider.calls == 3
