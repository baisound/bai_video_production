"""TASK-059 P1C-B bounded process controller for the PPK helper.

The controller owns only a fixed helper launch, anonymous-pipe frame transport,
timeouts, and terminate/kill cleanup. Protocol ordering remains in the P1C
wire module; PPK authentication and custody remain in P1A/P1B.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
import hashlib
import math
import ntpath
import os
from pathlib import Path
import stat
import subprocess
import threading
import time
from typing import Any, BinaryIO, Callable, Iterator, Mapping

from .owner_signing_key_ppk_process_wire import (
    MAX_FRAME_BYTES,
    PROTOCOL_VERSION,
    PpkProcessWireError,
    decode_frame,
    encode_frame,
)


HELPER_MODULE = "ai_video_production.owner_signing_key_ppk_helper"
PACKAGED_HELPER_FILENAME = "BAI Video Production Key Helper.exe"
MAX_PACKAGED_HELPER_BYTES = 128 * 1024 * 1024
HEADER_TIMEOUT_SECONDS = 5.0
FRAME_TIMEOUT_SECONDS = 10.0
ATTEMPT_TIMEOUT_SECONDS = 300.0
STOP_TIMEOUT_SECONDS = 2.0
_PARENT_FRAME_TYPES = frozenset({"HELLO", "AUTH_REQUEST", "CONFIRM", "CANCEL"})
_HELPER_FRAME_TYPES = frozenset({"HELLO_ACCEPTED", "READY", "COMPLETED", "FAILED"})
_HELPER_ENV_ALLOWLIST = frozenset(
    {"COMSPEC", "PATH", "PATHEXT", "PYTHONIOENCODING", "PYTHONUTF8",
     "SYSTEMROOT", "TEMP", "TMP", "WINDIR"}
)


class PpkHelperProcessError(RuntimeError):
    """Body-free controller error carrying only a fixed public code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)

    def __repr__(self) -> str:
        return f"PpkHelperProcessError(code={self.code!r})"


def _error(code: str) -> PpkHelperProcessError:
    return PpkHelperProcessError(code)


def _bounded_timeout(value: object, *, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("timeout must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0 or result > maximum:
        raise ValueError("timeout is outside the bounded process contract")
    return result


class _PpkHelperIdentityError(ValueError):
    pass


class PpkHelperLaunchMode(str, Enum):
    DEVELOPMENT_PYTHON_MODULE = "DEVELOPMENT_PYTHON_MODULE"
    PACKAGED_HELPER = "PACKAGED_HELPER"


@dataclass(frozen=True, slots=True)
class PpkHelperLaunchSpec:
    """Fixed non-secret argv for one packaged helper attempt."""

    executable: str
    mode: PpkHelperLaunchMode = PpkHelperLaunchMode.DEVELOPMENT_PYTHON_MODULE
    expected_executable_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.executable, str) or not self.executable:
            raise ValueError("helper executable identity is invalid")
        try:
            encoded_length = len(self.executable.encode("utf-8"))
        except UnicodeError:
            raise ValueError("helper executable identity is invalid") from None
        if (
            encoded_length > 4096
            or not (os.path.isabs(self.executable) or ntpath.isabs(self.executable))
            or any(character in self.executable for character in ("\x00", "\r", "\n"))
        ):
            raise ValueError("helper executable identity is invalid")
        if not isinstance(self.mode, PpkHelperLaunchMode):
            raise ValueError("helper launch mode is invalid")
        if self.mode is PpkHelperLaunchMode.DEVELOPMENT_PYTHON_MODULE:
            if self.expected_executable_sha256 is not None:
                raise ValueError("development helper cannot pin a packaged digest")
            return
        if ntpath.basename(self.executable).casefold() != (
            PACKAGED_HELPER_FILENAME.casefold()
        ):
            raise ValueError("packaged helper filename is invalid")
        expected = self.expected_executable_sha256
        if (
            not isinstance(expected, str)
            or len(expected) != 71
            or not expected.startswith("sha256:")
            or any(character not in "0123456789abcdef" for character in expected[7:])
        ):
            raise ValueError("packaged helper digest is invalid")

    @property
    def command(self) -> tuple[str, ...]:
        if self.mode is PpkHelperLaunchMode.PACKAGED_HELPER:
            return (
                self.executable,
                "--protocol-version",
                str(PROTOCOL_VERSION),
            )
        return (
            self.executable,
            "-I",
            "-u",
            "-m",
            HELPER_MODULE,
            "--protocol-version",
            str(PROTOCOL_VERSION),
        )

    def verify_identity(self) -> None:
        """Admit the exact packaged helper immediately before process start."""

        with self.hold_verified_identity():
            pass

    @contextmanager
    def hold_verified_identity(self) -> Iterator[None]:
        """Hold the verified executable handle through process creation."""

        if self.mode is PpkHelperLaunchMode.DEVELOPMENT_PYTHON_MODULE:
            yield
            return
        path = Path(self.executable)
        stream: BinaryIO | None = None
        try:
            if path.is_symlink():
                raise _PpkHelperIdentityError
            stream = path.open("rb")
            before = os.fstat(stream.fileno())
            size = before.st_size
            if (
                not stat.S_ISREG(before.st_mode)
                or size < 1
                or size > MAX_PACKAGED_HELPER_BYTES
            ):
                raise _PpkHelperIdentityError
            digest = hashlib.sha256()
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
            after = os.fstat(stream.fileno())
            coordinates = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
            if any(
                getattr(before, name) != getattr(after, name)
                for name in coordinates
            ):
                raise _PpkHelperIdentityError
            if "sha256:" + digest.hexdigest() != self.expected_executable_sha256:
                raise _PpkHelperIdentityError
        except (OSError, _PpkHelperIdentityError):
            if stream is not None:
                stream.close()
            raise _PpkHelperIdentityError(
                "packaged helper identity could not be verified"
            ) from None
        try:
            yield
        finally:
            stream.close()


def _sanitized_helper_environment(
    source: dict[str, str] | None,
) -> dict[str, str]:
    values = os.environ if source is None else source
    if source is not None and not isinstance(source, dict):
        raise ValueError("helper environment source must be a dictionary")
    return {
        key: str(value)
        for key, value in values.items()
        if key.upper() in _HELPER_ENV_ALLOWLIST
    }


def ppk_helper_popen_options(
    *,
    platform_name: str | None = None,
    environment: dict[str, str] | None = None,
) -> dict[str, object]:
    """Return the sole allowed P1C helper launch options."""

    platform = os.name if platform_name is None else platform_name
    options: dict[str, object] = {
        "stdin": subprocess.PIPE,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.DEVNULL,
        "shell": False,
        "close_fds": True,
        "bufsize": 0,
        "env": _sanitized_helper_environment(environment),
    }
    if platform == "nt":
        options["creationflags"] = getattr(
            subprocess, "CREATE_NO_WINDOW", 0x08000000
        )
    return options


class PpkHelperProcessController:
    """One-process-per-attempt transport with fail-closed cleanup."""

    def __init__(
        self,
        *,
        popen_factory: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
        platform_name: str | None = None,
        environment: dict[str, str] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._popen_factory = popen_factory
        self._platform_name = platform_name
        self._environment = environment
        self._clock = clock
        self._process: subprocess.Popen[bytes] | None = None
        self._started_at: float | None = None
        self._started_once = False
        self._lock = threading.RLock()

    @property
    def running(self) -> bool:
        with self._lock:
            return self._process is not None and self._process.poll() is None

    def start(self, spec: PpkHelperLaunchSpec) -> None:
        if not isinstance(spec, PpkHelperLaunchSpec):
            raise ValueError("spec must be PpkHelperLaunchSpec")
        with self._lock:
            if self._started_once:
                raise _error("ERR_PPK_HELPER_ALREADY_STARTED")
            self._started_once = True
            platform = (
                os.name if self._platform_name is None else self._platform_name
            )
            if (
                spec.mode is PpkHelperLaunchMode.PACKAGED_HELPER
                and platform != "nt"
            ):
                raise _error("ERR_PPK_HELPER_IDENTITY_MISMATCH") from None
            try:
                with spec.hold_verified_identity():
                    process = self._popen_factory(
                        list(spec.command),
                        **ppk_helper_popen_options(
                            platform_name=self._platform_name,
                            environment=self._environment,
                        ),
                    )
            except _PpkHelperIdentityError:
                raise _error("ERR_PPK_HELPER_IDENTITY_MISMATCH") from None
            except Exception:
                raise _error("ERR_PPK_HELPER_START_FAILED") from None
            if process.stdin is None or process.stdout is None:
                self._process = process
                self._abort_locked()
                raise _error("ERR_PPK_HELPER_PIPE_UNAVAILABLE")
            self._process = process
            self._started_at = self._clock()

    def send_frame(
        self,
        frame: Mapping[str, Any],
        *,
        timeout_seconds: float = FRAME_TIMEOUT_SECONDS,
    ) -> None:
        timeout = _bounded_timeout(timeout_seconds, maximum=FRAME_TIMEOUT_SECONDS)
        try:
            encoded = bytearray(encode_frame(frame))
        except PpkProcessWireError:
            raise _error("ERR_PPK_HELPER_PROTOCOL") from None
        if frame.get("frame_type") not in _PARENT_FRAME_TYPES:
            for index in range(len(encoded)):
                encoded[index] = 0
            raise _error("ERR_PPK_HELPER_PROTOCOL")
        try:
            with self._lock:
                process = self._require_running_locked()
                timeout = self._attempt_timeout_locked(timeout)
                stream = process.stdin
                assert stream is not None

                def write() -> None:
                    stream.write(encoded)
                    stream.flush()

                self._timed_locked(
                    write,
                    timeout=timeout,
                    timeout_code="ERR_PPK_HELPER_TIMEOUT",
                )
        finally:
            for index in range(len(encoded)):
                encoded[index] = 0

    def receive_frame(
        self,
        *,
        header_timeout_seconds: float = HEADER_TIMEOUT_SECONDS,
        frame_timeout_seconds: float = FRAME_TIMEOUT_SECONDS,
    ) -> dict[str, Any]:
        header_timeout = _bounded_timeout(
            header_timeout_seconds, maximum=HEADER_TIMEOUT_SECONDS
        )
        frame_timeout = _bounded_timeout(
            frame_timeout_seconds, maximum=FRAME_TIMEOUT_SECONDS
        )
        with self._lock:
            process = self._require_running_locked()
            stream = process.stdout
            assert stream is not None
            header = self._timed_locked(
                lambda: self._read_exact(stream, 4),
                timeout=self._attempt_timeout_locked(header_timeout),
                timeout_code="ERR_PPK_HELPER_TIMEOUT",
            )
            length = int.from_bytes(header, "big")
            if length < 1 or length > MAX_FRAME_BYTES:
                self._abort_locked()
                raise _error("ERR_PPK_HELPER_PROTOCOL")
            payload = self._timed_locked(
                lambda: self._read_exact(stream, length),
                timeout=self._attempt_timeout_locked(frame_timeout),
                timeout_code="ERR_PPK_HELPER_TIMEOUT",
            )
            try:
                frame = decode_frame(header + payload)
            except PpkProcessWireError:
                self._abort_locked()
                raise _error("ERR_PPK_HELPER_PROTOCOL") from None
            if frame["frame_type"] not in _HELPER_FRAME_TYPES:
                self._abort_locked()
                raise _error("ERR_PPK_HELPER_PROTOCOL")
            return frame

    def finish(self, *, timeout_seconds: float = STOP_TIMEOUT_SECONDS) -> None:
        timeout = _bounded_timeout(timeout_seconds, maximum=30.0)
        with self._lock:
            process = self._process
            if process is None:
                raise _error("ERR_PPK_HELPER_NOT_STARTED")
            try:
                exit_code = process.wait(
                    timeout=self._attempt_timeout_locked(timeout)
                )
            except subprocess.TimeoutExpired:
                self._abort_locked(timeout=timeout)
                raise _error("ERR_PPK_HELPER_TIMEOUT") from None
            except Exception:
                self._abort_locked(timeout=timeout)
                raise _error("ERR_PPK_HELPER_WAIT_FAILED") from None
            self._close_pipes_locked()
            self._process = None
            self._started_at = None
            if exit_code != 0:
                raise _error("ERR_PPK_HELPER_EXIT_FAILED")

    def abort(self, *, timeout_seconds: float = STOP_TIMEOUT_SECONDS) -> None:
        timeout = _bounded_timeout(timeout_seconds, maximum=30.0)
        with self._lock:
            self._abort_locked(timeout=timeout)

    def close(self) -> None:
        self.abort()

    def _require_running_locked(self) -> subprocess.Popen[bytes]:
        process = self._process
        if process is None:
            raise _error("ERR_PPK_HELPER_NOT_STARTED")
        if process.poll() is not None:
            self._close_pipes_locked()
            self._process = None
            self._started_at = None
            raise _error("ERR_PPK_HELPER_EXITED_EARLY")
        return process

    def _attempt_timeout_locked(self, requested: float) -> float:
        if self._started_at is None:
            raise _error("ERR_PPK_HELPER_NOT_STARTED")
        remaining = ATTEMPT_TIMEOUT_SECONDS - (self._clock() - self._started_at)
        if remaining <= 0:
            self._abort_locked()
            raise _error("ERR_PPK_HELPER_TIMEOUT")
        return min(requested, remaining)

    @staticmethod
    def _read_exact(stream: BinaryIO, size: int) -> bytes:
        result = bytearray()
        while len(result) < size:
            chunk = stream.read(size - len(result))
            if not chunk:
                for index in range(len(result)):
                    result[index] = 0
                raise EOFError
            result.extend(chunk)
        return bytes(result)

    def _timed_locked(
        self,
        operation: Callable[[], Any],
        *,
        timeout: float,
        timeout_code: str,
    ) -> Any:
        completed = threading.Event()
        result: list[Any] = []
        error: list[Exception] = []

        def run() -> None:
            try:
                result.append(operation())
            except Exception as exc:
                error.append(exc)
            finally:
                completed.set()

        thread = threading.Thread(
            target=run,
            name="task059-ppk-pipe",
            daemon=True,
        )
        thread.start()
        if not completed.wait(timeout):
            self._abort_locked(timeout=min(timeout, STOP_TIMEOUT_SECONDS))
            thread.join(timeout=STOP_TIMEOUT_SECONDS)
            raise _error(timeout_code)
        thread.join()
        if error:
            self._abort_locked()
            raise _error("ERR_PPK_HELPER_PIPE_IO")
        return result[0] if result else None

    def _close_pipes_locked(self) -> None:
        process = self._process
        if process is None:
            return
        for stream in (process.stdin, process.stdout):
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass

    def _abort_locked(self, *, timeout: float = STOP_TIMEOUT_SECONDS) -> None:
        process = self._process
        if process is None:
            self._started_at = None
            return
        self._close_pipes_locked()
        if process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    pass
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        self._process = None
        self._started_at = None


__all__ = [
    "ATTEMPT_TIMEOUT_SECONDS",
    "FRAME_TIMEOUT_SECONDS",
    "HEADER_TIMEOUT_SECONDS",
    "HELPER_MODULE",
    "MAX_PACKAGED_HELPER_BYTES",
    "PACKAGED_HELPER_FILENAME",
    "PpkHelperLaunchSpec",
    "PpkHelperLaunchMode",
    "PpkHelperProcessController",
    "PpkHelperProcessError",
    "STOP_TIMEOUT_SECONDS",
    "ppk_helper_popen_options",
]
