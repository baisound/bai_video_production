from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "TASK-037": ROOT / "docs/ai-team/tasks/TASK-037/schemas/production-control-asset-registry.schema.json",
    "TASK-038": ROOT / "docs/ai-team/tasks/TASK-038/schemas/audit-workspace.schema.json",
    "TASK-039": ROOT / "docs/ai-team/tasks/TASK-039/schemas/continuity-map.schema.json",
    "TASK-040": ROOT / "docs/ai-team/tasks/TASK-040/schemas/prompt-generation-registry.schema.json",
    "TASK-041": ROOT / "docs/ai-team/tasks/TASK-041/schemas/audio-workspace.schema.json",
}


@pytest.mark.parametrize("task,path", SCHEMAS.items())
def test_preimplementation_schema_is_valid_draft_202012(task: str, path: Path):
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema["$schema"].endswith("2020-12/schema")
    assert task.lower() in schema["$id"]
    jsonschema.Draft202012Validator.check_schema(schema)


def test_task037_rejects_locked_slot_without_candidate_identity():
    schema = json.loads(SCHEMAS["TASK-037"].read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    # Schema intentionally keeps cross-entity/lifecycle invariants in the future
    # domain service instead of encoding brittle conditional logic here.
    value = {
        "contract_version": "0.9.0-draft",
        "scene_asset_slots": [{
            "slot_id": "slot-1", "project_id": "p1", "scene_id": "s1",
            "slot_kind": "VIDEO", "required": True, "status": "LOCKED",
            "locked_candidate_id": None, "stale_state": "CURRENT", "revision": 1
        }],
        "asset_candidates": [], "dependency_edges": []
    }
    assert list(validator.iter_errors(value)) == []
