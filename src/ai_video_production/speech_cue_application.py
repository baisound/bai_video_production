"""Local consumer application service for word-timed speech cue generation.

This is a temporary creator-friendly bridge while Product Shell integration is
owned by TASK-036.  It reuses the canonical local FasterWhisper provider and
never creates a second ASR provider or Timeline authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .faster_whisper_asr import (
    FasterWhisperProvider,
    LocalTranscriptionService,
    TranscriptionPublication,
)
from .large_media_transcription import (
    AudioChunkExtractor,
    ChunkedTranscriptionConfig,
    MediaProbe,
    ResumableTranscriptionService,
)
from .semantic_audio_cues import (
    KeywordProfile,
    SpeechCueDetectionService,
    SpeechCuePublication,
    SpeechCuePublicationService,
)
from .subtitles import TranscriptManifest
from .timebase import FrameRate


@dataclass(frozen=True, slots=True)
class SpeechCueApplicationResult:
    transcript: TranscriptManifest
    cue_publication: SpeechCuePublication
    transcription_publication: TranscriptionPublication | None = None

    def public_status(self) -> dict[str, Any]:
        """Return bounded path/text-free status suitable for GUI/diagnostics."""
        counts = self.cue_publication.manifest.counts
        return {
            "status_version": "1.0.0",
            "ok": True,
            "source_asset_id": self.transcript.source_asset_id,
            "keyword_profile_id": self.cue_publication.manifest.keyword_profile_id,
            "confirmed_count": counts["confirmed"],
            "review_count": counts["review"],
            "rejected_count": counts["rejected"],
            "transcription_generated": self.transcription_publication is not None,
            "transcript_text_in_status": False,
            "host_path_in_status": False,
            "canonical_timeline": False,
            "auto_apply_authorized": False,
        }


class SpeechCueApplicationService:
    """Create semantic cue publications without taking Product/Timeline authority."""

    @staticmethod
    def detect_from_transcript(
        transcript: TranscriptManifest,
        *,
        source_frame_rate: FrameRate,
        keyword_profile: KeywordProfile,
        output_directory: str | Path,
        include_review_in_projection: bool = False,
    ) -> SpeechCueApplicationResult:
        manifest = SpeechCueDetectionService.detect(
            transcript,
            source_frame_rate=source_frame_rate,
            keyword_profile=keyword_profile,
        )
        cue_publication = SpeechCuePublicationService.publish(
            manifest,
            output_directory,
            include_review_in_projection=include_review_in_projection,
        )
        return SpeechCueApplicationResult(
            transcript=transcript,
            cue_publication=cue_publication,
        )

    @staticmethod
    def transcribe_and_detect(
        media_path: str | Path,
        *,
        source_asset_id: str,
        source_frame_rate: FrameRate,
        keyword_profile: KeywordProfile,
        output_directory: str | Path,
        provider: FasterWhisperProvider,
        language: str | None = None,
        include_review_in_projection: bool = False,
    ) -> SpeechCueApplicationResult:
        """Run the existing local ASR route with explicit word timing, then detect cues.

        The provider's existing `allow_model_download` setting remains the only
        model-download authority.  This method itself never enables downloads.
        """
        root = Path(output_directory).expanduser().resolve()
        transcription = LocalTranscriptionService.run(
            media_path,
            root / "transcription",
            provider=provider,
            source_asset_id=source_asset_id,
            language=language,
            timeline_rate=source_frame_rate,
            include_word_timestamps=True,
        )
        manifest = SpeechCueDetectionService.detect(
            transcription.transcript,
            source_frame_rate=source_frame_rate,
            keyword_profile=keyword_profile,
        )
        cues = SpeechCuePublicationService.publish(
            manifest,
            root / "semantic-cues",
            include_review_in_projection=include_review_in_projection,
        )
        return SpeechCueApplicationResult(
            transcript=transcription.transcript,
            cue_publication=cues,
            transcription_publication=transcription,
        )

    @staticmethod
    def transcribe_resumable_and_detect(
        media_path: str | Path,
        *,
        source_asset_id: str,
        source_frame_rate: FrameRate,
        keyword_profile: KeywordProfile,
        output_directory: str | Path,
        provider: FasterWhisperProvider,
        config: ChunkedTranscriptionConfig,
        language: str | None = None,
        include_review_in_projection: bool = False,
        resume: bool = False,
        restart: bool = False,
        probe: MediaProbe | None = None,
        extractor: AudioChunkExtractor | None = None,
    ) -> SpeechCueApplicationResult:
        """Run bounded/resumable local ASR with word timing, then detect cues.

        This is the creator path for long gameplay captures.  Checkpoint and
        partial state remain owned by ``ResumableTranscriptionService``; this
        bridge does not duplicate resumability semantics.  As with the direct
        route, model-download authority comes only from the supplied provider.
        """
        root = Path(output_directory).expanduser().resolve()
        transcription = ResumableTranscriptionService.run(
            media_path,
            root / "transcription",
            provider=provider,
            config=config,
            source_asset_id=source_asset_id,
            language=language,
            timeline_rate=source_frame_rate,
            include_word_timestamps=True,
            resume=resume,
            restart=restart,
            probe=probe,
            extractor=extractor,
        )
        manifest = SpeechCueDetectionService.detect(
            transcription.transcript,
            source_frame_rate=source_frame_rate,
            keyword_profile=keyword_profile,
        )
        cues = SpeechCuePublicationService.publish(
            manifest,
            root / "semantic-cues",
            include_review_in_projection=include_review_in_projection,
        )
        return SpeechCueApplicationResult(
            transcript=transcription.transcript,
            cue_publication=cues,
            transcription_publication=transcription,
        )
