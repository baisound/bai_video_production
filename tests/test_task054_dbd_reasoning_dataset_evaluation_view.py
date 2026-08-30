from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ai_video_production.dbd_reasoning_dataset_evaluation_view import (
    EvaluationArmView, EvidenceStageStatus,
    build_dataset_evaluation_snapshot,
)
from ai_video_production.dbd_reasoning_dataset_leakage import (
    DbDReasoningDatasetLeakageReport, LeakageAuditStatus,
)
from ai_video_production.dbd_reasoning_dataset_manifest import (
    ConsentDecision, DatasetRowDisposition, DatasetSplit, DbDReasoningDatasetRightsEntry,
    DbDReasoningDatasetRightsManifest, RightsDecision,
)


SHA = "sha256:" + "a" * 64
HEX = "a" * 64
MATCH = "MATCH-" + "0" * 26
MANIFEST = "MAN-" + "0" * 26


def _entry(index: int, split: DatasetSplit, *, eligible: bool = True):
    return DbDReasoningDatasetRightsEntry(
        candidate_id="CAND-R2D" + str(index) * 23, candidate_sha256=SHA,
        lineage_sha256=SHA, human_review_sha256=SHA,
        human_review_ref=f"human-review://sha256/{HEX}", match_id=MATCH,
        source_group_id=f"source-group-{index}", source_ref=f"media://sha256/{HEX}",
        split=split, patch_version="9.1.0", locale="ja-JP",
        rights_decision=RightsDecision.ADMITTED_FOR_TRAINING if eligible else RightsDecision.UNKNOWN,
        rights_ref=f"rights://sha256/{HEX}",
        consent_decision=ConsentDecision.EXPLICIT_TRAINING,
        consent_ref=f"consent://sha256/{HEX}", provenance_ref=f"provenance://sha256/{HEX}",
        disposition=DatasetRowDisposition.ELIGIBLE_CANDIDATE if eligible else DatasetRowDisposition.NEEDS_REVIEW,
        reason_codes=() if eligible else ("RIGHTS_UNKNOWN",),
    )


def _manifest():
    return DbDReasoningDatasetRightsManifest(MANIFEST, 3, (
        _entry(0, DatasetSplit.TRAIN), _entry(1, DatasetSplit.VALIDATION, eligible=False),
        _entry(2, DatasetSplit.TEST),
    ))


def test_dataset_view_counts_and_locks_test_split() -> None:
    snapshot = build_dataset_evaluation_snapshot(_manifest())
    train, validation, test = snapshot.splits
    assert (train.total_count, train.eligible_count, train.needs_review_count) == (1, 1, 0)
    assert (validation.total_count, validation.eligible_count, validation.needs_review_count) == (1, 0, 1)
    assert test.target_text_visible is False
    assert test.editable is False
    assert snapshot.evaluation_status is EvidenceStageStatus.NOT_AVAILABLE
    assert snapshot.adoption_enabled is False
    assert snapshot.promotion_enabled is False


def test_matching_leakage_report_is_visible_but_never_adopts() -> None:
    manifest = _manifest()
    leakage = DbDReasoningDatasetLeakageReport(
        rights_manifest_sha256=manifest.to_dict()["rights_manifest_sha256"],
        audited_segments_sha256=SHA, segment_count=3, split_count=3,
        findings=(), status=LeakageAuditStatus.PASS,
    )
    snapshot = build_dataset_evaluation_snapshot(manifest, leakage_report=leakage)
    assert snapshot.leakage_status == "PASS"
    assert snapshot.leakage_finding_count == 0
    assert snapshot.state == "READ_ONLY_EVIDENCE_NO_ADOPTION_OR_PROMOTION"


def test_crossed_leakage_manifest_fails_closed() -> None:
    leakage = DbDReasoningDatasetLeakageReport(
        rights_manifest_sha256="sha256:" + "b" * 64,
        audited_segments_sha256=SHA, segment_count=3, split_count=3,
        findings=(), status=LeakageAuditStatus.PASS,
    )
    with pytest.raises(ValueError, match="crosses Dataset manifest"):
        build_dataset_evaluation_snapshot(_manifest(), leakage_report=leakage)


def test_snapshot_cannot_enable_adoption_or_promotion() -> None:
    snapshot = build_dataset_evaluation_snapshot(_manifest())
    with pytest.raises(ValueError, match="cannot grant"):
        replace(snapshot, adoption_enabled=True)
    with pytest.raises(ValueError, match="cannot grant"):
        replace(snapshot, promotion_enabled=True)


def test_snapshot_rejects_inconsistent_stage_visibility() -> None:
    snapshot = build_dataset_evaluation_snapshot(_manifest())
    with pytest.raises(ValueError, match="available evaluation requires"):
        replace(snapshot, evaluation_status=EvidenceStageStatus.AVAILABLE)
    with pytest.raises(ValueError, match="available blind review requires"):
        replace(snapshot, blind_review_status=EvidenceStageStatus.AVAILABLE)
    with pytest.raises(ValueError, match="unavailable blind review cannot"):
        replace(snapshot, blind_sample_count=1)


def test_evaluation_arm_projection_rejects_out_of_range_metrics() -> None:
    with pytest.raises(ValueError, match="between 0 and 1000"):
        EvaluationArmView(
            arm="TUNED",
            status="PASS",
            sample_count=1,
            schema_valid_milli=1001,
            citation_coverage_milli=1000,
            replay_stability_milli=1000,
            safe_negative_abstention_milli=1000,
            failure_codes=(),
        )


def test_japanese_panel_has_locked_test_and_no_authority_copy() -> None:
    source = Path("src/ai_video_production/dbd_reasoning_dataset_evaluation_view_ui.py").read_text(encoding="utf-8")
    assert "Test splitの期待文は表示せず" in source
    assert "Dataset採用: 不可" in source
    assert "モデル昇格: Owner判断が必要" in source
    assert "Evidence閲覧専用" in source
