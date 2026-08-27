"""Body-free request for a later trusted Human signature-artifact custody decision.

This module deliberately does not authenticate a Human, read the R10D store, or
authorize custody.  It only freezes and validates an exact public R10D receipt
and produces a short-lived, non-authoritative request for a trusted interaction
boundary implemented by a later Unit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import re

from ai_video_production.knowledge_pack_signature_artifact_custody_store import (
    SIGNATURE_ARTIFACT_CUSTODY_CONTRACT,
    SIGNATURE_ARTIFACT_DPAPI_CIPHER_SUITE,
    SIGNATURE_ARTIFACT_PATH_SECURITY_MODEL,
    SignatureArtifactCustodyReceipt,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


SIGNATURE_ARTIFACT_CUSTODY_CONFIRMATION_REQUEST_VERSION = "1.0.0"
SIGNATURE_ARTIFACT_CUSTODY_CONFIRMATION_REQUEST_CONTRACT = (
    "TASK-029/SIGNATURE_ARTIFACT_CUSTODY_CONFIRMATION_REQUEST/1.0.0"
)
SIGNATURE_ARTIFACT_CUSTODY_CONFIRMATION_REQUEST_STATE = (
    "AWAITING_TRUSTED_HUMAN_CUSTODY_CONFIRMATION"
)
MAX_CONFIRMATION_REQUEST_TTL_MS = 15 * 60 * 1000

_LOGICAL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}")
_STABLE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}")
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
_SEMVER = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")

_FALSE_AUTHORITY_AND_EFFECT_FLAGS = (
    "standalone_request_authoritative",
    "source_store_origin_authenticated",
    "production_dpapi_storage_origin_authenticated",
    "trusted_clock_verified",
    "request_currently_fresh_verified",
    "trusted_human_confirmation_received",
    "human_confirmation_origin_authenticated",
    "one_shot_confirmation_enforced",
    "custody_promotion_authorized",
    "staging_delete_authorized",
    "owner_local_path_verified",
    "canonical_store_path_binding_confirmed",
    "canonical_custody_write_authorized",
    "canonical_custody_receipt_minted",
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


def _logical_id(value: object, field: str) -> str:
    if type(value) is not str or _LOGICAL_ID.fullmatch(value) is None:
        raise ValueError(f"{field} must be an exact logical identifier")
    return value


def _stable_id(value: object, field: str) -> str:
    if type(value) is not str or _STABLE_ID.fullmatch(value) is None:
        raise ValueError(f"{field} must be an exact stable identifier")
    return value


def _sha(value: object, field: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{field} must be an exact sha256 value")
    return value


def _positive(value: object, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field} must be an exact positive integer")
    return value


def _snapshot_json_value(
    value: object,
    *,
    field: str,
    depth: int = 0,
    budget: list[int] | None = None,
) -> Any:
    if budget is None:
        budget = [256]
    budget[0] -= 1
    if budget[0] < 0:
        raise ValueError(f"{field} exceeds the JSON node budget")
    if depth > 4:
        raise ValueError(f"{field} exceeds the JSON depth limit")
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is list:
        return [
            _snapshot_json_value(item, field=field, depth=depth + 1, budget=budget)
            for item in value
        ]
    if type(value) is dict:
        result: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"{field} keys must be exact strings")
            result[key] = _snapshot_json_value(
                item, field=field, depth=depth + 1, budget=budget
            )
        return result
    raise ValueError(f"{field} must contain exact built-in JSON values")


def _snapshot_json_object(value: object, field: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{field} must be an exact built-in dictionary")
    snapshot = _snapshot_json_value(value, field=field)
    if type(snapshot) is not dict:  # defensive; the entry gate already enforces it
        raise ValueError(f"{field} must be an exact built-in dictionary")
    return snapshot


@dataclass(frozen=True, slots=True)
class SignatureArtifactCustodyConfirmationRequest:
    request_id: str
    custody_receipt_id: str
    custody_receipt_sha256: str
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
    intent_attestation_sha256: str
    staged_at_epoch_ms: int
    requested_at_epoch_ms: int
    expires_at_epoch_ms: int

    def __post_init__(self) -> None:
        _logical_id(self.request_id, "request_id")
        _logical_id(self.custody_receipt_id, "custody_receipt_id")
        _logical_id(self.artifact_store_id, "artifact_store_id")
        _stable_id(self.pack_id, "pack_id")
        if type(self.pack_version) is not str or _SEMVER.fullmatch(self.pack_version) is None:
            raise ValueError("pack_version must be an exact semantic version")
        for field in (
            "custody_receipt_sha256",
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
            "intent_attestation_sha256",
        ):
            _sha(getattr(self, field), field)
        if self.predecessor_pack_sha256 is not None:
            _sha(self.predecessor_pack_sha256, "predecessor_pack_sha256")
        _positive(self.staged_at_epoch_ms, "staged_at_epoch_ms")
        _positive(self.requested_at_epoch_ms, "requested_at_epoch_ms")
        _positive(self.expires_at_epoch_ms, "expires_at_epoch_ms")
        if self.requested_at_epoch_ms < self.staged_at_epoch_ms:
            raise ValueError("confirmation request cannot predate encrypted staging")
        if self.expires_at_epoch_ms <= self.requested_at_epoch_ms:
            raise ValueError("confirmation request expiry must follow request creation")
        if self.expires_at_epoch_ms - self.requested_at_epoch_ms > MAX_CONFIRMATION_REQUEST_TTL_MS:
            raise ValueError("confirmation request exceeds the bounded TTL")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "request_version": SIGNATURE_ARTIFACT_CUSTODY_CONFIRMATION_REQUEST_VERSION,
            "record_type": "SIGNATURE_ARTIFACT_CUSTODY_CONFIRMATION_REQUEST",
            "task_owner": "TASK-029",
            "request_id": self.request_id,
            "custody_receipt_id": self.custody_receipt_id,
            "custody_receipt_sha256": self.custody_receipt_sha256,
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
            "intent_attestation_sha256": self.intent_attestation_sha256,
            "staged_at_epoch_ms": self.staged_at_epoch_ms,
            "requested_at_epoch_ms": self.requested_at_epoch_ms,
            "expires_at_epoch_ms": self.expires_at_epoch_ms,
            "source_custody_contract": SIGNATURE_ARTIFACT_CUSTODY_CONTRACT,
            "confirmation_request_contract": SIGNATURE_ARTIFACT_CUSTODY_CONFIRMATION_REQUEST_CONTRACT,
            "state": SIGNATURE_ARTIFACT_CUSTODY_CONFIRMATION_REQUEST_STATE,
            "path_security_model": SIGNATURE_ARTIFACT_PATH_SECURITY_MODEL,
            "source_receipt_self_hash_required_by_compiler": True,
            "source_receipt_self_hash_revalidated": False,
            "source_receipt_publicly_constructible": True,
            "production_dpapi_receipt_claim_required": True,
            "encrypted_staging_body_read": False,
            "post_write_storage_reverified": False,
            "human_interaction_channel_required": True,
            "trusted_human_confirmation_required": True,
            "body_free_request": True,
            "signature_artifact_body_included": False,
            "public_key_material_included": False,
            "private_key_material_included": False,
            "absolute_host_path_included": False,
            "credential_included": False,
            **{field: False for field in _FALSE_AUTHORITY_AND_EFFECT_FLAGS},
        }
        body["confirmation_request_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any]
    ) -> "SignatureArtifactCustodyConfirmationRequest":
        snapshot = _snapshot_json_object(value, "signature_artifact_custody_confirmation_request")
        result = cls(
            snapshot["request_id"],
            snapshot["custody_receipt_id"],
            snapshot["custody_receipt_sha256"],
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
            snapshot["intent_attestation_sha256"],
            snapshot["staged_at_epoch_ms"],
            snapshot["requested_at_epoch_ms"],
            snapshot["expires_at_epoch_ms"],
        )
        if result.to_dict() != snapshot:
            raise ValueError("signature artifact custody confirmation request identity mismatch")
        return result


def compile_signature_artifact_custody_confirmation_request(
    *,
    request_id: str,
    custody_receipt_payload: Mapping[str, Any],
    requested_at_epoch_ms: int,
    expires_at_epoch_ms: int,
) -> SignatureArtifactCustodyConfirmationRequest:
    _logical_id(request_id, "request_id")
    _positive(requested_at_epoch_ms, "requested_at_epoch_ms")
    _positive(expires_at_epoch_ms, "expires_at_epoch_ms")
    receipt_snapshot = _snapshot_json_object(
        custody_receipt_payload, "custody_receipt_payload"
    )
    receipt = SignatureArtifactCustodyReceipt.from_dict(receipt_snapshot)
    receipt_body = receipt.to_dict()
    if receipt_body != receipt_snapshot:
        raise ValueError("R10D custody receipt changed during exact read-back")
    if not receipt.production_dpapi_cipher_verified:
        raise ValueError("trusted Human confirmation requires a production DPAPI receipt claim")
    if receipt.cipher_suite != SIGNATURE_ARTIFACT_DPAPI_CIPHER_SUITE:
        raise ValueError("trusted Human confirmation requires the exact R10D DPAPI suite")
    if receipt_body["state"] != "SIGNATURE_ARTIFACT_STAGED_AWAITING_TRUSTED_HUMAN_CONFIRMATION":
        raise ValueError("R10D receipt is not awaiting trusted Human confirmation")
    if receipt_body["encrypted_artifact_staging_write_completed"] is not True:
        raise ValueError("R10D encrypted staging is not complete")
    if receipt_body["post_write_readback_verified"] is not True:
        raise ValueError("R10D post-write read-back is not verified")
    if receipt_body["signature_artifact_custody_confirmed"] is not False:
        raise ValueError("R10D receipt already claims custody confirmation")
    return SignatureArtifactCustodyConfirmationRequest(
        request_id=request_id,
        custody_receipt_id=receipt.receipt_id,
        custody_receipt_sha256=receipt_body["custody_receipt_sha256"],
        candidate_sha256=receipt.candidate_sha256,
        artifact_store_id=receipt.artifact_store_id,
        owner_scope_sha256=receipt.owner_scope_sha256,
        source_key_custody_receipt_sha256=receipt.source_key_custody_receipt_sha256,
        source_signing_ceremony_receipt_sha256=receipt.source_signing_ceremony_receipt_sha256,
        source_trusted_signature_admission_sha256=receipt.source_trusted_signature_admission_sha256,
        pack_id=receipt.pack_id,
        pack_version=receipt.pack_version,
        predecessor_pack_sha256=receipt.predecessor_pack_sha256,
        signature_request_sha256=receipt.signature_request_sha256,
        signature_message_sha256=receipt.signature_message_sha256,
        trusted_signer_policy_sha256=receipt.trusted_signer_policy_sha256,
        signer_key_id_sha256=receipt.signer_key_id_sha256,
        detached_signature_sha256=receipt.detached_signature_sha256,
        verification_receipt_sha256=receipt.verification_receipt_sha256,
        intent_attestation_sha256=receipt.intent_attestation_sha256,
        staged_at_epoch_ms=receipt.stored_at_epoch_ms,
        requested_at_epoch_ms=requested_at_epoch_ms,
        expires_at_epoch_ms=expires_at_epoch_ms,
    )


def verify_signature_artifact_custody_confirmation_request(
    value: Mapping[str, Any],
) -> SignatureArtifactCustodyConfirmationRequest:
    return SignatureArtifactCustodyConfirmationRequest.from_dict(value)


__all__ = [
    "MAX_CONFIRMATION_REQUEST_TTL_MS",
    "SIGNATURE_ARTIFACT_CUSTODY_CONFIRMATION_REQUEST_CONTRACT",
    "SIGNATURE_ARTIFACT_CUSTODY_CONFIRMATION_REQUEST_STATE",
    "SIGNATURE_ARTIFACT_CUSTODY_CONFIRMATION_REQUEST_VERSION",
    "SignatureArtifactCustodyConfirmationRequest",
    "compile_signature_artifact_custody_confirmation_request",
    "verify_signature_artifact_custody_confirmation_request",
]
