from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.owner_narration_local_primary import (
    LocalNarrationRouteMode,
    NarrationIntendedUsage,
)
from ai_video_production.owner_narration_local_render_admission import (
    AuthorityKind,
    ContractState,
    DurableJobState,
    DurableNarrationJobBinding,
    ExecutionAuthorizationBinding,
    LocalPrimaryPreflightBinding,
    OutputStagingDestinationBinding,
    PreflightDecision,
    RenderAdmissionDecision,
    RenderAuthorizationScope,
    ResourceAdmissionBinding,
    ResourceGateDecision,
    canonical_render_admission_json,
    compile_render_admission,
    parse_render_admission,
    render_operation_identity_sha256,
)
from ai_video_production.serialization import sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
SHA_A = sha256_bytes(b"a")
SHA_B = sha256_bytes(b"b")
SHA_C = sha256_bytes(b"c")
SHA_D = sha256_bytes(b"d")
SHA_E = sha256_bytes(b"e")
SHA_F = sha256_bytes(b"f")
SHA_G = sha256_bytes(b"g")
SHA_H = sha256_bytes(b"h")
SHA_I = sha256_bytes(b"i")
SHA_J = sha256_bytes(b"j")
CREATED = "2026-08-17T10:00:00Z"


def preflight(
    *,
    state: ContractState = ContractState.BOUND_VERIFIED,
    route: LocalNarrationRouteMode = LocalNarrationRouteMode.ZERO_SHOT_LOCAL,
    usage: NarrationIntendedUsage = NarrationIntendedUsage.PREVIEW,
    decision: PreflightDecision = PreflightDecision.READY_FOR_OWNER_HUMAN_GATE,
    script_sha: str = SHA_J,
    voice_sha: str = SHA_C,
    expires: str = "2026-08-17T10:05:00Z",
) -> LocalPrimaryPreflightBinding:
    if state is not ContractState.BOUND_VERIFIED:
        return LocalPrimaryPreflightBinding(state, None, None, None, None, None, None, None, None, None)
    return LocalPrimaryPreflightBinding(state, "preflight.local.1", SHA_A, route, usage, script_sha, voice_sha, decision, "2026-08-17T09:55:00Z", expires)


def resource(
    *,
    state: ContractState = ContractState.BOUND_VERIFIED,
    decision: ResourceGateDecision = ResourceGateDecision.ADMITTED,
    expires: str = "2026-08-17T10:05:00Z",
    route: LocalNarrationRouteMode = LocalNarrationRouteMode.ZERO_SHOT_LOCAL,
) -> ResourceAdmissionBinding:
    if state is not ContractState.BOUND_VERIFIED:
        return ResourceAdmissionBinding(state, None, None, None, None, None, None, None, None)
    return ResourceAdmissionBinding(state, "resource.gate.1", SHA_B, "LOCAL_NARRATION_RENDER", route, SHA_A, decision, "2026-08-17T09:59:00Z", expires)


def job(
    *,
    state: ContractState = ContractState.BOUND_VERIFIED,
    job_state: DurableJobState = DurableJobState.REGISTERED,
    operation_identity_sha256: str | None = None,
) -> DurableNarrationJobBinding:
    if state is not ContractState.BOUND_VERIFIED:
        return DurableNarrationJobBinding(state, None, None, None, None, None, None)
    operation_identity_sha256 = operation_identity_sha256 or render_operation_identity_sha256(
        project_id="project.alpha",
        admission_id="admission.render.1",
        admission_revision=1,
        route_mode=LocalNarrationRouteMode.ZERO_SHOT_LOCAL,
        intended_usage=NarrationIntendedUsage.PREVIEW,
        script_text_revision_sha256=SHA_J,
        voice_profile_revision_sha256=SHA_C,
        preflight_sha256=SHA_A,
        destination_policy_sha256=SHA_F,
    )
    return DurableNarrationJobBinding(state, "job.narration.1", 1, SHA_C, operation_identity_sha256, SHA_E, job_state)


def destination(*, state: ContractState = ContractState.BOUND_VERIFIED) -> OutputStagingDestinationBinding:
    if state is not ContractState.BOUND_VERIFIED:
        return OutputStagingDestinationBinding(state, None, None, None, None, None, None, None, None)
    return OutputStagingDestinationBinding(
        state,
        "destination.narration.staging.1",
        "storage.owner.task043",
        SHA_F,
        SHA_G,
        SHA_H,
        SHA_I,
        "STAGED_NARRATION_PCM_WAV_48000_MONO",
        False,
    )


def authorization(
    *,
    state: ContractState = ContractState.BOUND_VERIFIED,
    route: LocalNarrationRouteMode = LocalNarrationRouteMode.ZERO_SHOT_LOCAL,
    usage: NarrationIntendedUsage = NarrationIntendedUsage.PREVIEW,
    script_sha: str = SHA_J,
    expires: str = "2026-08-17T10:05:00Z",
) -> ExecutionAuthorizationBinding:
    if state is not ContractState.BOUND_VERIFIED:
        return ExecutionAuthorizationBinding(
            state, None, None, None, None, None, None, None, None, None,
            None, None, None, None, None, None, None, None, None, None, None, None,
        )
    scope = RenderAuthorizationScope.PREVIEW_RENDER if usage is NarrationIntendedUsage.PREVIEW else RenderAuthorizationScope.FULL_RENDER
    return ExecutionAuthorizationBinding(
        state,
        "authorization.owner.render.1",
        1,
        SHA_A,
        AuthorityKind.OWNER_HUMAN_GATE,
        "project.alpha",
        "admission.render.1",
        1,
        route,
        usage,
        script_sha,
        SHA_C,
        SHA_A,
        SHA_B,
        SHA_C,
        SHA_F,
        scope,
        "2026-08-17T09:59:30Z",
        expires,
        True,
        "evidence.owner.gate.1",
        SHA_J,
    )


def compile_ready(**overrides: object):
    values: dict[str, object] = {
        "project_id": "project.alpha",
        "admission_id": "admission.render.1",
        "revision": 1,
        "parent_revision_sha256": None,
        "created_at": CREATED,
        "route_mode": LocalNarrationRouteMode.ZERO_SHOT_LOCAL,
        "intended_usage": NarrationIntendedUsage.PREVIEW,
        "script_text_revision_id": "script.revision.1",
        "script_text_revision_sha256": SHA_J,
        "voice_profile_revision_id": "voice.profile.revision.1",
        "voice_profile_revision_sha256": SHA_C,
        "preflight_binding": preflight(),
        "resource_admission_binding": resource(),
        "durable_job_binding": job(),
        "output_destination_binding": destination(),
        "execution_authorization_binding": authorization(),
    }
    values.update(overrides)
    return compile_render_admission(**values)


def test_ready_preview_is_body_free_and_non_executing() -> None:
    result = compile_ready()
    assert result.decision is RenderAdmissionDecision.READY_FOR_EXTERNAL_DISPATCH_GATE
    assert result.reason_codes == ()
    private = result.to_private_dict()
    for key in (
        "script_body_persisted", "audio_body_persisted", "credential_value_persisted",
        "absolute_path_persisted", "execution_started", "job_dispatched", "model_loaded",
        "gpu_reserved", "audio_rendered", "asset_published",
    ):
        assert private[key] is False


def test_full_render_requires_full_render_scope() -> None:
    route = LocalNarrationRouteMode.FINE_TUNED_LOCAL
    usage = NarrationIntendedUsage.FULL_RENDER
    result = compile_ready(
        route_mode=route,
        intended_usage=usage,
        preflight_binding=preflight(route=route, usage=usage),
        resource_admission_binding=resource(route=route),
        durable_job_binding=job(operation_identity_sha256=render_operation_identity_sha256(
            project_id="project.alpha", admission_id="admission.render.1", admission_revision=1,
            route_mode=route, intended_usage=usage, script_text_revision_sha256=SHA_J,
            voice_profile_revision_sha256=SHA_C, preflight_sha256=SHA_A,
            destination_policy_sha256=SHA_F,
        )),
        execution_authorization_binding=authorization(route=route, usage=usage),
    )
    assert result.decision is RenderAdmissionDecision.READY_FOR_EXTERNAL_DISPATCH_GATE


@pytest.mark.parametrize("binding_name,binding", [
    ("preflight_binding", preflight(state=ContractState.CANONICAL_REF_NOT_PROVIDED)),
    ("resource_admission_binding", resource(state=ContractState.UNKNOWN)),
    ("durable_job_binding", job(state=ContractState.CANONICAL_REF_NOT_PROVIDED)),
    ("output_destination_binding", destination(state=ContractState.UNKNOWN)),
    ("execution_authorization_binding", authorization(state=ContractState.CANONICAL_REF_NOT_PROVIDED)),
])
def test_unresolved_binding_is_unknown(binding_name: str, binding: object) -> None:
    result = compile_ready(**{binding_name: binding})
    assert result.decision is RenderAdmissionDecision.UNKNOWN
    assert result.reason_codes == ("BINDING_UNRESOLVED",)


def test_mismatch_binding_is_blocked() -> None:
    result = compile_ready(resource_admission_binding=resource(state=ContractState.MISMATCH))
    assert result.decision is RenderAdmissionDecision.BLOCKED
    assert result.reason_codes == ("BINDING_MISMATCH",)


def test_preflight_scope_cannot_cross_route_or_usage() -> None:
    result = compile_ready(preflight_binding=preflight(route=LocalNarrationRouteMode.FINE_TUNED_LOCAL))
    assert "PREFLIGHT_SCOPE_MISMATCH" in result.reason_codes


def test_preflight_cannot_cross_script_voice_or_expiry() -> None:
    wrong_script = compile_ready(preflight_binding=preflight(script_sha=SHA_A))
    wrong_voice = compile_ready(preflight_binding=preflight(voice_sha=SHA_A))
    expired = compile_ready(preflight_binding=preflight(expires=CREATED))
    assert "PREFLIGHT_SCOPE_MISMATCH" in wrong_script.reason_codes
    assert "PREFLIGHT_SCOPE_MISMATCH" in wrong_voice.reason_codes
    assert "PREFLIGHT_EXPIRED" in expired.reason_codes


def test_preflight_blocked_cannot_promote() -> None:
    result = compile_ready(preflight_binding=preflight(decision=PreflightDecision.BLOCKED))
    assert "PREFLIGHT_NOT_READY" in result.reason_codes


def test_resource_denied_or_expired_is_blocked() -> None:
    denied = compile_ready(resource_admission_binding=resource(decision=ResourceGateDecision.DENIED))
    expired = compile_ready(resource_admission_binding=resource(expires=CREATED))
    assert "RESOURCE_NOT_ADMITTED" in denied.reason_codes
    assert "RESOURCE_RECEIPT_EXPIRED" in expired.reason_codes


def test_resource_route_and_preflight_are_exact() -> None:
    result = compile_ready(resource_admission_binding=resource(route=LocalNarrationRouteMode.FINE_TUNED_LOCAL))
    assert "RESOURCE_NOT_ADMITTED" in result.reason_codes


def test_job_must_be_registered_before_dispatch() -> None:
    result = compile_ready(durable_job_binding=job(job_state=DurableJobState.QUEUED))
    assert result.reason_codes == ("DURABLE_JOB_NOT_REGISTERED",)


def test_job_operation_identity_cannot_be_reused() -> None:
    result = compile_ready(durable_job_binding=job(operation_identity_sha256=SHA_D))
    assert "DURABLE_JOB_IDENTITY_MISMATCH" in result.reason_codes


def test_authorization_is_exact_and_fresh() -> None:
    wrong = compile_ready(execution_authorization_binding=authorization(script_sha=SHA_A))
    expired = compile_ready(execution_authorization_binding=authorization(expires=CREATED))
    assert "AUTHORIZATION_SCOPE_MISMATCH" in wrong.reason_codes
    assert "AUTHORIZATION_EXPIRED" in expired.reason_codes


def test_destination_is_private_exact_format() -> None:
    with pytest.raises(ValueError, match="private 48 kHz"):
        OutputStagingDestinationBinding(
            ContractState.BOUND_VERIFIED, "destination.1", "owner.1", SHA_A, SHA_B,
            SHA_C, SHA_D, "STAGED_NARRATION_PCM_WAV_48000_MONO", True,
        )


def test_unresolved_binding_cannot_invent_canonical_fields() -> None:
    with pytest.raises(ValueError, match="must not invent"):
        LocalPrimaryPreflightBinding(
            ContractState.UNKNOWN, "fake", None, None, None, None, None, None, None, None,
        )


def test_revision_parent_rules_are_append_only() -> None:
    with pytest.raises(ValueError, match="revision 1"):
        compile_ready(parent_revision_sha256=SHA_A)
    with pytest.raises(ValueError, match="requires parent"):
        compile_ready(revision=2)


def test_round_trip_is_deterministic_and_tamper_evident() -> None:
    result = compile_ready()
    payload = result.to_private_dict()
    assert parse_render_admission(payload) == result
    assert canonical_render_admission_json(result) == canonical_render_admission_json(compile_ready())
    changed = copy.deepcopy(payload)
    changed["script_text_revision_sha256"] = SHA_A
    with pytest.raises(ValueError, match="classification mismatch|checksum mismatch"):
        parse_render_admission(changed)


def test_classification_and_effect_flag_tamper_are_rejected() -> None:
    payload = compile_ready().to_private_dict()
    payload["decision"] = "BLOCKED"
    with pytest.raises(ValueError, match="classification mismatch"):
        parse_render_admission(payload)
    payload = compile_ready().to_private_dict()
    payload["audio_rendered"] = True
    with pytest.raises(ValueError, match="must remain false"):
        parse_render_admission(payload)


def test_unknown_property_and_raw_authorization_boolean_are_rejected() -> None:
    payload = compile_ready().to_private_dict()
    payload["execution_authorized"] = True
    with pytest.raises(ValueError, match="fields are incomplete or unknown"):
        parse_render_admission(payload)


def test_public_projection_redacts_private_coordinates() -> None:
    public = compile_ready().to_public_dict()
    text = json.dumps(public, sort_keys=True)
    for secret in ("project.alpha", SHA_A, SHA_B, SHA_C, SHA_F, SHA_J, "script.revision.1"):
        assert secret not in text
    assert public["private_binding_count"] == 5


def test_schema_validates_runtime_payload_and_rejects_effect() -> None:
    schema = json.loads((ROOT / "schemas/local-primary-narration-render-admission.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    payload = compile_ready().to_private_dict()
    validator.validate(payload)
    payload["job_dispatched"] = True
    assert list(validator.iter_errors(payload))


def test_schema_mirror_is_byte_exact() -> None:
    public = ROOT / "schemas/local-primary-narration-render-admission.schema.json"
    mirror = ROOT / "src/ai_video_production/schema_resources/local-primary-narration-render-admission.schema.json"
    assert public.read_bytes() == mirror.read_bytes()


def test_no_runtime_or_effect_api_is_exposed() -> None:
    import ai_video_production.owner_narration_local_render_admission as module

    public_names = {name.casefold() for name in dir(module) if not name.startswith("_")}
    forbidden = {"render", "synthesize", "dispatch", "execute", "load_model", "reserve_gpu", "publish", "write_audio"}
    assert not (public_names & forbidden)
