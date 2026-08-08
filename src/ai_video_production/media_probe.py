from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from .assets import AssetType
from .errors import ProductError, ProductErrorCategory

_RATIONAL = re.compile(r"^-?\d+/[1-9]\d*$")


def _duration_us(value: Any) -> int | None:
    if value in (None, "", "N/A"):
        return None
    try:
        result = int(Decimal(str(value)) * Decimal(1_000_000))
    except (InvalidOperation, ValueError):
        return None
    return max(0, result)


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_rational(value: Any) -> str | None:
    text = str(value) if value is not None else ""
    return text if _RATIONAL.fullmatch(text) else None


@dataclass(frozen=True, slots=True)
class MediaProbeResult:
    format_name: str | None
    duration_us: int | None
    size_bytes: int
    bit_rate: int | None
    streams: tuple[dict[str, Any], ...]

    @property
    def has_video(self) -> bool:
        return any(stream.get("codec_type") == "video" for stream in self.streams)

    @property
    def has_audio(self) -> bool:
        return any(stream.get("codec_type") == "audio" for stream in self.streams)

    def to_dict(self) -> dict[str, Any]:
        return {
            "format_name": self.format_name,
            "duration_us": self.duration_us,
            "size_bytes": self.size_bytes,
            "bit_rate": self.bit_rate,
            "streams": [dict(stream) for stream in self.streams],
        }


class FFprobeMediaProbe:
    """Fixed-argv ffprobe adapter; never executes a shell command string."""

    def __init__(self, executable: str = "ffprobe", *, timeout_seconds: int = 30) -> None:
        if not executable.strip():
            raise ValueError("ffprobe executable must be non-empty")
        if not 1 <= timeout_seconds <= 300:
            raise ValueError("timeout_seconds must be 1-300")
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    def probe(self, path: str | Path) -> MediaProbeResult:
        target = Path(path)
        argv = [
            self.executable,
            "-v", "error",
            "-show_streams",
            "-show_format",
            "-of", "json",
            str(target),
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
                "ERR_PROVIDER_FFPROBE_NOT_FOUND",
                "ffprobe executable is not available",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                retryable=False,
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ProductError(
                "ERR_PROVIDER_FFPROBE_TIMEOUT",
                "ffprobe timed out while inspecting the staged asset",
                ProductErrorCategory.TIMEOUT,
                retryable=True,
                details={"timeout_seconds": self.timeout_seconds},
            ) from exc
        if proc.returncode != 0:
            # stderr can contain paths; do not persist it in ProductError details.
            raise ProductError(
                "ERR_INPUT_MEDIA_PROBE_FAILED",
                "ffprobe rejected or could not inspect the staged asset",
                ProductErrorCategory.VALIDATION,
                retryable=False,
                details={"ffprobe_exit_code": proc.returncode},
            )
        try:
            raw = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise ProductError(
                "ERR_PROVIDER_FFPROBE_INVALID_JSON",
                "ffprobe returned invalid JSON",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                retryable=True,
            ) from exc

        format_info = raw.get("format") if isinstance(raw.get("format"), dict) else {}
        streams: list[dict[str, Any]] = []
        for source in raw.get("streams", []):
            if not isinstance(source, dict):
                continue
            stream: dict[str, Any] = {
                "index": _optional_int(source.get("index")),
                "codec_type": source.get("codec_type"),
                "codec_name": source.get("codec_name"),
                "time_base": _safe_rational(source.get("time_base")),
                "duration_us": _duration_us(source.get("duration")),
            }
            if source.get("codec_type") == "video":
                stream.update({
                    "width": _optional_int(source.get("width")),
                    "height": _optional_int(source.get("height")),
                    "avg_frame_rate": _safe_rational(source.get("avg_frame_rate")),
                    "r_frame_rate": _safe_rational(source.get("r_frame_rate")),
                    "pix_fmt": source.get("pix_fmt"),
                })
            elif source.get("codec_type") == "audio":
                stream.update({
                    "sample_rate": _optional_int(source.get("sample_rate")),
                    "channels": _optional_int(source.get("channels")),
                    "channel_layout": source.get("channel_layout"),
                })
            streams.append({key: value for key, value in stream.items() if value is not None})

        return MediaProbeResult(
            format_name=str(format_info.get("format_name")) if format_info.get("format_name") else None,
            duration_us=_duration_us(format_info.get("duration")),
            size_bytes=target.stat().st_size,
            bit_rate=_optional_int(format_info.get("bit_rate")),
            streams=tuple(streams),
        )

    @staticmethod
    def assert_compatible(asset_type: AssetType, result: MediaProbeResult) -> None:
        needs_video = asset_type in {AssetType.VIDEO, AssetType.IMAGE, AssetType.GENERATED_VIDEO}
        needs_audio = asset_type in {AssetType.AUDIO, AssetType.BGM, AssetType.SFX}
        if needs_video and not result.has_video:
            raise ProductError(
                "ERR_INPUT_MEDIA_TYPE_MISMATCH",
                f"{asset_type.value} ingest requires a video/image stream",
                ProductErrorCategory.VALIDATION,
            )
        if needs_audio and not result.has_audio:
            raise ProductError(
                "ERR_INPUT_MEDIA_TYPE_MISMATCH",
                f"{asset_type.value} ingest requires an audio stream",
                ProductErrorCategory.VALIDATION,
            )
