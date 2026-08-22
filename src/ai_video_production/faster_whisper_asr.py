"""Local FasterWhisper adapter and deterministic Transcript/SRT publication."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import hashlib
import importlib
from pathlib import Path
import re
from typing import Any, Callable, Iterable, Mapping

from .atomic import AtomicJsonWriter
from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, generate_id
from .subtitles import (
    AsrRequest, SrtRenderer, SubtitlePlanningService, TranscriptManifest,
    TranscriptSegment, TranscriptWord,
)
from .timebase import FrameRate
from .timeline_mapping import EditSegment, TimelineMappingService


ModelFactory = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class FasterWhisperConfig:
    model: str = "small"
    device: str = "auto"
    compute_type: str = "int8"
    beam_size: int = 5
    vad_filter: bool = True
    allow_model_download: bool = False
    cache_directory: str | Path | None = None

    def __post_init__(self) -> None:
        if not self.model or "\x00" in self.model:
            raise ValueError("model must be non-empty text")
        if self.device not in {"auto", "cpu", "cuda"}:
            raise ValueError("device must be auto, cpu, or cuda")
        if not self.compute_type or "\x00" in self.compute_type:
            raise ValueError("compute_type must be non-empty text")
        if not 1 <= self.beam_size <= 20:
            raise ValueError("beam_size must be 1-20")
        if self.cache_directory is not None and "\x00" in str(self.cache_directory):
            raise ValueError("cache_directory is invalid")


def _microseconds(value: Any, *, end: bool) -> int:
    try:
        seconds = Decimal(str(value))
    except Exception as exc:
        raise ValueError("FasterWhisper returned an invalid timestamp") from exc
    if not seconds.is_finite() or seconds < 0:
        raise ValueError("FasterWhisper returned an invalid timestamp")
    rounding = ROUND_CEILING if end else ROUND_FLOOR
    return int((seconds * 1_000_000).to_integral_value(rounding=rounding))


def _default_model_factory() -> ModelFactory:
    try:
        module = importlib.import_module("faster_whisper")
    except ImportError as exc:
        raise ProductError(
            "ERR_FASTER_WHISPER_NOT_INSTALLED",
            "FasterWhisper is not installed. Run: python -m pip install -e .[asr]",
            ProductErrorCategory.EXTERNAL_DEPENDENCY,
        ) from exc
    return module.WhisperModel


class FasterWhisperProvider:
    provider_id = "faster-whisper"

    def __init__(self, config: FasterWhisperConfig, *, model_factory: ModelFactory | None = None) -> None:
        self.config = config
        self.model_id = (
            config.model if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}", config.model)
            else f"local-model-{hashlib.sha256(config.model.encode('utf-8')).hexdigest()[:12]}"
        )
        self._model_factory = model_factory
        self._loaded_model: Any | None = None

    def _model(self) -> Any:
        if self._loaded_model is not None:
            return self._loaded_model
        factory = self._model_factory or _default_model_factory()
        kwargs: dict[str, Any] = {
            "device": self.config.device,
            "compute_type": self.config.compute_type,
            "local_files_only": not self.config.allow_model_download,
        }
        if self.config.cache_directory is not None:
            kwargs["download_root"] = str(Path(self.config.cache_directory).expanduser().resolve())
        self._loaded_model = factory(self.config.model, **kwargs)
        return self._loaded_model

    def transcribe(self, request: AsrRequest) -> TranscriptManifest:
        source = Path(request.media_path).expanduser().resolve()
        if not source.exists() or not source.is_file():
            raise ProductError(
                "ERR_ASR_MEDIA_NOT_FOUND", "Input media must be an existing regular file",
                ProductErrorCategory.VALIDATION,
            )
        try:
            model = self._model()
            transcribe_kwargs: dict[str, Any] = {
                "language": request.language,
                "beam_size": self.config.beam_size,
                "vad_filter": self.config.vad_filter,
            }
            # Preserve the legacy provider call shape unless word timing is explicitly requested.
            if request.include_word_timestamps:
                transcribe_kwargs["word_timestamps"] = True
            raw_segments, info = model.transcribe(str(source), **transcribe_kwargs)
            segments = self._segments(
                raw_segments,
                include_word_timestamps=request.include_word_timestamps,
            )
        except ProductError:
            raise
        except Exception as exc:
            message = "FasterWhisper transcription failed"
            if not self.config.allow_model_download:
                message += "; install/cache the model or rerun with --allow-model-download"
            raise ProductError(
                "ERR_FASTER_WHISPER_EXECUTION", message,
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                details={"exception_type": type(exc).__name__},
            ) from exc
        language = request.language or getattr(info, "language", None) or "und"
        return TranscriptManifest(
            request.source_asset_id,
            language,
            self.provider_id,
            self.model_id,
            segments,
            request.include_word_timestamps,
        )

    @staticmethod
    def _segments(
        raw_segments: Iterable[Any],
        *,
        include_word_timestamps: bool = False,
    ) -> tuple[TranscriptSegment, ...]:
        output: list[TranscriptSegment] = []
        previous_end = 0
        for raw in raw_segments:
            text = str(getattr(raw, "text", "")).strip()
            if not text:
                continue
            start = max(previous_end, _microseconds(getattr(raw, "start"), end=False))
            end = _microseconds(getattr(raw, "end"), end=True)
            if end <= start:
                continue
            words = (
                FasterWhisperProvider._words(raw, segment_start=start, segment_end=end)
                if include_word_timestamps
                else ()
            )
            output.append(
                TranscriptSegment(
                    f"seg-{len(output) + 1:06d}",
                    start,
                    end,
                    text,
                    words=words,
                )
            )
            previous_end = end
        return tuple(output)

    @staticmethod
    def _words(
        raw_segment: Any,
        *,
        segment_start: int,
        segment_end: int,
    ) -> tuple[TranscriptWord, ...]:
        raw_words = getattr(raw_segment, "words", None)
        if raw_words is None:
            return ()
        output: list[TranscriptWord] = []
        previous_end = segment_start
        for raw_word in raw_words:
            text = str(getattr(raw_word, "word", getattr(raw_word, "text", ""))).strip()
            if not text:
                continue
            try:
                raw_start = _microseconds(getattr(raw_word, "start"), end=False)
                raw_end = _microseconds(getattr(raw_word, "end"), end=True)
            except (AttributeError, TypeError, ValueError):
                # Invalid/missing word timing must never be promoted to canonical word timing.
                continue
            # Word timing is semantic-edit evidence. Do not repair malformed, overlapping,
            # or out-of-segment timing into apparently precise WORD timing; drop the word
            # so the detector can conservatively fall back to a REVIEW-only segment cue.
            if (
                raw_start < segment_start
                or raw_end > segment_end
                or raw_start < previous_end
                or raw_end <= raw_start
            ):
                continue
            start = raw_start
            end = raw_end
            raw_probability = getattr(raw_word, "probability", None)
            confidence: float | None
            if raw_probability is None:
                confidence = None
            else:
                try:
                    probability = float(raw_probability)
                except (TypeError, ValueError):
                    probability = -1.0
                confidence = probability if 0.0 <= probability <= 1.0 else None
            output.append(TranscriptWord(start, end, text, confidence))
            previous_end = end
        return tuple(output)


@dataclass(frozen=True, slots=True)
class TranscriptionPublication:
    output_directory: Path
    transcript_path: Path
    subtitle_path: Path
    report_path: Path
    transcript: TranscriptManifest


class LocalTranscriptionService:
    """Publish private Transcript/SRT plus text-free operational evidence."""

    @staticmethod
    def run(
        media_path: str | Path,
        output_directory: str | Path,
        *,
        provider: FasterWhisperProvider,
        source_asset_id: str | None = None,
        language: str | None = None,
        timeline_rate: FrameRate = FrameRate(30000, 1001),
        include_word_timestamps: bool = False,
    ) -> TranscriptionPublication:
        asset_id = source_asset_id or generate_id(IdKind.ASSET)
        transcript = provider.transcribe(
            AsrRequest(
                asset_id,
                str(media_path),
                language,
                include_word_timestamps=include_word_timestamps,
            )
        )
        return LocalTranscriptionService.publish(
            transcript,
            output_directory,
            timeline_rate=timeline_rate,
            model_download_authorized=provider.config.allow_model_download,
        )

    @staticmethod
    def publish(
        transcript: TranscriptManifest,
        output_directory: str | Path,
        *,
        timeline_rate: FrameRate = FrameRate(30000, 1001),
        model_download_authorized: bool = False,
        operational_metadata: Mapping[str, object] | None = None,
    ) -> TranscriptionPublication:
        asset_id = transcript.source_asset_id
        output = Path(output_directory).expanduser().resolve()
        if transcript.segments:
            duration_us = max(item.end_us for item in transcript.segments)
            timeline = TimelineMappingService.build(
                [EditSegment("uncut-source", asset_id, 0, duration_us)],
                timeline_rate=timeline_rate,
            )
        else:
            timeline = TimelineMappingService.build([], timeline_rate=timeline_rate)
        plan = SubtitlePlanningService.build(transcript, timeline)
        output.mkdir(parents=True, exist_ok=True)
        transcript_path = output / "transcript.json"
        subtitle_path = output / "subtitles.srt"
        report_path = output / "transcription-report.json"
        AtomicJsonWriter.write(transcript_path, transcript.to_dict())
        LocalTranscriptionService._atomic_text(subtitle_path, SrtRenderer.render(plan))
        report: dict[str, object] = {
            "report_version": "1.0.0",
            "ok": True,
            "source_asset_id": asset_id,
            "provider_id": transcript.provider_id,
            "model_id": transcript.model_id,
            "language": transcript.language,
            "segment_count": len(transcript.segments),
            "subtitle_cue_count": len(plan.cues),
            "transcript_file": transcript_path.name,
            "subtitle_file": subtitle_path.name,
            "transcript_text_in_report": False,
            "network_used_for_inference": False,
            "model_download_authorized": bool(model_download_authorized),
        }
        if operational_metadata:
            allowed = {"execution_mode", "chunk_count", "resumed_chunk_count"}
            unknown = set(operational_metadata) - allowed
            if unknown:
                raise ValueError(f"unsupported operational metadata: {sorted(unknown)}")
            mode = operational_metadata.get("execution_mode")
            if mode is not None and (
                not isinstance(mode, str)
                or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", mode)
            ):
                raise ValueError("execution_mode is invalid")
            for name in ("chunk_count", "resumed_chunk_count"):
                value = operational_metadata.get(name)
                if value is not None and (
                    not isinstance(value, int) or isinstance(value, bool) or value < 0
                ):
                    raise ValueError(f"{name} must be a non-negative integer")
            report.update(dict(operational_metadata))
        AtomicJsonWriter.write(report_path, report)
        return TranscriptionPublication(output, transcript_path, subtitle_path, report_path, transcript)

    @staticmethod
    def _atomic_text(path: Path, value: str) -> None:
        import os
        import tempfile

        fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(value)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
