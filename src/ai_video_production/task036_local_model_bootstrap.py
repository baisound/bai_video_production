"""TASK-036 local-only Connection Settings bootstrap."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from .ai_connections import (
    AiConnectionProfile, AiWorkload, CostClass, ModelRoute, ProviderFamily,
    ReasoningEffort, SelectionMode,
)
from .connection_settings_store import ConnectionSettingsStore
from .errors import ProductError
from .local_ollama_planning import LocalOllamaTransport, UrllibLocalOllamaTransport

_TAGS_URL = "http://127.0.0.1:11434/api/tags"
_MAX_MODELS = 64


def installed_ollama_planning_models(transport: LocalOllamaTransport | None = None) -> tuple[str, ...]:
    """Return only current tags from the fixed local endpoint."""
    try:
        raw = (transport or UrllibLocalOllamaTransport()).request("GET", _TAGS_URL, None, 5.0)
        document = json.loads(raw.decode("utf-8"))
    except (ProductError, UnicodeDecodeError, json.JSONDecodeError):
        return ()
    models = document.get("models") if isinstance(document, dict) else None
    if not isinstance(models, list) or len(models) > _MAX_MODELS:
        return ()
    values: set[str] = set()
    for item in models:
        name = item.get("name") if isinstance(item, dict) else None
        if not isinstance(name, str):
            return ()
        try:
            ModelRoute("bootstrap-validation", AiWorkload.PLANNING, ProviderFamily.LOCAL_OPEN_SOURCE, "ollama", name, CostClass.LOCAL_FREE_AI, capabilities=("TEXT_GENERATION",))
        except ValueError:
            return ()
        values.add(name)
    return tuple(sorted(values))


def local_bootstrap_profile(model_ids: tuple[str, ...]) -> AiConnectionProfile:
    """Build a secret-free profile from verified inventory only."""
    if not isinstance(model_ids, tuple) or len(model_ids) > _MAX_MODELS:
        raise ValueError("model_ids are invalid")
    if any(not isinstance(model_id, str) for model_id in model_ids):
        raise ValueError("model_ids are invalid")
    if len(set(model_ids)) != len(model_ids):
        raise ValueError("model_ids are invalid")
    routes = tuple(
        ModelRoute(
            f"ollama-planning-{index + 1}", AiWorkload.PLANNING,
            ProviderFamily.LOCAL_OPEN_SOURCE, "ollama", model_id,
            CostClass.LOCAL_FREE_AI, priority=index,
            reasoning_effort=ReasoningEffort.NONE, capabilities=("TEXT_GENERATION",),
        )
        for index, model_id in enumerate(sorted(model_ids))
    )
    return AiConnectionProfile(
        "task036-local-bootstrap", "1.0.0", SelectionMode.OFFLINE_ONLY, routes,
        {
            AiWorkload.PLANNING: SelectionMode.OFFLINE_ONLY,
            AiWorkload.IMAGE: SelectionMode.OFFLINE_ONLY,
            AiWorkload.VIDEO: SelectionMode.OFFLINE_ONLY,
            AiWorkload.AUDIO: SelectionMode.OFFLINE_ONLY,
            AiWorkload.MUSIC: SelectionMode.OFFLINE_ONLY,
        },
    )


def bootstrap_missing_connection_settings(
    settings_path: Path,
    *,
    inventory_provider: Callable[[], tuple[str, ...]] = installed_ollama_planning_models,
) -> bool:
    """Atomically create missing settings once; never rewrite an existing file."""
    if settings_path.is_symlink():
        raise ValueError("settings path must not be a symlink")
    if settings_path.exists():
        return False
    ConnectionSettingsStore.save(settings_path, local_bootstrap_profile(inventory_provider()), expected_revision=0)
    return True
