from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.candidate_audit import (
    AuditDimension,
    AuditFinding,
    AuditRecord,
    AuditorKind,
    CandidateAuditRegistry,
    FindingSeverity,
    HumanCandidateDecision,
    HumanDecision,
)
from ai_video_production.candidate_audit_store import CandidateAuditSnapshotStore
from ai_video_production.errors import ProductError
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


SHA = "sha256:" + "b" * 64


def registry() -> CandidateAuditRegistry:
    value = CandidateAuditRegistry()
    value.add_audit(AuditRecord(
        "audit-1", "candidate-1", SHA, ("contract-1",), AuditorKind.AI, "vision-judge", "v1",
        {"CONTRACT": 88.0},
        (AuditFinding("finding-1", AuditDimension.GEOMETRY, FindingSeverity.CRITICAL, "DEPTH_ORDER_REVERSED", "monitor is behind actor", True),),
        ("DEPTH_ORDER_REVERSED",),
    ))
    value.add_human_decision(HumanDecision(
        "decision-1", "candidate-1", ("audit-1",), HumanCandidateDecision.NEEDS_REGENERATION, "owner", ("DEPTH_ORDER_REVERSED",)
    ))
    return value


def test_audit_snapshot_round_trip_preserves_ai_and_human_separation(tmp_path: Path):
    path = tmp_path / "audit.json"
    CandidateAuditSnapshotStore.save(path, registry())
    loaded = CandidateAuditSnapshotStore.load(path)
    history = loaded.candidate_history("candidate-1")
    assert history["audits"][0]["critical_violation"] is True
    assert history["human_decisions"][0]["decision"] == "NEEDS_REGENERATION"


def test_existing_audit_snapshot_requires_compare_and_swap(tmp_path: Path):
    path = tmp_path / "audit.json"
    value = registry()
    CandidateAuditSnapshotStore.save(path, value)
    with pytest.raises(ProductError) as exc:
        CandidateAuditSnapshotStore.save(path, value)
    assert exc.value.code == "ERR_AUDIT_SNAPSHOT_CAS_REQUIRED"


def test_tampered_nested_audit_record_is_detected_even_if_snapshot_hash_recomputed(tmp_path: Path):
    path = tmp_path / "audit.json"
    doc = CandidateAuditSnapshotStore.snapshot(registry())
    doc["audits"][0]["dimension_scores"]["CONTRACT"] = 99.0
    body = {k: v for k, v in doc.items() if k != "snapshot_sha256"}
    doc["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        CandidateAuditSnapshotStore.load(path)
    assert exc.value.code == "ERR_AUDIT_RECORD_CHECKSUM"


def test_decision_reference_integrity_is_revalidated_on_load(tmp_path: Path):
    path = tmp_path / "audit.json"
    doc = CandidateAuditSnapshotStore.snapshot(registry())
    doc["human_decisions"][0]["audit_refs"] = ["missing-audit"]
    body = {k: v for k, v in doc.items() if k != "snapshot_sha256"}
    doc["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        CandidateAuditSnapshotStore.load(path)
    assert exc.value.code == "ERR_AUDIT_REFERENCE_NOT_FOUND"
