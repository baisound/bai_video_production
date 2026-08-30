"""Privacy-safe, bounded, cross-process diagnostics for TASK-066."""

from __future__ import annotations

from collections import deque
from contextlib import AbstractContextManager
from dataclasses import dataclass, replace
from enum import Enum
import json
import os
from pathlib import Path
import re
import shutil
import stat
import threading
import time
from typing import Any, Callable

from .atomic import AtomicJsonWriter
from .desktop_install_layout import DesktopInstallLayout
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso


MAX_RECORD_BYTES = 16 * 1024
MAX_ACTIVE_FILE_BYTES = 4 * 1024 * 1024
RETAINED_GENERATIONS = 4
SHARED_DIRECTORY_CAP_BYTES = 32 * 1024 * 1024
RETENTION_SECONDS = 14 * 24 * 60 * 60
PROCESS_RATE_PER_SECOND = 2
PROCESS_BURST = 20
GLOBAL_RATE_PER_SECOND = 10
GLOBAL_BURST = 50
DEDUPE_WINDOW_SECONDS = 60
MAX_QUEUE_RECORDS = 512
MAX_QUEUE_BYTES = 4 * 1024 * 1024
WRITER_LOCK_TIMEOUT_SECONDS = 2.0
CLEANUP_INTERVAL_SECONDS = 15 * 60
MIN_FREE_BYTES = 512 * 1024 * 1024
MIN_FREE_RATIO = 0.05

_FAMILY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,95}$")
_OPAQUE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+){0,3}(?:[-+][0-9A-Za-z.-]+)?$")
_CLOSED_RE = re.compile(r"^(?P<family>[a-z0-9][a-z0-9._-]{1,63})\.(?P<sequence>[0-9]{20})\.closed\.jsonl$")


class DiagnosticsError(ValueError):
    """A diagnostic request violates the bounded public contract."""


class DiagnosticSeverity(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class DiagnosticWriteStatus(str, Enum):
    WRITTEN = "WRITTEN"
    AGGREGATED = "AGGREGATED"
    QUEUED = "QUEUED"
    DROPPED_RATE_LIMIT = "DROPPED_RATE_LIMIT"
    DROPPED_QUEUE_FULL = "DROPPED_QUEUE_FULL"
    SUSPENDED_DISK_GUARD = "SUSPENDED_DISK_GUARD"
    SUSPENDED_ACTIVE_CAP = "SUSPENDED_ACTIVE_CAP"
    SUSPENDED_INTERNAL_ERROR = "SUSPENDED_INTERNAL_ERROR"


@dataclass(frozen=True, slots=True)
class DiagnosticEvent:
    application: str
    application_version: str
    session_id: str
    event_category: str
    severity: DiagnosticSeverity
    selected_preference: str
    detected_adapter: str
    effective_backend: str
    compatibility_result: str
    failure_stage: str
    reason_code: str
    next_action: str
    exception_category: str
    correlation_id: str
    duplicate_count: int = 1

    def __post_init__(self) -> None:
        for label, value in (
            ("application", self.application),
            ("event_category", self.event_category),
            ("selected_preference", self.selected_preference),
            ("detected_adapter", self.detected_adapter),
            ("effective_backend", self.effective_backend),
            ("compatibility_result", self.compatibility_result),
            ("failure_stage", self.failure_stage),
            ("reason_code", self.reason_code),
            ("next_action", self.next_action),
            ("exception_category", self.exception_category),
        ):
            _require_code(label, value)
        if _VERSION_RE.fullmatch(self.application_version) is None:
            raise DiagnosticsError("application_version is invalid")
        for label, value in (
            ("session_id", self.session_id),
            ("correlation_id", self.correlation_id),
        ):
            if _OPAQUE_ID_RE.fullmatch(value) is None:
                raise DiagnosticsError(f"{label} is invalid")
        if not 1 <= self.duplicate_count <= 1_000_000_000:
            raise DiagnosticsError("duplicate_count is invalid")

    def to_record(self, timestamp: str | None = None) -> dict[str, object]:
        return {
            "schema_version": "1.0.0",
            "message_type": "BvpDesktopDiagnosticEvent",
            "timestamp": timestamp or utc_now_iso(),
            "application": self.application,
            "application_version": self.application_version,
            "session_id": self.session_id,
            "event_category": self.event_category,
            "severity": self.severity.value,
            "selected_preference": self.selected_preference,
            "detected_adapter": self.detected_adapter,
            "effective_backend": self.effective_backend,
            "compatibility_result": self.compatibility_result,
            "failure_stage": self.failure_stage,
            "reason_code": self.reason_code,
            "next_action": self.next_action,
            "exception_category": self.exception_category,
            "correlation_id": self.correlation_id,
            "duplicate_count": self.duplicate_count,
        }


@dataclass(frozen=True, slots=True)
class DiagnosticWriteResult:
    status: DiagnosticWriteStatus
    reason_code: str
    bytes_written: int = 0


class BoundedDesktopDiagnostics:
    """One family writer coordinated by the install-instance lock namespace."""

    def __init__(
        self,
        layout: DesktopInstallLayout,
        *,
        application_family: str,
        wall_time: Callable[[], float] = time.time,
        monotonic: Callable[[], float] = time.monotonic,
        disk_usage: Callable[[str | os.PathLike[str]], Any] = shutil.disk_usage,
    ) -> None:
        if _FAMILY_RE.fullmatch(application_family) is None:
            raise DiagnosticsError("application family is invalid")
        self.layout = layout
        self.family = application_family
        self.root = layout.logs_root
        self.active_path = self.root / f"{application_family}.active.jsonl"
        self._wall_time = wall_time
        self._monotonic = monotonic
        self._disk_usage = disk_usage
        self._queue: deque[tuple[DiagnosticEvent, int]] = deque()
        self._queue_bytes = 0
        self._last_cleanup = 0.0
        self._dedupe: dict[str, tuple[float, int]] = {}
        self._process_times: deque[float] = deque(maxlen=PROCESS_BURST)
        self._validate_root()
        self.cleanup()

    def emit(self, event: DiagnosticEvent) -> DiagnosticWriteResult:
        payload_size = len(self._record_bytes(event))
        if payload_size > MAX_RECORD_BYTES:
            raise DiagnosticsError("diagnostic record exceeds 16 KiB")
        try:
            try:
                with _CoordinatorLock(
                    self.layout.install_instance_id,
                    self.root,
                    WRITER_LOCK_TIMEOUT_SECONDS,
                    self._monotonic,
                ):
                    return self._emit_locked(event)
            except TimeoutError:
                return self._enqueue(event, payload_size)
        except DiagnosticsError:
            return DiagnosticWriteResult(
                DiagnosticWriteStatus.SUSPENDED_INTERNAL_ERROR,
                "DIAGNOSTICS_INTEGRITY_FAILURE",
            )
        except Exception:
            return DiagnosticWriteResult(
                DiagnosticWriteStatus.SUSPENDED_INTERNAL_ERROR,
                "DIAGNOSTICS_INTERNAL_FAILURE",
            )

    def emit_terminal_guard(self, event: DiagnosticEvent) -> DiagnosticWriteResult:
        guarded = replace(
            event,
            severity=DiagnosticSeverity.ERROR,
            event_category="TERMINAL_GUARD",
        )
        key = sha256_bytes(
            canonical_json_bytes(
                {"family": self.family, "session_id": event.session_id}
            )
        )
        try:
            with _CoordinatorLock(
                self.layout.install_instance_id,
                self.root,
                WRITER_LOCK_TIMEOUT_SECONDS,
                self._monotonic,
            ):
                state = self._load_terminal_state()
                if key in state:
                    return DiagnosticWriteResult(
                        DiagnosticWriteStatus.AGGREGATED,
                        "TERMINAL_GUARD_ALREADY_RECORDED",
                    )
                if self._terminal_record_exists(key):
                    state.add(key)
                    self._save_terminal_state(state)
                    return DiagnosticWriteResult(
                        DiagnosticWriteStatus.AGGREGATED,
                        "TERMINAL_GUARD_RECOVERED",
                    )
                self._cleanup_locked(force=False)
                record_size = len(self._record_bytes(guarded))
                capacity = self._capacity_guard(record_size)
                if capacity is not None:
                    return capacity
                result = self._write_record_locked(guarded)
                if result.status is DiagnosticWriteStatus.WRITTEN:
                    state.add(key)
                    self._save_terminal_state(state)
                return result
        except TimeoutError:
            return DiagnosticWriteResult(
                DiagnosticWriteStatus.SUSPENDED_INTERNAL_ERROR,
                "TERMINAL_GUARD_LOCK_TIMEOUT",
            )
        except Exception:
            return DiagnosticWriteResult(
                DiagnosticWriteStatus.SUSPENDED_INTERNAL_ERROR,
                "TERMINAL_GUARD_INTEGRITY_FAILURE",
            )

    def cleanup(self) -> DiagnosticWriteResult:
        try:
            with _CoordinatorLock(
                self.layout.install_instance_id,
                self.root,
                WRITER_LOCK_TIMEOUT_SECONDS,
                self._monotonic,
            ):
                self._cleanup_locked(force=True)
            return DiagnosticWriteResult(DiagnosticWriteStatus.WRITTEN, "CLEANUP_COMPLETE")
        except TimeoutError:
            return DiagnosticWriteResult(DiagnosticWriteStatus.QUEUED, "CLEANUP_LOCK_TIMEOUT")
        except Exception:
            return DiagnosticWriteResult(
                DiagnosticWriteStatus.SUSPENDED_INTERNAL_ERROR,
                "CLEANUP_FAILED",
            )

    @property
    def queued_records(self) -> int:
        return len(self._queue)

    @property
    def queued_bytes(self) -> int:
        return self._queue_bytes

    def _emit_locked(self, event: DiagnosticEvent) -> DiagnosticWriteResult:
        self._cleanup_locked(force=False)
        guard = self._capacity_guard()
        if guard is not None:
            return guard
        now = self._wall_time()
        self._trim_process_rate(now)
        global_state = self._load_rate_state(now)
        if not self._rate_admitted(now, global_state):
            if event.severity in {DiagnosticSeverity.DEBUG, DiagnosticSeverity.INFO}:
                return DiagnosticWriteResult(
                    DiagnosticWriteStatus.DROPPED_RATE_LIMIT,
                    "DIAGNOSTIC_RATE_LIMIT",
                )
            return self._enqueue(event, len(self._record_bytes(event)))
        dedupe_key = sha256_bytes(
            canonical_json_bytes(
                {
                    "family": self.family,
                    "session_id": event.session_id,
                    "category": event.event_category,
                    "reason": event.reason_code,
                    "correlation": event.correlation_id,
                }
            )
        )
        if event.severity in {DiagnosticSeverity.WARN, DiagnosticSeverity.ERROR}:
            previous = self._dedupe.get(dedupe_key)
            if previous and now - previous[0] < DEDUPE_WINDOW_SECONDS:
                self._dedupe[dedupe_key] = (previous[0], previous[1] + 1)
                return DiagnosticWriteResult(
                    DiagnosticWriteStatus.AGGREGATED,
                    "DUPLICATE_AGGREGATED",
                )
            if previous and previous[1] > 1:
                event = replace(event, duplicate_count=previous[1])
            self._dedupe[dedupe_key] = (now, 1)

        record_size = len(self._record_bytes(event))
        guard = self._capacity_guard(record_size)
        if guard is not None:
            return guard
        result = self._write_record_locked(event)
        self._process_times.append(now)
        global_state["events"].append(now)
        self._flush_queue_locked(now, global_state)
        self._save_rate_state(global_state)
        return result

    def _write_record_locked(self, event: DiagnosticEvent) -> DiagnosticWriteResult:
        data = self._record_bytes(event)
        if len(data) > MAX_RECORD_BYTES:
            raise DiagnosticsError("diagnostic record exceeds 16 KiB")
        if self.active_path.exists():
            metadata = self.active_path.stat(follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or self.active_path.is_symlink():
                raise DiagnosticsError("active diagnostic file identity is unsafe")
            if not self._is_owned_log_file(self.active_path, self.family):
                raise DiagnosticsError("active diagnostic file content is not Product-owned")
            if metadata.st_size + len(data) > MAX_ACTIVE_FILE_BYTES:
                self._rotate_locked()
        with self.active_path.open("ab") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        return DiagnosticWriteResult(
            DiagnosticWriteStatus.WRITTEN,
            "DIAGNOSTIC_WRITTEN",
            len(data),
        )

    def _rotate_locked(self) -> None:
        if not self.active_path.exists():
            return
        if not self._is_owned_log_file(self.active_path, self.family):
            raise DiagnosticsError("active diagnostic file is not safely rotatable")
        sequence = time.time_ns()
        while True:
            closed = self.root / f"{self.family}.{sequence:020d}.closed.jsonl"
            if not closed.exists():
                break
            sequence += 1
        os.replace(self.active_path, closed)
        self._cleanup_locked(force=True)

    def _cleanup_locked(self, *, force: bool) -> None:
        now_mono = self._monotonic()
        if not force and now_mono - self._last_cleanup < CLEANUP_INTERVAL_SECONDS:
            return
        self._last_cleanup = now_mono
        now = self._wall_time()
        closed = self._closed_files()
        for path, _, modified in tuple(closed):
            if now - modified > RETENTION_SECONDS:
                path.unlink(missing_ok=True)
        closed = self._closed_files()
        by_family: dict[str, list[tuple[Path, int, float]]] = {}
        for item in closed:
            match = _CLOSED_RE.fullmatch(item[0].name)
            assert match is not None
            by_family.setdefault(match.group("family"), []).append(item)
        for items in by_family.values():
            for path, _, _ in sorted(items, key=_closed_sort_key)[:-RETAINED_GENERATIONS]:
                path.unlink(missing_ok=True)
        while self._product_log_bytes() > SHARED_DIRECTORY_CAP_BYTES:
            remaining = self._closed_files()
            if not remaining:
                break
            remaining.sort(key=_closed_sort_key)
            remaining[0][0].unlink(missing_ok=True)

    def _capacity_guard(self, required_bytes: int = 0) -> DiagnosticWriteResult | None:
        usage = self._disk_usage(self.root)
        required_free = max(MIN_FREE_BYTES, int(usage.total * MIN_FREE_RATIO))
        if usage.free < required_free:
            return DiagnosticWriteResult(
                DiagnosticWriteStatus.SUSPENDED_DISK_GUARD,
                "DIAGNOSTIC_DISK_GUARD",
            )
        total = self._product_log_bytes()
        while total + required_bytes > SHARED_DIRECTORY_CAP_BYTES:
            closed = self._closed_files()
            if not closed:
                break
            closed.sort(key=_closed_sort_key)
            closed[0][0].unlink(missing_ok=True)
            total = self._product_log_bytes()
        if total + required_bytes > SHARED_DIRECTORY_CAP_BYTES:
            return DiagnosticWriteResult(
                DiagnosticWriteStatus.SUSPENDED_ACTIVE_CAP,
                "DIAGNOSTIC_ACTIVE_ONLY_CAP",
            )
        return None

    def _closed_files(self) -> list[tuple[Path, int, float]]:
        result: list[tuple[Path, int, float]] = []
        for path in self.root.iterdir():
            if _CLOSED_RE.fullmatch(path.name) is None or path.is_symlink():
                continue
            metadata = path.stat(follow_symlinks=False)
            match = _CLOSED_RE.fullmatch(path.name)
            assert match is not None
            if (
                stat.S_ISREG(metadata.st_mode)
                and metadata.st_nlink == 1
                and self._is_owned_log_file(path, match.group("family"))
            ):
                result.append((path, metadata.st_size, metadata.st_mtime))
        return result

    def _product_log_bytes(self) -> int:
        total = sum(size for _, size, _ in self._closed_files())
        for path in self.root.glob("*.active.jsonl"):
            family = path.name.removesuffix(".active.jsonl")
            if _FAMILY_RE.fullmatch(family) is None or path.is_symlink():
                continue
            metadata = path.stat(follow_symlinks=False)
            if (
                stat.S_ISREG(metadata.st_mode)
                and metadata.st_nlink == 1
                and self._is_owned_log_file(path, family)
            ):
                total += metadata.st_size
        return total

    def _trim_process_rate(self, now: float) -> None:
        while self._process_times and now - self._process_times[0] >= 10.0:
            self._process_times.popleft()

    def _rate_admitted(self, now: float, state: dict[str, Any]) -> bool:
        process_one = sum(now - item < 1.0 for item in self._process_times)
        process_ten = len(self._process_times)
        global_one = sum(now - item < 1.0 for item in state["events"])
        global_ten = len(state["events"])
        return (
            process_one < PROCESS_BURST
            and process_ten < PROCESS_RATE_PER_SECOND * 10
            and global_one < GLOBAL_BURST
            and global_ten < GLOBAL_RATE_PER_SECOND * 10
        )

    def _rate_state_path(self) -> Path:
        digest = sha256_bytes(self.layout.install_instance_id.encode("utf-8"))[7:23]
        return self.root / f".task066-rate-{digest}.json"

    def _load_rate_state(self, now: float) -> dict[str, Any]:
        path = self._rate_state_path()
        events: list[float] = []
        if path.exists() and not path.is_symlink():
            try:
                metadata = path.stat(follow_symlinks=False)
                if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or not 1 <= metadata.st_size <= 64 * 1024:
                    raise DiagnosticsError("diagnostic rate state identity is unsafe")
                value = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(value, dict) or set(value) != {
                    "schema_version",
                    "install_instance_id",
                    "events",
                    "document_sha256",
                }:
                    raise DiagnosticsError("diagnostic rate state fields mismatch")
                body = dict(value)
                supplied = body.pop("document_sha256")
                if supplied != sha256_bytes(canonical_json_bytes(body)):
                    raise DiagnosticsError("diagnostic rate state digest mismatch")
                if value["schema_version"] != "1.0.0" or value["install_instance_id"] != self.layout.install_instance_id:
                    raise DiagnosticsError("diagnostic rate state identity mismatch")
                events = [float(item) for item in value["events"] if 0 <= now - float(item) < 10.0]
            except DiagnosticsError:
                raise
            except Exception as exc:
                raise DiagnosticsError("diagnostic rate state is invalid") from exc
        return {"events": events[-GLOBAL_RATE_PER_SECOND * 10 :]}

    def _save_rate_state(self, state: dict[str, Any]) -> None:
        body = {
            "schema_version": "1.0.0",
            "install_instance_id": self.layout.install_instance_id,
            "events": state["events"][-GLOBAL_RATE_PER_SECOND * 10 :],
        }
        document = dict(body)
        document["document_sha256"] = sha256_bytes(canonical_json_bytes(body))
        AtomicJsonWriter.write(self._rate_state_path(), document)

    def _terminal_state_path(self) -> Path:
        digest = sha256_bytes(self.layout.install_instance_id.encode("utf-8"))[7:23]
        return self.root / f".task066-terminal-{digest}.json"

    def _load_terminal_state(self) -> set[str]:
        path = self._terminal_state_path()
        if not path.exists() and not path.is_symlink():
            return set()
        metadata = path.stat(follow_symlinks=False)
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_size > 1024 * 1024:
            raise DiagnosticsError("terminal guard state identity is unsafe")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or set(value) != {
            "schema_version",
            "install_instance_id",
            "guard_keys",
            "document_sha256",
        }:
            raise DiagnosticsError("terminal guard state fields mismatch")
        body = dict(value)
        supplied = body.pop("document_sha256")
        if supplied != sha256_bytes(canonical_json_bytes(body)):
            raise DiagnosticsError("terminal guard state digest mismatch")
        if value["schema_version"] != "1.0.0" or value["install_instance_id"] != self.layout.install_instance_id:
            raise DiagnosticsError("terminal guard state identity mismatch")
        keys = value["guard_keys"]
        if not isinstance(keys, list) or len(keys) > 4096 or any(not isinstance(item, str) or not item.startswith("sha256:") for item in keys):
            raise DiagnosticsError("terminal guard state keys are invalid")
        return set(keys)

    def _save_terminal_state(self, keys: set[str]) -> None:
        body = {
            "schema_version": "1.0.0",
            "install_instance_id": self.layout.install_instance_id,
            "guard_keys": sorted(keys)[-4096:],
        }
        document = dict(body)
        document["document_sha256"] = sha256_bytes(canonical_json_bytes(body))
        AtomicJsonWriter.write(self._terminal_state_path(), document)

    def _record_bytes(self, event: DiagnosticEvent) -> bytes:
        record = event.to_record()
        record["application_family"] = self.family
        record["install_instance_id"] = self.layout.install_instance_id
        if event.event_category == "TERMINAL_GUARD":
            record["terminal_guard_key"] = sha256_bytes(
                canonical_json_bytes(
                    {"family": self.family, "session_id": event.session_id}
                )
            )
        record["record_sha256"] = sha256_bytes(canonical_json_bytes(record))
        return canonical_json_bytes(record) + b"\n"

    def _terminal_record_exists(self, key: str) -> bool:
        paths: list[Path] = []
        if self.active_path.exists() and self._is_owned_log_file(self.active_path, self.family):
            paths.append(self.active_path)
        paths.extend(
            path
            for path, _, _ in self._closed_files()
            if _CLOSED_RE.fullmatch(path.name).group("family") == self.family
        )
        for path in paths:
            for line in path.read_bytes().splitlines():
                value = json.loads(line.decode("utf-8"))
                if value.get("terminal_guard_key") == key:
                    return True
        return False

    def _is_owned_log_file(self, path: Path, family: str) -> bool:
        try:
            metadata = path.stat(follow_symlinks=False)
            if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or not 1 <= metadata.st_size <= MAX_ACTIVE_FILE_BYTES:
                return False
            data = path.read_bytes()
            if not data.endswith(b"\n"):
                return False
            for line in data.splitlines():
                if not 1 <= len(line) <= MAX_RECORD_BYTES:
                    return False
                value = json.loads(line.decode("utf-8"))
                body = dict(value) if isinstance(value, dict) else {}
                supplied = body.pop("record_sha256", None)
                if (
                    not isinstance(value, dict)
                    or value.get("schema_version") != "1.0.0"
                    or value.get("message_type") != "BvpDesktopDiagnosticEvent"
                    or value.get("application_family") != family
                    or value.get("install_instance_id") != self.layout.install_instance_id
                    or supplied != sha256_bytes(canonical_json_bytes(body))
                ):
                    return False
            return True
        except Exception:
            return False

    def _enqueue(self, event: DiagnosticEvent, size: int) -> DiagnosticWriteResult:
        while self._queue and (
            len(self._queue) >= MAX_QUEUE_RECORDS
            or self._queue_bytes + size > MAX_QUEUE_BYTES
        ):
            index = next(
                (
                    idx
                    for idx, (queued, _) in enumerate(self._queue)
                    if queued.severity in {DiagnosticSeverity.DEBUG, DiagnosticSeverity.INFO}
                ),
                None,
            )
            if index is None:
                return DiagnosticWriteResult(
                    DiagnosticWriteStatus.DROPPED_QUEUE_FULL,
                    "DIAGNOSTIC_QUEUE_FULL",
                )
            queued, queued_size = self._queue[index]
            del self._queue[index]
            self._queue_bytes -= queued_size
        self._queue.append((event, size))
        self._queue_bytes += size
        return DiagnosticWriteResult(DiagnosticWriteStatus.QUEUED, "DIAGNOSTIC_QUEUED")

    def _flush_queue_locked(self, now: float, global_state: dict[str, Any]) -> None:
        for _ in range(min(len(self._queue), PROCESS_BURST)):
            self._trim_process_rate(now)
            if not self._rate_admitted(now, global_state):
                return
            event, size = self._queue.popleft()
            self._queue_bytes -= size
            guard = self._capacity_guard(size)
            if guard is not None:
                self._queue.appendleft((event, size))
                self._queue_bytes += size
                return
            self._write_record_locked(event)
            self._process_times.append(now)
            global_state["events"].append(now)

    def _validate_root(self) -> None:
        if self.root.is_symlink():
            raise DiagnosticsError("log root must not be a symlink")
        try:
            metadata = self.root.stat(follow_symlinks=False)
        except OSError as exc:
            raise DiagnosticsError("log root must be installer-provisioned") from exc
        if not stat.S_ISDIR(metadata.st_mode):
            raise DiagnosticsError("log root must be a directory")


class _CoordinatorLock(AbstractContextManager[None]):
    def __init__(self, instance_id: str, root: Path, timeout: float, monotonic: Callable[[], float]) -> None:
        digest = sha256_bytes(instance_id.encode("utf-8"))[7:39]
        self.path = root / f".task066-coordinator-{digest}.lock"
        self.key = str(self.path)
        self.timeout = timeout
        self.monotonic = monotonic
        self.handle: Any = None
        self.thread_lock = _COORDINATOR_THREAD_LOCKS.setdefault(self.key, threading.Lock())

    def __enter__(self) -> None:
        if not self.thread_lock.acquire(timeout=self.timeout):
            raise TimeoutError("diagnostic coordinator timeout")
        self.handle = self.path.open("a+b")
        deadline = self.monotonic() + self.timeout
        try:
            while True:
                try:
                    if os.name == "nt":
                        import msvcrt

                        if self.handle.seek(0, os.SEEK_END) == 0:
                            self.handle.write(b"0")
                            self.handle.flush()
                        self.handle.seek(0)
                        msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return None
                except (BlockingIOError, OSError):
                    if self.monotonic() >= deadline:
                        raise TimeoutError("diagnostic coordinator timeout")
                    time.sleep(0.01)
        except Exception:
            self.handle.close()
            self.handle = None
            self.thread_lock.release()
            raise

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        try:
            if self.handle:
                if os.name == "nt":
                    import msvcrt

                    self.handle.seek(0)
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
                self.handle.close()
        finally:
            self.handle = None
            self.thread_lock.release()


_COORDINATOR_THREAD_LOCKS: dict[str, threading.Lock] = {}


def _require_code(label: str, value: str) -> None:
    if not isinstance(value, str) or _CODE_RE.fullmatch(value) is None:
        raise DiagnosticsError(f"{label} must be a public code")


def _closed_sort_key(item: tuple[Path, int, float]) -> tuple[int, str, str]:
    match = _CLOSED_RE.fullmatch(item[0].name)
    assert match is not None
    return (int(match.group("sequence")), match.group("family"), item[0].name)


__all__ = [
    "BoundedDesktopDiagnostics",
    "CLEANUP_INTERVAL_SECONDS",
    "DEDUPE_WINDOW_SECONDS",
    "DiagnosticEvent",
    "DiagnosticSeverity",
    "DiagnosticWriteResult",
    "DiagnosticWriteStatus",
    "DiagnosticsError",
    "GLOBAL_BURST",
    "GLOBAL_RATE_PER_SECOND",
    "MAX_ACTIVE_FILE_BYTES",
    "MAX_QUEUE_BYTES",
    "MAX_QUEUE_RECORDS",
    "MAX_RECORD_BYTES",
    "MIN_FREE_BYTES",
    "MIN_FREE_RATIO",
    "PROCESS_BURST",
    "PROCESS_RATE_PER_SECOND",
    "RETAINED_GENERATIONS",
    "RETENTION_SECONDS",
    "SHARED_DIRECTORY_CAP_BYTES",
    "WRITER_LOCK_TIMEOUT_SECONDS",
]
