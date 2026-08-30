"""TASK-029 R9B Owner-local encrypted Ed25519 signing-key custody.

One explicitly confirmed raw Ed25519 seed may be encrypted at rest. Public APIs
return only a body-free receipt; signing, export, replacement, and rotation are
outside this unit.
"""
from __future__ import annotations
import base64, ctypes, json, os, re
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, runtime_checkable
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from .atomic import AtomicJsonWriter, AtomicWriteResult, FailureInjector, exclusive_file_update_lock
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes

STORE_SCHEMA_VERSION = CUSTODY_RECORD_VERSION = CUSTODY_RECEIPT_VERSION = "1.0.0"
DPAPI_CIPHER_SUITE = "WINDOWS_DPAPI_CURRENT_USER_OWNER_SIGNING_KEY_V1"
_DPAPI_ENTROPY = b"BAI_VIDEO_PRODUCTION\0TASK029_OWNER_SIGNING_KEY_CUSTODY\0V1"
_MAX_CIPHERTEXT_BYTES = 64 * 1024
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")

def _fail(code: str, message: str, category: ProductErrorCategory, **details: object) -> ProductError:
    return ProductError(code, message, category, details=dict(details))
def _id(value: object, field: str) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None: raise ValueError(f"{field} must be a stable identifier")
    return value
def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA.fullmatch(value) is None: raise ValueError(f"{field} must be a lowercase sha256 coordinate")
    return value
def _positive(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1: raise ValueError(f"{field} must be an integer >= 1")
    return value
def _public_from_seed(seed: bytes) -> bytes:
    if not isinstance(seed, bytes) or len(seed) != 32: raise ValueError("private_key_seed must contain exactly 32 bytes")
    return Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)

@runtime_checkable
class OwnerSigningKeyCipher(Protocol):
    cipher_suite: str
    def encrypt(self, plaintext: bytes) -> bytes: ...
    def decrypt(self, ciphertext: bytes) -> bytes: ...

class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]
def _blob(value: bytes) -> tuple[_DataBlob, object]:
    if value:
        buffer = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
        return _DataBlob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer
    return _DataBlob(0, ctypes.POINTER(ctypes.c_ubyte)()), None

class WindowsDpapiOwnerSigningKeyCipher:
    cipher_suite = DPAPI_CIPHER_SUITE
    def __init__(self) -> None:
        if os.name != "nt": raise _fail("ERR_OWNER_SIGNING_KEY_CUSTODY_ENCRYPTION_UNAVAILABLE", "Windows DPAPI is unavailable", ProductErrorCategory.NOT_SUPPORTED)
    @staticmethod
    def _crypt(value: bytes, *, protect: bool) -> bytes:
        in_blob, in_buffer = _blob(value); entropy_blob, entropy_buffer = _blob(_DPAPI_ENTROPY); out_blob = _DataBlob()
        crypt32 = ctypes.WinDLL("crypt32", use_last_error=True); kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]; kernel32.LocalFree.restype = ctypes.c_void_p
        fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
        fn.argtypes = [ctypes.POINTER(_DataBlob), ctypes.c_wchar_p, ctypes.POINTER(_DataBlob), ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_DataBlob)]
        fn.restype = wintypes.BOOL
        if not fn(ctypes.byref(in_blob), None, ctypes.byref(entropy_blob), None, None, 1, ctypes.byref(out_blob)): raise OSError(ctypes.get_last_error(), "DPAPI operation failed")
        try: return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            if out_blob.pbData: kernel32.LocalFree(ctypes.cast(out_blob.pbData, ctypes.c_void_p))
            _ = in_buffer, entropy_buffer
    def encrypt(self, plaintext: bytes) -> bytes: return self._crypt(plaintext, protect=True)
    def decrypt(self, ciphertext: bytes) -> bytes: return self._crypt(ciphertext, protect=False)

_FALSE_AUTH = ("private_key_export_authorized", "signing_authorized", "knowledge_pack_write_authorized", "automatic_promotion_authorized", "external_effect_authorized")
@dataclass(frozen=True, slots=True)
class OwnerSigningKeyCustodyConfirmation:
    confirmation_id: str; custody_id: str; owner_scope_sha256: str; signer_key_id_sha256: str; confirmed_at_epoch_ms: int
    def __post_init__(self) -> None:
        _id(self.confirmation_id, "confirmation_id"); _id(self.custody_id, "custody_id"); _sha(self.owner_scope_sha256, "owner_scope_sha256"); _sha(self.signer_key_id_sha256, "signer_key_id_sha256"); _positive(self.confirmed_at_epoch_ms, "confirmed_at_epoch_ms")
    def to_dict(self) -> dict[str, Any]:
        body = {"record_version": CUSTODY_RECORD_VERSION, "record_type": "OWNER_SIGNING_KEY_CUSTODY_CONFIRMATION", "task_owner": "TASK-029", "confirmation_id": self.confirmation_id, "custody_id": self.custody_id, "owner_scope_sha256": self.owner_scope_sha256, "signer_key_id_sha256": self.signer_key_id_sha256, "signature_algorithm": "ED25519", "confirmed_at_epoch_ms": self.confirmed_at_epoch_ms, "explicit_human_confirmation_received": True, "private_key_import_authorized_once": True, **{x: False for x in _FALSE_AUTH}}
        body["confirmation_sha256"] = sha256_bytes(canonical_json_bytes(body)); return body
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OwnerSigningKeyCustodyConfirmation":
        result = cls(value["confirmation_id"], value["custody_id"], value["owner_scope_sha256"], value["signer_key_id_sha256"], value["confirmed_at_epoch_ms"])
        if result.to_dict() != dict(value): raise ValueError("custody confirmation identity or hash mismatch")
        return result

def confirm_owner_signing_key_custody(*, confirmation_id: str, custody_id: str, owner_scope_sha256: str, signer_public_key: bytes, confirmed_at_epoch_ms: int, explicit_human_confirmation: bool) -> OwnerSigningKeyCustodyConfirmation:
    if explicit_human_confirmation is not True: raise _fail("ERR_OWNER_SIGNING_KEY_CUSTODY_CONFIRMATION_REQUIRED", "explicit Human confirmation is required", ProductErrorCategory.AUTHORIZATION)
    if not isinstance(signer_public_key, bytes) or len(signer_public_key) != 32: raise ValueError("signer_public_key must contain exactly 32 bytes")
    return OwnerSigningKeyCustodyConfirmation(confirmation_id, custody_id, owner_scope_sha256, sha256_bytes(signer_public_key), confirmed_at_epoch_ms)

@dataclass(frozen=True, slots=True)
class OwnerSigningKeyCustodyReceipt:
    receipt_id: str; custody_id: str; owner_scope_sha256: str; signer_key_id_sha256: str; confirmation_sha256: str; custodied_at_epoch_ms: int; cipher_suite: str
    def __post_init__(self) -> None:
        _id(self.receipt_id, "receipt_id"); _id(self.custody_id, "custody_id"); _sha(self.owner_scope_sha256, "owner_scope_sha256"); _sha(self.signer_key_id_sha256, "signer_key_id_sha256"); _sha(self.confirmation_sha256, "confirmation_sha256"); _positive(self.custodied_at_epoch_ms, "custodied_at_epoch_ms"); _id(self.cipher_suite, "cipher_suite")
    def to_dict(self) -> dict[str, Any]:
        body = {"receipt_version": CUSTODY_RECEIPT_VERSION, "record_type": "OWNER_SIGNING_KEY_CUSTODY_RECEIPT", "task_owner": "TASK-029", "receipt_id": self.receipt_id, "custody_id": self.custody_id, "owner_scope_sha256": self.owner_scope_sha256, "signer_key_id_sha256": self.signer_key_id_sha256, "confirmation_sha256": self.confirmation_sha256, "signature_algorithm": "ED25519", "custodied_at_epoch_ms": self.custodied_at_epoch_ms, "cipher_suite": self.cipher_suite, "state": "CUSTODIED", "encrypted_at_rest": True, "explicit_human_confirmation_received": True, "private_key_material_included": False, "public_key_material_included": False, **{x: False for x in _FALSE_AUTH}}
        body["custody_receipt_sha256"] = sha256_bytes(canonical_json_bytes(body)); return body
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OwnerSigningKeyCustodyReceipt":
        result = cls(value["receipt_id"], value["custody_id"], value["owner_scope_sha256"], value["signer_key_id_sha256"], value["confirmation_sha256"], value["custodied_at_epoch_ms"], value["cipher_suite"])
        if result.to_dict() != dict(value): raise ValueError("custody receipt identity or hash mismatch")
        return result

@dataclass(frozen=True, slots=True)
class _Secret:
    custody_id: str; owner_scope_sha256: str; signer_key_id_sha256: str
    private_key_seed: bytes; signer_public_key: bytes
    confirmation: OwnerSigningKeyCustodyConfirmation
    custodied_at_epoch_ms: int; receipt_id: str
    def validate(self) -> None:
        _id(self.custody_id, "custody_id"); _sha(self.owner_scope_sha256, "owner_scope_sha256"); _sha(self.signer_key_id_sha256, "signer_key_id_sha256"); _positive(self.custodied_at_epoch_ms, "custodied_at_epoch_ms"); _id(self.receipt_id, "receipt_id")
        if _public_from_seed(self.private_key_seed) != self.signer_public_key: raise ValueError("custodied Ed25519 key pair mismatch")
        if self.signer_key_id_sha256 != sha256_bytes(self.signer_public_key): raise ValueError("custodied signer key identifier mismatch")
        if (self.confirmation.custody_id, self.confirmation.owner_scope_sha256, self.confirmation.signer_key_id_sha256) != (self.custody_id, self.owner_scope_sha256, self.signer_key_id_sha256): raise ValueError("explicit Human confirmation does not match key custody")
    def to_dict(self) -> dict[str, Any]:
        self.validate()
        body = {"record_version": CUSTODY_RECORD_VERSION, "record_type": "OWNER_SIGNING_KEY_CUSTODY_SECRET", "task_owner": "TASK-029", "custody_id": self.custody_id, "owner_scope_sha256": self.owner_scope_sha256, "signer_key_id_sha256": self.signer_key_id_sha256, "signature_algorithm": "ED25519", "private_key_seed_b64": base64.b64encode(self.private_key_seed).decode("ascii"), "signer_public_key_b64": base64.b64encode(self.signer_public_key).decode("ascii"), "confirmation": self.confirmation.to_dict(), "custodied_at_epoch_ms": self.custodied_at_epoch_ms, "receipt_id": self.receipt_id, **{x: False for x in _FALSE_AUTH}}
        body["secret_record_sha256"] = sha256_bytes(canonical_json_bytes(body)); return body
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "_Secret":
        body = {k: v for k, v in value.items() if k != "secret_record_sha256"}
        if value.get("secret_record_sha256") != sha256_bytes(canonical_json_bytes(body)): raise ValueError("custodied signing key hash mismatch")
        if (value.get("record_version"), value.get("record_type"), value.get("task_owner"), value.get("signature_algorithm")) != (CUSTODY_RECORD_VERSION, "OWNER_SIGNING_KEY_CUSTODY_SECRET", "TASK-029", "ED25519"): raise ValueError("custodied signing key identity mismatch")
        if any(value.get(x) is not False for x in _FALSE_AUTH): raise ValueError("custodied signing key authority mismatch")
        secret = cls(value["custody_id"], value["owner_scope_sha256"], value["signer_key_id_sha256"], base64.b64decode(value["private_key_seed_b64"], validate=True), base64.b64decode(value["signer_public_key_b64"], validate=True), OwnerSigningKeyCustodyConfirmation.from_dict(value["confirmation"]), value["custodied_at_epoch_ms"], value["receipt_id"])
        secret.validate(); return secret

@dataclass(frozen=True, slots=True)
class OwnerSigningKeyCustodySaveResult:
    receipt: OwnerSigningKeyCustodyReceipt
    write: AtomicWriteResult

class OwnerSigningKeyCustodyStore:
    def __init__(self, path: str | Path, cipher: OwnerSigningKeyCipher | None = None) -> None:
        self.path = Path(path); self.cipher = cipher if cipher is not None else WindowsDpapiOwnerSigningKeyCipher()
        if not isinstance(self.cipher, OwnerSigningKeyCipher): raise ValueError("cipher does not implement OwnerSigningKeyCipher")
        _id(self.cipher.cipher_suite, "cipher_suite")
    def _envelope(self, secret: _Secret) -> dict[str, Any]:
        ciphertext = self.cipher.encrypt(canonical_json_bytes(secret.to_dict()))
        if not ciphertext or len(ciphertext) > _MAX_CIPHERTEXT_BYTES: raise ValueError("ciphertext size is invalid")
        body = {"schema_version": STORE_SCHEMA_VERSION, "record_type": "OWNER_SIGNING_KEY_CUSTODY_STORE_ENCRYPTED", "task_owner": "TASK-029", "cipher_suite": self.cipher.cipher_suite, "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"), "ciphertext_sha256": sha256_bytes(ciphertext), "plaintext_fields_present": False}
        body["document_sha256"] = sha256_bytes(canonical_json_bytes(body)); return body
    def _parse_envelope(self, value: Mapping[str, Any]) -> _Secret:
        expected = {"schema_version", "record_type", "task_owner", "cipher_suite", "ciphertext_b64", "ciphertext_sha256", "plaintext_fields_present", "document_sha256"}
        if not isinstance(value, Mapping) or set(value) != expected: raise ValueError("encrypted custody fields are incomplete or unknown")
        if (value["schema_version"], value["record_type"], value["task_owner"]) != (STORE_SCHEMA_VERSION, "OWNER_SIGNING_KEY_CUSTODY_STORE_ENCRYPTED", "TASK-029"): raise ValueError("encrypted custody identity mismatch")
        if value["cipher_suite"] != self.cipher.cipher_suite or value["plaintext_fields_present"] is not False: raise ValueError("custody cipher or plaintext boundary mismatch")
        body = {k: v for k, v in value.items() if k != "document_sha256"}
        if value["document_sha256"] != sha256_bytes(canonical_json_bytes(body)): raise ValueError("encrypted custody document checksum mismatch")
        ciphertext = base64.b64decode(value["ciphertext_b64"], validate=True)
        if not ciphertext or len(ciphertext) > _MAX_CIPHERTEXT_BYTES or value["ciphertext_sha256"] != sha256_bytes(ciphertext): raise ValueError("encrypted custody ciphertext checksum mismatch")
        decrypted = json.loads(self.cipher.decrypt(ciphertext).decode("utf-8"))
        if not isinstance(decrypted, dict): raise ValueError("decrypted custody secret must be an object")
        return _Secret.from_dict(decrypted)
    def _load_secret(self) -> _Secret:
        try:
            if self.path.is_symlink() or not self.path.is_file(): raise ValueError("custody store must be a regular non-symlink file")
            document = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(document, dict): raise ValueError("encrypted custody store must be an object")
            return self._parse_envelope(document)
        except ProductError: raise
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise _fail("ERR_OWNER_SIGNING_KEY_CUSTODY_INTEGRITY", "Owner signing key custody could not be decrypted and verified safely", ProductErrorCategory.DATA_INTEGRITY, reason=type(exc).__name__) from exc
    def _receipt(self, secret: _Secret) -> OwnerSigningKeyCustodyReceipt:
        return OwnerSigningKeyCustodyReceipt(secret.receipt_id, secret.custody_id, secret.owner_scope_sha256, secret.signer_key_id_sha256, secret.confirmation.to_dict()["confirmation_sha256"], secret.custodied_at_epoch_ms, self.cipher.cipher_suite)
    def read_receipt(self) -> OwnerSigningKeyCustodyReceipt:
        return self._receipt(self._load_secret())
    def _sign_exact_message(self, *, message: bytes, expected_receipt: OwnerSigningKeyCustodyReceipt) -> tuple[bytes, bytes]:
        """R9C internal boundary: sign without exporting the custodied seed."""
        if not isinstance(message, bytes) or not message: raise ValueError("message must be non-empty bytes")
        if not isinstance(expected_receipt, OwnerSigningKeyCustodyReceipt): raise ValueError("expected_receipt must be an OwnerSigningKeyCustodyReceipt")
        with exclusive_file_update_lock(self.path):
            secret = self._load_secret()
            if self._receipt(secret) != expected_receipt: raise _fail("ERR_OWNER_SIGNING_KEY_CUSTODY_DRIFT", "Owner signing key custody changed before signing", ProductErrorCategory.DATA_INTEGRITY)
            return secret.signer_public_key, Ed25519PrivateKey.from_private_bytes(secret.private_key_seed).sign(message)
    def provision(self, *, receipt_id: str, custody_id: str, owner_scope_sha256: str, private_key_seed: bytes, confirmation: OwnerSigningKeyCustodyConfirmation, custodied_at_epoch_ms: int, failure_injector: FailureInjector | None = None) -> OwnerSigningKeyCustodySaveResult:
        public = _public_from_seed(private_key_seed)
        secret = _Secret(custody_id, owner_scope_sha256, sha256_bytes(public), private_key_seed, public, confirmation, custodied_at_epoch_ms, receipt_id)
        secret.validate()
        with exclusive_file_update_lock(self.path):
            if self.path.is_symlink(): raise _fail("ERR_OWNER_SIGNING_KEY_CUSTODY_INTEGRITY", "Owner signing key custody path is a symlink", ProductErrorCategory.DATA_INTEGRITY)
            if self.path.exists(): raise _fail("ERR_OWNER_SIGNING_KEY_CUSTODY_ALREADY_EXISTS", "Owner signing key custody is one-shot and cannot be overwritten", ProductErrorCategory.STATE)
            envelope = self._envelope(secret)
            write = AtomicJsonWriter.write(self.path, envelope, validator=lambda value: self._parse_envelope(value), failure_injector=failure_injector)
        return OwnerSigningKeyCustodySaveResult(self._receipt(secret), write)

__all__ = ["CUSTODY_RECEIPT_VERSION", "CUSTODY_RECORD_VERSION", "DPAPI_CIPHER_SUITE", "OwnerSigningKeyCipher", "OwnerSigningKeyCustodyConfirmation", "OwnerSigningKeyCustodyReceipt", "OwnerSigningKeyCustodySaveResult", "OwnerSigningKeyCustodyStore", "STORE_SCHEMA_VERSION", "WindowsDpapiOwnerSigningKeyCipher", "confirm_owner_signing_key_custody"]
