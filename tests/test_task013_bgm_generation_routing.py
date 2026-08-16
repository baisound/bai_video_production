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
from ai_video_production.bgm_generation_routing import (
    BgmAssetReference,
    BgmRightsEvidenceReference,
    BgmRouteAdmissionEvidence,
    BgmRouteDisposition,
    BgmRoutingCompiler,
    BgmRoutingRequest,
    BgmRoutingState,
    BindingState,
    CreativeGenerationIntentReference,
    EvidenceBinding,
)
from ai_video_production.creative_generation import CreativeGenerationMode
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64


def bound(suffix: str = "default") -> EvidenceBinding:
    return EvidenceBinding(BindingState.BOUND_VERIFIED, f"evidence://task013/{suffix}", SHA_A)


def route(
    route_id: str,
    *,
    priority: int = 100,
    cost: CostClass = CostClass.LOCAL_FREE_AI,
    enabled: bool = True,
    capabilities: tuple[str, ...] = ("MUSIC_GENERATION",),
    credential_ref: str | None = None,
) -> ModelRoute:
    family = ProviderFamily.LOCAL_OPEN_SOURCE if cost in {CostClass.LOCAL_FREE_AI, CostClass.LOCAL_LICENSED_AI} else ProviderFamily.ELEVENLABS
    return ModelRoute(
        route_id,
        AiWorkload.MUSIC,
        family,
        "music-provider",
        "music-model",
        cost,
        priority=priority,
        credential_ref=credential_ref,
        capabilities=capabilities,
        enabled=enabled,
    )


def profile(*routes: ModelRoute, mode: SelectionMode = SelectionMode.AUTO) -> AiConnectionProfile:
    return AiConnectionProfile("profile", "7", mode, tuple(routes))


def intent(active: AiConnectionProfile, binding: EvidenceBinding | None = None) -> CreativeGenerationIntentReference:
    return CreativeGenerationIntentReference(
        "request-bgm-1",
        "project-1",
        "scene-1",
        "slot:scene-1:bgm",
        "prompt-bgm-1",
        3,
        SHA_A,
        SHA_B,
        active.profile_id,
        active.profile_version,
        active.to_dict()["profile_sha256"],
        binding or bound("intent"),
    )


def admission(route_id: str, *, capability: BindingState = BindingState.BOUND_VERIFIED, license: BindingState = BindingState.BOUND_VERIFIED, resource: BindingState = BindingState.BOUND_VERIFIED) -> BgmRouteAdmissionEvidence:
    def evidence(state: BindingState, name: str) -> EvidenceBinding:
        if state is BindingState.CANONICAL_REF_NOT_PROVIDED:
            return EvidenceBinding(state)
        return EvidenceBinding(state, f"evidence://task013/{route_id}/{name}", SHA_C)

    return BgmRouteAdmissionEvidence(
        route_id,
        evidence(capability, "capability"),
        evidence(license, "license"),
        evidence(resource, "resource"),
    )


def request(active: AiConnectionProfile, *evidence: BgmRouteAdmissionEvidence, intent_binding: EvidenceBinding | None = None, rights_binding: EvidenceBinding | None = None, assets: tuple[BgmAssetReference, ...] = ()) -> BgmRoutingRequest:
    return BgmRoutingRequest(
        "compile-bgm-1",
        intent(active, intent_binding),
        BgmRightsEvidenceReference("rights://project-1/bgm", rights_binding or bound("rights")),
        tuple(evidence),
        assets,
    )


def test_selects_highest_priority_verified_route_and_records_ordered_reasons() -> None:
    active = profile(route("later", priority=20), route("first", priority=10))
    plan = BgmRoutingCompiler.compile(
        request(active, admission("later"), admission("first")),
        profile=active,
        availability=ConnectionAvailability(frozenset({"first", "later"})),
    )
    assert plan.routing_state is BgmRoutingState.ROUTE_SELECTED
    assert plan.selected_route_id == "first"
    assert [item.route_id for item in plan.route_decisions] == ["first", "later"]
    assert plan.route_decisions[0].disposition is BgmRouteDisposition.SELECTED
    assert plan.route_decisions[0].reason_codes == ("SELECTED_HIGHEST_PRIORITY_ELIGIBLE_ROUTE",)
    assert plan.route_decisions[1].reason_codes == ("NOT_SELECTED_LOWER_PRIORITY",)


def test_plan_is_canonical_deterministic_body_free_and_non_executing() -> None:
    active = profile(route("local"))
    asset = BgmAssetReference("asset-ref-1", SHA_B, SHA_C, bound("asset"))
    plan = BgmRoutingCompiler.compile(
        request(active, admission("local"), assets=(asset,)),
        profile=active,
        availability=ConnectionAvailability(frozenset({"local"})),
    )
    document = plan.to_dict()
    digest = document.pop("plan_sha256")
    assert digest == sha256_bytes(canonical_json_bytes(document))
    assert document == {key: value for key, value in plan.to_dict().items() if key != "plan_sha256"}
    assert document["intent"]["prompt"]["body_embedded"] is False
    assert document["input_assets"][0]["body_embedded"] is False
    assert document["provider_execution_admitted"] is False
    assert document["provider_execution_started"] is False
    assert document["bgm_generation_started"] is False
    assert document["asset_publication_started"] is False
    assert "credential://" not in str(document)


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (BindingState.UNKNOWN, BgmRoutingState.UNKNOWN),
        (BindingState.CANONICAL_REF_NOT_PROVIDED, BgmRoutingState.UNKNOWN),
        (BindingState.MISMATCH, BgmRoutingState.BLOCKED),
    ],
)
def test_global_rights_state_fails_closed_without_route_selection(state: BindingState, expected: BgmRoutingState) -> None:
    active = profile(route("local"))
    rights = EvidenceBinding(state) if state is BindingState.CANONICAL_REF_NOT_PROVIDED else EvidenceBinding(state, "evidence://task013/rights", SHA_A)
    plan = BgmRoutingCompiler.compile(
        request(active, admission("local"), rights_binding=rights),
        profile=active,
        availability=ConnectionAvailability(frozenset({"local"})),
    )
    assert plan.routing_state is expected
    assert plan.selected_route_id is None
    assert plan.route_decisions[0].reason_codes[0] == "GLOBAL_BINDING_NOT_ADMITTED"


def test_unknown_asset_binding_is_not_silently_admitted() -> None:
    active = profile(route("local"))
    asset = BgmAssetReference("asset-ref-1", SHA_B, SHA_C, EvidenceBinding(BindingState.UNKNOWN))
    plan = BgmRoutingCompiler.compile(
        request(active, admission("local"), assets=(asset,)),
        profile=active,
        availability=ConnectionAvailability(frozenset({"local"})),
    )
    assert plan.routing_state is BgmRoutingState.UNKNOWN
    assert plan.global_reason_codes == ("ASSET:asset-ref-1_UNKNOWN",)


@pytest.mark.parametrize("field", ["capability", "license", "resource"])
def test_unknown_route_evidence_is_unknown_not_zero_or_pass(field: str) -> None:
    active = profile(route("local"))
    values = {"capability": BindingState.BOUND_VERIFIED, "license": BindingState.BOUND_VERIFIED, "resource": BindingState.BOUND_VERIFIED}
    values[field] = BindingState.UNKNOWN
    plan = BgmRoutingCompiler.compile(
        request(active, admission("local", **values)),
        profile=active,
        availability=ConnectionAvailability(frozenset({"local"})),
    )
    assert plan.routing_state is BgmRoutingState.UNKNOWN
    assert plan.selected_route_id is None
    assert f"{field.upper()}_UNKNOWN" in plan.route_decisions[0].reason_codes


def test_missing_route_evidence_remains_unknown() -> None:
    active = profile(route("local"))
    plan = BgmRoutingCompiler.compile(
        request(active),
        profile=active,
        availability=ConnectionAvailability(frozenset({"local"})),
    )
    assert plan.routing_state is BgmRoutingState.UNKNOWN
    assert plan.route_decisions[0].reason_codes == ("ROUTE_ADMISSION_EVIDENCE_NOT_PROVIDED",)


def test_route_exclusions_are_complete_and_stably_ordered() -> None:
    paid = route(
        "cloud",
        cost=CostClass.CLOUD_PAID_AI,
        enabled=False,
        capabilities=("OTHER",),
        credential_ref="credential://music/cloud",
    )
    active = profile(paid, mode=SelectionMode.FREE)
    plan = BgmRoutingCompiler.compile(
        request(active, admission("cloud")),
        profile=active,
        availability=ConnectionAvailability(frozenset()),
    )
    assert plan.routing_state is BgmRoutingState.BLOCKED
    assert plan.route_decisions[0].reason_codes == (
        "ROUTE_DISABLED",
        "ROUTE_UNAVAILABLE",
        "CREDENTIAL_UNAVAILABLE",
        "CAPABILITY_NOT_CONFIGURED",
        "SELECTION_MODE_EXCLUDED",
    )


def test_disabled_music_workload_is_blocked() -> None:
    active = profile(route("local"), mode=SelectionMode.DISABLED)
    plan = BgmRoutingCompiler.compile(
        request(active, admission("local")),
        profile=active,
        availability=ConnectionAvailability(frozenset({"local"})),
    )
    assert plan.routing_state is BgmRoutingState.BLOCKED
    assert plan.global_reason_codes == ("MUSIC_WORKLOAD_DISABLED",)
    assert plan.selected_route_id is None


def test_no_music_route_is_blocked_with_explicit_reason() -> None:
    non_music = ModelRoute(
        "image", AiWorkload.IMAGE, ProviderFamily.COMFYUI, "provider", "model",
        CostClass.LOCAL_FREE_AI, capabilities=("TEXT_TO_IMAGE",),
    )
    active = profile(non_music)
    plan = BgmRoutingCompiler.compile(
        request(active),
        profile=active,
        availability=ConnectionAvailability(frozenset({"image"})),
    )
    assert plan.routing_state is BgmRoutingState.BLOCKED
    assert plan.global_reason_codes == ("NO_MUSIC_ROUTES_CONFIGURED",)
    assert plan.route_decisions == ()


def test_exact_profile_binding_mismatch_is_rejected() -> None:
    active = profile(route("local"))
    bad_intent = replace(intent(active), provider_profile_sha256=SHA_C)
    value = BgmRoutingRequest(
        "compile-bgm-1",
        bad_intent,
        BgmRightsEvidenceReference("rights://project-1/bgm", bound("rights")),
        (admission("local"),),
    )
    with pytest.raises(ValueError, match="provider profile"):
        BgmRoutingCompiler.compile(
            value,
            profile=active,
            availability=ConnectionAvailability(frozenset({"local"})),
        )


def test_non_music_intent_and_duplicate_coordinates_are_rejected() -> None:
    active = profile(route("local"))
    with pytest.raises(ValueError, match="MUSIC_GENERATION"):
        replace(intent(active), mode=CreativeGenerationMode.SFX)
    asset = BgmAssetReference("asset-ref-1", SHA_B, SHA_C, bound("asset"))
    with pytest.raises(ValueError, match="asset IDs"):
        request(active, admission("local"), assets=(asset, asset))
    with pytest.raises(ValueError, match="route admission"):
        request(active, admission("local"), admission("local"))


def test_bound_evidence_requires_real_reference_and_digest() -> None:
    with pytest.raises(ValueError, match="requires exact Evidence"):
        EvidenceBinding(BindingState.BOUND_VERIFIED)
    with pytest.raises(ValueError, match="must not contain invented"):
        EvidenceBinding(BindingState.CANONICAL_REF_NOT_PROVIDED, "evidence://fake", SHA_A)
    with pytest.raises(ValueError, match="evidence://"):
        EvidenceBinding(BindingState.UNKNOWN, "https://secret.example/token", SHA_A)
