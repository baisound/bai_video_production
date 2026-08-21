from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from ai_video_production.ai_connections import (
    AiConnectionProfile,
    AiWorkload,
    ConnectionAvailability,
    CostClass,
    ModelRoute,
    ProviderFamily,
    ReasoningEffort,
    SelectionMode,
)
from ai_video_production.dbd_reasoning_contracts import TunedModelBinding, TunedModelBindingStatus
from ai_video_production.dbd_reasoning_fake_adapter import (
    DbDReasoningFakeAttempt,
    DbDReasoningFakeFaultHarness,
    DbDReasoningFakeInvocation,
    DbDReasoningFakeScenario,
    DeterministicDbDReasoningFakeAdapter,
    FAKE_EXECUTION_STATE,
    FakeAdapterOutcome,
)
from ai_video_production.dbd_reasoning_routing import (
    DbDReasoningRouteCapabilityResolver,
    ROUTE_CAPABILITY,
)
from ai_video_production.dbd_tuned_model_registry import (
    BindingLifecycleTransition,
    DbDTunedModelRegistry,
    DbDTunedModelRegistryRecord,
)
from ai_video_production.dbd_reasoning_validation import MAX_RAW_OUTPUT_BYTES
from ai_video_production.errors import ProductError


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
SHA_E = "sha256:" + "e" * 64


def _binding(revision: int, status: TunedModelBindingStatus) -> TunedModelBinding:
    complete = status is not TunedModelBindingStatus.DRAFT
    approved = status is TunedModelBindingStatus.APPROVED
    return TunedModelBinding(
        binding_id="dbd-ja", revision=revision, status=status,
        base_model_ref="model://registry/base/v1", base_model_sha256=SHA_A,
        adapter_ref="model-adapter://registry/dbd/a", adapter_sha256=SHA_A,
        training_dataset_sha256=SHA_B if complete else None,
        training_recipe_sha256=SHA_C if complete else None,
        evaluation_report_sha256=SHA_D if complete else None,
        rights_manifest_sha256=SHA_E if complete else None,
        supported_locales=("ja-JP",),
        approved_at="2026-08-22T00:03:00Z" if approved else None,
        approved_by_ref="human://operator/approval-1" if approved else None,
    )


def _record(binding: TunedModelBinding, transition: BindingLifecycleTransition, previous: DbDTunedModelRegistryRecord | None, evidence_sha: str) -> DbDTunedModelRegistryRecord:
    technical = transition in {BindingLifecycleTransition.REGISTER, BindingLifecycleTransition.EVALUATE}
    scheme = "registry-intake" if transition is BindingLifecycleTransition.REGISTER else "evaluation"
    return DbDTunedModelRegistryRecord(
        binding=binding,
        transition=transition,
        previous_record_sha256=None if previous is None else previous.registry_record_sha256,
        decision_evidence_ref=(
            f"{scheme}://sha256/{evidence_sha.removeprefix('sha256:')}"
            if technical else f"human-confirmation://01ARZ3NDEKTSV4RRFFQ69G5FA{binding.revision}"
        ),
        decision_evidence_sha256=evidence_sha,
        recorded_at=f"2026-08-22T00:0{binding.revision}:00Z",
    )


def _current_inputs():
    draft = _record(_binding(1, TunedModelBindingStatus.DRAFT), BindingLifecycleTransition.REGISTER, None, SHA_A)
    evaluated = _record(_binding(2, TunedModelBindingStatus.EVALUATED), BindingLifecycleTransition.EVALUATE, draft, SHA_D)
    approved = _record(_binding(3, TunedModelBindingStatus.APPROVED), BindingLifecycleTransition.APPROVE, evaluated, SHA_A)
    registry = DbDTunedModelRegistry((draft, evaluated, approved))
    binding_sha = approved.binding.to_dict()["binding_sha256"]
    route = ModelRoute(
        route_id="dbd-tuned", workload=AiWorkload.PLANNING,
        provider_family=ProviderFamily.LOCAL_OPEN_SOURCE, provider_id="local-runtime",
        model_id="dbd-base:v1", cost_class=CostClass.LOCAL_FREE_AI,
        reasoning_effort=ReasoningEffort.HIGH, capabilities=(ROUTE_CAPABILITY,),
        settings={
            "dbd_tuned_binding_id": "dbd-ja",
            "dbd_tuned_binding_revision": 3,
            "dbd_tuned_binding_sha256": binding_sha,
        },
    )
    profile = AiConnectionProfile("dbd-profile", "1.0.0", SelectionMode.AUTO, (route,))
    availability = ConnectionAvailability(frozenset({route.route_id}))
    decision = DbDReasoningRouteCapabilityResolver.resolve(
        registry, profile, availability, locale="ja-JP",
    )
    invocation = DbDReasoningFakeInvocation(
        attempt_id="attempt-1", route_decision=decision, context_sha256=SHA_A,
        prompt_template_sha256=SHA_B, output_schema_sha256=SHA_C,
    )
    return registry, profile, availability, invocation


def _valid_raw() -> bytes:
    payload = {
        "schema_version": "1.0.0",
        "disposition": "PROPOSE",
        "observed_claims": [],
        "canonical_claims": [],
        "inferred_states": [],
        "tactical_interpretations": [],
        "commentary_outline": ["フックを確認"],
        "commentary_text": "フックに入りました。",
        "citations": [],
        "uncertainty_codes": [],
        "style_metrics": {"density_milli": 500, "emotion_milli": 400, "tempo_milli": 600},
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _run(scenario: DbDReasoningFakeScenario):
    registry, profile, availability, invocation = _current_inputs()
    return DbDReasoningFakeFaultHarness().run(
        invocation, scenario, registry=registry, profile=profile,
        availability=availability, locale="ja-JP",
    )


def test_success_is_deterministic_quarantined_and_raw_is_not_retained() -> None:
    scenario = DbDReasoningFakeScenario("success", FakeAdapterOutcome.SUCCESS, _valid_raw(), 12, 50, 20)
    first = _run(scenario)
    second = _run(scenario)
    assert first == second
    assert first.parser_result is not None and first.parser_result.structurally_valid is True
    assert first.error_code is None
    assert first.execution_state == FAKE_EXECUTION_STATE
    assert not hasattr(first, "raw_output")
    assert "フック" not in repr(first)


@pytest.mark.parametrize("raw", [b"{", b'{"x":1,"x":2}', b"x" * (MAX_RAW_OUTPUT_BYTES + 1)])
def test_malformed_duplicate_and_oversized_output_stay_in_r2a_failure(raw: bytes) -> None:
    result = _run(DbDReasoningFakeScenario("malformed", FakeAdapterOutcome.MALFORMED_OUTPUT, raw, 1, 1, 1))
    assert result.error_code == "FAKE_OUTPUT_REJECTED"
    assert result.parser_result is not None and result.parser_result.structurally_valid is False
    assert result.raw_output_sha256 == result.parser_result.raw_output_sha256


@pytest.mark.parametrize("outcome,code", [
    (FakeAdapterOutcome.TIMEOUT, "FAKE_TIMEOUT"),
    (FakeAdapterOutcome.CANCELLED, "FAKE_CANCELLED"),
    (FakeAdapterOutcome.RUNTIME_UNAVAILABLE, "FAKE_RUNTIME_UNAVAILABLE"),
    (FakeAdapterOutcome.RESOURCE_LIMIT, "FAKE_RESOURCE_LIMIT"),
])
def test_non_output_faults_are_body_free(outcome: FakeAdapterOutcome, code: str) -> None:
    result = _run(DbDReasoningFakeScenario(outcome.value.casefold(), outcome, None, 10, 5, 0))
    assert result.error_code == code
    assert result.raw_output_sha256 is None
    assert result.parser_result is None
    assert result.output_tokens == 0


@pytest.mark.parametrize("kwargs", [
    {"outcome": FakeAdapterOutcome.SUCCESS, "raw_output": None},
    {"outcome": FakeAdapterOutcome.TIMEOUT, "raw_output": b"body"},
    {"outcome": FakeAdapterOutcome.TIMEOUT, "raw_output": None, "output_tokens": 1},
    {"outcome": FakeAdapterOutcome.SUCCESS, "raw_output": b"{}", "elapsed_ms": True},
])
def test_scenario_invariants_reject_crossed_state(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        DbDReasoningFakeScenario("bad", **kwargs)


def test_attempt_invariants_reject_forged_authority_and_digest_crossing() -> None:
    result = _run(DbDReasoningFakeScenario("success", FakeAdapterOutcome.SUCCESS, _valid_raw()))
    with pytest.raises(ValueError, match="execution authority"):
        replace(result, execution_state="AUTHORIZED")
    with pytest.raises(ValueError, match="digest"):
        replace(result, raw_output_sha256=SHA_E)
    with pytest.raises(ValueError, match="disagree"):
        replace(result, outcome=FakeAdapterOutcome.MALFORMED_OUTPUT)


def test_stale_route_decision_fails_before_parser_invocation() -> None:
    registry, profile, availability, invocation = _current_inputs()
    changed_route = replace(profile.routes[0], model_id="other-model")
    changed_profile = replace(profile, routes=(changed_route,))
    with pytest.raises(ProductError):
        DbDReasoningFakeFaultHarness().run(
            invocation,
            DbDReasoningFakeScenario("success", FakeAdapterOutcome.SUCCESS, _valid_raw()),
            registry=registry, profile=changed_profile, availability=availability, locale="ja-JP",
        )


def test_harness_rejects_noncanonical_parser_and_attempt_rejects_mutated_result() -> None:
    class FakeParser:
        pass

    with pytest.raises(ValueError, match="canonical strict parser"):
        DbDReasoningFakeFaultHarness(FakeParser())
    result = _run(DbDReasoningFakeScenario("success", FakeAdapterOutcome.SUCCESS, _valid_raw()))
    assert result.parser_result is not None
    object.__setattr__(result.parser_result, "structurally_valid", False)
    with pytest.raises(ValueError):
        replace(result)


def test_fake_emitter_cannot_bypass_current_route_admission() -> None:
    scenario = DbDReasoningFakeScenario("success", FakeAdapterOutcome.SUCCESS, _valid_raw())
    with pytest.raises(ValueError, match="current-route admission"):
        DeterministicDbDReasoningFakeAdapter.emit(scenario, _admission_token=object())


def test_revoked_binding_and_unavailable_route_fail_before_emission() -> None:
    registry, profile, availability, invocation = _current_inputs()
    rows = list(registry.records)
    suspended = _record(_binding(4, TunedModelBindingStatus.SUSPENDED), BindingLifecycleTransition.SUSPEND, rows[-1], SHA_B)
    revoked = _record(_binding(5, TunedModelBindingStatus.REVOKED), BindingLifecycleTransition.REVOKE, suspended, SHA_C)
    scenario = DbDReasoningFakeScenario("success", FakeAdapterOutcome.SUCCESS, _valid_raw())
    with pytest.raises(ProductError):
        DbDReasoningFakeFaultHarness().run(
            invocation, scenario, registry=DbDTunedModelRegistry(tuple(rows + [suspended, revoked])),
            profile=profile, availability=availability, locale="ja-JP",
        )
    with pytest.raises(ProductError):
        DbDReasoningFakeFaultHarness().run(
            invocation, scenario, registry=registry, profile=profile,
            availability=ConnectionAvailability(frozenset()), locale="ja-JP",
        )


def test_fake_module_has_no_effectful_or_canonical_adoption_surface() -> None:
    source = Path("src/ai_video_production/dbd_reasoning_fake_adapter.py").read_text(encoding="utf-8")
    for forbidden in (
        "sqlite3", "subprocess", "requests", "urllib", "CredentialStore",
        "TextProviderAdapter", "DbDReasoningExecutionReceipt", "CommentaryCandidate",
        "open(", "write_text", "write_bytes", "sleep(", "random.", "secrets.",
    ):
        assert forbidden not in source
