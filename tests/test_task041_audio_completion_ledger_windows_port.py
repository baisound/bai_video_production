from __future__ import annotations

import ast
import ctypes
from pathlib import Path

import pytest

import ai_video_production.audio_completion_ledger_windows_port as native


ROOT = Path(__file__).resolve().parents[1]


def test_exact_access_share_flags_and_lock_range_are_frozen():
    assert native.DIRECTORY_SHARE == native.FILE_SHARE_READ | native.FILE_SHARE_WRITE
    assert not native.DIRECTORY_SHARE & native.FILE_SHARE_DELETE
    assert native.PENDING_ACCESS & native.DELETE
    assert native.PENDING_SHARE == native.FILE_SHARE_READ
    assert native.PENDING_FLAGS == native.FILE_FLAG_OPEN_REPARSE_POINT | native.FILE_FLAG_WRITE_THROUGH
    assert native.FINAL_SHARE == native.FILE_SHARE_READ
    assert native.FILE_RENAME_INFO_EX_CLASS == 22 and native.FILE_RENAME_FLAGS_NONE == 0


class _LockKernel:
    def __init__(self, *, success=True, error=0): self.success = success; self.error = error; self.calls = []
    def LockFileEx(self, *args): self.calls.append(args); return self.success
    def UnlockFileEx(self, *args): self.calls.append(args); return self.success


def _port_with_kernel(kernel):
    port = object.__new__(native.CtypesWindowsLedgerPort); port._kernel = kernel
    return port


def test_lockfileex_exclusive_immediate_whole_range_and_busy_no_retry(monkeypatch):
    kernel = _LockKernel(); port = _port_with_kernel(kernel); port.lock(99)
    call = kernel.calls[0]
    assert call[1] == native.LOCKFILE_EXCLUSIVE_LOCK | native.LOCKFILE_FAIL_IMMEDIATELY
    assert call[3:5] == (0xFFFFFFFF, 0xFFFFFFFF) and len(kernel.calls) == 1
    busy = _LockKernel(success=False, error=native.ERROR_LOCK_VIOLATION)
    monkeypatch.setattr(native.ctypes, "get_last_error", lambda: native.ERROR_LOCK_VIOLATION, raising=False)
    with pytest.raises(native.NativePortError, match="LOCK_BUSY"):
        _port_with_kernel(busy).lock(99)
    assert len(busy.calls) == 1


@pytest.mark.parametrize("name", ["", ".", "..", "a/b", "a\\b", "é", "x" * 256,
    "bad\x00name", "bad\x01name", "trailing.", "trailing ", "CON", "con.txt",
    "NUL.json", "COM1", "lpt9.dat"])
def test_relative_child_name_is_canonical_ascii_or_rejected(name):
    with pytest.raises(native.NativePortError): native._safe_component(name)
    assert native._safe_component(".global.lock") == ".global.lock"
    assert native._safe_component("a" * 64 + "-00000001.json").endswith(".json")


def test_dacl_policy_behavior_distinguishes_root_child_order_type_and_private_access():
    assert native._validate_ace_policy(role="private_child", ace_type=0,
        ace_flags=native._INHERITED_ACE, mask=native.GENERIC_READ,
        sid_is_allowed=True, allow_seen=False) is True
    with pytest.raises(native.NativePortError, match="DACL_NONCANONICAL_ACE"):
        native._validate_ace_policy(role="private_root", ace_type=0,
            ace_flags=native._INHERITED_ACE, mask=native.GENERIC_READ,
            sid_is_allowed=True, allow_seen=False)
    with pytest.raises(native.NativePortError, match="DACL_UNSUPPORTED_ACE"):
        native._validate_ace_policy(role="private_child", ace_type=9,
            ace_flags=0, mask=0, sid_is_allowed=True, allow_seen=False)
    with pytest.raises(native.NativePortError, match="DACL_PRIVACY_POLICY_FAILED"):
        native._validate_ace_policy(role="private_child", ace_type=0,
            ace_flags=0, mask=native.GENERIC_READ,
            sid_is_allowed=False, allow_seen=False)
    with pytest.raises(native.NativePortError, match="DACL_NONCANONICAL_ORDER"):
        native._validate_ace_policy(role="private_child", ace_type=1,
            ace_flags=0, mask=0, sid_is_allowed=True, allow_seen=True)


def test_non_windows_factory_fails_before_backend_construction(monkeypatch):
    calls = []
    monkeypatch.setattr(native.os, "name", "posix")
    monkeypatch.setattr(native, "CtypesWindowsLedgerPort", lambda: calls.append(True))
    with pytest.raises(native.NativePortError, match="UNSUPPORTED_PLATFORM"):
        native.create_production_port()
    assert calls == []


class _HandleKernel:
    def __init__(self, *, set_ok=True, get_ok=True, flags=0, close_ok=True, localfree=0):
        self.set_ok, self.get_ok, self.flags = set_ok, get_ok, flags
        self.close_ok, self.localfree = close_ok, localfree
    def SetHandleInformation(self, *args): return self.set_ok
    def GetHandleInformation(self, handle, pointer):
        pointer._obj.value = self.flags
        return self.get_ok
    def CloseHandle(self, handle): return self.close_ok
    def LocalFree(self, pointer): return self.localfree


def _tracked_port(kernel):
    port = object.__new__(native.CtypesWindowsLedgerPort)
    port._kernel = kernel; port._tracked_handles = set(); port._native_allocations = set()
    return port


def test_native_handle_and_local_allocation_cleanup_faults_retain_bounded_coordinates():
    retained = _tracked_port(_HandleKernel(set_ok=False, close_ok=False))
    with pytest.raises(native.NativePortError) as caught:
        retained._noninherit(41)
    assert caught.value.unreleased_handle_count == 1
    assert retained.resource_counts() == (1, 0)

    released = _tracked_port(_HandleKernel(set_ok=False, close_ok=True))
    with pytest.raises(native.NativePortError) as caught:
        released._noninherit(42)
    assert caught.value.unreleased_handle_count == 0
    assert released.resource_counts() == (0, 0)

    allocation = _tracked_port(_HandleKernel(localfree=1))
    allocation._native_allocations.add(99)
    with pytest.raises(native.NativePortError) as caught:
        allocation._release_local(ctypes.c_void_p(99))
    assert caught.value.unreleased_native_allocation_count == 1
    allocation._kernel.localfree = 0
    allocation._release_local(ctypes.c_void_p(99))
    assert allocation.resource_counts() == (0, 0)

    bounded = native.NativePortError(
        "SYNTHETIC_RESOURCE_FAULT", unreleased_handle_count=10_000)
    assert bounded.unreleased_handle_count == native.MAX_TRACKED_HANDLES == 32


def test_ntquery_status_and_malformed_directory_information_fail_closed():
    class Ntdll:
        def __init__(self, result): self.result = result
        def NtQueryDirectoryFile(self, *args):
            args[4]._obj.Information = 4
            return self.result
    port = object.__new__(native.CtypesWindowsLedgerPort)
    port._ntdll = Ntdll(native._STATUS_NO_MORE_FILES)
    assert port.enumerate_relative(7) == ()
    port._ntdll = Ntdll(0)
    with pytest.raises(native.NativePortError, match="MALFORMED_DIRECTORY_ENUMERATION"):
        port.enumerate_relative(7)
    assert ctypes.sizeof(native._IO_STATUS_BLOCK) >= ctypes.sizeof(ctypes.c_void_p) * 2
    assert native._STATUS_NO_MORE_FILES < 0


def test_native_source_has_only_root_createfile_and_handle_relative_children_enumeration():
    path = ROOT / "src" / "ai_video_production" / "audio_completion_ledger_windows_port.py"
    source = path.read_text(encoding="utf-8"); ast.parse(source)
    assert source.count("CreateFileW(") == 1
    assert "NtCreateFile(" in source and "RootDirectory" in source
    assert "NtQueryDirectoryFile(" in source
    for forbidden in ("FindFirstFileW(", "FindNextFileW(", "os.open", "pathlib.Path", "glob(", "scandir("):
        assert forbidden not in source


def test_rename_uses_class22_flags0_root_relative_ascii_and_no_fallback():
    class Kernel:
        def __init__(self): self.calls = []
        def SetFileInformationByHandle(self, *args): self.calls.append(args); return True
    kernel = Kernel(); port = _port_with_kernel(kernel)
    port.rename_no_replace(5, 7, "a" * 64 + "-00000001.json")
    call = kernel.calls[0]
    assert call[1] == 22 and len(kernel.calls) == 1
    head = native._FILE_RENAME_INFO_EX_HEAD.from_address(ctypes.addressof(call[2]))
    assert head.Flags == 0 and head.RootDirectory == 7
    assert head.FileNameLength == len(("a" * 64 + "-00000001.json").encode("utf-16-le"))
    offset = native._FILE_RENAME_INFO_EX_HEAD.FileNameLength.offset + ctypes.sizeof(native.wintypes.DWORD)
    observed = ctypes.string_at(ctypes.addressof(call[2]) + offset, head.FileNameLength)
    assert observed.decode("utf-16-le") == "a" * 64 + "-00000001.json"


def test_no_directory_flush_acl_mutation_elevation_network_or_native_effect_in_tests():
    source = (ROOT / "src" / "ai_video_production" / "audio_completion_ledger_windows_port.py").read_text(encoding="utf-8")
    assert "FlushFileBuffers(directory" not in source
    for forbidden in ("SetSecurityInfo", "SetNamedSecurityInfo", "ShellExecute", "runas", "socket", "requests", "subprocess"):
        assert forbidden not in source
    assert "SECURITY_DESCRIPTOR_LOCALFREE_FAILED" in source
    assert "IsValidSid" in source and "GetLengthSid" in source
    assert 'security_role == "ancestor"' in source
    assert '{"private_root", "private_child"}' in source and 'role == "private_root"' in source
