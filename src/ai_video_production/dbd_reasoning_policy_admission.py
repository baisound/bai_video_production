"""TASK-054 R2C deterministic policy admission for quarantined reasoning output."""
from __future__ import annotations

from dataclasses import dataclass, field
from math import log2
import re
import unicodedata

from .dbd_reasoning_admission import DbDReasoningFactAdmission, ReasoningFactAdmissionResult
from .dbd_reasoning_contracts import (
    DbDReasoningContextEnvelope, DbDReasoningProposal, InferenceQualifier,
    ReasoningDisposition, ReasoningFact, ReasoningInference, StyleMetrics,
)
from .dbd_reasoning_validation import StructuralReasoningProposal
from .game_commentary import CommentaryClaimKind, CommentaryPlan
from .ids import validate_id
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


POLICY_VERSION = "1.0.0"
_RECEIPT_VERSION = "1.0.0"
_STABLE_CODE_RE = re.compile(r"[A-Z][A-Z0-9_]{1,63}")
_PRODUCT_ID_RE = re.compile(r"[A-Z]+-[0-9A-HJKMNP-TV-Z]{26}")
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}", re.I)
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", re.I)
_URL_RE = re.compile(r"(?i)(?:\b[a-z][a-z0-9+.-]{1,20}://|\bmailto:|\b(?:www\.)?(?:[a-z0-9-]+\.)+[a-z]{2,63}(?:/[^\s]*)?)")
_URI_SCHEME_RE = re.compile(r"(?i)\b[a-z][a-z0-9+.-]{1,20}:(?!\s)")
_PATH_RE = re.compile(r"(?i)(?:^|[\s=:])(?:[a-z]:[\\/]|~[\\/]|\\\\|//|\\(?!\\)\S+|/(?!/)\S+)")
_SECRET_RE = re.compile(
    r"(?ix)(?:api[._ -]?key|access[._ -]?token|password|secret|private[._ -]?key|authorization)\s*(?::|=|\bis\b|\s)\s*\S+"
    r"|-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----|\b(?:bearer|basic)\s+[A-Za-z0-9+/=_:-]{8,}"
    r"|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|\bAIza[0-9A-Za-z_-]{30,}\b|\bxox[baprs]-[0-9A-Za-z-]{10,}\b"
    r"|\b(?:npm_|pypi-|github_pat_|glpat-|hf_|gh[pousr]_)[0-9A-Za-z_-]{10,}\b|\bsk(?:[._ /:-]+)[0-9A-Za-z_:/-]{8,}\b"
    r"|\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"
)
_EXECUTION_MARKERS = (
    "chain_of_thought", "reasoning_content", "reasoning_details", "analysis_content",
    "tool_call", "tool_calls", "tool_use", "tool_result", "tool_invocation", "function_call",
    "route_ref", "route_id", "provider_ref", "provider_id", "model_ref", "model_id",
    "credential_ref", "credential_id", "token_ref", "token_id",
)
_EXECUTION_TAG_RE = re.compile(r"(?is)<\s*/?\s*(?:analysis|reasoning|think|tool|function|route|provider|model|credential|token)(?:\s+[^>]*)?>")
_EXECUTION_NAMESPACE_RE = re.compile(r"(?:route|provider|model|credential|token)_(?:id|ref|value|version|selector|name|endpoint)(?:_|$)")
_EXECUTION_ASSIGNMENT_RE = re.compile(r"(?i)(?:^|[^0-9A-Za-z_])[\"']?(?:route|provider|model|credential|token)(?:[._ -]?(?:id|ref|value|version|selector|name|endpoint))?[\"']?\s*[:=]")
_ENTROPY_TOKEN_RE = re.compile(r"(?<![0-9A-Za-z_-])[0-9A-Za-z_-]{24,}(?![0-9A-Za-z_-])")
_HEX_TOKEN_RE = re.compile(r"(?i)(?<![0-9a-f])[0-9a-f]{32,256}(?![0-9a-f])")
_RAG_REFERENCE_SCHEMES = frozenset({"knowledge", "rag", "trivia", "manual", "https"})


@dataclass(frozen=True, slots=True)
class ContextReferenceIndex:
    context_sha256: str
    references: tuple[str, ...]
    snapshot_sha256: str = ""

    def __post_init__(self) -> None:
        validate_sha256(self.context_sha256, field_name="context_sha256")
        if self.references != tuple(sorted(set(self.references))):
            raise ValueError("references must be unique and canonically sorted")
        if any(not isinstance(item, str) or not item or len(item) > 512 for item in self.references):
            raise ValueError("reference index contains an invalid reference")
        expected = sha256_bytes(canonical_json_bytes({
            "schema_version": POLICY_VERSION,
            "context_sha256": self.context_sha256,
            "references": list(self.references),
        }))
        if self.snapshot_sha256 and self.snapshot_sha256 != expected:
            raise ValueError("reference snapshot digest mismatch")
        object.__setattr__(self, "snapshot_sha256", expected)

    @classmethod
    def from_context(cls, context: DbDReasoningContextEnvelope) -> "ContextReferenceIndex":
        if not isinstance(context, DbDReasoningContextEnvelope):
            raise TypeError("context must be DbDReasoningContextEnvelope")
        context.require_dispatchable()
        canonical_refs = [f"evidence://game/{value}" for value in context.evidence_refs]
        canonical_refs.extend(f"knowledge://sha256/{value.removeprefix('sha256:')}" for value in context.knowledge_ref_sha256s)
        rag_refs = [chunk.source_ref for chunk in context.rag_chunks]
        canonical_identities = {_reference_identity(ref) for ref in canonical_refs}
        seen_identities = set(canonical_identities)
        for ref in rag_refs:
            scheme, remainder = ref.split("://", 1)
            authority, _, path = remainder.partition("/")
            identity = _reference_identity(ref)
            if identity in canonical_identities:
                raise ValueError("RAG source_ref collides with a canonical reference identity")
            if scheme != scheme.casefold() or scheme not in _RAG_REFERENCE_SCHEMES:
                raise ValueError("RAG source_ref uses a reserved, noncanonical or unsupported namespace")
            if scheme != "trivia" and authority != authority.casefold():
                raise ValueError("RAG source_ref authority must use canonical lowercase")
            if scheme == "knowledge" and authority.casefold() == "sha256":
                raise ValueError("RAG source_ref must not use the canonical knowledge digest namespace")
            if "%" in ref or any(segment in {".", ".."} for segment in path.split("/")):
                raise ValueError("RAG source_ref must not contain aliasing path syntax")
            if identity in seen_identities:
                raise ValueError("RAG source_ref collides with an existing reference identity")
            seen_identities.add(identity)
        refs = [*canonical_refs, *rag_refs]
        return cls(context.to_dict()["context_sha256"], tuple(sorted(set(refs))))


@dataclass(frozen=True, slots=True)
class ReasoningPolicyAdmissionReceipt:
    schema_version: str
    policy_version: str
    structural_body_sha256: str
    context_sha256: str
    commentary_plan_sha256: str
    fact_admission_receipt_sha256: str
    reference_snapshot_sha256: str
    proposal_sha256: str | None
    passed: bool
    error_codes: tuple[str, ...]
    receipt_sha256: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != _RECEIPT_VERSION or self.policy_version != POLICY_VERSION:
            raise ValueError("unsupported policy admission receipt version")
        if not isinstance(self.passed, bool):
            raise ValueError("passed must be bool")
        for name in ("structural_body_sha256", "context_sha256", "commentary_plan_sha256", "fact_admission_receipt_sha256", "reference_snapshot_sha256"):
            validate_sha256(getattr(self, name), field_name=name)
        if self.proposal_sha256 is not None:
            validate_sha256(self.proposal_sha256, field_name="proposal_sha256")
        if self.passed != (self.proposal_sha256 is not None):
            raise ValueError("passed must match proposal digest presence")
        if self.error_codes != tuple(sorted(set(self.error_codes))) or any(not _STABLE_CODE_RE.fullmatch(code) for code in self.error_codes):
            raise ValueError("error_codes must be stable, unique and sorted")
        if self.passed == bool(self.error_codes):
            raise ValueError("receipt pass state is not canonical")
        expected = sha256_bytes(canonical_json_bytes(self._body()))
        if self.receipt_sha256 and self.receipt_sha256 != expected:
            raise ValueError("receipt_sha256 mismatch")
        object.__setattr__(self, "receipt_sha256", expected)

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version, "policy_version": self.policy_version,
            "structural_body_sha256": self.structural_body_sha256, "context_sha256": self.context_sha256,
            "commentary_plan_sha256": self.commentary_plan_sha256,
            "fact_admission_receipt_sha256": self.fact_admission_receipt_sha256,
            "reference_snapshot_sha256": self.reference_snapshot_sha256, "proposal_sha256": self.proposal_sha256,
            "passed": self.passed, "error_codes": list(self.error_codes),
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "receipt_sha256": self.receipt_sha256}


@dataclass(frozen=True, slots=True)
class ReasoningPolicyAdmissionResult:
    receipt: ReasoningPolicyAdmissionReceipt
    proposal: DbDReasoningProposal | None = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.receipt, ReasoningPolicyAdmissionReceipt):
            raise ValueError("receipt must be ReasoningPolicyAdmissionReceipt")
        if self.proposal is not None and not isinstance(self.proposal, DbDReasoningProposal):
            raise ValueError("proposal must be DbDReasoningProposal or null")
        if self.receipt.passed != (self.proposal is not None):
            raise ValueError("proposal exists exactly when receipt passed")
        if self.proposal is not None and self.proposal.to_dict()["proposal_sha256"] != self.receipt.proposal_sha256:
            raise ValueError("proposal does not match receipt")


class DbDReasoningPolicyAdmission:
    """Admit policy-safe output and only then create the canonical R0 Proposal."""

    def admit(
        self, *, context: DbDReasoningContextEnvelope, plan: CommentaryPlan,
        structural: StructuralReasoningProposal, fact_result: ReasoningFactAdmissionResult,
    ) -> ReasoningPolicyAdmissionResult:
        if not isinstance(context, DbDReasoningContextEnvelope) or not isinstance(plan, CommentaryPlan):
            raise TypeError("policy admission requires canonical context and plan")
        if not isinstance(structural, StructuralReasoningProposal) or not isinstance(fact_result, ReasoningFactAdmissionResult):
            raise TypeError("policy admission requires structural and fact admission results")
        context.require_dispatchable()
        context_sha = context.to_dict()["context_sha256"]
        plan_sha = plan.to_dict()["commentary_plan_sha256"]
        index = ContextReferenceIndex.from_context(context)
        recomputed = DbDReasoningFactAdmission().admit(context, plan, structural)
        errors: list[str] = []
        if fact_result.receipt.to_dict() != recomputed.receipt.to_dict():
            errors.append("FACT_ADMISSION_RESULT_MISMATCH")
        if not recomputed.receipt.passed:
            errors.append("FACT_ADMISSION_FAILED")
        allowed = frozenset(index.references)
        all_supporting = tuple(ref for item in (*structural.inferred_states, *structural.tactical_interpretations) for ref in item.supporting_refs)
        if any(ref not in allowed for ref in (*structural.citations, *all_supporting)):
            errors.append("REFERENCE_NOT_IN_CONTEXT")
        if any(ref not in structural.citations for ref in all_supporting):
            errors.append("SUPPORTING_REFERENCE_NOT_CITED")
        for item in (*structural.inferred_states, *structural.tactical_interpretations):
            if item.qualifier == InferenceQualifier.LIKELY.value and (not item.supporting_refs or item.confidence_milli < 700):
                errors.append("LIKELY_REQUIRES_SUPPORTED_CONFIDENCE")
        if not set(structural.uncertainty_codes).issubset(context.uncertainties):
            errors.append("UNCERTAINTY_NOT_IN_CONTEXT")
        text_fields = [structural.commentary_text, *structural.commentary_outline]
        text_fields.extend(item.statement for item in (*structural.inferred_states, *structural.tactical_interpretations))
        # Fact key/value text is not scanned here: R2B has already proved each
        # triple is an exact copy from the canonical Context.  Treating dotted
        # canonical keys as arbitrary free text would both duplicate R2B and
        # create false positives in the generic domain rule below.
        if any(_unsafe_free_text(value) for value in text_fields):
            errors.append("DLP_POLICY_REJECTED")
        if any(_contains_code(value, code) for code in context.forbidden_claims for value in text_fields):
            errors.append("FORBIDDEN_CLAIM")
        if _estimated_speech_ms(structural.commentary_text) > context.speech_budget_ms:
            errors.append("SPEECH_BUDGET_EXCEEDED")
        metrics = structural.style_metrics
        if any(value > 900 for value in (metrics.density_milli, metrics.emotion_milli, metrics.tempo_milli)):
            errors.append("STYLE_POLICY_EXCEEDED")

        proposal = None
        if not errors:
            proposal = DbDReasoningProposal(
                disposition=ReasoningDisposition(structural.disposition),
                observed_claims=tuple(ReasoningFact(CommentaryClaimKind(item.kind), item.key, item.value) for item in structural.observed_claims),
                canonical_claims=tuple(ReasoningFact(CommentaryClaimKind(item.kind), item.key, item.value) for item in structural.canonical_claims),
                inferred_states=tuple(_inference(item) for item in structural.inferred_states),
                tactical_interpretations=tuple(_inference(item) for item in structural.tactical_interpretations),
                commentary_outline=structural.commentary_outline, commentary_text=structural.commentary_text,
                citations=structural.citations, uncertainty_codes=structural.uncertainty_codes,
                style_metrics=StyleMetrics(metrics.density_milli, metrics.emotion_milli, metrics.tempo_milli),
            )
        error_codes = tuple(sorted(set(errors)))
        receipt = ReasoningPolicyAdmissionReceipt(
            _RECEIPT_VERSION, POLICY_VERSION, structural.structural_body_sha256, context_sha, plan_sha,
            recomputed.receipt.receipt_sha256, index.snapshot_sha256,
            proposal.to_dict()["proposal_sha256"] if proposal else None, not error_codes, error_codes,
        )
        return ReasoningPolicyAdmissionResult(receipt, proposal)


def _inference(item: object) -> ReasoningInference:
    return ReasoningInference(item.statement, InferenceQualifier(item.qualifier), item.confidence_milli, item.supporting_refs)  # type: ignore[attr-defined]


def _reference_identity(value: str) -> str:
    scheme, remainder = value.split("://", 1)
    authority, separator, path = remainder.partition("/")
    return f"{scheme.casefold()}://{authority.casefold()}{separator}{path}"


def _contains_code(value: str, code: str) -> bool:
    normalized_value = re.sub(r"[\s._/\\:-]+", "_", unicodedata.normalize("NFKC", value).casefold()).strip("_")
    normalized_code = re.sub(r"[\s._/\\:-]+", "_", unicodedata.normalize("NFKC", code).casefold()).strip("_")
    return normalized_code in normalized_value


def _estimated_speech_ms(value: str) -> int:
    return sum(not char.isspace() for char in value) * 80


def _unsafe_free_text(value: str) -> bool:
    normalized = unicodedata.normalize("NFKC", value)
    if any(unicodedata.category(char).startswith("C") for char in normalized):
        return True
    # Structured secret wrappers must be recognized before safe SHA/ID masking.
    if _SECRET_RE.search(normalized):
        return True
    masked = _SHA_RE.sub(" SHA256 ", normalized)
    masked = _UUID_RE.sub(" UUID ", masked)
    for match in tuple(_PRODUCT_ID_RE.finditer(masked)):
        try:
            validate_id(match.group())
        except ValueError:
            continue
        masked = masked.replace(match.group(), " PRODUCT_ID ")
    folded = masked.casefold()
    comparison = re.sub(r"[\s._/\\:=-]+", "_", folded).strip("_")
    return bool(
        _URL_RE.search(masked) or _URI_SCHEME_RE.search(masked) or _PATH_RE.search(masked) or _HEX_TOKEN_RE.search(masked)
        or _EXECUTION_TAG_RE.search(masked) or _EXECUTION_ASSIGNMENT_RE.search(masked)
        or _EXECUTION_NAMESPACE_RE.search(comparison)
        or any(marker in comparison for marker in _EXECUTION_MARKERS) or _has_high_entropy_token(masked)
    )


def contains_unsafe_reasoning_free_text(value: str) -> bool:
    """Return the canonical R2C DLP decision without creating policy authority."""
    if not isinstance(value, str):
        raise ValueError("free text must be a string")
    return _unsafe_free_text(value)


def _has_high_entropy_token(value: str) -> bool:
    for match in _ENTROPY_TOKEN_RE.finditer(value):
        token = match.group()
        frequencies = {character: token.count(character) for character in set(token)}
        entropy = -sum((count / len(token)) * log2(count / len(token)) for count in frequencies.values())
        # Long compact ASCII is never required for commentary.  Shorter
        # compact runs are rejected when their Shannon entropy resembles a
        # credential rather than ordinary prose.  Canonical ID/SHA/UUID values
        # were masked before this function.
        if len(token) >= 32 or entropy >= 3.5:
            return True
    return False


__all__ = [
    "ContextReferenceIndex", "DbDReasoningPolicyAdmission", "POLICY_VERSION",
    "ReasoningPolicyAdmissionReceipt", "ReasoningPolicyAdmissionResult",
    "contains_unsafe_reasoning_free_text",
]
