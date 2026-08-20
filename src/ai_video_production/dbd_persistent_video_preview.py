"""Persistent in-memory video preview pipeline for TASK-051 Human Acceptance.

The module keeps a single PyAV container/decoder alive inside one worker thread,
coalesces transport requests to the newest target frame, and returns bounded
in-memory grayscale previews suitable for Tk without per-frame subprocess or
disk I/O.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
import threading
from typing import Any, Callable, Mapping

from .dbd_video_transport import VideoTransportMetadata
from .dbd_training_diagnostics import DiagnosticLogger, get_diagnostic_logger


@dataclass(frozen=True, slots=True)
class PreviewGeometry:
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1:
            raise ValueError("preview geometry must be positive")


@dataclass(frozen=True, slots=True)
class PersistentPreviewFrame:
    source: str
    frame_index: int
    source_geometry: PreviewGeometry
    preview_geometry: PreviewGeometry
    pixels: bytes

    def __post_init__(self) -> None:
        if self.frame_index < 0:
            raise ValueError("frame_index must be non-negative")
        expected = self.preview_geometry.width * self.preview_geometry.height
        if len(self.pixels) != expected:
            raise ValueError("preview pixel payload length is invalid")

    def pgm_bytes(self) -> bytes:
        header = (
            f"P5\n{self.preview_geometry.width} "
            f"{self.preview_geometry.height}\n255\n"
        ).encode("ascii")
        return header + self.pixels

    def tk_photo_data(self) -> bytes:
        """Return binary PGM bytes for ``tk.PhotoImage(data=...)`` auto-detection.

        Real Tk accepts binary PGM bytes directly. Passing a base64 string while
        forcing ``format="PGM"`` is not portable and can fail with
        ``TclError: image format "PGM" is not supported``.
        """
        return self.pgm_bytes()


class PyAVPersistentFrameDecoder:
    """Single-source PyAV decoder with bounded recent-frame caching.

    The object is intentionally not thread-safe. ``PersistentPreviewWorker``
    owns it and guarantees all container operations remain on one worker thread.
    """

    def __init__(
        self,
        source: str | Path,
        metadata: VideoTransportMetadata,
        *,
        maximum_width: int = 960,
        maximum_height: int = 540,
        ring_size: int = 24,
    ) -> None:
        if maximum_width < 64 or maximum_height < 64:
            raise ValueError("preview bounds must be at least 64px")
        if ring_size < 2 or ring_size > 240:
            raise ValueError("ring_size must be 2..240")
        try:
            import av  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised on Windows HA
            raise RuntimeError(
                'PyAV is required for smooth Training Studio playback. '
                'Run: python -m pip install -e ".[windows-build]"'
            ) from exc

        self._av = av
        self.source = str(Path(source))
        self.metadata = metadata
        self.maximum_width = maximum_width
        self.maximum_height = maximum_height
        self.ring_size = ring_size
        self.container = av.open(self.source)
        streams = list(getattr(self.container.streams, "video", ()) or ())
        if not streams:
            self.container.close()
            raise ValueError("video source has no video stream")
        self.stream = streams[0]
        try:
            self.stream.thread_type = "AUTO"
        except Exception:
            pass
        source_width = int(getattr(self.stream.codec_context, "width", 0) or 0)
        source_height = int(getattr(self.stream.codec_context, "height", 0) or 0)
        if source_width < 1 or source_height < 1:
            self.container.close()
            raise ValueError("video stream geometry is unavailable")
        self.source_geometry = PreviewGeometry(source_width, source_height)
        # Fit the decoded preview to the actual viewport bounds.  Upscaling is
        # allowed for low-resolution sources because the Training Studio is an
        # inspection/annotation surface: leaving most of the viewport black makes
        # HUD and OCR work impractical.  The caller keeps the bounds capped.
        scale = min(
            maximum_width / source_width,
            maximum_height / source_height,
        )
        self.preview_geometry = PreviewGeometry(
            max(64, round(source_width * scale)),
            max(64, round(source_height * scale)),
        )
        time_base = getattr(self.stream, "time_base", None)
        start_time = getattr(self.stream, "start_time", None)
        self._time_base = None if time_base is None else float(time_base)
        self._start_seconds = (
            0.0
            if self._time_base is None or start_time is None
            else float(start_time) * self._time_base
        )
        self._iterator = iter(self.container.decode(self.stream))
        self._current_index: int | None = None
        self._cache: OrderedDict[int, PersistentPreviewFrame] = OrderedDict()
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._cache.clear()
        try:
            self.container.close()
        except Exception:
            pass

    def _remember(self, frame: PersistentPreviewFrame) -> PersistentPreviewFrame:
        self._cache[frame.frame_index] = frame
        self._cache.move_to_end(frame.frame_index)
        while len(self._cache) > self.ring_size:
            self._cache.popitem(last=False)
        return frame

    def _frame_seconds(self, frame) -> float | None:
        value = getattr(frame, "time", None)
        if value is not None:
            return max(0.0, float(value) - self._start_seconds)
        pts = getattr(frame, "pts", None)
        if pts is not None and self._time_base is not None:
            return max(0.0, float(pts) * self._time_base - self._start_seconds)
        return None

    def _estimate_index(self, frame) -> int:
        seconds = self._frame_seconds(frame)
        if seconds is not None:
            return min(
                self.metadata.last_frame,
                max(0, round(seconds * self.metadata.fps)),
            )
        if self._current_index is None:
            return 0
        return min(self.metadata.last_frame, self._current_index + 1)

    def _convert(self, frame, frame_index: int) -> PersistentPreviewFrame:
        converted = frame.reformat(
            width=self.preview_geometry.width,
            height=self.preview_geometry.height,
            format="gray",
        )
        plane = converted.planes[0]
        raw = bytes(plane)
        line_size = int(plane.line_size)
        width = self.preview_geometry.width
        height = self.preview_geometry.height
        if line_size == width:
            pixels = raw[: width * height]
        else:
            pixels = b"".join(
                raw[row * line_size : row * line_size + width]
                for row in range(height)
            )
        return PersistentPreviewFrame(
            source=self.source,
            frame_index=frame_index,
            source_geometry=self.source_geometry,
            preview_geometry=self.preview_geometry,
            pixels=pixels,
        )

    def _seek(self, target_index: int, *, backfill: bool) -> None:
        start_index = target_index
        if backfill:
            start_index = max(0, target_index - max(2, self.ring_size // 2))
        seconds = start_index / self.metadata.fps
        absolute_seconds = seconds + self._start_seconds
        if self._time_base is not None and self._time_base > 0:
            timestamp = max(0, int(absolute_seconds / self._time_base))
            self.container.seek(
                timestamp,
                stream=self.stream,
                backward=True,
                any_frame=False,
            )
        else:  # AV_TIME_BASE units when a stream time-base is unavailable.
            self.container.seek(
                max(0, int(absolute_seconds * 1_000_000)),
                backward=True,
                any_frame=False,
            )
        self._iterator = iter(self.container.decode(self.stream))
        self._current_index = None

    def get_frame(self, frame_index: int) -> PersistentPreviewFrame:
        if self._closed:
            raise RuntimeError("preview decoder is closed")
        target = min(max(0, int(frame_index)), self.metadata.last_frame)
        cached = self._cache.get(target)
        if cached is not None:
            self._cache.move_to_end(target)
            return cached

        needs_seek = self._current_index is None
        backfill = False
        if self._current_index is not None:
            if target < self._current_index:
                needs_seek = True
                backfill = True
            elif target - self._current_index > max(12, round(self.metadata.fps * 2)):
                needs_seek = True
        if needs_seek:
            self._seek(target, backfill=backfill)

        previous_decoded = None
        previous_index: int | None = None
        for decoded in self._iterator:
            index = self._estimate_index(decoded)
            if self._current_index is not None and index < self._current_index:
                continue
            self._current_index = index

            # When the wall-clock has advanced beyond the decoder, decode through
            # intermediate frames without converting every skipped frame into a
            # Tk preview. Keep only the immediate predecessor so a paused -1 frame
            # step remains instant, then convert the frame that catches the target.
            if index < target:
                previous_decoded = decoded
                previous_index = index
                continue
            if (
                previous_decoded is not None
                and previous_index == target - 1
                and previous_index not in self._cache
            ):
                self._remember(self._convert(previous_decoded, previous_index))
            return self._remember(self._convert(decoded, index))

        raise RuntimeError("video decoder reached end-of-stream before target frame")


@dataclass(frozen=True, slots=True)
class PreviewRequest:
    generation: int
    source: str
    frame_index: int
    metadata: VideoTransportMetadata
    callback: Callable[[PersistentPreviewFrame | None, Exception | None], None]
    diagnostic_context: Mapping[str, Any]


class PersistentPreviewWorker:
    """Latest-request-wins worker owning one persistent decoder/container."""

    def __init__(
        self,
        *,
        decoder_factory: Callable[[str, VideoTransportMetadata], object] | None = None,
        diagnostics: DiagnosticLogger | None = None,
    ) -> None:
        self._decoder_factory = decoder_factory or (
            lambda source, metadata: PyAVPersistentFrameDecoder(source, metadata)
        )
        self._diagnostics = diagnostics or get_diagnostic_logger()
        self._condition = threading.Condition()
        self._generation = 0
        self._pending: PreviewRequest | None = None
        self._closed = False
        self._decoder_reset_requested = False
        self._decoder = None
        self._decoder_source: str | None = None
        self._thread = threading.Thread(
            target=self._run,
            name="dbd-persistent-preview",
            daemon=True,
        )
        self._thread.start()

    @property
    def generation(self) -> int:
        with self._condition:
            return self._generation

    def request(
        self,
        *,
        source: str,
        frame_index: int,
        metadata: VideoTransportMetadata,
        callback: Callable[[PersistentPreviewFrame | None, Exception | None], None],
        diagnostic_context: Mapping[str, Any] | None = None,
    ) -> int:
        source_text = str(Path(source))
        with self._condition:
            if self._closed:
                raise RuntimeError("preview worker is closed")
            if self._decoder_source is not None and source_text != self._decoder_source:
                self._generation += 1
            request = PreviewRequest(
                generation=self._generation,
                source=source_text,
                frame_index=int(frame_index),
                metadata=metadata,
                callback=callback,
                diagnostic_context=dict(diagnostic_context or {}),
            )
            # Atomic latest-request replacement prevents unbounded playback lag.
            replaced = self._pending is not None
            self._pending = request
            self._condition.notify_all()
            if replaced:
                self._diagnostics.emit(
                    "FRAME_REQUEST_COALESCED",
                    frame_index=request.frame_index,
                    source=request.source,
                    **request.diagnostic_context,
                )
            return request.generation

    def invalidate(self) -> None:
        with self._condition:
            self._generation += 1
            self._pending = None
            # Decoder/container ownership stays on the worker thread.  Mark it
            # for replacement on the next request rather than closing it here.
            self._decoder_reset_requested = True
            self._condition.notify_all()

    def close(self, *, join_timeout: float = 1.0) -> None:
        with self._condition:
            if self._closed:
                return
            self._closed = True
            self._generation += 1
            self._pending = None
            self._condition.notify_all()
        self._thread.join(timeout=max(0.0, join_timeout))

    def _replace_decoder(self, request: PreviewRequest) -> None:
        if self._decoder is not None:
            try:
                self._decoder.close()
            except Exception as exc:
                self._diagnostics.exception(
                    "PYAV_DECODER_CLOSE_FAILED",
                    exc,
                    source=self._decoder_source or request.source,
                    **request.diagnostic_context,
                )
        self._diagnostics.emit(
            "PYAV_DECODER_OPEN_STARTED",
            source=request.source,
            **request.diagnostic_context,
        )
        self._decoder = self._decoder_factory(request.source, request.metadata)
        self._decoder_source = request.source
        self._diagnostics.emit(
            "PYAV_DECODER_OPENED",
            source=request.source,
            fps=request.metadata.fps,
            total_frames=request.metadata.total_frames,
            **request.diagnostic_context,
        )

    def _run(self) -> None:
        try:
            while True:
                with self._condition:
                    while self._pending is None and not self._closed:
                        self._condition.wait()
                    if self._closed:
                        return
                    request = self._pending
                    self._pending = None
                    reset_decoder = self._decoder_reset_requested
                    self._decoder_reset_requested = False
                assert request is not None
                try:
                    if reset_decoder or self._decoder is None or self._decoder_source != request.source:
                        self._replace_decoder(request)
                    self._diagnostics.emit(
                        "FRAME_DECODE_STARTED",
                        source=request.source,
                        frame_index=request.frame_index,
                        **request.diagnostic_context,
                    )
                    frame = self._decoder.get_frame(request.frame_index)
                    error = None
                    self._diagnostics.emit(
                        "FRAME_DECODED",
                        source=request.source,
                        requested_frame=request.frame_index,
                        decoded_frame=frame.frame_index,
                        **request.diagnostic_context,
                    )
                except Exception as exc:
                    frame = None
                    error = exc
                    self._diagnostics.exception(
                        "FRAME_DECODE_FAILED",
                        exc,
                        source=request.source,
                        frame_index=request.frame_index,
                        **request.diagnostic_context,
                    )
                    if self._decoder is not None:
                        try:
                            self._decoder.close()
                        except Exception as close_exc:
                            self._diagnostics.exception(
                                "PYAV_DECODER_CLOSE_FAILED",
                                close_exc,
                                source=request.source,
                                **request.diagnostic_context,
                            )
                    self._decoder = None
                    self._decoder_source = None

                with self._condition:
                    stale = self._closed or request.generation != self._generation
                if not stale:
                    try:
                        # Callback ownership is limited to Python mailbox delivery.
                        # Tk APIs are forbidden from the decoder thread.
                        request.callback(frame, error)
                    except Exception as exc:
                        self._diagnostics.exception(
                            "FRAME_CALLBACK_FAILED",
                            exc,
                            source=request.source,
                            frame_index=request.frame_index,
                            **request.diagnostic_context,
                        )
                else:
                    self._diagnostics.emit(
                        "FRAME_RESULT_STALE",
                        source=request.source,
                        frame_index=request.frame_index,
                        **request.diagnostic_context,
                    )
        finally:
            if self._decoder is not None:
                try:
                    self._decoder.close()
                except Exception as exc:
                    self._diagnostics.exception(
                        "PYAV_DECODER_CLOSE_FAILED",
                        exc,
                        source=self._decoder_source or "",
                    )
            self._decoder = None
            self._decoder_source = None


__all__ = [
    "PersistentPreviewFrame",
    "PersistentPreviewWorker",
    "PreviewGeometry",
    "PyAVPersistentFrameDecoder",
]
