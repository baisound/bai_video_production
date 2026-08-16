from __future__ import annotations

from dataclasses import replace

import pytest

from ai_video_production.ai_connections import (
    AiConnectionProfile,
    AiWorkload,
    ConnectionAvailability,
    CostClass,
    ModelRoute,
    ProviderFamily,
    SelectionMode,
)
from ai_video_production.creative_generation import CreativeGenerationMode
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.sfx_generation_routing import (
    SfxAssetReference,
    SfxBindingState,
    SfxCreativeGenerationIntentReference,
    SfxEvidenceBinding,
    SfxRightsEvidenceReference,
    SfxRouteAdmissionEvidence,
    SfxRouteDisposition,
    SfxRoutingCompiler,
    SfxRoutingRequest,
    SfxRoutingState,
)


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64


def bound(suffix: str = "default") -> SfxEvidenceBinding:
    return SfxEvidenceBinding(
        SfxBindingState.BOUND_VERIFIED,
        f"evidence://task013/sfx/{suffix}",
        SHA_A,
    )


def route(
    route_id: str,
    *,
    priority: int = 100,
    cost: CostClass = CostClass.LOCAL_FREE_AI,
    enabled: bool = True,
    capabilities: tuple[str, ...] = ("SFX",),
    credential_ref: str | None = None,
) -> ModelRoute:
    family = (
        ProviderFamily.LOCAL_OPEN_SOURCE
        if cost in {CostClass.LOCAL_FREE_AI, CostClass.LOCAL_LICENSED_AI}
        else ProviderFamily.ELEVENLABS
    )
    return ModelRoute(
        route_id,
        AiWorkload.AUDIO,
        family,
        "sfx-provider",
        "sfx-model",
        cost,
        priority=priority,
        credential_ref=credential_ref,
        capabilities=capabilities,
        enabled=enabled,
    )


def profile(
    *routes: ModelRoute,
    mode: SelectionMode = SelectionMode.AUTO,
) -> AiConnectionProfile:
    return AiConnectionProfile("profile", "8", mode, tuple(routes))


def intent(
    active: AiConnectionProfile,
    binding: SfxEvidenceBinding | None = None,
) -> SfxCreativeGenerationIntentReference:
    return SfxCreativeGenerationIntentReference(
        "request-sfx-1",
        "project-1",
        "scene-1",
        "slot:scene-1:sfx",
        "prompt-sfx-1",
        2,
        SHA_A,
        SHA_B,
        active.profile_id,
        active.profile_version,
        active.to_dict()["profile_sha256"],
        binding or bound("intent"),
    )


def admission(
    route_id: str,
    *,
    capability: SfxBindingState = SfxBindingState.BOUND_VERIFIED,
    license: SfxBindingState = SfxBindingState.BOUND_VERIFIED,
    resource: SfxBindingState = SfxBindingState.BOUND_VERIFIED,
) -> SfxRouteAdmissionEvidence:
    def evidence(state: SfxBindingState, name: str) -> SfxEvidenceBinding:
        if state is SfxBindingState.CANONICAL_REF_NOT_PROVIDED:
            return SfxEvidenceBinding(state)
        return SfxEvidenceBinding(
            state,
            f"evidence://task013/sfx/{route_id}/{name}",
            SHA_C,
        )

    return SfxRouteAdmissionEvidence(
        route_id,
        evidence(capability, "capability"),
        evidence(license, "license"),
        evidence(resource, "resource"),
    )


def request(
    active: AiConnectionProfile,
    *evidence: SfxRouteAdmissionEvidence,
    intent_binding: SfxEvidenceBinding | None = None,
    rights_binding: SfxEvidenceBinding | None = None,
    assets: tuple[SfxAssetReference, ...] = (),
) -> SfxRoutingRequest:
    return SfxRoutingRequest(
        "compile-sfx-1",
        intent(active, intent_binding),
        SfxRightsEvidenceReference(
            "rights://project-1/sfx",
            rights_binding or bound("rights"),
        ),
        tuple(evidence),
        assets,
    )


def test_selects_highest_priority_verified_route_and_records_ordered_reasons() -> None:
    active = profile(route("later", priority=20), route("first", priority=10))
    plan = SfxRoutingCompiler.compile(
        request(active, admission("later"), admission("first")),
        profile=active,
        availability=ConnectionAvailability(frozenset({"first", "later"})),
    )
    assert plan.routing_state is SfxRoutingState.ROUTE_SELECTED
    assert plan.selected_route_id == "first"
    assert [item.route_id for item in plan.route_decisions] == ["first", "later"]
    assert plan.route_decisions[0].disposition is SfxRouteDisposition.SELECTED
    assert plan.route_decisions[0].reason_codes == (
        "SELECTED_HIGHEST_PRIORITY_ELIGIBLE_ROUTE",
    )
    assert plan.route_decisions[1].reason_codes == ("NOT_SELECTED_LOWER_PRIORITY",)


def test_plan_is_canonical_deterministic_body_free_and_non_executing() -> None:
    active = profile(route("local"))
    first = SfxAssetReference("asset-ref-1", SHA_B, SHA_C, bound("asset-1"))
    second = SfxAssetReference("asset-ref-2", SHA_C, SHA_B, bound("asset-2"))
    one = SfxRoutingCompiler.compile(
        request(active, admission("local"), assets=(second, first)),
        profile=active,
        availability=ConnectionAvailability(frozenset({"local"})),
    )
    two = SfxRoutingCompiler.compile(
        request(active, admission("local"), assets=(first, second)),
        profile=active,
        availability=ConnectionAvailability(frozenset({"local"})),
    )
    document = one.to_dict()
    digest = document.pop("plan_sha256")
    assert digest == sha256_bytes(canonical_json_bytes(document))
    assert one.to_dict() == two.to_dict()
    assert document["intent"]["prompt"]["body_embedded"] is False
    assert all(item["body_embedded"] is False for item in document["input_assets"])
    for field in (
        "provider_execution_admitted",
        "provider_execution_started",
        "sfx_generation_started",
        "h3_foley_started",
        "asset_publication_started",
        "placement_started",
    ):
        assert document[field] is False
    assert "credential://" not in str(document)


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (SfxBindingState.UNKNOWN, SfxRoutingState.UNKNOWN),
        (SfxBindingState.CANONICAL_REF_NOT_PROVIDED, SfxRoutingState.UNKNOWN),
        (SfxBindingState.MISMATCH, SfxRoutingState.BLOCKED),
    ],
)
def test_global_rights_state_fails_closed_without_route_selection(
    state: SfxBindingState,
    expected: SfxRoutingState,
) -> None:
    active = profile(route("local"))
    rights = (
        SfxEvidenceBinding(state)
        if state is SfxBindingState.CANONICAL_REF_NOT_PROVIDED
        else SfxEvidenceBinding(state, "evidence://task013/sfx/rights", SHA_A)
    )
    plan = SfxRoutingCompiler.compile(
        request(active, admission("local"), rights_binding=rights),
        profile=active,
        availability=ConnectionAvailability(frozenset({"local"})),
    )
    assert plan.routing_state is expected
    assert plan.selected_route_id is None
    assert plan.route_decisions[0].reason_codes[0] == "GLOBAL_BINDING_NOT_ADMITTED"


def test_unknown_asset_binding_is_not_silently_admitted() -> None:
    active = profile(route("local"))
    asset = SfxAssetReference(
        "asset-ref-1",
        SHA_B,
        SHA_C,
        SfxEvidenceBinding(SfxBindingState.UNKNOWN),
    )
    plan = SfxRoutingCompiler.compile(
        request(active, admission("local"), assets=(asset,)),
        profile=active,
        availability=ConnectionAvailability(frozenset({"local"})),
    )
    assert plan.routing_state is SfxRoutingState.UNKNOWN
    assert plan.global_reason_codes == ("ASSET:asset-ref-1_UNKNOWN",)


@pytest.mark.parametrize("field", ["capability", "license", "resource"])
def test_unknown_route_evidence_is_unknown_not_zero_or_pass(field: str) -> None:
    active = profile(route("local"))
    values = {
        "capability": SfxBindingState.BOUND_VERIFIED,
        "license": SfxBindingState.BOUND_VERIFIED,
        "resource": SfxBindingState.BOUND_VERIFIED,
    }
    values[field] = SfxBindingState.UNKNOWN
    plan = SfxRoutingCompiler.compile(
        request(active, admission("local", **values)),
        profile=active,
        availability=ConnectionAvailability(frozenset({"local"})),
    )
    assert plan.routing_state is SfxRoutingState.UNKNOWN
    assert plan.selected_route_id is None
    assert f"{field.upper()}_UNKNOWN" in plan.route_decisions[0].reason_codes


def test_missing_route_evidence_remains_unknown() -> None:
    active = profile(route("local"))
    plan = SfxRoutingCompiler.compile(
        request(active),
        profile=active,
        availability=ConnectionAvailability(frozenset({"local"})),
    )
    assert plan.routing_state is SfxRoutingState.UNKNOWN
    assert plan.route_decisions[0].reason_codes == (
        "ROUTE_ADMISSION_EVIDENCE_NOT_PROVIDED",
    )


def test_route_exclusions_are_complete_and_stably_ordered() -> None:
    paid = route(
        "cloud",
        cost=CostClass.CLOUD_PAID_AI,
        enabled=False,
        capabilities=("OTHER",),
        credential_ref="credential://sfx/cloud",
    )
    active = profile(paid, mode=SelectionMode.FREE)
    plan = SfxRoutingCompiler.compile(
        request(active, admission("cloud")),
        profile=active,
        availability=ConnectionAvailability(frozenset()),
    )
    assert plan.routing_state is SfxRoutingState.BLOCKED
    assert plan.route_decisions[0].reason_codes == (
        "ROUTE_DISABLED",
        "ROUTE_UNAVAILABLE",
        "CREDENTIAL_UNAVAILABLE",
        "CAPABILITY_NOT_CONFIGURED",
        "SELECTION_MODE_EXCLUDED",
    )


def test_disabled_audio_workload_is_blocked() -> None:
    active = profile(route("local"), mode=SelectionMode.DISABLED)
    plan = SfxRoutingCompiler.compile(
        request(active, admission("local")),
        profile=active,
        availability=ConnectionAvailability(frozenset({"local"})),
    )
    assert plan.routing_state is SfxRoutingState.BLOCKED
    assert plan.global_reason_codes == ("AUDIO_WORKLOAD_DISABLED",)
    assert plan.selected_route_id is None


def test_no_audio_route_is_blocked_with_explicit_reason() -> None:
    music = ModelRoute(
        "music",
        AiWorkload.MUSIC,
        ProviderFamily.LOCAL_OPEN_SOURCE,
        "provider",
        "model",
        CostClass.LOCAL_FREE_AI,
        capabilities=("MUSIC_GENERATION",),
    )
    active = profile(music)
    plan = SfxRoutingCompiler.compile(
        request(active),
        profile=active,
        availability=ConnectionAvailability(frozenset({"music"})),
    )
    assert plan.routing_state is SfxRoutingState.BLOCKED
    assert plan.global_reason_codes == ("NO_AUDIO_SFX_ROUTES_CONFIGURED",)
    assert plan.route_decisions == ()


def test_exact_profile_binding_mismatch_is_rejected() -> None:
    active = profile(route("local"))
    bad_intent = replace(intent(active), provider_profile_sha256=SHA_C)
    value = SfxRoutingRequest(
        "compile-sfx-1",
        bad_intent,
        SfxRightsEvidenceReference("rights://project-1/sfx", bound("rights")),
        (admission("local"),),
    )
    with pytest.raises(ValueError, match="provider profile"):
        SfxRoutingCompiler.compile(
            value,
            profile=active,
            availability=ConnectionAvailability(frozenset({"local"})),
        )


def test_non_sfx_intent_and_duplicate_coordinates_are_rejected() -> None:
    active = profile(route("local"))
    with pytest.raises(ValueError, match="only SFX"):
        replace(intent(active), mode=CreativeGenerationMode.MUSIC_GENERATION)
    asset = SfxAssetReference("asset-ref-1", SHA_B, SHA_C, bound("asset"))
    with pytest.raises(ValueError, match="asset IDs"):
        request(active, admission("local"), assets=(asset, asset))
    with pytest.raises(ValueError, match="route admission"):
        request(active, admission("local"), admission("local"))


def test_bound_evidence_requires_real_reference_and_digest() -> None:
    with pytest.raises(ValueError, match="requires exact Evidence"):
        SfxEvidenceBinding(SfxBindingState.BOUND_VERIFIED)
    with pytest.raises(ValueError, match="must not contain invented"):
        SfxEvidenceBinding(
            SfxBindingState.CANONICAL_REF_NOT_PROVIDED,
            "evidence://fake",
            SHA_A,
        )
    with pytest.raises(ValueError, match="evidence://"):
        SfxEvidenceBinding(
            SfxBindingState.UNKNOWN,
            "https://secret.example/token",
            SHA_A,
        )


def test_required_capability_is_non_empty_and_safe() -> None:
    active = profile(route("local"))
    value = request(active, admission("local"))
    availability = ConnectionAvailability(frozenset({"local"}))
    with pytest.raises(ValueError, match="non-empty"):
        SfxRoutingCompiler.compile(
            value,
            profile=active,
            availability=availability,
            required_capabilities=(),
        )
    with pytest.raises(ValueError, match="safe identifiers"):
        SfxRoutingCompiler.compile(
            value,
            profile=active,
            availability=availability,
            required_capabilities=("SFX secret",),
        )
