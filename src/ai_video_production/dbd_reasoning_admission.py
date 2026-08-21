"""TASK-054 R2B deterministic, side-effect-free reasoning admission."""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from .dbd_reasoning_contracts import DbDReasoningContextEnvelope, ReasoningDisposition
from .dbd_reasoning_validation import StructuralReasoningProposal
from .game_commentary import CommentaryClaim, CommentaryClaimKind, CommentaryDraft, CommentaryFactValidator, CommentaryPlan, FactValidationResult
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


@dataclass(frozen=True, slots=True)
class ReasoningFactAdmissionReceipt:
    schema_version: str
    structural_body_sha256: str
    context_sha256: str
    commentary_plan_sha256: str
    commentary_draft_sha256: str | None
    passed: bool
    error_codes: tuple[str, ...]
    receipt_sha256: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != "1.0.0":
            raise ValueError("unsupported fact admission receipt schema")
        if not isinstance(self.passed, bool):
            raise ValueError("passed must be bool")
        for name in ("structural_body_sha256", "context_sha256", "commentary_plan_sha256"):
            validate_sha256(getattr(self, name), field_name=name)
        if self.commentary_draft_sha256 is not None:
            validate_sha256(self.commentary_draft_sha256, field_name="commentary_draft_sha256")
        if self.passed != (self.commentary_draft_sha256 is not None):
            raise ValueError("passed must match commentary_draft_sha256 presence")
        if any(not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", code) for code in self.error_codes):
            raise ValueError("receipt error_codes must be stable identifiers")
        if self.error_codes != tuple(sorted(set(self.error_codes))) or self.passed == bool(self.error_codes):
            raise ValueError("receipt pass state is not canonical")
        body = self._body()
        expected = sha256_bytes(canonical_json_bytes(body))
        if self.receipt_sha256 and self.receipt_sha256 != expected:
            raise ValueError("receipt_sha256 mismatch")
        object.__setattr__(self, "receipt_sha256", expected)

    def _body(self) -> dict[str, object]:
        return {"schema_version": self.schema_version, "structural_body_sha256": self.structural_body_sha256, "context_sha256": self.context_sha256, "commentary_plan_sha256": self.commentary_plan_sha256, "commentary_draft_sha256": self.commentary_draft_sha256, "passed": self.passed, "error_codes": list(self.error_codes)}

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "receipt_sha256": self.receipt_sha256}


@dataclass(frozen=True, slots=True)
class ReasoningFactAdmissionResult:
    receipt: ReasoningFactAdmissionReceipt
    draft: CommentaryDraft | None = field(repr=False)
    existing_validation: FactValidationResult | None = field(repr=False, default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.receipt, ReasoningFactAdmissionReceipt):
            raise ValueError("receipt must be ReasoningFactAdmissionReceipt")
        if self.receipt.passed != (self.draft is not None):
            raise ValueError("draft exists exactly when receipt passed")
        if self.draft is not None:
            if not isinstance(self.draft, CommentaryDraft) or self.receipt.commentary_draft_sha256 != self.draft.to_dict()["commentary_draft_sha256"]:
                raise ValueError("draft does not match receipt")
            if self.draft.provider_ref is not None:
                raise ValueError("R2B draft provider_ref must remain null")
        if self.existing_validation is not None and not isinstance(self.existing_validation, FactValidationResult):
            raise ValueError("existing_validation must be FactValidationResult or null")
        if self.receipt.passed and (self.existing_validation is None or not self.existing_validation.passed):
            raise ValueError("passed result requires passed existing validation")


class DbDReasoningFactAdmission:
    def admit(self, context: DbDReasoningContextEnvelope, plan: CommentaryPlan, proposal: StructuralReasoningProposal) -> ReasoningFactAdmissionResult:
        if not isinstance(context, DbDReasoningContextEnvelope) or not isinstance(plan, CommentaryPlan) or not isinstance(proposal, StructuralReasoningProposal):
            raise TypeError("fact admission requires canonical context/plan and structural proposal")
        errors: list[str] = []
        try:
            context.require_dispatchable()
        except ValueError:
            errors.append("CONTEXT_NOT_DISPATCHABLE")
        if (context.match_id, context.event_id, context.event_revision, context.language) != (plan.match_id, plan.event_id, plan.event_revision, plan.language):
            errors.append("PLAN_CONTEXT_COORDINATE_MISMATCH")
        if context.evidence_refs != plan.evidence_refs or context.knowledge_ref_sha256s != plan.knowledge_ref_sha256s:
            errors.append("PLAN_CONTEXT_DEPENDENCY_MISMATCH")
        context_sha = context.to_dict()["context_sha256"]
        plan_sha = plan.to_dict()["commentary_plan_sha256"]
        if proposal.disposition != ReasoningDisposition.PROPOSE.value:
            errors.append("STRUCTURAL_DISPOSITION_NOT_PROPOSE")
        observed = {(fact.kind.value, fact.key, fact.value) for fact in context.observed_facts}
        canonical = {(fact.kind.value, fact.key, fact.value) for fact in context.canonical_facts}
        claims = []
        for fact in proposal.observed_claims:
            key = (fact.kind, fact.key, fact.value)
            if key not in observed or key in canonical:
                errors.append("OBSERVED_FACT_NOT_EXACT")
            claims.append(CommentaryClaim(CommentaryClaimKind(fact.kind), fact.key, fact.value))
        for fact in proposal.canonical_claims:
            key = (fact.kind, fact.key, fact.value)
            if key not in canonical or key in observed:
                errors.append("CANONICAL_FACT_NOT_EXACT")
            claims.append(CommentaryClaim(CommentaryClaimKind(fact.kind), fact.key, fact.value))
        if len(set(claims)) != len(claims):
            errors.append("DUPLICATE_OR_CROSSED_FACT")
        draft = None
        validation = None
        if not errors:
            draft = CommentaryDraft(proposal.commentary_text, tuple(sorted(claims, key=lambda item: (item.kind.value, item.key, item.value))), None)
            validation = CommentaryFactValidator().validate(plan, draft)
            errors.extend(validation.errors)
        passed = not errors
        draft_sha = draft.to_dict()["commentary_draft_sha256"] if passed and draft else None
        receipt_errors = tuple(sorted({_receipt_error_code(error) for error in errors}))
        receipt = ReasoningFactAdmissionReceipt("1.0.0", proposal.structural_body_sha256, context_sha, plan_sha, draft_sha, passed, receipt_errors)
        return ReasoningFactAdmissionResult(receipt, draft if passed else None, validation)


def _receipt_error_code(error: str) -> str:
    code = error.split(":", 1)[0]
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", code):
        raise ValueError("existing validator returned an unstable error code")
    return code
