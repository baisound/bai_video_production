from __future__ import annotations

import base64
import hashlib
import inspect
from pathlib import Path
import textwrap
from types import SimpleNamespace

import pytest

from ai_video_production.owner_signing_key_ppk_native_adapter import (
    MAX_PASSPHRASE_UTF8_BYTES,
    PpkNativeOperatorAdapter,
    PpkNativeOperatorError,
)
from ai_video_production.owner_signing_key_ppk_operator_session import (
    PpkImportOperatorError,
)


NOW = 1_777_500_000_000
PUBLIC = bytes(range(32))
PRIVATE = b"encrypted-block!" * 2
SECRET = "synthetic-passphrase-雪".encode("utf-8")
FINGERPRINT = ""
SHA = "a" * 64


def _ssh_string(value: bytes) -> bytes:
    return len(value).to_bytes(4, "big") + value


def _public_blob() -> bytes:
    return _ssh_string(b"ssh-ed25519") + _ssh_string(PUBLIC)


def _b64_lines(value: bytes) -> list[str]:
    return textwrap.wrap(base64.b64encode(value).decode("ascii"), 64)


def _fingerprint() -> str:
    digest = hashlib.sha256(_public_blob()).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


FINGERPRINT = _fingerprint()


def _rfc4716() -> bytes:
    return (
        "\r\n".join(
            [
                "---- BEGIN SSH2 PUBLIC KEY ----",
                'Comment: "task059-native-adapter"',
                *_b64_lines(_public_blob()),
                "---- END SSH2 PUBLIC KEY ----",
            ]
        )
        + "\r\n"
    ).encode("ascii")


def _ppk(private: bytes = PRIVATE) -> bytes:
    public_lines = _b64_lines(_public_blob())
    private_lines = _b64_lines(private)
    return (
        "\r\n".join(
            [
                "PuTTY-User-Key-File-3: ssh-ed25519",
                "Encryption: aes256-cbc",
                "Comment: task059-native-adapter",
                f"Public-Lines: {len(public_lines)}",
                *public_lines,
                "Key-Derivation: Argon2id",
                "Argon2-Memory: 8192",
                "Argon2-Passes: 3",
                "Argon2-Parallelism: 1",
                "Argon2-Salt: " + "ab" * 16,
                f"Private-Lines: {len(private_lines)}",
                *private_lines,
                "Private-MAC: " + "c" * 64,
            ]
        )
        + "\r\n"
    ).encode("ascii")


class Backend:
    def __init__(
        self,
        ppk_path: str | None,
        public_path: str | None,
        *,
        secret: bytes | None = SECRET,
        mode: str = "ok",
    ) -> None:
        self.ppk_path = ppk_path
        self.public_path = public_path
        self.secret = secret
        self.mode = mode
        self.secret_destinations: list[bytearray] = []
        self.maximums: list[int] = []
        self.file_choices = 0

    def choose_encrypted_ppk(self) -> str | None:
        self.file_choices += 1
        if self.mode == "file-error":
            raise RuntimeError("path and detail must not escape")
        return self.ppk_path

    def choose_rfc4716_public_key(self) -> str | None:
        return self.public_path

    def read_passphrase_utf8(
        self, destination: bytearray, *, maximum_bytes: int
    ) -> int | None:
        self.secret_destinations.append(destination)
        self.maximums.append(maximum_bytes)
        if self.mode == "secret-error":
            raise RuntimeError("secret backend detail must not escape")
        if self.mode == "cancel":
            return None
        assert self.secret is not None
        for index, value in enumerate(self.secret):
            destination[index] = value
        if self.mode == "tail-dirty":
            destination[len(self.secret) + 1] = 1
        return len(self.secret)


class FakeSession:
    def __init__(self, *, begin_code: str | None = None) -> None:
        self.begin_code = begin_code
        self.begin_count = 0
        self.confirm_count = 0
        self.cancelled = False
        self.closed = False
        self.passphrase_values: list[int] = []
        self.buffers: tuple[bytearray, bytearray, bytearray] | None = None

    def begin(self, **kwargs):
        self.begin_count += 1
        ppk = kwargs["ppk_document"]
        public = kwargs["rfc4716_public_key"]
        passphrase = kwargs["passphrase_utf8"]
        self.buffers = (ppk, public, passphrase)
        self.passphrase_values = list(passphrase)
        for value in self.buffers:
            for index in range(len(value)):
                value[index] = 0
        if self.begin_code:
            raise PpkImportOperatorError(self.begin_code)
        return SimpleNamespace(
            openssh_sha256_fingerprint=FINGERPRINT,
            expires_at_epoch_ms=NOW + 120_000,
        )

    def confirm(self, *, explicit_human_confirmation: bool):
        assert explicit_human_confirmation is True
        self.confirm_count += 1
        return SimpleNamespace(state="CUSTODIED_AND_READBACK_VERIFIED")

    def cancel(self) -> None:
        self.cancelled = True

    def close(self) -> None:
        self.closed = True


def _files(tmp_path: Path) -> tuple[Path, Path]:
    ppk = tmp_path / "owner-key.ppk"
    public = tmp_path / "owner-key.pub"
    ppk.write_bytes(_ppk())
    public.write_bytes(_rfc4716())
    return ppk, public


def _adapter(
    backend: Backend,
    session: FakeSession | None = None,
    *,
    factory_error: bool = False,
    helper_probe=None,
) -> PpkNativeOperatorAdapter:
    helper_probe = helper_probe or (lambda: None)
    def factory():
        if factory_error:
            raise RuntimeError("packaged identity unavailable")
        assert session is not None
        return session

    return PpkNativeOperatorAdapter(
        dialog_backend=backend,
        session_factory=factory,
        helper_availability_probe=helper_probe,
        epoch_ms=lambda: NOW,
        identity=lambda kind: f"task059-{kind}-fixed",
    )


def _candidate(adapter: PpkNativeOperatorAdapter):
    result = adapter.choose_files(
        expected_openssh_sha256_fingerprint=FINGERPRINT
    )
    assert result is not None
    return result


def _confirmed(adapter: PpkNativeOperatorAdapter):
    candidate = _candidate(adapter)
    adapter.confirm_public_identity(
        candidate_id=candidate.candidate_id,
        explicit_human_confirmation=True,
    )
    return candidate


def test_selection_returns_body_free_candidate_and_keeps_paths_out_of_repr(
    tmp_path: Path,
) -> None:
    ppk, public = _files(tmp_path)
    adapter = _adapter(Backend(str(ppk), str(public)), FakeSession())
    candidate = _candidate(adapter)
    payload = candidate.to_ui_dict()

    assert candidate.state == "FILES_SELECTED_PUBLIC_CANDIDATE"
    assert payload["openssh_sha256_fingerprint"] == FINGERPRINT
    assert payload["selected_paths_exposed"] is False
    assert payload["file_bodies_exposed"] is False
    assert str(ppk) not in repr(candidate)
    assert str(public) not in repr(candidate)
    assert str(ppk) not in repr(adapter)
    assert "Private-MAC" not in repr(candidate)


@pytest.mark.parametrize("cancel_stage", ["ppk", "public"])
def test_file_selection_cancel_has_no_candidate(
    tmp_path: Path, cancel_stage: str
) -> None:
    ppk, public = _files(tmp_path)
    backend = Backend(
        None if cancel_stage == "ppk" else str(ppk),
        None if cancel_stage == "public" else str(public),
    )
    adapter = _adapter(backend, FakeSession())
    assert (
        adapter.choose_files(expected_openssh_sha256_fingerprint=FINGERPRINT)
        is None
    )
    with pytest.raises(PpkNativeOperatorError) as error:
        adapter.confirm_public_identity(
            candidate_id="task059-candidate-fixed",
            explicit_human_confirmation=True,
        )
    assert error.value.code == "ERR_PPK_NATIVE_CANDIDATE_NOT_FOUND"


def test_public_confirmation_is_explicit_and_stale_id_fails_closed(
    tmp_path: Path,
) -> None:
    ppk, public = _files(tmp_path)
    adapter = _adapter(Backend(str(ppk), str(public)), FakeSession())
    candidate = _candidate(adapter)
    with pytest.raises(PpkNativeOperatorError) as error:
        adapter.confirm_public_identity(
            candidate_id=candidate.candidate_id,
            explicit_human_confirmation=False,
        )
    assert error.value.code == "ERR_PPK_NATIVE_PUBLIC_CONFIRMATION_REQUIRED"
    with pytest.raises(PpkNativeOperatorError) as stale:
        adapter.confirm_public_identity(
            candidate_id="task059-candidate-stale",
            explicit_human_confirmation=True,
        )
    assert stale.value.code == "ERR_PPK_NATIVE_CANDIDATE_NOT_FOUND"


def test_secret_goes_directly_to_mutable_buffer_then_session_and_is_cleared(
    tmp_path: Path,
) -> None:
    ppk, public = _files(tmp_path)
    backend = Backend(str(ppk), str(public))
    session = FakeSession()
    adapter = _adapter(backend, session)
    candidate = _confirmed(adapter)

    ready = adapter.open_secret_dialog(
        candidate_id=candidate.candidate_id,
        owner_scope_sha256=SHA,
        destination_path=str(tmp_path / "custody.json"),
    )
    assert ready is not None
    assert ready.to_ui_dict()["passphrase_exposed"] is False
    assert SECRET.decode("utf-8") not in repr(ready)
    assert str(tmp_path) not in repr(ready)
    assert backend.maximums == [MAX_PASSPHRASE_UTF8_BYTES]
    assert session.passphrase_values == list(SECRET)
    assert session.buffers is not None
    assert all(value and set(value) == {0} for value in session.buffers)
    assert backend.secret_destinations[0] is session.buffers[2]
    assert set(backend.secret_destinations[0]) == {0}


def test_ready_confirmation_and_cancel_are_one_attempt_only(tmp_path: Path) -> None:
    ppk, public = _files(tmp_path)
    first = FakeSession()
    adapter = _adapter(Backend(str(ppk), str(public)), first)
    candidate = _confirmed(adapter)
    ready = adapter.open_secret_dialog(
        candidate_id=candidate.candidate_id,
        owner_scope_sha256=SHA,
        destination_path=str(tmp_path / "custody.json"),
    )
    assert ready is not None

    with pytest.raises(PpkNativeOperatorError) as denied:
        adapter.confirm_ready(
            attempt_id=ready.attempt_id,
            explicit_human_confirmation=False,
        )
    assert denied.value.code == "ERR_PPK_CUSTODY_IMPORT_CONFIRMATION_REQUIRED"
    result = adapter.confirm_ready(
        attempt_id=ready.attempt_id,
        explicit_human_confirmation=True,
    )
    assert result.state == "CUSTODIED_AND_READBACK_VERIFIED"
    assert first.confirm_count == 1
    with pytest.raises(PpkNativeOperatorError) as replay:
        adapter.confirm_ready(
            attempt_id=ready.attempt_id,
            explicit_human_confirmation=True,
        )
    assert replay.value.code == "ERR_PPK_NATIVE_ATTEMPT_NOT_READY"

    second = FakeSession()
    adapter = _adapter(Backend(str(ppk), str(public)), second)
    candidate = _confirmed(adapter)
    ready = adapter.open_secret_dialog(
        candidate_id=candidate.candidate_id,
        owner_scope_sha256=SHA,
        destination_path=str(tmp_path / "custody-2.json"),
    )
    assert ready is not None
    adapter.cancel_ready(attempt_id=ready.attempt_id)
    assert second.cancelled is True


def test_passphrase_cancel_clears_buffer_and_candidate(tmp_path: Path) -> None:
    ppk, public = _files(tmp_path)
    backend = Backend(str(ppk), str(public), mode="cancel")
    session = FakeSession()
    adapter = _adapter(backend, session)
    candidate = _confirmed(adapter)
    assert (
        adapter.open_secret_dialog(
            candidate_id=candidate.candidate_id,
            owner_scope_sha256=SHA,
            destination_path=str(tmp_path / "custody.json"),
        )
        is None
    )
    assert set(backend.secret_destinations[0]) == {0}
    assert session.begin_count == 0
    with pytest.raises(PpkNativeOperatorError):
        adapter.open_secret_dialog(
            candidate_id=candidate.candidate_id,
            owner_scope_sha256=SHA,
            destination_path=str(tmp_path / "custody.json"),
        )


@pytest.mark.parametrize(
    ("secret", "mode"),
    [
        (b"has\x00nul", "ok"),
        (b"\xff", "ok"),
        (SECRET, "tail-dirty"),
    ],
)
def test_invalid_secret_backend_output_fails_closed_and_zeroes(
    tmp_path: Path, secret: bytes, mode: str
) -> None:
    ppk, public = _files(tmp_path)
    backend = Backend(str(ppk), str(public), secret=secret, mode=mode)
    adapter = _adapter(backend, FakeSession())
    candidate = _confirmed(adapter)
    with pytest.raises(PpkNativeOperatorError) as error:
        adapter.open_secret_dialog(
            candidate_id=candidate.candidate_id,
            owner_scope_sha256=SHA,
            destination_path=str(tmp_path / "custody.json"),
        )
    assert error.value.code == "ERR_PPK_NATIVE_SECRET_INPUT_INVALID"
    assert set(backend.secret_destinations[0]) == {0}


def test_file_identity_is_rechecked_after_secret_entry(tmp_path: Path) -> None:
    ppk, public = _files(tmp_path)
    backend = Backend(str(ppk), str(public))
    session = FakeSession()
    adapter = _adapter(backend, session)
    candidate = _confirmed(adapter)
    ppk.write_bytes(_ppk(bytes(range(32))))

    with pytest.raises(PpkNativeOperatorError) as error:
        adapter.open_secret_dialog(
            candidate_id=candidate.candidate_id,
            owner_scope_sha256=SHA,
            destination_path=str(tmp_path / "custody.json"),
        )
    assert error.value.code == "ERR_PPK_NATIVE_FILE_IDENTITY_CHANGED"
    assert session.begin_count == 0
    assert set(backend.secret_destinations[0]) == {0}


def test_fixed_errors_hide_backend_path_and_secret_details(tmp_path: Path) -> None:
    ppk, public = _files(tmp_path)
    adapter = _adapter(
        Backend(str(ppk), str(public), mode="file-error"),
        FakeSession(),
    )
    with pytest.raises(PpkNativeOperatorError) as error:
        adapter.choose_files(expected_openssh_sha256_fingerprint=FINGERPRINT)
    assert error.value.code == "ERR_PPK_NATIVE_DIALOG_UNAVAILABLE"
    assert str(tmp_path) not in repr(error.value)
    assert "detail" not in repr(error.value)

    backend = Backend(str(ppk), str(public), mode="secret-error")
    adapter = _adapter(backend, FakeSession())
    candidate = _confirmed(adapter)
    with pytest.raises(PpkNativeOperatorError) as secret_error:
        adapter.open_secret_dialog(
            candidate_id=candidate.candidate_id,
            owner_scope_sha256=SHA,
            destination_path=str(tmp_path / "custody.json"),
        )
    assert secret_error.value.code == "ERR_PPK_NATIVE_SECRET_DIALOG_UNAVAILABLE"
    assert set(backend.secret_destinations[0]) == {0}


def test_packaged_helper_factory_failure_is_fixed_and_clears_secret(
    tmp_path: Path,
) -> None:
    ppk, public = _files(tmp_path)
    backend = Backend(str(ppk), str(public))
    adapter = _adapter(backend, factory_error=True)
    candidate = _confirmed(adapter)
    with pytest.raises(PpkNativeOperatorError) as error:
        adapter.open_secret_dialog(
            candidate_id=candidate.candidate_id,
            owner_scope_sha256=SHA,
            destination_path=str(tmp_path / "custody.json"),
        )
    assert error.value.code == "ERR_PPK_PACKAGED_HELPER_UNAVAILABLE"
    assert set(backend.secret_destinations[0]) == {0}


def test_session_error_code_is_preserved_and_close_is_terminal(tmp_path: Path) -> None:
    ppk, public = _files(tmp_path)
    session = FakeSession(begin_code="ERR_PPK_SECRET_AUTHENTICATION_FAILED")
    adapter = _adapter(Backend(str(ppk), str(public)), session)
    candidate = _confirmed(adapter)
    with pytest.raises(PpkNativeOperatorError) as error:
        adapter.open_secret_dialog(
            candidate_id=candidate.candidate_id,
            owner_scope_sha256=SHA,
            destination_path=str(tmp_path / "custody.json"),
        )
    assert error.value.code == "ERR_PPK_SECRET_AUTHENTICATION_FAILED"
    assert session.closed is True


def test_source_has_no_string_or_immutable_passphrase_conversion() -> None:
    source = inspect.getsource(
        __import__(
            "ai_video_production.owner_signing_key_ppk_native_adapter",
            fromlist=["PpkNativeOperatorAdapter"],
        )
    )
    assert "passphrase.decode" not in source
    assert "bytes(passphrase" not in source
    assert "passphrase_utf8: str" not in source

def test_helper_unavailable_blocks_before_file_selection(tmp_path: Path) -> None:
    ppk, public = _files(tmp_path)
    backend = Backend(str(ppk), str(public))

    def unavailable() -> None:
        raise RuntimeError("digest mismatch path must not escape")

    adapter = _adapter(backend, FakeSession(), helper_probe=unavailable)
    with pytest.raises(PpkNativeOperatorError) as error:
        adapter.choose_files(expected_openssh_sha256_fingerprint=FINGERPRINT)
    assert error.value.code == "ERR_PPK_PACKAGED_HELPER_UNAVAILABLE"
    assert backend.file_choices == 0
    assert str(tmp_path) not in repr(error.value)


def test_helper_is_rechecked_before_collecting_passphrase(tmp_path: Path) -> None:
    ppk, public = _files(tmp_path)
    backend = Backend(str(ppk), str(public))
    available = [True]

    def probe() -> None:
        if not available[0]:
            raise RuntimeError("helper moved")

    adapter = _adapter(backend, FakeSession(), helper_probe=probe)
    candidate = _confirmed(adapter)
    available[0] = False
    with pytest.raises(PpkNativeOperatorError) as error:
        adapter.open_secret_dialog(
            candidate_id=candidate.candidate_id,
            owner_scope_sha256=SHA,
            destination_path=str(tmp_path / "custody.json"),
        )
    assert error.value.code == "ERR_PPK_PACKAGED_HELPER_UNAVAILABLE"
    assert backend.secret_destinations == []
