from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import json
from pathlib import Path
import subprocess
from typing import Any

from .errors import ProductError, ProductErrorCategory


class FrameRounding(str, Enum):
    FLOOR = "FLOOR"
    CEIL = "CEIL"
    NEAREST = "NEAREST"


class TimingKind(str, Enum):
    CFR = "CFR"
    VFR = "VFR"
    AUDIO_ONLY = "AUDIO_ONLY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class FrameRate:
    numerator: int
    denominator: int = 1

    def __post_init__(self) -> None:
        if self.numerator <= 0 or self.denominator <= 0:
            raise ValueError("frame rate numerator/denominator must be positive")
        reduced = Fraction(self.numerator, self.denominator)
        object.__setattr__(self, "numerator", reduced.numerator)
        object.__setattr__(self, "denominator", reduced.denominator)

    @classmethod
    def parse(cls, value: str) -> "FrameRate":
        try:
            if "/" in value:
                n, d = value.split("/", 1)
                return cls(int(n), int(d))
            return cls(int(value), 1)
        except (TypeError, ValueError, ZeroDivisionError) as exc:
            raise ValueError(f"invalid frame rate: {value!r}") from exc

    @property
    def fraction(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)

    def to_rational(self) -> str:
        return f"{self.numerator}/{self.denominator}"

    def frame_to_us(self, frame: int, *, rounding: FrameRounding = FrameRounding.NEAREST) -> int:
        if frame < 0:
            raise ValueError("frame must be >= 0")
        value = Fraction(frame * 1_000_000 * self.denominator, self.numerator)
        return _round_fraction(value, rounding)

    def us_to_frame(self, microseconds: int, *, rounding: FrameRounding = FrameRounding.NEAREST) -> int:
        if microseconds < 0:
            raise ValueError("microseconds must be >= 0")
        value = Fraction(microseconds * self.numerator, 1_000_000 * self.denominator)
        return _round_fraction(value, rounding)


def _round_fraction(value: Fraction, mode: FrameRounding) -> int:
    floor = value.numerator // value.denominator
    if mode is FrameRounding.FLOOR:
        return floor
    if mode is FrameRounding.CEIL:
        return floor if value.denominator * floor == value.numerator else floor + 1
    remainder = value - floor
    # Deterministic half-up avoids Python banker's rounding in canonical timing.
    return floor + (1 if remainder >= Fraction(1, 2) else 0)


def _safe_rate(value: Any) -> FrameRate | None:
    if value in (None, "", "0/0", "N/A"):
        return None
    try:
        return FrameRate.parse(str(value))
    except ValueError:
        return None


def _duration_us(value: Any) -> int | None:
    if value in (None, "", "N/A"):
        return None
    try:
        return max(0, int(Fraction(str(value)) * 1_000_000))
    except (ValueError, ZeroDivisionError):
        try:
            from decimal import Decimal, InvalidOperation
            return max(0, int(Decimal(str(value)) * Decimal(1_000_000)))
        except (ValueError, InvalidOperation):
            return None


@dataclass(frozen=True, slots=True)
class TimingInspection:
    kind: TimingKind
    duration_us: int | None
    avg_frame_rate: FrameRate | None
    nominal_frame_rate: FrameRate | None
    time_base: str | None
    sampled_packet_count: int
    sampled_delta_count: int
    variable_delta_count: int
    min_delta_us: int | None
    max_delta_us: int | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "duration_us": self.duration_us,
            "avg_frame_rate": self.avg_frame_rate.to_rational() if self.avg_frame_rate else None,
            "nominal_frame_rate": self.nominal_frame_rate.to_rational() if self.nominal_frame_rate else None,
            "time_base": self.time_base,
            "sampled_packet_count": self.sampled_packet_count,
            "sampled_delta_count": self.sampled_delta_count,
            "variable_delta_count": self.variable_delta_count,
            "min_delta_us": self.min_delta_us,
            "max_delta_us": self.max_delta_us,
            "reason": self.reason,
        }


class FFprobeTimingProbe:
    """Bounded packet-sampling timing probe using fixed argv and no shell."""

    def __init__(
        self,
        executable: str = "ffprobe",
        *,
        timeout_seconds: int = 30,
        max_packets: int = 180,
        sample_seconds: int = 12,
        delta_tolerance_us: int = 200,
    ) -> None:
        if not executable.strip():
            raise ValueError("ffprobe executable must be non-empty")
        if not 1 <= timeout_seconds <= 300:
            raise ValueError("timeout_seconds must be 1-300")
        if not 2 <= max_packets <= 5000:
            raise ValueError("max_packets must be 2-5000")
        if not 1 <= sample_seconds <= 120:
            raise ValueError("sample_seconds must be 1-120")
        if not 0 <= delta_tolerance_us <= 100_000:
            raise ValueError("delta_tolerance_us out of range")
        self.executable = executable
        self.timeout_seconds = timeout_seconds
        self.max_packets = max_packets
        self.sample_seconds = sample_seconds
        self.delta_tolerance_us = delta_tolerance_us

    def _run(self, argv: list[str]) -> dict[str, Any]:
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
                "ERR_PROVIDER_FFPROBE_NOT_FOUND", "ffprobe executable is not available",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ProductError(
                "ERR_PROVIDER_FFPROBE_TIMING_TIMEOUT", "ffprobe timing inspection timed out",
                ProductErrorCategory.TIMEOUT, retryable=True,
                details={"timeout_seconds": self.timeout_seconds},
            ) from exc
        if proc.returncode != 0:
            raise ProductError(
                "ERR_PROVIDER_FFPROBE_TIMING_FAILED", "ffprobe could not inspect timing metadata",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                details={"exit_code": proc.returncode},
            )
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise ProductError(
                "ERR_PROVIDER_FFPROBE_TIMING_INVALID_JSON", "ffprobe timing inspection returned invalid JSON",
                ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=True,
            ) from exc

    def inspect(self, path: str | Path) -> TimingInspection:
        target = Path(path)
        structural = self._run([
            self.executable, "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=avg_frame_rate,r_frame_rate,time_base,duration:format=duration",
            "-of", "json", str(target),
        ])
        streams = structural.get("streams") if isinstance(structural.get("streams"), list) else []
        if not streams:
            # Distinguish actual audio-only from invalid/unknown at the caller's structural media probe.
            return TimingInspection(TimingKind.AUDIO_ONLY, _duration_us((structural.get("format") or {}).get("duration")), None, None, None, 0, 0, 0, None, None, "no video stream")
        first = streams[0] if isinstance(streams[0], dict) else {}
        avg = _safe_rate(first.get("avg_frame_rate"))
        nominal = _safe_rate(first.get("r_frame_rate"))
        duration = _duration_us(first.get("duration")) or _duration_us((structural.get("format") or {}).get("duration"))
        time_base = str(first.get("time_base")) if first.get("time_base") else None

        packet_doc = self._run([
            self.executable, "-v", "error", "-select_streams", "v:0",
            "-read_intervals", f"%+{self.sample_seconds}",
            "-show_packets", "-show_entries", "packet=pts_time,dts_time,duration_time",
            "-of", "json", str(target),
        ])
        packets = packet_doc.get("packets") if isinstance(packet_doc.get("packets"), list) else []
        packets = packets[: self.max_packets]
        pts_us: list[int] = []
        packet_durations_us: list[int] = []
        for packet in packets:
            if not isinstance(packet, dict):
                continue
            value = packet.get("pts_time", packet.get("dts_time"))
            parsed = _duration_us(value)
            if parsed is not None:
                pts_us.append(parsed)
            packet_duration = _duration_us(packet.get("duration_time"))
            if packet_duration is not None and packet_duration > 0:
                packet_durations_us.append(packet_duration)
        # Packet order is decode order and PTS can move backwards with B-frames.
        # Prefer explicit packet durations; otherwise sort presentation timestamps
        # before deriving cadence so ordinary B-frame GOPs are not mislabeled VFR.
        if len(packet_durations_us) >= 2:
            cadence_samples = packet_durations_us
        else:
            ordered_pts = sorted(set(pts_us))
            cadence_samples = [b - a for a, b in zip(ordered_pts, ordered_pts[1:]) if b > a]
        positive_deltas = cadence_samples
        variable = 0
        min_delta = min(positive_deltas) if positive_deltas else None
        max_delta = max(positive_deltas) if positive_deltas else None
        if positive_deltas:
            # Median-ish reference without floats.
            ordered = sorted(positive_deltas)
            reference = ordered[len(ordered) // 2]
            variable = sum(abs(delta - reference) > self.delta_tolerance_us for delta in positive_deltas)

        if avg is None and nominal is None:
            kind, reason = TimingKind.UNKNOWN, "missing valid avg/r_frame_rate"
        elif avg is not None and nominal is not None and avg != nominal:
            kind, reason = TimingKind.VFR, "avg_frame_rate differs from nominal r_frame_rate"
        elif variable > 0:
            kind, reason = TimingKind.VFR, "sampled packet PTS deltas vary materially"
        else:
            kind, reason = TimingKind.CFR, "rate metadata agrees and bounded packet sample is stable"
        return TimingInspection(
            kind, duration, avg, nominal, time_base, len(pts_us), len(positive_deltas), variable,
            min_delta, max_delta, reason,
        )
