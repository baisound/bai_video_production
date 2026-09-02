from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
from threading import Barrier, Lock
import time
from types import SimpleNamespace

import pytest

import ai_video_production.atomic as atomic_module
from ai_video_production.atomic import AtomicJsonWriter, exclusive_file_update_lock

def test_atomic_write_replaces_only_after_validation(tmp_path):
    target = tmp_path / "manifest.json"
    target.write_text('{"old":true}\n', encoding="utf-8")
    def fail(stage, _tmp):
        if stage == "before_replace": raise RuntimeError("fault")
    with pytest.raises(RuntimeError):
        AtomicJsonWriter.write(target, {"new": True}, failure_injector=fail)
    assert json.loads(target.read_text()) == {"old": True}
    assert not list(tmp_path.glob("*.tmp"))

def test_atomic_write_success(tmp_path):
    target = tmp_path / "manifest.json"
    result = AtomicJsonWriter.write(target, {"b":2,"a":1})
    assert json.loads(target.read_text()) == {"a":1,"b":2}
    assert result.checksum.startswith("sha256:")


def test_empty_lock_marker_is_written_only_after_windows_lock_acquisition(
    tmp_path, monkeypatch
):
    events = []

    class FakeHandle:
        def __enter__(self):
            events.append("open")
            return self

        def __exit__(self, *_):
            events.append("close")

        def fileno(self):
            return 17

        def seek(self, offset, whence=os.SEEK_SET):
            events.append(("seek", offset, whence))
            return 0

        def write(self, value):
            events.append(("write", value))
            return len(value)

    fake_msvcrt = SimpleNamespace(LK_LOCK=1, LK_UNLCK=2)

    def locking(fd, mode, count):
        events.append(("locking", fd, mode, count))

    fake_msvcrt.locking = locking
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)
    monkeypatch.setattr(
        atomic_module, "os", SimpleNamespace(name="nt", SEEK_END=os.SEEK_END)
    )
    monkeypatch.setattr(Path, "open", lambda *_args, **_kwargs: FakeHandle())

    with exclusive_file_update_lock(tmp_path / "manifest.json"):
        events.append("yield")

    acquire = events.index(("locking", 17, fake_msvcrt.LK_LOCK, 1))
    marker_write = events.index(("write", b"0"))
    release = events.index(("locking", 17, fake_msvcrt.LK_UNLCK, 1))
    assert acquire < marker_write < events.index("yield") < release


def test_lock_acquisition_failure_never_initializes_marker_or_unlocks(
    tmp_path, monkeypatch
):
    events = []

    class FakeHandle:
        def __enter__(self):
            events.append("open")
            return self

        def __exit__(self, *_):
            events.append("close")

        def fileno(self):
            return 19

        def seek(self, offset, whence=os.SEEK_SET):
            events.append(("seek", offset, whence))
            return 0

        def write(self, value):
            events.append(("write", value))
            return len(value)

    fake_msvcrt = SimpleNamespace(LK_LOCK=1, LK_UNLCK=2)

    def locking(fd, mode, count):
        events.append(("locking", fd, mode, count))
        if mode == fake_msvcrt.LK_LOCK:
            raise PermissionError("contended")

    fake_msvcrt.locking = locking
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)
    monkeypatch.setattr(
        atomic_module, "os", SimpleNamespace(name="nt", SEEK_END=os.SEEK_END)
    )
    monkeypatch.setattr(Path, "open", lambda *_args, **_kwargs: FakeHandle())

    with pytest.raises(PermissionError, match="contended"):
        with exclusive_file_update_lock(tmp_path / "manifest.json"):
            raise AssertionError("lock body must not run")

    assert not any(isinstance(event, tuple) and event[0] == "write" for event in events)
    assert ("locking", 19, fake_msvcrt.LK_UNLCK, 1) not in events
    assert events[-1] == "close"


def test_marker_write_failure_releases_windows_lock_without_entering_body(
    tmp_path, monkeypatch
):
    events = []

    class FakeHandle:
        def __enter__(self):
            events.append("open")
            return self

        def __exit__(self, *_):
            events.append("close")

        def fileno(self):
            return 23

        def seek(self, offset, whence=os.SEEK_SET):
            events.append(("seek", offset, whence))
            return 0

        def write(self, value):
            events.append(("write", value))
            if not writes:
                writes.append(value)
                raise OSError("marker write failed")
            return len(value)

    fake_msvcrt = SimpleNamespace(LK_LOCK=1, LK_UNLCK=2)
    writes = []

    def locking(fd, mode, count):
        events.append(("locking", fd, mode, count))

    fake_msvcrt.locking = locking
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)
    monkeypatch.setattr(
        atomic_module, "os", SimpleNamespace(name="nt", SEEK_END=os.SEEK_END)
    )
    monkeypatch.setattr(Path, "open", lambda *_args, **_kwargs: FakeHandle())

    with pytest.raises(OSError, match="marker write failed"):
        with exclusive_file_update_lock(tmp_path / "manifest.json"):
            raise AssertionError("lock body must not run")

    acquire = events.index(("locking", 23, fake_msvcrt.LK_LOCK, 1))
    write = events.index(("write", b"0"))
    release = events.index(("locking", 23, fake_msvcrt.LK_UNLCK, 1))
    assert acquire < write < release < events.index("close")

    with exclusive_file_update_lock(tmp_path / "manifest.json"):
        events.append("reacquired")
    assert "reacquired" in events


def test_existing_lock_marker_is_preserved_and_body_exception_releases_lock(tmp_path):
    target = tmp_path / "manifest.json"
    lock_path = tmp_path / ".manifest.json.lock"
    lock_path.write_bytes(b"existing")

    with pytest.raises(RuntimeError, match="body failed"):
        with exclusive_file_update_lock(target):
            raise RuntimeError("body failed")

    with exclusive_file_update_lock(target):
        pass
    assert lock_path.read_bytes() == b"existing"


def test_fresh_same_path_contenders_serialize_and_initialize_one_marker(tmp_path):
    target = tmp_path / "manifest.json"
    barrier = Barrier(8)
    state_lock = Lock()
    active = 0
    peak = 0

    def enter_once(_):
        nonlocal active, peak
        barrier.wait()
        with exclusive_file_update_lock(target):
            with state_lock:
                active += 1
                peak = max(peak, active)
            time.sleep(0.005)
            with state_lock:
                active -= 1

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(enter_once, range(8)))

    assert peak == 1
    assert (tmp_path / ".manifest.json.lock").read_bytes() == b"0"


def test_nonregular_and_symlink_lock_paths_fail_before_target_effect(tmp_path):
    target = tmp_path / "manifest.json"
    lock_path = tmp_path / ".manifest.json.lock"
    lock_path.mkdir()
    with pytest.raises(ValueError, match="regular non-symlink"):
        with exclusive_file_update_lock(target):
            raise AssertionError("lock body must not run")
    assert not target.exists()

    lock_path.rmdir()
    symlink_target = tmp_path / "foreign.lock"
    symlink_target.write_bytes(b"foreign")
    try:
        lock_path.symlink_to(symlink_target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ValueError, match="regular non-symlink"):
        with exclusive_file_update_lock(target):
            raise AssertionError("lock body must not run")
    assert symlink_target.read_bytes() == b"foreign"
    assert not target.exists()
