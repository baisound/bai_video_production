from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from ai_video_production.serialization import sha256_bytes
from ai_video_production.voice_profile_route_selection import (
    CASOutcome,
    ComputePreference,
    CurrentnessResult,
    ProducerBindingState,
    RouteMode,
    SourceRequirement,
    VoiceProfileRouteSelection,
    VoiceProfileRouteSelectionEphemeralFixture,
    VoiceRouteSelectionCASReadback,
    VoiceRouteSelectionCASRequest,
    VoiceRouteSelectionCurrentnessEvaluation,
    validate_route_selection_cas_readback,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "voice_profile_route_selection.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / "voice_profile_route_selection.schema.json"
NOW = "2026-09-01T09:00:00Z"


def digest(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def selection(
    *,
    mode: RouteMode = RouteMode.ZERO_SHOT_LOCAL,
    revision: int = 1,
    predecessor: str | None = None,
) -> VoiceProfileRouteSelection:
    fine = mode is RouteMode.FINE_TUNED_LOCAL
    return VoiceProfileRouteSelection.create(
        project_id="project.alpha",
        project_manifest_revision_sha256=digest("manifest"),
        voice_profile_id="voice.owner",
        voice_profile_revision=7,
        voice_profile_revision_sha256=digest("voice-profile-7"),
        consent_revision_sha256=digest("consent-4"),
        consent_current_evaluation_sha256=digest("consent-current"),
        consent_evaluated_at="2026-09-01T08:00:00Z",
        consent_expires_at="2026-10-01T08:00:00Z",
        selection_revision=revision,
        predecessor_selection_sha256=predecessor,
        route_mode=mode,
        public_route_key="narration.qwen3.local",
        installed_route_binding_sha256=digest("installed-route"),
        local_audio_model_inventory_revision_sha256=digest("inventory-revision"),
        local_audio_model_inventory_entry_sha256=digest("inventory-entry"),
        model_license_evidence_sha256=digest("license"),
        source_requirement=(
            SourceRequirement.MODEL_CANDIDATE_REQUIRED
            if fine
            else SourceRequirement.PRIVATE_REFERENCE_REQUIRED
        ),
        model_candidate_revision_sha256=digest("model-candidate") if fine else None,
        model_candidate_currentness_sha256=digest("model-current") if fine else None,
        compute_preference_ref=ComputePreference.AUTO,
        created_at=NOW,
    )


def currentness(
    chosen: VoiceProfileRouteSelection,
    *,
    evaluated_at: str = NOW,
    producer_readback_overrides: dict[str, str | None] | None = None,
    **overrides: ProducerBindingState,
) -> VoiceRouteSelectionCurrentnessEvaluation:
    model_state = (
        ProducerBindingState.NOT_APPLICABLE
        if chosen.route_mode is RouteMode.ZERO_SHOT_LOCAL
        else ProducerBindingState.CURRENT
    )
    values = {
        "project_state": ProducerBindingState.CURRENT,
        "voice_profile_state": ProducerBindingState.CURRENT,
        "consent_state": ProducerBindingState.CURRENT,
        "inventory_state": ProducerBindingState.CURRENT,
        "license_state": ProducerBindingState.CURRENT,
        "installed_route_state": ProducerBindingState.CURRENT,
        "model_candidate_revision_state": model_state,
        "model_candidate_currentness_state": model_state,
    }
    values.update(overrides)
    producer_readbacks = {
        "project_readback_sha256": digest("project-readback"),
        "voice_profile_readback_sha256": digest("voice-profile-readback"),
        "consent_readback_sha256": digest("consent-readback"),
        "inventory_readback_sha256": digest("inventory-readback"),
        "license_readback_sha256": digest("license-readback"),
        "installed_route_readback_sha256": digest("installed-route-readback"),
        "model_candidate_revision_readback_sha256": (
            None if chosen.route_mode is RouteMode.ZERO_SHOT_LOCAL else digest("model-revision-readback")
        ),
        "model_candidate_currentness_readback_sha256": (
            None if chosen.route_mode is RouteMode.ZERO_SHOT_LOCAL else digest("model-currentness-readback")
        ),
    }
    if producer_readback_overrides:
        producer_readbacks.update(producer_readback_overrides)
    return VoiceRouteSelectionCurrentnessEvaluation.create(
        selection=chosen,
        evaluated_at=evaluated_at,
        trusted_time_receipt_sha256=digest("trusted-time"),
        producer_readback_sha256s=producer_readbacks,
        **values,
    )


def test_durable_zero_shot_and_fine_tuned_are_deterministic_and_closed() -> None:
    zero = selection()
    fine = selection(mode=RouteMode.FINE_TUNED_LOCAL)
    assert VoiceProfileRouteSelection.from_dict(zero.to_dict()).to_dict() == zero.to_dict()
    assert VoiceProfileRouteSelection.from_dict(fine.to_dict()).to_dict() == fine.to_dict()
    assert zero.to_dict()["saved"] is True
    assert fine.to_dict()["model_candidate_revision_sha256"] == digest("model-candidate")
    assert zero.to_dict()["selection_sha256"] == selection().to_dict()["selection_sha256"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("route_mode", "UNSUPPORTED"),
        ("source_requirement", "MODEL_CANDIDATE_REQUIRED"),
        ("model_candidate_revision_sha256", digest("illegal-model")),
        ("model_candidate_currentness_sha256", digest("illegal-currentness")),
        ("saved", False),
        ("runtime_loaded", True),
        ("model_downloaded", True),
        ("inference_started", True),
        ("audio_body_persisted", True),
        ("path_persisted", True),
    ],
)
def test_durable_selection_rejects_mode_mix_or_effect_claim(field: str, value: object) -> None:
    payload = selection().to_dict()
    payload[field] = value
    with pytest.raises(ValueError):
        VoiceProfileRouteSelection.from_dict(payload)


def test_selection_revision_and_predecessor_are_exact() -> None:
    first = selection()
    second = selection(revision=2, predecessor=first.selection_sha256)
    assert second.to_dict()["predecessor_selection_sha256"] == first.selection_sha256
    payload = second.to_dict()
    payload["predecessor_selection_sha256"] = None
    with pytest.raises(ValueError, match="genesis"):
        VoiceProfileRouteSelection.from_dict(payload)


@pytest.mark.parametrize(
    "host_location",
    (
        "C:\\private\\voice.wav",
        "C:private_voice.wav",
        "private/voice.wav",
        "file:private_voice.wav",
        "file://private/voice.wav",
        "route.C:/Users/Alice/private/ref.wav",
        "source.https://host/private/ref.wav",
        "Ｃ：private_voice.wav",
        "private／voice.wav",
        "private_voice.wav",
    ),
)
def test_host_path_uri_or_file_name_cannot_become_route_identity(host_location: str) -> None:
    payload = selection().to_dict()
    payload["public_route_key"] = host_location
    with pytest.raises(ValueError, match="host path|closed narration"):
        VoiceProfileRouteSelection.from_dict(payload)


@pytest.mark.parametrize(
    "host_location",
    (
        "C:private_voice.wav",
        "private/voice.wav",
        "file:private_voice.wav",
        "Ｃ：private_voice.wav",
        "private／voice.wav",
        "private_voice.wav",
    ),
)
def test_ephemeral_public_route_key_rejects_path_like_values(host_location: str) -> None:
    fixture = VoiceProfileRouteSelectionEphemeralFixture.create(
        fixture_id="fixture.route.zero",
        project_id="project.alpha",
        voice_profile_id="voice.owner",
        voice_profile_revision_sha256=digest("voice-profile-7"),
        consent_current_evaluation_sha256=digest("consent-current"),
        route_mode=RouteMode.ZERO_SHOT_LOCAL,
        public_route_key="narration.qwen3.local",
        installed_route_binding_sha256=digest("installed-route"),
        local_audio_model_inventory_entry_sha256=digest("inventory-entry"),
        model_license_evidence_sha256=digest("license"),
        source_requirement=SourceRequirement.PRIVATE_REFERENCE_REQUIRED,
        model_candidate_revision_sha256=None,
        model_candidate_currentness_sha256=None,
        compute_preference_ref=ComputePreference.CPU,
        created_at=NOW,
    ).to_dict()
    fixture["public_route_key"] = host_location
    with pytest.raises(ValueError, match="host path|closed narration"):
        VoiceProfileRouteSelectionEphemeralFixture.from_dict(fixture)


def test_ephemeral_fixture_round_trips_but_never_gains_authority() -> None:
    fixture = VoiceProfileRouteSelectionEphemeralFixture.create(
        fixture_id="fixture.route.zero",
        project_id="project.alpha",
        voice_profile_id="voice.owner",
        voice_profile_revision_sha256=digest("voice-profile-7"),
        consent_current_evaluation_sha256=digest("consent-current"),
        route_mode=RouteMode.ZERO_SHOT_LOCAL,
        public_route_key="narration.qwen3.local",
        installed_route_binding_sha256=digest("installed-route"),
        local_audio_model_inventory_entry_sha256=digest("inventory-entry"),
        model_license_evidence_sha256=digest("license"),
        source_requirement=SourceRequirement.PRIVATE_REFERENCE_REQUIRED,
        model_candidate_revision_sha256=None,
        model_candidate_currentness_sha256=None,
        compute_preference_ref=ComputePreference.CPU,
        created_at=NOW,
    )
    value = fixture.to_dict()
    assert value["saved"] is False and value["fixture_only"] is True
    assert value["executable"] is False and value["authority_created"] is False
    assert VoiceProfileRouteSelectionEphemeralFixture.from_dict(value).to_dict() == value


def test_currentness_requires_every_mode_specific_producer() -> None:
    zero = currentness(selection())
    fine = currentness(selection(mode=RouteMode.FINE_TUNED_LOCAL))
    assert zero.runnable_current is True and fine.runnable_current is True
    stale = currentness(selection(), consent_state=ProducerBindingState.STALE)
    assert stale.runnable_current is False
    assert stale.to_dict()["result"] == CurrentnessResult.NOT_RUNNABLE.value
    unknown = currentness(selection(), installed_route_state=ProducerBindingState.NOT_CONFIRMED)
    assert unknown.to_dict()["result"] == CurrentnessResult.NOT_CONFIRMED.value


def test_zero_shot_model_currentness_must_be_not_applicable() -> None:
    result = currentness(
        selection(),
        model_candidate_revision_state=ProducerBindingState.CURRENT,
        model_candidate_currentness_state=ProducerBindingState.CURRENT,
    )
    assert result.runnable_current is False
    assert any("MUST_BE_NOT_APPLICABLE" in reason for reason in result.to_dict()["reason_codes"])


def test_currentness_tamper_cannot_invent_runnable() -> None:
    value = currentness(selection(), consent_state=ProducerBindingState.REVOKED).to_dict()
    value["runnable_current"] = True
    with pytest.raises(ValueError, match="classification"):
        VoiceRouteSelectionCurrentnessEvaluation.from_dict(value)


@pytest.mark.parametrize(
    "path_like_reason",
    (
        "C:private_voice.wav",
        "private/voice.wav",
        "file:private_voice.wav",
        "Ｃ：private_voice.wav",
        "private／voice.wav",
        "private_voice.wav",
    ),
)
def test_currentness_reason_codes_reject_path_like_values(path_like_reason: str) -> None:
    value = currentness(selection(), consent_state=ProducerBindingState.STALE).to_dict()
    value["reason_codes"] = [path_like_reason]
    with pytest.raises(ValueError, match="host path|closed public grammar"):
        VoiceRouteSelectionCurrentnessEvaluation.from_dict(value)


def test_route_selection_python_and_schema_share_200_character_bounds() -> None:
    value = selection().to_dict()
    value["project_id"] = "a" * 201
    with pytest.raises(ValueError, match="200 characters"):
        VoiceProfileRouteSelection.from_dict(value)

    value = selection().to_dict()
    value["public_route_key"] = f"narration.{'a' * 201}.local"
    with pytest.raises(ValueError, match="200 characters"):
        VoiceProfileRouteSelection.from_dict(value)


def test_currentness_uses_trusted_evaluation_time_for_consent_expiry() -> None:
    result = currentness(selection(), evaluated_at="2026-10-01T08:00:00Z")
    value = result.to_dict()
    assert value["result"] == CurrentnessResult.NOT_RUNNABLE.value
    assert value["runnable_current"] is False
    assert "CONSENT_EXPIRED_AT_EVALUATION" in value["reason_codes"]


def test_currentness_rejects_trusted_time_rollback_before_bound_evidence() -> None:
    with pytest.raises(ValueError, match="predates"):
        currentness(selection(), evaluated_at="2026-09-01T07:59:59Z")
    payload = selection().to_dict()
    payload["created_at"] = "2026-09-01T07:59:59Z"
    with pytest.raises(ValueError, match="cannot predate"):
        VoiceProfileRouteSelection.from_dict(payload)


def test_currentness_requires_exact_typed_producer_readback_set() -> None:
    with pytest.raises(ValueError, match="requires an exact typed producer readback"):
        currentness(
            selection(),
            producer_readback_overrides={"consent_readback_sha256": None},
        )
    value = currentness(selection()).to_dict()
    value["project_readback_sha256"] = digest("cross-selection-project-readback")
    with pytest.raises(ValueError, match="readback set digest mismatch"):
        VoiceRouteSelectionCurrentnessEvaluation.from_dict(value)


def test_cas_request_and_committed_readback_bind_exact_lineage() -> None:
    chosen = selection()
    request = VoiceRouteSelectionCASRequest.create(
        operation_id="operation.route.1",
        selection=chosen,
        expected_project_transaction_head_sha256=digest("project-head"),
        expected_selection_head_sha256=None,
    )
    readback = VoiceRouteSelectionCASReadback.create(
        request=request,
        outcome=CASOutcome.COMMITTED,
        result_project_transaction_head_sha256=digest("project-head-2"),
        result_selection_head_sha256=chosen.selection_sha256,
        committed_selection_sha256=chosen.selection_sha256,
        pinned_store_identity_sha256=digest("pinned-store"),
        pinned_readback_match=True,
        readback_at=NOW,
    )
    validate_route_selection_cas_readback(request, chosen, readback)
    value = readback.to_dict()
    assert value["automatic_retry_started"] is False
    assert value["producer_binding_state"] == "NOT_BOUND"
    assert value["fixture_only"] is True
    assert value["canonical_producer_acceptance_state"] == "NOT_CONFIRMED"
    assert value["canonical_producer_readback"] is False
    assert value["execution_ready"] is False
    value["producer_binding_state"] = "CURRENT"
    with pytest.raises(ValueError, match="canonical TASK074-C producer"):
        VoiceRouteSelectionCASReadback.from_dict(value)


def test_cas_rejects_stale_predecessor_reply_mismatch_and_retry_claim() -> None:
    first = selection()
    second = selection(revision=2, predecessor=first.selection_sha256)
    wrong = VoiceRouteSelectionCASRequest.create(
        operation_id="operation.route.2",
        selection=second,
        expected_project_transaction_head_sha256=digest("project-head"),
        expected_selection_head_sha256=digest("wrong-head"),
    )
    conflict = VoiceRouteSelectionCASReadback.create(
        request=wrong,
        outcome=CASOutcome.CONFLICT,
        result_project_transaction_head_sha256=digest("project-head-current"),
        result_selection_head_sha256=first.selection_sha256,
        committed_selection_sha256=None,
        pinned_store_identity_sha256=digest("pinned-store"),
        pinned_readback_match=False,
        readback_at=NOW,
    )
    with pytest.raises(ValueError, match="predecessor"):
        validate_route_selection_cas_readback(wrong, second, conflict)
    tampered = conflict.to_dict()
    tampered["automatic_retry_started"] = True
    with pytest.raises(ValueError, match="remain false"):
        VoiceRouteSelectionCASReadback.from_dict(tampered)


def test_digest_and_unknown_field_tamper_fail_closed() -> None:
    payload = selection().to_dict()
    payload["selection_sha256"] = digest("tampered")
    with pytest.raises(ValueError, match="digest mismatch"):
        VoiceProfileRouteSelection.from_dict(payload)
    payload = selection().to_dict()
    payload["raw_audio_body"] = "forbidden"
    with pytest.raises(ValueError, match="unknown"):
        VoiceProfileRouteSelection.from_dict(payload)


def test_schema_validates_all_body_free_route_records_and_is_mirrored() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    chosen = selection()
    request = VoiceRouteSelectionCASRequest.create(
        operation_id="operation.route.1",
        selection=chosen,
        expected_project_transaction_head_sha256=digest("project-head"),
        expected_selection_head_sha256=None,
    )
    records = [
        chosen.to_dict(),
        VoiceProfileRouteSelectionEphemeralFixture.create(
            fixture_id="fixture.route.zero",
            project_id="project.alpha",
            voice_profile_id="voice.owner",
            voice_profile_revision_sha256=digest("voice-profile-7"),
            consent_current_evaluation_sha256=digest("consent-current"),
            route_mode=RouteMode.ZERO_SHOT_LOCAL,
            public_route_key="narration.qwen3.local",
            installed_route_binding_sha256=digest("installed-route"),
            local_audio_model_inventory_entry_sha256=digest("inventory-entry"),
            model_license_evidence_sha256=digest("license"),
            source_requirement=SourceRequirement.PRIVATE_REFERENCE_REQUIRED,
            model_candidate_revision_sha256=None,
            model_candidate_currentness_sha256=None,
            compute_preference_ref=ComputePreference.CPU,
            created_at=NOW,
        ).to_dict(),
        currentness(chosen).to_dict(),
        request.to_dict(),
        VoiceRouteSelectionCASReadback.create(
            request=request,
            outcome=CASOutcome.COMMITTED,
            result_project_transaction_head_sha256=digest("project-head-2"),
            result_selection_head_sha256=chosen.selection_sha256,
            committed_selection_sha256=chosen.selection_sha256,
            pinned_store_identity_sha256=digest("pinned-store"),
            pinned_readback_match=True,
            readback_at=NOW,
        ).to_dict(),
    ]
    validator = Draft202012Validator(schema)
    for record in records:
        validator.validate(record)
    invalid = deepcopy(chosen.to_dict())
    invalid["audio_body_persisted"] = True
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    path_like_values = (
        "C:private_voice.wav",
        "private/voice.wav",
        "file:private_voice.wav",
        "Ｃ：private_voice.wav",
        "private／voice.wav",
        "private_voice.wav",
    )
    for path_like in path_like_values:
        invalid = deepcopy(chosen.to_dict())
        invalid["public_route_key"] = path_like
        with pytest.raises(ValidationError):
            validator.validate(invalid)
        invalid = deepcopy(records[1])
        invalid["public_route_key"] = path_like
        with pytest.raises(ValidationError):
            validator.validate(invalid)
        invalid = deepcopy(records[2])
        invalid["reason_codes"] = [path_like]
        with pytest.raises(ValidationError):
            validator.validate(invalid)
    invalid = deepcopy(chosen.to_dict())
    invalid["project_id"] = "a" * 201
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    invalid = deepcopy(chosen.to_dict())
    invalid["public_route_key"] = f"narration.{'a' * 201}.local"
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    invalid = deepcopy(records[2])
    del invalid["consent_readback_sha256"]
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    invalid = deepcopy(records[2])
    invalid["model_candidate_revision_readback_sha256"] = digest("illegal-zero-shot-model-readback")
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    invalid = deepcopy(records[2])
    invalid["runnable_current"] = True
    invalid["result"] = "NOT_RUNNABLE"
    invalid["reason_codes"] = ["STALE"]
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    invalid = deepcopy(records[-1])
    invalid["canonical_producer_acceptance_state"] = "CURRENT"
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()


def test_module_has_no_io_model_or_execution_surface() -> None:
    path = ROOT / "src" / "ai_video_production" / "voice_profile_route_selection.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported.isdisjoint({"os", "pathlib", "sqlite3", "subprocess", "socket", "wave", "soundfile", "requests"})
    exported = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    assert exported.isdisjoint({"execute", "save", "render", "infer", "load_model", "open_audio"})
