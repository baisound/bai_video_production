from __future__ import annotations

import ast
from dataclasses import replace
from importlib import resources
import json
from pathlib import Path

import jsonschema
import pytest

from ai_video_production.serialization import sha256_bytes
from ai_video_production.voice_quality_calibration import (
    BODY_AUTHORITY_FLAGS,
    CANONICAL_SERIALIZED_TYPES,
    AdditionalRecordingRecommendationRevision,
    AnalyzerProfileRevision,
    ApprovedStyleLanguageEmotionCoverageIndicator,
    CalibrationProfileRevision,
    CalibrationSessionRevision,
    CaptureChainRevision,
    CaptureChainStage,
    CaptureChainStageKind,
    CaptureEvidenceBinding,
    ContractState,
    CoverageIntervalEntry,
    DatasetReadinessIndicator,
    DriftComparisonReceipt,
    DurationCoverageIndicator,
    GainRecommendationRevision,
    HalfOpenSampleInterval,
    HumanInputBinding,
    MeasurementFactValidity,
    MeasurementInputRangeBinding,
    MeasurementReceipt,
    MeasurementSourceClass,
    MetricFact,
    MetricInputKind,
    MetricInputReference,
    MetricInputRole,
    MetricInputSetBinding,
    MetricValueState,
    ModelEvaluationReadinessIndicator,
    PrivacyPolicyBinding,
    ProcessingClass,
    QualityEvaluationReceipt,
    QualityPolicyRevision,
    QualityState,
    RXDerivedQualityBinding,
    RationalSampleDuration,
    RawAcousticQualityCoverageIndicator,
    RecommendationState,
    RecordReference,
    StagingToTask003AssetPromotionBinding,
    calculate_coverage_indicator,
    classify_quality_evaluation,
    clone_with_new_revision,
    parse_voice_quality_record,
    project_pvs3a_calibration_binding,
    to_public_dict,
    union_eligible_intervals,
    validate_append_only_revision,
    validate_capture_chain,
    validate_measurement_receipt,
    validate_metric_input_set,
    validate_readiness_axes,
    validate_revision_cas,
)


ROOT = Path(__file__).parents[1]
NOW = "2026-08-15T13:00:00Z"
LATER = "2026-08-15T14:00:00Z"


def h(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def base() -> dict[str, object]:
    return {
        "project_id": "project-opaque-1",
        "revision": 1,
        "parent_revision_sha256": None,
        "created_at": NOW,
        "body_authority_flags": BODY_AUTHORITY_FLAGS,
    }


def stages() -> tuple[CaptureChainStage, ...]:
    kinds = tuple(CaptureChainStageKind)
    digests = [h(f"stage-{index}") for index in range(1, 9)]
    rows: list[CaptureChainStage] = []
    for index, kind in enumerate(kinds, start=1):
        endpoint = kind is CaptureChainStageKind.DRIVER_OS_ENDPOINT
        rows.append(CaptureChainStage(
            stage_index=index,
            stage_kind=kind,
            stage_id=f"stage-{index}",
            stage_revision=1,
            stage_sha256=digests[index - 1],
            settings_sha256=h(f"settings-{index}"),
            processing_state="OBSERVED",
            phantom_power_observation_state="OBSERVED" if kind is CaptureChainStageKind.MIC_PAD_HPF else "NOT_APPLICABLE",
            pad_observation_state="OBSERVED" if kind is CaptureChainStageKind.MIC_PAD_HPF else "NOT_APPLICABLE",
            hpf_observation_state="OBSERVED" if kind is CaptureChainStageKind.MIC_PAD_HPF else "NOT_APPLICABLE",
            preamp_gain_observation_state="OBSERVED" if kind is CaptureChainStageKind.INTERFACE_ANALOGUE_PREAMP else "NOT_APPLICABLE",
            hidden_processing_state="CLEAR",
            gain_role="PRIMARY" if kind is CaptureChainStageKind.INTERFACE_ANALOGUE_PREAMP else "NONE",
            previous_stage_sha256=None if index == 1 else digests[index - 2],
            next_stage_sha256=None if index == 8 else digests[index],
            evidence_ref=f"stage-evidence-{index}",
            evidence_sha256=h(f"stage-evidence-{index}"),
            stable_private_ref="endpoint-private-1" if endpoint else None,
            stable_private_ref_sha256=h("endpoint-private-1") if endpoint else None,
            observed_display_name="Owner OBS endpoint" if endpoint else None,
        ))
    return tuple(rows)


def chain(*, state: QualityState = QualityState.PASS) -> CaptureChainRevision:
    return CaptureChainRevision(
        **base(), capture_chain_id="capture-chain-1", sample_rate=48_000,
        bit_depth=24, channels=1, stages=stages(), calibration_state=state,
        human_input_binding_sha256=h("human-input"),
    )


def privacy(*, bound: bool = True, details: bool = False) -> PrivacyPolicyBinding:
    return PrivacyPolicyBinding(
        **base(), privacy_policy_binding_id="privacy-binding-1",
        contract_state=ContractState.BOUND_VERIFIED if bound else ContractState.CANONICAL_REF_NOT_PROVIDED,
        policy_ref="privacy-policy-1" if bound else None,
        policy_sha256=h("privacy-policy-1") if bound else None,
        public_detail_state="POLICY_AUTHORIZED" if details else "SUPPRESSED",
        public_detail_allowed=details,
        low_count_suppression_evidence_sha256=h("low-count") if details else None,
    )


def policy(*, percentage_bound: bool = True, conflict_rule: str = "FAIL_WINS") -> QualityPolicyRevision:
    p = privacy()
    return QualityPolicyRevision(
        **base(), quality_policy_id="quality-policy-1", use_case_scope="TRAINING_SOURCE",
        metric_rules_sha256=h("metric-rules"), precedence_rule="EXACT_CURRENT_ONLY",
        conflict_rule=conflict_rule,
        percentage_policy_state=ContractState.BOUND_VERIFIED if percentage_bound else ContractState.CANONICAL_REF_NOT_PROVIDED,
        target_percentage_basis_points=9_500 if percentage_bound else None,
        privacy_policy_binding_sha256=p.sha256,
        default_valid_decision=QualityState.PASS,
    )


def analyzer() -> AnalyzerProfileRevision:
    return AnalyzerProfileRevision(
        **base(), analyzer_profile_id="analyzer-profile-1", analyzer_name="synthetic-analyzer",
        analyzer_version="1.0.0", code_sha256=h("analyzer-code"),
        supported_metrics=("SAMPLE_PEAK", "RMS", "SNR"),
        capability_evidence_sha256=h("analyzer-capability"),
        contract_state=ContractState.BOUND_VERIFIED,
    )


def calibration_profile(*, processing: ProcessingClass = ProcessingClass.RAW_PRE_FILTER) -> CalibrationProfileRevision:
    c = chain()
    return CalibrationProfileRevision(
        **base(), calibration_profile_id=f"calibration-profile-{processing.value.lower()}",
        capture_chain_revision_sha256=c.sha256, scenario="NORMAL_VOICE",
        processing_class=processing, sample_rate=48_000, bit_depth=24, channels=1,
        policy_scope="training-source",
    )


def staging_source(*, disposition: str = "ACTIVE", state: ContractState = ContractState.BOUND_VERIFIED) -> dict[str, object]:
    bound = state is ContractState.BOUND_VERIFIED
    return {
        "contract_state": state.value,
        "capture_evidence_binding_ref": "capture-evidence-1" if bound else None,
        "capture_evidence_binding_sha256": h("capture-evidence-1") if bound else None,
        "encrypted_staging_object_ref": "staging-object-private-1" if bound else None,
        "staging_object_sha256": h("staging-object-private-1") if bound else None,
        "canonical_mapping_receipt_ref": "sample-map-1" if bound else None,
        "canonical_mapping_receipt_sha256": h("sample-map-1") if bound else None,
        "retention_expires_at": LATER if bound else None,
        "disposition": disposition,
        "reverification_state": "AVAILABLE" if disposition == "ACTIVE" and bound else ("UNAVAILABLE" if disposition in {"EXPIRED", "DELETED"} else "UNKNOWN"),
        "dataset_adoption_permitted": False,
        "asset_publication_permitted": False,
        "training_use_permitted": False,
    }


def asset_source(*, state: ContractState = ContractState.BOUND_VERIFIED) -> dict[str, object]:
    bound = state is ContractState.BOUND_VERIFIED
    return {
        "contract_state": state.value,
        "asset_id": "ASSET-01HZX123456789ABCDEFGHJKMNP" if bound else None,
        "asset_checksum_sha256": h("asset-bytes") if bound else None,
        "asset_record_evidence_sha256": h("asset-record") if bound else None,
        "asset_revision_binding_ref": "task003-asset-revision-1" if bound else None,
        "asset_revision_binding_sha256": h("task003-mapping") if bound else None,
        "official_mapping_state": "BOUND" if bound else "UNBOUND_PENDING_TASK003",
    }


def measurement_range(
    range_id: str = "range-signal",
    start: int = 0,
    end: int = 48_000,
    *,
    source_class: MeasurementSourceClass = MeasurementSourceClass.CALIBRATION_STAGING_EVIDENCE,
    processing: ProcessingClass = ProcessingClass.RAW_PRE_FILTER,
) -> MeasurementInputRangeBinding:
    c = chain()
    return MeasurementInputRangeBinding(
        **base(), measurement_input_range_id=range_id, source_class=source_class,
        processing_class=processing, sample_rate=48_000, bit_depth=24, channels=1,
        interval=HalfOpenSampleInterval(start, end), canonical_mapping_sha256=h(f"mapping-{range_id}"),
        capture_chain_revision_sha256=c.sha256,
        source_binding=staging_source() if source_class is MeasurementSourceClass.CALIBRATION_STAGING_EVIDENCE else asset_source(),
    )


def input_set(
    ranges: tuple[MeasurementInputRangeBinding, ...] | None = None,
    *,
    kind: MetricInputKind = MetricInputKind.SINGLE_RANGE,
    purpose: str = "SAMPLE_PEAK",
    roles: tuple[MetricInputRole, ...] = (MetricInputRole.TARGET,),
) -> MetricInputSetBinding:
    rows = ranges or (measurement_range(),)
    return MetricInputSetBinding(
        **base(), metric_input_set_id=f"input-set-{purpose.lower()}", input_kind=kind,
        purpose=purpose,
        input_refs=tuple(MetricInputReference(role, item.measurement_input_range_id, item.sha256) for role, item in zip(roles, rows, strict=True)),
        analyzer_profile_revision_sha256=analyzer().sha256,
        calibration_profile_revision_sha256=calibration_profile().sha256,
        quality_policy_revision_sha256=policy().sha256,
        compatibility_state=QualityState.PASS,
    )


def fact(*, state: MetricValueState = MetricValueState.MEASURED, value: int | float | None = 0, error: str | None = None) -> MetricFact:
    inputs = input_set()
    return MetricFact(
        **base(), metric_fact_id=f"metric-fact-{state.value.lower()}",
        metric_input_set_sha256=inputs.sha256, metric_name="SAMPLE_PEAK", unit="DBFS",
        value_state=state, value=value, error_code=error, evidence_sha256=h(f"fact-{state.value}"),
    )


def measurement_receipt(*, validity: MeasurementFactValidity = MeasurementFactValidity.VALID) -> MeasurementReceipt:
    inputs = input_set()
    item = fact()
    return MeasurementReceipt(
        **base(), measurement_receipt_id="measurement-receipt-1", measured_at=NOW,
        metric_input_set_ref=inputs.metric_input_set_id, metric_input_set_sha256=inputs.sha256,
        analyzer_profile_ref=analyzer().analyzer_profile_id,
        analyzer_profile_revision_sha256=analyzer().sha256,
        calibration_profile_revision_sha256=inputs.calibration_profile_revision_sha256,
        capture_chain_revision_sha256=chain().sha256,
        metric_fact_refs=(RecordReference(item.metric_fact_id, item.sha256),),
        fact_validity=validity, current=True, tampered=False,
    )


def evaluation(*, result: QualityState = QualityState.PASS) -> QualityEvaluationReceipt:
    receipt = measurement_receipt()
    return QualityEvaluationReceipt(
        **base(), quality_evaluation_receipt_id=f"quality-evaluation-{result.value.lower()}", evaluated_at=LATER,
        measurement_receipt_refs=(RecordReference(receipt.measurement_receipt_id, receipt.sha256),),
        receipt_index_sha256=h("receipt-index"), analyzer_profile_ref=analyzer().analyzer_profile_id,
        analyzer_profile_revision_sha256=analyzer().sha256,
        quality_policy_ref=policy().quality_policy_id, quality_policy_revision_sha256=policy().sha256,
        capture_chain_revision_sha256=chain().sha256, result=result,
        reason_codes=("POLICY_EVALUATED",), precedence_digest=h("precedence"),
        conflict_state="CLEAR" if result is not QualityState.UNKNOWN else "UNKNOWN",
    )


def coverage_kwargs(*, state: QualityState = QualityState.PASS, bound: bool = True) -> dict[str, object]:
    return {
        "state": state if bound else QualityState.UNKNOWN,
        "policy_ref": "quality-policy-1",
        "policy_revision_sha256": policy().sha256,
        "numerator_sample_count": 24_000,
        "denominator_sample_count": 48_000,
        "percentage_basis_points": 5_000 if bound else None,
        "percentage_policy_state": ContractState.BOUND_VERIFIED if bound else ContractState.CANONICAL_REF_NOT_PROVIDED,
    }


def axes() -> tuple[object, ...]:
    duration = DurationCoverageIndicator(
        **base(), **coverage_kwargs(), duration_coverage_indicator_id="duration-axis-1",
        eligible_interval_index_sha256=h("duration-index"),
    )
    labels = ApprovedStyleLanguageEmotionCoverageIndicator(
        **base(), **coverage_kwargs(), approved_style_language_emotion_coverage_indicator_id="labels-axis-1",
        approved_label_index_ref="pvs3a-approved-label-index-1", approved_label_index_sha256=h("labels-index"),
        upstream_truth_recomputed=False,
    )
    acoustic = RawAcousticQualityCoverageIndicator(
        **base(), **coverage_kwargs(), raw_acoustic_quality_coverage_indicator_id="acoustic-axis-1",
        processing_class=ProcessingClass.RAW_PRE_FILTER, policy_scope="training-source",
        current_receipt_index_sha256=h("current-receipt-index"), eligible_interval_index_sha256=h("eligible-index"),
        conflict_state="CLEAR",
    )
    dataset = DatasetReadinessIndicator(
        **base(), dataset_readiness_indicator_id="dataset-axis-1",
        duration_axis_ref=RecordReference(duration.duration_coverage_indicator_id, duration.sha256),
        approved_coverage_axis_ref=RecordReference(labels.approved_style_language_emotion_coverage_indicator_id, labels.sha256),
        acoustic_quality_axis_ref=RecordReference(acoustic.raw_acoustic_quality_coverage_indicator_id, acoustic.sha256),
        policy_ref="dataset-readiness-policy-1", policy_revision_sha256=h("dataset-policy"),
        state=QualityState.UNKNOWN, percentage_basis_points=None, arithmetic_average_used=False,
        upstream_truth_recomputed=False,
    )
    model = ModelEvaluationReadinessIndicator(
        **base(), model_evaluation_readiness_indicator_id="model-axis-1",
        duration_axis_ref=RecordReference(duration.duration_coverage_indicator_id, duration.sha256),
        approved_coverage_axis_ref=RecordReference(labels.approved_style_language_emotion_coverage_indicator_id, labels.sha256),
        acoustic_quality_axis_ref=RecordReference(acoustic.raw_acoustic_quality_coverage_indicator_id, acoustic.sha256),
        dataset_readiness_ref=RecordReference(dataset.dataset_readiness_indicator_id, dataset.sha256),
        evaluation_policy_ref="model-evaluation-policy-1", evaluation_policy_sha256=h("model-policy"),
        state=QualityState.UNKNOWN, percentage_basis_points=None, arithmetic_average_used=False,
        model_effect_authorized=False,
    )
    return duration, labels, acoustic, dataset, model


def all_records() -> tuple[object, ...]:
    c = chain()
    cp = calibration_profile()
    qp = policy()
    ap = analyzer()
    session = CalibrationSessionRevision(
        **base(), calibration_session_id="calibration-session-1", state="DRAFT",
        capture_chain_revision_sha256=c.sha256, calibration_profile_revision_sha256=cp.sha256,
        quality_policy_revision_sha256=qp.sha256, analyzer_profile_revision_sha256=ap.sha256,
        human_input_binding_sha256=h("human-input"), capture_evidence_binding_sha256=h("capture-evidence"),
        production_admission=False,
    )
    source_range = measurement_range()
    promotion = StagingToTask003AssetPromotionBinding(
        **base(), promotion_binding_id="promotion-binding-1",
        contract_state=ContractState.CANONICAL_REF_NOT_PROVIDED,
        staging_input_range_sha256=None, asset_mapping_ref=None, asset_mapping_sha256=None,
        owner_decision_ref=None, owner_decision_sha256=None, effect_receipt_ref=None,
        effect_receipt_sha256=None, source_object_state_mutated=False, effect_issued_by_pqc=False,
    )
    inputs = input_set()
    metric = fact()
    receipt = measurement_receipt()
    quality = evaluation()
    capture = CaptureEvidenceBinding(
        **base(), capture_evidence_binding_id="capture-evidence-1",
        contract_state=ContractState.CANONICAL_REF_NOT_PROVIDED,
        capture_receipt_ref=None, capture_receipt_sha256=None, staging_owner_ref=None,
        staging_owner_sha256=None, evidence_state=QualityState.UNKNOWN,
        callback_bounded_copy_only=True, analyzer_in_callback=False,
    )
    rx = RXDerivedQualityBinding(
        **base(), rx_derived_quality_binding_id="rx-derived-1",
        contract_state=ContractState.CANONICAL_REF_NOT_PROVIDED,
        source_asset_ref=None, source_asset_sha256=None, derived_asset_ref=None,
        derived_asset_sha256=None, rx_version_ref=None, rx_version_sha256=None,
        module_preset_parameter_sha256=None, render_receipt_ref=None, render_receipt_sha256=None,
        before_measurement_receipt_sha256=None, after_measurement_receipt_sha256=None,
        source_overwritten=False, raw_delete_authorized=False, dataset_adoption_authorized=False,
    )
    human = HumanInputBinding(
        **base(), human_input_binding_id="human-input-1",
        contract_state=ContractState.CANONICAL_REF_NOT_PROVIDED,
        human_input_ref=None, human_input_sha256=None, input_state="UNKNOWN",
        required_answers_sha256=None, hardware_change_authorized=False,
        owner_voice_recording_authorized=False,
    )
    gain = GainRecommendationRevision(
        **base(), gain_recommendation_id="gain-recommendation-1", state=RecommendationState.PROPOSED,
        capture_chain_revision_sha256=c.sha256, measurement_receipt_sha256=receipt.sha256,
        quality_policy_revision_sha256=qp.sha256, proposed_stage_id="stage-2",
        proposed_change_sha256=h("gain-change"), human_confirmation_binding_sha256=human.sha256,
        device_setting_change_authorized=False,
    )
    extra = AdditionalRecordingRecommendationRevision(
        **base(), additional_recording_recommendation_id="recording-recommendation-1",
        state=RecommendationState.PROPOSED,
        readiness_axis_refs=(RecordReference("duration-axis-1", h("duration-axis")),),
        reason_codes=("MISSING_WHISPER_COVERAGE",), estimated_duration=RationalSampleDuration(48_000),
        proposed_coverage_sha256=h("proposed-coverage"), human_confirmation_binding_sha256=human.sha256,
        recording_plan_mutation_authorized=False,
    )
    drift = DriftComparisonReceipt(
        **base(), drift_comparison_receipt_id="drift-1", compared_at=LATER,
        before_capture_chain_sha256=c.sha256, after_capture_chain_sha256=c.sha256,
        before_profile_sha256=cp.sha256, after_profile_sha256=cp.sha256,
        before_measurement_receipt_sha256=receipt.sha256, after_measurement_receipt_sha256=receipt.sha256,
        paired_metric_input_set_sha256=h("paired-input"), result=QualityState.UNKNOWN, raw_fact_mutated=False,
    )
    return (
        c, cp, qp, ap, session, source_range, promotion, inputs, metric, receipt, quality,
        capture, rx, privacy(), human, gain, extra, drift, *axes(),
    )


def schema() -> dict[str, object]:
    return json.loads((ROOT / "schemas" / "voice-quality-calibration.schema.json").read_text(encoding="utf-8"))


def test_pqc_sch_001_003_canonical_23_schema_roundtrip_and_mirror() -> None:
    canonical = (ROOT / "schemas" / "voice-quality-calibration.schema.json").read_bytes()
    packaged = resources.files("ai_video_production").joinpath(
        "schema_resources", "voice-quality-calibration.schema.json"
    ).read_bytes()
    assert canonical == packaged
    jsonschema.Draft202012Validator.check_schema(json.loads(canonical))
    records = all_records()
    assert len(records) == 23
    assert tuple(record.record_type for record in records) == CANONICAL_SERIALIZED_TYPES
    validator = jsonschema.Draft202012Validator(schema(), format_checker=jsonschema.FormatChecker())
    for record in records:
        payload = record.to_private_dict()
        validator.validate(payload)
        assert parse_voice_quality_record(payload) == record
        tampered = dict(payload)
        tampered[record.hash_field] = h("tampered")
        with pytest.raises(ValueError, match="checksum mismatch"):
            parse_voice_quality_record(tampered)


def test_pqc_sch_002_alias_unknown_and_additional_property_rejected() -> None:
    record = all_records()[0].to_private_dict()
    record["record_type"] = "GainRecommendation"
    with pytest.raises(ValueError, match="unknown"):
        parse_voice_quality_record(record)
    record = all_records()[0].to_private_dict()
    record["raw_audio_path"] = "C:/private/audio.wav"
    with pytest.raises(ValueError, match="incomplete or unknown"):
        parse_voice_quality_record(record)


def test_pqc_sch_004_state_dependent_nullability_fails_closed() -> None:
    validator = jsonschema.Draft202012Validator(schema())
    capture = all_records()[11].to_private_dict()
    capture["capture_receipt_ref"] = "forged-receipt"
    capture["capture_receipt_sha256"] = h("forged-receipt")
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(capture)
    unknown_fact = fact(state=MetricValueState.UNKNOWN, value=None).to_private_dict()
    unknown_fact["value"] = 0
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(unknown_fact)
    unbound = DurationCoverageIndicator(
        **base(), **coverage_kwargs(bound=False), duration_coverage_indicator_id="unbound-schema-axis",
        eligible_interval_index_sha256=h("unbound-schema-axis"),
    ).to_private_dict()
    unbound["percentage_basis_points"] = 0
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(unbound)


def test_pqc_met_001_004_genuine_zero_and_fact_states_are_not_collapsed() -> None:
    assert fact().value == 0
    for state in (
        MetricValueState.DECLARED,
        MetricValueState.NOT_SUPPORTED,
        MetricValueState.INSUFFICIENT_INPUT,
        MetricValueState.UNKNOWN,
    ):
        item = fact(state=state, value=None)
        assert item.value is None
        assert item.value_state is state
    error = fact(state=MetricValueState.ERROR, value=None, error="ANALYZER_ERROR")
    assert error.value is None
    with pytest.raises(ValueError, match="non-MEASURED"):
        fact(state=MetricValueState.UNKNOWN, value=0)
    assert measurement_receipt(validity=MeasurementFactValidity.INVALID_INPUT).fact_validity is MeasurementFactValidity.INVALID_INPUT
    assert classify_quality_evaluation(
        [measurement_receipt(validity=MeasurementFactValidity.INVALID_INPUT)], policy()
    ).state is QualityState.FAIL


def test_pqc_chn_001_007_exact_stage_lineage_and_hidden_processing_fail_closed() -> None:
    validate_capture_chain(chain())
    broken = list(stages())
    with pytest.raises(ValueError, match="display name"):
        replace(broken[2], stable_private_ref=None, stable_private_ref_sha256=None)
    broken = list(stages())
    broken[5] = replace(broken[5], hidden_processing_state="UNKNOWN")
    with pytest.raises(ValueError, match="hidden processing"):
        CaptureChainRevision(
            **base(), capture_chain_id="chain-hidden", sample_rate=48_000, bit_depth=24,
            channels=1, stages=tuple(broken), calibration_state=QualityState.PASS,
            human_input_binding_sha256=h("human"),
        )
    broken = list(stages())
    broken[5] = replace(broken[5], gain_role="PRIMARY")
    with pytest.raises(ValueError, match="duplicate primary gain"):
        CaptureChainRevision(
            **base(), capture_chain_id="chain-double", sample_rate=48_000, bit_depth=24,
            channels=1, stages=tuple(broken), calibration_state=QualityState.UNKNOWN,
            human_input_binding_sha256=h("human"),
        )
    with pytest.raises(ValueError, match="auto-change"):
        replace(stages()[0], automatic_change_authorized=True)
    hardware_unknown = list(stages())
    hardware_unknown[0] = replace(hardware_unknown[0], phantom_power_observation_state="UNKNOWN")
    with pytest.raises(ValueError, match="hidden processing"):
        CaptureChainRevision(
            **base(), capture_chain_id="chain-phantom-unknown", sample_rate=48_000,
            bit_depth=24, channels=1, stages=tuple(hardware_unknown),
            calibration_state=QualityState.PASS, human_input_binding_sha256=h("human"),
        )


def test_pqc_inp_001_007_staging_asset_and_promotion_boundaries() -> None:
    assert measurement_range().source_class is MeasurementSourceClass.CALIBRATION_STAGING_EVIDENCE
    assert measurement_range(source_class=MeasurementSourceClass.TASK003_ASSET_REVISION).source_binding["official_mapping_state"] == "BOUND"
    expired = staging_source(disposition="EXPIRED")
    expired["reverification_state"] = "AVAILABLE"
    with pytest.raises(ValueError, match="re-verifiable"):
        MeasurementInputRangeBinding(
            **base(), measurement_input_range_id="expired-range",
            source_class=MeasurementSourceClass.CALIBRATION_STAGING_EVIDENCE,
            processing_class=ProcessingClass.RAW_PRE_FILTER, sample_rate=48_000, bit_depth=24,
            channels=1, interval=HalfOpenSampleInterval(0, 48_000),
            canonical_mapping_sha256=h("expired-map"), capture_chain_revision_sha256=chain().sha256,
            source_binding=expired,
        )
    adoption = staging_source()
    adoption["training_use_permitted"] = True
    with pytest.raises(ValueError, match="adopted/published/trained"):
        replace(measurement_range(), source_binding=adoption)
    bad_asset = asset_source()
    bad_asset["official_mapping_state"] = "MISMATCH"
    with pytest.raises(ValueError, match="official mapping"):
        replace(measurement_range(source_class=MeasurementSourceClass.TASK003_ASSET_REVISION), source_binding=bad_asset)
    with pytest.raises(ValueError, match="cannot mutate/promote"):
        replace(all_records()[6], source_object_state_mutated=True)


def test_pqc_set_001_007_single_snr_and_before_after_compatibility() -> None:
    target = measurement_range()
    single = input_set((target,))
    validate_metric_input_set(
        single, {target.measurement_input_range_id: target}, {chain().capture_chain_id: chain()},
        {calibration_profile().calibration_profile_id: calibration_profile()}, policy(),
    )
    signal = measurement_range("signal", 0, 48_000)
    noise = measurement_range("noise", 48_000, 96_000)
    snr = input_set((signal, noise), kind=MetricInputKind.ORDERED_MULTI_RANGE, purpose="SNR", roles=(MetricInputRole.SIGNAL, MetricInputRole.NOISE))
    validate_metric_input_set(
        snr, {"signal": signal, "noise": noise}, {chain().capture_chain_id: chain()},
        {calibration_profile().calibration_profile_id: calibration_profile()}, policy(),
    )
    with pytest.raises(ValueError, match="SIGNAL then NOISE"):
        input_set((signal, noise), kind=MetricInputKind.ORDERED_MULTI_RANGE, purpose="SNR", roles=(MetricInputRole.NOISE, MetricInputRole.SIGNAL))
    before = measurement_range("before")
    after = measurement_range("after")
    paired = input_set((before, after), kind=MetricInputKind.PAIRED_BEFORE_AFTER, purpose="BEFORE_AFTER", roles=(MetricInputRole.BEFORE, MetricInputRole.AFTER))
    validate_metric_input_set(
        paired, {"before": before, "after": after}, {chain().capture_chain_id: chain()},
        {calibration_profile().calibration_profile_id: calibration_profile()}, policy(),
    )
    with pytest.raises(ValueError, match="multi-range"):
        input_set((signal,), purpose="SNR")


def test_pqc_cov_001_009_union_dedup_conflict_and_integer_rational() -> None:
    receipt = evaluation()
    entries = [
        CoverageIntervalEntry(h("source"), ProcessingClass.RAW_PRE_FILTER, "training-source", HalfOpenSampleInterval(0, 48_000), receipt.sha256, QualityState.PASS, policy().sha256, True, False, "retry-1"),
        CoverageIntervalEntry(h("source"), ProcessingClass.RAW_PRE_FILTER, "training-source", HalfOpenSampleInterval(24_000, 72_000), receipt.sha256, QualityState.PASS, policy().sha256, True, False, "retry-1"),
        CoverageIntervalEntry(h("source"), ProcessingClass.RX_DERIVED, "training-source", HalfOpenSampleInterval(0, 48_000), receipt.sha256, QualityState.PASS, policy().sha256, True, False, "retry-2"),
    ]
    result = union_eligible_intervals([receipt], entries, policy())
    assert result.state is QualityState.PASS
    assert len(result.intervals_by_index) == 2
    raw = next(value for key, value in result.intervals_by_index.items() if "RAW_PRE_FILTER" in key)
    assert raw == (HalfOpenSampleInterval(0, 72_000),)
    calculation = calculate_coverage_indicator(raw, (HalfOpenSampleInterval(0, 96_000),), ProcessingClass.RAW_PRE_FILTER, "training-source")
    assert calculation.numerator_sample_count == 72_000
    assert calculation.percentage_basis_points == 7_500
    with pytest.raises(ValueError, match="outside"):
        calculate_coverage_indicator((HalfOpenSampleInterval(0, 96_001),), (HalfOpenSampleInterval(0, 96_000),), ProcessingClass.RAW_PRE_FILTER, "training-source")
    conflict_policy = policy(conflict_rule="UNKNOWN")
    conflict_receipt = replace(receipt, quality_evaluation_receipt_id="quality-fail", result=QualityState.FAIL, reason_codes=("FAIL",))
    conflict_entries = [
        replace(entries[0], policy_revision_sha256=conflict_policy.sha256),
        replace(entries[0], receipt_sha256=conflict_receipt.sha256, receipt_state=QualityState.FAIL, policy_revision_sha256=conflict_policy.sha256),
    ]
    assert union_eligible_intervals([receipt, conflict_receipt], conflict_entries, conflict_policy).state is QualityState.UNKNOWN


def test_pqc_axs_001_003_axes_are_independent_and_never_averaged() -> None:
    typed = axes()
    validate_readiness_axes(typed)
    with pytest.raises(ValueError, match="exactly once"):
        validate_readiness_axes(typed[:-1])
    with pytest.raises(ValueError, match="never averages"):
        replace(typed[3], arithmetic_average_used=True)
    unbound = DurationCoverageIndicator(
        **base(), **coverage_kwargs(bound=False), duration_coverage_indicator_id="duration-unbound",
        eligible_interval_index_sha256=h("duration-unbound"),
    )
    assert unbound.percentage_basis_points is None and unbound.state is QualityState.UNKNOWN


def test_pqc_rec_rx_001_002_proposals_and_rx_never_apply_effects() -> None:
    gain = all_records()[15]
    extra = all_records()[16]
    rx = all_records()[12]
    assert gain.device_setting_change_authorized is False
    assert extra.recording_plan_mutation_authorized is False
    assert rx.source_overwritten is rx.raw_delete_authorized is rx.dataset_adoption_authorized is False
    with pytest.raises(ValueError, match="proposal-only"):
        replace(gain, device_setting_change_authorized=True)
    with pytest.raises(ValueError, match="replace/delete/adopt"):
        replace(rx, dataset_adoption_authorized=True)


def test_pqc_cas_001_003_append_only_exact_cas_and_unknown_no_effect() -> None:
    first = chain()
    second = clone_with_new_revision(first, created_at=LATER, calibration_state=QualityState.UNKNOWN)
    validate_append_only_revision(first, second)
    validate_revision_cas(first, second, first.sha256)
    with pytest.raises(ValueError, match="stale"):
        validate_revision_cas(first, second, h("stale"))
    with pytest.raises(ValueError, match="lineage"):
        validate_append_only_revision(first, replace(second, parent_revision_sha256=h("wrong")))
    assert BODY_AUTHORITY_FLAGS["capture_or_staging_write_authorized"] is False
    assert BODY_AUTHORITY_FLAGS["analyzer_execution_authorized"] is False


def test_pqc_pvs_001_003_exact_pvs3a_projection_and_fail_closed_mapping() -> None:
    receipt = measurement_receipt()
    passed = evaluation(result=QualityState.PASS)
    projection = project_pvs3a_calibration_binding(passed, analyzer(), policy(), chain(), [receipt])
    assert projection == {
        "contract_state": "BOUND_VERIFIED",
        "analyzer_profile_ref": "analyzer-profile-1",
        "analyzer_profile_sha256": analyzer().sha256,
        "calibration_receipt_ref": passed.quality_evaluation_receipt_id,
        "calibration_receipt_sha256": passed.sha256,
        "result": "PASS",
        "threshold_profile_revision": "quality-policy-1",
        "capture_chain_sha256": chain().sha256,
        "measured_at": NOW,
    }
    rerecord = evaluation(result=QualityState.RERECORD_RECOMMENDED)
    assert project_pvs3a_calibration_binding(rerecord, analyzer(), policy(), chain(), [receipt])["result"] == "FAIL"
    mismatch = project_pvs3a_calibration_binding(passed, replace(analyzer(), analyzer_version="2.0.0"), policy(), chain(), [receipt])
    assert mismatch["contract_state"] == "MISMATCH" and mismatch["result"] == "UNKNOWN"
    unresolved = project_pvs3a_calibration_binding(None, None, None, None)
    assert unresolved == {
        "contract_state": "CANONICAL_REF_NOT_PROVIDED", "analyzer_profile_ref": None,
        "analyzer_profile_sha256": None, "calibration_receipt_ref": None,
        "calibration_receipt_sha256": None, "result": None,
        "threshold_profile_revision": None, "capture_chain_sha256": None, "measured_at": None,
    }


def test_pqc_pri_001_002_unbound_policy_suppresses_counts_ranges_and_private_refs() -> None:
    public = to_public_dict(axes()[2], privacy(bound=False))
    assert public["privacy_policy_contract_state"] == "CANONICAL_REF_NOT_PROVIDED"
    assert public["public_detail_allowed"] is False
    for private in (
        "numerator_sample_count", "denominator_sample_count", "percentage_basis_points",
        "current_receipt_index_sha256", "eligible_interval_index_sha256",
    ):
        assert private not in public


def test_pqc_srf_001_module_has_no_external_effect_surface() -> None:
    source_path = ROOT / "src" / "ai_video_production" / "voice_quality_calibration.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported.isdisjoint({"os", "pathlib", "subprocess", "socket", "requests", "soundfile", "wave", "obs", "rx", "cmake"})
    forbidden_calls = {"open", "write", "unlink", "mkdir", "remove", "rmdir", "system", "run", "Popen"}
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert called.isdisjoint(forbidden_calls)
    assert "cmake" not in source_path.read_text(encoding="utf-8").lower()
