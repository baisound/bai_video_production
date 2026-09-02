from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable, Iterator

from .serialization import canonical_json_bytes, sha256_bytes

FailureInjector = Callable[[str, Path], None]
Validator = Callable[[Any], None]


@contextmanager
def exclusive_file_update_lock(path: str | Path) -> Iterator[None]:
    """Serialize a bounded read-check-replace cycle across processes."""
    target = Path(path)
    lock_path = target.with_name(f".{target.name}.lock")
    if lock_path.is_symlink() or (lock_path.exists() and not lock_path.is_file()):
        raise ValueError("atomic update lock must be a regular non-symlink file")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    # Raw I/O makes the single-byte marker write immediate.  A buffered handle
    # can defer that write until a peer already owns the byte-zero lock, and a
    # later seek in cleanup can then retry the same failing flush.
    with lock_path.open("a+b", buffering=0) as handle:
        handle.seek(0)
        locked = False
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            locked = True
            # A Windows byte-range lock can cover byte zero even while the
            # newly created file is empty.  Initialize the marker only after
            # acquiring that lock.  Raw I/O has no deferred flush that could
            # write into a region already locked by the other contender.
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"0")
            handle.seek(0)
            yield
        finally:
            if locked:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

@dataclass(frozen=True, slots=True)
class AtomicWriteResult:
    path: Path
    checksum: str
    bytes_written: int

class AtomicJsonWriter:
    @staticmethod
    def write(
        path: str | Path,
        value: Any,
        *,
        validator: Validator | None = None,
        failure_injector: FailureInjector | None = None,
    ) -> AtomicWriteResult:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = canonical_json_bytes(value) + b"\n"
        fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb", closefd=True) as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            if failure_injector:
                failure_injector("after_fsync", tmp)
            parsed = json.loads(tmp.read_text(encoding="utf-8"))
            if validator:
                validator(parsed)
            if failure_injector:
                failure_injector("after_validation", tmp)
            checksum = sha256_bytes(data.rstrip(b"\n"))
            if failure_injector:
                failure_injector("before_replace", tmp)
            os.replace(tmp, target)
            # Persist directory entry when the platform supports directory fsync.
            try:
                dir_fd = os.open(target.parent, os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except OSError:
                pass
            return AtomicWriteResult(target, checksum, len(data))
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            finally:
                raise
