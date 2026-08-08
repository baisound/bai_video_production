from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable

from .serialization import canonical_json_bytes, sha256_bytes

FailureInjector = Callable[[str, Path], None]
Validator = Callable[[Any], None]

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
