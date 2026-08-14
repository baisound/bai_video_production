from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.production_control import (
    AssetCandidate, CandidateLifecycle, ProductionControlRegistry, SceneAssetSlot, SlotKind,
)
from ai_video_production.production_control_store import ProductionControlSnapshotStore
from ai_video_production.prompt_registry import (
    PromptCompilationBinding, PromptEntity, PromptGenerationRegistry,
)
from ai_video_production.prompt_registry_store import PromptRegistrySnapshotStore
from ai_video_production.quick_generation import (
    QuickGenerationMode, QuickReferenceInput, QuickReferenceRole, QuickReferenceSource,
)
from ai_video_production.quick_generation_application import Task042QuickGenerationApplication


H = lambda ch: "sha256:" + ch * 64


def binding() -> PromptCompilationBinding:
    return PromptCompilationBinding(
        "1.0.0", "project-private://prompt/manifest", H("b"),
        "project-private://prompt/ja", H("1"), "project-private://prompt/ja-normal", H("2"),
        "project-private://prompt/en", H("3"), None, None, "AI_PROOFREAD", "NONE",
        H("4"), H("5"), H("6"), H("7"), H("8"), H("9"), False, False, False,
        "profile-1", "v1", H("c"), "route-1", ("GENERATE",), (H("a"),), "scene-1", "slot-target",
    )


def seed(root: Path) -> None:
    production = ProductionControlRegistry()
    production.add_slot(SceneAssetSlot("slot-target", "project-1", "scene-1", SlotKind.START_FRAME, False))
    production.add_slot(SceneAssetSlot("slot-character", "project-1", "WORLD", SlotKind.CHARACTER_REFERENCE, True))
    production.add_candidate(AssetCandidate("candidate-character", "slot-character", "asset-character", H("a"), 1))
    production.transition_candidate("candidate-character", CandidateLifecycle.READY_FOR_AUDIT)
    production.transition_candidate("candidate-character", CandidateLifecycle.ACCEPTED)
    production.lock_candidate(slot_id="slot-character", candidate_id="candidate-character", expected_revision=production.slots["slot-character"].revision)
    ProductionControlSnapshotStore.save(root / "production-control.json", production)

    prompts = PromptGenerationRegistry()
    prompts.add_prompt(PromptEntity(
        "prompt-1", 1, "quick image", H("3"), "profile-1", "v1", ("keep",),
        scene_id="scene-1", slot_id="slot-target", body_ref="project-private://prompt/en",
        input_asset_hashes=(H("a"),), compilation_binding=binding(),
    ))
    PromptRegistrySnapshotStore.save(root / "prompt-registry.json", prompts)


def prepare(app: Task042QuickGenerationApplication, *, token_snapshots=None, references=None):
    state = app.snapshot() if token_snapshots is None else token_snapshots
    return app.prepare_intent(
        intent_id="quick-1", intent_version=1, scene_id="scene-1",
        mode=QuickGenerationMode.IMAGE, target_slot_id="slot-target",
        prompt_id="prompt-1", prompt_version=1, provider_profile_sha256=H("c"),
        selected_capability="GENERATE", route_capabilities=("GENERATE",),
        references=references or (QuickReferenceInput(
            "ref-character", QuickReferenceSource.ASSET_LIBRARY, QuickReferenceRole.CHARACTER_LOCK,
            "asset-character", H("a"), "slot-character", "candidate-character",
        ),),
        rights_authorization_ref="rights://owner/quick-1", currency="USD", cost_ceiling="0",
        execution_decision_id="decision-1", execution_decision_sha256=H("d"),
        expected_prompt_snapshot_sha256=state["prompt_snapshot_sha256"],
        expected_production_snapshot_sha256=state["production_snapshot_sha256"],
        expected_quick_snapshot_sha256=state["quick_snapshot_sha256"],
    )


def test_prepare_apply_restart_is_durable_and_execution_free(tmp_path: Path) -> None:
    seed(tmp_path)
    app = Task042QuickGenerationApplication(project_root=tmp_path, project_id="project-1", token_factory=lambda: "confirm")
    prepared = prepare(app)
    assert prepared["intent"]["approved_plan_used"] is False
    saved = app.apply_intent(confirmation_id="confirm")
    assert saved["intent_count"] == 1
    assert saved["intents"][0]["status"] == "CURRENT"
    assert saved["provider_execution_started"] is False
    reopened = Task042QuickGenerationApplication(project_root=tmp_path, project_id="project-1").snapshot()
    assert reopened["intents"][0]["status"] == "CURRENT"
    with pytest.raises(ProductError) as exc:
        app.apply_intent(confirmation_id="confirm")
    assert exc.value.code == "ERR_QUICK_CONFIRMATION_INVALID"


def test_prompt_drift_consumes_confirmation_and_rejects_apply(tmp_path: Path) -> None:
    seed(tmp_path)
    app = Task042QuickGenerationApplication(project_root=tmp_path, project_id="project-1", token_factory=lambda: "confirm")
    prepare(app)
    prompts = PromptRegistrySnapshotStore.load(tmp_path / "prompt-registry.json")
    old = PromptRegistrySnapshotStore.snapshot(prompts)["snapshot_sha256"]
    prompts.add_prompt(PromptEntity("other", 1, "other", H("e"), "p", "1", ("keep",)))
    PromptRegistrySnapshotStore.save(tmp_path / "prompt-registry.json", prompts, expected_previous_snapshot_sha256=old)
    with pytest.raises(ProductError) as exc:
        app.apply_intent(confirmation_id="confirm")
    assert exc.value.code == "ERR_QUICK_SNAPSHOT_CONFLICT"
    with pytest.raises(ProductError) as replay:
        app.apply_intent(confirmation_id="confirm")
    assert replay.value.code == "ERR_QUICK_CONFIRMATION_INVALID"


def test_restart_marks_intent_stale_after_production_snapshot_drift(tmp_path: Path) -> None:
    seed(tmp_path)
    app = Task042QuickGenerationApplication(project_root=tmp_path, project_id="project-1", token_factory=lambda: "confirm")
    prepare(app); app.apply_intent(confirmation_id="confirm")
    production = ProductionControlSnapshotStore.load(tmp_path / "production-control.json")
    old = ProductionControlSnapshotStore.snapshot(production)["snapshot_sha256"]
    production.add_slot(SceneAssetSlot("slot-other", "project-1", "scene-1", SlotKind.OTHER, False))
    ProductionControlSnapshotStore.save(tmp_path / "production-control.json", production, expected_previous_snapshot_sha256=old)
    reopened = Task042QuickGenerationApplication(project_root=tmp_path, project_id="project-1").snapshot()
    assert reopened["intents"][0]["status"] == "STALE_REPREPARE_REQUIRED"


def test_non_current_lock_reference_is_rejected(tmp_path: Path) -> None:
    seed(tmp_path)
    production = ProductionControlSnapshotStore.load(tmp_path / "production-control.json")
    production.slots["slot-character"] = production.slots["slot-character"].__class__(
        "slot-character", "project-1", "WORLD", SlotKind.CHARACTER_REFERENCE, True,
    )
    old_path = tmp_path / "production-control.json"
    old_sha = ProductionControlSnapshotStore.snapshot(ProductionControlSnapshotStore.load(old_path))["snapshot_sha256"]
    ProductionControlSnapshotStore.save(old_path, production, expected_previous_snapshot_sha256=old_sha)
    app = Task042QuickGenerationApplication(project_root=tmp_path, project_id="project-1")
    with pytest.raises(ProductError) as exc:
        prepare(app)
    assert exc.value.code == "ERR_QUICK_REFERENCE_LOCK_NOT_CURRENT"


def test_file_reference_requires_prior_secure_ingest(tmp_path: Path) -> None:
    seed(tmp_path)
    app = Task042QuickGenerationApplication(project_root=tmp_path, project_id="project-1")
    file_reference = QuickReferenceInput(
        "ref-file", QuickReferenceSource.FILE, QuickReferenceRole.GENERAL,
        "asset-character", H("a"),
    )
    with pytest.raises(ProductError) as exc:
        prepare(app, references=(file_reference,))
    assert exc.value.code == "ERR_QUICK_FILE_INGEST_REQUIRED"
