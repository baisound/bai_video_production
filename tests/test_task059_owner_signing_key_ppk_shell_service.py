from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ai_video_production.owner_signing_key_custody import (
    OwnerSigningKeyCustodyReceipt,
)
from ai_video_production.owner_signing_key_ppk_native_adapter import (
    PpkNativeCandidateView,
    PpkNativeOperatorAdapter,
    PpkNativeOperatorError,
    PpkNativeReadyView,
)
from ai_video_production.owner_signing_key_ppk_shell_service import (
    OwnerSigningKeyPpkShellService,
)


FINGERPRINT = "SHA256:" + "A" * 43
OWNER_SCOPE = "sha256:" + "a" * 64
SIGNER_ID = "sha256:" + "b" * 64
DESTINATION = r"C:\\private\\owner-signing-key.json"


class AdapterStub(PpkNativeOperatorAdapter):
    def __init__(self) -> None:
        self.probe_code: str | None = None
        self.confirm_code: str | None = None
        self.closed = 0
        self.cancelled: str | None = None
        self.open_coordinates: tuple[str, str, str] | None = None
        self.candidate = PpkNativeCandidateView(
            candidate_id="task059-candidate",
            preflight_sha256="sha256:" + "c" * 64,
            ppk_file_sha256="sha256:" + "d" * 64,
            public_key_file_sha256="sha256:" + "e" * 64,
            signer_key_id_sha256=SIGNER_ID,
            openssh_sha256_fingerprint=FINGERPRINT,
            ppk_format_version=3,
            algorithm="ssh-ed25519",
            encryption="aes256-cbc",
            key_derivation="Argon2id",
        )
        self.ready = PpkNativeReadyView(
            attempt_id="task059-attempt",
            openssh_sha256_fingerprint=FINGERPRINT,
            expires_at_epoch_ms=1_777_500_120_000,
        )

    def probe_availability(self) -> None:
        if self.probe_code:
            raise PpkNativeOperatorError(self.probe_code)

    def choose_files(self, *, expected_openssh_sha256_fingerprint: str):
        assert expected_openssh_sha256_fingerprint == FINGERPRINT
        return self.candidate

    def confirm_public_identity(
        self, *, candidate_id: str, explicit_human_confirmation: bool
    ):
        assert (candidate_id, explicit_human_confirmation) == (
            self.candidate.candidate_id,
            True,
        )
        return self.candidate

    def open_secret_dialog(
        self, *, candidate_id: str, owner_scope_sha256: str, destination_path: str
    ):
        self.open_coordinates = (
            candidate_id,
            owner_scope_sha256,
            destination_path,
        )
        return self.ready

    def confirm_ready(
        self, *, attempt_id: str, explicit_human_confirmation: bool
    ):
        assert (attempt_id, explicit_human_confirmation) == (
            self.ready.attempt_id,
            True,
        )
        if self.confirm_code:
            raise PpkNativeOperatorError(self.confirm_code)
        import_receipt = SimpleNamespace(
            receipt_id="task059-import-receipt",
            signer_key_id_sha256=SIGNER_ID,
            imported_at_epoch_ms=1_777_500_100_000,
            to_dict=lambda: {"import_receipt_sha256": "sha256:" + "f" * 64},
        )
        custody_receipt = SimpleNamespace(
            custody_id="task029-custody",
            to_dict=lambda: {"custody_receipt_sha256": "sha256:" + "1" * 64},
        )
        return SimpleNamespace(
            receipt=import_receipt,
            custody_receipt=custody_receipt,
        )

    def cancel_candidate(self, *, candidate_id: str) -> None:
        self.cancelled = candidate_id

    def cancel_ready(self, *, attempt_id: str) -> None:
        self.cancelled = attempt_id

    def close(self) -> None:
        self.closed += 1


def _service(
    adapter: AdapterStub,
    *,
    readback=None,
    destination: str = DESTINATION,
) -> OwnerSigningKeyPpkShellService:
    return OwnerSigningKeyPpkShellService(
        adapter=adapter,
        expected_openssh_sha256_fingerprint=FINGERPRINT,
        owner_scope_sha256=OWNER_SCOPE,
        destination_path=destination,
        custody_readback=readback,
    )


def _to_ready(service: OwnerSigningKeyPpkShellService) -> None:
    selected = service.choose_files()
    candidate_id = selected["candidate"]["candidate_id"]
    service.confirm_public_identity(
        candidate_id=candidate_id,
        explicit_human_confirmation=True,
    )
    service.open_native_secret_dialog(candidate_id=candidate_id)


def test_shell_service_projects_body_free_five_step_operator_flow() -> None:
    adapter = AdapterStub()
    service = _service(adapter)

    idle = service.snapshot()
    assert idle["state"] == "IDLE_NOT_CONFIGURED"
    assert idle["recommended_action"] == "CHOOSE_FILES"

    selected = service.choose_files()
    assert selected["state"] == "FILES_SELECTED_PUBLIC_CANDIDATE"
    assert selected["candidate"]["openssh_sha256_fingerprint"] == FINGERPRINT
    candidate_id = selected["candidate"]["candidate_id"]

    confirmed = service.confirm_public_identity(
        candidate_id=candidate_id,
        explicit_human_confirmation=True,
    )
    assert confirmed["state"] == "PUBLIC_IDENTITY_CONFIRMED"

    ready = service.open_native_secret_dialog(candidate_id=candidate_id)
    assert ready["state"] == "READY_FOR_EXPLICIT_IMPORT"
    assert ready["ready"]["attempt_id"] == "task059-attempt"
    assert adapter.open_coordinates == (
        candidate_id,
        OWNER_SCOPE,
        DESTINATION,
    )

    completed = service.confirm_ready(
        attempt_id=ready["ready"]["attempt_id"],
        explicit_human_confirmation=True,
    )
    assert completed["state"] == "CUSTODIED_READBACK_VERIFIED"
    assert completed["success"]["signer_key_id_sha256"] == SIGNER_ID
    assert completed["success"]["import_receipt_sha256"] == "sha256:" + "f" * 64
    assert completed["success"]["custody_receipt_sha256"] == "sha256:" + "1" * 64
    assert completed["success"]["signing_started"] is False
    assert completed["success"]["deploy_started"] is False

    rendered = repr(completed)
    assert DESTINATION not in rendered
    assert "private-key" not in rendered
    assert completed["selected_paths_exposed"] is False
    assert completed["file_bodies_exposed"] is False
    assert completed["passphrase_exposed"] is False
    assert completed["custody_destination_path_exposed"] is False


def test_helper_unavailable_disables_card_before_file_selection() -> None:
    adapter = AdapterStub()
    adapter.probe_code = "ERR_PPK_PACKAGED_HELPER_UNAVAILABLE"
    service = _service(adapter)

    snapshot = service.snapshot()
    assert snapshot["available"] is False
    assert snapshot["state"] == "UNAVAILABLE_PACKAGED_HELPER"
    assert snapshot["recommended_action"] == "CHECK_APPLICATION_INSTALLATION"
    assert snapshot["candidate"] is None


def test_cancel_uses_only_opaque_coordinate_and_returns_to_idle() -> None:
    adapter = AdapterStub()
    service = _service(adapter)
    candidate_id = service.choose_files()["candidate"]["candidate_id"]

    cancelled = service.cancel(attempt_id=candidate_id)
    assert adapter.cancelled == candidate_id
    assert cancelled["state"] == "IDLE_NOT_CONFIGURED"


def test_result_lost_is_terminal_for_retry_and_recovers_only_from_readback() -> None:
    adapter = AdapterStub()
    adapter.confirm_code = "ERR_PPK_CUSTODY_RESULT_LOST_REQUIRES_READBACK"
    receipt = OwnerSigningKeyCustodyReceipt(
        receipt_id="task029-receipt",
        custody_id="task029-custody",
        owner_scope_sha256=OWNER_SCOPE,
        signer_key_id_sha256=SIGNER_ID,
        confirmation_sha256="sha256:" + "2" * 64,
        custodied_at_epoch_ms=1_777_500_100_000,
        cipher_suite="WINDOWS_DPAPI_CURRENT_USER_OWNER_SIGNING_KEY_V1",
    )
    observed: list[int] = []
    service = _service(
        adapter,
        readback=lambda: (observed.append(1), receipt if len(observed) > 1 else None)[1],
    )
    _to_ready(service)

    lost = service.confirm_ready(
        attempt_id="task059-attempt",
        explicit_human_confirmation=True,
    )
    assert lost["state"] == "READBACK_REQUIRED_NO_RETRY"
    assert lost["available"] is False
    assert lost["recommended_action"] == "READ_BACK_ONLY"

    blocked = service.choose_files()
    assert blocked["state"] == "CUSTODIED_READBACK_VERIFIED"
    assert blocked["success"]["recovered_by_readback"] is True
    assert blocked["success"]["import_receipt_sha256"] is None


def test_invalid_confirmation_never_opens_secret_dialog() -> None:
    adapter = AdapterStub()
    service = _service(adapter)
    candidate_id = service.choose_files()["candidate"]["candidate_id"]

    failed = service.confirm_public_identity(
        candidate_id=candidate_id,
        explicit_human_confirmation=False,
    )
    assert failed["state"] == "IDLE_NOT_CONFIGURED"
    assert failed["error_code"] == "ERR_PPK_NATIVE_PUBLIC_CONFIRMATION_REQUIRED"
    assert adapter.open_coordinates is None


def test_existing_destination_is_rejected_before_native_secret_dialog(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "owner-signing-key.json"
    destination.write_text("occupied", encoding="utf-8")
    adapter = AdapterStub()
    service = _service(adapter, destination=str(destination))
    candidate_id = service.choose_files()["candidate"]["candidate_id"]
    service.confirm_public_identity(
        candidate_id=candidate_id,
        explicit_human_confirmation=True,
    )

    rejected = service.open_native_secret_dialog(candidate_id=candidate_id)

    assert rejected["state"] == "IDLE_NOT_CONFIGURED"
    assert rejected["error_code"] == "ERR_PPK_CUSTODY_IMPORT_DESTINATION_EXISTS"
    assert adapter.open_coordinates is None
    assert Path(destination).read_text(encoding="utf-8") == "occupied"
