from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.dbd_reasoning_dataset_leakage import (
    DbDReasoningDatasetLeakageReport,
    LeakageAuditStatus,
    LeakageFinding,
    LeakageKind,
)
from ai_video_production.dbd_reasoning_dataset_manifest import DatasetSplit
from ai_video_production.dbd_reasoning_offline_evaluation import (
    DbDReasoningOfflineEvaluationHarness,
    OfflineArmEvidence,
    OfflineEvaluationArm,
    OfflineGateStatus,
    admit_dbd_reasoning_offline_evaluation_report,
    admit_offline_arm_evidence,
)


SHA = "sha256:" + "a" * 64
SEEDS = (104729, 130363, 155921)
ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "dbd-reasoning-offline-evaluation-report.schema.json"
MIRROR_PATH = ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA_PATH.name


def _leakage(status: LeakageAuditStatus = LeakageAuditStatus.PASS) -> DbDReasoningDatasetLeakageReport:
    findings = ()
    split_count = 2
    if status is LeakageAuditStatus.FAIL:
        findings = (
            LeakageFinding(
                kind=LeakageKind.MATCH_SPLIT,
                left_segment_id="SEG-" + "1" * 26,
                right_segment_id="SEG-" + "2" * 26,
                left_split=DatasetSplit.TRAIN,
                right_split=DatasetSplit.TEST,
                fingerprint_sha256=SHA,
            ),
        )
    elif status is LeakageAuditStatus.NOT_CONFIRMED:
        split_count = 1
    return DbDReasoningDatasetLeakageReport(
        rights_manifest_sha256=SHA,
        audited_segments_sha256=SHA,
        segment_count=2,
        split_count=split_count,
        findings=findings,
        status=status,
    )


def _arm(arm: OfflineEvaluationArm, **changes: object) -> OfflineArmEvidence:
    refs = {
        OfflineEvaluationArm.BASELINE: "baseline://dbd/r4d-v1",
        OfflineEvaluationArm.GENERIC: "generic://dbd/r4d-v1",
        OfflineEvaluationArm.TUNED: "model-quarantine://dbd/r4d-v1",
    }
    values: dict[str, object] = {
        "arm": arm,
        "binding_ref": refs[arm],
        "binding_sha256": SHA,
        "output_evidence_set_sha256": SHA,
        "sample_count": 10,
        "observation_count": 30,
        "schema_valid_count": 30,
        "unsupported_admitted_fact_count": 0,
        "patch_incompatible_claim_count": 0,
        "citation_required_count": 30,
        "citation_covered_count": 30,
        "secret_pii_leak_count": 0,
        "split_leakage_count": 0,
        "replay_comparison_count": 20,
        "replay_stable_count": 19,
        "safe_negative_count": 10,
        "safe_negative_abstained_count": 10,
        "latency_p95_ms": 250,
        "total_cost_milli": 100,
        "peak_memory_mib": 512,
    }
    values.update(changes)
    return OfflineArmEvidence(**values)


def _report(
    *,
    shared_changes: dict[str, object] | None = None,
    tuned_changes: dict[str, object] | None = None,
):
    shared_changes = shared_changes or {}
    arms = tuple(
        _arm(
            arm,
            **{
                **shared_changes,
                **(tuned_changes or {} if arm is OfflineEvaluationArm.TUNED else {}),
            },
        )
        for arm in OfflineEvaluationArm
    )
    return DbDReasoningOfflineEvaluationHarness.evaluate(
        leakage_report=_leakage(),
        test_sample_set_sha256=SHA,
        seeds=SEEDS,
        arms=arms,
    )


def test_three_arm_evaluation_passes_without_promotion_authority() -> None:
    report = _report()
    assert tuple(item.arm for item in report.evaluations) == tuple(OfflineEvaluationArm)
    assert all(item.status is OfflineGateStatus.PASS for item in report.evaluations)
    assert report.tuned_gate_status is OfflineGateStatus.PASS
    assert report.evaluation_state == "EVIDENCE_ONLY_NO_PROMOTION"
    assert not hasattr(report, "promote")


def test_non_compensating_safety_failure_fails_tuned_arm() -> None:
    report = _report(tuned_changes={"unsupported_admitted_fact_count": 1})
    tuned = report.evaluations[-1]
    assert tuned.status is OfflineGateStatus.FAIL
    assert "UNSUPPORTED_ADMITTED_FACT" in tuned.failure_codes
    assert tuned.schema_valid_milli == 1000


def test_rate_gates_use_floor_milli_boundaries() -> None:
    shared = {"sample_count": 200, "observation_count": 600,
        "citation_required_count": 600, "citation_covered_count": 600,
        "replay_comparison_count": 400, "replay_stable_count": 380,
        "safe_negative_count": 200, "safe_negative_abstained_count": 190}
    passing = _report(shared_changes=shared, tuned_changes={"schema_valid_count": 597})
    assert passing.tuned_gate_status is OfflineGateStatus.PASS
    failing = _report(shared_changes=shared, tuned_changes={"schema_valid_count": 596})
    assert failing.tuned_gate_status is OfflineGateStatus.FAIL
    assert "SCHEMA_VALID_RATE_BELOW_GATE" in failing.evaluations[-1].failure_codes


def test_missing_safe_negative_evidence_is_not_confirmed() -> None:
    report = _report(tuned_changes={"safe_negative_count": 0, "safe_negative_abstained_count": 0})
    assert report.tuned_gate_status is OfflineGateStatus.NOT_CONFIRMED
    assert report.evaluations[-1].safe_negative_abstention_milli is None


def test_failed_or_incomplete_leakage_audit_cannot_enter_r4d() -> None:
    for status in (LeakageAuditStatus.FAIL, LeakageAuditStatus.NOT_CONFIRMED):
        with pytest.raises(ValueError, match="PASS R4C"):
            DbDReasoningOfflineEvaluationHarness.evaluate(
                leakage_report=_leakage(status),
                test_sample_set_sha256=SHA,
                seeds=SEEDS,
                arms=tuple(_arm(arm) for arm in OfflineEvaluationArm),
            )


def test_cohort_seed_coverage_and_canonical_arm_order_fail_closed() -> None:
    valid = tuple(_arm(arm) for arm in OfflineEvaluationArm)
    cases = (
        (valid[1], valid[0], valid[2]),
        (valid[0], replace(valid[1], sample_count=9), valid[2]),
        (valid[0], replace(valid[1], observation_count=29, schema_valid_count=29,
            citation_required_count=29, citation_covered_count=29), valid[2]),
        (valid[0], replace(valid[1], replay_comparison_count=19, replay_stable_count=19), valid[2]),
    )
    for arms in cases:
        with pytest.raises(ValueError):
            DbDReasoningOfflineEvaluationHarness.evaluate(
                leakage_report=_leakage(), test_sample_set_sha256=SHA, seeds=SEEDS, arms=arms
            )
    with pytest.raises(ValueError, match="seeds"):
        DbDReasoningOfflineEvaluationHarness.evaluate(
            leakage_report=_leakage(), test_sample_set_sha256=SHA,
            seeds=(155921, 104729, 130363), arms=valid
        )

    with pytest.raises(ValueError, match="canonical"):
        DbDReasoningOfflineEvaluationHarness.evaluate(
            leakage_report=_leakage(), test_sample_set_sha256=SHA,
            seeds=(1, 2, 3), arms=valid
        )

def test_arm_binding_and_count_forgery_fail_closed() -> None:
    with pytest.raises(ValueError, match="scheme"):
        replace(_arm(OfflineEvaluationArm.TUNED), binding_ref="generic://dbd/forged")
    with pytest.raises(ValueError, match="exceeds"):
        replace(_arm(OfflineEvaluationArm.TUNED), citation_covered_count=31)
    record = _arm(OfflineEvaluationArm.TUNED).to_dict()
    record["sample_count"] = True
    with pytest.raises(ValueError, match="sample_count"):
        admit_offline_arm_evidence(record)


def test_report_schema_mirror_exact_readmission_and_tamper_rejection() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    mirror = json.loads(MIRROR_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    record = _report().to_dict()
    assert mirror == schema
    assert list(Draft202012Validator(schema).iter_errors(record)) == []
    assert admit_dbd_reasoning_offline_evaluation_report(record).to_dict() == record
    with pytest.raises(ValueError):
        admit_dbd_reasoning_offline_evaluation_report({**record, "unexpected": True})
    forged = json.loads(json.dumps(record))
    forged["evaluations"][2]["schema_valid_milli"] = 0
    with pytest.raises(ValueError):
        admit_dbd_reasoning_offline_evaluation_report(forged)
    forged = json.loads(json.dumps(record))
    forged["evaluations"][2]["observation_count"] = 31
    with pytest.raises(ValueError, match="sample/seed"):
        admit_dbd_reasoning_offline_evaluation_report(forged)
    with pytest.raises(ValueError, match="checksum"):
        admit_dbd_reasoning_offline_evaluation_report({**record, "evaluation_report_sha256": SHA})


def test_report_contains_only_aggregate_evidence_and_no_execution_methods() -> None:
    record = _report().to_dict()
    assert "transcript" not in json.dumps(record)
    harness_names = set(dir(DbDReasoningOfflineEvaluationHarness))
    assert not ({"execute", "train", "adopt", "promote"} & harness_names)
