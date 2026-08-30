from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
import pickle

from jsonschema import Draft202012Validator, RefResolver
import pytest

import ai_video_production.audio_completion_ledger_store as store
from ai_video_production.audio_completion_ledger_contract import (
    AudioCompletionLedgerKeyBinding, cas_for_chain, make_entry_envelope,
)
from ai_video_production.audio_completion_receipt import (
    AudioCompletionAdmissionCandidate, AudioCompletionRole, EvidenceBinding,
    EvidenceState, FinishingRequirement, RoleDeclaration, RolePresence,
    RoleRequirement, ScopeBinding, make_closed_receipt_ref,
)
from ai_video_production.audio_completion_ledger_windows_port import (
    DirectoryEntry, HandleIdentity, NativePortError,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "audio-completion-ledger-store-receipt.schema.json"
MIRROR_PATH = ROOT / "src" / "ai_video_production" / "schema_resources" / "audio-completion-ledger-store-receipt.schema.json"
R1A_SCHEMA_PATH = ROOT / "schemas" / "audio-completion-ledger-contract.schema.json"
R0_SCHEMA_PATH = ROOT / "schemas" / "audio-completion-receipt.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
R1A_SCHEMA = json.loads(R1A_SCHEMA_PATH.read_text(encoding="utf-8"))
R0_SCHEMA = json.loads(R0_SCHEMA_PATH.read_text(encoding="utf-8"))
RESOLVER = RefResolver.from_schema(SCHEMA, store={R1A_SCHEMA["$id"]: R1A_SCHEMA, R0_SCHEMA["$id"]: R0_SCHEMA})
VALIDATOR = Draft202012Validator(SCHEMA, resolver=RESOLVER)
D = "sha256:" + "a" * 64


def _ref(kind: str):
    return make_closed_receipt_ref(kind, record_id=f"{kind}-1", record_sha256=D)


def _candidate(*, previous=None, evaluated_at="2026-08-21T01:00:00Z"):
    scope = ScopeBinding.create(
        project_id="project-1", project_revision=3, project_manifest_sha256="sha256:" + "1" * 64,
        timeline_id="timeline-1", timeline_revision=7, timeline_sha256="sha256:" + "2" * 64,
        workspace_snapshot_sha256="sha256:" + "3" * 64,
        source_truth_receipt_id="audio-source-1", source_truth_receipt_sha256="sha256:" + "4" * 64,
        role_policy_receipt_id="audio-policy-1", role_policy_receipt_sha256="sha256:" + "5" * 64,
    )
    item = EvidenceBinding.create(
        item_id="source-main", role=AudioCompletionRole.SOURCE,
        item_source_sha256="sha256:" + "6" * 64,
        review_receipt=_ref("review_receipt"), external_review_receipt=_ref("external_review_receipt"),
        placement_receipt=_ref("placement_receipt"), narration_publication_receipt=None,
        finishing_receipt=None, evidence_state=EvidenceState.PASS,
        evidence_current_at_evaluation=True, evidence_invalidation_epoch=0,
    )
    roles = tuple(RoleDeclaration(
        role,
        RoleRequirement.REQUIRED if role is AudioCompletionRole.SOURCE else RoleRequirement.OPTIONAL,
        RolePresence.PRESENT if role is AudioCompletionRole.SOURCE else RolePresence.ABSENT_CONFIRMED,
        FinishingRequirement.NOT_APPLICABLE,
        ("source-main",) if role is AudioCompletionRole.SOURCE else (),
        (item.to_dict()["evidence_binding_sha256"],) if role is AudioCompletionRole.SOURCE else (),
    ) for role in AudioCompletionRole)
    return AudioCompletionAdmissionCandidate.create(
        receipt_id="audio-completion-1", scope=scope, role_declarations=roles,
        evidence_bindings=(item,), evaluated_at=evaluated_at, previous=previous,
    )


class FakePort:
    def __init__(self, *, files=None, fail=None, shared_lock=None):
        self.files = dict(files or {})
        self.file_ids = {name: (index + 100).to_bytes(16, "little") for index, name in enumerate(self.files)}
        self.fail = dict(fail or {})
        self.shared_lock = shared_lock if shared_lock is not None else {"held": False}
        self.handles = {}; self.next_handle = 10; self.trace = []; self.locked = False

    def _fault(self, point):
        value = self.fail.get(point)
        if value:
            if isinstance(value, Exception):
                raise value
            raise NativePortError(value)

    def _new(self, name):
        handle = self.next_handle; self.next_handle += 1; self.handles[handle] = name
        return handle

    def open_volume_root(self):
        self.trace.append(("open_volume_root",)); self._fault("open_volume_root")
        return self._new("C:\\")

    def open_relative(self, parent, name, *, kind, create=False):
        self.trace.append(("open_relative", parent, name, kind, create)); self._fault(f"open:{name}")
        assert parent in self.handles
        if kind == "directory":
            return self._new(name)
        if name == ".global.lock":
            return self._new(name)
        if create:
            if name in self.files:
                raise NativePortError("CREATE_COLLISION")
            self.files[name] = b""
            self.file_ids[name] = (len(self.file_ids) + 1000).to_bytes(16, "little")
            return self._new(name)
        if name not in self.files:
            raise NativePortError("NOT_FOUND")
        return self._new(name)

    def identity(self, handle, *, security_role="private_child"):
        self.trace.append(("identity", handle, security_role)); self._fault(f"identity:{self.handles[handle]}")
        name = self.handles[handle]
        payload = self.files.get(name, b"")
        paths = {"C:\\": "C:\\", "ProgramData": "C:\\ProgramData",
            "BAISOUND": "C:\\ProgramData\\BAISOUND",
            "BAI Video Production": "C:\\ProgramData\\BAISOUND\\BAI Video Production",
            "audio-completion-ledgers": "C:\\ProgramData\\BAISOUND\\BAI Video Production\\audio-completion-ledgers"}
        final_path = paths.get(name, paths["audio-completion-ledgers"] + "\\" + name)
        file_id = self.file_ids.get(name, name.encode("utf-8")[:16].ljust(16, b"0"))
        return HandleIdentity(77, file_id, final_path,
            0x10 if name in paths else 0,
            1, len(payload), b"verified-security")

    def lock(self, handle):
        self.trace.append(("lock", handle)); self._fault("lock")
        if self.shared_lock["held"]:
            raise NativePortError("LOCK_BUSY")
        self.shared_lock["held"] = True; self.locked = True

    def unlock(self, handle):
        self.trace.append(("unlock", handle)); self._fault("unlock")
        self.shared_lock["held"] = False; self.locked = False

    def enumerate_relative(self, root, *, max_entries):
        self.trace.append(("enumerate", root, max_entries)); self._fault("enumerate")
        assert self.locked
        lock_id = ".global.lock".encode("utf-8")[:16].ljust(16, b"0")
        entries = [DirectoryEntry(".global.lock", lock_id, 0, 0)]
        for name, payload in self.files.items():
            entries.append(DirectoryEntry(name, self.file_ids[name], 0, len(payload)))
        return tuple(entries)

    def read_all(self, handle, *, maximum):
        self.trace.append(("read", handle, maximum)); self._fault(f"read:{self.handles[handle]}")
        payload = self.files[self.handles[handle]]
        if len(payload) > maximum:
            raise NativePortError("FILE_SIZE_BOUND_EXCEEDED")
        return payload

    def write_all(self, handle, payload):
        self.trace.append(("write", handle, len(payload))); self._fault("write")
        self.files[self.handles[handle]] = bytes(payload)

    def flush_file(self, handle):
        self.trace.append(("flush", handle)); self._fault("flush")

    def rewind(self, handle):
        self.trace.append(("rewind", handle)); self._fault("rewind")

    def rename_no_replace(self, handle, root, final_name):
        self.trace.append(("rename", handle, root, final_name)); self._fault("rename")
        if final_name in self.files:
            raise NativePortError("RENAME_COLLISION")
        old = self.handles[handle]; self.files[final_name] = self.files.pop(old); self.handles[handle] = final_name
        self.file_ids[final_name] = self.file_ids.pop(old)

    def close(self, handle):
        self.trace.append(("close", handle)); self._fault(f"close:{self.handles[handle]}")


@pytest.fixture
def prepared(monkeypatch):
    candidate = _candidate(); key = AudioCompletionLedgerKeyBinding.for_candidate(candidate)
    item = store.prepare_append(key=key, candidate=candidate, expectation=cas_for_chain((), key))
    port = FakePort(); monkeypatch.setattr(store, "_PORT_FACTORY", lambda: port)
    return candidate, key, item, port


def _assert_schema(value):
    VALIDATOR.validate(value)


def test_prepare_returns_token_before_any_port_or_mutation_and_is_sealed(monkeypatch):
    calls = []
    monkeypatch.setattr(store, "_PORT_FACTORY", lambda: calls.append(True))
    candidate = _candidate(); key = AudioCompletionLedgerKeyBinding.for_candidate(candidate)
    prepared = store.prepare_append(key=key, candidate=candidate, expectation=cas_for_chain((), key))
    assert calls == [] and len(prepared.recovery_token()) == 32
    assert "sealed" in repr(prepared) and prepared.recovery_token().hex() not in repr(prepared)
    with pytest.raises(TypeError): pickle.dumps(prepared)
    with pytest.raises(AttributeError): prepared._token = b"x" * 32
    with pytest.raises(TypeError):
        store.PreparedAudioCompletionAppend(key=key, candidate=candidate,
            expectation=cas_for_chain((), key), token=b"x" * 32, _seal=store._TOKEN)
    forged = object.__new__(store.PreparedAudioCompletionAppend)
    for field, value in (("_key", key), ("_candidate", candidate),
                         ("_expectation", cas_for_chain((), key)), ("_token", b"x" * 32)):
        object.__setattr__(forged, field, value)
    with pytest.raises(TypeError): store.append_prepared(forged)


def test_prepare_uses_exact_csprng_size_and_rejects_bad_provider_output(monkeypatch):
    candidate = _candidate(); key = AudioCompletionLedgerKeyBinding.for_candidate(candidate)
    calls = []
    monkeypatch.setattr(store.secrets, "token_bytes", lambda size: calls.append(size) or b"z" * 32)
    prepared = store.prepare_append(key=key, candidate=candidate, expectation=cas_for_chain((), key))
    assert calls == [32] and prepared.recovery_token() == b"z" * 32
    monkeypatch.setattr(store.secrets, "token_bytes", lambda size: b"short")
    with pytest.raises(ValueError):
        store.prepare_append(key=key, candidate=candidate, expectation=cas_for_chain((), key))


def test_prepared_issuer_is_not_module_discoverable_or_caller_registerable(prepared):
    candidate, key, issued, _ = prepared
    assert not hasattr(store, "_BUILD_PREPARED")
    assert not hasattr(store, "_ISSUE_PREPARED")
    assert not hasattr(store, "_REGISTER_PREPARED")
    assert not hasattr(store, "_prepared_api_factory")
    assert store._RESOLVE_PREPARED(issued) is not None
    forged = object.__new__(store.PreparedAudioCompletionAppend)
    for field, value in (("_key", issued._key), ("_candidate", issued._candidate),
                         ("_expectation", issued._expectation), ("_token", b"n" * 32)):
        object.__setattr__(forged, field, value)
    assert store._RESOLVE_PREPARED(forged) is None
    with pytest.raises(TypeError):
        store.append_prepared(forged)
    with pytest.raises(TypeError):
        store.prepare_append(key=key, candidate=candidate,
            expectation=cas_for_chain((), key), token=b"n" * 32)


@pytest.mark.parametrize("field,bad", [
    ("_key", object()), ("_candidate", object()),
    ("_expectation", object()), ("_token", b"q" * 32),
])
def test_prepare_snapshot_rejects_slot_mutation_copy_and_forge(prepared, field, bad):
    _, _, item, _ = prepared
    object.__setattr__(item, field, bad)
    with pytest.raises(TypeError):
        store.append_prepared(item)
    with pytest.raises(TypeError):
        copy.copy(item)
    with pytest.raises(TypeError):
        copy.deepcopy(item)


def test_observe_empty_uses_one_lock_handle_only_enumeration_and_257_relative_probes(prepared, monkeypatch):
    _, key, _, port = prepared
    receipt = store.observe_ledger(key).to_dict()
    assert receipt["decision"] == "OBSERVED" and receipt["entry_count"] == 0
    assert receipt["filesystem_write_observed"] is False
    assert sum(call[0] == "lock" for call in port.trace) == 1
    probes = [call for call in port.trace if call[0] == "open_relative" and call[3] == "final"]
    assert len(probes) == 257 and probes[-1][2].endswith("-00000257.json")
    assert any(call[0] == "enumerate" for call in port.trace)
    roles = [call[2] for call in port.trace if call[0] == "identity"]
    assert "ancestor" in roles and "private_root" in roles and "private_child" in roles
    _assert_schema(receipt); _assert_schema(store.parse_store_receipt(receipt).to_public_dict())


def test_successful_append_writes_exact_lf_wrapper_and_keeps_all_authority_false(prepared):
    _, _, item, port = prepared
    receipt, recovery = store.append_prepared(item)
    value = receipt.to_dict()
    assert value["decision"] == "APPENDED"
    assert value["commit_state"] == "KNOWN_COMMITTED" and value["rename_state"] == "RETURNED_TRUE"
    assert value["resource_observation_state"] == "FINAL_REOPEN_VERIFIED"
    assert not any(value["authority_flags"].values())
    assert recovery is not None and recovery.to_dict()["receipt_is_capability"] is False
    finals = {name: payload for name, payload in port.files.items() if not name.startswith(".pending-")}
    assert len(finals) == 1
    payload = next(iter(finals.values()))
    assert payload.endswith(b"\n") and not payload.endswith(b"\r\n")
    wrapper, _ = store._parse_stored(payload)
    _assert_schema(wrapper); _assert_schema(value); _assert_schema(recovery.to_dict()); _assert_schema(receipt.to_public_dict())
    serialized = json.dumps(receipt.to_public_dict(), sort_keys=True)
    for private in ("ledger_key_sha256", "stored_entry_sha256", "expected_cas_sha256", "token_sha256", "root_identity_sha256", "file_id"):
        assert private not in serialized
    assert store.parse_store_public_projection(receipt.to_public_dict()).to_dict() == receipt.to_public_dict()
    assert value["receipt_is_authority"] is False
    assert value["consumer_revalidation_required"] is True
    assert value["post_return_state_guaranteed"] is False
    assert value["lock_release_confirmed"] is True and value["unreleased_handle_count"] == 0
    assert value["unreleased_native_allocation_count"] == 0
    assert value["filesystem_read_attempted"] and value["filesystem_read_observed"]
    assert value["filesystem_write_attempted"] and value["filesystem_write_observed"]


def test_append_target_state_is_separate_from_other_global_pending_and_roundtrips(prepared, monkeypatch):
    candidate, key, first, port = prepared
    port.fail["rename"] = "RENAME_FAILED"
    first_receipt, first_recovery = store.append_prepared(first)
    assert first_recovery is not None and first_receipt.to_dict()["pending_count"] == 1
    port.fail.clear()
    second = store.prepare_append(key=key, candidate=candidate, expectation=cas_for_chain((), key))
    receipt, _ = store.append_prepared(second)
    value = receipt.to_dict()
    assert value["decision"] == "APPENDED"
    assert value["namespace_state"] == "FINAL_ONLY" and value["pending_state"] == "NONE"
    assert value["global_pending_state"] == "RECOVERABLE" and value["pending_count"] == 1
    assert store.parse_store_receipt(value).to_dict() == value
    _assert_schema(value); _assert_schema(receipt.to_public_dict())


def test_append_revalidates_before_rename_and_after_rename_closes_original_before_reopen(prepared):
    _, _, item, port = prepared
    receipt, _ = store.append_prepared(item)
    assert receipt.to_dict()["decision"] == "APPENDED"
    assert sum(call[0] == "enumerate" for call in port.trace) >= 3
    rename_index = next(index for index, call in enumerate(port.trace) if call[0] == "rename")
    final_name = next(name for name in port.files if name.endswith("-00000001.json"))
    close_index = next(index for index, call in enumerate(port.trace[rename_index + 1:], rename_index + 1)
        if call[0] == "close" and port.handles[call[1]] == final_name)
    reopen_index = next(index for index, call in enumerate(port.trace[rename_index + 1:], rename_index + 1)
        if call[0] == "open_relative" and call[2] == final_name and call[3] == "final")
    assert close_index < reopen_index


def test_exact_latest_replay_and_two_writer_loser_reconcile_without_second_write(prepared, monkeypatch):
    candidate, key, item, port = prepared
    first, _ = store.append_prepared(item)
    assert first.to_dict()["decision"] == "APPENDED"
    writes_before = sum(call[0] == "write" for call in port.trace)
    replay = store.prepare_append(key=key, candidate=candidate, expectation=cas_for_chain((), key))
    replayed, recovery = store.append_prepared(replay)
    assert replayed.to_dict()["decision"] == "ALREADY_COMMITTED_RECONCILED"
    assert replayed.to_dict()["reason_codes"] == ["EXACT_LATEST_REPLAY_RECONCILED"]
    assert sum(call[0] == "write" for call in port.trace) == writes_before and recovery is None


def test_earlier_revision_replay_is_blocked_after_later_commit(prepared):
    first_candidate, key, first_prepared, port = prepared
    first_receipt, _ = store.append_prepared(first_prepared)
    assert first_receipt.to_dict()["decision"] == "APPENDED"
    first_wrapper, first_entry = store._parse_stored(next(iter(port.files.values())))
    second_candidate = _candidate(previous=first_candidate, evaluated_at="2026-08-21T01:00:01Z")
    second_prepared = store.prepare_append(key=key, candidate=second_candidate,
        expectation=cas_for_chain((first_entry,), key))
    second_receipt, _ = store.append_prepared(second_prepared)
    assert second_receipt.to_dict()["decision"] == "APPENDED"
    replay = store.prepare_append(key=key, candidate=first_candidate, expectation=cas_for_chain((), key))
    blocked, _ = store.append_prepared(replay)
    assert blocked.to_dict()["decision"] == "BLOCKED"
    assert blocked.to_dict()["reason_codes"] == ["TRANSITION_CONFLICT"]
    assert first_wrapper["entry_revision"] == 1


@pytest.mark.parametrize("point,reason", [("write", "WRITE_FAILED"), ("flush", "FILE_FLUSH_FAILED"), ("rewind", "FILE_REWIND_FAILED")])
def test_pre_rename_fault_preserves_pending_and_never_claims_commit(prepared, point, reason):
    _, _, item, port = prepared; port.fail[point] = reason
    receipt, recovery = store.append_prepared(item)
    value = receipt.to_dict()
    assert value["commit_state"] == "NOT_COMMITTED" and value["decision"] == "BLOCKED"
    assert any(name.startswith(".pending-") for name in port.files)
    assert recovery is None


def test_rename_false_preserves_recoverable_pending_and_returns_sealed_recovery(prepared):
    _, _, item, port = prepared; port.fail["rename"] = "RENAME_FAILED"
    receipt, recovery = store.append_prepared(item)
    value = receipt.to_dict()
    assert value["decision"] == "INCOMPLETE" and value["rename_state"] == "RETURNED_FALSE"
    assert value["namespace_state"] == "PENDING_ONLY" and recovery is not None
    assert any(name.startswith(".pending-") for name in port.files)


def test_rename_completion_unknown_is_reconciled_and_only_ambiguous_namespace_stays_unknown(prepared, monkeypatch):
    candidate, key, item, port = prepared
    port.fail["rename"] = NativePortError("RENAME_COMPLETION_UNOBSERVED", completion_unknown=True)
    receipt, recovery = store.append_prepared(item)
    value = receipt.to_dict()
    assert value["decision"] == "INCOMPLETE" and value["commit_state"] == "NOT_COMMITTED"
    assert value["rename_state"] == "SYSCALL_COMPLETION_UNKNOWN" and recovery is not None

    ambiguous_port = FakePort()
    def disappear_then_unknown(handle, root, final_name):
        del root, final_name
        pending_name = ambiguous_port.handles[handle]
        del ambiguous_port.files[pending_name]; del ambiguous_port.file_ids[pending_name]
        raise NativePortError("RENAME_COMPLETION_UNOBSERVED", completion_unknown=True)
    ambiguous_port.rename_no_replace = disappear_then_unknown
    monkeypatch.setattr(store, "_PORT_FACTORY", lambda: ambiguous_port)
    second = store.prepare_append(key=key, candidate=candidate, expectation=cas_for_chain((), key))
    ambiguous, _ = store.append_prepared(second)
    assert ambiguous.to_dict()["decision"] == "COMMIT_STATE_UNKNOWN"
    assert ambiguous.to_dict()["commit_state"] == "COMMIT_STATE_UNKNOWN"


def test_rename_completion_unknown_with_observed_final_retains_known_commit(prepared):
    _, _, item, port = prepared
    original = port.rename_no_replace
    def moved_then_unknown(handle, root, final_name):
        original(handle, root, final_name)
        raise NativePortError("RENAME_COMPLETION_UNOBSERVED", completion_unknown=True)
    port.rename_no_replace = moved_then_unknown
    value = store.append_prepared(item)[0].to_dict()
    assert value["decision"] == "INCOMPLETE" and value["commit_state"] == "KNOWN_COMMITTED"
    assert value["rename_state"] == "SYSCALL_COMPLETION_UNKNOWN"
    assert value["namespace_state"] == "FINAL_ONLY"
    assert value["filesystem_write_attempted"] and value["filesystem_write_observed"]
    _assert_schema(value)


def test_unknown_rename_byte_identical_replacement_fileid_is_never_known_commit(prepared):
    _, _, item, port = prepared
    original = port.rename_no_replace
    def replaced_then_unknown(handle, root, final_name):
        original(handle, root, final_name)
        port.file_ids[final_name] = (0xFEED).to_bytes(16, "little")
        raise NativePortError("RENAME_COMPLETION_UNOBSERVED", completion_unknown=True)
    port.rename_no_replace = replaced_then_unknown
    value = store.append_prepared(item)[0].to_dict()
    assert value["decision"] == "COMMIT_STATE_UNKNOWN"
    assert value["commit_state"] == "COMMIT_STATE_UNKNOWN"
    assert "UNKNOWN_RENAME_RETAINED_HANDLE_UNVERIFIED" in value["reason_codes"]
    _assert_schema(value); _assert_schema(store.parse_store_receipt(value).to_public_dict())


def test_close_failure_after_rename_keeps_known_commit_but_is_incomplete(prepared):
    _, _, item, port = prepared
    original_close = port.close
    def close(handle):
        if port.handles[handle].endswith(".json") and not port.handles[handle].startswith(".pending-"):
            raise NativePortError("HANDLE_CLOSE_FAILED")
        original_close(handle)
    port.close = close
    receipt, _ = store.append_prepared(item)
    value = receipt.to_dict()
    assert value["decision"] == "INCOMPLETE" and value["commit_state"] == "KNOWN_COMMITTED"
    assert value["resource_release_state"] == "INCOMPLETE"
    assert value["unreleased_handle_count"] > 0


def test_observe_close_failure_converts_success_decision_without_api_escape(prepared):
    _, key, _, port = prepared
    port.fail["close:.global.lock"] = "HANDLE_CLOSE_FAILED"
    value = store.observe_ledger(key).to_dict()
    assert value["decision"] == "INCOMPLETE"
    assert value["commit_state"] == "NOT_COMMITTED"
    assert value["resource_release_state"] == "INCOMPLETE"
    assert value["unreleased_handle_count"] > 0
    assert "RESOURCE_RELEASE_INCOMPLETE" in value["reason_codes"]
    _assert_schema(value)


def test_unlock_failure_is_release_fault_only_and_does_not_erase_commit(prepared):
    _, _, item, port = prepared; port.fail["unlock"] = "LOCK_RELEASE_FAILED"
    receipt, _ = store.append_prepared(item)
    value = receipt.to_dict()
    assert value["decision"] == "INCOMPLETE" and value["commit_state"] == "KNOWN_COMMITTED"
    assert value["lock_release_confirmed"] is False
    assert value["resource_release_state"] == "INCOMPLETE"


def test_port_native_allocation_fault_is_aggregated_without_changing_commit_truth(prepared):
    _, _, item, port = prepared
    port.resource_counts = lambda: (0, 1)
    value = store.append_prepared(item)[0].to_dict()
    assert value["decision"] == "INCOMPLETE" and value["commit_state"] == "KNOWN_COMMITTED"
    assert value["resource_release_state"] == "INCOMPLETE"
    assert value["unreleased_handle_count"] == 0
    assert value["unreleased_native_allocation_count"] == 1
    assert "RESOURCE_RELEASE_INCOMPLETE" in value["reason_codes"]
    _assert_schema(value); _assert_schema(store.parse_store_receipt(value).to_public_dict())


def test_post_rename_reopen_fault_keeps_known_commit_and_reports_incomplete(prepared):
    _, _, item, port = prepared
    original_rename = port.rename_no_replace
    def rename(handle, root, final_name):
        original_rename(handle, root, final_name)
        port.fail[f"open:{final_name}"] = "FINAL_REOPEN_FAILED"
    port.rename_no_replace = rename
    receipt, recovery = store.append_prepared(item)
    value = receipt.to_dict()
    assert recovery is not None
    assert value["commit_state"] == "KNOWN_COMMITTED" and value["decision"] == "INCOMPLETE"
    assert value["rename_state"] == "RETURNED_TRUE"
    assert value["resource_observation_state"] == "INCOMPLETE"


def test_resume_post_rename_fault_never_escapes_and_clears_unverified_aggregate(prepared):
    key, token, recovery, port = _make_pending(prepared)
    original_rename = port.rename_no_replace
    def rename(handle, root, final_name):
        original_rename(handle, root, final_name)
        port.fail[f"open:{final_name}"] = "FINAL_REOPEN_FAILED"
    port.rename_no_replace = rename
    value = store.resume_pending(key=key, recovery=recovery, token=token).to_dict()
    assert value["decision"] == "INCOMPLETE" and value["commit_state"] == "KNOWN_COMMITTED"
    assert value["rename_state"] == "RETURNED_TRUE"
    assert value["namespace_state"] == "NOT_OBSERVED"
    assert value["chain_state"] == "NOT_OBSERVED"
    assert value["entry_count"] == value["pending_count"] == 0
    assert "final_count" not in value and "entry_revision" not in value
    assert value["stored_entry_sha256"] is None and value["expected_cas_sha256"] is None
    assert value["filesystem_write_attempted"] and value["filesystem_write_observed"]
    assert store.parse_store_receipt(value).to_dict() == value
    _assert_schema(value)


def test_wrong_cas_blocks_before_create(prepared):
    candidate, key, _, port = prepared
    wrong = copy.deepcopy(cas_for_chain((), key).to_dict())
    wrong["expected_entry_count"] = 1
    with pytest.raises(ValueError):
        store.AudioCompletionLedgerRecoveryReceipt.from_dict({})
    # A CAS for a distinct empty key is rejected by prepare, before port construction.
    other = _candidate().to_dict(); other["receipt_id"] = "other"
    with pytest.raises(ValueError):
        store.prepare_append(key=key, candidate=candidate,
            expectation=store.AudioCompletionLedgerCasExpectation.from_dict(wrong))
    assert not any(call[0] == "write" for call in port.trace)


def test_create_new_collision_from_noncooperator_never_overwrites(prepared):
    _, _, item, port = prepared
    original_open = port.open_relative
    foreign = b"foreign-preexisting-bytes"
    def race(parent, name, *, kind, create=False):
        if create:
            port.files[name] = foreign; port.file_ids[name] = (4444).to_bytes(16, "little")
        return original_open(parent, name, kind=kind, create=create)
    port.open_relative = race
    receipt, recovery = store.append_prepared(item)
    assert receipt.to_dict()["decision"] == "BLOCKED" and recovery is None
    assert receipt.to_dict()["filesystem_write_attempted"] is True
    assert receipt.to_dict()["filesystem_write_observed"] is False
    assert foreign in port.files.values() and not any(call[0] == "write" for call in port.trace)


def test_unknown_case_collision_gap_and_revision_257_fail_closed(prepared):
    _, key, _, port = prepared
    for name, reason in (("unknown.txt", "UNKNOWN_NAMESPACE_ENTRY"), (".GLOBAL.LOCK", "CASE_COLLISION")):
        port.files = {name: b"x"}
        port.file_ids = {name: (321).to_bytes(16, "little")}
        value = store.observe_ledger(key).to_dict()
        assert value["decision"] == "BLOCKED" and value["reason_codes"] == [reason]


def test_recovery_token_mismatch_direct_init_pickle_and_public_forge_are_rejected(prepared):
    _, key, item, port = prepared; port.fail["rename"] = "RENAME_FAILED"
    receipt, recovery = store.append_prepared(item)
    assert recovery is not None
    with pytest.raises(ValueError): store.inspect_pending(key=key, recovery=recovery, token=b"x" * 32)
    with pytest.raises(TypeError): store.AudioCompletionLedgerStoreReceipt({})
    with pytest.raises(TypeError): pickle.dumps(recovery)
    forged = object.__new__(store.AudioCompletionLedgerStoreReceipt)
    object.__setattr__(forged, "_data", {"secret_path": "C:\\private"})
    with pytest.raises(ValueError): forged.to_public_dict()
    assert receipt.to_dict()["decision"] == "INCOMPLETE"


def _make_pending(prepared):
    _, key, item, port = prepared
    port.fail["rename"] = "RENAME_FAILED"
    receipt, recovery = store.append_prepared(item)
    port.fail.clear()
    assert receipt.to_dict()["namespace_state"] == "PENDING_ONLY" and recovery is not None
    return key, item.recovery_token(), recovery, port


def test_existing_exact_pending_reconstructs_recovery_receipt_without_rewrite(prepared, monkeypatch):
    key, token, recovery, port = _make_pending(prepared)
    candidate = _candidate()
    monkeypatch.setattr(store.secrets, "token_bytes", lambda size: token if size == 32 else b"")
    replay_prepared = store.prepare_append(
        key=key, candidate=candidate, expectation=cas_for_chain((), key))
    writes_before = sum(call[0] == "write" for call in port.trace)
    receipt, rebuilt = store.append_prepared(replay_prepared)
    assert receipt.to_dict()["decision"] == "RECOVERY_AVAILABLE"
    assert rebuilt is not None and rebuilt.to_dict() == recovery.to_dict()
    assert sum(call[0] == "write" for call in port.trace) == writes_before


def test_partial_pending_is_bounded_recovery_observation_not_global_observe_brick(prepared):
    _, key, item, port = prepared
    name = ".pending-" + "a" * 64 + ".json"
    port.files[name] = b"{partial"; port.file_ids[name] = (8080).to_bytes(16, "little")
    observed = store.observe_ledger(key).to_dict()
    assert observed["decision"] == "OBSERVED" and observed["pending_state"] == "NONE"
    assert observed["namespace_state"] == "NEITHER"
    assert observed["global_pending_state"] == "CORRUPT"
    assert observed["reason_codes"] == ["POINT_IN_TIME_NAMESPACE_OBSERVED"]
    blocked, _ = store.append_prepared(item)
    assert blocked.to_dict()["reason_codes"] == ["CORRUPT_PENDING_REQUIRES_RECOVERY"]


def test_zero_byte_pending_is_corrupt_not_verified_or_recoverable(prepared):
    _, key, _, port = prepared
    name = ".pending-" + "c" * 64 + ".json"
    port.files[name] = b""; port.file_ids[name] = (8082).to_bytes(16, "little")
    observed = store.observe_ledger(key)
    value = observed.to_dict()
    assert value["decision"] == "OBSERVED"
    assert value["pending_count"] == 1 and value["pending_disk_bytes"] == 0
    assert value["global_pending_state"] == "CORRUPT"
    assert value["pending_state"] == "NONE"
    assert value["content_state"] == "NOT_OBSERVED"
    assert store.parse_store_receipt(value).to_dict() == value
    _assert_schema(value); _assert_schema(observed.to_public_dict())


def test_oversized_pending_is_identity_checked_without_payload_read_and_observable(prepared):
    _, key, item, port = prepared
    name = ".pending-" + "b" * 64 + ".json"
    port.files[name] = b"x" * (store._MAX_STORED_BYTES + 1)
    port.file_ids[name] = (8081).to_bytes(16, "little")
    observed = store.observe_ledger(key).to_dict()
    assert observed["decision"] == "OBSERVED"
    assert observed["pending_state"] == "NONE"
    assert observed["global_pending_state"] == "CORRUPT"
    assert observed["reason_codes"] == ["POINT_IN_TIME_NAMESPACE_OBSERVED"]
    pending_handles = {handle for handle, opened_name in port.handles.items()
                       if opened_name == name}
    assert pending_handles
    assert not any(call[0] == "read" and call[1] in pending_handles
                   for call in port.trace)
    blocked, _ = store.append_prepared(item)
    assert blocked.to_dict()["reason_codes"] == [
        "CORRUPT_PENDING_REQUIRES_RECOVERY"]


@pytest.mark.parametrize("field", ["root_identity_sha256", "expected_cas_sha256"])
def test_stored_prefix_root_and_cas_tamper_are_rejected(prepared, field):
    _, key, item, port = prepared
    assert store.append_prepared(item)[0].to_dict()["decision"] == "APPENDED"
    final_name, payload = next(iter(port.files.items()))
    wrapper, _ = store._parse_stored(payload)
    wrapper[field] = "sha256:" + "f" * 64
    wrapper["stored_entry_sha256"] = store._digest_without(wrapper, "stored_entry_sha256", store._STORED_DOMAIN)
    port.files[final_name] = store.canonical_json_bytes(wrapper) + b"\n"
    blocked = store.observe_ledger(key).to_dict()
    assert blocked["decision"] == "BLOCKED" and blocked["reason_codes"] == ["STORED_PREFIX_BINDING_MISMATCH"]


def test_pending_only_inspect_and_explicit_resume_revalidate_token_fileid_cas_and_commit(prepared):
    key, token, recovery, port = _make_pending(prepared)
    inspected = store.inspect_pending(key=key, recovery=recovery, token=token).to_dict()
    assert inspected["decision"] == "RECOVERY_AVAILABLE" and inspected["pending_state"] == "RECOVERABLE"
    resumed = store.resume_pending(key=key, recovery=recovery, token=token).to_dict()
    assert resumed["decision"] == "APPENDED" and resumed["commit_state"] == "KNOWN_COMMITTED"
    assert resumed["filesystem_write_observed"] is True
    assert not any(name.startswith(".pending-") for name in port.files)
    final = store.inspect_pending(key=key, recovery=recovery, token=token).to_dict()
    assert final["decision"] == "ALREADY_COMMITTED_RECONCILED" and final["namespace_state"] == "FINAL_ONLY"


def test_final_only_byte_identical_replacement_breaks_rename_fileid_continuity(prepared):
    key, token, recovery, port = _make_pending(prepared)
    assert store.resume_pending(key=key, recovery=recovery, token=token).to_dict()["decision"] == "APPENDED"
    body = recovery.to_dict()
    final_name = store._canonical_final_name(body["ledger_key_sha256"], body["entry_revision"])
    port.file_ids[final_name] = (0xDEAD).to_bytes(16, "little")
    blocked = store.inspect_pending(key=key, recovery=recovery, token=token).to_dict()
    assert blocked["decision"] == "BLOCKED"
    assert blocked["reason_codes"] == ["RENAME_FILE_ID_CONTINUITY_FAILED"]
    _assert_schema(blocked); _assert_schema(store.parse_store_receipt(blocked).to_public_dict())


def test_recovery_receipt_binds_one_fileid_across_pending_and_final_names(prepared):
    _, _, recovery, _ = _make_pending(prepared)
    body = recovery.to_dict()
    assert body["pending_file_identity_sha256"] == body["rename_continuity_file_identity_sha256"]
    body["rename_continuity_file_identity_sha256"] = "sha256:" + "f" * 64
    body["recovery_receipt_sha256"] = store._digest_without(
        body, "recovery_receipt_sha256", store._RECOVERY_DOMAIN)
    with pytest.raises(ValueError, match="rename-continuity"):
        store.parse_recovery_receipt(body)


def test_resume_target_final_is_separate_from_another_global_pending(prepared):
    key, token, recovery, port = _make_pending(prepared)
    target_name = store._pending_name(recovery.to_dict()["token_sha256"])
    wrapper, _ = store._parse_stored(port.files[target_name])
    wrapper["token_sha256"] = "sha256:" + "e" * 64
    wrapper["stored_entry_sha256"] = store._digest_without(
        wrapper, "stored_entry_sha256", store._STORED_DOMAIN)
    other_name = store._pending_name(wrapper["token_sha256"])
    port.files[other_name] = store.canonical_json_bytes(wrapper) + b"\n"
    port.file_ids[other_name] = (8181).to_bytes(16, "little")
    value = store.resume_pending(key=key, recovery=recovery, token=token).to_dict()
    assert value["decision"] == "APPENDED" and value["namespace_state"] == "FINAL_ONLY"
    assert value["pending_state"] == "NONE"
    assert value["global_pending_state"] == "RECOVERABLE" and value["pending_count"] == 1
    _assert_schema(value); _assert_schema(store.parse_store_receipt(value).to_public_dict())


def test_recovery_both_identical_neither_and_different_final_are_distinct(prepared):
    key, token, recovery, port = _make_pending(prepared)
    body = recovery.to_dict(); pending_name = store._pending_name(body["token_sha256"])
    final_name = store._canonical_final_name(body["ledger_key_sha256"], body["entry_revision"])
    pending_payload = port.files[pending_name]
    port.files[final_name] = pending_payload; port.file_ids[final_name] = (9000).to_bytes(16, "little")
    both = store.inspect_pending(key=key, recovery=recovery, token=token).to_dict()
    assert both["decision"] == "BLOCKED"
    assert both["reason_codes"] == ["RENAME_FILE_ID_CONTINUITY_FAILED"]
    del port.files[final_name]; del port.file_ids[final_name]
    del port.files[pending_name]; del port.file_ids[pending_name]
    neither = store.inspect_pending(key=key, recovery=recovery, token=token).to_dict()
    assert neither["decision"] == "NOT_COMMITTED" and neither["namespace_state"] == "NEITHER"

    # Recreate a valid but differently token-bound final for the same R1A entry.
    wrapper, entry = store._parse_stored(pending_payload)
    different, different_payload = store._stored_payload(entry=entry,
        expectation_sha=wrapper["expected_cas_sha256"], token_sha="sha256:" + "f" * 64,
        root_sha=wrapper["root_identity_sha256"])
    assert different["stored_entry_sha256"] != wrapper["stored_entry_sha256"]
    port.files[pending_name] = pending_payload; port.file_ids[pending_name] = (1000).to_bytes(16, "little")
    # Keep the recovery-bound pending FileId stable for this reconciliation.
    recovery_body = recovery.to_dict()
    recovery_body["pending_file_identity_sha256"] = store.sha256_bytes(store._FILE_ID_DOMAIN + port.file_ids[pending_name])
    recovery_body["rename_continuity_file_identity_sha256"] = recovery_body["pending_file_identity_sha256"]
    recovery_body["recovery_receipt_sha256"] = store._digest_without(recovery_body, "recovery_receipt_sha256", store._RECOVERY_DOMAIN)
    rebound = store.parse_recovery_receipt(recovery_body)
    port.files[final_name] = different_payload; port.file_ids[final_name] = (9001).to_bytes(16, "little")
    conflict = store.inspect_pending(key=key, recovery=rebound, token=token).to_dict()
    assert conflict["decision"] == "BLOCKED" and conflict["namespace_state"] == "DIFFERENT_FINAL"


def test_resume_final_plus_pending_is_never_reported_as_already_reconciled(prepared):
    key, token, recovery, port = _make_pending(prepared)
    body = recovery.to_dict(); pending_name = store._pending_name(body["token_sha256"])
    final_name = store._canonical_final_name(body["ledger_key_sha256"], body["entry_revision"])
    port.files[final_name] = port.files[pending_name]
    port.file_ids[final_name] = (9100).to_bytes(16, "little")
    both = store.resume_pending(key=key, recovery=recovery, token=token).to_dict()
    assert both["decision"] == "BLOCKED"
    assert both["reason_codes"] == ["RENAME_FILE_ID_CONTINUITY_FAILED"]

    port.files[pending_name] = b"different-pending"
    inspected = store.inspect_pending(key=key, recovery=recovery, token=token).to_dict()
    assert inspected["decision"] == "BLOCKED"
    assert inspected["reason_codes"] == ["RENAME_FILE_ID_CONTINUITY_FAILED"]
    conflict = store.resume_pending(key=key, recovery=recovery, token=token).to_dict()
    assert conflict["decision"] == "BLOCKED"
    assert conflict["reason_codes"] == ["RENAME_FILE_ID_CONTINUITY_FAILED"]


def test_recovery_fileid_change_and_stale_cas_fail_closed(prepared):
    key, token, recovery, port = _make_pending(prepared)
    pending_name = store._pending_name(recovery.to_dict()["token_sha256"])
    port.file_ids[pending_name] = (7777).to_bytes(16, "little")
    changed = store.inspect_pending(key=key, recovery=recovery, token=token).to_dict()
    assert changed["decision"] == "BLOCKED" and "PENDING_FILE_ID_CHANGED" in changed["reason_codes"]


def test_final_scan_close_fault_is_bounded_and_never_escapes(prepared):
    _, key, item, port = prepared
    assert store.append_prepared(item)[0].to_dict()["decision"] == "APPENDED"
    final_name = next(name for name in port.files if not name.startswith(".pending-"))
    port.fail[f"close:{final_name}"] = "CLOSE_FAILED"
    value = store.observe_ledger(key).to_dict()
    assert value["decision"] == "BLOCKED"
    assert value["reason_codes"] == ["FINAL_SCAN_HANDLE_CLOSE_FAILED", "RESOURCE_RELEASE_INCOMPLETE"]
    assert 1 <= value["unreleased_handle_count"] <= store._MAX_RETAINED_HANDLES == 32
    _assert_schema(value); _assert_schema(store.parse_store_receipt(value).to_public_dict())


def test_lock_busy_is_immediate_and_performs_no_namespace_read_or_write(prepared):
    _, key, _, port = prepared
    port.shared_lock["held"] = True
    value = store.observe_ledger(key).to_dict()
    assert value["decision"] == "BLOCKED" and value["reason_codes"] == ["LOCK_BUSY"]
    assert value["filesystem_read_observed"] is True and value["filesystem_write_observed"] is False
    assert not any(call[0] == "enumerate" for call in port.trace)


def test_unexpected_native_fault_is_normalized_without_exception_text(prepared):
    _, key, _, port = prepared; port.fail["enumerate"] = RuntimeError("private path C:\\secret")
    value = store.observe_ledger(key).to_dict()
    assert value["decision"] == "BLOCKED" and value["reason_codes"] == ["UNEXPECTED_NATIVE_FAULT"]
    assert value["lock_acquired"] is True
    assert value["filesystem_read_attempted"] is True and value["filesystem_read_observed"] is True
    assert value["chain_state"] == "NOT_OBSERVED"
    assert "secret" not in json.dumps(value).lower()


def test_two_process_ports_share_one_machine_lock_coordinate_and_reconcile_after_release(prepared, monkeypatch):
    _, key, _, _ = prepared
    shared = {"held": False}; first = FakePort(shared_lock=shared); second = FakePort(shared_lock=shared)
    held = store._LockedSession(first, []); held.open()
    monkeypatch.setattr(store, "_PORT_FACTORY", lambda: second)
    busy = store.observe_ledger(key).to_dict()
    assert busy["reason_codes"] == ["LOCK_BUSY"]
    held.close()
    observed = store.observe_ledger(key).to_dict()
    assert observed["decision"] == "OBSERVED" and any(call[0] == "enumerate" for call in second.trace)


def test_schema_mirror_digest_tamper_conditionals_and_static_effect_boundary(prepared):
    assert SCHEMA_PATH.read_bytes() == MIRROR_PATH.read_bytes()
    Draft202012Validator.check_schema(SCHEMA)
    _, _, item, _ = prepared
    receipt, _ = store.append_prepared(item)
    tampered = receipt.to_dict(); tampered["power_loss_durability_claimed"] = True
    with pytest.raises(Exception): _assert_schema(tampered)
    tampered = receipt.to_dict(); tampered["commit_state"] = "COMMIT_STATE_UNKNOWN"
    with pytest.raises(ValueError): store.parse_store_receipt(tampered)
    for field, bad in (("receipt_is_authority", True), ("consumer_revalidation_required", False),
                       ("post_return_state_guaranteed", True)):
        tampered = receipt.to_dict(); tampered[field] = bad
        with pytest.raises(Exception): _assert_schema(tampered)
        with pytest.raises(ValueError): store.parse_store_receipt(tampered)
    source = (ROOT / "src" / "ai_video_production" / "audio_completion_ledger_store.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imports |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not any(name.startswith(("socket", "subprocess", "requests", "urllib", "torch", "soundfile")) for name in imports)
    for forbidden in ("mkdir(", "unlink(", "os.remove(", "os.replace(", "rmtree(", "import final_review_gate", "TASK036"):
        assert forbidden not in source


def _generated_decision_receipts(monkeypatch):
    candidate = _candidate(); key = AudioCompletionLedgerKeyBinding.for_candidate(candidate)
    expectation = cas_for_chain((), key)
    receipts = []

    empty = FakePort(); monkeypatch.setattr(store, "_PORT_FACTORY", lambda: empty)
    receipts.append(store.observe_ledger(key))

    committed = FakePort(); monkeypatch.setattr(store, "_PORT_FACTORY", lambda: committed)
    receipts.append(store.append_prepared(store.prepare_append(
        key=key, candidate=candidate, expectation=expectation))[0])
    receipts.append(store.append_prepared(store.prepare_append(
        key=key, candidate=candidate, expectation=expectation))[0])

    pending = FakePort(fail={"rename": "RENAME_FAILED"})
    monkeypatch.setattr(store, "_PORT_FACTORY", lambda: pending)
    pending_capability = store.prepare_append(
        key=key, candidate=candidate, expectation=expectation)
    incomplete, recovery = store.append_prepared(pending_capability)
    receipts.append(incomplete); assert recovery is not None
    pending.fail.clear()
    token = pending_capability.recovery_token()
    pending_name = store._pending_name(recovery.to_dict()["token_sha256"])
    receipts.append(store.inspect_pending(key=key, recovery=recovery, token=token))
    del pending.files[pending_name]; del pending.file_ids[pending_name]
    receipts.append(store.inspect_pending(key=key, recovery=recovery, token=token))

    busy = FakePort(shared_lock={"held": True})
    monkeypatch.setattr(store, "_PORT_FACTORY", lambda: busy)
    receipts.append(store.observe_ledger(key))

    unknown = FakePort()
    def disappear_then_unknown(handle, root, final_name):
        del root, final_name
        name = unknown.handles[handle]
        del unknown.files[name]; del unknown.file_ids[name]
        raise NativePortError("RENAME_COMPLETION_UNOBSERVED", completion_unknown=True)
    unknown.rename_no_replace = disappear_then_unknown
    monkeypatch.setattr(store, "_PORT_FACTORY", lambda: unknown)
    receipts.append(store.append_prepared(store.prepare_append(
        key=key, candidate=candidate, expectation=expectation))[0])

    return receipts


def test_all_generated_decision_variants_roundtrip_private_public_and_schema(monkeypatch):
    receipts = _generated_decision_receipts(monkeypatch)

    assert {receipt.to_dict()["decision"] for receipt in receipts} == {
        "OBSERVED", "APPENDED", "ALREADY_COMMITTED_RECONCILED",
        "RECOVERY_AVAILABLE", "NOT_COMMITTED", "BLOCKED", "INCOMPLETE",
        "COMMIT_STATE_UNKNOWN",
    }
    for receipt in receipts:
        private = receipt.to_dict(); public = receipt.to_public_dict()
        assert store.parse_store_receipt(private).to_dict() == private
        assert store.parse_store_public_projection(public).to_dict() == public
        _assert_schema(private); _assert_schema(public)


def _receipt_mutations(value):
    enum_values = {
        "operation": [item.value for item in store.Operation],
        "decision": [item.value for item in store.StoreDecision],
        "rename_state": [item.value for item in store.RenameState],
        "namespace_state": [item.value for item in store.NamespaceState],
        "global_pending_state": [item.value for item in store.PendingState],
        "content_state": [item.value for item in store.ContentState],
        "resource_observation_state": [item.value for item in store.ResourceObservationState],
        "resource_release_state": [item.value for item in store.ResourceReleaseState],
        "pending_state": [item.value for item in store.PendingState],
        "chain_state": [item.value for item in store.ChainState],
        "commit_state": [item.value for item in store.CommitState],
    }
    boolean_fields = [field for field, item in value.items() if type(item) is bool]
    candidates = {**enum_values,
        **{field: [not value[field]] for field in boolean_fields},
        "entry_count": [0, 1, 256],
        "pending_count": [0, 1, 8], "unreleased_handle_count": [0, 1, 32],
        "unreleased_native_allocation_count": [0, 1, 64],
        "reason_codes": [
            ["SYNTHETIC_FAILURE"], ["NO_REPLACE_APPEND_OBSERVED"],
            ["POINT_IN_TIME_NAMESPACE_OBSERVED"], ["EXACT_LATEST_REPLAY_RECONCILED"],
            ["EXACT_PENDING_PRESENT"], ["NEITHER_PRESENT"],
            ["POINT_IN_TIME_NAMESPACE_OBSERVED", "CORRUPT_PENDING_OBSERVED"],
        ]}
    if "stored_entry_sha256" in value:
        candidates.update({"stored_entry_sha256": [None, D, "sha256:" + "b" * 64],
            "expected_cas_sha256": [None, D, "sha256:" + "c" * 64],
            "chain_disk_bytes": [0, 1, 16 * 1024 * 1024],
            "pending_disk_bytes": [0, 1, 16 * 1024 * 1024]})
    for field, choices in candidates.items():
        if field not in value:
            continue
        for choice in choices:
            if choice != value[field]:
                mutated = copy.deepcopy(value); mutated[field] = copy.deepcopy(choice)
                yield field, choice, mutated
    if "authority_flags" in value:
        for flag in value["authority_flags"]:
            mutated = copy.deepcopy(value); mutated["authority_flags"][flag] = True
            yield f"authority_flags.{flag}", True, mutated


def _runtime_accepts_private(value):
    value["receipt_sha256"] = store._digest_without(
        value, "receipt_sha256", store._RECEIPT_DOMAIN)
    try:
        store.parse_store_receipt(value)
    except (TypeError, ValueError):
        return False
    return True


def _runtime_accepts_public(value):
    value["public_projection_sha256"] = store._digest_without(
        value, "public_projection_sha256", store._PUBLIC_DOMAIN)
    try:
        store.parse_store_public_projection(value)
    except (TypeError, ValueError):
        return False
    return True


def test_generated_single_mutation_runtime_schema_parity_is_zero_mismatch(monkeypatch):
    mismatches = []
    for receipt in _generated_decision_receipts(monkeypatch):
        decision = receipt.to_dict()["decision"]
        for projection, runtime_accepts in (
                (receipt.to_dict(), _runtime_accepts_private),
                (receipt.to_public_dict(), _runtime_accepts_public)):
            for field, choice, mutated in _receipt_mutations(projection):
                runtime = runtime_accepts(copy.deepcopy(mutated))
                schema = VALIDATOR.is_valid(mutated)
                if runtime != schema:
                    mismatches.append((decision, projection["record_type"], field, choice,
                                       runtime, schema))
    assert mismatches == [], f"runtime/schema parity mismatches: {mismatches}"


def _assert_private_semantic_reject(value):
    value["receipt_sha256"] = store._digest_without(
        value, "receipt_sha256", store._RECEIPT_DOMAIN)
    with pytest.raises(ValueError):
        store.parse_store_receipt(value)
    assert not VALIDATOR.is_valid(value)


def _assert_public_semantic_reject(value):
    value["public_projection_sha256"] = store._digest_without(
        value, "public_projection_sha256", store._PUBLIC_DOMAIN)
    with pytest.raises(ValueError):
        store.parse_store_public_projection(value)
    assert not VALIDATOR.is_valid(value)


def test_semantic_expected_reject_corpus_is_independent_from_parity(monkeypatch):
    generated = _generated_decision_receipts(monkeypatch)
    success = {"OBSERVED", "APPENDED", "ALREADY_COMMITTED_RECONCILED",
        "RECOVERY_AVAILABLE", "NOT_COMMITTED"}
    for receipt in generated:
        if receipt.to_dict()["decision"] not in success:
            continue
        for field, bad in (("resource_release_state", "INCOMPLETE"),
                           ("resource_release_state", "UNKNOWN"),
                           ("lock_release_confirmed", False),
                           ("unreleased_handle_count", 1),
                           ("unreleased_native_allocation_count", 1)):
            private = receipt.to_dict(); private[field] = bad
            public = receipt.to_public_dict(); public[field] = bad
            _assert_private_semantic_reject(private)
            _assert_public_semantic_reject(public)

    candidate = _candidate(); key = AudioCompletionLedgerKeyBinding.for_candidate(candidate)
    port = FakePort(); monkeypatch.setattr(store, "_PORT_FACTORY", lambda: port)
    store.append_prepared(store.prepare_append(
        key=key, candidate=candidate, expectation=cas_for_chain((), key)))
    nonempty = store.observe_ledger(key)
    body = nonempty.to_dict()
    assert body["entry_count"] == 1
    assert "final_count" not in body and "entry_revision" not in body
    assert body["namespace_state"] == "FINAL_ONLY" and body["content_state"] == "FINAL_VERIFIED"
    assert all(body[field] is not None for field in (
        "stored_entry_sha256", "expected_cas_sha256"))
    _assert_schema(body); _assert_schema(nonempty.to_public_dict())
    for field, bad in (("namespace_state", "PENDING_ONLY"),
                       ("content_state", "CORRUPT"),
                       ("resource_observation_state", "NOT_OBSERVED"),
                       ("chain_disk_bytes", 0)):
        private = nonempty.to_dict(); private[field] = bad
        _assert_private_semantic_reject(private)
        if field != "chain_disk_bytes":
            public = nonempty.to_public_dict(); public[field] = bad
            _assert_public_semantic_reject(public)

    empty = next(item for item in generated if item.to_dict()["decision"] == "OBSERVED")
    for field, bad in (("namespace_state", "PENDING_ONLY"),
                       ("content_state", "PENDING_VERIFIED"),
                       ("resource_observation_state", "FINAL_REOPEN_VERIFIED"),
                       ("chain_disk_bytes", 1),
                       ("pending_disk_bytes", 1)):
        private = empty.to_dict(); private[field] = bad
        _assert_private_semantic_reject(private)
        if field not in {"chain_disk_bytes", "pending_disk_bytes"}:
            public = empty.to_public_dict(); public[field] = bad
            _assert_public_semantic_reject(public)

    not_committed = next(item for item in generated
        if item.to_dict()["decision"] == "NOT_COMMITTED")
    for field, bad in (("stored_entry_sha256", D),
                       ("expected_cas_sha256", D), ("chain_disk_bytes", 1),
                       ("pending_disk_bytes", 1)):
        private = not_committed.to_dict(); private[field] = bad
        _assert_private_semantic_reject(private)

    recovery = next(item for item in generated
        if item.to_dict()["decision"] == "RECOVERY_AVAILABLE")
    zero_pending_bytes = recovery.to_dict(); zero_pending_bytes["pending_disk_bytes"] = 0
    _assert_private_semantic_reject(zero_pending_bytes)


def test_receipt_shape_has_one_authoritative_tip_scalar_and_rejects_legacy_pairs(monkeypatch):
    receipts = _generated_decision_receipts(monkeypatch)
    private = receipts[0].to_dict()
    public = receipts[0].to_public_dict()
    private_shape = SCHEMA["$defs"]["storeReceipt"]
    public_shape = SCHEMA["$defs"]["publicProjection"]
    recovery_shape = SCHEMA["$defs"]["recoveryReceipt"]
    for shape in (private_shape, public_shape):
        assert shape["additionalProperties"] is False
        assert "entry_count" in shape["required"]
        assert "final_count" not in shape["properties"]
        assert "entry_revision" not in shape["properties"]
    assert "entry_revision" in recovery_shape["required"]
    assert "entry_count" not in recovery_shape["properties"]
    assert "final_count" not in recovery_shape["properties"]

    # The exhaustive legacy equality/inequality space is value-independent:
    # both removed names fail the sealed runtime field set for every pair.
    for count in range(257):
        for legacy in range(257):
            forged_private = dict(private, entry_count=count, final_count=legacy)
            forged_public = dict(public, entry_count=count, final_count=legacy)
            forged_private_revision = dict(private, entry_count=count, entry_revision=legacy)
            forged_public_revision = dict(public, entry_count=count, entry_revision=legacy)
            with pytest.raises(ValueError):
                store.parse_store_receipt(forged_private)
            with pytest.raises(ValueError):
                store.parse_store_public_projection(forged_public)
            with pytest.raises(ValueError):
                store.parse_store_receipt(forged_private_revision)
            with pytest.raises(ValueError):
                store.parse_store_public_projection(forged_public_revision)
    for count, legacy in ((0, 0), (0, 1), (1, 0), (1, 1), (256, 256)):
        assert not VALIDATOR.is_valid(dict(private, entry_count=count, final_count=legacy))
        assert not VALIDATOR.is_valid(dict(public, entry_count=count, final_count=legacy))
        assert not VALIDATOR.is_valid(dict(private, entry_count=count, entry_revision=legacy))
        assert not VALIDATOR.is_valid(dict(public, entry_count=count, entry_revision=legacy))


def test_recoverable_pending_count_byte_and_state_matrix_is_closed(prepared):
    key, token, recovery, _ = _make_pending(prepared)
    recovery_body = recovery.to_dict()
    for revision in range(1, 257):
        revised = copy.deepcopy(recovery_body); revised["entry_revision"] = revision
        revised["recovery_receipt_sha256"] = store._digest_without(
            revised, "recovery_receipt_sha256", store._RECOVERY_DOMAIN)
        assert store.AudioCompletionLedgerRecoveryReceipt.from_dict(
            revised).to_dict() == revised
        assert VALIDATOR.is_valid(revised)
    canonical = store.inspect_pending(
        key=key, recovery=recovery, token=token).to_dict()
    assert canonical["decision"] == "RECOVERY_AVAILABLE"
    for count in range(9):
        for byte_count in (0, 1):
            for global_state in ("RECOVERABLE", "CORRUPT"):
                for pending_state in ("RECOVERABLE", "CORRUPT"):
                    for content_state in ("PENDING_VERIFIED", "CORRUPT"):
                        mutated = copy.deepcopy(canonical)
                        mutated.update({"pending_count": count,
                            "pending_disk_bytes": byte_count,
                            "global_pending_state": global_state,
                            "pending_state": pending_state,
                            "content_state": content_state})
                        expected = (count > 0 and byte_count > 0
                            and pending_state == "RECOVERABLE"
                            and content_state == "PENDING_VERIFIED")
                        runtime = _runtime_accepts_private(copy.deepcopy(mutated))
                        schema = VALIDATOR.is_valid(mutated)
                        assert runtime == schema == expected, (
                            count, byte_count, global_state, pending_state, content_state,
                            runtime, schema, expected)

    public = store.parse_store_receipt(canonical).to_public_dict()
    for count in range(9):
        for global_state in ("RECOVERABLE", "CORRUPT"):
            for pending_state in ("RECOVERABLE", "CORRUPT"):
                for content_state in ("PENDING_VERIFIED", "CORRUPT"):
                    mutated = copy.deepcopy(public)
                    mutated.update({"pending_count": count,
                        "global_pending_state": global_state,
                        "pending_state": pending_state,
                        "content_state": content_state})
                    expected = (count > 0 and pending_state == "RECOVERABLE"
                        and content_state == "PENDING_VERIFIED")
                    runtime = _runtime_accepts_public(copy.deepcopy(mutated))
                    schema = VALIDATOR.is_valid(mutated)
                    assert runtime == schema == expected, (
                        count, global_state, pending_state, content_state,
                        runtime, schema, expected)


def test_self_resigned_private_and_public_impossible_state_tuples_are_rejected(prepared):
    _, _, item, _ = prepared
    receipt, _ = store.append_prepared(item)
    original = receipt.to_dict()
    variants = []
    value = copy.deepcopy(original)
    value["operation"] = "OBSERVE"
    variants.append(value)
    value = copy.deepcopy(original)
    value["filesystem_write_attempted"] = False
    variants.append(value)
    value = copy.deepcopy(original)
    value.update({"decision": "ALREADY_COMMITTED_RECONCILED",
        "reason_codes": ["EXACT_LATEST_REPLAY_RECONCILED"], "rename_state": "NOT_ATTEMPTED",
        "filesystem_write_attempted": False, "filesystem_write_observed": False,
        "filesystem_read_observed": False, "entry_count": 0,
        "chain_disk_bytes": 0, "stored_entry_sha256": None, "expected_cas_sha256": None,
        "global_pending_state": "NONE"})
    variants.append(value)
    for updates in (
        {"decision": "BLOCKED", "reason_codes": ["SYNTHETIC_FAILURE"]},
        {"decision": "BLOCKED", "reason_codes": ["SYNTHETIC_FAILURE"],
         "commit_state": "COMMIT_STATE_UNKNOWN", "rename_state": "SYSCALL_COMPLETION_UNKNOWN"},
        {"decision": "INCOMPLETE", "reason_codes": ["RENAME_FAILED"],
         "rename_state": "RETURNED_FALSE", "commit_state": "KNOWN_COMMITTED"},
        {"operation": "OBSERVE"},
        {"entry_count": 0,
         "stored_entry_sha256": None, "expected_cas_sha256": None},
        {"decision": "RECOVERY_AVAILABLE", "reason_codes": ["PENDING_ONLY_EXACT"],
         "commit_state": "NOT_COMMITTED", "rename_state": "NOT_ATTEMPTED",
         "namespace_state": "PENDING_ONLY", "content_state": "PENDING_VERIFIED",
         "pending_state": "RECOVERABLE", "filesystem_write_attempted": False,
         "filesystem_write_observed": False},
        {"decision": "NOT_COMMITTED", "reason_codes": ["NEITHER_PRESENT"],
         "commit_state": "NOT_COMMITTED", "rename_state": "NOT_ATTEMPTED",
         "namespace_state": "NEITHER", "filesystem_write_attempted": False,
         "filesystem_write_observed": False},
    ):
        value = copy.deepcopy(original); value.update(updates); variants.append(value)
    for value in variants:
        value["receipt_sha256"] = store._digest_without(
            value, "receipt_sha256", store._RECEIPT_DOMAIN)
        with pytest.raises(ValueError): store.parse_store_receipt(value)
        with pytest.raises(Exception): _assert_schema(value)

    public_original = receipt.to_public_dict()
    public_variants = []
    for updates in (
        {"filesystem_read_attempted": False},
        {"decision": "BLOCKED", "reason_codes": ["SYNTHETIC_FAILURE"]},
        {"decision": "BLOCKED", "reason_codes": ["SYNTHETIC_FAILURE"],
         "commit_state": "COMMIT_STATE_UNKNOWN", "rename_state": "SYSCALL_COMPLETION_UNKNOWN"},
        {"decision": "INCOMPLETE", "reason_codes": ["RENAME_FAILED"],
         "rename_state": "RETURNED_FALSE", "commit_state": "KNOWN_COMMITTED"},
        {"operation": "OBSERVE"},
        {"entry_count": 0},
        {"decision": "ALREADY_COMMITTED_RECONCILED",
         "reason_codes": ["EXACT_LATEST_REPLAY_RECONCILED"],
         "rename_state": "NOT_ATTEMPTED", "entry_count": 0,
         "filesystem_write_attempted": False, "filesystem_write_observed": False},
        {"decision": "RECOVERY_AVAILABLE", "reason_codes": ["PENDING_ONLY_EXACT"],
         "commit_state": "NOT_COMMITTED", "rename_state": "NOT_ATTEMPTED",
         "namespace_state": "PENDING_ONLY", "content_state": "PENDING_VERIFIED",
         "pending_state": "RECOVERABLE", "filesystem_write_attempted": False,
         "filesystem_write_observed": False},
        {"decision": "NOT_COMMITTED", "reason_codes": ["NEITHER_PRESENT"],
         "commit_state": "NOT_COMMITTED", "rename_state": "NOT_ATTEMPTED",
         "namespace_state": "NEITHER", "filesystem_write_attempted": False,
         "filesystem_write_observed": False},
    ):
        public = copy.deepcopy(public_original); public.update(updates); public_variants.append(public)
    for public in public_variants:
        public["public_projection_sha256"] = store._digest_without(
            public, "public_projection_sha256", store._PUBLIC_DOMAIN)
        with pytest.raises(ValueError): store.parse_store_public_projection(public)
        with pytest.raises(Exception): _assert_schema(public)
