"""TASK-059 P1C-I body-free unified Shell projection and coordinator.

The WebView sees only public identity, opaque coordinates, fixed status/error
codes and receipt digests. File paths, file bodies, passphrases and the custody
destination stay inside the Python/native adapter boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Callable

from .owner_signing_key_custody import OwnerSigningKeyCustodyReceipt
from .owner_signing_key_ppk_custody_import import PpkCustodyImportResult
from .owner_signing_key_ppk_native_adapter import (
    PpkNativeCandidateView,
    PpkNativeOperatorAdapter,
    PpkNativeOperatorError,
    PpkNativeReadyView,
)


_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_FINGERPRINT = re.compile(r"^SHA256:[A-Za-z0-9+/]{43}$")
_RESULT_LOST = "ERR_PPK_CUSTODY_RESULT_LOST_REQUIRES_READBACK"
_DESTINATION_DISPLAY = "Windowsユーザー専用の暗号化保管領域"

_ERROR_MESSAGES_JA = {
    "ERR_PPK_PACKAGED_HELPER_UNAVAILABLE": (
        "署名鍵取込helperを安全に確認できません。アプリ構成を確認してください。"
    ),
    "ERR_PPK_NATIVE_DIALOG_UNAVAILABLE": (
        "ファイル選択画面を開けませんでした。もう一度やり直してください。"
    ),
    "ERR_PPK_NATIVE_FILE_SELECTION_INVALID": (
        "選択したファイルを安全に読み取れません。PPKと公開鍵を確認してください。"
    ),
    "ERR_PPK_NATIVE_PUBLIC_PREFLIGHT_FAILED": (
        "公開鍵の照合に失敗しました。正しい組合せを選択してください。"
    ),
    "ERR_PPK_NATIVE_PUBLIC_CONFIRMATION_REQUIRED": (
        "公開fingerprintの明示確認が必要です。"
    ),
    "ERR_PPK_NATIVE_SECRET_DIALOG_UNAVAILABLE": (
        "安全なパスフレーズ入力画面を開けませんでした。"
    ),
    "ERR_PPK_NATIVE_SECRET_INPUT_INVALID": (
        "パスフレーズ入力を安全に受け取れませんでした。"
    ),
    "ERR_PPK_NATIVE_FILE_IDENTITY_CHANGED": (
        "確認後にファイルが変化しました。最初から選択し直してください。"
    ),
    "ERR_PPK_CUSTODY_IMPORT_DESTINATION_EXISTS": (
        "署名鍵はすでに保管されています。上書きは行いません。"
    ),
    "ERR_PPK_CUSTODY_IMPORT_CONFIRMATION_REQUIRED": (
        "one-shot取込の明示確認が必要です。"
    ),
    _RESULT_LOST: (
        "取込結果を受信できませんでした。再試行せず、正本のread-backだけを行います。"
    ),
}


@dataclass(frozen=True, slots=True)
class _SuccessView:
    receipt_id: str
    custody_id: str
    signer_key_id_sha256: str
    import_receipt_sha256: str | None
    custody_receipt_sha256: str
    custodied_at_epoch_ms: int
    recovered_by_readback: bool

    def to_dict(self) -> dict[str, object]:
        return {
            **{name: getattr(self, name) for name in self.__dataclass_fields__},
            "state": "CUSTODIED_READBACK_VERIFIED",
            "private_key_material_included": False,
            "public_key_material_included": False,
            "signing_started": False,
            "publication_started": False,
            "promotion_started": False,
            "release_started": False,
            "deploy_started": False,
        }


class OwnerSigningKeyPpkShellService:
    """Stateful one-attempt coordinator for the canonical Settings card."""

    def __init__(
        self,
        *,
        adapter: PpkNativeOperatorAdapter,
        expected_openssh_sha256_fingerprint: str,
        owner_scope_sha256: str,
        destination_path: str,
        custody_readback: Callable[[], OwnerSigningKeyCustodyReceipt | None]
        | None = None,
    ) -> None:
        if not isinstance(adapter, PpkNativeOperatorAdapter):
            raise ValueError("adapter must be a PpkNativeOperatorAdapter")
        if _FINGERPRINT.fullmatch(expected_openssh_sha256_fingerprint) is None:
            raise ValueError("expected fingerprint is invalid")
        if _SHA256.fullmatch(owner_scope_sha256) is None:
            raise ValueError("owner scope digest is invalid")
        if (
            not isinstance(destination_path, str)
            or not destination_path
            or any(character in destination_path for character in ("\x00", "\r", "\n"))
        ):
            raise ValueError("destination path is invalid")
        if custody_readback is not None and not callable(custody_readback):
            raise ValueError("custody readback must be callable")

        self._adapter = adapter
        self._expected_fingerprint = expected_openssh_sha256_fingerprint
        self._owner_scope_sha256 = owner_scope_sha256
        self._destination_path = destination_path
        self._custody_readback = custody_readback
        self._state = "IDLE_NOT_CONFIGURED"
        self._candidate: PpkNativeCandidateView | None = None
        self._ready: PpkNativeReadyView | None = None
        self._success: _SuccessView | None = None
        self._error_code: str | None = None
        self._signer_key_id_sha256: str | None = None

    def __repr__(self) -> str:
        return f"OwnerSigningKeyPpkShellService(state={self._state!r})"

    def snapshot(self) -> dict[str, object]:
        if self._state == "READBACK_REQUIRED_NO_RETRY":
            self._attempt_readback()
        available = self._state not in {
            "UNAVAILABLE_PACKAGED_HELPER",
            "READBACK_REQUIRED_NO_RETRY",
        }
        if self._state == "IDLE_NOT_CONFIGURED":
            try:
                self._adapter.probe_availability()
            except PpkNativeOperatorError as exc:
                self._set_error(exc.code, unavailable=True)
                available = False
        return {
            "available": available,
            "task_owner": "TASK-059",
            "state": self._state,
            "status_label_ja": self._status_label(),
            "recommended_action": self._recommended_action(),
            "destination_display": _DESTINATION_DISPLAY,
            "candidate": self._candidate.to_ui_dict() if self._candidate else None,
            "ready": self._ready.to_ui_dict() if self._ready else None,
            "success": self._success.to_dict() if self._success else None,
            "error_code": self._error_code,
            "error_message_ja": (
                _ERROR_MESSAGES_JA.get(
                    self._error_code,
                    "署名鍵取込を安全に続行できません。最初からやり直してください。",
                )
                if self._error_code
                else None
            ),
            "selected_paths_exposed": False,
            "file_bodies_exposed": False,
            "passphrase_exposed": False,
            "custody_destination_path_exposed": False,
            "one_shot_no_overwrite": True,
            "signing_authorized": False,
            "publication_authorized": False,
            "promotion_authorized": False,
            "release_authorized": False,
            "deploy_authorized": False,
        }

    def choose_files(self) -> dict[str, object]:
        if self._state != "IDLE_NOT_CONFIGURED":
            return self._invalid_state()
        try:
            candidate = self._adapter.choose_files(
                expected_openssh_sha256_fingerprint=self._expected_fingerprint
            )
            if candidate is None:
                self._reset_view()
            else:
                self._candidate = candidate
                self._signer_key_id_sha256 = candidate.signer_key_id_sha256
                self._state = "FILES_SELECTED_PUBLIC_CANDIDATE"
                self._error_code = None
        except PpkNativeOperatorError as exc:
            self._set_error(
                exc.code,
                unavailable=(exc.code == "ERR_PPK_PACKAGED_HELPER_UNAVAILABLE"),
            )
        return self.snapshot()

    def confirm_public_identity(
        self, *, candidate_id: str, explicit_human_confirmation: bool
    ) -> dict[str, object]:
        if explicit_human_confirmation is not True:
            return self._fixed_failure("ERR_PPK_NATIVE_PUBLIC_CONFIRMATION_REQUIRED")
        try:
            self._candidate = self._adapter.confirm_public_identity(
                candidate_id=candidate_id,
                explicit_human_confirmation=True,
            )
            self._state = "PUBLIC_IDENTITY_CONFIRMED"
            self._error_code = None
        except PpkNativeOperatorError as exc:
            self._set_error(exc.code)
        return self.snapshot()

    def open_native_secret_dialog(self, *, candidate_id: str) -> dict[str, object]:
        if self._state != "PUBLIC_IDENTITY_CONFIRMED":
            return self._invalid_state()
        if os.path.lexists(self._destination_path):
            self._set_error("ERR_PPK_CUSTODY_IMPORT_DESTINATION_EXISTS")
            return self.snapshot()
        try:
            ready = self._adapter.open_secret_dialog(
                candidate_id=candidate_id,
                owner_scope_sha256=self._owner_scope_sha256,
                destination_path=self._destination_path,
            )
            self._candidate = None
            if ready is None:
                self._reset_view()
            else:
                self._ready = ready
                self._state = "READY_FOR_EXPLICIT_IMPORT"
                self._error_code = None
        except PpkNativeOperatorError as exc:
            self._set_error(exc.code)
        return self.snapshot()

    def confirm_ready(
        self, *, attempt_id: str, explicit_human_confirmation: bool
    ) -> dict[str, object]:
        if explicit_human_confirmation is not True:
            return self._fixed_failure("ERR_PPK_CUSTODY_IMPORT_CONFIRMATION_REQUIRED")
        if self._state != "READY_FOR_EXPLICIT_IMPORT":
            return self._invalid_state()
        try:
            result = self._adapter.confirm_ready(
                attempt_id=attempt_id,
                explicit_human_confirmation=True,
            )
            self._ready = None
            self._success = self._success_from_result(result)
            self._state = "CUSTODIED_READBACK_VERIFIED"
            self._error_code = None
        except PpkNativeOperatorError as exc:
            self._set_error(exc.code)
        return self.snapshot()

    def cancel(self, *, attempt_id: str) -> dict[str, object]:
        try:
            if self._candidate is not None and attempt_id == self._candidate.candidate_id:
                self._adapter.cancel_candidate(candidate_id=attempt_id)
            elif self._ready is not None and attempt_id == self._ready.attempt_id:
                self._adapter.cancel_ready(attempt_id=attempt_id)
            else:
                return self._invalid_state()
            self._reset_view()
        except PpkNativeOperatorError as exc:
            self._set_error(exc.code)
        return self.snapshot()

    def close(self) -> None:
        self._adapter.close()
        if self._state != "CUSTODIED_READBACK_VERIFIED":
            self._reset_view()

    def _fixed_failure(self, code: str) -> dict[str, object]:
        self._set_error(code)
        return self.snapshot()

    def _invalid_state(self) -> dict[str, object]:
        if self._state == "READBACK_REQUIRED_NO_RETRY":
            return self.snapshot()
        self._set_error("ERR_PPK_NATIVE_STATE_INVALID")
        return self.snapshot()

    def _set_error(self, code: str, *, unavailable: bool = False) -> None:
        self._error_code = code
        self._candidate = None
        self._ready = None
        try:
            self._adapter.close()
        except Exception:
            pass
        if code == _RESULT_LOST:
            self._state = "READBACK_REQUIRED_NO_RETRY"
        elif unavailable:
            self._state = "UNAVAILABLE_PACKAGED_HELPER"
        else:
            self._state = "IDLE_NOT_CONFIGURED"

    def _reset_view(self) -> None:
        self._state = "IDLE_NOT_CONFIGURED"
        self._candidate = None
        self._ready = None
        self._success = None
        self._error_code = None
        self._signer_key_id_sha256 = None

    def _attempt_readback(self) -> None:
        if self._custody_readback is None or self._signer_key_id_sha256 is None:
            return
        try:
            receipt = self._custody_readback()
        except Exception:
            return
        if receipt is None:
            return
        if (
            receipt.owner_scope_sha256 != self._owner_scope_sha256
            or receipt.signer_key_id_sha256 != self._signer_key_id_sha256
        ):
            self._error_code = "ERR_PPK_CUSTODY_READBACK_CONFLICT"
            return
        payload = receipt.to_dict()
        self._success = _SuccessView(
            receipt_id=receipt.receipt_id,
            custody_id=receipt.custody_id,
            signer_key_id_sha256=receipt.signer_key_id_sha256,
            import_receipt_sha256=None,
            custody_receipt_sha256=str(payload["custody_receipt_sha256"]),
            custodied_at_epoch_ms=receipt.custodied_at_epoch_ms,
            recovered_by_readback=True,
        )
        self._state = "CUSTODIED_READBACK_VERIFIED"
        self._error_code = None

    @staticmethod
    def _success_from_result(result: PpkCustodyImportResult) -> _SuccessView:
        imported = result.receipt.to_dict()
        custody = result.custody_receipt.to_dict()
        return _SuccessView(
            receipt_id=result.receipt.receipt_id,
            custody_id=result.custody_receipt.custody_id,
            signer_key_id_sha256=result.receipt.signer_key_id_sha256,
            import_receipt_sha256=str(imported["import_receipt_sha256"]),
            custody_receipt_sha256=str(custody["custody_receipt_sha256"]),
            custodied_at_epoch_ms=result.receipt.imported_at_epoch_ms,
            recovered_by_readback=False,
        )

    def _status_label(self) -> str:
        return {
            "IDLE_NOT_CONFIGURED": "未設定",
            "UNAVAILABLE_PACKAGED_HELPER": "利用不可",
            "FILES_SELECTED_PUBLIC_CANDIDATE": "公開鍵を確認してください",
            "PUBLIC_IDENTITY_CONFIRMED": "パスフレーズ入力待ち",
            "READY_FOR_EXPLICIT_IMPORT": "取込の最終確認待ち",
            "READBACK_REQUIRED_NO_RETRY": "正本のread-backが必要",
            "CUSTODIED_READBACK_VERIFIED": "安全な保管を確認済み",
        }.get(self._state, "確認が必要")

    def _recommended_action(self) -> str:
        return {
            "IDLE_NOT_CONFIGURED": "CHOOSE_FILES",
            "UNAVAILABLE_PACKAGED_HELPER": "CHECK_APPLICATION_INSTALLATION",
            "FILES_SELECTED_PUBLIC_CANDIDATE": "CONFIRM_PUBLIC_IDENTITY",
            "PUBLIC_IDENTITY_CONFIRMED": "OPEN_NATIVE_SECRET_DIALOG",
            "READY_FOR_EXPLICIT_IMPORT": "CONFIRM_ONE_SHOT_IMPORT",
            "READBACK_REQUIRED_NO_RETRY": "READ_BACK_ONLY",
            "CUSTODIED_READBACK_VERIFIED": "NONE",
        }.get(self._state, "NONE")


__all__ = ["OwnerSigningKeyPpkShellService"]
