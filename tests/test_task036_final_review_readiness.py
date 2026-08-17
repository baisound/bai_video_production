from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from ai_video_production.final_review_readiness import Task036FinalReviewReadinessProjection


def h(char: str) -> str:
    return "sha256:" + char * 64


def sources():
    production = {
        "available": True,
        "project_id": "project-1",
        "snapshot_sha256": h("1"),
        "slots": [{
            "slot_id": "slot-1", "scene_id": "SC01", "required": True,
            "status": "LOCKED", "stale_state": "CURRENT",
        }],
    }
    audit = {
        "available": True,
        "project_id": "project-1",
        "production_snapshot_sha256": h("1"),
        "audit_snapshot_sha256": h("2"),
        "recovery": {"required": False},
        "workspace": {"candidates": [{
            "candidate_id": "candidate-1", "available_human_actions": [],
            "critical_violation": False,
        }]},
    }
    visual = {
        "available": True,
        "project_id": "project-1",
        "source_snapshots": {"production": h("1")},
        "projection_sha256": h("3"),
        "all_required_visual_slots_adopted": True,
        "required_blocker_count": 0,
    }
    timeline = {
        "available": True,
        "projected_timeline_sha256": h("4"),
        "project_manifest_sha256": h("5"),
    }
    export = {"available": True, "rows": []}
    gates = [{
        "gate_id": gate,
        "project_id": "project-1",
        "timeline_sha256": h("4"),
        "receipt_sha256": h(str(index + 5)),
        "state": "PASS",
    } for index, gate in enumerate((
        "AUDIO_COMPLETION", "EDIT_PERSISTENCE", "PRIVACY", "RESOURCE", "RIGHTS_LICENSE",
    ))]
    return production, audit, visual, timeline, export, gates


def project(values):
    production, audit, visual, timeline, export, gates = values
    return Task036FinalReviewReadinessProjection.project(
        production_snapshot=production,
        audit_snapshot=audit,
        visual_handoff_snapshot=visual,
        timeline_snapshot=timeline,
        export_snapshot=export,
        external_gate_receipts=gates,
    )


def test_exact_current_receipts_reach_readiness_without_creating_approval_or_effect() -> None:
    values = sources()
    first = project(values)
    second = project(copy.deepcopy(values))
    assert first == second
    assert first["state"] == "READY_FOR_TYPED_FINAL_REVIEW"
    assert first["product_blockers"] == []
    assert first["external_blockers"] == []
    assert first["delegated_audio_owner"] == "DEVELOPER2"
    assert first["final_approval_created"] is False
    assert first["export_job_created"] is False
    assert first["render_or_publish_started"] is False
    assert first["human_decision_authorized"] is False


def test_missing_external_receipts_remain_exact_blockers() -> None:
    values = sources()
    values[-1].clear()
    result = project(values)
    assert result["state"] == "BLOCKED_EXTERNAL_GATES"
    assert [row["gate_id"] for row in result["external_gates"]] == [
        "AUDIO_COMPLETION", "EDIT_PERSISTENCE", "PRIVACY", "RESOURCE", "RIGHTS_LICENSE",
    ]
    assert all(row["state"] == "MISSING" for row in result["external_gates"])
    assert len(result["external_blockers"]) == 5


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda p, a, v, t, e, g: p["slots"][0].update(status="ACCEPTED"), "REQUIRED_SLOT_NOT_LOCKED"),
        (lambda p, a, v, t, e, g: p["slots"][0].update(status="STALE", stale_state="STALE"), "STALE_PRODUCTION_SLOT"),
        (lambda p, a, v, t, e, g: a["recovery"].update(required=True), "AUDIT_RECOVERY_REQUIRED"),
        (lambda p, a, v, t, e, g: a["workspace"]["candidates"][0].update(available_human_actions=["ACCEPT"]), "HUMAN_ASSET_DECISION_REQUIRED"),
        (lambda p, a, v, t, e, g: v.update(all_required_visual_slots_adopted=False), "VISUAL_HANDOFF_INCOMPLETE"),
        (lambda p, a, v, t, e, g: t.update(project_manifest_sha256=None), "TIMELINE_PROJECT_MANIFEST_UNBOUND"),
        (lambda p, a, v, t, e, g: e["rows"].append({"job_id": "job-1"}), "UNSCOPED_EXPORT_JOB_PRESENT"),
    ],
)
def test_product_gate_failures_block_before_external_readiness(mutate, code: str) -> None:
    values = sources()
    mutate(*values)
    result = project(values)
    assert result["state"] == "BLOCKED_PRODUCT_GATES"
    assert code in {item["code"] for item in result["product_blockers"]}


def test_external_fail_unknown_stale_and_revoked_never_become_pass() -> None:
    for state in ("FAIL", "UNKNOWN", "STALE", "REVOKED"):
        values = sources()
        values[-1][0]["state"] = state
        result = project(values)
        assert result["state"] == "BLOCKED_EXTERNAL_GATES"
        assert result["external_gates"][0]["state"] == state


def test_cross_scope_duplicate_unknown_and_cap_plus_one_are_rejected() -> None:
    values = sources()
    values[1]["production_snapshot_sha256"] = h("9")
    with pytest.raises(ValueError, match="crosses production"):
        project(values)
    values = sources()
    values[-1].append(copy.deepcopy(values[-1][0]))
    with pytest.raises(ValueError, match="bounded sequence"):
        project(values)
    values = sources()
    values[-1][0]["gate_id"] = "INVENTED"
    with pytest.raises(ValueError, match="unknown external gate"):
        project(values)
    values = sources()
    values[4]["rows"] = [{"job_id": f"job-{index}"} for index in range(257)]
    with pytest.raises(ValueError, match="bounded sequence"):
        project(values)


def test_projection_has_no_filesystem_process_network_or_runner_surface() -> None:
    source_path = Path(__file__).parents[1] / "src" / "ai_video_production" / "final_review_readiness.py"
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
