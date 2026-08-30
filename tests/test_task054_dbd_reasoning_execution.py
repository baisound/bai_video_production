from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.ai_connections import (
    AiConnectionProfile, AiWorkload, ConnectionAvailability, CostClass,
    ModelRoute, ProviderFamily, ReasoningEffort, SelectionMode,
)
from ai_video_production.canonical_game_event import GameEnvironment
from ai_video_production.dbd_reasoning_contracts import (
    ContextFreshness, DbDReasoningContextEnvelope, ReasoningFact,
    ReasoningSessionMode, TunedModelBinding, TunedModelBindingStatus,
)
from ai_video_production.dbd_reasoning_execution import (
    AUTHORIZATION_STATE, DbDPreviewStateSnapshot,
    DbDReasoningExecutionAuthorization, DbDReasoningExecutionService,
    LocalDbDGeneration, LocalDbDReasoningTextAdapter,
    admit_dbd_reasoning_execution_authorization,
)
from ai_video_production.dbd_reasoning_routing import (
    DbDReasoningRouteCapabilityResolver, ROUTE_CAPABILITY,
)
from ai_video_production.dbd_tuned_model_registry import (
    BindingLifecycleTransition, DbDTunedModelRegistry, DbDTunedModelRegistryRecord,
)
from ai_video_production.errors import ProductError
from ai_video_production.game_commentary import CommentaryClaimKind
from ai_video_production.provider_execution import (
    AiProviderExecutionService, TextGenerationRequest,
)


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
SHA_E = "sha256:" + "e" * 64
MATCH_ID = "MATCH-01J5K4C2QH0F5S2BXNJQ2A1R9C"
EVENT_ID = "GEVT-01J5K4C2QH0F5S2BXNJQ2A1R9C"
EVIDENCE_ID = "GEVD-01J5K4C2QH0F5S2BXNJQ2A1R9C"


class NoCredentials:
    def resolve(self, _ref: str) -> str:
        raise AssertionError("local R3D execution must not resolve credentials")


class AuthorityVerifier:
    def __init__(self, trusted_sha256: str = SHA_E) -> None:
        self.trusted_sha256 = trusted_sha256

    def verify(self, authority_evidence_sha256: str) -> bool:
        return authority_evidence_sha256 == self.trusted_sha256


class UseStore:
    def __init__(self) -> None:
        self.claimed: set[str] = set()

    def claim_once(self, authorization_sha256: str) -> bool:
        if authorization_sha256 in self.claimed:
            return False
        self.claimed.add(authorization_sha256)

        return True

class Runtime:
    def __init__(self, *, base_sha: str = SHA_A, adapter_sha: str = SHA_B) -> None:
        self.base_sha = base_sha
        self.adapter_sha = adapter_sha
        self.calls: list[tuple[str, TextGenerationRequest]] = []

    def generate(self, model_id: str, request: TextGenerationRequest) -> LocalDbDGeneration:
        self.calls.append((model_id, request))
        payload = {
            "schema_version": "1.0.0", "disposition": "PROPOSE",
            "observed_claims": [], "canonical_claims": [],
            "inferred_states": [], "tactical_interpretations": [],
            "commentary_outline": ["フックを確認"],
            "commentary_text": "フックに入りました。", "citations": [],
            "uncertainty_codes": [],
            "style_metrics": {"density_milli": 500, "emotion_milli": 400, "tempo_milli": 600},
        }
        return LocalDbDGeneration(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            self.base_sha, self.adapter_sha, 11, 17,
        )


def _binding(revision: int, status: TunedModelBindingStatus) -> TunedModelBinding:
    complete = status is not TunedModelBindingStatus.DRAFT
    approved = status is TunedModelBindingStatus.APPROVED
    return TunedModelBinding(
        binding_id="dbd-ja", revision=revision, status=status,
        base_model_ref="model://registry/base/v1", base_model_sha256=SHA_A,
        adapter_ref="model-adapter://registry/dbd/a", adapter_sha256=SHA_B,
        training_dataset_sha256=SHA_C if complete else None,
        training_recipe_sha256=SHA_D if complete else None,
        evaluation_report_sha256=SHA_E if complete else None,
        rights_manifest_sha256=SHA_A if complete else None,
        supported_locales=("ja-JP",),
        approved_at="2026-08-26T00:03:00Z" if approved else None,
        approved_by_ref="human://operator/approval-1" if approved else None,
    )


def _record(
    binding: TunedModelBinding, transition: BindingLifecycleTransition,
    previous: DbDTunedModelRegistryRecord | None, evidence_sha: str,
) -> DbDTunedModelRegistryRecord:
    human = transition is BindingLifecycleTransition.APPROVE
    return DbDTunedModelRegistryRecord(
        binding=binding, transition=transition,
        previous_record_sha256=None if previous is None else previous.registry_record_sha256,
        decision_evidence_ref=(
            f"human-confirmation://01ARZ3NDEKTSV4RRFFQ69G5FA{binding.revision}"
            if human else (
                "registry-intake" if transition is BindingLifecycleTransition.REGISTER
                else "evaluation"
            ) + f"://sha256/{evidence_sha.removeprefix('sha256:')}"
        ),
        decision_evidence_sha256=evidence_sha,
        recorded_at=f"2026-08-26T00:0{binding.revision}:00Z",
    )


def _inputs(runtime: Runtime | None = None):
    draft = _record(_binding(1, TunedModelBindingStatus.DRAFT), BindingLifecycleTransition.REGISTER, None, SHA_A)
    evaluated = _record(_binding(2, TunedModelBindingStatus.EVALUATED), BindingLifecycleTransition.EVALUATE, draft, SHA_E)
    approved = _record(_binding(3, TunedModelBindingStatus.APPROVED), BindingLifecycleTransition.APPROVE, evaluated, SHA_A)
    registry = DbDTunedModelRegistry((draft, evaluated, approved))
    binding = approved.binding
    route = ModelRoute(
        "dbd-tuned", AiWorkload.PLANNING, ProviderFamily.LOCAL_OPEN_SOURCE,
        "local-runtime", "dbd-base:v1", CostClass.LOCAL_FREE_AI,
        reasoning_effort=ReasoningEffort.HIGH, capabilities=(ROUTE_CAPABILITY,),
        settings={
            "dbd_tuned_binding_id": binding.binding_id,
            "dbd_tuned_binding_revision": binding.revision,
            "dbd_tuned_binding_sha256": binding.to_dict()["binding_sha256"],
            "dbd_base_model_sha256": binding.base_model_sha256,
            "dbd_adapter_sha256": binding.adapter_sha256,
            "temperature": 0.0,
        },
    )
    profile = AiConnectionProfile("dbd-profile", "1.0.0", SelectionMode.AUTO, (route,))
    availability = ConnectionAvailability(frozenset({route.route_id}))
    decision = DbDReasoningRouteCapabilityResolver.resolve(registry, profile, availability, locale="ja-JP")
    local_runtime = runtime or Runtime()
    provider = AiProviderExecutionService((LocalDbDReasoningTextAdapter(local_runtime),), NoCredentials())
    return registry, profile, availability, decision, local_runtime, provider


def _context() -> DbDReasoningContextEnvelope:
    return DbDReasoningContextEnvelope(
        context_id="context-1", match_id=MATCH_ID, event_id=EVENT_ID,
        event_revision=1, event_sha256=SHA_A, evidence_snapshot_sha256=SHA_A,
        timeline_sha256=SHA_A, game_version="dbd-9.0",
        game_environment=GameEnvironment.LIVE, rag_snapshot_sha256=SHA_A,
        session_mode=ReasoningSessionMode.PREVIEW_NO_LEARNING,
        freshness=ContextFreshness.CURRENT,
        observed_facts=(ReasoningFact(CommentaryClaimKind.EVENT_OCCURRED, "EVENT", "HOOK"),),
        canonical_facts=(ReasoningFact(CommentaryClaimKind.EVENT_OCCURRED, "EVENT", "HOOK"),),
        evidence_refs=(EVIDENCE_ID,), knowledge_ref_sha256s=(SHA_A,),
        rag_chunks=(), uncertainties=(), forbidden_claims=(), speech_budget_ms=3000,
        language="ja", style_profile_ref="style://commentary/default",
    )


def _authorization(decision) -> DbDReasoningExecutionAuthorization:
    return DbDReasoningExecutionAuthorization(
        "owner-r3d-approval", SHA_E, decision.to_dict()["route_decision_sha256"],
        decision.binding_id, decision.binding_revision, decision.binding_sha256,
        "2026-08-26T00:00:00Z", "2026-08-26T01:00:00Z", 256,
    )


def test_local_preview_executes_through_canonical_provider_and_emits_body_free_receipt() -> None:
    registry, profile, availability, decision, runtime, provider = _inputs()
    state = DbDPreviewStateSnapshot(SHA_C, 4, 0)
    result = DbDReasoningExecutionService(provider, AuthorityVerifier(), UseStore()).execute_local_preview(
        attempt_id="attempt-1", authorization=_authorization(decision), decision=decision,
        registry=registry, profile=profile, availability=availability, locale="ja-JP",
        context=_context(), prompt="証拠だけで実況候補をJSON生成してください。",
        prompt_template_sha256=SHA_D, output_schema_sha256=SHA_E,
        state_before=state, state_after=state, now="2026-08-26T00:10:00Z",
        started_at="2026-08-26T00:10:00Z", ended_at="2026-08-26T00:10:01Z",
    )
    assert result.parser_result.structurally_valid is True
    assert result.receipt.parser_passed is True
    assert result.receipt.fact_validation_passed is False
    assert result.receipt.policy_validation_passed is False
    assert result.receipt.training_eligible is False
    assert result.receipt.dataset_before_sha256 == result.receipt.dataset_after_sha256
    assert result.receipt.final_disposition.value == "REVIEW_REQUIRED"
    assert len(runtime.calls) == 1
    assert "フック" not in repr(result.receipt)


def test_authorization_is_exact_checksum_bound_and_time_bounded() -> None:
    _, _, _, decision, runtime, provider = _inputs()
    authorization = _authorization(decision)
    assert admit_dbd_reasoning_execution_authorization(authorization.to_dict()) == authorization
    assert authorization.authorization_state == AUTHORIZATION_STATE
    forged = authorization.to_dict()
    forged["binding_revision"] = 99
    with pytest.raises(ValueError, match="checksum"):
        admit_dbd_reasoning_execution_authorization(forged)
    with pytest.raises(ProductError, match="not active"):
        authorization.validate_for(decision, now="2026-08-26T02:00:00Z")
    assert runtime.calls == []


def test_stale_route_fails_before_runtime_and_artifact_crossing_is_rejected() -> None:
    registry, profile, availability, decision, runtime, provider = _inputs()
    changed = replace(profile.routes[0], model_id="other-model")
    with pytest.raises(ProductError):
        DbDReasoningExecutionService(provider, AuthorityVerifier(), UseStore()).execute_local_preview(
            attempt_id="attempt-2", authorization=_authorization(decision), decision=decision,
            registry=registry, profile=replace(profile, routes=(changed,)), availability=availability,
            locale="ja-JP", context=_context(), prompt="JSONを生成",
            prompt_template_sha256=SHA_D, output_schema_sha256=SHA_E,
            state_before=DbDPreviewStateSnapshot(SHA_C, 4, 0),
            state_after=DbDPreviewStateSnapshot(SHA_C, 4, 0),
            now="2026-08-26T00:10:00Z", started_at="2026-08-26T00:10:00Z",
            ended_at="2026-08-26T00:10:01Z",
        )
    assert runtime.calls == []

    bad_runtime = Runtime(adapter_sha=SHA_E)
    _, _, _, _, _, bad_provider = _inputs(bad_runtime)
    route = profile.routes[0]
    with pytest.raises(ProductError, match="different model artifacts"):
        LocalDbDReasoningTextAdapter(bad_runtime).generate(
            route, TextGenerationRequest("JSONを生成"), None,
        )


def test_preview_state_drift_and_nonlocal_route_fail_closed() -> None:
    registry, profile, availability, decision, _, provider = _inputs()
    with pytest.raises(ProductError, match="changed Dataset"):
        DbDReasoningExecutionService(provider, AuthorityVerifier(), UseStore()).execute_local_preview(
            attempt_id="attempt-3", authorization=_authorization(decision), decision=decision,
            registry=registry, profile=profile, availability=availability, locale="ja-JP",
            context=_context(), prompt="JSONを生成", prompt_template_sha256=SHA_D,
            output_schema_sha256=SHA_E,
            state_before=DbDPreviewStateSnapshot(SHA_C, 4, 0),
            state_after=DbDPreviewStateSnapshot(SHA_D, 5, 1),
            now="2026-08-26T00:10:00Z", started_at="2026-08-26T00:10:00Z",
            ended_at="2026-08-26T00:10:01Z",
        )
    paid = replace(
        profile.routes[0], cost_class=CostClass.CLOUD_PAID_AI,
        credential_ref="credential://provider/default",
    )
    with pytest.raises(ProductError, match="not eligible"):
        LocalDbDReasoningTextAdapter(Runtime()).generate(
            paid, TextGenerationRequest("JSONを生成"), "secret",
        )


@pytest.mark.parametrize("capabilities", [(), [ROUTE_CAPABILITY], (ROUTE_CAPABILITY, ROUTE_CAPABILITY)])
def test_provider_capability_entry_rejects_noncanonical_capabilities(capabilities) -> None:
    _, profile, availability, _, _, provider = _inputs()
    with pytest.raises(ValueError, match="required_capabilities"):
        provider.generate_planning_text_for_capabilities(
            profile, availability, TextGenerationRequest("JSONを生成"),
            required_capabilities=capabilities,
        )


def test_authorization_schema_mirror_and_closed_object_admission() -> None:
    root = Path(__file__).resolve().parents[1]
    canonical = root / "schemas" / "dbd-reasoning-execution-authorization.schema.json"
    mirror = root / "src" / "ai_video_production" / "schema_resources" / canonical.name
    assert canonical.read_bytes() == mirror.read_bytes()
    schema = json.loads(canonical.read_text(encoding="utf-8"))
    _, _, _, decision, _, _ = _inputs()
    record = _authorization(decision).to_dict()
    assert list(Draft202012Validator(schema).iter_errors(record)) == []
    crossed = dict(record)
    crossed["unexpected"] = True
    assert list(Draft202012Validator(schema).iter_errors(crossed))


def _execute_guard_case(provider, use_store, registry, profile, availability, decision):
    state = DbDPreviewStateSnapshot(SHA_C, 4, 0)
    return DbDReasoningExecutionService(provider, AuthorityVerifier(), use_store).execute_local_preview(
        attempt_id="attempt-guard", authorization=_authorization(decision), decision=decision,
        registry=registry, profile=profile, availability=availability, locale="ja-JP",
        context=_context(), prompt="JSONを生成", prompt_template_sha256=SHA_D,
        output_schema_sha256=SHA_E, state_before=state, state_after=state,
        now="2026-08-26T00:10:00Z", started_at="2026-08-26T00:10:00Z",
        ended_at="2026-08-26T00:10:01Z",
    )


def test_consumed_authorization_fails_before_runtime_dispatch() -> None:
    registry, profile, availability, decision, runtime, provider = _inputs()

    class AlreadyUsed:
        def claim_once(self, _authorization_sha256: str) -> bool:
            return False

    with pytest.raises(ProductError, match="already been consumed"):
        _execute_guard_case(provider, AlreadyUsed(), registry, profile, availability, decision)
    assert runtime.calls == []


def test_runtime_reported_output_tokens_cannot_exceed_authorization() -> None:
    class ExcessRuntime(Runtime):
        def generate(self, model_id: str, request: TextGenerationRequest) -> LocalDbDGeneration:
            value = super().generate(model_id, request)
            return replace(value, output_tokens=9999)

    runtime = ExcessRuntime()
    registry, profile, availability, decision, _, provider = _inputs(runtime)
    with pytest.raises(ProductError, match="output-token ceiling"):
        _execute_guard_case(provider, UseStore(), registry, profile, availability, decision)
    assert len(runtime.calls) == 1


def test_untrusted_authority_evidence_fails_before_claim_and_runtime() -> None:
    registry, profile, availability, decision, runtime, provider = _inputs()
    state = DbDPreviewStateSnapshot(SHA_C, 4, 0)
    use_store = UseStore()
    with pytest.raises(ProductError, match="not trusted"):
        DbDReasoningExecutionService(
            provider, AuthorityVerifier(SHA_A), use_store,
        ).execute_local_preview(
            attempt_id="attempt-untrusted", authorization=_authorization(decision),
            decision=decision, registry=registry, profile=profile,
            availability=availability, locale="ja-JP", context=_context(),
            prompt="JSONを生成", prompt_template_sha256=SHA_D,
            output_schema_sha256=SHA_E, state_before=state, state_after=state,
            now="2026-08-26T00:10:00Z",
            started_at="2026-08-26T00:10:00Z",
            ended_at="2026-08-26T00:10:01Z",
        )
    assert use_store.claimed == set()
    assert runtime.calls == []
