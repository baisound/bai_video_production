from __future__ import annotations

import pytest

from ai_video_production.owner_signing_key_custody import OwnerSigningKeyCustodyReceipt
from ai_video_production.owner_signing_key_ppk_custody_import import (
    PpkCustodyImportReady,
    PpkCustodyImportReceipt,
    custody_destination_path_sha256,
)
from ai_video_production.owner_signing_key_ppk_operator_session import (
    PpkImportOperatorError,
    PpkImportOperatorSession,
)
from ai_video_production.owner_signing_key_ppk_preflight import PpkImportPreflight
from ai_video_production.owner_signing_key_ppk_process_controller import (
    PpkHelperLaunchSpec,
    PpkHelperProcessError,
)
from ai_video_production.owner_signing_key_ppk_process_wire import PROTOCOL_VERSION
from ai_video_production.serialization import sha256_bytes


SESSION = "task059-session-fixed"
NOW = 1_777_400_000_000
SHA = sha256_bytes(b"task059-p1ce")
DESTINATION = "C:\\BVP\\owner-signing-key-custody.json"


def _preflight() -> PpkImportPreflight:
    return PpkImportPreflight(
        observed_at_epoch_ms=NOW,
        ppk_file_sha256=SHA,
        public_key_file_sha256=SHA,
        ppk_public_blob_sha256=SHA,
        private_ciphertext_sha256=SHA,
        signer_key_id_sha256=SHA,
        openssh_sha256_fingerprint="SHA256:" + "A" * 43,
        argon2_memory_kib=8192,
        argon2_passes=3,
        argon2_parallelism=1,
    )


def _ready(*, owner_scope_sha256: str = SHA) -> PpkCustodyImportReady:
    return PpkCustodyImportReady(
        session_id=SESSION,
        challenge_id="task059-challenge-fixed",
        custody_id="task059-custody-fixed",
        preflight_sha256=_preflight().to_dict()["preflight_sha256"],
        ppk_file_sha256=SHA,
        signer_key_id_sha256=SHA,
        openssh_sha256_fingerprint="SHA256:" + "A" * 43,
        owner_scope_sha256=owner_scope_sha256,
        destination_path_sha256=custody_destination_path_sha256(DESTINATION),
        ready_at_epoch_ms=NOW,
        expires_at_epoch_ms=NOW + 120_000,
    )


def _frame(frame_type: str, **payload: object) -> dict[str, object]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "frame_type": frame_type,
        "session_id": SESSION,
        **payload,
    }


class FakeController:
    def __init__(
        self,
        *,
        failure_code: str | None = None,
        send_error: bool = False,
        ready_drift: bool = False,
    ):
        self.failure_code = failure_code
        self.send_error = send_error
        self.ready_drift = ready_drift
        self.sent: list[dict[str, object]] = []
        self.started = False
        self.finished = False
        self.aborted = False

    def start(self, spec) -> None:
        self.started = True

    def send_frame(self, frame) -> None:
        if self.send_error:
            raise PpkHelperProcessError("ERR_PPK_HELPER_PIPE_IO")
        self.sent.append(dict(frame))

    def receive_frame(self):
        frame_type = self.sent[-1]["frame_type"]
        if frame_type == "HELLO":
            return _frame("HELLO_ACCEPTED")
        if frame_type == "AUTH_REQUEST":
            if self.failure_code == "ERR_PPK_SECRET_AUTHENTICATION_FAILED":
                return _frame(
                    "FAILED",
                    phase="AUTHENTICATION",
                    error_code=self.failure_code,
                    retryable=False,
                )
            ready = _ready(
                owner_scope_sha256=sha256_bytes(b"drift") if self.ready_drift else SHA
            )
            return _frame("READY", ready=ready.to_dict())
        if frame_type == "CANCEL":
            return _frame(
                "FAILED",
                phase="CONFIRMATION",
                error_code="ERR_PPK_HELPER_CANCELLED",
                retryable=False,
            )
        if frame_type == "CONFIRM":
            if self.failure_code:
                return _frame(
                    "FAILED",
                    phase="CUSTODY",
                    error_code=self.failure_code,
                    retryable=False,
                )
            confirmation = self.sent[-1]["confirmation"]
            custody = OwnerSigningKeyCustodyReceipt(
                receipt_id="task029-custody-receipt-fixed",
                custody_id=_ready().custody_id,
                owner_scope_sha256=SHA,
                signer_key_id_sha256=SHA,
                confirmation_sha256=SHA,
                custodied_at_epoch_ms=NOW + 2_000,
                cipher_suite="TASK059_TEST_CIPHER_V1",
            )
            imported = PpkCustodyImportReceipt(
                receipt_id="task059-import-receipt-fixed",
                ready_sha256=_ready().to_dict()["ready_sha256"],
                confirmation_sha256=confirmation["confirmation_sha256"],
                custody_receipt_sha256=custody.to_dict()["custody_receipt_sha256"],
                preflight_sha256=SHA,
                ppk_file_sha256=SHA,
                signer_key_id_sha256=SHA,
                owner_scope_sha256=SHA,
                destination_path_sha256=custody_destination_path_sha256(DESTINATION),
                imported_at_epoch_ms=NOW + 2_000,
            )
            return _frame(
                "COMPLETED",
                import_receipt=imported.to_dict(),
                custody_receipt=custody.to_dict(),
            )
        raise AssertionError(frame_type)

    def finish(self) -> None:
        self.finished = True

    def abort(self) -> None:
        self.aborted = True


def _inputs() -> tuple[bytearray, bytearray, bytearray]:
    return (
        bytearray(b"synthetic encrypted PPK"),
        bytearray(b"synthetic public key"),
        bytearray(b"synthetic passphrase"),
    )


def _session(controller: FakeController) -> PpkImportOperatorSession:
    return PpkImportOperatorSession(
        helper_spec=PpkHelperLaunchSpec("C:\\Python312\\python.exe"),
        controller_factory=lambda: controller,
        epoch_ms=lambda: NOW + 1_000,
        identity=lambda kind: SESSION if kind == "session" else f"task059-{kind}-fixed",
    )


def _begin(session: PpkImportOperatorSession, inputs):
    ppk, public, passphrase = inputs
    return session.begin(
        preflight_payload=_preflight().to_dict(),
        ppk_document=ppk,
        rfc4716_public_key=public,
        passphrase_utf8=passphrase,
        owner_scope_sha256=SHA,
        destination_path=DESTINATION,
    )


def test_success_projects_operator_ready_and_completes_once() -> None:
    controller = FakeController()
    session = _session(controller)
    inputs = _inputs()
    view = _begin(session, inputs)

    assert view.state == "READY_FOR_EXPLICIT_HUMAN_CUSTODY_IMPORT"
    assert view.destination_path == DESTINATION
    assert "\u7f72\u540d\u9375" in view.title
    assert DESTINATION not in repr(view)
    assert all(value and set(value) == {0} for value in inputs)

    result = session.confirm(explicit_human_confirmation=True)
    assert result.receipt.to_dict()["state"] == "CUSTODIED_AND_READBACK_VERIFIED"
    assert controller.finished is True
    assert [frame["frame_type"] for frame in controller.sent] == [
        "HELLO",
        "AUTH_REQUEST",
        "CONFIRM",
    ]
    with pytest.raises(PpkImportOperatorError) as error:
        session.confirm(explicit_human_confirmation=True)
    assert error.value.code == "ERR_PPK_OPERATOR_SESSION_NOT_READY"


def test_cancel_is_explicit_and_finishes_without_confirm() -> None:
    controller = FakeController()
    session = _session(controller)
    _begin(session, _inputs())
    session.cancel()
    assert controller.finished is True
    assert controller.sent[-1]["frame_type"] == "CANCEL"


def test_false_confirmation_does_not_send_or_consume_ready() -> None:
    controller = FakeController()
    session = _session(controller)
    _begin(session, _inputs())
    count = len(controller.sent)
    with pytest.raises(PpkImportOperatorError) as error:
        session.confirm(explicit_human_confirmation=False)
    assert error.value.code == "ERR_PPK_CUSTODY_IMPORT_CONFIRMATION_REQUIRED"
    assert len(controller.sent) == count
    session.cancel()


@pytest.mark.parametrize(
    "code",
    [
        "ERR_PPK_SECRET_AUTHENTICATION_FAILED",
        "ERR_PPK_CUSTODY_RESULT_LOST_REQUIRES_READBACK",
    ],
)
def test_helper_failure_code_is_preserved_body_free(code: str) -> None:
    controller = FakeController(failure_code=code)
    session = _session(controller)
    inputs = _inputs()
    if code == "ERR_PPK_SECRET_AUTHENTICATION_FAILED":
        with pytest.raises(PpkImportOperatorError) as error:
            _begin(session, inputs)
    else:
        _begin(session, inputs)
        with pytest.raises(PpkImportOperatorError) as error:
            session.confirm(explicit_human_confirmation=True)
    assert error.value.code == code
    assert repr(error.value) == f"PpkImportOperatorError(code={code!r})"
    assert controller.aborted is True
    assert all(value and set(value) == {0} for value in inputs)


def test_send_failure_clears_every_transferred_input() -> None:
    controller = FakeController(send_error=True)
    session = _session(controller)
    inputs = _inputs()
    with pytest.raises(PpkImportOperatorError) as error:
        _begin(session, inputs)
    assert error.value.code == "ERR_PPK_HELPER_PIPE_IO"
    assert controller.aborted is True
    assert all(value and set(value) == {0} for value in inputs)

def test_invalid_input_clears_every_mutable_companion() -> None:
    controller = FakeController()
    session = _session(controller)
    inputs = (bytearray(b"ppk"), bytearray(), bytearray(b"passphrase"))
    with pytest.raises(PpkImportOperatorError) as error:
        _begin(session, inputs)
    assert error.value.code == "ERR_PPK_OPERATOR_INPUT_INVALID"
    assert inputs[0] and set(inputs[0]) == {0}
    assert inputs[1] == bytearray()
    assert inputs[2] and set(inputs[2]) == {0}
    assert controller.started is False


def test_parent_rejects_canonical_ready_drift() -> None:
    controller = FakeController(ready_drift=True)
    session = _session(controller)
    inputs = _inputs()
    with pytest.raises(PpkImportOperatorError) as error:
        _begin(session, inputs)
    assert error.value.code == "ERR_PPK_HELPER_PROTOCOL"
    assert controller.aborted is True
    assert all(value and set(value) == {0} for value in inputs)


def test_session_is_one_use_even_after_failed_begin() -> None:
    controller = FakeController(send_error=True)
    session = _session(controller)
    with pytest.raises(PpkImportOperatorError):
        _begin(session, _inputs())
    with pytest.raises(PpkImportOperatorError) as error:
        _begin(session, _inputs())
    assert error.value.code == "ERR_PPK_OPERATOR_SESSION_ALREADY_STARTED"


def test_close_aborts_active_ready_session() -> None:
    controller = FakeController()
    session = _session(controller)
    _begin(session, _inputs())
    session.close()
    assert controller.aborted is True
    with pytest.raises(PpkImportOperatorError):
        session.cancel()
