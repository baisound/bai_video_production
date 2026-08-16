from __future__ import annotations

import ast
from copy import deepcopy
from importlib import resources
import json
from pathlib import Path

import jsonschema
import pytest

from ai_video_production.serialization import sha256_bytes
from ai_video_production.voice_quality_gain_admission import (
    AdmissionClassification,
    CanonicalMeasurementBinding,
    CanonicalRecordBinding,
    ContractState,
    GainAdmissionContext,
    GainReceiptValidationError,
    MeasurementFactValidity,
    ProcessingClass,
    QualityState,
    canonical_sha256,
    classify_gain_receipt,
    parse_gain_admission_report,
    to_public_dict,
)


ROOT = Path(__file__).parents[1]


def h(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def source_receipt(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema": "bvp.task047.local-gain-check-receipt.v1",
        "terminal_reason": "GAIN_CHECK_COMPLETE",
        "started_at_utc": "2026-08-16T12:00:00.0000000Z",
        "finished_at_utc": "2026-08-16T12:00:10.0000000Z",
        "measurement_fact_state": "MEASURED",
        "signal_integrity_state": "MEASURED_NO_CLIPPING",
        "gain_admission_state": "UNKNOWN_POLICY_NOT_BOUND",
        "recommendation": "NO_AUTOMATIC_RECOMMENDATION",
        "sample_peak_dbfs": -6.021,
        "rms_dbfs": -18.125,
        "clip_threshold_abs": 0.9999,
        "clip_sample_count": 0,
        "non_finite_sample_count": 0,
        "measured_sample_values": 480_000,
        "received_bytes": 1_920_000,
        "audio_body_persisted": False,
        "hardware_setting_changed": False,
        "session_key_persisted": False,
    }
    value.update(updates)
    return value


def record_binding(state: ContractState = ContractState.CANONICAL_REF_NOT_PROVIDED, name: str = "record") -> CanonicalRecordBinding:
    bound = state is ContractState.BOUND_VERIFIED
    return CanonicalRecordBinding(
        contract_state=state,
        record_ref=f"{name}-1" if bound else None,
        record_sha256=h(name) if bound else None,
        evidence_sha256=h(f"{name}-evidence") if bound else None,
    )


def measurement_binding(state: ContractState = ContractState.CANONICAL_REF_NOT_PROVIDED) -> CanonicalMeasurementBinding:
    bound = state is ContractState.BOUND_VERIFIED
    return CanonicalMeasurementBinding(
        contract_state=state,
        measurement_input_range_ref="range-1" if bound else None,
        measurement_input_range_sha256=h("range-1") if bound else None,
        canonical_mapping_receipt_ref="mapping-1" if bound else None,
        canonical_mapping_receipt_sha256=h("mapping-1") if bound else None,
        sample_rate=48_000 if bound else None,
        bit_depth=24 if bound else None,
        channels=1 if bound else None,
        processing_class=ProcessingClass.CANONICAL_CONVERTED_RAW if bound else None,
    )


def context(state: ContractState = ContractState.CANONICAL_REF_NOT_PROVIDED) -> GainAdmissionContext:
    return GainAdmissionContext(
        measurement_binding=measurement_binding(state),
        capture_chain_binding=record_binding(state, "capture-chain"),
        analyzer_profile_binding=record_binding(state, "analyzer-profile"),
        quality_policy_binding=record_binding(state, "quality-policy"),
    )


def schema() -> dict[str, object]:
    return json.loads((ROOT / "schemas" / "voice-quality-gain-admission.schema.json").read_text(encoding="utf-8"))


def test_unbound_valid_measurement_stays_unknown() -> None:
    report = classify_gain_receipt(source_receipt(), context())
    assert report.classification is AdmissionClassification.MEASURED_FACTS_POLICY_OR_CHAIN_UNBOUND
    assert report.measurement_fact_validity is MeasurementFactValidity.VALID
    assert report.quality_state is QualityState.UNKNOWN
    assert report.to_dict()["canonical_pqc_quality_receipt_issued"] is False


def test_all_exact_bindings_only_make_input_ready_for_later_evaluation() -> None:
    report = classify_gain_receipt(source_receipt(), context(ContractState.BOUND_VERIFIED))
    assert report.classification is AdmissionClassification.READY_FOR_CANONICAL_PQC_EVALUATION
    assert report.quality_state is QualityState.UNKNOWN
    assert report.to_dict()["canonical_pqc_measurement_receipt_issued"] is False


def test_clipping_recommends_rerecord_even_when_context_bound() -> None:
    receipt = source_receipt(
        signal_integrity_state="FAIL_CLIPPING", clip_sample_count=4,
        recommendation="LOWER_HARDWARE_GAIN_PROPOSAL", sample_peak_dbfs=0.25,
    )
    report = classify_gain_receipt(receipt, context(ContractState.BOUND_VERIFIED))
    assert report.classification is AdmissionClassification.RERECORD_RECOMMENDED_CLIPPING
    assert report.quality_state is QualityState.RERECORD_RECOMMENDED
    assert report.to_dict()["gain_change_authorized"] is False


def test_nonfinite_error_is_invalid_and_never_passes() -> None:
    receipt = source_receipt(
        measurement_fact_state="ERROR_NON_FINITE_SAMPLE",
        non_finite_sample_count=1,
    )
    report = classify_gain_receipt(receipt, context(ContractState.BOUND_VERIFIED))
    assert report.classification is AdmissionClassification.INVALID_MEASUREMENT
    assert report.measurement_fact_validity is MeasurementFactValidity.INVALID_INPUT
    assert report.quality_state is QualityState.FAIL


def test_insufficient_input_is_unknown_not_zero() -> None:
    receipt = source_receipt(
        measurement_fact_state="INSUFFICIENT_INPUT", signal_integrity_state="UNKNOWN",
        sample_peak_dbfs=None, rms_dbfs=None, measured_sample_values=0, received_bytes=0,
    )
    report = classify_gain_receipt(receipt, context())
    assert report.measurement_fact_validity is MeasurementFactValidity.UNKNOWN
    assert report.to_dict()["measured_linear_zero"] is False


def test_genuine_measured_silence_is_distinct_from_unknown() -> None:
    receipt = source_receipt(sample_peak_dbfs=None, rms_dbfs=None)
    report = classify_gain_receipt(receipt, context())
    assert report.measurement_fact_validity is MeasurementFactValidity.VALID
    assert report.to_dict()["measured_linear_zero"] is True


@pytest.mark.parametrize("field", ["schema", "terminal_reason", "sample_peak_dbfs"])
def test_missing_source_field_rejected(field: str) -> None:
    receipt = source_receipt()
    del receipt[field]
    with pytest.raises(GainReceiptValidationError, match="fields") as error:
        classify_gain_receipt(receipt, context())
    assert error.value.code == "REJECTED_INVALID_RECEIPT"


def test_unknown_source_field_rejected() -> None:
    with pytest.raises(ValueError, match="fields"):
        classify_gain_receipt(source_receipt(secret_path="private"), context())


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_numeric_json_value_rejected(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        classify_gain_receipt(source_receipt(sample_peak_dbfs=value), context())


@pytest.mark.parametrize("field", ["audio_body_persisted", "hardware_setting_changed", "session_key_persisted"])
def test_source_effect_flag_cannot_be_forged(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        classify_gain_receipt(source_receipt(**{field: True}), context())


def test_source_cannot_claim_policy_admission() -> None:
    with pytest.raises(ValueError, match="policy admission"):
        classify_gain_receipt(source_receipt(gain_admission_state="PASS"), context())


def test_inconsistent_clipping_and_recommendation_rejected() -> None:
    with pytest.raises(ValueError, match="clipping facts"):
        classify_gain_receipt(source_receipt(clip_sample_count=1), context())


@pytest.mark.parametrize(
    "updates,match",
    [
        ({"finished_at_utc": "2026-08-16T11:59:59Z"}, "precede"),
        ({"clip_threshold_abs": 1.0}, "controller constant"),
        ({"clip_sample_count": 480_001, "signal_integrity_state": "FAIL_CLIPPING", "recommendation": "LOWER_HARDWARE_GAIN_PROPOSAL"}, "cannot exceed"),
        ({"received_bytes": 0}, "received bytes"),
        ({"recommendation": "LOWER_HARDWARE_GAIN_PROPOSAL"}, "recommendation"),
    ],
)
def test_hosted_controller_cross_field_invariants(updates: dict[str, object], match: str) -> None:
    with pytest.raises(GainReceiptValidationError, match=match):
        classify_gain_receipt(source_receipt(**updates), context())


def test_peak_rms_relation_rejected() -> None:
    with pytest.raises(ValueError, match="RMS"):
        classify_gain_receipt(source_receipt(sample_peak_dbfs=-20.0, rms_dbfs=-10.0), context())


def test_unprovided_binding_cannot_smuggle_reference() -> None:
    with pytest.raises(ValueError, match="cannot contain"):
        CanonicalRecordBinding(ContractState.CANONICAL_REF_NOT_PROVIDED, "fake", None, None)


def test_bound_record_requires_evidence_not_opaque_sha_alone() -> None:
    with pytest.raises(ValueError):
        CanonicalRecordBinding(ContractState.BOUND_VERIFIED, "record-1", h("record"), None)


@pytest.mark.parametrize("rate,bits,channels", [(44_100, 24, 1), (48_000, 16, 1), (48_000, 24, 2)])
def test_bound_measurement_requires_exact_canonical_mapping(rate: int, bits: int, channels: int) -> None:
    with pytest.raises(ValueError, match="48000"):
        CanonicalMeasurementBinding(
            ContractState.BOUND_VERIFIED, "range-1", h("range"), "map-1", h("map"),
            rate, bits, channels, ProcessingClass.CANONICAL_CONVERTED_RAW,
        )


def test_mismatch_dominates_unbound_context() -> None:
    mixed = GainAdmissionContext(
        measurement_binding=measurement_binding(),
        capture_chain_binding=CanonicalRecordBinding(ContractState.MISMATCH, None, None, None),
        analyzer_profile_binding=record_binding(),
        quality_policy_binding=record_binding(),
    )
    assert classify_gain_receipt(source_receipt(), mixed).classification is AdmissionClassification.MISMATCH


def test_report_schema_and_parser_round_trip() -> None:
    document = classify_gain_receipt(source_receipt(), context(ContractState.BOUND_VERIFIED)).to_dict()
    jsonschema.Draft202012Validator(schema()).validate(document)
    parsed = parse_gain_admission_report(document)
    assert parsed.to_dict() == document


def test_report_tamper_rejected() -> None:
    document = classify_gain_receipt(source_receipt(), context()).to_dict()
    document["quality_state"] = "FAIL"
    with pytest.raises(ValueError, match="inconsistent|tampered"):
        parse_gain_admission_report(document)


def test_classification_tamper_rejected_even_with_recomputed_outer_hash() -> None:
    document = classify_gain_receipt(source_receipt(), context()).to_dict()
    document["classification"] = "READY_FOR_CANONICAL_PQC_EVALUATION"
    body = dict(document)
    body.pop("gain_receipt_admission_report_sha256")
    document["gain_receipt_admission_report_sha256"] = canonical_sha256(body)
    with pytest.raises(ValueError, match="inconsistent|tampered"):
        parse_gain_admission_report(document)


def test_report_cannot_forge_effect_flag() -> None:
    document = classify_gain_receipt(source_receipt(), context()).to_dict()
    document["analyzer_executed"] = True
    with pytest.raises(ValueError, match="must remain false"):
        parse_gain_admission_report(document)


def test_report_digest_is_deterministic() -> None:
    first = classify_gain_receipt(source_receipt(), context()).to_dict()
    second = classify_gain_receipt(dict(reversed(list(source_receipt().items()))), context()).to_dict()
    assert first["source_receipt_sha256"] == second["source_receipt_sha256"]
    assert first["gain_receipt_admission_report_sha256"] == second["gain_receipt_admission_report_sha256"]
    body = dict(first)
    digest = body.pop("gain_receipt_admission_report_sha256")
    assert digest == canonical_sha256(body)


def test_public_projection_suppresses_private_refs_times_and_byte_counts() -> None:
    projection = to_public_dict(classify_gain_receipt(source_receipt(), context(ContractState.BOUND_VERIFIED)))
    serialized = json.dumps(projection, sort_keys=True)
    for forbidden in ("record_ref", "mapping-1", "range-1", "started_at_utc", "finished_at_utc", "received_bytes"):
        assert forbidden not in serialized
    assert projection["canonical_pqc_receipts_issued"] is False


def test_public_and_resource_schema_are_byte_exact() -> None:
    public = ROOT / "schemas" / "voice-quality-gain-admission.schema.json"
    resource = ROOT / "src" / "ai_video_production" / "schema_resources" / "voice-quality-gain-admission.schema.json"
    assert public.read_bytes() == resource.read_bytes()
    assert resources.files("ai_video_production.schema_resources").joinpath("voice-quality-gain-admission.schema.json").read_bytes() == public.read_bytes()


def test_schema_rejects_unknown_property_and_forged_pass() -> None:
    validator = jsonschema.Draft202012Validator(schema())
    document = classify_gain_receipt(source_receipt(), context()).to_dict()
    forged = deepcopy(document)
    forged["quality_state"] = "PASS"
    assert list(validator.iter_errors(forged))
    extra = deepcopy(document)
    extra["audio_path"] = "private.wav"
    assert list(validator.iter_errors(extra))


def test_module_has_no_filesystem_audio_process_network_or_effect_surface() -> None:
    module_path = ROOT / "src" / "ai_video_production" / "voice_quality_gain_admission.py"
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert imports.isdisjoint({"os", "pathlib", "subprocess", "socket", "wave", "audioop", "numpy", "requests"})
    source = module_path.read_text(encoding="utf-8").lower()
    for forbidden in ("open(", "write_bytes", "write_text", "file.write", "popen", "run(", "urlopen", "obs_frontend"):
        assert forbidden not in source
