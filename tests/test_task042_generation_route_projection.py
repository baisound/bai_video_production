from __future__ import annotations

import json

from ai_video_production.ai_connections import (
    AiConnectionProfile, AiWorkload, ConnectionAvailability, CostClass, ModelRoute,
    ProviderFamily, SelectionMode,
)
from ai_video_production.capability_execution import ModelCapabilityCatalog, ModelCapabilityDescriptor
from ai_video_production.generation_route_projection import GenerationRouteProjectionService


CAP = "TEXT_TO_IMAGE"


def profile() -> AiConnectionProfile:
    return AiConnectionProfile(
        "profile-1", "v1", SelectionMode.AUTO,
        (
            ModelRoute(
                "cloud", AiWorkload.IMAGE, ProviderFamily.STABILITY_AI, "stability", "sd3",
                CostClass.CLOUD_PAID_AI, credential_ref="credential://stability/default",
                endpoint_ref="endpoint://stability", capabilities=(CAP,), settings={"quality": "high"},
            ),
            ModelRoute(
                "local", AiWorkload.IMAGE, ProviderFamily.COMFYUI, "comfyui", "flux",
                CostClass.LOCAL_FREE_AI, capabilities=(CAP,), priority=10,
            ),
        ),
    )


def catalog() -> ModelCapabilityCatalog:
    return ModelCapabilityCatalog((
        ModelCapabilityDescriptor(ProviderFamily.STABILITY_AI, "stability", "sd3", frozenset({CAP}), frozenset({AiWorkload.IMAGE})),
        ModelCapabilityDescriptor(ProviderFamily.COMFYUI, "comfyui", "flux", frozenset({CAP}), frozenset({AiWorkload.IMAGE})),
    ))


def test_projection_lists_every_route_deterministically_without_secrets_or_settings() -> None:
    result = GenerationRouteProjectionService.project(
        profile(), AiWorkload.IMAGE,
        ConnectionAvailability(frozenset({"cloud", "local"}), frozenset({"credential://stability/default"})),
        required_capabilities=(CAP,), catalog=catalog(),
        installed_adapter_capabilities={
            ProviderFamily.STABILITY_AI: frozenset({CAP}),
            ProviderFamily.COMFYUI: frozenset({CAP}),
        },
    )
    assert [row["route_id"] for row in result["routes"]] == ["local", "cloud"]
    assert all(row["ready"] for row in result["routes"])
    public = json.dumps(result)
    assert "credential://" not in public
    assert "endpoint://" not in public
    assert "quality" not in public
    assert result["provider_probe_performed"] is False
    assert result == GenerationRouteProjectionService.project(
        profile(), AiWorkload.IMAGE,
        ConnectionAvailability(frozenset({"cloud", "local"}), frozenset({"credential://stability/default"})),
        required_capabilities=(CAP,), catalog=catalog(),
        installed_adapter_capabilities={ProviderFamily.COMFYUI: frozenset({CAP}), ProviderFamily.STABILITY_AI: frozenset({CAP})},
    )


def test_credential_or_catalog_alone_never_overclaims_readiness() -> None:
    result = GenerationRouteProjectionService.project(
        profile(), AiWorkload.IMAGE,
        ConnectionAvailability(frozenset({"cloud", "local"}), frozenset({"credential://stability/default"})),
        required_capabilities=(CAP,), catalog=catalog(), installed_adapter_capabilities={},
    )
    assert all(not row["ready"] for row in result["routes"])
    assert all("ADAPTER_CAPABILITY_MISSING" in row["blockers"] for row in result["routes"])

    without_catalog = GenerationRouteProjectionService.project(
        profile(), AiWorkload.IMAGE,
        ConnectionAvailability(frozenset({"cloud", "local"}), frozenset({"credential://stability/default"})),
        required_capabilities=(CAP,), catalog=None,
        installed_adapter_capabilities={ProviderFamily.COMFYUI: frozenset({CAP}), ProviderFamily.STABILITY_AI: frozenset({CAP})},
    )
    assert all("MODEL_CATALOG_UNAVAILABLE" in row["blockers"] for row in without_catalog["routes"])


def test_missing_route_and_credential_have_separate_blockers() -> None:
    result = GenerationRouteProjectionService.project(
        profile(), AiWorkload.IMAGE, ConnectionAvailability(frozenset()),
        required_capabilities=(CAP,), catalog=catalog(),
        installed_adapter_capabilities={ProviderFamily.COMFYUI: frozenset({CAP}), ProviderFamily.STABILITY_AI: frozenset({CAP})},
    )
    by_id = {row["route_id"]: row for row in result["routes"]}
    assert "ROUTE_UNAVAILABLE" in by_id["local"]["blockers"]
    assert "CREDENTIAL_MISSING" not in by_id["local"]["blockers"]
    assert {"ROUTE_UNAVAILABLE", "CREDENTIAL_MISSING"}.issubset(by_id["cloud"]["blockers"])
