from __future__ import annotations

import copy
import json
import pickle
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task083_voice_training_resource_reservation import (
    ReservationState,
    Task083ExecutionResourceReservationReceiptV1,
    Task083FixtureExecutionResourceReservationReceiptV1,
    Task083FixtureReservationLedger,
    Task083ResourceReservationPlanV1,
    Task083ResourceReservationReadbackV1,
    compile_fixture_observation,
    compile_production_reservation_admission,
    compile_resource_reservation_plan,
    evaluate_fixture_reservation,
    open_fixture_reservation,
    parse_security_json,
    project_legacy_execution_resource_reservation_binding,
)
from ai_video_production.voice_dataset_revision import add_record_digest as dataset_digest
from ai_video_production.voice_training_run import (
    ExecutionResourceReservationBinding,
    add_record_digest as training_digest,
)


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SCHEMA = ROOT / "schemas" / "task083-voice-training-resource-reservation.schema.json"
PACKAGED_SCHEMA = (
    ROOT
    / "src"
    / "ai_video_production"
    / "schema_resources"
    / "task083-voice-training-resource-reservation.schema.json"
)
H = lambda value: sha256_bytes(value.encode("utf-8"))
RECEIPT_DOMAIN = b"BAI:TASK-083:RESOURCE-RESERVATION-RECEIPT:V1\x00"
READBACK_DOMAIN = b"BAI:TASK-083:RESOURCE-RESERVATION-READBACK:V1\x00"
OBSERVATION_DOMAIN = b"BAI:TASK-083:FIXTURE-OBSERVATION:V1\x00"


def rehash(value: dict[str, object], field: str, domain: bytes) -> dict[str, object]:
    value[field] = sha256_bytes(
        domain + canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    return value


def make_snapshot() -> dict[str, object]:
    return dataset_digest(
        {
            "record_type": "TrainingInputSnapshot",
            "snapshot_id": "snapshot-083-1",
            "revision": 1,
            "parent_snapshot_sha256": None,
            "project_id": "project-083",
            "dataset_id": "dataset-owner-voice",
            "voice_dataset_revision_ref": "voice-dataset-revision:7",
            "voice_dataset_revision_sha256": H("dataset-revision"),
            "selected_member_entry_sha256s": [H("member-1")],
            "exclusion_sha256s": [],
            "policy_revision_sha256": H("dataset-policy"),
            "readiness_sha256": H("readiness"),
            "current_consent_evaluation_sha256": H("consent"),
            "current_rights_evaluation_sha256": H("rights"),
            "created_at": "2026-09-06T00:00:00Z",
            "audio_body_persisted": False,
            "text_body_persisted": False,
            "dataset_mutation_authorized": False,
            "training_authorized": False,
        },
        "snapshot_sha256",
    )


def make_job() -> dict[str, object]:
    return training_digest(
        {
            "record_type": "TrainingDurableJobBinding",
            "contract_state": "BOUND_VERIFIED",
            "job_id": "job-voice-training-083",
            "operation_id": "operation-voice-training-083",
            "idempotency_key": "idempotency-voice-training-083",
            "job_kind": "VOICE_MODEL_TRAINING",
            "job_revision": 3,
            "job_revision_sha256": H("job-revision-3"),
            "job_state": "READY",
            "canonical_job_evidence_ref": "job-evidence:083:3",
            "canonical_job_evidence_sha256": H("job-evidence"),
            "identity_shared_with_dataset_adoption_job": False,
        },
        "binding_sha256",
    )


def make_plan(**changes: object) -> Task083ResourceReservationPlanV1:
    kwargs: dict[str, object] = {
        "training_input_snapshot": make_snapshot(),
        "training_job_binding": make_job(),
        "run_id": "run-083-1",
        "training_input_snapshot_ref": "training-snapshot:083:1",
        "recipe_revision_ref": "training-recipe:083:5",
        "recipe_revision_sha256": H("recipe-5"),
        "backend_id": "fixture-windows-backend",
        "backend_build_sha256": H("backend-build"),
        "runtime_revision": "runtime-1",
        "runtime_sha256": H("runtime"),
        "device_profile_ref": "device-profile:083:1",
        "device_profile_sha256": H("device-profile"),
        "capability_admission_sha256": H("task066-advisory-admission"),
        "resource_floor": {
            "cpu_units": 4,
            "ram_bytes": 8_000_000_000,
            "vram_bytes": 6_000_000_000,
            "disk_bytes": 20_000_000_000,
        },
        "resource_ceiling": {
            "cpu_units": 12,
            "ram_bytes": 32_000_000_000,
            "vram_bytes": 24_000_000_000,
            "disk_bytes": 100_000_000_000,
        },
        "policy_revision_sha256": H("task083-policy"),
        "issued_at": "2026-09-06T01:00:00Z",
        "expires_at": "2026-09-06T02:00:00Z",
    }
    kwargs.update(changes)
    return compile_resource_reservation_plan(**kwargs)  # type: ignore[arg-type]


def make_observation(
    plan: Task083ResourceReservationPlanV1,
    **changes: object,
):
    kwargs: dict[str, object] = {
        "granted_resources": {
            "cpu_units": 8,
            "ram_bytes": 16_000_000_000,
            "vram_bytes": 12_000_000_000,
            "disk_bytes": 50_000_000_000,
        },
        "thermal_state": "PASS",
        "power_state": "PASS",
        "gpu_present": True,
        "live_capability_present": True,
        "observed_at": "2026-09-06T01:10:00Z",
        "fresh_until": "2026-09-06T01:20:00Z",
    }
    kwargs.update(changes)
    return compile_fixture_observation(plan, **kwargs)  # type: ignore[arg-type]


def reserve(ledger: Task083FixtureReservationLedger, plan: Task083ResourceReservationPlanV1):
    return ledger.reserve(
        request_id="request-reserve-1",
        observation=make_observation(plan),
        evaluated_at="2026-09-06T01:15:00Z",
    )


def begin(ledger: Task083FixtureReservationLedger, plan: Task083ResourceReservationPlanV1):
    head = reserve(ledger, plan).to_dict()
    return ledger.begin_fixture_consumption(
        request_id="request-burn-1",
        expected_revision=head["reservation_revision"],
        expected_receipt_sha256=head["receipt_sha256"],
        observation=make_observation(
            plan,
            observed_at="2026-09-06T01:16:00Z",
            fresh_until="2026-09-06T01:25:00Z",
        ),
        observed_at="2026-09-06T01:17:00Z",
    )


def test_plan_is_body_free_fixture_only_and_current_production_is_blocked() -> None:
    plan = make_plan()
    body = plan.to_dict()
    assert body["fixture_only"] is True
    assert body["authority_created"] is False
    assert body["production_eligible"] is False
    assert body["durable_job_source_state"] == "NOT_AVAILABLE_CURRENT_SOURCE"
    assert body["voice_training_workload_mapping_state"] == "DISABLED_UNTIL_MAPPED"
    assert body["cpu_unit"] == "LOGICAL_PROCESSOR"
    assert body["memory_unit"] == "BYTES"
    assert body["audio_body_persisted"] is False
    assert body["environment_body_persisted"] is False
    assert body["native_reservation_invoked"] is False
    assert body["training_dispatched"] is False
    assert body["resource_effect_count"] == 0

    admission = compile_production_reservation_admission(
        plan, evaluated_at="2026-09-06T01:05:00Z"
    ).to_dict()
    assert admission["decision"] == "BLOCKED"
    assert admission["reason_codes"] == [
        "COMPOUND_OPERATION_NOT_BOUND",
        "DURABLE_JOB_SOURCE_NOT_AVAILABLE",
        "H3_AUTHORIZATION_V2_NOT_PRESENT",
        "NATIVE_BACKEND_NOT_IMPLEMENTED",
        "TASK084_DESTINATION_PLAN_NOT_BOUND",
        "VOICE_TRAINING_WORKLOAD_NOT_MAPPED",
    ]
    assert admission["resource_effect_count"] == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("run_id", r"C:\\private\\voice"),
        ("run_id", "C:private"),
        ("training_input_snapshot_ref", "/private/voice"),
        ("recipe_revision_ref", "../private"),
        ("backend_id", "file:private-model"),
    ],
)
def test_plan_rejects_host_private_paths(field: str, value: str) -> None:
    with pytest.raises(ValueError, match="body-free|host/private"):
        make_plan(**{field: value})


def test_plan_rejects_unbound_wrong_job_and_body_snapshot() -> None:
    job = make_job()
    job["contract_state"] = "UNKNOWN"
    job = training_digest(job, "binding_sha256")
    with pytest.raises(ValueError, match="BOUND_VERIFIED"):
        make_plan(training_job_binding=job)

    job = make_job()
    job["job_kind"] = "PROJECT_MAINTENANCE"
    job = training_digest(job, "binding_sha256")
    with pytest.raises(ValueError, match="Training Job"):
        make_plan(training_job_binding=job)

    snapshot = make_snapshot()
    snapshot["audio_body_persisted"] = True
    snapshot = dataset_digest(snapshot, "snapshot_sha256")
    with pytest.raises(ValueError, match="false|body-free"):
        make_plan(training_input_snapshot=snapshot)


def test_plan_rejects_floor_ceiling_and_expiry_errors() -> None:
    with pytest.raises(ValueError, match="floor exceeds ceiling"):
        make_plan(
            resource_floor={
                "cpu_units": 13,
                "ram_bytes": 8,
                "vram_bytes": 8,
                "disk_bytes": 8,
            }
        )
    with pytest.raises(ValueError, match="expiry"):
        make_plan(expires_at="2026-09-06T00:59:59Z")


def test_fixture_admission_checks_binding_freshness_and_resources() -> None:
    plan = make_plan()
    ready = evaluate_fixture_reservation(
        plan, make_observation(plan), evaluated_at="2026-09-06T01:15:00Z"
    ).to_dict()
    assert ready["decision"] == "READY_FIXTURE_ONLY"
    assert ready["reason_codes"] == []
    assert ready["authority_created"] is False
    assert ready["native_reservation_invoked"] is False
    assert ready["training_dispatched"] is False
    assert ready["resource_effect_count"] == 0

    stale = evaluate_fixture_reservation(
        plan,
        make_observation(plan, fresh_until="2026-09-06T01:11:00Z"),
        evaluated_at="2026-09-06T01:15:00Z",
    ).to_dict()
    assert stale["decision"] == "BLOCKED"
    assert "OBSERVATION_STALE" in stale["reason_codes"]

    resources = make_observation(plan).to_dict()["granted_resources"]
    resources["vram_bytes"] = 1
    denied = evaluate_fixture_reservation(
        plan,
        make_observation(plan, granted_resources=resources, gpu_present=False),
        evaluated_at="2026-09-06T01:15:00Z",
    ).to_dict()
    assert "VRAM_BYTES_BELOW_FLOOR" in denied["reason_codes"]
    assert "GPU_DISAPPEARED" in denied["reason_codes"]


@pytest.mark.parametrize(
    "field",
    [
        "project_id",
        "job_id",
        "job_revision_sha256",
        "run_id",
        "training_input_snapshot_sha256",
        "recipe_revision_sha256",
        "backend_id",
        "backend_build_sha256",
        "runtime_sha256",
        "device_profile_sha256",
        "policy_revision_sha256",
    ],
)
def test_fixture_observation_rejects_cross_binding_replay(field: str) -> None:
    plan = make_plan()
    observation = make_observation(plan).to_dict()
    observation[field] = H(f"wrong-{field}") if field.endswith("sha256") else f"wrong-{field}"
    rehash(observation, "observation_sha256", OBSERVATION_DOMAIN)
    decision = evaluate_fixture_reservation(
        plan, observation, evaluated_at="2026-09-06T01:15:00Z"
    ).to_dict()
    assert decision["decision"] == "BLOCKED"
    assert f"{field.upper()}_MISMATCH" in decision["reason_codes"]


@pytest.mark.parametrize("field", ["cpu_units", "ram_bytes", "vram_bytes", "disk_bytes"])
@pytest.mark.parametrize("direction", ["below", "above"])
def test_every_resource_floor_and_ceiling_is_enforced(field: str, direction: str) -> None:
    plan = make_plan()
    resources = make_observation(plan).to_dict()["granted_resources"]
    resources[field] = (
        plan.to_dict()["resource_floor"][field] - 1
        if direction == "below"
        else plan.to_dict()["resource_ceiling"][field] + 1
    )
    decision = evaluate_fixture_reservation(
        plan,
        make_observation(plan, granted_resources=resources),
        evaluated_at="2026-09-06T01:15:00Z",
    ).to_dict()
    assert f"{field.upper()}_{'BELOW_FLOOR' if direction == 'below' else 'ABOVE_CEILING'}" in decision[
        "reason_codes"
    ]


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"thermal_state": "FAIL"}, "THERMAL_NOT_PASS"),
        ({"power_state": "FAIL"}, "POWER_NOT_PASS"),
        ({"live_capability_present": False}, "LIVE_CAPABILITY_MISSING"),
        ({"observed_at": "2026-09-06T00:59:00Z"}, "CLOCK_ROLLBACK"),
        ({"observed_at": "2026-09-06T02:01:00Z", "fresh_until": "2026-09-06T02:02:00Z"}, "PLAN_EXPIRED"),
        ({"observed_at": "2026-09-06T02:00:00Z", "fresh_until": "2026-09-06T02:01:00Z"}, "PLAN_EXPIRED"),
        ({"fresh_until": "2026-09-06T01:15:00Z"}, "OBSERVATION_STALE"),
    ],
)
def test_fixture_admission_fault_vectors(change: dict[str, object], reason: str) -> None:
    plan = make_plan()
    decision = evaluate_fixture_reservation(
        plan,
        make_observation(plan, **change),
        evaluated_at="2026-09-06T01:15:00Z" if reason != "PLAN_EXPIRED" else "2026-09-06T02:01:00Z",
    ).to_dict()
    assert decision["decision"] == "BLOCKED"
    assert reason in decision["reason_codes"]


def test_fixture_state_machine_full_success_and_body_free_readback() -> None:
    plan = make_plan()
    ledger = open_fixture_reservation(plan, reservation_id="reservation-083-1")
    assert ledger.state is ReservationState.PREPARED
    assert ledger.readback(read_back_at="2026-09-06T01:05:00Z").to_dict()["event_count"] == 0
    reserved = reserve(ledger, plan)
    assert reserved.to_dict()["record_type"] == "Task083FixtureExecutionResourceReservationReceiptV1"
    assert reserved.to_dict()["state"] == "RESERVED"
    burned = ledger.begin_fixture_consumption(
        request_id="request-burn-1",
        expected_revision=1,
        expected_receipt_sha256=reserved.to_dict()["receipt_sha256"],
        observation=make_observation(
            plan,
            observed_at="2026-09-06T01:16:00Z",
            fresh_until="2026-09-06T01:25:00Z",
        ),
        observed_at="2026-09-06T01:17:00Z",
    )
    assert burned.to_dict()["state"] == "CONSUMPTION_STARTED"
    assert burned.to_dict()["training_dispatched"] is False
    assert burned.to_dict()["h3_authorization_v2_sha256"] is None
    consumed = ledger.finish_fixture_consumption(
        request_id="request-finish-1",
        expected_revision=2,
        expected_receipt_sha256=burned.to_dict()["receipt_sha256"],
        acknowledged=True,
        observed_at="2026-09-06T01:18:00Z",
    )
    assert consumed.to_dict()["state"] == "CONSUMED"
    readback = ledger.readback(read_back_at="2026-09-06T01:19:00Z").to_dict()
    assert readback["state"] == "CONSUMED"
    assert readback["live_capability_present"] is False
    assert readback["production_backend_invoked"] is False
    assert readback["training_started"] is False
    assert readback["resource_effect_count"] == ledger.resource_effect_count == 0
    with pytest.raises(ValueError, match="forbidden|requires"):
        ledger.expire(request_id="late-expire", observed_at="2026-09-06T03:00:00Z")


@pytest.mark.parametrize(
    ("acknowledged", "state", "reason"),
    [
        (False, "FAILED_CLOSED", "DURABLE_NEGATIVE_ACKNOWLEDGEMENT"),
        (None, "CONSUMPTION_UNKNOWN", "AMBIGUOUS_AFTER_BURN"),
    ],
)
def test_post_burn_failure_classification(
    acknowledged: bool | None, state: str, reason: str
) -> None:
    plan = make_plan()
    ledger = open_fixture_reservation(plan, reservation_id=f"reservation-{state}")
    burned = begin(ledger, plan).to_dict()
    negative_ack = (
        ledger.issue_fixture_durable_negative_acknowledgement(
            acknowledgement_id=f"negative-ack-{state}",
            expected_revision=burned["reservation_revision"],
            expected_receipt_sha256=burned["receipt_sha256"],
            observed_at="2026-09-06T01:17:30Z",
        )
        if acknowledged is False
        else None
    )
    result = ledger.finish_fixture_consumption(
        request_id=f"finish-{state}",
        expected_revision=burned["reservation_revision"],
        expected_receipt_sha256=burned["receipt_sha256"],
        acknowledged=acknowledged,
        observed_at="2026-09-06T01:18:00Z",
        negative_acknowledgement=negative_ack,
    ).to_dict()
    assert result["state"] == state
    assert reason in result["reason_codes"]
    assert result["durable_negative_acknowledgement_sha256"] == (
        negative_ack.to_dict()["acknowledgement_sha256"]
        if negative_ack is not None
        else None
    )
    with pytest.raises(ValueError, match="requires"):
        ledger.finish_fixture_consumption(
            request_id="reuse-after-burn",
            expected_revision=result["reservation_revision"],
            expected_receipt_sha256=result["receipt_sha256"],
            acknowledged=True,
            observed_at="2026-09-06T01:19:00Z",
        )


def test_caller_boolean_cannot_forge_post_burn_failed_closed() -> None:
    plan = make_plan()
    ledger = open_fixture_reservation(plan, reservation_id="reservation-unproven-negative")
    burned = begin(ledger, plan).to_dict()
    result = ledger.finish_fixture_consumption(
        request_id="finish-unproven-negative",
        expected_revision=burned["reservation_revision"],
        expected_receipt_sha256=burned["receipt_sha256"],
        acknowledged=False,
        observed_at="2026-09-06T01:18:00Z",
    ).to_dict()
    assert result["state"] == "CONSUMPTION_UNKNOWN"
    assert "DURABLE_NEGATIVE_ACKNOWLEDGEMENT_MISSING" in result["reason_codes"]
    assert result["durable_negative_acknowledgement_sha256"] is None

    other = make_plan(run_id="other-run")
    other_ledger = open_fixture_reservation(other, reservation_id="reservation-wrong-ack")
    other_burned = begin(other_ledger, other).to_dict()
    ack_ledger = open_fixture_reservation(plan, reservation_id="reservation-wrong-ack")
    ack_burned = begin(ack_ledger, plan).to_dict()
    wrong_ack = ack_ledger.issue_fixture_durable_negative_acknowledgement(
        acknowledgement_id="wrong-ledger-negative-ack",
        expected_revision=ack_burned["reservation_revision"],
        expected_receipt_sha256=ack_burned["receipt_sha256"],
        observed_at="2026-09-06T01:17:30Z",
    )
    with pytest.raises(ValueError, match="binding/currentness mismatch"):
        other_ledger.finish_fixture_consumption(
            request_id="finish-wrong-ack",
            expected_revision=other_burned["reservation_revision"],
            expected_receipt_sha256=other_burned["receipt_sha256"],
            acknowledged=False,
            negative_acknowledgement=wrong_ack,
            observed_at="2026-09-06T01:18:00Z",
        )

    third = open_fixture_reservation(plan, reservation_id="reservation-bool-int")
    third_burned = begin(third, plan).to_dict()
    with pytest.raises(ValueError, match="true, false, or null"):
        third.finish_fixture_consumption(
            request_id="finish-bool-int",
            expected_revision=third_burned["reservation_revision"],
            expected_receipt_sha256=third_burned["receipt_sha256"],
            acknowledged=1,  # type: ignore[arg-type]
            observed_at="2026-09-06T01:18:00Z",
        )


def test_expiry_and_restart_fail_closed_or_unknown() -> None:
    plan = make_plan()
    prepared = open_fixture_reservation(plan, reservation_id="reservation-expire")
    expired = prepared.expire(
        request_id="request-expire", observed_at="2026-09-06T02:00:01Z"
    ).to_dict()
    assert expired["state"] == "EXPIRED"

    reserved = open_fixture_reservation(plan, reservation_id="reservation-restart")
    reserve(reserved, plan)
    failed = reserved.restart_readback(
        request_id="request-restart",
        live_capability_present=False,
        observed_at="2026-09-06T01:16:00Z",
    ).to_dict()
    assert failed["state"] == "FAILED_CLOSED"

    burned = open_fixture_reservation(plan, reservation_id="reservation-burn-restart")
    begin(burned, plan)
    unknown = burned.restart_readback(
        request_id="request-burn-restart",
        live_capability_present=False,
        observed_at="2026-09-06T01:18:00Z",
    ).to_dict()
    assert unknown["state"] == "CONSUMPTION_UNKNOWN"


def test_duplicate_and_concurrent_consumption_is_one_use() -> None:
    plan = make_plan()
    ledger = open_fixture_reservation(plan, reservation_id="reservation-concurrent")
    reserved = reserve(ledger, plan).to_dict()

    def consume() -> dict[str, object]:
        try:
            return ledger.begin_fixture_consumption(
                request_id="same-burn-request",
                expected_revision=reserved["reservation_revision"],
                expected_receipt_sha256=reserved["receipt_sha256"],
                observation=make_observation(
                    plan,
                    observed_at="2026-09-06T01:16:00Z",
                    fresh_until="2026-09-06T01:25:00Z",
                ),
                observed_at="2026-09-06T01:17:00Z",
            ).to_dict()
        except ValueError as exc:
            return {"error": str(exc)}

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: consume(), range(2)))
    assert [result["state"] for result in results] == [
        "CONSUMPTION_STARTED",
        "CONSUMPTION_STARTED",
    ]
    assert {result["record_type"] for result in results} == {
        "Task083FixtureExecutionResourceReservationReceiptV1",
        "Task083FixtureResourceReservationReadbackV1",
    }
    assert ledger.readback(read_back_at="2026-09-06T01:18:00Z").to_dict()["event_count"] == 2

    with pytest.raises(ValueError, match="replay payload mismatch"):
        ledger.begin_fixture_consumption(
            request_id="same-burn-request",
            expected_revision=999,
            expected_receipt_sha256=H("wrong"),
            observation=make_observation(plan),
            observed_at="2026-09-06T01:17:00Z",
        )


def test_exact_duplicate_returns_current_readback_and_restart_requests_are_indexed() -> None:
    plan = make_plan()
    observation = make_observation(plan)
    ledger = open_fixture_reservation(plan, reservation_id="reservation-current-readback")
    reserved = ledger.reserve(
        request_id="reserve-current",
        observation=observation,
        evaluated_at="2026-09-06T01:15:00Z",
    ).to_dict()
    burned = ledger.begin_fixture_consumption(
        request_id="burn-current",
        expected_revision=reserved["reservation_revision"],
        expected_receipt_sha256=reserved["receipt_sha256"],
        observation=make_observation(
            plan,
            observed_at="2026-09-06T01:16:00Z",
            fresh_until="2026-09-06T01:25:00Z",
        ),
        observed_at="2026-09-06T01:17:00Z",
    ).to_dict()
    current = ledger.reserve(
        request_id="reserve-current",
        observation=observation,
        evaluated_at="2026-09-06T01:15:00Z",
    ).to_dict()
    assert current["record_type"] == "Task083FixtureResourceReservationReadbackV1"
    assert current["state"] == "CONSUMPTION_STARTED"
    assert current["head_receipt_sha256"] == burned["receipt_sha256"]
    assert current["read_back_at"] >= burned["event_at"]
    with pytest.raises(ValueError, match="clock rollback"):
        ledger.readback(read_back_at="2026-09-06T01:16:59Z")

    readback = ledger.restart_readback(
        request_id="restart-current",
        live_capability_present=True,
        observed_at="2026-09-06T01:18:00Z",
    ).to_dict()
    assert readback["state"] == "CONSUMPTION_UNKNOWN"
    duplicate = ledger.restart_readback(
        request_id="restart-current",
        live_capability_present=True,
        observed_at="2026-09-06T01:18:00Z",
    ).to_dict()
    assert duplicate["state"] == "CONSUMPTION_UNKNOWN"
    with pytest.raises(ValueError, match="replay payload mismatch"):
        ledger.restart_readback(
            request_id="restart-current",
            live_capability_present=False,
            observed_at="2026-09-06T01:18:00Z",
        )


def test_failed_restart_does_not_pollute_request_index() -> None:
    plan = make_plan()
    ledger = open_fixture_reservation(plan, reservation_id="reservation-restart-index")
    for _ in range(2):
        with pytest.raises(ValueError, match="clock rollback"):
            ledger.restart_readback(
                request_id="invalid-restart",
                live_capability_present=True,
                observed_at="2026-09-06T00:59:59Z",
            )
    corrected = ledger.restart_readback(
        request_id="corrected-restart",
        live_capability_present=True,
        observed_at="2026-09-06T01:05:00Z",
    ).to_dict()
    assert corrected["state"] == "PREPARED"
    assert corrected["event_count"] == 0


def test_stale_head_and_cross_plan_observation_fail_closed() -> None:
    plan = make_plan()
    ledger = open_fixture_reservation(plan, reservation_id="reservation-stale")
    reserved = reserve(ledger, plan).to_dict()
    with pytest.raises(ValueError, match="CAS head mismatch"):
        ledger.begin_fixture_consumption(
            request_id="stale-head",
            expected_revision=0,
            expected_receipt_sha256=reserved["receipt_sha256"],
            observation=make_observation(plan),
            observed_at="2026-09-06T01:17:00Z",
        )

    other = make_plan(run_id="run-083-other")
    decision = evaluate_fixture_reservation(
        plan,
        make_observation(other),
        evaluated_at="2026-09-06T01:15:00Z",
    ).to_dict()
    assert decision["decision"] == "BLOCKED"
    assert "PLAN_MISMATCH" in decision["reason_codes"]
    assert "RUN_ID_MISMATCH" in decision["reason_codes"]


def test_fixture_ledger_is_sealed_nonserializable_and_not_authority() -> None:
    plan = make_plan()
    with pytest.raises(TypeError, match="created by"):
        Task083FixtureReservationLedger(object(), plan, "forged")
    with pytest.raises(TypeError, match="cannot be subclassed"):
        type("ForgedLedger", (Task083FixtureReservationLedger,), {})
    ledger = open_fixture_reservation(plan, reservation_id="reservation-sealed")
    with pytest.raises(TypeError, match="not serializable"):
        pickle.dumps(ledger)


def test_fixture_receipt_cannot_be_relabelled_as_production() -> None:
    plan = make_plan()
    receipt = reserve(
        open_fixture_reservation(plan, reservation_id="reservation-discriminator"), plan
    ).to_dict()
    forged = copy.deepcopy(receipt)
    forged["record_type"] = "Task083ExecutionResourceReservationReceiptV1"
    rehash(forged, "receipt_sha256", RECEIPT_DOMAIN)
    with pytest.raises(ValueError, match="production lineage|SHA-256"):
        Task083ExecutionResourceReservationReceiptV1.from_dict(forged)


def test_parse_only_production_receipt_and_readback_require_full_lineage() -> None:
    plan = make_plan()
    fixture_receipt = reserve(
        open_fixture_reservation(plan, reservation_id="reservation-production-parse"), plan
    ).to_dict()
    production = {
        **fixture_receipt,
        "record_type": "Task083ExecutionResourceReservationReceiptV1",
        "h3_authorization_v2_sha256": H("h3-v2"),
        "task084_destination_plan_sha256": H("task084-plan"),
        "compound_operation_id": "compound-operation-083",
        "compound_operation_sha256": H("compound-operation"),
        "compound_stage": "RESERVATION_ACTIVATED",
        "fixture_only": False,
        "live_capability_present": True,
        "production_backend_invoked": True,
        "native_reservation_invoked": True,
        "resource_effect_count": 1,
    }
    rehash(production, "receipt_sha256", RECEIPT_DOMAIN)
    parsed = Task083ExecutionResourceReservationReceiptV1.from_dict(production).to_dict()
    assert parsed["state"] == "RESERVED"
    assert parsed["authority_created"] is False
    assert parsed["live_capability_restorable"] is False

    for field, value in (
        ("reservation_revision", 2),
        ("live_capability_present", False),
        ("native_reservation_invoked", False),
        ("training_dispatched", True),
        ("training_started", True),
    ):
        invalid = copy.deepcopy(production)
        invalid[field] = value
        rehash(invalid, "receipt_sha256", RECEIPT_DOMAIN)
        with pytest.raises(ValueError, match="state/revision|state mismatch|flags/state|native"):
            Task083ExecutionResourceReservationReceiptV1.from_dict(invalid)

    for field in (
        "h3_authorization_v2_sha256",
        "task084_destination_plan_sha256",
        "compound_operation_id",
        "compound_operation_sha256",
    ):
        missing = copy.deepcopy(production)
        missing[field] = None
        rehash(missing, "receipt_sha256", RECEIPT_DOMAIN)
        with pytest.raises(ValueError):
            Task083ExecutionResourceReservationReceiptV1.from_dict(missing)

    unknown = {
        **production,
        "state": "CONSUMPTION_UNKNOWN",
        "reservation_revision": 3,
        "previous_receipt_sha256": H("consumption-started-receipt"),
        "compound_stage": "TRAINING_DISPATCH_UNKNOWN",
        "live_capability_present": False,
        "training_dispatched": None,
        "training_started": None,
    }
    rehash(unknown, "receipt_sha256", RECEIPT_DOMAIN)
    assert Task083ExecutionResourceReservationReceiptV1.from_dict(unknown).to_dict()[
        "training_started"
    ] is None

    unproven_failed = {
        **unknown,
        "state": "FAILED_CLOSED",
        "compound_stage": "TRAINING_DISPATCH_NOT_STARTED",
        "training_dispatched": False,
        "training_started": False,
    }
    rehash(unproven_failed, "receipt_sha256", RECEIPT_DOMAIN)
    with pytest.raises(ValueError, match="durable_negative_acknowledgement"):
        Task083ExecutionResourceReservationReceiptV1.from_dict(unproven_failed)

    wrong_stage = copy.deepcopy(production)
    wrong_stage["compound_stage"] = "TRAINING_DISPATCH_ACKNOWLEDGED"
    rehash(wrong_stage, "receipt_sha256", RECEIPT_DOMAIN)
    with pytest.raises(ValueError, match="state/compound_stage"):
        Task083ExecutionResourceReservationReceiptV1.from_dict(wrong_stage)

    ledger = open_fixture_reservation(plan, reservation_id="reservation-readback-parse")
    fixture_readback = ledger.readback(read_back_at="2026-09-06T01:05:00Z").to_dict()
    production_readback = {
        **fixture_readback,
        "record_type": "Task083ResourceReservationReadbackV1",
        "h3_authorization_v2_sha256": H("h3-v2"),
        "task084_destination_plan_sha256": H("task084-plan"),
        "compound_operation_id": "compound-operation-083",
        "compound_operation_sha256": H("compound-operation"),
        "compound_stage": "RESERVATION_ACTIVATED",
        "state": "RESERVED",
        "reservation_revision": 1,
        "event_count": 1,
        "head_receipt_sha256": production["receipt_sha256"],
        "fixture_only": False,
        "live_capability_present": True,
        "production_backend_invoked": True,
        "native_reservation_invoked": True,
        "resource_effect_count": 1,
    }
    # native_reservation_invoked is receipt-only and therefore unknown here.
    production_readback.pop("native_reservation_invoked")
    rehash(production_readback, "readback_sha256", READBACK_DOMAIN)
    parsed_readback = Task083ResourceReservationReadbackV1.from_dict(
        production_readback
    ).to_dict()
    assert (
        parsed_readback["state"]
        == "RESERVED"
    )
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(
        json.loads(PUBLIC_SCHEMA.read_text(encoding="utf-8")),
        format_checker=jsonschema.FormatChecker(),
    )
    assert not list(validator.iter_errors(production))
    assert not list(validator.iter_errors(unknown))
    assert list(validator.iter_errors(unproven_failed))
    assert not list(validator.iter_errors(production_readback))
    schema_invalid = copy.deepcopy(production)
    schema_invalid["training_started"] = True
    assert list(validator.iter_errors(schema_invalid))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", 2),
        ("canonical_owner_task", "TASK-084"),
        ("receipt_role", "TRAINING_START"),
    ],
)
def test_fixture_receipt_rejects_wrong_version_owner_and_role(field: str, value: object) -> None:
    plan = make_plan()
    receipt = reserve(
        open_fixture_reservation(plan, reservation_id="reservation-wrong-discriminator"), plan
    ).to_dict()
    receipt[field] = value
    rehash(receipt, "receipt_sha256", RECEIPT_DOMAIN)
    with pytest.raises(ValueError, match="discriminator"):
        Task083FixtureExecutionResourceReservationReceiptV1.from_dict(receipt)


def test_legacy_projection_is_closed_unknown_and_cannot_be_flipped() -> None:
    plan = make_plan()
    receipt = reserve(
        open_fixture_reservation(plan, reservation_id="reservation-projection"), plan
    )
    projected = project_legacy_execution_resource_reservation_binding(
        receipt, receipt_ref="task083-receipt:reservation-projection:1"
    )
    assert set(projected) == {
        "record_type",
        "contract_state",
        "reservation_id",
        "receipt_ref",
        "receipt_sha256",
        "gpu_ref",
        "cpu_units",
        "ram_bytes",
        "vram_bytes",
        "disk_bytes",
        "thermal_state",
        "power_state",
        "admission_state",
        "issued_at",
        "expires_at",
        "binding_sha256",
    }
    assert projected["contract_state"] == "UNKNOWN"
    assert projected["admission_state"] == "UNKNOWN"
    assert projected["reservation_id"] is None

    forged = copy.deepcopy(projected)
    forged["contract_state"] = "BOUND_VERIFIED"
    forged["binding_sha256"] = sha256_bytes(
        canonical_json_bytes({k: v for k, v in forged.items() if k != "binding_sha256"})
    )
    with pytest.raises(ValueError, match="incomplete"):
        ExecutionResourceReservationBinding.from_dict(forged)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda raw: b"\xef\xbb\xbf" + raw,
        lambda raw: raw + b" trailing",
        lambda raw: raw.replace(b'"schema_version":1', b'"schema_version":1,"schema_version":1'),
        lambda raw: raw.replace(b'"resource_effect_count":0', b'"resource_effect_count":NaN'),
        lambda raw: b"{" + b'"x":' * 18 + b"0" + b"}" * 18,
        lambda raw: b" " + raw,
    ],
)
def test_strict_security_json_rejects_ambiguous_inputs(mutation) -> None:
    raw = make_plan().canonical_bytes()
    with pytest.raises(ValueError):
        parse_security_json(mutation(raw), expected_type="Task083ResourceReservationPlanV1")


def test_strict_json_rejects_oversize_unknown_and_digest_mismatch() -> None:
    with pytest.raises(ValueError, match="oversized"):
        parse_security_json(b"{" + b" " * 65_536 + b"}")
    plan = make_plan().to_dict()
    plan["secret"] = "must-not-survive"
    with pytest.raises(ValueError, match="unknown"):
        Task083ResourceReservationPlanV1.from_dict(plan)
    plan = make_plan().to_dict()
    plan["run_id"] = "run-tampered"
    with pytest.raises(ValueError, match="plan_sha256 mismatch"):
        Task083ResourceReservationPlanV1.from_dict(plan)


def test_schema_is_valid_mirrored_closed_and_accepts_public_records() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    Draft202012Validator = jsonschema.Draft202012Validator
    assert PUBLIC_SCHEMA.read_bytes() == PACKAGED_SCHEMA.read_bytes()
    schema = json.loads(PUBLIC_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    plan = make_plan()
    observation = make_observation(plan)
    decision = evaluate_fixture_reservation(
        plan, observation, evaluated_at="2026-09-06T01:15:00Z"
    )
    ledger = open_fixture_reservation(plan, reservation_id="reservation-schema")
    receipt = reserve(ledger, plan)
    readback = ledger.readback(read_back_at="2026-09-06T01:16:00Z")
    production_admission = compile_production_reservation_admission(
        plan, evaluated_at="2026-09-06T01:05:00Z"
    )
    burned_for_ack = ledger.begin_fixture_consumption(
        request_id="schema-burn",
        expected_revision=receipt.to_dict()["reservation_revision"],
        expected_receipt_sha256=receipt.to_dict()["receipt_sha256"],
        observation=make_observation(
            plan,
            observed_at="2026-09-06T01:16:00Z",
            fresh_until="2026-09-06T01:25:00Z",
        ),
        observed_at="2026-09-06T01:17:00Z",
    ).to_dict()
    negative_ack = ledger.issue_fixture_durable_negative_acknowledgement(
        acknowledgement_id="schema-negative-ack",
        expected_revision=burned_for_ack["reservation_revision"],
        expected_receipt_sha256=burned_for_ack["receipt_sha256"],
        observed_at="2026-09-06T01:17:30Z",
    )
    for record in (
        plan,
        observation,
        decision,
        receipt,
        readback,
        production_admission,
        negative_ack,
    ):
        assert not list(validator.iter_errors(record.to_dict()))
        changed = record.to_dict()
        changed["unknown"] = True
        assert list(validator.iter_errors(changed))


@pytest.mark.parametrize(
    "value",
    [
        "20260906T010000Z",
        "2026-09-06T01:00Z",
        "2026-09-06 01:00:00Z",
        "2026-09-06T01:00:00,5Z",
        "2026-09-06T01:00:00+00:00",
        "2026-13-01T00:00:00Z",
        "2026-02-30T00:00:00Z",
        "2026-02-29T00:00:00Z",
        "1900-02-29T00:00:00Z",
        "0000-01-01T00:00:00Z",
        "2026-01-01T24:00:00Z",
        "2026-09-06T01:00:00Z\n",
    ],
)
def test_runtime_schema_timestamp_lexical_contract_matches(value: str) -> None:
    with pytest.raises(ValueError, match="RFC3339 UTC"):
        make_plan(issued_at=value)
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(
        json.loads(PUBLIC_SCHEMA.read_text(encoding="utf-8")),
        format_checker=jsonschema.FormatChecker(),
    )
    changed = make_plan().to_dict()
    changed["issued_at"] = value
    assert list(validator.iter_errors(changed))


@pytest.mark.parametrize(
    ("issued_at", "expires_at"),
    [
        ("2024-02-29T00:00:00Z", "2024-02-29T00:00:01Z"),
        ("2000-02-29T23:59:58.123456Z", "2000-02-29T23:59:59.123456Z"),
        ("9999-12-31T23:59:58Z", "9999-12-31T23:59:59Z"),
    ],
)
def test_runtime_schema_timestamp_semantic_valid_contract_matches(
    issued_at: str, expires_at: str
) -> None:
    plan = make_plan(issued_at=issued_at, expires_at=expires_at)
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(
        json.loads(PUBLIC_SCHEMA.read_text(encoding="utf-8")),
        format_checker=jsonschema.FormatChecker(),
    )
    assert not list(validator.iter_errors(plan.to_dict()))


@pytest.mark.parametrize(
    "value",
    [
        "http://private",
        "https://private",
        "file:private",
        "C:/private",
        "C:private",
        "/private",
        "x/../private",
        "logical-id\n",
    ],
)
def test_runtime_schema_body_free_identifier_contract_matches(value: str) -> None:
    with pytest.raises(ValueError, match="body-free|host/private|invalid"):
        make_plan(run_id=value)
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(
        json.loads(PUBLIC_SCHEMA.read_text(encoding="utf-8")),
        format_checker=jsonschema.FormatChecker(),
    )
    changed = make_plan().to_dict()
    changed["run_id"] = value
    assert list(validator.iter_errors(changed))


def test_no_private_or_effectful_terms_are_exported() -> None:
    plan = make_plan()
    ledger = open_fixture_reservation(plan, reservation_id="reservation-public")
    exported = canonical_json_bytes(
        {
            "plan": plan.to_dict(),
            "receipt": reserve(ledger, plan).to_dict(),
            "readback": ledger.readback(read_back_at="2026-09-06T01:16:00Z").to_dict(),
        }
    ).decode("utf-8")
    for forbidden in ("C:\\\\", "/home/", "private_key", "secret", "raw_audio", "process_token"):
        assert forbidden not in exported
    assert '"resource_effect_count":0' in exported
    assert '"training_started":false' in exported
