"""TASK-048 C1B trusted, read-only recording-meter host.

The browser supplies no paths, executable names, policy, or process identity.
Importing this module has no native effects. Only an explicit UI open action
starts the admitted same-build Controller, on a background thread. Native API
execution and latency remain separately verified by the C1C Windows gate.
"""
from __future__ import annotations

import ctypes as ct
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
import importlib
import os
from pathlib import Path, PureWindowsPath
import re
import secrets
import sys
import threading
import time
from typing import Any, Callable
import uuid
import weakref

from . import task048_meter_protocol as wire
from . import task048_windows_child_launch as launch
from .product_project_store import ProductProjectManifestStore
from .task048_meter_worker import BindingError

# Fixed-width ABI fields keep layout inspection meaningful on non-Windows tests.
_DWORD, _WORD, _HANDLE = ct.c_uint32, ct.c_uint16, ct.c_void_p
_BOOL, _SIZE_T = ct.c_int32, ct.c_size_t


class _FileTime(ct.Structure):
    _fields_ = [("low", _DWORD), ("high", _DWORD)]


class _ByHandle(ct.Structure):
    _fields_ = [
        ("attributes", _DWORD), ("creation", _FileTime), ("access", _FileTime),
        ("write", _FileTime), ("volume", _DWORD), ("size_high", _DWORD),
        ("size_low", _DWORD), ("links", _DWORD), ("index_high", _DWORD),
        ("index_low", _DWORD),
    ]


class _FileIdInfo(ct.Structure):
    _fields_ = [("volume", ct.c_uint64), ("file_id", ct.c_ubyte * 16)]


class _SecurityAttributes(ct.Structure):
    _fields_ = [("length", _DWORD), ("descriptor", ct.c_void_p), ("inherit", _BOOL)]


class _StartupInfo(ct.Structure):
    _fields_ = [
        ("cb", _DWORD), ("reserved", ct.c_wchar_p), ("desktop", ct.c_wchar_p),
        ("title", ct.c_wchar_p), ("x", _DWORD), ("y", _DWORD), ("cx", _DWORD),
        ("cy", _DWORD), ("chars_x", _DWORD), ("chars_y", _DWORD),
        ("fill", _DWORD), ("flags", _DWORD), ("show", _WORD),
        ("reserved2_size", _WORD), ("reserved2", ct.c_void_p),
        ("stdin", _HANDLE), ("stdout", _HANDLE), ("stderr", _HANDLE),
    ]


class _StartupInfoEx(ct.Structure):
    _fields_ = [("info", _StartupInfo), ("attributes", ct.c_void_p)]


class _ProcessInformation(ct.Structure):
    _fields_ = [("process", _HANDLE), ("thread", _HANDLE), ("pid", _DWORD), ("tid", _DWORD)]


class _JobBasicLimit(ct.Structure):
    _fields_ = [
        ("per_process_time", ct.c_int64), ("per_job_time", ct.c_int64),
        ("flags", _DWORD), ("minimum_working_set", _SIZE_T),
        ("maximum_working_set", _SIZE_T), ("active_process_limit", _DWORD),
        ("affinity", _SIZE_T), ("priority", _DWORD), ("scheduling", _DWORD),
    ]


class _IoCounters(ct.Structure):
    _fields_ = [(name, ct.c_uint64) for name in (
        "read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]


class _JobExtendedLimit(ct.Structure):
    _fields_ = [
        ("basic", _JobBasicLimit), ("io", _IoCounters),
        ("process_memory", _SIZE_T), ("job_memory", _SIZE_T),
        ("peak_process_memory", _SIZE_T), ("peak_job_memory", _SIZE_T),
    ]


@dataclass
class _PendingNativeCreation:
    receipt: _ProcessInformation
    exited: bool = False
    process_closed: bool = False
    thread_closed: bool = False


class Win32MeterOperations:
    """Concrete implementation of the frozen, injected C1A Win32 contract.

    FileIdInfo is GetFileInformationByHandleEx class 18. The attribute-list
    allocation and its handle-array storage remain alive until list deletion.
    All failures use fixed codes; native error text is never sent to the UI.
    """
    def __init__(self) -> None:
        if os.name != "nt" or ct.sizeof(ct.c_void_p) != 8:
            raise launch.LaunchError("API")
        self._kernel = ct.WinDLL("kernel32.dll", use_last_error=True)
        self._security = ct.WinDLL("advapi32.dll", use_last_error=True)
        self._pending_creation: _PendingNativeCreation | None = None
        self._bind_functions()

    def _bind_functions(self) -> None:
        def bind(lib: Any, name: str, result: Any, *arguments: Any) -> None:
            fn = getattr(lib, name)
            fn.restype, fn.argtypes = result, list(arguments)
        k, a, p, w, d, h = self._kernel, self._security, ct.c_void_p, ct.c_wchar_p, _DWORD, _HANDLE
        bind(k, "GetTempPathW", d, d, w)
        bind(k, "GetWindowsDirectoryW", d, w, d)
        bind(k, "CreateDirectoryW", _BOOL, w, p)
        bind(k, "CreateFileW", h, w, d, d, p, d, d, h)
        bind(k, "GetFinalPathNameByHandleW", d, h, w, d, d)
        bind(k, "GetFileInformationByHandle", _BOOL, h, p)
        bind(k, "GetFileInformationByHandleEx", _BOOL, h, ct.c_int, p, d)
        bind(k, "SetFilePointerEx", _BOOL, h, ct.c_int64, p, d)
        bind(k, "ReadFile", _BOOL, h, p, d, p, p)
        bind(k, "WriteFile", _BOOL, h, p, d, p, p)
        bind(k, "PeekNamedPipe", _BOOL, h, p, d, p, p, p)
        bind(k, "GetFileType", d, h)
        bind(k, "GetStdHandle", h, d)
        bind(k, "SetHandleInformation", _BOOL, h, d, d)
        bind(k, "CreatePipe", _BOOL, p, p, p, d)
        bind(k, "InitializeProcThreadAttributeList", _BOOL, p, d, d, p)
        bind(k, "UpdateProcThreadAttribute", _BOOL, p, d, _SIZE_T, p, _SIZE_T, p, p)
        bind(k, "DeleteProcThreadAttributeList", None, p)
        bind(k, "CreateProcessW", _BOOL, w, w, p, p, _BOOL, d, p, w, p, p)
        bind(k, "GetCurrentProcess", h)
        bind(k, "GetProcessId", d, h)
        bind(k, "GetProcessTimes", _BOOL, h, p, p, p, p)
        bind(k, "QueryFullProcessImageNameW", _BOOL, h, d, w, p)
        bind(k, "CreateJobObjectW", h, p, w)
        bind(k, "SetInformationJobObject", _BOOL, h, ct.c_int, p, d)
        bind(k, "AssignProcessToJobObject", _BOOL, h, h)
        bind(k, "ResumeThread", d, h)
        bind(k, "TerminateProcess", _BOOL, h, ct.c_uint)
        bind(k, "WaitForSingleObject", d, h, d)
        bind(k, "CloseHandle", _BOOL, h)
        bind(k, "LocalFree", p, p)
        bind(a, "OpenProcessToken", _BOOL, h, d, p)
        bind(a, "GetTokenInformation", _BOOL, h, ct.c_int, p, d, p)
        bind(a, "ConvertSidToStringSidW", _BOOL, p, p)

    @staticmethod
    def _require(value: Any, reason: str = "API") -> None:
        if not value:
            raise launch.LaunchError(reason)

    @staticmethod
    def _handle(value: Any) -> int:
        result = int(value or 0)
        if not 0 < result <= 2**63 - 1:
            raise launch.LaunchError("HANDLE")
        return result

    def system_temp_root(self) -> str:
        buffer = ct.create_unicode_buffer(32768)
        count = self._kernel.GetTempPathW(len(buffer), buffer)
        self._require(0 < count < len(buffer), "PATH")
        return buffer.value.rstrip("\\")

    def windows_directory(self) -> str:
        buffer = ct.create_unicode_buffer(32768)
        count = self._kernel.GetWindowsDirectoryW(buffer, len(buffer))
        self._require(0 < count < len(buffer), "PATH")
        return buffer.value

    def path_exists(self, path: str) -> bool:
        return os.path.lexists(path)

    def create_directory_new(self, path: str) -> None:
        self._require(self._kernel.CreateDirectoryW(path, None), "PATH")

    def open_file(self, path: str, *, access: int, sharing: int, creation: int, flags: int) -> int:
        return self._handle(self._kernel.CreateFileW(path, access, sharing, None, creation, flags, None))

    def observe_file(self, handle: int) -> launch.FileObservation:
        basic, identity = _ByHandle(), _FileIdInfo()
        self._require(self._kernel.GetFileInformationByHandle(handle, ct.byref(basic)), "IDENTITY")
        self._require(self._kernel.GetFileInformationByHandleEx(
            handle, 18, ct.byref(identity), ct.sizeof(identity)), "IDENTITY")
        buffer = ct.create_unicode_buffer(32768)
        count = self._kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
        self._require(0 < count < len(buffer), "IDENTITY")
        value = buffer.value
        self._require(value.startswith("\\\\?\\") and not value.startswith("\\\\?\\UNC\\"), "PATH")
        value = value[4:]
        return launch.FileObservation(
            value, launch.FileIdentity(identity.volume, bytes(identity.file_id)),
            basic.attributes, (basic.size_high << 32) | basic.size_low)

    def hash_file(self, handle: int) -> bytes:
        self._require(self._kernel.SetFilePointerEx(handle, 0, None, 0), "IDENTITY")
        digest = sha256()
        buffer = ct.create_string_buffer(1024 * 1024)
        while True:
            count = _DWORD()
            self._require(self._kernel.ReadFile(handle, buffer, len(buffer), ct.byref(count), None), "IDENTITY")
            if not count.value:
                break
            digest.update(buffer.raw[:count.value])
        self._require(self._kernel.SetFilePointerEx(handle, 0, None, 0), "IDENTITY")
        return digest.digest()

    def set_inheritable(self, handle: int, value: bool) -> None:
        self._require(self._kernel.SetHandleInformation(handle, 1, int(value)), "HANDLE")

    def _token_information(self, token: int, kind: int) -> Any:
        size = _DWORD()
        self._security.GetTokenInformation(token, kind, None, 0, ct.byref(size))
        self._require(0 < size.value <= 65536, "TOKEN")
        buffer = ct.create_string_buffer(size.value)
        self._require(self._security.GetTokenInformation(
            token, kind, buffer, len(buffer), ct.byref(size)), "TOKEN")
        return buffer

    def _token(self, process: int) -> launch.TokenIdentity:
        token = _HANDLE()
        self._require(self._security.OpenProcessToken(process, 0x8, ct.byref(token)), "TOKEN")
        try:
            user = self._token_information(token.value, 1)
            sid_pointer = ct.cast(user, ct.POINTER(ct.c_void_p))[0]
            sid_text = ct.c_wchar_p()
            self._require(self._security.ConvertSidToStringSidW(sid_pointer, ct.byref(sid_text)), "TOKEN")
            try:
                sid = sid_text.value
            finally:
                self._kernel.LocalFree(ct.cast(sid_text, ct.c_void_p))
            session = ct.cast(self._token_information(token.value, 12), ct.POINTER(_DWORD))[0]
            elevated = ct.cast(self._token_information(token.value, 20), ct.POINTER(_DWORD))[0]
            self._require(type(sid) is str and elevated in (0, 1), "TOKEN")
            return launch.TokenIdentity(sid, int(session), bool(elevated))
        finally:
            self.close_handle(token.value)

    def current_token(self) -> launch.TokenIdentity:
        return self._token(self._kernel.GetCurrentProcess())

    def create_pipes(self) -> launch.Pipes:
        owned: list[int] = []
        try:
            pairs: list[tuple[int, int]] = []
            attributes = _SecurityAttributes(ct.sizeof(_SecurityAttributes), None, True)
            for _ in range(3):
                reader, writer = _HANDLE(), _HANDLE()
                self._require(self._kernel.CreatePipe(
                    ct.byref(reader), ct.byref(writer), ct.byref(attributes), wire.MAX_FRAME_BYTES), "HANDLE")
                owned.extend((self._handle(reader.value), self._handle(writer.value)))
                pairs.append((reader.value, writer.value))
            return launch.Pipes(pairs[0][1], pairs[1][0], pairs[2][0],
                                pairs[0][0], pairs[1][1], pairs[2][1])
        except Exception:
            for handle in owned:
                self.close_handle(handle)
            raise

    def startup(self, *, attribute: int, inherited_handles: tuple[int, int, int], flags: int) -> launch.Startup:
        self._require(attribute == launch.PROC_THREAD_ATTRIBUTE_HANDLE_LIST
                      and len(set(inherited_handles)) == 3, "HANDLE")
        size = _SIZE_T()
        self._kernel.InitializeProcThreadAttributeList(None, 1, 0, ct.byref(size))
        self._require(0 < size.value <= 65536, "HANDLE")
        allocation = ct.create_string_buffer(size.value)
        handles = (_HANDLE * 3)(*inherited_handles)
        self._require(self._kernel.InitializeProcThreadAttributeList(
            allocation, 1, 0, ct.byref(size)), "HANDLE")
        try:
            self._require(self._kernel.UpdateProcThreadAttribute(
                allocation, 0, attribute, handles, ct.sizeof(handles), None, None), "HANDLE")
            return launch.Startup((allocation, handles), inherited_handles, flags)
        except Exception:
            self._kernel.DeleteProcThreadAttributeList(allocation)
            raise

    def delete_startup(self, startup: launch.Startup) -> None:
        self._kernel.DeleteProcThreadAttributeList(startup.attribute_list[0])

    def create_suspended(self, *, application: str, command_line: str, flags: int,
                         inherit_handles: bool, cwd: str, environment: dict[str, str],
                         startup: launch.Startup) -> launch.CreatedProcess:
        self._require(getattr(self, "_pending_creation", None) is None, "CLEANUP")
        info = _StartupInfoEx()
        info.info.cb = ct.sizeof(info)
        info.info.flags = startup.flags
        info.info.stdin, info.info.stdout, info.info.stderr = startup.inherited_handles
        info.attributes = ct.cast(startup.attribute_list[0], ct.c_void_p)
        # Deliberate environment allowlist; no inherited Python/path/user config.
        block = ct.create_unicode_buffer("\0".join(
            name + "=" + value for name, value in sorted(environment.items())) + "\0\0")
        mutable_command = ct.create_unicode_buffer(command_line)
        pending = _PendingNativeCreation(_ProcessInformation())
        receipt = pending.receipt
        self._require(self._kernel.CreateProcessW(
            application, mutable_command, None, None, inherit_handles, flags,
            block, cwd, ct.byref(info), ct.byref(receipt)), "CREATE")
        # Publish raw native ownership BEFORE handle validation or Python record
        # construction. A failed return must not abandon a suspended Controller.
        self._pending_creation = pending
        try:
            created = launch.CreatedProcess(
                self._handle(receipt.process), self._handle(receipt.thread), receipt.pid)
        except BaseException:
            recovered = self.recover_partial_creation(timeout_ms=1000)
            raise launch.LaunchError("CREATE" if recovered else "CLEANUP") from None
        self._pending_creation = None  # Exact receipt transfers to frozen C1A.
        return created

    def recover_partial_creation(self, *, timeout_ms: int = 0) -> bool:
        """Recover only a CreateProcess success that never returned to C1A.

        No resume occurred: terminate and wait the exact raw handle. A terminate
        failure must not suppress the wait; an unconfirmed exit/close retains
        ownership and prevents C1A from releasing its image/ancestor pins.
        """
        pending = getattr(self, "_pending_creation", None)
        if pending is None:
            return True
        try:
            process = self._handle(pending.receipt.process)
        except launch.LaunchError:
            return False  # Never use a pseudo handle or recover by PID/path.
        if not pending.exited:
            try:
                self.terminate_process(process)
            except Exception:
                pass
            try:
                pending.exited = self.wait_process(process, timeout_ms)
            except Exception:
                return False
            if not pending.exited:
                return False
        # All valid raw returned handles remain tracked even when validation or
        # an earlier close failed. Attempt both; never close either twice.
        for name in ("thread", "process"):
            if getattr(pending, name + "_closed"):
                continue
            value = getattr(pending.receipt, name)
            if value in (None, 0, ct.c_void_p(-1).value):
                setattr(pending, name + "_closed", True)
                continue
            try:
                self._require(self._kernel.CloseHandle(value), "CLEANUP")
                setattr(pending, name + "_closed", True)
            except Exception:
                pass
        if pending.process_closed and pending.thread_closed:
            self._pending_creation = None
            return True
        return False

    def inspect_process(self, process: launch.CreatedProcess) -> launch.ProcessObservation:
        pid = self._kernel.GetProcessId(process.process)
        self._require(pid > 0, "IDENTITY")
        creation, exited, kernel, user = _FileTime(), _FileTime(), _FileTime(), _FileTime()
        self._require(self._kernel.GetProcessTimes(
            process.process, ct.byref(creation), ct.byref(exited), ct.byref(kernel), ct.byref(user)), "IDENTITY")
        buffer, size = ct.create_unicode_buffer(32768), _DWORD(32768)
        self._require(self._kernel.QueryFullProcessImageNameW(
            process.process, 0, buffer, ct.byref(size)), "IDENTITY")
        handle = self.open_file(buffer.value, access=launch.GENERIC_READ,
                                sharing=launch.FILE_SHARE_READ, creation=launch.OPEN_EXISTING,
                                flags=launch.FILE_FLAG_OPEN_REPARSE_POINT)
        try:
            observation = self.observe_file(handle)
            self._require(observation.final_path == buffer.value
                          and not observation.attributes & (launch.FILE_ATTRIBUTE_DIRECTORY
                                                            | launch.FILE_ATTRIBUTE_REPARSE_POINT), "IDENTITY")
            identity = observation.identity
        finally:
            self.close_handle(handle)
        return launch.ProcessObservation(
            pid, (creation.high << 32) | creation.low, buffer.value, identity, self._token(process.process))

    def create_worker_job(self, *, flags: int, active_process_limit: int) -> int:
        self._require(flags == (launch.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                                | launch.JOB_OBJECT_LIMIT_ACTIVE_PROCESS)
                      and active_process_limit == 1, "JOB")
        job = self._handle(self._kernel.CreateJobObjectW(None, None))
        try:
            limits = _JobExtendedLimit()
            limits.basic.flags, limits.basic.active_process_limit = flags, active_process_limit
            self._require(self._kernel.SetInformationJobObject(
                job, 9, ct.byref(limits), ct.sizeof(limits)), "JOB")
            return job
        except Exception:
            self.close_handle(job)
            raise

    def assign_job(self, job: int, process: int) -> None:
        self._require(self._kernel.AssignProcessToJobObject(job, process), "JOB")

    def resume_thread(self, thread: int) -> int:
        return int(self._kernel.ResumeThread(thread))

    def write_bootstrap(self, pipe: int, data: bytes) -> None:
        self._require(type(data) is bytes and 0 < len(data) <= wire.MAX_FRAME_BYTES, "BOOTSTRAP")
        buffer = ct.create_string_buffer(data)
        offset = 0
        while offset < len(data):
            count = _DWORD()
            self._require(self._kernel.WriteFile(
                pipe, ct.byref(buffer, offset), len(data) - offset, ct.byref(count), None), "BOOTSTRAP")
            self._require(0 < count.value <= len(data) - offset, "BOOTSTRAP")
            offset += count.value

    def read_pipe_available(self, pipe: int, maximum: int = 4096) -> bytes | None:
        """None = no bytes yet, empty = EOF. Never wait for arbitrary pipe fill."""
        self._require(1 <= maximum <= wire.MAX_FRAME_BYTES, "HANDLE")
        available = _DWORD()
        if not self._kernel.PeekNamedPipe(pipe, None, 0, None, ct.byref(available), None):
            if ct.get_last_error() in (109, 232):  # Broken pipe / pipe being closed.
                return b""
            raise launch.LaunchError("HANDLE")
        if not available.value:
            return None
        buffer = ct.create_string_buffer(min(maximum, available.value))
        count = _DWORD()
        self._require(self._kernel.ReadFile(pipe, buffer, len(buffer), ct.byref(count), None), "HANDLE")
        return buffer.raw[:count.value]

    def standard_pipe(self, which: int) -> int:
        self._require(which in (-10, -11, -12), "HANDLE")
        handle = self._handle(self._kernel.GetStdHandle(which & 0xFFFFFFFF))
        self._require(self._kernel.GetFileType(handle) == 3, "HANDLE")
        self.set_inheritable(handle, False)
        return handle

    def terminate_process(self, process: int) -> None:
        self._require(self._kernel.TerminateProcess(process, 97), "CLEANUP")

    def wait_process(self, process: int, timeout_ms: int) -> bool:
        result = self._kernel.WaitForSingleObject(process, timeout_ms)
        self._require(result in (0, 258), "CLEANUP")
        return result == 0

    def close_handle(self, handle: int) -> None:
        # A launch that raised before returning its CreatedProcess cannot let
        # C1A discard any pins until this backend's raw receipt is fully drained.
        self._require(getattr(self, "_pending_creation", None) is None, "CLEANUP")
        self._require(self._kernel.CloseHandle(handle), "CLEANUP")


class WindowsProjectPins:
    """No-delete ancestor pins, separate from short-lived manifest read pins."""
    def __init__(self, operations: Any, root: str, *, expected: launch.FileIdentity | None = None) -> None:
        parsed = PureWindowsPath(root)
        if (not re.fullmatch(r"[A-Z]:\\.+", root) or str(parsed) != root
                or len(parsed.parts) < 3 or any(
                    part in (".", "..") or part.endswith((" ", ".")) or ":" in part
                    for part in parsed.parts[1:])):
            raise BindingError(wire.StatusCode.PROJECT_IDENTITY_CHANGED)
        self.project_root = Path(root)
        self._ops, self._pins = operations, []
        self._closed = False
        try:
            # Public path() never creates the control directory.
            control = PureWindowsPath(str(ProductProjectManifestStore.path(self.project_root).parent))
            directories = set(parsed.parents) | {parsed, control}
            for directory in sorted(directories, key=lambda value: (len(value.parts), str(value))):
                handle = operations.open_file(
                    str(directory), access=launch.FILE_READ_ATTRIBUTES,
                    sharing=launch.FILE_SHARE_READ | launch.FILE_SHARE_WRITE,
                    creation=launch.OPEN_EXISTING,
                    flags=launch.FILE_FLAG_OPEN_REPARSE_POINT | launch.FILE_FLAG_BACKUP_SEMANTICS)
                self._pins.append((handle, None))
                operations.set_inheritable(handle, False)
                observed = operations.observe_file(handle)
                self._pins[-1] = (handle, observed)
                self._validate(observed, str(directory))
            self.identity = next(observation.identity for _, observation in self._pins
                                 if observation.final_path == root)
            if expected is not None and self.identity != expected:
                raise BindingError(wire.StatusCode.PROJECT_IDENTITY_CHANGED)
        except Exception as error:
            code = error.code if isinstance(error, BindingError) else wire.StatusCode.READBACK_UNAVAILABLE
            failure = BindingError(code)
            try:
                self.close()
            except Exception:
                # Preserve the exact partially bound pins for the host/inspector.
                # A failed constructor must not orphan its raw handle ownership.
                failure.pending_pins = self
            raise failure from None

    @staticmethod
    def _validate(observation: launch.FileObservation, path: str) -> None:
        if (observation.final_path != path
                or not observation.attributes & launch.FILE_ATTRIBUTE_DIRECTORY
                or observation.attributes & launch.FILE_ATTRIBUTE_REPARSE_POINT):
            raise BindingError(wire.StatusCode.PROJECT_IDENTITY_CHANGED)

    def verify(self) -> None:
        if self._closed:
            raise BindingError(wire.StatusCode.PROJECT_IDENTITY_CHANGED)
        try:
            for handle, previous in self._pins:
                current = self._ops.observe_file(handle)
                self._validate(current, previous.final_path)
                if current.identity != previous.identity:
                    raise BindingError(wire.StatusCode.PROJECT_IDENTITY_CHANGED)
        except BindingError:
            raise
        except Exception:
            raise BindingError(wire.StatusCode.READBACK_UNAVAILABLE) from None

    def close(self) -> None:
        self._closed = True
        remaining = []
        for handle, observed in reversed(self._pins):
            try:
                self._ops.close_handle(handle)
            except Exception:
                remaining.append((handle, observed))
        self._pins = remaining
        if remaining:
            raise BindingError(wire.StatusCode.READBACK_UNAVAILABLE)


class WindowsProjectInspector:
    def __init__(self, operations: Any) -> None:
        self._ops = operations
        self._pending: WindowsProjectPins | None = None

    def bind(self, bootstrap: wire.Bootstrap) -> WindowsProjectPins:
        if self._pending is not None:
            self._pending.close()  # No new binding until earlier exact handles close.
            self._pending = None
        try:
            return WindowsProjectPins(self._ops, bootstrap.project_root,
                                      expected=launch.FileIdentity(bootstrap.root_volume, bootstrap.root_file_id))
        except BindingError as error:
            pending = getattr(error, "pending_pins", None)
            if type(pending) is WindowsProjectPins:
                self._pending = pending
            raise


@dataclass(frozen=True, slots=True, repr=False)
class SelectedProject:
    root: str
    project_id: str


def read_project_head(operations: Any, pins: WindowsProjectPins, project_id: str) -> tuple[int, bytes]:
    try:
        return _read_project_head(operations, pins, project_id)
    except BindingError:
        raise
    except Exception:
        # Includes manifest path/open/observe/close and root verification APIs.
        raise BindingError(wire.StatusCode.READBACK_UNAVAILABLE) from None


def _read_project_head(operations: Any, pins: WindowsProjectPins, project_id: str) -> tuple[int, bytes]:
    """Bracket the public read with fresh file identities without blocking saves.

    Immutable executable files are pinned against write/delete by C1A. The
    canonical Project head is deliberately different: its writer owns atomic
    replacement, so each short metadata handle shares READ|WRITE|DELETE.
    A replacement during the public read changes the second physical identity.
    """
    pins.verify()
    target = str(ProductProjectManifestStore.path(pins.project_root))

    def observe() -> launch.FileObservation:
        handle = operations.open_file(
            target, access=launch.FILE_READ_ATTRIBUTES,
            sharing=launch.FILE_SHARE_READ | launch.FILE_SHARE_WRITE | 0x4,  # FILE_SHARE_DELETE
            creation=launch.OPEN_EXISTING, flags=launch.FILE_FLAG_OPEN_REPARSE_POINT)
        try:
            value = operations.observe_file(handle)
            if (value.final_path != target or value.attributes & (
                    launch.FILE_ATTRIBUTE_DIRECTORY | launch.FILE_ATTRIBUTE_REPARSE_POINT)):
                raise BindingError(wire.StatusCode.PROJECT_IDENTITY_CHANGED)
            return value
        finally:
            operations.close_handle(handle)

    before = observe()
    try:
        manifest = ProductProjectManifestStore.load(pins.project_root)
    except Exception:
        raise BindingError(wire.StatusCode.READBACK_UNAVAILABLE) from None
    after = observe()
    pins.verify()
    if before != after or manifest.project_id != project_id:
        raise BindingError(wire.StatusCode.PROJECT_IDENTITY_CHANGED)
    return manifest.project_revision, bytes.fromhex(manifest.project_manifest_sha256.removeprefix("sha256:"))


_STATUS_LABELS = {
    "AVAILABLE": "OBS録音チェックを開けます。",
    "UNAVAILABLE": "同一ビルドの録音メーターが利用できません。",
    "PROJECT_REQUIRED": "先にProjectを開いてください。",
    "OPENING": "録音画面を開いています。",
    "CONNECTED": "録音画面に接続しました。録音開始は画面で操作してください。",
    "CONTROLLER_OPEN": "録音画面は開いています。閉じてから再接続してください。",
    "PROJECT_CHANGED": "Projectが変わったため判定を停止しました。録音画面を閉じて再接続してください。",
    "READBACK_UNAVAILABLE": "Projectの状態を確認できないため判定を停止しました。",
    "BOOTSTRAP_REJECTED": "Projectへの接続を確認できませんでした。",
    "TRANSPORT_FAILURE": "メーターとの接続が切れました。録音・停止は録音画面で操作できます。",
    "CLOSED": "メーター接続を終了しました。",
}


def unavailable_meter_snapshot(reason: str = "UNAVAILABLE") -> dict[str, Any]:
    return {
        "available": False, "can_open": False, "connected": False,
        "status": reason if reason in _STATUS_LABELS else "UNAVAILABLE",
        "message": _STATUS_LABELS.get(reason, _STATUS_LABELS["UNAVAILABLE"]),
        "advisory_label": "適正判定 未確定", "capture_started": False,
        "quality_pass": False, "loss_provenance": "UNKNOWN",
    }


class MeterControllerHost:
    """One owned Controller, exact current-Project binding, no blocking UI work."""
    def __init__(self, selection: SelectedProject, spec: launch.BundleSpec, *,
                 operations_factory: Callable[[], Any] = Win32MeterOperations,
                 pins_factory: Callable[..., Any] = WindowsProjectPins,
                 head_reader: Callable[..., tuple[int, bytes]] = read_project_head,
                 launcher_factory: Callable[[Any], Any] = launch.SuspendedChildLauncher) -> None:
        self._selection, self._spec = selection, spec
        self._operations_factory, self._pins_factory = operations_factory, pins_factory
        self._head_reader, self._launcher_factory = head_reader, launcher_factory
        self._lock = threading.RLock()
        self._state = "AVAILABLE"
        self._closed = False
        self._running = False
        self._stop = threading.Event()
        self._receipt = None
        self._thread = None
        self._epoch = None
        self._receipt_lock = threading.Lock()
        self._writes = 0

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                **unavailable_meter_snapshot(), "available": not self._closed,
                "can_open": not self._closed and not self._running and self._writes == 0,
                "connected": self._state == "CONNECTED",
                "status": self._state, "message": _STATUS_LABELS[self._state],
            }

    def open(self) -> dict[str, Any]:
        with self._lock:
            if self._closed or self._running or self._writes:
                return self.snapshot()
            self._running, self._state = True, "OPENING"
            self._stop = threading.Event()
            self._epoch = str(uuid.uuid4())
            thread = threading.Thread(target=self._run, args=(self._stop, self._epoch),
                                      name="task048-c1-controller-host", daemon=True)
            self._thread = thread
            thread.start()
            return self.snapshot()

    def invalidate_before_project_write(self) -> None:
        self._invalidate("PROJECT_CHANGED")

    @contextmanager
    def project_write(self):
        with self._lock:
            self._writes += 1
        self.invalidate_before_project_write()
        try:
            yield
        finally:
            with self._lock:
                self._writes -= 1

    def _invalidate(self, state: str) -> None:
        with self._lock:
            self._state = "CLOSED" if self._closed else state
            self._stop.set()
            receipt = self._receipt
        if receipt is not None:
            # Invalidate host admission synchronously; close the owned link on a
            # separate control thread even if the background Project reader stalls.
            def disconnect() -> None:
                with self._receipt_lock:
                    try:
                        receipt.close_advisory()
                    except Exception:
                        pass
            threading.Thread(target=disconnect, name="task048-c1-invalidate", daemon=True).start()

    def close(self) -> None:
        with self._lock:
            self._closed = True
        self._invalidate("CLOSED")

    @staticmethod
    def _admit_ready(message: wire.Message, bootstrap: wire.Message) -> bool:
        body, selected = message.body, bootstrap.body
        if (message.kind is not wire.MessageType.RESULT or message.sequence != 1
                or message.nonce != bootstrap.nonce
                or type(body) not in (wire.Ready, wire.Status)
                or body.correlation != wire.response_correlation(bootstrap)):
            raise wire.ProtocolError("CORRELATION")
        if type(body) is wire.Status:
            if body.code is not wire.StatusCode.BOOTSTRAP_REJECTED:
                raise wire.ProtocolError("STATE")
            return False
        if (body.project_revision, body.manifest_sha256, body.root_volume, body.root_file_id) != (
                selected.project_revision, selected.manifest_sha256, selected.root_volume, selected.root_file_id):
            raise wire.ProtocolError("CORRELATION")
        return True

    def _run(self, stop: threading.Event, epoch: str) -> None:
        pins = receipt = operations = launcher = None
        reason = "TRANSPORT_FAILURE"
        try:
            operations = self._operations_factory()
            pins = self._pins_factory(operations, self._selection.root)
            head = self._head_reader(operations, pins, self._selection.project_id)
            bootstrap = wire.Bootstrap(epoch, pins.identity.volume, pins.identity.file_id,
                                       head[0], head[1], self._selection.project_id, self._selection.root)
            raw = wire.encode_message(bootstrap, nonce=secrets.token_bytes(32), sequence=1)
            request = wire.decode_message(raw)
            if stop.is_set():
                return
            launcher = self._launcher_factory(_AdmissionOperations(operations, self._lock, stop))
            receipt = launcher.launch(self._spec, raw)
            with self._lock:
                self._receipt = receipt
            if stop.is_set():
                return
            parser = wire.FrameAccumulator()
            ready = False
            started, last_check = time.monotonic_ns(), 0
            while not stop.is_set():
                now = time.monotonic_ns()
                parser.expire(now)
                if not ready and now - started >= 5_000_000_000:
                    raise wire.ProtocolError("CLOSED")
                if now - last_check >= 100_000_000:
                    current = self._head_reader(operations, pins, self._selection.project_id)
                    if current != head:
                        reason = "PROJECT_CHANGED"
                        break
                    last_check = time.monotonic_ns()
                with self._receipt_lock:
                    if stop.is_set():
                        break
                    error = operations.read_pipe_available(receipt.pipes.parent_stderr, 81)
                    if error:  # No stderr payload is retained, logged, or displayed.
                        raise wire.ProtocolError("INVALID_FRAME")
                    chunk = operations.read_pipe_available(receipt.pipes.parent_stdout)
                if chunk == b"":
                    break
                if chunk:
                    for message in parser.feed(chunk, now_ns=time.monotonic_ns()):
                        if ready or not self._admit_ready(message, request):
                            reason = "BOOTSTRAP_REJECTED" if not ready else "TRANSPORT_FAILURE"
                            raise wire.ProtocolError("STATE")
                        # Head re-admission precedes even the connection-only display.
                        if self._head_reader(operations, pins, self._selection.project_id) != head:
                            reason = "PROJECT_CHANGED"
                            raise wire.ProtocolError("STATE")
                        ready = True
                        with self._lock:
                            if not stop.is_set() and self._epoch == epoch:
                                self._state = "CONNECTED"
                with self._receipt_lock:
                    if receipt.poll_exit():
                        break
                stop.wait(0.02)
        except BindingError as error:
            pending = getattr(error, "pending_pins", None)
            if pins is None and type(pending) is WindowsProjectPins:
                pins = pending
            reason = {
                wire.StatusCode.PROJECT_IDENTITY_CHANGED: "PROJECT_CHANGED",
                wire.StatusCode.PROJECT_HEAD_CHANGED: "PROJECT_CHANGED",
                wire.StatusCode.READBACK_UNAVAILABLE: "READBACK_UNAVAILABLE",
            }.get(error.code, "TRANSPORT_FAILURE")
        except Exception:
            pass
        finally:
            with self._lock:
                if not stop.is_set() and self._epoch == epoch:
                    self._state = reason
            if receipt is not None:
                while True:
                    with self._receipt_lock:
                        try:
                            receipt.close_advisory()
                        except Exception:
                            pass  # A pipe close failure cannot suppress exit polling.
                        try:
                            if receipt.poll_exit():
                                break
                        except Exception:
                            pass
                    # This live thread keeps both Project and executable pins.
                    # No PID/path reopen or Controller kill, including uncertainty.
                    time.sleep(0.1)
            elif launcher is not None:
                while True:
                    try:
                        recover_partial = getattr(operations, "recover_partial_creation", lambda: True)
                        if recover_partial() and launcher.recover_owned_cleanup():
                            break
                    except Exception:
                        pass
                    time.sleep(0.1)
            # Only exact Controller exit/backend recovery makes Project pin
            # release eligible. An uncertain close never permits another open.
            while pins is not None:
                try:
                    pins.close()
                    break
                except Exception:
                    with self._lock:
                        if not stop.is_set() and self._epoch == epoch:
                            self._state = "READBACK_UNAVAILABLE"
                time.sleep(0.1)
            with self._lock:
                if self._receipt is receipt:
                    self._receipt = None
                self._running = False


class _AdmissionOperations:
    """Linearize each launch effect against synchronous Project invalidation."""
    def __init__(self, operations: Any, lock: Any, stop: threading.Event) -> None:
        self._operations, self._lock, self._stop = operations, lock, stop

    def __getattr__(self, name: str) -> Any:
        operation = getattr(self._operations, name)
        if name not in ("create_suspended", "resume_thread", "write_bootstrap"):
            return operation

        def admitted(*args: Any, **kwargs: Any) -> Any:
            with self._lock:
                if self._stop.is_set():
                    raise launch.LaunchError("BOOTSTRAP")
                return operation(*args, **kwargs)
        return admitted


_packaged_hosts: weakref.WeakSet[MeterControllerHost] = weakref.WeakSet()


def close_packaged_meter_hosts() -> None:
    for host in tuple(_packaged_hosts):
        host.close()


def packaged_meter_host(project_root: Path, project_id: str) -> MeterControllerHost | None:
    """Only the frozen application's embedded identity selects executable files."""
    if os.name != "nt" or getattr(sys, "frozen", False) is not True:
        return None
    try:
        identity = importlib.import_module("_bvp_task048_meter_identity")
        raw = identity.METER_FILES
        if type(raw) is not tuple or not 2 <= len(raw) <= 4096:
            return None
        files = tuple(launch.BundleFile(path, bytes.fromhex(digest)) for path, digest in raw)
        spec = launch.BundleSpec(str(Path(sys.executable).parent),
                                 r"_internal\_meter\bai-voice-capture-controller.exe", files,
                                 launch.Role.CONTROLLER)
        host = MeterControllerHost(SelectedProject(str(project_root), project_id), spec)
        _packaged_hosts.add(host)
        return host
    except Exception:
        return None
