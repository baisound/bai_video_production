from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
import pickle

from jsonschema import Draft202012Validator, RefResolver
import pytest

import ai_video_production.audio_completion_ledger_contract as ledger
from ai_video_production.audio_completion_ledger_contract import (
    AppendDecision,
    AudioCompletionAppendEvaluation,
    AudioCompletionLatestObservation,
    AudioCompletionLedgerCasExpectation,
    AudioCompletionLedgerEntryEnvelope,
    AudioCompletionLedgerKeyBinding,
    EMPTY_CHAIN_SHA256,
    cas_for_chain,
    evaluate_append,
    make_entry_envelope,
    observe_latest,
    parse_append_evaluation,
    parse_cas_expectation,
    parse_entry_envelope,
    parse_latest_observation,
    parse_ledger_key,
    validate_full_chain,
)
from ai_video_production.audio_completion_receipt import (
    AudioCompletionAdmissionCandidate,
    AudioCompletionRole,
    EvidenceBinding,
    EvidenceState,
    FinishingRequirement,
    RoleDeclaration,
    RolePresence,
    RoleRequirement,
    ScopeBinding,
    make_closed_receipt_ref,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "audio-completion-ledger-contract.schema.json"
MIRROR_PATH = ROOT / "src" / "ai_video_production" / "schema_resources" / "audio-completion-ledger-contract.schema.json"
R0_SCHEMA_PATH = ROOT / "schemas" / "audio-completion-receipt.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
R0_SCHEMA = json.loads(R0_SCHEMA_PATH.read_text(encoding="utf-8"))
RESOLVER = RefResolver.from_schema(SCHEMA, store={R0_SCHEMA["$id"]: R0_SCHEMA})
VALIDATOR = Draft202012Validator(SCHEMA, resolver=RESOLVER)
D = "sha256:" + "a" * 64


def _scope(tag: str = "a") -> ScopeBinding:
    return ScopeBinding.create(
        project_id="project-1", project_revision=3,
        project_manifest_sha256="sha256:" + tag * 64,
        timeline_id="timeline-1", timeline_revision=7,
        timeline_sha256="sha256:" + "b" * 64,
        workspace_snapshot_sha256="sha256:" + "c" * 64,
        source_truth_receipt_id="audio-source-1",
        source_truth_receipt_sha256="sha256:" + "d" * 64,
        role_policy_receipt_id="audio-role-policy-1",
        role_policy_receipt_sha256="sha256:" + "9" * 64,
    )


def _ref(kind: str):
    return make_closed_receipt_ref(kind, record_id=f"{kind}-1", record_sha256=D)


def _candidate(*, previous=None, at="2026-08-21T01:00:00Z", scope=None, receipt_id="audio-completion-1"):
    item = EvidenceBinding.create(
        item_id="source-main", role=AudioCompletionRole.SOURCE,
        item_source_sha256="sha256:" + "e" * 64,
        review_receipt=_ref("review_receipt"),
        external_review_receipt=_ref("external_review_receipt"),
        placement_receipt=_ref("placement_receipt"),
        narration_publication_receipt=None, finishing_receipt=None,
        evidence_state=EvidenceState.PASS,
        evidence_current_at_evaluation=True, evidence_invalidation_epoch=0,
    )
    roles = []
    for role in AudioCompletionRole:
        present = role is AudioCompletionRole.SOURCE
        roles.append(RoleDeclaration(
            role,
            RoleRequirement.REQUIRED if present else RoleRequirement.OPTIONAL,
            RolePresence.PRESENT if present else RolePresence.ABSENT_CONFIRMED,
            FinishingRequirement.NOT_APPLICABLE,
            ("source-main",) if present else (),
            (item.to_dict()["evidence_binding_sha256"],) if present else (),
        ))
    return AudioCompletionAdmissionCandidate.create(
        receipt_id=receipt_id, scope=scope or _scope(),
        role_declarations=tuple(roles), evidence_bindings=(item,),
        evaluated_at=at, previous=previous,
    )


def _chain2():
    first_candidate = _candidate()
    second_candidate = _candidate(previous=first_candidate, at="2026-08-21T01:00:01Z")
    key = AudioCompletionLedgerKeyBinding.for_candidate(first_candidate)
    first = make_entry_envelope(first_candidate, key=key)
    second = make_entry_envelope(second_candidate, key=key, previous_entry=first)
    return key, first_candidate, second_candidate, first, second


def _assert_schema(value):
    VALIDATOR.validate(value)


def test_key_entry_cas_and_empty_observation_roundtrip_schema_parity():
    candidate = _candidate()
    key = AudioCompletionLedgerKeyBinding.for_candidate(candidate)
    entry = make_entry_envelope(candidate, key=key)
    empty_cas = cas_for_chain((), key)
    empty = observe_latest((), key)
    assert empty_cas.to_dict()["expected_chain_sha256"] == EMPTY_CHAIN_SHA256
    assert empty.to_dict()["observation_state"] == "EMPTY"
    assert entry.to_dict()["entry_state"] == "PERSISTENCE_NOT_OBSERVED_BY_R1A"
    for record, parser in (
        (key, parse_ledger_key), (entry, parse_entry_envelope),
        (empty_cas, parse_cas_expectation), (empty, parse_latest_observation),
    ):
        value = record.to_dict()
        _assert_schema(value)
        assert parser(value).to_dict() == value
    _assert_schema(empty.to_public_dict())


def test_two_entry_chain_is_ordered_domain_bound_and_non_authoritative():
    key, _, _, first, second = _chain2()
    chain = validate_full_chain((first, second), key)
    assert [entry.to_dict()["entry_revision"] for entry in chain] == [1, 2]
    assert second.to_dict()["parent_entry_sha256"] == first.to_dict()["entry_sha256"]
    assert second.to_dict()["prior_chain_sha256"] == first.to_dict()["chain_sha256"]
    latest = observe_latest(chain, key)
    value = latest.to_dict()
    assert value["entry_count"] == 2
    assert value["latest_candidate_state"] == "SOURCE_REVALIDATION_REQUIRED"
    assert value["canonical_state"] == "NOT_MINTED"
    assert value["current_valid"] is False
    assert value["provided_chain_semantically_validated"] is False
    assert value["consumer_revalidation_required"] is True
    assert not any(value["authority_flags"].values())
    assert not any(value["effect_flags"].values())
    _assert_schema(first.to_dict()); _assert_schema(second.to_dict()); _assert_schema(value)


def test_append_evaluation_eligible_and_idempotent_never_claims_commit():
    key, first_candidate, second_candidate, first, second = _chain2()
    empty_cas = cas_for_chain((), key)
    first_eval = evaluate_append((), first_candidate, empty_cas)
    assert first_eval.to_dict()["decision"] == AppendDecision.CONTRACT_APPEND_ELIGIBLE_NOT_AUTHORIZED.value
    current_cas = cas_for_chain((first,), key)
    second_eval = evaluate_append((first,), second_candidate, current_cas)
    assert second_eval.to_dict()["decision"] == AppendDecision.CONTRACT_APPEND_ELIGIBLE_NOT_AUTHORIZED.value
    replay = evaluate_append((first, second), second_candidate, current_cas)
    assert replay.to_dict()["decision"] == AppendDecision.IDEMPOTENT_LATEST_MATCH_NOT_AUTHORIZED.value
    for result in (first_eval, second_eval, replay):
        value = result.to_dict()
        assert value["reason_codes"] == [value["decision"]]
        assert not any(value["authority_flags"].values())
        assert not any(value["effect_flags"].values())
        _assert_schema(value)
        assert parse_append_evaluation(value).to_dict() == value


def test_stale_cas_rollback_gap_and_cross_key_are_fail_closed():
    key, first_candidate, second_candidate, first, second = _chain2()
    empty_cas = cas_for_chain((), key)
    stale = evaluate_append((first,), second_candidate, empty_cas)
    assert stale.to_dict()["decision"] == "CAS_CONFLICT"
    rollback = evaluate_append((first, second), first_candidate, empty_cas)
    assert rollback.to_dict()["decision"] == "TRANSITION_CONFLICT"
    third = _candidate(previous=second_candidate, at="2026-08-21T01:00:02Z")
    skipped = evaluate_append((first,), third, cas_for_chain((first,), key))
    assert skipped.to_dict()["decision"] == "TRANSITION_CONFLICT"
    other = _candidate(scope=_scope("f"), receipt_id="audio-completion-other")
    cross = evaluate_append((first,), other, cas_for_chain((first,), key))
    assert cross.to_dict()["decision"] == "LEDGER_KEY_CONFLICT"


@pytest.mark.parametrize("mutation", ["reorder", "entry-hash", "candidate", "parent", "prior-chain"])
def test_chain_tamper_reorder_fork_and_replay_reject(mutation):
    key, _, _, first, second = _chain2()
    values = [first.to_dict(), second.to_dict()]
    if mutation == "reorder":
        values.reverse()
    elif mutation == "entry-hash":
        values[1]["entry_sha256"] = D
    elif mutation == "candidate":
        values[1]["candidate_receipt_sha256"] = D
    elif mutation == "parent":
        values[1]["parent_entry_sha256"] = D
    else:
        values[1]["prior_chain_sha256"] = D
    with pytest.raises(ValueError):
        validate_full_chain(values, key)


def test_runtime_and_schema_reject_authority_unknown_fields_bool_counts_and_digest_tamper():
    key, _, _, first, second = _chain2()
    records = [key.to_dict(), first.to_dict(), cas_for_chain((first, second), key).to_dict(),
               observe_latest((first, second), key).to_dict()]
    for original in records:
        unknown = copy.deepcopy(original); unknown["unknown"] = True
        with pytest.raises(Exception): _assert_schema(unknown)
        if original["record_type"] == "AudioCompletionLedgerKeyBinding":
            with pytest.raises(ValueError): parse_ledger_key(unknown)
    entry = first.to_dict(); entry["authority_flags"]["native_append_authorized"] = True
    with pytest.raises(ValueError): parse_entry_envelope(entry)
    with pytest.raises(Exception): _assert_schema(entry)
    cas = cas_for_chain((), key).to_dict(); cas["expected_entry_count"] = True
    with pytest.raises(ValueError): parse_cas_expectation(cas)
    with pytest.raises(Exception): _assert_schema(cas)
    observation = observe_latest((first, second), key).to_dict(); observation["observation_sha256"] = D
    with pytest.raises(ValueError): parse_latest_observation(observation)


@pytest.mark.parametrize("bad_entries", [None, {}, "", b"", bytearray(), set()])
def test_append_rejects_false_empty_and_noncanonical_chain_containers(bad_entries):
    candidate = _candidate()
    key = AudioCompletionLedgerKeyBinding.for_candidate(candidate)
    with pytest.raises((TypeError, ValueError)):
        evaluate_append(bad_entries, candidate, cas_for_chain((), key))


@pytest.mark.parametrize("bad_entries", [[None], [{}], [{"key_binding": {}}]])
def test_malformed_first_entry_is_a_closed_validation_failure(bad_entries):
    candidate = _candidate()
    key = AudioCompletionLedgerKeyBinding.for_candidate(candidate)
    with pytest.raises(ValueError, match="entry chain item"):
        evaluate_append(bad_entries, candidate, cas_for_chain((), key))


def test_chain_count_entry_bytes_aggregate_bytes_and_items_are_bounded(monkeypatch):
    key, _, _, first, _ = _chain2()
    with pytest.raises(ValueError, match="entry-count"):
        validate_full_chain([first] * 257, key)
    oversized = first.to_dict()
    oversized["oversized"] = "x" * (ledger._MAX_ENTRY_CANONICAL_BYTES + 1)
    with pytest.raises(ValueError, match="canonical byte"):
        validate_full_chain([oversized], key)
    monkeypatch.setattr(ledger, "_MAX_CHAIN_CANONICAL_BYTES", 1)
    with pytest.raises(ValueError, match="aggregate canonical byte"):
        validate_full_chain([first], key)
    monkeypatch.setattr(ledger, "_MAX_CHAIN_CANONICAL_BYTES", 16 * 1024 * 1024)
    monkeypatch.setattr(ledger, "_MAX_CHAIN_ITEMS", 0)
    with pytest.raises(ValueError, match="aggregate item"):
        validate_full_chain([first], key)


def test_public_functions_reject_key_and_expectation_subclasses_before_reuse():
    candidate = _candidate()
    key = AudioCompletionLedgerKeyBinding.for_candidate(candidate)
    entry = make_entry_envelope(candidate, key=key)

    class ShiftingKey(AudioCompletionLedgerKeyBinding):
        pass

    class ShiftingExpectation(AudioCompletionLedgerCasExpectation):
        pass

    forged_key = object.__new__(ShiftingKey)
    object.__setattr__(forged_key, "_data", key._data)
    forged_expectation = object.__new__(ShiftingExpectation)
    object.__setattr__(forged_expectation, "_data", cas_for_chain((), key)._data)
    for operation in (
        lambda: make_entry_envelope(candidate, key=forged_key),
        lambda: validate_full_chain([entry], forged_key),
        lambda: cas_for_chain([entry], forged_key),
        lambda: observe_latest([entry], forged_key),
        lambda: evaluate_append([], candidate, forged_expectation),
    ):
        with pytest.raises(TypeError):
            operation()


def test_schema_closes_decision_reason_and_public_observation_state_matrix():
    candidate = _candidate()
    key = AudioCompletionLedgerKeyBinding.for_candidate(candidate)
    evaluation = evaluate_append([], candidate, cas_for_chain((), key)).to_dict()
    evaluation["reason_codes"] = ["CAS_CONFLICT"]
    with pytest.raises(Exception):
        _assert_schema(evaluation)
    public = observe_latest((), key).to_public_dict()
    public["entry_count"] = 2
    public["latest_candidate_state"] = "SOURCE_REVALIDATION_REQUIRED"
    with pytest.raises(Exception):
        _assert_schema(public)


def test_sealed_types_pickle_alias_and_fake_previous_are_rejected():
    key, first_candidate, second_candidate, first, _ = _chain2()
    for kind in (AudioCompletionLedgerKeyBinding, AudioCompletionLedgerEntryEnvelope,
                 AudioCompletionLedgerCasExpectation, AudioCompletionAppendEvaluation,
                 AudioCompletionLatestObservation):
        with pytest.raises(TypeError): kind({})
    for record in (key, first, cas_for_chain((first,), key), observe_latest((first,), key)):
        with pytest.raises(TypeError): pickle.dumps(record)
        with pytest.raises(AttributeError): record._data = {}
        exported = record.to_dict(); exported["task_owner"] = "FORGED"
        assert record.to_dict()["task_owner"] == "TASK-041"
    with pytest.raises(TypeError): make_entry_envelope(second_candidate, key=key, previous_entry=object())
    assert first_candidate.to_dict()["canonical_state"] == "NOT_MINTED"


def test_public_projection_is_reparsed_redacted_and_non_authoritative():
    key, _, _, first, second = _chain2()
    observation = observe_latest((first, second), key)
    public = observation.to_public_dict()
    _assert_schema(public)
    serialized = json.dumps(public, sort_keys=True)
    for private in ("project-1", "timeline-1", "audio-completion-1", "ledger_key_sha256",
                    "latest_entry_sha256", "latest_candidate_sha256", "chain_sha256"):
        assert private not in serialized
    assert public["canonical_state"] == "NOT_MINTED"
    assert public["observation_state"] == "PROVIDED_CHAIN_DIAGNOSTIC"
    assert public["provided_chain_semantically_validated"] is False
    assert public["consumer_revalidation_required"] is True
    assert public["canonical_latest_authorized"] is False
    assert public["canonical_pass_authorized"] is False
    forged = object.__new__(AudioCompletionLatestObservation)
    object.__setattr__(forged, "_data", {"record_type": "forged"})
    with pytest.raises(ValueError): forged.to_public_dict()


def test_schema_mirror_static_no_io_and_no_task036_or_owner_reader_surface():
    assert SCHEMA_PATH.read_bytes() == MIRROR_PATH.read_bytes()
    Draft202012Validator.check_schema(SCHEMA)
    source_path = ROOT / "src" / "ai_video_production" / "audio_completion_ledger_contract.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imports |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not any(name.startswith(("os", "pathlib", "tempfile", "socket", "http", "subprocess",
                                    "requests", "urllib", "torch", "soundfile")) for name in imports)
    assert not any("final_review_gate" in name for name in imports)
    for forbidden in ("open(", "write_text", "write_bytes", "save(", "get_latest(",
                      "socket.", "subprocess.", "requests.", "urlopen("):
        assert forbidden not in source
