from __future__ import annotations

import copy
import hashlib
import json
from importlib import resources
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task098_runtime_transcription_control import (
    ABSENCE_DOMAIN,
    ADJUDICATION_DOMAIN,
    BARRIER_DOMAIN,
    CANCEL_OUTCOME_DOMAIN,
    CANCEL_REQUEST_DOMAIN,
    TERMINAL_COMMIT_DOMAIN,
    RuntimeTranscriptionAdjudicationDecisionV1,
    RuntimeTranscriptionCancelOutcomeV1,
    RuntimeTranscriptionCancelRequestV1,
    RuntimeTranscriptionCommitBarrierV1,
    RuntimeTranscriptionGenerationAbsenceObservationV1,
    RuntimeTranscriptionLeaseFactV1,
    RuntimeTranscriptionReducerFactsV1,
    RuntimeTranscriptionTerminalClosureCommitV1,
    reduce_runtime_transcription_control,
    validate_schema_mirror,
)


JOB = "JOB-" + "0" * 26
LEASE_OP = "OP-" + "1" * 26
RUNTIME_OP = "OP-" + "2" * 26
SLOT_OP = "OP-" + "3" * 26
REQUEST_OP = "OP-" + "4" * 26
ADJUDICATION_OP = "OP-" + "5" * 26
ASSET = "ASSET-" + "6" * 26
PROJECT = "bvp-test"
SOURCE = "sha256:" + "a" * 64
REQUEST_SHA = "sha256:" + "b" * 64
DECISION_SHA = "sha256:" + "c" * 64
PUBLICATION_SHA = "sha256:" + "d" * 64
ADMISSION = "task098-runtime-admission:v2:" + "a" * 64 + ":" + "c" * 64
T0 = "2026-09-20T06:00:00Z"


def schema_document() -> dict:
    with resources.files("ai_video_production.schema_resources").joinpath(
        "task098-runtime-transcription-control.schema.json"
    ).open("r", encoding="utf-8") as source:
        return json.load(source)


def schema_validate(definition: str, value: dict) -> None:
    document = schema_document()
    Draft202012Validator({
        "$schema": document["$schema"],
        "$defs": document["$defs"],
        "$ref": f"#/$defs/{definition}",
    }).validate(value)


def guard_key() -> str:
    body = {
        "coordination_version": "1.0.0",
        "project_id": PROJECT,
        "source_asset_id": ASSET,
        "source_asset_sha256": SOURCE,
    }
    return "task036-transcription-cross-version-" + hashlib.sha256(
        b"bvp.task098.task036-cross-version-guard.v1\0" + canonical_json_bytes(body)
    ).hexdigest()


def lease(**changes) -> RuntimeTranscriptionLeaseFactV1:
    key = guard_key()
    values = {
        "production_job_id": JOB,
        "project_id": PROJECT,
        "source_asset_id": ASSET,
        "source_asset_sha256": SOURCE,
        "operation_id": LEASE_OP,
        "command_type": "task036.local_transcription.cross_version_guard.v1",
        "idempotency_key": key,
        "status": "IN_PROGRESS",
        "attempt": 0,
        "result_ref": "task098-runtime-owner:v2:" + key.rsplit("-", 1)[-1],
    }
    values.update(changes)
    return RuntimeTranscriptionLeaseFactV1(**values)


def cancel_request() -> RuntimeTranscriptionCancelRequestV1:
    return RuntimeTranscriptionCancelRequestV1.create(
        cancel_request_id=REQUEST_OP,
        runtime_operation_id=RUNTIME_OP,
        slot_operation_id=SLOT_OP,
        source_asset_sha256=SOURCE,
        runtime_admission_ref=ADMISSION,
        runtime_request_sha256=REQUEST_SHA,
        runtime_decision_sha256=DECISION_SHA,
        expected_attempt=1,
        requested_at=T0,
    )


def cancel_outcome(request, outcome: str, *, started: bool | None = None):
    matrix = {
        "CANCELLED_BEFORE_PROVIDER_EFFECT": (False, True, "PRE_PROVIDER"),
        "CANCELLED_AFTER_COOPERATIVE_BOUNDARY": (True, True, "COOPERATIVE_CHECKPOINT"),
        "STOP_NOT_CONFIRMED": (False if started is None else started, False, "NONE"),
    }
    execution, stopped, evidence = matrix[outcome]
    return RuntimeTranscriptionCancelOutcomeV1.create(
        cancel_request_sha256=request.record_sha256,
        runtime_operation_id=RUNTIME_OP,
        slot_operation_id=SLOT_OP,
        source_asset_sha256=SOURCE,
        runtime_admission_ref=ADMISSION,
        runtime_request_sha256=REQUEST_SHA,
        runtime_decision_sha256=DECISION_SHA,
        expected_attempt=1,
        outcome=outcome,
        provider_execution_started=execution,
        provider_stop_confirmed=stopped,
        stop_evidence=evidence,
        acknowledged_at=T0,
    )


def adjudication():
    return RuntimeTranscriptionAdjudicationDecisionV1.create(
        adjudication_id=ADJUDICATION_OP,
        runtime_operation_id=RUNTIME_OP,
        slot_operation_id=SLOT_OP,
        source_asset_sha256=SOURCE,
        runtime_admission_ref=ADMISSION,
        runtime_request_sha256=REQUEST_SHA,
        runtime_decision_sha256=DECISION_SHA,
        expected_attempt=1,
        decided_at=T0,
    )


def barrier(owner: str, closure=None):
    return RuntimeTranscriptionCommitBarrierV1.create(
        runtime_operation_id=RUNTIME_OP,
        slot_operation_id=SLOT_OP,
        source_asset_sha256=SOURCE,
        runtime_admission_ref=ADMISSION,
        expected_attempt=1,
        barrier_owner=owner,
        closure_record_sha256=None if closure is None else closure.record_sha256,
        acquired_at=T0,
    )


def absence(bound, observation="EXACT_GENERATION_ABSENT"):
    return RuntimeTranscriptionGenerationAbsenceObservationV1.create(
        runtime_operation_id=RUNTIME_OP,
        slot_operation_id=SLOT_OP,
        source_asset_sha256=SOURCE,
        runtime_admission_ref=ADMISSION,
        expected_attempt=1,
        commit_barrier_sha256=bound.record_sha256,
        observation=observation,
        observed_at=T0,
    )


def terminal_commit(closure, bound, observed, kind: str):
    prefix = (
        "task098-runtime-cancelled:v1:"
        if kind == "CONFIRMED_CANCEL"
        else "task098-runtime-adjudicated-failed:v1:"
    )
    return RuntimeTranscriptionTerminalClosureCommitV1.create(
        runtime_operation_id=RUNTIME_OP,
        slot_operation_id=SLOT_OP,
        source_asset_sha256=SOURCE,
        prior_runtime_admission_ref=ADMISSION,
        expected_attempt=1,
        closure_kind=kind,
        closure_record_sha256=closure.record_sha256,
        commit_barrier_sha256=bound.record_sha256,
        generation_absence_observation_sha256=observed.record_sha256,
        terminal_result_ref=prefix + closure.record_sha256.removeprefix("sha256:"),
        committed_at=T0,
    )


def facts(**changes) -> RuntimeTranscriptionReducerFactsV1:
    values = {
        "production_job_id": JOB,
        "project_id": PROJECT,
        "source_asset_id": ASSET,
        "source_asset_sha256": SOURCE,
        "runtime_operation_id": RUNTIME_OP,
        "operation_status": "IN_PROGRESS",
        "operation_attempt": 1,
        "operation_result_ref": ADMISSION,
        "slot_operation_id": SLOT_OP,
        "slot_status": "IN_PROGRESS",
        "slot_result_ref": RUNTIME_OP,
        "recovery_state": "ACTIVE_UNKNOWN",
        "phase": "PROVIDER_RUNNING",
        "lease": lease(),
    }
    values.update(changes)
    return RuntimeTranscriptionReducerFactsV1(**values)


def assert_projection(value: dict) -> None:
    assert set(value) == {
        "control_mode", "phase", "cancel_state", "adjudication_state",
        "available_action", "status_label", "provider_execution_started",
        "provider_execution_known", "provider_stop_confirmed", "stop_evidence",
        "slot_release_allowed", "no_replay",
    }
    schema_validate("public_projection", value)
    assert not any(key in value for key in (
        "operation_id", "slot_operation_id", "source_asset_sha256", "record_sha256",
        "timestamp", "path", "exception", "percentage", "eta", "segment_count",
    ))


def test_schema_mirror_and_all_record_round_trips_are_exact() -> None:
    validate_schema_mirror()
    root = Path(__file__).parents[1]
    assert (root / "schemas/task098-runtime-transcription-control.schema.json").read_bytes() == (
        root / "src/ai_video_production/schema_resources/task098-runtime-transcription-control.schema.json"
    ).read_bytes()
    request = cancel_request()
    before = cancel_outcome(request, "CANCELLED_BEFORE_PROVIDER_EFFECT")
    human = adjudication()
    pub = barrier("PUBLICATION")
    close = barrier("TERMINAL_CLOSURE", before)
    observed = absence(close)
    committed = terminal_commit(before, close, observed, "CONFIRMED_CANCEL")
    rows = (
        ("cancel_request", request, RuntimeTranscriptionCancelRequestV1, CANCEL_REQUEST_DOMAIN),
        ("cancel_outcome", before, RuntimeTranscriptionCancelOutcomeV1, CANCEL_OUTCOME_DOMAIN),
        ("adjudication_decision", human, RuntimeTranscriptionAdjudicationDecisionV1, ADJUDICATION_DOMAIN),
        ("commit_barrier", pub, RuntimeTranscriptionCommitBarrierV1, BARRIER_DOMAIN),
        ("generation_absence", observed, RuntimeTranscriptionGenerationAbsenceObservationV1, ABSENCE_DOMAIN),
        ("terminal_commit", committed, RuntimeTranscriptionTerminalClosureCommitV1, TERMINAL_COMMIT_DOMAIN),
    )
    for definition, record, record_type, domain in rows:
        value = record.to_dict()
        schema_validate(definition, value)
        assert record_type.from_dict(json.loads(json.dumps(value))).to_dict() == value
        body = {key: item for key, item in value.items() if key != "record_sha256"}
        assert record.record_sha256 == sha256_bytes(domain + canonical_json_bytes(body))


@pytest.mark.parametrize("factory", [
    cancel_request,
    lambda: cancel_outcome(cancel_request(), "CANCELLED_AFTER_COOPERATIVE_BOUNDARY"),
    adjudication,
    lambda: barrier("PUBLICATION"),
])
def test_records_reject_unknown_fields_and_tampering(factory) -> None:
    record = factory()
    value = record.to_dict()
    with pytest.raises(ValueError):
        type(record).from_dict(value | {"private_path": "C:\\private\\voice.wav"})
    tampered = copy.deepcopy(value)
    key = next(key for key in value if key not in {"record_sha256", "contract_version", "no_replay"})
    tampered[key] = "sha256:" + "f" * 64 if "sha256" in key else "tampered"
    with pytest.raises(ValueError):
        type(record).from_dict(tampered)


@pytest.mark.parametrize("outcome,started,stopped,evidence", [
    ("CANCELLED_BEFORE_PROVIDER_EFFECT", False, False, "PRE_PROVIDER"),
    ("CANCELLED_AFTER_COOPERATIVE_BOUNDARY", False, True, "COOPERATIVE_CHECKPOINT"),
    ("STOP_NOT_CONFIRMED", True, True, "NONE"),
    ("STOP_NOT_CONFIRMED", False, False, "PRE_PROVIDER"),
])
def test_cancel_outcome_matrix_rejects_false_stop_claims(outcome, started, stopped, evidence) -> None:
    request = cancel_request()
    with pytest.raises(ValueError):
        RuntimeTranscriptionCancelOutcomeV1.create(
            cancel_request_sha256=request.record_sha256,
            runtime_operation_id=RUNTIME_OP,
            slot_operation_id=SLOT_OP,
            source_asset_sha256=SOURCE,
            runtime_admission_ref=ADMISSION,
            runtime_request_sha256=REQUEST_SHA,
            runtime_decision_sha256=DECISION_SHA,
            expected_attempt=1,
            outcome=outcome,
            provider_execution_started=started,
            provider_stop_confirmed=stopped,
            stop_evidence=evidence,
            acknowledged_at=T0,
        )


def test_lease_fact_is_concrete_and_cannot_accept_proof_flags() -> None:
    valid = lease()
    schema_validate("lease_fact", valid.to_dict())
    assert RuntimeTranscriptionLeaseFactV1.from_dict(valid.to_dict()) == valid
    with pytest.raises(ValueError):
        RuntimeTranscriptionLeaseFactV1.from_dict(valid.to_dict() | {"lease_valid": True})
    for field, value in (
        ("command_type", "foreign"), ("idempotency_key", "foreign"),
        ("status", "COMPLETED"), ("attempt", 1), ("result_ref", "foreign"),
    ):
        projection = reduce_runtime_transcription_control(facts(lease=lease(**{field: value})))
        assert projection["phase"] == "BLOCKED"
        assert projection["available_action"] == "NONE"


def test_no_operation_is_not_started_but_lease_without_operation_is_blocked() -> None:
    empty = RuntimeTranscriptionReducerFactsV1(
        production_job_id=JOB, project_id=PROJECT, source_asset_id=ASSET,
        source_asset_sha256=SOURCE,
    )
    projection = reduce_runtime_transcription_control(empty)
    assert_projection(projection)
    assert projection["phase"] == "NOT_STARTED"
    assert projection["provider_execution_known"] is True
    blocked = reduce_runtime_transcription_control(RuntimeTranscriptionReducerFactsV1(
        production_job_id=JOB, project_id=PROJECT, source_asset_id=ASSET,
        source_asset_sha256=SOURCE, lease=lease(),
    ))
    assert blocked["phase"] == "BLOCKED"


@pytest.mark.parametrize("phase,expected_started,expected_action,expected_label", [
    ("ADMISSION", False, "REQUEST_CANCEL", "実行許可を確認中です"),
    ("PROVIDER_STARTING", False, "REQUEST_CANCEL", "音声認識を開始しています"),
    ("PROVIDER_RUNNING", True, "REQUEST_CANCEL", "音声認識を実行中です"),
    ("PUBLICATION_VALIDATING", True, "REQUEST_CANCEL", "結果を検証中です"),
    ("PUBLICATION_COMMITTING", True, "NONE", "結果確定の排他状態を確認できません"),
    (None, False, "NONE", "実行状態を確認できません"),
])
def test_in_progress_phase_rows_are_exact(phase, expected_started, expected_action, expected_label) -> None:
    projection = reduce_runtime_transcription_control(facts(phase=phase))
    assert_projection(projection)
    assert projection["provider_execution_started"] is expected_started
    assert projection["provider_execution_known"] is (phase is not None)
    assert projection["available_action"] == expected_action
    assert projection["status_label"] == expected_label
    assert projection["provider_stop_confirmed"] is False
    assert projection["slot_release_allowed"] is False
    assert projection["no_replay"] is True


def test_publication_barrier_precedes_phase_and_disables_cancel() -> None:
    pub = barrier("PUBLICATION")
    projection = reduce_runtime_transcription_control(facts(barrier=pub, phase="PROVIDER_RUNNING"))
    assert_projection(projection)
    assert projection == {
        "control_mode": "PHASE_ONLY_V1", "phase": "PUBLICATION_COMMITTING",
        "cancel_state": "NOT_REQUESTED", "adjudication_state": "NOT_REQUIRED",
        "available_action": "NONE", "status_label": "結果の確定処理が開始されています",
        "provider_execution_started": True, "provider_execution_known": True,
        "provider_stop_confirmed": False, "stop_evidence": "NONE",
        "slot_release_allowed": False, "no_replay": True,
    }


def test_cancel_request_without_outcome_is_row7_and_stop_outcome_is_row8() -> None:
    request = cancel_request()
    pending = reduce_runtime_transcription_control(facts(cancel_request=request, phase="PROVIDER_RUNNING"))
    assert pending["cancel_state"] == "CANCEL_REQUESTED"
    assert pending["provider_execution_started"] is True
    assert pending["provider_execution_known"] is True
    stopped = cancel_outcome(request, "STOP_NOT_CONFIRMED", started=True)
    unknown = reduce_runtime_transcription_control(facts(cancel_request=request, cancel_outcome=stopped))
    assert unknown["cancel_state"] == "STOP_NOT_CONFIRMED"
    assert unknown["status_label"] == "Provider停止を確認できません"
    assert unknown["provider_execution_started"] is True
    assert unknown["provider_stop_confirmed"] is False


def test_typed_partial_offers_only_human_failed_no_replay_action() -> None:
    projection = reduce_runtime_transcription_control(facts(
        operation_status="PARTIAL", recovery_state="ADJUDICATION_REQUIRED_NO_PUBLICATION",
        phase=None,
    ))
    assert_projection(projection)
    assert projection["available_action"] == "CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY"
    assert projection["adjudication_state"] == "REQUIRED"
    assert projection["provider_execution_known"] is False
    assert projection["slot_release_allowed"] is False


@pytest.mark.parametrize("changes", [
    {"operation_result_ref": None},
    {"operation_result_ref": "foreign"},
    {"operation_result_ref": PUBLICATION_SHA},
    {
        "operation_result_ref":
            "task098-runtime-admission:v2:" + "e" * 64 + ":" + DECISION_SHA.removeprefix("sha256:")
    },
    {"operation_attempt": 0},
    {
        "operation_status": "PARTIAL",
        "recovery_state": "ADJUDICATION_REQUIRED_NO_PUBLICATION",
        "operation_result_ref": None,
        "phase": None,
    },
    {
        "operation_status": "PARTIAL",
        "recovery_state": "ADJUDICATION_REQUIRED_NO_PUBLICATION",
        "operation_result_ref": PUBLICATION_SHA,
        "phase": None,
    },
    {
        "operation_status": "PARTIAL",
        "recovery_state": "ADJUDICATION_REQUIRED_NO_PUBLICATION",
        "operation_result_ref":
            "task098-runtime-admission:v2:" + "e" * 64 + ":" + DECISION_SHA.removeprefix("sha256:"),
        "phase": None,
    },
])
def test_operation_state_ref_matrix_blocks_false_actions(changes) -> None:
    projection = reduce_runtime_transcription_control(facts(**changes))
    assert_projection(projection)
    assert projection["phase"] == "BLOCKED"
    assert projection["adjudication_state"] == "NOT_REQUIRED"
    assert projection["available_action"] == "NONE"
    assert projection["slot_release_allowed"] is False


def test_invalid_partial_lease_or_slot_does_not_offer_human_adjudication() -> None:
    base = {
        "operation_status": "PARTIAL",
        "recovery_state": "ADJUDICATION_REQUIRED_NO_PUBLICATION",
        "phase": None,
    }
    for changed in ({"lease": lease(status="COMPLETED")}, {"slot_result_ref": "OP-" + "7" * 26}):
        projection = reduce_runtime_transcription_control(facts(**base, **changed))
        assert projection["phase"] == "BLOCKED"
        assert projection["adjudication_state"] == "NOT_REQUIRED"
        assert projection["available_action"] == "NONE"


def test_foreign_nested_fact_types_fail_closed_without_attribute_errors() -> None:
    for changed in ({"lease": object()}, {"cancel_request": object()}):
        projection = reduce_runtime_transcription_control(facts(**changed))
        assert_projection(projection)
        assert projection["phase"] == "BLOCKED"
        assert projection["available_action"] == "NONE"


def test_cancel_records_cannot_shadow_non_active_operation_rows() -> None:
    request = cancel_request()
    stopped = cancel_outcome(request, "STOP_NOT_CONFIRMED", started=True)
    rows = (
        {
            "operation_status": "PARTIAL",
            "operation_result_ref": PUBLICATION_SHA,
            "recovery_state": "RECOVERABLE_PUBLICATION",
            "phase": None,
            "cancel_request": request,
        },
        {
            "operation_status": "COMPLETED",
            "operation_result_ref": PUBLICATION_SHA,
            "recovery_state": "VERIFICATION_ONLY",
            "slot_status": "PENDING",
            "phase": None,
            "cancel_request": request,
            "cancel_outcome": stopped,
        },
        {
            "operation_status": "FAILED",
            "phase": None,
            "cancel_request": request,
        },
    )
    for changed in rows:
        projection = reduce_runtime_transcription_control(facts(**changed))
        assert_projection(projection)
        assert projection["phase"] == "BLOCKED"
        assert projection["available_action"] == "NONE"
        assert projection["slot_release_allowed"] is False


@pytest.mark.parametrize("status,recovery,label,phase", [
    ("PARTIAL", "RECOVERABLE_PUBLICATION", "既存結果の復旧が必要です", "PUBLICATION_COMMITTING"),
    ("COMPLETED", "VERIFICATION_ONLY", "音声認識は完了しています", "COMPLETED"),
])
def test_publication_states_never_offer_a2r2_actions(status, recovery, label, phase) -> None:
    projection = reduce_runtime_transcription_control(facts(
        operation_status=status, operation_result_ref=PUBLICATION_SHA,
        recovery_state=recovery, phase=None,
        slot_status="PENDING" if status == "COMPLETED" else "IN_PROGRESS",
    ))
    assert projection["phase"] == phase
    assert projection["status_label"] == label
    assert projection["available_action"] == "NONE"
    assert projection["provider_execution_started"] is True
    assert projection["provider_stop_confirmed"] is False


def test_pending_and_uncommitted_failed_rows_are_closed() -> None:
    pending = reduce_runtime_transcription_control(facts(
        operation_status="PENDING", operation_attempt=0, operation_result_ref=None,
        slot_operation_id=None, slot_status=None, slot_result_ref=None, phase=None,
    ))
    assert pending["phase"] == "NOT_STARTED"
    assert pending["available_action"] == "NONE"
    failed = reduce_runtime_transcription_control(facts(
        operation_status="FAILED", operation_result_ref=ADMISSION,
        slot_status="IN_PROGRESS", phase=None,
    ))
    assert failed["phase"] == "BLOCKED"
    assert failed["status_label"] == "失敗状態を確認してください"


@pytest.mark.parametrize("outcome,expected_started,expected_label", [
    ("CANCELLED_BEFORE_PROVIDER_EFFECT", False, "Provider開始前にキャンセルしました"),
    ("CANCELLED_AFTER_COOPERATIVE_BOUNDARY", True, "協調停止を確認してキャンセルしました"),
])
def test_only_exact_confirmed_cancel_terminal_commit_allows_release(outcome, expected_started, expected_label) -> None:
    request = cancel_request()
    closed = cancel_outcome(request, outcome)
    bound = barrier("TERMINAL_CLOSURE", closed)
    observed = absence(bound)
    committed = terminal_commit(closed, bound, observed, "CONFIRMED_CANCEL")
    terminal_ref = "task098-runtime-cancelled:v1:" + closed.record_sha256.removeprefix("sha256:")
    projection = reduce_runtime_transcription_control(facts(
        operation_status="FAILED", operation_result_ref=terminal_ref, phase=None,
        cancel_request=request, cancel_outcome=closed, barrier=bound,
        generation_observation=observed, terminal_commit=committed,
    ))
    assert_projection(projection)
    assert projection["provider_execution_started"] is expected_started
    assert projection["provider_execution_known"] is True
    assert projection["provider_stop_confirmed"] is True
    assert projection["status_label"] == expected_label
    assert projection["slot_release_allowed"] is True


def test_human_terminal_commit_is_attestation_not_technical_stop() -> None:
    decision = adjudication()
    bound = barrier("TERMINAL_CLOSURE", decision)
    observed = absence(bound)
    committed = terminal_commit(decision, bound, observed, "HUMAN_ADJUDICATED_FAILED")
    terminal_ref = "task098-runtime-adjudicated-failed:v1:" + decision.record_sha256.removeprefix("sha256:")
    projection = reduce_runtime_transcription_control(facts(
        operation_status="FAILED", operation_result_ref=terminal_ref, phase=None,
        adjudication=decision, barrier=bound, generation_observation=observed,
        terminal_commit=committed,
    ))
    assert projection["adjudication_state"] == "CLOSED_FAILED_NO_REPLAY"
    assert projection["stop_evidence"] == "HUMAN_ATTESTATION"
    assert projection["provider_execution_known"] is False
    assert projection["provider_stop_confirmed"] is False
    assert projection["slot_release_allowed"] is True


def test_incomplete_terminal_barrier_and_generation_presence_remain_blocked() -> None:
    decision = adjudication()
    bound = barrier("TERMINAL_CLOSURE", decision)
    present = absence(bound, "PRESENT_PARTIAL_OR_UNKNOWN")
    projection = reduce_runtime_transcription_control(facts(
        operation_status="PARTIAL", recovery_state="ADJUDICATION_REQUIRED_NO_PUBLICATION",
        phase=None, adjudication=decision, barrier=bound, generation_observation=present,
    ))
    assert projection["phase"] == "BLOCKED"
    assert projection["status_label"] == "Human終了処理を安全に確定できません"
    assert projection["slot_release_allowed"] is False
    assert projection["provider_stop_confirmed"] is False


def test_mixed_coordinates_predecessors_and_wrong_slot_fail_closed() -> None:
    request = cancel_request()
    stopped = cancel_outcome(request, "CANCELLED_AFTER_COOPERATIVE_BOUNDARY")
    foreign = RuntimeTranscriptionCancelRequestV1.create(
        cancel_request_id=REQUEST_OP, runtime_operation_id=RUNTIME_OP,
        slot_operation_id=SLOT_OP, source_asset_sha256=SOURCE,
        runtime_admission_ref=ADMISSION, runtime_request_sha256="sha256:" + "e" * 64,
        runtime_decision_sha256=DECISION_SHA, expected_attempt=1, requested_at=T0,
    )
    for changed in (
        {"cancel_request": foreign, "cancel_outcome": stopped},
        {"slot_result_ref": "OP-" + "7" * 26},
        {"operation_attempt": 2, "cancel_request": request},
    ):
        projection = reduce_runtime_transcription_control(facts(**changed))
        assert projection["phase"] == "BLOCKED"
        assert projection["available_action"] == "NONE"
        assert projection["provider_stop_confirmed"] is False
        assert projection["slot_release_allowed"] is False


def test_public_projection_schema_rejects_percent_eta_counts_ids_and_unknown_actions() -> None:
    projection = reduce_runtime_transcription_control(facts(phase="ADMISSION"))
    for field, value in (
        ("progress_percent", 50), ("eta_seconds", 10), ("segment_count", 2),
        ("runtime_operation_id", RUNTIME_OP), ("source_path", "C:\\private\\voice.wav"),
    ):
        invalid = projection | {field: value}
        with pytest.raises(Exception):
            schema_validate("public_projection", invalid)
    invalid = dict(projection)
    invalid["available_action"] = "RETRY"
    with pytest.raises(Exception):
        schema_validate("public_projection", invalid)
