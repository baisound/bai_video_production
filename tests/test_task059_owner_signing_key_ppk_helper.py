from __future__ import annotations

import base64
import hashlib
import io

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from ai_video_production.owner_signing_key_custody import OwnerSigningKeyCustodyReceipt
from ai_video_production.owner_signing_key_ppk_custody_import import (
    PpkCustodyImportConfirmation,
    PpkCustodyImportReady,
    PpkCustodyImportReceipt,
    PpkCustodyImportResult,
)
from ai_video_production.owner_signing_key_ppk_helper import (
    PpkHelperDependencies,
    PpkHelperRuntime,
    main,
)
from ai_video_production.owner_signing_key_ppk_preflight import PpkImportPreflight
from ai_video_production.owner_signing_key_ppk_process_wire import (
    BoundedFrameReader,
    PROTOCOL_VERSION,
    encode_frame,
)
from ai_video_production.owner_signing_key_ppk_secret_auth import (
    _AuthenticatedPpkSecret,
)
from ai_video_production.serialization import sha256_bytes


SESSION = "task059-helper-session-001"
SHA = sha256_bytes(b"task059-helper")
SEED = bytes(range(1, 33))
NOW = 1_777_300_000_000
DESTINATION = "C:\\BVP\\owner-signing-key-custody.json"


def _public() -> bytes:
    return (
        Ed25519PrivateKey.from_private_bytes(SEED)
        .public_key()
        .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    )


def _fingerprint() -> str:
    algorithm = b"ssh-ed25519"
    public = _public()
    blob = (
        len(algorithm).to_bytes(4, "big")
        + algorithm
        + len(public).to_bytes(4, "big")
        + public
    )
    return "SHA256:" + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")


def _preflight() -> PpkImportPreflight:
    return PpkImportPreflight(
        observed_at_epoch_ms=NOW,
        ppk_file_sha256=SHA,
        public_key_file_sha256=SHA,
        ppk_public_blob_sha256=SHA,
        private_ciphertext_sha256=SHA,
        signer_key_id_sha256=sha256_bytes(_public()),
        openssh_sha256_fingerprint=_fingerprint(),
        argon2_memory_kib=8192,
        argon2_passes=3,
        argon2_parallelism=1,
    )


def _frame(frame_type: str, **payload: object) -> dict[str, object]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "frame_type": frame_type,
        "session_id": SESSION,
        **payload,
    }


def _hello() -> dict[str, object]:
    return _frame(
        "HELLO",
        capability_coordinates={
            "preflight_schema_version": "1.0.0",
            "ready_record_version": "1.0.0",
        },
    )


def _auth(destination: str = DESTINATION) -> dict[str, object]:
    return _frame(
        "AUTH_REQUEST",
        preflight=_preflight().to_dict(),
        ppk_document_b64=base64.b64encode(b"synthetic encrypted PPK").decode(),
        rfc4716_public_key_b64=base64.b64encode(b"synthetic public key").decode(),
        passphrase_utf8_b64=base64.b64encode(b"synthetic-passphrase").decode(),
        custody_request={
            "owner_scope_sha256": SHA,
            "destination_path_utf8_b64": base64.b64encode(destination.encode()).decode(),
        },
    )


def _secret() -> _AuthenticatedPpkSecret:
    return _AuthenticatedPpkSecret(
        _private_key_seed=bytearray(SEED),
        preflight_sha256=_preflight().to_dict()["preflight_sha256"],
        ppk_file_sha256=SHA,
        signer_key_id_sha256=sha256_bytes(_public()),
        openssh_sha256_fingerprint=_fingerprint(),
    )


def _ready() -> PpkCustodyImportReady:
    return PpkCustodyImportReady(
        session_id=SESSION,
        challenge_id="task059-challenge-fixed",
        custody_id="task059-custody-fixed",
        preflight_sha256=_preflight().to_dict()["preflight_sha256"],
        ppk_file_sha256=SHA,
        signer_key_id_sha256=sha256_bytes(_public()),
        openssh_sha256_fingerprint=_fingerprint(),
        owner_scope_sha256=SHA,
        destination_path_sha256=SHA,
        ready_at_epoch_ms=NOW,
        expires_at_epoch_ms=NOW + 120_000,
    )


def _confirmation() -> PpkCustodyImportConfirmation:
    ready = _ready()
    return PpkCustodyImportConfirmation(
        confirmation_id="task059-confirmation-fixed",
        session_id=SESSION,
        challenge_id=ready.challenge_id,
        ready_sha256=ready.to_dict()["ready_sha256"],
        custody_id=ready.custody_id,
        signer_key_id_sha256=ready.signer_key_id_sha256,
        owner_scope_sha256=ready.owner_scope_sha256,
        destination_path_sha256=ready.destination_path_sha256,
        confirmed_at_epoch_ms=NOW + 1_000,
    )


def _result(secret: _AuthenticatedPpkSecret) -> PpkCustodyImportResult:
    confirmation = _confirmation()
    custody = OwnerSigningKeyCustodyReceipt(
        receipt_id="task029-custody-receipt-fixed",
        custody_id=_ready().custody_id,
        owner_scope_sha256=SHA,
        signer_key_id_sha256=sha256_bytes(_public()),
        confirmation_sha256=SHA,
        custodied_at_epoch_ms=NOW + 2_000,
        cipher_suite="TASK059_TEST_CIPHER_V1",
    )
    imported = PpkCustodyImportReceipt(
        receipt_id="task059-import-receipt-fixed",
        ready_sha256=_ready().to_dict()["ready_sha256"],
        confirmation_sha256=confirmation.to_dict()["confirmation_sha256"],
        custody_receipt_sha256=custody.to_dict()["custody_receipt_sha256"],
        preflight_sha256=_preflight().to_dict()["preflight_sha256"],
        ppk_file_sha256=SHA,
        signer_key_id_sha256=sha256_bytes(_public()),
        owner_scope_sha256=SHA,
        destination_path_sha256=SHA,
        imported_at_epoch_ms=NOW + 2_000,
    )
    secret.clear()
    return PpkCustodyImportResult(receipt=imported, custody_receipt=custody)


def _input(*frames: dict[str, object]) -> io.BytesIO:
    return io.BytesIO(b"".join(encode_frame(frame) for frame in frames))


def _output_frames(stream: io.BytesIO) -> list[dict[str, object]]:
    reader = BoundedFrameReader()
    frames = reader.feed(stream.getvalue())
    reader.finish()
    return frames


class _FailThirdWrite(io.BytesIO):
    def __init__(self) -> None:
        super().__init__()
        self.write_count = 0

    def write(self, value: bytes | bytearray) -> int:
        self.write_count += 1
        if self.write_count == 3:
            raise OSError("synthetic completed frame write failure")
        return super().write(value)


def _dependencies(
    *,
    secret: _AuthenticatedPpkSecret,
    authenticate=None,
    execute=None,
) -> PpkHelperDependencies:
    def fake_prepare(**kwargs):
        assert kwargs["destination_path"] == DESTINATION
        assert kwargs["owner_scope_sha256"] == SHA
        return _ready()

    return PpkHelperDependencies(
        authenticate=authenticate or (lambda *args, **kwargs: secret),
        prepare_ready=fake_prepare,
        execute_import=execute or (lambda **kwargs: _result(kwargs["secret"])),
        store_factory=lambda path: ("fake-store", path),
        epoch_ms=lambda: NOW,
        identity=lambda kind: f"task059-{kind}-fixed",
    )


def test_success_runs_one_exact_attempt_and_returns_body_free_receipts() -> None:
    secret = _secret()
    stdout = io.BytesIO()
    runtime = PpkHelperRuntime(_dependencies(secret=secret))
    code = runtime.run(
        _input(
            _hello(),
            _auth(),
            _frame("CONFIRM", confirmation=_confirmation().to_dict()),
        ),
        stdout,
    )

    frames = _output_frames(stdout)
    assert code == 0
    assert [frame["frame_type"] for frame in frames] == [
        "HELLO_ACCEPTED",
        "READY",
        "COMPLETED",
    ]
    assert secret.cleared is True
    rendered = repr(frames)
    assert "synthetic-passphrase" not in rendered
    assert DESTINATION not in rendered
    assert frames[-1]["import_receipt"]["destination_path_sha256"] == SHA


def test_cancel_clears_secret_and_returns_fixed_failure_without_custody() -> None:
    secret = _secret()
    executed = []
    dependencies = _dependencies(
        secret=secret,
        execute=lambda **kwargs: executed.append(kwargs),
    )
    stdout = io.BytesIO()
    code = PpkHelperRuntime(dependencies).run(
        _input(
            _hello(),
            _auth(),
            _frame("CANCEL", reason_code="OWNER_CANCELLED"),
        ),
        stdout,
    )
    frames = _output_frames(stdout)
    assert code == 0
    assert frames[-1] == _frame(
        "FAILED",
        phase="CONFIRMATION",
        error_code="ERR_PPK_HELPER_CANCELLED",
        retryable=False,
    )
    assert executed == []
    assert secret.cleared is True


def test_parent_eof_before_authentication_exits_without_failure_or_mutation() -> None:
    secret = _secret()
    stdout = io.BytesIO()
    code = PpkHelperRuntime(_dependencies(secret=secret)).run(_input(_hello()), stdout)
    frames = _output_frames(stdout)
    assert code == 0
    assert frames == [_frame("HELLO_ACCEPTED")]
    assert secret.cleared is False


def test_parent_eof_after_ready_clears_authenticated_secret() -> None:
    secret = _secret()
    stdout = io.BytesIO()
    code = PpkHelperRuntime(_dependencies(secret=secret)).run(
        _input(_hello(), _auth()), stdout
    )
    frames = _output_frames(stdout)
    assert code == 0
    assert [frame["frame_type"] for frame in frames] == ["HELLO_ACCEPTED", "READY"]
    assert secret.cleared is True


def test_authentication_failure_is_fixed_and_never_echoes_exception() -> None:
    secret_text = "SYNTHETIC_AUTH_EXCEPTION_SECRET"

    def fail_auth(*args, **kwargs):
        raise RuntimeError(secret_text)

    stdout = io.BytesIO()
    code = PpkHelperRuntime(
        _dependencies(secret=_secret(), authenticate=fail_auth)
    ).run(_input(_hello(), _auth()), stdout)
    rendered = repr(_output_frames(stdout))
    assert code == 3
    assert "ERR_PPK_SECRET_AUTHENTICATION_FAILED" in rendered
    assert secret_text not in rendered


def test_decoded_passphrase_buffer_is_zeroed_even_when_fake_auth_does_not() -> None:
    captured: list[bytearray] = []
    secret = _secret()

    def capture_auth(*args, **kwargs):
        captured.append(kwargs["passphrase_utf8"])
        return secret

    stdout = io.BytesIO()
    PpkHelperRuntime(
        _dependencies(secret=secret, authenticate=capture_auth)
    ).run(
        _input(
            _hello(),
            _auth(),
            _frame("CANCEL", reason_code="OWNER_CANCELLED"),
        ),
        stdout,
    )
    assert len(captured) == 1
    assert captured[0] and set(captured[0]) == {0}


def test_relative_destination_fails_before_authentication() -> None:
    calls = []
    stdout = io.BytesIO()
    dependencies = _dependencies(
        secret=_secret(),
        authenticate=lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    code = PpkHelperRuntime(dependencies).run(
        _input(_hello(), _auth("relative-custody.json")), stdout
    )
    assert code == 3
    assert calls == []
    assert _output_frames(stdout)[-1]["error_code"] == (
        "ERR_PPK_SECRET_AUTHENTICATION_FAILED"
    )


def test_custody_failure_clears_secret_and_maps_fixed_error() -> None:
    secret_text = "SYNTHETIC_CUSTODY_EXCEPTION_SECRET"
    secret = _secret()

    def fail_execute(**kwargs):
        raise RuntimeError(secret_text)

    stdout = io.BytesIO()
    code = PpkHelperRuntime(
        _dependencies(secret=secret, execute=fail_execute)
    ).run(
        _input(
            _hello(),
            _auth(),
            _frame("CONFIRM", confirmation=_confirmation().to_dict()),
        ),
        stdout,
    )
    rendered = repr(_output_frames(stdout))
    assert code == 4
    assert "ERR_PPK_CUSTODY_RESULT_LOST_REQUIRES_READBACK" in rendered
    assert secret_text not in rendered
    assert secret.cleared is True


def test_execute_adapter_must_consume_secret_and_requires_readback() -> None:
    secret = _secret()
    safe_result = _result(_secret())

    def return_without_consuming(**kwargs):
        return safe_result

    stdout = io.BytesIO()
    code = PpkHelperRuntime(
        _dependencies(secret=secret, execute=return_without_consuming)
    ).run(
        _input(
            _hello(),
            _auth(),
            _frame("CONFIRM", confirmation=_confirmation().to_dict()),
        ),
        stdout,
    )
    assert code == 4
    assert _output_frames(stdout)[-1]["error_code"] == (
        "ERR_PPK_CUSTODY_RESULT_LOST_REQUIRES_READBACK"
    )
    assert secret.cleared is True


def test_completed_output_failure_requires_custody_readback() -> None:
    secret = _secret()
    stdout = _FailThirdWrite()
    code = PpkHelperRuntime(_dependencies(secret=secret)).run(
        _input(
            _hello(),
            _auth(),
            _frame("CONFIRM", confirmation=_confirmation().to_dict()),
        ),
        stdout,
    )
    frames = _output_frames(stdout)
    assert code == 4
    assert [frame["frame_type"] for frame in frames] == [
        "HELLO_ACCEPTED",
        "READY",
        "FAILED",
    ]
    assert frames[-1]["error_code"] == (
        "ERR_PPK_CUSTODY_RESULT_LOST_REQUIRES_READBACK"
    )
    assert secret.cleared is True


def test_invalid_completed_payload_after_custody_requires_readback() -> None:
    secret = _secret()

    class EmptyReceipt:
        @staticmethod
        def to_dict():
            return {}

    class InvalidResult:
        receipt = EmptyReceipt()
        custody_receipt = EmptyReceipt()

    def return_invalid_result(**kwargs):
        kwargs["secret"].clear()
        return InvalidResult()

    stdout = io.BytesIO()
    code = PpkHelperRuntime(
        _dependencies(secret=secret, execute=return_invalid_result)
    ).run(
        _input(
            _hello(),
            _auth(),
            _frame("CONFIRM", confirmation=_confirmation().to_dict()),
        ),
        stdout,
    )
    frames = _output_frames(stdout)
    assert code == 4
    assert frames[-1]["error_code"] == (
        "ERR_PPK_CUSTODY_RESULT_LOST_REQUIRES_READBACK"
    )
    assert secret.cleared is True


def test_out_of_order_frame_maps_protocol_failure() -> None:
    stdout = io.BytesIO()
    code = PpkHelperRuntime(_dependencies(secret=_secret())).run(
        _input(_hello(), _frame("CANCEL", reason_code="OWNER_CANCELLED")),
        stdout,
    )
    assert code == 2
    assert _output_frames(stdout)[-1]["error_code"] == "ERR_PPK_HELPER_PROTOCOL"


@pytest.mark.parametrize(
    "arguments, expected",
    [
        ([], 64),
        (["--protocol-version", "2"], 64),
        (["--protocol-version", "1", "extra"], 64),
    ],
)
def test_main_rejects_every_nonexact_argument_vector(arguments, expected) -> None:
    assert main(arguments) == expected
