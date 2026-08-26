"""TASK-029 R10D encrypted Owner-local signature-artifact custody.

The store accepts only an exact R10C candidate, transient Ed25519 public-key
and detached-signature bytes, and an explicit Human confirmation.  It
recompiles R10B and R10C at the write boundary, encrypts the artifact bodies,
and returns a body-free receipt.  It never accepts or stores a private key.
"""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping, Protocol, runtime_checkable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .atomic import (
    AtomicJsonWriter,
    AtomicWriteResult,
    FailureInjector,
    exclusive_file_update_lock,
)
from .errors import ProductError, ProductErrorCategory
from .knowledge_pack_signature_artifact_custody_candidate import (
    SignatureArtifactCustodyCandidate,
    compile_signature_artifact_custody_candidate,
)
from .knowledge_pack_trusted_signature_admission import (
    KnowledgePackTrustedSignatureAdmission,
    compile_knowledge_pack_trusted_signature_admission,
)
from .serialization import canonical_json_bytes, sha256_bytes


SIGNATURE_ARTIFACT_CUSTODY_RECEIPT_VERSION = "1.0.0"
SIGNATURE_ARTIFACT_CUSTODY_RECORD_VERSION = "1.0.0"
SIGNATURE_ARTIFACT_CUSTODY_STORE_SCHEMA_VERSION = "1.0.0"
SIGNATURE_ARTIFACT_CUSTODY_CONTRACT = (
    "TASK-029/SIGNATURE_ARTIFACT_CUSTODY_STORE/1.0.0"
)
SIGNATURE_ARTIFACT_DPAPI_CIPHER_SUITE = (
    "WINDOWS_DPAPI_CURRENT_USER_SIGNATURE_ARTIFACT_CUSTODY_V1"
)
SIGNATURE_ARTIFACT_PATH_SECURITY_MODEL = (
    "COOPERATIVE_PROTECTED_LOCAL_WRITER_ONLY"
)
_DPAPI_ENTROPY = (
    b"BAI_VIDEO_PRODUCTION\0TASK029_SIGNATURE_ARTIFACT_CUSTODY\0V1"
)
_MAX_CIPHERTEXT_BYTES = 512 * 1024
_MAX_DEPTH = 24
_MAX_NODES = 16384
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_LOGICAL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")
_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")


def _fail(
    code: str,
    message: str,
    category: ProductErrorCategory,
    **details: object,
) -> ProductError:
    return ProductError(code, message, category, details=dict(details))


def _id(value: object, field: str) -> str:
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise ValueError(f"{field} must be an exact stable identifier")
    return value


def _logical_id(value: object, field: str) -> str:
    if type(value) is not str or _LOGICAL_ID.fullmatch(value) is None:
        raise ValueError(f"{field} must be an exact path-free logical identifier")
    return value


def _sha(value: object, field: str) -> str:
    if type(value) is not str or _SHA.fullmatch(value) is None:
        raise ValueError(f"{field} must be an exact lowercase SHA-256 coordinate")
    return value


def _positive(value: object, field: str) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{field} must be an exact positive integer")
    return value


def _exact_bytes(value: object, field: str, size: int) -> bytes:
    if type(value) is not bytes or len(value) != size:
        raise ValueError(f"{field} must contain exactly {size} bytes")
    return value


def _snapshot_json_object(value: object, field: str) -> dict[str, Any]:
    """Return one bounded hook-free JSON snapshot or reject before hook reads."""

    if type(value) is not dict:
        raise ValueError(f"{field} must be an exact built-in object")
    nodes = 0

    def visit(item: object, path: str, depth: int) -> Any:
        nonlocal nodes
        nodes += 1
        if nodes > _MAX_NODES:
            raise ValueError(f"{field} exceeds the node limit")
        if depth > _MAX_DEPTH:
            raise ValueError(f"{field} exceeds the depth limit")
        if item is None or type(item) in (str, int, bool):
            return item
        if type(item) is list:
            return [visit(child, f"{path}[]", depth + 1) for child in item]
        if type(item) is dict:
            result: dict[str, Any] = {}
            for key, child in item.items():
                if type(key) is not str:
                    raise ValueError(f"{path} keys must be exact strings")
                result[key] = visit(child, f"{path}.{key}", depth + 1)
            return result
        raise ValueError(f"{path} contains a non-JSON or derived value")

    return visit(value, field, 0)


@runtime_checkable
class SignatureArtifactCustodyCipher(Protocol):
    cipher_suite: str

    def encrypt(self, plaintext: bytes) -> bytes: ...

    def decrypt(self, ciphertext: bytes) -> bytes: ...


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _blob(value: bytes) -> tuple[_DataBlob, object]:
    if value:
        buffer = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
        return (
            _DataBlob(
                len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
            ),
            buffer,
        )
    return _DataBlob(0, ctypes.POINTER(ctypes.c_ubyte)()), None


class WindowsDpapiSignatureArtifactCustodyCipher:
    """Windows Current User DPAPI with an R10D-specific entropy domain."""

    cipher_suite = SIGNATURE_ARTIFACT_DPAPI_CIPHER_SUITE

    def __init__(self) -> None:
        if os.name != "nt":
            raise _fail(
                "ERR_SIGNATURE_ARTIFACT_CUSTODY_ENCRYPTION_UNAVAILABLE",
                "Windows DPAPI signature-artifact custody is unavailable",
                ProductErrorCategory.NOT_SUPPORTED,
            )

    @staticmethod
    def _crypt(value: bytes, *, protect: bool) -> bytes:
        if type(value) is not bytes or not value:
            raise ValueError("DPAPI input must be exact non-empty bytes")
        in_blob, in_buffer = _blob(value)
        entropy_blob, entropy_buffer = _blob(_DPAPI_ENTROPY)
        out_blob = _DataBlob()
        crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        function = (
            crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
        )
        function.argtypes = [
            ctypes.POINTER(_DataBlob),
            ctypes.c_wchar_p,
            ctypes.POINTER(_DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(_DataBlob),
        ]
        function.restype = wintypes.BOOL
        if not function(
            ctypes.byref(in_blob),
            None,
            ctypes.byref(entropy_blob),
            None,
            None,
            1,
            ctypes.byref(out_blob),
        ):
            raise OSError(ctypes.get_last_error(), "DPAPI operation failed")
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            if out_blob.pbData:
                kernel32.LocalFree(ctypes.cast(out_blob.pbData, ctypes.c_void_p))
            _ = in_buffer, entropy_buffer

    def encrypt(self, plaintext: bytes) -> bytes:
        return self._crypt(plaintext, protect=True)

    def decrypt(self, ciphertext: bytes) -> bytes:
        return self._crypt(ciphertext, protect=False)


_FALSE_EFFECTS = (
    "canonical_trust_root_confirmed",
    "owner_signer_binding_confirmed",
    "canonical_knowledge_pack_receipt_minted",
    "knowledge_pack_write_authorized",
    "knowledge_pack_promotion_authorized",
    "automatic_promotion_authorized",
    "runtime_profile_apply_authorized",
    "rollback_execution_authorized",
    "timeline_mutation_authorized",
    "resolve_mutation_authorized",
    "release_authorized",
    "deploy_authorized",
    "production_authorized",
    "external_effect_authorized",
)


@dataclass(frozen=True, slots=True)
class SignatureArtifactCustodyConfirmation:
    confirmation_id: str
    candidate_sha256: str
    artifact_store_id: str
    owner_scope_sha256: str
    signature_request_sha256: str
    signer_key_id_sha256: str
    detached_signature_sha256: str
    confirmed_at_epoch_ms: int

    def __post_init__(self) -> None:
        _logical_id(self.confirmation_id, "confirmation_id")
        _sha(self.candidate_sha256, "candidate_sha256")
        _logical_id(self.artifact_store_id, "artifact_store_id")
        for field in (
            "owner_scope_sha256",
            "signature_request_sha256",
            "signer_key_id_sha256",
            "detached_signature_sha256",
        ):
            _sha(getattr(self, field), field)
        _positive(self.confirmed_at_epoch_ms, "confirmed_at_epoch_ms")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "record_version": SIGNATURE_ARTIFACT_CUSTODY_RECORD_VERSION,
            "record_type": "SIGNATURE_ARTIFACT_CUSTODY_CONFIRMATION",
            "task_owner": "TASK-029",
            "confirmation_id": self.confirmation_id,
            "candidate_sha256": self.candidate_sha256,
            "artifact_store_id": self.artifact_store_id,
            "owner_scope_sha256": self.owner_scope_sha256,
            "signature_request_sha256": self.signature_request_sha256,
            "signer_key_id_sha256": self.signer_key_id_sha256,
            "detached_signature_sha256": self.detached_signature_sha256,
            "confirmed_at_epoch_ms": self.confirmed_at_epoch_ms,
            "explicit_human_confirmation_received": True,
            "signature_artifact_custody_write_authorized_once": True,
            **{field: False for field in _FALSE_EFFECTS},
        }
        body["confirmation_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any]
    ) -> "SignatureArtifactCustodyConfirmation":
        snapshot = _snapshot_json_object(value, "signature_artifact_confirmation")
        result = cls(
            snapshot["confirmation_id"],
            snapshot["candidate_sha256"],
            snapshot["artifact_store_id"],
            snapshot["owner_scope_sha256"],
            snapshot["signature_request_sha256"],
            snapshot["signer_key_id_sha256"],
            snapshot["detached_signature_sha256"],
            snapshot["confirmed_at_epoch_ms"],
        )
        if result.to_dict() != snapshot:
            raise ValueError("signature artifact confirmation identity or hash mismatch")
        return result


def confirm_signature_artifact_custody(
    *,
    confirmation_id: str,
    candidate_payload: Mapping[str, Any],
    confirmed_at_epoch_ms: int,
    explicit_human_confirmation: bool,
) -> SignatureArtifactCustodyConfirmation:
    if explicit_human_confirmation is not True:
        raise _fail(
            "ERR_SIGNATURE_ARTIFACT_CUSTODY_CONFIRMATION_REQUIRED",
            "explicit Human signature-artifact custody confirmation is required",
            ProductErrorCategory.AUTHORIZATION,
        )
    candidate = SignatureArtifactCustodyCandidate.from_dict(
        _snapshot_json_object(candidate_payload, "candidate_payload")
    )
    _positive(confirmed_at_epoch_ms, "confirmed_at_epoch_ms")
    if confirmed_at_epoch_ms < candidate.created_at_epoch_ms:
        raise ValueError("custody confirmation precedes the exact R10C candidate")
    candidate_dict = candidate.to_dict()
    return SignatureArtifactCustodyConfirmation(
        confirmation_id,
        candidate_dict["custody_candidate_sha256"],
        candidate.artifact_store_id,
        candidate.owner_scope_sha256,
        candidate.signature_request_sha256,
        candidate.signer_key_id_sha256,
        candidate.detached_signature_sha256,
        confirmed_at_epoch_ms,
    )


@dataclass(frozen=True, slots=True)
class SignatureArtifactCustodyReceipt:
    receipt_id: str
    candidate_sha256: str
    artifact_store_id: str
    owner_scope_sha256: str
    source_key_custody_receipt_sha256: str
    source_signing_ceremony_receipt_sha256: str
    source_trusted_signature_admission_sha256: str
    pack_id: str
    pack_version: str
    predecessor_pack_sha256: str | None
    signature_request_sha256: str
    signature_message_sha256: str
    trusted_signer_policy_sha256: str
    signer_key_id_sha256: str
    detached_signature_sha256: str
    verification_receipt_sha256: str
    confirmation_sha256: str
    stored_at_epoch_ms: int
    cipher_suite: str

    def __post_init__(self) -> None:
        _logical_id(self.receipt_id, "receipt_id")
        _logical_id(self.artifact_store_id, "artifact_store_id")
        _id(self.pack_id, "pack_id")
        if type(self.pack_version) is not str or re.fullmatch(
            r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)",
            self.pack_version,
        ) is None:
            raise ValueError("pack_version must be an exact semantic version")
        for field in (
            "candidate_sha256",
            "owner_scope_sha256",
            "source_key_custody_receipt_sha256",
            "source_signing_ceremony_receipt_sha256",
            "source_trusted_signature_admission_sha256",
            "signature_request_sha256",
            "signature_message_sha256",
            "trusted_signer_policy_sha256",
            "signer_key_id_sha256",
            "detached_signature_sha256",
            "verification_receipt_sha256",
            "confirmation_sha256",
        ):
            _sha(getattr(self, field), field)
        if self.predecessor_pack_sha256 is not None:
            _sha(self.predecessor_pack_sha256, "predecessor_pack_sha256")
        _positive(self.stored_at_epoch_ms, "stored_at_epoch_ms")
        _logical_id(self.cipher_suite, "cipher_suite")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "receipt_version": SIGNATURE_ARTIFACT_CUSTODY_RECEIPT_VERSION,
            "record_type": "SIGNATURE_ARTIFACT_CUSTODY_RECEIPT",
            "task_owner": "TASK-029",
            "receipt_id": self.receipt_id,
            "candidate_sha256": self.candidate_sha256,
            "artifact_store_id": self.artifact_store_id,
            "owner_scope_sha256": self.owner_scope_sha256,
            "source_key_custody_receipt_sha256": self.source_key_custody_receipt_sha256,
            "source_signing_ceremony_receipt_sha256": self.source_signing_ceremony_receipt_sha256,
            "source_trusted_signature_admission_sha256": self.source_trusted_signature_admission_sha256,
            "pack_id": self.pack_id,
            "pack_version": self.pack_version,
            "predecessor_pack_sha256": self.predecessor_pack_sha256,
            "signature_request_sha256": self.signature_request_sha256,
            "signature_message_sha256": self.signature_message_sha256,
            "trusted_signer_policy_sha256": self.trusted_signer_policy_sha256,
            "signer_key_id_sha256": self.signer_key_id_sha256,
            "detached_signature_sha256": self.detached_signature_sha256,
            "verification_receipt_sha256": self.verification_receipt_sha256,
            "confirmation_sha256": self.confirmation_sha256,
            "stored_at_epoch_ms": self.stored_at_epoch_ms,
            "cipher_suite": self.cipher_suite,
            "custody_contract": SIGNATURE_ARTIFACT_CUSTODY_CONTRACT,
            "state": "OWNER_LOCAL_SIGNATURE_ARTIFACT_CUSTODIED",
            "path_security_model": SIGNATURE_ARTIFACT_PATH_SECURITY_MODEL,
            "r10b_direct_recompiled_at_write": True,
            "caller_supplied_source_graph_recompiled_at_write": True,
            "cryptographic_signature_verified_against_supplied_policy_at_write": True,
            "r10c_candidate_recompiled_at_write": True,
            "explicit_human_custody_confirmation_received": True,
            "owner_local_encrypted_store_implemented": True,
            "one_shot_write_completed": True,
            "post_write_readback_verified": True,
            "signature_artifact_custody_confirmed": True,
            "symlink_rejection_present": True,
            "encrypted_at_rest": True,
            "body_free_receipt": True,
            "signature_artifact_body_included": False,
            "public_key_material_included": False,
            "private_key_material_included": False,
            "absolute_host_path_included": False,
            "credential_included": False,
            "directory_durability_confirmed": False,
            "power_loss_replay_prevention_confirmed": False,
            "hostile_path_race_protection_confirmed": False,
            "deletion_replay_prevention_confirmed": False,
            "alternate_path_replay_prevention_confirmed": False,
            "owner_local_path_verified": False,
            "canonical_store_path_binding_confirmed": False,
            "project_scope_coordinates_included": False,
            "canonical_project_binding_confirmed": False,
            "canonical_latest_source_revalidated": False,
            "canonical_trusted_signer_policy_revalidated": False,
            "owner_scope_origin_authenticated": False,
            **{field: False for field in _FALSE_EFFECTS},
        }
        body["custody_receipt_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any]
    ) -> "SignatureArtifactCustodyReceipt":
        snapshot = _snapshot_json_object(value, "signature_artifact_custody_receipt")
        result = cls(
            snapshot["receipt_id"],
            snapshot["candidate_sha256"],
            snapshot["artifact_store_id"],
            snapshot["owner_scope_sha256"],
            snapshot["source_key_custody_receipt_sha256"],
            snapshot["source_signing_ceremony_receipt_sha256"],
            snapshot["source_trusted_signature_admission_sha256"],
            snapshot["pack_id"],
            snapshot["pack_version"],
            snapshot["predecessor_pack_sha256"],
            snapshot["signature_request_sha256"],
            snapshot["signature_message_sha256"],
            snapshot["trusted_signer_policy_sha256"],
            snapshot["signer_key_id_sha256"],
            snapshot["detached_signature_sha256"],
            snapshot["verification_receipt_sha256"],
            snapshot["confirmation_sha256"],
            snapshot["stored_at_epoch_ms"],
            snapshot["cipher_suite"],
        )
        if result.to_dict() != snapshot:
            raise ValueError("signature artifact custody receipt identity mismatch")
        return result


@dataclass(frozen=True, slots=True)
class _SignatureArtifactCustodySecret:
    receipt_id: str
    candidate: SignatureArtifactCustodyCandidate
    admission: KnowledgePackTrustedSignatureAdmission
    confirmation: SignatureArtifactCustodyConfirmation
    public_key_bytes: bytes
    detached_signature_bytes: bytes
    stored_at_epoch_ms: int

    def validate(self) -> None:
        _logical_id(self.receipt_id, "receipt_id")
        _exact_bytes(self.public_key_bytes, "public_key_bytes", 32)
        _exact_bytes(self.detached_signature_bytes, "detached_signature_bytes", 64)
        _positive(self.stored_at_epoch_ms, "stored_at_epoch_ms")
        candidate = self.candidate
        admission = self.admission
        candidate_payload = candidate.to_dict()
        admission_payload = admission.to_dict()
        if candidate.source_trusted_signature_admission_sha256 != admission_payload[
            "trusted_signature_admission_sha256"
        ]:
            raise ValueError("custody candidate does not bind the exact R10B admission")
        candidate_coordinates = (
            candidate.pack_id,
            candidate.pack_version,
            candidate.predecessor_pack_sha256,
            candidate.signature_request_sha256,
            candidate.signature_message_sha256,
            candidate.trusted_signer_policy_sha256,
            candidate.signer_key_id_sha256,
            candidate.detached_signature_sha256,
            candidate.verification_receipt_sha256,
        )
        admission_coordinates = (
            admission.pack_id,
            admission.pack_version,
            admission.predecessor_pack_sha256,
            admission.signature_request_sha256,
            admission.signature_message_sha256,
            admission.trusted_signer_policy_sha256,
            admission.signer_key_id_sha256,
            admission.detached_signature_sha256,
            admission.verification_receipt_sha256,
        )
        if candidate_coordinates != admission_coordinates:
            raise ValueError("custodied R10B coordinates do not match R10C")
        if sha256_bytes(self.public_key_bytes) != candidate.signer_key_id_sha256:
            raise ValueError("transient public key does not match the custody candidate")
        if (
            sha256_bytes(self.detached_signature_bytes)
            != candidate.detached_signature_sha256
        ):
            raise ValueError("detached signature does not match the custody candidate")
        confirmation = self.confirmation
        if (
            confirmation.candidate_sha256,
            confirmation.artifact_store_id,
            confirmation.owner_scope_sha256,
            confirmation.signature_request_sha256,
            confirmation.signer_key_id_sha256,
            confirmation.detached_signature_sha256,
        ) != (
            candidate_payload["custody_candidate_sha256"],
            candidate.artifact_store_id,
            candidate.owner_scope_sha256,
            candidate.signature_request_sha256,
            candidate.signer_key_id_sha256,
            candidate.detached_signature_sha256,
        ):
            raise ValueError("explicit Human confirmation does not match R10C")
        if confirmation.confirmed_at_epoch_ms < candidate.created_at_epoch_ms:
            raise ValueError("custody confirmation precedes R10C")
        if self.stored_at_epoch_ms < max(
            candidate.created_at_epoch_ms,
            admission.verified_at_epoch_ms,
            confirmation.confirmed_at_epoch_ms,
        ):
            raise ValueError("signature artifact storage precedes exact Evidence")
        try:
            Ed25519PublicKey.from_public_bytes(self.public_key_bytes).verify(
                self.detached_signature_bytes,
                candidate.signature_message_sha256.encode("ascii"),
            )
        except InvalidSignature as exc:
            raise ValueError("custodied detached signature is invalid") from exc

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        body: dict[str, Any] = {
            "record_version": SIGNATURE_ARTIFACT_CUSTODY_RECORD_VERSION,
            "record_type": "SIGNATURE_ARTIFACT_CUSTODY_SECRET",
            "task_owner": "TASK-029",
            "receipt_id": self.receipt_id,
            "candidate": self.candidate.to_dict(),
            "trusted_signature_admission": self.admission.to_dict(),
            "confirmation": self.confirmation.to_dict(),
            "public_key_b64": base64.b64encode(self.public_key_bytes).decode("ascii"),
            "detached_signature_b64": base64.b64encode(
                self.detached_signature_bytes
            ).decode("ascii"),
            "stored_at_epoch_ms": self.stored_at_epoch_ms,
            "private_key_material_included": False,
            **{field: False for field in _FALSE_EFFECTS},
        }
        body["secret_record_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "_SignatureArtifactCustodySecret":
        snapshot = _snapshot_json_object(value, "signature_artifact_custody_secret")
        body = {key: item for key, item in snapshot.items() if key != "secret_record_sha256"}
        if snapshot.get("secret_record_sha256") != sha256_bytes(
            canonical_json_bytes(body)
        ):
            raise ValueError("signature artifact secret checksum mismatch")
        if (
            snapshot.get("record_version"),
            snapshot.get("record_type"),
            snapshot.get("task_owner"),
        ) != (
            SIGNATURE_ARTIFACT_CUSTODY_RECORD_VERSION,
            "SIGNATURE_ARTIFACT_CUSTODY_SECRET",
            "TASK-029",
        ):
            raise ValueError("signature artifact secret identity mismatch")
        if snapshot.get("private_key_material_included") is not False or any(
            snapshot.get(field) is not False for field in _FALSE_EFFECTS
        ):
            raise ValueError("signature artifact secret authority mismatch")
        secret = cls(
            snapshot["receipt_id"],
            SignatureArtifactCustodyCandidate.from_dict(snapshot["candidate"]),
            KnowledgePackTrustedSignatureAdmission.from_dict(
                snapshot["trusted_signature_admission"]
            ),
            SignatureArtifactCustodyConfirmation.from_dict(snapshot["confirmation"]),
            base64.b64decode(snapshot["public_key_b64"], validate=True),
            base64.b64decode(snapshot["detached_signature_b64"], validate=True),
            snapshot["stored_at_epoch_ms"],
        )
        secret.validate()
        if secret.to_dict() != snapshot:
            raise ValueError("signature artifact secret canonical form mismatch")
        return secret


@dataclass(frozen=True, slots=True)
class SignatureArtifactCustodySaveResult:
    receipt: SignatureArtifactCustodyReceipt
    write: AtomicWriteResult


class SignatureArtifactCustodyStore:
    def __init__(
        self,
        path: str | Path,
        cipher: SignatureArtifactCustodyCipher | None = None,
    ) -> None:
        self.path = Path(path)
        self.cipher = (
            cipher
            if cipher is not None
            else WindowsDpapiSignatureArtifactCustodyCipher()
        )
        if not isinstance(self.cipher, SignatureArtifactCustodyCipher):
            raise ValueError("cipher does not implement SignatureArtifactCustodyCipher")
        _logical_id(self.cipher.cipher_suite, "cipher_suite")

    def _receipt(
        self, secret: _SignatureArtifactCustodySecret
    ) -> SignatureArtifactCustodyReceipt:
        candidate = secret.candidate
        return SignatureArtifactCustodyReceipt(
            secret.receipt_id,
            candidate.to_dict()["custody_candidate_sha256"],
            candidate.artifact_store_id,
            candidate.owner_scope_sha256,
            candidate.source_key_custody_receipt_sha256,
            candidate.source_signing_ceremony_receipt_sha256,
            candidate.source_trusted_signature_admission_sha256,
            candidate.pack_id,
            candidate.pack_version,
            candidate.predecessor_pack_sha256,
            candidate.signature_request_sha256,
            candidate.signature_message_sha256,
            candidate.trusted_signer_policy_sha256,
            candidate.signer_key_id_sha256,
            candidate.detached_signature_sha256,
            candidate.verification_receipt_sha256,
            secret.confirmation.to_dict()["confirmation_sha256"],
            secret.stored_at_epoch_ms,
            self.cipher.cipher_suite,
        )

    def _envelope(self, secret: _SignatureArtifactCustodySecret) -> dict[str, Any]:
        plaintext = canonical_json_bytes(secret.to_dict())
        ciphertext = self.cipher.encrypt(plaintext)
        if (
            type(ciphertext) is not bytes
            or not ciphertext
            or ciphertext == plaintext
            or len(ciphertext) > _MAX_CIPHERTEXT_BYTES
        ):
            raise ValueError("ciphertext size or type is invalid")
        body: dict[str, Any] = {
            "schema_version": SIGNATURE_ARTIFACT_CUSTODY_STORE_SCHEMA_VERSION,
            "record_type": "SIGNATURE_ARTIFACT_CUSTODY_STORE_ENCRYPTED",
            "task_owner": "TASK-029",
            "cipher_suite": self.cipher.cipher_suite,
            "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
            "ciphertext_sha256": sha256_bytes(ciphertext),
            "plaintext_fields_present": False,
        }
        body["document_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    def _parse_envelope(
        self, value: Mapping[str, Any]
    ) -> _SignatureArtifactCustodySecret:
        snapshot = _snapshot_json_object(value, "signature_artifact_envelope")
        expected = {
            "schema_version",
            "record_type",
            "task_owner",
            "cipher_suite",
            "ciphertext_b64",
            "ciphertext_sha256",
            "plaintext_fields_present",
            "document_sha256",
        }
        if set(snapshot) != expected:
            raise ValueError("encrypted artifact fields are incomplete or unknown")
        if (
            snapshot["schema_version"],
            snapshot["record_type"],
            snapshot["task_owner"],
        ) != (
            SIGNATURE_ARTIFACT_CUSTODY_STORE_SCHEMA_VERSION,
            "SIGNATURE_ARTIFACT_CUSTODY_STORE_ENCRYPTED",
            "TASK-029",
        ):
            raise ValueError("encrypted artifact identity mismatch")
        if (
            snapshot["cipher_suite"] != self.cipher.cipher_suite
            or snapshot["plaintext_fields_present"] is not False
        ):
            raise ValueError("artifact cipher or plaintext boundary mismatch")
        body = {
            key: item for key, item in snapshot.items() if key != "document_sha256"
        }
        if snapshot["document_sha256"] != sha256_bytes(canonical_json_bytes(body)):
            raise ValueError("encrypted artifact document checksum mismatch")
        if type(snapshot["ciphertext_b64"]) is not str:
            raise ValueError("ciphertext_b64 must be an exact string")
        ciphertext = base64.b64decode(snapshot["ciphertext_b64"], validate=True)
        if (
            not ciphertext
            or len(ciphertext) > _MAX_CIPHERTEXT_BYTES
            or snapshot["ciphertext_sha256"] != sha256_bytes(ciphertext)
        ):
            raise ValueError("encrypted artifact ciphertext checksum mismatch")
        plaintext = self.cipher.decrypt(ciphertext)
        if type(plaintext) is not bytes:
            raise ValueError("decrypted artifact must be exact bytes")
        decrypted = json.loads(plaintext.decode("utf-8"))
        return _SignatureArtifactCustodySecret.from_dict(decrypted)

    def _load_secret(self) -> _SignatureArtifactCustodySecret:
        try:
            if self.path.is_symlink() or not self.path.is_file():
                raise ValueError(
                    "signature artifact custody must be a regular non-symlink file"
                )
            document = json.loads(self.path.read_text(encoding="utf-8"))
            return self._parse_envelope(document)
        except ProductError:
            raise
        except Exception as exc:
            raise _fail(
                "ERR_SIGNATURE_ARTIFACT_CUSTODY_INTEGRITY",
                "Signature artifact custody could not be decrypted and verified safely",
                ProductErrorCategory.DATA_INTEGRITY,
                reason=type(exc).__name__,
            ) from exc

    def read_receipt(self) -> SignatureArtifactCustodyReceipt:
        return self._receipt(self._load_secret())

    def provision(
        self,
        *,
        receipt_id: str,
        candidate_payload: Mapping[str, Any],
        key_custody_receipt_payload: Mapping[str, Any],
        trusted_signature_admission_compile_kwargs: Mapping[str, Any],
        confirmation: SignatureArtifactCustodyConfirmation,
        stored_at_epoch_ms: int,
        failure_injector: FailureInjector | None = None,
    ) -> SignatureArtifactCustodySaveResult:
        """Recompile exact sources and perform one encrypted custody write."""

        _logical_id(receipt_id, "receipt_id")
        _positive(stored_at_epoch_ms, "stored_at_epoch_ms")
        if type(confirmation) is not SignatureArtifactCustodyConfirmation:
            raise ValueError(
                "confirmation must be an exact SignatureArtifactCustodyConfirmation"
            )
        candidate_snapshot = _snapshot_json_object(
            candidate_payload, "candidate_payload"
        )
        candidate = SignatureArtifactCustodyCandidate.from_dict(candidate_snapshot)
        custody_snapshot = _snapshot_json_object(
            key_custody_receipt_payload, "key_custody_receipt_payload"
        )
        if type(trusted_signature_admission_compile_kwargs) is not dict:
            raise ValueError(
                "trusted_signature_admission_compile_kwargs must be an exact object"
            )
        required = {
            "admission_id",
            "promotion_intent_payload",
            "promotion_intent_compile_kwargs",
            "signing_ceremony_receipt_payload",
            "trusted_signer_policy_payload",
            "public_key_bytes",
            "detached_signature_bytes",
            "verified_at_epoch_ms",
        }
        if set(trusted_signature_admission_compile_kwargs) != required:
            raise ValueError("R10B compile kwargs are incomplete or unknown")
        r10b_arguments = {
            "admission_id": _id(
                trusted_signature_admission_compile_kwargs["admission_id"],
                "admission_id",
            ),
            "promotion_intent_payload": _snapshot_json_object(
                trusted_signature_admission_compile_kwargs[
                    "promotion_intent_payload"
                ],
                "promotion_intent_payload",
            ),
            "promotion_intent_compile_kwargs": trusted_signature_admission_compile_kwargs[
                "promotion_intent_compile_kwargs"
            ],
            "signing_ceremony_receipt_payload": _snapshot_json_object(
                trusted_signature_admission_compile_kwargs[
                    "signing_ceremony_receipt_payload"
                ],
                "signing_ceremony_receipt_payload",
            ),
            "trusted_signer_policy_payload": _snapshot_json_object(
                trusted_signature_admission_compile_kwargs[
                    "trusted_signer_policy_payload"
                ],
                "trusted_signer_policy_payload",
            ),
            "public_key_bytes": _exact_bytes(
                trusted_signature_admission_compile_kwargs["public_key_bytes"],
                "public_key_bytes",
                32,
            ),
            "detached_signature_bytes": _exact_bytes(
                trusted_signature_admission_compile_kwargs[
                    "detached_signature_bytes"
                ],
                "detached_signature_bytes",
                64,
            ),
            "verified_at_epoch_ms": _positive(
                trusted_signature_admission_compile_kwargs[
                    "verified_at_epoch_ms"
                ],
                "verified_at_epoch_ms",
            ),
        }
        admission = compile_knowledge_pack_trusted_signature_admission(
            **r10b_arguments
        )
        expected_candidate = compile_signature_artifact_custody_candidate(
            candidate_id=candidate.candidate_id,
            artifact_store_id=candidate.artifact_store_id,
            key_custody_receipt_payload=custody_snapshot,
            signing_ceremony_receipt_payload=r10b_arguments[
                "signing_ceremony_receipt_payload"
            ],
            trusted_signature_admission_payload=admission.to_dict(),
            created_at_epoch_ms=candidate.created_at_epoch_ms,
        )
        if expected_candidate.to_dict() != candidate_snapshot:
            raise ValueError("R10C candidate does not match exact write-time Evidence")
        secret = _SignatureArtifactCustodySecret(
            receipt_id,
            expected_candidate,
            admission,
            confirmation,
            r10b_arguments["public_key_bytes"],
            r10b_arguments["detached_signature_bytes"],
            stored_at_epoch_ms,
        )
        secret.validate()
        with exclusive_file_update_lock(self.path):
            if self.path.is_symlink():
                raise _fail(
                    "ERR_SIGNATURE_ARTIFACT_CUSTODY_INTEGRITY",
                    "Signature artifact custody path is a symlink",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            if self.path.exists():
                raise _fail(
                    "ERR_SIGNATURE_ARTIFACT_CUSTODY_ALREADY_EXISTS",
                    "Signature artifact custody is one-shot and cannot be overwritten",
                    ProductErrorCategory.STATE,
                )
            write = AtomicJsonWriter.write(
                self.path,
                self._envelope(secret),
                validator=lambda value: self._parse_envelope(value),
                failure_injector=failure_injector,
            )
            persisted = self._load_secret()
            if persisted != secret:
                raise _fail(
                    "ERR_SIGNATURE_ARTIFACT_CUSTODY_READBACK_MISMATCH",
                    "Signature artifact custody read-back did not match the write",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
        return SignatureArtifactCustodySaveResult(self._receipt(persisted), write)


__all__ = [
    "SIGNATURE_ARTIFACT_CUSTODY_CONTRACT",
    "SIGNATURE_ARTIFACT_CUSTODY_RECEIPT_VERSION",
    "SIGNATURE_ARTIFACT_CUSTODY_RECORD_VERSION",
    "SIGNATURE_ARTIFACT_CUSTODY_STORE_SCHEMA_VERSION",
    "SIGNATURE_ARTIFACT_DPAPI_CIPHER_SUITE",
    "SIGNATURE_ARTIFACT_PATH_SECURITY_MODEL",
    "SignatureArtifactCustodyCipher",
    "SignatureArtifactCustodyConfirmation",
    "SignatureArtifactCustodyReceipt",
    "SignatureArtifactCustodySaveResult",
    "SignatureArtifactCustodyStore",
    "WindowsDpapiSignatureArtifactCustodyCipher",
    "confirm_signature_artifact_custody",
]
