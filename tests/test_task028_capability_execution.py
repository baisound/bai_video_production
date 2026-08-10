import pytest

from ai_video_production import (
    AiConnectionProfile, AiWorkload, CapabilityExecutionRegistry,
    CapabilityExecutionRequest, CapabilityExecutionResult, ConnectionAvailability,
    CostClass, ModelCapabilityCatalog, ModelCapabilityDescriptor, ModelRoute,
    ProductError, ProviderFamily, SelectionMode, TextCapabilityAdapter,
)


class Credentials:
    def resolve(self, ref): return "secret"


class Adapter:
    def __init__(self, family, capabilities): self.provider_family, self.capabilities, self.calls = family, frozenset(capabilities), []
    def execute(self, route, request, credential):
        self.calls.append((route, request, credential))
        return CapabilityExecutionResult(route.route_id, route.provider_family, route.provider_id, route.model_id, request.workload, request.capability, "ASSET_JOB", {"accepted":True}, "job-1")


def route(route_id, workload, family, model, capability, priority=10):
    return ModelRoute(route_id, workload, family, family.value.lower(), model, CostClass.CLOUD_PAID_AI, priority=priority, credential_ref=f"credential://{family.value.lower()}/default", capabilities=(capability,))


@pytest.mark.parametrize("workload,capability", [
    (AiWorkload.IMAGE, "TEXT_TO_IMAGE"),
    (AiWorkload.VIDEO, "TEXT_TO_VIDEO"),
    (AiWorkload.AUDIO, "TTS"),
    (AiWorkload.MUSIC, "MUSIC_GENERATION"),
])
def test_same_openai_provider_can_execute_each_model_declared_workload(workload, capability):
    configured = route("r", workload, ProviderFamily.OPENAI, f"model-{workload.value.lower()}", capability)
    profile = AiConnectionProfile("p", "1", SelectionMode.AI, (configured,))
    adapter = Adapter(ProviderFamily.OPENAI, (capability,))
    registry = CapabilityExecutionRegistry((adapter,), Credentials())
    available = ConnectionAvailability(frozenset({"r"}), frozenset({configured.credential_ref}))
    result = registry.execute(profile, available, CapabilityExecutionRequest(workload, capability, {"prompt":"create"}))
    assert result.workload is workload and result.capability == capability and adapter.calls[0][2] == "secret"


def test_google_and_anthropic_are_not_workload_locked():
    for family in (ProviderFamily.GOOGLE, ProviderFamily.ANTHROPIC):
        configured = route("r", AiWorkload.IMAGE, family, "configured-image-model", "TEXT_TO_IMAGE")
        profile = AiConnectionProfile("p", "1", SelectionMode.AI, (configured,))
        registry = CapabilityExecutionRegistry((Adapter(family, ("TEXT_TO_IMAGE",)),), Credentials())
        result = registry.execute(profile, ConnectionAvailability(frozenset({"r"}), frozenset({configured.credential_ref})), CapabilityExecutionRequest(AiWorkload.IMAGE, "TEXT_TO_IMAGE", {"prompt":"x"}))
        assert result.provider_family is family


def test_model_catalog_not_provider_family_determines_support():
    descriptor = ModelCapabilityDescriptor(ProviderFamily.GOOGLE, "google", "video-model", frozenset({"TEXT_TO_VIDEO"}), frozenset({AiWorkload.VIDEO}))
    catalog = ModelCapabilityCatalog((descriptor,))
    good = route("good", AiWorkload.VIDEO, ProviderFamily.GOOGLE, "video-model", "TEXT_TO_VIDEO")
    catalog.assert_route_supported(good, "TEXT_TO_VIDEO")
    bad = route("bad", AiWorkload.IMAGE, ProviderFamily.GOOGLE, "video-model", "TEXT_TO_IMAGE")
    with pytest.raises(ProductError) as exc: catalog.assert_route_supported(bad, "TEXT_TO_IMAGE")
    assert exc.value.code == "ERR_PROVIDER_MODEL_CAPABILITY_UNSUPPORTED"


def test_uncataloged_model_fails_closed_when_catalog_is_enabled():
    configured = route("r", AiWorkload.VIDEO, ProviderFamily.OTHER, "unknown", "TEXT_TO_VIDEO")
    profile = AiConnectionProfile("p", "1", SelectionMode.AI, (configured,))
    registry = CapabilityExecutionRegistry((Adapter(ProviderFamily.OTHER, ("TEXT_TO_VIDEO",)),), Credentials(), catalog=ModelCapabilityCatalog(()))
    with pytest.raises(ProductError) as exc:
        registry.execute(profile, ConnectionAvailability(frozenset({"r"}), frozenset({configured.credential_ref})), CapabilityExecutionRequest(AiWorkload.VIDEO, "TEXT_TO_VIDEO", {"prompt":"x"}))
    assert exc.value.code == "ERR_PROVIDER_MODEL_NOT_CATALOGED"


def test_missing_capability_adapter_fails_closed():
    configured = route("r", AiWorkload.MUSIC, ProviderFamily.OPENAI, "music-model", "MUSIC_GENERATION")
    profile = AiConnectionProfile("p", "1", SelectionMode.AI, (configured,))
    with pytest.raises(ProductError) as exc:
        CapabilityExecutionRegistry((), Credentials()).execute(profile, ConnectionAvailability(frozenset({"r"}), frozenset({configured.credential_ref})), CapabilityExecutionRequest(AiWorkload.MUSIC, "MUSIC_GENERATION", {"prompt":"x"}))
    assert exc.value.code == "ERR_PROVIDER_CAPABILITY_ADAPTER_MISSING"


def test_duplicate_family_capability_binding_is_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        CapabilityExecutionRegistry((Adapter(ProviderFamily.OPENAI, ("TTS",)), Adapter(ProviderFamily.OPENAI, ("TTS",))), Credentials())


def test_payload_rejects_embedded_secrets_recursively():
    with pytest.raises(ValueError, match="secret-bearing"):
        CapabilityExecutionRequest(AiWorkload.IMAGE, "TEXT_TO_IMAGE", {"options":{"api_key":"secret"}})


def test_result_mismatch_is_rejected_as_integrity_error():
    class Bad(Adapter):
        def execute(self, route, request, credential):
            return CapabilityExecutionResult("wrong", route.provider_family, route.provider_id, route.model_id, request.workload, request.capability, "ASSET_JOB", {})
    configured = route("r", AiWorkload.VIDEO, ProviderFamily.LUMA, "m", "TEXT_TO_VIDEO")
    profile = AiConnectionProfile("p", "1", SelectionMode.AI, (configured,))
    with pytest.raises(ProductError) as exc:
        CapabilityExecutionRegistry((Bad(ProviderFamily.LUMA, ("TEXT_TO_VIDEO",)),), Credentials()).execute(profile, ConnectionAvailability(frozenset({"r"}), frozenset({configured.credential_ref})), CapabilityExecutionRequest(AiWorkload.VIDEO, "TEXT_TO_VIDEO", {"prompt":"x"}))
    assert exc.value.code == "ERR_PROVIDER_CAPABILITY_RESULT_MISMATCH"


def test_installed_capabilities_are_reported_per_provider():
    registry = CapabilityExecutionRegistry((Adapter(ProviderFamily.GOOGLE, ("TEXT_TO_IMAGE", "TEXT_TO_VIDEO")),), Credentials())
    assert registry.installed_capabilities(ProviderFamily.GOOGLE) == frozenset({"TEXT_TO_IMAGE", "TEXT_TO_VIDEO"})
