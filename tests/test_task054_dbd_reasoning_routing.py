from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

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
from ai_video_production.dbd_reasoning_routing import (
    DbDReasoningRouteCapabilityResolver,
    EXECUTION_AUTHORITY_STATE,
    ROUTE_CAPABILITY,
    admit_dbd_reasoning_route_decision,
)
from ai_video_production.dbd_tuned_model_registry import (
    BindingLifecycleTransition,
    DbDTunedModelRegistry,
    DbDTunedModelRegistryRecord,
)
from ai_video_production.errors import ProductError
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
SHA_E = "sha256:" + "e" * 64


def _binding(revision: int, status: TunedModelBindingStatus, *, binding_id: str = "dbd-ja", adapter: str = "a") -> TunedModelBinding:
    complete = status is not TunedModelBindingStatus.DRAFT
    approved = status is TunedModelBindingStatus.APPROVED
    return TunedModelBinding(
        binding_id=binding_id,
        revision=revision,
        status=status,
        base_model_ref="model://registry/base/v1",
        base_model_sha256=SHA_A,
        adapter_ref=f"model-adapter://registry/dbd/{adapter}",
        adapter_sha256="sha256:" + adapter * 64,
        training_dataset_sha256=SHA_B if complete else None,
        training_recipe_sha256=SHA_C if complete else None,
        evaluation_report_sha256=SHA_D if complete else None,
        rights_manifest_sha256=SHA_E if complete else None,
        supported_locales=("ja-JP",),
        approved_at="2026-08-22T00:03:00Z" if approved else None,
        approved_by_ref="human://operator/approval-1" if approved else None,
    )


def _record(binding: TunedModelBinding, transition: BindingLifecycleTransition, previous: DbDTunedModelRegistryRecord | None) -> DbDTunedModelRegistryRecord:
    human = transition in {
        BindingLifecycleTransition.APPROVE,
        BindingLifecycleTransition.REJECT,
        BindingLifecycleTransition.SUSPEND,
        BindingLifecycleTransition.REINSTATE,
        BindingLifecycleTransition.REVOKE,
    }
    evidence_sha = (
        SHA_D if transition is BindingLifecycleTransition.EVALUATE
        else {3: SHA_A, 4: SHA_B, 5: SHA_C, 6: SHA_D, 7: SHA_E}.get(binding.revision, SHA_A)
    )
    return DbDTunedModelRegistryRecord(
        binding=binding,
        transition=transition,
        previous_record_sha256=None if previous is None else previous.registry_record_sha256,
        decision_evidence_ref=(
            f"human-confirmation://01ARZ3NDEKTSV4RRFFQ69G5FA{binding.revision}"
            if human
            else ("registry-intake" if transition is BindingLifecycleTransition.REGISTER else "evaluation")
            + f"://sha256/{evidence_sha.removeprefix('sha256:')}"
        ),
        decision_evidence_sha256=evidence_sha,
        recorded_at=f"2026-08-22T00:0{binding.revision}:00Z",
    )


def _approved_chain(*, binding_id: str = "dbd-ja", adapter: str = "a") -> tuple[DbDTunedModelRegistryRecord, ...]:
    draft = _record(_binding(1, TunedModelBindingStatus.DRAFT, binding_id=binding_id, adapter=adapter), BindingLifecycleTransition.REGISTER, None)
    evaluated = _record(_binding(2, TunedModelBindingStatus.EVALUATED, binding_id=binding_id, adapter=adapter), BindingLifecycleTransition.EVALUATE, draft)
    approved = _record(_binding(3, TunedModelBindingStatus.APPROVED, binding_id=binding_id, adapter=adapter), BindingLifecycleTransition.APPROVE, evaluated)
    return draft, evaluated, approved


def _route(binding: TunedModelBinding, *, route_id: str = "dbd-tuned", priority: int = 10,
           family: ProviderFamily = ProviderFamily.LOCAL_OPEN_SOURCE,
           cost: CostClass = CostClass.LOCAL_FREE_AI,
           capability: bool = True, pin: bool = True) -> ModelRoute:
    settings = {
        "temperature": 0.2,
        "dbd_tuned_binding_id": binding.binding_id,
        "dbd_tuned_binding_revision": binding.revision,
        "dbd_tuned_binding_sha256": binding.to_dict()["binding_sha256"],
    } if pin else {"temperature": 0.2}
    return ModelRoute(
        route_id=route_id,
        workload=AiWorkload.PLANNING,
        provider_family=family,
        provider_id="local-runtime" if family is not ProviderFamily.NON_AI_LIBRARY else "library",
        model_id="dbd-base:v1",
        cost_class=cost,
        priority=priority,
        reasoning_effort=ReasoningEffort.HIGH,
        capabilities=(ROUTE_CAPABILITY,) if capability else ("TEXT_GENERATION",),
        settings=settings,
    )


def _inputs(*, routes: tuple[ModelRoute, ...] | None = None) -> tuple[DbDTunedModelRegistry, AiConnectionProfile, ConnectionAvailability]:
    chain = _approved_chain()
    selected_routes = routes or (_route(chain[-1].binding),)
    return (
        DbDTunedModelRegistry(chain),
        AiConnectionProfile("dbd-profile", "1.0.0", SelectionMode.AUTO, selected_routes),
        ConnectionAvailability(frozenset(route.route_id for route in selected_routes)),
    )


def _resolve(registry: DbDTunedModelRegistry, profile: AiConnectionProfile, availability: ConnectionAvailability, **kwargs):
    return DbDReasoningRouteCapabilityResolver.resolve(
        registry, profile, availability, locale="ja-JP", **kwargs,
    )


def test_route_decision_is_deterministic_body_free_and_execution_blocked() -> None:
    registry, profile, availability = _inputs()
    decision = _resolve(registry, profile, availability)
    payload = decision.to_dict()
    assert payload == decision.to_dict()
    assert payload["execution_authority_state"] == EXECUTION_AUTHORITY_STATE
    assert payload["route_capability"] == ROUTE_CAPABILITY
    assert payload["binding_sha256"] == registry.records[-1].binding.to_dict()["binding_sha256"]
    assert payload["profile_sha256"] == profile.to_dict()["profile_sha256"]
    assert not ({"credential_ref", "endpoint_ref", "settings", "prompt", "output"} & set(payload))


def test_existing_ai_connection_resolver_priority_is_preserved() -> None:
    binding = _approved_chain()[-1].binding
    registry, profile, availability = _inputs(routes=(
        _route(binding, route_id="second", priority=20),
        _route(binding, route_id="first", priority=5),
    ))
    assert _resolve(registry, profile, availability).route_id == "first"


def test_missing_capability_and_unavailable_route_fail_closed() -> None:
    binding = _approved_chain()[-1].binding
    registry, profile, availability = _inputs(routes=(_route(binding, capability=False),))
    with pytest.raises(ProductError) as exc:
        _resolve(registry, profile, availability)
    assert exc.value.code == "ERR_PROVIDER_ROUTE_UNAVAILABLE"
    with pytest.raises(ProductError):
        _resolve(registry, profile, ConnectionAvailability(frozenset()))


@pytest.mark.parametrize("mutation", ["missing", "id", "revision", "digest"])
def test_missing_or_crossed_binding_pin_fails_closed(mutation: str) -> None:
    registry, profile, availability = _inputs()
    route = profile.routes[0]
    settings = dict(route.settings)
    if mutation == "missing":
        settings.pop("dbd_tuned_binding_sha256")
    elif mutation == "id":
        settings["dbd_tuned_binding_id"] = "other"
    elif mutation == "revision":
        settings["dbd_tuned_binding_revision"] = 2
    else:
        settings["dbd_tuned_binding_sha256"] = SHA_E
    crossed = replace(profile, routes=(replace(route, settings=settings),))
    with pytest.raises(ProductError) as exc:
        _resolve(registry, crossed, availability)
    assert exc.value.code == "ERR_DBD_TUNED_ROUTE_BINDING_PIN_MISMATCH"


def test_pin_mismatch_does_not_silently_fallback_to_later_route() -> None:
    binding = _approved_chain()[-1].binding
    wrong = replace(_route(binding, route_id="wrong", priority=1), settings={"dbd_tuned_binding_id": "other"})
    right = _route(binding, route_id="right", priority=2)
    registry, profile, availability = _inputs(routes=(wrong, right))
    with pytest.raises(ProductError, match="different tuned binding"):
        _resolve(registry, profile, availability)


def test_non_ai_library_cannot_claim_tuned_reasoning_capability() -> None:
    binding = _approved_chain()[-1].binding
    library = _route(
        binding, family=ProviderFamily.NON_AI_LIBRARY, cost=CostClass.NON_AI_FREE,
    )
    library = replace(library, reasoning_effort=ReasoningEffort.NONE)
    registry, profile, availability = _inputs(routes=(library,))
    with pytest.raises(ProductError) as exc:
        _resolve(registry, profile, availability)
    assert exc.value.code == "ERR_DBD_TUNED_ROUTE_NOT_AI"


def test_revoked_latest_and_ambiguous_approved_bindings_cannot_auto_resolve() -> None:
    rows = list(_approved_chain())
    suspended = _record(_binding(4, TunedModelBindingStatus.SUSPENDED), BindingLifecycleTransition.SUSPEND, rows[-1])
    revoked = _record(_binding(5, TunedModelBindingStatus.REVOKED), BindingLifecycleTransition.REVOKE, suspended)
    binding = rows[-1].binding
    profile = AiConnectionProfile("p", "1", SelectionMode.AUTO, (_route(binding),))
    availability = ConnectionAvailability(frozenset({"dbd-tuned"}))
    with pytest.raises(ProductError):
        _resolve(DbDTunedModelRegistry(tuple(rows + [suspended, revoked])), profile, availability)

    first = _approved_chain()
    second = list(_approved_chain(binding_id="dbd-ja-b", adapter="b"))
    second[-1] = replace(second[-1], decision_evidence_ref="human-confirmation://01ARZ3NDEKTSV4RRFFQ69G5FA9", decision_evidence_sha256=SHA_B)
    registry = DbDTunedModelRegistry(tuple(sorted(first + tuple(second), key=lambda item: (item.binding.binding_id, item.binding.revision))))
    with pytest.raises(ProductError, match="Multiple approved"):
        _resolve(registry, profile, availability)


def test_explicit_binding_selection_requires_exact_selected_pin() -> None:
    first = _approved_chain()
    second = list(_approved_chain(binding_id="dbd-ja-b", adapter="b"))
    second[-1] = replace(second[-1], decision_evidence_ref="human-confirmation://01ARZ3NDEKTSV4RRFFQ69G5FA9", decision_evidence_sha256=SHA_B)
    registry = DbDTunedModelRegistry(tuple(sorted(first + tuple(second), key=lambda item: (item.binding.binding_id, item.binding.revision))))
    route = _route(second[-1].binding)
    profile = AiConnectionProfile("p", "1", SelectionMode.AUTO, (route,))
    decision = _resolve(registry, profile, ConnectionAvailability(frozenset({route.route_id})), binding_id="dbd-ja-b")
    assert decision.binding_id == "dbd-ja-b"


def test_context_or_output_schema_drift_fails_before_route_decision() -> None:
    registry, profile, availability = _inputs()
    with pytest.raises(ProductError):
        _resolve(registry, profile, availability, context_schema="9.9.9")
    with pytest.raises(ProductError):
        _resolve(registry, profile, availability, output_schema="9.9.9")


def test_route_decision_schema_mirror_and_runtime_admission_are_exact() -> None:
    registry, profile, availability = _inputs()
    payload = _resolve(registry, profile, availability).to_dict()
    canonical = Path("schemas/dbd-reasoning-route-decision.schema.json").read_bytes()
    mirror = Path("src/ai_video_production/schema_resources/dbd-reasoning-route-decision.schema.json").read_bytes()
    assert canonical == mirror
    assert not list(Draft202012Validator(json.loads(canonical)).iter_errors(payload))
    assert admit_dbd_reasoning_route_decision(payload).to_dict() == payload


@pytest.mark.parametrize("mutation", ["version", "kind", "extra", "binding", "authority", "bool", "checksum"])
def test_unknown_crossed_or_rehashed_decision_is_rejected(mutation: str) -> None:
    registry, profile, availability = _inputs()
    payload = _resolve(registry, profile, availability).to_dict()
    if mutation == "version":
        payload["schema_version"] = "9.9.9"
    elif mutation == "kind":
        payload["record_kind"] = "OTHER"
    elif mutation == "extra":
        payload["extra"] = True
    elif mutation == "binding":
        payload["binding_revision"] = 99
    elif mutation == "authority":
        payload["execution_authority_state"] = "AUTHORIZED"
    elif mutation == "bool":
        payload["binding_revision"] = True
    else:
        payload["route_decision_sha256"] = SHA_E
    if mutation in {"binding", "authority", "bool"}:
        body = {key: value for key, value in payload.items() if key != "route_decision_sha256"}
        payload["route_decision_sha256"] = sha256_bytes(canonical_json_bytes(body))
    if mutation == "binding":
        forged = admit_dbd_reasoning_route_decision(payload)
        with pytest.raises(ProductError) as exc:
            DbDReasoningRouteCapabilityResolver.validate_current(
                forged, registry, profile, availability, locale="ja-JP",
            )
        assert exc.value.code == "ERR_DBD_TUNED_ROUTE_DECISION_STALE"
    else:
        with pytest.raises(ValueError):
            admit_dbd_reasoning_route_decision(payload)


def test_availability_shape_is_revalidated_at_use_time() -> None:
    registry, profile, availability = _inputs()
    object.__setattr__(availability, "available_route_ids", ["dbd-tuned"])
    with pytest.raises(ValueError, match="frozenset"):
        _resolve(registry, profile, availability)


@pytest.mark.parametrize("field,value", [
    ("route_id", "other-route"),
    ("provider_id", "other-provider"),
    ("model_id", "other-model"),
    ("profile_sha256", SHA_E),
])
def test_rehashed_decision_coordinate_crossing_fails_current_validation(field: str, value: str) -> None:
    registry, profile, availability = _inputs()
    decision = _resolve(registry, profile, availability)
    forged = replace(decision, **{field: value})
    with pytest.raises(ProductError) as exc:
        DbDReasoningRouteCapabilityResolver.validate_current(
            forged, registry, profile, availability, locale="ja-JP",
        )
    assert exc.value.code == "ERR_DBD_TUNED_ROUTE_DECISION_STALE"


def test_decision_cannot_survive_later_binding_revocation() -> None:
    registry, profile, availability = _inputs()
    decision = _resolve(registry, profile, availability)
    rows = list(registry.records)
    suspended = _record(_binding(4, TunedModelBindingStatus.SUSPENDED), BindingLifecycleTransition.SUSPEND, rows[-1])
    revoked = _record(_binding(5, TunedModelBindingStatus.REVOKED), BindingLifecycleTransition.REVOKE, suspended)
    with pytest.raises(ProductError):
        DbDReasoningRouteCapabilityResolver.validate_current(
            decision,
            DbDTunedModelRegistry(tuple(rows + [suspended, revoked])),
            profile,
            availability,
            locale="ja-JP",
        )


def test_r3b_module_has_no_effectful_runtime_surface() -> None:
    source = Path("src/ai_video_production/dbd_reasoning_routing.py").read_text(encoding="utf-8")
    for forbidden in (
        "sqlite3", "subprocess", "requests", "urllib", "CredentialStore",
        "ProviderAdapter", "execute(", "generate(", "Path(", "open(", "write_text", "write_bytes",
    ):
        assert forbidden not in source
