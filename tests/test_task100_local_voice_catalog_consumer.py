from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator, ValidationError

from ai_video_production.local_audio_model_inventory import (
    AutomationReadiness,
    InstalledState,
    InventoryCurrentness,
    LocalFreeLicenseState,
    RuntimeReadiness,
)
from ai_video_production.owner_narration_local_primary import (
    LocalNarrationRouteMode,
    LocalPrimaryNarrationPreflight,
    NarrationIntendedUsage,
    compile_local_primary_preflight,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task100_local_voice_catalog_admission import (
    CompiledLocalVoiceCatalogAdmissionV1,
    CustodyContractState,
    ObservationSource,
    ProducerAuthenticity,
    ProducerCurrentness,
    compile_local_voice_catalog_admission,
    create_local_voice_catalog_assessment,
    create_local_voice_catalog_candidate,
)
from ai_video_production.task100_local_voice_catalog_consumer import (
    LocalVoiceCatalogConsumerReadbackV1,
    compile_local_voice_catalog_consumer_readback,
)
from ai_video_production.voice_profile_revision import ConsentReference, ConsentState
from ai_video_production.voice_profile_route_selection import (
    ComputePreference,
    ProducerBindingState,
    RouteMode,
    SourceRequirement,
    VoiceProfileRouteSelection,
    VoiceRouteSelectionCurrentnessEvaluation,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "task100-local-voice-catalog-consumer.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA.name
SOURCE = ROOT / "src" / "ai_video_production" / "task100_local_voice_catalog_consumer.py"


def digest(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def candidate(*, source: str = ObservationSource.VERIFIED_PRODUCER_READBACK.value):
    return create_local_voice_catalog_candidate(
        candidate_id="baisound-c04-stable-v2-0-1",
        revision=1,
        predecessor_sha256=None,
        provider_id="baisound-local",
        engine_id="gpt-sovits-v2pro",
        model_id="baisound-c04-stable-v2.0.1",
        runtime_build_sha256=digest("runtime-build"),
        model_pair_sha256=digest("model-pair"),
        sovits_sha256=digest("sovits"),
        gpt_sha256=digest("gpt"),
        voice_profile_revision_sha256=digest("voice-profile"),
        model_candidate_revision_sha256=digest("model-candidate"),
        custody_provenance={
            "variant": "EXISTING_MODEL_IMPORT",
            "producer_task": "TASK-101",
            "receipt_type": "ExistingModelImportCustodyReceiptV1",
            "receipt_sha256": digest("custody-receipt"),
            "readback_type": "ExistingModelImportCustodyReadbackV1",
            "readback_sha256": digest("custody-readback"),
        },
        consent_currentness_sha256=digest("consent-currentness"),
        h4_approval_sha256=digest("h4-approval"),
        license_evidence_sha256=digest("license"),
        installed_binding_sha256=digest("installed-binding"),
        capability_map_sha256=digest("capability-map"),
        execution_port_id="task075-c04-local",
        producer_readback_set_sha256=digest("producer-readback-set"),
        observation_source=source,
        observed_at="2026-09-29T00:00:00Z",
        expires_at="2026-09-29T00:10:00Z",
    )


def assessment(cand, **changes):
    producer_states = {
        key: ProducerCurrentness.CURRENT.value
        for key in (
            "LINEAGE",
            "CUSTODY",
            "CONSENT",
            "H4_APPROVAL",
            "INSTALLED_BINDING",
            "CAPABILITY_MAP",
            "EXECUTION_PORT",
        )
    }
    values = {
        "candidate_sha256": cand.candidate_sha256,
        "producer_readback_set_sha256": cand.to_dict()["producer_readback_set_sha256"],
        "evaluated_at": "2026-09-29T00:01:00Z",
        "installed_state": InstalledState.INSTALLED.value,
        "runtime_readiness": RuntimeReadiness.READY.value,
        "runtime_instance_id": "baisound-c04-runtime",
        "inventory_currentness": InventoryCurrentness.CURRENT.value,
        "license_state": LocalFreeLicenseState.CONFIRMED.value,
        "automation_readiness": AutomationReadiness.SCRIPTABLE.value,
        "producer_authenticity": ProducerAuthenticity.VERIFIED.value,
        "custody_contract_state": CustodyContractState.ACCEPTED.value,
        "required_producer_currentness": producer_states,
    }
    values.update(changes)
    return create_local_voice_catalog_assessment(**values)


def selection(cand, compiled, **changes) -> VoiceProfileRouteSelection:
    admission = compiled.admission.to_dict()
    values = {
        "project_id": "project.alpha",
        "project_manifest_revision_sha256": digest("project-manifest"),
        "voice_profile_id": "voice.owner",
        "voice_profile_revision": 7,
        "voice_profile_revision_sha256": cand.to_dict()["voice_profile_revision_sha256"],
        "consent_revision_sha256": digest("consent-revision"),
        "consent_current_evaluation_sha256": cand.to_dict()["consent_currentness_sha256"],
        "consent_evaluated_at": "2026-09-29T00:00:30Z",
        "consent_expires_at": "2026-09-29T00:09:30Z",
        "selection_revision": 1,
        "predecessor_selection_sha256": None,
        "route_mode": RouteMode.FINE_TUNED_LOCAL,
        "public_route_key": "narration.gpt-sovits.local",
        "installed_route_binding_sha256": cand.to_dict()["installed_binding_sha256"],
        "local_audio_model_inventory_revision_sha256": admission["inventory_sha256"],
        "local_audio_model_inventory_entry_sha256": admission["inventory_candidate_sha256"],
        "model_license_evidence_sha256": cand.to_dict()["license_evidence_sha256"],
        "source_requirement": SourceRequirement.MODEL_CANDIDATE_REQUIRED,
        "model_candidate_revision_sha256": cand.to_dict()["model_candidate_revision_sha256"],
        "model_candidate_currentness_sha256": digest("model-currentness"),
        "compute_preference_ref": ComputePreference.AUTO,
        "created_at": "2026-09-29T00:02:00Z",
    }
    values.update(changes)
    return VoiceProfileRouteSelection.create(**values)


def currentness(chosen, **changes) -> VoiceRouteSelectionCurrentnessEvaluation:
    states = {
        "project_state": ProducerBindingState.CURRENT,
        "voice_profile_state": ProducerBindingState.CURRENT,
        "consent_state": ProducerBindingState.CURRENT,
        "inventory_state": ProducerBindingState.CURRENT,
        "license_state": ProducerBindingState.CURRENT,
        "installed_route_state": ProducerBindingState.CURRENT,
        "model_candidate_revision_state": ProducerBindingState.CURRENT,
        "model_candidate_currentness_state": ProducerBindingState.CURRENT,
    }
    states.update(changes)
    return VoiceRouteSelectionCurrentnessEvaluation.create(
        selection=chosen,
        evaluated_at="2026-09-29T00:03:00Z",
        trusted_time_receipt_sha256=digest("trusted-time"),
        producer_readback_sha256s={
            "project_readback_sha256": digest("project-readback"),
            "voice_profile_readback_sha256": digest("voice-readback"),
            "consent_readback_sha256": digest("consent-readback"),
            "inventory_readback_sha256": digest("inventory-readback"),
            "license_readback_sha256": digest("license-readback"),
            "installed_route_readback_sha256": digest("installed-readback"),
            "model_candidate_revision_readback_sha256": digest("model-revision-readback"),
            "model_candidate_currentness_readback_sha256": digest("model-currentness-readback"),
        },
        **states,
    )


def narration_preflight(cand, chosen, **binding_changes):
    c = cand.to_dict()
    consent = ConsentReference(
        "owner.subject",
        "Local Owner narration",
        ("OWNER_NARRATION_LOCAL",),
        ConsentState.ACTIVE,
        True,
        "consent.evidence.1",
        digest("consent-evidence"),
    ).to_dict()
    values = {
        "project_id": chosen.to_dict()["project_id"],
        "preflight_id": "preflight.fine.1",
        "created_at": "2026-09-29T00:03:30Z",
        "route_mode": LocalNarrationRouteMode.FINE_TUNED_LOCAL,
        "intended_usage": NarrationIntendedUsage.PREVIEW,
        "script_text_binding": {
            "text_owner": "TASK-006",
            "approved_text_revision_ref": "script.revision.3",
            "approved_text_revision_sha256": digest("script-revision"),
            "source_text_binding_sha256": digest("source-text"),
            "approved": True,
            "body_persisted": False,
        },
        "voice_profile_revision_binding": {
            "contract_state": "BOUND_VERIFIED",
            "voice_profile_id": chosen.to_dict()["voice_profile_id"],
            "canonical_narration_profile_sha256": digest("narration-profile"),
            "revision": 7,
            "parent_revision_sha256": digest("voice-parent"),
            "voice_profile_revision_sha256": c["voice_profile_revision_sha256"],
            "consent": consent,
            "current_consent_state": ConsentState.ACTIVE.value,
            "current_consent_evaluation_sha256": c["consent_currentness_sha256"],
            "canonical_evidence_ref": "voice.profile.evidence.1",
            "canonical_evidence_sha256": digest("voice-profile-evidence"),
        },
        "engine_admission_binding": {
            "contract_state": "BOUND_VERIFIED",
            "route_mode": LocalNarrationRouteMode.FINE_TUNED_LOCAL.value,
            "engine_id": c["engine_id"],
            "engine_revision_sha256": digest("engine-revision"),
            "model_artifact_id": c["model_id"],
            "model_artifact_sha256": c["model_pair_sha256"],
            "runtime_id": "runtime.local",
            "runtime_sha256": c["runtime_build_sha256"],
            "code_revision_sha256": digest("code-revision"),
            "license_state": "COMMERCIAL_ALLOWED",
            "license_evidence_ref": "license.evidence.1",
            "license_evidence_sha256": c["license_evidence_sha256"],
            "capability_probe_state": "VERIFIED",
            "capability_probe_ref": "capability.probe.1",
            "capability_probe_sha256": c["capability_map_sha256"],
        },
        "resource_feasibility_binding": {
            "contract_state": "BOUND_VERIFIED",
            "route_mode": LocalNarrationRouteMode.FINE_TUNED_LOCAL.value,
            "resource_profile_ref": "resource.profile.1",
            "resource_profile_sha256": digest("resource-profile"),
            "result": "PASS",
            "evidence_ref": "resource.evidence.1",
            "evidence_sha256": digest("resource-evidence"),
        },
        "rights_evaluation_binding": {
            "contract_state": "BOUND_VERIFIED",
            "usage_class": "LOCAL_NARRATION_PREVIEW",
            "state": "PASS",
            "evidence_ref": "rights.evidence.1",
            "evidence_sha256": digest("rights-evidence"),
            "evaluated_at": "2026-09-29T00:03:00Z",
        },
        "zero_shot_reference_binding": None,
        "fine_tuned_model_binding": {
            "contract_state": "BOUND_VERIFIED",
            "dataset_revision_id": "voice.dataset.revision.2",
            "dataset_revision_sha256": digest("dataset-revision"),
            "training_input_snapshot_id": "training.input.snapshot.1",
            "training_input_snapshot_sha256": digest("training-input"),
            "model_candidate_revision_id": "model.candidate.revision.1",
            "model_candidate_revision_sha256": c["model_candidate_revision_sha256"],
            "model_artifact_binding_ref": "model.artifact.binding.1",
            "model_artifact_binding_sha256": c["installed_binding_sha256"],
            "owner_model_approval_decision_ref": "owner.model.approval.1",
            "owner_model_approval_decision_sha256": c["h4_approval_sha256"],
            "consent_current_evaluation_sha256": c["consent_currentness_sha256"],
            "rights_current_evaluation_sha256": digest("model-rights-current"),
            "dataset_body_persisted": False,
            "model_bytes_persisted": False,
        },
    }
    for binding_name, changes in binding_changes.items():
        if isinstance(changes, dict) and isinstance(values.get(binding_name), dict):
            values[binding_name] = {**values[binding_name], **changes}
        else:
            values[binding_name] = changes
    return compile_local_primary_preflight(**values)


def complete_inputs(*, assessment_changes=None, currentness_changes=None, preflight_changes=None):
    cand = candidate()
    assess = assessment(cand, **(assessment_changes or {}))
    compiled = compile_local_voice_catalog_admission(cand, assess)
    chosen = selection(cand, compiled)
    route_currentness = currentness(chosen, **(currentness_changes or {}))
    preflight = narration_preflight(cand, chosen, **(preflight_changes or {}))
    return cand, assess, compiled, chosen, route_currentness, preflight


def compile_readback(**changes):
    cand, assess, compiled, chosen, route_currentness, preflight = complete_inputs()
    values = {
        "candidate": cand,
        "assessment": assess,
        "compiled_admission": compiled,
        "route_selection": chosen,
        "route_currentness": route_currentness,
        "narration_preflight": preflight,
        "evaluated_at": "2026-09-29T00:04:00Z",
    }
    values.update(changes)
    return compile_local_voice_catalog_consumer_readback(**values)


def test_exact_fine_tuned_lineage_becomes_consumer_eligible_without_authority() -> None:
    readback = compile_readback()
    body = readback.to_dict()
    assert readback.consumer_live_eligible is True
    assert body["reason_codes"] == []
    assert body["authority_kind"] == "EVIDENCE_ONLY"
    assert body["resource_effect_count"] == 0
    for field in (
        "authority_created",
        "execution_authorized",
        "load_lease_created",
        "runtime_started",
        "model_loaded",
        "inference_started",
        "audio_body_persisted",
        "host_path_persisted",
    ):
        assert body[field] is False
    assert LocalVoiceCatalogConsumerReadbackV1.from_dict(body).to_dict() == body


@pytest.mark.parametrize(
    "changes",
    [
        {"voice_profile_revision_sha256": digest("wrong-voice")},
        {"consent_current_evaluation_sha256": digest("wrong-consent")},
        {"installed_route_binding_sha256": digest("wrong-installed")},
        {"local_audio_model_inventory_revision_sha256": digest("wrong-inventory")},
        {"local_audio_model_inventory_entry_sha256": digest("wrong-entry")},
        {"model_license_evidence_sha256": digest("wrong-license")},
        {"model_candidate_revision_sha256": digest("wrong-model-candidate")},
    ],
)
def test_task074_identity_crossing_is_rejected(changes) -> None:
    cand = candidate()
    assess = assessment(cand)
    compiled = compile_local_voice_catalog_admission(cand, assess)
    chosen = selection(cand, compiled, **changes)
    with pytest.raises(ValueError, match="mismatch"):
        compile_local_voice_catalog_consumer_readback(
            candidate=cand,
            assessment=assess,
            compiled_admission=compiled,
            route_selection=chosen,
            route_currentness=currentness(chosen),
            narration_preflight=narration_preflight(cand, chosen),
            evaluated_at="2026-09-29T00:04:00Z",
        )


@pytest.mark.parametrize(
    ("binding", "changes"),
    [
        ("voice_profile_revision_binding", {"voice_profile_id": "voice.other"}),
        ("voice_profile_revision_binding", {"voice_profile_revision_sha256": digest("wrong-voice")}),
        ("engine_admission_binding", {"engine_id": "other-engine"}),
        ("engine_admission_binding", {"model_artifact_id": "other-model"}),
        ("engine_admission_binding", {"model_artifact_sha256": digest("wrong-pair")}),
        ("engine_admission_binding", {"runtime_sha256": digest("wrong-runtime")}),
        ("engine_admission_binding", {"license_evidence_sha256": digest("wrong-license")}),
        ("engine_admission_binding", {"capability_probe_sha256": digest("wrong-capability")}),
        ("fine_tuned_model_binding", {"model_candidate_revision_sha256": digest("wrong-model")}),
        ("fine_tuned_model_binding", {"model_artifact_binding_sha256": digest("wrong-installed")}),
        ("fine_tuned_model_binding", {"owner_model_approval_decision_sha256": digest("wrong-h4")}),
        ("fine_tuned_model_binding", {"consent_current_evaluation_sha256": digest("wrong-consent")}),
    ],
)
def test_task014_identity_crossing_is_rejected(binding, changes) -> None:
    cand, assess, compiled, chosen, route_currentness, _ = complete_inputs()
    preflight = narration_preflight(cand, chosen, **{binding: changes})
    with pytest.raises(ValueError, match="mismatch"):
        compile_local_voice_catalog_consumer_readback(
            candidate=cand,
            assessment=assess,
            compiled_admission=compiled,
            route_selection=chosen,
            route_currentness=route_currentness,
            narration_preflight=preflight,
            evaluated_at="2026-09-29T00:04:00Z",
        )


def test_nonadmitted_catalog_is_ineligible_and_uses_closed_reasons() -> None:
    cand, assess, compiled, chosen, route_currentness, preflight = complete_inputs(
        assessment_changes={"installed_state": InstalledState.NOT_INSTALLED.value}
    )
    result = compile_local_voice_catalog_consumer_readback(
        candidate=cand,
        assessment=assess,
        compiled_admission=compiled,
        route_selection=chosen,
        route_currentness=route_currentness,
        narration_preflight=preflight,
        evaluated_at="2026-09-29T00:04:00Z",
    ).to_dict()
    assert result["consumer_live_eligible"] is False
    assert result["reason_codes"] == [
        "CATALOG_ADMISSION_NOT_ADMITTED",
        "INVENTORY_CANDIDATE_NOT_SELECTABLE",
    ]


def test_noncurrent_route_and_nonready_preflight_are_ineligible() -> None:
    cand, assess, compiled, chosen, route_currentness, preflight = complete_inputs(
        currentness_changes={"inventory_state": ProducerBindingState.STALE},
        preflight_changes={"script_text_binding": {"approved": False}},
    )
    result = compile_local_voice_catalog_consumer_readback(
        candidate=cand,
        assessment=assess,
        compiled_admission=compiled,
        route_selection=chosen,
        route_currentness=route_currentness,
        narration_preflight=preflight,
        evaluated_at="2026-09-29T00:04:00Z",
    ).to_dict()
    assert result["consumer_live_eligible"] is False
    assert result["reason_codes"] == [
        "ROUTE_CURRENTNESS_NOT_RUNNABLE",
        "NARRATION_PREFLIGHT_NOT_READY",
    ]


@pytest.mark.parametrize(
    "field",
    [
        "project_manifest_revision_sha256",
        "consent_current_evaluation_sha256",
        "model_candidate_currentness_sha256",
    ],
)
def test_resealed_task074_currentness_cannot_cross_selection_coordinates(field: str) -> None:
    cand, assess, compiled, chosen, route_currentness, preflight = complete_inputs()
    body = route_currentness.to_dict()
    body[field] = digest(f"crossed-{field}")
    digest_body = deepcopy(body)
    digest_body.pop("currentness_evaluation_sha256")
    body["currentness_evaluation_sha256"] = sha256_bytes(
        b"TASK074_VOICE_ROUTE_SELECTION_CURRENTNESS_EVALUATION_V1\0"
        + canonical_json_bytes(digest_body)
    )
    crossed = VoiceRouteSelectionCurrentnessEvaluation.from_dict(body)
    with pytest.raises(ValueError, match="route currentness .* mismatch"):
        compile_local_voice_catalog_consumer_readback(
            candidate=cand,
            assessment=assess,
            compiled_admission=compiled,
            route_selection=chosen,
            route_currentness=crossed,
            narration_preflight=preflight,
            evaluated_at="2026-09-29T00:04:00Z",
        )


def test_public_compiled_wrapper_cannot_bypass_canonical_readmission() -> None:
    cand = candidate()
    assess = assessment(cand, installed_state=InstalledState.NOT_INSTALLED.value)
    canonical = compile_local_voice_catalog_admission(cand, assess)
    forged_admission = canonical.admission.to_dict()
    forged_admission["admission_state"] = "ADMITTED_CATALOG_CANDIDATE"
    forged_admission["reason_codes"] = []
    forged_inventory = canonical.inventory.to_public_dict()
    forged_inventory["candidates"][0]["selectable"] = True
    forged_inventory["candidates"][0]["execution_port_id"] = cand.to_dict()["execution_port_id"]
    forged = CompiledLocalVoiceCatalogAdmissionV1(
        admission=SimpleNamespace(to_dict=lambda: forged_admission),
        inventory=SimpleNamespace(to_public_dict=lambda: forged_inventory),
    )
    chosen = selection(cand, canonical)
    with pytest.raises(TypeError, match="compiled_admission.admission"):
        compile_local_voice_catalog_consumer_readback(
            candidate=cand,
            assessment=assess,
            compiled_admission=forged,
            route_selection=chosen,
            route_currentness=currentness(chosen),
            narration_preflight=narration_preflight(cand, chosen),
            evaluated_at="2026-09-29T00:04:00Z",
        )


def test_typed_but_unrelated_compiled_admission_is_rejected() -> None:
    cand = candidate()
    assess = assessment(cand)
    unrelated = compile_local_voice_catalog_admission(
        cand,
        assessment(cand, evaluated_at="2026-09-29T00:01:30Z"),
    )
    chosen = selection(cand, unrelated)
    with pytest.raises(ValueError, match="canonical candidate/assessment"):
        compile_local_voice_catalog_consumer_readback(
            candidate=cand,
            assessment=assess,
            compiled_admission=unrelated,
            route_selection=chosen,
            route_currentness=currentness(chosen),
            narration_preflight=narration_preflight(cand, chosen),
            evaluated_at="2026-09-29T00:04:00Z",
        )


@pytest.mark.parametrize("evaluated_at", ["2026-09-28T23:59:59Z", "2026-09-29T00:10:00Z"])
def test_trusted_time_must_be_inside_candidate_window(evaluated_at: str) -> None:
    with pytest.raises(ValueError, match="validity window"):
        compile_readback(evaluated_at=evaluated_at)


@pytest.mark.parametrize("evaluated_at", ["2026-09-29T00:09:30Z", "2026-09-29T00:09:59Z"])
def test_trusted_time_cannot_reuse_currentness_at_or_after_consent_expiry(evaluated_at: str) -> None:
    with pytest.raises(ValueError, match="Consent validity window"):
        compile_readback(evaluated_at=evaluated_at)


def test_schema_mirror_and_positive_negative_vectors() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    body = compile_readback().to_dict()
    validator.validate(body)
    fractional = compile_readback(evaluated_at="2026-09-29T00:04:00.123Z").to_dict()
    validator.validate(fractional)
    malformed_fractional = deepcopy(body)
    malformed_fractional["evaluated_at"] = "2026-09-29T00:04:00\\123Z"
    with pytest.raises(ValidationError):
        validator.validate(malformed_fractional)
    bad = deepcopy(body)
    bad["execution_authorized"] = True
    with pytest.raises(ValidationError):
        validator.validate(bad)
    bad = deepcopy(body)
    bad["consumer_live_eligible"] = False
    with pytest.raises(ValidationError):
        validator.validate(bad)


def test_parser_rejects_effect_claim_reason_mismatch_and_digest_tamper() -> None:
    body = compile_readback().to_dict()
    for field, value in (
        ("model_loaded", True),
        ("resource_effect_count", 1),
        ("consumer_live_eligible", False),
        ("candidate_sha256", digest("tampered")),
    ):
        changed = deepcopy(body)
        changed[field] = value
        with pytest.raises(ValueError):
            LocalVoiceCatalogConsumerReadbackV1.from_dict(changed)


def test_hand_built_task014_preflight_cannot_bypass_producer_validation() -> None:
    cand, assess, compiled, chosen, route_currentness, preflight = complete_inputs()
    forged = LocalPrimaryNarrationPreflight(
        project_id=preflight.project_id,
        preflight_id=preflight.preflight_id,
        created_at=preflight.created_at,
        route_mode=preflight.route_mode,
        intended_usage=preflight.intended_usage,
        script_text_binding={**preflight.script_text_binding, "approved": False},
        voice_profile_revision_binding=preflight.voice_profile_revision_binding,
        engine_admission_binding=preflight.engine_admission_binding,
        resource_feasibility_binding=preflight.resource_feasibility_binding,
        rights_evaluation_binding=preflight.rights_evaluation_binding,
        zero_shot_reference_binding=preflight.zero_shot_reference_binding,
        fine_tuned_model_binding=preflight.fine_tuned_model_binding,
        decision=preflight.decision,
        reason_codes=preflight.reason_codes,
    )
    with pytest.raises(ValueError, match="classification mismatch"):
        compile_local_voice_catalog_consumer_readback(
            candidate=cand,
            assessment=assess,
            compiled_admission=compiled,
            route_selection=chosen,
            route_currentness=route_currentness,
            narration_preflight=forged,
            evaluated_at="2026-09-29T00:04:00Z",
        )


def test_source_has_no_effectful_runtime_imports() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    forbidden = {"os", "pathlib", "shutil", "socket", "subprocess", "requests", "httpx"}
    imported = {
        node.names[0].name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
    }
    imported.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert forbidden.isdisjoint(imported)
