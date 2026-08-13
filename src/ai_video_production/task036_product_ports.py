"""Product-service ports for the trusted TASK-036 pre-edit runtime."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Protocol

from .assets import AssetType, AudioRightsStatus, PermissionState, RetentionClass, RightsStatus
from .cut_candidates import (
    CutCandidateAnalyzer,
    CutCandidateConfig,
    CutCandidateManifest,
    CutCandidatePublicationService,
    FfmpegSilenceDetector,
)
from .desktop_media_workflow import IngestedMediaIdentity
from .faster_whisper_asr import FasterWhisperProvider, LocalTranscriptionService
from .ingest import AssetIngestRequest, AssetIngestService
from .subtitles import TranscriptManifest
from .timebase import FrameRate


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(slots=True)
class Task036AssetIngestPort:
    """Reuse TASK-003 ingest with trusted rights and Project bindings."""

    service: AssetIngestService
    production_job_id: str
    owner: str
    asset_type: AssetType = AssetType.VIDEO
    rights_status: RightsStatus = RightsStatus.OWNED
    retention_class: RetentionClass = RetentionClass.STANDARD
    commercial_use: PermissionState = PermissionState.UNKNOWN
    derivative_allowed: PermissionState = PermissionState.UNKNOWN
    reuse_allowed: PermissionState = PermissionState.ALLOWED
    audio_rights_status: AudioRightsStatus = AudioRightsStatus.NOT_APPLICABLE

    def ingest_local_media(self, source_path: Path) -> IngestedMediaIdentity:
        source = source_path.resolve()
        checksum = _file_sha256(source)
        result = self.service.ingest(
            AssetIngestRequest(
                production_job_id=self.production_job_id,
                source_path=source,
                asset_type=self.asset_type,
                rights_status=self.rights_status,
                owner=self.owner,
                idempotency_key=f"task036-media-{checksum}",
                retention_class=self.retention_class,
                commercial_use=self.commercial_use,
                derivative_allowed=self.derivative_allowed,
                reuse_allowed=self.reuse_allowed,
                audio_rights_status=self.audio_rights_status,
            )
        )
        return IngestedMediaIdentity(result.asset.asset_id, result.asset.checksum)


@dataclass(slots=True)
class Task036LocalTranscriptionPort:
    """Reuse TASK-006 FasterWhisper publication with fixed local settings."""

    provider: FasterWhisperProvider
    output_directory: Path
    language: str | None = None
    timeline_rate: FrameRate = FrameRate(30000, 1001)

    def transcribe_local_media(self, *, source_path: Path, source_asset_id: str) -> TranscriptManifest:
        publication = LocalTranscriptionService.run(
            source_path,
            self.output_directory,
            provider=self.provider,
            source_asset_id=source_asset_id,
            language=self.language,
            timeline_rate=self.timeline_rate,
        )
        return publication.transcript


class AnalysisAudioBinding(Protocol):
    def analysis_audio_for(self, source_path: Path) -> Path: ...


@dataclass(frozen=True, slots=True)
class FixedAnalysisAudioBinding:
    """Bind one normalized analysis WAV to one exact selected source."""

    source_path: Path
    analysis_audio_path: Path

    def analysis_audio_for(self, source_path: Path) -> Path:
        if source_path.resolve() != self.source_path.resolve():
            raise ValueError("analysis audio binding does not match the selected source")
        return self.analysis_audio_path.resolve()


@dataclass(slots=True)
class Task036CutCandidatePort:
    """Reuse TASK-024 with a trusted normalized-audio binding."""

    analysis_audio: AnalysisAudioBinding
    output_directory: Path
    config: CutCandidateConfig = CutCandidateConfig()
    detector: FfmpegSilenceDetector | None = None

    def generate_cut_candidates(
        self,
        *,
        source_path: Path,
        transcript: TranscriptManifest,
    ) -> CutCandidateManifest:
        manifest = CutCandidateAnalyzer.analyze(
            self.analysis_audio.analysis_audio_for(source_path),
            source_asset_id=transcript.source_asset_id,
            transcript=transcript,
            config=self.config,
            detector=self.detector,
        )
        CutCandidatePublicationService.publish(manifest, self.output_directory)
        return manifest
