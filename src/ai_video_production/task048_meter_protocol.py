"""TASK-048 C1 binary metadata protocol; no process, Project, or audio I/O.

Wire records are diagnostics, never P1/P2 capabilities. Native-v1 observations
must retain UNKNOWN loss provenance. The independent design fixes every byte.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum
from hashlib import sha256
import math
from pathlib import PureWindowsPath
import re
import struct
import threading
from typing import Any
import uuid

MAX_INTEGER = 9_007_199_254_740_991
MAX_FRAME_BYTES = 65_536
MAX_PROOF_BYTES = 49_152
DISPLAY_DEADLINE_NS = 250_000_000
MAGIC = b"BVM1"
VERSION = 1
_HEADER = struct.Struct("<I4sHHQ32s")
_BOOT = struct.Struct("<16sQ16sQ32sHH")
_WINDOW = struct.Struct("<16s16s16s16sQBBBBBQQQBQQBdBdBd")
_COMMON = struct.Struct("<BBHQ32s16s")
_READY = struct.Struct("<Q32sQ16s16s16s")
_PROJECTION = struct.Struct("<16s16s16sQQ16s16s16s32s32s32sBBHI32s")
_INVALIDATE = struct.Struct("<16s16s16s16sBBH")
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")
_PROJECT_ID = re.compile(r"[a-z][a-z0-9-]{2,63}\Z")


class ProtocolError(ValueError):
    """Closed errors intentionally omit payloads, paths and exception bodies."""

    def __init__(self, reason: str = "INVALID_FRAME") -> None:
        self.reason = reason if reason in {
            "INVALID_FRAME", "INVALID_VALUE", "INVALID_NUMBER", "INVALID_UUID",
            "CORRELATION", "SEQUENCE", "STATE", "CLOSED", "BUSY", "LIMIT",
        } else "INVALID_FRAME"
        super().__init__("ERR_TASK048_C1_" + self.reason)


def _fail(reason: str = "INVALID_FRAME") -> Any:
    raise ProtocolError(reason)


def _public(operation: Any, *args: Any, **kwargs: Any) -> Any:
    reason = "INVALID_FRAME"
    try:
        return operation(*args, **kwargs)
    except ProtocolError as error:
        reason = error.reason
    except Exception:
        pass
    raise ProtocolError(reason)


class MessageType(IntEnum):
    BOOTSTRAP = 1
    WINDOW = 2
    RESULT = 3
    INVALIDATE = 4
    CLOSE = 5


class CapturePoint(IntEnum):
    UNKNOWN = 0
    CONTROLLER_FLOAT32_PRE_DRAW = 1


class Loss(IntEnum):
    NO_LOSS_REPORTED = 0
    LOSS_REPORTED = 1
    UNKNOWN = 2


class CountState(IntEnum):
    VALID = 0
    COUNTER_OVERFLOW = 1
    UNAVAILABLE = 2


class MetricState(IntEnum):
    FINITE = 0
    LINEAR_ZERO = 1
    NO_VALUE = 2
    OVERFLOW = 3
    INVALID = 4


class Band(IntEnum):
    UNCONFIRMED = 0
    BELOW_TARGET = 1
    TARGET = 2
    ABOVE_TARGET = 3
    WARNING = 4
    TRUE_CLIP = 5


class P2Reason(IntEnum):
    POLICY_NOT_BOUND = 1
    POLICY_REVOKED = 2
    POLICY_STALE = 3
    POLICY_MISMATCH = 4
    PROJECT_RECOVERY_REQUIRED = 5
    PROJECT_ROLLBACK_UNCERTAIN = 6
    POLICY_INVALID = 7
    POLICY_READBACK_FAILED = 8
    OBSERVATION_INVALID_NUMERIC = 9
    OBSERVATION_COUNTS_UNAVAILABLE = 10
    OBSERVATION_NONFINITE = 11
    CAPTURE_POINT_UNKNOWN = 12
    OBSERVATION_LOSS = 13
    OBSERVATION_LOSS_UNKNOWN = 14
    OBSERVATION_PAUSED = 15
    OBSERVATION_NO_INPUT = 16
    WINDOW_POLICY_CLASSIFIED = 17


class StatusCode(IntEnum):
    BOOTSTRAP_REJECTED = 1
    PROJECT_HEAD_CHANGED = 2
    PROJECT_IDENTITY_CHANGED = 3
    P2_REJECTED = 4
    P2_BUSY = 5
    P2_CAPACITY_EXHAUSTED = 6
    READBACK_UNAVAILABLE = 7
    INVALIDATED = 8


class InvalidationReason(IntEnum):
    PROJECT_CHANGED = 1
    READBACK_UNAVAILABLE = 2
    TIMEOUT = 3
    PAUSED = 4
    RESUMED = 5
    RECONNECT = 6
    HOST_RESTORE_UNCERTAIN = 7
    NEW_SESSION = 8


class CloseReason(IntEnum):
    USER_CLOSE = 1
    PARENT_EXIT = 2
    PROJECT_SWITCH = 3
    WORKER_FAILURE = 4


def _integer(value: Any, minimum: int = 0, maximum: int = MAX_INTEGER) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        _fail("INVALID_NUMBER")
    return value


def _enum(value: Any, kind: Any) -> Any:
    if type(value) not in (int, kind):
        _fail("INVALID_VALUE")
    found = None
    try:
        found = kind(value)
    except ValueError:
        pass
    if found is None:
        _fail("INVALID_VALUE")
    return found


def _bytes(value: Any, size: int) -> bytes:
    if type(value) is not bytes or len(value) != size:
        _fail("INVALID_VALUE")
    return value


def _uuid(value: Any) -> bytes:
    if type(value) is not str or not _UUID.fullmatch(value):
        _fail("INVALID_UUID")
    return uuid.UUID(value).bytes


def _uuid_text(value: bytes) -> str:
    text = str(uuid.UUID(bytes=value))
    _uuid(text)
    return text


def _path(value: Any) -> bytes:
    if type(value) is not str or not re.match(r"^[A-Z]:\\", value):
        _fail("INVALID_VALUE")
    if any(ord(c) < 32 or c in '<>"|?*' for c in value) or ":" in value[2:]:
        _fail("INVALID_VALUE")
    path = PureWindowsPath(value)
    if len(path.parts) < 3 or str(path) != value or value.endswith("\\"):
        _fail("INVALID_VALUE")
    if any(p in (".", "..") or p.endswith((" ", ".")) for p in path.parts[1:]):
        _fail("INVALID_VALUE")
    encoded = value.encode("utf-8", errors="strict")
    if not 1 <= len(encoded) <= 8192:
        _fail("LIMIT")
    return encoded


@dataclass(frozen=True, slots=True, repr=False)
class Bootstrap:
    selected_epoch: str
    root_volume: int
    root_file_id: bytes
    project_revision: int
    manifest_sha256: bytes
    project_id: str
    project_root: str

    def __repr__(self) -> str:
        return "Bootstrap(<private Project binding>)"


@dataclass(frozen=True, slots=True)
class Metric:
    state: MetricState
    value_dbfs: float | None


@dataclass(frozen=True, slots=True)
class WindowCounts:
    state: CountState
    finite: int | None
    nonfinite: int | None
    clips: int | None


@dataclass(frozen=True, slots=True)
class SessionCounts:
    state: CountState
    finite: int | None
    clips: int | None


@dataclass(frozen=True, slots=True)
class Window:
    selected_epoch: str
    session_id: str
    consumer_epoch: str
    view_epoch: str
    ui_sequence: int
    capture_point: CapturePoint
    paused: bool
    loss: Loss
    window_counts: WindowCounts
    session_counts: SessionCounts
    window_peak: Metric
    window_rms: Metric
    session_peak: Metric

    @property
    def correlation(self) -> tuple[str, str, str, str, int]:
        return (self.selected_epoch, self.session_id, self.consumer_epoch,
                self.view_epoch, self.ui_sequence)


@dataclass(frozen=True, slots=True)
class Correlation:
    source_type: MessageType
    source_sequence: int
    source_sha256: bytes
    selected_epoch: str


@dataclass(frozen=True, slots=True)
class Ready:
    correlation: Correlation
    project_revision: int
    manifest_sha256: bytes
    root_volume: int
    root_file_id: bytes
    runtime_epoch: str
    producer_epoch: str


@dataclass(frozen=True, slots=True)
class Projection:
    correlation: Correlation
    session_id: str
    consumer_epoch: str
    view_epoch: str
    ui_sequence: int
    p2_sequence: int
    request_id: str
    runtime_epoch: str
    producer_epoch: str
    observation_sha256: bytes
    request_sha256: bytes
    projection_sha256: bytes
    band: Band
    reason: P2Reason
    canonical_projection: bytes

    @property
    def window_correlation(self) -> tuple[str, str, str, str, int]:
        return (self.correlation.selected_epoch, self.session_id,
                self.consumer_epoch, self.view_epoch, self.ui_sequence)


@dataclass(frozen=True, slots=True)
class Status:
    correlation: Correlation
    code: StatusCode


@dataclass(frozen=True, slots=True)
class Invalidate:
    selected_epoch: str
    next_session_id: str
    next_consumer_epoch: str
    next_view_epoch: str
    reason: InvalidationReason
    paused: bool


@dataclass(frozen=True, slots=True)
class Close:
    selected_epoch: str
    reason: CloseReason


Body = Bootstrap | Window | Ready | Projection | Status | Invalidate | Close


@dataclass(frozen=True, slots=True, repr=False)
class Message:
    kind: MessageType
    sequence: int
    nonce: bytes
    body: Body
    wire: bytes

    @property
    def sha256(self) -> bytes:
        return sha256(self.wire).digest()

    def __repr__(self) -> str:
        return f"Message(kind={self.kind.name}, sequence={self.sequence})"


def _metric_encode(metric: Metric) -> tuple[int, float]:
    if type(metric) is not Metric:
        _fail("INVALID_VALUE")
    state = _enum(metric.state, MetricState)
    if state is MetricState.FINITE:
        if type(metric.value_dbfs) is not float or not math.isfinite(metric.value_dbfs):
            _fail("INVALID_NUMBER")
        return int(state), metric.value_dbfs
    if metric.value_dbfs is not None:
        _fail("INVALID_VALUE")
    return int(state), 0.0


def _metric_decode(state: int, value: float, raw: bytes) -> Metric:
    kind = _enum(state, MetricState)
    if kind is MetricState.FINITE:
        if not math.isfinite(value):
            _fail("INVALID_NUMBER")
        return Metric(kind, value)
    if raw != b"\0" * 8:
        _fail("INVALID_VALUE")
    return Metric(kind, None)


def _counts_encode(counts: WindowCounts | SessionCounts) -> tuple[int, ...]:
    if type(counts) not in (WindowCounts, SessionCounts):
        _fail("INVALID_VALUE")
    state = _enum(counts.state, CountState)
    values = ((counts.finite, counts.nonfinite, counts.clips)
              if type(counts) is WindowCounts else (counts.finite, counts.clips))
    if state is not CountState.VALID:
        if any(value is not None for value in values):
            _fail("INVALID_VALUE")
        return (int(state),) + (0,) * len(values)
    numbers = tuple(_integer(value) for value in values)
    if numbers[-1] > numbers[0]:
        _fail("INVALID_VALUE")
    return (int(state),) + numbers


def _counts_decode(state: int, values: tuple[int, ...], *, window: bool) -> Any:
    kind = _enum(state, CountState)
    if kind is not CountState.VALID:
        if any(values):
            _fail("INVALID_VALUE")
        values = (None,) * len(values)
    result = WindowCounts(kind, *values) if window else SessionCounts(kind, *values)
    _counts_encode(result)
    return result


def _common_encode(kind: int, status: int, correlation: Correlation) -> bytes:
    if type(correlation) is not Correlation:
        _fail("CORRELATION")
    source_type = _enum(correlation.source_type, MessageType)
    if source_type not in (MessageType.BOOTSTRAP, MessageType.WINDOW, MessageType.INVALIDATE):
        _fail("CORRELATION")
    return _COMMON.pack(kind, status, source_type,
                        _integer(correlation.source_sequence, 1),
                        _bytes(correlation.source_sha256, 32),
                        _uuid(correlation.selected_epoch))


def _body_encode(body: Body) -> tuple[MessageType, bytes]:
    kind = type(body)
    if kind is Bootstrap:
        if type(body.project_id) is not str or not _PROJECT_ID.fullmatch(body.project_id):
            _fail("INVALID_VALUE")
        project = body.project_id.encode("ascii")
        path = _path(body.project_root)
        return MessageType.BOOTSTRAP, _BOOT.pack(
            _uuid(body.selected_epoch), _integer(body.root_volume, maximum=2**64-1),
            _bytes(body.root_file_id, 16), _integer(body.project_revision, 1),
            _bytes(body.manifest_sha256, 32), len(project), len(path),
        ) + project + path
    if kind is Window:
        if type(body.paused) is not bool:
            _fail("INVALID_VALUE")
        return MessageType.WINDOW, _WINDOW.pack(
            _uuid(body.selected_epoch), _uuid(body.session_id), _uuid(body.consumer_epoch),
            _uuid(body.view_epoch), _integer(body.ui_sequence, 1),
            _enum(body.capture_point, CapturePoint), int(body.paused), _enum(body.loss, Loss), 0,
            *_counts_encode(body.window_counts), *_counts_encode(body.session_counts),
            *_metric_encode(body.window_peak), *_metric_encode(body.window_rms),
            *_metric_encode(body.session_peak),
        )
    if kind is Ready:
        if body.correlation.source_type != MessageType.BOOTSTRAP:
            _fail("CORRELATION")
        return MessageType.RESULT, _common_encode(0, 0, body.correlation) + _READY.pack(
            _integer(body.project_revision, 1), _bytes(body.manifest_sha256, 32),
            _integer(body.root_volume, maximum=2**64-1), _bytes(body.root_file_id, 16),
            _uuid(body.runtime_epoch), _uuid(body.producer_epoch),
        )
    if kind is Projection:
        if body.correlation.source_type != MessageType.WINDOW:
            _fail("CORRELATION")
        proof = body.canonical_projection
        if type(proof) is not bytes or not 1 <= len(proof) <= MAX_PROOF_BYTES:
            _fail("LIMIT")
        if proof.startswith(b"\xef\xbb\xbf") or b"\0" in proof:
            _fail("INVALID_VALUE")
        # P2 semantic/canonical verification is the worker's public-P2 duty.
        proof.decode("utf-8", errors="strict")
        return MessageType.RESULT, _common_encode(1, 0, body.correlation) + _PROJECTION.pack(
            _uuid(body.session_id), _uuid(body.consumer_epoch), _uuid(body.view_epoch),
            _integer(body.ui_sequence, 1), _integer(body.p2_sequence, 1, 65536),
            _uuid(body.request_id), _uuid(body.runtime_epoch), _uuid(body.producer_epoch),
            _bytes(body.observation_sha256, 32), _bytes(body.request_sha256, 32),
            _bytes(body.projection_sha256, 32), _enum(body.band, Band),
            _enum(body.reason, P2Reason), 0, len(proof), sha256(proof).digest(),
        ) + proof
    if kind is Status:
        return MessageType.RESULT, _common_encode(
            2, _enum(body.code, StatusCode), body.correlation)
    if kind is Invalidate:
        if type(body.paused) is not bool:
            _fail("INVALID_VALUE")
        return MessageType.INVALIDATE, _INVALIDATE.pack(
            _uuid(body.selected_epoch), _uuid(body.next_session_id),
            _uuid(body.next_consumer_epoch), _uuid(body.next_view_epoch),
            _enum(body.reason, InvalidationReason), int(body.paused), 0,
        )
    if kind is Close:
        return MessageType.CLOSE, _uuid(body.selected_epoch) + bytes((
            _enum(body.reason, CloseReason), 0, 0, 0))
    _fail("INVALID_VALUE")


def _body_decode(kind: MessageType, data: bytes) -> Body:
    if kind is MessageType.BOOTSTRAP:
        if len(data) < 84:
            _fail()
        epoch, volume, fid, revision, digest, i, p = _BOOT.unpack_from(data)
        if not 3 <= i <= 64 or not 1 <= p <= 8192 or len(data) != 84 + i + p:
            _fail()
        result = Bootstrap(_uuid_text(epoch), volume, fid, revision, digest,
                           data[84:84+i].decode("ascii"), data[84+i:].decode("utf-8", errors="strict"))
    elif kind is MessageType.WINDOW:
        if len(data) != 145:
            _fail()
        v = _WINDOW.unpack(data)
        if v[6] not in (0, 1) or v[8] != 0:
            _fail("INVALID_VALUE")
        result = Window(
            *(_uuid_text(item) for item in v[:4]), v[4],
            _enum(v[5], CapturePoint), bool(v[6]), _enum(v[7], Loss),
            _counts_decode(v[9], v[10:13], window=True),
            _counts_decode(v[13], v[14:16], window=False),
            _metric_decode(v[16], v[17], data[119:127]),
            _metric_decode(v[18], v[19], data[128:136]),
            _metric_decode(v[20], v[21], data[137:145]),
        )
    elif kind is MessageType.RESULT:
        if len(data) < 60:
            _fail()
        variant, status, source, seq, digest, selected = _COMMON.unpack_from(data)
        correlation = Correlation(_enum(source, MessageType), seq, digest, _uuid_text(selected))
        if variant == 0 and status == 0 and len(data) == 156:
            revision, mdigest, volume, fid, runtime, producer = _READY.unpack_from(data, 60)
            result = Ready(correlation, revision, mdigest, volume, fid,
                           _uuid_text(runtime), _uuid_text(producer))
        elif variant == 2 and len(data) == 60:
            result = Status(correlation, _enum(status, StatusCode))
        elif variant == 1 and status == 0 and len(data) >= 308:
            v = _PROJECTION.unpack_from(data, 60)
            proof = data[308:]
            if v[13] != 0 or not 1 <= v[14] <= MAX_PROOF_BYTES or len(proof) != v[14]:
                _fail()
            if sha256(proof).digest() != v[15]:
                _fail("CORRELATION")
            result = Projection(correlation, *(_uuid_text(item) for item in v[:3]),
                                v[3], v[4], *(_uuid_text(item) for item in v[5:8]),
                                *v[8:11], _enum(v[11], Band), _enum(v[12], P2Reason), proof)
        else:
            _fail()
    elif kind is MessageType.INVALIDATE:
        if len(data) != 68:
            _fail()
        v = _INVALIDATE.unpack(data)
        if v[5] not in (0, 1) or v[6]:
            _fail()
        result = Invalidate(*(_uuid_text(item) for item in v[:4]),
                            _enum(v[4], InvalidationReason), bool(v[5]))
    elif kind is MessageType.CLOSE:
        if len(data) != 20 or data[17:] != b"\0\0\0":
            _fail()
        result = Close(_uuid_text(data[:16]), _enum(data[16], CloseReason))
    else:
        _fail()
    encoded_kind, encoded = _body_encode(result)
    if encoded_kind is not kind or encoded != data:
        _fail()
    return result


def _decode(data: bytes) -> Message:
    if type(data) is not bytes or not 52 <= len(data) <= MAX_FRAME_BYTES:
        _fail()
    size, magic, version, kind, sequence, nonce = _HEADER.unpack_from(data)
    if size != len(data) - 4 or not 48 <= size <= MAX_FRAME_BYTES - 4:
        _fail()
    if magic != MAGIC or version != VERSION or nonce == b"\0" * 32:
        _fail()
    kind = _enum(kind, MessageType)
    _integer(sequence, 1)
    return Message(kind, sequence, nonce, _body_decode(kind, data[52:]), data)


def decode_message(data: bytes) -> Message:
    """Decode exact bytes only. This route performs no external I/O."""
    return _public(_decode, data)


def _encode(body: Body, nonce: bytes, sequence: int) -> bytes:
    _bytes(nonce, 32)
    if nonce == b"\0" * 32:
        _fail()
    _integer(sequence, 1)
    kind, encoded = _body_encode(body)
    wire = _HEADER.pack(48 + len(encoded), MAGIC, VERSION, kind, sequence, nonce) + encoded
    _decode(wire)
    return wire


def encode_message(body: Body, *, nonce: bytes, sequence: int) -> bytes:
    return _public(_encode, body, nonce, sequence)


def response_correlation(message: Message) -> Correlation:
    if type(message) is not Message or message.kind not in {
        MessageType.BOOTSTRAP, MessageType.WINDOW, MessageType.INVALIDATE,
    }:
        _fail("CORRELATION")
    # Re-decode: serialized Message instances are data, not admission seals.
    original = decode_message(message.wire)
    if original != message:
        _fail("CORRELATION")
    return Correlation(message.kind, message.sequence, message.sha256,
                       message.body.selected_epoch)


def native_v1_observation(window: Window) -> Window:
    """No configurable bypass: legacy OBS transport cannot prove upstream loss."""
    if type(window) is not Window:
        _fail("INVALID_VALUE")
    result = replace(window, capture_point=CapturePoint.CONTROLLER_FLOAT32_PRE_DRAW,
                     loss=Loss.UNKNOWN)
    _body_encode(result)
    return result


class OrderedReceiver:
    """One bounded direction; framing errors permanently close this receiver."""

    __slots__ = ("_nonce", "_sequence", "_types", "_closed")

    def __init__(self, *, allowed: tuple[MessageType, ...], nonce: bytes | None = None) -> None:
        if type(allowed) is not tuple or not allowed:
            _fail("INVALID_VALUE")
        self._types = frozenset(_enum(value, MessageType) for value in allowed)
        self._nonce = None if nonce is None else _bytes(nonce, 32)
        self._sequence = 0
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        self._closed = True

    def accept(self, data: bytes) -> Message:
        if self._closed:
            _fail("CLOSED")
        error = None
        message = None
        try:
            message = decode_message(data)
            if message.kind not in self._types or message.sequence != self._sequence + 1:
                _fail("SEQUENCE")
            if self._nonce is not None and message.nonce != self._nonce:
                _fail("CORRELATION")
        except ProtocolError as failure:
            error = failure.reason
        if error is not None:
            self.close()
            raise ProtocolError(error)
        self._nonce = message.nonce
        self._sequence = message.sequence
        return message


class FrameAccumulator:
    """Bounded fragmented input; caller supplies monotonic time, never sleeps."""

    __slots__ = ("_data", "_started", "_closed", "_timeout")

    def __init__(self, *, timeout_ns: int = 1_000_000_000) -> None:
        self._data = bytearray()
        self._started: int | None = None
        self._closed = False
        self._timeout = _integer(timeout_ns, 1)

    def close(self) -> None:
        self._closed = True
        self._data.clear()
        self._started = None

    def expire(self, now_ns: int) -> None:
        _integer(now_ns, maximum=2**63-1)
        if self._closed:
            _fail("CLOSED")
        if self._started is not None and (
            now_ns < self._started or now_ns - self._started >= self._timeout
        ):
            self.close()
            _fail("CLOSED")

    def feed(self, chunk: bytes, *, now_ns: int) -> tuple[Message, ...]:
        self.expire(now_ns)
        if type(chunk) is not bytes or len(chunk) > MAX_FRAME_BYTES:
            self.close()
            _fail("LIMIT")
        messages: list[Message] = []
        try:
            for value in chunk:
                if not self._data:
                    self._started = now_ns
                self._data.append(value)
                if len(self._data) >= 4:
                    size = struct.unpack_from("<I", self._data)[0]
                    if not 48 <= size <= MAX_FRAME_BYTES - 4:
                        _fail("LIMIT")
                    if len(self._data) == size + 4:
                        messages.append(decode_message(bytes(self._data)))
                        self._data.clear()
                        self._started = None
            return tuple(messages)
        except ProtocolError as error:
            reason = error.reason
        self.close()
        raise ProtocolError(reason)

    def eof(self) -> None:
        self.close()


@dataclass(frozen=True, slots=True)
class WindowJob:
    window: Window
    observed_ns: int
    generation: int


class LatestWindowScheduler:
    """Short-lock one-active/latest-one queue and explicit 250ms UI expiration.

    No callback, Project read, process wait or user function runs under the lock.
    A cancelled active slot remains owned until that exact job finishes.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._generation = 0
        self._current: WindowJob | None = None
        self._pending: WindowJob | None = None
        self._active: WindowJob | None = None
        self._projection: Projection | None = None
        self._closed = False

    def offer(self, window: Window, *, now_ns: int) -> None:
        if type(window) is not Window:
            _fail("INVALID_VALUE")
        _body_encode(window)
        _integer(now_ns, maximum=2**63-1)
        with self._lock:
            if self._closed:
                _fail("CLOSED")
            if self._current is not None:
                previous = self._current
                if now_ns < previous.observed_ns:
                    _fail("INVALID_NUMBER")
                if (window.correlation[:4] == previous.window.correlation[:4]
                        and window.ui_sequence <= previous.window.ui_sequence):
                    _fail("SEQUENCE")
            self._projection = None
            job = WindowJob(window, now_ns, self._generation)
            self._current = self._pending = job

    def take(self) -> WindowJob | None:
        with self._lock:
            if self._closed or self._active is not None:
                return None
            self._active, self._pending = self._pending, None
            return self._active

    def finish(self, job: WindowJob, projection: Projection | None, *, now_ns: int) -> bool:
        _integer(now_ns, maximum=2**63-1)
        with self._lock:
            if self._active is not job:
                _fail("CORRELATION")
            self._active = None
            valid = (
                not self._closed and self._current is job
                and job.generation == self._generation and type(projection) is Projection
                and projection.window_correlation == job.window.correlation
                and 0 <= now_ns - job.observed_ns < DISPLAY_DEADLINE_NS
            )
            if valid:
                self._projection = projection
            return bool(valid)

    def display(self, *, now_ns: int) -> Projection | None:
        _integer(now_ns, maximum=2**63-1)
        with self._lock:
            if (self._closed or self._current is None
                    or not 0 <= now_ns - self._current.observed_ns < DISPLAY_DEADLINE_NS):
                self._projection = None
            return self._projection

    def invalidate(self) -> None:
        with self._lock:
            self._generation += 1
            self._pending = self._current = self._projection = None

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._generation += 1
            self._pending = self._current = self._projection = None

    @property
    def occupancy(self) -> tuple[int, int]:
        with self._lock:
            return (int(self._active is not None), int(self._pending is not None))
