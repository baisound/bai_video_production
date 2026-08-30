"""TASK-059 P1B body-free PPK-to-R9B custody import contract.

This module binds an already authenticated helper-local P1A secret to one
explicit Human confirmation and the canonical TASK-029 R9B one-shot store.
It does not sign, export, promote, release, or apply a runtime profile.
"""

from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import os
import re
from typing import Any, Mapping

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .errors import ProductError, ProductErrorCategory
from .owner_signing_key_custody import (
    OwnerSigningKeyCustodyReceipt,
    OwnerSigningKeyCustodyStore,
    confirm_owner_signing_key_custody,
)
from .owner_signing_key_ppk_secret_auth import _AuthenticatedPpkSecret
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


RECORD_VERSION = "1.0.0"
MAX_READY_WINDOW_MS = 5 * 60 * 1000
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_FINGERPRINT = re.compile(r"^SHA256:[A-Za-z0-9+/]{43}$")
_FALSE_AUTHORITY = (
    "private_key_export_authorized",
    "signing_authorized",
    "knowledge_pack_write_authorized",
    "knowledge_pack_promotion_authorized",
    "runtime_profile_apply_authorized",
    "release_authorized",
    "deploy_authorized",
    "production_authorized",
    "external_effect_authorized",
)


def _id(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a stable identifier")
    return value


def _sha(value: object, field_name: str) -> str:
    return validate_sha256(value, field_name=field_name)


def _time(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} must be a positive epoch millisecond")
    return value


def _fingerprint(value: object) -> str:
    if not isinstance(value, str) or _FINGERPRINT.fullmatch(value) is None:
        raise ValueError("openssh_sha256_fingerprint is invalid")
    return value


def custody_destination_path_sha256(path: str | os.PathLike[str]) -> str:
    canonical = os.path.normcase(os.path.abspath(os.fspath(path)))
    return sha256_bytes(canonical.encode("utf-8"))


def _body_with_sha(body: dict[str, object], field_name: str) -> dict[str, object]:
    return {**body, field_name: sha256_bytes(canonical_json_bytes(body))}




@dataclass(frozen=True, slots=True)
class PpkCustodyImportReady:
    session_id: str
    challenge_id: str
    custody_id: str
    preflight_sha256: str
    ppk_file_sha256: str
    signer_key_id_sha256: str
    openssh_sha256_fingerprint: str
    owner_scope_sha256: str
    destination_path_sha256: str
    ready_at_epoch_ms: int
    expires_at_epoch_ms: int

    def __post_init__(self) -> None:
        for field in ("session_id", "challenge_id", "custody_id"):
            _id(getattr(self, field), field)
        for field in (
            "preflight_sha256",
            "ppk_file_sha256",
            "signer_key_id_sha256",
            "owner_scope_sha256",
            "destination_path_sha256",
        ):
            _sha(getattr(self, field), field)
        _fingerprint(self.openssh_sha256_fingerprint)
        _time(self.ready_at_epoch_ms, "ready_at_epoch_ms")
        _time(self.expires_at_epoch_ms, "expires_at_epoch_ms")
        if not 1 <= self.expires_at_epoch_ms - self.ready_at_epoch_ms <= MAX_READY_WINDOW_MS:
            raise ValueError("PPK custody import READY expiry is outside bounds")

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "record_version": RECORD_VERSION,
            "record_type": "OWNER_SIGNING_KEY_PPK_CUSTODY_IMPORT_READY",
            "task_owner": "TASK-059",
            **{field: getattr(self, field) for field in self.__dataclass_fields__},
            "state": "READY_FOR_EXPLICIT_HUMAN_CUSTODY_IMPORT",
            "ppk_mac_verified": True,
            "public_key_rederived": True,
            "explicit_human_confirmation_received": False,
            "custody_import_authorized": False,
            "custody_import_started": False,
            **{field: False for field in _FALSE_AUTHORITY},
        }
        return _body_with_sha(body, "ready_sha256")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PpkCustodyImportReady":
        if not isinstance(value, Mapping):
            raise ValueError("PPK custody import READY must be a mapping")
        fields = cls.__dataclass_fields__
        result = cls(**{field: value[field] for field in fields})
        if result.to_dict() != dict(value):
            raise ValueError("PPK custody import READY is not exact canonical form")
        return result


def prepare_ppk_custody_import_ready(
    *,
    secret: _AuthenticatedPpkSecret,
    session_id: str,
    challenge_id: str,
    custody_id: str,
    owner_scope_sha256: str,
    destination_path: str | os.PathLike[str],
    ready_at_epoch_ms: int,
    expires_at_epoch_ms: int,
) -> PpkCustodyImportReady:
    if not isinstance(secret, _AuthenticatedPpkSecret) or secret.cleared:
        raise ValueError("an active authenticated PPK secret is required")
    if not os.path.isabs(os.fspath(destination_path)):
        raise ValueError("PPK custody destination path must be absolute")
    if os.path.lexists(destination_path):
        raise ProductError(
            "ERR_PPK_CUSTODY_IMPORT_DESTINATION_EXISTS",
            "PPK custody destination already exists before READY",
            ProductErrorCategory.STATE,
        )
    return PpkCustodyImportReady(
        session_id=session_id,
        challenge_id=challenge_id,
        custody_id=custody_id,
        preflight_sha256=secret.preflight_sha256,
        ppk_file_sha256=secret.ppk_file_sha256,
        signer_key_id_sha256=secret.signer_key_id_sha256,
        openssh_sha256_fingerprint=secret.openssh_sha256_fingerprint,
        owner_scope_sha256=owner_scope_sha256,
        destination_path_sha256=custody_destination_path_sha256(destination_path),
        ready_at_epoch_ms=ready_at_epoch_ms,
        expires_at_epoch_ms=expires_at_epoch_ms,
    )


@dataclass(frozen=True, slots=True)
class PpkCustodyImportConfirmation:
    confirmation_id: str
    session_id: str
    challenge_id: str
    ready_sha256: str
    custody_id: str
    signer_key_id_sha256: str
    owner_scope_sha256: str
    destination_path_sha256: str
    confirmed_at_epoch_ms: int

    def __post_init__(self) -> None:
        for field in ("confirmation_id", "session_id", "challenge_id", "custody_id"):
            _id(getattr(self, field), field)
        for field in (
            "ready_sha256",
            "signer_key_id_sha256",
            "owner_scope_sha256",
            "destination_path_sha256",
        ):
            _sha(getattr(self, field), field)
        _time(self.confirmed_at_epoch_ms, "confirmed_at_epoch_ms")

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "record_version": RECORD_VERSION,
            "record_type": "OWNER_SIGNING_KEY_PPK_CUSTODY_IMPORT_CONFIRMATION",
            "task_owner": "TASK-059",
            **{field: getattr(self, field) for field in self.__dataclass_fields__},
            "explicit_human_confirmation_received": True,
            "private_key_import_authorized_once": True,
            **{field: False for field in _FALSE_AUTHORITY},
        }
        return _body_with_sha(body, "confirmation_sha256")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PpkCustodyImportConfirmation":
        if not isinstance(value, Mapping):
            raise ValueError("PPK custody import confirmation must be a mapping")
        result = cls(**{field: value[field] for field in cls.__dataclass_fields__})
        if result.to_dict() != dict(value):
            raise ValueError("PPK custody import confirmation is not exact canonical form")
        return result


def confirm_ppk_custody_import(
    *,
    confirmation_id: str,
    ready_payload: Mapping[str, Any],
    confirmed_at_epoch_ms: int,
    explicit_human_confirmation: bool,
) -> PpkCustodyImportConfirmation:
    if explicit_human_confirmation is not True:
        raise ProductError(
            "ERR_PPK_CUSTODY_IMPORT_CONFIRMATION_REQUIRED",
            "Explicit Human confirmation is required for PPK custody import",
            ProductErrorCategory.AUTHORIZATION,
        )
    ready = PpkCustodyImportReady.from_dict(ready_payload)
    if not ready.ready_at_epoch_ms <= confirmed_at_epoch_ms <= ready.expires_at_epoch_ms:
        raise ProductError(
            "ERR_PPK_CUSTODY_IMPORT_CONFIRMATION_EXPIRED",
            "PPK custody import confirmation is outside the READY window",
            ProductErrorCategory.AUTHORIZATION,
        )
    return PpkCustodyImportConfirmation(
        confirmation_id=confirmation_id,
        session_id=ready.session_id,
        challenge_id=ready.challenge_id,
        ready_sha256=ready.to_dict()["ready_sha256"],
        custody_id=ready.custody_id,
        signer_key_id_sha256=ready.signer_key_id_sha256,
        owner_scope_sha256=ready.owner_scope_sha256,
        destination_path_sha256=ready.destination_path_sha256,
        confirmed_at_epoch_ms=confirmed_at_epoch_ms,
    )


@dataclass(frozen=True, slots=True)
class PpkCustodyImportReceipt:
    receipt_id: str
    ready_sha256: str
    confirmation_sha256: str
    custody_receipt_sha256: str
    preflight_sha256: str
    ppk_file_sha256: str
    signer_key_id_sha256: str
    owner_scope_sha256: str
    destination_path_sha256: str
    imported_at_epoch_ms: int

    def __post_init__(self) -> None:
        _id(self.receipt_id, "receipt_id")
        for field in (
            "ready_sha256",
            "confirmation_sha256",
            "custody_receipt_sha256",
            "preflight_sha256",
            "ppk_file_sha256",
            "signer_key_id_sha256",
            "owner_scope_sha256",
            "destination_path_sha256",
        ):
            _sha(getattr(self, field), field)
        _time(self.imported_at_epoch_ms, "imported_at_epoch_ms")

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "record_version": RECORD_VERSION,
            "record_type": "OWNER_SIGNING_KEY_PPK_CUSTODY_IMPORT_RECEIPT",
            "task_owner": "TASK-059",
            **{field: getattr(self, field) for field in self.__dataclass_fields__},
            "state": "CUSTODIED_AND_READBACK_VERIFIED",
            "ppk_mac_verified": True,
            "public_key_rederived": True,
            "explicit_human_confirmation_received": True,
            "custody_import_completed": True,
            "custody_readback_verified": True,
            "private_key_material_included": False,
            "public_key_material_included": False,
            **{field: False for field in _FALSE_AUTHORITY},
        }
        return _body_with_sha(body, "import_receipt_sha256")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PpkCustodyImportReceipt":
        if not isinstance(value, Mapping):
            raise ValueError("PPK custody import receipt must be a mapping")
        result = cls(**{field: value[field] for field in cls.__dataclass_fields__})
        if result.to_dict() != dict(value):
            raise ValueError("PPK custody import receipt is not exact canonical form")
        return result


@dataclass(frozen=True, slots=True)
class PpkCustodyImportResult:
    receipt: PpkCustodyImportReceipt
    custody_receipt: OwnerSigningKeyCustodyReceipt


def execute_ppk_custody_import(
    *,
    receipt_id: str,
    custody_receipt_id: str,
    r9b_confirmation_id: str,
    secret: _AuthenticatedPpkSecret,
    custody_store: OwnerSigningKeyCustodyStore,
    ready_payload: Mapping[str, Any],
    confirmation_payload: Mapping[str, Any],
    imported_at_epoch_ms: int,
) -> PpkCustodyImportResult:
    ready = PpkCustodyImportReady.from_dict(ready_payload)
    confirmation = PpkCustodyImportConfirmation.from_dict(confirmation_payload)
    expected_confirmation = confirm_ppk_custody_import(
        confirmation_id=confirmation.confirmation_id,
        ready_payload=ready_payload,
        confirmed_at_epoch_ms=confirmation.confirmed_at_epoch_ms,
        explicit_human_confirmation=True,
    )
    if confirmation != expected_confirmation:
        raise ValueError("PPK custody import confirmation does not match READY")
    if not confirmation.confirmed_at_epoch_ms <= imported_at_epoch_ms <= ready.expires_at_epoch_ms:
        raise ValueError("PPK custody import completion is outside the confirmed READY window")
    if not isinstance(secret, _AuthenticatedPpkSecret) or secret.cleared:
        raise ValueError("an active authenticated PPK secret is required")
    if (
        secret.preflight_sha256 != ready.preflight_sha256
        or secret.ppk_file_sha256 != ready.ppk_file_sha256
        or secret.signer_key_id_sha256 != ready.signer_key_id_sha256
        or secret.openssh_sha256_fingerprint != ready.openssh_sha256_fingerprint
        or custody_destination_path_sha256(custody_store.path)
        != ready.destination_path_sha256
    ):
        raise ProductError(
            "ERR_PPK_CUSTODY_IMPORT_DRIFT",
            "PPK custody import coordinates changed after confirmation",
            ProductErrorCategory.DATA_INTEGRITY,
        )

    if os.path.lexists(custody_store.path):
        raise ProductError(
            "ERR_PPK_CUSTODY_IMPORT_DESTINATION_EXISTS",
            "PPK custody destination appeared after confirmation",
            ProductErrorCategory.STATE,
        )

    private_seed = secret._consume_seed_for_r9b_once()
    try:
        public = (
            Ed25519PrivateKey.from_private_bytes(private_seed)
            .public_key()
            .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        )
        if sha256_bytes(public) != ready.signer_key_id_sha256:
            raise ProductError(
                "ERR_PPK_CUSTODY_IMPORT_DRIFT",
                "Authenticated PPK key changed before R9B provision",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        r9b_confirmation = confirm_owner_signing_key_custody(
            confirmation_id=r9b_confirmation_id,
            custody_id=ready.custody_id,
            owner_scope_sha256=ready.owner_scope_sha256,
            signer_public_key=public,
            confirmed_at_epoch_ms=confirmation.confirmed_at_epoch_ms,
            explicit_human_confirmation=True,
        )
        save = custody_store.provision(
            receipt_id=custody_receipt_id,
            custody_id=ready.custody_id,
            owner_scope_sha256=ready.owner_scope_sha256,
            private_key_seed=private_seed,
            confirmation=r9b_confirmation,
            custodied_at_epoch_ms=imported_at_epoch_ms,
        )
        readback = custody_store.read_receipt()
        if readback != save.receipt:
            raise ProductError(
                "ERR_PPK_CUSTODY_IMPORT_READBACK",
                "R9B custody receipt read-back did not match",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        receipt = PpkCustodyImportReceipt(
            receipt_id=receipt_id,
            ready_sha256=ready.to_dict()["ready_sha256"],
            confirmation_sha256=confirmation.to_dict()["confirmation_sha256"],
            custody_receipt_sha256=readback.to_dict()["custody_receipt_sha256"],
            preflight_sha256=ready.preflight_sha256,
            ppk_file_sha256=ready.ppk_file_sha256,
            signer_key_id_sha256=ready.signer_key_id_sha256,
            owner_scope_sha256=ready.owner_scope_sha256,
            destination_path_sha256=ready.destination_path_sha256,
            imported_at_epoch_ms=imported_at_epoch_ms,
        )
        return PpkCustodyImportResult(receipt=receipt, custody_receipt=readback)
    finally:
        del private_seed


__all__ = [
    "MAX_READY_WINDOW_MS",
    "PpkCustodyImportConfirmation",
    "PpkCustodyImportReady",
    "PpkCustodyImportReceipt",
    "PpkCustodyImportResult",
    "confirm_ppk_custody_import",
    "custody_destination_path_sha256",
    "execute_ppk_custody_import",
    "prepare_ppk_custody_import_ready",
]
