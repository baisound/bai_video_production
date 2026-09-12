from __future__ import annotations

import hashlib
import json
import pathlib
import re
from copy import deepcopy
from importlib import resources

import pytest
from jsonschema import Draft202012Validator, ValidationError


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    ROOT
    / "src"
    / "ai_video_production"
    / "schema_resources"
    / "task047-readiness-monitor-receipt-v1.schema.json"
)
RECEIPT_SOURCE = (
    ROOT
    / "native"
    / "task047_obs_voice_capture"
    / "controller"
    / "BaiReadinessReceipt.cs"
)
BUILD_SOURCE = (
    ROOT
    / "native"
    / "task047_obs_voice_capture"
    / "scripts"
    / "build-controller.ps1"
)


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _keys(schema: dict) -> set[str]:
    return set(schema["properties"])


H = "a" * 64
EH = "sha256:" + H
CREATED = "2026-01-01T00:00:00.000000Z"
OBSERVED = "2026-01-01T00:00:01.000000Z"
EFFECT = "2026-01-01T00:00:02.000000Z"
EXPIRES = "2026-01-01T00:10:00.000000Z"
SUBJECT_REF = "11111111-1111-1111-1111-111111111111"
QUERY_REF = "22222222-2222-2222-2222-222222222222"


def _external_digest(value: dict, domain: str, exclude: str | None = None) -> str:
    preimage = {key: item for key, item in value.items() if key != exclude}
    body = json.dumps(
        preimage,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(domain.encode("ascii") + b"\0" + body).hexdigest()


def _minimal_receipt() -> dict:
    subject = {
        "record_type": "OwnerVoiceSubjectBindingV1",
        "schema_version": 1,
        "canonical_owner_task": "TASK-046",
        "receipt_role": "OWNER_VOICE_SUBJECT_BINDING",
        "project_id": "BAI_VIDEO_PRODUCTION",
        "subject_ref": SUBJECT_REF,
        "subject_revision": 1,
        "subject_revision_sha256": "",
        "predecessor_subject_revision_sha256": None,
        "currentness_state": "CURRENT",
        "currentness_readback_sha256": EH,
        "created_at": CREATED,
        "observed_at": OBSERVED,
        "fresh_until": EXPIRES,
        "trusted_time_binding_sha256": EH,
        "binding_sha256": "",
    }
    subject["subject_revision_sha256"] = _external_digest(
        {
            "project_id": subject["project_id"],
            "subject_ref": subject["subject_ref"],
            "subject_revision": subject["subject_revision"],
            "predecessor_subject_revision_sha256": subject[
                "predecessor_subject_revision_sha256"
            ],
        },
        "TASK046_OWNER_VOICE_SUBJECT_REVISION_V1",
    )
    subject["binding_sha256"] = _external_digest(
        subject, "TASK046_OWNER_VOICE_SUBJECT_BINDING_V1", "binding_sha256"
    )
    consent = {
        "record_type": "OwnerVoicePurposeConsentEvaluationV1",
        "schema_version": 1,
        "canonical_owner_task": "TASK-046",
        "receipt_role": "OWNER_VOICE_PURPOSE_CONSENT_EVALUATION",
        "project_id": "BAI_VIDEO_PRODUCTION",
        "subject_ref": SUBJECT_REF,
        "subject_revision": 1,
        "subject_revision_sha256": subject["subject_revision_sha256"],
        "evaluation_revision": 1,
        "purpose": "OWNER_VOICE_CAPTURE",
        "decision": "ALLOW",
        "rights_scope": "LOCAL_CAPTURE_AND_BOUND_PRIVATE_CUSTODY_ONLY",
        "policy_revision_sha256": EH,
        "predecessor_evaluation_sha256": None,
        "issued_at": CREATED,
        "observed_at": OBSERVED,
        "expires_at": EXPIRES,
        "revocation_currentness_sha256": EH,
        "trusted_time_binding_sha256": EH,
        "evaluation_sha256": "",
    }
    consent["evaluation_sha256"] = _external_digest(
        consent,
        "TASK046_OWNER_VOICE_PURPOSE_CONSENT_EVALUATION_V1",
        "evaluation_sha256",
    )
    readback = {
        "record_type": "OwnerVoiceCurrentnessReadbackV1",
        "schema_version": 1,
        "canonical_owner_task": "TASK-046",
        "receipt_role": "OWNER_VOICE_CURRENTNESS_READBACK",
        "project_id": "BAI_VIDEO_PRODUCTION",
        "subject_ref": SUBJECT_REF,
        "query_ref": QUERY_REF,
        "subject_binding_sha256": subject["binding_sha256"],
        "consent_evaluation_sha256": consent["evaluation_sha256"],
        "head_sha256": EH,
        "head_event_sequence": 1,
        "head_event_sha256": EH,
        "subject_revision_sha256": subject["subject_revision_sha256"],
        "policy_revision_sha256": EH,
        "purpose": "OWNER_VOICE_CAPTURE",
        "rights_scope": "LOCAL_CAPTURE_AND_BOUND_PRIVATE_CUSTODY_ONLY",
        "consent_decision": "ALLOW",
        "currentness_state": "CURRENT",
        "reason_codes": ["CURRENT_MATCH"],
        "observed_at": OBSERVED,
        "fresh_until": EXPIRES,
        "trusted_time_binding_sha256": EH,
        "readback_sha256": "",
    }
    readback["readback_sha256"] = _external_digest(
        readback, "TASK046_OWNER_VOICE_CURRENTNESS_READBACK_V1", "readback_sha256"
    )
    return {
        "schema": "bvp.task047.readiness-monitor-receipt.v1",
        "schema_version": 1,
        "operation_id": "operation-1",
        "session_id": "session-1",
        "mode": "READINESS_MONITOR",
        "admission": {
            "envelope_ref": "envelope-1",
            "envelope_sha256": H,
            "owner_start_command_id": "owner-start-1",
            "authorized_start_count": 1,
            "expires_at_utc": EXPIRES,
            "owner_subject_binding": subject,
            "owner_capture_consent_evaluation": consent,
            "start_currentness_readback": readback,
            "execution_authorization_ref": "execution-1",
            "execution_authorization_sha256": H,
            "admitted_effect_time_utc": EFFECT,
            "durable_exclusion_token_ref": "exclusion-1",
            "durable_exclusion_readback_sha256": H,
            "durable_exclusion_head_sha256": H,
        },
        "limits": {
            "revision": 1,
            "hard_cap_minutes": 3,
            "arm_budget_ms": 10000,
            "no_input_budget_ms": 5000,
            "stop_settlement_budget_ms": 2000,
            "metadata_publication_budget_ms": 2000,
            "watchdog_max_interval_ms": 100,
            "max_pending_commands": 16,
            "max_settings_epochs": 8,
            "max_windows": 16,
            "max_events": 64,
            "max_receipt_bytes": 262144,
        },
        "clocks": {
            "started_at_utc": EFFECT,
            "stop_requested_at_utc": EFFECT,
            "settled_at_utc": EFFECT,
            "monotonic_frequency": 10_000_000,
            "start_tick": 0,
            "stop_request_tick": 10,
            "revoke_tick": 11,
            "settled_tick": 12,
        },
        "terminal": {
            "primary_reason": "OWNER_STOP",
            "secondary_reasons": [],
            "receiver_settled": True,
            "in_flight_count": 0,
            "local_admission_revoked": True,
            "open_window_disposition": "NONE_OPEN_AT_REVOKE",
            "producer_stop_ack_state": "UNAVAILABLE_LEGACY_WIRE",
        },
        "capture_binding": {
            "controller_sha256": H,
            "plugin_sha256": H,
            "obs_image_sha256": H,
            "process_identity_ref": "process-1",
            "source_chain_ref": "source-1",
            "source_chain_sha256": H,
            "source_assurance": "OWNER_ATTESTED_SINGLE_SOURCE_NOT_WIRE_PROVEN",
            "format_ref": "format-1",
            "sample_rate_hz": 48000,
            "channel_layout_ref": "stereo-1",
            "channel_count": 2,
            "format_assurance": "EXTERNAL_SNAPSHOT_BOUND_NOT_WIRE_PROVEN",
            "wire_version": 1,
            "source_clock_mapping_state": "UNBOUND",
            "queue_freshness_state": "NOT_PROVEN_WIRE_V1",
        },
        "transport": {
            "connection_attempts": 0,
            "authenticated_packets": 0,
            "committed_packets": 0,
            "committed_frames": 0,
            "incomplete_packets": 0,
            "invalid_headers": 0,
            "hmac_failures": 0,
            "nonce_mismatches": 0,
            "sequence_order_errors": 0,
            "source_timestamp_regressions": 0,
            "sequence_gap_events": 0,
            "missing_packets_lower_bound": 0,
            "discarded_after_revocation": 0,
            "discarded_on_token_change": 0,
            "first_sequence": None,
            "last_sequence": None,
            "first_source_timestamp": None,
            "last_source_timestamp": None,
            "upstream_callback_drop_state": "UNKNOWN_WIRE_V1",
            "acoustic_dropout_state": "NOT_MEASURED",
        },
        "settings_epochs": [],
        "windows": [],
        "events": [
            _event("event-start", "OWNER_START", 0, "owner-start-1"),
            _event("event-stop", "STOP_REQUESTED", 10, "owner-stop-1", "OWNER_STOP"),
            _event("event-revoke", "REVOCATION_LINEARIZED", 11),
            _event("event-settled", "RECEIVER_SETTLED", 12),
        ],
        "measurement_algorithm": {
            "id": "task047.received-float32-aggregate.v1",
            "revision": 1,
            "sample_representation": "PLANAR_LE_IEEE754_BINARY32",
            "accumulation": "BINARY64_IN_RECEIVED_ORDER",
            "excursion_comparison": "FINITE_ABS_GTE_0_9999",
            "channel_aggregation": "SEPARATE_CHANNELS",
        },
        "unknowns": {
            "source_callback_drop_count_state": "UNKNOWN_WIRE_V1",
            "acoustic_dropout_count_state": "NOT_MEASURED",
            "speech_occupancy_state": "NOT_MEASURED",
            "noise_policy_state": "UNALLOCATED_TASK048",
            "snr_evaluation_state": "NOT_EVALUATED",
            "true_peak_state": "NOT_MEASURED",
            "adc_distortion_state": "NOT_MEASURED",
            "source_wire_identity_state": "UNAVAILABLE_WIRE_V1",
            "source_clock_mapping_state": "UNBOUND",
            "queue_freshness_state": "NOT_PROVEN_WIRE_V1",
            "producer_stop_ack_state": "UNAVAILABLE_LEGACY_WIRE",
            "window_minimum_eligibility_state": "UNALLOCATED_TASK048",
        },
        "privacy": {
            "controller_audio_file_created": False,
            "recording_sink_capability_present": False,
            "receipt_contains_audio": False,
            "controller_transcript_created": False,
            "controller_external_audio_transfer": False,
            "controller_session_key_persisted": False,
            "metadata_only": True,
            "secure_ram_erasure_claimed": False,
            "whole_machine_audio_persistence_state": "NOT_CONFIRMED",
            "whole_machine_audio_persistence_reason": "EXTERNAL_HOST_OS_BEHAVIOR_OUT_OF_SCOPE",
        },
        "authority": {
            "measurement_facts_only": True,
            "quality_decision_authority": False,
            "task048_consumer_allocated": False,
            "dataset_adoption_authority": False,
            "training_authority": False,
            "production_eligible": False,
        },
    }


def _assert_task046_dependency_digests(receipt: dict) -> None:
    admission = receipt["admission"]
    subject = admission["owner_subject_binding"]
    consent = admission["owner_capture_consent_evaluation"]
    readback = admission["start_currentness_readback"]
    revision_preimage = {
        "project_id": subject["project_id"],
        "subject_ref": subject["subject_ref"],
        "subject_revision": subject["subject_revision"],
        "predecessor_subject_revision_sha256": subject[
            "predecessor_subject_revision_sha256"
        ],
    }
    assert subject["subject_revision_sha256"] == _external_digest(
        revision_preimage, "TASK046_OWNER_VOICE_SUBJECT_REVISION_V1"
    )
    assert subject["binding_sha256"] == _external_digest(
        subject, "TASK046_OWNER_VOICE_SUBJECT_BINDING_V1", "binding_sha256"
    )
    assert consent["evaluation_sha256"] == _external_digest(
        consent,
        "TASK046_OWNER_VOICE_PURPOSE_CONSENT_EVALUATION_V1",
        "evaluation_sha256",
    )
    assert readback["readback_sha256"] == _external_digest(
        readback, "TASK046_OWNER_VOICE_CURRENTNESS_READBACK_V1", "readback_sha256"
    )


def _event(
    event_id: str,
    code: str,
    tick: int,
    command_id: str | None = None,
    reason_code: str | None = None,
    *,
    epoch_id: str | None = None,
    window_id: str | None = None,
) -> dict:
    return {
        "event_id": event_id,
        "command_id": command_id,
        "tick": tick,
        "frame": 0,
        "epoch_id": epoch_id,
        "window_id": window_id,
        "code": code,
        "reason_code": reason_code,
    }


def _with_empty_room_window() -> dict:
    receipt = _minimal_receipt()
    not_attested = {
        "state": "NOT_ATTESTED",
        "attestation_ref": None,
        "owner_subject_binding_sha256": None,
        "command_id": None,
        "observed_tick": None,
        "currentness_state": "NOT_ATTESTED",
        "invalidation_event_ids": [],
        "epoch_id": "epoch-1",
    }
    fixed = {
        "state": "ATTESTED_FIXED",
        "attestation_ref": "fixed-1",
        "owner_subject_binding_sha256": EH,
        "command_id": "freeze-1",
        "observed_tick": 1,
        "currentness_state": "CURRENT",
        "invalidation_event_ids": [],
        "epoch_id": "epoch-1",
    }
    receipt["settings_epochs"] = [
        {
            "epoch_id": "epoch-1",
            "freeze_command_id": "freeze-1",
            "freeze_frame": 0,
            "freeze_tick": 1,
            "capture_binding_sha256": _capture_binding_hash(receipt["capture_binding"]),
            "settings_ref": "settings-1",
            "settings_sha256": H,
            "settings_assurance": "OWNER_ATTESTED_WITH_AVAILABLE_SOFTWARE_FACTS",
            "owner_ac_attestation": deepcopy(not_attested),
            "owner_fan_attestation": deepcopy(not_attested),
            "owner_fixed_settings_attestation": fixed,
            "invalidation_event_ids": [],
        }
    ]
    no_input = {
        "channel_index": 0,
        "frame_count": 0,
        "finite_count": 0,
        "nan_count": 0,
        "positive_inf_count": 0,
        "negative_inf_count": 0,
        "sum_finite": 0,
        "sum_squares_finite": 0,
        "signed_min_finite": None,
        "signed_max_finite": None,
        "max_abs_finite": None,
        "excursion_threshold_abs": 0.9999,
        "excursion_count": 0,
        "derived_state": "NO_INPUT",
        "mean_dc": None,
        "rms_linear": None,
        "peak_linear": None,
        "rms_dbfs": None,
        "peak_dbfs": None,
    }
    channel_two = deepcopy(no_input)
    channel_two["channel_index"] = 1
    receipt["windows"] = [
        {
            "window_id": "room-1",
            "epoch_id": "epoch-1",
            "purpose": "ROOM_TONE",
            "coordinate_domain": "ACCEPTED_AUTHENTICATED_FRAME_V1",
            "start_frame": 0,
            "end_frame": 0,
            "start_command_id": "room-start-1",
            "end_command_id": "room-end-1",
            "start_event_id": "event-room-start",
            "closure_event_id": "event-room-end",
            "start_tick": 2,
            "end_tick": 3,
            "first_sequence": None,
            "last_sequence": None,
            "frame_count": 0,
            "closure_state": "CLOSED",
            "currentness_state": "SAME_EPOCH_AT_CLOSE",
            "observation_flags": ["UPSTREAM_LOSS_UNKNOWN"],
            "invalidation_event_ids": [],
            "channel_statistics": [no_input, channel_two],
        }
    ]
    receipt["events"][1:1] = [
        _event("event-freeze", "SETTINGS_FROZEN", 1, "freeze-1", epoch_id="epoch-1"),
        _event(
            "event-room-start",
            "ROOM_TONE_STARTED",
            2,
            "room-start-1",
            epoch_id="epoch-1",
            window_id="room-1",
        ),
        _event(
            "event-room-end",
            "ROOM_TONE_ENDED",
            3,
            "room-end-1",
            epoch_id="epoch-1",
            window_id="room-1",
        ),
    ]
    return receipt


def _capture_binding_hash(capture_binding: dict) -> str:
    body = json.dumps(
        capture_binding,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(
        b"BVP_TASK047_READINESS_CAPTURE_BINDING_V1\0" + body
    ).hexdigest()


def test_schema_identity_and_exact_root_are_closed() -> None:
    schema = _schema()
    expected = {
        "schema",
        "schema_version",
        "operation_id",
        "session_id",
        "mode",
        "admission",
        "limits",
        "clocks",
        "terminal",
        "capture_binding",
        "transport",
        "settings_epochs",
        "windows",
        "events",
        "measurement_algorithm",
        "unknowns",
        "privacy",
        "authority",
    }
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "bvp.task047.readiness-monitor-receipt.v1"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == expected
    assert _keys(schema) == expected
    assert len(expected) == 18


def test_schema_is_valid_draft_2020_12_and_accepts_independent_golden() -> None:
    schema = _schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_minimal_receipt())
    Draft202012Validator(schema).validate(_with_empty_room_window())


def test_task046_uuid_predecessor_and_current_match_matrices_fail_closed() -> None:
    validator = Draft202012Validator(_schema())
    fixture = _minimal_receipt()
    fixture["admission"]["owner_subject_binding"]["subject_ref"] = "owner-primary"
    with pytest.raises(ValidationError):
        validator.validate(fixture)

    fixture = _minimal_receipt()
    fixture["admission"]["owner_subject_binding"]["subject_revision"] = 2
    with pytest.raises(ValidationError):
        validator.validate(fixture)

    fixture = _minimal_receipt()
    fixture["admission"]["owner_capture_consent_evaluation"]["evaluation_revision"] = 2
    with pytest.raises(ValidationError):
        validator.validate(fixture)

    fixture = _minimal_receipt()
    fixture["admission"]["start_currentness_readback"]["reason_codes"] = []
    with pytest.raises(ValidationError):
        validator.validate(fixture)


def test_task046_domain_digests_are_independently_recomputed() -> None:
    fixture = _minimal_receipt()
    _assert_task046_dependency_digests(fixture)
    for record_name, field in (
        ("owner_subject_binding", "subject_revision_sha256"),
        ("owner_subject_binding", "binding_sha256"),
        ("owner_capture_consent_evaluation", "evaluation_sha256"),
        ("start_currentness_readback", "readback_sha256"),
    ):
        forged = deepcopy(fixture)
        forged["admission"][record_name][field] = EH
        with pytest.raises(AssertionError):
            _assert_task046_dependency_digests(forged)

    source = RECEIPT_SOURCE.read_text(encoding="utf-8")
    for domain in (
        "TASK046_OWNER_VOICE_SUBJECT_REVISION_V1",
        "TASK046_OWNER_VOICE_SUBJECT_BINDING_V1",
        "TASK046_OWNER_VOICE_PURPOSE_CONSENT_EVALUATION_V1",
        "TASK046_OWNER_VOICE_CURRENTNESS_READBACK_V1",
    ):
        assert domain in source
    assert "ExternalUuid" in source


def test_independent_minimal_receipt_has_pinned_canonical_bytes() -> None:
    encoded = (
        json.dumps(
            _minimal_receipt(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    assert len(encoded) == 8461
    assert hashlib.sha256(encoded).hexdigest() == (
        "3cef9d2ae094c88c0f1178c745d234fbbf2560456db69655af761b16265d2b0e"
    )


def test_attestation_matrix_rejects_false_or_ambiguous_states() -> None:
    validator = Draft202012Validator(_schema())
    fixture = _with_empty_room_window()
    fixture["settings_epochs"][0]["owner_ac_attestation"]["state"] = "ATTESTED_FIXED"
    with pytest.raises(ValidationError):
        validator.validate(fixture)

    fixture = _with_empty_room_window()
    fixture["settings_epochs"][0]["owner_ac_attestation"]["attestation_ref"] = "forged"
    with pytest.raises(ValidationError):
        validator.validate(fixture)

    fixture = _with_empty_room_window()
    fixed = fixture["settings_epochs"][0]["owner_fixed_settings_attestation"]
    fixed["invalidation_event_ids"] = ["event-room-end"]
    with pytest.raises(ValidationError):
        validator.validate(fixture)


def test_window_statistics_and_event_matrices_reject_contradictions() -> None:
    validator = Draft202012Validator(_schema())
    fixture = _with_empty_room_window()
    fixture["windows"][0]["end_command_id"] = None
    with pytest.raises(ValidationError):
        validator.validate(fixture)

    fixture = _with_empty_room_window()
    fixture["windows"][0]["observation_flags"] = []
    with pytest.raises(ValidationError):
        validator.validate(fixture)

    fixture = _with_empty_room_window()
    fixture["windows"][0]["channel_statistics"][0]["mean_dc"] = 0
    with pytest.raises(ValidationError):
        validator.validate(fixture)

    fixture = _with_empty_room_window()
    fixture["events"][-2]["command_id"] = "forged-command"
    with pytest.raises(ValidationError):
        validator.validate(fixture)


def test_every_declared_object_is_closed_and_fully_required() -> None:
    def walk(value: object) -> None:
        if isinstance(value, dict):
            if value.get("type") == "object":
                assert value.get("additionalProperties") is False
                assert set(value.get("required", ())) == set(value.get("properties", ()))
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(_schema())


def test_owner_subject_binding_consumer_view_has_exact_sixteen_keys() -> None:
    subject = _schema()["properties"]["admission"]["properties"]["owner_subject_binding"]
    expected = {
        "record_type",
        "schema_version",
        "canonical_owner_task",
        "receipt_role",
        "project_id",
        "subject_ref",
        "subject_revision",
        "subject_revision_sha256",
        "predecessor_subject_revision_sha256",
        "currentness_state",
        "currentness_readback_sha256",
        "created_at",
        "observed_at",
        "fresh_until",
        "trusted_time_binding_sha256",
        "binding_sha256",
    }
    assert _keys(subject) == expected
    assert len(expected) == 16
    assert subject["properties"]["canonical_owner_task"]["const"] == "TASK-046"


def test_owner_capture_consent_consumer_view_has_exact_twenty_keys() -> None:
    consent = _schema()["properties"]["admission"]["properties"][
        "owner_capture_consent_evaluation"
    ]
    expected = {
        "record_type",
        "schema_version",
        "canonical_owner_task",
        "receipt_role",
        "project_id",
        "subject_ref",
        "subject_revision",
        "subject_revision_sha256",
        "evaluation_revision",
        "purpose",
        "decision",
        "rights_scope",
        "policy_revision_sha256",
        "predecessor_evaluation_sha256",
        "issued_at",
        "observed_at",
        "expires_at",
        "revocation_currentness_sha256",
        "trusted_time_binding_sha256",
        "evaluation_sha256",
    }
    assert _keys(consent) == expected
    assert len(expected) == 20
    assert consent["properties"]["purpose"]["const"] == "OWNER_VOICE_CAPTURE"
    assert (
        consent["properties"]["rights_scope"]["const"]
        == "LOCAL_CAPTURE_AND_BOUND_PRIVATE_CUSTODY_ONLY"
    )


def test_currentness_readback_consumer_view_has_exact_twenty_three_keys() -> None:
    readback = _schema()["properties"]["admission"]["properties"][
        "start_currentness_readback"
    ]
    expected = {
        "record_type",
        "schema_version",
        "canonical_owner_task",
        "receipt_role",
        "project_id",
        "subject_ref",
        "query_ref",
        "subject_binding_sha256",
        "consent_evaluation_sha256",
        "head_sha256",
        "head_event_sequence",
        "head_event_sha256",
        "subject_revision_sha256",
        "policy_revision_sha256",
        "purpose",
        "rights_scope",
        "consent_decision",
        "currentness_state",
        "reason_codes",
        "observed_at",
        "fresh_until",
        "trusted_time_binding_sha256",
        "readback_sha256",
    }
    assert _keys(readback) == expected
    assert len(expected) == 23


def test_admission_contains_non_bearer_durable_exclusion_coordinates() -> None:
    admission = _schema()["properties"]["admission"]
    for key in (
        "durable_exclusion_token_ref",
        "durable_exclusion_readback_sha256",
        "durable_exclusion_head_sha256",
    ):
        assert key in admission["required"]
    assert admission["properties"]["durable_exclusion_token_ref"]["pattern"].startswith("^")
    assert (
        admission["properties"]["durable_exclusion_readback_sha256"]["pattern"]
        == "^[0-9a-f]{64}$"
    )


def test_limits_pin_owner_three_minute_cap_and_bounded_metadata() -> None:
    limits = _schema()["properties"]["limits"]["properties"]
    assert limits["hard_cap_minutes"]["const"] == 3
    assert limits["max_receipt_bytes"]["const"] == 262144
    assert limits["stop_settlement_budget_ms"]["const"] == 2000
    assert limits["max_windows"]["const"] == 16
    assert limits["max_events"]["const"] == 64


def test_stop_reasons_keep_timestamp_regression_distinct_from_sequence_order() -> None:
    reasons = set(
        _schema()["properties"]["terminal"]["properties"]["primary_reason"]["enum"]
    )
    assert "SOURCE_TIMESTAMP_REGRESSION" in reasons
    assert "SEQUENCE_ORDER_ERROR" in reasons
    assert "SEQUENCE_GAP" in reasons
    assert len(reasons) == 26


def test_transport_has_distinct_sequence_and_timestamp_counters() -> None:
    transport = _schema()["properties"]["transport"]
    assert "sequence_order_errors" in transport["required"]
    assert "source_timestamp_regressions" in transport["required"]
    assert transport["properties"]["first_source_timestamp"]["anyOf"][0]["pattern"] == (
        "^(0|[1-9][0-9]{0,19})$"
    )


def test_window_and_statistics_coordinate_vocabularies_are_closed() -> None:
    window = _schema()["properties"]["windows"]["items"]
    assert (
        window["properties"]["coordinate_domain"]["const"]
        == "ACCEPTED_AUTHENTICATED_FRAME_V1"
    )
    assert set(window["properties"]["closure_state"]["enum"]) == {"CLOSED", "INTERRUPTED"}
    assert set(window["properties"]["currentness_state"]["enum"]) == {
        "SAME_EPOCH_AT_CLOSE",
        "INVALIDATED_AFTER_CLOSE",
        "INVALIDATED_WHILE_OPEN",
        "WITHDRAWN",
    }
    stats = window["properties"]["channel_statistics"]["items"]
    assert stats["properties"]["excursion_threshold_abs"]["const"] == 0.9999
    assert set(stats["properties"]["derived_state"]["enum"]) == {
        "COMPUTED_FINITE",
        "MEASURED_ZERO",
        "NO_INPUT",
        "NOT_COMPUTABLE_NONFINITE",
    }


def test_unknowns_never_turn_missing_proof_into_zero_or_pass() -> None:
    unknowns = _schema()["properties"]["unknowns"]
    expected = {
        "source_callback_drop_count_state": "UNKNOWN_WIRE_V1",
        "acoustic_dropout_count_state": "NOT_MEASURED",
        "speech_occupancy_state": "NOT_MEASURED",
        "noise_policy_state": "UNALLOCATED_TASK048",
        "snr_evaluation_state": "NOT_EVALUATED",
        "true_peak_state": "NOT_MEASURED",
        "adc_distortion_state": "NOT_MEASURED",
        "source_wire_identity_state": "UNAVAILABLE_WIRE_V1",
        "source_clock_mapping_state": "UNBOUND",
        "queue_freshness_state": "NOT_PROVEN_WIRE_V1",
        "producer_stop_ack_state": "UNAVAILABLE_LEGACY_WIRE",
        "window_minimum_eligibility_state": "UNALLOCATED_TASK048",
    }
    assert {
        key: value["const"] for key, value in unknowns["properties"].items()
    } == expected


def test_privacy_claim_is_controller_scoped_and_quality_authority_is_false() -> None:
    schema = _schema()
    privacy = schema["properties"]["privacy"]["properties"]
    assert privacy["controller_audio_file_created"]["const"] is False
    assert privacy["recording_sink_capability_present"]["const"] is False
    assert privacy["whole_machine_audio_persistence_state"]["const"] == "NOT_CONFIRMED"
    assert (
        privacy["whole_machine_audio_persistence_reason"]["const"]
        == "EXTERNAL_HOST_OS_BEHAVIOR_OUT_OF_SCOPE"
    )
    authority = schema["properties"]["authority"]["properties"]
    assert authority["measurement_facts_only"]["const"] is True
    for key in (
        "quality_decision_authority",
        "task048_consumer_allocated",
        "dataset_adoption_authority",
        "training_authority",
        "production_eligible",
    ):
        assert authority[key]["const"] is False


def test_schema_bytes_match_csharp_and_build_pins() -> None:
    digest = hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest()
    assert digest == "61e87d762db8d0fbc28a95dc4c3c7642b83c19bb1a6d197e2fdd1ebc6ff18472"
    receipt = RECEIPT_SOURCE.read_text(encoding="utf-8")
    build = BUILD_SOURCE.read_text(encoding="utf-8")
    assert f'EmbeddedSchemaSha256 = "{digest}"' in receipt
    assert f"$schemaSha -ne '{digest}'" in build
    assert "BVP.Task047.ReadinessMonitorReceiptV1.Schema" in receipt
    assert "BVP.Task047.ReadinessMonitorReceiptV1.Schema" in build


def test_metadata_filename_hashes_validated_id_instead_of_interpolating_it() -> None:
    receipt = RECEIPT_SOURCE.read_text(encoding="utf-8")
    token = receipt.split("internal static string TokenForOperation", 1)[1].split(
        "internal PublicationResult Publish", 1
    )[0]
    assert "BaiReadinessAdmission.RequireId(operationId)" in token
    assert "BVP_TASK047_READINESS_METADATA_FILENAME_V1" in receipt
    assert "SHA256.Create()" in token
    publish = receipt.split("private string PublishOwned", 1)[1]
    assert '"readiness-" + token + ".receipt.pending"' in publish
    assert '"readiness-" + token + ".receipt.json"' in publish
    assert 'Path.Combine(parent, "readiness-" + operationId' not in publish


def test_canonical_serializer_is_sorted_finite_bomless_and_lf_terminated() -> None:
    receipt = RECEIPT_SOURCE.read_text(encoding="utf-8")
    assert "keys.Sort(StringComparer.Ordinal)" in receipt
    assert 'value.ToString("R", CultureInfo.InvariantCulture)' in receipt
    assert "Double.IsNaN(value) || Double.IsInfinity(value)" in receipt
    assert "new UTF8Encoding(false, true)" in receipt
    assert "builder.Append('\\n')" in receipt
    assert "canonicalBytes.Length > BaiReadinessLimits.MaxReceiptBytes" in receipt


def test_package_data_route_already_includes_schema_resources_glob() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "schema_resources/*.json" in pyproject
    packaged = resources.files("ai_video_production").joinpath(
        "schema_resources", SCHEMA_PATH.name
    )
    assert packaged.read_bytes() == SCHEMA_PATH.read_bytes()


@pytest.mark.parametrize("controlling_record", ["subject", "consent", "equal"])
def test_digest_consistent_readback_freshness_bounds(controlling_record: str) -> None:
    # JSON Schema cannot compare timestamps across records. These independent
    # vectors remain schema-valid; the separate semantic validator must reject
    # later-than-controller readbacks even when every digest has been recomputed.
    receipt = _minimal_receipt()
    admission = receipt["admission"]
    subject = admission["owner_subject_binding"]
    consent = admission["owner_capture_consent_evaluation"]
    readback = admission["start_currentness_readback"]
    if controlling_record != "equal":
        earlier = "2026-01-01T00:05:00.000000Z"
        admission["expires_at_utc"] = earlier
        if controlling_record == "subject":
            subject["fresh_until"] = earlier
        else:
            consent["expires_at"] = earlier
    subject["binding_sha256"] = _external_digest(
        subject, "TASK046_OWNER_VOICE_SUBJECT_BINDING_V1", "binding_sha256"
    )
    consent["evaluation_sha256"] = _external_digest(
        consent, "TASK046_OWNER_VOICE_PURPOSE_CONSENT_EVALUATION_V1", "evaluation_sha256"
    )
    readback["subject_binding_sha256"] = subject["binding_sha256"]
    readback["consent_evaluation_sha256"] = consent["evaluation_sha256"]
    readback["readback_sha256"] = _external_digest(
        readback, "TASK046_OWNER_VOICE_CURRENTNESS_READBACK_V1", "readback_sha256"
    )
    Draft202012Validator(_schema()).validate(receipt)
    assert (readback["fresh_until"] <= min(subject["fresh_until"], consent["expires_at"])) is (
        controlling_record == "equal"
    )
    source = RECEIPT_SOURCE.read_text(encoding="utf-8")
    assert "readbackFresh <= subjectFresh && readbackFresh <= consentExpires" in source
    assert '"READBACK_CONTROLLING_EXPIRY_BOUND"' in source
