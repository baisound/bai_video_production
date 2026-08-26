from __future__ import annotations

import base64
from dataclasses import replace
import json

import pytest

from ai_video_production.owner_signing_key_custody import OwnerSigningKeyCustodyReceipt
from ai_video_production.owner_signing_key_ppk_custody_import import (
    PpkCustodyImportConfirmation,
    PpkCustodyImportReady,
    PpkCustodyImportReceipt,
)
from ai_video_production.owner_signing_key_ppk_preflight import PpkImportPreflight
from ai_video_production.owner_signing_key_ppk_process_wire import (
    BoundedFrameReader,
    MAX_FRAME_BYTES,
    MAX_FRAMES_PER_DIRECTION,
    PROTOCOL_VERSION,
    PpkHelperProtocolState,
    PpkProcessWireError,
    ProtocolState,
    decode_frame,
    encode_frame,
    validate_frame,
)
from ai_video_production.serialization import sha256_bytes


SESSION = "task059-p1c-session-001"
SHA = sha256_bytes(b"task059-p1c")
FINGERPRINT = "SHA256:" + base64.b64encode(bytes(range(32))).decode("ascii").rstrip("=")


def _base(frame_type: str) -> dict[str, object]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "frame_type": frame_type,
        "session_id": SESSION,
    }


def _preflight() -> PpkImportPreflight:
    return PpkImportPreflight(
        observed_at_epoch_ms=1_777_200_000_000,
        ppk_file_sha256=SHA,
        public_key_file_sha256=SHA,
        ppk_public_blob_sha256=SHA,
        private_ciphertext_sha256=SHA,
        signer_key_id_sha256=SHA,
        openssh_sha256_fingerprint=FINGERPRINT,
        argon2_memory_kib=8192,
        argon2_passes=3,
        argon2_parallelism=1,
    )


def _hello() -> dict[str, object]:
    return {
        **_base("HELLO"),
        "capability_coordinates": {
            "preflight_schema_version": "1.0.0",
            "ready_record_version": "1.0.0",
        },
    }


def _hello_accepted() -> dict[str, object]:
    return _base("HELLO_ACCEPTED")


def _auth_request(secret_text: str = "synthetic-passphrase") -> dict[str, object]:
    return {
        **_base("AUTH_REQUEST"),
        "preflight": _preflight().to_dict(),
        "custody_request": {
            "owner_scope_sha256": SHA,
            "destination_path_utf8_b64": base64.b64encode(b"C:\\\\BVP\\\\custody.json").decode("ascii"),
        },
        "ppk_document_b64": base64.b64encode(b"synthetic encrypted PPK").decode("ascii"),
        "rfc4716_public_key_b64": base64.b64encode(b"synthetic RFC4716 public").decode("ascii"),
        "passphrase_utf8_b64": base64.b64encode(secret_text.encode("utf-8")).decode("ascii"),
    }


def _ready_record() -> PpkCustodyImportReady:
    return PpkCustodyImportReady(
        session_id=SESSION,
        challenge_id="task059-challenge-001",
        custody_id="task059-custody-001",
        preflight_sha256=SHA,
        ppk_file_sha256=SHA,
        signer_key_id_sha256=SHA,
        openssh_sha256_fingerprint=FINGERPRINT,
        owner_scope_sha256=SHA,
        destination_path_sha256=SHA,
        ready_at_epoch_ms=1_777_200_000_000,
        expires_at_epoch_ms=1_777_200_120_000,
    )


def _ready() -> dict[str, object]:
    return {**_base("READY"), "ready": _ready_record().to_dict()}


def _confirmation_record() -> PpkCustodyImportConfirmation:
    ready = _ready_record()
    return PpkCustodyImportConfirmation(
        confirmation_id="task059-confirmation-001",
        session_id=SESSION,
        challenge_id=ready.challenge_id,
        ready_sha256=ready.to_dict()["ready_sha256"],
        custody_id=ready.custody_id,
        signer_key_id_sha256=ready.signer_key_id_sha256,
        owner_scope_sha256=ready.owner_scope_sha256,
        destination_path_sha256=ready.destination_path_sha256,
        confirmed_at_epoch_ms=1_777_200_001_000,
    )


def _confirm() -> dict[str, object]:
    return {**_base("CONFIRM"), "confirmation": _confirmation_record().to_dict()}


def _completed() -> dict[str, object]:
    confirmation = _confirmation_record()
    custody = OwnerSigningKeyCustodyReceipt(
        receipt_id="task029-custody-receipt-001",
        custody_id="task059-custody-001",
        owner_scope_sha256=SHA,
        signer_key_id_sha256=SHA,
        confirmation_sha256=SHA,
        custodied_at_epoch_ms=1_777_200_002_000,
        cipher_suite="TASK059_TEST_CIPHER_V1",
    )
    imported = PpkCustodyImportReceipt(
        receipt_id="task059-import-receipt-001",
        ready_sha256=_ready_record().to_dict()["ready_sha256"],
        confirmation_sha256=confirmation.to_dict()["confirmation_sha256"],
        custody_receipt_sha256=custody.to_dict()["custody_receipt_sha256"],
        preflight_sha256=SHA,
        ppk_file_sha256=SHA,
        signer_key_id_sha256=SHA,
        owner_scope_sha256=SHA,
        destination_path_sha256=SHA,
        imported_at_epoch_ms=1_777_200_002_000,
    )
    return {
        **_base("COMPLETED"),
        "import_receipt": imported.to_dict(),
        "custody_receipt": custody.to_dict(),
    }


def _failed() -> dict[str, object]:
    return {
        **_base("FAILED"),
        "phase": "AUTHENTICATION",
        "error_code": "ERR_PPK_SECRET_AUTHENTICATION_FAILED",
        "retryable": False,
    }


def _raw(payload: bytes, *, length: int | None = None) -> bytes:
    size = len(payload) if length is None else length
    return size.to_bytes(4, "big") + payload


@pytest.mark.parametrize(
    "frame",
    [
        _hello(),
        _hello_accepted(),
        _auth_request(),
        _ready(),
        _confirm(),
        {**_base("CANCEL"), "reason_code": "OWNER_CANCELLED"},
        _completed(),
        _failed(),
    ],
)
def test_all_frame_types_round_trip_in_canonical_form(frame: dict[str, object]) -> None:
    encoded = encode_frame(frame)
    assert int.from_bytes(encoded[:4], "big") == len(encoded) - 4
    assert decode_frame(encoded) == frame
    assert encoded[4:] == json.dumps(
        frame,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def test_partial_reader_assembles_multiple_frames_and_clears_buffer() -> None:
    first = encode_frame(_hello())
    second = encode_frame(_hello_accepted())
    reader = BoundedFrameReader()

    assert reader.feed(first[:2]) == []
    assert reader.feed(first[2:17]) == []
    frames = reader.feed(first[17:] + second)

    assert frames == [_hello(), _hello_accepted()]
    assert reader.frame_count == 2
    reader.finish()
    reader.clear()


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"\x00\x00\x00",
        _raw(b"", length=0),
        _raw(b"{}", length=MAX_FRAME_BYTES + 1),
        _raw(b"{}", length=3),
        _raw(b"{}") + b"x",
        _raw(b"\xef\xbb\xbf{}"),
        _raw(b"\xff"),
    ],
)
def test_invalid_frame_boundaries_fail_with_fixed_error(data: bytes) -> None:
    with pytest.raises(PpkProcessWireError) as caught:
        decode_frame(data)
    assert str(caught.value) == "ERR_PPK_HELPER_PROTOCOL"


@pytest.mark.parametrize(
    "payload",
    [
        b'{"frame_type":"HELLO_ACCEPTED","frame_type":"FAILED","protocol_version":1,"session_id":"task059"}',
        b'{"frame_type":"HELLO_ACCEPTED","protocol_version":1,"session_id":"task059","x":NaN}',
        b'{ "frame_type":"HELLO_ACCEPTED","protocol_version":1,"session_id":"task059"}',
        b'{"session_id":"task059","protocol_version":1,"frame_type":"HELLO_ACCEPTED"}',
        b'[]',
    ],
)
def test_duplicate_nan_unknown_noncanonical_or_nonobject_json_fails(payload: bytes) -> None:
    with pytest.raises(PpkProcessWireError):
        decode_frame(_raw(payload))


def test_depth_and_total_field_ceilings_fail_closed() -> None:
    deep: object = "x"
    for _ in range(14):
        deep = {"x": deep}
    with pytest.raises(PpkProcessWireError):
        validate_frame({**_hello_accepted(), "unexpected": deep})

    many = {f"x{index}": index for index in range(129)}
    with pytest.raises(PpkProcessWireError):
        validate_frame({**_hello_accepted(), "unexpected": many})


def test_unknown_field_version_session_and_failure_oracle_fail_closed() -> None:
    invalid = [
        {**_hello_accepted(), "unknown": True},
        {**_hello_accepted(), "protocol_version": 2},
        {**_hello_accepted(), "session_id": "bad session"},
        {**_failed(), "error_code": "ValueError: bad password"},
        {**_failed(), "retryable": True},
    ]
    for frame in invalid:
        with pytest.raises(PpkProcessWireError):
            encode_frame(frame)


def test_auth_request_error_and_repr_never_echo_secret() -> None:
    secret = "SYNTHETIC_SECRET_MUST_NOT_APPEAR"
    frame = _auth_request(secret)
    frame["unknown_secret"] = secret

    with pytest.raises(PpkProcessWireError) as caught:
        encode_frame(frame)

    rendered = f"{caught.value!s} {caught.value!r}"
    assert secret not in rendered
    assert base64.b64encode(secret.encode()).decode() not in rendered
    assert rendered == (
        "ERR_PPK_HELPER_PROTOCOL "
        "PpkProcessWireError(code='ERR_PPK_HELPER_PROTOCOL')"
    )


def test_reader_rejects_ninth_frame_and_truncated_finish() -> None:
    reader = BoundedFrameReader()
    frame = encode_frame(_hello_accepted())
    for _ in range(MAX_FRAMES_PER_DIRECTION):
        assert reader.feed(frame) == [_hello_accepted()]
    with pytest.raises(PpkProcessWireError):
        reader.feed(frame)

    truncated = BoundedFrameReader()
    assert truncated.feed(frame[:-1]) == []
    with pytest.raises(PpkProcessWireError):
        truncated.finish()


def test_exact_success_state_machine_and_exit() -> None:
    state = PpkHelperProtocolState(session_id=SESSION)
    state.parent_send(_hello())
    assert state.state is ProtocolState.HELLO_SENT
    state.helper_send(_hello_accepted())
    state.parent_send(_auth_request())
    state.helper_send(_ready())
    state.parent_send(_confirm())
    state.helper_send(_completed())
    state.helper_exit(exit_code=0)
    assert state.state is ProtocolState.EXITED


def test_cancel_and_fixed_failure_are_terminal_without_completion() -> None:
    state = PpkHelperProtocolState(session_id=SESSION)
    state.parent_send(_hello())
    state.helper_send(_hello_accepted())
    state.parent_send(_auth_request())
    state.helper_send(_ready())
    state.parent_send({**_base("CANCEL"), "reason_code": "OWNER_CANCELLED"})
    state.helper_send(
        {
            **_base("FAILED"),
            "phase": "CONFIRMATION",
            "error_code": "ERR_PPK_HELPER_CANCELLED",
            "retryable": False,
        }
    )
    state.helper_exit(exit_code=0)
    assert state.state is ProtocolState.EXITED


@pytest.mark.parametrize(
    "actions",
    [
        [("helper", _hello_accepted())],
        [("parent", _hello()), ("parent", _auth_request())],
        [("parent", _hello()), ("helper", _hello_accepted()), ("parent", _confirm())],
        [
            ("parent", _hello()),
            ("helper", _hello_accepted()),
            ("parent", _auth_request()),
            ("parent", _auth_request()),
        ],
    ],
)
def test_out_of_order_or_replayed_frames_fail_closed(actions: list[tuple[str, dict[str, object]]]) -> None:
    state = PpkHelperProtocolState(session_id=SESSION)
    with pytest.raises(PpkProcessWireError):
        for direction, frame in actions:
            if direction == "parent":
                state.parent_send(frame)
            else:
                state.helper_send(frame)
    assert state.state is ProtocolState.FAILED


def test_session_mismatch_and_unexpected_exit_fail_closed() -> None:
    state = PpkHelperProtocolState(session_id=SESSION)
    wrong = {**_hello(), "session_id": "task059-other-session"}
    with pytest.raises(PpkProcessWireError):
        state.parent_send(wrong)
    assert state.state is ProtocolState.FAILED

    state = PpkHelperProtocolState(session_id=SESSION)
    with pytest.raises(PpkProcessWireError):
        state.helper_exit(exit_code=0)
    assert state.state is ProtocolState.FAILED


def test_wire_module_has_no_process_filesystem_or_network_dependency() -> None:
    import ai_video_production.owner_signing_key_ppk_process_wire as module

    source_names = set(module.__dict__)
    assert source_names.isdisjoint(
        {"subprocess", "socket", "pathlib", "tempfile", "Popen", "Path"}
    )



def test_auth_request_requires_strict_utf8_after_base64_decode() -> None:
    frame = _auth_request()
    frame["passphrase_utf8_b64"] = base64.b64encode(b"\xff\xfe").decode("ascii")
    with pytest.raises(PpkProcessWireError):
        validate_frame(frame)


def test_nested_ready_and_confirmation_must_bind_outer_session() -> None:
    ready = _ready_record()
    wrong_ready = replace(ready, session_id="task059-other-session")
    with pytest.raises(PpkProcessWireError):
        validate_frame({**_base("READY"), "ready": wrong_ready.to_dict()})

    confirmation = _confirmation_record()
    wrong_confirmation = replace(confirmation, session_id="task059-other-session")
    with pytest.raises(PpkProcessWireError):
        validate_frame(
            {**_base("CONFIRM"), "confirmation": wrong_confirmation.to_dict()}
        )


def test_state_machine_binds_ready_confirmation_and_completion_hashes() -> None:
    state = PpkHelperProtocolState(session_id=SESSION)
    state.parent_send(_hello())
    state.helper_send(_hello_accepted())
    state.parent_send(_auth_request())
    state.helper_send(_ready())
    wrong_confirmation = replace(
        _confirmation_record(), challenge_id="task059-other-challenge"
    )
    with pytest.raises(PpkProcessWireError):
        state.parent_send(
            {**_base("CONFIRM"), "confirmation": wrong_confirmation.to_dict()}
        )
    assert state.state is ProtocolState.FAILED

    state = PpkHelperProtocolState(session_id=SESSION)
    state.parent_send(_hello())
    state.helper_send(_hello_accepted())
    state.parent_send(_auth_request())
    state.helper_send(_ready())
    state.parent_send(_confirm())
    completion = _completed()
    imported = PpkCustodyImportReceipt.from_dict(completion["import_receipt"])
    completion["import_receipt"] = replace(
        imported, confirmation_sha256=SHA
    ).to_dict()
    with pytest.raises(PpkProcessWireError):
        state.helper_send(completion)
    assert state.state is ProtocolState.FAILED


def test_completed_frame_binds_import_and_custody_receipts() -> None:
    completion = _completed()
    custody = OwnerSigningKeyCustodyReceipt.from_dict(completion["custody_receipt"])
    completion["custody_receipt"] = replace(
        custody, owner_scope_sha256=sha256_bytes(b"other-owner")
    ).to_dict()
    with pytest.raises(PpkProcessWireError):
        validate_frame(completion)


def test_invalid_reader_frame_clears_unconsumed_bytes() -> None:
    secret = b"SYNTHETIC_UNCONSUMED_SECRET"
    invalid = {**_hello_accepted(), "unexpected": "invalid"}
    payload = json.dumps(
        invalid, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    reader = BoundedFrameReader()
    with pytest.raises(PpkProcessWireError):
        reader.feed(_raw(payload) + secret)
    assert reader._buffer == bytearray()


def test_auth_request_requires_exact_body_safe_custody_coordinates() -> None:
    missing = _auth_request()
    del missing["custody_request"]
    with pytest.raises(PpkProcessWireError):
        validate_frame(missing)

    cases = [
        {"owner_scope_sha256": "bad", "destination_path_utf8_b64": base64.b64encode(b"C:\\x").decode()},
        {"owner_scope_sha256": SHA, "destination_path_utf8_b64": base64.b64encode(b"bad\x00path").decode()},
        {"owner_scope_sha256": SHA, "destination_path_utf8_b64": base64.b64encode(b"\xff").decode()},
        {"owner_scope_sha256": SHA, "destination_path_utf8_b64": ""},
        {
            "owner_scope_sha256": SHA,
            "destination_path_utf8_b64": base64.b64encode(b"C:\\x").decode(),
            "unknown": True,
        },
    ]
    for custody_request in cases:
        frame = _auth_request()
        frame["custody_request"] = custody_request
        with pytest.raises(PpkProcessWireError) as caught:
            validate_frame(frame)
        rendered = f"{caught.value!s} {caught.value!r}"
        assert "bad" not in rendered
        assert "C:\\x" not in rendered
