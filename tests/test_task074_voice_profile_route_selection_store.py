from __future__ import annotations

import ast
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from copy import copy, deepcopy
import pickle
from pathlib import Path
from threading import Barrier

import pytest

from ai_video_production.serialization import sha256_bytes
from ai_video_production.owner_voice_authority import (
    CompletionClass,
    PersistenceState,
    PrivateReferenceState,
    Task074OwnerVoiceAuthorityCompletionReceipt,
)
from ai_video_production.voice_profile_route_selection import (
    CASOutcome,
    ComputePreference,
    RouteMode,
    SourceRequirement,
    VoiceProfileRouteSelection,
    VoiceRouteSelectionCASReadback,
    VoiceRouteSelectionCASRequest,
    VoiceRouteSelectionStorePort,
    validate_route_selection_cas_readback,
)
from ai_video_production.voice_profile_route_selection_store import (
    EXPECTED_CONSUMER,
    FIXTURE_SCOPE,
    FIXTURE_STORE_CONTRACT_VERSION,
    FixtureCASFault,
    FixtureCASResultState,
    VoiceRouteSelectionFixtureCASResult,
    VoiceRouteSelectionFixtureStore,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "ai_video_production" / "voice_profile_route_selection_store.py"
READBACK_AT = "2026-09-01T09:01:00Z"
RECONCILIATION_AT = "2026-09-01T09:02:00Z"


def digest(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def selection(
    *,
    revision: int = 1,
    predecessor: str | None = None,
    project_id: str = "project.alpha",
    mode: RouteMode = RouteMode.ZERO_SHOT_LOCAL,
) -> VoiceProfileRouteSelection:
    fine_tuned = mode is RouteMode.FINE_TUNED_LOCAL
    return VoiceProfileRouteSelection.create(
        project_id=project_id,
        project_manifest_revision_sha256=digest("manifest"),
        voice_profile_id="voice.owner",
        voice_profile_revision=7,
        voice_profile_revision_sha256=digest("voice-profile-7"),
        consent_revision_sha256=digest("consent-4"),
        consent_current_evaluation_sha256=digest("consent-current"),
        consent_evaluated_at="2026-09-01T08:00:00Z",
        consent_expires_at="2026-09-02T08:00:00Z",
        selection_revision=revision,
        predecessor_selection_sha256=predecessor,
        route_mode=mode,
        public_route_key=(
            "narration.qwen3.finetuned" if fine_tuned else "narration.qwen3.local"
        ),
        installed_route_binding_sha256=digest("installed-route"),
        local_audio_model_inventory_revision_sha256=digest("inventory-revision"),
        local_audio_model_inventory_entry_sha256=digest("inventory-entry"),
        model_license_evidence_sha256=digest("license"),
        source_requirement=(
            SourceRequirement.MODEL_CANDIDATE_REQUIRED
            if fine_tuned
            else SourceRequirement.PRIVATE_REFERENCE_REQUIRED
        ),
        model_candidate_revision_sha256=(digest("model-revision") if fine_tuned else None),
        model_candidate_currentness_sha256=(
            digest("model-currentness") if fine_tuned else None
        ),
        compute_preference_ref=ComputePreference.AUTO,
        created_at="2026-09-01T09:00:00Z",
    )


def request(
    chosen: VoiceProfileRouteSelection,
    *,
    operation_id: str,
    expected_project_head: str,
) -> VoiceRouteSelectionCASRequest:
    return VoiceRouteSelectionCASRequest.create(
        operation_id=operation_id,
        selection=chosen,
        expected_project_transaction_head_sha256=expected_project_head,
        expected_selection_head_sha256=chosen.to_dict()["predecessor_selection_sha256"],
    )


def fixture_store(
    *,
    fault: FixtureCASFault = FixtureCASFault.NONE,
) -> VoiceRouteSelectionFixtureStore:
    return VoiceRouteSelectionFixtureStore(
        project_id="project.alpha",
        initial_project_transaction_head_sha256=digest("project-head-0"),
        pinned_fixture_store_identity_sha256=digest("fixture-store-identity"),
        readback_at=READBACK_AT,
        reconciliation_readback_at=RECONCILIATION_AT,
        expected_consumer=EXPECTED_CONSUMER,
        fixture_scope=FIXTURE_SCOPE,
        next_fault=fault,
    )


def typed_readback(value: object) -> VoiceRouteSelectionCASReadback:
    assert isinstance(value, VoiceRouteSelectionFixtureCASResult)
    assert not isinstance(value, Mapping)
    assert value.fixture_only is True
    assert value.canonical_port_compatible is False
    assert value.producer_binding_state == "NOT_BOUND"
    assert value.execution_ready is False
    return value.fixture_readback()


def assert_fixture_boundary(readback: VoiceRouteSelectionCASReadback) -> None:
    value = readback.to_dict()
    assert value["producer_binding_state"] == "NOT_BOUND"
    assert value["fixture_only"] is True
    assert value["canonical_producer_acceptance_state"] == "NOT_CONFIRMED"
    assert value["canonical_producer_readback"] is False
    assert value["execution_ready"] is False
    assert value["authority_created"] is False
    assert value["execution_authorized"] is False


def test_fixture_store_is_explicitly_noncanonical_and_effect_zero() -> None:
    store = fixture_store()
    assert FIXTURE_STORE_CONTRACT_VERSION == "VOICE_ROUTE_SELECTION_FIXTURE_STORE_V1"
    assert store.contract_version == FIXTURE_STORE_CONTRACT_VERSION
    assert store.expected_consumer == EXPECTED_CONSUMER
    assert store.fixture_scope == FIXTURE_SCOPE
    assert store.canonical_port_compatible is False
    assert store.fixture_only is True
    assert store.producer_binding_state == "NOT_BOUND"
    assert store.canonical_producer_readback is False
    assert store.authority_created is False
    assert store.execution_ready is False
    assert store.production_eligible is False
    assert store.durable_persistence_performed is False
    assert store.external_effect_performed is False
    assert store.private_body_present is False
    assert store.path_present is False
    assert store.secret_present is False
    assert store.selection_head_sha256 is None
    assert store.selection_revision == 0
    assert not hasattr(store, "__dict__")


def test_fixture_store_cannot_satisfy_the_canonical_port_shape() -> None:
    store = fixture_store()
    assert "compare_and_append" in VoiceRouteSelectionStorePort.__dict__
    assert not hasattr(store, "compare_and_append")
    chosen = selection()
    cas_request = request(
        chosen,
        operation_id="operation.route.structural",
        expected_project_head=store.project_transaction_head_sha256,
    )
    internal = getattr(
        store,
        "_VoiceRouteSelectionFixtureStore__simulate_compare_and_append_locked",
    )
    with pytest.raises(RuntimeError, match="atomic public seam"):
        internal(cas_request, chosen)
    assert store.selection_head_sha256 is None
    result = store.simulate_compare_and_append(cas_request, chosen)
    assert result.state is FixtureCASResultState.COMMITTED_FIXTURE
    readback = typed_readback(result)
    assert readback.to_dict()["outcome"] == CASOutcome.COMMITTED.value
    assert_fixture_boundary(readback)


def test_fixture_store_readback_composes_only_into_noncanonical_completion() -> None:
    store = fixture_store()
    chosen = selection()
    cas_request = request(
        chosen,
        operation_id="operation.route.completion-fixture",
        expected_project_head=store.project_transaction_head_sha256,
    )
    readback = typed_readback(store.simulate_compare_and_append(cas_request, chosen)).to_dict()
    completion = Task074OwnerVoiceAuthorityCompletionReceipt.create(
        completion_id="completion.fixture.store",
        completion_class=CompletionClass.TASK074_IMPLEMENTATION_COMPLETE,
        project_id="project.alpha",
        project_manifest_revision_sha256=digest("manifest"),
        installed_startup_context_binding_sha256=digest("startup-context"),
        voice_profile_id="voice.owner",
        voice_profile_revision=7,
        voice_profile_revision_sha256=digest("voice-profile-7"),
        consent_current_evaluation_sha256=digest("consent-current"),
        route_mode=RouteMode.ZERO_SHOT_LOCAL,
        route_selection_revision=1,
        route_selection_sha256=chosen.selection_sha256,
        route_selection_store_receipt_sha256=readback["cas_readback_sha256"],
        reference_lifecycle_snapshot_sha256=None,
        reference_preparation_receipt_sha256=None,
        reference_capability_binding_sha256=None,
        reference_media_policy_sha256=None,
        reference_transcript_binding_receipt_sha256=None,
        model_candidate_revision_sha256=None,
        model_candidate_currentness_sha256=None,
        human_action_registry_receipt_sha256=digest("human-registry-fixture"),
        operation_profile_registry_receipt_sha256=digest("operation-registry-fixture"),
        persistence_state=PersistenceState.DURABLE_VERIFIED,
        private_reference_state=PrivateReferenceState.NOT_CONFIRMED,
        owner_reference_verified=False,
        issued_at="2026-09-01T09:03:00Z",
        expires_at="2026-09-01T09:08:00Z",
    ).to_dict()
    assert completion["route_selection_store_receipt_sha256"] == readback[
        "cas_readback_sha256"
    ]
    assert completion["producer_binding_state"] == "NOT_BOUND"
    assert completion["fixture_only"] is True
    assert completion["canonical_producer_readback"] is False
    assert completion["execution_ready"] is False
    assert completion["execution_authorized"] is False
    assert completion["owner_reference_verified"] is False


def test_two_exact_revisions_commit_deterministically_in_memory() -> None:
    stores = (fixture_store(), fixture_store())
    results: list[tuple[dict[str, object], dict[str, object], str]] = []
    for store in stores:
        first = selection()
        first_request = request(
            first,
            operation_id="operation.route.1",
            expected_project_head=store.project_transaction_head_sha256,
        )
        first_readback = typed_readback(store.simulate_compare_and_append(first_request, first))
        validate_route_selection_cas_readback(first_request, first, first_readback)
        assert first_readback.to_dict()["outcome"] == CASOutcome.COMMITTED.value
        assert_fixture_boundary(first_readback)

        second = selection(revision=2, predecessor=first.selection_sha256)
        second_request = request(
            second,
            operation_id="operation.route.2",
            expected_project_head=store.project_transaction_head_sha256,
        )
        second_readback = typed_readback(store.simulate_compare_and_append(second_request, second))
        validate_route_selection_cas_readback(second_request, second, second_readback)
        assert second_readback.to_dict()["outcome"] == CASOutcome.COMMITTED.value
        assert_fixture_boundary(second_readback)
        assert store.selection_head_sha256 == second.selection_sha256
        assert store.selection_revision == 2
        results.append(
            (
                first_readback.to_dict(),
                second_readback.to_dict(),
                store.project_transaction_head_sha256,
            )
        )

    assert results[0] == results[1]


def test_stale_project_head_conflicts_without_mutation_or_retry() -> None:
    store = fixture_store()
    initial_head = store.project_transaction_head_sha256
    chosen = selection()
    stale_request = request(
        chosen,
        operation_id="operation.route.stale",
        expected_project_head=digest("stale-project-head"),
    )
    readback = typed_readback(store.simulate_compare_and_append(stale_request, chosen))
    validate_route_selection_cas_readback(stale_request, chosen, readback)
    assert readback.to_dict()["outcome"] == CASOutcome.CONFLICT.value
    assert readback.to_dict()["automatic_retry_started"] is False
    assert store.project_transaction_head_sha256 == initial_head
    assert store.selection_head_sha256 is None
    assert store.selection_revision == 0
    assert_fixture_boundary(readback)
    with pytest.raises(ValueError, match="non-replayable"):
        store.simulate_compare_and_append(stale_request, chosen)


@pytest.mark.parametrize(
    ("revision", "predecessor"),
    (
        (2, "wrong-selection-head"),
        (3, "current-selection-head"),
    ),
)
def test_stale_selection_head_or_noncontiguous_revision_conflicts(
    revision: int,
    predecessor: str,
) -> None:
    store = fixture_store()
    first = selection()
    first_request = request(
        first,
        operation_id="operation.route.first",
        expected_project_head=store.project_transaction_head_sha256,
    )
    store.simulate_compare_and_append(first_request, first)
    committed_project_head = store.project_transaction_head_sha256

    predecessor_sha256 = (
        digest("wrong-selection-head")
        if predecessor == "wrong-selection-head"
        else first.selection_sha256
    )
    candidate = selection(revision=revision, predecessor=predecessor_sha256)
    candidate_request = request(
        candidate,
        operation_id=f"operation.route.conflict-{revision}-{predecessor}",
        expected_project_head=committed_project_head,
    )
    readback = typed_readback(store.simulate_compare_and_append(candidate_request, candidate))
    assert readback.to_dict()["outcome"] == CASOutcome.CONFLICT.value
    assert store.project_transaction_head_sha256 == committed_project_head
    assert store.selection_head_sha256 == first.selection_sha256
    assert store.selection_revision == 1
    assert_fixture_boundary(readback)


def test_first_writer_wins_and_second_genesis_request_does_not_rebase() -> None:
    store = fixture_store()
    initial_head = store.project_transaction_head_sha256
    first = selection()
    second = selection(mode=RouteMode.FINE_TUNED_LOCAL)
    first_request = request(
        first,
        operation_id="operation.route.writer-one",
        expected_project_head=initial_head,
    )
    second_request = request(
        second,
        operation_id="operation.route.writer-two",
        expected_project_head=initial_head,
    )
    assert typed_readback(store.simulate_compare_and_append(first_request, first)).to_dict()[
        "outcome"
    ] == CASOutcome.COMMITTED.value
    second_readback = typed_readback(store.simulate_compare_and_append(second_request, second))
    assert second_readback.to_dict()["outcome"] == CASOutcome.CONFLICT.value
    assert store.selection_head_sha256 == first.selection_sha256
    assert store.selection_revision == 1
    assert_fixture_boundary(second_readback)


def test_concurrent_first_writers_have_exactly_one_winner() -> None:
    store = fixture_store()
    initial_head = store.project_transaction_head_sha256
    zero_shot = selection()
    fine_tuned = selection(mode=RouteMode.FINE_TUNED_LOCAL)
    zero_request = request(
        zero_shot,
        operation_id="operation.route.concurrent-zero",
        expected_project_head=initial_head,
    )
    fine_request = request(
        fine_tuned,
        operation_id="operation.route.concurrent-fine",
        expected_project_head=initial_head,
    )
    barrier = Barrier(3)

    def invoke(
        cas_request: VoiceRouteSelectionCASRequest,
        chosen: VoiceProfileRouteSelection,
    ) -> VoiceRouteSelectionFixtureCASResult:
        barrier.wait()
        return store.simulate_compare_and_append(cas_request, chosen)

    with ThreadPoolExecutor(max_workers=2) as executor:
        zero_future = executor.submit(invoke, zero_request, zero_shot)
        fine_future = executor.submit(invoke, fine_request, fine_tuned)
        barrier.wait()
        results = (zero_future.result(), fine_future.result())

    states = [result.state for result in results]
    assert states.count(FixtureCASResultState.COMMITTED_FIXTURE) == 1
    assert states.count(FixtureCASResultState.CONFLICT_FIXTURE) == 1
    readbacks = [typed_readback(result).to_dict() for result in results]
    assert [row["outcome"] for row in readbacks].count(CASOutcome.COMMITTED.value) == 1
    assert [row["outcome"] for row in readbacks].count(CASOutcome.CONFLICT.value) == 1
    assert store.selection_revision == 1
    assert store.selection_head_sha256 in {
        zero_shot.selection_sha256,
        fine_tuned.selection_sha256,
    }


def test_concurrent_duplicate_operation_has_one_commit_and_one_replay_rejection() -> None:
    store = fixture_store()
    chosen = selection()
    cas_request = request(
        chosen,
        operation_id="operation.route.concurrent-duplicate",
        expected_project_head=store.project_transaction_head_sha256,
    )
    barrier = Barrier(3)

    def invoke() -> VoiceRouteSelectionFixtureCASResult | ValueError:
        barrier.wait()
        try:
            return store.simulate_compare_and_append(cas_request, chosen)
        except ValueError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(invoke)
        second = executor.submit(invoke)
        barrier.wait()
        results = (first.result(), second.result())

    committed = [item for item in results if isinstance(item, VoiceRouteSelectionFixtureCASResult)]
    rejected = [item for item in results if isinstance(item, ValueError)]
    assert len(committed) == 1
    assert committed[0].state is FixtureCASResultState.COMMITTED_FIXTURE
    assert len(rejected) == 1
    assert "non-replayable" in str(rejected[0])
    assert store.selection_revision == 1
    assert store.selection_head_sha256 == chosen.selection_sha256


def test_stale_conflict_does_not_consume_the_next_valid_fault() -> None:
    store = fixture_store(fault=FixtureCASFault.BEFORE_COMMIT)
    chosen = selection()
    stale = request(
        chosen,
        operation_id="operation.route.stale-first",
        expected_project_head=digest("stale-project-head"),
    )
    assert typed_readback(store.simulate_compare_and_append(stale, chosen)).to_dict()[
        "outcome"
    ] == CASOutcome.CONFLICT.value

    valid = request(
        chosen,
        operation_id="operation.route.valid-second",
        expected_project_head=store.project_transaction_head_sha256,
    )
    assert typed_readback(store.simulate_compare_and_append(valid, chosen)).to_dict()[
        "outcome"
    ] == CASOutcome.NOT_CONFIRMED.value
    assert store.selection_head_sha256 is None


def test_f01_before_commit_keeps_old_heads_and_burns_operation() -> None:
    store = fixture_store(fault=FixtureCASFault.BEFORE_COMMIT)
    initial_head = store.project_transaction_head_sha256
    chosen = selection()
    cas_request = request(
        chosen,
        operation_id="operation.route.f01",
        expected_project_head=initial_head,
    )
    readback = typed_readback(store.simulate_compare_and_append(cas_request, chosen))
    validate_route_selection_cas_readback(cas_request, chosen, readback)
    value = readback.to_dict()
    assert value["outcome"] == CASOutcome.NOT_CONFIRMED.value
    assert value["committed_selection_sha256"] is None
    assert value["result_project_transaction_head_sha256"] == initial_head
    assert value["result_selection_head_sha256"] is None
    assert store.project_transaction_head_sha256 == initial_head
    assert store.selection_head_sha256 is None
    assert_fixture_boundary(readback)
    with pytest.raises(ValueError, match="non-replayable"):
        store.simulate_compare_and_append(cas_request, chosen)


def test_f02_post_commit_unknown_requires_exact_pinned_reconciliation() -> None:
    store = fixture_store(
        fault=FixtureCASFault.AFTER_COMMIT_BEFORE_PINNED_READBACK
    )
    chosen = selection()
    cas_request = request(
        chosen,
        operation_id="operation.route.f02",
        expected_project_head=store.project_transaction_head_sha256,
    )
    unknown = typed_readback(store.simulate_compare_and_append(cas_request, chosen))
    validate_route_selection_cas_readback(cas_request, chosen, unknown)
    unknown_value = unknown.to_dict()
    assert unknown_value["outcome"] == CASOutcome.NOT_CONFIRMED.value
    assert unknown_value["committed_selection_sha256"] is None
    assert unknown_value["pinned_readback_match"] is False
    assert store.selection_head_sha256 == chosen.selection_sha256
    assert_fixture_boundary(unknown)

    next_selection = selection(revision=2, predecessor=chosen.selection_sha256)
    next_request = request(
        next_selection,
        operation_id="operation.route.blocked",
        expected_project_head=store.project_transaction_head_sha256,
    )
    with pytest.raises(RuntimeError, match="must be reconciled"):
        store.simulate_compare_and_append(next_request, next_selection)

    internal_reconcile = getattr(
        store,
        "_VoiceRouteSelectionFixtureStore__simulate_reconcile_after_unknown_locked",
    )
    with pytest.raises(RuntimeError, match="atomic public seam"):
        internal_reconcile(cas_request, chosen)
    reconciled = typed_readback(store.simulate_reconcile_after_unknown(cas_request, chosen))
    validate_route_selection_cas_readback(cas_request, chosen, reconciled)
    reconciled_value = reconciled.to_dict()
    assert reconciled_value["outcome"] == CASOutcome.COMMITTED.value
    assert reconciled_value["committed_selection_sha256"] == chosen.selection_sha256
    assert reconciled_value["pinned_readback_match"] is True
    assert reconciled_value["readback_at"] == RECONCILIATION_AT
    assert_fixture_boundary(reconciled)

    with pytest.raises(ValueError, match="no reconcilable"):
        store.simulate_reconcile_after_unknown(cas_request, chosen)
    with pytest.raises(ValueError, match="non-replayable"):
        store.simulate_compare_and_append(cas_request, chosen)


def test_f02_reconciliation_rejects_cross_operation_or_selection_lineage() -> None:
    store = fixture_store(
        fault=FixtureCASFault.AFTER_COMMIT_BEFORE_PINNED_READBACK
    )
    chosen = selection()
    cas_request = request(
        chosen,
        operation_id="operation.route.f02-cross",
        expected_project_head=store.project_transaction_head_sha256,
    )
    store.simulate_compare_and_append(cas_request, chosen)

    wrong_selection = selection(mode=RouteMode.FINE_TUNED_LOCAL)
    wrong_request = request(
        wrong_selection,
        operation_id="operation.route.f02-cross",
        expected_project_head=digest("project-head-0"),
    )
    with pytest.raises(ValueError, match="lineage or pinned state mismatch"):
        store.simulate_reconcile_after_unknown(wrong_request, wrong_selection)
    assert store.selection_head_sha256 == chosen.selection_sha256


def test_f03_project_head_change_aborts_selection_and_is_nonreplayable() -> None:
    store = fixture_store(fault=FixtureCASFault.PROJECT_HEAD_CHANGED_DURING_CAS)
    initial_head = store.project_transaction_head_sha256
    chosen = selection()
    cas_request = request(
        chosen,
        operation_id="operation.route.f03",
        expected_project_head=initial_head,
    )
    readback = typed_readback(store.simulate_compare_and_append(cas_request, chosen))
    validate_route_selection_cas_readback(cas_request, chosen, readback)
    value = readback.to_dict()
    assert value["outcome"] == CASOutcome.CONFLICT.value
    assert value["result_project_transaction_head_sha256"] != initial_head
    assert value["result_selection_head_sha256"] is None
    assert store.project_transaction_head_sha256 != initial_head
    assert store.selection_head_sha256 is None
    assert store.selection_revision == 0
    assert_fixture_boundary(readback)
    with pytest.raises(ValueError, match="non-replayable"):
        store.simulate_compare_and_append(cas_request, chosen)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("expected_consumer", "TASK-075", "consumer"),
        ("fixture_scope", "PRODUCTION", "pure-test scope"),
        ("project_id", "C:\\private\\project", "host path"),
        ("project_id", "private/project", "host path"),
        ("readback_at", "now", "canonical UTC"),
        (
            "reconciliation_readback_at",
            "2026-09-01T09:00:00Z",
            "cannot predate",
        ),
    ),
)
def test_fixture_construction_rejects_wrong_consumer_scope_path_or_time(
    field: str,
    value: str,
    message: str,
) -> None:
    arguments: dict[str, object] = {
        "project_id": "project.alpha",
        "initial_project_transaction_head_sha256": digest("project-head-0"),
        "pinned_fixture_store_identity_sha256": digest("fixture-store-identity"),
        "readback_at": READBACK_AT,
        "reconciliation_readback_at": RECONCILIATION_AT,
        "expected_consumer": EXPECTED_CONSUMER,
        "fixture_scope": FIXTURE_SCOPE,
    }
    arguments[field] = value
    with pytest.raises(ValueError, match=message):
        VoiceRouteSelectionFixtureStore(**arguments)  # type: ignore[arg-type]


def test_store_rejects_wrong_project_without_consuming_or_mutating() -> None:
    store = fixture_store()
    initial_head = store.project_transaction_head_sha256
    wrong = selection(project_id="project.beta")
    cas_request = request(
        wrong,
        operation_id="operation.route.wrong-project",
        expected_project_head=initial_head,
    )
    with pytest.raises(ValueError, match="Project"):
        store.simulate_compare_and_append(cas_request, wrong)
    assert store.project_transaction_head_sha256 == initial_head
    assert store.selection_head_sha256 is None


def test_store_rejects_cross_selection_request_and_wrong_input_types() -> None:
    store = fixture_store()
    zero_shot = selection()
    fine_tuned = selection(mode=RouteMode.FINE_TUNED_LOCAL)
    zero_request = request(
        zero_shot,
        operation_id="operation.route.cross-selection",
        expected_project_head=store.project_transaction_head_sha256,
    )
    with pytest.raises(ValueError, match="digest mismatch"):
        store.simulate_compare_and_append(zero_request, fine_tuned)
    with pytest.raises(TypeError, match="request"):
        store.simulate_compare_and_append(object(), zero_shot)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="selection"):
        store.simulate_compare_and_append(zero_request, object())  # type: ignore[arg-type]
    assert store.selection_head_sha256 is None


def test_fixture_store_rejects_copy_pickle_and_subclass_promotion() -> None:
    store = fixture_store()
    with pytest.raises(TypeError, match="non-copyable"):
        copy(store)
    with pytest.raises(TypeError, match="non-copyable"):
        deepcopy(store)
    with pytest.raises(TypeError, match="non-serializable"):
        pickle.dumps(store)
    with pytest.raises(TypeError, match="cannot be subclassed"):

        class PromotedStore(VoiceRouteSelectionFixtureStore):
            pass

    chosen = selection()
    cas_request = request(
        chosen,
        operation_id="operation.route.nominal-result",
        expected_project_head=store.project_transaction_head_sha256,
    )
    result = store.simulate_compare_and_append(cas_request, chosen)
    with pytest.raises(TypeError, match="non-copyable"):
        copy(result)
    with pytest.raises(TypeError, match="non-copyable"):
        deepcopy(result)
    with pytest.raises(TypeError, match="non-serializable"):
        pickle.dumps(result)
    with pytest.raises(TypeError, match="created only"):
        VoiceRouteSelectionFixtureCASResult(result.fixture_readback())
    with pytest.raises(TypeError, match="cannot be subclassed"):

        class PromotedResult(VoiceRouteSelectionFixtureCASResult):
            pass


def test_fixture_store_module_has_no_io_native_model_or_runtime_wiring() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned_imports = {
        "ctypes",
        "http",
        "os",
        "pathlib",
        "requests",
        "shutil",
        "socket",
        "sqlite3",
        "subprocess",
        "tempfile",
        "torch",
        "urllib",
        "wave",
    }
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.lstrip(".").split(".", 1)[0])
    assert imported_roots.isdisjoint(banned_imports)

    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert called_names.isdisjoint({"breakpoint", "eval", "exec", "open"})
    assert "utc_now_iso" not in source
    assert "canonical producer adapter" not in source.casefold()

    for module_path in (ROOT / "src" / "ai_video_production").glob("*.py"):
        if module_path == SOURCE:
            continue
        assert "voice_profile_route_selection_store" not in module_path.read_text(
            encoding="utf-8"
        )
