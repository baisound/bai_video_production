from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import wave

import pytest

from ai_video_production.assets import RightsStatus
from ai_video_production.subtitles import TranscriptManifest, TranscriptSegment
from ai_video_production.task036_product_ports import (
    FixedAnalysisAudioBinding,
    Task036AssetIngestPort,
    Task036CutCandidatePort,
    Task036LocalTranscriptionPort,
)


class IngestService:
    def __init__(self):
        self.requests = []

    def ingest(self, request):
        self.requests.append(request)
        asset = SimpleNamespace(
            asset_id="ASSET-00000000000000000000000000",
            checksum="sha256:" + "a" * 64,
        )
        return SimpleNamespace(asset=asset)


class LocalProvider:
    config = SimpleNamespace(allow_model_download=False)

    def transcribe(self, request):
        return TranscriptManifest(
            request.source_asset_id,
            request.language or "ja",
            "faster-whisper",
            "cached-local-model",
            (TranscriptSegment("seg-000001", 0, 500_000, "hello"),),
        )


class NoSilenceDetector:
    def detect(self, source, *, duration_us, config):
        return ()


def write_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(48_000)
        handle.writeframes(b"\x00\x00" * 48_000)


def test_task003_ingest_port_uses_fixed_rights_and_content_idempotency(tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    service = IngestService()
    port = Task036AssetIngestPort(
        service,
        "JOB-00000000000000000000000000",
        "owner",
        rights_status=RightsStatus.OWNED,
    )
    identity = port.ingest_local_media(source)
    request = service.requests[0]
    assert identity.asset_sha256 == "sha256:" + "a" * 64
    assert request.source_path == source.resolve()
    assert request.rights_status is RightsStatus.OWNED
    assert request.idempotency_key.startswith("task036-media-")
    assert str(source) not in request.idempotency_key


def test_task006_and_task024_ports_publish_to_trusted_directories(tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    transcript_port = Task036LocalTranscriptionPort(
        LocalProvider(),
        tmp_path / "transcription",
        language="ja",
    )
    transcript = transcript_port.transcribe_local_media(
        source_path=source,
        source_asset_id="ASSET-00000000000000000000000000",
    )
    assert (tmp_path / "transcription" / "transcript.json").is_file()
    assert (tmp_path / "transcription" / "transcription-report.json").is_file()

    analysis = tmp_path / "analysis.wav"
    write_wav(analysis)
    cut_port = Task036CutCandidatePort(
        FixedAnalysisAudioBinding(source, analysis),
        tmp_path / "cut-candidates",
        detector=NoSilenceDetector(),
    )
    manifest = cut_port.generate_cut_candidates(source_path=source, transcript=transcript)
    assert manifest.source_asset_id == transcript.source_asset_id
    assert (tmp_path / "cut-candidates" / "cut-candidates.json").is_file()
    assert (tmp_path / "cut-candidates" / "cut-candidate-report.json").is_file()


def test_fixed_analysis_audio_binding_rejects_a_different_source(tmp_path: Path):
    source = tmp_path / "source.mp4"
    other = tmp_path / "other.mp4"
    analysis = tmp_path / "analysis.wav"
    source.write_bytes(b"source")
    other.write_bytes(b"other")
    write_wav(analysis)
    binding = FixedAnalysisAudioBinding(source, analysis)
    with pytest.raises(ValueError, match="does not match"):
        binding.analysis_audio_for(other)
