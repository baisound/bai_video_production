from __future__ import annotations

from pathlib import Path
import pytest


from ai_video_production.ai_connections import AiWorkload, CostClass, ProviderFamily
from ai_video_production.connection_settings_store import ConnectionSettingsStore
from ai_video_production.task036_local_model_bootstrap import (
    bootstrap_missing_connection_settings,
    installed_ollama_planning_models,
    local_bootstrap_profile,
)


class TagsTransport:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.calls: list[tuple[str, str, bytes | None, float]] = []

    def request(self, method: str, url: str, body: bytes | None, timeout_seconds: float) -> bytes:
        self.calls.append((method, url, body, timeout_seconds))
        return self.body


def test_inventory_admits_only_current_local_ollama_models() -> None:
    transport = TagsTransport(b'{"models":[{"name":"qwen3:8b"},{"name":"llama3.2:3b"}]}')
    assert installed_ollama_planning_models(transport) == ("llama3.2:3b", "qwen3:8b")
    assert transport.calls == [("GET", "http://127.0.0.1:11434/api/tags", None, 5.0)]


def test_malformed_inventory_never_creates_a_placeholder_candidate() -> None:
    assert installed_ollama_planning_models(TagsTransport(b'{"models":[{"name":"bad model"}]}')) == ()



def test_bootstrap_rejects_untrusted_injected_inventory_types() -> None:
    with pytest.raises(ValueError, match="model_ids are invalid"):
        local_bootstrap_profile(("qwen3:8b", 7))

def test_missing_settings_bootstrap_persists_only_verified_local_planning_routes(tmp_path: Path) -> None:
    path = tmp_path / "ai-connection-settings.json"
    assert bootstrap_missing_connection_settings(path, inventory_provider=lambda: ("qwen3:8b",)) is True
    record = ConnectionSettingsStore.load(path).record
    assert record.revision == 1
    assert record.profile.default_mode.value == "OFFLINE_ONLY"
    assert [(route.workload, route.provider_family, route.provider_id, route.model_id, route.cost_class, route.capabilities) for route in record.profile.routes] == [
        (AiWorkload.PLANNING, ProviderFamily.LOCAL_OPEN_SOURCE, "ollama", "qwen3:8b", CostClass.LOCAL_FREE_AI, ("TEXT_GENERATION",)),
    ]
    assert bootstrap_missing_connection_settings(path, inventory_provider=lambda: ("other:latest",)) is False
    assert ConnectionSettingsStore.load(path).record.profile.routes[0].model_id == "qwen3:8b"
