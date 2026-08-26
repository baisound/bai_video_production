"""TASK-059 P1C-D short-lived PPK import helper runtime.

The helper accepts one anonymous-pipe protocol attempt, keeps secret material
process-local, delegates cryptography/custody to P1A/P1B, and exits. It never
logs and never retries a custody mutation.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import os
import secrets
import sys
import time
from typing import Any, BinaryIO, Callable, Mapping

from .owner_signing_key_custody import OwnerSigningKeyCustodyStore
from .owner_signing_key_ppk_custody_import import (
    PpkCustodyImportResult,
    execute_ppk_custody_import,
    prepare_ppk_custody_import_ready,
)
from .owner_signing_key_ppk_process_wire import (
    MAX_FRAME_BYTES,
    PROTOCOL_VERSION,
    PpkHelperProtocolState,
    PpkProcessWireError,
    decode_frame,
    encode_frame,
)
from .owner_signing_key_ppk_secret_auth import (
    _AuthenticatedPpkSecret,
    _authenticate_ppk_secret_for_r9b,
)


READY_WINDOW_MS = 120_000
_FAILED_CODES = {
    "protocol": ("PROTOCOL", "ERR_PPK_HELPER_PROTOCOL"),
    "authentication": (
        "AUTHENTICATION",
        "ERR_PPK_SECRET_AUTHENTICATION_FAILED",
    ),
    "custody": ("CUSTODY", "ERR_PPK_CUSTODY_IMPORT_FAILED"),
    "result_lost": (
        "CUSTODY",
        "ERR_PPK_CUSTODY_RESULT_LOST_REQUIRES_READBACK",
    ),
    "cancelled": ("CONFIRMATION", "ERR_PPK_HELPER_CANCELLED"),
}


class _ParentEof(EOFError):
    pass


def _zero(value: bytearray | None) -> None:
    if value is not None:
        for index in range(len(value)):
            value[index] = 0


def _read_exact(stream: BinaryIO, size: int, *, allow_initial_eof: bool = False) -> bytes:
    result = bytearray()
    try:
        while len(result) < size:
            chunk = stream.read(size - len(result))
            if not chunk:
                if allow_initial_eof and not result:
                    raise _ParentEof
                raise PpkProcessWireError("ERR_PPK_HELPER_PROTOCOL")
            result.extend(chunk)
        return bytes(result)
    finally:
        _zero(result)


def _read_frame(stream: BinaryIO, *, allow_eof: bool = False) -> dict[str, Any]:
    header = _read_exact(stream, 4, allow_initial_eof=allow_eof)
    length = int.from_bytes(header, "big")
    if length < 1 or length > MAX_FRAME_BYTES:
        raise PpkProcessWireError("ERR_PPK_HELPER_PROTOCOL")
    payload = _read_exact(stream, length)
    return decode_frame(header + payload)


def _write_frame(stream: BinaryIO, frame: Mapping[str, Any]) -> None:
    encoded = bytearray(encode_frame(frame))
    try:
        stream.write(encoded)
        stream.flush()
    finally:
        _zero(encoded)


@dataclass(frozen=True, slots=True)
class PpkHelperDependencies:
    authenticate: Callable[..., _AuthenticatedPpkSecret] = (
        _authenticate_ppk_secret_for_r9b
    )
    prepare_ready: Callable[..., Any] = prepare_ppk_custody_import_ready
    execute_import: Callable[..., PpkCustodyImportResult] = execute_ppk_custody_import
    store_factory: Callable[[str], OwnerSigningKeyCustodyStore] = (
        OwnerSigningKeyCustodyStore
    )
    epoch_ms: Callable[[], int] = lambda: time.time_ns() // 1_000_000
    identity: Callable[[str], str] = lambda kind: (
        f"task059-{kind}-{secrets.token_hex(16)}"
    )


class PpkHelperRuntime:
    """Execute exactly one helper attempt over supplied binary streams."""

    def __init__(self, dependencies: PpkHelperDependencies | None = None) -> None:
        self._dependencies = dependencies or PpkHelperDependencies()

    def run(self, stdin: BinaryIO, stdout: BinaryIO) -> int:
        session_id: str | None = None
        state: PpkHelperProtocolState | None = None
        secret: _AuthenticatedPpkSecret | None = None
        custody_dispatched = False
        try:
            hello = _read_frame(stdin, allow_eof=True)
            session_id = hello["session_id"]
            state = PpkHelperProtocolState(session_id=session_id)
            state.parent_send(hello)
            accepted = self._frame(session_id, "HELLO_ACCEPTED")
            state.helper_send(accepted)
            _write_frame(stdout, accepted)

            auth = _read_frame(stdin, allow_eof=True)
            state.parent_send(auth)
            secret, destination_path = self._authenticate(auth)
            now = self._epoch_ms()
            ready = self._dependencies.prepare_ready(
                secret=secret,
                session_id=session_id,
                challenge_id=self._identity("challenge"),
                custody_id=self._identity("custody"),
                owner_scope_sha256=auth["custody_request"]["owner_scope_sha256"],
                destination_path=destination_path,
                ready_at_epoch_ms=now,
                expires_at_epoch_ms=now + READY_WINDOW_MS,
            )
            ready_frame = self._frame(session_id, "READY", ready=ready.to_dict())
            state.helper_send(ready_frame)
            _write_frame(stdout, ready_frame)

            decision = _read_frame(stdin, allow_eof=True)
            state.parent_send(decision)
            if decision["frame_type"] == "CANCEL":
                secret.clear()
                secret = None
                failed = self._failed(session_id, "cancelled")
                state.helper_send(failed)
                _write_frame(stdout, failed)
                return 0

            custody_dispatched = True
            result = self._dependencies.execute_import(
                receipt_id=self._identity("import-receipt"),
                custody_receipt_id=self._identity("custody-receipt"),
                r9b_confirmation_id=self._identity("r9b-confirmation"),
                secret=secret,
                custody_store=self._dependencies.store_factory(destination_path),
                ready_payload=ready.to_dict(),
                confirmation_payload=decision["confirmation"],
                imported_at_epoch_ms=self._epoch_ms(),
            )
            if not secret.cleared:
                raise ValueError("custody adapter did not consume the secret")
            secret = None
            completed = self._frame(
                session_id,
                "COMPLETED",
                import_receipt=result.receipt.to_dict(),
                custody_receipt=result.custody_receipt.to_dict(),
            )
            state.helper_send(completed)
            _write_frame(stdout, completed)
            return 0
        except _ParentEof:
            return 0
        except PpkProcessWireError:
            phase = "result_lost" if custody_dispatched else "protocol"
            self._write_failed_best_effort(stdout, session_id, phase)
            return 4 if phase == "result_lost" else 2
        except Exception as exc:
            phase = (
                "result_lost"
                if custody_dispatched
                else ("authentication" if secret is None else "custody")
            )
            self._write_failed_best_effort(stdout, session_id, phase)
            del exc
            return 4 if phase == "result_lost" else 3
        finally:
            if secret is not None:
                secret.clear()

    def _authenticate(
        self,
        auth: Mapping[str, Any],
    ) -> tuple[_AuthenticatedPpkSecret, str]:
        ppk = bytearray()
        public = bytearray()
        passphrase = bytearray()
        destination = bytearray()
        try:
            ppk.extend(base64.b64decode(auth["ppk_document_b64"], validate=True))
            public.extend(
                base64.b64decode(auth["rfc4716_public_key_b64"], validate=True)
            )
            passphrase.extend(
                base64.b64decode(auth["passphrase_utf8_b64"], validate=True)
            )
            destination.extend(
                base64.b64decode(
                    auth["custody_request"]["destination_path_utf8_b64"],
                    validate=True,
                )
            )
            destination_path = destination.decode("utf-8", errors="strict")
            if not os.path.isabs(destination_path):
                raise ValueError("custody destination must be absolute")
            authenticated = self._dependencies.authenticate(
                bytes(ppk),
                bytes(public),
                passphrase_utf8=passphrase,
                expected_preflight_payload=auth["preflight"],
            )
            return authenticated, destination_path
        finally:
            _zero(ppk)
            _zero(public)
            _zero(passphrase)
            _zero(destination)

    def _epoch_ms(self) -> int:
        value = self._dependencies.epoch_ms()
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("helper clock is invalid")
        return value

    def _identity(self, kind: str) -> str:
        value = self._dependencies.identity(kind)
        if not isinstance(value, str) or not value:
            raise ValueError("helper identity is invalid")
        return value

    @staticmethod
    def _frame(session_id: str, frame_type: str, **payload: object) -> dict[str, Any]:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "frame_type": frame_type,
            "session_id": session_id,
            **payload,
        }

    @classmethod
    def _failed(cls, session_id: str, kind: str) -> dict[str, Any]:
        phase, code = _FAILED_CODES[kind]
        return cls._frame(
            session_id,
            "FAILED",
            phase=phase,
            error_code=code,
            retryable=False,
        )

    @classmethod
    def _write_failed_best_effort(
        cls,
        stdout: BinaryIO,
        session_id: str | None,
        kind: str,
    ) -> None:
        if session_id is None:
            return
        try:
            _write_frame(stdout, cls._failed(session_id, kind))
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments != ["--protocol-version", str(PROTOCOL_VERSION)]:
        return 64
    return PpkHelperRuntime().run(sys.stdin.buffer, sys.stdout.buffer)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["PpkHelperDependencies", "PpkHelperRuntime", "main"]
