from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_video_production.approved_plan_orchestration import (
    ApprovedPlanGenerationAdmissionService,
    ApprovedPlanVerifier,
)
from ai_video_production.blueprint_v2_world_lock import BlueprintV2WorldLockService
from ai_video_production.errors import ProductError
from ai_video_production.generation_queue_application import Task027GenerationQueueApplication
from ai_video_production.production_blueprint import AssetSourceStrategy, CameraMotion, GenerationRisk
from ai_video_production.production_blueprint_v2 import (
    BlueprintSceneV2,
    CharacterLockBinding,
    CharacterRole,
    FrameIntent,
    FrameKind,
    FrameReferenceBinding,
    ProductionBlueprintV2,
)
from ai_video_production.production_control import (
    AssetCandidate,
    CandidateLifecycle,
    ProductionControlRegistry,
    SceneAssetSlot,
    SlotKind,
)
from ai_video_production.production_control_store import ProductionControlSnapshotStore
from ai_video_production.production_orchestrator import GenerationQueueAdmissionService
from ai_video_production.production_proposal import (
    ApprovedProductionPlan,
    ProviderPolicyBinding,
    ReferenceAssetBinding,
)
from ai_video_production.timebase import FrameRate
from ai_video_production.shot_feasibility import CheckState, ShotFeasibilityAssessment


H = lambda ch: "sha256:" + ch * 64


def blueprint(*, repeated_hash: bool = False) -> ProductionBlueprintV2:
    def frame(kind: FrameKind, suffix: str, sha: str) -> FrameIntent:
        return FrameIntent(
            kind,
            f"{kind.value} visual",
            "exact axis",
            ("subject",),
            ("crew",),
            ("subject", "background"),
            "eye-level",
            FrameReferenceBinding((CharacterLockBinding(
                CharacterRole.PRIMARY,
                f"asset-{suffix}",
                sha,
                f"slot-ref-{suffix}",
                f"candidate-ref-{suffix}",
            ),)),
        )

    return ProductionBlueprintV2(
        "BP-WORLD-QUEUE",
        "WORLD Queue",
        FrameRate(30, 1),
        300,
        (BlueprintSceneV2(
            "SC01",
            0,
            300,
            "Opening",
            AssetSourceStrategy.AI_GENERATED,
            GenerationRisk.B_HEADLINE,
            CameraMotion.STATIC,
            frame(FrameKind.START, "start", H("a")),
            frame(FrameKind.END, "end", H("a") if repeated_hash else H("b")),
        ),),
    )


def plan(value: ProductionBlueprintV2) -> ApprovedProductionPlan:
    rows = BlueprintV2WorldLockService.requirements(value)
    return ApprovedProductionPlan(
        "PLAN-1234567890ABCDEF",
        "PROPOSAL-WORLD-QUEUE",
        1,
        H("c"),
        H("c"),
        value.blueprint_id,
        value.to_dict()["blueprint_sha256"],
        ProviderPolicyBinding("policy", "v1", H("d")),
        tuple(ReferenceAssetBinding(row.reference_id, row.asset_id, row.asset_sha256) for row in rows),
        Decimal("0"),
        "USD",
        "owner",
        False,
    )


def registry(value: ProductionBlueprintV2) -> ProductionControlRegistry:
    result = ProductionControlRegistry()
    for row in BlueprintV2WorldLockService.requirements(value):
        result.add_slot(SceneAssetSlot(
            row.slot_id,
            "project-v2",
            "WORLD",
            row.expected_slot_kind,
            True,
        ))
        result.add_candidate(AssetCandidate(
            row.candidate_id,
            row.slot_id,
            row.asset_id,
            row.asset_sha256,
            1,
        ))
        result.transition_candidate(row.candidate_id, CandidateLifecycle.READY_FOR_AUDIT)
        result.transition_candidate(row.candidate_id, CandidateLifecycle.ACCEPTED)
        slot = result.slots[row.slot_id]
        result.lock_candidate(
            slot_id=row.slot_id,
            candidate_id=row.candidate_id,
            expected_revision=slot.revision,
        )
    result.add_slot(SceneAssetSlot("slot:SC01:VIDEO", "project-v2", "SC01", SlotKind.VIDEO, True))
    return result


def production_projection(value: ProductionBlueprintV2) -> dict:
    current = registry(value)
    rows = []
    for slot in current.slots.values():
        rows.append({
            **slot.to_dict(),
            "candidates": [
                item.to_dict() for item in current.candidates.values() if item.slot_id == slot.slot_id
            ],
        })
    return {"slots": rows}


def test_v2_queue_uses_exact_world_lock_candidate_not_go_only() -> None:
    value = blueprint()
    approved = plan(value).to_dict()
    prompt = {"input_asset_hashes": [H("a")]}
    proofs, required = Task027GenerationQueueApplication._input_proofs(
        prompt,
        approved,
        production_projection(value),
        value.to_dict(),
    )
    assert proofs == [{
        "asset_sha256": H("a"),
        "proof_kind": "WORLD_LOCKED_CURRENT_CANDIDATE",
        "reference_id": "SC01:START:CHARACTER:0",
        "slot_id": "slot-ref-start",
        "candidate_id": "candidate-ref-start",
        "asset_id": "asset-start",
    }]
    assert required == ("slot-ref-start",)

    with pytest.raises(ProductError) as go_only:
        Task027GenerationQueueApplication._input_proofs(
            prompt,
            approved,
            {"slots": []},
            value.to_dict(),
        )
    assert go_only.value.code == "ERR_QUEUE_WORLD_LOCK_NOT_CURRENT"


def test_v2_queue_repeated_hash_across_frame_paths_fails_ambiguous() -> None:
    value = blueprint(repeated_hash=True)
    with pytest.raises(ProductError) as exc:
        Task027GenerationQueueApplication._input_proofs(
            {"input_asset_hashes": [H("a")]},
            plan(value).to_dict(),
            production_projection(value),
            value.to_dict(),
        )
    assert exc.value.code == "ERR_QUEUE_INPUT_PROOF_AMBIGUOUS"
    assert exc.value.details["match_count"] == 2


def test_v2_queue_rechecks_reference_slot_role() -> None:
    value = blueprint()
    production = production_projection(value)
    slot = next(row for row in production["slots"] if row["slot_id"] == "slot-ref-start")
    slot["slot_kind"] = "SPACE_REFERENCE"
    with pytest.raises(ProductError) as exc:
        Task027GenerationQueueApplication._input_proofs(
            {"input_asset_hashes": [H("a")]},
            plan(value).to_dict(),
            production,
            value.to_dict(),
        )
    assert exc.value.code == "ERR_QUEUE_WORLD_LOCK_NOT_CURRENT"


def test_v2_approved_admission_cannot_omit_world_lock_slots(monkeypatch) -> None:
    value = blueprint()
    approved = plan(value)
    production = registry(value)
    captured = {}
    monkeypatch.setattr(
        ApprovedPlanVerifier,
        "require_current",
        staticmethod(lambda **_: approved),
    )

    def evaluate(**kwargs):
        captured.update(kwargs)
        return "admission"

    monkeypatch.setattr(GenerationQueueAdmissionService, "evaluate", staticmethod(evaluate))
    result = ApprovedPlanGenerationAdmissionService.evaluate(
        proposal_registry=object(),
        plan_id=approved.plan_id,
        blueprint=value,
        scene_id="SC01",
        slot_id="slot:SC01:VIDEO",
        feasibility=object(),
        required_input_slot_ids=(),
        production_registry=production,
        prompt_provider_policy_sha256=H("d"),
        explicit_paid_execution_authorization=False,
        cost_required=False,
    )
    assert result == "admission"
    assert captured["required_input_slot_ids"] == ("slot-ref-start", "slot-ref-end")
    assert captured["cost_authorized"] is False


class _StubApplication:
    def __init__(self, root: Path, value: dict) -> None:
        self.project_root = root
        self.project_id = "project-v2"
        self.value = value

    def snapshot(self) -> dict:
        return self.value


def _v2_queue_application(root: Path, *, token: str) -> Task027GenerationQueueApplication:
    value = blueprint()
    production_registry = registry(value)
    production_path = root / "production-control.json"
    if not production_path.exists():
        ProductionControlSnapshotStore.save(production_path, production_registry)
    production_snapshot = ProductionControlSnapshotStore.snapshot(production_registry)
    production = _StubApplication(root, {
        "snapshot_sha256": production_snapshot["snapshot_sha256"],
        "slots": [
            {
                **slot.to_dict(),
                "candidates": [
                    candidate.to_dict()
                    for candidate in production_registry.candidates.values()
                    if candidate.slot_id == slot.slot_id
                ],
                "available_actions": [],
            }
            for slot in production_registry.slots.values()
        ],
    })
    production.snapshot_path = production_path

    approved = plan(value).to_dict()
    planning = _StubApplication(root, {
        "snapshot_sha256": H("1"),
        "workspace": {
            "go_status": "APPROVED",
            "approved_plan": approved,
            "blueprint": value.to_dict(),
        },
        "installation": {"status": "INSTALLED"},
    })
    checks = {
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
    assessment = ShotFeasibilityAssessment(
        "SC01", checks, "HUMAN_REVIEWED_STRUCTURED_ASSERTION", (), H("f"),
    ).to_dict()
    safety = _StubApplication(root, {
        "safety_snapshot_sha256": H("2"),
        "scenes": [{
            "scene": {"scene_id": "SC01"},
            "feasibility_status": "PASS",
            "current_record": {
                "record_id": "FEAS-1234567890ABCDEF12345678",
                "assessment": assessment,
                "reference_spec": {"continuity_type": "CUT", "start_asset_sha256": None},
            },
        }],
    })
    continuity = _StubApplication(root, {
        "production_snapshot_sha256": production_snapshot["snapshot_sha256"],
        "continuity_snapshot_sha256": H("3"),
        "recovery": {"required": False},
        "workspace": {"edges": []},
    })
    audit = _StubApplication(root, {
        "production_snapshot_sha256": production_snapshot["snapshot_sha256"],
        "audit_snapshot_sha256": H("4"),
        "recovery": {"required": False},
    })
    prompts = _StubApplication(root, {
        "production_snapshot_sha256": production_snapshot["snapshot_sha256"],
        "prompt_snapshot_sha256": H("5"),
        "audit_snapshot_sha256": H("4"),
        "recovery": {"required": False},
        "prompts": [{
            "prompt_id": "prompt-v2", "prompt_version": 1, "scene_id": "SC01",
            "slot_id": "slot:SC01:VIDEO", "body_sha256": H("6"),
            "provider_profile_id": "policy", "provider_profile_version": "v1",
            "input_asset_hashes": [H("a"), H("b")],
        }],
    })
    prompts.audit_application = audit
    return Task027GenerationQueueApplication(
        project_root=root,
        project_id="project-v2",
        production_control=production,
        planning_application=planning,
        generation_safety_application=safety,
        continuity_application=continuity,
        prompt_evidence_application=prompts,
        token_factory=lambda: token,
    )


def test_v2_queue_world_lock_proof_persists_and_reloads_after_restart(tmp_path: Path) -> None:
    value = _v2_queue_application(tmp_path, token="confirm-v2")
    sources = value._sources()
    prepared = value.prepare_enqueue(
        prompt_id="prompt-v2",
        prompt_version=1,
        expected_queue_snapshot_sha256=value.snapshot()["queue_snapshot_sha256"],
        expected_upstream_snapshots={
            "planning": sources["planning"]["snapshot_sha256"],
            "generation_safety": sources["safety"]["safety_snapshot_sha256"],
            "production": sources["production"]["snapshot_sha256"],
            "continuity": sources["continuity"]["continuity_snapshot_sha256"],
            "prompt": sources["prompts"]["prompt_snapshot_sha256"],
            "audit": sources["audit"]["audit_snapshot_sha256"],
        },
    )
    assert {row["proof_kind"] for row in prepared["entry"]["input_bindings"]} == {
        "WORLD_LOCKED_CURRENT_CANDIDATE",
    }
    saved = value.apply_enqueue(confirmation_id="confirm-v2")
    assert saved["entry_count"] == 1

    reopened = _v2_queue_application(tmp_path, token="unused-after-restart")
    snapshot = reopened.snapshot()
    assert snapshot["entry_count"] == 1
    assert snapshot["entries"][0] == reopened.require_current_entry(
        queue_entry_id=snapshot["entries"][0]["queue_entry_id"],
    )["entry"]
