"""Shared Training Studio audio playback for video-based learning surfaces.

The desktop product already depends on the FFmpeg toolchain for exact frame/OCR
work.  This module uses ``ffplay`` as the bounded Windows audio-output backend so
normal 1x playback has audible source audio without adding a second media SDK.
The controller is deliberately process-isolated: video decode remains PyAV and
training evidence extraction remains frame-authoritative.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import threading
from typing import Callable

from .dbd_training_diagnostics import DiagnosticLogger, get_diagnostic_logger


@dataclass(frozen=True, slots=True)
class AudioPlaybackStatus:
    available: bool
    playing: bool
    muted: bool
    volume_percent: int
    executable: str | None


def _candidate_ffplay(explicit: str | None) -> str | None:
    raw = (explicit or os.environ.get("BVP_FFPLAY") or "ffplay").strip()
    if not raw:
        return None
    candidate = Path(raw)
    if candidate.is_file():
        return str(candidate)
    found = shutil.which(raw)
    if found:
        return found
    # Reuse an explicitly configured FFmpeg toolchain directory when ffplay is
    # not separately configured. Official Windows FFmpeg bundles normally place
    # ffmpeg/ffprobe/ffplay beside each other.
    for env_name in ("BVP_FFMPEG", "BVP_FFPROBE"):
        configured = os.environ.get(env_name, "").strip()
        if not configured:
            continue
        tool = Path(configured).expanduser()
        if tool.is_file():
            sibling = tool.with_name("ffplay.exe" if os.name == "nt" else "ffplay")
            if sibling.is_file():
                return str(sibling)
    return None


class FfplayAudioController:
    """Small restart-safe audio controller for normal-speed preview playback."""

    def __init__(
        self,
        *,
        executable: str | None = None,
        diagnostics: DiagnosticLogger | None = None,
        diagnostic_feature: str = "TRAINING_MEDIA",
        player_id: str = "shared-media",
        popen_factory: Callable[..., subprocess.Popen] = subprocess.Popen,
    ) -> None:
        self._requested_executable = executable
        self._resolved_executable = _candidate_ffplay(executable)
        self._diagnostics = diagnostics or get_diagnostic_logger()
        self._feature = str(diagnostic_feature)
        self._player_id = str(player_id)
        self._popen_factory = popen_factory
        self._lock = threading.RLock()
        self._process: subprocess.Popen | None = None
        self._source: str | None = None
        self._start_seconds = 0.0
        self._volume_percent = 80
        self._muted = False

    @property
    def available(self) -> bool:
        return self._resolved_executable is not None

    @property
    def playing(self) -> bool:
        with self._lock:
            process = self._process
            return process is not None and process.poll() is None

    @property
    def status(self) -> AudioPlaybackStatus:
        return AudioPlaybackStatus(
            available=self.available,
            playing=self.playing,
            muted=self._muted,
            volume_percent=self._volume_percent,
            executable=self._resolved_executable,
        )

    def set_volume(self, percent: int) -> None:
        value = min(100, max(0, int(percent)))
        with self._lock:
            self._volume_percent = value
        self._diagnostics.emit(
            "AUDIO_VOLUME_CHANGED",
            feature=self._feature,
            player_id=self._player_id,
            volume_percent=value,
            muted=self._muted,
        )

    def set_muted(self, muted: bool) -> None:
        with self._lock:
            self._muted = bool(muted)
        self._diagnostics.emit(
            "AUDIO_MUTE_CHANGED",
            feature=self._feature,
            player_id=self._player_id,
            muted=self._muted,
            volume_percent=self._volume_percent,
        )

    def play(self, source: str, *, start_seconds: float = 0.0) -> bool:
        source_path = Path(source)
        if not source_path.is_file():
            raise ValueError("audio source video does not exist")
        executable = self._resolved_executable
        if executable is None:
            self._diagnostics.emit(
                "AUDIO_OUTPUT_UNAVAILABLE",
                level="ERROR",
                feature=self._feature,
                player_id=self._player_id,
                requested_executable=self._requested_executable or "ffplay",
            )
            return False
        self.stop()
        with self._lock:
            self._source = str(source_path)
            self._start_seconds = max(0.0, float(start_seconds))
            volume = 0 if self._muted else self._volume_percent
            cmd = [
                executable,
                "-nodisp",
                "-autoexit",
                "-loglevel",
                "error",
                "-ss",
                f"{self._start_seconds:.6f}",
                "-volume",
                str(volume),
                str(source_path),
            ]
            kwargs = {
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            }
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if creationflags:
                kwargs["creationflags"] = creationflags
            try:
                process = self._popen_factory(cmd, **kwargs)
            except Exception as exc:
                self._diagnostics.exception(
                    "AUDIO_OUTPUT_START_FAILED",
                    exc,
                    feature=self._feature,
                    player_id=self._player_id,
                    source=str(source_path),
                    start_seconds=self._start_seconds,
                )
                return False
            self._process = process
        self._diagnostics.emit(
            "AUDIO_OUTPUT_STARTED",
            feature=self._feature,
            player_id=self._player_id,
            source=str(source_path),
            start_seconds=self._start_seconds,
            volume_percent=volume,
        )
        return True

    def restart(self, source: str, *, start_seconds: float) -> bool:
        return self.play(source, start_seconds=start_seconds)

    def stop(self) -> None:
        with self._lock:
            process = self._process
            self._process = None
        if process is None:
            return
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=0.5)
        except Exception as exc:
            self._diagnostics.exception(
                "AUDIO_OUTPUT_STOP_FAILED",
                exc,
                feature=self._feature,
                player_id=self._player_id,
            )
        finally:
            self._diagnostics.emit(
                "AUDIO_OUTPUT_STOPPED",
                feature=self._feature,
                player_id=self._player_id,
            )

    def close(self) -> None:
        self.stop()


__all__ = ["AudioPlaybackStatus", "FfplayAudioController"]
