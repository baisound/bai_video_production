from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.voice_training_run import (
    ArtifactKind,
    DecisionState,
    EngineAdmissionBinding,
    EvaluationInputSnapshot,
    ModelArtifactBinding,
    ModelCandidateRevision,
    TrainingRunIntent,
    TrainingRunRevision,
    add_record_digest,
    assert_no_effect_surface,
    classify_unknown_reconciliation,
    evaluate_candidate_evaluation_admission,
    evaluate_dispatch_admission,
    evaluate_owner_approval_current_use,
    evaluate_preflight,
    evaluate_resume_admission,
    public_projection,
    training_dispatch_projection,
    validate_record,
    validate_state_transition,
)


H = "sha256:" + "a" * 64
H2 = "sha256:" + "b" * 64
H3 = "sha256:" + "c" * 64
H4 = "sha256:" + "d" * 64
H5 = "sha256:" + "e" * 64
NOW = "2026-08-17T00:00:00Z"
LATER = "2026-08-17T01:00:00Z"
EXPIRES = "2026-08-18T00:00:00Z"


def digest(value: dict, field: str = "binding_sha256") -> dict:
    return add_record_digest(value, field)


def engine(*, license_state: str = "PASS", mode: str = "ADAPTER_OR_LORA") -> dict:
    return digest({
        "record_type": "EngineAdmissionBinding", "contract_state": "BOUND_VERIFIED",
        "engine_id": "engine:qwen3-tts", "engine_repository_ref": "repo:qwen3-tts",
        "engine_commit_sha256": H, "package_lock_sha256": H2,
        "training_mode": mode, "capability_state": "ADMITTED",
        "license_state": license_state, "base_model_id": "model:qwen3-tts-0.6b-base",
        "base_model_revision": "revision:5d8399", "base_model_sha256": H3,
        "runtime_revision": "runtime:torch-2.11-cu130", "runtime_sha256": H4,
        "code_revision": "code:qwen-tts-0.1.1", "code_sha256": H5,
        "weight_revision": "weights:5d8399", "weight_sha256": H3,
        "tokenizer_sha256": H, "codec_sha256": H2, "vocoder_sha256": H3,
        "config_sha256": H4, "target_probe_profile_ref": "probe:4070-super:lora:1",
        "target_probe_profile_sha256": H5, "evidence_ref": "evidence:engine:1",
        "evidence_sha256": H,
    })


def destination() -> dict:
    return digest({
        "record_type": "OutputArtifactDestinationBinding", "contract_state": "BOUND_VERIFIED",
        "canonical_owner_ref": "storage:voice-models", "canonical_owner_sha256": H,
        "storage_policy_ref": "policy:storage:1", "storage_policy_sha256": H2,
        "logical_uri": "artifact-destination:voice-models", "encryption_policy_sha256": H3,
        "recovery_policy_sha256": H4, "retention_policy_sha256": H5,
        "disk_quota_admission_ref": "admission:disk:1", "disk_quota_admission_sha256": H,
        "allowed_artifact_classes": ["CHECKPOINT", "EVALUATION_OUTPUT", "LOG", "MODEL_OUTPUT"],
        "public_exposure": False,
    })


def feasibility(*, mode: str = "ADAPTER_OR_LORA", admission: str = "ADMITTED") -> dict:
    return digest({
        "record_type": "TargetResourceFeasibilityBinding", "contract_state": "BOUND_VERIFIED",
        "mode": mode, "recipe_revision_ref": "recipe:qwen:lora:1", "recipe_revision_sha256": H,
        "probe_profile_ref": "probe:4070-super:lora:1", "probe_profile_sha256": H2,
        "target_gpu_ref": "gpu:rtx4070-super", "target_vram_bytes": 12878086144,
        "peak_vram_bytes": 9000000000, "peak_ram_bytes": 16000000000,
        "optimizer_overhead_bytes": 1000000000, "checkpoint_overhead_bytes": 2000000000,
        "representative_batch": 1, "representative_sequence_units": 1024,
        "thermal_floor_state": "PASS", "disk_floor_state": "PASS", "oom_recovery_state": "PASS",
        "expected_duration_seconds": 3600, "headroom_policy_ref": "policy:headroom:1",
        "headroom_policy_sha256": H3, "admission_state": admission,
        "evidence_ref": "evidence:feasibility:1", "evidence_sha256": H4,
    })


def rights(*, state: str = "PASS") -> dict:
    return digest({
        "record_type": "CurrentUseRightsBinding", "contract_state": "BOUND_VERIFIED",
        "evaluation_ref": "rights-evaluation:1", "evaluation_sha256": H,
        "consent_state": state, "training_data_rights_state": state,
        "reference_audio_rights_state": state, "output_rights_state": state,
        "license_state": state, "evaluated_at": NOW,
    })


def evaluation_snapshot() -> dict:
    item = {
        "source_kind": "PVS3B_DATASET_MEMBER", "item_ref": "eval-item:1",
        "item_sha256": H, "dataset_member_entry_sha256": H2,
        "asset_revision_ref": "asset:eval:1", "asset_revision_sha256": H3,
        "asset_checksum_sha256": H4, "sample_start": 0, "sample_end": 48000,
        "consent_evaluation_sha256": H, "evaluation_rights_sha256": H2,
        "reference_rights_sha256": H3, "output_rights_sha256": H4,
        "approved_labels_sha256": H5, "provenance_equivalence_sha256": H,
    }
    return digest({
        "record_type": "EvaluationInputSnapshot", "snapshot_id": "evaluation-input:1",
        "revision": 1, "parent_snapshot_sha256": None, "project_id": "project:owner",
        "selection_policy_ref": "policy:evaluation-selection:1", "selection_policy_sha256": H,
        "selected_items": [item], "private_equivalence_index_sha256": H2,
        "created_at": NOW, "audio_body_persisted": False, "text_body_persisted": False,
    }, "snapshot_sha256")


def contamination(*, decision: str = "PASS", semantic_state: str = "BOUND_VERIFIED") -> dict:
    semantic_ref = "policy:near-duplicate:1" if semantic_state == "BOUND_VERIFIED" else None
    semantic_sha = H3 if semantic_state == "BOUND_VERIFIED" else None
    return digest({
        "record_type": "ContaminationProofBinding",
        "training_input_snapshot_ref": "training-input:1", "training_input_snapshot_sha256": H,
        "evaluation_input_snapshot_ref": "evaluation-input:1",
        "evaluation_input_snapshot_sha256": evaluation_snapshot()["snapshot_sha256"],
        "identity_non_overlap": True, "asset_mapping_non_overlap": True,
        "checksum_non_overlap": True, "sample_range_non_overlap": True,
        "source_lineage_non_overlap": True, "semantic_policy_state": semantic_state,
        "semantic_policy_ref": semantic_ref, "semantic_policy_sha256": semantic_sha,
        "semantic_decision": "PASS" if semantic_state == "BOUND_VERIFIED" else "UNKNOWN",
        "decision": decision, "reason_codes": [] if decision == "PASS" else ["SEMANTIC_POLICY_UNKNOWN"],
    }, "proof_sha256")


def intent(*, license_state: str = "PASS", rights_state: str = "PASS", mode: str = "ADAPTER_OR_LORA") -> dict:
    proof = contamination()
    current_rights = rights(state=rights_state)
    return digest({
        "record_type": "TrainingRunIntent", "run_intent_id": "training-run-intent:1",
        "revision": 1, "parent_intent_sha256": None, "project_id": "project:owner",
        "training_mode": mode, "training_input_snapshot_ref": "training-input:1",
        "training_input_snapshot_sha256": H, "evaluation_input_snapshot_ref": "evaluation-input:1",
        "evaluation_input_snapshot_sha256": evaluation_snapshot()["snapshot_sha256"],
        "contamination_proof_binding": proof,
        "engine_admission_binding": engine(license_state=license_state, mode=mode),
        "output_artifact_destination_binding": destination(),
        "target_resource_feasibility_binding": feasibility(mode=mode),
        "current_use_rights_binding": current_rights,
        "current_consent_rights_license_sha256": current_rights["binding_sha256"],
        "config_sha256": H5, "created_at": NOW, "audio_body_persisted": False,
        "text_body_persisted": False, "execution_authorized": False,
    }, "intent_sha256")


def unresolved(record_type: str, digest_field: str, fields: list[str]) -> dict:
    return digest({"record_type": record_type, "contract_state": "CANONICAL_REF_NOT_PROVIDED", **{field: None for field in fields}}, digest_field)


JOB_FIELDS = ["job_id", "operation_id", "idempotency_key", "job_kind", "job_revision", "job_revision_sha256", "job_state", "canonical_job_evidence_ref", "canonical_job_evidence_sha256", "identity_shared_with_dataset_adoption_job"]
RESERVATION_FIELDS = ["reservation_id", "receipt_ref", "receipt_sha256", "gpu_ref", "cpu_units", "ram_bytes", "vram_bytes", "disk_bytes", "thermal_state", "power_state", "admission_state", "issued_at", "expires_at"]
AUTH_FIELDS = ["authorization_id", "authorization_revision", "authorization_sha256", "authority_kind", "project_id", "run_intent_sha256", "run_revision_sha256", "training_input_snapshot_sha256", "engine_admission_sha256", "config_sha256", "current_consent_rights_license_sha256", "scope", "issued_at", "expires_at", "one_shot", "replay_policy", "evidence_ref", "evidence_sha256"]
PROCESS_FIELDS = ["process_observation_id", "job_id", "process_identity_sha256", "observation_state", "gpu_process_present", "observed_at", "evidence_ref", "evidence_sha256"]
CHECKPOINT_FIELDS = ["checkpoint_id", "checkpoint_revision", "canonical_owner_ref", "canonical_owner_sha256", "persistence_receipt_ref", "persistence_receipt_sha256", "artifact_checksum_sha256", "training_input_snapshot_sha256", "base_model_sha256", "runtime_sha256", "code_sha256", "config_sha256", "license_evaluation_sha256", "consent_evaluation_sha256", "training_step", "optimizer_state_sha256", "resume_compatibility_sha256", "resume_decision", "logical_uri"]


def job() -> dict:
    return digest({
        "record_type": "TrainingDurableJobBinding", "contract_state": "BOUND_VERIFIED",
        "job_id": "job:training:1", "operation_id": "operation:training:1",
        "idempotency_key": "idempotency:training:1", "job_kind": "VOICE_MODEL_TRAINING",
        "job_revision": 1, "job_revision_sha256": H, "job_state": "QUEUED",
        "canonical_job_evidence_ref": "evidence:job:1", "canonical_job_evidence_sha256": H2,
        "identity_shared_with_dataset_adoption_job": False,
    })


def reservation(*, expires: str = EXPIRES) -> dict:
    return digest({
        "record_type": "ExecutionResourceReservationBinding", "contract_state": "BOUND_VERIFIED",
        "reservation_id": "reservation:1", "receipt_ref": "receipt:reservation:1",
        "receipt_sha256": H, "gpu_ref": "gpu:rtx4070-super", "cpu_units": 4,
        "ram_bytes": 16000000000, "vram_bytes": 10000000000, "disk_bytes": 50000000000,
        "thermal_state": "PASS", "power_state": "PASS", "admission_state": "ADMITTED",
        "issued_at": NOW, "expires_at": expires,
    })


def authorization(run_intent_sha: str, run_revision_sha: str, *, scope: str = "START") -> dict:
    return digest({
        "record_type": "TrainingExecutionAuthorizationBinding", "contract_state": "BOUND_VERIFIED",
        "authorization_id": "authorization:training:1", "authorization_revision": 1,
        "authorization_sha256": H, "authority_kind": "OWNER_HUMAN_GATE",
        "project_id": "project:owner", "run_intent_sha256": run_intent_sha,
        "run_revision_sha256": run_revision_sha, "training_input_snapshot_sha256": H,
        "engine_admission_sha256": engine()["binding_sha256"], "config_sha256": H5,
        "current_consent_rights_license_sha256": rights()["binding_sha256"],
        "scope": scope, "issued_at": NOW, "expires_at": EXPIRES, "one_shot": True,
        "replay_policy": "NO_REPLAY", "evidence_ref": "evidence:owner-gate:1",
        "evidence_sha256": H2,
    })


def process(*, present: bool = False) -> dict:
    return digest({
        "record_type": "GPUProcessObservationBinding", "contract_state": "BOUND_VERIFIED",
        "process_observation_id": "process-observation:1", "job_id": "job:training:1",
        "process_identity_sha256": H, "observation_state": "OBSERVED" if present else "NOT_FOUND",
        "gpu_process_present": present, "observed_at": NOW,
        "evidence_ref": "evidence:process:1", "evidence_sha256": H2,
    })


def checkpoint(*, resume: str = "ACCEPT") -> dict:
    return digest({
        "record_type": "CheckpointArtifactBinding", "contract_state": "BOUND_VERIFIED",
        "checkpoint_id": "checkpoint:1", "checkpoint_revision": 1,
        "canonical_owner_ref": "storage:checkpoints", "canonical_owner_sha256": H,
        "persistence_receipt_ref": "receipt:checkpoint:1", "persistence_receipt_sha256": H2,
        "artifact_checksum_sha256": H3, "training_input_snapshot_sha256": H,
        "base_model_sha256": H3, "runtime_sha256": H4, "code_sha256": H5,
        "config_sha256": H5, "license_evaluation_sha256": H,
        "consent_evaluation_sha256": H2, "training_step": 100,
        "optimizer_state_sha256": H3, "resume_compatibility_sha256": H4,
        "resume_decision": resume, "logical_uri": "checkpoint:run1:step100",
    })


def revision(*, state: str, number: int = 1, parent: str | None = None, auth: dict | None = None) -> dict:
    return digest({
        "record_type": "TrainingRunRevision", "run_revision_id": f"training-run-revision:{number}",
        "revision": number, "parent_revision_sha256": parent,
        "run_intent_sha256": intent()["intent_sha256"], "state": state,
        "durable_job_binding": job() if state in {"QUEUED", "RUNNING"} else unresolved("TrainingDurableJobBinding", "binding_sha256", JOB_FIELDS),
        "resource_reservation_binding": reservation() if state in {"QUEUED", "RUNNING"} else unresolved("ExecutionResourceReservationBinding", "binding_sha256", RESERVATION_FIELDS),
        "execution_authorization_binding": auth or unresolved("TrainingExecutionAuthorizationBinding", "binding_sha256", AUTH_FIELDS),
        "process_observation_binding": unresolved("GPUProcessObservationBinding", "binding_sha256", PROCESS_FIELDS),
        "checkpoint_artifact_binding": unresolved("CheckpointArtifactBinding", "binding_sha256", CHECKPOINT_FIELDS),
        "compute_terminal_receipt_sha256": H if state == "TRAINING_COMPLETED_ARTIFACT_UNBOUND" else None,
        "model_candidate_sha256": None, "evaluation_receipt_sha256": None,
        "owner_approval_binding_sha256": None, "reason_codes": [], "created_at": NOW,
        "execution_started": state in {"RUNNING"},
    }, "revision_sha256")


def artifact(*, kind: str = "FULL_MODEL", license_state: str = "PASS") -> dict:
    adapter = kind in {"PEFT_ADAPTER", "LORA_ADAPTER", "MERGED_MODEL"}
    merged = kind == "MERGED_MODEL"
    return digest({
        "record_type": "ModelArtifactBinding", "contract_state": "BOUND_VERIFIED",
        "artifact_id": "model-artifact:1", "artifact_kind": kind,
        "canonical_owner_ref": "registry:model-artifacts", "canonical_owner_sha256": H,
        "persistence_receipt_ref": "receipt:model-artifact:1", "persistence_receipt_sha256": H2,
        "artifact_checksum_sha256": H3, "artifact_manifest_sha256": H4,
        "artifact_index_sha256": H5, "component_checksums": [H, H2],
        "serialization_format": "safetensors", "base_model_id": "model:qwen3-tts-base",
        "base_model_revision": "revision:5d8399", "base_model_sha256": H3,
        "base_model_license_sha256": H4, "adapter_format": "lora" if adapter else None,
        "adapter_config_sha256": H5 if adapter else None,
        "merge_state": "MERGED_VERIFIED" if merged else ("UNMERGED" if adapter else "NOT_APPLICABLE"),
        "merge_provenance_receipt_ref": "receipt:merge:1" if merged else None,
        "merge_provenance_receipt_sha256": H if merged else None,
        "engine_sha256": H, "runtime_sha256": H2, "tokenizer_sha256": H3,
        "codec_sha256": H4, "vocoder_sha256": H5, "config_sha256": H,
        "load_compatibility_evidence_ref": "evidence:load:1",
        "load_compatibility_evidence_sha256": H2, "load_compatibility_state": "PASS",
        "license_inheritance_state": license_state, "logical_uri": "model-artifact:candidate1",
    })


def candidate(*, artifact_value: dict | None = None) -> dict:
    return digest({
        "record_type": "ModelCandidateRevision", "candidate_id": "model-candidate:1",
        "revision": 1, "parent_candidate_sha256": None, "run_intent_sha256": intent()["intent_sha256"],
        "compute_terminal_receipt_sha256": H, "model_artifact_binding": artifact_value or artifact(),
        "candidate_state": "REGISTERED", "current_consent_rights_license_sha256": rights()["binding_sha256"],
        "created_at": NOW, "model_use_authorized": False, "production_use_authorized": False,
    }, "candidate_sha256")


def evaluation(candidate_value: dict) -> dict:
    return digest({
        "record_type": "EvaluationReceipt", "evaluation_id": "evaluation:1",
        "candidate_sha256": candidate_value["candidate_sha256"],
        "model_artifact_binding_sha256": candidate_value["model_artifact_binding"]["binding_sha256"],
        "evaluation_input_snapshot_sha256": evaluation_snapshot()["snapshot_sha256"],
        "contamination_proof_sha256": contamination()["proof_sha256"],
        "similarity_decision": "PASS", "pronunciation_decision": "PASS",
        "style_emotion_whisper_decision": "PASS", "long_form_decision": "PASS",
        "artifact_integrity_decision": "PASS", "threshold_policy_state": "BOUND_VERIFIED",
        "threshold_policy_ref": "policy:model-evaluation:1", "threshold_policy_sha256": H,
        "held_out_decision": "PASS", "overall_decision": "PASS",
        "current_consent_rights_license_sha256": rights()["binding_sha256"],
        "evaluated_at": NOW, "audio_analysis_executed": False,
    }, "receipt_sha256")


def approval(candidate_value: dict, evaluation_value: dict) -> dict:
    return digest({
        "record_type": "OwnerModelApprovalDecisionBinding", "contract_state": "BOUND_VERIFIED",
        "decision_id": "owner-model-decision:1", "decision_revision": 1,
        "candidate_sha256": candidate_value["candidate_sha256"],
        "evaluation_receipt_sha256": evaluation_value["receipt_sha256"],
        "model_artifact_binding_sha256": candidate_value["model_artifact_binding"]["binding_sha256"],
        "artifact_composition_sha256": candidate_value["model_artifact_binding"]["artifact_manifest_sha256"],
        "current_consent_rights_license_sha256": rights()["binding_sha256"],
        "decision": "APPROVE", "decided_at": NOW, "reviewer_kind": "OWNER",
        "human_gate_evidence_ref": "evidence:owner-model-approval:1",
        "human_gate_evidence_sha256": H,
    })


def test_schema_mirror_and_all_canonical_payloads_validate() -> None:
    root = Path(__file__).resolve().parents[1]
    public = root / "schemas" / "voice-training-run.schema.json"
    mirror = root / "src" / "ai_video_production" / "schema_resources" / "voice-training-run.schema.json"
    assert public.read_bytes() == mirror.read_bytes()
    schema = json.loads(public.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    for payload in (engine(), destination(), feasibility(), rights(), evaluation_snapshot(), contamination(), intent(), revision(state="DRAFT"), artifact(), candidate()):
        Draft202012Validator(schema).validate(payload)


def test_preflight_pass_is_pure_and_legal_or_rights_unknown_blocks() -> None:
    report = evaluate_preflight(intent(), evaluated_at=NOW).to_dict()
    assert report["decision"] == "PASS"
    assert not report["dispatch_started"] and not report["training_started"]
    blocked = evaluate_preflight(intent(license_state="LEGAL_REVIEW_REQUIRED"), evaluated_at=NOW).to_dict()
    assert blocked["decision"] == "BLOCKED"
    assert "LICENSE_NOT_CURRENT_PASS" in blocked["reason_codes"]
    blocked_rights = evaluate_preflight(intent(rights_state="UNKNOWN"), evaluated_at=NOW).to_dict()
    assert "CURRENT_RIGHTS_CONSENT_LICENSE_NOT_PASS" in blocked_rights["reason_codes"]


def test_mode_admission_is_not_reused_between_full_and_lora() -> None:
    bad = intent()
    bad["target_resource_feasibility_binding"] = feasibility(mode="FULL_FINE_TUNE")
    bad = digest(bad, "intent_sha256")
    with pytest.raises(ValueError, match="mode cannot be reused"):
        TrainingRunIntent.from_dict(bad)


def test_evaluation_snapshot_rejects_same_asset_overlapping_range_and_bodies() -> None:
    bad = evaluation_snapshot()
    second = copy.deepcopy(bad["selected_items"][0])
    second["item_ref"] = "eval-item:2"
    second["item_sha256"] = H2
    second["sample_start"] = 24000
    second["sample_end"] = 72000
    bad["selected_items"].append(second)
    bad = digest(bad, "snapshot_sha256")
    with pytest.raises(ValueError, match="overlap"):
        EvaluationInputSnapshot.from_dict(bad)
    body = evaluation_snapshot()
    body["audio_body_persisted"] = True
    body = digest(body, "snapshot_sha256")
    with pytest.raises(ValueError, match="false"):
        EvaluationInputSnapshot.from_dict(body)


def test_unknown_near_duplicate_policy_cannot_be_contamination_pass() -> None:
    bad = contamination(decision="PASS", semantic_state="CANONICAL_REF_NOT_PROVIDED")
    with pytest.raises(ValueError, match="semantic proof"):
        validate_record(bad)


def test_output_destination_rejects_absolute_path_and_traversal() -> None:
    for uri in ("file:C:/models", "../models"):
        bad = destination()
        bad["logical_uri"] = uri
        bad = digest(bad)
        with pytest.raises(ValueError, match="invalid|logical identity"):
            validate_record(bad)


def test_dispatch_requires_job_fresh_reservation_and_owner_gate_without_effect() -> None:
    base = revision(state="READY_FOR_OWNER_HUMAN_GATE")
    queued_auth = authorization(intent()["intent_sha256"], base["revision_sha256"])
    queued = revision(state="QUEUED", number=2, parent=base["revision_sha256"], auth=queued_auth)
    report = evaluate_dispatch_admission(intent(), queued, now=LATER).to_dict()
    assert report["decision"] == "PASS"
    assert report["dispatch_started"] is False and report["gpu_process_started"] is False
    expired = copy.deepcopy(queued)
    expired["resource_reservation_binding"] = reservation(expires=NOW)
    expired = digest(expired, "revision_sha256")
    blocked = evaluate_dispatch_admission(intent(), expired, now=LATER).to_dict()
    assert "EXECUTION_RESERVATION_EXPIRED" in blocked["reason_codes"]


def test_dataset_adoption_or_project_maintenance_job_identity_is_rejected() -> None:
    for kind in ("VOICE_DATASET_ADOPTION", "PROJECT_MAINTENANCE"):
        bad = job()
        bad["job_kind"] = kind
        bad = digest(bad)
        with pytest.raises(ValueError, match="cannot reuse"):
            validate_record(bad)


def test_checkpoint_requires_canonical_receipt_and_exact_resume_compatibility() -> None:
    assert validate_record(checkpoint())["resume_decision"] == "ACCEPT"
    path_only = unresolved("CheckpointArtifactBinding", "binding_sha256", CHECKPOINT_FIELDS)
    path_only["logical_uri"] = "checkpoint:path-only"
    path_only = digest(path_only)
    with pytest.raises(ValueError, match="must not invent"):
        validate_record(path_only)


def test_resume_requires_exact_dataset_model_runtime_code_config_rights_and_owner_gate() -> None:
    resume_auth = authorization(intent()["intent_sha256"], H2, scope="RESUME")
    passed = evaluate_resume_admission(intent(), checkpoint(), resume_auth, rights(), now=LATER).to_dict()
    assert passed["decision"] == "PASS"
    assert passed["dispatch_started"] is False and passed["training_started"] is False
    stale = checkpoint()
    stale["config_sha256"] = H4
    stale = digest(stale)
    blocked = evaluate_resume_admission(intent(), stale, resume_auth, rights(), now=LATER).to_dict()
    assert "CHECKPOINT_CONFIG_SHA256_MISMATCH" in blocked["reason_codes"]


def test_unknown_reconciliation_never_auto_replays_or_duplicates_gpu_process() -> None:
    unknown_process = unresolved("GPUProcessObservationBinding", "binding_sha256", PROCESS_FIELDS)
    assert classify_unknown_reconciliation(job(), unknown_process, checkpoint()) is DecisionState.UNKNOWN
    assert classify_unknown_reconciliation(job(), process(present=True), checkpoint()) is DecisionState.BLOCKED
    assert classify_unknown_reconciliation(job(), process(present=False), checkpoint()) is DecisionState.PASS


def test_artifact_composition_cross_fields_reject_adapter_as_full_model() -> None:
    full = artifact()
    full["adapter_format"] = "lora"
    full["adapter_config_sha256"] = H5
    full = digest(full)
    with pytest.raises(ValueError, match="FULL_MODEL"):
        ModelArtifactBinding.from_dict(full)
    assert ModelArtifactBinding.from_dict(artifact(kind="LORA_ADAPTER")).to_dict()["merge_state"] == "UNMERGED"
    merged = artifact(kind="MERGED_MODEL")
    assert merged["merge_provenance_receipt_ref"] is not None


def test_unbound_artifact_cannot_register_candidate() -> None:
    unbound_fields = list(set(artifact().keys()) - {"record_type", "contract_state", "binding_sha256"})
    unbound = unresolved("ModelArtifactBinding", "binding_sha256", unbound_fields)
    bad = candidate(artifact_value=unbound)
    with pytest.raises(ValueError, match="requires BOUND_VERIFIED"):
        ModelCandidateRevision.from_dict(bad)


def test_license_inheritance_unknown_blocks_evaluation_and_approval() -> None:
    blocked_candidate = candidate(artifact_value=artifact(kind="LORA_ADAPTER", license_state="UNKNOWN"))
    assert evaluate_candidate_evaluation_admission(blocked_candidate) is DecisionState.BLOCKED


def test_owner_approval_is_exact_human_binding_not_production_effect() -> None:
    model_candidate = candidate()
    evaluation_receipt = evaluation(model_candidate)
    owner_decision = approval(model_candidate, evaluation_receipt)
    assert evaluate_owner_approval_current_use(
        model_candidate, evaluation_receipt, owner_decision,
        current_consent_rights_license_sha256=rights()["binding_sha256"],
    ) is DecisionState.PASS
    assert model_candidate["production_use_authorized"] is False
    revoked_hash = H5
    assert evaluate_owner_approval_current_use(
        model_candidate, evaluation_receipt, owner_decision,
        current_consent_rights_license_sha256=revoked_hash,
    ) is DecisionState.BLOCKED


def test_training_completion_does_not_skip_artifact_candidate_evaluation_gates() -> None:
    completed = revision(state="TRAINING_COMPLETED_ARTIFACT_UNBOUND")
    assert completed["model_candidate_sha256"] is None
    invalid = copy.deepcopy(completed)
    invalid["state"] = "EVALUATED_CANDIDATE"
    invalid = digest(invalid, "revision_sha256")
    with pytest.raises(ValueError, match="candidate lifecycle"):
        TrainingRunRevision.from_dict(invalid)


def test_state_transition_is_append_only_and_unknown_has_no_auto_retry() -> None:
    draft = revision(state="DRAFT")
    pending = revision(state="PREFLIGHT_PENDING", number=2, parent=draft["revision_sha256"])
    validate_state_transition(draft, pending)
    queued = revision(state="QUEUED", number=2, parent=draft["revision_sha256"], auth=authorization(intent()["intent_sha256"], draft["revision_sha256"]))
    with pytest.raises(ValueError, match="invalid training state"):
        validate_state_transition(draft, queued)


def test_public_projection_suppresses_items_paths_hashes_and_no_effect_surface() -> None:
    projected = public_projection(evaluation_snapshot())
    encoded = json.dumps(projected, sort_keys=True)
    assert "selected_items" not in encoded
    assert "sha256" not in encoded
    assert projected["projection"] == "PUBLIC_BODY_FREE"
    assert_no_effect_surface()


def test_training_projection_exposes_only_evaluation_snapshot_identity_not_items() -> None:
    projected = training_dispatch_projection(intent())
    encoded = json.dumps(projected, sort_keys=True)
    assert projected["evaluation_item_details_included"] is False
    assert "selected_items" not in encoded
    assert "asset_revision" not in encoded
    assert "sample_start" not in encoded
    assert projected["dispatch_started"] is False


def test_tamper_and_unknown_fields_fail_closed() -> None:
    tampered = intent()
    tampered["project_id"] = "project:other"
    with pytest.raises(ValueError, match="mismatch"):
        TrainingRunIntent.from_dict(tampered)
    extra = engine()
    extra["raw_audio_path"] = "private.wav"
    extra = digest(extra)
    with pytest.raises(ValueError, match="fields"):
        EngineAdmissionBinding.from_dict(extra)
