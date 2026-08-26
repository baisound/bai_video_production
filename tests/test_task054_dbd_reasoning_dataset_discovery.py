from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import pytest

from ai_video_production.dbd_reasoning_dataset_discovery import (
    DISCOVERY_POLICY_SHA256,
    DISCOVERY_STATE,
    DatasetDiscoveryItemStatus,
    DatasetDiscoveryStatus,
    admit_dataset_discovery_report,
    discover_task054_dataset_evidence,
)
from ai_video_production.dbd_reasoning_dataset_manifest import (
    ConsentDecision,
    DatasetRowDisposition,
    DatasetSplit,
    DbDReasoningDatasetRightsEntry,
    DbDReasoningDatasetRightsManifest,
    RightsDecision,
)


SHA = "sha256:" + "a" * 64
HEX = "a" * 64
MANIFEST = "MAN-" + "0" * 26
OBSERVED_AT = "2026-08-26T06:00:00Z"


def _entry(index: int = 0, **changes: object) -> DbDReasoningDatasetRightsEntry:
    digit = str(index)
    values: dict[str, object] = {
        "candidate_id": "CAND-R2D" + digit * 23,
        "candidate_sha256": SHA,
        "lineage_sha256": SHA,
        "human_review_sha256": SHA,
        "human_review_ref": f"human-review://sha256/{HEX}",
        "match_id": "MATCH-" + digit * 26,
        "source_group_id": f"source-group-{index}",
        "source_ref": f"media://sha256/{HEX}",
        "split": DatasetSplit.TRAIN,
        "patch_version": "9.1.0",
        "locale": "ja-JP",
        "rights_decision": RightsDecision.ADMITTED_FOR_TRAINING,
        "rights_ref": f"rights://sha256/{HEX}",
        "consent_decision": ConsentDecision.EXPLICIT_TRAINING,
        "consent_ref": f"consent://sha256/{HEX}",
        "provenance_ref": f"provenance://sha256/{HEX}",
        "disposition": DatasetRowDisposition.ELIGIBLE_CANDIDATE,
        "reason_codes": (),
    }
    values.update(changes)
    return DbDReasoningDatasetRightsEntry(**values)


def _manifest(*entries: DbDReasoningDatasetRightsEntry) -> DbDReasoningDatasetRightsManifest:
    return DbDReasoningDatasetRightsManifest(MANIFEST, 1, entries or (_entry(),))


def _write_manifest(root: Path, manifest: DbDReasoningDatasetRightsManifest | None = None, *, revision_dir: str = "1") -> Path:
    path = root / MANIFEST / revision_dir / "manifest.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps((manifest or _manifest()).to_dict()), encoding="utf-8")
    return path


def test_missing_and_empty_roots_are_body_free_no_manifest_reports(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    report = discover_task054_dataset_evidence(missing, observed_at=OBSERVED_AT)
    assert report.status is DatasetDiscoveryStatus.NO_MANIFEST_FOUND
    assert report.detail_code == "ROOT_NOT_FOUND"
    assert report.items == ()
    missing.mkdir()
    empty = discover_task054_dataset_evidence(missing, observed_at=OBSERVED_AT)
    assert empty.status is DatasetDiscoveryStatus.NO_MANIFEST_FOUND
    assert empty.detail_code == "NO_MANIFEST_FOUND"
    payload = json.dumps(empty.to_dict())
    assert str(missing) not in payload
    assert empty.discovery_policy_sha256 == DISCOVERY_POLICY_SHA256
    assert empty.state == DISCOVERY_STATE


def test_exact_manifest_is_read_only_admitted_candidate_evidence(tmp_path: Path) -> None:
    manifest = _manifest(
        _entry(0),
        _entry(
            1,
            split=DatasetSplit.VALIDATION,
            rights_decision=RightsDecision.UNKNOWN,
            disposition=DatasetRowDisposition.NEEDS_REVIEW,
            reason_codes=("RIGHTS_UNKNOWN",),
        ),
        _entry(
            2,
            split=DatasetSplit.TEST,
            rights_decision=RightsDecision.REJECTED,
            disposition=DatasetRowDisposition.REJECTED,
            reason_codes=("RIGHTS_REJECTED",),
        ),
    )
    _write_manifest(tmp_path, manifest)
    report = discover_task054_dataset_evidence(tmp_path, observed_at=OBSERVED_AT)
    assert report.status is DatasetDiscoveryStatus.DISCOVERED_CANDIDATE_ONLY
    assert report.detail_code == "PASS"
    assert len(report.items) == 1
    item = report.items[0]
    assert item.status is DatasetDiscoveryItemStatus.ADMITTED
    assert item.manifest_id == MANIFEST and item.revision == 1
    assert (item.entry_count, item.eligible_candidate_count, item.needs_review_count, item.rejected_count) == (3, 1, 1, 1)
    assert (item.train_count, item.validation_count, item.test_count) == (1, 1, 1)
    payload = report.to_dict()
    assert "training_eligible" not in json.dumps(payload)
    assert str(tmp_path) not in json.dumps(payload)
    assert admit_dataset_discovery_report(payload) == report


def test_invalid_body_and_identity_crossing_are_digest_only_blockers(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path)
    path.write_text('{"password":"do-not-retain","raw_path":"C:/private/video.mp4"}', encoding="utf-8")
    report = discover_task054_dataset_evidence(tmp_path, observed_at=OBSERVED_AT)
    assert report.status is DatasetDiscoveryStatus.BLOCKED_INVALID_EVIDENCE
    item = report.items[0]
    assert item.status is DatasetDiscoveryItemStatus.INVALID
    assert item.detail_code == "MANIFEST_ADMISSION_FAILED"
    assert item.manifest_id is None and item.rights_manifest_sha256 is None
    public = json.dumps(report.to_dict())
    assert "do-not-retain" not in public and "private/video" not in public

    path.write_text(json.dumps(_manifest().to_dict()), encoding="utf-8")
    crossed = tmp_path / "other" / "1" / "manifest.json"
    crossed.parent.mkdir(parents=True)
    crossed.write_bytes(path.read_bytes())
    crossed_report = discover_task054_dataset_evidence(tmp_path, observed_at=OBSERVED_AT)
    assert crossed_report.status is DatasetDiscoveryStatus.BLOCKED_INVALID_EVIDENCE
    assert any(value.detail_code == "MANIFEST_ADMISSION_FAILED" for value in crossed_report.items)


def test_unexpected_layout_and_size_limit_fail_closed(tmp_path: Path) -> None:
    shallow = tmp_path / "manifest.json"
    shallow.write_text("{}", encoding="utf-8")
    report = discover_task054_dataset_evidence(tmp_path, observed_at=OBSERVED_AT)
    assert report.status is DatasetDiscoveryStatus.BLOCKED_INVALID_EVIDENCE
    assert report.items[0].detail_code == "UNEXPECTED_MANIFEST_LAYOUT"

    shallow.unlink()
    path = _write_manifest(tmp_path)
    path.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    oversized = discover_task054_dataset_evidence(tmp_path, observed_at=OBSERVED_AT)
    assert oversized.status is DatasetDiscoveryStatus.BLOCKED_INVALID_EVIDENCE
    assert oversized.items[0].detail_code == "MANIFEST_SIZE_LIMIT"


def test_symlink_root_is_rejected_without_following(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    _write_manifest(target)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink is unavailable")
    report = discover_task054_dataset_evidence(alias, observed_at=OBSERVED_AT)
    assert report.status is DatasetDiscoveryStatus.BLOCKED_INVALID_EVIDENCE
    assert report.items[0].detail_code == "UNSAFE_DATASET_ROOT"


def test_report_tamper_and_authority_forge_fail_closed(tmp_path: Path) -> None:
    _write_manifest(tmp_path)
    report = discover_task054_dataset_evidence(tmp_path, observed_at=OBSERVED_AT)
    tampered = report.to_dict()
    tampered["status"] = "NO_MANIFEST_FOUND"
    with pytest.raises(ValueError):
        admit_dataset_discovery_report(tampered)
    with pytest.raises(ValueError, match="cannot grant"):
        replace(report, state="TRAINING_AUTHORIZED")


def test_noncanonical_revision_directory_and_discovery_limit_fail_closed(tmp_path: Path, monkeypatch) -> None:
    _write_manifest(tmp_path, revision_dir="01")
    report = discover_task054_dataset_evidence(tmp_path, observed_at=OBSERVED_AT)
    assert report.status is DatasetDiscoveryStatus.BLOCKED_INVALID_EVIDENCE

    import ai_video_production.dbd_reasoning_dataset_discovery as discovery
    monkeypatch.setattr(discovery, "MAX_DISCOVERY_MANIFESTS", 1)
    second = tmp_path / "other" / "2" / "manifest.json"
    second.parent.mkdir(parents=True)
    second.write_text("{}", encoding="utf-8")
    limited = discover_task054_dataset_evidence(tmp_path, observed_at=OBSERVED_AT)
    assert limited.status is DatasetDiscoveryStatus.BLOCKED_INVALID_EVIDENCE
    assert limited.items[0].detail_code == "DISCOVERY_LIMIT"


def test_directory_scan_limit_fails_closed(tmp_path: Path, monkeypatch) -> None:
    import ai_video_production.dbd_reasoning_dataset_discovery as discovery

    monkeypatch.setattr(discovery, "MAX_DISCOVERY_DIRECTORIES", 0)
    report = discover_task054_dataset_evidence(tmp_path, observed_at=OBSERVED_AT)
    assert report.status is DatasetDiscoveryStatus.BLOCKED_INVALID_EVIDENCE
    assert report.items[0].detail_code == "DIRECTORY_SCAN_LIMIT"


def test_walk_error_is_body_free_and_fails_closed(tmp_path: Path, monkeypatch) -> None:
    import ai_video_production.dbd_reasoning_dataset_discovery as discovery

    def failed_walk(root: Path, *, topdown: bool, followlinks: bool, onerror):
        onerror(OSError("C:/private/dataset"))
        return iter(())

    monkeypatch.setattr(discovery.os, "walk", failed_walk)
    report = discover_task054_dataset_evidence(tmp_path, observed_at=OBSERVED_AT)
    assert report.status is DatasetDiscoveryStatus.BLOCKED_INVALID_EVIDENCE
    assert report.items[0].detail_code == "ROOT_READ_ERROR"
    assert "private/dataset" not in json.dumps(report.to_dict())


def test_schema_mirror_and_runtime_reports_are_exact(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    canonical = root / "schemas" / "dbd-reasoning-dataset-discovery-report.schema.json"
    mirror = root / "src" / "ai_video_production" / "schema_resources" / canonical.name
    assert canonical.read_bytes() == mirror.read_bytes()
    schema = json.loads(canonical.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    _write_manifest(tmp_path)
    report = discover_task054_dataset_evidence(tmp_path, observed_at=OBSERVED_AT)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(report.to_dict())
    forged_blocked = report.to_dict()
    forged_blocked["status"] = "BLOCKED_INVALID_EVIDENCE"
    forged_blocked["detail_code"] = "INVALID_EVIDENCE"
    with pytest.raises(Exception):
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(forged_blocked)
    invalid = report.to_dict()
    invalid["state"] = "TRAINING_AUTHORIZED"
    with pytest.raises(Exception):
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(invalid)
