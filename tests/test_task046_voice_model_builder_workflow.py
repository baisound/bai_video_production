from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.voice_model_builder_workflow import (
    CanonicalSourceBinding,
    ExternalOperationRequest,
    MasterAssemblyPolicyBinding,
    MasterWavCandidateRevision,
    StyleCueRevision,
    VerticalSliceWorkflowRevision,
    add_record_digest,
    assert_no_effect_surface,
    beginner_projection,
    compile_operation_request,
    validate_record,
    validate_workflow_transition,
)


NOW = "2026-08-17T02:00:00Z"
H = "sha256:" + "a" * 64
H2 = "sha256:" + "b" * 64
H3 = "sha256:" + "c" * 64
H4 = "sha256:" + "d" * 64
ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "voice-model-builder-workflow.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / "voice-model-builder-workflow.schema.json"


def bound_source(kind: str) -> dict:
    return add_record_digest(
        {
            "record_type": "CanonicalSourceBinding",
            "contract_state": "BOUND_VERIFIED",
            "source_kind": kind,
            "canonical_ref": f"canonical:{kind.lower()}",
            "canonical_revision": 1,
            "canonical_sha256": H,
            "current_valid": True,
            "evaluated_at": NOW,
        },
        "binding_sha256",
    )


def workflow(*, revision: int = 1, parent: str | None = None, state: str = "RECORDINGS_REVIEW_REQUIRED", cues: list[str] | None = None, master: str | None = None) -> dict:
    return add_record_digest(
        {
            "record_type": "VerticalSliceWorkflowRevision",
            "workflow_id": "workflow:owner-voice-r0",
            "revision": revision,
            "parent_workflow_sha256": parent,
            "project_id": "project:owner-narration",
            "source_bindings": [bound_source("OBS_CAPTURE_SESSION")],
            "state": state,
            "ordered_cue_sha256": cues or [],
            "master_candidate_sha256": master,
            "reason_codes": [],
            "created_at": NOW,
            "dataset_effect_started": False,
            "training_started": False,
            "render_started": False,
        },
        "workflow_sha256",
    )


def cue(index: int, *, state: str = "PENDING", model: str = H2, profile: str = H3) -> dict:
    receipt = "receipt:cue" if state == "RENDERED_BOUND" else None
    artifact = "artifact:cue" if state == "RENDERED_BOUND" else None
    return add_record_digest(
        {
            "record_type": "StyleCueRevision",
            "cue_id": f"cue:{index}",
            "revision": 1,
            "parent_cue_sha256": None,
            "workflow_id": "workflow:owner-voice-r0",
            "order_index": index,
            "script_revision_sha256": H,
            "text_start": index * 10,
            "text_end": index * 10 + 10,
            "style_direction_sha256": H4,
            "model_candidate_sha256": model,
            "voice_profile_revision_sha256": profile,
            "render_admission_sha256": H,
            "state": state,
            "external_render_receipt_ref": receipt,
            "external_render_receipt_sha256": H if receipt else None,
            "cue_artifact_ref": artifact,
            "cue_artifact_sha256": H2 if artifact else None,
            "audio_body_persisted": False,
            "created_at": NOW,
        },
        "cue_sha256",
    )


def policy(*, state: str = "BOUND_VERIFIED") -> dict:
    digest = H if state == "BOUND_VERIFIED" else None
    return add_record_digest(
        {
            "record_type": "MasterAssemblyPolicyBinding",
            "contract_state": state,
            "sample_rate_hz": 48000,
            "channels": 1,
            "sample_format": "PCM_S24LE",
            "pause_policy_sha256": digest,
            "loudness_policy_state": state,
            "loudness_policy_sha256": digest,
            "boundary_policy_state": state,
            "boundary_policy_sha256": digest,
            "identity_policy_state": state,
            "identity_policy_sha256": digest,
            "max_crossfade_samples": 2400,
        },
        "policy_sha256",
    )


def master(*, accepted: bool = False) -> dict:
    bound = "ACCEPTED" if accepted else "PENDING"
    fact = "PASS" if accepted else "UNKNOWN"
    return add_record_digest(
        {
            "record_type": "MasterWavCandidateRevision",
            "master_id": "master:1",
            "revision": 1,
            "parent_master_sha256": None,
            "workflow_id": "workflow:owner-voice-r0",
            "ordered_cue_sha256": [H, H2],
            "model_candidate_sha256": H3,
            "voice_profile_revision_sha256": H4,
            "assembly_policy_sha256": H,
            "external_assembly_receipt_ref": "receipt:assembly" if accepted else None,
            "external_assembly_receipt_sha256": H if accepted else None,
            "master_artifact_ref": "artifact:master" if accepted else None,
            "master_artifact_sha256": H2 if accepted else None,
            "format_state": fact,
            "boundary_state": fact,
            "loudness_state": fact,
            "identity_continuity_state": fact,
            "style_state": fact,
            "owner_acceptance": bound,
            "audio_body_persisted": False,
            "asset_adoption_started": False,
            "publication_started": False,
            "created_at": NOW,
        },
        "master_sha256",
    )


@pytest.mark.parametrize(
    ("record", "cls"),
    [
        (bound_source("OBS_CAPTURE_SESSION"), CanonicalSourceBinding),
        (cue(0), StyleCueRevision),
        (policy(), MasterAssemblyPolicyBinding),
        (master(), MasterWavCandidateRevision),
        (workflow(), VerticalSliceWorkflowRevision),
    ],
)
def test_canonical_records_match_public_schema(record: dict, cls: type) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(record)
    assert cls(record).to_dict() == record


def test_schema_mirror_is_byte_exact() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()


def test_unresolved_source_cannot_invent_canonical_truth() -> None:
    record = bound_source("QUALITY_EVALUATION")
    record.update(contract_state="UNKNOWN", current_valid=None)
    record = add_record_digest(record, "binding_sha256")
    with pytest.raises(ValueError, match="must not invent"):
        validate_record(record)


def test_source_rejects_absolute_or_private_identity() -> None:
    for ref in ("C:/owner/audio.wav", "credential:owner"):
        record = bound_source("OBS_CAPTURE_SESSION")
        record["canonical_ref"] = ref
        record = add_record_digest(record, "binding_sha256")
        with pytest.raises(ValueError):
            validate_record(record)


def test_cue_is_body_free_and_unrendered_cannot_claim_artifact() -> None:
    record = cue(0)
    record["cue_artifact_ref"] = "artifact:fake"
    record = add_record_digest(record, "cue_sha256")
    with pytest.raises(ValueError, match="cannot claim"):
        validate_record(record)
    body = cue(0)
    body["audio_body_persisted"] = True
    body = add_record_digest(body, "cue_sha256")
    with pytest.raises(ValueError, match="cannot persist"):
        validate_record(body)


def test_master_requires_multiple_unique_ordered_cues() -> None:
    for cues in ([H], [H, H]):
        record = master()
        record["ordered_cue_sha256"] = cues
        record = add_record_digest(record, "master_sha256")
        with pytest.raises(ValueError, match="two unique"):
            validate_record(record)


def test_master_format_is_exact_48k_24bit_mono() -> None:
    record = policy()
    record["sample_rate_hz"] = 44100
    record = add_record_digest(record, "policy_sha256")
    with pytest.raises(ValueError, match="48 kHz"):
        validate_record(record)


def test_unhosted_policy_is_unknown_not_pass() -> None:
    assert MasterAssemblyPolicyBinding(policy(state="UNKNOWN"))


def test_owner_acceptance_requires_all_qa_and_bound_master() -> None:
    assert MasterWavCandidateRevision(master(accepted=True))
    record = master(accepted=True)
    record["boundary_state"] = "UNKNOWN"
    record = add_record_digest(record, "master_sha256")
    with pytest.raises(ValueError, match="all QA PASS"):
        validate_record(record)


def test_workflow_rejects_duplicate_source_owner() -> None:
    record = workflow()
    record["source_bindings"].append(bound_source("OBS_CAPTURE_SESSION"))
    record = add_record_digest(record, "workflow_sha256")
    with pytest.raises(ValueError, match="source_kind"):
        validate_record(record)


def test_workflow_cas_transition_is_append_only() -> None:
    old = workflow()
    new = workflow(revision=2, parent=old["workflow_sha256"], state="DATASET_PROPOSAL_READY")
    validate_workflow_transition(old, new)
    bad = copy.deepcopy(new)
    bad["parent_workflow_sha256"] = H
    bad = add_record_digest(bad, "workflow_sha256")
    with pytest.raises(ValueError, match="CAS"):
        validate_workflow_transition(old, bad)


def test_operation_request_is_proposal_only_and_never_dispatches() -> None:
    request = compile_operation_request(
        request_id="request:1",
        operation_kind="TRAINING_DISPATCH",
        workflow=workflow(),
        subject_sha256=H2,
        authorization_binding_sha256=H3,
        idempotency_key="idem:training:1",
        created_at=NOW,
    )
    assert isinstance(request, ExternalOperationRequest)
    assert request.to_dict()["dispatch_started"] is False
    forged = request.to_dict()
    forged["dispatch_started"] = True
    forged = add_record_digest(forged, "request_sha256")
    with pytest.raises(ValueError, match="undispatched"):
        validate_record(forged)


def test_beginner_projection_does_not_leak_source_coordinates() -> None:
    projected = beginner_projection(workflow())
    encoded = json.dumps(projected, sort_keys=True)
    assert "canonical_ref" not in encoded
    assert projected["friendly_ja"] == "録音を確認してください"
    assert projected["effect_authorized"] is False


def test_unknown_fields_and_digest_tamper_fail_closed() -> None:
    extra = workflow()
    extra["raw_audio_path"] = "owner.wav"
    with pytest.raises(ValueError, match="fields"):
        validate_record(extra)
    tampered = workflow()
    tampered["state"] = "MASTER_ACCEPTED"
    with pytest.raises(ValueError, match="mismatch"):
        validate_record(tampered)


def test_no_effect_surface() -> None:
    assert_no_effect_surface()
