"""TASK-059 P1C-E parent-side one-attempt PPK import session.

This module owns the transient parent orchestration and Operator READY
projection. It does not own PPK cryptography, custody, signing, persistence,
or a GUI toolkit.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import os
import secrets
import time
from typing import Any, Callable, Mapping

from .errors import ProductError
from .owner_signing_key_ppk_custody_import import (
    PpkCustodyImportReady,
    PpkCustodyImportReceipt,
    PpkCustodyImportResult,
    RECORD_VERSION as READY_RECORD_VERSION,
    confirm_ppk_custody_import,
    custody_destination_path_sha256,
)
from .owner_signing_key_custody import OwnerSigningKeyCustodyReceipt
from .owner_signing_key_ppk_preflight import (
    SCHEMA_VERSION as PREFLIGHT_SCHEMA_VERSION,
    admit_ppk_import_preflight,
)
from .owner_signing_key_ppk_process_controller import (
    PpkHelperLaunchSpec,
    PpkHelperProcessController,
    PpkHelperProcessError,
)
from .owner_signing_key_ppk_process_wire import (
    PROTOCOL_VERSION,
    PpkHelperProtocolState,
    PpkProcessWireError,
)


class PpkImportOperatorError(RuntimeError):
    """Body-free parent error carrying only a fixed code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)

    def __repr__(self) -> str:
        return f"PpkImportOperatorError(code={self.code!r})"


@dataclass(frozen=True, slots=True, repr=False)
class PpkImportOperatorReadyView:
    """Transient UI projection. Destination plaintext must never be persisted."""

    openssh_sha256_fingerprint: str
    destination_path: str
    expires_at_epoch_ms: int
    state: str = "READY_FOR_EXPLICIT_HUMAN_CUSTODY_IMPORT"
    title: str = "\u7f72\u540d\u9375\u3092\u5b89\u5168\u306b\u53d6\u308a\u8fbc\u3080"
    consequence_text: str = (
        "\u3053\u306e\u64cd\u4f5c\u306f1\u56de\u9650\u308a\u3067\u3001\u65e2\u5b58\u306e\u7f72\u540d\u9375\u306f\u4e0a\u66f8\u304d\u3057\u307e\u305b\u3093\u3002"
    )
    import_label: str = "\u5185\u5bb9\u3092\u78ba\u8a8d\u3057\u3066\u53d6\u308a\u8fbc\u3080"
    cancel_label: str = "\u30ad\u30e3\u30f3\u30bb\u30eb"

    def __repr__(self) -> str:
        return (
            "PpkImportOperatorReadyView("
            f"state={self.state!r}, fingerprint={self.openssh_sha256_fingerprint!r}, "
            "destination_path='<redacted>')"
        )


def _clear(value: bytearray) -> None:
    for index in range(len(value)):
        value[index] = 0


class PpkImportOperatorSession:
    """Drive one helper process without retaining secret-bearing frames."""

    def __init__(
        self,
        *,
        helper_spec: PpkHelperLaunchSpec,
        controller_factory: Callable[[], PpkHelperProcessController] = (
            PpkHelperProcessController
        ),
        epoch_ms: Callable[[], int] = lambda: time.time_ns() // 1_000_000,
        identity: Callable[[str], str] = lambda kind: (
            f"task059-{kind}-{secrets.token_hex(16)}"
        ),
    ) -> None:
        self._helper_spec = helper_spec
        self._controller_factory = controller_factory
        self._epoch_ms = epoch_ms
        self._identity = identity
        self._controller: PpkHelperProcessController | None = None
        self._wire: PpkHelperProtocolState | None = None
        self._ready: PpkCustodyImportReady | None = None
        self._terminal = False
        self._started = False

    def begin(
        self,
        *,
        preflight_payload: Mapping[str, Any],
        ppk_document: bytearray,
        rfc4716_public_key: bytearray,
        passphrase_utf8: bytearray,
        owner_scope_sha256: str,
        destination_path: str,
    ) -> PpkImportOperatorReadyView:
        if self._started:
            raise PpkImportOperatorError("ERR_PPK_OPERATOR_SESSION_ALREADY_STARTED")
        self._started = True
        buffers = (ppk_document, rfc4716_public_key, passphrase_utf8)
        if any(not isinstance(value, bytearray) for value in buffers):
            for value in buffers:
                if isinstance(value, bytearray):
                    _clear(value)
            raise PpkImportOperatorError("ERR_PPK_OPERATOR_INPUT_INVALID")
        if any(not value for value in buffers):
            for value in buffers:
                _clear(value)
            raise PpkImportOperatorError("ERR_PPK_OPERATOR_INPUT_INVALID")
        if not isinstance(destination_path, str) or not os.path.isabs(destination_path):
            for value in buffers:
                _clear(value)
            raise PpkImportOperatorError("ERR_PPK_OPERATOR_INPUT_INVALID")

        try:
            destination = bytearray(destination_path.encode("utf-8", errors="strict"))
        except UnicodeError:
            for value in buffers:
                _clear(value)
            raise PpkImportOperatorError("ERR_PPK_OPERATOR_INPUT_INVALID") from None
        succeeded = False
        try:
            session_id = self._safe_identity("session")
            preflight = admit_ppk_import_preflight(preflight_payload)
            controller = self._controller_factory()
            wire = PpkHelperProtocolState(session_id=session_id)
            self._controller = controller
            self._wire = wire
            controller.start(self._helper_spec)

            hello = self._frame(
                session_id,
                "HELLO",
                capability_coordinates={
                    "preflight_schema_version": PREFLIGHT_SCHEMA_VERSION,
                    "ready_record_version": READY_RECORD_VERSION,
                },
            )
            wire.parent_send(hello)
            controller.send_frame(hello)
            accepted = controller.receive_frame()
            wire.helper_send(accepted)
            if accepted["frame_type"] == "FAILED":
                self._raise_helper_failure(accepted)

            auth = self._frame(
                session_id,
                "AUTH_REQUEST",
                preflight=dict(preflight_payload),
                ppk_document_b64=base64.b64encode(ppk_document).decode("ascii"),
                rfc4716_public_key_b64=base64.b64encode(
                    rfc4716_public_key
                ).decode("ascii"),
                passphrase_utf8_b64=base64.b64encode(passphrase_utf8).decode("ascii"),
                custody_request={
                    "owner_scope_sha256": owner_scope_sha256,
                    "destination_path_utf8_b64": base64.b64encode(destination).decode(
                        "ascii"
                    ),
                },
            )
            wire.parent_send(auth)
            controller.send_frame(auth)
            del auth
            response = controller.receive_frame()
            wire.helper_send(response)
            if response["frame_type"] == "FAILED":
                self._raise_helper_failure(response)
            ready = PpkCustodyImportReady.from_dict(response["ready"])
            self._ready = ready
            if (
                ready.preflight_sha256 != preflight.to_dict()["preflight_sha256"]
                or ready.ppk_file_sha256 != preflight.ppk_file_sha256
                or ready.signer_key_id_sha256 != preflight.signer_key_id_sha256
                or ready.openssh_sha256_fingerprint
                != preflight.openssh_sha256_fingerprint
                or ready.owner_scope_sha256 != owner_scope_sha256
                or ready.destination_path_sha256
                != custody_destination_path_sha256(destination_path)
            ):
                raise PpkProcessWireError("ERR_PPK_HELPER_PROTOCOL")
            succeeded = True
            return PpkImportOperatorReadyView(
                openssh_sha256_fingerprint=ready.openssh_sha256_fingerprint,
                destination_path=destination_path,
                expires_at_epoch_ms=ready.expires_at_epoch_ms,
            )
        except PpkImportOperatorError:
            raise
        except PpkHelperProcessError as exc:
            raise PpkImportOperatorError(exc.code) from None
        except PpkProcessWireError:
            raise PpkImportOperatorError("ERR_PPK_HELPER_PROTOCOL") from None
        except ProductError as exc:
            raise PpkImportOperatorError(exc.code) from None
        except Exception:
            raise PpkImportOperatorError("ERR_PPK_OPERATOR_SESSION_FAILED") from None
        finally:
            for value in buffers:
                _clear(value)
            _clear(destination)
            if not succeeded:
                self._abort()

    def confirm(self, *, explicit_human_confirmation: bool) -> PpkCustodyImportResult:
        ready, controller, wire = self._require_ready()
        if explicit_human_confirmation is not True:
            raise PpkImportOperatorError("ERR_PPK_CUSTODY_IMPORT_CONFIRMATION_REQUIRED")
        try:
            confirmation = confirm_ppk_custody_import(
                confirmation_id=self._safe_identity("confirmation"),
                ready_payload=ready.to_dict(),
                confirmed_at_epoch_ms=self._safe_epoch_ms(),
                explicit_human_confirmation=True,
            )
            frame = self._frame(
                ready.session_id,
                "CONFIRM",
                confirmation=confirmation.to_dict(),
            )
            wire.parent_send(frame)
            controller.send_frame(frame)
            response = controller.receive_frame()
            wire.helper_send(response)
            if response["frame_type"] == "FAILED":
                self._raise_helper_failure(response)
            result = PpkCustodyImportResult(
                receipt=PpkCustodyImportReceipt.from_dict(response["import_receipt"]),
                custody_receipt=OwnerSigningKeyCustodyReceipt.from_dict(
                    response["custody_receipt"]
                ),
            )
            controller.finish()
            wire.helper_exit(exit_code=0)
            self._complete()
            return result
        except PpkImportOperatorError:
            raise
        except PpkHelperProcessError as exc:
            self._abort()
            raise PpkImportOperatorError(exc.code) from None
        except PpkProcessWireError:
            self._abort()
            raise PpkImportOperatorError("ERR_PPK_HELPER_PROTOCOL") from None
        except ProductError as exc:
            self._abort()
            raise PpkImportOperatorError(exc.code) from None
        except Exception:
            self._abort()
            raise PpkImportOperatorError("ERR_PPK_OPERATOR_SESSION_FAILED") from None

    def cancel(self) -> None:
        ready, controller, wire = self._require_ready()
        try:
            frame = self._frame(
                ready.session_id,
                "CANCEL",
                reason_code="OWNER_CANCELLED",
            )
            wire.parent_send(frame)
            controller.send_frame(frame)
            response = controller.receive_frame()
            wire.helper_send(response)
            if response["frame_type"] != "FAILED" or response["error_code"] != (
                "ERR_PPK_HELPER_CANCELLED"
            ):
                raise PpkProcessWireError("ERR_PPK_HELPER_PROTOCOL")
            controller.finish()
            wire.helper_exit(exit_code=0)
            self._complete()
        except PpkHelperProcessError as exc:
            self._abort()
            raise PpkImportOperatorError(exc.code) from None
        except PpkProcessWireError:
            self._abort()
            raise PpkImportOperatorError("ERR_PPK_HELPER_PROTOCOL") from None
        except Exception:
            self._abort()
            raise PpkImportOperatorError("ERR_PPK_OPERATOR_SESSION_FAILED") from None

    def close(self) -> None:
        self._abort()

    def _raise_helper_failure(self, frame: Mapping[str, Any]) -> None:
        code = frame["error_code"]
        self._abort()
        raise PpkImportOperatorError(code)

    def _require_ready(
        self,
    ) -> tuple[
        PpkCustodyImportReady,
        PpkHelperProcessController,
        PpkHelperProtocolState,
    ]:
        if (
            self._terminal
            or self._ready is None
            or self._controller is None
            or self._wire is None
        ):
            raise PpkImportOperatorError("ERR_PPK_OPERATOR_SESSION_NOT_READY")
        return self._ready, self._controller, self._wire

    def _complete(self) -> None:
        self._terminal = True
        self._controller = None
        self._wire = None
        self._ready = None

    def _abort(self) -> None:
        controller = self._controller
        if controller is not None:
            try:
                controller.abort()
            except Exception:
                pass
        self._complete()

    def _safe_epoch_ms(self) -> int:
        value = self._epoch_ms()
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise PpkImportOperatorError("ERR_PPK_OPERATOR_SESSION_FAILED")
        return value

    def _safe_identity(self, kind: str) -> str:
        value = self._identity(kind)
        if not isinstance(value, str) or not value:
            raise PpkImportOperatorError("ERR_PPK_OPERATOR_SESSION_FAILED")
        return value

    @staticmethod
    def _frame(session_id: str, frame_type: str, **payload: object) -> dict[str, Any]:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "frame_type": frame_type,
            "session_id": session_id,
            **payload,
        }


__all__ = [
    "PpkImportOperatorError",
    "PpkImportOperatorReadyView",
    "PpkImportOperatorSession",
]
