from __future__ import annotations

import ast
import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import pickle

from jsonschema import Draft202012Validator
import pytest

import ai_video_production.task084_voice_model_artifact_custody as task084
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task084_voice_model_artifact_custody import (
    ArtifactVariant,
    CustodyPhase,
    LeaseState,
    LoadPurpose,
    Task084CustodyReadbackV1,
    Task084FixtureCustodyEventV1,
    Task084FixtureCustodyReadbackV1,
    Task084FixtureModelArtifactCustodyReceiptV1,
    Task084FixtureModelArtifactWriteLeaseV1,
    Task084FixtureModelCheckpointCustodyReceiptV1,
    Task084FixtureModelLoadCompletionVerification,
    Task084FixtureModelLoadLeaseV1,
    Task084FixtureModelLoadOpenHandle,
    Task084FixtureModelLoadReadbackV1,
    Task084ModelArtifactCustodyReceiptV1,
    Task084ModelCheckpointCustodyReceiptV1,
    assert_effect_zero_surface,
    compile_fixture_inventory,
    compile_model_load_admission,
    compile_output_artifact_destination_plan,
    compile_production_custody_admission,
    open_fixture_custody,
    parse_security_json,
    replay_fixture_event_chain,
    replay_fixture_custody,
    validate_terminal_custody_for_model_artifact_binding,
)
from ai_video_production.voice_dataset_revision import add_record_digest as add_dataset_digest
from ai_video_production.voice_training_run import add_record_digest as add_training_digest


ROOT = Path(__file__).parents[1]
PUBLIC_SCHEMA = ROOT / "schemas" / "task084-voice-model-artifact-custody.schema.json"
PACKAGED_SCHEMA = (
    ROOT
    / "src"
    / "ai_video_production"
    / "schema_resources"
    / "task084-voice-model-artifact-custody.schema.json"
)
SOURCE = ROOT / "src" / "ai_video_production" / "task084_voice_model_artifact_custody.py"

NOW = "2026-09-06T00:00:00Z"
ACTIVE_AT = "2026-09-06T00:01:00Z"
ISSUED_AT = "2026-09-06T00:02:00Z"
OPEN_AT = "2026-09-06T00:03:00Z"
SEALED_AT = "2026-09-06T00:04:00Z"
EXPIRES_AT = "2026-09-06T01:00:00Z"


def H(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def training_snapshot() -> dict:
    return add_dataset_digest(
        {
            "record_type": "TrainingInputSnapshot",
            "snapshot_id": "training-input:task084:1",
            "revision": 1,
            "parent_snapshot_sha256": None,
            "project_id": "project:owner",
            "dataset_id": "dataset:owner-voice",
            "voice_dataset_revision_ref": "dataset-revision:owner:1",
            "voice_dataset_revision_sha256": H("dataset-revision"),
            "selected_member_entry_sha256s": [H("member-1")],
            "exclusion_sha256s": [],
            "policy_revision_sha256": H("dataset-policy"),
            "readiness_sha256": H("readiness"),
            "current_consent_evaluation_sha256": H("consent"),
            "current_rights_evaluation_sha256": H("rights"),
            "created_at": "2026-09-05T23:00:00Z",
            "audio_body_persisted": False,
            "text_body_persisted": False,
            "dataset_mutation_authorized": False,
            "training_authorized": False,
        },
        "snapshot_sha256",
    )


def binding(record_type: str, fields: dict) -> dict:
    return add_training_digest(
        {"record_type": record_type, "contract_state": "BOUND_VERIFIED", **fields},
        "binding_sha256",
    )


def engine_binding() -> dict:
    return binding(
        "EngineAdmissionBinding",
        {
            "engine_id": "engine:qwen3-tts",
            "engine_repository_ref": "repo:qwen3-tts",
            "engine_commit_sha256": H("engine-commit"),
            "package_lock_sha256": H("package-lock"),
            "training_mode": "ADAPTER_OR_LORA",
            "capability_state": "ADMITTED",
            "license_state": "PASS",
            "base_model_id": "model:qwen3-tts-base",
            "base_model_revision": "revision:base:1",
            "base_model_sha256": H("base-model"),
            "runtime_revision": "runtime:torch:1",
            "runtime_sha256": H("runtime"),
            "code_revision": "code:qwen:1",
            "code_sha256": H("code"),
            "weight_revision": "weights:qwen:1",
            "weight_sha256": H("weight"),
            "tokenizer_sha256": H("tokenizer"),
            "codec_sha256": H("codec"),
            "vocoder_sha256": H("vocoder"),
            "config_sha256": H("engine-config"),
            "target_probe_profile_ref": "probe:task084:1",
            "target_probe_profile_sha256": H("probe"),
            "evidence_ref": "evidence:engine:1",
            "evidence_sha256": H("engine-evidence"),
        },
    )


def destination_binding() -> dict:
    return binding(
        "OutputArtifactDestinationBinding",
        {
            "canonical_owner_ref": "storage:voice-models",
            "canonical_owner_sha256": H("storage-owner"),
            "storage_policy_ref": "policy:storage:1",
            "storage_policy_sha256": H("storage-policy"),
            "logical_uri": "artifact-destination:voice-models",
            "encryption_policy_sha256": H("destination-encryption"),
            "recovery_policy_sha256": H("recovery-policy"),
            "retention_policy_sha256": H("retention-policy"),
            "disk_quota_admission_ref": "admission:disk:1",
            "disk_quota_admission_sha256": H("disk-admission"),
            "allowed_artifact_classes": [
                "CHECKPOINT",
                "EVALUATION_OUTPUT",
                "LOG",
                "MODEL_OUTPUT",
            ],
            "public_exposure": False,
        },
    )


def feasibility_binding() -> dict:
    return binding(
        "TargetResourceFeasibilityBinding",
        {
            "mode": "ADAPTER_OR_LORA",
            "recipe_revision_ref": "recipe:owner-voice:1",
            "recipe_revision_sha256": H("recipe"),
            "probe_profile_ref": "probe:task084:1",
            "probe_profile_sha256": H("probe"),
            "target_gpu_ref": "gpu:rtx4070-super",
            "target_vram_bytes": 12_000_000_000,
            "peak_vram_bytes": 9_000_000_000,
            "peak_ram_bytes": 16_000_000_000,
            "optimizer_overhead_bytes": 1_000_000_000,
            "checkpoint_overhead_bytes": 2_000_000_000,
            "representative_batch": 1,
            "representative_sequence_units": 1024,
            "thermal_floor_state": "PASS",
            "disk_floor_state": "PASS",
            "oom_recovery_state": "PASS",
            "expected_duration_seconds": 3600,
            "headroom_policy_ref": "policy:headroom:1",
            "headroom_policy_sha256": H("headroom"),
            "admission_state": "ADMITTED",
            "evidence_ref": "evidence:feasibility:1",
            "evidence_sha256": H("feasibility"),
        },
    )


def rights_binding() -> dict:
    return binding(
        "CurrentUseRightsBinding",
        {
            "evaluation_ref": "rights:owner:1",
            "evaluation_sha256": H("rights-evaluation"),
            "consent_state": "PASS",
            "training_data_rights_state": "PASS",
            "reference_audio_rights_state": "PASS",
            "output_rights_state": "PASS",
            "license_state": "PASS",
            "evaluated_at": "2026-09-05T22:00:00Z",
        },
    )


def evaluation_snapshot() -> dict:
    item = {
        "source_kind": "PVS3B_DATASET_MEMBER",
        "item_ref": "evaluation-item:1",
        "item_sha256": H("evaluation-item"),
        "dataset_member_entry_sha256": H("eval-member"),
        "asset_revision_ref": "asset:evaluation:1",
        "asset_revision_sha256": H("eval-asset-revision"),
        "asset_checksum_sha256": H("eval-asset"),
        "sample_start": 0,
        "sample_end": 48_000,
        "consent_evaluation_sha256": H("eval-consent"),
        "evaluation_rights_sha256": H("eval-rights"),
        "reference_rights_sha256": H("reference-rights"),
        "output_rights_sha256": H("output-rights"),
        "approved_labels_sha256": H("labels"),
        "provenance_equivalence_sha256": H("provenance"),
    }
    return add_training_digest(
        {
            "record_type": "EvaluationInputSnapshot",
            "snapshot_id": "evaluation-input:1",
            "revision": 1,
            "parent_snapshot_sha256": None,
            "project_id": "project:owner",
            "selection_policy_ref": "policy:evaluation:1",
            "selection_policy_sha256": H("evaluation-policy"),
            "selected_items": [item],
            "private_equivalence_index_sha256": H("private-index"),
            "created_at": "2026-09-05T22:00:00Z",
            "audio_body_persisted": False,
            "text_body_persisted": False,
        },
        "snapshot_sha256",
    )


def contamination_binding(snapshot_sha256: str, evaluation_sha256: str) -> dict:
    return add_training_digest(
        {
            "record_type": "ContaminationProofBinding",
            "training_input_snapshot_ref": "training-input:task084:1",
            "training_input_snapshot_sha256": snapshot_sha256,
            "evaluation_input_snapshot_ref": "evaluation-input:1",
            "evaluation_input_snapshot_sha256": evaluation_sha256,
            "identity_non_overlap": True,
            "asset_mapping_non_overlap": True,
            "checksum_non_overlap": True,
            "sample_range_non_overlap": True,
            "source_lineage_non_overlap": True,
            "semantic_policy_state": "BOUND_VERIFIED",
            "semantic_policy_ref": "policy:near-duplicate:1",
            "semantic_policy_sha256": H("semantic-policy"),
            "semantic_decision": "PASS",
            "decision": "PASS",
            "reason_codes": [],
        },
        "proof_sha256",
    )


def training_intent(snapshot: dict | None = None) -> dict:
    snapshot = snapshot or training_snapshot()
    evaluation = evaluation_snapshot()
    rights = rights_binding()
    return add_training_digest(
        {
            "record_type": "TrainingRunIntent",
            "run_intent_id": "training-run-intent:task084:1",
            "revision": 1,
            "parent_intent_sha256": None,
            "project_id": snapshot["project_id"],
            "training_mode": "ADAPTER_OR_LORA",
            "training_input_snapshot_ref": snapshot["snapshot_id"],
            "training_input_snapshot_sha256": snapshot["snapshot_sha256"],
            "evaluation_input_snapshot_ref": evaluation["snapshot_id"],
            "evaluation_input_snapshot_sha256": evaluation["snapshot_sha256"],
            "contamination_proof_binding": contamination_binding(
                snapshot["snapshot_sha256"], evaluation["snapshot_sha256"]
            ),
            "engine_admission_binding": engine_binding(),
            "output_artifact_destination_binding": destination_binding(),
            "target_resource_feasibility_binding": feasibility_binding(),
            "current_use_rights_binding": rights,
            "current_consent_rights_license_sha256": rights["binding_sha256"],
            "config_sha256": H("run-config"),
            "created_at": "2026-09-05T23:30:00Z",
            "audio_body_persisted": False,
            "text_body_persisted": False,
            "execution_authorized": False,
        },
        "intent_sha256",
    )


def job_binding() -> dict:
    return binding(
        "TrainingDurableJobBinding",
        {
            "job_id": "job:voice-training:1",
            "operation_id": "operation:voice-training:1",
            "idempotency_key": "idempotency:voice-training:1",
            "job_kind": "VOICE_MODEL_TRAINING",
            "job_revision": 1,
            "job_revision_sha256": H("job-revision"),
            "job_state": "RUNNING",
            "canonical_job_evidence_ref": "evidence:job:1",
            "canonical_job_evidence_sha256": H("job-evidence"),
            "identity_shared_with_dataset_adoption_job": False,
        },
    )


RESERVATION_FIELDS = [
    "reservation_id", "receipt_ref", "receipt_sha256", "gpu_ref", "cpu_units",
    "ram_bytes", "vram_bytes", "disk_bytes", "thermal_state", "power_state",
    "admission_state", "issued_at", "expires_at",
]
AUTH_FIELDS = [
    "authorization_id", "authorization_revision", "authorization_sha256",
    "authority_kind", "project_id", "run_intent_sha256", "run_revision_sha256",
    "training_input_snapshot_sha256", "engine_admission_sha256", "config_sha256",
    "current_consent_rights_license_sha256", "scope", "issued_at", "expires_at",
    "one_shot", "replay_policy", "evidence_ref", "evidence_sha256",
]
PROCESS_FIELDS = [
    "process_observation_id", "job_id", "process_identity_sha256",
    "observation_state", "gpu_process_present", "observed_at", "evidence_ref",
    "evidence_sha256",
]
CHECKPOINT_BINDING_FIELDS = [
    "checkpoint_id", "checkpoint_revision", "canonical_owner_ref",
    "canonical_owner_sha256", "persistence_receipt_ref", "persistence_receipt_sha256",
    "artifact_checksum_sha256", "training_input_snapshot_sha256", "base_model_sha256",
    "runtime_sha256", "code_sha256", "config_sha256", "license_evaluation_sha256",
    "consent_evaluation_sha256", "training_step", "optimizer_state_sha256",
    "resume_compatibility_sha256", "resume_decision", "logical_uri",
]


def unresolved(record_type: str, fields: list[str]) -> dict:
    return add_training_digest(
        {
            "record_type": record_type,
            "contract_state": "CANONICAL_REF_NOT_PROVIDED",
            **{field: None for field in fields},
        },
        "binding_sha256",
    )


def training_run_revision(intent_value: dict, job_value: dict) -> dict:
    return add_training_digest(
        {
            "record_type": "TrainingRunRevision",
            "run_revision_id": "training-run-revision:task084:1",
            "revision": 1,
            "parent_revision_sha256": None,
            "run_intent_sha256": intent_value["intent_sha256"],
            "state": "DRAFT",
            "durable_job_binding": job_value,
            "resource_reservation_binding": unresolved(
                "ExecutionResourceReservationBinding", RESERVATION_FIELDS
            ),
            "execution_authorization_binding": unresolved(
                "TrainingExecutionAuthorizationBinding", AUTH_FIELDS
            ),
            "process_observation_binding": unresolved(
                "GPUProcessObservationBinding", PROCESS_FIELDS
            ),
            "checkpoint_artifact_binding": unresolved(
                "CheckpointArtifactBinding", CHECKPOINT_BINDING_FIELDS
            ),
            "compute_terminal_receipt_sha256": None,
            "model_candidate_sha256": None,
            "evaluation_receipt_sha256": None,
            "owner_approval_binding_sha256": None,
            "reason_codes": [],
            "created_at": "2026-09-05T23:45:00Z",
            "execution_started": False,
        },
        "revision_sha256",
    )


CHECKPOINT_EXPECTED = [
    {
        "entry_id": "checkpoint-weight",
        "role": "MODEL_WEIGHT",
        "index": 0,
        "relative_file": "encrypted/checkpoint-weight.bin",
    },
    {
        "entry_id": "optimizer-state",
        "role": "OPTIMIZER_STATE",
        "index": 1,
        "relative_file": "encrypted/optimizer-state.bin",
    },
]
TERMINAL_EXPECTED = [
    {
        "entry_id": "model-weight",
        "role": "MODEL_WEIGHT",
        "index": 0,
        "relative_file": "encrypted/model-weight.bin",
    },
    {
        "entry_id": "model-config",
        "role": "CONFIG",
        "index": 1,
        "relative_file": "encrypted/model-config.bin",
    },
]
DESTINATION_IDENTITIES = {
    "destination_root_identity_sha256": H("destination-root"),
    "destination_ancestor_identity_sha256": H("destination-ancestor"),
    "destination_target_identity_sha256": H("destination-target"),
    "destination_pinned_readback_sha256": H("destination-readback"),
}
TASK046_CHECKPOINT_BINDING_SHA256 = H("task046-checkpoint-binding")


def make_plan(**changes: object):
    snapshot = training_snapshot()
    intent_value = training_intent(snapshot)
    job_value = job_binding()
    run_value = training_run_revision(intent_value, job_value)
    kwargs = {
        "plan_id": "task084-plan:1",
        "training_run_head_sha256": run_value["revision_sha256"],
        "task043_job_readback_sha256": H("task043-job-readback"),
        "task043_job_head_sha256": H("task043-job-head"),
        "task083_reservation_plan_sha256": H("task083-plan"),
        "destination_coordinate": "artifact-destination:voice-models",
        "custody_policy_sha256": H("custody-policy"),
        "encryption_policy_sha256": H("encryption-policy"),
        "aead_suite": "AES_256_GCM",
        "cipher_backend_revision_sha256": H("cipher-backend"),
        "principal_scope_sha256": H("principal-scope"),
        "key_scope_sha256": H("key-scope"),
        "dacl_policy_sha256": H("dacl-policy"),
        "checkpoint_expected_entries": CHECKPOINT_EXPECTED,
        "terminal_expected_entries": TERMINAL_EXPECTED,
        "max_file_count": 8,
        "max_total_plain_bytes": 10_000_000,
        "max_total_cipher_bytes": 11_000_000,
        "compiled_at": NOW,
    }
    kwargs.update(changes)
    return compile_output_artifact_destination_plan(
        intent_value, run_value, snapshot, job_value, **kwargs
    )


def file_observation(expected: dict, *, label: str) -> dict:
    return {
        **expected,
        "plain_byte_count": 100 + expected["index"],
        "plain_sha256": H(f"plain-{label}-{expected['entry_id']}"),
        "cipher_byte_count": 132 + expected["index"],
        "cipher_sha256": H(f"cipher-{label}-{expected['entry_id']}"),
        "nonce_sha256": H(f"nonce-{label}-{expected['entry_id']}"),
        "aead_authentication_evidence_sha256": H(
            f"aead-{label}-{expected['entry_id']}"
        ),
        "envelope_evidence_sha256": H(f"envelope-{label}-{expected['entry_id']}"),
        "opened_physical_identity_sha256": H(
            f"physical-{label}-{expected['entry_id']}"
        ),
        "ancestor_identity_sha256": DESTINATION_IDENTITIES[
            "destination_target_identity_sha256"
        ],
        "regular_file": True,
        "nlink": 1,
        "reparse_point": False,
        "opened_identity_pinned": True,
        "file_flush_evidence_sha256": H(f"file-flush-{label}-{expected['entry_id']}"),
        "directory_flush_evidence_sha256": H(
            f"directory-flush-{label}-{expected['entry_id']}"
        ),
        "pinned_readback_sha256": H(f"reread-{label}-{expected['entry_id']}"),
    }


def inventory_identity_fields(label: str) -> dict:
    return {
        **DESTINATION_IDENTITIES,
        "manifest_nonce_sha256": H(f"manifest-nonce-{label}"),
        "manifest_envelope_evidence_sha256": H(f"manifest-envelope-{label}"),
        "manifest_opened_physical_identity_sha256": H(f"manifest-physical-{label}"),
        "manifest_ancestor_identity_sha256": DESTINATION_IDENTITIES[
            "destination_target_identity_sha256"
        ],
        "manifest_regular_file": True,
        "manifest_nlink": 1,
        "manifest_reparse_point": False,
        "manifest_opened_identity_pinned": True,
        "manifest_file_flush_evidence_sha256": H(f"manifest-file-flush-{label}"),
        "manifest_directory_flush_evidence_sha256": H(f"manifest-dir-flush-{label}"),
        "manifest_pinned_readback_sha256": H(f"manifest-reread-{label}"),
    }


def artifact_expected_entries(
    *,
    label: str,
    variant: ArtifactVariant,
    checkpoint_index: int | None = None,
) -> list[dict]:
    if variant is ArtifactVariant.TERMINAL:
        return copy.deepcopy(TERMINAL_EXPECTED)
    assert checkpoint_index is not None
    return task084._checkpoint_scoped_entries(
        CHECKPOINT_EXPECTED,
        checkpoint_index=checkpoint_index,
        producer_event_sha256=H(f"producer-{label}"),
    )


def checkpoint_manifest_relative_file(label: str, checkpoint_index: int) -> str:
    producer_event_sha256_hex = H(f"producer-{label}").removeprefix("sha256:")
    return (
        f"checkpoints/{checkpoint_index}/"
        f"{producer_event_sha256_hex}/manifest.json.enc"
    )


def fixture_inventory(
    plan,
    *,
    label: str,
    variant: ArtifactVariant,
    checkpoint_index: int | None = None,
):
    expected = artifact_expected_entries(
        label=label, variant=variant, checkpoint_index=checkpoint_index
    )
    manifest_relative_file = (
        checkpoint_manifest_relative_file(label, checkpoint_index)
        if variant is ArtifactVariant.CHECKPOINT
        else f"manifests/{label}.json.enc"
    )
    return compile_fixture_inventory(
        plan,
        inventory_id=f"inventory-{label}",
        producer_event_sha256=H(f"producer-{label}"),
        artifact_variant=variant,
        checkpoint_index=checkpoint_index,
        **inventory_identity_fields(label),
        entries=[file_observation(item, label=label) for item in expected],
        manifest_relative_file=manifest_relative_file,
        manifest_sha256=H(f"manifest-{label}"),
        manifest_authentication_evidence_sha256=H(f"manifest-auth-{label}"),
        manifest_confidentiality="ENCRYPTED_AUTHENTICATED",
    )


def terminal_receipt(plan, *, state: str = "COMPLETED", registered: bool = False) -> dict:
    plan_dict = plan.to_dict()
    return add_training_digest(
        {
            "record_type": "TrainingComputeTerminalReceipt",
            "receipt_id": "training-terminal:1",
            "run_intent_sha256": plan_dict["run_intent_sha256"],
            "run_revision_sha256": plan_dict["training_run_revision_sha256"],
            "job_binding_sha256": plan_dict["job_binding_sha256"],
            "compute_state": state,
            "last_checkpoint_binding_sha256": TASK046_CHECKPOINT_BINDING_SHA256,
            "started_at": "2026-09-06T00:01:30Z",
            "terminal_at": "2026-09-06T00:04:30Z",
            "reason_codes": [],
            "artifact_registered": registered,
        },
        "receipt_sha256",
    )


def activate(ledger):
    return ledger.activate_destination(
        request_id="activate-1",
        **DESTINATION_IDENTITIES,
        observed_at=ACTIVE_AT,
    )


def register_producer(
    ledger,
    plan,
    *,
    producer_sha256: str,
    variant: ArtifactVariant,
    observed_at: str,
    checkpoint_index: int | None = None,
    terminal_value: dict | None = None,
) -> None:
    ledger.register_fixture_producer_event(
        producer_event_sha256=producer_sha256,
        artifact_variant=variant,
        training_run_head_sha256=plan.to_dict()["training_run_head_sha256"],
        task043_job_readback_sha256=plan.to_dict()["task043_job_readback_sha256"],
        task043_job_head_sha256=plan.to_dict()["task043_job_head_sha256"],
        checkpoint_index=checkpoint_index,
        task046_checkpoint_binding_sha256=(
            TASK046_CHECKPOINT_BINDING_SHA256
            if variant is ArtifactVariant.CHECKPOINT
            else None
        ),
        task046_terminal_receipt_sha256=(
            terminal_value["receipt_sha256"] if terminal_value is not None else None
        ),
        observed_at=observed_at,
    )


def issue_and_begin(
    ledger,
    plan,
    *,
    variant: ArtifactVariant,
    label: str,
    checkpoint_index: int | None = None,
    training_step: int | None = None,
    progress_ppm: int | None = None,
):
    terminal_value = (
        terminal_receipt(plan) if variant is ArtifactVariant.TERMINAL else None
    )
    producer_sha256 = H(f"producer-{label}")
    register_producer(
        ledger,
        plan,
        producer_sha256=producer_sha256,
        variant=variant,
        checkpoint_index=checkpoint_index,
        terminal_value=terminal_value,
        observed_at=(
            "2026-09-06T00:01:30Z"
            if label == "checkpoint-1"
            else "2026-09-06T00:04:30Z"
        ),
    )
    lease = ledger.issue_write_lease(
        request_id=f"issue-{label}",
        lease_id=f"lease-{label}",
        producer_event_sha256=producer_sha256,
        artifact_variant=variant,
        checkpoint_index=checkpoint_index,
        training_step=training_step,
        progress_ppm=progress_ppm,
        task046_terminal_receipt=terminal_value,
        issued_at=ISSUED_AT if label == "checkpoint-1" else "2026-09-06T00:05:00Z",
        expires_at=EXPIRES_AT,
    )
    assert isinstance(lease, Task084FixtureModelArtifactWriteLeaseV1)
    ledger.begin_publish(
        lease,
        request_id=f"begin-{label}",
        observed_at=OPEN_AT if label == "checkpoint-1" else "2026-09-06T00:06:00Z",
    )
    return lease


def complete_artifact(ledger, plan, lease, *, label: str, sealed_at: str):
    expected = artifact_expected_entries(
        label=label,
        variant=lease.artifact_variant,
        checkpoint_index=lease.checkpoint_index,
    )
    observations = []
    for item in expected:
        handle = ledger.open_entry(lease, entry_id=item["entry_id"])
        observation = file_observation(item, label=label)
        ledger.complete_entry(lease, handle, observation)
        observations.append(observation)
    inventory = compile_fixture_inventory(
        plan,
        inventory_id=f"inventory-{label}",
        producer_event_sha256=H(f"producer-{label}"),
        artifact_variant=lease.artifact_variant,
        checkpoint_index=lease.checkpoint_index,
        **DESTINATION_IDENTITIES,
        entries=observations,
        manifest_relative_file=(
            checkpoint_manifest_relative_file(label, lease.checkpoint_index)
            if lease.artifact_variant is ArtifactVariant.CHECKPOINT
            else f"manifests/{label}.json.enc"
        ),
        manifest_sha256=H(f"manifest-{label}"),
        manifest_nonce_sha256=H(f"manifest-nonce-{label}"),
        manifest_authentication_evidence_sha256=H(f"manifest-auth-{label}"),
        manifest_envelope_evidence_sha256=H(f"manifest-envelope-{label}"),
        manifest_confidentiality="ENCRYPTED_AUTHENTICATED",
        manifest_opened_physical_identity_sha256=H(f"manifest-physical-{label}"),
        manifest_ancestor_identity_sha256=DESTINATION_IDENTITIES[
            "destination_target_identity_sha256"
        ],
        manifest_regular_file=True,
        manifest_nlink=1,
        manifest_reparse_point=False,
        manifest_opened_identity_pinned=True,
        manifest_file_flush_evidence_sha256=H(f"manifest-file-flush-{label}"),
        manifest_directory_flush_evidence_sha256=H(f"manifest-dir-flush-{label}"),
        manifest_pinned_readback_sha256=H(f"manifest-reread-{label}"),
    )
    verification = ledger.verify_manifest_last(lease, inventory)
    return ledger.complete_publish(
        lease,
        inventory,
        verification,
        request_id=f"complete-{label}",
        task083_reservation_receipt_sha256=H("task083-reservation-receipt"),
        sealed_at=sealed_at,
    )


def checkpoint(ledger, plan):
    lease = issue_and_begin(
        ledger,
        plan,
        variant=ArtifactVariant.CHECKPOINT,
        label="checkpoint-1",
        checkpoint_index=1,
        training_step=100,
        progress_ppm=250_000,
    )
    receipt = complete_artifact(
        ledger, plan, lease, label="checkpoint-1", sealed_at=SEALED_AT
    )
    assert isinstance(receipt, Task084FixtureModelCheckpointCustodyReceiptV1)
    return receipt


def sealed_ledger():
    plan = make_plan()
    ledger = open_fixture_custody(plan)
    activate(ledger)
    checkpoint_receipt = checkpoint(ledger, plan)
    lease = issue_and_begin(
        ledger,
        plan,
        variant=ArtifactVariant.TERMINAL,
        label="terminal-1",
    )
    terminal = complete_artifact(
        ledger,
        plan,
        lease,
        label="terminal-1",
        sealed_at="2026-09-06T00:07:00Z",
    )
    assert isinstance(terminal, Task084FixtureModelArtifactCustodyReceiptV1)
    return plan, ledger, checkpoint_receipt, terminal


def schema_validator() -> Draft202012Validator:
    schema = json.loads(PUBLIC_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def rehash(record: dict, field: str, domain: bytes) -> None:
    record[field] = task084._digest(record, field, domain)


def test_destination_plan_is_deterministic_deeply_immutable_and_body_free() -> None:
    first = make_plan()
    second = make_plan()
    assert first.to_dict() == second.to_dict()
    assert first.to_dict()["production_eligible"] is False
    assert first.to_dict()["resource_effect_count"] == 0
    changed = first.to_dict()
    changed["checkpoint_expected_entries"][0]["entry_id"] = "tampered"
    assert first.to_dict()["checkpoint_expected_entries"][0]["entry_id"] == "checkpoint-weight"
    assert_effect_zero_surface(first)
    exported = first.canonical_bytes().decode("utf-8")
    for forbidden in ("C:\\", "/home/", "private_key", "raw_model", "secret", "token"):
        assert forbidden not in exported


def test_current_source_production_and_all_load_purposes_are_exact_blocked_effect0() -> None:
    plan = make_plan()
    admission = compile_production_custody_admission(plan, evaluated_at=ACTIVE_AT)
    assert admission.to_dict()["decision"] == "BLOCKED"
    assert len(admission.to_dict()["reason_codes"]) == 7
    assert "TASK084_WINDOWS_BACKEND_NOT_AVAILABLE" in admission.to_dict()["reason_codes"]
    assert_effect_zero_surface(admission)
    fields = {
        LoadPurpose.TRAINING_RESUME: {
            "checkpoint_custody_receipt_sha256",
            "job_head_sha256",
            "recovery_readback_sha256",
            "task083_reservation_receipt_sha256",
            "h3_v2_authorization_sha256",
            "resume_compound_operation_sha256",
        },
        LoadPurpose.HELD_OUT_EVALUATION: {
            "terminal_custody_receipt_sha256",
            "model_artifact_binding_sha256",
            "pending_candidate_sha256",
            "evaluation_authorization_sha256",
            "evaluation_operation_sha256",
        },
        LoadPurpose.LOCAL_NARRATION_INFERENCE: {
            "terminal_custody_receipt_sha256",
            "model_artifact_binding_sha256",
            "h4_v2_approval_sha256",
            "fine_tuned_model_binding_sha256",
            "task075_admission_sha256",
            "current_consent_rights_sha256",
        },
    }
    for purpose, names in fields.items():
        result = compile_model_load_admission(
            plan,
            purpose=purpose,
            bindings={name: H(name) for name in names},
            evaluated_at=ACTIVE_AT,
        )
        assert result.to_dict()["decision"] == "BLOCKED"
        assert len(result.to_dict()["reason_codes"]) == 8
        assert_effect_zero_surface(result)
        missing = {name: H(name) for name in sorted(names)[1:]}
        with pytest.raises(ValueError, match="incomplete|cross-purpose"):
            compile_model_load_admission(
                plan,
                purpose=purpose,
                bindings=missing,
                evaluated_at=ACTIVE_AT,
            )


def test_plan_rejects_cross_project_snapshot_private_path_and_output_mismatch() -> None:
    snapshot = training_snapshot()
    intent = training_intent(snapshot)
    job_value = job_binding()
    run_value = training_run_revision(intent, job_value)
    wrong_snapshot = copy.deepcopy(snapshot)
    wrong_snapshot["project_id"] = "project:other"
    wrong_snapshot = add_dataset_digest(
        {k: v for k, v in wrong_snapshot.items() if k != "snapshot_sha256"},
        "snapshot_sha256",
    )
    with pytest.raises(ValueError, match="project mismatch|snapshot digest mismatch"):
        compile_output_artifact_destination_plan(
            intent,
            run_value,
            wrong_snapshot,
            job_value,
            plan_id="plan:wrong",
            training_run_head_sha256=run_value["revision_sha256"],
            task043_job_readback_sha256=H("task043-job-readback"),
            task043_job_head_sha256=H("task043-job-head"),
            task083_reservation_plan_sha256=H("reservation"),
            destination_coordinate="artifact-destination:voice-models",
            custody_policy_sha256=H("custody"),
            encryption_policy_sha256=H("encryption"),
            aead_suite="AES_256_GCM",
            cipher_backend_revision_sha256=H("backend"),
            principal_scope_sha256=H("principal"),
            key_scope_sha256=H("key"),
            dacl_policy_sha256=H("dacl"),
            checkpoint_expected_entries=CHECKPOINT_EXPECTED,
            terminal_expected_entries=TERMINAL_EXPECTED,
            max_file_count=8,
            max_total_plain_bytes=1000,
            max_total_cipher_bytes=2000,
            compiled_at=NOW,
        )
    with pytest.raises(ValueError, match="logical destination|coordinate|body-free"):
        make_plan(destination_coordinate="C:/private/model")


@pytest.mark.parametrize(
    ("relative_file", "message"),
    [
        ("a/b/c/d/e/f.bin", "namespace path budget"),
        ("/".join(["a" * 128] * 3 + ["b" * 38]), "namespace path budget"),
        ("MANIFEST.JSON.ENC", "reserved manifest"),
    ],
)
def test_checkpoint_plan_rejects_unmaterializable_base_paths(
    relative_file: str, message: str
) -> None:
    entries = copy.deepcopy(CHECKPOINT_EXPECTED)
    entries[0]["relative_file"] = relative_file
    with pytest.raises(ValueError, match=message):
        make_plan(checkpoint_expected_entries=entries)


def test_checkpoint_plan_path_budget_accepts_the_closed_length_boundary() -> None:
    boundary_file = "/".join(["a" * 128] * 3 + ["b" * 37])
    assert len(boundary_file) == task084.MAX_CHECKPOINT_BASE_RELATIVE_FILE_LENGTH
    entries = copy.deepcopy(CHECKPOINT_EXPECTED)
    entries[0]["relative_file"] = boundary_file
    plan = make_plan(checkpoint_expected_entries=entries)
    materialized = task084._checkpoint_scoped_entries(
        plan.to_dict()["checkpoint_expected_entries"],
        checkpoint_index=task084.MAX_CHECKPOINT_INDEX,
        producer_event_sha256=H("boundary-producer"),
    )
    assert len(materialized[0]["relative_file"]) == 512
    assert task084._relative_file(materialized[0]["relative_file"])
    with pytest.raises(ValueError, match="checkpoint_index"):
        task084._checkpoint_scoped_entries(
            CHECKPOINT_EXPECTED,
            checkpoint_index=task084.MAX_CHECKPOINT_INDEX + 1,
            producer_event_sha256=H("overflow-producer"),
        )


@pytest.mark.parametrize(
    "relative_file",
    [
        "a/b/c/d/e/f.bin",
        "/".join(["a" * 128] * 3 + ["b" * 38]),
        "MANIFEST.JSON.ENC",
    ],
)
def test_schema_rejects_unmaterializable_checkpoint_base_paths(
    relative_file: str,
) -> None:
    raw = make_plan().to_dict()
    raw["checkpoint_expected_entries"][0]["relative_file"] = relative_file
    assert list(schema_validator().iter_errors(raw))


def test_schema_rejects_checkpoint_index_above_closed_path_budget() -> None:
    raw = fixture_inventory(
        make_plan(),
        label="checkpoint-schema-index",
        variant=ArtifactVariant.CHECKPOINT,
        checkpoint_index=1,
    ).to_dict()
    raw["checkpoint_index"] = task084.MAX_CHECKPOINT_INDEX + 1
    assert list(schema_validator().iter_errors(raw))


def test_checkpoint_then_terminal_manifest_last_lifecycle_and_readback() -> None:
    plan, ledger, first_checkpoint, terminal = sealed_ledger()
    checkpoint_body = first_checkpoint.to_dict()
    assert checkpoint_body["receipt_role"] == "MODEL_CHECKPOINT_CUSTODY"
    assert checkpoint_body["task046_terminal_receipt_sha256"] is None
    assert checkpoint_body["checkpoint_count"] == 1
    terminal_body = terminal.to_dict()
    assert terminal_body["receipt_role"] == "MODEL_ARTIFACT_CUSTODY"
    assert terminal_body["checkpoint_index"] is None
    assert terminal_body["last_checkpoint_receipt_sha256"] == checkpoint_body["receipt_sha256"]
    assert terminal_body["model_artifact_binding_created"] is False
    assert terminal_body["candidate_registered"] is False
    readback = ledger.readback(read_back_at="2026-09-06T00:08:00Z")
    assert readback.to_dict()["phase"] == "TERMINAL_SEALED"
    assert readback.to_dict()["terminal_receipt_sha256"] == terminal_body["receipt_sha256"]
    for item in (first_checkpoint, terminal, readback):
        assert_effect_zero_surface(item)
    assert plan.to_dict()["fixture_only"] is True


def test_terminal_requires_at_least_one_checkpoint_and_successful_current_terminal() -> None:
    plan = make_plan()
    ledger = open_fixture_custody(plan)
    activate(ledger)
    with pytest.raises(ValueError, match="at least one"):
        ledger.issue_write_lease(
            request_id="terminal-before-checkpoint",
            lease_id="terminal-before-checkpoint",
            producer_event_sha256=H("terminal-before-checkpoint"),
            artifact_variant=ArtifactVariant.TERMINAL,
            issued_at=ISSUED_AT,
            expires_at=EXPIRES_AT,
            task046_terminal_receipt=terminal_receipt(plan),
        )
    checkpoint(ledger, plan)
    for state in ("FAILED", "UNKNOWN", "CANCELLED"):
        with pytest.raises(ValueError, match="unregistered COMPLETED"):
            ledger.issue_write_lease(
                request_id=f"bad-terminal-{state}",
                lease_id=f"bad-terminal-{state}",
                producer_event_sha256=H(f"bad-terminal-{state}"),
                artifact_variant=ArtifactVariant.TERMINAL,
                issued_at="2026-09-06T00:05:00Z",
                expires_at=EXPIRES_AT,
                task046_terminal_receipt=terminal_receipt(plan, state=state),
            )
    with pytest.raises(ValueError, match="artifact_registered must be false"):
        ledger.issue_write_lease(
            request_id="bad-terminal-pre-registered",
            lease_id="bad-terminal-pre-registered",
            producer_event_sha256=H("bad-terminal-pre-registered"),
            artifact_variant=ArtifactVariant.TERMINAL,
            issued_at="2026-09-06T00:05:00Z",
            expires_at=EXPIRES_AT,
            task046_terminal_receipt=terminal_receipt(plan, registered=True),
        )


def test_multiple_checkpoints_use_distinct_immutable_namespaces() -> None:
    plan = make_plan()
    ledger = open_fixture_custody(plan)
    activate(ledger)
    first = checkpoint(ledger, plan)
    second_lease = issue_and_begin(
        ledger,
        plan,
        variant=ArtifactVariant.CHECKPOINT,
        label="checkpoint-2",
        checkpoint_index=2,
        training_step=200,
        progress_ppm=500_000,
    )
    second = complete_artifact(
        ledger,
        plan,
        second_lease,
        label="checkpoint-2",
        sealed_at="2026-09-06T00:07:00Z",
    )
    assert isinstance(second, Task084FixtureModelCheckpointCustodyReceiptV1)
    assert first.to_dict()["checkpoint_namespace_sha256"] != second.to_dict()[
        "checkpoint_namespace_sha256"
    ]
    first_paths = artifact_expected_entries(
        label="checkpoint-1",
        variant=ArtifactVariant.CHECKPOINT,
        checkpoint_index=1,
    )
    with pytest.raises(ValueError, match="allowlist"):
        compile_fixture_inventory(
            plan,
            inventory_id="inventory-checkpoint-reuse",
            producer_event_sha256=H("producer-checkpoint-2"),
            artifact_variant="CHECKPOINT",
            checkpoint_index=2,
            **inventory_identity_fields("checkpoint-reuse"),
            entries=[
                file_observation(item, label="checkpoint-reuse")
                for item in first_paths
            ],
            manifest_relative_file=checkpoint_manifest_relative_file(
                "checkpoint-2", 2
            ),
            manifest_sha256=H("manifest-checkpoint-reuse"),
            manifest_authentication_evidence_sha256=H(
                "manifest-auth-checkpoint-reuse"
            ),
            manifest_confidentiality="ENCRYPTED_AUTHENTICATED",
        )


def test_exact_duplicate_returns_readback_and_changed_replay_is_rejected() -> None:
    plan = make_plan()
    ledger = open_fixture_custody(plan)
    first = activate(ledger)
    assert isinstance(first, Task084FixtureCustodyEventV1)
    duplicate = activate(ledger)
    assert isinstance(duplicate, Task084FixtureCustodyReadbackV1)
    with pytest.raises(ValueError, match="replay payload mismatch"):
        ledger.activate_destination(
            request_id="activate-1",
            destination_root_identity_sha256=H("different-destination"),
            destination_ancestor_identity_sha256=DESTINATION_IDENTITIES[
                "destination_ancestor_identity_sha256"
            ],
            destination_target_identity_sha256=DESTINATION_IDENTITIES[
                "destination_target_identity_sha256"
            ],
            destination_pinned_readback_sha256=DESTINATION_IDENTITIES[
                "destination_pinned_readback_sha256"
            ],
            observed_at=ACTIVE_AT,
        )
    register_producer(
        ledger,
        plan,
        producer_sha256=H("producer-duplicate"),
        variant=ArtifactVariant.CHECKPOINT,
        checkpoint_index=1,
        observed_at="2026-09-06T00:01:30Z",
    )
    lease = ledger.issue_write_lease(
        request_id="issue-duplicate",
        lease_id="lease-duplicate",
        producer_event_sha256=H("producer-duplicate"),
        artifact_variant="CHECKPOINT",
        checkpoint_index=1,
        training_step=1,
        progress_ppm=1,
        issued_at=ISSUED_AT,
        expires_at=EXPIRES_AT,
    )
    assert isinstance(lease, Task084FixtureModelArtifactWriteLeaseV1)
    replay = ledger.issue_write_lease(
        request_id="issue-duplicate",
        lease_id="lease-duplicate",
        producer_event_sha256=H("producer-duplicate"),
        artifact_variant="CHECKPOINT",
        checkpoint_index=1,
        training_step=1,
        progress_ppm=1,
        issued_at=ISSUED_AT,
        expires_at=EXPIRES_AT,
    )
    assert isinstance(replay, Task084FixtureCustodyReadbackV1)
    ledger.begin_publish(
        lease, request_id="begin-duplicate", observed_at=OPEN_AT
    )
    complete_artifact(
        ledger, plan, lease, label="duplicate", sealed_at=SEALED_AT
    )
    post_seal_replay = ledger.issue_write_lease(
        request_id="issue-duplicate",
        lease_id="lease-duplicate",
        producer_event_sha256=H("producer-duplicate"),
        artifact_variant="CHECKPOINT",
        checkpoint_index=1,
        training_step=1,
        progress_ppm=1,
        issued_at=ISSUED_AT,
        expires_at=EXPIRES_AT,
    )
    assert isinstance(post_seal_replay, Task084FixtureCustodyReadbackV1)
    assert post_seal_replay.to_dict()["phase"] == "CHECKPOINT_PUBLISHED"


def test_write_lease_and_entry_handles_are_factory_only_nonserializable_one_shot() -> None:
    plan = make_plan()
    ledger = open_fixture_custody(plan)
    activate(ledger)
    lease = issue_and_begin(
        ledger,
        plan,
        variant=ArtifactVariant.CHECKPOINT,
        label="checkpoint-1",
        checkpoint_index=1,
        training_step=10,
        progress_ppm=100,
    )
    assert lease.state is LeaseState.OPEN_STARTED
    assert "redacted" in repr(lease)
    with pytest.raises(TypeError):
        pickle.dumps(lease)
    with pytest.raises(TypeError):
        copy.copy(lease)
    handle = ledger.open_entry(lease, entry_id="checkpoint-weight")
    assert handle.private_handle_returned is False
    with pytest.raises(ValueError, match="twice"):
        ledger.open_entry(lease, entry_id="checkpoint-weight")
    with pytest.raises(TypeError):
        pickle.dumps(handle)
    with pytest.raises(TypeError):
        Task084FixtureModelArtifactWriteLeaseV1(  # type: ignore[call-arg]
            ledger_nonce=object(),
            lease_id="forged",
            request_sha256=H("request"),
            producer_event_sha256=H("producer"),
            variant=ArtifactVariant.CHECKPOINT,
            checkpoint_index=1,
            training_step=1,
            progress_ppm=1,
            task046_terminal_receipt_sha256=None,
            issued_at=ISSUED_AT,
            expires_at=EXPIRES_AT,
            expected_revision=1,
            expected_head_sha256=H("head"),
            key=object(),
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("regular_file", False, "regular_file"),
        ("nlink", 2, "nlink"),
        ("reparse_point", True, "reparse_point"),
        ("opened_identity_pinned", False, "opened_identity_pinned"),
        ("relative_file", "../private.bin", "relative"),
        ("relative_file", "C:/private.bin", "relative"),
        ("relative_file", "CON.bin", "relative"),
        ("relative_file", "encrypted/model.bin:ads", "relative"),
    ],
)
def test_physical_and_relative_file_faults_fail_before_inventory(
    field: str, value: object, message: str
) -> None:
    plan = make_plan()
    expected = artifact_expected_entries(
        label="fault", variant=ArtifactVariant.CHECKPOINT, checkpoint_index=1
    )
    observation = file_observation(expected[0], label="fault")
    observation[field] = value
    with pytest.raises(ValueError, match=message):
        compile_fixture_inventory(
            plan,
            inventory_id="inventory-fault",
            producer_event_sha256=H("producer-fault"),
            artifact_variant="CHECKPOINT",
            checkpoint_index=1,
            **inventory_identity_fields("fault"),
            entries=[observation, file_observation(expected[1], label="fault")],
            manifest_relative_file=checkpoint_manifest_relative_file("fault", 1),
            manifest_sha256=H("manifest"),
            manifest_authentication_evidence_sha256=H("manifest-auth"),
            manifest_confidentiality="ENCRYPTED_AUTHENTICATED",
        )


def test_inventory_rejects_extra_missing_case_collision_shared_identity_and_manifest_injection() -> None:
    plan = make_plan()
    expected = artifact_expected_entries(
        label="inventory", variant=ArtifactVariant.CHECKPOINT, checkpoint_index=1
    )
    valid = [file_observation(item, label="inventory") for item in expected]
    with pytest.raises(ValueError, match="allowlist"):
        compile_fixture_inventory(
            plan,
            inventory_id="inventory-missing",
            producer_event_sha256=H("producer-inventory"),
            artifact_variant="CHECKPOINT",
            checkpoint_index=1,
            **inventory_identity_fields("inventory"),
            entries=valid[:1],
            manifest_relative_file=checkpoint_manifest_relative_file("inventory", 1),
            manifest_sha256=H("manifest"),
            manifest_authentication_evidence_sha256=H("manifest-auth"),
            manifest_confidentiality="ENCRYPTED_AUTHENTICATED",
        )
    plan_external_name = copy.deepcopy(valid)
    plan_external_name[0]["relative_file"] = "arbitrary/not-in-plan.bin"
    with pytest.raises(ValueError, match="allowlist"):
        compile_fixture_inventory(
            plan,
            inventory_id="inventory-plan-external-name",
            producer_event_sha256=H("producer-inventory"),
            artifact_variant="CHECKPOINT",
            checkpoint_index=1,
            **inventory_identity_fields("inventory"),
            entries=plan_external_name,
            manifest_relative_file=checkpoint_manifest_relative_file("inventory", 1),
            manifest_sha256=H("manifest"),
            manifest_authentication_evidence_sha256=H("manifest-auth"),
            manifest_confidentiality="ENCRYPTED_AUTHENTICATED",
        )
    reused_nonce = H("reused-aead-nonce")
    nonce_reuse = copy.deepcopy(valid)
    for item in nonce_reuse:
        item["nonce_sha256"] = reused_nonce
    nonce_identity = inventory_identity_fields("inventory")
    nonce_identity["manifest_nonce_sha256"] = reused_nonce
    with pytest.raises(ValueError, match="nonces must be unique"):
        compile_fixture_inventory(
            plan,
            inventory_id="inventory-nonce-reuse",
            producer_event_sha256=H("producer-inventory"),
            artifact_variant="CHECKPOINT",
            checkpoint_index=1,
            **nonce_identity,
            entries=nonce_reuse,
            manifest_relative_file=checkpoint_manifest_relative_file("inventory", 1),
            manifest_sha256=H("manifest"),
            manifest_authentication_evidence_sha256=H("manifest-auth"),
            manifest_confidentiality="ENCRYPTED_AUTHENTICATED",
        )
    collision = copy.deepcopy(valid)
    collision[1]["relative_file"] = collision[0]["relative_file"].upper()
    with pytest.raises(ValueError, match="case collision"):
        task084._validate_inventory(
            task084._with_digest(
                {
                    "record_type": "Task084FixtureArtifactInventoryV1",
                    "schema_version": 1,
                    "canonical_owner_task": "TASK-084",
                    "inventory_id": "inventory-collision",
                    "plan_sha256": plan.to_dict()["plan_sha256"],
                    "producer_event_sha256": H("producer-inventory"),
                    "artifact_variant": "CHECKPOINT",
                    "checkpoint_index": 1,
                    "checkpoint_namespace_sha256": task084._checkpoint_namespace_sha256(
                        plan.to_dict()["plan_sha256"],
                        1,
                        H("producer-inventory"),
                    ),
                    **inventory_identity_fields("inventory"),
                    "entries": collision,
                    "entry_count": 2,
                    "total_plain_bytes": sum(item["plain_byte_count"] for item in collision),
                    "total_cipher_bytes": sum(item["cipher_byte_count"] for item in collision),
                    "manifest_relative_file": checkpoint_manifest_relative_file(
                        "inventory", 1
                    ),
                    "manifest_sha256": H("manifest"),
                    "manifest_authentication_evidence_sha256": H("manifest-auth"),
                    "manifest_confidentiality": "ENCRYPTED_AUTHENTICATED",
                    "opened_physical_identity_set_sha256": task084._physical_identity_set_sha256(collision),
                    "unexpected_files_present": False,
                    "fixture_only": True,
                    "authority_created": False,
                    "resource_effect_count": 0,
                },
                "inventory_sha256",
                task084._INVENTORY_DOMAIN,
            )
        )
    shared = copy.deepcopy(valid)
    shared[1]["opened_physical_identity_sha256"] = shared[0]["opened_physical_identity_sha256"]
    with pytest.raises(ValueError, match="share one physical"):
        compile_fixture_inventory(
            plan,
            inventory_id="inventory-shared",
            producer_event_sha256=H("producer-inventory"),
            artifact_variant="CHECKPOINT",
            checkpoint_index=1,
            **inventory_identity_fields("inventory"),
            entries=shared,
            manifest_relative_file=checkpoint_manifest_relative_file("inventory", 1),
            manifest_sha256=H("manifest"),
            manifest_authentication_evidence_sha256=H("manifest-auth"),
            manifest_confidentiality="ENCRYPTED_AUTHENTICATED",
        )
    with pytest.raises(ValueError, match="namespace|distinct"):
        compile_fixture_inventory(
            plan,
            inventory_id="inventory-manifest-injected",
            producer_event_sha256=H("producer-inventory"),
            artifact_variant="CHECKPOINT",
            checkpoint_index=1,
            **inventory_identity_fields("inventory"),
            entries=valid,
            manifest_relative_file=valid[0]["relative_file"],
            manifest_sha256=H("manifest"),
            manifest_authentication_evidence_sha256=H("manifest-auth"),
            manifest_confidentiality="ENCRYPTED_AUTHENTICATED",
        )


def test_partial_entry_set_cannot_mint_manifest_verification_or_receipt() -> None:
    plan = make_plan()
    ledger = open_fixture_custody(plan)
    activate(ledger)
    lease = issue_and_begin(
        ledger,
        plan,
        variant=ArtifactVariant.CHECKPOINT,
        label="checkpoint-1",
        checkpoint_index=1,
        training_step=10,
        progress_ppm=100,
    )
    expected = artifact_expected_entries(
        label="checkpoint-1",
        variant=ArtifactVariant.CHECKPOINT,
        checkpoint_index=1,
    )
    first = expected[0]
    handle = ledger.open_entry(lease, entry_id=first["entry_id"])
    ledger.complete_entry(lease, handle, file_observation(first, label="partial"))
    full_inventory = compile_fixture_inventory(
        plan,
        inventory_id="inventory-partial",
        producer_event_sha256=H("producer-checkpoint-1"),
        artifact_variant="CHECKPOINT",
        checkpoint_index=1,
        **inventory_identity_fields("partial"),
        entries=[file_observation(item, label="partial") for item in expected],
        manifest_relative_file=checkpoint_manifest_relative_file("checkpoint-1", 1),
        manifest_sha256=H("manifest-partial"),
        manifest_authentication_evidence_sha256=H("manifest-auth-partial"),
        manifest_confidentiality="ENCRYPTED_AUTHENTICATED",
    )
    with pytest.raises(ValueError, match="completed entry handles|partial"):
        ledger.verify_manifest_last(lease, full_inventory)


def test_post_burn_ambiguity_is_terminal_and_retry_reopen_is_forbidden() -> None:
    plan = make_plan()
    ledger = open_fixture_custody(plan)
    activate(ledger)
    lease = issue_and_begin(
        ledger,
        plan,
        variant=ArtifactVariant.CHECKPOINT,
        label="checkpoint-1",
        checkpoint_index=1,
        training_step=10,
        progress_ppm=100,
    )
    event = ledger.mark_publish_completion_unknown(
        lease, request_id="unknown-1", observed_at=SEALED_AT
    )
    assert isinstance(event, Task084FixtureCustodyEventV1)
    assert ledger.phase is CustodyPhase.COMPLETION_UNKNOWN
    assert lease.state is LeaseState.COMPLETION_UNKNOWN
    duplicate = ledger.mark_publish_completion_unknown(
        lease, request_id="unknown-1", observed_at=SEALED_AT
    )
    assert isinstance(duplicate, Task084FixtureCustodyReadbackV1)
    assert duplicate.to_dict()["phase"] == "COMPLETION_UNKNOWN"
    with pytest.raises(ValueError, match="opened twice"):
        ledger.begin_publish(lease, request_id="reopen", observed_at="2026-09-06T00:05:00Z")
    with pytest.raises(ValueError, match="cannot issue"):
        ledger.issue_write_lease(
            request_id="retry-new-lease",
            lease_id="retry-new-lease",
            producer_event_sha256=H("producer-retry"),
            artifact_variant="CHECKPOINT",
            checkpoint_index=1,
            training_step=10,
            progress_ppm=100,
            issued_at="2026-09-06T00:05:00Z",
            expires_at=EXPIRES_AT,
        )


def test_post_burn_failed_closed_requires_exact_ledger_issued_negative_ack() -> None:
    plan = make_plan()
    ledger = open_fixture_custody(plan)
    activate(ledger)
    lease = issue_and_begin(
        ledger,
        plan,
        variant=ArtifactVariant.CHECKPOINT,
        label="checkpoint-1",
        checkpoint_index=1,
        training_step=10,
        progress_ppm=100,
    )
    with pytest.raises(ValueError, match="predates publish burn"):
        ledger.issue_durable_negative_acknowledgement(
            lease,
            acknowledgement_id="negative-ack:too-early",
            observed_at="2026-09-06T00:02:30Z",
        )
    ack = ledger.issue_durable_negative_acknowledgement(
        lease,
        acknowledgement_id="negative-ack:1",
        observed_at="2026-09-06T00:03:30Z",
    )
    forged = ack.to_dict()
    forged["acknowledgement_id"] = "negative-ack:forged"
    rehash(forged, "acknowledgement_sha256", task084._NEGATIVE_ACK_DOMAIN)
    with pytest.raises(ValueError, match="ledger-issued"):
        ledger.fail_closed_after_burn(
            lease,
            forged,
            request_id="fail-forged",
            observed_at=SEALED_AT,
        )
    event = ledger.fail_closed_after_burn(
        lease,
        ack,
        request_id="fail-proven",
        observed_at=SEALED_AT,
    )
    assert isinstance(event, Task084FixtureCustodyEventV1)
    assert ledger.phase is CustodyPhase.FAILED_CLOSED
    assert lease.state is LeaseState.FAILED_CLOSED


def test_event_chain_rejects_gap_fork_rollback_and_duplicate_revision() -> None:
    plan = make_plan()
    ledger = open_fixture_custody(plan)
    activate(ledger)
    lease = issue_and_begin(
        ledger,
        plan,
        variant=ArtifactVariant.CHECKPOINT,
        label="checkpoint-1",
        checkpoint_index=1,
        training_step=10,
        progress_ppm=100,
    )
    ledger.mark_publish_completion_unknown(
        lease, request_id="unknown-chain", observed_at=SEALED_AT
    )
    events = [event.to_dict() for event in ledger.event_chain()]
    replay = replay_fixture_event_chain(plan, events, read_back_at="2026-09-06T00:05:00Z")
    assert replay.to_dict()["phase"] == "COMPLETION_UNKNOWN"
    gap = copy.deepcopy(events)
    gap[1]["event_revision"] = 3
    rehash(gap[1], "event_sha256", task084._EVENT_DOMAIN)
    with pytest.raises(ValueError, match="gap|rollback|duplicate"):
        replay_fixture_event_chain(plan, gap, read_back_at="2026-09-06T00:05:00Z")
    fork = copy.deepcopy(events)
    fork[1]["predecessor_event_sha256"] = H("wrong-predecessor")
    rehash(fork[1], "event_sha256", task084._EVENT_DOMAIN)
    with pytest.raises(ValueError, match="fork|predecessor"):
        replay_fixture_event_chain(plan, fork, read_back_at="2026-09-06T00:05:00Z")
    rollback = copy.deepcopy(events)
    rollback[1]["event_at"] = "2026-09-05T23:59:59Z"
    rehash(rollback[1], "event_sha256", task084._EVENT_DOMAIN)
    with pytest.raises(ValueError, match="rollback"):
        replay_fixture_event_chain(plan, rollback, read_back_at="2026-09-06T00:05:00Z")


def test_production_receipt_and_readback_are_parse_only_and_consumer_remains_blocked() -> None:
    plan, ledger, _, fixture_terminal = sealed_ledger()
    production_receipt = fixture_terminal.to_dict()
    production_receipt.update(
        {
            "record_type": "Task084ModelArtifactCustodyReceiptV1",
            "fixture_only": False,
            "native_backend_invoked": True,
            "artifact_body_persisted": True,
            "resource_effect_count": 1,
        }
    )
    rehash(
        production_receipt,
        "receipt_sha256",
        task084._PRODUCTION_TERMINAL_RECEIPT_DOMAIN,
    )
    parsed_receipt = Task084ModelArtifactCustodyReceiptV1.from_dict(production_receipt)
    current_inventory = fixture_inventory(
        plan, label="terminal-1", variant=ArtifactVariant.TERMINAL
    )
    replaced_inventory = current_inventory.to_dict()
    replaced_inventory["manifest_opened_physical_identity_sha256"] = H(
        "replacement-manifest-physical"
    )
    rehash(replaced_inventory, "inventory_sha256", task084._INVENTORY_DOMAIN)
    with pytest.raises(ValueError, match="inventory/receipt commitment"):
        ledger.readback(
            read_back_at="2026-09-06T00:08:00Z",
            current_terminal_inventory=replaced_inventory,
        )
    fixture_readback = ledger.readback(
        read_back_at="2026-09-06T00:08:00Z",
        current_terminal_inventory=current_inventory,
    ).to_dict()
    production_readback = {
        **fixture_readback,
        "record_type": "Task084CustodyReadbackV1",
        "terminal_receipt_sha256": parsed_receipt.to_dict()["receipt_sha256"],
        "fixture_only": False,
        "native_backend_observed": True,
        "resource_effect_count": 1,
    }
    rehash(
        production_readback,
        "readback_sha256",
        task084._PRODUCTION_READBACK_DOMAIN,
    )
    parsed_readback = Task084CustodyReadbackV1.from_dict(production_readback)
    with pytest.raises(RuntimeError, match="CUSTODY_AWARE_CONSUMER_NOT_AVAILABLE"):
        validate_terminal_custody_for_model_artifact_binding(
            parsed_receipt, parsed_readback
        )
    replaced = production_readback.copy()
    replaced["current_manifest_opened_physical_identity_sha256"] = H(
        "replacement-manifest-physical"
    )
    rehash(replaced, "readback_sha256", task084._PRODUCTION_READBACK_DOMAIN)
    with pytest.raises(ValueError, match="receipt/readback mismatch"):
        validate_terminal_custody_for_model_artifact_binding(
            parsed_receipt, Task084CustodyReadbackV1.from_dict(replaced)
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", 2, "discriminator"),
        ("canonical_owner_task", "TASK-046", "discriminator"),
        ("receipt_role", "MODEL_ARTIFACT_CUSTODY", "discriminator|variant"),
        ("artifact_variant", "TERMINAL", "discriminator|variant"),
        ("task046_terminal_receipt_sha256", H("forbidden"), "forbids terminal"),
    ],
)
def test_checkpoint_receipt_rejects_wrong_discriminator_and_cross_variant(
    field: str, value: object, message: str
) -> None:
    plan = make_plan()
    ledger = open_fixture_custody(plan)
    activate(ledger)
    raw = checkpoint(ledger, plan).to_dict()
    raw[field] = value
    rehash(raw, "receipt_sha256", task084._FIXTURE_CHECKPOINT_RECEIPT_DOMAIN)
    with pytest.raises(ValueError, match=message):
        Task084FixtureModelCheckpointCustodyReceiptV1.from_dict(raw)


def test_fixture_load_lease_purpose_matrix_one_shot_and_completion_unknown() -> None:
    plan, ledger, checkpoint_receipt, terminal = sealed_ledger()
    resume_bindings = {
        "checkpoint_custody_receipt_sha256": checkpoint_receipt.to_dict()["receipt_sha256"],
        "job_head_sha256": H("job-head"),
        "recovery_readback_sha256": H("recovery-readback"),
        "task083_reservation_receipt_sha256": H("reservation-receipt"),
        "h3_v2_authorization_sha256": H("h3-v2"),
        "resume_compound_operation_sha256": H("resume-compound"),
    }
    ledger.register_fixture_current_load_bindings(
        purpose="TRAINING_RESUME",
        bindings=resume_bindings,
        observed_at="2026-09-06T00:08:30Z",
    )
    for field in resume_bindings:
        wrong_lineage = dict(resume_bindings)
        wrong_lineage[field] = H(f"wrong-{field}")
        with pytest.raises(ValueError, match="current load bindings|custody mismatch"):
            ledger.issue_fixture_load_lease(
                request_id=f"load-wrong-lineage-{field}",
                lease_id=f"load-wrong-lineage-{field}",
                purpose="TRAINING_RESUME",
                bindings=wrong_lineage,
                issued_at="2026-09-06T00:09:00Z",
                expires_at=EXPIRES_AT,
            )
    lease = ledger.issue_fixture_load_lease(
        request_id="load-resume",
        lease_id="load-resume",
        purpose="TRAINING_RESUME",
        bindings=resume_bindings,
        issued_at="2026-09-06T00:09:00Z",
        expires_at=EXPIRES_AT,
    )
    assert isinstance(lease, Task084FixtureModelLoadLeaseV1)
    with pytest.raises(ValueError, match="before issuance"):
        ledger.begin_fixture_load(
            lease,
            request_id="begin-load-resume-too-early",
            observed_at="2026-09-06T00:08:45Z",
        )
    opened = ledger.begin_fixture_load(
        lease, request_id="begin-load-resume", observed_at="2026-09-06T00:10:00Z"
    )
    assert isinstance(opened, Task084FixtureModelLoadOpenHandle)
    with pytest.raises(TypeError):
        pickle.dumps(opened)
    assert ledger.fixture_load_readback(
        lease, read_back_at="2026-09-06T00:10:00Z"
    ).to_dict()["state"] == "OPEN_STARTED"
    with pytest.raises(ValueError, match="close identity"):
        ledger.observe_fixture_load_completion(
            lease,
            opened,
            close_identity_sha256=H("wrong-close"),
            completion_readback_sha256=H("load-readback"),
            zeroization_evidence_sha256=H("zeroization"),
            observed_at="2026-09-06T00:10:15Z",
        )
    verification = ledger.observe_fixture_load_completion(
        lease,
        opened,
        close_identity_sha256=opened.handle_identity_sha256,
        completion_readback_sha256=H("load-readback"),
        zeroization_evidence_sha256=H("zeroization"),
        observed_at="2026-09-06T00:10:15Z",
    )
    assert isinstance(verification, Task084FixtureModelLoadCompletionVerification)
    completed = ledger.complete_fixture_load(
        lease,
        verification,
        request_id="complete-load-resume",
        completed_at="2026-09-06T00:10:30Z",
    )
    assert completed.to_dict()["state"] == "CONSUMED"
    duplicate_completion = ledger.complete_fixture_load(
        lease,
        verification,
        request_id="complete-load-resume",
        completed_at="2026-09-06T00:10:30Z",
    )
    assert duplicate_completion.to_dict()["state"] == "CONSUMED"
    with pytest.raises(ValueError, match="ledger-issued exact"):
        ledger.complete_fixture_load(
            lease,
            verification,
            request_id="complete-load-resume-new-request",
            completed_at="2026-09-06T00:10:30Z",
        )
    assert lease.state is LeaseState.CONSUMED
    with pytest.raises(ValueError, match="twice"):
        ledger.begin_fixture_load(
            lease,
            request_id="begin-load-resume-again",
            observed_at="2026-09-06T00:11:00Z",
        )
    evaluation_bindings = {
        "terminal_custody_receipt_sha256": terminal.to_dict()["receipt_sha256"],
        "model_artifact_binding_sha256": H("artifact-binding"),
        "pending_candidate_sha256": H("pending-candidate"),
        "evaluation_authorization_sha256": H("evaluation-auth"),
        "evaluation_operation_sha256": H("evaluation-operation"),
    }
    ledger.register_fixture_current_load_bindings(
        purpose="HELD_OUT_EVALUATION",
        bindings=evaluation_bindings,
        observed_at="2026-09-06T00:11:30Z",
    )
    evaluation = ledger.issue_fixture_load_lease(
        request_id="load-evaluation",
        lease_id="load-evaluation",
        purpose="HELD_OUT_EVALUATION",
        bindings=evaluation_bindings,
        issued_at="2026-09-06T00:12:00Z",
        expires_at=EXPIRES_AT,
    )
    assert isinstance(evaluation, Task084FixtureModelLoadLeaseV1)
    ledger.begin_fixture_load(
        evaluation,
        request_id="begin-load-evaluation",
        observed_at="2026-09-06T00:13:00Z",
    )
    ledger.mark_fixture_load_completion_unknown(
        evaluation,
        request_id="unknown-load-evaluation",
        observed_at="2026-09-06T00:13:30Z",
    )
    assert evaluation.state is LeaseState.COMPLETION_UNKNOWN
    cross_purpose = dict(evaluation_bindings)
    cross_purpose["h4_v2_approval_sha256"] = H("h4")
    with pytest.raises(ValueError, match="cross-purpose"):
        ledger.issue_fixture_load_lease(
            request_id="load-cross",
            lease_id="load-cross",
            purpose="HELD_OUT_EVALUATION",
            bindings=cross_purpose,
            issued_at="2026-09-06T00:14:00Z",
            expires_at=EXPIRES_AT,
        )
    inference_bindings = {
        "terminal_custody_receipt_sha256": terminal.to_dict()["receipt_sha256"],
        "model_artifact_binding_sha256": H("inference-artifact-binding"),
        "h4_v2_approval_sha256": H("inference-h4"),
        "fine_tuned_model_binding_sha256": H("fine-tuned-binding"),
        "task075_admission_sha256": H("task075-admission"),
        "current_consent_rights_sha256": H("current-consent-rights"),
    }
    ledger.register_fixture_current_load_bindings(
        purpose="LOCAL_NARRATION_INFERENCE",
        bindings=inference_bindings,
        observed_at="2026-09-06T00:14:00Z",
    )
    expiring = ledger.issue_fixture_load_lease(
        request_id="load-expiring",
        lease_id="load-expiring",
        purpose="LOCAL_NARRATION_INFERENCE",
        bindings=inference_bindings,
        issued_at="2026-09-06T00:14:30Z",
        expires_at="2026-09-06T00:15:00Z",
    )
    assert isinstance(expiring, Task084FixtureModelLoadLeaseV1)
    expiring_handle = ledger.begin_fixture_load(
        expiring,
        request_id="begin-load-expiring",
        observed_at="2026-09-06T00:14:40Z",
    )
    assert isinstance(expiring_handle, Task084FixtureModelLoadOpenHandle)
    expiring_verification = ledger.observe_fixture_load_completion(
        expiring,
        expiring_handle,
        close_identity_sha256=expiring_handle.handle_identity_sha256,
        completion_readback_sha256=H("expiring-readback"),
        zeroization_evidence_sha256=H("expiring-zeroization"),
        observed_at="2026-09-06T00:14:50Z",
    )
    ambiguous = ledger.complete_fixture_load(
        expiring,
        expiring_verification,
        request_id="complete-load-expiring",
        completed_at="2026-09-06T00:15:00Z",
    )
    assert ambiguous.to_dict()["state"] == "COMPLETION_UNKNOWN"
    assert plan.to_dict()["load_lease_created"] is False


def test_load_lease_issue_exact_duplicate_survives_custody_head_advance() -> None:
    plan = make_plan()
    ledger = open_fixture_custody(plan)
    activate(ledger)
    first = checkpoint(ledger, plan)
    bindings = {
        "checkpoint_custody_receipt_sha256": first.to_dict()["receipt_sha256"],
        "job_head_sha256": H("load-replay-job-head"),
        "recovery_readback_sha256": H("load-replay-readback"),
        "task083_reservation_receipt_sha256": H("load-replay-reservation"),
        "h3_v2_authorization_sha256": H("load-replay-h3"),
        "resume_compound_operation_sha256": H("load-replay-compound"),
    }
    ledger.register_fixture_current_load_bindings(
        purpose="TRAINING_RESUME",
        bindings=bindings,
        observed_at="2026-09-06T00:04:10Z",
    )
    lease = ledger.issue_fixture_load_lease(
        request_id="load-issue-before-head-advance",
        lease_id="load-before-head-advance",
        purpose="TRAINING_RESUME",
        bindings=bindings,
        issued_at="2026-09-06T00:04:20Z",
        expires_at=EXPIRES_AT,
    )
    assert isinstance(lease, Task084FixtureModelLoadLeaseV1)
    second_lease = issue_and_begin(
        ledger,
        plan,
        variant=ArtifactVariant.CHECKPOINT,
        label="checkpoint-2",
        checkpoint_index=2,
        training_step=200,
        progress_ppm=500_000,
    )
    complete_artifact(
        ledger,
        plan,
        second_lease,
        label="checkpoint-2",
        sealed_at="2026-09-06T00:07:00Z",
    )
    duplicate = ledger.issue_fixture_load_lease(
        request_id="load-issue-before-head-advance",
        lease_id="load-before-head-advance",
        purpose="TRAINING_RESUME",
        bindings=bindings,
        issued_at="2026-09-06T00:04:20Z",
        expires_at=EXPIRES_AT,
    )
    assert isinstance(duplicate, Task084FixtureModelLoadReadbackV1)
    assert duplicate.to_dict()["state"] == "ISSUED"


def test_concurrent_write_lease_issue_has_exactly_one_capability_winner() -> None:
    plan = make_plan()
    ledger = open_fixture_custody(plan)
    activate(ledger)
    register_producer(
        ledger,
        plan,
        producer_sha256=H("same-producer"),
        variant=ArtifactVariant.CHECKPOINT,
        checkpoint_index=1,
        observed_at="2026-09-06T00:01:30Z",
    )

    def issue(index: int):
        try:
            return ledger.issue_write_lease(
                request_id=f"race-{index}",
                lease_id=f"race-{index}",
                producer_event_sha256=H("same-producer"),
                artifact_variant="CHECKPOINT",
                checkpoint_index=1,
                training_step=1,
                progress_ppm=1,
                issued_at=ISSUED_AT,
                expires_at=EXPIRES_AT,
            )
        except ValueError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(issue, (1, 2)))
    assert sum(isinstance(item, Task084FixtureModelArtifactWriteLeaseV1) for item in results) == 1
    assert sum(isinstance(item, str) for item in results) == 1


def test_producer_prerequisite_and_temporal_currentness_fail_closed() -> None:
    plan = make_plan()
    ledger = open_fixture_custody(plan)
    activate(ledger)
    with pytest.raises(ValueError, match="producer event prerequisite"):
        ledger.issue_write_lease(
            request_id="missing-producer",
            lease_id="missing-producer",
            producer_event_sha256=H("missing-producer"),
            artifact_variant="CHECKPOINT",
            checkpoint_index=1,
            training_step=1,
            progress_ppm=1,
            issued_at=ISSUED_AT,
            expires_at=EXPIRES_AT,
        )
    register_producer(
        ledger,
        plan,
        producer_sha256=H("producer-checkpoint-1"),
        variant=ArtifactVariant.CHECKPOINT,
        checkpoint_index=1,
        observed_at="2026-09-06T00:01:30Z",
    )
    lease = ledger.issue_write_lease(
        request_id="temporal-issue",
        lease_id="temporal-lease",
        producer_event_sha256=H("producer-checkpoint-1"),
        artifact_variant="CHECKPOINT",
        checkpoint_index=1,
        training_step=1,
        progress_ppm=1,
        issued_at=ISSUED_AT,
        expires_at=EXPIRES_AT,
    )
    with pytest.raises(ValueError, match="before issuance"):
        ledger.begin_publish(
            lease,
            request_id="temporal-open-too-early",
            observed_at="2026-09-06T00:01:45Z",
        )
    ledger.begin_publish(
        lease, request_id="temporal-open", observed_at=OPEN_AT
    )
    unknown = complete_artifact(
        ledger, plan, lease, label="checkpoint-1", sealed_at=EXPIRES_AT
    )
    assert isinstance(unknown, Task084FixtureCustodyReadbackV1)
    assert unknown.to_dict()["phase"] == "COMPLETION_UNKNOWN"
    assert ledger.phase is CustodyPhase.COMPLETION_UNKNOWN

    expiry_ledger = open_fixture_custody(plan)
    activate(expiry_ledger)
    register_producer(
        expiry_ledger,
        plan,
        producer_sha256=H("producer-expired-open"),
        variant=ArtifactVariant.CHECKPOINT,
        checkpoint_index=1,
        observed_at="2026-09-06T00:01:30Z",
    )
    expiring_lease = expiry_ledger.issue_write_lease(
        request_id="issue-expired-open",
        lease_id="lease-expired-open",
        producer_event_sha256=H("producer-expired-open"),
        artifact_variant="CHECKPOINT",
        checkpoint_index=1,
        training_step=1,
        progress_ppm=1,
        issued_at=ISSUED_AT,
        expires_at="2026-09-06T00:02:30Z",
    )
    expired = expiry_ledger.begin_publish(
        expiring_lease,
        request_id="begin-expired-open",
        observed_at="2026-09-06T00:02:30Z",
    )
    assert expired.to_dict()["active_lease_state"] is None
    duplicate_expired = expiry_ledger.begin_publish(
        expiring_lease,
        request_id="begin-expired-open",
        observed_at="2026-09-06T00:02:30Z",
    )
    assert duplicate_expired.to_dict()["phase"] == "DESTINATION_ACTIVE"


def test_inventory_destination_manifest_identity_and_crypto_faults() -> None:
    plan = make_plan()
    expected = artifact_expected_entries(
        label="identity", variant=ArtifactVariant.CHECKPOINT, checkpoint_index=1
    )
    entries = [file_observation(item, label="identity") for item in expected]
    bad_ancestor = copy.deepcopy(entries)
    bad_ancestor[0]["ancestor_identity_sha256"] = H("foreign-ancestor")
    with pytest.raises(ValueError, match="pinned destination target"):
        compile_fixture_inventory(
            plan,
            inventory_id="inventory-bad-ancestor",
            producer_event_sha256=H("producer-identity"),
            artifact_variant="CHECKPOINT",
            checkpoint_index=1,
            **inventory_identity_fields("identity"),
            entries=bad_ancestor,
            manifest_relative_file=checkpoint_manifest_relative_file("identity", 1),
            manifest_sha256=H("manifest-identity"),
            manifest_authentication_evidence_sha256=H("manifest-auth-identity"),
            manifest_confidentiality="ENCRYPTED_AUTHENTICATED",
        )
    bad_manifest = inventory_identity_fields("identity")
    bad_manifest["manifest_ancestor_identity_sha256"] = H("foreign-manifest-ancestor")
    with pytest.raises(ValueError, match="manifest ancestor"):
        compile_fixture_inventory(
            plan,
            inventory_id="inventory-bad-manifest",
            producer_event_sha256=H("producer-identity"),
            artifact_variant="CHECKPOINT",
            checkpoint_index=1,
            **bad_manifest,
            entries=entries,
            manifest_relative_file=checkpoint_manifest_relative_file("identity", 1),
            manifest_sha256=H("manifest-identity"),
            manifest_authentication_evidence_sha256=H("manifest-auth-identity"),
            manifest_confidentiality="ENCRYPTED_AUTHENTICATED",
        )
    with pytest.raises(ValueError, match="closed v1 allowlist"):
        make_plan(aead_suite="NONE")


def test_manifest_inventory_cannot_swap_the_activated_destination() -> None:
    plan = make_plan()
    ledger = open_fixture_custody(plan)
    activate(ledger)
    lease = issue_and_begin(
        ledger,
        plan,
        variant=ArtifactVariant.CHECKPOINT,
        label="checkpoint-1",
        checkpoint_index=1,
        training_step=1,
        progress_ppm=1,
    )
    foreign = dict(DESTINATION_IDENTITIES)
    foreign["destination_target_identity_sha256"] = H("foreign-target")
    observations = []
    scoped = artifact_expected_entries(
        label="checkpoint-1",
        variant=ArtifactVariant.CHECKPOINT,
        checkpoint_index=1,
    )
    for item in scoped:
        handle = ledger.open_entry(lease, entry_id=item["entry_id"])
        observation = file_observation(item, label="swap")
        observation["ancestor_identity_sha256"] = foreign[
            "destination_target_identity_sha256"
        ]
        ledger.complete_entry(lease, handle, observation)
        observations.append(observation)
    manifest = inventory_identity_fields("swap")
    manifest.update(foreign)
    manifest["manifest_ancestor_identity_sha256"] = foreign[
        "destination_target_identity_sha256"
    ]
    swapped = compile_fixture_inventory(
        plan,
        inventory_id="inventory-swap",
        producer_event_sha256=H("producer-checkpoint-1"),
        artifact_variant="CHECKPOINT",
        checkpoint_index=1,
        **manifest,
        entries=observations,
        manifest_relative_file=checkpoint_manifest_relative_file("checkpoint-1", 1),
        manifest_sha256=H("manifest-swap"),
        manifest_authentication_evidence_sha256=H("manifest-auth-swap"),
        manifest_confidentiality="ENCRYPTED_AUTHENTICATED",
    )
    with pytest.raises(ValueError, match="destination identity"):
        ledger.verify_manifest_last(lease, swapped)


def test_producer_event_rechecks_current_run_and_job_heads() -> None:
    plan = make_plan()
    ledger = open_fixture_custody(plan)
    activate(ledger)
    with pytest.raises(ValueError, match="current run/Job"):
        ledger.register_fixture_producer_event(
            producer_event_sha256=H("wrong-current-producer"),
            artifact_variant="CHECKPOINT",
            training_run_head_sha256=plan.to_dict()["training_run_head_sha256"],
            task043_job_readback_sha256=plan.to_dict()["task043_job_readback_sha256"],
            task043_job_head_sha256=H("wrong-job-head"),
            checkpoint_index=1,
            task046_checkpoint_binding_sha256=TASK046_CHECKPOINT_BINDING_SHA256,
            observed_at="2026-09-06T00:01:30Z",
        )


def test_terminal_receipt_time_and_run_checkpoint_lineage_are_current() -> None:
    plan = make_plan()
    ledger = open_fixture_custody(plan)
    activate(ledger)
    checkpoint(ledger, plan)
    future = terminal_receipt(plan)
    future["terminal_at"] = "2026-09-06T00:05:30Z"
    # Rehash with TASK-046's canonical helper; TASK-084 must then reject future evidence.
    future = add_training_digest(
        {key: value for key, value in future.items() if key != "receipt_sha256"},
        "receipt_sha256",
    )
    register_producer(
        ledger,
        plan,
        producer_sha256=H("producer-future-terminal"),
        variant=ArtifactVariant.TERMINAL,
        terminal_value=future,
        observed_at="2026-09-06T00:05:30Z",
    )
    with pytest.raises(ValueError, match="future"):
        ledger.issue_write_lease(
            request_id="future-terminal",
            lease_id="future-terminal",
            producer_event_sha256=H("producer-future-terminal"),
            artifact_variant="TERMINAL",
            task046_terminal_receipt=future,
            issued_at="2026-09-06T00:05:00Z",
            expires_at=EXPIRES_AT,
        )


def test_receipt_aware_replay_rebuilds_sealed_and_failed_closed_state() -> None:
    plan, ledger, checkpoint_receipt, terminal = sealed_ledger()
    current_terminal_inventory = fixture_inventory(
        plan, label="terminal-1", variant=ArtifactVariant.TERMINAL
    )
    rebuilt = replay_fixture_custody(
        plan,
        ledger.event_chain(),
        [checkpoint_receipt],
        terminal_receipt=terminal,
        current_terminal_inventory=current_terminal_inventory,
        read_back_at="2026-09-06T00:08:00Z",
    )
    assert rebuilt.to_dict()["phase"] == "TERMINAL_SEALED"
    assert rebuilt.to_dict()["current_inventory_sha256"] == terminal.to_dict()[
        "inventory_sha256"
    ]
    with pytest.raises(ValueError, match="predates durable custody evidence"):
        replay_fixture_custody(
            plan,
            ledger.event_chain(),
            [checkpoint_receipt],
            terminal_receipt=terminal,
            read_back_at="2026-09-06T00:06:30Z",
        )
    in_flight = open_fixture_custody(plan)
    activate(in_flight)
    issue_and_begin(
        in_flight,
        plan,
        variant=ArtifactVariant.CHECKPOINT,
        label="checkpoint-1",
        checkpoint_index=1,
        training_step=1,
        progress_ppm=1,
    )
    with pytest.raises(ValueError, match="durable terminal resolution"):
        replay_fixture_custody(
            plan,
            in_flight.event_chain(),
            [],
            read_back_at="2026-09-06T00:04:00Z",
        )
    failed_ledger = open_fixture_custody(plan)
    activate(failed_ledger)
    lease = issue_and_begin(
        failed_ledger,
        plan,
        variant=ArtifactVariant.CHECKPOINT,
        label="checkpoint-1",
        checkpoint_index=1,
        training_step=1,
        progress_ppm=1,
    )
    ack = failed_ledger.issue_durable_negative_acknowledgement(
        lease,
        acknowledgement_id="negative-ack:replay",
        observed_at="2026-09-06T00:03:30Z",
    )
    failed_ledger.fail_closed_after_burn(
        lease,
        ack,
        request_id="failed-replay",
        observed_at=SEALED_AT,
    )
    failed = replay_fixture_custody(
        plan,
        failed_ledger.event_chain(),
        [],
        negative_acknowledgements=[ack],
        read_back_at="2026-09-06T00:05:00Z",
    )
    assert failed.to_dict()["phase"] == "FAILED_CLOSED"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda raw: b"\xef\xbb\xbf" + raw,
        lambda raw: raw + b" trailing",
        lambda raw: raw.replace(b'"schema_version":1', b'"schema_version":1,"schema_version":1'),
        lambda raw: raw.replace(b'"resource_effect_count":0', b'"resource_effect_count":NaN'),
        lambda raw: b"{" + b'"x":' * 22 + b"0" + b"}" * 22,
        lambda raw: b" " + raw,
    ],
)
def test_strict_security_json_rejects_ambiguous_inputs(mutation) -> None:
    raw = make_plan().canonical_bytes()
    with pytest.raises(ValueError):
        parse_security_json(mutation(raw), expected_type="Task084OutputArtifactDestinationPlanV1")


def test_schema_is_valid_mirrored_closed_and_accepts_all_public_records() -> None:
    assert PUBLIC_SCHEMA.read_bytes() == PACKAGED_SCHEMA.read_bytes()
    validator = schema_validator()
    plan, ledger, checkpoint_receipt, terminal = sealed_ledger()
    admission = compile_production_custody_admission(plan, evaluated_at=ACTIVE_AT)
    load = compile_model_load_admission(
        plan,
        purpose="TRAINING_RESUME",
        bindings={
            "checkpoint_custody_receipt_sha256": checkpoint_receipt.to_dict()["receipt_sha256"],
            "job_head_sha256": H("job-head"),
            "recovery_readback_sha256": H("recovery"),
            "task083_reservation_receipt_sha256": H("reservation"),
            "h3_v2_authorization_sha256": H("h3"),
            "resume_compound_operation_sha256": H("compound"),
        },
        evaluated_at=ACTIVE_AT,
    )
    inventory = fixture_inventory(
        plan,
        label="schema-inventory",
        variant=ArtifactVariant.CHECKPOINT,
        checkpoint_index=1,
    )
    failed_ledger = open_fixture_custody(plan)
    activate(failed_ledger)
    failed_lease = issue_and_begin(
        failed_ledger,
        plan,
        variant=ArtifactVariant.CHECKPOINT,
        label="checkpoint-1",
        checkpoint_index=1,
        training_step=1,
        progress_ppm=1,
    )
    negative_ack = failed_ledger.issue_durable_negative_acknowledgement(
        failed_lease,
        acknowledgement_id="negative-ack:schema",
        observed_at="2026-09-06T00:03:30Z",
    )
    resume_bindings = {
        "checkpoint_custody_receipt_sha256": checkpoint_receipt.to_dict()["receipt_sha256"],
        "job_head_sha256": H("schema-job-head"),
        "recovery_readback_sha256": H("schema-recovery"),
        "task083_reservation_receipt_sha256": H("schema-reservation"),
        "h3_v2_authorization_sha256": H("schema-h3"),
        "resume_compound_operation_sha256": H("schema-compound"),
    }
    ledger.register_fixture_current_load_bindings(
        purpose="TRAINING_RESUME",
        bindings=resume_bindings,
        observed_at="2026-09-06T00:08:30Z",
    )
    load_lease = ledger.issue_fixture_load_lease(
        request_id="schema-load",
        lease_id="schema-load",
        purpose="TRAINING_RESUME",
        bindings=resume_bindings,
        issued_at="2026-09-06T00:09:00Z",
        expires_at=EXPIRES_AT,
    )
    assert isinstance(load_lease, Task084FixtureModelLoadLeaseV1)
    load_readback = ledger.fixture_load_readback(
        load_lease, read_back_at="2026-09-06T00:09:00Z"
    )
    production_checkpoint_body = checkpoint_receipt.to_dict()
    production_checkpoint_body.update(
        {
            "record_type": "Task084ModelCheckpointCustodyReceiptV1",
            "fixture_only": False,
            "native_backend_invoked": True,
            "artifact_body_persisted": True,
            "resource_effect_count": 1,
        }
    )
    rehash(
        production_checkpoint_body,
        "receipt_sha256",
        task084._PRODUCTION_CHECKPOINT_RECEIPT_DOMAIN,
    )
    production_checkpoint = Task084ModelCheckpointCustodyReceiptV1.from_dict(
        production_checkpoint_body
    )
    production_terminal_body = terminal.to_dict()
    production_terminal_body.update(
        {
            "record_type": "Task084ModelArtifactCustodyReceiptV1",
            "fixture_only": False,
            "native_backend_invoked": True,
            "artifact_body_persisted": True,
            "resource_effect_count": 1,
        }
    )
    rehash(
        production_terminal_body,
        "receipt_sha256",
        task084._PRODUCTION_TERMINAL_RECEIPT_DOMAIN,
    )
    production_terminal = Task084ModelArtifactCustodyReceiptV1.from_dict(
        production_terminal_body
    )
    current_terminal_inventory = fixture_inventory(
        plan, label="terminal-1", variant=ArtifactVariant.TERMINAL
    )
    production_readback_body = ledger.readback(
        read_back_at="2026-09-06T00:09:00Z",
        current_terminal_inventory=current_terminal_inventory,
    ).to_dict()
    production_readback_body.update(
        {
            "record_type": "Task084CustodyReadbackV1",
            "terminal_receipt_sha256": production_terminal.to_dict()["receipt_sha256"],
            "fixture_only": False,
            "native_backend_observed": True,
            "resource_effect_count": 1,
        }
    )
    rehash(
        production_readback_body,
        "readback_sha256",
        task084._PRODUCTION_READBACK_DOMAIN,
    )
    production_readback = Task084CustodyReadbackV1.from_dict(
        production_readback_body
    )
    for record in (
        plan,
        inventory,
        *ledger.event_chain(),
        checkpoint_receipt,
        terminal,
        production_checkpoint,
        production_terminal,
        ledger.readback(
            read_back_at="2026-09-06T00:08:00Z",
            current_terminal_inventory=current_terminal_inventory,
        ),
        production_readback,
        admission,
        load,
        load_readback,
        negative_ack,
    ):
        errors = list(validator.iter_errors(record.to_dict()))
        assert not errors, [error.message for error in errors]
        changed = record.to_dict()
        changed["unknown"] = True
        assert list(validator.iter_errors(changed))


def test_event_phase_relation_is_closed_identically_by_runtime_and_schema() -> None:
    plan = make_plan()
    ledger = open_fixture_custody(plan)
    activated = activate(ledger).to_dict()
    activated["phase"] = "TERMINAL_SEALED"
    rehash(activated, "event_sha256", task084._EVENT_DOMAIN)
    with pytest.raises(ValueError, match="event_kind/phase mismatch"):
        Task084FixtureCustodyEventV1.from_dict(activated)
    assert list(schema_validator().iter_errors(activated))


@pytest.mark.parametrize(
    "field",
    [
        "plan_id",
        "project_id",
        "dataset_id",
        "job_id",
        "training_mode",
        "engine_id",
        "base_model_id",
        "base_model_revision",
        "runtime_revision",
        "code_revision",
        "destination_coordinate",
    ],
)
def test_runtime_schema_reject_all_private_copied_logical_ids(field: str) -> None:
    raw = make_plan().to_dict()
    raw[field] = "C:/private/model"
    rehash(raw, "plan_sha256", task084._PLAN_DOMAIN)
    with pytest.raises(ValueError, match="logical|identifier|body-free"):
        task084.Task084OutputArtifactDestinationPlanV1.from_dict(raw)
    assert list(schema_validator().iter_errors(raw))


@pytest.mark.parametrize(
    "value",
    [
        "2026-13-01T00:00:00Z",
        "2026-02-30T00:00:00Z",
        "2026-02-29T00:00:00Z",
        "1900-02-29T00:00:00Z",
        "0000-01-01T00:00:00Z",
        "2026-01-01T24:00:00Z",
        "2026-01-01T00:60:00Z",
        "2026-01-01T00:00:60Z",
        "2026-01-01T00:00:00.1234567Z",
        "2026-01-01T00:00:00Z\n",
    ],
)
def test_runtime_schema_timestamp_contract_matches_without_format_checker(value: str) -> None:
    with pytest.raises(ValueError, match="RFC3339"):
        make_plan(compiled_at=value)
    schema = json.loads(PUBLIC_SCHEMA.read_text(encoding="utf-8"))
    pattern = schema["$defs"]["Timestamp"]["pattern"]
    assert task084.re.search(pattern, value) is None


@pytest.mark.parametrize(
    ("issued", "expires"),
    [
        ("2024-02-29T00:00:00Z", "2024-02-29T00:00:01Z"),
        ("2000-02-29T23:59:58.123456Z", "2000-02-29T23:59:59.123456Z"),
        ("9999-12-31T23:59:58Z", "9999-12-31T23:59:59Z"),
    ],
)
def test_runtime_schema_timestamp_valid_boundaries(issued: str, expires: str) -> None:
    assert task084._timestamp(issued, "issued") == issued
    assert task084._timestamp(expires, "expires") == expires
    pattern = json.loads(PUBLIC_SCHEMA.read_text(encoding="utf-8"))["$defs"]["Timestamp"]["pattern"]
    assert task084.re.search(pattern, issued)
    assert task084.re.search(pattern, expires)


def test_source_has_no_backend_import_or_effectful_surface() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "os" not in imported
    assert "subprocess" not in imported
    assert "ctypes" not in imported
    assert "socket" not in imported
    assert "secure_authority_io" not in imported
    assert not any("task082" in name or "task083" in name for name in imported)
    source = SOURCE.read_text(encoding="utf-8")
    for forbidden in ("open(", "write_bytes(", "write_text(", "unlink(", "subprocess."):
        assert forbidden not in source


def test_fixture_receipt_is_not_a_production_receipt_or_capability() -> None:
    _, _, _, terminal = sealed_ledger()
    with pytest.raises(ValueError, match="expected"):
        Task084ModelArtifactCustodyReceiptV1.from_dict(terminal.to_dict())
    assert not hasattr(terminal, "open")
    assert not hasattr(terminal, "load")
    assert not hasattr(terminal, "write")


def test_parse_only_production_checkpoint_requires_effect_and_body_attestation() -> None:
    plan = make_plan()
    ledger = open_fixture_custody(plan)
    activate(ledger)
    fixture = checkpoint(ledger, plan).to_dict()
    production = {
        **fixture,
        "record_type": "Task084ModelCheckpointCustodyReceiptV1",
        "fixture_only": False,
        "native_backend_invoked": True,
        "artifact_body_persisted": True,
        "resource_effect_count": 1,
    }
    rehash(
        production,
        "receipt_sha256",
        task084._PRODUCTION_CHECKPOINT_RECEIPT_DOMAIN,
    )
    parsed = Task084ModelCheckpointCustodyReceiptV1.from_dict(production)
    assert parsed.to_dict()["native_backend_invoked"] is True
    forged = copy.deepcopy(production)
    forged["resource_effect_count"] = 0
    rehash(
        forged,
        "receipt_sha256",
        task084._PRODUCTION_CHECKPOINT_RECEIPT_DOMAIN,
    )
    with pytest.raises(ValueError, match="observed backend effect"):
        Task084ModelCheckpointCustodyReceiptV1.from_dict(forged)


def test_no_private_or_effectful_terms_exported_from_fixture_surfaces() -> None:
    plan, ledger, checkpoint_receipt, terminal = sealed_ledger()
    exported = canonical_json_bytes(
        {
            "plan": plan.to_dict(),
            "events": [event.to_dict() for event in ledger.event_chain()],
            "checkpoint": checkpoint_receipt.to_dict(),
            "terminal": terminal.to_dict(),
            "readback": ledger.readback(read_back_at="2026-09-06T00:08:00Z").to_dict(),
        }
    ).decode("utf-8")
    for forbidden in (
        "C:\\",
        "/home/",
        "private_key",
        "raw_model",
        "model_bytes",
        "os_handle",
        "access_token",
    ):
        assert forbidden not in exported
    assert '"resource_effect_count":0' in exported
    assert '"authority_created":false' in exported
