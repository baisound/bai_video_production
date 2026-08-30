from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
import re

from .ai_connections import AiConnectionProfile, ConnectionAvailability
from .dbd_reasoning_routing import (
    DbDReasoningRouteCapabilityResolver,
    DbDReasoningRouteDecision,
    admit_dbd_reasoning_route_decision,
)
from .dbd_reasoning_validation import (
    DbDReasoningProposalParser,
    MAX_RAW_OUTPUT_BYTES,
    StructuralParseResult,
    StructuralReasoningFact,
    StructuralReasoningInference,
    StructuralReasoningProposal,
    StructuralStyleMetrics,
)
from .dbd_tuned_model_registry import DbDTunedModelRegistry
from .serialization import validate_sha256


FAKE_EXECUTION_STATE = "TEST_ONLY_NO_PROVIDER_EXECUTION"
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")


class FakeAdapterOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    MALFORMED_OUTPUT = "MALFORMED_OUTPUT"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    RUNTIME_UNAVAILABLE = "RUNTIME_UNAVAILABLE"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"


_FAULT_CODES = {
    FakeAdapterOutcome.MALFORMED_OUTPUT: "FAKE_OUTPUT_REJECTED",
    FakeAdapterOutcome.TIMEOUT: "FAKE_TIMEOUT",
    FakeAdapterOutcome.CANCELLED: "FAKE_CANCELLED",
    FakeAdapterOutcome.RUNTIME_UNAVAILABLE: "FAKE_RUNTIME_UNAVAILABLE",
    FakeAdapterOutcome.RESOURCE_LIMIT: "FAKE_RESOURCE_LIMIT",
}
_NO_OUTPUT_OUTCOMES = frozenset({
    FakeAdapterOutcome.TIMEOUT,
    FakeAdapterOutcome.CANCELLED,
    FakeAdapterOutcome.RUNTIME_UNAVAILABLE,
    FakeAdapterOutcome.RESOURCE_LIMIT,
})
_FAKE_ADMISSION_TOKEN = object()


def _safe_id(value: str, *, name: str) -> None:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{name} is invalid")


def _nonnegative_int(value: int, *, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _admit_parse_result(value: StructuralParseResult) -> StructuralParseResult:
    if not isinstance(value, StructuralParseResult):
        raise ValueError("parser_result must be StructuralParseResult")
    proposal = value.quarantined_proposal
    rebuilt_proposal = None
    if proposal is not None:
        if not isinstance(proposal, StructuralReasoningProposal):
            raise ValueError("quarantined proposal type is invalid")
        rebuilt_proposal = replace(
            proposal,
            observed_claims=tuple(replace(item) for item in proposal.observed_claims if isinstance(item, StructuralReasoningFact)),
            canonical_claims=tuple(replace(item) for item in proposal.canonical_claims if isinstance(item, StructuralReasoningFact)),
            inferred_states=tuple(replace(item) for item in proposal.inferred_states if isinstance(item, StructuralReasoningInference)),
            tactical_interpretations=tuple(replace(item) for item in proposal.tactical_interpretations if isinstance(item, StructuralReasoningInference)),
            style_metrics=replace(proposal.style_metrics) if isinstance(proposal.style_metrics, StructuralStyleMetrics) else proposal.style_metrics,
        )
    rebuilt = replace(value, quarantined_proposal=rebuilt_proposal)
    if rebuilt != value:
        raise ValueError("parser_result is not exact canonical form")
    return rebuilt


@dataclass(frozen=True, slots=True, repr=False)
class DbDReasoningFakeScenario:
    scenario_id: str
    outcome: FakeAdapterOutcome
    raw_output: bytes | None = field(default=None, repr=False)
    elapsed_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def __post_init__(self) -> None:
        _safe_id(self.scenario_id, name="scenario_id")
        if not isinstance(self.outcome, FakeAdapterOutcome):
            raise ValueError("outcome must be FakeAdapterOutcome")
        for name in ("elapsed_ms", "input_tokens", "output_tokens"):
            _nonnegative_int(getattr(self, name), name=name)
        if self.outcome in {FakeAdapterOutcome.SUCCESS, FakeAdapterOutcome.MALFORMED_OUTPUT}:
            if not isinstance(self.raw_output, bytes) or not self.raw_output:
                raise ValueError("output scenarios require non-empty raw bytes")
        elif self.raw_output is not None:
            raise ValueError("non-output fault scenarios cannot carry raw bytes")
        if self.outcome is FakeAdapterOutcome.SUCCESS and len(self.raw_output or b"") > MAX_RAW_OUTPUT_BYTES:
            raise ValueError("SUCCESS raw output exceeds the parser ceiling")
        if self.outcome in _NO_OUTPUT_OUTCOMES and self.output_tokens != 0:
            raise ValueError("non-output fault scenarios cannot report output tokens")


@dataclass(frozen=True, slots=True)
class DbDReasoningFakeInvocation:
    attempt_id: str
    route_decision: DbDReasoningRouteDecision
    context_sha256: str
    prompt_template_sha256: str
    output_schema_sha256: str
    execution_state: str = FAKE_EXECUTION_STATE

    def __post_init__(self) -> None:
        _safe_id(self.attempt_id, name="attempt_id")
        if not isinstance(self.route_decision, DbDReasoningRouteDecision):
            raise ValueError("route_decision must be DbDReasoningRouteDecision")
        admitted = admit_dbd_reasoning_route_decision(self.route_decision.to_dict())
        if admitted != self.route_decision:
            raise ValueError("route_decision is not exact canonical form")
        for name in ("context_sha256", "prompt_template_sha256", "output_schema_sha256"):
            validate_sha256(getattr(self, name), field_name=name)
        if self.execution_state != FAKE_EXECUTION_STATE:
            raise ValueError("fake invocation cannot grant execution authority")


@dataclass(frozen=True, slots=True)
class DbDReasoningFakeAttempt:
    attempt_id: str
    scenario_id: str
    outcome: FakeAdapterOutcome
    route_decision_sha256: str
    context_sha256: str
    prompt_template_sha256: str
    output_schema_sha256: str
    raw_output_sha256: str | None
    parser_result: StructuralParseResult | None = field(repr=False)
    error_code: str | None
    elapsed_ms: int
    input_tokens: int
    output_tokens: int
    execution_state: str = FAKE_EXECUTION_STATE

    def __post_init__(self) -> None:
        _safe_id(self.attempt_id, name="attempt_id")
        _safe_id(self.scenario_id, name="scenario_id")
        if not isinstance(self.outcome, FakeAdapterOutcome):
            raise ValueError("outcome must be FakeAdapterOutcome")
        for name in ("route_decision_sha256", "context_sha256", "prompt_template_sha256", "output_schema_sha256"):
            validate_sha256(getattr(self, name), field_name=name)
        for name in ("elapsed_ms", "input_tokens", "output_tokens"):
            _nonnegative_int(getattr(self, name), name=name)
        if self.execution_state != FAKE_EXECUTION_STATE:
            raise ValueError("fake attempt cannot grant execution authority")
        if self.outcome in {FakeAdapterOutcome.SUCCESS, FakeAdapterOutcome.MALFORMED_OUTPUT}:
            if self.raw_output_sha256 is None or not isinstance(self.parser_result, StructuralParseResult):
                raise ValueError("output attempts require a digest and parser result")
            validate_sha256(self.raw_output_sha256, field_name="raw_output_sha256")
            admitted_parser_result = _admit_parse_result(self.parser_result)
            if admitted_parser_result.raw_output_sha256 != self.raw_output_sha256:
                raise ValueError("parser result and raw output digest do not match")
            expected_valid = self.outcome is FakeAdapterOutcome.SUCCESS
            if self.parser_result.structurally_valid is not expected_valid:
                raise ValueError("scenario outcome and parser result disagree")
            expected_code = None if expected_valid else _FAULT_CODES[self.outcome]
            if self.error_code != expected_code:
                raise ValueError("scenario outcome and error code disagree")
        else:
            if self.raw_output_sha256 is not None or self.parser_result is not None:
                raise ValueError("non-output fault attempts cannot retain output or parser state")
            if self.error_code != _FAULT_CODES[self.outcome]:
                raise ValueError("scenario outcome and error code disagree")
            if self.output_tokens != 0:
                raise ValueError("non-output fault attempts cannot report output tokens")


@dataclass(frozen=True, slots=True, repr=False)
class _FakeEmission:
    raw_output: bytes | None = field(repr=False)
    error_code: str | None


class DeterministicDbDReasoningFakeAdapter:
    """Test-only fake; it has no Provider, credential, runtime or I/O surface."""

    @staticmethod
    def emit(scenario: DbDReasoningFakeScenario, *, _admission_token: object) -> _FakeEmission:
        if _admission_token is not _FAKE_ADMISSION_TOKEN:
            raise ValueError("fake emission requires current-route admission")
        if not isinstance(scenario, DbDReasoningFakeScenario):
            raise ValueError("scenario must be DbDReasoningFakeScenario")
        return _FakeEmission(
            raw_output=scenario.raw_output,
            error_code=None if scenario.outcome is FakeAdapterOutcome.SUCCESS else _FAULT_CODES[scenario.outcome],
        )


class DbDReasoningFakeFaultHarness:
    """Revalidate R3B state, emit one fixture and immediately discard raw bytes."""

    def __init__(self, parser: DbDReasoningProposalParser | None = None) -> None:
        if parser is not None and type(parser) is not DbDReasoningProposalParser:
            raise ValueError("harness requires the canonical strict parser")
        self._parser = parser or DbDReasoningProposalParser()

    def run(
        self,
        invocation: DbDReasoningFakeInvocation,
        scenario: DbDReasoningFakeScenario,
        *,
        registry: DbDTunedModelRegistry,
        profile: AiConnectionProfile,
        availability: ConnectionAvailability,
        locale: str,
        binding_id: str | None = None,
    ) -> DbDReasoningFakeAttempt:
        if not isinstance(invocation, DbDReasoningFakeInvocation):
            raise ValueError("invocation must be DbDReasoningFakeInvocation")
        current = DbDReasoningRouteCapabilityResolver.validate_current(
            invocation.route_decision,
            registry,
            profile,
            availability,
            locale=locale,
            binding_id=binding_id,
        )
        emission = DeterministicDbDReasoningFakeAdapter.emit(
            scenario, _admission_token=_FAKE_ADMISSION_TOKEN,
        )
        parser_result = self._parser.parse(emission.raw_output) if emission.raw_output is not None else None
        raw_digest = parser_result.raw_output_sha256 if parser_result is not None else None
        return DbDReasoningFakeAttempt(
            attempt_id=invocation.attempt_id,
            scenario_id=scenario.scenario_id,
            outcome=scenario.outcome,
            route_decision_sha256=current.to_dict()["route_decision_sha256"],
            context_sha256=invocation.context_sha256,
            prompt_template_sha256=invocation.prompt_template_sha256,
            output_schema_sha256=invocation.output_schema_sha256,
            raw_output_sha256=raw_digest,
            parser_result=parser_result,
            error_code=emission.error_code,
            elapsed_ms=scenario.elapsed_ms,
            input_tokens=scenario.input_tokens,
            output_tokens=scenario.output_tokens,
        )


__all__ = [
    "DbDReasoningFakeAttempt", "DbDReasoningFakeFaultHarness",
    "DbDReasoningFakeInvocation", "DbDReasoningFakeScenario",
    "DeterministicDbDReasoningFakeAdapter", "FAKE_EXECUTION_STATE",
    "FakeAdapterOutcome",
]
