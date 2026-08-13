from __future__ import annotations

import pytest

from ai_video_production.audit_production_binding import AuditProductionControlBinding
from ai_video_production.audit_workspace import Task038AuditWorkspaceService
from ai_video_production.candidate_audit import (
    AuditDimension,
    AuditFinding,
    AuditRecord,
    AuditorKind,
    CandidateAuditRegistry,
    FindingSeverity,
)
from ai_video_production.errors import ProductError
from ai_video_production.production_control import (
    AssetCandidate,
    CandidateLifecycle,
    ProductionControlRegistry,
    SceneAssetSlot,
    SlotKind,
)

SHA = "sha256:" + "a" * 64


def setup_state():
    production = ProductionControlRegistry()
    production.add_slot(SceneAssetSlot("slot-1", "project-1", "scene-1", SlotKind.START_FRAME, True))
    production.add_candidate(AssetCandidate("candidate-1", "slot-1", "asset-1", SHA, 1))
    audits = CandidateAuditRegistry()
    audit = AuditRecord(
        "audit-1", "candidate-1", SHA, ("contract-1",), AuditorKind.AI, "vision-judge", "v1",
        {"CONTRACT": 92.0, "COMPOSITION": 99.0},
        (AuditFinding("finding-1", AuditDimension.GEOMETRY, FindingSeverity.CRITICAL, "DEPTH_REVERSED", "wrong depth", True),),
        ("DEPTH_REVERSED",),
    )
    AuditProductionControlBinding.record_audit(production, audits, audit)
    return production, audits


def test_projection_keeps_ai_score_separate_from_human_authority():
    production, audits = setup_state()
    service = Task038AuditWorkspaceService(production=production, audits=audits)
    row = service.snapshot()["candidates"][0]
    assert row["critical_violation"] is True
    assert row["latest_dimension_scores"]["COMPOSITION"] == 99.0
    assert row["human_decision"] is None
    assert row["available_human_actions"] == ["ACCEPT", "REJECT", "ALTERNATE_USE", "NEEDS_REGENERATION"]
    assert row["ai_score_is_human_decision"] is False


def test_one_shot_accept_confirmation_drives_production_only_after_apply():
    production, audits = setup_state()
    service = Task038AuditWorkspaceService(production=production, audits=audits, token_factory=lambda: "confirm-1")
    prepared = service.prepare_human_decision(candidate_id="candidate-1", decision="ACCEPT")
    assert prepared["critical_violation_present"] is True
    assert production.candidates["candidate-1"].lifecycle_state is CandidateLifecycle.READY_FOR_AUDIT
    applied = service.apply_human_decision(confirmation_id="confirm-1", actor_id="owner")
    assert production.candidates["candidate-1"].lifecycle_state is CandidateLifecycle.ACCEPTED
    assert applied["production_binding"]["human_final_authority_preserved"] is True
    with pytest.raises(ProductError) as exc:
        service.apply_human_decision(confirmation_id="confirm-1", actor_id="owner")
    assert exc.value.code == "ERR_AUDIT_WORKSPACE_CONFIRMATION_INVALID"


def test_needs_regeneration_never_starts_provider_or_changes_lifecycle():
    production, audits = setup_state()
    service = Task038AuditWorkspaceService(production=production, audits=audits, token_factory=lambda: "regen")
    service.prepare_human_decision(candidate_id="candidate-1", decision="NEEDS_REGENERATION")
    result = service.apply_human_decision(confirmation_id="regen", actor_id="owner")
    assert production.candidates["candidate-1"].lifecycle_state is CandidateLifecycle.READY_FOR_AUDIT
    assert result["production_binding"]["regeneration_requested"] is True
    assert result["production_binding"]["automatic_regeneration_started"] is False


def test_confirmation_fails_closed_when_audit_set_changes_after_prepare():
    production, audits = setup_state()
    service = Task038AuditWorkspaceService(production=production, audits=audits, token_factory=lambda: "confirm")
    service.prepare_human_decision(candidate_id="candidate-1", decision="REJECT")
    audits.add_audit(AuditRecord(
        "audit-2", "candidate-1", SHA, ("contract-1",), AuditorKind.HUMAN, "reviewer", None,
        {"CONTRACT": 50.0}, (), ("MANUAL_REVIEW",),
    ))
    with pytest.raises(ProductError) as exc:
        service.apply_human_decision(confirmation_id="confirm", actor_id="owner")
    assert exc.value.code == "ERR_AUDIT_WORKSPACE_CONFIRMATION_STALE"
    assert production.candidates["candidate-1"].lifecycle_state is CandidateLifecycle.READY_FOR_AUDIT


def test_projection_rejects_stale_audit_bytes():
    production, audits = setup_state()
    # Simulate imported corruption after the valid audit.
    audits.audit_records["audit-1"] = AuditRecord(
        "audit-1", "candidate-1", "sha256:" + "b" * 64, ("contract-1",), AuditorKind.AI, "vision-judge", "v1",
        {"CONTRACT": 92.0}, (), (),
    )
    with pytest.raises(ProductError) as exc:
        Task038AuditWorkspaceService(production=production, audits=audits).snapshot()
    assert exc.value.code == "ERR_AUDIT_WORKSPACE_ASSET_HASH_MISMATCH"
