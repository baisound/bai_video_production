from __future__ import annotations

import copy
import ast
from pathlib import Path

import pytest

from ai_video_production.visual_generation_handoff import Task036VisualGenerationHandoffProjection


def h(char: str) -> str:
    return "sha256:" + char * 64


def snapshots():
    production = {
        "project_id": "project-1", "snapshot_sha256": h("1"),
        "slots": [{
            "slot_id": "slot-1", "scene_id": "SC01", "slot_kind": "VIDEO",
            "required": True, "status": "EMPTY", "stale_state": "CURRENT", "candidates": [],
        }, {
            "slot_id": "audio-1", "scene_id": "SC01", "slot_kind": "NARRATION",
            "required": True, "status": "EMPTY", "stale_state": "CURRENT", "candidates": [],
        }],
    }
    safety = {
        "project_id": "project-1", "safety_snapshot_sha256": h("2"),
        "scenes": [{"scene": {"scene_id": "SC01"}, "feasibility_status": "PASS"}],
    }
    prompt = {
        "project_id": "project-1", "prompt_snapshot_sha256": h("3"),
        "prompts": [{"prompt_id": "prompt-1", "prompt_version": 1, "scene_id": "SC01", "slot_id": "slot-1"}],
    }
    queue = {
        "project_id": "project-1", "queue_snapshot_sha256": h("4"),
        "entries": [{"queue_entry_id": "queue-1", "prompt_id": "prompt-1", "prompt_version": 1, "scene_id": "SC01", "slot_id": "slot-1"}],
        "execution_control": {"project_id": "project-1", "execution_snapshot_sha256": h("5"), "queue_snapshot_sha256": h("4"), "latest_executions": []},
        "output_adoption_control": {"project_id": "project-1", "adoption_snapshot_sha256": h("6"), "eligible_completed_outputs": [], "latest_adoptions": []},
    }
    return production, safety, prompt, queue


def project(values):
    production, safety, prompt, queue = values
    return Task036VisualGenerationHandoffProjection.project(
        production_snapshot=production, safety_snapshot=safety,
        prompt_snapshot=prompt, queue_snapshot=queue,
    )


def test_projection_is_deterministic_excludes_audio_and_starts_at_queue_gate() -> None:
    values = snapshots()
    first = project(values)
    second = project(copy.deepcopy(values))
    assert first == second
    assert first["rows"] == [{
        "scene_id": "SC01", "slot_id": "slot-1", "slot_kind": "VIDEO",
        "required": True, "state": "QUEUED_NOT_EXECUTED",
        "blockers": ["SEPARATE_EXECUTION_CONFIRMATION_REQUIRED"],
        "prompt_id": "prompt-1", "prompt_version": 1, "stale_prompt_count": 0,
        "queue_entry_id": "queue-1", "execution_id": None, "adoption_id": None,
    }]
    assert first["delegated_audio_owner"] == "DEVELOPER2"
    assert first["audio_slot_counted"] == 0
    assert first["required_blocker_count"] == 1
    assert first["provider_execution_authorized"] is False


@pytest.mark.parametrize(
    ("mutate", "state"),
    [
        (lambda p, s, r, q: s.update(scenes=[]), "FEASIBILITY_REQUIRED"),
        (lambda p, s, r, q: s["scenes"][0].update(feasibility_status="FAIL"), "FEASIBILITY_BLOCKED"),
        (lambda p, s, r, q: r.update(prompts=[]), "PROMPT_REQUIRED"),
        (lambda p, s, r, q: q.update(entries=[]), "PROMPT_READY"),
    ],
)
def test_missing_lifecycle_receipts_fail_closed(mutate, state: str) -> None:
    values = snapshots()
    mutate(*values)
    assert project(values)["rows"][0]["state"] == state


def test_completed_output_requires_explicit_adoption_then_human_asset_decision() -> None:
    values = snapshots()
    execution = {
        "execution_id": "execution-1", "queue_entry_id": "queue-1", "state": "COMPLETED",
    }
    values[3]["execution_control"]["latest_executions"] = [execution]
    assert project(values)["rows"][0]["state"] == "OUTPUT_ADOPTION_UNKNOWN"
    values[3]["output_adoption_control"]["eligible_completed_outputs"] = [{
        "execution_id": "execution-1", "adoption_status": "READY",
    }]
    assert project(values)["rows"][0]["state"] == "OUTPUT_READY_FOR_ADOPTION"
    values[3]["output_adoption_control"]["latest_adoptions"] = [{
        "execution_id": "execution-1", "adoption_id": "adoption-1", "state": "READY_FOR_AUDIT",
    }]
    result = project(values)
    assert result["rows"][0]["state"] == "READY_FOR_AUDIT"
    assert result["all_required_visual_slots_adopted"] is False


@pytest.mark.parametrize("status", ["ACCEPTED", "LOCKED"])
def test_only_exact_current_human_adopted_candidate_closes_required_slot(status: str) -> None:
    values = snapshots()
    slot = values[0]["slots"][0]
    slot["status"] = status
    slot["candidates"] = [{"candidate_id": "candidate-1", "lifecycle_state": status}]
    result = project(values)
    assert result["rows"][0]["state"] == f"{status}_ASSET"
    assert result["required_blocker_count"] == 0
    assert result["all_required_visual_slots_adopted"] is True


def test_cross_scope_duplicate_and_invalid_digest_are_rejected() -> None:
    values = snapshots()
    values[2]["prompts"][0]["scene_id"] = "SC02"
    with pytest.raises(ValueError, match="crosses scene"):
        project(values)
    values = snapshots()
    values[0]["slots"].append(dict(values[0]["slots"][0]))
    with pytest.raises(ValueError, match="duplicate slot"):
        project(values)
    values = snapshots()
    values[3]["queue_snapshot_sha256"] = "invented"
    with pytest.raises(ValueError, match="canonical SHA-256"):
        project(values)


def test_project_queue_and_duplicate_scene_or_execution_scope_are_fail_closed() -> None:
    values = snapshots()
    values[1]["project_id"] = "other-project"
    with pytest.raises(ValueError, match="crosses project scope"):
        project(values)
    values = snapshots()
    values[3]["execution_control"]["queue_snapshot_sha256"] = h("9")
    with pytest.raises(ValueError, match="crosses queue snapshot"):
        project(values)
    values = snapshots()
    values[1]["scenes"].append(copy.deepcopy(values[1]["scenes"][0]))
    with pytest.raises(ValueError, match="duplicate safety scene"):
        project(values)
    values = snapshots()
    values[3]["execution_control"]["latest_executions"] = [
        {"execution_id": "execution-1", "queue_entry_id": "queue-1", "state": "FAILED_KNOWN"},
        {"execution_id": "execution-2", "queue_entry_id": "queue-1", "state": "COMPLETED"},
    ]
    with pytest.raises(ValueError, match="duplicate execution queue_entry_id"):
        project(values)


def test_stale_and_dispatching_never_inflate_completion() -> None:
    values = snapshots()
    values[0]["slots"][0].update(status="STALE", stale_state="STALE")
    assert project(values)["rows"][0]["state"] == "STALE_BLOCKED"
    values = snapshots()
    values[3]["execution_control"]["latest_executions"] = [{
        "execution_id": "execution-1", "queue_entry_id": "queue-1", "state": "DISPATCHING",
    }]
    result = project(values)
    assert result["rows"][0]["state"] == "EXECUTION_RECOVERY_REQUIRED"
    assert result["rows"][0]["blockers"] == ["NO_AUTOMATIC_RETRY"]


def test_projection_has_no_filesystem_process_network_or_runner_surface() -> None:
    source_path = Path(__file__).parents[1] / "src" / "ai_video_production" / "visual_generation_handoff.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        (node.module or "").split(".")[-1]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    assert imports <= {"__future__", "abc", "re", "typing", "serialization"}
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert calls.isdisjoint({"open", "exec", "eval", "compile", "system", "run", "Popen"})
    assert all(token not in source for token in ("pathlib", "subprocess", "socket", "requests", "urllib"))
