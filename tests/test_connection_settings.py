from ai_video_production import (
    AiConnectionProfile, AiConnectionSettingsService, AiWorkload, ConnectionAvailability,
    CostClass, ModelRoute, ProviderFamily, ReasoningEffort, SelectionMode, SettingsRouteStatus,
)


def profile() -> AiConnectionProfile:
    return AiConnectionProfile(
        "creator-ui", "1.0.0", SelectionMode.AUTO,
        (
            ModelRoute("plan", AiWorkload.PLANNING, ProviderFamily.OPENAI, "openai", "gpt-demo", CostClass.CLOUD_PAID_AI, reasoning_effort=ReasoningEffort.MEDIUM, credential_ref="credential://openai/default"),
            ModelRoute("image", AiWorkload.IMAGE, ProviderFamily.COMFYUI, "comfyui", "flux-local", CostClass.LOCAL_FREE_AI),
        ),
        {AiWorkload.VIDEO: SelectionMode.DISABLED, AiWorkload.AUDIO: SelectionMode.DISABLED, AiWorkload.MUSIC: SelectionMode.DISABLED},
    )


def test_preflight_projects_all_workloads_without_provider_execution() -> None:
    report = AiConnectionSettingsService.preflight(
        profile(), ConnectionAvailability(frozenset({"plan", "image"}), frozenset({"credential://openai/default"}))
    )
    assert len(report.workloads) == 5
    assert report.ready
    planning = next(item for item in report.workloads if item.workload is AiWorkload.PLANNING)
    assert planning.status is SettingsRouteStatus.READY
    assert planning.model_id == "gpt-demo"
    assert planning.credential_required and planning.credential_configured


def test_preflight_blocks_missing_credential_without_exposing_reference() -> None:
    report = AiConnectionSettingsService.preflight(profile(), ConnectionAvailability(frozenset({"plan", "image"})))
    planning = next(item for item in report.workloads if item.workload is AiWorkload.PLANNING)
    assert planning.status is SettingsRouteStatus.BLOCKED
    assert planning.error_code == "ERR_PROVIDER_ROUTE_UNAVAILABLE"
    document = report.to_dict()
    assert "credential://" not in str(document)
    assert document["ready"] is False


def test_preflight_applies_exact_capability_requirement() -> None:
    report = AiConnectionSettingsService.preflight(
        profile(),
        ConnectionAvailability(frozenset({"plan", "image"}), frozenset({"credential://openai/default"})),
        required_capabilities={AiWorkload.IMAGE: ("IMAGE_GENERATION",)},
    )
    image = next(item for item in report.workloads if item.workload is AiWorkload.IMAGE)
    assert image.status is SettingsRouteStatus.BLOCKED


def test_preflight_hash_is_deterministic_for_same_inputs() -> None:
    availability = ConnectionAvailability(frozenset({"plan", "image"}), frozenset({"credential://openai/default"}))
    first = AiConnectionSettingsService.preflight(profile(), availability).to_dict()
    second = AiConnectionSettingsService.preflight(profile(), availability).to_dict()
    assert first == second
