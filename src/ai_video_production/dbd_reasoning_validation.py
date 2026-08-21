"""TASK-054 R2A strict, side-effect-free parser for tuned-reasoning output."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any
import unicodedata

from .dbd_reasoning_contracts import (
    InferenceQualifier,
    PROPOSAL_SCHEMA_VERSION,
    ReasoningDisposition,
)
from .game_commentary import CommentaryClaimKind
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


PARSER_VERSION = "2.0.0"
MAX_RAW_OUTPUT_BYTES = 128 * 1024
MAX_JSON_DEPTH = 32
_PROPOSAL_FIELDS = frozenset((
    "schema_version", "disposition", "observed_claims", "canonical_claims", "inferred_states",
    "tactical_interpretations", "commentary_outline", "commentary_text", "citations",
    "uncertainty_codes", "style_metrics",
))
_CONTROL_OR_SURROGATE_CATEGORIES = frozenset(("Cc", "Cf", "Cs"))
_GENERIC_SAFE_REF_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s\\@?#]+")
_STABLE_CODE_RE = re.compile(r"[A-Z][A-Z0-9_]{1,63}")
_OVERSIZE_SENTINEL_SHA256 = sha256_bytes(b"TASK-054:R2A:OVERSIZE_RAW_OUTPUT_NOT_HASHED")
_INVALID_TYPE_SENTINEL_SHA256 = sha256_bytes(b"TASK-054:R2A:INVALID_RAW_OUTPUT_TYPE")


@dataclass(frozen=True, slots=True, repr=False)
class StructuralReasoningFact:
    kind: str
    key: str
    value: str

    def __post_init__(self) -> None:
        CommentaryClaimKind(self.kind)
        _require_structural_text(self.key, maximum=256, name="fact key")
        _require_structural_text(self.value, maximum=4096, name="fact value")


@dataclass(frozen=True, slots=True, repr=False)
class StructuralReasoningInference:
    statement: str
    qualifier: str
    confidence_milli: int
    supporting_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_structural_text(self.statement, maximum=1000, name="inference statement")
        InferenceQualifier(self.qualifier)
        if isinstance(self.confidence_milli, bool) or not isinstance(self.confidence_milli, int) or not 0 <= self.confidence_milli <= 1000:
            raise ValueError("confidence_milli must be 0..1000")
        if self.supporting_refs != tuple(sorted(set(self.supporting_refs))) or len(self.supporting_refs) > 32:
            raise ValueError("supporting_refs must be bounded, unique and canonically sorted")
        for reference in self.supporting_refs:
            _require_structural_reference(reference)


@dataclass(frozen=True, slots=True, repr=False)
class StructuralStyleMetrics:
    density_milli: int
    emotion_milli: int
    tempo_milli: int

    def __post_init__(self) -> None:
        for value in (self.density_milli, self.emotion_milli, self.tempo_milli):
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1000:
                raise ValueError("style metrics must be 0..1000")


@dataclass(frozen=True, slots=True)
class StructuralReasoningProposal:
    """Quarantined structural output; deliberately not a canonical proposal."""

    state: str
    schema_version: str
    disposition: str
    observed_claims: tuple[StructuralReasoningFact, ...] = field(repr=False)
    canonical_claims: tuple[StructuralReasoningFact, ...] = field(repr=False)
    inferred_states: tuple[StructuralReasoningInference, ...] = field(repr=False)
    tactical_interpretations: tuple[StructuralReasoningInference, ...] = field(repr=False)
    commentary_outline: tuple[str, ...] = field(repr=False)
    commentary_text: str = field(repr=False)
    citations: tuple[str, ...] = field(repr=False)
    uncertainty_codes: tuple[str, ...] = field(repr=False)
    style_metrics: StructuralStyleMetrics = field(repr=False)
    structural_body_sha256: str = ""

    def __post_init__(self) -> None:
        if self.state != "STRUCTURAL_ONLY_NOT_ADMITTED" or self.schema_version != PROPOSAL_SCHEMA_VERSION:
            raise ValueError("quarantine state or schema version is invalid")
        disposition = ReasoningDisposition(self.disposition)
        for facts in (self.observed_claims, self.canonical_claims):
            if not isinstance(facts, tuple) or len(facts) > 128 or any(not isinstance(item, StructuralReasoningFact) for item in facts):
                raise ValueError("quarantine facts are invalid")
            keys = tuple((item.kind, item.key, item.value) for item in facts)
            if keys != tuple(sorted(set(keys))):
                raise ValueError("quarantine facts must be unique and canonically sorted")
        for values in (self.inferred_states, self.tactical_interpretations):
            if not isinstance(values, tuple) or len(values) > 32 or any(not isinstance(item, StructuralReasoningInference) for item in values):
                raise ValueError("quarantine inferences are invalid")
        if not isinstance(self.commentary_outline, tuple) or len(self.commentary_outline) > 16:
            raise ValueError("commentary outline is invalid")
        for line in self.commentary_outline:
            _require_structural_text(line, maximum=500, name="commentary outline")
        _require_structural_text(self.commentary_text, maximum=8000, name="commentary text", allow_empty=disposition is ReasoningDisposition.ABSTAIN)
        if self.citations != tuple(sorted(set(self.citations))) or len(self.citations) > 64:
            raise ValueError("citations must be bounded, unique and canonically sorted")
        for reference in self.citations:
            _require_structural_reference(reference)
        if self.uncertainty_codes != tuple(sorted(set(self.uncertainty_codes))) or len(self.uncertainty_codes) > 64:
            raise ValueError("uncertainty codes must be bounded, unique and canonically sorted")
        if any(not _STABLE_CODE_RE.fullmatch(code) for code in self.uncertainty_codes):
            raise ValueError("uncertainty code is invalid")
        if not isinstance(self.style_metrics, StructuralStyleMetrics):
            raise ValueError("style metrics are invalid")
        validate_sha256(self.structural_body_sha256, field_name="structural_body_sha256")
        if self.structural_body_sha256 != sha256_bytes(canonical_json_bytes(_structural_proposal_body(self))):
            raise ValueError("structural_body_sha256 does not match quarantine content")
        if disposition is ReasoningDisposition.ABSTAIN and any((self.observed_claims, self.canonical_claims, self.inferred_states, self.tactical_interpretations, self.commentary_outline, self.commentary_text, self.citations)):
            raise ValueError("ABSTAIN quarantine must not carry speakable content")


@dataclass(frozen=True, slots=True)
class StructuralParseResult:
    structurally_valid: bool
    quarantined_proposal: StructuralReasoningProposal | None
    raw_output_sha256: str
    parser_version: str
    error_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.structurally_valid, bool):
            raise ValueError("structurally_valid must be bool")
        if (self.quarantined_proposal is not None) is not self.structurally_valid:
            raise ValueError("quarantine is present exactly when parsing passed")
        if self.quarantined_proposal is not None and not isinstance(self.quarantined_proposal, StructuralReasoningProposal):
            raise ValueError("quarantined_proposal must be StructuralReasoningProposal or null")
        validate_sha256(self.raw_output_sha256, field_name="raw_output_sha256")
        if self.parser_version != PARSER_VERSION:
            raise ValueError("parser_version is unsupported")
        if not isinstance(self.error_codes, tuple) or self.error_codes != tuple(sorted(set(self.error_codes))):
            raise ValueError("error_codes must be unique and canonically sorted")
        if any(not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", code) for code in self.error_codes):
            raise ValueError("error_codes must be stable codes")
        if self.structurally_valid != (not self.error_codes):
            raise ValueError("error_codes must be empty exactly when parsing passed")


class DbDReasoningProposalParser:
    """Parse one exact UTF-8 JSON object into a non-admitted quarantine.

    The parser keeps only the output checksum and never writes, logs, calls a
    provider, retains raw model output, or creates a canonical proposal.
    """

    def parse(self, raw_output: bytes) -> StructuralParseResult:
        if not isinstance(raw_output, bytes):
            return _failure(_INVALID_TYPE_SENTINEL_SHA256, "RAW_OUTPUT_TYPE_INVALID")
        if len(raw_output) > MAX_RAW_OUTPUT_BYTES:
            # Do not hash attacker-controlled oversized bodies.  The sentinel
            # documents that no body digest was retained or computed.
            return _failure(_OVERSIZE_SENTINEL_SHA256, "RAW_OUTPUT_SIZE_INVALID")
        raw_digest = sha256_bytes(raw_output)
        if not raw_output:
            return _failure(raw_digest, "RAW_OUTPUT_SIZE_INVALID")
        if raw_output.startswith(b"\xef\xbb\xbf"):
            return _failure(raw_digest, "RAW_OUTPUT_BOM_FORBIDDEN")
        if _stream_depth_exceeds(raw_output, maximum=MAX_JSON_DEPTH):
            return _failure(raw_digest, "JSON_DEPTH_EXCEEDED")
        try:
            text = raw_output.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return _failure(raw_digest, "RAW_OUTPUT_UTF8_INVALID")
        try:
            value = json.loads(
                text,
                object_pairs_hook=_unique_object,
                parse_constant=_reject_json_constant,
            )
        except _DuplicateJsonKey:
            return _failure(raw_digest, "JSON_DUPLICATE_KEY")
        except (MemoryError, RecursionError):
            return _failure(raw_digest, "JSON_RESOURCE_LIMIT")
        except (ValueError, json.JSONDecodeError):
            return _failure(raw_digest, "JSON_SYNTAX_INVALID")
        if not isinstance(value, dict):
            return _failure(raw_digest, "JSON_ROOT_OBJECT_REQUIRED")
        if _depth(value) > MAX_JSON_DEPTH:
            return _failure(raw_digest, "JSON_DEPTH_EXCEEDED")
        if set(value) != _PROPOSAL_FIELDS:
            return _failure(raw_digest, "PROPOSAL_SHAPE_INVALID")
        if not _structural_strings_are_admitted(value):
            return _failure(raw_digest, "OUTPUT_STRING_INVALID")
        try:
            quarantine = _proposal_from_value(value)
        except _ShapeError as exc:
            return _failure(raw_digest, exc.code)
        except (TypeError, ValueError):
            return _failure(raw_digest, "PROPOSAL_CONTRACT_INVALID")
        return StructuralParseResult(True, quarantine, raw_digest, PARSER_VERSION, ())


class _DuplicateJsonKey(ValueError):
    pass


class _ShapeError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code


def _failure(raw_digest: str, *codes: str) -> StructuralParseResult:
    return StructuralParseResult(False, None, raw_digest, PARSER_VERSION, tuple(sorted(set(codes))))


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateJsonKey(key)
        value[key] = item
    return value


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"JSON constant {value} is forbidden")


def _depth(value: Any) -> int:
    maximum = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        maximum = max(maximum, depth)
        if isinstance(current, dict):
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)
    return maximum


def _stream_depth_exceeds(raw_output: bytes, *, maximum: int) -> bool:
    """Count JSON brackets without allocating recursive Python structures."""

    depth = 0
    in_string = False
    escaped = False
    for byte in raw_output:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5C:
                escaped = True
            elif byte == 0x22:
                in_string = False
            continue
        if byte == 0x22:
            in_string = True
        elif byte in (0x5B, 0x7B):
            depth += 1
            if depth > maximum:
                return True
        elif byte in (0x5D, 0x7D):
            depth = max(0, depth - 1)
    return False


def _text_is_structurally_safe(value: str) -> bool:
    """Reject non-scalar/control text without assigning semantic meaning."""

    if any(unicodedata.category(character) in _CONTROL_OR_SURROGATE_CATEGORIES for character in value):
        return False
    normalized = unicodedata.normalize("NFKC", value)
    return not any(unicodedata.category(character) in _CONTROL_OR_SURROGATE_CATEGORIES for character in normalized)


def _require_structural_text(value: str, *, maximum: int, name: str, allow_empty: bool = False) -> None:
    if not isinstance(value, str) or len(value) > maximum or (not allow_empty and not value):
        raise ValueError(f"{name} has invalid type or length")
    if not _text_is_structurally_safe(value):
        raise ValueError(f"{name} contains structurally unsafe Unicode")


def _reference_is_structurally_safe(value: str) -> bool:
    return _text_is_structurally_safe(value) and _GENERIC_SAFE_REF_RE.fullmatch(value) is not None


def _require_structural_reference(value: str) -> None:
    if not isinstance(value, str) or len(value) > 512 or not _reference_is_structurally_safe(value):
        raise ValueError("reference has invalid structural syntax or length")


def _structural_proposal_body(proposal: StructuralReasoningProposal) -> dict[str, Any]:
    return {
        "schema_version": proposal.schema_version,
        "disposition": proposal.disposition,
        "observed_claims": [{"kind": item.kind, "key": item.key, "value": item.value} for item in proposal.observed_claims],
        "canonical_claims": [{"kind": item.kind, "key": item.key, "value": item.value} for item in proposal.canonical_claims],
        "inferred_states": [
            {"statement": item.statement, "qualifier": item.qualifier, "confidence_milli": item.confidence_milli, "supporting_refs": list(item.supporting_refs)}
            for item in proposal.inferred_states
        ],
        "tactical_interpretations": [
            {"statement": item.statement, "qualifier": item.qualifier, "confidence_milli": item.confidence_milli, "supporting_refs": list(item.supporting_refs)}
            for item in proposal.tactical_interpretations
        ],
        "commentary_outline": list(proposal.commentary_outline),
        "commentary_text": proposal.commentary_text,
        "citations": list(proposal.citations),
        "uncertainty_codes": list(proposal.uncertainty_codes),
        "style_metrics": {
            "density_milli": proposal.style_metrics.density_milli,
            "emotion_milli": proposal.style_metrics.emotion_milli,
            "tempo_milli": proposal.style_metrics.tempo_milli,
        },
    }


def _structural_strings_are_admitted(value: Any, *, reference_list: bool = False) -> bool:
    if isinstance(value, str):
        return _reference_is_structurally_safe(value) if reference_list else _text_is_structurally_safe(value)
    if isinstance(value, list):
        return all(_structural_strings_are_admitted(item, reference_list=reference_list) for item in value)
    if isinstance(value, dict):
        for key, item in value.items():
            if not _text_is_structurally_safe(key):
                return False
            child_is_reference_list = key in {"citations", "supporting_refs"}
            if not _structural_strings_are_admitted(item, reference_list=child_is_reference_list):
                return False
        return True
    return True


def _object(value: Any, *, fields: frozenset[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise _ShapeError(code)
    return value


def _list(value: Any, *, maximum: int, code: str) -> list[Any]:
    if not isinstance(value, list) or len(value) > maximum:
        raise _ShapeError(code)
    return value


def _string(value: Any, *, maximum: int, allow_empty: bool, code: str) -> str:
    if not isinstance(value, str) or len(value) > maximum or (not allow_empty and not value):
        raise _ShapeError(code)
    return value


def _fact(value: Any) -> StructuralReasoningFact:
    item = _object(value, fields=frozenset(("kind", "key", "value")), code="FACT_SHAPE_INVALID")
    try:
        kind = CommentaryClaimKind(item["kind"])
        return StructuralReasoningFact(
            kind.value,
            _string(item["key"], maximum=256, allow_empty=False, code="FACT_SHAPE_INVALID"),
            _string(item["value"], maximum=4096, allow_empty=False, code="FACT_SHAPE_INVALID"),
        )
    except (TypeError, ValueError) as exc:
        raise _ShapeError("FACT_VALUE_INVALID") from exc


def _inference(value: Any) -> StructuralReasoningInference:
    item = _object(value, fields=frozenset(("statement", "qualifier", "confidence_milli", "supporting_refs")), code="INFERENCE_SHAPE_INVALID")
    refs = _list(item["supporting_refs"], maximum=32, code="INFERENCE_SHAPE_INVALID")
    if any(not isinstance(ref, str) for ref in refs):
        raise _ShapeError("INFERENCE_SHAPE_INVALID")
    try:
        qualifier = InferenceQualifier(item["qualifier"])
        confidence = item["confidence_milli"]
        if isinstance(confidence, bool) or not isinstance(confidence, int) or not 0 <= confidence <= 1000:
            raise ValueError("confidence_milli must be 0..1000")
        refs_tuple = tuple(_string(ref, maximum=512, allow_empty=False, code="INFERENCE_SHAPE_INVALID") for ref in refs)
        if refs_tuple != tuple(sorted(set(refs_tuple))):
            raise ValueError("supporting_refs must be unique and canonically sorted")
        return StructuralReasoningInference(
            _string(item["statement"], maximum=1000, allow_empty=False, code="INFERENCE_SHAPE_INVALID"),
            qualifier.value,
            confidence,
            refs_tuple,
        )
    except (TypeError, ValueError) as exc:
        raise _ShapeError("INFERENCE_VALUE_INVALID") from exc


def _facts(value: Any) -> tuple[StructuralReasoningFact, ...]:
    facts = tuple(_fact(item) for item in _list(value, maximum=128, code="FACTS_SHAPE_INVALID"))
    keys = tuple((item.kind, item.key, item.value) for item in facts)
    if keys != tuple(sorted(set(keys))):
        raise _ShapeError("FACTS_VALUE_INVALID")
    return facts


def _inferences(value: Any) -> tuple[StructuralReasoningInference, ...]:
    return tuple(_inference(item) for item in _list(value, maximum=32, code="INFERENCES_SHAPE_INVALID"))


def _proposal_from_value(value: dict[str, Any]) -> StructuralReasoningProposal:
    item = _object(value, fields=_PROPOSAL_FIELDS, code="PROPOSAL_SHAPE_INVALID")
    if item["schema_version"] != PROPOSAL_SCHEMA_VERSION:
        raise _ShapeError("PROPOSAL_SCHEMA_VERSION_INVALID")
    outline = _list(item["commentary_outline"], maximum=16, code="OUTLINE_SHAPE_INVALID")
    citations = _list(item["citations"], maximum=64, code="CITATIONS_SHAPE_INVALID")
    uncertainties = _list(item["uncertainty_codes"], maximum=64, code="UNCERTAINTIES_SHAPE_INVALID")
    if any(not isinstance(entry, str) for entry in (*outline, *citations, *uncertainties)):
        raise _ShapeError("PROPOSAL_STRING_LIST_INVALID")
    metrics = _object(item["style_metrics"], fields=frozenset(("density_milli", "emotion_milli", "tempo_milli")), code="STYLE_METRICS_SHAPE_INVALID")
    try:
        disposition = ReasoningDisposition(item["disposition"])
        observed = _facts(item["observed_claims"])
        canonical = _facts(item["canonical_claims"])
        inferred = _inferences(item["inferred_states"])
        tactical = _inferences(item["tactical_interpretations"])
        outline_values = tuple(_string(entry, maximum=500, allow_empty=False, code="OUTLINE_VALUE_INVALID") for entry in outline)
        text = _string(item["commentary_text"], maximum=8000, allow_empty=disposition is ReasoningDisposition.ABSTAIN, code="COMMENTARY_TEXT_INVALID")
        citations_tuple = tuple(_string(reference, maximum=512, allow_empty=False, code="CITATIONS_SHAPE_INVALID") for reference in citations)
        uncertainties_tuple = tuple(uncertainties)
        if citations_tuple != tuple(sorted(set(citations_tuple))):
            raise ValueError("citations must be unique and canonically sorted")
        if uncertainties_tuple != tuple(sorted(set(uncertainties_tuple))) or any(not _STABLE_CODE_RE.fullmatch(code) for code in uncertainties_tuple):
            raise ValueError("uncertainty codes are invalid")
        metric_values = tuple(metrics[name] for name in ("density_milli", "emotion_milli", "tempo_milli"))
        if any(isinstance(metric, bool) or not isinstance(metric, int) or not 0 <= metric <= 1000 for metric in metric_values):
            raise ValueError("style metrics must be 0..1000")
        if disposition is ReasoningDisposition.ABSTAIN and any((observed, canonical, inferred, tactical, outline_values, text, citations_tuple)):
            raise ValueError("ABSTAIN proposal must not carry speakable content")
        body_sha256 = sha256_bytes(canonical_json_bytes(value))
        return StructuralReasoningProposal(
            state="STRUCTURAL_ONLY_NOT_ADMITTED",
            schema_version=PROPOSAL_SCHEMA_VERSION,
            disposition=disposition.value,
            observed_claims=observed,
            canonical_claims=canonical,
            inferred_states=inferred,
            tactical_interpretations=tactical,
            commentary_outline=outline_values,
            commentary_text=text,
            citations=citations_tuple,
            uncertainty_codes=uncertainties_tuple,
            style_metrics=StructuralStyleMetrics(*metric_values),
            structural_body_sha256=body_sha256,
        )
    except (TypeError, ValueError) as exc:
        raise _ShapeError("PROPOSAL_VALUE_INVALID") from exc


__all__ = [
    "DbDReasoningProposalParser", "MAX_JSON_DEPTH", "MAX_RAW_OUTPUT_BYTES", "PARSER_VERSION",
    "StructuralParseResult", "StructuralReasoningFact", "StructuralReasoningInference",
    "StructuralReasoningProposal", "StructuralStyleMetrics",
]
