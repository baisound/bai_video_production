from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.generation_queue_application import Task027GenerationQueueApplication
from ai_video_production.production_control import ProductionControlRegistry, SceneAssetSlot, SlotKind
from ai_video_production.production_control_store import ProductionControlSnapshotStore
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.shot_feasibility import CheckState, ShotFeasibilityAssessment


H = lambda ch: "sha256:" + ch * 64
CHECKS = {
    name: CheckState.PASS
    for name in (
        "subject_position_exists", "orientation_camera_compatible",
        "required_visible_coexists", "prohibited_change_not_required",
        "shot_reference_matches_final_camera", "task_axis_valid", "depth_order_valid",
        "occlusion_valid", "furniture_integrity_valid", "room_anchor_integrity_valid",
        "production_gear_absent", "character_identity_valid", "reference_roles_valid",
        "continuity_contract_valid",
    )
}


class StubApplication:
    def __init__(self, root: Path, value: dict):
        self.project_root = root
        self.project_id = "project-1"
        self.value = value

    def snapshot(self):
        return self.value


def applications(root: Path):
    registry = ProductionControlRegistry()
    registry.add_slot(SceneAssetSlot("slot-video", "project-1", "scene-1", SlotKind.VIDEO, True))
    production_path = root / "production-control.json"
    if not production_path.exists():
        ProductionControlSnapshotStore.save(production_path, registry)
    production_sha = ProductionControlSnapshotStore.snapshot(registry)["snapshot_sha256"]
    production_value = {
        "snapshot_sha256": production_sha,
        "slots": [{
            **registry.slots["slot-video"].to_dict(), "candidates": [],
            "available_actions": ["REGISTER_CANDIDATE"],
        }],
    }
    production = StubApplication(root, production_value)
    production.snapshot_path = production_path

    assessment = ShotFeasibilityAssessment(
        "scene-1", CHECKS, "HUMAN_REVIEWED_STRUCTURED_ASSERTION", (), H("f"),
    ).to_dict()
    record = {
        "record_id": "FEAS-1234567890ABCDEF12345678",
        "assessment": assessment,
        "reference_spec": {"continuity_type": "CUT", "start_asset_sha256": None},
    }
    plan = {
        "plan_id": "PLAN-1234567890ABCDEF", "approved_plan_sha256": H("a"),
        "provider_policy": {"policy_id": "profile-1", "policy_version": "v1", "policy_sha256": H("b")},
        "reference_bindings": [],
    }
    planning = StubApplication(root, {
        "snapshot_sha256": H("1"), "workspace": {"go_status": "APPROVED", "approved_plan": plan},
        "installation": {"status": "INSTALLED"},
    })
    safety = StubApplication(root, {
        "safety_snapshot_sha256": H("2"),
        "scenes": [{"scene": {"scene_id": "scene-1"}, "feasibility_status": "PASS", "current_record": record}],
    })
    continuity = StubApplication(root, {
        "production_snapshot_sha256": production_sha, "continuity_snapshot_sha256": H("3"),
        "recovery": {"required": False}, "workspace": {"edges": []},
    })
    audit = StubApplication(root, {
        "production_snapshot_sha256": production_sha, "audit_snapshot_sha256": H("4"),
        "recovery": {"required": False},
    })
    prompts = StubApplication(root, {
        "production_snapshot_sha256": production_sha, "prompt_snapshot_sha256": H("5"),
        "audit_snapshot_sha256": H("4"), "recovery": {"required": False},
        "prompts": [{
            "prompt_id": "prompt-1", "prompt_version": 1, "scene_id": "scene-1",
            "slot_id": "slot-video", "body_sha256": H("6"),
            "provider_profile_id": "profile-1", "provider_profile_version": "v1",
            "input_asset_hashes": [],
        }],
    })
    prompts.audit_application = audit
    return production, planning, safety, continuity, prompts


def app(root: Path, *, token: str = "queue-confirm") -> Task027GenerationQueueApplication:
    production, planning, safety, continuity, prompts = applications(root)
    return Task027GenerationQueueApplication(
        project_root=root, project_id="project-1", production_control=production,
        planning_application=planning, generation_safety_application=safety,
        continuity_application=continuity, prompt_evidence_application=prompts,
        token_factory=lambda: token,
    )


def expected(value: Task027GenerationQueueApplication) -> dict[str, str]:
    sources = value._sources()
    return {
        "planning": sources["planning"]["snapshot_sha256"],
        "generation_safety": sources["safety"]["safety_snapshot_sha256"],
        "production": sources["production"]["snapshot_sha256"],
        "continuity": sources["continuity"]["continuity_snapshot_sha256"],
        "prompt": sources["prompts"]["prompt_snapshot_sha256"],
        "audit": sources["audit"]["audit_snapshot_sha256"],
    }


def test_queue_entry_is_one_shot_restart_durable_and_execution_free(tmp_path: Path):
    value = app(tmp_path)
    state = value.snapshot()
    prepared = value.prepare_enqueue(
        prompt_id="prompt-1", prompt_version=1,
        expected_queue_snapshot_sha256=state["queue_snapshot_sha256"],
        expected_upstream_snapshots=expected(value),
    )
    assert prepared["entry"]["queue_status"] == "ADMISSION_READY"
    assert prepared["entry"]["execution_status"] == "EXECUTION_NOT_AUTHORIZED"
    assert prepared["entry"]["entry_version"] == "1.1.0"
    assert prepared["entry"]["execution_lineage"] == {
        "lineage_version": "1.0.0", "kind": "INITIAL", "strategy_level": 0,
        "parent_attempt_id": None, "regeneration_plan_sha256": None,
    }
    saved = value.apply_enqueue(confirmation_id="queue-confirm")
    assert saved["entry_count"] == 1
    assert saved["provider_execution_started"] is False
    reopened = app(tmp_path, token="next").snapshot()
    assert reopened["entries"][0]["prompt_id"] == "prompt-1"
    assert reopened["entries"][0] == value.require_current_entry(
        queue_entry_id=reopened["entries"][0]["queue_entry_id"],
    )["entry"]
    with pytest.raises(ProductError) as exc:
        value.apply_enqueue(confirmation_id="queue-confirm")
    assert exc.value.code == "ERR_QUEUE_CONFIRMATION_INVALID"


def test_execution_consumer_rejects_stored_queue_entry_after_upstream_drift(tmp_path: Path):
    value = app(tmp_path)
    state = value.snapshot()
    value.prepare_enqueue(
        prompt_id="prompt-1", prompt_version=1,
        expected_queue_snapshot_sha256=state["queue_snapshot_sha256"],
        expected_upstream_snapshots=expected(value),
    )
    saved = value.apply_enqueue(confirmation_id="queue-confirm")
    queue_entry_id = saved["entries"][0]["queue_entry_id"]
    value.prompt_evidence_application.value["prompt_snapshot_sha256"] = H("9")
    with pytest.raises(ProductError) as exc:
        value.require_current_entry(queue_entry_id=queue_entry_id)
    assert exc.value.code == "ERR_QUEUE_ENTRY_STALE"


def test_queue_apply_rejects_upstream_change_after_confirmation(tmp_path: Path):
    value = app(tmp_path)
    state = value.snapshot()
    value.prepare_enqueue(
        prompt_id="prompt-1", prompt_version=1,
        expected_queue_snapshot_sha256=state["queue_snapshot_sha256"],
        expected_upstream_snapshots=expected(value),
    )
    value.prompt_evidence_application.value["prompt_snapshot_sha256"] = H("9")
    with pytest.raises(ProductError) as exc:
        value.apply_enqueue(confirmation_id="queue-confirm")
    assert exc.value.code == "ERR_QUEUE_CONFIRMATION_STALE"


def test_queue_blocks_while_continuity_recovery_is_pending(tmp_path: Path):
    value = app(tmp_path)
    value.continuity_application.value["recovery"] = {"required": True}
    with pytest.raises(ProductError) as exc:
        value.prepare_enqueue(
            prompt_id="prompt-1", prompt_version=1,
            expected_queue_snapshot_sha256=value.snapshot()["queue_snapshot_sha256"],
            expected_upstream_snapshots={key: H("0") for key in (
                "planning", "generation_safety", "production", "continuity", "prompt", "audit",
            )},
        )
    assert exc.value.code == "ERR_QUEUE_CONTINUITY_RECOVERY_REQUIRED"


def test_queue_rejects_checksum_valid_unknown_authority_field(tmp_path: Path):
    value = app(tmp_path)
    state = value.snapshot()
    value.prepare_enqueue(
        prompt_id="prompt-1", prompt_version=1,
        expected_queue_snapshot_sha256=state["queue_snapshot_sha256"],
        expected_upstream_snapshots=expected(value),
    )
    value.apply_enqueue(confirmation_id="queue-confirm")
    document = json.loads(value.queue_path.read_text(encoding="utf-8"))
    document["entries"][0]["dispatch_authorized"] = True
    body = {key: item for key, item in document.items() if key != "queue_snapshot_sha256"}
    document["queue_snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    value.queue_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        value.snapshot()
    assert exc.value.code == "ERR_QUEUE_ENTRY_INVALID"


def test_prompt_input_is_derived_from_exact_human_go_reference():
    prompt = {"input_asset_hashes": [H("7")]}
    plan = {"reference_bindings": [{"reference_id": "ref-1", "asset_id": "asset-1", "asset_sha256": H("7")}]}
    production = {"slots": []}
    proofs, required_slots = Task027GenerationQueueApplication._input_proofs(prompt, plan, production)
    assert proofs == [{
        "asset_sha256": H("7"), "proof_kind": "HUMAN_GO_REFERENCE",
        "reference_id": "ref-1", "slot_id": None, "candidate_id": None,
        "asset_id": "asset-1",
    }]
    assert required_slots == ()


def test_prompt_input_ambiguous_between_go_and_locked_candidate_fails_closed():
    prompt = {"input_asset_hashes": [H("7")]}
    plan = {"reference_bindings": [{"reference_id": "ref-1", "asset_id": "asset-1", "asset_sha256": H("7")}]}
    production = {"slots": [{
        "slot_id": "slot-input", "status": "LOCKED", "stale_state": "CURRENT",
        "locked_candidate_id": "candidate-1", "candidates": [{
            "candidate_id": "candidate-1", "lifecycle_state": "LOCKED",
            "asset_id": "asset-2", "asset_sha256": H("7"),
        }],
    }]}
    with pytest.raises(ProductError) as exc:
        Task027GenerationQueueApplication._input_proofs(prompt, plan, production)
    assert exc.value.code == "ERR_QUEUE_INPUT_PROOF_AMBIGUOUS"


def test_regenerated_prompt_queue_entry_binds_exact_strategy_and_parent(tmp_path: Path):
    value = app(tmp_path)
    prompt = value.prompt_evidence_application.value["prompts"][0]
    prompt["prompt_version"] = 2
    prompt["regeneration_binding"] = {
        "binding_version": "1.0.0", "parent_prompt_id": "prompt-1",
        "parent_prompt_version": 1, "parent_prompt_sha256": H("0"),
        "parent_attempt_id": "job-parent", "strategy_level": 2,
        "reason_codes": ["DEPTH_ORDER"], "regeneration_plan_sha256": H("8"),
    }
    state = value.snapshot()
    prepared = value.prepare_enqueue(
        prompt_id="prompt-1", prompt_version=2,
        expected_queue_snapshot_sha256=state["queue_snapshot_sha256"],
        expected_upstream_snapshots=expected(value),
    )
    assert prepared["entry"]["execution_lineage"] == {
        "lineage_version": "1.0.0", "kind": "REGENERATION", "strategy_level": 2,
        "parent_attempt_id": "job-parent", "regeneration_plan_sha256": H("8"),
    }


def test_regenerated_prompt_without_binding_cannot_receive_new_queue_entry(tmp_path: Path):
    value = app(tmp_path)
    value.prompt_evidence_application.value["prompts"][0]["prompt_version"] = 2
    state = value.snapshot()
    with pytest.raises(ProductError) as exc:
        value.prepare_enqueue(
            prompt_id="prompt-1", prompt_version=2,
            expected_queue_snapshot_sha256=state["queue_snapshot_sha256"],
            expected_upstream_snapshots=expected(value),
        )
    assert exc.value.code == "ERR_QUEUE_REGENERATION_BINDING_REQUIRED"


def test_strict_legacy_queue_entry_remains_readable_without_silent_upgrade(tmp_path: Path):
    value = app(tmp_path)
    state = value.snapshot()
    value.prepare_enqueue(
        prompt_id="prompt-1", prompt_version=1,
        expected_queue_snapshot_sha256=state["queue_snapshot_sha256"],
        expected_upstream_snapshots=expected(value),
    )
    value.apply_enqueue(confirmation_id="queue-confirm")
    document = json.loads(value.queue_path.read_text(encoding="utf-8"))
    document["queue_version"] = "1.0.0"
    entry = document["entries"][0]
    entry["entry_version"] = "1.0.0"
    del entry["execution_lineage"]
    seed = {key: item for key, item in entry.items() if key != "queue_entry_id"}
    entry["queue_entry_id"] = "QUEUE-" + sha256_bytes(canonical_json_bytes(seed)).split(":", 1)[1][:24].upper()
    body = {key: item for key, item in document.items() if key != "queue_snapshot_sha256"}
    document["queue_snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    value.queue_path.write_text(json.dumps(document), encoding="utf-8")
    reopened = value.snapshot()
    assert reopened["entries"][0]["entry_version"] == "1.0.0"
    assert "execution_lineage" not in reopened["entries"][0]
    assert value.require_current_entry(queue_entry_id=entry["queue_entry_id"])["entry"] == entry
