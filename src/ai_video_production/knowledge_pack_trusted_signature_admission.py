"""TASK-029 R10B trusted signature admission for Knowledge Pack promotion.

The compiler re-runs the R9A Ed25519 verifier in the current call and requires
that result to reproduce the exact R10A verification claim.  Public-key and
signature bytes are transient inputs only.  The returned body-free projection
is non-authoritative on its own and grants no promotion effect.
"""
from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields, is_dataclass, replace
from enum import Enum
import re
from typing import Any, Mapping

from .human_edit_learning import (
    HardGateState,
    HumanActionEvidence,
    HumanDisposition,
)
from .knowledge_pack_candidate import (
    KnowledgePackCandidatePolicy,
    KnowledgePackSource,
)
from .knowledge_pack_durable_signing_journal import DurableSigningJournalReceipt
from .knowledge_pack_local_signing_ceremony import LocalSigningCeremonyReceipt
from .knowledge_pack_promotion_intent import (
    KnowledgePackPromotionIntent,
    compile_knowledge_pack_promotion_intent,
)
from .knowledge_pack_signature_request import KnowledgePackSignatureAlgorithm
from .knowledge_pack_signature_verification import (
    KnowledgePackSignatureVerificationReceipt,
    verify_detached_knowledge_pack_signature,
)
from .knowledge_pack_signing import (
    CriticKnowledgePackDecision,
    HumanKnowledgePackDecision,
    HumanKnowledgePackReview,
    IndependentKnowledgePackCriticReview,
)
from .multimodal_scoring import (
    EvidenceValidity,
    FeatureModality,
    FeaturePolarity,
    FeatureRule,
    FeatureSourceSelector,
    ScoringProfile,
)
from .owner_decision_store import (
    HumanDecision,
    OwnerDecisionEntry,
    OwnerDecisionHistory,
)
from .owner_profile_registry import (
    OwnerProfileRegistryCandidate,
    OwnerProfileRegistryCandidateState,
)
from .owner_profile_registry_store import (
    OwnerProfileRegistryConfirmation,
    OwnerProfileRegistryHistory,
    OwnerProfileRegistryRevision,
)
from .serialization import canonical_json_bytes, sha256_bytes


KNOWLEDGE_PACK_TRUSTED_SIGNATURE_ADMISSION_VERSION = "1.0.0"
KNOWLEDGE_PACK_TRUSTED_SIGNATURE_ADMISSION_CONTRACT = (
    "TASK-029/KNOWLEDGE_PACK/TRUSTED_SIGNATURE_ADMISSION/1.0.0"
)
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_PROMOTION_INTENT_COMPILE_FIELDS = {
    "intent_id",
    "signature_request_payload",
    "signature_request_compile_kwargs",
    "verification_receipt_payload",
    "signing_journal_receipt_payload",
    "created_at_epoch_ms",
}
_MAX_COMPILE_SNAPSHOT_DEPTH = 64
_MAX_COMPILE_SNAPSHOT_NODES = 262_144
_ALLOWED_COMPILE_ENUM_TYPES = frozenset(
    {
        HardGateState,
        HumanDisposition,
        KnowledgePackSignatureAlgorithm,
        CriticKnowledgePackDecision,
        HumanKnowledgePackDecision,
        EvidenceValidity,
        FeatureModality,
        FeaturePolarity,
        HumanDecision,
        OwnerProfileRegistryCandidateState,
    }
)
_ALLOWED_COMPILE_DATACLASS_TYPES = frozenset(
    {
        HumanActionEvidence,
        KnowledgePackCandidatePolicy,
        KnowledgePackSource,
        HumanKnowledgePackReview,
        IndependentKnowledgePackCriticReview,
        FeatureRule,
        FeatureSourceSelector,
        ScoringProfile,
        OwnerDecisionEntry,
        OwnerDecisionHistory,
        OwnerProfileRegistryCandidate,
        OwnerProfileRegistryConfirmation,
        OwnerProfileRegistryHistory,
        OwnerProfileRegistryRevision,
    }
)


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


def _freeze_exact_json(
    value: object,
    field: str,
    *,
    active: set[int],
    budget: list[int],
    depth: int = 0,
) -> object:
    """Copy exact JSON primitives without invoking custom Mapping hooks."""

    if depth > _MAX_COMPILE_SNAPSHOT_DEPTH:
        raise ValueError(f"{field} exceeds depth limit")
    budget[0] += 1
    if budget[0] > _MAX_COMPILE_SNAPSHOT_NODES:
        raise ValueError(f"{field} exceeds node limit")
    if value is None or type(value) in (str, int, bool):
        return value
    identity = id(value)
    if identity in active:
        raise ValueError(f"{field} must not be cyclic")
    active.add(identity)
    try:
        if type(value) is dict:
            result: dict[str, object] = {}
            for key, item in value.items():
                if type(key) is not str:
                    raise ValueError(f"{field} keys must be exact strings")
                result[key] = _freeze_exact_json(
                    item,
                    f"{field}.{key}",
                    active=active,
                    budget=budget,
                    depth=depth + 1,
                )
            return result
        if type(value) is list:
            return [
                _freeze_exact_json(
                    item,
                    f"{field}[{index}]",
                    active=active,
                    budget=budget,
                    depth=depth + 1,
                )
                for index, item in enumerate(value)
            ]
    finally:
        active.remove(identity)
    raise ValueError(f"{field} must contain only exact JSON primitives")


def _freeze_exact_object(value: object, field: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{field} must be an exact built-in dict")
    frozen = _freeze_exact_json(value, field, active=set(), budget=[0])
    assert isinstance(frozen, dict)
    return frozen


def _freeze_compile_value(
    value: object,
    field: str,
    *,
    active: set[int],
    budget: list[int],
    depth: int = 0,
) -> Any:
    """Rebuild the mutable R6-R8 compile tree into a detached snapshot."""

    if depth > _MAX_COMPILE_SNAPSHOT_DEPTH:
        raise ValueError("signature request compile tree exceeds depth limit")
    budget[0] += 1
    if budget[0] > _MAX_COMPILE_SNAPSHOT_NODES:
        raise ValueError("signature request compile tree exceeds node limit")
    if value is None or type(value) in (str, int, bool):
        return value
    if isinstance(value, Enum):
        if type(value) not in _ALLOWED_COMPILE_ENUM_TYPES:
            raise ValueError(f"{field} enum is outside the exact TASK-029 contract")
        return value

    identity = id(value)
    if identity in active:
        raise ValueError("signature request compile tree must not be cyclic")
    active.add(identity)
    try:
        if type(value) is dict:
            result: dict[str, Any] = {}
            for key, item in value.items():
                if type(key) is not str:
                    raise ValueError(f"{field} keys must be exact strings")
                result[key] = _freeze_compile_value(
                    item,
                    f"{field}.{key}",
                    active=active,
                    budget=budget,
                    depth=depth + 1,
                )
            return result
        if type(value) in (list, tuple):
            items = [
                _freeze_compile_value(
                    item,
                    f"{field}[{index}]",
                    active=active,
                    budget=budget,
                    depth=depth + 1,
                )
                for index, item in enumerate(value)
            ]
            return items if type(value) is list else tuple(items)
        if is_dataclass(value) and not isinstance(value, type):
            value_type = type(value)
            if value_type not in _ALLOWED_COMPILE_DATACLASS_TYPES:
                raise ValueError(
                    f"{field} must use an exact frozen Product dataclass"
                )
            replacements = {
                item.name: _freeze_compile_value(
                    getattr(value, item.name),
                    f"{field}.{item.name}",
                    active=active,
                    budget=budget,
                    depth=depth + 1,
                )
                for item in dataclass_fields(value)
            }
            return replace(value, **replacements)
        raise ValueError(
            f"{field} must contain only exact TASK-029 compile contract values"
        )
    finally:
        active.remove(identity)


def _freeze_promotion_compile_kwargs(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(
            "promotion_intent_compile_kwargs must be an exact built-in dict"
        )
    if set(value) != _PROMOTION_INTENT_COMPILE_FIELDS:
        raise ValueError("promotion intent compile fields are incomplete or unknown")
    request_compile_kwargs = value["signature_request_compile_kwargs"]
    if type(request_compile_kwargs) is not dict:
        raise ValueError(
            "signature_request_compile_kwargs must be an exact built-in dict"
        )
    frozen_request_compile_kwargs = _freeze_compile_value(
        request_compile_kwargs,
        "signature_request_compile_kwargs",
        active=set(),
        budget=[0],
    )
    assert isinstance(frozen_request_compile_kwargs, dict)
    return {
        "intent_id": value["intent_id"],
        "signature_request_payload": _freeze_exact_object(
            value["signature_request_payload"], "signature_request_payload"
        ),
        "signature_request_compile_kwargs": frozen_request_compile_kwargs,
        "verification_receipt_payload": _freeze_exact_object(
            value["verification_receipt_payload"],
            "verification_receipt_payload",
        ),
        "signing_journal_receipt_payload": _freeze_exact_object(
            value["signing_journal_receipt_payload"],
            "signing_journal_receipt_payload",
        ),
        "created_at_epoch_ms": value["created_at_epoch_ms"],
    }


class KnowledgePackTrustedSignatureAdmissionState(str, Enum):
    READY_FOR_INITIAL_SIGNATURE_ARTIFACT_CUSTODY = (
        "READY_FOR_INITIAL_SIGNATURE_ARTIFACT_CUSTODY"
    )
    READY_FOR_REPLACEMENT_SIGNATURE_ARTIFACT_CUSTODY = (
        "READY_FOR_REPLACEMENT_SIGNATURE_ARTIFACT_CUSTODY"
    )


@dataclass(frozen=True, slots=True)
class KnowledgePackTrustedSignatureAdmission:
    admission_id: str
    promotion_intent_id: str
    promotion_intent_sha256: str
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
    verified_at_epoch_ms: int
    state: KnowledgePackTrustedSignatureAdmissionState

    def __post_init__(self) -> None:
        for field in ("admission_id", "promotion_intent_id", "pack_id"):
            _id(getattr(self, field), field)
        if not isinstance(self.pack_version, str) or _SEMVER.fullmatch(
            self.pack_version
        ) is None:
            raise ValueError("pack_version must be semantic version x.y.z")
        for field in (
            "promotion_intent_sha256",
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
        if self.rollback_target_pack_sha256 != self.predecessor_pack_sha256:
            raise ValueError("rollback target must equal the exact predecessor pack")
        _positive(self.verified_at_epoch_ms, "verified_at_epoch_ms")
        if not isinstance(self.state, KnowledgePackTrustedSignatureAdmissionState):
            raise ValueError(
                "state must be a KnowledgePackTrustedSignatureAdmissionState"
            )
        expected_state = (
            KnowledgePackTrustedSignatureAdmissionState.READY_FOR_INITIAL_SIGNATURE_ARTIFACT_CUSTODY
            if self.predecessor_pack_sha256 is None
            else KnowledgePackTrustedSignatureAdmissionState.READY_FOR_REPLACEMENT_SIGNATURE_ARTIFACT_CUSTODY
        )
        if self.state is not expected_state:
            raise ValueError("admission state does not match predecessor presence")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "admission_version": KNOWLEDGE_PACK_TRUSTED_SIGNATURE_ADMISSION_VERSION,
            "record_type": "KNOWLEDGE_PACK_TRUSTED_SIGNATURE_ADMISSION",
            "task_owner": "TASK-029",
            "admission_contract": KNOWLEDGE_PACK_TRUSTED_SIGNATURE_ADMISSION_CONTRACT,
            "admission_id": self.admission_id,
            "promotion_intent_id": self.promotion_intent_id,
            "promotion_intent_sha256": self.promotion_intent_sha256,
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
            "verified_at_epoch_ms": self.verified_at_epoch_ms,
            "state": self.state.value,
            "caller_supplied_source_graph_recompiled": True,
            "canonical_latest_source_revalidated": False,
            "r9a_verifier_executed_in_current_call": True,
            "verification_claim_reproduced_exactly": True,
            "cryptographic_signature_verified_against_supplied_policy": True,
            "caller_supplied_signer_policy_self_validated": True,
            "canonical_trusted_signer_policy_revalidated": False,
            "canonical_signer_origin_authenticated": False,
            "owner_signer_binding_confirmed": False,
            "signature_artifact_observed_during_verification": True,
            "signature_artifact_custody_confirmed": False,
            "standalone_admission_payload_authoritative": False,
            "direct_recompile_required_for_downstream": True,
            "canonical_receipt_minted": False,
            "promotion_confirmation_eligible": False,
            "explicit_human_promotion_confirmation_required": True,
            "canonical_store_transaction_required": True,
            "runtime_compatibility_validation_required": True,
            "signature_artifact_custody_required": True,
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
            "in_memory_admission_only": True,
            "knowledge_pack_write_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "automatic_promotion_authorized": False,
            "runtime_profile_apply_authorized": False,
            "rollback_execution_authorized": False,
            "release_authorized": False,
            "external_effect_authorized": False,
        }
        body["trusted_signature_admission_sha256"] = sha256_bytes(
            canonical_json_bytes(body)
        )
        return body

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any]
    ) -> "KnowledgePackTrustedSignatureAdmission":
        snapshot = _freeze_exact_object(value, "trusted_signature_admission")
        expected = set(
            cls(
                admission_id="shape",
                promotion_intent_id="shape",
                promotion_intent_sha256="sha256:" + "0" * 64,
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
                verified_at_epoch_ms=1,
                state=KnowledgePackTrustedSignatureAdmissionState.READY_FOR_INITIAL_SIGNATURE_ARTIFACT_CUSTODY,
            ).to_dict()
        )
        if set(snapshot) != expected:
            raise ValueError("trusted signature admission fields are incomplete or unknown")
        result = cls(
            admission_id=snapshot["admission_id"],
            promotion_intent_id=snapshot["promotion_intent_id"],
            promotion_intent_sha256=snapshot["promotion_intent_sha256"],
            pack_id=snapshot["pack_id"],
            pack_version=snapshot["pack_version"],
            predecessor_pack_sha256=snapshot["predecessor_pack_sha256"],
            rollback_target_pack_sha256=snapshot["rollback_target_pack_sha256"],
            signing_candidate_sha256=snapshot["signing_candidate_sha256"],
            signature_request_sha256=snapshot["signature_request_sha256"],
            signature_message_sha256=snapshot["signature_message_sha256"],
            trusted_signer_policy_sha256=snapshot["trusted_signer_policy_sha256"],
            signer_key_id_sha256=snapshot["signer_key_id_sha256"],
            detached_signature_sha256=snapshot["detached_signature_sha256"],
            verification_receipt_sha256=snapshot["verification_receipt_sha256"],
            signing_journal_receipt_sha256=snapshot[
                "signing_journal_receipt_sha256"
            ],
            signing_ceremony_receipt_sha256=snapshot[
                "signing_ceremony_receipt_sha256"
            ],
            verified_at_epoch_ms=snapshot["verified_at_epoch_ms"],
            state=KnowledgePackTrustedSignatureAdmissionState(snapshot["state"]),
        )
        if result.to_dict() != snapshot:
            raise ValueError("trusted signature admission identity, flags, or hash mismatch")
        return result


def compile_knowledge_pack_trusted_signature_admission(
    *,
    admission_id: str,
    promotion_intent_payload: Mapping[str, Any],
    promotion_intent_compile_kwargs: Mapping[str, Any],
    signing_ceremony_receipt_payload: Mapping[str, Any],
    trusted_signer_policy_payload: Mapping[str, Any],
    public_key_bytes: bytes,
    detached_signature_bytes: bytes,
    verified_at_epoch_ms: int,
) -> KnowledgePackTrustedSignatureAdmission:
    """Re-run trusted verification and return a body-free no-effect admission."""

    _id(admission_id, "admission_id")
    _positive(verified_at_epoch_ms, "verified_at_epoch_ms")
    if type(public_key_bytes) is not bytes:
        raise ValueError("public_key_bytes must be exact bytes")
    if type(detached_signature_bytes) is not bytes:
        raise ValueError("detached_signature_bytes must be exact bytes")

    intent_snapshot = _freeze_exact_object(
        promotion_intent_payload, "promotion_intent_payload"
    )
    policy_snapshot = _freeze_exact_object(
        trusted_signer_policy_payload, "trusted_signer_policy_payload"
    )
    compile_snapshot = _freeze_promotion_compile_kwargs(
        promotion_intent_compile_kwargs
    )
    ceremony_snapshot = _freeze_exact_object(
        signing_ceremony_receipt_payload, "signing_ceremony_receipt_payload"
    )
    journal = DurableSigningJournalReceipt.from_dict(
        compile_snapshot["signing_journal_receipt_payload"]
    )
    ceremony = LocalSigningCeremonyReceipt.from_dict(ceremony_snapshot)
    claimed_verification = KnowledgePackSignatureVerificationReceipt.from_dict(
        compile_snapshot["verification_receipt_payload"]
    )
    trusted_verification = verify_detached_knowledge_pack_signature(
        receipt_id=claimed_verification.receipt_id,
        signature_request_payload=compile_snapshot["signature_request_payload"],
        signature_request_compile_kwargs=compile_snapshot[
            "signature_request_compile_kwargs"
        ],
        trusted_signer_policy_payload=policy_snapshot,
        public_key_bytes=public_key_bytes,
        detached_signature_bytes=detached_signature_bytes,
    )
    trusted_verification_payload = trusted_verification.to_dict()
    if trusted_verification_payload != compile_snapshot[
        "verification_receipt_payload"
    ]:
        raise ValueError(
            "trusted verification does not reproduce the exact R10A claim"
        )

    verified_compile_kwargs = dict(compile_snapshot)
    verified_compile_kwargs["verification_receipt_payload"] = (
        trusted_verification_payload
    )
    intent = compile_knowledge_pack_promotion_intent(**verified_compile_kwargs)
    ceremony_payload = ceremony.to_dict()
    ceremony_sha256 = ceremony_payload["ceremony_receipt_sha256"]
    if (
        ceremony_sha256 != intent.signing_ceremony_receipt_sha256
        or journal.ceremony_receipt_sha256 != ceremony_sha256
        or ceremony.verification_receipt_sha256
        != trusted_verification_payload["verification_receipt_sha256"]
        or journal.verification_receipt_sha256
        != trusted_verification_payload["verification_receipt_sha256"]
        or ceremony.signature_request_sha256 != intent.signature_request_sha256
        or ceremony.signer_key_id_sha256 != intent.signer_key_id_sha256
        or ceremony.detached_signature_sha256
        != trusted_verification.detached_signature_sha256
    ):
        raise ValueError("signing ceremony or journal coordinate mismatch")
    causal_floor = max(
        intent.created_at_epoch_ms,
        journal.updated_at_epoch_ms,
        ceremony.completed_at_epoch_ms,
    )
    if verified_at_epoch_ms < causal_floor:
        raise ValueError("supplied-policy verification time precedes signed Evidence")
    intent_payload = intent.to_dict()
    if intent_snapshot != intent_payload:
        raise ValueError("promotion intent does not match exact current Evidence")

    state = (
        KnowledgePackTrustedSignatureAdmissionState.READY_FOR_INITIAL_SIGNATURE_ARTIFACT_CUSTODY
        if intent.predecessor_pack_sha256 is None
        else KnowledgePackTrustedSignatureAdmissionState.READY_FOR_REPLACEMENT_SIGNATURE_ARTIFACT_CUSTODY
    )
    return KnowledgePackTrustedSignatureAdmission(
        admission_id=admission_id,
        promotion_intent_id=intent.intent_id,
        promotion_intent_sha256=intent_payload["promotion_intent_sha256"],
        pack_id=intent.pack_id,
        pack_version=intent.pack_version,
        predecessor_pack_sha256=intent.predecessor_pack_sha256,
        rollback_target_pack_sha256=intent.rollback_target_pack_sha256,
        signing_candidate_sha256=intent.signing_candidate_sha256,
        signature_request_sha256=intent.signature_request_sha256,
        signature_message_sha256=intent.signature_message_sha256,
        trusted_signer_policy_sha256=intent.trusted_signer_policy_sha256,
        signer_key_id_sha256=intent.signer_key_id_sha256,
        detached_signature_sha256=trusted_verification.detached_signature_sha256,
        verification_receipt_sha256=trusted_verification_payload[
            "verification_receipt_sha256"
        ],
        signing_journal_receipt_sha256=intent.signing_journal_receipt_sha256,
        signing_ceremony_receipt_sha256=intent.signing_ceremony_receipt_sha256,
        verified_at_epoch_ms=verified_at_epoch_ms,
        state=state,
    )


def verify_knowledge_pack_trusted_signature_admission(
    payload: Mapping[str, Any], **compile_kwargs: Any
) -> None:
    snapshot = _freeze_exact_object(payload, "trusted_signature_admission")
    expected = compile_knowledge_pack_trusted_signature_admission(
        **compile_kwargs
    ).to_dict()
    if snapshot != expected:
        raise ValueError(
            "trusted signature admission does not match exact current Evidence"
        )


__all__ = [
    "KNOWLEDGE_PACK_TRUSTED_SIGNATURE_ADMISSION_CONTRACT",
    "KNOWLEDGE_PACK_TRUSTED_SIGNATURE_ADMISSION_VERSION",
    "KnowledgePackTrustedSignatureAdmission",
    "KnowledgePackTrustedSignatureAdmissionState",
    "compile_knowledge_pack_trusted_signature_admission",
    "verify_knowledge_pack_trusted_signature_admission",
]
