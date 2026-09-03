from __future__ import annotations

import copy
import hashlib
import json

import pytest

import ai_video_production.voice_obs_folder_dataset_intake as intake
from ai_video_production.voice_dataset_revision import (
    add_record_digest as add_dataset_record_digest,
    validate_record as validate_dataset_record,
)

from ai_video_production.voice_obs_folder_dataset_intake import (
    AUTHORITY_KIND,
    CONTRACT_VERSION,
    MINIMUM_COVERAGE_SAMPLES,
    TARGET_COVERAGE_SAMPLES,
    AvailabilityState,
    ContractState,
    CoverageState,
    FolderCurrentness,
    ObsFolderDatasetIntakeProposal,
    SpeechRangeCandidate,
    add_record_digest,
    assert_no_effect_surface,
    compile_folder_binding,
    compile_fingerprint_index_binding,
    compile_intake_proposal,
    public_projection,
    transcript_range_identity_sha256,
    validate_record,
)


NOW = "2026-09-03T00:00:00Z"
OP = "operation:obs-intake:1"


def h(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def folder(**changes: object) -> dict:
    values = dict(
        folder_binding_id="folder-binding:opaque:1",
        preference_revision=1,
        currentness=FolderCurrentness.CURRENT,
        configured=True,
        availability_state=AvailabilityState.AVAILABLE,
        reason_codes=(),
    )
    values.update(changes)
    return compile_folder_binding(**values).to_dict()


def observation(
    recording_id: str = "recording:1",
    *,
    operation_id: str = OP,
    track_class: str = "MIC_ISOLATED",
    finalization_state: str = "BOUND_VERIFIED",
    capture_format_state: str = "BOUND_VERIFIED",
    stability_state: str = "STABLE",
    media_state: str = "PASS",
    asset_state: str = "BOUND_VERIFIED",
    track_state: str = "BOUND_VERIFIED",
) -> dict:
    asset_bound = asset_state == "BOUND_VERIFIED"
    track_bound = track_state == "BOUND_VERIFIED"
    if not track_bound:
        track_class = "UNKNOWN"
    body = {
        "contract_version": CONTRACT_VERSION,
        "record_type": "ObservedRecording",
        "authority_kind": AUTHORITY_KIND,
        "synthetic_input_only": True,
        "owner_audio_used": False,
        "scan_operation_id": operation_id,
        "recording_id": recording_id,
        "source_identity_sha256": h(f"source:{recording_id}"),
        "finalization_state": finalization_state,
        "finalization_receipt_sha256": h(f"finalization:{recording_id}") if finalization_state == "BOUND_VERIFIED" else None,
        "capture_format_binding_state": capture_format_state,
        "capture_format_receipt_sha256": h(f"capture-format:{recording_id}") if capture_format_state == "BOUND_VERIFIED" else None,
        "capture_format": "PCM_S24LE_48000_MONO" if capture_format_state == "BOUND_VERIFIED" else None,
        "stability_state": stability_state,
        "media_validation_state": media_state,
        "track_binding_state": track_state,
        "track_class": track_class,
        "track_index": 1 if track_bound else None,
        "track_classification_receipt_sha256": h(f"track:{recording_id}") if track_bound else None,
        "asset_binding_state": asset_state,
        "source_asset_id": f"asset:{recording_id}" if asset_bound else None,
        "source_asset_revision_ref": f"asset:{recording_id}:rev1" if asset_bound else None,
        "source_asset_revision_sha256": h(f"asset-revision:{recording_id}") if asset_bound else None,
        "source_asset_checksum_sha256": h(f"asset-checksum:{recording_id}") if asset_bound else None,
        "private_media_custody_state": "BOUND_VERIFIED" if asset_bound else "NOT_BOUND",
        "private_media_custody_receipt_sha256": h(f"private-media:{recording_id}") if asset_bound else None,
        "source_path_body_present": False,
    }
    return add_record_digest(body, "observed_recording_sha256")


def candidate(
    observed: dict,
    candidate_id: str = "candidate:1",
    *,
    start_us: int = 0,
    sample_count: int = 48_000,
    fingerprint: str | None = None,
    transcript_state: str = "BOUND_VERIFIED",
    voice_state: str = "BOUND_VERIFIED",
    consent_state: str = "PASS",
    rights_state: str = "PASS",
    quality_state: str = "PASS",
    quality_reasons: tuple[str, ...] = (),
    label_state: str = "BOUND_VERIFIED",
    privacy_state: str = "PASS",
    owner_decision: str = "UNREVIEWED",
    training_state: str = "BOUND_VERIFIED",
) -> dict:
    transcript_bound = transcript_state == "BOUND_VERIFIED"
    voice_bound = voice_state == "BOUND_VERIFIED"
    label_bound = label_state == "BOUND_VERIFIED"
    training_bound = training_state == "BOUND_VERIFIED"
    normalization_bound = training_bound and observed["source_asset_checksum_sha256"] is not None
    duration_us = max(1, sample_count * 1_000_000 // 48_000)
    body = {
        "contract_version": CONTRACT_VERSION,
        "record_type": "SpeechRangeCandidate",
        "authority_kind": AUTHORITY_KIND,
        "synthetic_input_only": True,
        "owner_audio_used": False,
        "scan_operation_id": observed["scan_operation_id"],
        "candidate_id": candidate_id,
        "recording_id": observed["recording_id"],
        "observed_recording_sha256": observed["observed_recording_sha256"],
        "candidate_revision_ref": f"{candidate_id}:rev1",
        "candidate_revision_sha256": h(f"candidate-revision:{candidate_id}"),
        "source_start_us": start_us,
        "source_end_us": start_us + duration_us,
        "transcript_binding_state": transcript_state,
        "transcript_source_asset_id": observed["source_asset_id"] if transcript_bound else None,
        "transcript_manifest_sha256": h(f"transcript:{candidate_id}") if transcript_bound else None,
        "transcript_provider_id": "provider:faster-whisper" if transcript_bound else None,
        "transcript_model_id": "model:whisper-large-v3" if transcript_bound else None,
        "transcript_language": "ja" if transcript_bound else None,
        "transcript_range_sha256": transcript_range_identity_sha256(
            source_asset_id=observed["source_asset_id"],
            transcript_manifest_sha256=h(f"transcript:{candidate_id}"),
            source_start_us=start_us,
            source_end_us=start_us + duration_us,
        ) if transcript_bound else None,
        "transcript_private_custody_state": "BOUND_VERIFIED" if transcript_bound else "NOT_BOUND",
        "transcript_private_custody_receipt_sha256": h(f"transcript-custody:{candidate_id}") if transcript_bound else None,
        "voice_profile_binding_state": voice_state,
        "voice_profile_revision_sha256": h("voice-profile") if voice_bound else None,
        "consent_state": consent_state,
        "consent_evaluation_sha256": h(f"consent:{candidate_id}") if consent_state in {"PASS", "FAIL"} else None,
        "rights_state": rights_state,
        "rights_evaluation_sha256": h(f"rights:{candidate_id}") if rights_state in {"PASS", "FAIL"} else None,
        "quality_state": quality_state,
        "quality_evaluation_sha256": h(f"quality:{candidate_id}") if quality_state in {"PASS", "FAIL"} else None,
        "quality_subject_asset_checksum_sha256": observed["source_asset_checksum_sha256"] if quality_state in {"PASS", "FAIL"} else None,
        "quality_subject_start_us": start_us if quality_state in {"PASS", "FAIL"} else None,
        "quality_subject_end_us": start_us + duration_us if quality_state in {"PASS", "FAIL"} else None,
        "quality_reason_codes": sorted(quality_reasons),
        "label_binding_state": label_state,
        "approved_label_binding_sha256": h(f"label:{candidate_id}") if label_bound else None,
        "privacy_review_state": privacy_state,
        "owner_decision": owner_decision,
        "training_asset_binding_state": training_state,
        "training_asset_id": f"asset:training:{candidate_id}" if training_bound else None,
        "training_asset_revision_ref": f"asset:training:{candidate_id}:rev1" if training_bound else None,
        "training_asset_revision_sha256": h(f"training-revision:{candidate_id}") if training_bound else None,
        "training_asset_checksum_sha256": h(f"training-checksum:{candidate_id}") if training_bound else None,
        "training_copy_format": "PCM_S24LE_48000_MONO",
        "training_sample_rate_hz": 48_000,
        "training_channel_count": 1,
        "training_bit_depth": 24,
        "training_asset_sample_count": sample_count if training_bound else None,
        "training_private_custody_state": "BOUND_VERIFIED" if training_bound else "NOT_BOUND",
        "training_private_custody_receipt_sha256": h(f"training-custody:{candidate_id}") if training_bound else None,
        "normalization_binding_state": "BOUND_VERIFIED" if normalization_bound else "NOT_BOUND",
        "normalization_receipt_sha256": h(f"normalization:{candidate_id}") if normalization_bound else None,
        "normalization_source_asset_checksum_sha256": observed["source_asset_checksum_sha256"] if normalization_bound else None,
        "normalization_source_start_us": start_us if normalization_bound else None,
        "normalization_source_end_us": start_us + duration_us if normalization_bound else None,
        "normalization_output_asset_id": f"asset:training:{candidate_id}" if normalization_bound else None,
        "normalization_output_asset_revision_ref": f"asset:training:{candidate_id}:rev1" if normalization_bound else None,
        "normalization_output_asset_revision_sha256": h(f"training-revision:{candidate_id}") if normalization_bound else None,
        "normalization_output_asset_checksum_sha256": h(f"training-checksum:{candidate_id}") if normalization_bound else None,
        "normalization_output_sample_count": sample_count if normalization_bound else None,
        "audio_fingerprint_sha256": fingerprint or h(f"fingerprint:{candidate_id}"),
        "audio_body_persisted": False,
        "transcript_text_persisted": False,
    }
    return add_record_digest(body, "candidate_sha256")


def proposal(candidates: list[dict], observations: list[dict], **changes: object) -> dict:
    existing = tuple(changes.pop("existing_fingerprint_sha256s", ()))
    expected_head = changes.get("expected_dataset_head_sha256", None)
    values = dict(
        proposal_id="proposal:1",
        operation_id=OP,
        idempotency_key="idempotency:1",
        project_id="project:owner",
        dataset_id="dataset:owner-voice",
        expected_dataset_head_sha256=None,
        folder_binding=folder(),
        voice_profile_revision_sha256=h("voice-profile"),
        policy_revision_sha256=h("policy"),
        observations=observations,
        candidates=candidates,
        fingerprint_index_binding=compile_fingerprint_index_binding(
            dataset_id="dataset:owner-voice",
            dataset_head_sha256=expected_head,
            ordered_fingerprint_sha256s=existing,
        ).to_dict(),
        created_at=NOW,
    )
    values.update(changes)
    return compile_intake_proposal(**values).to_dict()


def test_exact_synthetic_mic_candidate_is_accepted_without_issuing_membership() -> None:
    observed = observation()
    row = candidate(observed)
    result = proposal([row], [observed])
    assert result["candidate_results"][0]["disposition"] == "ACCEPTED"
    assert result["coverage_state"] == "COVERAGE_LT_30"
    assert result["canonical_training_readiness"] == "NOT_CONFIRMED"
    assert result["synthetic_input_only"] is True
    assert result["owner_audio_used"] is False
    assert result["canonical_membership_issued"] is False
    assert result["training_input_snapshot_issued"] is False


@pytest.mark.parametrize(
    ("samples", "expected"),
    [
        (MINIMUM_COVERAGE_SAMPLES - 1, CoverageState.COVERAGE_LT_30.value),
        (MINIMUM_COVERAGE_SAMPLES, CoverageState.MINIMUM_COVERAGE_MET.value),
        (TARGET_COVERAGE_SAMPLES, CoverageState.TARGET_COVERAGE_MET.value),
    ],
)
def test_coverage_thresholds_use_actual_normalized_48k_samples(samples: int, expected: str) -> None:
    observed = observation()
    result = proposal([candidate(observed, sample_count=samples)], [observed])
    assert result["accepted_unique_samples"] == samples
    assert result["accepted_duration_ms"] == samples * 1000 // 48_000
    assert result["coverage_state"] == expected
    assert result["canonical_training_readiness"] == "NOT_CONFIRMED"


def test_unknown_required_fact_is_review_only_and_never_counts_duration() -> None:
    observed = observation(finalization_state="NOT_BOUND")
    result = proposal([candidate(observed)], [observed])
    row = result["candidate_results"][0]
    assert row["disposition"] == "REVIEW_REQUIRED"
    assert row["unique_samples"] == 0
    assert "SOURCE_FINALIZATION_NOT_BOUND" in row["reason_codes"]
    assert result["coverage_state"] == "REVIEW_BLOCKED"


@pytest.mark.parametrize("track_class", ["MIXED_OR_UNKNOWN", "NON_MIC_ONLY"])
def test_r1_never_accepts_non_isolated_mic_even_with_bound_track_receipt(track_class: str) -> None:
    observed = observation(track_class=track_class)
    result = proposal([candidate(observed)], [observed])
    assert result["candidate_results"][0]["disposition"] == "EXCLUDED"
    assert "MIC_ISOLATED_REQUIRED" in result["candidate_results"][0]["reason_codes"]


@pytest.mark.parametrize(
    ("changes", "reason", "disposition"),
    [
        ({"stability_state": "LOCKED"}, "SOURCE_LOCKED", "REVIEW_REQUIRED"),
        ({"stability_state": "UNSUPPORTED"}, "MEDIA_UNSUPPORTED", "EXCLUDED"),
        ({"media_state": "FAIL"}, "MEDIA_INVALID", "EXCLUDED"),
        ({"asset_state": "STALE"}, "SOURCE_ASSET_MISMATCH", "EXCLUDED"),
        ({"capture_format_state": "NOT_BOUND"}, "CAPTURE_FORMAT_NOT_BOUND", "REVIEW_REQUIRED"),
    ],
)
def test_source_and_storage_failures_are_fail_closed(changes: dict, reason: str, disposition: str) -> None:
    observed = observation(**changes)
    candidate_changes = {}
    if changes.get("asset_state") != "BOUND_VERIFIED":
        candidate_changes = {"transcript_state": "UNKNOWN", "quality_state": "UNKNOWN", "training_state": "NOT_BOUND"}
    result = proposal([candidate(observed, **candidate_changes)], [observed])
    row = result["candidate_results"][0]
    assert row["disposition"] == disposition
    assert reason in row["reason_codes"]


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"transcript_state": "UNKNOWN"}, "TRANSCRIPT_NOT_BOUND"),
        ({"voice_state": "STALE"}, "VOICE_PROFILE_MISMATCH"),
        ({"consent_state": "REVOKED"}, "CONSENT_NOT_CURRENT"),
        ({"rights_state": "FAIL"}, "RIGHTS_BLOCKED"),
        ({"label_state": "UNKNOWN"}, "LABEL_NOT_BOUND"),
        ({"training_state": "NOT_BOUND"}, "TRAINING_ASSET_NOT_BOUND"),
    ],
)
def test_required_binding_negatives_are_not_accepted(kwargs: dict, reason: str) -> None:
    observed = observation()
    result = proposal([candidate(observed, **kwargs)], [observed])
    row = result["candidate_results"][0]
    assert row["disposition"] != "ACCEPTED"
    assert reason in row["reason_codes"]


@pytest.mark.parametrize("quality_reason", ["SILENCE", "CLIPPING", "LOW_SNR", "OTHER_SPEAKER", "MUSIC_OR_GAME_AUDIO"])
def test_quality_failures_preserve_exact_exclusion_reason(quality_reason: str) -> None:
    observed = observation()
    result = proposal([candidate(observed, quality_state="FAIL", quality_reasons=(quality_reason,))], [observed])
    row = result["candidate_results"][0]
    assert row["disposition"] == "EXCLUDED"
    assert quality_reason in row["reason_codes"]


def test_privacy_and_owner_exclusion_override_otherwise_eligible_candidate() -> None:
    observed = observation()
    private = candidate(observed, "candidate:private", privacy_state="FAIL")
    owner = candidate(observed, "candidate:owner", start_us=2_000_000, owner_decision="EXCLUDE")
    result = proposal([private, owner], [observed])
    reasons = {row["candidate_id"]: row["reason_codes"] for row in result["candidate_results"]}
    assert "PRIVATE_OR_SECRET_CONTENT" in reasons["candidate:private"]
    assert "OWNER_EXCLUDED" in reasons["candidate:owner"]
    assert result["accepted_unique_samples"] == 0


def test_prior_dataset_fingerprint_wins_and_new_overlap_has_stable_tie_break() -> None:
    observed = observation()
    prior = h("prior-fingerprint")
    duplicate = candidate(observed, "candidate:z", fingerprint=prior)
    first = candidate(observed, "candidate:b", start_us=2_000_000)
    overlap = candidate(observed, "candidate:a", start_us=2_500_000)
    one = proposal([duplicate, first, overlap], [observed], existing_fingerprint_sha256s=(prior,))
    two = proposal([overlap, duplicate, first], [observed], existing_fingerprint_sha256s=(prior,))
    assert one["candidate_results"] == two["candidate_results"]
    by_id = {row["candidate_id"]: row for row in one["candidate_results"]}
    assert by_id["candidate:z"]["reason_codes"] == ["DUPLICATE"]
    assert by_id["candidate:b"]["disposition"] == "ACCEPTED"
    assert by_id["candidate:a"]["reason_codes"] == ["OVERLAP"]


def test_exact_transcript_source_asset_binding_is_required() -> None:
    observed = observation()
    row = candidate(observed)
    row["transcript_source_asset_id"] = "asset:wrong"
    row["transcript_range_sha256"] = transcript_range_identity_sha256(
        source_asset_id=row["transcript_source_asset_id"],
        transcript_manifest_sha256=row["transcript_manifest_sha256"],
        source_start_us=row["source_start_us"],
        source_end_us=row["source_end_us"],
    )
    row = add_record_digest(row, "candidate_sha256")
    result = proposal([row], [observed])
    assert result["candidate_results"][0]["disposition"] == "EXCLUDED"
    assert "TRANSCRIPT_SOURCE_ASSET_MISMATCH" in result["candidate_results"][0]["reason_codes"]


def test_operation_and_exact_observation_binding_mismatches_are_rejected() -> None:
    observed = observation(operation_id="operation:other")
    with pytest.raises(ValueError, match="observation operation mismatch"):
        proposal([candidate(observed)], [observed])
    observed = observation()
    row = candidate(observed)
    row["observed_recording_sha256"] = h("wrong")
    row = add_record_digest(row, "candidate_sha256")
    with pytest.raises(ValueError, match="observation binding mismatch"):
        proposal([row], [observed])


def test_public_projection_contains_no_ids_digests_paths_fingerprints_or_bodies() -> None:
    observed = observation()
    result = proposal([candidate(observed)], [observed])
    index = compile_fingerprint_index_binding(
        dataset_id="dataset:owner-voice", dataset_head_sha256=None,
        ordered_fingerprint_sha256s=(),
    ).to_dict()
    for record in (folder(), observed, candidate(observed), index, result):
        encoded = json.dumps(public_projection(record), sort_keys=True)
        for forbidden in ("sha256", "binding_id", "candidate:1", "fingerprint", "provider:", "model:", "E:\\", "transcript_language"):
            assert forbidden not in encoded
    projection = public_projection(result)
    assert projection["source_path_body_present"] is False
    assert projection["dataset_mutation_authorized"] is False
    assert projection["training_authorized"] is False
    assert projection["model_load_started"] is False
    assert projection["provider_execution_started"] is False


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("training_copy_format", "WAV_FLOAT"),
        ("training_sample_rate_hz", 44_100),
        ("training_channel_count", 2),
        ("training_bit_depth", 16),
    ],
)
def test_wrong_training_media_format_is_rejected(field: str, bad: object) -> None:
    observed = observation()
    row = candidate(observed)
    row[field] = bad
    row = add_record_digest(row, "candidate_sha256")
    with pytest.raises(ValueError):
        SpeechRangeCandidate.from_dict(row)


def test_capture_format_receipt_cannot_claim_float_or_multichannel_source_ready() -> None:
    observed = observation()
    observed["capture_format"] = "WAVE_FLOAT32_48000_STEREO"
    observed = add_record_digest(observed, "observed_recording_sha256")
    with pytest.raises(ValueError, match="capture format"):
        validate_record(observed)


def test_raw_path_text_body_unknown_fields_bool_as_int_and_digest_tamper_fail_closed() -> None:
    observed = observation()
    extra = candidate(observed)
    extra["raw_transcript_text"] = "secret"
    with pytest.raises(ValueError, match="fields"):
        validate_record(extra)
    forged = candidate(observed)
    forged["audio_body_persisted"] = True
    forged = add_record_digest(forged, "candidate_sha256")
    with pytest.raises(ValueError, match="false"):
        validate_record(forged)
    bad_bool = folder()
    bad_bool["configured"] = 1
    bad_bool = add_record_digest(bad_bool, "binding_sha256")
    with pytest.raises(ValueError, match="boolean"):
        validate_record(bad_bool)
    tampered = proposal([candidate(observed)], [observed])
    tampered["accepted_unique_samples"] += 1
    with pytest.raises(ValueError, match="mismatch"):
        ObsFolderDatasetIntakeProposal.from_dict(tampered)
    with pytest.raises(ValueError, match="host path"):
        folder(folder_binding_id="E:\\OBS")


def test_proposal_rejects_recomputed_forged_counts_coverage_and_training_readiness() -> None:
    observed = observation()
    base = proposal([candidate(observed)], [observed])
    for field, bad in (
        ("reason_counts", {"FORGED": 1}),
        ("coverage_state", "TARGET_COVERAGE_MET"),
        ("canonical_training_readiness", "TRAINING_READY"),
    ):
        forged = copy.deepcopy(base)
        forged[field] = bad
        forged = add_record_digest(forged, "proposal_sha256")
        with pytest.raises(ValueError):
            validate_record(forged)


def test_records_are_immutable_and_module_has_no_effect_surface() -> None:
    observed = observation()
    record = SpeechRangeCandidate.from_dict(candidate(observed))
    with pytest.raises(TypeError):
        record.data["owner_decision"] = "EXCLUDE"
    assert_no_effect_surface()


def test_production_or_owner_audio_authority_cannot_be_self_asserted() -> None:
    observed = observation()
    row = candidate(observed)
    for record, digest_field in (
        (folder(), "binding_sha256"),
        (observed, "observed_recording_sha256"),
        (row, "candidate_sha256"),
    ):
        forged = copy.deepcopy(record)
        forged["authority_kind"] = "PRODUCTION_OWNER_AUDIO"
        forged["synthetic_input_only"] = False
        forged["owner_audio_used"] = True
        forged = add_record_digest(forged, digest_field)
        with pytest.raises(ValueError, match="synthetic"):
            validate_record(forged)


def test_public_reason_codes_are_closed_and_cannot_encode_private_content() -> None:
    with pytest.raises(ValueError, match="unsupported reason"):
        folder(reason_codes=("PRIVATE_PATH_E_OBS_SECRET",))


@pytest.mark.parametrize("bad_id", ["folder/private.wav", "C:private/voice.wav", "file:/private/voice.wav"])
def test_typed_ids_reject_relative_drive_and_uri_path_smuggling(bad_id: str) -> None:
    with pytest.raises(ValueError):
        folder(folder_binding_id=bad_id)


@pytest.mark.parametrize(
    ("target", "state_field", "receipt_field", "reason"),
    [
        ("observation", "private_media_custody_state", "private_media_custody_receipt_sha256", "PRIVATE_MEDIA_CUSTODY_NOT_BOUND"),
        ("candidate", "transcript_private_custody_state", "transcript_private_custody_receipt_sha256", "TRANSCRIPT_PRIVATE_CUSTODY_NOT_BOUND"),
        ("candidate", "training_private_custody_state", "training_private_custody_receipt_sha256", "TRAINING_PRIVATE_CUSTODY_NOT_BOUND"),
        ("candidate", "normalization_binding_state", "normalization_receipt_sha256", "NORMALIZATION_NOT_BOUND"),
    ],
)
def test_missing_private_custody_or_normalization_receipt_is_never_accepted(
    target: str, state_field: str, receipt_field: str, reason: str,
) -> None:
    observed = observation()
    row = candidate(observed)
    record = observed if target == "observation" else row
    record[state_field] = "NOT_BOUND"
    record[receipt_field] = None
    if state_field == "normalization_binding_state":
        for field in (
            "normalization_source_asset_checksum_sha256", "normalization_source_start_us",
            "normalization_source_end_us", "normalization_output_asset_id",
            "normalization_output_asset_revision_ref", "normalization_output_asset_revision_sha256",
            "normalization_output_asset_checksum_sha256",
            "normalization_output_sample_count",
        ):
            record[field] = None
    digest_field = "observed_recording_sha256" if target == "observation" else "candidate_sha256"
    record = add_record_digest(record, digest_field)
    if target == "observation":
        row = candidate(record)
        observed = record
    else:
        row = record
    result = proposal([row], [observed])
    assert result["candidate_results"][0]["disposition"] == "REVIEW_REQUIRED"
    assert reason in result["candidate_results"][0]["reason_codes"]


def test_fingerprint_index_is_bounded_current_and_bound_to_exact_dataset_head() -> None:
    with pytest.raises(ValueError, match="bounded"):
        compile_fingerprint_index_binding(
            dataset_id="dataset:owner-voice",
            dataset_head_sha256=None,
            ordered_fingerprint_sha256s=tuple(h(f"fp:{index}") for index in range(4097)),
        )
    with pytest.raises(ValueError, match="must not invent"):
        compile_fingerprint_index_binding(
            dataset_id="dataset:owner-voice",
            dataset_head_sha256=h("head"),
            ordered_fingerprint_sha256s=(h("fp"),),
            contract_state=ContractState.NOT_BOUND,
        )
    observed = observation()
    wrong = compile_fingerprint_index_binding(
        dataset_id="dataset:owner-voice",
        dataset_head_sha256=h("wrong-head"),
        ordered_fingerprint_sha256s=(),
    ).to_dict()
    with pytest.raises(ValueError, match="Dataset/head mismatch"):
        proposal([candidate(observed)], [observed], fingerprint_index_binding=wrong)


def test_short_source_range_cannot_claim_target_coverage_via_inflated_sample_count() -> None:
    observed = observation()
    row = candidate(observed, sample_count=TARGET_COVERAGE_SAMPLES)
    row["source_end_us"] = 1_000_000
    row["quality_subject_end_us"] = 1_000_000
    row["normalization_source_end_us"] = 1_000_000
    row["transcript_range_sha256"] = transcript_range_identity_sha256(
        source_asset_id=row["transcript_source_asset_id"],
        transcript_manifest_sha256=row["transcript_manifest_sha256"],
        source_start_us=row["source_start_us"],
        source_end_us=row["source_end_us"],
    )
    row = add_record_digest(row, "candidate_sha256")
    with pytest.raises(ValueError, match="more samples"):
        SpeechRangeCandidate.from_dict(row)


@pytest.mark.parametrize(
    ("training_field", "source_field", "normalization_field"),
    [
        ("training_asset_id", "source_asset_id", "normalization_output_asset_id"),
        ("training_asset_revision_ref", "source_asset_revision_ref", "normalization_output_asset_revision_ref"),
        ("training_asset_revision_sha256", "source_asset_revision_sha256", "normalization_output_asset_revision_sha256"),
        ("training_asset_checksum_sha256", "source_asset_checksum_sha256", "normalization_output_asset_checksum_sha256"),
    ],
)
def test_each_source_and_training_asset_identity_coordinate_cannot_collapse(
    training_field: str, source_field: str, normalization_field: str,
) -> None:
    observed = observation()
    row = candidate(observed)
    row[training_field] = observed[source_field]
    row[normalization_field] = observed[source_field]
    row = add_record_digest(row, "candidate_sha256")
    result = proposal([row], [observed])
    assert result["candidate_results"][0]["disposition"] == "EXCLUDED"
    assert "TRAINING_ASSET_SOURCE_COLLISION" in result["candidate_results"][0]["reason_codes"]


def test_quality_and_normalization_receipts_must_bind_the_exact_source_subject() -> None:
    observed = observation()
    for field, reason in (
        ("quality_subject_asset_checksum_sha256", "QUALITY_SUBJECT_MISMATCH"),
        ("normalization_source_asset_checksum_sha256", "NORMALIZATION_SUBJECT_MISMATCH"),
    ):
        row = candidate(observed)
        row[field] = h(f"wrong:{field}")
        row = add_record_digest(row, "candidate_sha256")
        result = proposal([row], [observed])
        assert result["candidate_results"][0]["disposition"] == "EXCLUDED"
        assert reason in result["candidate_results"][0]["reason_codes"]


def test_privacy_stale_is_excluded_and_terminal_failure_is_not_downgraded_by_unknown_track() -> None:
    observed = observation()
    privacy = proposal([candidate(observed, privacy_state="STALE")], [observed])
    assert privacy["candidate_results"][0]["disposition"] == "EXCLUDED"
    assert "PRIVACY_NOT_CURRENT" in privacy["candidate_results"][0]["reason_codes"]
    terminal = observation(finalization_state="STALE", track_state="NOT_BOUND")
    result = proposal([candidate(terminal)], [terminal])
    assert result["candidate_results"][0]["disposition"] == "EXCLUDED"
    assert "SOURCE_FINALIZATION_MISMATCH" in result["candidate_results"][0]["reason_codes"]


def test_public_authority_constant_is_not_an_authority_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(intake, "AUTHORITY_KIND", "PRODUCTION_OWNER_AUDIO")
    compiled = compile_folder_binding(
        folder_binding_id="folder-binding:opaque:constant-test",
        preference_revision=1,
        currentness=FolderCurrentness.CURRENT,
        configured=True,
        availability_state=AvailabilityState.AVAILABLE,
    ).to_dict()
    assert compiled["authority_kind"] == "SYNTHETIC_CONTRACT_TEST"
    forged = dict(compiled)
    forged["authority_kind"] = "PRODUCTION_OWNER_AUDIO"
    forged = add_record_digest(forged, "binding_sha256")
    with pytest.raises(ValueError, match="synthetic"):
        validate_record(forged)


def test_transcript_range_digest_binds_manifest_asset_and_exact_range() -> None:
    observed = observation()
    row = candidate(observed)
    row["source_end_us"] += 1
    row["quality_subject_end_us"] += 1
    row["normalization_source_end_us"] += 1
    row = add_record_digest(row, "candidate_sha256")
    with pytest.raises(ValueError, match="transcript range binding mismatch"):
        SpeechRangeCandidate.from_dict(row)


@pytest.mark.parametrize(
    "field",
    [
        "normalization_output_asset_id",
        "normalization_output_asset_revision_ref",
        "normalization_output_asset_revision_sha256",
    ],
)
def test_normalization_receipt_binds_exact_training_asset_coordinates(field: str) -> None:
    observed = observation()
    row = candidate(observed)
    row[field] = h("other-training-revision") if field.endswith("sha256") else "asset:training:other"
    row = add_record_digest(row, "candidate_sha256")
    with pytest.raises(ValueError, match="normalization output Asset mismatch"):
        SpeechRangeCandidate.from_dict(row)


def test_terminal_fingerprint_index_and_media_currentness_are_excluded() -> None:
    observed = observation()
    mismatch_index = compile_fingerprint_index_binding(
        dataset_id="dataset:owner-voice",
        dataset_head_sha256=None,
        ordered_fingerprint_sha256s=(),
        contract_state=ContractState.MISMATCH,
    ).to_dict()
    result = proposal([candidate(observed)], [observed], fingerprint_index_binding=mismatch_index)
    assert result["candidate_results"][0]["disposition"] == "EXCLUDED"
    assert "FINGERPRINT_INDEX_MISMATCH" in result["candidate_results"][0]["reason_codes"]

    stale = observation(media_state="STALE")
    result = proposal([candidate(stale)], [stale])
    assert result["candidate_results"][0]["disposition"] == "EXCLUDED"
    assert "MEDIA_NOT_CURRENT" in result["candidate_results"][0]["reason_codes"]


def test_folder_reasons_are_derived_from_and_cannot_contradict_state() -> None:
    with pytest.raises(ValueError, match="do not match"):
        compile_folder_binding(
            folder_binding_id="folder-binding:opaque:stale",
            preference_revision=1,
            currentness=FolderCurrentness.CURRENT,
            configured=True,
            availability_state=AvailabilityState.AVAILABLE,
            reason_codes=("FOLDER_STALE",),
        )


def test_training_asset_identity_is_counted_at_most_once() -> None:
    observed = observation()
    first = candidate(observed, "candidate:first", start_us=0)
    second = candidate(observed, "candidate:second", start_us=2_000_000)
    for field in (
        "training_asset_id", "training_asset_revision_ref", "training_asset_revision_sha256",
        "training_asset_checksum_sha256", "normalization_output_asset_id",
        "normalization_output_asset_revision_ref", "normalization_output_asset_revision_sha256",
        "normalization_output_asset_checksum_sha256",
    ):
        second[field] = first[field]
    second = add_record_digest(second, "candidate_sha256")
    result = proposal([first, second], [observed])
    by_id = {row["candidate_id"]: row for row in result["candidate_results"]}
    assert by_id["candidate:first"]["disposition"] == "ACCEPTED"
    assert by_id["candidate:second"]["disposition"] == "EXCLUDED"
    assert by_id["candidate:second"]["reason_codes"] == ["TRAINING_ASSET_DUPLICATE"]
    assert result["accepted_unique_samples"] == first["training_asset_sample_count"]


def test_training_asset_revision_digest_is_bound_and_counted_once() -> None:
    observed = observation()
    first = candidate(observed, "candidate:revision-first", start_us=0)
    second = candidate(observed, "candidate:revision-second", start_us=2_000_000)
    second["training_asset_revision_sha256"] = first["training_asset_revision_sha256"]
    second["normalization_output_asset_revision_sha256"] = first["training_asset_revision_sha256"]
    second = add_record_digest(second, "candidate_sha256")
    result = proposal([first, second], [observed])
    by_id = {row["candidate_id"]: row for row in result["candidate_results"]}
    assert by_id["candidate:revision-first"]["disposition"] == "ACCEPTED"
    assert by_id["candidate:revision-second"]["disposition"] == "EXCLUDED"
    assert by_id["candidate:revision-second"]["reason_codes"] == ["TRAINING_ASSET_DUPLICATE"]


def test_quality_fail_requires_a_closed_reason() -> None:
    observed = observation()
    with pytest.raises(ValueError, match="quality FAIL"):
        SpeechRangeCandidate.from_dict(candidate(observed, quality_state="FAIL"))


@pytest.mark.parametrize(
    ("training_field", "normalization_field"),
    [
        ("training_asset_id", "normalization_output_asset_id"),
        ("training_asset_revision_ref", "normalization_output_asset_revision_ref"),
        ("training_asset_checksum_sha256", "normalization_output_asset_checksum_sha256"),
    ],
)
def test_each_training_asset_coordinate_is_counted_once(
    training_field: str, normalization_field: str,
) -> None:
    observed = observation()
    first = candidate(observed, "candidate:coordinate-first", start_us=0)
    second = candidate(observed, "candidate:coordinate-second", start_us=2_000_000)
    second[training_field] = first[training_field]
    second[normalization_field] = first[training_field]
    second = add_record_digest(second, "candidate_sha256")
    result = proposal([first, second], [observed])
    by_id = {row["candidate_id"]: row for row in result["candidate_results"]}
    assert by_id["candidate:coordinate-first"]["disposition"] == "ACCEPTED"
    assert by_id["candidate:coordinate-second"]["disposition"] == "EXCLUDED"
    assert by_id["candidate:coordinate-second"]["reason_codes"] == ["TRAINING_ASSET_DUPLICATE"]


def test_folder_terminal_states_exclude_and_unknown_state_requires_review() -> None:
    observed = observation()
    row = candidate(observed)
    cases = (
        (
            folder(
                currentness=FolderCurrentness.STALE,
                reason_codes=("FOLDER_STALE",),
            ),
            "EXCLUDED",
        ),
        (
            folder(
                currentness=FolderCurrentness.UNKNOWN,
                availability_state=AvailabilityState.UNAVAILABLE,
                reason_codes=("FOLDER_UNKNOWN", "FOLDER_UNAVAILABLE"),
            ),
            "EXCLUDED",
        ),
        (
            folder(
                currentness=FolderCurrentness.UNKNOWN,
                availability_state=AvailabilityState.UNKNOWN,
                reason_codes=("FOLDER_UNKNOWN",),
            ),
            "REVIEW_REQUIRED",
        ),
    )
    for binding, expected in cases:
        result = proposal([row], [observed], folder_binding=binding)
        assert result["candidate_results"][0]["disposition"] == expected


def test_accepted_candidate_has_non_issuing_membership_compatibility_fixture() -> None:
    observed = observation()
    row = candidate(observed)
    result = proposal([row], [observed])
    assert result["candidate_results"][0]["disposition"] == "ACCEPTED"
    fixture = add_dataset_record_digest(
        {
            "record_type": "VoiceDatasetMembershipEntry",
            "member_id": "member:synthetic-compatibility-only",
            "candidate_revision_ref": row["candidate_revision_ref"],
            "candidate_revision_sha256": row["candidate_revision_sha256"],
            "asset_binding_state": row["training_asset_binding_state"],
            "asset_revision_ref": row["training_asset_revision_ref"],
            "asset_revision_sha256": row["training_asset_revision_sha256"],
            "asset_checksum_sha256": row["training_asset_checksum_sha256"],
            "sample_start": 0,
            "sample_end": row["training_asset_sample_count"],
            "consent_evaluation_sha256": row["consent_evaluation_sha256"],
            "rights_evaluation_sha256": row["rights_evaluation_sha256"],
            "quality_evaluation_sha256": row["quality_evaluation_sha256"],
            "approved_label_binding_sha256": row["approved_label_binding_sha256"],
            "processing_class": "CANONICAL_CONVERTED_RAW",
            "audio_body_persisted": False,
        },
        "entry_sha256",
    )
    assert validate_dataset_record(fixture, expected_type="VoiceDatasetMembershipEntry") == fixture
    assert result["canonical_membership_issued"] is False
    assert result["training_input_snapshot_issued"] is False
