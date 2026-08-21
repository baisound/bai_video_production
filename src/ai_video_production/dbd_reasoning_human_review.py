"""TASK-054 R2D-C1 inert Human-review contracts.

This module validates an externally resolved Human confirmation against a
trusted, current in-memory snapshot.  It neither mints Human authority nor
persists, exports, dispatches, or otherwise applies a review decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
from typing import Any, Mapping

from .dbd_reasoning_candidate_lineage import (
    DbDReasoningCandidateLineage,
    admit_reasoning_candidate_lineage_record,
)
from .dbd_reasoning_contracts import DbDReasoningContextEnvelope
from .game_commentary import CommentaryCandidate, CommentaryPlan
from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


HUMAN_REVIEW_SCHEMA_VERSION = "1.0.0"
_CONFIRMATION_REF_RE = re.compile(r"human-confirmation://dbd-review/[0-9A-HJKMNP-TV-Z]{26}")
_EVIDENCE_REF_RE = re.compile(r"human-evidence://dbd-review/sha256/[0-9a-f]{64}")
_STABLE_CODE_RE = re.compile(r"[A-Z][A-Z0-9_]{1,63}")


class HumanReviewContractState(str, Enum):
    CANONICAL_REF_NOT_PROVIDED = "CANONICAL_REF_NOT_PROVIDED"
    BOUND_VERIFIED = "BOUND_VERIFIED"


class HumanReviewDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REVISE = "REVISE"


def _utc(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z") or len(value) > 40:
        raise ValueError(f"{name} must be UTC RFC3339")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be UTC RFC3339") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{name} must be UTC RFC3339")
    return parsed


def _safe_ref(value: Any, name: str, *, scheme: str) -> str:
    pattern = _CONFIRMATION_REF_RE if scheme == "human-confirmation" else _EVIDENCE_REF_RE
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"{name} must use the canonical body-free {scheme} namespace")
    return value


def _codes(value: Any, name: str, *, required: bool = False) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be an ordered array")
    result = tuple(value)
    if len(result) > 16 or result != tuple(sorted(set(result))):
        raise ValueError(f"{name} must be bounded, unique and sorted")
    if any(not isinstance(item, str) or not _STABLE_CODE_RE.fullmatch(item) for item in result):
        raise ValueError(f"{name} must contain stable codes")
    if required and not result:
        raise ValueError(f"{name} is required")
    return result


@dataclass(frozen=True, slots=True)
class DbDReasoningHumanReviewAuthorityBinding:
    """Admission result for an external Human Gate record; never authority minted here."""

    schema_version: str
    contract_state: HumanReviewContractState
    confirmation_ref: str | None
    confirmation_revision: int | None
    confirmation_sha256: str | None
    reviewer_kind: str | None
    decision: HumanReviewDecision | None
    decided_at: str | None
    expires_at: str | None
    one_shot: bool | None
    authority_evidence_ref: str | None
    authority_evidence_sha256: str | None
    root_candidate_id: str | None
    expected_leaf_candidate_id: str | None
    expected_leaf_candidate_sha256: str | None
    expected_leaf_lineage_sha256: str | None
    expected_context_sha256: str | None
    expected_commentary_plan_sha256: str | None
    expected_proposal_sha256: str | None
    expected_previous_review_revision: int | None
    expected_previous_review_sha256: str | None
    reason_codes: tuple[str, ...] | None
    correction_request_sha256: str | None
    binding_sha256: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != HUMAN_REVIEW_SCHEMA_VERSION or not isinstance(self.contract_state, HumanReviewContractState):
            raise ValueError("unsupported Human review authority binding")
        nullable = (
            self.confirmation_ref, self.confirmation_revision, self.confirmation_sha256,
            self.reviewer_kind, self.decision, self.decided_at, self.expires_at,
            self.one_shot, self.authority_evidence_ref, self.authority_evidence_sha256,
            self.root_candidate_id, self.expected_leaf_candidate_id,
            self.expected_leaf_candidate_sha256, self.expected_leaf_lineage_sha256,
            self.expected_context_sha256, self.expected_commentary_plan_sha256,
            self.expected_proposal_sha256, self.expected_previous_review_revision,
            self.expected_previous_review_sha256, self.reason_codes,
            self.correction_request_sha256,
        )
        if self.contract_state is HumanReviewContractState.CANONICAL_REF_NOT_PROVIDED:
            if any(value is not None for value in nullable):
                raise ValueError("unresolved Human authority binding must not invent fields")
        else:
            required = (
                self.confirmation_ref, self.confirmation_revision, self.confirmation_sha256,
                self.reviewer_kind, self.decision, self.decided_at, self.expires_at,
                self.one_shot, self.authority_evidence_ref, self.authority_evidence_sha256,
                self.root_candidate_id, self.expected_leaf_candidate_id,
                self.expected_leaf_candidate_sha256, self.expected_leaf_lineage_sha256,
                self.expected_context_sha256, self.expected_commentary_plan_sha256,
                self.expected_proposal_sha256, self.expected_previous_review_revision,
                self.reason_codes,
            )
            if any(value is None for value in required):
                raise ValueError("BOUND_VERIFIED Human authority binding is incomplete")
            _safe_ref(self.confirmation_ref, "confirmation_ref", scheme="human-confirmation")
            _safe_ref(self.authority_evidence_ref, "authority_evidence_ref", scheme="human-evidence")
            if isinstance(self.confirmation_revision, bool) or not isinstance(self.confirmation_revision, int) or self.confirmation_revision < 1:
                raise ValueError("confirmation_revision must be positive")
            for name in (
                "confirmation_sha256", "authority_evidence_sha256", "expected_leaf_candidate_sha256",
                "expected_leaf_lineage_sha256", "expected_context_sha256",
                "expected_commentary_plan_sha256", "expected_proposal_sha256",
            ):
                validate_sha256(getattr(self, name), field_name=name)
            validate_id(self.root_candidate_id, IdKind.CANDIDATE)
            validate_id(self.expected_leaf_candidate_id, IdKind.CANDIDATE)
            if not self.root_candidate_id.startswith("CAND-R2D") or not self.expected_leaf_candidate_id.startswith("CAND-R2D"):
                raise ValueError("Human review authority requires reserved R2D Candidate identities")
            if self.reviewer_kind != "HUMAN" or not isinstance(self.decision, HumanReviewDecision):
                raise ValueError("binding requires an external Human decision")
            if self.one_shot is not True:
                raise ValueError("Human confirmation must be one-shot")
            decided = _utc(self.decided_at, "decided_at")
            expires = _utc(self.expires_at, "expires_at")
            if expires <= decided:
                raise ValueError("expires_at must follow decided_at")
            if isinstance(self.expected_previous_review_revision, bool) or not isinstance(self.expected_previous_review_revision, int) or self.expected_previous_review_revision < 0:
                raise ValueError("expected_previous_review_revision must be non-negative")
            if (self.expected_previous_review_revision == 0) != (self.expected_previous_review_sha256 is None):
                raise ValueError("expected previous review revision/hash are inconsistent")
            if self.expected_previous_review_sha256 is not None:
                validate_sha256(self.expected_previous_review_sha256, field_name="expected_previous_review_sha256")
            codes = _codes(self.reason_codes, "reason_codes", required=self.decision is not HumanReviewDecision.APPROVE)
            object.__setattr__(self, "reason_codes", codes)
            if self.decision is HumanReviewDecision.REVISE:
                if not isinstance(self.correction_request_sha256, str):
                    raise ValueError("REVISE requires correction_request_sha256")
                validate_sha256(self.correction_request_sha256, field_name="correction_request_sha256")
            elif self.correction_request_sha256 is not None:
                raise ValueError("only REVISE may bind a correction request")
        expected = sha256_bytes(canonical_json_bytes(self._body()))
        if self.binding_sha256 and self.binding_sha256 != expected:
            raise ValueError("binding_sha256 mismatch")
        object.__setattr__(self, "binding_sha256", expected)

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "record_kind": "DBD_REASONING_HUMAN_REVIEW_AUTHORITY_BINDING",
            "contract_state": self.contract_state.value,
            "confirmation_ref": self.confirmation_ref,
            "confirmation_revision": self.confirmation_revision,
            "confirmation_sha256": self.confirmation_sha256,
            "reviewer_kind": self.reviewer_kind,
            "decision": None if self.decision is None else self.decision.value,
            "decided_at": self.decided_at,
            "expires_at": self.expires_at,
            "one_shot": self.one_shot,
            "authority_evidence_ref": self.authority_evidence_ref,
            "authority_evidence_sha256": self.authority_evidence_sha256,
            "root_candidate_id": self.root_candidate_id,
            "expected_leaf_candidate_id": self.expected_leaf_candidate_id,
            "expected_leaf_candidate_sha256": self.expected_leaf_candidate_sha256,
            "expected_leaf_lineage_sha256": self.expected_leaf_lineage_sha256,
            "expected_context_sha256": self.expected_context_sha256,
            "expected_commentary_plan_sha256": self.expected_commentary_plan_sha256,
            "expected_proposal_sha256": self.expected_proposal_sha256,
            "expected_previous_review_revision": self.expected_previous_review_revision,
            "expected_previous_review_sha256": self.expected_previous_review_sha256,
            "reason_codes": None if self.reason_codes is None else list(self.reason_codes),
            "correction_request_sha256": self.correction_request_sha256,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "binding_sha256": self.binding_sha256}


@dataclass(frozen=True, slots=True)
class DbDReasoningHumanReviewRecord:
    schema_version: str
    root_candidate_id: str
    leaf_candidate_id: str
    leaf_candidate_sha256: str
    leaf_lineage_sha256: str
    match_id: str
    event_id: str
    event_revision: int
    context_sha256: str
    commentary_plan_sha256: str
    proposal_sha256: str
    review_revision: int
    previous_review_sha256: str | None
    decision: HumanReviewDecision
    reason_codes: tuple[str, ...]
    correction_request_sha256: str | None
    authority_binding_sha256: str
    confirmation_sha256: str
    reviewed_at: str
    review_sha256: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != HUMAN_REVIEW_SCHEMA_VERSION:
            raise ValueError("unsupported Human review record")
        validate_id(self.root_candidate_id, IdKind.CANDIDATE)
        validate_id(self.leaf_candidate_id, IdKind.CANDIDATE)
        if not self.root_candidate_id.startswith("CAND-R2D") or not self.leaf_candidate_id.startswith("CAND-R2D"):
            raise ValueError("Human review requires reserved R2D Candidate identities")
        validate_id(self.match_id, IdKind.GAME_MATCH)
        validate_id(self.event_id, IdKind.GAME_EVENT)
        if self.root_candidate_id != self.leaf_candidate_id:
            raise ValueError("C1 review requires root and leaf to be identical")
        if isinstance(self.event_revision, bool) or not isinstance(self.event_revision, int) or self.event_revision < 1:
            raise ValueError("event_revision must be positive")
        if isinstance(self.review_revision, bool) or not isinstance(self.review_revision, int) or self.review_revision < 1:
            raise ValueError("review_revision must be positive")
        if (self.review_revision == 1) != (self.previous_review_sha256 is None):
            raise ValueError("review revision and previous hash are inconsistent")
        for name in (
            "leaf_candidate_sha256", "leaf_lineage_sha256", "context_sha256",
            "commentary_plan_sha256", "proposal_sha256", "authority_binding_sha256",
            "confirmation_sha256",
        ):
            validate_sha256(getattr(self, name), field_name=name)
        if self.previous_review_sha256 is not None:
            validate_sha256(self.previous_review_sha256, field_name="previous_review_sha256")
        if not isinstance(self.decision, HumanReviewDecision):
            raise ValueError("decision is invalid")
        object.__setattr__(self, "reason_codes", _codes(self.reason_codes, "reason_codes", required=self.decision is not HumanReviewDecision.APPROVE))
        if self.decision is HumanReviewDecision.REVISE:
            if not isinstance(self.correction_request_sha256, str):
                raise ValueError("REVISE requires correction_request_sha256")
            validate_sha256(self.correction_request_sha256, field_name="correction_request_sha256")
        elif self.correction_request_sha256 is not None:
            raise ValueError("only REVISE may bind a correction request")
        _utc(self.reviewed_at, "reviewed_at")
        expected = sha256_bytes(canonical_json_bytes(self._body()))
        if self.review_sha256 and self.review_sha256 != expected:
            raise ValueError("review_sha256 mismatch")
        object.__setattr__(self, "review_sha256", expected)

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version, "record_kind": "DBD_REASONING_HUMAN_REVIEW",
            "root_candidate_id": self.root_candidate_id, "leaf_candidate_id": self.leaf_candidate_id,
            "leaf_candidate_sha256": self.leaf_candidate_sha256, "leaf_lineage_sha256": self.leaf_lineage_sha256,
            "match_id": self.match_id, "event_id": self.event_id, "event_revision": self.event_revision,
            "context_sha256": self.context_sha256, "commentary_plan_sha256": self.commentary_plan_sha256,
            "proposal_sha256": self.proposal_sha256, "review_revision": self.review_revision,
            "previous_review_sha256": self.previous_review_sha256, "decision": self.decision.value,
            "reason_codes": list(self.reason_codes), "correction_request_sha256": self.correction_request_sha256,
            "authority_binding_sha256": self.authority_binding_sha256,
            "confirmation_sha256": self.confirmation_sha256, "reviewed_at": self.reviewed_at,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "review_sha256": self.review_sha256}


@dataclass(frozen=True, slots=True)
class CurrentHumanReviewSnapshot:
    """Runtime-only current values resolved by the future C2 server-side CAS."""

    root_candidate_id: str
    leaf_candidate: CommentaryCandidate = field(repr=False)
    leaf_lineage: DbDReasoningCandidateLineage = field(repr=False)
    context: DbDReasoningContextEnvelope = field(repr=False)
    plan: CommentaryPlan = field(repr=False)
    review_head_revision: int
    review_head_sha256: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.leaf_candidate, CommentaryCandidate) or not isinstance(self.leaf_lineage, DbDReasoningCandidateLineage):
            raise ValueError("snapshot requires canonical Candidate and lineage")
        if not isinstance(self.context, DbDReasoningContextEnvelope) or not isinstance(self.plan, CommentaryPlan):
            raise ValueError("snapshot requires canonical Context and Plan")
        self.context.require_dispatchable()
        validate_id(self.root_candidate_id, IdKind.CANDIDATE)
        if not self.root_candidate_id.startswith("CAND-R2D"):
            raise ValueError("Human review snapshot requires the reserved R2D Candidate identity")
        if self.root_candidate_id != self.leaf_candidate.candidate_id:
            raise ValueError("C1 snapshot requires root and leaf to be identical")
        if isinstance(self.review_head_revision, bool) or not isinstance(self.review_head_revision, int) or self.review_head_revision < 0:
            raise ValueError("review head revision must be non-negative")
        if (self.review_head_revision == 0) != (self.review_head_sha256 is None):
            raise ValueError("review head revision/hash are inconsistent")
        if self.review_head_sha256 is not None:
            validate_sha256(self.review_head_sha256, field_name="review_head_sha256")
        admit_reasoning_candidate_lineage_record(
            self.leaf_lineage.to_dict(), candidate_payload=self.leaf_candidate.to_dict(),
        )
        context_sha = self.context.to_dict()["context_sha256"]
        plan_sha = self.plan.to_dict()["commentary_plan_sha256"]
        if (
            self.leaf_lineage.candidate_id != self.leaf_candidate.candidate_id
            or self.leaf_lineage.context_sha256 != context_sha
            or self.leaf_lineage.commentary_plan_sha256 != plan_sha
            or (self.plan.match_id, self.plan.event_id, self.plan.event_revision)
            != (self.leaf_lineage.match_id, self.leaf_lineage.event_id, self.leaf_lineage.event_revision)
        ):
            raise ValueError("current review snapshot coordinates do not match")


@dataclass(frozen=True, slots=True)
class HumanReviewAdmissionResult:
    passed: bool
    error_codes: tuple[str, ...]
    review_record: DbDReasoningHumanReviewRecord | None = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.passed, bool) or self.passed == bool(self.error_codes):
            raise ValueError("review admission pass state is invalid")
        object.__setattr__(self, "error_codes", _codes(self.error_codes, "error_codes", required=not self.passed))
        if self.passed != isinstance(self.review_record, DbDReasoningHumanReviewRecord):
            raise ValueError("review record exists exactly when admission passed")


_AUTHORITY_KEYS = frozenset({
    "schema_version", "record_kind", "contract_state", "confirmation_ref",
    "confirmation_revision", "confirmation_sha256", "reviewer_kind", "decision",
    "decided_at", "expires_at", "one_shot", "authority_evidence_ref",
    "authority_evidence_sha256", "root_candidate_id", "expected_leaf_candidate_id",
    "expected_leaf_candidate_sha256", "expected_leaf_lineage_sha256",
    "expected_context_sha256", "expected_commentary_plan_sha256",
    "expected_proposal_sha256", "expected_previous_review_revision",
    "expected_previous_review_sha256", "reason_codes", "correction_request_sha256",
    "binding_sha256",
})
_REVIEW_KEYS = frozenset({
    "schema_version", "record_kind", "root_candidate_id", "leaf_candidate_id",
    "leaf_candidate_sha256", "leaf_lineage_sha256", "match_id", "event_id",
    "event_revision", "context_sha256", "commentary_plan_sha256", "proposal_sha256",
    "review_revision", "previous_review_sha256", "decision", "reason_codes",
    "correction_request_sha256", "authority_binding_sha256", "confirmation_sha256",
    "reviewed_at", "review_sha256",
})


def admit_reasoning_human_review_authority_record(record: Mapping[str, Any]) -> DbDReasoningHumanReviewAuthorityBinding:
    if not isinstance(record, Mapping) or set(record) != _AUTHORITY_KEYS:
        raise ValueError("Human review authority record has unknown or missing fields")
    if record.get("record_kind") != "DBD_REASONING_HUMAN_REVIEW_AUTHORITY_BINDING":
        raise ValueError("Human review authority record_kind is invalid")
    state = HumanReviewContractState(record["contract_state"])
    decision = None if record["decision"] is None else HumanReviewDecision(record["decision"])
    reason_codes = None if record["reason_codes"] is None else _codes(record["reason_codes"], "reason_codes")
    binding = DbDReasoningHumanReviewAuthorityBinding(
        record["schema_version"], state, record["confirmation_ref"], record["confirmation_revision"],
        record["confirmation_sha256"], record["reviewer_kind"], decision, record["decided_at"],
        record["expires_at"], record["one_shot"], record["authority_evidence_ref"],
        record["authority_evidence_sha256"], record["root_candidate_id"],
        record["expected_leaf_candidate_id"], record["expected_leaf_candidate_sha256"],
        record["expected_leaf_lineage_sha256"], record["expected_context_sha256"],
        record["expected_commentary_plan_sha256"], record["expected_proposal_sha256"],
        record["expected_previous_review_revision"], record["expected_previous_review_sha256"],
        reason_codes, record["correction_request_sha256"], record["binding_sha256"],
    )
    if binding.to_dict() != dict(record):
        raise ValueError("Human review authority record is not canonical")
    return binding


def admit_reasoning_human_review_record(record: Mapping[str, Any]) -> DbDReasoningHumanReviewRecord:
    if not isinstance(record, Mapping) or set(record) != _REVIEW_KEYS:
        raise ValueError("Human review record has unknown or missing fields")
    if record.get("record_kind") != "DBD_REASONING_HUMAN_REVIEW":
        raise ValueError("Human review record_kind is invalid")
    review = DbDReasoningHumanReviewRecord(
        record["schema_version"], record["root_candidate_id"], record["leaf_candidate_id"],
        record["leaf_candidate_sha256"], record["leaf_lineage_sha256"], record["match_id"],
        record["event_id"], record["event_revision"], record["context_sha256"],
        record["commentary_plan_sha256"], record["proposal_sha256"], record["review_revision"],
        record["previous_review_sha256"], HumanReviewDecision(record["decision"]),
        _codes(record["reason_codes"], "reason_codes"), record["correction_request_sha256"],
        record["authority_binding_sha256"], record["confirmation_sha256"],
        record["reviewed_at"], record["review_sha256"],
    )
    if review.to_dict() != dict(record):
        raise ValueError("Human review record is not canonical")
    return review


def admit_human_review(
    *, authority_record: Mapping[str, Any], current: CurrentHumanReviewSnapshot,
    previous_review: DbDReasoningHumanReviewRecord | None, evaluated_at: str,
) -> HumanReviewAdmissionResult:
    """Create inert review Evidence after exact comparison; never grant export authority."""

    try:
        binding = admit_reasoning_human_review_authority_record(authority_record)
        evaluated = _utc(evaluated_at, "evaluated_at")
    except (TypeError, ValueError):
        return HumanReviewAdmissionResult(False, ("AUTHORITY_BINDING_INVALID",), None)
    if not isinstance(current, CurrentHumanReviewSnapshot):
        return HumanReviewAdmissionResult(False, ("CURRENT_SNAPSHOT_INVALID",), None)
    try:
        _revalidate_current_snapshot(current)
    except (TypeError, ValueError):
        return HumanReviewAdmissionResult(False, ("CURRENT_SNAPSHOT_INVALID",), None)
    if binding.contract_state is not HumanReviewContractState.BOUND_VERIFIED:
        return HumanReviewAdmissionResult(False, ("HUMAN_AUTHORITY_NOT_BOUND",), None)
    assert binding.expires_at is not None and binding.decided_at is not None
    if not (_utc(binding.decided_at, "decided_at") <= evaluated < _utc(binding.expires_at, "expires_at")):
        return HumanReviewAdmissionResult(False, ("HUMAN_CONFIRMATION_EXPIRED",), None)
    if previous_review is None:
        previous_revision, previous_sha = 0, None
    elif not isinstance(previous_review, DbDReasoningHumanReviewRecord):
        return HumanReviewAdmissionResult(False, ("PREVIOUS_REVIEW_INVALID",), None)
    else:
        try:
            if admit_reasoning_human_review_record(previous_review.to_dict()) != previous_review:
                raise ValueError("previous review reconstruction mismatch")
        except (TypeError, ValueError):
            return HumanReviewAdmissionResult(False, ("PREVIOUS_REVIEW_INVALID",), None)
        previous_revision, previous_sha = previous_review.review_revision, previous_review.review_sha256
        if (
            previous_review.root_candidate_id != current.root_candidate_id
            or previous_review.leaf_candidate_id != current.leaf_candidate.candidate_id
            or previous_review.leaf_candidate_sha256 != current.leaf_candidate.to_dict()["commentary_candidate_sha256"]
            or previous_review.leaf_lineage_sha256 != current.leaf_lineage.lineage_sha256
            or (previous_review.match_id, previous_review.event_id, previous_review.event_revision)
            != (current.leaf_lineage.match_id, current.leaf_lineage.event_id, current.leaf_lineage.event_revision)
            or previous_review.context_sha256 != current.context.to_dict()["context_sha256"]
            or previous_review.commentary_plan_sha256 != current.plan.to_dict()["commentary_plan_sha256"]
            or previous_review.proposal_sha256 != current.leaf_lineage.proposal.to_dict()["proposal_sha256"]
        ):
            return HumanReviewAdmissionResult(False, ("PREVIOUS_REVIEW_CROSSING",), None)
    candidate = current.leaf_candidate.to_dict()
    lineage = current.leaf_lineage
    context_sha = current.context.to_dict()["context_sha256"]
    plan_sha = current.plan.to_dict()["commentary_plan_sha256"]
    expected = (
        binding.root_candidate_id, binding.expected_leaf_candidate_id,
        binding.expected_leaf_candidate_sha256, binding.expected_leaf_lineage_sha256,
        binding.expected_context_sha256, binding.expected_commentary_plan_sha256,
        binding.expected_proposal_sha256, binding.expected_previous_review_revision,
        binding.expected_previous_review_sha256,
    )
    actual = (
        current.root_candidate_id, current.leaf_candidate.candidate_id,
        candidate["commentary_candidate_sha256"], lineage.lineage_sha256,
        context_sha, plan_sha, lineage.proposal.to_dict()["proposal_sha256"],
        current.review_head_revision, current.review_head_sha256,
    )
    if expected != actual or (previous_revision, previous_sha) != (current.review_head_revision, current.review_head_sha256):
        return HumanReviewAdmissionResult(False, ("CURRENT_COORDINATE_MISMATCH",), None)
    assert binding.decision is not None and binding.reason_codes is not None and binding.confirmation_sha256 is not None
    assert binding.decided_at is not None
    if previous_review is not None and (
        _utc(binding.decided_at, "decided_at") <= _utc(previous_review.reviewed_at, "reviewed_at")
        or binding.confirmation_sha256 == previous_review.confirmation_sha256
    ):
        return HumanReviewAdmissionResult(False, ("HUMAN_CONFIRMATION_REPLAYED",), None)
    record = DbDReasoningHumanReviewRecord(
        HUMAN_REVIEW_SCHEMA_VERSION, current.root_candidate_id, current.leaf_candidate.candidate_id,
        candidate["commentary_candidate_sha256"], lineage.lineage_sha256,
        lineage.match_id, lineage.event_id, lineage.event_revision, context_sha, plan_sha,
        lineage.proposal.to_dict()["proposal_sha256"], previous_revision + 1, previous_sha,
        binding.decision, binding.reason_codes, binding.correction_request_sha256,
        binding.binding_sha256, binding.confirmation_sha256, binding.decided_at,
    )
    return HumanReviewAdmissionResult(True, (), record)


def _revalidate_current_snapshot(current: CurrentHumanReviewSnapshot) -> None:
    """Re-run every nested admission at use time; frozen objects are not a trust boundary."""

    CurrentHumanReviewSnapshot(
        current.root_candidate_id, current.leaf_candidate, current.leaf_lineage,
        current.context, current.plan, current.review_head_revision,
        current.review_head_sha256,
    )


__all__ = [
    "CurrentHumanReviewSnapshot", "DbDReasoningHumanReviewAuthorityBinding",
    "DbDReasoningHumanReviewRecord", "HUMAN_REVIEW_SCHEMA_VERSION",
    "HumanReviewAdmissionResult", "HumanReviewContractState", "HumanReviewDecision",
    "admit_human_review", "admit_reasoning_human_review_authority_record",
    "admit_reasoning_human_review_record",
]
