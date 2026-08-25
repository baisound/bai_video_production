"""TASK-029 R9C exact local Knowledge Pack signing ceremony.

The custodied seed never leaves the R9B store boundary. Exact R8 inputs are
revalidated before key access and the generated signature is immediately
verified by R9A. Only body-free receipts are returned.
"""
from __future__ import annotations
from dataclasses import dataclass
import re
from typing import Any, Mapping
from .errors import ProductError, ProductErrorCategory
from .knowledge_pack_signature_request import KnowledgePackSignatureVerificationRequest, verify_knowledge_pack_signature_verification_request
from .knowledge_pack_signature_verification import KnowledgePackSignatureVerificationReceipt, TrustedSignerPolicy, TrustedSignerPolicyState, verify_detached_knowledge_pack_signature
from .owner_signing_key_custody import OwnerSigningKeyCustodyReceipt, OwnerSigningKeyCustodyStore
from .serialization import canonical_json_bytes, sha256_bytes

CEREMONY_CONFIRMATION_VERSION = CEREMONY_RECEIPT_VERSION = "1.0.0"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
def _id(value: object, field: str) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None: raise ValueError(f"{field} must be a stable identifier")
    return value
def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA.fullmatch(value) is None: raise ValueError(f"{field} must be a lowercase sha256 coordinate")
    return value
def _positive(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1: raise ValueError(f"{field} must be an integer >= 1")
    return value

@dataclass(frozen=True, slots=True)
class LocalSigningCeremonyConfirmation:
    confirmation_id: str; ceremony_id: str; custody_receipt_sha256: str; signature_request_sha256: str; confirmed_at_epoch_ms: int
    def __post_init__(self) -> None:
        _id(self.confirmation_id, "confirmation_id"); _id(self.ceremony_id, "ceremony_id"); _sha(self.custody_receipt_sha256, "custody_receipt_sha256"); _sha(self.signature_request_sha256, "signature_request_sha256"); _positive(self.confirmed_at_epoch_ms, "confirmed_at_epoch_ms")
    def to_dict(self) -> dict[str, Any]:
        body = {"confirmation_version": CEREMONY_CONFIRMATION_VERSION, "record_type": "KNOWLEDGE_PACK_LOCAL_SIGNING_CEREMONY_CONFIRMATION", "task_owner": "TASK-029", "confirmation_id": self.confirmation_id, "ceremony_id": self.ceremony_id, "custody_receipt_sha256": self.custody_receipt_sha256, "signature_request_sha256": self.signature_request_sha256, "confirmed_at_epoch_ms": self.confirmed_at_epoch_ms, "explicit_human_confirmation_received": True, "exact_local_signing_authorized": True, "private_key_export_authorized": False, "knowledge_pack_write_authorized": False, "release_authorized": False, "external_effect_authorized": False}
        body["confirmation_sha256"] = sha256_bytes(canonical_json_bytes(body)); return body
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LocalSigningCeremonyConfirmation":
        result = cls(value["confirmation_id"], value["ceremony_id"], value["custody_receipt_sha256"], value["signature_request_sha256"], value["confirmed_at_epoch_ms"])
        if result.to_dict() != dict(value): raise ValueError("local signing ceremony confirmation mismatch")
        return result

def confirm_local_signing_ceremony(*, confirmation_id: str, ceremony_id: str, custody_receipt_payload: Mapping[str, Any], signature_request_payload: Mapping[str, Any], confirmed_at_epoch_ms: int, explicit_human_confirmation: bool) -> LocalSigningCeremonyConfirmation:
    if explicit_human_confirmation is not True: raise ProductError("ERR_KNOWLEDGE_PACK_LOCAL_SIGNING_CONFIRMATION_REQUIRED", "explicit Human confirmation is required", ProductErrorCategory.AUTHORIZATION)
    custody = OwnerSigningKeyCustodyReceipt.from_dict(custody_receipt_payload); request = KnowledgePackSignatureVerificationRequest.from_dict(signature_request_payload)
    return LocalSigningCeremonyConfirmation(confirmation_id, ceremony_id, custody.to_dict()["custody_receipt_sha256"], request.to_dict()["signature_request_sha256"], confirmed_at_epoch_ms)

@dataclass(frozen=True, slots=True)
class LocalSigningCeremonyReceipt:
    receipt_id: str; ceremony_id: str; custody_receipt_sha256: str; signature_request_sha256: str; signer_key_id_sha256: str; detached_signature_sha256: str; verification_receipt_sha256: str; confirmation_sha256: str; completed_at_epoch_ms: int
    def __post_init__(self) -> None:
        _id(self.receipt_id, "receipt_id"); _id(self.ceremony_id, "ceremony_id")
        for field in ("custody_receipt_sha256", "signature_request_sha256", "signer_key_id_sha256", "detached_signature_sha256", "verification_receipt_sha256", "confirmation_sha256"): _sha(getattr(self, field), field)
        _positive(self.completed_at_epoch_ms, "completed_at_epoch_ms")
    def to_dict(self) -> dict[str, Any]:
        body = {"receipt_version": CEREMONY_RECEIPT_VERSION, "record_type": "KNOWLEDGE_PACK_LOCAL_SIGNING_CEREMONY_RECEIPT", "task_owner": "TASK-029", "receipt_id": self.receipt_id, "ceremony_id": self.ceremony_id, "custody_receipt_sha256": self.custody_receipt_sha256, "signature_request_sha256": self.signature_request_sha256, "signer_key_id_sha256": self.signer_key_id_sha256, "detached_signature_sha256": self.detached_signature_sha256, "verification_receipt_sha256": self.verification_receipt_sha256, "confirmation_sha256": self.confirmation_sha256, "completed_at_epoch_ms": self.completed_at_epoch_ms, "state": "SIGNED_AND_VERIFIED", "latest_source_revalidated": True, "custody_revalidated_at_signing": True, "explicit_human_confirmation_received": True, "persistent_replay_prevention_present": False, "signature_bytes_included": False, "public_key_material_included": False, "private_key_material_included": False, "private_key_export_authorized": False, "knowledge_pack_write_authorized": False, "knowledge_pack_promotion_authorized": False, "automatic_promotion_authorized": False, "runtime_profile_apply_authorized": False, "rollback_execution_authorized": False, "release_authorized": False, "external_effect_authorized": False}
        body["ceremony_receipt_sha256"] = sha256_bytes(canonical_json_bytes(body)); return body
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LocalSigningCeremonyReceipt":
        result = cls(value["receipt_id"], value["ceremony_id"], value["custody_receipt_sha256"], value["signature_request_sha256"], value["signer_key_id_sha256"], value["detached_signature_sha256"], value["verification_receipt_sha256"], value["confirmation_sha256"], value["completed_at_epoch_ms"])
        if result.to_dict() != dict(value): raise ValueError("local signing ceremony receipt mismatch")
        return result

@dataclass(frozen=True, slots=True)
class LocalSigningCeremonyResult:
    receipt: LocalSigningCeremonyReceipt
    verification_receipt: KnowledgePackSignatureVerificationReceipt

def execute_local_signing_ceremony(*, receipt_id: str, verification_receipt_id: str, custody_store: OwnerSigningKeyCustodyStore, custody_receipt_payload: Mapping[str, Any], signature_request_payload: Mapping[str, Any], signature_request_compile_kwargs: Mapping[str, Any], trusted_signer_policy_payload: Mapping[str, Any], confirmation: LocalSigningCeremonyConfirmation, completed_at_epoch_ms: int) -> LocalSigningCeremonyResult:
    verify_knowledge_pack_signature_verification_request(signature_request_payload, **dict(signature_request_compile_kwargs))
    request = KnowledgePackSignatureVerificationRequest.from_dict(signature_request_payload); policy = TrustedSignerPolicy.from_dict(trusted_signer_policy_payload)
    if policy.state is not TrustedSignerPolicyState.ACTIVE: raise ValueError("trusted signer policy is not active")
    if policy.to_dict()["trusted_signer_policy_sha256"] != request.trusted_signer_policy_sha256: raise ValueError("trusted signer policy does not match signature request")
    custody = OwnerSigningKeyCustodyReceipt.from_dict(custody_receipt_payload)
    if custody_store.read_receipt() != custody: raise ValueError("custody receipt does not match current encrypted custody")
    if custody.signer_key_id_sha256 != request.signer_key_id_sha256 or custody.signer_key_id_sha256 not in policy.trusted_signer_key_ids: raise ValueError("custodied signer key is not allowed by the exact request policy")
    expected = LocalSigningCeremonyConfirmation(confirmation.confirmation_id, confirmation.ceremony_id, custody.to_dict()["custody_receipt_sha256"], request.to_dict()["signature_request_sha256"], confirmation.confirmed_at_epoch_ms)
    if confirmation != expected: raise ValueError("local signing confirmation does not match exact custody and request")
    if completed_at_epoch_ms < confirmation.confirmed_at_epoch_ms: raise ValueError("completion time precedes Human confirmation")
    public_key, signature = custody_store._sign_exact_message(message=request.to_dict()["signature_message_sha256"].encode("ascii"), expected_receipt=custody)
    verification = verify_detached_knowledge_pack_signature(receipt_id=verification_receipt_id, signature_request_payload=signature_request_payload, signature_request_compile_kwargs=signature_request_compile_kwargs, trusted_signer_policy_payload=trusted_signer_policy_payload, public_key_bytes=public_key, detached_signature_bytes=signature)
    receipt = LocalSigningCeremonyReceipt(receipt_id, confirmation.ceremony_id, custody.to_dict()["custody_receipt_sha256"], request.to_dict()["signature_request_sha256"], custody.signer_key_id_sha256, sha256_bytes(signature), verification.to_dict()["verification_receipt_sha256"], confirmation.to_dict()["confirmation_sha256"], completed_at_epoch_ms)
    if receipt.detached_signature_sha256 != verification.detached_signature_sha256: raise ValueError("signature verification receipt drift")
    return LocalSigningCeremonyResult(receipt, verification)

__all__ = ["CEREMONY_CONFIRMATION_VERSION", "CEREMONY_RECEIPT_VERSION", "LocalSigningCeremonyConfirmation", "LocalSigningCeremonyReceipt", "LocalSigningCeremonyResult", "confirm_local_signing_ceremony", "execute_local_signing_ceremony"]