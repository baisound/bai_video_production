"""C1 worker with real public synthetic Projects; injected filesystem identity only."""
from dataclasses import replace
import json
from pathlib import Path
import queue
import threading
import uuid

import pytest

from ai_video_production import task048_meter_protocol as p
from ai_video_production import task048_meter_worker as w
from ai_video_production import voice_quality_meter_policy_store as p1
from ai_video_production import voice_quality_meter_runtime_contract as p2
from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.voice_quality_meter_display_policy import MeterDisplayPolicyRevision

NONCE = bytes(range(32))


def uid():
    return str(uuid.uuid4())


def policy():
    return MeterDisplayPolicyRevision("meter-policy", 1, None, -24.0, -12.0, -3.0, 0.0).to_dict()


def apply(root, writer, action, payload):
    manifest = ProductProjectManifestStore.load(root)
    child = next((x for x in manifest.child_bindings if x.relative_path == p1.CHILD_PATH), None)
    request = {
        "record_type": "Task048MeterPolicyOperationRequestV1", "schema_version": 1,
        "canonical_owner_task": "TASK-048", "project_id": "meter-project",
        "operation_id": uid(), "action": action,
        "expected_project_revision": manifest.project_revision,
        "expected_project_manifest_sha256": manifest.project_manifest_sha256,
        "expected_child_sha256": None if child is None else child.content_sha256,
        "payload": payload,
    }
    request["request_sha256"] = sha256_bytes(p1.REQUEST_DOMAIN + canonical_json_bytes(request))
    return writer.apply(request)


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "synthetic-project"
    root.mkdir()
    ProductProjectManifestStore.save(root, ProductProjectManifest.create(
        project_id="meter-project", project_revision=1, product_version="0.23.0",
        timebase=ProjectTimebase(30, 1), child_bindings=(),
        created_at="2026-09-01T00:00:00.000Z", updated_at="2026-09-01T00:00:00.000Z",
    ))
    return root


class SyntheticPins:
    """Test-only POSIX/Windows fixture mapping, never a native admission claim."""
    def __init__(self, root):
        self.project_root = root
        info = root.stat()
        self.identity = (info.st_dev, info.st_ino)
        self.closed = False
        self.calls = 0
        self.fail = False

    def verify(self):
        self.calls += 1
        info = self.project_root.stat()
        if self.closed or self.fail or (info.st_dev, info.st_ino) != self.identity:
            raise w.BindingError(p.StatusCode.PROJECT_IDENTITY_CHANGED)

    def close(self):
        self.closed = True


class SyntheticInspector:
    def __init__(self, root):
        self.pins = SyntheticPins(root)
        self.bind_calls = 0
        self.fail = False

    def bind(self, bootstrap):
        self.bind_calls += 1
        if self.fail:
            raise ValueError("PRIVATE_PATH_MUST_NOT_ESCAPE")
        assert bootstrap.project_root == "C:\\Users\\fixture\\c1-project"
        assert (bootstrap.root_volume, bootstrap.root_file_id) == (
            self.pins.identity[0], self.pins.identity[1].to_bytes(16, "little"))
        self.pins.verify()
        return self.pins


def boot(root, inspector, **changes):
    manifest = ProductProjectManifestStore.load(root)
    return replace(p.Bootstrap(
        uid(), inspector.pins.identity[0], inspector.pins.identity[1].to_bytes(16, "little"),
        manifest.project_revision, bytes.fromhex(manifest.project_manifest_sha256[7:]),
        manifest.project_id, "C:\\Users\\fixture\\c1-project",
    ), **changes)


class Client:
    def __init__(self, root, *, selected=True, revoked=False):
        self.root = root
        self.writer = p1.MeterPolicyProjectStore(root, "meter-project")
        if selected:
            apply(root, self.writer, "BOOTSTRAP", {"policy_ref": "meter-policy"})
            apply(root, self.writer, "PUBLISH_POLICY", {"policy_document": policy()})
            apply(root, self.writer, "SELECT_POLICY", {
                "policy_revision_sha256": policy()["policy_revision_sha256"]})
            if revoked:
                apply(root, self.writer, "REVOKE_POLICY", {
                    "policy_revision_sha256": policy()["policy_revision_sha256"]})
        self.inspector = SyntheticInspector(root)
        self.bootstrap = boot(root, self.inspector)
        self.worker = w.MeterWorker(self.inspector)
        self.sequence = 0
        self.session, self.consumer, self.view = uid(), uid(), uid()

    def raw(self, body):
        self.sequence += 1
        return p.encode_message(body, nonce=NONCE, sequence=self.sequence)

    def send(self, body):
        return self.worker.process_frame(self.raw(body))

    def connect(self):
        return self.send(self.bootstrap)

    def window(self, *, ui_sequence=1, total=1, peak=-18.0, **changes):
        clips = int(peak >= p2.OBSERVED_CLIP_DBFS)
        metric = p.Metric(p.MetricState.FINITE, peak)
        return replace(p.Window(
            self.bootstrap.selected_epoch, self.session, self.consumer, self.view,
            ui_sequence, p.CapturePoint.CONTROLLER_FLOAT32_PRE_DRAW, False, p.Loss.UNKNOWN,
            p.WindowCounts(p.CountState.VALID, 1, 0, clips),
            p.SessionCounts(p.CountState.VALID, total, clips),
            metric, metric, metric,
        ), **changes)

    def close(self):
        self.worker.close()
        self.writer.close()


@pytest.fixture
def client(project):
    result = Client(project)
    try:
        yield result
    finally:
        result.close()


def test_selected_public_policy_genuine_projection_is_unknown_loss(client):
    ready = client.connect()
    assert type(ready) is p.Ready
    result = client.send(client.window())
    assert type(result) is p.Projection
    proof = p2.parse_meter_runtime_projection(result.canonical_projection)
    assert proof["policy_observation"]["window_policy_matched"] is True
    assert proof["display_band"] == "UNCONFIRMED"
    assert proof["reason_code"] == "OBSERVATION_LOSS_UNKNOWN"
    assert result.band is p.Band.UNCONFIRMED
    assert result.runtime_epoch == ready.runtime_epoch
    assert result.producer_epoch == ready.producer_epoch
    assert all(value is False for value in proof["authority"].values())
    assert proof["io_boundary"]["policy_or_project_write_executed"] is False


@pytest.mark.parametrize("selected,revoked,reason", [
    (False, False, "POLICY_NOT_BOUND"), (True, True, "POLICY_REVOKED"),
])
def test_public_not_bound_and_revoked_are_not_rehabilitated(project, selected, revoked, reason):
    client = Client(project, selected=selected, revoked=revoked)
    try:
        assert type(client.connect()) is p.Ready
        result = client.send(client.window())
        assert type(result) is p.Projection
        assert result.reason.name == reason
        assert result.band is p.Band.UNCONFIRMED
    finally:
        client.close()


def test_c1_ui_sequence_is_not_p2_ticket_sequence(client):
    client.connect()
    first = client.send(client.window())
    second = client.send(client.window(ui_sequence=9, total=2))
    assert first.p2_sequence == 1 and first.ui_sequence == 1
    assert second.p2_sequence == 2 and second.ui_sequence == 9
    assert second.request_id != first.request_id


@pytest.mark.parametrize("peak", [-0.0, 0.1, 6.0, 12.0, 18.0, float.fromhex("0x1.fffffffffffffp+1023")])
def test_positive_raw_metrics_preserved_without_quality_claim(client, peak):
    client.connect()
    result = client.send(client.window(peak=peak))
    proof = p2.parse_meter_runtime_projection(result.canonical_projection)
    assert proof["observation"]["window_peak"]["value_dbfs"] == peak
    assert result.band is p.Band.UNCONFIRMED


@pytest.mark.parametrize("change", ["id", "revision", "hash", "inspector"])
def test_bootstrap_binding_refused_before_ready(project, change):
    inspector = SyntheticInspector(project)
    body = boot(project, inspector)
    if change == "id":
        body = replace(body, project_id="different-project")
    elif change == "revision":
        body = replace(body, project_revision=body.project_revision+1)
    elif change == "hash":
        body = replace(body, manifest_sha256=b"x"*32)
    else:
        inspector.fail = True
    worker = w.MeterWorker(inspector)
    result = worker.process_frame(p.encode_message(body, nonce=NONCE, sequence=1))
    assert type(result) is p.Status and result.code is p.StatusCode.BOOTSTRAP_REJECTED
    assert worker.phase == "CLOSED"
    assert "PRIVATE_PATH" not in repr(result)


def test_no_project_io_before_frame_or_semantic_validation(client, monkeypatch):
    client.connect()
    reads = []
    real = ProductProjectManifestStore.load
    def watched(root):
        reads.append(root)
        return real(root)
    monkeypatch.setattr(ProductProjectManifestStore, "load", staticmethod(watched))
    impossible = client.window(window_peak=p.Metric(p.MetricState.FINITE, -20.0))
    # RMS -18 > peak -20 contradicts the public P2 observation contract.
    with pytest.raises(p.ProtocolError):
        client.send(impossible)
    assert reads == []


@pytest.mark.parametrize("loss", [p.Loss.NO_LOSS_REPORTED, p.Loss.LOSS_REPORTED])
def test_live_native_v1_route_has_no_loss_promotion_flag(client, loss):
    client.connect()
    with pytest.raises(p.ProtocolError):
        client.send(client.window(loss=loss))
    assert client.worker.phase == "CLOSED"


def test_unparsed_bootstrap_does_not_bind_or_read(project):
    inspector = SyntheticInspector(project)
    worker = w.MeterWorker(inspector)
    with pytest.raises(p.ProtocolError):
        worker.process_frame(b"not an admitted frame")
    assert inspector.bind_calls == 0


def test_current_head_change_refuses_old_classification(client):
    client.connect()
    apply(client.root, client.writer, "REVOKE_POLICY", {
        "policy_revision_sha256": policy()["policy_revision_sha256"]})
    result = client.send(client.window())
    assert type(result) is p.Status
    assert result.code is p.StatusCode.PROJECT_HEAD_CHANGED
    assert client.worker.phase == "CLOSED"


def test_root_identity_change_refuses_old_classification(client):
    client.connect()
    client.inspector.pins.fail = True
    result = client.send(client.window())
    assert result.code is p.StatusCode.PROJECT_IDENTITY_CHANGED
    assert client.worker.phase == "CLOSED"


def test_child_corruption_is_not_admitted_as_policy(client):
    client.connect()
    (client.root / p1.CHILD_PATH).write_bytes(b'{"corrupt":true}')
    result = client.send(client.window())
    assert type(result) is p.Projection
    assert result.band is p.Band.UNCONFIRMED
    proof = p2.parse_meter_runtime_projection(result.canonical_projection)
    assert proof["policy_observation"]["window_policy_matched"] is False
    assert proof["policy_observation"]["identity"] is None


def test_p1_readback_failure_is_body_free_unconfirmed(client, monkeypatch):
    client.connect()
    def broken(_store, _context):
        raise OSError("PRIVATE_PROJECT_NAME_AND_PATH")
    monkeypatch.setattr(p1.MeterPolicyProjectStore, "read_snapshot", broken)
    result = client.send(client.window())
    assert type(result) is p.Projection
    assert result.reason is p.P2Reason.POLICY_READBACK_FAILED
    assert b"PRIVATE_PROJECT" not in result.canonical_projection


def test_public_revalidation_stale_cannot_be_rehabilitated(client, monkeypatch):
    client.connect()
    real = p1.MeterPolicyProjectStore.revalidate
    def revoke_during_revalidation(store, snapshot, context):
        apply(client.root, client.writer, "REVOKE_POLICY", {
            "policy_revision_sha256": policy()["policy_revision_sha256"]})
        return real(store, snapshot, context)
    monkeypatch.setattr(p1.MeterPolicyProjectStore, "revalidate", revoke_during_revalidation)
    result = client.send(client.window())
    assert type(result) is p.Status
    assert result.code is p.StatusCode.PROJECT_HEAD_CHANGED
    assert client.worker.phase == "CLOSED"


def test_real_genuine_ticket_only_and_no_fixture_projection_injection(client, monkeypatch):
    client.connect()
    observed = []
    real = p2.MeterRuntimeController.project
    def spy(controller, ticket, request_bytes):
        assert type(ticket) is p2.MeterWindowTicket
        assert type(request_bytes) is bytes
        observed.append(ticket)
        return real(controller, ticket, request_bytes)
    monkeypatch.setattr(p2.MeterRuntimeController, "project", spy)
    result = client.send(client.window())
    assert type(result) is p.Projection and len(observed) == 1
    with pytest.raises(p.ProtocolError):
        client.send(result)  # RESULT is never an inbound worker request.


def test_pause_resume_new_epochs_preserve_session_history(client):
    client.connect()
    first = client.send(client.window())
    for index, (reason, paused) in enumerate([
        (p.InvalidationReason.PAUSED, True), (p.InvalidationReason.RESUMED, False),
        (p.InvalidationReason.RECONNECT, False),
    ], 2):
        client.consumer, client.view = uid(), uid()
        reply = client.send(p.Invalidate(
            client.bootstrap.selected_epoch, client.session, client.consumer,
            client.view, reason, paused))
        assert reply.code is p.StatusCode.INVALIDATED
        result = client.send(client.window(total=index, paused=paused))
        assert type(result) is p.Projection
        assert result.session_id == first.session_id
        proof = p2.parse_meter_runtime_projection(result.canonical_projection)
        assert proof["observation"]["session_counts"]["finite_sample_values"] == index


@pytest.mark.parametrize("reason", [p.InvalidationReason.PROJECT_CHANGED,
                                   p.InvalidationReason.READBACK_UNAVAILABLE,
                                   p.InvalidationReason.HOST_RESTORE_UNCERTAIN])
def test_terminal_invalidation_refuses_further_frames(client, reason):
    client.connect()
    client.send(client.window())
    result = client.send(p.Invalidate(
        client.bootstrap.selected_epoch, client.session, uid(), uid(), reason, False))
    assert result.code is p.StatusCode.INVALIDATED
    assert client.worker.phase == "CLOSED"
    with pytest.raises(p.ProtocolError):
        client.send(client.window(ui_sequence=2, total=2))


def test_reserved_window_cannot_be_overtaken_by_invalidation(client):
    client.connect()
    reserved = client.worker._receive(client.raw(client.window()))
    assert client.worker.busy
    client.consumer, client.view = uid(), uid()
    reply = client.send(p.Invalidate(
        client.bootstrap.selected_epoch, client.session, client.consumer,
        client.view, p.InvalidationReason.RECONNECT, False))
    assert reply.code is p.StatusCode.INVALIDATED
    assert client.worker._dispatch(reserved) is None
    assert not client.worker.busy
    assert type(client.send(client.window())) is p.Projection


def test_busy_has_no_history_advance_and_close_does_not_wait_for_p1(client, monkeypatch):
    client.connect()
    entered, release = threading.Event(), threading.Event()
    reads = []
    real = p1.MeterPolicyProjectStore.read_snapshot
    def slow(store, context):
        reads.append(context)
        entered.set()
        assert release.wait(3)
        return real(store, context)
    monkeypatch.setattr(p1.MeterPolicyProjectStore, "read_snapshot", slow)
    replies = []
    errors = []
    raw = client.raw(client.window())
    def evaluate():
        try:
            replies.append(client.worker.process_frame(raw))
        except Exception as error:
            errors.append(type(error))
    thread = threading.Thread(target=evaluate)
    thread.start()
    assert entered.wait(2)
    try:
        busy = client.send(client.window(ui_sequence=2, total=2))
        assert busy.code is p.StatusCode.P2_BUSY
        assert len(reads) == 1
        client.worker.eof()
        assert client.worker.phase == "CLOSED" and client.worker.busy
        assert not client.inspector.pins.closed
        with pytest.raises(p2.MeterRuntimeContractError, match="RUNTIME_BUSY"):
            p2.MeterRuntimeController(client.worker._store)
    finally:
        release.set()
        thread.join(3)
    assert not thread.is_alive() and not errors and replies == [None]
    assert not client.worker.busy and client.inspector.pins.closed


def test_explicit_close_frame_retains_no_future_admission(client):
    client.connect()
    assert client.send(p.Close(client.bootstrap.selected_epoch, p.CloseReason.USER_CLOSE)) is None
    assert client.worker.phase == "CLOSED"
    with pytest.raises(p.ProtocolError):
        client.send(client.window())


def test_no_policy_or_project_write_from_reader_route(client, monkeypatch):
    before = {path.relative_to(client.root): path.read_bytes()
              for path in client.root.rglob("*") if path.is_file()}
    def forbidden(*args, **kwargs):
        pytest.fail("C1 reader attempted a policy or Project write")
    monkeypatch.setattr(p1.MeterPolicyProjectStore, "apply", forbidden)
    monkeypatch.setattr(ProductProjectManifestStore, "save", forbidden)
    client.connect()
    client.send(client.window())
    client.worker.close()
    after = {path.relative_to(client.root): path.read_bytes()
             for path in client.root.rglob("*") if path.is_file()}
    assert after == before


@pytest.mark.parametrize("reused", ["consumer", "view"])
def test_unactivated_invalidation_epochs_cannot_be_reused(client, reused):
    client.connect()
    consumer, view = uid(), uid()
    client.send(p.Invalidate(client.bootstrap.selected_epoch, client.session,
        consumer, view, p.InvalidationReason.RECONNECT, False))
    with pytest.raises(p.ProtocolError):
        client.send(p.Invalidate(client.bootstrap.selected_epoch, client.session,
            consumer if reused == "consumer" else uid(),
            view if reused == "view" else uid(), p.InvalidationReason.RECONNECT, False))
    assert client.worker.phase == "CLOSED"


def test_queued_projection_is_not_current_after_next_window_or_invalidate(client):
    client.connect()
    first = client.send(client.window())
    assert client.worker.reply_is_current(first)
    second = client.send(client.window(ui_sequence=2, total=2))
    assert not client.worker.reply_is_current(first)
    assert client.worker.reply_is_current(second)
    client.send(p.Invalidate(client.bootstrap.selected_epoch, client.session,
        uid(), uid(), p.InvalidationReason.RECONNECT, False))
    assert not client.worker.reply_is_current(second)


class QueueReader:
    """Owned synthetic blocking pipe with explicit, nonblocking cancellation."""
    def __init__(self):
        self.chunks = queue.Queue()
        self.cancelled = threading.Event()
        self.read_started = threading.Event()
        self.read_again = threading.Event()
        self.read_count = 0

    def read(self, size):
        assert size == 4096
        self.read_count += 1
        self.read_started.set()
        if self.read_count > 1:
            self.read_again.set()
        return self.chunks.get(timeout=5)

    def cancel(self):
        self.cancelled.set()
        self.chunks.put_nowait(b"")


class QueueWriter:
    def __init__(self, failure=None):
        self.frames = queue.Queue()
        self.failure = failure

    def write(self, data):
        if self.failure == "exception":
            raise OSError("PRIVATE_PIPE_PATH")
        if self.failure == "short":
            return len(data) - 1
        self.frames.put_nowait(data)
        return len(data)

    def flush(self):
        pass


class StreamHarness:
    def __init__(self, client, *, failure=None):
        self.client = client
        self.reader, self.writer = QueueReader(), QueueWriter(failure)
        self.clock = 0
        self.errors = []
        self.thread = threading.Thread(target=self.run)

    def run(self):
        try:
            w.serve_metadata_stream(self.reader, self.writer, self.client.worker,
                cancel_read=self.reader.cancel, monotonic_ns=lambda: self.clock)
        except Exception as error:
            self.errors.append(error)

    def send(self, body):
        self.reader.chunks.put_nowait(self.client.raw(body))

    def result(self):
        return p.decode_message(self.writer.frames.get(timeout=5))

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *unused):
        self.reader.cancel()
        self.thread.join(5)
        assert not self.thread.is_alive()


def test_stream_genuine_bootstrap_window_and_private_eof(client):
    with StreamHarness(client) as stream:
        stream.send(client.bootstrap)
        ready = stream.result()
        assert type(ready.body) is p.Ready and ready.sequence == 1
        stream.send(client.window())
        result = stream.result()
        assert type(result.body) is p.Projection and result.sequence == 2
        assert result.body.reason is p.P2Reason.OBSERVATION_LOSS_UNKNOWN
        stream.reader.chunks.put_nowait(b"")
        stream.thread.join(3)
        assert not stream.thread.is_alive()
    assert not stream.errors
    assert client.worker.phase == "CLOSED"
    assert client.inspector.pins.closed


@pytest.mark.parametrize("partial", [False, True])
def test_stream_watchdog_cancels_owned_blocking_read(client, partial):
    with StreamHarness(client) as stream:
        if partial:
            stream.reader.chunks.put_nowait(client.raw(client.bootstrap)[:12])
            assert stream.reader.read_again.wait(2)
            stream.clock = 1_000_000_000
        else:
            assert stream.reader.read_started.wait(2)
            stream.clock = 5_000_000_000
        assert stream.reader.cancelled.wait(2)
        stream.thread.join(3)
        assert not stream.thread.is_alive()
    assert client.worker.phase == "CLOSED"
    assert client.inspector.bind_calls == 0


@pytest.mark.parametrize("failure", ["exception", "short"])
def test_stream_output_failure_cancels_reader_without_private_error(client, failure):
    with StreamHarness(client, failure=failure) as stream:
        stream.send(client.bootstrap)
        assert stream.reader.cancelled.wait(3)
        stream.thread.join(3)
        assert not stream.thread.is_alive()
    assert client.worker.phase == "CLOSED"
    assert all("PRIVATE" not in str(error) for error in stream.errors)


def test_stream_coalesced_busy_and_eof_preserve_lease_until_real_drain(client, monkeypatch):
    entered, release, drained = threading.Event(), threading.Event(), threading.Event()
    original = p1.MeterPolicyProjectStore.read_snapshot
    real_project = client.worker._project
    def slow(store, context):
        entered.set()
        assert release.wait(5)
        return original(store, context)
    def project(invocation):
        try:
            return real_project(invocation)
        finally:
            drained.set()
    monkeypatch.setattr(p1.MeterPolicyProjectStore, "read_snapshot", slow)
    monkeypatch.setattr(client.worker, "_project", project)
    try:
        with StreamHarness(client) as stream:
            stream.send(client.bootstrap)
            assert type(stream.result().body) is p.Ready
            stream.reader.chunks.put_nowait(client.raw(client.window())
                + client.raw(client.window(ui_sequence=2, total=2)))
            assert entered.wait(3)
            busy = stream.result().body
            assert type(busy) is p.Status and busy.code is p.StatusCode.P2_BUSY
            stream.reader.chunks.put_nowait(b"")
            stream.thread.join(3)
            assert not stream.thread.is_alive()
            assert client.worker.busy and not client.inspector.pins.closed
            with pytest.raises(p2.MeterRuntimeContractError, match="RUNTIME_BUSY"):
                p2.MeterRuntimeController(client.worker._store)
            release.set()
            assert drained.wait(3)
            assert not client.worker.busy and client.inspector.pins.closed
            assert stream.writer.frames.empty()
    finally:
        release.set()
        assert drained.wait(3)


def test_stream_requires_explicit_owned_read_cancellation(client):
    with pytest.raises(p.ProtocolError, match="INVALID_VALUE"):
        w.serve_metadata_stream(QueueReader(), QueueWriter(), client.worker, cancel_read=None)
