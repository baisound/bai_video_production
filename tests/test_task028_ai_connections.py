from importlib import resources
import json
from pathlib import Path

import pytest

from ai_video_production import (
    AiConnectionProfile,
    AiConnectionResolver,
    AiWorkload,
    ConnectionAvailability,
    CostClass,
    ModelRoute,
    ProductError,
    ProviderFamily,
    ReasoningEffort,
    SelectionMode,
)
from ai_video_production.schema_contracts import validate_instance


def route(
    route_id: str,
    workload: AiWorkload,
    family: ProviderFamily,
    cost: CostClass,
    *,
    priority: int = 100,
    credential_ref: str | None = None,
    capabilities: tuple[str, ...] = (),
    reasoning: ReasoningEffort = ReasoningEffort.NONE,
) -> ModelRoute:
    return ModelRoute(
        route_id, workload, family, family.value.casefold(), f"{route_id}-model", cost,
        priority, reasoning, credential_ref, capabilities=capabilities,
    )


def test_planning_route_preserves_provider_model_and_reasoning_effort():
    value = ModelRoute(
        "planning-primary", AiWorkload.PLANNING, ProviderFamily.OPENAI, "openai", "gpt-5-sol",
        CostClass.CLOUD_PAID_AI, reasoning_effort=ReasoningEffort.MEDIUM,
        credential_ref="credential://openai/default",
    )
    assert value.model_id == "gpt-5-sol"
    assert value.reasoning_effort is ReasoningEffort.MEDIUM
    assert value.to_dict()["credential_ref"] == "credential://openai/default"


def test_ai_mode_excludes_non_ai_library_even_when_it_has_higher_priority():
    library = route("stock", AiWorkload.IMAGE, ProviderFamily.NON_AI_LIBRARY, CostClass.NON_AI_FREE, priority=0)
    ai = route("flux", AiWorkload.IMAGE, ProviderFamily.LOCAL_OPEN_SOURCE, CostClass.LOCAL_FREE_AI, priority=10)
    profile = AiConnectionProfile("p", "1", SelectionMode.AI, (library, ai))
    selected = AiConnectionResolver.resolve(profile, AiWorkload.IMAGE, ConnectionAvailability(frozenset({"stock", "flux"})))
    assert selected.route_id == "flux"


def test_free_mode_excludes_paid_route_and_uses_local_free_model():
    paid = route("cloud-video", AiWorkload.VIDEO, ProviderFamily.OTHER, CostClass.CLOUD_PAID_AI, priority=0)
    free = route("local-video", AiWorkload.VIDEO, ProviderFamily.COMFYUI, CostClass.LOCAL_FREE_AI, priority=10)
    profile = AiConnectionProfile("p", "1", SelectionMode.FREE, (paid, free))
    selected = AiConnectionResolver.resolve(profile, AiWorkload.VIDEO, ConnectionAvailability(frozenset({"cloud-video", "local-video"})))
    assert selected.route_id == "local-video"


def test_offline_only_excludes_cloud_free_tier():
    cloud = route("cloud-music", AiWorkload.MUSIC, ProviderFamily.OTHER, CostClass.CLOUD_FREE_TIER_AI, priority=0)
    local = route("local-music", AiWorkload.MUSIC, ProviderFamily.LOCAL_OPEN_SOURCE, CostClass.LOCAL_FREE_AI, priority=5)
    profile = AiConnectionProfile("p", "1", SelectionMode.OFFLINE_ONLY, (cloud, local))
    selected = AiConnectionResolver.resolve(profile, AiWorkload.MUSIC, ConnectionAvailability(frozenset({"cloud-music", "local-music"})))
    assert selected.route_id == "local-music"


def test_missing_credential_uses_next_eligible_route():
    cloud = route("claude", AiWorkload.PLANNING, ProviderFamily.ANTHROPIC, CostClass.CLOUD_PAID_AI, priority=0, credential_ref="credential://anthropic/default")
    local = route("local-llm", AiWorkload.PLANNING, ProviderFamily.LOCAL_OPEN_SOURCE, CostClass.LOCAL_FREE_AI, priority=10)
    profile = AiConnectionProfile("p", "1", SelectionMode.AUTO, (cloud, local))
    selected = AiConnectionResolver.resolve(profile, AiWorkload.PLANNING, ConnectionAvailability(frozenset({"claude", "local-llm"})))
    assert selected.route_id == "local-llm"


def test_required_capability_filters_routes():
    basic = route("basic", AiWorkload.AUDIO, ProviderFamily.OTHER, CostClass.CLOUD_PAID_AI, priority=0)
    tts = route("tts", AiWorkload.AUDIO, ProviderFamily.OTHER, CostClass.CLOUD_PAID_AI, priority=10, capabilities=("TTS",))
    profile = AiConnectionProfile("p", "1", SelectionMode.AUTO, (basic, tts))
    selected = AiConnectionResolver.resolve(profile, AiWorkload.AUDIO, ConnectionAvailability(frozenset({"basic", "tts"})), required_capabilities=("TTS",))
    assert selected.route_id == "tts"


def test_disabled_or_unavailable_workload_fails_closed():
    profile = AiConnectionProfile("p", "1", SelectionMode.DISABLED, ())
    with pytest.raises(ProductError) as exc:
        AiConnectionResolver.resolve(profile, AiWorkload.PLANNING, ConnectionAvailability(frozenset()))
    assert exc.value.code == "ERR_PROVIDER_WORKLOAD_DISABLED"


def test_route_settings_reject_embedded_secrets():
    with pytest.raises(ValueError, match="secret setting"):
        ModelRoute("bad", AiWorkload.PLANNING, ProviderFamily.OPENAI, "openai", "model", CostClass.CLOUD_PAID_AI, settings={"api_key": "sk-secret"})


def test_model_id_accepts_local_runtime_tag_without_relaxing_route_ids():
    local = ModelRoute(
        "local-llm", AiWorkload.PLANNING, ProviderFamily.LOCAL_OPEN_SOURCE,
        "ollama", "qwen3:8b", CostClass.LOCAL_FREE_AI,
        capabilities=("TEXT_GENERATION",),
    )
    assert local.model_id == "qwen3:8b"
    with pytest.raises(ValueError, match="route_id"):
        ModelRoute("bad:route", AiWorkload.PLANNING, ProviderFamily.LOCAL_OPEN_SOURCE, "ollama", "qwen3:8b", CostClass.LOCAL_FREE_AI)


def test_connection_profile_is_deterministic_schema_valid_and_packaged():
    profile = AiConnectionProfile(
        "creator-default", "1.0.0", SelectionMode.AUTO,
        (route("gemini-plan", AiWorkload.PLANNING, ProviderFamily.GOOGLE, CostClass.CLOUD_FREE_TIER_AI),),
        {AiWorkload.MUSIC: SelectionMode.FREE},
    )
    document = profile.to_dict()
    assert document == profile.to_dict()
    assert AiConnectionProfile.from_dict(document).to_dict() == document
    canonical_path = Path(__file__).parents[1] / "schemas" / "ai-connection-profile.schema.json"
    validate_instance(document, canonical_path)
    packaged = resources.files("ai_video_production").joinpath("schema_resources", "ai-connection-profile.schema.json").read_text(encoding="utf-8")
    assert json.loads(canonical_path.read_text(encoding="utf-8")) == json.loads(packaged)


def test_connection_profile_rejects_checksum_tampering():
    profile = AiConnectionProfile("p", "1", SelectionMode.AUTO, ())
    document = profile.to_dict()
    document["default_mode"] = "FREE"
    with pytest.raises(ValueError, match="checksum mismatch"):
        AiConnectionProfile.from_dict(document)
