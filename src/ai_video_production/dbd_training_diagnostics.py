"""Opt-in diagnostics for BAI DbD Training Studio.

Diagnostics are enabled only when ``BAI_DIAGNOSTICS.ENABLE`` exists beside the
packaged executable.  When enabled, structured JSONL is written asynchronously
under ``diagnostics/`` beside the executable so playback/GUI failures can be
reported without a debug build or source-code edits.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import queue
import sys
import threading
import traceback
from typing import Any, Mapping

MARKER_NAME = "BAI_DIAGNOSTICS.ENABLE"
DIAGNOSTICS_DIR_NAME = "diagnostics"
LATEST_LOG_NAME = "latest.jsonl"
MAX_LOG_BYTES = 20 * 1024 * 1024
MAX_ROTATIONS = 5
_QUEUE_LIMIT = 4096
_REDACTED_KEYS = (
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "cookie",
    "api_key",
    "apikey",
    "credential",
)


def runtime_application_dir() -> Path:
    """Return the directory that owns the executable in packaged mode."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd().resolve()


def _path_identity(value: str | Path) -> str:
    text = str(value)
    try:
        resolved = str(Path(text).expanduser().resolve())
    except Exception:
        resolved = text
    digest = hashlib.sha256(resolved.encode("utf-8", errors="replace")).hexdigest()[:16]
    name = Path(text).name or "<path>"
    return f"{name}|sha256:{digest}"


def _sanitize(key: str, value: Any) -> Any:
    lowered = key.lower()
    if any(token in lowered for token in _REDACTED_KEYS):
        return "[REDACTED]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Path):
        return _path_identity(value)
    if isinstance(value, str):
        if lowered in {"path", "source", "video", "video_path", "source_path"} or lowered.endswith("_path"):
            return _path_identity(value)
        return value[:2000]
    if isinstance(value, Mapping):
        return {str(k): _sanitize(str(k), v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(key, item) for item in value[:100]]
    return repr(value)[:2000]


@dataclass(frozen=True, slots=True)
class DiagnosticState:
    enabled: bool
    marker_path: Path
    directory: Path
    latest_path: Path


class DiagnosticLogger:
    """Bounded non-blocking JSONL diagnostics writer."""

    def __init__(
        self,
        *,
        application_dir: str | Path | None = None,
        max_log_bytes: int = MAX_LOG_BYTES,
        max_rotations: int = MAX_ROTATIONS,
        queue_limit: int = _QUEUE_LIMIT,
    ) -> None:
        base = Path(application_dir) if application_dir is not None else runtime_application_dir()
        base = base.resolve()
        marker = base / MARKER_NAME
        directory = base / DIAGNOSTICS_DIR_NAME
        latest = directory / LATEST_LOG_NAME
        self.state = DiagnosticState(marker.is_file(), marker, directory, latest)
        self.max_log_bytes = max(1024, int(max_log_bytes))
        self.max_rotations = max(1, int(max_rotations))
        self._queue: queue.Queue[dict[str, Any] | None] = queue.Queue(maxsize=max(16, int(queue_limit)))
        self._closed = False
        self._drop_count = 0
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        if self.state.enabled:
            directory.mkdir(parents=True, exist_ok=True)
            self._rotate_startup()
            self._thread = threading.Thread(
                target=self._writer_loop,
                name="dbd-diagnostics-writer",
                daemon=True,
            )
            self._thread.start()
            self.emit(
                "DIAGNOSTICS_ENABLED",
                marker=MARKER_NAME,
                log_name=LATEST_LOG_NAME,
                max_log_bytes=self.max_log_bytes,
                max_rotations=self.max_rotations,
            )

    @property
    def enabled(self) -> bool:
        return self.state.enabled

    @property
    def latest_path(self) -> Path:
        return self.state.latest_path

    def _rotate_startup(self) -> None:
        latest = self.state.latest_path
        if not latest.exists() or latest.stat().st_size == 0:
            return
        stale = latest.with_name(f"latest.{self.max_rotations}.jsonl")
        stale.unlink(missing_ok=True)
        for index in range(self.max_rotations - 1, 0, -1):
            source = latest.with_name(f"latest.{index}.jsonl")
            target = latest.with_name(f"latest.{index + 1}.jsonl")
            if source.exists():
                source.replace(target)
        if latest.exists():
            latest.replace(latest.with_name("latest.1.jsonl"))

    def _rotate_size(self) -> None:
        latest = self.state.latest_path
        if not latest.exists() or latest.stat().st_size < self.max_log_bytes:
            return
        stale = latest.with_name(f"latest.{self.max_rotations}.jsonl")
        stale.unlink(missing_ok=True)
        for index in range(self.max_rotations - 1, 0, -1):
            source = latest.with_name(f"latest.{index}.jsonl")
            target = latest.with_name(f"latest.{index + 1}.jsonl")
            if source.exists():
                source.replace(target)
        latest.replace(latest.with_name("latest.1.jsonl"))

    def emit(self, event: str, *, level: str = "INFO", **fields: Any) -> None:
        if not self.enabled or self._closed:
            return
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds"),
            "level": str(level).upper(),
            "event": str(event),
            "thread": threading.current_thread().name,
        }
        payload.update({str(k): _sanitize(str(k), v) for k, v in fields.items()})
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            with self._lock:
                self._drop_count += 1

    def exception(self, event: str, exc: BaseException, **fields: Any) -> None:
        self.emit(
            event,
            level="ERROR",
            exception_type=type(exc).__name__,
            message=str(exc),
            traceback="".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-12000:],
            **fields,
        )

    def _writer_loop(self) -> None:
        latest = self.state.latest_path
        while True:
            item = self._queue.get()
            if item is None:
                return
            with self._lock:
                dropped = self._drop_count
                self._drop_count = 0
            if dropped:
                drop_record = {
                    "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds"),
                    "level": "WARNING",
                    "event": "DIAGNOSTIC_EVENTS_DROPPED",
                    "thread": threading.current_thread().name,
                    "count": dropped,
                }
                self._write_record(latest, drop_record)
            self._write_record(latest, item)

    def _write_record(self, latest: Path, record: dict[str, Any]) -> None:
        try:
            self._rotate_size()
            encoded = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
            with latest.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded)
        except Exception:
            # Diagnostics must never break the Product's primary function.
            return

    def close(self, *, join_timeout: float = 0.5) -> None:
        if not self.enabled or self._closed:
            return
        self.emit("DIAGNOSTICS_CLOSING")
        self._closed = True
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(None)
            except queue.Full:
                return
        if self._thread is not None:
            self._thread.join(timeout=max(0.0, join_timeout))


_default_logger: DiagnosticLogger | None = None
_default_lock = threading.Lock()


def get_diagnostic_logger() -> DiagnosticLogger:
    global _default_logger
    if _default_logger is not None:
        return _default_logger
    with _default_lock:
        if _default_logger is None:
            _default_logger = DiagnosticLogger()
    return _default_logger


def reset_diagnostic_logger_for_tests() -> None:
    global _default_logger
    with _default_lock:
        if _default_logger is not None:
            _default_logger.close()
        _default_logger = None


__all__ = [
    "DIAGNOSTICS_DIR_NAME",
    "LATEST_LOG_NAME",
    "MARKER_NAME",
    "DiagnosticLogger",
    "DiagnosticState",
    "get_diagnostic_logger",
    "reset_diagnostic_logger_for_tests",
    "runtime_application_dir",
]
