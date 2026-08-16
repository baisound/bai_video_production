from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from ai_video_production.owner_narration_local_primary import (
    ContractState,
    LocalNarrationRouteMode,
    NarrationIntendedUsage,
    PreflightDecision,
    compile_local_primary_preflight,
    parse_local_primary_preflight,
)
from ai_video_production.serialization import sha256_bytes
from ai_video_production.voice_profile_revision import ConsentReference, ConsentState


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SCHEMA = ROOT / "schemas" / "local-primary-narration-preflight.schema.json"
MIRROR_SCHEMA = (
    ROOT
    / "src"
    / "ai_video_production"
    / "schema_resources"
    / "local-primary-narration-preflight.schema.json"
)


def digest(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def consent(*, state: ConsentState = ConsentState.ACTIVE) -> dict[str, object]:
    return ConsentReference(
        consent_subject_ref="owner.subject",
        consent_scope="Local Owner narration",
        allowed_usage_classes=("OWNER_NARRATION_LOCAL",),
        state=state,
        subject_verified=state is not ConsentState.UNKNOWN,
        evidence_id=None if state is ConsentState.UNKNOWN else "consent.evidence.1",
        evidence_sha256=None if state is ConsentState.UNKNOWN else digest("consent evidence"),
    ).to_dict()


def script(*, approved: bool = True) -> dict[str, object]:
    return {
        "text_owner": "TASK-006",
        "approved_text_revision_ref": "script.revision.3",
        "approved_text_revision_sha256": digest("script revision"),
        "source_text_binding_sha256": digest("body-free text binding"),
        "approved": approved,
        "body_persisted": False,
    }


def voice(*, state: str = "BOUND_VERIFIED", consent_state: ConsentState = ConsentState.ACTIVE) -> dict[str, object]:
    if state == "CANONICAL_REF_NOT_PROVIDED":
        return {
            "contract_state": state,
            "voice_profile_id": None,
            "canonical_narration_profile_sha256": None,
            "revision": None,
            "parent_revision_sha256": None,
            "voice_profile_revision_sha256": None,
            "consent": None,
            "current_consent_state": None,
            "current_consent_evaluation_sha256": None,
            "canonical_evidence_ref": None,
            "canonical_evidence_sha256": None,
        }
    return {
        "contract_state": state,
        "voice_profile_id": "voice.profile.owner",
        "canonical_narration_profile_sha256": digest("narration profile"),
        "revision": 1,
        "parent_revision_sha256": None,
        "voice_profile_revision_sha256": digest("voice profile revision"),
        "consent": consent(state=consent_state),
        "current_consent_state": consent_state.value,
        "current_consent_evaluation_sha256": digest("current consent evaluation"),
        "canonical_evidence_ref": "voice.profile.evidence.1",
        "canonical_evidence_sha256": digest("voice profile evidence"),
    }


def engine(*, mode: LocalNarrationRouteMode = LocalNarrationRouteMode.ZERO_SHOT_LOCAL, state: str = "BOUND_VERIFIED", license_state: str = "COMMERCIAL_ALLOWED", capability: str = "VERIFIED") -> dict[str, object]:
    if state == "CANONICAL_REF_NOT_PROVIDED":
        return {
            "contract_state": state,
            "route_mode": None,
            "engine_id": None,
            "engine_revision_sha256": None,
            "model_artifact_id": None,
            "model_artifact_sha256": None,
            "runtime_id": None,
            "runtime_sha256": None,
            "code_revision_sha256": None,
            "license_state": None,
            "license_evidence_ref": None,
            "license_evidence_sha256": None,
            "capability_probe_state": None,
            "capability_probe_ref": None,
            "capability_probe_sha256": None,
        }
    return {
        "contract_state": state,
        "route_mode": mode.value,
        "engine_id": "local.tts.engine",
        "engine_revision_sha256": digest("engine revision"),
        "model_artifact_id": "model.artifact.local",
        "model_artifact_sha256": digest("model artifact"),
        "runtime_id": "runtime.local",
        "runtime_sha256": digest("runtime"),
        "code_revision_sha256": digest("code revision"),
        "license_state": license_state,
        "license_evidence_ref": "license.evidence.1",
        "license_evidence_sha256": digest("license evidence"),
        "capability_probe_state": capability,
        "capability_probe_ref": "capability.probe.1",
        "capability_probe_sha256": digest("capability probe"),
    }


def resource(mode: LocalNarrationRouteMode, *, state: str = "BOUND_VERIFIED", result: str = "PASS") -> dict[str, object]:
    if state == "CANONICAL_REF_NOT_PROVIDED":
        return {
            "contract_state": state,
            "route_mode": None,
            "resource_profile_ref": None,
            "resource_profile_sha256": None,
            "result": None,
            "evidence_ref": None,
            "evidence_sha256": None,
        }
    return {
        "contract_state": state,
        "route_mode": mode.value,
        "resource_profile_ref": "resource.profile.1",
        "resource_profile_sha256": digest("resource profile"),
        "result": result,
        "evidence_ref": "resource.evidence.1",
        "evidence_sha256": digest("resource evidence"),
    }


def rights(*, usage: NarrationIntendedUsage = NarrationIntendedUsage.PREVIEW, state: str = "PASS") -> dict[str, object]:
    return {
        "contract_state": "BOUND_VERIFIED",
        "usage_class": "LOCAL_NARRATION_PREVIEW" if usage is NarrationIntendedUsage.PREVIEW else "LOCAL_NARRATION_FULL_RENDER",
        "state": state,
        "evidence_ref": "rights.evidence.1",
        "evidence_sha256": digest("rights evidence"),
        "evaluated_at": "2026-08-16T05:00:00Z",
    }


def zero_shot(*, state: str = "BOUND_VERIFIED") -> dict[str, object]:
    fields: dict[str, object] = {
        "contract_state": state,
        "asset_id": "asset.owner.reference",
        "asset_checksum_sha256": digest("reference bytes"),
        "asset_revision_binding_ref": "asset.revision.binding.1",
        "asset_revision_binding_sha256": digest("asset revision binding"),
        "reference_profile_ref": "reference.profile.1",
        "reference_profile_sha256": digest("reference profile"),
        "consent_current_evaluation_sha256": digest("reference consent current"),
        "rights_current_evaluation_sha256": digest("reference rights current"),
        "audio_body_persisted": False,
    }
    if state == "CANONICAL_REF_NOT_PROVIDED":
        for key in set(fields) - {"contract_state", "audio_body_persisted"}:
            fields[key] = None
    return fields


def fine_tuned(*, state: str = "BOUND_VERIFIED") -> dict[str, object]:
    fields: dict[str, object] = {
        "contract_state": state,
        "dataset_revision_id": "voice.dataset.revision.2",
        "dataset_revision_sha256": digest("dataset revision"),
        "training_input_snapshot_id": "training.input.snapshot.1",
        "training_input_snapshot_sha256": digest("training input"),
        "model_candidate_revision_id": "model.candidate.revision.1",
        "model_candidate_revision_sha256": digest("model candidate"),
        "model_artifact_binding_ref": "model.artifact.binding.1",
        "model_artifact_binding_sha256": digest("model artifact binding"),
        "owner_model_approval_decision_ref": "owner.model.approval.1",
        "owner_model_approval_decision_sha256": digest("owner model approval"),
        "consent_current_evaluation_sha256": digest("model consent current"),
        "rights_current_evaluation_sha256": digest("model rights current"),
        "dataset_body_persisted": False,
        "model_bytes_persisted": False,
    }
    if state == "CANONICAL_REF_NOT_PROVIDED":
        for key in set(fields) - {"contract_state", "dataset_body_persisted", "model_bytes_persisted"}:
            fields[key] = None
    return fields


def compile_zero(**overrides: object):
    values: dict[str, object] = {
        "project_id": "project.alpha",
        "preflight_id": "preflight.zero.1",
        "created_at": "2026-08-16T05:00:00Z",
        "route_mode": LocalNarrationRouteMode.ZERO_SHOT_LOCAL,
        "intended_usage": NarrationIntendedUsage.PREVIEW,
        "script_text_binding": script(),
        "voice_profile_revision_binding": voice(),
        "engine_admission_binding": engine(),
        "resource_feasibility_binding": resource(LocalNarrationRouteMode.ZERO_SHOT_LOCAL),
        "rights_evaluation_binding": rights(),
        "zero_shot_reference_binding": zero_shot(),
        "fine_tuned_model_binding": None,
    }
    values.update(overrides)
    return compile_local_primary_preflight(**values)


def test_zero_shot_ready_is_body_free_and_non_executing() -> None:
    output = compile_zero().to_private_dict()
    assert output["decision"] == PreflightDecision.READY_FOR_OWNER_HUMAN_GATE.value
    for field in (
        "script_body_persisted", "audio_body_persisted", "credential_value_persisted",
        "absolute_path_persisted", "execution_started", "model_loaded", "gpu_reserved",
        "asset_published",
    ):
        assert output[field] is False


def test_fine_tuned_route_requires_exact_dataset_model_lineage() -> None:
    result = compile_local_primary_preflight(
        project_id="project.alpha",
        preflight_id="preflight.fine.1",
        created_at="2026-08-16T05:00:00Z",
        route_mode=LocalNarrationRouteMode.FINE_TUNED_LOCAL,
        intended_usage=NarrationIntendedUsage.PREVIEW,
        script_text_binding=script(),
        voice_profile_revision_binding=voice(),
        engine_admission_binding=engine(mode=LocalNarrationRouteMode.FINE_TUNED_LOCAL),
        resource_feasibility_binding=resource(LocalNarrationRouteMode.FINE_TUNED_LOCAL),
        rights_evaluation_binding=rights(),
        zero_shot_reference_binding=None,
        fine_tuned_model_binding=fine_tuned(),
    )
    assert result.decision is PreflightDecision.READY_FOR_OWNER_HUMAN_GATE


def test_mode_cannot_reuse_the_other_dependency_contract() -> None:
    with pytest.raises(ValueError, match="requires only"):
        compile_zero(zero_shot_reference_binding=None, fine_tuned_model_binding=fine_tuned())


def test_unresolved_route_is_unknown_not_ready() -> None:
    result = compile_zero(zero_shot_reference_binding=zero_shot(state="CANONICAL_REF_NOT_PROVIDED"))
    assert result.decision is PreflightDecision.UNKNOWN
    assert "ZERO_SHOT_REFERENCE_CANONICAL_REF_NOT_PROVIDED" in result.reason_codes


def test_unresolved_binding_cannot_invent_canonical_identity() -> None:
    binding = zero_shot(state="CANONICAL_REF_NOT_PROVIDED")
    binding["asset_id"] = "invented.asset"
    with pytest.raises(ValueError, match="must not invent"):
        compile_zero(zero_shot_reference_binding=binding)


def test_mismatch_is_blocked() -> None:
    result = compile_zero(engine_admission_binding=engine(state="MISMATCH"))
    assert result.decision is PreflightDecision.BLOCKED
    assert "ENGINE_MISMATCH" in result.reason_codes


def test_revoked_current_consent_is_blocked() -> None:
    result = compile_zero(voice_profile_revision_binding=voice(consent_state=ConsentState.REVOKED))
    assert result.decision is PreflightDecision.BLOCKED
    assert "CONSENT_REVOKED_OR_INACTIVE" in result.reason_codes


def test_unapproved_text_is_blocked() -> None:
    result = compile_zero(script_text_binding=script(approved=False))
    assert result.decision is PreflightDecision.BLOCKED
    assert "SCRIPT_TEXT_NOT_APPROVED" in result.reason_codes


@pytest.mark.parametrize("license_state", ["LEGAL_REVIEW_REQUIRED", "UNKNOWN"])
def test_undecided_engine_license_is_unknown(license_state: str) -> None:
    assert compile_zero(engine_admission_binding=engine(license_state=license_state)).decision is PreflightDecision.UNKNOWN


@pytest.mark.parametrize("license_state", ["NONCOMMERCIAL_ONLY", "RESTRICTED", "REVOKED"])
def test_non_admitted_engine_license_is_blocked(license_state: str) -> None:
    assert compile_zero(engine_admission_binding=engine(license_state=license_state)).decision is PreflightDecision.BLOCKED


def test_failed_capability_probe_is_blocked() -> None:
    assert compile_zero(engine_admission_binding=engine(capability="FAILED")).decision is PreflightDecision.BLOCKED


def test_unknown_resource_is_unknown_not_pass() -> None:
    binding = resource(LocalNarrationRouteMode.ZERO_SHOT_LOCAL, result="UNKNOWN")
    assert compile_zero(resource_feasibility_binding=binding).decision is PreflightDecision.UNKNOWN


def test_failed_resource_is_blocked() -> None:
    binding = resource(LocalNarrationRouteMode.ZERO_SHOT_LOCAL, result="FAIL")
    assert compile_zero(resource_feasibility_binding=binding).decision is PreflightDecision.BLOCKED


def test_resource_mode_cannot_be_reused() -> None:
    with pytest.raises(ValueError, match="route_mode mismatch"):
        compile_zero(resource_feasibility_binding=resource(LocalNarrationRouteMode.FINE_TUNED_LOCAL))


def test_engine_mode_cannot_be_reused() -> None:
    with pytest.raises(ValueError, match="engine route_mode mismatch"):
        compile_zero(engine_admission_binding=engine(mode=LocalNarrationRouteMode.FINE_TUNED_LOCAL))


def test_rights_usage_must_match_intended_usage() -> None:
    with pytest.raises(ValueError, match="usage_class mismatch"):
        compile_zero(rights_evaluation_binding=rights(usage=NarrationIntendedUsage.FULL_RENDER))


def test_public_projection_redacts_text_audio_and_private_evidence() -> None:
    public = compile_zero().to_public_dict()
    encoded = json.dumps(public, sort_keys=True)
    for secret in (
        "source_text_binding_sha256", "asset_checksum_sha256", "consent.evidence.1",
        "model.artifact.local", "resource.evidence.1",
    ):
        assert secret not in encoded
    assert public["text_digest_persisted"] is False
    assert public["audio_hash_persisted"] is False


def test_private_payload_round_trip_and_hash_are_deterministic() -> None:
    first = compile_zero().to_private_dict()
    second = compile_zero().to_private_dict()
    assert first == second
    assert parse_local_primary_preflight(first).to_private_dict() == first


def test_parser_rejects_classification_tamper() -> None:
    value = compile_zero().to_private_dict()
    value["decision"] = "BLOCKED"
    with pytest.raises(ValueError, match="classification mismatch"):
        parse_local_primary_preflight(value)


def test_parser_rejects_hash_tamper() -> None:
    value = compile_zero().to_private_dict()
    value["preflight_sha256"] = digest("tampered")
    with pytest.raises(ValueError, match="checksum mismatch"):
        parse_local_primary_preflight(value)


def test_raw_execution_authorized_boolean_is_rejected() -> None:
    value = compile_zero().to_private_dict()
    value["execution_authorized"] = True
    with pytest.raises(ValueError, match="unknown"):
        parse_local_primary_preflight(value)


def test_schema_validates_canonical_payload() -> None:
    schema_value = json.loads(PUBLIC_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema_value)
    Draft202012Validator(schema_value).validate(compile_zero().to_private_dict())


def test_schema_rejects_effect_authority_or_audio_body() -> None:
    schema_value = json.loads(PUBLIC_SCHEMA.read_text(encoding="utf-8"))
    payload = compile_zero().to_private_dict()
    payload["audio_body_persisted"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(schema_value).validate(payload)
    payload = compile_zero().to_private_dict()
    payload["execution_authorized"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(schema_value).validate(payload)


def test_schema_mode_exclusivity_is_fail_closed() -> None:
    schema_value = json.loads(PUBLIC_SCHEMA.read_text(encoding="utf-8"))
    payload = compile_zero().to_private_dict()
    payload["fine_tuned_model_binding"] = fine_tuned()
    with pytest.raises(ValidationError):
        Draft202012Validator(schema_value).validate(payload)


def test_schema_mirror_is_byte_exact() -> None:
    assert PUBLIC_SCHEMA.read_bytes() == MIRROR_SCHEMA.read_bytes()


def test_no_runtime_or_effect_api_is_exposed() -> None:
    import ai_video_production.owner_narration_local_primary as module

    names = set(dir(module))
    forbidden = {"render", "synthesize", "load_model", "reserve_gpu", "publish", "dispatch", "execute"}
    assert names.isdisjoint(forbidden)
