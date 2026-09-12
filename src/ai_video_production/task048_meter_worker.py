"""TASK-048 C1 read-only worker over the genuine public Project/P1/P2 APIs.

The trusted packaged host supplies physical-root pins. This module never starts
a process, changes a Project/policy, captures audio, or creates a default policy.
Only the legacy UNKNOWN-loss route is live in C1A.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import queue
import stat
import threading
import time
from typing import Any, BinaryIO, Protocol
import uuid

from . import task048_meter_protocol as wire
from . import voice_quality_meter_runtime_contract as p2
from .product_project_store import ProductProjectManifestStore
from .serialization import canonical_json_bytes, sha256_bytes
from .voice_quality_meter_policy_store import MeterPolicyProjectStore


class RootPins(Protocol):
    @property
    def project_root(self) -> Path: ...
    def verify(self) -> None: ...
    def close(self) -> None: ...


class RootInspector(Protocol):
    def bind(self, bootstrap: wire.Bootstrap) -> RootPins: ...


class BindingError(ValueError):
    def __init__(self, code: wire.StatusCode) -> None:
        self.code = code
        super().__init__("ERR_TASK048_C1_" + code.name)


def _head_signature(path: Path) -> tuple[int, int, int, int]:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise BindingError(wire.StatusCode.PROJECT_IDENTITY_CHANGED)
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def _status(message: wire.Message, code: wire.StatusCode) -> wire.Status:
    return wire.Status(wire.response_correlation(message), code)


def _metric(value: wire.Metric) -> dict[str, Any]:
    return {"state": value.state.name, "value_dbfs": value.value_dbfs}


def _observation(window: wire.Window, context: dict[str, Any]) -> dict[str, Any]:
    """Only representation adaptation; public P2 owns semantic validation."""
    document = {
        "record_type": p2.OBSERVATION_RECORD_TYPE, "schema_version": 1,
        "canonical_owner_task": "TASK-048", "query_context": context,
        "capture_point": (p2.KNOWN_CAPTURE_POINT if window.capture_point is
                          wire.CapturePoint.CONTROLLER_FLOAT32_PRE_DRAW else "UNKNOWN"),
        "paused": window.paused, "window_loss_state": window.loss.name,
        "window_counts": {
            "state": window.window_counts.state.name,
            "finite_sample_values": window.window_counts.finite,
            "nonfinite_sample_values": window.window_counts.nonfinite,
            "clip_sample_values": window.window_counts.clips,
        },
        "session_counts": {
            "state": window.session_counts.state.name,
            "finite_sample_values": window.session_counts.finite,
            "clip_sample_values": window.session_counts.clips,
        },
        "window_peak": _metric(window.window_peak),
        "window_rms": _metric(window.window_rms),
        "session_peak": _metric(window.session_peak),
    }
    document["observation_sha256"] = sha256_bytes(
        p2.OBSERVATION_DOMAIN + canonical_json_bytes(document))
    return document


def _digest(value: str) -> bytes:
    # All callers have already passed the genuine public P2 parser.
    if type(value) is not str or len(value) != 71 or not value.startswith("sha256:"):
        raise wire.ProtocolError("CORRELATION")
    result = bytes.fromhex(value[7:])
    if len(result) != 32:
        raise wire.ProtocolError("CORRELATION")
    return result


@dataclass(frozen=True, slots=True)
class _Invocation:
    message: wire.Message
    generation: int


class MeterWorker:
    """Thread-safe control plane and one separately scheduled synchronous read.

    process_frame returns a diagnostic reply body; one caller-owned output pump
    must serialize replies. Control invalidation never waits for the P1 read.
    Tests inject only physical pins, not a policy store or runtime capability.
    """

    def __init__(self, root_inspector: RootInspector) -> None:
        self._inspector = root_inspector
        self._lock = threading.RLock()
        self._receive_lock = threading.Lock()
        self._receiver = wire.OrderedReceiver(allowed=(
            wire.MessageType.BOOTSTRAP, wire.MessageType.WINDOW,
            wire.MessageType.INVALIDATE, wire.MessageType.CLOSE,
        ))
        self._phase = "NEW"
        self._generation = 0
        self._bootstrap: wire.Bootstrap | None = None
        self._pins: RootPins | None = None
        self._store: MeterPolicyProjectStore | None = None
        self._runtime: p2.MeterRuntimeController | None = None
        self._active: _Invocation | None = None
        self._consumer: tuple[str, str, str] | None = None
        self._next_consumer: tuple[str, str, str, bool] | None = None
        self._seen_consumers: set[str] = set()
        self._seen_views: set[str] = set()
        self._reserved_consumers: set[str] = set()
        self._reserved_views: set[str] = set()
        self._last_ui_sequence = 0
        self._disposed = False

    @property
    def phase(self) -> str:
        with self._lock:
            return self._phase

    @property
    def busy(self) -> bool:
        with self._lock:
            return self._active is not None

    def _check_head(self, bootstrap: wire.Bootstrap, pins: RootPins) -> Any:
        code = wire.StatusCode.READBACK_UNAVAILABLE
        manifest = None
        try:
            pins.verify()
            root = pins.project_root
            target = ProductProjectManifestStore.path(root)
            before = _head_signature(target)
            manifest = ProductProjectManifestStore.load(root)
            after = _head_signature(target)
            pins.verify()
            if before != after:
                raise BindingError(wire.StatusCode.PROJECT_IDENTITY_CHANGED)
            if manifest.project_id != bootstrap.project_id:
                raise BindingError(wire.StatusCode.PROJECT_IDENTITY_CHANGED)
            if (manifest.project_revision != bootstrap.project_revision
                    or _digest(manifest.project_manifest_sha256) != bootstrap.manifest_sha256):
                raise BindingError(wire.StatusCode.PROJECT_HEAD_CHANGED)
            return manifest
        except BindingError as error:
            code = error.code
        except Exception:
            pass
        raise BindingError(code)

    def _dispose_if_drained(self) -> None:
        if self._phase != "CLOSED" or self._active is not None or self._disposed:
            return
        self._disposed = True
        # Public close only; a live evaluation retains P2's lease until finally.
        for resource in (self._runtime, self._store, self._pins):
            if resource is not None:
                try:
                    resource.close()
                except Exception:
                    pass

    def close(self) -> None:
        with self._lock:
            self._generation += 1
            self._phase = "CLOSED"
            self._receiver.close()
            self._next_consumer = None
            if self._runtime is not None:
                self._runtime.close()
            self._dispose_if_drained()

    def _bind(self, message: wire.Message) -> wire.Ready | wire.Status | None:
        bootstrap = message.body
        with self._lock:
            if self._phase != "NEW":
                raise wire.ProtocolError("STATE")
            self._phase = "BINDING"
            generation = self._generation
        pins = store = runtime = None
        failed = False
        try:
            pins = self._inspector.bind(bootstrap)
            self._check_head(bootstrap, pins)
            store = MeterPolicyProjectStore(pins.project_root, bootstrap.project_id)
            runtime = p2.MeterRuntimeController(store)
            self._check_head(bootstrap, pins)
        except Exception:
            failed = True
        with self._lock:
            if failed or self._phase != "BINDING" or generation != self._generation:
                for resource in (runtime, store, pins):
                    if resource is not None:
                        try:
                            resource.close()
                        except Exception:
                            pass
                was_current = self._phase == "BINDING" and generation == self._generation
                self.close()
                return _status(message, wire.StatusCode.BOOTSTRAP_REJECTED) if was_current else None
            self._bootstrap, self._pins = bootstrap, pins
            self._store, self._runtime = store, runtime
            self._phase = "ACTIVE"
            return wire.Ready(
                wire.response_correlation(message), bootstrap.project_revision,
                bootstrap.manifest_sha256, bootstrap.root_volume, bootstrap.root_file_id,
                runtime.runtime_epoch, runtime.policy_producer_epoch,
            )

    def _invalidate(self, message: wire.Message) -> wire.Status | None:
        body = message.body
        with self._lock:
            if self._phase not in ("ACTIVE", "WAIT_NEXT") or self._runtime is None:
                raise wire.ProtocolError("STATE")
            if body.selected_epoch != self._bootstrap.selected_epoch:
                raise wire.ProtocolError("CORRELATION")
            if (body.next_consumer_epoch in self._seen_consumers
                    or body.next_view_epoch in self._seen_views
                    or body.next_consumer_epoch in self._reserved_consumers
                    or body.next_view_epoch in self._reserved_views):
                raise wire.ProtocolError("CORRELATION")
            if len(self._reserved_consumers | self._seen_consumers) >= 4096:
                raise wire.ProtocolError("LIMIT")
            if self._consumer is not None:
                if body.reason is wire.InvalidationReason.NEW_SESSION:
                    if body.next_session_id == self._consumer[0]:
                        raise wire.ProtocolError("CORRELATION")
                elif body.reason not in (
                    wire.InvalidationReason.PROJECT_CHANGED,
                    wire.InvalidationReason.READBACK_UNAVAILABLE,
                    wire.InvalidationReason.HOST_RESTORE_UNCERTAIN,
                ) and body.next_session_id != self._consumer[0]:
                    raise wire.ProtocolError("CORRELATION")
            self._generation += 1
            self._reserved_consumers.add(body.next_consumer_epoch)
            self._reserved_views.add(body.next_view_epoch)
            reason = ("RECONNECT" if body.reason is wire.InvalidationReason.NEW_SESSION
                      else body.reason.name)
            self._runtime.invalidate(reason)
            if body.reason in (
                wire.InvalidationReason.PROJECT_CHANGED,
                wire.InvalidationReason.READBACK_UNAVAILABLE,
                wire.InvalidationReason.HOST_RESTORE_UNCERTAIN,
            ):
                self.close()
            else:
                self._next_consumer = (
                    body.next_session_id, body.next_consumer_epoch,
                    body.next_view_epoch, body.paused,
                )
                self._phase = "WAIT_NEXT"
            return _status(message, wire.StatusCode.INVALIDATED)

    def _validate_window(self, window: wire.Window) -> None:
        if window.loss is not wire.Loss.UNKNOWN:
            raise wire.ProtocolError("INVALID_VALUE")
        context = {
            "project_id": self._bootstrap.project_id,
            "session_id": window.session_id, "consumer_epoch": window.consumer_epoch,
            "window_sequence": 1,
            "request_id": "00000000-0000-4000-8000-000000000001",
        }
        # Diagnostic validation only; this context is never used as a live ticket.
        observation = _observation(window, context)
        p2.serialize_meter_runtime_observation(observation)

    def _begin_invocation(self, message: wire.Message) -> _Invocation | wire.Status:
        window = message.body
        with self._lock:
            if self._phase not in ("ACTIVE", "WAIT_NEXT") or self._bootstrap is None:
                raise wire.ProtocolError("STATE")
            if window.selected_epoch != self._bootstrap.selected_epoch:
                raise wire.ProtocolError("CORRELATION")
            if self._active is not None:
                return _status(message, wire.StatusCode.P2_BUSY)
            consumer = (window.session_id, window.consumer_epoch, window.view_epoch)
            if self._phase == "WAIT_NEXT":
                if self._next_consumer != (*consumer, window.paused):
                    raise wire.ProtocolError("CORRELATION")
            elif self._consumer is not None and consumer != self._consumer:
                raise wire.ProtocolError("CORRELATION")
            if self._consumer != consumer:
                if (consumer[1] in self._seen_consumers or consumer[2] in self._seen_views
                        or len(self._seen_consumers) >= 4096):
                    raise wire.ProtocolError("LIMIT")
            elif window.ui_sequence <= self._last_ui_sequence:
                raise wire.ProtocolError("SEQUENCE")
            invocation = _Invocation(message, self._generation)
            self._active = invocation
            return invocation

    def _current(self, invocation: _Invocation) -> bool:
        return (self._active is invocation and invocation.generation == self._generation
                and self._phase in ("ACTIVE", "WAIT_NEXT"))

    def _project(self, invocation: _Invocation) -> wire.Projection | wire.Status | None:
        message = invocation.message
        code = wire.StatusCode.P2_REJECTED
        candidate = None
        try:
            window = message.body
            with self._lock:
                if not self._current(invocation):
                    return None
            self._check_head(self._bootstrap, self._pins)
            with self._lock:
                if not self._current(invocation):
                    return None
                consumer = (window.session_id, window.consumer_epoch, window.view_epoch)
                if consumer != self._consumer:
                    self._runtime.activate_consumer(
                        session_id=window.session_id, consumer_epoch=window.consumer_epoch)
                    self._seen_consumers.add(window.consumer_epoch)
                    self._seen_views.add(window.view_epoch)
                    self._consumer = consumer
                self._last_ui_sequence = window.ui_sequence
                self._next_consumer = None
                self._phase = "ACTIVE"
                ticket = self._runtime.begin_window()
            context = ticket.query_context.to_dict()
            observation = _observation(window, context)
            request = {
                "record_type": p2.REQUEST_RECORD_TYPE, "schema_version": 1,
                "canonical_owner_task": "TASK-048", "query_context": context,
                "runtime_epoch": ticket.runtime_epoch,
                "policy_producer_epoch": ticket.policy_producer_epoch,
                "observation": observation,
            }
            request["request_sha256"] = sha256_bytes(
                p2.REQUEST_DOMAIN + canonical_json_bytes(request))
            live = self._runtime.project(ticket, p2.serialize_meter_runtime_request(request))
            # Only a genuine project() return is used; no parsed fixture admission.
            proof = p2.serialize_meter_runtime_projection(live.to_dict())
            document = p2.parse_meter_runtime_projection(proof)
            self._check_head(self._bootstrap, self._pins)
            identity = document["policy_observation"]["identity"]
            if identity is not None and (
                identity["project_id"] != self._bootstrap.project_id
                or identity["project_revision"] != self._bootstrap.project_revision
                or _digest(identity["project_manifest_sha256"]) != self._bootstrap.manifest_sha256
            ):
                raise BindingError(wire.StatusCode.PROJECT_HEAD_CHANGED)
            projection = wire.Projection(
                wire.response_correlation(message), window.session_id, window.consumer_epoch,
                window.view_epoch, window.ui_sequence, context["window_sequence"],
                context["request_id"], document["runtime_epoch"],
                document["policy_producer_epoch"],
                _digest(document["observation"]["observation_sha256"]),
                _digest(document["request_sha256"]), _digest(document["projection_sha256"]),
                wire.Band[document["display_band"]], wire.P2Reason[document["reason_code"]], proof,
            )
            with self._lock:
                candidate = projection if self._current(invocation) else None
        except BindingError as error:
            code = error.code
        except p2.MeterRuntimeContractError as error:
            code = (wire.StatusCode.P2_CAPACITY_EXHAUSTED if error.reason == "CAPACITY_EXHAUSTED"
                    else wire.StatusCode.P2_BUSY if error.reason == "RUNTIME_BUSY"
                    else wire.StatusCode.P2_REJECTED)
        except Exception:
            code = wire.StatusCode.READBACK_UNAVAILABLE
        finally:
            with self._lock:
                current = self._current(invocation)
                if self._active is invocation:
                    self._active = None
                self._dispose_if_drained()
        if candidate is not None:
            with self._lock:
                return (candidate if invocation.generation == self._generation
                        and self.reply_is_current(candidate) else None)
        if not current:
            return None
        if code in (
            wire.StatusCode.PROJECT_HEAD_CHANGED, wire.StatusCode.PROJECT_IDENTITY_CHANGED,
            wire.StatusCode.READBACK_UNAVAILABLE, wire.StatusCode.P2_CAPACITY_EXHAUSTED,
        ):
            self.close()
        return _status(message, code)

    def reply_is_current(self, body: wire.Body) -> bool:
        """Output pump rechecks queued projection freshness before serialization."""
        with self._lock:
            if type(body) is wire.Projection:
                return (self._phase == "ACTIVE" and self._consumer == (
                    body.session_id, body.consumer_epoch, body.view_epoch)
                    and body.ui_sequence == self._last_ui_sequence)
            if type(body) is wire.Ready:
                return self._phase in ("ACTIVE", "WAIT_NEXT")
            return type(body) is wire.Status

    def _receive(self, data: bytes) -> wire.Message | _Invocation | wire.Status:
        # Reader-side reservation prevents a later control/window frame from
        # overtaking a scheduled evaluation that has not started its thread yet.
        with self._receive_lock:
            message = self._receiver.accept(data)
            if self._phase == "NEW" and message.kind is not wire.MessageType.BOOTSTRAP:
                raise wire.ProtocolError("STATE")
            if message.kind is wire.MessageType.WINDOW:
                if self._bootstrap is None:
                    raise wire.ProtocolError("STATE")
                self._validate_window(message.body)
                return self._begin_invocation(message)
            return message

    def _dispatch(self, received: wire.Message | _Invocation | wire.Status) -> wire.Body | None:
        if type(received) is _Invocation:
            return self._project(received)
        if type(received) is wire.Status:
            return received
        if received.kind is wire.MessageType.BOOTSTRAP:
            return self._bind(received)
        if received.kind is wire.MessageType.CLOSE:
            if (self._bootstrap is None
                    or received.body.selected_epoch != self._bootstrap.selected_epoch):
                raise wire.ProtocolError("CORRELATION")
            self.close()
            return None
        if received.kind is wire.MessageType.INVALIDATE:
            return self._invalidate(received)
        raise wire.ProtocolError("STATE")

    def process_frame(self, data: bytes) -> wire.Body | None:
        """Caller submits frames in transport order; WINDOW may run off-reader."""
        error = None
        try:
            return self._dispatch(self._receive(data))
        except wire.ProtocolError as failure:
            error = failure.reason
        except Exception:
            error = "INVALID_FRAME"
        self.close()
        raise wire.ProtocolError(error)

    def eof(self) -> None:
        self.close()


def serve_metadata_stream(
    reader: BinaryIO, writer: BinaryIO, worker: MeterWorker, *,
    cancel_read: Any,
    monotonic_ns: Any = time.monotonic_ns,
) -> None:
    """Private stdio worker pump; explicit host supplies handles/root inspector.

    No process/native API is called here. The trusted host supplies a nonblocking
    owned-read cancellation operation; there is no silent no-op fallback.
    At most one evaluation and two response
    slots exist. A blocking I/O operation is terminated by the owner's worker Job
    on close/timeout; the capture/UI process never waits on this function.
    """
    responses: queue.Queue[wire.Body | None] = queue.Queue(maxsize=2)
    stop = threading.Event()
    output_failure = threading.Event()
    nonce: bytes | None = None
    active: threading.Thread | None = None
    active_lock = threading.Lock()
    parser_lock = threading.Lock()
    parser = wire.FrameAccumulator()
    ready_deadline = monotonic_ns() + 5_000_000_000
    if not callable(cancel_read):
        raise wire.ProtocolError("INVALID_VALUE")

    def abort() -> None:
        stop.set()
        worker.close()
        try:
            cancel_read()
        except Exception:
            # Parent's owned worker Job remains the final cancellation boundary.
            pass

    def watchdog() -> None:
        while not stop.wait(0.025):
            try:
                now = monotonic_ns()
                with parser_lock:
                    parser.expire(now)
                if worker.phase in ("NEW", "BINDING") and now >= ready_deadline:
                    raise wire.ProtocolError("CLOSED")
            except Exception:
                abort()
                return

    def emit(body: wire.Body | None) -> None:
        if body is None or stop.is_set():
            return
        try:
            responses.put_nowait(body)
        except queue.Full:
            abort()

    def write_replies() -> None:
        sequence = 0
        while not stop.is_set() or not responses.empty():
            try:
                body = responses.get(timeout=0.05)
            except queue.Empty:
                continue
            if body is None:
                return
            if not worker.reply_is_current(body):
                continue
            sequence += 1
            try:
                data = wire.encode_message(body, nonce=nonce, sequence=sequence)
                written = writer.write(data)
                if written is not None and written != len(data):
                    raise wire.ProtocolError("INVALID_FRAME")
                writer.flush()
            except Exception:
                output_failure.set()
                abort()
                return

    output = threading.Thread(target=write_replies, name="task048-c1-output", daemon=True)
    output.start()
    timer = threading.Thread(target=watchdog, name="task048-c1-deadline", daemon=True)
    timer.start()

    def evaluate(invocation: _Invocation) -> None:
        try:
            emit(worker._dispatch(invocation))
        except Exception:
            abort()
        finally:
            with active_lock:
                pass

    try:
        while not stop.is_set() and worker.phase != "CLOSED":
            if worker.phase in ("NEW", "BINDING") and monotonic_ns() >= ready_deadline:
                raise wire.ProtocolError("CLOSED")
            # read1 avoids waiting for an arbitrary large fill on buffered pipes.
            read = getattr(reader, "read1", reader.read)
            chunk = read(4096)
            if not chunk:
                worker.eof()
                break
            with parser_lock:
                messages = parser.feed(chunk, now_ns=monotonic_ns())
            for message in messages:
                if nonce is None:
                    nonce = message.nonce
                received = worker._receive(message.wire)
                if type(received) is _Invocation:
                    with active_lock:
                        active = threading.Thread(
                            target=evaluate, args=(received,),
                            name="task048-c1-evaluation", daemon=True)
                        active.start()
                else:
                    emit(worker._dispatch(received))
        if output_failure.is_set():
            raise wire.ProtocolError("CLOSED")
    finally:
        stop.set()
        worker.close()
        # No evaluation join here: its P2 lease drains in its own finally.
        try:
            responses.put_nowait(None)
        except queue.Full:
            pass
        output.join(timeout=0.1)
