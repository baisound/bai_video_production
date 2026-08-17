"""TASK-046/P-VS-3B body-free Voice Dataset revision contract.

The module validates immutable metadata and classifies externally observed CAS
results.  It does not read audio/text bodies, write a Dataset store, create a
Job, issue an authoritative adoption receipt, or start training.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, ClassVar, Mapping
import copy
import re
from types import MappingProxyType

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_ID = "bai.task046.voice-dataset-revision.v1"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")


class ContractState(str, Enum):
    CANONICAL_REF_NOT_PROVIDED = "CANONICAL_REF_NOT_PROVIDED"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class StoreCommitState(str, Enum):
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class CommitResultState(str, Enum):
    VERIFIED_COMMITTED = "VERIFIED_COMMITTED"
    UNKNOWN = "UNKNOWN"
    CORRUPT_OR_INCOMPLETE = "CORRUPT_OR_INCOMPLETE"
    CONFLICT = "CONFLICT"


class ExistingCommitClassification(str, Enum):
    ACCEPT_PROVEN_COMMITTED = "ACCEPT_PROVEN_COMMITTED"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    CORRUPT_OR_INCOMPLETE = "CORRUPT_OR_INCOMPLETE"
    UNKNOWN = "UNKNOWN"


class DatasetReviewDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    RECORD_MORE = "RECORD_MORE"


def _expect_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _sha(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be SHA-256")
    return validate_sha256(value, field_name=name)


def _timestamp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{name} must be RFC3339 UTC")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be RFC3339 UTC") from exc
    return value


def _integer(value: Any, name: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _boolean(value: Any, name: str, *, exact: bool | None = None) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be boolean")
    if exact is not None and value is not exact:
        raise ValueError(f"{name} must be {str(exact).lower()}")
    return value


def _enum(enum_type: type[Enum], value: Any, name: str) -> Enum:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


def _digest_payload(value: Mapping[str, Any], digest_field: str) -> str:
    body = copy.deepcopy(dict(value))
    body.pop(digest_field, None)
    return sha256_bytes(canonical_json_bytes(body))


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def add_record_digest(value: Mapping[str, Any], digest_field: str) -> dict[str, Any]:
    """Return a copy with its canonical record digest populated."""

    body = copy.deepcopy(dict(value))
    body[digest_field] = _digest_payload(body, digest_field)
    return body


def _verify_record_digest(value: Mapping[str, Any], digest_field: str) -> None:
    actual = _sha(value[digest_field], digest_field)
    expected = _digest_payload(value, digest_field)
    if actual != expected:
        raise ValueError(f"{digest_field} mismatch")


def _validate_hash_list(value: Any, name: str, *, max_items: int = 4096) -> None:
    if not isinstance(value, list) or len(value) > max_items:
        raise ValueError(f"{name} must be a bounded list")
    for item in value:
        _sha(item, name)
    if value != sorted(set(value)):
        raise ValueError(f"{name} must be sorted and unique")


def _validate_store_identity(value: Mapping[str, Any]) -> None:
    expected = {
        "dataset_store_id", "schema_version", "canonicalization_profile",
        "project_id", "dataset_id", "policy_revision_sha256",
    }
    _expect_keys(value, expected, "StoreIdentity")
    for field in expected - {"policy_revision_sha256"}:
        _id(value[field], field)
    _sha(value["policy_revision_sha256"], "policy_revision_sha256")


def empty_store_document(store_identity: Mapping[str, Any]) -> dict[str, Any]:
    _validate_store_identity(store_identity)
    return {
        "record_type": "VoiceDatasetStore",
        **copy.deepcopy(dict(store_identity)),
        "store_generation": 0,
        "head_revision_sha256": None,
        "latest_revision_number": None,
        "revision_count": 0,
        "revision_index": [],
        "audio_body_persisted": False,
        "text_body_persisted": False,
        "dataset_store_write_authorized": False,
    }


def empty_store_sha256(store_identity: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(empty_store_document(store_identity)))


def _validate_member(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "member_id", "candidate_revision_ref",
        "candidate_revision_sha256", "asset_binding_state", "asset_revision_ref",
        "asset_revision_sha256", "asset_checksum_sha256", "sample_start",
        "sample_end", "consent_evaluation_sha256", "rights_evaluation_sha256",
        "quality_evaluation_sha256", "approved_label_binding_sha256",
        "processing_class", "audio_body_persisted", "entry_sha256",
    }
    _expect_keys(value, expected, "VoiceDatasetMembershipEntry")
    _id(value["member_id"], "member_id")
    _id(value["candidate_revision_ref"], "candidate_revision_ref")
    _sha(value["candidate_revision_sha256"], "candidate_revision_sha256")
    state = value["asset_binding_state"]
    if state not in {"BOUND_VERIFIED", "UNBOUND_PENDING_TASK003", "MISMATCH", "UNKNOWN"}:
        raise ValueError("asset_binding_state is invalid")
    asset_fields = (
        "asset_revision_ref", "asset_revision_sha256", "asset_checksum_sha256",
        "sample_start", "sample_end",
    )
    if state == "BOUND_VERIFIED":
        if any(value[field] is None for field in asset_fields):
            raise ValueError("BOUND_VERIFIED Asset binding is incomplete")
        _id(value["asset_revision_ref"], "asset_revision_ref")
        _sha(value["asset_revision_sha256"], "asset_revision_sha256")
        _sha(value["asset_checksum_sha256"], "asset_checksum_sha256")
        start = _integer(value["sample_start"], "sample_start")
        end = _integer(value["sample_end"], "sample_end", minimum=1)
        if end <= start:
            raise ValueError("sample range must be non-empty half-open interval")
    elif any(value[field] is not None for field in asset_fields):
        raise ValueError("unresolved Asset binding must not invent Asset truth")
    for field in (
        "consent_evaluation_sha256", "rights_evaluation_sha256",
        "quality_evaluation_sha256", "approved_label_binding_sha256",
    ):
        _sha(value[field], field)
    if value["processing_class"] not in {
        "RAW_PRE_FILTER", "OBS_POST_FILTER", "CANONICAL_CONVERTED_RAW", "RX_DERIVED",
    }:
        raise ValueError("processing_class is invalid")
    _boolean(value["audio_body_persisted"], "audio_body_persisted", exact=False)
    _verify_record_digest(value, "entry_sha256")


def _validate_exclusion(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "member_id", "source_entry_sha256", "reason_code",
        "excluded_at", "exclusion_sha256",
    }
    _expect_keys(value, expected, "DatasetMemberExclusion")
    _id(value["member_id"], "member_id")
    _sha(value["source_entry_sha256"], "source_entry_sha256")
    if value["reason_code"] not in {
        "OWNER_REJECTED", "QUALITY_FAILED", "RIGHTS_BLOCKED", "CONSENT_BLOCKED",
        "DUPLICATE", "RANGE_OVERLAP", "SUPERSEDED", "OTHER_APPROVED_REASON",
    }:
        raise ValueError("reason_code is invalid")
    _timestamp(value["excluded_at"], "excluded_at")
    _verify_record_digest(value, "exclusion_sha256")


def _validate_review(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "candidate_revision_ref", "candidate_revision_sha256",
        "decision", "owner_decision_ref", "owner_decision_sha256",
        "current_consent_evaluation_sha256", "current_rights_evaluation_sha256",
        "reviewed_at", "review_binding_sha256",
    }
    _expect_keys(value, expected, "DatasetCandidateReviewBinding")
    _id(value["candidate_revision_ref"], "candidate_revision_ref")
    _sha(value["candidate_revision_sha256"], "candidate_revision_sha256")
    _enum(DatasetReviewDecision, value["decision"], "decision")
    _id(value["owner_decision_ref"], "owner_decision_ref")
    for field in (
        "owner_decision_sha256", "current_consent_evaluation_sha256",
        "current_rights_evaluation_sha256",
    ):
        _sha(value[field], field)
    _timestamp(value["reviewed_at"], "reviewed_at")
    _verify_record_digest(value, "review_binding_sha256")


def _validate_readiness(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "policy_revision_ref", "policy_revision_sha256",
        "eligible_interval_index_sha256", "accepted_unique_samples",
        "eligible_unique_samples", "state", "reason_codes", "readiness_sha256",
    }
    _expect_keys(value, expected, "DatasetReadinessCoverageIndicator")
    _id(value["policy_revision_ref"], "policy_revision_ref")
    _sha(value["policy_revision_sha256"], "policy_revision_sha256")
    _sha(value["eligible_interval_index_sha256"], "eligible_interval_index_sha256")
    accepted = _integer(value["accepted_unique_samples"], "accepted_unique_samples")
    eligible = _integer(value["eligible_unique_samples"], "eligible_unique_samples")
    if accepted > eligible:
        raise ValueError("accepted_unique_samples cannot exceed denominator")
    if value["state"] not in {"PASS", "FAIL", "UNKNOWN"}:
        raise ValueError("readiness state is invalid")
    if not isinstance(value["reason_codes"], list) or len(value["reason_codes"]) > 64:
        raise ValueError("reason_codes must be bounded")
    for reason in value["reason_codes"]:
        _id(reason, "reason_code")
    if value["reason_codes"] != sorted(set(value["reason_codes"])):
        raise ValueError("reason_codes must be sorted and unique")
    _verify_record_digest(value, "readiness_sha256")


def _validate_training_snapshot(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "snapshot_id", "revision", "parent_snapshot_sha256",
        "project_id", "dataset_id", "voice_dataset_revision_ref",
        "voice_dataset_revision_sha256", "selected_member_entry_sha256s",
        "exclusion_sha256s", "policy_revision_sha256", "readiness_sha256",
        "current_consent_evaluation_sha256", "current_rights_evaluation_sha256",
        "created_at", "audio_body_persisted", "text_body_persisted",
        "dataset_mutation_authorized", "training_authorized", "snapshot_sha256",
    }
    _expect_keys(value, expected, "TrainingInputSnapshot")
    for field in ("snapshot_id", "project_id", "dataset_id", "voice_dataset_revision_ref"):
        _id(value[field], field)
    revision = _integer(value["revision"], "revision", minimum=1)
    parent = value["parent_snapshot_sha256"]
    if revision == 1 and parent is not None:
        raise ValueError("first TrainingInputSnapshot cannot have a parent")
    if revision > 1 and parent is None:
        raise ValueError("later TrainingInputSnapshot requires a parent")
    _sha(parent, "parent_snapshot_sha256", nullable=True)
    for field in (
        "voice_dataset_revision_sha256", "policy_revision_sha256", "readiness_sha256",
        "current_consent_evaluation_sha256", "current_rights_evaluation_sha256",
    ):
        _sha(value[field], field)
    _validate_hash_list(value["selected_member_entry_sha256s"], "selected_member_entry_sha256s")
    _validate_hash_list(value["exclusion_sha256s"], "exclusion_sha256s")
    _timestamp(value["created_at"], "created_at")
    for field in (
        "audio_body_persisted", "text_body_persisted", "dataset_mutation_authorized",
        "training_authorized",
    ):
        _boolean(value[field], field, exact=False)
    _verify_record_digest(value, "snapshot_sha256")


def _validate_intent(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "operation_id", "idempotency_key", "store_identity",
        "target_revision_id", "target_revision_number", "target_revision_sha256",
        "expected_store_generation", "expected_store_sha256",
        "expected_empty_store_sha256", "expected_head_revision_sha256",
        "expected_latest_revision_number", "expected_revision_count", "created_at",
        "intent_sha256",
    }
    _expect_keys(value, expected, "VoiceDatasetCommitIntent")
    for field in ("operation_id", "idempotency_key", "target_revision_id"):
        _id(value[field], field)
    _validate_store_identity(value["store_identity"])
    number = _integer(value["target_revision_number"], "target_revision_number", minimum=1)
    _sha(value["target_revision_sha256"], "target_revision_sha256")
    generation = _integer(value["expected_store_generation"], "expected_store_generation")
    _sha(value["expected_store_sha256"], "expected_store_sha256")
    expected_empty = _sha(value["expected_empty_store_sha256"], "expected_empty_store_sha256")
    if expected_empty != empty_store_sha256(value["store_identity"]):
        raise ValueError("expected_empty_store_sha256 is not context-complete")
    head = _sha(value["expected_head_revision_sha256"], "expected_head_revision_sha256", nullable=True)
    latest = value["expected_latest_revision_number"]
    count = _integer(value["expected_revision_count"], "expected_revision_count")
    if number == 1:
        if generation != 0 or head is not None or latest is not None or count != 0:
            raise ValueError("first revision requires exact empty-store CAS context")
        if value["expected_store_sha256"] != expected_empty:
            raise ValueError("first revision expected store must be empty store")
    else:
        if generation < 1 or head is None or latest != number - 1 or count != number - 1:
            raise ValueError("later revision requires parent/head/generation/full-store CAS")
    _timestamp(value["created_at"], "created_at")
    _verify_record_digest(value, "intent_sha256")


def _validate_revision(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "dataset_revision_id", "dataset_id", "revision",
        "parent_revision_id", "parent_revision_sha256", "commit_intent_sha256",
        "membership_entries", "exclusions", "review_binding", "readiness_coverage",
        "created_at", "audio_body_persisted", "text_body_persisted",
        "dataset_mutation_authorized", "revision_sha256",
    }
    _expect_keys(value, expected, "VoiceDatasetRevision")
    _id(value["dataset_revision_id"], "dataset_revision_id")
    _id(value["dataset_id"], "dataset_id")
    revision = _integer(value["revision"], "revision", minimum=1)
    if revision == 1:
        if value["parent_revision_id"] is not None or value["parent_revision_sha256"] is not None:
            raise ValueError("first VoiceDatasetRevision cannot have a parent")
    else:
        _id(value["parent_revision_id"], "parent_revision_id")
        _sha(value["parent_revision_sha256"], "parent_revision_sha256")
    _sha(value["commit_intent_sha256"], "commit_intent_sha256")
    if not isinstance(value["membership_entries"], list) or len(value["membership_entries"]) > 4096:
        raise ValueError("membership_entries must be bounded")
    for entry in value["membership_entries"]:
        validate_record(entry, expected_type="VoiceDatasetMembershipEntry")
    entry_ids = [entry["member_id"] for entry in value["membership_entries"]]
    if entry_ids != sorted(set(entry_ids)):
        raise ValueError("membership entries must be sorted and unique")
    if not isinstance(value["exclusions"], list) or len(value["exclusions"]) > 4096:
        raise ValueError("exclusions must be bounded")
    for exclusion in value["exclusions"]:
        validate_record(exclusion, expected_type="DatasetMemberExclusion")
    exclusion_ids = [entry["member_id"] for entry in value["exclusions"]]
    if exclusion_ids != sorted(set(exclusion_ids)):
        raise ValueError("exclusions must be sorted and unique")
    validate_record(value["review_binding"], expected_type="DatasetCandidateReviewBinding")
    validate_record(value["readiness_coverage"], expected_type="DatasetReadinessCoverageIndicator")
    _timestamp(value["created_at"], "created_at")
    for field in ("audio_body_persisted", "text_body_persisted", "dataset_mutation_authorized"):
        _boolean(value[field], field, exact=False)
    _verify_record_digest(value, "revision_sha256")


def _validate_receipt(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "operation_id", "idempotency_key", "intent_sha256",
        "revision_sha256", "store_preimage_sha256", "store_postimage_sha256",
        "generation_before", "generation_after", "head_before_sha256",
        "head_after_sha256", "latest_before", "latest_after", "revision_count_before",
        "revision_count_after", "atomic_cas", "read_back_verified", "result_state",
        "issued_at", "receipt_sha256",
    }
    _expect_keys(value, expected, "DatasetAdoptionReceipt")
    for field in ("operation_id", "idempotency_key"):
        _id(value[field], field)
    for field in (
        "intent_sha256", "revision_sha256", "store_preimage_sha256",
        "store_postimage_sha256", "head_after_sha256",
    ):
        _sha(value[field], field)
    _sha(value["head_before_sha256"], "head_before_sha256", nullable=True)
    before = _integer(value["generation_before"], "generation_before")
    after = _integer(value["generation_after"], "generation_after", minimum=1)
    if after != before + 1:
        raise ValueError("generation must increment exactly once")
    for field in ("revision_count_before", "revision_count_after"):
        _integer(value[field], field)
    if value["revision_count_after"] != value["revision_count_before"] + 1:
        raise ValueError("revision count must increment exactly once")
    if value["latest_before"] is not None:
        _integer(value["latest_before"], "latest_before", minimum=1)
    _integer(value["latest_after"], "latest_after", minimum=1)
    atomic = _boolean(value["atomic_cas"], "atomic_cas")
    readback = _boolean(value["read_back_verified"], "read_back_verified")
    result = _enum(CommitResultState, value["result_state"], "result_state")
    if result is CommitResultState.VERIFIED_COMMITTED and not (atomic and readback):
        raise ValueError("VERIFIED_COMMITTED requires atomic CAS and read-back")
    _timestamp(value["issued_at"], "issued_at")
    _verify_record_digest(value, "receipt_sha256")


def _validate_envelope(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "operation_id", "idempotency_key", "intent_sha256",
        "revision_sha256", "receipt_sha256", "previous_envelope_sha256",
        "created_at", "envelope_sha256",
    }
    _expect_keys(value, expected, "VoiceDatasetCommitEnvelope")
    for field in ("operation_id", "idempotency_key"):
        _id(value[field], field)
    for field in ("intent_sha256", "revision_sha256", "receipt_sha256"):
        _sha(value[field], field)
    _sha(value["previous_envelope_sha256"], "previous_envelope_sha256", nullable=True)
    _timestamp(value["created_at"], "created_at")
    _verify_record_digest(value, "envelope_sha256")


def _validate_store(value: Mapping[str, Any]) -> None:
    identity_keys = {
        "dataset_store_id", "schema_version", "canonicalization_profile",
        "project_id", "dataset_id", "policy_revision_sha256",
    }
    expected = {
        "record_type", *identity_keys, "store_generation", "head_revision_sha256",
        "latest_revision_number", "revision_count", "revision_index",
        "audio_body_persisted", "text_body_persisted", "dataset_store_write_authorized",
        "store_sha256",
    }
    _expect_keys(value, expected, "VoiceDatasetStore")
    _validate_store_identity({key: value[key] for key in identity_keys})
    generation = _integer(value["store_generation"], "store_generation")
    count = _integer(value["revision_count"], "revision_count")
    index = value["revision_index"]
    if not isinstance(index, list) or len(index) != count or len(index) > 4096:
        raise ValueError("revision_index/count mismatch")
    previous_revision_sha: str | None = None
    for position, item in enumerate(index, start=1):
        _expect_keys(
            item,
            {"revision_number", "revision_id", "revision_sha256", "parent_revision_sha256", "envelope_sha256"},
            "RevisionIndexEntry",
        )
        if _integer(item["revision_number"], "revision_number", minimum=1) != position:
            raise ValueError("revision_index must be contiguous")
        _id(item["revision_id"], "revision_id")
        _sha(item["revision_sha256"], "revision_sha256")
        parent = _sha(item["parent_revision_sha256"], "parent_revision_sha256", nullable=True)
        _sha(item["envelope_sha256"], "envelope_sha256")
        if parent != previous_revision_sha:
            raise ValueError("revision_index parent chain mismatch")
        previous_revision_sha = item["revision_sha256"]
    head = _sha(value["head_revision_sha256"], "head_revision_sha256", nullable=True)
    latest = value["latest_revision_number"]
    if count == 0:
        if generation != 0 or head is not None or latest is not None:
            raise ValueError("empty VoiceDatasetStore is inconsistent")
    else:
        if generation != count or head != index[-1]["revision_sha256"] or latest != count:
            raise ValueError("VoiceDatasetStore head/latest/index mismatch")
    for field in ("audio_body_persisted", "text_body_persisted", "dataset_store_write_authorized"):
        _boolean(value[field], field, exact=False)
    _verify_record_digest(value, "store_sha256")


def _validate_capability(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "contract_state", "canonical_owner_ref", "canonical_owner_sha256",
        "api_version", "atomic_full_store_cas", "authoritative_read_back",
        "history_reconciliation", "evidence_ref", "evidence_sha256",
        "capability_sha256",
    }
    _expect_keys(value, expected, "DatasetStorePersistenceCapabilityBinding")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    fields = expected - {"record_type", "contract_state", "capability_sha256"}
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in fields):
            raise ValueError("unresolved capability must not invent canonical fields")
    elif state is ContractState.BOUND_VERIFIED:
        if any(value[field] is None for field in fields):
            raise ValueError("BOUND_VERIFIED capability is incomplete")
        for field in ("canonical_owner_ref", "api_version", "evidence_ref"):
            _id(value[field], field)
        for field in ("canonical_owner_sha256", "evidence_sha256"):
            _sha(value[field], field)
        for field in ("atomic_full_store_cas", "authoritative_read_back", "history_reconciliation"):
            _boolean(value[field], field, exact=True)
    _verify_record_digest(value, "capability_sha256")


def _validate_commit_binding(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "contract_state", "authoritative_store_sha256",
        "store_generation", "head_revision_sha256", "latest_revision_number",
        "revision_count", "committed_envelope_sha256", "read_back_evidence_ref",
        "read_back_evidence_sha256", "observed_at", "reason_code",
        "binding_sha256",
    }
    _expect_keys(value, expected, "StoreCommitBinding")
    state = _enum(StoreCommitState, value["contract_state"], "contract_state")
    data_fields = expected - {"record_type", "contract_state", "reason_code", "binding_sha256"}
    if state is StoreCommitState.BOUND_VERIFIED:
        if any(value[field] is None for field in data_fields) or value["reason_code"] is not None:
            raise ValueError("BOUND_VERIFIED StoreCommitBinding is incomplete")
        for field in ("authoritative_store_sha256", "head_revision_sha256", "committed_envelope_sha256", "read_back_evidence_sha256"):
            _sha(value[field], field)
        for field in ("store_generation", "latest_revision_number", "revision_count"):
            _integer(value[field], field, minimum=1)
        _id(value["read_back_evidence_ref"], "read_back_evidence_ref")
        _timestamp(value["observed_at"], "observed_at")
    else:
        _id(value["reason_code"], "reason_code")
    _verify_record_digest(value, "binding_sha256")


def _validate_job(value: Mapping[str, Any]) -> None:
    expected = {
        "record_type", "contract_state", "job_id", "operation_id", "idempotency_key",
        "job_kind", "job_revision", "job_revision_sha256", "job_state",
        "canonical_job_evidence_ref", "canonical_job_evidence_sha256",
        "identity_shared_with_training_job", "binding_sha256",
    }
    _expect_keys(value, expected, "DurableDatasetAdoptionJobBinding")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    fields = expected - {"record_type", "contract_state", "binding_sha256", "identity_shared_with_training_job"}
    _boolean(value["identity_shared_with_training_job"], "identity_shared_with_training_job", exact=False)
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in fields):
            raise ValueError("unresolved Job binding must not invent Job truth")
    elif state is ContractState.BOUND_VERIFIED:
        if any(value[field] is None for field in fields):
            raise ValueError("BOUND_VERIFIED Job binding is incomplete")
        for field in ("job_id", "operation_id", "idempotency_key", "canonical_job_evidence_ref"):
            _id(value[field], field)
        if value["job_kind"] != "VOICE_DATASET_ADOPTION":
            raise ValueError("PROJECT_MAINTENANCE or Training Job cannot be reused")
        _integer(value["job_revision"], "job_revision", minimum=1)
        _sha(value["job_revision_sha256"], "job_revision_sha256")
        _id(value["job_state"], "job_state")
        _sha(value["canonical_job_evidence_sha256"], "canonical_job_evidence_sha256")
    _verify_record_digest(value, "binding_sha256")


_VALIDATORS: dict[str, Callable[[Mapping[str, Any]], None]] = {
    "VoiceDatasetStore": _validate_store,
    "VoiceDatasetCommitIntent": _validate_intent,
    "VoiceDatasetRevision": _validate_revision,
    "VoiceDatasetMembershipEntry": _validate_member,
    "DatasetMemberExclusion": _validate_exclusion,
    "DatasetCandidateReviewBinding": _validate_review,
    "DatasetAdoptionReceipt": _validate_receipt,
    "VoiceDatasetCommitEnvelope": _validate_envelope,
    "DatasetStorePersistenceCapabilityBinding": _validate_capability,
    "StoreCommitBinding": _validate_commit_binding,
    "DurableDatasetAdoptionJobBinding": _validate_job,
    "DatasetReadinessCoverageIndicator": _validate_readiness,
    "TrainingInputSnapshot": _validate_training_snapshot,
}


def validate_record(value: Mapping[str, Any], *, expected_type: str | None = None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("record must be an object")
    record_type = value.get("record_type")
    if record_type not in _VALIDATORS:
        raise ValueError("record_type is unknown")
    if expected_type is not None and record_type != expected_type:
        raise ValueError(f"expected {expected_type}")
    body = copy.deepcopy(dict(value))
    _VALIDATORS[record_type](body)
    return body


@dataclass(frozen=True, slots=True)
class _CanonicalRecord:
    data: Mapping[str, Any]
    RECORD_TYPE: ClassVar[str]

    def __post_init__(self) -> None:
        validated = validate_record(self.data, expected_type=self.RECORD_TYPE)
        object.__setattr__(self, "data", _freeze(validated))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "_CanonicalRecord":
        return cls(value)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.data)

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


class VoiceDatasetStore(_CanonicalRecord): RECORD_TYPE = "VoiceDatasetStore"
class VoiceDatasetCommitIntent(_CanonicalRecord): RECORD_TYPE = "VoiceDatasetCommitIntent"
class VoiceDatasetRevision(_CanonicalRecord): RECORD_TYPE = "VoiceDatasetRevision"
class VoiceDatasetMembershipEntry(_CanonicalRecord): RECORD_TYPE = "VoiceDatasetMembershipEntry"
class DatasetMemberExclusion(_CanonicalRecord): RECORD_TYPE = "DatasetMemberExclusion"
class DatasetCandidateReviewBinding(_CanonicalRecord): RECORD_TYPE = "DatasetCandidateReviewBinding"
class DatasetAdoptionReceipt(_CanonicalRecord): RECORD_TYPE = "DatasetAdoptionReceipt"
class VoiceDatasetCommitEnvelope(_CanonicalRecord): RECORD_TYPE = "VoiceDatasetCommitEnvelope"
class DatasetStorePersistenceCapabilityBinding(_CanonicalRecord): RECORD_TYPE = "DatasetStorePersistenceCapabilityBinding"
class StoreCommitBinding(_CanonicalRecord): RECORD_TYPE = "StoreCommitBinding"
class DurableDatasetAdoptionJobBinding(_CanonicalRecord): RECORD_TYPE = "DurableDatasetAdoptionJobBinding"
class DatasetReadinessCoverageIndicator(_CanonicalRecord): RECORD_TYPE = "DatasetReadinessCoverageIndicator"
class TrainingInputSnapshot(_CanonicalRecord): RECORD_TYPE = "TrainingInputSnapshot"


def classify_authoritative_read_back(
    *,
    atomic_cas_confirmed: bool,
    read_back_observed: bool,
    expected_store_sha256: str,
    observed_store_sha256: str | None,
    observed_graph_valid: bool | None,
    transient_io_failure: bool,
) -> CommitResultState:
    """Classify facts without weakening observed corruption into UNKNOWN."""

    _boolean(atomic_cas_confirmed, "atomic_cas_confirmed")
    _boolean(read_back_observed, "read_back_observed")
    _sha(expected_store_sha256, "expected_store_sha256")
    _boolean(transient_io_failure, "transient_io_failure")
    if not read_back_observed:
        if observed_store_sha256 is not None or observed_graph_valid is not None:
            raise ValueError("unobserved read-back cannot contain authoritative facts")
        return CommitResultState.UNKNOWN
    _sha(observed_store_sha256, "observed_store_sha256")
    if observed_graph_valid is not True or observed_store_sha256 != expected_store_sha256:
        return CommitResultState.CORRUPT_OR_INCOMPLETE
    if transient_io_failure:
        return CommitResultState.UNKNOWN
    if not atomic_cas_confirmed:
        return CommitResultState.CONFLICT
    return CommitResultState.VERIFIED_COMMITTED


def classify_existing_envelope(
    *,
    target_envelope_sha256: str,
    current_head_envelope_sha256: str | None,
    parent_by_envelope: Mapping[str, str | None],
    valid_envelope_sha256s: set[str],
    authoritative_history_observed: bool,
) -> ExistingCommitClassification:
    """Prove existing commit only by canonical-head ancestor inclusion."""

    target = _sha(target_envelope_sha256, "target_envelope_sha256")
    if not authoritative_history_observed:
        return ExistingCommitClassification.UNKNOWN
    if current_head_envelope_sha256 is None:
        return ExistingCommitClassification.NOT_FOUND
    head = _sha(current_head_envelope_sha256, "current_head_envelope_sha256")
    if head not in valid_envelope_sha256s:
        return ExistingCommitClassification.CORRUPT_OR_INCOMPLETE
    seen: set[str] = set()
    current: str | None = head
    while current is not None:
        if current in seen:
            return ExistingCommitClassification.CORRUPT_OR_INCOMPLETE
        seen.add(current)
        if current not in valid_envelope_sha256s or current not in parent_by_envelope:
            return ExistingCommitClassification.CORRUPT_OR_INCOMPLETE
        if current == target:
            return ExistingCommitClassification.ACCEPT_PROVEN_COMMITTED
        parent = parent_by_envelope[current]
        if parent is not None:
            _sha(parent, "parent envelope sha256")
        current = parent
    if target in parent_by_envelope or target in valid_envelope_sha256s:
        return ExistingCommitClassification.CONFLICT
    return ExistingCommitClassification.NOT_FOUND
