from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.voice_dataset_revision import (
    CommitResultState,
    ExistingCommitClassification,
    TrainingInputSnapshot,
    VoiceDatasetCommitIntent,
    VoiceDatasetRevision,
    VoiceDatasetStore,
    add_record_digest,
    classify_authoritative_read_back,
    classify_existing_envelope,
    empty_store_document,
    empty_store_sha256,
    validate_record,
)


H = "sha256:" + "a" * 64
H2 = "sha256:" + "b" * 64
H3 = "sha256:" + "c" * 64
H4 = "sha256:" + "d" * 64
NOW = "2026-08-17T00:00:00Z"


def identity() -> dict:
    return {
        "dataset_store_id": "store:owner-voice",
        "schema_version": "1.0.0",
        "canonicalization_profile": "RFC8785-SHA256-V1",
        "project_id": "project:owner",
        "dataset_id": "dataset:owner-voice",
        "policy_revision_sha256": H,
    }


def member(member_id: str = "member:001") -> dict:
    return add_record_digest(
        {
            "record_type": "VoiceDatasetMembershipEntry",
            "member_id": member_id,
            "candidate_revision_ref": "candidate:001:rev1",
            "candidate_revision_sha256": H,
            "asset_binding_state": "BOUND_VERIFIED",
            "asset_revision_ref": "asset:001:rev1",
            "asset_revision_sha256": H2,
            "asset_checksum_sha256": H3,
            "sample_start": 0,
            "sample_end": 48000,
            "consent_evaluation_sha256": H,
            "rights_evaluation_sha256": H2,
            "quality_evaluation_sha256": H3,
            "approved_label_binding_sha256": H4,
            "processing_class": "RAW_PRE_FILTER",
            "audio_body_persisted": False,
        },
        "entry_sha256",
    )


def review() -> dict:
    return add_record_digest(
        {
            "record_type": "DatasetCandidateReviewBinding",
            "candidate_revision_ref": "candidate:001:rev1",
            "candidate_revision_sha256": H,
            "decision": "APPROVE",
            "owner_decision_ref": "decision:001",
            "owner_decision_sha256": H2,
            "current_consent_evaluation_sha256": H3,
            "current_rights_evaluation_sha256": H4,
            "reviewed_at": NOW,
        },
        "review_binding_sha256",
    )


def readiness() -> dict:
    return add_record_digest(
        {
            "record_type": "DatasetReadinessCoverageIndicator",
            "policy_revision_ref": "policy:dataset:1",
            "policy_revision_sha256": H,
            "eligible_interval_index_sha256": H2,
            "accepted_unique_samples": 48000,
            "eligible_unique_samples": 96000,
            "state": "PASS",
            "reason_codes": [],
        },
        "readiness_sha256",
    )


def revision() -> dict:
    return add_record_digest(
        {
            "record_type": "VoiceDatasetRevision",
            "dataset_revision_id": "dataset-revision:001",
            "dataset_id": "dataset:owner-voice",
            "revision": 1,
            "parent_revision_id": None,
            "parent_revision_sha256": None,
            "commit_intent_sha256": H,
            "membership_entries": [member()],
            "exclusions": [],
            "review_binding": review(),
            "readiness_coverage": readiness(),
            "created_at": NOW,
            "audio_body_persisted": False,
            "text_body_persisted": False,
            "dataset_mutation_authorized": False,
        },
        "revision_sha256",
    )


def first_intent(target_sha: str | None = None) -> dict:
    empty = empty_store_sha256(identity())
    return add_record_digest(
        {
            "record_type": "VoiceDatasetCommitIntent",
            "operation_id": "operation:001",
            "idempotency_key": "idempotency:001",
            "store_identity": identity(),
            "target_revision_id": "dataset-revision:001",
            "target_revision_number": 1,
            "target_revision_sha256": target_sha or revision()["revision_sha256"],
            "expected_store_generation": 0,
            "expected_store_sha256": empty,
            "expected_empty_store_sha256": empty,
            "expected_head_revision_sha256": None,
            "expected_latest_revision_number": None,
            "expected_revision_count": 0,
            "created_at": NOW,
        },
        "intent_sha256",
    )


def snapshot() -> dict:
    return add_record_digest(
        {
            "record_type": "TrainingInputSnapshot",
            "snapshot_id": "training-input:001",
            "revision": 1,
            "parent_snapshot_sha256": None,
            "project_id": "project:owner",
            "dataset_id": "dataset:owner-voice",
            "voice_dataset_revision_ref": "dataset-revision:001",
            "voice_dataset_revision_sha256": revision()["revision_sha256"],
            "selected_member_entry_sha256s": [member()["entry_sha256"]],
            "exclusion_sha256s": [],
            "policy_revision_sha256": H,
            "readiness_sha256": readiness()["readiness_sha256"],
            "current_consent_evaluation_sha256": H2,
            "current_rights_evaluation_sha256": H3,
            "created_at": NOW,
            "audio_body_persisted": False,
            "text_body_persisted": False,
            "dataset_mutation_authorized": False,
            "training_authorized": False,
        },
        "snapshot_sha256",
    )


def test_empty_store_digest_is_context_complete_and_store_revision_is_forbidden() -> None:
    doc = empty_store_document(identity())
    doc["store_sha256"] = empty_store_sha256(identity())
    parsed = VoiceDatasetStore.from_dict(doc)
    assert parsed.to_dict()["store_generation"] == 0
    invalid = parsed.to_dict()
    invalid["store_revision"] = 1
    with pytest.raises(ValueError, match="fields"):
        VoiceDatasetStore.from_dict(invalid)


def test_first_revision_requires_exact_empty_store_cas() -> None:
    assert VoiceDatasetCommitIntent.from_dict(first_intent()).to_dict()["target_revision_number"] == 1
    invalid = first_intent()
    invalid["expected_store_generation"] = 1
    invalid = add_record_digest(invalid, "intent_sha256")
    with pytest.raises(ValueError, match="empty-store"):
        VoiceDatasetCommitIntent.from_dict(invalid)


def test_later_revision_requires_combined_parent_head_generation_and_full_store_cas() -> None:
    value = first_intent()
    value.update(
        target_revision_id="dataset-revision:002",
        target_revision_number=2,
        expected_store_generation=1,
        expected_store_sha256=H4,
        expected_head_revision_sha256=H3,
        expected_latest_revision_number=1,
        expected_revision_count=1,
    )
    value = add_record_digest(value, "intent_sha256")
    assert VoiceDatasetCommitIntent.from_dict(value).to_dict()["target_revision_number"] == 2
    value["expected_head_revision_sha256"] = None
    value = add_record_digest(value, "intent_sha256")
    with pytest.raises(ValueError, match="later revision"):
        VoiceDatasetCommitIntent.from_dict(value)


def test_revision_is_body_free_and_candidate_review_is_separate() -> None:
    parsed = VoiceDatasetRevision.from_dict(revision()).to_dict()
    assert parsed["review_binding"]["record_type"] == "DatasetCandidateReviewBinding"
    invalid = revision()
    invalid["audio_body_persisted"] = True
    invalid = add_record_digest(invalid, "revision_sha256")
    with pytest.raises(ValueError, match="false"):
        VoiceDatasetRevision.from_dict(invalid)


def test_unbound_task003_asset_cannot_invent_asset_fields() -> None:
    value = member()
    value.update(
        asset_binding_state="UNBOUND_PENDING_TASK003",
        asset_revision_ref=None,
        asset_revision_sha256=None,
        asset_checksum_sha256=None,
        sample_start=None,
        sample_end=None,
    )
    value = add_record_digest(value, "entry_sha256")
    validate_record(value)
    value["asset_revision_ref"] = "asset:forged"
    value = add_record_digest(value, "entry_sha256")
    with pytest.raises(ValueError, match="must not invent"):
        validate_record(value)


def test_training_snapshot_never_authorizes_training_or_mutation() -> None:
    record = TrainingInputSnapshot.from_dict(snapshot())
    parsed = record.to_dict()
    assert parsed["training_authorized"] is False
    assert parsed["dataset_mutation_authorized"] is False
    with pytest.raises(TypeError):
        record.data["training_authorized"] = True
    invalid = snapshot()
    invalid["training_authorized"] = True
    invalid = add_record_digest(invalid, "snapshot_sha256")
    with pytest.raises(ValueError, match="false"):
        TrainingInputSnapshot.from_dict(invalid)


def test_timeout_is_unknown_but_observed_mismatch_is_corrupt() -> None:
    assert classify_authoritative_read_back(
        atomic_cas_confirmed=False,
        read_back_observed=False,
        expected_store_sha256=H,
        observed_store_sha256=None,
        observed_graph_valid=None,
        transient_io_failure=True,
    ) is CommitResultState.UNKNOWN
    assert classify_authoritative_read_back(
        atomic_cas_confirmed=True,
        read_back_observed=True,
        expected_store_sha256=H,
        observed_store_sha256=H2,
        observed_graph_valid=True,
        transient_io_failure=False,
    ) is CommitResultState.CORRUPT_OR_INCOMPLETE


def test_verified_commit_requires_atomic_cas_and_matching_read_back() -> None:
    assert classify_authoritative_read_back(
        atomic_cas_confirmed=True,
        read_back_observed=True,
        expected_store_sha256=H,
        observed_store_sha256=H,
        observed_graph_valid=True,
        transient_io_failure=False,
    ) is CommitResultState.VERIFIED_COMMITTED


def test_existing_result_requires_valid_current_head_ancestor_inclusion() -> None:
    parents = {H4: H3, H3: H2, H2: None}
    valid = {H2, H3, H4}
    assert classify_existing_envelope(
        target_envelope_sha256=H2,
        current_head_envelope_sha256=H4,
        parent_by_envelope=parents,
        valid_envelope_sha256s=valid,
        authoritative_history_observed=True,
    ) is ExistingCommitClassification.ACCEPT_PROVEN_COMMITTED
    orphan = "sha256:" + "e" * 64
    parents[orphan] = None
    valid.add(orphan)
    assert classify_existing_envelope(
        target_envelope_sha256=orphan,
        current_head_envelope_sha256=H4,
        parent_by_envelope=parents,
        valid_envelope_sha256s=valid,
        authoritative_history_observed=True,
    ) is ExistingCommitClassification.CONFLICT


def test_receipt_cannot_contain_reverse_envelope_reference() -> None:
    receipt = add_record_digest(
        {
            "record_type": "DatasetAdoptionReceipt",
            "operation_id": "operation:001",
            "idempotency_key": "idempotency:001",
            "intent_sha256": H,
            "revision_sha256": H2,
            "store_preimage_sha256": H3,
            "store_postimage_sha256": H4,
            "generation_before": 0,
            "generation_after": 1,
            "head_before_sha256": None,
            "head_after_sha256": H2,
            "latest_before": None,
            "latest_after": 1,
            "revision_count_before": 0,
            "revision_count_after": 1,
            "atomic_cas": True,
            "read_back_verified": True,
            "result_state": "VERIFIED_COMMITTED",
            "issued_at": NOW,
        },
        "receipt_sha256",
    )
    validate_record(receipt)
    receipt["envelope_sha256"] = H
    with pytest.raises(ValueError, match="fields"):
        validate_record(receipt)


def test_job_kind_and_identity_cannot_be_shared_with_training() -> None:
    job = add_record_digest(
        {
            "record_type": "DurableDatasetAdoptionJobBinding",
            "contract_state": "BOUND_VERIFIED",
            "job_id": "job:adoption:001",
            "operation_id": "operation:001",
            "idempotency_key": "idempotency:001",
            "job_kind": "VOICE_DATASET_ADOPTION",
            "job_revision": 1,
            "job_revision_sha256": H,
            "job_state": "READY",
            "canonical_job_evidence_ref": "evidence:job:001",
            "canonical_job_evidence_sha256": H2,
            "identity_shared_with_training_job": False,
        },
        "binding_sha256",
    )
    validate_record(job)
    job["job_kind"] = "PROJECT_MAINTENANCE"
    job = add_record_digest(job, "binding_sha256")
    with pytest.raises(ValueError, match="cannot be reused"):
        validate_record(job)


def test_digest_tamper_is_rejected() -> None:
    value = snapshot()
    value["project_id"] = "project:tampered"
    with pytest.raises(ValueError, match="snapshot_sha256 mismatch"):
        TrainingInputSnapshot.from_dict(value)


def test_public_schema_and_mirror_are_identical_and_loadable() -> None:
    root = Path(__file__).resolve().parents[1]
    public = root / "schemas" / "voice-dataset-revision.schema.json"
    mirror = root / "src" / "ai_video_production" / "schema_resources" / "voice-dataset-revision.schema.json"
    assert public.read_bytes() == mirror.read_bytes()
    assert hashlib.sha256(public.read_bytes()).hexdigest() == hashlib.sha256(mirror.read_bytes()).hexdigest()
    schema = json.loads(public.read_text(encoding="utf-8"))
    assert schema["$id"] == "bai.task046.voice-dataset-revision.v1"
    assert len(schema["oneOf"]) == 13
    validator = Draft202012Validator(schema)
    for payload in (member(), review(), readiness(), revision(), first_intent(), snapshot()):
        validator.validate(payload)
