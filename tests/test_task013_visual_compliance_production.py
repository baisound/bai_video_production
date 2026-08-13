from __future__ import annotations

import pytest

from ai_video_production.candidate_audit import CandidateAuditRegistry
from ai_video_production.errors import ProductError
from ai_video_production.production_control import (
    AssetCandidate,
    CandidateLifecycle,
    ProductionControlRegistry,
    SceneAssetSlot,
    SlotKind,
)
from ai_video_production.visual_compliance import (
    CoordinateConvention,
    VisualCheckState,
    VisualComplianceContract,
    VisualComplianceGate,
    VisualContractCheck,
    VisualScoreSet,
)
from ai_video_production.visual_compliance_production import VisualComplianceProductionControlService


SHA = "sha256:" + "a" * 64
OTHER_SHA = "sha256:" + "b" * 64


def production() -> ProductionControlRegistry:
    value = ProductionControlRegistry()
    value.add_slot(SceneAssetSlot("slot-1", "project-1", "scene-1", SlotKind.START_FRAME, True))
    value.add_candidate(AssetCandidate("candidate-1", "slot-1", "asset-1", SHA, 1))
    return value


def contract():
    return VisualComplianceContract(
        "contract-1", 1, "scene-1",
        (
            VisualContractCheck("depth.order", "monitor foreground", True),
            VisualContractCheck("identity", "identity stable", False),
        ),
        CoordinateConvention.VIEWER,
    )


def decision(depth: VisualCheckState, *, sha: str = SHA):
    return VisualComplianceGate.evaluate(
        contract(),
        candidate_id="candidate-1",
        candidate_asset_sha256=sha,
        observed_checks={"depth.order": depth, "identity": VisualCheckState.PASS},
        scores=VisualScoreSet(0.95, 0.9, 0.9, 0.99),
        failure_codes=(() if depth is VisualCheckState.PASS else ("SPATIAL_RELATION_FAILURE",)),
        inspector_kind="VISION_JUDGE",
    )


def test_visual_pass_becomes_audit_ready_not_automatic_accept():
    prod = production(); audits = CandidateAuditRegistry()
    result = VisualComplianceProductionControlService.record_inspection(
        decision(VisualCheckState.PASS), audit_id="audit-1", auditor_id="vision-judge", auditor_version="v1",
        production=prod, audits=audits,
    )
    assert result.critical_pass is True
    assert result.candidate_lifecycle is CandidateLifecycle.READY_FOR_AUDIT
    assert result.to_dict()["automatic_candidate_accept"] is False
    assert not audits.decisions


def test_critical_visual_failure_is_recorded_but_does_not_auto_reject_or_regenerate():
    prod = production(); audits = CandidateAuditRegistry()
    result = VisualComplianceProductionControlService.record_inspection(
        decision(VisualCheckState.FAIL), audit_id="audit-1", auditor_id="vision-judge", auditor_version="v1",
        production=prod, audits=audits,
    )
    assert result.critical_pass is False
    assert prod.candidates["candidate-1"].lifecycle_state is CandidateLifecycle.READY_FOR_AUDIT
    body = result.to_dict()
    assert body["automatic_candidate_reject"] is False
    assert body["automatic_regeneration_started"] is False
    assert audits.audit_records["audit-1"].failure_codes == ("SPATIAL_RELATION_FAILURE",)


def test_visual_inspection_of_stale_or_wrong_asset_bytes_is_rejected():
    prod = production(); audits = CandidateAuditRegistry()
    with pytest.raises(ProductError) as exc:
        VisualComplianceProductionControlService.record_inspection(
            decision(VisualCheckState.PASS, sha=OTHER_SHA), audit_id="audit-1", auditor_id="vision-judge", auditor_version="v1",
            production=prod, audits=audits,
        )
    assert exc.value.code == "ERR_AUDIT_PRODUCTION_ASSET_HASH_MISMATCH"
    assert prod.candidates["candidate-1"].lifecycle_state is CandidateLifecycle.CREATED
    assert not audits.audit_records
