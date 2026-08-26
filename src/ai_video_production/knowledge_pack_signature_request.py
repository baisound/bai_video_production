"""TASK-029 R8 pure request for external Knowledge Pack signature verification."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Mapping

from .knowledge_pack_signing import (
    KNOWLEDGE_PACK_COMPATIBILITY_CONTRACT,
    KnowledgePackSigningState,
    compile_knowledge_pack_signing_candidate,
)
from .serialization import canonical_json_bytes, sha256_bytes


KNOWLEDGE_PACK_SIGNATURE_REQUEST_VERSION = "1.0.0"
KNOWLEDGE_PACK_SIGNATURE_MESSAGE_CONTRACT = (
    "TASK-029/KNOWLEDGE_PACK/EXTERNAL_SIGNATURE_MESSAGE/1.0.0"
)
KNOWLEDGE_PACK_SIGNATURE_INPUT_CONTRACT = (
    "TASK-029/KNOWLEDGE_PACK/SIGNATURE_INPUT/SHA256-PREFIXED-ASCII/1.0.0"
)
_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        raise ValueError(f"{field} must be sha256:<64 lowercase hex>")
    return value


def _id(value: object, field: str) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise ValueError(f"{field} is invalid")
    return value


class KnowledgePackSignatureAlgorithm(str, Enum):
    ED25519 = "ED25519"


class KnowledgePackSignatureRequestState(str, Enum):
    READY_FOR_EXTERNAL_CRYPTOGRAPHIC_VERIFICATION = (
        "READY_FOR_EXTERNAL_CRYPTOGRAPHIC_VERIFICATION"
    )


@dataclass(frozen=True, slots=True)
class KnowledgePackSignatureVerificationRequest:
    request_id: str
    signing_candidate_id: str
    signing_candidate_sha256: str
    pack_id: str
    pack_version: str
    predecessor_pack_sha256: str | None
    trusted_signer_policy_sha256: str
    signer_key_id_sha256: str
    signature_algorithm: KnowledgePackSignatureAlgorithm
    state: KnowledgePackSignatureRequestState = (
        KnowledgePackSignatureRequestState.READY_FOR_EXTERNAL_CRYPTOGRAPHIC_VERIFICATION
    )

    def __post_init__(self) -> None:
        for field in ("request_id", "signing_candidate_id", "pack_id"):
            _id(getattr(self, field), field)
        if not isinstance(self.pack_version, str) or _SEMVER.fullmatch(self.pack_version) is None:
            raise ValueError("pack_version must be semantic version x.y.z")
        for field in (
            "signing_candidate_sha256",
            "trusted_signer_policy_sha256",
            "signer_key_id_sha256",
        ):
            _sha(getattr(self, field), field)
        if self.predecessor_pack_sha256 is not None:
            _sha(self.predecessor_pack_sha256, "predecessor_pack_sha256")
        if not isinstance(self.signature_algorithm, KnowledgePackSignatureAlgorithm):
            raise ValueError("signature_algorithm must be a KnowledgePackSignatureAlgorithm")
        if self.state is not KnowledgePackSignatureRequestState.READY_FOR_EXTERNAL_CRYPTOGRAPHIC_VERIFICATION:
            raise ValueError("signature request state is invalid")

    def _signature_message(self) -> dict[str, Any]:
        return {
            "message_contract": KNOWLEDGE_PACK_SIGNATURE_MESSAGE_CONTRACT,
            "signature_input_contract": KNOWLEDGE_PACK_SIGNATURE_INPUT_CONTRACT,
            "compatibility_contract": KNOWLEDGE_PACK_COMPATIBILITY_CONTRACT,
            "signing_candidate_id": self.signing_candidate_id,
            "signing_candidate_sha256": self.signing_candidate_sha256,
            "pack_id": self.pack_id,
            "pack_version": self.pack_version,
            "predecessor_pack_sha256": self.predecessor_pack_sha256,
            "trusted_signer_policy_sha256": self.trusted_signer_policy_sha256,
            "signer_key_id_sha256": self.signer_key_id_sha256,
            "signature_algorithm": self.signature_algorithm.value,
        }

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "request_version": KNOWLEDGE_PACK_SIGNATURE_REQUEST_VERSION,
            "record_type": "KNOWLEDGE_PACK_SIGNATURE_VERIFICATION_REQUEST",
            "task_owner": "TASK-029",
            "compatibility_contract": KNOWLEDGE_PACK_COMPATIBILITY_CONTRACT,
            "signature_message_contract": KNOWLEDGE_PACK_SIGNATURE_MESSAGE_CONTRACT,
            "signature_input_contract": KNOWLEDGE_PACK_SIGNATURE_INPUT_CONTRACT,
            "request_id": self.request_id,
            "signing_candidate_id": self.signing_candidate_id,
            "signing_candidate_sha256": self.signing_candidate_sha256,
            "pack_id": self.pack_id,
            "pack_version": self.pack_version,
            "predecessor_pack_sha256": self.predecessor_pack_sha256,
            "trusted_signer_policy_sha256": self.trusted_signer_policy_sha256,
            "signer_key_id_sha256": self.signer_key_id_sha256,
            "signature_algorithm": self.signature_algorithm.value,
            "signature_message_sha256": sha256_bytes(
                canonical_json_bytes(self._signature_message())
            ),
            "state": self.state.value,
            "owner_scope_coordinates_included": False,
            "project_scope_coordinates_included": False,
            "reviewer_coordinates_included": False,
            "raw_media_included": False,
            "text_body_included": False,
            "absolute_host_path_included": False,
            "credential_included": False,
            "signature_bytes_included": False,
            "public_key_material_included": False,
            "private_key_material_included": False,
            "key_store_accessed": False,
            "signature_present": False,
            "signature_verified": False,
            "latest_source_revalidation_required": True,
            "external_cryptographic_verification_required": True,
            "in_memory_request_only": True,
            "knowledge_pack_write_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "automatic_promotion_authorized": False,
            "runtime_profile_apply_authorized": False,
            "rollback_execution_authorized": False,
            "release_authorized": False,
            "external_effect_authorized": False,
        }
        body["signature_request_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "KnowledgePackSignatureVerificationRequest":
        expected = {
            "request_version", "record_type", "task_owner", "compatibility_contract",
            "signature_message_contract", "signature_input_contract", "request_id",
            "signing_candidate_id",
            "signing_candidate_sha256", "pack_id", "pack_version",
            "predecessor_pack_sha256", "trusted_signer_policy_sha256",
            "signer_key_id_sha256", "signature_algorithm", "signature_message_sha256",
            "state", "owner_scope_coordinates_included",
            "project_scope_coordinates_included", "reviewer_coordinates_included",
            "raw_media_included", "text_body_included", "absolute_host_path_included",
            "credential_included", "signature_bytes_included",
            "public_key_material_included", "private_key_material_included",
            "key_store_accessed", "signature_present", "signature_verified",
            "latest_source_revalidation_required",
            "external_cryptographic_verification_required", "in_memory_request_only",
            "knowledge_pack_write_authorized", "knowledge_pack_promotion_authorized",
            "automatic_promotion_authorized", "runtime_profile_apply_authorized",
            "rollback_execution_authorized", "release_authorized",
            "external_effect_authorized", "signature_request_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("signature request fields are incomplete or unknown")
        if (
            value["request_version"], value["record_type"], value["task_owner"],
            value["compatibility_contract"], value["signature_message_contract"],
            value["signature_input_contract"],
        ) != (
            KNOWLEDGE_PACK_SIGNATURE_REQUEST_VERSION,
            "KNOWLEDGE_PACK_SIGNATURE_VERIFICATION_REQUEST",
            "TASK-029",
            KNOWLEDGE_PACK_COMPATIBILITY_CONTRACT,
            KNOWLEDGE_PACK_SIGNATURE_MESSAGE_CONTRACT,
            KNOWLEDGE_PACK_SIGNATURE_INPUT_CONTRACT,
        ):
            raise ValueError("signature request identity mismatch")
        false_fields = (
            "owner_scope_coordinates_included", "project_scope_coordinates_included",
            "reviewer_coordinates_included", "raw_media_included", "text_body_included",
            "absolute_host_path_included", "credential_included", "signature_bytes_included",
            "public_key_material_included", "private_key_material_included",
            "key_store_accessed", "signature_present", "signature_verified",
            "knowledge_pack_write_authorized", "knowledge_pack_promotion_authorized",
            "automatic_promotion_authorized", "runtime_profile_apply_authorized",
            "rollback_execution_authorized", "release_authorized",
            "external_effect_authorized",
        )
        for field in false_fields:
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        for field in (
            "latest_source_revalidation_required",
            "external_cryptographic_verification_required",
            "in_memory_request_only",
        ):
            if value[field] is not True:
                raise ValueError(f"{field} must remain true")
        result = cls(
            value["request_id"], value["signing_candidate_id"],
            value["signing_candidate_sha256"], value["pack_id"], value["pack_version"],
            value["predecessor_pack_sha256"], value["trusted_signer_policy_sha256"],
            value["signer_key_id_sha256"],
            KnowledgePackSignatureAlgorithm(value["signature_algorithm"]),
            KnowledgePackSignatureRequestState(value["state"]),
        )
        if result.to_dict() != dict(value):
            raise ValueError("signature request hash mismatch")
        return result


def compile_knowledge_pack_signature_verification_request(
    *, request_id: str, source_signing_candidate_payload: Mapping[str, Any],
    signing_candidate_compile_kwargs: Mapping[str, Any],
    trusted_signer_policy_sha256: str, signer_key_id_sha256: str,
    signature_algorithm: KnowledgePackSignatureAlgorithm,
) -> KnowledgePackSignatureVerificationRequest:
    """Recompile exact R7 and create a no-key, no-signature external verification request."""
    if not isinstance(signing_candidate_compile_kwargs, Mapping):
        raise ValueError("signing_candidate_compile_kwargs must be a mapping")
    current = compile_knowledge_pack_signing_candidate(
        **dict(signing_candidate_compile_kwargs)
    )
    current_payload = current.to_dict()
    if (
        not isinstance(source_signing_candidate_payload, Mapping)
        or dict(source_signing_candidate_payload) != current_payload
    ):
        raise ValueError("signing candidate does not match exact current sources and reviews")
    if current.state is not KnowledgePackSigningState.READY_FOR_EXTERNAL_SIGNATURE:
        raise ValueError("signing candidate is not ready for an external signature request")
    return KnowledgePackSignatureVerificationRequest(
        request_id,
        current.signing_candidate_id,
        current_payload["signing_candidate_sha256"],
        current.pack_id,
        current.pack_version,
        current.predecessor_pack_sha256,
        trusted_signer_policy_sha256,
        signer_key_id_sha256,
        signature_algorithm,
    )


def verify_knowledge_pack_signature_verification_request(
    payload: Mapping[str, Any], **compile_kwargs: Any,
) -> None:
    expected = compile_knowledge_pack_signature_verification_request(
        **compile_kwargs
    ).to_dict()
    if not isinstance(payload, Mapping) or dict(payload) != expected:
        raise ValueError("signature request does not match exact current sources and policy")


__all__ = [
    "KNOWLEDGE_PACK_SIGNATURE_MESSAGE_CONTRACT",
    "KNOWLEDGE_PACK_SIGNATURE_INPUT_CONTRACT",
    "KNOWLEDGE_PACK_SIGNATURE_REQUEST_VERSION",
    "KnowledgePackSignatureAlgorithm",
    "KnowledgePackSignatureRequestState",
    "KnowledgePackSignatureVerificationRequest",
    "compile_knowledge_pack_signature_verification_request",
    "verify_knowledge_pack_signature_verification_request",
]
