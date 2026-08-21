"""TASK-054 R0 pure contracts for the DbD tuned reasoning layer.

These records carry metadata only.  They do not load a model, call a provider,
adopt a Dataset example, or grant training/Production authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
import re
from typing import Any, Mapping

from .game_commentary import CommentaryClaim, CommentaryClaimKind, CommentaryFact
from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_VERSION = "1.0.0"
_LOCALE_RE = re.compile(r"[a-z]{2,3}(?:-[A-Z]{2})?")
_STABLE_CODE_RE = re.compile(r"[A-Z][A-Z0-9_]{1,63}")
_SAFE_REF_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s\\@?#]+")
_FORBIDDEN_REF_SCHEMES = ("credential://", "secret://", "env://", "file://")
_MAX_RAG_CHUNK_TEXT = 1000
_MAX_RAG_TEXT_TOTAL = 16000
MAX_CONTEXT_CANONICAL_BYTES = 128 * 1024
_SECRET_LIKE_RE = re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*[^\s]+")
_UTC_RFC3339_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z")


class TunedModelBindingStatus(str, Enum):
    DRAFT = "DRAFT"
    EVALUATED = "EVALUATED"
    APPROVED = "APPROVED"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    REJECTED = "REJECTED"


class ReasoningSessionMode(str, Enum):
    PREVIEW_NO_LEARNING = "PREVIEW_NO_LEARNING"
    LEARNING = "LEARNING"

    @property
    def training_eligible(self) -> bool:
        return self is ReasoningSessionMode.LEARNING


class ReasoningDisposition(str, Enum):
    PROPOSE = "PROPOSE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    ABSTAIN = "ABSTAIN"


class InferenceQualifier(str, Enum):
    POSSIBLE = "POSSIBLE"
    LIKELY = "LIKELY"


class ContextFreshness(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class HumanReviewResult(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AuthorizationDecision(str, Enum):
    ALLOWED = "ALLOWED"
    DENIED = "DENIED"
    NOT_REQUIRED = "NOT_REQUIRED"


def _text(value: str, *, name: str, maximum: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > maximum or (not allow_empty and not value.strip()):
        raise ValueError(f"{name} must be a string up to {maximum} characters")
    if any(ord(character) < 32 and character not in "\t\n\r" for character in value):
        raise ValueError(f"{name} contains a control character")
    return value


def _untrusted_text(value: str, *, name: str, maximum: int) -> str:
    """Accept instructions-looking RAG prose as data, but never secret material."""

    _text(value, name=name, maximum=maximum)
    if _SECRET_LIKE_RE.search(value):
        raise ValueError(f"{name} must not contain secret-like material")
    if any(scheme in value.casefold() for scheme in _FORBIDDEN_REF_SCHEMES):
        raise ValueError(f"{name} must not contain secret or raw credential references")
    return value


def _ref(value: str, *, name: str, schemes: tuple[str, ...] | None = None) -> str:
    _text(value, name=name, maximum=512)
    lowered = value.casefold()
    if lowered.startswith(_FORBIDDEN_REF_SCHEMES) or _SECRET_LIKE_RE.search(value) or not _SAFE_REF_RE.fullmatch(value):
        raise ValueError(f"{name} must be an admitted non-secret reference")
    if schemes is not None and not lowered.startswith(tuple(item.casefold() + "://" for item in schemes)):
        raise ValueError(f"{name} uses an unsupported reference scheme")
    return value


def _utc_timestamp(value: str, *, name: str) -> str:
    _text(value, name=name, maximum=64)
    if not _UTC_RFC3339_RE.fullmatch(value):
        raise ValueError(f"{name} must be an RFC3339 UTC timestamp")
    return value


def _receipt_elapsed_ms(*, started_at: str, ended_at: str) -> int:
    start = datetime.fromisoformat(_utc_timestamp(started_at, name="started_at").replace("Z", "+00:00"))
    end = datetime.fromisoformat(_utc_timestamp(ended_at, name="ended_at").replace("Z", "+00:00"))
    delta = end - start
    if delta.days < 0:
        raise ValueError("ended_at must not precede started_at")
    if delta.microseconds % 1000:
        raise ValueError("receipt timestamps must have millisecond precision")
    return (delta.days * 86400 + delta.seconds) * 1000 + delta.microseconds // 1000


def _optional_reason_code(value: str | None, *, name: str) -> None:
    if value is not None and (not isinstance(value, str) or not _STABLE_CODE_RE.fullmatch(value)):
        raise ValueError(f"{name} must be a stable uppercase code or null")


def _require_preview_unchanged(
    *, session_mode: ReasoningSessionMode, dataset_before_sha256: str, dataset_after_sha256: str,
    dataset_before_revision: int, dataset_after_revision: int,
    binding_before_revision: int, binding_after_revision: int,
    binding_before_status: TunedModelBindingStatus, binding_after_status: TunedModelBindingStatus,
    binding_before_sha256: str, binding_after_sha256: str,
    training_job_count_before: int, training_job_count_after: int,
) -> None:
    if session_mode is ReasoningSessionMode.PREVIEW_NO_LEARNING and not all((
        dataset_before_sha256 == dataset_after_sha256,
        dataset_before_revision == dataset_after_revision,
        binding_before_revision == binding_after_revision,
        binding_before_status == binding_after_status,
        binding_before_sha256 == binding_after_sha256,
        training_job_count_before == training_job_count_after,
    )):
        raise ValueError("PREVIEW_NO_LEARNING receipt must preserve all learning state")


def _sorted_unique(values: tuple[str, ...], *, name: str, maximum: int = 128) -> None:
    if not isinstance(values, tuple) or len(values) > maximum or values != tuple(sorted(set(values))):
        raise ValueError(f"{name} must be a bounded, unique, canonically sorted tuple")


def verify_canonical_record_sha256(record: Mapping[str, Any], *, checksum_field: str) -> None:
    """Fail closed unless a public contract's canonical digest is exact."""

    if not isinstance(record, Mapping) or checksum_field not in record:
        raise ValueError(f"{checksum_field} is required")
    supplied = record[checksum_field]
    if not isinstance(supplied, str):
        raise ValueError(f"{checksum_field} must be a string")
    validate_sha256(supplied, field_name=checksum_field)
    body = {key: value for key, value in record.items() if key != checksum_field}
    if sha256_bytes(canonical_json_bytes(body)) != supplied:
        raise ValueError(f"{checksum_field} does not match canonical content")


def _facts(values: tuple["ReasoningFact", ...], *, name: str) -> None:
    if not isinstance(values, tuple) or len(values) > 128 or any(not isinstance(item, ReasoningFact) for item in values):
        raise ValueError(f"{name} must contain at most 128 ReasoningFact values")
    keys = tuple((item.kind.value, item.key, item.value) for item in values)
    if keys != tuple(sorted(set(keys))):
        raise ValueError(f"{name} must be unique and canonically sorted")


@dataclass(frozen=True, slots=True)
class ReasoningFact:
    kind: CommentaryClaimKind
    key: str
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, CommentaryClaimKind):
            raise ValueError("kind must be CommentaryClaimKind")
        _text(self.key, name="fact key", maximum=256)
        _text(self.value, name="fact value", maximum=4096)

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind.value, "key": self.key, "value": self.value}

    def to_commentary_fact(self) -> CommentaryFact:
        return CommentaryFact(self.kind, self.key, self.value)

    def to_commentary_claim(self) -> CommentaryClaim:
        return CommentaryClaim(self.kind, self.key, self.value)


@dataclass(frozen=True, slots=True)
class RagChunk:
    source_ref: str
    source_type: str
    rights_status: str
    patch_interval: str
    verification_state: str
    text: str
    content_sha256: str
    content_role: str

    def __post_init__(self) -> None:
        _ref(self.source_ref, name="source_ref")
        for name in ("source_type", "rights_status", "verification_state"):
            if not _STABLE_CODE_RE.fullmatch(getattr(self, name)):
                raise ValueError(f"{name} must be a stable uppercase code")
        _text(self.patch_interval, name="patch_interval", maximum=128)
        _untrusted_text(self.text, name="RAG text", maximum=_MAX_RAG_CHUNK_TEXT)
        validate_sha256(self.content_sha256, field_name="content_sha256")
        if sha256_bytes(self.text.encode("utf-8")) != self.content_sha256:
            raise ValueError("RAG text does not match content_sha256")
        if self.content_role != "UNTRUSTED_DATA":
            raise ValueError("RAG content_role must be UNTRUSTED_DATA")

    def to_dict(self) -> dict[str, str]:
        return {
            "source_ref": self.source_ref,
            "source_type": self.source_type,
            "rights_status": self.rights_status,
            "patch_interval": self.patch_interval,
            "verification_state": self.verification_state,
            "text": self.text,
            "content_sha256": self.content_sha256,
            "content_role": self.content_role,
        }


@dataclass(frozen=True, slots=True)
class TunedModelBinding:
    binding_id: str
    revision: int
    status: TunedModelBindingStatus
    base_model_ref: str
    base_model_sha256: str
    adapter_ref: str
    adapter_sha256: str
    training_dataset_sha256: str | None
    training_recipe_sha256: str | None
    evaluation_report_sha256: str | None
    rights_manifest_sha256: str | None
    supported_locales: tuple[str, ...]
    approved_at: str | None = None
    approved_by_ref: str | None = None

    def __post_init__(self) -> None:
        _text(self.binding_id, name="binding_id", maximum=128)
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise ValueError("revision must be positive")
        if not isinstance(self.status, TunedModelBindingStatus):
            raise ValueError("status must be TunedModelBindingStatus")
        _ref(self.base_model_ref, name="base_model_ref", schemes=("model",))
        _ref(self.adapter_ref, name="adapter_ref", schemes=("model-adapter",))
        validate_sha256(self.base_model_sha256, field_name="base_model_sha256")
        validate_sha256(self.adapter_sha256, field_name="adapter_sha256")
        for name in (
            "training_dataset_sha256", "training_recipe_sha256",
            "evaluation_report_sha256", "rights_manifest_sha256",
        ):
            value = getattr(self, name)
            if value is not None:
                validate_sha256(value, field_name=name)
        _sorted_unique(self.supported_locales, name="supported_locales", maximum=16)
        if not self.supported_locales or any(not _LOCALE_RE.fullmatch(value) for value in self.supported_locales):
            raise ValueError("supported_locales contains an invalid locale")
        if self.status is TunedModelBindingStatus.APPROVED:
            required = (
                self.training_dataset_sha256, self.training_recipe_sha256,
                self.evaluation_report_sha256, self.rights_manifest_sha256,
                self.approved_at, self.approved_by_ref,
            )
            if any(value is None for value in required):
                raise ValueError("APPROVED binding requires complete lineage and Human approval")
            _ref(self.approved_by_ref or "", name="approved_by_ref", schemes=("human",))
            _utc_timestamp(self.approved_at or "", name="approved_at")
        elif self.approved_at is not None or self.approved_by_ref is not None:
            raise ValueError("only APPROVED bindings may carry approval metadata")

    @property
    def resolvable(self) -> bool:
        return self.status is TunedModelBindingStatus.APPROVED

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": SCHEMA_VERSION,
            "binding_id": self.binding_id,
            "revision": self.revision,
            "status": self.status.value,
            "purpose": "DBD_COMMENTARY_REASONING",
            "base_model_ref": self.base_model_ref,
            "base_model_sha256": self.base_model_sha256,
            "adapter_ref": self.adapter_ref,
            "adapter_sha256": self.adapter_sha256,
            "training_dataset_sha256": self.training_dataset_sha256,
            "training_recipe_sha256": self.training_recipe_sha256,
            "evaluation_report_sha256": self.evaluation_report_sha256,
            "rights_manifest_sha256": self.rights_manifest_sha256,
            "supported_locales": list(self.supported_locales),
            "context_schema": SCHEMA_VERSION,
            "output_schema": SCHEMA_VERSION,
            "route_capability": "DBD_TUNED_COMMENTARY_REASONING",
            "approved_at": self.approved_at,
            "approved_by_ref": self.approved_by_ref,
        }
        return {**body, "binding_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class DbDReasoningContextEnvelope:
    context_id: str
    match_id: str
    event_id: str
    event_revision: int
    event_sha256: str
    timeline_sha256: str
    game_version: str
    session_mode: ReasoningSessionMode
    freshness: ContextFreshness
    observed_facts: tuple[ReasoningFact, ...]
    canonical_facts: tuple[ReasoningFact, ...]
    evidence_refs: tuple[str, ...]
    knowledge_ref_sha256s: tuple[str, ...]
    rag_chunks: tuple[RagChunk, ...]
    uncertainties: tuple[str, ...]
    forbidden_claims: tuple[str, ...]
    speech_budget_ms: int
    language: str
    style_profile_ref: str

    def __post_init__(self) -> None:
        _text(self.context_id, name="context_id", maximum=128)
        validate_id(self.match_id, IdKind.GAME_MATCH)
        validate_id(self.event_id, IdKind.GAME_EVENT)
        _text(self.game_version, name="game_version", maximum=128)
        if isinstance(self.event_revision, bool) or not isinstance(self.event_revision, int) or self.event_revision < 1:
            raise ValueError("event_revision must be positive")
        validate_sha256(self.timeline_sha256, field_name="timeline_sha256")
        validate_sha256(self.event_sha256, field_name="event_sha256")
        if not isinstance(self.session_mode, ReasoningSessionMode):
            raise ValueError("session_mode must be ReasoningSessionMode")
        if not isinstance(self.freshness, ContextFreshness):
            raise ValueError("freshness must be ContextFreshness")
        for name in ("observed_facts", "canonical_facts"):
            _facts(getattr(self, name), name=name)
        _sorted_unique(self.evidence_refs, name="evidence_refs")
        for value in self.evidence_refs:
            validate_id(value, IdKind.GAME_EVIDENCE)
        _sorted_unique(self.knowledge_ref_sha256s, name="knowledge_ref_sha256s")
        for value in self.knowledge_ref_sha256s:
            validate_sha256(value, field_name="knowledge_ref_sha256")
        if not isinstance(self.rag_chunks, tuple) or len(self.rag_chunks) > 16 or any(not isinstance(item, RagChunk) for item in self.rag_chunks):
            raise ValueError("rag_chunks must contain at most 16 RagChunk values")
        refs = tuple(item.source_ref for item in self.rag_chunks)
        if refs != tuple(sorted(set(refs))):
            raise ValueError("rag_chunks must be unique and sorted by source_ref")
        if sum(len(item.text) for item in self.rag_chunks) > _MAX_RAG_TEXT_TOTAL:
            raise ValueError("rag_chunks text exceeds aggregate limit")
        for name in ("uncertainties", "forbidden_claims"):
            values = getattr(self, name)
            _sorted_unique(values, name=name, maximum=64)
            if any(not _STABLE_CODE_RE.fullmatch(value) for value in values):
                raise ValueError(f"{name} must contain stable uppercase codes")
        if isinstance(self.speech_budget_ms, bool) or not isinstance(self.speech_budget_ms, int) or not 0 <= self.speech_budget_ms <= 30000:
            raise ValueError("speech_budget_ms must be 0..30000")
        if not _LOCALE_RE.fullmatch(self.language):
            raise ValueError("language must be a locale")
        _ref(self.style_profile_ref, name="style_profile_ref", schemes=("style",))

    @property
    def training_eligible(self) -> bool:
        return self.session_mode.training_eligible

    @property
    def dispatchable(self) -> bool:
        return self.freshness is ContextFreshness.CURRENT and all(
            item.rights_status == "ADMITTED" and item.verification_state == "VERIFIED"
            for item in self.rag_chunks
        )

    def require_dispatchable(self) -> None:
        if not self.dispatchable:
            raise ValueError("only CURRENT, admitted, verified reasoning context is dispatchable")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "match_id": self.match_id,
            "event_id": self.event_id,
            "event_revision": self.event_revision,
            "event_sha256": self.event_sha256,
            "timeline_sha256": self.timeline_sha256,
            "game_version": self.game_version,
            "session_mode": self.session_mode.value,
            "freshness": self.freshness.value,
            "policy_version": SCHEMA_VERSION,
            "observed_facts": [item.to_dict() for item in self.observed_facts],
            "canonical_facts": [item.to_dict() for item in self.canonical_facts],
            "evidence_refs": list(self.evidence_refs),
            "knowledge_ref_sha256s": list(self.knowledge_ref_sha256s),
            "rag_chunks": [item.to_dict() for item in self.rag_chunks],
            "uncertainties": list(self.uncertainties),
            "forbidden_claims": list(self.forbidden_claims),
            "speech_budget_ms": self.speech_budget_ms,
            "language": self.language,
            "style_profile_ref": self.style_profile_ref,
            "training_eligible": self.training_eligible,
        }
        canonical = canonical_json_bytes(body)
        if len(canonical) > MAX_CONTEXT_CANONICAL_BYTES:
            raise ValueError("context canonical JSON exceeds maximum size")
        return {**body, "context_sha256": sha256_bytes(canonical)}


@dataclass(frozen=True, slots=True)
class ReasoningInference:
    statement: str
    qualifier: InferenceQualifier
    confidence_milli: int
    supporting_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.statement, name="inference statement", maximum=1000)
        if not isinstance(self.qualifier, InferenceQualifier):
            raise ValueError("qualifier must be POSSIBLE or LIKELY")
        if isinstance(self.confidence_milli, bool) or not isinstance(self.confidence_milli, int) or not 0 <= self.confidence_milli <= 1000:
            raise ValueError("confidence_milli must be 0..1000")
        _sorted_unique(self.supporting_refs, name="supporting_refs", maximum=32)
        for value in self.supporting_refs:
            _ref(value, name="supporting_ref")

    def to_dict(self) -> dict[str, Any]:
        return {
            "statement": self.statement,
            "qualifier": self.qualifier.value,
            "confidence_milli": self.confidence_milli,
            "supporting_refs": list(self.supporting_refs),
        }


@dataclass(frozen=True, slots=True)
class StyleMetrics:
    density_milli: int
    emotion_milli: int
    tempo_milli: int

    def __post_init__(self) -> None:
        for name in ("density_milli", "emotion_milli", "tempo_milli"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1000:
                raise ValueError(f"{name} must be 0..1000")

    def to_dict(self) -> dict[str, int]:
        return {
            "density_milli": self.density_milli,
            "emotion_milli": self.emotion_milli,
            "tempo_milli": self.tempo_milli,
        }


@dataclass(frozen=True, slots=True)
class DbDReasoningProposal:
    disposition: ReasoningDisposition
    observed_claims: tuple[ReasoningFact, ...]
    canonical_claims: tuple[ReasoningFact, ...]
    inferred_states: tuple[ReasoningInference, ...]
    tactical_interpretations: tuple[ReasoningInference, ...]
    commentary_outline: tuple[str, ...]
    commentary_text: str
    citations: tuple[str, ...]
    uncertainty_codes: tuple[str, ...]
    style_metrics: StyleMetrics

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, ReasoningDisposition):
            raise ValueError("disposition must be ReasoningDisposition")
        for name in ("observed_claims", "canonical_claims"):
            _facts(getattr(self, name), name=name)
        for name in ("inferred_states", "tactical_interpretations"):
            values = getattr(self, name)
            if not isinstance(values, tuple) or len(values) > 32 or any(not isinstance(item, ReasoningInference) for item in values):
                raise ValueError(f"{name} must contain at most 32 ReasoningInference values")
        if not isinstance(self.commentary_outline, tuple) or len(self.commentary_outline) > 16:
            raise ValueError("commentary_outline must be a bounded tuple")
        for value in self.commentary_outline:
            _text(value, name="commentary outline item", maximum=500)
        _text(self.commentary_text, name="commentary_text", maximum=8000, allow_empty=self.disposition is ReasoningDisposition.ABSTAIN)
        _sorted_unique(self.citations, name="citations", maximum=64)
        for value in self.citations:
            _ref(value, name="citation")
        _sorted_unique(self.uncertainty_codes, name="uncertainty_codes", maximum=64)
        if any(not _STABLE_CODE_RE.fullmatch(value) for value in self.uncertainty_codes):
            raise ValueError("uncertainty_codes must contain stable uppercase codes")
        if not isinstance(self.style_metrics, StyleMetrics):
            raise ValueError("style_metrics must be StyleMetrics")
        if self.disposition is ReasoningDisposition.ABSTAIN and any((self.observed_claims, self.canonical_claims, self.inferred_states, self.tactical_interpretations, self.commentary_outline, self.commentary_text, self.citations)):
            raise ValueError("ABSTAIN proposal must not carry speakable content")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": SCHEMA_VERSION,
            "disposition": self.disposition.value,
            "observed_claims": [item.to_dict() for item in self.observed_claims],
            "canonical_claims": [item.to_dict() for item in self.canonical_claims],
            "inferred_states": [item.to_dict() for item in self.inferred_states],
            "tactical_interpretations": [item.to_dict() for item in self.tactical_interpretations],
            "commentary_outline": list(self.commentary_outline),
            "commentary_text": self.commentary_text,
            "citations": list(self.citations),
            "uncertainty_codes": list(self.uncertainty_codes),
            "style_metrics": self.style_metrics.to_dict(),
        }
        return {**body, "proposal_sha256": sha256_bytes(canonical_json_bytes(body))}


def validate_context_freshness(
    context: DbDReasoningContextEnvelope,
    *,
    current_event_revision: int,
    event_sha256: str,
    timeline_sha256: str,
    game_version: str,
    knowledge_ref_sha256s: tuple[str, ...],
    rag_content_sha256s: tuple[str, ...],
) -> ContextFreshness:
    """Purely compare a context with the current canonical dependency snapshot."""

    if not isinstance(context, DbDReasoningContextEnvelope):
        raise TypeError("context must be DbDReasoningContextEnvelope")
    if isinstance(current_event_revision, bool) or not isinstance(current_event_revision, int) or current_event_revision < 1:
        raise ValueError("current_event_revision must be positive")
    validate_sha256(event_sha256, field_name="event_sha256")
    validate_sha256(timeline_sha256, field_name="timeline_sha256")
    _text(game_version, name="game_version", maximum=128)
    _sorted_unique(knowledge_ref_sha256s, name="knowledge_ref_sha256s")
    _sorted_unique(rag_content_sha256s, name="rag_content_sha256s", maximum=16)
    for value in (*knowledge_ref_sha256s, *rag_content_sha256s):
        validate_sha256(value, field_name="dependency_sha256")
    matches = (
        context.event_revision == current_event_revision
        and context.event_sha256 == event_sha256
        and context.timeline_sha256 == timeline_sha256
        and context.game_version == game_version
        and context.knowledge_ref_sha256s == knowledge_ref_sha256s
        and tuple(item.content_sha256 for item in context.rag_chunks) == rag_content_sha256s
    )
    return ContextFreshness.CURRENT if matches else ContextFreshness.STALE


@dataclass(frozen=True, slots=True)
class DbDReasoningExecutionReceipt:
    """Audit-only receipt.  Constructing it never executes a model or training job."""

    receipt_id: str
    attempt_id: str
    session_mode: ReasoningSessionMode
    context_sha256: str
    binding_revision: int
    binding_status: TunedModelBindingStatus
    binding_sha256: str
    prompt_sha256: str
    output_sha256: str
    prompt_template_sha256: str
    output_schema_sha256: str
    route_ref: str
    provider_ref: str
    base_model_ref: str
    adapter_ref: str
    authorization_ref: str
    authorization_decision: AuthorizationDecision
    cost_milli: int
    cost_ceiling_milli: int
    started_at: str
    ended_at: str
    elapsed_ms: int
    input_tokens: int
    output_tokens: int
    parser_passed: bool
    fact_validation_passed: bool
    policy_validation_passed: bool
    stale_result: ContextFreshness
    human_review_result: HumanReviewResult
    final_disposition: ReasoningDisposition
    fallback_reason_code: str | None
    retry_reason_code: str | None
    retry_count: int
    dataset_before_sha256: str
    dataset_after_sha256: str
    dataset_before_revision: int
    dataset_after_revision: int
    binding_before_revision: int
    binding_after_revision: int
    binding_before_status: TunedModelBindingStatus
    binding_after_status: TunedModelBindingStatus
    binding_before_sha256: str
    binding_after_sha256: str
    training_job_count_before: int
    training_job_count_after: int

    def __post_init__(self) -> None:
        _text(self.receipt_id, name="receipt_id", maximum=128)
        _text(self.attempt_id, name="attempt_id", maximum=128)
        if not isinstance(self.session_mode, ReasoningSessionMode):
            raise ValueError("session_mode must be ReasoningSessionMode")
        if not isinstance(self.binding_status, TunedModelBindingStatus):
            raise ValueError("binding_status must be TunedModelBindingStatus")
        if not isinstance(self.stale_result, ContextFreshness):
            raise ValueError("stale_result must be ContextFreshness")
        if not isinstance(self.human_review_result, HumanReviewResult):
            raise ValueError("human_review_result must be HumanReviewResult")
        if not isinstance(self.final_disposition, ReasoningDisposition):
            raise ValueError("final_disposition must be ReasoningDisposition")
        if not isinstance(self.authorization_decision, AuthorizationDecision):
            raise ValueError("authorization_decision must be AuthorizationDecision")
        _optional_reason_code(self.fallback_reason_code, name="fallback_reason_code")
        _optional_reason_code(self.retry_reason_code, name="retry_reason_code")
        if isinstance(self.retry_count, bool) or not isinstance(self.retry_count, int) or self.retry_count < 0:
            raise ValueError("retry_count must be a non-negative integer")
        if (self.retry_count == 0) != (self.retry_reason_code is None):
            raise ValueError("retry_reason_code must be null exactly when retry_count is zero")
        if not isinstance(self.binding_before_status, TunedModelBindingStatus) or not isinstance(self.binding_after_status, TunedModelBindingStatus):
            raise ValueError("binding status snapshots must be TunedModelBindingStatus")
        for name in ("context_sha256", "binding_sha256", "prompt_sha256", "output_sha256", "prompt_template_sha256", "output_schema_sha256", "dataset_before_sha256", "dataset_after_sha256", "binding_before_sha256", "binding_after_sha256"):
            validate_sha256(getattr(self, name), field_name=name)
        for name in ("route_ref", "provider_ref", "base_model_ref", "adapter_ref", "authorization_ref"):
            _ref(getattr(self, name), name=name)
        for name in ("binding_revision", "dataset_before_revision", "dataset_after_revision", "binding_before_revision", "binding_after_revision", "training_job_count_before", "training_job_count_after"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        for name in ("cost_milli", "cost_ceiling_milli", "elapsed_ms", "input_tokens", "output_tokens"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.cost_milli > self.cost_ceiling_milli:
            raise ValueError("cost_milli must not exceed cost_ceiling_milli")
        if self.elapsed_ms != _receipt_elapsed_ms(started_at=self.started_at, ended_at=self.ended_at):
            raise ValueError("elapsed_ms must equal the UTC timestamp difference")
        for name in ("parser_passed", "fact_validation_passed", "policy_validation_passed"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be bool")
        _require_preview_unchanged(
            session_mode=self.session_mode, dataset_before_sha256=self.dataset_before_sha256,
            dataset_after_sha256=self.dataset_after_sha256, dataset_before_revision=self.dataset_before_revision,
            dataset_after_revision=self.dataset_after_revision, binding_before_revision=self.binding_before_revision,
            binding_after_revision=self.binding_after_revision, binding_before_status=self.binding_before_status,
            binding_after_status=self.binding_after_status, binding_before_sha256=self.binding_before_sha256,
            binding_after_sha256=self.binding_after_sha256, training_job_count_before=self.training_job_count_before,
            training_job_count_after=self.training_job_count_after,
        )

    @property
    def training_eligible(self) -> bool:
        return self.session_mode.training_eligible

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": SCHEMA_VERSION, "receipt_id": self.receipt_id, "attempt_id": self.attempt_id,
            "session_mode": self.session_mode.value, "training_eligible": self.training_eligible,
            "context_sha256": self.context_sha256, "binding_revision": self.binding_revision,
            "binding_status": self.binding_status.value, "binding_sha256": self.binding_sha256,
            "prompt_sha256": self.prompt_sha256, "output_sha256": self.output_sha256,
            "prompt_template_sha256": self.prompt_template_sha256, "output_schema_sha256": self.output_schema_sha256,
            "route_ref": self.route_ref, "provider_ref": self.provider_ref, "base_model_ref": self.base_model_ref, "adapter_ref": self.adapter_ref,
            "authorization_ref": self.authorization_ref, "authorization_decision": self.authorization_decision.value,
            "cost_milli": self.cost_milli, "cost_ceiling_milli": self.cost_ceiling_milli,
            "started_at": self.started_at, "ended_at": self.ended_at,
            "elapsed_ms": self.elapsed_ms, "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
            "parser_passed": self.parser_passed, "fact_validation_passed": self.fact_validation_passed,
            "policy_validation_passed": self.policy_validation_passed, "stale_result": self.stale_result.value,
            "human_review_result": self.human_review_result.value, "final_disposition": self.final_disposition.value,
            "fallback_reason_code": self.fallback_reason_code, "retry_reason_code": self.retry_reason_code,
            "retry_count": self.retry_count,
            "dataset_before_sha256": self.dataset_before_sha256, "dataset_after_sha256": self.dataset_after_sha256,
            "dataset_before_revision": self.dataset_before_revision, "dataset_after_revision": self.dataset_after_revision,
            "binding_before_revision": self.binding_before_revision, "binding_after_revision": self.binding_after_revision,
            "binding_before_status": self.binding_before_status.value, "binding_after_status": self.binding_after_status.value,
            "binding_before_sha256": self.binding_before_sha256, "binding_after_sha256": self.binding_after_sha256,
            "training_job_count_before": self.training_job_count_before, "training_job_count_after": self.training_job_count_after,
        }
        return {**body, "receipt_sha256": sha256_bytes(canonical_json_bytes(body))}


def admit_reasoning_contract_record(record: Mapping[str, Any]) -> Mapping[str, Any]:
    """Validate schema version, JSON Schema, canonical record and embedded RAG digests."""

    if not isinstance(record, Mapping) or record.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported reasoning contract schema_version")
    from importlib.resources import files
    from jsonschema import Draft202012Validator

    schema = json.loads(files("ai_video_production.schema_resources").joinpath("dbd-reasoning-contracts.schema.json").read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(dict(record)))
    if errors:
        raise ValueError("reasoning contract does not satisfy JSON Schema")
    checksum_fields = ("receipt_sha256", "proposal_sha256", "context_sha256", "binding_sha256")
    checksum_field = next((field for field in checksum_fields if field in record), None)
    if checksum_field is None:
        raise ValueError("reasoning contract checksum is required")
    verify_canonical_record_sha256(record, checksum_field=checksum_field)

    def require_sha256(name: str) -> None:
        validate_sha256(record[name], field_name=name)

    def require_sorted_strings(name: str) -> None:
        values = record.get(name)
        if values is None:
            return
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values) or values != sorted(set(values)):
            raise ValueError(f"{name} must be unique and canonically sorted")

    def require_inference_refs(name: str) -> None:
        values = record.get(name, [])
        if not isinstance(values, list):
            raise ValueError(f"{name} must be a list")
        for value in values:
            if not isinstance(value, Mapping):
                raise ValueError(f"{name} must contain inference objects")
            refs = value.get("supporting_refs")
            if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs) or refs != sorted(set(refs)):
                raise ValueError(f"{name}.supporting_refs must be unique and canonically sorted")
            for ref in refs:
                _ref(ref, name=f"{name}.supporting_ref")

    for name in ("supported_locales", "evidence_refs", "knowledge_ref_sha256s", "uncertainties", "forbidden_claims", "citations", "uncertainty_codes"):
        require_sorted_strings(name)
    for name in ("observed_facts", "canonical_facts", "observed_claims", "canonical_claims"):
        values = record.get(name)
        if values is not None:
            if not isinstance(values, list) or any(not isinstance(item, Mapping) for item in values):
                raise ValueError(f"{name} must contain fact objects")
            keys = [(item.get("kind"), item.get("key"), item.get("value")) for item in values]
            if keys != sorted(set(keys)):
                raise ValueError(f"{name} must be unique and canonically sorted")
    for name in ("inferred_states", "tactical_interpretations"):
        require_inference_refs(name)
    for chunk in record.get("rag_chunks", []):
        if not isinstance(chunk, Mapping):
            raise ValueError("RAG chunk must be an object")
        text = chunk.get("text")
        if not isinstance(text, str):
            raise ValueError("RAG text must be a string")
        _untrusted_text(text, name="RAG text", maximum=_MAX_RAG_CHUNK_TEXT)
        if sha256_bytes(text.encode("utf-8")) != chunk.get("content_sha256"):
            raise ValueError("RAG content_sha256 is invalid")
    chunks = record.get("rag_chunks", [])
    if chunks:
        refs = [chunk["source_ref"] for chunk in chunks]
        if refs != sorted(set(refs)) or sum(len(chunk["text"]) for chunk in chunks) > _MAX_RAG_TEXT_TOTAL:
            raise ValueError("RAG chunks are not canonically admissible")
    if checksum_field == "binding_sha256":
        _ref(record["base_model_ref"], name="base_model_ref", schemes=("model",))
        _ref(record["adapter_ref"], name="adapter_ref", schemes=("model-adapter",))
        if record["status"] == TunedModelBindingStatus.APPROVED.value:
            for name in ("training_dataset_sha256", "training_recipe_sha256", "evaluation_report_sha256", "rights_manifest_sha256"):
                require_sha256(name)
            _ref(record["approved_by_ref"], name="approved_by_ref", schemes=("human",))
            _utc_timestamp(record["approved_at"], name="approved_at")
        elif record["approved_at"] is not None or record["approved_by_ref"] is not None:
            raise ValueError("only APPROVED binding may carry approval metadata")
    elif checksum_field == "context_sha256":
        body = {key: value for key, value in record.items() if key != "context_sha256"}
        if len(canonical_json_bytes(body)) > MAX_CONTEXT_CANONICAL_BYTES:
            raise ValueError("context canonical JSON exceeds maximum size")
        if record["freshness"] != ContextFreshness.CURRENT.value:
            raise ValueError("only CURRENT context is admissible for reasoning dispatch")
        if any(chunk["rights_status"] != "ADMITTED" or chunk["verification_state"] != "VERIFIED" for chunk in chunks):
            raise ValueError("only ADMITTED and VERIFIED RAG chunks are admissible for reasoning dispatch")
    elif checksum_field == "proposal_sha256":
        if record["disposition"] == ReasoningDisposition.ABSTAIN.value and any((
            record["observed_claims"], record["canonical_claims"], record["inferred_states"],
            record["tactical_interpretations"], record["commentary_outline"], record["commentary_text"], record["citations"],
        )):
            raise ValueError("ABSTAIN proposal must not carry speakable content")
    elif checksum_field == "receipt_sha256":
        _require_preview_unchanged(
            session_mode=ReasoningSessionMode(record["session_mode"]),
            dataset_before_sha256=record["dataset_before_sha256"], dataset_after_sha256=record["dataset_after_sha256"],
            dataset_before_revision=record["dataset_before_revision"], dataset_after_revision=record["dataset_after_revision"],
            binding_before_revision=record["binding_before_revision"], binding_after_revision=record["binding_after_revision"],
            binding_before_status=TunedModelBindingStatus(record["binding_before_status"]),
            binding_after_status=TunedModelBindingStatus(record["binding_after_status"]),
            binding_before_sha256=record["binding_before_sha256"], binding_after_sha256=record["binding_after_sha256"],
            training_job_count_before=record["training_job_count_before"], training_job_count_after=record["training_job_count_after"],
        )
        for name in ("route_ref", "provider_ref", "base_model_ref", "adapter_ref", "authorization_ref"):
            _ref(record[name], name=name)
        _utc_timestamp(record["started_at"], name="started_at")
        _utc_timestamp(record["ended_at"], name="ended_at")
        _optional_reason_code(record["fallback_reason_code"], name="fallback_reason_code")
        _optional_reason_code(record["retry_reason_code"], name="retry_reason_code")
        if (record["retry_count"] == 0) != (record["retry_reason_code"] is None):
            raise ValueError("retry_reason_code must be null exactly when retry_count is zero")
        if record["elapsed_ms"] != _receipt_elapsed_ms(started_at=record["started_at"], ended_at=record["ended_at"]):
            raise ValueError("elapsed_ms must equal the UTC timestamp difference")
        if record["cost_milli"] > record["cost_ceiling_milli"]:
            raise ValueError("cost_milli must not exceed cost_ceiling_milli")
    return record


__all__ = [
    "AuthorizationDecision", "ContextFreshness", "DbDReasoningContextEnvelope", "DbDReasoningExecutionReceipt", "DbDReasoningProposal", "HumanReviewResult", "InferenceQualifier", "MAX_CONTEXT_CANONICAL_BYTES",
    "RagChunk", "ReasoningDisposition", "ReasoningFact", "ReasoningInference",
    "ReasoningSessionMode", "SCHEMA_VERSION", "StyleMetrics", "TunedModelBinding",
    "TunedModelBindingStatus", "admit_reasoning_contract_record", "validate_context_freshness", "verify_canonical_record_sha256",
]
