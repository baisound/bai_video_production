from __future__ import annotations

from dataclasses import replace
import json

import pytest

from ai_video_production.owner_narration import (
    NarrationGenerationMode,
    NarrationPlanningService,
    NarrationScript,
    VoiceProfile,
)
from ai_video_production.owner_narration_local_primary import (
    ContractState,
    LocalNarrationRouteMode,
    NarrationIntendedUsage,
    compile_local_primary_preflight,
    parse_local_primary_preflight,
)
from ai_video_production.owner_narration_local_render_admission import (
    AuthorityKind,
    DurableJobState,
    DurableNarrationJobBinding,
    ExecutionAuthorizationBinding,
    LocalPrimaryPreflightBinding,
    OutputStagingDestinationBinding,
    RenderAuthorizationScope,
    ResourceAdmissionBinding,
    ResourceGateDecision,
    compile_render_admission,
    render_operation_identity_sha256,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task014_zero_shot_callable_contract import (
    PLAN_RECEIPT_SCHEMA_ID,
    SUBJECT_RECEIPT_SCHEMA_ID,
    TRANSCRIPT_RECEIPT_SCHEMA_ID,
    CallableEnvelopeDecision,
    CanonicalNarrationPlanRevisionReceipt,
    PlanDerivationAuthorityKind,
    PlanDerivationDecision,
    ReferenceTranscriptAuthorityKind,
    ReferenceTranscriptDecision,
    SubjectBindingAuthorityKind,
    SubjectMatchDecision,
    ZeroShotReferenceSubjectBindingReceipt,
    ZeroShotReferenceTranscriptBindingReceipt,
    compile_zero_shot_callable_envelope,
    parse_canonical_narration_plan_revision_receipt,
    parse_zero_shot_callable_envelope,
    parse_zero_shot_reference_subject_binding_receipt,
    parse_zero_shot_reference_transcript_binding_receipt,
)
from ai_video_production.voice_profile_revision import (
    ArtifactAdmissionState,
    CapabilityProbeState,
    ConsentReference,
    ConsentState,
    LicenseReference,
    LocalVoiceCapabilityDescription,
    ModelLicenseClass,
    VoiceProfileRevision,
)


EVALUATED_AT = "2026-08-20T00:00:30Z"
ADMISSION_AT = "2026-08-20T00:01:00Z"
COMPILED_AT = "2026-08-20T00:02:00Z"
EXPIRES_AT = "2026-08-20T00:10:00Z"


def h(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def _ordered_chunk_manifest_sha256(plan: object) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            [
                {
                    "chunk_id": chunk.chunk_id,
                    "order": chunk.order,
                    "text_sha256": chunk.text_sha256,
                }
                for chunk in plan.chunks
            ]
        )
    )


def assembled(
    *,
    route: LocalNarrationRouteMode = LocalNarrationRouteMode.ZERO_SHOT_LOCAL,
    intended_usage: NarrationIntendedUsage = NarrationIntendedUsage.PREVIEW,
    script_text: str = "一つ目の段落。\n二つ目の段落。",
    max_chars_per_chunk: int = 1_000,
    preflight_id: str = "preflight.zero.1",
    consent_state: ConsentState = ConsentState.ACTIVE,
    profile_exact_model_id: str = "qwen3",
    profile_capability_engine_id: str = "qwen3",
    engine_overrides: dict[str, object] | None = None,
    job_state: DurableJobState = DurableJobState.REGISTERED,
    operation_identity_override: str | None = None,
    authorization_expires_at: str = EXPIRES_AT,
    resource_state: ContractState = ContractState.BOUND_VERIFIED,
) -> dict[str, object]:
    voice = VoiceProfile(
        "voice.profile.owner",
        "LOCAL",
        "credential://fixture-only",
        "fixture-private-voice",
        True,
        True,
        ("ja-JP",),
        ("qwen3",),
        "owner.subject",
        "Local owner narration",
    )
    consent = ConsentReference(
        "owner.subject",
        "Local owner narration",
        ("OWNER_NARRATION_LOCAL",),
        consent_state,
        True,
        "consent.evidence.1",
        h("consent evidence"),
    )
    profile = VoiceProfileRevision(
        voice.voice_profile_id,
        voice.profile_digest,
        1,
        None,
        "2026-08-20T00:00:00Z",
        consent,
        LicenseReference(
            "model.artifact.1",
            profile_exact_model_id,
            h("model artifact"),
            "runtime.local.1",
            ModelLicenseClass.COMMERCIAL_ALLOWED,
            ArtifactAdmissionState.APPROVED,
            True,
            "license.evidence.1",
            h("license evidence"),
        ),
        LocalVoiceCapabilityDescription(
            "LOCAL",
            profile_capability_engine_id,
            ("ja-JP",),
            ("ZERO_SHOT",),
            True,
            CapabilityProbeState.VERIFIED,
            h("capability probe"),
        ),
    )
    script = NarrationScript("script.revision.1", script_text, "owner.subject")
    plan = NarrationPlanningService.compile(
        script,
        voice,
        mode=NarrationGenerationMode.PREVIEW if intended_usage is NarrationIntendedUsage.PREVIEW else NarrationGenerationMode.FULL_RENDER,
        model_id="qwen3",
        language_code="ja-JP",
        max_chars_per_chunk=max_chars_per_chunk,
    )
    engine: dict[str, object] = {
        "contract_state": "BOUND_VERIFIED",
        "route_mode": route.value,
        "engine_id": "qwen3",
        "engine_revision_sha256": h("engine revision"),
        "model_artifact_id": "model.artifact.1",
        "model_artifact_sha256": h("model artifact"),
        "runtime_id": "runtime.local.1",
        "runtime_sha256": h("runtime revision"),
        "code_revision_sha256": h("engine code revision"),
        "license_state": "COMMERCIAL_ALLOWED",
        "license_evidence_ref": "license.evidence.1",
        "license_evidence_sha256": h("license evidence"),
        "capability_probe_state": "VERIFIED",
        "capability_probe_ref": "capability.probe.1",
        "capability_probe_sha256": h("capability probe"),
    }
    engine.update(engine_overrides or {})
    zero = {
        "contract_state": "BOUND_VERIFIED",
        "asset_id": "asset.owner.reference",
        "asset_checksum_sha256": h("reference audio"),
        "asset_revision_binding_ref": "asset.revision.binding.1",
        "asset_revision_binding_sha256": h("asset revision binding"),
        "reference_profile_ref": "reference.profile.1",
        "reference_profile_sha256": h("reference profile"),
        "consent_current_evaluation_sha256": h("current consent"),
        "rights_current_evaluation_sha256": h("current rights"),
        "audio_body_persisted": False,
    }
    fine_tuned = {
        "contract_state": "BOUND_VERIFIED",
        "dataset_revision_id": "dataset.revision.1",
        "dataset_revision_sha256": h("dataset revision"),
        "training_input_snapshot_id": "training.snapshot.1",
        "training_input_snapshot_sha256": h("training snapshot"),
        "model_candidate_revision_id": "model.candidate.1",
        "model_candidate_revision_sha256": h("model candidate"),
        "model_artifact_binding_ref": "model.binding.1",
        "model_artifact_binding_sha256": h("model binding"),
        "owner_model_approval_decision_ref": "model.approval.1",
        "owner_model_approval_decision_sha256": h("model approval"),
        "consent_current_evaluation_sha256": h("current consent"),
        "rights_current_evaluation_sha256": h("current rights"),
        "dataset_body_persisted": False,
        "model_bytes_persisted": False,
    }
    preflight = compile_local_primary_preflight(
        project_id="project.alpha",
        preflight_id=preflight_id,
        created_at="2026-08-20T00:00:00Z",
        route_mode=route,
        intended_usage=intended_usage,
        script_text_binding={
            "text_owner": "TASK-006",
            "approved_text_revision_ref": script.script_id,
            "approved_text_revision_sha256": script.script_sha256,
            "source_text_binding_sha256": h("source text binding"),
            "approved": True,
            "body_persisted": False,
        },
        voice_profile_revision_binding={
            "contract_state": "BOUND_VERIFIED",
            "voice_profile_id": profile.voice_profile_id,
            "canonical_narration_profile_sha256": profile.canonical_narration_profile_sha256,
            "revision": profile.revision,
            "parent_revision_sha256": profile.parent_revision_sha256,
            "voice_profile_revision_sha256": profile.voice_profile_revision_sha256,
            "consent": profile.consent.to_dict(),
            "current_consent_state": consent_state.value,
            "current_consent_evaluation_sha256": h("current consent"),
            "canonical_evidence_ref": "profile.evidence.1",
            "canonical_evidence_sha256": h("profile evidence"),
        },
        engine_admission_binding=engine,
        resource_feasibility_binding={
            "contract_state": "BOUND_VERIFIED",
            "route_mode": route.value,
            "resource_profile_ref": "resource.profile.1",
            "resource_profile_sha256": h("resource profile"),
            "result": "PASS",
            "evidence_ref": "resource.evidence.1",
            "evidence_sha256": h("resource evidence"),
        },
        rights_evaluation_binding={
            "contract_state": "BOUND_VERIFIED",
            "usage_class": "LOCAL_NARRATION_PREVIEW" if intended_usage is NarrationIntendedUsage.PREVIEW else "LOCAL_NARRATION_FULL_RENDER",
            "state": "PASS",
            "evidence_ref": "rights.evidence.1",
            "evidence_sha256": h("current rights"),
            "evaluated_at": "2026-08-20T00:00:00Z",
        },
        zero_shot_reference_binding=zero if route is LocalNarrationRouteMode.ZERO_SHOT_LOCAL else None,
        fine_tuned_model_binding=fine_tuned if route is LocalNarrationRouteMode.FINE_TUNED_LOCAL else None,
    )
    destination_policy_sha256 = h("destination policy")
    operation_identity = render_operation_identity_sha256(
        project_id="project.alpha",
        admission_id="admission.render.1",
        admission_revision=1,
        route_mode=route,
        intended_usage=intended_usage,
        script_text_revision_sha256=script.script_sha256,
        voice_profile_revision_sha256=profile.voice_profile_revision_sha256,
        preflight_sha256=preflight.preflight_sha256,
        destination_policy_sha256=destination_policy_sha256,
    )
    operation_identity = operation_identity_override or operation_identity
    if resource_state is ContractState.BOUND_VERIFIED:
        resource = ResourceAdmissionBinding(
            resource_state,
            "resource.gate.1",
            h("resource gate"),
            "LOCAL_NARRATION_RENDER",
            route,
            preflight.preflight_sha256,
            ResourceGateDecision.ADMITTED,
            EVALUATED_AT,
            EXPIRES_AT,
        )
    else:
        resource = ResourceAdmissionBinding(resource_state, None, None, None, None, None, None, None, None)
    if resource_state is ContractState.BOUND_VERIFIED:
        authorization = ExecutionAuthorizationBinding(
            ContractState.BOUND_VERIFIED,
            "authorization.owner.1",
            1,
            h("authorization"),
            AuthorityKind.OWNER_HUMAN_GATE,
            "project.alpha",
            "admission.render.1",
            1,
            route,
            intended_usage,
            script.script_sha256,
            profile.voice_profile_revision_sha256,
            preflight.preflight_sha256,
            resource.resource_gate_sha256,
            h("job revision"),
            destination_policy_sha256,
            RenderAuthorizationScope.PREVIEW_RENDER if intended_usage is NarrationIntendedUsage.PREVIEW else RenderAuthorizationScope.FULL_RENDER,
            EVALUATED_AT,
            authorization_expires_at,
            True,
            "authorization.evidence.1",
            h("authorization evidence"),
        )
    else:
        authorization = ExecutionAuthorizationBinding(resource_state, *([None] * 21))
    admission = compile_render_admission(
        project_id="project.alpha",
        admission_id="admission.render.1",
        revision=1,
        parent_revision_sha256=None,
        created_at=ADMISSION_AT,
        route_mode=route,
        intended_usage=intended_usage,
        script_text_revision_id=script.script_id,
        script_text_revision_sha256=script.script_sha256,
        voice_profile_revision_id=profile.voice_profile_id,
        voice_profile_revision_sha256=profile.voice_profile_revision_sha256,
        preflight_binding=LocalPrimaryPreflightBinding(
            ContractState.BOUND_VERIFIED,
            preflight.preflight_id,
            preflight.preflight_sha256,
            route,
            intended_usage,
            script.script_sha256,
            profile.voice_profile_revision_sha256,
            preflight.decision,
            "2026-08-20T00:00:00Z",
            EXPIRES_AT,
        ),
        resource_admission_binding=resource,
        durable_job_binding=DurableNarrationJobBinding(
            ContractState.BOUND_VERIFIED,
            "job.narration.1",
            1,
            h("job revision"),
            operation_identity,
            h("idempotency"),
            job_state,
        ),
        output_destination_binding=OutputStagingDestinationBinding(
            ContractState.BOUND_VERIFIED,
            "destination.narration.1",
            "storage.owner.1",
            destination_policy_sha256,
            h("quota"),
            h("recovery"),
            h("retention"),
            "STAGED_NARRATION_PCM_WAV_48000_MONO",
            False,
        ),
        execution_authorization_binding=authorization,
    )
    return {
        "voice": voice,
        "script": script,
        "profile": profile,
        "plan": plan,
        "preflight": preflight,
        "admission": admission,
    }


def subject_receipt(parts: dict[str, object], **overrides: object) -> ZeroShotReferenceSubjectBindingReceipt:
    profile = parts["profile"]
    preflight = parts["preflight"]
    zero = preflight.zero_shot_reference_binding
    assert zero is not None
    body: dict[str, object] = {
        "schema": SUBJECT_RECEIPT_SCHEMA_ID,
        "record_type": "ZeroShotReferenceSubjectBindingReceipt",
        "task_owner": "TASK-014",
        "project_id": preflight.project_id,
        "voice_profile_id": profile.voice_profile_id,
        "voice_profile_revision_sha256": profile.voice_profile_revision_sha256,
        "consent_sha256": profile.consent.to_dict()["consent_sha256"],
        "consent_subject_ref_sha256": h(profile.consent.consent_subject_ref),
        "reference_asset_id": zero["asset_id"],
        "reference_asset_checksum_sha256": zero["asset_checksum_sha256"],
        "asset_revision_binding_ref": zero["asset_revision_binding_ref"],
        "asset_revision_binding_sha256": zero["asset_revision_binding_sha256"],
        "reference_profile_ref": zero["reference_profile_ref"],
        "reference_profile_sha256": zero["reference_profile_sha256"],
        "capture_lineage_ref": "capture.lineage.1",
        "capture_lineage_sha256": h("capture lineage"),
        "consent_current_evaluation_sha256": zero["consent_current_evaluation_sha256"],
        "rights_current_evaluation_sha256": zero["rights_current_evaluation_sha256"],
        "authority_kind": SubjectBindingAuthorityKind.CANONICAL_OWNER_CAPTURE_CHAIN.value,
        "subject_match_decision": SubjectMatchDecision.VERIFIED_SAME_SUBJECT.value,
        "subject_match_evidence_ref": "subject.match.evidence.1",
        "subject_match_evidence_sha256": h("subject match evidence"),
        "evaluated_at": EVALUATED_AT,
        "expires_at": EXPIRES_AT,
        "usage_scope": "ZERO_SHOT_OWNER_NARRATION",
        "audio_body_persisted": False,
        "speaker_embedding_persisted": False,
        "private_subject_ref_persisted": False,
        "host_path_persisted": False,
    }
    body.update(overrides)
    content_sha = sha256_bytes(canonical_json_bytes(body))
    values = {key: value for key, value in body.items() if key not in {"schema", "record_type", "task_owner"}}
    return ZeroShotReferenceSubjectBindingReceipt(
        receipt_id="zero-shot-subject-receipt-" + content_sha.removeprefix("sha256:"),
        receipt_sha256=content_sha,
        **values,
    )


def plan_receipt(parts: dict[str, object], **overrides: object) -> CanonicalNarrationPlanRevisionReceipt:
    profile = parts["profile"]
    preflight = parts["preflight"]
    plan = parts["plan"]
    body: dict[str, object] = {
        "schema": PLAN_RECEIPT_SCHEMA_ID,
        "record_type": "CanonicalNarrationPlanRevisionReceipt",
        "task_owner": "TASK-014",
        "project_id": preflight.project_id,
        "plan_id": plan.plan_id,
        "plan_revision": 1,
        "parent_plan_revision_sha256": None,
        "plan_sha256": plan.to_dict()["plan_sha256"],
        "approved_text_revision_ref": preflight.script_text_binding["approved_text_revision_ref"],
        "approved_text_revision_sha256": preflight.script_text_binding["approved_text_revision_sha256"],
        "approved_script_body_sha256": plan.script_sha256,
        "approved_text_code_point_count": len(parts["script"].text),
        "source_text_binding_sha256": preflight.script_text_binding["source_text_binding_sha256"],
        "voice_profile_id": profile.voice_profile_id,
        "voice_profile_revision_sha256": profile.voice_profile_revision_sha256,
        "route_mode": LocalNarrationRouteMode.ZERO_SHOT_LOCAL.value,
        "mode": plan.mode.value,
        "model_id": plan.model_id,
        "language_code": plan.language_code,
        "normalization_policy_id": "normalization.policy.1",
        "normalization_policy_revision": 1,
        "normalization_policy_sha256": h("normalization policy"),
        "chunking_policy_id": "chunking.policy.1",
        "chunking_policy_revision": 1,
        "chunking_policy_sha256": h("chunking policy"),
        "compiler_code_revision_sha256": h("plan compiler code"),
        "ordered_chunk_manifest_sha256": _ordered_chunk_manifest_sha256(plan),
        "chunk_count": len(plan.chunks),
        "plan_store_ref": "plan.store.1",
        "plan_store_revision": 1,
        "plan_store_record_sha256": h("plan store record"),
        "authority_kind": PlanDerivationAuthorityKind.CANONICAL_NARRATION_PLAN_STORE.value,
        "derivation_decision": PlanDerivationDecision.VERIFIED_FROM_APPROVED_BODY.value,
        "derivation_evidence_ref": "plan.derivation.evidence.1",
        "derivation_evidence_sha256": h("plan derivation evidence"),
        "evaluated_at": EVALUATED_AT,
        "expires_at": EXPIRES_AT,
        "script_body_persisted": False,
        "chunk_body_persisted": False,
        "host_path_persisted": False,
        "execution_authorized": False,
    }
    body.update(overrides)
    content_sha = sha256_bytes(canonical_json_bytes(body))
    values = {key: value for key, value in body.items() if key not in {"schema", "record_type", "task_owner"}}
    return CanonicalNarrationPlanRevisionReceipt(
        receipt_id="narration-plan-derivation-receipt-" + content_sha.removeprefix("sha256:"),
        receipt_sha256=content_sha,
        **values,
    )


def transcript_receipt(
    parts: dict[str, object], **overrides: object
) -> ZeroShotReferenceTranscriptBindingReceipt:
    profile = parts["profile"]
    preflight = parts["preflight"]
    zero = preflight.zero_shot_reference_binding
    assert zero is not None
    body: dict[str, object] = {
        "schema": TRANSCRIPT_RECEIPT_SCHEMA_ID,
        "record_type": "ZeroShotReferenceTranscriptBindingReceipt",
        "task_owner": "TASK-014",
        "project_id": preflight.project_id,
        "voice_profile_id": profile.voice_profile_id,
        "voice_profile_revision_sha256": profile.voice_profile_revision_sha256,
        "reference_asset_id": zero["asset_id"],
        "reference_asset_checksum_sha256": zero["asset_checksum_sha256"],
        "asset_revision_binding_ref": zero["asset_revision_binding_ref"],
        "asset_revision_binding_sha256": zero["asset_revision_binding_sha256"],
        "reference_profile_ref": zero["reference_profile_ref"],
        "reference_profile_sha256": zero["reference_profile_sha256"],
        "transcript_revision_ref": "reference.transcript.revision.1",
        "transcript_revision_sha256": h("reference transcript revision"),
        "transcript_body_sha256": h("exact reference transcript body"),
        "transcript_language_code": parts["plan"].language_code,
        "consent_current_evaluation_sha256": zero["consent_current_evaluation_sha256"],
        "rights_current_evaluation_sha256": zero["rights_current_evaluation_sha256"],
        "authority_kind": ReferenceTranscriptAuthorityKind.CANONICAL_REFERENCE_TRANSCRIPT_STORE.value,
        "transcript_decision": ReferenceTranscriptDecision.VERIFIED_EXACT_TRANSCRIPT.value,
        "transcript_evidence_ref": "reference.transcript.evidence.1",
        "transcript_evidence_sha256": h("reference transcript evidence"),
        "evaluated_at": EVALUATED_AT,
        "expires_at": EXPIRES_AT,
        "usage_scope": "ZERO_SHOT_OWNER_NARRATION",
        "transcript_body_persisted": False,
        "audio_body_persisted": False,
        "private_handle_persisted": False,
        "host_path_persisted": False,
    }
    body.update(overrides)
    content_sha = sha256_bytes(canonical_json_bytes(body))
    values = {key: value for key, value in body.items() if key not in {"schema", "record_type", "task_owner"}}
    return ZeroShotReferenceTranscriptBindingReceipt(
        receipt_id="zero-shot-transcript-receipt-" + content_sha.removeprefix("sha256:"),
        receipt_sha256=content_sha,
        **values,
    )


def compile_ready(parts: dict[str, object], **overrides: object):
    if "subject_binding_receipt" in overrides:
        subject = overrides.pop("subject_binding_receipt")
    else:
        preflight = parts["preflight"]
        subject = subject_receipt(parts) if preflight.zero_shot_reference_binding is not None else None
    derivation = (
        overrides.pop("plan_derivation_receipt")
        if "plan_derivation_receipt" in overrides
        else plan_receipt(parts)
    )
    transcript = (
        overrides.pop("reference_transcript_receipt")
        if "reference_transcript_receipt" in overrides
        else transcript_receipt(parts) if parts["preflight"].zero_shot_reference_binding is not None else None
    )
    values = {
        "admission": parts["admission"],
        "preflight": parts["preflight"],
        "profile_revision": parts["profile"],
        "plan": parts["plan"],
        "subject_binding_receipt": subject,
        "plan_derivation_receipt": derivation,
        "reference_transcript_receipt": transcript,
        "compiled_at": COMPILED_AT,
    }
    values.update(overrides)
    return compile_zero_shot_callable_envelope(**values)


def test_consistent_zero_shot_callable_envelope_is_body_free_and_deterministic() -> None:
    parts = assembled()
    first = compile_ready(parts)
    second = compile_ready(parts)
    assert first.decision is CallableEnvelopeDecision.UNKNOWN
    assert first.reason_codes == (
        "CANONICAL_AUTHORITY_NOT_CONFIRMED",
        "CANONICAL_TRANSCRIPT_AUTHORITY_NOT_CONFIRMED",
        "TRUSTED_EVALUATION_TIME_NOT_CONFIRMED",
    )
    assert first.to_private_dict() == second.to_private_dict()
    private = first.to_private_dict()
    assert private["required_artifact_class"] == "STAGED_NARRATION_PCM_WAV_48000_MONO"
    assert private["engine_revision_sha256"] == parts["preflight"].engine_admission_binding["engine_revision_sha256"]
    assert private["model_artifact_sha256"] == parts["preflight"].engine_admission_binding["model_artifact_sha256"]
    assert private["runtime_sha256"] == parts["preflight"].engine_admission_binding["runtime_sha256"]
    assert private["code_revision_sha256"] == parts["preflight"].engine_admission_binding["code_revision_sha256"]
    assert private["preview_text_code_point_count"] == len(parts["script"].text)
    assert private["model_loader_operation"] == "Qwen3TTSModel.from_pretrained"
    assert private["loader_model_root_argument"] == "POSITIONAL_0_EXACT_LOCAL_MODEL_ROOT"
    assert private["loader_attention_argument"] == "attn_implementation"
    assert private["generation_operation"] == "generate_voice_clone"
    assert private["generation_text_argument"] == "text"
    assert private["generation_language_argument"] == "language"
    assert private["generation_reference_audio_argument"] == "ref_audio"
    assert private["generation_reference_text_argument"] == "ref_text"
    assert private["reference_audio_reader_operation"] == "soundfile.read"
    assert private["audio_reader_dtype_argument"] == "dtype"
    assert private["audio_reader_always_2d_argument"] == "always_2d"
    assert private["local_files_only"] is True
    assert private["reference_audio_transport"] == "IN_MEMORY_WAVEFORM_SAMPLE_RATE_TUPLE"
    assert private["automatic_retry_allowed"] is False
    assert private["timeout_seconds"] == 180
    assert private["max_output_duration_seconds"] == 60
    assert private["max_output_bytes"] == 104_857_600
    assert private["runner_visibility"] == "HIDDEN"
    assert private["timeout_termination_scope"] == "EXACT_CHILD_ONLY"
    assert private["dispatch_ambiguity_decision"] == "UNKNOWN"
    assert private["ambiguous_dispatch_retry_allowed"] is False
    assert private["ambiguous_dispatch_replay_allowed"] is False
    for flag in (
        "script_body_persisted",
        "audio_body_persisted",
        "private_voice_id_persisted",
        "credential_value_persisted",
        "host_path_persisted",
        "execution_started",
        "dispatch_started",
        "model_loaded",
        "gpu_reserved",
        "audio_rendered",
        "asset_published",
        "transcript_body_persisted",
        "reference_audio_persisted",
        "runtime_object_persisted",
        "generation_started",
        "retry_started",
        "waveform_observed",
        "result_adopted",
        "qa_started",
    ):
        assert private[flag] is False
    encoded = json.dumps(private, ensure_ascii=False, sort_keys=True)
    assert "一つ目" not in encoded
    assert "fixture-private-voice" not in encoded
    assert "credential://fixture-only" not in encoded


def test_self_minted_receipts_and_envelope_cannot_claim_dispatch_authority() -> None:
    parts = assembled()
    envelope = compile_ready(parts)
    assert envelope.decision is CallableEnvelopeDecision.UNKNOWN
    document = envelope.to_private_dict()
    document["decision"] = "READY_FOR_EXTERNAL_DISPATCH_GATE"
    with pytest.raises(ValueError, match="decision is invalid"):
        parse_zero_shot_callable_envelope(document)


def test_h1_h2_h3_and_envelope_round_trip_are_typed_and_tamper_evident() -> None:
    parts = assembled()
    h1 = subject_receipt(parts)
    h2 = plan_receipt(parts)
    h3 = transcript_receipt(parts)
    envelope = compile_ready(parts, subject_binding_receipt=h1, plan_derivation_receipt=h2, reference_transcript_receipt=h3)
    assert parse_zero_shot_reference_subject_binding_receipt(h1.to_private_dict()) == h1
    assert parse_canonical_narration_plan_revision_receipt(h2.to_private_dict()) == h2
    assert parse_zero_shot_reference_transcript_binding_receipt(h3.to_private_dict()) == h3
    assert parse_zero_shot_callable_envelope(envelope.to_private_dict()) == envelope
    for value, parser, field in (
        (h1.to_private_dict(), parse_zero_shot_reference_subject_binding_receipt, "reference_profile_sha256"),
        (h2.to_private_dict(), parse_canonical_narration_plan_revision_receipt, "plan_sha256"),
        (h3.to_private_dict(), parse_zero_shot_reference_transcript_binding_receipt, "transcript_body_sha256"),
        (envelope.to_private_dict(), parse_zero_shot_callable_envelope, "engine_revision_sha256"),
    ):
        value[field] = h("tampered")
        with pytest.raises(ValueError, match="content address"):
            parser(value)


@pytest.mark.parametrize(
    "receipt_name, expected_reason",
    [
        ("subject", "SUBJECT_BINDING_NOT_PROVIDED"),
        ("plan", "PLAN_DERIVATION_NOT_PROVIDED"),
        ("transcript", "REFERENCE_TRANSCRIPT_NOT_PROVIDED"),
    ],
)
def test_missing_typed_receipt_is_unknown(receipt_name: str, expected_reason: str) -> None:
    parts = assembled()
    field = {
        "subject": "subject_binding_receipt",
        "plan": "plan_derivation_receipt",
        "transcript": "reference_transcript_receipt",
    }[receipt_name]
    overrides = {field: None}
    result = compile_ready(parts, **overrides)
    assert result.decision is CallableEnvelopeDecision.UNKNOWN
    assert result.reason_codes == (expected_reason,)


@pytest.mark.parametrize(
    "receipt_name, expected_reason",
    [
        ("subject", "SUBJECT_BINDING_UNKNOWN"),
        ("plan", "PLAN_DERIVATION_UNKNOWN"),
        ("transcript", "REFERENCE_TRANSCRIPT_UNKNOWN"),
    ],
)
def test_unknown_typed_receipt_is_fail_closed(receipt_name: str, expected_reason: str) -> None:
    parts = assembled()
    if receipt_name == "subject":
        overrides = {"subject_binding_receipt": subject_receipt(parts, subject_match_decision="UNKNOWN")}
    elif receipt_name == "plan":
        overrides = {"plan_derivation_receipt": plan_receipt(parts, derivation_decision="UNKNOWN")}
    else:
        overrides = {"reference_transcript_receipt": transcript_receipt(parts, transcript_decision="UNKNOWN")}
    result = compile_ready(parts, **overrides)
    assert result.decision is CallableEnvelopeDecision.UNKNOWN
    assert result.reason_codes == (expected_reason,)


@pytest.mark.parametrize(
    "receipt_name, expected_reason",
    [
        ("subject", "SUBJECT_BINDING_MISMATCH"),
        ("plan", "PLAN_DERIVATION_MISMATCH"),
        ("transcript", "REFERENCE_TRANSCRIPT_MISMATCH"),
    ],
)
def test_mismatched_typed_receipt_is_blocked(receipt_name: str, expected_reason: str) -> None:
    parts = assembled()
    if receipt_name == "subject":
        overrides = {"subject_binding_receipt": subject_receipt(parts, subject_match_decision="MISMATCH")}
    elif receipt_name == "plan":
        overrides = {"plan_derivation_receipt": plan_receipt(parts, derivation_decision="MISMATCH")}
    else:
        overrides = {"reference_transcript_receipt": transcript_receipt(parts, transcript_decision="MISMATCH")}
    result = compile_ready(parts, **overrides)
    assert result.decision is CallableEnvelopeDecision.BLOCKED
    assert result.reason_codes == (expected_reason,)


@pytest.mark.parametrize(
    "receipt_name, expected_reason",
    [
        ("subject", "SUBJECT_BINDING_EXPIRED"),
        ("plan", "PLAN_DERIVATION_EXPIRED"),
        ("transcript", "REFERENCE_TRANSCRIPT_EXPIRED"),
    ],
)
def test_expired_typed_receipt_is_blocked(receipt_name: str, expected_reason: str) -> None:
    parts = assembled()
    if receipt_name == "subject":
        overrides = {"subject_binding_receipt": subject_receipt(parts, expires_at="2026-08-20T00:01:00Z")}
    elif receipt_name == "plan":
        overrides = {"plan_derivation_receipt": plan_receipt(parts, expires_at="2026-08-20T00:01:00Z")}
    else:
        overrides = {"reference_transcript_receipt": transcript_receipt(parts, expires_at="2026-08-20T00:01:00Z")}
    result = compile_ready(parts, **overrides)
    assert result.decision is CallableEnvelopeDecision.BLOCKED
    assert result.reason_codes == (expected_reason,)


def test_callable_time_order_and_exact_expiry_are_fail_closed() -> None:
    parts = assembled()
    backdated = compile_ready(parts, compiled_at="2026-08-20T00:00:45Z")
    assert backdated.decision is CallableEnvelopeDecision.BLOCKED
    assert "CALLABLE_TIME_ORDER_MISMATCH" in backdated.reason_codes

    future_subject = subject_receipt(
        parts,
        evaluated_at="2026-08-20T00:03:00Z",
        expires_at=EXPIRES_AT,
    )
    future_result = compile_ready(parts, subject_binding_receipt=future_subject)
    assert future_result.decision is CallableEnvelopeDecision.BLOCKED
    assert "CALLABLE_TIME_ORDER_MISMATCH" in future_result.reason_codes

    exact_expiry = compile_ready(parts, compiled_at=EXPIRES_AT)
    assert exact_expiry.decision is CallableEnvelopeDecision.BLOCKED
    assert "SUBJECT_BINDING_EXPIRED" in exact_expiry.reason_codes
    assert "PLAN_DERIVATION_EXPIRED" in exact_expiry.reason_codes
    assert "REFERENCE_TRANSCRIPT_EXPIRED" in exact_expiry.reason_codes
    assert "AUTHORIZATION_EXPIRED" in exact_expiry.reason_codes


@pytest.mark.parametrize(
    "field",
    [
        "reference_asset_checksum_sha256",
        "asset_revision_binding_sha256",
        "reference_profile_sha256",
        "consent_current_evaluation_sha256",
        "rights_current_evaluation_sha256",
    ],
)
def test_h1_zero_shot_reference_coordinates_must_match_preflight(field: str) -> None:
    parts = assembled()
    result = compile_ready(parts, subject_binding_receipt=subject_receipt(parts, **{field: h("other " + field)}))
    assert result.decision is CallableEnvelopeDecision.BLOCKED
    assert "ZERO_SHOT_REFERENCE_MISMATCH" in result.reason_codes or "SUBJECT_BINDING_MISMATCH" in result.reason_codes


@pytest.mark.parametrize(
    "field",
    [
        "voice_profile_id",
        "voice_profile_revision_sha256",
        "consent_sha256",
        "consent_subject_ref_sha256",
    ],
)
def test_h1_subject_and_voice_profile_coordinates_must_match(field: str) -> None:
    parts = assembled()
    replacement = "voice.profile.other" if field == "voice_profile_id" else h("other " + field)
    result = compile_ready(
        parts,
        subject_binding_receipt=subject_receipt(parts, **{field: replacement}),
    )
    assert result.decision is CallableEnvelopeDecision.BLOCKED
    assert "SUBJECT_BINDING_MISMATCH" in result.reason_codes


@pytest.mark.parametrize(
    "field,replacement",
    [
        ("voice_profile_id", "voice.profile.other"),
        ("voice_profile_revision_sha256", h("other voice profile")),
        ("reference_asset_id", "asset.reference.other"),
        ("reference_asset_checksum_sha256", h("other reference asset")),
        ("asset_revision_binding_sha256", h("other asset revision")),
        ("reference_profile_sha256", h("other reference profile")),
        ("transcript_language_code", "en-US"),
        ("consent_current_evaluation_sha256", h("other consent evaluation")),
        ("rights_current_evaluation_sha256", h("other rights evaluation")),
    ],
)
def test_h3_reference_transcript_is_cross_bound_to_asset_profile_and_current_gates(
    field: str, replacement: object
) -> None:
    parts = assembled()
    result = compile_ready(
        parts,
        reference_transcript_receipt=transcript_receipt(parts, **{field: replacement}),
    )
    assert result.decision is CallableEnvelopeDecision.BLOCKED
    assert result.reason_codes == ("REFERENCE_TRANSCRIPT_BINDING_MISMATCH",)


def test_preview_text_code_point_limit_is_exact_and_body_free() -> None:
    at_limit_parts = assembled(script_text="あ" * 200)
    at_limit = compile_ready(at_limit_parts)
    assert at_limit.decision is CallableEnvelopeDecision.UNKNOWN
    assert "PREVIEW_TEXT_TOO_LONG" not in at_limit.reason_codes
    assert at_limit.preview_text_code_point_count == 200
    assert at_limit.preview_call_text_body_sha256 == at_limit_parts["script"].script_sha256

    over_limit_parts = assembled(script_text="あ" * 201)
    over_limit = compile_ready(over_limit_parts)
    assert over_limit.decision is CallableEnvelopeDecision.BLOCKED
    assert over_limit.reason_codes == ("PREVIEW_TEXT_TOO_LONG",)


def test_preview_call_text_count_and_single_chunk_derivation_are_fail_closed() -> None:
    parts = assembled()
    false_count = compile_ready(
        parts,
        plan_derivation_receipt=plan_receipt(parts, approved_text_code_point_count=200),
    )
    assert false_count.decision is CallableEnvelopeDecision.BLOCKED
    assert false_count.reason_codes == ("PLAN_DERIVATION_MISMATCH",)

    multi_chunk = assembled(script_text="あ" * 201, max_chars_per_chunk=100)
    multi_result = compile_ready(multi_chunk)
    assert multi_result.decision is CallableEnvelopeDecision.BLOCKED
    assert "PREVIEW_CALL_TEXT_DERIVATION_MISMATCH" in multi_result.reason_codes
    assert "PREVIEW_TEXT_TOO_LONG" in multi_result.reason_codes
    assert multi_result.preview_call_text_body_sha256 is None


def test_actual_voice_profile_revision_must_match_admission() -> None:
    parts = assembled()
    wrong_profile = replace(parts["profile"], voice_profile_id="voice.profile.other")
    result = compile_ready(parts, profile_revision=wrong_profile)
    assert result.decision is CallableEnvelopeDecision.BLOCKED
    assert "VOICE_PROFILE_REVISION_MISMATCH" in result.reason_codes
    assert "SUBJECT_BINDING_MISMATCH" in result.reason_codes


@pytest.mark.parametrize(
    "field",
    [
        "plan_sha256",
        "approved_text_revision_sha256",
        "approved_script_body_sha256",
        "voice_profile_revision_sha256",
        "ordered_chunk_manifest_sha256",
    ],
)
def test_h2_plan_derivation_coordinates_must_match_canonical_plan(field: str) -> None:
    parts = assembled()
    result = compile_ready(parts, plan_derivation_receipt=plan_receipt(parts, **{field: h("other " + field)}))
    assert result.decision is CallableEnvelopeDecision.BLOCKED
    assert result.reason_codes == ("PLAN_DERIVATION_MISMATCH",)


def test_plan_chunk_integrity_is_recomputed_from_ephemeral_chunks() -> None:
    parts = assembled()
    plan = parts["plan"]
    bad_chunk = replace(plan.chunks[0], text_sha256=h("wrong chunk body"))
    bad_plan = replace(plan, chunks=(bad_chunk, *plan.chunks[1:]))
    result = compile_ready(parts, plan=bad_plan)
    assert result.decision is CallableEnvelopeDecision.BLOCKED
    assert "PLAN_CHUNK_INTEGRITY_MISMATCH" in result.reason_codes


def test_callable_requires_zero_shot_route() -> None:
    parts = assembled(route=LocalNarrationRouteMode.FINE_TUNED_LOCAL)
    result = compile_ready(
        parts,
        subject_binding_receipt=None,
        plan_derivation_receipt=None,
    )
    assert result.decision is CallableEnvelopeDecision.BLOCKED
    assert "ZERO_SHOT_ROUTE_REQUIRED" in result.reason_codes


def test_one_shot_callable_surface_requires_preview_usage() -> None:
    parts = assembled(intended_usage=NarrationIntendedUsage.FULL_RENDER)
    result = compile_ready(parts)
    assert result.decision is CallableEnvelopeDecision.BLOCKED
    assert result.reason_codes == ("PREVIEW_USAGE_REQUIRED",)
    long_result = compile_ready(
        parts,
        plan_derivation_receipt=plan_receipt(parts, approved_text_code_point_count=201),
    )
    assert long_result.reason_codes == ("PREVIEW_USAGE_REQUIRED",)


def test_callable_requires_exact_preflight_and_ready_sources() -> None:
    ready = assembled()
    other = assembled(preflight_id="preflight.zero.other")
    mismatch = compile_ready(ready, preflight=other["preflight"])
    assert mismatch.decision is CallableEnvelopeDecision.BLOCKED
    assert "PREFLIGHT_BINDING_MISMATCH" in mismatch.reason_codes

    revoked = assembled(consent_state=ConsentState.REVOKED)
    blocked = compile_ready(revoked)
    assert blocked.decision is CallableEnvelopeDecision.BLOCKED
    assert "ADMISSION_NOT_READY" in blocked.reason_codes
    assert "PREFLIGHT_NOT_READY" in blocked.reason_codes
    assert "VOICE_PROFILE_NOT_ADMITTED" in blocked.reason_codes


@pytest.mark.parametrize(
    "engine_overrides",
    [
        {"engine_id": "other-engine"},
        {"model_artifact_id": "model.artifact.other"},
        {"model_artifact_sha256": h("other model")},
        {"runtime_id": "runtime.other"},
    ],
)
def test_engine_model_and_runtime_bindings_are_exact(engine_overrides: dict[str, object]) -> None:
    parts = assembled(engine_overrides=engine_overrides)
    result = compile_ready(parts)
    assert result.decision is CallableEnvelopeDecision.BLOCKED
    assert "ENGINE_BINDING_MISMATCH" in result.reason_codes


@pytest.mark.parametrize(
    "field",
    [
        "engine_id",
        "engine_revision_sha256",
        "model_artifact_id",
        "model_artifact_sha256",
        "runtime_id",
        "runtime_sha256",
        "code_revision_sha256",
    ],
)
def test_missing_engine_model_runtime_or_code_binding_is_structurally_rejected(field: str) -> None:
    parts = assembled()
    document = parts["preflight"].to_private_dict()
    document["engine_admission_binding"][field] = None
    with pytest.raises(ValueError, match="incomplete"):
        parse_local_primary_preflight(document)


def test_operation_job_destination_and_authorization_are_fail_closed() -> None:
    wrong_operation = assembled(operation_identity_override=h("wrong operation"))
    operation_result = compile_ready(wrong_operation)
    assert "OPERATION_IDENTITY_MISMATCH" in operation_result.reason_codes
    assert "ADMISSION_NOT_READY" in operation_result.reason_codes

    wrong_job = assembled(job_state=DurableJobState.QUEUED)
    job_result = compile_ready(wrong_job)
    assert "JOB_BINDING_MISMATCH" in job_result.reason_codes

    unresolved_resource = assembled(resource_state=ContractState.UNKNOWN)
    resource_result = compile_ready(unresolved_resource)
    assert "RESOURCE_OR_DESTINATION_MISMATCH" in resource_result.reason_codes

    expired = assembled(authorization_expires_at="2026-08-20T00:01:30Z")
    authorization_result = compile_ready(expired)
    assert "AUTHORIZATION_EXPIRED" in authorization_result.reason_codes


@pytest.mark.parametrize(
    "field, replacement",
    [
        ("required_artifact_class", "STAGED_NARRATION_OTHER"),
        ("required_sample_rate_hz", 44_100),
        ("required_channels", 2),
        ("required_sample_format", "PCM_S16LE"),
    ],
)
def test_intended_output_constraints_cannot_be_substituted(field: str, replacement: object) -> None:
    document = compile_ready(assembled()).to_private_dict()
    document[field] = replacement
    with pytest.raises(ValueError, match="media constraints"):
        parse_zero_shot_callable_envelope(document)


@pytest.mark.parametrize(
    "field,replacement",
    [
        ("model_loader_operation", "other_loader"),
        ("loader_model_root_argument", "PATH_KEYWORD"),
        ("loader_device_map_argument", "device"),
        ("loader_dtype_argument", "precision"),
        ("loader_attention_argument", "attention_implementation"),
        ("loader_offline_argument", "offline"),
        ("generation_operation", "other_generation"),
        ("generation_text_argument", "prompt"),
        ("generation_language_argument", "language_code"),
        ("generation_reference_audio_argument", "audio"),
        ("generation_reference_text_argument", "reference_text"),
        ("generation_x_vector_argument", "x_vector_mode"),
        ("generation_token_limit_argument", "token_limit"),
        ("reference_audio_reader_operation", "other_reader"),
        ("audio_reader_source_argument", "PATH_OR_URL"),
        ("audio_reader_dtype_argument", "sample_dtype"),
        ("audio_reader_always_2d_argument", "two_dimensional"),
        ("device_map", "cpu"),
        ("dtype", "torch.float32"),
        ("attn_implementation", "flash_attention_2"),
        ("local_files_only", False),
        ("required_tts_model_type", "custom_voice"),
        ("product_language_code", "en-US"),
        ("engine_language", "English"),
        ("required_supported_language", "english"),
        ("reference_audio_transport", "PATH_OR_URL"),
        ("reference_audio_dtype", "int16"),
        ("reference_audio_always_2d", True),
        ("reference_audio_required_ndim", 2),
        ("x_vector_only_mode", True),
        ("max_new_tokens", 4096),
        ("expected_waveform_count", 2),
        ("automatic_retry_allowed", True),
        ("max_attempts", 2),
        ("timeout_seconds", 181),
        ("max_output_duration_seconds", 61),
        ("max_output_bytes", 104_857_601),
        ("checkpoint_sampling_overrides_allowed", True),
        ("runner_platform", "LINUX"),
        ("runner_visibility", "VISIBLE"),
        ("timeout_termination_scope", "PROCESS_TREE"),
        ("dispatch_ambiguity_decision", "RETRY"),
        ("ambiguous_dispatch_retry_allowed", True),
        ("ambiguous_dispatch_replay_allowed", True),
    ],
)
def test_qwen_callable_surface_cannot_be_substituted(field: str, replacement: object) -> None:
    document = compile_ready(assembled()).to_private_dict()
    document[field] = replacement
    with pytest.raises(ValueError, match="Qwen callable surface"):
        parse_zero_shot_callable_envelope(document)


def test_qwen_callable_surface_policy_is_process_immutable() -> None:
    import ai_video_production.task014_zero_shot_callable_contract as module

    with pytest.raises(TypeError):
        module._CALL_SURFACE["timeout_seconds"] = 181


def test_known_blocker_has_precedence_over_unknown_receipt() -> None:
    parts = assembled(profile_exact_model_id="other-model")
    result = compile_ready(parts, subject_binding_receipt=None)
    assert result.decision is CallableEnvelopeDecision.BLOCKED
    assert "ENGINE_BINDING_MISMATCH" in result.reason_codes
    assert "SUBJECT_BINDING_NOT_PROVIDED" in result.reason_codes


@pytest.mark.parametrize(
    "private_value",
    [
        r"C:\private\voice.wav",
        "/private/voice.wav",
        "file://private/voice.wav",
        "credential.fixture",
        "private-key.fixture",
    ],
)
def test_h1_h2_reject_host_paths_and_private_identifiers(private_value: str) -> None:
    parts = assembled()
    with pytest.raises(ValueError, match="invalid|body-free"):
        subject_receipt(parts, capture_lineage_ref=private_value)
    with pytest.raises(ValueError, match="invalid|body-free"):
        plan_receipt(parts, plan_store_ref=private_value)
    with pytest.raises(ValueError, match="invalid|body-free"):
        transcript_receipt(parts, transcript_revision_ref=private_value)


@pytest.mark.parametrize("field", ["transcript_revision_ref", "transcript_evidence_ref"])
@pytest.mark.parametrize("body_like_value", ["hello", "owner-spoken-line", "opaque-handle-123"])
def test_h3_rejects_body_like_or_opaque_values_in_logical_ref_fields(
    field: str, body_like_value: str
) -> None:
    with pytest.raises(ValueError, match="canonical logical record ref"):
        transcript_receipt(assembled(), **{field: body_like_value})


@pytest.mark.parametrize("field", ["transcript_revision_ref", "transcript_evidence_ref"])
@pytest.mark.parametrize(
    "path_like_tail",
    ["/private/voice.wav", "../voice.wav", r"C:\private\voice.wav", "file://voice.wav"],
)
def test_h3_rejects_path_like_payload_after_canonical_ref_prefix(
    field: str, path_like_tail: str
) -> None:
    prefix = (
        "reference.transcript.revision."
        if field == "transcript_revision_ref"
        else "reference.transcript.evidence."
    )
    with pytest.raises(ValueError, match="canonical logical record ref|invalid|body-free"):
        transcript_receipt(assembled(), **{field: prefix + path_like_tail})


def test_parsers_reject_unknown_private_body_fields_and_no_effect_tamper() -> None:
    parts = assembled()
    envelope = compile_ready(parts)
    cases = [
        (subject_receipt(parts).to_private_dict(), parse_zero_shot_reference_subject_binding_receipt, "audio_bytes"),
        (plan_receipt(parts).to_private_dict(), parse_canonical_narration_plan_revision_receipt, "script_text"),
        (transcript_receipt(parts).to_private_dict(), parse_zero_shot_reference_transcript_binding_receipt, "ref_text"),
        (transcript_receipt(parts).to_private_dict(), parse_zero_shot_reference_transcript_binding_receipt, "audio_path"),
        (envelope.to_private_dict(), parse_zero_shot_callable_envelope, "result_ref"),
        (envelope.to_private_dict(), parse_zero_shot_callable_envelope, "replay"),
        (envelope.to_private_dict(), parse_zero_shot_callable_envelope, "qa_decision"),
    ]
    for document, parser, field in cases:
        document[field] = "forbidden"
        with pytest.raises(ValueError, match="incomplete or unknown"):
            parser(document)
    document = envelope.to_private_dict()
    document["dispatch_started"] = True
    with pytest.raises(ValueError, match="no-effect"):
        parse_zero_shot_callable_envelope(document)


def test_callable_module_exposes_no_result_replay_or_qa_api() -> None:
    import ai_video_production.task014_zero_shot_callable_contract as module

    forbidden = {
        "compile_render_result",
        "parse_render_result",
        "accept_result",
        "record_replay",
        "consume_operation",
        "start_qa",
        "publish_asset",
        "dispatch",
        "execute",
        "load_model",
    }
    assert set(module.__all__).isdisjoint(forbidden)
    envelope_fields = set(compile_ready(assembled()).to_private_dict())
    assert envelope_fields.isdisjoint(
        {"result_ref", "output_sha256", "replay", "terminal_job_sha256", "qa_decision"}
    )
