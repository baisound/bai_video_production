"""TASK-029 R10C body-free signature-artifact custody candidate.

The candidate binds exact R9B, R9C, and R10B receipt coordinates for a later
Owner-local custody transaction.  It stores no key or signature body and
grants no write, promotion, runtime, release, or external-effect authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Mapping

from .knowledge_pack_local_signing_ceremony import LocalSigningCeremonyReceipt
from .knowledge_pack_trusted_signature_admission import (
    KnowledgePackTrustedSignatureAdmission,
    KnowledgePackTrustedSignatureAdmissionState,
)
from .owner_signing_key_custody import OwnerSigningKeyCustodyReceipt
from .serialization import canonical_json_bytes, sha256_bytes


SIGNATURE_ARTIFACT_CUSTODY_CANDIDATE_VERSION = "1.0.0"
SIGNATURE_ARTIFACT_CUSTODY_CONTRACT = "TASK-029/SIGNATURE_ARTIFACT_CUSTODY/1.0.0"
_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_MAX_DEPTH = 16
_MAX_NODES = 4096


def _id(value: object, field: str) -> str:
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise ValueError(f"{field} is invalid")
    return value


def _sha(value: object, field: str) -> str:
    if type(value) is not str or _SHA.fullmatch(value) is None:
        raise ValueError(f"{field} must be sha256:<64 lowercase hex>")
    return value


def _positive(value: object, field: str) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{field} must be an exact positive integer")
    return value


def _snapshot_json_object(value: object, field: str) -> dict[str, Any]:
    """Create one hook-free exact JSON snapshot or reject before any hook read."""

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


class SignatureArtifactCustodyCandidateState(str, Enum):
    READY_FOR_EXPLICIT_HUMAN_CUSTODY_CONFIRMATION = (
        "READY_FOR_EXPLICIT_HUMAN_CUSTODY_CONFIRMATION"
    )


@dataclass(frozen=True, slots=True)
class SignatureArtifactCustodyCandidate:
    candidate_id: str
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
    created_at_epoch_ms: int
    state: SignatureArtifactCustodyCandidateState = (
        SignatureArtifactCustodyCandidateState.READY_FOR_EXPLICIT_HUMAN_CUSTODY_CONFIRMATION
    )

    def __post_init__(self) -> None:
        for field in ("candidate_id", "artifact_store_id", "pack_id"):
            _id(getattr(self, field), field)
        if type(self.pack_version) is not str or _SEMVER.fullmatch(self.pack_version) is None:
            raise ValueError("pack_version must be semantic version x.y.z")
        for field in (
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
        ):
            _sha(getattr(self, field), field)
        if self.predecessor_pack_sha256 is not None:
            _sha(self.predecessor_pack_sha256, "predecessor_pack_sha256")
        _positive(self.created_at_epoch_ms, "created_at_epoch_ms")
        if type(self.state) is not SignatureArtifactCustodyCandidateState:
            raise ValueError("state must be a SignatureArtifactCustodyCandidateState")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "candidate_version": SIGNATURE_ARTIFACT_CUSTODY_CANDIDATE_VERSION,
            "record_type": "KNOWLEDGE_PACK_SIGNATURE_ARTIFACT_CUSTODY_CANDIDATE",
            "task_owner": "TASK-029",
            "candidate_id": self.candidate_id,
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
            "r9b_r9c_r10b_receipts_self_validated": True,
            "owner_scope_sourced_from_r9b_receipt": True,
            "verification_receipt_sha256": self.verification_receipt_sha256,
            "created_at_epoch_ms": self.created_at_epoch_ms,
            "custody_contract": SIGNATURE_ARTIFACT_CUSTODY_CONTRACT,
            "state": self.state.value,
            "r10b_direct_recompile_required_at_write": True,
            "transient_public_key_required_at_write": True,
            "transient_detached_signature_required_at_write": True,
            "cryptographic_reverification_required_at_write": True,
            "owner_local_encrypted_store_required": True,
            "one_shot_artifact_write_required": True,
            "explicit_human_custody_confirmation_required": True,
            "in_memory_candidate_only": True,
            "owner_scope_coordinates_included": True,
            "project_scope_coordinates_included": False,
            "reviewer_coordinates_included": False,
            "signature_artifact_body_included": False,
            "public_key_material_included": False,
            "private_key_material_included": False,
            "absolute_host_path_included": False,
            "source_graph_currentness_confirmed": False,
            "owner_scope_origin_authenticated": False,
            "credential_included": False,
            "artifact_custody_write_authorized": False,
            "signature_artifact_custody_confirmed": False,
            "canonical_receipt_minted": False,
            "canonical_trust_root_confirmed": False,
            "owner_signer_binding_confirmed": False,
            "knowledge_pack_write_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "automatic_promotion_authorized": False,
            "runtime_profile_apply_authorized": False,
            "rollback_execution_authorized": False,
            "release_authorized": False,
            "external_effect_authorized": False,
        }
        body["custody_candidate_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SignatureArtifactCustodyCandidate":
        snapshot = _snapshot_json_object(value, "signature_artifact_custody_candidate")
        expected = set(
            cls(
                "candidate", "store", "sha256:" + "0" * 64,
                "sha256:" + "0" * 64, "sha256:" + "0" * 64,
                "sha256:" + "0" * 64, "pack", "1.0.0", None,
                "sha256:" + "0" * 64, "sha256:" + "0" * 64,
                "sha256:" + "0" * 64, "sha256:" + "0" * 64,
                "sha256:" + "0" * 64, "sha256:" + "0" * 64, 1,
            ).to_dict()
        )
        if set(snapshot) != expected:
            raise ValueError("custody candidate fields are incomplete or unknown")
        if (
            snapshot["candidate_version"], snapshot["record_type"],
            snapshot["task_owner"], snapshot["custody_contract"], snapshot["state"],
        ) != (
            SIGNATURE_ARTIFACT_CUSTODY_CANDIDATE_VERSION,
            "KNOWLEDGE_PACK_SIGNATURE_ARTIFACT_CUSTODY_CANDIDATE", "TASK-029",
            SIGNATURE_ARTIFACT_CUSTODY_CONTRACT,
            SignatureArtifactCustodyCandidateState.READY_FOR_EXPLICIT_HUMAN_CUSTODY_CONFIRMATION.value,
        ):
            raise ValueError("custody candidate identity mismatch")
        for field in (
            "r10b_direct_recompile_required_at_write",
            "transient_public_key_required_at_write",
            "transient_detached_signature_required_at_write",
            "cryptographic_reverification_required_at_write",
            "owner_local_encrypted_store_required",
            "one_shot_artifact_write_required",
            "explicit_human_custody_confirmation_required",
            "r9b_r9c_r10b_receipts_self_validated",
            "owner_scope_sourced_from_r9b_receipt",
            "in_memory_candidate_only",
            "owner_scope_coordinates_included",
        ):
            if snapshot[field] is not True:
                raise ValueError(f"{field} must remain true")
        for field in (
            "project_scope_coordinates_included", "reviewer_coordinates_included",
            "signature_artifact_body_included", "public_key_material_included",
            "private_key_material_included", "absolute_host_path_included",
            "credential_included", "artifact_custody_write_authorized",
            "signature_artifact_custody_confirmed", "canonical_receipt_minted",
            "canonical_trust_root_confirmed", "owner_signer_binding_confirmed",
            "knowledge_pack_write_authorized", "knowledge_pack_promotion_authorized",
            "source_graph_currentness_confirmed", "owner_scope_origin_authenticated",
            "automatic_promotion_authorized", "runtime_profile_apply_authorized",
            "rollback_execution_authorized", "release_authorized",
            "external_effect_authorized",
        ):
            if snapshot[field] is not False:
                raise ValueError(f"{field} must remain false")
        result = cls(
            snapshot["candidate_id"], snapshot["artifact_store_id"],
            snapshot["owner_scope_sha256"], snapshot["source_key_custody_receipt_sha256"],
            snapshot["source_signing_ceremony_receipt_sha256"],
            snapshot["source_trusted_signature_admission_sha256"], snapshot["pack_id"],
            snapshot["pack_version"], snapshot["predecessor_pack_sha256"],
            snapshot["signature_request_sha256"], snapshot["signature_message_sha256"],
            snapshot["trusted_signer_policy_sha256"], snapshot["signer_key_id_sha256"],
            snapshot["detached_signature_sha256"], snapshot["verification_receipt_sha256"],
            snapshot["created_at_epoch_ms"],
            SignatureArtifactCustodyCandidateState(snapshot["state"]),
        )
        if result.to_dict() != snapshot:
            raise ValueError("custody candidate hash mismatch")
        return result


def compile_signature_artifact_custody_candidate(
    *, candidate_id: str, artifact_store_id: str,
    key_custody_receipt_payload: Mapping[str, Any],
    signing_ceremony_receipt_payload: Mapping[str, Any],
    trusted_signature_admission_payload: Mapping[str, Any],
    created_at_epoch_ms: int,
) -> SignatureArtifactCustodyCandidate:
    """Compile a no-write custody candidate from exact body-free R9B/R9C/R10B receipts."""

    _id(candidate_id, "candidate_id")
    _id(artifact_store_id, "artifact_store_id")
    _positive(created_at_epoch_ms, "created_at_epoch_ms")
    custody = OwnerSigningKeyCustodyReceipt.from_dict(
        _snapshot_json_object(key_custody_receipt_payload, "key_custody_receipt_payload")
    )
    ceremony = LocalSigningCeremonyReceipt.from_dict(
        _snapshot_json_object(signing_ceremony_receipt_payload, "signing_ceremony_receipt_payload")
    )
    admission = KnowledgePackTrustedSignatureAdmission.from_dict(
        _snapshot_json_object(trusted_signature_admission_payload, "trusted_signature_admission_payload")
    )
    custody_payload = custody.to_dict()
    ceremony_payload = ceremony.to_dict()
    admission_payload = admission.to_dict()
    if admission.state is not KnowledgePackTrustedSignatureAdmissionState.READY_FOR_INITIAL_SIGNATURE_ARTIFACT_CUSTODY:
        raise ValueError("trusted signature admission is not ready for artifact custody")
    if ceremony.custody_receipt_sha256 != custody_payload["custody_receipt_sha256"]:
        raise ValueError("signing ceremony does not bind the exact key custody receipt")
    coordinates = (
        ceremony_payload["ceremony_receipt_sha256"], ceremony.signature_request_sha256,
        ceremony.signer_key_id_sha256, ceremony.detached_signature_sha256,
        ceremony.verification_receipt_sha256,
    )
    expected = (
        admission.signing_ceremony_receipt_sha256, admission.signature_request_sha256,
        admission.signer_key_id_sha256, admission.detached_signature_sha256,
        admission.verification_receipt_sha256,
    )
    if coordinates != expected:
        raise ValueError("R9C ceremony does not match the exact R10B admission")
    if custody.signer_key_id_sha256 != admission.signer_key_id_sha256:
        raise ValueError("Owner key custody signer does not match R10B")
    if created_at_epoch_ms < max(
        custody.custodied_at_epoch_ms, ceremony.completed_at_epoch_ms,
        admission.verified_at_epoch_ms,
    ):
        raise ValueError("custody candidate time precedes its exact source Evidence")
    return SignatureArtifactCustodyCandidate(
        candidate_id, artifact_store_id, custody.owner_scope_sha256,
        custody_payload["custody_receipt_sha256"],
        ceremony_payload["ceremony_receipt_sha256"],
        admission_payload["trusted_signature_admission_sha256"], admission.pack_id,
        admission.pack_version, admission.predecessor_pack_sha256,
        admission.signature_request_sha256, admission.signature_message_sha256,
        admission.trusted_signer_policy_sha256, admission.signer_key_id_sha256,
        admission.detached_signature_sha256, admission.verification_receipt_sha256,
        created_at_epoch_ms,
    )


def verify_signature_artifact_custody_candidate(
    payload: Mapping[str, Any], **compile_kwargs: Any,
) -> None:
    snapshot = _snapshot_json_object(payload, "signature_artifact_custody_candidate")
    expected = compile_signature_artifact_custody_candidate(**compile_kwargs).to_dict()
    if snapshot != expected:
        raise ValueError("custody candidate does not match exact current Evidence")


__all__ = [
    "SIGNATURE_ARTIFACT_CUSTODY_CANDIDATE_VERSION",
    "SIGNATURE_ARTIFACT_CUSTODY_CONTRACT",
    "SignatureArtifactCustodyCandidate",
    "SignatureArtifactCustodyCandidateState",
    "compile_signature_artifact_custody_candidate",
    "verify_signature_artifact_custody_candidate",
]
