"""Resumable bounded-memory transcription for large local media."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from types import MappingProxyType
from typing import Any, Mapping, Protocol

from .atomic import AtomicJsonWriter
from .errors import ProductError, ProductErrorCategory
from .faster_whisper_asr import FasterWhisperProvider, LocalTranscriptionService, TranscriptionPublication
from .ids import IdKind, generate_id, validate_id
from .media_probe import FFprobeMediaProbe, MediaProbeResult
from .serialization import sha256_json, validate_sha256
from .subtitles import AsrRequest, TranscriptManifest, TranscriptSegment
from .timebase import FrameRate


_LANGUAGE = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")


@dataclass(frozen=True, slots=True)
class ChunkedTranscriptionConfig:
    chunk_seconds: int = 900
    overlap_seconds: int = 2
    ffmpeg_executable: str = "ffmpeg"
    ffprobe_executable: str = "ffprobe"
    ffmpeg_timeout_seconds: int = 600
    ffprobe_timeout_seconds: int = 30
    max_chunks: int = 10_000
    audio_sample_rate: int = 16_000

    def __post_init__(self) -> None:
        if not 10 <= self.chunk_seconds <= 86_400:
            raise ValueError("chunk_seconds must be 10-86400")
        if not 0 <= self.overlap_seconds < self.chunk_seconds:
            raise ValueError("overlap_seconds must be >= 0 and smaller than chunk_seconds")
        if not self.ffmpeg_executable.strip() or "\x00" in self.ffmpeg_executable:
            raise ValueError("ffmpeg_executable is invalid")
        if not self.ffprobe_executable.strip() or "\x00" in self.ffprobe_executable:
            raise ValueError("ffprobe_executable is invalid")
        if not 1 <= self.ffmpeg_timeout_seconds <= 3600:
            raise ValueError("ffmpeg_timeout_seconds must be 1-3600")
        if not 1 <= self.ffprobe_timeout_seconds <= 300:
            raise ValueError("ffprobe_timeout_seconds must be 1-300")
        if not 1 <= self.max_chunks <= 100_000:
            raise ValueError("max_chunks must be 1-100000")
        if self.audio_sample_rate not in {8_000, 16_000, 24_000, 32_000, 44_100, 48_000}:
            raise ValueError("audio_sample_rate is unsupported")


@dataclass(frozen=True, slots=True)
class TranscriptionChunk:
    chunk_id: str
    ordinal: int
    core_start_us: int
    core_end_us: int
    extraction_start_us: int
    extraction_end_us: int

    def __post_init__(self) -> None:
        if not re.fullmatch(r"chunk-\d{6}", self.chunk_id):
            raise ValueError("chunk_id is invalid")
        if self.ordinal < 1:
            raise ValueError("ordinal must be positive")
        if self.core_start_us < 0 or self.core_end_us <= self.core_start_us:
            raise ValueError("core range is invalid")
        if self.extraction_start_us < 0 or self.extraction_end_us <= self.extraction_start_us:
            raise ValueError("extraction range is invalid")
        if self.extraction_start_us > self.core_start_us or self.extraction_end_us < self.core_end_us:
            raise ValueError("extraction range must contain core range")

    def to_dict(self) -> dict[str, int | str]:
        return {
            "chunk_id": self.chunk_id,
            "ordinal": self.ordinal,
            "core_start_us": self.core_start_us,
            "core_end_us": self.core_end_us,
            "extraction_start_us": self.extraction_start_us,
            "extraction_end_us": self.extraction_end_us,
        }


def build_chunk_plan(
    duration_us: int, config: ChunkedTranscriptionConfig
) -> tuple[tuple[TranscriptionChunk, ...], str]:
    if duration_us <= 0:
        raise ValueError("duration_us must be positive")
    chunk_us = config.chunk_seconds * 1_000_000
    overlap_us = config.overlap_seconds * 1_000_000
    count = (duration_us + chunk_us - 1) // chunk_us
    if count > config.max_chunks:
        raise ProductError(
            "ERR_ASR_CHUNK_LIMIT",
            "large-media transcription exceeds the configured chunk limit",
            ProductErrorCategory.RESOURCE_EXHAUSTED,
            details={"chunk_count": count, "max_chunks": config.max_chunks},
        )
    chunks: list[TranscriptionChunk] = []
    for index in range(count):
        core_start = index * chunk_us
        core_end = min(duration_us, core_start + chunk_us)
        chunks.append(
            TranscriptionChunk(
                chunk_id=f"chunk-{index + 1:06d}",
                ordinal=index + 1,
                core_start_us=core_start,
                core_end_us=core_end,
                extraction_start_us=max(0, core_start - overlap_us),
                extraction_end_us=min(duration_us, core_end + overlap_us),
            )
        )
    body = {
        "plan_version": "1.0.0",
        "duration_us": duration_us,
        "chunks": [chunk.to_dict() for chunk in chunks],
    }
    return tuple(chunks), sha256_json(body)


class MediaProbe(Protocol):
    def probe(self, path: str | Path) -> MediaProbeResult: ...


class AudioChunkExtractor(Protocol):
    def extract(self, source: Path, chunk: TranscriptionChunk, target: Path) -> None: ...


class FfmpegAudioChunkExtractor:
    """Extract one bounded PCM audio window with fixed argv and no shell."""

    def __init__(self, config: ChunkedTranscriptionConfig) -> None:
        self.config = config

    @staticmethod
    def _seconds_arg(value_us: int) -> str:
        return f"{value_us // 1_000_000}.{value_us % 1_000_000:06d}"

    def extract(self, source: Path, chunk: TranscriptionChunk, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.unlink(missing_ok=True)
        duration_us = chunk.extraction_end_us - chunk.extraction_start_us
        argv = [
            self.config.ffmpeg_executable,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            self._seconds_arg(chunk.extraction_start_us),
            "-i",
            str(source),
            "-t",
            self._seconds_arg(duration_us),
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(self.config.audio_sample_rate),
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
            str(target),
        ]
        try:
            proc = subprocess.run(
                argv,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=self.config.ffmpeg_timeout_seconds,
                check=False,
                shell=False,
            )
        except FileNotFoundError as exc:
            raise ProductError(
                "ERR_PROVIDER_FFMPEG_NOT_FOUND",
                "ffmpeg executable is not available",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ProductError(
                "ERR_ASR_CHUNK_EXTRACTION_TIMEOUT",
                "ffmpeg timed out while extracting a bounded transcription chunk",
                ProductErrorCategory.TIMEOUT,
                retryable=True,
                details={"timeout_seconds": self.config.ffmpeg_timeout_seconds},
            ) from exc
        if proc.returncode != 0 or not target.is_file() or target.stat().st_size <= 0:
            raise ProductError(
                "ERR_ASR_CHUNK_EXTRACTION_FAILED",
                "ffmpeg could not extract a bounded audio chunk",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                details={"ffmpeg_exit_code": proc.returncode},
            )


@dataclass(frozen=True, slots=True)
class TranscriptionCheckpoint:
    source_asset_id: str
    source_sha256: str
    source_size_bytes: int
    duration_us: int
    provider_id: str
    model_id: str
    config_sha256: str
    chunk_plan_sha256: str
    detected_language: str | None
    completed_chunks: Mapping[str, str]

    def __post_init__(self) -> None:
        validate_id(self.source_asset_id, IdKind.ASSET)
        validate_sha256(self.source_sha256, field_name="source_sha256")
        validate_sha256(self.config_sha256, field_name="config_sha256")
        validate_sha256(self.chunk_plan_sha256, field_name="chunk_plan_sha256")
        if self.source_size_bytes < 0 or self.duration_us <= 0:
            raise ValueError("checkpoint source metadata is invalid")
        for name, value in (("provider_id", self.provider_id), ("model_id", self.model_id)):
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}", value):
                raise ValueError(f"{name} is invalid")
        if self.detected_language is not None and not _LANGUAGE.fullmatch(self.detected_language):
            raise ValueError("detected_language is invalid")
        copied = dict(self.completed_chunks)
        for chunk_id, checksum in copied.items():
            if not re.fullmatch(r"chunk-\d{6}", chunk_id):
                raise ValueError("completed chunk id is invalid")
            validate_sha256(checksum, field_name=f"completed_chunks[{chunk_id!r}]")
        object.__setattr__(self, "completed_chunks", MappingProxyType(copied))

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_version": "1.0.0",
            "source_asset_id": self.source_asset_id,
            "source_sha256": self.source_sha256,
            "source_size_bytes": self.source_size_bytes,
            "duration_us": self.duration_us,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "config_sha256": self.config_sha256,
            "chunk_plan_sha256": self.chunk_plan_sha256,
            "detected_language": self.detected_language,
            "completed_chunks": dict(self.completed_chunks),
            "contains_transcript_text": False,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TranscriptionCheckpoint":
        if value.get("checkpoint_version") != "1.0.0":
            raise ValueError("unsupported transcription checkpoint version")
        if value.get("contains_transcript_text") is not False:
            raise ValueError("checkpoint privacy marker is invalid")
        completed = value.get("completed_chunks")
        if not isinstance(completed, dict):
            raise ValueError("completed_chunks must be an object")
        return cls(
            source_asset_id=str(value["source_asset_id"]),
            source_sha256=str(value["source_sha256"]),
            source_size_bytes=int(value["source_size_bytes"]),
            duration_us=int(value["duration_us"]),
            provider_id=str(value["provider_id"]),
            model_id=str(value["model_id"]),
            config_sha256=str(value["config_sha256"]),
            chunk_plan_sha256=str(value["chunk_plan_sha256"]),
            detected_language=(
                str(value["detected_language"]) if value.get("detected_language") is not None else None
            ),
            completed_chunks={str(k): str(v) for k, v in completed.items()},
        )


def _assert_safe_work_path(path: Path) -> None:
    if path.is_symlink():
        raise ProductError(
            "ERR_ASR_WORK_STATE_UNSAFE",
            "transcription work state must not be a symbolic link",
            ProductErrorCategory.SECURITY,
        )


def _assert_source_unchanged(path: Path, *, size_bytes: int, mtime_ns: int) -> None:
    stat = path.stat()
    if stat.st_size != size_bytes or stat.st_mtime_ns != mtime_ns:
        raise ProductError(
            "ERR_ASR_SOURCE_MUTATED_DURING_RUN",
            "input media changed during transcription; restart from a stable source",
            ProductErrorCategory.DATA_INTEGRITY,
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(4 * 1024 * 1024)
            if not block:
                break
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _probe_duration(result: MediaProbeResult) -> int:
    if result.duration_us is not None and result.duration_us > 0:
        return result.duration_us
    candidates = [
        int(stream["duration_us"])
        for stream in result.streams
        if isinstance(stream.get("duration_us"), int) and int(stream["duration_us"]) > 0
    ]
    if candidates:
        return max(candidates)
    raise ProductError(
        "ERR_ASR_MEDIA_DURATION_UNKNOWN",
        "input media duration is unavailable; bounded chunk planning cannot proceed",
        ProductErrorCategory.VALIDATION,
    )


def _config_sha(
    provider: FasterWhisperProvider,
    config: ChunkedTranscriptionConfig,
    *,
    language: str | None,
    timeline_rate: FrameRate,
) -> str:
    provider_config = provider.config
    return sha256_json(
        {
            "provider_id": provider.provider_id,
            "model_id": provider.model_id,
            "device": provider_config.device,
            "compute_type": provider_config.compute_type,
            "beam_size": provider_config.beam_size,
            "vad_filter": provider_config.vad_filter,
            "allow_model_download": provider_config.allow_model_download,
            "requested_language": language,
            "chunk_seconds": config.chunk_seconds,
            "overlap_seconds": config.overlap_seconds,
            "ffmpeg_executable": config.ffmpeg_executable,
            "ffprobe_executable": config.ffprobe_executable,
            "audio_sample_rate": config.audio_sample_rate,
            "timeline_rate": timeline_rate.to_rational(),
        }
    )


def _read_json(path: Path, *, error_code: str, message: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductError(error_code, message, ProductErrorCategory.DATA_INTEGRITY) from exc
    if not isinstance(value, dict):
        raise ProductError(error_code, message, ProductErrorCategory.DATA_INTEGRITY)
    return value


def _checkpoint_from_path(path: Path) -> TranscriptionCheckpoint:
    try:
        return TranscriptionCheckpoint.from_dict(
            _read_json(
                path,
                error_code="ERR_ASR_CHECKPOINT_INVALID",
                message="transcription checkpoint is unreadable or invalid",
            )
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductError(
            "ERR_ASR_CHECKPOINT_INVALID",
            "transcription checkpoint is unreadable or invalid",
            ProductErrorCategory.DATA_INTEGRITY,
        ) from exc


def _assert_compatible(
    checkpoint: TranscriptionCheckpoint,
    *,
    source_asset_id: str,
    source_sha256: str,
    source_size_bytes: int,
    duration_us: int,
    provider_id: str,
    model_id: str,
    config_sha256: str,
    chunk_plan_sha256: str,
    valid_chunk_ids: set[str],
) -> None:
    mismatches: list[str] = []
    expected = {
        "source_asset_id": source_asset_id,
        "source_sha256": source_sha256,
        "source_size_bytes": source_size_bytes,
        "duration_us": duration_us,
        "provider_id": provider_id,
        "model_id": model_id,
        "config_sha256": config_sha256,
        "chunk_plan_sha256": chunk_plan_sha256,
    }
    for name, current in expected.items():
        if getattr(checkpoint, name) != current:
            mismatches.append(name)
    if not set(checkpoint.completed_chunks).issubset(valid_chunk_ids):
        mismatches.append("completed_chunks")
    if mismatches:
        raise ProductError(
            "ERR_INTEGRITY_CHECKPOINT_MISMATCH",
            "transcription checkpoint cannot be resumed because canonical inputs changed",
            ProductErrorCategory.DATA_INTEGRITY,
            details={"mismatch_fields": sorted(set(mismatches))},
        )


def _owned_segments(
    transcript: TranscriptManifest, chunk: TranscriptionChunk
) -> tuple[TranscriptSegment, ...]:
    owned: list[TranscriptSegment] = []
    for index, segment in enumerate(transcript.segments, 1):
        absolute_start = chunk.extraction_start_us + segment.start_us
        absolute_end = min(
            chunk.extraction_end_us,
            chunk.extraction_start_us + segment.end_us,
        )
        if absolute_end <= absolute_start:
            continue
        midpoint = (absolute_start + absolute_end) // 2
        if not chunk.core_start_us <= midpoint < chunk.core_end_us:
            continue
        start = max(chunk.core_start_us, absolute_start)
        end = min(chunk.core_end_us, absolute_end)
        if end <= start:
            continue
        owned.append(
            TranscriptSegment(
                segment_id=f"{chunk.chunk_id}-seg-{index:06d}",
                start_us=start,
                end_us=end,
                text=segment.text,
                confidence=segment.confidence,
                speaker=segment.speaker,
            )
        )
    return tuple(owned)


def _partial_dict(
    chunk: TranscriptionChunk,
    source_asset_id: str,
    language: str,
    segments: tuple[TranscriptSegment, ...],
) -> dict[str, Any]:
    return {
        "partial_version": "1.0.0",
        "chunk_id": chunk.chunk_id,
        "source_asset_id": source_asset_id,
        "language": language,
        "segments": [segment.to_dict() for segment in segments],
    }


def _load_partial(
    path: Path,
    *,
    checksum: str,
    chunk: TranscriptionChunk,
    source_asset_id: str,
) -> tuple[str, tuple[TranscriptSegment, ...]]:
    if path.is_symlink():
        raise ProductError(
            "ERR_ASR_WORK_STATE_UNSAFE",
            "transcription partial must not be a symbolic link",
            ProductErrorCategory.SECURITY,
            details={"chunk_id": chunk.chunk_id},
        )
    value = _read_json(
        path,
        error_code="ERR_ASR_PARTIAL_INVALID",
        message="a completed transcription chunk is missing or invalid",
    )
    if sha256_json(value) != checksum:
        raise ProductError(
            "ERR_ASR_PARTIAL_HASH_MISMATCH",
            "a completed transcription chunk failed integrity verification",
            ProductErrorCategory.DATA_INTEGRITY,
            details={"chunk_id": chunk.chunk_id},
        )
    try:
        if value.get("partial_version") != "1.0.0":
            raise ValueError("unsupported partial version")
        if value.get("chunk_id") != chunk.chunk_id:
            raise ValueError("chunk id mismatch")
        if value.get("source_asset_id") != source_asset_id:
            raise ValueError("source asset mismatch")
        language = str(value["language"])
        if not _LANGUAGE.fullmatch(language):
            raise ValueError("invalid language")
        items = value.get("segments")
        if not isinstance(items, list):
            raise ValueError("segments must be a list")
        segments: list[TranscriptSegment] = []
        previous_end = chunk.core_start_us
        for raw in items:
            if not isinstance(raw, dict) or not isinstance(raw.get("range_us"), dict):
                raise ValueError("invalid segment")
            segment = TranscriptSegment(
                segment_id=str(raw["segment_id"]),
                start_us=int(raw["range_us"]["start"]),
                end_us=int(raw["range_us"]["end_exclusive"]),
                text=str(raw["text"]),
                confidence=raw.get("confidence"),
                speaker=raw.get("speaker"),
            )
            if (
                segment.start_us < chunk.core_start_us
                or segment.end_us > chunk.core_end_us
                or segment.start_us < previous_end
            ):
                raise ValueError("segment is outside canonical chunk ownership")
            previous_end = segment.end_us
            segments.append(segment)
        return language, tuple(segments)
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductError(
            "ERR_ASR_PARTIAL_INVALID",
            "a completed transcription chunk is missing or invalid",
            ProductErrorCategory.DATA_INTEGRITY,
            details={"chunk_id": chunk.chunk_id},
        ) from exc


class ResumableTranscriptionService:
    WORK_DIRECTORY = ".bai-transcription-work"
    CHECKPOINT_FILE = "checkpoint.json"
    PARTIAL_DIRECTORY = "partials"

    @classmethod
    def run(
        cls,
        media_path: str | Path,
        output_directory: str | Path,
        *,
        provider: FasterWhisperProvider,
        config: ChunkedTranscriptionConfig,
        source_asset_id: str | None = None,
        language: str | None = None,
        timeline_rate: FrameRate = FrameRate(30000, 1001),
        resume: bool = False,
        restart: bool = False,
        probe: MediaProbe | None = None,
        extractor: AudioChunkExtractor | None = None,
    ) -> TranscriptionPublication:
        if resume and restart:
            raise ValueError("resume and restart are mutually exclusive")
        if language is not None and not _LANGUAGE.fullmatch(language):
            raise ValueError("language must be a BCP-47 language tag")

        source = Path(media_path).expanduser().resolve()
        if not source.is_file():
            raise ProductError(
                "ERR_ASR_MEDIA_NOT_FOUND",
                "Input media must be an existing regular file",
                ProductErrorCategory.VALIDATION,
            )
        output = Path(output_directory).expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        work = output / cls.WORK_DIRECTORY
        checkpoint_path = work / cls.CHECKPOINT_FILE
        partial_root = work / cls.PARTIAL_DIRECTORY

        if work.exists():
            _assert_safe_work_path(work)
        if checkpoint_path.exists() and checkpoint_path.is_symlink():
            raise ProductError(
                "ERR_ASR_WORK_STATE_UNSAFE",
                "transcription checkpoint must not be a symbolic link",
                ProductErrorCategory.SECURITY,
            )
        if partial_root.exists():
            _assert_safe_work_path(partial_root)

        if restart and work.exists():
            shutil.rmtree(work)

        if resume:
            if not checkpoint_path.is_file():
                raise ProductError(
                    "ERR_ASR_CHECKPOINT_NOT_FOUND",
                    "resume was requested but no transcription checkpoint exists",
                    ProductErrorCategory.STATE,
                )
            checkpoint = _checkpoint_from_path(checkpoint_path)
            asset_id = source_asset_id or checkpoint.source_asset_id
        else:
            if work.exists():
                raise ProductError(
                    "ERR_ASR_RESUME_REQUIRED",
                    "unfinished transcription state exists; use --resume or explicit --restart",
                    ProductErrorCategory.STATE,
                )
            asset_id = source_asset_id or generate_id(IdKind.ASSET)
            checkpoint = None

        validate_id(asset_id, IdKind.ASSET)
        active_probe = probe or FFprobeMediaProbe(
            config.ffprobe_executable,
            timeout_seconds=config.ffprobe_timeout_seconds,
        )
        probe_result = active_probe.probe(source)
        if not probe_result.has_audio:
            raise ProductError(
                "ERR_ASR_MEDIA_HAS_NO_AUDIO",
                "input media has no audio stream for transcription",
                ProductErrorCategory.VALIDATION,
            )
        duration_us = _probe_duration(probe_result)
        chunks, plan_sha = build_chunk_plan(duration_us, config)
        valid_chunk_ids = {chunk.chunk_id for chunk in chunks}
        source_stat = source.stat()
        source_size = source_stat.st_size
        source_mtime_ns = source_stat.st_mtime_ns
        source_sha = _sha256_file(source)
        _assert_source_unchanged(
            source, size_bytes=source_size, mtime_ns=source_mtime_ns
        )
        config_sha = _config_sha(
            provider,
            config,
            language=language,
            timeline_rate=timeline_rate,
        )

        if checkpoint is None:
            work.mkdir(parents=True, exist_ok=False)
            partial_root.mkdir(parents=True, exist_ok=False)
            checkpoint = TranscriptionCheckpoint(
                source_asset_id=asset_id,
                source_sha256=source_sha,
                source_size_bytes=source_size,
                duration_us=duration_us,
                provider_id=provider.provider_id,
                model_id=provider.model_id,
                config_sha256=config_sha,
                chunk_plan_sha256=plan_sha,
                detected_language=language,
                completed_chunks={},
            )
            AtomicJsonWriter.write(checkpoint_path, checkpoint.to_dict())
        else:
            _assert_compatible(
                checkpoint,
                source_asset_id=asset_id,
                source_sha256=source_sha,
                source_size_bytes=source_size,
                duration_us=duration_us,
                provider_id=provider.provider_id,
                model_id=provider.model_id,
                config_sha256=config_sha,
                chunk_plan_sha256=plan_sha,
                valid_chunk_ids=valid_chunk_ids,
            )
            partial_root.mkdir(parents=True, exist_ok=True)

        by_id = {chunk.chunk_id: chunk for chunk in chunks}
        for chunk_id, checksum in checkpoint.completed_chunks.items():
            _load_partial(
                partial_root / f"{chunk_id}.json",
                checksum=checksum,
                chunk=by_id[chunk_id],
                source_asset_id=asset_id,
            )

        resumed_count = len(checkpoint.completed_chunks)
        active_extractor = extractor or FfmpegAudioChunkExtractor(config)

        for chunk in chunks:
            if chunk.chunk_id in checkpoint.completed_chunks:
                continue
            _assert_source_unchanged(
                source, size_bytes=source_size, mtime_ns=source_mtime_ns
            )
            audio_path = work / f".{chunk.chunk_id}.wav"
            try:
                active_extractor.extract(source, chunk, audio_path)
                effective_language = language
                if effective_language is None and checkpoint.detected_language not in {None, "und"}:
                    effective_language = checkpoint.detected_language
                transcript = provider.transcribe(
                    AsrRequest(asset_id, str(audio_path), effective_language)
                )
                _assert_source_unchanged(
                    source, size_bytes=source_size, mtime_ns=source_mtime_ns
                )
                detected_language = checkpoint.detected_language
                if language is None and detected_language is None and transcript.language != "und":
                    detected_language = transcript.language
                owned = _owned_segments(transcript, chunk)
                partial = _partial_dict(
                    chunk,
                    asset_id,
                    transcript.language,
                    owned,
                )
                result = AtomicJsonWriter.write(
                    partial_root / f"{chunk.chunk_id}.json",
                    partial,
                )
                completed = dict(checkpoint.completed_chunks)
                completed[chunk.chunk_id] = result.checksum
                checkpoint = replace(
                    checkpoint,
                    detected_language=detected_language,
                    completed_chunks=completed,
                )
                AtomicJsonWriter.write(checkpoint_path, checkpoint.to_dict())
            finally:
                audio_path.unlink(missing_ok=True)

        all_segments: list[TranscriptSegment] = []
        observed_languages: list[str] = []
        for chunk in chunks:
            checksum = checkpoint.completed_chunks.get(chunk.chunk_id)
            if checksum is None:
                raise ProductError(
                    "ERR_ASR_CHECKPOINT_INCOMPLETE",
                    "transcription checkpoint is incomplete after chunk execution",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"chunk_id": chunk.chunk_id},
                )
            partial_language, segments = _load_partial(
                partial_root / f"{chunk.chunk_id}.json",
                checksum=checksum,
                chunk=chunk,
                source_asset_id=asset_id,
            )
            if partial_language != "und":
                observed_languages.append(partial_language)
            all_segments.extend(segments)

        final_language = (
            language
            or checkpoint.detected_language
            or (observed_languages[0] if observed_languages else "und")
        )
        _assert_source_unchanged(
            source, size_bytes=source_size, mtime_ns=source_mtime_ns
        )
        if _sha256_file(source) != source_sha:
            raise ProductError(
                "ERR_ASR_SOURCE_MUTATED_DURING_RUN",
                "input media changed during transcription; restart from a stable source",
                ProductErrorCategory.DATA_INTEGRITY,
            )

        transcript = TranscriptManifest(
            source_asset_id=asset_id,
            language=final_language,
            provider_id=provider.provider_id,
            model_id=provider.model_id,
            segments=tuple(all_segments),
        )
        publication = LocalTranscriptionService.publish(
            transcript,
            output,
            timeline_rate=timeline_rate,
            model_download_authorized=provider.config.allow_model_download,
            operational_metadata={
                "execution_mode": "CHUNKED_RESUMABLE",
                "chunk_count": len(chunks),
                "resumed_chunk_count": resumed_count,
            },
        )
        shutil.rmtree(work)
        return publication
