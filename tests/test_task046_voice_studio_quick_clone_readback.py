from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from typing import Mapping

from jsonschema import Draft202012Validator, FormatChecker
import pytest

from ai_video_production.owner_narration_local_primary import (
    LocalNarrationRouteMode,
    NarrationIntendedUsage,
    compile_local_primary_preflight,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.voice_model_builder_runtime import add_record_digest
from ai_video_production.voice_profile_revision import ConsentReference, ConsentState
from ai_video_production.voice_studio_quick_clone import (
    ComputePreference,
    ComputeResolutionState,
    ExecutionState,
    ModelExecutionPolicy,
    OwnerListeningState,
    PreviewAssetAdoptionState,
    ProfileAdoptionState,
    QualityState,
    QuickCloneFlowRevision,
    ReferenceRetentionState,
    ResultAdmissionState,
    RuntimeAggregateState,
    SetupState,
    SourceKind,
)
from ai_video_production.voice_studio_quick_clone_readback import (
    MAX_SYNTHETIC_PREVIEW_FRAMES,
    QuickCloneReadbackReceipt,
    assert_no_effect_surface,
    compile_quick_clone_readback,
    public_projection,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "voice-studio-quick-clone-readback.schema.json"
MIRROR = (
    ROOT
    / "src"
    / "ai_video_production"
    / "schema_resources"
    / SCHEMA.name
)
SOURCE_AT = "2026-09-01T05:00:00Z"
FLOW_AT = "2026-09-01T05:01:00Z"
FIXTURE_REQUEST_AT = "2026-09-01T05:02:00Z"
FIXTURE_COMPLETED_AT = "2026-09-01T05:03:00Z"
NOW = "2026-09-01T05:04:00Z"


def digest(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def canonical_digest(value: Mapping[str, object]) -> str:
    return sha256_bytes(canonical_json_bytes(dict(value)))


def consent(*, state: ConsentState = ConsentState.ACTIVE) -> dict[str, object]:
    return ConsentReference(
        consent_subject_ref="owner.subject",
        consent_scope="Local Owner narration",
        allowed_usage_classes=("OWNER_NARRATION_LOCAL",),
        state=state,
        subject_verified=state is not ConsentState.UNKNOWN,
        evidence_id=None if state is ConsentState.UNKNOWN else "consent.evidence.1",
        evidence_sha256=None if state is ConsentState.UNKNOWN else digest("consent"),
    ).to_dict()


def script() -> dict[str, object]:
    return {
        "text_owner": "TASK-006",
        "approved_text_revision_ref": "script.revision.3",
        "approved_text_revision_sha256": digest("script revision"),
        "source_text_binding_sha256": digest("script binding"),
        "approved": True,
        "body_persisted": False,
    }


def voice(*, state: str = "BOUND_VERIFIED") -> dict[str, object]:
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
        "consent": consent(),
        "current_consent_state": "ACTIVE",
        "current_consent_evaluation_sha256": digest("consent current"),
        "canonical_evidence_ref": "voice.profile.evidence.1",
        "canonical_evidence_sha256": digest("voice evidence"),
    }


def engine(
    *,
    route: LocalNarrationRouteMode = LocalNarrationRouteMode.ZERO_SHOT_LOCAL,
    state: str = "BOUND_VERIFIED",
    license_state: str = "COMMERCIAL_ALLOWED",
    capability: str = "VERIFIED",
    engine_id: str = "local.tts.engine",
) -> dict[str, object]:
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
        "route_mode": route.value,
        "engine_id": engine_id,
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


def resource(route: LocalNarrationRouteMode) -> dict[str, object]:
    return {
        "contract_state": "BOUND_VERIFIED",
        "route_mode": route.value,
        "resource_profile_ref": "resource.profile.1",
        "resource_profile_sha256": digest("resource profile"),
        "result": "PASS",
        "evidence_ref": "resource.evidence.1",
        "evidence_sha256": digest("resource evidence"),
    }


def rights() -> dict[str, object]:
    return {
        "contract_state": "BOUND_VERIFIED",
        "usage_class": "LOCAL_NARRATION_PREVIEW",
        "state": "PASS",
        "evidence_ref": "rights.evidence.1",
        "evidence_sha256": digest("rights evidence"),
        "evaluated_at": SOURCE_AT,
    }


def zero_shot() -> dict[str, object]:
    return {
        "contract_state": "BOUND_VERIFIED",
        "asset_id": "asset.owner.reference",
        "asset_checksum_sha256": digest("reference bytes"),
        "asset_revision_binding_ref": "asset.revision.binding.1",
        "asset_revision_binding_sha256": digest("asset revision"),
        "reference_profile_ref": "reference.profile.1",
        "reference_profile_sha256": digest("reference profile"),
        "consent_current_evaluation_sha256": digest("reference consent"),
        "rights_current_evaluation_sha256": digest("reference rights"),
        "audio_body_persisted": False,
    }


def fine_tuned() -> dict[str, object]:
    return {
        "contract_state": "BOUND_VERIFIED",
        "dataset_revision_id": "dataset.revision.1",
        "dataset_revision_sha256": digest("dataset"),
        "training_input_snapshot_id": "training.snapshot.1",
        "training_input_snapshot_sha256": digest("training snapshot"),
        "model_candidate_revision_id": "model.candidate.1",
        "model_candidate_revision_sha256": digest("candidate"),
        "model_artifact_binding_ref": "model.binding.1",
        "model_artifact_binding_sha256": digest("model binding"),
        "owner_model_approval_decision_ref": "owner.approval.1",
        "owner_model_approval_decision_sha256": digest("approval"),
        "consent_current_evaluation_sha256": digest("model consent"),
        "rights_current_evaluation_sha256": digest("model rights"),
        "dataset_body_persisted": False,
        "model_bytes_persisted": False,
    }


def preflight(
    *,
    engine_binding: dict[str, object] | None = None,
    voice_binding: dict[str, object] | None = None,
    reference_binding: dict[str, object] | None = None,
    route: LocalNarrationRouteMode = LocalNarrationRouteMode.ZERO_SHOT_LOCAL,
    created_at: str = SOURCE_AT,
):
    return compile_local_primary_preflight(
        project_id="project.alpha",
        preflight_id="preflight.quick-clone.1",
        created_at=created_at,
        route_mode=route,
        intended_usage=NarrationIntendedUsage.PREVIEW,
        script_text_binding=script(),
        voice_profile_revision_binding=voice_binding or voice(),
        engine_admission_binding=engine_binding or engine(route=route),
        resource_feasibility_binding=resource(route),
        rights_evaluation_binding=rights(),
        zero_shot_reference_binding=(
            reference_binding or zero_shot()
            if route is LocalNarrationRouteMode.ZERO_SHOT_LOCAL
            else None
        ),
        fine_tuned_model_binding=(
            fine_tuned()
            if route is LocalNarrationRouteMode.FINE_TUNED_LOCAL
            else None
        ),
    )


def flow_for(preflight_record=None, **changes: object) -> QuickCloneFlowRevision:
    selected = preflight_record or preflight()
    engine_binding = dict(selected.engine_admission_binding)
    voice_binding = dict(selected.voice_profile_revision_binding)
    reference_binding = selected.zero_shot_reference_binding
    values: dict[str, object] = {
        "flow_id": "quick-clone:flow-readback-1",
        "revision": 1,
        "parent_revision_sha256": None,
        "created_at": FLOW_AT,
        "source_kind": SourceKind.TASK003_ASSET,
        "setup_state": SetupState.READY,
        "execution_state": ExecutionState.PREFLIGHT_BLOCKED,
        "quality_state": QualityState.NOT_AVAILABLE,
        "owner_listening_state": OwnerListeningState.NOT_AVAILABLE,
        "profile_adoption_state": ProfileAdoptionState.NOT_AVAILABLE,
        "preview_asset_adoption_state": PreviewAssetAdoptionState.NOT_AVAILABLE,
        "reference_retention_state": ReferenceRetentionState.UNDECIDED,
        "compute_preference": ComputePreference.AUTO,
        "compute_resolution_state": ComputeResolutionState.GPU_READY,
        "model_execution_policy": ModelExecutionPolicy.CUDA_ONLY,
        "runtime_aggregate_state": RuntimeAggregateState.BOUND_VERIFIED,
        "result_admission_state": ResultAdmissionState.NOT_BOUND,
        "source_binding_sha256": (
            canonical_digest(dict(reference_binding))
            if reference_binding is not None
            else digest("unsupported source binding")
        ),
        "consent_binding_sha256": voice_binding.get(
            "current_consent_evaluation_sha256"
        )
        or digest("unbound consent"),
        "reference_transcript_sha256": digest("reference transcript"),
        "preview_text_sha256": selected.script_text_binding[
            "source_text_binding_sha256"
        ],
        "preview_text_code_points": 42,
        "preview_profile_revision_sha256": voice_binding.get(
            "voice_profile_revision_sha256"
        )
        or digest("unbound profile"),
        "model_selection_binding_sha256": canonical_digest(engine_binding),
        "runtime_aggregate_binding_sha256": digest("runtime aggregate"),
        "preflight_sha256": selected.preflight_sha256,
        "reason_codes": ("TASK014_RESULT_PRODUCER_NOT_BOUND",),
    }
    values.update(changes)
    return QuickCloneFlowRevision(**values)  # type: ignore[arg-type]


def draft() -> QuickCloneFlowRevision:
    return QuickCloneFlowRevision(
        flow_id="quick-clone:draft-readback-1",
        revision=1,
        parent_revision_sha256=None,
        created_at=FLOW_AT,
        source_kind=SourceKind.TASK046_PRIVATE_REFERENCE,
        setup_state=SetupState.NOT_INSTALLED,
        execution_state=ExecutionState.DRAFT,
        quality_state=QualityState.NOT_AVAILABLE,
        owner_listening_state=OwnerListeningState.NOT_AVAILABLE,
        profile_adoption_state=ProfileAdoptionState.NOT_AVAILABLE,
        preview_asset_adoption_state=PreviewAssetAdoptionState.NOT_AVAILABLE,
        reference_retention_state=ReferenceRetentionState.UNDECIDED,
        compute_preference=ComputePreference.AUTO,
        compute_resolution_state=ComputeResolutionState.NOT_RESOLVED,
        model_execution_policy=ModelExecutionPolicy.CUDA_ONLY,
        runtime_aggregate_state=RuntimeAggregateState.NOT_BOUND,
        result_admission_state=ResultAdmissionState.NOT_BOUND,
        source_binding_sha256=digest("draft source"),
        consent_binding_sha256=digest("draft consent"),
        reference_transcript_sha256=digest("draft transcript"),
        preview_text_sha256=digest("draft text"),
        preview_text_code_points=20,
        preview_profile_revision_sha256=digest("draft profile"),
        model_selection_binding_sha256=digest("draft model selection"),
        runtime_aggregate_binding_sha256=None,
    )


def synthetic_request(**changes: object) -> dict[str, object]:
    body: dict[str, object] = {
        "record_type": "SyntheticMasterAssemblyRequest",
        "request_id": "fixture.request.1",
        "workflow_sha256": digest("gate3 workflow"),
        "model_candidate_sha256": digest("model candidate revision"),
        "voice_profile_revision_sha256": digest("fixture voice profile revision"),
        "assembly_policy_sha256": digest("assembly policy"),
        "authority_kind": "APPROVED_SYNTHETIC_TEST_AUTHORITY",
        "authority_evidence_sha256": digest("synthetic authority"),
        "ordered_inputs": [
            {
                "order_index": 0,
                "cue_sha256": digest("cue 1"),
                "source_logical_ref": "fixture/cue-1.wav",
                "inspection_receipt_sha256": digest("inspection 1"),
                "pause_after_samples": 480,
            },
            {
                "order_index": 1,
                "cue_sha256": digest("cue 2"),
                "source_logical_ref": "fixture/cue-2.wav",
                "inspection_receipt_sha256": digest("inspection 2"),
                "pause_after_samples": 0,
            },
        ],
        "output_logical_ref": "fixture/preview.wav",
        "max_total_frames": MAX_SYNTHETIC_PREVIEW_FRAMES,
        "execution_state": "PROPOSAL_ONLY",
        "execution_started": False,
        "owner_audio_used": False,
        "dataset_effect_started": False,
        "training_started": False,
        "model_inference_started": False,
        "publication_started": False,
        "created_at": FIXTURE_REQUEST_AT,
    }
    body.update(changes)
    return add_record_digest(body, "request_sha256")


def synthetic_fixture(
    request: Mapping[str, object],
    **changes: object,
) -> dict[str, object]:
    ordered_inputs = request["ordered_inputs"]
    assert isinstance(ordered_inputs, list)
    body: dict[str, object] = {
        "record_type": "SyntheticMasterAssemblyReceipt",
        "receipt_id": "fixture.receipt.1",
        "request_sha256": request["request_sha256"],
        "ordered_cue_sha256": [item["cue_sha256"] for item in ordered_inputs],
        "output_logical_ref": request["output_logical_ref"],
        "output_sha256": digest("fixture output"),
        "output_bytes": 144_044,
        "sample_rate_hz": 48_000,
        "channels": 1,
        "sample_width_bytes": 3,
        "frame_count": 48_000,
        "duration_numerator": 48_000,
        "duration_denominator": 48_000,
        "inserted_silence_samples": 480,
        "format_state": "PASS",
        "boundary_analysis_state": "UNKNOWN",
        "loudness_analysis_state": "UNKNOWN",
        "style_analysis_state": "UNKNOWN",
        "execution_state": "COMPLETED_SYNTHETIC",
        "owner_audio_used": False,
        "dataset_effect_started": False,
        "training_started": False,
        "model_inference_started": False,
        "asset_adoption_started": False,
        "publication_started": False,
        "completed_at": FIXTURE_COMPLETED_AT,
    }
    body.update(changes)
    return add_record_digest(body, "receipt_sha256")


def compile_without_fixture(
    flow_revision: QuickCloneFlowRevision,
    selected_preflight,
    *,
    generated_at: str = NOW,
) -> QuickCloneReadbackReceipt:
    return compile_quick_clone_readback(
        flow=flow_revision,
        task014_preflight=selected_preflight,
        calibration_projection=None,
        synthetic_fixture_request=None,
        synthetic_fixture_receipt=None,
        generated_at=generated_at,
    )


def validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def rehash_readback(value: dict[str, object]) -> dict[str, object]:
    body = {key: item for key, item in value.items() if key != "readback_sha256"}
    value["readback_sha256"] = canonical_digest(body)
    return value


def test_unbound_draft_round_trip_schema_mirror_and_public_projection_are_safe() -> None:
    receipt = compile_quick_clone_readback(
        flow=draft(),
        task014_preflight=None,
        calibration_projection=None,
        synthetic_fixture_request=None,
        synthetic_fixture_receipt=None,
        generated_at=NOW,
    )
    record = receipt.to_dict()
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    validator().validate(record)
    assert QuickCloneReadbackReceipt.from_dict(record) == receipt
    assert "TASK014_PREFLIGHT_NOT_BOUND" in receipt.reason_codes
    assert "TASK014_PRIVATE_REFERENCE_BINDING_NOT_AVAILABLE" in receipt.reason_codes
    assert "TRUSTED_TIME_NOT_BOUND" in receipt.reason_codes

    projection = public_projection(receipt)
    encoded = json.dumps(projection, sort_keys=True)
    assert projection["source_kind"] == "TASK046_PRIVATE_REFERENCE"
    assert projection["trusted_time_binding_state"] == "NOT_BOUND"
    assert projection["trusted_currentness_verified"] is False
    assert projection["synthetic_fixture_flow_binding_state"] == "NOT_BOUND"
    assert projection["product_result_bound"] is False
    assert projection["product_preview_playback_ready"] is False
    assert "sha256:" not in encoded
    assert "quick-clone:draft" not in encoded
    assert "owner.subject" not in encoded
    assert_no_effect_surface()


def test_exact_preflight_and_synthetic_pair_compose_without_product_promotion() -> None:
    exact_preflight = preflight()
    exact_flow = flow_for(exact_preflight)
    request = synthetic_request()
    receipt = compile_quick_clone_readback(
        flow=exact_flow,
        task014_preflight=exact_preflight,
        calibration_projection=None,
        synthetic_fixture_request=request,
        synthetic_fixture_receipt=synthetic_fixture(request),
        generated_at=NOW,
    )
    record = receipt.to_dict()
    validator().validate(record)
    assert receipt.source_kind is SourceKind.TASK003_ASSET
    assert receipt.model_binding_state.value == "BOUND_VERIFIED"
    assert receipt.model_license_state == "COMMERCIAL_ALLOWED"
    assert receipt.model_capability_probe_state == "VERIFIED"
    assert receipt.calibration_contract_state.value == "CANONICAL_REF_NOT_PROVIDED"
    assert receipt.calibration_result is None
    assert receipt.synthetic_fixture_state.value == "DEVELOPMENT_FIXTURE_ONLY"
    assert receipt.synthetic_fixture_request_sha256 == request["request_sha256"]
    assert receipt.synthetic_fixture_sample_count == 48_000
    assert receipt.synthetic_fixture_duration_us == 1_000_000
    assert "REFERENCE_CALIBRATION_NOT_BOUND" in receipt.reason_codes
    assert "SYNTHETIC_FIXTURE_DEVELOPMENT_ONLY" in receipt.reason_codes
    assert "SYNTHETIC_FIXTURE_FLOW_NOT_BOUND" in receipt.reason_codes
    assert record["product_result_bound"] is False
    assert record["model_loaded"] is False
    assert record["execution_authorized"] is False
    assert record["playback_authorized"] is False

    public = public_projection(receipt)
    assert public["task014_preflight_decision"] == "READY_FOR_OWNER_HUMAN_GATE"
    assert public["result_admission_state"] == "NOT_BOUND"
    assert public["output_quality_state"] == "NOT_AVAILABLE"
    assert public["owner_listening_state"] == "NOT_AVAILABLE"
    assert public["synthetic_fixture_sample_rate_hz"] == 48_000
    assert public["synthetic_fixture_channels"] == 1
    assert public["synthetic_fixture_sample_format"] == "PCM_S24LE"
    assert public["synthetic_fixture_request_receipt_pair_verified"] is True
    assert public["synthetic_fixture_flow_binding_state"] == "NOT_BOUND"
    assert public["synthetic_fixture_is_product_result"] is False
    assert public["profile_save_ready"] is False
    assert public["asset_publication_ready"] is False


def test_missing_extra_or_private_reference_preflight_binding_is_rejected() -> None:
    exact = preflight()
    with pytest.raises(ValueError, match="requires the exact"):
        compile_without_fixture(flow_for(exact), None)
    with pytest.raises(ValueError, match="unbound flow"):
        compile_without_fixture(
            replace(draft(), source_kind=SourceKind.TASK003_ASSET),
            exact,
        )
    with pytest.raises(ValueError, match="private reference"):
        compile_without_fixture(
            flow_for(exact, source_kind=SourceKind.TASK046_PRIVATE_REFERENCE),
            exact,
        )


def test_stale_preflight_profile_consent_model_and_preview_text_are_rejected() -> None:
    exact = preflight()
    stale_preflight = replace(exact, preflight_id="preflight.quick-clone.stale")
    with pytest.raises(ValueError, match="preflight digest"):
        compile_without_fixture(flow_for(exact), stale_preflight)

    cases = (
        (
            flow_for(exact, preview_profile_revision_sha256=digest("stale profile")),
            "VoiceProfile",
        ),
        (
            flow_for(exact, consent_binding_sha256=digest("stale consent")),
            "consent",
        ),
        (
            flow_for(exact, model_selection_binding_sha256=digest("wrong model")),
            "model selection",
        ),
        (
            flow_for(exact, preview_text_sha256=digest("wrong preview text")),
            "preview text",
        ),
    )
    for flow_revision, match in cases:
        with pytest.raises(ValueError, match=match):
            compile_without_fixture(flow_revision, exact)


@pytest.mark.parametrize(
    "field",
    [
        "asset_id",
        "asset_checksum_sha256",
        "asset_revision_binding_ref",
        "asset_revision_binding_sha256",
        "reference_profile_ref",
        "reference_profile_sha256",
        "consent_current_evaluation_sha256",
        "rights_current_evaluation_sha256",
    ],
)
def test_zero_shot_reference_revision_profile_consent_and_rights_digest_is_exact(
    field: str,
) -> None:
    canonical_reference = zero_shot()
    changed_reference = dict(canonical_reference)
    changed_reference[field] = digest(f"changed {field}")
    changed_preflight = preflight(reference_binding=changed_reference)
    stale_flow = flow_for(
        changed_preflight,
        source_binding_sha256=canonical_digest(canonical_reference),
    )
    with pytest.raises(ValueError, match="zero-shot reference"):
        compile_without_fixture(stale_flow, changed_preflight)


def test_unsupported_fine_tuned_route_cannot_enter_quick_clone_readback() -> None:
    fine = preflight(route=LocalNarrationRouteMode.FINE_TUNED_LOCAL)
    with pytest.raises(ValueError, match="ZERO_SHOT_LOCAL PREVIEW"):
        compile_without_fixture(flow_for(fine), fine)


def test_unbound_engine_is_visible_as_unknown_and_never_loaded() -> None:
    unresolved = preflight(engine_binding=engine(state="CANONICAL_REF_NOT_PROVIDED"))
    receipt = compile_without_fixture(flow_for(unresolved), unresolved)
    assert receipt.model_binding_state.value == "NOT_BOUND"
    assert receipt.task014_preflight_decision.value == "UNKNOWN"
    assert receipt.model_license_state is None
    assert receipt.model_capability_probe_state is None
    assert "MODEL_SELECTION_NOT_BOUND" in receipt.reason_codes
    assert public_projection(receipt)["model_loaded"] is False


@pytest.mark.parametrize(
    ("engine_binding", "reason"),
    [
        (engine(license_state="LEGAL_REVIEW_REQUIRED"), "MODEL_LICENSE_NOT_COMMERCIAL_ALLOWED"),
        (engine(capability="FAILED"), "MODEL_CAPABILITY_NOT_VERIFIED"),
        (engine(state="MISMATCH"), "MODEL_SELECTION_MISMATCH"),
    ],
)
def test_model_license_capability_and_binding_fail_closed(
    engine_binding: dict[str, object],
    reason: str,
) -> None:
    blocked = preflight(engine_binding=engine_binding)
    receipt = compile_without_fixture(flow_for(blocked), blocked)
    assert reason in receipt.reason_codes
    assert receipt.task014_preflight_decision.value in {"BLOCKED", "UNKNOWN"}
    assert receipt.to_dict()["execution_authorized"] is False


def test_self_asserted_calibration_projection_is_rejected_and_public_stays_unbound() -> None:
    exact = preflight()
    exact_flow = flow_for(exact)
    forged = {
        "contract_state": "BOUND_VERIFIED",
        "result": "PASS",
        "calibration_receipt_sha256": digest("self asserted calibration"),
    }
    with pytest.raises(ValueError, match="TASK-048 source bridge"):
        compile_quick_clone_readback(
            flow=exact_flow,
            task014_preflight=exact,
            calibration_projection=forged,
            synthetic_fixture_request=None,
            synthetic_fixture_receipt=None,
            generated_at=NOW,
        )
    receipt = compile_without_fixture(exact_flow, exact)
    public = public_projection(receipt)
    assert public["reference_calibration_contract_state"] == "CANONICAL_REF_NOT_PROVIDED"
    assert public["reference_calibration_result"] is None
    assert public["output_quality_state"] == "NOT_AVAILABLE"


def test_synthetic_fixture_requires_an_exact_request_receipt_pair() -> None:
    exact = preflight()
    exact_flow = flow_for(exact)
    request = synthetic_request()
    with pytest.raises(ValueError, match="request/receipt pair"):
        compile_quick_clone_readback(
            flow=exact_flow,
            task014_preflight=exact,
            calibration_projection=None,
            synthetic_fixture_request=request,
            synthetic_fixture_receipt=None,
            generated_at=NOW,
        )
    with pytest.raises(ValueError, match="request/receipt pair"):
        compile_quick_clone_readback(
            flow=exact_flow,
            task014_preflight=exact,
            calibration_projection=None,
            synthetic_fixture_request=None,
            synthetic_fixture_receipt=synthetic_fixture(request),
            generated_at=NOW,
        )


@pytest.mark.parametrize(
    ("updates", "match"),
    [
        ({"sample_rate_hz": 44_100, "format_state": "FAIL"}, "48 kHz"),
        ({"channels": 2, "format_state": "FAIL"}, "48 kHz"),
        ({"sample_width_bytes": 2, "format_state": "FAIL"}, "48 kHz"),
        ({"owner_audio_used": True}, "must remain false"),
        ({"model_inference_started": True}, "must remain false"),
    ],
)
def test_synthetic_fixture_wrong_format_or_effect_flags_are_rejected(
    updates: dict[str, object],
    match: str,
) -> None:
    exact = preflight()
    exact_flow = flow_for(exact)
    request = synthetic_request()
    with pytest.raises(ValueError, match=match):
        compile_quick_clone_readback(
            flow=exact_flow,
            task014_preflight=exact,
            calibration_projection=None,
            synthetic_fixture_request=request,
            synthetic_fixture_receipt=synthetic_fixture(request, **updates),
            generated_at=NOW,
        )


@pytest.mark.parametrize(
    "field",
    [
        "workflow_sha256",
        "model_candidate_sha256",
        "voice_profile_revision_sha256",
    ],
)
def test_synthetic_gate3_coordinates_are_not_reinterpreted_as_quick_clone_bindings(
    field: str,
) -> None:
    exact = preflight()
    exact_flow = flow_for(exact)
    request = synthetic_request(**{field: digest(f"different upstream {field}")})
    receipt = compile_quick_clone_readback(
        flow=exact_flow,
        task014_preflight=exact,
        calibration_projection=None,
        synthetic_fixture_request=request,
        synthetic_fixture_receipt=synthetic_fixture(request),
        generated_at=NOW,
    )
    assert "SYNTHETIC_FIXTURE_FLOW_NOT_BOUND" in receipt.reason_codes
    assert public_projection(receipt)["synthetic_fixture_flow_binding_state"] == "NOT_BOUND"


@pytest.mark.parametrize(
    ("request_updates", "match"),
    [
        ({"max_total_frames": MAX_SYNTHETIC_PREVIEW_FRAMES + 1}, "60 second"),
        ({"max_total_frames": 1}, "request frame cap"),
    ],
)
def test_synthetic_request_preview_cap_is_exact(
    request_updates: dict[str, object],
    match: str,
) -> None:
    exact = preflight()
    exact_flow = flow_for(exact)
    request = synthetic_request(**request_updates)
    with pytest.raises(ValueError, match=match):
        compile_quick_clone_readback(
            flow=exact_flow,
            task014_preflight=exact,
            calibration_projection=None,
            synthetic_fixture_request=request,
            synthetic_fixture_receipt=synthetic_fixture(request),
            generated_at=NOW,
        )


@pytest.mark.parametrize(
    ("receipt_updates", "match"),
    [
        ({"request_sha256": digest("different request")}, "request_sha256"),
        (
            {"ordered_cue_sha256": [digest("other cue 1"), digest("other cue 2")]},
            "ordered Cues",
        ),
        ({"output_logical_ref": "fixture/other.wav"}, "output logical ref"),
        (
            {
                "frame_count": MAX_SYNTHETIC_PREVIEW_FRAMES + 1,
                "duration_numerator": MAX_SYNTHETIC_PREVIEW_FRAMES + 1,
            },
            "request frame cap|60 second",
        ),
    ],
)
def test_synthetic_receipt_identity_and_output_cap_are_exact(
    receipt_updates: dict[str, object],
    match: str,
) -> None:
    exact = preflight()
    exact_flow = flow_for(exact)
    request = synthetic_request()
    with pytest.raises(ValueError, match=match):
        compile_quick_clone_readback(
            flow=exact_flow,
            task014_preflight=exact,
            calibration_projection=None,
            synthetic_fixture_request=request,
            synthetic_fixture_receipt=synthetic_fixture(request, **receipt_updates),
            generated_at=NOW,
        )


def test_synthetic_fixture_hash_tamper_and_analyzer_pass_are_rejected() -> None:
    exact = preflight()
    exact_flow = flow_for(exact)
    request = synthetic_request()
    tampered = synthetic_fixture(request)
    tampered["output_sha256"] = digest("tampered output")
    with pytest.raises(ValueError, match="receipt_sha256 mismatch"):
        compile_quick_clone_readback(
            flow=exact_flow,
            task014_preflight=exact,
            calibration_projection=None,
            synthetic_fixture_request=request,
            synthetic_fixture_receipt=tampered,
            generated_at=NOW,
        )
    with pytest.raises(ValueError, match="analyzer PASS"):
        compile_quick_clone_readback(
            flow=exact_flow,
            task014_preflight=exact,
            calibration_projection=None,
            synthetic_fixture_request=request,
            synthetic_fixture_receipt=synthetic_fixture(
                request,
                boundary_analysis_state="PASS",
            ),
            generated_at=NOW,
        )


def test_timestamp_causality_is_checked_but_trusted_currentness_is_not_claimed() -> None:
    exact = preflight()
    exact_flow = flow_for(exact)
    with pytest.raises(ValueError, match="flow.created_at"):
        compile_without_fixture(
            replace(exact_flow, created_at="2026-09-01T05:05:00Z"),
            exact,
        )

    later_preflight = preflight(created_at="2026-09-01T05:02:00Z")
    with pytest.raises(ValueError, match="postdate the Quick Clone flow"):
        compile_without_fixture(flow_for(later_preflight), later_preflight)

    early_request = synthetic_request(created_at="2026-09-01T04:59:00Z")
    unbound_fixture = compile_quick_clone_readback(
        flow=exact_flow,
        task014_preflight=exact,
        calibration_projection=None,
        synthetic_fixture_request=early_request,
        synthetic_fixture_receipt=synthetic_fixture(early_request),
        generated_at=NOW,
    )
    assert "SYNTHETIC_FIXTURE_FLOW_NOT_BOUND" in unbound_fixture.reason_codes

    request = synthetic_request(created_at=FIXTURE_COMPLETED_AT)
    with pytest.raises(ValueError, match="receipt must not predate"):
        compile_quick_clone_readback(
            flow=exact_flow,
            task014_preflight=exact,
            calibration_projection=None,
            synthetic_fixture_request=request,
            synthetic_fixture_receipt=synthetic_fixture(
                request,
                completed_at=FIXTURE_REQUEST_AT,
            ),
            generated_at=NOW,
        )

    request = synthetic_request()
    with pytest.raises(ValueError, match="postdate the read-back"):
        compile_quick_clone_readback(
            flow=exact_flow,
            task014_preflight=exact,
            calibration_projection=None,
            synthetic_fixture_request=request,
            synthetic_fixture_receipt=synthetic_fixture(
                request,
                completed_at="2026-09-01T05:05:00Z",
            ),
            generated_at=NOW,
        )

    public = public_projection(compile_without_fixture(exact_flow, exact))
    assert public["trusted_time_binding_state"] == "NOT_BOUND"
    assert public["trusted_currentness_verified"] is False


def test_host_private_paths_raw_body_and_unknown_fields_are_rejected() -> None:
    path_preflight = preflight(engine_binding=engine(engine_id="C:/private/model"))
    with pytest.raises(ValueError, match="host/private path"):
        compile_without_fixture(flow_for(path_preflight), path_preflight)

    exact = preflight()
    exact_flow = flow_for(exact)
    path_request = synthetic_request(
        output_logical_ref="https://private.invalid/voice.wav",
    )
    with pytest.raises(ValueError, match="host/private path"):
        compile_quick_clone_readback(
            flow=exact_flow,
            task014_preflight=exact,
            calibration_projection=None,
            synthetic_fixture_request=path_request,
            synthetic_fixture_receipt=synthetic_fixture(path_request),
            generated_at=NOW,
        )

    request = synthetic_request()
    raw_receipt = synthetic_fixture(request)
    raw_receipt["audio_body"] = "PRIVATE_AUDIO_BYTES"
    with pytest.raises(ValueError, match="fields"):
        compile_quick_clone_readback(
            flow=exact_flow,
            task014_preflight=exact,
            calibration_projection=None,
            synthetic_fixture_request=request,
            synthetic_fixture_receipt=raw_receipt,
            generated_at=NOW,
        )


def test_serialized_effect_reason_identity_digest_and_unknown_tampering_fail_closed() -> None:
    exact = preflight()
    exact_flow = flow_for(exact)
    request = synthetic_request()
    receipt = compile_quick_clone_readback(
        flow=exact_flow,
        task014_preflight=exact,
        calibration_projection=None,
        synthetic_fixture_request=request,
        synthetic_fixture_receipt=synthetic_fixture(request),
        generated_at=NOW,
    ).to_dict()

    effect = deepcopy(receipt)
    effect["execution_authorized"] = True
    rehash_readback(effect)
    with pytest.raises(ValueError, match="no-effect"):
        QuickCloneReadbackReceipt.from_dict(effect)

    reasons = deepcopy(receipt)
    reasons["reason_codes"] = ["FORGED_READY"]
    rehash_readback(reasons)
    with pytest.raises(ValueError, match="reason_codes"):
        QuickCloneReadbackReceipt.from_dict(reasons)

    private_source = deepcopy(receipt)
    private_source["source_kind"] = "TASK046_PRIVATE_REFERENCE"
    rehash_readback(private_source)
    with pytest.raises(ValueError, match="private reference"):
        QuickCloneReadbackReceipt.from_dict(private_source)
    assert list(validator().iter_errors(private_source))

    forged_result = deepcopy(receipt)
    forged_result["result_admission_state"] = "MISMATCH"
    rehash_readback(forged_result)
    with pytest.raises(ValueError, match="product result"):
        QuickCloneReadbackReceipt.from_dict(forged_result)

    missing_request = deepcopy(receipt)
    missing_request["synthetic_fixture_request_sha256"] = None
    rehash_readback(missing_request)
    with pytest.raises(ValueError, match="synthetic_fixture_request_sha256"):
        QuickCloneReadbackReceipt.from_dict(missing_request)
    assert list(validator().iter_errors(missing_request))

    trusted_time = deepcopy(receipt)
    trusted_time["trusted_time_binding_state"] = "BOUND_VERIFIED"
    rehash_readback(trusted_time)
    with pytest.raises(ValueError, match="identity"):
        QuickCloneReadbackReceipt.from_dict(trusted_time)

    forged_fixture_binding = deepcopy(receipt)
    forged_fixture_binding["synthetic_fixture_flow_binding_state"] = "BOUND_VERIFIED"
    rehash_readback(forged_fixture_binding)
    with pytest.raises(ValueError, match="identity"):
        QuickCloneReadbackReceipt.from_dict(forged_fixture_binding)
    assert list(validator().iter_errors(forged_fixture_binding))

    digest_tamper = deepcopy(receipt)
    digest_tamper["synthetic_fixture_sample_count"] = 96_000
    with pytest.raises(ValueError, match="duration|readback_sha256"):
        QuickCloneReadbackReceipt.from_dict(digest_tamper)

    unknown = deepcopy(receipt)
    unknown["private_prompt"] = "do not persist"
    with pytest.raises(ValueError, match="fields"):
        QuickCloneReadbackReceipt.from_dict(unknown)


def test_public_projection_is_log_safe_and_module_has_no_direct_effect_imports() -> None:
    exact = preflight()
    exact_flow = flow_for(exact)
    request = synthetic_request()
    receipt = compile_quick_clone_readback(
        flow=exact_flow,
        task014_preflight=exact,
        calibration_projection=None,
        synthetic_fixture_request=request,
        synthetic_fixture_receipt=synthetic_fixture(request),
        generated_at=NOW,
    )
    projection = public_projection(receipt)
    encoded = json.dumps(projection, sort_keys=True)
    for private in (
        "sha256:",
        "local.tts.engine",
        "model.artifact.local",
        "owner.subject",
        "fixture/preview.wav",
        "project.alpha",
        "preflight.quick-clone.1",
        "PRIVATE_AUDIO_BYTES",
        "C:/",
        "\\\\",
    ):
        assert private not in encoded
    assert projection["private_identity_exposed"] is False
    assert projection["digest_identity_exposed"] is False
    assert projection["result_admission_state"] == "NOT_BOUND"
    assert projection["profile_adoption_state"] == "NOT_AVAILABLE"
    assert projection["preview_asset_adoption_state"] == "NOT_AVAILABLE"

    source_path = (
        ROOT
        / "src"
        / "ai_video_production"
        / "voice_studio_quick_clone_readback.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported.isdisjoint(
        {
            "os",
            "pathlib",
            "subprocess",
            "socket",
            "requests",
            "wave",
            "soundfile",
            "torch",
        }
    )
    forbidden_calls = {"open", "write", "unlink", "mkdir", "remove", "run", "Popen"}
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert called.isdisjoint(forbidden_calls)
