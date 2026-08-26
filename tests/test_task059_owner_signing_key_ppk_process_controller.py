from __future__ import annotations

import base64
import io
import subprocess
import threading

import pytest

from ai_video_production.owner_signing_key_ppk_process_controller import (
    ATTEMPT_TIMEOUT_SECONDS,
    HELPER_MODULE,
    MAX_PACKAGED_HELPER_BYTES,
    PACKAGED_HELPER_FILENAME,
    PpkHelperLaunchSpec,
    PpkHelperLaunchMode,
    PpkHelperProcessController,
    PpkHelperProcessError,
    ppk_helper_popen_options,
)
from ai_video_production.owner_signing_key_ppk_process_wire import (
    PROTOCOL_VERSION,
    encode_frame,
)
from ai_video_production.serialization import sha256_bytes


SESSION = "task059-p1c-controller-session"


def _frame(frame_type: str = "HELLO_ACCEPTED") -> dict[str, object]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "frame_type": frame_type,
        "session_id": SESSION,
    }



def _hello() -> dict[str, object]:
    return {
        **_frame("HELLO"),
        "capability_coordinates": {
            "preflight_schema_version": "1.0.0",
            "ready_record_version": "1.0.0",
        },
    }


class _InspectableBytesIO(io.BytesIO):
    def __init__(self) -> None:
        super().__init__()
        self.final_contents = b""

    @property
    def contents(self) -> bytes:
        return self.final_contents if self.closed else self.getvalue()

    def close(self) -> None:
        self.final_contents = self.getvalue()
        super().close()



class _ReferenceWriter(_InspectableBytesIO):
    def __init__(self) -> None:
        super().__init__()
        self.last_reference: object | None = None

    def write(self, value: object) -> int:
        self.last_reference = value
        return super().write(value)


class _ChunkedReader(io.BytesIO):
    def read(self, size: int = -1) -> bytes:
        return super().read(min(size, 3) if size >= 0 else 3)


class _BlockingReader:
    def __init__(self) -> None:
        self.closed = False
        self._closed = threading.Event()

    def read(self, size: int = -1) -> bytes:
        self._closed.wait(2)
        return b""

    def close(self) -> None:
        self.closed = True
        self._closed.set()


class _FakeProcess:
    def __init__(
        self,
        *,
        stdout: object | None = None,
        stdin: object | None = None,
        wait_timeouts: int = 0,
    ) -> None:
        self.stdin = _InspectableBytesIO() if stdin is None else stdin
        self.stdout = io.BytesIO() if stdout is None else stdout
        self.return_code: int | None = None
        self.wait_timeouts = wait_timeouts
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self.return_code

    def wait(self, *, timeout: float) -> int:
        if self.wait_timeouts:
            self.wait_timeouts -= 1
            raise subprocess.TimeoutExpired("fixed-helper", timeout)
        if self.return_code is None:
            self.return_code = 0
        return self.return_code

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True
        self.return_code = -9


def _controller(
    process: _FakeProcess,
    *,
    calls: list[tuple[list[str], dict[str, object]]] | None = None,
    clock=lambda: 100.0,
) -> PpkHelperProcessController:
    def factory(command: list[str], **options: object) -> _FakeProcess:
        if calls is not None:
            calls.append((command, options))
        return process

    return PpkHelperProcessController(
        popen_factory=factory,
        platform_name="nt",
        environment={
            "PATH": "C:\\safe",
            "SYSTEMROOT": "C:\\Windows",
            "OPENAI_API_KEY": "must-not-pass",
            "PASSWORD": "must-not-pass",
        },
        clock=clock,
    )


def test_launch_spec_is_fixed_non_secret_argv() -> None:
    spec = PpkHelperLaunchSpec("C:\\Program Files\\BVP\\python.exe")
    assert spec.command == (
        spec.executable,
        "-I",
        "-u",
        "-m",
        HELPER_MODULE,
        "--protocol-version",
        str(PROTOCOL_VERSION),
    )
    rendered = " ".join(spec.command).lower()
    for forbidden in ("passphrase", "password", "fingerprint", "private-key", "token"):
        assert forbidden not in rendered
    for invalid in ("", "relative.exe", "x\n--password=bad", "x\x00bad"):
        with pytest.raises(ValueError):
            PpkHelperLaunchSpec(invalid)


def test_packaged_launch_spec_requires_exact_file_digest_and_command(tmp_path) -> None:
    path = tmp_path / PACKAGED_HELPER_FILENAME
    body = b"synthetic packaged helper"
    path.write_bytes(body)
    spec = PpkHelperLaunchSpec(
        str(path),
        mode=PpkHelperLaunchMode.PACKAGED_HELPER,
        expected_executable_sha256=sha256_bytes(body),
    )
    assert spec.command == (
        str(path),
        "--protocol-version",
        str(PROTOCOL_VERSION),
    )
    assert HELPER_MODULE not in spec.command
    spec.verify_identity()

    path.write_bytes(b"tampered helper")
    with pytest.raises(ValueError, match="identity"):
        spec.verify_identity()


def test_packaged_identity_launches_only_exact_command_on_windows(tmp_path) -> None:
    path = tmp_path / PACKAGED_HELPER_FILENAME
    body = b"synthetic packaged helper"
    path.write_bytes(body)
    spec = PpkHelperLaunchSpec(
        str(path),
        mode=PpkHelperLaunchMode.PACKAGED_HELPER,
        expected_executable_sha256=sha256_bytes(body),
    )
    calls: list[tuple[list[str], dict[str, object]]] = []
    controller = _controller(_FakeProcess(), calls=calls)

    controller.start(spec)

    assert len(calls) == 1
    command, options = calls[0]
    assert command == list(spec.command)
    assert HELPER_MODULE not in command
    assert options["shell"] is False
    assert options["stderr"] is subprocess.DEVNULL
    assert options["creationflags"] == getattr(
        subprocess, "CREATE_NO_WINDOW", 0x08000000
    )
    assert "OPENAI_API_KEY" not in options["env"]
    assert "PASSWORD" not in options["env"]


def test_packaged_identity_rejects_non_regular_or_unbounded_file(tmp_path) -> None:
    empty = tmp_path / "empty" / PACKAGED_HELPER_FILENAME
    empty.parent.mkdir()
    empty.write_bytes(b"")
    empty_spec = PpkHelperLaunchSpec(
        str(empty),
        mode=PpkHelperLaunchMode.PACKAGED_HELPER,
        expected_executable_sha256=sha256_bytes(b""),
    )
    with pytest.raises(ValueError, match="identity"):
        empty_spec.verify_identity()

    oversized = tmp_path / "oversized" / PACKAGED_HELPER_FILENAME
    oversized.parent.mkdir()
    with oversized.open("wb") as stream:
        stream.truncate(MAX_PACKAGED_HELPER_BYTES + 1)
    oversized_spec = PpkHelperLaunchSpec(
        str(oversized),
        mode=PpkHelperLaunchMode.PACKAGED_HELPER,
        expected_executable_sha256="sha256:" + "0" * 64,
    )
    with pytest.raises(ValueError, match="identity"):
        oversized_spec.verify_identity()

    directory = tmp_path / "directory" / PACKAGED_HELPER_FILENAME
    directory.mkdir(parents=True)
    directory_spec = PpkHelperLaunchSpec(
        str(directory),
        mode=PpkHelperLaunchMode.PACKAGED_HELPER,
        expected_executable_sha256="sha256:" + "0" * 64,
    )
    with pytest.raises(ValueError, match="identity"):
        directory_spec.verify_identity()


def test_packaged_launch_spec_rejects_implicit_or_unpinned_identity(tmp_path) -> None:
    exact = tmp_path / PACKAGED_HELPER_FILENAME
    for path, digest in (
        (tmp_path / "python.exe", "sha256:" + "0" * 64),
        (exact, None),
        (exact, "not-a-sha256"),
    ):
        with pytest.raises(ValueError):
            PpkHelperLaunchSpec(
                str(path),
                mode=PpkHelperLaunchMode.PACKAGED_HELPER,
                expected_executable_sha256=digest,
            )
    with pytest.raises(ValueError):
        PpkHelperLaunchSpec(
            str(exact),
            expected_executable_sha256="sha256:" + "0" * 64,
        )


def test_packaged_identity_mismatch_blocks_popen_and_consumes_controller(tmp_path) -> None:
    path = tmp_path / PACKAGED_HELPER_FILENAME
    path.write_bytes(b"synthetic packaged helper")
    spec = PpkHelperLaunchSpec(
        str(path),
        mode=PpkHelperLaunchMode.PACKAGED_HELPER,
        expected_executable_sha256="sha256:" + "0" * 64,
    )
    calls: list[tuple[list[str], dict[str, object]]] = []
    controller = _controller(_FakeProcess(), calls=calls)
    with pytest.raises(PpkHelperProcessError) as mismatch:
        controller.start(spec)
    assert mismatch.value.code == "ERR_PPK_HELPER_IDENTITY_MISMATCH"
    assert calls == []
    with pytest.raises(PpkHelperProcessError) as reused:
        controller.start(spec)
    assert reused.value.code == "ERR_PPK_HELPER_ALREADY_STARTED"


def test_packaged_mode_is_windows_only(tmp_path) -> None:
    path = tmp_path / PACKAGED_HELPER_FILENAME
    body = b"synthetic packaged helper"
    path.write_bytes(body)
    calls: list[tuple[list[str], dict[str, object]]] = []

    def factory(command: list[str], **options: object) -> _FakeProcess:
        calls.append((command, options))
        return _FakeProcess()

    controller = PpkHelperProcessController(
        popen_factory=factory,
        platform_name="posix",
        environment={},
    )
    spec = PpkHelperLaunchSpec(
        str(path),
        mode=PpkHelperLaunchMode.PACKAGED_HELPER,
        expected_executable_sha256=sha256_bytes(body),
    )
    with pytest.raises(PpkHelperProcessError) as error:
        controller.start(spec)
    assert error.value.code == "ERR_PPK_HELPER_IDENTITY_MISMATCH"
    assert calls == []


def test_windows_options_are_exact_pipes_no_console_and_sanitized() -> None:
    options = ppk_helper_popen_options(
        platform_name="nt",
        environment={
            "PATH": "C:\\safe",
            "SYSTEMROOT": "C:\\Windows",
            "OPENAI_API_KEY": "forbidden",
            "PASSWORD": "forbidden",
        },
    )
    assert options["stdin"] is subprocess.PIPE
    assert options["stdout"] is subprocess.PIPE
    assert options["stderr"] is subprocess.DEVNULL
    assert options["shell"] is False
    assert options["close_fds"] is True
    assert options["bufsize"] == 0
    assert options["creationflags"] == getattr(
        subprocess, "CREATE_NO_WINDOW", 0x08000000
    )
    assert options["env"] == {"PATH": "C:\\safe", "SYSTEMROOT": "C:\\Windows"}
    assert "creationflags" not in ppk_helper_popen_options(platform_name="posix")


def test_start_uses_fixed_command_and_controller_is_never_reused() -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []
    process = _FakeProcess()
    controller = _controller(process, calls=calls)
    spec = PpkHelperLaunchSpec("C:\\BVP\\python.exe")
    controller.start(spec)

    assert calls[0][0] == list(spec.command)
    assert calls[0][1]["shell"] is False
    assert controller.running is True
    controller.abort(timeout_seconds=0.1)
    with pytest.raises(PpkHelperProcessError) as reused:
        controller.start(spec)
    assert reused.value.code == "ERR_PPK_HELPER_ALREADY_STARTED"


def test_send_and_partial_receive_use_exact_wire_frames() -> None:
    incoming = _frame()
    process = _FakeProcess(stdout=_ChunkedReader(encode_frame(incoming)))
    controller = _controller(process)
    controller.start(PpkHelperLaunchSpec("C:\\BVP\\python.exe"))

    outgoing = {
        "protocol_version": PROTOCOL_VERSION,
        "frame_type": "HELLO",
        "session_id": SESSION,
        "capability_coordinates": {
            "preflight_schema_version": "1.0.0",
            "ready_record_version": "1.0.0",
        },
    }
    controller.send_frame(outgoing)
    assert process.stdin.getvalue() == encode_frame(outgoing)
    assert controller.receive_frame() == incoming
    process.return_code = 0
    controller.finish()
    assert controller.running is False


def test_invalid_outbound_frame_has_body_free_error_and_no_write() -> None:
    secret = "SYNTHETIC_SECRET_MUST_NOT_APPEAR"
    process = _FakeProcess()
    controller = _controller(process)
    controller.start(PpkHelperLaunchSpec("C:\\BVP\\python.exe"))
    invalid = {**_frame(), "unexpected": base64.b64encode(secret.encode()).decode()}

    with pytest.raises(PpkHelperProcessError) as caught:
        controller.send_frame(invalid)

    assert caught.value.code == "ERR_PPK_HELPER_PROTOCOL"
    assert secret not in f"{caught.value!s} {caught.value!r}"
    assert process.stdin.getvalue() == b""
    controller.abort()


@pytest.mark.parametrize(
    "raw",
    [b"\x00\x00\x00\x00", b"\x00\x02\x00\x01", b"\x00\x00\x00\x02{}"],
)
def test_invalid_or_truncated_inbound_frame_aborts(raw: bytes) -> None:
    process = _FakeProcess(stdout=_ChunkedReader(raw))
    controller = _controller(process)
    controller.start(PpkHelperLaunchSpec("C:\\BVP\\python.exe"))
    with pytest.raises(PpkHelperProcessError) as caught:
        controller.receive_frame(header_timeout_seconds=0.2, frame_timeout_seconds=0.2)
    assert caught.value.code in {
        "ERR_PPK_HELPER_PROTOCOL",
        "ERR_PPK_HELPER_PIPE_IO",
    }
    assert process.terminated is True
    assert controller.running is False


def test_header_timeout_closes_pipe_and_terminates_helper() -> None:
    reader = _BlockingReader()
    process = _FakeProcess(stdout=reader)
    controller = _controller(process)
    controller.start(PpkHelperLaunchSpec("C:\\BVP\\python.exe"))

    with pytest.raises(PpkHelperProcessError) as caught:
        controller.receive_frame(header_timeout_seconds=0.01)

    assert caught.value.code == "ERR_PPK_HELPER_TIMEOUT"
    assert reader.closed is True
    assert process.terminated is True
    assert controller.running is False


def test_abort_uses_bounded_kill_fallback() -> None:
    process = _FakeProcess(wait_timeouts=1)
    controller = _controller(process)
    controller.start(PpkHelperLaunchSpec("C:\\BVP\\python.exe"))
    controller.abort(timeout_seconds=0.01)
    assert process.terminated is True
    assert process.killed is True
    assert process.return_code == -9


def test_attempt_deadline_is_enforced_before_pipe_io() -> None:
    now = [100.0]
    process = _FakeProcess()
    controller = _controller(process, clock=lambda: now[0])
    controller.start(PpkHelperLaunchSpec("C:\\BVP\\python.exe"))
    now[0] += ATTEMPT_TIMEOUT_SECONDS + 0.001

    with pytest.raises(PpkHelperProcessError) as caught:
        controller.send_frame(_hello())

    assert caught.value.code == "ERR_PPK_HELPER_TIMEOUT"
    assert process.stdin.contents == b""
    assert process.terminated is True


def test_start_pipe_failure_and_early_exit_are_fixed_errors() -> None:
    missing_pipe = _FakeProcess(stdin=None)
    missing_pipe.stdin = None
    controller = _controller(missing_pipe)
    with pytest.raises(PpkHelperProcessError) as missing:
        controller.start(PpkHelperLaunchSpec("C:\\BVP\\python.exe"))
    assert missing.value.code == "ERR_PPK_HELPER_PIPE_UNAVAILABLE"

    process = _FakeProcess()
    controller = _controller(process)
    controller.start(PpkHelperLaunchSpec("C:\\BVP\\python.exe"))
    process.return_code = 2
    with pytest.raises(PpkHelperProcessError) as exited:
        controller.send_frame(_hello())
    assert exited.value.code == "ERR_PPK_HELPER_EXITED_EARLY"


def test_start_failure_and_finish_nonzero_do_not_expose_exception_text() -> None:
    secret = "SYNTHETIC_LAUNCH_SECRET"

    def failing_factory(*args: object, **kwargs: object) -> _FakeProcess:
        raise RuntimeError(secret)

    controller = PpkHelperProcessController(popen_factory=failing_factory)
    with pytest.raises(PpkHelperProcessError) as failed:
        controller.start(PpkHelperLaunchSpec("C:\\BVP\\python.exe"))
    assert failed.value.code == "ERR_PPK_HELPER_START_FAILED"
    assert secret not in f"{failed.value!s} {failed.value!r}"

    process = _FakeProcess()
    controller = _controller(process)
    controller.start(PpkHelperLaunchSpec("C:\\BVP\\python.exe"))
    process.return_code = 7
    with pytest.raises(PpkHelperProcessError) as nonzero:
        controller.finish()
    assert nonzero.value.code == "ERR_PPK_HELPER_EXIT_FAILED"


def test_sent_mutable_frame_copy_is_zeroed_after_write() -> None:
    writer = _ReferenceWriter()
    process = _FakeProcess(stdin=writer)
    controller = _controller(process)
    controller.start(PpkHelperLaunchSpec("C:\\BVP\\python.exe"))
    controller.send_frame(_hello())
    assert writer.getvalue() == encode_frame(_hello())
    assert isinstance(writer.last_reference, bytearray)
    assert set(writer.last_reference) <= {0}
    controller.abort()


def test_pipe_direction_and_nonfinite_timeouts_fail_closed() -> None:
    process = _FakeProcess(stdout=_ChunkedReader(encode_frame(_hello())))
    controller = _controller(process)
    controller.start(PpkHelperLaunchSpec("C:\\BVP\\python.exe"))
    with pytest.raises(PpkHelperProcessError) as direction:
        controller.receive_frame()
    assert direction.value.code == "ERR_PPK_HELPER_PROTOCOL"
    assert process.terminated is True

    process = _FakeProcess()
    controller = _controller(process)
    controller.start(PpkHelperLaunchSpec("C:\\BVP\\python.exe"))
    for invalid in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError):
            controller.send_frame(_hello(), timeout_seconds=invalid)
    controller.abort()
