from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

import ai_video_production.dbd_reasoning_dataset_leakage as leakage_module
from ai_video_production.dbd_reasoning_dataset_leakage import (
    DbDReasoningDatasetLeakageAuditor,
    DbDReasoningDatasetLeakageReport,
    LeakageAuditStatus,
    LeakageFinding,
    LeakageKind,
    admit_dbd_reasoning_dataset_leakage_report,
)
from ai_video_production.dbd_reasoning_dataset_manifest import (
    ConsentDecision,
    DatasetRowDisposition,
    DatasetSplit,
    DbDReasoningDatasetRightsEntry,
    DbDReasoningDatasetRightsManifest,
    RightsDecision,
)
from ai_video_production.dbd_reasoning_narration_intake import (
    DbDReasoningNarrationIntakeCandidate,
    NarrationDisposition,
    NarrationRole,
)
from ai_video_production.serialization import sha256_bytes


SHA = "sha256:" + "a" * 64
HEX = "a" * 64
ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "dbd-reasoning-dataset-leakage-report.schema.json"
MIRROR_PATH = ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA_PATH.name


def _entry(index: int, split: DatasetSplit) -> DbDReasoningDatasetRightsEntry:
    digit = str(index)
    return DbDReasoningDatasetRightsEntry(
        candidate_id="CAND-R2D" + digit * 23,
        candidate_sha256=SHA,
        lineage_sha256=SHA,
        human_review_sha256=SHA,
        human_review_ref=f"human-review://sha256/{HEX}",
        match_id="MATCH-" + digit * 26,
        source_group_id=f"group-{index}",
        source_ref=f"media://sha256/{digit * 64}",
        split=split,
        patch_version="9.1.0",
        locale="ja-JP",
        rights_decision=RightsDecision.ADMITTED_FOR_TRAINING,
        rights_ref=f"rights://sha256/{digit * 64}",
        consent_decision=ConsentDecision.EXPLICIT_TRAINING,
        consent_ref=f"consent://sha256/{digit * 64}",
        provenance_ref=f"provenance://sha256/{digit * 64}",
        disposition=DatasetRowDisposition.ELIGIBLE_CANDIDATE,
        reason_codes=(),
    )


def _segment(
    index: int,
    entry: DbDReasoningDatasetRightsEntry,
    manifest: DbDReasoningDatasetRightsManifest,
) -> DbDReasoningNarrationIntakeCandidate:
    digit = str(index)
    text = f"実況{index}"
    return DbDReasoningNarrationIntakeCandidate(
        segment_id="SEG-" + digit * 26,
        rights_candidate_id=entry.candidate_id,
        rights_manifest_sha256=manifest.to_dict()["rights_manifest_sha256"],
        match_id=entry.match_id,
        event_ids=("GEVT-" + digit * 26,),
        context_sha256=SHA,
        source_video_ref=entry.source_ref,
        source_audio_ref=entry.source_ref,
        source_start_us=index * 1000,
        source_end_us_exclusive=index * 1000 + 500,
        speaker_ref=f"speaker://sha256/{digit * 64}",
        asr_revision=1,
        asr_sha256=SHA,
        diarization_revision=1,
        diarization_sha256=SHA,
        original_transcript_sha256=SHA,
        corrected_transcript_sha256=sha256_bytes(text.encode()),
        redacted_transcript=text,
        role=NarrationRole.PLAY_BY_PLAY,
        patch_version="9.1.0",
        human_review_ref=entry.human_review_ref,
        human_review_sha256=entry.human_review_sha256,
        issue_codes=(),
        disposition=NarrationDisposition.ELIGIBLE_CANDIDATE,
    )


def _pass_report() -> DbDReasoningDatasetLeakageReport:
    return DbDReasoningDatasetLeakageReport(
        rights_manifest_sha256=SHA,
        audited_segments_sha256=SHA,
        segment_count=2,
        split_count=2,
        findings=(),
        status=LeakageAuditStatus.PASS,
    )


def test_report_schema_mirror_and_exact_readmission() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    record = _pass_report().to_dict()
    assert list(Draft202012Validator(schema).iter_errors(record)) == []
    assert json.loads(MIRROR_PATH.read_text(encoding="utf-8")) == schema
    assert admit_dbd_reasoning_dataset_leakage_report(record).to_dict() == record


def test_report_tamper_unknown_fields_and_invalid_bounds_fail_closed() -> None:
    record = _pass_report().to_dict()
    with pytest.raises(ValueError, match="checksum"):
        admit_dbd_reasoning_dataset_leakage_report({**record, "report_sha256": SHA})
    with pytest.raises(ValueError, match="checksum"):
        admit_dbd_reasoning_dataset_leakage_report({**record, "audited_segments_sha256": "sha256:" + "b" * 64})
    with pytest.raises(ValueError, match="shape"):
        admit_dbd_reasoning_dataset_leakage_report({**record, "unexpected": True})
    with pytest.raises(ValueError, match="segment_count"):
        replace(_pass_report(), segment_count=0)
    with pytest.raises(ValueError, match="split_count"):
        replace(_pass_report(), split_count=4)


def test_finding_requires_valid_ids_and_cross_split_evidence() -> None:
    values = dict(
        kind=LeakageKind.MATCH_SPLIT,
        left_segment_id="SEG-" + "1" * 26,
        right_segment_id="SEG-" + "2" * 26,
        left_split=DatasetSplit.TRAIN,
        right_split=DatasetSplit.TEST,
        fingerprint_sha256=SHA,
    )
    assert LeakageFinding(**values).kind is LeakageKind.MATCH_SPLIT
    with pytest.raises(ValueError, match="invalid SEG"):
        LeakageFinding(**{**values, "left_segment_id": "segment-1"})
    with pytest.raises(ValueError, match="cross"):
        LeakageFinding(**{**values, "right_split": DatasetSplit.TRAIN})


def test_aggregate_transcript_ceiling_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    first = _entry(1, DatasetSplit.TRAIN)
    second = _entry(2, DatasetSplit.TEST)
    manifest = DbDReasoningDatasetRightsManifest("MAN-" + "0" * 26, 1, (first, second))
    monkeypatch.setattr(leakage_module, "MAX_TOTAL_NORMALIZED_CHARS", 1)
    with pytest.raises(ValueError, match="aggregate audit ceiling"):
        DbDReasoningDatasetLeakageAuditor.audit(
            manifest,
            (_segment(1, first, manifest), _segment(2, second, manifest)),
        )
