from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.prompt_registry import GenerationAttempt, GenerationResult, PromptEntity, PromptGenerationRegistry, RegenerationStrategy
from ai_video_production.prompt_registry_store import PromptRegistrySnapshotStore
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


SHA = "sha256:" + "c" * 64


def registry() -> PromptGenerationRegistry:
    value = PromptGenerationRegistry()
    value.add_prompt(PromptEntity(
        "prompt-1", 1, "scene frame", SHA, "profile-1", "v1", ("monitor foreground",),
        scene_id="scene-1", slot_id="slot-1", body_ref="project-private://prompts/prompt-1"
    ))
    value.add_attempt(GenerationAttempt(
        "job-2", "slot-1", "prompt-1", 1, SHA, "provider-1", "model-1", RegenerationStrategy.TEXT_PROMPT,
        GenerationResult.FAIL, ("DEPTH_ORDER",)
    ))
    value.add_attempt(GenerationAttempt(
        "job-1", "slot-1", "prompt-1", 1, SHA, "provider-1", "model-1", RegenerationStrategy.PROMPT_RESTRUCTURE,
        GenerationResult.FAIL, ("DEPTH_ORDER",), parent_attempt_id="job-2"
    ))
    return value


def test_prompt_snapshot_round_trip_preserves_parent_graph_even_when_sort_order_differs(tmp_path: Path):
    path = tmp_path / "prompt.json"
    PromptRegistrySnapshotStore.save(path, registry())
    loaded = PromptRegistrySnapshotStore.load(path)
    assert loaded.attempts["job-1"].parent_attempt_id == "job-2"
    assert loaded.prompts[("prompt-1", 1)].body_ref.startswith("project-private://")


def test_prompt_snapshot_does_not_embed_prompt_body_or_credentials():
    doc = PromptRegistrySnapshotStore.snapshot(registry())
    assert doc["prompt_body_embedded"] is False
    assert doc["credential_values_embedded"] is False
    assert doc["provider_execution_authorized"] is False
    assert all("prompt_body" not in row for row in doc["prompts"])
    assert all("credential" not in key for row in doc["prompts"] for key in row)


def test_prompt_snapshot_parent_missing_is_rejected(tmp_path: Path):
    path = tmp_path / "prompt.json"
    doc = PromptRegistrySnapshotStore.snapshot(registry())
    doc["attempts"] = [row for row in doc["attempts"] if row["generation_job_id"] == "job-1"]
    body = {k: v for k, v in doc.items() if k != "snapshot_sha256"}
    doc["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        PromptRegistrySnapshotStore.load(path)
    assert exc.value.code == "ERR_PROMPT_SNAPSHOT_PARENT_GRAPH"


def test_existing_prompt_snapshot_requires_compare_and_swap(tmp_path: Path):
    path = tmp_path / "prompt.json"
    value = registry()
    PromptRegistrySnapshotStore.save(path, value)
    with pytest.raises(ProductError) as exc:
        PromptRegistrySnapshotStore.save(path, value)
    assert exc.value.code == "ERR_PROMPT_SNAPSHOT_CAS_REQUIRED"
