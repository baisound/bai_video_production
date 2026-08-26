"""TASK-058 P1C-A bounded source and Human-binding revalidation.

This module prepares one exact P1B entry-shaped candidate for later durable
membership verification. It performs deterministic validation, except that the
existing TASK-055 validator may lazily read packaged immutable JSON Schemas.
No mutable/external read, write, canonical store, receipt, Timeline, Resolve,
network, provider, or native effect exists.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from .montage_learning_admission_store import MontageLearningAdmissionEntry
from .montage_learning_bridge_contracts import (
    EXACT_CONTRACT_PROFILE,
    EXACT_LINEAGE_VERIFIED,
    OWNER_SCOPE_EXPECTATION_MATCHED_NONAUTHORITATIVE,
    REVIEW_REQUIRED,
    MontageLearningBridgeContractError,
    validate_exact_evidence_delivery,
)
from .montage_learning_receipt_contracts import (
    derive_montage_learning_idempotency_key_sha256,
)
from .serialization import canonical_json_bytes, sha256_bytes


SCHEMA_VERSION = "1.0.0"
RECORD_TYPE = "MONTAGE_LEARNING_CANONICAL_PREFLIGHT"
TASK_OWNER = "TASK-058"
NONAUTHORITATIVE_PREFLIGHT_PROJECTION = "NONAUTHORITATIVE_SOURCE_HUMAN_PREFLIGHT_PROJECTION"
HUMAN_BINDING_DOMAIN = b"TASK058_MONTAGE_LEARNING_HUMAN_BINDING_V1\0"
PREFLIGHT_DOMAIN = b"TASK058_MONTAGE_LEARNING_CANONICAL_PREFLIGHT_V1\0"
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_RECORD_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$")
_FIELDS = frozenset({
    "schema_version", "record_type", "task_owner", "source_contract_profile",
    "project_id", "source_record_id", "source_sha256", "owner_scope_hash",
    "proposal_sha256", "approved_plan_sha256",
    "idempotency_key_sha256", "staging_entry_sha256",
    "canonical_evidence_id", "canonical_evidence_sha256",
    "human_binding_sha256", "admission_state", "projection_structure_valid",
    "compiler_execution_verified", "source_lineage_origin_verified",
    "human_binding_origin_verified", "staging_entry_origin_verified",
    "staging_membership_verified", "staging_store_origin_verified",
    "do_not_learn", "negative_feedback_preserved",
    "monotonic_project_anchor_verified", "rollback_detection_authority_created",
    "canonical_store_written", "canonical_store_commit_sha256",
    "receipt_minted", "canonical_admission_authority_created",
    "automatic_learning_promotion_authorized", "timeline_mutation_authorized",
    "resolve_write_authorized", "external_effect_authorized", "preflight_sha256",
})


class MontageLearningCanonicalPreflightError(ValueError):
    """Raised when exact source and staging coordinates cannot be rebound."""


def _digest(value: object, name: str) -> str:
    if type(value) is not str or _DIGEST_RE.fullmatch(value) is None:
        raise MontageLearningCanonicalPreflightError(f"{name} is invalid")
    return value


def _snapshot(value: Mapping[str, Any], name: str) -> dict[str, Any]:
    """Copy exact built-in JSON values once without invoking user hooks."""

    def snapshot(item: object, path: str) -> Any:
        if item is None or type(item) in {str, bool, int}:
            return item
        if type(item) is list:
            return [snapshot(child, f"{path}[]") for child in item]
        if type(item) is dict:
            result: dict[str, Any] = {}
            for key, child in item.items():
                if type(key) is not str:
                    raise MontageLearningCanonicalPreflightError(
                        f"{path} keys must be exact strings"
                    )
                result[key] = snapshot(child, f"{path}.{key}")
            return result
        raise MontageLearningCanonicalPreflightError(
            f"{path} must contain exact built-in JSON values"
        )

    if type(value) is not dict:
        raise MontageLearningCanonicalPreflightError(
            f"{name} must be an exact built-in object"
        )
    return snapshot(value, name)


def derive_canonical_evidence_id(evidence_sha256: str) -> str:
    """Derive the stable P1C evidence identifier from exact TASK-055 Evidence."""

    digest = _digest(evidence_sha256, "evidence_sha256")
    return f"task055-evidence-{digest.removeprefix('sha256:')}"


def derive_human_binding_sha256(
    *,
    project_id: str,
    source_record_id: str,
    owner_scope_hash: str,
    proposal_sha256: str,
    approved_plan_sha256: str,
    evidence_sha256: str,
) -> str:
    """Bind one exact delivery, Owner scope and TASK-055 Human lineage."""

    for value, name in (
        (project_id, "project_id"),
        (source_record_id, "source_record_id"),
    ):
        if type(value) is not str or _RECORD_ID_RE.fullmatch(value) is None:
            raise MontageLearningCanonicalPreflightError(f"{name} is invalid")
    body = {
        "approved_plan_sha256": _digest(
            approved_plan_sha256, "approved_plan_sha256"
        ),
        "evidence_sha256": _digest(evidence_sha256, "evidence_sha256"),
        "owner_scope_hash": _digest(owner_scope_hash, "owner_scope_hash"),
        "project_id": project_id,
        "proposal_sha256": _digest(proposal_sha256, "proposal_sha256"),
        "source_contract_profile": EXACT_CONTRACT_PROFILE,
        "source_record_id": source_record_id,
    }
    return sha256_bytes(HUMAN_BINDING_DOMAIN + canonical_json_bytes(body))


@dataclass(frozen=True, slots=True)
class MontageLearningCanonicalPreflight:
    project_id: str
    source_record_id: str
    source_sha256: str
    owner_scope_hash: str
    proposal_sha256: str
    approved_plan_sha256: str
    idempotency_key_sha256: str
    staging_entry_sha256: str
    canonical_evidence_id: str
    canonical_evidence_sha256: str
    human_binding_sha256: str
    negative_feedback_preserved: bool

    def __post_init__(self) -> None:
        for value, name in (
            (self.project_id, "project_id"),
            (self.source_record_id, "source_record_id"),
        ):
            if type(value) is not str or _RECORD_ID_RE.fullmatch(value) is None:
                raise ValueError(f"{name} is invalid")
        for field in (
            "source_sha256", "owner_scope_hash", "proposal_sha256",
            "approved_plan_sha256", "idempotency_key_sha256",
            "staging_entry_sha256", "canonical_evidence_sha256",
            "human_binding_sha256",
        ):
            _digest(getattr(self, field), field)
        if self.source_sha256 != self.canonical_evidence_sha256:
            raise ValueError("source_sha256 must match canonical_evidence_sha256")
        expected_id = derive_canonical_evidence_id(self.canonical_evidence_sha256)
        if self.canonical_evidence_id != expected_id:
            raise ValueError("canonical_evidence_id mismatch")
        expected_idempotency = derive_montage_learning_idempotency_key_sha256(
            source_contract_profile=EXACT_CONTRACT_PROFILE,
            source_record_id=self.source_record_id,
            source_sha256=self.source_sha256,
            owner_scope_hash=self.owner_scope_hash,
        )
        if self.idempotency_key_sha256 != expected_idempotency:
            raise ValueError("idempotency_key_sha256 mismatch")
        expected_binding = derive_human_binding_sha256(
            project_id=self.project_id,
            source_record_id=self.source_record_id,
            owner_scope_hash=self.owner_scope_hash,
            proposal_sha256=self.proposal_sha256,
            approved_plan_sha256=self.approved_plan_sha256,
            evidence_sha256=self.canonical_evidence_sha256,
        )
        if self.human_binding_sha256 != expected_binding:
            raise ValueError("human_binding_sha256 mismatch")
        if type(self.negative_feedback_preserved) is not bool:
            raise ValueError("negative_feedback_preserved must be boolean")

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": RECORD_TYPE,
            "task_owner": TASK_OWNER,
            "source_contract_profile": EXACT_CONTRACT_PROFILE,
            "project_id": self.project_id,
            "source_record_id": self.source_record_id,
            "source_sha256": self.source_sha256,
            "owner_scope_hash": self.owner_scope_hash,
            "proposal_sha256": self.proposal_sha256,
            "approved_plan_sha256": self.approved_plan_sha256,
            "idempotency_key_sha256": self.idempotency_key_sha256,
            "staging_entry_sha256": self.staging_entry_sha256,
            "canonical_evidence_id": self.canonical_evidence_id,
            "canonical_evidence_sha256": self.canonical_evidence_sha256,
            "human_binding_sha256": self.human_binding_sha256,
            "admission_state": NONAUTHORITATIVE_PREFLIGHT_PROJECTION,
            "projection_structure_valid": True,
            "compiler_execution_verified": False,
            "source_lineage_origin_verified": False,
            "human_binding_origin_verified": False,
            "staging_entry_origin_verified": False,
            "staging_membership_verified": False,
            "staging_store_origin_verified": False,
            "do_not_learn": False,
            "negative_feedback_preserved": self.negative_feedback_preserved,
            "monotonic_project_anchor_verified": False,
            "rollback_detection_authority_created": False,
            "canonical_store_written": False,
            "canonical_store_commit_sha256": None,
            "receipt_minted": False,
            "canonical_admission_authority_created": False,
            "automatic_learning_promotion_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
            "external_effect_authorized": False,
        }
        body["preflight_sha256"] = sha256_bytes(
            PREFLIGHT_DOMAIN + canonical_json_bytes(body)
        )
        return body

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any]
    ) -> "MontageLearningCanonicalPreflight":
        if type(value) is not dict or set(value) != _FIELDS:
            raise ValueError("canonical preflight fields are incomplete or unknown")
        if (
            value["schema_version"] != SCHEMA_VERSION
            or value["record_type"] != RECORD_TYPE
            or value["task_owner"] != TASK_OWNER
            or value["source_contract_profile"] != EXACT_CONTRACT_PROFILE
            or value["admission_state"] != NONAUTHORITATIVE_PREFLIGHT_PROJECTION
        ):
            raise ValueError("canonical preflight identity mismatch")
        if value["projection_structure_valid"] is not True:
            raise ValueError("projection_structure_valid must remain true")
        if value["do_not_learn"] is not False:
            raise ValueError("do_not_learn must remain false")
        for field in (
            "compiler_execution_verified", "source_lineage_origin_verified",
            "human_binding_origin_verified", "staging_entry_origin_verified",
            "staging_membership_verified", "staging_store_origin_verified",
            "monotonic_project_anchor_verified",
            "rollback_detection_authority_created", "canonical_store_written",
            "receipt_minted", "canonical_admission_authority_created",
            "automatic_learning_promotion_authorized", "timeline_mutation_authorized",
            "resolve_write_authorized", "external_effect_authorized",
        ):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        if value["canonical_store_commit_sha256"] is not None:
            raise ValueError("canonical store commit must remain absent")
        result = cls(
            value["project_id"], value["source_record_id"], value["source_sha256"],
            value["owner_scope_hash"], value["proposal_sha256"],
            value["approved_plan_sha256"], value["idempotency_key_sha256"],
            value["staging_entry_sha256"], value["canonical_evidence_id"],
            value["canonical_evidence_sha256"], value["human_binding_sha256"],
            value["negative_feedback_preserved"],
        )
        if result.to_dict() != dict(value):
            raise ValueError("canonical preflight hash or derived field mismatch")
        return result


def compile_montage_learning_canonical_preflight(
    delivery: Mapping[str, Any],
    staged_entry: Mapping[str, Any],
    *,
    expected_owner_scope_hash: str,
) -> MontageLearningCanonicalPreflight:
    """Revalidate exact source/Human lineage and bind it to one P1B entry."""

    delivery_body = _snapshot(delivery, "delivery")
    staged_body = _snapshot(staged_entry, "staged_entry")
    try:
        candidate = validate_exact_evidence_delivery(
            delivery_body,
            expected_owner_scope_hash=expected_owner_scope_hash,
        )
        entry = MontageLearningAdmissionEntry.from_dict(staged_body)
    except (MontageLearningBridgeContractError, ValueError) as exc:
        raise MontageLearningCanonicalPreflightError(
            "exact source or staging entry failed revalidation"
        ) from exc
    expected_candidate_state = (
        "EXACT_BVP_NATIVE", EXACT_LINEAGE_VERIFIED,
        OWNER_SCOPE_EXPECTATION_MATCHED_NONAUTHORITATIVE,
        REVIEW_REQUIRED, "NOT_APPLICABLE",
    )
    actual_candidate_state = (
        candidate.lane, candidate.validation_state, candidate.owner_scope_state,
        candidate.review_state, candidate.runtime_observation_state,
    )
    if actual_candidate_state != expected_candidate_state:
        raise MontageLearningCanonicalPreflightError(
            "exact source candidate state drifted"
        )

    evidence = delivery_body["human_edit_evidence"]
    if type(evidence) is not dict:
        raise MontageLearningCanonicalPreflightError(
            "human_edit_evidence must be an object"
        )
    if evidence.get("do_not_learn") is not False:
        raise MontageLearningCanonicalPreflightError(
            "do_not_learn evidence cannot enter canonical preflight"
        )
    evidence_sha = _digest(delivery_body["evidence_sha256"], "evidence_sha256")
    evidence_id = derive_canonical_evidence_id(evidence_sha)
    proposal = delivery_body["proposal"]
    if type(proposal) is not dict:
        raise MontageLearningCanonicalPreflightError("proposal must be an object")
    project_id = proposal.get("project_id")
    binding_sha = derive_human_binding_sha256(
        project_id=project_id,
        source_record_id=candidate.record_id,
        owner_scope_hash=expected_owner_scope_hash,
        proposal_sha256=delivery_body["proposal_sha256"],
        approved_plan_sha256=delivery_body["approved_plan_sha256"],
        evidence_sha256=evidence_sha,
    )
    idempotency_sha = derive_montage_learning_idempotency_key_sha256(
        source_contract_profile=EXACT_CONTRACT_PROFILE,
        source_record_id=candidate.record_id,
        source_sha256=candidate.source_sha256,
        owner_scope_hash=expected_owner_scope_hash,
    )
    expected = (
        candidate.record_id,
        candidate.source_sha256,
        expected_owner_scope_hash,
        idempotency_sha,
        evidence_id,
        evidence_sha,
        binding_sha,
    )
    actual = (
        entry.source_record_id,
        entry.source_sha256,
        entry.owner_scope_hash,
        entry.idempotency_key_sha256,
        entry.canonical_evidence_id,
        entry.canonical_evidence_sha256,
        entry.human_binding_sha256,
    )
    if actual != expected:
        raise MontageLearningCanonicalPreflightError(
            "staging entry does not match revalidated exact Human lineage"
        )
    disposition = evidence.get("disposition")
    return MontageLearningCanonicalPreflight(
        project_id=project_id,
        source_record_id=candidate.record_id,
        source_sha256=candidate.source_sha256,
        owner_scope_hash=expected_owner_scope_hash,
        proposal_sha256=_digest(delivery_body["proposal_sha256"], "proposal_sha256"),
        approved_plan_sha256=_digest(
            delivery_body["approved_plan_sha256"], "approved_plan_sha256"
        ),
        idempotency_key_sha256=idempotency_sha,
        staging_entry_sha256=_digest(entry.to_dict()["entry_sha256"], "entry_sha256"),
        canonical_evidence_id=evidence_id,
        canonical_evidence_sha256=evidence_sha,
        human_binding_sha256=binding_sha,
        negative_feedback_preserved=disposition == "DELETED",
    )


__all__ = [
    "HUMAN_BINDING_DOMAIN", "NONAUTHORITATIVE_PREFLIGHT_PROJECTION", "PREFLIGHT_DOMAIN",
    "MontageLearningCanonicalPreflight", "MontageLearningCanonicalPreflightError",
    "compile_montage_learning_canonical_preflight", "derive_canonical_evidence_id",
    "derive_human_binding_sha256",
]
