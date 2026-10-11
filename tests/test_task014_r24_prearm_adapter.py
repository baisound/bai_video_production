from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from copy import copy, deepcopy
from pathlib import Path
import pickle

import pytest

from ai_video_production import task014_r24_prearm_adapter as prearm
from ai_video_production.task014_r24_prearm_adapter import (
    AMENDMENT_IDENTITY,
    FIXTURE_SCOPE,
    Task014R24CoordinatorState as Coordinator,
    Task014R24FakePrearmPort,
    Task014R24OwnerQuery as Query,
    Task014R24PrearmAdapter,
    Task014R24PrearmCurrentRead,
    Task014R24PrearmCurrentState as Current,
    Task014R24PrearmOwner as Owner,
    Task014R24PrearmOwnerReceipt,
    Task014R24PrearmOwnerReceiptSet,
    Task014R24PrearmScenario as Scenario,
    Task014R24ReservationState as Reservation,
    issue_effect_zero_owner_receipts,
    read_current,
)


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "src" / "ai_video_production" / "task014_r24_prearm_adapter.py"
PROJECT = "project.synthetic"
OPERATION = "operation.synthetic.1"
TICKET = "ticket.synthetic.1"
RESERVATION_ID = "reservation.synthetic.1"
CLAIM_ID = "claim.synthetic.1"


def adapter(*, port: Task014R24FakePrearmPort | None = None):
    fixture_port = port or Task014R24FakePrearmPort()
    value = Task014R24PrearmAdapter.create_synthetic(
        port=fixture_port,
        owner_receipts=issue_effect_zero_owner_receipts(),
        project_id=PROJECT,
        operation_id=OPERATION,
        ticket_id=TICKET,
        reservation_id=RESERVATION_ID,
        claim_id=CLAIM_ID,
    )
    return fixture_port, value


def execute(scenario: Scenario):
    port, value = adapter()
    result = value.execute(
        scenario=scenario,
        project_id=PROJECT,
        operation_id=OPERATION,
        ticket_id=TICKET,
    )
    return port, value, result


def current(port: Task014R24FakePrearmPort, **changes):
    arguments = {
        "project_id": PROJECT,
        "operation_id": OPERATION,
        "ticket_id": TICKET,
        "expected_reservation_id": RESERVATION_ID,
        "expected_claim_id": CLAIM_ID,
        "expected_snapshot_sha256": None,
    }
    arguments.update(changes)
    return read_current(port, **arguments)


def test_closed_vocabularies_and_amendment_identity_are_exact() -> None:
    assert AMENDMENT_IDENTITY == (
        "TASK014_TASK072_TASK075_TASK076_"
        "COORDINATED_PREARM_RESERVATION_AMENDMENT_V1"
    )
    assert FIXTURE_SCOPE == "TASK014_R24_S3_SYNTHETIC_EFFECT_ZERO"
    assert tuple(item.value for item in Owner) == (
        "TASK-014",
        "TASK-072",
        "TASK-075",
        "TASK-076",
    )
    assert tuple(item.value for item in Reservation) == (
        "RESERVED",
        "CANCEL_PENDING",
        "CANCELLED_KNOWN",
        "CANCEL_UNKNOWN",
        "ARMING",
        "JOIN_PENDING",
        "ARMED_CONSUMED",
        "ARM_REJECTED",
        "ARM_UNKNOWN",
    )
    assert tuple(item.value for item in Coordinator) == (
        "CLAIM_INTENT",
        "TASK014_CLAIMED",
        "ARM_CALL_ENTERING",
        "TASK076_RESULT_OBSERVED",
        "JOINED",
    )
    assert tuple(item.value for item in Query) == (
        "NOT_ENTERED_KNOWN",
        "JOB_CHILD_ARMED_READBACK_V3",
        "JOB_CHILD_REJECTED_READBACK_V3",
        "JOB_CHILD_BURNED_UNKNOWN_READBACK_V3",
        "ATTEMPT_TRUTH_UNKNOWN",
    )


def test_exact_four_owner_receipts_are_sealed_and_effect_zero() -> None:
    receipts = issue_effect_zero_owner_receipts()
    assert receipts.amendment_identity == AMENDMENT_IDENTITY
    assert receipts.owners == tuple(Owner)
    digests = []
    for owner in Owner:
        receipt = receipts.receipt_for(owner)
        assert receipt.owner is owner
        assert len(receipt.record_sha256) == 64
        assert receipt.record_sha256 == receipt.record_sha256.upper()
        assert receipt.fixture_only is True
        assert receipt.source_authority is False
        assert receipt.effect_authority is False
        digests.append(receipt.record_sha256)
    assert len(set(digests)) == 4
    assert prearm.TASK014_OWNER_ACCEPTANCE_RECORD_SHA256 == (
        "A398A9FE13F886DC6A4783B2AB3EEAB61721598F20F27ABAC2C0EB2811CBB06B"
    )
    assert prearm.TASK074_OWNER_ACCEPTANCE_RECORD_SHA256 == (
        "8EDDD5E86CD21A779ADBCF889A9478E67520F4E0E48748983D7ABE6F2D710BB0"
    )
    assert prearm.TASK041_OWNER_ACCEPTANCE_RECORD_SHA256 == (
        "AFDDFDF428BB0A98272F20E68CFBE906266218C40D2BFA1955F7ED23480A6853"
    )
    assert prearm.TASK036_OWNER_ACCEPTANCE_RECORD_SHA256 == (
        "78A998DDD65209EBF108755599A1AD755843F022B692277CADD18DD099BE5BAB"
    )


@pytest.mark.parametrize(
    ("scenario", "reservation_trace", "coordinator_trace", "initial", "joined"),
    (
        (
            Scenario.CANCEL_KNOWN,
            (Reservation.RESERVED, Reservation.CANCEL_PENDING, Reservation.CANCELLED_KNOWN),
            (),
            Query.NOT_ENTERED_KNOWN,
            Query.JOB_CHILD_REJECTED_READBACK_V3,
        ),
        (
            Scenario.CANCEL_UNKNOWN,
            (Reservation.RESERVED, Reservation.CANCEL_PENDING, Reservation.CANCEL_UNKNOWN),
            (),
            Query.ATTEMPT_TRUTH_UNKNOWN,
            Query.JOB_CHILD_BURNED_UNKNOWN_READBACK_V3,
        ),
        (
            Scenario.FAILURE_BEFORE_TASK014_CLAIM,
            (Reservation.RESERVED,),
            (Coordinator.CLAIM_INTENT,),
            Query.NOT_ENTERED_KNOWN,
            None,
        ),
        (
            Scenario.ARM_NOT_ENTERED,
            (
                Reservation.RESERVED,
                Reservation.ARMING,
                Reservation.JOIN_PENDING,
                Reservation.ARM_REJECTED,
            ),
            (
                Coordinator.CLAIM_INTENT,
                Coordinator.TASK014_CLAIMED,
                Coordinator.TASK076_RESULT_OBSERVED,
                Coordinator.JOINED,
            ),
            Query.NOT_ENTERED_KNOWN,
            Query.JOB_CHILD_REJECTED_READBACK_V3,
        ),
        (
            Scenario.ARM_ARMED,
            (
                Reservation.RESERVED,
                Reservation.ARMING,
                Reservation.JOIN_PENDING,
                Reservation.ARMED_CONSUMED,
            ),
            tuple(Coordinator),
            Query.JOB_CHILD_ARMED_READBACK_V3,
            Query.JOB_CHILD_ARMED_READBACK_V3,
        ),
        (
            Scenario.ARM_REJECTED,
            (
                Reservation.RESERVED,
                Reservation.ARMING,
                Reservation.JOIN_PENDING,
                Reservation.ARM_REJECTED,
            ),
            tuple(Coordinator),
            Query.JOB_CHILD_REJECTED_READBACK_V3,
            Query.JOB_CHILD_REJECTED_READBACK_V3,
        ),
        (
            Scenario.ARM_UNKNOWN,
            (
                Reservation.RESERVED,
                Reservation.ARMING,
                Reservation.JOIN_PENDING,
                Reservation.ARM_UNKNOWN,
            ),
            tuple(Coordinator),
            Query.JOB_CHILD_BURNED_UNKNOWN_READBACK_V3,
            Query.JOB_CHILD_BURNED_UNKNOWN_READBACK_V3,
        ),
        (
            Scenario.ATTEMPT_TRUTH_UNKNOWN,
            (
                Reservation.RESERVED,
                Reservation.ARMING,
                Reservation.JOIN_PENDING,
                Reservation.ARM_UNKNOWN,
            ),
            tuple(Coordinator),
            Query.ATTEMPT_TRUTH_UNKNOWN,
            Query.JOB_CHILD_BURNED_UNKNOWN_READBACK_V3,
        ),
    ),
)
def test_scenarios_have_exact_monotonic_traces_and_join(
    scenario, reservation_trace, coordinator_trace, initial, joined
) -> None:
    port, _, result = execute(scenario)
    assert result.state is Current.CURRENT_EFFECT_ZERO
    assert result.reservation_trace == reservation_trace
    assert result.coordinator_trace == coordinator_trace
    assert result.reservation_state is reservation_trace[-1]
    assert result.coordinator_state is (
        coordinator_trace[-1] if coordinator_trace else None
    )
    assert result.initial_query is initial
    assert result.join_query is joined
    assert result.store_revision == len(reservation_trace) + len(coordinator_trace)
    assert len(result.snapshot_sha256 or "") == 64
    assert current(
        port, expected_snapshot_sha256=result.snapshot_sha256
    ).state is Current.CURRENT_EFFECT_ZERO


def test_wrong_coordinate_burns_adapter_before_owner_store_mutation() -> None:
    port, value = adapter()
    with pytest.raises(ValueError, match="foreign coordinate"):
        value.execute(
            scenario=Scenario.ARM_ARMED,
            project_id="project.foreign",
            operation_id=OPERATION,
            ticket_id=TICKET,
        )
    reserved = current(
        port, expected_snapshot_sha256=value.reserved_snapshot_sha256
    )
    assert reserved.state is Current.CURRENT_EFFECT_ZERO
    assert reserved.reservation_trace == (Reservation.RESERVED,)
    assert reserved.coordinator_trace == ()
    assert reserved.initial_query is None
    assert reserved.join_query is None
    with pytest.raises(RuntimeError, match="already been burned"):
        value.execute(
            scenario=Scenario.ARM_ARMED,
            project_id=PROJECT,
            operation_id=OPERATION,
            ticket_id=TICKET,
        )


def test_one_use_concurrency_has_exactly_one_winner_and_no_second_arm() -> None:
    port, value = adapter()

    def invoke():
        try:
            return value.execute(
                scenario=Scenario.ARM_ARMED,
                project_id=PROJECT,
                operation_id=OPERATION,
                ticket_id=TICKET,
            )
        except RuntimeError:
            return None

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: invoke(), range(64)))
    winners = [item for item in results if item is not None]
    assert len(winners) == 1
    assert winners[0].reservation_state is Reservation.ARMED_CONSUMED
    assert current(port).reservation_state is Reservation.ARMED_CONSUMED


def test_second_adapter_cannot_rewrite_existing_reservation() -> None:
    port, first = adapter()
    first.execute(
        scenario=Scenario.ARM_REJECTED,
        project_id=PROJECT,
        operation_id=OPERATION,
        ticket_id=TICKET,
    )
    with pytest.raises(ValueError, match="already contains"):
        adapter(port=port)
    assert current(port).reservation_state is Reservation.ARM_REJECTED


def test_current_read_classifies_missing_foreign_stale_forked_ambiguous_broken() -> None:
    assert current(Task014R24FakePrearmPort()).state is Current.STORE_MISSING
    port, _, result = execute(Scenario.ARM_ARMED)
    assert current(port, project_id="project.foreign").state is Current.FOREIGN_PROJECT
    stale = current(
        port,
        operation_id="operation.changed",
        ticket_id="ticket.changed",
        expected_reservation_id="reservation.changed",
        expected_claim_id="claim.changed",
        expected_snapshot_sha256="A" * 64,
    )
    assert stale.state is Current.STALE_COORDINATE
    assert stale.reason_codes == (
        "CLAIM_CHANGED",
        "OPERATION_CHANGED",
        "RESERVATION_CHANGED",
        "SNAPSHOT_CHANGED",
        "TICKET_CHANGED",
    )
    assert result.currentness_verified is True
    cases = (
        (
            Task014R24FakePrearmPort.create_forked_fixture(),
            Current.FORKED_CHAIN,
            "MULTIPLE_RESERVATION_HEADS",
        ),
        (
            Task014R24FakePrearmPort.create_ambiguous_fixture(),
            Current.AMBIGUOUS_TRUTH,
            "OWNER_QUERY_TRUTH_AMBIGUOUS",
        ),
        (
            Task014R24FakePrearmPort.create_broken_fixture(),
            Current.BROKEN_CHAIN,
            "UNTRUSTED_FIXTURE_SNAPSHOT",
        ),
    )
    for fixture, state, reason in cases:
        observed = current(fixture)
        assert observed.state is state
        assert observed.reason_codes == (reason,)
        assert observed.currentness_verified is False


def test_current_read_rejects_invalid_expected_digest() -> None:
    with pytest.raises(ValueError, match="expected_snapshot_sha256"):
        current(Task014R24FakePrearmPort(), expected_snapshot_sha256="a" * 64)


def test_existing_snapshot_requires_exact_reservation_claim_and_head_expectations() -> None:
    port, _, result = execute(Scenario.ARM_ARMED)
    omitted = read_current(
        port,
        project_id=PROJECT,
        operation_id=OPERATION,
        ticket_id=TICKET,
        expected_reservation_id=None,
        expected_claim_id=None,
        expected_snapshot_sha256=None,
    )
    assert omitted.state is Current.STALE_COORDINATE
    assert omitted.reason_codes == (
        "CLAIM_EXPECTATION_MISSING",
        "RESERVATION_EXPECTATION_MISSING",
        "SNAPSHOT_EXPECTATION_MISSING",
    )
    with pytest.raises(TypeError, match="required keyword-only"):
        read_current(
            port,
            project_id=PROJECT,
            operation_id=OPERATION,
            ticket_id=TICKET,
        )
    assert current(
        port, expected_snapshot_sha256=result.snapshot_sha256
    ).state is Current.CURRENT_EFFECT_ZERO


def test_every_positive_read_is_fixture_only_and_has_zero_effect_authority() -> None:
    _, _, result = execute(Scenario.ARM_ARMED)
    assert result.fixture_only is True
    assert result.owner_store_read is True
    for name in prearm._FALSE_EFFECT_NAMES:
        assert getattr(result, name) is False
    for forbidden in (
        "canonical_arm",
        "private_body",
        "publication_current",
        "downstream_pass",
    ):
        with pytest.raises(AttributeError):
            getattr(result, forbidden)


@pytest.mark.parametrize(
    "capability_type",
    (
        Task014R24PrearmOwnerReceipt,
        Task014R24PrearmOwnerReceiptSet,
        Task014R24PrearmAdapter,
        Task014R24PrearmCurrentRead,
    ),
)
def test_capabilities_reject_direct_construction_and_unissued_object_new(
    capability_type,
) -> None:
    with pytest.raises(TypeError, match="owner-issued only"):
        capability_type()
    forged = object.__new__(capability_type)
    with pytest.raises(TypeError, match="provenance"):
        if capability_type is Task014R24PrearmOwnerReceipt:
            _ = forged.owner
        elif capability_type is Task014R24PrearmOwnerReceiptSet:
            _ = forged.owners
        elif capability_type is Task014R24PrearmCurrentRead:
            _ = forged.state
        else:
            forged.execute(
                scenario=Scenario.ARM_ARMED,
                project_id=PROJECT,
                operation_id=OPERATION,
                ticket_id=TICKET,
            )


def test_capabilities_ports_and_reads_are_immutable_noncopyable_nonserializable() -> None:
    port, value, result = execute(Scenario.ARM_REJECTED)
    objects = (
        issue_effect_zero_owner_receipts(),
        issue_effect_zero_owner_receipts().receipt_for(Owner.TASK014),
        value,
        result,
        port,
    )
    for item in objects:
        with pytest.raises(AttributeError):
            item.injected = True
        with pytest.raises((TypeError, AttributeError)):
            copy(item)
        with pytest.raises((TypeError, AttributeError)):
            deepcopy(item)
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(item)
        assert not hasattr(item, "__dict__")


def test_types_are_sealed_against_subclassing() -> None:
    for base in (
        Task014R24PrearmOwnerReceipt,
        Task014R24PrearmOwnerReceiptSet,
        Task014R24PrearmAdapter,
        Task014R24PrearmCurrentRead,
        Task014R24FakePrearmPort,
    ):
        with pytest.raises(TypeError, match="sealed"):
            type("Forged", (base,), {})


def test_raw_registration_and_execution_helpers_are_not_module_attributes() -> None:
    for name in (
        "_receipt_value",
        "_receipt_set_items",
        "_register_port",
        "_register_adapter",
        "_adapter_value",
        "_run_adapter",
        "_read_value",
    ):
        assert not hasattr(prearm, name)


def test_source_has_no_filesystem_network_process_provider_or_serialization_edge() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported.isdisjoint(
        {
            "asyncio",
            "httpx",
            "json",
            "openai",
            "os",
            "pathlib",
            "pickle",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        }
    )
    assert "open(" not in source
    assert "to_dict" not in source
    assert "from_dict" not in source
