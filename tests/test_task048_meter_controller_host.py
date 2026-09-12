from __future__ import annotations

import ctypes as ct
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import threading
import time
from types import SimpleNamespace
import uuid

import pytest

from ai_video_production import task048_meter_controller_host as host
from ai_video_production import task048_meter_protocol as wire
from ai_video_production import task048_windows_child_launch as launch

ROOT = Path(__file__).resolve().parents[1]



class FakePinOperations:
    def __init__(self, *, fault=None):
        self.fault = fault
        self.next_handle = 100
        self.opened = {}
        self.closed = []
        self.inheritable = []
        self.fail_close = False

    def open_file(self, path, **kwargs):
        assert kwargs["creation"] == launch.OPEN_EXISTING
        assert kwargs["flags"] & launch.FILE_FLAG_OPEN_REPARSE_POINT
        assert kwargs["sharing"] == launch.FILE_SHARE_READ | launch.FILE_SHARE_WRITE
        self.next_handle += 1
        self.opened[self.next_handle] = path
        return self.next_handle

    def set_inheritable(self, handle, value):
        assert value is False
        self.inheritable.append(handle)
        if self.fault == "inherit":
            raise RuntimeError("private error")

    def observe_file(self, handle):
        path = self.opened[handle]
        attributes = launch.FILE_ATTRIBUTE_DIRECTORY
        identity = launch.FileIdentity(7, bytes([handle]) * 16)
        if self.fault == "reparse":
            attributes |= launch.FILE_ATTRIBUTE_REPARSE_POINT
        if self.fault == "alias":
            path += "changed"
        if self.fault == "identity":
            identity = launch.FileIdentity(8, bytes([handle]) * 16)
        return launch.FileObservation(path, identity, attributes, 0)

    def close_handle(self, handle):
        if self.fail_close:
            raise RuntimeError("private close error")
        self.closed.append(handle)


@pytest.mark.parametrize("root", ["C:\\", r"C:\direct-child", r"\\server\share\project",
                                   r"C:\Users\..\project", r"C:\Users\project.",
                                   r"C:\Users\project ", r"C:\Users\project:stream",
                                   "relative-project", "c:\\Users\\project"])
def test_project_root_rejection_precedes_handle_effects(root):
    operations = FakePinOperations()
    with pytest.raises(host.BindingError):
        host.WindowsProjectPins(operations, root)
    assert operations.opened == {}


@pytest.mark.parametrize("fault", ["inherit", "reparse", "alias"])
def test_project_pin_partial_failure_closes_exact_owned_handles(fault, monkeypatch):
    monkeypatch.setattr(host.ProductProjectManifestStore, "path",
                        lambda root: Path(root) / ".bai-project" / "project.json")
    operations = FakePinOperations(fault=fault)
    with pytest.raises(host.BindingError):
        host.WindowsProjectPins(operations, PROJECT_ROOT)
    assert operations.opened
    assert sorted(operations.opened) == sorted(operations.closed)


def test_project_pins_reverify_physical_identity_and_keep_unknown_close_owned(monkeypatch):
    monkeypatch.setattr(host.ProductProjectManifestStore, "path",
                        lambda root: Path(root) / ".bai-project" / "project.json")
    operations = FakePinOperations()
    pins = host.WindowsProjectPins(operations, PROJECT_ROOT)
    pins.verify()
    operations.fault = "identity"
    with pytest.raises(host.BindingError):
        pins.verify()
    operations.fault = None
    operations.fail_close = True
    with pytest.raises(host.BindingError):
        pins.close()
    assert pins._pins
    operations.fail_close = False
    pins.close()
    assert pins._pins == []
    with pytest.raises(host.BindingError):
        pins.verify()


def test_project_manifest_read_uses_real_public_store_and_short_lived_file_pin(tmp_path):
    from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
    from ai_video_production.product_project_store import ProductProjectManifestStore
    root = tmp_path / "synthetic-project"
    root.mkdir()
    manifest = ProductProjectManifest.create(
        project_id="meter-project", project_revision=1, product_version="0.23.0",
        timebase=ProjectTimebase(30, 1), child_bindings=(),
        created_at="2026-09-01T00:00:00.000Z", updated_at="2026-09-01T00:00:00.000Z")
    ProductProjectManifestStore.save(root, manifest)
    target = str(ProductProjectManifestStore.path(root))
    calls = []

    class Operations:
        def open_file(self, path, **kwargs):
            assert path == target
            assert kwargs["sharing"] == 7  # Including DELETE: advisory cannot block atomic saves.
            assert kwargs["access"] == launch.FILE_READ_ATTRIBUTES
            calls.append("open")
            return 9
        def observe_file(self, handle):
            assert handle == 9
            calls.append("observe")
            return launch.FileObservation(target, launch.FileIdentity(1, b"i"*16), 0, 1)
        def close_handle(self, handle):
            assert handle == 9
            calls.append("close")

    pins = SimpleNamespace(project_root=root, verify=lambda: calls.append("verify"))
    revision, digest = host.read_project_head(Operations(), pins, "meter-project")
    assert (revision, digest) == (1, bytes.fromhex(manifest.project_manifest_sha256[7:]))
    assert calls == ["verify", "open", "observe", "close", "open", "observe", "close", "verify"]
    with pytest.raises(host.BindingError):
        host.read_project_head(Operations(), pins, "other-project")
    assert calls[-2:] == ["close", "verify"]


def test_win32_function_signatures_are_bound_without_executing_native_api():
    class Library:
        def __init__(self):
            self.functions = {}
        def __getattr__(self, name):
            if name not in self.functions:
                self.functions[name] = SimpleNamespace()
            return self.functions[name]
    operations = object.__new__(host.Win32MeterOperations)
    operations._kernel, operations._security = Library(), Library()
    operations._bind_functions()
    kernel = operations._kernel.functions
    assert kernel["CreateProcessW"].restype is host._BOOL
    assert len(kernel["CreateProcessW"].argtypes) == 10
    assert kernel["GetStdHandle"].argtypes == [host._DWORD]
    assert kernel["GetFileInformationByHandleEx"].argtypes[1] is ct.c_int
    assert kernel["UpdateProcThreadAttribute"].argtypes[2] is host._SIZE_T
    assert kernel["GetCurrentProcess"].restype is host._HANDLE
    assert "OpenProcessToken" in operations._security.functions


def test_incomplete_pin_cleanup_blocks_host_reuse_until_exact_handles_close():
    instance, receipt, pins, _, _, _ = fake_host()
    count = []
    original = pins.close
    def delayed_close():
        count.append(1)
        if len(count) < 3:
            raise RuntimeError("synthetic delayed close")
        original()
    pins.close = delayed_close
    receipt.exited = True
    instance.open()
    wait_until(lambda: not instance._running)
    assert len(count) == 3 and pins.closed
    finish(instance, receipt)


@pytest.mark.parametrize("trigger", ["project_write", "close", "transport"])
def test_project_pins_survive_live_controller_then_failed_close_blocks_reuse(trigger):
    instance, receipt, pins, operations, launches, _ = fake_host()
    observed_poll, attempted_close, allow_close = (threading.Event() for _ in range(3))
    counts = []
    def poll():
        observed_poll.set()
        return receipt.exited
    def close_pins():
        counts.append(1)
        assert receipt.exited, "Project pins released before exact Controller exit"
        attempted_close.set()
        if not allow_close.is_set():
            raise RuntimeError("private close failure")
        pins.closed = True
    receipt.poll_exit = poll
    pins.close = close_pins
    try:
        instance.open()
        wait_until(lambda: instance.snapshot()["connected"])
        observed_poll.clear()
        if trigger == "project_write":
            with instance.project_write():
                pass
        elif trigger == "close":
            instance.close()
        else:
            operations.stderr = b"private transport failure"
        assert receipt.closed.wait(3) and observed_poll.wait(3)
        assert counts == [] and not pins.closed
        assert instance._running and not instance.snapshot()["can_open"]
        instance.open()
        assert len(launches) == 1
        receipt.exited = True
        assert attempted_close.wait(3)
        assert instance._running and not instance.snapshot()["can_open"] and not pins.closed
        allow_close.set()
        wait_until(lambda: not instance._running)
        assert pins.closed
    finally:
        allow_close.set()
        finish(instance, receipt)


def test_advisory_close_failure_does_not_skip_exit_poll_or_discard_project_pins():
    instance, receipt, pins, _, _, _ = fake_host()
    polled = threading.Event()
    def close_link():
        receipt.closed.set()
        raise RuntimeError("private pipe close failure")
    def poll():
        polled.set()
        return receipt.exited
    receipt.close_advisory, receipt.poll_exit = close_link, poll
    try:
        instance.open()
        wait_until(lambda: instance.snapshot()["connected"])
        polled.clear()
        instance.invalidate_before_project_write()
        assert receipt.closed.wait(3) and polled.wait(3)
        assert not pins.closed and instance._running
        receipt.exited = True
        wait_until(lambda: not instance._running)
        assert pins.closed
    finally:
        finish(instance, receipt)


@pytest.mark.parametrize("phase", ["initial", "periodic", "ready"])
@pytest.mark.parametrize("code,expected", [
    (wire.StatusCode.PROJECT_IDENTITY_CHANGED, "PROJECT_CHANGED"),
    (wire.StatusCode.PROJECT_HEAD_CHANGED, "PROJECT_CHANGED"),
    (wire.StatusCode.READBACK_UNAVAILABLE, "READBACK_UNAVAILABLE"),
    (wire.StatusCode.P2_BUSY, "TRANSPORT_FAILURE"),
])
def test_host_binding_failures_map_fixed_codes_at_every_head_admission(phase, code, expected):
    reads = []
    failing_read = {"initial": 1, "ready": 3, "periodic": 4}[phase]
    def read(*_):
        reads.append(1)
        if len(reads) == failing_read:
            error = host.BindingError(code)
            error.args = ("private path and exception text",)
            raise error
        return 4, b"h" * 32
    instance, receipt, _, _, launches, _ = fake_host(head_reader=read)
    try:
        instance.open()
        wait_until(lambda: instance.snapshot()["status"] == expected)
        assert not instance.snapshot()["connected"]
        assert "private" not in json.dumps(instance.snapshot())
        if phase == "initial":
            assert launches == []
        else:
            assert receipt.closed.wait(3)
    finally:
        finish(instance, receipt)


@pytest.mark.parametrize("fault", ["verify", "open", "observe", "close", "load"])
def test_manifest_api_failures_normalize_to_readback_unavailable(tmp_path, monkeypatch, fault):
    target = tmp_path / "project.json"
    monkeypatch.setattr(host.ProductProjectManifestStore, "path", lambda _root: target)
    monkeypatch.setattr(host.ProductProjectManifestStore, "load",
                        lambda _root: (_ for _ in ()).throw(OSError("private read error")))
    calls = []
    def point(name):
        calls.append(name)
        if fault == name:
            raise launch.LaunchError("API")
    class Operations:
        def open_file(self, *_args, **_kwargs): point("open"); return 7
        def observe_file(self, _handle):
            point("observe")
            return launch.FileObservation(str(target), launch.FileIdentity(1, b"i"*16), 0, 1)
        def close_handle(self, _handle): point("close")
    pins = SimpleNamespace(project_root=tmp_path, verify=lambda: point("verify"))
    with pytest.raises(host.BindingError) as error:
        host.read_project_head(Operations(), pins, "meter-project")
    assert error.value.code is wire.StatusCode.READBACK_UNAVAILABLE
    assert "private" not in str(error.value)
    if fault in ("observe", "close", "load"):
        assert "close" in calls


class PartialCreateKernel:
    """Inert PROCESS_INFORMATION injection; no real OS process or handle."""
    def __init__(self, *, thread=701, hold_exit=False):
        self.thread, self.hold_exit = thread, hold_exit
        self.exited = False
        self.fail_terminate = False
        self.fail_wait = False
        self.fail_close = set()
        self.calls = []
    def CreateProcessW(self, *args):
        self.calls.append(("create",))
        result = ct.cast(args[-1], ct.POINTER(host._ProcessInformation)).contents
        result.process, result.thread, result.pid = 700, self.thread, 77
        return True
    def TerminateProcess(self, process, code):
        assert process == 700 and code == 97
        self.calls.append(("terminate", process))
        if self.fail_terminate:
            raise RuntimeError("private termination failure")
        if not self.hold_exit:
            self.exited = True
        return True
    def WaitForSingleObject(self, process, timeout):
        assert process == 700 and 0 <= timeout <= 1000
        self.calls.append(("wait", process))
        if self.fail_wait:
            raise RuntimeError("private wait failure")
        return 0 if self.exited else 258
    def CloseHandle(self, handle):
        assert self.exited and handle in (700, 701)
        self.calls.append(("close", handle))
        return handle not in self.fail_close


def concrete_partial_operations(kernel):
    operations = object.__new__(host.Win32MeterOperations)
    operations._kernel = kernel
    operations._pending_creation = None
    return operations


def invoke_partial_create(operations):
    startup = launch.Startup((ct.create_string_buffer(32), None), (11, 12, 13))
    return operations.create_suspended(
        application=r"C:\Users\fixture\controller.exe", command_line="fixed",
        flags=launch.CREATE_SUSPENDED, inherit_handles=True,
        cwd=r"C:\Users\fixture\temp", environment={"TEMP": r"C:\Users\fixture\temp"},
        startup=startup)


@pytest.mark.parametrize("fault", ["invalid_thread", "record_constructor"])
def test_concrete_partial_create_owns_raw_process_before_fallible_validation(fault, monkeypatch):
    kernel = PartialCreateKernel(thread=0 if fault == "invalid_thread" else 701)
    operations = concrete_partial_operations(kernel)
    if fault == "record_constructor":
        def broken_record(*_):
            assert operations._pending_creation.receipt.process == 700
            raise RuntimeError("private record construction error")
        monkeypatch.setattr(launch, "CreatedProcess", broken_record)
    with pytest.raises(launch.LaunchError) as error:
        invoke_partial_create(operations)
    assert error.value.reason == "CREATE"
    assert kernel.calls[:3] == [("create",), ("terminate", 700), ("wait", 700)]
    assert ("close", 700) in kernel.calls
    assert (("close", 701) in kernel.calls) is (fault == "record_constructor")
    assert operations._pending_creation is None


def test_partial_create_uncertainty_pins_all_owned_handles_and_waits_despite_terminate_error():
    kernel = PartialCreateKernel(thread=0, hold_exit=True)
    kernel.fail_terminate = kernel.fail_wait = True
    operations = concrete_partial_operations(kernel)
    with pytest.raises(launch.LaunchError) as error:
        invoke_partial_create(operations)
    assert error.value.reason == "CLEANUP"
    assert kernel.calls[:3] == [("create",), ("terminate", 700), ("wait", 700)]
    with pytest.raises(launch.LaunchError):
        operations.close_handle(123)  # C1A image/ancestor pin: must not reach native close.
    with pytest.raises(launch.LaunchError):
        invoke_partial_create(operations)
    assert kernel.calls.count(("create",)) == 1
    kernel.fail_wait = False
    kernel.exited = True
    assert operations.recover_partial_creation()
    assert kernel.calls[-3:] == [("terminate", 700), ("wait", 700), ("close", 700)]
    assert operations._pending_creation is None


def test_partial_creation_failed_raw_close_retries_only_unclosed_handle(monkeypatch):
    kernel = PartialCreateKernel()
    kernel.fail_close.add(700)
    operations = concrete_partial_operations(kernel)
    monkeypatch.setattr(launch, "CreatedProcess", lambda *_: (_ for _ in ()).throw(ValueError("private")))
    with pytest.raises(launch.LaunchError) as error:
        invoke_partial_create(operations)
    assert error.value.reason == "CLEANUP"
    assert operations._pending_creation.thread_closed
    kernel.fail_close.clear()
    assert operations.recover_partial_creation()
    assert kernel.calls.count(("close", 701)) == 1
    assert kernel.calls.count(("terminate", 700)) == 1


def test_frozen_launcher_pins_survive_concrete_create_partial_success_until_backend_recovery():
    # Reuse the frozen inert A fixture; no test function or native API is executed.
    specification = importlib.util.spec_from_file_location(
        "c1a_inert_launch_fixture", ROOT / "tests/test_task048_windows_child_launch.py")
    fixture = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(fixture)
    kernel = PartialCreateKernel(thread=0, hold_exit=True)
    native = concrete_partial_operations(kernel)
    class Operations(fixture.FakeOps):
        def startup(self, **kwargs):
            prior = super().startup(**kwargs)
            return launch.Startup((ct.create_string_buffer(32), None), prior.inherited_handles, prior.flags)
        def create_suspended(self, **kwargs):
            return native.create_suspended(**kwargs)
        def close_handle(self, handle):
            if native._pending_creation is not None:
                raise launch.LaunchError("CLEANUP")
            return super().close_handle(handle)
    operations = Operations()
    launcher = launch.SuspendedChildLauncher(operations)
    with pytest.raises(launch.LaunchError) as error:
        launcher.launch(fixture.spec(launch.Role.CONTROLLER), fixture.bootstrap())
    assert error.value.reason == "CLEANUP"
    assert len(operations.open_handles) > 6 and operations.closed == []
    assert not any(item[0] == "close" for item in kernel.calls)
    with pytest.raises(launch.LaunchError):
        launcher.recover_owned_cleanup()  # Cannot release pins ahead of concrete receipt recovery.
    kernel.exited = True
    assert native.recover_partial_creation()
    assert operations.closed == []
    assert launcher.recover_owned_cleanup()
    assert operations.open_handles == set()


def test_host_shutdown_hook_runs_after_success_and_failure(monkeypatch):
    from ai_video_production import task036_packaged_entry as entry
    calls = []
    monkeypatch.setattr(entry, "close_packaged_meter_hosts", lambda: calls.append("closed"))
    class Guard:
        def acquire(self):
            from contextlib import nullcontext
            return nullcontext()
    for fail in (False, True):
        def main(_):
            if fail:
                raise RuntimeError("synthetic")
            return 0
        result = entry.packaged_main(
            [], probe=SimpleNamespace(require_ready=lambda: None),
            instance_guard=Guard(), presenter=lambda *_: None, app_main=main)
        assert result == (2 if fail else 0)
    assert calls == ["closed", "closed"]
PROJECT_ROOT = r"C:\Users\example\Documents\private-meter-project"


def identifier():
    return str(uuid.uuid4())


def bootstrap():
    return wire.decode_message(wire.encode_message(
        wire.Bootstrap(identifier(), 7, b"i" * 16, 4, b"h" * 32, "meter-project", PROJECT_ROOT),
        nonce=b"n" * 32, sequence=1))


def ready(request):
    selected = request.body
    return wire.Ready(wire.response_correlation(request), selected.project_revision,
                      selected.manifest_sha256, selected.root_volume, selected.root_file_id,
                      identifier(), identifier())


def message(body, request, **changes):
    return wire.decode_message(wire.encode_message(
        body, nonce=changes.get("nonce", request.nonce), sequence=changes.get("sequence", 1)))


def wait_until(predicate):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError("bounded fake-host wait expired")


class Pins:
    identity = launch.FileIdentity(7, b"i" * 16)

    def __init__(self, *_args):
        self.closed = False

    def close(self):
        self.closed = True


class FakeOperations:
    def __init__(self):
        self.chunks = []
        self.stderr = None

    def read_pipe_available(self, pipe, maximum=4096):
        if pipe == 2:
            return self.stderr
        if self.chunks:
            return self.chunks.pop(0)
        return None


class Receipt:
    pipes = SimpleNamespace(parent_stdout=1, parent_stderr=2)

    def __init__(self):
        self.closed = threading.Event()
        self.exited = False

    def close_advisory(self):
        self.closed.set()

    def poll_exit(self):
        return self.exited


def fake_host(*, response=None, head_reader=None, launch_hook=None):
    operations, receipt, pins = FakeOperations(), Receipt(), Pins()
    launches = []
    selected_head = [4, b"h" * 32]

    class Launcher:
        def __init__(self, operations):
            self.operations = operations

        def launch(self, spec, raw):
            request = wire.decode_message(raw)
            launches.append(request)
            if launch_hook:
                launch_hook(self.operations, request)
            if response is None:
                operations.chunks.append(message(ready(request), request).wire)
            else:
                operations.chunks.extend(response(request))
            return receipt

        def recover_owned_cleanup(self):
            return True

    result = host.MeterControllerHost(
        host.SelectedProject(PROJECT_ROOT, "meter-project"), object(),
        operations_factory=lambda: operations, pins_factory=lambda *_: pins,
        head_reader=head_reader or (lambda *_: tuple(selected_head)),
        launcher_factory=Launcher)
    return result, receipt, pins, operations, launches, selected_head


def finish(instance, receipt):
    receipt.exited = True
    instance.close()
    if instance._thread:
        instance._thread.join(3)
        assert not instance._thread.is_alive()


def test_host_does_not_launch_until_explicit_open_and_never_exposes_binding():
    instance, receipt, pins, _, launches, _ = fake_host()
    assert launches == []
    snapshot = instance.snapshot()
    assert snapshot["can_open"] and not snapshot["connected"]
    assert PROJECT_ROOT not in repr(instance._selection)
    assert "private-meter-project" not in json.dumps(snapshot)
    assert snapshot["quality_pass"] is False
    instance.open()
    wait_until(lambda: instance.snapshot()["connected"])
    assert len(launches) == 1
    instance.open()
    assert len(launches) == 1
    finish(instance, receipt)
    assert pins.closed


def test_project_write_invalidates_immediately_without_waiting_for_stalled_reader():
    entered, release = threading.Event(), threading.Event()
    calls = []

    def read(*_):
        calls.append(1)
        if len(calls) == 4:
            entered.set()
            assert release.wait(3)
        return 4, b"h" * 32

    instance, receipt, _, _, launches, _ = fake_host(head_reader=read)
    try:
        instance.open()
        wait_until(lambda: instance.snapshot()["connected"])
        assert entered.wait(3)
        started = time.monotonic()
        with instance.project_write():
            assert instance.snapshot()["status"] == "PROJECT_CHANGED"
            assert not instance.snapshot()["can_open"]
            instance.open()
            assert len(launches) == 1
        assert time.monotonic() - started < 0.5
        assert receipt.closed.wait(1)
    finally:
        release.set()
        finish(instance, receipt)


def test_project_change_clears_connection_but_retains_controller_until_its_exit():
    instance, receipt, _, _, launches, selected_head = fake_host()
    try:
        instance.open()
        wait_until(lambda: instance.snapshot()["connected"])
        selected_head[0] = 5
        wait_until(lambda: instance.snapshot()["status"] == "PROJECT_CHANGED")
        assert receipt.closed.wait(1)
        assert not instance.snapshot()["can_open"]
        instance.open()
        assert len(launches) == 1
        receipt.exited = True
        wait_until(lambda: instance.snapshot()["can_open"])
    finally:
        finish(instance, receipt)


@pytest.mark.parametrize("kind", ["duplicate", "wrong_nonce", "wrong_head", "reject", "stderr", "eof"])
def test_transport_failures_are_safe_fixed_states(kind):
    def response(request):
        valid = message(ready(request), request).wire
        if kind == "duplicate":
            return [valid + valid]
        if kind == "wrong_nonce":
            return [message(ready(request), request, nonce=b"x" * 32).wire]
        if kind == "wrong_head":
            return [message(replace(ready(request), project_revision=5), request).wire]
        if kind == "reject":
            return [message(wire.Status(wire.response_correlation(request),
                                        wire.StatusCode.BOOTSTRAP_REJECTED), request).wire]
        return [b""] if kind == "eof" else [valid]

    instance, receipt, _, operations, _, _ = fake_host(response=response)
    if kind == "stderr":
        operations.stderr = b"private-error"
    try:
        instance.open()
        assert receipt.closed.wait(3)
        expected = "BOOTSTRAP_REJECTED" if kind == "reject" else "TRANSPORT_FAILURE"
        assert instance.snapshot()["status"] == expected
        assert not instance.snapshot()["connected"]
        assert "private-error" not in json.dumps(instance.snapshot())
    finally:
        finish(instance, receipt)


def test_fragmented_ready_is_accepted_without_payload_persistence():
    def fragments(request):
        frame = message(ready(request), request).wire
        return [frame[:7], frame[7:]]
    instance, receipt, _, _, _, _ = fake_host(response=fragments)
    try:
        instance.open()
        wait_until(lambda: instance.snapshot()["connected"])
        assert instance.snapshot()["quality_pass"] is False
    finally:
        finish(instance, receipt)


def test_ready_exact_correlation_checks():
    request = bootstrap()
    value = ready(request)
    assert host.MeterControllerHost._admit_ready(message(value, request), request)
    for body in (replace(value, root_volume=8), replace(value, root_file_id=b"x"*16),
                 replace(value, manifest_sha256=b"x"*32),
                 replace(value, correlation=replace(value.correlation, source_sha256=b"x"*32))):
        with pytest.raises(wire.ProtocolError):
            host.MeterControllerHost._admit_ready(message(body, request), request)
    with pytest.raises(wire.ProtocolError):
        host.MeterControllerHost._admit_ready(message(value, request, sequence=2), request)


@pytest.mark.parametrize("name", ["create_suspended", "resume_thread", "write_bootstrap"])
def test_cancelled_admission_has_no_launch_effect(name):
    calls = []
    operations = SimpleNamespace(**{name: lambda *a, **k: calls.append((a, k))})
    stop = threading.Event()
    guarded = host._AdmissionOperations(operations, threading.RLock(), stop)
    getattr(guarded, name)(1)
    assert len(calls) == 1
    stop.set()
    with pytest.raises(launch.LaunchError):
        getattr(guarded, name)(2)
    assert len(calls) == 1


def test_project_write_blocks_launch_even_before_receipt_is_published():
    gate, release = threading.Event(), threading.Event()
    effects = []
    operations = SimpleNamespace(write_bootstrap=lambda *args: effects.append(args))

    def launch_hook(_operations, request):
        gate.set()
        assert release.wait(3)
        host._AdmissionOperations(operations, instance._lock, instance._stop).write_bootstrap(1, b"data")

    instance, receipt, _, _, _, _ = fake_host(launch_hook=launch_hook)
    try:
        instance.open()
        assert gate.wait(3)
        with instance.project_write():
            release.set()
        wait_until(lambda: not instance._running)
        assert effects == []
        assert instance.snapshot()["status"] == "PROJECT_CHANGED"
    finally:
        release.set()
        finish(instance, receipt)


def test_launch_failure_recovers_owned_cleanup_without_killing_recording():
    recoveries = []

    class Broken:
        def __init__(self, *_): pass
        def launch(self, *_): raise RuntimeError("private launch failure")
        def recover_owned_cleanup(self):
            recoveries.append(1)
            return len(recoveries) >= 2

    instance, receipt, pins, *_ = fake_host()
    instance._launcher_factory = Broken
    instance.open()
    wait_until(lambda: not instance._running)
    assert len(recoveries) == 2 and pins.closed
    assert instance.snapshot()["status"] == "TRANSPORT_FAILURE"
    finish(instance, receipt)


def test_win32_structures_have_exact_x64_layout():
    if ct.sizeof(ct.c_void_p) != 8:
        pytest.skip("x64-specific ABI")
    assert ct.sizeof(host._StartupInfo) == 104
    assert ct.sizeof(host._StartupInfoEx) == 112
    assert ct.sizeof(host._SecurityAttributes) == 24
    assert ct.sizeof(host._ProcessInformation) == 24
    assert ct.sizeof(host._JobExtendedLimit) == 144
    assert ct.sizeof(host._FileIdInfo) == 24


@pytest.mark.parametrize("value", [0, None, -1, ct.c_void_p(-1).value, ct.c_void_p(-2).value, 2**63])
def test_invalid_windows_handles_fail_closed(value):
    with pytest.raises(launch.LaunchError):
        host.Win32MeterOperations._handle(value)


def test_partial_project_pin_binding_retains_exact_handles_and_blocks_inspector_reuse(monkeypatch):
    monkeypatch.setattr(host.ProductProjectManifestStore, "path",
                        lambda root: Path(root) / ".bai-project" / "project.json")
    operations = FakePinOperations(fault="inherit")
    operations.fail_close = True
    inspector = host.WindowsProjectInspector(operations)
    with pytest.raises(host.BindingError) as error:
        inspector.bind(bootstrap().body)
    assert error.value.code is wire.StatusCode.READBACK_UNAVAILABLE
    assert inspector._pending is error.value.pending_pins
    opened = dict(operations.opened)
    with pytest.raises(host.BindingError):
        inspector.bind(bootstrap().body)
    assert operations.opened == opened and operations.closed == []
    operations.fail_close = False
    inspector._pending.close()
    assert sorted(operations.closed) == sorted(opened)


def test_host_failed_root_bind_keeps_pending_pins_until_exact_cleanup(monkeypatch):
    monkeypatch.setattr(host.ProductProjectManifestStore, "path",
                        lambda root: Path(root) / ".bai-project" / "project.json")
    operations = FakePinOperations(fault="inherit")
    operations.fail_close = True
    instance, receipt, _, _, launches, _ = fake_host()
    instance._operations_factory = lambda: operations
    instance._pins_factory = host.WindowsProjectPins
    try:
        instance.open()
        wait_until(lambda: instance.snapshot()["status"] == "READBACK_UNAVAILABLE")
        assert instance._running and not instance.snapshot()["can_open"]
        assert len(operations.opened) == 1 and operations.closed == [] and launches == []
        operations.fail_close = False
        wait_until(lambda: not instance._running)
        assert sorted(operations.closed) == sorted(operations.opened)
    finally:
        operations.fail_close = False
        finish(instance, receipt)


def test_unfrozen_source_cannot_select_controller_from_path_or_environment(monkeypatch):
    monkeypatch.setattr(host.sys, "frozen", False, raising=False)
    monkeypatch.setenv("BVP_TASK048_CONTROLLER_EXE", r"C:\foreign\controller.exe")
    assert host.packaged_meter_host(Path("private"), "project") is None


@pytest.mark.parametrize("args", [[], ["--bvp-meter-worker-v1"], ["--help"],
                                ["--bvp-meter-worker-v1", "path"]])
def test_private_worker_entry_refuses_unfrozen_or_user_supplied_modes(args, monkeypatch):
    entry = ROOT / "packaging/task048_meter_worker_windows_entry.py"
    spec = importlib.util.spec_from_file_location("private_meter_entry", entry)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.sys, "frozen", False, raising=False)
    assert module.main(args) == 64
