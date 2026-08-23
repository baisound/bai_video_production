from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace
import wave

import pytest

from ai_video_production.assets import RightsStatus
from ai_video_production.faster_whisper_asr import FasterWhisperConfig
from ai_video_production.profile import ProfileSnapshot
from ai_video_production.store import SQLiteProductStore
from ai_video_production.subtitles import TranscriptManifest, TranscriptSegment
from ai_video_production.task036_product_ports import (
    FixedAnalysisAudioBinding,
    Task036AssetIngestPort,
    Task036CutCandidatePort,
    Task036LocalTranscriptionPort,
)


class IngestService:
    def __init__(self, canonical_source: Path):
        self.requests = []
        self.resolver = SimpleNamespace(resolve=lambda logical_uri: canonical_source)

    def ingest(self, request):
        self.requests.append(request)
        asset = SimpleNamespace(
            asset_id="ASSET-00000000000000000000000000",
            checksum="sha256:" + "a" * 64,
            logical_uri="asset://managed/source.mp4",
        )
        return SimpleNamespace(asset=asset)


class LocalProvider:
    provider_id = "faster-whisper"
    model_id = "cached-local-model"
    config = FasterWhisperConfig(model="cached-local-model", allow_model_download=False)

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
    managed = tmp_path / "managed.mp4"
    managed.write_bytes(b"managed media")
    service = IngestService(managed)
    port = Task036AssetIngestPort(
        service,
        "JOB-00000000000000000000000000",
        "owner",
        rights_status=RightsStatus.OWNED,
    )
    identity = port.ingest_local_media(source)
    request = service.requests[0]
    assert identity.asset_sha256 == "sha256:" + "a" * 64
    assert identity.canonical_source_path == managed
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
        SQLiteProductStore(tmp_path / "product.sqlite3"),
        "JOB-00000000000000000000000000",
        language="ja",
    )
    transcript_port.output_directory.mkdir()
    transcript_port.store.create_job(
        ProfileSnapshot.create("task036-test", "1.0.0", {}).profile_snapshot_id,
        job_id=transcript_port.production_job_id,
    )
    source_sha = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    outcome = transcript_port.transcribe_local_media(
        project_id="project-1",
        source_path=source,
        source_asset_id="ASSET-00000000000000000000000000",
        source_asset_sha256=source_sha,
    )
    transcript = outcome.transcript
    publication = tmp_path / "transcription"
    assert (publication / "transcript.json").is_file()
    assert (publication / "transcription-report.json").is_file()

    analysis = tmp_path / "analysis.wav"
    write_wav(analysis)
    cut_port = Task036CutCandidatePort(
        FixedAnalysisAudioBinding(
            "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest(), analysis,
        ),
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
    binding = FixedAnalysisAudioBinding(
        "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest(), analysis,
    )
    with pytest.raises(ValueError, match="does not match"):
        binding.analysis_audio_for(other)
