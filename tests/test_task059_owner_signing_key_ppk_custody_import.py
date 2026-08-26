from __future__ import annotations

import base64
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from ai_video_production.errors import ProductError, ProductErrorCategory
from ai_video_production.owner_signing_key_custody import (
    OwnerSigningKeyCustodyReceipt,
    OwnerSigningKeyCustodyStore,
)
from ai_video_production.owner_signing_key_ppk_custody_import import (
    MAX_READY_WINDOW_MS,
    PpkCustodyImportConfirmation,
    PpkCustodyImportReady,
    PpkCustodyImportReceipt,
    confirm_ppk_custody_import,
    custody_destination_path_sha256,
    execute_ppk_custody_import,
    prepare_ppk_custody_import_ready,
)
from ai_video_production.owner_signing_key_ppk_secret_auth import (
    _AuthenticatedPpkSecret,
)
from ai_video_production.serialization import sha256_bytes


SEED = bytes(range(1, 33))
READY_AT = 1_777_200_000_000
EXPIRES_AT = READY_AT + 120_000
CONFIRMED_AT = READY_AT + 1_000
IMPORTED_AT = READY_AT + 2_000
OWNER_SCOPE = sha256_bytes(b"task059-owner-scope")
PREFLIGHT = sha256_bytes(b"task059-preflight")
PPK_FILE = sha256_bytes(b"task059-ppk-file")


def _public(seed: bytes = SEED) -> bytes:
    return (
        Ed25519PrivateKey.from_private_bytes(seed)
        .public_key()
        .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    )


def _fingerprint(seed: bytes = SEED) -> str:
    public_blob = (
        len(b"ssh-ed25519").to_bytes(4, "big")
        + b"ssh-ed25519"
        + len(_public(seed)).to_bytes(4, "big")
        + _public(seed)
    )
    digest = hashlib.sha256(public_blob).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


def _secret(seed: bytes = SEED) -> _AuthenticatedPpkSecret:
    return _AuthenticatedPpkSecret(
        _private_key_seed=bytearray(seed),
        preflight_sha256=PREFLIGHT,
        ppk_file_sha256=PPK_FILE,
        signer_key_id_sha256=sha256_bytes(_public(seed)),
        openssh_sha256_fingerprint=_fingerprint(seed),
    )


class _FakeCipher:
    cipher_suite = "TASK059_TEST_FAKE_CIPHER_V1"

    def encrypt(self, plaintext: bytes) -> bytes:
        return b"task059:" + plaintext[::-1]

    def decrypt(self, ciphertext: bytes) -> bytes:
        if not ciphertext.startswith(b"task059:"):
            raise ValueError("fake ciphertext is invalid")
        return ciphertext[len(b"task059:") :][::-1]


def _store(path: Path) -> OwnerSigningKeyCustodyStore:
    return OwnerSigningKeyCustodyStore(path, cipher=_FakeCipher())


def _ready(secret: _AuthenticatedPpkSecret, path: Path) -> PpkCustodyImportReady:
    return prepare_ppk_custody_import_ready(
        secret=secret,
        session_id="task059-session-001",
        challenge_id="task059-challenge-001",
        custody_id="task059-custody-001",
        owner_scope_sha256=OWNER_SCOPE,
        destination_path=path,
        ready_at_epoch_ms=READY_AT,
        expires_at_epoch_ms=EXPIRES_AT,
    )


def _confirmation(ready: PpkCustodyImportReady) -> PpkCustodyImportConfirmation:
    return confirm_ppk_custody_import(
        confirmation_id="task059-confirmation-001",
        ready_payload=ready.to_dict(),
        confirmed_at_epoch_ms=CONFIRMED_AT,
        explicit_human_confirmation=True,
    )


def _execute(
    *,
    secret: _AuthenticatedPpkSecret,
    store: OwnerSigningKeyCustodyStore,
    ready: PpkCustodyImportReady,
    confirmation: PpkCustodyImportConfirmation,
):
    return execute_ppk_custody_import(
        receipt_id="task059-import-receipt-001",
        custody_receipt_id="task029-custody-receipt-task059-001",
        r9b_confirmation_id="task029-custody-confirmation-task059-001",
        secret=secret,
        custody_store=store,
        ready_payload=ready.to_dict(),
        confirmation_payload=confirmation.to_dict(),
        imported_at_epoch_ms=IMPORTED_AT,
    )


def test_ready_is_body_free_and_does_not_consume_secret(tmp_path: Path) -> None:
    secret = _secret()
    path = tmp_path / "owner-signing-key-custody.json"
    ready = _ready(secret, path)
    payload = ready.to_dict()

    assert PpkCustodyImportReady.from_dict(payload) == ready
    assert payload["state"] == "READY_FOR_EXPLICIT_HUMAN_CUSTODY_IMPORT"
    assert payload["ppk_mac_verified"] is True
    assert payload["explicit_human_confirmation_received"] is False
    assert payload["custody_import_authorized"] is False
    assert secret.cleared is False
    rendered = json.dumps(payload)
    assert str(path) not in rendered
    assert base64.b64encode(SEED).decode("ascii") not in rendered


def test_confirmation_requires_direct_human_action_and_live_window(tmp_path: Path) -> None:
    ready = _ready(_secret(), tmp_path / "custody.json")
    with pytest.raises(ProductError) as missing:
        confirm_ppk_custody_import(
            confirmation_id="task059-confirmation-001",
            ready_payload=ready.to_dict(),
            confirmed_at_epoch_ms=CONFIRMED_AT,
            explicit_human_confirmation=False,
        )
    assert missing.value.code == "ERR_PPK_CUSTODY_IMPORT_CONFIRMATION_REQUIRED"
    assert missing.value.category is ProductErrorCategory.AUTHORIZATION

    with pytest.raises(ProductError) as expired:
        confirm_ppk_custody_import(
            confirmation_id="task059-confirmation-001",
            ready_payload=ready.to_dict(),
            confirmed_at_epoch_ms=EXPIRES_AT + 1,
            explicit_human_confirmation=True,
        )
    assert expired.value.code == "ERR_PPK_CUSTODY_IMPORT_CONFIRMATION_EXPIRED"


def test_exact_confirmation_and_r9b_provision_complete_once(tmp_path: Path) -> None:
    secret = _secret()
    path = tmp_path / "custody.json"
    store = _store(path)
    ready = _ready(secret, path)
    confirmation = _confirmation(ready)
    result = _execute(
        secret=secret,
        store=store,
        ready=ready,
        confirmation=confirmation,
    )

    assert path.is_file()
    assert secret.cleared is True
    assert store.read_receipt() == result.custody_receipt
    assert PpkCustodyImportReceipt.from_dict(result.receipt.to_dict()) == result.receipt
    payload = result.receipt.to_dict()
    assert payload["state"] == "CUSTODIED_AND_READBACK_VERIFIED"
    assert payload["custody_readback_verified"] is True
    assert payload["signing_authorized"] is False
    assert payload["knowledge_pack_write_authorized"] is False
    assert payload["release_authorized"] is False
    rendered = json.dumps(payload)
    assert str(path) not in rendered
    assert base64.b64encode(SEED).decode("ascii") not in rendered
    assert result.custody_receipt.signer_key_id_sha256 == sha256_bytes(_public())

    with pytest.raises(ValueError, match="active authenticated"):
        _execute(
            secret=secret,
            store=store,
            ready=ready,
            confirmation=confirmation,
        )


def test_ready_or_confirmation_tamper_is_rejected_before_seed_consumption(
    tmp_path: Path,
) -> None:
    secret = _secret()
    ready = _ready(secret, tmp_path / "custody.json")
    confirmation = _confirmation(ready).to_dict()
    confirmation["challenge_id"] = "task059-challenge-tampered"
    with pytest.raises(ValueError, match="canonical"):
        execute_ppk_custody_import(
            receipt_id="task059-import-receipt-001",
            custody_receipt_id="task029-custody-receipt-task059-001",
            r9b_confirmation_id="task029-custody-confirmation-task059-001",
            secret=secret,
            custody_store=_store(tmp_path / "custody.json"),
            ready_payload=ready.to_dict(),
            confirmation_payload=confirmation,
            imported_at_epoch_ms=IMPORTED_AT,
        )
    assert secret.cleared is False


def test_destination_drift_is_rejected_before_seed_consumption(tmp_path: Path) -> None:
    secret = _secret()
    ready = _ready(secret, tmp_path / "expected.json")
    confirmation = _confirmation(ready)
    with pytest.raises(ProductError) as caught:
        _execute(
            secret=secret,
            store=_store(tmp_path / "different.json"),
            ready=ready,
            confirmation=confirmation,
        )
    assert caught.value.code == "ERR_PPK_CUSTODY_IMPORT_DRIFT"
    assert secret.cleared is False


def test_existing_destination_is_preserved_and_secret_cannot_auto_retry(
    tmp_path: Path,
) -> None:
    secret = _secret()
    path = tmp_path / "custody.json"
    ready = _ready(secret, path)
    confirmation = _confirmation(ready)
    path.write_text("existing", encoding="utf-8")
    with pytest.raises(ProductError) as caught:
        _execute(
            secret=secret,
            store=_store(path),
            ready=ready,
            confirmation=confirmation,
        )
    assert caught.value.code == "ERR_PPK_CUSTODY_IMPORT_DESTINATION_EXISTS"
    assert path.read_text(encoding="utf-8") == "existing"
    assert secret.cleared is False


def test_ready_window_and_record_tamper_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="expiry"):
        prepare_ppk_custody_import_ready(
            secret=_secret(),
            session_id="task059-session-001",
            challenge_id="task059-challenge-001",
            custody_id="task059-custody-001",
            owner_scope_sha256=OWNER_SCOPE,
            destination_path=tmp_path / "custody.json",
            ready_at_epoch_ms=READY_AT,
            expires_at_epoch_ms=READY_AT + MAX_READY_WINDOW_MS + 1,
        )
    ready_payload = _ready(_secret(), tmp_path / "custody.json").to_dict()
    ready_payload["custody_import_authorized"] = True
    with pytest.raises(ValueError, match="canonical"):
        PpkCustodyImportReady.from_dict(ready_payload)


def test_path_coordinate_is_stable_without_exposing_path(tmp_path: Path) -> None:
    path = tmp_path / "folder" / ".." / "custody.json"
    assert custody_destination_path_sha256(path) == custody_destination_path_sha256(
        Path(path)
    )
    assert str(tmp_path) not in custody_destination_path_sha256(path)


def test_confirmation_and_receipt_unknown_fields_or_authority_tamper_reject(
    tmp_path: Path,
) -> None:
    ready = _ready(_secret(), tmp_path / "custody.json")
    confirmation = _confirmation(ready).to_dict()
    assert confirmation["private_key_export_authorized"] is False
    confirmation["signing_authorized"] = True
    with pytest.raises(ValueError, match="canonical"):
        PpkCustodyImportConfirmation.from_dict(confirmation)

    receipt = PpkCustodyImportReceipt(
        receipt_id="task059-import-receipt-001",
        ready_sha256=ready.to_dict()["ready_sha256"],
        confirmation_sha256=_confirmation(ready).to_dict()["confirmation_sha256"],
        custody_receipt_sha256=sha256_bytes(b"custody-receipt"),
        preflight_sha256=PREFLIGHT,
        ppk_file_sha256=PPK_FILE,
        signer_key_id_sha256=sha256_bytes(_public()),
        owner_scope_sha256=OWNER_SCOPE,
        destination_path_sha256=ready.destination_path_sha256,
        imported_at_epoch_ms=IMPORTED_AT,
    ).to_dict()
    receipt["private_key_seed_b64"] = "forbidden"
    with pytest.raises(ValueError, match="canonical"):
        PpkCustodyImportReceipt.from_dict(receipt)


class _ReadbackDriftStore(OwnerSigningKeyCustodyStore):
    def __init__(self, path: Path) -> None:
        super().__init__(path, cipher=_FakeCipher())
        self._reads = 0

    def read_receipt(self) -> OwnerSigningKeyCustodyReceipt:
        value = super().read_receipt()
        self._reads += 1
        if self._reads == 1:
            return replace(value, receipt_id="task029-drifted-receipt")
        return value


def test_readback_drift_fails_after_canonical_custody_without_retry(tmp_path: Path) -> None:
    secret = _secret()
    store = _ReadbackDriftStore(tmp_path / "custody.json")
    ready = _ready(secret, store.path)
    with pytest.raises(ProductError) as caught:
        _execute(
            secret=secret,
            store=store,
            ready=ready,
            confirmation=_confirmation(ready),
        )
    assert caught.value.code == "ERR_PPK_CUSTODY_IMPORT_READBACK"
    assert store.path.is_file()
    assert secret.cleared is True
    assert store.read_receipt().custody_id == ready.custody_id
