from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import pytest

from ai_video_production.dbd_reasoning_dataset_discovery import (
    DISCOVERY_POLICY_SHA256,
    DISCOVERY_STATE,
    DatasetDiscoveryItem,
    DatasetDiscoveryItemStatus,
    DatasetDiscoveryReport,
    DatasetDiscoveryStatus,
)
from ai_video_production.dbd_reasoning_dataset_preflight import (
    PREFLIGHT_STATE,
    DatasetEvidencePreflightMode,
    DatasetEvidencePreflightStatus,
    admit_dataset_evidence_preflight,
    build_dataset_evidence_preflight,
)


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
MANIFEST = "MAN-" + "0" * 26
OBSERVED_AT = "2026-08-26T06:00:00Z"
CREATED_AT = "2026-08-26T08:00:00Z"


def _item(*, eligible: int = 1) -> DatasetDiscoveryItem:
    needs_review = 2 if eligible == 0 else 1
    rejected = 1
    entry_count = eligible + needs_review + rejected
    return DatasetDiscoveryItem(
        logical_path_sha256=SHA_A,
        observation_sha256=SHA_B,
        status=DatasetDiscoveryItemStatus.ADMITTED,
        detail_code="PASS",
        manifest_id=MANIFEST,
        revision=3,
        rights_manifest_sha256=SHA_C,
        entry_count=entry_count,
        eligible_candidate_count=eligible,
        needs_review_count=needs_review,
        rejected_count=rejected,
        train_count=1,
        validation_count=1,
        test_count=entry_count - 2,
    )


def _report(*, eligible: int = 1) -> DatasetDiscoveryReport:
    return DatasetDiscoveryReport(
        observed_at=OBSERVED_AT,
        root_observation_sha256=SHA_A,
        discovery_policy_sha256=DISCOVERY_POLICY_SHA256,
        status=DatasetDiscoveryStatus.DISCOVERED_CANDIDATE_ONLY,
        detail_code="PASS",
        items=(_item(eligible=eligible),),
        state=DISCOVERY_STATE,
    )


def _selection() -> dict[str, object]:
    return {
        "selected_manifest_id": MANIFEST,
        "selected_revision": 3,
        "selected_rights_manifest_sha256": SHA_C,
    }


@pytest.mark.parametrize(
    "mode",
    [
        DatasetEvidencePreflightMode.CONFIRMATION_ONLY,
        DatasetEvidencePreflightMode.LEARNING_PREPARATION,
    ],
)
def test_discovered_report_requires_explicit_operator_selection(mode: DatasetEvidencePreflightMode) -> None:
    result = build_dataset_evidence_preflight(
        _report().to_dict(),
        created_at=CREATED_AT,
        mode=mode,
    )
    assert result.status is DatasetEvidencePreflightStatus.SELECTION_REQUIRED
    assert result.detail_code == "SELECT_DATASET_REVISION"
    assert result.selected_manifest_id is None
    assert result.entry_count == 0
    assert result.requires_dataset_adoption_gate is False
    assert result.dataset_adoption_authorized is False
    assert result.training_authorized is False
    assert result.state == PREFLIGHT_STATE


def test_confirmation_mode_is_body_free_evidence_review_only() -> None:
    report = _report()
    result = build_dataset_evidence_preflight(
        report.to_dict(),
        created_at=CREATED_AT,
        mode=DatasetEvidencePreflightMode.CONFIRMATION_ONLY,
        **_selection(),
    )
    assert result.status is DatasetEvidencePreflightStatus.EVIDENCE_REVIEW_READY
    assert result.detail_code == "PASS_EVIDENCE_REVIEW"
    assert result.discovery_observed_at == OBSERVED_AT
    assert result.discovery_report_sha256 == report.to_dict()["report_sha256"]
    assert result.selected_logical_path_sha256 == SHA_A
    assert result.selected_observation_sha256 == SHA_B
    assert result.selected_manifest_id == MANIFEST
    assert result.entry_count == 3
    assert result.requires_dataset_adoption_gate is False
    assert result.dataset_adoption_authorized is False
    assert result.training_authorized is False
    public = json.dumps(result.to_dict())
    for forbidden in ("raw_path", "manifest.json", "transcript", "narration", "media_body"):
        assert forbidden not in public
    assert admit_dataset_evidence_preflight(result.to_dict()) == result


def test_preflight_time_cannot_precede_bound_discovery_observation() -> None:
    with pytest.raises(ValueError, match="before discovery_observed_at"):
        build_dataset_evidence_preflight(
            _report().to_dict(),
            created_at="2026-08-26T05:59:59Z",
            mode=DatasetEvidencePreflightMode.CONFIRMATION_ONLY,
        )


def test_learning_preparation_stops_at_human_dataset_adoption_gate() -> None:
    result = build_dataset_evidence_preflight(
        _report().to_dict(),
        created_at=CREATED_AT,
        mode=DatasetEvidencePreflightMode.LEARNING_PREPARATION,
        **_selection(),
    )
    assert result.status is DatasetEvidencePreflightStatus.DATASET_ADOPTION_REVIEW_REQUIRED
    assert result.detail_code == "HUMAN_DATASET_ADOPTION_REQUIRED"
    assert result.requires_dataset_adoption_gate is True
    assert result.eligible_candidate_count == 1
    assert result.dataset_adoption_authorized is False
    assert result.training_authorized is False


def test_learning_preparation_blocks_manifest_without_eligible_candidate() -> None:
    result = build_dataset_evidence_preflight(
        _report(eligible=0).to_dict(),
        created_at=CREATED_AT,
        mode=DatasetEvidencePreflightMode.LEARNING_PREPARATION,
        **_selection(),
    )
    assert result.status is DatasetEvidencePreflightStatus.BLOCKED_NO_ELIGIBLE_CANDIDATE
    assert result.detail_code == "NO_ELIGIBLE_CANDIDATE"
    assert result.eligible_candidate_count == 0
    assert result.requires_dataset_adoption_gate is False
    assert result.training_authorized is False


def test_no_manifest_and_invalid_discovery_are_stable_blockers() -> None:
    missing = DatasetDiscoveryReport(
        observed_at=OBSERVED_AT,
        root_observation_sha256=SHA_A,
        discovery_policy_sha256=DISCOVERY_POLICY_SHA256,
        status=DatasetDiscoveryStatus.NO_MANIFEST_FOUND,
        detail_code="NO_MANIFEST_FOUND",
        items=(),
    )
    no_evidence = build_dataset_evidence_preflight(
        missing.to_dict(),
        created_at=CREATED_AT,
        mode=DatasetEvidencePreflightMode.CONFIRMATION_ONLY,
    )
    assert no_evidence.status is DatasetEvidencePreflightStatus.BLOCKED_DISCOVERY
    assert no_evidence.detail_code == "NO_DATASET_EVIDENCE"

    invalid_item = DatasetDiscoveryItem(
        logical_path_sha256=SHA_A,
        observation_sha256=SHA_B,
        status=DatasetDiscoveryItemStatus.INVALID,
        detail_code="MANIFEST_ADMISSION_FAILED",
        manifest_id=None,
        revision=None,
        rights_manifest_sha256=None,
        entry_count=0,
        eligible_candidate_count=0,
        needs_review_count=0,
        rejected_count=0,
        train_count=0,
        validation_count=0,
        test_count=0,
    )
    blocked = DatasetDiscoveryReport(
        observed_at=OBSERVED_AT,
        root_observation_sha256=SHA_A,
        discovery_policy_sha256=DISCOVERY_POLICY_SHA256,
        status=DatasetDiscoveryStatus.BLOCKED_INVALID_EVIDENCE,
        detail_code="INVALID_EVIDENCE",
        items=(invalid_item,),
    )
    invalid = build_dataset_evidence_preflight(
        blocked.to_dict(),
        created_at=CREATED_AT,
        mode=DatasetEvidencePreflightMode.LEARNING_PREPARATION,
    )
    assert invalid.status is DatasetEvidencePreflightStatus.BLOCKED_DISCOVERY
    assert invalid.detail_code == "INVALID_DATASET_EVIDENCE"
    with pytest.raises(ValueError, match="not allowed"):
        build_dataset_evidence_preflight(
            blocked.to_dict(),
            created_at=CREATED_AT,
            mode=DatasetEvidencePreflightMode.LEARNING_PREPARATION,
            **_selection(),
        )


def test_partial_stale_and_crossed_selection_fail_closed() -> None:
    record = _report().to_dict()
    with pytest.raises(ValueError, match="complete"):
        build_dataset_evidence_preflight(
            record,
            created_at=CREATED_AT,
            mode=DatasetEvidencePreflightMode.CONFIRMATION_ONLY,
            selected_manifest_id=MANIFEST,
        )
    with pytest.raises(ValueError, match="stale"):
        build_dataset_evidence_preflight(
            record,
            created_at=CREATED_AT,
            mode=DatasetEvidencePreflightMode.CONFIRMATION_ONLY,
            selected_manifest_id=MANIFEST,
            selected_revision=4,
            selected_rights_manifest_sha256=SHA_C,
        )
    with pytest.raises(ValueError, match="stale"):
        build_dataset_evidence_preflight(
            record,
            created_at=CREATED_AT,
            mode=DatasetEvidencePreflightMode.CONFIRMATION_ONLY,
            selected_manifest_id=MANIFEST,
            selected_revision=3,
            selected_rights_manifest_sha256=SHA_B,
        )


def test_preflight_tamper_and_authority_forge_fail_closed() -> None:
    result = build_dataset_evidence_preflight(
        _report().to_dict(),
        created_at=CREATED_AT,
        mode=DatasetEvidencePreflightMode.LEARNING_PREPARATION,
        **_selection(),
    )
    tampered = result.to_dict()
    tampered["eligible_candidate_count"] = 2
    with pytest.raises(ValueError):
        admit_dataset_evidence_preflight(tampered)
    crossed_time = result.to_dict()
    crossed_time["discovery_observed_at"] = "2026-08-26T09:00:00Z"
    with pytest.raises(ValueError, match="before discovery_observed_at"):
        admit_dataset_evidence_preflight(crossed_time)
    forged = result.to_dict()
    forged["training_authorized"] = True
    with pytest.raises(ValueError, match="cannot grant"):
        admit_dataset_evidence_preflight(forged)
    with pytest.raises(ValueError, match="cannot grant"):
        replace(result, dataset_adoption_authorized=True)
    with pytest.raises(ValueError, match="state cannot grant"):
        replace(result, state="TRAINING_AUTHORIZED")


def test_schema_mirror_and_all_runtime_states_are_exact() -> None:
    root = Path(__file__).resolve().parents[1]
    canonical = root / "schemas" / "dbd-reasoning-dataset-evidence-preflight.schema.json"
    mirror = root / "src" / "ai_video_production" / "schema_resources" / canonical.name
    assert canonical.read_bytes() == mirror.read_bytes()
    schema = json.loads(canonical.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    records = [
        build_dataset_evidence_preflight(
            _report().to_dict(),
            created_at=CREATED_AT,
            mode=DatasetEvidencePreflightMode.CONFIRMATION_ONLY,
        ),
        build_dataset_evidence_preflight(
            _report().to_dict(),
            created_at=CREATED_AT,
            mode=DatasetEvidencePreflightMode.CONFIRMATION_ONLY,
            **_selection(),
        ),
        build_dataset_evidence_preflight(
            _report(eligible=0).to_dict(),
            created_at=CREATED_AT,
            mode=DatasetEvidencePreflightMode.LEARNING_PREPARATION,
            **_selection(),
        ),
        build_dataset_evidence_preflight(
            _report().to_dict(),
            created_at=CREATED_AT,
            mode=DatasetEvidencePreflightMode.LEARNING_PREPARATION,
            **_selection(),
        ),
    ]
    for record in records:
        validator.validate(record.to_dict())

    forged = records[-1].to_dict()
    forged["training_authorized"] = True
    with pytest.raises(Exception):
        validator.validate(forged)
