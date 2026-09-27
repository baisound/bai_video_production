from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task099_project_job_currentness import (
    ContractRecord, EvidenceSource, TransactionState, classify_operation_witness,
    compile_successor_index, create_digested_record, create_phase_result, execute_transaction,
    parse_candidate, parse_index, parse_proposal, parse_readback, parse_request, parse_result,
    parse_security_json, parse_snapshot, project_public_result,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "task099-project-job-currentness.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA.name


def h(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def event(sequence: int, operation: str = "operation-1") -> dict:
    body = {"task076_namespace": "task076-jobs", "task076_event_contract_version": "DURABLE_PRODUCT_JOB_EVENT_V2", "operation_id": operation, "event_sequence": sequence}
    return create_digested_record(body, kind="event", field="coordinate_sha256")


def candidate(sequence: int = 1, *, source: str = "FIXTURE_ONLY", predecessor: dict | None = None) -> dict:
    body = {
        "candidate_contract_version": "PROJECT_JOB_HEAD_CANDIDATE_V2", "record_type": "ProjectJobHeadCandidateV2",
        "project_id": "project-fixture", "job_semantic_key_sha256": h("semantic"), "namespace_plan_set_sha256": h("namespace"),
        "task076_profile_id": "DURABLE_PRODUCT_JOB_EVENT_V2", "task076_profile_version": "2.0.0", "task076_event_contract_version": "DURABLE_PRODUCT_JOB_EVENT_V2",
        "event_coordinate": event(sequence), "event_sha256": h(f"event-{sequence}"), "event_physical_identity_ref": f"event-physical-{sequence}",
        "predecessor_event_coordinate": None if predecessor is None else predecessor["event_coordinate"],
        "predecessor_event_sha256": None if predecessor is None else predecessor["event_sha256"],
        "predecessor_event_physical_identity_ref": None if predecessor is None else predecessor["event_physical_identity_ref"],
        "event_kind": "RESERVED" if sequence == 1 else "PREPARED", "event_sequence": sequence,
        "task076_candidate_readback_sha256": h(f"readback-{sequence}"), "task068_plan_sha256": h("plan"),
        "task068_publish_receipt_sha256": h(f"publish-{sequence}"), "task068_pinned_readback_sha256": h(f"pin-{sequence}"),
        "consumer_operation_id": "consumer-save-1", "install_build_binding_sha256": h("build"), "security_reader_binding_sha256": h("security"),
        "producer_issuer_binding_sha256": h("issuer"), "evidence_source": source,
        "observed_at": "2026-09-27T00:00:00Z", "expires_at": "2026-09-27T00:05:00Z",
    }
    return create_digested_record(body, kind="candidate", field="candidate_sha256")


def readback(*, manifest_revision: int = 3, head: dict | None = None, source: str = "FIXTURE_ONLY") -> dict:
    manifest_sha = h(f"manifest-{manifest_revision}")
    state_body = {"authority_instance_id": "task099-fixture", "epoch_id": "epoch-1", "manifest_generation_sequence": manifest_revision,
                  "manifest_physical_identity_ref": f"manifest-physical-{manifest_revision}", "manifest_revision": manifest_revision,
                  "manifest_sha256": manifest_sha, "project_id": "project-fixture", "project_root_identity_ref": "root-fixture"}
    state_sha = sha256_bytes(b"BAI:TASK-099:PROJECT-CURRENTNESS-STATE-COORDINATE:V2\0" + canonical_json_bytes(state_body))
    state = {key: state_body[key] for key in ("authority_instance_id", "epoch_id", "manifest_generation_sequence")}
    state["state_coordinate_sha256"] = state_sha
    obs_body = {"clock_binding_sha256": h("clock"), "expires_at": "2026-09-27T00:05:00Z", "observation_sequence": 7,
                "observed_at": "2026-09-27T00:00:00Z", "state_coordinate_sha256": state_sha}
    observation = {key: obs_body[key] for key in ("observation_sequence", "observed_at", "expires_at", "clock_binding_sha256")}
    observation["observation_sha256"] = sha256_bytes(b"BAI:TASK-099:PROJECT-CURRENTNESS-OBSERVATION:V2\0" + canonical_json_bytes(obs_body))
    body = {
        "contract_version": "PROJECT_JOB_CURRENTNESS_READBACK_V2", "record_type": "ProjectJobCurrentnessReadbackV2",
        "project_id": "project-fixture", "manifest_revision": manifest_revision, "manifest_sha256": manifest_sha,
        "predecessor_manifest_sha256": None if manifest_revision == 1 else h(f"manifest-{manifest_revision-1}"),
        "manifest_physical_identity_ref": f"manifest-physical-{manifest_revision}", "project_root_identity_ref": "root-fixture",
        "job_semantic_key_sha256": h("semantic"), "head": head or {"variant": "ABSENT_JOB_HEAD", "index_state": "UNINITIALIZED", "index_revision": None, "index_sha256": None, "index_physical_identity_ref": None, "absence_proof_sha256": h("absence")},
        "namespace_plan_set_sha256": h("namespace"), "consumer_operation_id": "consumer-save-1",
        "install_build_binding_sha256": h("build"), "security_reader_binding_sha256": h("security"), "producer_issuer_binding_sha256": h("issuer"),
        "evidence_source": source, "currentness_capability": "CURRENT" if source == "TRUSTED_BACKEND" else "FIXTURE_ONLY",
        "trusted_currentness_coordinate": {"state": state, "observation": observation},
    }
    return create_digested_record(body, kind="readback", field="readback_sha256")


def proposal(prior: dict, index: dict) -> dict:
    same_a, same_b = h("invariants"), h("children")
    body = {"proposal_version": "PROJECT_MANIFEST_SUCCESSOR_PROPOSAL_V2", "record_type": "ProjectManifestSuccessorProposalV2",
            "project_id": "project-fixture", "project_format_id": "BAI_VIDEO_PRODUCTION_PROJECT", "project_format_version": "2.0.0",
            "prior_manifest_revision": prior["manifest_revision"], "prior_manifest_sha256": prior["manifest_sha256"],
            "prior_manifest_physical_identity_ref": prior["manifest_physical_identity_ref"], "successor_manifest_revision": prior["manifest_revision"] + 1,
            "predecessor_manifest_sha256": prior["manifest_sha256"], "successor_manifest_sha256": h(f"manifest-{prior['manifest_revision'] + 1}"), "updated_at": "2026-09-27T00:01:00Z",
            "prior_project_invariant_fields_sha256": same_a, "successor_project_invariant_fields_sha256": same_a,
            "prior_unrelated_child_bindings_sha256": same_b, "successor_unrelated_child_bindings_sha256": same_b,
            "prior_task099_child_binding": None, "successor_task099_child_binding": {"content_sha256": index["index_sha256"]},
            "evidence_source": "FIXTURE_ONLY", "producer_issuer_binding_sha256": h("issuer")}
    return create_digested_record(body, kind="proposal", field="proposal_sha256")


def request(prior: dict, cand: dict, index: dict, prop: dict) -> dict:
    body = {"request_version": "PROJECT_JOB_CURRENTNESS_TRANSACTION_REQUEST_V2", "record_type": "ProjectJobCurrentnessTransactionRequestV2",
            "transaction_id": "transaction-1", "project_id": "project-fixture", "job_semantic_key_sha256": h("semantic"),
            "prior_readback_sha256": prior["readback_sha256"], "prior_state_coordinate_sha256": prior["trusted_currentness_coordinate"]["state"]["state_coordinate_sha256"],
            "candidate_sha256": cand["candidate_sha256"], "candidate_readback_sha256": cand["task076_candidate_readback_sha256"],
            "manifest_successor_proposal_sha256": prop["proposal_sha256"], "successor_manifest_revision": prop["successor_manifest_revision"],
            "successor_index_revision": index["index_revision"], "successor_index_sha256": index["index_sha256"],
            "namespace_plan_set_sha256": h("namespace"), "consumer_operation_id": "consumer-save-1", "install_build_binding_sha256": h("build"),
            "security_reader_binding_sha256": h("security"), "requested_at": "2026-09-27T00:00:30Z", "expires_at": "2026-09-27T00:04:00Z"}
    return create_digested_record(body, kind="request", field="request_sha256")


def snapshot(prior: dict, index: dict | None, prop: dict) -> dict:
    body = {
        "snapshot_version": "PROJECT_JOB_CURRENTNESS_SNAPSHOT_V2", "record_type": "ProjectJobCurrentnessSnapshotV2",
        "readback": prior, "index_state": "UNINITIALIZED" if index is None else "PRESENT", "index": index,
        "manifest_canonical_sha256": prior["manifest_sha256"], "manifest_physical_identity_ref": prior["manifest_physical_identity_ref"],
        "project_invariant_fields_sha256": prop["prior_project_invariant_fields_sha256"],
        "unrelated_child_bindings_sha256": prop["prior_unrelated_child_bindings_sha256"],
        "task099_child_binding_state": "ABSENT" if index is None else "PRESENT",
        "producer_issuer_binding_sha256": prior["producer_issuer_binding_sha256"], "evidence_source": prior["evidence_source"],
    }
    return create_digested_record(body, kind="snapshot", field="snapshot_sha256")


def with_observation(value: dict, *, sequence: int, observed_at: str, expires_at: str) -> dict:
    body = copy.deepcopy(value); state_sha = body["trusted_currentness_coordinate"]["state"]["state_coordinate_sha256"]
    obs = {"observation_sequence":sequence,"observed_at":observed_at,"expires_at":expires_at,"clock_binding_sha256":h("clock")}
    preimage = {**obs, "state_coordinate_sha256":state_sha}
    obs["observation_sha256"] = sha256_bytes(b"BAI:TASK-099:PROJECT-CURRENTNESS-OBSERVATION:V2\0" + canonical_json_bytes(preimage))
    body["trusted_currentness_coordinate"]["observation"] = obs
    return create_digested_record(body, kind="readback", field="readback_sha256")


class FakeBackend:
    def __init__(self, prior, cand, index, prop, successor=None, *, witness="SAME_OPERATION_COMMITTED_CURRENT", no_write=False):
        self.prior, self.cand, self.index, self.prop, self.successor = prior, cand, index, prop, successor
        self.witness, self.no_write, self.calls = witness, no_write, []

    def phase(self, name, status, payload, **kw):
        self.calls.append(name)
        return create_phase_result(phase=name, transaction_id="transaction-1", request_sha256=self.req_sha,
            evidence_source="FIXTURE_ONLY", producer_issuer_binding_sha256=h("issuer"), phase_status=status,
            payload=payload, no_manifest_write_proven=kw.get("no_write", False),
            manifest_commit_observation=kw.get("manifest", "NOT_COMMITTED"))

    def open_prior(self, request):
        self.req_sha=request["request_sha256"]
        return self.phase("OPEN","OPENED",{"snapshot":snapshot(self.prior,None,self.prop)})
    def pin_candidate(self, request, candidate):
        return self.phase("PIN_CANDIDATE","PINNED",{"candidate_sha256":candidate["candidate_sha256"],"candidate_readback_sha256":candidate["task076_candidate_readback_sha256"],"event_physical_identity_ref":candidate["event_physical_identity_ref"],"predecessor_event_physical_identity_ref":candidate["predecessor_event_physical_identity_ref"]})
    def acquire_exclusive(self, request):
        return self.phase("ACQUIRE","ACQUIRED",{"lease_ref":"lease-1","project_root_identity_ref":self.prior["project_root_identity_ref"],"manifest_physical_identity_ref":self.prior["manifest_physical_identity_ref"],"state_coordinate_sha256":request["prior_state_coordinate_sha256"]})
    def reread_under_lease(self, request, lease_ref): return self.phase("REREAD","REREAD",{"snapshot":snapshot(self.prior,None,self.prop)},no_write=True)
    def validate_successor_proposal(self, request, index, proposal, lease_ref):
        fields=("prior_project_invariant_fields_sha256","successor_project_invariant_fields_sha256","prior_unrelated_child_bindings_sha256","successor_unrelated_child_bindings_sha256")
        return self.phase("VALIDATE_PROPOSAL","PROPOSAL_ACCEPTED_NO_WRITE",{"proposal_sha256":proposal["proposal_sha256"],"successor_manifest_sha256":proposal["successor_manifest_sha256"],"index_sha256":index["index_sha256"],**{field:proposal[field] for field in fields}},no_write=True)
    def publish_index_generation(self, request, index, lease_ref): return self.phase("PUBLISH_INDEX","PUBLISHED",{"publication_state":"PUBLISHED_ORPHAN_SAFE","index_sha256":index["index_sha256"],"index_physical_identity_ref":"index-physical-1"},no_write=True)
    def commit_manifest_successor(self, request, index_readback, lease_ref):
        committed = self.witness in {"SAME_OPERATION_COMMITTED_CURRENT","SAME_OPERATION_COMMITTED_SUPERSEDED"}
        unknown = self.witness == "SAME_OPERATION_HISTORY_UNKNOWN"
        return self.phase("COMMIT","COMMIT_RESULT",{"witness_state":self.witness,"successor_manifest_sha256":self.prop["successor_manifest_sha256"] if committed else None,"successor_manifest_physical_identity_ref":"manifest-physical-4" if committed else None},no_write=self.no_write if not committed else False,manifest="COMMITTED" if committed else ("UNKNOWN" if unknown else "NOT_COMMITTED"))
    def read_successor(self, request, lease_ref): return self.phase("READ_SUCCESSOR","READ",{"readback":self.successor},manifest="COMMITTED")
    def query_operation(self, transaction_id, request_sha256):
        committed = self.witness in {"SAME_OPERATION_COMMITTED_CURRENT","SAME_OPERATION_COMMITTED_SUPERSEDED"}; unknown = self.witness == "SAME_OPERATION_HISTORY_UNKNOWN"
        return self.phase("QUERY_OPERATION","QUERY",{"witness_state":self.witness,"successor_manifest_sha256":self.prop["successor_manifest_sha256"] if committed else None,"successor_manifest_physical_identity_ref":"manifest-physical-4" if committed else None},no_write=self.no_write if not committed else False,manifest="COMMITTED" if committed else ("UNKNOWN" if unknown else "NOT_COMMITTED"))
    def release(self, request, lease_ref): return self.phase("RELEASE","RELEASED",{"release_state":"RELEASED"})


def test_frozen_vectors_and_strict_records() -> None:
    state_vector = {"authority_instance_id":"task099-fixture","epoch_id":"epoch-1","manifest_generation_sequence":1,"manifest_physical_identity_ref":"manifest-fixture","manifest_revision":3,"manifest_sha256":"sha256:"+"b"*64,"project_id":"project-fixture","project_root_identity_ref":"root-fixture"}
    state_sha = sha256_bytes(b"BAI:TASK-099:PROJECT-CURRENTNESS-STATE-COORDINATE:V2\0" + canonical_json_bytes(state_vector))
    assert state_sha == "sha256:a61a3a828ae786bfaa42c62ebb1442fdb2c408d99d55555eab0c58f209ec9045"
    observation_vector = {"clock_binding_sha256":"sha256:"+"a"*64,"expires_at":"2026-09-27T00:05:00Z","observation_sequence":7,"observed_at":"2026-09-27T00:00:00Z","state_coordinate_sha256":state_sha}
    assert sha256_bytes(b"BAI:TASK-099:PROJECT-CURRENTNESS-OBSERVATION:V2\0" + canonical_json_bytes(observation_vector)) == "sha256:99fa406c81dacccb2500a297bd6eda92713397f6ee4891feb5bde0a2fe4cdb05"
    rb = readback()
    assert parse_readback(rb).to_dict() == rb
    assert parse_candidate(candidate()).to_dict()["event_kind"] == "RESERVED"


def test_first_index_and_later_transition_preserve_unrelated_heads() -> None:
    rb = parse_readback(readback()); cand1 = parse_candidate(candidate())
    first = compile_successor_index(None, rb, cand1)
    assert first.to_dict()["index_revision"] == 1
    first_body = first.to_dict()
    selected = {"variant": "SELECTED_JOB_HEAD", "index_state": "PRESENT", "index_revision": 1, "index_sha256": first_body["index_sha256"], "index_physical_identity_ref": "index-physical-1",
                "event_coordinate": candidate()["event_coordinate"], "event_sha256": candidate()["event_sha256"], "event_physical_identity_ref": "event-physical-1",
                "predecessor_event_coordinate": None, "predecessor_event_sha256": None, "predecessor_event_physical_identity_ref": None, "selection_proof_sha256": h("selection")}
    cand2 = candidate(2, predecessor=candidate())
    second = compile_successor_index(first, parse_readback(readback(head=selected)), parse_candidate(cand2)).to_dict()
    assert second["index_revision"] == 2 and second["predecessor_index_sha256"] == first_body["index_sha256"]
    assert second["heads"][0]["event_sequence"] == 2


def test_constructor_and_typed_revalidation_block_bypass() -> None:
    with pytest.raises(TypeError): ContractRecord("candidate", candidate())
    forged = object.__new__(ContractRecord); object.__setattr__(forged, "kind", "candidate"); object.__setattr__(forged, "data", candidate())
    forged.data["event_kind"] = "SUCCEEDED"
    with pytest.raises(ValueError): compile_successor_index(None, parse_readback(readback()), forged)


def test_parser_rejects_duplicate_and_extreme_depth() -> None:
    with pytest.raises(ValueError, match="duplicate"): parse_security_json(b'{"a":1,"a":2}')
    with pytest.raises(ValueError, match="depth"): parse_security_json(b"[" * 2000 + b"0" + b"]" * 2000)
    with pytest.raises(ValueError): parse_security_json(b'{"value":1e999}')
    bad = candidate(); bad["event_physical_identity_ref"] = "urn:foreign"
    with pytest.raises(ValueError): parse_candidate(bad)


def test_superseded_operation_never_becomes_no_write() -> None:
    state, manifest, index = classify_operation_witness({"witness_state": "SAME_OPERATION_COMMITTED_SUPERSEDED"})
    assert (state, manifest, index) == (TransactionState.UNKNOWN, "COMMITTED", "SUPERSEDED_PRESERVED")


def test_fake_port_commit_is_structural_success_but_never_live_currentness() -> None:
    prior = readback(); cand = candidate()
    idx = compile_successor_index(None, parse_readback(prior), parse_candidate(cand)).to_dict()
    prop = proposal(prior, idx); req = request(prior, cand, idx, prop)
    selected = {"variant": "SELECTED_JOB_HEAD", "index_state": "PRESENT", "index_revision": idx["index_revision"],
                "index_sha256": idx["index_sha256"], "index_physical_identity_ref": "index-physical-1",
                "event_coordinate": cand["event_coordinate"], "event_sha256": cand["event_sha256"],
                "event_physical_identity_ref": cand["event_physical_identity_ref"], "predecessor_event_coordinate": None,
                "predecessor_event_sha256": None, "predecessor_event_physical_identity_ref": None,
                "selection_proof_sha256": h("selection")}
    successor = readback(manifest_revision=4, head=selected)

    backend = FakeBackend(prior, cand, idx, prop, successor)
    result = execute_transaction(req, cand, prior, None, prop, backend).to_dict()
    assert result["transaction_state"] == "COMMITTED_WITH_READBACK"
    assert result["live_currentness_eligible"] is False
    assert result["currentness_capability"] == "FIXTURE_ONLY"
    assert result["reason_codes"] == ["FIXTURE_ONLY_EVIDENCE"]
    assert parse_result(result).to_dict() == result
    public = project_public_result(result, project_id="project-fixture", job_semantic_key_sha256=h("semantic"), current_event_sha256=cand["event_sha256"])
    assert "manifest_physical_identity_ref" not in public and public["current_event_sha256"] == cand["event_sha256"]
    assert backend.calls == ["OPEN","PIN_CANDIDATE","ACQUIRE","REREAD","VALIDATE_PROPOSAL","PUBLISH_INDEX","COMMIT","READ_SUCCESSOR","RELEASE"]


def test_no_write_classification_requires_same_operation_proof() -> None:
    prior = readback(); cand = candidate(); idx = compile_successor_index(None, parse_readback(prior), parse_candidate(cand)).to_dict()
    prop = proposal(prior, idx); req = request(prior, cand, idx, prop)

    backend = FakeBackend(prior,cand,idx,prop,witness="SAME_OPERATION_NOT_COMMITTED",no_write=False)
    result = execute_transaction(req, cand, prior, None, prop, backend).to_dict()
    assert result["transaction_state"] == "COMMIT_OUTCOME_UNKNOWN"
    assert result["manifest_commit_observation"] == "UNKNOWN"
    assert "READ_SUCCESSOR" not in backend.calls


def test_snapshot_rejects_partial_or_inconsistent_prior_state() -> None:
    prior = readback(); cand = candidate(); idx = compile_successor_index(None, parse_readback(prior), parse_candidate(cand)).to_dict()
    prop = proposal(prior, idx); snap = snapshot(prior, None, prop)
    assert parse_snapshot(snap).to_dict() == snap
    partial = copy.deepcopy(snap); partial.pop("index_state")
    with pytest.raises(ValueError): parse_snapshot(partial)
    inconsistent = copy.deepcopy(snap); inconsistent["task099_child_binding_state"] = "PRESENT"
    inconsistent = create_digested_record(inconsistent, kind="snapshot", field="snapshot_sha256")
    with pytest.raises(ValueError): parse_snapshot(inconsistent)


def test_foreign_successor_identity_fails_closed_after_commit() -> None:
    prior = readback(); cand = candidate(); idx = compile_successor_index(None, parse_readback(prior), parse_candidate(cand)).to_dict()
    prop = proposal(prior, idx); req = request(prior, cand, idx, prop)
    selected = {"variant":"SELECTED_JOB_HEAD","index_state":"PRESENT","index_revision":1,"index_sha256":idx["index_sha256"],"index_physical_identity_ref":"index-physical-1",
                "event_coordinate":cand["event_coordinate"],"event_sha256":cand["event_sha256"],"event_physical_identity_ref":"foreign-event-physical",
                "predecessor_event_coordinate":None,"predecessor_event_sha256":None,"predecessor_event_physical_identity_ref":None,"selection_proof_sha256":h("selection")}
    successor = readback(manifest_revision=4, head=selected)
    result = execute_transaction(req, cand, prior, None, prop, FakeBackend(prior,cand,idx,prop,successor)).to_dict()
    assert result["transaction_state"] == "COMMIT_OUTCOME_UNKNOWN"
    assert result["reason_codes"] == ["SUCCESSOR_READBACK_FAILED"]


def test_phase_operation_binding_tamper_is_rejected() -> None:
    prior = readback(); cand = candidate(); idx = compile_successor_index(None, parse_readback(prior), parse_candidate(cand)).to_dict()
    prop = proposal(prior, idx); req = request(prior, cand, idx, prop)
    backend = FakeBackend(prior,cand,idx,prop)
    original = backend.open_prior
    def tampered(request_value):
        value = original(request_value); value["transaction_id"] = "foreign-transaction"
        return create_digested_record(value, kind="phase", field="phase_result_sha256")
    backend.open_prior = tampered
    with pytest.raises(ValueError, match="operation binding"): execute_transaction(req, cand, prior, None, prop, backend)


def test_unknown_phase_status_is_rejected_before_mutation() -> None:
    prior = readback(); cand = candidate(); idx = compile_successor_index(None, parse_readback(prior), parse_candidate(cand)).to_dict()
    prop = proposal(prior, idx); req = request(prior, cand, idx, prop); backend = FakeBackend(prior,cand,idx,prop)
    original = backend.pin_candidate
    def invalid_status(request_value, candidate_value):
        value = original(request_value, candidate_value); value["phase_status"] = "UNRECOGNIZED"
        return create_digested_record(value, kind="phase", field="phase_result_sha256")
    backend.pin_candidate = invalid_status
    with pytest.raises(ValueError, match="phase status unsupported"): execute_transaction(req,cand,prior,None,prop,backend)
    assert "PUBLISH_INDEX" not in backend.calls


def test_validate_rejection_blocks_before_publish_and_releases() -> None:
    prior = readback(); cand = candidate(); idx = compile_successor_index(None, parse_readback(prior), parse_candidate(cand)).to_dict()
    prop = proposal(prior, idx); req = request(prior, cand, idx, prop); backend = FakeBackend(prior,cand,idx,prop)
    def rejected(request_value, index_value, proposal_value, lease_ref):
        fields=("prior_project_invariant_fields_sha256","successor_project_invariant_fields_sha256","prior_unrelated_child_bindings_sha256","successor_unrelated_child_bindings_sha256")
        return backend.phase("VALIDATE_PROPOSAL","PROPOSAL_REJECTED_NO_WRITE",{"proposal_sha256":proposal_value["proposal_sha256"],"successor_manifest_sha256":proposal_value["successor_manifest_sha256"],"index_sha256":index_value["index_sha256"],**{field:proposal_value[field] for field in fields}},no_write=True)
    backend.validate_successor_proposal = rejected
    result = execute_transaction(req, cand, prior, None, prop, backend).to_dict()
    assert result["transaction_state"] == "BLOCKED_NO_WRITE"
    assert backend.calls[-1] == "RELEASE" and "PUBLISH_INDEX" not in backend.calls


def test_validate_rejection_without_no_write_proof_is_unknown() -> None:
    prior = readback(); cand = candidate(); idx = compile_successor_index(None, parse_readback(prior), parse_candidate(cand)).to_dict()
    prop = proposal(prior, idx); req = request(prior, cand, idx, prop); backend = FakeBackend(prior,cand,idx,prop)
    def uncertain(request_value, index_value, proposal_value, lease_ref):
        fields=("prior_project_invariant_fields_sha256","successor_project_invariant_fields_sha256","prior_unrelated_child_bindings_sha256","successor_unrelated_child_bindings_sha256")
        return backend.phase("VALIDATE_PROPOSAL","PROPOSAL_REJECTED_NO_WRITE",{"proposal_sha256":proposal_value["proposal_sha256"],"successor_manifest_sha256":proposal_value["successor_manifest_sha256"],"index_sha256":index_value["index_sha256"],**{field:proposal_value[field] for field in fields}},no_write=False,manifest="UNKNOWN")
    backend.validate_successor_proposal = uncertain
    with pytest.raises(ValueError, match="prove no manifest write"):
        execute_transaction(req,cand,prior,None,prop,backend)
    assert backend.calls[-1] == "RELEASE"


def test_fresh_observation_advance_is_not_a_state_conflict() -> None:
    prior = readback(); cand = candidate(); idx = compile_successor_index(None, parse_readback(prior), parse_candidate(cand)).to_dict()
    prop = proposal(prior, idx); req = request(prior, cand, idx, prop)
    selected = {"variant":"SELECTED_JOB_HEAD","index_state":"PRESENT","index_revision":1,"index_sha256":idx["index_sha256"],"index_physical_identity_ref":"index-physical-1","event_coordinate":cand["event_coordinate"],"event_sha256":cand["event_sha256"],"event_physical_identity_ref":cand["event_physical_identity_ref"],"predecessor_event_coordinate":None,"predecessor_event_sha256":None,"predecessor_event_physical_identity_ref":None,"selection_proof_sha256":h("selection")}
    successor = with_observation(readback(manifest_revision=4,head=selected),sequence=9,observed_at="2026-09-27T00:00:20Z",expires_at="2026-09-27T00:07:00Z")
    backend = FakeBackend(prior,cand,idx,prop,successor)
    refreshed = with_observation(prior,sequence=8,observed_at="2026-09-27T00:00:10Z",expires_at="2026-09-27T00:06:00Z")
    def reread(request_value, lease_ref): return backend.phase("REREAD","REREAD",{"snapshot":snapshot(refreshed,None,prop)},no_write=True)
    backend.reread_under_lease = reread
    assert execute_transaction(req,cand,prior,None,prop,backend).to_dict()["transaction_state"] == "COMMITTED_WITH_READBACK"


def test_publish_unknown_cannot_reach_commit_even_with_published_payload() -> None:
    prior = readback(); cand = candidate(); idx = compile_successor_index(None, parse_readback(prior), parse_candidate(cand)).to_dict()
    prop = proposal(prior, idx); req = request(prior, cand, idx, prop); backend = FakeBackend(prior,cand,idx,prop)
    def contradictory(request_value, index_value, lease_ref):
        return backend.phase("PUBLISH_INDEX","UNKNOWN",{"publication_state":"PUBLISHED_ORPHAN_SAFE","index_sha256":index_value["index_sha256"],"index_physical_identity_ref":"index-physical-1"},manifest="UNKNOWN")
    backend.publish_index_generation = contradictory
    with pytest.raises(ValueError, match="publish status/payload contradiction"):
        execute_transaction(req,cand,prior,None,prop,backend)
    assert "COMMIT" not in backend.calls and backend.calls[-1] == "RELEASE"


def test_known_superseded_commit_is_never_downgraded_by_query() -> None:
    prior = readback(); cand = candidate(); idx = compile_successor_index(None, parse_readback(prior), parse_candidate(cand)).to_dict()
    prop = proposal(prior, idx); req = request(prior, cand, idx, prop)
    backend = FakeBackend(prior,cand,idx,prop,witness="SAME_OPERATION_COMMITTED_SUPERSEDED")
    result = execute_transaction(req,cand,prior,None,prop,backend).to_dict()
    assert result["transaction_state"] == "COMMIT_OUTCOME_UNKNOWN"
    assert result["manifest_commit_observation"] == "COMMITTED" and result["index_disposition"] == "SUPERSEDED_PRESERVED"
    assert "QUERY_OPERATION" not in backend.calls


def test_query_committed_foreign_manifest_cannot_be_selected() -> None:
    prior = readback(); cand = candidate(); idx = compile_successor_index(None, parse_readback(prior), parse_candidate(cand)).to_dict()
    prop = proposal(prior, idx); req = request(prior, cand, idx, prop)
    backend = FakeBackend(prior,cand,idx,prop,witness="SAME_OPERATION_HISTORY_UNKNOWN")
    def foreign_query(transaction_id, request_sha256):
        return backend.phase("QUERY_OPERATION","QUERY",{"witness_state":"SAME_OPERATION_COMMITTED_CURRENT","successor_manifest_sha256":h("foreign-manifest"),"successor_manifest_physical_identity_ref":"manifest-physical-4"},manifest="COMMITTED")
    backend.query_operation = foreign_query
    result = execute_transaction(req,cand,prior,None,prop,backend).to_dict()
    assert result["transaction_state"] == "COMMIT_OUTCOME_UNKNOWN"
    assert result["manifest_commit_observation"] == "COMMITTED"
    assert "READ_SUCCESSOR" not in backend.calls


def test_release_failure_preserves_committed_result_with_warning() -> None:
    prior = readback(); cand = candidate(); idx = compile_successor_index(None, parse_readback(prior), parse_candidate(cand)).to_dict()
    prop = proposal(prior, idx); req = request(prior, cand, idx, prop)
    selected = {"variant":"SELECTED_JOB_HEAD","index_state":"PRESENT","index_revision":1,"index_sha256":idx["index_sha256"],"index_physical_identity_ref":"index-physical-1","event_coordinate":cand["event_coordinate"],"event_sha256":cand["event_sha256"],"event_physical_identity_ref":cand["event_physical_identity_ref"],"predecessor_event_coordinate":None,"predecessor_event_sha256":None,"predecessor_event_physical_identity_ref":None,"selection_proof_sha256":h("selection")}
    backend = FakeBackend(prior,cand,idx,prop,readback(manifest_revision=4,head=selected))
    def fail_release(request_value, lease_ref):
        backend.calls.append("RELEASE")
        raise RuntimeError("release unavailable")
    backend.release = fail_release
    result = execute_transaction(req,cand,prior,None,prop,backend).to_dict()
    assert result["transaction_state"] == "COMMITTED_WITH_READBACK"
    assert result["reason_codes"] == ["FIXTURE_ONLY_EVIDENCE","LEASE_RELEASE_WARNING"]


def test_release_status_payload_contradiction_preserves_warning() -> None:
    prior = readback(); cand = candidate(); idx = compile_successor_index(None, parse_readback(prior), parse_candidate(cand)).to_dict()
    prop = proposal(prior, idx); req = request(prior, cand, idx, prop)
    selected = {"variant":"SELECTED_JOB_HEAD","index_state":"PRESENT","index_revision":1,"index_sha256":idx["index_sha256"],"index_physical_identity_ref":"index-physical-1","event_coordinate":cand["event_coordinate"],"event_sha256":cand["event_sha256"],"event_physical_identity_ref":cand["event_physical_identity_ref"],"predecessor_event_coordinate":None,"predecessor_event_sha256":None,"predecessor_event_physical_identity_ref":None,"selection_proof_sha256":h("selection")}
    backend = FakeBackend(prior,cand,idx,prop,readback(manifest_revision=4,head=selected))
    def contradictory_release(request_value, lease_ref):
        return backend.phase("RELEASE","RELEASE_WARNING",{"release_state":"RELEASED"})
    backend.release = contradictory_release
    result = execute_transaction(req,cand,prior,None,prop,backend).to_dict()
    assert result["transaction_state"] == "COMMITTED_WITH_READBACK"
    assert result["reason_codes"] == ["FIXTURE_ONLY_EVIDENCE","LEASE_RELEASE_WARNING"]


def test_post_commit_read_exception_returns_unknown_and_releases() -> None:
    prior = readback(); cand = candidate(); idx = compile_successor_index(None, parse_readback(prior), parse_candidate(cand)).to_dict()
    prop = proposal(prior, idx); req = request(prior, cand, idx, prop); backend = FakeBackend(prior,cand,idx,prop)
    def fail_read(request_value, lease_ref): raise RuntimeError("readback unavailable")
    backend.read_successor = fail_read
    result = execute_transaction(req,cand,prior,None,prop,backend).to_dict()
    assert result["transaction_state"] == "COMMIT_OUTCOME_UNKNOWN"
    assert backend.calls[-1] == "RELEASE"


def test_schema_mirror_and_positive_records() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8")); Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    rb = readback(); cand = candidate(); idx = compile_successor_index(None, parse_readback(rb), parse_candidate(cand)).to_dict(); prop = proposal(rb, idx); req = request(rb, cand, idx, prop)
    snap = snapshot(rb, None, prop); phase = create_phase_result(phase="OPEN",transaction_id="transaction-1",request_sha256=req["request_sha256"],evidence_source="FIXTURE_ONLY",producer_issuer_binding_sha256=h("issuer"),phase_status="OPENED",payload={"snapshot":snap})
    selected = {"variant":"SELECTED_JOB_HEAD","index_state":"PRESENT","index_revision":1,"index_sha256":idx["index_sha256"],"index_physical_identity_ref":"index-physical-1","event_coordinate":cand["event_coordinate"],"event_sha256":cand["event_sha256"],"event_physical_identity_ref":cand["event_physical_identity_ref"],"predecessor_event_coordinate":None,"predecessor_event_sha256":None,"predecessor_event_physical_identity_ref":None,"selection_proof_sha256":h("selection")}
    result = execute_transaction(req,cand,rb,None,prop,FakeBackend(rb,cand,idx,prop,readback(manifest_revision=4,head=selected))).to_dict()
    for value in (rb, cand, idx, prop, req, snap, phase, result): assert list(validator.iter_errors(value)) == []
    contradictory_publish = create_phase_result(phase="PUBLISH_INDEX",transaction_id="transaction-1",request_sha256=req["request_sha256"],evidence_source="FIXTURE_ONLY",producer_issuer_binding_sha256=h("issuer"),phase_status="UNKNOWN",manifest_commit_observation="UNKNOWN",payload={"publication_state":"PUBLISHED_ORPHAN_SAFE","index_sha256":idx["index_sha256"],"index_physical_identity_ref":"index-physical-1"})
    assert list(validator.iter_errors(contradictory_publish))
    contradictory_release = create_phase_result(phase="RELEASE",transaction_id="transaction-1",request_sha256=req["request_sha256"],evidence_source="FIXTURE_ONLY",producer_issuer_binding_sha256=h("issuer"),phase_status="RELEASE_WARNING",payload={"release_state":"RELEASED"})
    assert list(validator.iter_errors(contradictory_release))


def test_effect_free_source_surface() -> None:
    source = (ROOT / "src" / "ai_video_production" / "task099_project_job_currentness.py").read_text(encoding="utf-8")
    for forbidden in ("from pathlib", "import os", "import subprocess", "import socket", "AtomicJsonWriter", "ProductProjectManifestStore"):
        assert forbidden not in source
