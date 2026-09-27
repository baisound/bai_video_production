from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid
from typing import Any


REPORT_VERSION = "TASK102_PMST_N1A_REPORT_V1"
RUN_PREFIX = "bvp-task102-pmst-n1-"
PREDECESSOR = b'{"generation":1,"state":"predecessor"}'
SUCCESSOR = b'{"generation":2,"state":"successor"}'


class FeasibilityError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _sha256(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")


def validate_run_root(run_root: Path, temp_root: Path | None = None) -> Path:
    """Validate the exact pre-effect PMST-N1 placement boundary."""
    root = run_root.absolute()
    temp = (temp_root or Path(tempfile.gettempdir())).resolve(strict=True)
    if not root.name.startswith(RUN_PREFIX):
        raise FeasibilityError("RUN_ROOT_NAME_REJECTED")
    try:
        root.relative_to(temp)
    except ValueError:
        raise FeasibilityError("RUN_ROOT_OUTSIDE_SYSTEM_TEMP") from None
    anchor = Path(root.anchor)
    if root == anchor or root.parent == anchor:
        raise FeasibilityError("DRIVE_ROOT_PLACEMENT_REJECTED")
    if root.exists():
        raise FeasibilityError("RUN_ROOT_ALREADY_EXISTS")
    if root.parent.resolve(strict=True) != temp:
        raise FeasibilityError("RUN_ROOT_NOT_DIRECT_TEMP_CHILD")
    return root


def classify_recovery(
    *,
    witness_state: str | None,
    observed_sha256: str | None,
    predecessor_sha256: str,
    successor_sha256: str,
    continuous_exclusion: bool,
) -> str:
    """Closed recovery classification used by native and pure tests."""
    if witness_state == "TERMINAL_COMMITTED" and observed_sha256 == successor_sha256:
        return "COMMITTED_WITH_READBACK"
    if witness_state == "PREPARED" and continuous_exclusion:
        if observed_sha256 == predecessor_sha256:
            return "NOT_COMMITTED_PROVEN"
        if observed_sha256 == successor_sha256:
            return "COMMITTED_WITH_READBACK"
    return "COMMIT_OUTCOME_UNKNOWN"


def _require_windows() -> None:
    if os.name != "nt":
        raise FeasibilityError("WINDOWS_REQUIRED")


def _close_handle(handle: int) -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    if handle and not kernel.CloseHandle(wintypes.HANDLE(handle)):
        raise FeasibilityError("HANDLE_CLOSE_FAILED")


def _open_barrier(
    path: Path, *, directory: bool, deny_write: bool, writable: bool = False
) -> int:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create.restype = wintypes.HANDLE
    access = 0x80000000 | (0x40000000 if writable else 0)
    share = 0x1 if deny_write else 0x1 | 0x2  # never FILE_SHARE_DELETE
    flags = 0x00200000 | (0x02000000 if directory else 0)
    handle = create(str(path), access, share, None, 3, flags, None)
    invalid = ctypes.c_void_p(-1).value
    if handle in (None, 0, invalid):
        raise FeasibilityError("BARRIER_OPEN_FAILED")
    kernel.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
    kernel.SetHandleInformation.restype = wintypes.BOOL
    if not kernel.SetHandleInformation(handle, 1, 0):
        _close_handle(int(handle))
        raise FeasibilityError("HANDLE_INHERITANCE_REJECTED")
    return int(handle)


class _ByHandleFileInformation(ctypes.Structure):
    _fields_ = [
        ("attributes", wintypes.DWORD),
        ("creation_low", wintypes.DWORD),
        ("creation_high", wintypes.DWORD),
        ("access_low", wintypes.DWORD),
        ("access_high", wintypes.DWORD),
        ("write_low", wintypes.DWORD),
        ("write_high", wintypes.DWORD),
        ("volume_serial", wintypes.DWORD),
        ("size_high", wintypes.DWORD),
        ("size_low", wintypes.DWORD),
        ("links", wintypes.DWORD),
        ("index_high", wintypes.DWORD),
        ("index_low", wintypes.DWORD),
    ]


def _identity(handle: int) -> tuple[int, int, int, int, int]:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_ByHandleFileInformation),
    ]
    kernel.GetFileInformationByHandle.restype = wintypes.BOOL
    info = _ByHandleFileInformation()
    if not kernel.GetFileInformationByHandle(wintypes.HANDLE(handle), ctypes.byref(info)):
        raise FeasibilityError("IDENTITY_READ_FAILED")
    return (
        int(info.volume_serial),
        (int(info.index_high) << 32) | int(info.index_low),
        (int(info.size_high) << 32) | int(info.size_low),
        int(info.attributes),
        int(info.links),
    )


def _assert_plain_native_object(handle: int, *, regular_file: bool) -> None:
    _, _, _, attributes, links = _identity(handle)
    if attributes & 0x400:  # FILE_ATTRIBUTE_REPARSE_POINT
        raise FeasibilityError("UNSUPPORTED_TOPOLOGY")
    if regular_file and links != 1:
        raise FeasibilityError("UNSUPPORTED_TOPOLOGY")


def _volume_facts(path: Path) -> dict[str, object]:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetVolumeInformationW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPWSTR,
        wintypes.DWORD,
    ]
    kernel.GetVolumeInformationW.restype = wintypes.BOOL
    kernel.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
    kernel.GetDriveTypeW.restype = wintypes.UINT
    volume = ctypes.create_unicode_buffer(261)
    filesystem = ctypes.create_unicode_buffer(261)
    serial = wintypes.DWORD()
    maximum = wintypes.DWORD()
    flags = wintypes.DWORD()
    drive = os.path.splitdrive(str(path))[0] + "\\"
    if not kernel.GetVolumeInformationW(
        drive,
        volume,
        len(volume),
        ctypes.byref(serial),
        ctypes.byref(maximum),
        ctypes.byref(flags),
        filesystem,
        len(filesystem),
    ):
        raise FeasibilityError("VOLUME_READ_FAILED")
    drive_type = int(kernel.GetDriveTypeW(drive))
    if filesystem.value.upper() != "NTFS" or drive_type != 3:
        raise FeasibilityError("UNSUPPORTED_TOPOLOGY")
    return {"filesystem": "NTFS", "drive_type": "FIXED", "volume_serial": int(serial.value)}


def _current_user_sid() -> str:
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    token = wintypes.HANDLE()
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    advapi.OpenProcessToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    advapi.OpenProcessToken.restype = wintypes.BOOL
    advapi.GetTokenInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi.GetTokenInformation.restype = wintypes.BOOL
    advapi.ConvertSidToStringSidW.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.LPWSTR),
    ]
    advapi.ConvertSidToStringSidW.restype = wintypes.BOOL
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
        raise FeasibilityError("TOKEN_OPEN_FAILED")
    try:
        needed = wintypes.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(needed))
        if not needed.value:
            raise FeasibilityError("TOKEN_USER_READ_FAILED")
        storage = ctypes.create_string_buffer(needed.value)
        if not advapi.GetTokenInformation(token, 1, storage, needed, ctypes.byref(needed)):
            raise FeasibilityError("TOKEN_USER_READ_FAILED")
        sid_ptr = ctypes.c_void_p.from_buffer(storage).value
        rendered = wintypes.LPWSTR()
        if not advapi.ConvertSidToStringSidW(sid_ptr, ctypes.byref(rendered)):
            raise FeasibilityError("TOKEN_SID_FORMAT_FAILED")
        try:
            return rendered.value
        finally:
            kernel.LocalFree(rendered)
    finally:
        _close_handle(int(token.value))


def _security_descriptor(path: Path) -> tuple[str, bool]:
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    descriptor = ctypes.c_void_p()
    advapi.GetNamedSecurityInfoW.argtypes = [
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    advapi.GetNamedSecurityInfoW.restype = wintypes.DWORD
    advapi.GetSecurityDescriptorControl.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.WORD),
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi.GetSecurityDescriptorControl.restype = wintypes.BOOL
    advapi.GetSecurityDescriptorLength.argtypes = [ctypes.c_void_p]
    advapi.GetSecurityDescriptorLength.restype = wintypes.DWORD
    result = advapi.GetNamedSecurityInfoW(
        str(path), 1, 0x1 | 0x4, None, None, None, None, ctypes.byref(descriptor)
    )
    if result != 0 or not descriptor.value:
        raise FeasibilityError("ACL_READ_FAILED")
    try:
        control = wintypes.WORD()
        revision = wintypes.DWORD()
        if not advapi.GetSecurityDescriptorControl(
            descriptor, ctypes.byref(control), ctypes.byref(revision)
        ):
            raise FeasibilityError("ACL_CONTROL_READ_FAILED")
        length = int(advapi.GetSecurityDescriptorLength(descriptor))
        digest = _sha256(ctypes.string_at(descriptor, length))
        return digest, bool(int(control.value) & 0x1000)
    finally:
        kernel.LocalFree(descriptor)


def _protect_owned_acl(path: Path) -> str:
    sid = _current_user_sid()
    command = [
        "icacls.exe",
        str(path),
        "/inheritance:r",
        "/grant:r",
        f"*{sid}:(OI)(CI)F",
        "*S-1-5-18:(OI)(CI)F",
        "*S-1-5-32-544:(OI)(CI)F",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise FeasibilityError("ACL_APPLY_FAILED")
    first, protected = _security_descriptor(path)
    second, protected_again = _security_descriptor(path)
    if not protected or not protected_again or first != second:
        raise FeasibilityError("ACL_TOPOLOGY_UNPROVEN")
    return first


def _directory_flush(handle: int) -> None:
    ntdll = ctypes.WinDLL("ntdll")
    status_block = (ctypes.c_void_p * 2)()
    ntdll.NtFlushBuffersFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    ntdll.NtFlushBuffersFile.restype = ctypes.c_long
    status = int(ntdll.NtFlushBuffersFile(wintypes.HANDLE(handle), ctypes.byref(status_block)))
    if status < 0:
        raise FeasibilityError("DIRECTORY_FLUSH_FAILED")


def _flush_fd(fd: int) -> None:
    import msvcrt

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.FlushFileBuffers.argtypes = [wintypes.HANDLE]
    kernel.FlushFileBuffers.restype = wintypes.BOOL
    if not kernel.FlushFileBuffers(wintypes.HANDLE(msvcrt.get_osfhandle(fd))):
        raise FeasibilityError("FILE_FLUSH_FAILED")


class _RenameInfoHead(ctypes.Structure):
    _fields_ = [
        ("replace", wintypes.BOOLEAN),
        ("root", wintypes.HANDLE),
        ("name_length", wintypes.DWORD),
    ]


def _handle_replace(fd: int, destination: Path) -> None:
    import msvcrt

    encoded = os.path.abspath(os.fspath(destination)).encode("utf-16-le")
    offset = _RenameInfoHead.name_length.offset + ctypes.sizeof(wintypes.DWORD)
    storage = ctypes.create_string_buffer(
        offset + len(encoded) + ctypes.sizeof(wintypes.WCHAR)
    )
    head = _RenameInfoHead.from_buffer(storage)
    head.replace = 1
    head.root = wintypes.HANDLE()
    head.name_length = len(encoded)
    ctypes.memmove(ctypes.addressof(storage) + offset, encoded, len(encoded))
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.SetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel.SetFileInformationByHandle.restype = wintypes.BOOL
    if not kernel.SetFileInformationByHandle(
        wintypes.HANDLE(msvcrt.get_osfhandle(fd)), 3, storage, len(storage)
    ):
        raise FeasibilityError("HANDLE_REPLACE_FAILED")


def _open_stage(path: Path) -> int:
    import msvcrt

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel.CreateFileW.restype = wintypes.HANDLE
    # DELETE is required for FileRenameInfo; ordinary os.open does not request it.
    access = 0x80000000 | 0x40000000 | 0x00010000
    handle = kernel.CreateFileW(
        str(path), access, 0x1, None, 1, 0x00200000, None
    )  # CREATE_NEW | OPEN_REPARSE_POINT
    invalid = ctypes.c_void_p(-1).value
    if handle in (None, 0, invalid):
        raise FeasibilityError("STAGE_CREATE_FAILED")
    kernel.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
    kernel.SetHandleInformation.restype = wintypes.BOOL
    if not kernel.SetHandleInformation(handle, 1, 0):
        _close_handle(int(handle))
        raise FeasibilityError("HANDLE_INHERITANCE_REJECTED")
    try:
        return int(
            msvcrt.open_osfhandle(
                int(handle), os.O_RDWR | int(getattr(os, "O_BINARY", 0))
            )
        )
    except OSError:
        _close_handle(int(handle))
        raise FeasibilityError("STAGE_CREATE_FAILED") from None


def _barrier_child(path: Path, kind: str) -> int:
    try:
        if kind == "rename":
            os.replace(path, path.with_name(path.name + "-moved"))
        elif kind == "write":
            with path.open("r+b") as stream:
                stream.write(b"foreign")
        elif kind == "delete":
            path.unlink()
        else:
            return 3
    except (OSError, PermissionError):
        return 0
    return 2


def _run_barrier_attempt(path: Path, kind: str) -> None:
    result = subprocess.run(
        [sys.executable, __file__, "--barrier-child", kind, str(path)],
        close_fds=True,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise FeasibilityError("BARRIER_UNPROVEN")


class _SecurityAttributes(ctypes.Structure):
    _fields_ = [
        ("length", wintypes.DWORD),
        ("descriptor", ctypes.c_void_p),
        ("inherit", wintypes.BOOL),
    ]


def _pipe_client(name: str) -> int:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.GetNamedPipeServerProcessId.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.ULONG),
    ]
    kernel.GetNamedPipeServerProcessId.restype = wintypes.BOOL
    kernel.ReadFile.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    kernel.ReadFile.restype = wintypes.BOOL
    kernel.WriteFile.argtypes = kernel.ReadFile.argtypes
    kernel.WriteFile.restype = wintypes.BOOL
    handle = kernel.CreateFileW(name, 0xC0000000, 0, None, 3, 0, None)
    invalid = ctypes.c_void_p(-1).value
    if handle in (None, 0, invalid):
        return 4
    try:
        server_pid = wintypes.ULONG()
        if not kernel.GetNamedPipeServerProcessId(handle, ctypes.byref(server_pid)):
            return 5
        payload = _canonical_json(
            {"client_pid": os.getpid(), "server_pid_observed": int(server_pid.value)}
        )
        written = wintypes.DWORD()
        if not kernel.WriteFile(handle, payload, len(payload), ctypes.byref(written), None):
            return 6
        buffer = ctypes.create_string_buffer(16)
        read = wintypes.DWORD()
        if not kernel.ReadFile(handle, buffer, len(buffer), ctypes.byref(read), None):
            return 7
        return 0 if buffer.raw[: read.value] == b"ACK" else 8
    finally:
        _close_handle(int(handle))


def _pipe_identity_proof() -> dict[str, object]:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    name = rf"\\.\pipe\BvpTask102PmstN1-{uuid.uuid4().hex}"
    descriptor = ctypes.c_void_p()
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p,
    ]
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    kernel.CreateNamedPipeW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(_SecurityAttributes),
    ]
    kernel.CreateNamedPipeW.restype = wintypes.HANDLE
    kernel.ConnectNamedPipe.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel.ConnectNamedPipe.restype = wintypes.BOOL
    kernel.GetNamedPipeClientProcessId.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.ULONG),
    ]
    kernel.GetNamedPipeClientProcessId.restype = wintypes.BOOL
    kernel.ReadFile.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    kernel.ReadFile.restype = wintypes.BOOL
    kernel.WriteFile.argtypes = kernel.ReadFile.argtypes
    kernel.WriteFile.restype = wintypes.BOOL
    sddl = f"D:P(A;;GA;;;SY)(A;;GA;;;BA)(A;;GA;;;{_current_user_sid()})"
    if not advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        sddl, 1, ctypes.byref(descriptor), None
    ):
        raise FeasibilityError("PIPE_DESCRIPTOR_FAILED")
    attributes = _SecurityAttributes(ctypes.sizeof(_SecurityAttributes), descriptor, False)
    access = 0x3 | 0x00080000  # DUPLEX | FILE_FLAG_FIRST_PIPE_INSTANCE
    mode = 0x4 | 0x2 | 0x8  # MESSAGE | READMODE_MESSAGE | REJECT_REMOTE_CLIENTS
    invalid = ctypes.c_void_p(-1).value
    # Permit a second ordinary instance so that its rejection proves
    # FILE_FLAG_FIRST_PIPE_INSTANCE, not merely max-instance exhaustion.
    pipe = kernel.CreateNamedPipeW(
        name, access, mode, 2, 4096, 4096, 5000, ctypes.byref(attributes)
    )
    if pipe in (None, 0, invalid):
        kernel.LocalFree(descriptor)
        raise FeasibilityError("PIPE_CREATE_FAILED")
    client: subprocess.Popen[bytes] | None = None
    try:
        second = kernel.CreateNamedPipeW(
            name, access, mode, 2, 4096, 4096, 5000, ctypes.byref(attributes)
        )
        if second not in (None, 0, invalid):
            _close_handle(int(second))
            raise FeasibilityError("PIPE_FIRST_INSTANCE_UNPROVEN")
        if ctypes.get_last_error() != 5:  # ERROR_ACCESS_DENIED from FIRST_PIPE_INSTANCE
            raise FeasibilityError("PIPE_FIRST_INSTANCE_UNPROVEN")
        client = subprocess.Popen(
            [sys.executable, __file__, "--pipe-client", name],
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        connected = bool(kernel.ConnectNamedPipe(pipe, None))
        if not connected and ctypes.get_last_error() != 535:  # ERROR_PIPE_CONNECTED
            client.kill()
            client.wait()
            raise FeasibilityError("PIPE_CONNECT_FAILED")
        client_pid = wintypes.ULONG()
        if not kernel.GetNamedPipeClientProcessId(pipe, ctypes.byref(client_pid)):
            raise FeasibilityError("PIPE_CLIENT_PID_FAILED")
        buffer = ctypes.create_string_buffer(512)
        read = wintypes.DWORD()
        if not kernel.ReadFile(pipe, buffer, len(buffer), ctypes.byref(read), None):
            raise FeasibilityError("PIPE_READ_FAILED")
        payload = json.loads(buffer.raw[: read.value].decode("ascii"))
        if payload != {"client_pid": client.pid, "server_pid_observed": os.getpid()}:
            raise FeasibilityError("PIPE_IDENTITY_UNPROVEN")
        written = wintypes.DWORD()
        if not kernel.WriteFile(pipe, b"ACK", 3, ctypes.byref(written), None):
            raise FeasibilityError("PIPE_WRITE_FAILED")
        if client.wait(timeout=10) != 0:
            raise FeasibilityError("PIPE_CLIENT_FAILED")
        return {
            "explicit_protected_descriptor": True,
            "first_instance_rejection": True,
            "remote_client_rejection_flag": True,
            "server_client_pid_readback": True,
        }
    finally:
        if client is not None and client.poll() is None:
            client.kill()
            client.wait()
        _close_handle(int(pipe))
        kernel.LocalFree(descriptor)


def _write_durable(path: Path, body: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_BINARY", 0), 0o600)
    try:
        if os.write(fd, body) != len(body):
            raise FeasibilityError("SHORT_WRITE")
        _flush_fd(fd)
    finally:
        os.close(fd)


def _crash_worker(root: Path, seam: str) -> int:
    manifest = root / "manifest.json"
    witness = root / "witness.json"
    _write_durable(witness, _canonical_json({"state": "PREPARED"}))
    if seam == "before_replace":
        os._exit(71)
    stage = root / "stage.json"
    _write_durable(stage, SUCCESSOR)
    os.replace(stage, manifest)
    if seam == "after_replace":
        os._exit(72)
    _write_durable(witness, _canonical_json({"state": "TERMINAL_COMMITTED"}))
    os._exit(73)


def _crash_matrix(root: Path) -> dict[str, str]:
    expected = {
        "before_replace": "NOT_COMMITTED_PROVEN",
        "after_replace": "COMMITTED_WITH_READBACK",
        "after_terminal": "COMMITTED_WITH_READBACK",
    }
    results: dict[str, str] = {}
    for seam, expected_result in expected.items():
        seam_root = root / ("crash-" + seam)
        seam_root.mkdir()
        _write_durable(seam_root / "manifest.json", PREDECESSOR)
        child = subprocess.run(
            [sys.executable, __file__, "--crash-worker", seam, str(seam_root)],
            close_fds=True,
            check=False,
        )
        if child.returncode not in {71, 72, 73}:
            raise FeasibilityError("CRASH_WORKER_FAILED")
        observed = _sha256((seam_root / "manifest.json").read_bytes())
        witness = json.loads((seam_root / "witness.json").read_text(encoding="ascii"))["state"]
        result = classify_recovery(
            witness_state=witness,
            observed_sha256=observed,
            predecessor_sha256=_sha256(PREDECESSOR),
            successor_sha256=_sha256(SUCCESSOR),
            continuous_exclusion=True,
        )
        if result != expected_result:
            raise FeasibilityError("RECOVERY_UNPROVEN")
        results[seam] = result
    return results


def run_n1a(run_root: Path) -> dict[str, object]:
    _require_windows()
    root = validate_run_root(run_root)
    root.mkdir(mode=0o700)
    control = root / "control"
    control.mkdir()
    manifest = control / "manifest.json"
    manifest.write_bytes(PREDECESSOR)
    root_handle = control_handle = manifest_handle = 0
    try:
        volume = _volume_facts(root)
        acl_digest = _protect_owned_acl(control)
        root_handle = _open_barrier(
            root, directory=True, deny_write=False, writable=True
        )
        control_handle = _open_barrier(
            control, directory=True, deny_write=False, writable=True
        )
        manifest_handle = _open_barrier(manifest, directory=False, deny_write=True)
        _assert_plain_native_object(root_handle, regular_file=False)
        _assert_plain_native_object(control_handle, regular_file=False)
        _assert_plain_native_object(manifest_handle, regular_file=True)
        predecessor_identity = _identity(manifest_handle)
        for path, action in (
            (root, "rename"),
            (control, "rename"),
            (manifest, "rename"),
            (manifest, "write"),
            (manifest, "delete"),
        ):
            _run_barrier_attempt(path, action)
        if not root.is_dir() or not control.is_dir() or manifest.read_bytes() != PREDECESSOR:
            raise FeasibilityError("BARRIER_UNPROVEN")
        _close_handle(manifest_handle)
        manifest_handle = 0
        stage = control / ("stage-" + uuid.uuid4().hex + ".json")
        stage_fd = _open_stage(stage)
        try:
            if os.write(stage_fd, SUCCESSOR) != len(SUCCESSOR):
                raise FeasibilityError("SHORT_WRITE")
            _flush_fd(stage_fd)
            _handle_replace(stage_fd, manifest)
        finally:
            os.close(stage_fd)
        manifest_handle = _open_barrier(manifest, directory=False, deny_write=True)
        _assert_plain_native_object(manifest_handle, regular_file=True)
        successor_identity = _identity(manifest_handle)
        _directory_flush(control_handle)
        if manifest.read_bytes() != SUCCESSOR:
            raise FeasibilityError("DURABILITY_UNPROVEN")
        if predecessor_identity[:2] == successor_identity[:2]:
            raise FeasibilityError("REPLACEMENT_UNPROVEN")
        crash = _crash_matrix(root)
        pipe = _pipe_identity_proof()
        final_acl_digest, final_acl_protected = _security_descriptor(control)
        if not final_acl_protected or final_acl_digest != acl_digest:
            raise FeasibilityError("ACL_TOPOLOGY_UNPROVEN")
        report: dict[str, Any] = {
            "report_version": REPORT_VERSION,
            "result": "PASS",
            "run_root_class": "UNIQUE_SYSTEM_TEMP_CHILD",
            "topology": volume,
            "barriers": {
                "non_inheritable": True,
                "root_control_no_delete_share": True,
                "manifest_no_write_delete_share": True,
                "second_process_rejections": 5,
            },
            "replacement": {
                "handle_bound_same_volume": True,
                "predecessor_sha256": _sha256(PREDECESSOR),
                "successor_sha256": _sha256(SUCCESSOR),
                "physical_identity_changed": True,
            },
            "durability": {
                "file_flush": "PASS",
                "directory_flush": "PASS",
                "process_kill_only_no_power_loss_claim": True,
            },
            "crash_recovery": crash,
            "acl": {"protected": True, "descriptor_sha256": acl_digest},
            "pipe": pipe,
            "service_sid": {"result": "NOT_RUN", "reason": "SEPARATE_PMST_N1B_GATE"},
            "residuals": ["OWNED_RUN_ROOT_RETAINED_FOR_EVIDENCE"],
        }
        report["report_sha256"] = _sha256(_canonical_json(report))
        return report
    finally:
        for handle in (manifest_handle, control_handle, root_handle):
            if handle:
                _close_handle(handle)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--barrier-child", nargs=2, metavar=("ACTION", "PATH"))
    parser.add_argument("--pipe-client")
    parser.add_argument("--crash-worker", nargs=2, metavar=("SEAM", "ROOT"))
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    if args.barrier_child:
        return _barrier_child(Path(args.barrier_child[1]), args.barrier_child[0])
    if args.pipe_client:
        return _pipe_client(args.pipe_client)
    if args.crash_worker:
        return _crash_worker(Path(args.crash_worker[1]), args.crash_worker[0])
    if args.run_root is None or args.report is None:
        parser.error("--run-root and --report are required")
    try:
        report = run_n1a(args.run_root)
        args.report.write_bytes(_canonical_json(report) + b"\n")
        return 0
    except FeasibilityError as exc:
        failure = {
            "report_version": REPORT_VERSION,
            "result": "FAIL",
            "reason_code": exc.code,
        }
        failure["report_sha256"] = _sha256(_canonical_json(failure))
        # Never create a rejected destination while reporting a pre-effect
        # placement failure. A failure report is written only inside the exact
        # run root after that owned root exists.
        if args.run_root.is_dir() and args.report.parent == args.run_root:
            args.report.write_bytes(_canonical_json(failure) + b"\n")
        else:
            print(exc.code, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
