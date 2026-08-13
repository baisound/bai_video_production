from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.continuity_map import ContinuityBoundaryType, ContinuityEdge
from ai_video_production.continuity_registry import ContinuityRegistry
from ai_video_production.continuity_registry_store import ContinuityRegistryStore
from ai_video_production.errors import ProductError


SHA = "sha256:" + "a" * 64
SHA2 = "sha256:" + "b" * 64


def registry():
    value = ContinuityRegistry()
    value.add_edge(ContinuityEdge(
        "edge-1", "scene-1", "slot-end", "candidate-1", "asset-1", SHA,
        "scene-2", "slot-start", ContinuityBoundaryType.SOFT_CONTINUITY,
    ))
    value.inspect_target("edge-1", target_asset_id="asset-2", target_asset_sha256=SHA2)
    value.human_approve_soft("edge-1", approved_by="owner")
    return value


def test_continuity_registry_round_trip_preserves_human_resolution(tmp_path: Path):
    path = tmp_path / "continuity.json"
    original = registry()
    ContinuityRegistryStore.save(path, original)
    recovered = ContinuityRegistryStore.recover(path)
    assert recovered.to_dict() == original.to_dict()
    assert recovered.require_generation_safe("edge-1").status == "HUMAN_APPROVED"


def test_continuity_store_detects_tamper(tmp_path: Path):
    path = tmp_path / "continuity.json"
    ContinuityRegistryStore.save(path, registry())
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["resolutions"][0]["target_asset_id"] = "asset-tampered"
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        ContinuityRegistryStore.load_document(path)
    assert exc.value.code == "ERR_CONTINUITY_STORE_CHECKSUM"


def test_continuity_store_requires_compare_and_swap(tmp_path: Path):
    path = tmp_path / "continuity.json"
    value = registry()
    ContinuityRegistryStore.save(path, value)
    with pytest.raises(ProductError) as exc:
        ContinuityRegistryStore.save(path, value)
    assert exc.value.code == "ERR_CONTINUITY_STORE_CAS_REQUIRED"


def test_continuity_registry_matches_task039_schema():
    import jsonschema
    schema_path = Path(__file__).resolve().parents[1] / "docs/ai-team/tasks/TASK-039/schemas/continuity-map.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(registry().to_dict())
