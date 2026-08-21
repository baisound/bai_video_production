"""TASK-054 R2D-C2 Human-review application boundary.

Resolvers are trusted composition-root dependencies. Operator input contains
only opaque identities and an optimistic head expectation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping, Protocol

from .dbd_reasoning_human_review import (
    CurrentHumanReviewSnapshot,
    DbDReasoningHumanReviewAuthorityBinding,
    DbDReasoningHumanReviewRecord,
    admit_reasoning_human_review_authority_record,
)
from .game_commentary import CommentaryCandidateStore
from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, validate_id
from .serialization import validate_sha256


_CAPABILITY_PROOF = object()


class _ApplicationRegistration:
    __slots__ = ("_proof", "store_identity")
    def __init__(self, proof: object, store_identity: int) -> None:
        if proof is not _CAPABILITY_PROOF:
            raise TypeError("internal registration cannot be constructed externally")
        self._proof, self.store_identity = proof, store_identity


class _InternalAdmissionToken:
    __slots__ = ("_proof", "store_identity", "authority_sha256", "candidate_id", "context_sha256", "evaluated_at")
    def __init__(self, proof: object, store_identity: int, authority_sha256: str, candidate_id: str, context_sha256: str, evaluated_at: str) -> None:
        if proof is not _CAPABILITY_PROOF:
            raise TypeError("internal admission token cannot be constructed externally")
        self._proof, self.store_identity = proof, store_identity
        self.authority_sha256, self.candidate_id = authority_sha256, candidate_id
        self.context_sha256, self.evaluated_at = context_sha256, evaluated_at


def _valid_registration(token: object, store: object) -> bool:
    return isinstance(token, _ApplicationRegistration) and token._proof is _CAPABILITY_PROOF and token.store_identity == id(store)


def _valid_admission_token(token: object, store: object, authority: DbDReasoningHumanReviewAuthorityBinding, current: CurrentHumanReviewSnapshot, evaluated_at: str) -> bool:
    return (
        isinstance(token, _InternalAdmissionToken) and token._proof is _CAPABILITY_PROOF
        and token.store_identity == id(store) and token.authority_sha256 == authority.binding_sha256
        and token.candidate_id == current.root_candidate_id
        and token.context_sha256 == current.context.to_dict()["context_sha256"]
        and token.evaluated_at == evaluated_at
    )


class HumanReviewAuthorityResolver(Protocol):
    def resolve(self, confirmation_ref: str) -> Mapping[str, object]: ...


class ReasoningReviewCurrentSnapshotResolver(Protocol):
    def resolve(self, candidate_id: str) -> CurrentHumanReviewSnapshot: ...


@dataclass(frozen=True, slots=True)
class HumanReviewHeadExpectation:
    revision: int
    review_sha256: str | None

    def __post_init__(self) -> None:
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 0:
            raise ValueError("review head revision must be non-negative")
        if (self.revision == 0) != (self.review_sha256 is None):
            raise ValueError("review head revision/hash are inconsistent")
        if self.review_sha256 is not None:
            validate_sha256(self.review_sha256, field_name="review_sha256")


@dataclass(frozen=True, slots=True)
class HumanReviewAppendResult:
    status: str
    review: DbDReasoningHumanReviewRecord = field(repr=False)

    def __post_init__(self) -> None:
        if self.status not in {"APPENDED", "IDEMPOTENT_EXISTING"}:
            raise ValueError("review append status is invalid")
        if not isinstance(self.review, DbDReasoningHumanReviewRecord):
            raise ValueError("review append result requires canonical review")


class DbDReasoningHumanReviewApplication:
    def __init__(
        self, *, store: CommentaryCandidateStore,
        authority_resolver: HumanReviewAuthorityResolver,
        current_snapshot_resolver: ReasoningReviewCurrentSnapshotResolver,
        clock: Callable[[], str],
    ) -> None:
        if not isinstance(store, CommentaryCandidateStore):
            raise TypeError("store must be CommentaryCandidateStore")
        if not callable(getattr(authority_resolver, "resolve", None)) or not callable(getattr(current_snapshot_resolver, "resolve", None)) or not callable(clock):
            raise TypeError("review application dependencies are invalid")
        self._store = store
        self._authority_resolver = authority_resolver
        self._current_snapshot_resolver = current_snapshot_resolver
        self._clock = clock
        self.__registration = _ApplicationRegistration(_CAPABILITY_PROOF, id(store))
        store._configure_reasoning_review_current_resolver(self.__registration, current_snapshot_resolver)

    def apply_review(
        self, *, candidate_id: str, confirmation_ref: str,
        expected_head: HumanReviewHeadExpectation,
    ) -> HumanReviewAppendResult:
        validate_id(candidate_id, IdKind.CANDIDATE)
        if not candidate_id.startswith("CAND-R2D"):
            raise ValueError("Human reasoning review requires reserved Candidate identity")
        if not isinstance(confirmation_ref, str) or not isinstance(expected_head, HumanReviewHeadExpectation):
            raise TypeError("review command requires opaque confirmation ref and head expectation")
        try:
            authority_record = self._authority_resolver.resolve(confirmation_ref)
            authority: DbDReasoningHumanReviewAuthorityBinding = admit_reasoning_human_review_authority_record(authority_record)
        except Exception as exc:
            raise ProductError("ERR_DBD_REVIEW_AUTHORITY_RESOLUTION", "Human review authority could not be resolved", ProductErrorCategory.AUTHORIZATION) from exc
        if authority.confirmation_ref != confirmation_ref:
            raise ValueError("resolved Human confirmation does not match requested reference")
        try:
            current = self._current_snapshot_resolver.resolve(candidate_id)
        except Exception as exc:
            raise ProductError("ERR_DBD_REVIEW_CURRENT_RESOLUTION", "Current reasoning review snapshot could not be resolved", ProductErrorCategory.DATA_INTEGRITY) from exc
        if not isinstance(current, CurrentHumanReviewSnapshot) or current.root_candidate_id != candidate_id:
            raise ValueError("current review resolver returned a crossing snapshot")
        try:
            evaluated_at = self._clock()
        except Exception as exc:
            raise ProductError("ERR_DBD_REVIEW_CLOCK", "Server review clock is unavailable", ProductErrorCategory.STATE) from exc
        token = _InternalAdmissionToken(
            _CAPABILITY_PROOF, id(self._store), authority.binding_sha256,
            current.root_candidate_id, current.context.to_dict()["context_sha256"], evaluated_at,
        )
        return self._store._append_resolved_human_review(
            token=token, authority=authority, current=current, expected_head=expected_head,
            evaluated_at=evaluated_at,
        )


__all__ = [
    "DbDReasoningHumanReviewApplication", "HumanReviewAppendResult",
    "HumanReviewAuthorityResolver", "HumanReviewHeadExpectation",
    "ReasoningReviewCurrentSnapshotResolver",
]
