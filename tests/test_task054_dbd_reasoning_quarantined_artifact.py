from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import pytest

from ai_video_production.dbd_reasoning_dataset_leakage import DbDReasoningDatasetLeakageReport, LeakageAuditStatus
from ai_video_production.dbd_reasoning_offline_evaluation import (
    DbDReasoningOfflineEvaluationHarness, OfflineArmEvidence, OfflineEvaluationArm,
)
from ai_video_production.dbd_reasoning_quarantined_artifact import (
    ArtifactFileEvidence, ArtifactFileRole, admit_quarantined_artifact_manifest,
    artifact_role_set_sha256, seal_quarantined_artifact,
)


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
ART_ID = "ART-01ARZ3NDEKTSV4RRFFQ69G5FAV"
QUARANTINE = "model-quarantine://task054/01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _report(*, tuned_safe_count: int = 10):
    leakage = DbDReasoningDatasetLeakageReport(
        rights_manifest_sha256=SHA_A, audited_segments_sha256=SHA_B,
        segment_count=10, split_count=3, findings=(), status=LeakageAuditStatus.PASS,
    )
    refs = {
        OfflineEvaluationArm.BASELINE: "baseline://dbd/r6c",
        OfflineEvaluationArm.GENERIC: "generic://dbd/r6c",
        OfflineEvaluationArm.TUNED: "model-quarantine://dbd/r6c",
    }
    digests = {
        OfflineEvaluationArm.BASELINE: SHA_A,
        OfflineEvaluationArm.GENERIC: SHA_B,
        OfflineEvaluationArm.TUNED: SHA_C,
    }
    arms = tuple(OfflineArmEvidence(
        arm=arm, binding_ref=refs[arm], binding_sha256=digests[arm],
        output_evidence_set_sha256=digests[arm], sample_count=10,
        observation_count=30, schema_valid_count=30,
        unsupported_admitted_fact_count=0, patch_incompatible_claim_count=0,
        citation_required_count=30, citation_covered_count=30,
        secret_pii_leak_count=0, split_leakage_count=0,
        replay_comparison_count=20, replay_stable_count=20,
        safe_negative_count=tuned_safe_count if arm is OfflineEvaluationArm.TUNED else 10,
        safe_negative_abstained_count=tuned_safe_count if arm is OfflineEvaluationArm.TUNED else 10,
        latency_p95_ms=200, total_cost_milli=100, peak_memory_mib=512,
    ) for arm in OfflineEvaluationArm)
    return DbDReasoningOfflineEvaluationHarness.evaluate(
        leakage_report=leakage, test_sample_set_sha256=SHA_D,
        seeds=(104729, 130363, 155921), arms=arms,
    )


def _files():
    return (
        ArtifactFileEvidence("adapter/config.json", ArtifactFileRole.CONFIG, 10, SHA_A),
        ArtifactFileEvidence("adapter/model.safetensors", ArtifactFileRole.ADAPTER, 100, SHA_B),
    )


def _manifest(**changes: object):
    values: dict[str, object] = {
        "artifact_manifest_id": ART_ID,
        "quarantine_ref": QUARANTINE,
        "base_model_ref": "model://registry/qwen-base",
        "base_model_sha256": SHA_A,
        "adapter_ref": "model-adapter://registry/task054/dbd-ja",
        "adapter_sha256": artifact_role_set_sha256(_files(), ArtifactFileRole.ADAPTER),
        "files": _files(),
        "training_dataset_sha256": SHA_C,
        "training_recipe_sha256": SHA_D,
        "offline_report": _report(),
        "sealed_at": "2026-08-25T02:00:00Z",
    }
    values.update(changes)
    return seal_quarantined_artifact(**values)


def test_pass_evaluation_seals_body_free_quarantined_manifest() -> None:
    manifest = _manifest()
    assert manifest.total_bytes == 110
    assert manifest.adapter_sha256 == artifact_role_set_sha256(_files(), ArtifactFileRole.ADAPTER)
    assert manifest.tuned_binding_sha256 == SHA_C
    assert manifest.state == "QUARANTINED_EVALUATED_NO_APPROVAL_OR_ACTIVATION"
    assert admit_quarantined_artifact_manifest(manifest.to_dict()) == manifest
    assert "safetensors" not in str(manifest.to_dict()).casefold() or "model.safetensors" in str(manifest.to_dict())


def test_adapter_file_digest_must_match_manifest() -> None:
    files = (
        ArtifactFileEvidence("adapter/config.json", ArtifactFileRole.CONFIG, 10, SHA_A),
        ArtifactFileEvidence("adapter/model.bin", ArtifactFileRole.ADAPTER, 100, SHA_C),
    )
    with pytest.raises(ValueError, match="adapter role set"):
        _manifest(files=files)


def test_sharded_adapter_uses_canonical_role_set_digest() -> None:
    files = (
        ArtifactFileEvidence("adapter/model-0001.safetensors", ArtifactFileRole.ADAPTER, 50, SHA_A),
        ArtifactFileEvidence("adapter/model-0002.safetensors", ArtifactFileRole.ADAPTER, 50, SHA_B),
    )
    manifest = _manifest(
        files=files,
        adapter_sha256=artifact_role_set_sha256(files, ArtifactFileRole.ADAPTER),
    )
    assert len(manifest.files) == 2


def test_paths_are_sorted_unique_relative_and_ascii_safe() -> None:
    with pytest.raises(ValueError, match="logical_path"):
        ArtifactFileEvidence("../model.bin", ArtifactFileRole.ADAPTER, 1, SHA_A)
    with pytest.raises(ValueError, match="sorted"):
        _manifest(files=tuple(reversed(_files())))
    duplicate = (_files()[0], _files()[0], _files()[1])
    with pytest.raises(ValueError, match="sorted"):
        _manifest(files=duplicate)


def test_manifest_cannot_approve_or_activate() -> None:
    with pytest.raises(ValueError, match="cannot approve"):
        replace(_manifest(), state="APPROVED")


def test_crossed_quarantine_adapter_identity_fails() -> None:
    with pytest.raises(ValueError, match="crosses quarantine"):
        _manifest(quarantine_ref="model-quarantine://task054/01BX5ZZKBKACTAV9WEVGEMMVRZ")


def test_failed_tuned_evaluation_cannot_be_sealed() -> None:
    with pytest.raises(ValueError, match="PASS TUNED"):
        _manifest(offline_report=_report(tuned_safe_count=0))


def test_manifest_checksum_and_lineage_tamper_fail_closed() -> None:
    payload = _manifest().to_dict()
    payload["training_recipe_sha256"] = SHA_A
    with pytest.raises(ValueError, match="not canonical"):
        admit_quarantined_artifact_manifest(payload)


def test_manifest_schema_and_packaged_mirror_are_exact() -> None:
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "schemas" / "dbd-reasoning-quarantined-artifact-manifest.schema.json"
    mirror_path = root / "src" / "ai_video_production" / "schema_resources" / schema_path.name
    assert schema_path.read_bytes() == mirror_path.read_bytes()
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    manifest = _manifest()
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(manifest.to_dict())
    invalid = manifest.to_dict()
    invalid["state"] = "APPROVED"
    with pytest.raises(Exception):
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(invalid)
