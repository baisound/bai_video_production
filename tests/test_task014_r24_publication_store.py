from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from copy import copy, deepcopy
from importlib import resources
import json
from pathlib import Path
import pickle

import pytest
from jsonschema import Draft202012Validator

from ai_video_production import owner_voice_authority as task074
from ai_video_production import task014_r24_publication_store as store_module
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task014_r24_publication_store import (
    FIXTURE_SCOPE,
    POST_HISTORY_TYPE,
    POST_RECORD_TYPE,
    R24_S1_COMPLETION_RECEIPT_SHA256,
    R24_S1_SOURCE_SHA256,
    TASK014_OWNER_ACCEPTANCE_RECORD_SHA256,
    TASK074_OWNER_ACCEPTANCE_RECORD_SHA256,
    Task014R24CurrentState,
    Task014R24FakePublicationPort,
    Task014R24PostCandidate,
    Task014R24RestrictedConsumer,
    read_current,
)


ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas" / "task014-r24-publication-history.schema.json"
PROJECT = "project.synthetic"
OPERATION = "operation.synthetic.1"
TICKET = "ticket.synthetic.1"
CANDIDATE = "candidate.synthetic.1"


def digest(label: str) -> str:
    return sha256_bytes(label.encode("ascii"))


def s1_decision(
    *,
    project_id: str = PROJECT,
    operation_id: str = OPERATION,
    ticket_id: str = TICKET,
    predecessor: task074.R24PredecessorKind = task074.R24PredecessorKind.UNKNOWN,
    post: task074.R24TruthValue = task074.R24TruthValue.UNKNOWN,
    job: task074.R24TruthValue = task074.R24TruthValue.UNKNOWN,
    retirement: task074.R24TruthValue = task074.R24TruthValue.UNKNOWN,
):
    producer = task074.Task074R24EffectZeroProducer(
        owner_acceptance_record_sha256=TASK074_OWNER_ACCEPTANCE_RECORD_SHA256
    )
    return producer.produce(
        project_id=project_id,
        operation_id=operation_id,
        ticket_id=ticket_id,
        predecessor_kind=predecessor,
        post=post,
        job_terminal=job,
        retirement=retirement,
        prepare_continuity_context=(
            task074.R24PrepareContinuityContext.NO_PREPARE_RECOVERY_EVENT
        ),
    )


def consumer() -> Task014R24RestrictedConsumer:
    return Task014R24RestrictedConsumer(
        task014_owner_acceptance_record_sha256=TASK014_OWNER_ACCEPTANCE_RECORD_SHA256,
        task074_owner_acceptance_record_sha256=TASK074_OWNER_ACCEPTANCE_RECORD_SHA256,
        r24_s1_completion_receipt_sha256=R24_S1_COMPLETION_RECEIPT_SHA256,
        r24_s1_source_sha256=R24_S1_SOURCE_SHA256,
    )


def current_read(port: Task014R24FakePublicationPort, **changes):
    decision = s1_decision()
    arguments = {
        "project_id": PROJECT,
        "operation_id": OPERATION,
        "expected_ticket_id": TICKET,
        "candidate_id": CANDIDATE,
        "expected_call_sha256": digest("call"),
        "expected_sink_sha256": digest("sink"),
        "expected_result_sha256": digest("result"),
        "expected_publication_readback_sha256": digest("publication"),
        "expected_task074_s1_coordinate_sha256": decision.coordinate_sha256,
        "expected_task074_s1_decision_sha256": decision.decision_sha256,
    }
    arguments.update(changes)
    return read_current(port, **arguments)


def candidate(
    decision,
    *,
    project_id: str = PROJECT,
    operation_id: str = OPERATION,
    ticket_id: str = TICKET,
    candidate_id: str = CANDIDATE,
    revision: int = 1,
    parent: str | None = None,
    call: str | None = None,
    sink: str | None = None,
    result: str | None = None,
    publication: str | None = None,
) -> Task014R24PostCandidate:
    return Task014R24PostCandidate.create_synthetic(
        project_id=project_id,
        operation_id=operation_id,
        ticket_id=ticket_id,
        candidate_id=candidate_id,
        revision=revision,
        parent_record_sha256=parent,
        call_sha256=call or digest("call"),
        sink_sha256=sink or digest("sink"),
        result_sha256=result or digest("result"),
        publication_readback_sha256=publication or digest("publication"),
        task074_s1_coordinate_sha256=decision.coordinate_sha256,
        task074_s1_decision_sha256=decision.decision_sha256,
    )


def append_first(
    *, port: Task014R24FakePublicationPort | None = None,
):
    port = port or Task014R24FakePublicationPort()
    decision = s1_decision()
    record = candidate(decision)
    current = consumer().append_candidate(
        port=port,
        s1_decision=decision,
        candidate=record,
        project_id=PROJECT,
        operation_id=OPERATION,
        ticket_id=TICKET,
        expected_previous_snapshot_sha256=None,
    )
    return port, decision, record, current


def rehash_snapshot(value: dict) -> None:
    value["snapshot_sha256"] = store_module._hash_without(
        store_module._HISTORY_DOMAIN, value, "snapshot_sha256"
    )


def test_r24_s2_schema_is_valid_packaged_exact_and_has_no_positive_publication_state() -> None:
    packaged = resources.files("ai_video_production").joinpath(
        "schema_resources", SCHEMA.name
    )
    assert SCHEMA.read_bytes() == packaged.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    port, _, _, _ = append_first()
    snapshot = json.loads(port.fixture_snapshot_bytes())
    Draft202012Validator(schema).validate(snapshot)
    assert snapshot["record_type"] == POST_HISTORY_TYPE
    assert snapshot["entries"][0]["record_type"] == POST_RECORD_TYPE
    assert "PUBLISHED_READBACK_VERIFIED" not in SCHEMA.read_text(encoding="utf-8")
    assert "Task014NarrationPublicationCurrentReadV1" not in SCHEMA.read_text(
        encoding="utf-8"
    )


def test_r24_s2_append_and_current_read_are_body_free_effect_zero() -> None:
    port, _, record, current = append_first()
    assert current.state is Task014R24CurrentState.CURRENT_EFFECT_ZERO
    assert current.project_id == PROJECT
    assert current.operation_id == OPERATION
    assert current.ticket_id == TICKET
    assert current.candidate_id == CANDIDATE
    assert current.record_sha256 == record.record_sha256
    assert current.store_revision == 1
    assert current.owner_store_read is True
    assert current.owner_origin_authenticated is True
    assert current.currentness_verified is True
    assert current.fixture_only is True
    assert current.source_authority is False
    assert current.effect_authority is False
    assert current.canonical_publication_type_minted is False
    assert current.private_body_present is False
    assert current.model_entered is False
    assert current.provider_entered is False
    assert current.audio_entered is False
    assert current.wav_created is False
    assert current.asset_created is False
    assert current.publication_current is False
    snapshot = json.loads(port.fixture_snapshot_bytes())
    assert snapshot["fixture_scope"] == FIXTURE_SCOPE
    assert snapshot["fake_persistence_only"] is True
    assert all(
        snapshot[name] is False
        for name in (
            "body_embedded",
            "source_authority",
            "effect_authority",
            "filesystem_write_authority",
            "publication_authority",
        )
    )


def test_post_candidate_parser_rejects_unknown_tampered_or_authority_fields() -> None:
    decision = s1_decision()
    value = candidate(decision).to_dict()
    mutations = (
        lambda row: row.update({"unknown": True}),
        lambda row: row.update({"publication_state": "PUBLISHED_READBACK_VERIFIED"}),
        lambda row: row.update({"source_authority": True}),
        lambda row: row.update({"effect_authority": True}),
        lambda row: row.update({"publication_current": True}),
        lambda row: row.update({"private_body_present": True}),
        lambda row: row.update({"record_sha256": digest("forged")}),
    )
    for mutate in mutations:
        changed = deepcopy(value)
        mutate(changed)
        with pytest.raises(ValueError):
            Task014R24PostCandidate.from_dict(changed)


@pytest.mark.parametrize("invalid_version", [True, 1.0])
def test_post_candidate_parser_requires_exact_integer_version(invalid_version) -> None:
    value = candidate(s1_decision()).to_dict()
    value["version"] = invalid_version
    value["record_sha256"] = store_module._hash_without(
        store_module._POST_DOMAIN, value, "record_sha256"
    )
    with pytest.raises(ValueError, match="identity"):
        Task014R24PostCandidate.from_dict(value)


def test_exact_s1_coordinate_and_all_unknown_contained_tuple_are_required() -> None:
    right = s1_decision()
    record = candidate(right)
    with pytest.raises(ValueError, match="exact S1 coordinate"):
        consumer().append_candidate(
            port=Task014R24FakePublicationPort(),
            s1_decision=s1_decision(project_id="project.other"),
            candidate=record,
            project_id=PROJECT,
            operation_id=OPERATION,
            ticket_id=TICKET,
            expected_previous_snapshot_sha256=None,
        )
    known = s1_decision(
        predecessor=task074.R24PredecessorKind.SUCCESS,
        post=task074.R24TruthValue.TRUE,
        job=task074.R24TruthValue.TRUE,
        retirement=task074.R24TruthValue.TRUE,
    )
    with pytest.raises(ValueError, match="all-UNKNOWN contained"):
        consumer().append_candidate(
            port=Task014R24FakePublicationPort(),
            s1_decision=known,
            candidate=candidate(known),
            project_id=PROJECT,
            operation_id=OPERATION,
            ticket_id=TICKET,
            expected_previous_snapshot_sha256=None,
        )


def test_caller_mapping_unissued_or_copied_object_cannot_substitute_for_consumer() -> None:
    decision = s1_decision()
    record = candidate(decision)
    with pytest.raises(TypeError, match="candidate type"):
        consumer().append_candidate(
            port=Task014R24FakePublicationPort(),
            s1_decision=decision,
            candidate=record.to_dict(),  # type: ignore[arg-type]
            project_id=PROJECT,
            operation_id=OPERATION,
            ticket_id=TICKET,
            expected_previous_snapshot_sha256=None,
        )
    with pytest.raises(TypeError, match="must use"):
        Task014R24PostCandidate()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        copy(record)
    with pytest.raises(TypeError):
        deepcopy(record)
    unissued = object.__new__(Task014R24PostCandidate)
    with pytest.raises(TypeError, match="provenance"):
        _ = unissued.record_sha256


def test_owner_history_is_append_only_chained_and_latest_head_selected() -> None:
    port, _, first, first_read = append_first()
    decision = s1_decision()
    second = candidate(
        decision,
        revision=2,
        parent=first.record_sha256,
        result=digest("result-v2"),
    )
    second_read = consumer().append_candidate(
        port=port,
        s1_decision=decision,
        candidate=second,
        project_id=PROJECT,
        operation_id=OPERATION,
        ticket_id=TICKET,
        expected_previous_snapshot_sha256=first_read.snapshot_sha256,
    )
    assert second_read.state is Task014R24CurrentState.CURRENT_EFFECT_ZERO
    assert second_read.record_sha256 == second.record_sha256
    assert second_read.store_revision == 2
    stale = current_read(
        port,
        project_id=PROJECT,
        operation_id=OPERATION,
        candidate_id=CANDIDATE,
        expected_call_sha256=digest("call"),
        expected_sink_sha256=digest("sink"),
        expected_result_sha256=digest("result"),
        expected_publication_readback_sha256=digest("publication"),
        expected_record_sha256=first.record_sha256,
    )
    assert stale.state is Task014R24CurrentState.STALE_UPSTREAM
    assert stale.reason_codes == ("POST_HEAD_CHANGED", "RESULT_CHANGED")


def test_append_requires_exact_cas_parent_revision_and_rejects_replay() -> None:
    port, _, first, first_read = append_first()
    decision = s1_decision()
    for record, previous in (
        (candidate(decision), first_read.snapshot_sha256),
        (
            candidate(decision, revision=2, parent=digest("wrong-parent")),
            first_read.snapshot_sha256,
        ),
        (
            candidate(decision, revision=2, parent=first.record_sha256),
            digest("stale-snapshot"),
        ),
    ):
        with pytest.raises(ValueError):
            consumer().append_candidate(
                port=port,
                s1_decision=decision,
                candidate=record,
                project_id=PROJECT,
                operation_id=OPERATION,
                ticket_id=TICKET,
                expected_previous_snapshot_sha256=previous,
            )


def test_append_rejects_changed_stable_ticket_and_s1_coordinate() -> None:
    port, _, first, first_read = append_first()
    changed_ticket = "ticket.synthetic.2"
    decision = s1_decision(ticket_id=changed_ticket)
    record = candidate(
        decision,
        ticket_id=changed_ticket,
        revision=2,
        parent=first.record_sha256,
    )
    with pytest.raises(ValueError, match="stable owner coordinate"):
        consumer().append_candidate(
            port=port,
            s1_decision=decision,
            candidate=record,
            project_id=PROJECT,
            operation_id=OPERATION,
            ticket_id=changed_ticket,
            expected_previous_snapshot_sha256=first_read.snapshot_sha256,
        )


def test_current_read_distinguishes_store_record_and_stale_coordinates() -> None:
    missing_store = current_read(
        Task014R24FakePublicationPort(),
        project_id=PROJECT,
        operation_id=OPERATION,
        candidate_id=CANDIDATE,
        expected_call_sha256=digest("call"),
        expected_sink_sha256=digest("sink"),
        expected_result_sha256=digest("result"),
        expected_publication_readback_sha256=digest("publication"),
    )
    assert missing_store.state is Task014R24CurrentState.STORE_NOT_FOUND
    assert missing_store.reason_codes == ("OWNER_STORE_NOT_FOUND",)
    port, _, _, _ = append_first()
    missing_record = current_read(
        port,
        project_id=PROJECT,
        operation_id=OPERATION,
        candidate_id="candidate.missing",
        expected_call_sha256=digest("call"),
        expected_sink_sha256=digest("sink"),
        expected_result_sha256=digest("result"),
        expected_publication_readback_sha256=digest("publication"),
    )
    assert missing_record.state is Task014R24CurrentState.RECORD_NOT_FOUND
    assert missing_record.owner_origin_authenticated is True
    stale = current_read(
        port,
        project_id=PROJECT,
        operation_id=OPERATION,
        candidate_id=CANDIDATE,
        expected_call_sha256=digest("wrong-call"),
        expected_sink_sha256=digest("wrong-sink"),
        expected_result_sha256=digest("wrong-result"),
        expected_publication_readback_sha256=digest("wrong-publication"),
        expected_ticket_id="ticket.synthetic.2",
        expected_task074_s1_coordinate_sha256=digest("wrong-s1-coordinate"),
        expected_task074_s1_decision_sha256=digest("wrong-s1-decision"),
    )
    assert stale.state is Task014R24CurrentState.STALE_UPSTREAM
    assert stale.reason_codes == (
        "CALL_CHANGED",
        "PUBLICATION_READBACK_CHANGED",
        "RESULT_CHANGED",
        "S1_COORDINATE_CHANGED",
        "S1_DECISION_CHANGED",
        "SINK_CHANGED",
        "TICKET_CHANGED",
    )


@pytest.mark.parametrize(
    ("mutation", "project_id", "expected_state"),
    [
        (
            lambda value: value["entries"][0].update(
                {"record_sha256": digest("tampered-record")}
            ),
            PROJECT,
            Task014R24CurrentState.BROKEN_CHAIN,
        ),
        (
            lambda value: value.update({"effect_authority": True}),
            PROJECT,
            Task014R24CurrentState.UNSAFE_AUTHORITY,
        ),
        (
            lambda value: value["entries"][0].update({"effect_authority": True}),
            PROJECT,
            Task014R24CurrentState.UNSAFE_AUTHORITY,
        ),
        (
            lambda value: None,
            "project.foreign",
            Task014R24CurrentState.FOREIGN_PROJECT,
        ),
    ],
)
def test_current_read_distinguishes_broken_foreign_and_unsafe_store(
    mutation, project_id: str, expected_state: Task014R24CurrentState
) -> None:
    port, _, _, _ = append_first()
    snapshot = json.loads(port.fixture_snapshot_bytes())
    mutation(snapshot)
    rehash_snapshot(snapshot)
    tampered = Task014R24FakePublicationPort(
        fixture_snapshot_bytes=canonical_json_bytes(snapshot)
    )
    result = current_read(
        tampered,
        project_id=project_id,
        operation_id=OPERATION,
        candidate_id=CANDIDATE,
        expected_call_sha256=digest("call"),
        expected_sink_sha256=digest("sink"),
        expected_result_sha256=digest("result"),
        expected_publication_readback_sha256=digest("publication"),
    )
    assert result.state is expected_state
    assert result.currentness_verified is False
    assert result.owner_origin_authenticated is False


@pytest.mark.parametrize("unsafe_value", [True, 1, "yes", None])
def test_entry_authority_non_false_values_are_distinctly_unsafe(unsafe_value) -> None:
    port, _, _, _ = append_first()
    snapshot = json.loads(port.fixture_snapshot_bytes())
    snapshot["entries"][0]["effect_authority"] = unsafe_value
    rehash_snapshot(snapshot)
    result = current_read(
        Task014R24FakePublicationPort(
            fixture_snapshot_bytes=canonical_json_bytes(snapshot)
        )
    )
    assert result.state is Task014R24CurrentState.UNSAFE_AUTHORITY
    assert result.reason_codes == ("UNSAFE_ENTRY_AUTHORITY_FLAG",)
    assert result.owner_origin_authenticated is False


@pytest.mark.parametrize("invalid_version", [True, 1.0])
def test_history_parser_requires_exact_integer_version(invalid_version) -> None:
    port, _, _, _ = append_first()
    snapshot = json.loads(port.fixture_snapshot_bytes())
    snapshot["version"] = invalid_version
    rehash_snapshot(snapshot)
    result = current_read(
        Task014R24FakePublicationPort(
            fixture_snapshot_bytes=canonical_json_bytes(snapshot)
        )
    )
    assert result.state is Task014R24CurrentState.BROKEN_CHAIN
    assert result.owner_origin_authenticated is False


def test_injected_valid_snapshot_cannot_authenticate_owner_origin_or_be_appended() -> None:
    original, decision, first, _ = append_first()
    raw = original.fixture_snapshot_bytes()
    assert raw is not None
    injected = Task014R24FakePublicationPort(fixture_snapshot_bytes=raw)
    result = current_read(injected)
    assert result.state is Task014R24CurrentState.BROKEN_CHAIN
    assert result.reason_codes == ("UNTRUSTED_FIXTURE_SNAPSHOT",)
    assert result.owner_store_read is True
    assert result.owner_origin_authenticated is False
    assert result.currentness_verified is False
    second = candidate(
        decision,
        revision=2,
        parent=first.record_sha256,
        result=digest("result-v2"),
    )
    with pytest.raises(ValueError, match="untrusted fixture"):
        consumer().append_candidate(
            port=injected,
            s1_decision=decision,
            candidate=second,
            project_id=PROJECT,
            operation_id=OPERATION,
            ticket_id=TICKET,
            expected_previous_snapshot_sha256=json.loads(raw)["snapshot_sha256"],
        )


@pytest.mark.parametrize("mutation", ["whitespace", "duplicate-key"])
def test_current_read_rejects_noncanonical_or_duplicate_key_json(mutation: str) -> None:
    port, _, _, _ = append_first()
    raw = port.fixture_snapshot_bytes()
    assert raw is not None
    if mutation == "whitespace":
        changed = raw + b"\n"
    else:
        changed = raw.replace(
            b'{"body_embedded":false,',
            b'{"body_embedded":false,"body_embedded":false,',
            1,
        )
    result = current_read(
        Task014R24FakePublicationPort(fixture_snapshot_bytes=changed)
    )
    assert result.state is Task014R24CurrentState.BROKEN_CHAIN
    assert result.owner_origin_authenticated is False


def test_consumer_burns_on_rejected_entry_and_cannot_be_rearmed() -> None:
    value = consumer()
    decision = s1_decision()
    record = candidate(decision)
    with pytest.raises(ValueError, match="exact S1 coordinate"):
        value.append_candidate(
            port=Task014R24FakePublicationPort(),
            s1_decision=decision,
            candidate=record,
            project_id="project.other",
            operation_id=OPERATION,
            ticket_id=TICKET,
            expected_previous_snapshot_sha256=None,
        )
    with pytest.raises(RuntimeError, match="already been burned"):
        value.append_candidate(
            port=Task014R24FakePublicationPort(),
            s1_decision=decision,
            candidate=record,
            project_id=PROJECT,
            operation_id=OPERATION,
            ticket_id=TICKET,
            expected_previous_snapshot_sha256=None,
        )
    with pytest.raises(AttributeError):
        object.__setattr__(value, "_burned", False)
    with pytest.raises(TypeError, match="already initialized"):
        value.__init__(
            task014_owner_acceptance_record_sha256=TASK014_OWNER_ACCEPTANCE_RECORD_SHA256,
            task074_owner_acceptance_record_sha256=TASK074_OWNER_ACCEPTANCE_RECORD_SHA256,
            r24_s1_completion_receipt_sha256=R24_S1_COMPLETION_RECEIPT_SHA256,
            r24_s1_source_sha256=R24_S1_SOURCE_SHA256,
        )


def test_concurrent_consumers_have_exactly_one_winner() -> None:
    value = consumer()
    port = Task014R24FakePublicationPort()
    decision = s1_decision()
    record = candidate(decision)

    def attempt(_: int) -> str:
        try:
            value.append_candidate(
                port=port,
                s1_decision=decision,
                candidate=record,
                project_id=PROJECT,
                operation_id=OPERATION,
                ticket_id=TICKET,
                expected_previous_snapshot_sha256=None,
            )
            return "winner"
        except RuntimeError:
            return "burned"

    with ThreadPoolExecutor(max_workers=16) as executor:
        outcomes = list(executor.map(attempt, range(64)))
    assert outcomes.count("winner") == 1
    assert outcomes.count("burned") == 63


def test_consumer_and_current_read_are_sealed_nonserializable_and_unforgeable() -> None:
    value = consumer()
    with pytest.raises(TypeError, match="consumer types are sealed"):
        class ForgedConsumer(Task014R24RestrictedConsumer):
            pass

    for operation in (
        lambda: copy(value),
        lambda: deepcopy(value),
        lambda: pickle.dumps(value),
        lambda: json.dumps(value),
        lambda: iter(value),
    ):
        with pytest.raises(TypeError):
            operation()
    _, _, _, current = append_first()
    assert not hasattr(current, "to_dict")
    assert not hasattr(current, "__dict__")
    for operation in (
        lambda: copy(current),
        lambda: deepcopy(current),
        lambda: pickle.dumps(current),
        lambda: json.dumps(current),
        lambda: iter(current),
    ):
        with pytest.raises(TypeError):
            operation()
    with pytest.raises(TypeError, match="may only be issued"):
        store_module._Task014R24EffectZeroCurrentRead()
    unissued = object.__new__(store_module._Task014R24EffectZeroCurrentRead)
    with pytest.raises(TypeError, match="provenance"):
        _ = unissued.state


def test_internal_state_escape_and_arbitrary_read_issuance_helpers_are_absent() -> None:
    for name in (
        "_CANDIDATE_STATES",
        "_CONSUMER_STATES",
        "_PORT_STATES",
        "_READ_STATES",
        "_candidate_state",
        "_consumer_state",
        "_initialize_consumer",
        "_issue_read_capability",
        "_owner_port_transaction",
        "_port_state",
        "_read_candidate_data",
        "_read_port_snapshot",
        "_read_state",
        "_register_candidate",
        "_issue_read",
    ):
        assert not hasattr(store_module, name)
    with pytest.raises(TypeError, match="field is invalid"):
        store_module._read_field(
            object.__new__(store_module._Task014R24EffectZeroCurrentRead),
            "__dict__",
        )


def test_unissued_and_reinitialized_objects_cannot_acquire_provenance() -> None:
    decision = s1_decision()
    record = candidate(decision)
    unissued_consumer = object.__new__(Task014R24RestrictedConsumer)
    with pytest.raises(TypeError, match="provenance"):
        unissued_consumer.append_candidate(
            port=Task014R24FakePublicationPort(),
            s1_decision=decision,
            candidate=record,
            project_id=PROJECT,
            operation_id=OPERATION,
            ticket_id=TICKET,
            expected_previous_snapshot_sha256=None,
        )
    unissued_port = object.__new__(Task014R24FakePublicationPort)
    with pytest.raises(TypeError, match="provenance"):
        current_read(unissued_port)
    port = Task014R24FakePublicationPort()
    with pytest.raises(TypeError, match="already initialized"):
        port.__init__()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("task014_owner_acceptance_record_sha256", "0" * 64),
        ("task074_owner_acceptance_record_sha256", "0" * 64),
        ("r24_s1_completion_receipt_sha256", "0" * 64),
        ("r24_s1_source_sha256", "0" * 64),
    ],
)
def test_consumer_rejects_wrong_acceptance_or_s1_bindings(field: str, value: str) -> None:
    arguments = {
        "task014_owner_acceptance_record_sha256": TASK014_OWNER_ACCEPTANCE_RECORD_SHA256,
        "task074_owner_acceptance_record_sha256": TASK074_OWNER_ACCEPTANCE_RECORD_SHA256,
        "r24_s1_completion_receipt_sha256": R24_S1_COMPLETION_RECEIPT_SHA256,
        "r24_s1_source_sha256": R24_S1_SOURCE_SHA256,
    }
    arguments[field] = value
    with pytest.raises(ValueError, match="exact accepted R24 record"):
        Task014R24RestrictedConsumer(**arguments)


def test_module_has_no_filesystem_provider_private_body_model_or_execution_api() -> None:
    path = ROOT / "src" / "ai_video_production" / "task014_r24_publication_store.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported.isdisjoint(
        {"os", "pathlib", "subprocess", "socket", "wave", "requests", "urllib"}
    )
    names = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    assert names.isdisjoint(
        {
            "execute",
            "authorize",
            "issue_ticket",
            "infer",
            "render",
            "load_model",
            "open_audio",
            "publish",
        }
    )
    source = path.read_text(encoding="utf-8")
    assert "Task014NarrationPublicationCurrentReadV1" not in source
    assert "PUBLISHED_READBACK_VERIFIED" not in source
