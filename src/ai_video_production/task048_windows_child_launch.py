"""TASK-048 C1 injected Win32 suspended-admission seam.

This module is deliberately not a ctypes runtime bootstrap: all Win32 operations
are supplied by the trusted packaged host. C1A tests use deterministic operations
and never execute Windows APIs/processes. The operation contract names the exact
Win32 primitives the production backend must implement and C must verify.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import PureWindowsPath
import re
from typing import Any, Protocol
import uuid

from . import task048_meter_protocol as wire

GENERIC_READ = 0x80000000
FILE_READ_ATTRIBUTES = 0x80
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
OPEN_EXISTING = 3
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
FILE_ATTRIBUTE_DIRECTORY = 0x10
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
CREATE_SUSPENDED = 0x4
CREATE_UNICODE_ENVIRONMENT = 0x400
EXTENDED_STARTUPINFO_PRESENT = 0x80000
CREATE_NO_WINDOW = 0x08000000
STARTF_USESTDHANDLES = 0x100
PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x00020002
JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x8
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000


class LaunchError(ValueError):
    def __init__(self, reason: str, *, residual_roots: tuple[str, ...] = ()) -> None:
        self.reason = reason if reason in {
            "SPEC", "PATH", "IDENTITY", "HANDLE", "CREATE", "TOKEN", "JOB",
            "RESUME", "BOOTSTRAP", "CLEANUP", "API",
        } else "API"
        self.residual_roots = residual_roots
        super().__init__("ERR_TASK048_C1_LAUNCH_" + self.reason)


class Role(str, Enum):
    CONTROLLER = "controller"
    WORKER = "worker"


@dataclass(frozen=True, slots=True)
class FileIdentity:
    volume: int
    file_id: bytes


@dataclass(frozen=True, slots=True)
class FileObservation:
    final_path: str
    identity: FileIdentity
    attributes: int
    size: int


@dataclass(frozen=True, slots=True)
class BundleFile:
    relative_path: str
    sha256: bytes


@dataclass(frozen=True, slots=True)
class BundleSpec:
    root: str
    image_relative_path: str
    files: tuple[BundleFile, ...]
    role: Role


@dataclass(frozen=True, slots=True)
class TokenIdentity:
    sid: str
    session_id: int
    elevated: bool


@dataclass(frozen=True, slots=True)
class CreatedProcess:
    process: int
    thread: int
    pid: int


@dataclass(frozen=True, slots=True)
class ProcessObservation:
    pid: int
    creation_time: int
    image_path: str
    image_identity: FileIdentity
    token: TokenIdentity


@dataclass(frozen=True, slots=True)
class Pipes:
    parent_stdin: int
    parent_stdout: int
    parent_stderr: int
    child_stdin: int
    child_stdout: int
    child_stderr: int

    @property
    def child_handles(self) -> tuple[int, int, int]:
        return self.child_stdin, self.child_stdout, self.child_stderr

    @property
    def parent_handles(self) -> tuple[int, int, int]:
        return self.parent_stdin, self.parent_stdout, self.parent_stderr


@dataclass(frozen=True, slots=True)
class Startup:
    attribute_list: Any
    inherited_handles: tuple[int, int, int]
    flags: int = STARTF_USESTDHANDLES


class WindowsOperations(Protocol):
    """Trusted backend requirements; none may shell out or fall back to Popen.

    open_file: CreateFileW, OPEN_EXISTING, security inheritance FALSE.
    observe_file: GetFileInformationByHandleEx(FILE_ID_INFO/attributes) and
      GetFinalPathNameByHandleW normalized DOS path, never path-only stat.
    create_pipes: three CreatePipe pairs, all failure intermediates closed.
    startup: InitializeProcThreadAttributeList/UpdateProcThreadAttributeList
      with exactly PROC_THREAD_ATTRIBUTE_HANDLE_LIST and three child handles;
      any unsuccessful setup releases its own partial attribute allocation.
    create_suspended: CreateProcessW with non-NULL absolute lpApplicationName,
      explicit STARTUPINFOEX, bInheritHandles TRUE, non-inheritable process and
      thread security handles; return the actual PROCESS_INFORMATION receipt.
    inspect_process: GetProcessId/GetProcessTimes/QueryFullProcessImageNameW,
      pinned reopened image FILE_ID_INFO and TokenUser/TokenSessionId/TokenElevation.
    create_worker_job: CreateJobObjectW + SetInformationJobObject with the exact
      supplied flags and active-process limit 1; no inheritable/named Job.
    No native backend is executed or represented as verified by C1A.
    """

    def system_temp_root(self) -> str: ...
    def windows_directory(self) -> str: ...
    def path_exists(self, path: str) -> bool: ...
    def create_directory_new(self, path: str) -> None: ...
    def open_file(self, path: str, *, access: int, sharing: int, creation: int, flags: int) -> int: ...
    def observe_file(self, handle: int) -> FileObservation: ...
    def hash_file(self, handle: int) -> bytes: ...
    def set_inheritable(self, handle: int, value: bool) -> None: ...
    def current_token(self) -> TokenIdentity: ...
    def create_pipes(self) -> Pipes: ...
    def startup(self, *, attribute: int, inherited_handles: tuple[int, int, int], flags: int) -> Startup: ...
    def delete_startup(self, startup: Startup) -> None: ...
    def create_suspended(self, *, application: str, command_line: str, flags: int,
                         inherit_handles: bool, cwd: str, environment: dict[str, str],
                         startup: Startup) -> CreatedProcess: ...
    def inspect_process(self, process: CreatedProcess) -> ProcessObservation: ...
    def create_worker_job(self, *, flags: int, active_process_limit: int) -> int: ...
    def assign_job(self, job: int, process: int) -> None: ...
    def resume_thread(self, thread: int) -> int: ...
    def write_bootstrap(self, pipe: int, data: bytes) -> None: ...
    def terminate_process(self, process: int) -> None: ...
    def wait_process(self, process: int, timeout_ms: int) -> bool: ...
    def close_handle(self, handle: int) -> None: ...


def _fail(reason: str) -> Any:
    raise LaunchError(reason)


def _int(value: Any, *, minimum: int = 0, maximum: int = 2**64-1) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        _fail("IDENTITY")
    return value


def _identity(value: Any) -> FileIdentity:
    if type(value) is not FileIdentity:
        _fail("IDENTITY")
    _int(value.volume)
    if type(value.file_id) is not bytes or len(value.file_id) != 16:
        _fail("IDENTITY")
    return value


def _token(value: Any) -> TokenIdentity:
    if type(value) is not TokenIdentity or type(value.sid) is not str:
        _fail("TOKEN")
    if not re.fullmatch(r"S-1-(?:[0-9]+-)*[0-9]+", value.sid) or len(value.sid) > 184:
        _fail("TOKEN")
    _int(value.session_id, maximum=2**32-1)
    if value.elevated is not False:
        _fail("TOKEN")
    return value


def _parts_safe(parts: tuple[str, ...]) -> bool:
    reserved = {"con", "prn", "aux", "nul"} | {
        f"{prefix}{number}" for prefix in ("com", "lpt") for number in range(1, 10)}
    return all(part and part not in (".", "..") and not part.endswith((" ", "."))
               and part.split(".")[0].lower() not in reserved
               and not any(ord(c) < 32 or c in '<>:"|?*' for c in part)
               for part in parts)


def _root(path: Any) -> PureWindowsPath:
    if type(path) is not str or not re.match(r"^[A-Z]:\\", path):
        _fail("PATH")
    result = PureWindowsPath(path)
    if str(result) != path or len(result.parts) < 3 or not _parts_safe(result.parts[1:]):
        _fail("PATH")
    return result


def _relative(value: Any) -> str:
    if type(value) is not str:
        _fail("PATH")
    parsed = PureWindowsPath(value)
    if parsed.is_absolute() or parsed.drive or str(parsed) != value or not _parts_safe(parsed.parts):
        _fail("PATH")
    return value


def _spec(value: Any) -> tuple[PureWindowsPath, dict[str, bytes]]:
    if type(value) is not BundleSpec or type(value.role) is not Role:
        _fail("SPEC")
    root = _root(value.root)
    image = _relative(value.image_relative_path)
    if type(value.files) is not tuple or not 1 <= len(value.files) <= 4096:
        _fail("SPEC")
    files: dict[str, bytes] = {}
    folded: set[str] = set()
    for item in value.files:
        if type(item) is not BundleFile:
            _fail("SPEC")
        path = _relative(item.relative_path)
        if path.casefold() in folded or type(item.sha256) is not bytes or len(item.sha256) != 32:
            _fail("SPEC")
        folded.add(path.casefold())
        files[path] = item.sha256
    if image not in files:
        _fail("SPEC")
    return root, files


class _Handles:
    def __init__(self, operations: WindowsOperations) -> None:
        self.ops = operations
        self.open: set[int] = set()

    def own(self, handle: int) -> int:
        _int(handle, minimum=1, maximum=2**63-1)
        if handle in self.open:
            _fail("HANDLE")
        self.open.add(handle)
        return handle

    def close(self, handle: int | None) -> None:
        if handle is not None and handle in self.open:
            self.ops.close_handle(handle)
            self.open.remove(handle)

    def close_all(self) -> None:
        failure = False
        for handle in tuple(self.open):
            try:
                self.close(handle)
            except Exception:
                failure = True
        if failure:
            _fail("CLEANUP")


@dataclass(frozen=True, slots=True)
class _Pin:
    handle: int
    observation: FileObservation
    digest: bytes | None


def _observe(ops: WindowsOperations, handle: int, path: str, directory: bool) -> FileObservation:
    observation = ops.observe_file(handle)
    if type(observation) is not FileObservation:
        _fail("IDENTITY")
    _identity(observation.identity)
    _int(observation.attributes, maximum=2**32-1)
    _int(observation.size)
    if (observation.final_path != path
            or observation.attributes & FILE_ATTRIBUTE_REPARSE_POINT
            or bool(observation.attributes & FILE_ATTRIBUTE_DIRECTORY) is not directory):
        _fail("IDENTITY")
    return observation


class LaunchReceipt:
    """Non-serializable ownership retained until explicit observed child exit."""

    def __init__(self, *, handles: _Handles, process: CreatedProcess, pipes: Pipes,
                 pins: tuple[_Pin, ...], job: int | None, runtime_root: str,
                 role: Role, identity: ProcessObservation) -> None:
        self._handles, self._process, self._pipes = handles, process, pipes
        self._pins, self._job, self._role = pins, job, role
        self._identity = identity
        self.runtime_root = runtime_root
        self._finished = False

    def __copy__(self) -> Any:
        raise TypeError("Native ownership cannot be copied")

    def __deepcopy__(self, memo: Any) -> Any:
        raise TypeError("Native ownership cannot be copied")

    def __reduce__(self) -> Any:
        raise TypeError("Native ownership cannot be serialized")

    @property
    def process_identity(self) -> ProcessObservation:
        return self._identity

    @property
    def pipes(self) -> Pipes:
        return self._pipes

    def close_advisory(self) -> bool:
        if self._finished:
            return True
        self._handles.close(self._pipes.parent_stdin)
        if self._role is Role.CONTROLLER:
            # Never wait for/kill an active recording Controller on main exit.
            return self.poll_exit()
        if not self._handles.ops.wait_process(self._process.process, 1000):
            self._handles.close(self._job)  # Only the owned pure-worker Job.
        return self.poll_exit(timeout_ms=1000)

    def poll_exit(self, *, timeout_ms: int = 0) -> bool:
        _int(timeout_ms, maximum=1000)
        if self._finished:
            return True
        if not self._handles.ops.wait_process(self._process.process, timeout_ms):
            return False  # Retain identity/file pins; no false cleanup PASS.
        self._handles.close_all()
        self._finished = True
        return True


class SuspendedChildLauncher:
    """Exact pre-resume ordering; no generic process-launch fallback exists."""

    def __init__(self, operations: WindowsOperations) -> None:
        self._ops = operations
        self._pending_owned: tuple[_Handles, CreatedProcess | None] | None = None

    def recover_owned_cleanup(self) -> bool:
        """Poll the retained exact handle; never reopen/kill another PID."""
        if self._pending_owned is None:
            return True
        handles, process = self._pending_owned
        if process is not None and not self._ops.wait_process(process.process, 0):
            return False
        handles.close_all()
        self._pending_owned = None
        return True

    def launch(self, spec: BundleSpec, bootstrap_frame: bytes) -> LaunchReceipt:
        error, residuals = "API", ()
        try:
            return self._launch(spec, bootstrap_frame)
        except LaunchError as failure:
            error, residuals = failure.reason, failure.residual_roots
        except Exception:
            pass
        raise LaunchError(error, residual_roots=residuals)

    def _launch(self, spec: BundleSpec, bootstrap_frame: bytes) -> LaunchReceipt:
        if self._pending_owned is not None:
            _fail("CLEANUP")
        root, files = _spec(spec)
        bootstrap = wire.decode_message(bootstrap_frame)
        if bootstrap.kind is not wire.MessageType.BOOTSTRAP or bootstrap.sequence != 1:
            _fail("BOOTSTRAP")
        ops, handles = self._ops, _Handles(self._ops)
        pins: list[_Pin] = []
        process = pipes = startup = None
        job = None
        resume_attempted = False
        runtime_root = None
        runtime_created = False
        process_owned = False
        reason = "API"
        success = False
        try:
            directories = set()
            for path in (root, *(root / relative for relative in files)):
                directory = path if path == root else path.parent
                directories.add(directory)
                directories.update(directory.parents)
            temp = _root(ops.system_temp_root())
            directories.add(temp)
            directories.update(temp.parents)
            for directory in sorted(directories, key=lambda p: (len(p.parts), str(p))):
                handle = handles.own(ops.open_file(
                    str(directory), access=FILE_READ_ATTRIBUTES,
                    sharing=FILE_SHARE_READ | FILE_SHARE_WRITE, creation=OPEN_EXISTING,
                    flags=FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTICS))
                ops.set_inheritable(handle, False)
                pins.append(_Pin(handle, _observe(ops, handle, str(directory), True), None))
            for relative, expected_digest in files.items():
                path = str(root / relative)
                handle = handles.own(ops.open_file(
                    path, access=GENERIC_READ, sharing=FILE_SHARE_READ, creation=OPEN_EXISTING,
                    flags=FILE_FLAG_OPEN_REPARSE_POINT))
                ops.set_inheritable(handle, False)
                observed = _observe(ops, handle, path, False)
                digest = ops.hash_file(handle)
                if type(digest) is not bytes or digest != expected_digest:
                    _fail("IDENTITY")
                pins.append(_Pin(handle, observed, digest))
            runtime_root = str(temp / ("bvp-task048-c1-" + uuid.uuid4().hex))
            if ops.path_exists(runtime_root):
                _fail("PATH")
            ops.create_directory_new(runtime_root)  # Atomic CreateDirectoryW; no reuse.
            runtime_created = True
            handle = handles.own(ops.open_file(
                runtime_root, access=FILE_READ_ATTRIBUTES,
                sharing=FILE_SHARE_READ | FILE_SHARE_WRITE, creation=OPEN_EXISTING,
                flags=FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTICS))
            ops.set_inheritable(handle, False)
            pins.append(_Pin(handle, _observe(ops, handle, runtime_root, True), None))
            current = _token(ops.current_token())
            pipes = ops.create_pipes()
            if type(pipes) is not Pipes:
                _fail("HANDLE")
            for handle in (*pipes.parent_handles, *pipes.child_handles):
                handles.own(handle)
            for handle in (*pipes.parent_handles, *pipes.child_handles):
                ops.set_inheritable(handle, handle in pipes.child_handles)
            startup = ops.startup(
                attribute=PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
                inherited_handles=pipes.child_handles, flags=STARTF_USESTDHANDLES)
            if (type(startup) is not Startup or startup.inherited_handles != pipes.child_handles
                    or startup.flags != STARTF_USESTDHANDLES):
                _fail("HANDLE")
            image = str(root / spec.image_relative_path)
            image_pin = next(pin for pin in pins if pin.observation.final_path == image)
            mode = "--bvp-meter-managed-v1" if spec.role is Role.CONTROLLER else "--bvp-meter-worker-v1"
            flags = CREATE_SUSPENDED | EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT
            if spec.role is Role.WORKER:
                flags |= CREATE_NO_WINDOW
            windows_directory = ops.windows_directory()
            if (type(windows_directory) is not str
                    or not re.fullmatch(r"[A-Z]:\\[A-Za-z0-9 _-]+", windows_directory)):
                _fail("PATH")
            environment = {
                "TEMP": runtime_root, "TMP": runtime_root, "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1", "SystemRoot": windows_directory,
                "WINDIR": windows_directory,
            }
            process = ops.create_suspended(
                application=image, command_line=f'"{image}" {mode}', flags=flags,
                inherit_handles=True, cwd=runtime_root, environment=environment, startup=startup)
            if type(process) is not CreatedProcess:
                _fail("CREATE")
            handles.own(process.process)
            process_owned = True
            handles.own(process.thread)
            _int(process.pid, minimum=1, maximum=2**32-1)
            # Close only parent's copies of the child ends after CreateProcess.
            for child_handle in pipes.child_handles:
                handles.close(child_handle)
            # The attribute list is not needed after CreateProcess returns.
            # Dispose it before any resume/bootstrap; a cleanup fault stays gated.
            ops.delete_startup(startup)
            startup = None
            observed = ops.inspect_process(process)
            if (type(observed) is not ProcessObservation or observed.pid != process.pid
                    or observed.image_path != image
                    or _identity(observed.image_identity) != image_pin.observation.identity
                    or _token(observed.token) != current):
                _fail("IDENTITY")
            _int(observed.creation_time, minimum=1)
            for pin in pins:
                check = _observe(ops, pin.handle, pin.observation.final_path,
                                 bool(pin.observation.attributes & FILE_ATTRIBUTE_DIRECTORY))
                if check.identity != pin.observation.identity:
                    _fail("IDENTITY")
                if pin.digest is not None and ops.hash_file(pin.handle) != pin.digest:
                    _fail("IDENTITY")
            if spec.role is Role.WORKER:
                job = handles.own(ops.create_worker_job(
                    flags=JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_ACTIVE_PROCESS,
                    active_process_limit=1))
                ops.set_inheritable(job, False)
                ops.assign_job(job, process.process)
            if ops.inspect_process(process) != observed:
                _fail("IDENTITY")
            # A return of zero or a wrapper failure does not prove the primary
            # thread stayed suspended. Never kill a Controller after this boundary.
            resume_attempted = True
            if ops.resume_thread(process.thread) != 1:
                _fail("RESUME")
            handles.close(process.thread)
            # No private Project path is sent until all identity/Job/handle gates pass.
            ops.write_bootstrap(pipes.parent_stdin, bootstrap_frame)
            receipt = LaunchReceipt(
                handles=handles, process=process, pipes=pipes, pins=tuple(pins), job=job,
                runtime_root=runtime_root, role=spec.role, identity=observed)
            success = True
            return receipt
        except LaunchError as error:
            reason = error.reason
        except Exception:
            reason = "API"
        finally:
            cleanup_failed = False
            if startup is not None:
                try:
                    ops.delete_startup(startup)
                except Exception:
                    cleanup_failed = True
            if not success:
                may_release_pins = True
                if pipes is not None:
                    try:
                        handles.close(pipes.parent_stdin)
                    except Exception:
                        cleanup_failed = True
                if process_owned:
                    try:
                        if not resume_attempted:
                            ops.terminate_process(process.process)
                            if not ops.wait_process(process.process, 1000):
                                cleanup_failed = True
                                may_release_pins = False
                        elif spec.role is Role.WORKER:
                            handles.close(job)
                            if not ops.wait_process(process.process, 1000):
                                cleanup_failed = True
                                may_release_pins = False
                        # A possibly resumed Controller is never terminated here.
                        elif not ops.wait_process(process.process, 0):
                            may_release_pins = False
                    except Exception:
                        cleanup_failed = True
                        may_release_pins = False
                if may_release_pins:
                    try:
                        handles.close_all()
                    except Exception:
                        cleanup_failed = True
                if handles.open:
                    self._pending_owned = (handles, process if process_owned else None)
                    cleanup_failed = True
            if cleanup_failed:
                reason = "CLEANUP"
        raise LaunchError(reason, residual_roots=(() if not runtime_created else (runtime_root,)))
