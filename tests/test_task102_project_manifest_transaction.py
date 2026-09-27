from __future__ import annotations

import ast
import copy
from dataclasses import replace
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task102_project_manifest_transaction import (
    AdmissionContext,
    NonceBinding,
    OperationProfile,
    PROTOCOL_VERSION,
    PureEvidenceRegistry,
    PureNonceLedger,
    PurePmstStateMachine,
    ReadbackBinding,
    ScriptedFakePmstPort,
    parse_enrollment,
    parse_intent,
    parse_journal,
    parse_participant_plan,
    parse_participant_receipt,
    parse_phase_result,
    parse_private_request,
    parse_profile_validation_receipt,
    parse_public_status,
    parse_security_json,
    parse_witness,
    run_operation,
    seal_record,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "ai_video_production" / "task102_project_manifest_transaction.py"
SCHEMA = ROOT / "schemas" / "task102-project-manifest-transaction.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA.name


def h(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def participant_plan_record() -> dict:
    return seal_record(
        {
            "record_type": "PMST_PARTICIPANT_PLAN_V1",
            "protocol_version": PROTOCOL_VERSION,
            "operation_id": "operation-1",
            "participant_id": "participant-1",
            "participant_profile_id": "participant-profile-1",
            "semantic_owner_task_id": "TASK-099",
            "object_commitments": [h("participant-object")],
            "prepare_supported": True,
            "commit_supported": True,
            "reconcile_supported": True,
            "abort_before_commit_supported": True,
        },
        kind="participant_plan",
    )


def payload_for(kind: str) -> dict:
    value = {
        "MANIFEST_CREATE_V1": {
            "successor_manifest": {"project_id": "project-1", "revision": 1},
            "successor_manifest_sha256": h("manifest-1"),
            "semantic_authorization_sha256": h("authority"),
        },
        "MANIFEST_TRANSITION_V1": {
            "prior_manifest_sha256": h("manifest-1"),
            "prior_manifest_physical_identity_ref": "manifest-physical-1",
            "successor_manifest": {"project_id": "project-1", "revision": 2},
            "successor_manifest_sha256": h("manifest-2"),
            "participant_plan_sha256": participant_plan_record()["plan_sha256"],
            "semantic_authorization_sha256": h("authority"),
        },
        "CONTROL_OBJECT_CAS_V1": {
            "predecessor_sha256": h("object-1"),
            "predecessor_physical_identity_ref": "object-physical-1",
            "successor_document": {"revision": 2},
            "successor_sha256": h("object-2"),
            "semantic_authorization_sha256": h("authority"),
        },
        "CONTROL_APPEND_CHAIN_V1": {
            "prior_terminal_revision": 2,
            "prior_terminal_sha256": h("chain-2"),
            "successor_document": {"revision": 3},
            "successor_sha256": h("chain-3"),
            "semantic_authorization_sha256": h("authority"),
        },
        "CONTROL_RECOVERY_OBJECT_V1": {
            "recovery_action": "COMPLETE_FORWARD",
            "predecessor_sha256": h("recovery-1"),
            "successor_document": {"state": "TERMINAL"},
            "successor_sha256": h("recovery-2"),
            "terminal_proof_sha256": h("terminal-proof"),
            "semantic_authorization_sha256": h("authority"),
        },
        "CONTROL_SNAPSHOT_SET_V1": {
            "create_set": [h("create-1")],
            "retain_set": [h("retain-1")],
            "remove_set": [h("remove-1")],
            "retention_policy_sha256": h("retention"),
            "semantic_authorization_sha256": h("authority"),
        },
        "PROJECT_READ_LEASE_V1": {
            "expected_manifest_sha256": h("manifest-1"),
            "expected_state_coordinate_sha256": h("state-1"),
            "observation_profile_id": "read-profile-1",
        },
        "QUERY_OPERATION_V1": {
            "queried_operation_id": "operation-prior",
            "queried_intent_sha256": h("intent-prior"),
            "queried_request_sha256": h("request-prior"),
        },
    }[kind]
    document_pairs = {
        "MANIFEST_CREATE_V1": ("successor_manifest", "successor_manifest_sha256"),
        "MANIFEST_TRANSITION_V1": ("successor_manifest", "successor_manifest_sha256"),
        "CONTROL_OBJECT_CAS_V1": ("successor_document", "successor_sha256"),
        "CONTROL_APPEND_CHAIN_V1": ("successor_document", "successor_sha256"),
        "CONTROL_RECOVERY_OBJECT_V1": ("successor_document", "successor_sha256"),
    }
    if kind in document_pairs:
        document_field, digest_field = document_pairs[kind]
        value[digest_field] = sha256_bytes(canonical_json_bytes(value[document_field]))
    return value


def intent(kind: str = "MANIFEST_TRANSITION_V1", *, profile: str = "profile-1") -> dict:
    body = {
        "protocol_version": PROTOCOL_VERSION,
        "record_type": "PMST_OPERATION_INTENT_V1",
        "project_registration_id": "registration-1",
        "operation_id": "operation-1",
        "operation_kind": kind,
        "operation_profile_id": profile,
        "caller_task_id": "TASK-099",
        "caller_build_sha256": h("build"),
        "caller_policy_sha256": h("policy"),
        "requested_at": "2026-09-27T00:00:00Z",
        "expires_at": "2026-09-27T00:05:00Z",
        "payload": payload_for(kind),
    }
    return seal_record(body, kind="intent")


def request(kind: str = "MANIFEST_TRANSITION_V1", *, profile: str = "profile-1") -> dict:
    body = {
        "protocol_version": PROTOCOL_VERSION,
        "record_type": "PMST_PRIVATE_REQUEST_V1",
        "broker_instance_id": "broker-1",
        "session_id": "session-1",
        "request_nonce_id": "nonce-1",
        "intent": intent(kind, profile=profile),
    }
    return seal_record(body, kind="request")


def admission_context() -> AdmissionContext:
    return AdmissionContext(
        broker_instance_id="broker-1",
        session_id="session-1",
        client_process_instance_sha256=h("client-process"),
        broker_process_instance_sha256=h("broker-process"),
        security_binding_sha256=h("security"),
        broker_install_binding_sha256=h("install"),
        trusted_now="2026-09-27T00:00:30Z",
    )


def nonce_ledger(req: dict, context: AdmissionContext) -> PureNonceLedger:
    operation = req["intent"]
    ledger = PureNonceLedger()
    ledger.register(
        NonceBinding(
            request_nonce_id=req["request_nonce_id"],
            intent_sha256=operation["intent_sha256"],
            project_registration_id=operation["project_registration_id"],
            operation_id=operation["operation_id"],
            operation_kind=operation["operation_kind"],
            operation_profile_id=operation["operation_profile_id"],
            context=context,
        )
    )
    return ledger


def operation_profile(kind: str, *, participants: bool = False) -> OperationProfile:
    phases = ["ADMIT"]
    if kind == "QUERY_OPERATION_V1":
        phases += ["QUERY", "RELEASE"]
    elif kind == "PROJECT_READ_LEASE_V1":
        phases += ["OPEN", "READ", "RELEASE"]
    else:
        phases += ["OPEN", "PREPARE"]
        if participants:
            phases.append("PARTICIPANTS")
        phases += ["STAGE", "COMMIT_OBJECTS"]
        if kind in {"MANIFEST_CREATE_V1", "MANIFEST_TRANSITION_V1"}:
            phases.append("COMMIT_MANIFEST")
        if participants:
            phases.append("RECONCILE")
        phases += ["TERMINAL", "RELEASE"]
    relation = {
        "MANIFEST_CREATE_V1": "ABSENT_TO_REVISION_1",
        "MANIFEST_TRANSITION_V1": "EXACT_PREDECESSOR_CAS",
        "CONTROL_OBJECT_CAS_V1": "EXACT_PREDECESSOR_CAS",
        "CONTROL_APPEND_CHAIN_V1": "APPEND_CHAIN",
        "CONTROL_RECOVERY_OBJECT_V1": "PROFILE_RECOVERY",
        "CONTROL_SNAPSHOT_SET_V1": "BOUNDED_SNAPSHOT_SET",
        "PROJECT_READ_LEASE_V1": "READ_ONLY_EXPECTED_STATE",
        "QUERY_OPERATION_V1": "QUERY_BY_OPERATION",
    }[kind]
    return OperationProfile(
        profile_id="profile-1",
        operation_kind=kind,
        target_class="FIXTURE_TARGET",
        parser_id="FIXTURE_PARSER_V1",
        transition_validator_id="FIXTURE_TRANSITION_V1",
        maximum_body_bytes=4_194_304,
        maximum_object_count=16,
        durability_class="READ_ONLY_PINNED" if kind in {"PROJECT_READ_LEASE_V1", "QUERY_OPERATION_V1"} else "DURABLE_READBACK",
        semantic_owner_task_id="TASK-099",
        allowed_predecessor_relation=relation,
        participant_plan_sha256s=(participant_plan_record()["plan_sha256"],) if participants else (),
        permitted_phases=tuple(phases),
        participant_required=participants,
    )


def enrollment_record(*, status: str = "ACTIVE") -> dict:
    return seal_record(
        {
            "record_type": "PMST_ENROLLMENT_V1",
            "protocol_version": PROTOCOL_VERSION,
            "project_registration_id": "registration-1",
            "project_id": "project-1",
            "root_physical_identity_ref": "root-physical-1",
            "control_physical_identity_ref": "control-physical-1",
            "manifest_physical_identity_ref": "manifest-physical-1",
            "volume_binding_sha256": h("volume"),
            "owner_dacl_binding_sha256": h("dacl"),
            "writer_migration_matrix_sha256": h("matrix"),
            "broker_install_binding_sha256": h("install"),
            "enrollment_epoch": "epoch-1",
            "created_at": "2026-09-27T00:00:00Z",
            "status": status,
        },
        kind="enrollment",
    )


def profile_validation_record(req: dict, profile: OperationProfile) -> dict | None:
    if req["intent"]["operation_kind"] in {"PROJECT_READ_LEASE_V1", "QUERY_OPERATION_V1"}:
        return None
    return seal_record(
        {
            "record_type": "PMST_PROFILE_VALIDATION_RECEIPT_V1",
            "protocol_version": PROTOCOL_VERSION,
            "operation_id": req["intent"]["operation_id"],
            "intent_sha256": req["intent"]["intent_sha256"],
            "operation_profile_id": profile.profile_id,
            "parser_id": profile.parser_id,
            "transition_validator_id": profile.transition_validator_id,
            "semantic_owner_task_id": profile.semantic_owner_task_id,
            "validated_payload_sha256": sha256_bytes(canonical_json_bytes(req["intent"]["payload"])),
            "validation_status": "ACCEPTED",
        },
        kind="profile_validation",
    )


def journal_record(req: dict, profile: OperationProfile, journal_phase: str, sequence: int) -> dict:
    operation = req["intent"]
    return seal_record(
        {
            "record_type": "PMST_TRANSACTION_JOURNAL_V1",
            "protocol_version": PROTOCOL_VERSION,
            "project_registration_id": operation["project_registration_id"],
            "operation_id": operation["operation_id"],
            "operation_kind": operation["operation_kind"],
            "operation_profile_id": operation["operation_profile_id"],
            "intent_sha256": operation["intent_sha256"],
            "request_sha256": req["request_sha256"],
            "caller_task_id": operation["caller_task_id"],
            "caller_build_sha256": operation["caller_build_sha256"],
            "caller_policy_sha256": operation["caller_policy_sha256"],
            "prior_observation_sha256": h("state"),
            "intended_successor_set_sha256": sha256_bytes(canonical_json_bytes(operation["payload"])),
            "participant_plan_sha256s": list(profile.participant_plan_sha256s),
            "broker_instance_id": req["broker_instance_id"],
            "enrollment_epoch": "epoch-1",
            "expires_at": operation["expires_at"],
            "phase": journal_phase,
            "phase_sequence": sequence,
            "phase_evidence_sha256s": [],
        },
        kind="journal",
    )


def witness_record(
    req: dict,
    profile: OperationProfile,
    journal: dict,
    state: str,
    observation: str,
    *,
    participant_receipts: tuple[str, ...] = (),
    objects: tuple[str, ...] = (),
) -> dict:
    manifest_committed = state == "COMMITTED_DURABLE" and profile.operation_kind in {"MANIFEST_CREATE_V1", "MANIFEST_TRANSITION_V1"}
    return seal_record(
        {
            "record_type": "PMST_OPERATION_WITNESS_V1",
            "protocol_version": PROTOCOL_VERSION,
            "project_registration_id": req["intent"]["project_registration_id"],
            "operation_id": req["intent"]["operation_id"],
            "operation_kind": profile.operation_kind,
            "operation_profile_id": profile.profile_id,
            "intent_sha256": req["intent"]["intent_sha256"],
            "request_sha256": req["request_sha256"],
            "prior_observation_sha256": journal["prior_observation_sha256"],
            "intended_successor_set_sha256": journal["intended_successor_set_sha256"],
            "participant_plan_sha256s": list(profile.participant_plan_sha256s),
            "observed_participant_receipt_sha256s": list(participant_receipts),
            "observed_object_identity_sha256s": list(objects),
            "journal_sha256": journal["journal_sha256"],
            "broker_instance_id": req["broker_instance_id"],
            "enrollment_epoch": "epoch-1",
            "witness_state": state,
            "manifest_commit_observation": observation,
            "committed_manifest_sha256": req["intent"]["payload"].get("successor_manifest_sha256") if manifest_committed else None,
            "committed_manifest_physical_identity_ref": "manifest-physical-2" if manifest_committed else None,
            "created_at": "2026-09-27T00:00:01Z",
            "terminalized_at": None if state == "PREPARED" else "2026-09-27T00:00:20Z",
        },
        kind="witness",
    )


def participant_receipt_record(status: str, phase_name: str, effect: str, sequence: int) -> dict:
    return seal_record(
        {
            "record_type": "PMST_PARTICIPANT_RECEIPT_V1",
            "protocol_version": PROTOCOL_VERSION,
            "operation_id": "operation-1",
            "participant_id": "participant-1",
            "plan_sha256": participant_plan_record()["plan_sha256"],
            "participant_phase": phase_name,
            "participant_status": status,
            "object_observations": participant_plan_record()["object_commitments"],
            "effect_observation": effect,
            "receipt_sequence": sequence,
        },
        kind="participant",
    )


def execute(
    req: dict,
    profile: OperationProfile,
    script: list[dict],
    *,
    evidence: PureEvidenceRegistry | None = None,
    validation: dict | None | object = ...,
) -> dict:
    context = admission_context()
    receipt = profile_validation_record(req, profile) if validation is ... else validation
    return run_operation(
        req,
        profile,
        ScriptedFakePmstPort(script),
        enrollment_record(),
        receipt,
        evidence or PureEvidenceRegistry(),
        nonce_ledger(req, context),
        context,
    ).to_dict()


def make_machine(
    req: dict,
    profile: OperationProfile,
    *,
    evidence: PureEvidenceRegistry | None = None,
    context: AdmissionContext | None = None,
    ledger: PureNonceLedger | None = None,
    enrollment: dict | None = None,
) -> PurePmstStateMachine:
    actual_context = context or admission_context()
    return PurePmstStateMachine(
        req,
        profile,
        enrollment or enrollment_record(),
        profile_validation_record(req, profile),
        evidence or PureEvidenceRegistry(),
        ledger or nonce_ledger(req, actual_context),
        actual_context,
    )


def phase(
    req: dict,
    name: str,
    status: str,
    payload: dict,
    *,
    observation: str = "NOT_OBSERVED",
    effects: int = 0,
    reason: str | None = None,
) -> dict:
    operation = req["intent"]
    body = {
        "protocol_version": PROTOCOL_VERSION,
        "record_type": "PMST_PRIVATE_PHASE_RESULT_V1",
        "broker_instance_id": req["broker_instance_id"],
        "session_id": req["session_id"],
        "project_registration_id": operation["project_registration_id"],
        "operation_id": operation["operation_id"],
        "operation_kind": operation["operation_kind"],
        "operation_profile_id": operation["operation_profile_id"],
        "intent_sha256": operation["intent_sha256"],
        "request_sha256": req["request_sha256"],
        "phase": name,
        "phase_status": status,
        "manifest_commit_observation": observation,
        "effect_count": effects,
        "reason_code": reason,
        "payload": payload,
    }
    return seal_record(body, kind="phase")


def release(req: dict, *, observation: str, effects: int, warning: str | None = None) -> dict:
    return phase(
        req,
        "RELEASE",
        "RELEASE_WARNING" if warning else "RELEASED",
        {"release_warning_code": warning},
        observation=observation,
        effects=effects,
        reason="LEASE_RELEASE_WARNING" if warning else None,
    )


def manifest_success_fixture(req: dict, *, reconciliation_required: bool = False) -> tuple[list[dict], PureEvidenceRegistry]:
    profile = operation_profile("MANIFEST_TRANSITION_V1", participants=True)
    prepared_journal = journal_record(req, profile, "PREPARED", 1)
    prepared_witness = witness_record(req, profile, prepared_journal, "PREPARED", "NOT_OBSERVED")
    prepare_receipt = participant_receipt_record("PREPARED_NO_COMMIT", "PREPARE", "NO_EFFECT", 1)
    commit_receipt = participant_receipt_record("OBJECTS_COMMITTED", "COMMIT", "COMMITTED", 2)
    terminal_status = "RECONCILIATION_REQUIRED_COMMITTED" if reconciliation_required else "RECONCILED_COMMITTED"
    reconcile_receipt = participant_receipt_record(terminal_status, "RECONCILE", "COMMITTED", 3)
    committed_journal = journal_record(req, profile, "MANIFEST_COMMITTED", 6)
    committed_witness = witness_record(
        req,
        profile,
        committed_journal,
        "COMMITTED_DURABLE",
        "COMMITTED",
        participant_receipts=(prepare_receipt["receipt_sha256"], commit_receipt["receipt_sha256"]),
        objects=(h("stage"),),
    )
    terminal_journal = journal_record(req, profile, "TERMINAL", 8)
    terminal_witness = witness_record(
        req,
        profile,
        committed_journal if reconciliation_required else terminal_journal,
        "COMMITTED_DURABLE",
        "COMMITTED",
        participant_receipts=(prepare_receipt["receipt_sha256"], commit_receipt["receipt_sha256"], reconcile_receipt["receipt_sha256"]),
        objects=(h("stage"),),
    )
    readback = ReadbackBinding(
        readback_sha256=h("readback"),
        operation_id=req["intent"]["operation_id"],
        intent_sha256=req["intent"]["intent_sha256"],
        manifest_sha256=req["intent"]["payload"]["successor_manifest_sha256"],
        state_coordinate_sha256=h("successor-state"),
        security_binding_sha256=h("security"),
        operation_witness_sha256=terminal_witness["witness_sha256"],
        manifest_commit_observation="COMMITTED",
    )
    registry = PureEvidenceRegistry(
        [participant_plan_record(), prepared_journal, prepared_witness, prepare_receipt, commit_receipt, reconcile_receipt, committed_journal, committed_witness, terminal_journal, terminal_witness],
        [readback],
    )
    script = [
        phase(req, "ADMIT", "ACCEPTED_NO_EFFECT", {"admission_binding_sha256": h("admission")}),
        phase(req, "OPEN", "CURRENT_NO_EFFECT", {"manifest_sha256": h("manifest-1"), "manifest_physical_identity_ref": "manifest-physical-1", "state_coordinate_sha256": h("state"), "security_binding_sha256": h("security")}),
        phase(req, "PREPARE", "PREPARED", {"journal_sha256": prepared_journal["journal_sha256"], "intent_witness_sha256": prepared_witness["witness_sha256"]}),
        phase(req, "PARTICIPANTS", "PARTICIPANTS_PREPARED", {"participant_receipt_sha256s": [prepare_receipt["receipt_sha256"]]}),
        phase(req, "STAGE", "OBJECTS_STAGED", {"staged_identity_sha256s": [h("stage")]}),
        phase(req, "COMMIT_OBJECTS", "OBJECTS_COMMITTED", {"object_receipt_sha256s": [commit_receipt["receipt_sha256"]]}, effects=1),
        phase(req, "COMMIT_MANIFEST", "MANIFEST_COMMITTED", {"prior_manifest_sha256": h("manifest-1"), "successor_manifest_sha256": req["intent"]["payload"]["successor_manifest_sha256"], "successor_physical_identity_ref": "manifest-physical-2", "operation_witness_sha256": committed_witness["witness_sha256"]}, observation="COMMITTED", effects=2),
        phase(req, "RECONCILE", "RECONCILIATION_REQUIRED" if reconciliation_required else "RECONCILED", {"participant_terminal_receipt_sha256s": [reconcile_receipt["receipt_sha256"]]}, observation="COMMITTED", effects=2, reason="RECONCILIATION_REQUIRED" if reconciliation_required else None),
        phase(req, "TERMINAL", "COMMITTED_WITH_READBACK", {"operation_witness_sha256": terminal_witness["witness_sha256"], "fresh_readback_sha256": h("readback"), "admission_barrier_state": "CLOSED" if reconciliation_required else "OPEN"}, observation="COMMITTED", effects=2),
        release(req, observation="COMMITTED", effects=2),
    ]
    return script, registry


def control_participant_success_fixture(req: dict) -> tuple[list[dict], PureEvidenceRegistry]:
    profile = operation_profile("CONTROL_OBJECT_CAS_V1", participants=True)
    prepared_journal = journal_record(req, profile, "PREPARED", 1)
    prepared_witness = witness_record(req, profile, prepared_journal, "PREPARED", "NOT_OBSERVED")
    prepare_receipt = participant_receipt_record("PREPARED_NO_COMMIT", "PREPARE", "NO_EFFECT", 1)
    commit_receipt = participant_receipt_record("OBJECTS_COMMITTED", "COMMIT", "COMMITTED", 2)
    reconcile_receipt = participant_receipt_record("RECONCILED_COMMITTED", "RECONCILE", "COMMITTED", 3)
    terminal_journal = journal_record(req, profile, "TERMINAL", 6)
    terminal_witness = witness_record(
        req,
        profile,
        terminal_journal,
        "COMMITTED_DURABLE",
        "NOT_OBSERVED",
        participant_receipts=(prepare_receipt["receipt_sha256"], commit_receipt["receipt_sha256"], reconcile_receipt["receipt_sha256"]),
        objects=(h("control-stage"),),
    )
    readback = ReadbackBinding(
        readback_sha256=h("control-readback"),
        operation_id=req["intent"]["operation_id"],
        intent_sha256=req["intent"]["intent_sha256"],
        manifest_sha256=h("manifest-1"),
        state_coordinate_sha256=h("control-successor-state"),
        security_binding_sha256=h("security"),
        operation_witness_sha256=terminal_witness["witness_sha256"],
        manifest_commit_observation="NOT_OBSERVED",
    )
    registry = PureEvidenceRegistry(
        [participant_plan_record(), prepared_journal, prepared_witness, prepare_receipt, commit_receipt, reconcile_receipt, terminal_journal, terminal_witness],
        [readback],
    )
    script = [
        phase(req, "ADMIT", "ACCEPTED_NO_EFFECT", {"admission_binding_sha256": h("admission")}),
        phase(req, "OPEN", "CURRENT_NO_EFFECT", {"manifest_sha256": h("manifest-1"), "manifest_physical_identity_ref": "manifest-physical-1", "state_coordinate_sha256": h("state"), "security_binding_sha256": h("security")}),
        phase(req, "PREPARE", "PREPARED", {"journal_sha256": prepared_journal["journal_sha256"], "intent_witness_sha256": prepared_witness["witness_sha256"]}),
        phase(req, "PARTICIPANTS", "PARTICIPANTS_PREPARED", {"participant_receipt_sha256s": [prepare_receipt["receipt_sha256"]]}),
        phase(req, "STAGE", "OBJECTS_STAGED", {"staged_identity_sha256s": [h("control-stage")]}),
        phase(req, "COMMIT_OBJECTS", "OBJECTS_COMMITTED", {"object_receipt_sha256s": [commit_receipt["receipt_sha256"]]}, effects=1),
        phase(req, "RECONCILE", "RECONCILED", {"participant_terminal_receipt_sha256s": [reconcile_receipt["receipt_sha256"]]}, effects=1),
        phase(req, "TERMINAL", "COMMITTED_WITH_READBACK", {"operation_witness_sha256": terminal_witness["witness_sha256"], "fresh_readback_sha256": h("control-readback"), "admission_barrier_state": "OPEN"}, effects=1),
        release(req, observation="NOT_OBSERVED", effects=1),
    ]
    return script, registry


def query_witness_fixture(
    req: dict,
    state: str,
    observation: str,
    *,
    with_readback: bool,
    readback_manifest_sha256: str | None = None,
) -> tuple[dict, PureEvidenceRegistry]:
    journal_phase, sequence = {
        "COMMITTED_DURABLE": ("MANIFEST_COMMITTED", 5),
        "NOT_COMMITTED_PROVEN": ("MANIFEST_COMMITTING", 4),
        "UNKNOWN_QUARANTINED": ("UNKNOWN_QUARANTINED", 5),
    }[state]
    journal = seal_record(
        {
            "record_type": "PMST_TRANSACTION_JOURNAL_V1",
            "protocol_version": PROTOCOL_VERSION,
            "project_registration_id": "registration-1",
            "operation_id": "operation-prior",
            "operation_kind": "MANIFEST_CREATE_V1",
            "operation_profile_id": "target-profile",
            "intent_sha256": h("intent-prior"),
            "request_sha256": h("request-prior"),
            "caller_task_id": "TASK-099",
            "caller_build_sha256": h("target-build"),
            "caller_policy_sha256": h("target-policy"),
            "prior_observation_sha256": h("target-prior"),
            "intended_successor_set_sha256": h("target-successors"),
            "participant_plan_sha256s": [],
            "broker_instance_id": "broker-1",
            "enrollment_epoch": "epoch-1",
            "expires_at": "2026-09-27T00:05:00Z",
            "phase": journal_phase,
            "phase_sequence": sequence,
            "phase_evidence_sha256s": [],
        },
        kind="journal",
    )
    committed = state == "COMMITTED_DURABLE"
    witness = seal_record(
        {
            "record_type": "PMST_OPERATION_WITNESS_V1",
            "protocol_version": PROTOCOL_VERSION,
            "project_registration_id": "registration-1",
            "operation_id": "operation-prior",
            "operation_kind": "MANIFEST_CREATE_V1",
            "operation_profile_id": "target-profile",
            "intent_sha256": h("intent-prior"),
            "request_sha256": h("request-prior"),
            "prior_observation_sha256": h("target-prior"),
            "intended_successor_set_sha256": h("target-successors"),
            "participant_plan_sha256s": [],
            "observed_participant_receipt_sha256s": [],
            "observed_object_identity_sha256s": [h("target-object")],
            "journal_sha256": journal["journal_sha256"],
            "broker_instance_id": "broker-1",
            "enrollment_epoch": "epoch-1",
            "witness_state": state,
            "manifest_commit_observation": observation,
            "committed_manifest_sha256": h("target-manifest") if committed else None,
            "committed_manifest_physical_identity_ref": "target-manifest-physical" if committed else None,
            "created_at": "2026-09-27T00:00:01Z",
            "terminalized_at": "2026-09-27T00:00:20Z",
        },
        kind="witness",
    )
    readbacks = []
    if with_readback:
        readbacks.append(
            ReadbackBinding(
                readback_sha256=h("query-readback"),
                operation_id=req["intent"]["operation_id"],
                intent_sha256=req["intent"]["intent_sha256"],
                manifest_sha256=readback_manifest_sha256 or h("target-manifest"),
                state_coordinate_sha256=h("target-state"),
                security_binding_sha256=h("security"),
                operation_witness_sha256=witness["witness_sha256"],
                manifest_commit_observation=observation,
            )
        )
    return witness, PureEvidenceRegistry([journal, witness], readbacks)


def test_all_intent_payload_variants_and_request_round_trip() -> None:
    for kind in (
        "MANIFEST_CREATE_V1",
        "MANIFEST_TRANSITION_V1",
        "CONTROL_OBJECT_CAS_V1",
        "CONTROL_APPEND_CHAIN_V1",
        "CONTROL_RECOVERY_OBJECT_V1",
        "CONTROL_SNAPSHOT_SET_V1",
        "PROJECT_READ_LEASE_V1",
        "QUERY_OPERATION_V1",
    ):
        value = intent(kind)
        assert parse_intent(value).to_dict() == value
        wrapped = request(kind)
        assert parse_private_request(wrapped).to_dict() == wrapped


def test_intent_rejects_wrong_union_paths_and_overlapping_snapshot_sets() -> None:
    wrong = intent("PROJECT_READ_LEASE_V1")
    wrong["payload"] = payload_for("QUERY_OPERATION_V1")
    wrong = seal_record(wrong, kind="intent")
    with pytest.raises(ValueError, match="fields are not exact"):
        parse_intent(wrong)

    path = intent()
    path["payload"]["prior_manifest_physical_identity_ref"] = "C:\\private\\project.json"
    path = seal_record(path, kind="intent")
    with pytest.raises(ValueError, match="opaque identifier"):
        parse_intent(path)

    overlap = intent("CONTROL_SNAPSHOT_SET_V1")
    overlap["payload"]["remove_set"] = overlap["payload"]["create_set"]
    overlap = seal_record(overlap, kind="intent")
    with pytest.raises(ValueError, match="disjoint"):
        parse_intent(overlap)

    mismatched = intent("MANIFEST_CREATE_V1")
    mismatched["payload"]["successor_manifest_sha256"] = h("foreign-document")
    mismatched = seal_record(mismatched, kind="intent")
    with pytest.raises(ValueError, match="canonical successor"):
        parse_intent(mismatched)


def test_strict_json_rejects_duplicate_bom_nonfinite_and_depth() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        parse_security_json(b'{"a":1,"a":2}')
    with pytest.raises(ValueError, match="BOM"):
        parse_security_json(b"\xef\xbb\xbf{}")
    with pytest.raises(ValueError, match="nonfinite"):
        parse_security_json(b'{"a":NaN}')
    with pytest.raises(ValueError, match="depth"):
        parse_security_json(("[" * 30 + "0" + "]" * 30).encode())


@pytest.mark.parametrize(
    ("participant_phase", "participant_status", "effect"),
    [
        ("PREPARE", "PREPARED_NO_COMMIT", "NO_EFFECT"),
        ("PREPARE", "PREPARE_BLOCKED_NO_EFFECT", "NO_EFFECT"),
        ("PREPARE", "PREPARE_OUTCOME_UNKNOWN", "UNKNOWN"),
        ("COMMIT", "OBJECTS_COMMITTED", "COMMITTED"),
        ("COMMIT", "OBJECTS_NOT_COMMITTED_PROVEN", "NOT_COMMITTED"),
        ("COMMIT", "OBJECT_COMMIT_OUTCOME_UNKNOWN", "UNKNOWN"),
        ("RECONCILE", "RECONCILED_COMMITTED", "COMMITTED"),
        ("RECONCILE", "RECONCILED_NOT_COMMITTED", "NOT_COMMITTED"),
        ("RECONCILE", "RECONCILIATION_REQUIRED_COMMITTED", "COMMITTED"),
        ("RECONCILE", "RECONCILIATION_REQUIRED_NOT_COMMITTED", "NOT_COMMITTED"),
        ("RECONCILE", "RECONCILIATION_REQUIRED_UNKNOWN", "UNKNOWN"),
        ("ABORT", "ABORTED_OWNED_PREPARE", "NOT_COMMITTED"),
        ("ABORT", "ABORT_NOT_PROVEN", "UNKNOWN"),
    ],
)
def test_participant_exact_tuple_union(participant_phase: str, participant_status: str, effect: str) -> None:
    body = {
        "record_type": "PMST_PARTICIPANT_RECEIPT_V1",
        "protocol_version": PROTOCOL_VERSION,
        "operation_id": "operation-1",
        "participant_id": "participant-1",
        "plan_sha256": h("plan"),
        "participant_phase": participant_phase,
        "participant_status": participant_status,
        "object_observations": [],
        "effect_observation": effect,
        "receipt_sequence": 1,
    }
    sealed = seal_record(body, kind="participant")
    assert parse_participant_receipt(sealed).to_dict() == sealed


@pytest.mark.parametrize(
    ("participant_phase", "participant_status", "effect"),
    [
        ("COMMIT", "OBJECTS_COMMITTED", "UNKNOWN"),
        ("COMMIT", "OBJECTS_NOT_COMMITTED_PROVEN", "COMMITTED"),
        ("RECONCILE", "RECONCILED_COMMITTED", "UNKNOWN"),
        ("RECONCILE", "RECONCILIATION_REQUIRED_UNKNOWN", "COMMITTED"),
    ],
)
def test_participant_contradictory_tuples_are_rejected(participant_phase: str, participant_status: str, effect: str) -> None:
    body = {
        "record_type": "PMST_PARTICIPANT_RECEIPT_V1",
        "protocol_version": PROTOCOL_VERSION,
        "operation_id": "operation-1",
        "participant_id": "participant-1",
        "plan_sha256": h("plan"),
        "participant_phase": participant_phase,
        "participant_status": participant_status,
        "object_observations": [],
        "effect_observation": effect,
        "receipt_sequence": 1,
    }
    with pytest.raises(ValueError, match="tuple"):
        parse_participant_receipt(seal_record(body, kind="participant"))


def test_prepared_and_terminal_witness_invariants() -> None:
    base = {
        "record_type": "PMST_OPERATION_WITNESS_V1",
        "protocol_version": PROTOCOL_VERSION,
        "project_registration_id": "registration-1",
        "operation_id": "operation-1",
        "operation_kind": "MANIFEST_TRANSITION_V1",
        "operation_profile_id": "profile-1",
        "intent_sha256": h("intent"),
        "request_sha256": h("request"),
        "prior_observation_sha256": h("prior"),
        "intended_successor_set_sha256": h("successors"),
        "participant_plan_sha256s": [h("plan")],
        "observed_participant_receipt_sha256s": [],
        "observed_object_identity_sha256s": [],
        "journal_sha256": h("journal"),
        "broker_instance_id": "broker-1",
        "enrollment_epoch": "epoch-1",
        "witness_state": "PREPARED",
        "manifest_commit_observation": "NOT_OBSERVED",
        "committed_manifest_sha256": None,
        "committed_manifest_physical_identity_ref": None,
        "created_at": "2026-09-27T00:00:01Z",
        "terminalized_at": None,
    }
    prepared = seal_record(base, kind="witness")
    assert parse_witness(prepared).to_dict() == prepared

    future = copy.deepcopy(base)
    future["observed_object_identity_sha256s"] = [h("future")]
    with pytest.raises(ValueError, match="future"):
        parse_witness(seal_record(future, kind="witness"))

    terminal = copy.deepcopy(base)
    terminal.update({
        "witness_state": "COMMITTED_DURABLE",
        "manifest_commit_observation": "COMMITTED",
        "committed_manifest_sha256": h("manifest-2"),
        "committed_manifest_physical_identity_ref": "manifest-physical-2",
        "terminalized_at": "2026-09-27T00:00:02Z",
    })
    assert parse_witness(seal_record(terminal, kind="witness")).to_dict()["witness_state"] == "COMMITTED_DURABLE"


def test_journal_phase_sequence_and_evidence_count_are_exact() -> None:
    body = {
        "record_type": "PMST_TRANSACTION_JOURNAL_V1",
        "protocol_version": PROTOCOL_VERSION,
        "project_registration_id": "registration-1",
        "operation_id": "operation-1",
        "operation_kind": "MANIFEST_TRANSITION_V1",
        "operation_profile_id": "profile-1",
        "intent_sha256": h("intent"),
        "request_sha256": h("request"),
        "caller_task_id": "TASK-099",
        "caller_build_sha256": h("build"),
        "caller_policy_sha256": h("policy"),
        "prior_observation_sha256": h("prior"),
        "intended_successor_set_sha256": h("successors"),
        "participant_plan_sha256s": [h("plan")],
        "broker_instance_id": "broker-1",
        "enrollment_epoch": "epoch-1",
        "expires_at": "2026-09-27T00:05:00Z",
        "phase": "OBJECTS_STAGED",
        "phase_sequence": 3,
        "phase_evidence_sha256s": [h("phase-1"), h("phase-2"), h("phase-3")],
    }
    sealed = seal_record(body, kind="journal")
    assert parse_journal(sealed).to_dict() == sealed
    bad = copy.deepcopy(body)
    bad["phase_sequence"] = 2
    with pytest.raises(ValueError, match="sequence"):
        parse_journal(seal_record(bad, kind="journal"))

    no_participants = copy.deepcopy(body)
    no_participants["operation_kind"] = "MANIFEST_CREATE_V1"
    no_participants["participant_plan_sha256s"] = []
    no_participants["phase"] = "OBJECTS_STAGED"
    no_participants["phase_sequence"] = 2
    no_participants["phase_evidence_sha256s"] = [h("phase-1"), h("phase-2")]
    assert parse_journal(seal_record(no_participants, kind="journal")).to_dict()["phase_sequence"] == 2

    control_terminal = copy.deepcopy(no_participants)
    control_terminal["operation_kind"] = "CONTROL_OBJECT_CAS_V1"
    control_terminal["phase"] = "TERMINAL"
    control_terminal["phase_sequence"] = 4
    control_terminal["phase_evidence_sha256s"] = [h(f"control-{index}") for index in range(4)]
    assert parse_journal(seal_record(control_terminal, kind="journal")).to_dict()["phase_sequence"] == 4


def test_enrollment_and_participant_plan_are_strict_body_free_records() -> None:
    enrollment = seal_record(
        {
            "record_type": "PMST_ENROLLMENT_V1",
            "protocol_version": PROTOCOL_VERSION,
            "project_registration_id": "registration-1",
            "project_id": "project-1",
            "root_physical_identity_ref": "root-physical-1",
            "control_physical_identity_ref": "control-physical-1",
            "manifest_physical_identity_ref": "manifest-physical-1",
            "volume_binding_sha256": h("volume"),
            "owner_dacl_binding_sha256": h("dacl"),
            "writer_migration_matrix_sha256": h("matrix"),
            "broker_install_binding_sha256": h("install"),
            "enrollment_epoch": "epoch-1",
            "created_at": "2026-09-27T00:00:00Z",
            "status": "ACTIVE",
        },
        kind="enrollment",
    )
    assert parse_enrollment(enrollment).to_dict() == enrollment

    plan = seal_record(
        {
            "record_type": "PMST_PARTICIPANT_PLAN_V1",
            "protocol_version": PROTOCOL_VERSION,
            "operation_id": "operation-1",
            "participant_id": "participant-1",
            "participant_profile_id": "participant-profile-1",
            "semantic_owner_task_id": "TASK-099",
            "object_commitments": [h("object-1")],
            "prepare_supported": True,
            "commit_supported": True,
            "reconcile_supported": True,
            "abort_before_commit_supported": True,
        },
        kind="participant_plan",
    )
    assert parse_participant_plan(plan).to_dict() == plan
    invalid = copy.deepcopy(plan)
    invalid["prepare_supported"] = 1
    invalid = seal_record(invalid, kind="participant_plan")
    with pytest.raises(ValueError, match="booleans"):
        parse_participant_plan(invalid)


def test_nonce_is_bound_and_consumed_once_before_port_use() -> None:
    req = request("MANIFEST_CREATE_V1")
    context = admission_context()
    ledger = nonce_ledger(req, context)
    make_machine(req, operation_profile("MANIFEST_CREATE_V1"), ledger=ledger, context=context)
    with pytest.raises(ValueError, match="already consumed"):
        make_machine(req, operation_profile("MANIFEST_CREATE_V1"), ledger=ledger, context=context)

    drifted = AdmissionContext(
        broker_instance_id=context.broker_instance_id,
        session_id=context.session_id,
        client_process_instance_sha256=h("foreign-client"),
        broker_process_instance_sha256=context.broker_process_instance_sha256,
        security_binding_sha256=context.security_binding_sha256,
        broker_install_binding_sha256=context.broker_install_binding_sha256,
        trusted_now=context.trusted_now,
    )
    second_ledger = nonce_ledger(req, context)
    with pytest.raises(ValueError, match="binding"):
        make_machine(req, operation_profile("MANIFEST_CREATE_V1"), ledger=second_ledger, context=drifted)

    inactive_ledger = nonce_ledger(req, context)
    with pytest.raises(ValueError, match="ACTIVE"):
        make_machine(req, operation_profile("MANIFEST_CREATE_V1"), enrollment=enrollment_record(status="SUSPENDED"), ledger=inactive_ledger, context=context)
    make_machine(req, operation_profile("MANIFEST_CREATE_V1"), ledger=inactive_ledger, context=context)


def test_profile_route_and_durability_are_closed() -> None:
    valid = operation_profile("CONTROL_OBJECT_CAS_V1")
    assert valid.permitted_phases == ("ADMIT", "OPEN", "PREPARE", "STAGE", "COMMIT_OBJECTS", "TERMINAL", "RELEASE")
    with pytest.raises(ValueError, match="permitted phases"):
        OperationProfile(
            profile_id="profile-1", operation_kind="CONTROL_OBJECT_CAS_V1", target_class="FIXTURE_TARGET",
            parser_id="PARSER", transition_validator_id="VALIDATOR", maximum_body_bytes=1024,
            maximum_object_count=1, durability_class="DURABLE_READBACK", semantic_owner_task_id="TASK-099",
            allowed_predecessor_relation="EXACT_PREDECESSOR_CAS", participant_plan_sha256s=(),
            permitted_phases=("ADMIT", "RELEASE"),
            participant_required=False,
        )


def test_prepared_phase_may_report_durable_internal_effects() -> None:
    req = request("MANIFEST_CREATE_V1")
    value = phase(
        req,
        "PREPARE",
        "PREPARED",
        {"journal_sha256": h("journal"), "intent_witness_sha256": h("intent-witness")},
        effects=2,
    )
    assert parse_phase_result(value).to_dict()["effect_count"] == 2


def test_manifest_happy_path_is_deterministic_and_public_safe() -> None:
    req = request()
    script, evidence = manifest_success_fixture(req)
    port = ScriptedFakePmstPort(script)
    context = admission_context()
    profile = operation_profile("MANIFEST_TRANSITION_V1", participants=True)
    result = run_operation(req, profile, port, enrollment_record(), profile_validation_record(req, profile), evidence, nonce_ledger(req, context), context).to_dict()
    assert result["status"] == "COMMITTED_WITH_READBACK"
    assert result["effect_count"] == 2
    assert result["retry_allowed"] is False
    assert result["human_recovery_required"] is False
    assert port.calls == ["ADMIT", "OPEN", "PREPARE", "PARTICIPANTS", "STAGE", "COMMIT_OBJECTS", "COMMIT_MANIFEST", "RECONCILE", "TERMINAL", "RELEASE"]
    assert "session_id" not in result and "request_nonce_id" not in result
    assert parse_public_status(result).to_dict() == result


def test_release_warning_attaches_without_changing_known_outcome() -> None:
    req = request()
    script, evidence = manifest_success_fixture(req)
    script[-1] = release(req, observation="COMMITTED", effects=2, warning="LEASE_RELEASE_WARNING")
    result = execute(req, operation_profile("MANIFEST_TRANSITION_V1", participants=True), script, evidence=evidence)
    assert result["status"] == "COMMITTED_WITH_READBACK"
    assert result["reason_codes"] == ["LEASE_RELEASE_WARNING"]
    assert result["human_recovery_required"] is False


def test_out_of_order_binding_and_effect_regression_fail_closed() -> None:
    req = request()
    context = admission_context()
    script, evidence = manifest_success_fixture(req)
    machine = make_machine(req, operation_profile("MANIFEST_TRANSITION_V1", participants=True), evidence=evidence, context=context)
    with pytest.raises(ValueError, match="out of order"):
        machine.accept(script[1])

    admit = script[0]
    foreign = copy.deepcopy(admit)
    foreign["operation_id"] = "foreign-operation"
    foreign = seal_record(foreign, kind="phase")
    with pytest.raises(ValueError, match="binding"):
        machine.accept(foreign)

    script, evidence = manifest_success_fixture(req)
    context = admission_context()
    machine = make_machine(req, operation_profile("MANIFEST_TRANSITION_V1", participants=True), evidence=evidence, context=context)
    for value in script[:7]:
        machine.accept(value)
    regression = copy.deepcopy(script[7])
    regression["effect_count"] = 1
    regression = seal_record(regression, kind="phase")
    with pytest.raises(ValueError, match="monotonic"):
        machine.accept(regression)


def test_manifest_commit_and_terminal_witness_must_match_intent_chain() -> None:
    req = request()
    script, evidence = manifest_success_fixture(req)
    context = admission_context()
    machine = make_machine(req, operation_profile("MANIFEST_TRANSITION_V1", participants=True), evidence=evidence, context=context)
    for value in script[:6]:
        machine.accept(value)
    foreign_successor = copy.deepcopy(script[6])
    foreign_successor["payload"]["successor_manifest_sha256"] = h("foreign-successor")
    foreign_successor = seal_record(foreign_successor, kind="phase")
    with pytest.raises(ValueError, match="successor commitment"):
        machine.accept(foreign_successor)

    context = admission_context()
    machine = make_machine(req, operation_profile("MANIFEST_TRANSITION_V1", participants=True), evidence=evidence, context=context)
    for value in script[:8]:
        machine.accept(value)
    foreign_witness = copy.deepcopy(script[8])
    foreign_witness["payload"]["operation_witness_sha256"] = h("foreign-witness")
    foreign_witness = seal_record(foreign_witness, kind="phase")
    with pytest.raises(ValueError, match="witness|evidence"):
        machine.accept(foreign_witness)


def test_unknown_manifest_outcome_keeps_barrier_closed() -> None:
    req = request("MANIFEST_CREATE_V1")
    profile = operation_profile("MANIFEST_CREATE_V1")
    prepared_journal = journal_record(req, profile, "PREPARED", 1)
    prepared_witness = witness_record(req, profile, prepared_journal, "PREPARED", "NOT_OBSERVED")
    unknown_journal = journal_record(req, profile, "UNKNOWN_QUARANTINED", 5)
    unknown_witness = witness_record(req, profile, unknown_journal, "UNKNOWN_QUARANTINED", "UNKNOWN", objects=(h("stage"),))
    evidence = PureEvidenceRegistry([prepared_journal, prepared_witness, unknown_journal, unknown_witness])
    script = [
        phase(req, "ADMIT", "ACCEPTED_NO_EFFECT", {"admission_binding_sha256": h("admission")}),
        phase(req, "OPEN", "CURRENT_NO_EFFECT", {"manifest_sha256": h("absent-proof"), "manifest_physical_identity_ref": "manifest-slot-1", "state_coordinate_sha256": h("state"), "security_binding_sha256": h("security")}),
        phase(req, "PREPARE", "PREPARED", {"journal_sha256": prepared_journal["journal_sha256"], "intent_witness_sha256": prepared_witness["witness_sha256"]}),
        phase(req, "STAGE", "OBJECTS_STAGED", {"staged_identity_sha256s": [h("stage")]}),
        phase(req, "COMMIT_OBJECTS", "OBJECTS_COMMITTED", {"object_receipt_sha256s": [h("object-receipt")]}, effects=1),
        phase(req, "COMMIT_MANIFEST", "MANIFEST_OUTCOME_UNKNOWN", {"prior_manifest_sha256": h("absent-proof"), "successor_manifest_sha256": req["intent"]["payload"]["successor_manifest_sha256"], "successor_physical_identity_ref": None, "operation_witness_sha256": unknown_witness["witness_sha256"]}, observation="UNKNOWN", effects=1),
        phase(req, "TERMINAL", "COMMIT_OUTCOME_UNKNOWN", {"operation_witness_sha256": unknown_witness["witness_sha256"], "fresh_readback_sha256": None, "admission_barrier_state": "CLOSED"}, observation="UNKNOWN", effects=1, reason="MANIFEST_COMMIT_UNKNOWN"),
        release(req, observation="UNKNOWN", effects=1),
    ]
    result = execute(req, profile, script, evidence=evidence)
    assert result["status"] == "COMMIT_OUTCOME_UNKNOWN"
    assert result["human_recovery_required"] is True

    script[-2]["payload"]["admission_barrier_state"] = "OPEN"
    script[-2] = seal_record(script[-2], kind="phase")
    with pytest.raises(ValueError, match="closed"):
        execute(req, profile, script, evidence=evidence)


@pytest.mark.parametrize(
    ("status", "payload", "observation", "public_status", "human"),
    [
        ("COMMITTED_CURRENT", {"operation_witness_sha256": h("w"), "fresh_readback_sha256": h("r")}, "COMMITTED", "QUERY_COMMITTED_CURRENT", False),
        ("COMMITTED_SUPERSEDED", {"operation_witness_sha256": h("w"), "fresh_readback_sha256": h("r")}, "COMMITTED", "QUERY_COMMITTED_SUPERSEDED", False),
        ("NOT_COMMITTED", {"operation_witness_sha256": h("w"), "fresh_readback_sha256": h("r")}, "NOT_COMMITTED", "QUERY_NOT_COMMITTED", False),
        ("UNKNOWN_WITH_WITNESS", {"operation_witness_sha256": h("w"), "fresh_readback_sha256": h("r")}, "UNKNOWN", "QUERY_UNKNOWN_WITH_WITNESS", True),
        ("WITNESS_NOT_FOUND_NO_EFFECT", {"queried_operation_id": "operation-prior", "queried_intent_sha256": h("intent-prior"), "absence_observation_sha256": h("absence")}, "NOT_OBSERVED", "QUERY_WITNESS_NOT_FOUND_NO_EFFECT", False),
        ("WITNESS_EVIDENCE_UNAVAILABLE_NO_EFFECT", {"queried_operation_id": "operation-prior", "queried_intent_sha256": h("intent-prior"), "evidence_failure_class": "CORRUPT_RECORD", "failure_observation_sha256": h("failure")}, "NOT_OBSERVED", "QUERY_WITNESS_EVIDENCE_UNAVAILABLE_NO_EFFECT", True),
        ("READBACK_EVIDENCE_UNAVAILABLE_WITH_WITNESS", {"queried_operation_id": "operation-prior", "queried_intent_sha256": h("intent-prior"), "operation_witness_sha256": h("w"), "evidence_failure_class": "IO_FAILURE", "failure_observation_sha256": h("failure")}, "COMMITTED", "QUERY_READBACK_EVIDENCE_UNAVAILABLE_WITH_WITNESS", True),
    ],
)
def test_all_query_outcomes_have_closed_public_mapping(status: str, payload: dict, observation: str, public_status: str, human: bool) -> None:
    req = request("QUERY_OPERATION_V1")
    evidence = PureEvidenceRegistry()
    state_by_status = {
        "COMMITTED_CURRENT": "COMMITTED_DURABLE",
        "COMMITTED_SUPERSEDED": "COMMITTED_DURABLE",
        "NOT_COMMITTED": "NOT_COMMITTED_PROVEN",
        "UNKNOWN_WITH_WITNESS": "UNKNOWN_QUARANTINED",
        "READBACK_EVIDENCE_UNAVAILABLE_WITH_WITNESS": "COMMITTED_DURABLE",
    }
    if status in state_by_status:
        witness, evidence = query_witness_fixture(
            req,
            state_by_status[status],
            observation,
            with_readback=status != "READBACK_EVIDENCE_UNAVAILABLE_WITH_WITNESS",
            readback_manifest_sha256=h("later-manifest") if status == "COMMITTED_SUPERSEDED" else None,
        )
        payload = {**payload, "operation_witness_sha256": witness["witness_sha256"]}
        if "fresh_readback_sha256" in payload:
            payload["fresh_readback_sha256"] = h("query-readback")
    script = [
        phase(req, "ADMIT", "ACCEPTED_NO_EFFECT", {"admission_binding_sha256": h("admission")}),
        phase(req, "QUERY", status, payload, observation=observation),
        release(req, observation=observation, effects=0),
    ]
    result = execute(req, operation_profile("QUERY_OPERATION_V1"), script, evidence=evidence)
    assert result["status"] == public_status
    assert result["human_recovery_required"] is human
    assert result["effect_count"] == 0


@pytest.mark.parametrize(
    ("status", "payload", "public_status"),
    [
        ("READ_CURRENT_NO_EFFECT", {"manifest_sha256": h("manifest"), "state_coordinate_sha256": h("state"), "readback_sha256": h("readback")}, "READ_CURRENT_NO_EFFECT"),
        ("READ_BLOCKED_NO_EFFECT", {"read_failure_class": "IO_FAILURE", "failure_observation_sha256": h("failure")}, "READ_BLOCKED_NO_EFFECT"),
    ],
)
def test_read_success_and_failure_never_create_witness(status: str, payload: dict, public_status: str) -> None:
    req = request("PROJECT_READ_LEASE_V1")
    expected_manifest = req["intent"]["payload"]["expected_manifest_sha256"]
    expected_state = req["intent"]["payload"]["expected_state_coordinate_sha256"]
    if status == "READ_CURRENT_NO_EFFECT":
        payload = {**payload, "manifest_sha256": expected_manifest, "state_coordinate_sha256": expected_state}
        evidence = PureEvidenceRegistry(
            readbacks=[
                ReadbackBinding(
                    readback_sha256=payload["readback_sha256"],
                    operation_id=req["intent"]["operation_id"],
                    intent_sha256=req["intent"]["intent_sha256"],
                    manifest_sha256=expected_manifest,
                    state_coordinate_sha256=expected_state,
                    security_binding_sha256=h("security"),
                    operation_witness_sha256=None,
                    manifest_commit_observation="NOT_OBSERVED",
                )
            ]
        )
    else:
        evidence = PureEvidenceRegistry()
    script = [
        phase(req, "ADMIT", "ACCEPTED_NO_EFFECT", {"admission_binding_sha256": h("admission")}),
        phase(req, "OPEN", "CURRENT_NO_EFFECT", {"manifest_sha256": expected_manifest, "manifest_physical_identity_ref": "manifest-physical-1", "state_coordinate_sha256": expected_state, "security_binding_sha256": h("security")}),
        phase(req, "READ", status, payload),
        release(req, observation="NOT_OBSERVED", effects=0),
    ]
    result = execute(req, operation_profile("PROJECT_READ_LEASE_V1"), script, evidence=evidence)
    assert result["status"] == public_status
    assert result["operation_witness_sha256"] is None
    assert result["effect_count"] == 0


def test_pre_effect_rejection_projects_blocked_without_witness() -> None:
    req = request("MANIFEST_CREATE_V1")
    script = [
        phase(req, "ADMIT", "REJECTED_NO_EFFECT", {"rejection_class": "SESSION_REJECTED"}, reason="SESSION_REJECTED"),
        release(req, observation="NOT_OBSERVED", effects=0),
    ]
    result = execute(req, operation_profile("MANIFEST_CREATE_V1"), script)
    assert result["status"] == "BLOCKED_NO_WRITE"
    assert result["operation_witness_sha256"] is None
    assert result["readback_sha256"] is None


def test_public_nullability_and_recovery_flags_fail_closed() -> None:
    req = request("QUERY_OPERATION_V1")
    script = [
        phase(req, "ADMIT", "ACCEPTED_NO_EFFECT", {"admission_binding_sha256": h("admission")}),
        phase(req, "QUERY", "WITNESS_EVIDENCE_UNAVAILABLE_NO_EFFECT", {"queried_operation_id": "operation-prior", "queried_intent_sha256": h("intent-prior"), "evidence_failure_class": "IO_FAILURE", "failure_observation_sha256": h("failure")}),
        release(req, observation="NOT_OBSERVED", effects=0),
    ]
    value = execute(req, operation_profile("QUERY_OPERATION_V1"), script)
    bad = copy.deepcopy(value)
    bad["operation_witness_sha256"] = h("fabricated")
    bad = seal_record(bad, kind="public")
    with pytest.raises(ValueError, match="nullability"):
        parse_public_status(bad)
    bad = copy.deepcopy(value)
    bad["human_recovery_required"] = False
    bad = seal_record(bad, kind="public")
    with pytest.raises(ValueError, match="flags"):
        parse_public_status(bad)


def test_fake_port_cannot_be_mistaken_for_live_backend() -> None:
    req = request("MANIFEST_CREATE_V1")

    class PretendLivePort:
        fixture_only = False

        def perform(self, phase_name, request_value, prior_result):
            raise AssertionError((phase_name, request_value, prior_result))

    with pytest.raises(ValueError, match="fixture-only"):
        context = admission_context()
        profile = operation_profile("MANIFEST_CREATE_V1")
        run_operation(req, profile, PretendLivePort(), enrollment_record(), profile_validation_record(req, profile), PureEvidenceRegistry(), nonce_ledger(req, context), context)

    class FakeSubclass(ScriptedFakePmstPort):
        pass

    with pytest.raises(ValueError, match="fixture-only"):
        context = admission_context()
        profile = operation_profile("MANIFEST_CREATE_V1")
        run_operation(req, profile, FakeSubclass([]), enrollment_record(), profile_validation_record(req, profile), PureEvidenceRegistry(), nonce_ledger(req, context), context)


def test_phase_sha_nulls_are_rejected_by_parser_and_schema() -> None:
    req = request("MANIFEST_CREATE_V1")
    value = phase(req, "PREPARE", "PREPARED", {"journal_sha256": None, "intent_witness_sha256": h("witness")})
    with pytest.raises(ValueError, match="must not be null"):
        parse_phase_result(value)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(value))


def test_admission_time_and_open_security_binding_fail_before_any_commit() -> None:
    req = request("MANIFEST_CREATE_V1")
    profile = operation_profile("MANIFEST_CREATE_V1")
    expired = replace(admission_context(), trusted_now="2026-09-27T00:05:00Z")
    expired_ledger = nonce_ledger(req, expired)
    with pytest.raises(ValueError, match="trusted broker time"):
        make_machine(req, profile, context=expired, ledger=expired_ledger)

    machine = make_machine(req, profile)
    machine.accept(phase(req, "ADMIT", "ACCEPTED_NO_EFFECT", {"admission_binding_sha256": h("admission")}))
    with pytest.raises(ValueError, match="security observation"):
        machine.accept(phase(req, "OPEN", "CURRENT_NO_EFFECT", {"manifest_sha256": h("absent"), "manifest_physical_identity_ref": "manifest-slot", "state_coordinate_sha256": h("state"), "security_binding_sha256": h("foreign-security")}))
    assert machine.effect_count == 0


def test_profile_limits_and_validation_receipt_are_enforced() -> None:
    req = request("CONTROL_SNAPSHOT_SET_V1")
    profile = operation_profile("CONTROL_SNAPSHOT_SET_V1")
    with pytest.raises(ValueError, match="byte bound"):
        make_machine(req, replace(profile, maximum_body_bytes=1))
    with pytest.raises(ValueError, match="object bound"):
        make_machine(req, replace(profile, maximum_object_count=2))

    validation = profile_validation_record(req, profile)
    assert validation is not None
    validation["parser_id"] = "foreign-parser"
    validation = seal_record(validation, kind="profile_validation")
    context = admission_context()
    with pytest.raises(ValueError, match="does not match"):
        PurePmstStateMachine(req, profile, enrollment_record(), validation, PureEvidenceRegistry(), nonce_ledger(req, context), context)


def test_commit_effect_and_release_count_cannot_be_fabricated() -> None:
    req = request()
    script, evidence = manifest_success_fixture(req)
    machine = make_machine(req, operation_profile("MANIFEST_TRANSITION_V1", participants=True), evidence=evidence)
    for value in script[:6]:
        machine.accept(value)
    zero_effect_commit = copy.deepcopy(script[6])
    zero_effect_commit["effect_count"] = 1
    zero_effect_commit = seal_record(zero_effect_commit, kind="phase")
    with pytest.raises(ValueError, match="advance effect_count"):
        machine.accept(zero_effect_commit)

    machine = make_machine(req, operation_profile("MANIFEST_TRANSITION_V1", participants=True), evidence=evidence)
    for value in script[:-1]:
        machine.accept(value)
    jumping_release = release(req, observation="COMMITTED", effects=3)
    with pytest.raises(ValueError, match="preserve"):
        machine.accept(jumping_release)


def test_empty_participant_and_object_evidence_fail_closed() -> None:
    req = request()
    script, evidence = manifest_success_fixture(req)
    machine = make_machine(req, operation_profile("MANIFEST_TRANSITION_V1", participants=True), evidence=evidence)
    for value in script[:3]:
        machine.accept(value)
    empty_participants = copy.deepcopy(script[3])
    empty_participants["payload"]["participant_receipt_sha256s"] = []
    empty_participants = seal_record(empty_participants, kind="phase")
    with pytest.raises(ValueError, match="incomplete"):
        machine.accept(empty_participants)

    machine = make_machine(req, operation_profile("MANIFEST_TRANSITION_V1", participants=True), evidence=evidence)
    for value in script[:4]:
        machine.accept(value)
    empty_stage = copy.deepcopy(script[4])
    empty_stage["payload"]["staged_identity_sha256s"] = []
    empty_stage = seal_record(empty_stage, kind="phase")
    with pytest.raises(ValueError, match="at least one"):
        machine.accept(empty_stage)


def test_terminal_status_must_match_witness_and_manifest_outcome() -> None:
    req = request()
    script, evidence = manifest_success_fixture(req)
    machine = make_machine(req, operation_profile("MANIFEST_TRANSITION_V1", participants=True), evidence=evidence)
    for value in script[:8]:
        machine.accept(value)
    contradiction = copy.deepcopy(script[8])
    contradiction["phase_status"] = "NOT_COMMITTED_PROVEN"
    contradiction = seal_record(contradiction, kind="phase")
    with pytest.raises(ValueError, match="witness state|contradicts"):
        machine.accept(contradiction)


def test_reconciliation_required_preserves_known_commit_and_requires_human() -> None:
    req = request()
    script, evidence = manifest_success_fixture(req, reconciliation_required=True)
    result = execute(req, operation_profile("MANIFEST_TRANSITION_V1", participants=True), script, evidence=evidence)
    assert result["status"] == "COMMITTED_WITH_READBACK"
    assert result["reason_codes"] == ["RECONCILIATION_REQUIRED"]
    assert result["human_recovery_required"] is True
    assert result["effect_count"] == 2


def test_committed_witness_and_terminal_readback_content_are_cross_bound() -> None:
    req = request()
    profile = operation_profile("MANIFEST_TRANSITION_V1", participants=True)
    script, evidence = manifest_success_fixture(req)
    committed = evidence.require(script[6]["payload"]["operation_witness_sha256"], "PMST_OPERATION_WITNESS_V1")
    committed["committed_manifest_sha256"] = h("foreign-manifest")
    committed["committed_manifest_physical_identity_ref"] = "foreign-manifest-physical"
    committed = seal_record(committed, kind="witness")
    evidence.add(committed)
    foreign_commit = copy.deepcopy(script[6])
    foreign_commit["payload"]["operation_witness_sha256"] = committed["witness_sha256"]
    foreign_commit = seal_record(foreign_commit, kind="phase")
    machine = make_machine(req, profile, evidence=evidence)
    for value in script[:6]:
        machine.accept(value)
    with pytest.raises(ValueError, match="committed witness"):
        machine.accept(foreign_commit)

    script, evidence = manifest_success_fixture(req)
    terminal_witness_sha = script[8]["payload"]["operation_witness_sha256"]
    evidence.add_readback(
        ReadbackBinding(
            readback_sha256=h("foreign-terminal-readback"),
            operation_id=req["intent"]["operation_id"],
            intent_sha256=req["intent"]["intent_sha256"],
            manifest_sha256=h("foreign-manifest"),
            state_coordinate_sha256=h("successor-state"),
            security_binding_sha256=h("security"),
            operation_witness_sha256=terminal_witness_sha,
            manifest_commit_observation="COMMITTED",
        )
    )
    script[8]["payload"]["fresh_readback_sha256"] = h("foreign-terminal-readback")
    script[8] = seal_record(script[8], kind="phase")
    with pytest.raises(ValueError, match="readback does not match"):
        execute(req, profile, script, evidence=evidence)


def test_prepared_journal_content_is_bound_to_open_state_and_intent() -> None:
    req = request()
    profile = operation_profile("MANIFEST_TRANSITION_V1", participants=True)
    script, evidence = manifest_success_fixture(req)
    prepared = evidence.require(script[2]["payload"]["journal_sha256"], "PMST_TRANSACTION_JOURNAL_V1")
    prepared["intended_successor_set_sha256"] = h("foreign-successor-set")
    prepared = seal_record(prepared, kind="journal")
    prepared_witness = evidence.require(script[2]["payload"]["intent_witness_sha256"], "PMST_OPERATION_WITNESS_V1")
    prepared_witness["journal_sha256"] = prepared["journal_sha256"]
    prepared_witness["intended_successor_set_sha256"] = prepared["intended_successor_set_sha256"]
    prepared_witness = seal_record(prepared_witness, kind="witness")
    evidence.add(prepared)
    evidence.add(prepared_witness)
    script[2]["payload"] = {"journal_sha256": prepared["journal_sha256"], "intent_witness_sha256": prepared_witness["witness_sha256"]}
    script[2] = seal_record(script[2], kind="phase")
    machine = make_machine(req, profile, evidence=evidence)
    machine.accept(script[0])
    machine.accept(script[1])
    with pytest.raises(ValueError, match="intent payload"):
        machine.accept(script[2])


def test_terminal_witness_requires_complete_observations_and_terminal_journal() -> None:
    req = request()
    profile = operation_profile("MANIFEST_TRANSITION_V1", participants=True)
    script, evidence = manifest_success_fixture(req)
    terminal = evidence.require(script[8]["payload"]["operation_witness_sha256"], "PMST_OPERATION_WITNESS_V1")
    terminal["observed_participant_receipt_sha256s"] = []
    terminal["observed_object_identity_sha256s"] = []
    terminal = seal_record(terminal, kind="witness")
    evidence.add(terminal)
    incomplete = copy.deepcopy(script)
    incomplete[8]["payload"]["operation_witness_sha256"] = terminal["witness_sha256"]
    incomplete[8] = seal_record(incomplete[8], kind="phase")
    with pytest.raises(ValueError, match="observations"):
        execute(req, profile, incomplete, evidence=evidence)

    script, evidence = manifest_success_fixture(req)
    terminal = evidence.require(script[8]["payload"]["operation_witness_sha256"], "PMST_OPERATION_WITNESS_V1")
    terminal["journal_sha256"] = evidence.require(script[6]["payload"]["operation_witness_sha256"], "PMST_OPERATION_WITNESS_V1")["journal_sha256"]
    terminal = seal_record(terminal, kind="witness")
    evidence.add(terminal)
    evidence.add_readback(
        ReadbackBinding(
            readback_sha256=h("nonterminal-journal-readback"),
            operation_id=req["intent"]["operation_id"],
            intent_sha256=req["intent"]["intent_sha256"],
            manifest_sha256=req["intent"]["payload"]["successor_manifest_sha256"],
            state_coordinate_sha256=h("successor-state"),
            security_binding_sha256=h("security"),
            operation_witness_sha256=terminal["witness_sha256"],
            manifest_commit_observation="COMMITTED",
        )
    )
    script[8]["payload"] = {
        "operation_witness_sha256": terminal["witness_sha256"],
        "fresh_readback_sha256": h("nonterminal-journal-readback"),
        "admission_barrier_state": "OPEN",
    }
    script[8] = seal_record(script[8], kind="phase")
    with pytest.raises(ValueError, match="TERMINAL journal"):
        execute(req, profile, script, evidence=evidence)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("participant_id", "foreign-participant", "identity"),
        ("receipt_sequence", 999, "sequence"),
        ("object_observations", [h("foreign-object")], "observations"),
    ],
)
def test_participant_identity_and_sequence_bind_to_plan(field: str, value: object, message: str) -> None:
    req = request()
    profile = operation_profile("MANIFEST_TRANSITION_V1", participants=True)
    script, evidence = manifest_success_fixture(req)
    receipt = evidence.require(script[3]["payload"]["participant_receipt_sha256s"][0], "PMST_PARTICIPANT_RECEIPT_V1")
    receipt[field] = value
    receipt = seal_record(receipt, kind="participant")
    evidence.add(receipt)
    script[3]["payload"]["participant_receipt_sha256s"] = [receipt["receipt_sha256"]]
    script[3] = seal_record(script[3], kind="phase")
    machine = make_machine(req, profile, evidence=evidence)
    for phase_result in script[:3]:
        machine.accept(phase_result)
    with pytest.raises(ValueError, match=message):
        machine.accept(script[3])


def test_query_current_and_superseded_are_readback_derived() -> None:
    req = request("QUERY_OPERATION_V1")
    witness, current_evidence = query_witness_fixture(req, "COMMITTED_DURABLE", "COMMITTED", with_readback=True)
    superseded_script = [
        phase(req, "ADMIT", "ACCEPTED_NO_EFFECT", {"admission_binding_sha256": h("admission")}),
        phase(req, "QUERY", "COMMITTED_SUPERSEDED", {"operation_witness_sha256": witness["witness_sha256"], "fresh_readback_sha256": h("query-readback")}, observation="COMMITTED"),
        release(req, observation="COMMITTED", effects=0),
    ]
    with pytest.raises(ValueError, match="supersession"):
        execute(req, operation_profile("QUERY_OPERATION_V1"), superseded_script, evidence=current_evidence)

    witness, later_evidence = query_witness_fixture(
        req,
        "COMMITTED_DURABLE",
        "COMMITTED",
        with_readback=True,
        readback_manifest_sha256=h("later-manifest"),
    )
    current_script = [
        phase(req, "ADMIT", "ACCEPTED_NO_EFFECT", {"admission_binding_sha256": h("admission")} ),
        phase(req, "QUERY", "COMMITTED_CURRENT", {"operation_witness_sha256": witness["witness_sha256"], "fresh_readback_sha256": h("query-readback")}, observation="COMMITTED"),
        release(req, observation="COMMITTED", effects=0),
    ]
    with pytest.raises(ValueError, match="currentness"):
        execute(req, operation_profile("QUERY_OPERATION_V1"), current_script, evidence=later_evidence)


def test_query_witness_state_must_match_journal_phase() -> None:
    req = request("QUERY_OPERATION_V1")
    witness, evidence = query_witness_fixture(req, "COMMITTED_DURABLE", "COMMITTED", with_readback=True)
    journal = evidence.require(witness["journal_sha256"], "PMST_TRANSACTION_JOURNAL_V1")
    journal["phase"] = "PREPARED"
    journal["phase_sequence"] = 1
    journal = seal_record(journal, kind="journal")
    witness["journal_sha256"] = journal["journal_sha256"]
    witness = seal_record(witness, kind="witness")
    evidence = PureEvidenceRegistry(
        [journal, witness],
        [
            ReadbackBinding(
                readback_sha256=h("query-readback"),
                operation_id=req["intent"]["operation_id"],
                intent_sha256=req["intent"]["intent_sha256"],
                manifest_sha256=h("target-manifest"),
                state_coordinate_sha256=h("target-state"),
                security_binding_sha256=h("security"),
                operation_witness_sha256=witness["witness_sha256"],
                manifest_commit_observation="COMMITTED",
            )
        ],
    )
    script = [
        phase(req, "ADMIT", "ACCEPTED_NO_EFFECT", {"admission_binding_sha256": h("admission")}),
        phase(req, "QUERY", "COMMITTED_CURRENT", {"operation_witness_sha256": witness["witness_sha256"], "fresh_readback_sha256": h("query-readback")}, observation="COMMITTED"),
        release(req, observation="COMMITTED", effects=0),
    ]
    with pytest.raises(ValueError, match="journal phase"):
        execute(req, operation_profile("QUERY_OPERATION_V1"), script, evidence=evidence)


def test_unknown_query_parser_matches_schema_observation_domain() -> None:
    req = request("QUERY_OPERATION_V1")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for observation in ("COMMITTED", "NOT_COMMITTED"):
        value = phase(
            req,
            "QUERY",
            "UNKNOWN_WITH_WITNESS",
            {"operation_witness_sha256": h("unknown-witness"), "fresh_readback_sha256": h("unknown-readback")},
            observation=observation,
        )
        with pytest.raises(ValueError, match="unknown query witness observation"):
            parse_phase_result(value)
        assert list(validator.iter_errors(value))


def test_nonmanifest_participant_route_reconciles_before_terminal() -> None:
    req = request("CONTROL_OBJECT_CAS_V1")
    profile = operation_profile("CONTROL_OBJECT_CAS_V1", participants=True)
    script, evidence = control_participant_success_fixture(req)
    result = execute(req, profile, script, evidence=evidence)
    assert result["status"] == "COMMITTED_WITH_READBACK"
    assert result["effect_count"] == 1
    assert result["human_recovery_required"] is False

    script, evidence = control_participant_success_fixture(req)
    unknown_receipt = participant_receipt_record("OBJECT_COMMIT_OUTCOME_UNKNOWN", "COMMIT", "UNKNOWN", 2)
    evidence.add(unknown_receipt)
    unknown = phase(
        req,
        "COMMIT_OBJECTS",
        "OBJECT_OUTCOME_UNKNOWN",
        {"object_receipt_sha256s": [unknown_receipt["receipt_sha256"]]},
        effects=1,
        reason="OBJECT_COMMIT_UNKNOWN",
    )
    machine = make_machine(req, profile, evidence=evidence)
    for result_phase in script[:5]:
        machine.accept(result_phase)
    machine.accept(unknown)
    assert machine.expected_phase == "RECONCILE"


def test_manifest_object_unknown_reconciles_and_closes_without_claiming_manifest_attempt() -> None:
    req = request()
    profile = operation_profile("MANIFEST_TRANSITION_V1", participants=True)
    success, evidence = manifest_success_fixture(req)
    prepare_receipt_sha = success[3]["payload"]["participant_receipt_sha256s"][0]
    commit_unknown = participant_receipt_record("OBJECT_COMMIT_OUTCOME_UNKNOWN", "COMMIT", "UNKNOWN", 2)
    reconcile_unknown = participant_receipt_record("RECONCILIATION_REQUIRED_UNKNOWN", "RECONCILE", "UNKNOWN", 3)
    unknown_journal = journal_record(req, profile, "UNKNOWN_QUARANTINED", 4)
    unknown_witness = witness_record(
        req,
        profile,
        unknown_journal,
        "UNKNOWN_QUARANTINED",
        "NOT_OBSERVED",
        participant_receipts=(prepare_receipt_sha, commit_unknown["receipt_sha256"], reconcile_unknown["receipt_sha256"]),
        objects=(h("stage"),),
    )
    for record in (commit_unknown, reconcile_unknown, unknown_journal, unknown_witness):
        evidence.add(record)
    script = success[:5] + [
        phase(req, "COMMIT_OBJECTS", "OBJECT_OUTCOME_UNKNOWN", {"object_receipt_sha256s": [commit_unknown["receipt_sha256"]]}, effects=1, reason="OBJECT_COMMIT_UNKNOWN"),
        phase(req, "RECONCILE", "RECONCILIATION_REQUIRED", {"participant_terminal_receipt_sha256s": [reconcile_unknown["receipt_sha256"]]}, effects=1, reason="RECONCILIATION_REQUIRED"),
        phase(req, "TERMINAL", "BLOCKED_AFTER_PREPARE", {"operation_witness_sha256": unknown_witness["witness_sha256"], "fresh_readback_sha256": None, "admission_barrier_state": "CLOSED"}, effects=1, reason="OBJECT_COMMIT_UNKNOWN"),
        release(req, observation="NOT_OBSERVED", effects=1),
    ]
    result = execute(req, profile, script, evidence=evidence)
    assert result["status"] == "COMMIT_OUTCOME_UNKNOWN"
    assert result["human_recovery_required"] is True
    assert result["readback_sha256"] is None
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    assert list(validator.iter_errors(unknown_witness)) == []
    assert list(validator.iter_errors(script[-2])) == []


def test_open_current_physical_identity_null_is_rejected_by_parser_and_schema() -> None:
    req = request("MANIFEST_CREATE_V1")
    value = phase(req, "OPEN", "CURRENT_NO_EFFECT", {"manifest_sha256": h("manifest"), "manifest_physical_identity_ref": None, "state_coordinate_sha256": h("state"), "security_binding_sha256": h("security")})
    with pytest.raises(ValueError, match="physical identity"):
        parse_phase_result(value)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(value))


def test_unrelated_query_witness_and_readback_are_rejected() -> None:
    req = request("QUERY_OPERATION_V1")
    witness, evidence = query_witness_fixture(req, "COMMITTED_DURABLE", "COMMITTED", with_readback=True)
    script = [
        phase(req, "ADMIT", "ACCEPTED_NO_EFFECT", {"admission_binding_sha256": h("admission")}),
        phase(req, "QUERY", "COMMITTED_CURRENT", {"operation_witness_sha256": witness["witness_sha256"], "fresh_readback_sha256": h("query-readback")}, observation="COMMITTED"),
        release(req, observation="COMMITTED", effects=0),
    ]
    foreign = copy.deepcopy(witness)
    foreign["operation_id"] = "foreign-operation"
    foreign = seal_record(foreign, kind="witness")
    foreign_registry = PureEvidenceRegistry([evidence.require(witness["journal_sha256"], "PMST_TRANSACTION_JOURNAL_V1"), foreign])
    script[1]["payload"]["operation_witness_sha256"] = foreign["witness_sha256"]
    script[1] = seal_record(script[1], kind="phase")
    with pytest.raises(ValueError, match="queried operation"):
        execute(req, operation_profile("QUERY_OPERATION_V1"), script, evidence=foreign_registry)

    correct_script = [
        phase(req, "ADMIT", "ACCEPTED_NO_EFFECT", {"admission_binding_sha256": h("admission")}),
        phase(req, "QUERY", "COMMITTED_CURRENT", {"operation_witness_sha256": witness["witness_sha256"], "fresh_readback_sha256": h("query-readback")}, observation="COMMITTED"),
        release(req, observation="COMMITTED", effects=0),
    ]
    foreign_readback = ReadbackBinding(
        readback_sha256=h("query-readback"),
        operation_id="foreign-query",
        intent_sha256=req["intent"]["intent_sha256"],
        manifest_sha256=h("target-manifest"),
        state_coordinate_sha256=h("target-state"),
        security_binding_sha256=h("security"),
        operation_witness_sha256=witness["witness_sha256"],
        manifest_commit_observation="COMMITTED",
    )
    records = [
        evidence.require(witness["journal_sha256"], "PMST_TRANSACTION_JOURNAL_V1"),
        witness,
    ]
    with pytest.raises(ValueError, match="readback binding"):
        execute(req, operation_profile("QUERY_OPERATION_V1"), correct_script, evidence=PureEvidenceRegistry(records, [foreign_readback]))


def test_schema_is_valid_mirrored_and_covers_records() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    req = request()
    success_script, _ = manifest_success_fixture(req)
    records = [req["intent"], req, success_script[0], enrollment_record()]
    participant_plan = seal_record(
        {
            "record_type": "PMST_PARTICIPANT_PLAN_V1", "protocol_version": PROTOCOL_VERSION,
            "operation_id": "operation-1", "participant_id": "participant-1",
            "participant_profile_id": "participant-profile-1", "semantic_owner_task_id": "TASK-099",
            "object_commitments": [h("object")], "prepare_supported": True, "commit_supported": True,
            "reconcile_supported": True, "abort_before_commit_supported": True,
        },
        kind="participant_plan",
    )
    records.append(participant_plan)
    participant = {
        "record_type": "PMST_PARTICIPANT_RECEIPT_V1", "protocol_version": PROTOCOL_VERSION,
        "operation_id": "operation-1", "participant_id": "participant-1", "plan_sha256": h("plan"),
        "participant_phase": "COMMIT", "participant_status": "OBJECTS_COMMITTED",
        "object_observations": [h("object")], "effect_observation": "COMMITTED", "receipt_sequence": 1,
    }
    records.append(seal_record(participant, kind="participant"))
    profile = operation_profile("MANIFEST_TRANSITION_V1", participants=True)
    validation = profile_validation_record(req, profile)
    assert validation is not None
    assert parse_profile_validation_receipt(validation).to_dict() == validation
    records.append(validation)
    for record in records:
        assert list(validator.iter_errors(record)) == []

    extra = copy.deepcopy(req)
    extra["path"] = "C:/forbidden"
    assert list(validator.iter_errors(extra))

    contradiction = seal_record({**participant, "effect_observation": "UNKNOWN"}, kind="participant")
    assert list(validator.iter_errors(contradiction))

    wrong_phase = copy.deepcopy(success_script[0])
    wrong_phase["phase"] = "OPEN"
    wrong_phase = seal_record(wrong_phase, kind="phase")
    assert list(validator.iter_errors(wrong_phase))

    extra_payload = copy.deepcopy(success_script[0])
    extra_payload["payload"]["path"] = "C:/forbidden"
    extra_payload = seal_record(extra_payload, kind="phase")
    assert list(validator.iter_errors(extra_payload))


def test_source_has_no_native_or_existing_store_imports() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported.isdisjoint({"os", "pathlib", "subprocess", "socket", "ctypes", "winreg", "shutil", "tempfile"})
    text = SOURCE.read_text(encoding="utf-8")
    assert "product_project_store" not in text
    assert "project_save" not in text
    assert "open(" not in text
