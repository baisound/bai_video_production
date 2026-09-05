from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task014_local_primary_narration_call_profile_v2 import (
    PROFILE_FIELDS,
    REASON_CODES,
    CallProfileDecision,
    LocalPrimaryNarrationCallProfileV2,
    compile_local_primary_narration_call_profile_v2,
    parse_local_primary_narration_call_profile_v2,
)
import ai_video_production.task014_local_primary_narration_call_profile_v2 as task014_v2
import ai_video_production.task073_owner_voice_local_wav_composition as task073
from test_task014_zero_shot_callable_contract import (
    assembled,
    compile_ready,
    h,
    plan_receipt,
    subject_receipt,
    transcript_receipt,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "task014-local-primary-narration-call-profile-v2.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA.name


def make_profile(
    *,
    parts: dict[str, object] | None = None,
    envelope: object | None = None,
    **overrides: object,
) -> LocalPrimaryNarrationCallProfileV2:
    current = assembled() if parts is None else parts
    values: dict[str, object] = {
        "profile_id": "call.profile.1",
        "profile_revision": 1,
        "parent_profile_sha256": None,
        "compiled_at": "2026-08-20T00:03:00Z",
        "expires_at": "2026-08-20T00:09:00Z",
        "project_manifest_revision": 1,
        "project_manifest_sha256": h("manifest"),
        "installed_session_sha256": h("installed session"),
        "operation_plan_id": "operation.plan.1",
        "operation_plan_sha256": h("operation plan"),
        "route_selection_revision_sha256": h("route selection"),
        "fixture_lineage_sha256": h("fixture lineage"),
        "callable_envelope": compile_ready(current) if envelope is None else envelope,
        "render_admission": current["admission"],
        "preflight": current["preflight"],
        "subject_binding_receipt": subject_receipt(current),
        "plan_derivation_receipt": plan_receipt(current),
        "reference_transcript_receipt": transcript_receipt(current),
        "narration_plan": current["plan"],
    }
    values.update(overrides)
    return compile_local_primary_narration_call_profile_v2(**values)


def test_ready_v2_profile_is_exact_body_free_and_round_trips() -> None:
    parts = assembled()
    profile = make_profile(parts=parts)
    document = profile.to_dict()
    assert tuple(document) == PROFILE_FIELDS
    assert profile.decision is CallProfileDecision.READY_FOR_TASK075_DISPATCH
    assert profile.reason_codes == ()
    assert profile.route_mode.value == "ZERO_SHOT_LOCAL"
    assert profile.intended_usage.value == "PREVIEW"
    assert profile.required_artifact_class == "STAGED_NARRATION_PCM_WAV_48000_MONO"
    assert (profile.required_sample_rate_hz, profile.required_channels) == (48_000, 1)
    assert profile.required_sample_format == "PCM_S24LE"
    assert profile.max_attempts == 1
    assert profile.automatic_retry_allowed is False
    assert parse_local_primary_narration_call_profile_v2(document).to_dict() == document
    serialized = canonical_json_bytes(document)
    assert b"reference audio" not in serialized
    assert parts["script"].text.encode("utf-8") not in serialized
    assert "script_text" not in document
    assert "output_path" not in document
    assert b"C:\\" not in serialized and b"/home/" not in serialized


def test_v1_envelope_is_not_relabelled_or_mutated() -> None:
    envelope = compile_ready(assembled())
    before = envelope.to_private_dict()
    assert envelope.decision.value == "UNKNOWN"
    profile = make_profile(envelope=envelope)
    assert profile.decision is CallProfileDecision.READY_FOR_TASK075_DISPATCH
    assert envelope.to_private_dict() == before
    with pytest.raises(ValueError, match="incomplete, unknown, or reordered"):
        parse_local_primary_narration_call_profile_v2(before)


def test_schema_and_resource_mirror_are_exact_and_closed() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(make_profile().to_dict())
    assert schema["additionalProperties"] is False
    assert tuple(schema["required"]) == PROFILE_FIELDS
    assert tuple(schema["x-bai-field-order"]) == PROFILE_FIELDS
    assert schema["properties"]["schema"]["const"] == document_schema()
    assert set(schema["properties"]["reason_codes"]["items"]["enum"]) == REASON_CODES


def document_schema() -> str:
    return "bai.task014.local-primary-narration-call-profile.v2"


@pytest.mark.parametrize("mutation", ["missing", "extra", "reordered", "tuple-reasons"])
def test_parser_rejects_non_exact_documents(mutation: str) -> None:
    document = make_profile().to_dict()
    if mutation == "missing":
        document.pop("fixture_lineage_sha256")
    elif mutation == "extra":
        document["output_path"] = "forbidden"
    elif mutation == "reordered":
        value = document.pop("profile_id")
        document["profile_id"] = value
    else:
        document["reason_codes"] = tuple(document["reason_codes"])
    with pytest.raises(ValueError):
        parse_local_primary_narration_call_profile_v2(document)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("required_sample_rate_hz", 44_100),
        ("required_channels", 2),
        ("required_sample_format", "PCM_S16LE"),
        ("max_attempts", 2),
        ("automatic_retry_allowed", True),
        ("route_mode", "FINE_TUNED_LOCAL"),
        ("intended_usage", "FULL_RENDER"),
    ],
)
def test_execution_bounds_cannot_be_substituted(field: str, replacement: object) -> None:
    document = make_profile().to_dict()
    document[field] = replacement
    with pytest.raises(ValueError):
        parse_local_primary_narration_call_profile_v2(document)


def test_self_hash_detects_copy_tamper_and_recomputed_v1_is_not_v2() -> None:
    profile = make_profile()
    with pytest.raises(ValueError, match="profile_sha256"):
        replace(profile, operation_plan_sha256=h("foreign operation"))
    document = profile.to_dict()
    document["operation_plan_sha256"] = h("foreign operation")
    with pytest.raises(ValueError, match="profile_sha256"):
        parse_local_primary_narration_call_profile_v2(document)


def test_stale_time_and_foreign_binding_fail_closed() -> None:
    stale = make_profile(compiled_at="2026-08-20T00:10:00Z", expires_at="2026-08-20T00:11:00Z")
    assert stale.decision is CallProfileDecision.BLOCKED
    assert "CALLABLE_EVIDENCE_EXPIRED" in stale.reason_codes

    before_envelope = make_profile(compiled_at="2026-08-20T00:01:59Z")
    assert before_envelope.decision is CallProfileDecision.BLOCKED
    assert "CALL_PROFILE_TIME_ORDER_MISMATCH" in before_envelope.reason_codes

    primary = assembled()
    foreign = assembled(preflight_id="preflight.zero.foreign")
    mismatch = make_profile(
        parts=primary,
        render_admission=foreign["admission"],
        preflight=foreign["preflight"],
    )
    assert mismatch.decision is CallProfileDecision.BLOCKED
    assert "CALLABLE_ENVELOPE_BINDING_MISMATCH" in mismatch.reason_codes


def test_missing_unknown_or_expiry_overrun_receipt_cannot_be_ready() -> None:
    parts = assembled()
    with pytest.raises(TypeError, match="subject_binding_receipt"):
        make_profile(subject_binding_receipt=None)

    unknown_subject = subject_receipt(parts, subject_match_decision="UNKNOWN")
    unknown_envelope = compile_ready(parts, subject_binding_receipt=unknown_subject)
    unknown = make_profile(
        parts=parts,
        envelope=unknown_envelope,
        subject_binding_receipt=unknown_subject,
    )
    assert unknown.decision is CallProfileDecision.UNKNOWN
    assert "SUBJECT_BINDING_UNKNOWN" in unknown.reason_codes

    overrun = make_profile(expires_at="2026-08-20T00:10:01Z")
    assert overrun.decision is CallProfileDecision.BLOCKED
    assert "CALLABLE_EVIDENCE_EXPIRED" in overrun.reason_codes


def test_foreign_typed_receipt_cannot_close_v1_currentness() -> None:
    primary = assembled()
    profile = make_profile(
        parts=primary,
        subject_binding_receipt=subject_receipt(
            primary,
            subject_match_evidence_sha256=h("foreign subject evidence"),
        ),
    )
    assert profile.decision is CallProfileDecision.BLOCKED
    assert "SUBJECT_BINDING_MISMATCH" in profile.reason_codes


def test_current_preflight_receipt_and_plan_coordinates_are_rechecked() -> None:
    parts = assembled()
    stale_subject = make_profile(
        parts=parts,
        subject_binding_receipt=subject_receipt(
            parts,
            consent_current_evaluation_sha256=h("stale consent evaluation"),
        ),
    )
    assert stale_subject.decision is CallProfileDecision.BLOCKED
    assert "SUBJECT_BINDING_MISMATCH" in stale_subject.reason_codes

    stale_transcript = make_profile(
        parts=parts,
        reference_transcript_receipt=transcript_receipt(
            parts,
            rights_current_evaluation_sha256=h("stale rights evaluation"),
        ),
    )
    assert stale_transcript.decision is CallProfileDecision.BLOCKED
    assert "REFERENCE_TRANSCRIPT_BINDING_MISMATCH" in stale_transcript.reason_codes

    stale_plan_receipt = make_profile(
        parts=parts,
        plan_derivation_receipt=plan_receipt(
            parts,
            source_text_binding_sha256=h("stale source text binding"),
        ),
    )
    assert stale_plan_receipt.decision is CallProfileDecision.BLOCKED
    assert "PLAN_DERIVATION_MISMATCH" in stale_plan_receipt.reason_codes

    foreign_plan = assembled(script_text="別の承認済み本文。")["plan"]
    stale_plan_body = make_profile(parts=parts, narration_plan=foreign_plan)
    assert stale_plan_body.decision is CallProfileDecision.BLOCKED
    assert "PLAN_DERIVATION_MISMATCH" in stale_plan_body.reason_codes


def test_revision_parent_and_expiry_are_strict() -> None:
    with pytest.raises(ValueError, match="parent_profile_sha256"):
        make_profile(profile_revision=2, parent_profile_sha256=None)
    with pytest.raises(ValueError, match="parent_profile_sha256"):
        make_profile(profile_revision=1, parent_profile_sha256=h("parent"))
    with pytest.raises(ValueError, match="later"):
        make_profile(expires_at="2026-08-20T00:03:00Z")


def test_task073_call_profile_projection_is_accepted_but_not_authority() -> None:
    profile = make_profile()
    receipt = profile.to_task073_receipt_ref(
        producer_build_sha256=h("producer build"),
        quick_clone_flow_sha256=h("quick clone flow"),
    )
    accepted = task073._receipt("call_profile", receipt)
    assert accepted == receipt
    assert receipt["producer_state"] == "READY_FOR_TASK075_DISPATCH"
    assert receipt["authority_created"] is False
    assert receipt["production_eligible"] is False


def test_v2_module_cannot_dispatch_or_perform_io() -> None:
    forbidden_exports = {
        "dispatch",
        "execute",
        "load_model",
        "open_output_sink",
        "publish_audio",
        "mint_capability",
    }
    assert set(task014_v2.__all__).isdisjoint(forbidden_exports)
    assert not hasattr(task014_v2, "subprocess")
    assert not hasattr(task014_v2, "Path")
    assert not hasattr(task014_v2, "os")


def test_reason_vocabulary_is_closed() -> None:
    document = make_profile().to_dict()
    document["decision"] = "UNKNOWN"
    document["reason_codes"] = ["NEW_UNREVIEWED_REASON"]
    preimage = {field: document[field] for field in PROFILE_FIELDS[:-1]}
    document["profile_sha256"] = sha256_bytes(canonical_json_bytes(preimage))
    with pytest.raises(ValueError, match="reason_codes"):
        parse_local_primary_narration_call_profile_v2(document)
