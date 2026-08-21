"""Shared Training Studio video preview/transport composition.

All user-facing DbD Training Studio surfaces use this module for preview playback.
The session owns the persistent PyAV worker, source/metadata resolution, stale-source
protection, UI-thread delivery and lifecycle cleanup.  Standard tabs use the
split preview/transport widget; HUD calibration reuses the same session while
painting its custom ROI canvas.

Exact teacher-data extraction remains outside this module.  Crop/OCR/ROI
registration continues to use the existing exact-frame services so a display
preview can never silently become canonical training evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
from typing import Callable

from .dbd_persistent_video_preview import (
    PersistentPreviewFrame, PersistentPreviewWorker, PyAVPersistentFrameDecoder,
)
from .dbd_training_audio import FfplayAudioController
from .dbd_video_transport import (
    TkVideoTransportBar, VideoTransportEvent, VideoTransportMetadata,
    VideoTransportState, probe_video_metadata,
)
from .dbd_training_diagnostics import DiagnosticLogger, get_diagnostic_logger


@dataclass(frozen=True, slots=True)
class _UiFrameDelivery:
    source: str
    frame: PersistentPreviewFrame | None
    error: Exception | None


class _LatestFrameMailbox:
    """One-slot thread-safe mailbox; producer never calls Tk APIs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: _UiFrameDelivery | None = None

    def put(self, item: _UiFrameDelivery) -> bool:
        with self._lock:
            replaced = self._latest is not None
            self._latest = item
            return replaced

    def take_latest(self) -> _UiFrameDelivery | None:
        with self._lock:
            item = self._latest
            self._latest = None
            return item

    def clear(self) -> None:
        with self._lock:
            self._latest = None


class TkTrainingMediaSession:
    """Canonical persistent preview session shared by every Training Studio tab.

    One session is intentionally created per visible video surface.  The code and
    behavior are shared, while decoder state is not leaked across tabs or source
    fields.  This avoids cross-tab ownership surprises and still removes the old
    per-tab FFmpeg preview implementations.
    """

    def __init__(
        self,
        *,
        root,
        source_getter: Callable[[], str],
        frame_getter: Callable[[], int],
        frame_setter: Callable[[int], None],
        on_frame: Callable[[PersistentPreviewFrame], None],
        status_setter: Callable[[str], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
        ffprobe_executable: str = "ffprobe",
        maximum_preview_fps: float = 30.0,
        worker: PersistentPreviewWorker | None = None,
        metadata_getter: Callable[[str], VideoTransportMetadata] | None = None,
        diagnostics: DiagnosticLogger | None = None,
        diagnostic_feature: str = "TRAINING_VIDEO",
        player_id: str = "shared-video",
        ui_poll_interval_ms: int = 16,
        audio_controller: FfplayAudioController | None = None,
        ffplay_executable: str | None = None,
        preview_maximum_width: int = 1280,
        preview_maximum_height: int = 720,
    ) -> None:
        self.root = root
        self.source_getter = source_getter
        self.frame_getter = frame_getter
        self.frame_setter = frame_setter
        self.on_frame = on_frame
        self.status_setter = status_setter
        self.on_error = on_error
        self.ffprobe_executable = ffprobe_executable
        self.maximum_preview_fps = float(maximum_preview_fps)
        if self.maximum_preview_fps <= 0:
            raise ValueError("maximum_preview_fps must be positive")
        self.diagnostics = diagnostics or get_diagnostic_logger()
        self.diagnostic_feature = str(diagnostic_feature)
        self.player_id = str(player_id)
        self.ui_poll_interval_ms = max(4, int(ui_poll_interval_ms))
        self.preview_maximum_width = max(320, int(preview_maximum_width))
        self.preview_maximum_height = max(180, int(preview_maximum_height))
        self.worker = worker or PersistentPreviewWorker(
            diagnostics=self.diagnostics,
            decoder_factory=lambda source, metadata: PyAVPersistentFrameDecoder(
                source, metadata, maximum_width=self.preview_maximum_width,
                maximum_height=self.preview_maximum_height,
            ),
        )
        self.audio = audio_controller or FfplayAudioController(
            executable=ffplay_executable, diagnostics=self.diagnostics,
            diagnostic_feature=self.diagnostic_feature, player_id=self.player_id,
        )
        self._volume_percent = 80
        self._muted = False
        self._mailbox = _LatestFrameMailbox()
        self._ui_poll_after_id = None
        self._metadata_getter = metadata_getter
        self._metadata_source: str | None = None
        self._metadata: VideoTransportMetadata | None = None
        self.transport: TkVideoTransportBar | None = None
        self._closed = False
        try:
            root.bind("<Destroy>", self._on_destroy, add="+")
        except Exception as exc:
            # Unit-test/fake roots and non-Tk hosts may omit bind().
            self.diagnostics.exception(
                "TK_DESTROY_BIND_FAILED", exc, feature=self.diagnostic_feature, player_id=self.player_id
            )
        # Only a real Tk root owns the self-rescheduling UI poll. Test/fake roots
        # drain the mailbox explicitly, which avoids recursive fake after() calls.
        if hasattr(root, "tk"):
            self._schedule_ui_poll()

    def _current_source(self) -> str:
        return self.source_getter().strip()

    def _metadata_for(self, source: str) -> VideoTransportMetadata:
        transport = self.transport
        if (
            transport is not None
            and transport.model is not None
            and transport.source_identity == source
        ):
            metadata = transport.model.metadata
            self._metadata_source = source
            self._metadata = metadata
            return metadata
        if self._metadata_source == source and self._metadata is not None:
            return self._metadata
        if self._metadata_getter is not None:
            metadata = self._metadata_getter(source)
        else:
            metadata = probe_video_metadata(
                source,
                ffprobe_executable=self.ffprobe_executable,
            )
        self._metadata_source = source
        self._metadata = metadata
        return metadata

    def create_transport(self, parent, *, title: str = "動画操作") -> TkVideoTransportBar:
        if self.transport is not None:
            raise RuntimeError("video transport is already attached")
        self.transport = TkVideoTransportBar(
            parent,
            root=self.root,
            source_getter=self.source_getter,
            frame_getter=self.frame_getter,
            frame_setter=self.frame_setter,
            render_frame=self.request_frame,
            ffprobe_executable=self.ffprobe_executable,
            title=title,
            maximum_preview_fps=self.maximum_preview_fps,
            diagnostics=self.diagnostics,
            diagnostic_feature=self.diagnostic_feature,
            player_id=self.player_id,
            state_listener=self._on_transport_state,
        )
        return self.transport

    def _on_transport_state(self, event: VideoTransportEvent) -> None:
        if self._closed:
            return
        source = self._current_source()
        if event.state is VideoTransportState.PLAYING and source:
            self.audio.set_volume(self._volume_percent)
            self.audio.set_muted(self._muted)
            started = self.audio.play(source, start_seconds=event.position_seconds)
            if not started and self.status_setter is not None:
                self.status_setter(
                    "音声を再生できません。ffplay をFFmpegと一緒にインストールするか "
                    "BVP_FFPLAY で場所を指定してください。"
                )
        else:
            # Frame stepping, stop, rewind and fast-forward are intentionally
            # muted. Normal 1x play restarts source audio at the exact position.
            self.audio.stop()

    def set_volume(self, percent: int) -> None:
        self._volume_percent = min(100, max(0, int(percent)))
        self.audio.set_volume(self._volume_percent)
        transport = self.transport
        if transport is not None and transport.model is not None and transport.model.state is VideoTransportState.PLAYING:
            source = self._current_source()
            if source:
                self.audio.restart(source, start_seconds=transport.model.position_seconds())

    def set_muted(self, muted: bool) -> None:
        self._muted = bool(muted)
        self.audio.set_muted(self._muted)
        transport = self.transport
        if transport is not None and transport.model is not None and transport.model.state is VideoTransportState.PLAYING:
            source = self._current_source()
            if source:
                self.audio.restart(source, start_seconds=transport.model.position_seconds())

    @property
    def audio_available(self) -> bool:
        return self.audio.available

    def set_preview_bounds(self, width: int, height: int, *, refresh: bool = True) -> bool:
        """Rebind decoder output to the real visible viewport.

        Returns ``True`` only when the effective bounds changed enough to require
        a decoder reopen.  The worker owns decoder close/open operations.
        """
        width = min(1920, max(320, int(width)))
        height = min(1080, max(180, int(height)))
        if (
            abs(width - self.preview_maximum_width) < 24
            and abs(height - self.preview_maximum_height) < 24
        ):
            return False
        self.preview_maximum_width = width
        self.preview_maximum_height = height
        self.diagnostics.emit(
            "VIDEO_PREVIEW_BOUNDS_CHANGED",
            feature=self.diagnostic_feature, player_id=self.player_id,
            width=width, height=height,
        )
        self.worker.invalidate()
        if refresh and self._current_source():
            self.request_current_frame()
        return True

    def request_current_frame(self) -> None:
        self.request_frame(self.frame_getter())

    def request_frame(self, frame_index: int) -> None:
        if self._closed:
            return
        source = self._current_source()
        if not source:
            if self.status_setter is not None:
                self.status_setter("動画を選択してください。")
            return
        try:
            metadata = self._metadata_for(source)
        except Exception as exc:
            self._deliver_error(exc)
            return

        requested_source = str(Path(source))
        context = {
            "feature": self.diagnostic_feature,
            "player_id": self.player_id,
        }
        self.diagnostics.emit(
            "FRAME_REQUESTED",
            source=requested_source,
            frame_index=int(frame_index),
            **context,
        )

        def delivered(frame, error) -> None:
            # Decoder thread boundary: Python synchronization only. Never call Tk.
            replaced = self._mailbox.put(
                _UiFrameDelivery(requested_source, frame, error)
            )
            self.diagnostics.emit(
                "FRAME_MAILBOX_PUT",
                source=requested_source,
                frame_index=(frame.frame_index if frame is not None else int(frame_index)),
                replaced_previous=replaced,
                **context,
            )
            if replaced:
                self.diagnostics.emit(
                    "FRAME_MAILBOX_DROP",
                    source=requested_source,
                    reason="latest-frame-wins",
                    **context,
                )

        try:
            self.worker.request(
                source=requested_source,
                frame_index=int(frame_index),
                metadata=metadata,
                callback=delivered,
                diagnostic_context=context,
            )
        except Exception as exc:
            self.diagnostics.exception(
                "FRAME_REQUEST_FAILED",
                exc,
                source=requested_source,
                frame_index=int(frame_index),
                **context,
            )
            self._deliver_error(exc)

    def _schedule_ui_poll(self) -> None:
        if self._closed or self._ui_poll_after_id is not None:
            return
        try:
            self._ui_poll_after_id = self.root.after(
                self.ui_poll_interval_ms, self._poll_mailbox
            )
        except Exception as exc:
            self.diagnostics.exception(
                "TK_MAILBOX_SCHEDULE_FAILED",
                exc,
                feature=self.diagnostic_feature,
                player_id=self.player_id,
            )

    def _poll_mailbox(self) -> None:
        self._ui_poll_after_id = None
        if self._closed:
            return
        self._drain_mailbox_once()
        self._schedule_ui_poll()

    def _drain_mailbox_once(self) -> bool:
        """Drain at most the newest delivery. Must run on the Tk/UI thread."""
        item = self._mailbox.take_latest()
        if item is None:
            return False
        context = {
            "feature": self.diagnostic_feature,
            "player_id": self.player_id,
        }
        self.diagnostics.emit(
            "FRAME_MAILBOX_GET",
            source=item.source,
            frame_index=(item.frame.frame_index if item.frame is not None else None),
            **context,
        )
        current = self._current_source()
        if not current or Path(current) != Path(item.source):
            self.diagnostics.emit(
                "FRAME_UI_STALE_SOURCE",
                source=item.source,
                current_source=current,
                **context,
            )
            return True
        if item.error is not None:
            self._deliver_error(item.error)
            return True
        if item.frame is None:
            self.diagnostics.emit("FRAME_UI_EMPTY", level="WARNING", **context)
            return True
        try:
            self.diagnostics.emit(
                "FRAME_UI_CALLBACK_STARTED",
                source=item.source,
                frame_index=item.frame.frame_index,
                **context,
            )
            self.on_frame(item.frame)
            self.diagnostics.emit(
                "FRAME_UI_CALLBACK_COMPLETED",
                source=item.source,
                frame_index=item.frame.frame_index,
                **context,
            )
        except Exception as exc:
            self.diagnostics.exception(
                "FRAME_UI_CALLBACK_FAILED",
                exc,
                source=item.source,
                frame_index=item.frame.frame_index,
                **context,
            )
            self._deliver_error(exc)
        return True

    def _deliver_error(self, error: Exception) -> None:
        self.diagnostics.exception(
            "VIDEO_PREVIEW_ERROR",
            error,
            feature=self.diagnostic_feature,
            player_id=self.player_id,
        )
        if self.on_error is not None:
            try:
                self.on_error(error)
            except Exception as callback_error:
                self.diagnostics.exception(
                    "VIDEO_PREVIEW_ERROR_HANDLER_FAILED",
                    callback_error,
                    feature=self.diagnostic_feature,
                    player_id=self.player_id,
                )
            return
        if self.status_setter is not None:
            try:
                self.status_setter(
                    f"動画プレビュー: {type(error).__name__}: {error}"
                )
            except Exception as status_error:
                self.diagnostics.exception(
                    "VIDEO_PREVIEW_STATUS_FAILED",
                    status_error,
                    feature=self.diagnostic_feature,
                    player_id=self.player_id,
                )

    def invalidate(self) -> None:
        self._metadata_source = None
        self._metadata = None
        self._mailbox.clear()
        try:
            self.worker.invalidate()
        except Exception as exc:
            self.diagnostics.exception(
                "VIDEO_PREVIEW_INVALIDATE_FAILED",
                exc,
                feature=self.diagnostic_feature,
                player_id=self.player_id,
            )

    def close(self, *, join_timeout: float = 0.25) -> None:
        if self._closed:
            return
        self._closed = True
        if self._ui_poll_after_id is not None:
            try:
                self.root.after_cancel(self._ui_poll_after_id)
            except Exception as exc:
                self.diagnostics.exception(
                    "TK_MAILBOX_CANCEL_FAILED",
                    exc,
                    feature=self.diagnostic_feature,
                    player_id=self.player_id,
                )
            self._ui_poll_after_id = None
        self._mailbox.clear()
        transport = self.transport
        if transport is not None:
            try:
                transport.stop()
            except Exception as exc:
                self.diagnostics.exception(
                    "VIDEO_TRANSPORT_STOP_FAILED",
                    exc,
                    feature=self.diagnostic_feature,
                    player_id=self.player_id,
                )
        self.audio.close()
        self.worker.close(join_timeout=join_timeout)

    def _on_destroy(self, event=None) -> None:
        if event is not None and getattr(event, "widget", None) is not self.root:
            return
        self.close()


class TkTrainingMediaPlayer:
    """Standard split preview + transport UI backed by the canonical session."""

    def __init__(
        self,
        parent,
        *,
        root,
        source_getter: Callable[[], str],
        frame_getter: Callable[[], int],
        frame_setter: Callable[[int], None],
        status_setter: Callable[[str], None] | None = None,
        preview_title: str = "動画プレビュー",
        transport_title: str = "動画操作",
        empty_text: str = "動画を選択してください。",
        ffprobe_executable: str = "ffprobe",
        maximum_preview_fps: float = 30.0,
        worker: PersistentPreviewWorker | None = None,
        metadata_getter: Callable[[str], VideoTransportMetadata] | None = None,
        diagnostics: DiagnosticLogger | None = None,
        diagnostic_feature: str = "TRAINING_VIDEO",
        player_id: str = "shared-video",
        ffplay_executable: str | None = None,
        show_audio_controls: bool = True,
        control_header_builder: Callable[[object], None] | None = None,
        preview_maximum_width: int = 1280,
        preview_maximum_height: int = 720,
    ) -> None:
        import tkinter as tk
        from tkinter import ttk

        self._tk = tk
        self.root = root
        self.photo = None
        self._raw_photo = None
        self._fit_after_id = None
        self._last_frame: PersistentPreviewFrame | None = None
        self.frame = ttk.Frame(parent)
        self.frame.columnconfigure(0, weight=2)
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(0, weight=1)

        preview_box = ttk.LabelFrame(self.frame, text=preview_title, padding=6)
        preview_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        preview_box.columnconfigure(0, weight=1)
        preview_box.rowconfigure(0, weight=1)
        # A plain Tk label gives us a deterministic black letterbox. The image
        # is always subsampled to fit; the source is never cropped.
        self.preview_label = tk.Label(
            preview_box, text=empty_text, anchor="center",
            background="black", foreground="white",
        )
        self.preview_label.grid(row=0, column=0, sticky="nsew")
        self.preview_label.bind("<Configure>", self._on_preview_configure, add="+")

        self.controls = ttk.Frame(self.frame)
        self.controls.grid(row=0, column=1, sticky="new")
        self.controls.columnconfigure(0, weight=1)
        next_row = 0
        if control_header_builder is not None:
            header = ttk.Frame(self.controls)
            header.grid(row=next_row, column=0, sticky="ew", pady=(0, 6))
            header.columnconfigure(0, weight=1)
            control_header_builder(header)
            next_row += 1

        self.session = TkTrainingMediaSession(
            root=root, source_getter=source_getter, frame_getter=frame_getter,
            frame_setter=frame_setter, on_frame=self._paint_frame,
            status_setter=status_setter, ffprobe_executable=ffprobe_executable,
            maximum_preview_fps=maximum_preview_fps, worker=worker,
            metadata_getter=metadata_getter, diagnostics=diagnostics,
            diagnostic_feature=diagnostic_feature, player_id=player_id,
            ffplay_executable=ffplay_executable,
            preview_maximum_width=preview_maximum_width,
            preview_maximum_height=preview_maximum_height,
        )
        self.transport = self.session.create_transport(self.controls, title=transport_title)
        self.transport.grid(row=next_row, column=0, sticky="ew")
        next_row += 1

        self.volume_var = tk.IntVar(value=80)
        self.mute_var = tk.BooleanVar(value=False)
        if show_audio_controls:
            audio = ttk.LabelFrame(self.controls, text="音声", padding=6)
            audio.grid(row=next_row, column=0, sticky="ew", pady=(6, 0))
            audio.columnconfigure(1, weight=1)
            ttk.Label(audio, text="🔊").grid(row=0, column=0, padx=(0, 4))
            scale = ttk.Scale(
                audio, from_=0, to=100, orient="horizontal",
                variable=self.volume_var,
                command=lambda _value: self._preview_volume_label(),
            )
            scale.grid(row=0, column=1, sticky="ew")
            scale.bind("<ButtonRelease-1>", lambda _event: self._commit_volume())
            self.volume_text = ttk.Label(audio, text="80%", width=5, anchor="e")
            self.volume_text.grid(row=0, column=2, padx=4)
            ttk.Checkbutton(
                audio, text="ミュート", variable=self.mute_var,
                command=self._commit_mute,
            ).grid(row=0, column=3, padx=(6, 0))
            availability = "音声出力: 使用可能" if self.session.audio_available else "音声出力: ffplay が見つかりません"
            ttk.Label(audio, text=availability).grid(
                row=1, column=0, columnspan=4, sticky="w", pady=(3, 0)
            )

    def _fit_photo(self, raw_photo):
        width = max(1, int(self.preview_label.winfo_width() or 1))
        height = max(1, int(self.preview_label.winfo_height() or 1))
        iw, ih = raw_photo.width(), raw_photo.height()
        if width <= 1 or height <= 1:
            return raw_photo
        factor = max(1, int(max((iw + width - 1) // width, (ih + height - 1) // height)))
        return raw_photo if factor == 1 else raw_photo.subsample(factor, factor)

    def _paint_frame(self, frame: PersistentPreviewFrame) -> None:
        context = {
            "feature": self.session.diagnostic_feature, "player_id": self.session.player_id,
            "frame_index": frame.frame_index, "source": frame.source,
        }
        self.session.diagnostics.emit("TK_IMAGE_CREATE_STARTED", **context)
        try:
            raw_photo = self._tk.PhotoImage(data=frame.tk_photo_data())
            photo = self._fit_photo(raw_photo)
        except Exception as exc:
            self.session.diagnostics.exception("TK_IMAGE_CREATE_FAILED", exc, **context)
            raise
        self._raw_photo = raw_photo
        self.photo = photo
        self._last_frame = frame
        self.session.diagnostics.emit(
            "TK_IMAGE_CREATED", image_width=photo.width(), image_height=photo.height(), **context
        )
        try:
            self.preview_label.configure(image=photo, text="")
        except Exception as exc:
            self.session.diagnostics.exception("TK_WIDGET_UPDATE_FAILED", exc, **context)
            raise
        self.session.diagnostics.emit(
            "TK_FRAME_PAINTED", fit_mode="FIT_TO_VIEW", **context
        )

    def _on_preview_configure(self, _event=None) -> None:
        # Resize storms must not reopen PyAV on every pixel.  Keep the current
        # frame visible, then re-decode once against the settled viewport.
        raw = self._raw_photo
        if raw is not None:
            try:
                self.photo = self._fit_photo(raw)
                self.preview_label.configure(image=self.photo, text="")
            except Exception as exc:
                self.session.diagnostics.exception(
                    "TK_FIT_TO_VIEW_FAILED", exc, feature=self.session.diagnostic_feature,
                    player_id=self.session.player_id,
                )
        if self._fit_after_id is not None:
            try:
                self.root.after_cancel(self._fit_after_id)
            except Exception:
                pass
        try:
            self._fit_after_id = self.root.after(120, self._apply_viewport_bounds)
        except Exception as exc:
            self.session.diagnostics.exception(
                "TK_FIT_SCHEDULE_FAILED", exc, feature=self.session.diagnostic_feature,
                player_id=self.session.player_id,
            )

    def _apply_viewport_bounds(self) -> None:
        self._fit_after_id = None
        try:
            width = max(320, int(self.preview_label.winfo_width()))
            height = max(180, int(self.preview_label.winfo_height()))
            self.session.set_preview_bounds(width, height, refresh=True)
        except Exception as exc:
            self.session.diagnostics.exception(
                "VIDEO_PREVIEW_BOUNDS_APPLY_FAILED", exc,
                feature=self.session.diagnostic_feature, player_id=self.session.player_id,
            )

    def _preview_volume_label(self) -> None:
        if hasattr(self, "volume_text"):
            self.volume_text.configure(text=f"{int(round(self.volume_var.get()))}%")

    def _commit_volume(self) -> None:
        self._preview_volume_label()
        self.session.set_volume(int(round(self.volume_var.get())))

    def _commit_mute(self) -> None:
        self.session.set_muted(bool(self.mute_var.get()))

    def grid(self, **kwargs) -> None:
        self.frame.grid(**kwargs)

    def pack(self, **kwargs) -> None:
        self.frame.pack(**kwargs)

    def request_current_frame(self) -> None:
        self.session.request_current_frame()

    def close(self) -> None:
        self.session.close()


TkTrainingVideoPlayer = TkTrainingMediaPlayer
TkTrainingVideoSession = TkTrainingMediaSession

__all__ = [
    "TkTrainingMediaPlayer", "TkTrainingMediaSession",
    "TkTrainingVideoPlayer", "TkTrainingVideoSession",
]
