from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import pytest

from ai_video_production.continuity_application import Task039ContinuityApplication
from ai_video_production.errors import ProductError
from ai_video_production.production_control import (
    AssetCandidate,
    CandidateLifecycle,
    ProductionControlRegistry,
    SceneAssetSlot,
    SlotKind,
)
from ai_video_production.production_control_application import Task037ProductionControlApplication
from ai_video_production.production_control_store import ProductionControlSnapshotStore


H1 = "sha256:" + "a" * 64
H2 = "sha256:" + "b" * 64


def seed_production(root: Path, *, target_same: bool = False) -> Task037ProductionControlApplication:
    registry = ProductionControlRegistry()
    registry.add_slot(SceneAssetSlot("slot-end", "project-1", "scene-1", SlotKind.END_FRAME, True))
    registry.add_slot(SceneAssetSlot("slot-start", "project-1", "scene-2", SlotKind.START_FRAME, True))
    registry.add_candidate(AssetCandidate("candidate-end", "slot-end", "asset-end", H1, 1))
    registry.add_candidate(AssetCandidate(
        "candidate-start", "slot-start", "asset-end" if target_same else "asset-start",
        H1 if target_same else H2, 1,
    ))
    for candidate_id in ("candidate-end", "candidate-start"):
        registry.transition_candidate(candidate_id, CandidateLifecycle.READY_FOR_AUDIT)
        registry.transition_candidate(candidate_id, CandidateLifecycle.ACCEPTED)
    for slot_id, candidate_id in (("slot-end", "candidate-end"), ("slot-start", "candidate-start")):
        slot = registry.slots[slot_id]
        registry.lock_candidate(slot_id=slot_id, candidate_id=candidate_id, expected_revision=slot.revision)
    ProductionControlSnapshotStore.save(root / "production-control.json", registry)
    return Task037ProductionControlApplication(project_root=root, project_id="project-1")


def prepare(app: Task039ContinuityApplication, *, boundary: str = "SOFT_CONTINUITY", edge_id: str = "edge-1"):
    state = app.snapshot()
    return app.prepare_register_edge(
        edge_id=edge_id, from_slot_id="slot-end", to_slot_id="slot-start", boundary_type=boundary,
        character_contract_refs=("CHAR-1",), space_contract_refs=("SPACE-1",),
        expected_production_snapshot_sha256=state["production_snapshot_sha256"],
        expected_continuity_snapshot_sha256=state["continuity_snapshot_sha256"],
    )


def register(app: Task039ContinuityApplication, *, boundary: str = "SOFT_CONTINUITY"):
    prepared = prepare(app, boundary=boundary)
    return app.apply_register_edge(confirmation_id=prepared["confirmation_id"])


def test_edge_registration_persists_both_stores_and_restart_projection(tmp_path: Path) -> None:
    production = seed_production(tmp_path)
    app = Task039ContinuityApplication(
        project_root=tmp_path, project_id="project-1", production_control=production,
        token_factory=lambda: "edge-confirm",
    )
    state = register(app)
    assert state["recovery"]["required"] is False
    assert state["workspace"]["edges"][0]["edge_id"] == "edge-1"
    reopened = Task039ContinuityApplication(project_root=tmp_path, project_id="project-1").snapshot()
    assert reopened["workspace"]["edges"][0]["generation_safe"] is False
    assert reopened["automatic_regeneration_started"] is False
    with pytest.raises(ProductError) as exc:
        app.apply_register_edge(confirmation_id="edge-confirm")
    assert exc.value.code == "ERR_CONTINUITY_APPLICATION_CONFIRMATION_INVALID"


def test_soft_inspection_and_human_approval_are_durable_and_separate(tmp_path: Path) -> None:
    production = seed_production(tmp_path)
    tokens = iter(("edge", "soft"))
    app = Task039ContinuityApplication(
        project_root=tmp_path, project_id="project-1", production_control=production,
        token_factory=lambda: next(tokens),
    )
    register(app)
    state = app.snapshot()
    inspected = app.inspect_locked_target(
        edge_id="edge-1", expected_production_snapshot_sha256=state["production_snapshot_sha256"],
        expected_continuity_snapshot_sha256=state["continuity_snapshot_sha256"],
    )
    assert inspected["resolution"]["status"] == "HUMAN_REVIEW_REQUIRED"
    state = inspected["application"]
    prepared = app.prepare_soft_approval(
        edge_id="edge-1", expected_production_snapshot_sha256=state["production_snapshot_sha256"],
        expected_continuity_snapshot_sha256=state["continuity_snapshot_sha256"],
    )
    approved = app.apply_soft_approval(confirmation_id=prepared["confirmation_id"], approved_by="owner")
    assert approved["resolution"]["status"] == "HUMAN_APPROVED"
    row = Task039ContinuityApplication(project_root=tmp_path, project_id="project-1").snapshot()["workspace"]["edges"][0]
    assert row["generation_safe"] is True
    assert row["resolution"]["human_approved_by"] == "owner"
    with pytest.raises(ProductError) as exc:
        app.inspect_locked_target(
            edge_id="edge-1", expected_production_snapshot_sha256=approved["application"]["production_snapshot_sha256"],
            expected_continuity_snapshot_sha256=approved["application"]["continuity_snapshot_sha256"],
        )
    assert exc.value.code == "ERR_CONTINUITY_APPLICATION_ALREADY_INSPECTED"


def test_direct_continuation_exact_match_passes_without_human_override(tmp_path: Path) -> None:
    production = seed_production(tmp_path, target_same=True)
    app = Task039ContinuityApplication(project_root=tmp_path, project_id="project-1", production_control=production, token_factory=lambda: "edge")
    register(app, boundary="DIRECT_CONTINUATION")
    state = app.snapshot()
    inspected = app.inspect_locked_target(
        edge_id="edge-1", expected_production_snapshot_sha256=state["production_snapshot_sha256"],
        expected_continuity_snapshot_sha256=state["continuity_snapshot_sha256"],
    )
    row = inspected["application"]["workspace"]["edges"][0]
    assert row["resolution"]["status"] == "PASS"
    assert row["generation_safe"] is True
    assert row["direct_continuation_human_override_allowed"] is False
    with pytest.raises(ProductError) as exc:
        app.prepare_soft_approval(
            edge_id="edge-1", expected_production_snapshot_sha256=inspected["application"]["production_snapshot_sha256"],
            expected_continuity_snapshot_sha256=inspected["application"]["continuity_snapshot_sha256"],
        )
    assert exc.value.code == "ERR_CONTINUITY_HARD_RULE_NOT_OVERRIDABLE"


def test_crash_after_first_store_requires_exact_completion(tmp_path: Path) -> None:
    production = seed_production(tmp_path)
    def fail(stage: str):
        if stage == "after_continuity_save":
            raise RuntimeError("crash")
    app = Task039ContinuityApplication(
        project_root=tmp_path, project_id="project-1", production_control=production,
        token_factory=lambda: "edge", failure_injector=fail,
    )
    prepared = prepare(app)
    with pytest.raises(RuntimeError):
        app.apply_register_edge(confirmation_id=prepared["confirmation_id"])
    reopened = Task039ContinuityApplication(project_root=tmp_path, project_id="project-1")
    state = reopened.snapshot()
    assert state["recovery"]["state"] == "CONTINUITY_NEW_PRODUCTION_OLD"
    assert state["workspace"]["edges"][0]["generation_safe"] is False
    completed = reopened.apply_recovery(action="COMPLETE")
    assert completed["recovery"]["required"] is False
    assert completed["workspace"]["edges"][0]["edge_id"] == "edge-1"


def test_crash_before_store_write_can_be_abandoned(tmp_path: Path) -> None:
    production = seed_production(tmp_path)
    def fail(stage: str):
        if stage == "after_transaction_prepare":
            raise RuntimeError("crash")
    app = Task039ContinuityApplication(
        project_root=tmp_path, project_id="project-1", production_control=production,
        token_factory=lambda: "edge", failure_injector=fail,
    )
    prepared = prepare(app)
    with pytest.raises(RuntimeError):
        app.apply_register_edge(confirmation_id=prepared["confirmation_id"])
    reopened = Task039ContinuityApplication(project_root=tmp_path, project_id="project-1")
    assert reopened.snapshot()["recovery"]["available_actions"] == ["COMPLETE", "ABANDON"]
    state = reopened.apply_recovery(action="ABANDON")
    assert state["workspace"]["edges"] == []


def test_restart_rejects_checksum_valid_transaction_with_unknown_authority_field(tmp_path: Path) -> None:
    production = seed_production(tmp_path)

    def fail(stage: str):
        if stage == "after_transaction_prepare":
            raise RuntimeError("crash")

    app = Task039ContinuityApplication(
        project_root=tmp_path, project_id="project-1", production_control=production,
        token_factory=lambda: "edge", failure_injector=fail,
    )
    prepared = prepare(app)
    with pytest.raises(RuntimeError):
        app.apply_register_edge(confirmation_id=prepared["confirmation_id"])
    document = json.loads(app.transaction_path.read_text(encoding="utf-8"))
    document["force_complete"] = True
    document = Task039ContinuityApplication._transaction_body(document)
    app.transaction_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        Task039ContinuityApplication(project_root=tmp_path, project_id="project-1").snapshot()
    assert exc.value.code == "ERR_CONTINUITY_TRANSACTION_INVALID"


def test_stale_propagates_and_never_regenerates_or_clears_resolution(tmp_path: Path) -> None:
    production = seed_production(tmp_path, target_same=True)
    app = Task039ContinuityApplication(project_root=tmp_path, project_id="project-1", production_control=production, token_factory=lambda: "edge")
    register(app, boundary="DIRECT_CONTINUATION")
    state = app.snapshot()
    app.inspect_locked_target(
        edge_id="edge-1", expected_production_snapshot_sha256=state["production_snapshot_sha256"],
        expected_continuity_snapshot_sha256=state["continuity_snapshot_sha256"],
    )
    state = app.snapshot()
    result = app.propagate_stale(
        root_slot_id="slot-end", expected_production_snapshot_sha256=state["production_snapshot_sha256"],
        expected_continuity_snapshot_sha256=state["continuity_snapshot_sha256"],
    )
    assert result["automatic_regeneration_started"] is False
    row = result["application"]["workspace"]["edges"][0]
    assert row["target_slot_status"] == "STALE"
    assert row["generation_safe"] is False
    assert row["resolution"]["status"] == "PASS"


def test_concurrent_edge_registration_allows_exactly_one_writer(tmp_path: Path) -> None:
    seed_production(tmp_path)
    first = Task039ContinuityApplication(project_root=tmp_path, project_id="project-1", token_factory=lambda: "first")
    second = Task039ContinuityApplication(project_root=tmp_path, project_id="project-1", token_factory=lambda: "second")
    prepare(first); prepare(second)

    def publish(service, token):
        try:
            service.apply_register_edge(confirmation_id=token)
            return "PASS"
        except ProductError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda item: publish(*item), ((first, "first"), (second, "second"))))
    assert results.count("PASS") == 1
    assert results.count("ERR_CONTINUITY_APPLICATION_SNAPSHOT_CONFLICT") == 1


def test_project_scope_and_slot_kind_fail_closed(tmp_path: Path) -> None:
    production = seed_production(tmp_path)
    with pytest.raises(ProductError) as exc:
        Task039ContinuityApplication(project_root=tmp_path, project_id="other", production_control=production)
    assert exc.value.code == "ERR_CONTINUITY_APPLICATION_PRODUCTION_SCOPE_MISMATCH"
    app = Task039ContinuityApplication(project_root=tmp_path, project_id="project-1")
    state = app.snapshot()
    with pytest.raises(ProductError) as exc:
        app.prepare_register_edge(
            edge_id="bad", from_slot_id="slot-start", to_slot_id="slot-end", boundary_type="SOFT_CONTINUITY",
            character_contract_refs=(), space_contract_refs=(),
            expected_production_snapshot_sha256=state["production_snapshot_sha256"],
            expected_continuity_snapshot_sha256=state["continuity_snapshot_sha256"],
        )
    assert exc.value.code == "ERR_CONTINUITY_APPLICATION_SLOT_KIND"
