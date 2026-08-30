"""TASK-029 R10A body-free Knowledge Pack promotion intent.

This module recompiles the exact R8 request (and therefore its R6/R7 inputs),
then cross-binds body-free R9A and terminal R9D receipts.  It performs no I/O,
does not accept key or signature bodies, and grants no promotion effect.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Mapping

from .knowledge_pack_durable_signing_journal import (
    DurableSigningJournalReceipt,
    DurableSigningJournalState,
)
from .knowledge_pack_signature_request import (
    KNOWLEDGE_PACK_COMPATIBILITY_CONTRACT,
    KnowledgePackSignatureVerificationRequest,
    verify_knowledge_pack_signature_verification_request,
)
from .knowledge_pack_signature_verification import (
    KnowledgePackSignatureVerificationReceipt,
)
from .serialization import canonical_json_bytes, sha256_bytes


KNOWLEDGE_PACK_PROMOTION_INTENT_VERSION = "1.0.0"
KNOWLEDGE_PACK_PROMOTION_INTENT_CONTRACT = (
    "TASK-029/KNOWLEDGE_PACK/PROMOTION_INTENT/1.0.0"
)
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def _id(value: object, field: str) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise ValueError(f"{field} must be a stable identifier")
    return value


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase sha256 coordinate")
    return value


def _positive(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{field} must be an integer >= 1")
    return value


def _freeze_signature_request_payload(
    value: Mapping[str, Any],
) -> dict[str, str | bool | None]:
    """Take one hook-free snapshot before any verification reads."""

    if type(value) is not dict:
        raise ValueError("signature_request_payload must be an exact built-in dict")
    snapshot = value.copy()
    if any(type(key) is not str for key in snapshot):
        raise ValueError("signature_request_payload keys must be exact strings")
    if any(
        item is not None and type(item) not in (str, bool)
        for item in snapshot.values()
    ):
        raise ValueError("signature_request_payload values must be exact primitives")
    return snapshot


class KnowledgePackPromotionIntentState(str, Enum):
    READY_FOR_INITIAL_PROMOTION_PREFLIGHT = (
        "READY_FOR_INITIAL_PROMOTION_PREFLIGHT"
    )
    READY_FOR_REPLACEMENT_PROMOTION_PREFLIGHT = (
        "READY_FOR_REPLACEMENT_PROMOTION_PREFLIGHT"
    )


@dataclass(frozen=True, slots=True)
class KnowledgePackPromotionIntent:
    intent_id: str
    pack_id: str
    pack_version: str
    predecessor_pack_sha256: str | None
    rollback_target_pack_sha256: str | None
    signing_candidate_sha256: str
    signature_request_sha256: str
    signature_message_sha256: str
    trusted_signer_policy_sha256: str
    signer_key_id_sha256: str
    detached_signature_sha256: str
    verification_receipt_sha256: str
    signing_journal_receipt_sha256: str
    signing_ceremony_receipt_sha256: str
    created_at_epoch_ms: int
    state: KnowledgePackPromotionIntentState

    def __post_init__(self) -> None:
        for field in ("intent_id", "pack_id"):
            _id(getattr(self, field), field)
        if not isinstance(self.pack_version, str) or _SEMVER.fullmatch(self.pack_version) is None:
            raise ValueError("pack_version must be semantic version x.y.z")
        for field in (
            "signing_candidate_sha256",
            "signature_request_sha256",
            "signature_message_sha256",
            "trusted_signer_policy_sha256",
            "signer_key_id_sha256",
            "detached_signature_sha256",
            "verification_receipt_sha256",
            "signing_journal_receipt_sha256",
            "signing_ceremony_receipt_sha256",
        ):
            _sha(getattr(self, field), field)
        if self.predecessor_pack_sha256 is not None:
            _sha(self.predecessor_pack_sha256, "predecessor_pack_sha256")
        if self.rollback_target_pack_sha256 is not None:
            _sha(self.rollback_target_pack_sha256, "rollback_target_pack_sha256")
        _positive(self.created_at_epoch_ms, "created_at_epoch_ms")
        if not isinstance(self.state, KnowledgePackPromotionIntentState):
            raise ValueError("state must be a KnowledgePackPromotionIntentState")
        expected_state = (
            KnowledgePackPromotionIntentState.READY_FOR_INITIAL_PROMOTION_PREFLIGHT
            if self.predecessor_pack_sha256 is None
            else KnowledgePackPromotionIntentState.READY_FOR_REPLACEMENT_PROMOTION_PREFLIGHT
        )
        if self.state is not expected_state:
            raise ValueError("promotion intent state does not match predecessor presence")
        if self.rollback_target_pack_sha256 != self.predecessor_pack_sha256:
            raise ValueError("rollback target must equal the exact predecessor pack")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "intent_version": KNOWLEDGE_PACK_PROMOTION_INTENT_VERSION,
            "record_type": "KNOWLEDGE_PACK_PROMOTION_INTENT",
            "task_owner": "TASK-029",
            "intent_contract": KNOWLEDGE_PACK_PROMOTION_INTENT_CONTRACT,
            "compatibility_contract": KNOWLEDGE_PACK_COMPATIBILITY_CONTRACT,
            "intent_id": self.intent_id,
            "pack_id": self.pack_id,
            "pack_version": self.pack_version,
            "predecessor_pack_sha256": self.predecessor_pack_sha256,
            "rollback_target_pack_sha256": self.rollback_target_pack_sha256,
            "signing_candidate_sha256": self.signing_candidate_sha256,
            "signature_request_sha256": self.signature_request_sha256,
            "signature_message_sha256": self.signature_message_sha256,
            "trusted_signer_policy_sha256": self.trusted_signer_policy_sha256,
            "signer_key_id_sha256": self.signer_key_id_sha256,
            "detached_signature_sha256": self.detached_signature_sha256,
            "verification_receipt_sha256": self.verification_receipt_sha256,
            "signing_journal_receipt_sha256": self.signing_journal_receipt_sha256,
            "signing_ceremony_receipt_sha256": self.signing_ceremony_receipt_sha256,
            "created_at_epoch_ms": self.created_at_epoch_ms,
            "state": self.state.value,
            "latest_source_revalidated": True,
            "upstream_signature_verification_claim_present": True,
            "signature_origin_authenticated": False,
            "signature_verified": False,
            "promotion_confirmation_eligible": False,
            "explicit_human_promotion_confirmation_required": True,
            "canonical_store_transaction_required": True,
            "runtime_compatibility_validation_required": True,
            "signature_artifact_required": True,
            "signature_artifact_present": False,
            "promotion_execution_blocked_until_signature_artifact": True,
            "rollback_plan_required": self.predecessor_pack_sha256 is not None,
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
            "in_memory_intent_only": True,
            "knowledge_pack_write_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "automatic_promotion_authorized": False,
            "runtime_profile_apply_authorized": False,
            "rollback_execution_authorized": False,
            "release_authorized": False,
            "external_effect_authorized": False,
        }
        body["promotion_intent_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "KnowledgePackPromotionIntent":
        if not isinstance(value, Mapping):
            raise ValueError("promotion intent must be a mapping")
        expected = set(cls(
            intent_id="shape",
            pack_id="shape",
            pack_version="0.0.0",
            predecessor_pack_sha256=None,
            rollback_target_pack_sha256=None,
            signing_candidate_sha256="sha256:" + "0" * 64,
            signature_request_sha256="sha256:" + "0" * 64,
            signature_message_sha256="sha256:" + "0" * 64,
            trusted_signer_policy_sha256="sha256:" + "0" * 64,
            signer_key_id_sha256="sha256:" + "0" * 64,
            detached_signature_sha256="sha256:" + "0" * 64,
            verification_receipt_sha256="sha256:" + "0" * 64,
            signing_journal_receipt_sha256="sha256:" + "0" * 64,
            signing_ceremony_receipt_sha256="sha256:" + "0" * 64,
            created_at_epoch_ms=1,
            state=KnowledgePackPromotionIntentState.READY_FOR_INITIAL_PROMOTION_PREFLIGHT,
        ).to_dict())
        if set(value) != expected:
            raise ValueError("promotion intent fields are incomplete or unknown")
        result = cls(
            intent_id=value["intent_id"],
            pack_id=value["pack_id"],
            pack_version=value["pack_version"],
            predecessor_pack_sha256=value["predecessor_pack_sha256"],
            rollback_target_pack_sha256=value["rollback_target_pack_sha256"],
            signing_candidate_sha256=value["signing_candidate_sha256"],
            signature_request_sha256=value["signature_request_sha256"],
            signature_message_sha256=value["signature_message_sha256"],
            trusted_signer_policy_sha256=value["trusted_signer_policy_sha256"],
            signer_key_id_sha256=value["signer_key_id_sha256"],
            detached_signature_sha256=value["detached_signature_sha256"],
            verification_receipt_sha256=value["verification_receipt_sha256"],
            signing_journal_receipt_sha256=value["signing_journal_receipt_sha256"],
            signing_ceremony_receipt_sha256=value["signing_ceremony_receipt_sha256"],
            created_at_epoch_ms=value["created_at_epoch_ms"],
            state=KnowledgePackPromotionIntentState(value["state"]),
        )
        if result.to_dict() != dict(value):
            raise ValueError("promotion intent identity, flags, or hash mismatch")
        return result


def compile_knowledge_pack_promotion_intent(
    *,
    intent_id: str,
    signature_request_payload: Mapping[str, Any],
    signature_request_compile_kwargs: Mapping[str, Any],
    verification_receipt_payload: Mapping[str, Any],
    signing_journal_receipt_payload: Mapping[str, Any],
    created_at_epoch_ms: int,
) -> KnowledgePackPromotionIntent:
    """Compile a no-effect intent from exact R6-R9D body-free Evidence."""

    request_snapshot = _freeze_signature_request_payload(signature_request_payload)
    if not isinstance(signature_request_compile_kwargs, Mapping):
        raise ValueError("signature_request_compile_kwargs must be a mapping")
    compile_kwargs_snapshot = dict(signature_request_compile_kwargs)
    verify_knowledge_pack_signature_verification_request(
        request_snapshot, **compile_kwargs_snapshot
    )
    request = KnowledgePackSignatureVerificationRequest.from_dict(
        request_snapshot
    )
    verification = KnowledgePackSignatureVerificationReceipt.from_dict(
        verification_receipt_payload
    )
    journal = DurableSigningJournalReceipt.from_dict(
        signing_journal_receipt_payload
    )
    request_payload = request.to_dict()
    verification_payload = verification.to_dict()
    journal_payload = journal.to_dict()

    if journal.state is not DurableSigningJournalState.SIGNED_AND_VERIFIED:
        raise ValueError("signing journal is not terminal signed-and-verified")
    expected_verification = (
        request.request_id,
        request_payload["signature_request_sha256"],
        request.signing_candidate_sha256,
        request.pack_id,
        request.pack_version,
        request.trusted_signer_policy_sha256,
        request.signer_key_id_sha256,
        request_payload["signature_message_sha256"],
    )
    observed_verification = (
        verification.signature_request_id,
        verification.signature_request_sha256,
        verification.signing_candidate_sha256,
        verification.pack_id,
        verification.pack_version,
        verification.trusted_signer_policy_sha256,
        verification.signer_key_id_sha256,
        verification.signature_message_sha256,
    )
    if observed_verification != expected_verification:
        raise ValueError("verification receipt does not bind the exact request")
    if journal.signature_request_sha256 != request_payload["signature_request_sha256"]:
        raise ValueError("signing journal does not bind the exact request")
    if journal.verification_receipt_sha256 != verification_payload["verification_receipt_sha256"]:
        raise ValueError("signing journal does not bind the exact verification receipt")
    if journal.ceremony_receipt_sha256 is None:
        raise ValueError("terminal signing journal lacks a ceremony receipt")

    state = (
        KnowledgePackPromotionIntentState.READY_FOR_INITIAL_PROMOTION_PREFLIGHT
        if request.predecessor_pack_sha256 is None
        else KnowledgePackPromotionIntentState.READY_FOR_REPLACEMENT_PROMOTION_PREFLIGHT
    )
    return KnowledgePackPromotionIntent(
        intent_id=intent_id,
        pack_id=request.pack_id,
        pack_version=request.pack_version,
        predecessor_pack_sha256=request.predecessor_pack_sha256,
        rollback_target_pack_sha256=request.predecessor_pack_sha256,
        signing_candidate_sha256=request.signing_candidate_sha256,
        signature_request_sha256=request_payload["signature_request_sha256"],
        signature_message_sha256=request_payload["signature_message_sha256"],
        trusted_signer_policy_sha256=request.trusted_signer_policy_sha256,
        signer_key_id_sha256=request.signer_key_id_sha256,
        detached_signature_sha256=verification.detached_signature_sha256,
        verification_receipt_sha256=verification_payload["verification_receipt_sha256"],
        signing_journal_receipt_sha256=journal_payload["journal_receipt_sha256"],
        signing_ceremony_receipt_sha256=journal.ceremony_receipt_sha256,
        created_at_epoch_ms=created_at_epoch_ms,
        state=state,
    )


def verify_knowledge_pack_promotion_intent(
    payload: Mapping[str, Any], **compile_kwargs: Any,
) -> None:
    expected = compile_knowledge_pack_promotion_intent(**compile_kwargs).to_dict()
    if not isinstance(payload, Mapping) or dict(payload) != expected:
        raise ValueError("promotion intent does not match exact current Evidence")


__all__ = [
    "KNOWLEDGE_PACK_PROMOTION_INTENT_CONTRACT",
    "KNOWLEDGE_PACK_PROMOTION_INTENT_VERSION",
    "KnowledgePackPromotionIntent",
    "KnowledgePackPromotionIntentState",
    "compile_knowledge_pack_promotion_intent",
    "verify_knowledge_pack_promotion_intent",
]
