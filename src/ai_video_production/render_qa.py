"""TASK-011 render artifact QA and loudness/true-peak verification."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Protocol

from .errors import ProductError, ProductErrorCategory
from .media_probe import FFprobeMediaProbe, MediaProbeResult
from .serialization import canonical_json_bytes, sha256_bytes
from .timebase import FrameRate


@dataclass(frozen=True, slots=True)
class LoudnessProfile:
    target_lufs: float = -16.0
    tolerance_lu: float = 2.0
    max_true_peak_dbtp: float = -1.0
    max_lra_lu: float | None = None

    def __post_init__(self) -> None:
        if not -40.0 <= self.target_lufs <= -5.0:
            raise ValueError("target_lufs must be -40..-5")
        if not 0.1 <= self.tolerance_lu <= 10.0:
            raise ValueError("tolerance_lu must be 0.1..10")
        if not -20.0 <= self.max_true_peak_dbtp <= 0.0:
            raise ValueError("max_true_peak_dbtp must be -20..0")
        if self.max_lra_lu is not None and not 0.1 <= self.max_lra_lu <= 40.0:
            raise ValueError("max_lra_lu must be 0.1..40")

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_lufs": self.target_lufs,
            "tolerance_lu": self.tolerance_lu,
            "max_true_peak_dbtp": self.max_true_peak_dbtp,
            "max_lra_lu": self.max_lra_lu,
        }


@dataclass(frozen=True, slots=True)
class LoudnessMeasurement:
    integrated_lufs: float
    true_peak_dbtp: float
    loudness_range_lu: float

    def to_dict(self) -> dict[str, float]:
        return {
            "integrated_lufs": self.integrated_lufs,
            "true_peak_dbtp": self.true_peak_dbtp,
            "loudness_range_lu": self.loudness_range_lu,
        }


class LoudnessAnalyzer(Protocol):
    def analyze(self, path: str | Path, *, profile: LoudnessProfile) -> LoudnessMeasurement: ...


class FfmpegLoudnessAnalyzer:
    """Measure audio with FFmpeg loudnorm using fixed argv and no shell."""

    def __init__(self, executable: str = "ffmpeg", *, timeout_seconds: int = 1800) -> None:
        if not executable.strip():
            raise ValueError("ffmpeg executable must be non-empty")
        if not 1 <= timeout_seconds <= 7200:
            raise ValueError("timeout_seconds must be 1-7200")
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    def analyze(self, path: str | Path, *, profile: LoudnessProfile) -> LoudnessMeasurement:
        target = Path(path)
        if target.is_symlink() or not target.is_file() or target.stat().st_size <= 0:
            raise ProductError(
                "ERR_RENDER_QA_ARTIFACT_INVALID",
                "render artifact must be a non-empty regular file",
                ProductErrorCategory.VALIDATION,
            )
        filter_arg = (
            f"loudnorm=I={profile.target_lufs}:TP={profile.max_true_peak_dbtp}:"
            "LRA=11:print_format=json"
        )
        argv = [
            self.executable,
            "-hide_banner",
            "-nostdin",
            "-v", "info",
            "-i", str(target),
            "-map", "0:a:0",
            "-vn", "-sn", "-dn",
            "-af", filter_arg,
            "-f", "null",
            "-",
        ]
        try:
            proc = subprocess.run(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                check=False,
                shell=False,
            )
        except FileNotFoundError as exc:
            raise ProductError(
                "ERR_PROVIDER_FFMPEG_NOT_FOUND",
                "ffmpeg executable is not available for loudness QA",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ProductError(
                "ERR_RENDER_QA_LOUDNESS_TIMEOUT",
                "FFmpeg loudness analysis timed out",
                ProductErrorCategory.TIMEOUT,
                retryable=True,
                details={"timeout_seconds": self.timeout_seconds},
            ) from exc
        if proc.returncode != 0:
            raise ProductError(
                "ERR_RENDER_QA_LOUDNESS_FAILED",
                "FFmpeg failed while measuring render loudness",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                details={"ffmpeg_exit_code": proc.returncode},
            )
        measurement_json = self._extract_loudnorm_json(proc.stderr)
        try:
            return LoudnessMeasurement(
                integrated_lufs=float(Decimal(str(measurement_json["input_i"]))),
                true_peak_dbtp=float(Decimal(str(measurement_json["input_tp"]))),
                loudness_range_lu=float(Decimal(str(measurement_json["input_lra"]))),
            )
        except (KeyError, InvalidOperation, ValueError) as exc:
            raise ProductError(
                "ERR_RENDER_QA_LOUDNESS_RESULT_INVALID",
                "FFmpeg returned an invalid loudness measurement",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            ) from exc

    @staticmethod
    def _extract_loudnorm_json(stderr: str) -> dict[str, Any]:
        # loudnorm emits one JSON object near the end of stderr. Match the
        # smallest object containing the required input_* keys.
        for match in reversed(list(re.finditer(r"\{[\s\S]*?\}", stderr))):
            text = match.group(0)
            if '"input_i"' not in text or '"input_tp"' not in text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
        raise ProductError(
            "ERR_RENDER_QA_LOUDNESS_JSON_MISSING",
            "FFmpeg did not emit a parseable loudnorm measurement",
            ProductErrorCategory.EXTERNAL_DEPENDENCY,
        )


@dataclass(frozen=True, slots=True)
class RenderQAReport:
    artifact_sha256: str
    artifact_size_bytes: int
    media_probe: MediaProbeResult
    loudness: LoudnessMeasurement | None
    loudness_profile: LoudnessProfile | None
    expected_duration_frames: int
    timeline_rate: FrameRate
    duration_tolerance_frames: int
    checks: tuple[dict[str, Any], ...]

    @property
    def status(self) -> str:
        return "PASS" if all(item["status"] == "PASS" for item in self.checks) else "FAIL"

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "report_version": "1.0.0",
            "task_owner": "TASK-011",
            "artifact_sha256": self.artifact_sha256,
            "artifact_size_bytes": self.artifact_size_bytes,
            "media_probe": self.media_probe.to_dict(),
            "loudness": None if self.loudness is None else self.loudness.to_dict(),
            "loudness_profile": None if self.loudness_profile is None else self.loudness_profile.to_dict(),
            "expected_duration_frames": self.expected_duration_frames,
            "timeline_rate": {
                "numerator": self.timeline_rate.numerator,
                "denominator": self.timeline_rate.denominator,
            },
            "duration_tolerance_frames": self.duration_tolerance_frames,
            "checks": list(self.checks),
            "status": self.status,
            "render_path_persisted": False,
        }
        body["report_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class RenderQAService:
    def __init__(
        self,
        *,
        media_probe: FFprobeMediaProbe | Any | None = None,
        loudness_analyzer: LoudnessAnalyzer | None = None,
    ) -> None:
        self.media_probe = media_probe or FFprobeMediaProbe()
        self.loudness_analyzer = loudness_analyzer or FfmpegLoudnessAnalyzer()

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return "sha256:" + digest.hexdigest()

    def verify(
        self,
        render_path: str | Path,
        *,
        expected_duration_frames: int,
        timeline_rate: FrameRate,
        duration_tolerance_frames: int = 2,
        require_video: bool = True,
        require_audio: bool = True,
        loudness_profile: LoudnessProfile | None = LoudnessProfile(),
    ) -> RenderQAReport:
        path = Path(render_path)
        if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
            raise ProductError(
                "ERR_RENDER_QA_ARTIFACT_INVALID",
                "render artifact must be a non-empty regular file",
                ProductErrorCategory.VALIDATION,
            )
        if expected_duration_frames <= 0:
            raise ValueError("expected_duration_frames must be positive")
        if not 0 <= duration_tolerance_frames <= 300:
            raise ValueError("duration_tolerance_frames must be 0-300")

        probe = self.media_probe.probe(path)
        checks: list[dict[str, Any]] = []
        checks.append({"check": "NON_EMPTY_ARTIFACT", "status": "PASS"})
        checks.append({
            "check": "VIDEO_STREAM",
            "status": "PASS" if (probe.has_video or not require_video) else "FAIL",
        })
        checks.append({
            "check": "AUDIO_STREAM",
            "status": "PASS" if (probe.has_audio or not require_audio) else "FAIL",
        })

        if probe.duration_us is None:
            checks.append({"check": "DURATION", "status": "FAIL", "reason": "UNKNOWN_DURATION"})
        else:
            observed_frames = timeline_rate.us_to_frame(probe.duration_us)
            delta = abs(observed_frames - expected_duration_frames)
            checks.append({
                "check": "DURATION",
                "status": "PASS" if delta <= duration_tolerance_frames else "FAIL",
                "observed_frames": observed_frames,
                "expected_frames": expected_duration_frames,
                "delta_frames": delta,
            })

        loudness: LoudnessMeasurement | None = None
        if require_audio and loudness_profile is not None and probe.has_audio:
            loudness = self.loudness_analyzer.analyze(path, profile=loudness_profile)
            integrated_delta = abs(loudness.integrated_lufs - loudness_profile.target_lufs)
            checks.append({
                "check": "INTEGRATED_LOUDNESS",
                "status": "PASS" if integrated_delta <= loudness_profile.tolerance_lu else "FAIL",
                "delta_lu": round(integrated_delta, 3),
            })
            checks.append({
                "check": "TRUE_PEAK",
                "status": "PASS" if loudness.true_peak_dbtp <= loudness_profile.max_true_peak_dbtp else "FAIL",
            })
            if loudness_profile.max_lra_lu is not None:
                checks.append({
                    "check": "LOUDNESS_RANGE",
                    "status": "PASS" if loudness.loudness_range_lu <= loudness_profile.max_lra_lu else "FAIL",
                })

        return RenderQAReport(
            artifact_sha256=self._sha256_file(path),
            artifact_size_bytes=path.stat().st_size,
            media_probe=probe,
            loudness=loudness,
            loudness_profile=loudness_profile if loudness is not None else None,
            expected_duration_frames=expected_duration_frames,
            timeline_rate=timeline_rate,
            duration_tolerance_frames=duration_tolerance_frames,
            checks=tuple(checks),
        )
