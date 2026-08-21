"""TASK-054 R2D-A pure composition and candidate-lineage contracts.

This module never performs I/O.  It is the only admitted composition path from
raw tuned-model bytes to the existing CommentaryCandidate owner.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from .dbd_reasoning_admission import DbDReasoningFactAdmission, ReasoningFactAdmissionReceipt
from .dbd_reasoning_contracts import DbDReasoningContextEnvelope, DbDReasoningProposal
from .dbd_reasoning_policy_admission import DbDReasoningPolicyAdmission, ReasoningPolicyAdmissionReceipt
from .dbd_reasoning_validation import DbDReasoningProposalParser, PARSER_VERSION
from .game_commentary import CommentaryCandidate, CommentaryPlan
from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


LINEAGE_SCHEMA_VERSION = "1.0.0"
_STABLE_CODE_RE = re.compile(r"[A-Z][A-Z0-9_]{1,63}")


@dataclass(frozen=True, slots=True)
class DbDReasoningCandidateLineage:
    schema_version: str
    origin: str
    candidate_id: str
    commentary_candidate_sha256: str
    match_id: str
    event_id: str
    event_revision: int
    parser_version: str
    raw_output_sha256: str
    structural_body_sha256: str
    context_sha256: str
    commentary_plan_sha256: str
    fact_admission_receipt: ReasoningFactAdmissionReceipt = field(repr=False)
    policy_admission_receipt: ReasoningPolicyAdmissionReceipt = field(repr=False)
    proposal: DbDReasoningProposal = field(repr=False)
    parent_candidate_id: str | None = None
    parent_candidate_sha256: str | None = None
    correction_request_review_sha256: str | None = None
    lineage_sha256: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != LINEAGE_SCHEMA_VERSION or self.origin != "TUNED_REASONING":
            raise ValueError("unsupported root lineage contract")
        validate_id(self.candidate_id, IdKind.CANDIDATE)
        validate_id(self.match_id, IdKind.GAME_MATCH)
        validate_id(self.event_id, IdKind.GAME_EVENT)
        if isinstance(self.event_revision, bool) or not isinstance(self.event_revision, int) or self.event_revision < 1:
            raise ValueError("event_revision must be positive")
        if self.parser_version != PARSER_VERSION:
            raise ValueError("parser_version mismatch")
        for name in ("commentary_candidate_sha256", "raw_output_sha256", "structural_body_sha256", "context_sha256", "commentary_plan_sha256"):
            validate_sha256(getattr(self, name), field_name=name)
        if not isinstance(self.fact_admission_receipt, ReasoningFactAdmissionReceipt) or not self.fact_admission_receipt.passed:
            raise ValueError("lineage requires a passed R2B receipt")
        if not isinstance(self.policy_admission_receipt, ReasoningPolicyAdmissionReceipt) or not self.policy_admission_receipt.passed:
            raise ValueError("lineage requires a passed R2C receipt")
        if not isinstance(self.proposal, DbDReasoningProposal):
            raise ValueError("lineage requires a canonical reasoning proposal")
        if any(value is not None for value in (self.parent_candidate_id, self.parent_candidate_sha256, self.correction_request_review_sha256)):
            raise ValueError("TUNED_REASONING root lineage cannot have a parent or correction review")
        fact = self.fact_admission_receipt
        policy = self.policy_admission_receipt
        if (fact.structural_body_sha256, fact.context_sha256, fact.commentary_plan_sha256) != (
            self.structural_body_sha256, self.context_sha256, self.commentary_plan_sha256,
        ):
            raise ValueError("R2B receipt coordinates do not match lineage")
        if (
            policy.structural_body_sha256 != self.structural_body_sha256
            or policy.context_sha256 != self.context_sha256
            or policy.commentary_plan_sha256 != self.commentary_plan_sha256
            or policy.fact_admission_receipt_sha256 != fact.receipt_sha256
            or policy.proposal_sha256 != self.proposal.to_dict()["proposal_sha256"]
        ):
            raise ValueError("R2C receipt coordinates do not match lineage")
        expected = sha256_bytes(canonical_json_bytes(self._body()))
        if self.lineage_sha256 and self.lineage_sha256 != expected:
            raise ValueError("lineage_sha256 mismatch")
        object.__setattr__(self, "lineage_sha256", expected)

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version, "record_kind": "DBD_REASONING_CANDIDATE_LINEAGE",
            "origin": self.origin, "candidate_id": self.candidate_id,
            "commentary_candidate_sha256": self.commentary_candidate_sha256,
            "match_id": self.match_id, "event_id": self.event_id, "event_revision": self.event_revision,
            "parser_version": self.parser_version, "raw_output_sha256": self.raw_output_sha256,
            "structural_body_sha256": self.structural_body_sha256, "context_sha256": self.context_sha256,
            "commentary_plan_sha256": self.commentary_plan_sha256,
            "fact_admission_receipt": self.fact_admission_receipt.to_dict(),
            "policy_admission_receipt": self.policy_admission_receipt.to_dict(),
            "proposal": self.proposal.to_dict(), "parent_candidate_id": self.parent_candidate_id,
            "parent_candidate_sha256": self.parent_candidate_sha256,
            "correction_request_review_sha256": self.correction_request_review_sha256,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "lineage_sha256": self.lineage_sha256}


@dataclass(frozen=True, slots=True)
class DbDReasoningCandidateCreationResult:
    passed: bool
    error_codes: tuple[str, ...]
    raw_output_sha256: str
    candidate: CommentaryCandidate | None = field(repr=False)
    lineage: DbDReasoningCandidateLineage | None = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.passed, bool):
            raise ValueError("passed must be bool")
        validate_sha256(self.raw_output_sha256, field_name="raw_output_sha256")
        if self.error_codes != tuple(sorted(set(self.error_codes))) or any(not _STABLE_CODE_RE.fullmatch(code) for code in self.error_codes):
            raise ValueError("error_codes must be stable, unique and sorted")
        if self.passed == bool(self.error_codes):
            raise ValueError("result pass state is not canonical")
        if self.passed != (self.candidate is not None and self.lineage is not None):
            raise ValueError("candidate and lineage exist exactly when composition passed")
        if self.candidate is not None:
            if not isinstance(self.candidate, CommentaryCandidate) or not isinstance(self.lineage, DbDReasoningCandidateLineage):
                raise ValueError("result contains invalid candidate or lineage")
            candidate_payload = self.candidate.to_dict()
            if (
                self.lineage.candidate_id != self.candidate.candidate_id
                or self.lineage.commentary_candidate_sha256 != candidate_payload["commentary_candidate_sha256"]
                or self.lineage.raw_output_sha256 != self.raw_output_sha256
                or not self.candidate.validation.passed
                or self.candidate.draft.provider_ref is not None
                or self.candidate.plan.to_dict()["commentary_plan_sha256"] != self.lineage.commentary_plan_sha256
                or self.candidate.draft.to_dict()["commentary_draft_sha256"] != self.lineage.fact_admission_receipt.commentary_draft_sha256
                or (self.candidate.plan.match_id, self.candidate.plan.event_id, self.candidate.plan.event_revision)
                != (self.lineage.match_id, self.lineage.event_id, self.lineage.event_revision)
            ):
                raise ValueError("candidate/result/lineage mismatch")
            proposal = self.lineage.proposal
            expected_claims = tuple(sorted(
                (item.to_commentary_claim() for item in (*proposal.observed_claims, *proposal.canonical_claims)),
                key=lambda item: (item.kind.value, item.key, item.value),
            ))
            if self.candidate.draft.text != proposal.commentary_text or self.candidate.draft.claims != expected_claims:
                raise ValueError("candidate draft does not exactly match admitted proposal")


class DbDReasoningCandidateComposer:
    """Compose R2A -> R2B -> R2C internally; no receipt is an authority input."""

    def create(self, *, raw_output: bytes, context: DbDReasoningContextEnvelope, plan: CommentaryPlan) -> DbDReasoningCandidateCreationResult:
        if not isinstance(raw_output, bytes):
            raise TypeError("raw_output must be bytes")
        if not isinstance(context, DbDReasoningContextEnvelope) or not isinstance(plan, CommentaryPlan):
            raise TypeError("composer requires canonical context and plan")
        parsed = DbDReasoningProposalParser().parse(raw_output)
        if not parsed.structurally_valid:
            return DbDReasoningCandidateCreationResult(False, parsed.error_codes, parsed.raw_output_sha256, None, None)
        structural = parsed.quarantined_proposal
        assert structural is not None
        fact = DbDReasoningFactAdmission().admit(context, plan, structural)
        if not fact.receipt.passed:
            return DbDReasoningCandidateCreationResult(False, fact.receipt.error_codes, parsed.raw_output_sha256, None, None)
        policy = DbDReasoningPolicyAdmission().admit(context=context, plan=plan, structural=structural, fact_result=fact)
        if not policy.receipt.passed:
            return DbDReasoningCandidateCreationResult(False, policy.receipt.error_codes, parsed.raw_output_sha256, None, None)
        if fact.draft is None or fact.existing_validation is None or policy.proposal is None:
            raise ValueError("passed admission composition is incomplete")
        if fact.draft.provider_ref is not None:
            raise ValueError("reasoning candidate draft must remain provider-neutral")
        candidate = CommentaryCandidate(plan, fact.draft, fact.existing_validation)
        candidate_payload = candidate.to_dict()
        lineage = DbDReasoningCandidateLineage(
            LINEAGE_SCHEMA_VERSION, "TUNED_REASONING", candidate.candidate_id,
            candidate_payload["commentary_candidate_sha256"], plan.match_id, plan.event_id, plan.event_revision,
            parsed.parser_version, parsed.raw_output_sha256, structural.structural_body_sha256,
            context.to_dict()["context_sha256"], plan.to_dict()["commentary_plan_sha256"],
            fact.receipt, policy.receipt, policy.proposal,
        )
        return DbDReasoningCandidateCreationResult(True, (), parsed.raw_output_sha256, candidate, lineage)


__all__ = [
    "DbDReasoningCandidateComposer", "DbDReasoningCandidateCreationResult",
    "DbDReasoningCandidateLineage", "LINEAGE_SCHEMA_VERSION",
]
