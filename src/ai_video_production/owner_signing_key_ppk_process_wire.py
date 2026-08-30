"""TASK-059 P1C strict, body-safe helper process wire contract.

This module owns canonical JSON framing and protocol ordering only.  It does
not launch a process, authenticate a PPK, handle custody, sign, or persist
anything.  AUTH_REQUEST is the sole secret-bearing frame; validation errors
therefore expose fixed codes and never payload content.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from enum import Enum
import json
import re
from typing import Any, Mapping

from .owner_signing_key_custody import OwnerSigningKeyCustodyReceipt
from .owner_signing_key_ppk_custody_import import (
    RECORD_VERSION as CUSTODY_IMPORT_RECORD_VERSION,
    PpkCustodyImportConfirmation,
    PpkCustodyImportReady,
    PpkCustodyImportReceipt,
)
from .owner_signing_key_ppk_preflight import (
    SCHEMA_VERSION as PREFLIGHT_SCHEMA_VERSION,
    PpkImportPreflight,
)


PROTOCOL_VERSION = 1
MAX_FRAME_BYTES = 131_072
MAX_FRAMES_PER_DIRECTION = 8
MAX_JSON_DEPTH = 12
MAX_JSON_FIELDS = 128
MAX_JSON_LIST_ITEMS = 256
MAX_PPK_DOCUMENT_BYTES = 65_536
MAX_PUBLIC_KEY_BYTES = 16_384
MAX_PASSPHRASE_UTF8_BYTES = 4_096
MAX_DESTINATION_PATH_UTF8_BYTES = 4_096

_SESSION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_B64 = re.compile(r"^[A-Za-z0-9+/]*={0,2}$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_FAILED_PHASES = frozenset(
    {"HELLO", "AUTHENTICATION", "READY", "CONFIRMATION", "CUSTODY", "PROTOCOL"}
)
_FAILED_CODES = frozenset(
    {
        "ERR_PPK_HELPER_PROTOCOL",
        "ERR_PPK_HELPER_TIMEOUT",
        "ERR_PPK_HELPER_CANCELLED",
        "ERR_PPK_SECRET_AUTHENTICATION_FAILED",
        "ERR_PPK_CUSTODY_IMPORT_FAILED",
        "ERR_PPK_CUSTODY_RESULT_LOST_REQUIRES_READBACK",
    }
)


class PpkProcessWireError(ValueError):
    """Fixed-detail protocol error safe for body-free diagnostics."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)

    def __repr__(self) -> str:
        return f"PpkProcessWireError(code={self.code!r})"


def _fail(code: str = "ERR_PPK_HELPER_PROTOCOL") -> PpkProcessWireError:
    return PpkProcessWireError(code)


def _exact_fields(value: Mapping[str, Any], expected: set[str]) -> None:
    if set(value) != expected:
        raise _fail()


def _stable_text(value: object, pattern: re.Pattern[str] = _SESSION_ID) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise _fail()
    return value


def _strict_b64(
    value: object,
    *,
    maximum: int,
    strict_utf8: bool = False,
    reject_nul: bool = False,
) -> None:
    if not isinstance(value, str) or not value or len(value) > (maximum * 4 // 3) + 4:
        raise _fail()
    if len(value) % 4 != 0 or _B64.fullmatch(value) is None:
        raise _fail()
    try:
        decoded = bytearray(base64.b64decode(value, validate=True))
    except (ValueError, TypeError):
        raise _fail() from None
    try:
        if not decoded or len(decoded) > maximum or (reject_nul and 0 in decoded):
            raise _fail()
        if strict_utf8:
            try:
                decoded.decode("utf-8", errors="strict")
            except UnicodeError:
                raise _fail() from None
    finally:
        for index in range(len(decoded)):
            decoded[index] = 0


def _validate_json_shape(value: object, *, depth: int = 0, count: list[int] | None = None) -> None:
    if count is None:
        count = [0]
    if depth > MAX_JSON_DEPTH:
        raise _fail()
    if isinstance(value, Mapping):
        count[0] += len(value)
        if count[0] > MAX_JSON_FIELDS:
            raise _fail()
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > 160:
                raise _fail()
            _validate_json_shape(item, depth=depth + 1, count=count)
        return
    if isinstance(value, list):
        if len(value) > MAX_JSON_LIST_ITEMS:
            raise _fail()
        for item in value:
            _validate_json_shape(item, depth=depth + 1, count=count)
        return
    if value is None or isinstance(value, (str, bool, int)):
        if isinstance(value, str):
            try:
                encoded_length = len(value.encode("utf-8"))
            except UnicodeError:
                raise _fail() from None
            if encoded_length > MAX_FRAME_BYTES:
                raise _fail()
        return
    raise _fail()


def _preflight_from_dict(value: object) -> PpkImportPreflight:
    if not isinstance(value, Mapping):
        raise _fail()
    fields = PpkImportPreflight.__dataclass_fields__
    try:
        result = PpkImportPreflight(**{name: value[name] for name in fields})
    except (KeyError, TypeError, ValueError):
        raise _fail() from None
    if result.to_dict() != dict(value):
        raise _fail()
    return result


def _canonical_object(value: Mapping[str, Any]) -> bytes:
    try:
        encoded = json.dumps(
            dict(value),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise _fail() from None
    if not encoded or len(encoded) > MAX_FRAME_BYTES:
        raise _fail()
    return encoded


def _reject_constant(_: str) -> None:
    raise _fail()


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _fail()
        result[key] = value
    return result


def validate_frame(value: object) -> dict[str, Any]:
    """Validate one decoded frame and return a shallow defensive copy."""

    if not isinstance(value, Mapping):
        raise _fail()
    frame = dict(value)
    _validate_json_shape(frame)
    frame_type = frame.get("frame_type")
    if frame.get("protocol_version") != PROTOCOL_VERSION or not isinstance(frame_type, str):
        raise _fail()
    _stable_text(frame.get("session_id"))
    common = {"protocol_version", "frame_type", "session_id"}

    if frame_type == "HELLO":
        _exact_fields(frame, common | {"capability_coordinates"})
        coordinates = frame["capability_coordinates"]
        if not isinstance(coordinates, Mapping):
            raise _fail()
        _exact_fields(
            coordinates,
            {"preflight_schema_version", "ready_record_version"},
        )
        if coordinates != {
            "preflight_schema_version": PREFLIGHT_SCHEMA_VERSION,
            "ready_record_version": CUSTODY_IMPORT_RECORD_VERSION,
        }:
            raise _fail()
    elif frame_type == "HELLO_ACCEPTED":
        _exact_fields(frame, common)
    elif frame_type == "AUTH_REQUEST":
        _exact_fields(
            frame,
            common
            | {
                "preflight",
                "ppk_document_b64",
                "custody_request",
                "rfc4716_public_key_b64",
                "passphrase_utf8_b64",
            },
        )
        custody_request = frame["custody_request"]
        if not isinstance(custody_request, Mapping):
            raise _fail()
        _exact_fields(
            custody_request,
            {"owner_scope_sha256", "destination_path_utf8_b64"},
        )
        if not isinstance(custody_request["owner_scope_sha256"], str) or (
            _SHA256.fullmatch(custody_request["owner_scope_sha256"]) is None
        ):
            raise _fail()
        _strict_b64(
            custody_request["destination_path_utf8_b64"],
            maximum=MAX_DESTINATION_PATH_UTF8_BYTES,
            strict_utf8=True,
            reject_nul=True,
        )
        _preflight_from_dict(frame["preflight"])
        _strict_b64(frame["ppk_document_b64"], maximum=MAX_PPK_DOCUMENT_BYTES)
        _strict_b64(frame["rfc4716_public_key_b64"], maximum=MAX_PUBLIC_KEY_BYTES)
        _strict_b64(
            frame["passphrase_utf8_b64"],
            maximum=MAX_PASSPHRASE_UTF8_BYTES,
            strict_utf8=True,
        )
    elif frame_type == "READY":
        _exact_fields(frame, common | {"ready"})
        try:
            ready = PpkCustodyImportReady.from_dict(frame["ready"])
        except (KeyError, TypeError, ValueError):
            raise _fail() from None
        if ready.session_id != frame["session_id"]:
            raise _fail()
    elif frame_type == "CONFIRM":
        _exact_fields(frame, common | {"confirmation"})
        try:
            confirmation = PpkCustodyImportConfirmation.from_dict(frame["confirmation"])
        except (KeyError, TypeError, ValueError):
            raise _fail() from None
        if confirmation.session_id != frame["session_id"]:
            raise _fail()
    elif frame_type == "CANCEL":
        _exact_fields(frame, common | {"reason_code"})
        if frame["reason_code"] != "OWNER_CANCELLED":
            raise _fail()
    elif frame_type == "COMPLETED":
        _exact_fields(frame, common | {"import_receipt", "custody_receipt"})
        try:
            imported = PpkCustodyImportReceipt.from_dict(frame["import_receipt"])
            custody = OwnerSigningKeyCustodyReceipt.from_dict(frame["custody_receipt"])
        except (KeyError, TypeError, ValueError):
            raise _fail() from None
        if (
            imported.custody_receipt_sha256
            != custody.to_dict()["custody_receipt_sha256"]
            or imported.signer_key_id_sha256 != custody.signer_key_id_sha256
            or imported.owner_scope_sha256 != custody.owner_scope_sha256
        ):
            raise _fail()
    elif frame_type == "FAILED":
        _exact_fields(frame, common | {"phase", "error_code", "retryable"})
        if (
            frame["phase"] not in _FAILED_PHASES
            or frame["error_code"] not in _FAILED_CODES
            or frame["retryable"] is not False
        ):
            raise _fail()
    else:
        raise _fail()
    return frame


def encode_frame(value: Mapping[str, Any]) -> bytes:
    """Encode one exact canonical frame with a big-endian uint32 prefix."""

    payload = _canonical_object(validate_frame(value))
    return len(payload).to_bytes(4, "big") + payload


def decode_frame(data: bytes | bytearray | memoryview) -> dict[str, Any]:
    """Decode one complete frame; additional or incomplete bytes fail closed."""

    raw = bytes(data)
    if len(raw) < 4:
        raise _fail()
    length = int.from_bytes(raw[:4], "big")
    if length < 1 or length > MAX_FRAME_BYTES or len(raw) != 4 + length:
        raise _fail()
    payload = raw[4:]
    if payload.startswith(b"\xef\xbb\xbf"):
        raise _fail()
    try:
        text = payload.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except PpkProcessWireError:
        raise
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        raise _fail() from None
    frame = validate_frame(value)
    if _canonical_object(frame) != payload:
        raise _fail()
    return frame


@dataclass(slots=True)
class BoundedFrameReader:
    """Incrementally assemble frames while enforcing byte and count ceilings."""

    _buffer: bytearray
    _frame_count: int = 0

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._frame_count = 0

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def feed(self, chunk: bytes | bytearray | memoryview) -> list[dict[str, Any]]:
        if not isinstance(chunk, (bytes, bytearray, memoryview)):
            raise _fail()
        self._buffer.extend(chunk)
        frames: list[dict[str, Any]] = []
        while len(self._buffer) >= 4:
            length = int.from_bytes(self._buffer[:4], "big")
            if length < 1 or length > MAX_FRAME_BYTES:
                self.clear()
                raise _fail()
            total = 4 + length
            if len(self._buffer) < total:
                break
            if self._frame_count >= MAX_FRAMES_PER_DIRECTION:
                self.clear()
                raise _fail()
            raw = bytes(self._buffer[:total])
            for index in range(total):
                self._buffer[index] = 0
            del self._buffer[:total]
            try:
                frames.append(decode_frame(raw))
            except PpkProcessWireError:
                self.clear()
                raise
            self._frame_count += 1
        if len(self._buffer) > MAX_FRAME_BYTES + 4:
            self.clear()
            raise _fail()
        return frames

    def finish(self) -> None:
        if self._buffer:
            self.clear()
            raise _fail()

    def clear(self) -> None:
        for index in range(len(self._buffer)):
            self._buffer[index] = 0
        self._buffer.clear()


class ProtocolState(str, Enum):
    SPAWNED = "SPAWNED"
    HELLO_SENT = "HELLO_SENT"
    HELLO_ACCEPTED = "HELLO_ACCEPTED"
    AUTH_REQUEST_SENT = "AUTH_REQUEST_SENT"
    READY_RECEIVED = "READY_RECEIVED"
    CONFIRM_SENT = "CONFIRM_SENT"
    CANCEL_SENT = "CANCEL_SENT"
    TERMINAL_RECEIVED = "TERMINAL_RECEIVED"
    EXITED = "EXITED"
    FAILED = "FAILED"


class PpkHelperProtocolState:
    """Parent-side exact ordering validator without payload retention."""

    def __init__(self, *, session_id: str) -> None:
        self.session_id = _stable_text(session_id)
        self.state = ProtocolState.SPAWNED
        self._parent_frames = 0
        self._helper_frames = 0
        self._auth_request_sent = False
        self._confirm_sent = False
        self._ready_coordinates: tuple[object, ...] | None = None
        self._confirmation_coordinates: tuple[object, ...] | None = None

    def _accept(
        self, value: Mapping[str, Any], *, parent: bool
    ) -> dict[str, Any]:
        try:
            frame = validate_frame(value)
        except PpkProcessWireError:
            self.state = ProtocolState.FAILED
            raise
        if frame["session_id"] != self.session_id:
            self.state = ProtocolState.FAILED
            raise _fail()
        count = self._parent_frames if parent else self._helper_frames
        if count >= MAX_FRAMES_PER_DIRECTION:
            self.state = ProtocolState.FAILED
            raise _fail()
        if parent:
            self._parent_frames += 1
        else:
            self._helper_frames += 1
        return frame

    def parent_send(self, value: Mapping[str, Any]) -> None:
        frame = self._accept(value, parent=True)
        frame_type = frame["frame_type"]
        transition = (self.state, frame_type)
        if transition == (ProtocolState.SPAWNED, "HELLO"):
            self.state = ProtocolState.HELLO_SENT
        elif transition == (ProtocolState.HELLO_ACCEPTED, "AUTH_REQUEST"):
            if self._auth_request_sent:
                self._protocol_failure()
            self._auth_request_sent = True
            self.state = ProtocolState.AUTH_REQUEST_SENT
        elif transition == (ProtocolState.READY_RECEIVED, "CONFIRM"):
            if self._confirm_sent:
                self._protocol_failure()
            confirmation = PpkCustodyImportConfirmation.from_dict(frame["confirmation"])
            if self._ready_coordinates is None or (
                confirmation.ready_sha256,
                confirmation.challenge_id,
                confirmation.custody_id,
                confirmation.signer_key_id_sha256,
                confirmation.owner_scope_sha256,
                confirmation.destination_path_sha256,
            ) != self._ready_coordinates:
                self._protocol_failure()
            self._confirm_sent = True
            self._confirmation_coordinates = (
                confirmation.ready_sha256,
                confirmation.to_dict()["confirmation_sha256"],
            )
            self.state = ProtocolState.CONFIRM_SENT
        elif transition == (ProtocolState.READY_RECEIVED, "CANCEL"):
            self.state = ProtocolState.CANCEL_SENT
        else:
            self._protocol_failure()

    def helper_send(self, value: Mapping[str, Any]) -> None:
        frame = self._accept(value, parent=False)
        frame_type = frame["frame_type"]
        transition = (self.state, frame_type)
        if transition == (ProtocolState.HELLO_SENT, "HELLO_ACCEPTED"):
            self.state = ProtocolState.HELLO_ACCEPTED
        elif transition == (ProtocolState.AUTH_REQUEST_SENT, "READY"):
            ready = PpkCustodyImportReady.from_dict(frame["ready"])
            self._ready_coordinates = (
                ready.to_dict()["ready_sha256"],
                ready.challenge_id,
                ready.custody_id,
                ready.signer_key_id_sha256,
                ready.owner_scope_sha256,
                ready.destination_path_sha256,
            )
            self.state = ProtocolState.READY_RECEIVED
        elif frame_type == "FAILED" and self.state in {
            ProtocolState.HELLO_SENT,
            ProtocolState.AUTH_REQUEST_SENT,
            ProtocolState.CONFIRM_SENT,
            ProtocolState.CANCEL_SENT,
        }:
            self.state = ProtocolState.TERMINAL_RECEIVED
        elif transition == (ProtocolState.CONFIRM_SENT, "COMPLETED"):
            imported = PpkCustodyImportReceipt.from_dict(frame["import_receipt"])
            if self._confirmation_coordinates is None or (
                imported.ready_sha256,
                imported.confirmation_sha256,
            ) != self._confirmation_coordinates:
                self._protocol_failure()
            self.state = ProtocolState.TERMINAL_RECEIVED
        else:
            self._protocol_failure()

    def helper_exit(self, *, exit_code: int) -> None:
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            self._protocol_failure()
        if self.state is not ProtocolState.TERMINAL_RECEIVED or exit_code != 0:
            self._protocol_failure()
        self.state = ProtocolState.EXITED

    def _protocol_failure(self) -> None:
        self.state = ProtocolState.FAILED
        raise _fail()


__all__ = [
    "BoundedFrameReader",
    "MAX_FRAME_BYTES",
    "MAX_FRAMES_PER_DIRECTION",
    "PROTOCOL_VERSION",
    "PpkHelperProtocolState",
    "PpkProcessWireError",
    "ProtocolState",
    "decode_frame",
    "encode_frame",
    "validate_frame",
]
