"""TASK-029 R9A Ed25519 verification with body-free receipts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .knowledge_pack_signature_request import (
    KNOWLEDGE_PACK_SIGNATURE_INPUT_CONTRACT,
    KnowledgePackSignatureVerificationRequest,
    verify_knowledge_pack_signature_verification_request,
)
from .serialization import canonical_json_bytes, sha256_bytes


TRUSTED_SIGNER_POLICY_VERSION = "1.0.0"
SIGNATURE_VERIFICATION_RECEIPT_VERSION = "1.0.0"
_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_SEMVER = re.compile(r"^(0|[1-9]d*).(0|[1-9]d*).(0|[1-9]d*)$")


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        raise ValueError(f"{field} must be sha256:<64 lowercase hex>")
    return value


def _id(value: object, field: str) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise ValueError(f"{field} is invalid")
    return value


class TrustedSignerPolicyState(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


@dataclass(frozen=True, slots=True)
class TrustedSignerPolicy:
    policy_id: str
    trusted_signer_key_ids: tuple[str, ...]
    state: TrustedSignerPolicyState = TrustedSignerPolicyState.ACTIVE

    def __post_init__(self) -> None:
        _id(self.policy_id, "policy_id")
        if not isinstance(self.state, TrustedSignerPolicyState):
            raise ValueError("state must be a TrustedSignerPolicyState")
        if not 1 <= len(self.trusted_signer_key_ids) <= 32:
            raise ValueError("trusted_signer_key_ids must contain 1..32 values")
        for item in self.trusted_signer_key_ids:
            _sha(item, "trusted_signer_key_id")
        if self.trusted_signer_key_ids != tuple(sorted(set(self.trusted_signer_key_ids))):
            raise ValueError("trusted_signer_key_ids must be unique and sorted")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "policy_version": TRUSTED_SIGNER_POLICY_VERSION,
            "record_type": "TRUSTED_KNOWLEDGE_PACK_SIGNER_POLICY",
            "task_owner": "TASK-029",
            "policy_id": self.policy_id,
            "signature_algorithm": "ED25519",
            "trusted_signer_key_ids": list(self.trusted_signer_key_ids),
            "state": self.state.value,
            "private_key_material_included": False,
            "signature_authorized": False,
            "knowledge_pack_write_authorized": False,
            "automatic_promotion_authorized": False,
        }
        body["trusted_signer_policy_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TrustedSignerPolicy":
        expected = {
            "policy_version", "record_type", "task_owner", "policy_id",
            "signature_algorithm", "trusted_signer_key_ids", "state",
            "private_key_material_included", "signature_authorized",
            "knowledge_pack_write_authorized", "automatic_promotion_authorized",
            "trusted_signer_policy_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("trusted signer policy fields are incomplete or unknown")
        identity = (
            value["policy_version"], value["record_type"], value["task_owner"],
            value["signature_algorithm"],
        )
        if identity != (
            TRUSTED_SIGNER_POLICY_VERSION, "TRUSTED_KNOWLEDGE_PACK_SIGNER_POLICY",
            "TASK-029", "ED25519",
        ):
            raise ValueError("trusted signer policy identity mismatch")
        for field in (
            "private_key_material_included", "signature_authorized",
            "knowledge_pack_write_authorized", "automatic_promotion_authorized",
        ):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        key_ids = value["trusted_signer_key_ids"]
        if not isinstance(key_ids, list):
            raise ValueError("trusted_signer_key_ids must be an array")
        result = cls(
            value["policy_id"], tuple(key_ids), TrustedSignerPolicyState(value["state"])
        )
        if result.to_dict() != dict(value):
            raise ValueError("trusted signer policy hash mismatch")
        return result


@dataclass(frozen=True, slots=True)
class KnowledgePackSignatureVerificationReceipt:
    receipt_id: str
    signature_request_id: str
    signature_request_sha256: str
    signing_candidate_sha256: str
    pack_id: str
    pack_version: str
    trusted_signer_policy_sha256: str
    signer_key_id_sha256: str
    signature_message_sha256: str
    detached_signature_sha256: str

    def __post_init__(self) -> None:
        for field in ("receipt_id", "signature_request_id", "pack_id"):
            _id(getattr(self, field), field)
        for field in (
            "signature_request_sha256", "signing_candidate_sha256",
            "trusted_signer_policy_sha256", "signer_key_id_sha256",
            "signature_message_sha256", "detached_signature_sha256",
        ):
            _sha(getattr(self, field), field)
        if not isinstance(self.pack_version, str):
            raise ValueError("pack_version must be a string")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "receipt_version": SIGNATURE_VERIFICATION_RECEIPT_VERSION,
            "record_type": "KNOWLEDGE_PACK_SIGNATURE_VERIFICATION_RECEIPT",
            "task_owner": "TASK-029",
            "receipt_id": self.receipt_id,
            "signature_request_id": self.signature_request_id,
            "signature_request_sha256": self.signature_request_sha256,
            "signing_candidate_sha256": self.signing_candidate_sha256,
            "pack_id": self.pack_id,
            "pack_version": self.pack_version,
            "trusted_signer_policy_sha256": self.trusted_signer_policy_sha256,
            "signer_key_id_sha256": self.signer_key_id_sha256,
            "signature_algorithm": "ED25519",
            "signature_input_contract": KNOWLEDGE_PACK_SIGNATURE_INPUT_CONTRACT,
            "signature_message_sha256": self.signature_message_sha256,
            "detached_signature_sha256": self.detached_signature_sha256,
            "state": "VERIFIED",
            "signature_present": True,
            "signature_verified": True,
            "latest_source_revalidated": True,
            "signature_bytes_included": False,
            "public_key_material_included": False,
            "private_key_material_included": False,
            "knowledge_pack_write_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "automatic_promotion_authorized": False,
            "runtime_profile_apply_authorized": False,
            "rollback_execution_authorized": False,
            "release_authorized": False,
            "external_effect_authorized": False,
        }
        body["verification_receipt_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "KnowledgePackSignatureVerificationReceipt":
        expected = {
            "receipt_version", "record_type", "task_owner", "receipt_id",
            "signature_request_id", "signature_request_sha256",
            "signing_candidate_sha256", "pack_id", "pack_version",
            "trusted_signer_policy_sha256", "signer_key_id_sha256",
            "signature_algorithm", "signature_input_contract",
            "signature_message_sha256", "detached_signature_sha256", "state",
            "signature_present", "signature_verified", "latest_source_revalidated",
            "signature_bytes_included",
            "public_key_material_included", "private_key_material_included",
            "knowledge_pack_write_authorized", "knowledge_pack_promotion_authorized",
            "automatic_promotion_authorized", "runtime_profile_apply_authorized",
            "rollback_execution_authorized", "release_authorized",
            "external_effect_authorized",
            "verification_receipt_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("signature verification receipt fields are incomplete or unknown")
        if (
            value["receipt_version"], value["record_type"], value["task_owner"],
            value["signature_algorithm"], value["signature_input_contract"],
            value["state"], value["signature_present"], value["signature_verified"],
            value["latest_source_revalidated"],
        ) != (
            SIGNATURE_VERIFICATION_RECEIPT_VERSION,
            "KNOWLEDGE_PACK_SIGNATURE_VERIFICATION_RECEIPT", "TASK-029", "ED25519",
            KNOWLEDGE_PACK_SIGNATURE_INPUT_CONTRACT, "VERIFIED", True, True, True,
        ):
            raise ValueError("signature verification receipt identity mismatch")
        for field in (
            "signature_bytes_included", "public_key_material_included",
            "private_key_material_included", "knowledge_pack_write_authorized",
            "knowledge_pack_promotion_authorized", "automatic_promotion_authorized",
            "runtime_profile_apply_authorized", "rollback_execution_authorized",
            "release_authorized", "external_effect_authorized",
        ):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        result = cls(
            value["receipt_id"], value["signature_request_id"],
            value["signature_request_sha256"], value["signing_candidate_sha256"],
            value["pack_id"], value["pack_version"],
            value["trusted_signer_policy_sha256"], value["signer_key_id_sha256"],
            value["signature_message_sha256"], value["detached_signature_sha256"],
        )
        if result.to_dict() != dict(value):
            raise ValueError("signature verification receipt hash mismatch")
        return result


def verify_detached_knowledge_pack_signature(
    *, receipt_id: str, signature_request_payload: Mapping[str, Any],
    signature_request_compile_kwargs: Mapping[str, Any],
    trusted_signer_policy_payload: Mapping[str, Any], public_key_bytes: bytes,
    detached_signature_bytes: bytes,
) -> KnowledgePackSignatureVerificationReceipt:
    """Verify exact R8 bytes and return a body-free, no-effect receipt."""
    if not isinstance(signature_request_compile_kwargs, Mapping):
        raise ValueError("signature_request_compile_kwargs must be a mapping")
    verify_knowledge_pack_signature_verification_request(
        signature_request_payload, **dict(signature_request_compile_kwargs)
    )
    request = KnowledgePackSignatureVerificationRequest.from_dict(signature_request_payload)
    policy = TrustedSignerPolicy.from_dict(trusted_signer_policy_payload)
    if policy.state is not TrustedSignerPolicyState.ACTIVE:
        raise ValueError("trusted signer policy is not active")
    policy_sha = policy.to_dict()["trusted_signer_policy_sha256"]
    if policy_sha != request.trusted_signer_policy_sha256:
        raise ValueError("trusted signer policy does not match signature request")
    if not isinstance(public_key_bytes, bytes) or len(public_key_bytes) != 32:
        raise ValueError("Ed25519 public key must be exactly 32 bytes")
    signer_key_id = sha256_bytes(public_key_bytes)
    if signer_key_id != request.signer_key_id_sha256:
        raise ValueError("public key identity does not match signature request")
    if signer_key_id not in policy.trusted_signer_key_ids:
        raise ValueError("public key is not allowed by trusted signer policy")
    if not isinstance(detached_signature_bytes, bytes) or len(detached_signature_bytes) != 64:
        raise ValueError("Ed25519 detached signature must be exactly 64 bytes")
    request_payload = request.to_dict()
    message = request_payload["signature_message_sha256"].encode("ascii")
    try:
        Ed25519PublicKey.from_public_bytes(public_key_bytes).verify(
            detached_signature_bytes, message
        )
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("Ed25519 signature verification failed") from exc
    return KnowledgePackSignatureVerificationReceipt(
        receipt_id, request.request_id, request_payload["signature_request_sha256"],
        request.signing_candidate_sha256, request.pack_id, request.pack_version,
        request.trusted_signer_policy_sha256, request.signer_key_id_sha256,
        request_payload["signature_message_sha256"], sha256_bytes(detached_signature_bytes),
    )


__all__ = [
    "KnowledgePackSignatureVerificationReceipt", "TrustedSignerPolicy",
    "TrustedSignerPolicyState", "verify_detached_knowledge_pack_signature",
]
