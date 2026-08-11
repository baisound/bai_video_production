"""Deterministic TASK-024 silence/filler/disfluency cut-candidate analysis.

The worker is deliberately review-only: it never mutates media, never edits a
Timeline, and never authorizes downstream cuts. Silence detection delegates to
the project's existing FFmpeg runtime using fixed argv/no shell. Transcript
evidence is converted to identifiers and reason codes; transcript text is not
written to candidate/report outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unicodedata
import wave
from typing import Any, Callable, Iterable, Mapping, Sequence

from .atomic import AtomicJsonWriter
from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes
from .subtitles import TranscriptManifest, TranscriptSegment


_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SAFE_REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_SAFE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SILENCE_START_RE = re.compile(r"silence_start:\s*([0-9]+(?:\.[0-9]+)?)")
_SILENCE_END_RE = re.compile(r"silence_end:\s*([0-9]+(?:\.[0-9]+)?)")


class CutCandidateKind(str, Enum):
    SILENCE = "SILENCE"
    FILLER = "FILLER"
    REPEATED_UTTERANCE = "REPEATED_UTTERANCE"


@dataclass(frozen=True, slots=True)
class CutCandidateConfig:
    silence_threshold_dbfs: float = -45.0
    min_silence_ms: int = 500
    min_cut_ms: int = 180
    preserve_leading_ms: int = 80
    preserve_trailing_ms: int = 120
    transcript_guard_ms: int = 80
    max_filler_ms: int = 2500
    repeat_max_gap_ms: int = 1500
    repeat_min_chars: int = 4
    transcript_duration_tolerance_ms: int = 500
    max_candidates: int = 100_000
    max_keep_blocks: int = 100_000
    ffmpeg_timeout_seconds: int = 1800
    filler_terms: tuple[str, ...] = (
        "えー",
        "えっと",
        "ええと",
        "えーと",
        "あの",
        "あのー",
        "うーん",
        "んー",
        "あー",
    )

    def __post_init__(self) -> None:
        if not -120.0 <= self.silence_threshold_dbfs <= -1.0:
            raise ValueError("silence_threshold_dbfs must be -120..-1")
        if not 50 <= self.min_silence_ms <= 60_000:
            raise ValueError("min_silence_ms must be 50-60000")
        if not 20 <= self.min_cut_ms <= self.min_silence_ms:
            raise ValueError("min_cut_ms must be 20..min_silence_ms")
        for name in ("preserve_leading_ms", "preserve_trailing_ms", "transcript_guard_ms"):
            value = getattr(self, name)
            if not 0 <= value <= 5000:
                raise ValueError(f"{name} must be 0-5000")
        if not 100 <= self.max_filler_ms <= 10_000:
            raise ValueError("max_filler_ms must be 100-10000")
        if not 0 <= self.repeat_max_gap_ms <= 10_000:
            raise ValueError("repeat_max_gap_ms must be 0-10000")
        if not 2 <= self.repeat_min_chars <= 100:
            raise ValueError("repeat_min_chars must be 2-100")
        if not 0 <= self.transcript_duration_tolerance_ms <= 10_000:
            raise ValueError("transcript_duration_tolerance_ms must be 0-10000")
        if not 1 <= self.max_candidates <= 1_000_000:
            raise ValueError("max_candidates must be 1-1000000")
        if not 1 <= self.max_keep_blocks <= 1_000_000:
            raise ValueError("max_keep_blocks must be 1-1000000")
        if not 1 <= self.ffmpeg_timeout_seconds <= 7200:
            raise ValueError("ffmpeg_timeout_seconds must be 1-7200")
        if not self.filler_terms or len(self.filler_terms) > 128:
            raise ValueError("filler_terms must contain 1-128 terms")
        normalized = tuple(_normalize_transcript_text(item) for item in self.filler_terms)
        if any(not item or len(item) > 32 for item in normalized):
            raise ValueError("filler_terms contain an invalid term")
        if len(set(normalized)) != len(normalized):
            raise ValueError("filler_terms must be unique after normalization")

    def to_hash_dict(self) -> dict[str, Any]:
        return {
            "config_version": "1.0.0",
            "silence_threshold_dbfs_milli": int(round(self.silence_threshold_dbfs * 1000)),
            "min_silence_ms": self.min_silence_ms,
            "min_cut_ms": self.min_cut_ms,
            "preserve_leading_ms": self.preserve_leading_ms,
            "preserve_trailing_ms": self.preserve_trailing_ms,
            "transcript_guard_ms": self.transcript_guard_ms,
            "max_filler_ms": self.max_filler_ms,
            "repeat_max_gap_ms": self.repeat_max_gap_ms,
            "repeat_min_chars": self.repeat_min_chars,
            "transcript_duration_tolerance_ms": self.transcript_duration_tolerance_ms,
            "max_candidates": self.max_candidates,
            "max_keep_blocks": self.max_keep_blocks,
            "ffmpeg_timeout_seconds": self.ffmpeg_timeout_seconds,
            "filler_terms": sorted(_normalize_transcript_text(item) for item in self.filler_terms),
        }

    @property
    def config_sha256(self) -> str:
        return sha256_bytes(canonical_json_bytes(self.to_hash_dict()))


@dataclass(frozen=True, slots=True)
class KeepBlock:
    keep_id: str
    start_us: int
    end_us: int
    reason: str
    source_segment_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not re.fullmatch(r"keep-\d{6}", self.keep_id):
            raise ValueError("keep_id is invalid")
        if self.start_us < 0 or self.end_us <= self.start_us:
            raise ValueError("keep block range must be positive and end-exclusive")
        if not _SAFE_REASON_RE.fullmatch(self.reason):
            raise ValueError("keep block reason is invalid")
        if not self.source_segment_ids:
            raise ValueError("keep block must cite at least one source segment")
        for value in self.source_segment_ids:
            if not _SAFE_SEGMENT_RE.fullmatch(value):
                raise ValueError("source segment id is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "keep_id": self.keep_id,
            "range_us": {"start": self.start_us, "end_exclusive": self.end_us},
            "reason": self.reason,
            "source_segment_ids": list(self.source_segment_ids),
        }


@dataclass(frozen=True, slots=True)
class CutCandidate:
    candidate_id: str
    kind: CutCandidateKind
    start_us: int
    end_us: int
    strength_score: int
    evidence_codes: tuple[str, ...]
    source_segment_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not re.fullmatch(r"cut-\d{6}", self.candidate_id):
            raise ValueError("candidate_id is invalid")
        if self.start_us < 0 or self.end_us <= self.start_us:
            raise ValueError("candidate range must be positive and end-exclusive")
        if not 0 <= self.strength_score <= 100:
            raise ValueError("strength_score must be 0-100")
        if not self.evidence_codes:
            raise ValueError("candidate requires evidence")
        for value in self.evidence_codes:
            if not _SAFE_REASON_RE.fullmatch(value):
                raise ValueError("evidence code is invalid")
        for value in self.source_segment_ids:
            if not _SAFE_SEGMENT_RE.fullmatch(value):
                raise ValueError("source segment id is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "kind": self.kind.value,
            "range_us": {"start": self.start_us, "end_exclusive": self.end_us},
            "strength_score": self.strength_score,
            "evidence_codes": list(self.evidence_codes),
            "source_segment_ids": list(self.source_segment_ids),
            "action": "REVIEW_ONLY",
            "auto_apply_authorized": False,
        }


@dataclass(frozen=True, slots=True)
class CutCandidateManifest:
    source_asset_id: str
    analysis_audio_sha256: str
    analysis_sample_rate: int
    source_duration_us: int
    config_sha256: str
    transcript_manifest_sha256: str | None
    candidates: tuple[CutCandidate, ...]
    keep_blocks: tuple[KeepBlock, ...]

    def __post_init__(self) -> None:
        validate_id(self.source_asset_id, IdKind.ASSET)
        if not _SHA256_RE.fullmatch(self.analysis_audio_sha256):
            raise ValueError("analysis_audio_sha256 is invalid")
        if not 8_000 <= self.analysis_sample_rate <= 192_000:
            raise ValueError("analysis_sample_rate is invalid")
        if self.source_duration_us <= 0:
            raise ValueError("source_duration_us must be positive")
        if not _SHA256_RE.fullmatch(self.config_sha256):
            raise ValueError("config_sha256 is invalid")
        if self.transcript_manifest_sha256 is not None and not _SHA256_RE.fullmatch(
            self.transcript_manifest_sha256
        ):
            raise ValueError("transcript_manifest_sha256 is invalid")

        previous_end = 0
        ids: set[str] = set()
        for item in self.candidates:
            if item.candidate_id in ids:
                raise ValueError("duplicate candidate_id")
            if item.start_us < previous_end:
                raise ValueError("cut candidates overlap or are out of order")
            ids.add(item.candidate_id)
            previous_end = item.end_us

        previous_end = 0
        keep_ids: set[str] = set()
        for item in self.keep_blocks:
            if item.keep_id in keep_ids:
                raise ValueError("duplicate keep_id")
            if item.start_us < previous_end:
                raise ValueError("keep blocks overlap or are out of order")
            keep_ids.add(item.keep_id)
            previous_end = item.end_us

        for candidate in self.candidates:
            for keep in self.keep_blocks:
                if candidate.start_us < keep.end_us and keep.start_us < candidate.end_us:
                    raise ValueError("cut candidate overlaps protected keep block")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "manifest_version": "1.0.0",
            "task_owner": "TASK-024",
            "downstream_plan_owner": "TASK-007",
            "downstream_execution_owner": "TASK-010",
            "source_asset_id": self.source_asset_id,
            "analysis_audio_sha256": self.analysis_audio_sha256,
            "analysis_sample_rate": self.analysis_sample_rate,
            "source_duration_us": self.source_duration_us,
            "config_sha256": self.config_sha256,
            "transcript_manifest_sha256": self.transcript_manifest_sha256,
            "transcript_text_in_manifest": False,
            "auto_apply_authorized": False,
            "candidates": [item.to_dict() for item in self.candidates],
            "keep_blocks": [item.to_dict() for item in self.keep_blocks],
        }
        body["manifest_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(frozen=True, slots=True)
class CutCandidatePublication:
    output_directory: Path
    manifest_path: Path
    report_path: Path
    manifest: CutCandidateManifest


@dataclass(frozen=True, slots=True)
class SilenceRange:
    start_us: int
    end_us: int

    def __post_init__(self) -> None:
        if self.start_us < 0 or self.end_us <= self.start_us:
            raise ValueError("silence range must be positive and end-exclusive")


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _normalize_transcript_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value)).casefold()
    output: list[str] = []
    for char in normalized:
        category = unicodedata.category(char)
        if char.isspace() or category.startswith("P") or category.startswith("Z"):
            continue
        output.append(char)
    return "".join(output)


def _is_filler_only(normalized_text: str, normalized_terms: Sequence[str]) -> bool:
    if not normalized_text:
        return False
    terms = tuple(sorted(set(normalized_terms), key=lambda value: (-len(value), value)))
    reachable = {0}
    for index in range(len(normalized_text) + 1):
        if index not in reachable:
            continue
        for term in terms:
            if normalized_text.startswith(term, index):
                reachable.add(index + len(term))
    return len(normalized_text) in reachable


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _seconds_to_us(value: str, *, end: bool) -> int:
    try:
        seconds = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid FFmpeg silence timestamp") from exc
    if not seconds.is_finite() or seconds < 0:
        raise ValueError("invalid FFmpeg silence timestamp")
    rounding = ROUND_CEILING if end else ROUND_FLOOR
    return int((seconds * 1_000_000).to_integral_value(rounding=rounding))


def _merge_keep_blocks(
    blocks: Iterable[tuple[int, int, str]],
) -> list[tuple[int, int, tuple[str, ...]]]:
    ordered = sorted(blocks, key=lambda item: (item[0], item[1], item[2]))
    merged: list[list[Any]] = []
    for start, end, segment_id in ordered:
        if not merged or start > merged[-1][1]:
            merged.append([start, end, [segment_id]])
            continue
        merged[-1][1] = max(merged[-1][1], end)
        if segment_id not in merged[-1][2]:
            merged[-1][2].append(segment_id)
    return [(item[0], item[1], tuple(item[2])) for item in merged]


def _subtract_ranges(
    start: int, end: int, protected: Sequence[tuple[int, int]]
) -> list[tuple[int, int]]:
    parts = [(start, end)]
    for keep_start, keep_end in protected:
        next_parts: list[tuple[int, int]] = []
        for part_start, part_end in parts:
            if keep_end <= part_start or keep_start >= part_end:
                next_parts.append((part_start, part_end))
                continue
            if part_start < keep_start:
                next_parts.append((part_start, keep_start))
            if keep_end < part_end:
                next_parts.append((keep_end, part_end))
        parts = next_parts
        if not parts:
            break
    return parts


def _inspect_pcm_wav(source: Path) -> tuple[int, int]:
    try:
        handle = wave.open(str(source), "rb")
    except (wave.Error, EOFError) as exc:
        raise ProductError(
            "ERR_CUT_AUDIO_FORMAT",
            "Analysis audio must be a readable PCM WAV file",
            ProductErrorCategory.VALIDATION,
        ) from exc
    with handle:
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        sample_rate = handle.getframerate()
        total_frames = handle.getnframes()
        compression = handle.getcomptype()
    if (
        compression != "NONE"
        or sample_width != 2
        or not 1 <= channels <= 8
        or not 8_000 <= sample_rate <= 192_000
        or total_frames <= 0
    ):
        raise ProductError(
            "ERR_CUT_AUDIO_FORMAT",
            "Analysis audio must be uncompressed 16-bit PCM WAV (1-8 channels, 8-192 kHz)",
            ProductErrorCategory.NOT_SUPPORTED,
            details={
                "channels": channels,
                "sample_width_bytes": sample_width,
                "sample_rate": sample_rate,
                "compression": compression,
            },
        )
    duration_us = (total_frames * 1_000_000 + sample_rate - 1) // sample_rate
    return sample_rate, duration_us


class FfmpegSilenceDetector:
    """Run FFmpeg silencedetect using fixed argv and parse bounded timestamps."""

    def __init__(
        self,
        *,
        executable: str = "ffmpeg",
        runner: Runner | None = None,
    ) -> None:
        if not executable or "\x00" in executable:
            raise ValueError("ffmpeg executable is invalid")
        self.executable = executable
        self._runner = runner or subprocess.run

    def detect(
        self,
        source: Path,
        *,
        duration_us: int,
        config: CutCandidateConfig,
    ) -> tuple[SilenceRange, ...]:
        threshold = f"{config.silence_threshold_dbfs:.3f}".rstrip("0").rstrip(".")
        duration = f"{Decimal(config.min_silence_ms) / Decimal(1000):.3f}"
        argv = [
            self.executable,
            "-hide_banner",
            "-nostdin",
            "-v",
            "info",
            "-nostats",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-vn",
            "-sn",
            "-dn",
            "-af",
            f"silencedetect=noise={threshold}dB:d={duration}",
            "-f",
            "null",
            "-",
        ]
        try:
            result = self._runner(
                argv,
                shell=False,
                capture_output=True,
                text=True,
                timeout=config.ffmpeg_timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ProductError(
                "ERR_CUT_FFMPEG_NOT_FOUND",
                "FFmpeg was not found for TASK-024 silence analysis",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ProductError(
                "ERR_CUT_FFMPEG_TIMEOUT",
                "FFmpeg silence analysis exceeded its bounded timeout",
                ProductErrorCategory.TIMEOUT,
                retryable=True,
            ) from exc
        except OSError as exc:
            raise ProductError(
                "ERR_CUT_FFMPEG_EXECUTION",
                "FFmpeg silence analysis could not be started",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                details={"exception_type": type(exc).__name__},
            ) from exc
        if result.returncode != 0:
            raise ProductError(
                "ERR_CUT_FFMPEG_EXECUTION",
                "FFmpeg silence analysis failed",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                details={"returncode": int(result.returncode)},
            )

        text = (result.stderr or "") + "\n" + (result.stdout or "")
        pending_start: int | None = None
        ranges: list[SilenceRange] = []
        tolerance_us = 2_000
        for line in text.splitlines():
            start_match = _SILENCE_START_RE.search(line)
            if start_match:
                if pending_start is not None:
                    raise ProductError(
                        "ERR_CUT_FFMPEG_OUTPUT",
                        "FFmpeg emitted nested silence_start events",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
                try:
                    pending_start = _seconds_to_us(start_match.group(1), end=False)
                except ValueError as exc:
                    raise ProductError(
                        "ERR_CUT_FFMPEG_OUTPUT",
                        "FFmpeg emitted an invalid silence_start timestamp",
                        ProductErrorCategory.DATA_INTEGRITY,
                    ) from exc
                continue
            end_match = _SILENCE_END_RE.search(line)
            if end_match:
                if pending_start is None:
                    raise ProductError(
                        "ERR_CUT_FFMPEG_OUTPUT",
                        "FFmpeg emitted silence_end without silence_start",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
                try:
                    end_us = _seconds_to_us(end_match.group(1), end=True)
                except ValueError as exc:
                    raise ProductError(
                        "ERR_CUT_FFMPEG_OUTPUT",
                        "FFmpeg emitted an invalid silence_end timestamp",
                        ProductErrorCategory.DATA_INTEGRITY,
                    ) from exc
                if end_us > duration_us + tolerance_us:
                    raise ProductError(
                        "ERR_CUT_FFMPEG_OUTPUT",
                        "FFmpeg silence range exceeds the analysis-audio duration",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
                end_us = min(end_us, duration_us)
                if pending_start < end_us:
                    ranges.append(SilenceRange(pending_start, end_us))
                pending_start = None

        if pending_start is not None and pending_start < duration_us:
            ranges.append(SilenceRange(pending_start, duration_us))

        previous_end = 0
        for item in ranges:
            if item.start_us < previous_end:
                raise ProductError(
                    "ERR_CUT_FFMPEG_OUTPUT",
                    "FFmpeg silence ranges overlap or are out of order",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            previous_end = item.end_us
        return tuple(ranges)


class CutCandidateAnalyzer:
    """Analyze normalized PCM audio plus optional Transcript into review-only candidates."""

    @staticmethod
    def analyze(
        audio_path: str | Path,
        *,
        source_asset_id: str,
        transcript: TranscriptManifest | None = None,
        config: CutCandidateConfig = CutCandidateConfig(),
        detector: FfmpegSilenceDetector | None = None,
    ) -> CutCandidateManifest:
        validate_id(source_asset_id, IdKind.ASSET)
        if transcript is not None and transcript.source_asset_id != source_asset_id:
            raise ProductError(
                "ERR_CUT_TRANSCRIPT_ASSET_MISMATCH",
                "Transcript source Asset does not match the requested source Asset",
                ProductErrorCategory.DATA_INTEGRITY,
            )

        source = Path(audio_path).expanduser()
        if source.is_symlink():
            raise ProductError(
                "ERR_CUT_AUDIO_SYMLINK",
                "Analysis audio symlinks are not accepted",
                ProductErrorCategory.SECURITY,
            )
        source = source.resolve()
        if not source.exists() or not source.is_file():
            raise ProductError(
                "ERR_CUT_AUDIO_NOT_FOUND",
                "Analysis audio must be an existing regular file",
                ProductErrorCategory.VALIDATION,
            )

        before = source.stat()
        before_sha = _file_sha256(source)
        sample_rate, duration_us = _inspect_pcm_wav(source)
        if transcript is not None and transcript.segments:
            transcript_end = max(item.end_us for item in transcript.segments)
            tolerance_us = config.transcript_duration_tolerance_ms * 1000
            if transcript_end > duration_us + tolerance_us:
                raise ProductError(
                    "ERR_CUT_TRANSCRIPT_DURATION",
                    "Transcript duration exceeds the analysis-audio duration tolerance",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={
                        "transcript_end_us": transcript_end,
                        "analysis_duration_us": duration_us,
                        "tolerance_us": tolerance_us,
                    },
                )
        silence_ranges = (detector or FfmpegSilenceDetector()).detect(
            source, duration_us=duration_us, config=config
        )
        after = source.stat()
        after_sha = _file_sha256(source)
        if (
            before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or before_sha != after_sha
        ):
            raise ProductError(
                "ERR_CUT_SOURCE_CHANGED",
                "Analysis audio changed while cut candidates were being computed",
                ProductErrorCategory.DATA_INTEGRITY,
            )

        transcript_hash: str | None = None
        transcript_candidates: list[
            tuple[CutCandidateKind, int, int, int, tuple[str, ...], tuple[str, ...]]
        ] = []
        protected: list[tuple[int, int, str]] = []
        reserved_cut_ranges: list[tuple[int, int]] = []

        if transcript is not None:
            transcript_hash = transcript.to_dict()["manifest_sha256"]
            (
                transcript_candidates,
                protected,
                reserved_cut_ranges,
            ) = CutCandidateAnalyzer._transcript_analysis(transcript, duration_us, config)

        merged_keep = _merge_keep_blocks(protected)
        keep_blocks = tuple(
            KeepBlock(f"keep-{index:06d}", start, end, "SPEECH_CONTENT", segment_ids)
            for index, (start, end, segment_ids) in enumerate(merged_keep, 1)
        )
        if len(keep_blocks) > config.max_keep_blocks:
            raise ProductError(
                "ERR_CUT_KEEP_BLOCK_LIMIT",
                "Protected keep-block count exceeds the configured safety bound",
                ProductErrorCategory.RESOURCE_EXHAUSTED,
                details={"count": len(keep_blocks), "limit": config.max_keep_blocks},
            )
        protected_ranges = [(item.start_us, item.end_us) for item in keep_blocks]
        all_reserved = sorted(protected_ranges + reserved_cut_ranges)

        raw_candidates: list[
            tuple[CutCandidateKind, int, int, int, tuple[str, ...], tuple[str, ...]]
        ] = list(transcript_candidates)

        min_cut_us = config.min_cut_ms * 1000
        for silent in silence_ranges:
            start = silent.start_us + config.preserve_leading_ms * 1000
            end = silent.end_us - config.preserve_trailing_ms * 1000
            if end - start < min_cut_us:
                continue
            for part_start, part_end in _subtract_ranges(start, end, all_reserved):
                if part_end - part_start < min_cut_us:
                    continue
                duration_ms = (part_end - part_start) // 1000
                score = min(100, 60 + max(0, duration_ms - config.min_cut_ms) // 25)
                evidence = ("FFMPEG_SILENCEDETECT",)
                if part_end - part_start >= 1_500_000:
                    evidence += ("LONG_PAUSE",)
                raw_candidates.append(
                    (
                        CutCandidateKind.SILENCE,
                        part_start,
                        part_end,
                        score,
                        evidence,
                        (),
                    )
                )

        raw_candidates.sort(key=lambda item: (item[1], item[2], item[0].value))
        if len(raw_candidates) > config.max_candidates:
            raise ProductError(
                "ERR_CUT_CANDIDATE_LIMIT",
                "Cut-candidate count exceeds the configured safety bound",
                ProductErrorCategory.RESOURCE_EXHAUSTED,
                details={"count": len(raw_candidates), "limit": config.max_candidates},
            )
        candidates: list[CutCandidate] = []
        previous_end = 0
        for kind, start, end, score, evidence, segment_ids in raw_candidates:
            if start < previous_end:
                raise ProductError(
                    "ERR_CUT_CANDIDATE_COLLISION",
                    "Cut-candidate analysis produced overlapping review ranges",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            candidates.append(
                CutCandidate(
                    f"cut-{len(candidates) + 1:06d}",
                    kind,
                    start,
                    end,
                    score,
                    evidence,
                    segment_ids,
                )
            )
            previous_end = end

        return CutCandidateManifest(
            source_asset_id=source_asset_id,
            analysis_audio_sha256=before_sha,
            analysis_sample_rate=sample_rate,
            source_duration_us=duration_us,
            config_sha256=config.config_sha256,
            transcript_manifest_sha256=transcript_hash,
            candidates=tuple(candidates),
            keep_blocks=keep_blocks,
        )

    @staticmethod
    def _transcript_analysis(
        transcript: TranscriptManifest,
        duration_us: int,
        config: CutCandidateConfig,
    ) -> tuple[
        list[tuple[CutCandidateKind, int, int, int, tuple[str, ...], tuple[str, ...]]],
        list[tuple[int, int, str]],
        list[tuple[int, int]],
    ]:
        normalized_terms = tuple(_normalize_transcript_text(item) for item in config.filler_terms)
        normalized = [_normalize_transcript_text(item.text) for item in transcript.segments]
        filler_ids: set[str] = set()
        repeat_ids: set[str] = set()

        for segment, text in zip(transcript.segments, normalized):
            if (
                segment.end_us - segment.start_us <= config.max_filler_ms * 1000
                and _is_filler_only(text, normalized_terms)
            ):
                filler_ids.add(segment.segment_id)

        for index in range(len(transcript.segments) - 1):
            first = transcript.segments[index]
            second = transcript.segments[index + 1]
            text = normalized[index]
            if first.segment_id in filler_ids or second.segment_id in filler_ids:
                continue
            if len(text) < config.repeat_min_chars or text != normalized[index + 1]:
                continue
            gap = second.start_us - first.end_us
            if 0 <= gap <= config.repeat_max_gap_ms * 1000:
                repeat_ids.add(first.segment_id)

        candidates: list[
            tuple[CutCandidateKind, int, int, int, tuple[str, ...], tuple[str, ...]]
        ] = []
        protected: list[tuple[int, int, str]] = []
        reserved: list[tuple[int, int]] = []
        guard = config.transcript_guard_ms * 1000

        for segment in transcript.segments:
            if segment.start_us >= duration_us:
                continue
            start = segment.start_us
            end = min(segment.end_us, duration_us)
            if end <= start:
                continue
            if segment.segment_id in repeat_ids:
                candidates.append(
                    (
                        CutCandidateKind.REPEATED_UTTERANCE,
                        start,
                        end,
                        85,
                        ("EXACT_ADJACENT_REPEAT", "KEEP_LATER_OCCURRENCE"),
                        (segment.segment_id,),
                    )
                )
                reserved.append((start, end))
                continue
            if segment.segment_id in filler_ids:
                candidates.append(
                    (
                        CutCandidateKind.FILLER,
                        start,
                        end,
                        90,
                        ("FILLER_ONLY_SEGMENT",),
                        (segment.segment_id,),
                    )
                )
                reserved.append((start, end))
                continue
            protected.append((max(0, start - guard), min(duration_us, end + guard), segment.segment_id))

        return candidates, protected, reserved


class CutCandidatePublicationService:
    @staticmethod
    def publish(
        manifest: CutCandidateManifest,
        output_directory: str | Path,
    ) -> CutCandidatePublication:
        output = Path(output_directory).expanduser()
        if output.is_symlink():
            raise ProductError(
                "ERR_CUT_OUTPUT_SYMLINK",
                "Cut-candidate output directory symlinks are not accepted",
                ProductErrorCategory.SECURITY,
            )
        output = output.resolve()
        output.mkdir(parents=True, exist_ok=True)
        manifest_path = output / "cut-candidates.json"
        report_path = output / "cut-candidate-report.json"
        AtomicJsonWriter.write(manifest_path, manifest.to_dict())

        counts = {kind.value: 0 for kind in CutCandidateKind}
        for item in manifest.candidates:
            counts[item.kind.value] += 1
        report = {
            "report_version": "1.0.0",
            "ok": True,
            "task_owner": "TASK-024",
            "source_asset_id": manifest.source_asset_id,
            "analysis_audio_sha256": manifest.analysis_audio_sha256,
            "source_duration_us": manifest.source_duration_us,
            "candidate_count": len(manifest.candidates),
            "candidate_counts": counts,
            "keep_block_count": len(manifest.keep_blocks),
            "transcript_used": manifest.transcript_manifest_sha256 is not None,
            "transcript_text_in_report": False,
            "auto_apply_authorized": False,
            "downstream_plan_owner": "TASK-007",
            "downstream_execution_owner": "TASK-010",
        }
        AtomicJsonWriter.write(report_path, report)
        return CutCandidatePublication(output, manifest_path, report_path, manifest)


def load_transcript_manifest(path: str | Path, *, max_bytes: int = 64 * 1024 * 1024) -> TranscriptManifest:
    source = Path(path).expanduser()
    if source.is_symlink():
        raise ProductError(
            "ERR_CUT_TRANSCRIPT_SYMLINK",
            "Transcript symlinks are not accepted",
            ProductErrorCategory.SECURITY,
        )
    source = source.resolve()
    if not source.exists() or not source.is_file():
        raise ProductError(
            "ERR_CUT_TRANSCRIPT_NOT_FOUND",
            "Transcript must be an existing regular JSON file",
            ProductErrorCategory.VALIDATION,
        )
    size = source.stat().st_size
    if size <= 0 or size > max_bytes:
        raise ProductError(
            "ERR_CUT_TRANSCRIPT_SIZE",
            "Transcript JSON size is outside the accepted bound",
            ProductErrorCategory.VALIDATION,
            details={"bytes": size, "max_bytes": max_bytes},
        )
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ProductError(
            "ERR_CUT_TRANSCRIPT_INVALID",
            "Transcript JSON is not valid UTF-8 JSON",
            ProductErrorCategory.VALIDATION,
        ) from exc
    if not isinstance(data, Mapping):
        raise ProductError(
            "ERR_CUT_TRANSCRIPT_INVALID",
            "Transcript JSON must contain an object",
            ProductErrorCategory.VALIDATION,
        )
    claimed = data.get("manifest_sha256")
    body = dict(data)
    body.pop("manifest_sha256", None)
    calculated = sha256_bytes(canonical_json_bytes(body))
    if not isinstance(claimed, str) or claimed != calculated:
        raise ProductError(
            "ERR_CUT_TRANSCRIPT_HASH",
            "Transcript manifest hash does not match its content",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    try:
        segments_raw = body["segments"]
        if not isinstance(segments_raw, list):
            raise ValueError("segments must be a list")
        segments = tuple(
            TranscriptSegment(
                segment_id=item["segment_id"],
                start_us=item["range_us"]["start"],
                end_us=item["range_us"]["end_exclusive"],
                text=item["text"],
                confidence=item.get("confidence"),
                speaker=item.get("speaker"),
            )
            for item in segments_raw
        )
        transcript = TranscriptManifest(
            source_asset_id=body["source_asset_id"],
            language=body["language"],
            provider_id=body["provider_id"],
            model_id=body["model_id"],
            segments=segments,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductError(
            "ERR_CUT_TRANSCRIPT_INVALID",
            "Transcript JSON does not satisfy the canonical Transcript contract",
            ProductErrorCategory.VALIDATION,
        ) from exc
    if transcript.to_dict()["manifest_sha256"] != claimed:
        raise ProductError(
            "ERR_CUT_TRANSCRIPT_HASH",
            "Transcript canonical reconstruction changed the manifest hash",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    return transcript
