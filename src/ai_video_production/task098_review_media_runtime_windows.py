"""Registry-bound WAV review runtime for TASK-098 A4-R2b.

The runtime is disabled by default and has no Shell composition.  It resolves
only a canonical Asset ID, keeps decoded audio and waveform peaks process-local,
and returns the non-canonical A4-R2 observation contract.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from io import BytesIO
import os
from pathlib import Path
import stat
import struct
import threading
import wave
from typing import Protocol

from .assets import AssetRecord, AssetType, RightsStatus
from .errors import ProductError
from .paths import LogicalPathResolver
from .task098_review_media_runtime_contract import (
    MAX_WAVEFORM_POINT_COUNT,
    ReviewMediaRuntimeObservation,
    ReviewMediaRuntimeRequest,
    ReviewMediaRuntimeState,
)


MAX_DECODED_RANGE_BYTES = 16 * 1024 * 1024
MAX_SOURCE_WAV_BYTES = 8 * 1024 * 1024 * 1024
MAX_AUDIO_CHANNELS = 8
_HASH_CHUNK_BYTES = 4 * 1024 * 1024
_ALLOWED_ASSET_TYPES = frozenset({AssetType.AUDIO, AssetType.BGM, AssetType.SFX})
_ALLOWED_RIGHTS = frozenset(
    {RightsStatus.OWNED, RightsStatus.LICENSED, RightsStatus.PERMISSION_GRANTED}
)


class AssetLookupPort(Protocol):
    def get_asset(self, asset_id: str) -> AssetRecord: ...


class ReviewAudioPlaybackBackend(Protocol):
    def play(self, wav_body: bytes, cancel_event: threading.Event) -> None: ...

    def stop(self) -> None: ...


class ReviewRuntimeCancelled(Exception):
    """The owned runtime stopped without leaving an unknown native effect."""


class ReviewRuntimeDisconnected(Exception):
    """Native execution or cleanup could not be observed to completion."""


class ReviewRuntimeKnownFailure(Exception):
    """The runtime rejected or failed the request with a known terminal result."""


@dataclass(slots=True)
class WindowsWavePlaybackBackend:
    """Explicit Windows-only in-memory PCM WAV playback backend."""

    poll_interval_seconds: float = 0.02
    stop_timeout_seconds: float = 2.0

    def __post_init__(self) -> None:
        if self.poll_interval_seconds <= 0 or self.stop_timeout_seconds <= 0:
            raise ValueError("playback timing bounds must be positive")

    @staticmethod
    def _winsound():
        if os.name != "nt":
            raise ReviewRuntimeKnownFailure("Windows playback is unavailable")
        try:
            import winsound
        except ImportError as exc:  # pragma: no cover - defensive Windows failure
            raise ReviewRuntimeKnownFailure("Windows playback is unavailable") from exc
        return winsound

    def stop(self) -> None:
        winsound = self._winsound()
        try:
            winsound.PlaySound(None, 0)
        except (OSError, RuntimeError) as exc:
            raise ReviewRuntimeDisconnected("audio-device stop was not observed") from exc

    def play(self, wav_body: bytes, cancel_event: threading.Event) -> None:
        if type(wav_body) is not bytes or not wav_body:
            raise ReviewRuntimeKnownFailure("WAV body is invalid")
        if not isinstance(cancel_event, threading.Event):
            raise ReviewRuntimeKnownFailure("cancel token is invalid")
        if cancel_event.is_set():
            raise ReviewRuntimeCancelled()
        winsound = self._winsound()
        completed = threading.Event()
        failures: list[BaseException] = []

        def worker() -> None:
            try:
                winsound.PlaySound(
                    wav_body,
                    winsound.SND_MEMORY
                    | getattr(winsound, "SND_SYNC", 0)
                    | winsound.SND_NODEFAULT,
                )
            except Exception as exc:
                failures.append(exc)
            finally:
                completed.set()

        thread = threading.Thread(
            target=worker,
            name="task098-review-audio",
            daemon=True,
        )
        thread.start()
        while not completed.wait(self.poll_interval_seconds):
            if cancel_event.is_set():
                self.stop()
                if not completed.wait(self.stop_timeout_seconds):
                    raise ReviewRuntimeDisconnected(
                        "audio-device cancellation was not observed"
                    )
                raise ReviewRuntimeCancelled()
        if failures:
            raise ReviewRuntimeKnownFailure("native playback failed") from failures[0]
        if cancel_event.is_set():
            raise ReviewRuntimeCancelled()


def _file_identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)


def _hash_open_file(handle) -> str:
    digest = hashlib.sha256()
    handle.seek(0)
    for chunk in iter(lambda: handle.read(_HASH_CHUNK_BYTES), b""):
        digest.update(chunk)
    handle.seek(0)
    return "sha256:" + digest.hexdigest()


def _decode_sample(body: memoryview, offset: int, width: int) -> int:
    if width == 1:
        return int(body[offset]) - 128
    if width == 2:
        return struct.unpack_from("<h", body, offset)[0]
    if width == 3:
        value = int(body[offset]) | (int(body[offset + 1]) << 8) | (
            int(body[offset + 2]) << 16
        )
        return value - (1 << 24) if value & (1 << 23) else value
    if width == 4:
        return struct.unpack_from("<i", body, offset)[0]
    raise ReviewRuntimeKnownFailure("PCM sample width is unsupported")


def _waveform_peaks(
    pcm_body: bytes,
    *,
    frame_count: int,
    channels: int,
    sample_width: int,
) -> list[int]:
    if frame_count <= 0:
        raise ReviewRuntimeKnownFailure("decoded range is empty")
    point_count = min(frame_count, MAX_WAVEFORM_POINT_COUNT)
    peaks = [0] * point_count
    view = memoryview(pcm_body)
    frame_bytes = channels * sample_width
    try:
        for frame_index in range(frame_count):
            bucket = frame_index * point_count // frame_count
            base = frame_index * frame_bytes
            peak = 0
            for channel in range(channels):
                sample = abs(
                    _decode_sample(view, base + channel * sample_width, sample_width)
                )
                if sample > peak:
                    peak = sample
            if peak > peaks[bucket]:
                peaks[bucket] = peak
        return peaks
    finally:
        view.release()


def _range_wav(
    pcm_body: bytes,
    *,
    channels: int,
    sample_width: int,
    sample_rate_hz: int,
) -> bytes:
    output = BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(channels)
        target.setsampwidth(sample_width)
        target.setframerate(sample_rate_hz)
        target.writeframes(pcm_body)
    return output.getvalue()


class RegistryBoundReviewMediaRuntimePort:
    """Concrete exact-Asset WAV runtime; construction is the activation gate."""

    def __init__(
        self,
        *,
        assets: AssetLookupPort,
        resolver: LogicalPathResolver,
        playback: ReviewAudioPlaybackBackend,
    ) -> None:
        if not hasattr(assets, "get_asset"):
            raise ValueError("assets lookup is invalid")
        if type(resolver) is not LogicalPathResolver:
            raise ValueError("resolver is invalid")
        if not hasattr(playback, "play") or not hasattr(playback, "stop"):
            raise ValueError("playback backend is invalid")
        self._assets = assets
        self._resolver = resolver
        self._playback = playback
        self._state_lock = threading.Lock()
        self._active_cancel: threading.Event | None = None
        self._cleanup_disconnected = threading.Event()

    def cancel(self) -> bool:
        with self._state_lock:
            active = self._active_cancel
        if active is None:
            return False
        active.set()
        try:
            self._playback.stop()
        except ReviewRuntimeDisconnected:
            self._cleanup_disconnected.set()
        except Exception:
            self._cleanup_disconnected.set()
        return True

    @staticmethod
    def _observation(
        request: ReviewMediaRuntimeRequest,
        state: ReviewMediaRuntimeState,
        *,
        playback: bool = False,
        waveform: bool = False,
        point_count: int | None = None,
        reasons: tuple[str, ...] = (),
        connected: bool = True,
    ) -> ReviewMediaRuntimeObservation:
        return ReviewMediaRuntimeObservation(
            request.request_sha256,
            state,
            connected,
            playback,
            waveform,
            point_count,
            reasons,
        )

    def _load_exact_range(
        self, request: ReviewMediaRuntimeRequest
    ) -> tuple[bytes, int, int]:
        asset = self._assets.get_asset(request.source_asset_id)
        if type(asset) is not AssetRecord:
            raise ReviewRuntimeKnownFailure("registry result is invalid")
        if (
            asset.asset_type not in _ALLOWED_ASSET_TYPES
            or asset.rights_status not in _ALLOWED_RIGHTS
            or asset.checksum != request.source_content_sha256
        ):
            raise ReviewRuntimeKnownFailure("Asset identity or rights mismatch")
        self._resolver.assert_job_scope(asset.logical_uri, asset.production_job_id)
        resolved = self._resolver.resolve_existing_regular_file(asset.logical_uri)
        if not isinstance(resolved, Path):
            raise ReviewRuntimeKnownFailure("local Asset resolution is unavailable")
        if resolved.is_symlink():
            raise ReviewRuntimeKnownFailure("symlink Assets are not accepted")
        before = resolved.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size <= 0
            or before.st_size > MAX_SOURCE_WAV_BYTES
        ):
            raise ReviewRuntimeKnownFailure("Asset is not a regular file")

        with resolved.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if _file_identity(before) != _file_identity(opened):
                raise ReviewRuntimeKnownFailure("Asset identity changed before open")
            if _hash_open_file(handle) != request.source_content_sha256:
                raise ReviewRuntimeKnownFailure("Asset content checksum mismatch")
            try:
                with wave.open(handle, "rb") as source:
                    channels = source.getnchannels()
                    sample_width = source.getsampwidth()
                    sample_rate = source.getframerate()
                    total_frames = source.getnframes()
                    compression = source.getcomptype()
                    range_frames = (
                        request.range_end_sample_exclusive
                        - request.range_start_sample
                    )
                    decoded_bytes = range_frames * channels * sample_width
                    if (
                        compression != "NONE"
                        or not 1 <= channels <= MAX_AUDIO_CHANNELS
                        or sample_width not in {1, 2, 3, 4}
                        or sample_rate != request.sample_rate_hz
                        or total_frames != request.source_duration_samples
                        or decoded_bytes <= 0
                        or decoded_bytes > MAX_DECODED_RANGE_BYTES
                    ):
                        raise ReviewRuntimeKnownFailure(
                            "WAV format, duration or range is unsupported"
                        )
                    source.setpos(request.range_start_sample)
                    pcm_body = source.readframes(range_frames)
            except (EOFError, wave.Error) as exc:
                raise ReviewRuntimeKnownFailure("Asset is not a supported PCM WAV") from exc
            expected_bytes = range_frames * channels * sample_width
            if len(pcm_body) != expected_bytes:
                raise ReviewRuntimeKnownFailure("decoded WAV range is incomplete")
            if _hash_open_file(handle) != request.source_content_sha256:
                raise ReviewRuntimeKnownFailure("Asset content changed during read")
            after_open = os.fstat(handle.fileno())
            after_path = resolved.stat(follow_symlinks=False)
            resolved_after = self._resolver.resolve_existing_regular_file(
                asset.logical_uri
            )
            if (
                _file_identity(opened) != _file_identity(after_open)
                or _file_identity(opened) != _file_identity(after_path)
                or resolved_after != resolved
                or resolved.is_symlink()
            ):
                raise ReviewRuntimeKnownFailure("Asset identity changed during read")
        return pcm_body, channels, sample_width

    def _play_with_cleanup(
        self, wav_body: bytes, cancel_event: threading.Event
    ) -> None:
        outcome: Exception | None = None
        try:
            self._playback.play(wav_body, cancel_event)
        except (
            ReviewRuntimeCancelled,
            ReviewRuntimeDisconnected,
            ReviewRuntimeKnownFailure,
        ) as exc:
            outcome = exc
        except Exception as exc:
            outcome = ReviewRuntimeKnownFailure("playback backend failed")
            outcome.__cause__ = exc
        try:
            self._playback.stop()
        except Exception as exc:
            raise ReviewRuntimeDisconnected(
                "audio-device cleanup was not observed"
            ) from exc
        if outcome is not None:
            raise outcome

    def execute(
        self, request: ReviewMediaRuntimeRequest
    ) -> ReviewMediaRuntimeObservation:
        if type(request) is not ReviewMediaRuntimeRequest:
            raise ValueError("request is invalid")
        with self._state_lock:
            if self._active_cancel is not None:
                return self._observation(
                    request,
                    ReviewMediaRuntimeState.FAILED_KNOWN,
                    reasons=("RUNTIME_FAILED",),
                )
            cancel_event = threading.Event()
            self._active_cancel = cancel_event
            self._cleanup_disconnected.clear()

        pcm_body = b""
        waveform_peaks: list[int] | None = None
        try:
            if cancel_event.is_set():
                raise ReviewRuntimeCancelled()
            pcm_body, channels, sample_width = self._load_exact_range(request)
            if cancel_event.is_set():
                raise ReviewRuntimeCancelled()

            waveform_requested = "WAVEFORM_VIEW" in request.requested_operations
            playback_requested = "AUDITION" in request.requested_operations
            if waveform_requested:
                waveform_peaks = _waveform_peaks(
                    pcm_body,
                    frame_count=(
                        request.range_end_sample_exclusive
                        - request.range_start_sample
                    ),
                    channels=channels,
                    sample_width=sample_width,
                )
            if cancel_event.is_set():
                raise ReviewRuntimeCancelled()
            if playback_requested:
                self._play_with_cleanup(
                    _range_wav(
                        pcm_body,
                        channels=channels,
                        sample_width=sample_width,
                        sample_rate_hz=request.sample_rate_hz,
                    ),
                    cancel_event,
                )
            if self._cleanup_disconnected.is_set():
                raise ReviewRuntimeDisconnected()
            return self._observation(
                request,
                ReviewMediaRuntimeState.SUCCEEDED,
                playback=playback_requested,
                waveform=waveform_requested,
                point_count=(len(waveform_peaks) if waveform_peaks is not None else None),
            )
        except ReviewRuntimeCancelled:
            return self._observation(
                request,
                ReviewMediaRuntimeState.CANCELLED_SAFE,
                reasons=("CANCELLED_BY_RUNTIME",),
            )
        except ReviewRuntimeDisconnected:
            return self._observation(
                request,
                ReviewMediaRuntimeState.UNKNOWN_AFTER_DISCONNECT,
                reasons=("RUNTIME_DISCONNECTED",),
                connected=False,
            )
        except (OSError, ProductError, ReviewRuntimeKnownFailure, ValueError):
            return self._observation(
                request,
                ReviewMediaRuntimeState.FAILED_KNOWN,
                reasons=("RUNTIME_FAILED",),
            )
        finally:
            if waveform_peaks is not None:
                for index in range(len(waveform_peaks)):
                    waveform_peaks[index] = 0
                waveform_peaks.clear()
            pcm_body = b""
            with self._state_lock:
                self._active_cancel = None


__all__ = [
    "AssetLookupPort",
    "MAX_AUDIO_CHANNELS",
    "MAX_DECODED_RANGE_BYTES",
    "MAX_SOURCE_WAV_BYTES",
    "RegistryBoundReviewMediaRuntimePort",
    "ReviewAudioPlaybackBackend",
    "ReviewRuntimeCancelled",
    "ReviewRuntimeDisconnected",
    "ReviewRuntimeKnownFailure",
    "WindowsWavePlaybackBackend",
]
