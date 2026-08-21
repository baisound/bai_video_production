"""TASK-054 R2D-A pure composition and candidate-lineage contracts.

This module never performs I/O.  It is the only admitted composition path from
raw tuned-model bytes to the existing CommentaryCandidate owner.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
import secrets
from typing import Any, Mapping

from .dbd_reasoning_admission import DbDReasoningFactAdmission, ReasoningFactAdmissionReceipt
from .dbd_reasoning_contracts import (
    DbDReasoningContextEnvelope, DbDReasoningProposal, InferenceQualifier,
    ReasoningDisposition, ReasoningFact, ReasoningInference, StyleMetrics,
)
from .dbd_reasoning_policy_admission import DbDReasoningPolicyAdmission, ReasoningPolicyAdmissionReceipt
from .dbd_reasoning_validation import DbDReasoningProposalParser, PARSER_VERSION
from .game_commentary import (
    CommentaryCandidate, CommentaryClaim, CommentaryClaimKind, CommentaryDisposition,
    CommentaryDraft, CommentaryFact, CommentaryPlan,
)
from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


LINEAGE_SCHEMA_VERSION = "1.0.0"
_STABLE_CODE_RE = re.compile(r"[A-Z][A-Z0-9_]{1,63}")
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


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
        if not self.candidate_id.startswith("CAND-R2D"):
            raise ValueError("reasoning lineage requires the reserved R2D Candidate identity")
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
                or not self.candidate.reasoning_lineage_required
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
        candidate = CommentaryCandidate(
            plan, fact.draft, fact.existing_validation,
            candidate_id=_generate_reasoning_candidate_id(), reasoning_lineage_required=True,
        )
        candidate_payload = candidate.to_dict()
        lineage = DbDReasoningCandidateLineage(
            LINEAGE_SCHEMA_VERSION, "TUNED_REASONING", candidate.candidate_id,
            candidate_payload["commentary_candidate_sha256"], plan.match_id, plan.event_id, plan.event_revision,
            parsed.parser_version, parsed.raw_output_sha256, structural.structural_body_sha256,
            context.to_dict()["context_sha256"], plan.to_dict()["commentary_plan_sha256"],
            fact.receipt, policy.receipt, policy.proposal,
        )
        return DbDReasoningCandidateCreationResult(True, (), parsed.raw_output_sha256, candidate, lineage)


_LINEAGE_KEYS = frozenset({
    "schema_version", "record_kind", "origin", "candidate_id", "commentary_candidate_sha256",
    "match_id", "event_id", "event_revision", "parser_version", "raw_output_sha256",
    "structural_body_sha256", "context_sha256", "commentary_plan_sha256",
    "fact_admission_receipt", "policy_admission_receipt", "proposal", "parent_candidate_id",
    "parent_candidate_sha256", "correction_request_review_sha256", "lineage_sha256",
})


def admit_reasoning_candidate_lineage_record(
    record: Mapping[str, Any], *, candidate_payload: Mapping[str, Any],
) -> DbDReasoningCandidateLineage:
    """Re-admit serialized lineage and its existing Candidate fail-closed."""

    if not isinstance(record, Mapping) or set(record) != _LINEAGE_KEYS:
        raise ValueError("lineage record has unknown or missing fields")
    if record.get("record_kind") != "DBD_REASONING_CANDIDATE_LINEAGE":
        raise ValueError("lineage record_kind is invalid")
    fact_data = _exact_mapping(record["fact_admission_receipt"], {
        "schema_version", "structural_body_sha256", "context_sha256", "commentary_plan_sha256",
        "commentary_draft_sha256", "passed", "error_codes", "receipt_sha256",
    }, "fact receipt")
    policy_data = _exact_mapping(record["policy_admission_receipt"], {
        "schema_version", "policy_version", "structural_body_sha256", "context_sha256",
        "commentary_plan_sha256", "fact_admission_receipt_sha256", "reference_snapshot_sha256",
        "proposal_sha256", "passed", "error_codes", "receipt_sha256",
    }, "policy receipt")
    fact = ReasoningFactAdmissionReceipt(
        fact_data["schema_version"], fact_data["structural_body_sha256"], fact_data["context_sha256"],
        fact_data["commentary_plan_sha256"], fact_data["commentary_draft_sha256"], fact_data["passed"],
        _string_tuple(fact_data["error_codes"], "fact error_codes"), fact_data["receipt_sha256"],
    )
    policy = ReasoningPolicyAdmissionReceipt(
        policy_data["schema_version"], policy_data["policy_version"], policy_data["structural_body_sha256"],
        policy_data["context_sha256"], policy_data["commentary_plan_sha256"],
        policy_data["fact_admission_receipt_sha256"], policy_data["reference_snapshot_sha256"],
        policy_data["proposal_sha256"], policy_data["passed"],
        _string_tuple(policy_data["error_codes"], "policy error_codes"), policy_data["receipt_sha256"],
    )
    proposal = _proposal_from_record(record["proposal"])
    lineage = DbDReasoningCandidateLineage(
        record["schema_version"], record["origin"], record["candidate_id"], record["commentary_candidate_sha256"],
        record["match_id"], record["event_id"], record["event_revision"], record["parser_version"],
        record["raw_output_sha256"], record["structural_body_sha256"], record["context_sha256"],
        record["commentary_plan_sha256"], fact, policy, proposal, record["parent_candidate_id"],
        record["parent_candidate_sha256"], record["correction_request_review_sha256"], record["lineage_sha256"],
    )
    _verify_candidate_payload_against_lineage(candidate_payload, lineage)
    return lineage


def _verify_candidate_payload_against_lineage(candidate: Mapping[str, Any], lineage: DbDReasoningCandidateLineage) -> None:
    required = {"schema_version", "candidate_id", "match_id", "event_id", "event_revision", "status", "plan", "draft", "validation", "created_at", "reasoning_origin", "commentary_candidate_sha256"}
    if not isinstance(candidate, Mapping) or set(candidate) != required:
        raise ValueError("candidate payload has unknown or missing fields")
    body = {key: value for key, value in candidate.items() if key != "commentary_candidate_sha256"}
    if candidate["commentary_candidate_sha256"] != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError("candidate payload digest mismatch")
    plan = _exact_mapping(candidate["plan"], {"schema_version", "match_id", "event_id", "event_revision", "language", "disposition", "priority_milli", "reason_codes", "facts", "evidence_refs", "knowledge_ref_sha256s", "commentary_plan_sha256"}, "candidate plan")
    draft = _exact_mapping(candidate["draft"], {"schema_version", "text", "claims", "provider_ref", "commentary_draft_sha256"}, "candidate draft")
    validation = _exact_mapping(candidate["validation"], {"passed", "errors"}, "candidate validation")
    for nested, checksum in ((plan, "commentary_plan_sha256"), (draft, "commentary_draft_sha256")):
        nested_body = {key: value for key, value in nested.items() if key != checksum}
        if nested[checksum] != sha256_bytes(canonical_json_bytes(nested_body)):
            raise ValueError(f"{checksum} mismatch")
    admitted_plan = CommentaryPlan(
        plan["match_id"], plan["event_id"], plan["event_revision"], plan["language"],
        CommentaryDisposition(plan["disposition"]), plan["priority_milli"],
        _string_tuple(plan["reason_codes"], "plan reason_codes"),
        tuple(CommentaryFact(CommentaryClaimKind(item["kind"]), item["key"], item["value"]) for item in _object_rows(plan["facts"], {"kind", "key", "value"}, "plan facts")),
        _string_tuple(plan["evidence_refs"], "plan evidence_refs"),
        _string_tuple(plan["knowledge_ref_sha256s"], "plan knowledge refs"),
    )
    if admitted_plan.to_dict() != dict(plan):
        raise ValueError("candidate plan is not canonical")
    admitted_draft = CommentaryDraft(
        draft["text"],
        tuple(CommentaryClaim(CommentaryClaimKind(item["kind"]), item["key"], item["value"]) for item in _object_rows(draft["claims"], {"kind", "key", "value"}, "draft claims")),
        draft["provider_ref"],
    )
    if admitted_draft.to_dict() != dict(draft):
        raise ValueError("candidate draft is not canonical")
    created_at = candidate["created_at"]
    if not isinstance(created_at, str) or not created_at.strip() or len(created_at) > 64 or any(ord(char) < 32 for char in created_at):
        raise ValueError("candidate created_at is not canonical stable text")
    if (
        candidate["schema_version"] != "1.1.0" or candidate["status"] != "VALIDATED" or candidate["reasoning_origin"] != "TUNED_REASONING"
        or not candidate["candidate_id"].startswith("CAND-R2D")
        or validation != {"passed": True, "errors": []} or draft["provider_ref"] is not None
        or candidate["candidate_id"] != lineage.candidate_id
        or candidate["commentary_candidate_sha256"] != lineage.commentary_candidate_sha256
        or (candidate["match_id"], candidate["event_id"], candidate["event_revision"])
        != (lineage.match_id, lineage.event_id, lineage.event_revision)
        or (plan["match_id"], plan["event_id"], plan["event_revision"])
        != (candidate["match_id"], candidate["event_id"], candidate["event_revision"])
        or plan["commentary_plan_sha256"] != lineage.commentary_plan_sha256
        or draft["commentary_draft_sha256"] != lineage.fact_admission_receipt.commentary_draft_sha256
        or draft["text"] != lineage.proposal.commentary_text
    ):
        raise ValueError("candidate payload does not match lineage")
    expected_claims = [item.to_dict() for item in sorted(
        (item.to_commentary_claim() for item in (*lineage.proposal.observed_claims, *lineage.proposal.canonical_claims)),
        key=lambda item: (item.kind.value, item.key, item.value),
    )]
    if draft["claims"] != expected_claims:
        raise ValueError("candidate claims do not match lineage proposal")


def _proposal_from_record(value: Any) -> DbDReasoningProposal:
    data = _exact_mapping(value, {"schema_version", "disposition", "observed_claims", "canonical_claims", "inferred_states", "tactical_interpretations", "commentary_outline", "commentary_text", "citations", "uncertainty_codes", "style_metrics", "proposal_sha256"}, "proposal")
    facts = lambda rows, name: tuple(ReasoningFact(CommentaryClaimKind(item["kind"]), item["key"], item["value"]) for item in _object_rows(rows, {"kind", "key", "value"}, name))
    inferences = lambda rows, name: tuple(ReasoningInference(item["statement"], InferenceQualifier(item["qualifier"]), item["confidence_milli"], _string_tuple(item["supporting_refs"], f"{name} refs")) for item in _object_rows(rows, {"statement", "qualifier", "confidence_milli", "supporting_refs"}, name))
    metrics = _exact_mapping(data["style_metrics"], {"density_milli", "emotion_milli", "tempo_milli"}, "style metrics")
    proposal = DbDReasoningProposal(
        ReasoningDisposition(data["disposition"]), facts(data["observed_claims"], "observed claims"),
        facts(data["canonical_claims"], "canonical claims"), inferences(data["inferred_states"], "inferred states"),
        inferences(data["tactical_interpretations"], "tactical interpretations"),
        _string_tuple(data["commentary_outline"], "commentary outline"), data["commentary_text"],
        _string_tuple(data["citations"], "citations"), _string_tuple(data["uncertainty_codes"], "uncertainty codes"),
        StyleMetrics(metrics["density_milli"], metrics["emotion_milli"], metrics["tempo_milli"]),
    )
    if proposal.to_dict()["proposal_sha256"] != data["proposal_sha256"]:
        raise ValueError("proposal_sha256 mismatch")
    return proposal


def _generate_reasoning_candidate_id() -> str:
    value = "CAND-R2D" + "".join(secrets.choice(_CROCKFORD) for _ in range(23))
    validate_id(value, IdKind.CANDIDATE)
    return value


def _exact_mapping(value: Any, keys: set[str], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"{name} has unknown or missing fields")
    return value


def _string_tuple(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be a string array")
    return tuple(value)


def _object_rows(value: Any, keys: set[str], name: str) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be an array")
    return tuple(_exact_mapping(item, keys, name) for item in value)


__all__ = [
    "DbDReasoningCandidateComposer", "DbDReasoningCandidateCreationResult",
    "DbDReasoningCandidateLineage", "LINEAGE_SCHEMA_VERSION",
    "admit_reasoning_candidate_lineage_record",
]
