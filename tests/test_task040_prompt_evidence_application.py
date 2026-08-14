from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.audit_production_binding import AuditProductionControlBinding
from ai_video_production.candidate_audit import (
    AuditDimension, AuditFinding, AuditRecord, AuditorKind, CandidateAuditRegistry,
    FindingSeverity, HumanCandidateDecision, HumanDecision,
)
from ai_video_production.candidate_audit_store import CandidateAuditSnapshotStore
from ai_video_production.errors import ProductError
from ai_video_production.production_control import (
    AssetCandidate, CandidateLifecycle, ProductionControlRegistry, SceneAssetSlot, SlotKind,
)
from ai_video_production.production_control_application import Task037ProductionControlApplication
from ai_video_production.production_control_store import ProductionControlSnapshotStore
from ai_video_production.prompt_evidence_application import Task040PromptEvidenceApplication
from ai_video_production.prompt_registry import (
    GenerationAttempt, GenerationResult, PromptEntity, PromptGenerationRegistry, RegenerationStrategy,
)
from ai_video_production.prompt_registry_store import PromptRegistrySnapshotStore


H = lambda ch: "sha256:" + ch * 64


def seed_production(root: Path, *, candidate: bool = True) -> Task037ProductionControlApplication:
    value = ProductionControlRegistry()
    value.add_slot(SceneAssetSlot("slot-1", "project-1", "scene-1", SlotKind.START_FRAME, True))
    if candidate:
        value.add_candidate(AssetCandidate("candidate-1", "slot-1", "asset-1", H("a"), 1, generation_job_id="job-1"))
        value.transition_candidate("candidate-1", CandidateLifecycle.READY_FOR_AUDIT)
    ProductionControlSnapshotStore.save(root / "production-control.json", value)
    return Task037ProductionControlApplication(project_root=root, project_id="project-1")


def seed_prompt(root: Path) -> None:
    value = PromptGenerationRegistry()
    value.add_prompt(PromptEntity(
        "prompt-1", 1, "scene frame", H("1"), "profile-1", "v1", ("keep face",),
        scene_id="scene-1", slot_id="slot-1", body_ref="project-private://prompts/prompt-1/v1",
    ))
    PromptRegistrySnapshotStore.save(root / "prompt-registry.json", value)


def prepare_pass(app: Task040PromptEvidenceApplication):
    state = app.snapshot()
    return app.prepare_attempt(
        generation_job_id="job-1", slot_id="slot-1", prompt_id="prompt-1", prompt_version=1,
        provider_id="provider-1", model_id="model-1", strategy_level=0, result="PASS",
        failure_codes=(), output_candidate_id="candidate-1", parent_attempt_id=None,
        cost=None, latency_ms=1200,
        expected_prompt_snapshot_sha256=state["prompt_snapshot_sha256"],
        expected_production_snapshot_sha256=state["production_snapshot_sha256"],
    )


def test_initial_prompt_registration_is_one_shot_private_and_restart_durable(tmp_path: Path) -> None:
    seed_production(tmp_path, candidate=False)
    app = Task040PromptEvidenceApplication(
        project_root=tmp_path, project_id="project-1", token_factory=lambda: "prompt-confirm",
    )
    state = app.snapshot()
    prepared = app.prepare_prompt(
        prompt_id="prompt-1", prompt_version=1, purpose="scene frame", scene_id="scene-1",
        slot_id="slot-1", body_ref="project-private://prompts/prompt-1/v1", body_sha256=H("1"),
        provider_profile_id="profile-1", provider_profile_version="v1", input_asset_hashes=(),
        keep_conditions=("keep face",), expected_prompt_snapshot_sha256=state["prompt_snapshot_sha256"],
        expected_production_snapshot_sha256=state["production_snapshot_sha256"],
    )
    saved = app.apply_prompt(confirmation_id=prepared["confirmation_id"])
    assert saved["prompt_count"] == 1
    assert saved["provider_execution_started"] is False
    assert "prompt_body" not in saved["prompts"][0]
    assert Task040PromptEvidenceApplication(project_root=tmp_path, project_id="project-1").snapshot()["prompt_count"] == 1
    with pytest.raises(ProductError) as exc:
        app.apply_prompt(confirmation_id="prompt-confirm")
    assert exc.value.code == "ERR_PROMPT_APPLICATION_CONFIRMATION_INVALID"


def test_fail_attempt_import_persists_only_prompt_evidence(tmp_path: Path) -> None:
    seed_production(tmp_path, candidate=False); seed_prompt(tmp_path)
    app = Task040PromptEvidenceApplication(project_root=tmp_path, project_id="project-1", token_factory=lambda: "attempt")
    state = app.snapshot()
    prepared = app.prepare_attempt(
        generation_job_id="job-fail", slot_id="slot-1", prompt_id="prompt-1", prompt_version=1,
        provider_id="provider-1", model_id="model-1", strategy_level=0, result="FAIL",
        failure_codes=("DEPTH_REVERSED",), output_candidate_id=None, parent_attempt_id=None,
        cost=None, latency_ms=900,
        expected_prompt_snapshot_sha256=state["prompt_snapshot_sha256"],
        expected_production_snapshot_sha256=state["production_snapshot_sha256"],
    )
    assert prepared["production_binding_required"] is False
    before_production = state["production_snapshot_sha256"]
    saved = app.apply_attempt(confirmation_id="attempt")
    assert saved["attempt_count"] == 1
    assert saved["production_snapshot_sha256"] == before_production
    assert saved["candidate_creation_started"] is False


def test_pass_attempt_binds_both_stores_and_restart_projection(tmp_path: Path) -> None:
    seed_production(tmp_path); seed_prompt(tmp_path)
    app = Task040PromptEvidenceApplication(project_root=tmp_path, project_id="project-1", token_factory=lambda: "pass")
    prepared = prepare_pass(app)
    assert prepared["production_binding_required"] is True
    saved = app.apply_attempt(confirmation_id="pass")
    assert saved["recovery"]["required"] is False
    production = ProductionControlSnapshotStore.load(tmp_path / "production-control.json")
    assert any(edge.to_ref.entity_id == "candidate-1" for edge in production.edges.values())
    reopened = Task040PromptEvidenceApplication(project_root=tmp_path, project_id="project-1").snapshot()
    assert reopened["attempt_count"] == 1
    assert reopened["prompts"][0]["attempts"][0]["output_candidate_id"] == "candidate-1"


def test_crash_after_prompt_save_requires_exact_production_completion(tmp_path: Path) -> None:
    seed_production(tmp_path); seed_prompt(tmp_path)

    def fail(stage: str):
        if stage == "after_prompt_save":
            raise RuntimeError("crash")

    app = Task040PromptEvidenceApplication(
        project_root=tmp_path, project_id="project-1", token_factory=lambda: "pass",
        failure_injector=fail,
    )
    prepare_pass(app)
    with pytest.raises(RuntimeError):
        app.apply_attempt(confirmation_id="pass")
    reopened = Task040PromptEvidenceApplication(project_root=tmp_path, project_id="project-1")
    state = reopened.snapshot()
    assert state["recovery"]["state"] == "PROMPT_NEW_PRODUCTION_OLD"
    assert state["actions_allowed"] is False
    completed = reopened.apply_recovery(action="COMPLETE")
    assert completed["recovery"]["required"] is False
    assert completed["attempt_count"] == 1


def test_crash_before_store_write_can_be_abandoned(tmp_path: Path) -> None:
    seed_production(tmp_path); seed_prompt(tmp_path)

    def fail(stage: str):
        if stage == "after_transaction_prepare":
            raise RuntimeError("crash")

    app = Task040PromptEvidenceApplication(
        project_root=tmp_path, project_id="project-1", token_factory=lambda: "pass",
        failure_injector=fail,
    )
    prepare_pass(app)
    with pytest.raises(RuntimeError):
        app.apply_attempt(confirmation_id="pass")
    reopened = Task040PromptEvidenceApplication(project_root=tmp_path, project_id="project-1")
    assert reopened.snapshot()["recovery"]["available_actions"] == ["COMPLETE", "ABANDON"]
    abandoned = reopened.apply_recovery(action="ABANDON")
    assert abandoned["attempt_count"] == 0


def test_human_regeneration_creates_next_prompt_version_without_provider(tmp_path: Path) -> None:
    production_app = seed_production(tmp_path); seed_prompt(tmp_path)
    prompts = PromptRegistrySnapshotStore.load(tmp_path / "prompt-registry.json")
    prompts.add_attempt(GenerationAttempt(
        "job-1", "slot-1", "prompt-1", 1, H("1"), "provider-1", "model-1",
        RegenerationStrategy.TEXT_PROMPT, GenerationResult.PASS, (), "candidate-1",
        provider_profile_version="v1",
    ))
    old_prompt = PromptRegistrySnapshotStore.snapshot(PromptRegistrySnapshotStore.load(tmp_path / "prompt-registry.json"))["snapshot_sha256"]
    PromptRegistrySnapshotStore.save(tmp_path / "prompt-registry.json", prompts, expected_previous_snapshot_sha256=old_prompt)

    production = ProductionControlSnapshotStore.load(tmp_path / "production-control.json")
    audits = CandidateAuditRegistry()
    AuditProductionControlBinding.record_audit(production, audits, AuditRecord(
        "audit-1", "candidate-1", H("a"), ("contract-1",), AuditorKind.AI, "vision", "v1",
        {"GEOMETRY": 10.0},
        (AuditFinding("finding-1", AuditDimension.GEOMETRY, FindingSeverity.CRITICAL, "DEPTH_REVERSED", "depth reversed", True),),
        ("DEPTH_REVERSED",),
    ))
    AuditProductionControlBinding.apply_human_decision(production, audits, HumanDecision(
        "decision-1", "candidate-1", ("audit-1",), HumanCandidateDecision.NEEDS_REGENERATION, "owner",
    ))
    CandidateAuditSnapshotStore.save(tmp_path / "candidate-audit.json", audits)

    app = Task040PromptEvidenceApplication(
        project_root=tmp_path, project_id="project-1", production_control=production_app,
        token_factory=lambda: "regen",
    )
    state = app.snapshot()
    assert state["prompts"][0]["attempts"][0]["human_regeneration_available"] is True
    prepared = app.prepare_regeneration(
        candidate_id="candidate-1", new_body_sha256=H("2"),
        new_body_ref="project-private://prompts/prompt-1/v2", provider_profile_id=None,
        provider_profile_version=None, input_asset_hashes=None, keep_conditions=None,
        repeated_failure_threshold=2, expected_prompt_snapshot_sha256=state["prompt_snapshot_sha256"],
        expected_production_snapshot_sha256=state["production_snapshot_sha256"],
        expected_audit_snapshot_sha256=state["audit_snapshot_sha256"],
    )
    assert prepared["draft"]["new_prompt"]["prompt_version"] == 2
    saved = app.apply_regeneration(confirmation_id="regen")
    assert saved["prompt_count"] == 2
    assert saved["provider_execution_started"] is False


def test_prompt_scope_requires_existing_project_slot_and_private_body_ref(tmp_path: Path) -> None:
    seed_production(tmp_path, candidate=False)
    app = Task040PromptEvidenceApplication(project_root=tmp_path, project_id="project-1")
    state = app.snapshot()
    with pytest.raises(ProductError) as exc:
        app.prepare_prompt(
            prompt_id="prompt-1", prompt_version=1, purpose="x", scene_id="scene-1",
            slot_id="slot-missing", body_ref="C:/private/prompt.txt", body_sha256=H("1"),
            provider_profile_id="profile-1", provider_profile_version="v1", input_asset_hashes=(),
            keep_conditions=("keep",), expected_prompt_snapshot_sha256=state["prompt_snapshot_sha256"],
            expected_production_snapshot_sha256=state["production_snapshot_sha256"],
        )
    assert exc.value.code == "ERR_PROMPT_APPLICATION_BODY_REF_INVALID"


def test_invalid_attempt_metadata_is_normalized_to_product_error(tmp_path: Path) -> None:
    seed_production(tmp_path, candidate=False); seed_prompt(tmp_path)
    app = Task040PromptEvidenceApplication(project_root=tmp_path, project_id="project-1")
    state = app.snapshot()
    with pytest.raises(ProductError) as exc:
        app.prepare_attempt(
            generation_job_id="job-invalid", slot_id="slot-1", prompt_id="prompt-1",
            prompt_version=1, provider_id="provider-1", model_id="model-1",
            strategy_level=0, result="NOT_A_RESULT", failure_codes=(),
            output_candidate_id=None, parent_attempt_id=None, cost=None, latency_ms=None,
            expected_prompt_snapshot_sha256=state["prompt_snapshot_sha256"],
            expected_production_snapshot_sha256=state["production_snapshot_sha256"],
        )
    assert exc.value.code == "ERR_PROMPT_APPLICATION_ATTEMPT_INVALID"
