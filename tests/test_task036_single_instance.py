from __future__ import annotations

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.task036_single_instance import Task036SingleInstanceGuard


class Kernel32:
    def __init__(self, *, last_error: int = 0, handle: object | None = object()) -> None:
        self.last_error = last_error
        self.handle = handle
        self.closed = []

    def CreateMutexW(self, _attributes, _initial_owner, _name):
        return self.handle

    def GetLastError(self):
        return self.last_error

    def CloseHandle(self, handle):
        self.closed.append(handle)
        return True


def test_first_instance_holds_then_releases_the_os_mutex():
    kernel32 = Kernel32()
    lease = Task036SingleInstanceGuard(kernel32=kernel32).acquire()
    assert kernel32.closed == []
    lease.close()
    assert kernel32.closed == [kernel32.handle]


def test_second_instance_is_rejected_and_its_handle_is_closed():
    kernel32 = Kernel32(last_error=183)
    with pytest.raises(ProductError) as rejected:
        Task036SingleInstanceGuard(kernel32=kernel32).acquire()
    assert rejected.value.code == "ERR_TASK036_ALREADY_RUNNING"
    assert kernel32.closed == [kernel32.handle]


def test_unavailable_mutex_fails_closed():
    kernel32 = Kernel32(handle=None)
    with pytest.raises(ProductError) as rejected:
        Task036SingleInstanceGuard(kernel32=kernel32).acquire()
    assert rejected.value.code == "ERR_TASK036_SINGLE_INSTANCE_UNAVAILABLE"