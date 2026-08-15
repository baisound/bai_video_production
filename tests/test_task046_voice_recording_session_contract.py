from __future__ import annotations

from dataclasses import replace
from importlib import resources
import json
from pathlib import Path

import jsonschema
import pytest

from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.voice_recording_session import (
    BODY_AUTHORITY_FLAGS,
    CandidateState,
    CaptureMode,
    ContractState,
    DatasetCandidateReviewDecision,
    DatasetCandidateRevision,
    ReadinessEvaluationState,
    RecordingSessionState,
    ReviewDecision,
    SegmentAttemptState,
    TeleprompterCheckpointRevision,
    VoiceRecordingSessionRevision,
    VoiceSegmentAttemptRevision,
    clone_with_new_revision,
    evaluate_capture_command,
    parse_record,
    validate_resume_attempt,
    validate_append_only_revision,
    validate_attempt_transition,
    validate_candidate_transition,
    validate_session_transition,
)


ROOT = Path(__file__).parents[1]
NOW = "2026-08-15T13:00:00Z"
LATER = "2026-08-15T14:00:00Z"


def h(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def unresolved(fields: tuple[str, ...]) -> dict[str, object]:
    return {"contract_state": ContractState.CANONICAL_REF_NOT_PROVIDED.value, **{field: None for field in fields}}


def consent() -> dict[str, object]:
    body: dict[str, object] = {
        "consent_subject_ref": "owner-subject-private",
        "consent_scope": "owner-private-recording",
        "allowed_usage_classes": ["VOICE_RECORDING", "DATASET_REVIEW"],
        "state": "ACTIVE",
        "subject_verified": True,
        "evidence_id": "consent-evidence-private",
        "evidence_sha256": h("consent-evidence"),
    }
    body["consent_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def voice_profile() -> dict[str, object]:
    return {
        "voice_profile_id": "voice-profile-owner",
        "canonical_narration_profile_sha256": h("canonical-narration-profile"),
        "revision": 2,
        "parent_revision_sha256": h("voice-profile-parent"),
        "voice_profile_revision_sha256": h("voice-profile-revision"),
        "consent": consent(),
    }


def text_binding() -> dict[str, object]:
    return {
        "text_owner": "TASK-006/SRT",
        "approved_text_revision_ref": "approved-text-revision-7",
        "approved_text_revision_sha256": h("approved-text-revision-7"),
        "source_text_binding_sha256": h("source-text-binding"),
        "body_persisted": False,
    }


def source(*, synthetic: bool = True) -> dict[str, object]:
    return {
        "contract_state": "BOUND_VERIFIED",
        "source_private_ref": "source-private-1",
        "source_revision_sha256": h("source-revision"),
        "public_opaque_ref": "source-opaque-1",
        "source_class": "SYNTHETIC_VIRTUAL" if synthetic else "OWNER_VOICE_PRIVATE",
        "synthetic_non_biometric": synthetic,
    }


def capture_adapter_unresolved() -> dict[str, object]:
    return unresolved(("adapter_ref", "adapter_ref_sha256", "probe_state", "evidence_sha256"))


def resource_unresolved() -> dict[str, object]:
    return unresolved((
        "receipt_ref", "receipt_sha256", "decision_state", "resource_profile_ref",
        "resource_profile_sha256", "evidence_source_revision",
    ))


def calibration_unresolved() -> dict[str, object]:
    return unresolved((
        "analyzer_profile_ref", "analyzer_profile_sha256", "calibration_receipt_ref",
        "calibration_receipt_sha256", "result", "threshold_profile_revision",
        "capture_chain_sha256", "measured_at",
    ))


def calibration_pass() -> dict[str, object]:
    return {
        "contract_state": "BOUND_VERIFIED",
        "analyzer_profile_ref": "analyzer-profile-1",
        "analyzer_profile_sha256": h("analyzer"),
        "calibration_receipt_ref": "calibration-receipt-1",
        "calibration_receipt_sha256": h("calibration"),
        "result": "PASS",
        "threshold_profile_revision": "threshold-profile-1",
        "capture_chain_sha256": h("capture-chain"),
        "measured_at": NOW,
    }


def durable_job_unresolved() -> dict[str, object]:
    return unresolved(("job_ref", "job_sha256", "checkpoint_ref", "checkpoint_sha256", "job_state"))


def result_unresolved(ref: str) -> dict[str, object]:
    return unresolved((ref, f"{ref}_sha256", "result", "evidence_sha256"))


def owner_go_unresolved() -> dict[str, object]:
    return unresolved(("decision_ref", "decision_ref_sha256", "decision", "evidence_sha256"))


def authorization_unresolved() -> dict[str, object]:
    return unresolved((
        "authorization_id", "authorization_revision", "authorization_sha256",
        "authority_kind", "project_id", "recording_session_id", "session_revision_sha256",
        "capture_mode", "readiness_evaluation_sha256", "selected_source_binding_sha256",
        "consent_current_evaluation_sha256", "approved_text_binding_sha256", "scope",
        "issued_at", "expires_at", "one_shot", "replay_policy", "evidence_ref", "evidence_sha256",
    ))


def consent_evaluation(state: str = "PASS") -> dict[str, object]:
    return {
        "consent_snapshot_sha256": consent()["consent_sha256"],
        "current_evaluation_state": state,
        "current_evaluation_sha256": h(f"consent-current-{state}"),
        "evaluated_at": NOW,
    }


def cancel_none() -> dict[str, object]:
    return {
        "cancel_ack_state": "NOT_REQUESTED",
        "external_work_present": False,
        "retained_evidence_present": False,
        "complete_candidate_present": False,
        "retained_evidence_ledger_sha256": None,
        "retention_state": "NOT_APPLICABLE",
        "encryption_recovery_state": "NOT_APPLICABLE",
    }


def asset_unbound() -> dict[str, object]:
    return {
        "asset_binding_state": "UNBOUND_PENDING_TASK003",
        "asset_id": None,
        "asset_checksum_sha256": None,
        "asset_record_evidence_sha256": None,
        "asset_revision_binding_ref": None,
        "asset_revision_binding_sha256": None,
    }


def asset_bound() -> dict[str, object]:
    return {
        "asset_binding_state": "BOUND",
        "asset_id": "ASSET-01HZX123456789ABCDEFGHJKMNP",
        "asset_checksum_sha256": h("asset-bytes"),
        "asset_record_evidence_sha256": h("asset-record"),
        "asset_revision_binding_ref": "task003-asset-revision-1",
        "asset_revision_binding_sha256": h("task003-mapping"),
    }


def capture_receipt_unresolved() -> dict[str, object]:
    return unresolved(("receipt_ref", "receipt_ref_sha256", "capture_state", "evidence_sha256"))


def capture_receipt_bound() -> dict[str, object]:
    return {
        "contract_state": "BOUND_VERIFIED",
        "receipt_ref": "capture-receipt-1",
        "receipt_ref_sha256": h("capture-receipt"),
        "capture_state": "CAPTURED",
        "evidence_sha256": h("capture-evidence"),
    }


def adoption_unresolved() -> dict[str, object]:
    return unresolved((
        "approved_review_decision_sha256", "dataset_parent_revision_sha256",
        "dataset_new_revision_sha256", "adoption_receipt_ref", "adoption_receipt_sha256",
        "effect_operation_id", "idempotency_key",
    ))


def review_unresolved() -> dict[str, object]:
    return unresolved(("decision_ref", "decision_ref_sha256", "decision", "evidence_sha256"))


def review_approved() -> dict[str, object]:
    return {
        "contract_state": "BOUND_VERIFIED",
        "decision_ref": "candidate-review-decision-1",
        "decision_ref_sha256": h("review-decision"),
        "decision": "APPROVE_FOR_ADOPTION",
        "evidence_sha256": h("owner-review-evidence"),
    }


def review_decision(decision: str) -> dict[str, object]:
    return {
        **review_approved(),
        "decision_ref": f"candidate-review-{decision.lower()}",
        "decision_ref_sha256": h(f"review-{decision}"),
        "decision": decision,
    }


def session(
    *,
    state: RecordingSessionState = RecordingSessionState.DRAFT,
    mode: CaptureMode = CaptureMode.SYNTHETIC_CONTRACT_TEST,
    readiness: ReadinessEvaluationState = ReadinessEvaluationState.NOT_EVALUATED,
    production: bool = False,
    selected_source: dict[str, object] | None = None,
    revision: int = 1,
    parent: str | None = None,
    cancel: dict[str, object] | None = None,
) -> VoiceRecordingSessionRevision:
    return VoiceRecordingSessionRevision(
        project_id="project-opaque-1",
        recording_session_id="recording-session-1",
        revision=revision,
        parent_revision_sha256=parent,
        created_at=NOW,
        state=state,
        capture_mode=mode,
        readiness_evaluation_state=readiness,
        readiness_evaluation_sha256=h(f"readiness-{mode.value}-{readiness.value}"),
        production_admission=production,
        operation_id=f"session-operation-{revision}",
        voice_profile_binding=voice_profile(),
        approved_text_binding=text_binding(),
        selected_source_binding=selected_source or source(),
        capture_adapter_binding=capture_adapter_unresolved(),
        resource_admission_binding=resource_unresolved(),
        calibration_binding=calibration_unresolved(),
        capture_durable_job_binding=durable_job_unresolved(),
        encryption_recovery_binding=result_unresolved("policy_ref"),
        disk_floor_binding=result_unresolved("receipt_ref"),
        owner_go_binding=owner_go_unresolved(),
        consent_current_evaluation=consent_evaluation(),
        execution_authorization_binding=authorization_unresolved(),
        cancel_disposition=cancel or cancel_none(),
        dataset_adoption_receipt_binding=adoption_unresolved(),
        body_authority_flags=BODY_AUTHORITY_FLAGS,
    )


def attempt(
    *,
    attempt_id: str = "attempt-1",
    attempt_number: int = 1,
    parent_attempt: str | None = None,
    state: SegmentAttemptState = SegmentAttemptState.PLANNED,
) -> VoiceSegmentAttemptRevision:
    return VoiceSegmentAttemptRevision(
        project_id="project-opaque-1",
        recording_session_id="recording-session-1",
        segment_id="segment-1",
        attempt_id=attempt_id,
        revision=1,
        parent_revision_sha256=None,
        attempt_number=attempt_number,
        parent_attempt_sha256=parent_attempt,
        cue_id="cue-1",
        sentence_id="sentence-1",
        source_text_binding_sha256=text_binding()["source_text_binding_sha256"],
        sentence_start_anchor=0,
        state=state,
        capture_receipt_binding=capture_receipt_unresolved(),
        asset_binding=asset_unbound(),
        calibration_binding=calibration_unresolved(),
        consent_current_evaluation=consent_evaluation(),
        operation_id=f"attempt-operation-{attempt_number}",
        created_at=NOW,
        body_authority_flags=BODY_AUTHORITY_FLAGS,
    )


def candidate(*, state: CandidateState = CandidateState.CAPTURED_CANDIDATE, bound_asset: bool = False) -> DatasetCandidateRevision:
    return DatasetCandidateRevision(
        project_id="project-opaque-1",
        recording_session_id="recording-session-1",
        candidate_id="candidate-1",
        revision=1,
        parent_revision_sha256=None,
        state=state,
        segment_attempt_id="attempt-1",
        segment_attempt_revision_sha256=h("attempt-revision"),
        capture_receipt_binding=capture_receipt_bound(),
        asset_binding=asset_bound() if bound_asset else asset_unbound(),
        voice_profile_binding=voice_profile(),
        consent_current_evaluation=consent_evaluation(),
        calibration_binding=calibration_pass(),
        label_proposals=({"axis": "style", "value": "normal", "source": "AI_PROPOSAL", "evidence_sha256": h("proposal")},),
        approved_labels=(),
        review_decision_binding=review_approved() if state is CandidateState.APPROVED_FOR_ADOPTION else review_unresolved(),
        dataset_adoption_receipt_binding=adoption_unresolved(),
        operation_id="candidate-operation-1",
        created_at=NOW,
        body_authority_flags=BODY_AUTHORITY_FLAGS,
    )


def schema() -> dict[str, object]:
    return json.loads((ROOT / "schemas" / "voice-recording-session.schema.json").read_text(encoding="utf-8"))


def test_schema_is_valid_and_packaged_mirror_is_byte_exact() -> None:
    canonical = (ROOT / "schemas" / "voice-recording-session.schema.json").read_bytes()
    packaged = resources.files("ai_video_production").joinpath(
        "schema_resources", "voice-recording-session.schema.json"
    ).read_bytes()
    assert packaged == canonical
    jsonschema.Draft202012Validator.check_schema(json.loads(canonical))


def test_canonical_five_records_schema_roundtrip_and_hash_tamper() -> None:
    first_attempt = attempt()
    checkpoint = TeleprompterCheckpointRevision(
        project_id="project-opaque-1",
        recording_session_id="recording-session-1",
        checkpoint_id="checkpoint-1",
        revision=1,
        parent_revision_sha256=None,
        plan_binding={
            "plan_id": "teleprompter-plan-1",
            "plan_revision": 1,
            "plan_sha256": h("plan"),
            "approved_text_binding_sha256": text_binding()["source_text_binding_sha256"],
            "planned_minutes": 30,
        },
        segment_id="segment-1",
        attempt_id="attempt-1",
        attempt_number=1,
        cue_id="cue-1",
        sentence_id="sentence-1",
        source_text_binding_sha256=text_binding()["source_text_binding_sha256"],
        sentence_start_anchor=0,
        scroll_position=0,
        last_completed_segment_id=None,
        checkpoint_state="CURRENT",
        created_at=NOW,
        body_authority_flags=BODY_AUTHORITY_FLAGS,
    )
    review = DatasetCandidateReviewDecision(
        project_id="project-opaque-1",
        recording_session_id="recording-session-1",
        review_decision_id="review-1",
        revision=1,
        parent_revision_sha256=None,
        candidate_id="candidate-1",
        candidate_revision_sha256=h("candidate"),
        decision=ReviewDecision.APPROVE_FOR_ADOPTION,
        reviewer_kind="OWNER",
        human_gate_evidence_ref="owner-review-evidence-1",
        human_gate_evidence_sha256=h("review-evidence"),
        asset_binding=asset_bound(),
        consent_current_evaluation=consent_evaluation(),
        calibration_binding=calibration_pass(),
        decided_at=NOW,
        training_start_authorized=False,
        body_authority_flags=BODY_AUTHORITY_FLAGS,
    )
    records = [session(), first_attempt, checkpoint, candidate(), review]
    validator = jsonschema.Draft202012Validator(schema())
    assert {record.record_type for record in records} == {
        "VoiceRecordingSessionRevision",
        "VoiceSegmentAttemptRevision",
        "TeleprompterCheckpointRevision",
        "DatasetCandidateRevision",
        "DatasetCandidateReviewDecision",
    }
    for record in records:
        document = record.to_private_dict()
        validator.validate(document)
        assert parse_record(document).to_private_dict() == document
        tampered = dict(document)
        tampered[record.hash_field] = h("tampered")
        with pytest.raises(ValueError, match="checksum mismatch"):
            parse_record(tampered)


def test_voice_profile_binding_uses_exact_pvs1a_names_without_aliases() -> None:
    document = session().to_private_dict()
    binding = document["voice_profile_binding"]
    assert set(binding) == {
        "voice_profile_id", "canonical_narration_profile_sha256", "revision",
        "parent_revision_sha256", "voice_profile_revision_sha256", "consent",
    }
    assert set(binding["consent"]) == {
        "consent_subject_ref", "consent_scope", "allowed_usage_classes", "state",
        "subject_verified", "evidence_id", "evidence_sha256", "consent_sha256",
    }
    bad = dict(binding)
    bad["consent_evidence_id"] = "forbidden-alias"
    with pytest.raises(ValueError, match="incomplete or unknown"):
        replace(session(), voice_profile_binding=bad)


def test_test_ready_allows_unresolved_upstream_but_never_production() -> None:
    ready = session(state=RecordingSessionState.READY, readiness=ReadinessEvaluationState.TEST_READY)
    assert ready.production_admission is False
    assert ready.resource_admission_binding["contract_state"] == "CANONICAL_REF_NOT_PROVIDED"
    with pytest.raises(ValueError, match="production_admission requires"):
        session(
            state=RecordingSessionState.READY,
            mode=CaptureMode.SYNTHETIC_CONTRACT_TEST,
            readiness=ReadinessEvaluationState.TEST_READY,
            production=True,
        )
    with pytest.raises(ValueError, match="non-biometric synthetic"):
        session(
            state=RecordingSessionState.READY,
            readiness=ReadinessEvaluationState.TEST_READY,
            selected_source=source(synthetic=False),
        )


def test_production_ready_fails_closed_on_unresolved_task020_048_and_job() -> None:
    with pytest.raises(ValueError, match="production admission gates"):
        session(
            state=RecordingSessionState.READY,
            mode=CaptureMode.PRODUCTION_RECORDING,
            readiness=ReadinessEvaluationState.PRODUCTION_READY,
            production=True,
            selected_source={**source(synthetic=False), "source_class": "PRODUCTION_SELECTED_SOURCE"},
        )
    with pytest.raises(ValueError, match="cannot claim production_admission=false"):
        session(
            state=RecordingSessionState.READY,
            mode=CaptureMode.PRODUCTION_RECORDING,
            readiness=ReadinessEvaluationState.PRODUCTION_READY,
        )


def test_session_append_only_cas_transition_and_unknown_no_replay() -> None:
    first = session()
    pending = clone_with_new_revision(
        first,
        state=RecordingSessionState.PREFLIGHT_PENDING,
        operation_id="session-operation-2",
    )
    assert isinstance(pending, VoiceRecordingSessionRevision)
    validate_session_transition(first, pending, expected_parent_revision_sha256=first.sha256)
    with pytest.raises(ValueError, match="stale session CAS"):
        validate_session_transition(first, pending, expected_parent_revision_sha256=h("stale"))
    unknown = clone_with_new_revision(
        pending,
        state=RecordingSessionState.UNKNOWN,
        operation_id="session-operation-3",
    )
    validate_session_transition(pending, unknown, expected_parent_revision_sha256=pending.sha256)
    replay = clone_with_new_revision(
        unknown,
        state=RecordingSessionState.PREFLIGHT_PENDING,
        operation_id="session-operation-4",
    )
    with pytest.raises(ValueError, match="forbidden"):
        validate_session_transition(unknown, replay, expected_parent_revision_sha256=unknown.sha256)


def test_all_record_revisions_use_exact_cas_and_terminal_states_do_not_replay() -> None:
    planned = attempt()
    capturing = clone_with_new_revision(
        planned,
        state=SegmentAttemptState.CAPTURING,
        operation_id="attempt-operation-capturing",
    )
    validate_attempt_transition(
        planned,
        capturing,
        expected_parent_revision_sha256=planned.sha256,
    )
    with pytest.raises(ValueError, match="stale append-only CAS"):
        validate_append_only_revision(
            planned,
            capturing,
            expected_parent_revision_sha256=h("stale"),
        )
    unknown = clone_with_new_revision(
        capturing,
        state=SegmentAttemptState.UNKNOWN,
        operation_id="attempt-operation-unknown",
    )
    validate_attempt_transition(
        capturing,
        unknown,
        expected_parent_revision_sha256=capturing.sha256,
    )
    replay = clone_with_new_revision(
        unknown,
        state=SegmentAttemptState.CAPTURING,
        operation_id="attempt-operation-replay",
    )
    with pytest.raises(ValueError, match="forbidden"):
        validate_attempt_transition(
            unknown,
            replay,
            expected_parent_revision_sha256=unknown.sha256,
        )

    captured = candidate()
    pending = clone_with_new_revision(
        captured,
        state=CandidateState.REVIEW_PENDING,
        operation_id="candidate-operation-review",
    )
    validate_candidate_transition(
        captured,
        pending,
        expected_parent_revision_sha256=captured.sha256,
    )


def test_capture_mode_change_requires_new_preflight_and_drops_admission() -> None:
    first = session()
    changed = clone_with_new_revision(
        first,
        state=RecordingSessionState.PREFLIGHT_PENDING,
        capture_mode=CaptureMode.OWNER_APPROVED_NON_DATASET_TECHNICAL_PROBE,
        readiness_evaluation_state=ReadinessEvaluationState.NOT_EVALUATED,
        readiness_evaluation_sha256=h("new-preflight"),
        operation_id="session-operation-2",
    )
    validate_session_transition(first, changed, expected_parent_revision_sha256=first.sha256)
    bad = replace(changed, state=RecordingSessionState.READY, readiness_evaluation_state=ReadinessEvaluationState.TECHNICAL_PROBE_READY)
    with pytest.raises(ValueError, match="capture_mode change requires"):
        validate_session_transition(first, bad, expected_parent_revision_sha256=first.sha256)


def test_cancel_retained_evidence_is_explicit_and_complete_candidate_not_hidden() -> None:
    plain = {
        **cancel_none(),
        "cancel_ack_state": "ACK_VERIFIED",
    }
    assert session(state=RecordingSessionState.CANCELLED, cancel=plain).state is RecordingSessionState.CANCELLED
    retained = {
        **plain,
        "external_work_present": True,
        "retained_evidence_present": True,
        "retained_evidence_ledger_sha256": h("retained-ledger"),
        "retention_state": "BOUND",
        "encryption_recovery_state": "PASS",
    }
    record = session(state=RecordingSessionState.CANCELLED_WITH_RETAINED_EVIDENCE, cancel=retained)
    assert record.state is RecordingSessionState.CANCELLED_WITH_RETAINED_EVIDENCE
    with pytest.raises(ValueError, match="plain CANCELLED"):
        session(state=RecordingSessionState.CANCELLED, cancel=retained)
    with pytest.raises(ValueError, match="complete Candidate"):
        session(
            state=RecordingSessionState.CANCELLED_WITH_RETAINED_EVIDENCE,
            cancel={**retained, "complete_candidate_present": True},
        )


def test_resume_requires_new_exact_attempt_from_sentence_start() -> None:
    prior = attempt(state=SegmentAttemptState.INCOMPLETE)
    resumed = attempt(
        attempt_id="attempt-2",
        attempt_number=2,
        parent_attempt=prior.sha256,
        state=SegmentAttemptState.PLANNED,
    )
    validate_resume_attempt(prior, resumed)
    with pytest.raises(ValueError, match="exact segment/cue/sentence/text/start anchor"):
        validate_resume_attempt(prior, replace(resumed, sentence_start_anchor=1))
    with pytest.raises(ValueError, match="increment by one"):
        validate_resume_attempt(prior, replace(resumed, attempt_number=3))
    with pytest.raises(ValueError, match="new P-VS-3A attempt identity"):
        validate_resume_attempt(prior, replace(resumed, attempt_id=prior.attempt_id))


def execution_authorization(ready: VoiceRecordingSessionRevision, *, scope: str = "START") -> dict[str, object]:
    body: dict[str, object] = {
        "contract_state": "BOUND_VERIFIED",
        "authorization_id": "synthetic-start-authorization-1",
        "authorization_revision": 1,
        "authority_kind": "APPROVED_SYNTHETIC_TEST_AUTHORITY",
        "project_id": ready.project_id,
        "recording_session_id": ready.recording_session_id,
        "session_revision_sha256": ready.sha256,
        "capture_mode": ready.capture_mode.value,
        "readiness_evaluation_sha256": ready.readiness_evaluation_sha256,
        "selected_source_binding_sha256": sha256_bytes(canonical_json_bytes(ready.selected_source_binding)),
        "consent_current_evaluation_sha256": ready.consent_current_evaluation["current_evaluation_sha256"],
        "approved_text_binding_sha256": ready.approved_text_binding["source_text_binding_sha256"],
        "scope": scope,
        "issued_at": NOW,
        "expires_at": LATER,
        "one_shot": True,
        "replay_policy": "DENY_REPLAY",
        "evidence_ref": "synthetic-test-authority-evidence-1",
        "evidence_sha256": h("synthetic-authority-evidence"),
    }
    body["authorization_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def command(ready: VoiceRecordingSessionRevision, auth: dict[str, object], *, kind: str = "START") -> dict[str, object]:
    return {
        "command_id": "capture-command-1",
        "operation_id": "capture-command-operation-1",
        "command": kind,
        "project_id": ready.project_id,
        "recording_session_id": ready.recording_session_id,
        "session_revision_sha256": ready.sha256,
        "capture_mode": ready.capture_mode.value,
        "readiness_evaluation_sha256": ready.readiness_evaluation_sha256,
        "selected_source_binding_sha256": sha256_bytes(canonical_json_bytes(ready.selected_source_binding)),
        "consent_current_evaluation_sha256": ready.consent_current_evaluation["current_evaluation_sha256"],
        "approved_text_binding_sha256": ready.approved_text_binding["source_text_binding_sha256"],
        "execution_authorization_binding": auth,
        "segment_id": "segment-1",
        "attempt_id": "attempt-1",
        "attempt_number": 1,
        "parent_attempt_sha256": None,
        "cue_id": "cue-1",
        "sentence_id": "sentence-1",
        "source_text_binding_sha256": ready.approved_text_binding["source_text_binding_sha256"],
        "sentence_start_anchor": 0,
        "dispatch_started": False,
        "runtime_probe_started": False,
    }


def test_structured_execution_authorization_is_not_forgeable_boolean_or_dispatch() -> None:
    ready = session(state=RecordingSessionState.READY, readiness=ReadinessEvaluationState.TEST_READY)
    auth = execution_authorization(ready)
    admitted = evaluate_capture_command(ready, command(ready, auth), evaluated_at="2026-08-15T13:30:00Z")
    assert admitted.admitted is True
    assert admitted.reason_codes == ("ADMITTED_METADATA_ONLY",)
    assert admitted.dispatch_authorized is False
    assert admitted.dispatch_started is False
    forged = command(ready, auth)
    forged["execution_authorized"] = True
    with pytest.raises(ValueError, match="incomplete or unknown"):
        evaluate_capture_command(ready, forged, evaluated_at="2026-08-15T13:30:00Z")
    effect = command(ready, auth)
    effect["dispatch_started"] = True
    with pytest.raises(ValueError, match="cannot claim dispatch"):
        evaluate_capture_command(ready, effect, evaluated_at="2026-08-15T13:30:00Z")


@pytest.mark.parametrize(
    ("mutator", "reason"),
    [
        (lambda row: row.update(project_id="other-project"), "AUTHORIZATION_PROJECT_ID_MISMATCH"),
        (lambda row: row.update(capture_mode="OWNER_APPROVED_NON_DATASET_TECHNICAL_PROBE"), "AUTHORIZATION_CAPTURE_MODE_MISMATCH"),
        (lambda row: row.update(scope="RESUME"), "AUTHORIZATION_SCOPE_MISMATCH"),
        (lambda row: row.update(approved_text_binding_sha256=h("wrong-text")), "AUTHORIZATION_APPROVED_TEXT_BINDING_SHA256_MISMATCH"),
        (lambda row: row.update(consent_current_evaluation_sha256=h("wrong-consent")), "AUTHORIZATION_CONSENT_CURRENT_EVALUATION_SHA256_MISMATCH"),
    ],
)
def test_authorization_exact_scope_and_binding_mismatches_fail_closed(mutator, reason: str) -> None:
    ready = session(state=RecordingSessionState.READY, readiness=ReadinessEvaluationState.TEST_READY)
    auth = execution_authorization(ready)
    mutator(auth)
    auth["authorization_sha256"] = sha256_bytes(canonical_json_bytes({
        key: value for key, value in auth.items() if key != "authorization_sha256"
    }))
    report = evaluate_capture_command(ready, command(ready, auth), evaluated_at="2026-08-15T13:30:00Z")
    assert report.admitted is False
    assert reason in report.reason_codes


def test_authorization_checksum_tamper_is_rejected_before_admission() -> None:
    ready = session(state=RecordingSessionState.READY, readiness=ReadinessEvaluationState.TEST_READY)
    auth = execution_authorization(ready)
    auth["evidence_sha256"] = h("tampered-evidence")
    with pytest.raises(ValueError, match="ExecutionAuthorizationBinding checksum mismatch"):
        evaluate_capture_command(
            ready,
            command(ready, auth),
            evaluated_at="2026-08-15T13:30:00Z",
        )


def test_authorization_expiry_and_one_shot_replay_fail_closed() -> None:
    ready = session(state=RecordingSessionState.READY, readiness=ReadinessEvaluationState.TEST_READY)
    auth = execution_authorization(ready)
    expired = evaluate_capture_command(ready, command(ready, auth), evaluated_at="2026-08-15T15:00:00Z")
    assert "AUTHORIZATION_EXPIRED_OR_NOT_YET_VALID" in expired.reason_codes
    replay = evaluate_capture_command(
        ready,
        command(ready, auth),
        evaluated_at="2026-08-15T13:30:00Z",
        consumed_authorization_sha256s=(auth["authorization_sha256"],),
    )
    assert "AUTHORIZATION_REPLAY_REJECTED" in replay.reason_codes


def test_resume_command_binds_exact_new_attempt_lineage() -> None:
    ready = session(state=RecordingSessionState.READY, readiness=ReadinessEvaluationState.TEST_READY)
    prior = attempt(state=SegmentAttemptState.INCOMPLETE)
    resumed = attempt(attempt_id="attempt-2", attempt_number=2, parent_attempt=prior.sha256)
    auth = execution_authorization(ready, scope="RESUME")
    row = command(ready, auth, kind="RESUME")
    row.update({
        "attempt_id": resumed.attempt_id,
        "attempt_number": resumed.attempt_number,
        "parent_attempt_sha256": resumed.parent_attempt_sha256,
    })
    report = evaluate_capture_command(
        ready,
        row,
        evaluated_at="2026-08-15T13:30:00Z",
        previous_attempt=prior,
        new_attempt=resumed,
    )
    assert report.admitted is True
    bad = dict(row)
    bad["attempt_id"] = "adapter-invented-attempt"
    rejected = evaluate_capture_command(
        ready,
        bad,
        evaluated_at="2026-08-15T13:30:00Z",
        previous_attempt=prior,
        new_attempt=resumed,
    )
    assert "RESUME_ATTEMPT_ID_MISMATCH" in rejected.reason_codes


def test_candidate_review_is_separate_and_effect_gates_do_not_autostart_training() -> None:
    captured = candidate()
    assert captured.state is CandidateState.CAPTURED_CANDIDATE
    with pytest.raises(ValueError, match="Review/Asset/Consent/quality"):
        candidate(state=CandidateState.APPROVED_FOR_ADOPTION)
    approved_candidate = candidate(state=CandidateState.APPROVED_FOR_ADOPTION, bound_asset=True)
    assert approved_candidate.dataset_adoption_receipt_binding["contract_state"] == "CANONICAL_REF_NOT_PROVIDED"
    with pytest.raises(ValueError, match="verified external adoption receipt"):
        replace(approved_candidate, state=CandidateState.ADOPTED_TO_DATASET)
    with pytest.raises(ValueError, match="cannot authorize training"):
        DatasetCandidateReviewDecision(
            project_id="project-opaque-1",
            recording_session_id="recording-session-1",
            review_decision_id="review-1",
            revision=1,
            parent_revision_sha256=None,
            candidate_id="candidate-1",
            candidate_revision_sha256=approved_candidate.sha256,
            decision=ReviewDecision.APPROVE_FOR_ADOPTION,
            reviewer_kind="OWNER",
            human_gate_evidence_ref="owner-review-evidence-1",
            human_gate_evidence_sha256=h("review"),
            asset_binding=asset_bound(),
            consent_current_evaluation=consent_evaluation(),
            calibration_binding=calibration_pass(),
            decided_at=NOW,
            training_start_authorized=True,
            body_authority_flags=BODY_AUTHORITY_FLAGS,
        )

    rejected = replace(
        captured,
        state=CandidateState.REJECTED,
        review_decision_binding=review_decision("REJECT"),
    )
    assert rejected.state is CandidateState.REJECTED
    with pytest.raises(ValueError, match="exact Owner ReviewDecision"):
        replace(captured, state=CandidateState.RERECORD)


def test_reserved_session_adopted_state_requires_external_effect_receipt() -> None:
    with pytest.raises(ValueError, match="verified external adoption receipt"):
        session(state=RecordingSessionState.ADOPTED_TO_DATASET)


def test_consent_revoked_and_quality_unknown_block_adoption_approval() -> None:
    common = dict(
        project_id="project-opaque-1",
        recording_session_id="recording-session-1",
        review_decision_id="review-1",
        revision=1,
        parent_revision_sha256=None,
        candidate_id="candidate-1",
        candidate_revision_sha256=h("candidate"),
        decision=ReviewDecision.APPROVE_FOR_ADOPTION,
        reviewer_kind="OWNER",
        human_gate_evidence_ref="owner-review-evidence-1",
        human_gate_evidence_sha256=h("review"),
        asset_binding=asset_bound(),
        calibration_binding=calibration_pass(),
        decided_at=NOW,
        training_start_authorized=False,
        body_authority_flags=BODY_AUTHORITY_FLAGS,
    )
    with pytest.raises(ValueError, match="gates are incomplete"):
        DatasetCandidateReviewDecision(**common, consent_current_evaluation=consent_evaluation("REVOKED"))
    with pytest.raises(ValueError, match="gates are incomplete"):
        DatasetCandidateReviewDecision(
            **{**common, "calibration_binding": calibration_unresolved()},
            consent_current_evaluation=consent_evaluation(),
        )


def test_public_projection_redacts_private_biometric_and_text_linkage() -> None:
    public = session().to_public_dict()
    serialized = json.dumps(public, ensure_ascii=False, sort_keys=True)
    for secret in (
        "owner-subject-private", "owner-private-recording", "VOICE_RECORDING",
        "consent-evidence-private", "source-private-1", "approved-text-revision-7",
    ):
        assert secret not in serialized
    assert public["projection"] == "PUBLIC_REDACTED"
    assert public["public_projection_sha256"].startswith("sha256:")
    assert public["body_authority_flags"] == BODY_AUTHORITY_FLAGS
    candidate_public = candidate(
        state=CandidateState.APPROVED_FOR_ADOPTION,
        bound_asset=True,
    ).to_public_dict()
    candidate_text = json.dumps(candidate_public, ensure_ascii=False, sort_keys=True)
    assert "label_proposals" not in candidate_text
    assert "approved_labels" not in candidate_text
    assert "ASSET-" not in candidate_text
    assert h("asset-bytes") not in candidate_text


def test_unknown_unresolved_and_project_maintenance_are_not_synthesized_as_success() -> None:
    with pytest.raises(ValueError, match="unresolved resource binding"):
        replace(session(), resource_admission_binding={**resource_unresolved(), "decision_state": "ADMITTED"})
    bad_job = {
        "contract_state": "BOUND_VERIFIED",
        "job_ref": "job-1",
        "job_sha256": h("job"),
        "checkpoint_ref": "checkpoint-1",
        "checkpoint_sha256": h("checkpoint"),
        "job_state": "PROJECT_MAINTENANCE",
    }
    with pytest.raises(ValueError, match="PROJECT_MAINTENANCE"):
        replace(session(), capture_durable_job_binding=bad_job)


def test_no_root_aliases_or_unknown_serialized_types_are_accepted() -> None:
    document = session().to_private_dict()
    document["record_type"] = "RecordingSegmentRevision"
    with pytest.raises(ValueError, match="unknown recording contract"):
        parse_record(document)
    assert "SemanticSessionCheckpoint" not in schema()["$defs"]
    assert "RecordingSegmentRevision" not in schema()["$defs"]
