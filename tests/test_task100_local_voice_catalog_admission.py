from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from ai_video_production.local_audio_model_inventory import (
    AutomationReadiness,
    InstalledState,
    InventoryCurrentness,
    LocalFreeLicenseState,
    RuntimeReadiness,
    project_public_voice_profile_models,
)
from ai_video_production.task100_local_voice_catalog_admission import (
    CatalogAdmissionState,
    CustodyContractState,
    LocalVoiceCatalogAdmissionV1,
    LocalVoiceCatalogAssessmentV1,
    LocalVoiceCatalogCandidateV1,
    ObservationSource,
    ProducerAuthenticity,
    ProducerCurrentness,
    compile_local_voice_catalog_admission,
    create_local_voice_catalog_assessment,
    create_local_voice_catalog_candidate,
    parse_local_voice_catalog_candidate_json,
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
from ai_video_production.voice_profile_store import VoiceProfileRevisionHistory


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SCHEMA = ROOT / "schemas" / "task100-local-voice-catalog-admission.schema.json"
PACKAGE_SCHEMA = ROOT / "src" / "ai_video_production" / "schema_resources" / PUBLIC_SCHEMA.name


def h(value: str) -> str:
    return "sha256:" + value * 64


def custody(variant: str = "TRAINING_TERMINAL") -> dict[str, str]:
    if variant == "EXISTING_MODEL_IMPORT":
        return {
            "variant": variant,
            "producer_task": "TASK-101",
            "receipt_type": "ExistingModelImportCustodyReceiptV1",
            "receipt_sha256": h("7"),
            "readback_type": "ExistingModelImportCustodyReadbackV1",
            "readback_sha256": h("8"),
        }
    return {
        "variant": variant,
        "producer_task": "TASK-084",
        "receipt_type": "Task084ModelArtifactCustodyReceiptV1",
        "receipt_sha256": h("7"),
        "readback_type": "Task084CustodyReadbackV1",
        "readback_sha256": h("8"),
    }


def candidate(*, source: str = "VERIFIED_PRODUCER_READBACK", variant: str = "TRAINING_TERMINAL", revision: int = 1, predecessor: str | None = None):
    return create_local_voice_catalog_candidate(
        candidate_id="baisound-c04-stable-v2-0-1",
        revision=revision,
        predecessor_sha256=predecessor,
        provider_id="baisound-local",
        engine_id="gpt-sovits-v2pro",
        model_id="baisound-c04-stable-v2.0.1",
        runtime_build_sha256=h("1"),
        model_pair_sha256=h("2"),
        sovits_sha256=h("3"),
        gpt_sha256=h("4"),
        voice_profile_revision_sha256=h("5"),
        model_candidate_revision_sha256=h("6"),
        custody_provenance=custody(variant),
        consent_currentness_sha256=h("9"),
        h4_approval_sha256=h("a"),
        license_evidence_sha256=h("b"),
        installed_binding_sha256=h("c"),
        capability_map_sha256=h("d"),
        execution_port_id="task075-c04-local",
        producer_readback_set_sha256=h("e"),
        observation_source=source,
        observed_at="2026-09-27T00:00:00Z",
        expires_at="2026-09-27T00:05:00Z",
    )


def currentness(**changes: str) -> dict[str, str]:
    body = {
        "LINEAGE": "CURRENT",
        "CUSTODY": "CURRENT",
        "CONSENT": "CURRENT",
        "H4_APPROVAL": "CURRENT",
        "INSTALLED_BINDING": "CURRENT",
        "CAPABILITY_MAP": "CURRENT",
        "EXECUTION_PORT": "CURRENT",
    }
    body.update(changes)
    return body


def assessment(cand, **changes):
    values = {
        "candidate_sha256": cand.candidate_sha256,
        "producer_readback_set_sha256": cand.to_dict()["producer_readback_set_sha256"],
        "evaluated_at": "2026-09-27T00:01:00Z",
        "installed_state": InstalledState.INSTALLED.value,
        "runtime_readiness": RuntimeReadiness.READY.value,
        "runtime_instance_id": "baisound-c04-runtime",
        "inventory_currentness": InventoryCurrentness.CURRENT.value,
        "license_state": LocalFreeLicenseState.CONFIRMED.value,
        "automation_readiness": AutomationReadiness.SCRIPTABLE.value,
        "producer_authenticity": ProducerAuthenticity.VERIFIED.value,
        "custody_contract_state": CustodyContractState.ACCEPTED.value,
        "required_producer_currentness": currentness(),
    }
    values.update(changes)
    return create_local_voice_catalog_assessment(**values)


def profile_history() -> VoiceProfileRevisionHistory:
    sha = h("f")
    consent = ConsentReference("owner-subject", "narration", ("NARRATION",), ConsentState.ACTIVE, True, "consent-evidence", sha)
    license_row = LicenseReference(
        "c04-artifact", "baisound-c04-stable-v2.0.1", sha, "gpt-sovits-v2pro",
        ModelLicenseClass.COMMERCIAL_ALLOWED, ArtifactAdmissionState.APPROVED,
        True, "license-evidence", sha,
    )
    capability = LocalVoiceCapabilityDescription(
        "GPT_SOVITS", "gpt-sovits-v2pro", ("ja-JP",), ("NARRATION",),
        True, CapabilityProbeState.VERIFIED, sha,
    )
    revision = VoiceProfileRevision("owner-voice", sha, 1, None, "2026-09-27T00:00:00Z", consent, license_row, capability)
    return VoiceProfileRevisionHistory("owner-voice", (revision,))


def schema_validator() -> Draft202012Validator:
    schema = json.loads(PUBLIC_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def test_frozen_fixture_vector_and_strict_json_parser() -> None:
    cand = candidate(source=ObservationSource.FIXTURE_ONLY.value, variant="EXISTING_MODEL_IMPORT")
    assert cand.candidate_sha256 == "sha256:587ca3aeecd17700695a1cffeeba8b5a7cb671cd2225e5a79a72fd3552acb2eb"
    encoded = json.dumps(cand.to_dict(), sort_keys=True, separators=(",", ":")).encode()
    assert parse_local_voice_catalog_candidate_json(encoded).to_dict() == cand.to_dict()


def test_custody_variants_are_closed_and_cross_variant_is_rejected() -> None:
    candidate(variant="EXISTING_MODEL_IMPORT")
    candidate(variant="TRAINING_TERMINAL")
    changed = candidate().to_dict()
    changed["custody_provenance"]["producer_task"] = "TASK-101"
    with pytest.raises(ValueError, match="custody producer/type"):
        create_local_voice_catalog_candidate(**{k: v for k, v in changed.items() if k not in {"contract_version", "record_type", "candidate_sha256"}})


def test_revision_requires_exact_predecessor_shape() -> None:
    with pytest.raises(ValueError, match="predecessor"):
        candidate(revision=2)
    with pytest.raises(ValueError, match="predecessor"):
        candidate(predecessor=h("0"))
    assert candidate(revision=2, predecessor=h("0")).to_dict()["revision"] == 2


@pytest.mark.parametrize("value", [r"C:\\private", "https:private", "bad/id", "../model"])
def test_public_ids_and_model_ids_reject_path_or_uri_shapes(value: str) -> None:
    body = candidate().to_dict()
    body["model_id"] = value
    body.pop("candidate_sha256")
    with pytest.raises(ValueError, match="model_id"):
        create_local_voice_catalog_candidate(**{k: v for k, v in body.items() if k not in {"contract_version", "record_type"}})


def test_parser_rejects_duplicate_nested_keys_bom_trailing_and_nonfinite() -> None:
    base = json.dumps(candidate().to_dict(), separators=(",", ":"))
    duplicate = base.replace('"variant":"TRAINING_TERMINAL"', '"variant":"TRAINING_TERMINAL","variant":"TRAINING_TERMINAL"')
    with pytest.raises(ValueError, match="duplicate"):
        parse_local_voice_catalog_candidate_json(duplicate.encode())
    for payload in (b"\xef\xbb\xbf" + base.encode(), base.encode() + b" ", b'{"x":NaN}'):
        with pytest.raises(ValueError):
            parse_local_voice_catalog_candidate_json(payload)


def test_parser_rejects_boundary_and_extreme_depth_as_value_error() -> None:
    for levels in (13, 2_000):
        payload = b"[" * levels + b"0" + b"]" * levels
        with pytest.raises(ValueError, match="depth"):
            parse_local_voice_catalog_candidate_json(payload)


def test_admitted_candidate_composes_existing_inventory_but_grants_no_live_authority() -> None:
    cand = candidate()
    compiled = compile_local_voice_catalog_admission(cand, assessment(cand))
    result = compiled.admission.to_dict()
    row = compiled.inventory.candidates[0]
    assert result["admission_state"] == CatalogAdmissionState.ADMITTED.value
    assert result["reason_codes"] == []
    assert row.selectable is True
    assert row.observation.source.value == "PINNED_CONTRACT"
    assert result["inventory_candidate_sha256"] == compiled.inventory.to_public_dict()["candidates"][0]["candidate_sha256"]
    assert result["inventory_sha256"] == compiled.inventory.to_public_dict()["inventory_sha256"]
    assert result["consumer_live_eligible"] is False
    assert result["consumer_currentness_required"] is True
    assert result["replayable_authority"] is False
    assert result["execution_authorized"] is False
    assert result["resource_effect_count"] == 0


@pytest.mark.parametrize(
    ("candidate_changes", "assessment_changes", "state", "reason"),
    [
        ({"source": "FIXTURE_ONLY", "variant": "EXISTING_MODEL_IMPORT"}, {"custody_contract_state": "PROPOSED_FIXTURE_ONLY"}, "FIXTURE_ONLY_CANDIDATE", "FIXTURE_ONLY_SOURCE"),
        ({}, {"producer_authenticity": "NOT_VERIFIED"}, "BLOCKED_CATALOG_CANDIDATE", "PRODUCER_AUTHENTICITY_NOT_VERIFIED"),
        ({"variant": "EXISTING_MODEL_IMPORT"}, {"custody_contract_state": "PROPOSED_FIXTURE_ONLY"}, "BLOCKED_CATALOG_CANDIDATE", "CUSTODY_CONTRACT_NOT_ACCEPTED"),
        ({}, {"required_producer_currentness": currentness(CONSENT="REVOKED")}, "BLOCKED_CATALOG_CANDIDATE", "CONSENT_REVOKED"),
    ],
)
def test_nonadmitted_inputs_normalize_legacy_inventory_fail_closed(candidate_changes, assessment_changes, state, reason) -> None:
    cand = candidate(**candidate_changes)
    compiled = compile_local_voice_catalog_admission(cand, assessment(cand, **assessment_changes))
    result = compiled.admission.to_dict()
    row = compiled.inventory.candidates[0]
    assert result["admission_state"] == state
    assert reason in result["reason_codes"]
    assert row.selectable is False
    assert row.observation.runtime_instance_id is None
    assert row.observation.execution_port_id is None
    assert row.observation.source.value == "HISTORICAL_EVIDENCE"
    projection = project_public_voice_profile_models((profile_history(),), compiled.inventory)[0]
    assert projection["generation_ready"] is False
    assert projection["profile_selectable"] is False


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"installed_state": "NOT_INSTALLED"}, "MODEL_NOT_INSTALLED"),
        ({"runtime_readiness": "STOPPED", "runtime_instance_id": None}, "RUNTIME_STOPPED"),
        ({"inventory_currentness": "STALE"}, "STALE_INVENTORY"),
        ({"license_state": "UNKNOWN"}, "LICENSE_NOT_CONFIRMED"),
        ({"automation_readiness": "DISPLAY_ONLY"}, "AUTOMATION_API_NOT_SCRIPTABLE"),
    ],
)
def test_each_negative_operational_state_blocks(changes, reason) -> None:
    cand = candidate()
    result = compile_local_voice_catalog_admission(cand, assessment(cand, **changes))
    assert reason in result.admission.to_dict()["reason_codes"]
    assert result.inventory.candidates[0].selectable is False


def test_assessment_binds_candidate_readback_set_and_valid_time() -> None:
    cand = candidate()
    with pytest.raises(ValueError, match="exact candidate"):
        compile_local_voice_catalog_admission(cand, assessment(cand, candidate_sha256=h("0")))
    with pytest.raises(ValueError, match="readback set"):
        compile_local_voice_catalog_admission(cand, assessment(cand, producer_readback_set_sha256=h("0")))
    for evaluated in ("2026-09-26T23:59:59Z", "2026-09-27T00:05:00Z"):
        with pytest.raises(ValueError, match="validity"):
            compile_local_voice_catalog_admission(cand, assessment(cand, evaluated_at=evaluated))


def test_evaluation_time_changes_assessment_and_admission_digest_and_round_trips() -> None:
    cand = candidate()
    left_assessment = assessment(cand, evaluated_at="2026-09-27T00:01:00Z")
    right_assessment = assessment(cand, evaluated_at="2026-09-27T00:02:00Z")
    left = compile_local_voice_catalog_admission(cand, left_assessment).admission.to_dict()
    right = compile_local_voice_catalog_admission(cand, right_assessment).admission.to_dict()
    assert left_assessment.to_dict()["assessment_sha256"] != right_assessment.to_dict()["assessment_sha256"]
    assert left["admission_sha256"] != right["admission_sha256"]
    assert left["candidate_observed_at"] == "2026-09-27T00:00:00Z"
    assert left["evaluated_at"] == "2026-09-27T00:01:00Z"
    assert left["candidate_expires_at"] == "2026-09-27T00:05:00Z"


def test_mapping_inputs_are_reparsed_and_deep_copied() -> None:
    cand = candidate()
    candidate_mapping = cand.to_dict()
    assessment_mapping = assessment(cand).to_dict()
    compiled = compile_local_voice_catalog_admission(candidate_mapping, assessment_mapping)
    candidate_mapping["candidate_id"] = "tampered"
    assessment_mapping["required_producer_currentness"]["LINEAGE"] = "REVOKED"
    assert compiled.inventory.candidates[0].observation.candidate_id == "baisound-c04-stable-v2-0-1"
    assert compiled.admission.to_dict()["reason_codes"] == []


def test_record_constructors_cannot_bypass_validated_factories_or_compiler() -> None:
    cand = candidate()
    assess = assessment(cand)
    admission = compile_local_voice_catalog_admission(cand, assess).admission
    for record_type, body in (
        (LocalVoiceCatalogCandidateV1, cand.to_dict()),
        (LocalVoiceCatalogAssessmentV1, assess.to_dict()),
        (LocalVoiceCatalogAdmissionV1, admission.to_dict()),
    ):
        with pytest.raises(TypeError, match="factory|compiler"):
            record_type(body)

    forged_body = candidate(
        source=ObservationSource.FIXTURE_ONLY.value,
        variant="EXISTING_MODEL_IMPORT",
    ).to_dict()
    forged_body["observation_source"] = ObservationSource.VERIFIED_PRODUCER_READBACK.value
    forged = object.__new__(LocalVoiceCatalogCandidateV1)
    object.__setattr__(forged, "data", forged_body)
    with pytest.raises(ValueError, match="canonical content"):
        compile_local_voice_catalog_admission(forged, assessment(cand))


def test_returned_records_are_deeply_immutable_and_exports_are_detached() -> None:
    cand = candidate()
    assess = assessment(cand)
    compiled = compile_local_voice_catalog_admission(cand, assess)
    with pytest.raises(TypeError):
        cand.data["candidate_id"] = "tampered"  # type: ignore[index]
    with pytest.raises(TypeError):
        assess.data["required_producer_currentness"]["LINEAGE"] = "REVOKED"  # type: ignore[index]
    with pytest.raises(TypeError):
        compiled.admission.data["reason_codes"] = ["TAMPERED"]  # type: ignore[index]
    exported = compiled.admission.to_dict()
    exported["reason_codes"].append("TAMPERED")
    assert compiled.admission.to_dict()["reason_codes"] == []


def test_schema_mirror_is_exact_and_validates_all_record_types() -> None:
    assert PUBLIC_SCHEMA.read_bytes() == PACKAGE_SCHEMA.read_bytes()
    validator = schema_validator()
    cand = candidate()
    assess = assessment(cand)
    admission = compile_local_voice_catalog_admission(cand, assess).admission
    for document in (cand.to_dict(), assess.to_dict(), admission.to_dict()):
        assert list(validator.iter_errors(document)) == []


def test_schema_and_parser_reject_unknown_fields_and_tampered_digests() -> None:
    validator = schema_validator()
    changed = candidate().to_dict()
    changed["private_path"] = r"C:\\private\\model.pth"
    assert list(validator.iter_errors(changed))
    changed.pop("private_path")
    changed["candidate_sha256"] = h("0")
    with pytest.raises(ValueError, match="canonical content"):
        parse_local_voice_catalog_candidate_json(json.dumps(changed, separators=(",", ":")).encode())


def test_schema_enforces_cross_field_conditions_and_calendar_timestamps() -> None:
    validator = schema_validator()

    changed_candidate = candidate().to_dict()
    changed_candidate["revision"] = 2
    assert list(validator.iter_errors(changed_candidate))
    changed_candidate = candidate().to_dict()
    changed_candidate["observed_at"] = "2026-02-30T00:00:00Z"
    assert list(validator.iter_errors(changed_candidate))

    cand = candidate()
    changed_assessment = assessment(cand).to_dict()
    changed_assessment["runtime_instance_id"] = None
    assert list(validator.iter_errors(changed_assessment))

    changed_admission = compile_local_voice_catalog_admission(cand, assessment(cand)).admission.to_dict()
    changed_admission["reason_codes"] = ["FIXTURE_ONLY_SOURCE"]
    assert list(validator.iter_errors(changed_admission))


def test_source_surface_is_effect_free_and_public_records_contain_no_private_material() -> None:
    source = (ROOT / "src" / "ai_video_production" / "task100_local_voice_catalog_admission.py").read_text(encoding="utf-8")
    for forbidden_import in ("import os", "import subprocess", "import socket", "from pathlib", "requests", "urllib"):
        assert forbidden_import not in source
    compiled = compile_local_voice_catalog_admission(candidate(), assessment(candidate()))
    encoded = json.dumps(compiled.admission.to_dict(), sort_keys=True)
    for forbidden in ("C:\\\\", "/home/", "private_key", "reference_audio", "transcript_body", "credential"):
        assert forbidden not in encoded
