"""Injected Win32 call-order/fault evidence only: no Win32 API/process executed."""
from dataclasses import replace
from hashlib import sha256
import ast
from pathlib import Path
import pickle

import pytest

from ai_video_production import task048_meter_protocol as p
from ai_video_production import task048_windows_child_launch as m


def uid(n):
    return f"00000000-0000-4000-8000-{n:012x}"


def bootstrap():
    return p.encode_message(p.Bootstrap(
        uid(6), 1, b"x"*16, 4, b"a"*32,
        "meter-project", "C:\\Users\\example\\Documents\\c1-project"),
        nonce=bytes(range(32)), sequence=1)


def spec(role=m.Role.WORKER):
    return m.BundleSpec(
        "C:\\Users\\fixture\\bundle", "meter.exe",
        (m.BundleFile("meter.exe", b"a"*32), m.BundleFile("_internal\\meter.pyz", b"b"*32)),
        role)


class FakeOps:
    """Synthetic handles; none are accepted by an operating-system API."""
    def __init__(self, *, fail=None, tamper=None):
        self.audit = []
        self.handles = {}
        self.next_handle = 100
        self.open_handles = set()
        self.closed = []
        self.fail = fail
        self.failed_once = False
        self.tamper = tamper
        self.counts = {}
        self.exited = False
        self.process_args = None
        self.bootstrap_written = None
        self.process_receipt = None
        self.job = None

    def point(self, name):
        self.audit.append(name)
        self.counts[name] = self.counts.get(name, 0)+1
        if self.fail == name and not self.failed_once:
            self.failed_once = True
            raise RuntimeError("PRIVATE_ERROR_BODY_NOT_FOR_CALLER")

    def new(self, value):
        self.next_handle += 1
        handle = self.next_handle
        self.handles[handle] = value
        self.open_handles.add(handle)
        return handle

    def system_temp_root(self):
        self.point("system_temp_root")
        return "C:\\Users\\fixture\\AppData\\Local\\Temp"

    def windows_directory(self):
        self.point("windows_directory")
        return "C:\\Windows"

    def path_exists(self, path):
        self.point("path_exists")
        return self.tamper == "runtime_collision"

    def create_directory_new(self, path):
        self.point("create_directory_new")

    def open_file(self, path, **kwargs):
        self.point("open_file")
        directory = bool(kwargs["flags"] & m.FILE_FLAG_BACKUP_SEMANTICS)
        assert kwargs["creation"] == m.OPEN_EXISTING
        assert kwargs["flags"] & m.FILE_FLAG_OPEN_REPARSE_POINT
        assert kwargs["sharing"] == (3 if directory else 1)  # No DELETE sharing.
        assert kwargs["access"] == (m.FILE_READ_ATTRIBUTES if directory else m.GENERIC_READ)
        return self.new((path, directory))

    def set_inheritable(self, handle, value):
        self.point("set_inheritable")
        assert handle in self.open_handles

    def observe_file(self, handle):
        self.point("observe_file")
        path, directory = self.handles[handle]
        ident = m.FileIdentity(1, sha256(path.encode()).digest()[:16])
        attrs = m.FILE_ATTRIBUTE_DIRECTORY if directory else 0
        seen = self.counts.get("observe:"+str(handle), 0)+1
        self.counts["observe:"+str(handle)] = seen
        if path.endswith("meter.exe"):
            if self.tamper == "reparse":
                attrs |= m.FILE_ATTRIBUTE_REPARSE_POINT
            if self.tamper == "wrong_path":
                path = "C:\\Users\\foreign\\replacement.exe"
            if self.tamper == "replacement" and seen > 1:
                ident = m.FileIdentity(1, b"z"*16)
        return m.FileObservation(path, ident, attrs, 0 if directory else 1)

    def hash_file(self, handle):
        self.point("hash_file")
        path, directory = self.handles[handle]
        assert not directory
        if self.tamper == "wrong_hash":
            return b"z"*32
        return b"a"*32 if path.endswith("meter.exe") else b"b"*32

    def current_token(self):
        self.point("current_token")
        return m.TokenIdentity("S-1-5-21-123", 1, False)

    def create_pipes(self):
        self.point("create_pipes")
        return m.Pipes(*(self.new("pipe") for _ in range(6)))

    def startup(self, **kwargs):
        self.point("startup")
        assert kwargs["attribute"] == m.PROC_THREAD_ATTRIBUTE_HANDLE_LIST
        assert len(set(kwargs["inherited_handles"])) == 3
        assert kwargs["flags"] == m.STARTF_USESTDHANDLES
        return m.Startup(object(), kwargs["inherited_handles"])

    def delete_startup(self, startup):
        self.point("delete_startup")

    def create_suspended(self, **kwargs):
        self.point("create_suspended")
        self.process_args = kwargs
        assert kwargs["flags"] & m.CREATE_SUSPENDED
        assert kwargs["flags"] & m.EXTENDED_STARTUPINFO_PRESENT
        assert kwargs["flags"] & m.CREATE_UNICODE_ENVIRONMENT
        assert kwargs["inherit_handles"] is True
        assert kwargs["application"] == "C:\\Users\\fixture\\bundle\\meter.exe"
        assert "Documents" not in repr(kwargs)  # No private Project path before resume.
        self.process_receipt = m.CreatedProcess(self.new("process"), self.new("thread"), 700)
        if self.tamper == "invalid_process_handle":
            return replace(self.process_receipt, process=-1)
        return self.process_receipt

    def inspect_process(self, process):
        self.point("inspect_process")
        token = m.TokenIdentity("S-1-5-21-123", 1, False)
        image = self.process_args["application"]
        ident = m.FileIdentity(1, sha256(image.encode()).digest()[:16])
        created = 123456
        pid = 700
        if self.tamper == "sid":
            token = replace(token, sid="S-1-5-21-999")
        if self.tamper == "session":
            token = replace(token, session_id=2)
        if self.tamper == "elevation":
            token = replace(token, elevated=True)
        if self.tamper == "image_identity":
            ident = m.FileIdentity(2, b"z"*16)
        if self.tamper == "pid":
            pid = 999
        if self.tamper == "creation_time" and self.counts["inspect_process"] > 1:
            created += 1
        return m.ProcessObservation(pid, created, image, ident, token)

    def create_worker_job(self, **kwargs):
        self.point("create_worker_job")
        assert kwargs == {
            "flags": m.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | m.JOB_OBJECT_LIMIT_ACTIVE_PROCESS,
            "active_process_limit": 1,
        }
        self.job = self.new("job")
        return self.job

    def assign_job(self, job, process):
        self.point("assign_job")
        assert job == self.job and process == self.process_receipt.process

    def resume_thread(self, thread):
        self.point("resume_thread")
        assert thread == self.process_receipt.thread
        return 0 if self.tamper == "resume_count" else 1

    def write_bootstrap(self, pipe, data):
        self.point("write_bootstrap")
        assert self.audit.index("inspect_process") < self.audit.index("resume_thread")
        self.bootstrap_written = data

    def terminate_process(self, process):
        self.point("terminate_process")
        assert process == self.process_receipt.process
        assert process > 0  # Never the current-process pseudo handle.
        self.exited = True

    def wait_process(self, process, timeout_ms):
        self.point("wait_process")
        assert process == self.process_receipt.process
        assert 0 <= timeout_ms <= 1000
        return False if self.tamper == "cannot_reap" else self.exited

    def close_handle(self, handle):
        self.point("close_handle")
        assert handle in self.open_handles
        assert handle not in self.closed
        self.open_handles.remove(handle)
        self.closed.append(handle)
        if handle == self.job:
            self.exited = True


@pytest.mark.parametrize("role", list(m.Role))
def test_exact_suspended_identity_handle_job_resume_bootstrap_order(role):
    ops = FakeOps()
    receipt = m.SuspendedChildLauncher(ops).launch(spec(role), bootstrap())
    assert ops.bootstrap_written == bootstrap()
    assert ops.audit.index("inspect_process") < ops.audit.index("resume_thread") < ops.audit.index("write_bootstrap")
    assert ops.audit.count("inspect_process") == 2
    assert ops.audit.index("delete_startup") < ops.audit.index("resume_thread")
    if role is m.Role.WORKER:
        assert ops.audit.index("assign_job") < ops.audit.index("resume_thread")
        assert ops.process_args["flags"] & m.CREATE_NO_WINDOW
    else:
        assert "create_worker_job" not in ops.audit
        assert not ops.process_args["flags"] & m.CREATE_NO_WINDOW
    environment = ops.process_args["environment"]
    assert "PYTHONPATH" not in environment and "PYTHONHOME" not in environment
    assert environment["TEMP"] == environment["TMP"] == receipt.runtime_root
    assert environment["SystemRoot"] == "C:\\Windows"
    assert receipt.runtime_root.startswith("C:\\Users\\fixture\\AppData\\Local\\Temp\\bvp-task048-c1-")
    if role is m.Role.CONTROLLER:
        assert receipt.close_advisory() is False
        assert "terminate_process" not in ops.audit
        assert ops.open_handles  # Pins remain while recording process is alive.
        ops.exited = True
        assert receipt.poll_exit()
    else:
        assert receipt.close_advisory()
    assert not ops.open_handles


@pytest.mark.parametrize("point", [
    "system_temp_root", "open_file", "observe_file", "hash_file", "set_inheritable",
    "path_exists", "create_directory_new", "current_token", "create_pipes", "startup",
    "windows_directory", "create_suspended", "delete_startup", "inspect_process",
    "create_worker_job", "assign_job", "resume_thread", "write_bootstrap",
])
def test_all_injected_failure_points_have_no_early_disclosure_and_owned_cleanup(point):
    ops = FakeOps(fail=point)
    launcher = m.SuspendedChildLauncher(ops)
    with pytest.raises(m.LaunchError) as caught:
        launcher.launch(spec(), bootstrap())
    assert "PRIVATE" not in str(caught.value)
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None
    if point != "write_bootstrap":
        assert "write_bootstrap" not in ops.audit
    assert ops.bootstrap_written is None
    assert not ops.open_handles


@pytest.mark.parametrize("tamper", [
    "reparse", "wrong_path", "wrong_hash", "replacement", "sid", "session",
    "elevation", "image_identity", "pid", "creation_time", "resume_count",
])
def test_identity_replacement_and_peer_negatives_stop_before_bootstrap(tamper):
    ops = FakeOps(tamper=tamper)
    with pytest.raises(m.LaunchError):
        m.SuspendedChildLauncher(ops).launch(spec(), bootstrap())
    assert ops.bootstrap_written is None
    assert not ops.open_handles
    if tamper != "resume_count":
        assert "resume_thread" not in ops.audit


def test_invalid_process_pseudo_handle_is_never_terminated():
    ops = FakeOps(tamper="invalid_process_handle")
    with pytest.raises(m.LaunchError):
        m.SuspendedChildLauncher(ops).launch(spec(), bootstrap())
    assert "terminate_process" not in ops.audit
    assert "write_bootstrap" not in ops.audit


def test_runtime_collision_is_not_owned_residual_or_reused():
    ops = FakeOps(tamper="runtime_collision")
    with pytest.raises(m.LaunchError) as caught:
        m.SuspendedChildLauncher(ops).launch(spec(), bootstrap())
    assert "create_directory_new" not in ops.audit
    assert caught.value.residual_roots == ()
    assert not ops.open_handles


def test_unconfirmed_reap_retains_exact_pins_and_blocks_new_launch():
    ops = FakeOps(fail="inspect_process", tamper="cannot_reap")
    launcher = m.SuspendedChildLauncher(ops)
    with pytest.raises(m.LaunchError, match="CLEANUP"):
        launcher.launch(spec(), bootstrap())
    assert ops.open_handles
    count = len(ops.audit)
    with pytest.raises(m.LaunchError, match="CLEANUP"):
        launcher.launch(spec(), bootstrap())
    assert len(ops.audit) == count
    assert launcher.recover_owned_cleanup() is False
    ops.tamper = None
    assert launcher.recover_owned_cleanup()
    assert not ops.open_handles


def test_resumed_controller_bootstrap_error_does_not_kill_recording():
    ops = FakeOps(fail="write_bootstrap")
    launcher = m.SuspendedChildLauncher(ops)
    with pytest.raises(m.LaunchError, match="CLEANUP"):
        launcher.launch(spec(m.Role.CONTROLLER), bootstrap())
    assert "terminate_process" not in ops.audit
    assert ops.open_handles
    ops.exited = True
    assert launcher.recover_owned_cleanup()


@pytest.mark.parametrize("role", list(m.Role))
@pytest.mark.parametrize("case", ["unexpected_resume_count", "resume_exception"])
def test_uncertain_resume_never_terminates_controller_or_bypasses_worker_job(role, case):
    ops = (FakeOps(tamper="resume_count") if case == "unexpected_resume_count"
           else FakeOps(fail="resume_thread"))
    launcher = m.SuspendedChildLauncher(ops)
    with pytest.raises(m.LaunchError):
        launcher.launch(spec(role), bootstrap())
    assert "resume_thread" in ops.audit
    assert "terminate_process" not in ops.audit
    assert ops.bootstrap_written is None
    if role is m.Role.CONTROLLER:
        assert ops.open_handles  # Keep physical pins while execution is uncertain.
        before = len(ops.audit)
        with pytest.raises(m.LaunchError, match="CLEANUP"):
            launcher.launch(spec(role), bootstrap())
        assert len(ops.audit) == before
        assert not launcher.recover_owned_cleanup()
        ops.exited = True
        assert launcher.recover_owned_cleanup()
    else:
        assert ops.job is not None and ops.exited  # Only the owned pure-worker Job.
    assert not ops.open_handles


def test_proven_pre_resume_controller_identity_failure_still_reaps_owned_child():
    ops = FakeOps(fail="inspect_process")
    with pytest.raises(m.LaunchError):
        m.SuspendedChildLauncher(ops).launch(spec(m.Role.CONTROLLER), bootstrap())
    assert "resume_thread" not in ops.audit
    assert "terminate_process" in ops.audit
    assert ops.exited and not ops.open_handles


@pytest.mark.parametrize("root", ["C:\\", "C:\\bundle", "\\\\server\\share\\bundle",
                                "C:\\Users\\..\\bundle", "C:\\Users\\bundle\\"])
def test_bad_bundle_roots_stop_before_any_api(root):
    ops = FakeOps()
    with pytest.raises(m.LaunchError):
        m.SuspendedChildLauncher(ops).launch(replace(spec(), root=root), bootstrap())
    assert ops.audit == []


@pytest.mark.parametrize("relative", ["..\\evil.exe", "C:\\evil.exe", "meter.exe:ads",
                                     "CON", "dir\\LPT1.dll", "dir\\bad.", "dir/alt.exe"])
def test_bad_or_aliased_relative_paths_stop_before_api(relative):
    ops = FakeOps()
    bundle = replace(spec(), image_relative_path=relative,
                     files=(m.BundleFile(relative, b"a"*32),))
    with pytest.raises(m.LaunchError):
        m.SuspendedChildLauncher(ops).launch(bundle, bootstrap())
    assert ops.audit == []


def test_wrong_or_malformed_bootstrap_stops_before_api():
    for data in (b"bad", bootstrap()[:-1]):
        ops = FakeOps()
        with pytest.raises(m.LaunchError):
            m.SuspendedChildLauncher(ops).launch(spec(), data)
        assert ops.audit == []


def test_native_ownership_is_not_serializable():
    ops = FakeOps()
    receipt = m.SuspendedChildLauncher(ops).launch(spec(), bootstrap())
    with pytest.raises(TypeError):
        pickle.dumps(receipt)
    receipt.close_advisory()


def test_seam_does_not_load_native_dll_or_process_module():
    tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
    assert not {"ctypes", "subprocess", "multiprocessing"}.intersection(imports)
