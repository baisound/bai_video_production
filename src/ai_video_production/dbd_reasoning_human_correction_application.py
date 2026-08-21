"""TASK-054 R2D-C3 opaque Human correction application boundary.

The resolver is the only component allowed to expose the Human-edited bytes.
Those bytes are admitted immediately and are never serialized by this module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any, Callable, Mapping, Protocol

from .dbd_reasoning_candidate_lineage import (
    DbDReasoningCandidateComposer, DbDReasoningCandidateCreationResult,
    DbDReasoningCandidateLineage,
)
from .dbd_reasoning_contracts import DbDReasoningContextEnvelope
from .dbd_reasoning_human_review import CurrentHumanReviewSnapshot
from .dbd_reasoning_human_review_application import (
    HumanReviewHeadExpectation, _ApplicationRegistration, _CAPABILITY_PROOF,
)
from .errors import ProductError, ProductErrorCategory
from .game_commentary import CommentaryCandidate, CommentaryCandidateStore, CommentaryPlan
from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


_CORRECTION_REF_RE = re.compile(r"human-correction://dbd-review/[0-9A-HJKMNP-TV-Z]{26}")
_EVIDENCE_REF_RE = re.compile(r"human-evidence://dbd-review/sha256/[0-9a-f]{64}")
_CORRECTION_SCHEMA_VERSION = "1.0.0"


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


@dataclass(frozen=True, slots=True)
class DbDReasoningHumanCorrectionSubmission:
    schema_version: str
    correction_ref: str
    reviewer_kind: str
    one_shot: bool
    submitted_at: str
    expires_at: str
    parent_candidate_id: str
    parent_candidate_sha256: str
    parent_lineage_sha256: str
    correction_review_sha256: str
    correction_request_sha256: str
    context_sha256: str
    commentary_plan_sha256: str
    proposal_sha256: str
    child_candidate_id: str
    child_created_at: str
    edited_output_sha256: str
    evidence_ref: str
    evidence_sha256: str
    binding_sha256: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != _CORRECTION_SCHEMA_VERSION:
            raise ValueError("unsupported Human correction submission")
        if not isinstance(self.correction_ref, str) or not _CORRECTION_REF_RE.fullmatch(self.correction_ref):
            raise ValueError("correction_ref must use the canonical opaque namespace")
        if self.reviewer_kind != "HUMAN" or self.one_shot is not True:
            raise ValueError("correction submission requires external one-shot Human authority")
        if _utc(self.expires_at, "expires_at") <= _utc(self.submitted_at, "submitted_at"):
            raise ValueError("correction expires_at must follow submitted_at")
        for name in ("parent_candidate_id", "child_candidate_id"):
            validate_id(getattr(self, name), IdKind.CANDIDATE)
            if not getattr(self, name).startswith("CAND-R2D"):
                raise ValueError("correction requires reserved R2D Candidate identities")
        if self.parent_candidate_id == self.child_candidate_id:
            raise ValueError("correction child cannot equal parent")
        _utc(self.child_created_at, "child_created_at")
        for name in (
            "parent_candidate_sha256", "parent_lineage_sha256", "correction_review_sha256",
            "correction_request_sha256", "context_sha256", "commentary_plan_sha256",
            "proposal_sha256", "edited_output_sha256", "evidence_sha256",
        ):
            validate_sha256(getattr(self, name), field_name=name)
        if not isinstance(self.evidence_ref, str) or not _EVIDENCE_REF_RE.fullmatch(self.evidence_ref):
            raise ValueError("evidence_ref must be body-free and canonical")
        expected = sha256_bytes(canonical_json_bytes(self._body()))
        if self.binding_sha256 and self.binding_sha256 != expected:
            raise ValueError("correction binding_sha256 mismatch")
        object.__setattr__(self, "binding_sha256", expected)

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version, "record_kind": "DBD_REASONING_HUMAN_CORRECTION_SUBMISSION",
            "correction_ref": self.correction_ref, "reviewer_kind": self.reviewer_kind,
            "one_shot": self.one_shot, "submitted_at": self.submitted_at, "expires_at": self.expires_at,
            "parent_candidate_id": self.parent_candidate_id, "parent_candidate_sha256": self.parent_candidate_sha256,
            "parent_lineage_sha256": self.parent_lineage_sha256,
            "correction_review_sha256": self.correction_review_sha256,
            "correction_request_sha256": self.correction_request_sha256,
            "context_sha256": self.context_sha256, "commentary_plan_sha256": self.commentary_plan_sha256,
            "proposal_sha256": self.proposal_sha256, "child_candidate_id": self.child_candidate_id,
            "child_created_at": self.child_created_at, "edited_output_sha256": self.edited_output_sha256,
            "evidence_ref": self.evidence_ref, "evidence_sha256": self.evidence_sha256,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "binding_sha256": self.binding_sha256}


_SUBMISSION_KEYS = frozenset({
    "schema_version", "record_kind", "correction_ref", "reviewer_kind", "one_shot", "submitted_at",
    "expires_at", "parent_candidate_id", "parent_candidate_sha256", "parent_lineage_sha256",
    "correction_review_sha256", "correction_request_sha256", "context_sha256", "commentary_plan_sha256",
    "proposal_sha256", "child_candidate_id", "child_created_at", "edited_output_sha256", "evidence_ref",
    "evidence_sha256", "binding_sha256",
})


def admit_reasoning_human_correction_submission(record: Mapping[str, object]) -> DbDReasoningHumanCorrectionSubmission:
    if not isinstance(record, Mapping) or set(record) != _SUBMISSION_KEYS:
        raise ValueError("Human correction submission has unknown or missing fields")
    if record.get("record_kind") != "DBD_REASONING_HUMAN_CORRECTION_SUBMISSION":
        raise ValueError("Human correction submission record_kind is invalid")
    admitted = DbDReasoningHumanCorrectionSubmission(
        record["schema_version"], record["correction_ref"], record["reviewer_kind"], record["one_shot"],
        record["submitted_at"], record["expires_at"], record["parent_candidate_id"],
        record["parent_candidate_sha256"], record["parent_lineage_sha256"],
        record["correction_review_sha256"], record["correction_request_sha256"], record["context_sha256"],
        record["commentary_plan_sha256"], record["proposal_sha256"], record["child_candidate_id"],
        record["child_created_at"], record["edited_output_sha256"], record["evidence_ref"],
        record["evidence_sha256"], record["binding_sha256"],
    )
    if admitted.to_dict() != dict(record):
        raise ValueError("Human correction submission is not exact canonical content")
    return admitted


@dataclass(frozen=True, slots=True)
class ResolvedHumanCorrectionSubmission:
    submission: DbDReasoningHumanCorrectionSubmission = field(repr=False)
    edited_output: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.submission, DbDReasoningHumanCorrectionSubmission) or not isinstance(self.edited_output, bytes):
            raise TypeError("resolved Human correction submission is invalid")
        if sha256_bytes(self.edited_output) != self.submission.edited_output_sha256:
            raise ValueError("resolved Human correction output digest differs from its binding")


class HumanCorrectionSubmissionResolver(Protocol):
    def resolve(self, correction_ref: str) -> ResolvedHumanCorrectionSubmission: ...


class ReasoningCorrectionCurrentSnapshotResolver(Protocol):
    def resolve(self, candidate_id: str) -> CurrentHumanReviewSnapshot: ...


class _InternalCorrectionToken:
    __slots__ = (
        "_proof", "store_identity", "binding_sha256", "correction_ref", "parent_candidate_id",
        "parent_candidate_sha256", "parent_lineage_sha256", "context_sha256", "commentary_plan_sha256",
        "proposal_sha256", "correction_review_sha256", "correction_request_sha256", "review_head_revision",
        "review_head_sha256", "edited_output_sha256", "evaluated_at",
    )
    def __init__(self, proof: object, store_identity: int, submission: DbDReasoningHumanCorrectionSubmission, current: CurrentHumanReviewSnapshot, evaluated_at: str) -> None:
        if proof is not _CAPABILITY_PROOF:
            raise TypeError("internal correction token cannot be constructed externally")
        self._proof, self.store_identity = proof, store_identity
        self.binding_sha256, self.correction_ref = submission.binding_sha256, submission.correction_ref
        self.parent_candidate_id = current.root_candidate_id
        self.parent_candidate_sha256, self.parent_lineage_sha256 = submission.parent_candidate_sha256, submission.parent_lineage_sha256
        self.context_sha256, self.commentary_plan_sha256, self.proposal_sha256 = submission.context_sha256, submission.commentary_plan_sha256, submission.proposal_sha256
        self.correction_review_sha256, self.correction_request_sha256 = submission.correction_review_sha256, submission.correction_request_sha256
        self.review_head_revision, self.review_head_sha256 = current.review_head_revision, current.review_head_sha256
        self.edited_output_sha256, self.evaluated_at = submission.edited_output_sha256, evaluated_at


def _valid_correction_token(token: object, store: object, submission: DbDReasoningHumanCorrectionSubmission, current: CurrentHumanReviewSnapshot, evaluated_at: str) -> bool:
    return (
        isinstance(token, _InternalCorrectionToken) and token._proof is _CAPABILITY_PROOF
        and token.store_identity == id(store) and token.binding_sha256 == submission.binding_sha256
        and token.correction_ref == submission.correction_ref and token.parent_candidate_id == current.root_candidate_id
        and (token.parent_candidate_sha256, token.parent_lineage_sha256) == (submission.parent_candidate_sha256, submission.parent_lineage_sha256)
        and (token.context_sha256, token.commentary_plan_sha256, token.proposal_sha256) == (submission.context_sha256, submission.commentary_plan_sha256, submission.proposal_sha256)
        and (token.correction_review_sha256, token.correction_request_sha256) == (submission.correction_review_sha256, submission.correction_request_sha256)
        and (token.review_head_revision, token.review_head_sha256) == (current.review_head_revision, current.review_head_sha256)
        and token.edited_output_sha256 == submission.edited_output_sha256 and token.evaluated_at == evaluated_at
    )


@dataclass(frozen=True, slots=True)
class HumanCorrectionAppendResult:
    status: str
    candidate: CommentaryCandidate = field(repr=False)
    lineage: DbDReasoningCandidateLineage = field(repr=False)
    submission: DbDReasoningHumanCorrectionSubmission = field(repr=False)

    def __post_init__(self) -> None:
        if self.status not in {"APPENDED", "IDEMPOTENT_EXISTING"}:
            raise ValueError("correction append status is invalid")
        if not isinstance(self.candidate, CommentaryCandidate) or not isinstance(self.lineage, DbDReasoningCandidateLineage) or not isinstance(self.submission, DbDReasoningHumanCorrectionSubmission):
            raise ValueError("correction append result requires canonical objects")
        from .dbd_reasoning_candidate_lineage import admit_reasoning_candidate_lineage_record
        admitted_submission = admit_reasoning_human_correction_submission(self.submission.to_dict())
        if admitted_submission.to_dict() != self.submission.to_dict():
            raise ValueError("correction append result submission is not canonical")
        admitted = admit_reasoning_candidate_lineage_record(self.lineage.to_dict(), candidate_payload=self.candidate.to_dict())
        if (
            admitted.origin != "TUNED_REASONING_CORRECTION" or admitted.schema_version != "1.1.0"
            or self.candidate.to_dict().get("schema_version") != "1.2.0"
            or (admitted.candidate_id, admitted.commentary_candidate_sha256) != (admitted_submission.child_candidate_id, self.candidate.to_dict()["commentary_candidate_sha256"])
            or (admitted.parent_candidate_id, admitted.parent_candidate_sha256) != (admitted_submission.parent_candidate_id, admitted_submission.parent_candidate_sha256)
            or admitted.correction_request_review_sha256 != admitted_submission.correction_review_sha256
            or (admitted.correction_submission_ref, admitted.correction_submission_binding_sha256) != (admitted_submission.correction_ref, admitted_submission.binding_sha256)
            or admitted.raw_output_sha256 != admitted_submission.edited_output_sha256
            or self.candidate.created_at != admitted_submission.child_created_at
            or admitted.context_sha256 != admitted_submission.context_sha256
            or admitted.commentary_plan_sha256 != admitted_submission.commentary_plan_sha256
        ):
            raise ValueError("correction append result crosses its submission")


class DbDReasoningHumanCorrectionApplication:
    def __init__(
        self, *, store: CommentaryCandidateStore, correction_resolver: HumanCorrectionSubmissionResolver,
        current_snapshot_resolver: ReasoningCorrectionCurrentSnapshotResolver,
        clock: Callable[[], str],
    ) -> None:
        if not isinstance(store, CommentaryCandidateStore):
            raise TypeError("store must be CommentaryCandidateStore")
        if not callable(getattr(correction_resolver, "resolve", None)) or not callable(getattr(current_snapshot_resolver, "resolve", None)) or not callable(clock):
            raise TypeError("correction application dependencies are invalid")
        self._store, self._resolver, self._current, self._clock = store, correction_resolver, current_snapshot_resolver, clock
        self.__registration = _ApplicationRegistration(_CAPABILITY_PROOF, id(store))
        store._configure_reasoning_review_current_resolver(self.__registration, current_snapshot_resolver)

    def apply_correction(
        self, *, parent_candidate_id: str, correction_ref: str, expected_review_head: HumanReviewHeadExpectation,
    ) -> HumanCorrectionAppendResult:
        validate_id(parent_candidate_id, IdKind.CANDIDATE)
        if not parent_candidate_id.startswith("CAND-R2D") or not isinstance(correction_ref, str) or not isinstance(expected_review_head, HumanReviewHeadExpectation):
            raise TypeError("correction command requires opaque reference and expected review head")
        try:
            resolved = self._resolver.resolve(correction_ref)
            if not isinstance(resolved, ResolvedHumanCorrectionSubmission):
                raise TypeError("resolver returned noncanonical submission")
            submission = resolved.submission
        except Exception as exc:
            raise ProductError("ERR_DBD_CORRECTION_RESOLUTION", "Human correction submission could not be resolved", ProductErrorCategory.AUTHORIZATION) from exc
        if submission.correction_ref != correction_ref or submission.parent_candidate_id != parent_candidate_id:
            raise ValueError("resolved Human correction does not match requested identity")
        try:
            current = self._current.resolve(parent_candidate_id)
        except Exception as exc:
            raise ProductError("ERR_DBD_CORRECTION_CURRENT_RESOLUTION", "Current correction snapshot could not be resolved", ProductErrorCategory.DATA_INTEGRITY) from exc
        if not isinstance(current, CurrentHumanReviewSnapshot) or current.root_candidate_id != parent_candidate_id:
            raise ValueError("current correction resolver returned a crossing snapshot")
        try:
            evaluated_at = self._clock()
            now = _utc(evaluated_at, "clock")
        except Exception as exc:
            raise ProductError("ERR_DBD_CORRECTION_CLOCK", "Server correction clock is unavailable", ProductErrorCategory.STATE) from exc
        if now < _utc(submission.submitted_at, "submitted_at") or _utc(submission.expires_at, "expires_at") <= now:
            raise ProductError("ERR_DBD_CORRECTION_EXPIRED", "Human correction submission has expired", ProductErrorCategory.AUTHORIZATION)
        parent, parent_lineage = current.leaf_candidate, current.leaf_lineage
        parent_payload, lineage_payload = parent.to_dict(), parent_lineage.to_dict()
        if (
            parent_payload["commentary_candidate_sha256"] != submission.parent_candidate_sha256
            or lineage_payload["lineage_sha256"] != submission.parent_lineage_sha256
            or lineage_payload["context_sha256"] != submission.context_sha256
            or lineage_payload["commentary_plan_sha256"] != submission.commentary_plan_sha256
            or lineage_payload["proposal"]["proposal_sha256"] != submission.proposal_sha256
        ):
            raise ValueError("Human correction binding crosses current parent")
        composed = DbDReasoningCandidateComposer().create_correction(
            raw_output=resolved.edited_output, context=current.context, plan=current.plan,
            parent_candidate=parent, parent_lineage=parent_lineage,
            correction_request_review_sha256=submission.correction_review_sha256,
            correction_submission_ref=submission.correction_ref,
            correction_submission_binding_sha256=submission.binding_sha256,
            candidate_id=submission.child_candidate_id, created_at=submission.child_created_at,
        )
        if not composed.passed or composed.candidate is None or composed.lineage is None:
            raise ProductError("ERR_DBD_CORRECTION_ADMISSION_REJECTED", ",".join(composed.error_codes), ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        token = _InternalCorrectionToken(_CAPABILITY_PROOF, id(self._store), submission, current, evaluated_at)
        return self._store._append_resolved_human_correction(
            token=token, submission=submission, current=current, child_candidate=composed.candidate,
            child_lineage=composed.lineage, expected_review_head=expected_review_head, evaluated_at=token.evaluated_at,
        )


__all__ = [
    "DbDReasoningHumanCorrectionApplication", "DbDReasoningHumanCorrectionSubmission",
    "HumanCorrectionAppendResult", "HumanCorrectionSubmissionResolver",
    "ReasoningCorrectionCurrentSnapshotResolver", "ResolvedHumanCorrectionSubmission",
    "admit_reasoning_human_correction_submission",
]
