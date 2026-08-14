from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from ai_video_production.blueprint_v2_world_lock import BlueprintV2WorldLockService
from ai_video_production.errors import ProductError
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
from ai_video_production.production_proposal import (
    ApprovedProductionPlan,
    ProviderPolicyBinding,
    ReferenceAssetBinding,
)
from ai_video_production.timebase import FrameRate


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64


def frame(kind: FrameKind, suffix: str, sha: str) -> FrameIntent:
    return FrameIntent(
        kind,
        f"{kind.value} visual",
        "exact task axis",
        ("subject",),
        ("crew",),
        ("subject", "background"),
        "eye-level",
        FrameReferenceBinding((CharacterLockBinding(
            CharacterRole.PRIMARY,
            f"asset-{suffix}",
            sha,
            f"slot-{suffix}",
            f"candidate-{suffix}",
        ),)),
    )


def blueprint() -> ProductionBlueprintV2:
    return ProductionBlueprintV2(
        "BP-WORLD-LOCK",
        "WORLD LOCK",
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
            frame(FrameKind.START, "start", SHA_A),
            frame(FrameKind.END, "end", SHA_B),
        ),),
    )


def plan(value: ProductionBlueprintV2, *, changed_sha: str | None = None) -> ApprovedProductionPlan:
    requirements = BlueprintV2WorldLockService.requirements(value)
    bindings = tuple(
        ReferenceAssetBinding(
            row.reference_id,
            row.asset_id,
            changed_sha if changed_sha is not None and index == 0 else row.asset_sha256,
        )
        for index, row in enumerate(requirements)
    )
    return ApprovedProductionPlan(
        "PLAN-1234567890ABCDEF",
        "PROPOSAL-WORLD-LOCK",
        1,
        SHA_C,
        SHA_C,
        value.blueprint_id,
        value.to_dict()["blueprint_sha256"],
        ProviderPolicyBinding("policy", "v1", SHA_C),
        bindings,
        Decimal("0"),
        "USD",
        "owner",
        False,
    )


def locked_registry(value: ProductionBlueprintV2) -> ProductionControlRegistry:
    registry = ProductionControlRegistry()
    for row in BlueprintV2WorldLockService.requirements(value):
        registry.add_slot(SceneAssetSlot(
            row.slot_id,
            "project-1",
            "WORLD",
            row.expected_slot_kind,
            True,
        ))
        registry.add_candidate(AssetCandidate(
            row.candidate_id,
            row.slot_id,
            row.asset_id,
            row.asset_sha256,
            1,
        ))
        registry.transition_candidate(row.candidate_id, CandidateLifecycle.READY_FOR_AUDIT)
        registry.transition_candidate(row.candidate_id, CandidateLifecycle.ACCEPTED)
        slot = registry.slots[row.slot_id]
        registry.lock_candidate(
            slot_id=row.slot_id,
            candidate_id=row.candidate_id,
            expected_revision=slot.revision,
        )
    return registry


def test_reference_slot_kinds_round_trip_without_changing_old_store_contract(tmp_path: Path) -> None:
    value = blueprint()
    registry = locked_registry(value)
    path = tmp_path / "production-control.json"
    ProductionControlSnapshotStore.save(path, registry)
    loaded = ProductionControlSnapshotStore.load(path)
    assert loaded.slots["slot-start"].slot_kind is SlotKind.CHARACTER_REFERENCE
    assert loaded.slots["slot-end"].slot_kind is SlotKind.CHARACTER_REFERENCE
    assert ProductionControlSnapshotStore.snapshot(loaded) == ProductionControlSnapshotStore.snapshot(registry)


def test_projection_requires_exact_current_task037_lock_and_is_deterministic() -> None:
    value = blueprint()
    approved = plan(value)
    registry = locked_registry(value)
    first = BlueprintV2WorldLockService.require_current(
        blueprint=value,
        approved_plan=approved,
        registry=registry,
        project_id="project-1",
    )
    second = BlueprintV2WorldLockService.require_current(
        blueprint=value,
        approved_plan=approved,
        registry=registry,
        project_id="project-1",
    )
    assert first == second
    assert first["status"] == "PASS"
    assert [row["status"] for row in first["bindings"]] == ["LOCKED_CURRENT", "LOCKED_CURRENT"]
    assert first["world_lock_store_created"] is False
    assert first["human_lock_inferred_from_go"] is False
    assert first["provider_execution_started"] is False


def test_human_go_identity_alone_never_becomes_world_lock() -> None:
    value = blueprint()
    projection = BlueprintV2WorldLockService.project(
        blueprint=value,
        approved_plan=plan(value),
        registry=ProductionControlRegistry(),
        project_id="project-1",
    )
    assert projection["status"] == "BLOCKED"
    assert projection["recovery_required"] is True
    assert {"SLOT_MISSING", "CANDIDATE_MISSING"}.issubset(projection["blockers"])
    with pytest.raises(ProductError) as exc:
        BlueprintV2WorldLockService.require_current(
            blueprint=value,
            approved_plan=plan(value),
            registry=ProductionControlRegistry(),
            project_id="project-1",
        )
    assert exc.value.code == "ERR_BLUEPRINT_V2_WORLD_LOCK_NOT_CURRENT"


def test_projection_rejects_wrong_go_identity_role_project_and_stale_state() -> None:
    value = blueprint()
    registry = locked_registry(value)
    registry.slots["slot-start"] = SceneAssetSlot(
        "slot-start",
        "other-project",
        "WORLD",
        SlotKind.SPACE_REFERENCE,
        True,
        status=registry.slots["slot-start"].status,
        locked_candidate_id="candidate-start",
        stale_state=registry.slots["slot-start"].stale_state,
        revision=registry.slots["slot-start"].revision,
    )
    projection = BlueprintV2WorldLockService.project(
        blueprint=value,
        approved_plan=plan(value, changed_sha=SHA_C),
        registry=registry,
        project_id="project-1",
    )
    assert projection["status"] == "BLOCKED"
    assert {
        "GO_REFERENCE_IDENTITY_MISMATCH",
        "SLOT_PROJECT_MISMATCH",
        "SLOT_ROLE_MISMATCH",
    }.issubset(projection["blockers"])


def test_dependency_edges_are_candidate_to_scene_and_deduplicated() -> None:
    value = blueprint()
    registry = locked_registry(value)
    edges = BlueprintV2WorldLockService.dependency_edges(
        blueprint=value,
        approved_plan=plan(value),
        registry=registry,
        project_id="project-1",
    )
    assert len(edges) == 2
    assert {edge.from_ref.entity_id for edge in edges} == {"candidate-start", "candidate-end"}
    assert {edge.to_ref.entity_id for edge in edges} == {"SC01"}
    assert all(edge.to_dict()["dependency_kind"] == "USES" for edge in edges)
