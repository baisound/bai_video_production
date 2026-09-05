from __future__ import annotations

from dataclasses import fields, replace
import math
import threading

import pytest

from ai_video_production.voice_quality_audio_finishing import (
    AudioFormat,
    BoundaryMode,
    CaptureChainBinding,
    CaptureCondition,
    ChannelStrategy,
    ClassificationState,
    DeterministicFixtureAudioRunner,
    DenoisePairMeasurement,
    EnvironmentABPlan,
    EnvironmentCaptureBinding,
    EnvironmentMeasurementBundle,
    EnvironmentSegmentMeasurement,
    FinishingContractError,
    FixtureEffectReadback,
    FixtureVoiceQualityAudioFinishingService,
    GeneratedFinishingPlan,
    OperationAlreadyConsumedError,
    OperationKind,
    QAState,
    QualityMeasurements,
    NoiseBandProfile,
    ReasonCode,
    SourceSnapshot,
    SegmentEligibility,
    SampleRange,
    SpeechContinuityPolicy,
    SpeechContinuousReadback,
    SpeechEvidenceInterval,
    StrictWavDecodeEvidence,
    TrainingCopyPlan,
    TrainingFormatPolicy,
    VoiceEffort,
    IntervalClass,
    plan_speech_continuous,
)


def digest(char: str) -> str:
    return "sha256:" + char * 64


def source(**changes: object) -> SourceSnapshot:
    values = {
        "source_ref": "recording-source-01",
        "source_sha256": digest("1"),
        "source_identity_sha256": digest("2"),
        "terminal_receipt_sha256": digest("3"),
        "terminal_receipt_owner": "TASK-047",
        "terminal_receipt_type": "TASK047_FINALIZED_RECORDING_READBACK_V1",
        "terminal_receipt_current": True,
        "source_size_bytes": 144_000,
        "sample_count": 96_000,
        "source_format": AudioFormat(),
        "regular_file": True,
        "single_link": True,
        "no_reparse": True,
        "ancestor_current": True,
        "identity_current": True,
        "read_current": True,
        "write_closed_verified": True,
        "wav_complete": True,
    }
    values.update(changes)
    return SourceSnapshot(**values)  # type: ignore[arg-type]


def measurements(**changes: object) -> QualityMeasurements:
    values = {
        "integrated_lufs": -16.1,
        "true_peak_dbtp": -1.2,
        "loudness_range_lu": 4.0,
        "clipped_sample_count": 0,
        "snr_db": 28.0,
        "silence_ratio": 0.1,
        "speech_duration_seconds": 1.8,
        "speech_ratio": 0.9,
        "dropout_count": 0,
        "dc_offset_abs": 0.001,
        "other_speaker_state": ClassificationState.PASS,
        "bgm_state": ClassificationState.PASS,
    }
    values.update(changes)
    return QualityMeasurements(**values)  # type: ignore[arg-type]


def readback(**changes: object) -> FixtureEffectReadback:
    values = {
        "output_sha256": digest("4"),
        "output_identity_sha256": digest("5"),
        "output_format": AudioFormat(),
        "output_sample_count": 96_000,
        "exact_range_applied": True,
        "readback_verified": True,
        "directory_durable": True,
        "raw_source_preserved": True,
        "external_effect_count": 0,
    }
    values.update(changes)
    return FixtureEffectReadback(**values)  # type: ignore[arg-type]


def runner(*, generated=None, training=None, environment=None, speech=None) -> DeterministicFixtureAudioRunner:
    return DeterministicFixtureAudioRunner(
        runner_build_sha256=digest("6"),
        generated_result=generated,
        training_result=training,
        environment_result=environment,
        speech_result=speech,
    )


def generated_plan(**changes: object) -> GeneratedFinishingPlan:
    values = {
        "operation_id": "finish/op-1",
        "project_id": "project-1",
        "project_manifest_sha256": digest("c"),
        "installed_session_sha256": digest("d"),
        "operation_plan_sha256": digest("e"),
        "quick_clone_flow_sha256": digest("f"),
        "source": source(
            terminal_receipt_sha256=None,
            terminal_receipt_owner=None,
            terminal_receipt_type=None,
            terminal_receipt_current=False,
        ),
        "runner_build_sha256": digest("6"),
        "analyzer_profile_sha256": digest("7"),
        "start_sample": 0,
        "end_sample": 96_000,
    }
    values.update(changes)
    return GeneratedFinishingPlan(**values)  # type: ignore[arg-type]


def training_plan(**changes: object) -> TrainingCopyPlan:
    values = {
        "operation_id": "copy/op-1",
        "project_id": "project-1",
        "project_manifest_sha256": digest("c"),
        "installed_session_sha256": digest("d"),
        "operation_plan_sha256": digest("e"),
        "quick_clone_flow_sha256": digest("f"),
        "source": source(),
        "runner_build_sha256": digest("6"),
        "analyzer_profile_sha256": digest("7"),
        "engine_recipe_sha256": digest("8"),
        "consent_receipt_sha256": digest("9"),
        "review_receipt_sha256": digest("a"),
        "canonical_input_receipt_sha256": digest("b"),
        "transport_format_receipt_sha256": digest("0"),
        "capture_chain_receipt_sha256": digest("1"),
        "consent_current": True,
        "review_current": True,
        "canonical_input_current": True,
        "start_sample": 0,
        "end_sample": 96_000,
    }
    values.update(changes)
    return TrainingCopyPlan(**values)  # type: ignore[arg-type]


def capture_chain(**changes: object) -> CaptureChainBinding:
    values = {
        "microphone_sha256": digest("2"),
        "filter_chain_sha256": digest("3"),
        "gain_sha256": digest("4"),
        "transport_format_sha256": digest("5"),
        "sample_rate_hz": 48_000,
        "channels": 1,
        "current": True,
    }
    values.update(changes)
    return CaptureChainBinding(**values)  # type: ignore[arg-type]


def capture(condition: CaptureCondition, **changes: object) -> EnvironmentCaptureBinding:
    values = {
        "session_id": "session-off" if condition is CaptureCondition.AIR_CONDITIONER_OFF else "session-on",
        "condition": condition,
        "capture_receipt_sha256": digest("6") if condition is CaptureCondition.AIR_CONDITIONER_OFF else digest("7"),
        "room_tone_receipt_sha256": digest("8") if condition is CaptureCondition.AIR_CONDITIONER_OFF else digest("9"),
        "source_sha256": digest("a") if condition is CaptureCondition.AIR_CONDITIONER_OFF else digest("b"),
        "source_identity_sha256": digest("0") if condition is CaptureCondition.AIR_CONDITIONER_OFF else digest("1"),
        "capture_generation_sha256": digest("2"),
        "room_tone_generation_sha256": digest("2"),
        "same_content_prompt_sha256": digest("3"),
        "prompt_revision": 1,
        "capture_receipt_current": True,
        "room_tone_receipt_current": True,
        "source_identity_current": True,
        "source_read_current": True,
        "source_ancestor_current": True,
        "capture_chain": capture_chain(),
    }
    values.update(changes)
    return EnvironmentCaptureBinding(**values)  # type: ignore[arg-type]


def environment_segment(condition: CaptureCondition, effort: VoiceEffort, **changes: object) -> EnvironmentSegmentMeasurement:
    values = {
        "condition": condition,
        "effort": effort,
        "source_sha256": digest("a") if condition is CaptureCondition.AIR_CONDITIONER_OFF else digest("b"),
        "source_identity_sha256": digest("0") if condition is CaptureCondition.AIR_CONDITIONER_OFF else digest("1"),
        "same_content_prompt_sha256": digest("3"),
        "prompt_revision": 1,
        "comparison_plan_sha256": digest("0"),
        "room_tone_noise_floor_dbfs": -54.0 if condition is CaptureCondition.AIR_CONDITIONER_OFF else -48.0,
        "speech_rms_dbfs": -20.0,
        "speech_peak_dbfs": -4.0,
        "clipped_sample_count": 0,
        "nonfinite_sample_count": 0,
        "dc_offset_abs": 0.001,
        "dropout_count": 0,
        "snr_db": 26.0,
        "snr_approximate": False,
        "speech_ratio": 0.8,
        "noise_profile": NoiseBandProfile(-60.0, -55.0, -58.0) if condition is CaptureCondition.AIR_CONDITIONER_OFF else NoiseBandProfile(-52.0, -50.0, -54.0),
        "current": True,
    }
    values.update(changes)
    return EnvironmentSegmentMeasurement(**values)  # type: ignore[arg-type]


def denoise_pair(condition: CaptureCondition, effort: VoiceEffort, **changes: object) -> DenoisePairMeasurement:
    source_sha = digest("a") if condition is CaptureCondition.AIR_CONDITIONER_OFF else digest("b")
    values = {
        "condition": condition,
        "effort": effort,
        "input_source_sha256": source_sha,
        "denoised_input_source_sha256": source_sha,
        "input_source_identity_sha256": digest("0") if condition is CaptureCondition.AIR_CONDITIONER_OFF else digest("1"),
        "denoised_input_source_identity_sha256": digest("0") if condition is CaptureCondition.AIR_CONDITIONER_OFF else digest("1"),
        "raw_artifact_sha256": digest("c"),
        "denoised_artifact_sha256": digest("d"),
        "noise_reduction_db": 4.0,
        "voice_distortion_ratio": 0.02,
        "overprocessing_state": ClassificationState.PASS,
        "current": True,
    }
    values.update(changes)
    return DenoisePairMeasurement(**values)  # type: ignore[arg-type]


def environment_bundle(*, segment_changes=None, pair_changes=None) -> EnvironmentMeasurementBundle:
    segment_changes = segment_changes or {}
    pair_changes = pair_changes or {}
    return EnvironmentMeasurementBundle(
        segments=tuple(
            environment_segment(condition, effort, **segment_changes.get((condition, effort), {}))
            for condition in CaptureCondition
            for effort in VoiceEffort
        ),
        denoise_pairs=tuple(
            denoise_pair(condition, effort, **pair_changes.get((condition, effort), {}))
            for condition in CaptureCondition
            for effort in VoiceEffort
        ),
    )


def environment_plan(**changes: object) -> EnvironmentABPlan:
    values = {
        "operation_id": "environment/op-1",
        "project_id": "project-1",
        "project_manifest_sha256": digest("e"),
        "installed_session_sha256": digest("f"),
        "operation_plan_sha256": digest("0"),
        "runner_build_sha256": digest("6"),
        "analyzer_profile_sha256": digest("7"),
        "quality_policy_sha256": digest("8"),
        "off_capture": capture(CaptureCondition.AIR_CONDITIONER_OFF),
        "on_capture": capture(CaptureCondition.AIR_CONDITIONER_ON),
    }
    values.update(changes)
    return EnvironmentABPlan(**values)  # type: ignore[arg-type]


def decode_evidence(**changes: object) -> StrictWavDecodeEvidence:
    values = {
        "source_sha256": digest("1"),
        "source_identity_sha256": digest("2"),
        "decoder_build_sha256": digest("3"),
        "sample_rate_hz": 48_000,
        "channels": 1,
        "sample_format": "PCM_S24LE",
        "sample_count_per_channel": 96_000,
        "riff_header_valid": True,
        "format_chunk_valid": True,
        "data_length_exact": True,
        "odd_chunks_validated": True,
        "nonfinite_sample_count": 0,
        "current": True,
    }
    values.update(changes)
    return StrictWavDecodeEvidence(**values)  # type: ignore[arg-type]


def format_policy(**changes: object) -> TrainingFormatPolicy:
    values = {
        "policy_receipt_sha256": digest("4"),
        "policy_current": True,
        "output_format": AudioFormat(),
        "channel_strategy": ChannelStrategy.MONO_PRESERVE,
        "selected_channel_index": None,
        "phase_audit_receipt_sha256": None,
        "resampler_build_sha256": digest("5"),
        "dither_policy_sha256": None,
        "lossy_codec": False,
    }
    values.update(changes)
    return TrainingFormatPolicy(**values)  # type: ignore[arg-type]


def continuity_policy(**changes: object) -> SpeechContinuityPolicy:
    values = {"policy_receipt_sha256": digest("6")}
    values.update(changes)
    return SpeechContinuityPolicy(**values)  # type: ignore[arg-type]


def speech_intervals(*, middle_class: IntervalClass = IntervalClass.NON_SPEECH, middle_end: int = 72_000):
    return (
        SpeechEvidenceInterval(SampleRange(0, 24_000), IntervalClass.SPEECH, 0.99, digest("7")),
        SpeechEvidenceInterval(SampleRange(24_000, middle_end), middle_class, 0.95, digest("8")),
        SpeechEvidenceInterval(SampleRange(middle_end, 96_000), IntervalClass.SPEECH, 0.99, digest("9")),
    )


def speech_plan(**changes: object):
    values = {
        "operation_id": "speech/op-1",
        "project_id": "project-1",
        "project_manifest_sha256": digest("a"),
        "installed_session_sha256": digest("b"),
        "operation_plan_sha256": digest("c"),
        "runner_build_sha256": digest("6"),
        "source": source(),
        "decode_evidence": decode_evidence(),
        "format_policy": format_policy(),
        "continuity_policy": continuity_policy(),
        "quality_measurements_sha256": digest("d"),
        "intervals": speech_intervals(),
    }
    values.update(changes)
    return plan_speech_continuous(**values)


def speech_readback(**changes: object) -> SpeechContinuousReadback:
    plan = speech_plan()
    values = {
        "output_sha256": digest("e"),
        "output_identity_sha256": digest("f"),
        "output_format": AudioFormat(),
        "output_sample_count": plan.output_sample_count,
        "boundary_mode": plan.boundary_mode,
        "boundary_count": plan.boundary_count,
        "crossfade_overlap_samples": plan.crossfade_overlap_samples,
        "boundary_evidence_sha256s": tuple(digest(str(index)) for index in range(plan.boundary_count)),
        "range_map_verified": True,
        "zero_cross_or_crossfade_verified": True,
        "speech_attack_preserved": True,
        "speech_tail_preserved": True,
        "partial_output_published": False,
        "readback_verified": True,
        "directory_durable": True,
        "raw_source_preserved": True,
        "external_effect_count": 0,
    }
    values.update(changes)
    return SpeechContinuousReadback(**values)  # type: ignore[arg-type]


def test_generated_fixture_pass_is_body_free_and_never_authority() -> None:
    fake = runner(generated=(measurements(), readback()))
    receipt = FixtureVoiceQualityAudioFinishingService(fake).finish_generated(generated_plan())

    assert receipt.state is QAState.PASS
    assert receipt.operation_kind is OperationKind.GENERATED_WAV_FINISH
    assert receipt.reason_codes == ()
    assert fake.calls == [(OperationKind.GENERATED_WAV_FINISH, "finish/op-1")]
    body = receipt.to_dict()
    assert body["receipt_type"] == "FIXTURE_OWNER_VOICE_TECHNICAL_QA_RECEIPT_V1"
    assert body["project_manifest_sha256"] == digest("c")
    assert body["installed_session_sha256"] == digest("d")
    assert body["operation_plan_sha256"] == digest("e")
    assert body["quick_clone_flow_sha256"] == digest("f")
    assert body["fixture_only"] is True
    assert body["authority_created"] is False
    assert body["production_eligible"] is False
    assert body["external_effect_count"] == 0
    assert body["audio_body_persisted"] is False
    assert body["transcript_body_persisted"] is False
    assert body["host_absolute_path_persisted"] is False
    assert body["dataset_adoption_started"] is False
    assert body["receipt_sha256"].startswith("sha256:")
    assert "C:\\" not in repr(body)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"head_tail_trim_only": False}, "head/tail"),
        ({"cleanup_chain": ("acompressor",)}, "cleanup chain"),
        ({"loudnorm_passes": 1}, "policy"),
        ({"target_lufs": -14.0}, "policy"),
        ({"target_true_peak_dbtp": 0.0}, "policy"),
    ],
)
def test_generated_policy_rejects_caller_effect_injection(changes: dict[str, object], message: str) -> None:
    with pytest.raises(FinishingContractError, match=message):
        generated_plan(**changes)


@pytest.mark.parametrize(
    ("source_change", "reason"),
    [
        ({"write_closed_verified": False}, ReasonCode.SOURCE_STILL_WRITING),
        ({"read_current": False}, ReasonCode.SOURCE_CURRENTNESS_UNKNOWN),
        ({"ancestor_current": False}, ReasonCode.SOURCE_CURRENTNESS_UNKNOWN),
        ({"identity_current": False}, ReasonCode.SOURCE_IDENTITY_CHANGED),
        ({"single_link": False}, ReasonCode.SOURCE_LINK_REJECTED),
        ({"no_reparse": False}, ReasonCode.SOURCE_LINK_REJECTED),
        ({"wav_complete": False}, ReasonCode.WAV_INVALID_OR_INCOMPLETE),
    ],
)
def test_unsafe_source_blocks_runner_and_preserves_raw(source_change: dict[str, object], reason: ReasonCode) -> None:
    fake = runner(generated=(measurements(), readback()))
    plan = generated_plan(source=source(terminal_receipt_sha256=None, **source_change))
    receipt = FixtureVoiceQualityAudioFinishingService(fake).finish_generated(plan)

    assert receipt.state is QAState.UNKNOWN if reason in {
        ReasonCode.SOURCE_STILL_WRITING,
        ReasonCode.SOURCE_CURRENTNESS_UNKNOWN,
    } else receipt.state is not QAState.PASS
    assert reason in receipt.reason_codes
    assert receipt.output_sha256 is None
    assert receipt.raw_source_preserved is True
    assert fake.calls == []


@pytest.mark.parametrize(
    ("measurement_change", "readback_change", "reason"),
    [
        ({"clipped_sample_count": 1}, {}, ReasonCode.CLIPPING_DETECTED),
        ({"integrated_lufs": -13.0}, {}, ReasonCode.LOUDNESS_OUT_OF_POLICY),
        ({"true_peak_dbtp": -0.5}, {}, ReasonCode.TRUE_PEAK_OUT_OF_POLICY),
        ({"loudness_range_lu": None}, {}, ReasonCode.LOUDNESS_RANGE_UNKNOWN),
        ({"loudness_range_lu": 12.0}, {}, ReasonCode.LOUDNESS_RANGE_OUT_OF_POLICY),
        ({"silence_ratio": 0.8}, {}, ReasonCode.SILENCE_EXCESSIVE),
        ({}, {"readback_verified": False}, ReasonCode.GENERATED_READBACK_MISMATCH),
        ({}, {"directory_durable": False}, ReasonCode.GENERATED_READBACK_MISMATCH),
    ],
)
def test_generated_quality_or_readback_failure_never_passes(measurement_change, readback_change, reason) -> None:
    fake = runner(generated=(measurements(**measurement_change), readback(**readback_change)))
    receipt = FixtureVoiceQualityAudioFinishingService(fake).finish_generated(generated_plan())
    assert receipt.state is not QAState.PASS
    assert reason in receipt.reason_codes


def test_runner_build_mismatch_burns_operation_before_effect() -> None:
    fake = runner(generated=(measurements(), readback()))
    service = FixtureVoiceQualityAudioFinishingService(fake)
    plan = generated_plan(runner_build_sha256=digest("b"))
    with pytest.raises(FinishingContractError, match="runner build"):
        service.finish_generated(plan)
    with pytest.raises(OperationAlreadyConsumedError):
        service.finish_generated(plan)
    assert fake.calls == []


def test_runner_exception_burns_operation_and_does_not_retry() -> None:
    fake = runner(generated=RuntimeError("private path and body must not escape"))
    service = FixtureVoiceQualityAudioFinishingService(fake)
    plan = generated_plan()
    with pytest.raises(FinishingContractError, match="fixture generated finishing failed"):
        service.finish_generated(plan)
    with pytest.raises(OperationAlreadyConsumedError):
        service.finish_generated(plan)
    assert len(fake.calls) == 1


@pytest.mark.parametrize("method", ["finish_generated", "prepare_training_copy"])
def test_runner_contract_exception_body_is_not_forwarded(method: str) -> None:
    leaked = FinishingContractError("LEAK_SENTINEL_PRIVATE_BODY")
    fake = runner(generated=leaked, training=leaked)
    service = FixtureVoiceQualityAudioFinishingService(fake)
    plan = generated_plan() if method == "finish_generated" else training_plan()
    with pytest.raises(FinishingContractError) as caught:
        getattr(service, method)(plan)
    assert "LEAK_SENTINEL" not in str(caught.value)
    assert caught.value.__cause__ is None


def test_training_copy_pass_is_separate_format_only_evidence() -> None:
    fake = runner(training=(measurements(), readback()))
    plan = training_plan()
    receipt = FixtureVoiceQualityAudioFinishingService(fake).prepare_training_copy(plan)

    assert plan.format_only is True
    assert plan.effects == ()
    assert receipt.state is QAState.PASS
    assert receipt.operation_kind is OperationKind.TRAINING_COPY_QA
    assert receipt.receipt_type == "VOICE_TRAINING_COPY_QA_RECEIPT_V1"
    assert receipt.engine_recipe_sha256 == digest("8")
    assert receipt.to_dict()["dataset_adoption_started"] is False
    assert fake.calls == [(OperationKind.TRAINING_COPY_QA, "copy/op-1")]


def test_training_copy_requires_terminal_recording_receipt() -> None:
    with pytest.raises(FinishingContractError, match="terminal recording receipt"):
        training_plan(source=source(
            terminal_receipt_sha256=None,
            terminal_receipt_owner=None,
            terminal_receipt_type=None,
            terminal_receipt_current=False,
        ))


@pytest.mark.parametrize(
    "changes",
    [
        {"source": source(terminal_receipt_owner="TASK-014")},
        {"source": source(terminal_receipt_type="OTHER_RECEIPT_V1")},
        {"source": source(terminal_receipt_current=False)},
        {"consent_current": False},
        {"review_current": False},
    ],
)
def test_training_copy_requires_exact_current_source_consent_and_review(changes) -> None:
    with pytest.raises(FinishingContractError):
        training_plan(**changes)


@pytest.mark.parametrize(
    ("measurement_change", "reason", "state"),
    [
        ({"clipped_sample_count": 2}, ReasonCode.CLIPPING_DETECTED, QAState.FAIL),
        ({"snr_db": 10.0}, ReasonCode.SNR_BELOW_POLICY, QAState.FAIL),
        ({"snr_db": None}, ReasonCode.SNR_UNKNOWN, QAState.UNKNOWN),
        ({"silence_ratio": 0.9}, ReasonCode.SILENCE_EXCESSIVE, QAState.FAIL),
        ({"speech_duration_seconds": 0.2}, ReasonCode.SPEECH_TOO_SHORT, QAState.FAIL),
        ({"speech_ratio": 0.2}, ReasonCode.SPEECH_RATIO_OUT_OF_POLICY, QAState.FAIL),
        ({"speech_ratio": None}, ReasonCode.SPEECH_RATIO_UNKNOWN, QAState.UNKNOWN),
        ({"dropout_count": 1}, ReasonCode.DROPOUT_DETECTED, QAState.FAIL),
        ({"dropout_count": None}, ReasonCode.DROPOUT_UNKNOWN, QAState.UNKNOWN),
        ({"dc_offset_abs": 0.02}, ReasonCode.DC_OFFSET_OUT_OF_POLICY, QAState.FAIL),
        ({"dc_offset_abs": None}, ReasonCode.DC_OFFSET_UNKNOWN, QAState.UNKNOWN),
        ({"other_speaker_state": ClassificationState.DETECTED}, ReasonCode.OTHER_SPEAKER_DETECTED, QAState.FAIL),
        ({"other_speaker_state": ClassificationState.UNKNOWN}, ReasonCode.OTHER_SPEAKER_UNVERIFIED, QAState.UNKNOWN),
        ({"bgm_state": ClassificationState.DETECTED}, ReasonCode.BGM_EXCESSIVE, QAState.FAIL),
        ({"bgm_state": ClassificationState.UNKNOWN}, ReasonCode.BGM_CLASSIFICATION_UNKNOWN, QAState.UNKNOWN),
    ],
)
def test_training_copy_closed_quality_axes(measurement_change, reason, state) -> None:
    fake = runner(training=(measurements(**measurement_change), readback()))
    receipt = FixtureVoiceQualityAudioFinishingService(fake).prepare_training_copy(training_plan())
    assert receipt.state is state
    assert reason in receipt.reason_codes


def test_training_copy_rejects_processing_and_invalid_range() -> None:
    with pytest.raises(FinishingContractError, match="format-only"):
        training_plan(effects=("loudnorm",))
    with pytest.raises(FinishingContractError, match="range"):
        training_plan(start_sample=96_000, end_sample=96_001)


@pytest.mark.parametrize(
    "changes",
    [
        {"canonical_input_current": False},
        {"source": source(source_format=None)},
        {"canonical_input_receipt_sha256": "not-a-digest"},
        {"transport_format_receipt_sha256": "not-a-digest"},
        {"capture_chain_receipt_sha256": "not-a-digest"},
    ],
)
def test_training_copy_requires_verified_canonical_input_and_transport(changes) -> None:
    with pytest.raises(FinishingContractError):
        training_plan(**changes)


def test_training_copy_exact_range_readback_is_required() -> None:
    fake = runner(training=(measurements(), readback(output_sample_count=95_999)))
    receipt = FixtureVoiceQualityAudioFinishingService(fake).prepare_training_copy(training_plan())
    assert receipt.state is QAState.FAIL
    assert ReasonCode.TRAINING_FORMAT_MISMATCH in receipt.reason_codes


def test_training_measurement_cannot_exceed_selected_range() -> None:
    fake = runner(training=(measurements(speech_duration_seconds=3.0), readback()))
    receipt = FixtureVoiceQualityAudioFinishingService(fake).prepare_training_copy(training_plan())
    assert receipt.state is QAState.FAIL
    assert ReasonCode.SPEECH_DURATION_OUT_OF_RANGE in receipt.reason_codes


def test_same_operation_id_cannot_cross_generated_and_training_purpose() -> None:
    fake = runner(generated=(measurements(), readback()), training=(measurements(), readback()))
    service = FixtureVoiceQualityAudioFinishingService(fake)
    service.finish_generated(generated_plan(operation_id="shared/op"))
    with pytest.raises(OperationAlreadyConsumedError):
        service.prepare_training_copy(training_plan(operation_id="shared/op"))


@pytest.mark.parametrize(
    ("method", "wrong_plan"),
    [
        ("finish_generated", training_plan(operation_id="wrong/generated")),
        ("prepare_training_copy", generated_plan(operation_id="wrong/training")),
    ],
)
def test_wrong_purpose_plan_is_rejected_before_runner(method, wrong_plan) -> None:
    fake = runner(generated=(measurements(), readback()), training=(measurements(), readback()))
    service = FixtureVoiceQualityAudioFinishingService(fake)
    with pytest.raises(FinishingContractError, match="plan type"):
        getattr(service, method)(wrong_plan)
    assert fake.calls == []


def test_plan_subclass_is_rejected_before_runner() -> None:
    class ForgedGeneratedPlan(GeneratedFinishingPlan):
        pass

    original = generated_plan()
    forged = ForgedGeneratedPlan(**{
        name: getattr(original, name)
        for name in original.__dataclass_fields__
    })
    fake = runner(generated=(measurements(), readback()))
    with pytest.raises(FinishingContractError, match="plan type"):
        FixtureVoiceQualityAudioFinishingService(fake).finish_generated(forged)
    assert fake.calls == []


def test_concurrent_double_call_executes_runner_once() -> None:
    entered = threading.Event()
    release = threading.Event()

    class BlockingRunner(DeterministicFixtureAudioRunner):
        def finish_generated(self, plan):
            self.calls.append((OperationKind.GENERATED_WAV_FINISH, plan.operation_id))
            entered.set()
            assert release.wait(timeout=2)
            return measurements(), readback()

    fake = BlockingRunner(runner_build_sha256=digest("6"))
    service = FixtureVoiceQualityAudioFinishingService(fake)
    plan = generated_plan()
    outcome: list[object] = []

    thread = threading.Thread(target=lambda: outcome.append(service.finish_generated(plan)))
    thread.start()
    assert entered.wait(timeout=2)
    with pytest.raises(OperationAlreadyConsumedError):
        service.finish_generated(plan)
    release.set()
    thread.join(timeout=2)
    assert len(outcome) == 1
    assert len(fake.calls) == 1


def test_nonfinite_measurements_and_noncanonical_format_are_rejected() -> None:
    with pytest.raises(FinishingContractError, match="finite"):
        measurements(snr_db=math.nan)
    with pytest.raises(FinishingContractError, match="PCM_S24LE"):
        AudioFormat(sample_rate_hz=44_100)


def test_fixture_readback_cannot_claim_external_effect_or_mutated_raw() -> None:
    with pytest.raises(FinishingContractError, match="external effect"):
        readback(external_effect_count=1)
    with pytest.raises(FinishingContractError, match="raw source preservation"):
        bad = replace(
            FixtureVoiceQualityAudioFinishingService(
                runner(generated=(measurements(), readback()))
            ).finish_generated(generated_plan()),
            raw_source_preserved=False,
        )
        assert bad


def test_public_receipt_copy_cannot_claim_incomplete_pass() -> None:
    receipt = FixtureVoiceQualityAudioFinishingService(
        runner(generated=(measurements(), readback()))
    ).finish_generated(generated_plan())
    with pytest.raises(FinishingContractError, match="complete durable output"):
        replace(
            receipt,
            output_sha256=None,
            output_identity_sha256=None,
            output_format=None,
            output_sample_count=None,
        )


def test_known_failure_takes_precedence_over_unknown_measurement() -> None:
    fake = runner(training=(measurements(clipped_sample_count=1, snr_db=None), readback()))
    receipt = FixtureVoiceQualityAudioFinishingService(fake).prepare_training_copy(training_plan())
    assert receipt.state is QAState.FAIL
    assert ReasonCode.CLIPPING_DETECTED in receipt.reason_codes
    assert ReasonCode.SNR_UNKNOWN in receipt.reason_codes


@pytest.mark.parametrize("unsafe_ref", ["C:/Users/user/voice.wav", "https://example.invalid/a", "../voice"])
def test_source_ref_is_opaque_not_a_path_or_uri(unsafe_ref: str) -> None:
    with pytest.raises(FinishingContractError, match="source_ref"):
        source(source_ref=unsafe_ref)


@pytest.mark.parametrize("unsafe_id", ["C:/Users/user", "https://example.invalid/a", "../operation"])
def test_public_identifiers_cannot_encode_paths_or_uris(unsafe_id: str) -> None:
    with pytest.raises(FinishingContractError, match="operation_id"):
        generated_plan(operation_id=unsafe_id)


def test_reconstructed_service_is_not_durable_authority() -> None:
    first = FixtureVoiceQualityAudioFinishingService(runner(generated=(measurements(), readback()))).finish_generated(generated_plan())
    second = FixtureVoiceQualityAudioFinishingService(runner(generated=(measurements(), readback()))).finish_generated(generated_plan())
    assert first.to_dict() == second.to_dict()
    assert first.authority_created is second.authority_created is False
    assert first.production_eligible is second.production_eligible is False


def test_service_rejects_runner_that_claims_authority() -> None:
    fake = runner(generated=(measurements(), readback()))
    fake.authority_created = True
    with pytest.raises(FinishingContractError, match="authority flags"):
        FixtureVoiceQualityAudioFinishingService(fake)


def test_environment_ab_compares_measurements_not_condition_labels() -> None:
    bundle = environment_bundle()
    fake = runner(environment=bundle)
    receipt = FixtureVoiceQualityAudioFinishingService(fake).compare_environment(environment_plan())

    assert receipt.comparison_state is QAState.PASS
    assert receipt.recommended_condition is None
    assert len(receipt.segment_assessments) == 6
    assert all(item.eligibility is SegmentEligibility.TRAINING_ELIGIBLE for item in receipt.segment_assessments)
    assert len(receipt.noise_deltas) == 3
    assert all(item.noise_floor_delta_dbfs == 6.0 for item in receipt.noise_deltas)
    body = receipt.to_dict()
    assert body["measurement_unit"] == "dBFS"
    assert body["dba_or_spl_claimed"] is False
    assert body["recommended_condition"] is None
    assert body["authority_created"] is False
    assert body["dataset_adoption_started"] is False
    assert "same_content_prompt_sha256" not in body
    assert "prompt_revision" not in body


def test_environment_chain_mismatch_is_not_comparable_and_skips_runner() -> None:
    mismatched = capture(
        CaptureCondition.AIR_CONDITIONER_ON,
        capture_chain=capture_chain(gain_sha256=digest("9")),
    )
    fake = runner(environment=environment_bundle())
    receipt = FixtureVoiceQualityAudioFinishingService(fake).compare_environment(
        environment_plan(on_capture=mismatched)
    )
    assert receipt.comparison_state is QAState.UNKNOWN
    assert receipt.reason_codes == (ReasonCode.AB_CHAIN_MISMATCH,)
    assert fake.calls == []


@pytest.mark.parametrize(
    "capture_changes",
    [
        {"same_content_prompt_sha256": digest("4")},
        {"prompt_revision": 2},
    ],
)
def test_environment_ab_requires_same_content_prompt_and_revision(capture_changes) -> None:
    mismatched = capture(CaptureCondition.AIR_CONDITIONER_ON, **capture_changes)
    fake = runner(environment=environment_bundle())
    receipt = FixtureVoiceQualityAudioFinishingService(fake).compare_environment(
        environment_plan(on_capture=mismatched)
    )

    assert receipt.comparison_state is QAState.UNKNOWN
    assert receipt.reason_codes == (ReasonCode.AB_CONTENT_PROMPT_MISMATCH,)
    assert receipt.measurement_bundle_sha256 is None
    assert fake.calls == []


@pytest.mark.parametrize(
    "segment_changes",
    [
        {"same_content_prompt_sha256": digest("4")},
        {"prompt_revision": 2},
        {"comparison_plan_sha256": digest("5")},
    ],
)
def test_environment_measurement_must_bind_prompt_revision_and_plan(segment_changes) -> None:
    key = (CaptureCondition.AIR_CONDITIONER_ON, VoiceEffort.NORMAL)
    receipt = FixtureVoiceQualityAudioFinishingService(
        runner(environment=environment_bundle(segment_changes={key: segment_changes}))
    ).compare_environment(environment_plan())

    assert receipt.comparison_state is QAState.UNKNOWN
    assert receipt.reason_codes == (ReasonCode.AB_MEASUREMENT_NOT_CURRENT,)
    assert receipt.measurement_bundle_sha256 is None
    assert receipt.segment_assessments == ()
    assert receipt.noise_deltas == ()


@pytest.mark.parametrize("prompt_revision", [True, 0, -1, 2**31])
def test_environment_prompt_revision_requires_bounded_positive_integer(prompt_revision) -> None:
    with pytest.raises(FinishingContractError, match="prompt_revision"):
        capture(CaptureCondition.AIR_CONDITIONER_OFF, prompt_revision=prompt_revision)


def test_environment_bundle_rejects_duplicate_effort_pair_and_missing_counterpart() -> None:
    bundle = environment_bundle()
    duplicate = bundle.segments[:-1] + (bundle.segments[0],)
    with pytest.raises(FinishingContractError, match="segment measurement set"):
        replace(bundle, segments=duplicate)


def test_environment_bundle_rejects_cross_effort_substitution() -> None:
    bundle = environment_bundle()
    substituted = list(bundle.segments)
    substituted[4] = replace(substituted[4], effort=VoiceEffort.WHISPER)
    with pytest.raises(FinishingContractError, match="segment measurement set"):
        replace(bundle, segments=tuple(substituted))


def test_environment_operation_replay_is_rejected_before_second_runner_call() -> None:
    fake = runner(environment=environment_bundle())
    service = FixtureVoiceQualityAudioFinishingService(fake)
    service.compare_environment(environment_plan())

    with pytest.raises(OperationAlreadyConsumedError):
        service.compare_environment(environment_plan())

    assert fake.calls == [(OperationKind.ENVIRONMENT_AB_QA, "environment/op-1")]


def test_environment_stale_capture_is_not_comparable() -> None:
    stale = capture(
        CaptureCondition.AIR_CONDITIONER_ON,
        capture_chain=capture_chain(current=False),
    )
    receipt = FixtureVoiceQualityAudioFinishingService(runner(environment=environment_bundle())).compare_environment(
        environment_plan(on_capture=stale)
    )
    assert receipt.comparison_state is QAState.UNKNOWN
    assert ReasonCode.AB_CAPTURE_NOT_CURRENT in receipt.reason_codes


@pytest.mark.parametrize(
    ("changes", "reason", "decision"),
    [
        ({"nonfinite_sample_count": 1}, ReasonCode.NONFINITE_SAMPLES, SegmentEligibility.REJECT),
        ({"clipped_sample_count": 1}, ReasonCode.CLIPPING_DETECTED, SegmentEligibility.REJECT),
        ({"dropout_count": 1}, ReasonCode.DROPOUT_DETECTED, SegmentEligibility.REJECT),
        ({"dc_offset_abs": 0.02}, ReasonCode.DC_OFFSET_OUT_OF_POLICY, SegmentEligibility.REJECT),
        ({"snr_db": 10.0}, ReasonCode.SNR_BELOW_POLICY, SegmentEligibility.REJECT),
        ({"snr_db": 18.0}, ReasonCode.SNR_BELOW_POLICY, SegmentEligibility.REVIEW),
        ({"snr_approximate": True}, ReasonCode.SNR_BELOW_POLICY, SegmentEligibility.REVIEW),
        ({"speech_ratio": 0.3}, ReasonCode.SPEECH_RATIO_OUT_OF_POLICY, SegmentEligibility.REJECT),
        ({"noise_profile": None}, ReasonCode.NOISE_PROFILE_UNKNOWN, SegmentEligibility.REVIEW),
    ],
)
def test_environment_segment_policy_is_effort_and_measurement_based(changes, reason, decision) -> None:
    key = (CaptureCondition.AIR_CONDITIONER_ON, VoiceEffort.WHISPER)
    fake = runner(environment=environment_bundle(segment_changes={key: changes}))
    receipt = FixtureVoiceQualityAudioFinishingService(fake).compare_environment(environment_plan())
    if changes.get("noise_profile") is None and "noise_profile" in changes:
        assert receipt.comparison_state is QAState.UNKNOWN
        assert ReasonCode.AB_MEASUREMENT_SET_INVALID in receipt.reason_codes
        return
    assessment = next(item for item in receipt.segment_assessments if (item.condition, item.effort) == key)
    assert assessment.eligibility is decision
    assert reason in assessment.reason_codes


@pytest.mark.parametrize("condition", list(CaptureCondition))
def test_environment_policy_threshold_edges_do_not_depend_on_air_conditioner_label(
    condition: CaptureCondition,
) -> None:
    key = (condition, VoiceEffort.WHISPER)

    def assess(changes: dict[str, object]):
        receipt = FixtureVoiceQualityAudioFinishingService(
            runner(environment=environment_bundle(segment_changes={key: changes}))
        ).compare_environment(environment_plan())
        assessment = next(
            item for item in receipt.segment_assessments
            if (item.condition, item.effort) == key
        )
        return assessment, receipt

    assessment, receipt = assess({
        "snr_db": 20.0,
        "speech_ratio": 0.5,
        "dc_offset_abs": 0.01,
    })
    assert assessment.eligibility is SegmentEligibility.TRAINING_ELIGIBLE
    assert receipt.recommended_condition is None

    assessment, receipt = assess({"snr_db": 15.0})
    assert assessment.eligibility is SegmentEligibility.REVIEW
    assert receipt.comparison_state is QAState.UNKNOWN
    assert receipt.recommended_condition is None

    for changes, reason in (
        ({"snr_db": 14.999}, ReasonCode.SNR_BELOW_POLICY),
        ({"speech_ratio": 0.499999}, ReasonCode.SPEECH_RATIO_OUT_OF_POLICY),
        ({"dc_offset_abs": 0.010001}, ReasonCode.DC_OFFSET_OUT_OF_POLICY),
    ):
        assessment, receipt = assess(changes)
        assert assessment.eligibility is SegmentEligibility.REJECT
        assert reason in assessment.reason_codes
        assert receipt.comparison_state is QAState.FAIL
        assert receipt.recommended_condition is None


def test_environment_denoise_improvement_and_distortion_are_separate() -> None:
    key = (CaptureCondition.AIR_CONDITIONER_ON, VoiceEffort.SHOUT)
    bundle = environment_bundle(pair_changes={key: {
        "noise_reduction_db": 8.0,
        "voice_distortion_ratio": 0.25,
        "overprocessing_state": ClassificationState.DETECTED,
    }})
    receipt = FixtureVoiceQualityAudioFinishingService(runner(environment=bundle)).compare_environment(environment_plan())
    assessment = next(item for item in receipt.denoise_assessments if (item.condition, item.effort) == key)
    assert assessment.eligibility is SegmentEligibility.REJECT
    assert ReasonCode.DENOISE_DISTORTION_RISK in assessment.reason_codes


def test_environment_denoise_wrong_input_invalidates_comparison() -> None:
    key = (CaptureCondition.AIR_CONDITIONER_OFF, VoiceEffort.NORMAL)
    bundle = environment_bundle(pair_changes={key: {"denoised_input_source_sha256": digest("f")}})
    receipt = FixtureVoiceQualityAudioFinishingService(runner(environment=bundle)).compare_environment(environment_plan())
    assert receipt.comparison_state is QAState.UNKNOWN
    assert ReasonCode.AB_MEASUREMENT_NOT_CURRENT in receipt.reason_codes


def test_environment_measurement_set_requires_all_six_effort_condition_pairs() -> None:
    full = environment_bundle()
    with pytest.raises(FinishingContractError, match="segment measurement set"):
        EnvironmentMeasurementBundle(segments=full.segments[:-1], denoise_pairs=full.denoise_pairs)


def test_environment_nonfinite_and_non_dbfs_values_are_rejected() -> None:
    with pytest.raises(FinishingContractError, match="finite"):
        NoiseBandProfile(math.nan, -50.0, -50.0)
    with pytest.raises(FinishingContractError, match="dBFS"):
        NoiseBandProfile(1.0, -50.0, -50.0)


@pytest.mark.parametrize(
    "changes",
    [
        {"room_tone_noise_floor_dbfs": math.nan},
        {"speech_rms_dbfs": math.inf},
        {"speech_peak_dbfs": -math.inf},
        {"snr_db": math.nan},
        {"dc_offset_abs": math.inf},
        {"speech_ratio": math.nan},
        {"speech_rms_dbfs": 0.1},
        {"speech_peak_dbfs": 0.1},
    ],
)
def test_uncalibrated_or_nonfinite_meter_scalars_cannot_enter_ab_evidence(changes) -> None:
    with pytest.raises(FinishingContractError):
        environment_segment(CaptureCondition.AIR_CONDITIONER_OFF, VoiceEffort.NORMAL, **changes)


def test_zero_dbfs_peak_is_a_level_fact_not_a_clipping_decision() -> None:
    key = (CaptureCondition.AIR_CONDITIONER_OFF, VoiceEffort.NORMAL)
    receipt = FixtureVoiceQualityAudioFinishingService(
        runner(environment=environment_bundle(segment_changes={key: {
            "speech_peak_dbfs": 0.0,
            "clipped_sample_count": 0,
        }}))
    ).compare_environment(environment_plan())
    assessment = next(
        item for item in receipt.segment_assessments
        if (item.condition, item.effort) == key
    )
    assert assessment.eligibility is SegmentEligibility.TRAINING_ELIGIBLE
    assert ReasonCode.CLIPPING_DETECTED not in assessment.reason_codes

    clipped = FixtureVoiceQualityAudioFinishingService(
        runner(environment=environment_bundle(segment_changes={key: {
            "speech_peak_dbfs": 0.0,
            "clipped_sample_count": 1,
        }}))
    ).compare_environment(environment_plan(operation_id="environment/op-zero-dbfs-clipped"))
    clipped_assessment = next(
        item for item in clipped.segment_assessments
        if (item.condition, item.effort) == key
    )
    assert clipped_assessment.eligibility is SegmentEligibility.REJECT
    assert ReasonCode.CLIPPING_DETECTED in clipped_assessment.reason_codes

    with pytest.raises(FinishingContractError, match="dBFS"):
        environment_segment(
            CaptureCondition.AIR_CONDITIONER_OFF,
            VoiceEffort.NORMAL,
            speech_peak_dbfs=math.nextafter(0.0, 1.0),
        )


def test_environment_receipt_never_promotes_dbfs_to_dba_or_spl() -> None:
    body = FixtureVoiceQualityAudioFinishingService(
        runner(environment=environment_bundle())
    ).compare_environment(environment_plan()).to_dict()
    assert body["measurement_unit"] == "dBFS"
    assert body["dba_or_spl_claimed"] is False
    assert body["recommended_condition"] is None
    assert not any("spl" in key.lower() and key != "dba_or_spl_claimed" for key in body)


def test_environment_comparison_burns_after_body_free_runner_failure() -> None:
    leaked = FinishingContractError("PRIVATE_CAPTURE_PATH")
    fake = runner(environment=leaked)
    service = FixtureVoiceQualityAudioFinishingService(fake)
    plan = environment_plan()
    with pytest.raises(FinishingContractError) as caught:
        service.compare_environment(plan)
    assert "PRIVATE_CAPTURE_PATH" not in str(caught.value)
    assert caught.value.__cause__ is None
    with pytest.raises(OperationAlreadyConsumedError):
        service.compare_environment(plan)


def test_environment_same_session_and_wrong_condition_are_rejected() -> None:
    with pytest.raises(FinishingContractError, match="distinct sessions"):
        environment_plan(on_capture=capture(CaptureCondition.AIR_CONDITIONER_ON, session_id="session-off"))
    with pytest.raises(FinishingContractError, match="exact OFF and ON"):
        environment_plan(off_capture=capture(CaptureCondition.AIR_CONDITIONER_ON))


def test_speech_continuity_removes_only_long_non_speech_with_padding() -> None:
    plan = speech_plan()
    assert plan.retained_ranges == (SampleRange(0, 30_000), SampleRange(69_600, 96_000))
    assert plan.removed_ranges == (SampleRange(30_000, 69_600),)
    assert plan.output_sample_count == 56_160
    assert plan.input_pcm_payload_bytes == 288_000
    assert plan.output_pcm_payload_bytes == 168_480
    assert plan.size_reduction_bytes == 119_520


@pytest.mark.parametrize(
    "intervals",
    [
        (SpeechEvidenceInterval(SampleRange(0, 96_000), IntervalClass.SPEECH, 1.0, digest("1")),),
        speech_intervals(middle_class=IntervalClass.UNCERTAIN),
        speech_intervals(middle_end=30_000),
    ],
)
def test_speech_continuity_preserves_continuous_speech_uncertain_audio_and_short_pause(intervals) -> None:
    plan = speech_plan(intervals=intervals)
    assert plan.retained_ranges == (SampleRange(0, 96_000),)
    assert plan.removed_ranges == ()
    assert plan.output_sample_count == 96_000
    assert plan.size_reduction_bytes == 0


@pytest.mark.parametrize("confidence", [0.0, 0.949999])
def test_low_confidence_non_speech_is_preserved_as_ambiguous(confidence: float) -> None:
    intervals = speech_intervals()
    low_confidence = replace(intervals[1], confidence=confidence)
    plan = speech_plan(intervals=(intervals[0], low_confidence, intervals[2]))
    assert plan.retained_ranges == (SampleRange(0, 96_000),)
    assert plan.removed_ranges == ()
    assert plan.size_reduction_bytes == 0


def test_confirmed_non_speech_confidence_boundary_is_closed_and_fixed() -> None:
    plan = speech_plan()
    assert plan.removed_ranges == (SampleRange(30_000, 69_600),)
    with pytest.raises(FinishingContractError, match="confidence is fixed"):
        continuity_policy(minimum_confirmed_non_speech_confidence=0.5)


@pytest.mark.parametrize(
    ("middle_end", "expected_removed", "expected_reduction_bytes"),
    [
        (71_999, (), 0),
        (72_000, (SampleRange(30_000, 69_600),), 119_520),
    ],
)
def test_long_non_speech_duration_threshold_is_exact_and_capacity_is_sample_derived(
    middle_end: int,
    expected_removed: tuple[SampleRange, ...],
    expected_reduction_bytes: int,
) -> None:
    plan = speech_plan(intervals=speech_intervals(middle_end=middle_end))
    assert plan.removed_ranges == expected_removed
    assert plan.size_reduction_bytes == expected_reduction_bytes
    assert plan.size_reduction_bytes == (
        sum(item.sample_count for item in plan.removed_ranges)
        + plan.crossfade_overlap_samples
    ) * 3


def test_speech_padding_preserves_attack_tail_and_hangover_around_long_silence() -> None:
    intervals = (
        SpeechEvidenceInterval(SampleRange(0, 48_000), IntervalClass.NON_SPEECH, 0.99, digest("1")),
        SpeechEvidenceInterval(SampleRange(48_000, 52_800), IntervalClass.SPEECH, 0.99, digest("2")),
        SpeechEvidenceInterval(SampleRange(52_800, 120_000), IntervalClass.NON_SPEECH, 0.99, digest("3")),
    )
    plan = speech_plan(
        source=source(sample_count=120_000),
        decode_evidence=decode_evidence(sample_count_per_channel=120_000),
        intervals=intervals,
    )
    assert plan.retained_ranges == (SampleRange(45_600, 58_800),)
    assert plan.removed_ranges == (
        SampleRange(0, 45_600),
        SampleRange(58_800, 120_000),
    )


def test_speech_plan_rejects_nonpartitioning_range_map_reconstruction() -> None:
    plan = speech_plan()
    with pytest.raises(FinishingContractError, match="partition"):
        replace(
            plan,
            retained_ranges=(SampleRange(0, 24_000),),
            removed_ranges=(SampleRange(30_000, 96_000),),
            boundary_count=0,
            crossfade_overlap_samples=0,
            output_sample_count=24_000,
        )
    with pytest.raises(FinishingContractError, match="exactly cover"):
        replace(
            plan,
            intervals=(
                SpeechEvidenceInterval(
                    SampleRange(0, 24_000),
                    IntervalClass.SPEECH,
                    1.0,
                    digest("1"),
                ),
            ),
        )
    with pytest.raises(FinishingContractError, match="source binding"):
        replace(plan, source=source(identity_current=False))


def test_all_silence_and_incomplete_vad_coverage_are_rejected() -> None:
    silence = (SpeechEvidenceInterval(SampleRange(0, 96_000), IntervalClass.NON_SPEECH, 1.0, digest("1")),)
    with pytest.raises(FinishingContractError, match="speech evidence"):
        speech_plan(intervals=silence)
    incomplete = (SpeechEvidenceInterval(SampleRange(0, 24_000), IntervalClass.SPEECH, 1.0, digest("1")),)
    with pytest.raises(FinishingContractError, match="exactly cover"):
        speech_plan(intervals=incomplete)


@pytest.mark.parametrize(
    "decode_change",
    [
        {"riff_header_valid": False},
        {"format_chunk_valid": False},
        {"data_length_exact": False},
        {"odd_chunks_validated": False},
        {"nonfinite_sample_count": 1},
        {"current": False},
    ],
)
def test_speech_continuity_requires_strict_current_wav_decode(decode_change) -> None:
    with pytest.raises(FinishingContractError, match="strict WAV"):
        speech_plan(decode_evidence=decode_evidence(**decode_change))


def test_task048_does_not_take_task047_raw_conversion_ownership() -> None:
    raw_float = decode_evidence(sample_format="IEEE_FLOAT32")
    explicit = format_policy(dither_policy_sha256=digest("e"))
    with pytest.raises(FinishingContractError, match="canonical TASK-047 input"):
        speech_plan(decode_evidence=raw_float, format_policy=explicit)
    stereo = decode_evidence(channels=2)
    phase_safe = format_policy(
        channel_strategy=ChannelStrategy.PHASE_SAFE_DOWNMIX,
        phase_audit_receipt_sha256=digest("f"),
    )
    with pytest.raises(FinishingContractError, match="canonical TASK-047 input"):
        speech_plan(decode_evidence=stereo, format_policy=phase_safe)


def test_multichannel_policy_requires_explicit_phase_or_channel_evidence() -> None:
    stereo = decode_evidence(channels=2)
    with pytest.raises(FinishingContractError, match="multichannel"):
        format_policy().validate_input(stereo)
    with pytest.raises(FinishingContractError, match="audit receipt"):
        format_policy(channel_strategy=ChannelStrategy.PHASE_SAFE_DOWNMIX).validate_input(stereo)
    with pytest.raises(FinishingContractError, match="outside"):
        format_policy(channel_strategy=ChannelStrategy.SELECT_CHANNEL, selected_channel_index=2).validate_input(stereo)


def test_lossy_training_format_and_unsafe_fade_policy_are_rejected() -> None:
    with pytest.raises(FinishingContractError, match="lossy"):
        format_policy(lossy_codec=True)
    with pytest.raises(FinishingContractError, match="natural pauses"):
        continuity_policy(long_non_speech_min_samples=10_000, max_natural_pause_samples=20_000)


@pytest.mark.parametrize(
    ("fade_samples", "message"),
    [
        (True, "positive integer"),
        (240.0, "positive integer"),
        (1, "fade sample count is fixed"),
        (239, "fade sample count is fixed"),
        (241, "fade sample count is fixed"),
        (3_000, "fade sample count is fixed"),
    ],
)
def test_equal_power_boundary_fade_is_fixed_to_240_samples(
    fade_samples: object,
    message: str,
) -> None:
    with pytest.raises(FinishingContractError, match=message):
        continuity_policy(fade_samples=fade_samples)


def test_speech_continuous_fixture_pass_binds_ranges_and_never_publishes_partial() -> None:
    plan = speech_plan()
    fake = runner(speech=speech_readback())
    receipt = FixtureVoiceQualityAudioFinishingService(fake).finish_speech_continuous(plan)
    assert receipt.state is QAState.PASS
    body = receipt.to_dict()
    assert body["retained_ranges"] == [
        {"start_sample": 0, "end_sample": 30_000},
        {"start_sample": 69_600, "end_sample": 96_000},
    ]
    assert body["removed_sample_count"] == 39_600
    assert body["input_sample_count"] == 96_000
    assert body["input_pcm_payload_bytes"] == 288_000
    assert body["output_pcm_payload_bytes"] == 168_480
    assert body["size_reduction_bytes"] == 119_520
    assert body["size_optimization_mode"] == "LOSSLESS_SAMPLE_RANGE_REMOVAL_PLUS_BOUNDARY_CROSSFADE"
    assert body["canonical_wav_container"] == "RIFF_WAVE_PCM_S24LE"
    assert body["boundary_mode"] == "EQUAL_POWER_CROSSFADE"
    assert body["boundary_count"] == 1
    assert body["crossfade_overlap_samples"] == 240
    assert len(body["boundary_evidence_sha256s"]) == 1
    assert body["zero_gap_compression"] is False
    assert body["partial_output_published"] is False
    assert body["lossy_codec_used"] is False
    assert body["raw_source_preserved"] is True
    assert body["dataset_adoption_started"] is False
    assert body["task046_lineage_candidate_sha256"].startswith("sha256:")
    assert body["task046_lineage_authority_created"] is False
    assert body["authority_created"] is False


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"zero_cross_or_crossfade_verified": False}, ReasonCode.SPEECH_BOUNDARY_UNVERIFIED),
        ({"speech_attack_preserved": False}, ReasonCode.SPEECH_ATTACK_OR_TAIL_DAMAGED),
        ({"speech_tail_preserved": False}, ReasonCode.SPEECH_ATTACK_OR_TAIL_DAMAGED),
        ({"partial_output_published": True}, ReasonCode.COPY_READBACK_MISMATCH),
        ({"readback_verified": False}, ReasonCode.COPY_READBACK_MISMATCH),
        ({"directory_durable": False}, ReasonCode.COPY_READBACK_MISMATCH),
    ],
)
def test_speech_continuous_boundary_and_publish_failures_cannot_pass(changes, reason) -> None:
    receipt = FixtureVoiceQualityAudioFinishingService(
        runner(speech=speech_readback(**changes))
    ).finish_speech_continuous(speech_plan())
    assert receipt.state is QAState.FAIL
    assert reason in receipt.reason_codes
    assert receipt.task046_lineage_candidate_sha256 is None


def test_speech_continuous_wrong_output_count_and_runner_error_burn() -> None:
    plan = speech_plan()
    service = FixtureVoiceQualityAudioFinishingService(runner(speech=speech_readback(output_sample_count=1)))
    receipt = service.finish_speech_continuous(plan)
    assert receipt.state is QAState.FAIL
    assert ReasonCode.COPY_READBACK_MISMATCH in receipt.reason_codes
    with pytest.raises(OperationAlreadyConsumedError):
        service.finish_speech_continuous(plan)

    failing = FixtureVoiceQualityAudioFinishingService(runner(speech=FinishingContractError("PRIVATE_WAV_BODY")))
    failure_plan = speech_plan(operation_id="speech/op-error")
    with pytest.raises(FinishingContractError) as caught:
        failing.finish_speech_continuous(failure_plan)
    assert "PRIVATE_WAV_BODY" not in str(caught.value)
    assert caught.value.__cause__ is None


def test_speech_continuous_source_identity_and_lineage_must_match() -> None:
    with pytest.raises(FinishingContractError, match="not current"):
        speech_plan(decode_evidence=decode_evidence(source_identity_sha256=digest("f")))
    with pytest.raises(FinishingContractError, match="not current"):
        speech_plan(source=source(identity_current=False))


@pytest.mark.parametrize(
    "source_changes",
    [
        {
            "terminal_receipt_sha256": None,
            "terminal_receipt_owner": None,
            "terminal_receipt_type": None,
            "terminal_receipt_current": False,
        },
        {"terminal_receipt_owner": "TASK-014"},
        {"terminal_receipt_type": "LIVE_METER_RECEIPT_V1"},
        {"terminal_receipt_current": False},
    ],
)
def test_speech_continuous_requires_post_stop_task047_terminal_receipt(source_changes) -> None:
    with pytest.raises(FinishingContractError, match="not current"):
        speech_plan(source=source(**source_changes))


@pytest.mark.parametrize(
    "operation_kind",
    [OperationKind.ENVIRONMENT_AB_QA, OperationKind.SPEECH_CONTINUOUS_TRAINING_FINISH],
)
def test_audio_receipt_cannot_be_relabelled_across_operation_families(operation_kind) -> None:
    receipt = FixtureVoiceQualityAudioFinishingService(
        runner(training=(measurements(), readback()))
    ).prepare_training_copy(training_plan())
    with pytest.raises(FinishingContractError, match="operation kind"):
        replace(receipt, operation_kind=operation_kind)


@pytest.mark.parametrize(
    "capture_changes",
    [
        {"capture_receipt_current": False},
        {"room_tone_receipt_current": False},
        {"source_identity_current": False},
        {"source_read_current": False},
        {"source_ancestor_current": False},
        {"room_tone_generation_sha256": digest("f")},
    ],
)
def test_environment_capture_snapshot_must_be_current_before_runner(capture_changes) -> None:
    fake = runner(environment=environment_bundle())
    receipt = FixtureVoiceQualityAudioFinishingService(fake).compare_environment(
        environment_plan(
            on_capture=capture(CaptureCondition.AIR_CONDITIONER_ON, **capture_changes)
        )
    )
    assert receipt.comparison_state is QAState.UNKNOWN
    assert receipt.reason_codes == (ReasonCode.AB_CAPTURE_NOT_CURRENT,)
    assert fake.calls == []


def test_environment_same_bytes_different_identity_and_mixed_identity_are_rejected() -> None:
    key = (CaptureCondition.AIR_CONDITIONER_ON, VoiceEffort.NORMAL)
    segment_swap = environment_bundle(
        segment_changes={key: {"source_identity_sha256": digest("f")}}
    )
    receipt = FixtureVoiceQualityAudioFinishingService(
        runner(environment=segment_swap)
    ).compare_environment(environment_plan())
    assert receipt.comparison_state is QAState.UNKNOWN
    assert receipt.reason_codes == (ReasonCode.AB_MEASUREMENT_NOT_CURRENT,)

    denoise_swap = environment_bundle(
        pair_changes={key: {"denoised_input_source_identity_sha256": digest("f")}}
    )
    receipt = FixtureVoiceQualityAudioFinishingService(
        runner(environment=denoise_swap)
    ).compare_environment(environment_plan(operation_id="environment/op-identity-2"))
    assert receipt.comparison_state is QAState.UNKNOWN
    assert receipt.reason_codes == (ReasonCode.AB_MEASUREMENT_NOT_CURRENT,)


@pytest.mark.parametrize("missing_level", ["speech_rms_dbfs", "speech_peak_dbfs"])
def test_environment_missing_speech_levels_requires_review(missing_level: str) -> None:
    key = (CaptureCondition.AIR_CONDITIONER_OFF, VoiceEffort.WHISPER)
    receipt = FixtureVoiceQualityAudioFinishingService(
        runner(environment=environment_bundle(segment_changes={key: {missing_level: None}}))
    ).compare_environment(environment_plan())
    assessment = next(
        item for item in receipt.segment_assessments
        if (item.condition, item.effort) == key
    )
    assert assessment.eligibility is SegmentEligibility.REVIEW
    assert ReasonCode.SPEECH_LEVEL_UNKNOWN in assessment.reason_codes
    assert receipt.comparison_state is QAState.UNKNOWN
    assert receipt.reason_codes == (ReasonCode.AB_REVIEW_REQUIRED,)


def test_environment_missing_room_tone_blocks_ab_delta_without_recommendation() -> None:
    key = (CaptureCondition.AIR_CONDITIONER_ON, VoiceEffort.NORMAL)
    receipt = FixtureVoiceQualityAudioFinishingService(
        runner(environment=environment_bundle(segment_changes={
            key: {"room_tone_noise_floor_dbfs": None},
        }))
    ).compare_environment(environment_plan())

    assert receipt.comparison_state is QAState.UNKNOWN
    assert receipt.reason_codes == (ReasonCode.AB_MEASUREMENT_SET_INVALID,)
    assert receipt.measurement_bundle_sha256 is None
    assert receipt.noise_deltas == ()
    assert receipt.recommended_condition is None


def test_environment_reject_is_reflected_in_top_level_comparison_state() -> None:
    key = (CaptureCondition.AIR_CONDITIONER_ON, VoiceEffort.SHOUT)
    receipt = FixtureVoiceQualityAudioFinishingService(
        runner(environment=environment_bundle(segment_changes={key: {"clipped_sample_count": 1}}))
    ).compare_environment(environment_plan())
    assert receipt.comparison_state is QAState.FAIL
    assert receipt.reason_codes == (ReasonCode.AB_SEGMENT_REJECTED,)


def test_environment_pass_receipt_requires_exact_typed_canonical_cardinality() -> None:
    receipt = FixtureVoiceQualityAudioFinishingService(
        runner(environment=environment_bundle())
    ).compare_environment(environment_plan())
    with pytest.raises(FinishingContractError, match="segment assessments"):
        replace(receipt, segment_assessments=tuple(reversed(receipt.segment_assessments)))
    with pytest.raises(FinishingContractError, match="segment assessments"):
        replace(receipt, segment_assessments=(receipt.segment_assessments[0],) * 6)
    with pytest.raises(FinishingContractError, match="denoise assessments"):
        replace(receipt, denoise_assessments=tuple(reversed(receipt.denoise_assessments)))
    with pytest.raises(FinishingContractError, match="noise deltas"):
        replace(receipt, noise_deltas=tuple(reversed(receipt.noise_deltas)))


def test_environment_bundle_rejects_permuted_measurement_order() -> None:
    bundle = environment_bundle()
    with pytest.raises(FinishingContractError, match="segment measurement set"):
        replace(bundle, segments=tuple(reversed(bundle.segments)))
    with pytest.raises(FinishingContractError, match="denoise comparison set"):
        replace(bundle, denoise_pairs=tuple(reversed(bundle.denoise_pairs)))


def test_crossfade_boundaries_have_exact_overlap_and_per_boundary_evidence() -> None:
    plan = speech_plan()
    assert plan.boundary_mode is BoundaryMode.EQUAL_POWER_CROSSFADE
    assert plan.boundary_count == 1
    assert plan.crossfade_overlap_samples == 240
    assert plan.output_sample_count == sum(item.sample_count for item in plan.retained_ranges) - 240
    with pytest.raises(FinishingContractError, match="crossfade accounting"):
        replace(plan, crossfade_overlap_samples=0, output_sample_count=56_400)
    with pytest.raises(FinishingContractError, match="boundary evidence cardinality"):
        speech_readback(boundary_evidence_sha256s=())

    receipt = FixtureVoiceQualityAudioFinishingService(
        runner(speech=speech_readback(crossfade_overlap_samples=0))
    ).finish_speech_continuous(plan)
    assert receipt.state is QAState.FAIL
    assert ReasonCode.COPY_READBACK_MISMATCH in receipt.reason_codes
    assert receipt.task046_lineage_candidate_sha256 is None


def test_public_pass_receipt_cannot_redefine_fixed_crossfade_duration() -> None:
    receipt = FixtureVoiceQualityAudioFinishingService(
        runner(speech=speech_readback())
    ).finish_speech_continuous(speech_plan())
    with pytest.raises(FinishingContractError, match="fade sample count is fixed"):
        replace(
            receipt,
            fade_samples=120,
            crossfade_overlap_samples=120,
            output_sample_count=56_280,
        )


def test_exact_nested_types_and_boolean_markers_reject_subclasses_and_ints() -> None:
    class SourceSubclass(SourceSnapshot):
        pass

    class AudioFormatSubclass(AudioFormat):
        pass

    original = source(terminal_receipt_sha256=None)
    source_subclass = SourceSubclass(**{
        field.name: getattr(original, field.name) for field in fields(SourceSnapshot)
    })
    with pytest.raises(FinishingContractError, match="binding type"):
        generated_plan(source=source_subclass)
    with pytest.raises(FinishingContractError, match="binding type"):
        generated_plan(output_format=AudioFormatSubclass())
    with pytest.raises(FinishingContractError, match="consent_current"):
        training_plan(consent_current=1)
    with pytest.raises(FinishingContractError, match="exact_range_applied"):
        readback(exact_range_applied=1)

    receipt = FixtureVoiceQualityAudioFinishingService(
        runner(generated=(measurements(), readback()))
    ).finish_generated(generated_plan())
    with pytest.raises(FinishingContractError, match="fixture_only"):
        replace(receipt, fixture_only=1)


@pytest.mark.parametrize("external_effect_count", [False, 0.0])
def test_fixture_external_effect_count_requires_exact_integer_zero(external_effect_count) -> None:
    with pytest.raises(FinishingContractError, match="external effect"):
        readback(external_effect_count=external_effect_count)
    with pytest.raises(FinishingContractError, match="external effect"):
        speech_readback(external_effect_count=external_effect_count)


def test_policy_boolean_fields_reject_integer_lookalikes() -> None:
    with pytest.raises(FinishingContractError, match="head/tail"):
        generated_plan(head_tail_trim_only=1)
    with pytest.raises(FinishingContractError, match="lossy_codec"):
        format_policy(lossy_codec=0)


@pytest.mark.parametrize(
    "changes",
    [
        {"sample_rate_hz": 48_000.0},
        {"sample_rate_hz": True},
        {"channels": 1.0},
        {"channels": True},
    ],
)
def test_audio_format_requires_exact_json_scalar_types(changes) -> None:
    with pytest.raises(FinishingContractError, match="audio format"):
        AudioFormat(**changes)


@pytest.mark.parametrize(
    ("sample_count", "intervals"),
    [
        (
            100_000,
            (
                SpeechEvidenceInterval(SampleRange(0, 1), IntervalClass.UNCERTAIN, 0.5, digest("1")),
                SpeechEvidenceInterval(SampleRange(1, 60_001), IntervalClass.NON_SPEECH, 0.99, digest("2")),
                SpeechEvidenceInterval(SampleRange(60_001, 100_000), IntervalClass.SPEECH, 0.99, digest("3")),
            ),
        ),
        (
            200_000,
            (
                SpeechEvidenceInterval(SampleRange(0, 1), IntervalClass.UNCERTAIN, 0.5, digest("1")),
                SpeechEvidenceInterval(SampleRange(1, 60_001), IntervalClass.NON_SPEECH, 0.99, digest("2")),
                SpeechEvidenceInterval(SampleRange(60_001, 60_002), IntervalClass.UNCERTAIN, 0.5, digest("3")),
                SpeechEvidenceInterval(SampleRange(60_002, 120_002), IntervalClass.NON_SPEECH, 0.99, digest("4")),
                SpeechEvidenceInterval(SampleRange(120_002, 200_000), IntervalClass.SPEECH, 0.99, digest("5")),
            ),
        ),
    ],
)
def test_crossfade_rejects_tiny_retained_islands_without_deleting_ambiguity(
    sample_count: int,
    intervals,
) -> None:
    with pytest.raises(FinishingContractError, match="too short for boundary crossfade"):
        speech_plan(
            source=source(sample_count=sample_count),
            decode_evidence=decode_evidence(sample_count_per_channel=sample_count),
            intervals=intervals,
        )
